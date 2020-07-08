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

from typing import NamedTuple


class _Version(NamedTuple):
    major: int = 0
    minor: int = 9
    revision: int = 4
    extra: str = ''


__version_info__ = _Version()

__version__ = '.'.join(
    [str(item) for item in __version_info__]
)
