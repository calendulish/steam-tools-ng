#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
from subprocess import call

from gi.repository import Gtk, Pango
from stlib import plugins

from . import utils, advanced, authenticator, login
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
        content_grid.attach(stack, 1, 0, 1, 1)

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        content_grid.attach(sidebar, 0, 0, 1, 1)

        general_section = utils.Section("general", _("General Settings"))

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

        theme = general_section.new("theme", _("Theme:"), Gtk.ComboBoxText, 0, 3, items=config.gtk_themes)
        theme.connect('changed', self.on_theme_changed)

        show_close_button = general_section.new("show_close_button", _("Show close button:"), Gtk.CheckButton, 0, 4)
        show_close_button.connect('toggled', self.on_show_close_button_toggled)

        language_item = general_section.new(
            "language", _("Language"), Gtk.ComboBoxText, 0, 5, items=config.translations
        )
        language_item.connect("changed", self.update_language)

        login_section = utils.Section("login", _("Login Settings"))

        account_name = login_section.new('account_name', _("Username:"), Gtk.Entry, 0, 0)
        account_name.connect('changed', on_setting_changed)

        login_button = Gtk.Button()
        login_button.set_label(_("Login with another account"))
        login_button.set_name("login_button")
        login_button.connect('clicked', self.on_login_button_clicked)
        login_section.grid.attach(login_button, 0, 1, 2, 1)

        new_authenticator_button = Gtk.Button()
        new_authenticator_button.set_label(_("Use STNG as your Steam Authenticator"))
        new_authenticator_button.set_name("new_authenticator_button")
        new_authenticator_button.connect("clicked", self.on_new_authenticator_clicked)
        login_section.grid.attach(new_authenticator_button, 0, 2, 2, 1)

        reset_password_button = Gtk.Button()
        reset_password_button.set_label(_("Remove Saved Password"))
        reset_password_button.set_name("reset_password_button")
        reset_password_button.connect("clicked", self.on_reset_password_clicked)
        login_section.grid.attach(reset_password_button, 0, 3, 2, 1)

        advanced_button = Gtk.ToggleButton()
        advanced_button.set_label(_("Advanced"))
        advanced_button.set_name("advanced_button")
        advanced_button.connect("toggled", self.on_advanced_button_toggled)
        login_section.grid.attach(advanced_button, 0, 4, 2, 1)

        confirmations_section = utils.Section('confirmations', _('Confirmations Settings'))

        confirmations_enable = confirmations_section.new("enable", _("Enable"), Gtk.CheckButton, 0, 0)
        confirmations_enable.connect('toggled', on_setting_toggled)

        if not config.parser.get("login", "identity_secret"):
            confirmations_section.set_sensitive(False)
            confirmations_enable.set_active(False)
            _confirmations_disabled = Gtk.Label()
            _confirmations_disabled.set_justify(Gtk.Justification.CENTER)
            _confirmations_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "confirmations module has been disabled because you have\n"
                "logged in but no identity secret is found. To enable it again,\n"
                "go to login -> advanced and add a valid identity secret\n"
                "or use STNG as your Steam Authenticator\n"
            )

            _confirmations_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            confirmations_section.grid.attach(_confirmations_disabled, 0, 1, 4, 4)

        steamguard_section = utils.Section('steamguard', _('SteamGuard Settings'))

        steamguard_enable = steamguard_section.new("enable", _("Enable"), Gtk.CheckButton, 0, 0)
        steamguard_enable.connect('toggled', on_setting_toggled)

        if not config.parser.get("login", "shared_secret"):
            steamguard_section.set_sensitive(False)
            steamguard_enable.set_active(False)
            _steamguard_disabled = Gtk.Label()
            _steamguard_disabled.set_justify(Gtk.Justification.CENTER)
            _steamguard_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamguard module has been disabled because you have\n"
                "logged in but no shared secret is found. To enable it again,\n"
                "go to login -> advanced and add a valid shared secret\n"
                "or use STNG as your Steam Authenticator\n"
            )

            _steamguard_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamguard_section.grid.attach(_steamguard_disabled, 0, 1, 4, 4)

        steamtrades_section = utils.Section('steamtrades', _('Steamtrades Settings'))

        steamtrades_enable = steamtrades_section.new("enable", _("Enable"), Gtk.CheckButton, 0, 0)
        steamtrades_enable.connect('toggled', on_setting_toggled)

        trade_ids = steamtrades_section.new("trade_ids", _("Trade IDs:"), Gtk.Entry, 0, 1)
        trade_ids.set_placeholder_text('12345, asdfg, ...')
        trade_ids.connect("changed", on_setting_changed)

        wait_min = steamtrades_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 2)
        wait_min.connect("changed", on_digit_only_setting_changed)

        wait_max = steamtrades_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 3)
        wait_max.connect("changed", on_digit_only_setting_changed)

        if not plugins.has_plugin("steamtrades"):
            steamtrades_section.set_sensitive(False)
            steamtrades_enable.set_active(False)
            _steamtrades_disabled = Gtk.Label()
            _steamtrades_disabled.set_justify(Gtk.Justification.CENTER)
            _steamtrades_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamtrades module has been disabled because you don't\n"
                "have steamtrades plugin installed. To enable it again,\n"
                "install the steamtrades plugin.\n"
            )

            _steamtrades_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamtrades_section.grid.attach(_steamtrades_disabled, 0, 1, 4, 4)

        steamgifts_section = utils.Section("steamgifts", _("Steamgifts Settings"))

        steamgifts_enable = steamgifts_section.new("enable", _("Enable"), Gtk.CheckButton, 0, 0)
        steamgifts_enable.connect('toggled', on_setting_toggled)

        giveaway_type = steamgifts_section.new(
            "giveaway_type",
            _("Giveaway Type:"),
            Gtk.ComboBoxText,
            0, 1,
            items=config.giveaway_types,
        )
        giveaway_type.connect("changed", on_combo_setting_changed, config.giveaway_types)

        sort_giveaways = steamgifts_section.new(
            "sort",
            _("Sort Giveaways:"),
            Gtk.ComboBoxText,
            0, 2,
            items=config.giveaway_sort_types,
        )
        sort_giveaways.connect("changed", on_combo_setting_changed, config.giveaway_sort_types)

        reverse_sorting = steamgifts_section.new("reverse_sorting", _("Reverse Sorting:"), Gtk.CheckButton, 0, 3)
        reverse_sorting.connect("toggled", on_setting_toggled)

        developer_giveaways = steamgifts_section.new(
            "developer_giveaways",
            _("Developer Giveaways"),
            Gtk.CheckButton,
            0, 4,
        )
        developer_giveaways.connect("toggled", on_setting_toggled)

        wait_min = steamgifts_section.new("wait_min", _("Wait MIN:"), Gtk.Entry, 0, 5)
        wait_min.connect("changed", on_digit_only_setting_changed)

        wait_max = steamgifts_section.new("wait_max", _("Wait MAX:"), Gtk.Entry, 0, 6)
        wait_max.connect("changed", on_digit_only_setting_changed)

        if not plugins.has_plugin("steamgifts"):
            steamgifts_section.set_sensitive(False)
            steamgifts_enable.set_active(False)
            _steamgifts_disabled = Gtk.Label()
            _steamgifts_disabled.set_justify(Gtk.Justification.CENTER)
            _steamgifts_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamgifts module has been disabled because you don't\n"
                "have steamgifts plugin installed. To enable it again,\n"
                "install the steamgifts plugin.\n"
            )

            _steamgifts_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamgifts_section.grid.attach(_steamgifts_disabled, 0, 1, 4, 4)

        cardfarming_section = utils.Section("cardfarming", _("Cardfarming settings"))

        cardfarming_enable = cardfarming_section.new("enable", _("Enable"), Gtk.CheckButton, 0, 0)
        cardfarming_enable.connect("toggled", on_setting_toggled)

        first_wait = cardfarming_section.new("first_wait", _("First Wait:"), Gtk.Entry, 0, 1)
        first_wait.connect("changed", on_digit_only_setting_changed)

        default_wait = cardfarming_section.new("default_wait", _("Default Wait:"), Gtk.Entry, 0, 2)
        default_wait.connect("changed", on_digit_only_setting_changed)

        min_wait = cardfarming_section.new("min_wait", _("MIN Wait:"), Gtk.Entry, 0, 3)
        min_wait.connect("changed", on_digit_only_setting_changed)

        reverse_sorting = cardfarming_section.new("reverse_sorting", _("More cards First:"), Gtk.CheckButton, 0, 4)

        if not config.client:
            cardfarming_section.set_sensitive(False)
            cardfarming_enable.set_active(False)
            _cardfarming_disabled = Gtk.Label()
            _cardfarming_disabled.set_justify(Gtk.Justification.CENTER)
            _cardfarming_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "cardfarming module has been disabled because you have\n"
                "a stlib built without steam_api support. To enable it again,\n"
                "reinstall stlib with Steam API support\n"
            )

            _cardfarming_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            cardfarming_section.grid.attach(_cardfarming_disabled, 0, 1, 4, 4)

        logger_section = utils.Section("logger", _('Logger settings'))

        log_level_item = logger_section.new("log_level", _("Level:"), Gtk.ComboBoxText, 0, 0, items=config.log_levels)

        log_console_level_item = logger_section.new(
            "log_console_level",
            _("Console level:"),
            Gtk.ComboBoxText,
            0, 1,
            items=config.log_levels,
        )

        log_level_item.connect("changed", on_combo_setting_changed, config.log_levels)
        log_console_level_item.connect("changed", on_combo_setting_changed, config.log_levels)

        self.connect('response', lambda dialog, response_id: self.destroy())

        for section in [
            general_section,
            login_section,
            logger_section,
            steamtrades_section,
            cardfarming_section,
            steamgifts_section,
            steamguard_section,
            confirmations_section,
        ]:
            section.stackup_section(stack)

    @staticmethod
    def on_log_button_clicked(button: Gtk.Button) -> None:
        call(f'{config.file_manager} {config.parser.get("logger", "log_directory")}')

    @staticmethod
    def on_config_button_clicked(button: Gtk.Button) -> None:
        call(f'{config.file_manager} {str(config.config_file_directory)}')

    def on_advanced_button_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            advanced_settings = advanced.AdvancedSettingsDialog(self, self.application, button)
            advanced_settings.show()

    def on_show_close_button_toggled(self, button: Gtk.Button) -> None:
        current_value = button.get_active()

        if current_value:
            self.parent_window.set_deletable(True)
        else:
            self.parent_window.set_deletable(False)

        config.new('general', 'show_close_button', current_value)

    def on_theme_changed(self, combo: Gtk.ComboBoxText) -> None:
        theme = list(config.gtk_themes)[combo.get_active()]

        if theme == 'dark':
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = True
        else:
            self.gtk_settings_class.props.gtk_application_prefer_dark_theme = False

        config.new('general', 'theme', theme)

    def on_login_button_clicked(self, button: Gtk.Button) -> None:
        login_dialog = login.LoginDialog(self.parent_window, self.application)
        login_dialog.show()
        self.destroy()

    def on_new_authenticator_clicked(self, button: Gtk.Button) -> None:
        new_authenticator_dialog = authenticator.NewAuthenticatorDialog(self.parent_window, self.application)
        new_authenticator_dialog.show()
        self.destroy()

    def on_reset_password_clicked(self, button: Gtk.Button) -> None:
        login_dialog = login.LoginDialog(self.parent_window, self.application)
        login_dialog.status.info(_("Removing saved password..."))
        login_dialog.user_details_section.hide()
        login_dialog.advanced_login.hide()
        login_dialog.set_deletable(False)
        login_dialog.show()

        config.new("login", "password", "")

        def reset_password_callback() -> None:
            self.destroy()
            login_dialog.destroy()

        asyncio.get_event_loop().call_later(2, reset_password_callback)

    def update_language(self, combo: Gtk.ComboBoxText) -> None:
        language = list(config.translations)[combo.get_active()]
        config.new('general', 'language', language)
        refresh_widget_childrens(self)
        refresh_widget_childrens(self.parent_window)


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


def refresh_widget_childrens(widget: Gtk.Widget) -> None:
    next_child = widget.get_first_child()
    while next_child:
        refresh_widget(next_child)
        next_child = next_child.get_next_sibling()


def refresh_widget(widget: Gtk.Widget) -> None:
    if isinstance(widget, Gtk.MenuButton):
        refresh_widget(widget.get_popover())
        return

    if isinstance(widget, Gtk.ComboBoxText):
        model = widget.get_model()

        for index in range(len(model)):
            iter = model[index].iter
            combo_item_label = model.get_value(iter, 0)

            try:
                cached_text = i18n.cache[i18n.new_hash(combo_item_label)]
            except KeyError:
                log.debug("it's not an i18n string: %s", combo_item_label)
                return

            model.set_value(iter, 0, _(cached_text))

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

        log.debug('widget refreshed: %s', widget)
        return

    log.debug('widget not refresh: %s', widget)
    refresh_widget_childrens(widget)
