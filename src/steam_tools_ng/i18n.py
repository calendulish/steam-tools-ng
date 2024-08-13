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

# Never use VHL methods in this file to avoid infinite recursion:
# [method>get_translation->vhlm->get_translation->vhlm] IT'S NOT A BUG!
import configparser
import gettext
import os
from importlib import resources
from pathlib import Path

from . import config


def get_translation(text: str) -> str:
    try:
        language = config.parser.get('general', 'language')
    except configparser.NoSectionError:
        # assume that config is not fully loaded yet
        return text

    with resources.as_file(resources.files('steam_tools_ng')) as path:
        locale_path = path / 'locale'

    if os.name == 'posix':
        xdg_data_home = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        mo_file = Path(language) / 'LC_MESSAGES' / 'steam-tools-ng.mo'

        test_paths = (
            locale_path,
            xdg_data_home / 'locale',
            Path('/usr/local/share/locale'),
            Path('/usr/share/locale'),
        )

        for path in test_paths:
            if (path / mo_file).is_file():
                locale_path = path
                break

    translation = gettext.translation("steam-tools-ng", locale_path, languages=[language], fallback=True)
    return translation.gettext(text)
