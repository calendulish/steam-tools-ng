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
from stlib import authenticator, steamtrades, webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


@config.Check("login")
async def on_get_login_data(
        api_http: webapi.Http,
        authenticator_code: str,
        steamid: Optional[config.ConfigStr] = None,
        token: Optional[config.ConfigStr] = None,
        token_secure: Optional[config.ConfigStr] = None,
) -> Dict[str, str]:
    while True:
        if not steamid or not token or not token_secure:
            log.critical(_("Unable to find a valid login data on config file or command line"))

            username = config.ConfigStr(str(utils.safe_input(_("Please, write your username"))))
            assert isinstance(username, str), "safe_input is returning an invalid username"
            password = getpass.getpass(_("Please, write your password (it's hidden, and will be encrypted):"))
            assert isinstance(password, str), "safe_input is returning and invalid password"
            public_key = await api_http.get_public_key(username)
            encrypted_password = webapi.encrypt_password(public_key[0], password.encode())
            del password

            log.debug(_("Trying to login on Steam..."))

            steam_login_data = await api_http.do_login(
                username,
                encrypted_password,
                public_key[1],
                ''.join(authenticator_code[0])
            )

            if not steam_login_data['success']:
                log.critical("Unable to log-in on Steam")
                try_again = utils.safe_input(_("Do you want to try again?"), True)

                if not try_again:
                    raise aiohttp.ClientConnectionError()
                else:
                    continue

            logging.info(_("Success!"))

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
                logging.info(_("Configuration has been saved!"))

        return {
            'steamLogin': f'{steamid}%7C%7C{token}',
            'steamLoginSecure': f'{steamid}%7C%7C{token_secure}'
        }


@config.Check("authenticator")
async def on_get_code(shared_secret: Optional[config.ConfigStr] = None) -> Any:
    if not shared_secret:
        log.critical(_("Authenticator module is not configured"))
        log.critical(_("Please, run 'authenticator' module, set up it, and try again"))
        sys.exit(1)

    return authenticator.get_code(shared_secret)


@config.Check("steamtrades")
async def run(
        trade_ids: Optional[config.ConfigStr] = None,
        wait_min: Union[config.ConfigInt, int] = 3700,
        wait_max: Union[config.ConfigInt, int] = 4100,
) -> None:
    if not trade_ids:
        logging.critical("No trade ID found in config file")
        sys.exit(1)

    authenticator_code = await on_get_code()

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        api_http = webapi.Http(session, 'https://lara.click/api')
        login_data = await on_get_login_data(api_http, authenticator_code)
        session.cookie_jar.update_cookies(login_data)
        await api_http.do_openid_login('https://steamtrades.com/?login')

        trades_http = steamtrades.Http(session)

        while True:
            current_datetime = time.strftime('%B, %d, %Y - %H:%M:%S')
            trades = [trade.strip() for trade in trade_ids.split(',')]

            for trade_id in trades:
                try:
                    trade_info = await trades_http.get_trade_info(trade_id)
                except (IndexError, aiohttp.ClientResponseError):
                    logging.error('Unable to find id: %s. Ignoring...', trade_id)
                    continue

                result = await trades_http.bump(trade_info)

                if result['success']:
                    log.info("%s (%s) Bumped! [%s]", trade_info.id, trade_info.title, current_datetime)
                elif result['reason'] == 'Not Ready':
                    log.warning(
                        "%s (%s) Already bumped. Waiting more %d minutes",
                        trade_info.id,
                        trade_info.title,
                        result['minutes_left']
                    )
                    wait_min = result['minutes_left'] * 60
                    wait_max = wait_min + 400
                elif result['reason'] == 'trade is closed':
                    log.error("%s (%s) is closed. Ignoring...", trade_info.id, trade_info.title)
                    continue

            wait_offset = random.randint(wait_min, wait_max)
            for past_time in range(wait_offset):
                print("Waiting: {:4d} seconds".format(wait_offset - past_time), end='\r')
                await asyncio.sleep(1)
            print()  # keep history
