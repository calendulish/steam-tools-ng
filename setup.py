#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2018
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

import os
import sys
from distutils.command.build_py import build_py
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_scripts import install_scripts
from distutils.sysconfig import get_python_lib
from importlib.machinery import SourceFileLoader
from typing import Any, List, Mapping, Tuple

from steam_tools_ng import version

po_build_path = os.path.join('build', 'share', 'locale')

if os.name == 'nt':
    # noinspection PyPackageRequirements
    from cx_Freeze import setup, Executable

    if sys.maxsize > 2 ** 32:
        arch = 64
    else:
        arch = 32
else:
    from distutils.core import setup


class RemoveExtension(install_scripts):
    def run(self) -> None:
        install_scripts.run(self)

        if os.name != 'nt':
            for script in self.get_outputs():
                os.rename(script, script[:-3])


class BuildTranslations(build_py):
    def run(self) -> None:
        build_py.run(self)

        if os.getenv("SCRUTINIZER") or os.getenv("TRAVIS"):
            print("bypassing BuildTranslations")
            return

        build_translations_path = os.path.join('i18n', 'build_translations.py')
        build_translations = SourceFileLoader('build_translations', build_translations_path).load_module()
        build_translations.build(os.path.join(po_build_path))


class InstallTranslations(install_data):
    def run(self) -> None:
        if os.getenv("SCRUTINIZER") or os.getenv("TRAVIS"):
            print("bypassing InstallTranslations")
            return

        base_directory = 'share'
        output_directory = os.path.join(self.install_dir, base_directory)

        self.mkpath(output_directory)

        for root, directories, files in os.walk(po_build_path):
            current_folder = root[root.index(os.path.sep) + 1 + len(base_directory) + 1:]
            self.mkpath(os.path.join(output_directory, current_folder))

            for file in files:
                output, _ = self.copy_file(
                    os.path.join(root, file),
                    os.path.join(output_directory, current_folder)
                )
                self.outfiles.append(output)


class Install(install):
    def run(self) -> None:
        install.run(self)
        self.run_command('install_data')


def fix_gtk() -> List[Tuple[str, str]]:
    namespace_packages = [
        'Gtk-3.0',
        'Gdk-3.0',
        'GObject-2.0',
        'GLib-2.0',
        'Gio-2.0',
        'Pango-1.0',
        'Cairo-1.0',
        'GdkPixbuf-2.0',
        'GModule-2.0',
        'Atk-1.0',
    ]

    required_dlls = [
        'libgtk-3-0',
        'libgdk-3-0',
        'libpango-1.0-0',
        'libpangowin32-1.0-0',
        'libatk-1.0-0',
    ]

    includes = []

    lib_path = os.path.join(get_python_lib(), '..', '..')
    bin_path = os.path.join(get_python_lib(), '..', '..', '..', 'bin')

    for package in namespace_packages:
        includes.append((
            os.path.join(lib_path, 'girepository-1.0', f'{package}.typelib'),
            os.path.join('lib', 'girepository-1.0', f'{package}.typelib')
        ))

    for dll in required_dlls:
        includes.append((
            os.path.join(bin_path, f'{dll}.dll'),
            f'{dll}.dll',
        ))

    return includes


def freeze_options() -> Mapping[str, Any]:
    if os.name != 'nt':
        return {}

    executables = [
        Executable(
            "steam-tools-ng.py",
        )
    ]

    packages = ['asyncio', 'steam_tools_ng', 'gi']

    paths = ['.']
    paths.extend(sys.path)

    includes = [*fix_gtk()]
    excludes = ['tkinter']

    build_exe_options = {
        "packages": packages,
        "include_files": includes,
        "excludes": excludes,
        "path": paths,
    }

    options = {
        "build_exe": build_exe_options,
    }

    return {
        "options": options,
        "executables": executables,
    }


setup(
    name='steam-tools-ng',
    version=version.__version__,
    description="Useful tools for Steam",
    author='Lara Maia',
    author_email='dev@lara.click',
    url='http://github.com/ShyPixie/steam-tools-ng',
    license='GPL',
    packages=[
        'steam_tools_ng',
        'steam_tools_ng.console',
        'steam_tools_ng.gtk',
    ],
    scripts=['steam-tools-ng.py'],
    requires=['stlib'],
    cmdclass={
        'build_py': BuildTranslations,
        'install': Install,
        'install_scripts': RemoveExtension,
        'install_data': InstallTranslations,
    },
    **freeze_options()
)
