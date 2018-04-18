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
from typing import Optional

from gi.repository import Gio, Gtk
from stlib import authenticator

from ui import config, settings, window


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = window.Main(application=self)

        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        settings_action = Gio.SimpleAction.new('settings')
        settings_action.connect("activate", self.on_settings_activate)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about")
        about_action.connect("activate", self.on_about_activate)
        self.add_action(about_action)

        return_code = asyncio.ensure_future(self.run_authenticator())

    @config.Check("authenticator")
    async def run_authenticator(self, shared_secret: Optional[config.ConfigStr] = None):
        while True:
            try:
                auth_code, epoch = authenticator.get_code(shared_secret)
            except TypeError:
                status_msg = _("The currently secret is invalid")
                self.window.status_markup(self.window.authenticator_status_label, 'red', status_msg)
            except ProcessLookupError:
                status_msg = _("Steam Client is not running")
                self.window.status_markup(self.window.authenticator_status_label, 'red', status_msg)
            else:
                status_msg = _("user") # FIXME: get user from steam_api
                self.window.status_markup(self.window.authenticator_status_label, 'green', status_msg)

                seconds = 30 - (epoch % 30)

                for past_time in range(seconds):
                    progress = int(past_time / seconds * 10)
                    self.window.authenticator_level_bar.set_max_value(seconds)
                    self.window.authenticator_level_bar.set_value(progress)
                    self.window.authenticator_code.set_text(' '.join(auth_code))

            await asyncio.sleep(3)

    def on_settings_activate(self, action, data):
        dialog = settings.SettingsDialog(parent_window=self.window)
        dialog.run()

    def on_about_activate(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()
