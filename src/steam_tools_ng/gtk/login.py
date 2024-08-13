#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2024
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
from typing import Any

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
        self.auth_code_type = None

        self.login_button = utils.AsyncButton()
        self.login_button.set_label(_("Log-in"))
        self.login_button.connect("clicked", self.on_login_button_clicked)
        self.header_bar.pack_end(self.login_button)
        self.set_title(_('Login'))

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.5)
        self.progress_bar.set_visible(False)
        self.content_grid.attach(self.progress_bar, 0, 1, 1, 1)

        self.user_details_section = utils.Section("login")
        self.content_grid.attach(self.user_details_section, 0, 2, 1, 1)

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

        self.no_steamguard = utils.ClickableLabel()
        self.no_steamguard.set_markup(utils.markup(_("I Removed my authenticator"), font_size='small', color='blue'))
        self.no_steamguard.set_halign(Gtk.Align.END)
        self.no_steamguard.set_margin_end(10)
        self.no_steamguard.set_margin_bottom(10)
        self.no_steamguard.connect("clicked", self.on_no_steamguard_clicked)
        self.content_grid.attach(self.no_steamguard, 0, 3, 1, 1)

        self.connect('destroy', self.on_quit)
        self.connect('close-request', self.on_quit)

        self.auth_code_item.set_visible(False)

        self.check_login_availability()
        self.login_session = login.Login.get_session(0)
        self.poll_task: asyncio.Task[Any] | None = None
        self.poll_cancelled = False

    async def poll_login(self, steamid: int, client_id: str, request_id: str) -> None:
        while True:
            login_data = await self.login_session.poll_login(steamid, client_id, request_id)

            if login_data:
                self.login_button.set_sensitive(False)
                break

            if self.poll_cancelled:
                return None

            self.progress_bar.pulse()
            await asyncio.sleep(2)

        self.save_login_data(login_data)
        self.application.main_window.statusbar.clear('steamguard')
        self.has_user_data = True
        self.destroy()

    def save_login_data(self, login_data: login.LoginData) -> None:
        new_configs = {
            "account_name": self.username,
            "steamid": login_data.steamid,
        }

        if self.save_password_item.get_active():
            encrypted_password = core.utils.encode_password(self.__password)
            new_configs["password"] = encrypted_password

        for key_, value_ in new_configs.items():
            config.new("login", key_, value_)

        self.login_session.http_session.cookie_jar.save(config.cookies_file)

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
        return config.parser.get("login", "shared_secret")

    @property
    def identity_secret(self) -> str:
        return config.parser.get("login", "identity_secret")

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
            auth_code_type: AuthCodeType | None = AuthCodeType.device,
    ) -> None:
        self.status.info(_("Retrieving user data"))
        self.application.main_window.statusbar.set_warning("steamguard", _("Not logged in"))
        self.username_item.set_sensitive(False)
        self.__password_item.set_sensitive(False)
        self.save_password_item.set_sensitive(False)
        self.login_button.set_sensitive(False)
        self.progress_bar.set_visible(False)

        if self.poll_task:
            log.info(_("Cancelling current login poll."))
            self.poll_cancelled = True

            # wait poll be cancelled
            await self.poll_task

            self.poll_cancelled = False
            self.poll_task = None

        self.login_session.http_session.cookie_jar.clear()
        self.login_session.username = self.username
        self.login_session.password = self.__password

        if not self.shared_secret:
            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))
            # self.code_item.set_visible(True)

        self.status.info(_("Logging in"))
        self.auth_code_item.set_visible(False)

        try_count = 3

        while True:
            try:
                login_data = await self.login_session.do_login(
                    self.shared_secret,
                    self.auth_code or auth_code,
                    self.auth_code_type or auth_code_type,
                    self.mobile_login,
                )
            except login.MailCodeError:
                self.status.info(_("Write code received by email\nand click on 'Log-in' button"))
                self.auth_code_item.set_text("")
                self.auth_code_item.set_visible(True)
                self.auth_code_item.grab_focus()
                self.auth_code_type = AuthCodeType.email
            except login.LoginBlockedError:
                self.status.error(_(
                    "Your network is blocked!\n"
                    "It'll take some time until unblocked. Please, try again later\n"
                ))
                self.user_details_section.set_visible(False)
                self.no_steamguard.set_visible(False)
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
            except login.TwoFactorCodeError as exception:
                self.status.error(_("Confirm the login on your mobile device or write the steam code\nWaiting..."))
                self.progress_bar.set_visible(True)

                self.poll_task = asyncio.create_task(
                    self.poll_login(
                        exception.steamid,
                        exception.client_id,
                        exception.request_id,
                    )
                )

                self.auth_code_item.set_text("")
                self.auth_code_item.set_visible(True)
                self.auth_code_item.grab_focus()
                self.auth_code_type = AuthCodeType.device
            except binascii.Error:
                self.status.error(_("shared secret is invalid!"))
                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
            except AttributeError as exception:
                log.error(str(exception))
                self.status.error(':\n'.join(str(exception).split(': ')))

                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
                self.__password_item.grab_focus()
                break
            except login.LoginError as exception:
                if try_count > 0:
                    for count in range(10, 0):
                        self.status.info(_("Retrying login in {} seconds ({} left)").format(count, try_count))
                        await asyncio.sleep(1)

                    try_count -= 1
                    continue
                else:
                    log.error(str(exception))
                    self.status.error(':\n'.join(str(exception).split(': ')))

                    self.username_item.set_sensitive(True)
                    self.__password_item.set_sensitive(True)
                    self.__password_item.grab_focus()
                    break
            except (aiohttp.ClientError, ValueError):
                for count in range(20, 0):
                    self.status.error(_("Check your connection. (server down? blocked?)\nWaiting {}").format(count))
                    await asyncio.sleep(1)

                self.username_item.set_sensitive(True)
                self.__password_item.set_sensitive(True)
                self.login_button.grab_focus()
            else:
                self.save_login_data(login_data)
                self.application.main_window.statusbar.clear('steamguard')
                self.has_user_data = True
                self.destroy()
            finally:
                self.save_password_item.set_sensitive(True)
                self.login_button.set_sensitive(True)
                self.set_size_request(400, 100)

            break

    def on_no_steamguard_clicked(self, *args: Any) -> None:
        self.status.info(_("Disabling authenticator..."))
        self.auth_code_item.set_visible(False)
        self.login_button.set_sensitive(False)

        config.remove("login", "identity_secret")
        config.remove("login", "shared_secret")
        self.login_session.http_session.cookie_jar.clear()

        self.status.info(_("Authenticator disabled!\nTry to login again."))
        self.login_button.set_sensitive(True)
