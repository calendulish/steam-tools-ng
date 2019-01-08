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
import logging
import random
import sys
import time

import aiohttp
from stlib import plugins, webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


async def run(session: aiohttp.ClientSession, plugin_manager: plugins.Manager) -> None:
    wait_min = config.parser.getint("steamgifts", "wait_min")
    wait_max = config.parser.getint("steamgifts", "wait_max")
    giveaway_type = config.parser.get("steamgifts", "giveaway_type")
    pinned_giveaways = config.parser.get("steamgifts", "developer_giveaways")
    sort_giveaways = config.parser.get("steamgifts", "sort")
    reverse_sorting = config.parser.getboolean("steamgifts", "reverse_sorting")
    api_url = config.parser.get('steam', 'api_url')
    webapi_session = webapi.SteamWebAPI(session, api_url)

    if plugin_manager.has_plugin("steamgifts"):
        steamgifts = plugin_manager.load_plugin('steamgifts')
        steamgifts_session = steamgifts.Main(session, api_url=api_url)
    else:
        log.critical(_("Unable to find steamgifts plugin"))
        sys.exit(1)

    log.info(_("Loading, please wait..."))
    time_offset = await config.time_offset(webapi_session)
    steam_login_status = await utils.check_login(session, webapi_session, time_offset)

    if not steam_login_status:
        sys.exit(1)

    try:
        await steamgifts_session.do_login()
    except aiohttp.ClientError:
        logging.critical(_("No connection"))
        sys.exit(1)

    try:
        await steamgifts_session.configure()
    except steamgifts.ConfigureError:
        log.critical(_("Unable to configure steamgifts"))
        sys.exit(1)

    while True:
        current_datetime = time.strftime('%B, %d, %Y - %H:%M:%S')
        giveaways = await steamgifts_session.get_giveaways(giveaway_type, pinned_giveaways=pinned_giveaways)

        if giveaways and sort_giveaways:
            # FIXME: check if config is valid
            giveaways = sorted(
                giveaways,
                key=lambda giveaway_: getattr(giveaway_, sort_giveaways),
                reverse=reverse_sorting,
            )
        else:
            log.info(_("No giveaways to join."))
            wait_min //= 2
            wait_max //= 2

        for giveaway in giveaways:
            antiban_max = random.randint(5, 15)
            for past_time in range(antiban_max):
                print(_("Waiting anti-ban timer") + f" ({antiban_max - past_time})", end='\r')
                await asyncio.sleep(1)

            try:
                if await steamgifts_session.join(giveaway):
                    log.info(
                        _("Joined! %s (%s:%s:%s) [%s]"),
                        giveaway.name,
                        giveaway.copies,
                        giveaway.points,
                        giveaway.level,
                        current_datetime,
                    )
                else:
                    log.error(_("Unable to join %s"), giveaway.id)
                    await asyncio.sleep(5)
                    continue
            except steamgifts.NoGiveawaysError as exception:
                log.error(str(exception))
                await asyncio.sleep(15)
                continue
            except steamgifts.GiveawayEndedError as exception:
                log.error(str(exception))
                await asyncio.sleep(5)
                continue
            except webapi.LoginError as exception:
                log.info(_("Login is lost. Trying to relogin."))
                await asyncio.sleep(5)
                break
            except steamgifts.NoLevelError as exception:
                log.error(_("User don't have required level to join"))
                await asyncio.sleep(5)
                continue
            except steamgifts.NoPointsError as exception:
                log.error(_("User don't have required points to join"))
                await asyncio.sleep(5)

                if steamgifts_session.user_info.points <= 2:
                    break
                else:
                    continue

        wait_offset = random.randint(wait_min, wait_max)
        for past_time in range(wait_offset):
            print(_("Waiting: {:4d} seconds").format(wait_offset - past_time), end='\r')
            await asyncio.sleep(1)
        print()  # keep history
