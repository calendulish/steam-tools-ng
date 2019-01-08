#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2019
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
from collections import OrderedDict

import aiohttp
from gi.repository import Gtk, Pango
from stlib import webapi

from . import utils, setup, advanced
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation

gtk_themes = OrderedDict([
    ('light', _("Light")),
    ('dark', _("Dark")),
])

log_levels = OrderedDict([
    ('critical', _("Critical")),
    ('error', _("Error")),
    ('warning', _("Warning")),
    ('info', _("Info")),
    ('debug', _("Debug")),
])

translations = OrderedDict([
    ('en', _("English")),
    ('pt_BR', _("Portuguese (Brazil)")),
])

giveaway_types = OrderedDict([
    ('main', _("Main Giveaways")),
    ('new', _("New Giveaways")),
    ('recommended', _("Recommended")),
    ('wishlist', _("Wishlist Only")),
    ('group', _('Group Only')),
])

giveaway_sort_types = OrderedDict([
    ('name', _("Name")),
    ('copies', _("Copies")),
    ('points', _("Points")),
    ('level', _("Level")),
])


# noinspection PyUnusedLocal
class SettingsDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Widget,
            session: aiohttp.ClientSession,
            webapi_session: webapi.SteamWebAPI,
            time_offset: int,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.session = session
        self.webapi_session = webapi_session
        self.time_offset = time_offset

        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.gtk_settings_class = Gtk.Settings.get_default()

        content_area = self.get_content_area()
        content_grid = Gtk.Grid()
        content_grid.set_border_width(10)
        content_grid.set_row_spacing(10)
        content_grid.set_column_spacing(10)
        content_area.add(content_grid)

        login_section = utils.Section("login", _("Login Settings"))

        account_name = login_section.new('account_name', _("Username:"), Gtk.Entry, 0, 0)
        account_name.connect('changed', on_setting_changed)

        advanced_button = Gtk.ToggleButton(_("Advanced"))
        advanced_button.set_name("advanced_button")
        advanced_button.connect("toggled", self.on_advanced_button_toggled)
        login_section.grid.attach(advanced_button, 0, 7, 4, 1)

        setup_button = Gtk.Button(_("Magic Box"))
        setup_button.set_name("setup_button")
        setup_button.connect('clicked', self.on_setup_clicked)
        login_section.grid.attach(setup_button, 0, 8, 4, 1)

        reset_password_button = Gtk.Button(_("Reset Password"))
        reset_password_button.set_name("reset_password_button")
        reset_password_button.connect("clicked", self.on_reset_password_clicked)
        login_section.grid.attach(reset_password_button, 0, 10, 4, 1)

        login_section.show_all()

        plugins_section = utils.Section('plugins', _('Plugins Settings'))

        steamguard = plugins_section.new("steamguard", _("Authenticator:"), Gtk.CheckButton, 0, 1)
        steamguard.connect('toggled', on_setting_toggled)

        confirmations = plugins_section.new("confirmations", _("Confirmations:"), Gtk.CheckButton, 2, 1)
        confirmations.connect('toggled', on_setting_toggled)

        __disabled = plugins_section.new("___", "________", Gtk.CheckButton, 4, 1)
        __disabled.set_sensitive(False)
        __disabled.label.set_sensitive(False)

        steamtrades = plugins_section.new("steamtrades", _("Steamtrades:"), Gtk.CheckButton, 0, 2)
        steamtrades.connect('toggled', on_setting_toggled)

        steamgifts = plugins_section.new("steamgifts", _("Steamgifts:"), Gtk.CheckButton, 2, 2)
        steamgifts.connect('toggled', on_setting_toggled)

        cardfarming = plugins_section.new("cardfarming", _("Cardfarming:"), Gtk.CheckButton, 4, 2)
        cardfarming.connect("toggled", on_setting_toggled)

        plugins_section.show_all()

        gtk_section = utils.Section('gtk', _('Gtk Settings'))

        theme = gtk_section.new("theme", _("Theme:"), Gtk.ComboBoxText, 0, 0, items=gtk_themes)
        theme.connect('changed', self.on_theme_changed)

        show_close_button = gtk_section.new("show_close_button", _("Show close button:"), Gtk.CheckButton, 0, 1)
        show_close_button.connect('toggled', self.on_show_close_button_toggled)

        gtk_section.show_all()

        steamtrades_section = utils.Section('steamtrades', _('Steamtrades Settings'))

        trade_ids = steamtrades_section.new("trade_ids", _("Trade IDs:"), Gtk.Entry, 0, 0)
        trade_ids.set_placeholder_text('12345, asdfg, ...')
        trade_ids.connect("changed", on_setting_changed)

        wait_min = steamtrades_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 1)
        wait_min.connect("changed", on_digit_only_setting_changed)

        wait_max = steamtrades_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 2)
        wait_max.connect("changed", on_digit_only_setting_changed)

        steamtrades_section.show_all()

        steamgifts_section = utils.Section("steamgifts", _("Steamgifts Settings"))

        giveaway_type = steamgifts_section.new(
            "giveaway_type",
            _("Giveaway Type:"),
            Gtk.ComboBoxText,
            0, 0,
            items=giveaway_types,
        )
        giveaway_type.connect("changed", on_combo_setting_changed, giveaway_types)

        sort_giveaways = steamgifts_section.new(
            "sort",
            _("Sort Giveaways:"),
            Gtk.ComboBoxText,
            0, 1,
            items=giveaway_sort_types,
        )
        sort_giveaways.connect("changed", on_combo_setting_changed, giveaway_sort_types)

        reverse_sorting = steamgifts_section.new("reverse_sorting", _("Reverse Sorting:"), Gtk.CheckButton, 0, 2)
        reverse_sorting.connect("toggled", on_setting_toggled)

        developer_giveaways = steamgifts_section.new(
            "developer_giveaways",
            _("Developer Giveaways"),
            Gtk.CheckButton,
            0, 3,
        )
        developer_giveaways.connect("toggled", on_setting_toggled)

        wait_min = steamgifts_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 4)
        wait_min.connect("changed", on_digit_only_setting_changed)

        wait_max = steamgifts_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 5)
        wait_max.connect("changed", on_digit_only_setting_changed)

        steamgifts_section.show_all()

        cardfarming_section = utils.Section("cardfarming", _("Cardfarming settings"))

        wait_min = cardfarming_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 0)
        wait_min.connect("changed", on_digit_only_setting_changed)

        wait_max = cardfarming_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 1)
        wait_max.connect("changed", on_digit_only_setting_changed)

        reverse_sorting = cardfarming_section.new("reverse_sorting", _("More cards First:"), Gtk.CheckButton, 0, 2)

        cardfarming_section.show_all()

        locale_section = utils.Section("locale", _('Locale settings'))
        language_item = locale_section.new("language", _("Language"), Gtk.ComboBoxText, 0, 0, items=translations)
        language_item.connect("changed", self.update_language)

        locale_section.show_all()

        logger_section = utils.Section("logger", _('Logger settings'))

        log_level_item = logger_section.new("log_level", _("Level:"), Gtk.ComboBoxText, 0, 0, items=log_levels)

        log_console_level_item = logger_section.new(
            "log_console_level",
            _("Console level:"),
            Gtk.ComboBoxText,
            0, 1,
            items=log_levels,
        )

        log_level_item.connect("changed", on_combo_setting_changed, log_levels)
        log_console_level_item.connect("changed", on_combo_setting_changed, log_levels)

        logger_section.show_all()

        self.connect('response', lambda dialog, response_id: self.destroy())

        content_grid.attach(login_section, 0, 0, 1, 2)
        content_grid.attach(logger_section, 1, 0, 1, 1)
        content_grid.attach(gtk_section, 1, 1, 1, 1)

        content_grid.attach(steamtrades_section, 0, 2, 1, 1)
        content_grid.attach(cardfarming_section, 0, 3, 1, 1)
        content_grid.attach(steamgifts_section, 1, 2, 1, 2)

        content_grid.attach(locale_section, 0, 4, 1, 1)
        content_grid.attach(plugins_section, 1, 4, 1, 1)

        content_grid.show()
        self.show()

    def on_advanced_button_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            advanced_settings = advanced.AdvancedSettingsDialog(
                button,
                self,
                self.session,
                self.webapi_session,
                self.time_offset,
            )

            advanced_settings.show_all()

    def on_show_close_button_toggled(self, button: Gtk.Button) -> None:
        current_value = button.get_active()

        if current_value:
            self.parent_window.set_deletable(True)
        else:
            self.parent_window.set_deletable(False)

        config.new('gtk', 'show_close_button', current_value)

    def on_theme_changed(self, combo: Gtk.ComboBoxText) -> None:
        theme = list(gtk_themes)[combo.get_active()]

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new('gtk', 'theme', theme)

    def on_setup_clicked(self, button: Gtk.Button) -> None:
        setup_dialog = setup.SetupDialog(self, self.session, self.webapi_session, self.time_offset)
        setup_dialog.login_mode()
        setup_dialog.show()

    def on_reset_password_clicked(self, button: Gtk.Button) -> None:
        setup_dialog = setup.SetupDialog(self, self.session, self.webapi_session, self.time_offset)
        setup_dialog.show()
        setup_dialog.status.info(_("Reseting Password..."))
        setup_dialog.status.show()
        setup_dialog.header_bar.set_show_close_button(False)

        config.new("login", "password", "")

        setup_dialog.status.info(_("Done!"))
        asyncio.get_event_loop().call_later(2, setup_dialog.destroy)

    def update_language(self, combo: Gtk.ComboBoxText) -> None:
        language = list(translations)[combo.get_active()]
        config.new('locale', 'language', language)
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)


def on_setting_toggled(checkbutton: Gtk.CheckButton) -> None:
    current_value = checkbutton.get_active()
    section = checkbutton.get_section_name()
    option = checkbutton.get_name()

    config.new(section, option, current_value)


def on_setting_changed(entry: Gtk.Entry) -> None:
    current_value = entry.get_text()
    section = entry.get_section_name()
    option = entry.get_name()

    config.new(section, option, current_value)


def on_digit_only_setting_changed(entry: Gtk.Entry) -> None:
    current_value = entry.get_text()
    section = entry.get_section_name()
    option = entry.get_name()

    if current_value.isdigit():
        config.new(section, option, int(current_value))
    else:
        entry.set_text(utils.remove_letters(current_value))


def on_combo_setting_changed(combo: Gtk.ComboBoxText, items: 'OrderedDict[str, str]') -> None:
    current_value = list(items)[combo.get_active()]
    section = combo.get_section_name()
    option = combo.get_name()

    config.new(section, option, current_value)


def refresh_widget_text(widget: Gtk.Widget) -> None:
    if isinstance(widget, Gtk.MenuButton):
        if widget.get_use_popover():
            refresh_widget_text(widget.get_popover())
        else:
            refresh_widget_text(widget.get_popup())

        return

    if isinstance(widget, Gtk.Container):
        childrens = Gtk.Container.get_children(widget)
    else:
        if isinstance(widget, Gtk.Label):
            try:
                cached_text = i18n.cache[i18n.new_hash(widget.get_text())]
            except KeyError:
                log.debug("it's not an i18n string: %s", widget.get_text())
                return

            c_ = _

            if widget.get_use_markup():
                old_attributes = Pango.Layout.get_attributes(widget.get_layout())
                widget.set_text(c_(cached_text))
                widget.set_attributes(old_attributes)
            else:
                widget.set_text(c_(cached_text))

            log.debug('widget refreshed: %s', widget)
        else:
            log.debug('widget not refresh: %s', widget)

        return

    for children in childrens:
        refresh_widget_text(children)
