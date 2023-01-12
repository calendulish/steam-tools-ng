#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
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
from gi.repository import Gtk
from typing import Any, Dict, List, Tuple, Union

from stlib import universe, community
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
        self.community_session = community.Community.get_session(0)

        if action == "allow":
            self.action = _("accept")
        else:
            self.action = _("cancel")

        self.raw_action = action
        self.model = model
        self.iter = iter_

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_title_buttons(False)

        self.set_default_size(300, 60)
        self.set_title(_('Finalize Confirmation'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)

        self.content_area = self.get_content_area()
        self.content_area.set_orientation(Gtk.Orientation.VERTICAL)
        self.content_area.set_spacing(10)
        self.content_area.set_margin_start(10)
        self.content_area.set_margin_end(10)
        self.content_area.set_margin_top(10)
        self.content_area.set_margin_bottom(10)

        self.status = utils.SimpleStatus()
        self.content_area.append(self.status)

        self.yes_button = Gtk.Button()
        self.yes_button.set_label(_("Continue"))
        self.yes_button.connect("clicked", self.on_yes_button_clicked)
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button()
        self.no_button.set_label(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        if self.iter is None or not model:
            self.status.error(_("You must select something"))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.hide()
            self.no_button.hide()
        elif self.iter is False:
            self.status.info(
                _("Do you really want to {} ALL confirmations?\nIt can't be undone!").format(self.action.upper())
            )
        else:
            self.set_size_request(600, 400)

            self.give_label = Gtk.Label()
            self.content_area.append(self.give_label)

            self.receive_label = Gtk.Label()
            self.content_area.append(self.receive_label)

            self.give_label.set_markup(
                utils.markup(
                    _("You are trading the following items with {}:").format(self.model[self.iter][4]),
                    color='blue',
                )
            )

            self.status.info(_("Do you really want to {} that?\nIt can't be undone!").format(self.action.upper()))

            self.grid = Gtk.Grid()
            self.content_area.append(self.grid)

            self.give_tree = utils.SimpleTextTree(_("You will give"), fixed_width=300, model=Gtk.ListStore)
            self.grid.attach(self.give_tree, 0, 0, 1, 1)

            self.arrow = Gtk.Image()
            self.arrow.set_from_icon_name('emblem-synchronizing-symbolic')
            self.grid.attach(self.arrow, 1, 0, 1, 1)

            self.receive_tree = utils.SimpleTextTree(_("You will receive"), fixed_width=300, model=Gtk.ListStore)
            self.grid.attach(self.receive_tree, 2, 0, 1, 1)

            utils.copy_childrens(self.model, self.give_tree.store, self.iter, 3)
            utils.copy_childrens(self.model, self.receive_tree.store, self.iter, 5)

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
        self.header_bar.set_show_title_buttons(False)
        self.parent_window.confirmation_tree.lock = True
        loop = asyncio.get_event_loop()
        task: asyncio.Task[Union[Dict[str, Any], List[Tuple[Gtk.TreeIter, Dict[str, Any]]]]]

        if self.iter:
            task = loop.create_task(self.finalize())
        else:
            task = loop.create_task(self.batch_finalize())

        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, task: asyncio.Task[Any]) -> None:
        exception = task.exception()

        if exception and not isinstance(exception, asyncio.CancelledError):
            try:
                current_exception = task.exception()
                assert isinstance(current_exception, BaseException)
                raise current_exception
            except Exception as exception:
                stack = task.get_stack()

                for frame in stack:
                    log.error("%s at %s", type(exception).__name__, frame)

                log.error("Steam Server is slow. (%s)", str(exception))

                self.status.error(
                    _("Steam Server is slow. Please, try again.")
                )

                self.header_bar.set_show_title_buttons(True)
                self.yes_button.hide()
        else:
            self.parent_window.confirmation_tree.lock = False
            self.destroy()

    async def finalize(self, keep_iter: bool = False) -> Dict[str, Any]:
        identity_secret = config.parser.get("login", "identity_secret")
        deviceid = config.parser.get("login", "deviceid")
        steamid_raw = config.parser.getint("login", "steamid")

        try:
            steamid = universe.generate_steamid(steamid_raw)
        except ValueError:
            self.status.info(_("Your steam is invalid. (are you logged in?)"))
            await asyncio.sleep(5)
            return {}

        self.status.info(_("Waiting Steam Server (OP: {})").format(self.model[self.iter][1]))

        # steam confirmation server isn't reliable
        for i in range(2):
            result = await self.community_session.send_confirmation(
                identity_secret,
                universe.generate_steamid(steamid),
                deviceid,
                self.model[self.iter][0],
                self.model[self.iter][2],
                self.raw_action,
            )
            await asyncio.sleep(0.5)

        if not keep_iter:
            try:
                self.model.remove(self.iter)
            except IndexError:
                log.debug(_("Unable to remove tree path %s (already removed?). Ignoring."), self.iter)

        # noinspection PyUnboundLocalVariable
        assert isinstance(result, dict)
        return result

    async def batch_finalize(self) -> List[Tuple[Gtk.TreeIter, Dict[str, Any]]]:
        results = []
        batch_status = utils.Status(20, "")
        batch_status.set_pausable(False)
        self.content_area.append(batch_status)
        batch_status.get_label_widget().hide()
        batch_status.set_info(_("Waiting Steam Server response"))
        batch_status.show()
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
