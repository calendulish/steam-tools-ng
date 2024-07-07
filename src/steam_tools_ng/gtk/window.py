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
import contextlib
import logging
from pathlib import Path
from subprocess import call
from typing import Tuple, Any

import stlib
from gi.repository import Gio, Gtk, Gdk
from stlib import login, plugins

from . import confirmation, utils, coupon, authenticator
from .login import LoginWindow
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
        self._gtk_settings = Gtk.Settings.get_default()

        _display = Gdk.Display.get_default()
        _style_provider = Gtk.CssProvider()

        _style_provider.load_from_data(
            b"* { border-radius: 2px; }"
            b"label.warning { background-color: darkblue; color: white; }"
            b"label.critical { background-color: darkred; color: white; }"
        )

        _style_context = self.get_style_context()

        _style_context.add_provider_for_display(
            _display,
            _style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        header_bar = Gtk.HeaderBar()

        menu = Gio.Menu()
        menu.append(_("Preferences"), "app.settings")
        menu.append(_("About"), "app.about")
        menu.append(_("Exit"), "app.exit")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(750, 10)
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

        self.limited_label = Gtk.Label()
        self.limited_label.set_visible(False)
        self.limited_label.set_markup(
            utils.markup(
                _("Limited Account! Some modules will not work!"),
                background='red',
                color='white',
            )
        )
        main_grid.attach(self.limited_label, 1, 0, 1, 1)

        self.user_info_label = Gtk.Label()
        self.user_info_label.set_halign(Gtk.Align.END)
        header_bar.pack_start(self.user_info_label)

        self.main_tabs = Gtk.Stack()
        self.main_tabs.set_hhomogeneous(True)
        self.main_tabs.connect("notify::visible-child", self.on_stack_child_changed)
        main_grid.attach(self.main_tabs, 1, 2, 1, 1)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.main_tabs)
        main_grid.attach(switcher, 1, 1, 1, 1)

        steamguard_section = utils.Section("steamguard")
        steamguard_section.stackup_section("SteamGuard", self.main_tabs)

        cardfarming_section = utils.Section("cardfarming")
        cardfarming_section.stackup_section("CardFarming", self.main_tabs)

        steamgifts_section = utils.Section("steamgifts")
        steamgifts_section.stackup_section("SteamGifts", self.main_tabs)

        steamtrades_section = utils.Section("steamtrades")
        steamtrades_section.stackup_section("SteamTrades", self.main_tabs)

        coupons_section = utils.Section("coupons")
        coupons_section.stackup_section(_("Coupons"), self.main_tabs)

        # grid managed by plugin switch
        self.steamguard_status = utils.Status(4)
        self.cardfarming_status = utils.Status(6)
        self.steamgifts_status = utils.Status(5)
        self.steamtrades_status = utils.Status(5)

        steamguard_section.attach(self.steamguard_status, 0, 0, 2, 1)

        steamguard_stack = Gtk.Stack()
        steamguard_stack.set_vexpand(True)
        steamguard_section.attach(steamguard_stack, 1, 1, 1, 1)

        steamguard_sidebar = Gtk.StackSidebar()
        steamguard_sidebar.set_stack(steamguard_stack)
        steamguard_sidebar.set_size_request(150, -1)
        steamguard_section.attach(steamguard_sidebar, 0, 1, 1, 1)

        self.confirmations_grid = Gtk.Grid()
        self.confirmations_grid.set_row_spacing(10)
        steamguard_stack.add_titled(self.confirmations_grid, "confirmations", _("Confirmations"))

        confirmation_tree_headers = 'id', 'creatorid', 'nonce', '_give', '_to', '_receive', 'summary',
        self.confirmations_tree = utils.SimpleTextTree(*confirmation_tree_headers)
        self.confirmations_grid.attach(self.confirmations_tree, 0, 0, 4, 1)

        for index, column in enumerate(self.confirmations_tree.view.get_columns()):
            if index != 0:
                column.set_resizable(True)
                column.set_expand(True)

            if index in (1, 2, 3, 7):
                column.set_visible(False)

        self.confirmations_tree.model.connect("selection-changed", self.on_tree_selection_changed)

        accept_button = Gtk.Button()
        accept_button.set_margin_start(3)
        accept_button.set_margin_end(3)
        accept_button.set_label(_('Accept'))
        accept_button.connect('clicked', self.on_validate_confirmations, "allow")
        self.confirmations_grid.attach(accept_button, 0, 1, 1, 1)

        cancel_button = Gtk.Button()
        cancel_button.set_margin_start(3)
        cancel_button.set_margin_end(3)
        cancel_button.set_label(_('Cancel'))
        cancel_button.connect('clicked', self.on_validate_confirmations, "cancel")
        self.confirmations_grid.attach(cancel_button, 1, 1, 1, 1)

        accept_all_button = Gtk.Button()
        accept_all_button.set_margin_start(3)
        accept_all_button.set_margin_end(3)
        accept_all_button.set_label(_('Accept All'))
        accept_all_button.connect('clicked', self.on_validate_confirmations, "allow", True)
        self.confirmations_grid.attach(accept_all_button, 2, 1, 1, 1)

        cancel_all_button = Gtk.Button()
        cancel_all_button.set_margin_start(3)
        cancel_all_button.set_margin_end(3)
        cancel_all_button.set_label(_('Cancel All'))
        cancel_all_button.connect('clicked', self.on_validate_confirmations, "cancel", True)
        self.confirmations_grid.attach(cancel_all_button, 3, 1, 1, 1)

        steamguard_settings = utils.Section("steamguard")
        steamguard_settings.stackup_section(_("Settings"), steamguard_stack)
        steamguard_settings.set_halign(Gtk.Align.CENTER)

        self.steamguard_enable = steamguard_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 0)
        self.steamguard_enable.widget.set_margin_top(40)
        self.steamguard_enable.label.set_margin_top(40)
        self.steamguard_enable.connect("state-set", utils.on_setting_state_set)

        self.steamguard_disabled = Gtk.Label()
        self.steamguard_disabled.set_justify(Gtk.Justification.CENTER)
        self.steamguard_disabled.set_halign(Gtk.Align.CENTER)

        _message = _(
            "steamguard module has been disabled because you have\n"
            "logged in but no shared secret is found. To enable it again,\n"
            "click Settings -> Add STNG as your Steam Authenticator\n"
            "or go to Advanced and add a valid shared secret\n"
        )

        self.steamguard_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
        self.steamguard_disabled.set_visible(False)
        steamguard_section.attach(self.steamguard_disabled, 0, 0, 2, 1)

        self.confirmations_enable = steamguard_settings.new_item(
            "enable_confirmations", _("Enable Confirmations:"),
            Gtk.Switch,
            0, 1,
        )
        self.confirmations_enable.connect("state-set", utils.on_setting_state_set)

        self.confirmations_disabled = Gtk.Label()
        self.confirmations_disabled.set_justify(Gtk.Justification.CENTER)
        self.confirmations_disabled.set_halign(Gtk.Align.CENTER)

        _message = _(
            "confirmations module has been disabled because you have\n"
            "logged in but no identity secret is found. To enable it again,\n"
            "click Settings -> Add STNG as your Steam Authenticator\n"
            "or go to Advanced and add a valid identity secret\n"
        )

        self.confirmations_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
        self.confirmations_disabled.set_visible(False)
        self.confirmations_grid.attach(self.confirmations_disabled, 0, 0, 4, 1)

        login_button = Gtk.Button()
        login_button.set_margin_top(40)
        login_button.set_label(_("Login with another account"))
        login_button.set_name("login_button")
        login_button.connect('clicked', self.on_login_button_clicked)
        steamguard_settings.attach(login_button, 0, 2, 2, 1)

        new_authenticator_button = Gtk.Button()
        new_authenticator_button.set_label(_("Add STNG as your Steam Authenticator"))
        new_authenticator_button.set_name("new_authenticator_button")
        new_authenticator_button.connect("clicked", self.on_new_authenticator_clicked)
        steamguard_settings.attach(new_authenticator_button, 0, 3, 2, 1)

        remove_authenticator_button = Gtk.Button()
        remove_authenticator_button.set_label(_("Remove STNG Authenticator from your Steam Account"))
        remove_authenticator_button.set_name("remove_authenticator_button")
        remove_authenticator_button.connect("clicked", self.on_remove_authenticator_clicked)
        steamguard_settings.attach(remove_authenticator_button, 0, 4, 2, 1)

        reset_password_button = Gtk.Button()
        reset_password_button.set_label(_("Remove Saved Password"))
        reset_password_button.set_name("reset_password_button")
        reset_password_button.connect("clicked", self.on_reset_password_clicked)
        steamguard_settings.attach(reset_password_button, 0, 5, 2, 1)

        steamguard_advanced = utils.Section("login")
        steamguard_advanced.stackup_section(_("Advanced"), steamguard_stack, scroll=True)

        warning_label = Gtk.Label()
        warning_label.set_markup(utils.markup(
            _("Warning: Don't mess up these settings unless you know what you are doing!"),
            color='darkred' if self.theme == 'light' else 'red',
        ))
        steamguard_advanced.attach(warning_label, 0, 0, 2, 1)

        shared_secret = steamguard_advanced.new_item('shared_secret', _("Shared Secret:"), Gtk.Entry, 0, 1)
        shared_secret.connect('changed', utils.on_setting_changed)

        identity_secret = steamguard_advanced.new_item('identity_secret', _("Identity Secret:"), Gtk.Entry, 0, 4)
        identity_secret.connect('changed', utils.on_setting_changed)

        deviceid = steamguard_advanced.new_item('deviceid', _("Device ID:"), Gtk.Entry, 0, 5)
        deviceid.connect('changed', utils.on_setting_changed)

        steamid_item = steamguard_advanced.new_item("steamid", _("Steam ID:"), Gtk.Entry, 0, 6)
        steamid_item.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.connect("changed", utils.on_digit_only_setting_changed)

        account_name = steamguard_advanced.new_item('account_name', _("Username:"), Gtk.Entry, 0, 7)
        account_name.connect('changed', utils.on_setting_changed)

        reset_button = Gtk.Button()
        reset_button.set_label(_("Reset Everything (USE WITH CAUTION!!!)"))
        reset_button.set_name("reset_button")
        reset_button.connect("clicked", self.on_reset_clicked)
        steamguard_advanced.attach(reset_button, 0, 8, 2, 1)

        cardfarming_section.attach(self.cardfarming_status, 0, 0, 2, 1)

        cardfarming_stack = Gtk.Stack()
        cardfarming_stack.set_vexpand(True)
        cardfarming_section.attach(cardfarming_stack, 1, 1, 1, 1)

        cardfarming_sidebar = Gtk.StackSidebar()
        cardfarming_sidebar.set_stack(cardfarming_stack)
        cardfarming_sidebar.set_size_request(150, -1)
        cardfarming_section.attach(cardfarming_sidebar, 0, 1, 1, 1)

        cardfarming_settings = utils.Section("cardfarming")
        cardfarming_settings.stackup_section(_("Settings"), cardfarming_stack, scroll=True)

        cardfarming_enable = cardfarming_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 1)
        cardfarming_enable.connect("state-set", utils.on_setting_state_set)

        mandatory_waiting = cardfarming_settings.new_item("mandatory_waiting", _("Mandatory waiting:"), Gtk.Entry, 0, 2)
        mandatory_waiting.connect("changed", utils.on_digit_only_setting_changed)

        wait_while_running = cardfarming_settings.new_item(
            "wait_while_running",
            _("Wait while running:"),
            Gtk.Entry,
            0, 3,
        )
        wait_while_running.connect("changed", utils.on_digit_only_setting_changed)

        wait_for_drops = cardfarming_settings.new_item("wait_for_drops", _("Wait for drops:"), Gtk.Entry, 0, 4)
        wait_for_drops.connect("changed", utils.on_digit_only_setting_changed)

        max_concurrency = cardfarming_settings.new_item("max_concurrency", _("Max concurrency:"), Gtk.Entry, 0, 5)
        max_concurrency.connect("changed", utils.on_digit_only_setting_changed)

        cardfarming_invisible = cardfarming_settings.new_item("invisible", _("Invisible:"), Gtk.Switch, 0, 6)
        cardfarming_invisible.connect("state-set", utils.on_setting_state_set)

        reverse_sorting = cardfarming_settings.new_item("reverse_sorting", _("Reverse Sorting:"), Gtk.Switch, 0, 7)
        reverse_sorting.connect("state-set", utils.on_setting_state_set)

        if not stlib.steamworks_available:
            cardfarming_settings.set_sensitive(False)
            cardfarming_enable.set_active(False)
            _cardfarming_disabled = Gtk.Label()
            _cardfarming_disabled.set_justify(Gtk.Justification.CENTER)
            _cardfarming_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "cardfarming module has been disabled because you have\n"
                "a stlib built without SteamWorks support. To enable it again,\n"
                "reinstall stlib with SteamWorks support\n"
            )

            _cardfarming_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            cardfarming_section.attach(_cardfarming_disabled, 0, 0, 2, 1)

        steamgifts_section.attach(self.steamgifts_status, 0, 0, 2, 1)

        steamgifts_stack = Gtk.Stack()
        steamgifts_stack.set_vexpand(True)
        steamgifts_section.attach(steamgifts_stack, 1, 1, 1, 1)

        steamgifts_sidebar = Gtk.StackSidebar()
        steamgifts_sidebar.set_stack(steamgifts_stack)
        steamgifts_sidebar.set_size_request(150, -1)
        steamgifts_section.attach(steamgifts_sidebar, 0, 1, 1, 1)

        steamgifts_settings = utils.Section("steamgifts")
        steamgifts_settings.stackup_section(_("Settings"), steamgifts_stack)

        steamgifts_enable = steamgifts_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 0)
        steamgifts_enable.connect('state-set', utils.on_setting_state_set)

        developer_giveaways = steamgifts_settings.new_item(
            "developer_giveaways", _("Developer Giveaways"),
            Gtk.Switch,
            0, 1,
        )
        developer_giveaways.connect("state-set", utils.on_setting_state_set)

        steamgifts_mode = steamgifts_settings.new_item(
            "mode", _("Mode:"),
            Gtk.DropDown,
            0, 2,
            items=config.steamgifts_modes,
        )
        steamgifts_mode.connect("notify::selected", utils.on_dropdown_setting_changed, config.steamgifts_modes)

        wait_after_each_strategy = steamgifts_settings.new_item(
            "wait_after_each_strategy", _("Wait after each strategy:"),
            Gtk.Entry,
            0, 3,
        )
        wait_after_each_strategy.connect("changed", utils.on_digit_only_setting_changed)

        wait_after_full_cycle = steamgifts_settings.new_item(
            "wait_after_full_cycle", _("Wait after full cycle:"),
            Gtk.Entry,
            0, 4,
        )
        wait_after_full_cycle.connect("changed", utils.on_digit_only_setting_changed)

        minimum_points = steamgifts_settings.new_item("minimum_points", _("Minimum points:"), Gtk.Entry, 0, 5)
        minimum_points.connect("changed", utils.on_digit_only_setting_changed)

        for index in range(1, 6):
            strategy_section = utils.Section(f"steamgifts_strategy{index}")
            strategy_section.stackup_section(_("Strategy {}").format(index), steamgifts_stack, scroll=True)

            label = Gtk.Label()
            label.set_text(_("Strategy {}").format(index))
            strategy_section.attach(label, 0, 0, 1, 1)

            enable = strategy_section.new_item("enable", None, Gtk.Switch, 1, 0)
            enable.connect("state-set", utils.on_setting_state_set)

            minimum_label = Gtk.Label()
            minimum_label.set_text(_("Minimum"))
            strategy_section.attach(minimum_label, 0, 1, 1, 1)

            maximum_label = Gtk.Label()
            maximum_label.set_text(_("Maximum"))
            strategy_section.attach(maximum_label, 1, 1, 1, 1)

            for tree_level, item in enumerate(["points", "level", "copies", "metascore", "entries"]):
                minimum = strategy_section.new_item(f"minimum_{item}", _(item) + ':', Gtk.Entry, 0, tree_level + 2)
                minimum.connect("changed", utils.on_digit_only_setting_changed)

                maximum = strategy_section.new_item(f"maximum_{item}", None, Gtk.Entry, 1, tree_level + 2)
                maximum.connect("changed", utils.on_digit_only_setting_changed)

            restrict_type = strategy_section.new_item(
                "restrict_type",
                _("Restrict Type:"),
                Gtk.DropDown,
                0, 7,
                items=config.giveaway_types,
            )
            restrict_type.connect("notify::selected", utils.on_dropdown_setting_changed, config.giveaway_types)

            sort_type = strategy_section.new_item(
                "sort_type",
                _("Sort Type:"),
                Gtk.DropDown,
                0, 8,
                items=config.giveaway_sort_types,
            )
            sort_type.connect("notify::selected", utils.on_dropdown_setting_changed, config.giveaway_sort_types)

            # setattr(self, f"steamgifts_strategy{index}", strategy_section)

        if not plugins.has_plugin("steamgifts"):
            steamgifts_section.set_sensitive(False)
            steamgifts_enable.set_active(False)
            _steamgifts_disabled = Gtk.Label()
            _steamgifts_disabled.set_justify(Gtk.Justification.CENTER)
            _steamgifts_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamgifts module has been disabled because you don't\n"
                "have steamgifts plugin installed. To enable it again,\n"
                "install the steamgifts plugin.\n"
            )

            _steamgifts_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamgifts_section.attach(_steamgifts_disabled, 0, 0, 2, 2)

        steamtrades_section.attach(self.steamtrades_status, 0, 0, 2, 1)

        steamtrades_stack = Gtk.Stack()
        steamtrades_stack.set_vexpand(True)
        steamtrades_section.attach(steamtrades_stack, 1, 1, 1, 1)

        steamtrades_sidebar = Gtk.StackSidebar()
        steamtrades_sidebar.set_stack(steamtrades_stack)
        steamtrades_sidebar.set_size_request(150, -1)
        steamtrades_section.attach(steamtrades_sidebar, 0, 1, 1, 1)

        steamtrades_settings = utils.Section("steamtrades")
        steamtrades_settings.stackup_section(_("Settings"), steamtrades_stack)

        steamtrades_enable = steamtrades_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 1)
        steamtrades_enable.label.set_margin_top(40)
        steamtrades_enable.widget.set_margin_top(40)
        steamtrades_enable.connect("state-set", utils.on_setting_state_set)

        trade_ids = steamtrades_settings.new_item("trade_ids", _("Trade IDs:"), Gtk.Entry, 0, 2)
        trade_ids.set_placeholder_text('12345, asdfg, ...')
        trade_ids.connect("changed", utils.on_setting_changed)

        wait_for_bump = steamtrades_settings.new_item("wait_for_bump", _("Wait for Bump:"), Gtk.Entry, 0, 3)
        wait_for_bump.connect("changed", utils.on_digit_only_setting_changed)

        if not plugins.has_plugin("steamtrades"):
            steamtrades_settings.set_sensitive(False)
            steamtrades_enable.set_active(False)
            _steamtrades_disabled = Gtk.Label()
            _steamtrades_disabled.set_justify(Gtk.Justification.CENTER)
            _steamtrades_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamtrades module has been disabled because you don't\n"
                "have steamtrades plugin installed. To enable it again,\n"
                "install the steamtrades plugin.\n"
            )

            _steamtrades_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamtrades_settings.attach(_steamtrades_disabled, 0, 1, 2, 2)

        self.coupon_warning = Gtk.Label()
        self.coupon_warning.set_markup(utils.markup(
            _("Warning: It's a heavy uncached operation. Fetch only once a day or you will be blocked."),
            color='darkred' if self.theme == 'light' else 'red',
        ))
        self.coupon_warning.set_margin_top(37)
        self.coupon_warning.set_margin_bottom(37)
        coupons_section.attach(self.coupon_warning, 0, 0, 2, 1)

        coupons_stack = Gtk.Stack()
        coupons_stack.set_vexpand(True)
        coupons_section.attach(coupons_stack, 1, 1, 1, 1)

        coupons_sidebar = Gtk.StackSidebar()
        coupons_sidebar.set_stack(coupons_stack)
        coupons_sidebar.set_size_request(150, -1)
        coupons_section.attach(coupons_sidebar, 0, 1, 1, 1)

        self.coupons_grid = Gtk.Grid()
        self.coupons_grid.set_row_spacing(10)
        coupons_stack.add_titled(self.coupons_grid, "coupons_list", _("Coupon List"))

        coupons_tree_headers = '_price', '_name', 'link', 'botid', 'token', 'assetid'
        self.coupons_tree = utils.SimpleTextTree(*coupons_tree_headers)

        price_sorter = Gtk.CustomSorter()
        price_sorter.set_sort_func(self.coupon_sorting)

        price_column = self.coupons_tree.view.get_columns()[1]
        price_column.set_sorter(price_sorter)

        self.coupons_tree.view.sort_by_column(price_column, Gtk.SortType.ASCENDING)
        self.coupons_grid.attach(self.coupons_tree, 0, 0, 4, 2)

        for index, column in enumerate(self.coupons_tree.view.get_columns()):
            if column != 0:
                column.set_resizable(True)
                column.set_expand(True)

            if index in (0, 3, 4, 5, 6):
                column.set_visible(False)

        self.coupons_tree.view.connect("activate", self.on_coupon_double_clicked)
        self.coupons_tree.model.connect("selection-changed", self.on_tree_selection_changed)

        self.coupon_progress = Gtk.LevelBar()
        self.coupons_grid.attach(self.coupon_progress, 0, 3, 4, 1)

        self.coupon_running_progress = Gtk.ProgressBar()
        self.coupon_running_progress.set_pulse_step(0.5)
        self.coupons_grid.attach(self.coupon_running_progress, 0, 4, 4, 1)

        fetch_coupons_button = Gtk.Button()
        fetch_coupons_button.set_margin_start(3)
        fetch_coupons_button.set_margin_end(3)
        fetch_coupons_button.set_label(_('Fetch'))
        fetch_coupons_button.connect('clicked', self.on_fetch_coupons)
        self.coupons_grid.attach(fetch_coupons_button, 0, 5, 1, 1)

        self.fetch_coupon_event = asyncio.Event()

        stop_fetching_coupons_button = Gtk.Button()
        stop_fetching_coupons_button.set_margin_start(3)
        stop_fetching_coupons_button.set_margin_end(3)
        stop_fetching_coupons_button.set_label(_('Stop fetching'))
        stop_fetching_coupons_button.connect('clicked', self.on_stop_fetching_coupons)
        self.coupons_grid.attach(stop_fetching_coupons_button, 1, 5, 1, 1)

        get_coupon_button = Gtk.Button()
        get_coupon_button.set_margin_start(3)
        get_coupon_button.set_margin_end(3)
        get_coupon_button.set_label(_('Get selected'))
        get_coupon_button.connect('clicked', self.on_coupon_action, 'get')
        self.coupons_grid.attach(get_coupon_button, 2, 5, 1, 1)

        give_coupon_button = Gtk.Button()
        give_coupon_button.set_margin_start(3)
        give_coupon_button.set_margin_end(3)
        give_coupon_button.set_label(_('Send'))
        give_coupon_button.connect('clicked', self.on_coupon_action, 'give')
        self.coupons_grid.attach(give_coupon_button, 3, 5, 1, 1)

        coupons_settings = utils.Section("coupons")
        coupons_settings.stackup_section(_("Settings"), coupons_stack)

        coupon_botids = coupons_settings.new_item("botids", _("BotIDs:"), Gtk.Entry, 0, 1)
        coupon_botids.set_placeholder_text('12345, asdfg, ...')
        coupon_botids.connect("changed", utils.on_setting_changed)

        coupon_tokens = coupons_settings.new_item("tokens", _("Tokens:"), Gtk.Entry, 0, 2)
        coupon_tokens.set_placeholder_text('12345, asdfg, ...')
        coupon_tokens.connect("changed", utils.on_setting_changed)

        coupon_botid_to_donate = coupons_settings.new_item("botid_to_donate", _("BotID To Donate:"), Gtk.Entry, 0, 3)
        coupon_botid_to_donate.connect("changed", utils.on_digit_only_setting_changed)

        coupon_token_to_donate = coupons_settings.new_item("token_to_donate", _("Token To Donate:"), Gtk.Entry, 0, 4)
        coupon_token_to_donate.connect("changed", utils.on_setting_changed)

        coupon_blacklist = coupons_settings.new_item("blacklist", _("Blacklist:"), Gtk.Entry, 0, 5)
        coupon_blacklist.connect("changed", utils.on_setting_changed)

        coupon_discount = coupons_settings.new_item(
            "minimum_discount",
            _("Minimum Discount:"),
            Gtk.DropDown,
            0, 6,
            items=config.coupon_discounts,
        )
        coupon_discount.connect("notify::selected", utils.on_dropdown_setting_changed, config.coupon_discounts)

        self.statusbar = utils.StatusBar()
        main_grid.attach(self.statusbar, 1, 3, 1, 1)

        self.connect("destroy", lambda *args: core.safe_exit())
        self.connect("close-request", lambda *args: core.safe_exit())

        plugin_status_task = asyncio.create_task(self.plugin_status())
        plugin_status_task.add_done_callback(utils.safe_task_callback)

        user_info_task = asyncio.create_task(self.user_info())
        user_info_task.add_done_callback(utils.safe_task_callback)

        coupon_indicator_task = asyncio.create_task(self.coupon_running_indicator())
        coupon_indicator_task.add_done_callback(utils.safe_task_callback)

    @property
    def theme(self) -> str:
        option = config.parser.get('general', 'theme')

        if option == 'default':
            prefer_dark_theme = self._gtk_settings.get_property("gtk-application-prefer-dark-theme")
            return 'dark' if prefer_dark_theme else 'light'

        return option

    async def user_info(self) -> None:
        while self.get_realized():
            account_name = config.parser.get('login', 'account_name')
            steamid_raw = config.parser.get('login', 'steamid')
            login_session = None

            with contextlib.suppress(IndexError):
                login_session = login.Login.get_session(0)

            if (
                    not login_session
                    or not await login_session.is_logged_in()
                    or not self.application.steamid
            ):
                self.application.main_window.user_info_label.set_markup(
                    utils.markup(
                        _('Not logged in'),
                        color='darkred' if self.theme == 'light' else 'red',
                        size='small',
                    )
                )

                await asyncio.sleep(5)
                continue

            self.application.main_window.user_info_label.set_markup(
                utils.markup(
                    _('You are logged in as:\n'),
                    color='darkgreen' if self.theme == 'light' else 'green',
                    size='small',
                ) +
                utils.markup(
                    account_name,
                    color='darkblue' if self.theme == 'light' else 'blue',
                    size='small',
                ) +
                utils.markup(
                    f" {self.application.steamid.id3_string}",
                    color='grey',
                    size='small',
                )
            )

            if config.parser.get("login", "shared_secret"):
                self.steamguard_disabled.set_visible(False)
                self.steamguard_status.set_sensitive(True)
            else:
                self.steamguard_disabled.set_visible(True)
                self.steamguard_status.set_sensitive(False)
                self.steamguard_enable.set_active(False)

            if config.parser.get("login", "identity_secret"):
                self.confirmations_disabled.set_visible(False)
                self.confirmations_grid.set_sensitive(True)
            else:
                self.confirmations_disabled.set_visible(True)
                self.confirmations_grid.set_sensitive(False)
                self.confirmations_enable.set_active(False)

            self.on_stack_child_changed(self.main_tabs)
            await asyncio.sleep(30)

    async def plugin_status(self) -> None:
        while self.get_realized():
            for plugin_name in config.plugins.keys():
                if plugin_name in ["coupons", "confirmations"]:
                    if plugin_name == "confirmations":
                        enabled = config.parser.getboolean("steamguard", "enable_confirmations")
                    else:
                        enabled = config.parser.getboolean(plugin_name, "enable")

                    main = getattr(self, f'{plugin_name}_grid')
                    tree = getattr(self, f'{plugin_name}_tree')

                    if enabled:
                        tree.disabled = False
                        main.set_sensitive(True)
                    else:
                        tree.disabled = True
                        main.set_sensitive(False)
                else:
                    enabled = config.parser.getboolean(plugin_name, "enable")
                    status = getattr(self, f'{plugin_name}_status')

                    if not enabled:
                        def disabled_callback(status_: utils.SimpleStatus) -> None:
                            status_.set_status(_("Disabled"))
                            status_.set_info("")

                        asyncio.get_running_loop().call_later(3, disabled_callback, status)

            await asyncio.sleep(3)

    async def coupon_running_indicator(self) -> None:
        while self.get_realized():
            await self.fetch_coupon_event.wait()
            self.coupon_running_progress.pulse()
            await asyncio.sleep(1)

    def on_fetch_coupons(self, button: Gtk.Button) -> None:
        self.fetch_coupon_event.set()

    def on_stop_fetching_coupons(self, button: Gtk.Button) -> None:
        self.fetch_coupon_event.clear()
        self.coupon_progress.set_value(0)
        self.coupon_progress.set_max_value(0)
        self.coupon_running_progress.set_fraction(0)

    def on_coupon_action(self, button: Gtk.Button, action: str) -> None:
        coupon_window = coupon.CouponWindow(self, self.application, self.coupons_tree, action)
        coupon_window.present()

    def on_validate_confirmations(self, button: Gtk.Button, action: str, batch: bool = False) -> None:
        finalize_window = confirmation.FinalizeWindow(self, self.application, self.confirmations_tree, action, batch)
        finalize_window.present()

    def on_coupon_double_clicked(self, view: Gtk.ColumnView, position: int) -> None:
        row = self.coupons_tree.model.get_item(position)
        item = row.get_item()
        url = f"steam://openurl/{item.link}"
        steam_running = False

        if stlib.steamworks_available:
            with contextlib.suppress(ProcessLookupError):
                with client.SteamGameServer() as server:
                    steam_running = True

        if not steam_running:
            url = item.link

        call([config.file_manager, url])

    @staticmethod
    def on_tree_selection_changed(view: Gtk.SingleSelection, position: int, item_count: int) -> None:
        item = view.get_selected_item()
        if parent := item.get_parent():
            view.set_selected(parent.get_position())

    @staticmethod
    def on_stack_child_changed(tabs: Gtk.Stack, *args: Any) -> None:
        main_section = tabs.get_visible_child()

        if not (config_stack := main_section.get_child_at(1, 1)):
            log.debug("Not reading config values cause GUI didn't finish loading")
            return

        for config_section in config_stack.observe_children():
            if isinstance(config_section, Gtk.ScrolledWindow):
                # ScrolledWindow > ViewPort > Section
                config_section = config_section.get_child().get_child()

            if not isinstance(config_section, utils.Section):
                log.debug(f"Not reading config for {config_section} cause there's no config section")
                continue

            for item in config_section.items:
                if item.get_name().startswith('_'):
                    continue

                log.debug(f'Reading {item.section.get_name()}:{item.get_name()} from config file')
                item.update_values()

    @staticmethod
    def coupon_sorting(item1: utils.SimpleTextTreeItem, item2: utils.SimpleTextTreeItem, *data: Any) -> Any:
        if float(item1.price) < float(item2.price):
            return -1

        return 0 if item1.price == item2.price else 1

    def set_status(
            self,
            module: str,
            module_data: core.utils.ModuleData | None = None,
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

    def on_login_button_clicked(self, button: Gtk.Button) -> None:
        login_window = LoginWindow(self, self.application)
        login_window.shared_secret_item.set_text('')
        login_window.identity_secret_item.set_text('')
        login_window.present()

    def on_new_authenticator_clicked(self, button: Gtk.Button) -> None:
        authenticator_window = authenticator.AuthenticatorWindow(self, self.application)
        authenticator_window.present()

        task = asyncio.create_task(authenticator_window.on_add_authenticator())
        task.add_done_callback(utils.safe_task_callback)

    def on_remove_authenticator_clicked(self, button: Gtk.Button) -> None:
        authenticator_window = authenticator.AuthenticatorWindow(self, self.application)
        authenticator_window.present()

        task = asyncio.create_task(authenticator_window.on_remove_authenticator())
        task.add_done_callback(utils.safe_task_callback)

    def on_reset_clicked(self, button: Gtk.Button) -> None:
        login_window = LoginWindow(self, self.application)
        login_window.status.info(_("Reseting... Please wait!"))
        login_window.set_deletable(False)
        login_window.user_details_section.set_visible(False)
        login_window.no_steamguard.set_visible(False)
        login_window.present()

        config.cookies_file.unlink(missing_ok=True)
        config.config_file.unlink(missing_ok=True)

        log_directory = config.parser.get("logger", "log_directory")
        Path(log_directory, 'steam-tools-ng.log').unlink()
        Path(log_directory, 'steam-tools-ng.log.1').unlink()

        login_window.status.info(_("Successful!\nExiting..."))
        asyncio.get_running_loop().call_later(3, lambda: core.safe_exit())

    def on_reset_password_clicked(self, button: Gtk.Button) -> None:
        reseting_window = utils.PopupWindowBase(self, self.application)

        reseting_status = utils.SimpleStatus()
        reseting_status.info(_("Removing saved password..."))

        reseting_window.content_grid.attach(reseting_status, 0, 0, 1, 1)
        reseting_window.set_deletable(False)
        reseting_window.present()

        config.new("login", "password", "")

        reseting_status.info(_("Successful!"))
        asyncio.get_running_loop().call_later(3, lambda: reseting_window.destroy())
