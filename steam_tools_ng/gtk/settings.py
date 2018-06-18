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
from typing import Any, Optional

from gi.repository import Gtk, Pango

from . import login, utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation

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
    def __init__(self, parent_window: Gtk.Widget) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        content_area = self.get_content_area()
        content_area.set_orientation(Gtk.Orientation.VERTICAL)
        content_area.set_border_width(10)
        content_area.set_spacing(10)

        content_area.add(self.login_settings())
        content_area.add(self.logger_settings())
        content_area.add(self.locale_settings())
        content_area.add(self.steamtrades_settings())

        self.connect('response', self.on_response)
        self.show()

    def login_settings(self) -> Gtk.Frame:
        login_section = utils.new_section("login", _('Login settings'))
        steamid_item = utils.new_item("steamid", _("steam id:"), login_section, Gtk.Entry, 0, 0)
        token_item = utils.new_item("token", _("Token:"), login_section, Gtk.Entry, 0, 2)
        token_secure_item = utils.new_item("token_secure", _("Token secure:"), login_section, Gtk.Entry, 0, 4)

        load_settings(login_section, Gtk.Entry)

        steamid_item.children.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.children.connect("changed", self.on_steamid_changed)
        token_item.children.connect("changed", self.on_token_changed)
        token_secure_item.children.connect("changed", self.on_token_secure_changed)

        log_in = Gtk.Button(_("Log-in"))

        log_in.connect(
            'clicked',
            self.on_log_in_clicked,
            steamid_item.children,
            token_item.children,
            token_secure_item.children,
        )

        login_section.grid.attach(log_in, 0, 6, 2, 1)

        login_section.frame.show_all()
        return login_section.frame

    @staticmethod
    def steamtrades_settings() -> Gtk.Frame:
        steamtrades_section = utils.new_section('steamtrades', _('Steamtrades settings'))
        info_label = Gtk.Label("trade id separated by commas. (E.g.: '12345,asdfg')")
        steamtrades_section.grid.attach(info_label, 0, 0, 2, 1)
        trade_ids = utils.new_item("trade_ids", _("trade ids:"), steamtrades_section, Gtk.Entry, 0, 1)

        load_settings(steamtrades_section, Gtk.Entry)

        steamtrades_section.frame.show_all()
        return steamtrades_section.frame

    def locale_settings(self) -> Gtk.Frame:
        locale_section = utils.new_section("locale", _('Locale settings'))
        language_item = utils.new_item("language", _("Language"), locale_section, Gtk.ComboBoxText, 0, 0)

        load_settings(locale_section, Gtk.ComboBoxText, combo_items=translations)
        language_item.children.connect("changed", self.on_language_combo_changed)

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

        log_level_item.children.connect("changed", self.on_log_level_changed)
        log_console_level_item.children.connect("changed", self.on_log_console_level_changed)

        logger_section.frame.show_all()
        return logger_section.frame

    def on_language_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        language = config.ConfigStr(list(translations)[combo.get_active()])
        config.new(config.ConfigType('locale', 'language', language))
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)

    @staticmethod
    def on_steamid_changed(entry: Gtk.Entry) -> None:
        text = entry.get_text()

        if text.isdigit():
            config.new(config.ConfigType('login', 'steamid', entry.get_text()))
        else:
            new_text = []

            for char in text:
                if char.isdigit():
                    new_text.append(char)

            entry.set_text(''.join(new_text))

    @staticmethod
    def on_token_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('login', 'token', entry.get_text()))

    @staticmethod
    def on_token_secure_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('login', 'token_secure', entry.get_text()))

    def on_log_in_clicked(
            self,
            button: Gtk.Button,
            steamid_entry: Gtk.Entry,
            token_entry: Gtk.Entry,
            token_secure_entry: Gtk.Entry,
    ) -> None:
        login_dialog = login.LogInDialog(parent_window=self)
        login_dialog.show()

        asyncio.ensure_future(wait_login_data(login_dialog, steamid_entry, token_entry, token_secure_entry))

    @staticmethod
    def on_log_level_changed(combo: Gtk.ComboBoxText) -> None:
        log_level = config.ConfigStr(list(log_levels)[combo.get_active()])
        config.new(config.ConfigType('logger', 'log_level', log_level))

    @staticmethod
    def on_log_console_level_changed(combo: Gtk.ComboBoxText) -> None:
        log_console_level = config.ConfigStr(list(log_levels)[combo.get_active()])
        config.new(config.ConfigType('logger', 'log_console_level', log_console_level))

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()


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


async def wait_login_data(
        login_dialog: Gtk.Dialog,
        steamid_entry: Gtk.Entry,
        token_entry: Gtk.Entry,
        token_secure_entry: Gtk.Entry,
) -> None:
    while not login_dialog.login_data:
        await asyncio.sleep(5)

    steamid = login_dialog.login_data["transfer_parameters"]["steamid"]
    token = login_dialog.login_data["transfer_parameters"]["token"]
    token_secure = login_dialog.login_data["transfer_parameters"]["token_secure"]

    steamid_entry.set_text(steamid)
    token_entry.set_text(token)
    token_secure_entry.set_text(token_secure)

    config.new(
        config.ConfigType(
            "login",
            "steamid",
            config.ConfigStr(steamid),
        ),
        config.ConfigType(
            "login",
            "token",
            config.ConfigStr(token)
        ),
        config.ConfigType(
            "login",
            "token_secure",
            config.ConfigStr(token_secure)
        ),
    )

    login_dialog.destroy()


def load_settings(
        section: utils.Section,
        children_type: Gtk.Widget,
        combo_items: Optional = None,
        **kwargs: Any,
):
    childrens = Gtk.Container.get_children(section.grid)

    for children in childrens:
        if isinstance(children, children_type):
            config_section = section.frame.get_name()
            config_option = children.get_name()

            try:
                config_value = config.config_parser.get(config_section, config_option)
            except (configparser.NoOptionError, configparser.NoSectionError):
                log.debug(_("Unable to find %s in section %s at config file. Ignoring."), config_section, config_option)
                continue

            if combo_items:
                for value in combo_items.values():
                    children.append_text(value)

                if isinstance(children, Gtk.ComboBox):
                    children.set_active(list(combo_items).index(config_value))
            else:
                children.set_text(config_value)
