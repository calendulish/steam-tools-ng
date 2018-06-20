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
import itertools
import logging
import os

from gi.repository import GdkPixbuf, Gio, Gtk
from stlib import webapi

from . import confirmation, utils
from .. import config, i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class Main(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Steam Tools NG")
        self.application = application

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)

        icon = Gtk.Image()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(config.icons_dir, 'steam-tools-ng.png'), 28, 28)
        icon.set_from_pixbuf(pix)
        header_bar.pack_start(icon)

        menu = Gio.Menu()
        menu.append(_("Settings"), "app.settings")
        menu.append(_("About"), "app.about")

        menu_button = Gtk.MenuButton("☰")
        menu_button.set_use_popover(True)
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(600, 600)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_titlebar(header_bar)
        self.set_title('Steam Tools NG')

        main_grid = Gtk.Grid()
        main_grid.set_border_width(10)
        main_grid.set_row_spacing(10)
        self.add(main_grid)

        steamtrades_status = utils.Status(5, "SteamTrades (bump)")
        main_grid.attach(steamtrades_status, 0, 0, 4, 1)

        steamguard_status = utils.Status(4, _('Steam Guard Code'))
        main_grid.attach(steamguard_status, 0, 1, 4, 1)

        info_label = Gtk.Label()

        info_label.set_markup(
            utils.markup(_("If you have confirmations, they will be shown here. (15 seconds delay)"), color='blue')
        )

        main_grid.attach(info_label, 0, 2, 4, 1)

        warning_label = Gtk.Label()
        main_grid.attach(warning_label, 0, 3, 4, 1)

        tree_store = Gtk.TreeStore(*[str for number in range(6)])
        tree_view = Gtk.TreeView(model=tree_store)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(tree_view)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_overlay_scrolling(False)
        main_grid.attach(scrolled_window, 0, 4, 4, 1)

        cell_renderer = Gtk.CellRendererText()

        # noinspection PyProtectedMember
        for index, header in enumerate(webapi.Confirmation._fields):
            column = Gtk.TreeViewColumn(header, cell_renderer, text=index)

            if index == 0 or index == 1 or index == 2:
                column.set_visible(False)

            if index == 4:
                column.set_fixed_width(140)
            else:
                column.set_fixed_width(220)

            column.set_resizable(True)
            tree_view.append_column(column)

        tree_view.set_has_tooltip(True)
        tree_view.connect('query-tooltip', self.on_query_confirmations_tooltip)

        tree_selection = tree_view.get_selection()
        tree_selection.connect("changed", self.on_tree_selection_changed)

        accept_button = Gtk.Button(_('Accept selected'))
        accept_button.connect('clicked', self.on_accept_button_clicked, tree_selection)
        main_grid.attach(accept_button, 0, 5, 1, 1)

        cancel_button = Gtk.Button(_('Cancel selected'))
        cancel_button.connect('clicked', self.on_cancel_button_clicked, tree_selection)
        main_grid.attach(cancel_button, 1, 5, 1, 1)

        accept_all_button = Gtk.Button(_('Accept all'))
        accept_all_button.connect('clicked', self.on_accept_all_button_clicked, tree_store)
        main_grid.attach(accept_all_button, 2, 5, 1, 1)

        cancel_all_button = Gtk.Button(_('Cancel all'))
        cancel_all_button.connect('clicked', self.on_cancel_all_button_clicked, tree_store)
        main_grid.attach(cancel_all_button, 3, 5, 1, 1)

        main_grid.show_all()

        asyncio.ensure_future(self.check_steamguard_status(steamguard_status))
        asyncio.ensure_future(self.check_confirmations_status(tree_view, warning_label))
        asyncio.ensure_future(self.check_steamtrades_status(steamtrades_status))

        self.show_all()

    async def check_confirmations_status(
            self,
            tree_view: Gtk.TreeView,
            warning_label: Gtk.Label,
    ) -> None:
        while self.get_realized():
            status = self.application.confirmations_status
            tree_store = tree_view.get_model()
            warning_label.hide()

            if not status['running']:
                warning_label.set_markup(utils.markup(status['message'], color='white', background='red'))
                warning_label.show()
            elif not status['confirmations']:
                tree_store.clear()
            else:
                for confirmation_index, confirmation_ in enumerate(status['confirmations']):
                    give = confirmation_.give
                    receive = confirmation_.receive

                    if len(tree_store) == confirmation_index:
                        iter_ = tree_store.insert(None, confirmation_index)
                    else:
                        iter_ = tree_store[confirmation_index].iter

                    safe_give, give = utils.safe_confirmation_get(confirmation_, 'give')
                    safe_receive, receive = utils.safe_confirmation_get(confirmation_, 'receive')

                    tree_store[confirmation_index] = [
                        confirmation_.mode,
                        str(confirmation_.id),
                        str(confirmation_.key),
                        safe_give,
                        confirmation_.to,
                        safe_receive,
                    ]

                    if len(give) > 1 or len(receive) > 1:
                        for item_index, item in enumerate(itertools.zip_longest(give, receive)):
                            children_iter = tree_store.iter_nth_child(iter_, item_index)

                            if children_iter is None:
                                children_iter = tree_store.insert(iter_, item_index)

                            tree_store[children_iter] = ['', '', '', item[0], '', item[1]]

                    utils.match_column_childrens(tree_store, iter_, give, 3)
                    utils.match_column_childrens(tree_store, iter_, receive, 5)

                utils.match_rows(tree_store, status['confirmations'])

            await asyncio.sleep(1)

    async def check_steamtrades_status(
            self,
            status: utils.Status,
    ) -> None:
        while self.get_realized():
            steamtrades_status = self.application.steamtrades_status

            if steamtrades_status['trade_id']:
                status.set_current(steamtrades_status['trade_id'])

            if steamtrades_status['running']:
                status.set_info(steamtrades_status['message'])
                try:
                    status.set_level(steamtrades_status['progress'], steamtrades_status['maximum'])
                except KeyError:
                    status.set_level(0, 0)
            else:
                status.set_error(steamtrades_status['message'])

            await asyncio.sleep(0.5)

    async def check_steamguard_status(
            self,
            status: utils.Status,
    ) -> None:
        while self.get_realized():
            steamguard_status = self.application.steamguard_status

            if steamguard_status['running']:
                status.set_current(steamguard_status['code'])
                status.set_info(_("Running"))
                status.set_level(steamguard_status['progress'], steamguard_status['maximum'])
            else:
                status.set_error(steamguard_status['message'])

            await asyncio.sleep(0.125)

    @staticmethod
    def on_query_confirmations_tooltip(
            tree_view: Gtk.TreeView,
            x: int,
            y: int,
            tip: bool,
            tooltip: Gtk.Tooltip,
    ) -> bool:
        context = tree_view.get_tooltip_context(x, y, tip)

        if context[0]:
            if context.model.iter_depth(context.iter) != 0:
                return False

            tooltip.set_text('Id:{}\nKey:{}'.format(
                context.model.get_value(context.iter, 1),
                context.model.get_value(context.iter, 2),
            ))

            return True
        else:
            return False

    def on_accept_button_clicked(self, button: Gtk.Button, selection: Gtk.TreeSelection) -> None:
        finalize_dialog = confirmation.FinalizeDialog(self, "allow", *selection.get_selected())
        finalize_dialog.show()

    def on_cancel_button_clicked(self, button: Gtk.Button, selection: Gtk.TreeSelection) -> None:
        finalize_dialog = confirmation.FinalizeDialog(self, "cancel", *selection.get_selected())
        finalize_dialog.show()

    def on_accept_all_button_clicked(self, button: Gtk.Button, model: Gtk.TreeModel) -> None:
        finalize_dialog = confirmation.FinalizeDialog(self, "allow", model)
        finalize_dialog.show()

    def on_cancel_all_button_clicked(self, button: Gtk.Button, model: Gtk.TreeModel) -> None:
        finalize_dialog = confirmation.FinalizeDialog(self, "cancel", model)
        finalize_dialog.show()

    @staticmethod
    def on_tree_selection_changed(selection: Gtk.TreeSelection) -> None:
        model, iter_ = selection.get_selected()

        if iter_:
            parent = model.iter_parent(iter_)

            if parent:
                selection.select_iter(parent)
