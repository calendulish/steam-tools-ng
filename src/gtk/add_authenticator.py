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
import json
import logging
from typing import Any, Dict

import aiohttp
from gi.repository import Gtk
from stlib import authenticator, webapi

from . import login, utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class AddAuthenticator(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, session: aiohttp.ClientSession) -> None:
        super().__init__(use_header_bar=True)
        self.session = session
        self.data: Dict[str, Any] = {}

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 60)
        self.set_title(_("Add Authenticator"))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status = utils.SimpleStatus()
        self.content_area.add(self.status)

        self.code = Gtk.Entry()
        self.content_area.add(self.code)

        self.connect('response', lambda button: self.destroy())

        self.content_area.show_all()
        self.header_bar.show_all()
        self.show()

        self.steam_webapi = webapi.SteamWebAPI(self.session, 'https://lara.click/api')

    def do_login(self) -> None:
        self.code.hide()

        login_dialog = login.LogInDialog(self.parent_window, self.session, True)
        login_dialog.show()
        self.hide()

        # noinspection PyTypeChecker
        asyncio.ensure_future(self.wait_login_data(login_dialog))

    async def wait_login_data(self, login_dialog: Gtk.Dialog) -> None:
        while not login_dialog.login_data:
            if login_dialog.get_realized():
                await asyncio.sleep(1)
            else:
                login_dialog.destroy()
                self.destroy()
                return

        login_dialog.destroy()

        self.set_size_request(300, 60)
        self.show()
        self.status.info(_("Loading data..."))

        if not login_dialog.login_data['has_phone']:
            raise NotImplementedError

        await self.on_add_authenticator(login_dialog.login_data)

    async def on_add_authenticator(self, login_data: Dict[str, Any]) -> None:
        self.set_size_request(300, 60)
        self.status.info(_("Waiting Steam Server..."))
        oauth_data = json.loads(login_data['oauth'])
        deviceid = authenticator.generate_device_id(token=oauth_data['oauth_token'])

        auth_data = await self.steam_webapi.add_authenticator(
            oauth_data['steamid'],
            deviceid,
            oauth_data['oauth_token'],
        )

        if auth_data['status'] != 1:
            raise NotImplementedError

        self.status.info(_("Write code received by SMS\nand click on 'Add Authenticator' button"))
        self.code.show()

        add_authenticator_button = Gtk.Button(_("Add Authenticator"))

        add_authenticator_button.connect(
            "clicked",
            utils.safe_callback,
            self.on_finalize_add_authenticator,
            login_data,
            auth_data,
            deviceid,
        )

        self.header_bar.pack_end(add_authenticator_button)
        add_authenticator_button.show()

    async def on_finalize_add_authenticator(
            self,
            login_data: Dict[str, Any],
            auth_data: Dict[str, Any],
            deviceid: str,
    ) -> None:
        self.code.hide()
        self.status.info(_("Waiting Steam Server..."))

        authenticator_code = authenticator.get_code(int(auth_data['server_time']), auth_data['shared_secret'])
        oauth_data = json.loads(login_data['oauth'])

        try:
            complete = await self.steam_webapi.finalize_add_authenticator(
                oauth_data['steamid'],
                oauth_data['oauth_token'],
                authenticator_code.code,
                self.code.get_text(),
            )
        except webapi.SMSCodeError:
            self.status.info(_("Invalid SMS Code. Please,\ncheck the code and try again."))
            self.code.show()

            try_again = Gtk.Button(_("Try Again?"))

            try_again.connect(
                "clicked",
                utils.safe_callback,
                self.on_finalize_add_authenticator,
                login_data,
                auth_data,
                deviceid,
            )

            self.header_bar.pack_end(try_again)
            try_again.show()

            return

        if complete:
            self.status.info(_("Success! Saving..."))

            new_configs = {
                'steamid': oauth_data['steamid'],
                'deviceid': deviceid,
                'token': oauth_data['wgtoken'],
                'token_secure': oauth_data['wgtoken_secure'],
                'oauth_token': oauth_data['oauth_token'],
                'account_name': oauth_data['account_name'],
                'shared_secret': auth_data['shared_secret'],
                'identity_secret': auth_data['identity_secret'],
            }

            config.new(*[
                config.ConfigType("login", key, value) for key, value in new_configs.items()
            ])

            self.data = {**login_data, **auth_data}
        else:
            self.status.error(_("Unable to add a new authenticator"))
            self.header_bar.set_show_close_button(True)
