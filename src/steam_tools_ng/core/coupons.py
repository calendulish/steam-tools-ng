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


async def main(fetch_coupon_event: asyncio.Event) -> Generator[utils.ModuleData, None, None]:
    session = webapi.get_session(0)
    botid = config.parser.getint('coupons', 'botid')
    appid = config.parser.getint('coupons', 'appid')
    contextid = config.parser.getint('coupons', 'contextid')

    await fetch_coupon_event.wait()

    try:
        inventory = await session.get_inventory(botid, appid, contextid)
    except AttributeError:
        yield utils.ModuleData(error=_("Error when fetch inventory"), info=_("Waiting Changes"))
        await asyncio.sleep(15)
        return
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
        await asyncio.sleep(60)
        return

    yield utils.ModuleData(action="clear")

    for index, coupon_ in enumerate(inventory):
        if not fetch_coupon_event.is_set():
            log.warning(_("Stopping fetching coupons (requested by user)"))
            yield utils.ModuleData(action="update_level", raw_data=(0, 0))
            return

        yield utils.ModuleData(action="update_level", raw_data=(index, len(inventory)))
        package_link = coupon_.actions[0]['link']
        packageids = [int(id_) for id_ in package_link.split('=')[1].split(',')]

        try:
            package_details = await session.get_package_details(packageids)

            if not package_details:
                raise ValueError
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
            await asyncio.sleep(60)
            continue
        except ValueError:
            yield utils.ModuleData(error=_("Failed to get package details"), info=_("Waiting Changes"))
            await asyncio.sleep(15)
            continue
        else:
            await asyncio.sleep(.3)

        games_prices = []
        for package in package_details:
            try:
                games_prices.extend(await session.get_games_prices(package.apps))

                if not games_prices:
                    raise ValueError
            except aiohttp.ClientError:
                yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
                await asyncio.sleep(60)
                continue
            except ValueError:
                yield utils.ModuleData(error=_("Failed to get games prices"), info=_("Waiting Changes"))
                await asyncio.sleep(15)
                continue
            else:
                await asyncio.sleep(.3)

        discount = int(coupon_.name.split('%')[0])
        current_price = games_prices[0][1] if len(games_prices) > 0 else 0  # uni duni tee
        real_price = current_price - (current_price * discount / 100)

        yield utils.ModuleData(action='update', raw_data={
            'price': round(real_price, 2),
            'name': coupon_.name,
            'assetid': coupon_.assetid,
        })

        if index and not index % 100:
            yield utils.ModuleData(error=_("Api rate limit reached. Waiting."), info=_("Waiting Changes"))
            await asyncio.sleep(2 * 60)
