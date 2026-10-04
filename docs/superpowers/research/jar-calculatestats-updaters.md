# The CalculateStats updaters, line by line

Verified against 42.20.4 (b0bbce05d5) · 2026-10-04 · scope: the seven updaters `IsoGameCharacter.calculateStats` runs when `Hook.CalculateStats` does not answer true, plus `IsoPlayer.updateStats_Sleeping`, `autoDrink`, the `GameTime` clock getters, the `Stats` write API, the hook's Lua registration, and the Lua reachability of every member a takeover handler needs; written for Plan 1's `Hook.CalculateStats` handler.

Conventions. Offsets are bytecode offsets in the method named in the section heading; `L<n>` is the source line the dump's LineNumberTable gives. Arithmetic types matter for a bit-close reproduction: where the bytecode multiplies in `double` (`dmul`) and narrows once at the end (`d2f`), the pseudo-Java keeps the `(double)` chain and the single `(float)` cast. Every `ZomboidGlobals` field below is a `double` loaded in `ZomboidGlobals.Load` through `Double.doubleValue` from the Lua key named beside it; the values are `media/lua/shared/defines.lua` lines in the install. `SD` is `SandboxOptions.instance.getStatsDecreaseMultiplier()` (a `double`); `M` is `GameTime.instance.getMultiplier()` (a `float`); `DMPD` is `GameTime.instance.getDeltaMinutesPerDay()` (a `float`). Section 9 shows that `M × DMPD` is the game-seconds that elapse in one update, which is the unit every "per game-second" rate in `facts/body-and-weight.md#hunger-thirst` is quoted in.

Shared constants (from `ZomboidGlobals.Load` and `defines.lua`):

| `ZomboidGlobals` field | Lua key | `defines.lua` | value | `Load` offset |
|---|---|---|---|---|
| `imobileEnduranceReduce` | `ImobileEnduranceIncrease` | line 7 `0.0000930/3` | 3.1e-5 | @49–@62 |
| `thirstIncrease` | `ThirstIncrease` | line 9 `0.0000040 * 2` | 8.0e-6 | @66–@79 |
| `thirstSleepingIncrease` | `ThirstSleepingIncrease` | line 10 `0.0000010` | 1.0e-6 | @83–@96 |
| `thirstLevelToAutoDrink` | `ThirstLevelToAutoDrink` | line 11 `0.1` | 0.1 (loaded, read by nothing — § 1) | @100–@113 |
| `thirstLevelReductionOnAutoDrink` | `ThirstLevelReductionOnAutoDrink` | line 12 `0.1` | 0.1 (loaded, read by nothing — § 1) | @117–@130 |
| `hungerIncrease` | `HungerIncrease` | line 14 `0.0000032 * 3` | 9.6e-6 | @134–@147 |
| `hungerIncreaseWhenWellFed` | `HungerIncreaseWhenWellFed` | line 15 `0` | 0 | @151–@164 |
| `hungerIncreaseWhileAsleep` | `HungerIncreaseWhileAsleep` | line 17 `0.0000010` | 1.0e-6 | @168–@181 |
| `hungerIncreaseWhenExercise` | `HungerIncreaseWhenExercise` | line 16 `0.0000032 * 6` | 1.92e-5 | @185–@198 |
| `fatigueIncrease` | `FatigueIncrease` | line 19 `0.0000345` | 3.45e-5 | @202–@215 |
| `stressReduction` | `StressDecrease` | line 21 `0.00003` | 3.0e-5 | @219–@232 |
| `idleIncreaseRate` | `IdleIncrease` | line 55 `0.0005` | 5.0e-4 | @508–@521 |
| `idleDecreaseRate` | `IdleDecrease` | line 56 `0.0060` | 6.0e-3 | @525–@538 |

`SandboxOptions.getStatsDecreaseMultiplier()D` @0–@65 L545–L550 is a `tableswitch` on `statsDecrease.getValue()`: 1 → 2.0, 2 → 1.6, 3 → 1.0, 4 → 0.8, 5 → 0.65, any other value → 1.0 (`double`). `SandboxOptions.getEnduranceRegenMultiplier()D` @0–@65 L535–L540 has the same shape on `endRegen`: 1 → 1.8, 2 → 1.3, 3 → 1.0, 4 → 0.7, 5 → 0.4, else 1.0 (agrees with `facts/endurance-fatigue-sleep.md#regen`).

## 1. `IsoGameCharacter.updateThirst()` — private

```java
private void updateThirst() {
    float trait = 1.0f;                                                   // @0   L10367
    if (characterTraits.get(HIGH_THIRST)) trait *= 2.0f;                   // @2–@18  L10369–L10370 (fconst_2)
    if (characterTraits.get(LOW_THIRST))  trait *= 0.5f;                   // @19–@37 L10373–L10374
    if ((GameServer.server
         || (!GameClient.client && IsoPlayer.getInstance() == this))       // @38–@54 L10377
        && (isoPlayer == null || !isoPlayer.isGhostMode())) {              // @57–@71 L10377
        if (asleep) {                                                     // @74 L10378 (field read, not isAsleep())
            stats.add(THIRST, (float)( ZomboidGlobals.thirstSleepingIncrease
                                     * SD * (double)M * (double)DMPD
                                     * (double)trait));                   // @81–@121 L10379
        } else {
            stats.add(THIRST, (float)( ZomboidGlobals.thirstIncrease
                                     * SD * (double)M
                                     * getRunningThirstReduction()         // double, private
                                     * (double)DMPD * (double)trait
                                     * getThirstMultiplier()));            // @125–@175 L10381
        }
    }
    autoDrink();                                                          // @176 L10384, always
}                                                                         // @180 L10385
```

Per update: asleep, `THIRST += 1.0e-6 × SD × M × DMPD × trait`; awake, `THIRST += 8.0e-6 × SD × M × run × DMPD × trait × thermo`, where `trait` is 2 for High Thirst, 0.5 for Low Thirst, 1 for both or neither (the two tests are independent, so both traits give 1.0), `run` is `getRunningThirstReduction()` and `thermo` is `getThirstMultiplier()`. Thirst has no damping term. The asleep arm carries neither `run` nor `thermo`.

`getRunningThirstReduction()D` @0–@21 L10388–L10391 (private): returns `1.2` (`ldc2_w`) when `this == IsoPlayer.getInstance()` and `IsoPlayer.getInstance().IsRunning()`, else `1.0`. On a dedicated server the test is against the server process's `IsoPlayer.getInstance()`, not against the character, so whether a remote player can ever get 1.2 depends on what that static holds on a dedicated server (Not read below). `IsoPlayer.IsRunning()` @0–@4 L8517 is `return isRunning();`.

`getThirstMultiplier()D` @0–@29 L14948–L14951 (public): `getBodyDamage() != null && getBodyDamage().getThermoregulator() != null ? thermoregulator.getFluidsMultiplier() : 1.0` (agrees with `facts/body-and-weight.md#multipliers`).

`IsoPlayer.isGhostMode()` @0–@4 L1118 is `return isInvisible();` — the ghost-mode gate is the invisibility flag.

| constant | source | value |
|---|---|---|
| `thirstIncrease` | `ZomboidGlobals`, Lua `ThirstIncrease` | 8.0e-6 |
| `thirstSleepingIncrease` | `ZomboidGlobals`, Lua `ThirstSleepingIncrease` | 1.0e-6 |
| High Thirst factor | literal `fconst_2` @16 | 2.0 |
| Low Thirst factor | literal `ldc 0.5` @33 | 0.5 |
| running factor | literal `ldc2_w 1.2` @16 of `getRunningThirstReduction` | 1.2 |
| `SD` | `SandboxOptions.getStatsDecreaseMultiplier()` | 2.0 / 1.6 / 1.0 / 0.8 / 0.65 |

Gates: `GameServer.server`, or `!GameClient.client && IsoPlayer.getInstance() == this` (@38–@54); ghost mode / invisibility of `isoPlayer` (@57–@71); asleep is the `asleep` field (@74). No animal return of its own (the animal return is in `calculateStats`). No clamp beyond `Stats.add`'s stat clamp.

Non-stat writes: none in `updateThirst` itself; the `autoDrink()` call at @176 is unconditional — outside the side gate and the ghost gate (agrees with `facts/character-stats.md#updaters`).

### `IsoGameCharacter.autoDrink()` — `public void autoDrink()`, declared on `IsoGameCharacter`, no parameters

```java
public void autoDrink() {
    if (GameClient.client) return;                                        // @0–@6   L11727–L11728
    if (GameServer.server && this instanceof IsoPlayer p
        && !p.getAutoDrink()) return;                                     // @7–@34  L11730–L11731
    if (!Core.getInstance().getOptionAutoDrink()) return;                 // @35–@44 L11733–L11734
    if (isAsleep() || isPerformingGrappleAnimation() || isKnockedDown()
        || isbFalling() || isAiming() || isClimbing()) return;            // @45–@87 L11736–L11737
    if (LuaHookManager.TriggerHook("AutoDrink", this)) return;            // @88–@98 L11739–L11740
    if (stats.get(THIRST) <= 0.1f) return;                                // @99–@116 L11743–L11744 (ldc_w 0.1 literal)
    InventoryItem src = getWaterSource(getInventory().getItems());        // @117–@128 L11747
    if (src != null && src.hasComponent(ComponentType.FluidContainer)) {  // @129–@140 L11748–L11749
        float want   = stats.get(THIRST) * 2.0f;                          // @143–@155 L11750
        float amount = Math.min(src.getFluidContainer().getAmount(), want);  // @156–@167 L11751
        float frac   = amount / src.getFluidContainer().getAmount();      // @168–@177 L11752
        DrinkFluid(src, frac, false);                                     // @179–@187 L11753, DrinkFluid(InventoryItem,F,Z)Z
        if (GameServer.server && this instanceof IsoPlayer p)
            INetworkPacket.send(p, PacketType.SyncItemFields, p, src);    // @188–@230 L11754–L11755
    }
}                                                                         // @233 L11759
```

So: the option and flag tests are inside `autoDrink`, not in `updateThirst`. On a server the per-player flag is `IsoPlayer.autoDrink` (public boolean field; `getAutoDrink()Z` @0–@4 L9600 and `setAutoDrink(Z)V` @0–@5 L9604–L9605, both public); the `Core.getOptionAutoDrink()` test runs on every side that gets past the client return, the server included. The threshold is a hard-coded `0.1f` literal at @109, not `ZomboidGlobals.thirstLevelToAutoDrink`; the amount is `min(fluid amount, 2 × thirst)` of the found container, passed to `DrinkFluid` as a fraction; `ZomboidGlobals.thirstLevelReductionOnAutoDrink` plays no part. A jar-wide reference scan finds `thirstLevelToAutoDrink` and `thirstLevelReductionOnAutoDrink` written once each in `ZomboidGlobals.Load` (@113, @130) and read nowhere. `updateThirst @177` is the only call site of `autoDrink` in the jar (same scan).

### Not read

- What `IsoPlayer.getInstance()` holds in a dedicated-server process, so whether `getRunningThirstReduction()` can ever return 1.2 for a remote player there; `getWaterSource` and `DrinkFluid(InventoryItem,F,Z)` bodies; whether `Core.getOptionAutoDrink()` is true on a dedicated server.

## 2. `IsoGameCharacter.updateStats_Awake()` — protected

```java
protected void updateStats_Awake() {
    // STRESS decay (the arm the character-stats page lists as not covered)
    stats.remove(STRESS, (float)( ZomboidGlobals.stressReduction
                                * (double)M * (double)DMPD ));            // @0–@30  L10242

    // FATIGUE — agrees with facts/endurance-fatigue-sleep.md#fatigue
    float endDef = 1.0f - stats.get(ENDURANCE);                           // @31–@43 L10244
    if (endDef < 0.3f) endDef = 0.3f;                                     // @44–@55 L10245–L10246
    float sleepTrait = 1.0f;                                              // @56 L10249
    if (characterTraits.get(NEEDS_LESS_SLEEP)) sleepTrait = 0.7f;          // @58–@74 L10250–L10251
    if (characterTraits.get(NEEDS_MORE_SLEEP)) sleepTrait = 1.3f;          // @75–@91 L10253–L10254
    float rest = 1.0f;                                                    // @92 L10258
    if (isSitOnGround() || isSittingOnFurniture() || isResting()) rest = 1.5f;  // @94–@118 L10259–L10260
    stats.add(FATIGUE, (float)( ZomboidGlobals.fatigueIncrease * SD
                              * (double)endDef * (double)M * (double)DMPD
                              * (double)sleepTrait * getFatiqueMultiplier()
                              / (double)rest ));                          // @119–@170 L10262

    // HUNGER
    float appetite = getAppetiteMultiplier();                             // @171–@175 L10266 (protected)
    boolean exercising = (this instanceof IsoPlayer && ((IsoPlayer)this).IsRunning()
                          && isPlayerMoving())
                         || isCurrentState(SwipeStatePlayer.instance());  // @177–@208 L10267
    if (exercising) {
        if (moodles.getMoodleLevel(FOOD_EATEN) == 0)                      // @211–@221 L10268
            stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncreaseWhenExercise / 3.0
                                     * SD * (double)appetite * (double)M * (double)DMPD
                                     * getHungerMultiplier() ));          // @224–@274 L10269
        else
            stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncreaseWhenExercise
                                     * SD * (double)appetite * (double)M * (double)DMPD
                                     * getHungerMultiplier() ));          // @278–@324 L10271
    } else {
        if (moodles.getMoodleLevel(FOOD_EATEN) == 0)                      // @328–@338 L10275
            stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncrease
                                     * SD * (double)appetite * (double)M * (double)DMPD
                                     * getHungerMultiplier() ));          // @341–@387 L10276
        else
            stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncreaseWhenWellFed
                                     * SD * (double)M * (double)DMPD
                                     * getHungerMultiplier() ));          // @391–@433 L10278 (no appetite)
    }

    // IDLENESS and the idle-square timer
    updateIdleSquareTime();                                               // @434 L10283 (private)
    if (isInCombat()) {                                                   // @438–@442 L10285 (private)
        stats.reset(IDLENESS);                                            // @445–@455 L10286
    } else if (isCurrentlyIdle() && getCurrentSquare() != null) {         // @459–@470 L10287
        if (getCurrentSquare() == getLastSquare() && getIdleSquareTime() >= 1800.0f)   // @473–@492 L10288
            stats.set(IDLENESS, (float)( (double)stats.get(IDLENESS)
                                       + ZomboidGlobals.idleIncreaseRate * (double)M * (double)DMPD ));  // @495–@537 L10289
        if (getCurrentSquare().isInARoom())                               // @538–@545 L10292
            stats.set(IDLENESS, (float)( (double)stats.get(IDLENESS)
                                       + ZomboidGlobals.idleIncreaseRate / 3.0 * (double)M * (double)DMPD ));  // @548–@594 L10293
    } else if (!isSittingOnFurniture() && !isSitOnGround()) {             // @598–@609 L10296
        stats.set(IDLENESS, (float)( (double)stats.get(IDLENESS)
                                   - ZomboidGlobals.idleDecreaseRate * (double)M * (double)DMPD ));  // @612–@654 L10297
    }
}                                                                         // @655 L10300
```

Per update, awake:

- `STRESS −= 3.0e-5 × M × DMPD` — no `SD`, no trait, no gate (beyond the wake-state gate of § 3).
- `FATIGUE += 3.45e-5 × SD × max(0.3, 1 − endurance) × M × DMPD × sleepTrait × thermoFatigue ÷ rest` — agrees with `facts/endurance-fatigue-sleep.md#fatigue` term for term; the only reading this dump adds is the arithmetic order (double chain, one `d2f`). `NEEDS_MORE_SLEEP` is tested second, so a character holding both traits gets 1.3.
- `HUNGER += k × SD × appetite × M × DMPD × getHungerMultiplier()`, with `k` = `hungerIncreaseWhenExercise / 3` (6.4e-6) exercising with `FOOD_EATEN` level 0, `hungerIncreaseWhenExercise` (1.92e-5) exercising with `FOOD_EATEN` above 0, `hungerIncrease` (9.6e-6) not exercising with level 0; not exercising with `FOOD_EATEN` above 0 it is `hungerIncreaseWhenWellFed × SD × M × DMPD × getHungerMultiplier()`, which drops the appetite factor and is 0 at the shipped `HungerIncreaseWhenWellFed = 0`. Agrees with `facts/body-and-weight.md#hunger-thirst` (#0470, #0471, #0473, #0499).
- `appetite` = `getAppetiteMultiplier()F` @0–@52 L10322–L10329, protected: `a = 1 − HUNGER; if Hearty Appetite a *= 1.5; if Light Eater a *= 0.75; return a` (the two tests are independent, so both traits give 1.125 × (1 − HUNGER)). Agrees with #0474.
- `getHungerMultiplier()D` @0–@1 L14955, public: `return 1.0` (agrees with #0475). It is not overridden on `IsoPlayer` (the access scan walks `IsoPlayer → IsoLivingCharacter → IsoGameCharacter` and finds only the `IsoGameCharacter` declaration).
- "exercising" is `(this instanceof IsoPlayer && IsRunning() && isPlayerMoving()) || isCurrentState(SwipeStatePlayer.instance())` — running while moving, or in the melee swing state; sprinting is not tested here unless `isRunning()` is true while sprinting (not read).
- IDLENESS (in this order): the timer update; in combat → `IDLENESS` reset to its default 0; else if currently idle with a square → `+0.0005 × M × DMPD` when on the same square as last update with `idleSquareTime ≥ 1800`, and, independently, `+0.0005 / 3 × M × DMPD` when the square is in a room (both can apply in one update); else, unless sitting on furniture or the ground, `−0.006 × M × DMPD`. The writes use `Stats.set(get ± …)` rather than `add`, and so pass the `[0,1]` clamp once.

Helpers the arms call:

- `updateIdleSquareTime()V` @0–@54 L17641–L17648, private: if `getCurrentSquare() == getLastSquare()` then, while `idleSquareTime <= 3600`, `idleSquareTime += 1.0f × M × DMPD` (float); else `idleSquareTime = 0`. The field `idleSquareTime` is a private `float` on `IsoGameCharacter`; the public getter `getIdleSquareTime()F` exists, and no setter named `setIdleSquareTime` is declared on the `IsoPlayer` chain. The timer is therefore in game-seconds (by § 9) and saturates just above 3600.
- `isInCombat()Z` @0–@26 L17711, private: `stats.getNumVeryCloseZombies() > 0 || stats.getNumChasingZombies() >= 3` (both getters public on `Stats`).
- `isCurrentlyIdle()Z` @0–@212 L17651–L17685, public: false for a non-player; false when moving and walking, running or sprinting; false asleep; false sitting (furniture or ground) with the `ENDURANCE` moodle at level 1 or more; false reading; false with any queued character action (`characterActions` non-empty); false with `PANIC` moodle above 1; false in combat; on a server, false when the network AI state's enter state or exit state is set and is not `IdleState`; else true.
- `getFatiqueMultiplier()D` @0–@29 L14959–L14962, public: the thermoregulator's `getFatigueMultiplier()` when body damage and thermoregulator are non-null, else 1.0.

| constant | source | value |
|---|---|---|
| `stressReduction` | `ZomboidGlobals`, Lua `StressDecrease` | 3.0e-5 |
| `fatigueIncrease` | Lua `FatigueIncrease` | 3.45e-5 |
| endurance-deficit floor | literal `ldc 0.3` @45/@52 | 0.3 |
| Needs Less / More Sleep | literals @71 / @88 | 0.7 / 1.3 |
| rest divisor | literal @115 | 1.5 |
| `hungerIncrease` | Lua `HungerIncrease` | 9.6e-6 |
| `hungerIncreaseWhenExercise` | Lua `HungerIncreaseWhenExercise` | 1.92e-5 |
| exercise-on-empty divisor | literal `ldc2_w 3.0` @234 | 3.0 |
| `hungerIncreaseWhenWellFed` | Lua `HungerIncreaseWhenWellFed` | 0 |
| Hearty Appetite / Light Eater | literals in `getAppetiteMultiplier` @27 / @46 | 1.5 / 0.75 |
| idle same-square threshold | literal `ldc 1800.0` @488 | 1800 |
| `idleIncreaseRate` | Lua `IdleIncrease` | 5.0e-4 |
| in-room divisor | literal `ldc2_w 3.0` @569 | 3.0 |
| `idleDecreaseRate` | Lua `IdleDecrease` | 6.0e-3 |
| idle-timer cap | literal `ldc 3600.0` @15 of `updateIdleSquareTime` | 3600 |

Gates: none inside the method — no side gate, no animal return, no asleep test; all of that is in the caller (§ 3). Writes: `STRESS`, `FATIGUE`, `HUNGER`, `IDLENESS` and the private field `idleSquareTime`. There is no `ANGER`, `BOREDOM`, `UNHAPPINESS`, `SANITY`, `MORALE` or `ENDURANCE` write in the method (the full instruction list's `getstatic CharacterStat.*` operands are `STRESS`, `ENDURANCE` (read only, @36), `FATIGUE`, `HUNGER` and `IDLENESS`).

Who reads the timer: a jar-wide reference scan finds the field `idleSquareTime` touched only by `getIdleSquareTime` and `updateIdleSquareTime`, and `getIdleSquareTime()` called by `updateStats_Awake @485` and `BodyDamage.UpdateBoredom @49`. A takeover that skips the wake-state updater therefore freezes the timer boredom reads, and Lua cannot advance it (the updater is private and there is no setter).

`IsoGameCharacter.isRunning()Z` @0–@27 L13775–L13778 returns false when the `ENDURANCE` moodle is at level 3 or more and otherwise the `running` field; `isSprinting()Z` @0–@20 L13786–L13789 returns the separate `sprinting` field, false when `canSprint()` is false. So at endurance moodle level 3 or more a running character stops counting as exercising for hunger.

### Not read

- Whether the `running` field is also set while sprinting (so whether a sprint counts as "exercising" for hunger); the `Moodles.getMoodleLevel` body; the network-state branch of `isCurrentlyIdle` beyond its instruction list; what `BodyDamage.UpdateBoredom` does with the timer.

## 3. `IsoGameCharacter.updateStats_WakeState()` and the two sleeping paths

```java
protected void updateStats_WakeState() {
    if (isAnimal()) return;                                               // @0–@7  L10224–L10225
    if (GameServer.server
        || (!GameClient.client && IsoPlayer.getInstance() == this)) {     // @8–@24 L10227
        if (asleep) updateStats_Sleeping();                               // @27–@38 L10228–L10229 (field read)
        else        updateStats_Awake();                                  // @41 L10231
    }
}                                                                         // @45 L10234
```

The dispatch test is the public boolean field `asleep` read directly (`getfield` @28), not a call; `isAsleep()Z` @0–@4 L2984 returns the same field, so a handler's `character:isAsleep()` is the same test. The side gate is the one `updateThirst` carries (agrees with `facts/character-stats.md#updaters`, #2219).

`IsoGameCharacter.updateStats_Sleeping()V` @0 L10239 is a bare `return` (protected; agrees with #2218). `IsoPlayer.updateStats_Sleeping()V` (protected) overrides it:

```java
protected void updateStats_Sleeping() {
    // ENDURANCE
    float f = 2.0f;                                                       // @0  L3290
    if (IsoPlayer.allPlayersAsleep()) f *= GameTime.instance.getDeltaMinutesPerDay();  // @2–@16 L3291–L3292 (float fmul)
    stats.add(ENDURANCE, (float)( ZomboidGlobals.imobileEnduranceReduce
                                * SandboxOptions.instance.getEnduranceRegenMultiplier()
                                * (double)getRecoveryMod()
                                * (double)M * (double)f ));               // @17–@55 L3295

    // FATIGUE — agrees with facts/endurance-fatigue-sleep.md#sleep (#2276, #2277)
    if (stats.isAboveMinimum(FATIGUE)) { ... }                            // @56–@422 L3297–L3345

    // HUNGER
    if (moodles.getMoodleLevel(FOOD_EATEN) == 0) {                        // @423–@433 L3357
        float appetite = getAppetiteMultiplier();                         // @436–@440 L3358
        stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncreaseWhileAsleep * SD
                                 * (double)appetite * (double)M * (double)DMPD
                                 * getHungerMultiplier() ));              // @441–@486 L3359
    } else {
        stats.add(HUNGER, (float)( ZomboidGlobals.hungerIncreaseWhenWellFed * SD
                                 * ZomboidGlobals.hungerIncreaseWhileAsleep * SD
                                 * (double)M * getHungerMultiplier()
                                 * (double)DMPD ));                       // @490–@543 L3361
    }
}                                                                         // @544 L3363
```

Per update, asleep (player only, on the gated side):

- `ENDURANCE += 3.1e-5 × EndRegen × getRecoveryMod() × M × f`, `f = 2`, or `2 × DMPD` when `IsoPlayer.allPlayersAsleep()`; no fatigue term, no `SD`, no sitting factor (agrees with #2261 and `facts/endurance-fatigue-sleep.md#regen`). This arm lives inside the hook-skipped updaters: `IsoPlayer.updateEndurance` (which runs outside the hook) has no asleep test in its instruction list — its first branch is the sitting/resting test @14–@39 L3432–L3434 — so a takeover handler that skips the seven updaters also drops the sleep regeneration of endurance and must reproduce it.
- `FATIGUE` restoration: the dump's instructions @56–@422 match the page's decode offset for offset (bed factors, Insomniac 0.5, Night Owl 1.4, Needs Less Sleep 0.75 and Needs More Sleep 1.18 on the nominal hours, the 0.3 split, `dt = 1 / getMinutesPerDay() / 60 × M / 2` in float). The page's open point — "the unit of `dt` was not reconciled" — is settled by `GameTime.update` @469–@536 L519–L528: the clock advances `timeOfDay` (in hours) by exactly the same float expression `1 / getMinutesPerDay() / 60 × getMultiplier() / 2` per update, so `dt` is the game-hours elapsed this update, the 5 and 7 are game-hours, and fatigue above 0.3 clears 0.7 in 5 × t game-hours scaled by `f × bed`.
- `HUNGER += 1.0e-6 × SD × appetite × M × DMPD × 1.0` with `FOOD_EATEN` at level 0; with the moodle up, `HungerIncreaseWhenWellFed × SD × HungerIncreaseWhileAsleep × SD × M × 1.0 × DMPD` — the product carries `SD` twice and the asleep constant as a factor, and is 0 at the shipped `HungerIncreaseWhenWellFed = 0` (agrees with #0472 and #0473 on value).
- There is no `THIRST` arm in `IsoPlayer.updateStats_Sleeping`: asleep thirst is the `asleep` branch of `updateThirst` (§ 1).

`IsoPlayer.allPlayersAsleep()Z` @0–@77 L1048–L1057, public static: walks the static `IsoPlayer.players[0..numPlayers)`, counts non-null non-dead players and those of them `isAsleep()`, returns `count > 0 && count == asleepCount`. It reads the process's local-player array, not the server's connected-player list (`GameServer.getPlayers()`, which `GameTime.update` @603 uses for the hours-survived loop).

`timeOfSleep` and `delayToActuallySleep` are `protected float` fields declared on `IsoGameCharacter`. Public setters exist — `setTimeOfSleep(F)V` and `setDelayToSleep(F)V` on `IsoGameCharacter` — and no getter of either name is declared on the `IsoPlayer` chain, so Lua can write but not read them. A jar-wide reference scan finds the fields touched only by those setters and by `IsoPlayer.updateStats_Sleeping` (@270–@284), and the setters called only from `SleepingEvent.setPlayerFallAsleep(IsoPlayer,I,Z,Z)` @58–@65 L62 (`setTimeOfSleep(GameTime.getTimeOfDay())`) and `SleepingEvent.doDelayToSleep(IsoPlayer)` @262–@272 L201 (`setDelayToSleep(GameTime.getTimeOfDay() + Rand.Next(0, d))`). `doDelayToSleep` @0–@255 L159–L197 builds `d` from 0.3 (1.0 for Insomniac), `+ (1 + 0.2 × PAIN level)` while in pain, × 1.2 under any `STRESS` moodle, a bed factor (badBed 1.3, badBedPillow 1.25, goodBed 0.8, goodBedPillow 0.6, floor 1.6, floorPillow 1.45, averageBedPillow 1.0), × 0.5 for Night Owl, 0.1 when the sleeping-tablet effect exceeds 1000, then capped at 2.0 — so the fall-asleep delay is up to 2 game-hours, measured on the same hour scale `timeOfSleep` advances on. Both fields compare in un-wrapped hours: neither the advance nor the gate wraps at 24.

Non-stat writes of the sleeping path: `timeOfSleep` only (agrees with #2227).

| constant | source | value |
|---|---|---|
| sleep endurance factor | literal `fconst_2` @0 | 2.0 |
| `imobileEnduranceReduce` | Lua `ImobileEnduranceIncrease` | 3.1e-5 |
| EndRegen | `SandboxOptions.getEnduranceRegenMultiplier()` | 1.8 / 1.3 / 1.0 / 0.7 / 0.4 |
| `hungerIncreaseWhileAsleep` | Lua `HungerIncreaseWhileAsleep` | 1.0e-6 |
| `hungerIncreaseWhenWellFed` | Lua `HungerIncreaseWhenWellFed` | 0 |

### Not read

- What `IsoPlayer.players` and `numPlayers` hold in a dedicated-server process, and so whether `allPlayersAsleep()` can ever be true there (if the array is empty it returns false and the sleep endurance arm uses `f = 2` with no day-length term); `getRecoveryMod` beyond the page's ladder; the `SleepingEvent` callers of `setPlayerFallAsleep`.

## 4. `IsoGameCharacter.updateMorale()` — private

```java
private void updateMorale() {
    float m = 1.0f - stats.getNicotineStress() - 0.5f;                    // @0–@13  L10303
    m *= 1.0E-4f;                                                         // @14–@19 L10304 (ldc 9.9999997e-05)
    if (m > 0.0f) m += 0.5f;                                              // @20–@31 L10305–L10306
    stats.add(MORALE, PZMath.clamp(m, 0.0f, 1.0f));                       // @32–@48 L10308
}                                                                         // @49 L10309
```

`Stats.getNicotineStress()F` @0–@23 L132–L133 (public) is `STRESS.clamp(stats.get(STRESS) + stats.get(NICOTINE_WITHDRAWAL))`, i.e. stress plus nicotine withdrawal clamped to `[0,1]`.

Per update: with `ns = clamp(STRESS + NICOTINE_WITHDRAWAL, 0, 1)`, if `ns < 0.5` the add is `0.5 + (0.5 − ns) × 1e-4` — every update adds at least 0.5 to `MORALE`, which `Stats.add`'s `[0,1]` clamp pins at 1 within two updates; if `ns ≥ 0.5` the add is `clamp(≤ 0, 0, 1) = 0`. The updater never lowers morale, has no time factor (`M`, `DMPD` absent) and no `SD`. Reads: `STRESS`, `NICOTINE_WITHDRAWAL`. Writes: `MORALE` only. No gate (no side gate, no animal return of its own). No non-stat write.

| constant | source | value |
|---|---|---|
| midpoint | literal `ldc 0.5` @9 | 0.5 |
| rate | literal `ldc 1.0E-4` @15 | 1e-4 (float) |
| jump | literal `ldc 0.5` @27 | 0.5 |

### Not read

- Any other writer of `MORALE` that would pull it down between updates (the register's #2228 bounds the literal to `CharacterStat`, `IsoGameCharacter` and `Book`; the `Book` and other `IsoGameCharacter` writers were not dumped here).

## 5. `IsoGameCharacter.updateTripping()` — private

```java
private void updateTripping() {
    if (stats.isTripping()) stats.addTrippingRotAngle(0.06f);             // @0–@17 L10316–L10317 (ldc 0.05999999865889549)
}                                                                         // @20 L10319
```

Per update: while `Stats.tripping` is true, `Stats.trippingRotAngle += 0.06f`; no time factor. `Stats.isTripping()Z` @0–@4 L181, `addTrippingRotAngle(F)V` @0–@10 L197–L198 (`trippingRotAngle += f`), `getTrippingRotAngle()F` @0–@4 L189, `setTrippingRotAngle(F)V` and `setTripping(Z)V` @0–@5 L185–L186 are all public on `Stats`, an exposed class; the fields `tripping` and `trippingRotAngle` are private. So the angle is readable and writable from Lua through `getStats():getTrippingRotAngle()` / `setTrippingRotAngle(f)` / `addTrippingRotAngle(f)`. Agrees with #2225 on the write.

### Not read

- What sets `tripping` true and what consumes the angle beyond the register's grep (#2225).

## 6. `IsoGameCharacter.updateFitness()` — private

```java
private void updateFitness() {
    stats.set(FITNESS, (float)getPerkLevel(PerkFactory.Perks.Fitness) / 5.0f - 1.0f);   // @0–@24 L10312
}                                                                         // @25 L10313
```

Per update: `FITNESS = Fitness level / 5 − 1` in float (`i2f`, `ldc 5.0`, `fdiv`, `fconst_1`, `fsub`), so −1 at level 0, 0 at level 5, +1 at level 10 — inside the stat's `[−1,1]` bounds. Agrees with #2223. The perk getter is `IsoGameCharacter.getPerkLevel(PerkFactory$Perk)I` @0–@16 L4786–L4790, public: `getPerkInfo(perk)` then its `level`, or 0 when there is no `PerkInfo`. `PerkFactory$Perks.Fitness` is a static on an exposed class (`Perks.Fitness` from Lua). No time factor, no gate, no non-stat write.

### Not read

- `getPerkInfo`.

## 7. `IsoGameCharacter.updateEndurance()` — private (the base stub, not `IsoPlayer.updateEndurance`)

```java
private void updateEndurance() {
    stats.setLastEndurance(stats.get(ENDURANCE));                         // @0–@14  L10360
    if (isUnlimitedEndurance()) stats.reset(ENDURANCE);                   // @17–@34 L10361–L10362
}                                                                         // @35 L10364
```

Agrees with #2215. The stamp field is `Stats.lastEndurance`, a private `float`; `Stats.getLastEndurance()F` and `Stats.setLastEndurance(F)V` are public on the exposed `Stats`. A jar-wide reference scan finds the field touched by `Stats.<init>` @22, the getter and the setter only, `setLastEndurance` called only by this updater @14, and `getLastEndurance` called by nothing in the jar — so the stamp has no Java reader and dropping it changes nothing Java computes. `isUnlimitedEndurance()Z` @0–@10 L15469, public on `IsoGameCharacter`: `getCheats().isSet(CheatType.UNLIMITED_ENDURANCE)`. `PlayerCheats` is not in the exposer's class set, so a handler tests the cheat through `character:isUnlimitedEndurance()`, not through `getCheats()`. `Stats.reset(ENDURANCE)` sets the default, 1.

A text search of the install's `media/lua` tree for `LastEndurance` (2026-10-04) returns no file, so no vanilla Lua reads the stamp either.

### Not read

- Whether any workshop mod reads `getLastEndurance`.

## 8. `IsoGameCharacter.calculateStats()` — protected, and `IsoPlayer.calculateStats()` — protected

```java
protected void calculateStats() {                                         // IsoGameCharacter
    if (isAnimal()) return;                                               // @0–@7   L10196–L10197
    if (GameServer.server
        && !( ServerOptions.instance.sleepAllowed.getValue()
           && ServerOptions.instance.sleepNeeded.getValue() ))            // @8–@35  L10200
        stats.reset(FATIGUE);                                             // @38–@48 L10201
    if (LuaHookManager.TriggerHook("CalculateStats", this)) return;       // @49–@59 L10204–L10205
    updateEndurance();                                                    // @60 L10208
    updateTripping();                                                     // @64 L10210
    updateThirst();                                                       // @68 L10212
    updateStress();                                                       // @72 L10214
    updateStats_WakeState();                                              // @76 L10216
    updateMorale();                                                       // @80 L10218
    updateFitness();                                                      // @84 L10220
}                                                                         // @88 L10221

protected void calculateStats() {                                         // IsoPlayer
    if (!GameClient.client) super.calculateStats();                       // @0–@7 L3280–L3281 (invokespecial IsoLivingCharacter.calculateStats)
}                                                                         // @10 L3283
```

The reset condition reads two `ServerOptions` fields, `sleepAllowed` and `sleepNeeded`, each a `ServerOptions$BooleanServerOption` read through `getValue()`; fatigue is reset on a server unless both are true (agrees with #2723). The hook call is the two-argument overload `TriggerHook(String, Object)Z` with `this` as the only payload: `LuaHookManager.TriggerHook(String,Object)` @0–@42 L35–L41 puts the object in slot 0 of a one-element static array and calls `Event.trigger(env, caller, array)`, so a Lua handler receives exactly one argument, the character (`function(character)`). `IsoLivingCharacter` declares no `calculateStats`, so the `invokespecial` in `IsoPlayer` resolves to the `IsoGameCharacter` body. Order agrees with #2724; the client gate agrees with #2236.

### Not read

- `ServerOptions` default values of `SleepAllowed` and `SleepNeeded`.

## 9. The clock: `GameTime.getMultiplier()`, `getDeltaMinutesPerDay()`, `getMinutesPerDay()`, `getGameWorldSecondsSinceLastUpdate()`

```java
public float getDeltaMinutesPerDay() { return 30.0f / minutesPerDay; }    // @0–@6 L440
public float getMinutesPerDay()      { return minutesPerDay; }            // @0–@4 L960

public float getMultiplier() {                                            // L984–L1005
    if (!GameServer.server && !GameClient.client && IsoPlayer.getInstance() != null
        && IsoPlayer.allPlayersAsleep())
        return 200.0f * (30.0f / PerformanceSettings.getLockFPS());       // @0–@35 L984–L985 (single-player sleep)
    float m = 1.0f;                                                       // @36 L988
    if (GameServer.server && GameServer.fastForward)
        m = (float)ServerOptions.instance.fastForwardMultiplier.getValue() / getDeltaMinutesPerDay();  // @38–@65 L990–L991
    else if (GameClient.client && GameClient.fastForward && GameWindow.isIngameState())
        m = (float)ServerOptions.instance.fastForwardMultiplier.getValue() / getDeltaMinutesPerDay();  // @69–@102 L992–L993
    m *= multiplier;                                                      // @103 L996
    m *= fpsMultiplier;                                                   // @110 L997
    m *= multiplierBias;                                                  // @117 L998
    m *= perObjectMultiplier;                                             // @124 L999
    m *= GameTime.getSlomoMultiplier();                                   // @131 L1000 (DebugOptions slow-motion)
    m *= 0.8f;                                                            // @137 L1003
    return m;                                                             // @143 L1005
}

public float getGameWorldSecondsSinceLastUpdate() {                       // @0–@14 L214–L215
    return getTimeDelta() * (1440.0f / getMinutesPerDay());
}
public float getTimeDelta() { return getTimeDeltaFromMultiplier(getMultiplier()); }   // @0–@8 L1013
public float getTimeDeltaFromMultiplier(float m) {                        // @0–@14 L1017
    return m / 0.8f / multiplierBias / 60.0f;
}
```

The factors, as written:

- `minutesPerDay`: a field initialised to 30 in `GameTime.<init>` @141–@143 L106; the day length in real minutes (set from the `DayLength` sandbox option; the setter's caller was not dumped). So `DMPD = 30 / dayLengthMinutes`: 0.5 at a 60-minute day, 1.0 at 30.
- `fpsMultiplier`: on a dedicated server `GameServer.main` @4377–@4424 L1118–L1123 computes an instantaneous rate `1000 / frameMillis`, smooths it as `fps += min((inst − fps) × 0.05, 1.0)` (NaN skipped), and stores `fpsMultiplier = 60 / fps`; on a client `FPSTracking.frameStep` @28–@139 L28–L47 stores `60 × frameSeconds` capped at 5. Either way it is `60 ×` (seconds per frame) — 1.0 at 60 frames per second.
- `multiplier`: the time-speed field, 1 in `<init>` @176–@177 L116, written by `setMultiplier(F)` @0–@5 L1009.
- `multiplierBias`: 1 in `<init>` @33–@35 L83; `SandboxOptions.updateFromLua` @0–@18 L421–L422 sets 1.2 for `LastStand` and then @72–@137 L430–L436 always overwrites it from a `tableswitch` on `SandboxOptions.speed` (1 → 0.8, 2 → 0.9, 3 → 1.0, 4 → 1.1, 5 → 1.2); `speed` is a public `int` set to 3 in `SandboxOptions.<init>` @4–@6 L59 and written nowhere else in the jar (reference scan), so `multiplierBias` is 1.0 after every sandbox load.
- `perObjectMultiplier`: 1 in `<init>` @38–@40 L85; `MovingObjectUpdateSchedulerUpdateBucket.update(I)` @0–@8 L38 sets it to the bucket's `frameMod` around a bucket's object updates and back to 1 @152–@156 L60 (also `postupdate` @8, @109) — an object updated every Nth frame sees an N-times multiplier.
- `0.8f`: a literal.

What one update is worth: `GameTime.update` @469–@536 L519–L528 advances `timeOfDay` (hours) by `1 / getMinutesPerDay() / 60 × getMultiplier() / 2` per update (or with `getUnmoddedMultiplier()` under `Core.lastStand`, @488–@511 L520–L521; zero under the debug freeze-time option). In game-seconds that is `3600 × M / (120 × minutesPerDay) = 30 × M / minutesPerDay = M × DMPD`. So **game-seconds elapsed this update = `getMultiplier() × getDeltaMinutesPerDay()`**, read inside the hook (where `perObjectMultiplier` is whatever the vanilla updaters would have seen in that same call). `getGameWorldSecondsSinceLastUpdate()` equals `M / 0.8 / multiplierBias / 60 × 1440 / minutesPerDay = M × DMPD / multiplierBias`, which is the same number while `multiplierBias` is 1.0 (every sandbox load, as above). Check at a 60-minute day, 60 FPS, time speed 1: `M = 0.8`, `DMPD = 0.5`, so 0.4 game-seconds per frame, 24 per real second, 86 400 per real hour — one game day per real hour, as the day length says.

Lua reach: `GameTime` and `SandboxOptions` are in the exposer's class set; `getGameTime()` and `getSandboxOptions()` are public static on `LuaManager$GlobalObject`; `getMultiplier()F`, `getDeltaMinutesPerDay()F`, `getMinutesPerDay()F`, `getGameWorldSecondsSinceLastUpdate()F`, `getTimeDelta()F`, `getTrueMultiplier()F`, `getUnmoddedMultiplier()F` and `getTimeOfDay()F` are public. Two other getters for comparison: `getTrueMultiplier()` @0–@8 L1052 is `multiplier × perObjectMultiplier` (no frame term — not per update); `getThirtyFPSMultiplier()` @0–@7 L1057 is `getMultiplier() / 1.6`.

Lua arithmetic note: Kahlua numbers are doubles, so a handler that multiplies the same factors in Lua reproduces the Java `double` chains (`SD`, the `ZomboidGlobals` doubles, the thermoregulator doubles) exactly only if each Java `float` factor (`M`, `DMPD`, `appetite`, `getRecoveryMod()`, the trait literals) enters as the float value the getter returns, and the final narrowing to float happens when the Lua double crosses into `Stats.add`'s `float` parameter (taken to match `d2f`; not read, § 10). The float-only chains — `updateIdleSquareTime`, the sleep `dt` and fatigue removal, `updateMorale`, `updateFitness`, the sleep endurance factor `f` — Java computes entirely in float, so a Lua double reproduction of them can differ in the last bit. Literals the Java code holds as floats (0.3, 0.7, 1.3, 1.5, 0.5, 1e-4, 0.06) are not exactly their decimal value; a bit-close reproduction writes them as the float values the dump prints (e.g. `0.30000001192092896`).

| factor | source | value |
|---|---|---|
| `0.8` | literal @138 L1003 | 0.8 (float) |
| `minutesPerDay` default | `GameTime.<init>` @141 | 30 |
| `multiplierBias` | `SandboxOptions.updateFromLua` switch on `speed` = 3 | 1.0 |
| fast-forward | `ServerOptions.fastForwardMultiplier` (double) ÷ `DMPD` | server-wide while `GameServer.fastForward` |

### Not read

- What sets `GameServer.fastForward` (presumably every player asleep on the server) and the default of `ServerOptions.FastForwardMultiplier`; the writer of `minutesPerDay` from the `DayLength` sandbox value; whether players on a dedicated server are updated through the `MovingObjectUpdateScheduler` buckets (and so ever see `perObjectMultiplier ≠ 1`); the slow-motion debug multiplier's value outside debug.

## 10. `Stats.get`, `set`, `add`, `remove`, `reset` — all public on `zombie/characters/Stats`

```java
public float   get(CharacterStat s)          { return stats.getOrDefault(s, s.getDefaultValue()); }  // @0–@23 L77
public boolean set(CharacterStat s, float v) {                                                         // @0–@41 L81–L84
    float old = get(s); float c = s.clamp(v); stats.put(s, c); return c != old;
}
public boolean add(CharacterStat s, float d)    { return set(s, get(s) + d); }     // @0–@12 L88
public boolean remove(CharacterStat s, float d) { return add(s, -d); }             // @0–@7  L92
public boolean reset(CharacterStat s)           { return set(s, s.getDefaultValue()); }   // @0–@9 L96
public boolean isAboveMinimum(CharacterStat s)  { return !isAtMinimum(s); }        // @0–@13 L108
```

`CharacterStat.clamp(F)F` @0–@12 L70 is `PZMath.clamp(v, minimumValue, maximumValue)`, and `PZMath.clamp(FFF)F` @0–@17 L102–L110 is `v < min ? min : (v > max ? max : v)` (a NaN passes through unclamped, since both float compares fail). So all four writers clamp once to the stat's bounds and return whether the stored float changed (`fcmpl` against the pre-write value) — `add` and `remove` return `set`'s answer (agrees with #2208, extended to `add`, `remove` and `reset`). `add` sums in float (`fadd`), so a delta below half the float spacing at the current value is lost: for a stat in `[0.5, 1)` the spacing is 2^-24 ≈ 6.0e-8, so a delta under about 3e-8 does not move it (the per-update thirst add at default settings, 8e-6 × 0.4 = 3.2e-6, is well clear). `get`, `set`, `add`, `remove`, `reset`, `isAboveMinimum`, `getNicotineStress`, `getNumVeryCloseZombies`, `getNumChasingZombies`, `getLastEndurance`, `setLastEndurance`, `isTripping`, `getTrippingRotAngle`, `setTrippingRotAngle`, `addTrippingRotAngle` are public; `CharacterStat.clamp`, `getDefaultValue`, `getMinimumValue`, `getMaximumValue` are public; `Stats` and `CharacterStat` are both in the exposer's class set.

### Not read

- `CharacterStat.isAtMinimum(F)` (`Stats.isAtMinimum` @0–@9 L100 delegates to it with `get(s)`); how Kahlua narrows a Lua double to the `float` parameter of `add`/`set` (assumed round-to-nearest, as `d2f`).

## 11. `Hook.CalculateStats.Add` / `Remove` — `LuaHookManager` and `Event`

The `Hook` table: `LuaHookManager.register(Platform, KahluaTable)` @0–@16 L162–L164 rawsets a new table as the global `Hook` and calls `AddEvents()`, which @0–@40 L127–L135 calls `AddEvent` for `AutoDrink`, `UseItem`, `Attack`, `CalculateStats`, `ContextualAction`, `WeaponHitCharacter`, `WeaponSwing` and `WeaponSwingHitPoint`. `AddEvent(String)` @0–@82 L110–L124 returns if the name exists, else creates `new Event(name, EventList.size())`, adds it to `EventList` and `EventMap`, and calls `event.register(platform, Hook)`. `Event.register` @0–@42 L120–L125 rawsets a fresh table at `Hook[name]` holding two Java functions, `Add` (an `Event$Add`) and `Remove` (an `Event$Remove`).

```java
// Event$Add.call(LuaCallFrame frame, int nArgs)                          @0–@42 L76–L83
if (LuaCompiler.rewriteEvents) return 0;                                  // @0–@7
Object a0 = frame.get(0);                                                 // @8–@13 L80
if (a0 instanceof LuaClosure) e.callbacks.add((LuaClosure)a0);            // @15–@40 L80–L81
return 0;

// Event$Remove.call(LuaCallFrame frame, int nArgs)                       @0–@41 L96–L104
if (LuaCompiler.rewriteEvents) return 0;                                  // @0–@7
Object a0 = frame.get(0);                                                 // @8–@13 L100
if (a0 instanceof LuaClosure) e.callbacks.remove((LuaClosure)a0);         // @14–@39 L101–L102
return 0;
```

So the Lua shape is `Hook.CalculateStats.Add(fn)` with a dot: argument 0 must be the Lua function itself. Called with a colon (`Hook.CalculateStats:Add(fn)`), argument 0 is the `Hook.CalculateStats` table, the `instanceof LuaClosure` test fails, and the call silently does nothing. A Java function or any non-closure argument is likewise ignored without error. `Add` does not de-duplicate — adding the same closure twice puts it in `callbacks` twice and it runs twice. `Remove` is `ArrayList.remove(Object)`: it removes the first element `equals` to the argument, so it takes the same closure object that was added (a fresh closure with the same body is a different object; `LuaClosure` identity equality is assumed, Not read), and removes one registration per call. Both return 0 Lua results. Both are no-ops while `LuaCompiler.rewriteEvents` is true, a static that `LuaManager.RunLuaInternal(String, boolean)` sets from its boolean argument @84–@85 L1366 before running a file and clears @428–@429 L1409 after — so an `Add` executed while a file is being run with that flag set is dropped.

`LuaHookManager.TriggerHook(String, Object)Z` @0–@42 L35–L41: false when the name is not in `EventMap`; else slot 0 of the static one-element array `a` is set to the payload and `Event.trigger(LuaManager.env, LuaManager.caller, a)` decides. `Event.trigger` @0–@11 L26–L27 returns false when `callbacks` is empty; otherwise it calls each closure through `LuaCaller.protectedCallVoid` (@82–@89 L36 in the slow-event-check branch, @269–@276 L55 otherwise), logs an exception through `ExceptionLogger.logException` without stopping the loop, re-indexes when a callback removed itself (`callbacks.contains` @201–@213 / @329–@341), and returns true @222 L49 / @350 L64. Agrees with #2238: the handler's return value is discarded, and any registrant makes the hook answer true. A handler that raises still makes `calculateStats` return — the seven updaters stay skipped for that update.

`LuaHookManager` and `Event` are not in the exposer's class set; the only Lua surface is the `Hook` global table and its `Add`/`Remove` functions.

### Not read

- `LuaClosure.equals` (identity assumed); which callers pass `true` to `RunLuaInternal`'s rewrite flag (a reload path is the likely one); `LuaCaller.protectedCallVoid`.

## 12. Lua reachability

Access flags were read with a session-scoped scanner rebuilt from `pz-b42/tools/cp.py` and `dis.py`, walking each class up its superclass chain; exposure is membership in the class constants of `LuaManager$Exposer.exposeAll` (`./pz.sh refs`). Every class in the table except `PlayerCheats`, `LuaHookManager` and `Event` is in that set: `IsoGameCharacter`, `IsoPlayer`, `GameTime`, `SandboxOptions`, `Stats`, `CharacterStat`, `BodyDamage`, `Thermoregulator`, `Moodles`, `MoodleType`, `CharacterTraits`, `CharacterTrait`, `PerkFactory$Perks`, `PerkFactory$Perk`, `CheatType`, `IsoGridSquare`, `SwipeStatePlayer`, `Core`. `IsoLivingCharacter` is not in the set, and declares none of the members below. A public field is not a Lua door: the register's #2745 states the only Lua route to a Java field is reflective and debug-only.

| method | declared on | public? | arity (descriptor) |
|---|---|---|---|
| `autoDrink` | `IsoGameCharacter` | yes | 0 `()V` |
| `getPerkLevel` | `IsoGameCharacter` | yes | 1 `(PerkFactory$Perk)I` |
| `IsoPlayer.getFitness` (the exercise object, not the stat) | `IsoPlayer` | yes | 0 `()Fitness` |
| `getStats` | `IsoGameCharacter` | yes | 0 |
| `Stats.getLastEndurance` / `setLastEndurance` | `Stats` | yes / yes | 0 `()F` / 1 `(F)V` |
| `isUnlimitedEndurance` | `IsoGameCharacter` | yes | 0 |
| `getCheats` → `PlayerCheats.isSet` | `IsoGameCharacter` / `PlayerCheats` | yes / yes, but `PlayerCheats` not exposed | 0 / 1 |
| `isAsleep` | `IsoGameCharacter` | yes | 0 |
| `isSitOnGround` | `IsoGameCharacter` | yes | 0 |
| `isSittingOnFurniture` | `IsoGameCharacter` | yes | 0 |
| `isResting` | `IsoGameCharacter` | yes (a public field `isResting` also exists) | 0 |
| `isSneaking` | `IsoGameCharacter` | yes | 0 |
| `getMoodles` / `Moodles.getMoodleLevel` | `IsoGameCharacter` / `Moodles` | yes / yes | 0 / 1 `(MoodleType)I` |
| `getCharacterTraits` / `CharacterTraits.get` | `IsoGameCharacter` / `CharacterTraits` | yes / yes | 0 / 1 `(CharacterTrait)Z` |
| `hasTrait` | `IsoGameCharacter` | yes | 1 `(CharacterTrait)Z`; also `(CharacterTrait[])Z` |
| `getPlayerNum` | `IsoPlayer` | yes (final) | 0 |
| `isGhostMode` | `IsoPlayer` | yes | 0 (returns `isInvisible()`) |
| `isLocalPlayer` | `IsoPlayer` | yes | 0; static overloads `(Object)Z`, `(IsoGameCharacter)Z` |
| `getBodyDamage` / `BodyDamage.getThermoregulator` | `IsoGameCharacter` / `BodyDamage` | yes / yes | 0 / 0 |
| `Thermoregulator.getFatigueMultiplier` | `Thermoregulator` | yes | 0 `()D` |
| `Thermoregulator.getFluidsMultiplier` (the thirst term) | `Thermoregulator` | yes | 0 `()D` |
| `Thermoregulator.getEnergyMultiplier` | `Thermoregulator` | yes | 0 `()D` |
| `Thermoregulator.getThirstMultiplier` | — | not declared | — |
| `getFatiqueMultiplier` | `IsoGameCharacter` | yes | 0 `()D` |
| `getThirstMultiplier` | `IsoGameCharacter` | yes | 0 `()D` |
| `getHungerMultiplier` | `IsoGameCharacter` | yes | 0 `()D` (constant 1.0) |
| `getAppetiteMultiplier` | `IsoGameCharacter` | **no — protected** | 0 `()F` |
| `getRunningThirstReduction` | `IsoGameCharacter` | **no — private** | 0 `()D` |
| `isInCombat` | `IsoGameCharacter` | **no — private** | 0 |
| `updateIdleSquareTime` | `IsoGameCharacter` | **no — private** | 0 |
| `getIdleSquareTime` | `IsoGameCharacter` | yes | 0 `()F`; no setter declared |
| `isCurrentlyIdle` | `IsoGameCharacter` | yes | 0 |
| `isPlayerMoving` | `IsoGameCharacter`, `IsoPlayer` | yes | 0 |
| `isCurrentState` / `SwipeStatePlayer.instance` | `IsoGameCharacter` / `SwipeStatePlayer` | yes / yes (static) | 1 `(State)Z` / 0 |
| `getCurrentSquare` / `getLastSquare` / `IsoGridSquare.isInARoom` | `IsoMovingObject` / `IsoGridSquare` | yes | 0 |
| `Stats.getNumVeryCloseZombies` / `getNumChasingZombies` | `Stats` | yes | 0 |
| `Stats.getNicotineStress` | `Stats` | yes | 0 |
| `Stats.isTripping` / `getTrippingRotAngle` / `setTrippingRotAngle` / `addTrippingRotAngle` | `Stats` | yes | 0 / 0 / 1 / 1 |
| `getSandboxOptions()` → `getStatsDecreaseMultiplier` | `LuaManager$GlobalObject` / `SandboxOptions` | yes (static) / yes | 0 / 0 `()D` |
| `SandboxOptions.getEnduranceRegenMultiplier` | `SandboxOptions` | yes | 0 `()D` |
| `getRecoveryMod` | `IsoGameCharacter` | yes | 0 `()F` |
| `getPacingMod` | `IsoGameCharacter` | yes | 0 `()F` |
| `getHyperthermiaMod` | `IsoGameCharacter` | yes | 0 `()F` |
| `getFatigueMod` | `IsoGameCharacter` | yes | 0 `()F` |
| `isRunning` | `IsoGameCharacter` | yes | 0 |
| `IsRunning` | `IsoPlayer` | yes | 0 (returns `isRunning()`) |
| `isSprinting` | `IsoGameCharacter` | yes | 0 |
| `isDraggingCorpse` | `IsoGameCharacter` | yes | 0 |
| `getCurrentSpeed` | — | not declared on the `IsoPlayer` chain | — |
| `IsoPlayer.currentSpeed` (the field the drain tests) | `IsoPlayer` | public **field**, no getter — not Lua-readable (#2745) | — |
| `getMoveSpeed` | `IsoPlayer` | yes | 0 `()F` (not the field the drain tests) |
| `getAutoDrink` / `setAutoDrink` | `IsoPlayer` | yes / yes | 0 / 1 `(Z)V` |
| `setTimeOfSleep` / `setDelayToSleep` | `IsoGameCharacter` | yes / yes | 1 `(F)V` each; no getters |
| `getBedType` | `IsoGameCharacter` | yes | 0 |
| `IsoPlayer.allPlayersAsleep` | `IsoPlayer` | yes (static) | 0 |
| `IsoPlayer.getInstance` | `IsoPlayer` | yes (static) | 0 |
| `getGameTime()` → `getMultiplier` / `getDeltaMinutesPerDay` / `getMinutesPerDay` / `getGameWorldSecondsSinceLastUpdate` | `LuaManager$GlobalObject` / `GameTime` | yes | 0 |
| `Core.getOptionAutoDrink` | `Core` | yes | 0 |
| `exert` | `IsoGameCharacter` | yes | 1 `(F)V` |
| `calculateStats` | `IsoGameCharacter`, `IsoPlayer` | **no — protected** | 0 |
| `updateStats_WakeState` / `updateStats_Awake` / `updateStats_Sleeping` | `IsoGameCharacter` (+ `IsoPlayer.updateStats_Sleeping`) | **no — protected** | 0 |
| `updateEndurance`, `updateTripping`, `updateThirst`, `updateStress`, `updateMorale`, `updateFitness` | `IsoGameCharacter` | **no — private** | 0 |
| `IsoPlayer.updateEndurance` | `IsoPlayer` | **no — private** | 0 |

Consequences for the handler: it cannot call any vanilla updater (all protected or private), so every arm is re-implemented; the appetite factor is rebuilt as `(1 − HUNGER) × 1.5 (Hearty Appetite) × 0.75 (Light Eater)`; the combat test as `getNumVeryCloseZombies() > 0 or getNumChasingZombies() >= 3`; the running thirst factor as 1.2 only when the character is `IsoPlayer.getInstance()` and running; the idle-square timer cannot be advanced from Lua at all; and the speed test of the endurance drain is out of reach but runs outside the hook anyway.

## Claims candidates

Each line is worded as a claim in the register's grammar, grade C, bound `C-only` (read from the bytecode, not exercised on a live server), from this build's jar. Lines marked (supersedes-check) touch an existing row.

1. Awake, thirst rises per update by `ThirstIncrease × StatsDecrease × multiplier × running factor × deltaMinutesPerDay × thirst trait × thermoregulator fluids multiplier`, multiplied in double and narrowed to float once — pointer: jar:IsoGameCharacter.updateThirst @125–@175 L10381 — grade C
2. Asleep, thirst rises per update by `ThirstSleepingIncrease × StatsDecrease × multiplier × deltaMinutesPerDay × thirst trait`, with neither the running factor nor the thermoregulator term — pointer: jar:IsoGameCharacter.updateThirst @74–@121 L10378–L10379 — grade C
3. The High Thirst and Low Thirst factors are two independent tests, so a character holding both traits gets a thirst trait factor of 1.0 — pointer: jar:IsoGameCharacter.updateThirst @0–@37 L10367–L10374 — grade C
4. The thirst updater's asleep test reads the `asleep` field directly, and its ghost-mode test is the player's invisibility flag, since `IsoPlayer.isGhostMode` returns `isInvisible()` — pointer: jar:IsoGameCharacter.updateThirst @57–@75 L10377–L10378; jar:IsoPlayer.isGhostMode @0–@4 L1118 — grade C
5. `autoDrink` is `public void autoDrink()` on `IsoGameCharacter` and carries its own gates: it returns on a client, on a server for a player whose `autoDrink` flag is off, when `Core.getOptionAutoDrink()` is false, while asleep, grappling, knocked down, falling, aiming or climbing, and when the `AutoDrink` hook answers true — pointer: jar:IsoGameCharacter.autoDrink @0–@98 L11727–L11740 — grade C
6. `autoDrink` drinks only when thirst exceeds a hard-coded 0.1 literal, and drinks `min(container amount, 2 × thirst)` of the found water source as a fraction through `DrinkFluid`, then on a server sends `SyncItemFields` for the container — pointer: jar:IsoGameCharacter.autoDrink @99–@230 L11743–L11755 — grade C (supersedes-check: #0480)
7. `ZomboidGlobals.thirstLevelToAutoDrink` and `thirstLevelReductionOnAutoDrink` are loaded from the Lua table and read by nothing else in the jar — pointer: jar:ZomboidGlobals.Load @100–@130; jar:jar-wide reference scan thirstLevelToAutoDrink, thirstLevelReductionOnAutoDrink — grade C (supersedes-check: #0480)
8. Awake, stress falls per update by `StressDecrease × multiplier × deltaMinutesPerDay`, with no StatsDecrease, trait or moodle term — pointer: jar:IsoGameCharacter.updateStats_Awake @0–@30 L10242 — grade C
9. The awake hunger arm adds `rate × StatsDecrease × appetite × multiplier × deltaMinutesPerDay × getHungerMultiplier()`, the rate being `HungerIncreaseWhenExercise ÷ 3` exercising with the food-eaten moodle at 0, `HungerIncreaseWhenExercise` exercising with it up and `HungerIncrease` idle with it at 0, and adds `HungerIncreaseWhenWellFed × StatsDecrease × multiplier × deltaMinutesPerDay × getHungerMultiplier()` idle with it up — pointer: jar:IsoGameCharacter.updateStats_Awake @171–@433 L10266–L10278 — grade C
10. Exercising, for the awake hunger arm, is a player running while moving or any character in the melee swing state — pointer: jar:IsoGameCharacter.updateStats_Awake @177–@208 L10267 — grade C
11. `isRunning` returns false at endurance moodle level 3 or above, so an exhausted runner stops counting as exercising for hunger — pointer: jar:IsoGameCharacter.isRunning @0–@27 L13775–L13778 — grade C
12. The appetite factor is `(1 − hunger)`, times 1.5 for Hearty Appetite and 0.75 for Light Eater as two independent tests, and `getAppetiteMultiplier` is protected, so Lua rebuilds it rather than calling it — pointer: jar:IsoGameCharacter.getAppetiteMultiplier @0–@52 L10322–L10329 — grade C
13. In combat — more than zero very-close zombies or at least three chasing — the awake updater resets idleness to 0, and `isInCombat` is private — pointer: jar:IsoGameCharacter.isInCombat @0–@26 L17711; jar:IsoGameCharacter.updateStats_Awake @438–@456 L10285–L10286 — grade C
14. Idle and on a square, idleness rises by `IdleIncrease × multiplier × deltaMinutesPerDay` once the idle-square timer reaches 1800 on an unchanged square and, independently, by a third of that indoors; not idle and not sitting, it falls by `IdleDecrease × multiplier × deltaMinutesPerDay` — pointer: jar:IsoGameCharacter.updateStats_Awake @459–@654 L10287–L10297 — grade C
15. The idle-square timer advances by `multiplier × deltaMinutesPerDay` per update while the square is unchanged and the timer is at most 3600, and resets to 0 on a square change; its updater is private and no setter exists, so Lua cannot advance it — pointer: jar:IsoGameCharacter.updateIdleSquareTime @0–@54 L17641–L17648 — grade C
16. The idle-square timer is read only by the awake updater and by `BodyDamage.UpdateBoredom`, so a takeover that skips the wake-state updater freezes the timer boredom reads — pointer: jar:IsoGameCharacter.updateStats_Awake @485; jar:BodyDamage.UpdateBoredom @49; jar:jar-wide reference scan idleSquareTime, getIdleSquareTime — grade C
17. The awake updater writes stress, fatigue, hunger, idleness and the idle-square timer and nothing else — pointer: jar:IsoGameCharacter.updateStats_Awake @0–@655 L10242–L10300 — grade C
18. The asleep endurance regeneration is in `IsoPlayer.updateStats_Sleeping`, one of the hook-skipped updaters, and `IsoPlayer.updateEndurance` has no asleep test, so a registered `CalculateStats` handler also drops sleep's endurance regeneration — pointer: jar:IsoPlayer.updateStats_Sleeping @0–@55 L3290–L3295; jar:IsoGameCharacter.calculateStats @49–@59 L10204–L10205; jar:IsoPlayer.updateEndurance @0–@39 L3427–L3434 — grade C
19. Asleep with the food-eaten moodle at 0, hunger rises per update by `HungerIncreaseWhileAsleep × StatsDecrease × appetite × multiplier × deltaMinutesPerDay × getHungerMultiplier()`; with it up, by a product of `HungerIncreaseWhenWellFed`, `HungerIncreaseWhileAsleep` and StatsDecrease twice, which is 0 at the shipped constant — pointer: jar:IsoPlayer.updateStats_Sleeping @423–@543 L3357–L3361 — grade C
20. `IsoPlayer.updateStats_Sleeping` has no thirst arm; asleep thirst is the asleep branch of `updateThirst` — pointer: jar:IsoPlayer.updateStats_Sleeping @0–@544 L3290–L3363; jar:IsoGameCharacter.updateThirst @74–@121 L10378–L10379 — grade C
21. The sleep fatigue clock `dt` equals the per-update advance of `GameTime.timeOfDay`, so it is game-hours and the 5- and 7-hour constants of sleep restoration are game-hours — pointer: jar:IsoPlayer.updateStats_Sleeping @245–@266 L3325; jar:GameTime.update @469–@536 L519–L528 — grade C (settles the unreconciled-unit sentence beside #2276/#2277)
22. `timeOfSleep` is set to the time of day when the player falls asleep and `delayToActuallySleep` to the time of day plus a random 0 to `d` hours, `d` built from Insomniac, pain, stress, bed type, Night Owl and sleeping tablets and capped at 2 — pointer: jar:SleepingEvent.setPlayerFallAsleep @58–@65 L62; jar:SleepingEvent.doDelayToSleep @0–@272 L159–L201 — grade C
23. `timeOfSleep` and `delayToActuallySleep` are protected fields with public setters `setTimeOfSleep(F)` and `setDelayToSleep(F)` and no getters — pointer: jar:IsoGameCharacter.setTimeOfSleep @2; jar:IsoGameCharacter.setDelayToSleep @2; jar:jar-wide reference scan timeOfSleep, delayToActuallySleep — grade C
24. `IsoPlayer.allPlayersAsleep` counts the process's local `IsoPlayer.players` array, not the server's connected players — pointer: jar:IsoPlayer.allPlayersAsleep @0–@77 L1048–L1057 — grade C
25. The morale updater adds `0.5 + (0.5 − ns) × 1e-4` while stress plus nicotine withdrawal is below 0.5 and 0 otherwise, so it pins morale at 1 and never lowers it — pointer: jar:IsoGameCharacter.updateMorale @0–@48 L10303–L10308; jar:Stats.getNicotineStress @0–@23 L132–L133 — grade C
26. The tripping angle is readable and writable from Lua through the public `Stats` getters and setters — pointer: jar:Stats.getTrippingRotAngle @0–@4 L189; jar:Stats.addTrippingRotAngle @0–@10 L197–L198 — grade C
27. `Stats.getLastEndurance` has no caller in the jar and no vanilla Lua file names it, so the last-endurance stamp has no vanilla reader — pointer: jar:jar-wide reference scan getLastEndurance, lastEndurance; jar:IsoGameCharacter.updateEndurance @0–@14 L10360 — grade C
28. The unlimited-endurance test is `isUnlimitedEndurance()`, public, over `PlayerCheats`, which is not exposed — pointer: jar:IsoGameCharacter.isUnlimitedEndurance @0–@10 L15469 — grade C
29. The server fatigue reset reads `ServerOptions.sleepAllowed` and `ServerOptions.sleepNeeded` and runs unless both are true — pointer: jar:IsoGameCharacter.calculateStats @8–@48 L10200–L10201 — grade C
30. `calculateStats` fires the hook through `TriggerHook(String, Object)` with the character as the only payload, so a `Hook.CalculateStats` handler receives one argument, the character — pointer: jar:IsoGameCharacter.calculateStats @49–@53 L10204; jar:LuaHookManager.TriggerHook @0–@40 L35–L38 — grade C
31. Game-seconds elapsed in one update equal `GameTime.getMultiplier() × getDeltaMinutesPerDay()`, since the clock advances the time of day by `getMultiplier() ÷ (120 × minutesPerDay)` hours per update — pointer: jar:GameTime.update @469–@536 L519–L528; jar:GameTime.getDeltaMinutesPerDay @0–@6 L440 — grade C
32. `getMultiplier` is the product of the time-speed field, the frame multiplier, the sandbox bias, the per-object bucket multiplier, the slow-motion multiplier and 0.8, the leading 1 being replaced on a fast-forwarding server by the fast-forward option divided by `deltaMinutesPerDay` — pointer: jar:GameTime.getMultiplier @0–@143 L984–L1005 — grade C
33. On a dedicated server the frame multiplier is `60 ÷ fps`, with `fps` smoothed toward the instantaneous rate by at most 1 per frame — pointer: jar:GameServer.main @4377–@4424 L1118–L1123 — grade C
34. The game-time multiplier bias is 1.0 after every sandbox load, because the `speed` field it switches on is set to 3 at construction and written nowhere else — pointer: jar:SandboxOptions.updateFromLua @72–@137 L430–L436; jar:SandboxOptions.<init> @4–@6 L59 — grade C
35. `getGameWorldSecondsSinceLastUpdate` equals `getMultiplier × getDeltaMinutesPerDay ÷ multiplierBias`, the same game-seconds while the bias is 1 — pointer: jar:GameTime.getGameWorldSecondsSinceLastUpdate @0–@14 L214–L215; jar:GameTime.getTimeDeltaFromMultiplier @0–@14 L1017 — grade C
36. `Stats.add`, `remove` and `reset` all write through `set`, so each clamps once to the stat's bounds and returns whether the stored value changed, and `add` sums in float — pointer: jar:Stats.add @0–@12 L88; jar:Stats.remove @0–@7 L92; jar:Stats.reset @0–@9 L96 — grade C
37. `Hook.CalculateStats.Add` registers only a Lua closure passed as its first argument, so the colon form passes the table and registers nothing, without error — pointer: jar:Event$Add.call @8–@42 L80–L83 — grade C
38. `Add` does not de-duplicate and `Remove` removes one matching closure per call, so a function added twice runs twice and needs two removes — pointer: jar:Event$Add.call @29–@40 L81; jar:Event$Remove.call @27–@39 L102 — grade C
39. `Add` and `Remove` are no-ops while `LuaCompiler.rewriteEvents` is set, which `LuaManager.RunLuaInternal` sets from its flag for the duration of one file run — pointer: jar:Event$Add.call @0–@7 L76–L77; jar:LuaManager.RunLuaInternal @84–@85 L1366; jar:LuaManager.RunLuaInternal @428–@429 L1409 — grade C
40. `StatsDecrease` maps 1 to 5 onto 2.0, 1.6, 1.0, 0.8 and 0.65, with any other value 1.0 — pointer: jar:SandboxOptions.getStatsDecreaseMultiplier @0–@65 L545–L550 — grade C

## Bibliography of dumps

All run from `C:\Users\Angus\pz-b42` on 2026-10-04 against `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar` (42.20.4):

```bash
./pz.sh dump zombie/characters/IsoGameCharacter calculateStats
./pz.sh dump zombie/characters/IsoGameCharacter updateThirst
./pz.sh dump zombie/characters/IsoGameCharacter updateStats_Awake
./pz.sh dump zombie/characters/IsoGameCharacter updateStats_WakeState
./pz.sh dump zombie/characters/IsoGameCharacter updateStats_Sleeping
./pz.sh dump zombie/characters/IsoGameCharacter updateMorale
./pz.sh dump zombie/characters/IsoGameCharacter updateTripping
./pz.sh dump zombie/characters/IsoGameCharacter updateFitness
./pz.sh dump zombie/characters/IsoGameCharacter updateEndurance
./pz.sh dump zombie/characters/IsoGameCharacter autoDrink
./pz.sh dump zombie/characters/IsoGameCharacter getAppetiteMultiplier
./pz.sh dump zombie/characters/IsoGameCharacter getRunningThirstReduction
./pz.sh dump zombie/characters/IsoGameCharacter getThirstMultiplier
./pz.sh dump zombie/characters/IsoGameCharacter getHungerMultiplier
./pz.sh dump zombie/characters/IsoGameCharacter getFatiqueMultiplier
./pz.sh dump zombie/characters/IsoGameCharacter updateIdleSquareTime
./pz.sh dump zombie/characters/IsoGameCharacter isCurrentlyIdle
./pz.sh dump zombie/characters/IsoGameCharacter isInCombat
./pz.sh dump zombie/characters/IsoGameCharacter isAsleep
./pz.sh dump zombie/characters/IsoGameCharacter isUnlimitedEndurance
./pz.sh dump zombie/characters/IsoGameCharacter getPerkLevel
./pz.sh dump zombie/characters/IsoGameCharacter isRunning
./pz.sh dump zombie/characters/IsoGameCharacter isSprinting
./pz.sh dump zombie/characters/IsoPlayer updateStats_Sleeping
./pz.sh dump zombie/characters/IsoPlayer calculateStats
./pz.sh dump zombie/characters/IsoPlayer updateEndurance
./pz.sh dump zombie/characters/IsoPlayer getAutoDrink
./pz.sh dump zombie/characters/IsoPlayer setAutoDrink
./pz.sh dump zombie/characters/IsoPlayer getTimeOfSleep            # method not found
./pz.sh dump zombie/characters/IsoPlayer allPlayersAsleep
./pz.sh dump zombie/characters/IsoPlayer isGhostMode
./pz.sh dump zombie/characters/IsoPlayer IsRunning
./pz.sh methods zombie/characters/IsoLivingCharacter                # no calculateStats declared
./pz.sh methods zombie/characters/IsoPlayer
./pz.sh methods zombie/GameTime
./pz.sh dump zombie/GameTime getMultiplier
./pz.sh dump zombie/GameTime getDeltaMinutesPerDay
./pz.sh dump zombie/GameTime getMinutesPerDay
./pz.sh dump zombie/GameTime getGameWorldSecondsSinceLastUpdate
./pz.sh dump zombie/GameTime getMultipliedSecondsSinceLastUpdate
./pz.sh dump zombie/GameTime getRealworldSecondsSinceLastUpdate
./pz.sh dump zombie/GameTime getThirtyFPSMultiplier
./pz.sh dump zombie/GameTime getTrueMultiplier
./pz.sh dump zombie/GameTime getUnmoddedMultiplier
./pz.sh dump zombie/GameTime setMultiplier
./pz.sh dump zombie/GameTime getTimeDelta
./pz.sh dump zombie/GameTime getTimeDeltaFromMultiplier
./pz.sh dump zombie/GameTime getMultiplierFromTimeDelta
./pz.sh dump zombie/GameTime getServerMultiplier
./pz.sh dump zombie/GameTime getSlomoMultiplier
./pz.sh dump zombie/GameTime update
./pz.sh dump zombie/GameTime "<init>"
./pz.sh grep fpsMultiplier
./pz.sh grep perObjectMultiplier
./pz.sh grep multiplierBias
./pz.sh dump zombie/FPSTracking frameStep --from 0 --to 150
./pz.sh dump zombie/network/GameServer main --from 4370 --to 4440
./pz.sh dump zombie/SandboxOptions updateFromLua --from 0 --to 145
./pz.sh dump zombie/SandboxOptions "<init>" --from 0 --to 12
./pz.sh dump zombie/SandboxOptions getStatsDecreaseMultiplier
./pz.sh dump zombie/SandboxOptions getEnduranceRegenMultiplier
./pz.sh methods zombie/SandboxOptions
./pz.sh dump zombie/MovingObjectUpdateSchedulerUpdateBucket update --from 0 --to 170
./pz.sh refs zombie/MovingObjectUpdateSchedulerUpdateBucket update
./pz.sh methods zombie/ZomboidGlobals
./pz.sh dump zombie/ZomboidGlobals Load
./pz.sh methods zombie/characters/Stats
./pz.sh dump zombie/characters/Stats add
./pz.sh dump zombie/characters/Stats remove
./pz.sh dump zombie/characters/Stats set
./pz.sh dump zombie/characters/Stats get
./pz.sh dump zombie/characters/Stats reset
./pz.sh dump zombie/characters/Stats isAboveMinimum
./pz.sh dump zombie/characters/Stats isAtMinimum
./pz.sh dump zombie/characters/Stats isTripping
./pz.sh dump zombie/characters/Stats setTripping
./pz.sh dump zombie/characters/Stats addTrippingRotAngle
./pz.sh dump zombie/characters/Stats getTrippingRotAngle
./pz.sh dump zombie/characters/Stats getNicotineStress
./pz.sh dump zombie/characters/CharacterStat clamp
./pz.sh dump zombie/core/math/PZMath clamp --desc "(FFF)"
./pz.sh methods zombie/Lua/LuaHookManager
./pz.sh dump zombie/Lua/LuaHookManager TriggerHook
./pz.sh dump zombie/Lua/LuaHookManager AddEvent
./pz.sh dump zombie/Lua/LuaHookManager AddEvents
./pz.sh dump zombie/Lua/LuaHookManager register
./pz.sh methods zombie/Lua/Event
./pz.sh grep 'zombie/Lua/Event$' --max 20
./pz.sh dump zombie/Lua/Event trigger
./pz.sh dump zombie/Lua/Event register
./pz.sh methods "zombie/Lua/Event\$Add"
./pz.sh dump "zombie/Lua/Event\$Add" call
./pz.sh dump "zombie/Lua/Event\$Remove" call
./pz.sh dump zombie/Lua/LuaManager RunLuaInternal --from 60 --to 95
./pz.sh dump zombie/Lua/LuaManager RunLuaInternal --from 415 --to 435
./pz.sh dump zombie/ai/sadisticAIDirector/SleepingEvent setPlayerFallAsleep --from 40 --to 75
./pz.sh dump zombie/ai/sadisticAIDirector/SleepingEvent doDelayToSleep
./pz.sh refs "zombie/Lua/LuaManager\$Exposer" exposeAll
./pz.sh methods "zombie/Lua/LuaManager\$GlobalObject"
./pz.sh grep getCurrentSpeed --max 20
```

The `tableswitch` case tables of `getStatsDecreaseMultiplier`, `getEnduranceRegenMultiplier` and `updateFromLua @79` (which the dumper does not print) were decoded with a few lines of Python over `dis.code_of`. The access flags and the jar-wide reference scans came from a session-scoped scanner rebuilt from `pz-b42/tools/cp.py` and `dis.py` (not kept): an `acc` mode printing each named member's access flags up the superclass chain, and a `callers` mode that opens every class whose bytes hold the member name and lists each method instruction referencing it. The reference scans quoted above were run on `GameTime.fpsMultiplier`, `multiplierBias`, `perObjectMultiplier`, `SandboxOptions.speed`, `LuaCompiler.rewriteEvents`, `ZomboidGlobals.thirstLevelToAutoDrink`, `thirstLevelReductionOnAutoDrink`, `IsoGameCharacter.autoDrink`, `Stats.lastEndurance`, `getLastEndurance`, `setLastEndurance`, `timeOfSleep`, `delayToActuallySleep`, `setTimeOfSleep`, `setDelayToSleep`, `idleSquareTime` and `getIdleSquareTime`. Install text searches: `media/lua/shared/defines.lua` for the constants, and `media/lua` for `LastEndurance`, `setTimeOfSleep` and `setDelayToSleep` (no hits).

