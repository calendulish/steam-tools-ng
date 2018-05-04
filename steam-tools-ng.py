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


def safe_import(method):
    try:
        module_ = importlib.import_module(f'.{method}', 'ui')
    except ModuleNotFoundError:
        module_ = importlib.import_module(f'.{method}', 'steam_tools_ng_ui')

    return module_


config = safe_import('config')

config.init()

i18n = safe_import('i18n')
_ = i18n.get_translation

log = logging.getLogger(__name__)

if os.name == 'nt':
    event_loop = asyncio.ProactorEventLoop()
else:
    event_loop = asyncio.new_event_loop()

asyncio.set_event_loop(event_loop)

if __name__ == "__main__":
    log.info('Steam Tools NG version 0.0.0-0 (Made with Girl Power <33)')
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
        console = safe_import('console')
        module_name = f'on_start_{console_params.module[0]}'
        module_options = console_params.options

        assert hasattr(console, module_name), f'{module_name} doesn\'t exist in {console}'
        module = getattr(console, module_name)

        return_code = event_loop.run_until_complete(module(*module_options))

        sys.exit(return_code)
    else:
        from gi.repository import Gtk

        application = safe_import('application')

        if os.name is 'posix' and not os.getenv('DISPLAY'):
            log.critical('The DISPLAY is not set!')
            log.critical('Use -c / --cli <module> for the command line interface.')
            sys.exit(1)

        app = application.Application()
        app.register()
        app.activate()


        async def async_gtk_iterator():
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

            if app.window.get_realized():
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
