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
from typing import Generator

import aiohttp
from stlib import webapi, login, universe

from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(steamid: int, time_offset: int) -> Generator[utils.ModuleData, None, None]:
    identity_secret = config.parser.get("login", "identity_secret")

    if not identity_secret:
        config.new("plugins", "confirmations", "false")
        yield utils.ModuleData(error=_("The current identity secret is invalid."), info=_("Waiting Changes"))
        await asyncio.sleep(10)
        return

    deviceid = config.parser.get("login", "deviceid")

    if not deviceid:
        log.warning(_("Unable to find deviceid. Generating from identity."))
        deviceid = universe.generate_device_id(identity_secret)
        config.new("login", "deviceid", deviceid)

    session = webapi.get_session(0)

    try:
        confirmations = await session.get_confirmations(identity_secret, steamid, deviceid, time_offset=time_offset)
    except AttributeError:
        yield utils.ModuleData(error=_("Error when fetch confirmations"), info=_("Waiting Changes"))
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam is not running"), info=_("Waiting Changes"))
    except login.LoginError:
        yield utils.ModuleData(error=_("User is not logged in"), action="login")
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
    else:
        yield utils.ModuleData(action="update", raw_data=confirmations)

    await asyncio.sleep(20)
