#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
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
from gi.repository import Gtk, GLib
from typing import Optional


async def async_iterator(
        application: Gtk.Application,
        main_context: GLib.MainContext,
        loop: asyncio.AbstractEventLoop,
) -> None:
    while main_context.pending():
        main_context.iteration(False)

    await asyncio.sleep(0.01)

    if application.main_window and application.main_window.get_realized():
        loop.create_task(async_iterator(application, main_context, loop))
    else:
        application.quit()
        loop.stop()


async def async_iterator_for_the_fifth_dimension(
        main_context: GLib.MainContext,
        loop: asyncio.AbstractEventLoop,
) -> None:
    while main_context.pending():
        main_context.iteration(False)

    await asyncio.sleep(0.01)
    loop.create_task(async_iterator_for_the_fifth_dimension(main_context, loop))


# FIXME: https://github.com/python/asyncio/pull/465
def run(application: Optional[Gtk.Application] = None) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_context = GLib.MainContext.default()

    if not application:
        iterator = async_iterator_for_the_fifth_dimension(main_context, loop)
    else:
        iterator = async_iterator(application, main_context, loop)
        application.register()
        application.activate()

    loop.create_task(iterator)

    with contextlib.suppress(KeyboardInterrupt):
        loop.run_forever()
