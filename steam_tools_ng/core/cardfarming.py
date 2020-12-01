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
import random
from typing import Tuple, Generator

import aiohttp
from stlib import webapi, client

from . import utils
from .. import i18n, config

_ = i18n.get_translation


async def main(steamid: int) -> Generator[utils.ModuleData, None, None]:
    reverse_sorting = config.parser.getboolean("cardfarming", "reverse_sorting")
    wait_min = config.parser.getint("cardfarming", "wait_min")
    wait_max = config.parser.getint("cardfarming", "wait_max")

    if not steamid:
        raise NotImplementedError("Card farming with no steamid")

    session = webapi.get_session(0)

    try:
        badges = sorted(
            await session.get_badges(steamid),
            key=lambda badge_: badge_.cards,
            reverse=reverse_sorting
        )
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(10)
        return

    if not badges:
        yield utils.ModuleData(status=_("Stopped"), info=_("No more cards to drop."))
        await asyncio.sleep(random.randint(500, 1200))
        return

    for badge in badges:
        yield utils.ModuleData(
            display=str(badge.game_id),
            status=_("Loading {}").format(badge.game_name),
        )

        game_info = await session.get_owned_games(steamid, appids_filter=[badge.game_id])
        assert isinstance(game_info, webapi.Game), "game_info is not a Game object"

        if game_info.playtime >= 2 * 60:
            wait_offset = random.randint(wait_min, wait_max)
        else:
            wait_offset = (2 * 60 - game_info.playtime) * 60

        while badge.cards != 0:
            executor = client.SteamApiExecutor(badge.game_id)

            try:
                await executor.init()
            except client.SteamAPIError:
                yield utils.ModuleData(info=_("Invalid game id {}. Ignoring.").format(badge.game_id))
                badge = badge._replace(cards=0)
                break
            except ProcessLookupError:
                yield utils.ModuleData(error=_("Steam Client is not running."))
                await asyncio.sleep(15)
                continue

            for past_time in range(wait_offset):
                yield utils.ModuleData(
                    display=str(badge.game_id),
                    info=_("Waiting drops for {} minutes.").format(round((wait_offset - past_time) / 60)),
                    status=_("Running {}").format(badge.game_name),
                    level=(past_time, wait_offset),
                    raw_data=executor,
                    action="check",
                )

                await asyncio.sleep(1)

            yield utils.ModuleData(
                display=str(badge.game_id),
                info=_("{} ({})").format(_("Updating drops"), badge.game_name),
            )

            await executor.shutdown()
            await asyncio.sleep(random.randint(60, 120))

            try:
                badge = await session.update_badge_drops(badge, steamid)
                break
            except aiohttp.ClientError:
                yield utils.ModuleData(error=_("Check your connection. (server down?)"))
                await asyncio.sleep(10)
            except webapi.BadgeError:
                yield utils.ModuleData(error=_("Steam Server is busy"))
                await asyncio.sleep(20)

        utils.ModuleData(
            display=str(badge.game_id),
            info=_("{} ({})").format(_("Done"), badge.game_name),
        )
