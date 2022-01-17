[STNG] Steam Tools NG (formerly Steam Tools)
========================================
[![STNG](https://lara.monster/archive/stng_last.png)](https://github.com/ShyPixie/steam-tools-ng)  
  
[![transifex](https://img.shields.io/badge/transifex-contribute%20now-blue.svg)](https://www.transifex.com/steam-tools-ng)
[![GitHub license](https://img.shields.io/badge/license-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![GitHub release](https://img.shields.io/github/release/ShyPixie/steam-tools-ng.svg)](https://github.com/ShyPixie/steam-tools-ng/releases)


Some useful tools to use with steam client or compatible programs and websites.

You can run the follow modules from steam-tools:

* Steam Guard: Will provide codes for login on steam (mobile authenticator clone)

* Trade Card (**Coming Soon**): Accept/decline trades from steam

* Confirmations: Confirm trades and/or market listing

* SteamTrades: Bump trades at steamtrades.com

* SteamGifts: Join in giveaway at steamgifts.com

* Card Farming: Drop cards from steam games

* More (**Coming Soon**)

Gtk Interface
-------------

```
Just run and follow on-screen instructions
```

Console Interface
-----------------
```
usage: steam-tools-ng [-h] [-c module [options]] [--config-dir] [--log-dir]
                      [--reset] [--reset-password]

optional arguments:
  -h, --help            show this help message and exit
  -c module [options], --cli module [options]
                        Start module without GUI (console mode)
  --config-dir          Shows directory used to save config files
  --log-dir             Shows directory used to save log files
  --reset               Clean up settings and log files
  --reset-password      Clean up saved password

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
