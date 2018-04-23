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
from gi.repository import Gio, Gtk


class Main(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Steam Tools NG")
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

    def authenticator_tab(self):
        main_grid = Gtk.Grid()
        main_grid.set_row_spacing(10)
        main_grid.set_border_width(20)

        frame = Gtk.Frame(label=_('Steam Guard Code'))
        frame.set_label_align(0.03, 0.5)
        main_grid.attach(frame, 0, 0, 1, 1)

        frame_grid = Gtk.Grid()
        frame_grid.set_row_spacing(5)
        frame_grid.set_border_width(10)
        frame.add(frame_grid)

        self.authenticator_code.set_text('_ _ _ _')
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
        show_sensitive.connect("toggled", self.on_show_sensitive_toggled, sensitive_data_grid)
        main_grid.attach(show_sensitive, 0, 2, 1, 1)
        main_grid.attach(sensitive_data_grid, 0, 3, 1, 1)

        tip = Gtk.Label(''.join(
            (
                _("A code will be requested every time you try to log in on Steam.\n\n"),
                _("Tip: If you are not on a shared computer, select 'Remember password'\n"),
                _("when you log in to Steam Client so you do not have to enter the password and\n"),
                _("the authenticator code."),
            )
        ))

        tip.set_vexpand(True)
        tip.set_justify(Gtk.Justification.CENTER)
        tip.set_valign(Gtk.Align.END)
        main_grid.attach(tip, 0, 4, 1, 1)

        main_grid.show_all()

        adb_path_label = Gtk.Label(_("adb path:"))
        adb_path_label.set_halign(Gtk.Align.START)
        sensitive_data_grid.attach(adb_path_label, 0, 0, 1, 1)

        adb_path = Gtk.Entry()
        adb_path.set_hexpand(True)
        adb_path.set_sensitive(False)
        sensitive_data_grid.attach_next_to(adb_path, adb_path_label, Gtk.PositionType.RIGHT, 1, 1)

        shared_secret_label = Gtk.Label(_("shared secret:"))
        shared_secret_label.set_halign(Gtk.Align.START)
        sensitive_data_grid.attach(shared_secret_label, 0, 1, 1, 1)

        shared_secret = Gtk.Entry()
        shared_secret.set_hexpand(True)
        shared_secret.set_sensitive(False)
        sensitive_data_grid.attach_next_to(shared_secret, shared_secret_label, Gtk.PositionType.RIGHT, 1, 1)

        return main_grid

    @staticmethod
    def on_show_sensitive_toggled(button, grid):
        if button.get_active():
            grid.show_all()
        else:
            grid.hide()
