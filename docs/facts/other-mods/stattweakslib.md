# Stat Tweaks Lib
Verified against 42.21.0 (4a0e9546ec) · 2026-10-08 · scope: whether Build 42.21 loads the Stat Tweaks Lib stat library, what its one client file does and why it raises, and why it cannot meet a server mod; the discovery gate, the server's `client/` skip and the raise semantics are handed off to the platform pages.

## Key facts
<a id="techniques"></a>

- Read a stat through `get(CharacterStat)` on this build: the named getters a Build 41 library calls are gone, and an unguarded call to one raises [T1101.27].
- Do not rescale another writer's change by diffing a stat against its last read: the library multiplies every writer's change, a server's per-minute write included, by its own modifiers [T1101.26].

## How it works

<a id="what-it-does"></a>
### What it does

Stat Tweaks Lib lets other mods register gain, loss and maximum modifiers for nine stats and queue gradual changes to them.
Workshop item `3415375593` ships one Lua file, `42.0/media/lua/client/StatTweaksMain.lua`, under the mod id `LazoloStatTweaksLib`, in a `42.0/` folder whose `mod.info` sets no `versionMin`, beside an empty `Common` folder [T1101.24].
Build 42.21 discovers and loads Stat Tweaks Lib: `42.0` is the one entry of its folder whose parsed version lies from 42.0 up to the running build, so the resolver picks it and its `mod.info` is there [T1101.25].
It registers `LazoloLibMain` on `OnPlayerUpdate`, which keeps closures over the Java getters and setters of nine stats in `player:getModData().StatsLib`, and each update multiplies every stat's change since its last read by the gain or loss modifiers other mods registered there and writes the stat back clamped [T1101.26].

<a id="raise"></a>
### Why it raises on 42.21

On 42.21 it raises on every local-player update before it writes any stat: each of its nine getters names a member the jar lacks, such as `Stats:getEndurance`, where `Stats` carries `get(CharacterStat)`, so its first read raises, and because that read never stores a value the same read raises again on the next update [T1101.27].
A debug client parks on the first such raise ([#0954/M/n=2], [`../../platform/lua-platform.md#debug-break`](../../platform/lua-platform.md#debug-break)), while a release client aborts only the raising handler and keeps running the handlers behind it ([#3317/M/n=1], [`../../platform/lua-platform.md#raises`](../../platform/lua-platform.md#raises)).
Its gradual-change path calls `LazDir`, which nothing in the file defines [T1101.28].
That path runs only once another mod has queued a change, so it is a second raise waiting behind the first.

<a id="collisions"></a>
### How it collides

Stat Tweaks Lib never runs on a dedicated server, its one file being under `client/`, and it touches no `ZomboidGlobals` field, no item and no global modData; on a client its writes of a server-owned stat would be erased by the next player stats packet [T1101.29].
Nothing it does reaches a server's rates or its per-minute writes, so a server mod needs no guard against it; the cost it carries is a client log line on every update.

## Walls and bounds

Every line on this page is a reading of the installed copy's code and of the 42.21 jar on 2026-10-08; the raise is read off the code and the member lists and was never observed [T1101.27].

<a id="licence"></a>
### Licence

None of its three files carries a licence text, and its `mod.info` names no author [T1101.30].
With no grant the default is all rights reserved: this repository learns from the code and copies none of it.

Not covered: the Workshop page and its terms, any mod that registers modifiers with it, and a booted reading of the raise on either client kind.

## Open
<a id="open"></a>

- Whether the raise reads as one trace per update on a release client — settled by a client session with the mod loaded and the log counted; no `X` id.

## See also

- [`../../platform/lua-platform.md#raises`](../../platform/lua-platform.md#raises) — what an unguarded raise aborts.
- [`../../platform/mp-model.md#routes-client-to-server`](../../platform/mp-model.md#routes-client-to-server) — why a client's stat write does not last.
- [`statsapi.md`](statsapi.md) — the other stat library read the same day, which 42.21 never discovers [T1101.19].
- [`catalog.md#status`](catalog.md#status) — the Workshop page reading and the code-read status of this and the other neighbours.
