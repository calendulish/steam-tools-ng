@echo off
call %~dp0common.cmd
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

echo Checking current environment...

if not exist I:\\msys64 (
	echo System msys not installed.
	exit 1
)

echo Fixing GPG
:: gpg is unable to work when msys2 is running from a WSL path
call :shell sed 's/SigLevel    = Required/SigLevel    = Never/' -i /etc/pacman.conf
echo Installing core packages
call :shell pacman -Syyuu --noconfirm
echo Running normal system update
call :shell pacman -Syu --noconfirm

echo Installing Python
call :install python
call :install pip
:: Reset python version
call %~dp0common.cmd

echo Updating setuptools to latest
call :install setuptools --ignore-installed

echo Installing dev tools
call :install git tar unzip
call :install gcc make
call :install mypy pylint pytest

echo Installing freezing tools
call :install cx-freeze pywin32

echo Updating project dependencies
call :shell python setup.py egg_info
set requires="src\\%project_name%.egg-info\\requires.txt"

if exist %requires% (
    echo Installing project dependencies

    for /f "usebackq delims=" %%i in (%requires%) do (
        call :install %%i
    )
)

echo Cleaning...
del /f /q /s msys2.exe >nul 2>&1 || exit 1

echo Done.
exit 0

:shell
%BINPATH%\\sh.exe -c "%*" || exit 1
goto :eof

:install
setlocal enabledelayedexpansion
for %%i in (%*) do (
    set packages=!packages! %ARCH%-%%i
    set python_packages=!python_packages! %ARCH%-python-%%i
)

set pacman=pacman -S --needed --noconfirm
set pip=python -m pip install
%BINPATH%\\sh.exe -c "%pacman% !python_packages! 2>&- || %pacman% !packages! 2>&- || %pacman% %* 2>&- || %pip% %*" || exit 1
endlocal
goto :eof
