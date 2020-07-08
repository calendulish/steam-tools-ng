#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2019
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
from typing import Any, Dict, List, Tuple, Union

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
            parent_window: Gtk.Window,
            application: Gtk.Application,
            action: str,
            model: Gtk.TreeModel,
            iter_: Union[Gtk.TreeIter, bool, None] = False,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.application = application

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
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

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

        if self.iter is None or not model:
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
            self.arrow.set_from_icon_name('emblem-synchronizing-symbolic', Gtk.IconSize.DIALOG)
            self.grid.attach(self.arrow, 1, 0, 1, 1)

            self.receive_tree = utils.SimpleTextTree((_("You will receive"),), fixed_width=300, model=Gtk.ListStore)
            self.grid.attach(self.receive_tree, 2, 0, 1, 1)

            utils.copy_childrens(self.model, self.give_tree.store, self.iter, 3)
            utils.copy_childrens(self.model, self.receive_tree.store, self.iter, 5)

            self.header_bar.show_all()

        self.content_area.show_all()

        self.connect('response', lambda dialog, response_id: self.destroy())

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        button.hide()
        self.no_button.hide()

        with contextlib.suppress(AttributeError):
            self.give_label.hide()
            self.give_tree.hide()
            self.arrow.hide()
            self.receive_tree.hide()

        self.set_size_request(0, 0)
        self.header_bar.set_show_close_button(False)
        self.parent_window.text_tree_lock = True

        task: asyncio.Future[Union[Dict[str, Any], List[Tuple[Any, Dict[str, Any]]]]]

        if self.iter:
            task = asyncio.ensure_future(self.finalize())
        else:
            task = asyncio.ensure_future(self.batch_finalize())

        task.add_done_callback(self.on_task_finish)

    # FIXME: https://github.com/python/typing/issues/446
    # noinspection PyUnresolvedReferences
    def on_task_finish(self, future: 'asyncio.Future[Any]') -> None:
        if future.exception():
            try:
                raise future.exception()
            except Exception as exception:
                log.exception(str(exception))

                self.status.error(
                    _("Steam Server is slow. Please, try again.")
                )

                self.header_bar.set_show_close_button(True)
                self.yes_button.hide()
        else:
            self.parent_window.text_tree_lock = False
            self.destroy()

    async def finalize(self, keep_iter: bool = False) -> Dict[str, Any]:
        identity_secret = config.parser.get("login", "identity_secret")
        steamid = config.parser.getint("login", "steamid")
        deviceid = config.parser.get("login", "deviceid")

        self.status.info(_("Waiting Steam Server (OP: {})").format(self.model[self.iter][1]))

        result = await self.application.webapi_session.finalize_confirmation(
            identity_secret,
            steamid,
            deviceid,
            self.model[self.iter][1],
            self.model[self.iter][2],
            self.raw_action,
            time_offset=self.application.time_offset,
        )
        assert isinstance(result, dict), "finalize_confirmation return is not a dict"

        if not keep_iter:
            try:
                self.model.remove(self.iter)
            except IndexError:
                log.debug(_("Unable to remove tree path %s (already removed?). Ignoring."), self.iter)

        return result

    async def batch_finalize(self) -> List[Tuple[Gtk.TreeIter, Dict[str, Any]]]:
        results = []
        batch_status = utils.Status(20, "")
        self.content_area.add(batch_status)
        batch_status.get_label_widget().hide()
        batch_status.set_info(_("Waiting Steam Server response"))
        batch_status.show_all()
        self.status.hide()

        confirmation_count = len(self.model)

        for index in range(confirmation_count):
            self.iter = self.model[index].iter

            batch_status.set_display(self.model[self.iter][1])

            try:
                batch_status.set_level(index, confirmation_count)
            except KeyError:
                batch_status.set_level(0, 0)

            result = await self.finalize(True)
            results.append((self.iter, result))

        batch_status.hide()
        self.status.show()
        self.status.info(_("Updating tree"))
        for iter_, result in results:
            self.model.remove(iter_)

        return results
