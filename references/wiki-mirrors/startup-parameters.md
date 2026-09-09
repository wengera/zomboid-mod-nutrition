# Mirror: PZwiki "Startup parameters"

- **Source:** https://pzwiki.net/wiki/Startup_parameters
- **Retrieved:** 2026-09-13 · page revised for 42.20.4
- License: CC BY-NC-SA, attribution: PZwiki contributors. Structured excerpt.

Syntax: JVM args first, then `--`, then game args (`--` required whenever JVM
args are given). Server bat separates them already (game args after `%1 %2`).

## Client & server
| Arg | Effect |
|---|---|
| `-cachedir=<path>` | absolute cache dir (Zomboid folder) — **one per client instance** |
| `-nosteam` | disable Steam API (= `-Dzomboid.steam`); workshop folder then ignored for mods |
| `-console_dot_txt_size_kb=<n>` | console.txt cap |
| `-anti-cheats` | force-enable anticheat flag |

## Client
| Arg | Effect |
|---|---|
| `+connect <ip>:<port>` | join server directly (= `-Dargs.server.connect`) |
| `+password <pw>` | server password (= `-Dargs.server.password`) |
| `-debug` | debug mode (also makes coop host debug) |
| `-debuglog=<Types>` | enable log filters, e.g. `All`, `Network,-Sound` |
| `-safemode` | low res, 1x scale, no WeatherShader/FBO (no offscreen rendering) |
| `-nosound` / `-novoip` | disable audio / VoiceManager |
| `-modfolders <list>` | mod source dirs + order: `workshop,steam,mods` |
| `-debugcfg=<file>` | custom debug config |
| `-imgui` / `-imguidebugviewports` | debug UI |
| `-aitest` | neglected AI test flag (sets isNPC) |
| `-debugtranslation` | translation problems file + F12 reload |

## Server
| Arg | Effect |
|---|---|
| `-servername <name>` | internal name → save/ini/db file names |
| `-adminpassword <pw>` / `-adminusername <name>` | default admin bootstrap (skips prompt) |
| `-port <n>` / `-udpport <n>` / `-ip <addr>` | bind overrides |
| `-coop` | coop server mode (no default admin) |
| `-nosteam` | non-Steam server |
| `-debuglog=<Types>` / `-disablelog=<Types>` | log filters |
| `-statistic <sec>` | MP statistics to cachedir/Statistic |
| `-steamvac <bool>` | VAC toggle |
| `-gui` | unfinished server GUI (avoid) |

## JVM
`-Xmx/-Xms`, `-XX:+AlwaysPreTouch` (ZGC advice), `-Dzomboid.ConsoleDotTxtSizeKB`,
`-Dzomboid.steam=1`, `-Ddeployment.user.cachedir` (Linux only), `-Ddebug`,
`-Dsoftreset` (broken in 42.20.4), client: `-Dargs.server.connect`,
`-Dargs.server.password`.

## Launcher (ProjectZomboid64.exe)
`-pzexeconfig <json>` alternate launcher config (per-instance vmArgs!),
`-pzexelog`, `-pzexejavacmd <java>`.

Install facts (local): `ProjectZomboid64.json` mainClass
`zombie/gameStates/MainScreenState`, vmArgs incl. `-Xmx3072m`,
`-Dzomboid.steam=1`; `ProjectZomboidServer.bat` runs
`zombie.network.GameServer` with `-Xmx3072m -XX:+UseZGC`.
