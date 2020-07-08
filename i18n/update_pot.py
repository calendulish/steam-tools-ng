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

import importlib
import os
import platform
import sys
from datetime import datetime
from importlib.machinery import SourceFileLoader
from tokenize import TokenError, tokenize
from typing import NamedTuple

sys.path.append('..')
version = importlib.import_module('.version', 'steam_tools_ng')
script_path = os.path.dirname(__file__)

if script_path:
    os.chdir(os.path.join(script_path, '..'))
else:
    os.chdir('..')

if 'MSC' in platform.python_compiler():
    tools_path = os.path.join(sys.prefix, 'Tools', 'i18n')
else:
    python_version = f'python{sys.version_info.major}.{sys.version_info.minor}'
    tools_path = os.path.join(sys.prefix, 'lib', python_version, 'Tools', 'i18n')

pygettext = SourceFileLoader('pygettext', os.path.join(tools_path, 'pygettext.py')).load_module()


class Options(NamedTuple):
    docstrings = 0
    nodocstrings = {}
    keywords = ['_']
    toexclude = []
    writelocations = 1

    GNU = 1
    SOLARIS = 2
    locationstyle = GNU
    width = 78


now = datetime.now()
current_datetime = '{:%Y-%m-%d %H:%M}{}'.format(
    now,
    # ensure tz as number
    now.astimezone(tz=None).strftime('%z'),
)

pygettext.pot_header = f'''\
# Steam Tools NG - Useful tools for Steam
# Lara Maia <dev@lara.click> (C) 2015 ~ 2018
#
msgid ""
msgstr ""
"Project-Id-Version: {version.__version__}\\n"
"POT-Creation-Date: {current_datetime}\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=%(charset)s\\n"
"Content-Transfer-Encoding: %(encoding)s\\n"
"Generated-By: pygettext.py %(version)s\\n"

'''

if __name__ == "__main__":
    output_file = os.path.join('i18n', 'steam_tools_ng.pot')
    translatable_files = []

    for root, dirs, files in os.walk('steam_tools_ng'):
        for file in files:
            if file.endswith(".py"):
                translatable_files.append(os.path.join(root, file))

    translatable_files.append('steam_tools_ng.py')

    pygettext.make_escapes(True)
    eater = pygettext.TokenEater(Options())

    for file in translatable_files:
        with open(file, 'rb') as file_pointer:
            eater.set_filename(file)

            try:
                tokens = tokenize(file_pointer.readline)
                for token in tokens:
                    eater(*token)
            except TokenError as exception:
                print(repr(exception), file=sys.stderr)

    with open(output_file, 'w', encoding='UTF-8', newline='\n') as file_pointer:
        eater.write(file_pointer)
