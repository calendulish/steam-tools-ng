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
import configparser
import locale
import logging
import os
import sys
from typing import Dict, Any

from . import i18n, logger_handlers

parser = configparser.RawConfigParser()
log = logging.getLogger(__name__)
_ = i18n.get_translation

if os.path.isdir('src'):
    data_dir = 'config'
    icons_dir = 'icons'
elif hasattr(sys, 'frozen') or sys.platform == 'win32':
    data_dir = os.environ['LOCALAPPDATA']
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'share', 'icons')
else:
    data_dir = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    icons_dir = os.path.abspath(os.path.join(os.path.sep, 'usr', 'share', 'steam-tools-ng', 'icons'))

config_file_directory = os.path.join(data_dir, 'steam-tools-ng')
config_file_name = 'steam-tools-ng.config'
config_file = os.path.join(config_file_directory, config_file_name)
log_levels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']


def update_log_level(type_: str, level_string: str) -> None:
    level = getattr(logging, level_string.upper())
    file_handler, console_handler = logging.root.handlers

    if type_ == "console":
        console_handler.setLevel(level)
    else:
        file_handler.setLevel(level)


def init() -> None:
    os.makedirs(config_file_directory, exist_ok=True)

    parser.read_dict(
        {
            'logger': {
                'log_directory': os.path.join(data_dir, 'steam-tools-ng'),
                'log_level': 'debug',
                'log_console_level': 'info',
                'log_color': True,
            },
            'locale': {
                'language': str(locale.getdefaultlocale()[0])
            },
            'steam': {
                'api_url': 'https://api.lara.click',
            },
            'steamtrades': {
                'wait_min': 3700,
                'wait_max': 4100,
                'trade_ids': None,
            },
            'steamgifts': {
                'wait_min': 3700,
                'wait_max': 4100,
                'giveaway_type': 'main',
                'developer_giveaways': 'True',
                'sort': 'name',
                'reverse_sorting': False,
            },
            'cardfarming': {
                'reverse_sorting': False,
                'wait_min': 480,
                'wait_max': 600,
            },
            'gtk': {
                'theme': 'light',
            },
            'plugins': {
                'steamtrades': True,
                'steamgifts': True,
                'cardfarming': True,
                'steamguard': True,
            },
            'login': {
                'steamid': 0,
                'deviceid': None,
                'token': None,
                'token_secure': None,
                'oauth_token': None,
                'account_name': None,
                'shared_secret': None,
                'identity_secret': None,
                'nickname': None,
            },
        }
    )

    if os.path.isfile(config_file):
        parser.read(config_file)

    log_directory = parser.get("logger", "log_directory")
    log_level = parser.get("logger", "log_level")
    log_console_level = parser.get("logger", "log_console_level")

    if log_level and not log_level.upper() in log_levels:
        raise configparser.Error(
            _("Please, fix your config file. Accepted values for log_level are:\n{}").format(
                ', '.join(log_levels),
            )
        )

    if log_console_level and not log_console_level.upper() in log_levels:
        raise configparser.Error(
            _("Please, fix your config file. Accepted values for log_console_level are:\n{}").format(
                ', '.join(log_levels),
            )
        )

    os.makedirs(log_directory, exist_ok=True)


def init_logger() -> None:
    log_directory = parser.get("logger", "log_directory")
    log_level = parser.get("logger", "log_level")
    log_console_level = parser.get("logger", "log_console_level")

    log_file_handler = logger_handlers.RotatingFileHandler(os.path.join(log_directory, 'steam-tools-ng.log'),
                                                           backupCount=1,
                                                           encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(module)s:%(levelname)s => %(message)s'))
    log_file_handler.setLevel(getattr(logging, log_level.upper()))

    try:
        log_file_handler.doRollover()
    except PermissionError:
        log.debug(_("Unable to open steam-tools-ng.log"))
        log_file_handler.close()
        log_file_handler = logger_handlers.NullHandler()  # type: ignore

    log_console_handler = logger_handlers.ColoredStreamHandler()
    log_console_handler.setLevel(getattr(logging, log_console_level.upper()))

    logging.basicConfig(level=logging.DEBUG, handlers=[log_file_handler, log_console_handler])


def new(section: str, option: str, value: Any) -> None:
    if option == "log_level":
        update_log_level("file", value)
    elif option == "log_console_level":
        update_log_level("console", value)

    if parser.get(section, option) != str(value):
        log.debug(_('Saving %s:%s on config file'), section, option)
        parser.set(section, option, str(value))

        with open(config_file, 'w') as config_file_object:
            parser.write(config_file_object)
    else:
        log.debug(_('Not saving %s:%s because values are already updated'), section, option)


def login_cookies() -> Dict[str, str]:
    steamid = parser.getint("login", "steamid")
    token = parser.get("login", "token")
    token_secure = parser.get("login", "token_secure")

    if not steamid or not token or not token_secure:
        return {}

    return {
        'steamLogin': f'{steamid}%7C%7C{token}',
        'steamLoginSecure': f'{steamid}%7C%7C{token_secure}',
    }
