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
import logging
from typing import Optional, Union

from gi.repository import Gtk, Pango

from . import password, utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation

log_levels = [
    'critical',
    'error',
    'warning',
    'info',
    'debug',
]

translations = {
    'en': _("English"),
    'pt_BR': _("Portuguese (Brazil)"),
}

languages = list(translations.keys())


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
        login_section = utils.new_section(_('Login settings'))
        username_item = utils.new_item(_("Username"), login_section, Gtk.Entry, 0, 0)
        encrypted_password_item = utils.new_item(_("Encrypted password"), login_section, Gtk.Entry, 0, 2)
        encrypted_password_item.children.set_editable(False)

        load_login_options(username_item.children, encrypted_password_item.children)
        username_item.children.connect("changed", self.on_username_changed)

        change_password = Gtk.Button(_("Change password"))

        change_password.connect(
            'clicked',
            self.on_change_password_clicked,
            username_item.children,
            encrypted_password_item.children,
        )

        login_section.grid.attach(change_password, 0, 4, 2, 1)

        login_section.frame.show_all()
        return login_section.frame

    def steamtrades_settings(self) -> Gtk.Frame:
        steamtrades_section = utils.new_section(_('Steamtrades settings'))
        info_label = Gtk.Label("trade id separated by commas. (E.g.: '12345,asdfg')")
        steamtrades_section.grid.attach(info_label, 0, 0, 2, 1)
        trade_ids = utils.new_item(_("trade ids:"), steamtrades_section, Gtk.Entry, 0, 1)

        load_steamtrades_options(trade_ids.children)

        steamtrades_section.frame.show_all()
        return steamtrades_section.frame

    def locale_settings(self) -> Gtk.Frame:
        locale_section = utils.new_section(_('Locale settings'))
        language_item = utils.new_item(_("Language"), locale_section, Gtk.ComboBoxText, 0, 0)

        load_locale_options(language_item.children)
        language_item.children.connect("changed", self.on_language_combo_changed)

        locale_section.frame.show_all()
        return locale_section.frame

    def logger_settings(self) -> Gtk.Frame:
        logger_section = utils.new_section(_('Logger settings'))
        log_level_item = utils.new_item(_("Level:"), logger_section, Gtk.ComboBoxText, 0, 0)
        log_console_level_item = utils.new_item(_("Console level:"), logger_section, Gtk.ComboBoxText, 0, 1)

        load_logger_options(log_level_item.children, log_console_level_item.children)
        log_level_item.children.connect("changed", self.on_log_level_changed)
        log_console_level_item.children.connect("changed", self.on_log_console_level_changed)

        logger_section.frame.show_all()
        return logger_section.frame

    def on_language_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        language = config.ConfigStr(languages[combo.get_active()])
        config.new(config.ConfigType('locale', 'language', language))
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)

    @staticmethod
    def on_username_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('login', 'username', entry.get_text()))

    def on_change_password_clicked(
            self,
            button: Gtk.Button,
            username_entry: Gtk.Entry,
            encrypted_password_entry: Gtk.Entry
    ) -> None:
        password_dialog = password.PasswordDialog(parent_window=self, username=username_entry.get_text())
        password_dialog.show()

        asyncio.ensure_future(wait_encrypted_password(password_dialog, encrypted_password_entry))

    @staticmethod
    def on_log_level_changed(combo: Gtk.ComboBoxText) -> None:
        config.new(config.ConfigType('logger', 'log_level', combo.get_active_text()))

    @staticmethod
    def on_log_console_level_changed(combo: Gtk.ComboBoxText) -> None:
        config.new(config.ConfigType('logger', 'log_console_level', combo.get_active_text()))

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()


@config.Check("login")
def load_login_options(
        username_entry: Gtk.Entry,
        encrypted_password_entry: Gtk.Entry,
        username: Optional[config.ConfigStr] = None,
        encrypted_password: Optional[config.ConfigStr] = None,
):
    if username:
        username_entry.set_text(username)

    if encrypted_password:
        encrypted_password_entry.set_text(encrypted_password)


@config.Check("locale")
def load_locale_options(
        language_combo: Gtk.ComboBoxText,
        language: Union[str, config.ConfigStr] = i18n.fallback_language,
) -> None:
    for translation, description in translations.items():
        language_combo.append_text(f'[{translation}] {description}')

    language_combo.set_active(languages.index(language))


@config.Check("logger")
def load_logger_options(
        log_level_combo: Gtk.ComboBoxText,
        log_console_level_combo: Gtk.ComboBoxText,
        log_level: Union[str, config.ConfigStr] = 'debug',
        log_console_level: Union[str, config.ConfigStr] = 'info',
) -> None:
    for level in log_levels:
        log_level_combo.append_text(level)
        log_console_level_combo.append_text(level)

    log_level_combo.set_active(log_levels.index(log_level))
    log_console_level_combo.set_active(log_levels.index(log_console_level))


@config.Check("steamtrades")
def load_steamtrades_options(
        trade_ids_entry: Gtk.Entry,
        trade_ids: Optional[config.ConfigStr] = None
) -> None:
    if trade_ids:
        trade_ids_entry.set_text(trade_ids)


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


async def wait_encrypted_password(password_dialog: Gtk.Dialog, encrypted_password_entry: Gtk.Entry) -> None:
    while not password_dialog.encrypted_password:
        await asyncio.sleep(5)

    encrypted_password_entry.set_text(password_dialog.encrypted_password)

    config.new(
        config.ConfigType(
            "login",
            "encrypted_password",
            config.ConfigStr(password_dialog.encrypted_password)
        )
    )

    password_dialog.destroy()
