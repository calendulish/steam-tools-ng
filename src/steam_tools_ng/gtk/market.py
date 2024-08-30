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
from typing import Any, Dict

import aiohttp
import stlib.utils
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
            data: str,
    ) -> None:
        super().__init__(parent_window, application)
        self.community_session = community.Community.get_session(0)
        self.action = _(action)
        self.raw_action = action
        self.data = data
        self.tree = tree
        self.selection = self.tree.model.get_selected_item()

        self.header_bar.set_show_title_buttons(False)
        self.set_title(_('Market Monitor'))

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        steamid_raw = config.parser.getint("login", "steamid")

        try:
            self.steamid = universe.generate_steamid(steamid_raw)
        except ValueError:
            self.status.error(_("Your steamid is invalid. (are you logged in?)"))
            self.header_bar.set_show_title_buttons(True)
            return

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
            self.item = self.selection.get_item()
            sell_table = self.item.histogram.sell_order_table
            buy_table = self.item.histogram.buy_order_table
            default_price = universe.SteamPrice(0.03)

            if self.raw_action != 'cancel':
                price_map = {
                    'sell': {
                        'max': self.item.histogram.buy_order_price,
                        'min': sell_table[0].price - 0.01 if sell_table else default_price,
                        'same': sell_table[1].price - 0.01 if len(sell_table) > 1 else default_price,
                    },
                    'buy': {
                        'max': self.item.histogram.sell_order_price,
                        'min': buy_table[0].price + 0.01 if buy_table else default_price,
                        'same': buy_table[1].price + 0.01 if len(buy_table) > 1 else default_price,
                    }
                }

                self.price = price_map[self.raw_action][self.data]

                if self.price < 0.03:
                    price_offset = default_price
                else:
                    price_offset = universe.SteamPrice(self.price.fees(reverse=True)[0])

                message = _("{}\nDo you want to {} the item for {}?\nIt can't be undone!").format(
                    self.item.order.name,
                    self.action.upper(),
                    self.price.as_monetary_string(),
                )

                extra_message = ""

                if (self.raw_action == 'sell' and price_offset != self.price or
                        self.raw_action == 'buy' and self.price < 0.03):
                    self.price = price_offset
                    extra_message = _("\nItem will be listed for {} due steam market price calculation").format(
                        self.price.as_monetary_string(),
                    )

                self.status.info(
                    message,
                    utils.markup(extra_message, color='yellow'),
                )
            else:
                self.status.info(
                    _("{}\nDo you want to {} the order?\nIt can't be undone!").format(
                        self.item.order.name,
                        self.action.upper(),
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
        task = loop.create_task(self.single_action())
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

    async def cancel(self, order: stlib.community.Order, type_: str) -> None:
        if type_ == 'sell':
            self.status.info(_("Waiting Steam Server (OP: {})").format(order.assetid))

            # steam market server isn't reliable
            for tries in range(3):
                try:
                    await self.community_session.cancel_sell_order(order.orderid)
                    break
                except (community.MarketError, aiohttp.ClientError) as error:
                    if tries == 2:
                        raise error from None

                await asyncio.sleep(1)
        else:
            self.status.info(_("Waiting Steam Server (OP: {})").format(order.orderid))

            # steam market server isn't reliable
            for tries in range(3):
                try:
                    await self.community_session.cancel_buy_order(order.orderid)
                    break
                except (community.MarketError, aiohttp.ClientError) as error:
                    if tries == 2:
                        raise error from None

                await asyncio.sleep(1)

    async def sell(self, order: stlib.community.Order, price: universe.SteamPrice) -> Dict[str, Any]:
        self.status.info(_("Waiting Steam Server (OP: {})").format(order.assetid))

        # steam market server isn't reliable
        for tries in range(3):
            try:
                response = await self.community_session.sell_item(
                    self.steamid,
                    order.appid,
                    order.contextid,
                    order.assetid,
                    price,
                    order.amount,
                )
                break
            except (community.MarketError, aiohttp.ClientError) as error:
                if tries == 2:
                    raise error from None

            await asyncio.sleep(1)

        # noinspection PyUnboundLocalVariable
        return response

    async def buy(self, order: stlib.community.Order, price: universe.SteamPrice) -> Dict[str, Any]:
        self.status.info(_("Waiting Steam Server (OP: {})").format(order.orderid))

        # steam market server isn't reliable
        for tries in range(3):
            try:
                response = await self.community_session.buy_item(
                    order.appid,
                    order.hash_name,
                    price,
                    order.currency,
                    order.amount,
                )
                break
            except (community.MarketError, aiohttp.ClientError) as error:
                if tries == 2:
                    raise error from None

            await asyncio.sleep(1)

        # noinspection PyUnboundLocalVariable
        return response

    async def single_action(self) -> None:
        total_amount = self.item.order.amount

        if self.raw_action == 'sell':
            await self.cancel(self.item.order, "sell")
            await asyncio.sleep(2)

            await self.sell(self.item.order, self.price)

            self.item.histogram._replace(sell_order_price=self.price)  # noqa

            if self.data == 'same' and self.item.histogram.sell_order_table:
                total_amount += self.item.histogram.sell_order_table[0].quantity

            add_new = True

            if (self.item.histogram.sell_order_table and
                    self.item.order.price == self.item.histogram.sell_order_table[0].price):
                fixed_amount = self.item.histogram.sell_order_table[0].quantity - self.item.order.amount

                if fixed_amount > 0:
                    self.item.histogram.sell_order_table[0]._replace(quantity=fixed_amount)
                else:
                    self.item.histogram.sell_order_table[0]._replace(price=self.price)
                    self.item.histogram.sell_order_table[0]._replace(quantity=self.item.order.amount)
                    add_new = False

            if add_new:
                self.item.histogram.sell_order_table.insert(0, community.PriceInfo(self.price, self.item.order.amount))

            new_item = self.tree.new_item(
                self.item.name,
                utils.markup(f"${self.price.as_float()} ({self.item.order.amount})", foreground='green'),
                f"$ {self.price.as_float()} ({total_amount}:{self.item.histogram.sell_order_count})",
                self.item.buy_price,
                self.item.order,
                self.item.histogram,
            )
        elif self.raw_action == 'buy':
            await self.cancel(self.item.order, "buy")
            await asyncio.sleep(2)

            response = await self.buy(self.item.order, self.price)
            self.item.order._replace(orderid=response['buy_orderid'])  # noqa
            self.item.histogram._replace(buy_order_price=self.price)  # noqa

            if self.data == 'same' and self.item.histogram.buy_order_table:
                total_amount += self.item.histogram.buy_order_table[0].quantity

            add_new = True

            if (self.item.histogram.buy_order_table and
                    self.item.order.price == self.item.histogram.buy_order_table[0].price):
                fixed_amount = self.item.histogram.buy_order_table[0].quantity - self.item.order.amount

                if fixed_amount > 0:
                    self.item.histogram.buy_order_table[0]._replace(quantity=fixed_amount)
                else:
                    self.item.histogram.buy_order_table[0]._replace(price=self.price)
                    self.item.histogram.buy_order_table[0]._replace(quantity=self.item.order.amount)
                    add_new = False

            if add_new:
                self.item.histogram.buy_order_table.insert(0, community.PriceInfo(self.price, self.item.order.amount))

            new_item = self.tree.new_item(
                self.item.name,
                utils.markup(f"${self.price.as_float()} ({self.item.order.amount})", foreground='green'),
                self.item.sell_price,
                f"$ {self.price.as_float()} ({total_amount}:{self.item.histogram.buy_order_count})",
                self.item.order,
                self.item.histogram,
            )
        else:
            await self.cancel(self.item.order, self.data)
            await asyncio.sleep(2)
            self.tree.remove_item(self.item)
            return

        for i in range(1, 5):
            child = self.tree.new_item(
                sell_price=self.item.histogram.sell_order_table[i].price.as_monetary_string() +
                           f" ({self.item.histogram.sell_order_table[i].quantity})"
                if len(self.item.histogram.sell_order_table) > i else '-',
                buy_price=self.item.histogram.buy_order_table[i].price.as_monetary_string() +
                          f" ({self.item.histogram.buy_order_table[i].quantity})"
                if len(self.item.histogram.buy_order_table) > i else '-'
            )

            new_item.children.append(child)

        self.tree.append_row(new_item)
        self.tree.remove_item(self.item)
