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
from typing import Any, Optional, Union

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
            iter_: Union[Gtk.TreeIter, bool, None] = False,
    ) -> None:
        super().__init__(use_header_bar=True)
        if action == "allow":
            self.action = _("accept")
        else:
            self.action = _("cancel")

        self.raw_action = action
        self.model = model
        self.iter = iter_

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.parent_window = parent_window
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

        self.set_default_size(300, 90)

        self.give_label = Gtk.Label()
        self.content_area.add(self.give_label)

        self.grid = Gtk.Grid()
        self.content_area.add(self.grid)

        self.cell_renderer = Gtk.CellRendererText()

        self.scroll_give = Gtk.ScrolledWindow()
        self.scroll_give.set_hexpand(True)
        self.scroll_give.set_vexpand(True)
        self.grid.attach(self.scroll_give, 0, 0, 1, 1)

        self.list_store_give = Gtk.ListStore(str)
        self.tree_view_give = Gtk.TreeView(model=self.list_store_give)
        self.scroll_give.add(self.tree_view_give)

        self.column_give = Gtk.TreeViewColumn("You will give", self.cell_renderer, text=0)
        self.column_give.set_fixed_width(300)
        self.tree_view_give.append_column(self.column_give)

        self.arrow = Gtk.Image()
        self.arrow.set_from_icon_name('emblem-synchronizing', Gtk.IconSize.DIALOG)
        self.grid.attach(self.arrow, 1, 0, 1, 1)

        self.scroll_receive = Gtk.ScrolledWindow()
        self.scroll_receive.set_hexpand(True)
        self.scroll_receive.set_vexpand(True)
        self.grid.attach(self.scroll_receive, 2, 0, 1, 1)

        self.list_store_receive = Gtk.ListStore(str)
        self.tree_view_receive = Gtk.TreeView(model=self.list_store_receive)
        self.scroll_receive.add(self.tree_view_receive)

        self.column_receive = Gtk.TreeViewColumn("You will Receive", self.cell_renderer, text=0)
        self.column_receive.set_fixed_width(300)
        self.tree_view_receive.append_column(self.column_receive)

        self.info_label = Gtk.Label()
        self.info_label.set_justify(Gtk.Justification.CENTER)

        self.content_area.add(self.info_label)

        self.yes_button = Gtk.Button(_("Yes"))
        self.yes_button.connect("clicked", self.on_yes_button_clicked)
        self.content_area.add(self.yes_button)

        self.no_button = Gtk.Button(_("No"))
        self.no_button.connect("clicked", self.on_no_button_clicked)
        self.content_area.add(self.no_button)

        self.status_section.frame.show_all()

        if self.iter is None or len(model) == 0:
            self.set_default_size(300, 90)

            self.status_label.set_markup(
                utils.markup(_("No items to accept or cancel"), color='red')
            )

            self.header_bar.set_show_close_button(True)
            self.content_area.show()
        elif self.iter is False:
            self.info_label.set_markup(
                utils.markup(_("Do you really want to"), font_size='medium') +
                utils.markup(_(" {} ALL ").format(self.action.upper()), font_size='medium', font_weight='bold') +
                utils.markup(_("confirmations?"), font_size='medium') +
                utils.markup(_("\nIt can't be undone!"), color='red', font_weight='ultrabold')
            )

            self.info_label.show()
            self.yes_button.show()
            self.no_button.show()
            self.spin.show()
            self.content_area.show()
        else:
            self.set_default_size(600, 400)

            self.give_label.set_markup(
                utils.markup(
                    _("You are trading the following items with {}:").format(self.model[self.iter][4]),
                    color='blue',
                )
            )

            self.info_label.set_markup(
                utils.markup(_("Do you really want to {} that?").format(self.action), font_size='medium') +
                utils.markup(_("\nIt can't be undone!"), color='red', font_weight='ultrabold')
            )

            utils.copy_childrens(self.model, self.list_store_give, self.iter, 3)
            utils.copy_childrens(self.model, self.list_store_receive, self.iter, 5)

            self.content_area.show_all()

        self.connect('response', self.on_response)

    @staticmethod
    def on_response(dialog: Gtk.Dialog, response_id: int) -> None:
        dialog.destroy()

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        self.status_label.set_markup(utils.markup(_("Running"), color='green'))
        self.spin.start()
        self.yes_button.set_sensitive(False)
        self.no_button.set_sensitive(False)

        future: Any = asyncio.Future()

        if self.iter:
            asyncio.ensure_future(finalize(future, self.raw_action, self.model, self.iter))
        else:
            asyncio.ensure_future(batch_finalize(future, self.raw_action, self.model))

        future.add_done_callback(functools.partial(finalize_callback, dialog=self))

    def on_no_button_clicked(self, button: Gtk.Button) -> None:
        self.destroy()


@config.Check("authenticator")
async def finalize(
        future: Any,
        action: str,
        model: Gtk.TreeModel,
        iter_: Gtk.TreeIter,
        identity_secret: Optional[config.ConfigStr] = None,
        steamid: Optional[config.ConfigInt] = None,
        deviceid: Optional[config.ConfigStr] = None,
) -> None:
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        session.cookie_jar.update_cookies(config.login_cookies())
        http = webapi.Http(session, 'https://lara.click/api')

        result = await http.finalize_confirmation(
            identity_secret,
            steamid,
            deviceid,
            model[iter_][1],
            model[iter_][2],
            action,
        )
        assert isinstance(result, dict), "finalize_confirmation return is not a dict"
        future.set_result(result)


@config.Check("authenticator")
async def batch_finalize(
        future: Any,
        action: str,
        model: Gtk.TreeModel,
        identity_secret: Optional[config.ConfigStr] = None,
        steamid: Optional[config.ConfigInt] = None,
        deviceid: Optional[config.ConfigStr] = None,
) -> None:
    results = []

    for index in range(len(model)):
        iter_ = model[index].iter

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            session.cookie_jar.update_cookies(config.login_cookies())
            http = webapi.Http(session, 'https://lara.click/api')

            result = await http.finalize_confirmation(
                identity_secret,
                steamid,
                deviceid,
                model[iter_][1],
                model[iter_][2],
                action,
            )

            results.append(result)
            assert isinstance(result, dict), "finalize_confirmation return is not a dict"

    future.set_result(results)


def finalize_callback(
        future: Any,
        dialog: Gtk.Dialog
) -> None:
    log.debug("confirmation finalized. The return is %s", future.result())
    dialog.destroy()
