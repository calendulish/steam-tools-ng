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

import base64
import logging
import time
from typing import Optional

from stlib import authenticator

from ui import authenticator_utils, config, console_utils

log = logging.getLogger(__name__)


@config.Check('authenticator')
async def on_start_authenticator(shared_secret: Optional[config.ConfigStr] = None) -> int:
    try:
        base64.b64decode(shared_secret)
    except ValueError:
        log.critical(f'{shared_secret} is not a valid parameter')
        return 1
    except TypeError:
        log.critical("No shared_secret found on config file.")

        use_adb = console_utils.safe_input("Do you want to get it now using adb?", False)
        if use_adb:
            try:
                adb = authenticator_utils.on_connect_to_adb()
                secret = await authenticator_utils.on_get_secret_from_adb(adb, 'shared')
                shared_secret = config.ConfigStr(secret.decode())
            except (FileNotFoundError, AttributeError):
                logging.critical("Failed to get shared_secret!")
                return 1

            logging.info("Success!")

            save_config = console_utils.safe_input("Do you want to save this configuration?", True)
            if save_config:
                config.new(config.Config('authenticator', 'shared_secret', shared_secret))
                logging.info("Configuration has been saved!")
        else:
            return 1

    while True:
        try:
            auth_code, epoch = authenticator.get_code(shared_secret)
        except ProcessLookupError:
            logging.critical("Steam Client is not running.")
            try_again = console_utils.safe_input("Try again?", True)
            if try_again:
                continue
            else:
                return 1

        seconds = 30 - (epoch % 30)

        for past_time in range(seconds):
            progress = '█' * int(past_time / seconds * 10)
            print("SteamGuard Code: {} ┌{:10}┐".format(''.join(auth_code), progress), end='\r')
            time.sleep(1)
