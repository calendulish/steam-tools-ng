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
from typing import AsyncGenerator, Callable, Awaitable

import aiohttp

from stlib import universe, community, internals, webapi
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(
        steamid: universe.SteamId,
        fetch_coupon_event: asyncio.Event,
        wait_available: Callable[[], Awaitable[None]],
) -> AsyncGenerator[utils.ModuleData, None]:
    await wait_available()
    await fetch_coupon_event.wait()

    community_session = community.Community.get_session(0)
    internals_session = internals.Internals.get_session(0)
    webapi_session = webapi.SteamWebAPI.get_session(0)
    botids = config.parser.get('coupons', 'botids')
    tokens = config.parser.get('coupons', 'tokens')
    appid = config.parser.getint('coupons', 'appid')
    contextid = config.parser.getint('coupons', 'contextid')

    if not botids:
        yield utils.ModuleData(error=_("No botID found"), info=_("Waiting Changes"))
        await asyncio.sleep(5)
        return

    bot_list = [bot.strip() for bot in botids.split(',')]
    token_list = [token.strip() for token in tokens.split(',')]

    if len(bot_list) != len(token_list):
        yield utils.ModuleData(error=_("Invalid config. Each bot must have id and token."), info=_("Waiting Changes"))
        await asyncio.sleep(5)
        return

    try:
        owned_games = await webapi_session.get_owned_games(steamid)
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Failed when trying to get owned games"))
        await asyncio.sleep(30)
        return

    yield utils.ModuleData(action="clear")
    package_count = 1

    for botid, token in zip(bot_list, token_list):
        try:
            steamid = universe.generate_steamid(botid)
        except ValueError:
            yield utils.ModuleData(error=_("The botid {} is invalid").format(botid))
            await asyncio.sleep(5)
            return

        try:
            inventory = await community_session.get_inventory(steamid, appid, contextid)
        except AttributeError:
            module_data = utils.ModuleData(error=_("Error when fetch inventory"), info=_("Waiting Changes"))

            async for data in utils.timed_module_data(30, module_data):
                yield data

            return
        except aiohttp.ClientError:
            module_data = utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))

            async for data in utils.timed_module_data(120, module_data):
                yield data

            return
        except community.InventoryEmptyError:
            module_data = utils.ModuleData(error=_("The botid {} inventory is empty"), info=_("Skipping"))

            async for data in utils.timed_module_data(30, module_data):
                yield data

            continue

        if not inventory:
            module_data = utils.ModuleData(error=_("The botid {} has no coupons available"), info=_("Skipping"))

            async for data in utils.timed_module_data(30, module_data):
                yield data

            continue

        for index, coupon_ in enumerate(inventory):
            yield utils.ModuleData(action="update_level", raw_data=(index, len(inventory)))
            package_link = coupon_.actions[0]['link']
            packageids = [int(id_) for id_ in package_link.split('=')[1].split(',')]
            blacklist = config.parser.get('coupons', 'blacklist')
            ignored_list = [name.split('% OFF')[-1].split('- Coupon')[0].strip() for name in blacklist.split(',')]
            ignored_list.extend([game.name for game in owned_games])
            minimum_discount = config.parser.getint('coupons', 'minimum_discount')
            game_name = coupon_.name.split('% OFF')[-1].split('- Coupon')[0].strip()

            for package_id in packageids:
                if not fetch_coupon_event.is_set():
                    log.warning(_("Stopping fetching coupons (requested by user)"))
                    yield utils.ModuleData(action="update_level", raw_data=(0, 0))
                    return

                if any(
                        ignored == game_name or
                        (ignored.startswith('*') and game_name.endswith(ignored[1:])) or
                        (ignored.endswith('*') and game_name.startswith(ignored[:-1]))
                        for ignored in blacklist
                ):
                    log.info(_('Ignoring coupon %s due blacklist'), coupon_.name)
                    continue

                if coupon_.name.split('% OFF')[-1].split('- Coupon')[0].strip() in ignored_list:
                    log.info(_('Ignoring coupon %s due blacklist'), coupon_.name)
                    continue

                coupon_discount = int(coupon_.name.split('%')[0])

                if coupon_discount < minimum_discount:
                    log.info(_('Ignoring coupon %s due low discount value'), coupon_.name)
                    continue

                package_count += 1

                try:
                    package_details = await internals_session.get_package(package_id)

                    if not package_details:
                        raise ValueError
                except aiohttp.ClientError:
                    module_data = utils.ModuleData(
                        error=_("Check your connection. (server down?)"),
                        info=_("Waiting Changes"),
                    )

                    async for data in utils.timed_module_data(60, module_data):
                        yield data

                    continue
                except ValueError:
                    yield utils.ModuleData(error=_("Failed to get package details"), info=_("Waiting Changes"))
                    await asyncio.sleep(1)
                    continue
                else:
                    await asyncio.sleep(.5)

                if package_details.discount_percent:
                    real_price = package_details.price - (
                            package_details.price * package_details.discount_percent / 100)
                else:
                    real_price = package_details.price - (package_details.price * coupon_discount / 100)

                yield utils.ModuleData(action='update', raw_data={
                    'price': round(real_price, 2),
                    'name': coupon_.name,
                    'link': coupon_.actions[0]['link'],
                    'botid': botid,
                    'token': token,
                    'assetid': coupon_.assetid,
                })

            if index and not package_count % 130:
                module_data = utils.ModuleData(error=_("Api rate limit reached. Waiting."), info=_("Waiting Changes"))

                async for data in utils.timed_module_data(120, module_data):
                    yield data

    yield utils.ModuleData(action="update_level", raw_data=(0, 0))
    fetch_coupon_event.clear()
