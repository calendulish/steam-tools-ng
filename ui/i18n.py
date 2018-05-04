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

import gettext
import hashlib
import locale
from typing import Any

from . import config

cache = {}


def new_hash(text):
    md5 = hashlib.md5(text.encode())

    return md5.digest()


def get_translation(text: Any) -> Any:
    language = config.config_parser.get('locale', 'language', fallback=locale.getdefaultlocale()[0])
    translation = gettext.translation("steam-tools-ng", languages=[language], fallback=True)
    translated_text = translation.gettext(text)
    cache[new_hash(translated_text)] = text

    return translated_text
