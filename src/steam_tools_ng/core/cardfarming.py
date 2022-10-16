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
import atexit
import contextlib
import random
import sys
import time
from pathlib import Path
from subprocess import call
from typing import AsyncGenerator, Dict, Optional, Any

import aiohttp
from psutil import Popen, NoSuchProcess

from stlib import webapi, client, universe, community
from . import utils
from .. import i18n, config

_ = i18n.get_translation


# FIXME: Workaround for keyboard lag when running games on GUI on Windows
# FIXME: https://gitlab.gnome.org/GNOME/gtk/-/issues/2015
# FIXME: L36:79
def killall(process: 'Popen') -> None:
    if not process.is_running():
        return

    for child in process.children(recursive=True):
        with contextlib.suppress(NoSuchProcess):
            child.kill()
            child.wait()

    process.kill()
    process.wait()


class SteamAPIExecutorWorkaround:
    def __init__(self, appid: int, *args: Any, **kwargs: Any) -> None:
        self.process = None
        self.appid = appid

        if sys.platform == 'win32':
            if getattr(sys, 'frozen', False):
                executor_path = [str(Path(sys.executable).parent / 'steam-api-executor.exe'), str(self.appid)]
            else:
                executor_path = [sys.executable, '-m', 'steam_tools_ng.steam_api_executor', str(self.appid)]

            self.process = Popen(executor_path, creationflags=0x08000000)
            atexit.register(killall, self.process)
        else:
            self.executor = _SteamAPIExecutor(appid, *args, **kwargs)

    def shutdown(self, *args: Any, **kwargs: Any) -> None:
        if sys.platform == 'win32':
            killall(self.process)
        else:
            self.executor.shutdown(*args, **kwargs)


_SteamAPIExecutor = client.SteamAPIExecutor
client.SteamAPIExecutor = SteamAPIExecutorWorkaround


# FIXME: L36:79
# FIXME: ---- #

async def while_has_cards(
        steamid: universe.SteamId,
        badge: community.Badge,
) -> AsyncGenerator[utils.ModuleData, None]:
    webapi_session = webapi.SteamWebAPI.get_session(0)
    community_session = community.Community.get_session(0)

    while badge.cards != 0:
        first_wait = config.parser.getint("cardfarming", "first_wait")
        default_wait = config.parser.getint("cardfarming", "default_wait")
        min_wait = config.parser.getint("cardfarming", "min_wait")

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

        try:
            executor = client.SteamAPIExecutor(badge.appid)
        except AttributeError:
            yield utils.ModuleData(action='ignore', info=_("Invalid game id {}. Ignoring.").format(badge.appid))
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
                info=_("{} {} for {}").format(current_time, current_time_size, badge.name),
                status=_("Running {}").format(badge.name),
                level=(past_time, wait_offset),
                raw_data=executor,
                action="check",
            )
            await asyncio.sleep(1)

        executor.shutdown()
        wait_offset = random.randint(min_wait, int(min_wait / 100 * 125))
        for past_time in range(wait_offset):
            yield utils.ModuleData(
                display=str(badge.appid),
                info=f"{_('Updating drops')} ({badge.name})",
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

        # noinspection PyProtectedMember
        badge = badge._replace(cards=cards)

    utils.ModuleData(
        display=str(badge.appid),
        info=_("{} ({})").format(_("Done"), badge.name),
    )


async def main(steamid: universe.SteamId, custom_game_id: int = 0) -> AsyncGenerator[utils.ModuleData, None]:
    reverse_sorting = config.parser.getboolean("cardfarming", "reverse_sorting")
    max_concurrency = config.parser.getint("cardfarming", "max_concurrency")
    invisible = config.parser.getboolean("cardfarming", "invisible")
    community_session = community.Community.get_session(0)

    try:
        badges = sorted(
            await community_session.get_badges(steamid),
            key=lambda badge_: badge_.cards,  # type: ignore
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

    generators = {}

    if invisible:
        call(f'{config.file_manager} "steam://friends/status/invisible"')

    for badge in badges:
        yield utils.ModuleData(
            display=str(badge.appid),
            status=_("Loading {}").format(badge.name),
        )

        if custom_game_id and badge.appid != custom_game_id:
            yield utils.ModuleData(info=_("Skipping {}").format(badge.appid))
            continue

        generators[badge.appid] = while_has_cards(steamid, badge)

    tasks: Dict[int, Optional[asyncio.Task[Any]]] = {}
    executors = {}
    semaphore = asyncio.Semaphore(max_concurrency)
    last_update = 0

    while True:
        for appid in generators.keys():
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
                data: utils.ModuleData = task.result()

                if data.action == 'check':
                    executors[appid] = data.raw_data

                if int(time.time()) > last_update + 3:
                    current_running = len(tasks)
                    total_remaining = len(generators) - len([task for task in tasks.values() if not task])
                    yield utils.ModuleData(
                        display=' : '.join([str(appid) for appid in tasks.keys()]),
                        info=data.info,
                        status=_('Running {} from {} remaining').format(current_running, total_remaining),
                        level=data.level,
                        raw_data=executors.values(),
                        action=data.action,
                    )
                    last_update = int(time.time())
