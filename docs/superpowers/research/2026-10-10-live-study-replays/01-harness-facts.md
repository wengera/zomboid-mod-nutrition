# Live study replays — 01: the harness facts a live plan stands on

Research report, 2026-10-10, read-only (no boot, no commit). Author model: claude-opus-5-5.
Question: can the satiety oracles' study replays (`testing/tests/kernel/test_satiety_meal_studies.py`,
`test_satiety_activity.py`, `test_writer_shape.py`'s nicotine arm, `test_kernel_monotony.py`) be replayed on a live
dedicated server, and what does each replay need. Every engine or harness mechanism below carries a register row
(`#NNNN`) or a `file:line`; where neither exists the sentence says **unmeasured** or **inference**.

Build caveat (CLAUDE.md § 2): almost every cadence and live-behaviour row cited here was read on 42.20.4; the build is
42.21 since 2026-10-08. A live plan re-reads the cadence rows (#3346, #1816, #3349) in its first session (the S0 gate
below) before relying on them.

---

## 1. How fast can game time run live

### What is measured

| Setting | Measured | Row |
|---|---|---|
| DayLength 1, speed 1 (the mod profiles' setting, e.g. `testing/profiles/x25-rebaseline.toml` `DayLength = 1`) | 63 consecutive game minutes at a mean 6.270 `OnTick` calls each (46 of 6, 17 of 7, none of 0), 10.115 ticks/s, **1.600 game-min per wall s** (a game minute 0.625 s) | #3346/M/n=1 |
| DayLength 4 (fixture value), `settimespeed 30` | 7.99, 7.99, 8.00 world-min per wall s, the minute event at exactly one tick per game minute | #1814/M/n=3, #1776, #0156 |
| DayLength 1, `settimespeed 5` (same arithmetic value 8) | **7.57 world-min/s, 1.018 harness-scheduler ticks per game minute, no suspect flag** | #1816/M/n=1 |
| DayLength 1, `settimespeed 30` | overran: 0.22 scheduler ticks per game minute, the minute event 20 times while the world advanced 91.05 min | #1813/M/n=1 |
| DayLength 1, `settimespeed 30` (x222) | 213 `EveryOneMinute` calls in 214 ticks, 47.66 world-min/s, **about 4.7 game minutes per tick reaching Lua as ONE call** | #3349/M/n=1 |
| the event's own ceiling | 10.08 ticks per wall s on the run that overran; where the ceiling sits between 8 and 10.08 is open | #1815/M/n=1/open |
| `time.multiplier 0.1674` at DayLength 1 | 37 or 38 ticks between minute events (the DayLength-4 spacing); `SandboxOptions:set DayLength 4` live did NOT change the clock | #3394/M/n=1 |
| sleep fast-forward (only player held asleep, sleep allowed and needed) | 61.764 game h in 115.998 s (about 32 game-min/s, about 20x the waking rate) | #2956/M/n=1 |

The rule of thumb is `24 × speed / day_minutes ≤ 8` game-minutes per wall second (harness.md:20, #1814; rule on
areas/testing-your-mod.md `## Rules`).

### What the mod does when the clock outruns the ticks

- The mod's per-player work is driven by `EveryOneMinute` (it snapshots the roster and merges the queue) and drained
  on `OnTick` under a budget (`mod/NutritionRevamp/common/media/lua/server/NR_Server_Players.lua:200-210`, `P.minute`
  :78, `P.drain` :172). One `EveryOneMinute` call per tick when the clock is fast (#3349) means **the event skips game
  minutes**: one call can stand for 4.7 game minutes.
- Every step integrates elapsed world age, not a count of events: Metabolism `dtM = clamp((ageH - lastAgeH) × 60, 0,
  60)` (`NR_Server_Metabolism.lua:375`), Nutrients the same (`NR_Server_Nutrients.lua:367`), Kinetics drains a gap in
  one-minute substeps capped at 60 (`NR_Server_Kinetics.lua:53-60`), the writer "stepping by elapsed world age"
  (`NR_Server_Writer.lua:6-7`, #3371). So minutes are not *lost* to the integrals under a fast clock, but the per-minute
  writes (HUNGER once per run) and the per-eat timing coarsen, and a multi-minute step is not the oracle's one-minute
  step (the oracles step one game minute: `test_satiety_meal_studies.py:1-6`).
- The queue's budget divides by measured ticks per minute (`NR_Kernel_Sched.lua:39-49`, `TPM_DEFAULT = 6` from #3346);
  under a fast clock "every queued name runs each tick" (`NR_Kernel_Sched.lua:52-53`). The 1.0.0 build served only one
  of two players per minute event at `settimespeed 30` (#3352/M/n=1); the 11a queue that replaced it has **never been
  measured under a fast clock** (Plan 11b's x251c fast-clock arm, plan :239, is unrun because Plan 11b is pending).
- The writer's per-minute write held (every per-write delta 0 on two awake players over 309 writes at speed 30, #3371) —
  that is the zeroed vanilla rates, not the integral.

### Conclusion: the safe setting and the game hours per session

- **Safe and measured:** DayLength 1 at speed 1, 1.6 game-min/s, about 6.27 ticks per game minute (#3346). This is the
  only setting where every game minute is its own event with ticks to spare.
- **Safe by the cadence rule, unmeasured for the current mod:** DayLength 1 at `settimespeed 5`, about 7.6 game-min/s
  and one scheduler tick per game minute (#1816). It is the highest setting at which the minute event still fires once
  per game minute; the 11a queue is expected to run both players each minute there (one or two ticks per minute,
  `runCap = floor(15 / 1.6) = 9` from `NR_Kernel_Sched.lua:11,13,58-63`) — inference until the S0 gate measures it.
- **Unsafe:** anything above about 8 game-min/s (#1813, #3349: the minute event carries several game minutes).
- Session arithmetic, a ≤ 15-minute driver: server start 14.9–16.1 s (#3286/M/n=1), a client ready about 35–41 s after
  launch (#3298/M/n=1, #3302), a clean teardown with a departure flush wait about 1 min (§ 2), setup and gates about
  1 min → **about 11–12 min of running clock**. At speed 1 that is **≈ 16–19 game hours**; at `settimespeed 5`
  **≈ 75–85 game hours** (planning figure **72 game hours per session**, leaving margin for slowed eat windows).
- The bus is not free at speed: the server polls the command file every 20 ticks and on every `EveryOneMinute`
  (`testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua:1369-1374`), so at speed 5 a round trip spans
  several game minutes. Per-minute readings at speed need a server-side sampler (harness addition H2, § 3.7).
- An eat takes about 5.5–6.8 wall seconds from queue to landing at speed 1 (#0121/M/n=2, #2834/M/n=2); whether the
  action's `maxTime` scales with `settimespeed` is **open** (#0141/open). At 7.6 game-min/s an unscaled eat would span
  about 45 game minutes; at DayLength 1 speed 1 it is about 10 game minutes. Short-window readings (Rolls 1999 at
  minute 17, Rolls 1998 at 30, Goetze at minute 1) therefore slow the clock around the eat with `time.multiplier
  0.1674` (37 ticks a minute, #3394), and the replay's minute 0 is the measured landing, not the queue.

---

## 2. Persistence across sessions

**Yes, by driver, not by `pzt run`.**

- `pzt run` always restores the fixture into a fresh run dir (`testing/pzt/fixture.py:71-74`, `restore_server`
  copies `fixtures/<name>/cache/server`); a profile never mutates the fixture (#1792). A second `pzt run` therefore
  starts from the fixture's world and an empty mod store.
- A driver can boot a server again on a run dir that already holds a server cache: `make_server(run_dir, rec,
  reuse=True)` (`testing/pzt/session.py:128-139`; it refuses a dir with no `server/Server`). x192 booted three servers
  on one run dir and a control on a fresh restore (`testing/experiments/x192_persist_mod.py:24-90`; #3274, #3276,
  #3286). A client cache is always a fresh fixture restore in its own folder: `restore_client` refuses an existing
  folder (`testing/pzt/fixture.py:77-87`; x192's `c1b`, `x192_persist_mod.py:281-283`); the character persists
  server-side, so a restored client skips creation (#1715).
- Recommended chain shape (a planning choice, not a measured route): session N+1's driver **copies** session N's
  `<run>/server` into its own run dir and boots it with `reuse=True`, so each session has its own run folder and a
  failed session never damages the previous saved state. Run folders are per-machine and gitignored (CLAUDE.md § 5),
  so the chain lives on this host only.
- **The world** is written only on a console save and a clean quit with the fixture's `SaveWorldEveryMinutes` 0
  (#2097/M, #2756/M); a hard kill rolls the world back to the last save. `PauseEmpty=false` is written into a fresh
  ini (`testing/pzt/server.py:48-49`), so the world clock runs while no player is online.
- **The mod's record** no longer lives in modData: an in-memory table persisted per player to two alternating JSON
  slot files under the server's Lua cache folder, `NutritionRevamp/<server name>/` (#3647/C,
  `NR_Server_Store.lua:1-9, 160-176`), inputs only (#3644/C), loaded in place at every first sight (#3274, #3276 on the
  older build). A player's slot is written at most once a real minute (`S.SAVE_GAP_MS = 60000`, `NR_Server_Store.lua:82`),
  promptly after an eat, a drink or a reset (the stop window, `NR_Server_Store.lua:59-68`), and a departure queues a
  flush task (`NR_Server_Store.lua:41-46`). There is no save or stop event on a dedicated server (11b amendment 4,
  plan :24), so a clean stop can lose up to one real minute of record drift — **96 game minutes at DayLength 1 speed 1,
  ~7.6 game hours at speed 5**.
- So a chain's end-of-session sequence must be: restore speed 1 → `quit` the client → poll until the departure flush
  ran (`lua.global NutritionRevamp.server.players.online.admin` nil and `...store.file.lastWrite.admin` ≥ the quit's
  server wall ms — the Plan 11b Task 4 G pattern, plan :308) → clean server quit (world save). The record's
  `satiety.t` carries the writer's step age across a restart (`NR_Kernel_Store.lua` INPUTS comment at :34, ruling C-1),
  and an offline gap is clamped at 60 game minutes (`NR_Server_Metabolism.lua:375`); the world clock does not move while
  the server is down, so a clean chain has no gap but the few seconds between the client's quit and the server's quit.
- Measured for the current store: nothing live yet. The file store's restart is Plan 11b Task 4 F/G (pending); the
  in-place load was measured on the global-modData build (#3274, #3276, #3277). A chain's first restart is therefore
  also the store's first live restart and should be graded as such.

---

## 3. The driver's verbs

### 3.1 Eating

| Route | Side | Goes through the mod's eat wrapper (intake landing, P feed, monotony) | Evidence |
|---|---|---|---|
| `eat.action <fullType> [<fraction>]` (client) | queues the real `ISEatFoodAction`, the server completes it | **yes** — the wrapper of `ISEatFoodAction.complete` / `serverStop` is server-side (`NR_Server_Intake.lua:1-4`); landing order IN.land → stomach → P feed (`:31-52`), then `IN.atEat` monotony (`:455`, `:876-905`) | harness-commands.md row `eat.action`; #2830, #2831 |
| `eat <fullType> [<fraction>]` (client) | calls `IsoGameCharacter.Eat` on the client | **no** — "in MP this is not the path a real eat takes" (`PZTestKit_Client.lua:455-458`); the server owns nutrition (#1826) | |
| `nutrition.set <user> calories <v>` (server) | writes the vanilla store | only through the reconcile path: a calorie rise lands a minute late as macros only, no nutrient vector, no water or fibre mass, no monotony (#3306/C, #3293/M; writer limitation text `NR_Server_Writer.lua:22`) | |
| `item.use` (server) | consumes uses like a craft input | no eat; not an intake route (harness.md:261) | #1738 |

Constraints on `eat.action`:
- The item must exist server-side: spawn with `inventory.add <user> <fullType> <count>` (server) or RCON `additem`;
  a client-only item raises server-side in `ISEatFoodAction.new` and blocks the queue (#2917/M).
- FOOD_EATEN at level 3 or more refuses the eat (#0077, #2889/M); prime `foodtimer.set <user> 0` before an eat.
- A started eat cannot be cancelled from the bus (#2834/M).
- A fraction is `Eat`'s share **of what is left**, not of the whole item (#2831/M); use a fresh item per partial eat.
  A finishing eat (fraction 1 of a partly eaten item) read a NaN share on the 42.20.4 build (#2832/M); whether the
  current wrapper is NaN-safe was not re-read here — a driver eats whole fresh items or first fractions only.
- Landing time: poll `NutritionRevamp.server.intake.stats.eats` (`NR_Server_Intake.lua:62-66`) and stamp the world age
  when it rises.

Foods: the oracles use synthetic vectors (`mixed`, `snack`, `preload`, `dense`, `milk`, CASSEROLE/SOUP:
`test_satiety_meal_studies.py:102-150`). A live replay that should inherit the oracle's study comparison needs foods
whose landed vector equals those vectors. The declared-vector route does that: a module-TKX food with
`Calories/Carbohydrates/Proteins/Lipids` and `NR_Nutrients = fibre:..;water:..` (the item-pass contract;
`testing/experiments/TKX_DeclaredFood/42.20/media/scripts/tkx_declared_food.txt`; landing #3148/M), with
`BoredomChange`/`UnhappyChange` 0 so vanilla's own mood adds (#3655) do not mix into a monotony reading. That is a
new experiment mod (`TKX_StudyFoods`), installed only through a profile (CLAUDE.md § 5).

Drinks: `drink.action` queues the real `ISDrinkFluidAction` and lands sips through the drink wrapper into the liquid
lane (`NR_Server_Intake.lua:603-616`; #2944, #2966). The drink's vector is the mod's per-fluid table times the litres;
a fluid the table does not know is `missing` and contributes nothing (`IN.fluidVector`, `NR_Server_Intake.lua:662-679`).
So a liquid preload of arbitrary composition (Callahan's `preload(k)`, Rolls 1998's `milk(ml)`) **cannot be made live**:
only vanilla fluids the table carries (Water, Milk, juices, ...) land. The server `drink` command calls `DrinkFluid`
directly and is not seen by the wrapper (writer limitation, `NR_Server_Writer.lua:22`; #3612/C). Auto-drink lands
through the writer's sip fold (#2965/M, `NR_Server_Writer.lua:6-7`).

### 3.2 Spawning, vanilla stats

- Spawn: `inventory.add <user> <fullType> <count>` (server; `PZTestKit_Server.lua:1781`), fluids `fluid.fill <user>
  <fullType> <fluidType> <litres>` (both sides; use the server side).
- Read in one tick: `stats.all <user>` (server) reads all 24 CharacterStats including HUNGER, THIRST, FATIGUE, ENDURANCE,
  BOREDOM, UNHAPPINESS, NICOTINE_WITHDRAWAL with worldAge and wall (`PZTestKit_Server.lua:1390`, list at
  `PZTestKit_Core.lua:978-985`); its client twin reads the 1 Hz mirror. `stats.get` adds moodles, asleep, foodTimer.
- Write: `stats.setany <user> <StatName> <value>` (server, any CharacterStat by enum name; `PZTestKit_Server.lua:1992`);
  `stats.set` reaches only hunger/thirst/fatigue/endurance. In Mode 1 the writer overwrites HUNGER, THIRST and FATIGUE
  at its next minute (`NR_Server_Writer.lua:3-7`), so a HUNGER write is a seed, not a hold (the seed rule: #3646/C).
- NICOTINE_WITHDRAWAL rises on the server alone (#3631/C); the Smoker trait is added with `trait.set <user> SMOKER add`
  and pushed with `trait.push` (server). **Corrected at Plan 11f Task 10:** the key is `SMOKER`, not `Smoker`: the
  harness resolves the name as a `CharacterTrait` static field (`PZTestKit_Server.lua:287-291`) and the jar registers
  the display name `Smoker` into the field `SMOKER` (`CharacterTrait.<clinit> @661-@667 L85`); `Smoker` read
  `enumFound` false in x311 and the admin smoked as a non-smoker (F-T8-1, ruling T8-1); x321 used `SMOKER`. A smoke is an eat of one of the six smokable foods whose `OnEat` is
  `consumeNicotine` (#3633/C), e.g. `Base.CigaretteSingle`; whether `eat.action` completes a smoke without a lighter in
  hand is **unmeasured** — add `Base.Lighter` first and gate on the server's withdrawal falling. **Measured since
  (Plan 11f Task 8):** with a lighter the smoke completes through `eat.action` and drops the stat by min(w, 0.51)
  (x321, x323); a non-smoker's smoke raises FoodSickness instead (x311, #3632).

### 3.3 Sleep

- Profile keys `[server] SleepAllowed = true, SleepNeeded = true` (harness.md:68; #2947/M, #2948/M: with either false
  the fatigue reset erases each write; with sleep disabled the record's sleep state is frozen, #2961/M, so the sleep
  factor is inert — 11d amendment "Live reads" 1).
- `player.sleep.hold <user> <seconds>` re-asserts asleep every tick; about 85 % of updates run asleep (#2840/M/n=2,
  #3076/M) and the mod books the asleep minutes and resets hours awake under it (#3001/M). With the only player held
  asleep the world fast-forwards about 20x (#2956/M) — about 32 game-min/s, above the cadence rule, though the mod's
  dt integration handled it (#3001). Night length is controlled by cancelling the hold (`player.sleep.hold <user> 0`)
  at a target world age, to a resolution of one poll (several game minutes under the fast-forward).
- The acute record books debt once per 24 h window at the window's close, not at waking (#3638/C; writer limitation
  `NR_Server_Writer.lua:22`); the window's phase is set by the record's creation, so the driver reads `acute` fields
  to place the short night inside one window.

### 3.4 Exercise and activity

- `exercise.do <squats|pushups|situp|burpees> <minutes>` (client) queues `ISFitnessAction` (harness-commands.md row);
  its reps run on the server (#2879/M).
- The acute suppression needs vigorous work: the melee/tool swing state, or the billed MET `record.body.met ≥ 6.0`
  (HeavyWork), with a Fitness exercise in progress counting as resistance only when MET passes that bar
  (`NR_Server_Writer.lua:153-169`). Billed MET comes from the server's metabolic rate through `classOf`
  (`NR_Server_Metabolism.lua:176-188, 383-388`); live squats billed **3.0–4.0** on the server, never 6.0
  (#2984/M, #3000/M; the rate is a bounded approach that reached 5.1 per tick, #2875/M). So **squats are unlikely to
  register as vigorous** — inference, to be read in the scenario's gate.
- The run and sprint flags do not reach the server's copy of the player (#2877/M; 11 of 188 ticks on a sprint leg,
  #3384/M): aerobic vigorous work is **not reachable** by the harness's walk/sprint commands.
- The swing state: `attack.melee [<n>]` swings at the nearest zombie within 2 tiles (`PZTestKit_Client.lua:990-1000`);
  `zombie.near` spawns none on the default fixture (#2916/M); an RCON-spawned zombie drew two hits of five swings
  (#2880/M). Whether the server's copy of the player is in `SwipeStatePlayer` during a client swing is **unmeasured**.
- Exercise kcal for the lag: `K.energy.exerciseLag` on the minute's exercise kcal (`NR_Server_Metabolism.lua:394-396`).

### 3.5 Reading the mod's record

The record is `NutritionRevamp.server.store.records.<user>` (a Lua table on the server; 11b plan :303 uses that
path). Fields the scenarios need: `satiety.P`, `satiety.S`, `satiety.L`, `satiety.t`, `satiety.nicH`
(`NR_Kernel_Store.lua` INPUTS :32-34), `body.energyState` (es), `body.met`, `body.trail.at` and the six rings
`body.trail.{kcal,ee,ex,p,carb,lip}.<1..25>` (:66-68), `acute.debtH` / `sleptH` / `awakeH`, `stomachFill`,
`monotony.t[<fullType>] = {n, last}` (`NR_Kernel_Monotony.lua:15-21`).

| Command | What it can read | Gap |
|---|---|---|
| `lua.global <a.b.c>` | one scalar per call, its value | **no numeric-segment fallback** (`PZTestKit_Core.lua:877`, `node = node[part]`), so ring slots `trail.kcal.3` do not resolve; a key holding a dot (`Base.Bread`) cannot be addressed; a table answers its key count only |
| `lua.call <a.b.c> ...` | calls a function with ≤ 4 scalar args, returns 3 scalars | has the numeric fallback (`PZTestKit_Core.lua:1164`); cannot pass a table |
| `lua.setpath <a.b.c> <v>` (server) | sets a scalar (nil allowed), numeric fallback (`PZTestKit_Server.lua:2793`) | never creates a missing parent (harness.md:194) |
| `witness.moddata` | player, item or global modData | the record is no longer in modData (#3647) |
| `lua.global NutritionRevamp.server.store.file.last.<user>` | the whole last-saved inputs-only JSON line as one string (`F.last[username] = text`, `NR_Server_Store.lua:323-327`) | inputs only, as old as the last save (≤ one real minute, or the last eat) |
| `mirror.request` and the client mirror | `body_energyState`, `acute_debtH`, `stomachFill`, `stomachMass` (`NR_Kernel_Mirror.lua:38-158`) | client copy at request time (#2974/M), 5 s request limit (`NR_Server_Bus.lua:21`), no satiety P/S |

**Harness additions needed** (each lands in its own commit with the balance check and the regenerated table before the
run that uses it, CLAUDE.md § 5):

- **H1 `lua.read <path> [<path> ...]`** (shared, or server): several dotted scalars read in one tick, with the numeric
  segment fallback `lua.call` already has and an escape for a key holding dots (e.g. `monotony.t.[Base.Bread].n`), or
  equivalently a `lua.dump <path> [depth]` that returns a subtable through `TK.json` (depth cap 8, as x192 relied on).
- **H2 `minute.ring <user> <n> <path...> | read | off`** (server): on every `EveryOneMinute` (or every mod run, read off
  `NutritionRevamp.server.players.served`) append worldAge, hour, the subject's HUNGER, THIRST, FATIGUE, ENDURANCE,
  BOREDOM, UNHAPPINESS, NICOTINE_WITHDRAWAL and up to N record scalars to a capped ring; `read` writes a result file.
  This is what makes per-minute readings possible at speed 5, where a bus round trip spans several game minutes. The
  precedent is `tick.ring` (harness-commands.md). The sampler must state its phase: the minute event fires before the
  queue drains, so a sample taken in the event reads the previous run's writes.
- No new command is needed for eating, spawning, stats, sleep, smoking (pending the lighter gate) or chain restarts.
- Not harness, but needed: **`TKX_StudyFoods`** (declared study foods, § 3.1) and a **replay-of-live tool** (Python
  on the lupa kernel host, as the oracles run) that steps the real kernels and the writer over the ring's minute log —
  the eats' landed vectors and ages, the billed class, asleep flags, the hour — and emits the minute-by-minute HUNGER
  and record fields the live run should have produced.

### 3.6 Clock control

- `settimespeed <N>` by RCON, as `pzt scenario` does (harness.md:40, 313-321), restored in a `finally`. The server-only
  `time.multiplier` (`PZTestKit_Server.lua:7`) is the fallback used for the 37-tick spacing (#3394); the claim that a
  server-only restore leaves the client accelerated is unverified (#1870/unverified), so a driver restores by RCON.
- World age 0 is 07:00 on the default fixture (#2890/M); read the hour off `time.snapshot`.

### 3.7 The "request-level eater" (question 4)

Two forms, and the plan should run the first and may add the second:

1. **The oracle's mapping, live** — the energy oracles eat three meals at fixed clock times `FAST_MEAL_H = (8, 13, 20)`
   (`test_satiety_meal_studies.py:657`), each meal's kcal `= 650/0.25 × min(0.69, hungerTarget(1 - 0.25, es) ×
   circadian(h))` (`ENERGY_REPLAY`, `:683-688`). Live, at each meal time the driver reads `body.energyState` (H1) and the
   hour, computes that kcal and eats it as whole declared portions (e.g. a 50-kcal `TKX_StudyFoods` unit eaten n times,
   or one fresh item of the nearest size). The next-day intake is the day's sum; it is comparable to the pinned
   ratios (1.304 / 0.986, `:827-840`) through a replay-of-live with the live body.
2. **A closed-loop eater** — poll the written HUNGER (H2's ring or `stats.all`); when it crosses 0.25 (the request,
   vanilla HUNGRY level 2, `test_satiety_meal_studies.py:8`) eat 650 × H/0.25 kcal. It reads the model as a player
   meets it, but **no oracle pins it**; it is graded against the replay-of-live only, and its study comparison is a
   reading, not a pass.

Both need thirst kept (§ 5): a filled water container in the inventory with `autodrink.set <user> true` lands sips
through the fold (#2965/M).

---

## 4. Per-session constraints

- `python testing/pzt doctor` before every boot (CLAUDE.md § 5; #1703).
- ≥ 12 GB free host memory, read and ledgered before each boot (CLAUDE.md § 5; Plan 10c ruling H2-1). The host has
  about 13 GB, so the margin is one client: prefer fixture `default` (one admin client) and use fixture `two` (admin
  -debug plus bob release, #3302, #3298) only where a parallel arm saves a whole session.
- A driver longer than about 15 minutes of wall time is split into sessions, each with its own driver (CLAUDE.md § 5);
  x242 was killed by the background-shell reaper for memory.
- One live session at a time, repository-wide; no live boot overlaps an offline edit under `mod/` (CLAUDE.md § 5).
- Two clients are one session; `pzt run` attaches them one at a time (#3304, #3298).
- Never `-safemode` (#1711).
- **Staged copy:** CLAUDE.md § 5 requires it for a release profile; Plan 11b's Global Constraints (plan :54) extend it
  to every live session of the mod ("the STAGED copy boots ... never `mod/`"), as every x24/x25 profile does
  (`testing/profiles/x25-rebaseline.toml` `path = "release/..."`). Recommendation: the study profiles boot a staged copy
  (`python tools/release_pack.py stage mod/NutritionRevamp --out release/<dir>`), recording the MANIFEST sha256.
- **`Nutrition = false`** in every acceptance profile of the mod (ruling T18-1; CLAUDE.md § 5), DayLength 1, verify rows
  that are load gates only (the version on each side) (#2050, #1828).
- `[client] timeout` low (180) where a probe may park the `-debug` client (#1768).
- A sleep scenario's profile sets both sleep keys true (§ 3.3).

---

## 5. Live risks already recorded

- **Debug break:** the admin client runs `-debug` and parks in the debugger on the first unguarded mod Lua error
  (#1712/M/n=2, #3318/M); every client-side reading after a park is unusable (#0869). A study session drives the
  client only for `eat.action`, `drink.action`, `exercise.do`, `attack.melee`; the readings are server-side.
- **Raising probes** are gated on the server with a low client timeout, and `pzt run` is expected to fail on them
  (#1246/M/n=2, #1767/M).
- **Store read/write ordering:** compare a raised vanilla store against `record.reconcile.baseline` read after the write,
  or accept one slow minute of legacy-mirror drift (#3309/C, #3293/M, #3294/M; CLAUDE.md § 5). `LegacyMirror` defaults
  true (`NR_Server_Options.lua:51`). The study drivers should not write vanilla stores at all.
- **Driver discipline:** a driver is never edited after its run; a crash before any reading allows one fix
  (ruling B3-2); a host kill before any reading is not a run (B3-1); a trivial, unmeasured or falsified reading is
  written as such and never re-run (CLAUDE.md § 5). The run prefix and profile constants name the driver's own file.
- **Artifacts:** copied byte-identical to `testing/artifacts/<run-id>/` with the artifacts-register row, the
  `do-not-cite.csv` keys and the re-anchor of shifted `artifacts.md` pointers in one commit (CLAUDE.md §§ 4.1, 6;
  harness.md:23). Timeline and window fields are do-not-cite by rule (#1708/M); a truncated timeline mark is never
  quoted (#1794/M).
- **Log greps** exclude the driver's own probe names (CLAUDE.md § 5).
- **Hunger and thirst management:** an unattended subject dies of thirst in about 35 game hours on a 90-minute day
  (#0179/M); with the mod's writer an empty stomach no longer reaches the level-4 hunger drain (#3074/M), but water
  must be supplied.
- **Eat throughput:** a 5–7 s eat (#0121, #2834) and FOOD_EATEN's refusal (#0077) cap eats per minute; many small eats
  per meal are slow.
- **The mod's fresh record:** a fresh record seeds P from vanilla HUNGER at its first minute and starts an empty
  trailing-24 h window (#3646/C, `NR_Kernel_Body.lua:192`). An unfed first day therefore reads a deficit. Every
  scenario except the fast starts with a maintenance warm-up day so es reads about 1 (the steady eater, `:944-956`).
- **Two clients near each other:** not needed here; the release client does not park (#3317/M).

---

## 6. The scenarios

Grading, for every row: **live vs offline replay-of-live** (the replay steps the real kernels over the live minute
log; tolerance below), and **replay vs study** as already pinned by the oracle. The second holds for the live replay
only when the live inputs equal the oracle's (same food vector, same start state, same clock and es); where they
differ, the replay-of-live's study ratio is reported as a reading and its distance from the pinned oracle figure is
named, never graded as a mod failure.

Default tolerances (proposed; the plan pre-registers its own): a request minute within ±3 game minutes or 2 %,
whichever is larger; a HUNGER sample within 0.002 absolute; es within 0.005; a factor (circadian, sleep, nicotine,
acute) within 1 % of the replay's at matched minutes; a monotony delta within 0.05. The live-vs-replay gap is expected
to come from dtM ≠ 1 minutes, the eat's landing time and the partial sleep hold — each logged in the ring and fed to
the replay, so the residual should be near float noise; anything larger is a finding.

Speed: "fast" = DayLength 1 with `settimespeed 5` (≈ 7.6 game-min/s, about 72 game h per session), conditional on S0;
"slow" = DayLength 1 speed 1 (1.6 game-min/s, about 16 game h per session); eat windows slowed with
`time.multiplier 0.1674` where a reading sits within 30 game minutes of an eat.

| # | Effect | Study / S rows | Offline oracle (pin) | What the driver does | Game h | Sessions | Readings | Pass |
|---|---|---|---|---|---|---|---|---|
| S0 | Cadence gate (prerequisite) | — | `NR_Kernel_Sched.lua` (code) | at speed 1 then `settimespeed 5`: count minute events against world minutes, `players.served`, `ticksLast`, writer `stats.writes`, the ring's per-run dtM | ≈ 2 | folded into session 1 | events/min, runs per player per game minute, dtM histogram | ≥ 0.99 writes per player per game minute and dtM ≤ 1.05 min on ≥ 99 % of runs at speed 5; else every "fast" row below runs slow (×4–5 sessions) |
| 1 | Single-meal hunger return | S1247 (Callahan 2004), S1248 (Cummings 2004) | `test_a_650_kcal_mixed_meal_holds_hunger_off_for_four_to_five_hours` (240–300 × 1.1, ≤ 425), `test_a_fasted_400_kcal_breakfast...` (≥ 180 min), `test_one_meal_or_three_items...` (equal ±2 min) | warm-up day; wait to the request (written HUNGER ≥ 0.25); eat `TKX_StudyFoods.Mixed650`; ring to the next request; next morning a fasted `Mixed400` at 08:00; then three `Mixed217` items at once | ≈ 48 | 1 (fast) | request minute after the landing, held-below duration, P, stomach mass | live request within ±3 min of replay-of-live; replay-of-live within the oracle's band (the oracle holds circadian at 1, live does not: reported) |
| 2 | Protein vs carbohydrate (isoenergetic) | S1222 (Kohanmoo), S1223 (Dhillon), S1224 (Marmonier, differences), S1384 (null, checked) | `test_marmonier_snack_delay_differences_bound_the_protein_weight` (p−c 34 vs 26, p−f 26 vs 35, within 1.5x), `test_a_protein_preload_leaves_less_hunger...`, `test_s1222_vas_level_is_reproduced_at_half_or_more` (0.0134) | per arm: `Mixed650` lunch at the request, a 239 kcal `Snack{P,C,F}` (77/84/58 % share) at +240 min, ring to the dinner request; base arm with no snack; arms sequential (admin), or two in parallel on fixture `two` | ≈ 100 (4 × 25) | 2 (fast; 1 with two players) | dinner-request delays, protein contrast in HUNGER over 3 h | live delays within ±3 min of replay; differences' ratio to the study pinned as oracle; S1224's absolute delays and S1222's half-size stay named non-reproductions (#3622) |
| 3 | Energy density and volume | S1231 (Rolls 1999), S1233 (Rolls 1998, check), S1232 (Marciani), S1235 (Goetze), S1230 (Robinson), S1229 (Rolls 1999 ED) | `test_rolls_1999_soup_casserole...` (1.1x), `test_soup_sates_more...`, `test_fullness_is_linear...` (r² > 0.999), `test_a_less_energy_dense_meal_sates_more` | from the request: `Casserole`, `Soup` (same + 356 g water), `Casserole` + 356 mL water by `drink.action`; HUNGER at minute 17 (slow clock around the eat); `Marc` solid+water vs soup over 3 h; `Dense400@0.8` vs `@1.6` over 15 h; water-only foods 100–600 g at minute 1 | ≈ 60 | 2 (mixed slow/fast) | HUNGER at minute 17 → intake mapping (kJ), 3 h means, minute-1 fullness | live within 0.002 of replay at the reading minute; replay's Rolls ratios vs 1.1x (oracle) |
| 4 | Liquid vs solid calories | S1233, S1247 (liquid preloads), S1228 (Melanson, non-reproduction) | `test_rolls_1998_milk_volume_check`, `test_callahans_preloads_*` (250/279/339) | **partial**: a vanilla caloric fluid the mod's table carries (Milk) by `drink.action` against a declared solid of the same kcal and water, both from the request at 09:00 | ≈ 24 | 1 (fast) | request minutes, liquid-lane mass | live vs replay-of-live only; the oracle's composition cannot be drunk (§ 3.1), so no study band is inherited — flagged |
| 5 | Circadian | S1273 (Scheer 2013) | `test_circadian_peaks_at_19_50_and_troughs_at_07_50`, `test_callahans_replay_minutes...the_09_00_factor_matters`; 11c amendment "dinner at 19:00 wakes at about 0.34" | warm-up day; identical `Mixed650` at 08:00 and at 19:00 on two days; ring through each return | ≈ 48 | 1 (fast) | written HUNGER over the day; ratio written/replay-without-factor | factor within 1 % of `1 + 0.085 cos(2π(h − 19.833)/24)` at every minute (`NR_Kernel_Satiety.lua:41-42, 126-127`); 19:00 dinner's wake-up HUNGER vs the amendment's 0.34 as a reading |
| 6 | 36 h fast, next-day intake | S1613 (Johnstone 2002), S1614 (Clayton 2016), S1255 (deficit pin) | `test_the_36_h_fast_ratios_sit_within_their_studies` (1.1x), `test_the_36_h_fast_intake_ratios_are_pinned` (1.304, 0.986), `test_the_fasts_glycogen_is_logged_and_pinned` (es 1.0/1.087/1.13; eb24 −1/−1301/−1950) | warm-up day + day 0 maintenance; fast 20:00 day 0 → 08:00 day 2; days 2–3 request-level meals by § 3.7 form 1; the fed arm is bob in parallel (fixture `two`) or the replay | ≈ 108 | 2 (fast, chained) | es and eb24h at 12/24/36 h, kcal per day per arm | es within 0.005 of replay-of-live; live day-2/day-3 ratios within 2 % of replay; replay vs 1.20 / 1.0 at 1.1x (the oracle's 70 kg man vs the live body: named) |
| 7 | Steady eater's balance | ruling C-8 (no study row) | `test_a_steady_eater_reads_balance_at_every_hour` (es 1.0004–1.0005), `test_a_request_level_eater_eats_maintenance` (1.0075/0.994/0.9978) | shares row 6's chain: bob eats one maintenance day then request-level days 2–5 | ≈ 120 | 0 extra (rides row 6, +1 session for days 4–5) | es each hour of day 5, intake per day | es within 1.00 ± 0.03 every hour and within 0.005 of replay; intake within ±3 % of maintenance |
| 8 | Six meals vs three | S1608 (Ohkawara 2013), S1607 (Raynor 2015) | `test_six_meals_against_three_is_pinned_inside_the_band` (0.969, state held), `..._with_the_energy_state_live_is_pinned` (0.994) | warm-up day; from 08:00 admin eats three `Mixed667`, bob six `Mixed333` every 150 min (fixture `two`), same mass | ≈ 48 | 1 (fast) | 24 h mean written HUNGER per arm | ratio within 1 % of replay-of-live and within [0.9, 1.3]; S1608's direction stays a named non-reproduction (#3622) |
| 9 | Acute exercise suppression | S1502 (King 2017), S1500 (Hu 2023), S1303, S1305, S1306, S1301, S1302 | `test_the_bout_tracks_the_pooled_mm_readings` (0.674 over the bout, −3.8 mm at +30), `test_the_suppression_is_gone_by...`, `test_resistance_swinging_suppresses_less...`, `test_brisk_walking...` | gate: 20 game min `exercise.do squats`, and `attack.melee` at an RCON-spawned zombie, reading `body.met`, `satiety.S` per minute; decay leg: `lua.setpath ...satiety.S 1` at rest and ring the decay | ≈ 6 | 1 (slow) | S, met, HUNGER/(replay without acute) | **likely unmeasured** for the rise (squats bill 3–4 MET, #2984/#3000; the run flag never reaches the server, #2877); the decay leg passes at half-life 0.15 h within 1 % (`NR_Kernel_Satiety.lua:167`) — flagged |
| 10 | Exercise lag over days | S1318 (Whybrow, days 3–16), S1312 (King 2011), S1325 (Karl 2021), S1320/S1664 (24 wk) | `test_whybrow_compensation_over_days_3_to_16_is_about_30_percent`, `test_king_2011_at_steady_state...`, `test_karl_2021_*` (pinned −57.0/19.3 and −45.0/55.2), `test_e_mechanic_at_24_weeks` | 7 game days: daily `exercise.do` sets (the most exercise kcal the server bills), maintenance-sized meals, ring `satiety.L`, `body.trail.ex.*`, es | ≈ 168 | 3 (fast, chained) | L trajectory, the lag's share of the exercise deficit | L and es within 0.5 % of replay-of-live; Whybrow (16 d) and 24-week readings **not run live** (16 days ≈ 6 sessions, 24 weeks impossible) — the 7-day share is a reading against the oracle's day-7 value |
| 11 | Sleep debt | S1284 (Zhu 2019), S1565 (Fenton 2021), S1564, S1567 (Markwald 2013) | `test_one_short_night_raises_hunger_at_the_request_by_the_pooled_size` (11.7 mm, debt 2.0), `..._next_day_intake_within_the_pooled_band` (1.18), `test_recovery_sleep_reverses_the_factor_partially` (debt 1.0, 1.09), `test_a_short_night_across_two_windows_splits_its_debt` (1.5/0.5, 1.135) | profile with both sleep keys; fixture `default` (one player, so the fast-forward runs); nights by `player.sleep.hold`: 7.5 h rested, 5.5 h short in phase with the window close, 9.5 h recovery; request-level meals each day | ≈ 96 | 2 (fast days, fast-forward nights) | `acute.sleptH`, `debtH` at each close, written HUNGER at the meals, factor = written/replay-without-sleep | factor = 1 + 0.18 × clamp(debtH/2) within 1 % (`NR_Kernel_Satiety.lua:187-196`); the booked debt differs from the held night because ~15 % of held minutes run awake (#2840) — the replay uses the booked minutes; replay vs study as pinned |
| 12 | Nicotine withdrawal | S1576 (Stamford 1986), S1577 (Hall 1989) | `test_a_quitting_smokers_next_day_intake_sits_in_s1576s_band`, `test_the_nicotine_replay_is_pinned` (1.1304 next day; 48-day mean 1.1135); `test_writer_shape.py:1162-1181` | `trait.set admin SMOKER add` + push (corrected at Task 10: `Smoker` is not the key); lighter + `Base.CigaretteSingle` by `eat.action`; ring NICOTINE_WITHDRAWAL, `satiety.nicH`, HUNGER for ≈ 13 game h (corrected at Task 10: #3636's 12.7 h is the 60-minute day's; at DayLength 1 the threshold, rate and cap scale with the day length, about 5.5 game h before the stat moves, 0.01125 a game hour and about 51 game h to the cap after a smoke, so the rise spans three sessions, F-T8-3); smoke again (anchor reset); `lua.setpath ...satiety.nicH` nil (T2-F: no rise until a smoke) and to age − 91 × 24 (fade at half) | ≈ 30 | 1 (fast) | w, nicH, factor = written/replay-without-nicotine; next-day request-level intake | factor = 1 + 0.1313 × clamp(w/0.51) × clamp(1 − d/182) within 1 % (`NR_Kernel_Satiety.lua:215-229`); next-day ratio within 2 % of 1.1304; the 48-day mean and week 26 are **not runnable live** (48 and 182 days) — only via the anchor edit |
| 13 | Monotony over 5 days, staple arm, effects floor | S1592–S1595, S1597 (direction; sizes are game choices anchored on #0042) | `test_the_fifth_daily_eat_reads_about_a_stale_item` (9.978), `test_staples_take_the_reduced_slope` (× 0.25), `test_the_cap_holds` (20), `test_a_partial_eat_counts_its_share...` | daily for 5 days: `TKX_StudyFoods.Mono450` (non-staple, mood changes 0) and `Staple450` (FoodType Bread); before each eat `stats.setany` BOREDOM and UNHAPPINESS to fixed values, read server before/after and the client's `stats.all`; ring UNHAPPINESS for 30 game min after each eat | ≈ 100 | 2 (fast, chained) | the eat's BOREDOM and UNHAPPINESS delta, client arrival, UNHAPPINESS after the writer's floor minutes, `monotony.t` via H1 | fifth eat 9.978 ± 0.05 (non-staple), 2.4945 ± 0.05 (staple); delta equal on both stats; no fall below the post-eat value within 30 min (the floor builds on the add, `NR_Server_Intake.lua:870-872`); the +16.6/day tuning question (11e amendment 3) read and handed to Angus |

**Scenario count:** 13 study scenarios plus the S0 gate.
**Sessions:** about **20** at the fast setting with the chains above (rows 1–5: 1+2+2+1+1; rows 6–7: 3; rows 8–13:
1+1+3+2+1+2; S0 folded into the first). Rows 2, 6 and 8 assume two players in parallel on fixture `two` where noted;
run on one client (the memory-safer choice at ~13 GB free) they add about 2 sessions. If S0 fails, the fast rows run
slow and the count roughly quadruples for rows 6, 7, 10, 11 and 13.

### Rows that cannot be run live, and why

- **Callahan's liquid preloads, Rolls 1998's milks and Melanson's drinks with their oracle compositions** — a drink's
  vector is the mod's per-fluid table; an undeclared test fluid lands nothing (`IN.fluidVector`,
  `NR_Server_Intake.lua:662-679`). Only vanilla fluids can be drunk, so row 4 is live vs replay only.
- **Aerobic acute suppression** — the run and sprint flags do not reach the server (#2877, #3384) and squats bill
  3–4 MET (#2984, #3000), under the 6.0 vigorous bar (`NR_Server_Writer.lua:162-169`). The rise leg is likely
  unmeasured; the swing leg depends on an unmeasured server swing state; only the decay leg is certain.
- **Whybrow's days 3–16, E-MECHANIC's 24 weeks, S1576's 48-day mean and S1577's week 26** — too long for any session
  budget at a safe clock (16 days ≈ 6 fast sessions; 24 weeks ≈ 56). The nicotine fade is read by moving the anchor;
  the lag only to day 7.
- **Absolute study numbers on the oracle's 70 kg man** — the fixture's admin is a male body (corrected at Plan 11f
  Task 10: `body.sex` 1 in x260b's LOAD check, fat 14.4 kg and lean 65.6 kg read by the replay tool on `default`,
  F-T4-3; the female body of #2984's bound was an earlier fixture's); every energy-path ratio is graded against a replay of the live body, and its
  distance from the pinned 1.304 / 0.986 / 0.994 is named.

### Blockers and open items for the plan

1. **S0 must pass before any fast row**: the 11a queue under a fast clock is unmeasured (#3352 was the old build),
   and the cadence rows are 42.20.4 readings.
2. **Harness H1 (multi-read with numeric and dotted-key segments) and H2 (per-minute server ring)** must land, each in
   its own commit, before the first study run; without H2, per-minute readings at speed are impossible and only slow
   rows are gradable.
3. **`TKX_StudyFoods`** (declared vectors, mood changes 0, a Bread-type staple, a 50-kcal unit) and the
   **replay-of-live tool** must exist and be tested offline first (the tool's own oracle is the existing tests: fed
   the oracle's own event lists it must reproduce their pins).
4. **The file store's restart** has never run live (Plan 11b Task 4 F/G pending): the first chained session doubles as
   that reading; an end-of-session departure-flush wait is mandatory (§ 2).
5. **Plan 11b is pending** and its Task 4 (live acceptance) covers several of the same paths (eat between writes,
   restart, monotony and nicotine "live reads" in the 11c/11d/11e amendments). Ordering against 11b is Angus's call;
   the 11b amendments' live reads (`.superpowers/sdd/2026-10-08-plan-11b-live-release/11c-amendments.md`) overlap
   rows 1, 5, 9, 10, 11, 12 and 13 here.
6. **Unmeasured gates inside rows**: a smoke by `eat.action` (lighter), the swing state on the server, the eat
   action's duration under `settimespeed` (#0141/open), and a NaN-safe partial eat on the current wrapper (#2832 was
   42.20.4).
