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

import os
import platform
import sys
from importlib.machinery import SourceFileLoader

script_path = os.path.dirname(__file__)
python_version = f'python{sys.version_info.major}.{sys.version_info.minor}'

if sys.maxsize > 2 ** 32:
    arch = 64
else:
    arch = 32

if script_path:
    os.chdir(os.path.join(script_path, '..'))
else:
    os.chdir('..')

if 'MSC' in platform.python_compiler():
    tools_path = os.path.join(sys.prefix, 'Tools', 'i18n')
elif sys.platform == 'msys':
    tools_path = os.path.join(f'/mingw{arch}/lib/{python_version}/Tools/i18n')
else:
    tools_path = os.path.join(sys.prefix, 'lib', python_version, 'Tools', 'i18n')

msgfmt = SourceFileLoader('msgfmt', os.path.join(tools_path, 'msgfmt.py')).load_module()

translations = [
    "pt_BR",
    "fr",
]


def build(destination):
    for translation in translations:
        os.makedirs(os.path.join(destination, translation, 'LC_MESSAGES'), exist_ok=True)

        msgfmt.make(
            os.path.join('i18n', translation),
            os.path.join(destination, translation, 'LC_MESSAGES', 'steam-tools-ng.mo')
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Missing parameters: <DESTINATION>")
        sys.exit(1)

    build(sys.argv[1])
