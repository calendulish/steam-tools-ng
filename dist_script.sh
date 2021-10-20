#/bin/sh
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

PYTHON_VERSION=$(python --version | sed 's/ /-/')
MINGW_VERSION="3.9"
STLIB_VERSION="0.13.5"
STLIB_PLUGINS_VERSION="0.2"

delayed_exit() {
    echo "Cleaning"
    rm -rfv build stlib*
    read -p "Press any key to exit"
    exit $1
}

if test -z $1; then
    echo "You must specify a version"
    delayed_exit 1
fi

if ! grep -q "MSYS" <<<$(uname -s); then
    echo "Unsupported platform"
    delayed_exit 1
fi

#clean
rm -rfv build dist stlib*

# build stlib and install stlib
# git clone https://github.com/ShyPixie/stlib || delayed_exit 1
curl -o stlib.tar.gz -L https://github.com/ShyPixie/stlib/archive/refs/tags/v$STLIB_VERSION.tar.gz || delayed_exit 1
tar xfv stlib.tar.gz || delayed_exit 1
pushd stlib-$STLIB_VERSION/src/steam_api/steamworks_sdk
curl -o steamworks-sdk.zip -L https://github.com/ShyPixie/Overlays/blob/master/dev-util/steamworks-sdk/files/steamworks_sdk_151.zip?raw=true || delayed_exit 1
unzip -o steamworks-sdk.zip || delayed_exit 1
mv sdk/* . || delayed_exit 1
popd
pushd stlib-$STLIB_VERSION
./setup.py build || delayed_exit 1
./setup.py install || delayed_exit 1
popd

# build STNG
./setup.py build || delayed_exit 1
pushd build
mv "exe.mingw_x86_64-$MINGW_VERSION" "STNG-WIN64-$1-$PYTHON_VERSION" || delayed_exit 1

# plugins
mkdir -p "STNG-WIN64-$1-$PYTHON_VERSION"/plugins || delayed_exit 1
popd
# git clone https://github.com/ShyPixie/stlib-plugins || delayed_exit 1
curl -o stlib-plugins.tar.gz -L https://github.com/ShyPixie/stlib-plugins/archive/refs/tags/v$STLIB_PLUGINS_VERSION.tar.gz || delayed_exit 1
tar xfv stlib-plugins.tar.gz || delayed_exit 1
pushd stlib-plugins-$STLIB_PLUGINS_VERSION
mingw32-make || delayed_exit 1
popd
pushd build
cp -fv ../stlib-plugins-$STLIB_PLUGINS_VERSION/src/__pycache__/steamtrades* "STNG-WIN64-$1-$PYTHON_VERSION"/plugins/steamtrades.pyc || delayed_exit 1
cp -fv ../stlib-plugins-$STLIB_PLUGINS_VERSION/src/__pycache__/steamgifts* "STNG-WIN64-$1-$PYTHON_VERSION"/plugins/steamgifts.pyc || delayed_exit 1
# Fix translations
mv share/* "STNG-WIN64-$1-$PYTHON_VERSION"/share/ || delayed_exit 1
popd

# Creating installer
/c/Program\ Files\ \(x86\)/Inno\ Setup\ 6/ISCC.exe installer.iss || delayed_exit 1

delayed_exit 0
