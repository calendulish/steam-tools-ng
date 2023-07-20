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
import binascii
import logging
from typing import Any, Optional

import aiohttp
from gi.repository import Gtk, Gdk

from stlib import login
from stlib.login import AuthCodeType
from . import utils
from .. import i18n, config, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class LoginWindow(utils.PopupWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            mobile_login: bool = True,
    ) -> None:
        super().__init__(parent_window, application)
        self.mobile_login = mobile_login
        self.has_user_data = False

        self.login_button = utils.AsyncButton()
        self.login_button.set_label(_("Log-in"))
        self.login_button.connect("clicked", self.on_login_button_clicked)
        self.header_bar.pack_end(self.login_button)
        self.set_title(_('Login'))

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        self.user_details_section = utils.Section("login")
        self.content_grid.attach(self.user_details_section, 0, 1, 1, 1)

        self.username_item = self.user_details_section.new_item("account_name", _("Username:"), Gtk.Entry, 0, 0)

        self.__password_item = self.user_details_section.new_item("_password", _("Password:"), Gtk.Entry, 0, 1)
        self.__password_item.set_visibility(False)
        self.__password_item.set_invisible_char('*')

        self.auth_code_item = self.user_details_section.new_item("_auth_code", _("Code:"), Gtk.Entry, 0, 2)

        self.save_password_item = self.user_details_section.new_item(
            "_savepwd",
            _("Save Password:"),
            Gtk.CheckButton,
            0, 5,
        )
        self.save_password_item.set_active(True)

        self.advanced_login = utils.ClickableLabel()
        self.advanced_login.set_markup(utils.markup(_("Advanced Login"), font_size='x-small', color='blue'))
        self.advanced_login.set_halign(Gtk.Align.END)
        self.advanced_login.set_margin_end(10)
        self.advanced_login.set_margin_bottom(10)
        self.advanced_login.connect("clicked", self.on_advanced_login_clicked)
        self.content_grid.attach(self.advanced_login, 0, 2, 1, 1)

        self.advanced_login_section = utils.Section("login")
        self.content_grid.attach(self.advanced_login_section, 0, 3, 1, 1)

        self.identity_secret_item = self.advanced_login_section.new_item(
            'identity_secret',
            _("Identity Secret:"),
            Gtk.Entry,
            0, 0,
        )

        self.shared_secret_item = self.advanced_login_section.new_item(
            'shared_secret',
            _("Shared Secret:"),
            Gtk.Entry,
            0, 1,
        )

        self.connect('destroy', self.on_quit)
        self.connect('close-request', self.on_quit)

        self.auth_code_item.set_visible(False)
        self.advanced_login_section.set_visible(False)
        self.check_login_availability()

    @property
    def username(self) -> str:
        return self.username_item.get_text()

    @property
    def __password(self) -> str:
        return self.__password_item.get_text()

    def set_password(self, encrypted_password: str) -> None:
        try:
            __password = core.utils.decode_password(encrypted_password)
            self.__password_item.set_text(__password)
        except (binascii.Error, UnicodeError, TypeError):
            log.warning(_("Password decode failed. Trying RAW."))
            self.__password_item.set_text(encrypted_password)

    @property
    def auth_code(self) -> str:
        return self.auth_code_item.get_text()

    @property
    def shared_secret(self) -> str:
        return self.shared_secret_item.get_text()

    @property
    def identity_secret(self) -> str:
        return self.identity_secret_item.get_text()

    def check_login_availability(self) -> None:
        if not self.username or not self.__password:
            self.login_button.set_sensitive(False)
        else:
            self.login_button.set_sensitive(True)

    def on_quit(self, *args: Any, **kwargs: Any) -> None:
        self.application.main_window.statusbar.set_warning(
            'steamguard',
            _("Login cancelled! Modules will not work correctly!"),
        )
        self.destroy()

    def on_key_released_event(
            self,
            controller: Gtk.EventControllerKey,
            keyval: int,
            keycode: int,
            state: Gdk.ModifierType
    ) -> None:
        super().on_key_released_event(controller, keyval, keycode, state)

        self.check_login_availability()

        if keyval == Gdk.KEY_Return:
            if self.username and self.__password:
                self.login_button.emit('clicked')
            else:
                self.status.error(_("Username or Password is blank!"))

    async def on_login_button_clicked(
            self,
            auto: bool,
            auth_code: str = '',
            auth_code_type: Optional[AuthCodeType] = AuthCodeType.device,
    ) -> None:
        self.status.info(_("Retrieving user data"))
        self.application.main_window.statusbar.set_warning("steamguard", _("Not logged in"))
        self.username_item.set_sensitive(False)
        self.__password_item.set_sensitive(False)
        self.save_password_item.set_sensitive(False)
        self.login_button.set_sensitive(False)

        _login_session = login.Login.get_session(0)
        _login_session.username = self.username
        _login_session.password = self.__password

        if not self.shared_secret:
            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))
            # self.code_item.set_visible(True)

        self.status.info(_("Logging in"))
        self.auth_code_item.set_visible(False)

        try_count = 3

        while True:
            try:
                login_data = await _login_session.do_login(
                    self.shared_secret,
                    self.auth_code if self.auth_code else auth_code,
                    auth_code_type,
                    self.mobile_login,
                )
            except login.MailCodeError:
                self.status.info(_("Write code received by email\nand click on 'Log-in' button"))
                self.auth_code_item.set_text("")
                self.auth_code_item.set_visible(True)
                self.auth_code_item.grab_focus()
                auth_code_type = AuthCodeType.email
            except login.TwoFactorCodeError:
                if self.shared_secret:
                    if try_count > 0:
                        for count in range(10, 0):
                            self.status.info(_("Retrying login in {} seconds").format(count))
                            await asyncio.sleep(1)

                        try_count -= 1
                        continue
                    else:
                        self.status.error(_("shared secret is invalid!"))
                        self.username_item.set_sensitive(True)
                        self.__password_item.set_sensitive(True)
                        self.shared_secret_item.grab_focus()
                        break

                self.status.error(_("Write Steam Code bellow and click on 'Log-in'"))
                self.auth_code_item.set_text("")
                self.auth_code_item.set_visible(True)
                self.auth_code_item.grab_focus()
                auth_code_type = AuthCodeType.device
            except login.LoginBlockedError:
                self.status.error(_(
                    "Your network is blocked!\n"
                    "It'll take some time until unblocked. Please, try again later\n"
                ))
                self.user_details_section.set_visible(False)
                self.advanced_login.set_visible(False)
                self.advanced_login_section.set_visible(False)
                self.login_button.set_visible(False)
                self.set_deletable(True)
            except login.CaptchaError as exception:
                # TODO: Captcha gid?? (where did you go? where did you go?)
                self.status.info(_("Write captcha code as shown bellow\nand click on 'Log-in' button"))

                # pixbuf_loader = GdkPixbuf.PixbufLoader()
                # pixbuf_loader.set_size(140, 50)
                # pixbuf_loader.write(exception.captcha)
                # pixbuf_loader.close()
                # self.captcha_item.set_from_pixbuf(pixbuf_loader.get_pixbuf())

                # self.captcha_item.set_visible(True)
                self.captcha_text_item.set_text("")
                self.captcha_text_item.set_visible(True)
                self.captcha_text_item.grab_focus()
            except (login.LoginError, AttributeError) as exception:
                log.error(str(exception))
                # self.__password_item.set_text('')
                self.__password_item.grab_focus()
                config.remove('login', 'refresh_token')
                config.remove('login', 'access_token')

                self.status.error(
                    ':\n'.join(str(exception).split(': ')) +
                    _(
                        '\n\nIf your previous authenticator has been removed,'
                        '\nopen advanced login bellow and remove the old secrets.'
                    ),
                )

                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
                self.__password_item.grab_focus()
            except binascii.Error:
                self.status.error(_("shared secret is invalid!"))
                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
                self.shared_secret_item.grab_focus()
            except (aiohttp.ClientError, ValueError):
                for count in range(20, 0):
                    self.status.error(_("Check your connection. (server down? blocked?)\nWaiting {}").format(count))
                    await asyncio.sleep(1)

                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
                self.login_button.grab_focus()
            else:
                new_configs = {
                    "account_name": self.username,
                    'steamid': login_data.steamid,
                    'refresh_token': login_data.refresh_token,
                    'access_token': login_data.access_token,
                }

                if self.save_password_item.get_active():
                    encrypted_password = core.utils.encode_password(self.__password)
                    new_configs["password"] = encrypted_password

                for key_, value_ in new_configs.items():
                    config.new("login", key_, value_)

                # steamid = universe.generate_steamid(new_configs['steamid'])
                # _login_session.restore_login(steamid, new_configs['token'], new_configs['token_secure'])

                self.application.main_window.statusbar.clear('steamguard')

                self.has_user_data = True
                self.destroy()
            finally:
                self.save_password_item.set_sensitive(True)
                self.login_button.set_sensitive(True)
                self.set_size_request(400, 100)

            break

    def on_advanced_login_clicked(self, *args: Any) -> None:
        if self.advanced_login_section.props.visible:
            self.identity_secret_item.set_text('')
            self.shared_secret_item.set_text('')
            self.advanced_login_section.set_visible(False)
            self.set_size_request(400, 100)
        else:
            self.advanced_login_section.set_visible(True)
