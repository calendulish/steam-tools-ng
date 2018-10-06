#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2018
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
import json
import logging
import random
from typing import Any, List, Optional, Dict

import aiohttp
import binascii
from gi.repository import Gio, Gtk
from stlib import authenticator, client, plugins, webapi

from . import about, settings, setup, window, utils
from .. import config, i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class Application(Gtk.Application):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.session = session
        self.api_url = config.get('steam', 'api_url')
        self.webapi_session = webapi.SteamWebAPI(session, self.api_url.value)

        self.window = None
        self.gtk_settings = Gtk.Settings.get_default()

        self.api_login: Optional[webapi.Login] = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        settings_action = Gio.SimpleAction.new('settings')
        settings_action.connect("activate", self.on_settings_activate)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about")
        about_action.connect("activate", self.on_about_activate)
        self.add_action(about_action)

        theme = config.get("gtk", "theme")

        if theme.value == 'dark':
            self.gtk_settings.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings.props.gtk_application_prefer_dark_theme = False

    def do_activate(self) -> None:
        if not self.window:
            self.window = window.Main(application=self)

        self.window.present()  # type: ignore

        asyncio.ensure_future(self.async_activate())

    @config.Check("login")
    async def async_activate(
            self,
            token: Optional[config.ConfigStr] = None,
            token_secure: Optional[config.ConfigStr] = None,
            steamid: config.ConfigInt = 0,
    ) -> None:
        setup_requested = False
        login_requested = False

        while True:
            token = config.get("login", "token")
            token_secure = config.get("login", "token_secure")
            steamid = config.getint("login", "steamid")
            nickname = config.get("login", "nickname")
            mobile_login = True if config.get("login", "oauth_token").value else False

            if not token.value or not token_secure.value or not steamid.value:
                if not setup_requested:
                    setup_dialog = setup.SetupDialog(self.window, self.session, self.webapi_session)
                    setup_dialog.login_mode()
                    setup_dialog.show()
                    setup_requested = True

                await asyncio.sleep(5)
                continue

            setup_requested = False

            if not nickname.value:
                try:
                    new_nickname = await self.webapi_session.get_nickname(steamid.value)
                except ValueError:
                    raise NotImplementedError
                else:
                    nickname = nickname._replace(value=config.ConfigStr(new_nickname))
                    config.new(nickname)

            self.session.cookie_jar.update_cookies(config.login_cookies())

            if not await self.webapi_session.is_logged_in(nickname.value):
                if not login_requested:
                    setup_dialog = setup.SetupDialog(self.window, self.session, self.webapi_session)

                    def __save_new_login_data(login_data: Dict[str, Any]):
                        new_configs = {}

                        if 'oauth' in login_data:
                            oauth_data = json.loads(login_data['oauth'])
                            new_configs.update({
                                'steamid': oauth_data['steamid'],
                                'token': oauth_data['wgtoken'],
                                'token_secure': oauth_data['wgtoken_secure'],
                                'oauth_token': oauth_data['oauth_token'],
                                'account_name': oauth_data['account_name'],
                            })
                        else:
                            raise NotImplementedError

                        config.new(*[
                            config.ConfigType("login", key, value) for key, value in new_configs.items()
                        ])

                        setup_dialog.destroy()

                    setup_dialog.prepare_login(__save_new_login_data, mobile_login)
                    setup_dialog.previous_button.hide()
                    setup_dialog.status.info(_("Could not connect to the Steam Servers.\nPlease, relogin."))
                    setup_dialog.status.show()
                    setup_dialog.show()
                    login_requested = True

                await asyncio.sleep(5)
                continue

            login_requested = False

            break

        asyncio.ensure_future(self.window.update_login_icons())
        asyncio.ensure_future(self.run_steamguard())
        asyncio.ensure_future(self.run_confirmations())
        asyncio.ensure_future(self.run_steamtrades())

    async def run_steamguard(self) -> None:
        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            if not self.window.plugin_switch("steamguard"):
                await asyncio.sleep(5)
                continue

            shared_secret = config.get("login", "shared_secret")

            try:
                if not shared_secret.value:
                    raise ValueError

                with client.SteamGameServer() as server:
                    server_time = server.get_server_time()

                auth_code = authenticator.get_code(server_time, shared_secret.value)
            except (ValueError, binascii.Error):
                self.window.steamguard_status.set_error(_("The currently secret is invalid"))
                await asyncio.sleep(10)
            except ProcessLookupError:
                self.window.steamguard_status.set_error(_("Steam Client is not running"))
                await asyncio.sleep(10)
            else:
                self.window.steamguard_status.set_error(_("Loading..."))

                seconds = 30 - (server_time % 30)

                for past_time in range(seconds * 9):
                    self.window.steamguard_status.set_current(auth_code)
                    self.window.steamguard_status.set_info(_("Running"))
                    self.window.steamguard_status.set_level(past_time, seconds * 8)

                    await asyncio.sleep(0.125)

    async def run_confirmations(self) -> None:
        old_confirmations: List[webapi.Confirmation] = []

        def warning(message: str) -> None:
            self.window.warning_label.set_markup(utils.markup(message, color='white', background='red'))
            self.window.warning_label.show()

        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            identity_secret = config.get("login", "identity_secret")
            steamid = config.getint("login", "steamid")
            deviceid = config.get("login", "deviceid")
            cookies = config.login_cookies()

            if not identity_secret.value:
                warning(_("Unable to get confirmations without a valid identity secret"))
                await asyncio.sleep(10)
                continue

            if not deviceid.value:
                log.debug(_("Unable to find deviceid. Generating from identity."))
                new_deviceid = authenticator.generate_device_id(identity_secret.value)
                deviceid = deviceid._replace(value=config.ConfigStr(new_deviceid))
                config.new(deviceid)

            if cookies:
                self.session.cookie_jar.update_cookies(cookies)
            else:
                warning(_("Unable to find a valid login data"))
                await asyncio.sleep(5)
                continue

            try:
                confirmations = await self.webapi_session.get_confirmations(
                    identity_secret.value,
                    steamid.value,
                    deviceid.value,
                )
            except AttributeError as exception:
                warning(_("Error when fetch confirmations"))
            except aiohttp.ClientConnectorError:
                warning(_("No connection"))
            except ProcessLookupError:
                warning(_("Steam is not running"))
            except webapi.LoginError:
                warning(_("User is not logged in"))
            else:
                self.window.warning_label.hide()
                if old_confirmations != confirmations:
                    self.window.text_tree.store.clear()

                    for confirmation_index, confirmation_ in enumerate(confirmations):
                        safe_give, give = utils.safe_confirmation_get(confirmation_, 'give')
                        safe_receive, receive = utils.safe_confirmation_get(confirmation_, 'receive')

                        iter_ = self.window.text_tree.store.append(None, [
                            confirmation_.mode,
                            str(confirmation_.id),
                            str(confirmation_.key),
                            safe_give,
                            confirmation_.to,
                            safe_receive,
                        ])

                        if len(give) > 1 or len(receive) > 1:
                            for item_index, item in enumerate(itertools.zip_longest(give, receive)):
                                self.window.text_tree.store.append(iter_, ['', '', '', item[0], '', item[1]])
                else:
                    log.debug(_("Skipping confirmations update because data doesn't seem to have changed"))

                old_confirmations = confirmations

            await asyncio.sleep(15)

    async def run_steamtrades(self) -> None:
        def error(message: str) -> None:
            self.window.steamtrades_status.set_current('_ _ _ _ _')
            self.window.steamtrades_status.set_error(message)

        def info(message: str, tradeid: str = '_ _ _ _ _') -> None:
            self.window.steamtrades_status.set_current(tradeid)
            self.window.steamtrades_status.set_info(message)

        if plugins.has_plugin("steamtrades"):
            steamtrades = plugins.get_plugin("steamtrades", self.session, api_url=self.api_url.value)
        else:
            error(_("Unable to find Steamtrades plugin"))
            return

        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            if not self.window.plugin_switch("steamtrades"):
                await asyncio.sleep(5)
                continue

            info(_("Loading"))
            trade_ids = config.get("steamtrades", "trade_ids")
            wait_min = config.getint("steamtrades", "wait_min")
            wait_max = config.getint("steamtrades", "wait_max")
            cookies = config.login_cookies()

            if not trade_ids.value:
                error(_("No trade ID found in config file"))
                await asyncio.sleep(5)
                continue

            if cookies:
                self.session.cookie_jar.update_cookies(cookies)
                try:
                    await steamtrades.do_login()
                except aiohttp.ClientConnectionError:
                    error(_("No connection"))
                    await asyncio.sleep(15)
                    continue
                except webapi.LoginError:
                    error(_("User is not logged in"))
                    await asyncio.sleep(15)
                    continue
            else:
                error(_("Unable to find a valid login data"))
                await asyncio.sleep(5)
                continue

            trades = [trade.strip() for trade in trade_ids.value.split(',')]
            bumped = False

            for trade_id in trades:
                try:
                    trade_info = await steamtrades.get_trade_info(trade_id)
                except (IndexError, aiohttp.ClientResponseError):
                    error(_("Unable to find TradeID {}").format(trade_id))
                    await asyncio.sleep(5)
                    continue
                except aiohttp.ClientConnectionError:
                    error(_("No connection"))
                    await asyncio.sleep(15)
                    continue

                try:
                    if await steamtrades.bump(trade_info):
                        info(_("Waiting anti-ban timer"))
                        await asyncio.sleep(random.randint(3, 8))
                        info(_("Bumped!"), trade_info.id)
                        bumped = True
                    else:
                        error(_("Unable to bump {}").format(trade_info.id))
                        await asyncio.sleep(5)
                        continue
                except plugins.steamtrades.NoTradesError as exception:
                    log.error(exception)
                    await asyncio.sleep(15)
                    continue
                except plugins.steamtrades.NotReadyError as exception:
                    wait_min = config.ConfigType('staemtrades', 'wait_min', config.ConfigInt(exception.time_left * 60))
                    wait_max = config.ConfigType('steamtrades', 'wait_max', config.ConfigInt(wait_min.value + 400))
                    bumped = True
                except plugins.steamtrades.ClosedError as exception:
                    self.error(str(exception))
                    await asyncio.sleep(5)
                    continue

            if not bumped:
                await asyncio.sleep(10)
                continue

            wait_offset = random.randint(wait_min.value, wait_max.value)
            log.debug(_("Setting wait_offset from steamtrades to %s"), wait_offset)
            for past_time in range(wait_offset):
                info(_("Waiting more {} minutes").format(round(wait_offset / 60)))

                try:
                    self.window.steamtrades_status.set_level(past_time, wait_offset)
                except KeyError:
                    self.window.steamtrades_status.set_level(0, 0)

                await asyncio.sleep(1)

    def on_settings_activate(self, action: Any, data: Any) -> None:
        settings_dialog = settings.SettingsDialog(self.window, self.session, self.webapi_session)
        settings_dialog.show()

    def on_about_activate(self, action: Any, data: Any) -> None:
        dialog = about.AboutDialog(self.window)
        dialog.show()
