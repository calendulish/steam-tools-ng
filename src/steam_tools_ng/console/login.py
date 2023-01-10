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
import aiohttp
import asyncio
import binascii
import codecs
import getpass
import logging
import tempfile
from typing import TYPE_CHECKING

from stlib import login, universe
from . import utils
from .. import i18n, config

if TYPE_CHECKING:
    from . import cli

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class Login:
    def __init__(self, cli_: 'cli.SteamToolsNG', mobile_login: bool = True) -> None:
        self.cli = cli_
        self.mobile_login = mobile_login
        self.has_user_data = False
        self.captcha_gid = -1
        self._username = ''
        self.__password = ''
        self._mail_code = ''
        self._steam_code = ''
        self._captcha_text = ''

    @property
    def username(self) -> str:
        return self._username

    def set_password(self, encrypted_password: str) -> None:
        try:
            key = codecs.decode(encrypted_password, 'rot13')
            raw = codecs.decode(key.encode(), 'base64')
            self.__password = raw.decode()
        except (binascii.Error, UnicodeError, TypeError):
            log.warning(_("Password decode failed. Trying RAW."))
            self.__password = encrypted_password

    @property
    def mail_code(self) -> str:
        return self._mail_code

    @property
    def steam_code(self) -> str:
        return self._steam_code

    @property
    def captcha_text(self) -> str:
        return self._captcha_text

    @property
    def shared_secret(self) -> str:
        return config.parser.get("login", "shared_secret")

    @property
    def identity_secret(self) -> str:
        return config.parser.get("login", "identity_secret")

    async def do_login(self, auto: bool) -> None:
        utils.set_console(info=_("Retrieving user data"))

        if auto:
            self._username = config.parser.get("login", "account_name")
            encrypted_password = config.parser.get("login", "password")
            self.set_password(encrypted_password)

        if not self.username or not self.__password:
            user_input = utils.safe_input(_("Please, write your username"))
            assert isinstance(user_input, str), "Safe input is returning bool when it should return str"
            config.new("login", "account_name", user_input)
            self._username = user_input

            self.__password = getpass.getpass(_("Please, write your password (IT'S HIDDEN, and will be encrypted)"))
            password_key = codecs.encode(self.__password.encode(), 'base64')
            encrypted_password = codecs.encode(password_key.decode(), 'rot13')
            config.new("login", "password", encrypted_password)

        _login_session = login.Login.get_session(0)
        _login_session.username = self.username
        _login_session.password = self.__password

        kwargs = {'emailauth': self.mail_code, 'mobile_login': self.mobile_login}

        # no reason to send captcha_text if no gid is found
        if self.captcha_gid != -1:
            kwargs['captcha_text'] = self.captcha_text
            kwargs['captcha_gid'] = self.captcha_gid
            # if login fails for any reason, gid must be unset
            # CaptchaError exception will reset it if needed
            self.captcha_gid = -1

        if not self.shared_secret or not self.identity_secret:
            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))
            # self.code_item.show()

        kwargs['shared_secret'] = self.shared_secret
        kwargs['authenticator_code'] = self.steam_code

        utils.set_console(info=_("Logging in"))
        try_count = 3

        while True:
            try:
                login_data = await _login_session.do_login(**kwargs)
            except login.MailCodeError:
                user_input = utils.safe_input(_("Write code received by email"))
                assert isinstance(user_input, str), "safe_input is returning bool when it should return str"
                self._mail_code = user_input
                await self.do_login(True)
            except login.TwoFactorCodeError:
                if self.shared_secret:
                    if try_count > 0:
                        log.warning(_("Retrying login in 10 seconds"))
                        await asyncio.sleep(10)
                        try_count -= 1
                        continue
                    else:
                        log.error(_("shared secret is invalid!"))
                        self.cli.on_quit()

                user_input = utils.safe_input(_("Write Steam Code"))
                assert isinstance(user_input, str), "safe_input is returning bool when it should return str"
                self._steam_code = user_input
                await self.do_login(True)
            except login.LoginBlockedError:
                log.error(_(
                    "Your network is blocked!\n"
                    "It'll take some time until unblocked. Please, try again later\n"
                ))
                self.cli.on_quit()
            except login.CaptchaError as exception:
                self.captcha_gid = exception.captcha_gid

                utils.set_console(info=_("Steam server is requesting a captcha code."))

                with tempfile.NamedTemporaryFile(buffering=0, prefix='stng_', suffix='.captcha.png') as temp_file:
                    temp_file.write(exception.captcha)
                    temp_file.flush()

                    user_input = utils.safe_input(
                        _("Open {} in an image view and write captcha code that it shows").format(temp_file.name),
                    )

                assert isinstance(user_input, str)
                self._captcha_text = user_input
                await self.do_login(True)
            except binascii.Error:
                log.error(_("shared secret is invalid!"))
                self.cli.on_quit()
            except login.LoginError as exception:
                log.error(str(exception))
                config.remove('login', 'token')
                config.remove('login', 'token_secure')
                config.remove('login', 'oauth_token')
                self.cli.on_quit()
            except (aiohttp.ClientError, ValueError):
                log.error(_("Check your connection. (server down?)"))
                await asyncio.sleep(15)
                continue
            else:
                new_configs = {}

                if "shared_secret" in login_data.auth:
                    new_configs["shared_secret"] = login_data.auth["shared_secret"]
                elif self.shared_secret:
                    new_configs["shared_secret"] = self.shared_secret

                if "identity_secret" in login_data.auth:
                    new_configs['identity_secret'] = login_data.auth['identity_secret']
                elif self.identity_secret:
                    new_configs["identity_secret"] = self.identity_secret

                if login_data.oauth:
                    new_configs['steamid'] = login_data.oauth['steamid']
                    new_configs['token'] = login_data.oauth['wgtoken']
                    new_configs['token_secure'] = login_data.oauth['wgtoken_secure']
                    new_configs['oauth_token'] = login_data.oauth['oauth_token']
                else:
                    new_configs['steamid'] = login_data.auth['transfer_parameters']['steamid']
                    new_configs['token'] = login_data.auth['transfer_parameters']['webcookie']
                    new_configs['token_secure'] = login_data.auth['transfer_parameters']['token_secure']

                for key, value in new_configs.items():
                    config.new("login", key, value)

                steamid = universe.generate_steamid(new_configs['steamid'])
                _login_session.restore_login(steamid, new_configs['token'], new_configs['token_secure'])
                self.has_user_data = True

            break
