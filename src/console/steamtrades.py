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
    trade_ids = config.get("steamtrades", "trade_ids")
    wait_min = config.getint("steamtrades", "wait_min")
    wait_max = config.getint("steamtrades", "wait_max")
    api_url = config.get('steam', 'api_url')
    webapi_session = webapi.SteamWebAPI(session, api_url.value)

    if plugin_manager.has_plugin("steamtrades"):
        steamtrades = plugin_manager.load_plugin('steamtrades')
        steamtrades_session = steamtrades.Main(session, api_url=api_url.value)
    else:
        log.critical("Unable to find steamtrades plugin")
        sys.exit(1)

    if not trade_ids.value:
        logging.critical("No trade ID found in config file")
        sys.exit(1)

    log.info(_("Loading, please wait..."))
    steam_login_status = await utils.check_login(session, webapi_session)

    if not steam_login_status:
        sys.exit(1)

    try:
        await steamtrades_session.do_login()
    except aiohttp.ClientConnectionError:
        logging.critical(_("No connection"))
        sys.exit(1)

    while True:
        current_datetime = time.strftime('%B, %d, %Y - %H:%M:%S')
        trades = [trade.strip() for trade in trade_ids.value.split(',')]

        for trade_id in trades:
            try:
                trade_info = await steamtrades_session.get_trade_info(trade_id)
            except (IndexError, aiohttp.ClientResponseError):
                log.error('Unable to find id: %s. Ignoring...', trade_id)
                continue

            try:
                bump_result = await steamtrades_session.bump(trade_info)
            except steamtrades.TradeNotReadyError as exception:
                log.warning(
                    "%s (%s) Already bumped. Waiting more %d minutes",
                    trade_info.id,
                    trade_info.title,
                    exception.time_left,
                )
                wait_min = config.ConfigType('steamtrades', 'wait_min', config.ConfigInt(exception.time_left * 60))
                wait_max = config.ConfigType('steamtrades', 'wait_max', config.ConfigInt(wait_min.value + 400))
            except steamtrades.TradeClosedError:
                log.error("%s (%s) is closed. Ignoring...", trade_info.id, trade_info.title)
                continue
            else:
                if bump_result:
                    log.info("%s (%s) Bumped! [%s]", trade_info.id, trade_info.title, current_datetime)
                else:
                    log.error('Unable to bump %s (%s). Ignoring...', trade_info.id, trade_info.title)

        wait_offset = random.randint(wait_min.value, wait_max.value)
        for past_time in range(wait_offset):
            print("Waiting: {:4d} seconds".format(wait_offset - past_time), end='\r')
            await asyncio.sleep(1)
        print()  # keep history
