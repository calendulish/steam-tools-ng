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
import logging
from typing import AsyncGenerator

from stlib import login, universe, community
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(steamid: universe.SteamId) -> AsyncGenerator[utils.ModuleData, None]:
    identity_secret = config.parser.get("login", "identity_secret")
    session = community.Community.get_session(0)

    if not identity_secret:
        config.new("confirmations", "enable", "false")
        module_data = utils.ModuleData(error=_("The current identity secret is invalid."), info=_("Waiting Changes"))

        async for data in utils.timed_module_data(10, module_data):
            yield data

        return

    deviceid = config.parser.get("login", "deviceid")

    if not deviceid:
        log.warning(_("Unable to find deviceid. Generating from identity."))
        deviceid = universe.generate_device_id(identity_secret)
        config.new("login", "deviceid", deviceid)

    try:
        confirmations = await session.get_confirmations(identity_secret, steamid, deviceid)
    except AttributeError as exception:
        log.error(str(exception))
        module_data = utils.ModuleData(error=_("Error when fetch confirmations"), info=_("Waiting Changes"))
    except ProcessLookupError:
        module_data = utils.ModuleData(error=_("Steam is not running"), info=_("Waiting Changes"))
    except login.LoginError:
        module_data = utils.ModuleData(error=_("Not logged in"), action="login")
    except aiohttp.ClientError:
        module_data = utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
    else:
        module_data = utils.ModuleData(action="update", raw_data=confirmations)

    async for data in utils.timed_module_data(20, module_data):
        yield data
