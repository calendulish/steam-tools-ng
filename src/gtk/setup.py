#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2019
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
import codecs
import contextlib
import functools
import logging
import os
from typing import Any, Optional

import aiohttp
from gi.repository import Gtk, Gdk, GdkPixbuf
from stlib import webapi, universe

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class SetupDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Widget,
            session: aiohttp.ClientSession,
            webapi_session: webapi.SteamWebAPI,
            mobile_login: bool = False,
            relogin: bool = False,
            advanced: bool = False,
            add_auth_after_login: bool = False,
            destroy_after_run: bool = False,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.session = session
        self.webapi_session = webapi_session
        self.login_session: Optional[webapi.Login] = None
        self.mobile_login = mobile_login
        self.relogin = relogin
        self.advanced = advanced
        self.add_auth_after_login = add_auth_after_login
        self.destroy_after_run = destroy_after_run

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(True)

        self.previous_button = utils.VariableButton()
        self.header_bar.pack_start(self.previous_button)

        self.next_button = utils.VariableButton()
        self.header_bar.pack_end(self.next_button)

        self.parent_window = parent_window
        self.set_default_size(300, 60)
        self.set_title(_('Magic Box'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status = utils.SimpleStatus()
        self.content_area.add(self.status)

        self.combo = Gtk.ComboBoxText()
        self.content_area.add(self.combo)

        self.user_details_section = utils.Section("login", _("User Details"))
        self.content_area.add(self.user_details_section)

        self.username_item = self.user_details_section.new("account_name", _("Username:"), Gtk.Entry, 0, 0)

        self.__password_item = self.user_details_section.new("_password", _("Password:"), Gtk.Entry, 0, 1)
        self.__password_item.set_visibility(False)
        self.__password_item.set_invisible_char('*')

        self.code_item = self.user_details_section.new("_code", _("Code:"), Gtk.Entry, 0, 2)

        self.captcha_gid = -1
        self.captcha_item = self.user_details_section.new("_captcha", _("Code:"), Gtk.Image, 0, 3)
        self.captcha_text_item = self.user_details_section.new(
            "_captcha_text", _("Captcha Text:"), Gtk.Entry, 0, 4,
        )

        self.save_password_item = self.user_details_section.new("_savepwd", _("Save Password:"), Gtk.CheckButton, 0, 5)
        self.save_password_item.set_active(True)

        self.advanced_settings = utils.Section("login", _("Advanced Settings"))
        self.content_area.add(self.advanced_settings)

        self.identity_secret = self.advanced_settings.new('identity_secret', _("Identity Secret:"), Gtk.Entry, 0, 0)
        self.shared_secret = self.advanced_settings.new('shared_secret', _("Shared Secret:"), Gtk.Entry, 0, 1)

        self.connect('response', lambda dialog, response_id: self.destroy())
        self.connect('key-release-event', self.__on_key_release)
        self.egg_index = 0

    def __on_key_release(self, dialog: Gtk.Dialog, event: Gdk.Event) -> None:
        if event.keyval == Gdk.KEY_Return:
            self.next_button.clicked()

        egg = ['F', 'O', 'R', 'E', 'V', 'E', 'R']

        if self.egg_index == 6 and event.keyval == Gdk.KEY_R:
            self.status.info("""   ## ##
  #  #  #     Amo como ama o amor.
   #   #    Não conheço nenhuma outra razão para amar senão amar.
    # #   Que queres que te diga, além de que te amo,
     #  se o que quero dizer-te é que te amo?
        """)
            self.egg_index = 0
        elif event.keyval == getattr(Gdk, f'KEY_{egg[self.egg_index]}'):
            self.egg_index += 1
        else:
            self.egg_index = 0

    def __fatal_error(self, exception: BaseException) -> None:
        message = "{}\n\n{}".format(_("IT'S A FATAL ERROR!!! PLEASE, REPORT!!!"), repr(exception))
        log.critical(message)
        self.status.error(message)
        self.status._label.set_selectable(True)
        self.status.show()
        self.user_details_section.hide()
        self.advanced_settings.hide()
        self.previous_button.hide()

    def __reset_and_restart(self) -> None:
        self.status.info(_("Removing old config files..."))
        self.user_details_section.hide()
        self.advanced_settings.hide()
        self.previous_button.hide()
        self.next_button.hide()

        with contextlib.suppress(FileNotFoundError):
            os.remove(config.config_file)

        config.parser.clear()
        config.init()
        self.status.info(_("Restarting Magic Box..."))
        # destroy that dialog after 5 seconds (time for main application loop)
        # setup dialog will be automatically reopened with new parameters
        asyncio.get_event_loop().call_later(5, self.destroy)

    def _login_mode_callback(self) -> None:
        if self.combo.get_active() == 0:
            self.add_auth_after_login = True
            self.mobile_login = True
            self.advanced = False
            self.destroy_after_run = False
            self.prepare_login()
        else:
            self.advanced = True
            self.destroy_after_run = True
            self.add_auth_after_login = False
            self.mobile_login = False
            self.prepare_login()

    def _prepare_login_callback(self) -> None:
        self.status.info(_("Waiting Steam Server..."))
        self.advanced_settings.hide()
        self.user_details_section.hide()
        self.previous_button.hide()
        self.next_button.set_label(_("Try Again?"))
        self.next_button.connect("clicked", self._prepare_login_callback)
        self.next_button.hide()
        self.status.show()
        self.set_size_request(0, 0)

        mail_code = self.code_item.get_text()
        username = self.username_item.get_text()
        __password = self.__password_item.get_text()

        self.login_session = webapi.Login(self.session, self.webapi_session, username, __password)
        kwargs = {'emailauth': mail_code, 'mobile_login': self.mobile_login}

        # no reason to send captcha_text if no gid is found
        if self.captcha_gid != -1:
            kwargs['captcha_text'] = self.captcha_text_item.get_text()
            kwargs['captcha_gid'] = self.captcha_gid
            # if login fails for some reason, gid must be unset
            # CaptchaError exception will reset it if needed
            self.captcha_gid = -1

        if not username or not __password:
            self.status.error(_("Unable to log-in!\nUsername or password is blank."))
            self.user_details_section.show()
            self.previous_button.show()
            self.next_button.show()

            if self.advanced:
                self.advanced_settings.show()
            else:
                self.advanced_settings.hide()

            return None

        shared_secret = self.shared_secret.get_text()
        # it's required for openid login
        identity_secret = self.identity_secret.get_text()

        if not shared_secret or not identity_secret:
            if self.advanced or self.relogin:
                self.status.error(_("Unable to log-in!\nShared secret or Identity secret is blank."))
                self.user_details_section.show()
                self.advanced_settings.show()
                self.previous_button.show()
                self.next_button.show()
                return None

            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))

        kwargs['shared_secret'] = shared_secret

        self.status.info(_("Waiting Steam Server..."))
        self.status.show()
        self.set_size_request(0, 0)

        # log.trace(f'login: {kwargs}')
        task = asyncio.ensure_future(self.login_session.do_login(**kwargs))
        task.add_done_callback(self._do_login_callback)

        return None

    def _do_login_callback(self, future: 'asyncio.Future[Any]') -> None:
        self.next_button.set_label(_("Try Again?"))
        self.next_button.connect("clicked", self._prepare_login_callback)

        if future.exception():
            self.next_button.show()

            # noinspection PyBroadException
            try:
                raise future.exception()
            except webapi.MailCodeError:
                self.status.info(_("Write code received by email\nand click on 'Try Again?' button"))
                self.captcha_item.hide()
                self.captcha_text_item.hide()
                self.code_item.set_text("")
                self.code_item.show()
                self.username_item.hide()
                self.__password_item.hide()
                self.save_password_item.hide()
                self.user_details_section.show()
            except webapi.TwoFactorCodeError:
                if self.mobile_login and not self.relogin:
                    self.status.error(_(
                        "Unable to log-in!\n"
                        "You already have a Steam Authenticator active on current account.\n\n"
                        "To log-in, remove authenticator from your account and use the 'Try Again?' button.\n"
                        "(STNG will add itself as Steam Authenticator in your account)\n"
                    ))
                else:
                    self.status.error(_("Unable to log-in!\nThe secret keys are invalid!\n"))

                self.previous_button.show()
            except webapi.LoginBlockedError:
                self.status.error(_(
                    "Your network is blocked!\n"
                    "It'll take some time until unblocked. Please, try again later\n"
                ))
                self.username_item.hide()
                self.__password_item.hide()
                self.save_password_item.hide()
                self.previous_button.hide()
            except webapi.CaptchaError as exception:
                self.status.info(_("Write captcha code as shown bellow\nand click on 'Try Again?' button"))
                self.captcha_gid = exception.captcha_gid

                pixbuf_loader = GdkPixbuf.PixbufLoader()
                pixbuf_loader.write(exception.captcha)
                pixbuf_loader.close()
                self.captcha_item.set_from_pixbuf(pixbuf_loader.get_pixbuf())

                self.captcha_item.show()
                self.captcha_text_item.set_text("")
                self.captcha_text_item.show()
                self.username_item.hide()
                self.__password_item.hide()
                self.save_password_item.hide()
                self.user_details_section.show()
            except webapi.LoginError as exception:
                log.debug("Login error: %s", exception)
                self.captcha_item.hide()
                self.captcha_text_item.hide()
                self.username_item.show()
                self.__password_item.set_text('')
                self.__password_item.show()
                self.save_password_item.show()

                self.status.error(_(
                    "Unable to log-in!\n"
                    "Please, check your username/password and try again.\n"
                ))

                if self.advanced:
                    self.advanced_settings.show()
                else:
                    self.advanced_settings.hide()
                    self.status.append_link(
                        _("click here"),
                        self.__reset_and_restart,
                        _("You removed the authenticator? If yes, "),
                    )

                self.user_details_section.show()
                self.previous_button.show()
            except aiohttp.ClientError:
                self.status.error(_("No Connection"))
                self.user_details_section.show()
                self.previous_button.show()
            except Exception as exception:
                log.exception(str(exception))
                self.__fatal_error(exception)

            return None

        if future.result():
            login_data = future.result()

            if self.add_auth_after_login:
                self.prepare_add_authenticator(login_data)
            else:
                args = [login_data, self.relogin]

                if self.save_password_item.get_active():
                    args.append(self.__password_item.get_text().encode())

                config.save_login_data(*args)

                if self.advanced:
                    config.new("login", "identity_secret", self.identity_secret.get_text())
                    config.new("login", "shared_secret", self.shared_secret.get_text())

            if self.destroy_after_run:
                self.destroy()
        else:
            self.next_button.show()

        return None

    def _add_authenticator_callback(self, future: 'asyncio.Future[Any]') -> None:
        if future.exception():
            # noinspection PyBroadException
            try:
                raise future.exception()
            except aiohttp.ClientError:
                self.status.error(_("No Connection"))
                self.previous_button.show()
            except Exception as exception:
                log.exception(str(exception))
                self.__fatal_error(exception)

            return None

        if future.result():
            self.status.info(_("Write code received by SMS\nand click on 'Add Authenticator' button"))
            self.captcha_item.hide()
            self.captcha_text_item.hide()
            self.code_item.set_text("")
            self.code_item.show()
            self.username_item.hide()
            self.__password_item.hide()
            self.save_password_item.hide()
            self.user_details_section.show()

            self.next_button.set_label(_("Add Authenticator"))

            self.next_button.connect(
                "clicked",
                self.prepare_finalize_add_authenticator,
                future.result(),
            )

            self.next_button.show()
        else:
            # FIXME
            raise AssertionError("No return from `add_authenticator'")

        return None

    def _finalize_add_authenticator_callback(
            self,
            login_data: webapi.LoginData,
            future: 'asyncio.Future[Any]',
    ) -> None:
        self.next_button.set_label(_("Try Again?"))

        self.next_button.connect(
            "clicked",
            self.prepare_finalize_add_authenticator,
            login_data,
        )

        if future.exception():
            # noinspection PyBroadException
            try:
                raise future.exception()
            except webapi.SMSCodeError:
                self.status.info(_("Invalid SMS Code. Please,\ncheck the code and try again."))
                self.code_item.set_text("")
                self.code_item.show()
                self.next_button.show()
                self.user_details_section.show()
            except aiohttp.ClientError:
                self.status.error(_("No Connection"))
                self.code_item.set_text("")
                self.code_item.show()
                self.next_button.show()
                self.user_details_section.show()
            except Exception as exception:
                log.exception(str(exception))
                self.__fatal_error(exception)

            return None

        if future.result():
            args = [login_data, False]

            if self.save_password_item.get_active():
                args.append(self.__password_item.get_text().encode())

            config.save_login_data(*args)
            self.recovery_code(login_data.auth['revocation_code'])
        else:
            self.status.error(_("Unable to add a new authenticator"))
            self.next_button.show()
            self.user_details_section.show()

        return None

    async def _recovery_code_timer(self, revocation_code: utils.Status) -> None:
        max_value = 30 * 3
        for offset in range(max_value):
            revocation_code.set_level(offset, max_value)
            await asyncio.sleep(0.3)

        self.header_bar.set_show_close_button(True)

    def login_mode(self) -> None:
        self.previous_button.hide()
        self.user_details_section.hide()
        self.advanced_settings.hide()
        self.set_size_request(0, 0)

        self.status.info(_(
            "Welcome to STNG Setup\n\n"
            "How do you want to log-in?"
        ))

        self.status.show()

        self.combo.get_model().clear()
        self.combo.append_text(_("Use STNG as Steam Authenticator"))
        self.combo.append_text(_("Use custom secrets (advanced users only!)"))
        self.combo.set_active(0)
        self.combo.show()

        self.next_button.set_label(_("Next"))
        self.next_button.connect("clicked", self._login_mode_callback)
        self.next_button.show()

    def prepare_login(self, encrypted_password: Optional[str] = None) -> None:
        self.status.info(_("Waiting user input..."))

        self.combo.hide()
        self.user_details_section.show_all()
        self.code_item.hide()
        self.captcha_item.hide()
        self.captcha_text_item.hide()

        if self.advanced:
            self.advanced_settings.show_all()
        else:
            self.advanced_settings.hide()

        self.next_button.set_label(_("Next"))
        self.next_button.connect("clicked", self._prepare_login_callback)
        self.next_button.show()

        self.previous_button.set_label(_("Previous"))
        self.previous_button.connect("clicked", self.login_mode)
        self.previous_button.show()

        if encrypted_password:
            # Just for curious people. It's not even safe.
            key = codecs.decode(encrypted_password, 'rot13')
            raw = codecs.decode(key.encode(), 'base64')
            self.__password_item.set_text(raw.decode())
            self._prepare_login_callback()

        return None

    def prepare_add_authenticator(self, login_data: webapi.LoginData) -> None:
        if not login_data.has_phone:
            # FIXME: Impossible to add an authenticator without a phone
            raise NotImplementedError

        deviceid = universe.generate_device_id(token=login_data.oauth['oauth_token'])
        config.new("login", "deviceid", deviceid)

        self.previous_button.hide()
        self.next_button.hide()
        self.status.info(_("Waiting Steam Server..."))
        self.status.show()
        self.set_size_request(0, 0)

        task = asyncio.ensure_future(self.webapi_session.add_authenticator(login_data, deviceid))
        task.add_done_callback(self._add_authenticator_callback)

    def prepare_finalize_add_authenticator(
            self,
            login_data: webapi.LoginData,
    ) -> None:
        self.previous_button.hide()
        self.next_button.hide()
        self.user_details_section.hide()
        self.status.info(_("Waiting Steam Server..."))
        self.status.show()
        self.status.set_size_request(0, 0)

        task = asyncio.ensure_future(
            self.webapi_session.finalize_add_authenticator(
                login_data,
                self.code_item.get_text(),
            )
        )
        callback = functools.partial(self._finalize_add_authenticator_callback, login_data)
        task.add_done_callback(callback)

    def recovery_code(self, code: str) -> None:
        self.user_details_section.hide()
        self.previous_button.hide()
        self.status.info(_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ))

        revocation_code = utils.Status(6, _("Recovery Code"))
        revocation_code.set_current(code)
        revocation_code.set_info('')
        self.content_area.add(revocation_code)
        revocation_code.show_all()

        self.header_bar.set_show_close_button(False)

        asyncio.ensure_future(self._recovery_code_timer(revocation_code))
