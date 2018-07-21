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

import aiohttp
from gi.repository import Gtk

from . import adb, add_authenticator, login, utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class SetupDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, session: aiohttp.ClientSession) -> None:
        super().__init__(use_header_bar=True)
        self.session = session
        self.login_data = None

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 60)
        self.set_title(_('Setup'))
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

        self.combo = Gtk.ComboBoxText()
        self.content_area.add(self.combo)

        self.entry = Gtk.Entry()
        self.content_area.add(self.entry)

        self.connect('response', lambda dialog, response_id: self.destroy())

        self.content_area.show_all()
        self.header_bar.show_all()
        self.show()

    @staticmethod
    def __back(previous_button: Gtk.Button, next_button: Gtk.Button, callback) -> None:
        previous_button.destroy()
        next_button.destroy()
        callback()

    def select_login_mode(self):
        self.status.info(_(
            "Welcome to STNG Setup\n\n"
            "How do you want to log-in?"
        ))

        self.combo.get_model().clear()
        self.combo.append_text(_("Using Steam Tools NG as Steam Authenticator"))
        self.combo.append_text(_("Using a rooted Android phone and ADB"))
        self.combo.set_active(0)
        self.combo.show()

        next_button = Gtk.Button(_("Next"))
        next_button.connect("clicked", self.on_login_mode_selected)
        self.header_bar.pack_end(next_button)
        next_button.show()

        self.entry.hide()

        self.set_size_request(300, 60)

    def on_login_mode_selected(self, button: Gtk.Button) -> None:
        button.destroy()

        if self.combo.get_active() == 0:
            add_authenticator_dialog = add_authenticator.AddAuthenticator(self.parent_window, self.session)
            add_authenticator_dialog.do_login()
            self.hide()
            asyncio.ensure_future(self.wait_add_authenticator(add_authenticator_dialog))
        else:
            self.insert_adb_path()

    async def wait_add_authenticator(self, dialog: Gtk.Dialog) -> None:
        while not dialog.data:
            if dialog.get_realized():
                await asyncio.sleep(1)
            else:
                self.show()
                dialog.destroy()
                return

        dialog.destroy()

        self.status.info(_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ))

        oauth_data = json.loads(dialog.data['oauth'])

        revocation_code = utils.Status(6, _("Recovery Code"))
        revocation_code.set_current(oauth_data['revocation_code'])
        revocation_code.set_info('')
        self.content_area.add(revocation_code)

        revocation_code.show()
        self.show()

        max_value = 60 * 3
        for offset in range(max_value):
            revocation_code.set_level(offset, max_value)
            await asyncio.sleep(0.3)

        self.header_bar.set_show_close_button(True)

    def insert_adb_path(self):
        self.status.info(_(
            "To automatic get login data using adb, you will need:\n"
            "- A 'rooted' Android phone\n"
            "- adb tool from Google\n"
            "- adb path (set bellow)\n"
            "- USB debugging up and running (on phone)\n"
            "\nIt's a one-time config\n\n"
            "Please, write path where you adb is located. E.g:\n\n"
            "Windows: C:\platform-tools\\adb.exe\n"
            "Linux: /usr/bin/adb"
        ))

        self.combo.hide()
        self.entry.show()

        next_button = Gtk.Button(_("Next"))
        next_button.connect("clicked", self.on_adb_path_inserted)
        self.header_bar.pack_end(next_button)
        next_button.show()

        previous_button = Gtk.Button(_("Previous"))
        previous_button.connect("clicked", self.__back, next_button, self.select_login_mode)
        self.header_bar.pack_start(previous_button)
        previous_button.show()

        self.set_size_request(300, 60)

    def on_adb_path_inserted(self, button: Gtk.Button):
        if not self.entry.get_text():
            self.status.error(_("Unable to run without a valid adb path."))
            self.set_size_request(300, 60)
            return

        config.new(config.ConfigType("login", "adb_path", self.entry.get_text()))
        adb_dialog = adb.AdbDialog(parent_window=self.parent_window)
        adb_dialog.show()
        self.hide()

        asyncio.ensure_future(self.wait_adb_data(adb_dialog))

    async def wait_adb_data(self, adb_dialog: Gtk.Dialog) -> None:
        while not adb_dialog.adb_data:
            if adb_dialog.get_realized():
                await asyncio.sleep(1)
            else:
                self.show()
                adb_dialog.destroy()
                return

        adb_dialog.destroy()
        self.show()

        config.new(*[config.ConfigType("login", key, value) for key, value in adb_dialog.adb_data.items()])

        self.call_login_dialog()

    def call_login_dialog(self):
        login_dialog = login.LogInDialog(parent_window=self.parent_window, session=self.session)
        login_dialog.show()
        self.hide()

        asyncio.ensure_future(self.wait_login_data(login_dialog))

    async def wait_login_data(self, login_dialog: Gtk.Dialog) -> None:
        while not login_dialog.login_data:
            if login_dialog.get_realized():
                await asyncio.sleep(3)
            else:
                self.show()
                login_dialog.destroy()
                return

        config.new(*[config.ConfigType("login", key, value) for key, value in login_dialog.login_data.items()])
        login_dialog.destroy()

        self.show()
        self.finish()

    def finish(self):
        self.destroy()
