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
import logging
from subprocess import call
from typing import Any

from gi.repository import Gtk

from . import utils
from .. import i18n, config

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class UpdateWindow(utils.PopupWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            version: str,
    ) -> None:
        super().__init__(parent_window, application)
        self.releases_url = 'https://github.com/calendulish/steam-tools-ng/releases'
        self.set_title(_('Updates'))

        self.status = utils.SimpleStatus()
        self.status.info(_("A new version is available [{}].\nIt's highly recommended to update.").format(version))
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        link = utils.ClickableLabel()
        link.set_text(self.releases_url)
        link.connect("clicked", self.on_link_clicked)
        self.status._grid.attach(link, 0, 1, 1, 1)

        self.connect('destroy', lambda *args: self.destroy)
        self.connect('close-request', lambda *args: self.destroy)

    def on_link_clicked(self, *args: Any, **kwargs: Any) -> None:
        call([config.file_manager, self.releases_url])
