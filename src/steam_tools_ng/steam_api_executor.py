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
# FIXME: Workaround for keyboard lag when running games on GUI on Windows
# FIXME: https://gitlab.gnome.org/GNOME/gtk/-/issues/2015
from multiprocessing import freeze_support

import sys
import time

from stlib import client

if __name__ == "__main__":
    freeze_support()

    if len(sys.argv) < 2:
        raise AttributeError('No appid')

    with client.SteamAPIExecutor(int(sys.argv[1])):
        while True:
            time.sleep(5)
