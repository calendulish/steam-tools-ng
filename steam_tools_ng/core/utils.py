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
import sys
from dataclasses import dataclass
from typing import Tuple, Any


@dataclass
class ModuleData:
    display: str = ''
    status: str = ''
    info: str = ''
    error: str = ''
    level: Tuple[int, int] = (0, 0)
    action: str = ''
    raw_data: Any = None


def asyncio_shutdown(loop: asyncio.BaseEventLoop = asyncio.get_event_loop()) -> None:
    try:
        asyncio.runners._cancel_all_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())

        if sys.version_info.minor > 8:
            loop.run_until_complete(loop.shutdown_default_executor())
    finally:
        asyncio.set_event_loop(None)
        loop.close()
