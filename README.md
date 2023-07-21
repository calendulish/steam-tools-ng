[STNG] Steam Tools NG (formerly Steam Tools)
========================================
[![STNG](https://lara.monster/archive/stng_last.png)](https://github.com/calendulish/steam-tools-ng)  
  
[![transifex](https://img.shields.io/badge/transifex-contribute%20now-blue.svg?style=flat)](https://www.transifex.com/calendulish/steam-tools-ng)
[![windows build status](https://badges.lara.monster/calendulish/.github/steam-tools-ng-windows-build)](https://github.com/calendulish/steam-tools-ng/actions/workflows/build.yml)
[![linux build status](https://badges.lara.monster/calendulish/.github/steam-tools-ng-linux-build)](https://github.com/calendulish/steam-tools-ng/actions/workflows/build.yml)
[![GitHub license](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.html)
[![GitHub release](https://img.shields.io/github/release/calendulish/steam-tools-ng.svg?style=flat)](https://github.com/calendulish/steam-tools-ng/releases)

Some useful tools to use with steam client or compatible programs and websites.

You can run the follow modules from steam-tools:

* Steam Guard: Will provide codes for login on steam (mobile authenticator clone)

* Confirmations: Confirm trades and/or market listing

* SteamTrades: Bump trades at steamtrades.com

* SteamGifts: Join in giveaway at steamgifts.com

* Card Farming: Drop cards from steam games

* Fake Run: Will run any game forever, even if you don't have it installed

* Free coupons: Get coupons for free and donate your coupons

* More (**Coming Soon**)

Graphical User Interface
-------------

```
Just run steam-tools-ng-gui and follow on-screen instructions
```

Command Line Interface
-----------------
```
usage: steam-tools-ng [-h] [--reset] [--reset-password] [--add-authenticator] [-v] [<module>]

positional arguments:
  <module>             Start a module

options:
  -h, --help           show this help message and exit
  --reset              Clean up settings and log files
  --reset-password     Clean up saved password
  --add-authenticator  Use STNG as your Steam Authenticator
  -v, --version        Show version

Available modules | available options
 steamguard       | [oneshot]
 steamtrades      | [oneshot]
 steamgifts       | [oneshot]
 cardfarming      | [oneshot],[gameid]
 fakerun          | <gameid>
```
___________________________________________________________________________________________

You can request improvements and/or new features at https://github.com/calendulish/steam-tools-ng/issues

The Steam Tools NG is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

The Steam Tools NG is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

Lara Maia <dev@lara.monster> 2015 ~ 2023

[![Made with](https://img.shields.io/badge/made%20with-girl%20power-f070D0.svg?longCache=true&style=for-the-badge)](https://lara.monster)
