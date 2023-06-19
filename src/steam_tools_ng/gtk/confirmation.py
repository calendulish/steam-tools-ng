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
import logging
from typing import Any, Dict, List, Tuple

from gi.repository import Gtk

from stlib import universe, community
from . import utils
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class FinalizeWindow(utils.StatusWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            confirmations_tree: utils.SimpleTextTree,
            action: str,
            batch: bool = False,
    ) -> None:
        super().__init__(parent_window, application)
        self.community_session = community.Community.get_session(0)
        self.confirmations_tree = confirmations_tree
        self.selection = self.confirmations_tree.model.get_selected_item()
        self.batch = batch

        if action == "allow":
            self.action = _("accept")
        else:
            self.action = _("cancel")

        self.raw_action = action

        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_title_buttons(False)
        self.set_titlebar(self.header_bar)
        self.set_title(_('Finalize Confirmation'))

        self.progress = Gtk.LevelBar()
        self.content_area.append(self.progress)

        self.yes_button = Gtk.Button()
        self.yes_button.set_label(_("Continue"))
        self.yes_button.connect("clicked", self.on_yes_button_clicked)
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button()
        self.no_button.set_label(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        if self.batch:
            self.status.info(
                _("Do you really want to {} ALL confirmations?\nIt can't be undone!").format(self.action.upper())
            )
        else:
            if self.selection:
                self.status.info(
                    _("Do you want to {} the offer (to {})?\nIt can't be undone!").format(
                        self.action.upper(),
                        utils.unmarkup(self.selection.get_item().to),
                    )
                )
            else:
                self.status.error(_("You must select something"))
                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
                self.no_button.set_visible(False)

        self.connect('destroy', lambda *args: self.destroy())
        self.connect('close-request', lambda *args: self.destroy())

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        button.set_visible(False)
        self.no_button.set_visible(False)
        self.set_size_request(0, 0)
        self.header_bar.set_show_title_buttons(False)
        self.confirmations_tree.lock = True

        loop = asyncio.get_event_loop()

        if self.batch:
            task = loop.create_task(self.batch_finalize())
        else:
            task = loop.create_task(self.single_finalize())

        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, task: asyncio.Task[Any]) -> None:
        self.confirmations_tree.lock = False
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
                    _(
                        "Unable to complete this trade. The reason is one of the following:\n\n"
                        "1. The item you choose already gone. Try another one.\n"
                        "2. You wrote a wrong token in config. Update you config.\n"
                        "3. The Steam server is slow. Wait a minute and try again.\n\n"
                        "If you keep seeing this error, please update the coupon list."
                    )
                )

                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
        else:
            self.destroy()

    async def do_finalize(self, item: Gtk.ListItem) -> Dict[str, Any]:
        identity_secret = config.parser.get("login", "identity_secret")
        deviceid = config.parser.get("login", "deviceid")
        steamid_raw = config.parser.getint("login", "steamid")

        try:
            steamid = universe.generate_steamid(steamid_raw)
        except ValueError:
            self.status.info(_("Your steam is invalid. (are you logged in?)"))
            await asyncio.sleep(5)
            return {}

        self.status.info(_("Waiting Steam Server (OP: {})").format(item.creatorid))
        result: Dict[str, Any] = {}

        # steam confirmation server isn't reliable
        for i in range(2):
            result = await self.community_session.send_confirmation(
                identity_secret,
                steamid,
                deviceid,
                item.id,
                item.nonce,
                self.raw_action,
            )
            await asyncio.sleep(0.5)

        assert isinstance(result, dict)
        return result

    async def single_finalize(self) -> Dict[str, Any]:
        item = self.selection.get_item()
        result = await self.do_finalize(item)
        self.confirmations_tree.remove_row(self.selection)

        assert isinstance(result, dict)
        return result

    async def batch_finalize(self) -> List[Tuple[Gtk.TreeIter, Dict[str, Any]]]:
        results = []
        n_rows = self.confirmations_tree.model.get_n_items()
        self.status.info(_("Waiting Steam Server response"))

        for index in range(n_rows):
            self.progress.set_value(index)
            self.progress.set_max_value(n_rows)
            row = self.confirmations_tree.model.get_item(index)
            item = row.get_item()
            result = await self.do_finalize(item)
            results.append((item, result))

        self.confirmations_tree.clear()

        return results
