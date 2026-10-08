# StatsAPI
Verified against 42.21.0 (4a0e9546ec) · 2026-10-08 · scope: whether Build 42.21 finds and runs the StatsAPI stat library, what its code would do if it ran, and why it cannot meet a server mod; the discovery gate and the server's `client/` skip are handed off to the platform pages.

## Key facts
<a id="techniques"></a>

- Save a `ZomboidGlobals` value before zeroing it, so the vanilla number stays readable to the mod and to anyone it publishes it to [T1101.20].
- Ship a Build 42 mod with a `common/` or a version folder: a root `mod.info` alone is a Build 41 layout that 42.21 never discovers [T1101.19, T1101.42].

## How it works

<a id="what-it-does"></a>
### What it does

StatsAPI is a Build 41 library that recalculates the character's stats in Lua [T1101.18, T1101.20].
Workshop item `2997722072` ships the mod `StatsAPI`, modversion 0.4.15 by albion with `versionMin=41.78.16`, as a root `mod.info` beside `media/`, with no `common/` and no version folder [T1101.18].
Its stat code is a Lua rewrite of the stat update under `client/`: it registers `Hook.CalculateStats`, reads `HungerIncrease`, `ThirstIncrease` and `FatigueIncrease` from `ZomboidGlobals`, and at file scope saves then zeroes `BoredomIncrease`, `BoredomDecrease` and `UnhappinessIncrease` [T1101.20].
It calls Build 41 members the 42.21 jar lacks: `getStressFromCigarettes`, a name no class carries, and `HasTrait` with a string, where the character carries only `hasTrait` overloads taking `CharacterTrait` [T1101.21].
So its stat code names members this build lacks, and the game never finds the folder that holds it [T1101.21, T1101.19].

<a id="discovery"></a>
### Why 42.21 never runs it

Build 42.21 never discovers StatsAPI: no entry of its folder parses as a version from 42.0 up to the running build, so the version-dir resolver returns `42.0`, and neither `common/mod.info` nor `42.0/mod.info` exists there, so a server listing it in `Mods=` cannot find it [T1101.19].
The resolver's fallback is `42.0`, not `42` ([#3505/C/C-only], [`../../platform/mod-anatomy.md#version-dirs`](../../platform/mod-anatomy.md#version-dirs)), and the root `mod.info` is never tested ([T1101.42], [`../../platform/mod-anatomy.md#mod-discovery`](../../platform/mod-anatomy.md#mod-discovery)).

<a id="collisions"></a>
### How it collides

Undiscovered, StatsAPI shares nothing with a server mod on 42.21, and a port in the same layout still could not contest a server's stat hook, because a dedicated server never runs `client/` Lua [T1101.22].
A port's client-side stat writes would also be erased by the next player stats packet ([#0568/M/n=2], [`../../platform/mp-model.md#routes-client-to-server`](../../platform/mp-model.md#routes-client-to-server)).
Its file-scope save is the technique of the first key fact: it keeps each rate it zeroes in a Lua copy, so the vanilla number stays readable once `ZomboidGlobals` holds zero [T1101.20].

## Walls and bounds

Every line on this page is a reading of the installed copy's code and of the 42.21 jar on 2026-10-08; nothing was booted [T1101.21].

<a id="licence"></a>
### Licence

None of its 32 files carries a licence text, and its `mod.info` names the author only [T1101.23].
With no grant the default is all rights reserved: copying its code into another mod needs the author's permission.

Not covered: its moodle UI, its sleep handling and its over-time effects beyond a read for stat writes; whether its author has published a separate version for this build; and the Workshop page and its terms.

## Open
<a id="open"></a>

- Whether a StatsAPI for this build exists under another Workshop id — settled by a Workshop search for the author's items; no `X` id.

## See also

- [`../../platform/mod-anatomy.md#mod-discovery`](../../platform/mod-anatomy.md#mod-discovery) — the discovery gate that skips this folder.
- [`../../platform/lua-platform.md#events`](../../platform/lua-platform.md#events) — which VM runs which Lua tree, and the server's `client/` skip.
- [`stattweakslib.md`](stattweakslib.md) — the other stat library read the same day, which 42.21 does load [T1101.25].
- [`catalog.md#status`](catalog.md#status) — the Workshop page reading and the code-read status of this and the other neighbours.
