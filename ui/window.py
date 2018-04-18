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

        main_box = Gtk.Box()
        self.add(main_box)
        self.show_all()

        self.authenticator_status_label = Gtk.Label()
        self.authenticator_level_bar = Gtk.LevelBar()
        self.authenticator_code = Gtk.Label()

        stack = Gtk.Stack()
        stack.set_hexpand(True)
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_duration(500)
        stack.add_titled(self.authenticator_tab(), "authenticator", _("Authenticator"))
        stack.show()

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        sidebar.show()

        main_box.pack_start(sidebar, False, False, 0)
        main_box.pack_end(stack, False, True, 0)

    @staticmethod
    def status_markup(widget, foreground, text):
        widget.set_markup(f"<span foreground='{foreground}' font_size='small'>{text}</span>")

    def authenticator_tab(self):
        box = Gtk.Box()
        box.set_border_width(20)
        box.set_spacing(10)
        box.set_orientation(Gtk.Orientation.VERTICAL)

        frame = Gtk.Frame(label=_('Steam Guard Code'))
        frame.set_label_align(0.03, 0.5)
        box.pack_start(frame, False, False, 0)

        frame_box = Gtk.Box()
        frame_box.set_border_width(5)
        frame_box.set_spacing(5)
        frame_box.set_orientation(Gtk.Orientation.VERTICAL)
        frame.add(frame_box)

        self.authenticator_code.set_text('_ _ _ _')
        frame_box.pack_start(self.authenticator_code, False, False, 0)

        status_msg = _("loading...")
        self.status_markup(self.authenticator_status_label, 'blue', status_msg)
        frame_box.pack_start(self.authenticator_status_label, False, False, 0)
        frame_box.pack_start(self.authenticator_level_bar, False, False, 0)

        tip = Gtk.Label(''.join(
            (
                _("A code will be requested every time you try to log in on Steam.\n\n"),
                _("Tip: If you are not on a shared computer, select 'Remember password'\n"),
                _("when you log in to Steam Client so you do not have to enter the password and\n"),
                _("the authenticator code."),
            )
        ))

        tip.set_justify(Gtk.Justification.CENTER)
        box.pack_end(tip, False, False, 0)

        sensitive_data_box = Gtk.Box()
        sensitive_data_box.set_orientation(Gtk.Orientation.VERTICAL)

        show_sensitive = Gtk.CheckButton(_('Show sensitive data'))
        show_sensitive.connect("toggled", self.on_show_sensitive_toggled, sensitive_data_box)
        box.pack_start(show_sensitive, False, False, 0)
        box.pack_start(sensitive_data_box, False, False, 0)

        box.show_all()

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        sensitive_data_box.pack_start(grid, False, False, 0)

        adb_path_label = Gtk.Label(_("adb path:"))
        grid.attach(adb_path_label, 0, 0, 1, 1)

        adb_path = Gtk.Entry()
        adb_path.set_hexpand(True)
        adb_path.set_sensitive(False)
        grid.attach_next_to(adb_path, adb_path_label, Gtk.PositionType.RIGHT, 1, 1)

        shared_secret_label = Gtk.Label(_("shared secret:"))
        grid.attach(shared_secret_label, 0, 1, 1, 1)

        shared_secret = Gtk.Entry()
        shared_secret.set_hexpand(True)
        shared_secret.set_sensitive(False)
        grid.attach_next_to(shared_secret, shared_secret_label, Gtk.PositionType.RIGHT, 1, 1)

        return box

    @staticmethod
    def on_show_sensitive_toggled(button, sensitive_data_box):
        if button.get_active():
            sensitive_data_box.show_all()
        else:
            sensitive_data_box.hide()
