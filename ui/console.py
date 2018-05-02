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

from . import authenticator_utils, config, console_utils

log = logging.getLogger(__name__)


@config.Check('authenticator')
async def on_start_authenticator(shared_secret: Optional[config.ConfigStr] = None) -> int:
    if shared_secret:
        try:
            base64.b64decode(shared_secret)
        except ValueError:
            log.critical(_(f'{shared_secret} is not a valid parameter'))
            return 1
    else:
        log.critical(_("No shared_secret found on config file or command line"))

        use_adb = console_utils.safe_input(_("Do you want to get it now using adb?"), False)
        if use_adb:
            try:
                adb = authenticator_utils.on_connect_to_adb()
                json_data = await authenticator_utils.on_get_json_from_adb(adb, 'shared_secret')
                shared_secret = config.ConfigStr(json_data['shared_secret'])
            except (FileNotFoundError, AttributeError) as exception:
                logging.critical(_("Failed to get shared_secret!"))
                logging.critical(exception.args[0])
                return 1

            logging.info(_("Success!"))

            save_config = console_utils.safe_input(_("Do you want to save this configuration?"), True)
            if save_config:
                config.new(config.Config('authenticator', 'shared_secret', shared_secret),
                           config.Config('authenticator', 'adb_path', adb.adb_path))
                logging.info(_("Configuration has been saved!"))
        else:
            return 1

    while True:
        try:
            auth_code, epoch = authenticator.get_code(shared_secret)
        except ProcessLookupError:
            logging.critical(_("Steam Client is not running."))
            try_again = console_utils.safe_input(_("Try again?"), True)
            if try_again:
                continue
            else:
                return 1

        seconds = 30 - (epoch % 30)

        for past_time in range(seconds):
            progress = '█' * int(past_time / seconds * 10)
            print(_("SteamGuard Code:"), "{} ┌{:10}┐".format(''.join(auth_code), progress), end='\r')
            time.sleep(1)
