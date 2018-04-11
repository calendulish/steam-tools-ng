#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2018
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

import logging
import os
import shutil
import sys
from ctypes import Structure, byref, c_short, windll
from ctypes.wintypes import DWORD
from logging import Handler, handlers
from types import TracebackType
from typing import Any, Optional, Type

from ui import config

if os.name == 'nt':
    class WindowsConsoleCoord(Structure):
        _fields_ = [
            ("x", c_short),
            ("y", c_short),
        ]


    class WindowsConsoleSmallRect(Structure):
        _fields_ = [
            ("left", c_short),
            ("top", c_short),
            ("right", c_short),
            ("bottom", c_short),
        ]


    class WindowsConsoleBufferInfo(Structure):
        _fields_ = [
            ("size", WindowsConsoleCoord),
            ("cursor_position", WindowsConsoleCoord),
            ("attributes", c_short),
            ("window", WindowsConsoleSmallRect),
            ("maximum_window_size", WindowsConsoleCoord),
        ]


    class LowLevelConsoleAPI(object):
        def __init__(self) -> None:
            self.saved_buffer_info = WindowsConsoleBufferInfo()
            self.screen_buffer = windll.kernel32.GetStdHandle(-11)

        def __enter__(self) -> Any:
            windll.kernel32.GetConsoleScreenBufferInfo(self.screen_buffer, byref(self.saved_buffer_info))
            return self

        def __exit__(self,
                     exception_type: Optional[Type[BaseException]],
                     exception_value: Optional[Exception],
                     traceback: Optional[TracebackType]) -> None:
            windll.kernel32.SetConsoleTextAttribute(self.screen_buffer, self.saved_buffer_info.attributes)

        def set_color(self, color_number: int) -> None:
            windll.kernel32.SetConsoleTextAttribute(self.screen_buffer, color_number)

        def write(self, msg: str) -> None:
            windll.kernel32.WriteConsoleW(self.screen_buffer, msg, len(msg), byref(DWORD(0)), None)


class ColoredStreamHandler(Handler):
    unix_color_map = {
        'INFO': 37,
        'WARNING': 33,
        'ERROR': 35,
        'CRITICAL': 31,
        'DEBUG': 36,
    }

    windows_color_map = {
        'INFO': 1 | 2 | 4,
        'WARNING': 2 | 4 | 8,
        'ERROR': 1 | 4 | 8,
        'CRITICAL': 4 | 8,
        'debug': 2 | 1,
    }

    def emit(self, record: Any) -> None:
        # noinspection PyBroadException
        try:
            msg = record.getMessage().split('\n')

            if os.name == 'nt':
                color_number = self.windows_color_map.get(record.levelname, 1 | 2 | 4)

                with LowLevelConsoleAPI() as console:
                    console.set_color(2)
                    console.write(' --> ')

                    console.set_color(color_number)
                    console.write(f'{msg.pop(0)}\r\n')

                    console.set_color(1 | 2 | 4 | 8)
                    for line in msg:
                        console.write(f'{line}\r\n')
            else:
                color_number = self.unix_color_map.get(record.levelname, 37)
                sys.stdout.write('\033[32m --> ')
                sys.stdout.write(f'\033[{color_number}m{msg.pop(0)}\033[m\n')

                sys.stdout.write('\033[1;37m')
                for line in msg:
                    sys.stdout.write(f'{line}\n')
                sys.stdout.write('\033[m')
        except Exception:
            self.handleError(record)


def console_fixer(end: str = '\n') -> None:
    tsize = shutil.get_terminal_size()[0]
    print(('{:' + str(tsize - 1) + 's}').format(''), end=end, flush=True)


@config.check
def configure(
        log_directory: config.ConfigStr = config.DefaultConfig.log_directory,
        log_console_level: config.ConfigStr = config.DefaultConfig.log_console_level,
        log_level: config.ConfigStr = config.DefaultConfig.log_level
) -> None:
    os.makedirs(log_directory, exist_ok=True)

    log_file = logging.handlers.RotatingFileHandler(os.path.join(log_directory, 'steam-tools-ng.log'),
                                                    backupCount=1,
                                                    encoding='utf-8')
    log_file.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    log_file.setLevel(getattr(logging, log_level.upper()))
    log_file.doRollover()

    console = ColoredStreamHandler()
    console.setLevel(getattr(logging, log_console_level.upper()))

    logging.basicConfig(level=logging.DEBUG, handlers=[log_file, console])
