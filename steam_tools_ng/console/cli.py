#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2020
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
import os
import ssl
import sys
from typing import Optional, Any, Callable

import aiohttp
from stlib import plugins, webapi

from . import utils, login
from .. import i18n, config, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


def while_running(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    async def wrapper(self, *args, **kwargs) -> None:
        while True:
            await function(self, *args, **kwargs)

    return wrapper


# noinspection PyUnusedLocal
class SteamToolsNG:
    def __init__(self, plugin_manager: plugins.Manager, module_name: str, module_options: str) -> None:
        self.module_name = module_name
        self.module_options = module_options

        self._session = None
        self._webapi_session = None
        self.plugin_manager = plugin_manager

        self.api_login: Optional[webapi.Login] = None
        self._time_offset = 0
        self.api_url = config.parser.get("steam", "api_url")

    @property
    def time_offset(self) -> int:
        return self._time_offset

    @property
    def session(self) -> aiohttp.ClientSession:
        assert isinstance(self._session, aiohttp.ClientSession), "session has not been created"
        return self._session

    @property
    def webapi_session(self) -> webapi.SteamWebAPI:
        assert isinstance(self._webapi_session, webapi.SteamWebAPI), "webapi session has not been created"
        return self._webapi_session

    @property
    def steamid(self) -> Optional[int]:
        return config.parser.getint("login", "steamid")

    # FIXME: https://github.com/python/asyncio/pull/465
    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self.async_activate())
        task.add_done_callback(self.async_activate_callback)

        with contextlib.suppress(KeyboardInterrupt):
            loop.run_forever()

    def async_activate_callback(self, task: asyncio.Task) -> None:
        if task.cancelled():
            log.debug(_("%s has been stopped due user request"), task.get_coro())
            return

        exception = task.exception()

        if exception and not isinstance(exception, asyncio.CancelledError):
            stack = task.get_stack()

            for frame in stack:
                log.critical(f"{type(exception).__name__} at {frame}")

            log.critical(f"Fatal Error: {str(exception)}")
            loop = asyncio.get_running_loop()
            loop.stop()
            self.on_quit()

    async def do_login(self, *, block: bool = True, auto: bool = False) -> None:
        login_session = login.Login(self)
        future = login_session.do_login(auto)
        await asyncio.gather(future)

    async def async_activate(self) -> None:
        ssl_context = ssl.SSLContext()

        if hasattr(sys, 'frozen'):
            _executable_path = os.path.dirname(sys.executable)
            ssl_context.load_verify_locations(cafile=os.path.join(_executable_path, 'etc', 'cacert.pem'))

        tcp_connector = aiohttp.TCPConnector(ssl=ssl_context)
        self._session = aiohttp.ClientSession(raise_for_status=True, connector=tcp_connector)
        self._webapi_session = webapi.get_session(0, api_url=self.api_url, http_session=self._session)
        self._time_offset = await config.time_offset(self.webapi_session)

        log.info(_("Logging on Steam. Please wait!"))

        token = config.parser.get("login", "token")
        token_secure = config.parser.get("login", "token_secure")

        if not token or not token_secure or not self.steamid:
            await self.do_login()

        self.session.cookie_jar.update_cookies(config.login_cookies())  # type: ignore

        try:
            if await self.webapi_session.is_logged_in(self.steamid):
                log.info("Steam login Successful")
            else:
                await self.do_login(auto=True)
        except aiohttp.ClientError as exception:
            log.exception(str(exception))
            log.error(_("Check your connection. (server down?)"))
            await asyncio.sleep(10)
            return  # FIXME: RETRY ###

        log.debug(_("Initializing module %s"), self.module_name)
        module = getattr(self, f"run_{self.module_name}")
        task = asyncio.create_task(module())
        log.debug(_("Adding a new callback for %s"), task)
        task.add_done_callback(self.async_activate_callback)

    @while_running
    async def run_steamguard(self) -> None:
        steamguard = core.steamguard.main(self.time_offset)

        async for module_data in steamguard:
            utils.set_console(module_data)

    @while_running
    async def run_cardfarming(self) -> None:
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        cardfarming = core.cardfarming.main(self.steamid)

        async for module_data in cardfarming:
            utils.set_console(module_data)

    @while_running
    async def run_steamtrades(self) -> None:
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        steamtrades = core.steamtrades.main()

        async for module_data in steamtrades:
            utils.set_console(module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    @while_running
    async def run_steamgifts(self) -> None:
        self.webapi_session.http.cookie_jar.update_cookies(config.login_cookies())
        steamgifts = core.steamgifts.main()

        async for module_data in steamgifts:
            utils.set_console(module_data)

            if module_data.action == "login":
                await self.do_login(auto=True)
                continue

    def on_quit(self, *args: Any) -> None:
        loop = asyncio.get_running_loop()
        loop.stop()
