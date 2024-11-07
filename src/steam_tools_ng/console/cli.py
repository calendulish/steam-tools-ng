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
import functools
import logging
import sys
from typing import Any, Callable

import aiohttp
import stlib
from steam_tools_ng import __version__
from stlib import plugins, universe, login, community, webapi, internals

from . import authenticator, utils
from . import login as cli_login
from .. import i18n, config, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


def while_running(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    async def wrapper(self: 'SteamToolsNG', *args: Any, **kwargs: Any) -> None:
        while True:
            await function(self, *args, **kwargs)

            if self.stop:
                break

    return wrapper


# noinspection PyUnusedLocal
class SteamToolsNG:
    def __init__(self, module_name: str, module_options: str) -> None:
        self.module_name = module_name
        self.stop = False
        self.custom_gameid = 0
        self.extra_gameid = None

        if (
                module_name in {'cardfarming', 'fakerun'}
                and not stlib.steamworks_available
        ):
            log.critical(_(
                "{} module has been disabled because you have "
                "a stlib built without SteamWorks support. To enable it again, "
                "reinstall stlib with SteamWorks support"
            ).format(module_name))
            sys.exit(1)

        if module_name in {'steamtrades', 'steamgifts'} and not plugins.has_plugin(module_name):
            log.critical(_(
                "{0} module has been disabled because you don't "
                "have {0} plugin installed. To enable it again, "
                "install the {0} plugin."
            ).format(module_name))
            sys.exit(1)

        try:
            if module_name == 'fakerun':
                self.stop = True

                if not module_options:
                    raise ValueError

            for index, option in enumerate(module_options):
                if option == 'oneshot':
                    self.stop = True
                    continue

                if module_name in {'cardfarming', 'fakerun'}:
                    self.custom_gameid = int(option)

                    if self.custom_gameid == 34:
                        if len(module_options) < 2:
                            raise ValueError

                        self.extra_gameid = int(module_options[index + 1])

                        break
        except ValueError:
            logging.critical("Wrong command line params!")
            sys.exit(1)

        self.api_url = config.parser.get("steam", "api_url")

    @property
    def steamid(self) -> universe.SteamId | None:
        if steamid := config.parser.getint("login", "steamid"):
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

        return None

    async def init(self) -> None:
        await core.fix_ssl()

        task = asyncio.create_task(self.async_activate())
        task.add_done_callback(utils.safe_task_callback)

        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_session = cli_login.Login(self)
        await login_session.do_login(auto)

    async def async_activate(self) -> None:
        login_session = await login.Login.new_session(0, api_url=self.api_url)
        utils.set_console(info=_("Logging on Steam. Please wait!"))
        try_count = 3

        for login_count in range(try_count):
            if await login_session.is_logged_in():
                utils.set_console(info=_("Steam login Successful"))
                config.update_steamid_from_cookies()
                break

            try:
                if login_count == 0:
                    await self.do_login(auto=True)
                else:
                    await self.do_login()
            except aiohttp.ClientError as exception:
                log.exception(str(exception))
                log.error(_("Check your connection. (server down?)"))

                if login_count == 2:
                    return
                log.error(_("Waiting 10 seconds to try again"))
                await asyncio.sleep(10)

        try:
            release_data = await login_session.request_json(
                "https://api.github.com/repos/calendulish/steam-tools-ng/releases/latest",
            )
            latest_version = release_data['tag_name'][1:]

            if latest_version > __version__:
                log.warning(_("A new version is available [{}]."))
                log.warning(_("It's highly recommended to update."))
                log.warning('https://github.com/calendulish/steam-tools-ng/releases')
        except aiohttp.ClientError as error:
            log.exception(str(error))
            # bypass

        community_session = await community.Community.new_session(0, api_url=self.api_url)

        try:
            api_key = await community_session.get_api_key()
            log.debug(_('SteamAPI key found: %s'), api_key)

            if api_key[1] != 'Steam Tools NG':
                raise AttributeError
        except AttributeError:
            log.warning(_('Updating your SteamAPI dev key'))
            await asyncio.sleep(3)
            await community_session.revoke_api_key()
            await asyncio.sleep(3)
            api_key = await community_session.register_api_key('Steam Tools NG')

            if not api_key:
                raise ValueError(_('Something wrong with your SteamAPI dev key'))
        except PermissionError:
            log.error(_("Limited account! Using dummy API key"))
            api_key = (0, 'Steam Tools NG')

        await webapi.SteamWebAPI.new_session(0, api_key=api_key[0], api_url=self.api_url)
        await internals.Internals.new_session(0)

        if self.module_name in ['steamtrades', 'steamgifts']:
            plugin = plugins.get_plugin(self.module_name)
            await plugin.Main.new_session(0)

        log.debug(_("Initializing module %s"), self.module_name)
        module = getattr(self, f"run_{self.module_name}")
        await module()

    async def run_add_authenticator(self) -> None:
        authenticator_manage = authenticator.ManageAuthenticator(self)
        await authenticator_manage.add_authenticator()

    async def run_remove_authenticator(self) -> None:
        authenticator_manage = authenticator.ManageAuthenticator(self)
        await authenticator_manage.remove_authenticator()

    @while_running
    async def run_steamguard(self) -> None:
        steamguard = core.steamguard.main()

        async for module_data in steamguard:
            utils.set_console(module_data)

    @while_running
    async def run_cardfarming(self) -> None:
        cardfarming = core.cardfarming.main(self.steamid, custom_game_id=self.custom_gameid)

        async for module_data in cardfarming:
            utils.set_console(module_data)

    @while_running
    async def run_fakerun(self) -> None:
        fakerun = core.fakerun.main(self.steamid, self.custom_gameid, self.extra_gameid)

        async for module_data in fakerun:
            utils.set_console(module_data)

    @while_running
    async def run_steamtrades(self) -> None:
        steamtrades = core.steamtrades.main()

        async for module_data in steamtrades:
            utils.set_console(module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    @while_running
    async def run_steamgifts(self) -> None:
        steamgifts = core.steamgifts.main()

        async for module_data in steamgifts:
            utils.set_console(module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue
