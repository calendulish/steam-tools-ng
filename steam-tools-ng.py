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
import contextlib
import importlib
import logging
import os
import ssl
import sys
import textwrap

import aiohttp

if os.environ.get('GTK_DEBUG', False) or os.environ.get('DEBUG', False):
    from src import config, i18n, version
else:
    # noinspection PyUnresolvedReferences
    from steam_tools_ng import config, i18n, version

config.init()
_ = i18n.get_translation

log = logging.getLogger(__name__)

if sys.platform == 'win32':
    event_loop = asyncio.ProactorEventLoop()
    file_manager = 'explorer'
else:
    file_manager = 'xdg-open'
    event_loop = asyncio.new_event_loop()

asyncio.set_event_loop(event_loop)

if __name__ == "__main__":
    command_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
                Available modules for console mode:
                    - authenticator
                       '''))

    command_parser.add_argument(
        '-c', '--cli',
        choices=['authenticator', 'steamtrades'],
        metavar='module [options]',
        action='store',
        nargs=1,
        help='Start module without GUI (console mode)',
        dest='module'
    )

    command_parser.add_argument(
        '--config-dir',
        action='store_true',
        help='Shows directory used to save config files',
        dest='config_dir'
    )

    command_parser.add_argument(
        '--log-dir',
        action='store_true',
        help='Shows directory used to save log files',
        dest='log_dir',
    )

    command_parser.add_argument(
        '--reset',
        action='store_true',
        help='Clean up settings and log files',
        dest='reset',
    )

    command_parser.add_argument(
        'options',
        nargs='*',
        help=argparse.SUPPRESS
    )

    console_params = command_parser.parse_args()

    if console_params.config_dir:
        os.system(f'{file_manager} {config.config_file_directory}')
        sys.exit(0)

    if console_params.log_dir:
        os.system(f'{file_manager} {config.DefaultConfig.log_directory}')
        sys.exit(0)

    if console_params.reset:
        with contextlib.suppress(FileNotFoundError):
            os.remove(config.config_file)

        logging.root.removeHandler(logging.root.handlers[0])

        log_directory = config.config_parser.get("logger", "log_directory", fallback=config.DefaultConfig.log_directory)
        os.remove(os.path.join(log_directory, 'steam-tools-ng.log'))
        os.remove(os.path.join(log_directory, 'steam-tools-ng.log.1'))

        log.info(_('Done!'))
        sys.exit(0)

    log.info(f'Steam Tools NG version {version.__version__} (Made with Girl Power <33)')
    log.info('Copyright (C) 2015 ~ 2018 Lara Maia - <dev@lara.click>')

    ssl_context = ssl.SSLContext()

    if hasattr(sys, 'frozen'):
        _executable_path = os.path.dirname(sys.executable)
        ssl_context.load_verify_locations(cafile=os.path.join(_executable_path, 'etc', 'cacert.pem'))

    tcp_connector = aiohttp.TCPConnector(ssl=ssl_context)
    http_session = aiohttp.ClientSession(raise_for_status=True, connector=tcp_connector)

    if console_params.module:
        module_name = console_params.module[0]
        module_options = console_params.options
        module = importlib.import_module(f'.{module_name}', 'steam_tools_ng.console')

        asyncio.ensure_future(module.run(*module_options))  # type: ignore
    else:
        if os.environ.get('GTK_DEBUG', False):
            from src.gtk import application
        else:
            # noinspection PyUnresolvedReferences
            from steam_tools_ng.gtk import application

        from gi.repository import Gtk

        if sys.platform.startswith("linux") and not os.getenv('DISPLAY'):
            log.critical('The DISPLAY is not set!')
            log.critical('Use -c / --cli <module> for the command line interface.')
            sys.exit(1)

        app = application.Application(http_session)
        app.register()
        app.activate()


        async def async_gtk_iterator() -> None:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

            await asyncio.sleep(0.01)

            if app.window and app.window.get_realized():
                asyncio.ensure_future(async_gtk_iterator())
            else:
                event_loop.stop()
                app.quit()


        asyncio.ensure_future(async_gtk_iterator())

    try:
        event_loop.run_forever()
    finally:
        log.info(_("Exiting..."))

        unfinished_tasks = asyncio.Task.all_tasks()

        for task in unfinished_tasks:
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                event_loop.run_until_complete(task)

        event_loop.run_until_complete(http_session.close())
        # FIXME https://github.com/aio-libs/aiohttp/issues/1925
        event_loop.run_until_complete(asyncio.sleep(1))
        event_loop.close()
