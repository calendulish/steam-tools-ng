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
import contextlib
import logging
import sys

from gi.repository import Gtk, GLib, Gio

from .. import core


async def main_loop(application: Gtk.Application | None = None) -> None:
    main_context = GLib.MainContext.default()

    await core.fix_ssl()

    if application:
        application.register()
        application.activate()

    while Gio.ListModel.get_n_items(Gtk.Window.get_toplevels()):
        while main_context.pending():
            main_context.iteration(False)

        await asyncio.sleep(0.01)


def run(application: Gtk.Application | None = None) -> None:
    with contextlib.suppress(asyncio.CancelledError, KeyboardInterrupt):
        asyncio.run(main_loop(application))

    # prevent tries to open log file at shutdown
    logging.root.removeHandler(logging.root.handlers[0])

    sys.exit(0)
