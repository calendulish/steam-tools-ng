#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
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
from subprocess import call
from typing import Any

from gi.repository import Gtk

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class SettingsWindow(Gtk.Window):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
    ) -> None:
        super().__init__()
        self.parent_window = parent_window
        self.application = application

        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)

        self.gtk_settings_class = Gtk.Settings.get_default()

        content_grid = Gtk.Grid()
        content_grid.set_row_spacing(10)
        content_grid.set_column_spacing(10)
        self.set_child(content_grid)

        stack = Gtk.Stack()
        stack.set_margin_end(10)
        content_grid.attach(stack, 1, 0, 1, 1)

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        content_grid.attach(sidebar, 0, 0, 1, 1)

        general_section = utils.Section("general")
        general_section.stackup_section(_("General"), stack)

        config_button = Gtk.Button()
        config_button.set_label(_("Config File Directory"))
        config_button.set_name("config_button")
        config_button.set_hexpand(True)
        config_button.connect("clicked", self.on_config_button_clicked)

        if config.parser.get("logger", "log_directory") == str(config.config_file_directory):
            config_button.set_label(_("Config / Log file Directory"))
            general_section.grid.attach(config_button, 0, 1, 2, 1)
        else:
            log_button = Gtk.Button()
            log_button.set_label(_("Log File Directory"))
            log_button.set_name("log_button")
            log_button.connect("clicked", self.on_log_button_clicked)
            general_section.grid.attach(config_button, 0, 1, 1, 1)
            general_section.grid.attach(log_button, 1, 1, 1, 1)

        theme = general_section.new_item(
            "theme",
            _("Theme:"),
            Gtk.DropDown,
            0, 3,
            items=config.gtk_themes,
        )

        theme.connect('notify::selected', self.on_theme_changed)

        language_item = general_section.new_item(
            "language", _("Language"), Gtk.DropDown, 0, 4, items=config.translations
        )
        language_item.connect("notify::selected", self.update_language)

        show_close_button = general_section.new_item(
            "show_close_button",
            _("Show close button:"),
            Gtk.Switch,
            0, 5,
        )
        show_close_button.set_halign(Gtk.Align.END)

        show_close_button.connect('state-set', self.on_show_close_button_state_set)

        logger_section = utils.Section("logger")
        logger_section.stackup_section(_("Logger"), stack)

        log_level_item = logger_section.new_item(
            "log_level",
            _("Level:"),
            Gtk.DropDown,
            0, 0,
            items=config.log_levels,
        )

        log_console_level_item = logger_section.new_item(
            "log_console_level",
            _("Console level:"),
            Gtk.DropDown,
            0, 1,
            items=config.log_levels,
        )

        log_level_item.connect("notify::selected", utils.on_dropdown_setting_changed, config.log_levels)
        log_console_level_item.connect("notify::selected", utils.on_dropdown_setting_changed, config.log_levels)

        log_color = logger_section.new_item("log_color", _("Log color:"), Gtk.Switch, 0, 2)
        log_color.set_halign(Gtk.Align.END)
        log_color.connect('state-set', utils.on_setting_state_set)

        self.connect('destroy', lambda *args: self.destroy())
        self.connect('close-request', lambda *args: self.destroy())

    @staticmethod
    def on_log_button_clicked(button: Gtk.Button) -> None:
        call(f'{config.file_manager} {config.parser.get("logger", "log_directory")}')

    @staticmethod
    def on_config_button_clicked(button: Gtk.Button) -> None:
        call(f'{config.file_manager} {str(config.config_file_directory)}')

    def on_show_close_button_state_set(self, switch: Gtk.Switch, state: bool) -> None:
        if state:
            self.parent_window.set_deletable(True)
        else:
            self.parent_window.set_deletable(False)

        config.new('general', 'show_close_button', state)

    def on_theme_changed(self, dropdown: Gtk.DropDown, *args: Any) -> None:
        theme = list(config.gtk_themes)[dropdown.get_selected()]

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new('general', 'theme', theme)

    def update_language(self, dropdown: Gtk.DropDown, *args: Any) -> None:
        language = list(config.translations)[dropdown.get_selected()]
        config.new('general', 'language', language)
