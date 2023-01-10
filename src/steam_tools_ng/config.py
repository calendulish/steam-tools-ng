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
from collections import OrderedDict

import asyncio
import configparser
import locale
import logging
import os
import site
import sys
from pathlib import Path
from typing import Any, Mapping

from stlib import plugins as stlib_plugins
from . import i18n, logger_handlers

parser = configparser.RawConfigParser()
log = logging.getLogger(__name__)

if Path('src').is_dir():
    # development mode
    data_dir = Path('config')
elif hasattr(sys, 'frozen') or sys.platform == 'win32':
    data_dir = Path(os.environ['LOCALAPPDATA'])
else:
    data_dir = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config'))

config_file_directory = data_dir / 'steam-tools-ng'
config_file_name = 'steam-tools-ng.config'
config_file = config_file_directory / config_file_name

try:
    from stlib import client
except ImportError as exception:
    log.error(str(exception))
    client = None


def _(message):
    return message


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
    ("coupons", _("Free Coupons")),
    ("confirmations", _("Confirmations")),
    ("steamtrades", _("Steam Trades")),
    ("steamgifts", _("Steam Gifts")),
    ("steamguard", _("Steam Guard")),
    ("cardfarming", _("Card Farming")),
])

coupon_discounts = OrderedDict([
    ("33", _("33% OFF")),
    ("50", _("50% OFF")),
    ("66", _("66% OFF")),
    ("75", _("75% OFF")),
    ("90", _("90% OFF")),
])

_ = i18n.get_translation

if sys.platform == 'win32':
    event_loop = asyncio.ProactorEventLoop()
    file_manager = 'explorer'
else:
    file_manager = 'xdg-open'
    event_loop = asyncio.new_event_loop()

asyncio.set_event_loop(event_loop)

default_config: Mapping[str, Mapping[str, Any]] = {
    'logger': {
        'log_directory': data_dir / 'steam-tools-ng',
        'log_level': 'debug',
        'log_console_level': 'info',
        'log_color': True,
    },
    'steam': {
        'api_url': 'https://api.steampowered.com',
    },
    'coupons': {
        'enable': True,
        'botid_to_donate': '76561198018370992',
        'botids': '76561198018370992',
        'appid': '753',
        'contextid': '3',
        'token_to_donate': '6Z6Xn5NM',
        'tokens': '6Z6Xn5NM',
        'blacklist': '',
        'last_trade_time': 0,
        'minimum_discount': 75,
    },
    'confirmations': {
        'enable': True,
    },
    'steamguard': {
        'enable': True,
    },
    'steamtrades': {
        'enable': True,
        'wait_for_bump': 3700,
        'trade_ids': '',
    },
    'steamgifts': {
        'enable': True,
        'wait_for_giveaways': 3700,
        'giveaway_type': 'main',
        'developer_giveaways': 'True',
        'sort': 'name',
        'reverse_sorting': False,
    },
    'cardfarming': {
        'enable': True,
        'reverse_sorting': False,
        'mandatory_waiting': 7200,
        'wait_while_running': 300,
        'wait_for_drops': 120,
        'max_concurrency': 50,
        'invisible': True,
    },
    'fakerun': {
        'cakes': '',
    },
    'general': {
        'theme': 'light',
        'show_close_button': True,
        'language': str(locale.getdefaultlocale()[0]),
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
    file_handler, console_handler, *extra_handlers = logging.root.handlers

    if type_ == "console":
        console_handler.setLevel(level)
    else:
        file_handler.setLevel(level)


def validate_config(section: str, option: str, defaults: OrderedDict[str, str]) -> None:
    value = parser.get(section, option)

    if value and value not in defaults.keys():
        if option == 'language':
            log.error(_("Unsupported language requested. Fallbacking to English."))
            new('general', 'language', 'en')
            return

        raise configparser.Error(_("Please, fix your config file. Available values for {}:\n{}").format(
            option,
            ', '.join(defaults.keys()),
        ))


def init() -> None:
    config_file_directory.mkdir(parents=True, exist_ok=True)
    parser.read_dict(default_config)

    if config_file.is_file():
        parser.read(config_file)

    # fallback deprecated values
    if (parser.get('steam', 'api_url') in [
        'https://api.lara.monster', 'https://api.lara.click',
    ]):
        new('steam', 'api_url', default_config['steam']['api_url'])

    log_directory = Path(parser.get("logger", "log_directory"))

    if not log_directory.is_dir():
        log.error(_("Incorrect log directory. Fallbacking to default."))
        log_directory = data_dir / 'steam-tools-ng'
        new("logger", "log_directory", log_directory)

    validate_config("logger", "log_level", log_levels)
    validate_config("logger", "log_console_level", log_levels)
    validate_config("general", "theme", gtk_themes)
    validate_config("general", "language", translations)
    validate_config("steamgifts", "giveaway_type", giveaway_types)
    validate_config("steamgifts", "sort", giveaway_sort_types)

    log_directory.mkdir(parents=True, exist_ok=True)

    stlib_plugins.add_search_paths(
        str(Path(os.getcwd(), 'lib', 'stlib-plugins')),
        *[str(Path(site_, 'stlib-plugins')) for site_ in site.getsitepackages()],
        str(Path(site.getusersitepackages(), 'stlib-plugins')),
    )

    if not stlib_plugins.has_plugin("steamtrades"):
        new("steamtrades", "enable", False)

    if not stlib_plugins.has_plugin("steamgifts"):
        new("steamgifts", "enable", False)

    if not client:
        new("cardfarming", "enable", False)


def init_logger() -> None:
    log_directory = Path(parser.get("logger", "log_directory"))
    log_level = parser.get("logger", "log_level")
    log_console_level = parser.get("logger", "log_console_level")

    log_file_handler = logger_handlers.RotatingFileHandler(log_directory / 'steam-tools-ng.log',
                                                           backupCount=1,
                                                           encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(name)s:%(levelname)s (%(funcName)s) => %(message)s'))
    log_file_handler.setLevel(getattr(logging, log_level.upper()))

    try:
        log_file_handler.doRollover()
    except PermissionError:
        log.debug(_("Unable to open steam-tools-ng.log"))
        log_file_handler.close()
        log_file_handler = logger_handlers.NullHandler()  # type: ignore

    log_console_handler = logger_handlers.ColoredStreamHandler()
    log_console_handler.setLevel(getattr(logging, log_console_level.upper()))

    if 'gtk' not in sys.modules:
        log_console_handler.setLevel(logging.WARNING)

    # noinspection PyArgumentList
    logging.basicConfig(level=logging.DEBUG, handlers=[log_file_handler, log_console_handler])


def new(section: str, option: str, value: Any) -> None:
    if option == "log_level":
        update_log_level("file", value)
    elif option == "log_console_level":
        update_log_level("console", value)

    if parser.get(section, option, fallback='') != str(value):
        log.debug(_('Saving {}:{} on config file').format(section, option))
        parser.set(section, option, str(value))

        with open(config_file, 'w', encoding="utf8") as config_file_object:
            parser.write(config_file_object)
    else:
        log.debug(_('Not saving {}:{} because values are already updated').format(section, option))


def remove(section: str, option: str) -> None:
    # Some GUI checks will fail if option doesn't exists
    new(section, option, '')
    # parser.remove_option(section, option)

    # with open(config_file, 'w', encoding="utf8") as config_file_object:
    #    parser.write(config_file_object)
