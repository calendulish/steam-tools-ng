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
set GVSBUILD=I:\\gvsbuild-release
set PATH=%GVSBUILD%\\bin;%PATH%
set LIB=%GVSBUILD%\\lib;%LIB%
set PYTHONPATH=src

for /f %%i in (
    'py -c "import sys;print(sys.winver)" 2^>nul'
) do (
    set PYTHON_VERSION=%%i
)

for %%i in (%GVSBUILD%\\python\\pycairo-*-cp%PYTHON_VERSION:.=%-cp%PYTHON_VERSION:.=%-win_amd64.whl) do (py -m pip install --force-reinstall %%i) || exit 1
for %%i in (%GVSBUILD%\\python\\PyGObject-*-cp%PYTHON_VERSION:.=%-cp%PYTHON_VERSION:.=%-win_amd64.whl) do (py -m pip install --force-reinstall --no-deps %%i) || exit 1

py -m pip install -r requirements.txt || exit 1

py
