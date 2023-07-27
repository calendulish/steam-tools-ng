@echo off
pushd %~dp0..\\.. || exit 1
::
:: Lara Maia <dev@lara.monster> 2015 ~ 2023
::
:: The Steam Tools NG is free software: you can redistribute it and/or
:: modify it under the terms of the GNU General Public License as
:: published by the Free Software Foundation, either version 3 of
:: the License, or (at your option) any later version.
::
:: The Steam Tools NG is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
:: See the GNU General Public License for more details.
::
:: You should have received a copy of the GNU General Public License
:: along with this program. If not, see http://www.gnu.org/licenses/.
::
for /f "tokens=*" %%i in ('findstr /c:"version =" pyproject.toml') do (set APP_VERSION=%%i)
set APP_VERSION=%APP_VERSION:~11,-1%
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

if not exist gvsbuild.zip (
    set gvsbuild="https://github.com/calendulish/gvsbuild/releases/download/latest/gvsbuild-py!PYTHON_VERSION!-vs17-x64.zip"
    !curl! -o gvsbuild.zip -L !gvsbuild! || !certutil! -urlcache -split -f !gvsbuild! gvsbuild.zip || exit 1
)

if not exist release (
    7z x gvsbuild.zip || exit 1
)

set PATH=%cd%\\release\\bin;%PATH%
for %%i in (release\\python\\pycairo-*-cp%PYTHON_VERSION:.=%-cp%PYTHON_VERSION:.=%-win_amd64.whl) do (python -m pip install --force-reinstall %%i) || exit 1
for %%i in (release\\python\\PyGObject-*-cp%PYTHON_VERSION:.=%-cp%PYTHON_VERSION:.=%-win_amd64.whl) do (python -m pip install --force-reinstall --no-deps %%i) || exit 1

set NO_FREEZE=1
python -m pip install . || exit 1

set NO_FREEZE=
python ./setup.py -v build || exit 1

pushd build || exit 1
move /y "exe.win-amd64-%PYTHON_VERSION%" "%RELEASE_NAME%" || exit 1

:: zip release
tar -vvcf "%RELEASE_NAME%.zip" "%RELEASE_NAME%" || exit 1
popd || exit 1

pushd installer || exit 1

if not exist vc_redist.x64.exe (
    set vc_redist="https://aka.ms/vs/17/release/vc_redist.x64.exe"
    !curl! -o vc_redist.x64.exe -L !vc_redist! || !certutil! -urlcache -split -f !vc_redist! vc_redist.x64.exe || exit 1
)

%ISCC% /dAppVersion="%APP_VERSION%" /dReleaseName="%RELEASE_NAME%" install.iss || exit 1
%ISCC% netinstall.iss || exit 1

echo Done.
exit 0
