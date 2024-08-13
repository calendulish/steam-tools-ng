#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2024
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
import sysconfig
from pathlib import Path
from typing import Any, List, Mapping, Tuple

import certifi

if os.name == 'nt' and not os.getenv('NO_FREEZE'):
    # noinspection PyPackageRequirements
    from cx_Freeze import setup, Executable
else:
    from setuptools import setup


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

    if 'MSC ' in sys.version:
        # windows
        from gi.repository import Gtk
        lib_path = Path(Gtk.__path__[0]).parent.parent.resolve()
        required_dlls = [
            'gtk-4-1',
            'pango-1.0-0',
            'pangocairo-1.0-0',
            'pangowin32-1.0-0',
            'Rsvg-2.0-vs17',
            'graphene-1.0-0',
            'freetype-6',
        ]

        pixbuf_loaders = [
            'libpixbufloader-svg',
        ]
    else:
        # mingw
        lib_path = Path(sysconfig.get_path('platlib')).parent.parent.resolve()
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

    bin_path = lib_path.parent.resolve() / 'bin'

    includes = [
        (
            str(lib_path / 'girepository-1.0' / f'{package}.typelib'),
            str(Path('lib', 'girepository-1.0', f'{package}.typelib')),
        )
        for package in namespace_packages
    ]
    includes.extend(
        (str(bin_path / f'{dll}.dll'), f'{dll}.dll') for dll in required_dlls
    )
    includes.extend(
        (
            str(lib_path / 'gdk-pixbuf-2.0' / '2.10.0' / 'loaders' / f'{loader}.dll'),
            str(Path('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders', f'{loader}.dll')),
        )
        for loader in pixbuf_loaders
    )
    includes.extend(
        (
            (
                str(lib_path / 'gdk-pixbuf-2.0' / '2.10.0' / 'loaders.cache'),
                str(Path('lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders.cache')),
            ),
            (
                str(Path('src', 'steam_tools_ng', 'icons', 'settings.ini')),
                str(Path('etc', 'gtk-4.0', 'settings.ini')),
            ),
        )
    )
    return includes


def freeze_options() -> Mapping[str, Any]:
    if os.name != 'nt' or os.getenv('NO_FREEZE'):
        return {}

    icons_path = Path('src', 'steam_tools_ng', 'icons')
    copyright_ = 'Lara Maia (C) 2015 ~ 2024'

    executables = [
        Executable(
            Path("src", "steam_tools_ng", "cli.py"),
            target_name='steam-tools-ng',
            base=None,
            icon=Path(icons_path, 'stng_console.ico'),
            shortcut_name='Steam Tools NG CLI',
            copyright=copyright_,
        ),
        Executable(
            Path("src", "steam_tools_ng", "gui.py"),
            target_name='steam-tools-ng-gui',
            base='Win32GUI',
            icon=Path(icons_path, 'stng.ico'),
            shortcut_name='Steam Tools NG GUI',
            copyright=copyright_,
        ),
    ]

    paths = ['src']
    paths.extend(sys.path)

    includes = [*fix_gtk(), (certifi.where(), Path('etc', 'cacert.pem'))]

    includes.extend(
        (file, Path('share', 'icons', 'Default', file.name))
        for file in Path(icons_path, 'Default').iterdir()
        if file != 'settings.ini'
    )
    for language in ['fr', 'pt_BR']:
        language_directory = Path('locale', language, 'LC_MESSAGES')
        includes.append((
            Path(language_directory, 'steam-tools-ng.mo'),
            Path('lib', 'steam_tools_ng', language_directory, 'steam-tools-ng.mo'),
        ))

    build_exe_options = {
        "include_files": includes,
        "path": paths,
    }

    options = {
        "build_exe": build_exe_options,
    }

    return {
        "options": options,
        "executables": executables,
    }


setup(**freeze_options())
