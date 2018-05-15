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
from distutils.command.build_py import build_py
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_scripts import install_scripts
from distutils.core import setup
from importlib.machinery import SourceFileLoader

from ui import version

po_build_path = os.path.join('build', 'share', 'locale')
build_translations_path = os.path.join('i18n', 'build_translations.py')
build_translations = SourceFileLoader('build_translations', build_translations_path).load_module()


class RemoveExtension(install_scripts):
    def run(self):
        install_scripts.run(self)

        if os.name != 'nt':
            for script in self.get_outputs():
                os.rename(script, script[:-3])


class BuildTranslations(build_py):
    def run(self):
        build_py.run(self)
        build_translations.build(os.path.join(po_build_path))


class InstallTranslations(install_data):
    def run(self):
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
    def run(self):
        install.run(self)
        self.run_command('install_data')


setup(
    name='steam-tools-ng',
    version=version.__version__,
    description="Useful tools for Steam",
    author='Lara Maia',
    author_email='dev@lara.click',
    url='http://github.com/ShyPixie/steam-tools-ng',
    license='GPL',
    packages=['steam_tools_ng_ui'],
    package_dir={'steam_tools_ng_ui': 'ui'},
    scripts=['steam-tools-ng.py'],
    requires=['stlib'],
    cmdclass={
        'build_py': BuildTranslations,
        'install': Install,
        'install_scripts': RemoveExtension,
        'install_data': InstallTranslations,
    }
)
