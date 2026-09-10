# Wiki mirror — Startup parameters

**Source:** https://pzwiki.net/wiki/Startup_parameters
**Fetched:** 2026-09-09
**Wiki page version:** 42.20.4
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Reference table of launcher, JVM and game arguments, split client / server / both, with usage recipes for Steam launch options, desktop shortcuts and `StartServer64.bat`. Stamped 42.20.4.
- Syntax rule: JVM arguments come first and must be terminated with `--` even when no game arguments follow; the shipped server bat already separates them.
- Client arguments the test harness leans on: `+connect <ip>:<port>` and `+password <pw>` (= `-Dargs.server.connect` / `-Dargs.server.password`) to skip the server browser, `-debug`, `-debuglog=<Types>`, `-modfolders workshop,steam,mods` for mod source and load order, `-nosteam`, `-safemode`, and `-cachedir=<path>` — one per client instance, since it is the whole Zomboid folder.
- Server side: `-servername` (drives save/ini/db names), `-adminusername`/`-adminpassword` to skip the interactive prompt, `-port`/`-udpport`/`-ip`, `-coop`, `-statistic <sec>`, `-steamvac`; `-gui` is described as unfinished and exception-prone, so avoid it.
- JVM and launcher: `-Xmx`/`-Xms`, `-Dzomboid.steam`, `-Ddeployment.user.cachedir` (Linux only), and `-pzexeconfig <json>`, which swaps the entire launcher config including its vmArgs — the cleanest way to give one instance its own heap.
- Page states `-Dsoftreset` does not work as of current stable (42.20.4), citing a Steam discussion — the one entry here not to build on.
- Local install cross-check carried over from the hand excerpt this file replaces: `ProjectZomboid64.json` sets mainClass `zombie/gameStates/MainScreenState` with vmArgs including `-Xmx3072m -Dzomboid.steam=1`, and `ProjectZomboidServer.bat` runs `zombie.network.GameServer` with `-Xmx3072m -XX:+UseZGC`.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.20.4}}
Project Zomboid has customizable '''startup parameters''' that are used to override the default options of the launcher, JVM, and game. JVM arguments must be provided first and end with <code>--</code> even if there are no game arguments. Game arguments can be passed to the launcher because they are forwarded to the game itself.

== Usage ==

=== From the [[Steam]] application ===
#Right-click the game in the ''Steam Library'', a menu will pop up.
#Click ''Properties''. A new modal window will appear.
#By default the 'general' tab in the modal window should be opened, but if not, click it.
#Look under ''Launch Options'' → ''Selected Launch Option''. Add a parameter from the table below, e.g., <code>-debug</code> to the field.
#Close window and launch the game.

==== Example ====
{{CodeSnip
| code=
-Xmx8192m -Xms8192m -- -debug
}}

=== From a game shortcut ===
#Navigate to the game folder via right-clicking ''Project Zomboid'' in the ''Steam Library'' → ''Manage'' → ''Browse local files''.
#Create a shortcut of the game launcher <code>ProjectZomboid<32/64>.exe</code>.
#Add the arguments to the ''Target'' field.

==== Example ====
{{CodeSnip
| code=
"C:\ProjectZomboid64.exe" -Xmx8192m -Xms8192m -- -debug
}}

=== From the StartServer64.bat parameters ===
This method is only for dedicated servers.
#Open the <code>StartServer64.bat</code> script with a text editor.
#Add any JVM arguments after the <code>-Xmx</code> line in the script.
#Add any game parameters after the <code>%1 %2</code> text inside the script, which is at the end of the file before PAUSE.

{{Note|type=warn|Here the <code>--</code> is not needed because the script already separates the JVM and game arguments.}}

==== Example ====
{{CodeSnip
| code=
-Xmx16g -Duser.home=C:\Zomboid
}}
{{CodeSnip
| code=
%1 %2 -nosteam -servername MySecondServer -adminpassword Password123
}}

== Common use cases ==

=== Increasing allocated memory ===
To increase the maximum allocated memory to 8 GB and the minimum to 8 GB, add the following to the launch options:
{{CodeSnip
| code=
-Xmx8192m -Xms8192m --
}}

{{Note|type=warn|If the JVM cannot allocate the minimum amount of memory set here (as noted by <code>-Xms</code>), the game will not boot. For most people, and to recommend on a wide range of systems, its better to not set the minimum at all.}}

=== Opening the game in debug mode ===
To open the game in debug mode, add the following to the launch options:
{{CodeSnip
| code=
-debug
}}

=== Disabling Steam integration ===
To disable Steam integration, add the following to the launch options:
{{CodeSnip
| code=
-nosteam
}}

== Game arguments ==

=== Client & server ===
{| class="wikitable theme-blue" style="width: 100%;"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-console_dot_txt_size_kb={int <span style="color: #c21d1d;">size</span>}</code>
| Sets the maximum console.txt file size in kilobytes.
| style="white-space: nowrap" | <code>-console_dot_txt_size_kb=<span style="color: #c21d1d;">512000</span></code>
|-
| style="white-space: nowrap" | <code>-cachedir={str <span style="color: #c21d1d;">path</span>}</code>
| Sets the absolute path for the game's cache directory.
| style="white-space: nowrap" | <code>-cachedir="<span style="color: #c21d1d;">C:\Zomboid</span>"</code>
|-
| style="white-space: nowrap" | <code>-nosteam</code>
| This is equal to using the <code>-Dzomboid.steam</code> JVM property.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-anti-cheats</code>
| Sets the internal anticheats enable flag which force-enables the anticheat. This flag is automatically true when in a non-coop environment. This option will do nothing if anticheats are disabled in the server config.
| style="white-space: nowrap" |
|}

=== Client ===
{| class="wikitable theme-blue"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-safemode</code>
| Launches the game with reduced resolution, texture compression, 1x tile scale, and 1x texture scale. Disables the [https://projectzomboid.com/modding/zombie/iso/weather/WeatherShader.html WeatherShader] and [https://www.khronos.org/opengl/wiki/Framebuffer_Object FBO] support. No FBO means that offscreen rendering will not work! The game will enable safe mode if it fails to create a framebuffer object.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-nosound</code>
| Disables the game audio. This has the side effect of disabling some aspects of the voice chat.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-aitest</code>
| Enables the AI testing mode. It has been neglected and isn't used anywhere but to set [https://projectzomboid.com/modding/zombie/characters/IsoGameCharacter.html#isNPC() IsoGameCharacter.isNPC].
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-novoip</code>
| Disables the [https://projectzomboid.com/modding/zombie/core/raknet/VoiceManager.html VoiceManager] from starting, which controls in-game voice chat.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-debug</code>
| Launches the game in [[debug mode]]. Makes the [https://projectzomboid.com/modding/zombie/network/CoopMaster.html CoopMaster] coop server use debug mode.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-debuglog={DebugType[] <span style="color: #c21d1d;">types</span>}</code>
| Enables certain filters in the console log. Takes in a comma-separated list of [https://projectzomboid.com/modding/zombie/debug/DebugType.html DebugType] values. Since the client doesn't have <code>-disablelog</code>, this allows us to specify whether to enable or disable the filter.
| style="white-space: nowrap" | <code>-debuglog=<span style="color: #c21d1d;">All</span></code><br><code>-debuglog=<span style="color: #c21d1d;">Network,-Sound</span></code>
|-
| style="white-space: nowrap" | <code>+connect {str <span style="color: #c21d1d;">ip</span>}:{str <span style="color: #00881d;">port</span>}</code>
| This is equivalent to using the <code>-Dargs.server.connect</code> JVM property.
| style="white-space: nowrap" | <code>+connect <span style="color: #c21d1d;">127.0.0.1</span>:<span style="color: #00881d;">16261</span></code>
|-
| style="white-space: nowrap" | <code>+password {str <span style="color: #c21d1d;">password</span>}</code>
| This is equivalent to using the <code>-Dargs.server.password</code> JVM property.
| style="white-space: nowrap" | <code>+password <span style="color: #c21d1d;">ServersPassword</span></code>
|-
| style="white-space: nowrap" | <code>-debugtranslation</code>
| Enables the debug mode for the [https://projectzomboid.com/modding/zombie/core/Translator.html Translator] class. Writes possible translation issues to <code>cachedir/translationProblems.txt</code> and allows for reloading translation files while holding F12 in-game.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-modfolders {Folder[] <span style="color: #c21d1d;">folders</span>}</code>
| Controls where mods load from and their load order. There are only 3 possible folders. Any folder can be unspecified to disable the game from loading mods in that directory, and rearranged to change the load order of the mods.
| style="white-space: nowrap" | <code>-modfolders <span style="color: #c21d1d;">workshop,steam,mods</span></code><br><code>-modfolders <span style="color: #c21d1d;">workshop,steam</span></code>
|-
| style="white-space: nowrap" | <code>-debugcfg={str <span style="color: #c21d1d;">path</span>}</code>
| Loads a custom debug config file instead of the default (<code>debuglog.cfg</code> or <code>debuglog-server.cfg</code>)
| style="white-space: nowrap" | <code>-debugcfg=<span style="color: #c21d1d;">debuglog-custom.cfg</span></code>
|-
| style="white-space: nowrap" | <code>-imgui</code>
| Launches the game in [[debug mode]] with [[Imgui]] enabled.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-imguidebugviewports</code>
| Launches the game in [[debug mode]] with [[Imgui]] enabled in a separate window.
| style="white-space: nowrap" |
|}

=== Server ===
{| class="wikitable theme-blue"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-coop</code>
| Runs a coop server instead of a dedicated server. Disables the default admin from being accessible.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-disablelog={DebugType[] <span style="color: #c21d1d;">types</span>}</code>
| Disables certain filters in the console log. Takes in a comma-separated list of [https://projectzomboid.com/modding/zombie/debug/DebugType.html DebugType] values.
| style="white-space: nowrap" | <code>-disablelog=<span style="color: #c21d1d;">All</span></code><br><code>-disablelog=<span style="color: #c21d1d;">Network,Sound</span></code>
|-
| style="white-space: nowrap" | <code>-debuglog={DebugType[] <span style="color: #c21d1d;">types</span>}</code>
| Enables certain filters in the console log. Takes in a comma-separated list of [https://projectzomboid.com/modding/zombie/debug/DebugType.html DebugType] values.
| style="white-space: nowrap" | <code>-debuglog=<span style="color: #c21d1d;">All</span></code><br><code>-debuglog=<span style="color: #c21d1d;">Network,Sound</span></code>
|-
| style="white-space: nowrap" | <code>-adminusername {str <span style="color: #c21d1d;">name</span>}</code>
| Uses a different username for the default admin user when creating a server. It doesn't remove the previous default admin user if there is one.
| style="white-space: nowrap" | <code>-adminusername <span style="color: #c21d1d;">BobTheAdmin75</span></code>
|-
| style="white-space: nowrap" | <code>-adminpassword {str <span style="color: #c21d1d;">pass</span>}</code>
| Set the default admin user's password automatically, bypassing the prompt if the default admin user is not found.
| style="white-space: nowrap" | <code>-adminpassword <span style="color: #c21d1d;">ReallySecurePassword</span></code>
|-
| style="white-space: nowrap" | <code>-ip {str <span style="color: #c21d1d;">ip</span>}</code>
| Forces the server to bind to a specific IP address.
| style="white-space: nowrap" | <code>-ip <span style="color: #c21d1d;">123.45.678.9</span></code>
|-
| style="white-space: nowrap" | <code>-gui</code>
| Launches the server GUI alongside the console. Another neglected argument that is unfinished, doesn't render properly, causes lots of exceptions, and uses extra memory.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-statistic {int <span style="color: #c21d1d;">period</span>}</code>
| Enables multiplayer statistics monitoring. The period is measured in seconds. Monitored statistics are saved in the <code>cachedir/Statistic</code> directory.
| style="white-space: nowrap" | <code>-statistic <span style="color: #c21d1d;">10</span></code>
|-
| style="white-space: nowrap" | <code>-port {int <span style="color: #c21d1d;">port</span>}</code>
| Overrides the DefaultPort config option in the INI file.
| style="white-space: nowrap" | <code>-port <span style="color: #c21d1d;">16261</span></code>
|-
| style="white-space: nowrap" | <code>-udpport {int <span style="color: #c21d1d;">port</span>}</code>
| Overrides the UDPPort config option in the INI file.
| style="white-space: nowrap" | <code>-udpport <span style="color: #c21d1d;">16261</span></code>
|-
| style="white-space: nowrap" | <code>-steamvac {bool <span style="color: #c21d1d;">enabled</span>}</code>
| Enables or disables [[wikipedia:{{lcs}}:Valve_Anti-Cheat|Valve Anti-Cheat]] on the server. Overrides the option in the server INI config.
| style="white-space: nowrap" | <code>-steamvac <span style="color: #c21d1d;">true</span></code>
|-
| style="white-space: nowrap" | <code>-servername {str <span style="color: #c21d1d;">name</span>}</code>
| Sets the internal servername to use. It affects the name of the save files that are loaded/saved.
| style="white-space: nowrap" | <code>-servername <span style="color: #c21d1d;">AnotherWorldSave</span></code>
|}

== JVM arguments ==
{{Note|type=warn|JVM arguments must be provided first before client/server arguments and ending with {{Code|--}} even if there are no game arguments. {{Code|--}} must be included at the ending if Java arguments are used.}}

=== Client & server ===
{| class="wikitable theme-blue"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-Xms{int <span style="color: #c21d1d;">size</span>}{char <span style="color: #00881d;">unit</span>}</code>
|  The minimum amount of memory to allocate to the JVM. The game will not start if there is not enough memory available on the system to allocate. The unit can be <code>g</code> or <code>m</code>.
| style="white-space: nowrap" | <code>-Xms<span style="color: #c21d1d;">8192</span><span style="color: #00881d;">m</span></code>
|-
| style="white-space: nowrap" | <code>-Xmx{int <span style="color: #c21d1d;">size</span>}{char <span style="color: #00881d;">unit</span>}</code>
| The maximum amount of memory to allocate to the JVM. Setting this above the physical RAM amount of the system will end up using virtual memory. The unit can be <code>g</code> or <code>m</code>.
| style="white-space: nowrap" | <code>-Xmx<span style="color: #c21d1d;">8192</span><span style="color: #00881d;">m</span></code>
|-
| style="white-space: nowrap" | <code>-XX:+AlwaysPreTouch</code>
| Requests the VM to touch every page on the Java heap after requesting it from the operating system and before handing memory out to the application.  If you are using ZGC it is officially recommended that one enables this option as of Java 21. <ref>[https://docs.oracle.com/en/java/javase/25/gctuning/z-garbage-collector.html HotSpot Virtual Machine Garbage Collection Tuning Guide]</ref>
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-Dzomboid.ConsoleDotTxtSizeKB={int <span style="color: #c21d1d;">size</span>}</code>
| Sets the maximum console.txt file size in kilobytes.
| style="white-space: nowrap" | <code>-Dzomboid.ConsoleDotTxtSizeKB=<span style="color: #c21d1d;">512000</span></code>
|-
| style="white-space: nowrap" | <code>-Dzomboid.steam={int <span style="color: #c21d1d;">enabled</span>}</code>
| Disables the game's Steam API integration, which prevents joining Steam servers or accessing Workshop content.
| style="white-space: nowrap" | <code>-Dzomboid.steam=<span style="color: #c21d1d;">1</span></code>
|-
| style="white-space: nowrap" | <code>-Ddeployment.user.cachedir={str <span style="color: #c21d1d;">path</span>}</code>
| Sets the game's cache directory. The same as setting <code>-cachedir</code>. Only works on Linux.
| style="white-space: nowrap" | <code>-Ddeployment.user.cachedir="<span style="color: #c21d1d;">/home/user/zomboid_server</span>"</code>
|-
| style="white-space: nowrap" | <code>-Dsoftreset</code>
| Forces the game to perform a soft reset. This does not work as of {{Current version|stable}}. The issue was reported and could be fixed in [[Build 42|future versions]]<ref>[https://steamcommunity.com/app/108600/discussions/0/3191367619812018387/ Dedicated Server Soft Reset :: Project Zomboid General Discussions]</ref>.
| style="white-space: nowrap" |
|-
| style="white-space: nowrap" | <code>-Ddebug</code>
| Launches the game in [[debug mode]]. Makes the [https://projectzomboid.com/modding/zombie/network/CoopMaster.html CoopMaster] coop server use debug mode if enabled.
| style="white-space: nowrap" |
|}

=== Client ===
{| class="wikitable theme-blue"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-Dargs.server.connect={str <span style="color: #c21d1d;">ip</span>}:{str <span style="color: #00881d;">port</span>}</code>
| Connects to the server specified without needing to use the server browser.
| style="white-space: nowrap" | <code>-Dargs.server.connect="<span style="color: #c21d1d;">123.4.567.89</span>:<span style="color: #00881d;">16261</span>"</code>
|-
| style="white-space: nowrap" | <code>-Dargs.server.password={str <span style="color: #c21d1d;">pass</span>}</code>
| Provides the server being connected to a password without needing to use the server browser.
| style="white-space: nowrap" | <code>-Dargs.server.password="<span style="color: #c21d1d;">DinoNuggetsTasteGood!!</span>"</code>
|}

== Launcher arguments ==

=== Client ===
{| class="wikitable theme-blue"
|-
! Arguments !! Description !! Example
|-
| style="white-space: nowrap" | <code>-pzexeconfig {str <span style="color: #c21d1d;">config</span>}</code>
| Overrides the default launcher config <code>ProjectZomboid64.json</code>. An alternative to specifying args in the bat or in launch options.
| style="white-space: nowrap" | <code>-pzexeconfig <span style="color: #c21d1d;">ProjectZomboid64Custom.json</span></code>
|-
| style="white-space: nowrap" | <code>-pzexelog {str <span style="color: #c21d1d;">logfile</span>}</code>
| Stores the logging output of the launcher <code>ProjectZomboid64.exe</code>. It is only useful for debugging purposes.
| style="white-space: nowrap" | <code>-pzexelog <span style="color: #c21d1d;">ProjectZomboid64.log</span></code>
|-
| style="white-space: nowrap" | <code>-pzexejavacmd {str <span style="color: #c21d1d;">path</span>}</code>
| Overrides the default bundled JRE, allowing you to specify the path to any Java installation.
| style="white-space: nowrap" | <code>-pzexejavacmd <span style="color: #c21d1d;">jre64/bin/java</span></code>
|}

== References ==
<references />

== Navigation ==
{{Navbox modding}}

{{ll|Category:Multiplayer}}
{{ll|Category:Project Zomboid}}
```
