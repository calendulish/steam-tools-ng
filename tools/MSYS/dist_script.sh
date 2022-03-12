#!/bin/bash
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

source "$(dirname "$0")/common.sh"

check_msys

#clean
rm -rfv build dist

# build stlib
mkdir -p build || exit 1
pushd build || exit 1
curl -o stlib.tar.gz -L https://github.com/ShyPixie/stlib/archive/refs/tags/v"$STLIB_VERSION".tar.gz || exit 1
tar xfv stlib.tar.gz || exit 1
pushd stlib-"$STLIB_VERSION"/src/steam_api/steamworks_sdk || exit 1
curl -o steamworks-sdk.zip -L https://github.com/ShyPixie/Overlays/blob/master/dev-util/steamworks-sdk/files/steamworks_sdk_151.zip?raw=true || exit 1
unzip -o steamworks-sdk.zip || exit 1
popd || exit 1
pushd "stlib-$STLIB_VERSION" || exit 1
./setup.py bdist_wheel
python -m pip install --upgrade . || exit 1
popd || exit 1

# build stng
popd || exit 1
./setup.py -v build || exit 1
pushd build || exit 1
mv "exe.mingw_x86_64-$PYTHON_VERSION" "$RELEASE_NAME" || exit 1

# build plugins
mkdir -p "$RELEASE_NAME"/plugins || exit 1
curl -o stlib-plugins.tar.gz -L "https://github.com/ShyPixie/stlib-plugins/archive/refs/tags/v$STLIB_PLUGINS_VERSION.tar.gz" || exit 1
tar xfv stlib-plugins.tar.gz || exit 1
pushd "stlib-plugins-$STLIB_PLUGINS_VERSION" || exit 1
mingw32-make || exit 1
cp -fv src/__pycache__/steamtrades* ../"$RELEASE_NAME"/plugins/steamtrades.pyc || exit 1
cp -fv src/__pycache__/steamgifts* ../"$RELEASE_NAME"/plugins/steamgifts.pyc || exit 1
popd || exit 1

# zip release
tar -vvcf "$RELEASE_NAME.zip" "$RELEASE_NAME" || exit 1
popd || exit 1

# build installer
pushd installer || exit 1
"$ISCC" //dAppVersion="$APP_VERSION" //dReleaseName="$RELEASE_NAME" install.iss || exit 1
"$ISCC" netinstall.iss || exit 1

exit 0
