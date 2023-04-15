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
from gi.repository import Gio, Gtk, Gdk
from subprocess import call
from typing import Union, Optional, Tuple, Any, List

import stlib
from stlib import login, universe, plugins
from . import confirmation, utils, coupon
from .authenticator import NewAuthenticatorDialog
from .login import LoginDialog
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

        main_tabs = Gtk.Stack()
        main_tabs.set_hhomogeneous(True)
        main_grid.attach(main_tabs, 1, 2, 1, 1)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(main_tabs)
        main_grid.attach(switcher, 1, 1, 1, 1)

        steamguard_section = utils.Section("steamguard")
        steamguard_section.stackup_section("SteamGuard", main_tabs)

        cardfarming_section = utils.Section("cardfarming")
        cardfarming_section.stackup_section("CardFarming", main_tabs)

        steamgifts_section = utils.Section("steamgifts")
        steamgifts_section.stackup_section("SteamGifts", main_tabs)

        steamtrades_section = utils.Section("steamtrades")
        steamtrades_section.stackup_section("SteamTrades", main_tabs)

        coupons_section = utils.Section("coupons")
        coupons_section.stackup_section(_("Coupons"), main_tabs)

        # grid managed by plugin switch
        self.steamguard_status = utils.Status(4)
        self.cardfarming_status = utils.Status(6)
        self.steamgifts_status = utils.Status(5)
        self.steamtrades_status = utils.Status(5)

        steamguard_section.grid.attach(self.steamguard_status, 0, 0, 2, 1)

        steamguard_stack = Gtk.Stack()
        steamguard_stack.set_vexpand(True)
        steamguard_section.grid.attach(steamguard_stack, 1, 1, 1, 1)

        steamguard_sidebar = Gtk.StackSidebar()
        steamguard_sidebar.set_stack(steamguard_stack)
        steamguard_sidebar.set_size_request(150, -1)
        steamguard_section.grid.attach(steamguard_sidebar, 0, 1, 1, 1)

        self.confirmations_grid = Gtk.Grid()
        self.confirmations_grid.set_row_spacing(10)
        steamguard_stack.add_titled(self.confirmations_grid, "confirmations", _("Confirmations"))

        self.confirmations_tree = utils.SimpleTextTree(
            _('confid'), _('creatorid'), _('key'), _('give'), _('to'), _('receive'),
            overlay_scrolling=False,
        )

        self.confirmations_grid.attach(self.confirmations_tree, 0, 0, 4, 1)

        for index, column in enumerate(self.confirmations_tree.view.get_columns()):
            if index in (0, 1, 2):
                column.set_visible(False)

            if index == 4:
                column.set_fixed_width(100)
            else:
                column.set_fixed_width(200)

        self.confirmations_tree.view.set_has_tooltip(True)
        self.confirmations_tree.view.connect('query-tooltip', self.on_query_confirmations_tooltip)

        confirmation_tree_selection = self.confirmations_tree.view.get_selection()
        confirmation_tree_selection.connect("changed", self.on_tree_selection_changed)

        accept_button = Gtk.Button()
        accept_button.set_margin_start(3)
        accept_button.set_margin_end(3)
        accept_button.set_label(_('Accept'))
        accept_button.connect('clicked', self.on_validate_confirmations, "allow", confirmation_tree_selection)
        self.confirmations_grid.attach(accept_button, 0, 1, 1, 1)

        cancel_button = Gtk.Button()
        cancel_button.set_margin_start(3)
        cancel_button.set_margin_end(3)
        cancel_button.set_label(_('Cancel'))
        cancel_button.connect('clicked', self.on_validate_confirmations, "cancel", confirmation_tree_selection)
        self.confirmations_grid.attach(cancel_button, 1, 1, 1, 1)

        accept_all_button = Gtk.Button()
        accept_all_button.set_margin_start(3)
        accept_all_button.set_margin_end(3)
        accept_all_button.set_label(_('Accept All'))
        accept_all_button.connect('clicked', self.on_validate_confirmations, "allow", self.confirmations_tree.store)
        self.confirmations_grid.attach(accept_all_button, 2, 1, 1, 1)

        cancel_all_button = Gtk.Button()
        cancel_all_button.set_margin_start(3)
        cancel_all_button.set_margin_end(3)
        cancel_all_button.set_label(_('Cancel All'))
        cancel_all_button.connect('clicked', self.on_validate_confirmations, "cancel", self.confirmations_tree.store)
        self.confirmations_grid.attach(cancel_all_button, 3, 1, 1, 1)

        steamguard_settings = utils.Section("steamguard")
        steamguard_settings.stackup_section(_("Settings"), steamguard_stack)
        steamguard_settings.grid.set_halign(Gtk.Align.CENTER)

        steamguard_enable = steamguard_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 0)
        steamguard_enable.set_margin_top(40)
        steamguard_enable.label.set_margin_top(40)
        steamguard_enable.set_halign(Gtk.Align.END)
        steamguard_enable.connect("state-set", utils.on_setting_state_set)

        if not config.parser.get("login", "shared_secret"):
            self.steamguard_status.set_sensitive(False)
            steamguard_enable.set_active(False)
            _steamguard_disabled = Gtk.Label()
            _steamguard_disabled.set_justify(Gtk.Justification.CENTER)
            _steamguard_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "steamguard module has been disabled because you have\n"
                "logged in but no shared secret is found. To enable it again,\n"
                "go to Advanced and add a valid shared secret\n"
                "or use STNG as your Steam Authenticator\n"
            )

            _steamguard_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            steamguard_section.grid.attach(_steamguard_disabled, 0, 0, 2, 1)

        confirmations_enable = steamguard_settings.new_item(
            "enable_confirmations", _("Enable Confirmations:"),
            Gtk.Switch,
            0, 1,
        )

        confirmations_enable.set_halign(Gtk.Align.END)
        confirmations_enable.connect("state-set", utils.on_setting_state_set)

        if not config.parser.get("login", "identity_secret"):
            self.confirmations_grid.set_sensitive(False)
            confirmations_enable.set_active(False)
            _confirmations_disabled = Gtk.Label()
            _confirmations_disabled.set_justify(Gtk.Justification.CENTER)
            _confirmations_disabled.set_halign(Gtk.Align.CENTER)

            _message = _(
                "confirmations module has been disabled because you have\n"
                "logged in but no identity secret is found. To enable it again,\n"
                "go to login -> advanced and add a valid identity secret\n"
                "or use STNG as your Steam Authenticator\n"
            )

            _confirmations_disabled.set_markup(utils.markup(_message, color="hotpink", background="black"))
            self.confirmations_grid.attach(_confirmations_disabled, 0, 0, 4, 1)

        login_button = Gtk.Button()
        login_button.set_margin_top(40)
        login_button.set_label(_("Login with another account"))
        login_button.set_name("login_button")
        login_button.connect('clicked', self.on_login_button_clicked)
        steamguard_settings.grid.attach(login_button, 0, 2, 2, 1)

        new_authenticator_button = Gtk.Button()
        new_authenticator_button.set_label(_("Use STNG as your Steam Authenticator"))
        new_authenticator_button.set_name("new_authenticator_button")
        new_authenticator_button.connect("clicked", self.on_new_authenticator_clicked)
        steamguard_settings.grid.attach(new_authenticator_button, 0, 3, 2, 1)

        reset_password_button = Gtk.Button()
        reset_password_button.set_label(_("Remove Saved Password"))
        reset_password_button.set_name("reset_password_button")
        reset_password_button.connect("clicked", self.on_reset_password_clicked)
        steamguard_settings.grid.attach(reset_password_button, 0, 4, 2, 1)

        steamguard_advanced = utils.Section("login")
        steamguard_advanced.stackup_section(_("Advanced"), steamguard_stack, scroll=True)

        warning_label = Gtk.Label()
        warning_label.set_markup(utils.markup(
            _("Warning: Don't mess up these settings unless you know what you are doing!"),
            color='darkred' if self.theme == 'light' else 'red',
        ))
        steamguard_advanced.grid.attach(warning_label, 0, 0, 2, 1)

        shared_secret = steamguard_advanced.new_item('shared_secret', _("Shared Secret:"), Gtk.Entry, 0, 1)
        shared_secret.connect('changed', utils.on_setting_changed)

        token_item = steamguard_advanced.new_item("token", _("Token:"), Gtk.Entry, 0, 2)
        token_item.connect("changed", utils.on_setting_changed)

        token_secure_item = steamguard_advanced.new_item("token_secure", _("Token Secure:"), Gtk.Entry, 0, 3)
        token_secure_item.connect("changed", utils.on_setting_changed)

        identity_secret = steamguard_advanced.new_item('identity_secret', _("Identity Secret:"), Gtk.Entry, 0, 4)
        identity_secret.connect('changed', utils.on_setting_changed)

        deviceid = steamguard_advanced.new_item('deviceid', _("Device ID:"), Gtk.Entry, 0, 5)
        deviceid.connect('changed', utils.on_setting_changed)

        steamid_item = steamguard_advanced.new_item("steamid", _("Steam ID:"), Gtk.Entry, 0, 6)
        steamid_item.set_input_purpose(Gtk.InputPurpose.DIGITS)
        steamid_item.connect("changed", utils.on_digit_only_setting_changed)

        account_name = steamguard_advanced.new_item('account_name', _("Username:"), Gtk.Entry, 0, 7)
        account_name.connect('changed', utils.on_setting_changed)

        reset_button = utils.AsyncButton()
        reset_button.set_label(_("Reset Everything (USE WITH CAUTION!!!)"))
        reset_button.set_name("reset_button")
        reset_button.connect("clicked", self.on_reset_clicked)
        steamguard_advanced.grid.attach(reset_button, 0, 8, 2, 1)

        cardfarming_section.grid.attach(self.cardfarming_status, 0, 0, 2, 1)

        cardfarming_stack = Gtk.Stack()
        cardfarming_stack.set_vexpand(True)
        cardfarming_section.grid.attach(cardfarming_stack, 1, 1, 1, 1)

        cardfarming_sidebar = Gtk.StackSidebar()
        cardfarming_sidebar.set_stack(cardfarming_stack)
        cardfarming_sidebar.set_size_request(150, -1)
        cardfarming_section.grid.attach(cardfarming_sidebar, 0, 1, 1, 1)

        cardfarming_settings = utils.Section("cardfarming")
        cardfarming_settings.stackup_section(_("Settings"), cardfarming_stack, scroll=True)

        cardfarming_enable = cardfarming_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 1)
        cardfarming_enable.set_halign(Gtk.Align.END)
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
        cardfarming_invisible.set_halign(Gtk.Align.END)
        cardfarming_invisible.connect("state-set", utils.on_setting_state_set)

        reverse_sorting = cardfarming_settings.new_item("reverse_sorting", _("Reverse Sorting:"), Gtk.Switch, 0, 7)
        reverse_sorting.set_halign(Gtk.Align.END)
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

        # TODO: Maintain plugin switch?
        steamgifts_section.grid.attach(self.steamgifts_status, 0, 0, 2, 1)

        steamgifts_stack = Gtk.Stack()
        steamgifts_stack.set_vexpand(True)
        steamgifts_section.grid.attach(steamgifts_stack, 1, 1, 1, 1)

        steamgifts_sidebar = Gtk.StackSidebar()
        steamgifts_sidebar.set_stack(steamgifts_stack)
        steamgifts_sidebar.set_size_request(150, -1)
        steamgifts_section.grid.attach(steamgifts_sidebar, 0, 1, 1, 1)

        steamgifts_settings = utils.Section("steamgifts")
        steamgifts_settings.stackup_section(_("Settings"), steamgifts_stack)

        steamgifts_enable = steamgifts_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 0)
        steamgifts_enable.set_halign(Gtk.Align.END)
        steamgifts_enable.connect('state-set', utils.on_setting_state_set)

        developer_giveaways = steamgifts_settings.new_item(
            "developer_giveaways", _("Developer Giveaways"),
            Gtk.Switch,
            0, 1,
        )
        developer_giveaways.set_halign(Gtk.Align.END)
        developer_giveaways.connect("state-set", utils.on_setting_state_set)

        steamgifts_mode = steamgifts_settings.new_item(
            "mode", _("Mode:"),
            Gtk.ComboBoxText,
            0, 2,
            items=config.steamgifts_modes,
        )
        steamgifts_mode.connect("changed", utils.on_combo_setting_changed, config.steamgifts_modes)

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
            strategy_section.grid.attach(label, 0, 0, 1, 1)

            enable = strategy_section.new_item("enable", None, Gtk.Switch, 2, 0)
            enable.set_halign(Gtk.Align.END)
            enable.connect("state-set", utils.on_setting_state_set)

            minimum_label = Gtk.Label()
            minimum_label.set_text(_("Minimum"))
            strategy_section.grid.attach(minimum_label, 1, 1, 1, 1)

            maximum_label = Gtk.Label()
            maximum_label.set_text(_("Maximum"))
            strategy_section.grid.attach(maximum_label, 2, 1, 1, 1)

            for tree_level, item in enumerate(["points", "level", "copies", "metascore", "entries"]):
                label = Gtk.Label()
                label.set_text(_(item))
                strategy_section.grid.attach(label, 0, tree_level + 2, 1, 1)

                minimum = strategy_section.new_item(f"minimum_{item}", None, Gtk.Entry, 1, tree_level + 2)
                minimum.connect("changed", utils.on_digit_only_setting_changed)

                maximum = strategy_section.new_item(f"maximum_{item}", None, Gtk.Entry, 2, tree_level + 2)
                maximum.connect("changed", utils.on_digit_only_setting_changed)

            restrict_type = strategy_section.new_item(
                "restrict_type",
                _("Restrict Type:"),
                Gtk.ComboBoxText,
                0, 7,
                items=config.giveaway_types,
            )
            restrict_type.connect("changed", utils.on_combo_setting_changed, config.giveaway_types)

            sort_type = strategy_section.new_item(
                "sort_type",
                _("Sort Type:"),
                Gtk.ComboBoxText,
                0, 8,
                items=config.giveaway_sort_types,
            )
            sort_type.connect("changed", utils.on_combo_setting_changed, config.giveaway_sort_types)

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
            steamgifts_section.grid.attach(_steamgifts_disabled, 0, 0, 2, 2)

        steamtrades_section.grid.attach(self.steamtrades_status, 0, 0, 2, 1)

        steamtrades_stack = Gtk.Stack()
        steamtrades_stack.set_vexpand(True)
        steamtrades_section.grid.attach(steamtrades_stack, 1, 1, 1, 1)

        steamtrades_sidebar = Gtk.StackSidebar()
        steamtrades_sidebar.set_stack(steamtrades_stack)
        steamtrades_sidebar.set_size_request(150, -1)
        steamtrades_section.grid.attach(steamtrades_sidebar, 0, 1, 1, 1)

        steamtrades_settings = utils.Section("steamtrades")
        steamtrades_settings.stackup_section(_("Settings"), steamtrades_stack)

        steamtrades_enable = steamtrades_settings.new_item("enable", _("Enable:"), Gtk.Switch, 0, 1)
        steamtrades_enable.label.set_margin_top(40)
        steamtrades_enable.set_margin_top(40)
        steamtrades_enable.set_halign(Gtk.Align.END)
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
            steamtrades_settings.grid.attach(_steamtrades_disabled, 0, 1, 2, 2)

        self.coupon_warning = Gtk.Label()
        self.coupon_warning.set_markup(utils.markup(
            _("Warning: It's a heavy uncached operation. Fetch only once a day or you will be blocked."),
            color='darkred' if self.theme == 'light' else 'red',
        ))
        self.coupon_warning.set_margin_top(37)
        self.coupon_warning.set_margin_bottom(37)
        coupons_section.grid.attach(self.coupon_warning, 0, 0, 2, 1)

        coupons_stack = Gtk.Stack()
        coupons_stack.set_vexpand(True)
        coupons_section.grid.attach(coupons_stack, 1, 1, 1, 1)

        coupons_sidebar = Gtk.StackSidebar()
        coupons_sidebar.set_stack(coupons_stack)
        coupons_sidebar.set_size_request(150, -1)
        coupons_section.grid.attach(coupons_sidebar, 0, 1, 1, 1)

        self.coupons_grid = Gtk.Grid()
        self.coupons_grid.set_row_spacing(10)
        coupons_stack.add_titled(self.coupons_grid, "coupons_list", _("Coupon List"))

        self.coupons_tree = utils.SimpleTextTree(
            _('price'), _('name'), 'link', 'botid', 'token', 'assetid',
            overlay_scrolling=False,
            model=Gtk.ListStore,
        )

        self.coupons_tree.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.coupons_tree.store.set_sort_func(0, self.coupon_sorting)
        self.coupons_grid.attach(self.coupons_tree, 0, 0, 4, 2)

        for index, column in enumerate(self.coupons_tree.view.get_columns()):
            if index in (2, 3, 4, 5):
                column.set_visible(False)

        self.coupons_tree.view.connect('row-activated', self.on_coupon_double_clicked)

        coupon_tree_selection = self.coupons_tree.view.get_selection()
        coupon_tree_selection.connect("changed", self.on_tree_selection_changed)

        self.coupon_progress = Gtk.LevelBar()
        self.coupons_grid.attach(self.coupon_progress, 0, 3, 4, 1)

        fetch_coupons_button = Gtk.Button()
        fetch_coupons_button.set_margin_start(3)
        fetch_coupons_button.set_margin_end(3)
        fetch_coupons_button.set_label(_('Fetch'))
        fetch_coupons_button.connect('clicked', self.on_fetch_coupons)
        self.coupons_grid.attach(fetch_coupons_button, 0, 4, 1, 1)

        self.fetch_coupon_event = asyncio.Event()

        stop_fetching_coupons_button = Gtk.Button()
        stop_fetching_coupons_button.set_margin_start(3)
        stop_fetching_coupons_button.set_margin_end(3)
        stop_fetching_coupons_button.set_label(_('Stop fetching'))
        stop_fetching_coupons_button.connect('clicked', self.on_stop_fetching_coupons)
        self.coupons_grid.attach(stop_fetching_coupons_button, 1, 4, 1, 1)

        get_coupon_button = Gtk.Button()
        get_coupon_button.set_margin_start(3)
        get_coupon_button.set_margin_end(3)
        get_coupon_button.set_label(_('Get selected'))
        get_coupon_button.connect('clicked', self.on_coupon_action, coupon_tree_selection)
        self.coupons_grid.attach(get_coupon_button, 2, 4, 1, 1)

        give_coupon_button = Gtk.Button()
        give_coupon_button.set_margin_start(3)
        give_coupon_button.set_margin_end(3)
        give_coupon_button.set_label(_('Send'))
        give_coupon_button.connect('clicked', self.on_coupon_action)
        self.coupons_grid.attach(give_coupon_button, 3, 4, 1, 1)

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
            Gtk.ComboBoxText,
            0, 6,
            items=config.coupon_discounts,
        )
        coupon_discount.connect("changed", utils.on_combo_setting_changed, config.coupon_discounts)

        self.statusbar = utils.StatusBar()
        main_grid.attach(self.statusbar, 1, 3, 1, 1)

        self.connect("destroy", self.application.on_exit_activate)
        self.connect("close-request", self.application.on_exit_activate)

        self.loop = asyncio.get_event_loop()

        plugin_status_task = self.loop.create_task(self.plugin_status())
        plugin_status_task.add_done_callback(utils.safe_task_callback)

        user_info_task = self.loop.create_task(self.user_info())
        user_info_task.add_done_callback(utils.safe_task_callback)

    @property
    def theme(self) -> str:
        return config.parser.get('general', 'theme')

    async def user_info(self) -> None:
        while self.get_realized():
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
                        def disabled_callback(status_) -> None:
                            status_.set_status(_("Disabled"))
                            status_.set_info("")

                        self.loop.call_later(3, disabled_callback, status)

            await asyncio.sleep(3)

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
        self.coupon_progress.set_value(0)
        self.coupon_progress.set_max_value(0)

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

    async def on_reset_clicked(self, button: Gtk.Button) -> None:
        login_dialog = LoginDialog(self, self.application)
        login_dialog.status.info(_("Reseting... Please wait!"))
        login_dialog.set_deletable(False)
        login_dialog.user_details_section.hide()
        login_dialog.advanced_login.hide()
        login_dialog.show()
        await asyncio.sleep(3)

        config.config_file.unlink(missing_ok=True)

        config.parser.clear()
        config.init()
        self.destroy()

    def on_login_button_clicked(self, button: Gtk.Button) -> None:
        login_dialog = LoginDialog(self, self.application)
        login_dialog.shared_secret_item.set_text('')
        login_dialog.identity_secret_item.set_text('')
        login_dialog.show()

    def on_new_authenticator_clicked(self, button: Gtk.Button) -> None:
        new_authenticator_dialog = NewAuthenticatorDialog(self, self.application)
        new_authenticator_dialog.show()

    def on_reset_password_clicked(self, button: Gtk.Button) -> None:
        login_dialog = LoginDialog(self, self.application)
        login_dialog.status.info(_("Removing saved password..."))
        login_dialog.user_details_section.hide()
        login_dialog.advanced_login.hide()
        login_dialog.set_deletable(False)
        login_dialog.show()

        config.new("login", "password", "")

        def reset_password_callback() -> None:
            login_dialog.destroy()
            self.destroy()

        login_dialog.status.info(_("Successful!\nExiting..."))
        self.loop.call_later(3, reset_password_callback)
