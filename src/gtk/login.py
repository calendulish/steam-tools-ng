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
from typing import Any, Dict, Optional

import aiohttp
from gi.repository import Gdk, Gtk
from stlib import webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class LogInDialog(Gtk.Dialog):
    def __init__(self, parent_window: Gtk.Widget, session: aiohttp.ClientSession, mobile_login: bool = False) -> None:
        super().__init__(use_header_bar=True)
        self.session = session
        self.mobile_login = mobile_login
        self.login_data: Dict[str, Any] = {}

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

        self.log_in_button = Gtk.Button(_("Log-in"))
        self.log_in_button.connect("clicked", self.on_log_in_button_clicked)
        self.header_bar.pack_end(self.log_in_button)

        self.cancel_button = Gtk.Button(_("Cancel"))
        self.cancel_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.cancel_button)

        self.content_area.show_all()
        self.header_bar.show_all()

        self.code_item = utils.new_item("code", _("Code:"), self.user_details_section, Gtk.Entry, 0, 2)
        self.code_item.label.hide()
        self.code_item.children.hide()

        self.connect('response', lambda dialog, response_id: self.destroy())

    def on_key_release(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
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

    # FIXME: https://github.com/python/typing/issues/446
    # noinspection PyUnresolvedReferences
    def on_task_finish(self, future: 'asyncio.Future[Any]') -> None:
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
            mail_code: str = '',
            authenticator_code: str = '',
    ) -> None:
        if not username or not password:
            self.status.error(_("Unable to log-in!\nYour username/password is blank."))
            return None

        login = webapi.Login(self.session, username, password)
        steam_webapi = webapi.SteamWebAPI(self.session, 'https://lara.click/api')

        try:
            login_data = await login.do_login(
                emailauth=mail_code,
                authenticator_code=authenticator_code,
                mobile_login=self.mobile_login
            )

            if not login_data['success']:
                raise webapi.LoginError
        except webapi.MailCodeError:
            self.status.info(_("Write code received by email\nand click on 'Try Again?' button"))
            self.code_item.label.show()
            self.code_item.children.show()

            self.log_in_button.connect("clicked",
                                       lambda button: asyncio.ensure_future(
                                           self.do_login(
                                               username,
                                               password,
                                               self.code_item.children.get_text(),
                                               authenticator_code,
                                           )
                                       )
                                       )

            self.log_in_button.show()
            self.header_bar.set_show_close_button(True)
            return
        except webapi.TwoFactorCodeError:
            self.status.error(_(
                "Unable to log-in!\n"
                "You already have a Steam Authenticator active on current account\n\n"
                "To log-in, you have two options:\n\n"
                "- Just remove authenticator from your account and use the 'Try Again?' button\n"
                "    to set STNG as your Steam Authenticator.\n\n"
                "- Put your shared secret on settings or let us automagically find it using adb\n"
                "    (settings -> 'get login data using adb' button)\n"

            ))
            self.header_bar.set_show_close_button(True)
            return
        except webapi.LoginError:
            self.status.error(_(
                "Unable to log-in!\n"
                "Please, check your username/password and try again.\n"
            ))
            self.header_bar.set_show_close_button(True)
            return
        except aiohttp.ClientConnectionError:
            self.status.error(_("No Connection"))
            self.header_bar.set_show_close_button(True)
            return

        if self.mobile_login:
            async with self.session.get('https://steamcommunity.com') as response:
                sessionid = response.cookies['sessionid'].value

            has_phone: Optional[bool]

            if await login.has_phone(sessionid):
                has_phone = True
            else:
                has_phone = False
        else:
            has_phone = None

        self.login_data = {
            **login_data,
            'account_name': username,
            'has_phone': has_phone,
        }
