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
- Intoxication decays on the body-damage tick, by its reduction value times the game-time multiplier on every server update, ahead of the `CalculateStats` hook and outside any Lua hook, so a handler's intoxication write is the later one in the update [#2918/C/C-only] [#2921/C/C-only].
- DISCOMFORT is relaxed toward vanilla's own target on the server alone, awake, at time speed 1, with a half-life of about 2.9 real seconds, and reaches the client on the once-a-second player-stats packet, so a once-a-minute server floor does not hold there [#3603/C/C-only] [#3606/C/arith.] [#3600/C/C-only] [#3607/C/inference].
- On 42.21 nothing in the engine or the shipped Lua writes SICKNESS in play, so it stays at its default of 0 unless a mod or the debug menu writes it [T11407.1] [T11407.2] [T11407.3].
- NICOTINE_WITHDRAWAL rises on the server alone, for an awake Smoker, falls only at a smoke, and is read only as stress, so vanilla's withdrawal moves no hunger [T11407.4] [T11407.5] [T11407.6] [T11407.9].

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
`Stats.add`, `remove` and `reset` all write through `set`, so each clamps once to the stat's bounds and returns whether the stored value changed, and `add` sums in float. [#2800/C/C-only]
Where the fixed order meets the wire — the packet's field order — is [the player-stats packet](wire-packets.md#player-stats-packet) [#0564].

<a id="updaters"></a>
### The seven updaters and what each does beyond its stat

The stat update fires the Lua hook and returns when it answers true; otherwise it runs seven updaters in a fixed order — endurance, tripping, thirst, stress, the wake state, morale and fitness — and those seven are the whole of what a takeover handler replaces [#2724/C/C-only].
What makes the hook answer true, and who reaches it at all, is [the hook surface](../platform/lua-platform.md#hooks).
On a live dedicated server the skip is whole and indifferent to the handler's answer: with a handler returning true alone, the same handler beside one returning false, and the false-returning handler alone, thirst read the same value to the last bit across about 32 game-minutes in each arm while the calorie store still drained, each handler's server count rose by about 245 calls, and thirst rose again at the vanilla rate once neither was registered [#2086/M/n=1].
Against an overlay boot of the same fixture over eight game-hours, a takeover handler reproducing the seven updaters held thirst within 7e-6 per game-hour of the overlay boot's in seven of the eight hours, with hour 5, an hour the harness sleep command covered, 4.02e-4 apart and every hour within 2 % of vanilla's 0.0288, and hunger within 2 % in every hour, the hunger residual following the level the two boots started from, with no handler failure logged [#2809/M/n=1].
Idleness left its pre-written band in four of those hours, two of them consecutive, so that prediction is falsified as graded; every out-of-band hour holds the clamp at 1 or the reset to 0 on movement at a time that differs between the boots, and the one hour in which idleness rose unclamped throughout read 0.600005 per game-hour on both [#2750/M/n=1].
Stress and anger read 0 at every hourly sample of both boots, standing idle with no zombie, wound, infection or sound, so that session gave the stress terms no live measurement [#2751/M/n=1].
Thirst's and hunger's rates, their trait multipliers and their gates are stated at [the hunger and thirst rates](../facts/body-and-weight.md#hunger-thirst), and endurance's and fatigue's at [the endurance drain](../facts/endurance-fatigue-sleep.md#drain) and [the fatigue accumulation](../facts/endurance-fatigue-sleep.md#fatigue), so the seven formulas a takeover reproduces are all reachable from this section.
From hunger 0, vanilla's awake idle hunger with the FOOD_EATEN moodle down follows 1 - e^(-kt) with k = 9.6e-6 per game-second at StatsDecrease 3, so 1 - HUNGER halves every ln 2 / k = 20.06 game-hours. [#3342/C/arith.]
Every per-update rise of HUNGER, THIRST and FATIGUE in the seven updaters is scaled by one of seven `ZomboidGlobals` statics — `thirstIncrease`, `thirstSleepingIncrease`, `hungerIncrease`, `hungerIncreaseWhenWellFed`, `hungerIncreaseWhileAsleep`, `hungerIncreaseWhenExercise` and `fatigueIncrease` — and the only writer of each is `ZomboidGlobals.Load`, which copies it once from the Lua table key of the same name. [#3362/C/C-only]
Measured live with the six non-zero rise rates zeroed and no writer, a player's HUNGER, THIRST and FATIGUE stayed bit-for-bit at 0.3, 0.2 and 0.1 across 20 server reads spanning 0.5161 game hours awake, while STRESS fell 0.058332 over the 1944.39 game-seconds between the two whole-stat reads bracketing the window, against the 0.058332 the awake updater's stress decay predicts. [#3368/M/n=1]
With `HungerIncreaseWhenExercise` zeroed, HUNGER held while the server's copy of a sprinting player read the run flag: measured live over a 15 s `player.sprint` leg, the server read `IsRunning` and `isSprinting` true on 11 of the leg's 188 per-tick samples, 8 of them with `isPlayerMoving` true, while HUNGER read 0.3 at every one of the arm's 1040 per-tick samples and all 36 writer deltas were 0 [#3384/M/n=1].
No Lua route reaches one character's stat update alone: `calculateStats` is protected on `IsoGameCharacter` and `IsoPlayer`, `updateStats_WakeState` is protected and `updateEndurance`, `updateTripping`, `updateThirst`, `updateStress`, `updateMorale` and `updateFitness` are private, so the nearest public route is the whole character `update()` [#3385/C/C-only].
With no `CalculateStats` handler registered, vanilla's decay took a PANIC of 0.5, written once a game minute, to about 0.32, 0.14 and 0 in three ticks at `DayLength` 1, falling 0.17969 a tick over 44 falls (0.17889 to 0.18069); with `time.multiplier` 0.1674 (37 or 38 ticks a game minute) it fell 0.030086 a tick over 336 falls (0.029987 to 0.030320), so about 1.12 a game minute at either clock. [#3392/M/n=1]

At a realistic target the decay stays linear: a PANIC of 10 written once a game minute fell 0.17916 a tick at `DayLength` 1 and 0.030061 a tick with `time.multiplier` 0.1674, and read 8.7444 to 8.9287 and 8.8560 to 8.8921 just before each write [#3400/M/n=1]. A PANIC of 6.5 written the same way dropped under 6, the first moodle threshold, in every gap at both spacings [#3401/M/n=1]. The `OnTick` read carrying the write's tick count sits one tick's fall above the value the `EveryOneMinute` handler reads before writing, so a once-a-minute write's floor is the target less the fall per tick times the ticks in the gap [#3402/M/n=1].

The character's endurance updater does nothing but stamp the last-endurance value from the current endurance and, under the unlimited-endurance cheat, reset endurance to its default of 1 [#2215/C/C-only].
It is not the endurance model: the player's model is a separate method the hook never sees, placed in [the tick order](#tick-order).

`Stats.getLastEndurance` has no caller in the jar and no vanilla Lua file names it, so the last-endurance stamp has no vanilla reader. [#2791/C/C-only]
The unlimited-endurance test is `isUnlimitedEndurance()`, public, over `PlayerCheats`, which is not exposed. [#2792/C/C-only]

The tripping updater's only write is the tripping rotation angle, advanced by `0.06` per call while the character is tripping, and nothing in the jar outside `Stats` reads that angle [#2225/C/C-only].

The tripping angle is readable and writable from Lua through the public `Stats` getters and setters. [#2790/C/C-only]

The thirst updater adds thirst only when the process is a server, or is not a client and the character is the local player instance, and it skips the add while the character's player is in ghost mode [#0560/M/n=1].
A takeover that drops the thirst updater drops that ghost-mode gate with it, because the gate lives inside one of the seven updaters the hook skips [#2724/C/C-only] [#0560/M/n=1].
The thirst updater also calls the auto-drink method on every call, after and outside that gate, and is its only call site in the jar, so a registered handler also stops auto-drinking and the `AutoDrink` hook it fires; the method is public on an exposed class, so a takeover can call it itself [#2250/C/C-only].

The stress updater carries no side gate of its own beyond an animal return and relies on the player's stat update for its side; it adds the sound stress at the character's square unless the character is Deaf, with no game-time factor, and adds the bite-or-scratch term once when any part is bitten and once more when any part is scratched [#2220/C/C-only].
It adds the same term once more while the character is infected or fake-infected, and a Hemophobic character adds a term scaled by the character's total blood [#2230/C/C-only].
It is also the only anger write among the seven, while the awake arm of the wake-state updater resets idleness to 0 whenever the character is in combat, more than zero very-close zombies or at least three chasing, `isInCombat` being private, and advances the idle-square timer by `multiplier × deltaMinutesPerDay` per update while the square is unchanged and the timer is at most 3600, resetting it to 0 on a square change, the updater being private with no setter, so Lua cannot advance it [#2226/C/C-only, #2777/C/C-only, #2779/C/C-only].
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

The awake arm of the wake-state updater, as read, is the one place stress, idleness and the idle-square timer move together.
The awake updater writes stress, fatigue, hunger, idleness and the idle-square timer and nothing else. [#2781/C/C-only]
Awake, stress falls per update by `StressDecrease × multiplier × deltaMinutesPerDay`, with no StatsDecrease, trait or moodle term. [#2772/C/C-only]
Idle and on a square, idleness rises by `IdleIncrease × multiplier × deltaMinutesPerDay` once the idle-square timer reaches 1800 on an unchanged square and, independently, by a third of that indoors; not idle and not sitting, it falls by `IdleDecrease × multiplier × deltaMinutesPerDay`. [#2778/C/C-only]
The idle-square timer is read only by the awake updater and by `BodyDamage.UpdateBoredom`, so a takeover that skips the wake-state updater freezes the timer boredom reads. [#2780/C/C-only]

The morale literal is held by three classes only — the stat class, the character class and the book class — so skipping the morale updater reaches no moodle, speed or combat term [#2228/C/C-only].

The morale updater adds `0.5 + (0.5 − ns) × 1e-4` while stress plus nicotine withdrawal is below 0.5 and 0 otherwise, so it pins morale at 1 and never lowers it. [#2789/C/C-only]

The fitness updater writes the `FITNESS` stat as the Fitness perk level divided by `5`, minus `1` [#2223/C/C-only].
It does not drive the exercise system, which is the separate `Fitness` object with its own update [#2224/C/C-only].
The updater is private, so Lua cannot call it to refresh the stat [#2222/C/C-only].

The moodle update carries no side gate, so each side recomputes its own moodles from its own copy of the stats [#0563].
A server-side stat write therefore reaches the client's moodle levels once the client's stats copy has it, through [the player-stats push](../platform/mp-model.md#packets).

On a dedicated server the character-action stack of a connected player is empty while its client runs a timed action, so `Nutrition.updateCalories` on the server never sees the action's calorie modifier [#2878/M/n=1].

<a id="tick-order"></a>
### One server update of a player, up to the hook

The two endurance updaters are both private, so they are two separate methods rather than an override pair: the character's is reached from the stat update and the player's from the player's second-stage update [#2214/C/C-only].
A player's update calls only its first stage, which calls the second stage first and, when that returns true, the character update, whose internal update calls the stat update under the character-stats system switch [#2233/C/C-only].
On a dedicated server the second stage takes the remote-player branch, which after the server-gated movement-rate update calls the player's endurance model, or its in-vehicle variant, and returns true, ahead of the `OnPlayerUpdate` trigger in the later local-player path [#2232/C/C-only].
Measured live, an `OnPlayerUpdate` handler registered by a server-side Lua file never recorded the connected player across 2903 armed ticks in seven windows on two boots, while the same file's `OnTick` handler read the player at every tick [#2959/M/n=1].
The nutrition update, under the same system switch, and the exercise object's update also run inside the second stage, before the hook [#2234/C/C-only].
Inside the stat update the order is an animal return [#2239/C/C-only], then on a server the fatigue reset, which reads `ServerOptions.sleepAllowed` and `ServerOptions.sleepNeeded` and runs unless both are true, then the hook [#2723/C/C-only, #2793/C/C-only].
The hook therefore cannot suppress the player's endurance model, which has already run for that tick, and a handler that writes endurance writes after vanilla's drain or regeneration [#2235/C/C-only].
At rest on a live server the push carries the handler's endurance write and not the value the player's model wrote earlier in the update: with a takeover handler writing 0.4242 every update, the client read 0.4242 to float precision at sixteen client-first pairs while vanilla's resting regeneration, read once the sentinel was cleared, ran at about 0.067 per game-hour, about 1.8e-4 per handler call; no pair was taken while running [#2753/M/n=1].

The order within one server update of a player, as read [#2233/C/C-only] [#2232/C/C-only] [#2234/C/C-only] [#2723/C/C-only] [#2235/C/C-only] [#2921/C/C-only]:

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
      BodyDamage.Update                 (doCharacterStats switch; the intoxication decay)
      calculateStats                    (doCharacterStats switch)
        animal                                      -> return
        server, sleep not both allowed and needed   -> Stats.reset(FATIGUE)
        TriggerHook("CalculateStats") answers true  -> return
        the seven updaters
```

Intoxication is the one stat in this section whose decay runs on the body-damage tick rather than in the stat update.
`BodyDamage.Update` removes its reduction value times the game-time multiplier from INTOXICATION on every call, with no day-length factor, after its return on a client for a live player, and it calls no Lua hook, so in multiplayer the decay runs on the server only and no handler can skip it [#2918/C/C-only].
The internal update calls `BodyDamage.Update` before the stat update, so the decay lands before the hook in the same update and a handler's intoxication write is the later one [#2921/C/C-only].
The constructor sets the reduction value to 0.0042 and the increase value to 400, two private fields behind public getter and setter pairs [#2919/C/C-only].
Nothing else in the jar or the shipped Lua sets the reduction value and no save or load method names it, so a value a mod sets is gone after a reload [#2920/C/inference].
In game time the decay is 0.504 times the day length in real minutes per game-hour, about 30.24 per game-hour on the 60-minute default day and 45.36 on a 90-minute day, so 100 intoxication clears in about 3.3 game-hours on the default day [#2922/C/arith.].
Measured live, the decay runs at that rate: INTOXICATION written to 40 on the server fell 0.20123 per wall second and 7.5599 per game hour over 55.7 s at DayLength 1, the multiplier reading 4.781 to 4.799, against the 7.56 per game hour the reading predicts for that day length [#2951/M/n=1, #2922/C/arith.].
Two writers raise the stat at the drink and at the eat.
The fluid writer adds 400 times the alcohol it is handed, times 1.1 above 0.8 hunger and 1.25 between 0.6 and 0.8, and calls four pill effects on the character [#2923/C/C-only].
The food writer adds 400 times a rescaled fraction, quartered for a beer or low-alcohol item, times 1.25 above 0.8 hunger and 1.1 above 0.6, and calls the same four pill effects [#2924/C/C-only].
What the drink path hands its writer is [the fluid path's](eating-pipeline.md#fluid-path).
Measured live, a 0.3-litre can of beer drunk through the game's drink action raised INTOXICATION as the can emptied, 0.630 with 0.244 litres left, 2.703 at 0.115 and 5.054 with the can empty 4.2 s after the first read, to a per-tick peak of 5.0947 at HUNGER 0.46, and the stat then read 0.0914 24.7 s after the 5.054 read and 0 at the next [#2950/M/n=1].

Panic, boredom, unhappiness and food sickness are driven by three more body-damage sub-updaters, which run in the same tick before the hook and which the hook never skips.
None of the three sets its stat to a level of its own: each adds or removes an amount from the stored value or resets the stat to its default on a named condition, so a value a `CalculateStats` handler writes after `BodyDamage.Update` is the base the next update's change starts from [#3017/C/inference].
The panic updater counts the zombies newly in view since its last call, resets PANIC for a Desensitized character, and otherwise raises PANIC for new sightings or lets it decay [#3013/C/C-only].
The rise is 7 per newly visible zombie, halved in a vehicle and scaled by the beta-blocker and the Cowardly, Brave and Desensitized traits, and the decay removes 0.06 times the thirty-FPS multiplier plus the months survived (at most 5), doubled asleep [#3014/C/C-only].
The boredom updater does nothing for a sleeping player, otherwise moves BOREDOM up or down by its two rates according to idleness, speech, company, business, a vehicle and drink, and resets it whenever PANIC is above 5 [#3015/C/C-only].
The same updater only ever raises UNHAPPINESS: by 0.0005 times the BORED moodle level per multiplier unit while that moodle is at level 2 or more, and by half that times the STRESS moodle level while stress is at level 2 or more, neither while reading [#3016/C/C-only].
Across the body-damage, character, player and stats classes the only passive fall of UNHAPPINESS is the antidepressant's, while a pill's effect lasts [#3033/C/inference].
The illness updater adds corpse sickness to FOOD_SICKNESS while the decaying-corpse option is on and that sickness is above zero, and otherwise removes 0.0015 per multiplier unit from FOOD_SICKNESS only while POISON is at its minimum [#3018/C/C-only].
Measured live, a POISON value written on the server held and decayed at the rate [the poison section](health-surfaces.md#poison-infection) states: written to 8, it fell 1.80001105587019 per game hour while FOOD_SICKNESS rose 5.400028375716543 per game hour, the poison and sickness damage tags never firing, and the client's copy read the server's values [#3036/M/n=1].
The poison health drain waited for the sickness: at POISON about 24 with FOOD_SICKNESS 11 to 13 no POISON damage tag fired in 100 ticks, and with FOOD_SICKNESS written to 24 the server's health held steady for five reads and then fell, about when FOOD_SICKNESS passed 25, while the tag fired 538 times in 600 ticks [#3037/M/n=1].
FOOD_SICKNESS written to 30 at POISON 0 decayed, from 29.820615768432617 to 28.763460159301758 between two server reads [#3038/M/n=1].
The two sides' FOOD_SICKNESS copies read alike at 30, 60 and 95, and at 95 the SICK damage tag fired 287 times in 300 ticks; the SICK moodle levels themselves were not read [#3039/M/n=1].
A PANIC and UNHAPPINESS write made by an `OnTick` handler on every server tick, outside the stat hook, survived each update: UNHAPPINESS rose the written 0.5 per tick and stayed at 100 after the writes stopped, while PANIC rose 0.32044067796610165 per tick and fell once they stopped [#3048/M/n=1].
The first direct per-tick reading of the decay, agreeing with the arithmetic 0.17956 of the row above, took PANIC from 19 to 11.099 over 44 per-tick samples, 0.17956818181818182 a tick [#3116/M/n=1].
The client's copies of the two trailed the server's by up to about a second [#3049/M/n=1].
With the drunk-reduction value written to 0 the decay stops: INTOXICATION written to 40 read 40 on both sides for 0.65 game hours, over which the default value removes about 4.9 [#3054/M/n=1].
A beer drunk at that setting still added the drink writer's full amount, 400 times 0.05 times 0.3 litres, taking the stat from 40 to 46, where it then stayed [#3055/M/n=1].
A write made inside the `CalculateStats` handler is the later write against the decay, as the order reads: with the reduction back at its default, INTOXICATION written to 25 in the handler on every update read 25 at every kept per-tick sample and on the client, and fell once the writes stopped [#3056/M/n=1].
On a server with sleep neither allowed nor needed, a FATIGUE of 0.42 written in the handler after the reset read 0.42 on the server and on the client for as long as it was written [#3057/M/n=1].
On the same server an `OnTick` write of 0.42, outside the player update, reached the client as well, while the server's own reads between frames gave the reset value of about 1e-4; that the push carries what stands at the frame's tail, after `OnTick`, is an inference from that pair [#3058/M/n=1].
A takeover handler's endurance write, folded every tick, reached the owning client as written: one client copy equalled the server's value read mid-regeneration a push earlier [#3079/M/n=1].
A drink action's per-sip INTOXICATION increment lands outside the hook and stands for one update before a handler's next write replaces it, on the server and on the client [#3087/M/n=1].
What these updaters leave to a mod's floors and the sickness stat they never touch are [the mood surface](health-surfaces.md#mood-surface) and [the poison section](health-surfaces.md#poison-infection).

The frame's tail — `OnTick` and the network manager — is [the server tick order](../platform/server-lifecycle.md#tick-order), and the push that follows it is [the player-stats push](../platform/mp-model.md#packets).
Which side runs the player's endurance model, and for whom it returns early, is [the ownership section](../platform/mp-model.md#ownership).

<a id="discomfort"></a>
### DISCOMFORT: the body-damage updater and the client's copy

DISCOMFORT runs on `[0,100]` with a default of 0 at index 2 of the fixed order, and the player-stats packet writes and reads the whole fixed order, so the server's value reaches the owning client [#3600/C/C-only].
`BodyDamage.UpdateDiscomfort` computes a target on every call from the dragged corpse, the worn clothing, the bed while asleep, the HYPOTHERMIA, HYPERTHERMIA and WET moodle levels and the vehicle, scaled down by intoxication, clamped and times 100 [#3601/C/C-only].
The target reads no hunger, food or stomach state [#3601/C/C-only].
Awake, the stat moves toward the target by `lerp(D, target, r)` per call, with `r = 0.005 * GameTime.getMultiplier()` cut to a fortieth when the target lies above the stat, and it snaps to the target once the two are within `r` [#3602/C/C-only].
Asleep, the stat is set to the target on every call [#3602/C/C-only].
The relaxation is exponential and fast: with the target at 0 a value keeps about 0.79 of itself per real second at time speed 1 whatever the day length, and about 0.55 over one game minute of the 60-minute default day [#3606/C/arith.].
For players the updater runs on the server only, because the body-damage tick returns on a multiplayer client before it, and the only methods in the jar that name the stat outside its registration are the updater and the moodle update [#3603/C/C-only].
The UNCOMFORTABLE moodle reads DISCOMFORT against 20, 40, 60 and 80 for its four levels, on each side from its own copy [#3604/C/C-only] [#0563].
While that moodle is up and STRESS is below its maximum, the updater adds `StressFromDiscomfort * DISCOMFORT * k` to STRESS per game-second, with `StressFromDiscomfort` at 1.3e-7 and `k` at 3 unless the target's raw sum exceeds 1 [#3605/C/C-only].
A floor written on the server once a game minute therefore does not hold on the client [#3607/C/inference].
The client stores each packet's value and recomputes the moodle from it, so a floor of 100 reads about 100, 79 and 62 at the next three packets on the 60-minute day, and the moodle steps from level 4 to 3 before the next write [#3607/C/inference].
While the character sleeps, the next server update overwrites the floor with vanilla's own target [#3607/C/inference].

<a id="sickness-nicotine"></a>
### SICKNESS and NICOTINE_WITHDRAWAL: what moves them

Both stats were read on the 42.21 jar, and every sentence in this section holds on that build [T11407.1] [T11407.4].
SICKNESS has no writer in the engine's Java: outside its registration, the only method bodies in the jar that name it are the thermoregulator's set point, a second thermoregulator class's update and `Moodle.Update`, and each only reads it [T11407.1].
No Java class looks a stat up by its id, and no class but the registry holds the id `Sickness` as a constant [T11407.1].
The shipped Lua names the stat in two places, the debug menu's stat slider and a read in the forage system [T11407.2].
The radio's `SIC` interaction code goes through a helper that looks up a `getSickness` getter `Stats` does not declare, so it writes nothing, and no shipped broadcast carries the code [T11407.2].
In play SICKNESS therefore stays at its default of 0 unless a mod or the debug menu writes it: the infection, cold and food-sickness paths never move it [T11407.3].
The SICK moodle's level is the apparent infection level, the largest of FOOD_SICKNESS, ZOMBIE_FEVER and ZOMBIE_INFECTION over 100, with SICKNESS added on top, so the moodle moves while SICKNESS stays at 0 [#3130/C/C-only].
A server-side mod that reads SICKNESS once a game minute on an unmodded server reads 0 [T11407.3].
A value a mod writes stays until the next write and raises the thermoregulator's set point by twice itself [#3019/C/inference] [#3024/C/C-only].

NICOTINE_WITHDRAWAL rises only for a Smoker, in the boredom sub-updater of the body-damage tick [T11407.4].
Each call adds `1e-4` times the game-time multiplier to the time since the last smoke, and while that timer exceeds 1 it adds `StressFromBiteOrScratch / 8` times a step `k = min(floor(timer / 10) + 1, 10)` times the multiplier to the stat, `StressFromBiteOrScratch` being 0.00005 [T11407.4].
The sub-updater returns before any of this for a sleeping player, so neither the timer nor the stat moves while the character sleeps [T11407.4].
The stat runs on `[0, 0.51]` with a default of 0 at index 11 of the fixed order, so the clamp holds it at 0.51 and the player-stats packet carries it [#2205/C/C-only].
For a player on a dedicated server the rise runs on the server alone, because the boredom sub-updater's one call site is in `BodyDamage.Update`, which returns on a multiplayer client before it [T11407.5].
The only other methods in the jar that name the stat are the smoking code and the nicotine-stress getter [T11407.5].
At time speed 1 the timer passes 1 about 208 real seconds after a full smoke, and the stat then climbs about 3.0e-4 per real second to its cap about 32 real minutes after the smoke, about 12.7 game-hours on the 60-minute default day, before the step `k` ever leaves 1 [T11407.10].

The only fall is a smoke.
For a Smoker, `RecipeCodeOnEat.consumeNicotineLogic` adds the item's stress change times the fraction to UNHAPPINESS and STRESS, removes 0.51 times the fraction from NICOTINE_WITHDRAWAL and sets the timer to what remains over 0.51 [T11407.6].
For anyone else it adds the item's food-sickness change times the fraction to FOOD_SICKNESS, and for both it adds a flat -0.03 to HUNGER whatever the fraction [T11407.6].
The six smokable foods and the two nicotine drainables, the cigarette pack and chewing tobacco, name `RecipeCodeOnEat.consumeNicotine` as their `OnEat`; the food overload passes the eat's fraction and the drainable overload passes 1 [T11407.7].
The eat hook fires inside `Eat` on the server and again through the packet twin on a receiver [#0130], and this hook writes stats, so the receiving client's copy takes the smoke's writes until the next player-stats packet replaces them with the server's [T11407.8].

Withdrawal is read only as stress: `Stats.getNicotineStress` returns STRESS plus NICOTINE_WITHDRAWAL clamped to STRESS's bounds, and its only callers are the STRESS moodle, the morale updater and a debug panel [T11407.9] [#2789/C/C-only].
Vanilla's withdrawal therefore moves no hunger, and the flat -0.03 at the smoke is nicotine's whole effect on HUNGER [T11407.9].
A server-side mod can read once a game minute the server's own NICOTINE_WITHDRAWAL and `getTimeSinceLastSmoke`, both computed on the server for a player: 0 for a character without the Smoker trait, at most 0.51, and unchanged while the character sleeps [T11407.11].
## Walls and bounds
<a id="walls"></a>

The stat class declares no setter for a stat's minimum, maximum or default, so the `[0,1]` range of endurance and fatigue cannot be widened [#2209/C/C-only].
Registration goes through a compute-if-absent, so registering an id that already exists returns the existing stat and never rewrites its bounds [#2210/C/C-only].
The hook's all-or-nothing answer and its unreadable registrant list are walls of the Lua surface, stated at [the hook surface](../platform/lua-platform.md#hooks).
The eight-hour comparison held no sleeping path across an hourly sample and reached no endurance arm: the harness asleep flag read back true when set and false at the hourly samples in both boots, the hour-5 thirst and hunger drop in the takeover boot being consistent with a brief asleep spell the samples cannot confirm, and the harness walk asked to run moved the player with the running flag false and endurance at 1 [#2810/M/n=1].
Under the harness's partial sleep hold (about 85 % asleep and 15 % awake updates) thirst rose 2.05 times the pure asleep constant on both the vanilla boot (0.00738 per game-hour on the server) and the takeover boot (0.00740), the awake share accounting for the excess, so the two agree with each other and with the asleep constant [#2841/M/n=2, #0477/C/C-only]; fatigue at 0 and endurance at 1 did not move on a rested character [#2841/M/n=2]; the harness run still only walked, so no running or endurance arm was exercised [#2840/M/n=2].
Not covered: the sound-stress source function and the awake path's stress decay, the awake and sleeping paths' own rates (handed off above), a non-player living character's use of the updaters beyond its empty sleeping path, what sets the character-stats system switch, whether Kahlua can call the registration static and what a mod-registered stat does across a save and reload, and the per-moodle update bodies — none of them was read here.

## Open
<a id="open"></a>

- Whether a handler that reproduces the seven skipped updaters from the library's formulas tracks vanilla's stat trajectory stat by stat over several game-hours — settled by two boots of one fixture, with no handler and with the reproducing handler, sampling the seven stats hourly against a per-stat band; run x131c-20261004-181223 measured thirst and hunger but left stress, anger, endurance and the sleeping path unexercised, so the stress arm is still a first measurement to take; run x132r-20261005-072441 measured asleep thirst in band, left asleep fatigue and endurance trivial on a rested character and its running arm walked; -> [X34](../areas/open-questions.md#x34) [#2081/C/open].
- Whether a handler's endurance write is the last before the player-stats push, as the tick order reads — settled by a sentinel endurance written each tick and read in client-first pairs at rest and running, beside an arm with the handler removed; run x131c-20261004-181223 took the resting pairs and no running pair, and run x132r-20261005-072441 none, no handler writing the sentinel and the run arm walking, and run x161s-20261006-031534 read only vanilla's awake write reaching the client within about one push [#3050/M/n=1]; -> [X35](../areas/open-questions.md#x35) [#2082/C/open].
- Decision: whether a takeover handler integrates endurance from its own stored value or from the stat it reads back — the player's endurance model runs outside the hook, earlier in the same update [#2235/C/C-only], on the side [the ownership section](../platform/mp-model.md#ownership) states.
- Decision: which of the updaters' non-stat side effects a takeover reproduces and which it drops — the last-endurance stamp [#2215/C/C-only], the anger decay and the idle-square timer [#2226/C/C-only], the time-of-sleep advance [#2227/C/C-only], the thirst ghost-mode gate [#0560/M/n=1], the auto-drink call [#2250/C/C-only] and the fitness stat's refresh [#2223/C/C-only].
- Decision: whether a mod that owns intoxication writes it from the handler on every update, after the decay [#2921/C/C-only], or sets the reduction value to zero and sets it again after every load, since the value is not saved [#2920/C/inference].
- Decision: whether the mod keeps a nutrient in a stat it registers or in its own store — a registered stat answers `get` and `set` and is never saved or synced [#2211/C/C-only].
- Decision: whether an illness appetite term reads SICKNESS, which vanilla never writes [T11407.3], or the SICK moodle's inputs [#3130/C/C-only], and whether a withdrawal hunger term reads the server's NICOTINE_WITHDRAWAL [T11407.11].

## See also

- [`../platform/lua-platform.md`](../platform/lua-platform.md#hooks) — the hook surface: what makes it answer true, who reaches it, and what Lua can read of it.
- [`../platform/mp-model.md`](../platform/mp-model.md#ownership) — which side owns each stat, and the push that carries them.
- [`wire-packets.md`](wire-packets.md#player-stats-packet) — the player-stats packet's field order over the fixed stat order.
- [`body-and-weight.md`](body-and-weight.md#hunger-thirst) — the hunger and thirst rates the thirst and wake-state updaters apply.
- [`endurance-fatigue-sleep.md`](endurance-fatigue-sleep.md#drain) — the endurance model and the fatigue and sleep rates.
- [`../platform/server-lifecycle.md`](../platform/server-lifecycle.md#tick-order) — the rest of the server frame after the hook.
- [`../areas/open-questions.md`](../areas/open-questions.md#x34) — the experiments the open rows point at.
