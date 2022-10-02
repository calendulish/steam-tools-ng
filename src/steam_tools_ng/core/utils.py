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
import time
from dataclasses import dataclass
from functools import cache, wraps
from typing import Tuple, Any, Callable


@dataclass
class ModuleData:
    display: str = ''
    status: str = ''
    info: str = ''
    error: str = ''
    level: Tuple[int, int] = (0, 0)
    action: str = ''
    raw_data: Any = None


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
