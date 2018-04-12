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
import logging
import os
from typing import Any, Callable, NamedTuple, NewType, Optional, Union

config_parser = configparser.RawConfigParser()
log = logging.getLogger(__name__)

if os.name == 'nt':
    data_dir = os.environ['LOCALAPPDATA']
else:
    data_dir = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))

config_file_directory = os.path.join(data_dir, 'steam-tools-ng')
config_file_name = 'steam-tools-ng.config'
config_file = os.path.join(config_file_directory, config_file_name)

ConfigStr = NewType('ConfigStr', str)
ConfigInt = NewType('ConfigInt', int)
ConfigBool = NewType('ConfigBool', bool)
ConfigFloat = NewType('ConfigFloat', float)

Config = NamedTuple(
    'Config', [
        ('section', str),
        ('option', str),
        ('value', Union[ConfigStr, ConfigInt, ConfigBool, ConfigFloat])
    ]
)


class DefaultConfig(object):
    log_directory = ConfigStr(os.path.join(data_dir, 'steam-tools-ng'))
    log_level = ConfigStr('debug')
    log_console_level = ConfigStr('info')
    log_color = ConfigBool(True)


class Check(object):
    def __init__(self, section) -> None:
        self.section = section

    def __call__(self, function_: Callable[..., Any]) -> Any:
        log.debug('Loading new configs from %s', config_file)
        config_parser.read(config_file)
        new_parameters = {}
        signature = inspect.signature(function_)

        for option in signature.parameters.values():
            value_type = option.annotation
            # noinspection PyUnusedLocal
            value: Union[ConfigStr, ConfigInt, ConfigBool, ConfigFloat]

            try:
                if value_type in [ConfigStr, Optional[ConfigStr]]:
                    value = ConfigStr(config_parser.get(self.section, option.name))
                elif value_type is [ConfigInt, Optional[ConfigInt]]:
                    value = ConfigInt(config_parser.getint(self.section, option.name))
                elif value_type is [ConfigBool, Optional[ConfigBool]]:
                    value = ConfigBool(config_parser.getboolean(self.section, option.name))
                elif value_type is [ConfigFloat, Optional[ConfigFloat]]:
                    value = ConfigFloat(config_parser.getfloat(self.section, option.name))
                else:
                    log.debug('Nothing to do with {}. Ignoring.'.format(option))
                    continue
            except configparser.NoOptionError:
                log.debug('Option not found in config: %s', option.name)
            except configparser.NoSectionError:
                log.debug('Section not found in config: %s', self.section)
                config_parser.add_section(self.section)
            else:
                log.debug('%s will be injected into %s', option.name, function_.__name__)
                new_parameters[option.name] = value

        if new_parameters:
            return functools.partial(function_, **new_parameters)
        else:
            return function_


def init() -> None:
    os.makedirs(config_file_directory, exist_ok=True)

    if os.path.isfile(config_file):
        config_parser.read(config_file)
    else:
        log.debug('No config file found.')


def new(*new_configs: Config) -> None:
    for config in new_configs:
        if not config_parser.has_section(config.section):
            config_parser.add_section(config.section)

        config_parser.set(config.section, config.option, str(config.value))

    with open(config_file, 'w') as config_file_object:
        log.debug('Saving new configs at %s', config_file_object)
        config_parser.write(config_file_object)
