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

import logging
from typing import Any, Dict, Optional

from stlib import authenticator

from ui import config, console_utils

log = logging.getLogger(__name__)


async def on_get_json_from_adb(adb: Any, *names: str) -> Dict[str, str]:
    while True:
        try:
            json_data = await adb.get_json(*names)
        except AttributeError as exception:
            log.critical(exception.args[0])
            try_again = console_utils.safe_input(_("Do you want to try again?"), True)

            if not try_again:
                raise exception
        else:
            return json_data


@config.Check('authenticator')
def on_connect_to_adb(adb_path: Optional[config.ConfigStr] = None) -> Any:
    while True:
        if not adb_path:
            user_input = console_utils.safe_input(_("Paste here the path to your adb 'binary'"))
            assert isinstance(user_input, str), "safe_input is returning an invalid user_input"
            adb_path = config.ConfigStr(user_input)

        try:
            adb = authenticator.AndroidDebugBridge(adb_path)
        except FileNotFoundError as exception:
            log.critical(exception.args[0])
            try_again = console_utils.safe_input(_("Do you want to try again?"), True)

            if not try_again:
                raise exception
            else:
                adb_path = None
        else:
            return adb
