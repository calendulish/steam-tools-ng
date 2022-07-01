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

set BINPATH=msys64\\usr\\bin
set ARCH=mingw-w64-x86_64
set PATH=/mingw64/bin:/usr/local/bin:/usr/bin:/bin:/opt/bin

for /d %%i in (%cd%) do (set project_name=%%~ni)
call set project_name=%%project_name:-=_%%
set PS1=\[\e]0;\w\a\]\n[%project_name%] \[\e[32m\]\u@\h \[\e[35m\]$MSYSTEM\[\e[0m\] \[\e[33m\]\w\[\e[0m\]\n\$

setlocal enabledelayedexpansion
for /f "skip=1 tokens=2 delims=: " %%i in (
    '%BINPATH%\\pacman.exe -Qi %ARCH%-python 2^>nul'
) do (
    set PYTHON_VERSION=%%i
    set PYTHON_VERSION=!PYTHON_VERSION:~0,3!
    goto :break
)
echo Warning: Python isn't installed
exit /b 1
:break
endlocal

set PYTHONHOME=/mingw64
set PYTHONPATH=/mingw64/lib/python%PYTHON_VERSION%/lib-dynload

exit /b 0