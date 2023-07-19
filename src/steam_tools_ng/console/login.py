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
import getpass
import logging
from typing import TYPE_CHECKING, Optional

import aiohttp

from stlib import login
from stlib.login import AuthCodeType
from . import utils
from .. import i18n, config, core

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
        self._username = ''
        self.__password = ''

    @property
    def username(self) -> str:
        return self._username

    def set_password(self, encrypted_password: str) -> None:
        try:
            __password = core.utils.decode_password(encrypted_password)
            self.__password = __password
        except (binascii.Error, UnicodeError, TypeError):
            log.warning(_("Password decode failed. Trying RAW."))
            self.__password = encrypted_password

    @property
    def shared_secret(self) -> str:
        return config.parser.get("login", "shared_secret")

    @property
    def identity_secret(self) -> str:
        return config.parser.get("login", "identity_secret")

    async def do_login(
            self,
            auto: bool,
            auth_code: str = '',
            auth_code_type: Optional[AuthCodeType] = AuthCodeType.device,
    ) -> None:
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
            encrypted_password = core.utils.encode_password(self.__password)
            config.new("login", "password", encrypted_password)

        _login_session = login.Login.get_session(0)
        _login_session.username = self.username
        _login_session.password = self.__password

        if not self.shared_secret:
            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))

        utils.set_console(info=_("Logging in"))
        try_count = 3

        while True:
            try:
                login_data = await _login_session.do_login(
                    self.shared_secret,
                    auth_code,
                    auth_code_type,
                    self.mobile_login,
                )
            except login.MailCodeError:
                user_input = utils.safe_input(_("Write code received by email"))
                assert isinstance(user_input, str), "safe_input is returning bool when it should return str"
                await self.do_login(True, user_input, AuthCodeType.email)
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
                await self.do_login(True, user_input)
            except login.LoginBlockedError:
                log.error(_(
                    "Your network is blocked!\n"
                    "It'll take some time until unblocked. Please, try again later\n"
                ))
                self.cli.on_quit()
            except login.CaptchaError as exception:
                utils.set_console(info=_("Steam server is requesting a captcha code."))
                # TODO: Captcha gid?? (where did you go? where did you go?)
                # with tempfile.NamedTemporaryFile(buffering=0, prefix='stng_', suffix='.captcha.png') as temp_file:
                #    temp_file.write(exception.captcha)
                #    temp_file.flush()
                user_input = utils.safe_input(_("Write Captcha Code"))
                assert isinstance(user_input, str)
                await self.do_login(True, user_input, AuthCodeType.machine)
            except binascii.Error:
                log.error(_("shared secret is invalid!"))
                self.cli.on_quit()
            except login.LoginError as exception:
                log.error(str(exception))
                config.remove('login', 'refresh_token')
                config.remove('login', 'access_token')
                log.warning(_(
                    "If your previous authenticator has been removed,"
                    "\nopen your config file and remove the old secrets."
                ))
                self.cli.on_quit()
            except (aiohttp.ClientError, ValueError):
                log.error(_("Check your connection. (server down?)"))
                await asyncio.sleep(15)
                continue
            else:
                new_configs = {
                    "account_name": self.username,
                    'steamid': login_data.steamid,
                    'refresh_token': login_data.refresh_token,
                    'access_token': login_data.access_token,
                }

                for key, value in new_configs.items():
                    config.new("login", key, value)

                # steamid = universe.generate_steamid(new_configs['steamid'])
                # _login_session.restore_login(steamid, new_configs['token'], new_configs['token_secure'])
                self.has_user_data = True

            break
