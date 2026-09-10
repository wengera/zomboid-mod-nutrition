# Wiki mirror — Networking

**Source:** https://pzwiki.net/wiki/Networking
**Fetched:** 2026-09-10
**Wiki page version:** 42.13.1
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- **The server owns the state.** "Since Build 42.13.1 release, server side handles most of the
  logic for player damage, item stats etc. This means you need to set any of these from the
  server side instead of the client side and then use sync functions." That is the wiki's own
  statement of the rule this library measured independently for `Nutrition`, hunger and thirst
  ([vanilla/eating-pipeline.md](../../docs/vanilla/eating-pipeline.md) § MP behaviour).
- **Environment gates.** `isClient()` / `isServer()` — both false means singleplayer; the
  file-top `if isClient() then return end` idiom skips a whole file, and `lua/client/`,
  `lua/server/`, `lua/shared/` placement is the declarative form of the same thing.
- **Commands are the channel.** `sendClientCommand(module, command, args)` is received by
  `Events.OnClientCommand.Add(f(module, command, playerObj, args))`;
  `sendServerCommand([playerObj,] module, command, args)` by
  `Events.OnServerCommand.Add(f(module, command, args))`. `args` is plain-old data only — no
  `IsoPlayer`, no container, no Java object of any kind.
- **Passing a player** means passing `player:getOnlineID()` and re-resolving with
  `getPlayerByOnlineID(...)`; the id is explicitly **not persistent** across load/unload, so it
  is not an identity key. On the client→server direction the sender arrives as `playerObj`
  anyway.
- **"Syncing functions" is a `{{Stub}}`** with exactly one row —
  `syncPlayerStats(IsoPlayer player, int syncParams)` — so the page names the command bus in
  full and the sync surface barely at all.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.13.1}}
'''Networking''' is a process needed to handle client/server interactions, allowing for the exchange of data and commands between the two to properly sync. This guide will not explain when networking should be used, but rather how to implement it.

Since [[Build 42.13.1]] release, server side handles most of the logic for player damage, item stats etc. This means you need to set any of these from the server side instead of the client side and then use sync functions to sync specifically what you changed.

== Client/Server only code ==
When writing code that should only run on the client or server, you can use the following checks:
{{CodeSnip
| lang = lua
| code =
if isClient() then
    -- this code is ran client side
elseif isServer() then
    -- this code is ran server side
else
    -- this code is ran in singleplayer
end
}}

You can user a helper function to check if the code is ran in singleplayer:
{{CodeSnip
| lang = lua
| code =
local function isSinglePlayer()
    return not isClient() and not isServer()
end
}}

These methods can be used to have client/server or singleplayer only specific Lua files by adding at the very top of your lua files the following which will skip the entire file content based on the environment it is ran in:
{{CodeSnip
| lang = lua
| code =
-- most commonly used: file should load only on the server side or in singleplayer
if isClient() then return end
}}
{{CodeSnip
| lang = lua
| code =
-- file should load only on the client side or in singleplayer
-- you can also accomplish this by placing your file in the lua/client/ directory
if isServer() then return end
}}
{{CodeSnip
| lang = lua
| code =
-- file should load only on the client side and not in singleplayer
if not isClient() then return end
}}
{{CodeSnip
| lang = lua
| code =
-- file should load only on the server side and not in singleplayer
if not isServer() then return end
}}
{{CodeSnip
| lang = lua
| code =
-- file should load only in singleplayer
if isClient() or isServer() then return end
}}

Use these to skip loading functions or variables in an environment that does not need them.

=== Client status ===
To check if the client is an admin, you can use {{Code|lang=lua|isAdmin()}} from client side, and from server side you can use {{Code|lang=Java|IsoPlayer.getAccessLevel()}}:
{{CodeSnip
| lang = lua
| code =
-- if ran client side, check if the client is an admin
-- else, check if it's singleplayer, meaning the player has admin rights
-- use this based on what your mod needs to do for both situations
local function checkClientIsAdmin()
    return isClient() and isAdmin() or isSinglePlayer()
end
}}

== Commands ==
The main method used for networking is the ''command'' system. Commands are sent from one side (client or server) to the other, and are handled by a function on the receiving side. Commands can be sent with or without parameters, and can be sent to all clients, a specific client, or the server and intercepted by the use of specific [[Lua event]]s.

Commands can be identified with the use a {{Code|lang=lua|module}}, which is suggested to be your mod name, and {{Code|lang=lua|command}} name. The transmitted data can only hold plain old data (strings, booleans, numbers, and tables), so no [[Java object]] instances such as the player ({{JavaObject|IsoPlayer|package=zombie/characters}}) or an inventory ({{JavaObject|InventoryContainer|package=zombie/inventory/types}}).

[[File:Networking.png|center|800px|class=logo-dark]]

=== Client to server ===
The client sends commands to the server with the use of the following:
{{CodeSnip
| lang = lua
| code =
local args = {} -- put any data inside this table
sendClientCommand("ModuleName", "CommandName", args)
}}

And the server intercepts the client commands with the use of [[OnClientCommand]]:
{{CodeSnip
| lang = lua
| code =
local function onClientCommand(module, command, playerObj, args)
    if module == "MyModule" then
        if command == "MyCommand" then
            -- do something
            -- access arguments with -> args.myValue
            -- access the sender with playerObj
        end
    end
end
Events.OnClientCommand.Add(onClientCommand)
}}

=== Server to client ===
The server sends commands to every clients with the use of the following:
{{CodeSnip
| lang = lua
| code =
local args = {}
sendServerCommand("ModuleName", "CommandName", args)
}}

Or a specific client by using its IsoPlayer instance:
{{CodeSnip
| lang = lua
| code =
-- assuming playerObj here is an IsoPlayer instance
local args = {}
sendServerCommand(playerObj, "ModuleName", "CommandName", args)
}}

And the client intercepts the server commands with the use of [[OnServerCommand]]:
{{CodeSnip
| lang = lua
| code =
local function onServerCommand(module, command, args)
    if module == "MyModule" then
        if command == "MyCommand" then
            -- do something
            -- access arguments with -> args.myValue
        end
    end
end
Events.OnServerCommand.Add(onServerCommand)
}}

=== Passing a player object ===
Since you can't send an {{JavaObject|IsoPlayer|package=zombie/characters}} instance directly, you need to utilize what is called the ''onlineID'' which is a simple unique identifier associated to the player. This ID also exists for zombies but doesn't have a dedicated function to retrieve the zombie object from the server side compared to IsoPlayer.

When sending a command from the client to the server, the command caller IsoPlayer instance is passed to the [[OnClientCommand]] event, thus it is usually not needed to pass the onlineID of the player client from client to server.

To pass a player object from client to server, simply use this:
{{CodeSnip
| lang = lua
| code =
--- CLIENT SIDE
-- assuming player is an IsoPlayer instance
local args = { onlineID = player:getOnlineID() }
sendClientCommand("YourModule", "YourCommand", args)
}}
{{CodeSnip
| lang = lua
| code =
--- SERVER SIDE
local function onClientCommand(module, command, playerObj, args)
    if module == "YourModule" then
        if command == "YourCommand" then
            local playerObj = getPlayerByOnlineID(args.onlineID)
        end
    end
end
Events.OnClientCommand.Add(onClientCommand)
}}

To pass it from server to client, use this:
{{CodeSnip
| lang = lua
| code =
local args = { onlineID = playerObj:getOnlineID() }
sendServerCommand("YourModule", "YourCommand", args)
}}
{{CodeSnip
| lang = lua
| code =
local function onServerCommand(module, command, args)
    if module == "YourModule" then
        if command == "YourCommand" then
            local playerObj = getPlayerByOnlineID(args.onlineID)
        end
    end
end
Events.OnServerCommand.Add(onServerCommand)
}}

{{Note|type=warn|The onlineID is '''not persistent''' so it cannot be used for identification of players or zombies after loading or unloading them. For zombies, see [[PersistentOutfitID]].}}

== Syncing functions ==
{{Stub}}
Syncing functions are defined as global methods for the [[Lua (API)|Lua API]] to call to update stats, items etc. Below is a list of them:
{| class="wikitable sortable theme-blue"
|+ style="white-space:nowrap" | List of Script types
! function !! Description
|-
| {{Code|lang=java|syncPlayerStats(IsoPlayer player, int syncParams}}
| Syncs various player stats, need to pass an integer in {{Code|syncParams}} which can be easily found using {{JavaObject|CharacterStat|package=zombie/characters}}.
|}

== See also ==
* [[Mod data]] – methods for storing data.
* [[Lua (API)#Folder structure]] – details which files are loaded on client/server/singleplayer.

== External links ==
* [https://discord.com/channels/908422782554107904/908459714248048730/927057055246868490|Konijima command guide] – a guide on Discord on commands by Konijima.

== Navigation ==
{{Navbox modding}}

{{ll|Category:Lua (API)}}
{{ll|Category:Modding guides}}
```
