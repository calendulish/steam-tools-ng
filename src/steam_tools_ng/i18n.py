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

from importlib import resources

# Never use VHL methods in this file to avoid infinite recursion:
# [method>get_translation->vhlm->get_translation->vhlm] IT'S NOT A BUG!
import configparser
import gettext
import hashlib
from typing import Dict

from . import config

cache: Dict[bytes, str] = {}


def new_hash(text: str) -> bytes:
    sums = hashlib.sha256(text.encode())

    return sums.digest()


def get_translation(text: str) -> str:
    try:
        language = config.parser.get('general', 'language')
    except configparser.NoSectionError:
        # assume that config is not fully loaded yet
        return text

    with resources.as_file(resources.files('steam_tools_ng')) as path:
        translation = gettext.translation("steam-tools-ng", path / 'locale', languages=[language], fallback=True)
        translated_text = translation.gettext(text)
        cache[new_hash(translated_text)] = text

    return translated_text
