#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2022
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
import time
from typing import Union, Optional

from gi.repository import Gtk

from stlib import community
from stlib import universe
from . import utils, confirmation
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class CouponDialog(Gtk.Dialog):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            model: Optional[Gtk.TreeModel] = None,
            iter_: Union[Gtk.TreeIter, bool, None] = False,
    ) -> None:
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.application = application
        self.community_session = community.Community.get_session(0)
        self.model = model
        self.iter = iter_

        self.header_bar = self.get_header_bar()
        self.header_bar.set_show_title_buttons(False)

        self.set_default_size(300, 60)
        self.set_title(_('Get Coupon'))
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
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button()
        self.no_button.set_label(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        trade_time = int(time.time()) - config.parser.getint('coupons', 'last_trade_time')
        if self.iter and trade_time < 120:
            self.status.error(_("You must wait {} seconds to get another coupon").format(120 - trade_time))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.hide()
            self.no_button.hide()
            return

        if self.iter is None:
            self.status.error(_("You must select something"))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.hide()
            self.no_button.hide()
        elif self.iter is False:
            self.status.info(
                _(
                    "You are about to giveaway all coupons in your inventory\n"
                    "The items will be automatically accepted and transfered in 1 minute"
                )
            )
            self.yes_button.connect("clicked", self.on_yes_button_clicked, 'give')
        else:
            self.status.info(
                _(
                    "You are about to request {}\n"
                    "The item will be automatically added at your inventory in 1 minute"
                ).format(utils.unmarkup(self.model.get_value(self.iter, 1)))
            )
            self.yes_button.connect("clicked", self.on_yes_button_clicked, 'get')

        self.connect('response', lambda dialog, response_id: self.destroy())

    def on_yes_button_clicked(self, button: Gtk.Button, mode: str) -> None:
        button.hide()
        self.no_button.hide()

        self.set_size_request(0, 0)
        self.header_bar.set_show_title_buttons(False)

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.send_trade_offer(mode))
        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, task: asyncio.Task) -> None:
        exception = task.exception()

        if exception and not isinstance(exception, asyncio.CancelledError):
            try:
                raise task.exception()
            except community.InventoryEmptyError:
                self.status.error(_("Inventory is empty."))
                self.header_bar.set_show_title_buttons(True)
            except Exception as exception:
                stack = task.get_stack()

                for frame in stack:
                    log.error(f"{type(exception).__name__} at {frame}")

                log.error(f"Steam Server is slow. {str(exception)}")

                self.status.error(
                    _("Steam Server is slow. Please, try again.")
                )

                self.header_bar.set_show_title_buttons(True)
                self.yes_button.hide()
        else:
            self.destroy()

    async def send_trade_offer(self, mode: str) -> None:
        self.status.info(_("Waiting Steam Server"))
        botid = config.parser.getint('coupons', 'botid')
        token = config.parser.get('coupons', 'token')
        contextid = config.parser.getint('coupons', 'contextid')
        appid = config.parser.getint('coupons', 'appid')
        steamid = config.parser.getint('login', 'steamid')
        give = []
        receive = []

        if mode == 'get':
            assetid = int(self.model.get_value(self.iter, 2))
            receive = [(appid, assetid, 1)]
        else:
            json_data = await self.community_session.get_inventory(
                universe.generate_steamid(steamid),
                appid,
                contextid,
            )

            for coupon in json_data:
                give.append((coupon.appid, coupon.assetid, coupon.amount))

        steamid = universe.generate_steamid(botid)
        json_data = await self.community_session.send_trade_offer(steamid, token, contextid, give, receive)

        if len(json_data) == 1 and 'tradeofferid' in json_data:
            config.new("coupons", "last_trade_time", int(time.time()))
            return

        if 'needs_email_confirmation' in json_data and json_data['needs_email_confirmation']:
            self.status.info(_('You will need to manually confirm the trade offer. Check your email.'))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.hide()
            # FIXME: track tradeoffer and wait for email confirmation
            config.new("coupons", "last_trade_time", int(time.time()) + 20)
            return

        if 'needs_mobile_confirmation' in json_data and json_data['needs_mobile_confirmation']:
            confirmation_store = self.parent_window.confirmation_tree.store
            confirmation_count = len(confirmation_store)

            while True:
                target = None

                for index in range(confirmation_count):
                    iter_ = confirmation_store[index].iter
                    if confirmation_store.get_value(iter_, 1) == json_data['tradeofferid']:
                        target = iter_
                        break

                if target:
                    break
                else:
                    self.status.info(_('Waiting trade confirmation'))
                    await asyncio.sleep(5)

            finalize_dialog = confirmation.FinalizeDialog(
                self.parent_window,
                self.application,
                'allow',
                confirmation_store, target,
            )

            finalize_dialog.show()
            finalize_dialog.yes_button.emit('clicked')
            config.new("coupons", "last_trade_time", int(time.time()))
            self.destroy()
