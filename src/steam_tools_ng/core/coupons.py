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

from stlib import universe, community, internals
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(fetch_coupon_event: asyncio.Event) -> Generator[utils.ModuleData, None, None]:
    community_session = community.Community.get_session(0)
    internals_session = internals.Internals.get_session(0)
    botid = config.parser.getint('coupons', 'botid')
    appid = config.parser.getint('coupons', 'appid')
    contextid = config.parser.getint('coupons', 'contextid')

    await fetch_coupon_event.wait()

    try:
        steamid = universe.generate_steamid(botid)
        inventory = await community_session.get_inventory(steamid, appid, contextid)
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
        yield utils.ModuleData(action="update_level", raw_data=(index, len(inventory)))
        package_link = coupon_.actions[0]['link']
        packageids = [int(id_) for id_ in package_link.split('=')[1].split(',')]

        for package_id in packageids:
            if not fetch_coupon_event.is_set():
                log.warning(_("Stopping fetching coupons (requested by user)"))
                yield utils.ModuleData(action="update_level", raw_data=(0, 0))
                return

            coupon_discount = int(coupon_.name.split('%')[0])

            if coupon_discount < 75:
                log.info(_('Ignoring coupon %s due low discount value'), coupon_.name)
                continue

            try:
                package_details = await internals_session.get_package(package_id)

                if not package_details:
                    raise ValueError
            except aiohttp.ClientError:
                yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
                await asyncio.sleep(30)
                continue
            except ValueError:
                yield utils.ModuleData(error=_("Failed to get package details"), info=_("Waiting Changes"))
                await asyncio.sleep(1)
                continue
            else:
                await asyncio.sleep(.5)

            if package_details.discount_percent:
                real_price = package_details.price - (package_details.price * package_details.discount_percent / 100)
            else:
                real_price = package_details.price - (package_details.price * coupon_discount / 100)

            yield utils.ModuleData(action='update', raw_data={
                'price': round(real_price, 2),
                'name': coupon_.name,
                'assetid': coupon_.assetid,
                'link': coupon_.actions[0]['link'],
            })

        if index and not index % 150:
            yield utils.ModuleData(error=_("Api rate limit reached. Waiting."), info=_("Waiting Changes"))
            await asyncio.sleep(100)

    fetch_coupon_event.clear()