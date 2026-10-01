# Character stats — the registry, the updaters and the tick order
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: the registered character stats and the `Stats` API, the seven updaters the stat hook skips and what each does beyond its stat, and one server update of a player up to the hook; the updaters' rates are `facts/body-and-weight.md` and `facts/endurance-fatigue-sleep.md`, the hook as a Lua surface is `platform/lua-platform.md`, the frame's tail is `platform/server-lifecycle.md` and the push is `platform/mp-model.md`

## Key facts

- `CharacterStat` registers 24 stats in its class initialiser, each with an id, a minimum, a maximum and a default, and fixes the 24-entry `ORDERED_STATS` array in the same initialiser [#2205/C/C-only].
- A stat a mod registers is usable through `get` and `set` but sits outside `ORDERED_STATS`, so no save and no sync carries it [#2211/C/C-only].
- Every `Stats` write passes the stat's own clamp, and no setter for a stat's bounds exists, so endurance and fatigue stay on `[0,1]` [#2208/C/C-only] [#2209/C/C-only].
- The stat update fires the `CalculateStats` hook and, unless it answers true, runs seven updaters in a fixed order: endurance, tripping, thirst, stress, the wake state, morale and fitness [#2724/C/C-only].
- Registering any handler on that hook makes it answer true whatever the handler returns, so the seven are skipped all together or not at all [#2238/C/C-only].
- On a server the fatigue stat is reset to its default on every call unless sleep is both allowed and needed, and the reset runs before the hook, so no handler can stop it [#2723/C/C-only].
- The character's endurance updater and the player's are two separate private methods, and the one the stat update reaches only stamps the last-endurance value and honours the unlimited-endurance cheat [#2214/C/C-only] [#2215/C/C-only].
- The player's endurance model runs earlier in the same update than the hook, so the hook cannot suppress it and a handler's endurance write lands after vanilla's for that tick [#2235/C/C-only].
- The thirst updater adds thirst only on a server, or off a client for the local player, and skips the add while the player is in ghost mode [#0560/M/n=1].
- The fitness updater writes the `FITNESS` stat as the Fitness perk level divided by `5`, minus `1`, and is private [#2223/C/C-only] [#2222/C/C-only].
- On a multiplayer client the player's stat update returns before calling the character's, so the fatigue reset, the hook and the seven updaters run only on the server for players [#2236/C/C-only].
- Each side recomputes its own moodles from its own copy of the stats [#0563].

## How it works

<a id="registry"></a>
### The stat registry and the `Stats` API

The character stats are not a Java enum: they are a registry the stat class fills in its own initialiser, and a character's `Stats` object is a sparse map over that registry.
The registry and the fixed order are built once, so every stat that exists when the class loads is in both, and a stat added later is in the registry only.

The registry as the initialiser builds it, with each stat's bounds, its default and its index in the fixed order that saves and syncs walk [#2205/C/C-only]:

| field | id | min | max | default | `ORDERED_STATS` index |
|---|---|---|---|---|---|
| `ANGER` | `Anger` | 0 | 1 | 0 | 0 |
| `BOREDOM` | `Boredom` | 0 | 100 | 0 | 1 |
| `DISCOMFORT` | `Discomfort` | 0 | 100 | 0 | 2 |
| `ENDURANCE` | `Endurance` | 0 | 1 | 1 | 3 |
| `FATIGUE` | `Fatigue` | 0 | 1 | 0 | 4 |
| `FITNESS` | `Fitness` | −1 | 1 | 0 | 5 |
| `FOOD_SICKNESS` | `FoodSickness` | 0 | 100 | 0 | 6 |
| `HUNGER` | `Hunger` | 0 | 1 | 0 | 7 |
| `IDLENESS` | `Idleness` | 0 | 1 | 0 | 8 |
| `INTOXICATION` | `Intoxication` | 0 | 100 | 0 | 9 |
| `MORALE` | `Morale` | 0 | 1 | 1 | 10 |
| `NICOTINE_WITHDRAWAL` | `NicotineWithdrawal` | 0 | 0.51 | 0 | 11 |
| `PAIN` | `Pain` | 0 | 100 | 0 | 12 |
| `PANIC` | `Panic` | 0 | 100 | 0 | 13 |
| `POISON` | `Poison` | 0 | 100 | 0 | 14 |
| `SANITY` | `Sanity` | 0 | 1 | 1 | 15 |
| `SICKNESS` | `Sickness` | 0 | 1 | 0 | 16 |
| `STRESS` | `Stress` | 0 | 1 | 0 | 17 |
| `TEMPERATURE` | `Temperature` | 20 | 40 | 37 | 18 |
| `THIRST` | `Thirst` | 0 | 1 | 0 | 19 |
| `UNHAPPINESS` | `Unhappiness` | 0 | 100 | 0 | 20 |
| `WETNESS` | `Wetness` | 0 | 100 | 0 | 21 |
| `ZOMBIE_FEVER` | `ZombieFever` | 0 | 100 | 0 | 22 |
| `ZOMBIE_INFECTION` | `ZombieInfection` | 0 | 100 | 0 | 23 |

Endurance runs on `[0,1]` with a default of 1 at index 3, and fatigue on `[0,1]` with a default of 0 at index 4 [#2206/C/C-only].
`Stats.get` reads a sparse map and falls back to the stat's own default, so a stat never written reads its default rather than zero and no stat is ever registered on a `Stats` instance [#2207/C/C-only].
`Stats.set` passes every write through the stat's own clamp before storing it and returns whether the stored value changed [#2208/C/C-only].
The bounds the clamp enforces cannot themselves be moved, which is [a wall](#walls).

A mod can mint a stat of its own through the registration static stated at [the walls](#walls), but the fixed order is not rebuilt for it.
A stat a mod registers is absent from `ORDERED_STATS` and therefore from every save and every sync: both save forms and the per-stat write walk that array, and the stats packet's mask is `1 << index` for a member and zero for a non-member [#2211/C/C-only].
Such a stat is still reset with the others, because the reset-all method iterates the whole registry rather than the fixed order [#2212/C/C-only].
Registering an id that already exists is [a wall](#walls) as well.
Three endurance helpers on `Stats` are hard-coded: the recharging flag is a constant false, and the warning and danger thresholds are constants of 0.5 and 0.25 [#2213/C/C-only].
Where the fixed order meets the wire — the packet's field order — is [the player-stats packet](wire-packets.md#player-stats-packet) [#0564].

<a id="updaters"></a>
### The seven updaters and what each does beyond its stat

The stat update fires the Lua hook and returns when it answers true; otherwise it runs seven updaters in a fixed order — endurance, tripping, thirst, stress, the wake state, morale and fitness — and those seven are the whole of what a takeover handler replaces [#2724/C/C-only].
What makes the hook answer true, and who reaches it at all, is [the hook surface](../platform/lua-platform.md#hooks).
Thirst's and hunger's rates, their trait multipliers and their gates are stated at [the hunger and thirst rates](../facts/body-and-weight.md#hunger-thirst), and endurance's and fatigue's at [the endurance drain](../facts/endurance-fatigue-sleep.md#drain) and [the fatigue accumulation](../facts/endurance-fatigue-sleep.md#fatigue), so the seven formulas a takeover reproduces are all reachable from this section.

The character's endurance updater does nothing but stamp the last-endurance value from the current endurance and, under the unlimited-endurance cheat, reset endurance to its default of 1 [#2215/C/C-only].
It is not the endurance model: the player's model is a separate method the hook never sees, placed in [the tick order](#tick-order).

The tripping updater's only write is the tripping rotation angle, advanced by `0.06` per call while the character is tripping, and nothing in the jar outside `Stats` reads that angle [#2225/C/C-only].

The thirst updater adds thirst only when the process is a server, or is not a client and the character is the local player instance, and it skips the add while the character's player is in ghost mode [#0560/M/n=1].
A takeover that drops the thirst updater drops that ghost-mode gate with it, because the gate lives inside one of the seven updaters the hook skips [#2724/C/C-only] [#0560/M/n=1].
The thirst updater also calls the auto-drink method on every call, after and outside that gate, and is its only call site in the jar, so a registered handler also stops auto-drinking and the `AutoDrink` hook it fires; the method is public on an exposed class, so a takeover can call it itself [#2250/C/C-only].

The stress updater carries no side gate of its own beyond an animal return and relies on the player's stat update for its side; it adds the sound stress at the character's square unless the character is Deaf, with no game-time factor, and adds the bite-or-scratch term once when any part is bitten and once more when any part is scratched [#2220/C/C-only].
It adds the same term once more while the character is infected or fake-infected, and a Hemophobic character adds a term scaled by the character's total blood [#2230/C/C-only].
It is also the only anger write among the seven, while the awake arm of the wake-state updater advances the idle-square timer and resets idleness whenever the character is in combat [#2226/C/C-only].
Its four constants come from the Lua globals table the loader reads: the sound multiplier `0.00002`, the bite-or-scratch term `0.00005`, the Hemophobic term `0.0000003333` and the anger decrease `0.0001` [#2231/C/C-only].

The stress updater as read, one call [#2220/C/C-only] [#2230/C/C-only] [#2226/C/C-only] [#2231/C/C-only]:

```text
animal                    -> return
not Deaf                  -> STRESS += soundStress(square) × StressFromSoundsMultiplier
parts bitten > 0          -> STRESS += StressFromBiteOrScratch × multiplier × deltaMinutesPerDay
parts scratched > 0       -> STRESS += StressFromBiteOrScratch × multiplier × deltaMinutesPerDay
infected or fake-infected -> STRESS += StressFromBiteOrScratch × multiplier × deltaMinutesPerDay
Hemophobic                -> STRESS += totalBlood × StressFromHemophobic × (multiplier ÷ 0.8) × deltaMinutesPerDay
always                    -> ANGER  -= AngerDecrease × multiplier × deltaMinutesPerDay
```

The wake-state updater runs its awake or sleeping path only when the process is a server, or is not a client and the character is the local player instance, so neither path runs on a multiplayer client [#2219/C/C-only].
The character's own sleeping path is an empty method, so a non-player character's stats do not move through it while it sleeps [#2218/C/C-only].
The player's sleeping path writes one field besides the stats — the time-of-sleep advance its restoration gate compares against — and carries no wake-up, no call that sets the asleep flag and no bed release [#2227/C/C-only].

The morale literal is held by three classes only — the stat class, the character class and the book class — so skipping the morale updater reaches no moodle, speed or combat term [#2228/C/C-only].

The fitness updater writes the `FITNESS` stat as the Fitness perk level divided by `5`, minus `1` [#2223/C/C-only].
It does not drive the exercise system, which is the separate `Fitness` object with its own update [#2224/C/C-only].
The updater is private, so Lua cannot call it to refresh the stat [#2222/C/C-only].

The moodle update carries no side gate, so each side recomputes its own moodles from its own copy of the stats [#0563].
A server-side stat write therefore reaches the client's moodle levels once the client's stats copy has it, through [the player-stats push](../platform/mp-model.md#packets).

<a id="tick-order"></a>
### One server update of a player, up to the hook

The two endurance updaters are both private, so they are two separate methods rather than an override pair: the character's is reached from the stat update and the player's from the player's second-stage update [#2214/C/C-only].
A player's update calls only its first stage, which calls the second stage first and, when that returns true, the character update, whose internal update calls the stat update under the character-stats system switch [#2233/C/C-only].
On a dedicated server the second stage takes the remote-player branch, which after the server-gated movement-rate update calls the player's endurance model, or its in-vehicle variant, and returns true, ahead of the `OnPlayerUpdate` trigger in the later local-player path [#2232/C/C-only].
The nutrition update, under the same system switch, and the exercise object's update also run inside the second stage, before the hook [#2234/C/C-only].
Inside the stat update the order is an animal return [#2239/C/C-only], then on a server the fatigue reset unless sleep is both allowed and needed, then the hook [#2723/C/C-only].
The hook therefore cannot suppress the player's endurance model, which has already run for that tick, and a handler that writes endurance writes after vanilla's drain or regeneration [#2235/C/C-only].

The order within one server update of a player, as read [#2233/C/C-only] [#2232/C/C-only] [#2234/C/C-only] [#2723/C/C-only] [#2235/C/C-only]:

```text
IsoPlayer.update
  updateInternal1
    updateInternal2
      Nutrition.update                  (doCharacterStats switch)
      Fitness.update
      updateRemotePlayer true           (the server's path for a player)
        updateMovementRates             (server only)
        IsoPlayer.updateEndurance       (or updateEnduranceWhileInVehicle)
        return true
    IsoLivingCharacter.update -> IsoGameCharacter.update -> updateInternal
      calculateStats                    (doCharacterStats switch)
        animal                                      -> return
        server, sleep not both allowed and needed   -> Stats.reset(FATIGUE)
        TriggerHook("CalculateStats") answers true  -> return
        the seven updaters
```

The frame's tail — `OnTick` and the network manager — is [the server tick order](../platform/server-lifecycle.md#tick-order), and the push that follows it is [the player-stats push](../platform/mp-model.md#packets).
Which side runs the player's endurance model, and for whom it returns early, is [the ownership section](../platform/mp-model.md#ownership).

## Walls and bounds
<a id="walls"></a>

The stat class declares no setter for a stat's minimum, maximum or default, so the `[0,1]` range of endurance and fatigue cannot be widened [#2209/C/C-only].
Registration goes through a compute-if-absent, so registering an id that already exists returns the existing stat and never rewrites its bounds [#2210/C/C-only].
The hook's all-or-nothing answer and its unreadable registrant list are walls of the Lua surface, stated at [the hook surface](../platform/lua-platform.md#hooks).
Not covered: the sound-stress source function and the awake path's stress decay, the awake and sleeping paths' own rates (handed off above), a non-player living character's use of the updaters beyond its empty sleeping path, what sets the character-stats system switch, whether Kahlua can call the registration static and what a mod-registered stat does across a save and reload, and the per-moodle update bodies — none of them was read here.

## Open
<a id="open"></a>

- Whether any registered `Hook.CalculateStats` handler, whatever it returns, skips the seven updaters on the server, and whether the hook fires on both sides — settled by a handler added and removed through the hook's own add and remove, reading thirst against the macro drain with and without a registrant; -> [X32](../areas/open-questions.md#x32) [#2100/C/open].
- Whether a handler that reproduces the seven skipped updaters from the library's formulas tracks vanilla's stat trajectory stat by stat over several game-hours — settled by two boots of one fixture, with no handler and with the reproducing handler, sampling the seven stats hourly against a per-stat band; the stress arm rests on the terms at [the updaters](#updaters) and is a first measurement of them; -> [X34](../areas/open-questions.md#x34) [#2081/C/open].
- Whether a handler's endurance write is the last before the player-stats push, as the tick order reads — settled by a sentinel endurance written each tick and read in client-first pairs at rest and running, beside an arm with the handler removed; -> [X35](../areas/open-questions.md#x35) [#2082/C/open].
- Whether a second registrant of the hook changes what the first one causes — settled by thirst across one handler, that handler with a second, the second alone, and no handler; -> [X46](../areas/open-questions.md#x46) [#2086/C/open].
- Decision: whether a takeover handler integrates endurance from its own stored value or from the stat it reads back — the player's endurance model runs outside the hook, earlier in the same update [#2235/C/C-only], on the side [the ownership section](../platform/mp-model.md#ownership) states.
- Decision: which of the updaters' non-stat side effects a takeover reproduces and which it drops — the last-endurance stamp [#2215/C/C-only], the anger decay and the idle-square timer [#2226/C/C-only], the time-of-sleep advance [#2227/C/C-only], the thirst ghost-mode gate [#0560/M/n=1], the auto-drink call [#2250/C/C-only] and the fitness stat's refresh [#2223/C/C-only].
- Decision: whether the mod keeps a nutrient in a stat it registers or in its own store — a registered stat answers `get` and `set` and is never saved or synced [#2211/C/C-only].

## See also

- [`../platform/lua-platform.md`](../platform/lua-platform.md#hooks) — the hook surface: what makes it answer true, who reaches it, and what Lua can read of it.
- [`../platform/mp-model.md`](../platform/mp-model.md#ownership) — which side owns each stat, and the push that carries them.
- [`wire-packets.md`](wire-packets.md#player-stats-packet) — the player-stats packet's field order over the fixed stat order.
- [`body-and-weight.md`](body-and-weight.md#hunger-thirst) — the hunger and thirst rates the thirst and wake-state updaters apply.
- [`endurance-fatigue-sleep.md`](endurance-fatigue-sleep.md#drain) — the endurance model and the fatigue and sleep rates.
- [`../platform/server-lifecycle.md`](../platform/server-lifecycle.md#tick-order) — the rest of the server frame after the hook.
- [`../areas/open-questions.md`](../areas/open-questions.md#x32) — the experiments the open rows point at.
