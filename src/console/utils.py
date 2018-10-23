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

import getpass
import json
import logging
import sys
import tempfile
from typing import Optional, Union, Dict, Any, List

import aiohttp
from stlib import webapi, authenticator

from .. import i18n, config

log = logging.getLogger(__name__)
_ = i18n.get_translation


async def add_authenticator(
        webapi_session: webapi.SteamWebAPI,
        login_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    oauth_data = json.loads(login_data['oauth'])
    deviceid = authenticator.generate_device_id(token=oauth_data['oauth_token'])

    auth_data = await webapi_session.add_authenticator(
        oauth_data['steamid'],
        deviceid,
        oauth_data['oauth_token'],
    )

    if auth_data['status'] != 1:
        log.debug(auth_data['status'])
        raise NotImplementedError

    while True:
        sms_code = safe_input(_("Write code received by SMS"))
        auth_code = authenticator.get_code(int(auth_data['server_time']), auth_data['shared_secret'])

        try:
            complete = await webapi_session.finalize_add_authenticator(
                oauth_data['steamid'],
                oauth_data['oauth_token'],
                auth_code,
                sms_code,
            )
        except webapi.SMSCodeError:
            log.error(_("Invalid SMS Code. Please, check the code and try again."))
            continue
        else:
            break

    if complete:
        log.info(_("Success! Saving..."))

        new_configs = {
            'steamid': oauth_data['steamid'],
            'deviceid': deviceid,
            'token': oauth_data['wgtoken'],
            'token_secure': oauth_data['wgtoken_secure'],
            'oauth_token': oauth_data['oauth_token'],
            'account_name': oauth_data['account_name'],
            'shared_secret': auth_data['shared_secret'],
            'identity_secret': auth_data['identity_secret'],
        }

        for key, value in new_configs.items():
            config.new("login", key, value)

        return {**login_data, **auth_data}
    else:
        log.error(_("Unable to add a new authenticator"))
        return None


async def check_login(
        session: aiohttp.ClientSession,
        webapi_session: webapi.SteamWebAPI,
        captcha_gid: int = -1,
        captcha_text: str = '',
        auth_code: str = '',
        mail_code: str = '',
        relogin: bool = False,
) -> bool:
    token = config.parser.get("login", "token")
    token_secure = config.parser.get("login", "token_secure")
    steamid = config.parser.getint("login", "steamid")
    nickname = config.parser.get("login", "nickname")
    identity_secret = config.parser.get("login", "identity_secret")
    shared_secret = config.parser.get("login", "shared_secret")
    mobile_login = True if config.parser.get("login", "oauth_token") else False

    if not token or not token_secure or not steamid:
        log.error(_("STNG is not configured."))
        log.info("Welcome to STNG Setup")
        log.info("How do you want to log-in?")

        user_input = safe_input(_(
            "[1] Use STNG as Steam Authenticator\n"
            "[2] Use custom secrets (advanced users only!)\n"
        ), custom_choices=["1", "2"])

        if user_input == '1':
            mobile_login = True
        elif user_input == '2':
            mobile_login = False
    elif not nickname:
        try:
            nickname = await webapi_session.get_nickname(steamid)
        except ValueError:
            raise NotImplementedError
        else:
            config.new("login", "nickname", nickname)

    session.cookie_jar.update_cookies(config.login_cookies())  # type: ignore

    try:
        is_logged_in = await webapi_session.is_logged_in(nickname)
    except aiohttp.ClientError:
        log.critical(_("No Connection. Please, check your connection and try again."))
        sys.exit(1)

    if not is_logged_in:
        log.error(_("User is not logged in."))

        username = config.parser.get("login", "account_name")

        if not username:
            user_input = safe_input(_("Please, write your username"))
            assert isinstance(user_input, str), "Safe input is returning bool when it should return str"
            username = user_input

        __password = getpass.getpass(_("Please, write your password (it's hidden, and will be not saved)"))

        login = webapi.Login(session, username, __password)

        if shared_secret:
            server_time = await webapi_session.get_server_time()
            auth_code = authenticator.get_code(server_time, shared_secret)
        else:
            log.warning(_("No shared secret found. Trying to log-in without two-factor authentication."))

        if captcha_gid == -1:
            # no reason to send captcha_text if no gid is found
            captcha_text = ''

        while True:
            try:
                login_data = await login.do_login(auth_code, mail_code, captcha_gid, captcha_text, mobile_login)

                if not login_data['success']:
                    raise webapi.LoginError
            except webapi.MailCodeError:
                user_input = safe_input(_("Write code received by email"))
                assert isinstance(user_input, str), "safe_input is returning bool when it should return str"
                mail_code = user_input
                continue
            except webapi.TwoFactorCodeError:
                if mobile_login and not relogin:
                    log.error(_("Unable to log-in! You already have a Steam Authenticator active on current account."))
                    log.error(_("¬ To log-in, remove authenticator from your account and try again."))
                    log.error(_("¬ (STNG will add itself as Steam Authenticator in your account)"))
                else:
                    log.error(_("Unable to log-in! The secret keys are invalid!"))

                return False
            except webapi.LoginBlockedError:
                log.error(_("Your network is blocked! It'll take some time until unblocked. Please, try again later."))
                return False
            except webapi.CaptchaError as exception:
                log.info(_("Steam server is requesting a captcha code."))

                with tempfile.TemporaryFile('w', prefix='stng_', suffix='.captcha') as temp_file:
                    temp_file.write(await login.get_captcha(captcha_gid))

                user_input = safe_input(
                    _("Open {} in an image view and write captcha code that it shows").format(temp_file.name),
                )
                assert isinstance(user_input, str), "Safe input is returning bool when it should return str"
                captcha_text = user_input
                continue
            except webapi.LoginError:
                log.error(_("Unable to log-in! Please, check your username/password and try again."))
                log.error(
                    _("(If you removed the authenticator from your account, run steam-tools-ng --reset and try again.)")
                )

                return False
            except aiohttp.ClientConnectionError:
                log.error(_("No Connection"))
                return False

            has_phone: Optional[bool]

            if mobile_login:
                sessionid = await webapi_session.get_session_id()

                if await login.has_phone(sessionid):
                    has_phone = True
                else:
                    has_phone = False
            else:
                has_phone = None

            if mobile_login:
                if not has_phone:
                    # Impossible to add an authenticator without a phone
                    raise NotImplementedError

                full_login_data = await add_authenticator(webapi_session, login_data)

                assert isinstance(full_login_data, dict)

                print(_("WRITE DOWN THE RECOVERY CODE: %s"), full_login_data['revocation_code'])
                print(_("YOU WILL NOT ABLE TO VIEW IT AGAIN!"))

                break
            else:
                new_configs = {
                    'steamid': login_data['transfer_parameters']['steamid'],
                    'token': login_data['transfer_parameters']['webcookie'],
                    'token_secure': login_data['transfer_parameters']['token_secure'],
                    'account_name': username,
                    'shared_secret': shared_secret,
                    'identity_secret': identity_secret,
                }

                for key, value in new_configs.items():
                    config.new("login", key, value)

                break

    return True


def safe_input(
        msg: str,
        default_response: Optional[bool] = None,
        custom_choices: Optional[List[str]] = None,
) -> Union[bool, str]:
    if default_response and custom_choices:
        raise AttributeError("You can not use both default_response and custom_choices")

    if default_response is True:
        options = _('[Y/n]')
    elif default_response is False:
        options = _('[y/N]')
    elif custom_choices:
        options = f"Your choice [{'/'.join(custom_choices)}]"
    else:
        options = ''

    while True:
        try:
            user_input = input(f'{msg} {options}: ')

            if custom_choices:
                if not user_input:
                    raise ValueError(_('Invalid response from user'))

                if user_input.lower() in custom_choices:
                    return user_input.lower()
                else:
                    raise ValueError(_('{} is not an accepted value').format(user_input))

            if default_response is None:
                if len(user_input) > 2:
                    return user_input
                else:
                    raise ValueError(_('Invalid response from user'))
            elif not user_input:
                return default_response

            if user_input.lower() == _('y'):
                return True
            elif user_input.lower() == _('n'):
                return False
            else:
                raise ValueError(_('{} is not an accepted value').format(user_input))
        except ValueError as exception:
            log.error(exception.args[0])
            log.error(_('Please, try again.'))
