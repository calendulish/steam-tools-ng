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
from stlib import webapi

from . import about, settings, login, window, utils
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

        self._session = None
        self._webapi_session = None

        self._main_window_id = 0
        self.gtk_settings = Gtk.Settings.get_default()

        self.api_login: Optional[webapi.Login] = None
        self._time_offset = 0
        self.api_url = config.parser.get("steam", "api_url")
        self.api_key = config.parser.get("steam", "api_key")

        self.old_confirmations: List[webapi.Confirmation] = []

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

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.async_activate())
        task.add_done_callback(utils.safe_task_callback)

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_dialog = login.LoginDialog(self.main_window, self)
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
        self._session = aiohttp.ClientSession(raise_for_status=True, connector=tcp_connector)

        self._webapi_session = webapi.get_session(
            0,
            api_url=self.api_url,
            key=self.api_key,
            http_session=self._session
        )

        self._time_offset = await config.time_offset(self.webapi_session)

        self.main_window.set_warning(_("Logging on Steam. Please wait!"))
        log.info(_("Logging on Steam"))

        token = config.parser.get("login", "token")
        token_secure = config.parser.get("login", "token_secure")

        if not token or not token_secure or not self.steamid:
            await self.do_login()

        self.session.cookie_jar.update_cookies(config.login_cookies())  # type: ignore

        # noinspection PyShadowingNames
        try:
            if self.api_key and await self.webapi_session.is_logged_in(self.steamid):
                log.info("Steam login Successful")
            else:
                await self.do_login(auto=True)
        except aiohttp.ClientError as exception:
            log.exception(str(exception))
            self.main_window.set_critical(_("Check your connection. (server down?)"))
            await asyncio.sleep(10)
            return  # FIXME: RETRY ###

        self.main_window.unset_critical()
        self.main_window.unset_warning()

        modules: Dict = {}

        while self.main_window.get_realized():
            for module_name in config.plugins.keys():
                task = None

                if module_name in modules:
                    task = modules[module_name]

                if config.parser.getboolean("plugins", module_name):
                    if task:
                        if task.cancelled() and not task._exception:  # why task.exception() is raising?
                            log.debug(_("%s is requesting a reinitialization."), module_name)
                            modules.pop(module_name)

                        await asyncio.sleep(1)
                    else:
                        log.debug(_("%s is enabled but not initialized. Initializing now."), module_name)

                        module = getattr(self, f"run_{module_name}")

                        if module_name == "confirmations":
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
                        if module_name != "confirmations":
                            self.main_window.set_status(module_name, status=_("Disabled"))
                else:
                    await asyncio.sleep(1)

    @while_window_realized
    async def run_steamguard(self, play_event) -> None:
        await play_event.wait()
        steamguard = core.steamguard.main(self.time_offset)

        async for module_data in steamguard:
            self.main_window.set_status("steamguard", module_data)

    @while_window_realized
    async def run_cardfarming(self, play_event) -> None:
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        cardfarming = core.cardfarming.main(self.steamid)

        async for module_data in cardfarming:
            self.main_window.set_status("cardfarming", module_data)

            if module_data.action == "check":
                executor = module_data.raw_data
                assert isinstance(executor, client.SteamApiExecutor), "No SteamApiExecutor"

                if not play_event.is_set():
                    await executor.shutdown()
                    await play_event.wait()
                    executor.__init__(executor.game_id)
                    await executor.init()

    @while_window_realized
    async def run_confirmations(self) -> None:
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        confirmations = core.confirmations.main(self.steamid, self.time_offset)

        async for module_data in confirmations:
            if module_data.error:
                self.main_window.set_critical(module_data.error)
            else:
                self.main_window.unset_critical()

            if self.main_window.text_tree_lock:
                self.main_window.set_warning(_("Waiting another confirmation process"))
                while self.main_window.text_tree_lock: await asyncio.sleep(1)
                self.main_window.unset_warning()
                continue

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

            if module_data.action == "update":
                if module_data.raw_data == self.old_confirmations:
                    log.info(_("Skipping confirmations update because data doesn't seem to have changed"))
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

                self.old_confirmations = module_data.raw_data

    @while_window_realized
    async def run_steamtrades(self, play_event) -> None:
        await play_event.wait()
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        steamtrades = core.steamtrades.main()

        async for module_data in steamtrades:
            self.main_window.set_status("steamtrades", module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    @while_window_realized
    async def run_steamgifts(self, play_event) -> None:
        await play_event.wait()
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
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
