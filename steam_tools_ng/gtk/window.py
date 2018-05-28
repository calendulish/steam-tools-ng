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
import functools
import logging
from typing import Any, Dict, Optional

from gi.repository import Gio, Gtk

from . import adb, utils
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

        menu = Gio.Menu()
        menu.append(_("Settings"), "app.settings")
        menu.append(_("About"), "app.about")

        menu_button = Gtk.MenuButton("☰")
        menu_button.set_use_popover(True)
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        self.set_default_size(640, 480)
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

        steam_guard_section = utils.new_section(_('Steam Guard Code'))
        main_grid.attach(steam_guard_section.frame, 0, 0, 1, 1)

        code_label = Gtk.Label()
        code_label.set_markup('<span font_size="large" font_weight="bold">_ _ _ _</span>')
        code_label.set_hexpand(True)
        code_label.set_selectable(True)
        steam_guard_section.grid.attach(code_label, 0, 0, 1, 1)

        status_label = Gtk.Label()
        status_label.set_markup(utils.status_markup('info', _("loading...")))
        steam_guard_section.grid.attach(status_label, 0, 1, 1, 1)

        level_bar = Gtk.LevelBar()
        steam_guard_section.grid.attach(level_bar, 0, 2, 1, 1)

        show_sensitive = Gtk.CheckButton(_('Show sensitive data'))
        main_grid.attach(show_sensitive, 0, 1, 2, 1)

        sensitive_data_section = utils.new_section(_('Sensitive data'))
        main_grid.attach(sensitive_data_section.frame, 0, 2, 1, 1)

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

        show_sensitive.connect("toggled", self.on_authenticator_show_sensitive_toggled, sensitive_data_section.frame,
                               tip)

        steam_guard_section.frame.show_all()
        show_sensitive.show()
        tip.show()
        main_grid.show()

        info_label = Gtk.Label()
        info_label_text = _("Don't worry, everything is saved on-the-fly")
        info_label.set_markup(f"<span foreground='blue'>{info_label_text}</span>")
        info_label.set_justify(Gtk.Justification.CENTER)
        sensitive_data_section.grid.attach(info_label, 0, 0, 2, 1)

        sensitive_data = {
            'adb_path': utils.new_item(_("adb path:"), sensitive_data_section, Gtk.Entry, 0, 1),
            'shared_secret': utils.new_item(_("shared secret:"), sensitive_data_section, Gtk.Entry, 0, 3),
            'identity_secret': utils.new_item(_("identity secret:"), sensitive_data_section, Gtk.Entry, 0, 5),
            'account_name': utils.new_item(_("account name:"), sensitive_data_section, Gtk.Entry, 0, 7),
            'steamid': utils.new_item(_("steam id:"), sensitive_data_section, Gtk.Entry, 0, 9),
        }

        sensitive_data['adb_path'].children.connect('changed', self.on_adb_path_entry_changed)
        sensitive_data['shared_secret'].children.connect('changed', self.on_shared_secret_entry_changed)
        sensitive_data['identity_secret'].children.connect('changed', self.on_identity_secret_entry_changed)
        sensitive_data['account_name'].children.connect('changed', self.on_account_name_entry_changed)
        sensitive_data['steamid'].children.connect('changed', self.on_steam_id_entry_changed)

        adb_button = Gtk.Button(_("get sensitive data using an Android phone and Android Debug Bridge"))
        adb_button.connect('clicked', self.on_adb_clicked, sensitive_data)
        sensitive_data_section.grid.attach(adb_button, 0, 11, 2, 1)

        load_sensitive_data(sensitive_data)
        asyncio.ensure_future(self.check_authenticator_status(code_label, status_label, level_bar))

        return main_grid

    def steamtrades_tab(self):
        main_grid = Gtk.Grid()
        main_grid.set_border_width(10)
        main_grid.set_row_spacing(10)

        trade_bump_section = utils.new_section(_('Trades bump'))
        main_grid.attach(trade_bump_section.frame, 0, 0, 1, 1)

        current_trade_label = Gtk.Label()
        current_trade_label.set_hexpand(True)
        trade_bump_section.grid.attach(current_trade_label, 0, 0, 1, 1)

        status_label = Gtk.Label()
        status_label.set_markup(utils.status_markup('info', _("loading...")))
        trade_bump_section.grid.attach(status_label, 0, 1, 1, 1)

        level_bar = Gtk.LevelBar()
        trade_bump_section.grid.attach(level_bar, 0, 2, 1, 1)

        show_sensitive = Gtk.CheckButton(_('Show sensitive data'))
        main_grid.attach(show_sensitive, 0, 1, 2, 1)

        sensitive_data_section = utils.new_section(_('Sensitive data'))
        main_grid.attach(sensitive_data_section.frame, 0, 2, 1, 1)

        show_sensitive.connect("toggled", self.on_steamtrades_show_sensitive_toggled, sensitive_data_section.frame)

        trade_bump_section.frame.show_all()
        show_sensitive.show()
        main_grid.show()

        asyncio.ensure_future(self.check_steamtrades_status(current_trade_label, status_label, level_bar))

        return main_grid

    async def check_steamtrades_status(
            self,
            current_trade_label: Gtk.Label,
            status_label: Gtk.Label,
            level_bar: Gtk.LevelBar,
    ) -> None:
        while self.get_realized():
            current_trade_label.set_markup(
                f'<span font_size="large" font_weight="bold">{self.application.steamtrades_status["trade_id"]}</span>'
            )

            if self.application.steamtrades_status['running']:
                status_label.set_markup(utils.status_markup("info", self.application.steamtrades_status['message']))
            else:
                status_label.set_markup(utils.status_markup("error", self.application.steamtrades_status['message']))

            await asyncio.sleep(0.5)

    async def check_authenticator_status(
            self,
            code_label: Gtk.Label,
            status_label: Gtk.Label,
            level_bar: Gtk.LevelBar
    ) -> None:
        while self.get_realized():
            if self.application.authenticator_status['running']:
                code_label.set_markup(
                    f'<span font_size="large" font_weight="bold">{self.application.authenticator_status["code"]}</span>'
                )
                status_label.set_markup(utils.status_markup("info", "Running"))
                level_bar.set_max_value(self.application.authenticator_status['maximum'])
                level_bar.set_value(self.application.authenticator_status['progress'])
            else:
                status_label.set_markup(utils.status_markup("error", self.application.authenticator_status["message"]))

            await asyncio.sleep(0.125)

    @staticmethod
    def on_adb_path_entry_changed(entry: Gtk.Entry) -> None:
        if len(entry.get_text()) > 2:
            config.new(config.ConfigType('authenticator', 'adb_path', entry.get_text()))

    @staticmethod
    def on_shared_secret_entry_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('authenticator', 'shared_secret', entry.get_text()))

    @staticmethod
    def on_identity_secret_entry_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('authenticator', 'identity_secret', entry.get_text()))

    @staticmethod
    def on_account_name_entry_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('authenticator', 'account_name', entry.get_text()))

    @staticmethod
    def on_steam_id_entry_changed(entry: Gtk.Entry) -> None:
        config.new(config.ConfigType('authenticator', 'steamid', entry.get_text()))

    def on_adb_clicked(self, button: Gtk.Button, sensitive_data: Dict[str, utils.Item]) -> None:
        adb_dialog = adb.AdbDialog(parent_window=self)
        task = asyncio.ensure_future(adb_dialog.get_sensitive_data())
        task.add_done_callback(functools.partial(on_sensitive_data_task_done, adb_dialog, sensitive_data))
        adb_dialog.show()

    @staticmethod
    def on_authenticator_show_sensitive_toggled(button: Gtk.CheckButton, frame: Gtk.Frame, tip: Gtk.Label) -> None:
        if button.get_active():
            tip.hide()
            frame.show_all()
        else:
            tip.show()
            frame.hide()

    @staticmethod
    def on_steamtrades_show_sensitive_toggled(button: Gtk.CheckButton, frame: Gtk.Frame):
        if button.get_active():
            frame.show_all()
        else:
            frame.hide()


@config.Check("authenticator")
def load_sensitive_data(
        sensitive_data: Dict[str, utils.Item],
        adb_path: Optional[config.ConfigStr] = None,
        shared_secret: Optional[config.ConfigStr] = None,
        identity_secret: Optional[config.ConfigStr] = None,
        account_name: Optional[config.ConfigStr] = None,
        steamid: Optional[config.ConfigStr] = None
) -> None:
    for name, data in sensitive_data.items():
        try:
            data.children.set_text(locals()[name])
        except TypeError:
            pass  # Not found on config file


def on_sensitive_data_task_done(adb_dialog: Gtk.Dialog, sensitive_data: Dict[str, utils.Item], future: Any) -> None:
    if future.exception():
        exception = future.exception()
        log.debug(repr(exception))
    else:
        load_sensitive_data(sensitive_data, **future.result())
        adb_dialog.destroy()
