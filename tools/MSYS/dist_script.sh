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

source "$(dirname "$0")/common.sh"

check_msys

#clean
rm -rfv build dist

# build
./setup.py -v build || exit 1
pushd build || exit 1
mv "exe.mingw_x86_64-$PYTHON_VERSION" "$RELEASE_NAME" || exit 1

# zip release
tar -vvcf "$RELEASE_NAME.zip" "$RELEASE_NAME" || exit 1
popd || exit 1

# build installer
pushd installer || exit 1
"$ISCC" //dAppVersion="$APP_VERSION" //dReleaseName="$RELEASE_NAME" install.iss || exit 1
"$ISCC" netinstall.iss || exit 1

exit 0
