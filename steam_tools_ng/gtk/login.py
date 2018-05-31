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
import logging
from typing import Optional

import aiohttp
from gi.repository import Gtk
from stlib import authenticator, webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class LogInDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget) -> None:
        super().__init__(use_header_bar=True)
        self.login_data = None

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(True)

        self.parent_window = parent_window
        self.set_default_size(300, 90)
        self.set_title(_('Log-in on Steam'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status_label = Gtk.Label()
        self.status_label.set_markup(utils.status_markup("info", _("Waiting")))
        self.content_area.add(self.status_label)

        self.spinner = Gtk.Spinner()
        self.spinner.set_vexpand(True)
        self.content_area.add(self.spinner)

        user_details_section = utils.new_section(_("User details"))
        self.content_area.add(user_details_section.frame)

        self.username_item = utils.new_item(_("Username:"), user_details_section, Gtk.Entry, 0, 0)
        self.password_item = utils.new_item(_("Password:"), user_details_section, Gtk.Entry, 0, 1)
        self.password_item.children.set_visibility(False)
        self.password_item.children.set_invisible_char('*')

        log_in_button = Gtk.Button(_("Log In"))
        log_in_button.connect("clicked", self.on_log_in_button_clicked)

        user_details_section.grid.attach_next_to(
            log_in_button,
            self.password_item.children,
            Gtk.PositionType.RIGHT,
            1,
            1,
        )

        self.content_area.show_all()

        self.connect('response', self.on_response)

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()

    def on_log_in_button_clicked(self, button: Gtk.Button) -> None:
        username = self.username_item.children.get_text()
        password = self.password_item.children.get_text()

        asyncio.ensure_future(self.do_login(username, password))

    @config.Check("authenticator")
    async def do_login(
            self,
            username: str,
            password: str,
            shared_secret: Optional[config.ConfigStr] = None
    ) -> None:
        if not shared_secret:
            self.status_label.set_markup(
                utils.status_markup("error", _("Unable to login!\nAuthenticator is not configured."))
            )
            return None

        if not username or not password:
            self.status_label.set_markup(
                utils.status_markup("error", _("Unable to log-in with a blank username/password"))
            )
            return None

        self.status_label.set_markup(utils.status_markup("info", _("Running")))
        self.spinner.start()

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            http = webapi.Http(session, 'https://lara.click/api')
            steam_key = await http.get_steam_key(username)
            encrypted_password = webapi.encrypt_password(steam_key, password.encode())
            authenticator_code, server_time = authenticator.get_code(shared_secret)

            steam_login_data = await http.do_login(
                username,
                encrypted_password,
                steam_key.timestamp,
                authenticator_code,
            )

            if steam_login_data['success']:
                self.login_data = steam_login_data
            else:
                self.status_label.set_markup(
                    utils.status_markup("error", "Unable to log-in on Steam!\nPlease, try again.")
                )
                self.spinner.stop()
                return None
