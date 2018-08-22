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
import binascii
import logging
import random
from typing import Any, List, Optional

import aiohttp
from gi.repository import Gio, Gtk
from stlib import authenticator, client, plugins, webapi

from . import about, login, settings, setup, window, utils
from .. import config, i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class Application(Gtk.Application):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.session = session
        self.webapi_session = webapi.SteamWebAPI(session, 'https://lara.click/api')

        self.window = None
        self.gtk_settings = Gtk.Settings.get_default()

        self.api_login: Optional[webapi.Login] = None

        self.steamguard_status = {'running': False, 'message': "SteamGuard is not running"}
        self.confirmations_status = {'running': False, 'message': "Confirmations is not running"}
        self.steamtrades_status = {'running': False, 'message': "Steamtrades is not running", 'trade_id': ''}

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        settings_action = Gio.SimpleAction.new('settings')
        settings_action.connect("activate", self.on_settings_activate)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about")
        about_action.connect("activate", self.on_about_activate)
        self.add_action(about_action)

        theme = config.config_parser.get("gtk", "theme", fallback="light")

        if theme == 'dark':
            self.gtk_settings.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings.props.gtk_application_prefer_dark_theme = False

    @config.Check("login")
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
            token = config.config_parser.get("login", "token", fallback='')
            token_secure = config.config_parser.get("login", "token_secure", fallback='')
            steamid = config.config_parser.getint("login", "steamid", fallback=0)
            nickname = config.config_parser.get("login", "nickname", fallback='')
            mobile_login = True if config.config_parser.get("login", "oauth_token", fallback='') else False

            if not token or not token_secure or not steamid:
                if not setup_requested:
                    setup_dialog = setup.SetupDialog(self.window, self.session, self.webapi_session)
                    setup_dialog.select_login_mode()
                    setup_requested = True

                await asyncio.sleep(5)
                continue

            setup_requested = False

            if not nickname:
                try:
                    nickname = await self.webapi_session.get_nickname(steamid)
                    config.new(config.ConfigType("login", "nickname", config.ConfigStr(nickname)))
                except ValueError:
                    raise NotImplementedError

            if not await self.webapi_session.is_logged_in(nickname):
                if not login_requested:
                    utils.async_wait_dialog(
                        login.LogInDialog,
                        self.login_dialog_callback,
                        self.window,
                        self.session,
                        self.webapi_session,
                        mobile_login,
                        True
                    )

                    login_requested = True

                await asyncio.sleep(5)
                continue

            login_requested = False

            break

        asyncio.ensure_future(self.run_steamguard())
        asyncio.ensure_future(self.run_confirmations())
        asyncio.ensure_future(self.run_steamtrades())

    async def run_steamguard(self) -> None:
        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            shared_secret = config.config_parser.get("login", "shared_secret", fallback='')

            try:
                if not shared_secret:
                    raise TypeError

                with client.SteamGameServer() as server:
                    server_time = server.get_server_time()

                auth_code = authenticator.get_code(server_time, shared_secret)
            except (TypeError, binascii.Error):
                self.steamguard_status = {'running': False, 'message': _("The currently secret is invalid")}
                await asyncio.sleep(10)
            except ProcessLookupError:
                self.steamguard_status = {'running': False, 'message': _("Steam Client is not running")}
                await asyncio.sleep(10)
            else:
                self.steamguard_status = {'running': False, 'message': _("Loading...")}

                seconds = 30 - (server_time % 30)

                for past_time in range(seconds * 9):
                    self.steamguard_status = {
                        'running': True,
                        'maximum': seconds * 8,
                        'progress': past_time,
                        'code': auth_code.code,
                    }

                    await asyncio.sleep(0.125)

    async def run_confirmations(self) -> None:
        old_confirmations: List[webapi.Confirmation] = []

        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            identity_secret = config.config_parser.get("login", "identity_secret", fallback='')
            steamid = config.config_parser.getint("login", "steamid", fallback=0)
            deviceid = config.config_parser.get("login", "deviceid", fallback='')
            cookies = config.login_cookies()

            if not identity_secret:
                self.confirmations_status = {
                    'running': False,
                    'message': _("Unable to get confirmations without a valid identity secret"),
                }
                await asyncio.sleep(10)
                continue

            if not deviceid:
                log.debug(_("Unable to find deviceid. Generating from identity."))
                deviceid = authenticator.generate_device_id(identity_secret)
                config.new(config.ConfigType("login", "deviceid", config.ConfigStr(deviceid)))

            if cookies:
                self.session.cookie_jar.update_cookies(cookies)
            else:
                self.confirmations_status = {
                    'running': False,
                    'message': _("Unable to find a valid login data"),
                }
                await asyncio.sleep(5)
                continue

            try:
                confirmations = await self.webapi_session.get_confirmations(identity_secret, steamid, deviceid)
            except AttributeError as exception:
                self.confirmations_status = {'running': False, 'message': _("Error when fetch confirmations")}
            except aiohttp.ClientConnectorError:
                self.confirmations_status = {'running': False, 'message': _("No connection")}
            except ProcessLookupError:
                self.confirmations_status = {'running': False, 'message': _("Steam is not running")}
            except webapi.LoginError:
                self.confirmations_status = {'running': False, 'message': _("User is not logged in")}
            else:
                if old_confirmations != confirmations:
                    self.confirmations_status = {'running': True, 'update': True, 'confirmations': confirmations}
                else:
                    self.confirmations_status = {'running': True, 'update': False, 'confirmations': confirmations}

                old_confirmations = confirmations

            await asyncio.sleep(15)

    async def run_steamtrades(self) -> None:
        steamtrades = plugins.get_plugin("steamtrades", self.session, api_url='https://lara.click/api')

        assert isinstance(self.window, Gtk.Window), "No window"

        while self.window.get_realized():
            self.steamtrades_status = {'running': True, 'message': "Loading...", 'trade_id': ''}
            trade_ids = config.config_parser.get("steamtrades", "trade_ids", fallback='')

            wait_min = config.config_parser.getint(
                "steamtrades",
                "wait_min",
                fallback=config.DefaultConfig.wait_min
            )

            wait_max = config.config_parser.getint(
                "steamtrades",
                "wait_max",
                fallback=config.DefaultConfig.wait_max
            )

            cookies = config.login_cookies()

            if not trade_ids:
                self.steamtrades_status = {
                    'running': False,
                    'message': _("No trade ID found in config file"),
                    'trade_id': '',
                }
                await asyncio.sleep(5)
                continue

            if cookies:
                self.session.cookie_jar.update_cookies(cookies)
                try:
                    await steamtrades.do_login()
                except aiohttp.ClientConnectionError:
                    self.steamtrades_status = {'running': False, 'message': _("No connection"), 'trade_id': ''}
                    await asyncio.sleep(15)
                    continue
                except webapi.LoginError:
                    self.steamtrades_status = {
                        'running': False,
                        'message': _("User is not logged in"),
                        'trade_id': ''
                    }
                    await asyncio.sleep(15)
                    continue
            else:
                self.steamtrades_status = {
                    'running': False,
                    'message': "Unable to find a valid login data",
                    'trade_id': '',
                }
                await asyncio.sleep(5)
                continue

            trades = [trade.strip() for trade in trade_ids.split(',')]
            bumped = False

            for trade_id in trades:
                try:
                    trade_info = await steamtrades.get_trade_info(trade_id)
                except (IndexError, aiohttp.ClientResponseError):
                    self.steamtrades_status = {
                        'running': False,
                        'message': f"Unable to find id {trade_id}",
                        'trade_id': trade_id,
                    }
                    await asyncio.sleep(5)
                    continue
                except aiohttp.ClientConnectionError:
                    self.steamtrades_status = {'running': False, 'message': _("No connection"), 'trade_id': ''}
                    await asyncio.sleep(15)
                    continue

                try:
                    if await steamtrades.bump(trade_info):
                        self.steamtrades_status = {
                            'running': True,
                            'message': _("Waiting anti-ban timer"),
                            'trade_id': ''
                        }

                        await asyncio.sleep(random.randint(3, 8))

                        self.steamtrades_status = {
                            'running': True,
                            'message': 'Bumped!',
                            'trade_id': trade_info.id,
                        }

                        bumped = True
                    else:
                        log.critical(f"Unable to bump {trade_info.id}")
                        await asyncio.sleep(5)
                        continue
                except plugins.steamtrades.NoTradesError as exception:
                    log.error(exception)
                    await asyncio.sleep(15)
                    continue
                except plugins.steamtrades.NotReadyError as exception:
                    wait_min = exception.time_left * 60
                    wait_max = wait_min + 400
                    bumped = True
                except plugins.steamtrades.ClosedError as exception:
                    self.steamtrades_status = {
                        'running': False,
                        'message': str(exception),
                        'trade_id': exception.id,
                    }
                    await asyncio.sleep(5)
                    continue

            if not bumped:
                await asyncio.sleep(10)
                continue

            wait_offset = random.randint(wait_min, wait_max)
            log.debug(_("Setting wait_offset from steamtrades to {}").format(wait_offset))
            for past_time in range(wait_offset):
                self.steamtrades_status = {
                    'running': True,
                    'message': f"Waiting more {round(wait_offset / 60)} minutes",
                    'trade_id': None,
                    'maximum': wait_offset,
                    'progress': past_time,
                }
                await asyncio.sleep(1)

    def on_settings_activate(self, action: Any, data: Any) -> None:
        settings_dialog = settings.SettingsDialog(self.window, self.session)
        settings_dialog.show()

    def on_about_activate(self, action: Any, data: Any) -> None:
        dialog = about.AboutDialog(self.window)
        dialog.show()

    async def login_dialog_callback(self, dialog: Gtk.Dialog) -> None:
        while not dialog.login_data:
            await asyncio.sleep(5)

        # FIXME: We can't known useful values without login_section
        settings_dialog = settings.SettingsDialog(self.window, self.session)
        settings.load_settings(settings_dialog.login_section, Gtk.Entry, data=dialog.login_data, save=True)

        dialog.destroy()
        settings_dialog.destroy()
