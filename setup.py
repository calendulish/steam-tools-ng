#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2020
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
import subprocess
from distutils.command.install_data import install_data
from distutils.sysconfig import get_python_lib
from importlib.machinery import SourceFileLoader
from typing import Any, List, Mapping, Tuple

import certifi
from setuptools.command.build_py import build_py
from setuptools.command.install import install
from setuptools.command.install_scripts import install_scripts

from steam_tools_ng import version

po_build_path = os.path.join('build', 'share', 'locale')

if os.name == 'nt':
    # noinspection PyPackageRequirements
    from cx_Freeze import setup, Executable

    if sys.maxsize > 2 ** 32:
        arch = 64
    else:
        arch = 32

    icon_path = os.path.join(get_python_lib(), 'steam-tools-ng', 'share', 'icons')
else:
    from setuptools import setup

    icon_path = os.path.abspath(os.path.join(os.path.sep, 'usr', 'share', 'steam-tools-ng', 'icons'))


class RemoveExtension(install_scripts):
    def run(self) -> None:
        install_scripts.run(self)

        if os.name != 'nt':
            for script in self.get_outputs():
                os.rename(script, script[:-3])


class BuildTranslations(build_py):
    def run(self) -> None:
        build_py.run(self)

        os.makedirs(po_build_path, exist_ok=True)

        for root, directories, files in os.walk('i18n'):
            for file in files:
                if file.endswith(".po"):
                    subprocess.run(
                        [
                            'msgfmt',
                            os.path.join(root, file),
                            '-o',
                            os.path.join(po_build_path, os.path.splitext(file)[0]+".mo")
                        ], check=True
                    )


class InstallTranslations(install_data):
    def run(self) -> None:
        install_data.run(self)

        locale_directory = os.path.join(self.install_dir, 'share', 'locale')
        self.mkpath(locale_directory)

        for root, directories, files in os.walk(po_build_path):
            for file in files:
                language = os.path.splitext(file)[0]
                output_directory = os.path.join(locale_directory, language, 'LC_MESSAGES')
                self.mkpath(output_directory)

                output, _ = self.copy_file(
                    os.path.join(root, file),
                    os.path.join(output_directory, 'steam-tools-ng.mo'),
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
        'HarfBuzz-0.0',
    ]

    required_dlls = [
        'libgtk-3-0',
        'libgdk-3-0',
        'libpango-1.0-0',
        'libpangowin32-1.0-0',
        'libatk-1.0-0',
        'librsvg-2-2',
    ]

    pixbuf_loaders = [
        'libpixbufloader-png',
        'libpixbufloader-svg',
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

    for loader in pixbuf_loaders:
        includes.append((
            os.path.join(lib_path, 'gdk-pixbuf-2.0', '2.10.0', 'loaders', f'{loader}.dll'),
            os.path.join('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders', f'{loader}.dll'),
        ))

    includes.append((
        os.path.join(lib_path, 'gdk-pixbuf-2.0', '2.10.0', 'loaders.cache'),
        os.path.join('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders.cache'),
    ))

    includes.append((
        os.path.join('icons', 'settings.ini'),
        os.path.join('etc', 'gtk-3.0', 'settings.ini'),
    ))

    return includes


def freeze_options() -> Mapping[str, Any]:
    if os.name != 'nt':
        return {}

    executables = [
        Executable(
            "steam-tools-ng.py",
            base=None,
            icon=os.path.join('icons', 'stng.ico'),
            shortcutName='Steam Tools NG',
            copyright='Lara Maia (C) 2015 ~ 2020',
        )
    ]

    packages = ['asyncio', 'steam_tools_ng', 'gi', 'idna', 'six', 'pkg_resources']  # idna for cx_freeze <= 5.1.1

    paths = ['.']
    paths.extend(sys.path)

    includes = [*fix_gtk(), (certifi.where(), os.path.join('etc', 'cacert.pem'))]

    for file in os.listdir('icons'):
        if file != 'settings.ini':
            includes.append((os.path.join('icons', file), os.path.join('share', 'icons', file)))

    excludes = [
        'tkinter',
        'chardet',
        'distutils',
        'pydoc_data',
        'unittest',
        'xmlrpc',
        'doctest',
        'ftplib',
        'lzma',
        'pdb',
        'py_compile',
        'tarfile',
        'webbrowser',
    ]

    build_exe_options = {
        "packages": packages,
        "include_files": includes,
        "excludes": excludes,
        "path": paths,
        "optimize": 2,
    }

    options = {
        "build_exe": build_exe_options,
    }

    return {
        "options": options,
        "executables": executables,
    }


def data_files() -> Mapping[str, List[Tuple[str, List[str]]]]:
    icons = [
        os.path.join('icons', 'stng.png'),
        os.path.join('icons', 'stng.ico'),
        os.path.join('icons', 'stng_nc.ico'),
        os.path.join('icons', 'stng_console.ico'),
    ]

    return {'data_files': [
        (icon_path, icons),
        ("share/applications", ["steam-tools-ng.desktop"]),
    ]}


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
        'steam_tools_ng.core',
        'steam_tools_ng.console',
        'steam_tools_ng.gtk',
    ],
    package_dir={'steam_tools_ng': 'steam_tools_ng'},
    scripts=['steam-tools-ng.py'],
    install_requires=['stlib>=0.13', 'aiohttp'],
    cmdclass={
        'build_py': BuildTranslations,
        'install': Install,
        'install_scripts': RemoveExtension,
        'install_data': InstallTranslations,
    },
    **freeze_options(),
    **data_files()
)
