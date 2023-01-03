#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
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

from importlib.metadata import version, PackageNotFoundError

import sys
from pathlib import Path

try:
    __version__ = version(__package__)
except PackageNotFoundError:  # Freezed
    # noinspection PyPackageRequirements
    from win32com.client import Dispatch

    parser = Dispatch('Scripting.FileSystemObject')
    working_directory = Path(sys.executable).parent.resolve()
    version_raw = parser.GetFileVersion(working_directory / Path(sys.executable).name)
    __version__ = str(version_raw).rpartition('.')[0]
