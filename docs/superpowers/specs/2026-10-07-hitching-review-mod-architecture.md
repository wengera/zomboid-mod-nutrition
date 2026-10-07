# Architecture review: the mod's own hitch risks at 60 players (lens: the mod's architecture, server and client)

Reviewer model: claude-opus-5-5. Read-only pass over `mod/NutritionRevamp/` at `3d88133`, the decision memo
(`docs/superpowers/specs/2026-10-07-plan-11-decisions.md`: Performance, The 60-player design load, Decisions 1
and 6, Appendices C, G, H, I), `docs/platform/lessons.md` (#1071, #1080), the golden trace and the x231
instruments. Nothing was booted and nothing in the repository was edited.

## How to read the figures

- **Measured** figures cite the register row the memo cites. Every live figure is n = 1 with 2 players.
- **Estimated** figures are labelled `est.`, and the basis is given beside each. All extrapolation to 60
  players is linear and unmeasured.
- A **hitch** is taken to be a server tick whose total work (vanilla's plus the mod's) overruns the 100 ms
  tick at the 10-tick lock. A client then sees late world updates. A flat per-tick cost is not a hitch; it
  only uses up headroom. A client-side hitch is a client frame that overruns about 16 ms.
- **The unknown under every ranking:** vanilla's own per-tick work at 60 players is unmeasured.
  - The mod's safe worst tick is 100 ms minus vanilla's p99 at 60. No reading gives that p99.
  - Experiment E7 asks for it. Until it lands, this review uses a conservative mod budget of 10 ms for the
    worst tick.
- **Install read, not a register row:** the dedicated server launches with `-XX:+UseZGC`
  (`ProjectZomboidServer.bat` and `ProjectZomboid64.json` in the install).
  - ZGC's pauses are sub-millisecond, so allocation churn in the mod costs server CPU time, not
    stop-the-world pauses, unless the heap is near `-Xmx`.
  - GC is therefore ranked low on the server. What table churn costs is Kahlua CPU, which the per-step timers
    already include.

## Inventory of every event site and every piece of periodic or burst work

| # | site | trigger and frequency | per-firing work | scales with |
|---|---|---|---|---|
| S1 | `NR_Server_Players.lua:97-99` `P.minute` | `EveryOneMinute`: once a game minute (6.27 ticks at DayLength 1, 37.46 at DayLength 4, #3346 #3347), and every tick under a fast clock (#3348) | walks `getOnlinePlayers` (3 Java calls a player), builds `seen` and a fresh `P.queue`, runs first sight (store load, body, mirror) synchronously, fires departures | N (walk); joiners (first sight) |
| S2 | `NR_Server_Players.lua:100-102` `P.drain` | `OnTick`, every tick | one queued player's `P.work` (the 9-step pipeline), or an early-out | 1 player a tick, fixed |
| S3 | `NR_Server_Minute.lua:31-45` `MIN.run` | one player's minute | 9 steps under pcall: bus, fast, reconcile, kinetics, metabolism, nutrients, effects, strength, weight; 1.583 ms in play (#3387) | per player-run |
| S4 | `NR_Server_Options.lua:108-109` `pollDirect` | `EveryOneMinute` | 9 `SandboxVars` reads; on a change it runs the `changed` hooks (Fast's mode switch) | none |
| S5 | `NR_Server_Fast.lua:484` the `Hook.CalculateStats` takeover | every player, every tick | 19.33 µs a player a tick (#3353) | N; withdrawn by Decision 1 |
| S6 | `NR_Server_Players.lua:103-111` `OnNewGame` | each respawn or new character | `store.reset`, then the first-sight hooks: body, effects forget, one mirror | events |
| S7 | `NR_Server_Bus.lua:44-57` `mirror.request` | each client request; one at every client's `OnGameStart`, then unthrottled | `K.mirror.build` (138 keys) plus `sendServerCommand` | requests |
| S8 | `NR_Server_Bus.lua:74-95` effects flush | the pipeline's bus step, when the record is dirty and 60 s of wall clock have passed since the player's last push | the whole mirror, about 3.3 KB (est.: 138 keys, 1650 key bytes, the #1495 table format) | dirty players |
| S9 | `NR_Server_Training.lua:189-191` `AddXP`, `OnWeaponHitXp`, `OnWeaponHitTree` | every XP grant, every weapon hit, every tree hit, server-wide | early-outs on other perks; otherwise one store lookup and one `K.training.event` | events (combat-heavy) |
| S10 | `NR_Server_Intake.lua` eat (`complete` and `serverStop`), drink (`updateEat`, `:673`, `:707`) and world water (`transferFluid`) | each eat; **each tick of a drink**, plus the animation events | a vector of 31 keys, a fluid sample and mix tables, a store lookup, the landing, and a level-3 log string built eagerly | concurrent drinkers |
| S11 | `NR_Server_Store.lua:68-86` `S.get` to `S.load` (`K.store.fillInPlace`, `NR_Kernel_Store.lua:334`) | the first `get` in a sight: first sight, a reconnect, a mirror request or an eat | builds a fresh record of about 624 leaves (golden-trace record) and copies it over | joiners |
| S12 | global modData save of `NutritionRevamp.players` | engine world save and shutdown (cadence and thread unknown) | every record ever made; about 624 leaves and about 10 KB as JSON each (golden trace); pruning is off by default (Decision 3) | players ever joined |
| S13 | day close: `NR_Server_Metabolism.lua:303-306` (partition, strength, training ring, TAC, AT), `NR_Server_Nutrients.lua:384`, `NR_Server_Effects.lua:503-508` (a rebuild forced by `lastDay`, then a mark at `:573`) | once a game day, **on the same game minute for every player** (`floor(ageH / 24)`) | close arithmetic, a full `K.effects.compose`, a dirty mark, then a mirror push at the player's next minute | N, synchronised |
| S14 | Effects slow channels: `partFolds :353-417`, `coldFold`, `bruise :438`, `syncBodyPart` | each minute, only when `healMul < 1`, `bleedMul > 1` or `infectMul > 1` (a deficient player) | 17 parts × up to 6 wound get/set pairs, plus bleed and infection: up to about 150 Java calls a minute | deficient players |
| C1 | `NR_Client_Mirror.lua:20-26`, then `NR_Client_View.lua:106` rebuild and the moodle and tooltip listeners | each received mirror (at most 1 per 60 s plus requests) | `K.view.rows` over 27 nutrients with translations; 6 moodle `setValue`s; clears the tooltip cache | none (own mirror only) |
| C2 | `NR_Client_Panel.lua:92` prerender and `:120` render; `NR_Client_Moodles.lua:171` render | every frame while shown | a counter compare; cached rows drawn; two closures allocated a frame (`V.smallFont`, `V.lineHeight`) | none |
| C3 | `NR_Client_Tooltip.lua:424` wrapper, then `T.entryFor :267` | every frame while an item tooltip shows | about 10 Java reads, a 4-field macro table, `string.format` and concatenations, **before** the same-item fast path; a cache miss runs `K.view.tooltip` and `MeasureStringX` for each line | none |
| C4 | `NR_Client_Effects.lua:132` `OnWeaponSwing` | each swing | 2 to 3 reads, logged only at level 3 | none |

Two notes on the inventory:
- **No `transmitModData` site exists.** The store is never transmitted (`NR_Server_Store.lua` header, #2416).
- **The client's cost does not grow with the server's player count.** Every server command is addressed to its
  own player.

## Ranked hitch risks (by expected worst tick at 60 players)

### R1. The planned rule-6 minute: one `EveryOneMinute` event over every player (Decision 1(c), Decision 6(a) or (c))

- **Site:** the drain's replacement for S1 and S2 (`NR_Server_Players.lua:42-102`). Today the drain is per tick;
  the memo's rule-6 design moves it into the event.
- **Cost:**
  - 1.583 ms a player-run in play (#3387). The burst basis is 1.23 ms (#3391).
  - So 73.8–103.2 ms in one tick at m = 1, 36.9–51.6 ms at m = 2 and 14.8–20.6 ms at m = 5. This is the memo's
    arithmetic, unmeasured at 60.
- **Frequency:** once a game minute, which is every 0.63 s at DayLength 1 and every 3.75 s at DayLength 4.
  - Under a fast clock it is **every tick** (#3348): sleep fast-forward needs every live player asleep, which
    is rare at 60, but an admin's `settimespeed` is enough.
- **Scaling:** linear in N, and nothing spreads it, because one event fires at most once a tick (#3348).
- **Worst tick at 60:** about the whole 100 ms budget at m = 1, before vanilla's own work. That is a certain
  hitch.
- **Candidate fixes:**
  - (a) A budgeted per-tick scheduler (A1 below), which is Decision 6(b).
  - (b) A cheaper run (A3) with a round-robin. Reaching 10 ms at m = 2 needs 0.333 ms a run, 4.75 times cheaper
    than today.
  - (c) Tiering the pipeline (A4), so a minute event carries only the fast tier.
- **Decides it:** E5 (synthetic-N injection with a tick-gap ring), E1 (the profile below the step), E4 (tiering
  drift) and E7 (vanilla's headroom).

### R2. The shipped drain starves players whenever N exceeds the ticks in a game minute

This is a correctness failure today, and its naive fix becomes R1.

- **Site:** `NR_Server_Players.lua:49` (`P.queue = {}`, a fresh queue each minute) with `:82-94` (one player a
  tick).
- **Behaviour (read from the code):**
  - Each game minute only the first `ticks` players in `getOnlinePlayers` order run. That is 6 or 7 at
    DayLength 1 and 37 or 38 at DayLength 4 (#3346, #3347).
  - The rest are re-queued behind them and never reached. The order is the same each minute, so the **same**
    players starve.
  - At 60 players, 53–54 players get no minute at DayLength 1, and 22–23 at DayLength 4.
  - A starved player's record never steps: no thirst target, no nutrients, no effects. The bus flush and the
    first-sight body still run.
  - Appendix C S3.2 saw this only under a fast clock (`bob` starved). It is the same defect on any slow clock
    once N exceeds the ticks a minute.
- **Cost:** no hitch, because each tick carries exactly 1.58 ms. But Plan 11 Task 2's drafted fix
  (`perTick = ceil(N / CYCLE_TICKS)`) makes it 10 players a tick at DayLength 1, which is **12.3–15.8 ms on
  every tick** (memo), and 2 a tick at DayLength 4, which is 2.5–3.2 ms.
- **Scaling:** linear in N divided by the ticks a game minute. So it is worst at short days.
  - DayLength 1 is the harness's 15-minute day, not a typical 60-player server day.
  - At a 1-hour day (about 25 ticks a minute, inferred in Appendix C S3.1) it is 2.4 players a tick, about
    3.8 ms (est.).
- **Candidate fixes:**
  - A1 with a due-time per player, so no player is skipped and the cost is capped.
  - Any fix needs a starvation counter in the bench: players whose `lastRunAge` is more than 1 game minute old
    at each minute event.
- **Decides it:** E5 arm D, which reads starvation on the shipped code and on each candidate.

### R3. The day boundary is synchronised: every player's close, effects rebuild and mirror push in the same game minute

- **Site:**
  - `NR_Server_Metabolism.lua:301-310`: `today = floor(ageH / 24)` is the same for every player.
  - `NR_Server_Nutrients.lua:383-384`.
  - `NR_Server_Effects.lua:503-508`: `E.lastDay` moves, so `K.effects.changed` is true and every player runs a
    full `compose`, which has 3 surface passes and 2 `foldRows`.
  - `:573`: a mark, then a full mirror (S8) at that player's next minute.
- **Cost:** unmeasured. P1's A window was not shown to cross a close, and no row isolates one.
  - Estimate (est., from the code's call counts): about 0.3–1.0 ms extra a player on the close minute. That is
    the close kernels, the compose, and one extra `K.mirror.build` (138 keys, 101 string concatenations)
    plus the send, the minute after.
  - At 60 players under R1's burst: +18–60 ms on the close tick (est.), on top of 74–103 ms.
  - Under a count-based scheduler, the close minute's ticks each overrun their budget by k × the close cost.
  - The pushes: 60 × about 3.3 KB, about 200 KB of `sendServerCommand` in one game minute (est.). It is
    serialised on the server's main thread. It is spread across ticks only if the minute itself is spread.
- **Frequency:** once a game day, which is every 15 min of wall at DayLength 1 and every 2 h at DayLength 4.
- **Candidate fixes:**
  - An elapsed-time-checked scheduler, which absorbs a heavy minute.
  - A per-player close offset: slot = hash(username) mod 60 game minutes after the boundary. This changes
    behaviour, so it needs a golden-trace diff.
  - Not marking the mirror dirty on a day change alone: rebuild the set, but push only if a pushed field
    changed.
- **Decides it:** E8.

### R4. The global modData save grows with every player ever seen

- **Site:** S12. `NR_Server_Store.lua:68-86` creates a record per username. The live record holds derived and
  input fields alike (`fillInPlace` strips derived fields only on load), and Decision 3 leaves pruning off.
- **Cost:** unmeasured.
  - Size (est.): about 624 leaves and about 10 KB as JSON per record (the golden-trace record: nutrients 308,
    body 117, effects 54, acute 48, stomach 32, pool 31, fluids 16). 500 records ever seen is about 5–7 MB in
    the binary format.
  - The jar shows `GlobalModData.save` allocating one `ByteBuffer` and walking every table (a `pz.sh refs`
    read of its body, not a register row).
  - Its caller, its cadence and its thread are not read.
  - If it runs on the main loop at a world save, a 5–7 MB serialise is plausibly tens to hundreds of ms
    (est., wide).
- **Second exposure (unread):** whether the server answers a client's `ModData.request` for any key. If it
  does, one client request ships the whole table: a network and serialise burst, and a privacy leak of
  every player's record.
- **Frequency:** each world save, which is operator-set.
- **Scaling:** players **ever** joined, not online. It grows for the life of the server.
- **Candidate fixes:**
  - Keep derived state out of the durable table. Hold a Lua-side shadow `S.derived[username]` that is never
    saved; the global table holds `K.store.INPUTS` only. This needs a count of the inputs-only leaves.
  - Prune or compact on departure.
  - Pruning on by default (it reopens Decision 3).
  - Drop the departed players' derived fields at departure, since `fillInPlace` rebuilds them at the next sight
    anyway.
- **Decides it:** E11.

### R5. The per-run multiplier: seven heal passes and recomputed constants in every player-minute

This multiplies R1–R3.

- **Site:**
  - Nutrients `heal`: `:367` and `:488`. Each walks every numeric field of 27 nutrient keys (11 fields each),
    `fluids` and `acute`, about 400 `type` and `finite` checks. It also builds the `"nutrients." .. key .. "."`
    prefix string for each of the 27 keys **on every pass**, even when nothing heals (`:204`).
  - Metabolism `K.heal.body` at `:276` and `:326`: about 80 `K.vector.finite` calls a pass.
  - Effects `heal` at `:478` and `:577`.
  - Strength `heal` at `:232`.
  - `K.nutrients.minute` (`NR_Kernel_Nutrients.lua:328-396`):
    - it recomputes `dialExp` (a `math.log` and `ladderOf`) for each pool every minute (`:116-135`), though it
      is constant per record;
    - it computes `math.exp(-dtD)` in `excess` 27 times (`:216`), though it is one value a minute;
    - it walks `ORDER` again for `allRepleteOf`.
- **Cost (inference):** D2 measured Nutrients at a **zero interval** at 144.4 µs (#3390). At a zero interval
  the step does only `ensure`, **one** heal and the reads before `dtM <= 0` returns (`:379`). So one Nutrients
  heal pass is on the order of 100–140 µs warm.
  - The in-play run is cold: A is 1.3–4 times D2 for the same work in reconcile, strength and weight (#3387,
    #3390).
  - So the two Nutrients heals are plausibly 250–500 µs of the step's 800 µs (est.).
  - All seven passes are plausibly 25–45 % of the pipeline (est.).
- **Frequency:** every player-run.
- **Candidate fixes:**
  - Heal once a minute, after the step only, and on load. The pre-step heal guards only against writes made
    outside the pipeline (Intake writes `ax`, `axr` and the pending sums).
  - Build the heal prefixes lazily, only when a bad field is found.
  - Hoist the per-record constants (`dialExp`, the ladder) into `NR.data.records` at load.
  - Compute one `exp(-dtD)` a minute.
- **Decides it:**
  - E1 says how big it is.
  - E2 and E3 must reproduce the golden trace byte for byte. E2 also needs a NaN-injection mutation pass, so
    that the remaining heal is still proven to catch a NaN.

### R6. First sight and a mass reconnect are synchronous inside the minute event

- **Site:**
  - `NR_Server_Players.lua:59-64` runs, inside `P.minute`, for each new username: `store.get` to `S.load` to
    `K.store.fillInPlace` (a full rebuild of about 624 leaves and about 100 tables, `NR_Kernel_Store.lua:311-350`).
  - Then the first-sight hooks: `MET.ensureBody`, which makes 12 `ZombRandFloat` draws and reads 6 traits, and
    `B.sendMirror`, a full mirror.
- **Cost:** unmeasured. Est. 1–5 ms a joiner in Kahlua.
- **Frequency:**
  - Joins are spread by connection time.
  - After a restart a reconnect wave can put several joiners into one event: a game minute is 3.75 s at
    DayLength 4.
  - Each joining client also fires `mirror.request` (S7), so the mirror is built twice within the first
    minute.
- **Worst tick at 60 (est.):** 10 joiners in one event is about 10–50 ms, plus whatever the minute's design
  adds.
- **Candidate fixes:**
  - Enqueue first sight into the scheduler as a budgeted job, and leave only the identity bookkeeping in
    `P.minute`.
  - Answer a `mirror.request` from an unloaded record by marking it dirty, not by a synchronous load.
- **Decides it:** E10.

### R7. A fast clock turns every minute-shaped design into an every-tick load

- **Site:** S1 and S2 under `settimespeed` or all-asleep fast-forward. Every tick carries one minute event
  (#3348); about 4.7 game minutes a tick at speed 30 (#3346 and Appendix C S3.2).
- **Cost:**
  - The rule-6 burst: 74–103 ms **every tick**. The server saturates.
  - The round-robin at m: ceil(60 / m) runs every tick.
  - The shipped drain: one player a tick, and 59 starve.
  - The wall-cycle share (Appendix C, `CYCLE_TICKS` 10): 6 a tick, about 7–10 ms (est., at 1.23–1.58 ms a run).
- **Frequency:** rare at 60 players, but an admin command triggers it.
- **Candidate fixes:**
  - A1's wall-time cadence: each player at most once a wall second when the game minute outruns the budget,
    with the step integrating the elapsed world age.
  - The steps already clamp at 60 game minutes (`NR_Server_Nutrients.lua:377`, Metabolism `:277`).
  - The dt biases of Appendix H (`exEma`, `coldH`, `cafMean`, the bruise roll) must be fixed first, because a
    run then integrates 47 or more game minutes.
- **Decides it:** E6.

### R8. A deficient player's minute is heavier than any measured minute

- **Site:** `NR_Server_Effects.lua:353-417` (`partFolds`), `:419` (`coldFold`) and `:438` (`bruise`), plus the
  `regen` setters and `syncBodyPart`.
- **Cost:**
  - P1's players were replete, so the folds returned early and the effects step read 121 µs (#3387).
  - A scurvy or anaemic player walks 17 parts × (6 wound get/set pairs, bleed, infection): up to about 150 Java
    calls a minute.
  - At #3388's 0.214 µs a call that is about 32 µs. At the 2.2 µs in-session upper bound it is about 330 µs a
    deficient player-run (est.).
- **Scaling:** the number of deficient players, which a hardcore server may make most of the population late in
  a run.
- **Candidate fixes:**
  - Fold only parts with a nonzero timer, read through one `getBodyParts` walk that skips clean parts.
  - Fold every k minutes, since wound timers move slowly.
- **Decides it:** E1's deficient arm.

### Lower risks (listed for completeness)

- **R9. The takeover hook (S5):** 19.33 µs a player a tick (#3353), so 1.16 ms flat each tick at 60. It is
  withdrawn by Decision 1(a). If it ever returns, it is a flat cost, not a spike.
- **R10. The drink capture (S10):** it runs every tick while a player drinks, allocating a fluid sample, a
  vector of 31 keys, a mix table, a `lastIntake` table and an eager level-3 log string.
  - Est. 50–150 µs a call, with a few concurrent drinkers at 60, so under 1 ms a tick.
  - Fix: build the log string only behind `NR.log.level >= 3`, and accumulate the litres on the action object
    and land once at completion or stop. The landing timing then changes, so it needs a golden-trace and live
    check.
- **R11. `mirror.request` is unthrottled (S7, `NR_Server_Bus.lua:44-57`):** a looping client or another mod can
  make the server build and send about 3.3 KB on each call.
  - Fix: one answer a player per N wall seconds, with the 60 s push gap's own timestamp table reused.
- **R12. The client tooltip (C3):** every frame it computes the key (about 10 Java reads, a table,
  `string.format`) before the same-item fast path at `:279`.
  - Est. 20–60 µs a frame, against a 16 ms frame, so negligible.
  - A cache miss runs `MeasureStringX` once per line (est. 0.5–2 ms, once per item per mirror, because
    `T.cache` is cleared on each mirror at `:172`).
  - Fix: test `T.last.item == item` first, and re-key only every N frames.
- **R13. The client mirror rebuild (C1):** once per received mirror. Est. 1–3 ms one frame on the client, at most
  once a wall minute. Not player-visible.
- **R14. Allocation churn:** per player-run, roughly the 54 heal prefix strings, the `P.minute` tables and the
  varargs of `NR.call`, `NR.num` and `NR.obj`, on the order of KB.
  - At 60 players at DayLength 1 that is about 100 runs a second, a few MB a second on a ZGC heap.
  - It is a CPU cost already inside the step timers, not a pause risk.
  - On the client the panel allocates two closures a frame (`NR_Client_View.lua`, `V.smallFont` and
    `V.lineHeight`). That is trivial under G1 or ZGC.

## Candidate architectures

**A1. A budgeted per-tick scheduler** (Decision 6(b); per-tick work that only schedules, no simulation).
- **State:** a persistent ring of usernames with `due[u]` = the world age at which the player's next minute is
  owed.
- **`EveryOneMinute`** does identity bookkeeping only: the online diff, departures, and first sight enqueued, not
  run.
- **`OnTick`:**
  - while the head is due, `ms < budgetMs` and `runs < capRuns`: run `P.work` for the head and re-arm its due
    time at +1 game minute;
  - `ms` is read with `getTimestampMs` after each player (1 ms resolution);
  - `capRuns = max(1, floor(budgetMs / emaRunMs))` guards the 1 ms resolution;
  - `emaRunMs` is the mean of the truncated per-run ms over the last 100 runs, as P1 computed its means.
- **Under a fast clock or an overload:** due players stay queued; each run integrates its true elapsed age,
  which is dt-correct once Appendix H's biases are fixed. The scheduler never starves anyone (round-robin
  order), and its worst tick is the budget plus one run.
- **What it costs:**
  - an `OnTick` early-out (a pcall'd `isServer` plus one table read, about 1 µs);
  - a per-player due-time, so behaviour stays every-minute whenever the budget allows;
  - the golden trace holds if the host fires each player's run at the same world age as today. The golden
    host's minute-driven harness must model "run at due", which is offline work.
- **Budget:** 5 ms covers 60 players at DayLength 4 (2 a tick). DayLength 1 needs 15 ms, or tolerates a lag of
  about 1.5 game minutes a player at 5 ms. That lag is P2's k of about 1.5, inside the fairer band.

**A2. A round-robin on `EveryOneMinute`** (rule 6 as written).
- Spike = ceil(N / m) × run cost. At 60 players it needs m of 5 or more, or a run of 0.33 ms or less, to stay
  under 20 ms.
- m = 5 is player-visible (#3396).
- It is dominated by A1 on worst tick and on drift. It only beats A1 on the "no `OnTick`" letter of the rule.

**A3. A cheaper run.** Each item takes a golden-trace byte-for-byte proof unless it is marked as a behaviour
change.
- One heal per sub-table a minute, with the prefix strings lazy (R5).
- Hoisted record constants and one `exp(-dtD)` a minute (R5).
- `allRepleteOf`, `anaemic` and `vitDClinical` folded into the main loop.
- Weight: skip the four legacy setters when the values are unchanged since the last write. **This is a behaviour
  change:** other mods' writes would no longer be overwritten each minute.
- Strength: call `vanillaLevel`'s `getTotalXpForLevel` loop only when the XP changed.
- Effects: skip `traits` and `toggle` reads unless the grade epoch or the night-vision machine moved. A
  re-assert once every N minutes still repairs an admin edit.
- **Target:** 0.33–0.42 ms a run (the memo's figure for under 10–25 ms at m = 2). Whether it is reachable is
  E1's question.

**A4. Tiered cadence.**
- **A fast tier every game minute:** stomach and kinetics, fluids and the thirst target, the acute states
  (alcohol, caffeine, glucose, sleep), the effects per-minute scalars, and the weight and carry writes.
- **A slow tier every K game minutes in a hashed slot** (each player's slot = hash(username) mod K): the 27
  nutrient records (`K.nutrients.minute`), the excess ladder, the effects rebuild check, and the strength
  ceiling.
- **Integration:** the pools are exact under zero-order hold at constant intake (the kernel header). A slow
  step over K minutes with the summed absorbed amount spreads a meal over K minutes, a drift of the same kind
  P2 measured, but on stores whose onset runs in days.
- **Saving:** the slow tier's share × (1 − 1/K). With heal fixed, the nutrients loop is probably the largest
  remaining block (est.).
- **The slot hash also spreads every slow-tier spike,** including the day-close effects rebuild, if the close is
  moved into the slot (R3).

**A5. Staggered day close.** Close each player's day at its slot minute after the boundary. This is a behaviour
change; the golden diff is bounded by the slot offset.

**A6. A leaner mirror.**
- Push only on a change of a field that is pushed, not on any rebuild.
- Pack `nut_<key>_{g,p,x}` into one string or array: 81 keys become 1, about 3.3 KB becomes under 1 KB (est.).
- Throttle `mirror.request`.

**A7. A durable store of inputs only.** The global modData holds `K.store.INPUTS` paths; the derived state lives
in a never-saved Lua shadow table. The save shrinks by the derived share (unmeasured; E11 counts it).

## Experiments

Every live experiment runs on a staged copy with the x231 instrument file
(`testing/spikes/instruments/x231_NR_Server_Bench.lua`) extended and appended. It never touches `mod/`.
Harness changes land first, in their own commit (CLAUDE.md § 5).

**E1. The profile below the step** (the memo's Plan 11 first performance task, made concrete).
- **Question:** where do the 800 µs of Nutrients, the 333 µs of Metabolism and the 121 µs of Effects go? How
  much is heal? What does a day-close minute cost, and what does a deficient player's minute cost?
- **Method, offline first:** in lupa, time each sub-block over 10⁵ runs of the golden scenario's records
  (relative shares only, because Kahlua is not C Lua).
- **Method, then live:** timers inside the steps on the staged copy. They are accumulated over runs, as P1 did,
  around:
  - each heal pass;
  - `K.nutrients.minute`;
  - the fluids block (`:421-454`);
  - the acute block (`:457-486`);
  - `readActivity`;
  - the Metabolism and Nutrients day-close functions;
  - `K.effects.compose`;
  - `partFolds`;
  - `K.mirror.build` and `sendServerCommand`.
- **Arms:**
  - A: in play, 240 runs or more, as in x231.
  - DC: drive 10 or more day closes with `settimespeed` across 07:00 and read the close minute's runs apart.
  - DEF: one player's `nutrients.vitC.p` and `iron.p` set to clinical through `lua.setpath` (a scurvy bleedMul
    and healMul), with a wound applied, for 60 runs.
- **Readings:** ms totals per sub-block with the binomial sd; the run count; `NR.call` counts.
- **Decision rule:**
  - A sub-block of 15 % of the pipeline or more is a named refactor target.
  - A heal total of 20 % or more adopts E2.
  - A close minute of 2 times a normal minute or more forces A1 to check elapsed time, not only count, and puts
    A5 on the table.
  - A DEF run of 1.5 times A or more puts R8's fix into Plan 11.
- **Cost:** half a day of instrument and driver work, one 60–90 min session, and one artifact commit.

**E2. Heal once.**
- **Question:** can the pre-step heals in Nutrients, Metabolism and Effects go, with lazy prefixes, without
  moving the golden trace?
- **Method:** offline. A patched tree is run through `testing/tests/kernel/test_golden_trace.py`. Then a
  mutation pass: inject a NaN into a nutrient field, a body ring slot and an effects key between minutes, and
  show the remaining post-step heal stamps it fresh, with the same log line as before.
- **Readings:** golden byte-equality; mutation kills; offline µs saved.
- **Decision rule:** byte-identical and all mutations killed means adopt. The live saving is confirmed by
  re-running E1's A arm in the same session as the next live task.
- **Cost:** 2–4 h offline.

**E3. Hoisted constants.**
- **Question:** do the cached `dialExp`, the ladders and a shared `exp(-dtD)` keep the trace byte-identical?
- **Method:** offline golden.
- **Decision rule:** byte-identical means adopt. If not, examine which floating-point path differs; for example
  `exp` computed once versus 27 times is the same value, so a difference would point to a real bug.
- **Cost:** 1–2 h.

**E4. Tiered cadence drift.**
- **Question:** at which K does the slow tier (A4) stay inside Appendix H's fairer band?
- **Method:** offline. In the golden host, gate `K.nutrients.minute`, the excess ladder and the effects rebuild
  on `slot(u, K)`, with the summed absorbed and ingested amounts carried between slow steps. K is 5, 10, 30
  and 60.
- **Readings:** leaves outside the band per field; discrete mismatches (grade, excess rung, epoch, trait
  toggles); the maximum delay of each grade change in game minutes; the effects rebuild count.
- **Decision rule:** take the largest K with no band or grade flip beyond a delay of K minutes or less on
  records whose onset is a day or longer, and no change to the deaths or respawns of g3.
- **Cost:** 1 day offline.

**E5. Synthetic-N injection (the 60-player question inside the 2-client limit).**
- **Question:** what is each scheduler's worst tick, tick-gap p99 and starvation at an effective N of 20, 40
  and 60?
- **Method:** live.
  - An instrument clones each real player's record into ghosts `ghost_<i>_<u>` (a deep copy, outside the store's
    table) and runs `P.work` against the real `IsoPlayer`, so the Java reads and writes are real and the cost is
    honest; the behaviour is garbage and is discarded.
  - An `OnTick` ring records `getTimestampMs` at each tick and the count of runs in that tick.
- **Arms:**
  - A, burst m = 1;
  - B, round-robin m = 2 and m = 5;
  - C, A1 at budgets of 5, 10 and 15 ms;
  - D, the shipped one-a-tick drain, with a starvation counter.
  - Each arm runs at DayLength 1 and 4 for at least 30 game minutes.
- **Readings:** the tick-gap distribution (p50, p99, max, and the count over 110 ms); the max runs in one tick;
  the max staleness of a player in game minutes; the server's ticks per second.
- **Decision rule:**
  - With vanilla's load near zero (2 clients), the mod's contribution is the gap above 100 ms plus the
    in-tick ms.
  - A design passes at N = 60 if its worst in-tick mod ms is within the budget from E7 (10 ms until then) and
    no player runs staler than 1 game minute at DayLength 4.
  - A1 is expected to pass; the burst is expected to fail. The experiment confirms or falsifies.
- **Cost:**
  - a harness and instrument commit (ghost cloning; a tick-gap ring replied through a `TK` command, or the
    instrument's text reply as x231 did);
  - one 2 h session;
  - a guard that the ghosts never enter the store's table, so they are never saved.

**E6. The fast clock under each scheduler.**
- **Question:** under `settimespeed 30` and all-asleep fast-forward, is the worst tick bounded and does every
  player still run?
- **Method:** the same as E5, with an effective N of 60.
- **Arms:** the burst, round-robin m = 5, A1 at 10 ms, and the drafted wall-cycle share.
- **Readings:** runs per tick; each player's wall interval between runs; the game minutes integrated per run; the
  tick gaps.
- **Decision rule:** pass if every player runs at least once per 2 wall seconds and the worst tick is the budget
  plus one run. The dt-bias fixes (Appendix H) are a precondition of shipping a pass.
- **Cost:** a 30 min arm added to E5's session.

**E7. Vanilla headroom at 60** (the denominator of every rule above).
- **Question:** how much of a 100 ms tick does vanilla use at 60 players, and what does the server do when a
  tick overruns: catch up or slip?
- **Method:**
  - A jar read of `GameServer.main`'s loop and the update limiter (`pz.sh dump`), and of any frame-time figure
    the server exposes to Lua or the console.
  - Then ask Angus for one reading from a populated server, or a cited community figure.
- **Readings:** the limiter's code path with offsets; the per-tick ms if exposed; the 60-player p99, sourced.
- **Decision rule:** the mod's worst-tick budget is 100 ms minus that p99, minus a 20 % margin. Without a
  reading, use 10 ms.
- **Cost:** 1–2 h of jar read plus Angus's input.

**E8. The day-close burst.**
- **Question:** what does the boundary minute cost at an effective N of 60, and how many pushes and bytes follow?
- **Method:** E5's injector across 07:00 under A1 at 10 ms and under the burst. Read the close-minute ticks and
  the next minute's `B.effects.stats.pushes` and payload bytes. Offline, a `#` count of the serialised mirror.
- **Decision rule:**
  - If the close tick under A1 exceeds the budget plus 1 run, adopt an elapsed-time check.
  - If the pushes exceed 30 in one game minute, push only on a change of pushed fields (A6).
  - If either still fails, run A5's golden diff.
- **Cost:** a 30 min arm.

**E9. The mirror's cost and size.**
- **Question:** what do `K.mirror.build` plus `sendServerCommand` cost, and how many bytes are on the wire?
- **Method:**
  - Live bench: 1000 `B.sendMirror` calls to the admin client in one call, at 1 ms resolution, divided by the
    count.
  - The client counts received mirrors.
  - Bytes: offline, through the #1495 format (or the jar's `writeTable` read).
- **Decision rule:** a cost of 300 µs or more, or 2 KB or more, means pack (A6).
- **Cost:** 1 h, riding E5's session.

**E10. First-sight cost.**
- **Question:** how long are `S.load` plus `ensureBody` plus the first mirror per player?
- **Method:**
  - Live bench: 200 `K.store.fillInPlace` calls on a deep copy of a live record, plus 200 `MET.ensureBody` calls
    on a fresh record table.
  - Plus `bob` quitting and rejoining 3 times with a minute-event ring that reads the first-sight event's ms.
- **Decision rule:** more than 2 ms a joiner means first sight is enqueued into A1 as a budgeted job.
- **Cost:** 1 h.

**E11. The global modData save and request.**
- **Question:** who calls `GlobalModData.save`, on which thread and how often, and what does it cost at 100, 500
  and 2000 records? Does the server answer any client's `ModData.request` for this key?
- **Method:**
  - A jar read of the callers of `GlobalModData.save` and of its request handler.
  - Live: seed N synthetic records of about 624 leaves into `NutritionRevamp.players` through a bench call, issue
    the admin `save`, and read the tick-gap ring and the server log's `Saving GlobalModData` stamps.
- **Decision rule:**
  - If the save runs on the main loop and passes the budget at 500 records, adopt A7 and an operator prune
    default (back to Angus as Decision 3).
  - If any client may request the key, the store must not live under a requestable key, or the request must be
    refused. That is a jar question first.
- **Cost:** 2 h of jar read plus a 30 min arm, with a fixture restore after the run.

**E12. The client tooltip and panel frame cost** (low priority).
- **Method:**
  - Offline in lupa, `T.entryFor` with a stubbed item.
  - On the `-debug` client, `lua.call` of a bench that runs `T.entryFor` 1000 times on the first inventory food
    (`T.probe`'s route), at 1 ms resolution.
- **Decision rule:** more than 50 µs a call means the same-item check moves before the key build.
- **Cost:** 1 h.

## Concerns

1. **R2 is a shipped-1.0.0 correctness defect, not only a performance one.**
   - At more players than ticks in a game minute (7 or more at DayLength 1, 38 or more at DayLength 4) the same
     tail of `getOnlinePlayers` never runs its minute (`NR_Server_Players.lua:49`, `:82-94`).
   - The memo files this under the fast clock only (Appendix C S3.2).
   - Plan 11 Task 2 must name the slow-clock case and test N greater than the ticks a minute in the golden host.
2. **"12.3–15.8 ms a tick" is the drafted wall-cycle share at DayLength 1, not the shipped drain.**
   - The shipped drain costs 1.58 ms a tick and starves players.
   - DayLength 1 (a 15-minute day) is also the worst case for any spread design. At the presets' DayLength 4 the
     same share is 2.5–3.2 ms a tick.
   - Decision 6 should be read against the day length real 60-player servers run.
3. **Offline lupa timings are C Lua 5.1, not Kahlua on the JVM.**
   - They give relative shares and byte-for-byte behaviour, never absolute ms.
   - Every ms figure in a decision must be live (E1, E5).
4. **The 1 ms resolution of `getTimestampMs` limits a per-tick budget check.**
   - A1 needs the count cap from a running mean as well as the elapsed check.
   - E7's jar read should also look for any finer timer exposed to Lua.
5. **Ghost injection (E5) measures the mod's cost honestly but cannot measure vanilla's growth with 60 real
   players** (more zombies loaded, more packets). E7 is the only route to that denominator, and it may need
   Angus.
6. **R4's second exposure (a client's `ModData.request` returning every player's record) is unverified.** If it
   holds, it is a privacy issue as well as a performance one, and it should be read before Plan 11 is written.
