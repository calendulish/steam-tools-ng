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
import logging
import sys
from typing import TYPE_CHECKING

import aiohttp
from stlib import universe, webapi, login

from . import utils
from .. import i18n, config, core

if TYPE_CHECKING:
    from . import cli

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class ManageAuthenticator:
    def __init__(self, cli_: 'cli.SteamToolsNG') -> None:
        self.cli = cli_
        self.webapi_session = webapi.SteamWebAPI.get_session(0)
        self.authenticator_data: webapi.AuthenticatorData | None = None
        self._sms_code = ''

    @property
    def sms_code(self) -> str:
        return self._sms_code

    @property
    def access_token(self) -> str:
        _store_cookies = self.webapi_session.http_session.cookie_jar.filter_cookies("https://store.steampowered.com")
        return _store_cookies['steamLoginSecure'].value.split('%7C%7C')[1]

    @property
    def steamid(self) -> universe.SteamId | None:
        if steamid := config.parser.getint("login", "steamid"):
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

        return None

    async def add_authenticator(self) -> None:
        task = asyncio.current_task()
        assert isinstance(task, asyncio.Task), "no task?"
        utils.set_console(info=_("Retrieving user data"))

        if not self.access_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            await core.safe_cancel(task)

        assert isinstance(self.steamid, universe.SteamId)

        if not self.authenticator_data or not self.sms_code:
            try:
                self.authenticator_data = await self.webapi_session.new_authenticator(self.steamid, self.access_token)
            except aiohttp.ClientError:
                log.error(_("Check your connection. (server down?)"))
                await core.safe_cancel(task)
            except webapi.AuthenticatorExists:
                log.error(_(
                    "There's already an authenticator active for that account.\n"
                    "Remove your current steam authenticator and try again."
                ))
                await core.safe_cancel(task)
            except webapi.PhoneNotRegistered:
                log.error(_(
                    "You must have a phone registered on your steam account to proceed.\n"
                    "Go to your Steam Account Settings, add a Phone Number, and try again."
                ))
                await core.safe_cancel(task)
            except NotImplementedError as exception:
                log.critical("%s: %s", type(exception).__name__, str(exception))
                await core.safe_cancel(task)
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
            await core.safe_cancel(task)
        except aiohttp.ClientError:
            log.error(_("Check your connection. (server down?)"))
            await core.safe_cancel(task)
        except Exception as exception:
            log.critical("%s: %s", type(exception).__name__, str(exception))
            await core.safe_cancel(task)

        utils.set_console(info=_("Saving new secrets"))
        config.new("login", "shared_secret", self.authenticator_data.shared_secret)
        config.new("login", "identity_secret", self.authenticator_data.identity_secret)
        config.new("steamguard", "enable", True)
        config.new("steamguard", "enable_confirmations", True)

        utils.set_console(info=_(
            "RECOVERY CODE\n\n"
            "You will need this code to recovery your Steam Account\n"
            "if you lose access to STNG Authenticator. So, write"
            "down this recovery code.\n\n"
            "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
        ), suppress_logging=True)

        for progress in range(30):
            utils.set_console(info=self.authenticator_data.revocation_code, level=(progress, 30), suppress_logging=True)
            await asyncio.sleep(1)

    async def remove_authenticator(self) -> None:
        task = asyncio.current_task()
        assert isinstance(task, asyncio.Task), "no task?"
        utils.set_console(info=_("Retrieving user data"))

        if not self.access_token or not self.steamid:
            log.error(_(
                "Some login data is missing. If the problem persists, run:\n"
                "{} --reset"
            ).format(sys.argv[0]))

            await core.safe_cancel(task)

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
            await core.safe_cancel(task)
        except webapi.RevocationError:
            log.error(_("Too many attempts, try again later."))
            await core.safe_cancel(task)
        else:
            if removed:
                utils.set_console(info=_("Authenticator has been removed."))
            else:
                utils.set_console(error=_("Unable to remove the authenticator."))
