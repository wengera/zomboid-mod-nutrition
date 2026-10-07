# Plan 10c — Hitching Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure where the mod can make a player notice a hitch at the 60-player design load, and which scheduling architecture minimises the worst server frame, before Plan 11 is written.

**Architecture:** Measurement only, with no change to `mod/`. The work has five parts:
- **The harness.** It first gains a frame-time instrument and a synthetic-load mode, so a two-client session can stand in for 60 players' work.
- **Offline.** Prototype refactors (heal once, hoisted constants, a slow tier) run against the golden trace in lupa, on copies of the mod's Lua under `testing/spikes/proto/`.
- **Live sessions.** They boot staged copies with the instruments added only in the copy, as Plan 10b did. They measure the sub-step costs, then a scheduler shoot-out at N = 20, 40 and 60 synthetic players.
- **Jar reads.** These settle the global store's save path and whether a client can request it.
- **Outputs.** Every answer becomes register rows and a "Hitching" section in the decision memo, ending in Decision 6's answer.

**Tech Stack:** the mod's Lua (Kahlua; read-only here); Python 3, pytest and lupa 2.8 offline; the harness (`pzt`, fixture `two`, `bench.global`, `lua.call`, `lua.setpath`, `settimespeed`, the eat and sleep routes); the jar toolchain at `C:\Users\Angus\pz-b42` (read-only); the claims register and its delta tools.

**Spec:** the architecture review pass of 2026-10-07. Its two reports are in `.superpowers/sdd/2026-10-07-arch-review-hitching/`:
- `review-mod-architecture.md`: 14 risks and experiments E1–E12.
- `review-platform.md`: answers on the server loop, the scheduling primitives, GC, the network and the harness, with experiments X0–X8.

The plan also rests on the decision memo `docs/superpowers/specs/2026-10-07-plan-11-decisions.md`: its Performance section, the 60-player design load, rule 6 as Angus restated it, and Decision 6.

## Global Constraints

Plan 10 and Plan 10b's Global Constraints hold. Plan 10c adds:

- **Rule 6, as Angus restated it on 2026-10-07.** The goal is no noticeable performance degradation or hitching, the mod's primary point of failure. Per-tick work is admitted only where a measurement proves it reduces hitching. Every design is judged by its worst server frame and how often that frame comes, at the 60-player design load.
- **The design load** is a 60-player average (Angus). Every live reading is taken at an effective N of 20, 40 and 60.
- **No edit under `mod/`.** Instruments and prototypes live in staged copies (`release/hitch-<HEAD>/`, gitignored) or under `testing/spikes/proto/`. Each one is recorded by sha256 in its artifact, or kept under `testing/spikes/instruments/` like x231's.
- **A harness change lands first, in its own commit.** It carries its comment block, `tools/luabalance.py` green, `tools/bus_inventory.py` regenerated, and `#2808` and `#1235` updated if the count line moves. The next run is its smoke test (CLAUDE.md § 4.5, § 5).
- **Timings.** The Lua clock is 1 ms. The engine's frame-period counter (`getPerformanceLocal()`, read once a second) is the reference reading of a frame's length. Every Lua-side figure is a total over many frames or runs, with its count stated.
- **Synthetic players are cost, not behaviour.** A ghost record runs the real pipeline against a real player object, so its state is not a player's state. No behaviour row rests on a ghost.
- **Live.** One session at a time. Run `python testing/pzt doctor` first. Use fixture `two` with `Nutrition = false`. A driver is never edited after its run. An unmeasured or trivial reading is written as such. Never `-safemode`.
- **The artifact commit belongs to the controller.** An implementer stages the artifact files and hands over. The controller folds the `artifacts.md` pointer re-anchor into that commit (CLAUDE.md § 6).
- **Pytest floor 2634.**
- **Rulings this plan takes:**
  1. **Order.** Task 0. Then H0 (the harness) ∥ H1 (offline prototypes) ∥ H6 (store and privacy, jar plus offline). Then H2 (live sub-step costs) after H0. Then H3 (live scheduler shoot-out) after H0 and H2. Then H4 (player-visible) and H5 (fake clients, optional). Then Task M, then Task Z.
  2. **Decision 6's rules** (from review-platform X1). They are read at N = 60, DayLength 1 and DayLength 4, against the engine's frame period:
     - **(b), the budgeted per-tick scheduler,** is adopted if two things hold. First, the mod adds at most 20 ms at the 99th percentile and at most 25 ms at the maximum. Second, the alternative (the one-event burst) adds more than 33 ms or pushes a frame over 133 ms. The scheduler must also not aggravate: its empty-queue check adds at most 0.1 ms a frame, and its total frame time over a game minute is at most 1.1 times the burst's.
     - **(c), a round-robin of m = 2,** is admissible only if it meets the same bounds and Angus adopts Appendix H's fairer band.
     - **(a), the one-event design,** is admissible only if the burst itself stays at most 25 ms at N = 60.
     - The thresholds are this plan's. If H4 shows a player cannot notice a frame below some length, the controller rewrites them by ruling before H3's analysis, never after.
  3. **The shipped 1.0.0 drain starves players.** It rebuilds its queue each minute and serves one player a tick (`NR_Server_Players.lua:49`, `:82–95`). So at N = 60 only about 6 players a game minute run at DayLength 1, and about 37 at DayLength 4. The current tree is therefore not a 60-player baseline. H3 measures the shipped drain only as a starvation reading, and its cost arms use the designs under test. Task 0 records the bug in the memo for Plan 11 Task 2.
  4. **A prototype that changes the golden trace is a finding, not a fix.** It is reported with the first differing leaf.
  5. **Not this plan:** any change to the mod, the fixes themselves, or a reading from a populated public server. That last one needs Angus (E7), and the memo names it as his to supply.

## Execution order

Task 0 → { H0 (Opus; harness) ∥ H1 (Opus; offline) ∥ H6 (Opus; jar plus offline) } → H2 (Opus; live) → H3 (Opus; live) → H4 (Opus; live) → H5 (Opus; live, optional) → Task M → Task Z. Every review is Opus. A scoped re-review is Sonnet.

## File structure

| path | responsibility | task |
|---|---|---|
| `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua` (append), `docs/reference/harness-commands.md` (generated) | `tick.ring`, `perf.local`, the ghost-load commands | H0 |
| `testing/pzt/server.py` (one flag) | the opt-in `-Xlog:gc*` launch flag for a profile | H0 |
| `testing/spikes/proto/<name>/` (copies of the mod's Lua), `testing/spikes/proto_*.py`, `testing/spikes/out/proto-*` | offline prototypes and their golden-trace diffs | H1 |
| `testing/spikes/store_size.py`, `testing/spikes/out/store-*` | the record serialisation size | H6 |
| `release/hitch-<HEAD>/` (gitignored) | staged copies with the sub-step timers and schedulers | H2, H3, H4 |
| `testing/spikes/instruments/x24*_*.lua` | each run's instrument file, kept | H2, H3, H4 |
| `testing/experiments/x24{1..5}_*.py`, `testing/profiles/x24-*.toml`, `testing/artifacts/x24*-*/` | the live sessions | H0 smoke, H2–H5 |
| `docs/superpowers/specs/2026-10-07-plan-11-decisions.md` (a "Hitching" section; Decision 6; Decision 3 if H6 flips it) | the memo | 0, M |
| owner pages the rows name (`docs/platform/lua-platform.md`, `docs/platform/mp-model.md`, `docs/areas/testing-your-mod.md#walls`, `docs/platform/harness.md`) | the rows' sentences | H0–H6, M |

---

### Task 0: Workspace, and the two findings Plan 11 must not lose — controller

- [ ] `scripts/sdd-workspace docs/superpowers/plans/2026-10-07-plan-10c-hitching-experiments.md`. The ledger's first block copies the two reports' top risks and this plan's rulings.
- [ ] In the memo, under "Re-basing the draft", Task 2, add a line:
  - The shipped drain starves players on a normal clock whenever more players are online than there are ticks in a game minute: 53–54 of 60 at DayLength 1, 22–23 at DayLength 4 (review-mod-architecture risk 2; review-platform concern 1).
  - Task 2 must cover that case, not only the fast clock.
- [ ] In the memo, under Decision 3, add a line:
  - A client may be able to `ModData.request` the store's key and receive every player's record. H6 reads it.
  - If it can, that is a privacy fix for Plan 11 whatever Decision 3 says.
- [ ] Commit the memo by pathspec.

---

### Task H0: The frame-time instrument and the synthetic load — Opus implementer (harness, then a smoke run), Opus reviewer

**Questions:** Can the harness read a server frame's length? Can two clients carry N players' minute work?

**Interfaces (harness, server side):**
- `tick.ring <n>`: arm a ring of the last n frames' wall times, measured from `OnTickEvenPaused` to `OnTick` and from `OnTick` to `OnTick`. The reply is the ring with p50, p99 and max.
- `perf.local`: the engine's `getPerformanceLocal()` frame-period figures (min, max, average), read once a second into a ring.
- `ghost.load <N> <scheduler>` and `ghost.stop`: create N−2 ghost records (deep copies of the two real players' records under synthetic usernames) and run each ghost's `P.work`-equivalent against a real player object. The real player object is chosen round-robin from the two online players.
  - The scheduler is one of `burst`, `rr<m>`, `drainTicks` (the drafted spread over the minute's ticks) and `budget<ms>` (a queue drained each `OnTick` until a ms cap or a run cap from a running mean).
  - The harness owns ghosts. The staged copy's adapters run them unchanged. A ghost's record lives in a harness table, never in the mod's store.
- `ghost.stats`: runs, players never run in a minute (starvation), staleness per ghost in game minutes, and runs per frame.
- A profile key `[server] gclog = true` adds `-Xlog:gc*:file=<run>/gc.log` to the server's launch.

Steps:
- [ ] **Step 1: Read.** Cover the harness's server file and how it registers commands, `testing/pzt/server.py`'s launch line, `docs/platform/harness.md`, review-platform's question 5, and the staged copy's `NR_Server_Players.lua` (`P.work`, `P.minute`, `P.drain`).
  - Decide how a ghost reaches the pipeline: through `NR.server.minute.run(username, player, record)` with a harness-held record, keeping `P.work`'s `lastSeen` and dead checks in the harness's copy of it.
  - State the choice in the comment block.
- [ ] **Step 2: Write the commands.** Append them at the end of the harness file (CLAUDE.md § 5).
  - The schedulers' code lives in the harness, so H3 compares them without editing the mod.
  - Kahlua rules: no `goto`, no `%d` on floats, no `#` on Java lists.
- [ ] **Step 3: Check and commit.**
  - Run `python tools/luabalance.py` on the HEAD copy, then on the working tree.
  - Run `python tools/bus_inventory.py`, and update `#2808` and `#1235` if the count line moves.
  - Run `python tools/kahlua_lint.py testing/PZTestKit` → 0, and pytest at or above 2634.
  - Commit: `Harness: tick.ring, perf.local, ghost.load and the gc log, before x241`.
- [ ] **Step 4: The smoke run, x241.** Use fixture `two` and the staged copy `release/hitch-<HEAD>/` with no instruments added. Read:
  - `tick.ring` and `perf.local` over 120 s idle;
  - the same with `ghost.load 20 burst` for 3 game minutes;
  - `ghost.stats`.

  The readings to take:
  - whether `perf.local`'s max and the ring's max agree within 2 ms at p99 (review-platform X0); if not, the engine's figure is the hitch reading from here on, by ruling;
  - the ghost burst frame's length at N = 20 against 20 × 1.583 ms (#3387);
  - whether ghosts starve.

  Commit the profile and driver before the run. The artifact goes to the controller.
- [ ] **Step 5: Hand over.** Write the delta (`T112.n`, owner `docs/platform/harness.md` for the instrument and `docs/platform/lua-platform.md` for the frame order if read), the memo notes and the report.

---

### Task H1: Offline prototypes against the golden trace — Opus implementer, Opus reviewer

**Questions:** Which behaviour-free refactors cut the minute's cost, and by what relative share (lupa is C Lua: shares, not milliseconds)? Which slow-tier period K keeps the trace inside the fairer band?

**Files:** `testing/spikes/proto/{heal1,hoist,slowK}/` (each a copy of `mod/NutritionRevamp/common/media/lua/` with one change), `testing/spikes/proto_run.py`, `testing/spikes/out/proto-*.{json,md}`.

- [ ] **Step 1: A lupa profiler.** In `proto_run.py`, run `golden_trace.run` with the server path pointed at a copy, and time each pipeline step and named sub-block with `os.clock` (lupa has it). Report each block's share of the step and of the pipeline, over the whole golden scenario. Run the unmodified copy first: that is the baseline (review-mod-architecture E1, offline half).
- [ ] **Step 2: heal1** (E2). Heal once after the step instead of in every adapter, with lazy key prefixes.
  - The trace must reproduce byte for byte.
  - Run the Plan 10 mutation pass on the copy: inject the NaNs the heals guard against, at each adapter's input, and show each injection is still caught.
  - Report the share saved.
- [ ] **Step 3: hoist** (E3). Cache `dialExp` and the ladders across minutes, and compute one shared `exp(-dtD)` a minute. The trace must reproduce byte for byte. Report the share saved.
- [ ] **Step 4: slowK** (E4). Move the 27 nutrient records, the excess ladder and the effects rebuild to a slow tier that runs every K minutes in per-player slots, at K = 5, 10, 30 and 60.
  - Diff against k = 1 with P2's `compare` and P2's fairer band (Appendix H).
  - Report the largest K with no band or grade flip beyond a K-minute delay.
  - Report the per-minute cost share that leaves the minute.
- [ ] **Step 5: Commit and hand over.** Run each prototype twice to show determinism. Commit by pathspec: `Spike H1: offline prototypes (heal once, hoisted constants, a slow tier) against the golden trace`. Write the delta (`T113.n`, C rows, bound "inference; an offline simulation", owner `docs/areas/testing-your-mod.md#walls`), the memo section and the report.

---

### Task H6: The global store — its save, its size, and who can request it — Opus implementer (jar plus offline), Opus reviewer

**Questions:**
- On which thread, and how often, is global modData saved?
- How large is one record serialised, and how large is the store at 100, 500 and 2000 records?
- Can a client `ModData.request` the store's key and receive the table?

- [ ] **Step 1: The jar.** Read `GlobalModData` save and request handling, `ServerMap.QueuedSaveAll` and the request packet's server handler, with `./pz.sh refs` and `dump`. Cite class.method for each answer. Say whether a request for an arbitrary key returns that key's table to any client, and whether a mod can refuse it.
- [ ] **Step 2: Offline size.** Write `testing/spikes/store_size.py`. It serialises the golden trace's final records the way the save does (read the format from the jar) and reports the bytes per record and at 100, 500 and 2000 records.
- [ ] **Step 3: Live, only if Step 1 leaves the save's cost open.** Add one arm to H2's session: seed 100, 500 and 2000 synthetic records into the staged copy's store, force a save, and read the frame ring.
- [ ] **Step 4: Rules and hand-over.**
  - If 500 records exceed about 1 MB, or a main-thread save overruns 25 ms at 500, Decision 3's recommendation flips to pruning on, with an inputs-only store as a Plan 11 candidate.
  - If any client can request the key, that is a privacy blocker for Plan 11, named in the memo.
  - Write the delta (`T118.n`; owner `docs/platform/mp-model.md` for the request path), the memo section and the report.

---

### Task H2: Sub-step and burst-source costs, live — Opus implementer, Opus reviewer

**Questions:**
- Where inside Nutrients, Metabolism and Effects does the time go?
- What do a day-close minute, a seven-close catch-up, a deficient player's minute, first sight and one mirror send cost?
- What does the client tooltip cost?

These come from review-mod-architecture E1, E9, E10 and E12, and review-platform X4 and X5.

- [ ] **Step 1: Instruments.** Work in `release/hitch-<HEAD>/` only. Put sub-block timers inside the three steps, at the blocks H1's lupa profile ranked highest (H1 must have reported first, or use review-mod-architecture's named blocks). Add bench entries for one day close, a seven-close catch-up, one first sight (a store load plus `ensureBody`) and one mirror send (`sendServerCommand` with the real payload). Keep the file under `testing/spikes/instruments/`.
- [ ] **Step 2: The session, x242.**
  - **A.** In play, at DayLength 1, for 120 game minutes, crossing 07:00 twice. Force the day boundary with `time.set` if the harness has it; otherwise use `settimespeed` to reach it.
  - **B.** A deficient arm: one player's record seeded deficient in vitamin C and iron through `lua.setpath`, then 60 game minutes.
  - **C.** The benches, run 1000 times each, interleaved: the day close, the catch-up, first sight, the mirror send.
  - **D.** A client bench of `T.entryFor`, run 1000 times.
  - **E.** H6's live arm, if H6 asked for it.
- [ ] **Step 3: Rules.**
  - A sub-block at 15 % or more of its step is a refactor target.
  - A day-close minute at more than 3 times the typical minute must go through the scheduler.
  - First sight costing more than 2 ms per joiner is queued.
  - 60 mirror sends costing more than 5 ms get a per-player jitter.
  - A tooltip build over 50 µs moves its same-item check first.
- [ ] **Step 4: Hand over.** The artifact goes to the controller. Write the delta (`T114.n`), the memo section and the report.

---

### Task H3: The scheduler shoot-out at N = 20, 40, 60 — Opus implementer, Opus reviewer

**Question:** Which scheduler minimises the worst server frame at N = 60, without starving a player and without aggravating the total? This answers Decision 6 by ruling 2 (review-mod-architecture E5, E6, E8; review-platform X1, X6).

- [ ] **Step 1: The session, x243.** Use a profile with `gclog = true`. For each N in 20, 40 and 60, at DayLength 1, and then at DayLength 4 through `time.multiplier` (#3394 shows the live DayLength set does not take), run each scheduler for 10 game minutes:
  - `burst`;
  - `rr2` and `rr5`;
  - `drainTicks`;
  - `budget5`, `budget10` and `budget15`.

  For each, read `tick.ring` (p50, p99, max), `perf.local` and `ghost.stats` (starvation, staleness, runs per frame). Add:
  - a fast-clock arm, `settimespeed 30` at N = 60, for `burst` and `budget10`;
  - a day-boundary arm, N = 60 across 07:00, for `burst` and `budget10`;
  - one arm with the shipped drain at N = 60, reading starvation only (ruling 3).

  Order the arms so no scheduler always runs first; state the order.
- [ ] **Step 2: Analysis.**
  - Apply ruling 2's rules at N = 60 and both day lengths.
  - Give a table of N × scheduler × day length showing worst frame, p99, total ms a game minute, starvation and staleness.
  - Line the GC log's pauses up against the minute frames (X6).
  - State whether the budgeted drain's empty check and its total meet the no-aggravation bounds.
- [ ] **Step 3: Hand over.** The artifact goes to the controller. Write the delta (`T115.n`), the memo section with Decision 6's measured answer, and the report.

---

### Task H4: Does a player notice? — Opus implementer (live), Opus reviewer

**Question:** Under the one-event burst at N = 60, does a client see a stutter in world updates that the budgeted drain does not cause (review-platform X2)?

- [ ] **Step 1: Read.** Check `harness-commands.md` for a client-side read of a nearby zombie's or the other player's position. If there is none, add a client command `world.posring <n>` in its own harness commit before the run (H0's rules). It records, each client frame, the other player's and the nearest zombie's position and the local time.
- [ ] **Step 2: The session, x244.** At N = 60 ghosts, admin and bob stand near each other near a few zombies. Run `burst` for 5 game minutes, then `budget10` for 5, then `burst` again. Read both clients' rings and the server's `tick.ring`.
- [ ] **Step 3: Rule.** The burst counts as evidence for (b) when two things hold. First, it shows update gaps of 100 ms or more at the minute frames' frequency, lined up with them. Second, the drain shows none. If neither shows gaps, a frame below the burst's length is not noticeable at this load. Rewrite ruling 2's thresholds by ruling before H3's analysis is final.
- [ ] **Step 4: Hand over.** The artifact goes to the controller. Write the delta (`T116.n`), the memo section and the report.

---

### Task H5 (optional): Real load from the engine's fake clients — Opus implementer (live), Opus reviewer

**Question:** Can 42.20.4's `zombie.network.FakeClientManager` join the harness's `-nosteam` server? If it can, does H3's answer hold with real player objects, with vanilla's own per-player cost included (review-platform X3; it would partly answer E7)?

- [ ] **Step 1: Read.** Read `FakeClientManager` with `./pz.sh methods` and `dump`: its main, its arguments and its login path. Decide whether it can run from the install read-only, with the classpath only. Never write into the install.
- [ ] **Step 2: Join.** In one session, x245, add fake clients in steps of 5. Read whether each joins and holds, and the frame ring at each step.
- [ ] **Step 3: Rule.**
  - If 58 hold for 10 minutes, rerun H3's `burst` and `budget10` arms on real players at N = 60.
  - If none join in this session, H5 ends as "not reachable on 42.20.4", with the failure read, and is not retried.
- [ ] **Step 4: Hand over.** The artifact goes to the controller. Write the delta (`T117.n`), the memo section and the report.

---

### Task M: The decision memo's Hitching section — Opus writer (per Plan 10b's ruling M-1), Opus review

- [ ] Add a "Hitching (Plan 10c)" section to the memo, after the Performance section. It covers:
  - the frame instrument and how far it can be trusted;
  - the sub-step costs and the refactor targets;
  - the prototypes' savings;
  - the store's size, its save and the request finding;
  - the scheduler table with Decision 6's measured answer;
  - whether a player notices;
  - the fake clients' result.
- [ ] Rewrite Decision 6 with the measured answer and its rule. Update the ranked refactor list and Decision 3 if H6 flipped it. Name what still needs Angus: the populated-server reading (E7), and the fairer band if (c) is in play.
- [ ] The controller applies the deltas in task order (`T112` … `T118`), writes the owner sentences with the writer, runs the gates and commits.

---

### Task Z: The close — controller

- [ ] Run the whole-pass review (Opus, read-only), one consolidated fix wave, and its re-review.
- [ ] Run every § 3 gate, plus pytest at or above 2634. Push. Update memory in both scopes. Write the Rulings block and the § 7 list in the ledger, then `Plan 10c: complete`.

## Self-Review

- **Coverage.** Every experiment in both reports is mapped to a task:

| Experiments | Task |
|---|---|
| E1 | H1 (offline) and H2 (live) |
| E2, E3, E4 | H1 |
| E5, E6, E8 | H3 |
| E7 | named for Angus (ruling 5); partly H5 |
| E9, E10, E12 | H2 |
| E11 | H6 |
| X0 | H0 |
| X1 | H3 |
| X2 | H4 |
| X3 | H5 |
| X4, X5 | H2 |
| X6 | H3 (GC log) and H1 (lupa) |
| X7 | H6 |
| X8 | left out: it matters only if work is ever sliced below one player |

- **The two findings Plan 11 must not lose** (the starvation bug, the request exposure) are written into the memo at Task 0, before any experiment runs.
- **Placeholders.** `<HEAD>` and the run stamps are filled at dispatch. The ghost design is decided in H0 Step 1 and stated in its comment block. The interfaces are named here.
