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
import contextlib
import random
import time
from subprocess import call
from typing import AsyncGenerator, Dict, Any

import aiohttp
from stlib import webapi, client, universe, community

from . import utils
from .. import i18n, config

_ = i18n.get_translation
executors = {}


def safe_exit(*args: Any, **kwargs: Any) -> None:
    for executor in executors.values():
        with contextlib.suppress(RuntimeError):
            executor.shutdown(*args, **kwargs)


async def while_has_cards(
        steamid: universe.SteamId,
        badge: community.Badge,
        play_event: asyncio.Event | None = None,
) -> AsyncGenerator[utils.ModuleData, None]:
    webapi_session = webapi.SteamWebAPI.get_session(0)
    community_session = community.Community.get_session(0)

    while badge.cards != 0:
        if play_event:
            await play_event.wait()

        mandatory_waiting = config.parser.getint("cardfarming", "mandatory_waiting")
        wait_while_running = config.parser.getint("cardfarming", "wait_while_running")
        wait_for_drops = config.parser.getint("cardfarming", "wait_for_drops")

        try:
            game_list = await webapi_session.get_owned_games(steamid, appids_filter=[badge.appid])
            game_info = game_list[0]
        except aiohttp.ClientError:
            module_data = utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))

            async for data in utils.timed_module_data(10, module_data):
                yield data

            continue

        if game_info.playtime_forever * 60 >= mandatory_waiting:
            wait_offset = random.randint(wait_while_running, int(wait_while_running / 100 * 125))
        else:
            wait_offset = mandatory_waiting - game_info.playtime_forever * 60

        try:
            executor = client.SteamAPIExecutor(badge.appid)
        except AttributeError:
            yield utils.ModuleData(action='ignore', info=_("Invalid game id {}. Ignoring.").format(badge.appid))
            break
        except ProcessLookupError:
            module_data = utils.ModuleData(error=_("Steam Client is not running."), info=_("Waiting Changes"))

            async for data in utils.timed_module_data(15, module_data):
                yield data

            continue

        module_data = utils.ModuleData(
            display=str(badge.appid),
            info=badge.name,
            status=_("Running {}").format(badge.name),
            raw_data=executor,
            action="check",
        )

        async for data in utils.timed_module_data(wait_offset, module_data):
            if play_event and not play_event.is_set():
                executor.shutdown()
                await asyncio.sleep(1)
                await play_event.wait()
                executor.__init__(executor.appid)

            yield data

        executor.shutdown()
        wait_offset = random.randint(wait_for_drops, int(wait_for_drops / 100 * 125))

        module_data = utils.ModuleData(
            display=str(badge.appid),
            info=_('Updating {} drops').format(badge.name),
            status=_("Game paused"),
        )

        async for data in utils.timed_module_data(wait_offset, module_data):
            yield data

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

        yield utils.ModuleData(action="update_drops", raw_data=badge.cards - cards)

        # noinspection PyProtectedMember
        badge = badge._replace(cards=cards)

    utils.ModuleData(
        display=str(badge.appid),
        info=_("{} ({})").format(_("Done"), badge.name),
    )


async def main(
        steamid: universe.SteamId,
        play_event: asyncio.Event | None = None,
        custom_game_id: int = 0,
) -> AsyncGenerator[utils.ModuleData, None]:
    if play_event:
        await play_event.wait()

    asyncio.current_task().add_done_callback(safe_exit)

    reverse_sorting = config.parser.getboolean("cardfarming", "reverse_sorting")
    max_concurrency = config.parser.getint("cardfarming", "max_concurrency")
    invisible = config.parser.getboolean("cardfarming", "invisible")
    community_session = community.Community.get_session(0)
    total_cards_remaining = 0

    try:
        badges = sorted(
            await community_session.get_badges(steamid),
            key=lambda badge_: badge_.cards,  # type: ignore
            reverse=reverse_sorting
        )
    except aiohttp.ClientError:
        module_data = utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))

        async for data in utils.timed_module_data(10, module_data):
            yield data

        return

    if not badges or (custom_game_id and custom_game_id not in [badge.appid for badge in badges]):
        module_data = utils.ModuleData(error=_("No more cards to drop."), info=_("Waiting Changes"))
        wait_offset = random.randint(300, 500)

        async for data in utils.timed_module_data(wait_offset, module_data):
            yield data

        return

    generators = {}

    if invisible:
        call([config.file_manager, "steam://friends/status/invisible"])

    for badge in badges:
        yield utils.ModuleData(
            display=str(badge.appid),
            status=_("Loading {}").format(badge.name),
        )

        if custom_game_id and badge.appid != custom_game_id:
            yield utils.ModuleData(info=_("Skipping {}").format(badge.appid))
            continue

        generators[badge.appid] = while_has_cards(steamid, badge, play_event)
        total_cards_remaining += badge.cards

    tasks: Dict[int, asyncio.Task[Any] | None] = {}
    semaphore = asyncio.Semaphore(max_concurrency)
    last_update = 0

    while True:
        for appid in generators:
            progress_coro = anext(generators[appid])
            assert asyncio.iscoroutine(progress_coro)

            if appid not in tasks:
                if semaphore.locked():
                    break

                await semaphore.acquire()
                tasks[appid] = asyncio.create_task(progress_coro)

            if not tasks[appid]:
                continue

            current_task = tasks[appid]
            assert isinstance(current_task, asyncio.Task)

            if current_task.done():
                semaphore.release()

                if current_task.exception():
                    if isinstance(current_task.exception(), StopAsyncIteration):
                        tasks[appid] = None
                        continue

                    current_exception = current_task.exception()
                    assert isinstance(current_exception, BaseException)
                    raise current_exception

                await semaphore.acquire()
                tasks[appid] = asyncio.create_task(progress_coro)

        if not any(tasks.values()):
            break

        await asyncio.wait([task for task in tasks.values() if task], return_when=asyncio.FIRST_COMPLETED)

        for appid, task in tasks.items():
            if task and task.done() and not task.exception():
                global executors
                data: utils.ModuleData = task.result()

                if data.action == 'check':
                    executors[appid] = data.raw_data

                if data.action == "update_drops":
                    total_cards_remaining -= data.raw_data

                if int(time.time()) > last_update + 3:
                    current_running_limit = len(tasks)
                    total_remaining = len(generators) - len([task for task in tasks.values() if not task])
                    running_executors = [executor for executor in executors.values() if executor.is_running()]
                    extra_info = ''

                    current_running_limit = min(current_running_limit, total_remaining)
                    if current_running_limit == 2:
                        extra_info = _(" +{} other").format(current_running_limit - 1)
                    elif current_running_limit > 2:
                        extra_info = _(" +{} others").format(current_running_limit - 1)

                    yield utils.ModuleData(
                        display=' : '.join([str(executor.appid) for executor in running_executors]),
                        info=data.info + extra_info,
                        status=_('{} from {} remaining ({} cards)').format(
                            current_running_limit,
                            total_remaining,
                            total_cards_remaining,
                        ),
                        level=data.level,
                        raw_data=running_executors,
                        action=data.action,
                    )
                    last_update = int(time.time())
