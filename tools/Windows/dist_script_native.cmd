@echo off
pushd %~dp0..\\.. || exit 1
::
:: Lara Maia <dev@lara.monster> <YEAR>
::
:: The <program> is free software: you can redistribute it and/or
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
for /f %%i in ('findstr /c:"version=" setup.py') do (set APP_VERSION=%%i)
set APP_VERSION=%APP_VERSION:~9,-2%
set STLIB_PLUGINS_VERSION="0.2"
set ISCC="C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
for /d %%i in (%cd%) do (set project_name=%%~ni)
call set project_name=%%project_name:-=_%%

for /f %%i in (
    'python -c "import sys;print(sys.winver)" 2^>nul'
) do (
    set PYTHON_VERSION=%%i
)

for /d %%i in (%cd%) do (
    set RELEASE_NAME=%%~ni-WIN64-Python-%PYTHON_VERSION%
)

setlocal enabledelayedexpansion

set system32=%comspec%
set system32=!system32:cmd.exe=!
set curl="!system32!curl.exe"
set certutil="!system32!certutil.exe"

if not exist stlib.zip (
    set stlib="https://next.lara.monster/s/YC4G9pi8swBwYWj/download/windows.zip"
    !curl! -o stlib.zip -L !stlib! || !certutil! -urlcache -split -f !stlib! stlib.zip || exit 1
)

if not exist dist (
    7z x stlib.zip || exit 1
)

if not exist gvsbuild.zip (
    set gvsbuild="https://github.com/ShyPixie/gvsbuild-release/releases/download/latest/gvsbuild-py3.10-vs22-x64.zip"
    !curl! -o gvsbuild.zip -L !gvsbuild! || !certutil! -urlcache -split -f !gvsbuild! gvsbuild.zip || exit 1
)

if not exist release (
    7z x gvsbuild.zip || exit 1
)

set PATH=%cd%\\release\\bin;%PATH%
python -m pip install --force-reinstall dist\\stlib-0.14.1-cp310-cp310-win_amd64.whl || exit 1
python ./setup.py -v build || exit 1
pushd build || exit 1
move /y "exe.win-amd64-%PYTHON_VERSION%" "%RELEASE_NAME%" || exit 1

:: build plugins (FIXME)
if not exist "%RELEASE_NAME%"\\plugins (
    mkdir "%RELEASE_NAME%"\\plugins || exit 1
)

if not exist stlib-plugins.tar.gz (
    set stlib_plugins="https://github.com/ShyPixie/stlib-plugins/archive/refs/tags/v%STLIB_PLUGINS_VERSION%.tar.gz"
    !curl! -o stlib-plugins.tar.gz -L !stlib_plugins! || !certutil! -urlcache -split -f !stlib_plugins! stlib-plugins.tar.gz || exit 1
)

if not exist "stlib-plugins-%STLIB_PLUGINS_VERSION%" (
    tar -vvxf stlib-plugins.tar.gz || exit 1
)

pushd "stlib-plugins-%STLIB_PLUGINS_VERSION%" || exit 1
python -m compileall src || exit 1
copy /y src\\__pycache__\\steamtrades* "..\\%RELEASE_NAME%\\plugins\\steamtrades.pyc" || exit 1
copy /y src\\__pycache__\\steamgifts* "..\\%RELEASE_NAME%\\plugins\\steamgifts.pyc" || exit 1
popd || exit 1

:: zip release
tar -vvcf "%RELEASE_NAME%.zip" "%RELEASE_NAME%" || exit 1
popd || exit 1

pushd installer || exit 1
%ISCC% /dAppVersion="%APP_VERSION%" /dReleaseName="%RELEASE_NAME%" install.iss || exit 1
%ISCC% netinstall.iss || exit 1

echo Done.
exit 0
