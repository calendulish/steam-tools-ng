#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
import functools
import itertools
import logging
import ssl
import sys
from pathlib import Path
from typing import Any, Optional, Dict, Callable, List

import aiohttp
from gi.repository import Gio, Gtk

from stlib import universe, login, community, webapi, internals
from . import about, settings, window, utils
from . import login as gtk_login
from .. import config, i18n, core

_ = i18n.get_translation
log = logging.getLogger(__name__)

try:
    from stlib import client
except ImportError as exception:
    log.error(str(exception))
    client = None


def while_window_realized(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    async def wrapper(self, *args, **kwargs) -> None:
        while self.main_window.get_realized():
            await function(self, *args, **kwargs)

    return wrapper


# noinspection PyUnusedLocal
class SteamToolsNG(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="monster.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._main_window_id = 0
        self.gtk_settings = Gtk.Settings.get_default()

        self.api_login: Optional[login.Login] = None
        self.api_url = config.parser.get("steam", "api_url")
        self.api_key = config.parser.get("steam", "api_key")

        self.old_confirmations: List[community.Confirmation] = []

    @property
    def main_window(self) -> Optional[window.Main]:
        current_window = self.get_window_by_id(self._main_window_id)
        return self.get_window_by_id(self._main_window_id)

    @property
    def steamid(self) -> Optional[universe.SteamId]:
        steamid = config.parser.getint("login", "steamid")

        if steamid:
            return universe.generate_steamid(steamid)
        else:
            return None

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

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.async_activate())
        task.add_done_callback(utils.safe_task_callback)

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_dialog = gtk_login.LoginDialog(self.main_window, self)
        login_dialog.set_deletable(False)
        login_dialog.show()

        if auto:
            encrypted_password = config.parser.get("login", "password")
            try:
                login_dialog.set_password(encrypted_password)
                login_dialog.login_button.emit('clicked')
            except ValueError:
                log.error(_("Saved password is not usable"))

        if block:
            while self.main_window.get_realized():
                if login_dialog.has_user_data:
                    break

                await asyncio.sleep(1)

    async def async_activate(self) -> None:
        ssl_context = ssl.SSLContext()

        if hasattr(sys, 'frozen'):
            _executable_path = Path(sys.executable).parent
            ssl_context.load_verify_locations(cafile=_executable_path / 'etc' / 'cacert.pem')

        tcp_connector = aiohttp.TCPConnector(ssl=ssl_context)
        http_session = aiohttp.ClientSession(raise_for_status=True, connector=tcp_connector)
        login_session = await login.Login.new_session(0, api_url=self.api_url, http_session=http_session)
        community_session = await community.Community.new_session(0, api_url=self.api_url)
        webapi_session = await webapi.SteamWebAPI.new_session(0, api_key=self.api_key, api_url=self.api_url)
        internals_session = await internals.Internals.new_session(0)

        self.main_window.statusbar.set_warning("steamguard", _("Logging on Steam. Please wait!"))
        log.info(_("Logging on Steam"))

        token = config.parser.get("login", "token")
        token_secure = config.parser.get("login", "token_secure")

        if not token or not token_secure or not self.steamid:
            await self.do_login()

        login_session.restore_login(self.steamid, token, token_secure)

        try:
            if self.api_key and await login_session.is_logged_in(self.steamid):
                log.info("Steam login Successful")
            else:
                await self.do_login(auto=True)
        except aiohttp.ClientError as exception_:
            log.exception(str(exception_))
            self.main_window.statusbar.set_critical("steamguard", _("Check your connection. (server down?)"))
            await asyncio.sleep(10)
            return  # FIXME: RETRY ###

        self.main_window.statusbar.clear("steamguard")

        modules: Dict = {}

        while self.main_window.get_realized():
            for module_name in config.plugins.keys():
                task = None

                if module_name in modules:
                    task = modules[module_name]

                if config.parser.getboolean(module_name, "enable"):
                    if task:
                        if task.cancelled() and not task._exception:  # why task.exception() is raising?
                            log.debug(_("%s is requesting a reinitialization."), module_name)
                            modules.pop(module_name)

                        await asyncio.sleep(1)
                    else:
                        log.debug(_("%s is enabled but not initialized. Initializing now."), module_name)

                        module = getattr(self, f"run_{module_name}")

                        if module_name in ["confirmations", "coupons"]:
                            task = asyncio.create_task(module())
                        else:
                            self.main_window.set_status(module_name, status=_("Loading"))
                            play_event = self.main_window.get_play_event(module_name)
                            task = asyncio.create_task(module(play_event))

                        log.debug(_("Adding a new callback for %s"), task)
                        task.add_done_callback(utils.safe_task_callback)
                        modules[module_name] = task

                    continue

                if task and not task.cancelled():
                    log.debug(_("%s is disabled but not cancelled. Cancelling now."), module_name)
                    task.cancel()

                    try:
                        await task
                    except asyncio.CancelledError:
                        if module_name not in ["confirmations", "coupons"]:
                            self.main_window.set_status(module_name, status=_("Disabled"))
                else:
                    await asyncio.sleep(1)

    @while_window_realized
    async def run_steamguard(self, play_event) -> None:
        await play_event.wait()
        steamguard = core.steamguard.main()

        async for module_data in steamguard:
            self.main_window.set_status("steamguard", module_data)

    @while_window_realized
    async def run_cardfarming(self, play_event) -> None:
        cardfarming = core.cardfarming.main(self.steamid)

        async for module_data in cardfarming:
            self.main_window.set_status("cardfarming", module_data)

            if module_data.action == "check":
                executors = module_data.raw_data

                if not play_event.is_set():
                    for executor in executors:
                        await executor.shutdown()

                    await play_event.wait()

                    for executor in executors:
                        executor.__init__(executor.appid)
                        await executor.init()

    @while_window_realized
    async def run_confirmations(self) -> None:
        confirmations = core.confirmations.main(self.steamid)

        async for module_data in confirmations:
            if module_data.error:
                self.main_window.statusbar.set_critical('confirmations', module_data.error)
            else:
                self.main_window.statusbar.clear('confirmations')

            if self.main_window.confirmation_tree.lock:
                await self.main_window.confirmation_tree.wait_available()
                continue

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

            if module_data.action == "update":
                self.main_window.statusbar.set_warning("confirmations", "Updating now!")
                if module_data.raw_data == self.old_confirmations:
                    log.info(_("Skipping confirmations update because data doesn't seem to have changed"))
                    self.main_window.statusbar.clear('confirmations')
                    continue

                self.main_window.confirmation_tree.store.clear()

                for confirmation_ in module_data.raw_data:
                    # translatable strings
                    t_give = utils.sanitize_confirmation(confirmation_.give)
                    t_receive = utils.sanitize_confirmation(confirmation_.receive)

                    iter_ = self.main_window.confirmation_tree.store.append(None, [
                        str(confirmation_.confid),
                        str(confirmation_.creatorid),
                        str(confirmation_.key),
                        utils.markup(t_give),
                        utils.markup(confirmation_.to),
                        utils.markup(t_receive),
                    ])

                    for item in itertools.zip_longest(confirmation_.give, confirmation_.receive):
                        self.main_window.confirmation_tree.store.append(iter_, ['', '', '', item[0], '', item[1]])

                self.old_confirmations = module_data.raw_data
                self.main_window.statusbar.clear('confirmations')

    @while_window_realized
    async def run_coupons(self) -> None:
        coupons = core.coupons.main(self.main_window.fetch_coupon_event)

        async for module_data in coupons:
            if module_data.error:
                self.main_window.statusbar.set_critical("coupons", module_data.error)

            if module_data.info:
                self.main_window.statusbar.set_warning("coupons", module_data.info)

            if not any([module_data.info, module_data.error]):
                self.main_window.statusbar.clear("coupons")

            if module_data.action == "update":
                iter_ = self.main_window.coupon_tree.store.append([
                    str(module_data.raw_data['price']),
                    utils.markup(module_data.raw_data['name'], foreground='blue', underline='single'),
                    str(module_data.raw_data['assetid']),
                    module_data.raw_data['link'],
                ])

            if module_data.action == "clear":
                self.main_window.coupon_tree.store.clear()

            if module_data.action == "update_level":
                self.main_window.coupon_progress.set_value(module_data.raw_data[0])
                self.main_window.coupon_progress.set_max_value(module_data.raw_data[1])

    @while_window_realized
    async def run_steamtrades(self, play_event) -> None:
        await play_event.wait()
        steamtrades = core.steamtrades.main()

        async for module_data in steamtrades:
            self.main_window.set_status("steamtrades", module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    @while_window_realized
    async def run_steamgifts(self, play_event) -> None:
        await play_event.wait()
        steamgifts = core.steamgifts.main()

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
