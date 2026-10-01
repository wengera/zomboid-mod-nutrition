---
name: pz-modding-platform
description: Writing, debugging or reviewing a Project Zomboid mod that is not about food or nutrition — weapons, UI, world, vehicles, sounds, tiles — through its `mod.info` (`id=`, `require=`), `common/` and version dirs, `media/scripts` blocks, `media/lua/client`, `server` and `shared` files, event and script hooks, `isServer()` guards, `sendClientCommand`, `OnClientCommand` and `sendServerCommand`, modData and `transmitModData`, `pcall` around Java members, translations, `Mods=` load order, or who owns what on a dedicated multiplayer server. Does not fire on a nutrition task (hunger, thirst, calories, macros, food items, eating, cooking, nutrition moodles, the nutrition mod's packaging or tests), which the nutrition skills own.
---
## Read first
- docs/platform/overview.md
- then the one surface page the task names:
  - docs/platform/mod-anatomy.md — the folder, `mod.info`, version dirs, translations, the join checksum
  - docs/platform/loader-and-scripts.md — the file map, script blocks, load and replay order
  - docs/platform/lua-platform.md — the dialect, `pcall`, Java members, hooks, events, registries
  - docs/platform/mp-model.md — ownership, packets, modData routes, the command bus
  - docs/platform/server-lifecycle.md — a join, a creation, a death and a disconnect on the server, player ids, the player and world stores, the tick order
  - docs/platform/sandbox-options.md — a mod's own sandbox options: the declaration file, the `SandboxVars` mirror, the join sync, a runtime change
  - docs/platform/client-ui.md — the panel toolkit, layout, keybinds, textures, the tooltip, the character-info window, the UI events
- docs/platform/lessons.md

## Coverage
`platform/` is not a modding manual.
It holds what this library measured or read while building a nutrition mod on a dedicated `42.20.4` server with one client.
A topic marked absent has no page, no rule and no claim here; an agent asked about it says so and reads the jar or the mirror, and never infers a wall from silence.
Every verdict is dedicated-server multiplayer; single-player is never claimed.

## Rules quoted
- Ask the routing table which page owns a mechanism before reading any page: a mod reaches the game through four surfaces only, and the command bus is the one sanctioned client-to-server path for anything the engine does not sync [#0888/C/C-only].
- Ship a `42/` tree with `42.x/` overrides beside `common/` and declare dependency order with `mod.info` `require=`: the version folder wins a same-relative-path collision while `common/` supplies everything that folder does not ship [#1073/M/n=2].
- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Wrap every third-party and engine-boundary call in `pcall` and fail soft: an unguarded raise aborts the rest of the handler body it fires in, while the handlers registered behind it still run [#1072/C/snapshot, #0948/M/n=1, #0949/M/n=1].
- Reach every Java member by indexing first and calling second: a nil call never says which member was nil, aborts the body it sits in when unguarded and is session-ending on a debug client, and every Lua file in the experiment mods carries its own guard so that a mod never depends on the harness being installed [#0935/C/C-only].
- Monkey-patch idempotently and keep the original, testing for your own wrapper before you replace the target: that shape is safe under a Lua reload, unwindable, and it composes when two mods wrap the same function [#1067/C/snapshot].

## Also
- docs/platform/jar-research.md — the next source when no page carries the topic (skill `pz-jar-research`).
- docs/platform/harness.md — proving on a live server that the mod loaded and does what it claims (skill `pz-mod-testing`).
- docs/reference/tools.md#mod-lint — the layout lint to run on the mod folder before any boot.
- docs/platform/overview.md#coverage — which topics have a page, the server lifecycle, the sandbox options and the client UI among them, and which are only touched or absent.
