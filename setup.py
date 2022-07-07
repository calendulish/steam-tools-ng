#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any, List, Mapping, Tuple

import certifi
from setuptools import find_packages
from setuptools.command.build_py import build_py

if os.name == 'nt':
    # noinspection PyPackageRequirements
    from cx_Freeze import setup, Executable
else:
    from setuptools import setup


class BuildTranslations(build_py):
    def run(self) -> None:
        super().run()

        po_build_path = Path('build', 'lib', 'steam_tools_ng', 'locale')
        po_build_path.mkdir(exist_ok=True)

        for path in Path('i18n').glob('*.po'):
            language = path.stem
            output_directory = po_build_path / language / 'LC_MESSAGES'
            output_directory.mkdir(exist_ok=True, parents=True)

            subprocess.run(
                [
                    'msgfmt',
                    path,
                    '-o',
                    output_directory / 'steam-tools-ng.mo',
                ], check=True
            )


def fix_gtk() -> List[Tuple[str, str]]:
    namespace_packages = [
        'Gtk-4.0',
        'Gdk-4.0',
        'Gsk-4.0',
        'GObject-2.0',
        'GLib-2.0',
        'Gio-2.0',
        'Pango-1.0',
        'PangoCairo-1.0',
        'cairo-1.0',
        'GdkPixbuf-2.0',
        'GModule-2.0',
        'HarfBuzz-0.0',
        'Graphene-1.0',
        'freetype2-2.0',
    ]

    required_dlls = [
        'libgtk-4-1',
        'libpango-1.0-0',
        'libpangocairo-1.0-0',
        'libpangowin32-1.0-0',
        'librsvg-2-2',
        'libgraphene-1.0-0',
        'libfreetype-6',
    ]

    pixbuf_loaders = [
        'libpixbufloader-png',
        'libpixbufloader-svg',
    ]

    includes = []

    lib_path = Path(sysconfig.get_path('platlib')).parent.parent.resolve()
    bin_path = Path(sysconfig.get_path('platlib')).parent.parent.parent.resolve() / 'bin'

    for package in namespace_packages:
        includes.append((
            lib_path / 'girepository-1.0' / f'{package}.typelib',
            Path('lib', 'girepository-1.0', f'{package}.typelib'),
        ))

    for dll in required_dlls:
        includes.append((
            bin_path / f'{dll}.dll',
            f'{dll}.dll',
        ))

    for loader in pixbuf_loaders:
        includes.append((
            lib_path / 'gdk-pixbuf-2.0' / '2.10.0' / 'loaders' / f'{loader}.dll',
            Path('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders', f'{loader}.dll'),
        ))

    includes.append((
        lib_path / 'gdk-pixbuf-2.0' / '2.10.0' / 'loaders.cache',
        Path('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders.cache'),
    ))

    includes.append((
        Path('src', 'steam_tools_ng', 'icons', 'settings.ini'),
        Path('etc', 'gtk-4.0', 'settings.ini'),
    ))

    return includes


def freeze_options() -> Mapping[str, Any]:
    if os.name != 'nt':
        return {}

    icons_path = Path('src', 'steam_tools_ng', 'icons')
    copyright = 'Lara Maia (C) 2015 ~ 2022'

    executables = [
        Executable(
            Path("src", "steam_tools_ng", "cli.py"),
            target_name='steam-tools-ng',
            base=None,
            icon=Path(icons_path, 'stng_console.ico'),
            shortcut_name='Steam Tools NG CLI',
            copyright=copyright,
        ),
        Executable(
            Path("src", "steam_tools_ng", "gui.py"),
            target_name='steam-tools-ng-gui',
            base='Win32GUI',
            icon=Path(icons_path, 'stng.ico'),
            shortcut_name='Steam Tools NG GUI',
            copyright=copyright,
        )
    ]

    packages = ['asyncio', 'steam_tools_ng', 'gi', 'win32com.client']

    paths = ['src']
    paths.extend(sys.path)

    includes = [*fix_gtk(), (certifi.where(), Path('etc', 'cacert.pem'))]

    for file in Path(icons_path, 'Default').iterdir():
        if file != 'settings.ini':
            includes.append((file, Path('share', 'icons', 'Default', file.name)))

    for language in ['fr', 'pt_BR']:
        language_directory = Path('lib', 'steam_tools_ng', 'locale', language, 'LC_MESSAGES')
        includes.append((
            Path('build', language_directory, 'steam-tools-ng.mo'),
            language_directory / 'steam-tools-ng.mo',
        ))

    excludes = [
        'tkinter',
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
        'mypy',
        'pytest',
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


classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: End Users/Desktop',
    'Topic :: Games/Entertainment',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Operating System :: POSIX :: Linux',
    'Operating System :: Microsoft :: Windows :: Windows 10',
    'Environment :: X11 Applications :: GTK',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Typing :: Typed',
]

setup(
    name='steam-tools-ng',
    version='1.1.1',
    description="Some useful tools to use with steam client or compatible programs and websites.",
    author='Lara Maia',
    author_email='dev@lara.monster',
    url='http://github.com/ShyPixie/steam-tools-ng',
    license='GPLv3',
    classifiers=classifiers,
    keywords='steam valve',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={'console_scripts': [
        'steam-tools-ng-gui=steam_tools_ng.gui:main',
        'steam-tools-ng=steam_tools_ng.cli:main',
    ]},
    install_requires=[
        "pywin32; sys_platform == 'win32'",
        'stlib>=0.14',
        'aiohttp',
        'certifi',
    ],
    python_requires='>=3.7',
    cmdclass={'build_py': BuildTranslations},
    **freeze_options()
)
