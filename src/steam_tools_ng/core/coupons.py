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

from stlib import webapi
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main() -> Generator[utils.ModuleData, None, None]:
    session = webapi.get_session(0)
    botid = config.parser.getint('coupons', 'botid')
    appid = config.parser.getint('coupons', 'appid')
    contextid = config.parser.getint('coupons', 'contextid')

    try:
        inventory = await session.get_inventory(botid, appid, contextid)
    except AttributeError:
        yield utils.ModuleData(error=_("Error when fetch inventory"), info=_("Waiting Changes"))
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
    else:
        yield utils.ModuleData(action="update", raw_data=inventory)

    await asyncio.sleep(60)
