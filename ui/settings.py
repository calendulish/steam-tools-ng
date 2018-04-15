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

from gi.repository import Gtk

from ui import config


class SettingsDialog(Gtk.Dialog):
    log_levels = ['critical', 'error', 'warning', 'info', 'debug']

    def __init__(self, parent_window):
        super().__init__(use_header_bar=True)
        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.add_button(_('Ok'), Gtk.ResponseType.OK)
        self.add_button(_('Cancel'), Gtk.ResponseType.CANCEL)

        content_area = self.get_content_area()
        content_area.set_orientation(Gtk.Orientation.VERTICAL)
        content_area.set_border_width(10)

        frame = Gtk.Frame(label=_('Logger settings'))
        frame.set_label_align(0.03, 0.5)
        content_area.pack_start(frame, False, False, 0)

        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        main_box.set_homogeneous(True)
        main_box.set_border_width(10)
        frame.add(main_box)

        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.set_homogeneous(True)
        box.set_spacing(3)
        main_box.pack_start(box, False, True, 0)

        label = Gtk.Label()
        label.set_text('Log level:')
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        label = Gtk.Label()
        label.set_text('Console log level:')
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.set_homogeneous(True)
        box.set_spacing(3)
        main_box.pack_start(box, False, True, 0)

        self.log_level_combo = Gtk.ComboBoxText()
        box.pack_start(self.log_level_combo, False, False, 0)

        self.log_console_level_combo = Gtk.ComboBoxText()
        box.pack_start(self.log_console_level_combo, False, False, 0)

        self.connect('response', self.on_response)

        self.load_logger_options()

        self.show_all()

    def on_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            self.save()

        dialog.destroy()

    def save(self):
        config.new(
            config.Config('logger', 'log_level', self.log_level_combo.get_active_text()),
            config.Config('logger', 'log_console_level', self.log_console_level_combo.get_active_text()),
        )

    @config.Check("logger")
    def load_logger_options(
            self,
            log_level: config.ConfigStr = 'debug',
            log_console_level: config.ConfigStr = 'info',
    ):
        for level in self.log_levels:
            self.log_level_combo.append_text(level)
            self.log_console_level_combo.append_text(level)

        self.log_level_combo.set_active(self.log_levels.index(log_level))
        self.log_console_level_combo.set_active(self.log_levels.index(log_console_level))
