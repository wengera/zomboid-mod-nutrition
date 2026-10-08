# Plan 11 decisions — what Plan 10's spikes and refactor found

Plan 10 (`docs/superpowers/plans/2026-10-07-plan-10-spikes-and-refactor.md`) ran six spikes on questions the 2026-10-07 review left open under the fixes. It also restructured the server adapters behind a golden trace. This memo is what Plan 11 is written from. The sections below give each spike's answer, its recommendation and what it changes in the fixes draft (`docs/superpowers/plans/2026-10-07-plan-11-review-fixes-DRAFT.md`). Each spike's full section, with every reading and its register row, is in the appendices. Six decisions are Angus's and are listed last (the sixth added by Plan 10b at the 60-player design load).

## How to read this memo

- A `#nnnn` is a row of the claims register, `docs/reference/claims.tsv`. Every number in the front sections is at its row or in the appendix named beside it.
- **The takeover** is the mod's shipped `Hook.CalculateStats` handler. Registering it stops vanilla's seven stat updaters for every player (#2238), and the handler computes hunger, thirst, fatigue and the other stats itself, every tick.
- **The zeroed-rates route** sets vanilla's hunger, thirst and fatigue rise rates to zero at boot and lets vanilla's updaters run. The mod then writes the three stats itself once a game minute.
- **The hybrid** is the zeroed-rates route plus a once-a-minute write of PANIC and TEMPERATURE, which vanilla decays or resets every update. S1 first defined it with a per-tick (`OnTick`) PANIC hold; rule 6 (Angus 2026-10-07), Decision 1 and the Performance section replace the hold with the once-a-minute write.
- **The slow minute** is the mod's once-a-game-minute work per player. **The stagger** spreads that work over the server's ticks so no tick runs every player. Under rule 6 (no per-tick work, Angus 2026-10-07) the drain becomes an `EveryOneMinute` round-robin of period m (Decision 1; Performance). Plan 10c's measurements replace that with a budgeted `OnTick` queue that runs every player every minute (Decision 6 (b); Hitching).
- **The floors** are minimum values the mod's effects hold a vanilla stat at: PANIC, UNHAPPINESS, FOOD_SICKNESS and STRESS, plus the INTOXICATION target.
- **`rmod`** is the mod's endurance-regeneration modifier. It scales vanilla's endurance recovery by the character's nutrition state (among its inputs glycogen, protein, iron, dehydration, sleep debt and alcohol).
- **Draft ruling 2** is the draft's rule for the stagger: how many queued players run per tick. **Draft ruling 4** is the draft's rule for a respawn or a reconnect: which `IsoPlayer` object the mod keeps for a username.
- **Day lengths.** DayLength 1, 2, 3 and 4 are 15-, 30-, 60- and 90-minute days (Appendix D). The acceptance profile runs DayLength 1, the fixture DayLength 4, and vanilla's default is DayLength 3.

## The spikes

### S1 and S1b — can the takeover go? (rows #3362–#3373, #3380–#3386; X30 answered, #1296 superseded by #3368)

**Answer.** Yes, by the route X30 asked about. Vanilla's hunger, thirst and fatigue rise rates are seven engine values (#3362). The engine copies them once from the Lua `ZomboidGlobals` table at server boot, one instruction after `OnGameBoot` fires (#3364). A mod that assigns them zero in an `OnGameBoot` handler or at file scope leaves the three stats flat (#3368). Every other vanilla updater keeps running (#3368). A once-a-minute server write of the three stats holds exactly between writes and reaches the owner's client (#3369, #3370).

**Cost.** Per player per game minute at a 15-minute day:
- The takeover handler costs about 121 µs, 113–132 over three runs (#3353; Appendix A § 7).
- The route's own Lua writer costs about 11 µs (#3373).
- The route also hands back vanilla's seven updaters, which the takeover had stopped. S1b timed them at about 1 to 11 µs per player per update (#3386). That is 6–66 µs per player per game minute (Appendix B § 5).
- So the route costs about 17–77 µs against the takeover's 121 µs. The saving is a third to six-sevenths, about 0.57 at the mean (Appendix B § 5).
- The once-a-minute PANIC and TEMPERATURE write that rule 6 puts in place of a per-tick hold adds two stat sets a player a minute, under a microsecond by #3373's 0.6–0.9 µs per set (inference; not timed as such; Decision 1 (c)).
- The slow minute's own work is the same under every option: 1583 µs per player measured in play (#3387); 377 µs (#3354) is the zero-interval lower bound.

**What the route reproduces, approximates and loses** (Appendix A § 5):
- **Reproduces:** hunger from the stomach; thirst from the pool; INTOXICATION; UNHAPPINESS; the HUNGER and THIRST caps under moodle level 4 (by inference, no run read them). Each lags by up to one write interval.
- **Approximates:**
  - fatigue asleep: vanilla's sleep recovery still runs between writes, so FATIGUE saw-tooths (#3372);
  - the STRESS and FOOD_SICKNESS floors, which vanilla decays between writes;
  - `rmod` on sleep endurance, applied one interval late.
- **Loses unless rewritten:** the sleep-onset terms `solMul` and `solAddH`. The writer could re-set vanilla's sleep delay through `setDelayToSleep` (#2787), one interval late; this is unmeasured.
- **Loses:**
  - the PANIC hold, because vanilla decays PANIC every update (#3116). A once-a-minute write keeps PANIC within 1.2556 of its target between writes, measured at a target of 10 (#3400; Decision 1 (c)). S1 first proposed a per-tick write outside the hook, which survives (#3048); rule 6 replaces it.
  - the TEMPERATURE target, because vanilla sets it every update. The takeover's own hold is itself unmeasured (X81).
  - the auto-drink bracket. The takeover throttled auto-drink inside its handler. Under the route the writer reads THIRST before each write, and that read holds the whole sip (#3382). S1b showed the sip must also be folded into the next THIRST target (below).
- **Unchanged and moot:** the frozen-FATIGUE arm. On a server where sleep is not both allowed and needed, vanilla resets FATIGUE before the hook on every update, so neither route holds FATIGUE there.
- **Gets better:** the arms the takeover re-implements (the idle timer, the sleep-delay mirrors, the tripping angle) are vanilla's own again.

**S1b** ran the route's open seats live (x224):
- The server's `OnGameBoot` reads the mod's own `NR.Mode` at the operator's value (#3380). So a boot-time mode works on the server.
- A client's `OnGameBoot` reads the defaults (#3381). So a client must never read the mode there.
- Auto-drink still fires under zeroed rates, and its drop holds until the next write (#3382). The writer must fold each sip into its THIRST target. Otherwise, by inference from vanilla's drink size (#2770, #2939), vanilla drinks twice the target at every write while water lasts.
- An eat between writes moves HUNGER at once, and the next write erases it (#3383). So the writer must run after the minute's eats land.
- HUNGER stayed flat on a sprint leg whose run flag reached the server on 11 of 188 ticks (#3384). That reading also narrows #2877 to x141a's arms. The squats' exertion was not read, and the swing branch was never driven.

**Recommendation.** The hybrid: zero the rates at the server's `OnGameBoot`; write the stats and the floors once a slow minute, stepping by elapsed world age; keep a thin `OnTick` PANIC hold (TEMPERATURE optionally); remove `Hook.CalculateStats` and its failover. Rule 6 (no per-tick work, Angus 2026-10-07) replaces the `OnTick` PANIC hold with the once-a-minute PANIC and TEMPERATURE write (Decision 1 (c); Performance). The fork is Angus's (Decision 1). It is coupled to the hunger-feel choice (Decision 2).

**Changes to the draft under Decision 1's (b) or (c).**
- **Task 3** (takeover resilience) goes, with draft rulings 6 (the failover's strikes and re-arm) and 7 (the per-tick trim).
- **Task 6** becomes the main build. Draft ruling 10 ("Overlay is nutrients only") and Task 6's drafted body (the dehydration terms read zero while vanilla owns thirst) go with the hook. The new Task 6:
  - zeroes the rates at the server's `OnGameBoot`, behind the mode, setting each key to `0`, never `nil` (#3366);
  - never reads the mode at the client's `OnGameBoot` (#3381);
  - writes HUNGER, THIRST and FATIGUE and the UNHAPPINESS, FOOD_SICKNESS, STRESS and INTOXICATION floors once a slow minute, stepping by elapsed world age, not by the event count (#3371);
  - runs the writer after the minute's eats land (#3383);
  - folds each auto-drink sip into the THIRST target before the write (#3382);
  - adds the once-a-minute PANIC and TEMPERATURE write;
  - adds a test that the takeover's arithmetic is gone or moved.
- **Task 13** measures what the re-based list leaves: vanilla's updaters at 20 or more players. Its re-based list is under Re-basing the draft, Task 13 (about :192–199).
- **Task 12**'s CHANGELOG line "the stat takeover recovers after a fault" and the README sentence on the re-arm schedule go. The Overlay line is rewritten to say what the mode now chooses.
- **Draft ruling 4**'s concern that `FAST.byChar` may be keyed by an object the online list never shows (Appendix C S3.3) leaves with the handler. The per-minute writer's handle inherits it.

**Changes to the draft under Decision 1's (a)** ((a) withdrawn under rule 6; kept for the record)**.** Task 3 stays as drafted. Task 6 stays as drafted (Overlay is nutrients only). Draft ruling 4's fix must also re-key `FAST.byChar` to the object the list shows. No constant snapshot is needed, because nothing is zeroed.

### S2 and S3 — the real cost, the clock, the lifecycle (rows #3346–#3361)

**Answer.**
- The takeover handler costs 19.33 µs per player per tick (#3353, the mean of 19, 21 and 18).
- One player's slow-minute work costs about 377 µs (#3354). That is a lower bound: it was measured at an unchanged world age.
- The kernel's fast step alone costs 4.36 µs (#3356).
- The tick rate read 10.07 under either mode (#3355). At the server's 10-tick lock it cannot see these costs. So #2822–#2824 measured the wrong thing; their narrowing is in Appendix C.
- A game minute is 6.27 ticks at a 15-minute day (#3346) and 37.46 at a 90-minute day (#3347).
- **A fast clock never fires more than one minute event per tick** (#3348). Under `settimespeed 30` each tick's ~4.7 game minutes reach Lua as one call (#3349).
- The stagger's starvation was measured live: at speed 30 with two players, one player's minute work ran per event (#3352).
- The respawn bug reproduced live, in an order the draft did not expect (#3358, #3359). `OnNewGame` fires while the online list still holds only the dead body. The pending queue then marks the new record dead. The new object enters the list three ticks after `OnNewGame`. So the draft's fix (store the new object at `OnNewGame`) is wrong.
- A rejoin makes a new `IsoPlayer` (#3360). A rejoin inside one game minute is unmeasured.
- The version folder's `sandbox-options.txt` loads (#3361). That answers X22's first half for that shape.

**Recommendation.**
- **The stagger (draft ruling 2).** Keep the persistent queue. Size the per-tick share from a wall-time cycle: `perTick = ceil(N / CYCLE_TICKS)`, with `CYCLE_TICKS = (ticksLastMinute <= 1) and 10 or min(ticksLastMinute, 10)`. Every player then runs once per wall second under a fast clock. Rule 6 withdraws this wall-cycle per-tick share in favour of an `EveryOneMinute` round-robin of period m (Decision 1; Performance); kept for the record.
  - The peak is about 57 µs per player per tick, which allows 17, 35 or 87 players at 1, 2 or 5 % of a tick (Appendix C S2.4).
  - That 57 µs includes the takeover handler's 19.33 µs. Under the hybrid the handler leaves the per-tick figure, and the writer's 11 µs and the unmeasured PANIC hold enter it. Rule 6 withdraws the per-tick share altogether, so this figure is a record.
  - Every step must then accept a 60-game-minute interval. A test of that belongs in Task 2.
- **The respawn (draft ruling 4).** `OnNewGame` evicts the dead object from the online table instead of storing the new one. The dead mark is guarded by the record's reset count, carried in the queue entry.

**Changes to the draft.**
- **Task 2:** draft ruling 2 becomes the `EveryOneMinute` round-robin, not the wall cycle (rule 6; Decision 1), and draft ruling 4 is rewritten as above. Its tests change with them (Appendix C).
- **Task 13:** A's options-file reading is done for this shape; it is re-read only for 1.0.1. B reads `drained` per wall second, not per event. F can copy the bench entries x222 used, and its budget is Appendix C's table. The re-based Task 13 list (about :192–199) supersedes this item.
- **Task 14:** the lessons rule says "drain the minute from `EveryOneMinute` as a round-robin of period m, never from `OnTick`; a fast clock delivers one event per tick, so ceil(N / m) players run an event" (rule 6; #3348). The narrowing of #2822–#2824 rests on #3353 and #3354.
- **Task 3** (only under Decision 1's (a); (a) withdrawn under rule 6; kept for the record): its cost case is now measured at 19 µs per player per tick (#3353), not the review's 60–130 µs estimate.

### S4 — hunger feel (rows #3341–#3345)

**Answer.**
- **No stomach half-time reproduces vanilla.** The sweep's best value moves with the day length: 4.5 h on a 15-minute day, 4.25 h on the 30-, 60- and 90-minute days (Appendix D). At its best the stomach holds hunger at exactly 0 for 1142 to 1221 minutes a day, against vanilla's 669, 290, 144 and 96. On the light menu it reaches level 3 and is hungrier than vanilla for 683 to 795 minutes at every day length.
- The shipped 2 h half-time spends 783 of 1,440 minutes at level 3 on a 60-minute day, where vanilla spends 0 (#3344).
- **A satiety scalar matches vanilla exactly at every day length** (#3345). The scalar is raised by vanilla's eat relief, decays at vanilla's rates and keeps vanilla's food-eaten freeze. It matches because it *is* vanilla's hunger, scaled by the energy balance. The match is an identity of the model, not a measurement.
- Under that scalar a meal's bulk, fibre and fat stop affecting hunger. The stomach then times absorption only.
- Two risks hold for any option. The intake reads a food's raw hunger value, which leaves out vanilla's cooked ×1.3 and its stale, rotten and burnt reductions. And vanilla's freeze gate reads the HUNGER the mod last wrote.

**Recommendation.** Option (a), vanilla's hunger plus the energy term, if the goal is "feels like vanilla, reads the energy balance" (Appendix D). It is the only option exact at every day length. If bulk must matter, option (c)'s relief scaling at a β chosen for taste. The choice is Angus's (Decision 2), and it is coupled to the takeover fork (Decision 1). Under rule 6 the match holds within a slow minute's lag (the coupling at :124 and :453).

**Changes to the draft under every option.**
- `IN.readBefore` also captures the laddered `getHungerChange()`, and the relief uses it.
- Plan 11 re-blesses the golden trace for hunger: every option changes the HUNGER the mod writes.
- The satiety test names its day lengths. A single tolerance cannot be written, because vanilla's own hunger moves with the day length.
- `record.stomachFill` stays: the acute dose test, the last-fed clock and the mirror read it (Appendix D Question 4).

**Changes under (a) or (c).** Task 9 is rewritten around a satiety scalar S.
- S is a new persisted field, so the store version bumps.
- A loaded record without S seeds `S = 1 − current HUNGER`. Only a new record seeds S = 1.
- `K.fast.hungerTarget` takes S instead of the stomach fill.
- S's home depends on Decision 1 (the coupling below).
- The design names the freeze gate's two differences from vanilla: under a calorie deficit the gate fires less often, and at the 0.69 cap a starving character can earn a freeze S did not.
- Draft ruling 13's half-time dial goes. Under (c) a β option replaces it.

**Changes under (b).** Task 9 keeps the half-time dial. Its default comes from the sweep at the day length Angus picks (4.5 h at DayLength 1; 4.25 h at DayLength 2 to 4), not from draft ruling 13's derivation.

**The coupling with Decision 1.** Appendix D recommends homing S in `K.fast.step`, the takeover's per-tick kernel step. There S tracks vanilla tick for tick, and the exact match is testable to 1e-6. Decision 1's (b) and (c) remove the takeover hook, and with it that per-tick step. S would then step once per slow minute. It would lag vanilla by up to one game minute, at most 5.8e-4 hunger idle and 1.2e-3 exercising (Appendix D). The exact equality would be lost, so the test would need a tolerance. Rule 6 excludes a per-tick home, so S steps once a slow minute. Under every Decision 1 option, vanilla's freeze gate reads the HUNGER the mod last wrote: the handler's under the takeover, the writer's under the hybrid.

### S5 — food instance semantics (rows #3326–#3340)

**Answer.**
- A partial eat lowers an item's stored calories, macros and hunger, but never its base hunger (#3326).
- A caught fish scales its macros by weight and its hunger by a separate factor (#3328). The 0.606 skew between the two is confirmed (Appendix E Q2).
- A butchered cut's hunger and calories are scaled from its script by independent random draws, so neither ratio predicts the other (Appendix E Q3).
- A split output holds its script values unless its recipe sets `InheritFood`, and a `ReplaceOnCooked` item always holds its own script values. Only `InheritFood` carries food values from inputs to outputs (Appendix E Q4–Q5).
- One rule covers every family: **scale an eaten item's micronutrients to the calories the eat delivered** (`b.cal × frac ÷ table kcal`). Fall back to the hunger ratio only when there are no calories to anchor on (#3340).
- A vanilla bug surfaced: the fishing code's bait exemption compares against the wrong item name and never fires (#3328).

**Changes to the draft.**
- **Task 7:**
  - Step 1 is answered: `b.calFull = b.cal × b.instBase ÷ b.rawBefore`, guarded on `rawBefore ~= 0` (#3326).
  - Prefer the direct form `vec × (b.cal × frac ÷ vec.calories)` with factor 1. It needs no `calFull` and survives a later clamp on the scale.
  - Add the thirst-only-with-calories form (`calFull = b.cal × b.scriptThirst ÷ b.thirstBefore`, or the direct form).
  - Add two shape tests: a thirst-only Food with calories, and a fish fillet.
  - Correct the comment above the `K.vector.meat` call, or remove the function. "1/amount for a split output" holds only for an `InheritFood` split.
- **Task 8:** owns the OpenHotdogPack energy creation and the MakeHotDog output (Appendix E). It also decides whether the craft-map path normalises to the output's delivered calories (`b.cal × frac ÷ craftVec.kcal`, guarded for zero calories).
- **Register (controller):** #0143 narrows its bound. Every spawn and craft writer read sets base hunger equal to hunger. The row stays open, because `ItemStatsPacket.applyItemStats` is unread.

### S6 — the Lua checksum arm (rows #3374–#3379)

**Answer.** The Lua arm gates exactly like the script arm (#3377). One changed byte inside a comment of one Lua file disconnects a user-role client at the join, before it reaches the game (#3374). A copy differing only in line endings joins (#3376). So **any update that touches a script or Lua file is a server event** (#3378). In practice that is every code release.

**Changes to the draft.**
- Task 12's README update procedure takes Appendix F's text.
- The release tool's manifest diff covers `.lua` files too, with the same CR-dropping hash.
- The harness's `kicked` marker misses a Lua kick, which only the client's connections log records. A Plan 11 run that needs a kick reads that log.

## The refactor (R0–R4) — what Plan 11 builds on

- **The golden trace** (`testing/tests/kernel/test_golden_trace.py`, golden `df7806d8…daa9e8b3`): six stand-in players over 240 game minutes through meals, second bites, a butchered cut, a dish, alcohol and caffeine, a drink, an outside store write, a death and respawn, a departure and return, a NaN injection and a day close. Every mutation the reviews aimed at the refactor fails it or a pinned unit test. **Plan 11 changes behaviour on purpose, so it re-records the trace once per task, in the task that names the behaviour change** (the proposed CLAUDE.md rule).
- **Interfaces Plan 11's code samples must use** (the draft predates them):
  - `NR.worldAge()` (nil on a failed or non-finite read), `NR.finite`, `NR.num`, `NR.obj` and `NR.flag` in `NR_Core.lua`.
  - The slow minute is `NR.server.minute` (`ORDER`, `register(name, fn)`, `run`). Steps take `(username, player, record, ctx)`.
  - `ctx.absorbed` and `ctx.mealCa` replace `KIN.lastAbsorbed` and `KIN.lastMealCa`. `ctx.body`, `ctx.dtM` and `ctx.ageH` replace Nutrients' hand call of `EFF.minute`.
  - Two hand-offs outside the minute remain: `IN.pendingAlc` and `IN.pendingCaf` (eat time to the Nutrients step, `NR_Server_Intake.lua:205-206`, `NR_Server_Nutrients.lua:371-375`), and `FAST.lastInp` (the per-tick handler to the Effects step, `NR_Server_Fast.lua:183`, `NR_Server_Effects.lua:230`).
  - `P.onMinute` still fires, after the pipeline.
  - `K.intake.fractionOf`, `macrosEaten` and `assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)`; `K.heal.body(body, ageH, l0)`.
  - The store kernel takes `records` as its last argument and never falls back to a global.
- **The zero-age sites Plan 11's fix must change.** Six sites still turn a failed clock read into age 0:
  - the four `worldAge()` wrappers that return `NR.worldAge() or 0`: `NR_Server_Fast.lua:83`, `NR_Server_Intake.lua:292`, `NR_Server_Kinetics.lua:38`, `NR_Server_Players.lua:12`;
  - `NR_Server_Metabolism.lua:202` (`ageH or worldAge() or 0`);
  - `NR_Server_Bus.lua:51-53`, which reads `getWorldAgeHours` itself and passes `okA and age or 0` (a non-finite age passes through).
- **Changes the trace cannot see, accepted by ruling** (R1-1, R2-1, R3-1):
  - R1-1, first difference: a shared helper now returns its default where an old copy raised on a throwing getter.
  - R1-1, second difference: a non-finite world age now reads 0 in the four wrappers, where the old copies passed NaN or infinity through.
  - No reachable raise was found on 42.20.4 for either (the R1 review's jar reads; the bug review did not check every Effects and Nutrients call site).
  - R2-1: a step raising outside its own guard logs `minute: <step> failed for <user>` and counts `NR.server.minute.stats.failures`.
  - R2-1: a third-party minute listener added at file load now runs after the pipeline, not before it.
  - R2-1's two changes go into Task 12's operator notes (the CHANGELOG and the README).
  - R3-1: the intake's `IN.fractionOf`, `IN.macrosEaten` and kin are bound to `K.intake` when the file loads, and `K.intake.assemble` calls the kernel functions directly, so a third party that wraps `IN.fractionOf` no longer reaches the eaten item's own chain (nothing in the mod, the harness or the installed corpus wraps them).
  - R0-1: the golden trace was recorded three times in R0's own review rounds, each from the frozen 1.0.0 tree and before the first refactor commit; Plan 11 re-records it only in a task that names the behaviour change it records.

### Re-basing the draft

**What Plan 10c rewrites.** The draft (`docs/superpowers/plans/2026-10-07-plan-11-review-fixes-DRAFT.md`) predates Plan 10c, which rewrites four of its parts (Hitching; Decisions 3 and 6):
- **the drain (Task 2):** a budgeted per-tick queue that carries unserved players across minutes, with a budget sized to the minute's work, in place of both the shipped drain and the round-robin of period m (#3482, #3489, #3490; Decision 6 (b));
- **the store's home (Task 10 and Decision 3):** a server-local file, with pruning on by default (#3417, #3467, #3469);
- **the send stagger (Task 4's push):** each player's push offset over the minute's frames rather than every push in one frame (#3456, #3464; rule #3498);
- **the heal-once refactor:** heal once, before the step, which no draft task holds (#3413, #3458; Ranked refactors, item 1).

1.0.0 has not shipped to the Workshop, so the request leak (#3417, #3469) affects no live server: the store's move is Plan 11 work, not an urgent patch.

The draft's code samples predate the refactor. Per task:
- **Task 1.** The helper set, `server_host.py` and `test_core_helpers.py` landed in Plan 10 R1; Steps 2, 3 and 5's `NR_Core.lua` append are done. What remains is the zero-age fix at the six sites above. Step 5's Kinetics sample is re-based: the step is `step(username, player, record, pipe)` (`NR_Server_Kinetics.lua:46`), and a nil age clears `pipe.absorbed` and `pipe.mealCa`, not `KIN.lastAbsorbed` and `KIN.lastMealCa`. Intake's `num(v)` was kept under its name, not renamed `numv`.
- **Task 2.** `P.minute`'s `NR.worldAge() or 0` becomes the Players wrapper that Task 1 fixes. `P.work(username, player)` keeps calling `NR.server.minute.run` and then `P.onMinute`. `K.stagger.perTick`'s wall-cycle form is replaced by the `EveryOneMinute` round-robin of period m (rule 6; Decision 1), and its "no tick in the last minute" tests go: that case never happens (#3348–#3350). The `OnNewGame` sample evicts instead of storing. The queue entry carries the record's `resets`. The respawn test brings the new object in three ticks after `OnNewGame` (#3358). A 60-game-minute step test is added. Step 9's dead options branch is at `NR_Server_Options.lua:88-110`.
  - **The shipped drain starves players on a normal clock (architecture review, 2026-10-07).** `P.minute` rebuilds the queue each game minute (`NR_Server_Players.lua:49`) and `P.drain` serves one player a tick (`:82-95`). Whenever more players are online than there are ticks in a game minute, the tail of the online list never runs its minute: about 53-54 of 60 at DayLength 1 and 22-23 at DayLength 4 (arithmetic on #3346, #3347). Task 2 must cover this case, not only the fast clock (#3352). Plan 10c measures the replacement scheduler.
  - **Confirmed live, and the replacement chosen (Plan 10c; Hitching).** A mirror of the drain at N = 60 and DayLength 1 left 53 of 58 ghosts never run, the longest 115.7 game minutes stale (#3482). Under Decision 6 (b) Task 2 replaces both the drain and the round-robin of period m above with a budgeted `OnTick` queue that carries unserved players forward, under a budget sized to the minute's work. A 15 ms budget starved none in nine draws at both spacings (#3489, #3490). Task 2's tests cover a normal clock with more players than the minute has ticks, and a fast clock.
- **Task 3** (only under Decision 1's (a); (a) withdrawn under rule 6; kept for the record). `onMinute` is now the pipeline's `"fast"` step, registered with `NR.server.minute.register("fast", onMinute)` (`NR_Server_Fast.lua:563`), with the signature `(username, player, record, ctx)`. A raise there outside its own `pcall` is caught by the pipeline, logged and counted. `FAST.stampSlow` is called from that step. The line ranges in its file list are re-read.
- **Task 4.** `B.flushEffects` is the pipeline's `"bus"` step (`NR_Server_Bus.lua:113`), with the signature `(username, player, record)`. The `mirror.request` listener it rewrites holds one zero-age site (`NR_Server_Bus.lua:51-53`).
- **Task 6.** Rewritten by Decision 1.
- **Task 7.** The scale call moved into the kernel: `K.intake.assemble` calls `K.vector.meat(vec, b.instBase, b.scriptHunger)` at `NR_Kernel_Intake.lua:165`. `IN.readBefore` is at `NR_Server_Intake.lua:334`. Step 1 is answered (S5).
- **Task 9.** Rewritten by Decision 2. The Kinetics call to `K.stomach.empty` is at `NR_Server_Kinetics.lua:63`.
- **Task 10.** `S.prune` already guards a nil age; the sample stands.
- **Task 12.** Adds R2-1's operator notes and the lines each decision changes.
- **Task 13.** Its bench measurements are done (Plan 10b; Performance, below):
  - the minute by step in play, under a fast clock and at a zero interval (#3387–#3390);
  - the burst and the round-robin (#3391);
  - the once-a-minute PANIC and TEMPERATURE write that replaces the hold (#3392, #3393).
  - So F no longer measures the cost on 1.0.1. At most it re-reads `bench.minute`, which still calls `NR.server.players.work(u, p)`, for continuity with #3390. `bench.handler` leaves with the takeover (Decision 1).
  - Its budget table is re-based on the minute's cost = 1583 µs (#3387), not 377.
  - B reads the drain under its `EveryOneMinute` round-robin (each player's ages advance within m game minutes), not the `OnTick` share per wall second.
  - Still unmeasured, and Task 13's if Plan 11 wants them: vanilla's updaters at 20 or more players; the PANIC moodle itself (no harness command reads it); and DayLength 4 set as the option rather than through `time.multiplier` (#3394).
- **Tasks 5, 8 and 11** touch no refactored interface.

### Refactor follow-ups for Plan 11
- The shared helpers' pcall swallows a raising getter without a log line: log it once per member (the bug review's should-fix).
- `K.intake.assemble` builds its chained-lookup closure before the nothing-eaten guard: one allocation per no-op eat (bug review nit 3).
- The gitignored `release/NutritionRevamp` build predates Plan 10: re-stage it with `tools/release_pack.py stage` before any upload (bug review nit 5).
- R1's line-count padding (about 80 blank lines across Effects, Fast, Kinetics, Nutrients, Players, Strength, Training and Weight, and `NR_Server_Metabolism.lua:252`) is collapsed at each file's first Plan 11 edit, with the re-anchor in that commit (whole-pass review).
- The minute context is named `pipe` in the adapters and `ctx` in `NR_Server_Minute.lua` and this memo: pick one name (whole-pass review).


- `test_core_helpers.py` does not pin `NR.obj`, `NR.flag`, `NR.worldAge`'s rejection of infinity, or the four wrappers (R1 review).
- Metabolism's limitation string at `NR_Server_Metabolism.lua:35` is still true, but its reason ("NR_Server_Nutrients sorts after this file") is wrong since R2: the pipeline's `ORDER` sets the order. The string is shipped and pinned by `testing/tests/kernel/test_metabolism_shape.py:922`, so the rewording changes both.
- Stale sentences for the doc track: any page or comment saying an adapter appends to `P.onMinute`, or that Nutrients calls `EFF.minute` by hand. One is the comment at `NR_Server_Options.lua:88-91`.
- The Options append to `P.onMinute` (`NR_Server_Options.lua:92-110`) is dead: Options loads before Players, so the branch is never taken. Draft Task 2 Step 9 removes it.
- `testing/experiments/x151_records2.py:160` reads `NutritionRevamp.server.kinetics.lastMealCa`, which no longer exists. A driver is never edited after its run (CLAUDE.md § 5), so a re-run needs a new driver.
- The six zero-age sites (above).
- `IN.pendingAlc`, `IN.pendingCaf` and `FAST.lastInp` remain outside the context. `FAST.lastInp` leaves with the handler under Decision 1's (b) or (c).
- `NR_Server_Effects.lua:9` carries a 142-character comment line (R2 review); reflow it at the file's first edit.

## Performance (Plan 10b)

**Rule 6, as Angus restated it on 2026-10-07.** The rule's goal is no noticeable performance degradation or hitching, which Angus names the mod's primary point of potential failure. Per-tick work is the default suspect, not banned: it is admitted where a measurement proves it alleviates hitching rather than aggravating it. Every "rule 6" below that reads "no per-tick work" is read this way. A design is judged by its worst tick and how often that tick comes, at the 60-player design load. An architecture review pass and a further experiment plan follow, and they supersede Decision 6 (Plan 10c; Hitching, below, and Decision 6 as rewritten).

Plan 10b (`docs/superpowers/plans/2026-10-07-plan-10b-performance-spikes.md`) asked where the mod's server time goes, before Plan 11 is written. P1 profiled the slow minute by step in live play. P2 ran the minute every k game minutes offline against the golden trace. P3 measured what a design with no per-tick work gives up and pays (rule 6, Angus 2026-10-07: no per-tick work). P4, the caching of Java reads, was gated on P1 and did not trigger.
- The live run is `x231-20261007-111042` on the tree staged at `dc619d0`, with fixture `two`, Nutrition false and DayLength 1; its rows are #3387–#3394. P2's rows are #3395–#3399.
- The full sections, with every reading, are Appendix G (P1 and P3) and Appendix H (P2).
- Every live figure is n = 1. #3387–#3391 are cost readings, not behaviour; #3392–#3394 are behaviour.

### P1 — where the slow minute goes

`getTimestampMs` has 1 ms resolution, so each per-run figure is a step's total over its runs divided by the count. A step's total is a sum of 1 ms truncations, and its noise is the binomial sd given beside it (Appendix G).
- **A, in play:** 240 runs over 120 game minutes, both players, with meals, a walk and one player's sleep (#3387). The µs per run are the row's ms totals ÷ 240.
- **B, a fast clock:** `settimespeed 30`, 606 runs (#3389).
- **D2, the bench:** the bench minute at an unchanged world age, 1004 runs of the pipeline (#3390).
- **Marks:** † means indicative only, because the step's noise in A is above 10 % of its total. ‡ means below the 1 ms resolution in D2 (a truncation floor, not a cost).
- **Java columns:** `NR.call`s are counted at run time (#3388). Direct Java calls are a static count of the staged adapters.

| step | A µs/run | A share of the pipeline | A's total, ms ±1 sd | B µs/run | D2 µs/run | `NR.call`/run | direct Java/run |
|---|---|---|---|---|---|---|---|
| bus | 8.3 † | 0.5 % | 2 ±1.4 (70 %) | 11.6 | 1.0 ‡ | 0 | 1 |
| fast | 4.2 † | 0.3 % | 1 ±1.0 (100 %) | 3.3 | 1.0 ‡ | 0 | 0 |
| reconcile | 58.3 † | 3.7 % | 14 ±3.6 (26 %) | 44.6 | 11.0 (±30 %) | 5 | 0 |
| kinetics | 58.3 † | 3.7 % | 14 ±3.6 (26 %) | 107.3 | 2.0 ‡ | 1 | 1 |
| metabolism | 333.3 | 21.4 % | 80 ±7.3 (9 %) | 272.3 | 135.5 | 30 | 5 |
| **nutrients** | **800.0** | **51.3 %** | 192 ±6.2 (3 %) | 651.8 | 144.4 | 9 | 2 |
| effects | 120.8 † | 7.8 % | 29 ±5.0 (17 %) | 123.8 | 1.0 ‡ | 7 | 0 |
| strength | 70.8 † | 4.5 % | 17 ±4.0 (23 %) | 59.4 | 29.9 | 11 | 2 |
| weight | 70.8 † | 4.5 % | 17 ±4.0 (23 %) | 47.9 | 25.9 | 16 | 1 |
| the pipeline | **1558.3** | 100 % | 374 ±7.7 (2 %) | 1358.1 | 360.6 | 79 | 12 |
| `P.work` | 1583.3 | — | 380 | 1376.2 | 362.5 | 82 | — |

**What the table says.**
- **One in-play player-run costs about 1.56 ms** (#3387). That is about 4.1 times S2's 377 µs (#3354).
  - At an unchanged world age the same session read 430, 389 and 333 µs (#3390), which agrees with #3354.
  - So S2's figure was the shape of the work at a zero interval, where Nutrients returns early.
  - About 100 µs of A is this session's instrument overhead, which leaves about 3.9 times (arithmetic, Appendix G).
  - Reconcile, strength and weight make the same `NR.call` counts in A and D2 but cost more in A. So part of the rise is cold interleaved running against a warm bench loop, not a longer interval (inference).
- **Nutrients is half the minute (51.3 %), and its time is Lua, not Java:** it makes 9 `NR.call`s and 2 direct calls a run. Metabolism is the next fifth (21.4 %).
- **A fast clock did not raise the per-run cost.** B cost 1358 µs a run against A's 1558, though each B run integrated several game minutes (4.7 or 9.4, inference, #3389). A run's cost is therefore taken not to grow with its interval. This is an inference from B's flat cost, and it is the basis for dividing the minute by a round-robin period below.
- **S2's player budget (Appendix C, S2.4) under-counts the minute's cost by about 4×.** Plan 11 re-bases the minute's cost on 1583 µs (`P.work` in play), not 377.

**The Java share (P1 Step 4's estimate) and P4.**
- 79 of the pipeline's 91 Java calls a run go through `NR.call` (#3388), and 12 are direct (86.8 % and 13.2 %).
- The calibration is the handler less the pure step over the handler's 70 calls: (19.33 − 4.36) ÷ 70 = 0.214 µs a call (#3353, #3356). The whole pipeline's Java is then 91 × 0.214 = 19.5 µs of 1558 (1.25 %). The largest step share is weight's 5.1 %.
- An in-session upper bound comes from D2's reconcile step (5 `NR.call`s for 11.0 µs ±30 %). It gives at most 2.2 µs per `NR.call`-routed call, or about 2.9 µs at +1 sd.
  - At 2.2 µs, weight's Java is about half its 71 µs and strength's about 40 %.
  - At 2.9 µs both cross half.
  - Together the two steps are about 9 % of the minute.
- **P4: not triggered** (ruling 3). No step reaches half by the estimate P1 Step 4 names. At the upper bound, caching would save at most about 37 + 29 µs per player-run (about 49 + 37 at +1 sd), about 4 % of the minute.

### P2 — running the minute less often

- **The harness is sound.** The golden scenario re-run with the minute fired every k game minutes reproduces the golden byte for byte at k = 1. Ticking off-minutes changes nothing (#3395).
- **Under ruling 4's band no k from 2 to 30 is safe** (#3396):
  - k = 2, 5, 10, 15 and 30 leave 1130, 5543, 6092, 5906 and 6618 of about 9600 continuous leaves outside the band;
  - they have 5, 13, 26, 35 and 45 discrete mismatches.
- **k = 2 fails on g4's insulin band at its departure** (6 against 5) (#3397). With the first sight aligned it still leaves 489 leaves and a pending push. The flip is the 0.6 edge crossed a minute late, at minute 148, because minute 149 never runs before g4 leaves. That attribution is the P2 review's re-derivation and sits in no output (Appendix H).
- **The drift grows with k** (#3398):
  - the stamped stomach fill drifts up to 0.0052 at k = 2 and 0.25 at k = 30, against a range of 0.552;
  - the water pool drifts up to 30 g at k = 2 and 853 g at k = 30.
  - Most of the fat mass's and the water pool's drift is the first-sight and departure lag.
- **`fluids.sweatLmin` holds the step's litres**, so it reads k times a per-minute value. No reader uses it (#3399).
- **The verdict under a fairer band.** This is the P2 review's recomputation in Appendix H, not a register row. It aligns the first sight, uses an absolute band for constant leaves and takes the range per field.
  - **k = 2 is nearly safe.** It leaves 75 leaves in 19 fields with no band or grade flip. What remains is one-minute back-dating (the minute-50 drinks, g6's sleep onset, meal back-dating into the day close) and g4's push pending at departure.
  - **k = 5 is player-visible.** It leaves 1309 leaves in 154 fields and 8 discrete mismatches. g4's insulin band 6 is never shown before its departure. g6's caffeine band goes 0 → 1 four minutes early.
  - **k ≥ 15 misses a death.** g3 dies at minute 100 and respawns at minute 101, between fired minutes.
- **What a coarse minute does to the player** (inference from the code, unmeasured live):
  - HUNGER, read off the stomach fill stamped once a slow minute, holds for k minutes and then jumps.
  - A change reaches the client up to 2k − 1 game minutes late, against up to 1 now.
  - The moodles inherit that lag.
  - A joining player's record starts at the first fired minute, up to k − 1 minutes late.
  - Under Decision 1's (b) or (c), Decision 2's satiety scalar S would also step every k minutes (the coupling in Decision 2).
- **The saving is the minute ÷ k:** about 790 µs per player per game minute at k = 2 and 317 at k = 5, on P1's 1583 µs. This assumes a run integrating k minutes costs what a one-minute run costs, which #3389's flat cost supports (inference). P2's own 188.3 and 75.3 µs used S2's 377 µs and are superseded by this re-base.

**The dt-correctness findings for Plan 11** (the P2 review; Appendix H). No kernel assumes dt = 1: the fluids are dt-correct and the exponentials are exact. What grows with the step is the following:
- **Event back-dating.** A dose that lands between fired minutes is integrated from the step's start (`NR_Server_Nutrients.lua:371-376`, `:387`).
- **End-of-step sampling.** Asleep and moving are sampled at the step's end and applied to the whole step (`NR_Kernel_Acute.lua:448-451`).
- **Three biased integrators:**
  - `exEma` (`NR_Kernel_Acute.lua:529`) and `coldH` (`:544`) add the step's inflow undecayed, a bias of about +dtM/2. The exact form is r·τ·(1 − e^(−dt/τ)).
  - `cafMean` (`:251`) is explicit Euler, which is fine while dtH ≪ 168.
- **Two more:** `fluids.sweatLmin` is named per minute (#3399), and the bruise roll (`NR_Server_Effects.lua:440`) is one Bernoulli per step at `E.bruise × dtM`, which undercounts at large steps.

### P3 — what no per-tick work gives up and pays

**The once-a-minute PANIC write: a sawtooth.** It was measured under Overlay, with no stat hook registered.
- Vanilla's decay is linear and per game time: 0.17969 a tick at DayLength 1 and 0.030086 a tick at the DayLength 4 tick spacing. Both are **about 1.12 PANIC a game minute** (#3392, agreeing with #3116).
- The plan's 0.5 target was on the wrong scale (PANIC spans 0–100), so x231's amplitude is the clipped target. The follow-up run x232 measured a target of 10 (#3400): PANIC fell linearly, 0.17916 a tick at DayLength 1 and 0.030061 at the slow spacing, within #3392's range, and read 8.7444 to 8.9287 before each write at DayLength 1 (a loss of 1.0713 to 1.2556, mean 1.1260) and 8.8560 to 8.8921 at the slow spacing. The floor is the target less the fall per tick times the gap's ticks (#3402), so a 7-tick minute loses 1.2556, more than the 1.12 mean.
- The PANIC moodle thresholds are 6, 30, 65 and 80 (#2369). At a target of 10 the stat never went under 6 at either spacing; at 6.5 it went under 6 in every game minute at both (#3401). So a floor within about 1.26 above a threshold flickers one level once a game minute (inferred: the moodle itself was not read); a target of 10 did not (a target of 20 is clear of every threshold by the same arithmetic).
- The targets the earlier holds wrote sit outside all four windows: 10, 12.75 and 14.5 (#3101), and 19.25, 35 and 14.75 (#3082).
- Vanilla's panic rise from zombies in view adds on top between writes. No reading covers it.

**The once-a-minute TEMPERATURE write: it held** (#3393).
- At 37.5, 0.5 above the set point, the pre-write read settled at 37.47803–37.48045 at DayLength 1 (about 0.02 °C under) and 37.46046–37.46208 at the DayLength 4 tick spacing (0.04 under).
- The thermoregulator's core moved with it, from 36.2675 to 37.4277.
- This is the per-minute absolute write a no-per-tick design would use, not the takeover's own path. X81, whether the takeover's target holds, stays unmeasured.

**DayLength 4 on a live server.** `SandboxOptions:set` read back 4 but left the clock at 6.47 ticks a game minute for the next 10 s (#3394). So every "DayLength 4" reading above ran under `time.multiplier` 0.1674, which gives the same tick spacing. That the decay matches under the real option is inference.

**The burst and the round-robin** (#3391). The minute was driven from `EveryOneMinute` with the `OnTick` drain left on.
- **Burst:** both players in one event cost 1228.8 µs per player-run and 2457.6 µs per event, at most 6 ms.
- **Round-robin, m = 5:** one player an event cost 1721.3 µs per event, at most 4 ms. With two players each ran every second minute.
- **The tick spike** (extrapolation, labelled). This assumes a constant 1.23–1.58 ms per player-run for the burst, 1.23–1.72 ms for the round-robin (its measured 1721.3 µs per player-run, #3391) and a 100 ms tick:
  - a full burst costs 24.6–31.7 ms per event at 20 players and 49–63 ms at 40, once a game minute;
  - a round-robin at m = 5 runs ceil(N / 5) players an event, 4.9–6.9 ms at 20 players and 9.8–13.8 ms at 40, on the round-robin's own 1.23–1.72 ms basis.
- **Under a fast clock every tick carries one minute event** (#3348). So a burst there runs every player every tick, the shape S2 corrected in draft ruling 2 (inference). A round-robin bounds it at ceil(N / m) players a tick.

**The all-in cost with no per-tick work**, per player per game minute (arithmetic on the readings; Appendix G):
- the writer, Lua side, is 11 µs (#3373);
- vanilla's updaters, which run again when no hook is registered, are 1.0–10.6 µs per update (#3386) × 6.27 ticks (#3346) or × 37.46 (#3347);
- the minute is 1583 µs (#3387) ÷ the round-robin period m.

| design | DayLength 1 | DayLength 4 |
|---|---|---|
| no per-tick work, m = 1 (the burst) | 1600–1660 µs | 1631–1991 µs |
| no per-tick work, round-robin m = 2 (arithmetic, as above) | 809–869 µs | 840–1200 µs |
| no per-tick work, round-robin m = 5 | 334–394 µs | 365–725 µs |
| the takeover, for the record: 19.33 µs a tick (#3353) × the ticks, plus the minute | 121 + 1583 = 1704 µs | 724 + 1583 = 2307 µs |

So rule 6's design costs less than the takeover at both day lengths. Its own risk is the burst, which the round-robin spreads. Under the round-robin, each player runs every m game minutes, which is P2's coarse minute at k = m.

### Ranked performance refactors for Plan 11

Each item names its reading and its expected saving per player per game minute, and goes no further than that reading. The list is ordered by that saving, largest first. Item 4 is required by rule 6 whatever its saving.

**Re-ranked by Plan 10c.** The order below is superseded by Hitching's "Ranked refactors for Plan 11": heal once before the step first, then the budgeted scheduler, then send staggering, then the store's move. Item 4 (the round-robin drain) is superseded by Decision 6 (b).
1. **The Nutrients step's Lua** (saving up to 800 µs).
   - The reading: 192 ±6.2 ms (3 %), 51.3 % of the pipeline, of the pipeline's 374 ms in play (#3387). It is also 395 of 823 ms under a fast clock (#3389) and 145 of 362 ms at a zero interval (#3390).
   - Its Java is 9 `NR.call`s and 2 direct calls a run (#3388): under 0.3 % by the estimate, and about 24 µs (11 calls × 2.2) at the upper bound.
   - The saving: at most its 800 µs at m = 1, or 800 ÷ m under a round-robin. No reading resolves where inside the step the time goes, so Plan 11's first performance task is a profile below the step, before any rewrite. The x231 instruments (the per-step timers, the call counter, the hold and the burst; sha256 c20f645d…0f8d, as perf.json's `meta` records) are kept at `testing/spikes/instruments/x231_NR_Server_Bench.lua`; they are appended to a staged copy's bench file, never to `mod/`.
   - Metabolism, 333 µs (21.4 %, #3387), is next by the same reading. It carries more Java (30 `NR.call`s and 5 direct, about 77 µs at the upper bound).
2. **A coarse minute at k = 2** (a round-robin of m = 2; saving about 790 µs), **conditional: it holds only if Angus adopts the fairer band of Appendix H.** Under ruling 4's band k = 2 fails (#3396, #3397). It also needs first-sight alignment and event landing, and event landing at its own minute was never run.
   - The reading: #3396–#3398, and the P2 review's fairer-band recomputation (Appendix H). Under the fairer band, k = 2 leaves one-minute back-dating and the first-sight lag, with no band or grade flip.
   - First-sight alignment means a joining player's first minute runs at the join, not at the next fired minute. Event landing means a dose is integrated from its own minute, not back-dated to the step's start.
   - The saving: about 790 µs, the minute ÷ 2 (arithmetic on #3387; flat cost per #3389, inference). That takes the all-in cost from 1600–1660 to 809–869 µs at DayLength 1, and the spike to 12.3–17.2 ms at 20 players (extrapolation on the round-robin's 1.23–1.72 ms basis, #3391).
   - k = 5 is not supported, because it is player-visible (#3396; Appendix H). k ≥ 15 misses a death.
3. **Caching Java reads: not supported** (saving at most about 66 µs).
   - The reading: #3388 with P1 Step 4's estimate. 0.214 µs a call gives 19.5 µs of 1558 (1.25 %).
   - The saving: at most about 66 µs per player-run at the 2.2 µs upper bound, where weight and strength reach about half (about 86 µs at +1 sd). That is about 4 % of the minute. P4 was not triggered.
4. **A round-robin `EveryOneMinute` drain in place of the `OnTick` drain** (rule 6; saving zero on average, but required by rule 6).
   - The reading: #3391, with #3389's flat per-run cost and #3348's one event a tick under a fast clock.
   - The saving at m = 1 is none on average: the 1583 µs moves from the tick to the event.
   - What it buys is no per-tick work and a bounded spike: ceil(N / m) players an event instead of a 24.6–31.7 ms burst at 20 players (extrapolation).
   - The period m is a coarse minute per player (item 2).
5. **The three dt biases: `exEma`, `coldH` and `cafMean`** (Appendix H), with the bruise roll and `fluids.sweatLmin` (#3399) beside them (saving zero).
   - The saving: none; this is correctness.
   - It is a precondition of item 2. It already matters under a fast clock, where one run integrates several game minutes (#3389) (inference).

### The 60-player design load (Angus, 2026-10-07)

Angus set the design load at a 60-player average. Every figure below is arithmetic on the measured per-player costs (two players measured; linear extrapolation, unmeasured at 60). It assumes a 100 ms tick (10 ticks a second), a game minute of 6.27 ticks at DayLength 1 and 37.46 at DayLength 4 (#3346, #3347), and these per-player-run costs:
- 1.583 ms for one player's minute in play: `P.work`'s 380 ms over 240 runs, around the pipeline's 1558.33 µs a run (#3387);
- 1.23 to 1.58 ms on the burst basis: the burst's 1228.8 µs a player-run (#3391) to `P.work`'s 1.583 (#3387);
- 1.23 to 1.72 ms on the round-robin basis (#3391).

**The average load is affordable.** 60 players' minutes cost about 95 ms a game minute: about 15 % of the server's time at DayLength 1 and about 2.5 % at DayLength 4. The writer (#3373) and vanilla's updaters (#3386) add under 1 % at 60 players.

**The spike is not.** Under rule 6 the minute's work runs inside one `EveryOneMinute` event, and one event fires at most once a tick (#3348). So it cannot be spread across the ticks of a minute.

| round-robin period m | players a event | the event's cost (ms) | average a game minute (ms) | drift (P2) |
|---|---|---|---|---|
| 1 | 60 | 73.7 to 103.3 | 95 | exact |
| 2 | 30 | 36.9 to 51.6 | 47.5 | unsafe under ruling 4; clean only under Appendix H's fairer band |
| 5 | 12 | 14.8 to 20.6 | 19 | player-visible (#3396) |
| 10 | 6 | 7.4 to 10.3 | 9.5 | 26 discrete mismatches (#3396) |

- At m = 1 one tick in every game minute costs about a whole tick's budget before vanilla's own work. At DayLength 1 that is once every 0.63 s.
- No period that the drift study passes brings the event under a quarter of a tick.

**What closing the gap needs.**
- **A cheaper minute.**
  - To keep the event under 10 ms, a player-run must cost about 0.167 ms at m = 1, or 0.333 ms at m = 2: 9.5 or 4.75 times cheaper than today.
  - Under 25 ms, it must cost 0.417 ms or 0.833 ms.
  - Deleting the Nutrients step outright leaves 0.783 ms, so the Nutrients step alone cannot close the gap. The whole pipeline must get cheaper.
- **Or spreading the minute across ticks.**
  - The per-tick drain spreads it: 10 players a tick at DayLength 1 is 12.3 to 15.8 ms every tick, and 2 at DayLength 4 is 2.5 to 3.2 ms. That is a flat load with no spike.
  - The drain does no simulation per tick; it only schedules the minute's work.
  - Rule 6 as written excludes it. Whether a budgeted scheduler counts as the per-tick anti-pattern is Angus's call (a new decision, 6, below).
  - Plan 10c measured it with 58 ghost records beside two players. A 15 ms budget held the frame within 13 ms of idle at the 99th percentile, where the burst added 43 to 56 ms. At N = 60 the burst's minute frame read 50 ms of busy at the median and 88 at the worst, below this table's 73.7 to 103.3 ms arithmetic (#3472, #3489, #3490; Decision 6).

**What it changes in the ranked list.** At 60 players, item 1 (the Nutrients step) becomes a cost target for the whole pipeline: about 0.33 ms a player-run, against 1.583 today. Plan 11's first performance task, the profile below the step, is a blocker for a 60-player release, not insurance. A live run at 20 or more players (Task 13) is needed before any 60-player figure is trusted.

## Hitching (Plan 10c)

Plan 10c (`docs/superpowers/plans/2026-10-07-plan-10c-hitching-experiments.md`) asked where the mod can make a player notice a hitch at the 60-player design load, and which scheduler keeps the worst server frame lowest, before Plan 11 is written. It changed nothing under `mod/`: every instrument and prototype ran in a staged copy or under `testing/spikes/`.
- **Rows.** H0 (the frame instrument and the ghost load) #3403–#3410; H1 (offline prototypes) #3411–#3416; H6 (the global store) #3417–#3422; Task D's durable record #3423–#3456; H2 (sub-step and burst-source costs, runs `x242` and `x242b`) #3457–#3470; H3 (the scheduler shoot-out, four `x243` sessions) #3471–#3484; H4 (does a player notice, three `x244` sessions) #3485–#3493; H5 (the engine's fake clients, one `x245` session) #3494–#3496; the three new lessons rules #3497–#3499. The H1–H6 task memos are Appendices J–O, verbatim, and keep their own provisional ids, which each appendix's first line maps: a figure in this section that rests on a memo and on no row names its appendix, and a figure computed here is labelled (arithmetic).
- **The durable record.** Every finding below that a future change needs is also on `docs/platform/performance.md` (the frame, the scheduling primitives, the measured costs, the shoot-out, how to measure) and in `docs/platform/lessons.md`'s rules. This section is the decision record; those pages are what a reader cites.
- **Scope.** Every live figure is one session on one host, fixture `two`, Nutrition false. Ghost records are cost, never behaviour. Both clients ran on the server's host.

### The frame instrument, and how far it can be trusted

- **Two readings of a frame.** The harness's `tick.ring` stamps each frame at `OnTickEvenPaused` and `OnTick`. It gives the frame's **busy** time (start to the end of `OnTick`), the **start-to-start** period and the **end-to-end** period (a frame's start to the next frame's end). `perf.local` reads the engine's own per-window `max-update-period`, the hitch reading.
  - The two agree within 2 ms at the 99th percentile, idle and under a burst (#3403).
  - The engine's `avg-update-period` is no mean, so no driver reads it (#3409).
  - The minute's work runs between the frame's `OnTickEvenPaused` and its `OnTick` (#3410).
  - Idle, with two players: busy p50 1, p99 9, max 13 ms; start-to-start p50 100 ms (#3404).
- **The ghost load.** `ghost.load <N>` runs N minus the online count of ghost records through the real pipeline against the real players, under a named scheduler.
  - Over forty interleaved pairs, a fed ghost's minute cost 0.978 of a real player's and an unfed one 0.778 (#3466). Forty pairs at the 1 ms clock resolve that ratio only coarsely, so H3 and H4 read the ghosts' cost off `ghost.stats`' batch totals over whole arms (0.762–1.107 ms a run across the arms: #3472, #3473, #3476, #3478, #3491).
  - So N = 60 is a cost stand-in for about 44 to 60 players' minutes (inference). It carries none of vanilla's own per-player work, which H5 could not read: the engine's fake clients were kicked at join (#3494).
- **What it cannot resolve.**
  - The Lua clock is 1 ms, so every Lua figure is a total over many runs with its count.
  - Two no-load arms of one session drifted from 1.873 to 1.256 ms of busy a frame (#3483). So a total compared across arms on busy over idle carries about 0.6 ms a frame of drift. The drift-immune total is the ghosts' own batch-timed ms a minute event (#3479, #3491; rule #3499).
- **GC is not a factor.** ZGC pauses inside the measured arms were at most 0.695 ms over four sessions, and every allocation stall fell during boot, before any arm (#3484; #3408).

### Where the minute's time goes, and the refactor targets (H2)

Run `x242` (phases A and B, by ruling H2-1) and run `x242b` (phases C to F), on the staged copy with sub-block timers.
- **The live minute** is 356 ms over 244 runs with the timers on, 1.459 ms a run (#3457). By step: nutrients 173, metabolism 79, effects 38, kinetics 18, strength 15, weight 13, reconcile 9, bus 2, fast 0 ms.
  - Timer overhead: the profiled bench's typical run is 1.080× the unprofiled one (about ±0.04; the `x242b` guide), and the un-bracketed remainder bounds the cost outside the brackets at about 5.6 % (the `x242` guide; both guides are in `docs/reference/artifacts.md`, and Appendix K).
- **The heals are the top block live too.** The Nutrients heal pair is the two largest sub-blocks: `heal.pre` 62 and `heal.post` 39 ms, 28.4 % of the minute. The seven heal passes together are 143 ms, 40.2 % (#3458).
  - Offline the same pair is 38.4 % of the C-Lua pipeline (#3411). The shares are not like-for-like: the live minute holds Java-interop blocks lupa stubs, the scenarios differ, and about 30 bracket pairs were on.
- **The 15 %-of-step targets** (#3459): `nutrients/heal.pre`, `nutrients/heal.post` and `nutrients/records`; `metabolism/readActivity` (9.0 % of the minute, the next live target after the heals) and `metabolism/heal.post`. The effects and strength targets rest on 5–9 ms totals, at the noise.
- **What is not a burst source** at the plan's rules:
  - a day close: 0.901 of the typical minute over 1000 bench runs, and a seven-day catch-up no costlier (#3462); in play at N = 60 the burst's first minute frame after 07:00 read 1.34× the minute p50, not a separate burst (#3481);
  - first sight, per joiner: 0.861 ms, a floor (#3463); sixty joiners in one frame would cost at least 51.7 ms (arithmetic), so a mass join is open;
  - a deficient player: no burst at 1 ms resolution, the onset unmeasured (#3461);
  - the client tooltip: 7–18 µs a call on an unchanged item (#3465).
- **The send is one.** One mirror send of the 138-key payload costs about 0.1 ms, so 60 in one frame are about 6.12 ms (#3464). That is over the plan's 5 ms jitter rule. It is the per-send cost times 60, not a 60-player reading. Rule #3498 spreads the pushes.

### The prototypes (H1, offline)

- **Heal once, before the step, saves about 28 % and keeps the trace.** It reproduces the golden byte for byte and saves 27.7 % of the pipeline's C-Lua time (IQR 23.9–28.8), and it keeps every input-NaN heal (#3413).
  - A probe-free re-timing put all seven heals at 55.7 % and the Nutrients pair at 41.6 % (the H1 review's probe-free re-timing; Appendix J).
  - Its cost: a NaN the step's own arithmetic makes may sit in the record until the next minute (#3413). Keep a post-step guard where a step's NaN would leak in the same minute (Metabolism's masses at least), and enumerate the cross-step reads before settling it (Appendix J).
  - Healing once **after** the step changes the trace (#3412): a finding, not a fix (ruling 4).
- **Hoisted constants** save nothing measurable (0.3 %, #3414).
- **A slow tier for the records** (K = 5, the rebuild check kept every minute) takes about 7.2 % off the average minute, not the worst player-run (#3415, #3416).

### The global store (H6 and H2b)

- **Size.** A record is about 10.8 KB in the save's format (#3422); live, each seeded copy added 10877 bytes to `global_mod_data.bin` (#3468). So 1 MB is reached at about 92 records (arithmetic, 1,000,000 / 10877), 500 records are about 5.4 MB, and 2000 about 21.8 MB. An inputs-only record is only 19 % smaller.
- **The save is a hitch source.** It runs on the main loop for the console save and the autosave (#3420). The first save at a new size pays far more than the next (#3467):

| seeded records | first save (ms) | second save (ms) |
|---|---|---|
| 0 | 11 | 9 |
| 100 | 22 | 16 |
| 500 | 153 | 50 |
| 2000 | 2770 | 193 |

  - At 2000 the first save made a 2990 ms server frame and logged `Pausing clients…`.
  - At 500 the second save adds 41 ms over 0, so H6's 25 ms rule fires.
  - That the first save at a size pays the buffer's growth restarts is inference (#3421). So the save that stalls is the first after the store passes its last high-water mark, an autosave after a long uptime among them.
- **The request leak is confirmed live.** Any logged-in client can request the store by name, and a mod cannot refuse (#3417, #3418).
  - Live, a release client received the whole table at 2 and 60 records (#3469).
  - At 500 records the request failed on both sides, and the client kept its session (#3470). The truncated send and the client's parse rejection are confirmed (#3419). The `IllegalMonitorStateException` H6 inferred did not appear.
  - The request's frame cost at 60 records was within the 4–5 ms idle jitter (#3469). Above 60 and repeated, it is unmeasured.
- **Consequence:** the store leaves global modData in Plan 11 (Decision 3).

### The scheduler shoot-out (H3 and H4): a headroom reading

N = 60 means 58 fed ghost records beside the two real players, who stayed on the mod's own drain. Adds are over the same session's idle arm. The p99 add is on the ring's end-to-end period (about 1020 frames an arm); the max add is on the engine's per-window longest frame (about 95 windows an arm). Starvation is ghost-minutes not run within their period.

| scheduler | spacing | busy p50 / max (ms) | longest window (ms) | adds p99 / max (ms) | starved | rows |
|---|---|---|---|---|---|---|
| idle | DayLength 1 | 2 / 13 | 115 | — | — | #3471 |
| burst (one event) | DayLength 1 | 50 / 88, minute frames | 188 | +62 / +73 | — | #3472 |
| burst, six draws | DayLength 1 | — | 164–176 | +46 to +56 / +48 to +61 | — | #3489 |
| round-robin of two | DayLength 1 | 31 / 48, minute frames | 146 | +32 / +31 | none; each ghost every second minute by design | #3475 |
| ceil(N / ticks) a tick (the draft) | DayLength 1 | 10 / 22 | 119 | — / +4 | 176 over 167 events | #3478 |
| 5 ms budget | DayLength 1 | — / 43 | 141 | — / +26 | every event | #3477 |
| 10 ms budget | DayLength 1 | 10 / 26 | 124 | +5 / +9 | 207 over 166 (34 events), at most one event late | #3476 |
| 15 ms budget | DayLength 1 | 11 / 31 | 134 | +13 / +19 | none | #3477 |
| 15 ms budget, six draws | DayLength 1 | — | 127–139 | +12 to +13 / +11 to +25 | none | #3489 |
| burst | 37 ticks | 48 / 60, minute frames | 161 | +44 / +42 | — | #3473 |
| burst, three draws | 37 ticks | — | 153–173 | +43 to +46 / +47 to +67 | — | #3490 |
| 15 ms budget, three draws | 37 ticks | — | 123 | +12 to +13 / +17 | none | #3490 |
| the shipped 1.0.0 drain (mirrored) | DayLength 1 | — | — | — | 53 of 58 never ran | #3482 |

- **The headroom framing.** The loop's start-to-start cadence held under both the burst and the budget at N = 60 on this host (#3486).
  - The one exception is a single unexplained 136 ms start-to-start period in `x244a`'s burst2; the period held at 103–106 ms in every other `x244` arm.
  - In the `x244` sessions the burst's busy, 46–51 ms at the minute-frame median and 56–77 ms at the frame max, fits inside the 100 ms period; so did the 88 ms frame max of `x243a` (#3472).
  - So the 153–188 ms "worst frames" are end-to-end periods: the burst moves the frame's end, not the loop's cadence.
  - The burst's busy is linear in N, 18, 32 and 50 ms at the median at N = 20, 40 and 60 (#3474). Extrapolated linearly (inference), the worst minute frame at N = 60, 88 ms of busy (#3472), crosses the 100 ms period near N = 68–74 on this host, and the median minute frame, about 50 ms, near N = 120. The H4 review's estimate of N = 85–95 sits inside the 68–107 that the frame maxima of 56–88 ms across the H3 and H4 sessions give (arithmetic). None of these counts vanilla's own per-player load at 60 real players, which is unmeasured: H5's fake clients could not join (#3494).
  - So (b) buys headroom for more players, heavier minutes and slower hosts. It is not relief from a stall players see today at 60 on this host.
- **A budget sized to the minute's work keeps the worst frame flat.**
  - A 15 ms budget added 12–13 ms at p99 in all nine draws at both spacings and starved no ghost, against the burst's 43–56 (#3489, #3490).
  - A 10 ms budget runs at the margin of the minute's work. It served 56.75 of 58 a minute event, each ghost at most one event late: bounded lateness, not loss (#3476).
  - A 5 ms budget starved every event (#3477).
  - The drafted ceil(N / ticks) spread starved at N = 40 and 60 at DayLength 1, because its count comes from the last minute's 6 or 7 ticks (#3478, inference).
  - Rule #3497 states it: a per-tick cap with headroom over the minute's work divided by the minute's ticks.
- **The total.** On the drift-immune measure, the 15 ms budget ran 1.053, 1.061 and 1.060× the burst's ghost ms a minute event in three sessions (#3491). That settles H3's 1.22× for the 10 ms budget at 37 ticks as drift: its ghost ms a minute event read 1.046× (#3479). The 5–6 % excess is not resolved from the spread between arms.
- **The empty-queue check is not resolved** (#3483).
  - The A/B (about 3000 frames a side, none, empty, empty, none) reads −0.052 ms a frame by the totals and −0.077 by the quiet frames. The two pairs read −0.238 and +0.133, against about 0.6 ms a frame of drift.
  - In A-B-B-A order the arms read 1.873, 1.635, 1.389 and 1.256 ms a frame, the empty arms net of their ghost ms. A fit of a linear drift plus an empty-side offset gives −0.053 ms a frame.
  - **Caveat:** the fit's largest residual, 0.018, is the curvature a one-degree-of-freedom fit leaves, not an error bar. The offset's standard error is about 0.03 ms. So the reading weakly supports the ≤ 0.1 ms bound and no more.
- **A fast clock.** Under `settimespeed 30` every frame is a minute frame. The burst then ran 58 ghosts every frame at busy up to 76 ms, yet the end-to-end period stayed at 123 ms at p99. A 10 ms budget there starved 29715 ghost-minutes over 623 events, up to 42.8 game minutes stale (#3480). So the budget must scale with the clock, or run everything when every frame is a minute frame (inference; for Plan 11).
- **The starvation bug is confirmed live** (ruling 3). The shipped drain, mirrored at N = 60, ran 4.26 ghost minutes a minute event, dropped 6180 queued ghost-minutes and left 53 of 58 ghosts never run, the longest 115.7 game minutes stale (#3482). #3444's rule and #3439 carry this as a status note.

### Does a player notice? (H4)

Session `x244c` put admin 1.58 tiles from bob (arithmetic off #3493's coordinates). Fixture `two` spawns them about 248 tiles apart, and an RCON `teleport` moves nobody; the debug menu's `/teleportto` through `lua.call` does (#3493).
- **The clients' own frames** never reached 100 ms, at most 32 ms under the burst (#3486).
- **The other player's motion** showed no minute-aligned gap above chance. Gaps of 100 ms or more lined up with a minute frame 32–43 times an arm under the burst against 30–41 in a shifted control, and 35–44 against 28–38 under the 15 ms budget (#3486).
- **The packet-stamp test was blind** (#3487, #3488).
  - A remote player's `getLastRemoteUpdate()` is stamped at each player packet (#3485). It advanced every 201–400 ms at the median.
  - Every stamp gap was at least 167 ms, so the 100 ms rule counted every gap, and the windows cover 32–37 % of the time. A stamp test cannot see a frame shorter than the packet cadence.
  - The near-player stamps stayed within one or two client frames of the 200 ms grid in every arm, burst frames included.
- **The supported reading:** at N = 60 on loopback, with no zombies, the burst has no visible effect on another player's updates (#3488). The plan's prediction, evidence for (b), was falsified.
- **What it does not cover:**
  - a player's own actions on server-owned state (timed-action completion, container transfers, hits, eating), which wait on the frame;
  - real network latency, jitter and loss;
  - zombies;
  - more than one session per geometry.
- **Ruling H4-2 (restated by the H4 review): ruling 2's thresholds stay as written.** H4 could not have loosened them: its stamp test was blind at the 200–400 ms packet cadence, and no tick started late in any arm (one unexplained 136 ms period in x244a aside), so there was no stall to see. Hitching is the mod's primary failure risk (Angus). Cost if wrong: a tighter budget than needed, which costs nothing in hitching.

### The fake clients (H5)

Run `x245`: one server-only session with PZTestKit only, no NutritionRevamp and no game client, the server on port 16261 with `Open=true` and `DoLuaChecksum=false`, and the fake JVM run read-only from the install (Appendix N).
- **Not reachable on 42.20.4.** The engine's `FakeClientManager` connects, logs in and passes the login queue, then the server kicks it at `player-connect` with `UI_LoadPlayerProfileError`. Over about five minutes its one connected client, `Client1`, was allowed to join and kicked 23 times, and no fake player was ever online (#3494).
- **Why.** The server kicks a joining player for whom it finds no saved character, and the fake client sends `PlayerConnect` straight after the login queue with no character of its own (#3495).
- **One JVM, one connection.** At each connect round all but one of the clients due failed, and the server only ever saw `Client1`, so one JVM gave one connected client (inference). That JVM held 133.3–180.9 MB (#3496), so sixty JVMs would need about 8–11 GB (arithmetic).
- **What it leaves unmeasured.** Vanilla's own frame at each N, the denominator E7 asked for, and H4's burst and budget15 arms on real players: neither ran. With nobody online, the idle server-only baseline read busy p99 3–4 ms and an end-to-end period p99 of 105 ms, with no client and no mod, so it is no per-player reading (Appendix N).
- **What would make it reachable** (not tried; a new task and a new session): a saved character for each fake username before it connects, and one JVM per client with `-id=<n>` (Appendix N). Until then E7 stays Angus's to supply.

### Ranked refactors for Plan 11 (re-ranked by Plan 10c)

This supersedes the order of the Plan 10b list above. Each item names its reading. The list ranks by expected saving, and the budgeted scheduler (item 2) is a correctness fix on top: it fixes the 1.0.0 starvation, confirmed live by #3482.
1. **Heal once, before the step.**
   - The reading: offline it saves 27.7 % of the pipeline and keeps the golden trace byte for byte (#3413). Live the heals are the top block: the Nutrients pair is 28.4 % of the minute and the seven heals 40.2 % (#3458).
   - The saving: about a quarter of the minute, about 0.4 ms a player-run on the profiled 1.459 ms (arithmetic), if the offline share holds live (unpriced).
   - Conditions: a post-step guard where a step's NaN would leak in the same minute, and the cross-step reads enumerated first (#3413). The trace is unchanged, so no re-record.
   - Then the remaining heal walk (cheaper finiteness checks) and `metabolism/readActivity` (9.0 % of the live minute, #3458).
2. **The budgeted per-tick scheduler (Decision 6 (b)).**
   - It fixes the 1.0.0 drain's starvation bug: 53 of 58 never ran live at N = 60 (#3482; Re-basing, Task 2).
   - It keeps the worst frame flat: +12 to +13 ms at p99 against the burst's +43 to +56 (#3489, #3490).
   - Its shape: a queue that carries unserved players forward, drained on `OnTick` under a budget sized to the minute's work (15 ms at 60 on this host; a minute-sized adaptive budget is Plan 11's to build and measure), plus a fast-clock rule (#3480).
   - The saving on average: none (1.053–1.061× the burst's total, #3491). What it buys is headroom.
3. **Stagger the per-player sends.** Sixty mirror sends in one frame are about 6.12 ms (#3464). The push gap's wall-time phase lock keeps players first seen together pushing in the same minute (#3456), so the push needs its own per-player offset or a share of the spread queue. Rule #3498.
4. **Move the store out of global modData (Decision 3).** It is a privacy and griefing blocker (#3417–#3419, #3469, #3470) and a save hitch: 2770 ms on the first save at 2000 records, and the second save at 500 added 41 ms over the second at 0 (#3467). The recommended home is a server-local file through `getFileWriter`.

Below these, the Plan 10b list's other items stand:
- the slow tier for the records (K = 5, about 7.2 % offline, #3415, #3416);
- a coarse minute (conditional on the fairer band, and no longer needed for the spike once (b) is adopted);
- caching Java reads (not supported);
- the dt biases (correctness).

Plan 10b's item 4, the `EveryOneMinute` round-robin drain, is superseded by item 2: Decision 6's (c) is excluded.

## Angus's decisions

### Decisions taken (Angus, 2026-10-08)

Angus answered the six decisions on 2026-10-08, in a brainstorming pass that set out each option's trade-offs. Plan 11 is written from these answers and the sections below.

1. **The takeover fork: (c), the once-a-minute hybrid.**
   - Vanilla's hunger, thirst and fatigue rise rates are zeroed at the server's `OnGameBoot`, and the mod writes those stats once per player-minute.
   - The same pass writes PANIC and TEMPERATURE.
   - There is no per-tick hook.
   - Angus accepts three costs: a restart-only mode; a writer outage that stops hunger rather than falling back to vanilla; and other mods reading zero rates.
   - The writes land in each player's own minute run, which Decision 6 schedules.
2. **Hunger feel: (c), vanilla's hunger plus the energy term, with bulk scaling a meal's relief, at a modest β of 0.25 to 0.5.**
   - It keeps (a)'s vanilla calibration on a normal menu, which is identical to (a) for β up to 0.5, and a bulky meal sates more, the realism (a) lacks.
   - Plan 11 picks β within 0.25 to 0.5 against Appendix D's light-menu reading. At β 0.25, the light menu is less hungry than vanilla for 111 minutes a day.
   - The satiety scalar's migration rides on the store's move (Decision 3).
   - Under Decision 1 the scalar steps once a player-minute, so the match is within a minute's lag.
3. **The store and pruning.**
   - The store leaves global modData for a server-local file, read with `getFileReader` and written with `getFileWriter`. This is the privacy and griefing blocker.
   - Pruning is on by default. It is measured in **real time** since a player was last seen, **30 days**, and operators can change it as a sandbox option.
   - Real time, not game days, because game days pass at each server's own speed.
   - A player away longer returns with a fresh nutrient record; the vanilla character is untouched.
4. **Internal ids in shipped comments: keep.** They are the maintainers' route from code to evidence.
5. **The neighbour mods: subscribe before Plan 11.**
   - Angus subscribed on 2026-10-08 to Nutrition Makes Sense (3690404044), StatsAPI (2997722072), Stat Tweaks Lib (3415375593) and Tooltiplib (3694097672).
   - ApocalipseBR - Nutrition Sync Fix (3736275816) no longer exists on the Workshop, so its open questions close as unavailable, not unread.
   - Plan 11 opens with a read of the four. StatsAPI and Stat Tweaks Lib adjust the same stats Decision 1 zeroes the rates of, so the zeroed-rates build gets a guard or a compatibility note from that read.
   - The files were not yet on disk when the decisions were recorded. The read waits on Steam's download.
6. **Spreading the minute: (b), a budgeted `OnTick` queue with an adaptive budget.**
   - The minute event queues every player, and `OnTick` drains the queue under a per-tick budget, carrying the unserved forward.
   - The budget is the measured per-player run cost times the queue, divided by the minute's ticks, plus headroom. Its floor is 15 ms, the smallest fixed cap that starved none at 60 on this host, and it scales with a fast clock.
   - Bundled with it:
     - per-player sends are staggered across the minute;
     - the 07:00 day close and first sight go through the same queue;
     - the harness gains a route that feeds ghost records into the mod's own queue, so the mod's scheduler is measured against `budget15` at both spacings.
   - Open items 1 to 9 below are Plan 11's scheduler task.

7. **What the neighbour reads add to Plan 11** (Angus, 2026-10-08).
   - **Source.** Four reads ran on 2026-10-08, kept in the workspace `.superpowers/sdd/2026-10-08-neighbour-reads/`. The lens was long-term operability, maintainability, control of our mod, and accuracy or realism.
   - **The compatibility picture.**
     - StatsAPI is a Build 41 mod that 42.20.4 never discovers, so it is inert.
     - Stat Tweaks Lib loads but raises on every client update on 42.20.4, and never runs on a dedicated server.
     - Tooltiplib chains cleanly with our tooltip.
     - Nutrition Makes Sense is incompatible: write wars over HUNGER, calories and weight, each mod booking the other's calorie writes as meals, and overrides of 438 shared food items.
   - **Into Plan 11:**
     1. **A jar read of how a food's HungerChange drives half and quarter eating and recipe ingredients**, before Decision 2's bulk scaling. The scaling acts on the applied hunger drop, not on the item value.
     2. **Vanilla's rates saved before they are zeroed, and exposed read-only**, so nothing that reads them gets zero.
     3. **A boot-time warning to the operator when Nutrition Makes Sense is installed.** The mod warns and does not refuse to run.
     4. **Two tooltip guards:** stop retrying after repeated errors, and fall back to the saved original on re-entry.
     5. **Nutrition conserved through recipes that split food.**
        - First, measure which recipes break conservation and by how much.
        - Then fix the material ones server-side, where the eat is booked, driven by data rather than a hand-kept recipe list.
        - The client tooltip may still show the unscaled values in multiplayer, because a Lua item write does not reach the client (#1074). Document that limit.
   - **Left out, with the reason:**
     - **A public rate-source API for other mods.** It would be a permanent contract that lets outside code change our model, and it has no consumer today. Add it when one appears.
     - **Recovery fields that yield to other mods' edits.** Another mod could silently switch off our malnutrition effects. Our effects stay authoritative, the behaviour goes in the compatibility notes, and a later conflict is answered by applying our factor on top of the other mod's value.
     - **Sending player state only when it changes.** More state, stale-detection and a re-request spam vector, to save bandwidth we have not shown we need. The fixed staggered cadence stays.
     - **The UX ideas:** display modes, time hints, a kg/week trend and a moodle that names its cause. They go to a later plan.
   - **The durable record.** The four mods' pages and catalog rows, the compatibility notes, and two new jar facts go into the reference library with register rows (Plan 11's first task):
     - a dedicated server never runs `client/` Lua;
     - the discovery rule that hides a mod with no `common/` or version folder.

### 1. The takeover fork

**The design target is no per-tick work** (rule 6, Angus 2026-10-07; the lessons rule against simulation on `OnTick`, #3423, #1080). Plan 10b measured the fork under that target (Performance, above). Under the restated rule 6 the takeover stays withdrawn, because a per-tick hook is not measured to reduce hitching. The options below are lettered as before, so the cross-references in Decision 2 and the appendices still resolve.

**(a) Keep the takeover — withdrawn.**
- **Why it leaves the table:** `Hook.CalculateStats` runs once per player per tick by nature, so it cannot meet rule 6. Plan 10b measured no takeover variant.
- **Its measured cost, for the record:** the handler is 19.33 µs per player per tick (#3353). That makes 121 µs per player per game minute at DayLength 1 and 724 µs at DayLength 4 (#3346, #3347). With the in-play minute of 1583 µs (#3387), the all-in cost is 121 + 1583 = 1704 µs at DayLength 1 and 724 + 1583 = 2307 µs at DayLength 4.
- **What leaves with it:**
  - the live mode switch (#3357);
  - the failover to vanilla's own update;
  - PANIC held every tick inside the hook;
  - other mods reading the real `ZomboidGlobals` rates (#2564);
  - draft Task 3 and draft rulings 6 and 7.

**(b) Zeroed rates with per-minute writes, and no PANIC or TEMPERATURE write.**
- Cost: the writer's 11 µs (#3373), plus vanilla's updaters at 6–66 µs per player per game minute at DayLength 1 or 37–397 µs at DayLength 4 (#3386), plus the minute. The all-in table is below.
- For it: the lowest cost. Vanilla runs its own arms again.
- Against it: the PANIC floor is lost, because vanilla decays PANIC by about 1.12 a game minute (#3392) and nothing restores it. The TEMPERATURE target is lost too.

**(c) The hybrid, re-shaped for rule 6: (b) plus a once-a-minute PANIC and TEMPERATURE write.** S1 defined the hybrid with a per-tick `OnTick` PANIC hold, and rule 6 replaces that hold with this write.
- **PANIC saw-tooths.** Vanilla decays PANIC linearly, the same per game minute at either clock (#3392, #3400). A floor of 10 written once a minute read 8.7444 to 8.9287 before each write at DayLength 1 (#3400).
  - The moodle flickers one level once a game minute only when the floor sits within about 1.26 above 6, 30, 65 or 80 (#2369's thresholds; a 6.5 floor went under 6 every minute, #3401). The moodle itself was not read, so the flicker is inferred. A floor that must sit near a threshold can be written about 1.26 higher so it never dips under.
  - The targets the earlier holds wrote sit outside all four windows: 10, 12.75 and 14.5 (#3101), and 19.25, 35 and 14.75 (#3082).
  - Vanilla's own rise from zombies in view adds on top between writes, and no reading covers it.
- **TEMPERATURE held.** Written to 37.5 once a game minute, it held within about 0.02 °C at DayLength 1 and 0.04 °C at the DayLength 4 tick spacing, and the thermoregulator's core followed it (#3393). This is the per-minute write, not the takeover's own path, so X81 stays unmeasured, and with (a) withdrawn it is moot.
- Cost: (b)'s, plus two more stat sets a player a minute. By #3373's three sets at 0.6–0.9 µs that is under a microsecond (inference; not timed as such).
- For it: (b)'s cost, with PANIC kept within 1.2556 of its floor (#3400) and TEMPERATURE within 0.04 °C of its target.
- Against it: the PANIC sawtooth near a threshold, and vanilla's panic rise between writes, which is unread.

**The design's all-in cost with no per-tick work** (per player per game minute; arithmetic on #3373, #3386, #3387; Performance, above). The slow minute moves from the `OnTick` drain to `EveryOneMinute` (superseded by Decision 6 (b): a budgeted `OnTick` queue runs every player every minute), run for every player in one event (m = 1, the burst) or for ceil(N / m) players an event in a rotation (a round-robin of period m).

| design | DayLength 1 | DayLength 4 |
|---|---|---|
| (b) or (c), m = 1 (the burst) | 1600–1660 µs | 1631–1991 µs |
| (b) or (c), round-robin m = 5 | 334–394 µs | 365–725 µs |
| (a), withdrawn, for the record | 1704 µs | 2307 µs |

- **The burst spike.** The burst measured at most 6 ms per event with two players, and the round-robin at m = 5 at most 4 ms (#3391).
  - Extrapolated at 1.23–1.58 ms per player-run (labelled extrapolation), a full burst costs 24.6–31.7 ms per event at 20 players and 49–63 ms at 40, a quarter to over half of a 100 ms tick, once a game minute.
  - The m = 5 round-robin costs 4.9–6.9 ms at 20 players and 9.8–13.8 ms at 40, on its own basis of 1.23–1.72 ms, the round-robin's measured 1721.3 µs per player-run (#3391).
  - Under a fast clock every tick carries one minute event (#3348), so a burst there runs every player every tick (inference). The round-robin bounds that too.
- **The round-robin's period is a coarse minute.** Each player then runs every m game minutes, which is P2's k = m.
  - m = 2 holds only if Angus adopts Appendix H's fairer band; under ruling 4, k = 2 fails (#3396, #3397), and event landing at its own minute was never run. It also needs first-sight alignment. Its all-in cost is 809–869 µs at DayLength 1 (arithmetic).
  - m = 5 is player-visible (#3396; Appendix H).
  - Appendix C's wall-cycle share is an `OnTick` share, so it leaves with rule 6.

**What (b) and (c) share.**
- The mode becomes a restart-only choice. It can be read at the server's `OnGameBoot` (#3380), but no mod route re-runs the engine's load of the rates (#3365).
- A writer outage is not a vanilla fallback. With the rates zeroed and the writer stopped, players stop getting hungry, thirsty or tired.
- Any other mod reading the rates reads zero (#2564).
- Fatigue asleep, the STRESS and FOOD_SICKNESS floors and `rmod` are approximated, one write interval late (Appendix A § 5). Under a round-robin, the interval is m game minutes.
- Still unmeasured: the exercise arm's swing branch, the `setDelayToSleep` rewrite, and the updaters' cost under non-zero rates and many players.
- Obligations on the build: fold each auto-drink sip into the THIRST target (#3382); run the writer after the minute's eats (#3383); never read the mode at the client's `OnGameBoot` (#3381); step by elapsed world age (#3371); set each rate to `0`, never `nil` (#3366).

**Coupled with Decision 2.** Under Decision 2's (a) or (c) the satiety scalar S needs a home. With the takeover withdrawn, S steps once a slow minute: it lags by up to a minute and loses the exact match (the S4 coupling above). Under a round-robin of period m it steps every m minutes (Performance, P2).

**Recommendation:** (c), the once-a-minute hybrid.
- It rests on:
  - the measured boot-time mode read;
  - the measured auto-drink and eat behaviour;
  - a measured TEMPERATURE hold;
  - a PANIC sawtooth that stays within 1.2556 of its floor (#3400);
  - an all-in cost below the withdrawn takeover's at both day lengths.
- It asks Angus to accept a restart-only mode, an outage with no vanilla fallback, and the PANIC sawtooth.
- The drain's period is Angus's:
  - m = 1 keeps every-minute behaviour and pays the burst;
  - m = 2 halves the cost and the spike, at P2's one-minute back-dating, once the first sight is aligned and events land at their own minute, and only if Angus adopts Appendix H's fairer band (under ruling 4, k = 2 fails, #3396, #3397; event landing was never run);
  - m = 5 is player-visible.
- **Under Decision 6 (b) (Plan 10c)** every player runs every game minute through a budgeted `OnTick` queue. So the period m above matters only if (b) is not adopted, and (c)'s writes land in each player's own minute run.

### 2. Hunger feel

**(a) Vanilla's hunger plus the energy term.**
- Evidence: it matches vanilla's HUNGRY level in all 1440 minutes on every day length, by the model's identity (#3345; Appendix D).
- For it: no tuning, on any day length. The energy deficit is the realism coupling on hunger.
- Cost: bulk, fibre and fat no longer touch hunger. It needs the laddered relief getter, a migration of S with a store version bump, and the freeze gate's two differences named.

**(b) A stomach-driven feel at a tuned half-time.**
- Evidence: it is closest on a 15-minute day (4.5 h: MAD 0.0304, 1344 minutes agreeing) and drifts as the day lengthens (4.25 h: MAD 0.0626, 0.0785, 0.0850) (Appendix D). Its plateau at hunger 0 runs 1142–1221 minutes a day, against vanilla's 96–669.
- Cost: it fails the light menu at every day length. It reaches level 3 and is hungrier than vanilla for 683–795 minutes (Appendix D). The shipped 2 h is far off: MAD 0.31–0.38 and 1067 minutes hungrier.
- For it: no migration, and bulk shapes hunger.

**(c) A blend in which bulk shapes relief.**
- Evidence: it equals (a) on the main menu for β 0.5 or less; at β 1 it departs from (a) even there, hungrier for 76, 137 and 158 minutes on the 30-, 60- and 90-minute days (MAD 0.0097, 0.0167, 0.0188). On the light menu β 0.25 makes the character less hungry than vanilla for 111 minutes (MAD 0.0348), and β 1 for 894 minutes (MAD 0.1372) (Appendix D). The fill-floor form is inert below w 1.
- For it: a bulky meal sates more.
- Cost: a vanilla-relative feel that varies with the menu, at a β chosen by taste. It carries (a)'s migration too.

**Which day length the feel is tuned for.** This matters for (b) and for (c)'s β. It does not matter for (a), which reads the same timer vanilla reads. The acceptance profile runs a 15-minute day, the fixture a 90-minute day and vanilla's default a 60-minute day. A (b) tuned at 15 minutes (4.5 h) is not the best at 60 minutes (4.25 h).

**Coupled with Decision 1.** (a) and (c) are exact only where S updates every tick, in the takeover's step. Under Decision 1's hybrid, S steps once a slow minute and the match is within a minute's lag, not exact (the S4 coupling above). (b) does not depend on Decision 1.
- A coarse minute or a round-robin of period m (Decision 1; Performance, P2) steps S every k or m minutes instead, multiplying that lag: about 5.8e-3 idle and 1.2e-2 exercising at k = 10, by linear scaling and unmeasured (Appendix H).

**Recommendation:** (a), if the goal is "feels like vanilla, reads the energy balance" (Appendix D). If bulk must matter, (c)'s relief scaling at a β Angus picks.

### 3. Record pruning default, and where the store lives

**Read by Plan 10c H6 (jar and offline) and H2b (live); Hitching, The global store.** The answer changes in two ways.

**First, the store must leave global modData in Plan 11, whatever the pruning default.** This is a privacy and griefing blocker.
- Any logged-in client can request the store by name, and the server sends it whole. A mod cannot refuse, because the handler fires no Lua event and consults no hook (#3417, #3418).
- Live, a release client received every record at 2 and 60 records (#3469). Above about 92 records (arithmetic, 1,000,000 / 10877) the reply is truncated (#3419); at 500 it failed on both sides, and the client kept its session (#3470).
- What leaks (inference from what a record holds; Appendix O): the username of everyone who ever joined, and their health state.
- The griefing half: a ~30-byte request (Appendix O) makes the server serialise up to 1 MB on its main loop. A modified client can repeat it at will. At 60 records its frame cost was within the idle jitter (#3469); above that, and repeated, it is unmeasured.
- Pruning or an inputs-only record shrinks the leak but does not close it.
- **The storage candidates** (H6; Appendix O, with their jar cites):
  1. **A server-local file through `getFileWriter` and `getFileReader`: recommended.** It sits under the server's Lua cache folder, and no network route reads it. Its costs:
     - the mod writes its own JSON serialiser;
     - the file name must carry the server or world name, because the folder is per host;
     - the write still runs on the main thread;
     - it is not atomic with the world save: after a hard kill the world rolls back (#2098, #2758) and the file does not.
  2. **Global modData under a secret name**, possibly one table per player. The secret must live in option 1's file. It still pays the main-thread save, and it shrinks a request from a guessed name to one record.
  3. **Player modData: rejected.** Any mod on the owning client can replace the server's copy (#1085), and the server's copy is empty at join (#1432).
  4. **`getModFileWriter`: rejected.** It writes into the mod's own folder, which a Workshop update replaces (#1866).

  Plan 11 needs a jar read of the chosen route before it builds on it.

**Second, the recommendation flips to pruning on by default.**
- **The size.** A record is about 10.8 KB in the save's format (#3422), and 10877 bytes on disk live (#3468). So 500 records are about 5.4 MB, over the rule's 1 MB, and 2000 about 21.8 MB. An inputs-only record is only 19 % smaller, so it is not a size fix on its own.
- **The save.** While the store stays in global modData, its size is a hitch (#3467). The first console save at 2000 records took 2770 ms, made a 2990 ms server frame and paused the clients. At 500 the second save added 41 ms over the second at 0.
- In a server-local file the size still sets the write's main-thread cost, so pruning keeps paying after the move (inference).

**The options.**
- **On by default, with a keep of N game days.** Cost: a player away longer than N days returns to a fresh record.
- **Off by default, operators opt in** (the draft's ruling 14). Cost: the store grows with every player who ever joined, about 10.9 KB each, and with it the save or the write.

**Recommendation:** pruning on by default, with N Angus's to set; and the store moves to a server-local file in Plan 11 (the blocker above), whichever default he picks.

### 4. Internal ids in shipped comments

- **Keep.** The ids are the maintainers' route to the evidence (the draft's ruling 15). Cost: they are opaque to a Workshop reader.
- **Strip.** Cost: the route to the evidence is lost from the code. The edit touches every commented Lua file, so it is a server event like any code release (#3378), and it changes lines that the register's `repo:mod/` pointers quote.
- No spike measured this beyond S6's server-event reading; it is a judgement.
- **Recommendation:** keep.

### 5. Subscribing to the five Workshop neighbours

- **Subscribe.** The five deferred code reads can then run. Cost: Angus's time to subscribe.
- **Do not subscribe.** The five reads stay deferred, and the compatibility notes stay as they are.
- No spike touched this.
- **Recommendation:** subscribe when convenient; nothing in Plan 11 waits on it.

### 6. Spreading the minute at 60 players

**Measured by Plan 10c (H3, H4; Hitching, The scheduler shoot-out).** Angus answered the principle on 2026-10-07: a per-tick site is allowed where it is measured to reduce hitching. The choice was then read against ruling 2's rules at N = 60, at DayLength 1 and at 37 ticks a game minute (the DayLength 4 spacing). The options carry ruling 2's letters:
- **(a) The one-event design:** every player's minute in one `EveryOneMinute` event. This is the earlier "(c) accept the spike", and "(a) make a player-run cheaper" at m = 1. It is admissible only if the burst itself stays at most 25 ms at N = 60.
- **(b) A budgeted per-tick scheduler.** The minute event queues the players, and `OnTick` drains the queue under a per-tick budget, carrying the unserved forward, with no simulation per tick.
- **(c) A round-robin of m = 2.** This is the earlier "(a)" at m = 2. It is admissible only if it meets (b)'s bounds and Angus adopts Appendix H's fairer band.

**The answer.**
- **(a) is excluded.** The burst added 47 to 67 ms to the longest frame in nine of nine draws, at both spacings (#3489, #3490). Its minute frame is 50 ms of busy at the median and 88 at the worst at N = 60 (#3472).
- **(c) is excluded on H3's evidence.** A round-robin of two added 32 ms at the 99th percentile and 31 at the maximum (#3475).
- **(b) is adopted, provisionally, with a 15 ms budget at both measured spacings.** In nine draws (#3489–#3492):
  - it added 12 to 13 ms at the 99th percentile and 11 to 25 ms at the maximum (one draw exactly at 25);
  - no ghost starved;
  - its total was 1.053 to 1.061 times the burst's on the drift-immune measure.
  - The burst met the alternative clause in every draw: more than 33 ms added, or a frame over 133 ms.
  - The empty-queue clause (at most 0.1 ms a frame) is **weakly supported, not measured to 0.1 ms.** `x243d`'s A-B-B-A estimate is −0.053 ms a frame with a standard error of about 0.03, inside a drift of about 0.6 ms a frame (#3483).
- **The budget must be sized to the minute's work** (rule #3497).
  - At N = 60 and DayLength 1, a 10 ms budget ran at the margin: 56.75 of 58 a minute event, each ghost at most one event late (#3476).
  - A 5 ms budget starved every event (#3477).
  - The draft's ceil(N / ticks) spread starved at N = 40 and 60 (#3478).
  - Under a fast clock a 10 ms budget left ghosts up to 42.8 game minutes stale (#3480).
- **Caveat: (b) is headroom, not relief.** Ruling 2's thresholds are read on the end-to-end period. On the loop's own cadence neither design delayed a tick at N = 60 on this host, one unexplained 136 ms period aside: the burst's busy of 56 to 77 ms at the frame max (x244; x243a's 88 ms also fits) (46 to 51 at the minute-frame median) fits inside the 100 ms period (#3486). So (b) buys headroom for larger N, heavier minutes and slower hosts. The burst's busy is linear in N (#3474). Extrapolated (inference), the worst minute frame at N = 60, 88 ms (#3472), crosses the period near N = 68–74 and the median minute frame, about 50 ms, near N = 120; the H4 review's 85–95 sits inside the 68–107 the frame maxima give (arithmetic). None of it counts vanilla's own per-player load at a real 60, which is unmeasured: H5's fake clients could not join (#3494).
- **The client reading does not loosen ruling 2** (ruling H4-2, restated). The stamp test was blind at the 200–400 ms packet cadence. Another player's motion showed no minute-aligned gap above chance on loopback with no zombies (#3486, #3488). And no tick started late (one unexplained 136 ms period in x244a aside), so there was no stall to see.

**Open items for Plan 11's scheduler task:**
1. A minute-sized adaptive budget: the per-run cost times the queue over the minute's ticks, with headroom, and scaled to the clock (ruling H4-1). The 15 ms budget is a fixed cap that suits 60 players on this host only.
2. A direct bench of the empty-check loop (ruling H4-1). The A/B could not resolve 0.1 ms above the drift.
3. A player's own-action latency under the burst and under (b): timed-action completion and a container round trip. This is the noticeability reading H4 did not take.
4. Real network latency and jitter, on a second host or behind a latency shim (E7, Angus's to supply).
5. Zombies near the players: the fixture has none.
6. The mass join. First sight's 0.861 ms a joiner is a floor, so sixty joiners in one frame are at least 51.7 ms (#3463; arithmetic). Whether a mass reconnect is a burst is unmeasured.
7. Routing the 07:00 day close and first sight through the same queue as the minute. A game-time boundary every player shares falls in the same game minute for all of them, so a per-player close keyed on it is a synchronised burst otherwise (#3427).
8. A fast-clock policy, Plan 11's to decide: scale the budget with the clock, or run everything when every frame is a minute frame. Under `settimespeed 30` a 10 ms budget left records up to 42.8 game minutes stale (#3480).
9. The measurement route for the mod's own scheduler. `ghost.load`'s schedulers are the harness's own copies (#3455), so once Task 2 moves the drain into the mod the harness cannot measure it as it stands. Measuring it needs the harness to feed ghost records into the mod's own queue, then its own shoot-out against the 15 ms budget (`budget15`) at both spacings (performance.md, Open).

**Still Angus's:**
- the populated-server reading (E7), which also gives vanilla's own frame at a real 60. H5's fake clients are not an answer: on 42.20.4 they are kicked at join for want of a saved character (#3494, #3495), so vanilla's per-player load at 60 stays unmeasured. It is Angus's to supply from a populated server, or a new task that saves a character per fake client and runs one JVM each (#3496; Hitching, The fake clients);
- the fairer band, which matters for Decision 6 only if (c) comes back into play.

**Recommendation:** (b), a budgeted `OnTick` queue that carries unserved players forward, with a budget sized to the minute's work (15 ms at N = 60 on this host is the smallest measured cap that starved none; the true floor lies between 10 and 15 ms), a fast-clock rule, and the per-player sends staggered (#3464). The cheaper run stays Plan 11's performance target either way: heal once before the step first (Hitching, Ranked refactors).

## Appendices

The spike sections follow verbatim, each with its readings and rows.
Appendices A–D, and the per-tick text in G and H (the wall cycle, the `OnTick` hold, a per-tick home for S), predate rule 6. Decision 1 and the Performance section supersede them; the appendices are records and are not edited. Appendices J–O are Plan 10c's H1–H6 task memos, verbatim, their headings demoted one level.


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
- Recommended: `OnNewGame` **evicts** instead of storing — `P.online[u] = nil` and the username dropped from the queue (or the queue entry made to re-read `P.online[u]` at drain time, which then finds nil and skips) — so no drain can reach the dead object after the reset; `P.minute`'s identity comparison (ruling 4's second clause) then adopts the list's object at the next event and fires first sight. The "dead" mark must also never be written onto a record whose `resets` changed since the queue entry was made (a cheap guard: carry the record's `resets` in the queue entry). Test: the golden-trace host's respawn at minute 101 with the new object appearing three ticks after `OnNewGame`.

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

## Appendix G. P1 and P3 — the slow minute by step, and the cost of no per-tick work

Its provisional rows T108.1–T108.8 are #3387–#3394.

## P1+P3 — the slow minute by step, and the cost of no per-tick work (memo section)

Run: `x231-20261007-111042` (profile `x23-perf`; phases S0 A B D C2 C Z). The run booted the staged copy of the tree at `dc619d0` (MANIFEST sha256 `c86e295a…2415b389`). Its `NR_Server_Bench.lua` had the P1+P3 instruments appended (sha256 `c20f645d…0f8d`, the same on all three deployed copies).
- Fixture `two`: `admin` -debug, `bob` release. Nutrition false, DayLength 1, sleep on, one host.
- The driver and profile were committed at `105c0d3` before the run; the artifact at `061630a`.
- The provisional rows `T108.1`–`T108.8` are in `task-P1P3-claims-delta.tsv`. Every figure is n = 1 and a cost, not behaviour.
- `getTimestampMs` has 1 ms resolution, so every per-run figure is a total divided by a count. Each step's total is a sum of 1 ms truncations, so it carries a binomial noise of sd = sqrt(sum d(1-d)) over the runs (d the fractional ms of each run): in A (240 runs) bus 2 ms ±1.4 (70 %), fast 1 ±1.0 (100 %), reconcile and kinetics 14 ±3.6 (26 %, ±15 µs a run), strength and weight 17 ±4.0 (23 %), effects 29 ±5.0 (17 %), metabolism 80 ±7.3 (9 %, ±30 µs a run), nutrients 192 ±6.2 (3 %), `__run` 374 ±7.7 (2 %) (arithmetic on the totals). So A's bus, fast, reconcile, kinetics, strength, weight and effects µs/run are indicative only; only metabolism, nutrients and `__run` carry a figure to better than 10 %.

### P1 — the slow minute by step

The wrap ran at the first `profStart`, not at `OnServerStarted`. `NR_Server_Bench.lua` loads before every adapter, so an `OnServerStarted` handler there would have wrapped nothing. This is the artifact's first deviation.

**Per step**, in µs per run. A is in play (240 runs, 120 game minutes, both players: two apples each, a walk out and back, `admin` asleep for minutes 80–110). B is `settimespeed 30` (606 runs). D2 is the bench minute at an unchanged world age (1000 bench calls plus 4 drain runs, 1004 runs of the pipeline). In D2 bus, fast and effects (1 ms each) and kinetics (2 ms) are below the resolution and meaningless as µs/run (the table's 1.0, 1.0, 2.0 and 1.0 are truncation floors, not costs); reconcile's 11 ms is ±30 % (about ±3.3 ms). NR.call is counted at run time; direct calls are the static count.

| step | A µs/run | A share of `__run` | B µs/run | D2 µs/run | NR.call/run (A) | direct Java/run (static) |
|---|---|---|---|---|---|---|
| bus | 8.3 | 0.5 % | 11.6 | 1.0 | 0 | 1 |
| fast | 4.2 | 0.3 % | 3.3 | 1.0 | 0 | 0 |
| reconcile | 58.3 | 3.7 % | 44.6 | 11.0 | 5 | 0 |
| kinetics | 58.3 | 3.7 % | 107.3 | 2.0 | 1 | 1 |
| metabolism | 333.3 | 21.4 % | 272.3 | 135.5 | 30 | 5 |
| **nutrients** | **800.0** | **51.3 %** | 651.8 | 144.4 | 9 | 2 |
| effects | 120.8 | 7.8 % | 123.8 | 1.0 | 7 | 0 |
| strength | 70.8 | 4.5 % | 59.4 | 29.9 | 11 | 2 |
| weight | 70.8 | 4.5 % | 47.9 | 25.9 | 16 | 1 |
| `__run` (the pipeline) | **1558.3** | 100 % | 1358.1 | 360.6 | 79 | 12 |
| `__work` (`P.work`) | 1583.3 | — | 1376.2 | 362.5 | 82 | not recounted |

A's step totals in ms: 2, 1, 14, 14, 80, 192, 29, 17, 17. They sum to 366 of `__run`'s 374; the rest is `MIN.run`'s loop and pcalls plus truncation [T108.1]. B's totals are in [T108.3], the bench in [T108.4].

**What this changes.**
- **One in-play player-run costs about 1.56 ms**, about 4.1 times S2's 377 µs (#3354). S2's figure was taken at a zero interval, where Nutrients returns early and Effects never runs; this session's bench at a zero interval read 333–430 µs, agreeing with #3354 [T108.4]. The 4.1 is not all elapsed-time work, and not all of it is the pipeline: A's `__run` includes about 100 µs of this session's instrument overhead (step timers and the call counter), which leaves about 3.9 times (arithmetic). Reconcile, strength and weight make the same NR.call counts in A and D2 (5, 11 and 16 a run) yet cost 58, 71 and 71 µs in A against 11, 30 and 26 in D2, so a part of the rise is cold interleaved running against the warm tight bench loop, not integration of a longer interval (inference; reconcile's D2 figure is itself ±30 %).
- **The S2 player budget (Appendix C, S2.4) under-counts m by about 4×.** With m = 1583 µs, the per-player-per-tick rows rise accordingly (arithmetic below).
- **Nutrients is half the minute, and it is Lua, not Java.** It makes 9 NR.calls and 2 direct calls a run. Metabolism is the next fifth.
- A fast clock did not raise the per-run cost: B's 606 runs cost 1358 µs a run against A's 1558 [T108.3]. The minute counter advanced 607 events over 631 ticks in B (`verdicts.B.observed.start` and `end`: minutes 288 to 895, ticks 1806 to 2437), about one event a tick, and 606 runs, one player drained an event, so each player ran every second event. Under `settimespeed 30` (`phases.B.time_fast.mult` 142.8, 60 s wall by `constants.B_S`) the game minutes a tick are arithmetic, about 4.7, not a field of the file, so a run integrated about 4.7 game minutes if a run's interval is one event's or about 9.4 if it is the player's own gap of two events (inference, from the closed-form steps integrating from each player's own last age). The steps integrate elapsed time in closed form, so a run's cost is taken not to grow with its interval; that is an inference from B's flat cost, and the basis for dividing the minute by the round-robin period below.

**Java calls per run.** The run-time counter wraps `NR.call`. `NR.num`, `NR.obj` and `NR.flag` call it as `pcall(NR.call, …)`, a table lookup at call time, and the adapters' local `num`/`obj`/`flag` aliases capture those three, not `NR.call`. So every NR.call-routed call is counted [T108.2].
- A static read of the adapters (one typical awake minute, no day close, healthy) counted 82 NR.call-routed calls in `P.work` (79 in the pipeline `__run`, 3 outside it) and, recounted from the staged adapters for `__run`, 12 direct ones: 8 `getGameTime` (kinetics 1, metabolism 2, nutrients 2, strength 2, weight 1), 1 `NR.isServer` in the bus step's `flushEffects` and 3 state `.instance()` in metabolism (`SwipeStatePlayer`, `ClimbOverFenceState`, `ClimbThroughWindowState`). The earlier 14 had two direct calls with no location; none was found in `bus`, `fast`, `reconcile`, `kinetics`, `effects` (its `ZombRandFloat` roll is gated on `E.bruise` above 0, so it is not a typical minute's) or the `OnServerStarted` registrations. The per-step column above is the 12.
- The static and run-time NR.call counts agree step by step: metabolism 30, weight 16, strength 11, nutrients 9, effects 7, reconcile 5, kinetics 1.
- **Route shares, on the `__run` basis:** 79 of 91 Java calls go through NR.call (86.8 %) and 12 (13.2 %) are direct.
- The takeover handler's `body(h)`: about 70 Java calls a call, typical (66–82), all through hoisted handles.

**The Java-share estimate (P1 Step 4; an estimate).**
- Calibration: (19.33 − 4.36) ÷ 70 = **0.214 µs per Java call**, from the handler (#3353) less the pure step (#3356) over the handler's 70 static calls.
- Java µs per run in A: bus 0.21 (2.6 %), reconcile 1.07 (1.8 %), kinetics 0.43 (0.7 %), metabolism 7.5 (2.2 %), nutrients 2.4 (0.3 %), effects 1.5 (1.2 %), strength 2.8 (3.9 %), weight 3.6 (5.1 %).
- The whole pipeline: 91 calls × 0.214 = 19.5 µs of `__run`'s 1558 (1.25 %).
- **The caution.** The calibration is for hoisted handle calls. An NR.call-routed call also pays a pcall, an index, a vararg pass and this session's counter wrapper.
- An in-session upper bound comes from D2's reconcile step: 11.0 µs per run for 5 NR.calls and a small kernel compare, so at most **2.2 µs per NR.call-routed call**. That bound rests on a step of 11 ms ±3.3 ms (the binomial noise above); at +1 sd (14.3 ms) it is about 2.9 µs a call.
- At that bound, weight's 17 calls are about 37 µs of its 71 in play (about half) and of all its 26 µs at D2. Strength's 13 are about 29 of 71 (40 %), metabolism's 35 about 77 of 333 (23 %). At +1 sd (2.9 µs a call) weight's 17 would be about 49 of 71 and strength's 13 about 37 of 71, so strength would also cross half (arithmetic). The two small steps would then be Java-bound, but each is about 70 µs of a 1583 µs minute.

**P4's trigger (ruling 3): NOT TRIGGERED** by the estimate P1 Step 4 names. No step's Java share reaches half; the largest is weight at 5.1 %. P4 stays not triggered by rule 3's letter: its estimate is 0.214 µs a call, and the largest share it gives is weight's 5.1 %. The controller should note the bound above: at 2.2 µs per NR.call-routed call, weight (and nearly strength) would reach half, for a saving of at most about 37 µs + 29 µs per player-run (at +1 sd about 49 + 37) (4 % of the minute). The step that matters for cost is Nutrients' Lua.

### P3 — what no per-tick work gives up and pays

#### C — the once-a-minute PANIC and TEMPERATURE write (Overlay: `options.mode` 2, `fast.registered` false)

**PANIC [T108.6].** Vanilla's decay is linear and per game time.
- At DayLength 1 it fell **0.17969 a tick** (44 falls, 0.17889–0.18069), from 0.5 to 0.32, 0.14, then 0. That agrees with #3116.
- At the slowed clock (37 or 38 ticks a game minute) it fell **0.030086 a tick** (336 falls).
- Both are **about 1.12 PANIC a game minute** (0.17969 × 6.24 = 1.121; 0.030086 × 37.4 = 1.125). The day length changes ticks, not the per-minute fall.
- **The plan's target of 0.5 was the wrong scale.** PANIC spans 0–100, so 0.5 decays to 0 within three ticks at DayLength 1 and within 17 at the slowed clock. Both recorded amplitudes are the clipped target, 0.5. The driver's C1 "falsified" and C4 "as_predicted" (ratio 1.0) are therefore trivial and are listed in do-not-cite.
- **The sawtooth at a real target (arithmetic on the measured linear decay; not measured at such a target):** a floor written once a minute at T drops to about T − 1.12 just before the next write, at any day length.
- The PANIC moodle thresholds are 6, 30, 65 and 80 (#2369).
- **So a player sees a flicker only when T sits within 1.12 above a threshold**: the four windows are [6, 7.12), [30, 31.12), [65, 66.12) and [80, 81.12), each flickering one level up and down once a game minute (arithmetic on the measured decay and #2369's thresholds). The targets the earlier holds wrote sit outside all four: 10, 12.75 and 14.5 (#3101) and 19.25, 35 and 14.75 (#3082; 35 is #3082's, not #3101's).
- A floor that releases between writes is also not the takeover's hold (T13-1). Vanilla's panic rise from zombies in view adds on top between writes, which no reading here covers.

**TEMPERATURE [T108.7]: the write held.** Written to 37.5 once a game minute (0.5 above the set point 37):
- At DayLength 1 the pre-write read climbed 36.3309 → 36.9170 → 37.2068 → 37.3503 and then sat 37.47803–37.48045 for the last ten writes, about 0.02 °C under the target. The tick after each late write read 0.011–0.013 under it.
- At the slowed clock the last ten pre-writes read 37.46046–37.46208 (0.04 °C under).
- The thermoregulator's core moved with it: 36.2675 before, 37.4277 after (`temp.core`). The stat write moves the core, and the regulator pulls back only a few hundredths a minute.
- **Answer to "did the takeover's temperature target ever hold" (X81):** this is not the takeover path. The takeover writes only on the adjustment's far side, every tick. It is the once-a-minute absolute write a no-per-tick design would use, and **under Overlay it held within 0.04 °C**. X81 for the takeover's own path stays unmeasured.

**The day-length route [T108.8].** `sandbox.set DayLength 4` read back 4 but left the clock at 6.47 ticks a minute for 10 s. C4 therefore ran under `time.multiplier` 0.1674 (37 or 38 ticks a gap), the DayLength 4 tick spacing. Whether vanilla's decay under a real DayLength 4 equals the multiplier's is inference. Both are game-time scaled, and the per-minute fall matched at the two clocks.

#### C2 — the burst and the round-robin [T108.5]

The minute was driven from `EveryOneMinute`, with the `OnTick` drain left on.
- **Burst** (both players, one event): 145 ms over 59 events and 118 player-runs. That is **1228.8 µs per player-run** and 2457.6 µs per event, max 6 ms. The per-event histogram: 1 ms ×11, 2 ×28, 3 ×8, 4 ×8, ≥5 ×4.
- **Round-robin `B.burstRR(5)`:** ceil(2/5) = 1 player an event, 105 ms over 61 events. That is **1721.3 µs per event** (= per player-run), max 4 ms. With N = 2 each player ran every second minute, so each run integrated about 2 game minutes.
- **The tick spike (extrapolation, labelled).** These assume a constant per-player cost of 1.23 ms (C2) to 1.58 ms (A), and a 100 ms tick:
  - a full burst costs 24.6–31.7 ms per event at 20 players (25–32 % of one tick) and 49–63 ms at 40 (half a tick or more), once every game minute;
  - the round-robin at m = 5 runs ceil(N/5) players: 4 at 20 players, 4.9–6.9 ms (1.23–1.72 ms each); 8 at 40, 9.8–13.8 ms.
  - The per-run cost at m = 5 (each run integrating 5 minutes) is assumed flat by B's reading, not measured.

#### The all-in cost of no per-tick work, per player per game minute (arithmetic on readings)

The terms:
- the S1 writer, Lua side: 11 µs (#3373);
- vanilla's updaters, which run when no hook is registered: 1.0–10.6 µs per update (#3386), × 6.27 ticks (DayLength 1) = 6–66 µs, or × 37.46 (DayLength 4) = 37–397 µs;
- the minute work: 1583 µs (A's `__work`), divided by the round-robin period m. B's flat per-run cost supports dividing the per-run cost by m.

| design | DayLength 1 | DayLength 4 |
|---|---|---|
| no per-tick work, m = 1 | 1600–1660 µs | 1631–1991 µs |
| no per-tick work, round-robin m = 5 | 334–394 µs | 365–725 µs |
| the takeover (for scale): 19.33 µs/tick (#3353) × ticks + the minute | 121 + 1583 = 1704 µs | 724 + 1583 = 2307 µs |

Per tick at DayLength 1 (÷ 6.27), m = 1 gives about 255–265 µs per player per tick: 5.1–5.3 ms per tick at 20 players, 10.2–10.6 ms at 40. Most of that is the minute's Lua, whichever clock drives it. At m = 5 it is 53–63 µs per player per tick (1.1–1.3 ms at 20 players). At DayLength 4 (÷ 37.46), m = 1 is 44–53 µs and m = 5 is 10–19 µs per player per tick.

So rule 6's design costs less than the takeover at both day lengths: it drops the handler and pays vanilla's updaters instead. Its own risk is the burst. A full burst at 20–40 players spends a quarter to a half of one tick once a minute. The round-robin, or a wall-cycle share (Appendix C, S3.2), spreads it.

### Plan 11 tasks this changes

- **Decision 1 (no per-tick work):** the once-a-minute write is measured.
  - TEMPERATURE holds within 0.04 °C.
  - PANIC falls 1.12 a game minute, linear, so a floor flickers a moodle only within 1.12 above 6, 30, 65 or 80.
  - The burst must be spread: round-robin or wall cycle.
- **The cost rows (Task 13, S2.4's table):** re-base m on 1583 µs in play, not 377.
- **The performance target:** Nutrients' Lua (51 % of the minute) and Metabolism (21 %). Java caching (P4) is not triggered.

### Concerns

1. The plan's PANIC target of 0.5 was on the wrong scale (0–100), so the sawtooth at a realistic target is arithmetic on the measured decay, not a reading. A follow-up hold at a target near 10 or 20 would take one short session.
2. P4's trigger is "not triggered" by ruling 3's estimate. By the in-session upper bound of 2.2 µs per NR.call-routed call, weight sits at about half (37 of 71 µs) and strength at 40 %, both small; at +1 sd of the bound's step (2.9 µs a call) weight is about 49 and strength about 37 of 71, so strength crosses half too. P4 stays not triggered by rule 3's letter. That is the controller's call.
3. The live DayLength change did not take, so C4 used `time.multiplier`. The DayLength 4 figures are at the DayLength 4 tick spacing, not under the DayLength 4 option.
4. A's per-step figures are 1 ms truncation totals with binomial noise (sd 1.0 to 7.7 ms a step over 240 runs, the table under Per step): 70 % of bus's 2 ms and 100 % of fast's 1 ms, 26 % of reconcile's and kinetics' 14 ms, 23 % of strength's and weight's 17 ms, 17 % of effects' 29 ms, 9 % of metabolism's 80 ms, 3 % of nutrients' 192 ms and 2 % of `__run`'s 374 ms. D2's bus, fast, effects and kinetics are below the resolution.
5. The call counter's wrapper adds one Lua call to every NR.call, in every phase including D. D's 333–430 µs agrees with #3354's 345–395, so the overhead is within noise.
6. The meals, walk and sleep in A are load, not graded. Both eats queued with `validStart` true; admin read asleep at minute 95; HUNGER fell between the nut reads after the second meal.

## Appendix H. P2 — running the slow minute less often

Its provisional rows T109.1–T109.5 are #3395–#3399.

## P2 — Running the slow minute less often (memo section draft; rows T109.1–T109.5)

**Question.** Can the slow minute run every k game minutes instead of every one, with negligible drift?

**Answer: not under ruling 4's band. The largest safe k is 1.**
- **The method.** The golden trace's scenario was re-run offline (`testing/spikes/coarse_minute.py`, commit 0453181) with the slow minute (`h.minute()` then `h.tick(25)`) fired only on minutes m with m % k == 0, for k = 2, 5, 10, 15 and 30. The world age, the engine step, every event and every snapshot keep their own minute. Every k divides 30 and 240, so each snapshot follows a fired minute.
- **The sanity check.** k = 1 reproduces `golden/trace-1.0.0.json` byte for byte (sha256 df7806d8…daa9e8b3). Two full runs gave byte-identical outputs. Ticking 25 frames on every minute and ticking only on the fired minutes gave byte-identical traces at every k, because the drain's queue is empty between fired minutes [T109.1]. The choice of off-minute ticks therefore does not matter here; the outputs use no off-minute ticks, the coarse-`EveryOneMinute` shape.
- **The verdict.** No k from 2 to 30 is safe [T109.2]:

| k | continuous leaves outside the band (of ~9600) | discrete-state mismatches | safe |
|---|---|---|---|
| 2 | 1130 | 5 | no |
| 5 | 5543 | 13 | no |
| 10 | 6092 | 26 | no |
| 15 | 5906 | 35 | no |
| 30 | 6618 | 45 (+406 structural leaves) | no |

- **Why k = 2, the first unsafe k, fails** [T109.3]:
  - *Discrete state:* g4's effects key is one band lower in slot 9, the insulin band (6 against 5), at its departure snapshot (minute 150). Its effects epoch is one rebuild behind from then on.
  - *Continuous fields outside the band* (105 fields), in four groups:
    - First-sight timestamps: `firstSeen`, `bornAge`, `lastFallAge`, `acute.winStartH`. Each is one minute late, because the first fired minute is minute 2. Each is constant over the k = 1 run, so its range is 0 and any drift fails.
    - The closed day's intake `body.inDayClosed`: 0.22 to 1.69 kcal off, about 1.2–1.9 % of the value. It is set once per day, so its range over the run is 0.
    - `fluids.sweatLmin`: it doubles, by construction (below).
    - The nutrient pools' `p` values near 1 (vitA, zinc, vitB6, riboflavin, thiamine, calcium and others). Their ranges over the run are 1e-5 to 1e-4, so drifts of 1e-5 fail.
  - 385 of k = 2's 1130 failing leaves drift by 1e-3 or less. Measured against each field's range over all players instead (a secondary reading), 114 leaves still fail.
  - *With the first sight aligned.* A diagnostic run also fires minute 1, so every k starts from k = 1's first sight. k = 2 still fails: 489 leaves in 85 fields, plus one discrete flag (g4's effects push still pending at its departure) [T109.3].
- **The drift grows with k** [T109.4]. Largest drifts against k = 1, over six players and eight snapshots:

| field (range over k = 1) | k = 2 | k = 5 | k = 10 | k = 15 | k = 30 |
|---|---|---|---|---|---|
| stamped stomach fill (0.552) | 0.0052 | 0.021 | 0.048 | 0.063 | 0.25 |
| fat mass, kg (9.67) | 0.00086 | 0.0034 | 0.0076 | 0.012 | 0.024 |
| water pool, g (3435) | 30 | 121 | 270 | 416 | 853 |

  - The fat mass and the water pool drift roughly in proportion to k − 1. Most of that is the first-sight lag (the player is first seen at minute k, so k − 1 minutes go unintegrated) and the departure lag. Aligned, the fat mass's drift falls to 0.00015, 0.0006, 0.0012, 0.0016 and 0.0016 kg (summary, the aligned headline table).
- **A naming finding.** `fluids.sweatLmin` stores the step's sweat litres (the rate × dtM / 60), not a per-minute rate. Under a coarse minute it reads k times the per-minute value. No reader uses it [T109.5].

**What a coarse minute does to the player** (inference from the mod's code and the readings above; none of it was measured live):
- **Hunger moves in steps of k minutes.** Hunger is the view of `record.stomachFill`, which Kinetics stamps once per slow minute. The takeover's per-tick write (or the hybrid's writer) reads that stamp, so HUNGER holds flat for k minutes and then jumps. The stamped fill drifts up to 0.0052 at k = 2 and 0.048 at k = 10 [T109.4].
- **The bus push gap stretches.** Effects marks the mirror dirty at the end of a player's minute. The bus's flush is the first step in the pipeline's order, so the push goes out at the next fired minute, k minutes later. A change caused just after a fired minute therefore reaches the client up to 2k − 1 game minutes late, against up to 1 minute now. The `effects.dirty` flags left set at snapshots under every k > 1 show the pending pushes.
- **The moodles lag.** The client's moodles read the mirror, so they inherit the push lag. Mod-driven targets (panic, temperature) jump at a fired minute: at k ≥ 5 one snapshot already shows `panicTarget` 1.875 apart, and at k ≥ 10 (k ≥ 15 aligned) `tempTarget` 37.075 apart (summary, the headline tables).
- **First sight and departure.** A joining player's record, body and stomach are created at the first fired minute, up to k − 1 minutes after the join. At k ≥ 10 the scenario's minute-10 meals arrived before first sight. They took the intake's own path: `store.get` creates the record and the stomach is seeded full (`NR_Server_Intake.lua:425`). At a departure, the minutes between the last fired minute and the departure are integrated only when the player returns within the 60-minute clamp.
- **The day close** lands at the first fired minute after the day boundary. In this scenario every k divides minute 90, so the close's timing was not tested. `inDayClosed` differs from step size alone: the stomach's emptying and absorption over one k-minute step do not equal k one-minute steps.

**The cost saving** (arithmetic on #3354; P1's per-step figure supersedes it when it lands):
- One player's slow minute costs about 377 µs (#3354, the mean of 390, 395 and 345). That is a lower bound: it was measured at an unchanged world age.
- Divided by k, the per-player cost per game minute is 188.3, 75.3, 37.7, 25.1 and 12.6 µs at k = 2, 5, 10, 15 and 30.
- This assumes a call integrating k minutes costs what a call integrating one costs. The steps are closed-form in dtM, so that is plausible, but it is unmeasured.
- Under the S2 table's wall-cycle share, the per-tick peak (57.0 µs including the handler) does not fall with k: a fired minute still runs one player's whole minute. Only the average falls.

**The coupling with Decision 2.**
- Under options (a) and (c), S has its home in the takeover's per-tick step. A coarse minute does not touch S there.
- Under the hybrid (Decision 1 (b) or (c)), S steps once per slow minute. Appendix D bounds that lag at one minute: 5.8e-4 hunger idle and 1.2e-3 exercising. A coarse minute would multiply the lag by k. **Inference by linear scaling, unmeasured:** about 5.8e-3 idle and 1.2e-2 exercising at k = 10.
- So a coarse minute and the hybrid's once-a-minute S compound.
- Option (b) feels it through the stamped fill, which steps every k minutes (above).

### The recomputed verdict under a fairer band

The review (claude-opus-5-5) re-hashed the k = 2 and k = 5 outputs, found the harness right, and recomputed the verdict with the first sight aligned, an absolute band for constant leaves and a per-field range.
- **k = 2:** 75 leaves in 19 fields, and no band or grade flip once the first sight is aligned. What remains is one-minute back-dating: the minute-50 drinks, g6's sleep onset, the meal back-dating into the day close, g3's pools, `dmod` and `solAddH`, with g4's effects push pending at its departure. The strict count is 1130 leaves and 5 discrete mismatches; the per-field range gives 114. k = 2 is unsafe only on transient artefacts and the first-sight lag.
- **k = 5 (aligned):** 1309 leaves in 154 fields and 8 discrete mismatches, and two player-visible differences. g4's insulin band 6 is never shown before its minute-150 departure: the edge is crossed at minute 148, after the last fired minute 145. g6's caffeine band goes 0 to 1 at minute 150 (caffeine 50.84 against 48.74 mg), back-dated 4 minutes early.
- **The b/9 flip at k = 2 is the 0.6 edge crossed a minute late.** Slot 9 is the insulin band (K.effects.B.iu); iu is 0.599394 against 0.603771 (re-derived by the review, not in the outputs) at minute 148, and minute 149 never runs before g4 leaves. It is a one-minute back-dating, not a lasting difference. The effects epoch stays one rebuild behind at minutes 180, 210 and 240 (summary lines 229-231).
- **Back-dating.** A dose that lands between fired minutes is integrated over the whole step, so its effect begins at the step's start. Asleep and moving are sampled at the step's end, so a state held for part of a step is applied to all of it. Both grow with k.
- **The departure clip.** The minutes between a player's last fired minute and a departure are integrated only if the player returns within the 60-minute clamp; at larger k the clip is up to k - 1 minutes of the player's last state.
- **A missed death at k >= 15.** `printed_count` is 24 at k = 1 and 23 at k = 15 and k = 30 (summary lines 1193 and 1566): g3 dies at minute 100 and respawns at minute 101, between fired minutes, so a coarse minute never sees the death. The count was kept out of the verdict as telemetry, and this is a state event it hides.

### dt-correctness findings for Plan 11

No kernel assumes dt = 1: the fluids are dt-correct and the exponentials are exact. What grows with k is in the pipeline and in a few kernel lines.
- **Event back-dating and end-of-step sampling are pipeline artefacts** that grow with k: `NR_Server_Nutrients.lua:371-376` and `:387` (events land on the step), `NR_Kernel_Acute.lua:448-451` (asleep and moving sampled at the step's end).
- **exEma** (`NR_Kernel_Acute.lua:529`) and **coldH** (`NR_Kernel_Acute.lua:544`) decay the old value exactly but add the step's inflow undecayed, so they carry a bias of about +dtM/2; the exact form is r * tau * (1 - e^(-dt/tau)).
- **cafMean** (`NR_Kernel_Acute.lua:251`) is explicit Euler; it is fine while dtH is far below 168.
- **fluids.sweatLmin** (`NR_Kernel_Fluids.lua:177`, `:190`) holds the step's litres, so it reads k times a per-minute rate (T109.5).
- **The bruise roll** (`NR_Server_Effects.lua:440`) is one Bernoulli per step at E.bruise * dtM, so it undercounts at large k.

**What this does not settle.**
- It is one scenario of 240 minutes with eight snapshots, so a field's range over the run is often degenerate.
- Ruling 4's band is strict on near-constant leaves. A looser band (a field-wide range, or the value-relative drift) would still fail k = 2 on the effects key and on 114 leaves. Choosing a band is Angus's call; this study reports and does not tune.
- Untested here: a day boundary that falls between fired minutes, and a fast clock's one event per tick (#3348) combined with a coarse minute.

**Page sentences for the controller** (owner `docs/areas/testing-your-mod.md#walls`, one per row):
- T109.1: "The golden trace's scenario re-run with the slow minute fired every k game minutes reproduces the golden byte for byte at k = 1, and the off-minute ticks do not change it [T109.1]."
- T109.2: "No coarse minute from 2 to 30 game minutes passes the drift band: every one changes discrete state and moves hundreds to thousands of leaves outside 1 % of their range [T109.2]."
- T109.3: "At k = 2 the effects key already differs (g4's insulin band one lower at its departure), and aligning the first sight does not remove the failure [T109.3]."
- T109.4: "The drift grows with k: the stamped stomach fill by up to 0.0052 at k = 2 and 0.25 at k = 30 [T109.4]."
- T109.5: "`fluids.sweatLmin` is the step's sweat litres, not a per-minute rate, so a coarse minute multiplies it by k [T109.5]."

## Appendix I. P3b — the PANIC sawtooth at a target of 10 (run x232)

Provisional ids map T111.n -> #(3399+n).

### Task P3b memo section: the PANIC sawtooth at a realistic target (run x232-20261007-121312)

For the decision memo's Performance section ("The once-a-minute PANIC write: a sawtooth") and Decision 1 (c). Tags are provisional (T111.n; the dry run mints #3400-#3402).

**Measured, not arithmetic.** Under Overlay (no stat hook), with no panic source, a PANIC of 10 written once a game minute:
- falls linearly, not in proportion to its value: 0.17916 a tick at `DayLength` 1 and 0.030061 a tick at the `time.multiplier` 0.1674 spacing, within #3392's range at a 0.5 target (0.17969, 0.17889 to 0.18069; 0.030086, 0.029987 to 0.030320) [T111.1];
- reads 8.7444 to 8.9287 just before each write at `DayLength` 1 (a loss of 1.0713 to 1.2556, mean 1.1260, on gaps of 6 or 7 ticks) and 8.8560 to 8.8921 at the slow spacing (1.1079 to 1.1440, mean 1.1243) [T111.1];
- the floor is the target less the fall per tick times the gap's ticks: the `OnTick` read carrying the write's tick count sits one fall above the handler's pre-write read (the frame order is inference), and the next `OnTick` reads the written value unchanged [T111.3].

**The moodle.** It was not read: no harness command reads the PANIC moodle. Against the thresholds 6, 30, 65 and 80 (#2369), a target of 10 never brought the stat under 6 at either spacing, so the level is inferred unchanged. A target of 6.5 brought it under 6 in every game minute at both spacings (5.2459 to 5.4297 before each write at `DayLength` 1, 66 of 126 tick reads under 6; 5.3561 to 5.3883 at the slow spacing, 429 of 786) [T111.2]: the inferred level drops and returns once a game minute, under 6 for about half of each minute at either clock.

**What it changes in Decision 1 (c).**
- The arithmetic stands: the decay is linear and per game time, so the slow spacing does not deepen the sawtooth. The memo's "about 1.12" is the mean; the worst gap at `DayLength` 1 is 1.2556 (a 7-tick minute), so a flicker window above each threshold is about [T_h, T_h + 1.26) at `DayLength` 1 and [T_h, T_h + 1.14) at the slow spacing, not [T_h, T_h + 1.12).
- A floor at 10 or 20 is clear of every threshold by a wide margin, so for the mod's realistic floors (c) shows no inferred moodle flicker. A floor placed within about 1.3 above 6, 30, 65 or 80 flickers once a game minute; a design that must sit near a threshold can write the target plus the per-minute fall (about 1.26) so the floor stays at or above it.
- Still unread: the moodle itself (client and server), and vanilla's panic rise from zombies between writes.

## Appendix J. H1 — offline prototypes against the golden trace

Provisional ids map T113.n -> #(3410+n), minted (the Rows bullet).

### H1 — offline prototypes against the golden trace (memo section draft; rows T113.1–T113.6)

**Question.** Which behaviour-free refactors cut the slow minute's cost, by what share, and which slow-tier period K stays inside P2's fairer band?

**Method.** `testing/spikes/proto_run.py` (commit 024fe2d) runs the golden scenario (six stand-ins, 240 game minutes, about 1410 pipeline runs) on `server_host.Host` under lupa, with the mod tree pinned at 9578eb9 (`testing/spikes/proto/BASE.sha256`) and each prototype an overlay of whole-file copies under `testing/spikes/proto/<name>/`. Nothing under `mod/` or `testing/tests/` is touched. lupa is C Lua 5.1, not Kahlua, so every figure below is a share or a ratio of C-Lua time, never a server millisecond. The full outputs are `testing/spikes/out/proto-summary.md` and `proto-results.json`.

**The baseline profile (E1's offline half)** [T113.1]
- The unmodified copy reproduces the golden byte for byte, and so does the probed copy, so the probes change no state.
- Over 28200 pipeline runs, the seven heal passes are **52.1 %** of the pipeline (a repeat profile gives 52.3 %). The two Nutrients heals alone are 38.4 %.
- The Nutrients step is 57.3 % of the pipeline, and its record engine (`K.nutrients.minute`) is 10.9 %.
- The ten largest sub-blocks by share of the pipeline:
  1. `nutrients/heal.pre` 19.5 %
  2. `nutrients/heal.post` 18.9 %
  3. `nutrients/records` 10.9 %
  4. `metabolism/heal.pre` 4.2 %
  5. `metabolism/heal.post` 4.1 %
  6. `nutrients/acute` 3.2 %
  7. `metabolism/readActivity` 3.2 %
  8. `effects/heal.pre` 2.7 %
  9. `effects/heal.post` 2.5 %
  10. `nutrients/fluids` 2.1 %
- E1's rule is met: a heal total of 20 % or more adopts E2.
- **For H2:** the live sub-block timers should sit at least around the seven heals, `K.nutrients.minute`, `readActivity`, the acute and fluids blocks, and Strength's perk block (43.1 % of its step). Kahlua's table walk may weigh differently from C Lua's.

**Heal once (E2): the placement decides it**
- **heal1, one heal after the step (the plan's wording)** [T113.2].
  - It does **not** reproduce the golden. This is a finding under ruling 4, not a fix.
  - The first differing leaf is g2's stand-in calories at the minute-120 snapshot: heal1 −357.05911773776234 against the golden −478.88257398338897.
  - The cause: the golden's own minute-115 NaN in g2's body (`at`, `inDay`) reaches Metabolism's arithmetic before any heal.
  - With one NaN written into a record between minutes, the state matches the shipped tree in only 11 of 18 injections. Seven of them steer the stand-in's stores or the regeneration writes before the post heal stamps the field.
  - In five more, the step absorbs the NaN silently: `K.max` or an overwrite clears it, with no heal line and no heal count.
- **heal1pre, one heal before the step** [T113.3].
  - It reproduces the golden byte for byte.
  - Under all 18 input NaNs it matches the shipped tree's state and heal log. Each of the 17 mutants that remove its remaining heal is killed.
  - It saves **27.7 %** of the pipeline's C-Lua time: the paired median over 40 interleaved scenario runs, IQR 23.9 to 28.8. That is close to the 25.5 % base share of the heals it removes plus the lazy prefixes.
  - Its cost is the other class. A NaN the step's own arithmetic leaves now stays in the record until the next minute (6 of 6 injections).
  - In 1 of 6 (`body.fm` out of the energy step) the state changes (`proto-results.json` `mutation.arithmetic[0]`). Under heal1pre that NaN spreads in the same minute to 16 fields in body, nutrients, fluids, acute and effects: `thiamine.p`, the iron pools, `acute.bac/alc/glyc/g`, `fluids.dehydPct/thirstTarget/viewPct` and `effects.intoxTarget`.
  - The weight step skips its write for that minute, and the next minute's pre-step heals reset those pools fresh: BAC, glycogen and the iron pools. The shipped tree never makes that loss, because Metabolism's post heal contains the NaN.
  - The arithmetic injections are synthetic and sampled (6 fields), so "5 of 6" is not a rate.
  - `fm` cannot in fact go NaN out of the partition step: `K.max(NaN, FM_MIN)` returns `FM_MIN` (`NR_Kernel_Partition.lua:174`, `NR_Kernel.lua:20`), and `K.energy.minute` never writes `fm`.
  - That the mirror or a save could read such a NaN within that minute is inference, unmeasured.
- **The remaining heal is still the largest block.** In heal1pre, `nutrients/heal.pre` is 25.8 % of the pipeline.
  - The walk itself is the cost: `pairs` over 27 keys of 11 fields, plus fluids and acute. Building the prefix strings is not.
  - A cheaper heal is the next target (inference, untested): one finiteness check on a running sum, or healing only the fields the step wrote.
- **What Plan 11 can take:** heal before the step, once, with lazy prefixes.
  - Keep a post-step guard only where a step's NaN would leak in the same minute: Metabolism's masses, at least.
  - Or accept a one-minute NaN window, which needs Angus's ruling.
  - Before settling the guard, enumerate every cross-step read and inject each one: Nutrients reads `body.lm`, eeDay, alcDay and dayIndex; Effects reads the fluids and acute fields.

- **The review's probe-free re-measurement of the heal share** (probes around the pipeline only, no probes inside it).
  - All seven heals removed saves **55.7 %** of the pipeline (IQR 52.3–57.8). The two Nutrients heals alone save 41.6 % (IQR 39.8–45.4).
  - The profile's 52.1 % stays the profile figure (T113.1); this is the cross-check, and it agrees within the profile's probe error.
- **Kahlua points for a shipped version.**
  - Kahlua has no weak tables (`./pz.sh grep '__mode'` finds nothing), so a shipped hoist drops its metatable; the prototype's weak keys are offline only.
  - `string.byte` exists (`StringLib.stringByte`), so the slot hash can use it.

**Hoisted constants (E3)** [T113.4]
- The variant caches the dial exponent across minutes, reads the ladder once per record and computes one `exp(-dtD)` a pass. It reproduces the golden byte for byte.
- Its saving is not distinguished from zero: 0.3 % of the pipeline (paired median, IQR −2.5 to 2.7).
- The record engine's block falls from 23.54 to 21.22 C-Lua µs a run, about 1 % of the pipeline. It is a correctness-neutral tidy, not a hitch fix.

**A slow tier (E4)** [T113.5, T113.6]
- **The design.** The 27 nutrient records and the effects rebuild run every K minutes in a per-player slot (hash(username) mod K). The absorbed and ingested amounts and dtM are summed between slow steps. At K = 1 the tier reproduces the golden.
- **How it is judged.** Against k = 1, with P2's `compare` and Appendix H's fairer band.
  - 550 band and grade paths are followed minute by minute.
  - A band change matches when it lands at most K online minutes off.
  - A change within K minutes before g4's departure or the run's end is clipped.
- **K = 5 is the largest K of 5, 10, 30 and 60 with no band or grade flip.**
  - Every band change lands at most 4 minutes late.
  - One change is clipped: g4's insulin band 6, crossed at minute 148, two minutes before its departure. This is P2's k = 5 finding again.
  - Of the 896 leaves outside the fairer band, 894 are explained by the tier's delay. The 2 that are not are g1's vitamin A pool p, a drift of about 3e-5 against a 1.45e-5 band.
- **K = 10 never shows g4's exercise band 2** (slot 12, minutes 17–24 in the base run). K = 30 and 60 skip more.
- **The rebuild gate causes the flips, not the records** [T113.6].
  - With the rebuild check kept every minute (records only on the slow tier), no band or grade leaf changes at any K.
  - The unexplained continuous leaves grow from 2 and 4 at K = 5 and 10 to 67 and 81 at K = 30 and 60. They are mostly the one-day excess sums e24, which lose their decay inside the summed step.
  - No nutrient grade moves in the 240-minute scenario, so the records' own grade delays are untested.
- **The share it takes off the minute.**
  - The base shares of the records and the rebuild are 11.7 % of the pipeline.
  - At K = 5 the tier moves **7.2 %** off the average player-minute: the paired median, IQR 3.8 to 9.4, against 9.3 % by arithmetic. The summing it adds costs 1.6 %, every minute.
  - At K = 10, 30 and 60 it moves 9.3 %, 10.1 % and 9.9 %.
  - The slot minute still pays the records whole, so the tier lowers the average, not the worst player-run.
- **What Plan 11 can take:** the records alone on a slow tier, with the rebuild check kept every minute.
  - It takes about a tenth off the average minute (offline, C-Lua).
  - It needs a stored accumulator (this prototype's is transient) and an e24 that integrates the intake's decay within the step.
  - The heal fix is worth roughly three times as much (offline, C-Lua).

**Determinism.** Every variant's trace was run twice, with identical sha256:
- the golden's `df7806d8…daa9e8b3` for base, heal1pre and hoist;
- `b91803cb…` for heal1;
- `381c98bd…`, `df69168f…`, `df689d8e…` and `15ff263b…` for slowK at K = 5, 10, 30 and 60.

The profiles' shares agree to 0.2 points between two 20-run profiles.

**What this does not settle.**
- C Lua is not Kahlua: H2's live timers give the milliseconds.
- One scenario of 240 minutes, with no nutrient grade moving.
- K from 6 to 9 was not run.
- The one-minute NaN window under heal1pre is unmeasured live.

**Page sentences for the controller** (owner `docs/areas/testing-your-mod.md#walls`, one per row):
- T113.1: "An offline profile of the golden scenario in lupa, with the trace unchanged, puts the seven heal passes at about half of the slow minute's C-Lua time, and the record engine at a tenth [T113.1]."
- T113.2: "Healing only after the step does not keep the golden trace: a NaN written between minutes reaches the step's arithmetic before the heal [T113.2]."
- T113.3: "Healing once before the step keeps the golden trace and every input-NaN heal, and cuts the minute's C-Lua time by 27.7 %; a NaN the step itself makes may spread to later steps and reset their fields at the next heal [T113.3]."
- T113.4: "Hoisting the record engine's constants keeps the trace but saves nothing measurable offline, C-Lua [T113.4]."
- T113.5: "A slow tier that also gates the effects rebuild keeps every band change only up to K = 5; at K = 10 a short exercise band is never shown [T113.5]."
- T113.6: "With the rebuild check kept every minute, the records alone on a slow tier change no band in the golden scenario, but their one-day excess sums drift beyond the band from K = 30 [T113.6]."

## Appendix K. H2 — sub-step and burst-source costs, live (runs x242 and x242b)

Provisional ids in this appendix are its source memo's own; they map at the mint as T114.n -> #(3456+n), T115.n -> #(3470+n), T116.n -> #(3484+n), T117.n -> #(3493+n), T120.n -> #(3496+n).


## H2 — sub-step and burst-source costs, live (memo section; runs x242 and x242b)

Two runs on the same staged instrument copy (`release/hitch-x242/`, the tree at `9578eb9` with the x242 instruments, MANIFEST `c86e295a…`). `x242-20261007-151339` (driver `fadf200`) was stopped by the host for memory at the start of its phase C; by ruling H2-1 it stands for phases A and B. `x242b-20261007-152926` (driver `198fd27`, 645 s wall) ran the unreached phases C, D, E and F. Fixture `two`, Nutrition false, DayLength 1, n = 1 each; every per-run figure is a whole-ms total over its runs. Provisional rows `T114.1`–`T114.14` (delta `task-H2-claims-delta.tsv`).

### Where the minute's time goes (x242 A, in play, sub-blocks on)

- The minute is 356 ms over 244 runs: 195/122 for admin plus 161/122 for bob, 1.459 ms a run [T114.1]. The two players differ 1.21x, inside the noise. By step: nutrients 173, metabolism 79, effects 38, kinetics 18, strength 15, weight 13, reconcile 9, bus 2, fast 0 ms.
- The Nutrients heal pair is the top two sub-blocks: heal.pre 62 and heal.post 39 ms, 28.4 % of the minute [T114.2]. The seven heals together are 143 ms (40.2 %). Next come nutrients/records 34, metabolism/readActivity 32 (9.0 %), nutrients/acute 20, and metabolism/heal.post 15 and heal.pre 11 ms.
- **Against H1:** the Nutrients heal pair is the top two blocks on both hosts, 38.4 % offline and 28.4 % live. This is not a Kahlua effect. The shares differ for three reasons:
  - the live denominator holds Java-interop blocks that lupa stubs (`metabolism/readActivity` 9.0 %);
  - the scenarios differ (H1's six golden stand-ins against two healthy players);
  - about 30 bracket pairs were on.
- **Timer overhead:** the un-bracketed remainder of the four sub-timed steps is 20 of 356 ms (nutrients 6, metabolism 6, effects 6, strength 2). That bounds the timer cost outside the brackets at about 5.6 %. x231's A without sub-block timers ran 1.558 ms a run against 1.459 here, but x231 carried an `NR.call` counter, so that comparison is a sanity bound only.
- **15 %-of-step refactor targets** [T114.3]: nutrients heal.pre (35.8 % of its step), heal.post (22.5 %) and records (19.7 %); metabolism readActivity (40.5 %) and heal.post (19.0 %). The effects (heal.post, heal.pre, scalars) and strength (perk, carry) targets rest on 5–9 ms totals and are at the noise.
- **The in-play day close:** four close runs took 1 or 2 ms against a plain p50 of 1 ms [T114.4]. n = 4 at 1 ms does not settle the 3x rule; the bench below does.

### A deficient player (x242 B)

bob held at vitamin C and iron grade 4 for 60 game minutes: 93 ms over 63 runs against admin's 89 over 63 [T114.5]. The 4 ms gap is inside the 1 ms noise and crosses players (1.21x apart already in A). bob against himself is 1.320 ms a run in A and 1.476 in B. The grades were read 7 to 10 game minutes after the seeds (vitC.g at about 7.7, iron.g at about 10), the wait having reached 2 bench minutes after `profStart`; the counter's measured rate is 0.627 s a game minute against DayLength's nominal 0.625. Their change began before the profile started. So B is the steady deficient minute, and the onset is unmeasured. `effects.stats.rebuilds` is server-wide; bob's own rebuilds in the window are the two composes of his accumulator. **Reading: no burst at 1 ms resolution; the onset unmeasured.**

### The burst sources (x242b C, 1000 interleaved bench sets on copies of admin's record)

| Kind | ms / runs | ms a run | Plan rule | Verdict |
|---|---|---|---|---|
| typical minute | 1134 / 1000 | 1.134 | — | see the note below on the x242 A comparison |
| one day close | 1022 / 1000 | 1.022 | over 3x typical → scheduler | 0.901x: does not fire [T114.6] |
| seven-close catch-up | 1053 / 1000 (7000 closes) | 1.053, max 5 | — | no extra cost visible [T114.6] |
| first sight, measured parts (load + ensureBody + hooks, re-hoist skipped, sends stubbed) | 698 + 74 + 89 / 1000 | 0.861, a floor | over 2 ms → queue | does not fire [T114.7] |
| mirror send (138-key payload) | 102 / 1000 | 0.102 (60 sends 6.12 ms) | 60 over 5 ms → jitter | **fires** [T114.8] |
| payload build alone | 42 / 1000 | 0.042 | — | — |

- The 0.777 ratio of the bench's typical run to x242 A's 1.459 ms compares an unprofiled bench with a profiled in-play minute. The profiled bench typical run (CS) is 1.225 ms, 0.840 of A. Profiled against unprofiled typical is 1.080x (about 0.04, approximate either way), a direct estimate of the whole timer overhead, above the 5.6 % outside-the-brackets bound under Timer overhead [T114.1].
- A close or catch-up run read 0.08 to 0.11 ms cheaper than the typical run (close 112 ms under, catch 81 under over 1000 runs), beyond the truncation noise (about 22 ms either way on a difference over 1000 runs), for an unmeasured reason; a difference is not a close's cost [T114.6].
- The day close is not a burst source: `metabolism/closeDay` took 20 ms over 1400 closes in the profiled sets.
- The one rule that fires is the send: at 60 players a same-frame mirror push is about 6 ms. That is the per-send total times 60, not a 60-player reading. A per-player jitter (or spreading the push) is warranted.
- First sight's hooks ran with Fast's re-hoist skipped, because admin's handle existed, and sends were stubbed. The 0.861 ms is the measured parts only, a floor [T114.7].

### The client tooltip (x242b D)

`T.entryFor` on the same item costs 7–18 µs a call over 1000 calls (9.4 and 14.7 µs over 10000), against the 50 µs rule [T114.9]. A build each call costs 108–218 µs. The rule does not fire: the same-item check need not move.

### The global store (x242b E, H6's arm)

**The save** [T114.11, T114.12] (`Saving GlobalModData` to `Saving finish`, two console saves about 32 s apart at each size, `phases.E.E1.0.saves[k].save.wall` 270.3 and 302.4 s):

| Seeded records | First save (ms) | Second save (ms) | `global_mod_data.bin` (bytes) |
|---|---|---|---|
| 0 (the session's first console save) | 11 | 9 | 21633 |
| 100 | 22 | 16 | 1109333 |
| 500 | 153 | 50 | 5460133 |
| 2000 | 2770 | 193 | 21775633 |

- The second save at 500 adds 41 ms over 0, so H6's 25 ms rule fires. The save is a hitch source in its own right, and the store's move or pruning is a performance fix too.
- The first save at a new size pays far more. At 2000 it made a 2990 ms server frame and logged `Pausing clients…`. That the first save at a size pays the 512 KiB buffer-growth restarts (#3421) is inference. The `Pausing clients` line came 2769 ms after `Saving GlobalModData` began, so clients were told to pause only after the stall (#3421). In practice the first save after the store grows past its last high-water mark is the hitch, and an autosave after a long uptime is exactly that case.
- Each record is 10877 bytes on disk against 10821.8, H6's record with its store entry and the figure the driver graded against (ratio 1.0051). Of the 55 B gap, about 4 B is the nine-character seeded username against admin's five; about 51 B is admin's live record against H6's offline mean of six golden records (10877 lies within their 10684 to 10883, and every seed copies one record), the attribution being inference. The cleanup save returned the file to 21633.

**The request** [T114.13, T114.14]:

- At 2 and 60 records the table arrived whole (2 and 60 keys, 23 and 44 ms). The frames around each request peaked 4 and 5 ms over a 100 ms median, which is the idle jitter, so the request's cost is not distinguishable from the 4 to 5 ms idle jitter in the frame period. H6's 5 ms griefing rule does not fire at 60 records (the driver's E2 verdict reads `falsified` on this clause alone: the pre-registered prediction, more than 5 ms, was falsified at exactly 5 ms).
- At 500 records (run after F) the request failed on both sides, and bob stayed in the session:
  - the server logged a `BufferOverflowException` in `GlobalModData.receiveRequest` (`:193`);
  - bob's client logged a `BufferUnderflowException` in `GlobalModDataPacket.parse` (`:53`);
  - no receive event fired.

  This is #3419's truncated reply, live. H6 also expected an `IllegalMonitorStateException` line; none appeared, and the handler logged the `BufferOverflowException` itself, so that inference of #3419 is not borne out. #3417's table also reached a release client at 2 and 60 keys live [T114.13], so its "not exercised on a live server" is superseded.
- The privacy finding stands (any client reads every record, whole up to about 90 records by H6's inference, and 60 arrived whole here). The hitch-vector half is not measured at 60 records.

### Ghost calibration (x242b F, for H3)

| | Ghost ms / 40 | Real ms / 40 | Ratio | Zero-dt (g/r) | Failures (g/r) | Reason |
|---|---|---|---|---|---|---|
| Unfed | 35 | 45 | 0.778 | 0 / 0 | 0 / 0 | none |
| Fed | 45 | 46 | 0.978 | 0 / 0 | 0 / 0 | none |

Both benches had 83 waits and 20 minute events [T114.10]. **H3 scales by the fed ratio, 0.978**: a fed ghost costs a real player's minute within the bench's resolution (40 pairs at 1 ms).

### For Plan 11 and H3

1. Spread or jitter the mirror push (T114.8).
2. Take the store out of global modData for privacy (H6), and also for the save hitch: about 2.8 s at 2000 records on the first save at that size, and 41 ms over baseline at 500 on every later save (T114.11).
3. Heal-once remains the largest lever (T114.2); readActivity is the next live target. The effects and strength targets are at the noise.
4. The day close, first sight, a deficient player and the tooltip are not burst sources at these rules.

## Appendix L. H3 — the scheduler shoot-out (four x243 sessions)

Provisional ids in this appendix are its source memo's own; they map at the mint as T114.n -> #(3456+n), T115.n -> #(3470+n), T116.n -> #(3484+n), T117.n -> #(3493+n), T120.n -> #(3496+n).


## H3 — the scheduler shoot-out at N = 20, 40, 60 (memo section; runs x243a, session b, x243c, x243d)

Four short live sessions on the uninstrumented staged copy `release/hitch-9578eb9/` (MANIFEST `c86e295a…`), fixture `two`, Nutrition false, gclog on, n = 1 each, one host:

| session | run id | driver commit | content |
|---|---|---|---|
| a | `x243a-20261007-160539` | `a0c5af1` | DayLength 1, N = 60: idle, then budget10, rr2, burst, budget5, drainTicks, budget15, rr5 |
| b | `x243a-20261007-162255` (sic) | `da3fdcb` | DayLength 1: idle, then burst20, drainTicks20, budget10_20, budget10_40, burst40, drainTicks40, shipped60 |
| c | `x243c-20261007-163949` | `c23586a` | 37 ticks a game minute (`time.multiplier 0.1674`), N = 60: idle, rr5, budget10, burst, drainTicks; then `settimespeed 30`: fastIdle, fastBudget10, fastBurst |
| d | `x243d-20261007-165535` | `b031fc9` | DayLength 1: the empty-check A/B (none, empty, empty, none), then N = 60 across 07:00 under budget10 and burst |

Provisional rows `T115.1`–`T115.14` (delta `task-H3-claims-delta.tsv`, owners on `platform/performance.md#costs`, `#measure`, `#gc`).

**Session b's id.** Driver b was a copy of driver a and kept `PREFIX = "x243a"` and `PROFILE = "x24-shootout-a"`. So its run id carries `x243a`, and it booted `x24-shootout-a.toml`. That profile's content equals `x24-shootout-b.toml` except for the header comment and `description`. The arms, predictions and grading are session b's. The defect was found after the run, so the driver was not edited. Drivers c and d were fixed before their commits.

**Deviation from the amendments: four sessions, not three.** The A/B (2 × 3000 frames) alone is about 10 minutes, so session a with the A/B would have run about 27 minutes against the 15-minute cap. The A/B and the day-boundary arm went to a fourth session, d. Every session ran 909–996 s of wall, boot included. Free memory fell from about 20 GB to 0.55–1.17 GB in each, as in x242b. No session was killed.

**Deviation: arm sizes.** The fast arms hold about 610 frames each (`summaries.fastIdle.frames`, `fastBudget10`, `fastBurst` in x243c) and the day-boundary arms 515 kept frames each (`summaries.db_budget10.frames`, `summaries.db_burst.frames` in x243d), under the amendments' sizing rule of at least 1000 frames an arm. Their p99s rest on fewer frames than the rule asks.

**How the arms were run.** Every ghost was loaded with `feed`. Between arms: `ghost.stop`, a fresh `ghost.load`, then `ghost.stats reset`. drainTicks got `tpm<n>` from `TK.H0.tpmSeen`, and `tpmSource` was never "none". `ghost.bench` was never called. The **two real players stayed on the mod's own drain** throughout; ghosts are cost, not behaviour.

**The cost-equivalent N.** On x242b's calibration, a fed ghost is 0.72–1.0 of a real player, so N = 60 is a cost-equivalent 43.8–60 players. Batch-timed ghost cost read 0.767–1.149 ms a run across the arms (most 0.80–0.90). shipped60's 1.427 is one ghost a batch, dominated by 1 ms truncation.

### The populations (amendments' rules)

- **Ring frames** (`tick.ring`, about 1020 an arm). Readings: `busy` (frame start to the end of `OnTick`, the ghost batches inside it) and `endPeriod` (the end-to-end period).
  - Kept frames are every frame minus those that overlapped the ring arm or the `perf.local read` bus step.
  - The `tick.ring read` writes its document after its own ring's last frame, so it is in no ring and in no kept window.
- **Perf windows** (`perf.local` max-update-period, the hitch reading per #3443; about 95 kept an arm). The first sample and any window over a bus step are dropped.
  - Below 100 windows, the window p99 by nearest rank IS the window max. So every "longest window" below is both the p99 and the max of that population.
- **Adds** are the arm's figure minus the same session's idle arm, over the same population. The fast arms' baseline is fastIdle; session d's DB arms' baseline is none1.
- **Total a game minute** is the kept busy sum over the kept minute frames.

### N × scheduler × spacing

Units: ms. "Worst" is the longest engine window (= its p99), then the longest end-to-end period, then the max busy. "p99" is the ring endPeriod's p99, then busy's p99. "Adds" are over idle: the period's p99, then the longest window. "Total" is busy a game minute over idle. "Starved" is starved ghost-minutes over minute events. "Stale" is the most game minutes a ghost waited. "Ghost" is ms a run.

| N | sched | spacing | worst (window / period / busy) | p99 (period / busy) | adds (p99 / max) | total | starved | stale | ghost |
|---|---|---|---|---|---|---|---|---|---|
| idle | — | DL1 (a) | 115 / 111 / 13 | 108 / 10 | — | (12.7) | — | — | — |
| 60 | burst | DL1 | **188** / 188 / 88 | 170 / 70 | **+62 / +73** | 46.9 | 0 / 151 | 1.13 | 0.868 |
| 60 | rr2 | DL1 | 146 / 147 / 48 | 140 / 40 | +32 / +31 | 27.2 (29 a minute) | 0 / 162 | 2.13 | 0.990 |
| 60 | rr5 | DL1 | 123 / 122 / 23 | 117 / 16 | +9 / +8 | 4.4 (12 a minute) | 0 / 165 | 5.10 | 0.824 |
| 60 | drainTicks | DL1 | 119 / 119 / 22 | 115 / 19 | +7 / +4 | 51.1 | **176 / 167** | 1.28 | 0.959 |
| 60 | budget5 | DL1 | 141 / 141 / 43 | 108 / 12 | 0 / +26 | 21.6 (21.5 a minute) | **6079 / 167** | 4.12 | 1.149 |
| 60 | budget10 | DL1 | 124 / 123 / 26 | 113 / 16 | +5 / +9 | 47.3 (56.75 a minute) | **207 / 166** | 2.08 | 0.857 |
| 60 | budget15 | DL1 | 134 / 134 / 31 | 121 / 19 | +13 / +19 | 41.8 | 0 / 165 | 1.11 | 0.805 |
| idle | — | DL1 (b) | 115 / 114 / 15 | 107 / 8 | — | (11.8) | — | — | — |
| 20 | burst | DL1 | 135 / 135 / 36 | 125 / 26 | +18 / +20 | 14.3 | 0 / 165 | 1.11 | 0.897 |
| 20 | drainTicks | DL1 | 115 / 115 / 15 | 108 / 10 | +1 / 0 | 14.9 | 0 / 167 | 1.12 | 0.967 |
| 20 | budget10 | DL1 | 123 / 123 / 21 | 116 / 16 | +9 / +8 | 10.8 | 0 / 166 | 1.12 | 0.799 |
| 40 | burst | DL1 | 151 / 151 / 51 | 141 / 41 | +34 / +36 | 25.8 | 0 / 161 | 1.09 | 0.800 |
| 40 | drainTicks | DL1 | 120 / 120 / 23 | 111 / 13 | +4 / +5 | 27.9 | **88 / 166** | 1.28 | 0.859 |
| 40 | budget10 | DL1 | 139 / 139 / 40 | 115 / 15 | +8 / +24 | 29.2 | 0 / 167 | 1.12 | 0.850 |
| 60 | shipped (ruling 3) | DL1 | 117 / 117 / 16 | 107 / 7 | 0 / +2 | 1.9 (4.26 a minute) | **6180 / 116; 53 of 58 never ran** | 115.7 | (1.427) |
| idle | — | DL4 (c) | 119 / 120 / 18 | 105 / 5 | — | (47.5) | — | — | — |
| 60 | burst | DL4 | **161** / 161 / 60 | 149 / 50 | **+44 / +42** | 24.5 | 0 / 29 | 1.01 | 0.794 |
| 60 | rr5 | DL4 | 121 / 121 / 20 | 113 / 14 | +8 / +2 | 0.6 (12 a minute) | 0 / 28 | 5.01 | 0.896 |
| 60 | drainTicks | DL4 | 113 / 112 / 11 | 107 / 7 | +2 / −6 | 43.2 | 0 / 29 | 1.02 | 1.107 |
| 60 | budget10 | DL4 | 121 / 120 / 21 | 112 / 13 | +7 / +2 | 29.9 | 0 / 29 | 1.02 | 0.831 |
| idle | — | fast (c) | 145 / 145 / 47 | 113 / 16 | — | (6.2) | — | — | — |
| 60 | burst | settimespeed 30 | 134 / 134 / 76 | 123 / 67 | +10 / −11 | 43.1 | 0 / 623 | 4.82 | 0.767 |
| 60 | budget10 | settimespeed 30 | 138 / 138 / 52 | 116 / 25 | +3 / −7 | 8.4 (10.3 a frame) | **29715 / 623** | 42.8 | 0.854 |

Notes on the table:
- **DL4 minute frames.** At 37 ticks a game minute an arm holds 27 or 28 minute frames, so the minute-frame p99 is not reachable. The table reads the ring's frame p99 (about 1030 frames) and the max.
- **Day closes inside arms.** The mod's 07:00 day close fell inside budget15 in session a. Its longest frame (31 ms busy, 134 ms period) started about 2 s after the interpolated 07:00 (inference). It also fell inside drainTicks40 in session b. Each fast arm crossed 07:00 about twice.

### Decision 6 (ruling 2), provisional

These are H3's answers on ruling 2's thresholds as they stand. H4 may rewrite the thresholds by ruling before Task M. Populations:
- every **p99** threshold is read on the ring's end-to-end period (about 1020 frames, adds over idle);
- every **max** threshold, and "over 133 ms", on the engine's per-window longest frame (adds over idle);
- the totals on ring busy a game minute.

**(a) the one-event design: excluded.** The burst itself must stay at most 25 ms at N = 60.
- At DayLength 1 it adds 73 ms to the longest window (188 ms) and 62 ms to the period's p99. Its minute frames read busy 50/81/88 ms, and every one of 95 windows held a frame over 133 ms.
- At the DayLength 4 spacing it adds 42 ms (161 ms) and 44 ms at p99.
- Across 07:00 it adds 58 ms (175 ms). The first minute frame after the interpolated 07:00 is 67 ms busy, 1.34× the arm's minute p50, and 11 ms of it lay outside its 56 ghost ms. That it is the day close's frame is inference: the previous minute frame started 61 ms before the interpolated close, inside the interpolation's one game minute (`summaries.db_burst.close`). Either way, the day close is not a separate burst.
- Growth is linear: the minute frame's busy p50 is 18, 32 and 50 ms at N = 20, 40 and 60.

**The alternative clause of (b) holds.** The burst adds more than 33 ms and pushes a frame over 133 ms at both spacings.

**(b) the budgeted per-tick scheduler: it meets the peak clauses and the alternative clause where measured; adoption is pending.** The no-aggravation clauses (the empty check and the total at DayLength 4) and a minute-sized budget at both spacings are not yet read. Each budget at N = 60:

| budget | spacing | adds at p99 (≤ 20) | adds at max (≤ 25) | starvation | total vs the burst (≤ 1.1×) |
|---|---|---|---|---|---|
| budget10 | DL1 | +5 ✓ | +9 ✓ | **starved** | 47.3 vs 46.9, 1.01× ✓ |
| budget10 | DL4 | +7 ✓ | +2 ✓ | none ✓ | 29.9 vs 24.5, **1.22×** |
| budget15 | DL1 | +13 ✓ | +19 ✓ | none ✓ | 41.8, 0.89× ✓ |
| budget5 | DL1 | — | **+26 ✗** (one frame 40 ms outside the ghost runs) | starved every minute | — |

- **budget10 at DayLength 1** runs at the edge of capacity. It served 56.75 of the 58 ghosts a minute (207 starved ghost-minutes over 166 events, 34 of them), each ghost at most one event late (2.08 game minutes). The day-boundary session repeated it: 166 over 86.
  - Mechanism (inference, from the ring's per-frame `runs` and `ghostMs`, `phases.budget10.ring_doc.frames_list`): both caps bind. Run-capped frames ran mostly 11–13 ghosts in 7–9 ghost ms; time-capped frames mostly 6–10 ghosts in 10 ms. That averages 9.61 runs a run frame (`summaries.budget10.ghost.meanRunsPerRunFrame`).
  - The ring's minutes were 6 ticks in 119 of 163 and 7 in the rest. A 6-tick minute at 9.61 runs a tick serves about 57.7 of the 58 due.
  - So the starvation is a design property of a 10 ms budget at this load: bounded lateness (each ghost at most one minute event late), not loss (inference).
- **budget10's 1.22× at DayLength 4** is a 5.4 ms a game minute difference, 0.15 ms a frame. Session d's two no-load arms drifted 0.62 ms a frame over 10 minutes, about 23 ms a game minute at 37 ticks. So the 1.22× is **not resolved** by the totals.
  - Drift-immune reading (inference): the ghosts' own batch-timed ms over the arm's minute events (`summaries.<arm>.ghost_ms_per_minute_event`) reads 48.21 under budget10 against the burst's 46.07 at 37 ticks, 1.046×. At DayLength 1 budget10 reads 48.64 and budget15 46.70 against the burst's 50.32, 0.97× and 0.93×. So the 1.22× is drift. This reading leaves out any scheduler cost outside the runs, which the empty check bounds near zero.
- **budget15 at DayLength 1** is the one budget that met every bound measured with no starvation. Its longest frame was probably the day close. budget15 was **not run at the DayLength 4 spacing** (a gap).
- **budget5**: one 43 ms frame (ring frame 4746) set the 141 ms window (`summaries.budget5.perf_max`). Its busy time outside the ghost runs was 40 ms (3 ghosts, 3 ghost ms). Frames like it (30 ms or more outside the ghost runs) appeared in 3 of the 22 loaded slow arms (this one, session b's `budget10_40` frame 4635, x243d's `empty2` frame 4609) and in 0 of the 5 no-load arms, cause unknown. So the max is not attributed to the 5 ms budget. budget5 still fails on starvation.
- **The empty-queue check (x243d A/B, about 3000 frames a side): ≤ 0.1 ms a frame is not contradicted and not resolved.**
  - The A/B reads −0.052 ms a frame by the totals and −0.077 by the quiet frames.
  - The two pairs read −0.238 and +0.133, and the drift is about 0.6 ms a frame over the session.
  - A per-tick early-out sits below this host's session-to-session resolution of about ±0.2 ms a frame.
  - Drift-immune reading (inference): in A-B-B-A order the arms read 1.873, 1.635, 1.389 and 1.256 ms a frame, the empty arms net of their ghost ms (`summaries.<arm>.busy_sum` less `ghostMs_sum`, over `frames`). A fit of a linear drift plus an empty-side offset gives −0.053 ms a frame with residuals of at most 0.018. That weakly supports ≤ 0.1 ms.

**(c) the round-robin of m = 2: excluded on the bounds.** It adds 32 ms at p99 and 31 ms at the max (146 ms) at DayLength 1. rr5 meets the bounds (+9/+8), but it serves each ghost once in five minutes (5.1 game minutes stale) and is not a design under ruling 2.

**Provisional answer.**
- (a) and (c) are excluded.
- (b) meets the peak and alternative clauses where measured.
- Adoption of (b) is pending:
  - the no-aggravation clauses: the empty check (weakly supported, below) and the total at DayLength 4 (drift-immune reading below: 1.046×, inside 1.1×, inference);
  - a minute-sized budget at both spacings. At N = 60 and DayLength 1 a 10 ms budget starves at the margin, and a 15 ms budget does not. One budget expressed per minute (N × per-run ÷ ticks a minute, with headroom) would serve both spacings, but that is inference, unmeasured.
- H4 adds budget15 at the 37-tick spacing, and repeats.

**drainTicks** (the drafted per-tick spread) met the peak bounds everywhere. It starved at DayLength 1 at N = 40 (88) and N = 60 (176): ceil(N / T) with T taken from the last minute's 6 or 7 ticks under-serves a 6-tick minute (inference). It did not starve at 37 ticks. Its totals ran 1.09× (DayLength 1) and 1.76× (DayLength 4) the burst's, both inside or near the drift.

### The other arms

- **Fast clock** (`settimespeed 30`, every frame a minute frame).
  - The burst ran 58 ghosts every frame at busy 48/67/76 ms, yet the end-to-end period stayed at 123 ms p99, and the longest window was 134 against fastIdle's 145. A load present on every frame moves every frame's end alike and does not lengthen the period while busy stays under 100 ms (inference).
  - budget10 under the fast clock served about 10.3 a frame against 58 due. It starved 29715 ghost-minutes over 623 events, with ghosts up to 42.8 game minutes stale.
  - So under a fast clock the budget trades staleness for nothing the frame needed. A fast-clock rule (run all when every frame is a minute frame, or scale the budget to the clock) is for Plan 11 (inference).
- **Shipped drain (ruling 3), starvation only.** It ran 4.26 ghost minutes a minute event, about 6.27 ticks less the two real players' ticks. It dropped 6180 queued ghost-minutes over 116 events, and 53 of 58 ghosts never ran (115.7 game minutes stale). Ruling 3 is confirmed live. #3444's rule and #3439 have their live reading here (a status note for Task M).

### GC against the minute frames (X6)

- ZGC pauses inside the measured arms were at most 0.695 ms over the four sessions; most were under 0.06 ms.
- Every allocation stall fell at 32.4–35.1 s of the server JVM's uptime (a 34.7–35.1, b 34.2–34.6, c 34.1–34.4, d 32.4–32.9; `gc.events[*].up_ms`), during boot, before any arm: 29–36 a session, the longest 274.56 ms.
- No minute frame has a pause or stall within 1 s that could explain its length. The gc.log stamps are JVM uptime, mapped to epoch from the driver's launch epoch, aligned within about 1 s.
- The minute frames' cost is the mod's work, not the collector.

### Readings for Task M

- The burst's per-minute frame at N = 60 is 50 ms busy at p50 and 81–88 at the top on this host. That is about 0.86 ms a ghost run, linear in N, and below #3440's 73.7–103.3 ms arithmetic on in-play runs. Its effect on the engine's frame is +62–77 ms at DayLength 1.
- Every live number is one host, one session each; idle drift between arms in one session is about 0.6 ms a frame. Totals compared across arms are reliable only to about ±4 ms a game minute at DayLength 1 and ±23 at 37 ticks.
- H4 should judge whether a 124–139 ms longest window (budget10/15) is noticeable against a 188 ms one (burst). The ruling thresholds stand until then.


**Re-review residuals (H3 fix-1 re-review).** Spikes of 30 ms or more outside the ghost runs also appear in the fast arms, the fast idle arm included (fastIdle frame 5856, 47 ms busy with no ghost; fastBudget10 frame 7049), so they are not unique to loaded arms; the slow-arm count (3 of 22 loaded, 0 of 5 no-load) holds only in its slow-arm scope. The 1.046x drift-immune total rests on ghost ms alone, so it assumes the scheduler costs little outside its runs, the weakly supported 0.1 ms bound. budget10's 11-13 runs in 7-9 ms describes most run-capped frames, not a bound (one frame ran 14 in 12 ms). The x243d guide's A/B line should carry the same one-degree-of-freedom caveat as T115.13; Task M applies it.

## Appendix M. H4 — does a player notice (three x244 sessions)

Provisional ids in this appendix are its source memo's own; they map at the mint as T114.n -> #(3456+n), T115.n -> #(3470+n), T116.n -> #(3484+n), T117.n -> #(3493+n), T120.n -> #(3496+n).


## H4 — does a player notice the minute burst; Decision 6's evidence completed (ruling H4-1)

Three live sessions on the uninstrumented staged copy `release/hitch-9578eb9/` (MANIFEST `c86e295a…`), fixture `two`, Nutrition false, gclog on, N = 60 (58 fed ghosts), n = 1 each, one host, both clients on the server's host:

| session | run id | driver commit | spacing | client geometry |
|---|---|---|---|---|
| a | `x244a-20261007-174509` | `48d7378` | DayLength 1 | players 248 tiles apart (spawn points): admin sees bob as a far player only; bob sees nobody |
| b | `x244b-20261007-181148` | `71271bc`, edited once before its boot at `dbb78a8` | 37 ticks a game minute (`time.multiplier 0.1674`) | as a: the RCON `teleport` replied an empty string and moved nobody |
| c | `x244c-20261007-182845` | `6df7f07` | DayLength 1 | admin teleported 1.58 tiles from bob (debug menu `/teleportto` through `lua.call` on admin's client) |

Arm order in every session: idle, burst, budget15, burst, budget15, budget15, burst; each arm about 1020 server frames (101.5 s); both clients paced ±6 tiles. Harness: `world.posring` (client), committed `e15a9ca` before any run. Provisional rows `T116.1`–`T116.9` (delta `task-H4-claims-delta.tsv`; owners `platform/performance.md#measure`, `#costs`, `platform/harness.md#driven-client`).

**Deviation: a third session.** The amendments name two sessions. Sessions a and b never brought the players together (fixture `two` spawns them 248 tiles apart, and the RCON `teleport` I added to driver b before its boot did nothing), so their client reading is only admin's far-player stream (whole-tile positions, a stamp every 400 ms, bob's client blind). Session c moved admin beside bob with the vanilla debug menu's own `/teleportto` and repeated session a's arms. Ruling H4-1 named one more live session as its cost if wrong; no harness change was needed for c.

**Deviation: no zombies.** Fixture `two` has `Zombies = 6` (none); `zombie.near` spawns one tile from the first player and the harness has no god mode, so a 15-minute session would put the subjects under attack. The reading rests on the other player (the plan's "or"); zombie columns read -1. Also: `IsoZombie` has no `lastRemoteUpdate` getter (T116.1).

### The client reading (session c, players beside each other)

What the clients can read (T116.1, jar): a remote player's `getLastRemoteUpdate()` is stamped with the client's wall clock each time it processes a `PlayerPacket` for that player. Live, that stamp advances every 201–400 ms at the median, while the remote player's position changes nearly every client frame (the client's own interpolation, inference). So the ring records three series: stamp gaps (packet arrivals), move gaps (frames between position changes) and the client's own frame intervals.

Per arm, both clients (gap ms; "lined" = gaps of 100 ms or more overlapping a server minute frame widened ±100 ms; "control" = the same against minute frames shifted by half their spacing, ~313–340 ms):

| arm | client frame p50 / p99 / max | stamp p50 / p99 / max | stamp ≥100 lined / control | move p50 / p99 / max | move ≥100 lined / control |
|---|---|---|---|---|---|
| I | 17 / 19–20 / 23–29 | 400 / 801–817 / 817–818 | 181/180, 194/183 | 17 / 135–149 / 584–667 | 46/41, 48/45 |
| burst1 | 17 / 19 / 23–32 | 201–400 / 801–816 / 817 | 211/231, 192/180 | 17 / 51–66 / 716–733 | 32/31, 34/36 |
| b15_1 | 17 / 19 / 22–27 | 399–400 / 801 / 816–817 | 214/210, 200/185 | 17 / 68 / 502–567 | 35/28, 40/38 |
| burst2 | 17 / 19 / 20–22 | 201 / 801 / 816–817 | 212/227, 235/218 | 17 / 100–132 / 634–850 | 40/41, 43/36 |
| b15_2 | 17 / 19–20 / 21 | 201–399 / 801 / 801–816 | 206/210, 244/224 | 17 / 66 / 553–834 | 36/31, 37/35 |
| b15_3 | 17 / 19 / 20–21 | 399–400 / 816 / 817 | 208/206, 197/184 | 17 / 50–116 / 518–634 | 44/38, 37/37 |
| burst3 | 17 / 18–19 / 21–23 | 383–400 / 801–816 / 817 | 175/182, 226/205 | 17 / 50–83 / 616–783 | 39/30, 37/37 |

(admin first, then bob, where two values are given; the full per-client table is in the x244c guide in `artifacts.md`.)

- **No client frame reached 100 ms in any arm** (max 32 ms, under burst1); the clients' own frames do not feel the server's minute frame. The burst's busy (at most 74 ms in this session) ran inside an unbroken 100 ms start-to-start cadence: the start-to-start period held at 104-105 ms in every x244c arm and 103-106 ms in the x244a and x244b arms (`summaries.<arm>.period`), so no tick started late; the 176 ms figure is the end-to-end period (`endPeriod`).
- **The other player's motion shows no minute-aligned gap above chance.** Move gaps of 100 ms or more lined up 32–43 times an arm under the burst against 30–41 in the control, 35–44 against 28–38 under budget15, and 46–48 against 41–45 at idle. The long move gaps (500–850 ms) are the pacing's own stops (a walk ends; the next is queued ≥500 ms later), which are random against the minute frames.
- **Packet stamps:** median 201-400 ms, max 801-818 ms in every arm (idle included); lined against control 175-244 vs 180-231. **The stamp test was blind at this cadence (inference):** every stamp gap was at least 167 ms, so the 100 ms threshold counted every gap (`stamp.ge_gap` equals `gaps.n` in all arms), and the windows cover 32-37 % of the time, so a gap that long overlaps a window about 70 % of the time in the control too; lined above twice the control was out of reach. Near-player stamps stayed within one or two client frames of the 200 ms grid in every arm (at most 18 ms off on admin, 33 on bob in the burst arms, 34 on bob in any arm), including about 135-180 gaps per client in a burst arm that spanned a frame with 30 ms or more of busy.
- **The client rule (plan Step 3; the driver's SHOWS/NONE):** no burst draw and no budget15 draw SHOWS on either client. Its outcome "not noticeable at this load" follows from the rule's construction, not from a reading (the stamp test above could not have shown an effect). The prediction "evidence for (b)" was falsified. **The supported reading (T116.4), resting on the move series (which resolves an effect present at about half the minute frames or more) and on the near-player stamp grid:** at N = 60 on loopback, the burst has no visible effect on another player's updates. No zombies were present (the fixture has none; the zombie columns read -1): the other player only.

**Sessions a and b (far-player stream only):** the same outcome on admin's client — no lined excess (a: 192-221 vs 190-210; b: 39-42 vs 36-41; the same blind stamp test); the stamp max was 801 ms in idle and budget15 arms and 834-850 ms in the burst arms in a, 817-818 in every arm in b. The x244a hint of a ~33-49 ms stretch is not attributed to the burst: stamp gaps more than 30 ms off the 200 ms grid also occur in all three x244a budget15 arms (28-32 an arm, 0 at idle), and the burst-arm ones overlap a busy frame of 30 ms or more 21/42, 29/55 and 35/63 times, below the ~70 % chance rate. Bob's series are empty; driver a graded bob "not noticeable" on an empty series (driver a had no empty-series guard; flagged in `do-not-cite.csv`; drivers b and c grade it "unmeasured").

**What this does not show (for the controller's ruling on ruling 2's thresholds):**
- It measures what a client renders of **another** player (packet arrivals and interpolated motion). A player's **own** actions on server-owned state (timed-action completion, container transfers, hit registration, eating) wait on the server frame and were not measured; a 176 ms end-to-end period delays those by up to ~76 ms over nominal (inference), though no tick started late at N = 60 here (the start-to-start period held at 100 ms).
- Loopback only: both clients on the server's host, no network latency, jitter or loss. Interpolation that hides a 50–75 ms relay delay on loopback may not hide it on top of real jitter.
- n = 1 session per geometry; the alignment test with ±100 ms windows covers 32-37 % of the time, so a small effect (a few extra lined gaps an arm) is below its resolution, and the stamp test had none at this cadence (above).

### Decision 6 — the three draws (ruling H4-1)

Adds over each session's own idle arm: p99 on the ring end-to-end period (~1020 frames), max on the engine's per-window longest frame (~95 windows); "ghost ms/ev" = `ghost.stats` ms ÷ `minuteEventsSince` (drift-immune).

| session | arm | p99 add | max add (window) | starved | ghost ms/ev | busy/min over idle |
|---|---|---|---|---|---|---|
| a DL1 | burst1 / 2 / 3 | 56 / 49 / 50 | 57 (171) / 52 (166) / 61 (175) | 0 | 48.74 / 44.78 / 45.15 | 47.81 / 40.56 / 39.90 |
| a DL1 | b15_1 / 2 / 3 | 13 / 13 / 12 | 15 (129) / 25 (139) / 15 (129) | 0 | 52.13 / 46.82 / 47.07 | 50.06 / 42.46 / 42.48 |
| b 37 ticks | burst1 / 2 / 3 | 46 / 45 / 43 | 67 (173) / 63 (169) / 47 (153) | 0 | 48.66 / 47.72 / 44.83 | 39.66 / 29.05 / 20.01 |
| b 37 ticks | b15_1 / 2 / 3 | 13 / 12 / 12 | 17 (123) / 17 (123) / 17 (123) | 0 | 49.61 / 49.62 / 50.64 | 35.41 / 26.41 / 31.00 |
| c DL1 | burst1 / 2 / 3 | 51 / 48 / 46 | 53 (169) / 48 (164) / 60 (176) | 0 | 46.59 / 45.24 / 44.22 | 44.24 / 41.46 / 39.09 |
| c DL1 | b15_1 / 2 / 3 | 13 / 13 / 12 | 13 (129) / 11 (127) / 12 (128) | 0 | 50.67 / 47.15 / 46.42 | 48.34 / 42.60 / 41.94 |

Totals (budget15 mean ÷ burst mean): ghost ms a minute event **1.053 (a), 1.061 (b), 1.060 (c)**; busy a game minute over idle 1.052, 1.046, 1.065 (the busy figure carries the idle drift: b's burst draws read 20.01 to 39.66). Ghost ms a run spreads 0.762-0.874 between arms within x244c (`summaries.<arm>.ghost_ms_per_run`), so the budget's 5-6 % excess over the burst is not resolved from drift (its cause, per-batch overhead or 1 ms truncation, is inference and unmeasured); the 1.1x clause holds either way.

Notes: a's b15_2 25 ms add was one 41 ms frame (139 ms window), exactly at the 25 ms bound. c's burst3 spans the mod's 07:00 day close (interpolated, inference): its frame nearest 07:00 read 72 ms busy; the arm's 74 ms frame came ~25 s earlier with 70 ghost ms. No 07:00 in a or b. GC: in-arm pauses ≤ 0.058 ms; allocation stalls only at boot (28.97–34.19 s JVM uptime).

**Ruling 2 applied to budget15 (T116.8), at N = 60:**
- **Peak clauses** (≤ 20 ms at p99, ≤ 25 ms at the max): held in all nine draws, at DayLength 1 (six draws: p99 +12–13, max +11–25) and at 37 ticks (three draws: +12–13, +17).
- **No starvation:** 0 starved ghost-minutes in all nine draws.
- **Total ≤ 1.1× the burst:** held in all three sessions on the drift-immune measure (1.053, 1.061, 1.060). This settles H3's open "1.22× at 37 ticks" (drift) for budget15.
- **Empty-queue check ≤ 0.1 ms a frame:** not measured (ruling H4-1 leaves it to Plan 11; H3's x243d A/B −0.052 ms, unresolved).
- **The alternative clause** (the burst adds > 33 ms or pushes a frame over 133 ms, read on the end-to-end period): held in every burst draw at both spacings (+43–56 at p99, windows 153–176 ms, every window over 133 ms in the DL1 burst arms).
- **(a) the one-event design** (the burst ≤ 25 ms at N = 60): not admissible on all nine draws (max adds +47–67).

**Decision 6 for Task M:**
- (a) is excluded (max adds +47-67 in nine of nine draws); (c) is excluded on H3's evidence.
- (b) budget15 is adopted provisionally at both spacings, with nine draws: p99 adds +12 to +13, max adds +11 to +25 (one exactly at 25), no starvation, total 1.053-1.061x on ghost ms.
- The empty-check clause rests on x243d's weak support (A-B-B-A, -0.053 ms, se about 0.03), not on a measurement here.
- **Caveat:** ruling 2's thresholds are read on the end-to-end period. On the loop's own cadence neither design delayed a tick at N = 60 on this host, because the burst's busy of 56-77 ms at the frame max (46-51 ms at the minute-frame median) fits inside the 100 ms period. So (b) buys headroom, not relief from a stall players see today. H3 found the burst's busy linear in N, so it would overrun the period at roughly N = 85-95 here (inference).
- The client reading does not loosen ruling 2: its stamp test was blind at this cadence, and it covers only another player's updates on loopback, not a player's own-action latency.

### Open items for Task M / Plan 11

- The empty-queue clause (Plan 11's scheduler task, ruling H4-1); a minute-sized adaptive budget (ruling H4-1).
- A player's own-action latency under the burst (timed-action completion delay, container transfer round trip) — the noticeability reading H4 did not take.
- A run with real network latency (a second host or a latency shim) — Angus's to supply, as E7.
- Fixture `two`'s 248-tile spawn separation (T116.9): any two-player reading that needs proximity must move a player first; `lua.call DebugContextMenu.onTeleportValid nil x y z` on admin's client works; RCON `teleport` does not.

## Appendix N. H5 — the engine's fake clients (run x245)

Provisional ids in this appendix are its source memo's own; they map at the mint as T114.n -> #(3456+n), T115.n -> #(3470+n), T116.n -> #(3484+n), T117.n -> #(3493+n), T120.n -> #(3496+n).


## H5: the engine's fake clients (run x245): not reachable on 42.20.4

One server-only session, `x245-20261007-192340`. The driver `testing/experiments/x245_fake.py` and the profile `x24-fake` were committed at `0086c08` before the boot. The session loaded PZTestKit only: no NutritionRevamp and no game client. The server ran on port 16261, which the fake hard-codes. The run copy of the ini set `MaxPlayers=64` and `DoLuaChecksum=false`, with `Open=true` and no password. The fake JVM ran read-only from the install's `jre64` and classpath. Its working directory and cache dir were in the run folder. Provisional rows are `T117.1`–`T117.3`, plus a `#3452` status row (delta `task-H5-claims-delta.tsv`; owner `platform/performance.md#measure`).

### The answer

**The shipped fake client gives no player load on 42.20.4 (T117.1).** It connects and logs in, and `Open=true` creates its account. It passes the login queue. Then the server kicks it at `player-connect` with `UI_LoadPlayerProfileError`. Over about five minutes `Client1` went through that cycle 23 times, and no fake player was ever online.

The jar gives the cause (T117.2). `GameServer.receivePlayerConnect` kicks whenever `ServerPlayerDB.serverLoadNetworkCharacter` finds no saved character for the username in `networkPlayers`. The fake never creates one: it goes from the login queue straight to `PlayerConnect`.

**One JVM carries one connection (T117.3).** At each connect round all but one of the clients due failed with RakNet code 4 (24 lines, Client1's own thread among them), and the server only ever saw the username Client1. That code 4 means "attempt already in progress" is inference. `-id=<n>` gives each JVM its own port, but each such JVM runs only one client. Sixty players would need about 60 JVMs at roughly 133–181 MB each, about 8–11 GB.

### Vanilla's frame (no player online)

E7's per-player denominator is **unmeasured**. The three windows had nobody online. `N05` and `N10` are only the scheduled fake counts.

As an idle server-only baseline, each window had about 1050 kept frames:
- busy p50 0 ms, p99 3–4 ms, max 5–37 ms;
- end-to-end period p50 100 ms, p99 105 ms, max 112–138 ms;
- perf.local window max: p99 112–138 ms, max 112–175 ms.

This idle p99 of 105 ms is 3 ms below the x24 sessions' two-client idle p99 of 108 ms. That gap is a comparison across sessions, n = 1 each, and x245 had no client and no NutritionRevamp.

### Memory at each step (free GB / server working set MB / fake JVM MB)

| step | free | server | fake |
|---|---|---|---|
| preboot | 19.22 | — | — |
| ready (server up) | 15.44 | 3792 | — |
| after N00 | 15.44 | 3552 | — |
| before group 0 | 15.27 | 3554 | 133 |
| after group 0's window | 14.27 | 3585 | 175 |
| before group 1 | 14.01 | 3588 | 177 |
| after group 1's window | 13.07 | 3613 | 178 |
| Z (fake killed) | 13.09 | 3614 | — |

Free memory never came near the 2 GB stop or the 1 GB watcher kill. The roughly 2.4 GB that drifted down over the session was not this session's load: the server's working set rose only 61 MB.

### The scheduler arms

The arms were not run, for two reasons. No player joined. And the harness's schedulers drive only harness-held ghost records, so no command runs `P.work` for the online usernames on a schedule. A burst or budget15 reading on real players needs a harness change, which I have reported and not made.

### What would make it reachable (not tried; the plan's no-retry rule)

1. Provision a saved character for each `Client<n>` username before the fakes connect. This could be done by a real client logging in once per name, or by seeding `networkPlayers` in a fixture.
2. Run one JVM per client with `-id=<n>`. Memory allows about 60 on this host only without game clients.

Both are a new task and a new session. Whether the fake's later packets (`PlayerConnect` data, `ExtraInfo`, `Equip`) parse on 42.20.4 is still unread past the profile check.

### For Task M

- E7 stays Angus's to supply (a populated-server reading). The engine's fake client is not a substitute on 42.20.4 as shipped.
- `#3452`'s open half is answered (status row).

## Appendix O. H6 — the global store: its save, its size, and who can request it

Provisional ids map T118.n -> #(3416+n), minted (the Rows bullet).

## H6 memo section: the global store — its save, its size, and who can request it

For Task M to fold into the decision memo's Hitching section and Decision 3. Provisional ids are this task's delta (`task-H6-claims-delta.tsv`, T118.1–T118.6). Build 42.20.4, jar b0bbce05d5.

### The request: a privacy blocker for Plan 11

- **Any logged-in client can request any global modData table by name and receive it** [T118.1].
  - `ModData.request(name)` is exposed to Lua and sends a `GlobalModDataRequest` packet carrying only the name.
  - That packet type requires only `Capability.LoginOnServer`, which the built-in `user` role holds.
  - The server's parse calls `GlobalModData.receiveRequest`. It looks the name up and sends that table, serialised whole, to the requesting connection. It never checks who asked or which name.
  - The store's name, `NutritionRevamp.players`, is in the mod's shipped Lua. Any client, any other mod on the server, or a modified client can ask for it.
- **A mod cannot refuse** [T118.2]. `receiveRequest` fires no Lua event and calls no hook before it sends. The `SendCustomModData` event (#2406) belongs to a different packet. A mod's only control is what it keeps under a global modData name.
- **The size cap does not close the leak** [T118.3]. The reply is written into the connection's fixed 1,000,000-byte send buffer.
  - Below that size, about 92 records, the requester's `OnReceiveGlobalModData` receives every player's full record.
  - Above it, the serialise overflows. The handler then still sends the buffer as it stands: the store's leading bytes, about 92 records, in plain form. The stock client's parse fails on the truncated table, so no Lua event fires, but the bytes still reach the client. This is inference from the bytecode.
- **It is also a hitch source.** The server parses packets in `GameServer.main`'s `mainLoopDealWithNetData` (`@157 L1612` → `PacketType.onServerPacket`). So every request serialises up to 1 MB on the main loop, and a modified client can repeat it at will: a stock client cancels its own over-limit packet (`PacketType.send @0–@22 L932–L934`), and only the server side just logs (`onServerPacket @23–@48 L956–L957`). The cost is unmeasured; the live arm below reads it.
- **Consequence for Plan 11.** The store must leave global modData, whatever Decision 3 says. Pruning or an inputs-only record shrinks the leak but does not close it. The candidates are under "Storage candidates for the privacy fix" below; Plan 11 needs a jar read of the chosen route before it builds on it.
- **Severity.** The stronger reason for "blocker" is the hitch and griefing vector. A ~30-byte request makes the server serialise about 1 MB on its main loop (`mainLoopDealWithNetData @157 L1612`) and send about 1 MB back. The leaked data is the usernames of everyone who ever joined, plus their health state. No write vector exists today (#2399; the mod has no `OnReceiveGlobalModData` handler), and Plan 11 must keep it that way.

#### Storage candidates for the privacy fix

1. **A server-local file through `getFileWriter`/`getFileReader`: recommended.** It is rooted at the server's Lua cache folder (`LuaManager.getLuaCacheDir`, `LuaManager$GlobalObject.getFileWriter @0–@105 L5848–L5859`, #1866). Only the ini, cfg, txt, log and json extensions are allowed (#1120). No network route reads it. Costs:
   - the mod writes its own JSON serialiser;
   - the folder is per host, so the file name must carry the server or world name;
   - the write still runs on the main thread;
   - it is not atomic with the world save: after a hard kill the world rolls back (#2098, #2758) and the file does not.

   `getFileOutput` (`@0–@8 L5076–L5077`) skips the extension check, but whether `DataOutputStream` is exposed to Lua is unread.
2. **Global modData under a secret name, possibly one table per player.** No packet lists table names: `GlobalModData`'s only network methods are `transmit`, `request` and `receiveRequest`, and `collectTableNames`/`getTableNames` are local. The secret must live in option 1's file. It still pays T118.5's main-thread save. It shrinks a request from a guessed name to one record.
3. **Player modData: rejected.** Any mod on the owning client can replace the server's copy with `transmitModData` (#0914, #1091, #1088, #1336), and the server's copy is empty at join (#1432).
4. **`getModFileWriter`: rejected.** It writes into the mod's own folder (#1866), which a Workshop update replaces.

### The save: thread, trigger, frequency

- **Thread** [T118.4]: the console save and the autosave run on the server's main loop. The quit save runs on the JVM shutdown-hook thread. The main-loop chain is:
  - `GameServer.main @3466 L978` → `ServerMap.preupdate`;
  - when `queuedSaveAll` is set and no zip backup runs, `@544–@551 L957–L958` → `ServerMap.QueuedSaveAll(false)`;
  - `@143–@146 L856` → `GlobalModData.save()`.

  The quit chain: `QuitCommand.Command @10–@13 L25` → `ServerMap.QueueQuit @0–@2 L193` sets `queuedQuit` → `ServerMap.preupdate @554–@562 L960–L961` calls `System.exit(0)`. The hook `GameServer$1`, registered at `GameServer.main @0–@6 L400`, then runs `run @28–@35 L375–L376` → `ServerMap.QueuedQuit` → `QueuedSaveAll(true)` → `GlobalModData.save`. The same hook runs on any JVM termination unless `softReset`.
- **Triggers:**
  - the console `save` (`SaveCommand.Command` → `QueueSaveAll`, which queues for the next frame);
  - `SaveWorldEveryMinutes` above 0, counted in real-time minutes (`currentTimeMillis` against `lastSaved + minutes × 60 × 1000`, `preupdate @483–@528 L948–L953`);
  - the quit (`QueuedQuit` → `QueuedSaveAll(true)`).

  The fixture runs at 0, so only the console save and quit write the file (#2097).
- **Frequency:** once per operator-set autosave interval, plus each console save and the quit. `GlobalModData.save` is one step of the whole world save: the player DB, chunks, map collision, radio and more.
- **Shape** [T118.5]:
  - Every table is serialised into one heap buffer. It starts at 1 MiB on the process's first save, and each `BufferOverflowException` grows it by 512 KiB and re-serialises the overflowing table from its start.
  - The save then writes `global_mod_data.tmp` and copies it over `.bin`, on the same thread.
  - `checkClientPause` runs between the world save's steps (`QueuedSaveAll L828–L869`), never during `GlobalModData.save` (`@139 L854`). It sends `StartPause` at the first check after 600 ms, and returns at once on a quit save (`saveQuitFlag`, `L815`) [T118.5].
- **First-save restarts.** These are modelled, not measured: the first save after a boot re-serialises the store 9 times at 500 records (about 33.7 MB written in all against 5.4 MB) and 40 times at 2000. Later saves in the same process start at the grown size (`store-size.json`, `first_save_*`).

### The size (offline, `testing/spikes/store_size.py`, commit 3001c68)

The golden scenario's six final records are serialised in the save's own format, read from the jar. Every number is a Double of 8 bytes, every string a short length plus UTF-8, and every table an int count plus typed key-value pairs [T118.6].

| | per record | 100 | 500 | 2000 |
|---|---|---|---|---|
| full record, as saved (bytes) | 10,807.8 mean (10,684–10,883; 619–625 leaves) | 1,082,082 | 5,411,040 | 21,643,790 |
| inputs only, `K.store.inputsOnly` (bytes) | 8,774.2 mean (507–508 leaves) | 878,850 | 4,394,132 | 17,576,382 |

- 1 MB is reached at about 92 full records. The design load of 60 online players is 649,351 bytes for 60 records, but the store counts every player who ever joined.
- The inputs-only store saves only 19 %, so it is not a size fix on its own.

### Decision 3's rule

- **Outcome: flips.** 500 full records are 5,411,040 bytes, over the 1 MB bound. So the recommendation becomes **pruning on by default**, with an inputs-only store as a Plan 11 candidate.
- The size prong decides it alone, so no save timing is needed for the flip.
- H6 adds that pruning is not enough. The privacy blocker moves the store out of global modData altogether, and the inputs-only record cuts the size by only 19 %.
- Suggested memo text for Decision 3's open bullet: "Read by H6. Any client can request the store and a mod cannot refuse (T118.1–T118.3): the store must leave global modData in Plan 11. At 500 records the store is 5.4 MB (T118.6), over the rule's 1 MB, so the recommendation flips to pruning on."

### Step 3: the live arm (spec for H2's arm E)

The jar settles the save's thread and trigger, not its cost. Decision 3 does not need the cost, but rule 6 does: how much the mod adds to each world-save frame at 60 players, and what one request costs the main loop. Recommended, and cheap.

- **Staged copy only.** Add one bench helper to the instrument file, `NR_H6.seed(n)`. It deep-copies the first live record into `n` synthetic usernames `h6p000001…` under `NR.server.store.records`, and `NR_H6.clear()` removes them. Never edit `mod/`.
- **Arm E1, the save.** For n in 0, 100, 500 and 2000:
  - seed with `lua.call NR_H6.seed <n>`;
  - issue the RCON `save` twice, 30 s apart. The first save after a process start pays the buffer-growth restarts and the second does not, so record which save is the first of the process;
  - read the server log's `Saving GlobalModData` stamp, the next save step's stamp, and `QueuedSaveAll`'s own `Saving finish` elapsed-ms line (`L871–L872`);
  - read the H0 frame ring and `perf.local` across the save frame, and whether `Pausing clients because saving is taking longer than 600ms` appears;
  - compare `global_mod_data.bin` as the change over n = 0, against `store-size.json`'s file bytes for that n. n = 60 means 59 seeded records plus the real one. A small difference is expected from the real record and username lengths.
- **Arm E2, the request.** At n = 0, 60 and 500, the client runs `lua.call ModData.request NutritionRevamp.players`.
  - The server's frame ring gives the request's frame cost.
  - A client-side `OnReceiveGlobalModData` probe, in the instrument file and gated to the client, records the name, whether the table arrived and its key count.
  - Expected at 0 and 60: a table of every record. Expected at 500: no event, and three log lines: the server's `printException` (`receiveRequest L196`), the IllegalMonitorStateException message (`L204`), and the client's parse exception (`GlobalModDataPacket.parse L56–L57`).
  - This turns T118.1 and T118.3 into M rows.
- **Dependency:** arm E depends on H0's `tick.ring` and `perf.local` landing first.
- **Rule.**
  - If the second save at 500 records adds more than 25 ms over n = 0 on the main thread, the save is a hitch source in its own right, and the store's move or pruning is a performance fix too.
  - If one request at 60 records costs more than 5 ms of server frame, the request is a griefing hitch vector to note in the memo. That stays true until the store leaves global modData.
- **Cleanup:** `NR_H6.clear()` and one more save, or a fixture restore.
