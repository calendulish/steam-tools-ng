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
import functools
import json
import logging
from typing import Any, Callable, Dict, Optional, Type

import aiohttp
from gi.repository import Gtk, GdkPixbuf
from stlib import authenticator, webapi

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
    ) -> None:
        super().__init__(use_header_bar=True)
        self.session = session
        self.webapi_session = webapi_session
        self.login_data = None

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

        self.adb_section = utils.new_section("adb", "Adb")
        self.content_area.add(self.adb_section.frame)

        self.adb_path_item = utils.new_item("adb_path", _("Adb Path:"), self.adb_section, Gtk.Entry, 0, 0)

        self.user_details_section = utils.new_section("login", _("User Details"))
        self.content_area.add(self.user_details_section.frame)

        self.username_item = utils.new_item("username", _("Username:"), self.user_details_section, Gtk.Entry, 0, 0)
        config_username = config.get("login", "account_name")

        if config_username.value:
            self.username_item.children.set_text(config_username.value)

        self.__password_item = utils.new_item("password", _("Password:"), self.user_details_section, Gtk.Entry, 0, 1)
        self.__password_item.children.set_visibility(False)
        self.__password_item.children.set_invisible_char('*')
        self.__password_item.children.set_placeholder_text(_("It will not be saved"))

        self.code_item = utils.new_item("code", _("Code:"), self.user_details_section, Gtk.Entry, 0, 2)

        self.captcha_gid = -1
        self.captcha_item = utils.new_item("captcha", _("Code:"), self.user_details_section, Gtk.Image, 0, 3)
        self.captcha_text_item = utils.new_item(
            "captcha_text", _("Captcha Text:"), self.user_details_section, Gtk.Entry, 0, 4,
        )

        self.connect('response', lambda dialog, response_id: self.destroy())

    def __fatal_error(self, exception: Type[BaseException]) -> None:
        self.status.error("{}\n\n{}".format(_("IT'S A FATAL ERROR!!! PLEASE, REPORT!!!"), repr(exception)))
        self.status.show_all()
        self.user_details_section.frame.hide()
        self.adb_section.frame.hide()
        self.previous_button.hide()

    def _login_mode_callback(self) -> None:
        if self.combo.get_active() == 0:
            self.prepare_login(self.prepare_add_authenticator, mobile_login=True)
        else:
            self.adb_path()

    def _prepare_login_callback(self, next_stage: Callable[..., Any], mobile_login: bool) -> None:
        self.status.info(_("Waiting Steam Server..."))
        self.user_details_section.frame.hide()
        self.previous_button.hide()
        self.next_button.hide()
        self.status.show_all()
        self.set_size_request(0, 0)

        username = self.username_item.children.get_text()
        password = self.__password_item.children.get_text()
        mail_code = self.code_item.children.get_text()
        captcha_text = self.captcha_text_item.children.get_text()

        task = asyncio.ensure_future(
            self.do_login(username, password, mail_code, captcha_text=captcha_text, mobile_login=mobile_login)
        )

        task.add_done_callback(functools.partial(self._do_login_callback, next_stage, mobile_login))

    def _do_login_callback(
            self,
            next_stage: Callable[..., Any],
            mobile_login: bool,
            future: 'asyncio.Future[Any]',
    ) -> None:
        if future.exception():
            self.__fatal_error(future.exception())
            return

        if future.result():
            next_stage(future.result())
            self.__password_item.children.set_text("")
        else:
            self.next_button.set_label(_("Try Again?"))
            self.next_button.connect("clicked", self._prepare_login_callback, next_stage, mobile_login)
            self.next_button.show()

    def _add_authenticator_callback(
            self,
            login_data: Dict[str, Any],
            deviceid: str,
            future: 'asyncio.Future[Any]',
    ) -> None:
        if future.exception():
            self.__fatal_error(future.exception())
            return

        if future.result():
            self.status.info(_("Write code received by SMS\nand click on 'Add Authenticator' button"))
            self.code_item.label.show()
            self.code_item.children.set_text("")
            self.code_item.children.show()
            self.username_item.label.hide()
            self.username_item.children.hide()
            self.__password_item.label.hide()
            self.__password_item.children.hide()
            self.user_details_section.frame.show()

            self.next_button.set_label(_("Add Authenticator"))

            self.next_button.connect(
                "clicked",
                self.prepare_finalize_add_authenticator,
                login_data,
                future.result(),
                deviceid,
            )

            self.next_button.show()
        else:
            raise AssertionError("No return from `add_authenticator'")

    def _finalize_add_authenticator_callback(
            self,
            login_data: Dict[str, Any],
            auth_data: Dict[str, Any],
            deviceid: str,
            future: 'asyncio.Future[Any]',
    ) -> None:
        if future.exception():
            self.__fatal_error(future.exception())
            return

        if future.result():
            oauth_data = json.loads(future.result()['oauth'])
            self.recovery_code(oauth_data['revocation_code'])
        else:
            self.next_button.set_label(_("Try Again?"))

            self.next_button.connect(
                "clicked",
                self.prepare_finalize_add_authenticator,
                login_data,
                auth_data,
                deviceid
            )

            self.next_button.show()
            self.user_details_section.frame.show()

    def _adb_path_callback(self) -> None:
        self.adb_section.frame.hide()

        if not self.adb_path_item.children.get_text():
            self.status.error(_("Unable to run without a valid adb path."))
            self.next_button.hide()
            self.previous_button.set_label(_("Previous"))
            self.previous_button.connect('clicked', self.adb_path)
            return

        self.previous_button.hide()
        task = asyncio.ensure_future(self.adb_data())
        task.add_done_callback(self._adb_data_callback)

    def _adb_data_callback(self, future: 'asyncio.Future[Any]') -> None:
        if future.exception():
            self.__fatal_error(future.exception())
            return

        if future.result():
            self.previous_button.hide()
            self.next_button.hide()
            self.status.info(_("Loading Data..."))
            data = future.result()
            config.new(*[config.ConfigType("login", key, value) for key, value in data.items()])
            self.status.info(_("Done!"))
            self.header_bar.set_show_close_button(True)
        else:
            self.next_button.set_label(_("Try Again?"))
            self.next_button.connect("clicked", self._adb_path_callback)
            self.next_button.show()

            self.previous_button.set_label(_("Previous"))
            self.previous_button.connect("clicked", self.login_mode)
            self.previous_button.show()

    async def _recovery_code_timer(self, revocation_code: utils.Status) -> None:
        max_value = 60 * 3
        for offset in range(max_value):
            revocation_code.set_level(offset, max_value)
            await asyncio.sleep(0.3)

        self.header_bar.set_show_close_button(True)

    def login_mode(self) -> None:
        self.previous_button.hide()
        self.user_details_section.frame.hide()
        self.adb_section.frame.hide()
        self.set_size_request(0, 0)

        self.status.info(_(
            "Welcome to STNG Setup\n\n"
            "How do you want to log-in?"
        ))

        self.status.show_all()

        self.combo.get_model().clear()
        self.combo.append_text(_("Using Steam Tools NG as Steam Authenticator"))
        self.combo.append_text(_("Using a rooted Android phone and ADB"))
        self.combo.set_active(0)
        self.combo.show()

        self.next_button.set_label(_("Next"))
        self.next_button.connect("clicked", self._login_mode_callback)
        self.next_button.show()

    def adb_path(self) -> None:
        self.combo.hide()
        self.status.info(_("ADB support is currently disabled. Please, go back."))
        self.previous_button.set_label(_("Previous"))
        self.previous_button.connect('clicked', self.login_mode)
        self.previous_button.show()
        self.next_button.hide()
        self.set_size_request(0, 0)

        # FIXME: ADB is unstable, stderr and return codes lies
        return

        self.status.info(_(
            "To automatic get login data using adb, you will need:\n"
            "- A 'rooted' Android phone\n"
            "- adb tool from Google\n"
            "- adb path (set bellow)\n"
            "- USB debugging up and running (on phone)\n"
            "\nIt's a one-time config\n\n"
            "Please, write here the full path where adb is located. E.g:\n\n"
            "Windows: C:\platform-tools\\adb.exe\n"
            "Linux: /usr/bin/adb"
        ))

        self.adb_section.frame.show_all()

        self.next_button.set_label(_("Next"))
        self.next_button.connect("clicked", self._adb_path_callback)
        self.next_button.show()

        self.previous_button.set_label(_("Previous"))
        self.previous_button.connect("clicked", self.login_mode)
        self.previous_button.show()

    async def adb_data(self) -> Optional[Dict[str, Any]]:
        self.status.info(_("Running... Please wait"))
        self.adb_section.frame.hide()
        self.previous_button.hide()
        self.next_button.hide()
        adb_path = self.adb_path_item.children.get_text()

        if not adb_path:
            self.status.error(_("Unable to run without a valid 'adb path'\n\n"))
            return

        try:
            adb = authenticator.AndroidDebugBridge(adb_path)
        except FileNotFoundError:
            self.status.error(_(
                "Unable to find adb in:\n\n{}\n\n"
                "Please, enter a valid 'adb path' and try again."
            ).format(adb_path))
            self.adb_section.frame.show_all()
            return

        try:
            json_data = await adb.get_json(
                'shared_secret',
                'identity_secret',
                'account_name',
                'steamid',
            )
            assert isinstance(json_data, dict), "Invalid json_data"
            json_data['deviceid'] = await adb.get_device_id()
        except authenticator.DeviceError:
            self.status.error(_("No phone connected"))
        except authenticator.RootError:
            self.status.error(_("Unable to switch to root mode"))
        except authenticator.LoginError:
            self.status.error(_("User is not logged-in on Mobile Authenticator"))
        except authenticator.SteamGuardError:
            self.status.error(_("Steam Guard is not enabled"))
        else:
            return json_data

        return None

    def prepare_login(self, next_stage: Callable[..., Any], mobile_login: bool = False) -> None:
        self.status.info(_("Waiting user input..."))
        self.user_details_section.frame.show_all()
        self.combo.hide()
        self.code_item.label.hide()
        self.code_item.children.hide()
        self.captcha_item.label.hide()
        self.captcha_item.children.hide()
        self.captcha_text_item.label.hide()
        self.captcha_text_item.children.hide()

        self.next_button.set_label(_("Next"))
        username = self.username_item.children.get_text()
        password = self.__password_item.children.get_text()
        self.next_button.connect("clicked", self._prepare_login_callback, next_stage, mobile_login)
        self.next_button.show()

        self.previous_button.set_label(_("Previous"))
        self.previous_button.connect("clicked", self.login_mode)
        self.previous_button.show()

    @config.Check("login")
    async def do_login(
            self,
            username: str,
            password: str,
            mail_code: str = '',
            authenticator_code: str = '',
            captcha_gid: int = -1,
            captcha_text: str = '',
            mobile_login: bool = False,
            relogin: bool = False,
            shared_secret: Optional[config.ConfigStr] = None,
    ) -> Optional[Dict[str, Any]]:
        if not username or not password:
            self.status.error(_("Unable to log-in!\nYour username/password is blank."))
            self.user_details_section.frame.show()
            self.previous_button.show()
            return None

        self.status.info(_("Waiting Steam Server..."))
        self.status.show_all()
        self.set_size_request(0, 0)

        login = webapi.Login(self.session, username, password)

        if shared_secret:
            server_time = await self.webapi_session.get_server_time()
            authenticator_code = authenticator.get_code(server_time, shared_secret)
        else:
            log.warning("No shared secret found. Trying to log-in without two-factor authentication.")

        if self.captcha_gid == -1:
            # no reason to send captcha_text if no gid is found
            captcha_text = ''
        else:
            captcha_gid = self.captcha_gid
            # if login fails for some reason, gid must be unset
            # CaptchaError exception will reset it if needed
            self.captcha_gid = -1

        try:
            login_data = await login.do_login(authenticator_code, mail_code, captcha_gid, captcha_text, mobile_login)

            if not login_data['success']:
                raise webapi.LoginError
        except webapi.MailCodeError:
            self.status.info(_("Write code received by email\nand click on 'Try Again?' button"))
            self.code_item.label.show()
            self.code_item.children.set_text("")
            self.code_item.children.show()
            self.username_item.label.hide()
            self.username_item.children.hide()
            self.__password_item.label.hide()
            self.__password_item.children.hide()
            self.user_details_section.frame.show()
            return
        except webapi.TwoFactorCodeError:
            if mobile_login and not relogin:
                self.status.error(_(
                    "Unable to log-in!\n"
                    "You already have a Steam Authenticator active on current account\n\n"
                    "To log-in, you have two options:\n\n"
                    "- Just remove authenticator from your account and use the 'Try Again?' button\n"
                    "    to set STNG as your Steam Authenticator.\n\n"
                    "- Put your shared secret on settings or let us automagically find it using adb\n"
                    "    (settings -> 'get login data using adb' button)\n"

                ))
            else:
                self.status.error(_("Unable to log-in!\nThe authenticator code is invalid!\n"))

            self.previous_button.show()
            return
        except webapi.LoginBlockedError:
            self.status.error(_(
                "Your network is blocked!\n"
                "It'll take some time until unblocked. Please, try again later\n"
            ))
            self.username_item.children.hide()
            self.__password_item.children.hide()
            self.previous_button.hide()
            return
        except webapi.CaptchaError as exception:
            self.status.info(_("Write captcha code as shown bellow\nand click on 'Try Again?' button"))
            self.captcha_gid = exception.captcha_gid

            pixbuf_loader = GdkPixbuf.PixbufLoader()
            pixbuf_loader.write(await login.get_captcha(self.captcha_gid))
            pixbuf_loader.close()
            self.captcha_item.children.set_from_pixbuf(pixbuf_loader.get_pixbuf())

            self.captcha_item.label.show()
            self.captcha_item.children.show()
            self.captcha_text_item.label.show()
            self.captcha_text_item.children.set_text("")
            self.captcha_text_item.children.show()
            self.username_item.label.hide()
            self.username_item.children.hide()
            self.__password_item.label.hide()
            self.__password_item.children.hide()
            self.user_details_section.frame.show()
            return
        except webapi.LoginError as exception:
            log.debug("Login error: %s", exception)
            self.status.error(_(
                "Unable to log-in!\n"
                "Please, check your username/password and try again.\n"
            ))
            self.user_details_section.frame.show()
            self.previous_button.show()
            return
        except aiohttp.ClientConnectionError:
            self.status.error(_("No Connection"))
            self.user_details_section.frame.show()
            self.previous_button.show()
            return

        has_phone: Optional[bool]

        if mobile_login:
            sessionid = await self.webapi_session.get_session_id()

            if await login.has_phone(sessionid):
                has_phone = True
            else:
                has_phone = False
        else:
            has_phone = None

        return {
            **login_data,
            'account_name': username,
            'has_phone': has_phone,
        }

    def prepare_add_authenticator(self, login_data: Dict[str, Any]) -> None:
        if not login_data['has_phone']:
            # Impossible to add an authenticator without a phone
            raise NotImplementedError

        oauth_data = json.loads(login_data['oauth'])
        deviceid = authenticator.generate_device_id(token=oauth_data['oauth_token'])

        task = asyncio.ensure_future(self.add_authenticator(oauth_data, deviceid))
        task.add_done_callback(functools.partial(self._add_authenticator_callback, login_data, deviceid))

    async def add_authenticator(self, oauth_data: Dict[str, Any], deviceid: str) -> Dict[str, Any]:
        self.previous_button.hide()
        self.next_button.hide()
        self.status.info(_("Waiting Steam Server..."))
        self.status.show_all()
        self.set_size_request(0, 0)

        auth_data = await self.webapi_session.add_authenticator(
            oauth_data['steamid'],
            deviceid,
            oauth_data['oauth_token'],
        )

        if auth_data['status'] != 1:
            log.debug(auth_data['status'])
            raise NotImplementedError

        return auth_data

    def prepare_finalize_add_authenticator(
            self,
            login_data: Dict[str, Any],
            auth_data: Dict[str, Any],
            deviceid: str,
    ) -> None:
        task = asyncio.ensure_future(self.finalize_add_authenticator(login_data, auth_data, deviceid))
        callback = functools.partial(self._finalize_add_authenticator_callback, login_data, auth_data, deviceid)
        task.add_done_callback(callback)

    def recovery_code(self, code):
        self.user_details_section.frame.hide()
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
        revocation_code.show()

        self.header_bar.set_show_close_button(False)

        asyncio.ensure_future(functools.partial(self._recovery_code_timer, revocation_code))

    async def finalize_add_authenticator(
            self,
            login_data: Dict[str, Any],
            auth_data: Dict[str, Any],
            deviceid: str,
    ) -> Optional[Dict[str, Any]]:
        self.previous_button.hide()
        self.next_button.hide()
        self.user_details_section.frame.hide()
        self.status.info(_("Waiting Steam Server..."))
        self.status.show_all()
        self.status.set_size_request(0, 0)

        authenticator_code = authenticator.get_code(int(auth_data['server_time']), auth_data['shared_secret'])
        oauth_data = json.loads(login_data['oauth'])

        try:
            complete = await self.webapi_session.finalize_add_authenticator(
                oauth_data['steamid'],
                oauth_data['oauth_token'],
                authenticator_code,
                self.code_item.children.get_text(),
            )
        except webapi.SMSCodeError:
            self.status.info(_("Invalid SMS Code. Please,\ncheck the code and try again."))
            self.code_item.children.set_text("")
            self.code_item.children.show()
            return

        if complete:
            self.status.info(_("Success! Saving..."))

            new_configs = {
                'steamid': oauth_data['steamid'],
                'deviceid': deviceid,
                'token': oauth_data['wgtoken'],
                'token_secure': oauth_data['wgtoken_secure'],
                'oauth_token': oauth_data['oauth_token'],
                'account_name': oauth_data['account_name'],
                'shared_secret': auth_data['shared_secret'],
                'identity_secret': auth_data['identity_secret'],
            }

            config.new(*[
                config.ConfigType("login", key, value) for key, value in new_configs.items()
            ])

            return {**login_data, **auth_data}
        else:
            self.status.error(_("Unable to add a new authenticator"))
            return
