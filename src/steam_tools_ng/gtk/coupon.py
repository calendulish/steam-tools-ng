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
import time
from typing import Any, Tuple, List

from gi.repository import Gtk

from stlib import community
from stlib import universe
from . import utils, confirmation
from .. import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class CouponWindow(utils.PopupWindowBase):
    def __init__(
            self,
            parent_window: Gtk.Window,
            application: Gtk.Application,
            coupons_tree: utils.SimpleTextTree,
            action: str
    ) -> None:
        super().__init__(parent_window, application)
        self.community_session = community.Community.get_session(0)
        self.coupons_tree = coupons_tree
        self.selection = self.coupons_tree.model.get_selected_item()
        self.has_status = False
        self.action = action
        self.header_bar.set_show_title_buttons(False)

        self.yes_button = Gtk.Button()
        self.yes_button.set_label(_("Continue"))
        self.header_bar.pack_end(self.yes_button)

        self.no_button = Gtk.Button()
        self.no_button.set_label(_("Cancel"))
        self.no_button.connect("clicked", lambda button: self.destroy())
        self.header_bar.pack_start(self.no_button)

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        if self.action == 'get':
            self.set_title(_('Get Coupon'))

            trade_time = int(time.time()) - config.parser.getint('coupons', 'last_trade_time')
            if trade_time < 120:
                self.status.error(_("You must wait {} seconds to get another coupon").format(120 - trade_time))
                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
                self.no_button.set_visible(False)
                return

            if self.selection:
                self.status.info(
                    _(
                        "You are about to request {}\n"
                        "The item will be automatically added at your inventory in 1 minute"
                    ).format(utils.unmarkup(self.selection.get_item().name))
                )
            else:
                self.status.error(_("You must select something"))
                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
                self.no_button.set_visible(False)
        else:
            self.set_title(_('Send Coupon'))

            self.status.info(
                _(
                    "You are about to giveaway all coupons in your inventory\n"
                    "The items will be automatically accepted and transferred in 1 minute"
                )
            )

        self.yes_button.connect("clicked", self.on_yes_button_clicked)

    def on_yes_button_clicked(self, button: Gtk.Button) -> None:
        button.set_visible(False)
        self.no_button.set_visible(False)
        self.set_size_request(0, 0)
        self.header_bar.set_show_title_buttons(False)
        self.coupons_tree.lock = True

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.send_trade_offer())
        task.add_done_callback(self.on_task_finish)

    def on_task_finish(self, task: asyncio.Task[Any]) -> None:
        self.coupons_tree.lock = False
        exception = task.exception()

        if exception and not isinstance(exception, asyncio.CancelledError):
            try:
                current_exception = task.exception()
                assert isinstance(current_exception, BaseException)
                raise current_exception
            except community.InventoryEmptyError:
                self.status.error(_("Inventory is empty."))
                self.header_bar.set_show_title_buttons(True)
            except Exception as exception:
                stack = task.get_stack()

                for frame in stack:
                    log.error(f"{type(exception).__name__} at {frame}")

                log.error(f"Steam Server is slow. {str(exception)}")

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
            if not self.has_status:
                if self.action == 'get':
                    config.new("coupons", "last_trade_time", int(time.time()))
                else:
                    self.parent_window.confirmations_tree.remove_row(self.selection)

                self.destroy()

    async def send_trade_offer(self) -> None:
        self.status.info(_("Waiting Steam Server"))
        contextid = config.parser.getint('coupons', 'contextid')
        appid = config.parser.getint('coupons', 'appid')
        botid_raw = config.parser.get('coupons', 'botid_to_donate')
        token = config.parser.get('coupons', 'token_to_donate')
        steamid_raw = config.parser.getint('login', 'steamid')

        try:
            steamid = universe.generate_steamid(steamid_raw)
        except ValueError:
            self.status.info(_("Your steamid is invalid. (are you logged in?)"))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.set_visible(False)
            self.has_status = True
            return

        give: List[Tuple[int, ...]] = []
        receive = []

        if self.action == 'get':
            botid_raw = self.selection.get_item().botid
            token = self.selection.get_item().token
            assetid = int(self.selection.get_item().assetid)
            receive = [(appid, assetid, 1)]
        else:
            json_data = await self.community_session.get_inventory(steamid, appid, contextid)

            give.extend(
                (coupon.appid, coupon.assetid, coupon.amount)
                for coupon in json_data
            )
        try:
            botid = universe.generate_steamid(botid_raw)
        except ValueError:
            self.status.info(_("botid to donation is invalid. Check your config."))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.set_visible(False)
            self.has_status = True
            return

        json_data = await self.community_session.send_trade_offer(botid, token, contextid, give, receive)

        if len(json_data) == 1 and 'tradeofferid' in json_data:
            return

        if 'needs_email_confirmation' in json_data and json_data['needs_email_confirmation']:
            self.status.info(_('You will need to manually confirm the trade offer. Check your email.'))
            self.header_bar.set_show_title_buttons(True)
            self.yes_button.set_visible(False)

            # FIXME: track tradeoffer and wait for email confirmation
            self.has_status = True
            return

        if 'needs_mobile_confirmation' in json_data and json_data['needs_mobile_confirmation']:
            if not config.parser.getboolean('confirmations', 'enable'):
                self.status.info(_(
                    "Mobile confirmation is needed but the confirmation module isn't enabled.\n"
                    "You will need to manually confirm the trade offer."
                ))

                self.header_bar.set_show_title_buttons(True)
                self.yes_button.set_visible(False)
                # FIXME: track and wait for manual confirmation
                self.has_status = True
                return

            confirmations_tree = self.parent_window.confirmations_tree
            target = None

            while True:
                for index in range(confirmations_tree.store.get_n_items()):
                    item = confirmations_tree.store.get_item(index)

                    if item.creatorid == json_data['tradeofferid']:
                        confirmations_tree.model.set_selected(index)
                        break

                if target:
                    break
                self.status.info(_('Waiting trade confirmation'))
                await asyncio.sleep(5)

            finalize_window = confirmation.FinalizeWindow(
                self.parent_window,
                self.application,
                confirmations_tree,
                'allow',
            )

            finalize_window.present()
            finalize_window.yes_button.emit('clicked')
