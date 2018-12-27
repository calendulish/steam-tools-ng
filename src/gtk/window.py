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
import logging
import os
from typing import Union, Optional, Tuple

from gi.repository import GdkPixbuf, Gio, Gtk

from . import confirmation, utils
from .. import config, i18n

_ = i18n.get_translation
log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
class Main(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Steam Tools NG")
        self.application = application
        self.session = application.session
        self.webapi_session = application.webapi_session
        self.plugin_manager = application.plugin_manager

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)

        icon = Gtk.Image()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(config.icons_dir, 'steam-tools-ng.png'), 28, 28)
        icon.set_from_pixbuf(pix)
        header_bar.pack_start(icon)

        menu = Gio.Menu()
        menu.append(_("Settings"), "app.settings")
        menu.append(_("About"), "app.about")
        menu.append(_("Exit"), "app.exit")

        menu_button = Gtk.MenuButton("☰")
        menu_button.set_relief(Gtk.ReliefStyle.NONE)
        menu_button.set_use_popover(True)
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(650, 450)
        self.set_resizable(False)

        if config.parser.getboolean("gtk", "show_close_button"):
            self.set_deletable(True)
        else:
            self.set_deletable(False)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_titlebar(header_bar)
        self.set_title('Steam Tools NG')

        main_grid = Gtk.Grid()
        main_grid.set_border_width(10)
        main_grid.set_row_spacing(10)
        self.add(main_grid)

        self.status_grid = Gtk.Grid()
        self.status_grid.set_column_homogeneous(True)
        main_grid.attach(self.status_grid, 0, 0, 4, 1)

        self.steamtrades_status = utils.Status(5, "SteamTrades (bump)")
        self.status_grid.attach(self.steamtrades_status, 0, 0, 1, 1)

        self.steamgifts_status = utils.Status(5, "SteamGifts (join)")
        self.status_grid.attach(self.steamgifts_status, 1, 0, 1, 1)

        self.steamguard_status = utils.Status(4, _('Steam Guard Code'))
        self.status_grid.attach(self.steamguard_status, 0, 1, 1, 1)

        self.cardfarming_status = utils.Status(6, _("Card Farming"))
        self.status_grid.attach(self.cardfarming_status, 1, 1, 1, 1)

        self._info_label = Gtk.Label()
        self._info_label.set_text(_("If you have confirmations, they will be shown here. (15 seconds delay)"))
        main_grid.attach(self._info_label, 0, 2, 4, 1)

        self._warning_label = Gtk.Label()
        main_grid.attach(self._warning_label, 0, 3, 4, 1)

        self.text_tree = utils.SimpleTextTree((_('mode'), _('id'), _('key'), _('give'), _('to'), _('receive')), False)
        main_grid.attach(self.text_tree, 0, 4, 4, 1)

        for index, column in enumerate(self.text_tree.view.get_columns()):
            if index in (0, 1, 2):
                column.set_visible(False)

            if index == 4:
                column.set_fixed_width(140)
            else:
                column.set_fixed_width(220)

        self.text_tree.view.set_has_tooltip(True)
        self.text_tree.view.connect('query-tooltip', self.on_query_confirmations_tooltip)

        tree_selection = self.text_tree.view.get_selection()
        tree_selection.connect("changed", self.on_tree_selection_changed)

        accept_button = Gtk.Button(_('Accept selected'))
        accept_button.connect('clicked', self.on_validate_confirmations, "allow", *tree_selection.get_selected())
        main_grid.attach(accept_button, 0, 5, 1, 1)

        cancel_button = Gtk.Button(_('Cancel selected'))
        cancel_button.connect('clicked', self.on_validate_confirmations, "cancel", *tree_selection.get_selected())
        main_grid.attach(cancel_button, 1, 5, 1, 1)

        accept_all_button = Gtk.Button(_('Accept all'))
        accept_all_button.connect('clicked', self.on_validate_confirmations, "allow", self.text_tree.store)
        main_grid.attach(accept_all_button, 2, 5, 1, 1)

        cancel_all_button = Gtk.Button(_('Cancel all'))
        cancel_all_button.connect('clicked', self.on_validate_confirmations, "cancel", self.text_tree.store)
        main_grid.attach(cancel_all_button, 3, 5, 1, 1)

        icon_bar = Gtk.Grid()
        icon_bar.set_column_spacing(5)
        main_grid.attach(icon_bar, 0, 6, 4, 1)

        self.steam_icon = Gtk.Image.new_from_file(os.path.join(config.icons_dir, 'steam_red.png'))
        self.steam_icon.set_hexpand(True)
        self.steam_icon.set_halign(Gtk.Align.END)
        icon_bar.add(self.steam_icon)

        self.steamtrades_icon = Gtk.Image.new_from_file(os.path.join(config.icons_dir, 'steamtrades_red.png'))
        icon_bar.attach_next_to(self.steamtrades_icon, self.steam_icon, Gtk.PositionType.RIGHT, 1, 1)

        self.steamgifts_icon = Gtk.Image.new_from_file(os.path.join(config.icons_dir, 'steamgifts_red.png'))
        icon_bar.attach_next_to(self.steamgifts_icon, self.steamtrades_icon, Gtk.PositionType.RIGHT, 1, 1)

        icon_bar.show_all()
        main_grid.show_all()
        self.show_all()

        asyncio.ensure_future(self.plugin_switch())

    async def plugin_switch(self) -> None:
        while self.get_realized():
            plugins_enabled = []

            for plugin_name in ["steamgifts", "steamtrades", "steamguard", "cardfarming"]:
                plugin_config = config.parser.getboolean("plugins", plugin_name)

                if plugin_config:
                    plugins_enabled.append(plugin_name)

            for widget in self.status_grid.get_children():
                self.status_grid.remove(widget)

            for index, plugin_name in enumerate(plugins_enabled):
                plugin = getattr(self, f'{plugin_name}_status')

                if index == 0:
                    if len(plugins_enabled) >= 2:
                        self.status_grid.attach(plugin, 0, 0, 1, 1)
                    else:
                        self.status_grid.attach(plugin, 0, 0, 2, 1)

                if index == 1 and len(plugins_enabled) >= 2:
                    self.status_grid.attach(plugin, 1, 0, 1, 1)

                if index == 2:
                    if len(plugins_enabled) == 3:
                        self.status_grid.attach(plugin, 0, 1, 2, 1)
                    else:
                        self.status_grid.attach(plugin, 0, 1, 1, 1)

                if index == 3 and len(plugins_enabled) == 4:
                    self.status_grid.attach(plugin, 1, 1, 1, 1)

                plugin.show()

            await asyncio.sleep(1)

    def set_login_icon(self, plugin_name: str, color: str) -> None:
        plugin_icon = getattr(self, f'{plugin_name}_icon')

        plugin_icon.set_from_file(
            os.path.join(config.icons_dir, f'{plugin_name}_{color}.png'),
        )

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

        return False

    def on_validate_confirmations(
            self,
            button: Gtk.Button,
            action: str,
            model: Gtk.TreeModel,
            iter_: Union[Gtk.TreeIter, bool, None] = False) -> None:
        finalize_dialog = confirmation.FinalizeDialog(self, self.webapi_session, action, model, iter_)
        finalize_dialog.show()

    @staticmethod
    def on_tree_selection_changed(selection: Gtk.TreeSelection) -> None:
        model, iter_ = selection.get_selected()

        if iter_:
            parent = model.iter_parent(iter_)

            if parent:
                selection.select_iter(parent)

    def set_status(
            self,
            module: str,
            display: Optional[str] = None,
            info: Optional[str] = None,
            error: Optional[str] = None,
            level: Optional[Tuple[int, int]] = None,
    ) -> None:
        status = getattr(self, f'{module}_status')

        if display:
            status.set_display(display)
        else:
            status.unset_display()

        if info:
            status.set_info(info)

        if error:
            status.set_error(error)

        if level:
            try:
                status.set_level(*level)
            except KeyError:
                status.unset_level()
        else:
            status.unset_level()

    def set_warning(self, message: str) -> None:
        self._warning_label.set_markup(utils.markup(message, color='white', background='red'))
        self._warning_label.show()

    def unset_warning(self) -> None:
        self._warning_label.hide()
