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
import sys

import aiohttp
from stlib import universe, webapi, login

from . import utils
from .. import i18n, config

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class NewAuthenticator:
    def __init__(self, cli_: 'SteamToolsNG') -> None:
        self.cli = cli_
        self._login_data = None
        self._sms_code = ''

    @property
    def sms_code(self) -> str:
        return self._sms_code

    @property
    def oauth_token(self) -> None:
        return config.parser.get("login", "oauth_token")

    @property
    def steamid(self) -> None:
        return config.parser.get("login", "steamid")

    async def add_authenticator(self) -> None:
        log.info(_("Retrieving user data"))

        if not self.oauth_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            self.cli.on_quit(1)

        deviceid = universe.generate_device_id(token=self.oauth_token)
        oauth = {'steamid': self.steamid, 'oauth_token': self.oauth_token}
        login_data = login.LoginData(auth={}, oauth=oauth)

        if not self._login_data or not self.sms_code:
            try:
                self._login_data = await self.cli.webapi_session.add_authenticator(login_data, deviceid)
            except aiohttp.ClientError:
                log.error(_("Check your connection. (server down?)"))
                self.cli.on_quit(1)
            except webapi.AuthenticatorExists:
                log.error(_(
                    "There's already an authenticator active for that account.\n"
                    "Remove your current steam authenticator and try again."
                ))
                self.cli.on_quit()
            except webapi.PhoneNotRegistered:
                log.error(_(
                    "You must have a phone registered on your steam account to proceed.\n"
                    "Go to your Steam Account Settings, add a Phone Number, and try again."
                ))
                self.cli.on_quit(1)
            except NotImplementedError as exception:
                log.critical(f"{type(exception).__name__}: {str(exception)}")
                self.cli.on_quit(1)
            else:
                user_input = utils.safe_input(_("Enter the code received by SMS"))
                self._sms_code = user_input

        log.info(_("Adding authenticator"))

        try:
            await self.cli.webapi_session.finalize_add_authenticator(
                self._login_data, self.sms_code, time_offset=self.cli.time_offset,
            )
        except webapi.SMSCodeError:
            log.error(_("Invalid SMS Code. Please, check the code and try again."))
            self.cli.on_quit(1)
        except aiohttp.ClientError:
            log.error(_("Check your connection. (server down?)"))
            self.cli.on_quit(1)
        except Exception as exception:
            log.critical(f"{type(exception).__name__}: {str(exception)}")
            self.cli.on_quit(1)

        log.info(_("Saving new secrets"))
        config.new("login", "shared_secret", self._login_data.auth['shared_secret'])
        config.new("login", "identity_secret", self._login_data.auth['identity_secret'])
        config.new("plugins", "steamguard", True)
        config.new("plugins", "confirmations", True)

        log.info(_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ))

        revocation_code = self._login_data.auth['revocation_code']
        log.info(revocation_code)
        await asyncio.sleep(30)
