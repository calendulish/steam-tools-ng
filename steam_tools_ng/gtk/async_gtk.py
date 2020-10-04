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

from gi.repository import Gtk

from .. import core


async def async_iterator(application: Gtk.Application, loop: asyncio.AbstractEventLoop) -> None:
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    await asyncio.sleep(0.01)

    if application.main_window and application.main_window.get_realized():
        loop.create_task(async_iterator(application, loop))
    else:
        application.quit()
        loop.stop()


# FIXME: https://github.com/python/asyncio/pull/465
def run(application: Gtk.Application) -> None:
    loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        loop.create_task(async_iterator(application, loop))
        application.register()
        application.activate()
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        core.utils.asyncio_shutdown(loop)
