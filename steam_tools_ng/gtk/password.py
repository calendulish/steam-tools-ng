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

import aiohttp
from gi.repository import Gtk
from stlib import webapi

from . import utils
from .. import i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class PasswordDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, username: str) -> None:
        super().__init__(use_header_bar=True)
        self.username = username
        self.encrypted_password = None

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(True)

        self.parent_window = parent_window
        self.set_default_size(300, 90)
        self.set_title(_('Password Encrypt'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.spinner = Gtk.Spinner()
        self.spinner.set_vexpand(True)
        self.content_area.add(self.spinner)

        password_section = utils.new_section("Password")
        self.content_area.add(password_section.frame)

        self.password_item = utils.new_item("Write your password:", password_section, Gtk.Entry, 0, 0)
        self.password_item.children.set_visibility(False)
        self.password_item.children.set_invisible_char('*')

        encrypt_button = Gtk.Button(_("Encrypt"))
        encrypt_button.connect("clicked", self.on_encrypt_button_clicked)
        password_section.grid.attach_next_to(encrypt_button, self.password_item.children, Gtk.PositionType.RIGHT, 1, 1)

        self.content_area.show_all()

        self.connect('response', self.on_response)

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()

    def on_encrypt_button_clicked(self, button: Gtk.Button) -> None:
        password = self.password_item.children.get_text()

        asyncio.ensure_future(self.do_encrypt(password))

    async def do_encrypt(self, password: str):
        self.spinner.start()

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            http = webapi.Http(session, 'https://lara.click/api')
            public_key = await http.get_public_key(self.username)

        encrypted_password = webapi.encrypt_password(public_key[0], password.encode())
        self.encrypted_password = encrypted_password.decode()
