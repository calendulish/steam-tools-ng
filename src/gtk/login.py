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
import base64
import binascii
import logging
from typing import Optional

from gi.repository import Gdk, Gtk
from stlib import authenticator, webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class LogInDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget) -> None:
        super().__init__(use_header_bar=True)
        self.session = parent_window.session
        self.login_data = None

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 60)
        self.set_title(_('Log-in on Steam'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status = utils.SimpleStatus()
        self.content_area.add(self.status)

        self.user_details_section = utils.new_section("login", _("User Details"))
        self.content_area.add(self.user_details_section.frame)

        config_username = config.config_parser.get("login", "account_name", fallback="")
        self.username_item = utils.new_item("username", _("Username:"), self.user_details_section, Gtk.Entry, 0, 0)
        self.username_item.children.set_text(config_username)
        self.username_item.children.connect("key-release-event", self.on_key_release)

        self.__password_item = utils.new_item("password", _("Password:"), self.user_details_section, Gtk.Entry, 0, 1)
        self.__password_item.children.set_visibility(False)
        self.__password_item.children.set_invisible_char('*')
        self.__password_item.children.set_placeholder_text(_("It will not be saved"))
        self.__password_item.children.connect("key-release-event", self.on_key_release)

        self.log_in_button = Gtk.Button(_("Log In"))
        self.log_in_button.connect("clicked", self.on_log_in_button_clicked)
        self.header_bar.pack_end(self.log_in_button)

        self.cancel_button = Gtk.Button(_("Cancel"))
        self.cancel_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.cancel_button)

        self.content_area.show_all()
        self.header_bar.show_all()

        self.connect('response', lambda dialog, response_id: self.destroy())

    def on_key_release(self, entry: Gtk.Entry, event: Gdk.EventKey):
        if event.keyval == Gdk.KEY_Return:
            self.log_in_button.clicked()

    def on_log_in_button_clicked(self, button: Gtk.Button) -> None:
        username = self.username_item.children.get_text()
        password = self.__password_item.children.get_text()
        self.user_details_section.frame.hide()
        self.log_in_button.hide()
        self.cancel_button.hide()
        self.set_size_request(300, 60)
        self.status.info(_("Running... Please wait"))
        self.header_bar.set_show_close_button(False)
        task = asyncio.ensure_future(self.do_login(username, password))
        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, future: asyncio.Future) -> None:
        if not self.login_data:
            self.header_bar.set_show_close_button(True)
            self.log_in_button.set_label(_("Try again?"))
            self.log_in_button.show()
            self.user_details_section.frame.show()
        else:
            self.__password_item.children.set_text("")

    @config.Check("login")
    async def do_login(
            self,
            username: str,
            password: str,
            shared_secret: Optional[config.ConfigStr] = None
    ) -> None:
        if not shared_secret:
            self.status.error(_(
                "Unable to log-in!\n\n"
                "To login you need to provide at last a valid shared secret.\n"
                "You can use 'Get login data using ADB' button to get it,\n"
                "or insert it manually on:\n\n"
                "settings -> login settings -> mark 'advanced' -> shared secret\n"
            ))
            return None

        try:
            base64.b64decode(shared_secret)
        except binascii.Error:
            self.status.error(_("Unable to log-in!\nThe shared secret received is invalid."))
            return None

        if not username or not password:
            self.status.error(_("Unable to log-in!\nYour username/password is blank."))
            return None

        steam_webapi = webapi.SteamWebAPI(self.session, 'https://lara.click/api')
        steam_key = await steam_webapi.get_steam_key(username)
        encrypted_password = webapi.encrypt_password(steam_key, password)

        try:
            authenticator_code, server_time = authenticator.get_code(shared_secret)
        except ProcessLookupError:
            self.status.error(_("Unable to log-in!\nSteam Client is not running."))
            return None

        steam_login_data = await steam_webapi.do_login(
            username,
            encrypted_password,
            steam_key.timestamp,
            authenticator_code,
        )

        if steam_login_data['success']:
            self.login_data = {**steam_login_data["transfer_parameters"], 'account_name': username}
        else:
            self.status.error(_("Unable to log-in on Steam!\nPlease, try again."))
            return None
