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
import asyncio
import logging
import random
from typing import AsyncGenerator

import aiohttp

from stlib import plugins, login
from . import utils
from .. import i18n, config

_ = i18n.get_translation
log = logging.getLogger(__name__)


async def main() -> AsyncGenerator[utils.ModuleData, None]:
    yield utils.ModuleData(status=_("Loading"))

    if not plugins.has_plugin("steamgifts"):
        raise ImportError(_("Unable to find Steamgifts plugin."))

    steamgifts = plugins.get_plugin("steamgifts")
    steamgifts_session = steamgifts.Main.get_session(0)
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

    pinned = config.parser.getboolean("steamgifts", "developer_giveaways")
    points_to_preserve = config.parser.getint("steamgifts", "minimum_points")
    mode = config.parser.get("steamgifts", "mode")
    wait_after_each_strategy = config.parser.getint("steamgifts", "wait_after_each_strategy")
    wait_after_full_cycle = config.parser.getint("steamgifts", "wait_after_full_cycle")

    for strategy_index in range(1, 6):
        strategy = f"steamgifts_strategy{strategy_index}"
        enabled = config.parser.get(strategy, "enable")

        if not enabled:
            yield utils.ModuleData(info=_("Strategy {} is disabled. Skipping.").format(strategy_index))
            continue

        type_ = config.parser.get(strategy, "restrict_type")
        minimum_points = config.parser.getint(strategy, "minimum_points")
        maximum_points = config.parser.getint(strategy, "maximum_points")
        minimum_level = config.parser.getint(strategy, "minimum_level")
        maximum_level = config.parser.getint(strategy, "maximum_level")
        minimum_copies = config.parser.getint(strategy, "minimum_copies")
        maximum_copies = config.parser.getint(strategy, "maximum_copies")
        minimum_metascore = config.parser.getint(strategy, "minimum_metascore")
        maximum_metascore = config.parser.getint(strategy, "maximum_metascore")
        minimum_entries = config.parser.getint(strategy, "minimum_entries")
        maximum_entries = config.parser.getint(strategy, "maximum_entries")

        max_ban_wait = random.randint(5, 15)
        async for data in utils.timed_module_data(max_ban_wait, utils.ModuleData()):
            yield data

        try:
            giveaways = await steamgifts_session.get_giveaways(
                type_,
                (minimum_metascore, maximum_metascore),
                (minimum_level, maximum_level),
                (minimum_entries, maximum_entries),
                (minimum_points, maximum_points),
                (minimum_copies, maximum_copies),
                pinned_giveaways=pinned,
            )
        except aiohttp.ClientError:
            yield utils.ModuleData(error=_("Check your connection. (server down?)"))
            await asyncio.sleep(15)
            return

        wait_enabled = False

        if giveaways:
            sort_type = config.parser.get(strategy, "sort_type")
            sort_name = sort_type[:-1]
            sort_direction = sort_type[-1]

            giveaways = sorted(
                giveaways,
                key=lambda giveaway_: getattr(giveaway_, sort_name),
                reverse=sort_direction == '-',
            )
        else:
            yield utils.ModuleData(status=_("No giveaways to join for strategy {}. Skipping.").format(strategy_index))
            continue

        restart = False

        for index, giveaway in enumerate(giveaways):
            module_data = utils.ModuleData(display=giveaway.id, info=giveaway.name)
            max_ban_wait = random.randint(5, 15)

            async for data in utils.timed_module_data(max_ban_wait, module_data):
                yield data

            if steamgifts_session.user_info.points <= points_to_preserve:
                yield utils.ModuleData(status=_("Minimum points reached."))
                wait_enabled = True

                if mode == 'stop_after_minimum_and_restart':
                    restart = True

                break

            yield utils.ModuleData(level=(index, len(giveaway)))

            try:
                if await steamgifts_session.join(giveaway):
                    yield utils.ModuleData(
                        display=giveaway.id,
                        status=f"{_('Joined')} {giveaway.name} "
                               f"(C:{giveaway.copies} P:{giveaway.points} L:{giveaway.level})",
                    )
                    wait_enabled = True
                else:
                    yield utils.ModuleData(display=giveaway.id, error=_("Unable to join {}."))
                    await asyncio.sleep(5)
                    continue
            except aiohttp.ClientError:
                yield utils.ModuleData(error=_("Check your connection. (server down?)"))
                await asyncio.sleep(15)
                wait_enabled = False
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
                wait_enabled = False
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

        if not wait_enabled:
            await asyncio.sleep(10)
            return

        wait_offset = random.randint(
            wait_after_each_strategy,
            wait_after_each_strategy + int(wait_after_each_strategy / 6),
        )

        module_data = utils.ModuleData(info=_("Waiting before next strategy"))

        async for data in utils.timed_module_data(wait_offset, module_data):
            yield data

        if restart:
            yield utils.ModuleData(info=_("Restarting due to mode selection"))
            break

    wait_offset = random.randint(
        wait_after_full_cycle,
        wait_after_full_cycle + int(wait_after_full_cycle / 6),
    )

    module_data = utils.ModuleData(info=_("Waiting for next cycle"))

    async for data in utils.timed_module_data(wait_offset, module_data):
        yield data
