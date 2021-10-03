#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2021
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

import importlib
import logging
import os
import subprocess
import sys

sys.path.append('..')
version = importlib.import_module('.version', 'steam_tools_ng')
script_path = os.path.dirname(__file__)
log = logging.getLogger(__name__)

if script_path:
    os.chdir(os.path.join(script_path, '..'))
else:
    os.chdir('..')

copyright='''
Steam Tools NG - Useful tools for Steam
Lara Maia <dev@lara.monster> (C) 2015 ~ 2021
'''

if __name__ == "__main__":
    output_file = os.path.join('i18n', 'steam-tools-ng.pot')
    translatable_files = []

    for root, dirs, files in os.walk('steam_tools_ng'):
        for file in files:
            if file.endswith(".py"):
                translatable_files.append(os.path.join(root, file))

    translatable_files.append('steam-tools-ng.py')

    for file in translatable_files:
        process_info = subprocess.run(
            [
                'xgettext',
                '-jo',
                os.path.join('i18n', 'steam-tools-ng.pot'),
                file,
                '--copyright-holder='+copyright,
                '--package-name=steam-tools-ng',
                '--package-version='+version.__version__,
                '--msgid-bugs-address=dev@lara.monster',
            ]
        )

        log.info(f"Processing {file}")

        if process_info.returncode == 1:
            log.error(f"This error occurs when processing {file}")
            break
