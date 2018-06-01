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

from gi.repository import Gtk

from . import utils
from .. import i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class FinalizeDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, data: str) -> None:
        super().__init__(use_header_bar=True)
        self.data = data

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(True)

        self.parent_window = parent_window
        self.set_default_size(300, 90)
        self.set_title(_('Finalize Confirmation'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status_section = utils.new_section(_("Status"))
        self.content_area.add(self.status_section.frame)

        self.status_label = Gtk.Label()
        self.status_label.set_markup(utils.markup(_("Waiting"), color='green'))
        self.status_section.grid.attach(self.status_label, 0, 0, 1, 1)

        self.info_label = Gtk.Label()
        markup = "{} {}\n{} {}\n{} {}\n\n{} {}".format(
            _("Trade with"),
            utils.markup(self.data[4], color='blue'),
            _("You will give"),
            utils.markup(self.data[3], color='blue'),
            _("and receives"),
            utils.markup(self.data[5], color='blue'),
            _("You really want to do that?"),
            utils.markup(_("It can't be undone!"), color='red'),
        )

        self.info_label.set_markup(markup)
        self.info_label.set_justify(Gtk.Justification.CENTER)
        self.content_area.add(self.info_label)

        self.accept_button = Gtk.Button(_("Accept"))
        self.accept_button.connect("clicked", self.on_accept_button_clicked)
        self.content_area.add(self.accept_button)

        self.cancel_button = Gtk.Button(_("Cancel"))
        self.cancel_button.connect("clicked", self.on_cancel_button_clicked)
        self.content_area.add(self.cancel_button)

        self.content_area.show_all()

        self.connect('response', self.on_response)

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()

    def on_accept_button_clicked(self, button: Gtk.Button) -> None:
        raise NotImplementedError

    def on_cancel_button_clicked(self, button: Gtk.Button) -> None:
        raise NotImplementedError
