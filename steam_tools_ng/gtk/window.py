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

from gi.repository import Gio, Gtk
from stlib import webapi

from . import confirmation, utils
from .. import i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class Main(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Steam Tools NG")
        self.application = application

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)

        menu = Gio.Menu()
        menu.append(_("Settings"), "app.settings")
        menu.append(_("About"), "app.about")

        menu_button = Gtk.MenuButton("☰")
        menu_button.set_use_popover(True)
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(700, 450)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_titlebar(header_bar)
        self.set_title('Steam Tools NG')

        main_grid = Gtk.Grid()
        self.add(main_grid)

        self.show_all()

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_duration(500)
        stack.add_titled(self.authenticator_tab(), "authenticator", _("Authenticator"))
        stack.add_titled(self.confirmations_tab(), "confirmations", _("Confirmations"))
        stack.add_titled(self.steamtrades_tab(), "steamtrades", _("Steamtrades"))
        stack.show()

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        sidebar.show()

        main_grid.attach(sidebar, 0, 0, 1, 1)
        main_grid.attach_next_to(stack, sidebar, Gtk.PositionType.RIGHT, 1, 1)

    def authenticator_tab(self) -> Gtk.Grid:
        main_grid = Gtk.Grid()
        main_grid.set_border_width(10)
        main_grid.set_row_spacing(10)

        steam_guard_section = utils.new_section("authenticator", _('Steam Guard Code'))
        main_grid.attach(steam_guard_section.frame, 0, 0, 1, 1)

        code_label = Gtk.Label()
        code_label.set_markup(utils.markup('_ _ _ _', font_size='large', font_weight='bold'))
        code_label.set_hexpand(True)
        code_label.set_selectable(True)
        steam_guard_section.grid.attach(code_label, 0, 0, 1, 1)

        status_label = Gtk.Label()
        status_label.set_markup(utils.markup(_("loading..."), color='green'))
        steam_guard_section.grid.attach(status_label, 0, 1, 1, 1)

        level_bar = Gtk.LevelBar()
        steam_guard_section.grid.attach(level_bar, 0, 2, 1, 1)

        tip = Gtk.Label(_(
            "A code will be requested every time you try to log in on Steam.\n\n"
            "Tip: If you are not on a shared computer, select 'Remember password'\n"
            "when you log in to Steam Client so you do not have to enter the password and\n"
            "the authenticator code."
        ))

        tip.set_vexpand(True)
        tip.set_justify(Gtk.Justification.CENTER)
        tip.set_valign(Gtk.Align.END)
        main_grid.attach(tip, 0, 3, 2, 1)

        steam_guard_section.frame.show_all()
        tip.show()
        main_grid.show()

        asyncio.ensure_future(self.check_authenticator_status(code_label, status_label, level_bar))

        return main_grid

    def confirmations_tab(self) -> Gtk.Grid:
        main_grid = Gtk.Grid()

        info_label = Gtk.Label()

        info_label.set_markup(
            utils.markup(_("If you have confirmations, they will be shown here. (15 seconds delay)"), color='blue')
        )

        main_grid.attach(info_label, 0, 0, 4, 1)

        warning_label = Gtk.Label()
        main_grid.attach(warning_label, 0, 1, 4, 1)

        tree_store = Gtk.TreeStore(*[str for number in range(6)])
        tree_view = Gtk.TreeView(model=tree_store)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(tree_view)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_overlay_scrolling(False)
        main_grid.attach(scrolled_window, 0, 2, 4, 1)

        cell_renderer = Gtk.CellRendererText()

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
        main_grid.attach(accept_button, 0, 3, 1, 1)

        cancel_button = Gtk.Button(_('Cancel selected'))
        cancel_button.connect('clicked', self.on_cancel_button_clicked, tree_selection)
        main_grid.attach(cancel_button, 1, 3, 1, 1)

        accept_all_button = Gtk.Button(_('Accept all'))
        accept_all_button.connect('clicked', self.on_accept_all_button_clicked, tree_store)
        main_grid.attach(accept_all_button, 2, 3, 1, 1)

        cancel_all_button = Gtk.Button(_('Cancel all'))
        cancel_all_button.connect('clicked', self.on_cancel_all_button_clicked, tree_store)
        main_grid.attach(cancel_all_button, 3, 3, 1, 1)

        main_grid.show_all()

        asyncio.ensure_future(self.check_confirmations_status(tree_view, warning_label))

        return main_grid

    def steamtrades_tab(self) -> Gtk.Grid:
        main_grid = Gtk.Grid()
        main_grid.set_border_width(10)
        main_grid.set_row_spacing(10)

        trade_bump_section = utils.new_section("steamtrades", _('Trades bump'))
        main_grid.attach(trade_bump_section.frame, 0, 0, 1, 1)

        current_trade_label = Gtk.Label()
        current_trade_label.set_hexpand(True)
        trade_bump_section.grid.attach(current_trade_label, 0, 0, 1, 1)

        status_label = Gtk.Label()
        status_label.set_markup(utils.markup(_("loading..."), color='green'))
        trade_bump_section.grid.attach(status_label, 0, 1, 1, 1)

        level_bar = Gtk.LevelBar()
        trade_bump_section.grid.attach(level_bar, 0, 2, 1, 1)

        trade_bump_section.frame.show_all()
        main_grid.show()

        asyncio.ensure_future(self.check_steamtrades_status(current_trade_label, status_label, level_bar))

        return main_grid

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
            current_trade_label: Gtk.Label,
            status_label: Gtk.Label,
            level_bar: Gtk.LevelBar,
    ) -> None:
        while self.get_realized():
            status = self.application.steamtrades_status

            if status['trade_id']:
                current_trade_label.set_markup(utils.markup(status['trade_id'], font_size='large', font_weight='bold'))

            if status['running']:
                status_label.set_markup(utils.markup(status['message'], color='green'))
                try:
                    level_bar.set_max_value(status['maximum'])
                    level_bar.set_value(status['progress'])
                except KeyError:
                    level_bar.set_value(0)
            else:
                status_label.set_markup(utils.markup(status['message'], color='red'))

            await asyncio.sleep(0.5)

    async def check_authenticator_status(
            self,
            code_label: Gtk.Label,
            status_label: Gtk.Label,
            level_bar: Gtk.LevelBar
    ) -> None:
        while self.get_realized():
            status = self.application.authenticator_status

            if status['running']:
                code_label.set_markup(utils.markup(status['code'], font_size='large', font_weight='bold'))
                status_label.set_markup(utils.markup(_("Running"), color='green'))
                level_bar.set_max_value(status['maximum'])
                level_bar.set_value(status['progress'])
            else:
                status_label.set_markup(utils.markup(status["message"], color='red'))

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
