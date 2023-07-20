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
import logging
import sys
from typing import Optional, TYPE_CHECKING

import aiohttp

from stlib import universe, webapi
from . import utils
from .. import i18n, config

if TYPE_CHECKING:
    from . import cli

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class ManageAuthenticator:
    def __init__(self, cli_: 'cli.SteamToolsNG') -> None:
        self.cli = cli_
        self.webapi_session = webapi.SteamWebAPI.get_session(0)
        self.authenticator_data: Optional[webapi.AuthenticatorData] = None
        self._sms_code = ''

    @property
    def sms_code(self) -> str:
        return self._sms_code

    @property
    def access_token(self) -> str:
        return config.parser.get("login", "access_token")

    @property
    def steamid(self) -> Optional[universe.SteamId]:
        if steamid := config.parser.getint("login", "steamid"):
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

        return None

    async def add_authenticator(self) -> None:
        utils.set_console(info=_("Retrieving user data"))

        if not self.access_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            self.cli.on_quit(1)

        assert isinstance(self.steamid, universe.SteamId)

        if not self.authenticator_data or not self.sms_code:
            try:
                self.authenticator_data = await self.webapi_session.new_authenticator(self.steamid, self.access_token)
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

        try:
            await self.webapi_session.add_authenticator(
                self.steamid,
                self.access_token,
                self.authenticator_data.shared_secret,
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
        config.new("login", "shared_secret", self.authenticator_data.shared_secret)
        config.new("login", "identity_secret", self.authenticator_data.identity_secret)
        config.new("steamguard", "enable", True)
        config.new("confirmations", "enable", True)

        utils.set_console(info=_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ))

        utils.set_console(info=self.authenticator_data.revocation_code)
        await asyncio.sleep(30)

    async def remove_authenticator(self) -> None:
        utils.set_console(info=_("Retrieving user data"))

        if not self.access_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            self.cli.on_quit(1)

        user_input = utils.safe_input(_("Enter the revocation code"))
        assert isinstance(user_input, str)

        utils.set_console(info=_("Removing authenticator"))

        try:
            removed = await self.webapi_session.remove_authenticator(
                self.steamid,
                self.access_token,
                user_input,
            )
        except aiohttp.ClientError:
            log.error(_("Check your connection. (server down?)"))
            self.cli.on_quit(1)
        except webapi.RevocationError:
            log.error(_("Too many attempts, try again later."))
            self.cli.on_quit(1)
        else:
            if removed:
                utils.set_console(info=_("Authenticator has been removed."))
            else:
                utils.set_console(error=_("Unable to remove the authenticator."))
