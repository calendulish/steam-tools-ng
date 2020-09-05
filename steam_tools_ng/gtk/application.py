#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2020
#
# The Steam Tools NG is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Steam Tools NG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#
import asyncio
import itertools
import logging
import os
import ssl
import sys
from typing import Any, List, Optional

import aiohttp
from gi.repository import Gio, Gtk
from stlib import universe, plugins, webapi

from . import about, settings, login, window, utils
from .. import config, i18n, core

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class SteamToolsNG(Gtk.Application):
    def __init__(self, plugin_manager: plugins.Manager) -> None:
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self._session = None
        self._webapi_session = None
        self.plugin_manager = plugin_manager

        self._main_window_id = 0
        self.gtk_settings = Gtk.Settings.get_default()

        self.api_login: Optional[webapi.Login] = None
        self._time_offset = 0
        self.api_url = config.parser.get("steam", "api_url")

    @property
    def main_window(self) -> Gtk.ApplicationWindow:
        current_window = self.get_window_by_id(self._main_window_id)
        assert isinstance(current_window, Gtk.ApplicationWindow), "main window has not been created"
        return self.get_window_by_id(self._main_window_id)

    @property
    def time_offset(self) -> int:
        return self._time_offset

    @property
    def session(self) -> aiohttp.ClientSession:
        assert isinstance(self._session, aiohttp.ClientSession), "session has not been created"
        return self._session

    @property
    def webapi_session(self) -> webapi.SteamWebAPI:
        assert isinstance(self._webapi_session, webapi.SteamWebAPI), "webapi session has not been created"
        return self._webapi_session

    @property
    def steamid(self) -> Optional[int]:
        return config.parser.getint("login", "steamid")

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        settings_action = Gio.SimpleAction.new('settings')
        settings_action.connect("activate", self.on_settings_activate)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about")
        about_action.connect("activate", self.on_about_activate)
        self.add_action(about_action)

        exit_action = Gio.SimpleAction.new("exit")
        exit_action.connect("activate", self.on_exit_activate)
        self.add_action(exit_action)

        theme = config.parser.get("general", "theme")

        if theme == 'dark':
            self.gtk_settings.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings.props.gtk_application_prefer_dark_theme = False

    def do_activate(self) -> None:
        current_window = window.Main(application=self, title="Steam Tools NG")
        self._main_window_id = current_window.get_id()
        current_window.show()

        task = asyncio.gather(self.async_activate())
        task.add_done_callback(self.async_activate_callback)

    def async_activate_callback(self, future: 'asyncio.Future[Any]') -> None:
        if future.cancelled():
            return

        exception = future.exception()

        if exception and not isinstance(exception, asyncio.CancelledError):
            stack = future.get_stack()

            for frame in stack:
                log.critical(f"{type(exception).__name__} at {frame}")

            log.critical(f"Fatal Error: {str(exception)}")

            utils.fatal_error_dialog(exception, stack, self.main_window)
            loop = asyncio.get_running_loop()
            loop.stop()
            self.quit()

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_dialog = login.LoginDialog(self.main_window, self)
        login_dialog.set_deletable(False)
        login_dialog.show()

        if auto:
            encrypted_password = config.parser.get("login", "password")
            login_dialog.set_password(encrypted_password)
            login_dialog.login_button.clicked()

        if block:
            while self.main_window.get_realized():
                if login_dialog.has_user_data:
                    break

                await asyncio.sleep(1)

    async def async_activate(self) -> None:
        ssl_context = ssl.SSLContext()

        if hasattr(sys, 'frozen'):
            _executable_path = os.path.dirname(sys.executable)
            ssl_context.load_verify_locations(cafile=os.path.join(_executable_path, 'etc', 'cacert.pem'))

        tcp_connector = aiohttp.TCPConnector(ssl=ssl_context)
        self._session = aiohttp.ClientSession(raise_for_status=True, connector=tcp_connector)
        self._webapi_session = webapi.get_session(0, api_url=self.api_url, http_session=self._session)
        self._time_offset = await config.time_offset(self.webapi_session)

        self.main_window.set_warning(_("Logging on Steam. Please wait!"))
        log.info(_("Logging on Steam"))

        token = config.parser.get("login", "token")
        token_secure = config.parser.get("login", "token_secure")

        if not token or not token_secure or not self.steamid:
            await self.do_login()

        self.session.cookie_jar.update_cookies(config.login_cookies())  # type: ignore

        try:
            if await self.webapi_session.is_logged_in(self.steamid):
                log.info("Steam login Successful")
            else:
                await self.do_login(auto=True)
        except aiohttp.ClientError as exception:
            log.exception(str(exception))
            self.main_window.set_warning(_("No Connection. Please, check your connection."))
            await asyncio.sleep(10)
            return  # FIXME: RETRY ###

        self.main_window.unset_warning()

        modules = {
            "confirmations": asyncio.ensure_future(self.run_confirmations()),
            "steamguard": asyncio.ensure_future(self.run_steamguard()),
            "steamtrades": asyncio.ensure_future(self.run_steamtrades()),
            "steamgifts": asyncio.ensure_future(self.run_steamgifts()),
            "cardfarming": asyncio.ensure_future(self.run_cardfarming()),
        }

        while self.main_window.get_realized():
            for module_name, task in modules.items():
                if config.parser.getboolean("plugins", module_name):
                    if task.cancelled() and not task.exception():
                        if module_name != "confirmations":
                            self.main_window.set_status(module_name, status=_("Loading"))

                        coro = getattr(self, f"run_{module_name}")
                        modules[module_name] = asyncio.ensure_future(coro())

                    task.add_done_callback(self.async_activate_callback)
                else:
                    if not task.cancelled():
                        task.cancel()

                        try:
                            await task
                        except asyncio.CancelledError:
                            if module_name != "confirmations":
                                self.main_window.set_status(module_name, status=_("Disabled"))

            await asyncio.sleep(3)

    async def run_steamguard(self) -> None:
        while self.main_window.get_realized():
            shared_secret = config.parser.get("login", "shared_secret")
            steamguard = core.steamguard.main(shared_secret, self.time_offset)

            async for module_data in steamguard:
                self.main_window.set_status("steamguard", module_data)

    async def run_cardfarming(self) -> None:
        while self.main_window.get_realized():
            reverse_sorting = config.parser.getboolean("cardfarming", "reverse_sorting")
            wait_min = config.parser.getint("cardfarming", "wait_min")
            wait_max = config.parser.getint("cardfarming", "wait_max")

            self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
            cardfarming = core.cardfarming.main(self.steamid, reverse_sorting, (wait_min, wait_max))

            async for module_data in cardfarming:
                self.main_window.set_status("cardfarming", module_data)

    async def run_confirmations(self) -> None:
        old_confirmations: List[webapi.Confirmation] = []

        while self.main_window.get_realized():
            identity_secret = config.parser.get("login", "identity_secret")
            deviceid = config.parser.get("login", "deviceid")

            if not deviceid:
                log.warning(_("Unable to find deviceid. Generating from identity."))
                deviceid = universe.generate_device_id(identity_secret)
                config.new("login", "deviceid", deviceid)

            self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
            confirmations = core.confirmations.main(self.steamid, identity_secret, deviceid, self.time_offset)

            async for module_data in confirmations:
                self.main_window.set_warning(module_data)

                while self.main_window.text_tree_lock:
                    self.main_window.set_warning(_("Waiting another confirmation process"))
                    await asyncio.sleep(5)

                self.main_window.unset_warning()

                if module_data.action == "login":
                    await self.do_login(auto=True)
                    continue

                if module_data.action == "update":
                    if module_data.raw_data == old_confirmations:
                        log.warning(_("Skipping confirmations update because data doesn't seem to have changed"))
                        continue

                    self.main_window.text_tree.store.clear()

                    for confirmation_ in module_data.raw_data:
                        # translatable strings
                        t_give = utils.sanitize_confirmation(confirmation_.give)
                        t_receive = utils.sanitize_confirmation(confirmation_.receive)

                        iter_ = self.main_window.text_tree.store.append(None, [
                            confirmation_.mode,
                            str(confirmation_.id),
                            str(confirmation_.key),
                            t_give,
                            confirmation_.to,
                            t_receive,
                        ])

                        for item in itertools.zip_longest(confirmation_.give, confirmation_.receive):
                            self.main_window.text_tree.store.append(iter_, ['', '', '', item[0], '', item[1]])

                    old_confirmations = module_data.raw_data

    async def run_steamtrades(self) -> None:
        while self.main_window.get_realized():
            self.main_window.set_status("steamtrades", status=_("Loading"))
            trade_ids = config.parser.get("steamtrades", "trade_ids")
            wait_min = config.parser.getint("steamtrades", "wait_min")
            wait_max = config.parser.getint("steamtrades", "wait_max")

            if not trade_ids:
                self.main_window.set_status("steamtrades", error=_("No trade ID found"), info=_("Waiting Changes"))
                await asyncio.sleep(5)
                continue

            self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
            trades = [trade.strip() for trade in trade_ids.split(',')]
            steamtrades = core.steamtrades.main(trades, (wait_min, wait_max))

            async for module_data in steamtrades:
                self.main_window.set_status("steamtrades", module_data)

                if module_data.action == "login":
                    await self.do_login(auto=True)
                    continue

    async def run_steamgifts(self) -> None:
        while self.main_window.get_realized():
            self.main_window.set_status("steamgifts", status=_("Loading"))
            wait_min = config.parser.getint("steamgifts", "wait_min")
            wait_max = config.parser.getint("steamgifts", "wait_max")
            type_ = config.parser.get("steamgifts", "giveaway_type")
            pinned = config.parser.get("steamgifts", "developer_giveaways")
            sort = config.parser.get("steamgifts", "sort")
            reverse = config.parser.getboolean("steamgifts", "reverse_sorting")
            self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
            steamgifts = core.steamgifts.main(type_, pinned, sort, reverse, (wait_min, wait_max))

            async for module_data in steamgifts:
                self.main_window.set_status("steamgifts", module_data)

                if module_data.action == "login":
                    await self.do_login(auto=True)
                    continue

    def on_settings_activate(self, *args: Any) -> None:
        settings_dialog = settings.SettingsDialog(self.main_window, self)
        settings_dialog.show()

    def on_about_activate(self, *args: Any) -> None:
        dialog = about.AboutDialog(self.main_window)
        dialog.show()

    def on_exit_activate(self, *args: Any) -> None:
        loop = asyncio.get_running_loop()
        loop.stop()
        self.main_window.destroy()
