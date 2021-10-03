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
import configparser
import http
import locale
import logging
import os
import sys
import time
from collections import OrderedDict
from typing import Any

import aiohttp
from stlib import webapi, client

from . import i18n, logger_handlers

parser = configparser.RawConfigParser()
log = logging.getLogger(__name__)
_ = i18n.get_translation

if os.path.isdir('steam_tools_ng'):
    # development mode
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

gtk_themes = OrderedDict([
    ('light', _("Light")),
    ('dark', _("Dark")),
])

log_levels = OrderedDict([
    ('critical', _("Critical")),
    ('error', _("Error")),
    ('warning', _("Warning")),
    ('info', _("Info")),
    ('debug', _("Debug")),
])

translations = OrderedDict([
    ('en', _("English")),
    ('pt_BR', _("Portuguese (Brazil)")),
    ('fr', _("French")),
])

giveaway_types = OrderedDict([
    ('main', _("Main Giveaways")),
    ('new', _("New Giveaways")),
    ('recommended', _("Recommended")),
    ('wishlist', _("Wishlist Only")),
    ('group', _('Group Only')),
])

giveaway_sort_types = OrderedDict([
    ('name', _("Name")),
    ('copies', _("Copies")),
    ('points', _("Points")),
    ('level', _("Level")),
])

plugins = OrderedDict([
    ("confirmations", _("Confirmations")),
    ("steamtrades", _("Steam Trades")),
    ("steamgifts", _("Steam Gifts")),
    ("steamguard", _("Steam Guard")),
    ("cardfarming", _("Card Farming")),
])

if sys.platform == 'win32':
    event_loop = asyncio.ProactorEventLoop()
    file_manager = 'explorer'
else:
    file_manager = 'xdg-open'
    event_loop = asyncio.new_event_loop()

asyncio.set_event_loop(event_loop)

default_config = {
    'logger': {
        'log_directory': os.path.join(data_dir, 'steam-tools-ng'),
        'log_level': 'debug',
        'log_console_level': 'info',
        'log_color': True,
    },
    'steam': {
        'api_url': 'https://api.steampowered.com',
        'api_key': '',
    },
    'steamtrades': {
        'wait_min': 3700,
        'wait_max': 4100,
        'trade_ids': '',
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
    'general': {
        'theme': 'light',
        'show_close_button': True,
        'language': str(locale.getdefaultlocale()[0]),
    },
    'plugins': {
        'steamtrades': True,
        'steamgifts': True,
        'cardfarming': True,
        'steamguard': True,
        'confirmations': True,
    },
    'login': {
        'steamid': 0,
        'deviceid': '',
        'token': '',
        'token_secure': '',
        'oauth_token': '',
        'account_name': '',
        'shared_secret': '',
        'identity_secret': '',
        'password': '',
    },
}


def update_log_level(type_: str, level_string: str) -> None:
    level = getattr(logging, level_string.upper())
    file_handler, console_handler = logging.root.handlers

    if type_ == "console":
        console_handler.setLevel(level)
    else:
        file_handler.setLevel(level)


def validate_config(section: str, option: str, defaults: OrderedDict) -> None:
    value = parser.get(section, option)

    if value and not value in defaults.keys():
        if option == 'language':
            log.error(_("Unsupported language requested. Fallbacking to English."))
            new('general', 'language', 'en')
            return

        raise configparser.Error(_("Please, fix your config file. Available values for {}:\n{}").format(
            option,
            ', '.join(defaults.keys()),
        ))


def init() -> None:
    os.makedirs(config_file_directory, exist_ok=True)

    parser.read_dict(default_config)

    if os.path.isfile(config_file):
        parser.read(config_file)

    # fallback deprecated values
    if (parser.get('steam', 'api_url') in [
        'https://api.lara.monster', 'https://api.lara.click',
    ]):
        new('steam', 'api_url', default_config['steam']['api_url'])

    log_directory = parser.get("logger", "log_directory")

    if not os.path.isdir(log_directory):
        log.error(_("Incorrect log directory. Fallbacking to default."))
        log_directory = os.path.join(data_dir, 'steam-tools-ng')
        new("logger", "log_directory", log_directory)

    validate_config("logger", "log_level", log_levels)
    validate_config("logger", "log_console_level", log_levels)
    validate_config("general", "theme", gtk_themes)
    validate_config("general", "language", translations)
    validate_config("steamgifts", "giveaway_type", giveaway_types)
    validate_config("steamgifts", "sort", giveaway_sort_types)

    os.makedirs(log_directory, exist_ok=True)


def init_logger() -> None:
    log_directory = parser.get("logger", "log_directory")
    log_level = parser.get("logger", "log_level")
    log_console_level = parser.get("logger", "log_console_level")

    log_file_handler = logger_handlers.RotatingFileHandler(os.path.join(log_directory, 'steam-tools-ng.log'),
                                                           backupCount=1,
                                                           encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(module)s:%(levelname)s (%(funcName)s) => %(message)s'))
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
        log.debug(_('Saving {}:{} on config file').format(section, option))
        parser.set(section, option, str(value))

        with open(config_file, 'w', encoding="utf8") as config_file_object:
            parser.write(config_file_object)
    else:
        log.debug(_('Not saving {}:{} because values are already updated').format(section, option))


def remove(section: str, option: str) -> None:
    parser.remove_option(section, option)

    with open(config_file, 'w', encoding="utf8") as config_file_object:
        parser.write(config_file_object)


def login_cookies() -> http.cookies.SimpleCookie:
    steamid = parser.getint("login", "steamid")
    token = parser.get("login", "token")
    token_secure = parser.get("login", "token_secure")

    if not steamid or not token or not token_secure:
        log.warning(_("No login cookies"))
        return {}

    cookies_dict = {
        'steamLogin': f'{steamid}%7C%7C{token}',
        'steamLoginSecure': f'{steamid}%7C%7C{token_secure}',
    }

    return http.cookies.SimpleCookie(cookies_dict)


async def time_offset(webapi_session: webapi.SteamWebAPI) -> int:
    try:
        with client.SteamGameServer() as server:
            server_time = server.get_server_time()
    except ProcessLookupError:
        log.warning(_("Steam is not running."))
        log.debug(_("Fallbacking time offset to WebAPI"))

        while True:
            try:
                server_time = await webapi_session.get_server_time()
            except aiohttp.ClientError:
                raise aiohttp.ClientError(
                    _(
                        "Unable to Connect. You can try these things:\n"
                        "1. Check your connection\n"
                        "2. Check if Steam Server isn't down\n"
                        "3. Check if api_url and api_key is correct on config file\n"
                    )
                )
            else:
                break

    return int(time.time()) - server_time
