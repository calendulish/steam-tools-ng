#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> <YEAR>
#
# The <program> is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The <program> is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#

import logging
import os
import platform
import subprocess
import sys
from typing import List

os.chdir(os.path.abspath(os.path.dirname(__file__)) + "/../..")
log = logging.getLogger(__name__)


def check_wsl() -> None:
    if 'WSL' not in platform.release():
        log.error("Unsupported platform")
        sys.exit(1)


def run_cmd(command: List[str], check: bool = False) -> None:
    subprocess.run(['cmd.exe', '/c'] + command, check=check)
