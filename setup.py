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
from distutils.command.install_scripts import install_scripts
from distutils.core import setup


class RemoveExtension(install_scripts):
    def run(self):
        install_scripts.run(self)

        if os.name != 'nt':
            for script in self.get_outputs():
                os.rename(script, script[:-3])


setup(
    name='steam-tools-ng',
    version='0.0.0-DEV',
    description="Useful tools for Steam",
    author='Lara Maia',
    author_email='dev@lara.click',
    url='http://github.com/ShyPixie/steam-tools-ng',
    license='GPL',
    packages=['steam_tools_ng_ui'],
    package_dir={'steam_tools_ng_ui': 'ui'},
    scripts=['steam-tools-ng.py'],
    requires=['stlib'],
    cmdclass={'install_scripts': RemoveExtension}
)
