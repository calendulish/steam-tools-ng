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
import aiohttp
import asyncio
import logging
import random
from typing import AsyncGenerator

from stlib import plugins, login
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main() -> AsyncGenerator[utils.ModuleData, None]:
    yield utils.ModuleData(status=_("Loading"))

    if plugins.has_plugin("steamgifts"):
        steamgifts = plugins.get_plugin("steamgifts")
        steamgifts_session = steamgifts.Main.get_session(0)
    else:
        raise ImportError(_("Unable to find Steamgifts plugin."))

    wait_for_giveaways = config.parser.getint("steamgifts", "wait_for_giveaways")
    type_ = config.parser.get("steamgifts", "giveaway_type")
    pinned = config.parser.get("steamgifts", "developer_giveaways")
    sort = config.parser.get("steamgifts", "sort")
    reverse = config.parser.getboolean("steamgifts", "reverse_sorting")

    try:
        await steamgifts_session.do_login()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
        await asyncio.sleep(15)
        return
    except steamgifts.TooFast:
        yield utils.ModuleData(error=_("Unable to login. Trying again in 15 seconds"))
        await asyncio.sleep(15)
        return
    except steamgifts.UserSuspended:
        module_data = utils.ModuleData(error=_("User is suspended."))

        async for data in utils.timed_module_data(18000, module_data):
            yield data

        return
    except steamgifts.PrivateProfile:
        yield utils.ModuleData(error=_("Your profile must be public to use steamgifts."), info=_("Waiting Changes"))
        await asyncio.sleep(30)
        return
    except login.LoginError:
        yield utils.ModuleData(error=_("User is not logged in. Trying again in 30 seconds"))
        await asyncio.sleep(30)
        return

    try:
        await steamgifts_session.configure()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return
    except steamgifts.ConfigureError:
        yield utils.ModuleData(error=_("Unable to configure steamgifts."))
        await asyncio.sleep(20)
        return

    try:
        giveaways = await steamgifts_session.get_giveaways(type_, pinned_giveaways=pinned)
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return

    joined = False

    if giveaways:
        if sort:
            giveaways = sorted(
                giveaways,
                key=lambda giveaway_: getattr(giveaway_, sort),  # type: ignore
                reverse=reverse,
            )
    else:
        yield utils.ModuleData(status=_("No giveaways to join."))
        joined = True

    for index, giveaway in enumerate(giveaways):
        yield utils.ModuleData(level=(index, len(giveaway)))

        module_data = utils.ModuleData(display=giveaway.id, info=giveaway.name)
        max_ban_wait = random.randint(5, 15)

        async for data in utils.timed_module_data(max_ban_wait, module_data):
            yield data

        try:
            if await steamgifts_session.join(giveaway):
                yield utils.ModuleData(
                    display=giveaway.id,
                    status=f"{_('Joined')} {giveaway.name} "
                           f"(C:{giveaway.copies} P:{giveaway.points} L:{giveaway.level})",
                )
                joined = True
            else:
                yield utils.ModuleData(display=giveaway.id, error=_("Unable to join {}."))
                await asyncio.sleep(5)
                continue
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Check your connection. (server down?)"))
            await asyncio.sleep(15)
            joined = False
            break
        except steamgifts.NoGiveawaysError:
            yield utils.ModuleData(error=_("No giveaways available to join."))
            await asyncio.sleep(15)
            continue
        except steamgifts.GiveawayEndedError:
            yield utils.ModuleData(error=_("Giveaway is already ended."))
            await asyncio.sleep(5)
            continue
        except login.LoginError:
            yield utils.ModuleData(error=_("Login is lost. Trying to relogin."))
            await asyncio.sleep(5)
            joined = False
            break
        except steamgifts.NoLevelError:
            yield utils.ModuleData(error=_("User don't have required level to join."))
            await asyncio.sleep(5)
            continue
        except steamgifts.NoPointsError:
            yield utils.ModuleData(error=_("User don't have required points to join."))
            await asyncio.sleep(5)

            if steamgifts_session.user_info.points <= 2:
                break

            continue

    if not joined:
        await asyncio.sleep(10)
        return

    wait_offset = random.randint(wait_for_giveaways, wait_for_giveaways + 400)
    module_data = utils.ModuleData(info=_("Waiting Changes"))

    async for data in utils.timed_module_data(wait_offset, module_data):
        yield data
