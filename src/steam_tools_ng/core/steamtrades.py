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

    if plugins.has_plugin("steamtrades"):
        steamtrades = plugins.get_plugin("steamtrades")
    else:
        raise ImportError(_("Unable to find Steamtrades plugin"))

    trade_ids = config.parser.get("steamtrades", "trade_ids")
    wait_min = config.parser.getint("steamtrades", "wait_min")
    wait_max = config.parser.getint("steamtrades", "wait_max")

    if not trade_ids:
        yield utils.ModuleData(error=_("No trade ID found"), info=_("Waiting Changes"))
        await asyncio.sleep(5)
        return

    trades = [trade.strip() for trade in trade_ids.split(',')]

    try:
        await steamtrades.do_login()
    except aiohttp.ClientError:
        yield utils.ModuleData(error=_("Check your connection. (server down?)"))
        await asyncio.sleep(15)
        return
    except steamtrades.TooFast:
        yield utils.ModuleData(error=_("Unable to login. Trying again in 15 seconds"))
        await asyncio.sleep(15)
        return
    except steamtrades.UserSuspended:
        yield utils.ModuleData(error=_("User is suspended."))
        await asyncio.sleep(18000)
        return
    except steamtrades.PrivateProfile:
        yield utils.ModuleData(error=_("Your profile must be public to use steamtrades."), info=_("Waiting Changes"))
        await asyncio.sleep(30)
        return
    except steamtrades.UserLevelError:
        yield utils.ModuleData(error=_("You must be level 1 or greater to use steamtrades."))
        await asyncio.sleep(300)
        return
    except login.LoginError:
        yield utils.ModuleData(error=_("User is not logged in. Trying again in 30 seconds"))
        await asyncio.sleep(30)
        return

    bumped = False

    for trade_id in trades:
        try:
            trade_info = await steamtrades.get_trade_info(trade_id)
        except (IndexError, aiohttp.ClientResponseError):
            yield utils.ModuleData(error=_("Unable to find trade id"))
            bumped = False
            break
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Check your connection. (server down?)"))
            bumped = False
            break

        yield utils.ModuleData(display=trade_info.id, info=trade_info.title)
        max_ban_wait = random.randint(5, 15)
        for past_time in range(max_ban_wait):
            try:
                yield utils.ModuleData(level=(past_time, max_ban_wait))
            except KeyError:
                yield utils.ModuleData(level=(0, 0))

            await asyncio.sleep(1)

        try:
            if await steamtrades.bump(trade_info):
                yield utils.ModuleData(display=trade_id, info=_("Bumped!"))
                bumped = True
            else:
                yield utils.ModuleData(display=trade_id, error=_("Unable to bump"))
                await asyncio.sleep(5)
                continue
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Check your connection. (server down?)"))
            await asyncio.sleep(10)
            bumped = False
            break
        except steamtrades.NoTradesError:
            yield utils.ModuleData(error=_("No trades available to bump"))
            await asyncio.sleep(15)
            continue
        except steamtrades.TradeNotReadyError as exception:
            wait_min = exception.time_left * 60
            wait_max = wait_min + 400
            bumped = True
        except steamtrades.TradeClosedError as exception:
            yield utils.ModuleData(error=_("Trade {}({}) is closed").format(exception.title, exception.id))
            await asyncio.sleep(5)
            continue
        except login.LoginError:
            yield utils.ModuleData(error=_("Login is lost. Trying to relogin."))
            await asyncio.sleep(5)
            bumped = False
            break

    if not bumped:
        await asyncio.sleep(10)
        return

    wait_offset = random.randint(wait_min, wait_max)
    log.debug(_("Setting wait_offset from steamtrades to %s"), wait_offset)
    for past_time in range(wait_offset):
        yield utils.ModuleData(
            info=_("Waiting more {} minutes").format(round(wait_offset / 60)),
            level=(past_time, wait_offset),
        )

        await asyncio.sleep(1)
