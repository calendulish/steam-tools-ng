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
import codecs
import getpass
import logging
import os
import sys
import tempfile
from typing import Optional, Union, List, Tuple

import aiohttp
from stlib import webapi, universe, login

from .. import i18n, config, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


def safe_input(
        msg: str,
        default_response: Optional[bool] = None,
        custom_choices: Optional[List[str]] = None,
) -> Union[bool, str]:
    if default_response and custom_choices:
        raise AttributeError("You can not use both default_response and custom_choices")

    if default_response is True:
        options = _('[Y/n]')
    elif default_response is False:
        options = _('[y/N]')
    elif custom_choices:
        options = f"Your choice [{'/'.join(custom_choices)}]"
    else:
        options = ''

    while True:
        try:
            user_input = input(f'{msg} {options}: ')

            if custom_choices:
                if not user_input:
                    raise ValueError(_('Invalid response from user'))

                if user_input.lower() in custom_choices:
                    return user_input.lower()

                raise ValueError(_('{} is not an accepted value').format(user_input))

            if default_response is None:
                if len(user_input) > 2:
                    return user_input

                raise ValueError(_('Invalid response from user'))

            if not user_input:
                return default_response

            if user_input.lower() == _('y'):
                return True
            elif user_input.lower() == _('n'):
                return False
            else:
                raise ValueError(_('{} is not an accepted value').format(user_input))
        except ValueError as exception:
            log.error(exception.args[0])
            log.error(_('Please, try again.'))


def set_console(
        module_data: Optional[core.utils.ModuleData] = None,
        *,
        display: Optional[str] = None,
        status: Optional[str] = None,
        info: Optional[str] = None,
        error: Optional[str] = None,
        level: Optional[Tuple[int, int]] = None,
) -> None:
    for std in (sys.stdout, sys.stderr):
        print(' ' * (os.get_terminal_size().columns - 1), end='\r', file=std)

    if not module_data:
        module_data = core.utils.ModuleData(display, status, info, error, level)

    if module_data.error:
        log.error(module_data.error)
        return

    if module_data.status:
        print(module_data.status, end=' ')

    if module_data.display:
        print(module_data.display, end=' ')

    if module_data.level:
        progress = module_data.level[0] + 1
        total = module_data.level[1]
        bar_size = 20

        if total > 0:
            total = int(progress * bar_size / total)
        else:
            total = bar_size

        print("┌{:{}}┐".format('█' * total, bar_size), end=' ')

    if module_data.info:
        print(module_data.info, sep=' ', end=' ')

    print('', end='\r')


def safe_task_callback(task: asyncio.Task) -> None:
    if task.cancelled():
        log.debug(_("%s has been stopped due user request"), task.get_coro())
        return

    exception = task.exception()

    if exception and not isinstance(exception, asyncio.CancelledError):
        stack = task.get_stack()

        for frame in stack:
            log.critical(f"{type(exception).__name__} at {frame}")

        log.critical(f"Fatal Error: {str(exception)}")
        loop = asyncio.get_running_loop()
        loop.stop()
        sys.exit(1)
