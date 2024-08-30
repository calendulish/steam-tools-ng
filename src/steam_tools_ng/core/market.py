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
from typing import AsyncGenerator, List, Dict, Any

import aiohttp
from stlib import community

from . import utils
from .. import i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def get_histogram(
        orders: List[community.Order],
        order_type: str,
        fetch_event: asyncio.Event,
) -> AsyncGenerator[utils.ModuleData, None]:
    community_session = community.Community.get_session(0)

    for position, order in enumerate(orders):
        if not fetch_event.is_set():
            log.debug(_("Waiting market fetch event"))
            yield utils.ModuleData(action=f"update_{order_type}_level", raw_data=(0, 0))
            await fetch_event.wait()

        yield utils.ModuleData(action=f"update_{order_type}_level", raw_data=(position + 1, len(orders)))

        try:
            histogram = await community_session.get_item_histogram(order.appid, order.hash_name)
        except (community.MarketError, aiohttp.ClientError):
            module_data = utils.ModuleData(error=_("Failed when trying to get order histogram"))

            async for data in utils.timed_module_data(15, module_data):
                yield data

            return

        yield utils.ModuleData(action='update', raw_data={
            'position': position,
            'order': order,
            'histogram': histogram,
            'type': order_type,
        })

    yield utils.ModuleData(action=f"update_{order_type}_level", raw_data=(0, 0))
    fetch_event.clear()


async def main(
        fetch_buy_event: asyncio.Event,
        fetch_sell_event: asyncio.Event,
) -> AsyncGenerator[utils.ModuleData, None]:
    while not fetch_sell_event.is_set() and not fetch_buy_event.is_set():
        await asyncio.sleep(5)

    community_session = community.Community.get_session(0)

    try:
        my_orders = await community_session.get_my_orders()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Failed when trying to get user orders"))
        await asyncio.sleep(30)
        return

    yield utils.ModuleData(action="clear")

    generators = {
        "sell": get_histogram(my_orders[0], "sell", fetch_sell_event),
        "buy": get_histogram(my_orders[1], "buy", fetch_buy_event),
    }

    tasks: Dict[str, asyncio.Task[Any] | None] = {}
    semaphore = asyncio.Semaphore(2)

    while True:
        for type_ in generators:
            progress_coro = anext(generators[type_])
            assert asyncio.iscoroutine(progress_coro)

            if type_ not in tasks:
                if semaphore.locked():
                    break

                await semaphore.acquire()
                tasks[type_] = asyncio.create_task(progress_coro)

            if not tasks[type_]:
                continue

            current_task = tasks[type_]
            assert isinstance(current_task, asyncio.Task)

            if current_task.done():
                semaphore.release()

                if current_task.exception():
                    if isinstance(current_task.exception(), StopAsyncIteration):
                        tasks[type_] = None
                        continue

                    current_exception = current_task.exception()
                    assert isinstance(current_exception, BaseException)
                    raise current_exception

                await semaphore.acquire()
                tasks[type_] = asyncio.create_task(progress_coro)

        if not any(tasks.values()):
            break

        await asyncio.wait([task for task in tasks.values() if task], return_when=asyncio.FIRST_COMPLETED)

        for task in tasks.values():
            if task and task.done() and not task.exception():
                yield task.result()
