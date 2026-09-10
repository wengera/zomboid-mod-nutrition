# Wiki mirror — Mod_data

**Source:** https://pzwiki.net/wiki/Mod_data
**Fetched:** 2026-09-10
**Wiki page version:** 42.13.1
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- **Two scopes.** *Object* modData belongs to an instance — `object:getModData()` on any
  `IsoObject`, players included. *Global* modData is keyed by a string through
  `ModData.getOrCreate("MyModDataID")`. Both hold plain-old data only (string, number, boolean,
  table); the game saves them, so a mod must not save them itself.
- **Neither scope is synchronised automatically in multiplayer**, and the page frames that as
  deliberate ("more control over what data is sent"), with the cheating caveat that
  client-only global modData is not authoritative. It also warns that in online MP global
  modData is **not saved on clients**, so it does not survive a reconnect.
- **The one native sync it names is whole-table**: `ModData.transmit("MyModDataID")` sends the
  entire table for that id one way, intercepted with `OnReceiveGlobalModData`, and the page
  itself calls this "limited to small amounts of data … problematic and costly".
- **Recommended pattern:** cache the table once in `OnInitGlobalModData` — the reference does
  not change within a session — and read the cached local thereafter.
- **Gap against our own measurements.** The page never mentions `IsoObject.transmitModData()`
  (the *object*-scope push, which slice 08 measured as whole-table:
  [`exp08-20260910-152944`](../../testing/artifacts/exp08-20260910-152944/witness-probe.json)),
  nor `SyncItemFieldsPacket`'s wipe-and-replace of item modData. Treat it as a partial map of
  the modData sync surface, not the whole of it.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.13.1}}
'''Mod data''' tables are used to persistently store Lua data. Mod data tables are regular Lua tables; they do not have any special semantics or functionality. Only plain old data (strings, booleans, numbers, and tables) can be stored persistently.

In other games, to have persistent data it is often required that you manually save your data when the save gets closed, but in Project Zomboid, you '''should not do that''' because the game handles the saving of the mod data. You should simply use the mod data as a [[Lua (language)#Tables|table]] that will persist between sessions. If data you are using doesn't need to be persistent, you can simply use a [[Lua (language)#Modules|module]].

{{Note|type=error|Accessing mod data during the event [[OnSave]] will not access the save mod data but the next session mod data. This means if you store anything during the [[OnSave]] event, these data will possibly be there in the next session, as long as you don't close the game.}}

== Object Mod Data ==
Any IsoObject has mod data, typically referred to as ''object mod data'' for disambiguation. Object mod data belongs to an instance of an object, such as a specific player or tile. Object mod data can be retrieved using {{Code|object:getModData()|lang=lua}}.
{{CodeSnip
| lang = lua
| code =
local player = getPlayer()
local modData = player:getModData()
modData.myString = "Hello World"
modData.myNumber = 42
modData.myTable = {1, 2, 3}
modData.myBoolean = true
}}

== Global Mod Data ==
Global mod data is similar to object mod data, but does not belong to a specific object. Instead, global mod data tables are accessed with a unique string key through the {{JavaObject|ModData|package=zombie/world/moddata}} class.
{{CodeSnip
| lang = lua
| code =
local modData = ModData.getOrCreate("MyModDataID")
modData.myString = "Hello World"
modData.myNumber = 42
modData.myTable = {1, 2, 3}
modData.myBoolean = true
}}

To improve [[Mod optimization|performance]], mod data can be cached, as the reference will not change throughout the course of a session:
{{CodeSnip
| lang = lua
| code =
local modData

-- cache the current save mod data when the save launches
Events.OnInitGlobalModData.Add(function()
    modData = ModData.getOrCreate("MyModDataID")
end)

-- example usage
Events.OnWeaponHitCharacter.Add(function(attacker, target, weapon, damage)
    modData.lastUsedWeapon = weapon:getFullType() -- persistently store the last used weapon
end)
}}

{{Note|type=warn|In online [[multiplayer]], GlobalModData is not saved on clients (client-only save), so it will not persist on reconnect!}}

== Networking ==
Global and object mod data is '''not''' automatically synchronized between server and clients in multiplayer games. This is actually a good thing, as it allows for more control over what data is sent over the network by allowing for network optimization, as well as client-side persistent data. This can however be a source of potential cheating if important data is only stored in client-side global mod data, and thus you need [[networking]] solutions.

The [[networking]] page covers part of the solutions available, but there exists an native solution for mod data, which however has some limitations. {{JavaObject|ModData|package=zombie/world/moddata}} has a function {{Code|transmit}}, which can be used to send the entire mod data table for a specific {{Code|"MyModDataID"}} from the client to the server, or vice versa. However, you have to manually intercept the transmited data with the use of [[OnReceiveGlobalModData]]. This networking solution is limited to small amounts of data, as the entire table is serialized and sent over the network at once, which was shown to be problematic and costly. Instead, use other [[networking]] solutions for larger amounts of data.

== External links ==
* [https://github.com/MrBounty/PZ-Mod---Doc/blob/main/How%20to%20use%20global%20modData.md Global mod data guide] - notably explains more in details the available functions and the networking aspects.

== Navigation ==
{{Navbox modding}}

{{ll|Category:Lua (API)}}
```
