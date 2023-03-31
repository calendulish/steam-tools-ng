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
from gi.repository import Gtk, Pango
from subprocess import call
from typing import Type

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class SettingsDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.application = application

        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)

        self.gtk_settings_class = Gtk.Settings.get_default()

        content_area = self.get_content_area()
        content_grid = Gtk.Grid()
        content_grid.set_row_spacing(10)
        content_grid.set_column_spacing(10)
        content_area.append(content_grid)

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
            Gtk.ComboBoxText,
            0, 3,
            items=config.gtk_themes,
        )

        theme.connect('changed', self.on_theme_changed)

        language_item = general_section.new_item(
            "language", _("Language"), Gtk.ComboBoxText, 0, 4, items=config.translations
        )
        language_item.connect("changed", self.update_language)

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
            Gtk.ComboBoxText,
            0, 0,
            items=config.log_levels,
        )

        log_console_level_item = logger_section.new_item(
            "log_console_level",
            _("Console level:"),
            Gtk.ComboBoxText,
            0, 1,
            items=config.log_levels,
        )

        log_level_item.connect("changed", utils.on_combo_setting_changed, config.log_levels)
        log_console_level_item.connect("changed", utils.on_combo_setting_changed, config.log_levels)

        log_color = logger_section.new_item("log_color", _("Log color:"), Gtk.Switch, 0, 2)
        log_color.set_halign(Gtk.Align.END)
        log_color.connect('state-set', utils.on_setting_state_set)

        self.connect('response', lambda dialog, response_id: self.destroy())

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

    def on_theme_changed(self, combo: Gtk.ComboBoxText) -> None:
        theme = list(config.gtk_themes)[combo.get_active()]

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new('general', 'theme', theme)

    def update_language(self, combo: Gtk.ComboBoxText) -> None:
        language = list(config.translations)[combo.get_active()]
        config.new('general', 'language', language)
        refresh_widget_childrens(self)
        refresh_widget_childrens(self.parent_window)


def refresh_widget_childrens(widget: Type[Gtk.Widget]) -> None:
    next_child = widget.get_first_child()

    while next_child:
        refresh_widget(next_child)
        next_child = next_child.get_next_sibling()


def refresh_widget(widget: Type[Gtk.Widget]) -> None:
    if isinstance(widget, Gtk.MenuButton):
        refresh_widget(widget.get_popover())
        return

    if isinstance(widget, Gtk.ComboBoxText):
        model = widget.get_model()

        for index, row in enumerate(model):
            combo_item_label = model.get_value(row.iter, 0)

            try:
                cached_text = i18n.cache[i18n.new_hash(combo_item_label)]
            except KeyError:
                log.debug("it's not an i18n string: %s", combo_item_label)
                return

            model.set_value(row.iter, 0, _(cached_text))

        log.debug('ComboBox refreshed: %s', widget)

    if isinstance(widget, Gtk.Label):
        try:
            cached_text = i18n.cache[i18n.new_hash(widget.get_text())]
        except KeyError:
            log.debug("it's not an i18n string: %s", widget.get_text())
            return

        if widget.get_use_markup():
            old_attributes = Pango.Layout.get_attributes(widget.get_layout())
            widget.set_text(_(cached_text))
            widget.set_attributes(old_attributes)
        else:
            widget.set_text(_(cached_text))

        log.debug('widget refreshed: %s', str(widget))
        return

    log.debug('widget not refresh: %s', str(widget))
    refresh_widget_childrens(widget)
