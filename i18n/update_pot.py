#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
import os
import subprocess
import sys

from fileinput import FileInput
from pathlib import Path

sys.path.append('..')
os.chdir(Path(__file__).parent.parent.resolve())
log = logging.getLogger(__name__)

copyright_ = '''
Steam Tools NG - Useful tools for Steam
Lara Maia <dev@lara.monster> (C) 2015 ~ 2022
'''

if __name__ == "__main__":
    output_file = Path('i18n', 'steam-tools-ng.pot')
    output_file.write_text("")
    translatable_files = []

    for file in Path('src').glob('**/*.py'):
        translatable_files.append(file)

    for file in translatable_files:
        process_info = subprocess.run(
            [
                'xgettext',
                '-jo',
                output_file,
                file,
                '--copyright-holder=' + copyright_,
                '--package-name=steam-tools-ng',
                '--msgid-bugs-address=dev@lara.monster',
            ]
        )

        log.info(f"Processing {file}")

        if process_info.returncode == 1:
            log.error(f"This error occurs when processing {file}")
            sys.exit(1)

    with FileInput(output_file, inplace=True) as pot:
        for line in pot:
            if '# SOME DESCRIPTIVE TITLE' in line or '# Copyright (C) YEAR' in line:
                continue

            print(line.replace('CHARSET', 'UTF-8'), end='')
