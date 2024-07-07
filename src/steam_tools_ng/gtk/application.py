#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2024
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
import contextlib
import functools
import itertools
import logging
from typing import Any, Dict, Callable, List

import aiohttp
from gi.repository import Gio, Gtk
from steam_tools_ng import __version__
from stlib import universe, login, community, webapi, internals, plugins

from . import about, settings, window, utils, update
from . import login as gtk_login
from .. import config, i18n, core

_ = i18n.get_translation
log = logging.getLogger(__name__)


def while_window_realized(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    async def wrapper(self: 'SteamToolsNG', *args: Any, **kwargs: Any) -> None:
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

        self.api_login: login.Login | None = None
        self.api_url = config.parser.get("steam", "api_url")

        self.old_confirmations: List[community.Confirmation] = []

    @property
    def main_window(self) -> window.Main | None:
        return self.get_window_by_id(self._main_window_id)

    @property
    def steamid(self) -> universe.SteamId | None:
        if steamid := config.parser.getint("login", "steamid"):
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

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
        exit_action.connect("activate", lambda *args: core.safe_exit())
        self.add_action(exit_action)

    def do_activate(self) -> None:
        if self._main_window_id != 0:
            self.main_window.present()
            return

        current_window = window.Main(application=self, title="Steam Tools NG")
        self.gtk_settings.props.gtk_application_prefer_dark_theme = current_window.theme == 'dark'
        self._main_window_id = current_window.get_id()
        current_window.present()

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.async_activate())
        task.add_done_callback(utils.safe_task_callback)

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_window = gtk_login.LoginWindow(self.main_window, self)
        login_window.set_deletable(False)
        login_window.present()

        if auto:
            encrypted_password = config.parser.get("login", "password")
            login_window.set_password(encrypted_password)
            login_window.login_button.emit('clicked')

        if block:
            while self.main_window.get_realized() and not login_window.has_user_data:
                await asyncio.sleep(1)

    async def async_activate(self) -> None:
        # TODO: Wait for window manager catch the main window position and size
        await asyncio.sleep(3)
        assert isinstance(self.main_window, window.Main)
        login_session = await login.Login.new_session(0, api_url=self.api_url)

        self.main_window.statusbar.set_warning("steamguard", _("Logging on Steam. Please wait!"))
        log.info(_("Logging on Steam"))

        if config.cookies_file.is_file():
            login_session.http_session.cookie_jar.load(config.cookies_file)

        try_count = 3

        for login_count in range(try_count):
            if await login_session.is_logged_in():
                log.info("Steam login Successful")
                config.update_steamid_from_cookies()
                break

            try:
                if login_count == 0:
                    await self.do_login(auto=True)
                else:
                    await self.do_login()
            except aiohttp.ClientError as error:
                log.exception(str(error))
                self.main_window.statusbar.set_critical(
                    "steamguard",
                    _("Check your connection. (server down?)"),
                )

                if login_count == 2:
                    return
                log.error(_("Waiting 10 seconds to try again"))
                await asyncio.sleep(10)

        self.main_window.statusbar.clear("steamguard")

        try:
            release_data = await login_session.request_json(
                "https://api.github.com/repos/calendulish/steam-tools-ng/releases/latest",
            )
            latest_version = release_data['tag_name'][1:]

            if latest_version > __version__:
                update_window = update.UpdateWindow(self.main_window, self, latest_version)
                update_window.present()
        except aiohttp.ClientError as error:
            log.exception(str(error))
            # bypass

        community_session = await community.Community.new_session(0, api_url=self.api_url)

        try:
            api_key = await community_session.get_api_key()
            log.debug(_('SteamAPI key found: %s'), api_key)

            if api_key[1] != 'Steam Tools NG':
                raise AttributeError
        except AttributeError:
            self.main_window.statusbar.set_warning('steamguard', _('Updating your SteamAPI dev key'))
            await asyncio.sleep(3)
            await community_session.revoke_api_key()
            await asyncio.sleep(3)
            api_key = await community_session.register_api_key('Steam Tools NG')
            self.main_window.statusbar.clear('steamguard')

            if not api_key:
                utils.fatal_error_dialog(ValueError(_('Something wrong with your SteamAPI dev key')), [])
        except PermissionError:
            log.error(_("Limited account! Using dummy API key"))
            self.main_window.limited_label.set_visible(True)
            api_key = (0, 'Steam Tools NG')

        webapi_session = await webapi.SteamWebAPI.new_session(0, api_key=api_key[0], api_url=self.api_url)
        internals_session = await internals.Internals.new_session(0)

        modules: Dict[str, asyncio.Task[Any]] = {}

        while self.main_window.get_realized():
            for module_name in config.plugins.keys():
                task = modules.get(module_name)

                if module_name == "confirmations":
                    enabled = config.parser.getboolean("steamguard", "enable_confirmations")
                else:
                    enabled = config.parser.getboolean(module_name, "enable")

                if enabled:
                    if task:
                        if task.cancelled() and not task._exception:  # why task.exception() is raising?
                            log.debug(_("%s is requesting a reinitialization."), module_name)
                            modules.pop(module_name)

                        await asyncio.sleep(1)
                    else:
                        log.debug(_("%s is enabled but not initialized. Initializing now."), module_name)
                        module = getattr(self, f"run_{module_name}")

                        if module_name in ["steamgifts", "steamtrades"]:
                            plugin = plugins.get_plugin(module_name)

                            with contextlib.suppress(IndexError):
                                await plugin.Main.new_session(0)

                        if module_name in ["coupons", "confirmations"]:
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
    async def run_steamguard(self, play_event: asyncio.Event) -> None:
        await play_event.wait()
        steamguard = core.steamguard.main()

        async for module_data in steamguard:
            self.main_window.set_status("steamguard", module_data)

    @while_window_realized
    async def run_cardfarming(self, play_event: asyncio.Event) -> None:
        assert isinstance(self.steamid, universe.SteamId)
        cardfarming = core.cardfarming.main(self.steamid, play_event)

        async for module_data in cardfarming:
            self.main_window.set_status("cardfarming", module_data)

            if module_data.action == "check":
                executors = module_data.raw_data

                if not play_event.is_set():
                    for executor in executors:
                        executor.shutdown()
                        # TODO: On Windows processes can't answer too fast due executor workaround
                        await asyncio.sleep(1)

                    await play_event.wait()

                    for executor in executors:
                        executor.__init__(executor.appid)

    @while_window_realized
    async def run_confirmations(self) -> None:
        wait_available = self.main_window.confirmations_tree.wait_available
        confirmations = core.confirmations.main(self.steamid, wait_available)

        async for module_data in confirmations:
            await wait_available()

            if module_data.error:
                self.main_window.statusbar.set_critical('confirmations', module_data.error)
            else:
                self.main_window.statusbar.clear('confirmations')

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

            if module_data.action == "update":
                self.main_window.statusbar.set_warning("confirmations", "Updating now!")
                if module_data.raw_data == self.old_confirmations:
                    log.debug(_("Skipping confirmations update because data doesn't seem to have changed"))
                    self.main_window.statusbar.clear('confirmations')
                    continue

                self.main_window.confirmations_tree.clear()

                for confirmation_ in module_data.raw_data:
                    # translatable strings
                    t_give = utils.sanitize_confirmation(confirmation_.give)
                    t_receive = utils.sanitize_confirmation(confirmation_.receive)

                    item = self.main_window.confirmations_tree.new_item(
                        str(confirmation_.id),
                        str(confirmation_.creatorid),
                        str(confirmation_.nonce),
                        utils.markup(t_give),
                        utils.markup(confirmation_.to),
                        utils.markup(t_receive),
                        '. '.join(confirmation_.summary),
                    )

                    for give, receive in itertools.zip_longest(confirmation_.give, confirmation_.receive):
                        child = self.main_window.confirmations_tree.new_item(
                            give=give or _("Nothing"),
                            to='-->',
                            receive=receive or _("Nothing"),
                        )

                        item.children.append(child)

                    self.main_window.confirmations_tree.append_row(item)

                self.old_confirmations = module_data.raw_data
                self.main_window.statusbar.clear('confirmations')

    @while_window_realized
    async def run_coupons(self) -> None:
        fetch_coupon_event = self.main_window.fetch_coupon_event
        wait_available = self.main_window.coupons_tree.wait_available
        coupons = core.coupons.main(self.steamid, fetch_coupon_event, wait_available)

        async for module_data in coupons:
            self.main_window.statusbar.clear("coupons")
            await wait_available()
            await fetch_coupon_event.wait()

            if module_data.error:
                self.main_window.statusbar.set_critical("coupons", module_data.error)

            if module_data.info:
                self.main_window.statusbar.set_warning("coupons", module_data.info)

            if not any([module_data.info, module_data.error]):
                self.main_window.statusbar.clear("coupons")

            if module_data.action == "update":
                item = self.main_window.coupons_tree.new_item(
                    f"{module_data.raw_data['price']:.2f}",
                    utils.markup(module_data.raw_data['name'], foreground='blue', underline='single'),
                    module_data.raw_data['link'],
                    module_data.raw_data['botid'],
                    module_data.raw_data['token'],
                    str(module_data.raw_data['assetid']),
                )

                self.main_window.coupons_tree.append_row(item)

            if module_data.action == "clear":
                self.main_window.coupons_tree.clear()

            if module_data.action == "update_level":
                self.main_window.coupon_progress.set_value(module_data.raw_data[0])
                self.main_window.coupon_progress.set_max_value(module_data.raw_data[1])

    @while_window_realized
    async def run_steamtrades(self, play_event: asyncio.Event) -> None:
        await play_event.wait()
        steamtrades = core.steamtrades.main()

        async for module_data in steamtrades:
            self.main_window.set_status("steamtrades", module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    @while_window_realized
    async def run_steamgifts(self, play_event: asyncio.Event) -> None:
        await play_event.wait()
        steamgifts = core.steamgifts.main()

        async for module_data in steamgifts:
            self.main_window.set_status("steamgifts", module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    def on_settings_activate(self, *args: Any) -> None:
        settings_window = settings.SettingsWindow(self.main_window, self)
        settings_window.present()

    def on_about_activate(self, *args: Any) -> None:
        about_dialog = about.AboutDialog(self.main_window)
        about_dialog.present()
