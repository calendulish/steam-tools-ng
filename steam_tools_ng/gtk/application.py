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
import random
from typing import Any

import aiohttp
from gi.repository import Gio, Gtk
from stlib import authenticator, steamtrades, webapi

from . import about, settings, window
from .. import config, i18n

_ = i18n.get_translation


# noinspection PyUnusedLocal
class Application(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.window: Gtk.ApplicationWindow = None
        self.authenticator_status = {'running': False, 'message': "Authenticator is not running"}
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

    def do_activate(self) -> None:
        if not self.window:
            self.window = window.Main(application=self)

        self.window.present()

        asyncio.ensure_future(self.run_authenticator())
        asyncio.ensure_future(self.run_confirmations())
        asyncio.ensure_future(self.run_steamtrades())

    async def run_authenticator(self) -> None:
        while self.window.get_realized():
            shared_secret = config.config_parser.get("authenticator", "shared_secret", fallback='')

            try:
                if not shared_secret:
                    raise TypeError

                auth_code, server_time = authenticator.get_code(shared_secret)
            except (TypeError, binascii.Error):
                self.authenticator_status = {'running': False, 'message': _("The currently secret is invalid")}
            except ProcessLookupError:
                self.authenticator_status = {'running': False, 'message': _("Steam Client is not running")}
            else:
                self.authenticator_status = {'running': False, 'message': _("Loading...")}

                seconds = 30 - (server_time % 30)

                for past_time in range(seconds * 9):
                    self.authenticator_status = {
                        'running': True,
                        'maximum': seconds * 8,
                        'progress': past_time,
                        'code': auth_code,
                    }

                    await asyncio.sleep(0.125)

    async def run_confirmations(self) -> None:
        while self.window.get_realized():
            identity_secret = config.config_parser.get("authenticator", "identity_secret", fallback='')
            steamid = config.config_parser.getint("authenticator", "steamid", fallback=None)
            deviceid = config.config_parser.get("authenticator", "deviceid", fallback='')
            cookies = config.login_cookies()

            if not cookies:
                self.confirmations_status = {
                    'running': False,
                    'message': "Unable to find a valid login data",
                }
                await asyncio.sleep(5)
                continue

            async with aiohttp.ClientSession(raise_for_status=True) as session:
                session.cookie_jar.update_cookies(cookies)
                http = webapi.Http(session, 'https://lara.click/api')
                confirmations = await http.get_confirmations(identity_secret, steamid, deviceid)

            self.confirmations_status = {'running': True, 'confirmations': confirmations}

            await asyncio.sleep(15)

    async def run_steamtrades(self) -> None:
        while self.window.get_realized():
            self.steamtrades_status = {'running': True, 'message': "Loading...", 'trade_id': ''}
            trade_ids = config.config_parser.get("steamtrades", "trade_ids", fallback='')
            wait_min = config.config_parser.getint("steamtrades", "wait_min", fallback=3700)
            wait_max = config.config_parser.getint("steamtrades", "wait_max", fallback=4100)
            cookies = config.login_cookies()

            if not trade_ids:
                self.steamtrades_status = {
                    'running': False,
                    'message': _("No trade ID found in config file"),
                    'trade_id': '',
                }
                await asyncio.sleep(5)
                continue

            if not cookies:
                self.steamtrades_status = {
                    'running': False,
                    'message': "Unable to find a valid login data",
                    'trade_id': '',
                }
                await asyncio.sleep(5)
                continue

            async with aiohttp.ClientSession(raise_for_status=True) as session:
                session.cookie_jar.update_cookies(cookies)

                http = webapi.Http(session, 'https://lara.click/api')
                await http.do_openid_login('https://steamtrades.com/?login')

                trades_http = steamtrades.Http(session)
                trades = [trade.strip() for trade in trade_ids.split(',')]

                for trade_id in trades:
                    try:
                        trade_info = await trades_http.get_trade_info(trade_id)
                    except (IndexError, aiohttp.ClientResponseError):
                        self.steamtrades_status = {
                            'running': False,
                            'message': f"Unable to find id {trade_id}",
                            'trade_id': trade_id,
                        }
                        continue

                    result = await trades_http.bump(trade_info)

                    if result['success']:
                        self.steamtrades_status = {
                            'running': True,
                            'message': 'Bumped!',
                            'trade_id': trade_info.id,
                        }
                        await asyncio.sleep(random.randint(1, 5))
                    elif result['reason'] == 'Not Ready':
                        self.steamtrades_status = {
                            'running': True,
                            'message': f"Waiting more {result['minutes_left']} minutes",
                            'trade_id': trade_info.id
                        }
                        wait_min = result['minutes_left'] * 60
                        wait_max = wait_min + 400
                    elif result['reason'] == 'trade is closed':
                        self.steamtrades_status = {
                            'running': False,
                            'message': 'trade is closed',
                            'trade_id': trade_info.id,
                        }
                        continue

                wait_offset = random.randint(wait_min, wait_max)
                for past_time in range(wait_offset):
                    await asyncio.sleep(1)

    def on_settings_activate(self, action: Any, data: Any) -> None:
        settings_dialog = settings.SettingsDialog(parent_window=self.window)
        settings_dialog.show()

    def on_about_activate(self, action: Any, data: Any) -> None:
        dialog = about.AboutDialog(parent_window=self.window)
        dialog.show()
