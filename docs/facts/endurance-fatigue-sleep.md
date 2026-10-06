# Endurance, fatigue and sleep
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: what moves a player's endurance and fatigue — the drain, the regeneration, the event writers, awake fatigue, sleep, the moodles the two stats drive and the setters a mod has against them; the stat registry and the tick order are `facts/character-stats.md`'s, walk and combat speed are `facts/perception-speed.md`'s, and the weight-band traits are `facts/body-and-weight.md`'s.

## Key facts

- Running drains endurance from a base rate of 5.2e-5 and sprinting or dragging a corpse from 4.55e-4, each multiplied by a trait multiplier, 0.5, an asthma factor, the game-time multiplier and a sneak factor [#2251/C/C-only].
- The drain's trait multiplier is 1.4, or 2.9 under Overweight, or 0.8 under Athletic, then times 2.3, the Fitness pacing ladder and the hyperthermia term [#2252/C/C-only].
- Walking costs endurance only above heavy-load level 2, at half the running arithmetic with a 3.0 stage in place of 2.3 [#2256/C/C-only].
- Walking also drains `runningEnduranceReduce ÷ 7` once the endurance moodle reaches level 2, and regenerates at a quarter of the standing rate below it [#2259/C/C-only].
- No waking endurance arm carries a day-length term, so endurance rates do not scale with the day length while awake fatigue does [#2257/C/C-only].
- Standing still, endurance regenerates at `imobileEnduranceReduce × EndRegen × getRecoveryMod() × (1 − 0.85 × fatigue) × multiplier`, with `imobileEnduranceReduce` read from `ImobileEnduranceIncrease = 0.0000930/3` [#2258/C/C-only].
- Sitting, resting or riding awake in a vehicle regenerates endurance at five times the standing rate, and sleep at twice it [#2260/C/C-only] [#2261/C/C-only].
- The `EndRegen` sandbox option maps its values 1 to 5 onto 1.8, 1.3, 1.0, 0.7 and 0.4, defaults to 3, and multiplies every regeneration arm [#2265/C/C-only].
- `getRecoveryMod` starts from a Fitness ladder running from 0.7 at level 0 to 1.6 at level 10 [#2262/C/C-only].
- Awake fatigue accumulates at `fatigueIncrease` 3.45e-5 times the `StatsDecrease` multiplier, the endurance deficit floored at 0.3, the game clock, the sleep traits and the thermoregulator's fatigue multiplier, divided by 1.5 while sitting or resting [#2270/C/C-only].
- Sleep takes fatigue above 0.3 down over a nominal 5 hours and the last 0.3 over a nominal 7 hours, scaled by bed type, Insomniac, Night Owl and the sleep traits [#2276/C/C-only].
- The `TIRED` moodle fires above 0.6, 0.7, 0.8 and 0.9 on fatigue, on a strict greater-than [#2279/C/C-only].
- A `TIRED` level and an `ENDURANCE` level each cut stomp power by the same 0.5, 0.2, 0.1 and 0.05 ladder, and the two compound [#2280/C/C-only].

## How it works

Endurance and fatigue are two registered stats; their bounds, their defaults and the stat API a mod writes them through are [character-stats.md](../facts/character-stats.md#registry).
Every path on this page writes one of the two stats, reads one of them, or reads a moodle level computed from one of them.
The whole waking endurance model sits in one private method, `IsoPlayer.updateEndurance`, which returns for an animal and on a game client; the side gate and its owner are [mp-model.md](../platform/mp-model.md#ownership).
Where each updater runs in the frame, and where the server's fatigue reset sits relative to the `CalculateStats` hook, is [character-stats.md](../facts/character-stats.md#tick-order).

<a id="drain"></a>
### Drain: running, sprinting, dragging and loaded walking

The drain arms of `IsoPlayer.updateEndurance`, decoded from the bytecode [#2251/C/C-only] [#2252/C/C-only] [#2255/C/C-only] [#2256/C/C-only]:

```java
float sneak = 1.0f;                                   // @40  L3437
if (isSneaking()) sneak = 1.5f;                       // @49  L3439

// running, sprinting or dragging a corpse
if (currentSpeed > 0 && (isRunning() || isSprinting() || isDraggingCorpse())) {   // @53  L3441
    double rate = ZomboidGlobals.runningEnduranceReduce;                          // @83  L3442
    if (isSprinting())      rate = ZomboidGlobals.sprintingEnduranceReduce;       // @94  L3444
    if (isDraggingCorpse()) rate = ZomboidGlobals.sprintingEnduranceReduce;       // @105 L3447
    float m = 1.4f;                                                               // @109 L3450
    if (traits.get(OVERWEIGHT)) m = 2.9f;                                          // @127 L3452
    if (traits.get(ATHLETIC))   m = 0.8f;                                          // @145 L3455
    m *= 2.3f;                                                                     // @150 L3458
    m *= getPacingMod();                                                           // @158 L3459
    m *= getHyperthermiaMod();                                                     // @167 L3460
    float asthma = 0.7f;                                                           // @176 L3461
    if (traits.get(ASTHMATIC)) asthma = 1.0f;                                       // @194 L3464
    if (moodles.getMoodleLevel(HEAVY_LOAD) == 0)                                    // @197 L3467
        stats.remove(ENDURANCE, rate*m*0.5*asthma*GameTime.getMultiplier()*sneak);  // @210 L3468
    else {
        float load;          // tableswitch @259: 1 -> 1.5, 2 -> 1.9, 3 -> 2.3, default -> 2.8
        stats.remove(ENDURANCE, rate*m*0.5*asthma*GameTime.getMultiplier()*load*sneak);  // @307 L3476
    }
}
// walking under a heavy load
else if (currentSpeed > 0 && moodles.getMoodleLevel(HEAVY_LOAD) > 2) {              // @350 L3480
    float asthma = 0.7f; if (traits.get(ASTHMATIC)) asthma = 1.0f;                  // @373 L3481
    float m = 1.4f;                                                                 // @392 L3486
    if (traits.get(OVERWEIGHT)) m = 2.9f;                                           // @409 L3488
    if (traits.get(ATHLETIC))   m = 0.8f;                                           // @426 L3492
    m *= 3.0f;                                                                      // @430 L3495
    m *= getPacingMod();                                                            // @436 L3496
    m *= getHyperthermiaMod();                                                      // @443 L3497
    float load = 2.8f;   // tableswitch @465: 2 -> 1.5, 3 -> 1.9, 4 -> 2.3; only 3 and 4 pass the gate
    stats.remove(ENDURANCE,
        runningEnduranceReduce*m*0.5*asthma*sneak*GameTime.getMultiplier()*load / 2.0);  // @513 L3510
}
```

Running, sprinting and dragging a corpse share one arm, and only the base rate differs between them: `runningEnduranceReduce` is 5.2e-5 while running, and `sprintingEnduranceReduce` is 4.55e-4 while sprinting or dragging, both read once from the Lua `ZomboidGlobals` table [#2251/C/C-only].
The arm removes `rate × mult × 0.5 × asthma × GameTime.getMultiplier() × sneak` from endurance on each update [#2251/C/C-only].
The multiplier chain starts at 1.4, becomes 2.9 under Overweight, and becomes 0.8 under Athletic, which is tested second and so overrides Overweight; it is then multiplied by 2.3, by `getPacingMod()` and by `getHyperthermiaMod()` [#2252/C/C-only].
The weight-band traits' whole footprint on this chain is [body-and-weight.md](../facts/body-and-weight.md#weight-traits).
Asthmatic raises the drain by replacing a 0.7 factor with 1.0, in the running arm and in the loaded-walking arm alike [#2253/C/C-only].
Sneaking sets a 1.5 factor that multiplies the three drain arms of the method and reaches none of its regeneration arms, so sneaking raises the cost of whichever drain it rides on [#2254/C/C-only].
Under a heavy-load moodle the running arm is multiplied again, by 1.5, 1.9, 2.3 or 2.8 at moodle levels 1, 2, 3 and 4 [#2255/C/C-only].

Walking has two drain paths of its own, and both are conditional.
Walking drains endurance only above heavy-load level 2, at `runningEnduranceReduce × mult × 0.5 × asthma × sneak × multiplier × load ÷ 2`, where the multiplier chain carries a 3.0 stage in place of 2.3 and the load factor is 1.9 at level 3 and 2.3 at level 4 [#2256/C/C-only].
The walking rate is the running constant whatever the gait, so a loaded walk is priced off the running rate rather than off a walking rate of its own.

The endurance model has no day-length term.
No arm of `IsoPlayer.updateEndurance` or of the sitting and vehicle regenerators multiplies by `GameTime.getDeltaMinutesPerDay()`, so waking endurance rates are per update, at most times the game-time multiplier, and do not scale with the day length, while the awake fatigue accumulation does [#2257/C/C-only].
The one exception is the asleep regeneration arm, stated at [the regeneration anchor](#regen).
A server that lengthens its day therefore stretches fatigue across the longer day while endurance drains and refills at the same per-update pace.

<a id="regen"></a>
### Regeneration and the recovery multipliers

Every regeneration arm shares one product, `imobileEnduranceReduce × EndRegen multiplier × getRecoveryMod()`, and differs only in the factor in front of it and in the fatigue term beside it.

Standing still, endurance regenerates at `imobileEnduranceReduce × EnduranceRegenMultiplier × getRecoveryMod() × (1 − 0.85 × fatigue) × multiplier`, and only while the heavy-load moodle is at level 1 or below; `imobileEnduranceReduce` is read from `ImobileEnduranceIncrease = 0.0000930/3` in the Lua `ZomboidGlobals` table [#2258/C/C-only].
Walking, endurance regenerates at a quarter of the standing rate with a `(1 − fatigue)` term and no 0.85 factor, while the endurance moodle is below level 2 and the heavy-load moodle at level 1 or below; at endurance moodle level 2 or above, walking drains it instead, at `runningEnduranceReduce ÷ 7 × sneak` [#2259/C/C-only].
Sitting on the ground or on furniture, resting, or riding awake in a vehicle regenerates endurance at five times the standing rate with a `(1 − 0.8 × fatigue)` term, the five being the hard-coded `sittingEnduranceMultiplier` rather than a Lua value [#2260/C/C-only].
Asleep, endurance regenerates at twice the standing rate, multiplied by `getDeltaMinutesPerDay()` when every player is asleep, with no fatigue term at all [#2261/C/C-only].
The asleep endurance regeneration is in `IsoPlayer.updateStats_Sleeping`, one of the hook-skipped updaters, and `IsoPlayer.updateEndurance` has no asleep test, so a registered `CalculateStats` handler also drops sleep's endurance regeneration. [#2782/C/C-only]
`IsoPlayer.allPlayersAsleep` counts the process's local `IsoPlayer.players` array, not the server's connected players. [#2788/C/C-only]

Fatigue therefore gates every waking regeneration arm and none of the sleeping one.
A tired character standing still recovers endurance more slowly than a rested one, and a fully fatigued character walking recovers none, while the same character asleep recovers at the full sleeping rate.

The `EndRegen` sandbox option, an enum whose translation key is `EnduranceRegen`, maps its values 1, 2, 3, 4 and 5 to 1.8, 1.3, 1.0, 0.7 and 0.4, defaults to 3, and is multiplied into every regeneration arm [#2265/C/C-only].
Which sandbox label corresponds to each integer is not read here; the mapping is the switch's.

`getRecoveryMod` is the per-character multiplier every regeneration arm carries, and it is built from the Fitness perk and the weight-band traits.
Its Fitness ladder and the pacing ladder that enters the drain, as read [#2262/C/C-only] [#2263/C/C-only]:

| Fitness level | `getRecoveryMod` start | `getPacingMod` |
|---|---|---|
| 0 | 0.70 | 0.90 |
| 1 | 0.80 | 0.80 |
| 2 | 0.90 | 0.75 |
| 3 | 1.00 | 0.70 |
| 4 | 1.10 | 0.65 |
| 5 | 1.20 | 0.60 |
| 6 | 1.30 | 0.57 |
| 7 | 1.40 | 0.53 |
| 8 | 1.50 | 0.49 |
| 9 | 1.55 | 0.46 |
| 10 | 1.60 | 0.43 |

`getRecoveryMod` starts from a Fitness ladder of 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.55 and 1.6 at levels 0 to 10 [#2262/C/C-only].
The weight-band traits then multiply that value cumulatively, and their four factors are live [#0183].
After them come a lipid and a protein branch that can never fire, because the stores they test are clamped above their thresholds; that reading is [nutrition-core.md](../facts/nutrition-core.md#macro-effects).
`getPacingMod` returns 0.9 at Fitness 0 and 0.8, 0.75, 0.7, 0.65, 0.6, 0.57, 0.53, 0.49, 0.46 and 0.43 at levels 1 to 10, so a fitter character's drain multiplier is smaller [#2263/C/C-only].

`getHyperthermiaMod` returns 2.0 only when the hyperthermia moodle is at exactly level 4 and 1.0 at every other level, levels 2 and 3 included: its first test admits any level above 1 and its second then requires 4 [#2264/C/C-only].
Read as written, the first test is dead weight and moderate heat costs no extra endurance at all.

None of the three multipliers has a setter; the missing setters are listed under [Walls and bounds](#walls).
A mod moves `getRecoveryMod` only through the Fitness perk or the weight-band traits, and `getPacingMod` only through the Fitness perk.

Measured live, vanilla's awake endurance reaches the owning client within about one push: with ENDURANCE written to 0.6 on the server and rising under a harness walk, the client's copies lay 369.61376953125 to 1162.46142578125 ms behind the server's series; no handler wrote awake endurance on that boot (code inference; #3050's bound), so whether a handler's write is the one the push carries is still [X35](../areas/open-questions.md#x35)'s question [#3050/M/n=1] [#2082/C/open].

<a id="writers"></a>
### Event writers

The per-update model is not the only writer.
Endurance has three event writers outside the per-update model: one per melee swing, one per vault over a fence and one per exercise repetition [#2269/C/C-only].

The per-swing drain, `CombatManager.processWeaponEndurance`, decoded [#2266/C/C-only]:

```java
if (!weapon.isUseEndurance()) return;                              // @0  L1190
float w = weapon.getEffectiveWeight();                             // @8  L1194
float extra = 0;                                                   // @13 L1195
if (weapon.isTwoHandWeapon() && !heldInBothHands) extra = w/1.5f/10f;  // @16 L1196, @39 L1197
float d = ( w * 0.18f
          * weapon.getFatigueMod(chr)                              // @56 L1200
          * chr.getFatigueMod()                                    // @61 L1200 — the character's Fitness ladder
          * weapon.getEnduranceMod()                               // @66 L1200 — the item script's EnduranceMod
          * 0.3f + extra ) * 0.04f;                                // @70..@80 L1200
float t = chr.getCharacterTraits().getTraitEnduranceLossModifier(); // @83 L1201
chr.getStats().remove(ENDURANCE, d * t);                           // @92 L1202
```

A melee swing with a weapon whose `UseEndurance` is set drains endurance by `(effectiveWeight × 0.18 × weapon fatigue mod × character fatigue mod × EnduranceMod × 0.3 + two-hand term) × 0.04`, times 1.2 for Asthmatic, where the two-hand term is `effectiveWeight ÷ 1.5 ÷ 10` for a two-handed weapon not held in both hands [#2266/C/C-only].
A weapon's own fatigue modifier is 0.8 once the matching Blunt, Axe or Spear perk reaches level 8, and 1.0 otherwise [#2267/C/C-only].

`IsoGameCharacter.exert(float)` is `public` on an exposed class and removes that amount of endurance, times 0.9 for Jogger [#2268/C/C-only].
Like every write to the stat, it holds only on the side that owns the stat; the owner is [mp-model.md](../platform/mp-model.md#ownership).

Food and fluids write both stats too: `Eat` adds each item's endurance and fatigue changes, and that write and its order are [eating-pipeline.md](../facts/eating-pipeline.md#eat).
A drink's fatigue write lands at the drink and is lost only to the reset: 0.2 litres of Coffee (`fatigueChange = -10.0` per litre) drunk by one server-side `DrinkFluid` call lowered FATIGUE from 0.5765 to 0.5566 on a server that allows and needs sleep and the lower value held, while on a server that disables sleep the stat sat at its reset value of 0.00011, the probe's minimum read 0 across the drink and every later read was 0.00011 again [#2949/M/n=1].
A pill writes fatigue on its own path, [eating-pipeline.md](../facts/eating-pipeline.md#pill-path).

<a id="fatigue"></a>
### Awake fatigue

Awake fatigue accumulation, `IsoGameCharacter.updateStats_Awake`, decoded [#2270/C/C-only] [#2271/C/C-only]:

```java
float endDef = 1.0f - stats.get(ENDURANCE);                     // @31 L10244
if (endDef < 0.3f) endDef = 0.3f;                               // @44 L10245, @52 L10246
float sleepTrait = 1.0f;                                        // @56 L10249
if (traits.get(NEEDS_LESS_SLEEP)) sleepTrait = 0.7f;            // @71 L10251
if (traits.get(NEEDS_MORE_SLEEP)) sleepTrait = 1.3f;            // @88 L10254
float rest = 1.0f;                                              // @92 L10258
if (isSitOnGround() || isSittingOnFurniture() || isResting())
    rest = 1.5f;                                                // @115 L10260
stats.add(FATIGUE, ZomboidGlobals.fatigueIncrease
    * SandboxOptions.instance.getStatsDecreaseMultiplier()
    * endDef
    * GameTime.getMultiplier()
    * GameTime.getDeltaMinutesPerDay()
    * sleepTrait
    * getFatiqueMultiplier()          // the engine's spelling
    / rest);                                                    // @119 L10262
```

Awake fatigue accumulates at `fatigueIncrease × StatsDecrease × max(0.3, 1 − endurance) × multiplier × deltaMinutesPerDay × sleepTrait × thermoregulator fatigue multiplier ÷ restMod`, with `fatigueIncrease` 3.45e-5 read from the Lua `ZomboidGlobals` table [#2270/C/C-only].
Endurance already drives fatigue through the deficit term, so a character who spends endurance also tires faster, and a fully rested body still accumulates fatigue at the floored deficit.
The `StatsDecrease` multiplier and its mapping are [body-and-weight.md](../facts/body-and-weight.md#sandbox).
Needs Less Sleep scales awake fatigue by 0.7 and Needs More Sleep by 1.3, and sitting on the ground, sitting on furniture or resting divides it by 1.5 [#2271/C/C-only].
Resting therefore slows the fatigue climb rather than speeding it.

The thermoregulator's fatigue multiplier is raised by both cold and heat and never falls below 1, so it can only speed fatigue up; with no thermoregulator the term is 1 [#2272/C/C-only].
The primary and secondary thermal totals that feed it are unbounded on this page, and the rest of the thermal model is [body-and-weight.md](../facts/body-and-weight.md#multipliers).

`ZomboidGlobals.sleepFatigueReduction` is loaded from the Lua table and read by nothing else in the jar, so the constant whose name suggests it owns sleep restoration owns nothing [#2273/C/C-only].

Two writers sit outside the awake updater.
Inside a toxic building without protection, fatigue rises by 1.0e-4 times the thirty-FPS multiplier on each update while it is below 1 [#2274/C/C-only].
God mode resets fatigue, endurance and temperature to their defaults on every update [#2275/C/C-only].

On a dedicated server the whole awake accumulation is moot unless the server allows and needs sleep, because the server resets fatigue ahead of it on every update; that reset and its gate are [character-stats.md](../facts/character-stats.md#tick-order).
Measured live, the reset runs at the next update after a write: on a server whose ini set both options false, three server writes of FATIGUE 0.5 each read back 0.5 in the writing call, a per-tick server probe saw 0.5 and counted three falls of more than 0.1 in 301 ticks, and the next server read after each write was 9.99e-05 to 1.01e-04 [#2947/M/n=1].
With both options true the same write held: FATIGUE read 0.00637 at first sight against 9.781e-05 on the sleep-disabled boot, the write read 0.50060 at the next server read and 0.55930 at the end of a 60 s window, and the probe counted no fall in 600 ticks [#2948/M/n=1].

<a id="sleep"></a>
### Sleep

Sleep restoration, `IsoPlayer.updateStats_Sleeping` past its endurance arm, decoded [#2276/C/C-only] [#2277/C/C-only]:

```java
if (stats.isAboveMinimum(FATIGUE)) {                            // @56 L3297
    float f = 1.0f;                                             // @69 L3299
    if (traits.get(INSOMNIAC)) f *= 0.5f;                        // @84 L3301
    if (traits.get(NIGHT_OWL)) f *= 1.4f;                        // @103 L3304
    float bed = 1.0f;                                           // @109 L3307
    //   averageBedPillow 1.05 (@124 L3309)  goodBed 1.10 (@141 L3312)
    //   goodBedPillow    1.15 (@161 L3314)  badBed  0.90 (@181 L3316)
    //   badBedPillow     0.95 (@201 L3318)  floor   0.60 (@221 L3320)
    //   floorPillow      0.75 (@241 L3322)  anything else 1.00
    float dt = 1.0f / GameTime.getMinutesPerDay() / 60.0f
                    * GameTime.getMultiplier() / 2.0f;           // @245 L3325
    timeOfSleep += dt;                                           // @268 L3327
    if (timeOfSleep > delayToActuallySleep) {                     // @279 L3328
        float t = 1.0f;                                           // @291 L3329
        if (traits.get(NEEDS_LESS_SLEEP))      t *= 0.75f;         // @307 L3331
        else if (traits.get(NEEDS_MORE_SLEEP)) t *= 1.18f;         // @331 L3333
        if (stats.get(FATIGUE) <= 0.3f)                            // @339 L3338
            stats.remove(FATIGUE, dt/(7.0f*t) * 0.3f * f * bed);   // @356 L3339, @364 L3340
        else
            stats.remove(FATIGUE, dt/(5.0f*t) * 0.7f * f * bed);   // @391 L3344, @399 L3345
    }
}
```

Asleep, fatigue above 0.3 comes off at `dt ÷ (5 × t) × 0.7 × f × bed` per update and fatigue at or below 0.3 at `dt ÷ (7 × t) × 0.3 × f × bed`, so the top 0.7 is sized to clear over a nominal 5 hours and the last 0.3 over a nominal 7 [#2276/C/C-only].
The bed factor is 0.6 on a floor, 0.75 on a floor with a pillow, 0.9 in a bad bed, 0.95 in a bad bed with a pillow, 1.05 in an average bed with a pillow, 1.1 in a good bed, 1.15 in a good bed with a pillow and 1.0 otherwise [#2276/C/C-only].
Insomniac halves the rate and Night Owl multiplies it by 1.4, while Needs Less Sleep scales the nominal hours by 0.75 and Needs More Sleep by 1.18 [#2276/C/C-only].
The nominal hours are the code's own constants, and the clock that drives them is the game's.
The sleep fatigue clock `dt` equals the per-update advance of `GameTime.timeOfDay`, so it is game-hours and the 5- and 7-hour constants of sleep restoration are game-hours. [#2785/C/C-only]

Restoration waits for sleep to take hold: fatigue comes off only once `timeOfSleep` exceeds `delayToActuallySleep`, and `timeOfSleep` advances by `1 ÷ minutesPerDay ÷ 60 × multiplier ÷ 2` on each call [#2277/C/C-only].
`timeOfSleep` is set to the time of day when the player falls asleep and `delayToActuallySleep` to the time of day plus a random 0 to `d` hours, `d` built from Insomniac, pain, stress, bed type, Night Owl and sleeping tablets and capped at 2. [#2786/C/C-only]
`timeOfSleep` and `delayToActuallySleep` are protected fields with public setters `setTimeOfSleep(F)` and `setDelayToSleep(F)` and no getters. [#2787/C/C-only]
The base `IsoGameCharacter.updateStats_Sleeping` is an empty stub, so all of this is a player's alone; the stub is [character-stats.md](../facts/character-stats.md#updaters).

Waking has its own fatigue write.
`SleepingEvent.wakeUp` clears the asleep flag and, on a good bed with or without a pillow, removes a random 0.05 to 0.12 of fatigue scaled by the sleep event's sleeping time over 8 [#2278/C/C-only].
The same method's other bed branches are not read here.

No fatigue value wakes a sleeper.
The player's waking check, run after the stat update for a sleeping player, wakes on the force-wake-up clock time, after more than 16 hours asleep, on aim or movement input in multiplayer, or on the force flag, and reads no stat; the sleeping event wakes a sleeper for very close zombies, a nightmare or intruders [#3029/C/C-only].
Fatigue sets a bed sleep's length once, at its start, in the client's bed handler: the wake time is the time of day plus a random 10 to 13 hours per unit of fatigue plus one, shifted by the bed and the sleep traits and clamped to 3 to 16 hours, and the sleep dialog sets it from the hours the player picks instead [#3030/C/C-only].
A fatigue write during sleep therefore neither wakes the player earlier nor keeps them asleep longer.

On a server that allows and needs sleep, the harness's per-tick asleep hold read asleep at 1014 of 1200 server ticks over 120 s, and while the only player was held asleep the world clock ran about 20 times its waking rate, 61.764 game hours in 115.998 s of server wall time against 1.5095 game hours in 56.703 s awake [#2956/M/n=1].
What the takeover handler did with that sleep is a reading of the mod, [testing-your-mod.md](../areas/testing-your-mod.md#scenario-inputs).

<a id="moodles"></a>
### What the moodles do with the two stats

The `TIRED` moodle fires above 0.6, 0.7, 0.8 and 0.9 on fatigue, on a strict greater-than with the last match winning, and is skipped when body health is exactly zero [#2279/C/C-only].
The `ENDURANCE` moodle is inverted, firing as the stat falls, and its thresholds are carried on the body page's threshold table [#0510/C/C-only].

A `TIRED` level multiplies stomp power by 0.5, 0.2, 0.1 and 0.05 at levels 1 to 4, the same ladder the `ENDURANCE` moodle applies immediately before it, so a tired and winded character's stomps compound the two cuts [#2280/C/C-only].
Each `TIRED` level and each `ENDURANCE` level adds a firearm to-hit penalty of 2.5 by default, the two keys being `CombatConfig` entries ranged 0 to 10, and the whole moodle penalty sum is scaled by the firearm-moodle sandbox multiplier [#2281/C/C-only].
A `TIRED` level subtracts 3 per level from the defence roll against a zombie, where the endurance, heavy-load and drunk moodles subtract 2 per level each [#2282/C/C-only].
A `TIRED` level of exactly 4 drains sanity by 2.0e-6 on every update [#2283/C/C-only].
`calculateIdleSpeed` returns 0.01 plus 0.25 per `ENDURANCE` moodle level, and reads no stat directly [#2284/C/C-only].

The `ENDURANCE` moodle's cuts to base speed and to combat speed are moodle-level terms too, and they are [perception-speed.md](../facts/perception-speed.md#speed) and [perception-speed.md](../facts/perception-speed.md#combat).
Fatigue's movement and combat reach is the `TIRED` moodle in the stomp, firearm, defence and sanity readers above; its reach into sight is [perception-speed.md](../facts/perception-speed.md#vision-cone).
A moodle level has no setter of its own, as [Walls and bounds](#walls) states, so a mod that wants a level moves the stat underneath it.

<a id="setters"></a>
### The setters a mod has

The only setters on the character that take one float and are named for a speed, a modifier or a multiplier are `setSpeedMod`, `setStaggerTimeMod`, `setLevelUpMultiplier`, `setPathSpeed`, `setSneakLimpSpeedScale`, `setLastFallSpeed`, `IsoPlayer.setMoveSpeed` and `IsoPlayer.setCombatSpeed`, and the no-argument `IsoPlayer.setFitnessSpeed` is the ninth speed setter; all nine are `public` [#2286/C/C-only].
None of the nine is an endurance, fatigue or recovery lever, and what each speed setter reaches is [perception-speed.md](../facts/perception-speed.md#speed).
The setters a mod might expect for regeneration, recovery, pacing and fatigue do not exist; they are listed under [Walls and bounds](#walls).
`setRunSpeedModifier` and `setEnduranceMod` exist only on script items, clothing and weapons, never on the character [#2288/C/C-only].
The weapon one is the `EnduranceMod` the per-swing drain multiplies by.

`updateSpeedModifiers` resets the run, walk and combat speed-modifier fields to 1 and rebuilds them from worn items, and the server calls it immediately before every injuries packet, so those three fields cannot hold a mod's value [#2289/C/C-only].

`setUnlimitedEndurance` forces the unlimited-endurance cheat off rather than on when the caller's role lacks the `ToggleUnlimitedEndurance` capability, and writes the argument only when the capability is present [#2290/C/C-only].
The cheat it writes is the one the base `updateEndurance` stub honours by resetting endurance; the stub is [character-stats.md](../facts/character-stats.md#updaters).

`setFitnessSpeed` sets the `FitnessSpeed` animation variable to `Fitness ÷ 5 ÷ 1.1 − ENDURANCE moodle ÷ 20`, caps it at 1.5, and below 0.85 snaps it to 1.0 and raises the `FitnessStruggle` variable [#2291/C/C-only].
It writes animation variables, not a field, so it changes an animation rather than a stat or a speed field.

## Walls and bounds
<a id="walls"></a>

The engine has no setter for a moodle level: the `Moodles` member list is twelve methods, none of which writes a level, so a mod moves a moodle only by moving the stat under it [#2285/C/C-only].
The engine has no `setEnduranceRegenMod`, `setFatigueMod`, `setRecoveryMod`, `setPacingMod`, `setWalkSpeedModifier`, `setAttackDelay`, `setNimbleMod`, `setFatigueMultiplier` or `setEnduranceMultiplier` in any class: the recovery, pacing, fatigue and thermoregulator multipliers are computed only, and moved only through what they read [#2287/C/C-only].
Every formula on this page is read from the bytecode of one jar and none of it was exercised on a live server, so the rates are the code's and not a measurement's.
Not covered: the cadence of the injuries packet that carries the rebuilt speed fields; what writes `delayToActuallySleep`; the unit of the sleep clock against the game clock; the other bed branches of `SleepingEvent.wakeUp`; what the `TIRED` moodle does inside `Fitness.incFutureStiffness`; whether `CombatConfig` is reachable from Lua, and so whether the firearm penalties can be retuned at runtime; the thermal totals behind the thermoregulator's fatigue multiplier; and the sandbox labels behind the `EndRegen` integers.

## Open
<a id="open"></a>

- Does a `CalculateStats` handler that reproduces the skipped updaters, endurance and awake fatigue among them, track vanilla's stat trajectory stat by stat over several game-hours on a live server — settled by two boots of one fixture, one with and one without the handler; run x131c-20261004-181223 compared thirst and hunger but neither endurance arm nor the asleep fatigue, its sleep flag and run flag not holding; -> [X34](../areas/open-questions.md#x34) [#2081/C/open]
- Is a `CalculateStats` handler's endurance write the last write before the player-stats push, as the tick order reads — settled by a handler writing a sentinel endurance each tick, read in client-first pairs; run x131c-20261004-181223 read the sentinel at rest only, its running pairs having walked ([character-stats.md](../facts/character-stats.md#tick-order)), and run x161s-20261006-031534 read only vanilla's awake write reaching the client [#3050/M/n=1]; -> [X35](../areas/open-questions.md#x35) [#2082/C/open]
- Decision: where a mod moves endurance recovery — `getRecoveryMod` multiplies every regeneration arm but has no setter, so the levers are the Fitness perk, the weight-band traits, the `EndRegen` option, or a replacement of the whole stat tick through the hook the two experiments above test [#2258/C/C-only] [#2287/C/C-only].
- Decision: whether fatigue is modelled at all on a server that does not both allow and need sleep, where the server pins it every update ahead of the `CalculateStats` hook (see [character-stats.md](../facts/character-stats.md#tick-order)).
- Decision: whether the mod's endurance costs ride the per-update model, the three event writers, or both — the event writers sit outside the per-update model, so a per-update replacement that ignores them loses the swing, vault and exercise costs [#2269/C/C-only].

## See also

- [character-stats.md#registry](../facts/character-stats.md#registry) — the stat registry, the two stats' bounds and defaults, and the write API.
- [character-stats.md#tick-order](../facts/character-stats.md#tick-order) — where each updater runs, the server's fatigue reset and the `CalculateStats` hook.
- [perception-speed.md#speed](../facts/perception-speed.md#speed) — walk speed, the moodle cuts to base speed and the speed setters.
- [perception-speed.md#combat](../facts/perception-speed.md#combat) — combat speed and the moodle cuts to it.
- [body-and-weight.md#weight-traits](../facts/body-and-weight.md#weight-traits) — the weight-band traits and their recovery and drain terms.
- [nutrition-core.md#macro-effects](../facts/nutrition-core.md#macro-effects) — the macro stores and the dead recovery branches.
- [eating-pipeline.md#eat](../facts/eating-pipeline.md#eat) — the endurance and fatigue fields of an eat.
- [../platform/mp-model.md#ownership](../platform/mp-model.md#ownership) — which side owns the two stats.
- [`../areas/open-questions.md#x34`](../areas/open-questions.md#x34) — the stat-tick replacement experiments.
