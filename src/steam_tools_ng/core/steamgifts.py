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
import logging
import random
from typing import Generator

import aiohttp
from stlib import plugins, login

from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main() -> Generator[utils.ModuleData, None, None]:
    yield utils.ModuleData(status=_("Loading"))

    if plugins.has_plugin("steamgifts"):
        steamgifts = plugins.get_plugin("steamgifts")
    else:
        raise ImportError(_("Unable to find Steamgifts plugin."))

    wait_min = config.parser.getint("steamgifts", "wait_min")
    wait_max = config.parser.getint("steamgifts", "wait_max")
    type_ = config.parser.get("steamgifts", "giveaway_type")
    pinned = config.parser.get("steamgifts", "developer_giveaways")
    sort = config.parser.get("steamgifts", "sort")
    reverse = config.parser.getboolean("steamgifts", "reverse_sorting")

    try:
        await steamgifts.do_login()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"), info=_("Waiting Changes"))
        await asyncio.sleep(15)
        return
    except steamgifts.TooFast:
        yield utils.ModuleData(error=_("Unable to login. Trying again in 15 seconds"))
        await asyncio.sleep(15)
        return
    except steamgifts.UserSuspended:
        yield utils.ModuleData(error=_("User is suspended."))
        await asyncio.sleep(18000)
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
        await steamgifts.configure()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return
    except steamgifts.ConfigureError:
        yield utils.ModuleData(error=_("Unable to configure steamgifts."))
        await asyncio.sleep(20)
        return

    try:
        giveaways = await steamgifts.get_giveaways(type_, pinned_giveaways=pinned)
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return

    joined = False

    if giveaways:
        if sort:
            giveaways = sorted(
                giveaways,
                key=lambda giveaway_: getattr(giveaway_, sort),
                reverse=reverse,
            )
    else:
        yield utils.ModuleData(status=_("No giveaways to join."))
        joined = True

    for index, giveaway in enumerate(giveaways):
        yield utils.ModuleData(level=(index, len(giveaway)))

        max_ban_wait = random.randint(5, 15)
        for past_time in range(max_ban_wait):
            try:
                yield utils.ModuleData(level=(past_time, max_ban_wait))
            except KeyError:
                yield utils.ModuleData(level=(0, 0))

            await asyncio.sleep(1)

        try:
            if await steamgifts.join(giveaway):
                yield utils.ModuleData(
                    display=giveaway.id,
                    status="{} {} ({}:{}:{})".format(_("Joined!"), *giveaway[:4]),
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

            if steamgifts.user_info.points <= 2:
                break
            else:
                continue

    if not joined:
        await asyncio.sleep(10)
        return

    wait_offset = random.randint(wait_min, wait_max)
    log.debug(_("Setting wait_offset from steamgifts to %s."), wait_offset)
    for past_time in range(wait_offset):
        yield utils.ModuleData(
            info=_("Waiting more {} minutes.").format(round((wait_offset - past_time) / 60)),
            level=(past_time, wait_offset),
        )

        await asyncio.sleep(1)
