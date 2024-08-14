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
class MarketWindow(utils.PopupWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            tree: utils.SimpleTextTree,
            action: str,
    ) -> None:
        super().__init__(parent_window, application)
        self.community_session = community.Community.get_session(0)
        self.action = _(action)
        self.raw_action = action
        self.tree = tree
        self.selection = self.tree.model.get_selected_item()

        self.header_bar.set_show_title_buttons(False)
        self.set_title(_('Market Monitor'))

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        self.progress = Gtk.LevelBar()
        self.progress.set_visible(False)
        self.content_grid.attach(self.progress, 0, 1, 1, 1)

        self.yes_button = Gtk.Button()
        self.yes_button.set_label(_("Continue"))
        self.yes_button.connect("clicked", self.on_yes_button_clicked)
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button()
        self.no_button.set_label(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        if self.selection:
            self.status.info(
                _("{}\nDo you want to {} the item for {}?\nIt can't be undone!").format(
                    self.selection.get_item().name,
                    self.action.upper(),
                    self.selection.get_item().trade_for,
                )
            )
        else:
            self.status.error(_("You must select something"))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.set_visible(False)
            self.no_button.set_visible(False)

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        button.set_visible(False)
        self.no_button.set_visible(False)
        self.progress.set_visible(True)
        self.set_size_request(0, 0)
        self.header_bar.set_show_title_buttons(False)
        self.tree.lock = True

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.single_action_test())
        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, task: asyncio.Task[Any]) -> None:
        self.progress.set_visible(False)
        self.tree.lock = False
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
                        "Unable to complete this confirmation. The reason is one of the following:\n\n"
                        "1. The order you choose already gone. Try to refetch market data.\n"
                        "2. The Steam server is slow. Wait a minute and try again.\n\n"
                        "If you keep seeing this error, verify if your account is able to use the market."
                    )
                )

                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
        else:
            self.destroy()

    async def single_action(self) -> None:
        item = self.selection.get_item()

        if self.raw_action == 'sell':
            self.status.info(_("Waiting Steam Server (OP: {})").format(item.assetid))
            await self.community_session.remove_sell_order(int(item.orderid))

            await asyncio.sleep(2)

            result = await self.community_session.sell_item(
                int(item.appid),
                int(item.contextid),
                int(item.assetid),
                int(item.trade_for),
                int(item.amount),
            )
        else:
            self.status.info(_("Waiting Steam Server (OP: {})").format(item.orderid))
            await self.community_session.remove_buy_order(int(item.orderid))

            await asyncio.sleep(2)

            result = await self.community_session.buy_item(
                int(item.appid),
                item.hash_name,
                int(item.trade_for),
                int(item.amount),
            )

        await asyncio.sleep(0.5)

        item.price = item.trade_for
        return None

    async def single_action_test(self) -> None:
        item = self.selection.get_item()

        if self.raw_action == 'sell':
            self.status.info(_("Waiting Steam Server (OP: {})").format(item.assetid))
            print(f'remove sell order: {item.orderid}')

            await asyncio.sleep(2)

            print(f'sell item \
                {item.appid} \
                {item.contextid} \
                {item.assetid} \
                {item.trade_for} \
                {item.amount}'
            )
        else:
            self.status.info(_("Waiting Steam Server (OP: {})").format(item.orderid))
            print(f'remove buy order: {item.orderid}')

            await asyncio.sleep(2)

            print(f'buy item \
                {item.appid} \
            {item.hash_nam} \
             {item.trade_for} \
            {item.amount}'
            )

        await asyncio.sleep(0.5)

        # TODO: Update item values in current list
        # TODO: remove and create a new one from scratch?
        return None
