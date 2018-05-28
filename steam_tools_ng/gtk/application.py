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
from typing import Any, Optional

from gi.repository import Gio, Gtk
from stlib import authenticator
import binascii

from . import about, settings, window
from .. import config, i18n

_ = i18n.get_translation


# noinspection PyUnusedLocal
class Application(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="click.lara.SteamToolsNG",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.window: Gtk.ApplicationWindow = None
        self.authenticator_status = {'running': False, 'message': "Authenticator is not running"}

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        settings_action = Gio.SimpleAction.new('settings')
        settings_action.connect("activate", self.on_settings_activate)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about")
        about_action.connect("activate", self.on_about_activate)
        self.add_action(about_action)

    def do_activate(self) -> None:
        if not self.window:
            self.window = window.Main(application=self)

        self.window.present()

        asyncio.ensure_future(self.run_authenticator())

    async def run_authenticator(self) -> None:
        while self.window.get_realized():
            shared_secret = config.config_parser.get("authenticator", "shared_secret", fallback='')

            try:
                if not shared_secret:
                    raise TypeError

                auth_code, epoch = authenticator.get_code(shared_secret)
            except (TypeError, binascii.Error):
                self.authenticator_status = {'running': False, 'message': _("The currently secret is invalid")}
            except ProcessLookupError:
                self.authenticator_status = {'running': False, 'message': _("Steam Client is not running")}
            else:
                self.authenticator_status = {'running': False, 'message': _("Loading...")}

                seconds = 30 - (epoch % 30)

                for past_time in range(seconds*9):
                    self.authenticator_status = {
                        'running': True,
                        'maximum': seconds*8,
                        'progress': past_time,
                        'code': ''.join(auth_code)
                    }

                    await asyncio.sleep(0.125)

    def on_settings_activate(self, action: Any, data: Any) -> None:
        settings_dialog = settings.SettingsDialog(parent_window=self.window)
        settings_dialog.run()

    def on_about_activate(self, action: Any, data: Any) -> None:
        dialog = about.AboutDialog(parent_window=self.window)
        dialog.run()
