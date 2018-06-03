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
import asyncio
import functools
import logging
from typing import Any, Dict, Optional

import aiohttp
from gi.repository import Gtk
from stlib import webapi

from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class FinalizeDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Widget,
            action: str,
            model: Gtk.TreeModel,
            iter_: Gtk.TreeIter
    ) -> None:
        super().__init__(use_header_bar=True)
        self.action = action

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
        self.set_default_size(300, 90)
        self.set_title(_('Finalize Confirmation'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status_section = utils.new_section(_("Status"))
        self.content_area.add(self.status_section.frame)

        self.status_label = Gtk.Label()
        self.status_label.set_markup(utils.markup(_("Waiting"), color='green'))
        self.status_section.grid.attach(self.status_label, 0, 0, 1, 1)

        self.spin = Gtk.Spinner()
        self.content_area.add(self.spin)

        # FIXME: cairo bug (see on confirmations_tab)
        if not iter_ or model[iter_][1] == '':
            self.status_label.set_markup(
                utils.markup(_("You must select an item before accept/cancel"), color='red')
            )
            self.header_bar.set_show_close_button(True)
        else:
            self.data = model[iter_]
            self.info_label = Gtk.Label()
            markup = "{} {}\n{} {}\n{} {}\n\n{} {}".format(
                _("Trade with"),
                utils.markup(self.data[4], color='blue'),
                _("You will give"),
                utils.markup(self.data[3], color='blue'),
                _("and receives"),
                utils.markup(self.data[5], color='blue'),
                _("Do you really want to {} that?".format(action)),
                utils.markup(_("It can't be undone!"), color='red'),
            )

            self.info_label.set_markup(markup)
            self.info_label.set_justify(Gtk.Justification.CENTER)
            self.content_area.add(self.info_label)

            self.yes_button = Gtk.Button(_("Yes"))
            self.yes_button.connect("clicked", self.on_yes_button_clicked)
            self.content_area.add(self.yes_button)

            self.no_button = Gtk.Button(_("No"))
            self.no_button.connect("clicked", self.on_no_button_clicked)
            self.content_area.add(self.no_button)

        self.content_area.show_all()

        self.connect('response', self.on_response)

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        self.spin.start()
        task = asyncio.ensure_future(finalize(self.action, self.data))
        task.add_done_callback(functools.partial(finalize_callback, dialog=self))

    def on_no_button_clicked(self, button: Gtk.Button) -> None:
        self.destroy()


@config.Check("authenticator")
async def finalize(
        action: str,
        data: Any,
        identity_secret: Optional[config.ConfigStr] = None,
        steamid: Optional[config.ConfigInt] = None,
        deviceid: Optional[config.ConfigStr] = None,
) -> Dict[str, bool]:
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        session.cookie_jar.update_cookies(config.login_cookies())
        http = webapi.Http(session, 'https://lara.click/api')

        result = await http.finalize_confirmation(
            identity_secret,
            steamid,
            deviceid,
            data[1],
            data[2],
            action,
        )

        return result


def finalize_callback(future: Any, dialog) -> None:
    log.debug("confirmation finalized. The return is %s", future.result)
    dialog.destroy()
