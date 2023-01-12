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
from gi.repository import Gio, Gtk
from subprocess import call
from typing import Union, Optional, Tuple, Any, List

import stlib
from stlib import login, universe
from . import confirmation, utils, coupon
from .. import config, i18n, core

_ = i18n.get_translation
log = logging.getLogger(__name__)

if stlib.steamworks_available:
    from stlib import client


# noinspection PyUnusedLocal
class Main(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, title: str) -> None:
        super().__init__(application=application, title=title)
        self.application = application
        header_bar = Gtk.HeaderBar()

        menu = Gio.Menu()
        menu.append(_("Settings"), "app.settings")
        menu.append(_("About"), "app.about")
        menu.append(_("Exit"), "app.exit")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(650, 10)
        self.set_resizable(False)

        if config.parser.getboolean("general", "show_close_button"):
            self.set_deletable(True)
        else:
            self.set_deletable(False)

        self.set_titlebar(header_bar)
        self.set_title('Steam Tools NG')

        main_grid = Gtk.Grid()
        main_grid.set_margin_start(10)
        main_grid.set_margin_end(10)
        main_grid.set_margin_top(10)
        main_grid.set_margin_bottom(10)
        self.set_child(main_grid)

        self.user_info_label = Gtk.Label()
        self.user_info_label.set_halign(Gtk.Align.END)
        header_bar.pack_start(self.user_info_label)

        stack = Gtk.Stack()
        stack.set_hhomogeneous(True)
        main_grid.attach(stack, 1, 2, 1, 1)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        main_grid.attach(switcher, 1, 1, 1, 1)

        general_section = utils.Section("general", _("General"))
        general_section.stackup_section(stack)

        coupons_section = utils.Section("coupons", _("Free Coupons"))
        coupons_section.stackup_section(stack)

        self.status_grid = Gtk.Grid()
        self.status_grid.set_row_spacing(10)
        self.status_grid.set_column_spacing(10)
        self.status_grid.set_column_homogeneous(True)
        general_section.grid.attach(self.status_grid, 0, 0, 4, 1)

        # grid managed by plugin switch
        self.steamtrades_status = utils.Status(5, config.plugins['steamtrades'])
        self.steamgifts_status = utils.Status(5, config.plugins['steamgifts'])
        self.steamguard_status = utils.Status(4, config.plugins['steamguard'])
        self.cardfarming_status = utils.Status(6, config.plugins['cardfarming'])

        self.confirmations_grid = Gtk.Grid()
        self.confirmations_grid.set_size_request(655, 250)
        self.confirmations_grid.set_row_spacing(10)
        general_section.grid.attach(self.confirmations_grid, 0, 1, 4, 1)

        self.confirmation_tree = utils.SimpleTextTree(
            _('confid'), _('creatorid'), _('key'), _('give'), _('to'), _('receive'),
            overlay_scrolling=False,
        )

        self.confirmations_grid.attach(self.confirmation_tree, 0, 0, 4, 1)

        for index, column in enumerate(self.confirmation_tree.view.get_columns()):
            if index in (0, 1, 2):
                column.set_visible(False)

            if index == 4:
                column.set_fixed_width(140)
            else:
                column.set_fixed_width(220)

        self.confirmation_tree.view.set_has_tooltip(True)
        self.confirmation_tree.view.connect('query-tooltip', self.on_query_confirmations_tooltip)

        confirmation_tree_selection = self.confirmation_tree.view.get_selection()
        confirmation_tree_selection.connect("changed", self.on_tree_selection_changed)

        accept_button = Gtk.Button()
        accept_button.set_margin_start(5)
        accept_button.set_margin_end(5)
        accept_button.set_label(_('Accept selected'))
        accept_button.connect('clicked', self.on_validate_confirmations, "allow", confirmation_tree_selection)
        self.confirmations_grid.attach(accept_button, 0, 1, 1, 1)

        cancel_button = Gtk.Button()
        cancel_button.set_margin_start(5)
        cancel_button.set_margin_end(5)
        cancel_button.set_label(_('Cancel selected'))
        cancel_button.connect('clicked', self.on_validate_confirmations, "cancel", confirmation_tree_selection)
        self.confirmations_grid.attach(cancel_button, 1, 1, 1, 1)

        accept_all_button = Gtk.Button()
        accept_all_button.set_margin_start(5)
        accept_all_button.set_margin_end(5)
        accept_all_button.set_label(_('Accept all'))
        accept_all_button.connect('clicked', self.on_validate_confirmations, "allow", self.confirmation_tree.store)
        self.confirmations_grid.attach(accept_all_button, 2, 1, 1, 1)

        cancel_all_button = Gtk.Button()
        cancel_all_button.set_margin_start(5)
        cancel_all_button.set_margin_end(5)
        cancel_all_button.set_label(_('Cancel all'))
        cancel_all_button.connect('clicked', self.on_validate_confirmations, "cancel", self.confirmation_tree.store)
        self.confirmations_grid.attach(cancel_all_button, 3, 1, 1, 1)

        self.coupon_grid = Gtk.Grid()
        self.coupon_grid.set_size_request(655, 300)
        self.coupon_grid.set_row_spacing(10)
        coupons_section.grid.attach(self.coupon_grid, 0, 1, 1, 1)

        self.coupon_warning = Gtk.Label()
        self.coupon_warning.set_markup(utils.markup(
            _("Warning: It's a heavy uncached operation. Fetch only once a day or you will be blocked."),
            color='red',
        ))
        coupons_section.grid.attach(self.coupon_warning, 0, 0, 1, 1)

        self.coupon_tree = utils.SimpleTextTree(
            _('price'), _('name'), 'link', 'botid', 'token', 'assetid',
            overlay_scrolling=False,
            model=Gtk.ListStore,
        )

        self.coupon_tree.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.coupon_tree.store.set_sort_func(0, self.coupon_sorting)
        self.coupon_grid.attach(self.coupon_tree, 0, 0, 4, 2)

        for index, column in enumerate(self.coupon_tree.view.get_columns()):
            if index in (2, 3, 4, 5):
                column.set_visible(False)

        self.coupon_tree.view.connect('row-activated', self.on_coupon_double_clicked)

        coupon_tree_selection = self.coupon_tree.view.get_selection()
        coupon_tree_selection.connect("changed", self.on_tree_selection_changed)

        self.coupon_progress = Gtk.LevelBar()
        self.coupon_grid.attach(self.coupon_progress, 0, 3, 4, 1)

        get_coupon_button = Gtk.Button()
        get_coupon_button.set_margin_start(5)
        get_coupon_button.set_margin_end(5)
        get_coupon_button.set_label(_('Get selected coupon'))
        get_coupon_button.connect('clicked', self.on_coupon_action, coupon_tree_selection)
        self.coupon_grid.attach(get_coupon_button, 2, 4, 1, 1)

        give_coupon_button = Gtk.Button()
        give_coupon_button.set_margin_start(5)
        give_coupon_button.set_margin_end(5)
        give_coupon_button.set_label(_('Giveaway your coupons'))
        give_coupon_button.connect('clicked', self.on_coupon_action)
        self.coupon_grid.attach(give_coupon_button, 3, 4, 1, 1)

        fetch_coupons_button = Gtk.Button()
        fetch_coupons_button.set_margin_start(5)
        fetch_coupons_button.set_margin_end(5)
        fetch_coupons_button.set_label(_('Fetch coupons'))
        fetch_coupons_button.connect('clicked', self.on_fetch_coupons)
        self.coupon_grid.attach(fetch_coupons_button, 0, 4, 1, 1)

        self.fetch_coupon_event = asyncio.Event()

        stop_fetching_coupons_button = Gtk.Button()
        stop_fetching_coupons_button.set_margin_start(5)
        stop_fetching_coupons_button.set_margin_end(5)
        stop_fetching_coupons_button.set_label(_('Stop fetching coupons'))
        stop_fetching_coupons_button.connect('clicked', self.on_stop_fetching_coupons)
        self.coupon_grid.attach(stop_fetching_coupons_button, 1, 4, 1, 1)

        self.statusbar = utils.StatusBar()
        main_grid.attach(self.statusbar, 1, 3, 1, 1)

        self.connect("destroy", self.application.on_exit_activate)
        self.connect("close-request", self.application.on_exit_activate)

        loop = asyncio.get_event_loop()

        plugin_switch_task = loop.create_task(self.plugin_switch())
        plugin_switch_task.add_done_callback(utils.safe_task_callback)

        user_info_task = loop.create_task(self.user_info())
        user_info_task.add_done_callback(utils.safe_task_callback)

    async def user_info(self) -> None:
        while self.get_realized():
            theme = config.parser.get('general', 'theme')
            account_name = config.parser.get('login', 'account_name')
            steamid_raw = config.parser.get('login', 'steamid')

            try:
                steamid = universe.generate_steamid(steamid_raw)
            except ValueError:
                log.warning(_("SteamId is invalid"))
                steamid = None

            login_session = None

            with contextlib.suppress(IndexError):
                login_session = login.Login.get_session(0)

            if not steamid or not login_session or not await login_session.is_logged_in(steamid):
                self.application.main_window.user_info_label.set_markup(
                    utils.markup(
                        _('Not logged in'),
                        color='darkred' if theme == 'light' else 'red',
                        size='small',
                    )
                )

                await asyncio.sleep(5)
                continue

            self.application.main_window.user_info_label.set_markup(
                utils.markup(
                    _('You are logged in as:\n'),
                    color='darkgreen' if theme == 'light' else 'green',
                    size='small',
                ) +
                utils.markup(
                    account_name,
                    color='darkblue' if theme == 'light' else 'blue',
                    size='small',
                ) +
                utils.markup(
                    f" {self.application.steamid.id3_string}",
                    color='grey',
                    size='small',
                )
            )

            await asyncio.sleep(30)

    async def plugin_switch(self) -> None:
        plugins_enabled: List[str] = []
        plugins_status: List[utils.Status] = []

        for plugin_name in config.plugins.keys():
            if plugin_name in ["confirmations", "coupons"]:
                continue

            plugins_status.append(getattr(self, f'{plugin_name}_status'))

        while self.get_realized():
            plugins: List[str] = []

            for plugin_name in config.plugins.keys():
                enabled = config.parser.getboolean(plugin_name, "enable")

                if plugin_name == "confirmations":
                    if enabled:
                        self.confirmations_grid.show()
                    else:
                        self.confirmations_grid.hide()

                    continue

                if plugin_name == "coupons":
                    if enabled:
                        self.coupon_grid.show()
                    else:
                        self.coupon_grid.hide()

                    continue

                if enabled:
                    plugins.append(plugin_name)

            if plugins == plugins_enabled:
                self.status_grid.show()
                await asyncio.sleep(1)
                continue

            plugins_enabled = plugins

            for status in plugins_status:
                self.status_grid.remove(status)

            for index, plugin_name in enumerate(plugins_enabled):
                status = getattr(self, f'{plugin_name}_status')

                if index == 0:
                    if len(plugins_enabled) >= 2:
                        self.status_grid.attach(status, 0, 0, 1, 1)
                    else:
                        self.status_grid.attach(status, 0, 0, 2, 1)

                if index == 1 and len(plugins_enabled) >= 2:
                    self.status_grid.attach(status, 1, 0, 1, 1)

                if index == 2:
                    if len(plugins_enabled) == 3:
                        self.status_grid.attach(status, 0, 1, 2, 1)
                    else:
                        self.status_grid.attach(status, 0, 1, 1, 1)

                if index == 3 and len(plugins_enabled) == 4:
                    self.status_grid.attach(status, 1, 1, 1, 1)

                status.show()

    @staticmethod
    def on_query_confirmations_tooltip(
            tree_view: Gtk.TreeView,
            x_coord: int,
            y_coord: int,
            keyboard_tip: bool,
            tooltip: Gtk.Tooltip,
    ) -> bool:
        context = tree_view.get_tooltip_context(x_coord, y_coord, keyboard_tip)

        if context[0]:
            if context.model.iter_depth(context.iter) != 0:
                return False

            tooltip.set_text(
                f'ConfID:{context.model.get_value(context.iter, 0)}\n'
                f'CreatorID{context.model.get_value(context.iter, 1)}\n'
                f'Key:{context.model.get_value(context.iter, 2)}'
            )

            return True

        return False

    def on_fetch_coupons(self, button: Gtk.Button) -> None:
        self.fetch_coupon_event.set()

    def on_stop_fetching_coupons(self, button: Gtk.Button) -> None:
        self.fetch_coupon_event.clear()

    def on_coupon_action(self, button: Gtk.Button, model: Union[Gtk.TreeModel, Gtk.TreeSelection] = None) -> None:
        if model:
            coupon_dialog = coupon.CouponDialog(self, self.application, *model.get_selected())
        else:
            coupon_dialog = coupon.CouponDialog(self, self.application)

        coupon_dialog.show()

    def on_validate_confirmations(
            self,
            button: Gtk.Button,
            action: str,
            model: Union[Gtk.TreeModel, Gtk.TreeSelection]) -> None:
        if isinstance(model, Gtk.TreeModel):
            finalize_dialog = confirmation.FinalizeDialog(
                self,
                self.application,
                action,
                model,
                False
            )
        else:
            finalize_dialog = confirmation.FinalizeDialog(
                self,
                self.application,
                action,
                *model.get_selected()
            )

        finalize_dialog.show()

    @staticmethod
    def on_coupon_double_clicked(view: Gtk.TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn) -> None:
        model = view.get_model()
        url = model[path][2]
        steam_running = False

        if stlib.steamworks_available:
            with contextlib.suppress(ProcessLookupError):
                with client.SteamGameServer() as server:
                    steam_running = True

        if steam_running:
            url = f"steam://openurl/{url}"

        call(f'{config.file_manager} "{url}"')

    @staticmethod
    def on_tree_selection_changed(selection: Gtk.TreeSelection) -> None:
        model, iter_ = selection.get_selected()

        if iter_:
            parent = model.iter_parent(iter_)

            if parent:
                selection.select_iter(parent)

    @staticmethod
    def coupon_sorting(model: Gtk.TreeModel, iter1: Gtk.TreeIter, iter2: Gtk.TreeIter, user_data: Any) -> Any:
        column, _ = model.get_sort_column_id()
        price1 = model.get_value(iter1, column)
        price2 = model.get_value(iter2, column)

        if float(price1) < float(price2):
            return -1

        if price1 == price2:
            return 0

        return 1

    def set_status(
            self,
            module: str,
            module_data: Optional[core.utils.ModuleData] = None,
            *,
            display: str = '',
            status: str = '',
            info: str = '',
            error: str = '',
            level: Tuple[int, int] = (0, 0),
            suppress_logging: bool = False,
    ) -> None:
        _status = getattr(self, f'{module}_status')

        if not module_data:
            module_data = core.utils.ModuleData(display, status, info, error, level, suppress_logging=suppress_logging)

        if module_data.display:
            if not module_data.suppress_logging:
                log.debug(f"display data: {module_data.display}")

            _status.set_display(module_data.display)
        else:
            _status.unset_display()

        if module_data.status:
            if not module_data.suppress_logging:
                log.debug(f"status data: {module_data.status}")

            _status.set_status(module_data.status)

        if module_data.info:
            if not module_data.suppress_logging:
                log.info(module_data.info)

            _status.set_info(module_data.info)

        if module_data.error:
            if not module_data.suppress_logging:
                log.error(module_data.error)

            _status.set_error(module_data.error)

        if module_data.level:
            _status.set_level(*module_data.level)

    def get_play_event(self, module: str) -> asyncio.Event:
        _status = getattr(self, f'{module}_status')
        assert isinstance(_status, utils.Status)
        return _status.play_event
