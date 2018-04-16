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

import logging
from typing import Optional, Union

log = logging.getLogger(__name__)


def safe_input(msg: str, default_response: Optional[bool] = None) -> Union[bool, str]:
    if default_response is True:
        options = _('[Y/n]')
    elif default_response is False:
        options = _('[y/N]')
    else:
        options = ''

    while True:
        try:
            user_input = input(f'{msg} {options}: ')

            if default_response is None:
                if len(user_input) > 2:
                    return user_input
                else:
                    raise ValueError(_('Invalid response from user'))
            elif not user_input:
                return default_response

            if user_input.lower() == _('y'):
                return True
            elif user_input.lower() == _('n'):
                return False
            else:
                raise ValueError(_(f'{user_input} is not an accepted value'))
        except ValueError as exception:
            log.error(exception.args[0])
            log.error(_('Please, try again.'))
