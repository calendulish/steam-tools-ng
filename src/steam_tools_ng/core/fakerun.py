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
from subprocess import call
from typing import AsyncGenerator, List

import aiohttp
from stlib import webapi, client, universe, community, login

from . import utils
from .. import i18n, config

_ = i18n.get_translation


async def mixing_igredients(ids: List[str]) -> AsyncGenerator[utils.ModuleData, None]:
    yield utils.ModuleData(display=str(34), status=_("Mixing ingredients"))
    await asyncio.sleep(2)

    try:
        for id_ in ids:
            with client.SteamAPIExecutor(int(id_)):
                await asyncio.sleep(2)
                yield utils.ModuleData(display=id_, status=_("Sugar successfully added"))
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam Client is not running."))


async def cake(
        webapi_session: webapi.SteamWebAPI,
        steamid: universe.SteamId,
        game_id: int,
) -> AsyncGenerator[utils.ModuleData, None]:
    yield utils.ModuleData(display=str(34), status=_("Loading a delicious cake"))
    ids = config.parser.get('fakerun', 'cakes').strip().split(',')
    call([config.file_manager, "steam://friends/status/invisible"])

    if len(ids) < 3:
        yield utils.ModuleData(error=_("Not enough ingredients"))
        return

    try:
        game_list = await webapi_session.get_owned_games(steamid, appids_filter=[game_id, *ids])

        if len(game_list) != 4:
            raise ValueError
    except aiohttp.ClientError:
        module_data = utils.ModuleData(error=_("Check your connection. (server down?)"))

        async for data in utils.timed_module_data(15, module_data):
            yield data

        return
    except ValueError:
        yield utils.ModuleData(error=_("Some ingredients are missing from your cuisine"))
        return

    call([config.file_manager, "steam://run/{game_id}"])
    await asyncio.sleep(3)

    async for slice_ in mixing_igredients(ids):
        yield slice_

    community_session = community.Community.get_session(0)

    while True:
        last_played_game = await community_session.get_last_played_game(steamid)

        if last_played_game == game_id:
            yield utils.ModuleData(display=str(34), status=_("getting cake out of pan"))

            # Prevent pan to fall out of hands
            await asyncio.sleep(3)

            async for slice_ in mixing_igredients(ids):
                yield slice_

            yield utils.ModuleData(display=str(34), status=_("Cake is ready"))
            break

        await asyncio.sleep(10)


async def main(
        steamid: universe.SteamId,
        game_id: int,
        extra_game_id: int | None = None,
) -> AsyncGenerator[utils.ModuleData, None]:
    webapi_session = webapi.SteamWebAPI.get_session(0)
    login_session = login.Login.get_session(0)

    if game_id == 34:
        assert isinstance(extra_game_id, int), "No extra game_id"
        async for slice_ in cake(webapi_session, steamid, extra_game_id):
            yield slice_
        return

    if not await login_session.is_limited():
        try:
            game_list = await webapi_session.get_owned_games(steamid, appids_filter=[game_id])
            game_name = game_list[0].name
        except aiohttp.ClientError:
            module_data = utils.ModuleData(error=_("Check your connection. (server down?)"))

            async for data in utils.timed_module_data(15, module_data):
                yield data

            return
        except ValueError:
            yield utils.ModuleData(error=_("Game {} doesn't exist").format(game_id))
            return
    else:
        # fallback
        game_name = "[limited account]"

    yield utils.ModuleData(
        display=str(game_id),
        status=_("Loading {}").format(game_name),
    )

    start_time = 0

    try:
        with client.SteamAPIExecutor(game_id) as executor:
            while True:
                yield utils.ModuleData(
                    display=str(game_id),
                    info=_("Running for {} minutes.").format(round(start_time / 60)),
                    status=_("Running {}").format(game_name),
                    raw_data=executor,
                    action="check",
                )
                await asyncio.sleep(1)
                start_time += 1
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam Client is not running."))
