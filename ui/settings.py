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

        content_area = self.get_content_area()
        content_area.set_orientation(Gtk.Orientation.VERTICAL)
        content_area.set_border_width(10)
        content_area.set_spacing(10)

        content_area.pack_start(self.logger_settings(), False, False, 0)

        self.connect('response', self.on_response)
        self.show_all()

    def logger_settings(self):
        frame = Gtk.Frame(label=_('Logger settings'))
        frame.set_label_align(0.03, 0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        frame.add(grid)

        log_level_label = Gtk.Label("Level:")
        log_level_label.set_halign(Gtk.Align.START)
        grid.attach(log_level_label, 0, 0, 1, 1)

        log_level_combo = Gtk.ComboBoxText()
        log_level_combo.set_hexpand(True)
        log_level_combo.connect("changed", self.on_log_level_changed)
        grid.attach_next_to(log_level_combo, log_level_label, Gtk.PositionType.RIGHT, 1, 1)

        log_console_level_label = Gtk.Label("Console level:")
        log_console_level_label.set_halign(Gtk.Align.START)
        grid.attach(log_console_level_label, 0, 1, 1, 1)

        log_console_level_combo = Gtk.ComboBoxText()
        log_console_level_combo.set_hexpand(True)
        log_console_level_combo.connect("changed", self.on_log_console_level_changed)
        grid.attach_next_to(log_console_level_combo, log_console_level_label, Gtk.PositionType.RIGHT, 1, 1)

        self.load_logger_options(log_level_combo, log_console_level_combo)

        return frame

    @config.Check("logger")
    def load_logger_options(
            self,
            log_level_combo,
            log_console_level_combo,
            log_level: config.ConfigStr = 'debug',
            log_console_level: config.ConfigStr = 'info',
    ):
        for level in self.log_levels:
            log_level_combo.append_text(level)
            log_console_level_combo.append_text(level)

        log_level_combo.set_active(self.log_levels.index(log_level))
        log_console_level_combo.set_active(self.log_levels.index(log_console_level))

    @staticmethod
    def on_response(dialog, response_id):
        dialog.destroy()

    @staticmethod
    def on_log_level_changed(combo):
        config.new(config.Config('logger', 'log_level', combo.get_active_text()))

    @staticmethod
    def on_log_console_level_changed(combo):
        config.new(config.Config('logger', 'log_console_level', combo.get_active_text()))
