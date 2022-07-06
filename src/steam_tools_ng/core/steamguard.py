#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
import binascii
import time
from typing import Generator

from stlib import universe

from . import utils
from .. import i18n, config

_ = i18n.get_translation


async def main(time_offset: int) -> Generator[utils.ModuleData, None, None]:
    shared_secret = config.parser.get("login", "shared_secret")

    try:
        if not shared_secret:
            config.new("plugins", "steamguard", "false")
            raise ValueError

        server_time = int(time.time()) - time_offset
        auth_code = universe.generate_steam_code(server_time, shared_secret)
    except (ValueError, binascii.Error):
        yield utils.ModuleData(error=_("The current shared secret is invalid."), info=_("Waiting Changes"))
        await asyncio.sleep(10)
    except ProcessLookupError:
        yield utils.ModuleData(status=_("Steam Client is not running"), info=_("Waiting Changes"))
        await asyncio.sleep(10)
    else:
        yield utils.ModuleData(status=_("Loading..."))

        seconds = 30 - (server_time % 30)

        for past_time in range(seconds * 8):
            yield utils.ModuleData(
                display=auth_code,
                status=_("Running"),
                info=_("New code in {} seconds").format(seconds * 8 - past_time),
                level=(past_time, seconds * 8),
            )

            await asyncio.sleep(0.125)
