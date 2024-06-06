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
import aiohttp
import asyncio
import binascii
import logging
from typing import AsyncGenerator

from stlib import universe, webapi
from . import utils
from .. import i18n, config

try:
    from stlib import client
except ImportError as exception:
    client = None

log = logging.getLogger(__name__)
_ = i18n.get_translation


@utils.time_offset_cache(ttl=3600)
def cached_server_time() -> int:
    if not client:
        raise ProcessLookupError

    with client.SteamGameServer() as server:
        real_time = server.get_server_real_time()
        assert isinstance(real_time, int)
        return real_time


async def main() -> AsyncGenerator[utils.ModuleData, None]:
    shared_secret = config.parser.get("login", "shared_secret")
    webapi_session = webapi.SteamWebAPI.get_session(0)

    try:
        server_time = cached_server_time()
    except ProcessLookupError:
        yield utils.ModuleData(error=_("Steam is not running."), info=_("Fallbacking server time to WebAPI"))

        try:
            server_time = await webapi_session.get_server_time()
        except aiohttp.ClientError:
            raise aiohttp.ClientError(
                _(
                    "Unable to Connect. You can try these things:\n"
                    "1. Check your connection\n"
                    "2. Check if Steam Server isn't down\n"
                    "3. Check if Steam Client is running\n"
                )
            )

    try:
        if not shared_secret:
            config.new("steamguard", "enable", "false")
            raise ValueError

        auth_code = universe.generate_steam_code(server_time, shared_secret)
    except (ValueError, binascii.Error):
        yield utils.ModuleData(error=_("The current shared secret is invalid."), info=_("Waiting Changes"))
        await asyncio.sleep(10)
    except ProcessLookupError:
        yield utils.ModuleData(status=_("Steam Client is not running"), info=_("Waiting Changes"))
        await asyncio.sleep(10)
    else:
        log.info(_("New code in 30 seconds"))
        seconds = 30 - (server_time % 30)

        for past_time in range(seconds * 8):
            yield utils.ModuleData(
                display=auth_code,
                status=_("Running"),
                info=_("New code in {} seconds").format(seconds - round(past_time / 8)),
                level=(past_time, seconds * 8),
                suppress_logging=True,
            )

            await asyncio.sleep(0.125)
