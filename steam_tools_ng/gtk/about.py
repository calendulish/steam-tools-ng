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

from gi.repository import GdkPixbuf, Gtk

from .. import config, version, i18n

_ = i18n.get_translation


# noinspection PyUnusedLocal
class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent_window: Gtk.Window) -> None:
        super().__init__(self, transient_for=parent_window, modal=True)
        self.set_program_name("Steam Tools NG")

        self.set_authors([
            "Lara Maia",
        ])

        self.set_translator_credits(
            "Fernando Manfredi (pt_BR)\n"
            "®omano (fr)"
        )

        self.set_website("http://github.com/ShyPixie/steam-tools-ng")
        self.set_website_label(_("Git Repository"))
        self.set_version(version.__version__)
        self.set_copyright("Lara Maia (C) 2015 ~ 2020 - dev@lara.click")
        self.set_comments(_("Made with Love <3"))
        self.set_license_type(Gtk.License.GPL_3_0)

        logo = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(config.icons_dir, 'stng.png'), 96, 96)
        self.set_logo(logo)

        self.connect("response", lambda dialog, response_id: self.destroy())

        self.present()
