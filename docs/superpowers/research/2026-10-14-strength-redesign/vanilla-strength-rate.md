# Vanilla Strength gain rate — B42.21, dedicated MP, unmodded

Researcher: claude-opus-5-5, 2026-10-14. Read-only. Sources: install Lua (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`, 42.21), the 42.21 jar through `C:\Users\Angus\pz-b42\pz.sh`, this repo's register (tags `#NNNN`, most read on 42.20.4), and community posts (marked **[community]**).
Jar cites are `Class.method @bytecode-offset Lline` as `pz.sh dump` printed them on the installed (42.21) jar.

**Bottom line.** Every vanilla Strength source is paced by the wall clock (real time), not the game clock: the exercise rep loop, endurance regen, the carry roll and combat are all real-time. So XP per *in-game day* scales with DayLength, and XP per *real hour of play* does not. A trainer who cycles push-ups and sitting rest as efficiently as possible earns about **1.8–1.95 Strength XP per real second (about 6,500–7,000 an hour)**. Strength 5→10 (450,000 XP) then takes **about 69 real hours of active training**. That is about 69 game days at the 90-minute default day if the trainer cycles all 16 waking hours. A trainer on a habit of a few exhaustion bouts a day takes about 330 game days. A survivor who never trains takes 225 to 900+ game days. Rust is negligible: −10 XP every ~21.5 game days of no Strength gain, and only while the player is online.

---

## 1. The XP ladder

Strength and Fitness share one ladder. The declared thresholds are ×1.5 in `AddPerk` [#2102/C/arith.]; the table is on `docs/facts/perks-and-strength.md` lines 34–45.

| Level | Cost of level | Cumulative | Δ from L5 (37,500) |
|---|---|---|---|
| 5 | 18,000 | 37,500 | 0 |
| 6 | 30,000 | 67,500 | 30,000 |
| 7 | 60,000 | 127,500 | 90,000 |
| 8 | 90,000 | 217,500 | 180,000 |
| 9 | 120,000 | 337,500 | 300,000 |
| 10 | 150,000 | 487,500 | 450,000 |

- Level 10 cap: `AddXP` drops any non-negative amount once XP ≥ `getTotalXpForLevel(10)` (jar `IsoGameCharacter$XP.AddXP(Perk,F,Z,Z,Z,Z) @198–@221 L14252–L14254`, re-read 42.21) [#2109].
- New characters are seeded at level 5 with 37,500 XP [#2104, #2874/M].

## 2. The multiplier chain a Strength grant passes (42.21 jar)

On a dedicated server every Strength grant reaches the six-argument `AddXP` with the multiplier flag set:

- `GameServer.addXp(p,perk,F)` → `addXp(p,perk,F,false,false)` (`@0–@5 L1903`);
- that calls `AddXP(perk, amt, false, !noMult=true, true, halo)` (`GameServer.addXp(...FZZ) @33–@52 L1919`) [#2132].
- The Lua global `addXp` routes to `GameServer.addXp` on a server (`LuaManager$GlobalObject.addXp @8–@17 L9807–L9808`) [#2130].

In order:

1. **Protein**: ×1.5 when 50 < protein store < 300; ×0.7 below −300 (`@107–@190`) [#2112]. Vanilla protein drains 0.00086 g per game second, about 74 g per game day [#0069/M], so ~75 g of protein a day keeps a survivor in the ×1.5 window.
2. **Boost-map and trait multipliers do not touch Strength**:
   - the 0.25 "no boost" reduction skips Strength (`isSkillExcludedFromSpeedReduction @18–@30 L14387`);
   - the 1.33 and 1.66 boosts, Fast Learner ×1.3 and Slow Learner ×0.7 all test `isSkillExcludedFromSpeedIncrease` / `…Reduction`, which answer true for Strength (`isSkillExcludedFromSpeedIncrease @9–@21 L14394`; `AddXP @222–@579 L14257–L14285`) [#2110].
3. **Per-perk book multiplier** `getMultiplier(perk)`, applied only when > 1 (`@738–@756 L14300–L14302`) [#2113]. No vanilla Strength book exists to my knowledge (not verified jar-wide).
4. **Sandbox XP multiplier** (`@757–@823 L14305–L14308`):
   - when `MultiplierConfig.GlobalToggle` is true (the preset default: `media/lua/shared/Sandbox/Apocalypse.lua:242–246`, `Global = 1.0, GlobalToggle = true, Strength = 1.0`), the amount is × `Global`;
   - otherwise it is × the per-perk `MultiplierConfig.Strength`.
   - It is linear, so **days scale by 1/multiplier** (×2 halves every day count below). It also multiplies the rust step's −1.
5. Clamp to [0, 487,500] (`@824–@861 L14312–L14319`).

Anti-cheat: `AntiCheatXP` flags growth > 1000 × multiplier × boost per check, i.e. > 250 at default for Strength [#2147, #2863]. The check interval is still open [#2085]. A push-up stream (~2 XP/s) trips it only if the interval exceeds ~2 real minutes (inference).

## 3. Every vanilla Strength XP source

### 3a. Fitness exercise (the trainer's source)

Per rep, `Fitness.incStats` gives Strength XP of 4 per `arms` and 2 per `chest` in the exercise's stiffness list.

- Level scaling `1 + (lvl−5)/10` uses integer division, so it is ×1.0 at every level 0–10 [#2171, #2172].
- The result is × `xpMod`, then truncated to an int on the server (`Fitness.incStats @153–@201`: `xpModifier`, `f2i`, `GameServer.addXp`, 42.21) [#2173].
- Regularity does **not** enter the XP: no term in `incStats` [#2171]. The community agrees ("Regularity has nothing to do with how fast you gain Strength", **[community]** steamcommunity 3415432674401458011).

Exercise rows are in `media/lua/shared/Definitions/FitnessExercises.lua:4–65`. Rep periods are in `media/lua/shared/TimedActions/ISFitnessAction.lua:134–148`.

| Exercise | Stiffness | xpMod | Str XP/rep (server, before protein) | Rep period | Endurance/rep | Str XP per endurance |
|---|---|---|---|---|---|---|
| push-ups | arms,chest | 1 | **6** | 1300 ms | 0.015 | **400** |
| dumbbell press | arms | 1.8 | 7 (7.2 trunc.) | 1500 ms | 0.0195 (heavy ×1.3) | 359 |
| biceps curl | arms | 1.8 | 7 | 1900 ms | 0.0195 | 359 |
| barbell curl | arms,chest | 1.2 | 7 (7.2) | 2200 ms | 0.0195 | 359 |
| burpees | legs,arms,chest | 0.8 | 4 (4.8) | 2400 ms | 0.0195 | 205 |
| squats, sit-ups | legs / abs | 1 | 0 | 3000 / 1300 | 0.015 | 0 |

Measured: a push-up rep fires the Strength `AddXP` event at 4.2 = 6 × 0.7 (low-protein branch), and squats at Strength 0 [#2900/M/n=1, #2879/M/n=1].

**Pacing is real time.**
- `ISFitnessAction:serverStart` arms `emulateAnimEvent(netAction, period, …)` (`ISFitnessAction.lua:128–150`).
- `AnimEventEmulator.update` fires when `GameTime.getServerTimeMills() ≥ time + duration` and then re-stamps `time = now` (`AnimEventEmulator.update @0–@105 L57–L64`).
- `getServerTime` is `System.nanoTime()` on a server (`GameTime.getServerTime @14–@23 L163–L164`).
- So a rep comes every `period` real ms, rounded up to the next server frame. The server runs ~10 frames/s: 6.26 frames per game minute at DayLength 15 min [#3512/M]. I use 1.35 s for push-ups.

**Gates on exercise.**
- **Endurance (the binding gate).**
  - A set cannot start, and is force-stopped, when the ENDURANCE moodle level > 2 (`ISFitnessUI.lua:3, 237`; `ISFitnessAction.lua:5–7, 39–43`). That is endurance < 0.25 [#0510].
  - Rep cost = 0.015 × ln(reg/50+50)/ln(51) (≈1) × 1.3 if heavy × heavy-load factor [#2174].
- **Pain moodle > 3** blocks start (`ISFitnessUI.lua:256`).
  - Exercise stiffness does **not** feed pain on 42.21. `BodyPart.getPain` reads scratch, cut, bite, deep wound, stitch, fracture, burn, glass, bullet, infection, splint and additionalPain, and no stiffness (`pz.sh refs BodyPart getPain`).
  - The only `BodyDamage` reader of stiffness is `save`, and the shipped health panel labels stiffness "(Debug - HAS NO EFFECT ON THE PLAYER!)" (`client/XpSystem/ISUI/ISHealthPanel.lua:716`).
  - Stiffness is capped at 100 (`BodyPart.addStiffness @0–@14 L1751`). It decays 0.002 × multiplier per update (≈0.096 per real s) once no group is pending (`BodyPart.DamageUpdate @2356–@2431 L507–L512`).
  - So in vanilla 42.21 stiffness is cosmetic for the XP rate. Confidence medium: a grep-based negative.
- **Heavy-load moodle > 2** blocks start (`ISFitnessUI.lua:241`). **Regularity** only lowers soreness [#2176]. **Level-10 cap** [#2109].

### 3b. Melee combat (normal survivor)

- `xpUpdate.onWeaponHitXp`: + `owner:getLastHitCount()` Strength per non-ranged swing that hits (number of targets) (`server/XpSystem/XpUpdate.lua:76–78`) [#2195]. It fires on the server only [#2193, #2880/M].
- `IsoGameCharacter.hitConsequences`: **+2.0** Strength to the attacker when the victim survives a non-ranged hit from a weapon with `KnockBackOnNoDeath = true` (`@103–@158 L6317–L6324`, 42.21) [#2191].
  - 145 of 362 weapon items set it true (`media/scripts/generated/items/weapon.txt`). True: baseball bat, crowbar, axe, shovel, sledgehammer, hammer, katana. False: machete, kitchen knife, crafted spear, lead pipe, plank.
- A kill with a knockback weapon in ~3 hits ≈ 2×(1+2) + 1 = **~7 XP**. A non-knockback weapon gives ≈ 1 per hit (~2–3 per kill).

### 3c. Carrying load while moving

`xpUpdate.onPlayerMove`: inventory weight > 50 % of max weight → `isRandXp(1000, 0.05, Strength)` → +2 (`XpUpdate.lua:32–37`).

- On 42.21, `IsoPlayer.isRandXp` allows one roll per 1000 ms of `System.currentTimeMillis()` per perk. It succeeds when `ZombRand(1/0.05 = 20) == 0` (`IsoPlayer.isRandXp @0–@81 L9626–L9633`).
- That is **0.1 XP per real second of loaded movement = 360 XP per real hour**, independent of DayLength.
- **The register is stale here**: #2115/#2116 describe the 42.20.4 `randXp()` (1 in 100×InvMultiplier). That code is gone in 42.21's `XpUpdate.lua`.
- `OnPlayerMove` fires on the dedicated server for a remote player [#2245].

### 3d. Minor

- Hitting a tree with any non-bare-hands weapon: +2 per hit (`XpUpdate.lua:43–46`) [#2202].
- Removing a plank barricade: +2 (`shared/TimedActions/ISUnbarricadeAction.lua:144`) [#2203].
- Dismantling a `Stone` moveable: 5/10/15, only below `LevelForDismantleXPCutoff` (`shared/Moveables/ISMoveableDefinitions.lua:530`) [#2204].
- No other Strength grant (Java or Lua) was found: `grep Perks.Strength` over the install Lua, plus [#2191, #2190] on the Java side.

## 4. Rates (default multiplier 1, protein neutral ×1.0)

### Trainer arithmetic (push-ups, Fitness 5, fatigue ≈ 0.2)

- **Server multiplier**: the per-update game multiplier sums to 48 per real second [#3606] (4.78–4.80 per update measured [#0529/M]).
- **Standing regen** = 3.1e-5 × 48 × recoveryMod 1.2 × (1−0.85F) = **1.48e-3/s** [#2258, #2262].
  - Validated live: resting regen ran 0.067 per game hour at DayLength 15 min, which is 1.79e-3 per real s at F≈0 [#2753/M/n=1]. The model gives 1.79e-3 at F=0.
- **Sitting regen** = 5× standing with (1−0.8F) = **7.50e-3/s** [#2260].
  - Endurance regen has no day-length term [#2257]. It is real-time.
- **Exercising drain** = 0.015/1.35 s − standing regen = 9.63e-3/s.
  - If standing regen does not run in FitnessState (not read), it is 1.11e-2/s.
- **One exhaustion bout** (1.0 → 0.25): 78 s, ~58 reps, **~346 XP**. Then 100 s sitting refills it.
- **Steady cycle** (exercise ↔ sit), fraction exercising f = 7.50/(9.63+7.50) = 0.438. XP rate = 6/1.35 × 0.438 = **1.95 XP/real s**, or 1.79 without standing regen.
  - I use **1.8 XP/s** effective (≈5 % lost to sit/stand/start transitions): **6,480 XP per real hour of cycling**.
  - It rises with Fitness: recoveryMod 1.6 at Fitness 10 [#2262].

**Best-case trainer** cycles through all 16 waking game hours, i.e. 16/24 of a day's real minutes.

| DayLength | Best-case trainer (XP/game day) | Typical trainer: 4 exhaustion bouts/day | Normal survivor, typical | Normal survivor, heavy-combat best |
|---|---|---|---|---|
| 15 min (index 1; this repo's test servers) | 1,080 | ~1,080 (capped by real time) | 83 | 333 |
| 60 min (index 3, "1 h") | 4,320 | 1,368 | 333 | 1,333 |
| **90 min (index 4, the jar default)** | **6,480** | **1,368** | **500** | **2,000** |
| 120 min (index 5, "2 h") | 8,640 | 1,368 | 667 | 2,667 |

How each column is built:
- **Typical trainer**: 4 × 342 XP. The player follows a game-time habit (a few bouts a day), so the column is DayLength-independent until real time caps it. The community's untuned routines land here or lower:
  - "around 6000 points in 10 days with permanent training" (≈600/day, **[community]** https://steamcommunity.com/app/108600/discussions/0/4477100383806074711);
  - "a full month… with x10 XP mods" for 0→10 (**[community]**, search summary).
- **Survivor typical** at 90 min: ~50 kills × ~7 with a knockback weapon (350) + 20 real min loaded movement (120) + a few tree hits ≈ 500. **Survivor heavy-combat best**: 200 kills × 7 (1,400) + 1 real h loaded (360) + 120 tree hits (240) ≈ 2,000. Both scale with DayLength/90 because kills and loaded walking happen per real minute. These two columns are assumptions about play, not engine numbers.

Protein ×1.5 divides every day count by 1.5. Sandbox `Global` multiplier m divides every day count by m.

## 5. Game days from Strength 5 (at the 37,500 threshold) to each level

### DayLength 90 min (default), multiplier 1, protein neutral

| Target | Δ XP | Best-case trainer | Typical trainer | Survivor typical | Survivor heavy-combat |
|---|---|---|---|---|---|
| 6 | 30,000 | 4.6 | 21.9 | 60 | 15 |
| 7 | 90,000 | 13.9 | 65.8 | 180 | 45 |
| 8 | 180,000 | 27.8 | 131.6 | 360 | 90 |
| 9 | 300,000 | 46.3 | 219.3 | 600 | 150 |
| 10 | 450,000 | 69.4 | 328.9 | 900 | 225 |

At DayLength 60 min: best-case 6.9 / 20.8 / 41.7 / 69.4 / 104.2 days. Typical trainer is unchanged. Survivor typical is 90 / 270 / 540 / 900 / 1350.
At DayLength 120 min: best-case 3.5 / 10.4 / 20.8 / 34.7 / 52.1 days. Survivor typical is 45 / 135 / 270 / 450 / 675.

## 6. Real hours

**Active training time is DayLength-independent**: Δ XP / 6,480 per hour gives **4.6, 13.9, 27.8, 46.3 and 69.4 real hours** to reach 6–10.

Calendar real time = game days × DayLength:

| Target | Best-case, any DL (= active hours) | Typical trainer @60 min | @90 min | @120 min | Survivor typical, any DL | Survivor heavy, any DL |
|---|---|---|---|---|---|---|
| 6 | 6.9 h | 21.9 h | 32.9 h | 43.9 h | 90 h | 22.5 h |
| 7 | 20.8 h | 65.8 h | 98.7 h | 131.6 h | 270 h | 67.5 h |
| 8 | 41.7 h | 131.6 h | 197.4 h | 263.2 h | 540 h | 135 h |
| 9 | 69.4 h | 219.3 h | 328.9 h | 438.6 h | 900 h | 225 h |
| 10 | 104.2 h | 328.9 h | 493.4 h | 657.9 h | 1350 h | 337.5 h |

Notes on the table:
- The best-case calendar figure is 1.5× the active hours, because the trainer cycles only 16 of 24 game hours.
- The survivor columns are DayLength-independent in real hours because the activity is real-time.
- The typical trainer, whose habit is game-time, takes longer in real hours on a longer day.

**DayLength default.** The jar default is index 4 = **90 min**: `SandboxOptions.<init> @110–@120 L70`, `newEnumOption("DayLength", 27, 4)`; mapping 1→15, 2→30, 3→60, 4→90, n≥5→(n−3)×60 at `SandboxOptions.getDayLengthMinutes @0–@66 L555–L561`, on the 42.21 jar. The presets agree (`media/lua/shared/Sandbox/Apocalypse.lua:8 DayLength = 4`).

**Register caveat**: #0529 and #3344 call the 60-minute day "the default". On this jar that is wrong; the default is 90 min.

## 7. Decay (rust)

All in the server file `media/lua/server/XpSystem/XpUpdate.lua:293–328`, on `EveryTenMinutes`, for `getOnlinePlayers()` on a server. **An offline player never rusts.**

- **Timer.** `strengthUpTimer += getLoosingXpTick() = 10` per ten game minutes (1,440 per game day) (`LuaManager$GlobalObject.getLoosingXpTick @0–@50 L9779–L9785`, 42.21; the debug `fastLooseXp` cheat is off on a release server).
- **Loss.** While the timer > 20,000, each new 1,200-unit bucket costs `getLoosingXpValue() = −1` XP (`@27 L9774`), only while XP > 0, then `checkForLosingLevel` (lines 301–309).
- **Reset.** Above 31,000 the timer resets to 0 (lines 310–312).
- **Training holds it off.** Each positive Strength grant subtracts 3,000, floored at −50,000 (lines 175–180) [#2156]. About one grant every two game days keeps the timer from ever reaching 20,000.
- **Rate.** The first loss comes 48.6 game days after the −50,000 default with no Strength gain, or 13.9 days from 0 [#2155]. After that: buckets 16–25 give **10 XP lost over ~7.6 days**, then the reset and 13.9 quiet days. That is a cycle of ~21.5 game days and **−10 XP (≈ −0.47 XP/day)**.
- **Multipliers apply to the loss too.** The −1 passes the multiplier chain: × Global m, and × 1.5 in the protein window, since the branch is unsigned [#2112].
- **Level loss** happens only when XP falls below the current level's cumulative total (`XpUpdate.lua:283–291`) [#2124]. Since a level-up lands just above the threshold, a player who levels then idles could drop back after ≥ 48.6 days, but only within the first ~10 XP of the level.
- **In effect, Strength does not decay in vanilla.** No Java decay exists [#2151].

## 8. Confidence

| Item | Confidence | Why |
|---|---|---|
| Ladder, cap, multiplier chain, sources and their amounts | High | Jar and Lua read on 42.21; push-up 6 and squat 0 measured [#2900, #2879] |
| Real-time pacing of reps, endurance and carry roll | High | `nanoTime`/`currentTimeMillis` read; standing regen matches #2753 within 1 % |
| Best-case trainer rate 1.8–1.95 XP/s | Medium | Sitting regen and the FitnessState standing arm are read, not measured; fatigue is assumed 0.2; transitions are estimated |
| Stiffness has no gating effect | Medium | Negative from refs and grep plus the health-panel label; no live test |
| Typical trainer / survivor days | Low | Behavioural assumptions; community B41/B42 posts (≈600/day) bracket the typical trainer from below |
| Rust rate | High | Code read; arithmetic on the timer |

Not done: no live measurement of a full exercise-rest cycle on 42.21. A 10-minute harness run with push-ups to exhaustion, sitting refill and repeat, logging Strength XP against wall time, would settle the 1.8–1.95 XP/s figure.
