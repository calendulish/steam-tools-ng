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
import codecs
import inspect
import logging
import time
from dataclasses import dataclass
from functools import cache, wraps
from typing import Tuple, Any, Callable, AsyncGenerator


@dataclass
class ModuleData:
    display: str = ''
    status: str = ''
    info: str = ''
    error: str = ''
    level: Tuple[int, int] = (0, 0)
    action: str = ''
    raw_data: Any = None
    suppress_logging: bool = False


async def timed_module_data(wait_offset: int, module_data: ModuleData) -> AsyncGenerator[ModuleData, None]:
    info = module_data.info
    assert module_data.level == (0, 0), "level should not be used here"

    # Prevent action to being executed multiple times
    if module_data.action:
        yield module_data
        module_data.action = ''

    module_data.suppress_logging = True
    caller = inspect.currentframe().f_back
    log = logging.getLogger(caller.f_globals['__name__'])
    log.info(info)

    for past_time in range(wait_offset):
        current_time = round((wait_offset - past_time) / 60)
        current_time_size = 'm'

        if current_time <= 1:
            current_time = wait_offset - past_time
            current_time_size = 's'

        module_data.level = (past_time, wait_offset)
        module_data.info = f'{info} ({current_time}{current_time_size})'

        yield module_data
        await asyncio.sleep(1)


def time_offset_cache(ttl: int = 60) -> Callable[[Callable[[], int]], Callable[[], int]]:
    def wrapper(function_: Any) -> Callable[[], int]:
        function_ = cache(function_)
        function_.time_base = time.time()

        @wraps(function_)
        def wrapped() -> int:
            if time.time() >= function_.time_base + ttl:
                function_.cache_clear()
                function_.time_base = time.time()

            time_raw = function_()

            if function_.cache_info().currsize == 0:
                assert isinstance(time_raw, int)
                return time_raw

            function_.time_offset = function_.time_base - time_raw
            return round(time.time() + function_.time_offset)

        return wrapped

    return wrapper


def encode_password(__password: str) -> str:
    password_key = codecs.encode(__password.encode(), 'base64')
    encrypted_password = codecs.encode(password_key.decode(), 'rot13')
    return encrypted_password.replace('\n', '')


def decode_password(encrypted_password: str) -> str:
    password_key = codecs.decode(encrypted_password, 'rot13')
    __password_raw = codecs.decode(password_key.encode(), 'base64')
    return __password_raw.decode()
