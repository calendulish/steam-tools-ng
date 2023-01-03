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
import asyncio
import logging
from gi.repository import Gtk

from . import utils, settings, login
from .. import i18n, config

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class AdvancedSettingsDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            toggle_button: Gtk.ToggleButton,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.application = application
        self.toggle_button = toggle_button

        self.set_default_size(600, 150)
        self.set_title(_('Advanced Settings'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)

        self.gtk_settings_class = Gtk.Settings.get_default()

        content_area = self.get_content_area()
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)

        content_grid = Gtk.Grid()
        content_grid.set_row_spacing(10)
        content_grid.set_column_spacing(10)
        content_area.append(content_grid)

        login_section = utils.Section("login", _("Advanced Login Settings"))
        content_grid.attach(login_section, 0, 0, 1, 2)

        shared_secret = login_section.new_item('shared_secret', _("Shared Secret:"), Gtk.Entry, 0, 0)
        shared_secret.connect('changed', settings.on_setting_changed)

        token_item = login_section.new_item("token", _("Token:"), Gtk.Entry, 0, 1)
        token_item.connect("changed", settings.on_setting_changed)

        token_secure_item = login_section.new_item("token_secure", _("Token Secure:"), Gtk.Entry, 0, 2)
        token_secure_item.connect("changed", settings.on_setting_changed)

        identity_secret = login_section.new_item('identity_secret', _("Identity Secret:"), Gtk.Entry, 2, 0)
        identity_secret.connect('changed', settings.on_setting_changed)

        deviceid = login_section.new_item('deviceid', _("Device ID:"), Gtk.Entry, 2, 1)
        deviceid.connect('changed', settings.on_setting_changed)

        steamid_item = login_section.new_item("steamid", _("Steam ID:"), Gtk.Entry, 2, 2)
        steamid_item.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.connect("changed", settings.on_digit_only_setting_changed)

        reset_button = utils.AsyncButton()
        reset_button.set_label(_("Reset Everything (USE WITH CAUTION!!!)"))
        reset_button.set_name("reset_button")
        reset_button.connect("clicked", self.on_reset_clicked)
        login_section.grid.attach(reset_button, 0, 9, 4, 1)

        self.connect('response', lambda dialog, response_id: self._exit())

    def _exit(self) -> None:
        # self.toggle_button.set_active(False)
        # FIXME: enabled plugins must be updated
        self.parent_window.destroy()
        self.destroy()

    async def on_reset_clicked(self, button: Gtk.Button) -> None:
        login_dialog = login.LoginDialog(self.parent_window, self.application)
        login_dialog.status.info(_("Reseting... Please wait!"))
        login_dialog.set_deletable(False)
        login_dialog.user_details_section.hide()
        login_dialog.advanced_login.hide()
        login_dialog.show()
        await asyncio.sleep(3)

        config.config_file.unlink(missing_ok=True)

        config.parser.clear()
        config.init()
        self.parent_window.destroy()

        login_dialog.status.info(_("Waiting"))
        login_dialog.user_details_section.show()
        login_dialog.advanced_login.show()

        self.destroy()
