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
import logging
from typing import Dict

from gi.repository import Gtk
from stlib import authenticator

from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class AdbDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget) -> None:
        super().__init__(use_header_bar=True)
        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 90)
        self.set_title(_('Android Debug Bridge'))
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

        self.spinner.start()
        self.spinner.show()

        if len(config.config_parser.get("authenticator", "adb_path", fallback='')) < 3:
            self.new_error(_(
                "Unable to run without a valid adb path.\n"
                "Please, enter a valid 'adb path' and try again"
            ))

        self.connect('response', self.on_response)

    async def get_sensitive_data(self) -> Dict[str, str]:
        adb_path = config.config_parser.get("authenticator", "adb_path", fallback='')

        try:
            adb = authenticator.AndroidDebugBridge(adb_path)
        except FileNotFoundError:
            self.new_error(''.join(
                (
                    _("Unable to find adb in:\n"),
                    adb_path,
                    _("\nPlease, enter a valid 'adb path' and try again.")
                )
            ))
            raise FileNotFoundError

        try:
            json_data = await adb.get_json(
                'shared_secret',
                'identity_secret',
                'account_name',
                'steamid',
            )
            assert isinstance(json_data, dict), "Invalid json_data"
            json_data['deviceid'] = await adb.get_device_id()
        except (AttributeError, KeyError) as exception:
            self.new_error(repr(exception))
            raise AttributeError

        return json_data

    def new_error(self, text: str) -> None:
        self.spinner.hide()

        frame = Gtk.Frame(label=_("Error"))
        frame.set_label_align(0.03, 0.5)

        error_label = Gtk.Label(text)
        error_label.set_justify(Gtk.Justification.CENTER)
        error_label.set_vexpand(True)
        error_label.set_margin_top(10)
        error_label.set_margin_bottom(10)

        frame.add(error_label)

        self.header_bar.set_show_close_button(True)

        self.content_area.add(frame)

        frame.show_all()

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()
