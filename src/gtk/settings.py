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
import sys
from collections import OrderedDict
from typing import Any, Dict, Optional

import aiohttp
from gi.repository import Gtk, Pango
from stlib import webapi

from . import utils, setup
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
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.session = session
        self.webapi_session = webapi_session

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

        content_grid.attach(self.login_settings(), 0, 0, 1, 2)
        content_grid.attach(self.logger_settings(), 1, 0, 1, 1)
        content_grid.attach(self.locale_settings(), 1, 1, 1, 1)

        content_grid.attach(self.steamtrades_settings(), 0, 2, 1, 1)
        content_grid.attach(self.steamgifts_settings(), 1, 2, 1, 1)

        content_grid.attach(self.gtk_settings(), 0, 3, 1, 1)
        content_grid.attach(self.plugins_settings(), 1, 3, 1, 1)

        content_grid.show()

        self.connect('response', lambda dialog, response_id: self.destroy())
        self.show()

    def login_settings(self) -> utils.Section:
        login_section = utils.Section("login", _("Login Settings"))

        account_name = login_section.new('account_name', _("Username:"), Gtk.Entry, 0, 0)
        account_name.connect('changed', on_account_name_changed)

        login_section.show_all()

        shared_secret = login_section.new('shared_secret', _("Shared Secret:"), Gtk.Entry, 0, 1)
        shared_secret.connect('changed', on_shared_secret_changed)

        token_item = login_section.new("token", _("Token:"), Gtk.Entry, 0, 2)
        token_item.connect("changed", on_token_changed)

        token_secure_item = login_section.new("token_secure", _("Token Secure:"), Gtk.Entry, 0, 3)
        token_secure_item.connect("changed", on_token_secure_changed)

        identity_secret = login_section.new('identity_secret', _("Identity Secret:"), Gtk.Entry, 2, 0)
        identity_secret.connect('changed', on_identity_secret_changed)

        deviceid = login_section.new('deviceid', _("Device ID:"), Gtk.Entry, 2, 1)
        deviceid.connect('changed', on_device_id_changed)

        steamid_item = login_section.new("steamid", _("Steam ID:"), Gtk.Entry, 2, 2)
        steamid_item.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.connect("changed", on_steamid_changed)

        advanced = Gtk.CheckButton(_("Advanced"))
        advanced.set_name("advanced_button")
        advanced.connect("toggled", self.on_advanced_button_toggled, login_section)
        login_section.grid.attach(advanced, 0, 7, 1, 1)
        advanced.show()

        load_settings(login_section, Gtk.Entry)

        setup_button = Gtk.Button(_("Magic Box"))
        setup_button.set_name("setup_button")
        setup_button.connect('clicked', self.on_setup_clicked)
        login_section.grid.attach(setup_button, 0, 8, 4, 1)
        setup_button.show()

        return login_section

    def on_advanced_button_toggled(self, button: Gtk.Button, login_section: utils.Section) -> None:
        if button.get_active():
            login_section.grid.show_all()
            login_section.set_label_align(0.017, 0.5)
        else:
            childrens = Gtk.Container.get_children(login_section.grid)
            keep_list = ['account_name', 'advanced_button', 'setup_button']

            for children in childrens:
                if children.get_name() in keep_list:
                    children.show()
                else:
                    children.hide()

            self.set_size_request(300, 150)
            login_section.set_label_align(0.03, 0.5)

    def plugins_settings(self) -> utils.Section:
        plugins_section = utils.Section('plugins', _('Plugins Settings'))

        steamguard = plugins_section.new("steamguard", _("SteamGuard:"), Gtk.CheckButton, 0, 1)
        steamguard.connect('toggled', on_steamguard_plugin_toggled)

        steamtrades = plugins_section.new("steamtrades", _("Steamtrades:"), Gtk.CheckButton, 0, 2)
        steamtrades.connect('toggled', on_steamtrades_plugin_toggled)

        steamgifts = plugins_section.new("steamgifts", _("Steamgifts:"), Gtk.CheckButton, 2, 1)
        steamgifts.connect('toggled', on_steamgifts_plugin_toggled)

        load_settings(plugins_section, Gtk.CheckButton)

        plugins_section.show_all()
        return plugins_section

    def gtk_settings(self) -> utils.Section:
        gtk_section = utils.Section('gtk', _('Gtk Settings'))

        theme = gtk_section.new("theme", _("Theme:"), Gtk.ComboBoxText, 0, 0)
        theme.connect('changed', self.on_theme_changed)

        load_settings(gtk_section, Gtk.ComboBoxText, combo_items=gtk_themes)

        gtk_section.show_all()
        return gtk_section

    def on_theme_changed(self, combo: Gtk.ComboBoxText) -> None:
        theme = list(gtk_themes)[combo.get_active()]

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new('gtk', 'theme', theme)

    @staticmethod
    def steamtrades_settings() -> utils.Section:
        steamtrades_section = utils.Section('steamtrades', _('Steamtrades Settings'))

        trade_ids = steamtrades_section.new("trade_ids", _("Trade IDs:"), Gtk.Entry, 0, 0)
        trade_ids.set_placeholder_text('12345, asdfg, ...')
        trade_ids.connect("changed", on_trade_ids_changed)

        wait_min = steamtrades_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 1)
        wait_min.connect("changed", save_digit_only, "steamtrades", "wait_min")

        wait_max = steamtrades_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 2)
        wait_max.connect("changed", save_digit_only, "steamtrades", "wait_max")

        load_settings(steamtrades_section, Gtk.Entry)

        steamtrades_section.show_all()
        return steamtrades_section

    def steamgifts_settings(self) -> utils.Section:
        steamgifts_section = utils.Section("steamgifts", _("Steamgifts Settings"))

        giveaway_type = steamgifts_section.new("giveaway_type", _("Giveaway Type:"), Gtk.ComboBoxText, 0, 0)
        giveaway_type.connect("changed", on_giveaway_type_changed)

        load_setting(giveaway_type, "steamgifts", combo_items=giveaway_types)

        sort_giveaways = steamgifts_section.new("sort", _("Sort Giveaways:"), Gtk.ComboBoxText, 0, 1)
        sort_giveaways.connect("changed", on_sort_giveaways_changed)

        load_setting(sort_giveaways, "steamgifts", combo_items=giveaway_sort_types)

        developer_giveaways = steamgifts_section.new(
            "developer_giveaways",
            _("Developer Giveaways"),
            Gtk.CheckButton,
            0, 2,
        )
        developer_giveaways.connect("toggled", on_developer_giveaways_toggled)

        load_setting(developer_giveaways, "steamgifts")

        wait_min = steamgifts_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 3)
        wait_min.connect("changed", save_digit_only, "steamgifts", "wait_min")

        wait_max = steamgifts_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 4)
        wait_max.connect("changed", save_digit_only, "steamgifts", "wait_max")

        load_settings(steamgifts_section, Gtk.Entry)

        steamgifts_section.show_all()
        return steamgifts_section

    def locale_settings(self) -> utils.Section:
        locale_section = utils.Section("locale", _('Locale settings'))
        language_item = locale_section.new("language", _("Language"), Gtk.ComboBoxText, 0, 0)

        load_settings(locale_section, Gtk.ComboBoxText, combo_items=translations)
        language_item.connect("changed", self.update_language)

        locale_section.show_all()
        return locale_section

    def logger_settings(self) -> utils.Section:
        logger_section = utils.Section("logger", _('Logger settings'))
        log_level_item = logger_section.new("log_level", _("Level:"), Gtk.ComboBoxText, 0, 0)

        log_console_level_item = logger_section.new(
            "log_console_level",
            _("Console level:"),
            Gtk.ComboBoxText,
            0, 1,
        )

        load_settings(logger_section, Gtk.ComboBoxText, combo_items=log_levels)

        log_level_item.connect("changed", on_log_level_changed)
        log_console_level_item.connect("changed", on_log_console_level_changed)

        logger_section.show_all()
        return logger_section

    def on_setup_clicked(self, button: Gtk.Button) -> None:
        setup_dialog = setup.SetupDialog(self, self.session, self.webapi_session)
        setup_dialog.login_mode()
        setup_dialog.show()

    def update_language(self, combo: Gtk.ComboBoxText) -> None:
        language = list(translations)[combo.get_active()]
        config.new('locale', 'language', language)
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)


def on_developer_giveaways_toggled(checkbutton: Gtk.CheckButton) -> None:
    activate = checkbutton.get_active()
    config.new("steamgifts", "developer_giveaways", activate)


def on_steamguard_plugin_toggled(checkbutton: Gtk.CheckButton) -> None:
    activate = checkbutton.get_active()
    config.new('plugins', 'steamguard', activate)


def on_steamid_changed(entry: Gtk.Entry) -> None:
    text = entry.get_text()

    if text.isdigit():
        config.new('login', 'steamid', text)
    else:
        entry.set_text(utils.remove_letters(text))


def on_token_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'token', entry.get_text())


def on_token_secure_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'token_secure', entry.get_text())


def on_shared_secret_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'shared_secret', entry.get_text())


def on_identity_secret_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'identity_secret', entry.get_text())


def on_account_name_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'account_name', entry.get_text())


def on_device_id_changed(entry: Gtk.Entry) -> None:
    config.new('login', 'deviceid', entry.get_text())


def on_sort_giveaways_changed(combo: Gtk.ComboBoxText) -> None:
    sort_giveaways = list(giveaway_sort_types)[combo.get_active()]
    config.new('steamgifts', 'sort', sort_giveaways)


def on_log_level_changed(combo: Gtk.ComboBoxText) -> None:
    log_level = list(log_levels)[combo.get_active()]
    config.new('logger', 'log_level', log_level)


def on_log_console_level_changed(combo: Gtk.ComboBoxText) -> None:
    log_console_level = list(log_levels)[combo.get_active()]
    config.new('logger', 'log_console_level', log_console_level)


def on_steamtrades_plugin_toggled(checkbutton: Gtk.CheckButton) -> None:
    activate = checkbutton.get_active()
    config.new('plugins', 'steamtrades', activate)


def on_trade_ids_changed(entry: Gtk.Entry) -> None:
    config.new('steamtrades', 'trade_ids', entry.get_text())


def save_digit_only(entry: Gtk.Entry, section: str, option: str) -> None:
    text = entry.get_text()

    if text.isdigit():
        config.new(section, option, int(text))
    else:
        entry.set_text(utils.remove_letters(text))


def on_steamgifts_plugin_toggled(checkbutton: Gtk.CheckButton) -> None:
    activate = checkbutton.get_active()
    config.new('plugins', 'steamgifts', activate)


def on_giveaway_type_changed(combo: Gtk.ComboBoxText) -> None:
    current_type = list(giveaway_types)[combo.get_active()]
    config.new('steamgifts', 'giveaway_type', current_type)


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


def load_setting(
        widget: Gtk.Widget,
        config_section: str,
        combo_items: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        save: bool = False,
) -> None:
    config_option = widget.get_name()

    if combo_items:
        for value in combo_items.values():
            widget.append_text(value)

    if data:
        try:
            config_value = data[config_option]
        except KeyError:
            log.debug(
                _("Unable to find %s in prefilled data. Ignoring."),
                config_option,
            )
            return None
    else:
        # FIXME: Type can be wrong
        config_value = config.parser.get(config_section, config_option)

        if not config_value:
            return None

    if isinstance(widget, Gtk.ComboBox):
        assert isinstance(combo_items, dict), "No combo_items"

        try:
            widget.set_active(list(combo_items).index(config_value))
        except ValueError:
            error_message = _("Please, fix your config file. Accepted values for {} are:\n{}").format(
                config_option,
                ', '.join(combo_items.keys()),
            )
            utils.fatal_error_dialog(error_message)
            sys.exit(1)
    elif isinstance(widget, Gtk.CheckButton):
        if isinstance(config_value, bool):
            widget.set_active(config_value)
        else:
            # FIXME: Type can be wrong
            widget.set_active(True if config_value == 'True' else False)
    else:
        widget.set_text(str(config_value))

    if save:
        config.new(config_section, config_option, config_value)


def load_settings(
        section: utils.Section,
        children_type: Gtk.Widget,
        combo_items: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        save: bool = False,
) -> None:
    childrens = Gtk.Container.get_children(section.grid)
    config_section = section.get_name()

    for children in childrens:
        if isinstance(children, children_type):
            load_setting(children, config_section, combo_items, data, save)
