#!/bin/bash
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

check_msys() {
    if ! grep -q "MSYS" <<<"$(uname -s)"; then
        echo "Unsupported platform"
        exit 1
    fi
}

cd "$(dirname "$0")/../.." || exit 1

export PYTHON_VERSION RELEASE_NAME APP_VERSION STLIB_PLUGINS_VERSION ISCC
PYTHON_VERSION="$(python --version | cut -f2 -d' ' | cut -f1,2 -d'.')"
RELEASE_NAME="$(basename "$PWD")-MINGW64-Python-$PYTHON_VERSION"
APP_VERSION="$(grep version= setup.py | cut -d\' -f2)"
STLIB_PLUGINS_VERSION="0.2"
ISCC="/c/Program Files (x86)/Inno Setup 6/ISCC.exe"
