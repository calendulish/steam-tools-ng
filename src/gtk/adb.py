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

from gi.repository import Gtk
from stlib import authenticator

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class AdbDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget) -> None:
        super().__init__(use_header_bar=True)
        self.adb_data = None

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 60)
        self.set_title("Android Debug Bridge")
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

        self.connect('response', self.on_response)

        self.try_again_button = Gtk.Button(_("Try again?"))
        self.try_again_button.connect("clicked", self.on_try_again_button_clicked)
        self.header_bar.pack_end(self.try_again_button)

        self.content_area.show_all()

        self.try_again_button.clicked()

    def on_try_again_button_clicked(self, button: Gtk.Button) -> None:
        self.try_again_button.hide()
        self.set_size_request(300, 60)
        self.status.info(_("Running... Please wait"))
        self.header_bar.set_show_close_button(False)
        task = asyncio.ensure_future(self.get_adb_data())
        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, future: asyncio.Future) -> None:
        if not self.adb_data:
            self.header_bar.set_show_close_button(True)
            self.try_again_button.show()

    @config.Check("login")
    async def get_adb_data(self, adb_path: Optional[config.ConfigStr] = None) -> None:
        if not adb_path:
            self.status.error(_(
                "Unable to run without a valid 'adb path'.\n\n"
                "To automatic get login data using adb, you will need:\n"
                "- A 'rooted' Android phone\n"
                "- adb tool from Google\n"
                "- adb path (set it on settings -> adb path)\n"
                "- USB debugging up and running (on phone)\n"
                "\nIt's a one-time config\n"
            ))
            return None

        try:
            adb = authenticator.AndroidDebugBridge(adb_path)
        except FileNotFoundError:
            self.status.error(_(
                "Unable to find adb in:\n\n{}\n\n"
                "Please, enter a valid 'adb path' and try again."
            ).format(adb_path))
            return None

        try:
            json_data = await adb.get_json(
                'shared_secret',
                'identity_secret',
                'account_name',
                'steamid',
            )
            assert isinstance(json_data, dict), "Invalid json_data"
            json_data['deviceid'] = await adb.get_device_id()
        except authenticator.DeviceError:
            self.status.error(_("No phone connected"))
            return None
        else:
            self.adb_data = json_data

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()
