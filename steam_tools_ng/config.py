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
import functools
import inspect
import locale
import logging
import os
import sys
from typing import Any, Callable, Dict, NamedTuple, NewType, Optional, Union

from . import i18n, logger_handlers

config_parser = configparser.RawConfigParser()
log = logging.getLogger(__name__)
_ = i18n.get_translation

if sys.platform == 'win32':
    data_dir = os.environ['LOCALAPPDATA']
    icons_dir = os.path.join('share', 'icons')
else:
    data_dir = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    icons_dir = os.path.abspath(os.path.join(os.path.sep, 'usr', 'share', 'steam-tools-ng', 'icons'))

config_file_directory = os.path.join(data_dir, 'steam-tools-ng')
config_file_name = 'steam-tools-ng.config'
config_file = os.path.join(config_file_directory, config_file_name)

ConfigStr = NewType('ConfigStr', str)
ConfigInt = NewType('ConfigInt', int)
ConfigBool = NewType('ConfigBool', bool)
ConfigFloat = NewType('ConfigFloat', float)

ConfigValue = Union[ConfigStr, ConfigInt, ConfigBool, ConfigFloat]


class ConfigType(NamedTuple):
    section: str
    option: str
    value: ConfigValue


class DefaultConfig(object):
    log_directory = ConfigStr(os.path.join(data_dir, 'steam-tools-ng'))
    log_level = ConfigStr('debug')
    log_console_level = ConfigStr('info')
    log_color = ConfigBool(True)
    language = ConfigStr(str(locale.getdefaultlocale()[0]))


class Check(object):
    def __init__(self, section: str) -> None:
        self.section = section

    def __call__(self, function_: Callable[..., Any]) -> Any:
        log.debug(_('Loading new configs from %s'), config_file)
        config_parser.read(config_file)
        new_parameters = {}
        signature = inspect.signature(function_)

        def wrapped_function(*args: Any, **kwargs: Any) -> Any:
            for index, option in enumerate(signature.parameters.values()):
                if len(args) >= index + 1:
                    log.debug(_("A positional argument already exists for %s. Ignoring..."), option.name)
                    continue

                # noinspection PyUnusedLocal
                value: Union[ConfigStr, ConfigInt, ConfigBool, ConfigFloat]

                try:
                    if 'ConfigStr' in str(option.annotation):
                        value = ConfigStr(config_parser.get(self.section, option.name))
                    elif 'ConfigInt' in str(option.annotation):
                        value = ConfigInt(config_parser.getint(self.section, option.name))
                    elif 'ConfigBool' in str(option.annotation):
                        value = ConfigBool(config_parser.getboolean(self.section, option.name))
                    elif 'ConfigFloat' in str(option.annotation):
                        value = ConfigFloat(config_parser.getfloat(self.section, option.name))
                    else:
                        log.debug(_('Nothing to do with %s. Ignoring.'), option)
                        continue
                except configparser.NoOptionError:
                    log.debug(_('Option not found in config: %s'), option.name)
                except configparser.NoSectionError:
                    log.debug(_('Section not found in config: %s'), self.section)
                    config_parser.add_section(self.section)
                else:
                    log.debug(_('%s will be injected into %s'), option.name, function_.__name__)
                    new_parameters[option.name] = value

            if new_parameters:
                return functools.partial(function_, **new_parameters)(*args, **kwargs)
            else:
                return function_(*args, **kwargs)

        return wrapped_function


def update_log_level(type_: str, level_string: ConfigValue) -> None:
    assert isinstance(level_string, str), "Invalid log_level"
    level = getattr(logging, level_string.upper())
    file_handler, console_handler = logging.root.handlers

    if type_ == "console":
        console_handler.setLevel(level)
    else:
        file_handler.setLevel(level)


def init() -> None:
    os.makedirs(config_file_directory, exist_ok=True)

    if os.path.isfile(config_file):
        config_parser.read(config_file)

    log_directory = config_parser.get("logger", "log_directory", fallback=DefaultConfig.log_directory)
    log_level = config_parser.get("logger", "log_level", fallback=DefaultConfig.log_level)
    log_console_level = config_parser.get("logger", "log_console_level", fallback=DefaultConfig.log_console_level)

    os.makedirs(log_directory, exist_ok=True)

    log_file_handler = logger_handlers.RotatingFileHandler(os.path.join(log_directory, 'steam-tools-ng.log'),
                                                           backupCount=1,
                                                           encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
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


def new(*new_configs: ConfigType) -> None:
    for config in new_configs:
        if config.option == "log_level":
            update_log_level("file", config.value)
        elif config.option == "log_console_level":
            update_log_level("console", config.value)

        if not config_parser.has_section(config.section):
            config_parser.add_section(config.section)

        config_parser.set(config.section, config.option, str(config.value))

    with open(config_file, 'w') as config_file_object:
        log.debug(_('Saving new configs at %s'), config_file)
        config_parser.write(config_file_object)


@Check("login")
def login_cookies(
        steamid: Optional[ConfigInt] = None,
        token: Optional[ConfigStr] = None,
        token_secure: Optional[ConfigStr] = None,
) -> Dict[str, str]:
    if not steamid or not token or not token_secure:
        return {}

    return {
        'steamLogin': f'{steamid}%7C%7C{token}',
        'steamLoginSecure': f'{steamid}%7C%7C{token_secure}',
    }
