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

__all__ = [
    'steamguard',
    'confirmations',
    'steamtrades',
    'steamgifts',
    'coupons',
    'utils',
]

import asyncio
import contextlib
import ssl
import sys
from pathlib import Path
from typing import Any

import aiohttp
import stlib

from . import *

if stlib.steamworks_available:
    from . import cardfarming, fakerun


async def fix_ssl() -> None:
    ssl_context = ssl.SSLContext()

    if hasattr(sys, 'frozen'):
        _executable_path = Path(sys.executable).parent
        ssl_context.load_verify_locations(cafile=_executable_path / 'etc' / 'cacert.pem')

    tcp_connector = aiohttp.TCPConnector(ssl=ssl_context, force_close=True)
    await stlib.set_default_http_params(0, connector=tcp_connector)


# TODO: https://github.com/python/cpython/issues/103486
def safe_exit() -> None:
    for task in asyncio.all_tasks():
        task.cancel()

    # safe_task_callback will handle cancelled errors


# TODO: https://github.com/python/cpython/issues/103486
async def safe_cancel(task: asyncio.Task[Any]) -> None:
    task.cancel()
    await asyncio.sleep(0)

    if not task.done():
        with contextlib.suppress(asyncio.CancelledError):
            await task
