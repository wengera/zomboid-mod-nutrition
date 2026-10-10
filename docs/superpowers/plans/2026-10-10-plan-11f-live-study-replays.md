# Plan 11f: Live study replays — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Judge the satiety, energy, nicotine and monotony model in the live game. Replay each study effect on a dedicated server across different food intakes and spans of game time. Grade every live reading two ways:
1. Against an offline replay of the same live events through the real kernels. This shows the mechanics hold live.
2. Against the study. This is already pinned by the oracles, and is re-read wherever the live inputs equal the study's.

Angus, 2026-10-10: "judge with some thorough in game testing and make sure based on different food intakes and game time elapsed that we get the effects the studies indicate".

**Architecture:**
- Two harness additions:
  - H1: one multi-path read of the mod's record.
  - H2: a server-side per-game-minute ring log.
- One experiment mod, `TKX_StudyFoods`, declaring foods with the oracle vectors.
- One offline replay-of-live tool, which steps the real kernels over a run's minute log.
- Then one live task per scenario group. Each is a chain of sessions of 15 minutes or less, each session its own driver. The world persists between sessions by reusing the previous session's server folder.

**Tech Stack:**
- Lua 5.1 (Kahlua) harness and mod.
- Python drivers under `testing/experiments/`.
- `testing/pzt`.
- lupa 2.8 for the replay tool.

**Spec:**
- `docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md`: the facts, the scenario table in § 6, and the blockers.
- The oracles:
  - `testing/tests/kernel/test_satiety_meal_studies.py`;
  - `test_satiety_activity.py`;
  - `test_writer_shape.py`;
  - `test_kernel_monotony.py`.

## Global Constraints
- **The rules.** CLAUDE.md § 5 governs every live step:
  - run doctor before every boot;
  - at least 12 GB free, read and ledgered before every boot;
  - one live session at a time, and no `mod/` edit during one;
  - a driver runs 15 minutes of wall time or less, is committed before its boot, and is never edited after its run;
  - never use `-safemode`;
  - never kill a stray `ProjectZomboid64.exe`;
  - artifacts are committed byte-identical, with an artifacts-register row and do-not-cite keys;
  - the server-log grep excludes probe names;
  - `Nutrition = false` in every profile;
  - the staged copy is booted as Plan 11b's profiles do.

  CLAUDE.md §§ 3, 4 and 6 govern commits, the register and the SDD process.
- **One client.** Only fixture `default` is used, because about 13 GB are free. Arms that the research ran in parallel run sequentially, as admin arms (ruling 11f-3).
- **Pre-registered tolerances** (research § 6), fixed before any run:
  - a request minute within ±3 game minutes or 2 %;
  - a HUNGER sample within 0.002;
  - es within 0.005;
  - a factor (circadian, sleep, nicotine, acute) within 1 % of the replay's;
  - a monotony delta within 0.05;
  - L and es within 0.5 % (exercise lag).

  A reading outside its tolerance is a finding. It is never re-run to make a number prettier (§ 5).
- **Grading.** Live vs replay-of-live is the gate. Replay vs study is the oracle's pin: it is re-graded against the study wherever the live inputs equal the oracle's; otherwise the distance is reported as a reading.
- **Mod defects.** A mod defect found live is ruled on by the controller and fixed in its own lane-M task (with the golden re-record rule) before the affected scenario is re-run as a new run with a new driver. The defective run stays recorded.
- **Models.** Live and evidence tasks use Opus implementers and Opus reviewers. Spelled-out harness or tool edits may use Sonnet.

## The rulings this plan carries
- **11f-1 (order).** Plan 11f runs before Plan 11b. It absorbs the live satiety, sleep, exercise, nicotine and monotony reads of the 11b amendments (11c, 11d and 11e sections). Plan 11b keeps the scheduler shoot-out, the release and the release package's acceptance. Angus asked for this testing now; release follows it. Cost if wrong: 11b's Task 4 repeats a few reads.
- **11f-2 (clock).** Every fast row is conditional on S0: DayLength 1 with `settimespeed 5`, at 0.99 or more writes per player per game minute. If S0 fails, those rows run slow and the session count grows. The plan does not change; each live task re-counts its sessions.
- **11f-3 (one client).** Arms run sequentially on admin. A "fed" or comparison arm may be the replay-of-live of the same body, with the arm's events in place of the live ones, labelled as such.
- **11f-4 (out of reach live).** These are named, not hidden:
  - the liquid preloads with the oracle compositions;
  - aerobic acute-suppression rises;
  - Whybrow's days 3–16, E-MECHANIC's 24 weeks, S1576's 48-day mean and S1577's week 26.

  The nicotine fade is read by moving `satiety.nicH`.

  Absolute study numbers measured on the oracle's 70 kg man are graded on a replay of the live body, and the distance is named.
- **11f-5 (exercise rise).** Task 6 gates two candidate vigorous paths: melee swings at an RCON-spawned zombie, and the heaviest Fitness exercise the server bills. If neither bills a MET of 6.0 or more, the rise leg is recorded as unmeasured live (with its MET readings). A synthetic MET injection is not added, because it would test the harness, not the game.

---

### Task 0: Gate and workspace (controller)
- [ ] Create the workspace and its ledger.
- [ ] Ledger the baseline (pytest 3473; register #3657; golden c53794a2), rulings 11f-1 to 11f-5, the tolerances, and free memory.
- [ ] Write the pre-flight scan table, then dispatch Task 1.

### Task 1: Harness H1 and H2 (Opus; harness lane; its own commits)
**Files:**
- `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server}/…`, with new sites appended at the end of each file (CRLF files keep CRLF);
- `docs/reference/harness-commands.md`, regenerated;
- `#2808` and `#1235`'s quotes, per CLAUDE.md § 5, the one register edit allowed.

**H1, `lua.read <root> <path> [<path> ...]`** (both sides):
- Reads several dotted paths from a root (a global, or the mod's record for a user through the mod's own accessor; name the accessor after reading `NR_Server_Store.lua`).
- A segment may be numeric (`trail.kcal.3`), or a bracketed string key (`monotony.t.[Base.Bread].n`).
- Returns `{path: value}` scalars, with nil or absent named.

**H2, `minute.ring <user> start <fields…> | read [<from>] | stop`** (server):
- On each game-minute event, appends one row per watched user to a bounded ring, holding:
  - world age;
  - the minute event's dtM;
  - written HUNGER, THIRST and FATIGUE, BOREDOM, UNHAPPINESS and NICOTINE_WITHDRAWAL (one `stats` read);
  - the H1 paths named at start.
- Bounded: 4,320 rows, which is 72 game hours at one per game minute. Rows past the bound overwrite and are counted.
- Read in pages.
- Rule 6 does not apply to the harness, but the cost per row must be measured with `bench.global` and reported.

Then:
- [ ] Run the balance check (`tools/luabalance.py`, HEAD then the working tree), `bus_inventory.py`, `kahlua_lint`, and the offline tests for the harness's Lua host, if they exist.
- [ ] Update #2808 and #1235 per § 5.
- [ ] Commit. Its smoke test is Task 3's first session.

### Task 2: `TKX_StudyFoods` and the replay-of-live tool (Opus; offline)
**`testing/experiments/TKX_StudyFoods/`** is an experiment mod, installed only through test profiles. Item scripts and the mod's own declaration path (read how the mod reads a food's vector: `NR_Data_Nutrients.lua`, the item pass and `IN.foodTypeOf`) give each food the oracle's vector:
- `Mixed650`, `Mixed400`, `Mixed217`, `Mixed667`, `Mixed333`;
- `SnackP`, `SnackC`, `SnackF` (239 kcal, with the oracle's shares);
- `Casserole` and `Soup` (Rolls 1999);
- `Marc`, the Marciani solid;
- `Dense400`;
- water-only foods of 100–600 g;
- `Mono450`, a non-staple;
- `Staple450`, FoodType Bread;
- a 50 kcal unit.

Every food has its boredom and unhappiness change set to 0. If the mod cannot take a declared vector for a non-vanilla item, stop and report.

**`tools/replay_live.py`** loads the run's ring and event log into the lupa kernel host and steps the real kernels and writer adapters minute by minute, with the live dtM. It emits the same fields as the ring.

**Its own oracle.** Fed the event lists the oracle tests use, it must reproduce their pins exactly:
- 312 min;
- 1.304 / 0.986;
- 0.994;
- 9.978;
- 1.1304.

It must also pass a mutation pass.

Then:
- [ ] Write tests for both pieces (`tools/tests/`, `testing/tests/`).
- [ ] Commit.

### Task 3: S0, the cadence gate, plus session chaining (Opus; live)
- [ ] Session 1 (driver `x260_cadence.py`, profile `x26-cadence.toml`):
  - boot the staged copy with `TKX_StudyFoods`;
  - read S0 at speed 1, then at `settimespeed 5` (research table row S0);
  - exercise H1 and H2 (their smoke test);
  - eat one `Mixed650` by `eat.action` and confirm it books;
  - end with the departure-flush procedure (research § 2).
- [ ] Session 2 (`x260b_chain.py`): boot that server folder again with `reuse=True`. Confirm the record, P, the trail and the world clock persisted. This is the first live file-store restart.
- [ ] Copy the artifacts and add the register rows (the controller mints).
- [ ] Rule S0 pass or fail, and re-count the sessions for Tasks 4–9.

### Task 4: Meals (rows 1, 2, 3, 4 and 5) (Opus; live; about 7 sessions)
One driver per session. Each step:
1. Run the research row's driver actions.
2. Read the ring, then run `replay_live.py`.
3. Grade against the tolerances.

Row 4 is live vs replay only (ruling 11f-4). Report every row as a table: reading, replay, tolerance, verdict, and the study figure with its distance.

### Task 5: Energy (rows 6, 7 and 8) (Opus; live; about 5 sessions)
- **Rows 6 and 7:** the 36 h fast chain, with request-level eating by research § 3.7 form 1.
- **Row 8:** six meals against three. Run the arms as sequential days on admin, or one arm live and one as a replay, per ruling 11f-3.

### Task 6: Exercise (rows 9 and 10) (Opus; live; about 4 sessions)
- [ ] Gate the vigorous paths (ruling 11f-5), then read the decay leg.
- [ ] Run the 7-day lag chain.

### Task 7: Sleep (row 11) (Opus; live; about 2 sessions)
Use a profile with SleepAllowed and SleepNeeded true. The replay uses the booked asleep minutes.

### Task 8: Nicotine (row 12) (Opus; live; about 1–2 sessions)
- Gate first: confirm the smoke completes with a lighter.
- Read the T2-F first-seen case and the fade by moving the anchor.

### Task 9: Monotony (row 13) (Opus; live; about 2 sessions)
1. Run five days of `Mono450` and `Staple450`.
2. Check:
   - client arrival of the BOREDOM and UNHAPPINESS changes;
   - the effects floor.
3. Read the steady UNHAPPINESS climb under the +16.6/day question, and hand it to Angus with every option's downsides.

### Task 10: The record (Opus; docs lane)
1. Write the artifacts rows and do-not-cite keys for every run.
2. Write the delta: live rows (M grade, n per run) on their owner pages, for:
   - body-effects#hunger-from-satiety;
   - effects-seats;
   - testing-your-mod#walls, for the harness and the replay tool;
   - lessons, for any platform finding (framed as a rule, with its mechanism row).
3. Settle the open rows the runs answer:
   - #3637, the nicotine read live;
   - BOREDOM's client arrival;
   - the file-store restart;
   - the eat duration under `settimespeed`.

   For each: the experiments and wall-map rows, and the line removed from `open-questions.md`.

### Task 11: The close (controller; Opus whole-pass review)
1. Run the whole-pass review, then one fix wave and its re-review.
2. Run the § 3 gates.
3. Update CLAUDE.md and memory.
4. Rewrite the 11b amendments so they say which reads 11f absorbed.
5. Push.
6. Report to Angus: every scenario's verdict, the study effects confirmed live, those confirmed only in the replay, those out of reach, the findings, and the +16.6/day decision with its options.

---

## Self-Review
- **Coverage.** Every row of research § 6 maps to a task:
  - S0: Task 3;
  - rows 1–5: Task 4;
  - rows 6–8: Task 5;
  - rows 9–10: Task 6;
  - row 11: Task 7;
  - row 12: Task 8;
  - row 13: Task 9.

  Blockers 1–4 map to Tasks 1–3. Blocker 5 maps to ruling 11f-1. Blocker 6's gates sit inside Tasks 3, 6 and 8.
- **No placeholders.** The live tasks name their research rows, which hold the exact actions, readings and pass criteria. Each live implementer copies its row into the driver's docstring before committing the driver.
- **Consistency.** `lua.read`, `minute.ring`, `replay_live.py` and `TKX_StudyFoods` are each named once and used as named.
