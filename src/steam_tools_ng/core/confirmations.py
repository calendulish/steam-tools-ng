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
import inspect
import logging
from typing import AsyncGenerator, Callable, Awaitable

import aiohttp
from stlib import login, universe, community

from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main(
        steamid: universe.SteamId,
        wait_available: Callable[[], Awaitable[None]],
) -> AsyncGenerator[utils.ModuleData, None]:
    await wait_available()

    identity_secret = config.parser.get("login", "identity_secret")
    session = community.Community.get_session(0)

    if not identity_secret:
        config.new("steamguard", "enable_confirmations", "false")
        module_data = utils.ModuleData(error=_("The current identity secret is invalid."), info=_("Waiting Changes"))

        async for data in utils.timed_module_data(10, module_data):
            yield data

        return

    deviceid = config.parser.get("login", "deviceid")

    if not deviceid:
        log.warning(_("Unable to find deviceid. Generating from identity."))
        deviceid = universe.generate_device_id(identity_secret)
        config.new("login", "deviceid", deviceid)

    try:
        confirmations = await session.get_confirmations(identity_secret, steamid, deviceid)
    except AttributeError as error:
        log.error("%s[%s]: %s", inspect.trace()[-1][3], type(error).__name__, str(error))
        module_data = utils.ModuleData(error=_("Error when fetching confirmations"), info=_("Waiting Changes"))
    except ProcessLookupError:
        module_data = utils.ModuleData(error=_("Steam is not running"), info=_("Waiting Changes"))
    except login.LoginError:
        module_data = utils.ModuleData(error=_("Not logged in"), action="login")
    except aiohttp.ClientError:
        module_data = utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
    else:
        module_data = utils.ModuleData(action="update", raw_data=confirmations)

    async for data in utils.timed_module_data(30, module_data):
        yield data
