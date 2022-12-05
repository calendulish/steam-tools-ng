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

from multiprocessing import freeze_support

import argparse
import logging
import sys
import textwrap
from pathlib import Path

from steam_tools_ng import config, i18n, __version__
from steam_tools_ng.console import cli

_ = i18n.get_translation
log = logging.getLogger(__name__)


def main() -> None:
    freeze_support()
    config.init()

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
        'module',
        choices=['steamguard', 'steamtrades', 'steamgifts', 'cardfarming', 'fakerun'],
        metavar='<module>',
        action='store',
        nargs='?',
        help='Start a module',
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
        '-v', '--version',
        action='store_true',
        help='Show version',
        dest='version',
    )

    command_parser.add_argument(
        'options',
        metavar='<options>',
        nargs='*',
        help=argparse.SUPPRESS,
    )

    console_params = command_parser.parse_args()
    config.init_logger()

    if console_params.version:
        print(__version__)
        sys.exit(0)

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
    print('Copyright (C) 2015 ~ 2022 Lara Maia - <dev@lara.monster>')

    if console_params.add_authenticator:
        app = cli.SteamToolsNG('add_authenticator', '')
        app.run()
        sys.exit(0)

    if not console_params.module:
        log.critical('No module has scheduled to run.')
        log.critical("Use 'steam-tools-ng-gui' for the graphical user interface.")
        sys.exit(1)

    module_name = console_params.module
    module_options = console_params.options

    app = cli.SteamToolsNG(module_name, module_options)
    app.run()


if __name__ == "__main__":
    main()
