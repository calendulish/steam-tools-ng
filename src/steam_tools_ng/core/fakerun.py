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
from typing import Generator

import aiohttp
from stlib import webapi, client

from . import utils
from .. import i18n

_ = i18n.get_translation


async def main(steam_id: int, game_id: int) -> Generator[utils.ModuleData, None, None]:
    session = webapi.get_session(0)

    try:
        game_info = await session.get_owned_games(steam_id, appids_filter=[game_id])
        assert isinstance(game_info, webapi.Game), "game_info is not a Game object"
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return
    except ValueError:
        yield utils.ModuleData(error=_("Game {} doesn't exist").format(game_id))
        return

    yield utils.ModuleData(
        display=str(game_id),
        status=_("Loading {}").format(game_info.name),
    )

    start_time = 0

    try:
        async with client.SteamApiExecutor(game_id) as executor:
            while True:
                yield utils.ModuleData(
                    display=str(game_id),
                    info=_("Running for {} minutes.").format(round(start_time / 60)),
                    status=_("Running {}").format(game_info.name),
                    raw_data=executor,
                    action="check",
                )
                await asyncio.sleep(1)
                start_time += 1
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam Client is not running."))
