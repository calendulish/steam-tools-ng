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

import argparse
import asyncio
import importlib
import logging
import os
import sys
import textwrap

from steam_tools_ng import config, i18n, version

config.init()
_ = i18n.get_translation

log = logging.getLogger(__name__)

if sys.platform == 'win32':
    event_loop = asyncio.ProactorEventLoop()
else:
    event_loop = asyncio.new_event_loop()

asyncio.set_event_loop(event_loop)

if __name__ == "__main__":
    log.info(f'Steam Tools NG version {version.__version__} (Made with Girl Power <33)')
    log.info('Copyright (C) 2015 ~ 2018 Lara Maia - <dev@lara.click>')

    command_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
                Available modules for console mode:
                    - authenticator
                       '''))

    command_parser.add_argument('-c', '--cli',
                                choices=['authenticator'],
                                metavar='module [options]',
                                action='store',
                                nargs=1,
                                help='Start module without GUI (console mode)',
                                dest='module')
    command_parser.add_argument('options',
                                nargs='*',
                                help=argparse.SUPPRESS)

    console_params = command_parser.parse_args()

    if console_params.module:
        module_name = console_params.module[0]
        module_options = console_params.options
        module = importlib.import_module(f'.{module_name}', 'steam_tools_ng.console')

        return_code = event_loop.run_until_complete(module.run(*module_options))  # type: ignore

        sys.exit(return_code)
    else:
        from steam_tools_ng.gtk import application
        from gi.repository import Gtk

        if sys.platform.startswith("linux") and not os.getenv('DISPLAY'):
            log.critical('The DISPLAY is not set!')
            log.critical('Use -c / --cli <module> for the command line interface.')
            sys.exit(1)

        app = application.Application()
        app.register()
        app.activate()


        async def async_gtk_iterator() -> None:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

            if app.window and app.window.get_realized():
                asyncio.ensure_future(async_gtk_iterator())
            else:
                event_loop.stop()


        asyncio.ensure_future(async_gtk_iterator())
        event_loop.run_forever()

        log.info(_("Exiting..."))

        unfinished_tasks = asyncio.Task.all_tasks()

        if unfinished_tasks:
            event_loop.run_until_complete(asyncio.wait(unfinished_tasks, return_when=asyncio.ALL_COMPLETED))

        event_loop.close()
        app.quit()
