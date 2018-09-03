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
import contextlib
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

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
            future: asyncio.Future,
            parent_window: Gtk.Window,
            webapi_session: webapi.SteamWebAPI,
            action: str,
            model: Gtk.TreeModel,
            iter_: Union[Gtk.TreeIter, bool, None] = False,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.future = future
        self.webapi_session = webapi_session

        if action == "allow":
            self.action = _("accept")
        else:
            self.action = _("cancel")

        self.raw_action = action
        self.model = model
        self.iter = iter_

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_close_button(False)

        self.set_default_size(300, 60)
        self.set_title(_('Finalize Confirmation'))
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_border_width(10)
        self.content_area.set_spacing(10)

        self.status = utils.SimpleStatus()
        self.content_area.add(self.status)

        self.yes_button = Gtk.Button(_("Continue"))
        self.yes_button.connect("clicked", self.on_yes_button_clicked)
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        if self.iter is None or len(model) == 0:
            self.status.error(_("No items to accept or cancel"))
            self.header_bar.set_show_close_button(True)
        elif self.iter is False:
            self.status.info(
                _("Do you really want to {} ALL confirmations?\nIt can't be undone!").format(self.action.upper())
            )
            self.header_bar.show_all()
        else:
            self.set_size_request(600, 400)

            self.give_label = Gtk.Label()
            self.content_area.add(self.give_label)

            self.receive_label = Gtk.Label()
            self.content_area.add(self.receive_label)

            self.give_label.set_markup(
                utils.markup(
                    _("You are trading the following items with {}:").format(self.model[self.iter][4]),
                    color='blue',
                )
            )

            self.status.info(_("Do you really want to {} that?\nIt can't be undone!").format(self.action.upper()))

            self.grid = Gtk.Grid()
            self.content_area.add(self.grid)

            self.give_tree = utils.SimpleTextTree((_("You will give"),), fixed_width=300, model=Gtk.ListStore)
            self.grid.attach(self.give_tree, 0, 0, 1, 1)

            self.arrow = Gtk.Image()
            self.arrow.set_from_icon_name('emblem-synchronizing', Gtk.IconSize.DIALOG)
            self.grid.attach(self.arrow, 1, 0, 1, 1)

            self.receive_tree = utils.SimpleTextTree((_("You will receive"),), fixed_width=300, model=Gtk.ListStore)
            self.grid.attach(self.receive_tree, 2, 0, 1, 1)

            utils.copy_childrens(self.model, self.give_tree._store, self.iter, 3)
            utils.copy_childrens(self.model, self.receive_tree._store, self.iter, 5)

            self.header_bar.show_all()

        self.content_area.show_all()

        self.connect('response', lambda dialog, response_id: self.destroy())

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        self.yes_button.hide()
        self.no_button.hide()

        with contextlib.suppress(AttributeError):
            self.give_label.hide()
            self.give_tree.hide()
            self.arrow.hide()
            self.receive_tree.hide()

        self.set_size_request(300, 60)
        self.status.info(_("Running... Please wait"))
        self.header_bar.set_show_close_button(False)

        if self.iter:
            task = asyncio.ensure_future(self.finalize())
        else:
            task = asyncio.ensure_future(self.batch_finalize())

        task.add_done_callback(self.on_task_finish)

    # FIXME: https://github.com/python/typing/issues/446
    # noinspection PyUnresolvedReferences
    def on_task_finish(self, future: 'asyncio.Future[Any]') -> None:
        if future.exception():
            self.status.error(_("An error occurred:\n\n{}").format(future.exception()))
            self.header_bar.set_show_close_button(True)
            self.yes_button.set_label(_("Try again?"))
            self.yes_button.show()
        else:
            self.destroy()

    @config.Check("login")
    async def finalize(
            self,
            identity_secret: Optional[config.ConfigStr] = None,
            steamid: Optional[config.ConfigInt] = None,
            deviceid: Optional[config.ConfigStr] = None,
            keep_iter: bool = False,
    ) -> Dict[str, Any]:
        self.status.info(_("Processing {}").format(self.model[self.iter][1]))

        server_time = await self.webapi_session.get_server_time()

        result = await self.webapi_session.finalize_confirmation(
            server_time,
            identity_secret,
            steamid,
            deviceid,
            self.model[self.iter][1],
            self.model[self.iter][2],
            self.raw_action,
        )
        assert isinstance(result, dict), "finalize_confirmation return is not a dict"

        if not keep_iter:
            self.model.remove(self.iter)

        return result

    @config.Check("login")
    async def batch_finalize(
            self,
            identity_secret: Optional[config.ConfigStr] = None,
            steamid: Optional[config.ConfigInt] = None,
            deviceid: Optional[config.ConfigStr] = None,
    ) -> List[Tuple[Gtk.TreeIter, Dict[str, Any]]]:
        results = []

        for index in range(len(self.model)):
            self.iter = self.model[index].iter

            result = await self.finalize(identity_secret, steamid, deviceid, True)
            results.append((self.iter, result))

        self.status.info(_("Updating tree"))
        for iter_, result in results:
            self.model.remove(iter_)

        return results
