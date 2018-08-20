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
import configparser
import logging
from collections import OrderedDict
from typing import Any, Dict, Optional

import aiohttp
from gi.repository import Gtk, Pango

from . import adb, login, utils
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


# noinspection PyUnusedLocal
class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, session: aiohttp.ClientSession) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.session = session

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

        content_grid.attach(self.login_settings(), 0, 0, 1, 3)
        content_grid.attach(self.logger_settings(), 1, 0, 1, 2)
        content_grid.attach(self.locale_settings(), 1, 2, 1, 1)
        content_grid.attach(self.gtk_settings(), 2, 0, 1, 1)
        content_grid.attach(self.steamtrades_settings(), 2, 1, 1, 2)

        content_grid.show()

        self.connect('response', lambda dialog, response_id: self.destroy())
        self.show()

    def login_settings(self) -> Gtk.Frame:
        login_section = utils.new_section("login", _("Login Settings"))
        login_section.grid.set_row_spacing(5)

        adb_path = utils.new_item('adb_path', _("Adb Path:"), login_section, Gtk.Entry, 0, 0)
        adb_path.children.set_placeholder_text('E.g.: c:\\adb.exe or /opt/adb')
        adb_path.children.connect('changed', on_adb_path_changed)

        account_name = utils.new_item('account_name', _("Username:"), login_section, Gtk.Entry, 0, 2)
        account_name.children.connect('changed', on_account_name_changed)

        shared_secret = utils.new_item('shared_secret', _("Shared Secret:"), login_section, Gtk.Entry, 0, 4)
        shared_secret.children.connect('changed', on_shared_secret_changed)

        login_section.frame.show_all()

        token_item = utils.new_item("token", _("Token:"), login_section, Gtk.Entry, 0, 6)
        token_item.children.connect("changed", on_token_changed)

        token_secure_item = utils.new_item("token_secure", _("Token Secure:"), login_section, Gtk.Entry, 2, 0)
        token_secure_item.children.connect("changed", on_token_secure_changed)

        identity_secret = utils.new_item('identity_secret', _("Identity Secret:"), login_section, Gtk.Entry, 2, 2)
        identity_secret.children.connect('changed', on_identity_secret_changed)

        deviceid = utils.new_item('deviceid', _("Device ID:"), login_section, Gtk.Entry, 2, 4)
        deviceid.children.connect('changed', on_device_id_changed)

        steamid_item = utils.new_item("steamid", _("Steam ID:"), login_section, Gtk.Entry, 2, 6)
        steamid_item.children.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.children.connect("changed", on_steamid_changed)

        advanced = Gtk.CheckButton(_("Advanced"))
        advanced.set_name("advanced_button")
        advanced.connect("toggled", self.on_advanced_button_toggled, login_section)
        login_section.grid.attach(advanced, 0, 7, 1, 1)
        advanced.show()

        load_settings(login_section, Gtk.Entry)

        log_in = Gtk.Button(_("Log-in"))
        log_in.set_name("log_in_button")
        log_in.connect('clicked', self.on_log_in_clicked, login_section)
        login_section.grid.attach(log_in, 0, 8, 4, 1)
        log_in.show()

        adb_button = Gtk.Button(_("Get login data using ADB"))
        adb_button.set_name("adb_button")
        adb_button.connect('clicked', self.on_adb_clicked, login_section)
        login_section.grid.attach(adb_button, 0, 9, 4, 1)
        adb_button.show()

        return login_section.frame

    def on_advanced_button_toggled(self, button: Gtk.Button, section: utils.Section) -> None:
        if button.get_active():
            section.grid.show_all()
            section.frame.set_label_align(0.017, 0.5)
        else:
            childrens = Gtk.Container.get_children(section.grid)
            keep_list = ['adb_path', 'account_name', 'shared_secret', 'advanced_button', 'log_in_button', 'adb_button']

            for children in childrens:
                if children.get_name() in keep_list:
                    children.show()
                else:
                    children.hide()

            self.set_size_request(300, 150)
            section.frame.set_label_align(0.03, 0.5)

    def gtk_settings(self) -> Gtk.Frame:
        gtk_section = utils.new_section('gtk', _('Gtk Settings'))

        theme = utils.new_item("theme", _("Theme:"), gtk_section, Gtk.ComboBoxText, 0, 0)
        theme.children.connect('changed', self.on_theme_changed)

        load_settings(gtk_section, Gtk.ComboBoxText, combo_items=gtk_themes)

        gtk_section.frame.show_all()
        return gtk_section.frame

    def on_theme_changed(self, combo: Gtk.ComboBoxText) -> None:
        theme = config.ConfigStr(list(gtk_themes)[combo.get_active()])

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new(config.ConfigType('gtk', 'theme', theme))

    @staticmethod
    def steamtrades_settings() -> Gtk.Frame:
        steamtrades_section = utils.new_section('steamtrades', _('Steamtrades Settings'))

        trade_ids = utils.new_item("trade_ids", _("Trade IDs:"), steamtrades_section, Gtk.Entry, 0, 0)
        trade_ids.children.set_placeholder_text('12345, asdfg, ...')
        trade_ids.children.connect("changed", on_trade_ids_changed)

        wait_min = utils.new_item("wait_min", _("Wait MIN:"), steamtrades_section, Gtk.Entry, 0, 1)
        wait_min.children.connect("changed", on_wait_min_changed)

        wait_max = utils.new_item("wait_max", _("Wait MAX:"), steamtrades_section, Gtk.Entry, 0, 2)
        wait_max.children.connect("changed", on_wait_max_changed)

        load_settings(steamtrades_section, Gtk.Entry)

        steamtrades_section.frame.show_all()
        return steamtrades_section.frame

    def locale_settings(self) -> Gtk.Frame:
        locale_section = utils.new_section("locale", _('Locale settings'))
        language_item = utils.new_item("language", _("Language"), locale_section, Gtk.ComboBoxText, 0, 0)

        load_settings(locale_section, Gtk.ComboBoxText, combo_items=translations)
        language_item.children.connect("changed", self.update_language)

        locale_section.frame.show_all()
        return locale_section.frame

    def logger_settings(self) -> Gtk.Frame:
        logger_section = utils.new_section("logger", _('Logger settings'))
        log_level_item = utils.new_item("log_level", _("Level:"), logger_section, Gtk.ComboBoxText, 0, 0)

        log_console_level_item = utils.new_item(
            "log_console_level",
            _("Console level:"),
            logger_section,
            Gtk.ComboBoxText,
            0, 1,
        )

        load_settings(logger_section, Gtk.ComboBoxText, combo_items=log_levels)

        log_level_item.children.connect("changed", on_log_level_changed)
        log_console_level_item.children.connect("changed", on_log_console_level_changed)

        logger_section.frame.show_all()
        return logger_section.frame

    def on_adb_clicked(self, button: Gtk.Button, login_section: utils.Section) -> None:
        adb_dialog = adb.AdbDialog(self)
        adb_dialog.show()

        # noinspection PyTypeChecker
        asyncio.ensure_future(wait_adb_data(adb_dialog, login_section))

    def on_log_in_clicked(
            self,
            button: Gtk.Button,
            login_section: utils.Section,
    ) -> None:
        login_dialog = login.LogInDialog(self, session=self.session)
        login_dialog.show()

        # noinspection PyTypeChecker
        asyncio.ensure_future(wait_login_data(login_dialog, login_section))

    def update_language(self, combo: Gtk.ComboBoxText) -> None:
        language = config.ConfigStr(list(translations)[combo.get_active()])
        config.new(config.ConfigType('locale', 'language', language))
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)


async def wait_adb_data(
        adb_dialog: Gtk.Dialog,
        login_section: utils.Section,
) -> None:
    while not adb_dialog.adb_data:
        await asyncio.sleep(5)

    load_settings(login_section, Gtk.Entry, data=adb_dialog.adb_data, save=True)

    adb_dialog.destroy()


async def wait_login_data(
        login_dialog: Gtk.Dialog,
        login_section: utils.Section,
) -> None:
    while not login_dialog.login_data:
        await asyncio.sleep(5)

    load_settings(login_section, Gtk.Entry, data=login_dialog.login_data, save=True)

    login_dialog.destroy()


def on_steamid_changed(entry: Gtk.Entry) -> None:
    text = entry.get_text()

    if text.isdigit():
        config.new(config.ConfigType('login', 'steamid', text))
    else:
        entry.set_text(utils.remove_letters(text))


def on_token_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'token', entry.get_text()))


def on_token_secure_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'token_secure', entry.get_text()))


def on_adb_path_changed(entry: Gtk.Entry) -> None:
    if len(entry.get_text()) > 2:
        config.new(config.ConfigType('login', 'adb_path', entry.get_text()))


def on_shared_secret_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'shared_secret', entry.get_text()))


def on_identity_secret_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'identity_secret', entry.get_text()))


def on_account_name_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'account_name', entry.get_text()))


def on_device_id_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('login', 'deviceid', entry.get_text()))


def on_log_level_changed(combo: Gtk.ComboBoxText) -> None:
    log_level = config.ConfigStr(list(log_levels)[combo.get_active()])
    config.new(config.ConfigType('logger', 'log_level', log_level))


def on_log_console_level_changed(combo: Gtk.ComboBoxText) -> None:
    log_console_level = config.ConfigStr(list(log_levels)[combo.get_active()])
    config.new(config.ConfigType('logger', 'log_console_level', log_console_level))


def on_trade_ids_changed(entry: Gtk.Entry) -> None:
    config.new(config.ConfigType('steamtrades', 'trade_ids', entry.get_text()))


def on_wait_min_changed(entry: Gtk.Entry) -> None:
    text = entry.get_text()

    if text.isdigit():
        config.new(config.ConfigType('steamtrades', 'wait_min', text))
    else:
        entry.set_text(utils.remove_letters(text))


def on_wait_max_changed(entry: Gtk.Entry) -> None:
    text = entry.get_text()

    if text.isdigit():
        config.new(config.ConfigType('steamtrades', 'wait_max', text))
    else:
        entry.set_text(utils.remove_letters(text))


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


def load_settings(
        section: utils.Section,
        children_type: Gtk.Widget,
        combo_items: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        save: bool = False,
) -> None:
    childrens = Gtk.Container.get_children(section.grid)
    config_section = section.frame.get_name()

    for children in childrens:
        if isinstance(children, children_type):
            config_option = children.get_name()

            if combo_items:
                for value in combo_items.values():
                    children.append_text(value)

            if data:
                try:
                    config_value = data[config_option]
                except KeyError:
                    log.debug(
                        _("Unable to find %s in prefilled data. Ignoring."),
                        config_option,
                    )
                    continue
            else:
                try:
                    config_value = config.config_parser.get(config_section, config_option)
                except (configparser.NoOptionError, configparser.NoSectionError):
                    log.debug(
                        _("Unable to find %s in section %s at config file. Using fallback value."),
                        config_option,
                        config_section,
                    )

                    try:
                        config_value = str(getattr(config.DefaultConfig, config_option))
                    except AttributeError:
                        log.debug(_("Unable to find fallback value to %s. Ignoring"), config_option)
                        continue

            if isinstance(children, Gtk.ComboBox):
                assert isinstance(combo_items, dict), "No combo_items"
                children.set_active(list(combo_items).index(config_value))
            else:
                children.set_text(config_value)

            if save:
                config.new(config.ConfigType(config_section, config_option, config.ConfigStr(config_value)))
