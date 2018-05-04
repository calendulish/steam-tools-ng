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
from typing import Optional, Tuple

from gi.repository import Gio, Gtk

from . import adb, config, i18n

_ = i18n.get_translation


class Main(Gtk.ApplicationWindow):
    def __init__(self, application):
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

        self.authenticator_status_label = Gtk.Label()
        self.authenticator_level_bar = Gtk.LevelBar()
        self.authenticator_code = Gtk.Label()
        self.authenticator_code.set_selectable(True)

        self.adb_path_label, self.adb_path_entry = self._new_tab_item(_("adb_path:"))
        self.adb_path_entry.connect('changed', self.on_adb_path_entry_changed)

        self.shared_secret_label, self.shared_secret_entry = self._new_tab_item(_("shared secret:*"))
        self.shared_secret_entry.connect('changed', self.on_shared_secret_entry_changed)

        self.identity_secret_label, self.identity_secret_entry = self._new_tab_item(_("identity secret:"))
        self.identity_secret_entry.connect('changed', self.on_identity_secret_entry_changed)

        self.account_name_label, self.account_name_entry = self._new_tab_item(_("account name:"))
        self.account_name_entry.connect('changed', self.on_account_name_entry_changed)

        self.steam_id_label, self.steam_id_entry = self._new_tab_item(_("steam id:"))
        self.steam_id_entry.connect('changed', self.on_steam_id_entry_changed)

        self.populate_sensitive_data()

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_duration(500)
        stack.add_titled(self.authenticator_tab(), "authenticator", _("Authenticator"))
        stack.show()

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        sidebar.show()

        main_grid.attach(sidebar, 0, 0, 1, 1)
        main_grid.attach_next_to(stack, sidebar, Gtk.PositionType.RIGHT, 1, 1)

    @staticmethod
    def status_markup(widget, foreground, text):
        widget.set_markup(f"<span foreground='{foreground}' font_size='small'>{text}</span>")

    @staticmethod
    def _new_tab_item(text: str) -> Tuple[Gtk.Widget, Gtk.Widget]:
        item_label = Gtk.Label(text)
        item_label.set_halign(Gtk.Align.START)

        item = Gtk.Entry()
        item.set_hexpand(True)

        return item_label, item

    def authenticator_tab(self):
        main_grid = Gtk.Grid()
        main_grid.set_row_spacing(10)
        main_grid.set_column_spacing(10)
        main_grid.set_border_width(20)

        frame = Gtk.Frame(label=_('Steam Guard Code'))
        frame.set_label_align(0.03, 0.5)
        main_grid.attach(frame, 0, 0, 2, 1)

        frame_grid = Gtk.Grid()
        frame_grid.set_row_spacing(5)
        frame_grid.set_border_width(10)
        frame.add(frame_grid)

        self.authenticator_code.set_markup('<span font_size="large">_ _ _ _</span>')
        self.authenticator_code.set_hexpand(True)
        frame_grid.attach(self.authenticator_code, 0, 0, 1, 1)

        status_msg = _("loading...")
        self.status_markup(self.authenticator_status_label, 'blue', status_msg)
        frame_grid.attach(self.authenticator_status_label, 0, 1, 1, 1)
        frame_grid.attach(self.authenticator_level_bar, 0, 2, 1, 1)

        sensitive_data_grid = Gtk.Grid()
        sensitive_data_grid.set_row_spacing(10)
        sensitive_data_grid.set_column_spacing(10)

        show_sensitive = Gtk.CheckButton(_('Show sensitive data'))
        main_grid.attach(show_sensitive, 0, 3, 2, 1)
        main_grid.attach(sensitive_data_grid, 0, 4, 2, 1)

        tip = Gtk.Label(_(
            "A code will be requested every time you try to log in on Steam.\n\n"
            "Tip: If you are not on a shared computer, select 'Remember password'\n"
            "when you log in to Steam Client so you do not have to enter the password and\n"
            "the authenticator code."
        ))

        tip.set_vexpand(True)
        tip.set_justify(Gtk.Justification.CENTER)
        tip.set_valign(Gtk.Align.END)
        main_grid.attach(tip, 0, 4, 2, 1)

        show_sensitive.connect("toggled", self.on_show_sensitive_toggled, sensitive_data_grid, tip)

        main_grid.show_all()

        info_label = Gtk.Label()
        info_label_text = _("Don't worry, everything is saved on-the-fly")
        info_label.set_markup(f"<span foreground='blue'>{info_label_text}</span>")
        info_label.set_justify(Gtk.Justification.CENTER)
        sensitive_data_grid.attach(info_label, 0, 0, 2, 1)

        sensitive_data_grid.attach(self.adb_path_label, 0, 1, 1, 1)
        sensitive_data_grid.attach_next_to(self.adb_path_entry,
                                           self.adb_path_label,
                                           Gtk.PositionType.RIGHT,
                                           1, 1)

        sensitive_data_grid.attach(self.shared_secret_label, 0, 3, 1, 1)
        sensitive_data_grid.attach_next_to(self.shared_secret_entry,
                                           self.shared_secret_label,
                                           Gtk.PositionType.RIGHT,
                                           1, 1)

        sensitive_data_grid.attach(self.identity_secret_label, 0, 5, 1, 1)
        sensitive_data_grid.attach_next_to(self.identity_secret_entry,
                                           self.identity_secret_label,
                                           Gtk.PositionType.RIGHT,
                                           1, 1)

        sensitive_data_grid.attach(self.account_name_label, 0, 7, 1, 1)
        sensitive_data_grid.attach_next_to(self.account_name_entry,
                                           self.account_name_label,
                                           Gtk.PositionType.RIGHT,
                                           1, 1)

        sensitive_data_grid.attach(self.steam_id_label, 0, 9, 1, 1)
        sensitive_data_grid.attach_next_to(self.steam_id_entry,
                                           self.steam_id_label,
                                           Gtk.PositionType.RIGHT,
                                           1, 1)

        adb_button = Gtk.Button(_("get sensitive data using an Android phone and Android Debug Bridge"))
        adb_button.connect('clicked', self.on_adb_clicked)
        sensitive_data_grid.attach(adb_button, 0, 11, 2, 1)

        return main_grid

    @staticmethod
    def on_adb_path_entry_changed(entry):
        if len(entry.get_text()) > 2:
            config.new(config.Config('authenticator', 'adb_path', entry.get_text()))

    @staticmethod
    def on_shared_secret_entry_changed(entry):
        config.new(config.Config('authenticator', 'shared_secret', entry.get_text()))

    @staticmethod
    def on_identity_secret_entry_changed(entry):
        config.new(config.Config('authenticator', 'identity_secret', entry.get_text()))

    @staticmethod
    def on_account_name_entry_changed(entry):
        config.new(config.Config('authenticator', 'account_name', entry.get_text()))

    @staticmethod
    def on_steam_id_entry_changed(entry):
        config.new(config.Config('authenticator', 'steamid', entry.get_text()))

    def on_adb_clicked(self, button):
        adb_dialog = adb.AdbDialog(parent_window=self)
        adb_dialog.show()

    @staticmethod
    def on_show_sensitive_toggled(button, grid, tip):
        if button.get_active():
            tip.hide()
            grid.show_all()
        else:
            tip.show()
            grid.hide()

    @config.Check("authenticator")
    def populate_sensitive_data(
            self,
            adb_path: Optional[config.ConfigStr] = None,
            shared_secret: Optional[config.ConfigStr] = None,
            identity_secret: Optional[config.ConfigStr] = None,
            account_name: Optional[config.ConfigStr] = None,
            steamid: Optional[config.ConfigStr] = None
    ) -> None:
        try:
            self.adb_path_entry.set_text(adb_path)
            self.shared_secret_entry.set_text(shared_secret)
            self.identity_secret_entry.set_text(identity_secret)
            self.account_name_entry.set_text(account_name)
            self.steam_id_entry.set_text(steamid)
        except TypeError:
            pass
