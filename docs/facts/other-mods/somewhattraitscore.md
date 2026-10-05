# SomewhatTraitsCore — a second writer of the player's calories
Verified against 42.20.4 (b0bbce05d5) · 2026-10-04 · scope: one workshop mod read for the one surface it shares with a nutrition overhaul — the adaptive-metabolism handler that writes the player's calorie store on the server — and measured once beside vanilla under a co-boot; the corpus counts belong to [catalog.md](catalog.md#sweep), the calorie store and its drain to [nutrition-core.md](../nutrition-core.md#macro-effects) and the push that mirrors it to [wire-packets.md](../wire-packets.md#player-stats-packet).

## Key facts

- The adaptive-metabolism handler's write reaches the server's calorie store under a co-boot: a held trait moved calories in steps of a third of a kilocalorie, one every five seconds, up below 77 kg and down above 83 kg [#2091/M/n=1].
- Inside its 77-to-83 kg band the handler writes nothing, so a character in the band is the mod absent for this store [#2762/M/n=1].
- The step is fixed when the file loads, from the day length read once at file scope, and the selector writes each online player at most once every five seconds whatever the player count [#2764/C/C-only].
- Read a trait-held arm only against a trait-absent arm at the same weight: vanilla's own idle drain scales with weight over 80, which dwarfs the handler's slope [#2763/M/n=1].

## How it works

The mod ships three folders in one Workshop item, `3498347699`: `SomewhatTraitsCore`, the server and client code; `SomewhatTraits`, which registers the traits; and `SomewhatTraitsSkills`, so a server or a test profile names each by its id rather than by the item [#1617/C/snapshot].
The live tree on `42.20.4` is `42.15/` for all three; this page read it on 2026-10-04, its server file dated 2026-08-12 on disk.
Its patching surface is wide — 56 `function IS…:` headers and 66 save-and-wrap sites [#1624/C/snapshot] — and 24 of its `OnTick` registrations sit in its one server file [#2581/C/snapshot]; only the calorie write touches the nutrition store, and it is the corpus's only player macro write [#1588].

<a id="what-it-does"></a>
### What it does

`SomewhatTraits` registers each trait as `CharacterTrait.register("SWTraits:" .. name)`, so the adaptive-metabolism trait's registry id is `SWTraits:SWAdaptiveMetabolism`, and its name in a trait list is the id's path alone, as with any registered trait [#2761/M/n=1].
The server file returns at once on a client, then caches the sandbox day length at file scope.
A selector `OnTick` handler clears its chosen player on every tick and, once five seconds divided by the online player count have passed, picks the next player in rotation; the adaptive-metabolism handler, registered after it on the same event, runs in that tick on that player [#2764/C/C-only].
With the trait held, it adds `60 / dayLength × 0.5` calories while weight is under 77 kg and calories under 3600, subtracts the same while weight is over 83 kg and calories over -2100, and multiplies the step by five while the player runs or sprints [#1588] [#2764/C/C-only].
At the fixture's 90-minute day the step is a third of a kilocalorie, which is the size the run measured [#2091/M/n=1].
Because the day length is read once at file load, a running server whose day length changes keeps the old step until its Lua reloads [#2764/C/C-only].

<a id="mp"></a>
### Multiplayer behaviour

The write is a server-side `setCalories` on the player's own Nutrition, so it lands in the authoritative store and reaches the client on the ordinary once-a-second push ([#1633/C/inference], [mp-model.md](../../platform/mp-model.md#ownership)).
One session of six sixty-second idle arms in weight-matched pairs measured it [#2091/M/n=1]:

| weight | trait absent, kcal/s | trait held, kcal/s | held minus absent | steps in the held arm |
|---|---|---|---|---|
| 75 kg | -0.2404 | -0.1749 | +0.0655 | 12, 0.332 to 0.334 kcal, mean spacing 5.01 s |
| 85 kg | -0.2724 | -0.3388 | -0.0665 | 12, -0.333 to -0.336 kcal, mean spacing 5.09 s |
| 80 kg | -0.2567 | -0.2566 | +0.0001 | none |

Every step-to-step spacing in the two writing arms brackets five seconds, and none of the three trait-absent arms showed a single step, so the steps are the handler's and the smooth slope beneath them is vanilla's [#2091/M/n=1].
The 80 kg pair is the band's control: the held arm matched its twin to a ten-thousandth of a kilocalorie per second [#2762/M/n=1].
The three trait-absent slopes stand in the ratio of the weights over 80 to within two parts in a thousand, which is vanilla's idle drain doing what its weight term says, and the reason no pair is read across weights [#2763/M/n=1].
The handler's correction is about a quarter of vanilla's idle drain at either edge of the band: it holds a character near the band over game-days, not over a meal.

## Walls and bounds
<a id="walls"></a>

- The run held one idle player at one day length, so the rotation across several players and the five-fold running step are code readings rather than measurements [#2764/C/C-only].
- The band's edges were not probed: the arms sat at 75, 80 and 85 kg, and the 3600 and -2100 calorie caps were never approached [#2762/M/n=1].
- The workshop tree drifts under Steam's own updates, so every reading of the code here is dated to 2026-10-04 ([lessons.md](../../platform/lessons.md#corpus-drift)).

Not covered: the mod's other traits, its patching of the timed actions, its client file and its command bus were not read for this page; no single-player process was booted; and no mod but the harness and the trait-grant probe ran beside it, so its interaction with another writer of the calorie store is outside what this page measured.

## Open
<a id="open"></a>

- The design must decide whether it writes over this handler or leaves the store to it, because the handler writes the same server-side calorie store a nutrition overhaul would own, a third of a kilocalorie every five seconds per player outside its band [#2091/M/n=1] [#2762/M/n=1].

## See also

- [catalog.md](catalog.md#sweep) — where the mod sits in the corpus, and the sweep that found its calorie write.
- [simplestatus.md](simplestatus.md#mp) — the client-side reader of the same store, measured tracking the mirror this write reaches.
- [../nutrition-core.md](../nutrition-core.md#macro-effects) — the calorie store and the drain this handler adds to.
- [../wire-packets.md](../wire-packets.md#player-stats-packet) — the push that carries the written store to the client.
- [../../areas/packaging.md](../../areas/packaging.md#resident-stack) — the resident stack this mod sits in, and what its write asks of a nutrition overhaul.
- [../../platform/mp-model.md](../../platform/mp-model.md#ownership) — why a server-side write sticks and a client-side one would not.
