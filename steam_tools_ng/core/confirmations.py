#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2020
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
from stlib import webapi, login

from . import utils
from .. import i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(steamid, identity: str, deviceid: str, time_offset: int) -> Generator[utils.ModuleData, None, None]:
    if not identity:
        yield utils.ModuleData(error=_("The current identity secret is invalid."))
        await asyncio.sleep(10)
        return

    session = webapi.get_session(0)

    try:
        confirmations = await session.get_confirmations(identity, steamid, deviceid, time_offset=time_offset)
    except AttributeError as exception:
        yield utils.ModuleData(error=_("Error when fetch confirmations"))
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam is not running"))
    except login.LoginError as exception:
        yield utils.ModuleData(error=_("User is not logged in"), action="login")
    except aiohttp.ClientError as exception:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
    else:
        yield utils.ModuleData(action="update", raw_data=confirmations)

    await asyncio.sleep(20)
