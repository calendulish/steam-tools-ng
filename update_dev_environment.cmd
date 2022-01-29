@echo off
::
:: Lara Maia <dev@lara.monster> 2025~2021
::
:: The steam-tools-ng is free software: you can redistribute it and/or
:: modify it under the terms of the GNU General Public License as
:: published by the Free Software Foundation, either version 3 of
:: the License, or (at your option) any later version.
::
:: The <program> is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
:: See the GNU General Public License for more details.
::
:: You should have received a copy of the GNU General Public License
:: along with this program. If not, see http://www.gnu.org/licenses/.
::

set PYTHON_VERSION=3.9
set PYTHONHOME=/mingw64
set PYTHONPATH=/mingw64/lib/python%PYTHON_VERSION%/lib-dynload
set ARCH=mingw-w64-x86_64

pushd %~dp0 || exit 1
echo Current path changed to %cd%

echo Checking current environment...

if not exist msys64 (

    if not exist msys2.exe (
        echo Downloading msys2...
        curl -o msys2.exe -L https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.sfx.exe || exit 1
    )

    if not exist msys64 (
        echo Extracting msys2...
        msys2.exe -y || exit 1
    )

)

echo Updating msys2
set PATH=/mingw64/bin:/usr/local/bin:/usr/bin:/bin:/opt/bin
:: gpg can't work inside WSL paths
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "sed 's/SigLevel    = Required/SigLevel    = Never/' -i /etc/pacman.conf"

:: core packages
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -Syyuu --noconfirm"
:: normal system update
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -Syu --noconfirm"

echo Installing Python
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm %ARCH%-python %ARCH%-python-pip"
::msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "python3 -m pip install setuptools --ignore-installed"

echo Installing Gtk+
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm %ARCH%-gtk4 %ARCH%-python-gobject"

echo Installing dev tools
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm git tar unzip %ARCH%-gcc %ARCH%-make"

echo Installing python testing tools
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm %ARCH%-mypy %ARCH%-python-pylint"
::msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "python3 -m pip install mypy PyGObject-stubs pylint"

echo Installing freezing tools
::msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "python3 -m pip install cx_Freeze"
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm %ARCH%-python-cx-freeze %ARCH%-python-cx-pywin32"

echo Installing STNG dependencies
::msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "python3 -m pip install aiohttp certifi rsa beautifulsoup4 cchardet"
msys64\\usr\\bin\\mintty.exe -d -e /bin/sh -c "pacman -S --needed --noconfirm %ARCH%-python-aiohttp %ARCH%-python-certifi %ARCH%-python-rsa %ARCH%-python-beautifulsoup4"

echo Cleaning...
del /f /q /s msys2.exe >nul 2>&1 || exit 1

popd || exit 1
echo Done.
exit 0
