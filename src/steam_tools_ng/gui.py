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

import os
import sys

# FIXME: Temporary workaround for cx_freeze
#  not running from Win32GUI correctly
if os.name == 'nt' and hasattr(sys, 'frozen'):
    import ctypes

    console = ctypes.windll.kernel32.GetConsoleWindow()
    ctypes.windll.user32.ShowWindow(console, 0)
    ctypes.windll.kernel32.CloseHandle(console)

from multiprocessing import freeze_support

import argparse
import configparser
import logging
from pathlib import Path
from subprocess import call
from typing import Optional, Any

from steam_tools_ng import config, i18n
from steam_tools_ng.gtk import application
from steam_tools_ng.gtk import async_gtk, utils

_ = i18n.get_translation
log = logging.getLogger(__name__)


class GraphicalArgParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: Optional[Any] = None) -> None:
        if message:
            utils.fatal_error_dialog(Exception(message), [])


def main() -> None:
    freeze_support()
    try:
        config.init()
    except configparser.Error as exception:
        utils.fatal_error_dialog(exception, [])
        sys.exit(1)

    command_parser = GraphicalArgParser(formatter_class=argparse.RawDescriptionHelpFormatter)

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

    console_params = command_parser.parse_args()

    if console_params.config_dir:
        call(f'{config.file_manager} {config.config_file_directory}')
        sys.exit(0)

    if console_params.log_dir:
        call(f'{config.file_manager} {config.parser.get("logger", "log_directory")}')
        sys.exit(0)

    try:
        config.init_logger()
    except configparser.Error as exception:
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

    if sys.platform.startswith("linux") and not os.getenv('DISPLAY'):
        log.critical('The DISPLAY is not set!')
        log.critical("Use 'steam-tools-ng' for the command line interface.")
        sys.exit(1)

    app = application.SteamToolsNG()
    async_gtk.run(app)


if __name__ == "__main__":
    main()
