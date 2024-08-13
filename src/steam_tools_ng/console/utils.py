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
import inspect
import logging
import multiprocessing
import os
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, Any

from .. import i18n, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


def safe_input(
        msg: str,
        default_response: bool | None = None,
        custom_choices: List[str] | None = None,
) -> bool | str:
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
            print(f'\n{msg} {options}: ', end="", flush=True)

            with os.fdopen(0, closefd=False) as stdin:
                user_input = stdin.readline().strip()

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

            if user_input.lower() == _('n'):
                return False

            raise ValueError(_('{} is not an accepted value').format(user_input))
        except ValueError as exception:
            log.error(str(exception))
            log.error(_('Please, try again.'))


class AsyncInput(ProcessPoolExecutor):
    def __init__(self, *args: Any, max_workers: int = 2) -> None:
        self.process_context = multiprocessing.get_context("spawn")
        super().__init__(max_workers=max_workers, mp_context=self.process_context)

        self._pid = self.submit(os.getpid).result()
        self._input = self.submit(safe_input, *args)

    def done(self) -> bool:
        return self._input.done()

    def result(self) -> bool | str:
        return self._input.result()

    def cancel(self, *args: Any, **kwargs: Any) -> None:
        self.submit(os.kill, self._pid, signal.SIGABRT)
        super().shutdown(*args, **kwargs)


def set_console(
        module_data: core.utils.ModuleData | None = None,
        *,
        display: str = '',
        status: str = '',
        info: str = '',
        error: str = '',
        level: Tuple[int, int] = (0, 0),
        suppress_logging: bool = False,
) -> None:
    for std in (sys.stdout, sys.stderr):
        print(' ' * (os.get_terminal_size().columns - 1), end='\r', file=std)

    if not module_data:
        module_data = core.utils.ModuleData(display, status, info, error, level, suppress_logging=suppress_logging)

    if module_data.error:
        if module_data.suppress_logging:
            print(module_data.error)
        else:
            log.error(module_data.error)

        return

    if module_data.status:
        if not module_data.suppress_logging:
            log.debug(f"status data: {module_data.status}")

        print(module_data.status, end=' ')

    if module_data.display:
        if not module_data.suppress_logging:
            log.debug(f"display data: {module_data.display}")

        print(module_data.display, end=' ')

    if module_data.level[1] > 0:
        progress = module_data.level[0] + 1
        total = module_data.level[1]
        bar_size = 20

        total = int(progress * bar_size / total) if total > 0 else bar_size
        print(f"┌{'█' * total:{bar_size}}┐", end=' ')

    if module_data.info:
        if not module_data.suppress_logging:
            log.info(module_data.info)

        print(module_data.info, sep=' ', end=' ')

    print('', end='\r')


def safe_task_callback(task: asyncio.Task[Any]) -> None:
    if task.cancelled():
        coro = task.get_coro()
        assert inspect.iscoroutine(coro), "isn't coro?"
        log.debug(_("\n%s has been stopped due user request"), coro.__name__)
        return

    exception = task.exception()

    if exception and not isinstance(exception, KeyboardInterrupt):
        stack = task.get_stack()

        for frame in stack:
            log.critical("%s at %s", type(exception).__name__, frame)

        log.critical("Fatal Error: %s", str(exception))

        core.safe_exit()
