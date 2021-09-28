#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2025~2021
#
# The steam-tools-ng is free software: you can redistribute it and/or
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

log = logging.Logger(__name__)

if __name__ == "__main__":
    if not 'WSL' in platform.release():
        log.error("Unsupported")
        sys.exit(1)

    current_directory=subprocess.run(['wslpath', '-w', os.getcwd()], check=True, stdout=subprocess.PIPE).stdout.decode()

    subprocess.run(['powershell.exe', '-Command', f"pushd {current_directory}; .\\update_dev_environment.cmd"], check=True)