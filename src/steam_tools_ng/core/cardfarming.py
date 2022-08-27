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
import random
from typing import Generator

import aiohttp

from stlib import webapi, client, universe, community
from . import utils
from .. import i18n, config

_ = i18n.get_translation


async def main(steamid: universe.SteamId, custom_game_id: int = 0) -> Generator[utils.ModuleData, None, None]:
    reverse_sorting = config.parser.getboolean("cardfarming", "reverse_sorting")
    first_wait = config.parser.getint("cardfarming", "first_wait")
    default_wait = config.parser.getint("cardfarming", "default_wait")
    min_wait = config.parser.getint("cardfarming", "min_wait")
    community_session = community.Community.get_session(0)
    webapi_session = webapi.SteamWebAPI.get_session(0)

    try:
        badges = sorted(
            await community_session.get_badges(steamid),
            key=lambda badge_: badge_.cards,
            reverse=reverse_sorting
        )
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
        await asyncio.sleep(10)
        return

    if not badges or (custom_game_id and custom_game_id not in [badge.appid for badge in badges]):
        yield utils.ModuleData(error=_("No more cards to drop."), info=_("Waiting Changes"))
        await asyncio.sleep(random.randint(500, 1200))
        return

    for badge in badges:
        if custom_game_id and badge.appid != custom_game_id:
            yield utils.ModuleData(info=_("Skipping {}").format(badge.appid))
            continue

        yield utils.ModuleData(
            display=str(badge.appid),
            status=_("Loading {}").format(badge.name),
        )

        while badge.cards != 0:
            try:
                game_list = await webapi_session.get_owned_games(steamid, appids_filter=[badge.appid])
                game_info = game_list[0]
            except aiohttp.ClientError:
                yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
                await asyncio.sleep(10)
                continue

            if game_info.playtime_forever * 60 >= first_wait:
                wait_offset = random.randint(default_wait, int(default_wait / 100 * 125))
            else:
                wait_offset = first_wait - game_info.playtime_forever * 60

            executor = client.SteamApiExecutor(badge.appid)

            try:
                await executor.init()
            except client.SteamAPIError:
                yield utils.ModuleData(info=_("Invalid game id {}. Ignoring.").format(badge.appid))
                # noinspection PyProtectedMember
                badge = badge._replace(cards=0)
                break
            except ProcessLookupError:
                yield utils.ModuleData(error=_("Steam Client is not running."), info=_("Waiting Changes"))
                await asyncio.sleep(15)
                continue

            for past_time in range(wait_offset):
                current_time = round((wait_offset - past_time) / 60)
                current_time_size = _('minutes')

                if current_time <= 1:
                    current_time = wait_offset - past_time
                    current_time_size = _('seconds')

                yield utils.ModuleData(
                    display=str(badge.appid),
                    info=_("Waiting drops for {} {}.").format(current_time, current_time_size),
                    status=_("Running {}").format(badge.name),
                    level=(past_time, wait_offset),
                    raw_data=executor,
                    action="check",
                )

                await asyncio.sleep(1)

            await executor.shutdown()
            wait_offset = random.randint(min_wait, int(min_wait / 100 * 125))
            for past_time in range(wait_offset):
                yield utils.ModuleData(
                    display=str(badge.appid),
                    info="{} ({})".format(_("Updating drops"), badge.name),
                    status=_("Game paused"),
                    level=(past_time, wait_offset),
                )

                await asyncio.sleep(1)

            while True:
                try:
                    cards = await community_session.get_card_drops_remaining(steamid, badge.appid)
                except aiohttp.ClientError:
                    yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
                    await asyncio.sleep(10)
                except community.BadgeError:
                    yield utils.ModuleData(error=_("Steam Server is busy"), info=_("Waiting Changes"))
                    await asyncio.sleep(20)
                else:
                    break

            badge._replace(cards=cards)

        utils.ModuleData(
            display=str(badge.appid),
            info=_("{} ({})").format(_("Done"), badge.name),
        )
