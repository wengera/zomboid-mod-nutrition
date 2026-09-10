# Wiki mirror — Lua_event

**Source:** https://pzwiki.net/wiki/Lua_event
**Fetched:** 2026-09-10
**Wiki page version:** 42.20.4
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- **The API is two calls.** `Events.<Name>.Add(fn)` and `Events.<Name>.Remove(fn)` (the same
  function reference), with `fn`'s parameters matching the event's. The roster itself lives in
  the wiki's *Current Lua events* category and in LuaDocs, not on this page.
- **Boot order, as listed.** Launch: `OnLoadSoundBanks`, `OnGameBoot`. Session:
  `OnPreMapLoad` → `OnPreDistributionMerge` → `OnDistributionMerge` → `OnPostDistributionMerge`
  → `OnInitWorld` → *sandbox options load here* → `OnLoadedTileDefinitions` →
  `OnLoadRadioScripts` → **`OnInitGlobalModData`** → `OnLoadMapZones` → `OnLoadedMapZones` →
  `OnNewGame` (client only) → `OnGameTimeLoaded` → `OnSGlobalObjectSystemInit` →
  **`OnServerStarted` (server only)**. After the Click-to-Start screen: `OnCreatePlayer`,
  `OnGameStart`, `OnLoad` — **all three client only**.
- **The consequence for an MP mod** is the one that matters to this library: the three hooks a
  mod usually initialises in never run on a dedicated server, so `OnInitGlobalModData` and
  `OnServerStarted` are the server-side pair. That is exactly the split the installed corpus
  shows (`OnGameStart` 70 hooks / 25 mods against `OnInitGlobalModData` 33 / 14, over the
  `top_events` lists of `data/mod-inventory.json`, 2026-09-10).
- The page also warns that heavy work on the post-Click-to-Start events is the cause of the
  load freeze, and names three third-party event libraries (Events Plus API, Starlit Library,
  Doggy's Library).

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.20.4}}
A '''Lua event''' in programming is a signal or notification that something has occurred or changed. In [[Project Zomboid]], most often a modder's custom functions are attached as observers to an event, so they'll run when the event is called.

A full list of the Lua events can be found in:
* [[:Category:Current Lua events|Lua events category]]
* [[LuaDocs]]

== Hooking to an event ==
To hook a function to an event, you use the <code>Events</code> object. For example, to hook a function to the <code>OnCreatePlayer</code> event, you would write:
{{CodeSnip
| lang = lua
| code =
Events.OnCreatePlayer.Add(yourFunction)
}}

<code>yourFunction</code> is a reference to your Lua function. By using this same reference, you can also remove the function from the event:
{{CodeSnip
| lang = lua
| code =
Events.OnCreatePlayer.Remove(yourFunction)
}}

Your function needs to have parameters that match the event's output. For example, the <code>OnCreatePlayer</code> event has the parameter <code>player</code>. Your function would need to be:
{{CodeSnip
| lang = lua
| code =
local function yourFunction(player)
    -- your code here
end
}}

Each events listed in [[:Category:Current Lua events|Lua events category]] have example code snippets to show how to hook a function to them and their various parameters.

== List of events triggered on game start ==
The list below is a list of events that are triggered when loading into game, ''in the order in which they are triggered.''

'''Launch Game'''
* [[OnLoadSoundBanks]]
* [[OnGameBoot]]

'''Start new game/load game/connect to server'''
* [[OnPreMapLoad]]
* [[OnPreDistributionMerge]]
* [[OnDistributionMerge]]
* [[OnPostDistributionMerge]]
* [[OnInitWorld]]
* ''Sandbox Options loaded here''
* [[OnLoadedTileDefinitions]]
* [[OnLoadRadioScripts]]
* [[OnInitGlobalModData]]
* [[OnLoadMapZones]]
* [[OnLoadedMapZones]]
* [[OnNewGame]] - Client only
* [[OnGameTimeLoaded]]
* [[OnSGlobalObjectSystemInit]] - Basically right before the Click to Start screen
* [[OnServerStarted]] - Server only

'''Click to Start screen here''' - running heavy functions on the following events is the cause for freezing after clicking to start.
* [[OnCreatePlayer]] - Client only
* [[OnGameStart]] - Client only
* [[OnLoad]] - Client only

== Custom events libraries ==
Below are different libraries that add custom events to the game for modders to hook functions to in the same way as vanilla events.
* [[Events Plus API]] by Dismellion
* [[Starlit Library]] by Albion
* [[Doggy's Library]] by Sir Doggy Jvla

== See also ==
* {{ll|Lua (API)}}
* {{ll|Lua object}}
* [https://demiurgequantified.github.io/ProjectZomboidLuaDocs/md_Events.html Lua events] – The [[LuaDocs]] event list.

== Navigation ==
{{Navbox modding}}

{{ll|Category:Lua (API)}}
{{ll|Category:Lua events|&#32;}}
```
