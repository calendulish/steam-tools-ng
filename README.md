[STNG] Steam Tools NG (formerly Steam Tools)
========================================
[![STNG](https://lara.monster/archive/stng_last.png)](https://github.com/ShyPixie/steam-tools-ng)  
  
[![transifex](https://img.shields.io/badge/transifex-contribute%20now-blue.svg?style=flat)](https://www.transifex.com/steam-tools-ng)
[![windows build status](https://badges.lara.monster/ShyPixie/badge-metadata/steam-tools-ng-windows-build)](https://github.com/ShyPixie/steam-tools-ng/actions/workflows/build.yml)
[![linux build status](https://badges.lara.monster/ShyPixie/badge-metadata/steam-tools-ng-linux-build)](https://github.com/ShyPixie/steam-tools-ng/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/ShyPixie/steam-tools-ng/branch/master/graph/badge.svg?token=RTNIQZDZ69)](https://codecov.io/gh/ShyPixie/steam-tools-ng)
[![Quality](https://api.codiga.io/project/33951/score/svg)](https://app.codiga.io/project/33951/dashboard)
[![GitHub license](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.html)
[![GitHub release](https://img.shields.io/github/release/ShyPixie/steam-tools-ng.svg?style=flat)](https://github.com/ShyPixie/steam-tools-ng/releases)

Some useful tools to use with steam client or compatible programs and websites.

You can run the follow modules from steam-tools:

* Steam Guard: Will provide codes for login on steam (mobile authenticator clone)

* Confirmations: Confirm trades and/or market listing

* SteamTrades: Bump trades at steamtrades.com

* SteamGifts: Join in giveaway at steamgifts.com

* Card Farming: Drop cards from steam games

* More (**Coming Soon**)

Graphical User Interface
-------------

```
Just run and follow on-screen instructions
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

You can request improvements and/or new features at https://github.com/ShyPixie/steam-tools-ng/issues

The Steam Tools NG is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

The Steam Tools NG is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

Lara Maia <dev@lara.monster>
