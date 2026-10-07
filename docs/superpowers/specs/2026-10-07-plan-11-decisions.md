# Plan 11 decisions — what Plan 10's spikes and refactor found

Plan 10 (`docs/superpowers/plans/2026-10-07-plan-10-spikes-and-refactor.md`) asked six questions the 2026-10-07 review left under the fixes, and restructured the server adapters behind a golden trace. This memo is what Plan 11 is written from. Each spike's full section, with every reading and its register row, is in the appendices; the sections below give the answer, the recommendation and what it changes in the fixes draft (`docs/superpowers/plans/2026-10-07-plan-11-review-fixes-DRAFT.md`). Five decisions are Angus's and are listed last.

## The spikes

### S1 and S1b — can the takeover go? (rows #3362–#3373; X30 settled, #1296 → #3368)

**Answer.** Yes, by a route nobody had tried. Vanilla's hunger, thirst and fatigue rise rates are seven engine values copied once from the Lua `ZomboidGlobals` table at server boot, one instruction after `OnGameBoot` fires. A mod that assigns them to zero there (or at file scope) leaves the three stats bit-flat while every other vanilla updater runs, and a once-a-minute server write of the three holds exactly and reaches the owner's client (x221). The route's Lua cost is about 11 µs per player per game minute against the takeover's 121 µs (113–132) at a 15-minute day — but the takeover also stops vanilla's seven Java updaters, which the route hands back, and their cost is untimed.

**What the route reproduces, approximates and loses.** Reproduced within one minute: hunger from the stomach, thirst from the pool, INTOXICATION, UNHAPPINESS. Approximated: fatigue asleep (vanilla's sleep recovery still runs between writes, a sawtooth), the STRESS and FOOD_SICKNESS floors, the rmod on sleep endurance, the auto-drink capture. Lost: the PANIC hold (vanilla decays panic every update) and the TEMPERATURE target (vanilla copies the core temperature into the stat every update) — a thin `OnTick` writer keeps PANIC, as #3048 shows a per-tick write outside the hook survives.

**S1b** — the route's seats, run live (x224). The server's `OnGameBoot` reads the mod's own `NR.Mode` at the operator's value, so a boot-time mode works on the server; a client's `OnGameBoot` reads the defaults, so the mode is never read there. Auto-drink still fires under zeroed rates and its drop holds until the next write — so the writer must fold each sip into its THIRST target, or (by inference from vanilla's drink amount) it drinks twice the target at every write while water lasts. An eat between writes moves HUNGER at once and the next write erases it, so the writer must run after the minute's eats land. HUNGER stayed flat on a sprint leg whose run flag reached the server on 11 of 188 ticks (which also narrows #2877); the squats were unread and the swing branch undriven. Vanilla's updaters, timed as the difference an empty hook makes to one player's `update()`, cost about 1 to 11 µs per player per update (three noisy pairs, hook-off first) — so the route's total is about 17 to 77 µs per player per game minute at a 15-minute day against the takeover's 121 µs: a saving of a third to six-sevenths, about 0.57 at the mean, not nine-tenths. (rows #3380–#3386)

**Recommendation.** The hybrid: zero the rates at the server's `OnGameBoot`, write the stats and floors once a slow minute stepping by elapsed world age, keep a thin `OnTick` PANIC (and optionally TEMPERATURE) hold, and remove `Hook.CalculateStats` with its failover. The fork is Angus's (below).

**Changes to the draft.** Task 3 (takeover resilience) goes if the hook goes. Task 6 becomes the main build: the zeroing at the server's `OnGameBoot` behind the mode, the per-minute writer stepping by elapsed world age and running after the minute's eats, each auto-drink sip folded into the THIRST target, and the `OnTick` PANIC hold. Task 13 measures the writer, the hold and vanilla's updaters at 20+ players instead of the handler.

### S2 and S3 — the real cost, the clock, the lifecycle (rows #3346–#3361)

**Answer.**
- The takeover handler costs 19.33 µs per player per tick; one player's slow-minute work about 377 µs (a lower bound: measured at an unchanged world age); the kernel's fast step 4.36 µs. The tick rate (10.07 under either mode) cannot see these costs at the server's 10-tick lock, so #2822–#2824 measured the wrong thing; their narrowing is in the S2+S3 appendix.
- A game minute is 6.27 ticks at a 15-minute day and 37.46 at a 90-minute day, and **a fast clock never fires more than one minute event per tick** — under `settimespeed 30` each tick's ~4.7 game minutes reach Lua as one call. The stagger starvation was measured live: at speed 30 with two players, one player's minute work ran per event.
- The respawn bug reproduced live, in an order the draft did not expect: `OnNewGame` fires while the online list still holds only the dead body, the pending drain then marks the new record dead, and the new object enters the list two ticks later — so the draft's fix (store the new object at `OnNewGame`) is wrong.
- A rejoin makes a new `IsoPlayer`; a rejoin inside one game minute is unmeasured.
- The version folder's `sandbox-options.txt` loads (X22's first half settled for that shape).

**Recommendation.** For the stagger: keep the persistent queue, but size the per-tick share from a wall-time cycle — `perTick = ceil(N / CYCLE_TICKS)`, `CYCLE_TICKS = (ticksLastMinute <= 1) and 10 or min(ticksLastMinute, 10)` — so every player runs once per wall second under a fast clock, at a peak of about 57 µs per player per tick (17, 35 or 87 players at 1, 2 or 5 % of a tick). Every step must then accept a 60-game-minute interval; a test belongs in Task 2. For the respawn: `OnNewGame` evicts the dead object from the online table, and the dead mark is guarded by the record's reset count.

**Changes to the draft.** Task 2's rulings 2 and 4 are rewritten as above. Task 13's acceptance reads `drained` per wall second.

### S4 — hunger feel (rows #3341–#3345)

**Answer.** No stomach half-time reproduces vanilla's hunger: at 4.25 h or less a character goes Very Hungry overnight, at 5 h or more a character on three meals is never hungry, and the shipped 2 h spends 783 of 1,440 minutes at level 3 on a 60-minute day. A satiety scalar raised by vanilla's eat relief and decaying at vanilla's rates, with vanilla's food-eaten freeze, matches vanilla exactly at every day length — because it *is* vanilla's hunger, scaled by the energy balance (an identity of the model, not a measurement). Under it, a meal's bulk, fibre and fat stop affecting hunger; the stomach then times absorption only. Two live risks for any option: the intake reads a food's raw hunger value, which leaves out vanilla's cooked ×1.3 and its stale, rotten and burnt reductions; and the freeze gate would read the mod's own hunger.

**Changes to the draft.** Task 9 is rewritten around the option Angus picks.

### S5 — food instance semantics (rows #3326–#3340)

**Answer.** A partial eat lowers an item's stored calories, macros and hunger but never its base hunger; caught fish scale macros by weight and hunger by a separate factor (the 0.606 skew confirmed); butchering keeps neither ratio; split and replaced outputs hold script values unless `InheritFood`; only `InheritFood` carries food values. One rule covers every family: **scale an eaten item's micronutrients to the calories the eat delivered** (`b.cal × frac ÷ table kcal`), with the hunger ratio only when there are no calories to anchor on (rule #3340). A vanilla bug surfaced: the fishing code's bait exemption compares against the wrong item name and never fires.

**Changes to the draft.** Task 7 Step 1 is answered (`b.calFull = b.cal × b.instBase ÷ b.rawBefore`); its scale also needs the thirst-only form and a craft-path normaliser (guarded for zero calories).

### S6 — the Lua checksum arm (rows #3374–#3379)

**Answer.** It gates exactly like the script arm. One changed byte inside a comment of one Lua file disconnects a user-role client at the join, before it reaches the game; a copy differing only in line endings joins. So **any update that touches a script or Lua file is a server event**, which in practice is every code release.

**Changes to the draft.** Task 12's README update procedure takes the S6 appendix's text; the release tool's manifest diff should cover `.lua` files too.

## The refactor (R0–R4) — what Plan 11 builds on

- **The golden trace** (`testing/tests/kernel/test_golden_trace.py`, golden `df7806d8…daa9e8b3`): six stand-in players over 240 game minutes through meals, second bites, a butchered cut, a dish, alcohol and caffeine, a drink, an outside store write, a death and respawn, a departure and return, a NaN injection and a day close. Every mutation the reviews aimed at the refactor fails it or a pinned unit test. **Plan 11 changes behaviour on purpose, so it re-records the trace — once per task that names the behaviour change it records** (the proposed CLAUDE.md rule).
- **Interfaces Plan 11's code samples must use** (the draft predates them):
  - `NR.worldAge()` (nil on a failed read; `NR.finite` on the value), `NR.finite`, `NR.num`, `NR.obj`, `NR.flag` in `NR_Core.lua`. Four adapters keep `worldAge() or 0` wrappers on purpose — Plan 11's zero-age fix changes exactly those.
  - The slow minute is `NR.server.minute` (`ORDER`, `register(name, fn)`, `run`); steps take `(username, player, record, ctx)`; `ctx.absorbed`, `ctx.mealCa`, `ctx.body`, `ctx.dtM`, `ctx.ageH` replace the hand-off globals. `P.onMinute` still fires, after the pipeline.
  - `K.intake.fractionOf`, `macrosEaten`, `assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)`; `K.heal.body(body, ageH, l0)`.
  - The store kernel takes `records` as its last argument and never falls back to a global.
- **Accepted changes the trace cannot see** (rulings R1-1, R2-1): a shared helper now returns its default where an old copy raised on a throwing getter (unreachable on 42.20.4); a step raising outside its own guard logs `minute: <step> failed for <user>` and counts `NR.server.minute.stats.failures`; a third-party minute listener added at file load now runs after the pipeline.

## Angus's decisions

1. **The takeover fork.** (a) Keep the takeover and harden it (draft Task 3). (b) Switch to zeroed rates with per-minute writes, losing the PANIC hold and the TEMPERATURE target. (c) The hybrid (recommended). Weigh: the cost gap is real on the Lua side but vanilla's updaters come back untimed (measured in S1b at about 1–11 µs per player per update, which makes the saving roughly a half rather than nine-tenths); the mode becomes a restart-only choice; a writer outage means players stop getting hungry rather than falling back to vanilla; any other mod reading the rates sees zero.
2. **Hunger feel.** (a) Vanilla's hunger plus the energy term (exact vanilla feel; bulk stops mattering). (b) A stomach-driven feel at a tuned half-time (closest at about 4.5 h on a 15-minute day; poor on a 60-minute day). (c) A blend in which bulk modulates relief (only distinguishable on a light diet; strength chosen by taste). And separately: **which day length the feel is tuned for** (the fixture runs 90 minutes, the acceptance profile 15, vanilla's default 60).
3. **Record pruning default.** The draft proposes off by default (operators opt in).
4. **Internal ids in shipped comments.** Keep (the maintainers' route to the evidence) or strip (opaque to a Workshop reader).
5. **Subscribing to the five Workshop neighbours** (still the gate on the deferred code reads).

## Appendices

The spike sections follow verbatim, each with its readings and rows.


## Appendix A. S1 — the zeroed-drains alternative

## S1 — the zeroed-drains alternative to the takeover

Run `x221-20261007-083259` (committed at `f6023b1`; probe, profile and driver at `21a667b`). Desk: `task-S1-desk.md`. Delta: `task-S1-claims-delta.tsv` (T101.1–T101.12, a status row for #1216, and #1296 superseded by T101.7). Fix round 1 (claude-opus-5-5) corrected §§ 4, 5 and 7 against the S1 review and added the unmeasured seats and the closing weighing.

**Verdict:** the route works. A mod can zero vanilla's hunger, thirst and fatigue rise rates on a dedicated server. Vanilla's own update then leaves the three stats still in an awake character while every other updater keeps running. A once-a-minute server write holds exactly between writes, at normal and high time speed, and reaches each owner's client. On the Lua side the write costs about 1 µs per player per write, and a whole instrumented minute 11 µs; the takeover handler costs about 121 µs per player per game minute at DayLength 1. That gap is the Lua side only: the route gives back vanilla's seven updaters, which the takeover skips and whose cost is unmeasured (§ 7).

**Recommendation: a hybrid that drops the takeover.**
- Zero the rates at `OnGameBoot` and keep a per-minute writer for HUNGER, THIRST, FATIGUE and the floors that hold between minutes.
- Keep a small `OnTick` writer for the two holds a minute cannot keep: PANIC, and TEMPERATURE if it is kept at all.
- Remove `Hook.CalculateStats` and its failover.
- Before Plan 11 Task 6 builds it, run S1b (Ruling S1-1) for the seats this run left unmeasured (§ 8).

### 1. Where the rates come from

- Each rise of HUNGER, THIRST and FATIGUE in the seven updaters is scaled by one of seven `ZomboidGlobals` statics (T101.1).
- `ZomboidGlobals.Load` writes each one once, copying the Lua key of the same name (`@66–@215 L72–L82`).
- The updaters read them at:
  - `updateThirst @88/@132`
  - `updateStats_Awake @126–@398`
  - `IsoPlayer.updateStats_Sleeping @448–@507`
- Nothing else writes them.
- Not rates: fatigue's sleep recovery is built from literals (T101.2). Endurance's `ImobileEnduranceIncrease` also drives the resting regeneration outside the hook.

### 2. Whether a mod can set them, and when

**On a dedicated server, `Load` runs once.** It runs in `GameServer.doMinimumInit @531 L1517`, in this order (T101.3):
1. Every mod file's file scope (`LoadDirBase @341–@354`).
2. The server's sandbox is loaded into `SandboxVars` (`@423–@498`).
3. `OnGameBoot` fires (`@525–@528`).
4. `Load` runs, one instruction after `OnGameBoot`.

`OnInitGlobalModData` and `OnServerStarted` fire after `Load`, so a write in either is inert.

**Two routes are reachable** (T101.4):
- **File scope:** earliest, but `SandboxVars` still holds the defaults there.
- **An `OnGameBoot` handler:** the server's sandbox is already loaded, so a sandbox option can choose the route.

**Not reachable:**
- `ZomboidGlobals` has no setter.
- It is not exposed to Lua.
- Every exposed path that re-runs `Load` goes through `Core.ResetLua(String,String)`, which resets the whole engine: the boolean overload `ResetLua(Z,String)` delegates to it (`@5 L4111`), and `Core.DelayResetLua` only stores two fields (`L4216–L4217`) that `Core.CheckDelayResetLua` later hands to it (`@30`).

**Live (T101.6):** the `OnGameBoot` handler ran on the server and read `DayLength` 1, the profile's value, already in `SandboxVars`. Both routes landed: B2's flat stats cover the file-scope thirst keys and the `OnGameBoot` hunger and fatigue keys. This answers X30 (#1296, superseded by T101.7), with one gap: X30 asked about a file-scope `HungerIncrease`, and the run zeroed `HungerIncrease` in `OnGameBoot`, with no non-zero value tried. `Load` reads the same table either way, so the gap is taken as closed by inference.

**Not read, and load-bearing for the hybrid:**
- **`NR.Mode` at the server's `OnGameBoot`.** The run read the vanilla `DayLength` there, not a mod's own nested option. Whether `SandboxVars.NR.Mode` is already the server's value at that moment is unmeasured, and the boot-time mode choice rests on it (S1b).
- **The client's `OnGameBoot` against its own `Load`.** The client's handler fired and read its table zeroed, but where `OnGameBoot` falls against `GameWindow.init`'s `Load @262 L1147` was not read. The player updaters do not run on a client (#2236), so this matters only for a mod that reads the client's statics or table.

**Cautions:**
- Set a key to `0`, never `nil`. `Load`'s `doubleValue` would throw at boot (T101.5).
- Lua readers of the table see the zero. That includes the takeover's own `readConstants` (`NR_Server_Fast.lua:52-58`) and QualityCooking (#2564).

### 3. Whether zeroing works

**Yes.** With the writer paused, HUNGER, THIRST and FATIGUE stayed bit-for-bit still across 20 server reads spanning 0.5161 game hours (about 1858 game-seconds) awake (T101.7). Vanilla's unzeroed rates would have moved each by about 0.01–0.02.

**The other updaters still ran:**
- STRESS fell 0.058332 against a predicted 0.058332, over the 1944.39 game-seconds between the two whole-stat reads that bracket the 20 reads.
- BOREDOM rose.

**Asleep (T101.11):** HUNGER and THIRST stayed still. FATIGUE fell in every one of 92 asleep write intervals by vanilla's sleep recovery, 4.56e-4 to 7.99e-4 and 6.15e-4 on average at 0.1. That recovery is literals, not a rate (T101.2). An interval is one `EveryOneMinute` event, about one game minute at the sleep multiplier by inference.

**The 13 excluded intervals.** 13 intervals inside the sleep hold read `isAsleep` false at the minute, yet FATIGUE still fell across every one of them, as it does asleep. They are on the do-not-cite list and excluded from the D grading. The likeliest reading is that the character was asleep for most of each interval and the flag read at the write was the outlier, but that was not read.

**Rates still active for a sleeping or exercising character:**
- Fatigue's sleep recovery (`IsoPlayer.updateStats_Sleeping @56–@422`). It cannot be zeroed.
- Endurance: the sleep regeneration (`@17–@55`), the resting and standing regeneration, and the running, sprinting and swing drains (`IsoPlayer.updateEndurance`, outside the hook).
- Stress decay, idleness, boredom, morale and fitness.

**Zeroed but not exercised here:**
- The exercise hunger arm (`HungerIncreaseWhenExercise`).
- The running thirst factor. It multiplies a zero rate, so it is inferred zero.

### 4. Whether a per-minute write holds

**Yes, between writes.**
- **Holds between writes (T101.8):** every one of 55 per-player minute deltas was 0 on both awake players. All 52 server reads in the window returned the written floats.
- **High time speed (T101.10):** under `settimespeed 30` every per-write delta was still 0, across 309 `EveryOneMinute` writes per player. Those 309 are events, not game minutes: the phase's 60 reads spanned 23.41 game hours, so each event covered about 4.5 game minutes. A fast clock fires at most one `EveryOneMinute` per tick (#3349).
- **Consequence for the writer:** anything it integrates per game minute (a hunger target that advances with time, a sleep sawtooth correction, a floor's rise) must step by the elapsed world age since its last write, never by the event count, or it under-counts under a fast clock or a sleep fast-forward.
- **Reaches the client (T101.9):** every client/server pair matched on `admin` and `bob`. How soon after a write the client changes was not read.

**Not measured:**
- Auto-drink under the writer: neither player carried water.
- A real eat or drink landing between two writes.

### 5. What the takeover does that this route cannot

From the desk table, per item:

| item | verdict | note |
|---|---|---|
| HUNGER from the stomach | reproduces | Its inputs are stamped once a slow minute. An eat's own HUNGER drop now shows for up to one write interval instead of one tick. |
| THIRST from the pool | reproduces | A drink shows for up to one write interval. |
| The HUNGER and THIRST caps under moodle level 4 (0.69 and 0.83, `NR_Kernel_Fast.lua:50-51`) | reproduces, by inference | With the rates zeroed nothing raises either stat between writes, and an eat or drink only lowers it, so a capped write stays under the level-4 threshold until the next. No run read it. |
| FATIGUE (`fS + fCirc + fOff`) | reproduces awake; approximates asleep | Asleep, a sawtooth of one interval of vanilla recovery: measured 4.6–8.0e-4 at 0.1; about 2.3e-3 a game minute above 0.3, by the jar's formula. |
| The frozen-FATIGUE arm (a server where sleep is not both allowed and needed) | unchanged, and moot | `calculateStats @38–@45 L10201` resets FATIGUE before the hook on every update on such a server (#2723), so a per-minute FATIGUE write is erased within one tick. The takeover's frozen arm writes the reset back unchanged, so neither route holds a FATIGUE there. |
| The sleep-onset terms `solMul` and `solAddH` (Plan 5 B6, `NR_Kernel_Fast.lua:203`) | lost unless rewritten | The takeover folds them into its own sleep delay. Under this route vanilla sets `delayToActuallySleep` at sleep onset, and the delay gates vanilla's recovery, which matters while FATIGUE is not owned (`not inp.fOwned`, `:219`). The writer could re-set it through the public `setDelayToSleep` (#2787) one interval late; unmeasured. |
| The re-implemented vanilla arms | gets better | Vanilla runs them itself: the idle-timer and sleep-delay mirrors and the dropped tripping angle stop being limitations. |
| `rmod` on sleep endurance | approximates | By a per-minute correction, one interval late. |
| PANIC hold | loses | Vanilla decays PANIC in the body-damage tick every update: `BodyDamage.UpdatePanicState @74–@75 L482` calls `ReducePanic`, whose `Stats.remove` is `@84 L443` (#3013; the decay was measured at about 0.18 an update, #3048, #3116). A per-minute hold lasts until the next update; it needs a per-tick writer. (The S1 draft's `updateInternal @877 L9138` is the beta-blocker branch, not the general decay.) |
| STRESS floor rise | approximates | A sawtooth of 1.8e-3 per game minute. |
| UNHAPPINESS rise and release | reproduces | One-interval steps; vanilla never decays it. |
| FOOD_SICKNESS floor | approximates | `UpdateIllness @168` decays it. |
| TEMPERATURE target | loses | `Thermoregulator.updateHeatDeltas @203 L985` sets it every update. The takeover's own hold is itself unmeasured (X81). |
| INTOXICATION | reproduces | One-interval lag; `setDrunkReductionValue(0)` does not need the hook. |
| The auto-drink bracket | loses the bracket; the capture approximates | `updateThirst` calls `autoDrink` every update. The writer's pre-write read can land an interval's whole THIRST drop as water, one interval late. Telling it apart from drinks the wrappers already captured needs its own seat. |
| The global hook, its three-strike failover and the server-wide latch | gone | |

### 6. What Overlay could become

Overlay becomes the main path rather than a stub:
- Rates zeroed at `OnGameBoot`.
- A slow-clock writer for the three stats and the minute-holdable floors, stepping by elapsed world age (§ 4).
- A thin `OnTick` writer for PANIC (and TEMPERATURE if kept).

**Constraints:**
- **The zeroing is fixed for the server's life.** No mod route re-runs `Load`, so Mode becomes a boot-time choice read from `SandboxVars` in `OnGameBoot`, which is itself unmeasured for a mod option (§ 2). It can no longer be a live switch.
- **A takeover kept alongside it must snapshot its constants before zeroing.** Today its awake-fatigue arm for an unowned record would read zero.
- **A writer outage is not a vanilla fallback.** With the rates zeroed and the writer stopped, the three stats stand still: the character never grows hungry, thirsty or tired. A failover from the takeover to vanilla would leave no rise at all, so the per-minute writer must always run.

### 7. Cost

| | figure |
|---|---|
| three sets (one call) | 0.8, 0.9 and 0.6 µs over three runs (T101.12) |
| three gets plus three sets | 1.4, 1.6 and 1.6 µs |
| a whole instrumented minute, one player | 11 µs (Lua side; an upper bound with string building) |
| the per-tick PANIC (and TEMPERATURE) hold | **unmeasured** |
| vanilla's seven updaters, which this route runs again | **unmeasured** (the server's ten-tick lock hid them in x222) |
| the takeover handler (S2, #3353) | 19, 21 and 18 µs per call, mean 19.33 µs per player per tick: 19.33 × 6.27 = 121.2 µs per player per game minute at DayLength 1 (113–132 over the three runs), 19.33 × 37.46 = 724 µs at DayLength 4 |

- The writer's figures are T101.12. They are the Lua side only.
- Under the takeover the stat update returns at `calculateStats @49–@59 L10204–L10205` once the hook is registered, so vanilla's seven updaters do not run. The zeroed route runs them again. Their Java cost is added back and not measured.
- On the Lua side the route costs about 11 µs against about 121 µs per player per game minute at DayLength 1, roughly a tenth. The whole-route saving is that tenth less the seven updaters' cost and the per-tick hold's, neither measured; the S1 draft's "about 99 %" was the Lua side alone and is withdrawn.
- The slow minute's own ≈ 350–395 µs is unchanged.

### 8. Unmeasured seats this run leaves

S1b (Ruling S1-1) is to run these after S6:
- `SandboxVars.NR.Mode` read in the server's `OnGameBoot` (the boot-time Mode choice rests on it).
- An auto-drink sip under zeroed rates, with a water container (the capture approximation in § 5).
- An eat landing between two per-minute writes (the one-interval HUNGER visibility in § 5).
- Vanilla's seven updaters' cost against the takeover's, timed by the bench around one `CalculateStats` with and without the hook.

Also unmeasured, outside S1b:
- The exercise hunger arm's zero.
- The client's `OnGameBoot` position against its own `Load`.
- The per-tick PANIC hold's cost.
- The `setDelayToSleep` rewrite of the sleep-onset terms.

### The Plan 11 draft tasks this changes

- **Task 3 (the takeover failover re-arm):** obsolete if the hook is removed. Otherwise it must also snapshot the constants before zeroing.
- **Task 6 (Overlay):** becomes the main build, after S1b. Add:
  - the `OnGameBoot` zeroing behind a sandbox mode;
  - the per-minute writer for HUNGER, THIRST and FATIGUE and the UNHAPPINESS, FOOD_SICKNESS, STRESS and INTOXICATION floors, stepping by elapsed world age;
  - a thin `OnTick` PANIC hold;
  - the pre-write THIRST-drop capture for auto-drink;
  - a test that the takeover's arithmetic is gone or moved.
- **Task 13 (measure the handler and the minute with 20 characters):** the handler bench goes. Measure the minute writer, the `OnTick` hold and vanilla's updaters instead, at 20+ players, under the stagger fix.

**Decision for Angus:**
- (a) Keep the takeover.
- (b) Switch to zeroed drains and per-minute writes, losing the PANIC hold and the TEMPERATURE target.
- (c) The hybrid above (recommended).

### What Angus weighs

The saving is smaller and less certain than the draft said. The route cuts the Lua work per player per game minute to about a tenth, from about 121 µs to about 11 µs at DayLength 1, but it hands the seven vanilla updaters back to the server, and nobody has timed them, so the net saving is less than nine-tenths of the Lua side, by the untimed updaters' cost. The mode would be chosen once at boot and need a restart to change, and even that rests on a read of the mod's own option in `OnGameBoot` that no run has made. A failure of the writer would not drop players back to vanilla: with the rates at zero they would simply stop getting hungry, thirsty or tired until it came back. Any other mod that reads the `ZomboidGlobals` rates, QualityCooking among them (#2564), would read zero. And three things the route depends on are still untested: auto-drink, an eat between two writes, and the exercise hunger arm. They should be run, with the mode read and the updaters' cost, before Plan 11 Task 6 builds on the route.


## Appendix B. S1b — the route's unmeasured seats

## S1b — the zeroed-rates route's unmeasured seats

Run `x224-20261007-092319` (artifact committed at `f9c5f16`; probe `TKX_GlobalsProbe2`, profile `x22-globals2` and driver `x224_globals2.py` at `caab8dd`, before the run). Implementer claude-opus-5-5. Delta: `task-S1b-claims-delta.tsv` (T107.1–T107.7; dry run mints #3380–#3386). Every verdict came back as predicted, with 0 server errors and `admin` never parked.

**Setup.** One boot on fixture `two`, `admin` (-debug) then `bob` (release). PZTestKit, then the frozen 1.0.0 spike copy in Mode 2 with Severity 1.5, then the probe. Nutrition was false and DayLength 4: a game minute is 3.75 s, 37 or 38 server ticks between two writes. The probe zeroed all six non-zero rise keys in the server's `OnGameBoot`. A per-minute writer set HUNGER 0.3, THIRST 0.05 (0.3 during the auto-drink phase) and FATIGUE 0.1. An `OnTick` sampler read `admin` on the server at every tick of each armed window. Mode 2 left the takeover unregistered: the frozen copy's self-report read `mode=overlay … hook=false`, and `NutritionRevamp.server.fast.registered` read false.

### 1. The mod's own sandbox option at `OnGameBoot`: readable, with the server's value

- **Server.** The `OnGameBoot` handler read `SandboxVars.NR.Mode` 2 and `NR.Severity` 1.5, the profile's values. The same file's file scope read 1 and 1, the defaults (T107.1). So Mode can choose the zeroing at the one moment it must happen, one instruction before `ZomboidGlobals.Load`.
- **Client.** The client's `OnGameBoot` read the defaults, Mode 1 and Severity 1, and its `OnGameStart` read 2 (T107.2). A client must never take the mode from its own `OnGameBoot`.
- **Changes in S1.** The boot-time Mode, which § 6 rested on an unread option, now stands on a measurement. The client-side caution is new.

### 2. Auto-drink under zeroed rates: it fires, and its drop survives to the next write

- **The run.** `admin` carried a 0.9 L canteen, and the THIRST target was raised to 0.3. Within two ticks of the next write, `autoDrink` drank 0.6 L (min(amount, 2 × thirst)) and THIRST went to 0. THIRST read 0 at all 36 samples until the next write, and that write's pre-read was 0 (ring `d` −0.3). The 0.3 written then drank the remaining 0.3 L within two ticks and left 0.15, which held to the next write (`d` −0.15). From then on the writes held 0.3 with nothing left to drink (T107.3).
- **Changes in S1.**
  - The "pre-write capture" in S1 § 5 works in full: the writer's read before each write holds the whole sip.
  - There is a new consequence, read as inference from the jar's drink size (#2770) and x151w's live drink (#2939) beside these two drinks, not measured write by write. Each write re-raises THIRST to the mod's target, so while that target stays above 0.1 and the player carries water, vanilla would drink 2 × target at every write. The capture has to feed the sip into the next write's THIRST target before the write. Otherwise a thirsty character drains a full canteen in a few game minutes.
  - The takeover's bracket throttled this. The hybrid has to do it through the target.

### 3. An eat between writes: HUNGER moves at once, and the next write overwrites it

- **The run.** An apple eaten through the client's real `ISEatFoodAction` dropped the server's HUNGER from 0.3 to 0.14 (the item's −0.16) on a tick with no write. The same tick moved THIRST from 0.05 to 0. HUNGER held 0.14 at every sample, 33 ticks or about 3.3 s, until the next write. That write's pre-read was 0.14 and its post 0.3 (T107.4).
- **Changes in S1.** The "one write interval" visibility in S1 § 5 is confirmed. The write erases the eat's satiety unless the hunger target already reflects the eat.
  - The intake wrapper lands the eat in the stomach.
  - The target is stamped on the slow minute.
  - So in Plan 11 Task 6 the writer must run after the slow minute's landing, or read the landing's own result in the same minute. If it runs first, the eat's drop vanishes for a minute and comes back only when the stomach-derived target catches up.

### 4. The exercise arm: HUNGER stayed flat

- **The run.** The phase had a 15 s sprint, a three-minute squat set and five melee swings at a spawned zombie. HUNGER read 0.3 at all 1040 sampled ticks, and all 36 writer deltas were 0 (T107.5). Only the sprint leg engaged the arm.
- **Did the arm engage?** On the sprint leg the server's copy read `IsRunning` and `isSprinting` true on 11 of 188 sampled ticks, 8 of them with `isPlayerMoving` true. Those are the jar's run-branch conditions (`updateStats_Awake @177–@208 L10267`). So the zeroed `HungerIncreaseWhenExercise` had at least those ticks to act on.
- **The squats and the swings did not engage it.** The squats were queued, but their exertion was not read, and endurance rose 0.9935 → 1 across them. The swings never attacked.
- **Caveats.**
  - 8 ticks is thin.
  - The sampler reads at `OnTick`, not inside the update.
  - The swing branch was never driven: `DoAttack` returned false at all five swings, and no tick read `SwipeStatePlayer`.
  - `isPlayerMoving` read true through the squats and the swings while the player stood. It is on the do-not-cite list.
  - x141a (#2877) read `IsRunning` false at every tick of its arms, so the server's view of running is intermittent. This contradicts #2877 as written; the delta narrows #2877 to x141a's arms.
- **Changes in S1.** The run branch of the exercise arm is lightly confirmed, on 8 ticks: its zero is the jar's single writer (#3362), now with a live flat reading on those ticks. The swing branch stays open.

### 5. Vanilla's updaters' cost: about 1–11 µs per player per update

- **Jar.**
  - `calculateStats` is protected on both `IsoGameCharacter` and `IsoPlayer`.
  - `updateStats_WakeState` is protected, and the other six updaters are private.
  - So no Lua route runs one character's stat update alone. The nearest public route is the whole `IsoPlayer.update()` (T107.6), which reaches `calculateStats` through `updateInternal1 → IsoLivingCharacter.update → updateInternal @1555 L9230`.
- **The bench.** `update()` was timed 5000 times on `bob`, with and without an empty `CalculateStats` hook. Any registered callback skips the updaters (#2238, #2100).

  | pair | no hook (µs/call) | hook (µs/call) | difference (µs) |
  |---|---|---|---|
  | 1 | 22.8 | 14.8 | 8.0 |
  | 2 | 27.6 | 17.0 | 10.6 |
  | 3 | 12.6 | 11.6 | 1.0 |

- **Witness that the hook did skip.** STRESS was set to 0.5 before each run. It fell about 0.24 across every unhooked run and 0 across every hooked one (T107.7).
- **Reading the difference.** The difference is the updaters' cost minus the hook's dispatch; the empty handler's body is 0.10 µs. It was measured with the rates zeroed, so the arithmetic was the same but no stat moved. The 1.0–10.6 µs spread is the whole update's noise, not the updaters' own.
- **No upper bound from the tick rate.** The tick rate does not support one: the server's ten-tick lock hides any spare time.

**Changes in S1 § 7 and in "What Angus weighs".** Per player per game minute at DayLength 1 (6.27 ticks):

| | per player per game minute |
|---|---|
| zeroed route: the updaters less the hook's dispatch (off − on) | 6–66 µs (about 41 at the mean, 6.5 µs) |
| zeroed route: the writer's minute | 11 µs |
| zeroed route, total | 17–77 µs |
| takeover handler alone (#3353) | 121 µs |

- The net saving is about a third to six-sevenths, 0.57 at the mean. That is less than the Lua-side "nine-tenths" but well clear of break-even.
- The hook's dispatch cancels. Off − on is the updaters less the dispatch, and #3353's 121 µs is the handler alone, without the dispatch. So the zeroed route less the takeover is (off − on) less the handler, with the dispatch on neither side.
- At DayLength 4 the route costs 48–408 µs against 724 µs.
- The per-tick PANIC hold is still unmeasured and comes on top.

### What changes in the S1 recommendation

The hybrid stands: zero at `OnGameBoot`, write per minute, add a thin `OnTick` PANIC hold, and drop `Hook.CalculateStats`. It now rests on the measured `OnGameBoot` option read, a measured auto-drink and eat behaviour, and a measured cost margin of roughly half. Plan 11 Task 6 gains two ordering rules:
- **Drinks.** Fold the pre-write THIRST drop, the auto-drink sip, into the THIRST target before the write. Otherwise vanilla would re-drink 2 × target at every write while water lasts (inference from #2770 and #2939).
- **Eats.** Run the writer after the slow minute has landed that minute's eats, so the write never erases an eat for a minute.

It also gains one client rule: never read the mode at the client's `OnGameBoot`.

### Still unmeasured

- The swing branch of the exercise arm.
- The per-tick PANIC hold's cost.
- The client's `OnGameBoot` against its own `Load`. T107.2 shows its sandbox read is the defaults, not where it falls.
- The `setDelayToSleep` rewrite.
- Updater cost under non-zero rates and with many players.


## Appendix C. S2 and S3 — the real cost, the clock, the lifecycle

## S2+S3 — the real cost, the clock and the lifecycle (memo section)

Runs: `x222-20261007-075752` (profile `x22-clock`: DayLength 1, `NR.Severity` 1.5, sleep on; phases A B C D F E Z) and `x222d-20261007-080709` (profile `x22-clock-default`: the fixture's DayLength 4; phases A B Z). Both boot the frozen 1.0.0 copy staged at `42784ff` with `NR_Server_Bench.lua` appended (sha256 `8eec9f2f…110839ad9de`, the same on all three deployed copies); fixture `two`, `admin` -debug and `bob` release, Nutrition false, the server at its 10-tick lock, one host. Driver and profiles committed at `e94c36e` before the runs; artifacts at `669ec7a`. Provisional rows `T102.n` / `T103.n` are in `task-S2S3-claims-delta.tsv`. Every figure is n = 1.

### S3 — the clock

**S3.1 OnTick calls per EveryOneMinute.**
- DayLength 1: mean **6.270** ticks per game minute over 63 minutes (46 × 6, 17 × 7, none 0), 10.115 ticks/s, 1.600 world min/s [T103.1].
- DayLength 4 (the fixture's and every vanilla preset's but SixMonthsLater): mean **37.46** over 50 minutes (28 × 38, 20 × 37, one 29, one 40), 10.011 ticks/s, 0.2665 world min/s [T103.2].
- A one-hour day (DayLength 3) is not measured; by proportion about 25 (inference). The review's "about 25 ticks at the default 1-hour day" is right for DayLength 3; the presets' default is DayLength 4, about 37.

**S3.2 EveryOneMinute calls per tick under a fast clock: never more than one.**
- The jar: `GameTime.update` triggers `EveryOneMinute` once when the stored minute stamp differs from the current one, then copies the stamp over, however many minutes the update advanced (`GameTime.update(Z)V @1395–@1418 L664–L666`) [T103.3].
- `settimespeed 30`: 213 EveryOneMinute calls in 214 ticks, `hmax` 1, while the world ran 47.66 min/s at 10.05 ticks/s — about **4.7 game minutes per tick, each tick's 4.7 game minutes reaching Lua as one call** [T103.4].
- All-asleep fast-forward (both players held asleep, both read asleep at the window's middle): the server fast-forwarded to 31.89 world min/s (20× speed 1), 213 events in 213 ticks, `hmax` 1 — about 3.2 game minutes per event [T103.5]. The jar's trigger: `GameServer.main` sets fast-forward when `SleepAllowed`, at least one live player, and every live player asleep (`GameServer.main @3783–@3922 L1033–L1048`) [T103.6].
- So under any fast clock **every game-minute event is followed by exactly one tick** (the ring's every gap was 1), and the event count under-counts game minutes by the speed factor.

**What this does to the 1.0.0 stagger (measured).** Under `settimespeed 30` with two players online the mod's minute counter rose 221 and its drained counter 225 — one player's minute work per event, against 442 had both run [T102.5]. The counters' window is wider than the bench's (their before reads end at wall 183.27, the settimespeed is acknowledged at 184.54, so about 2 s at speed 1 sit inside; reads up to 0.76 s apart; the after reads start at 206.296), so 221 and 225 are not the 213 events of the bench window; the halving against 442 holds across that skew. The second player (by list order `bob`, inference) was starved, as the review predicted for N > ticks per minute: here N = 2 against 1 tick per event.

**Draft ruling 2 — corrected.** "Each tick processes `ceil(queued / ticksLastMinute)` players (all of them when the last minute had no tick, as under sleep fast-forward)": a minute with no tick never happens (T103.3 – T103.5); under a fast clock `ticksLastMinute` reads **1**, so the share is **every queued player every tick**. That is correct (nobody starves) but expensive: every tick then pays N × the slow minute (S2 below), 7.5 ms per tick at 20 players. The kernels integrate elapsed world age, so the minute work need not run once per *event*. Recommended form for Plan 11 Task 2:
- keep the persistent queue (ruling 2's first half stands);
- size the per-tick share from a wall-time cycle, not the game clock: `perTick = ceil(N / CYCLE_TICKS)` with `CYCLE_TICKS = (ticksLastMinute <= 1) and 10 or min(ticksLastMinute, 10)` (one second at the lock; the earlier `max(1, min(ticksLastMinute, 10))` returned 1 under a fast clock, where `ticksLastMinute` reads 1, which is ruling 2 as drafted again and was wrong), so at speed 1 every player still runs every game minute (6 or 7 ticks at DayLength 1, the cycle; 37 or 38 at DayLength 4, capped to 10), and under a fast clock each player runs once per second of wall, its step covering about 47 game minutes at speed 30 or 32 asleep;
- the one constraint that follows: every step must accept a 60-game-minute interval (Metabolism already clamps offline gaps at 60 minutes; Kinetics empties over the whole gap). A test with dt = 60 game minutes per step belongs in Task 2.
- Task 13's B (the stagger under fast-forward) then reads `drained` ≥ N per wall second, not per event.

### S3.3 — the respawn order (ruling 4)

Read every server tick by the bench's watch [T103.7]; the 4345 row is the server log's frame (`players: admin is dead; record kept until respawn`), not a bench tick, and a log frame is read as the bench tick of the same number (inference; the log frames of the reconnect, 3289 and 3914, equal the watch's ticks of the same events):

| tick | event |
|---|---|
| 4296 | `admin` read dead; the dead object stays in `getOnlinePlayers`, marked dead |
| 4344 | `OnNewGame` fires; the list still holds only the dead object; the server logs `store: reset record for admin (reset 1)` |
| 4345 | the pending queue's drain on the dead object logs `players: admin is dead; record kept until respawn` — on the **new** record |
| 4346 | the dead object leaves the list |
| 4347 | the new `admin` object enters the list |
| 4351 | the next game-minute event; the mod's `P.online` moves to the new object |

The record then read `dead` true, `resets` 1, at three reads over 8.6 s [T103.8]: review finding 2 reproduced live, at one tick's distance.

**Draft ruling 4 — confirmed in its aim, corrected in its mechanism.**
- A respawn is a new `IsoPlayer` under the username (confirmed), and so is a reconnect (S3.4).
- But at `OnNewGame` the new object is **not yet** in `getOnlinePlayers` (it enters three ticks later), and the object handed to `OnNewGame` took a different identity number in the bench's Lua identity table from the one that entered the list (`#4` against `#5`; one Java object keyed twice or two objects is not settled by this instrument). So "`OnNewGame` stores the new object in `P.online`" may store an object the list never shows, and `FAST.byChar` keyed by it would miss.
- Recommended: `OnNewGame` **evicts** instead of storing — `P.online[u] = nil` and the username dropped from the queue (or the queue entry made to re-read `P.online[u]` at drain time, which then finds nil and skips) — so no drain can reach the dead object after the reset; `P.minute`'s identity comparison (ruling 4's second clause) then adopts the list's object at the next event and fires first sight. The "dead" mark must also never be written onto a record whose `resets` changed since the queue entry was made (a cheap guard: carry the record's `resets` in the queue entry). Test: the golden-trace host's respawn at minute 101 with the new object appearing two ticks after `OnNewGame`.

### S3.4 — the reconnect

A quit and rejoin of `bob` brought a new `IsoPlayer` (`#3` against `#2`) [T103.9]. The game clock was slowed (`time.multiplier 0.01`, about 68 s of wall per game minute) so a minute might span the reconnect, but the rejoin took 98 s from the quit (a fresh client from the fixture), and one game-minute event fell between the departure (tick 2867) and the arrival (tick 3516): the mod logged `bob left` and a new `first sight of bob`. **A reconnect wholly inside one game minute — the case that skips the first-sight hooks — is unmeasured.** At speed 1 a game minute is 0.6 s (DayLength 1) to 3.75 s (DayLength 4) against a reconnect of well over a minute, so the case needs a day length of many hours or a slowed clock; ruling 4's identity comparison is the cheap guard and stays.

### S3.5 — the options file in the version dir

`NR.Severity` 1.5 read 1.5 as `NutritionRevamp.server.options.severity` and as `SandboxVars.NR.Severity` on the server, `admin` and `bob`; the control boot with no override read 1 [T103.10]. The option is declared only in `42.20.4/media/sandbox-options.txt`, a file that collides with nothing in `common/`. **This settles X22's first half for this shape** (a version dir whose `media/` collides with nothing loads); the shadowed-`common/` half stays open. Owner suggestion: `areas/packaging.md#layout`; `#0835` and `#1288` keep `open` with `bound` naming `x222-20261007-075752` for the first half (CLAUDE.md § 4.3), unless the controller splits them. Plan 11 Task 13's A no longer needs to settle it (it can re-read it for 1.0.1).

### S2 — the real per-player cost

**S2.1 the takeover handler:** 19, 21 and 18 µs per call (3 × 1000 calls on `admin`, `getTimestampMs` resolution 1 ms per run) [T102.1]. The pure kernel step (`bench_fast`) cost 4.36 µs in the same session [T102.4], so the Java reads and writes are about three quarters of the handler. The handler ran 2.06 times per tick with two players (one per player per tick) [T102.3]. Each bench call advances the player's stats by a tick: the reading is cost, not behaviour.

**S2.2 one player's slow-minute work:** 390, 395 and 345 µs per call (3 × 200) [T102.2]. Each call runs at an unchanged world age, so the closed-form steps integrate a zero interval: the shape of the work, not a meal or a sleep minute (a bound, not a worst case).

**S2.3 the tick rate with two clients:** 10.073 ticks/s under the takeover, 10.070 under Overlay (entered live through `sandbox.var NR.Mode 2`, which the options poll had applied when read 6.0 s after the write (wall 282.564 to 288.565), the handler unregistered; set back to 1 it re-registered) [T102.3, T102.6]. **At the server's 10-tick lock the tick rate cannot see a cost this small** (2 × 19 µs + 2 × 377 µs / 6.3 ≈ 0.16 ms of a 100 ms tick): the tick-rate ratio is not a cost instrument.

**S2.4 the player budget** (100 ms tick; means h = 19.33 µs (handler) and m = 376.67 µs (one player's minute work); the budget is N = limit ÷ per-player-per-tick, floored; a limit of 1 % is 1 ms, 2 % 2 ms, 5 % 5 ms of the tick):

Arithmetic: h + m / t where t is the number of ticks over which one player's minute work is spread. Under ruling 2 as drafted (t = 1): 19.33 + 376.67 = 396.0 µs; 1000 / 396.0 = 2.5, 2000 / 396.0 = 5.05, 5000 / 396.0 = 12.6, so 2, 5, 12. Under the wall cycle of CYCLE_TICKS = 10: 19.33 + 376.67 / 10 = 19.33 + 37.667 = 57.0 µs; 1000 / 57.0 = 17.5, 2000 / 57.0 = 35.1, 5000 / 57.0 = 87.7, so 17, 35, 87. The slow-clock rows are averages over the measured ticks per game minute (t = 37.46 and 6.27); the cycle's cap is 10, so at DayLength 4 the capped peak is not the average but the same 57.0 µs, 17, 35, 87 as the fast clock (the minute work lands in 10 ticks and the other 27 pay h only), and at DayLength 1 (6 or 7 ticks, under the cap) the share is the average.

| clock | ticks per game minute | µs per player per tick | 1 % (1 ms) | 2 % (2 ms) | 5 % (5 ms) |
|---|---|---|---|---|---|
| DayLength 4, speed 1, average over 37.46 ticks (uncapped) | 37.46 | 29.4 | 34 | 68 | 170 |
| DayLength 4, speed 1, capped peak (cycle 10) | 10 | 57.0 | 17 | 35 | 87 |
| DayLength 3, speed 1 (inferred), average over ~25 ticks (uncapped) | ~25 | ~34 | ~29 | ~58 | ~145 |
| DayLength 3, speed 1, capped peak (cycle 10) | 10 | 57.0 | 17 | 35 | 87 |
| DayLength 1, speed 1 (6 or 7 ticks, under the cap) | 6.27 | 79.4 | 12 | 25 | 63 |
| any fast clock, ruling 2 as drafted (every player every tick) | 1 | 396.0 | 2 | 5 | 12 |
| any fast clock, the wall-cycle share recommended above (each player once per 10 ticks) | 10 | 57.0 | 17 | 35 | 87 |
| Overlay, DayLength 1 (minute work only; **inference**: Overlay's per-minute cost is assumed equal to the takeover's m, which was not measured) | 6.27 | 60.1 | 16 | 33 | 83 |

So a 20-player server costs about 0.6 ms per tick (0.6 %) averaged at DayLength 4 and 1.6 ms (1.6 %) at DayLength 1, and 1.1 ms (1.1 %) at the capped peak (20 × 57.0 µs); 40 players about 1.2 % and 3.2 % averaged, 2.3 % at the capped peak. Under ruling 2 as drafted a fast clock (sleep fast-forward, or an admin's `settimespeed`) costs 7.9 ms per tick at 20 players and 15.8 ms at 40; the wall-cycle share brings that to 1.1 and 2.3 ms. The handler alone is 2 % of a tick at about 100 players. The per-player cost is not the scaling risk; the per-event minute under a fast clock is.

**The mismeasured rows, and their narrowing for Plan 11's docs** (status rows for the controller; `claims.tsv` untouched):
- `#2822` measured `bench_fast`, the pure kernel step (3.06 µs, now 4.36 µs in x222), not the handler. Narrow its claim to "the fast-kernel step alone" and drop "a representative per-tick floor of the takeover handler's own cost"; its bound names T102.1 (the handler, 18–21 µs) as the handler's figure.
- `#2823` compared one player's takeover and overlay tick rates at the 10-tick lock (ratio 0.990); the lock hides any cost under a few ms. Narrow to "with one player the tick rate at the server's lock did not move", and add to its bound that the ratio is not a cost reading (T102.3: 10.073 against 10.070 with two players).
- `#2824`'s entry-gate verdict rested on `#2822`'s floor and `#2823`'s ratio. The corrected handler figure (18–21 µs) still sits inside the gate's 50 µs budget, so the verdict survives on T102.1, but the slow-minute work (T102.2, 345–395 µs per player-minute) was never in the gate. Narrow it to "the gate passed on the pure step and the tick-rate ratio" with T102.1 and T102.2 named in its bound as the measured cost.

### Plan 11 draft tasks this changes

- **Task 2** (the stagger): ruling 2's "no tick" branch never occurs; replace the share with the wall-cycle share and add a 60-game-minute-step test (S3.2 above).
- **Task 2 / ruling 4** (respawn and reconnect): evict at `OnNewGame` rather than store; guard the dead mark by the queue entry's `resets` (S3.3 above).
- **Task 3** (the takeover): its cost case is now measured (T102.1); the S1 fork weighs 19 µs per player per tick against S1's alternative, not the review's 60–130 µs estimate.
- **Task 13**: A's options-file reading is done for this shape (re-read for 1.0.1 only); B's stagger reading should count `drained` per wall second under fast-forward; F's bench entries are the ones this task used and can be copied; its cost row's budget is the table above.
- **Task 14**: the narrowing of `#2822`–`#2824`; the lessons rule on the stagger should say "size the share from wall ticks, not from game-minute events: a fast clock delivers one event per tick".


## Appendix D. S4 — hunger feel

### S4 — Hunger feel and the satiety default (fix round 1)

Evidence: the fix-round commit (subject `Spike S4: the satiety simulation across day lengths, with vanilla's food-eaten freeze`), `testing/spikes/satiety_sim.py` and its outputs under `testing/spikes/out/`: the index `satiety-summary.md`, one table per day length `satiety-<N>-summary.md`, and the CSVs `satiety-<N>-<model>-<parameter>.csv`. Two runs gave byte-identical outputs (34 files). Delta: `task-S4-claims-delta.tsv` (T104.1–T104.5).

Every day length below is named "a <N>-minute day (DayLength <k>)". `SandboxOptions.getDayLengthMinutes` maps DayLength 1, 2, 3 and 4 to 15, 30, 60 and 90 real minutes (jar L556–L561), and the harness table at `docs/platform/harness.md:153` agrees. The fixture runs DayLength 4, the mod's acceptance profile runs DayLength 1, and vanilla's default is DayLength 3. The c57c82e memo called its day "DayLength = 1" but simulated a 60-minute day (DayLength 3). That was defect 1, and it is corrected here.

#### Verdict

**A satiety scalar that keeps vanilla's FOOD_EATEN freeze is vanilla's hunger, scaled by `energyState`, plus the deficit floor and the 0.69 cap.** The scalar S is raised by the relief `|getHungerChange| × frac` (clamped at 1), decays at vanilla's awake, asleep and exercise rates with the appetite traits, and holds while the health-from-food timer is above 0. At `energyState` 1, S is exactly `1 − HUNGER`, and the update rule is vanilla's rule rewritten on `1 − H`. The 1440/0.0000 agreement below is an identity of the model, not a measurement or a live reading: at energyState 1 below the 0.69 cap S is 1 − HUNGER by construction, and the timer fill is computed from the takeover's own hunger. The simulation shows it on every day length: the menu day, the light menu, the sleep, water and exercise-with-Hearty-Appetite days all give 1440 of 1440 minutes in level agreement and a mean absolute difference of 0.0000.

This means that under option (a), **bulk, fibre and fat stop affecting hunger.** The stomach only times absorption into the pool. The one realism coupling left on hunger is `energyState`: a calorie deficit raises the felt hunger after the same meals.

**The freeze is not optional.** Without it, the scalar is hungrier than vanilla for 594, 457, 236 and 157 minutes of the menu day on the 15-, 30-, 60- and 90-minute days, and never less hungry. The gap grows as the day shortens, because vanilla's freeze lasts 30/N game-seconds per timer unit: the 11000 cap holds 366.7 game-minutes on a 15-minute day and 61.1 on a 90-minute one. The c57c82e figure of "MAD 0.0276, 1204 minutes" holds only on a 60-minute day.

**No stomach half-time reproduces vanilla.** The sweep's best value moves with the day length: 4.5 h on a 15-minute day, 4.25 h on the 30-, 60- and 90-minute days. At its best, the stomach holds hunger at exactly 0 for 1142 to 1221 minutes, against vanilla's 669, 290, 144 and 96. On the light menu it reaches level 3 and is hungrier than vanilla for 683 to 795 minutes at every day length.

#### Question 1 — vanilla, per day length

- **Rates per game-second.** These do not depend on the day length, because every stat rate carries `deltaMinutesPerDay` (#2773).
  - Awake and idle with the FOOD_EATEN moodle down: 9.6e-6 × (1 − H) (#0470, #0474). That is 0.03456 per game-hour at H = 0 (#0574), a time constant of 28.94 game-hours (#0490), and a half-life of `1 − H` of 20.06 game-hours (T104.2).
  - Asleep: 1.0e-6 (#0472).
  - Exercising: 6.4e-6 with the moodle down and 1.92e-5 with it up, so exercise never freezes (#0471, #2773).
  - The appetite traits scale every branch by 1.5 (Hearty Appetite) or 0.75 (Light Eater) (#0485).
  - `StatsDecrease` 3 gives a multiplier of 1.0 (#0483).
- **The freeze.** With the moodle up and the character not exercising, the rate is 0 both awake and asleep (#0473, #2783). The moodle is up while `healthFromFoodTimer` is above 0 (#0511).
- **The timer** depends on the day length. It decays at N/30 units per game-second on an N-minute day (#0529): 0.5 on a 15-minute day, 1.0 on a 30-minute day, 2.0 on a 60-minute day and 3.0 on a 90-minute day.
- **The fill.** It happens only when HUNGER is at its minimum after `Eat`'s write. The timer becomes `(int)(timer + |getHungerChange| × f × 13000)`, the same is added again for a cooked item, and the result is capped at 11000 (#0054, #0503; jar `BodyDamage.JustAteFood` @461 L650, @491 L653, @516 L656, @532 L660). A partly-hungry eater gets no freeze.
- **The HUNGRY moodle** is set at H > 0.15, > 0.25, > 0.45 and > 0.70 (#0508, #0507).

A game minute lasts N/24 real seconds on an N-minute day: 0.625 s, 1.25 s, 2.5 s and 3.75 s.

#### Question 2 — the menu

The menu is T104.1 (`facts/food-item-model.md#script-keys`):
- 07:00: `CerealBowl` −20 and `Banana` −16.
- 12:00: `OpenBeans` −24 and `BreadSlices` −10.
- 19:00: a cooked `Steak`, −40 × 1.3.

The reliefs are 0.36, 0.34 and 0.52, and the menu carries 967 kcal.

A second menu, `light`, tests the options when no meal covers the hunger it meets: a banana at 07:00, bread slices at 12:00 and opened beans at 19:00. On the light menu vanilla never reaches hunger 0, so no freeze fires. On the main menu every meal takes vanilla's hunger to 0. That saturation hides any change to a meal's relief that still covers the pre-meal hunger.

On a 60-minute day, the main menu's freezes are 17.3, 36.8 and 91.7 game-minutes, 145.8 minutes in total. The table reads 144 because the minutes at hunger 0 are counted at the end of each game minute, so a freeze that ends inside a minute does not count that minute (the residual 17 + 37 + 92 = 146 against 144).

#### Question 3 — the options, every day length

The numbers come from `satiety-summary.md`. "Hungrier" and "less hungry" count the minutes in which the model's HUNGRY level is above or below **vanilla's own level at that minute**; this replaces the c57c82e counting (defect 8). A table cell reads agreement / MAD, with (hungrier / less hungry) after it.

| option | model | 15 min (DayLength 1) | 30 min (DayLength 2) | 60 min (DayLength 3) | 90 min (DayLength 4) | light menu (every day) |
|---|---|---|---|---|---|---|
| (a) vanilla hunger + the energy term | decoupled-freeze | 1440 / 0.0000 | 1440 / 0.0000 | 1440 / 0.0000 | 1440 / 0.0000 | 1440 / 0.0000 |
| (a) without the freeze (rejected) | decoupled | 846 / 0.0989 (594/0) | 983 / 0.0524 (457/0) | 1204 / 0.0276 (236/0) | 1283 / 0.0187 (157/0) | 1440 / 0.0000 |
| (b) the stomach, sweep best | stomach | T 4.5 h: 1344 / 0.0304 (96/0) | T 4.25 h: 1226 / 0.0626 (99/115) | T 4.25 h: 1187 / 0.0785 (8/245) | T 4.25 h: 1124 / 0.0850 (0/316) | T 4.25 h: 413 / 0.1516 (795/232); T 4.5 h: 477 / 0.1306 (683/280) |
| (b) shipped | stomach, T 2 h | 373 / 0.3790 (1067/0) | 373 / 0.3396 (1067/0) | 373 / 0.3200 (1067/0) | 373 / 0.3132 (1067/0) | 68 / 0.2924 (1361/11) |
| (c) bulk scales relief | blend-relief β 0.25 | = (a) | = (a) | = (a) | = (a) | 1329 / 0.0348 (0/111) |
| | β 0.5 | = (a) | = (a) | = (a) | = (a) | 963 / 0.0708 (0/477) |
| | β 1 | = (a) | 1364 / 0.0097 (76/0) | 1303 / 0.0167 (137/0) | 1282 / 0.0188 (158/0) | 546 / 0.1372 (0/894) |
| (c) a fill floor | blend-floor w ≤ 0.75, T 2 h | = (a) | = (a) | = (a) | = (a) | = (a) |
| | w 1, T 2 h | 1440 / 0.0001 | 1440 / 0.0036 | 1440 / 0.0062 | 1440 / 0.0072 | 1429 / 0.0012 (0/11) |

Minutes at hunger 0 on the menu day:
- Vanilla: 669, 290, 144 and 96.
- (b) at its best: 1221, 1142, 1142 and 1142. The stomach's plateau does not move with the day length, but vanilla's freeze does.
- (c) floor w 1: 685, 466, 374 and 344.

The (c) parameters are defined as follows:
- **blend-relief:** the relief is multiplied by `clamp(r / r0, 0.25, 4)^β`. Here r is the meal's fill (bulk / 8) over its relief, and r0 = 2.5079 is the menu day's total fill over its total relief. The day's mean is unchanged, and only the ranking between foods moves.
- **blend-floor:** HUNGER = `1 − max(S, w × fill)` with the stomach at its shipped 2 h.

Both keep the freeze. The other scenarios (`sleep`, `water`, `active`) are in each day's summary. On every one of them, (a) is identical to vanilla.

How to read (c): it can only score worse than (a) against vanilla, because (a) *is* vanilla. MAD is the wrong ruler for it. (c) buys realism (a bulky meal sates more, a full stomach caps hunger) at the price of a vanilla-relative feel, and the table shows that price.
- The floor is inert below w 1. It never binds on either menu, because the fill is never high enough at the same moment that S is low.
- At w 1 the floor only adds a pin at hunger 0 while the stomach is full.
- The relief scaling acts only where a meal does not saturate. On the light menu at β 1 it makes the character less hungry than vanilla for 894 minutes, because bread and beans have a fill-over-relief ratio above the menu mean.

#### Question 4 — fixes in the design (defects 3, 5–9)

- **The relief (defect 3).** The landing does not measure a stat drop. It reads the item's getter. `IN.readBefore` (`NR_Server_Intake.lua:469`) captures the raw `getHungChange` (#0002), which carries none of `Food.getHungerChange`'s ladder (jar L1698-L1704): cooked ×1.3 (the raw read under-relieves), and stale /1.3, rotten /2.2, burnt /3 with a 0.01 floor (the raw read over-relieves). Vanilla's `Eat` and `JustAteFood` use the laddered `getHungerChange` (#0017, #0054). On the menu the difference never shows: the `decoupled-freeze-raw` row equals vanilla, because the steak's raw 0.40 still covers the 0.198 before dinner. A cooked meal that does not saturate would relieve only 1/1.3 of what vanilla does. **Recommendation:** `readBefore` also captures `getHungerChange()`, and S takes `|getHungerChange()| × frac`, clamped at 1.
- **The freeze gate under the takeover.** The eat still runs vanilla's `Eat` and `JustAteFood`. The timer fills when `Eat`'s write takes the *takeover's* last-written HUNGER to 0. The simulation models this for every takeover model.
  - At energyState 1 and below the cap, that stat is `1 − S`, so the gate fires exactly when S reaches 1.
  - Under a deficit (energyState > 1), the stat sits above `1 − S`, so the gate fires less often and the deficit character freezes less. That is a second, intended-looking coupling, and it should be named in the design.
  - At the 0.69 cap the stat can reach 0 while S < 1, so a starving character can earn a freeze its S did not. This is rare and harmless, but it is a difference from vanilla.
- **The update rule and where the decay lives (defect 5).** The rule per game-second is `dS = −rate × StatsDecrease × trait × S`:
  - rate = 9.6e-6 awake idle, 1.0e-6 asleep, 6.4e-6 exercising. With the moodle up it is 0 idle or asleep and 1.92e-5 exercising (#0470–#0473, #2773, #2783).
  - trait = 1.5 Hearty Appetite, 0.75 Light Eater, otherwise 1 (#0485).
  - It is applied as `S × exp(−k·s)`, or per tick as vanilla's own Euler step.

  There are two candidate homes:
  - **`K.fast.step`** — recommended. Every input is already in the input table: `inp.asleep`, `inp.exercising`, `inp.heartyAppetite`, `inp.lightEater`, `inp.sd`, `inp.foodEaten` (the FOOD_EATEN moodle level, `NR_Server_Fast.lua:231`, which is vanilla's gate itself) and `s = M × D`. The four hunger constants are already in `K.fast.defaults` (`hungerIncrease`, `…WhenWellFed`, `…WhileAsleep`, `…WhenExercise`, `NR_Kernel_Fast.lua:33–36`). It tracks vanilla tick for tick, including a sprint and the moment the freeze ends.
    - Cost: S must live where the fast step can write it every tick (on the record the handle holds), which adds one number written per tick on the hot path (`hotpath_lint`). S is persisted at the record's save cadence, like every other record field.
    - Lag: none.
  - **The slow clock.** One closed-form step per slow minute, from the states the adapter left in `lastInp`.
    - Cost: no hot-path change.
    - Lag: up to one game minute. The asleep, exercise and freeze-end states are sampled once a minute, so a sprint shorter than a minute is missed or overcounted and the end of a freeze is late by up to a minute. That is at most 5.8e-4 hunger per minute idle and 1.2e-3 exercising.

    The view would read a value up to a minute stale, which is negligible for feel but breaks the exact equality with vanilla that makes (a) testable to 1e-6.
- **`stomachFill` stays (defect 6).** Kinetics keeps stamping `record.stomachFill` (`NR_Server_Kinetics.lua:95`). Two readers depend on it: the acute dose test (`NR_Server_Intake.lua:194`) and the last-fed clock (`NR_Server_Nutrients.lua:475`). The mirror also reads it (`NR_Kernel_Mirror.lua:24`). Only `K.fast.hungerTarget` stops reading it: it takes S instead of the fill. Its input `inp.stomachFill` can stay filled.
- **The migration (defect 7).** S is a new persisted input field, so the store version bumps.
  - A loaded record without S seeds `S = 1 − current HUNGER`, read off the player at adoption. A character at the 0.69 cap seeds S = 0.31, which is acceptable.
  - Only a new record seeds S = 1, as `seedFull` seeds a new stomach.
  - Seeding S = 1 on every migrated record would sate every existing character at the update.
- **The test tolerance names its day lengths (defect 9).** For (a), `test_satiety_default.py` runs the menu and the light menu on a 15-, 60- and 90-minute day (DayLength 1, 3, 4). It asserts 1440 minutes of level agreement and MAD ≤ 1e-6 against an independent vanilla model at energyState 1, plus the per-tick rate equality. For (b) it would assert, at the chosen T, the table's numbers with a margin on each named day length. A single tolerance with no day length cannot be written, because vanilla itself moves with the day.

#### The decision for Angus

1. **Which option.**
   - **(a) Vanilla hunger plus the energy term.** It tracks vanilla exactly on every day length offline, by the algebra above, so it needs no tuning there; live it holds only once the relief reads the laddered getter and the freeze gate's behaviour under a deficit and at the cap is settled (Question 4), and the energy deficit is the only realism coupling on hunger. Bulk, fibre and fat no longer touch hunger, and the stomach times absorption only. This is the recommendation if the goal is "feels like vanilla, reads the energy balance".
   - **(b) Stomach-driven feel at a tuned half-time.**
     - It is closest on a 15-minute day (T 4.5 h, MAD 0.0304, 1344 minutes agreeing) and drifts as the day lengthens (T 4.25 h, MAD 0.0626, 0.0785, 0.0850).
     - Its plateau at hunger 0 (1142–1221 minutes) is 1.8 to 11.9 times vanilla's freeze minutes.
     - It fails the light menu at every day length: it reaches level 3 and is hungrier than vanilla for 683–795 minutes.
     - The shipped 2 h is far off (MAD 0.31–0.38, 1067 minutes hungrier).
   - **(c) A blend in which bulk shapes the feel.** It is (a) plus a bulk term. The fill floor is inert below w 1 and only a pin at w 1. The relief scaling acts only on meals that do not saturate: β 0.25 shifts the light menu by 111 minutes (MAD 0.0348), and β 1 by 894 minutes (0.1372). If bulk must matter, the relief scaling is the form that does something, at a β Angus picks for taste. Its cost is a vanilla-relative feel that varies with the menu.
2. **Which day length the feel is tuned for.** This matters for (b) and for the β of (c), and not for (a), which reads the same timer vanilla reads and is exact at every length. The fixture runs a 90-minute day (DayLength 4), the acceptance profile a 15-minute day (DayLength 1), and vanilla's default is a 60-minute day (DayLength 3). A (b) tuned on the acceptance profile's 15-minute day (4.5 h) is not the best on the default 60-minute day (4.25 h).

**Whatever is chosen, Plan 11 re-blesses the golden trace for hunger.** Every option changes the HUNGER the takeover writes, so the 1.0.0 trace's hunger columns move.

#### Limits

- `energyState` is held at 1 throughout. The menu's 967 kcal a day is a deficit that would raise it in the mod.
- There are two menus. Both are judgements, not measured play.
- The vanilla model is built from register rows and the jar, not from a live run.
- The kernel lines cited are those at 42784ff and may shift under the refactor before the delta is applied.


## Appendix E. S5 — food instance semantics

## S5 memo: food instance semantics (desk read, 42.20.4 jar b0bbce05d5 and the install's shipped Lua)

controller: write the minted ids into T105.15's bound at apply

Delta: `task-S5-claims-delta.tsv`, 15 rows. Their provisional ids are `T105.1` to `T105.15`, because `claims_delta.py` accepts only numeric `T<n>.<n>` ids and rejects `TS5.n`. A dry run against a copy of the register mints `#3326` to `#3340`, and `claims_check --register-only` on that copy reports 0 findings. Every `lua:` quote was matched by a script against its cited line on the install.

### Q1. Does a partial eat lower the item's stored calories, and its stored hunger?

**Answer: yes for calories, the three macros and `hungChange`; no for `baseHunger`.**

`IsoGameCharacter.Eat(InventoryItem,float,boolean)` does three things in order:
- **The fraction (@28-@78 L5753-L5757).** It turns the requested fraction into a share of what is left: `f = clamp01(baseHunger*f/hungChange)`.
- **The intake (@266-@281 L5778).** It adds `getCalories()*f` to the nutrition store, and the same for carbohydrates, proteins and lipids. When the item is burnt the sum is divided by 5 (@361-@380 L5784).
- **The leftover (@837-@842 L5825).** It calls `multiplyFoodValues(1 - f)`.

`Food.multiplyFoodValues @0-@156 L2288-L2303` multiplies calories, carbohydrates, proteins, lipids and `hungChange` by the factor, along with the other fields in its list. Its body contains no `setBaseHunger`.

A use-based reduction keeps the same invariant. The path is `Food.setCurrentUses` → `consumeHunger` → `multiplyFoodValues(1 - consumed/|hungChange|)` (@0-@14 L2714-L2715).

**What follows (T105.1):**
- The ratio of stored calories to `hungChange` survives every partial eat and every use reduction.
- `getCalories()*getBaseHunger()/getHungChange()`, read before an eat, gives the instance's full-portion calories.
- So the Plan 11 draft's Task 7 Step 1 takes its first branch: `b.calFull = b.cal * b.instBase / b.rawBefore`, guarded on `rawBefore ~= 0`. It is **not** `b.cal`.

### Q2. How does `Fishing.onCreateFish` set a caught fish's macros, BaseHunger and weight?

`lua/shared/Fishing/fishing_properties.lua:709-748` runs server-only and makes three changes (T105.3):
- **Macros.** Each of the four macros is multiplied by `2.2*w/getActualWeight()`, where `w` is the drawn weight in kg. At OnCreate the item is not custom-weight, so `getActualWeight()` is the script `Weight` (#1029).
- **Hunger.** `baseHunger = -(w/weightFactor)`, at least 0.05 in magnitude, and then `hungChange = baseHunger`. The bait exemption never fires: `fishing_properties.lua:737` and `Fish.lua:196` compare `itemType ~= "BaitFish"`, but `itemType` is the full type `Base.BaitFish` (:646), so every fish, bait included, gets the 0.05 floor. This is a vanilla bug a mod cannot fix, and its effect is that every bait fish lands at hunger -0.05 or larger in magnitude (T105.3).
- **Weight.** Actual weight is set to `2.2*w`, with a custom weight.

The same block runs in two more places: `Fish:createFish` (Fish.lua:186-207, the rod catch) and `FishingNet.lua:125-145`. The OnCreate fires at instantiation: `Item.InstanceItem @4022-@4059 L1941-L1944` calls `InventoryItem.initialiseItem`, which calls the Lua `OnCreate` (T105.2). A rod catch therefore composes two scalings, and the result is consistent, because the second divides by the first's custom weight.

**Macro scale and hunger scale are independent (T105.4).** A 2 kg LargemouthBass (Weight 0.4, HungerChange -15, weightFactor 2) has:
- macros ×11
- hunger ×6.67

The ratio between the two is 0.606, which confirms the item-pass review's finding 2.

### Q3. How does butchering set a cut's calories and hunger against its script values?

**Animal carcass, the Lua `ButcheringUtil.modifyMeat` (#2671, extended by T105.5).**
- `hungChange = baseHunger*ratio*draw1`.
- Then `baseHunger = getHungerChange()`. This runs before `setAge`, so the item is still fresh and `baseHunger` equals `hungChange`.
- Then `calories*ratio*draw2`, and likewise for lipids, proteins and carbohydrates, each with its own draw.
- So hunger/script and calories/script differ by `draw1/draw2`, which lies in [0.818, 1.222] (#2672).

**Small animal, `RecipeCodeOnCreate.cutSmallAnimal @72-@169 L347-L355` (T105.6).**
- The cut's `baseHunger` and `hungChange` are the animal's remaining `hungChange`.
- The four macros are 0.75 × the animal's.
- The cut's hunger and macros therefore relate to the cut's own script by unrelated factors.

**Fish fillet, `RecipeCodeOnCreate.cutFish @320-@410 L254-L262` (T105.7).** This is a second fish family.
- Each of the 2 fillets gets hunger = max(base, hungChange)/2 of the fish.
- Each fillet's macros are the fish's current macros /2.
- Guts (uncooked fish only) get the guts script's own max(base, hungChange) (L238-L241). A roe sac, when the month and chance roll gives a fraction above zero, gets the fish's larger hunger times 0.05, 0.10 or 0.15 by size name (L229-L233, L245-L248). Their macros stay at script values.

**Other spawn scalers (T105.8, T105.9).**
- Traps and the forage dead-trap-animal path: one factor on everything.
- Foraged wild food: the macros are always scaled, the hunger only above a floor.
- A fishing lure: its `hungChange` alone is lowered.

T105.10 records that, outside the item edit panel and two client test files, only nine shipped Lua files write these fields.

### Q4. What do a split output and a `ReplaceOnCooked` item hold against their scripts?

**A split without `InheritFood` (T105.11).** A craft output is a fresh `InventoryItemFactory.CreateItem` of the output script (`CraftRecipeManager.createOutputItemInternal @41-@49 L1189-L1190`).
- OpenHotdogPack's input flags are only `AllowFrozenItem;InheritFoodAge;InheritFreezingTime`.
- So each of the four `Hotdog_single` holds exactly its own script values, with `baseHunger == hungChange`, whatever the pack held.

**`ReplaceOnCooked` (T105.12).** `Food.update @255-@286 L400-L402` adds the replacement by name and then calls only `copyConditionStatesFrom`, which reads @0-@125 L5277-L5301.
- That call copies condition, repairs, head condition, sharpness, favourite, blood and a drainable's uses.
- Of the modData, it copies only keys that start with `condition:`.
- It copies no nutrition field. The replacement holds its own script values.

### Q5. Which recipe flags carry food values from inputs to outputs?

**From `InputFlag`'s static initialiser and `CraftRecipeData.createOutputItems` (T105.13):**
- `InheritFood`, through `copyFoodFromSplit` → `copyNutritionFromRatio(1/N)`, is the only flag that copies food values. It copies nine fields, `baseHunger` and `hungChange` among them (#2660, #2661).
- `InheritUses` and `InheritUsesAndEmpty` call `setCurrentUsesFrom`. On a Food that is `setCurrentUses` → `consumeHunger` → `multiplyFoodValues`, so it scales the macros and `hungChange` but not `baseHunger`. The output flags `HasOneUse` and `HasNoUses` act the same way.
- `InheritCooked` copies cooked, burnt and cooking time.
- `InheritFoodAge` copies age.
- `InheritFreezingTime` copies the frozen state.
- `InheritWeight` sets the output to half the input's weight.

**Java craft `OnCreate` writers (T105.14):**
- `copyFoodValuesFromList`, through `makeOmelette` and `makeJar`
- `cutFish`
- `cutSmallAnimal`
- `makeCoffee`, which sets hunger to -0.05 and leaves the macros at the output script's

### Step 2: the per-family scale

**The general formula (T105.15).** The micronutrients that stay proportional to the macros Eat delivers are:

```
landed_micro = table_micro * (b.cal * frac) / table.kcal
```

- `b.cal` is `getCalories()` read before the eat.
- `frac` is Eat's own fraction of what was left. The mod already computes it as `(rawBefore - rawAfter) / rawBefore`, and it is the same `frac` `macrosEaten` uses. For a thirst-only Food it comes from the raw thirst drop.

Inside Intake's existing `vec * instanceScale * share` shape this is:

```
instanceScale = b.calFull / table.kcal,   with b.calFull = b.cal * b.instBase / b.rawBefore
```

The product `instanceScale * share` reduces exactly to `b.cal * frac / table.kcal`.

**Per family.** Each line gives the scale on the table vector, then the factor:

| Family | Scale on the table vector | Factor |
|---|---|---|
| Plain, never eaten | `b.cal/table.kcal`, which is 1 when the item pass matches the table | `share` (= `frac`) |
| Partial | `(b.cal*b.instBase/b.rawBefore)/table.kcal` | `share`. Equivalently `b.cal*frac/table.kcal` |
| Fish (onCreateFish, rod, net) | `b.cal*b.instBase/b.rawBefore/table.kcal`, which is 2.2w/Weight for a whole fish (×11 for a 2 kg bass) | `share`. The hunger ratio (×6.67) is wrong here |
| Butchered (carcass `modifyMeat`, `cutSmallAnimal`, `cutFish` fillets) | the same calorie scale | `share`. Exact per kcal; protein-per-micro carries the independent draw, ±10% per field |
| Split | `InheritFood`: the same calorie scale (macros and both hungers at 1/N of the input, a part-eaten input's ratio carried). No `InheritFood` (OpenHotdogPack): script values, so scale 1 | `share` |
| Replaced (`ReplaceOnCooked`) | script values, so scale 1 | `share` |
| Crafted, the hand-craft map path (`K.vector.craft`) | does not pass through `instanceScale`. To stay proportional, scale the summed vector by `(b.cal*frac)/craftVec.kcal` instead of `share` | — |
| Dish (`K.vector.dish`) | already scaled to the live macro mass | `frac`, proportional by mass |
| Inferred | read off the live macros | `frac`, already proportional |

**Fallback.** When `table.kcal` or `b.cal` is 0 or absent (water, salt, coffee from `makeCoffee` and similar), there are no delivered calories to anchor on. Use the hunger ratio `b.instBase/b.scriptHunger` with `share`, and 1 when the script hunger is 0.

### Step 3: replacement for the Plan 11 draft's Task 7 Step 1

> **Step 1 (answered by Plan 10 S5, T105.1):** A partial eat lowers the stored calories. `Eat` calls `multiplyFoodValues(1 - f)` (`IsoGameCharacter.Eat @837-@842 L5825`), which scales calories, the three macros and `hungChange` but never `baseHunger` (`Food.multiplyFoodValues @0-@156 L2288-L2303`). A use reduction runs the same method. So `b.calFull = b.cal * b.instBase / b.rawBefore`, read at the before-snapshot and guarded on `rawBefore ~= 0`. The product `instanceScale * share` then equals `b.cal * frac / vec.calories`, the calories Eat delivered over the table's. No jar read remains in this task.

### Families the draft mishandles

The draft's `K.vector.instanceScale(tableKcal, fullKcal, rawHunger, baseHunger)` is right for:
- plain, partial, fish, butchered and fillet items
- small-animal cuts
- trap and forage spawns
- `InheritFood` splits
- non-`InheritFood` outputs and replacements

It is right for them provided `fullKcal = b.cal*b.instBase/b.rawBefore`, so that the factor stays `share`. Three cases are still off:

1. **Thirst-only Food with calories** (`instBase == 0`). `calFull` comes out 0, so the draft falls back to the hunger ratio. With `baseHunger` 0 that gives 1, and the micronutrients become `table * share`, where `share = drop/scriptThirst`. Calories and thirst scale together after a partial eat and after an `InheritFood` split, so there the result is proportional to the delivered `b.cal*frac`. It is off only on an item-pass mismatch (the table's kcal against the instance's script calories), on an instance whose calories are not co-scaled with its thirst, or when `scriptThirst` is 0. The fix: `calFull = b.cal * b.scriptThirst / b.thirstBefore`, or the direct form `b.cal*frac/table.kcal` with factor 1. The draft's fallback order is otherwise right.
2. **A lure-reduced item** (T105.9): `hungChange` lowered alone. The draft gives the right total, because `calFull*share` reduces to `b.cal*frac` whatever `instBase` holds. Its `calFull` is inflated, though, so a clamp or cap added later on `instanceScale` would break it. Prefer the direct form.
3. **The craft-map path** (`source == "craft"`). This path never reaches `instanceScale`. It lands Σ input seeds × `share` while Eat delivers the output's own script macros, for example `MakeHotDog`: inputs 176.9 + 150.8 kcal, output 150.8. The micronutrients then run about 2.2× the delivered calories' worth. This is outside Task 7 as drafted. Either normalise the craft vector to `b.cal*frac/craftVec.kcal` in Task 7, guarded on `craftVec.kcal == 0` (no calories to anchor on, so fall back to `share`), or leave it to Task 8, the energy through recipes.

`K.vector.meat`'s comment says "1/amount for a split output (#2660)". That holds only for `InheritFood` splits. A non-`InheritFood` output holds script values, so its scale is 1 under either formula.

### Recommendation and the Plan 11 tasks it changes

- **Task 7.**
  - Step 1 is replaced by the text above.
  - Add a thirst-only-with-calories case and a fillet case to the shape tests. Fillet: macros at half the fish's, hunger at half, against a FishFillet script.
  - Consider the direct form `vec * (b.cal*frac/vec.calories)`, factor 1, with the hunger fallback. It needs no `calFull` and no `instBase` and has fewer guards.
  - Correct `K.vector.meat`'s comment, or remove the function.
- **Task 8, the item pass's energy through recipes.**
  - Owns the OpenHotdogPack energy creation: there is no `InheritFood`, so four fresh script instances are made (T105.11).
  - Owns the MakeHotDog output.
  - Should decide whether the craft-map path normalises to the output's delivered calories.
- **Register follow-up for the controller.** `#0143` (open) asks which items set `baseHunger` different from `hungChange` at spawn. T105.3 and T105.5–T105.8 and T105.14 show that every spawn and craft writer read sets them equal. The unequal pair arises only from a partial eat, a use reduction, a lure (`hungChange` alone) or an `InheritFood` split of a part-eaten input. `ItemStatsPacket.applyItemStats` remains unread, so the row can narrow its bound but not settle.


## Appendix F. S6 — the Lua checksum arm

## Task S6 memo — the Lua checksum arm

Model: claude-opus-5-5. Runs `x223a-20261007-085224` (one-byte copy) and `x223b-20261007-085832` (CRLF copy), each one boot of fixture `two`: the server and `admin` (-debug, role `admin`) on the frozen 1.0.0 spike copy, `bob` (release, role `user` 2) on a copy whose `common/media/lua/shared/NR_Core.lua` alone differs (`meta.tree_diff`: 1 of 65 files). The per-client copy came through the new profile key `[client_overrides.bob]` (harness commit `aaa51f4`). Provisional ids `T106.1`–`T106.5` are in `task-S6-claims-delta.tsv`.

### Question 1 — does a one-byte Lua difference join, disconnect, or join with the difference?

**It disconnects.** The one-byte copy changed one letter inside a comment (`its version` → `its versiom`, same size, LF kept). `bob` never reached the game. Its own connection log records `force-disconnect` at 08:54:10.064, with the reason `checksum-File doesn't match the one on the server:`, then `media/lua/shared/nr_core.lua`, then the path of its copy. The server's user log has no `fully connected` line for `bob`, and the server's player list read `["admin"]` afterwards [T106.1].

The kick is immediate and comes from the client's side, the same shape as the script arm (#3137):
- The client disconnected 1.227 s after the server's anti-cheat line (08:54:08.837).
- No `Timed out connection because checksum was different` line appeared.
- One userlog row was written: `bob`, `LuaChecksum`, `Lua`, `ChecksumPacket`, 1.

`admin`, whose bytes match the server's, stayed connected [T106.2]. A comment is not exempt. The jar shows why: `LuaManager.LoadDirBase` feeds every loaded Lua file except `SandboxVars.lua` to `NetChecksum$Checksummer.addFile`, the same checksummer the script arm uses. `addFile` drops only byte 13 before hashing [T106.4].

### Question 2 — what do both sides' consoles print?

- **Server stdout (boot a):** at boot, its own `luaChecksum: 6191c643de0fc74cb1503a69ff655be3`. At `bob`'s join:
  - `WARN : Multiplayer ... at ChecksumPacket.parseServer > user bob will be kicked in 60000ms because Lua/script checksums do not match`
  - `WARN : Multiplayer ... at AntiCheat.log > Anti-cheat="ChecksumUpdate" is triggered for connection="bob" server-option="AntiCheatChecksum" reason="Lua incorrect checksum" counter=1/1 action="Kick" ping=0`

  The script arm's reason was `Script incorrect checksum`. The warning text is shared by both arms.
- **Server `Logs/<date>_user.txt`:** the same anti-cheat line, then `Connection disconnect index=1` at 08:54:10.088. **`Logs/<date>_connections.txt`:** `bob` at `role="user"`, then `disconnect` `receive-disconnect` at 08:54:10.101.
- **`bob`'s console.txt:** `client: DoLuaChecksum start` with no `DoLuaChecksum end`, then `LuaEventManager: adding unknown event "OnDisconnect"`, and nothing further. The console holds no kick reason. The reason is written only to `bob`'s `Logs/<date>_connections.txt` (`event="force-disconnect" message="checksum-File doesn't match the one on the server: media/lua/shared/nr_core.lua <path>"`), so the three log files are committed beside each artifact.
- **`admin`'s console:** `DoLuaChecksum start` and `end`, and it receives the anti-cheat line as an admin-chat message (`Got message from server: ChatMessage{chat=Admin chat, author='Server', text='Anti-cheat="ChecksumUpdate" ... connection="bob" ...'}`).
- **Boot b:** both sides print only the ordinary lines: the server's `luaChecksum:` hash, and `DoLuaChecksum start` and `end` on both clients.

### Question 3 — is a line-ending-only difference forgiven, as the script arm's is (#1182, #3138)?

**Yes.** `bob`'s copy was `NR_Core.lua` with every line ending CRLF: 3333 bytes with 61 CRs, and with the CRs dropped its MD5 matched the server's `1283f1708c35f2e5ec01349c3414a594`. `bob`:
- fully connected at 09:00:19.186 (server user log);
- reached ready 44.7 s after its launch;
- answered `lua.global NutritionRevamp.version` `1.0.0` at ready and again 93.014 s later, past the 60 s grace;
- appeared in the server's player list at both reads.

Neither log carried a mismatch line, and the userlog stayed empty [T106.3]. The jar shows the mechanism: the Lua arm runs through the same `addFile`, which skips every CR [T106.4].

**Grade defect, recorded and not re-run:** the driver's own grade for boot b reads `falsified`. Its mismatch regex matched `luaChecksum:` (the server's hash line) and `client: DoLuaChecksum start/end`, which are not mismatch lines. Its `bob_disconnect_evidence` matched the settings-table line `SafetyDisconnectDelay` in both boots. These keys and the mismatch-line counts are do-not-cite rows, with the readings to cite named beside them. The driver is not edited (CLAUDE.md § 5).

### What the README's update procedure should say (for Plan 11 Task 12)

Replace the sentence in "Updates and the join checksum" that says the Lua check "is unread" with:

> The game hashes every script **and Lua** file the mod ships and compares them when a client joins; a client whose copy of any one file differs from the server's — even by one character inside a comment — is disconnected before it reaches the game (its log names the file: `checksum-File doesn't match the one on the server`). Only line endings are ignored. So any update that changes a script file or a `.lua` file is a server event: stop the server, update the mod on the server, start it, then let clients update. A client still holding the old release is refused at the join until it updates; it does not join with the difference.

Keep the bypass-role warning as it is. A bypass role clears the Lua flag too (#1230), so a bypassed client would run Lua code the server does not hold. Release notes should say whether a release changes a script **or Lua** file. In practice every code release does, so every release is a server event. The release tool's manifest diff (`#3325`) should cover `.lua` files with the same CR-dropping hash.

### Pages the controller may want touched (not done here: the register and pages are the controller's)

- `docs/platform/mod-anatomy.md`:
  - the checksum-gate section should add the Lua arm's three readings (T106.1–T106.4);
  - the walls line (:239) and "Not covered" line (:241) say the Lua arm is a code reading or uncovered. It is now measured for one byte and for line endings, in one file, under the `user` role.
- `docs/areas/packaging.md`:
  - line 15 ("a reading no run has exercised") and line 99 ("leaves the Lua and animation arms outside its coverage") are affected;
  - line 260 ("Not covered: ... the Lua and animation arms") can drop "Lua";
  - the rule T106.5 belongs in `## Rules`.
- `docs/platform/harness.md`: its profile key table (:56–:70) does not list `client_overrides`. `testing/profiles/README.md` documents the key (commit `aaa51f4`). The harness page's count sentence ("seventeen leaves") is unchanged, since the key is new and outside both figures, the same as `clients`.
- The animation arm stays unread.
