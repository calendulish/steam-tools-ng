#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2024
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
class SettingsWindow(utils.PopupWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
    ) -> None:
        super().__init__(parent_window, application)
        self.set_title(_('Settings'))

        stack = Gtk.Stack()
        stack.set_margin_end(10)
        self.content_grid.attach(stack, 1, 0, 1, 1)

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        self.content_grid.attach(sidebar, 0, 0, 1, 1)

        general_section = utils.Section("general")
        general_section.stackup_section(_("General"), stack)

        config_button = Gtk.Button()
        config_button.set_label(_("Config File Directory"))
        config_button.set_name("config_button")
        config_button.set_hexpand(True)
        config_button.connect("clicked", self.on_config_button_clicked)

        if config.parser.get("logger", "log_directory") == str(config.config_file_directory):
            config_button.set_label(_("Config / Log file Directory"))
            general_section.attach(config_button, 0, 1, 2, 1)
        else:
            buttons_grid = Gtk.Grid()
            buttons_grid.set_column_homogeneous(10)
            buttons_grid.set_column_spacing(10)

            log_button = Gtk.Button()
            log_button.set_label(_("Log File Directory"))
            log_button.set_name("log_button")
            log_button.connect("clicked", self.on_log_button_clicked)

            buttons_grid.attach(config_button, 0, 1, 1, 1)
            buttons_grid.attach(log_button, 1, 1, 1, 1)
            general_section.attach(buttons_grid, 0, 1, 2, 1)

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

    @staticmethod
    def on_log_button_clicked(button: Gtk.Button) -> None:
        call([config.file_manager, config.parser.get("logger", "log_directory")])

    @staticmethod
    def on_config_button_clicked(button: Gtk.Button) -> None:
        call([config.file_manager, str(config.config_file_directory)])

    def on_show_close_button_state_set(self, switch: Gtk.Switch, state: bool) -> None:
        if state:
            self.parent_window.set_deletable(True)
        else:
            self.parent_window.set_deletable(False)

        config.new('general', 'show_close_button', state)

    def on_theme_changed(self, dropdown: Gtk.DropDown, *args: Any) -> None:
        theme = list(config.gtk_themes)[dropdown.get_selected()]

        if theme == 'default':
            self.gtk_settings_class.reset_property("gtk-application-prefer-dark-theme")
            prefer_dark_theme = self.gtk_settings_class.get_property("gtk-application-prefer-dark-theme")
            theme = 'dark' if prefer_dark_theme else 'light'

        self.gtk_settings_class.props.gtk_application_prefer_dark_theme = (
            theme == 'dark'
        )
        config.new('general', 'theme', theme)

    def update_language(self, dropdown: Gtk.DropDown, *args: Any) -> None:
        language = list(config.translations)[dropdown.get_selected()]
        config.new('general', 'language', language)

        language_popup = utils.PopupWindowBase(self, self.application)
        language_popup.set_title(_("Language"))

        language_status = utils.SimpleStatus()
        language_status.info(_("You must restart the STNG to apply the new language"))

        language_popup.content_grid.attach(language_status, 0, 0, 1, 1)
        language_popup.present()
