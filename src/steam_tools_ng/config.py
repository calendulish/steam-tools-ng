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
import configparser
import locale
import logging
import os
import site
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List

import sys
from stlib import login
from stlib import plugins as stlib_plugins

from . import i18n, logger_handlers

log = logging.getLogger(__name__)
script_dir = Path(__file__).resolve().parent

if (script_dir / 'src').is_dir() or (script_dir / 'portable_mode.txt').is_file():
    data_dir = script_dir / 'config'
elif hasattr(sys, 'frozen') or sys.platform == 'win32':
    data_dir = Path(os.environ['LOCALAPPDATA'])
else:
    data_dir = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config'))

config_file_directory = data_dir / 'steam-tools-ng'

try:
    from stlib import client
except ImportError as exception:
    log.error(str(exception))
    client = None


# translation module isn't initialized yet
def _(message: str) -> str:
    return message


gtk_themes = OrderedDict([
    ('default', _("Default")),
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
    ('main', _("No restriction")),
    ('new', _("New Giveaways")),
    ('recommended', _("Recommended")),
    ('wishlist', _("Wishlist")),
    ('group', _('Group')),
    ('dlc', _('DLC')),
    ('region_restricted', _("Region Restricted")),
])

giveaway_sort_types = OrderedDict([
    ('name+', _("Name (A-Z)")),
    ('name-', _("Name (Z-A)")),
    ('copies+', _("Copies (0..99)")),
    ('copies-', _("Copies (99..0)")),
    ('points+', _("Points (0-50)")),
    ('points-', _("Points (50-0)")),
    ('level+', _("Level (0-100)")),
    ('level-', _("Level (100-0)")),
])

steamgifts_modes = OrderedDict([
    ('run_all_and_restart', _('Run all and restart\nRun all strategies and restart')),
    ('stop_after_minimum_and_wait', _('Stop and wait\nafter minimum points')),
    ('stop_after_minimum_and_restart', _('Stop and restart\nafter minimum points')),
])

plugins = OrderedDict([
    ("coupons", _("Free Coupons")),
    ("confirmations", _("Confirmations")),
    ("steamtrades", _("Steam Trades")),
    ("steamgifts", _("Steam Gifts")),
    ("steamguard", _("Steam Guard")),
    ("cardfarming", _("Card Farming")),
    ("market", _("Market Monitor")),
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
    file_manager = 'explorer'
else:
    file_manager = 'xdg-open'

default_global_config: Dict[str, Dict[str, Any]] = {
    'logger': {
        'log_directory': data_dir / 'steam-tools-ng',
        'log_level': 'debug',
        'log_console_level': 'info',
        'log_color': True,
    },
    'steam': {
        'api_url': 'https://api.steampowered.com',
    },
    'general': {
        'theme': 'default',
        'show_close_button': True,
        'language': str(locale.getdefaultlocale()[0]),
    },
}

default_config: Dict[str, Dict[str, Any]] = {
    'coupons': {
        'enable': True,
        'botid_to_donate': '76561199642778394',
        'botids': '76561199642778394',
        'appid': '753',
        'contextid': '3',
        'token_to_donate': 'BsccNcth',
        'tokens': 'BsccNcth',
        'blacklist': '',
        'last_trade_time': 0,
        'minimum_discount': 75,
    },
    'market': {
        'enable': True,
    },
    'steamguard': {
        'enable': True,
        'enable_confirmations': True,
    },
    'steamtrades': {
        'enable': False,
        'wait_for_bump': 3700,
        'trade_ids': '',
    },
    'steamgifts': {
        'enable': False,
        'developer_giveaways': 'True',
        'mode': 'run_all_and_restart',
        'wait_after_each_strategy': 10,
        'wait_after_full_cycle': 3700,
        'minimum_points': 0,
    },
    'cardfarming': {
        'enable': False,
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
    'login': {
        'steamid': 0,
        'deviceid': '',
        'account_name': '',
        'shared_secret': '',
        'identity_secret': '',
        'password': '',
    },
}

for index in range(1, 6):
    default_config[f'steamgifts_strategy{index}'] = {
        'enable': False,
        'minimum_points': 0,
        'maximum_points': 50,
        'minimum_level': 0,
        'maximum_level': 100,
        'minimum_copies': 1,
        'maximum_copies': 999999,
        'minimum_metascore': 0,
        'maximum_metascore': 100,
        'minimum_entries': 0,
        'maximum_entries': 999999,
        'restrict_type': "main",
        'sort_type': "name+",
    }

    if index == 1:
        default_config[f'steamgifts_strategy{index}']['enable'] = True

_parser_cache: Dict[int, configparser.RawConfigParser] = {}


def get_parser(session_index: int) -> configparser.RawConfigParser:
    if session_index in _parser_cache:
        return _parser_cache[session_index]

    parser = configparser.RawConfigParser()
    _parser_cache[session_index] = parser

    if session_index == 0:
        parser.read_dict(default_global_config)
    else:
        parser.read_dict(default_config)

    return parser


def update_log_level(type_: str, level_string: str) -> None:
    level = getattr(logging, level_string.upper())
    file_handler, console_handler, *extra_handlers = logging.root.handlers

    if type_ == "console":
        console_handler.setLevel(level)
    else:
        file_handler.setLevel(level)


def validate_config(session_index: int, section: str, option: str, defaults: OrderedDict[str, str]) -> None:
    _configparser = get_parser(session_index)
    value = _configparser.get(section, option)

    if value and value not in defaults.keys():
        if option == 'language':
            log.error(_("Unsupported language requested. Fallbacking to English."))
            new(session_index, 'general', 'language', 'en')
            return

        raise configparser.Error(_("Please, fix your config file. Available values for {}:\n{}").format(
            option,
            ', '.join(defaults.keys()),
        ))


def init(users: List[int]) -> None:
    config_file_directory.mkdir(parents=True, exist_ok=True)

    stlib_plugins.add_search_paths(
        str(Path(os.getcwd(), 'lib', 'stlib-plugins')),
        *[str(Path(site_, 'stlib-plugins')) for site_ in site.getsitepackages()],
        str(Path(site.getusersitepackages(), 'stlib-plugins')),
    )

    for session_index in users:
        config_file = config_file_directory / f'steam-tools-ng.session{session_index}.config'

        if not config_file.is_file() and session_index == 1:
            deprecated_config_file = config_file_directory / 'steam-tools-ng.config'

            if deprecated_config_file.is_file():
                log.warning(_("Migrating old config file for multiuser support"))
                deprecated_config = configparser.RawConfigParser()
                deprecated_config.read(deprecated_config_file)

                for section in default_global_config.keys():
                    deprecated_config.remove_section(section)

                with open(deprecated_config_file, 'w', encoding="utf8") as config_file_object:
                    deprecated_config.write(config_file_object)

                del deprecated_config
                deprecated_config_file.rename(config_file)

        _configparser = get_parser(session_index)

        if config_file.is_file():
            _configparser.read(config_file)

        validate_config(session_index, "steamgifts", "mode", steamgifts_modes)

        for _index in range(1, 4):
            validate_config(session_index, f"steamgifts_strategy{_index}", "restrict_type", giveaway_types)
            validate_config(session_index, f"steamgifts_strategy{_index}", "sort_type", giveaway_sort_types)

        if not stlib_plugins.has_plugin("steamtrades"):
            new(session_index, "steamtrades", "enable", False)

        if not stlib_plugins.has_plugin("steamgifts"):
            new(session_index, "steamgifts", "enable", False)

        if not client:
            new(session_index, "cardfarming", "enable", False)

    global_config = get_parser(0)
    global_config_file = config_file_directory / 'steam-tools-ng.global.config'

    if global_config_file.is_file():
        global_config.read(global_config_file)

    log_directory = Path(global_config.get("logger", "log_directory"))

    if not log_directory.is_dir():
        log.error(_("Incorrect log directory. Fallbacking to default."))
        log_directory = data_dir / 'steam-tools-ng'
        new(0, "logger", "log_directory", log_directory)

    validate_config(0, "logger", "log_level", log_levels)
    validate_config(0, "logger", "log_console_level", log_levels)
    validate_config(0, "general", "theme", gtk_themes)
    validate_config(0, "general", "language", translations)

    log_directory.mkdir(parents=True, exist_ok=True)

    if sys.platform == 'win32':
        event_loop = asyncio.ProactorEventLoop()
    else:
        event_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(event_loop)


def init_logger() -> None:
    global_config = get_parser(0)
    log_directory = Path(global_config.get("logger", "log_directory"))
    log_level = global_config.get("logger", "log_level")
    log_console_level = global_config.get("logger", "log_console_level")

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
    log_console_level = getattr(logging, log_console_level.upper())
    log_console_handler.setLevel(log_console_level)

    log_stlib = logging.getLogger('stlib')
    log_stlib.setLevel(logging.DEBUG)

    # TODO: ColoredStreamHandler isn't working from root log
    log_stlib.propagate = False
    log_stlib_handler = logger_handlers.ColoredStreamHandler()
    log_stlib_handler.setLevel(log_console_level)
    log_stlib.addHandler(log_stlib_handler)
    log_stlib.addHandler(log_file_handler)

    if 'gtk' not in sys.modules:
        log_console_handler.setLevel(logging.WARNING)

    # noinspection PyArgumentList
    logging.basicConfig(level=logging.DEBUG, handlers=[log_file_handler, log_console_handler])


def new(session_index: int, section: str, option: str, value: Any) -> None:
    if option == "log_level":
        update_log_level("file", value)
    elif option == "log_console_level":
        update_log_level("console", value)

    _configparser = get_parser(session_index)

    if _configparser.get(section, option, fallback='') != str(value):
        log.debug(_('Saving {}:{} on config file').format(section, option))
        _configparser.set(section, option, str(value))

        if session_index == 0:
            config_file = config_file_directory / "steam-tools-ng.global.config"
        else:
            config_file = config_file_directory / f'steam-tools-ng.session{session_index}.config'

        with open(config_file, 'w', encoding="utf8") as config_file_object:
            _configparser.write(config_file_object)
    else:
        log.debug(_('Not saving {}:{} because values are already updated').format(section, option))


def remove(session_index: int, section: str, option: str) -> None:
    # Some GUI checks will fail if option doesn't exist
    new(session_index, section, option, '')
    # parser.remove_option(section, option)

    # with open(config_file, 'w', encoding="utf8") as config_file_object:
    #    parser.write(config_file_object)


def update_steamid_from_cookies(session_index: int) -> None:
    login_session = login.Login.get_session(session_index)
    store_cookies = login_session.http_session.cookie_jar.filter_cookies('https://store.steampowered.com')
    steamid = store_cookies['steamLoginSecure'].value.split('%7')[0]
    new(session_index, "login", "steamid", steamid)


async def load_cookies(session_index: int, login_session: login.Login) -> bool:
    cookies_file = config_file_directory / f"cookiejar.session{session_index}"

    if cookies_file.is_file():
        login_session.http_session.cookie_jar.load(cookies_file)

        if await login_session.is_logged_in():
            log.info(_("Steam login Successul (session {})").format(session_index))
            return True

    return False


def save_cookies(session_index: int, login_session: login.Login) -> None:
    cookies_file = config_file_directory / f"cookiejar.session{session_index}"
    login_session.http_session.cookie_jar.save(cookies_file)


def reset(users: List[int]) -> None:
    for session_index in users:
        (config_file_directory / f"cookiejar.session{session_index}").unlink(missing_ok=True)
        (config_file_directory / f"steam-tools-ng.session{session_index}.config").unlink(missing_ok=True)

    logging.root.removeHandler(logging.root.handlers[0])
    global_config = get_parser(0)
    log_directory = global_config.get("logger", "log_directory")
    (log_directory / 'steam-tools-ng.log').unlink()
    (log_directory / 'steam-tools-ng.log.1').unlink()

    log.warning(_('Config cleaned!'))
