#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2021
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
import configparser
import logging
import os
import sys
import textwrap
from multiprocessing import freeze_support
from pathlib import Path

from steam_tools_ng import config, i18n, __version__

_ = i18n.get_translation
log = logging.getLogger(__name__)


def main() -> None:
    freeze_support()
    try:
        config.init()
    except configparser.Error as exception:
        if len(sys.argv) > 1:
            raise exception from None
        else:
            from steam_tools_ng.gtk import utils

            utils.fatal_error_dialog(exception, [])
            sys.exit(1)

    command_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
                Available modules | available options
                 steamguard       | [oneshot]
                 steamtrades      | [oneshot]
                 steamgifts       | [oneshot]
                 cardfarming      | [oneshot],[gameid]
                 fakerun          | <gameid>
                       '''))

    command_parser.add_argument(
        '-c', '--cli',
        choices=['steamguard', 'steamtrades', 'steamgifts', 'cardfarming', 'fakerun'],
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
        '--reset-password',
        action='store_true',
        help='Clean up saved password',
        dest='reset_password',
    )

    command_parser.add_argument(
        '--add-authenticator',
        action='store_true',
        help='Use STNG as your Steam Authenticator',
        dest='add_authenticator',
    )

    command_parser.add_argument(
        'options',
        nargs='*',
        help=argparse.SUPPRESS
    )

    console_params = command_parser.parse_args()

    if console_params.config_dir:
        os.system(f'{config.file_manager} {config.config_file_directory}')
        sys.exit(0)

    if console_params.log_dir:
        os.system(f'{config.file_manager} {config.parser.get("logger", "log_directory")}')
        sys.exit(0)

    try:
        config.init_logger()
    except configparser.Error as exception:
        if console_params.module:
            raise exception from None
        else:
            from steam_tools_ng.gtk import utils

            utils.fatal_error_dialog(exception, [])
            sys.exit(1)

    if console_params.reset:
        config.config_file.unlink(missing_ok=True)
        logging.root.removeHandler(logging.root.handlers[0])

        log_directory = config.parser.get("logger", "log_directory")
        Path(log_directory, 'steam-tools-ng.log').unlink()
        Path(log_directory, 'steam-tools-ng.log.1').unlink()

        log.info(_('Done!'))
        sys.exit(0)

    if console_params.reset_password:
        config.new("login", "password", "")
        log.info(_('Done!'))
        sys.exit(0)

    print(f'Steam Tools NG version {__version__} (Made with Girl Power <33)')
    print('Copyright (C) 2015 ~ 2021 Lara Maia - <dev@lara.monster>')

    if console_params.add_authenticator:
        from steam_tools_ng.console import cli

        app = cli.SteamToolsNG('add_authenticator', '')
        app.run()
        sys.exit(0)

    if console_params.module:
        module_name = console_params.module[0]
        module_options = console_params.options

        from steam_tools_ng.console import cli

        app = cli.SteamToolsNG(module_name, module_options)
        app.run()
    else:
        if os.name == 'nt' and hasattr(sys, 'frozen'):
            import ctypes

            console = ctypes.windll.kernel32.GetConsoleWindow()
            menu = ctypes.windll.user32.GetSystemMenu(console, False)
            ctypes.windll.user32.ShowWindow(console, False)
            ctypes.windll.user32.EnableMenuItem(menu, 0xF060, 0 | 2 | 1)
            ctypes.windll.kernel32.CloseHandle(console)

        from steam_tools_ng.gtk import async_gtk
        from steam_tools_ng.gtk import application

        if sys.platform.startswith("linux") and not os.getenv('DISPLAY'):
            log.critical('The DISPLAY is not set!')
            log.critical('Use -c / --cli <module> for the command line interface.')
            sys.exit(1)

        app = application.SteamToolsNG()
        async_gtk.run(app)


if __name__ == "__main__":
    main()
