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

if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'src')):
    data_dir = 'config'
    icons_dir = 'icons'
elif sys.platform == 'win32':
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


class Default:
    @staticmethod
    def _logger(option: str) -> Union[str, bool]:
        log_directory = ConfigStr(os.path.join(data_dir, 'steam-tools-ng'))
        log_level = ConfigStr('debug')
        log_console_level = ConfigStr('info')
        log_color = ConfigBool(True)

        return locals()[option]

    @staticmethod
    def _locale(option: str) -> str:
        language = ConfigStr(str(locale.getdefaultlocale()[0]))

        return locals()[option]

    @staticmethod
    def _steamtrades(option: str) -> int:
        wait_min = ConfigInt(3700)
        wait_max = ConfigInt(4100)

        return locals()[option]

    @staticmethod
    def _gtk(option: str) -> str:
        theme = ConfigStr("light")

        return locals()[option]

    @classmethod
    def get(cls, section: str, option: str) -> Optional[ConfigType]:
        try:
            default_value = getattr(cls(), f'_{section}')(option)
            log.debug(_("Using fallback value for {}:{} ({})".format(section, option, default_value)))
        except (AttributeError, ValueError, KeyError):
            default_value = None
            log.debug(_("No value found for {}:{}. Using None").format(section, option))

        return default_value


class Check(object):
    def __init__(self, section: str) -> None:
        self.section = section

    def __call__(self, function_: Callable[..., Any]) -> Any:
        signature = inspect.signature(function_)

        def wrapped_function(*args: Any, **kwargs: Any) -> Any:
            new_parameters = {}

            for index, option in enumerate(signature.parameters.values()):
                if len(args) >= index + 1:
                    log.debug(_("A positional argument already exists for %s. Ignoring..."), option.name)
                    continue

                log.debug(_('Loading config for %s:%s'), self.section, option.name)

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


def _get(section: str, option: str, type_: str) -> ConfigValue:
    log.debug(_("Loading config for {}:{}").format(section, option))

    if type_ == 'str':
        get_method = config_parser.get
    else:
        get_method = getattr(config_parser, f'get{type_}')

    return get_method(section, option, fallback=Default.get(section, option))


def get(section: str, option: str) -> ConfigType:
    value = ConfigStr(_get(section, option, 'str'))
    return ConfigType(section, option, value)


def getint(section: str, option: str) -> ConfigType:
    value = ConfigInt(_get(section, option, 'int'))
    return ConfigType(section, option, value)


def getfloat(section: str, option: str) -> ConfigType:
    value = ConfigInt(_get(section, option, 'float'))
    return ConfigType(section, option, value)


def getboolean(section: str, option: str) -> ConfigType:
    value = ConfigInt(_get(section, option, 'boolean'))
    return ConfigType(section, option, value)


def init() -> None:
    os.makedirs(config_file_directory, exist_ok=True)

    if os.path.isfile(config_file):
        config_parser.read(config_file)

    log_directory = get("logger", "log_directory")
    log_level = get("logger", "log_level")
    log_console_level = get("logger", "log_console_level")

    os.makedirs(log_directory.value, exist_ok=True)

    log_file_handler = logger_handlers.RotatingFileHandler(os.path.join(log_directory.value, 'steam-tools-ng.log'),
                                                           backupCount=1,
                                                           encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    log_file_handler.setLevel(getattr(logging, log_level.value.upper()))

    try:
        log_file_handler.doRollover()
    except PermissionError:
        log.debug(_("Unable to open steam-tools-ng.log"))
        log_file_handler.close()
        log_file_handler = logger_handlers.NullHandler()  # type: ignore

    log_console_handler = logger_handlers.ColoredStreamHandler()
    log_console_handler.setLevel(getattr(logging, log_console_level.value.upper()))

    logging.basicConfig(level=logging.DEBUG, handlers=[log_file_handler, log_console_handler])


def new(*new_configs: ConfigType) -> None:
    for config in new_configs:
        if config.option == "log_level":
            update_log_level("file", config.value)
        elif config.option == "log_console_level":
            update_log_level("console", config.value)

        if not config_parser.has_section(config.section):
            config_parser.add_section(config.section)

        if get(config.section, config.option).value != str(config.value):
            log.debug(_('Saving %s:%s on config file'), config.section, config.option)
            config_parser.set(config.section, config.option, str(config.value))

            with open(config_file, 'w') as config_file_object:
                config_parser.write(config_file_object)
        else:
            log.debug(_('Not saving %s:%s because values are already updated'), config.section, config.option)


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
