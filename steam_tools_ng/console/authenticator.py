#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2019
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
import base64
import logging
import sys
import time

import aiohttp
from stlib import webapi, plugins, universe

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


async def run(plugin_manager: plugins.Manager) -> int:
    api_url = config.parser.get('steam', 'api_url')
    webapi_session = webapi.SteamWebAPI(utils.http_session(), api_url)
    time_offset = await config.time_offset(webapi_session)
    steam_login_status = await utils.check_login(session, webapi_session, time_offset)

    if not steam_login_status:
        sys.exit(1)

    shared_secret = config.parser.get("login", "shared_secret")

    if shared_secret:
        try:
            base64.b64decode(shared_secret)
        except ValueError:
            log.critical(_('%s is not a valid parameter'), shared_secret)
            return 1
    else:
        log.critical(_("No shared_secret found on config file or command line"))
        return 1

    while True:
        server_time = int(time.time()) - time_offset
        auth_code = universe.generate_steam_code(server_time, shared_secret)
        seconds = 30 - (server_time % 30)

        for past_time in range(seconds):
            progress = '█' * int(past_time / seconds * 10)
            print(_("SteamGuard Code:"), "{} ┌{:10}┐".format(auth_code, progress), end='\r')
            await asyncio.sleep(1)
