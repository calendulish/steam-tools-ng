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
from typing import AsyncGenerator

import aiohttp
from stlib import community

from . import utils
from .. import i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main() -> AsyncGenerator[utils.ModuleData, None]:
    community_session = community.Community.get_session(0)

    try:
        my_orders = await community_session.get_my_orders()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Failed when trying to get user orders"))
        await asyncio.sleep(30)
        return

    for position, buy_order in enumerate(my_orders[0]):
        try:
            histogram = await community_session.get_item_histogram(buy_order.appid, buy_order.hash_name)
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Failed when trying to get item histogram"))
            await asyncio.sleep(30)
            return

        yield utils.ModuleData(action='update', raw_data={
            'position': position,
            'order': buy_order,
            'histogram': histogram,
        })
