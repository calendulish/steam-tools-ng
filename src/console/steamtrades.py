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
import getpass
import logging
import random
import sys
import time
from typing import Any, Dict, Optional, Union

import aiohttp
from stlib import authenticator, plugins, webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


@config.Check("login")
async def on_get_login_data(
        session: aiohttp.ClientSession,
        authenticator_code: str,
        steamid: Optional[config.ConfigStr] = None,
        token: Optional[config.ConfigStr] = None,
        token_secure: Optional[config.ConfigStr] = None,
) -> Dict[str, str]:
    steamtrades_plugin = plugins.get_plugin('steamtrades')
    steamtrades = steamtrades_plugin.Main(session, api_url='https://lara.click/api')

    while True:
        if not steamid or not token or not token_secure:
            log.critical(_("Unable to find a valid login data on config file or command line"))

            username = config.ConfigStr(str(utils.safe_input(_("Please, write your username"))))
            assert isinstance(username, str), "safe_input is returning an invalid username"
            password = getpass.getpass(_("Please, write your password (it's hidden, and will be encrypted):"))
            assert isinstance(password, str), "safe_input is returning and invalid password"
            steam_key = await steamtrades.get_steam_key(username)
            encrypted_password = webapi.encrypt_password(steam_key, password)
            del password

            log.debug(_("Trying to login on Steam..."))

            steam_login_data = await steamtrades.do_login(
                username,
                encrypted_password,
                steam_key.timestamp,
                authenticator_code,
            )

            if not steam_login_data['success']:
                log.critical("Unable to log-in on Steam")
                try_again = utils.safe_input(_("Do you want to try again?"), True)

                if not try_again:
                    raise aiohttp.ClientConnectionError()
                else:
                    continue

            log.info(_("Success!"))

            steamid = config.ConfigStr(steam_login_data["transfer_parameters"]["steamid"])
            token = config.ConfigStr(steam_login_data["transfer_parameters"]["token"])
            token_secure = config.ConfigStr(steam_login_data["transfer_parameters"]["token_secure"])

            save_config = utils.safe_input(_("Do you want to save this configuration?"), True)
            if save_config:
                config.new(
                    config.ConfigType("login", "steamid", steamid),
                    config.ConfigType("login", "token", token),
                    config.ConfigType("login", "token_secure", token_secure),
                )
                log.info(_("Configuration has been saved!"))

        cookies = config.login_cookies(steamid, token, token_secure)
        assert isinstance(cookies, dict), "login_cookies return is not a dict"
        return cookies


@config.Check("login")
async def on_get_code(webapi_session: webapi.SteamWebAPI, shared_secret: Optional[config.ConfigStr] = None) -> Any:
    if not shared_secret:
        log.critical(_("Authenticator module is not configured"))
        log.critical(_("Please, run 'authenticator' module, set up it, and try again"))
        sys.exit(1)

    server_time = await webapi_session.get_server_time()
    return authenticator.get_code(server_time, shared_secret)


@config.Check("steamtrades")
async def run(
        session: aiohttp.ClientSession,
        trade_ids: Optional[config.ConfigStr] = None,
        wait_min: Union[config.ConfigInt, int] = 3700,
        wait_max: Union[config.ConfigInt, int] = 4100,
) -> None:
    if not trade_ids:
        logging.critical("No trade ID found in config file")
        sys.exit(1)

    log.info(_("Loading, please wait..."))
    webapi_session = webapi.SteamWebAPI(session, 'https://lara.click/api')
    authenticator_code = await on_get_code(webapi_session)

    login_data = await on_get_login_data(session, authenticator_code.code)
    session.cookie_jar.update_cookies(login_data)
    steamtrades_plugin = plugins.get_plugin('steamtrades')
    steamtrades = steamtrades_plugin.Main(session, api_url='https://lara.click/api')

    try:
        await steamtrades.do_login()
    except aiohttp.ClientConnectionError:
        logging.critical(_("No connection"))
        sys.exit(1)

    while True:
        current_datetime = time.strftime('%B, %d, %Y - %H:%M:%S')
        trades = [trade.strip() for trade in trade_ids.split(',')]

        for trade_id in trades:
            try:
                trade_info = await steamtrades.get_trade_info(trade_id)
            except (IndexError, aiohttp.ClientResponseError):
                log.error('Unable to find id: %s. Ignoring...', trade_id)
                continue

            try:
                bump_result = await steamtrades.bump(trade_info)
            except steamtrades_plugin.TradeNotReadyError as exception:
                log.warning(
                    "%s (%s) Already bumped. Waiting more %d minutes",
                    trade_info.id,
                    trade_info.title,
                    exception.time_left,
                )
                wait_min = exception.time_left * 60
                wait_max = wait_min + 400
            except steamtrades_plugin.TradeClosedError:
                log.error("%s (%s) is closed. Ignoring...", trade_info.id, trade_info.title)
                continue
            else:
                if bump_result:
                    log.info("%s (%s) Bumped! [%s]", trade_info.id, trade_info.title, current_datetime)
                else:
                    log.error('Unable to bump %s (%s). Ignoring...', trade_info.id, trade_info.title)

        wait_offset = random.randint(wait_min, wait_max)
        for past_time in range(wait_offset):
            print("Waiting: {:4d} seconds".format(wait_offset - past_time), end='\r')
            await asyncio.sleep(1)
        print()  # keep history
