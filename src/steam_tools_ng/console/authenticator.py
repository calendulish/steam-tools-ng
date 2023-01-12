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
import logging
import sys
from typing import Optional, TYPE_CHECKING

from stlib import universe, webapi, login
from . import utils
from .. import i18n, config

if TYPE_CHECKING:
    from . import cli

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class NewAuthenticator:
    def __init__(self, cli_: 'cli.SteamToolsNG') -> None:
        self.cli = cli_
        self.webapi_session = webapi.SteamWebAPI.get_session(0)
        self._login_data: Optional[login.LoginData] = None
        self._sms_code = ''

    @property
    def sms_code(self) -> str:
        return self._sms_code

    @property
    def oauth_token(self) -> str:
        return config.parser.get("login", "oauth_token")

    @property
    def steamid(self) -> Optional[universe.SteamId]:
        steamid = config.parser.getint("login", "steamid")

        if steamid:
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

        return None

    async def add_authenticator(self) -> None:
        utils.set_console(info=_("Retrieving user data"))

        if not self.oauth_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            self.cli.on_quit(1)

        assert isinstance(self.steamid, universe.SteamId)
        oauth = {'steamid': self.steamid.id64, 'oauth_token': self.oauth_token}
        login_data = login.LoginData(auth={}, oauth=oauth)

        if not self._login_data or not self.sms_code:
            try:
                self._login_data = await self.webapi_session.new_authenticator(self.steamid, self.oauth_token)
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
                log.critical("%s: %s", type(exception).__name__, str(exception))
                self.cli.on_quit(1)
            else:
                user_input = utils.safe_input(_("Enter the code received by SMS"))
                assert isinstance(user_input, str)
                self._sms_code = user_input

        utils.set_console(info=_("Adding authenticator"))
        assert isinstance(self._login_data, login.LoginData)

        try:
            await self.webapi_session.add_authenticator(
                self.steamid,
                self.oauth_token,
                self._login_data.auth['shared_secret'],
                self.sms_code,
            )
        except webapi.SMSCodeError:
            log.error(_("Invalid SMS Code. Please, check the code and try again."))
            self.cli.on_quit(1)
        except aiohttp.ClientError:
            log.error(_("Check your connection. (server down?)"))
            self.cli.on_quit(1)
        except Exception as exception:
            log.critical("%s: %s", type(exception).__name__, str(exception))
            self.cli.on_quit(1)

        utils.set_console(info=_("Saving new secrets"))
        config.new("login", "shared_secret", self._login_data.auth['shared_secret'])
        config.new("login", "identity_secret", self._login_data.auth['identity_secret'])
        config.new("steamguard", "enable", True)
        config.new("confirmations", "enable", True)

        utils.set_console(info=_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ))

        revocation_code = self._login_data.auth['revocation_code']
        utils.set_console(info=revocation_code)
        await asyncio.sleep(30)
