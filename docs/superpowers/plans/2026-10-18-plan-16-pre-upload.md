# Plan 16: the pre-upload fixes — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make NutritionRevamp ready for its first Workshop upload by:
- freezing every character completely while offline;
- giving the body rhythm a server-aware personal clock;
- fixing the fasting partition on the science;
- refusing a direct eat at Overfull 4 server-side;
- closing the replay and live-evidence gaps;
- re-staging the release.

**Architecture:**
- **Offline freeze:** a single resume step at each sight's first touch shifts every world-age stamp by the offline gap. The record day becomes an online-time clock, and a backup of the record rides on the character's modData.
- **Body rhythm:** the rhythm reads a per-character `acute.bodyHour` that runs only while online, resets on a full sleep and is absent on sleep-off servers.
- **Fasting partition:** fixed after a research pass.
- **The rest:** the eat refusal is a `serverStart` on `ISEatFoodAction`. The replay gains per-sip drinks, the cold multiplier and an old-liquid overlay. New harness commands and live sessions prove each change. The close re-stages and Angus uploads.

**Tech stack:**
- Kahlua Lua in mod/NutritionRevamp/common/media/lua;
- Python tools and pytest on the lupa 2.8 kernel host;
- the harness: testing/pzt, PZTestKit and the drivers on xlib.py;
- the jar toolchain at C:\Users\Angus\pz-b42, read-only.

**Spec:** docs/superpowers/specs/2026-10-18-pre-upload-design.md (ed5d8855). The brainstorm evidence is in .superpowers/sdd/plan-16-brainstorm/: offline-audit.md, plan14-findings.md, carries.md, circadian*.md.

## Global constraints
1. **Nothing changes offline (Angus, 2026-10-18).** A character resumes exactly as left. A test that pins offline integration as intended is rewritten to the freeze, never kept.
2. **The tuning rule.**
   - Subjective follows vanilla, objective follows science.
   - Every deviation is a labelled game choice in its code comment and in spec § 6.
   - This plan's game choices:
     - no body rhythm on sleep-off servers;
     - a full sleep of 4 h or more resets the body clock to 07:00;
     - the fast's death is whatever the science gives first.
3. **Rule 6: no per-tick work.**
   - Bench every per-minute change before and after, with the Java call-count stub.
   - The Plan 15 baseline is 70/68/76 Java calls per player-minute (steady, unfed, draining).
   - The sleep poll adds 2 Java calls per server minute, not per player.
   - The hour read is hoisted to once per server minute.
   - The record backup is written only at the store's save cadence.
4. **No compatibility code.** The mod is unreleased, so there are no migrations and no fallbacks for old saves.
5. **CLAUDE.md §§ 3–6 bind every task.**
   - The gates, register deltas and live rules apply.
   - Pathspec commits only.
   - The golden trace is re-recorded under a named cause, with every leaf attributed.
   - Pointers are re-anchored, or pinned only when a line is rewritten.
   - A § 3 gate reads 0 before a commit, and pytest is read from its own summary and exit code.
   - Model names: Opus for implementers and high-stakes reviews, Sonnet for scoped re-reviews.
6. **Lanes.**
   - One serial lane edits mod/ Lua and the kernel tests: Tasks 2, 3, 4, 5, 6.
   - The research task (Task 1) and the tools and harness tasks (Tasks 7, 8) may run beside it on disjoint files.
   - A live boot never overlaps a mod/ edit.

---

### Task 1: the fasting science pass (Opus; research, docs lane)
**Files:**
- Create `docs/superpowers/research/2026-10-18-fasting/partition-report.md`.
- Create a science part file `.superpowers/sdd/2026-10-18-plan-16-pre-upload/fasting-science.tsv`, for the controller's apply.

**Produces:** settled rows for what the Task 5 partition fix rests on. Each one is resolved against its record; the report says which were read in full and which only as abstracts.
- Alpert 2005: the fat-oxidation ceiling and the lean energy density it pairs with.
- Elia and Henry 1990: the protein share of energy against initial fat. This settles or supersedes S1056.
- Nitrogen excretion over a prolonged fast.
- The Keys 1950 body-composition series, where reachable (S0657, S0058).
- The share of weight lost as lean in prolonged starvation, by day.

- [ ] **Step 1:** Read plan14-findings.md § 1, `NR_Kernel_Partition.lua:15, 61-80` and the rows it cites (S0054, S0056, S2241, S2243, S0104, S1910, S2231–S2262).
- [ ] **Step 2:** Harvest and resolve the citations. Write the report, ending with a recommended partition form:
  - (a) drop the ceiling from the deficit arm;
  - (b) re-base it on a corrected lean energy density;
  - (c) keep it with a protein-sparing term.

  Give each its predicted lean share by day and its death outcome, for the default, Obese and Gaunt bodies.
- [ ] **Step 3:** Run `python tools/science_check.py --part <file>`; it must report 0. Return the report and the part file. The controller applies and commits them.

### Task 2: the offline freeze and the online record day (Opus; mod lane)
**Files:**
- The store and players: `server/NR_Server_Store.lua`, `server/NR_Server_Players.lua`.
- The resume, a new `shared/NR_Kernel_Resume.lua`. Its job is to list every world-age stamp in a record and shift it by a gap.
- The step clamps: `NR_Kernel_Body.lua:225-238`, `NR_Kernel_Satiety.lua:51`, `NR_Server_Kinetics.lua:57-59, 203-212`, `NR_Server_Metabolism.lua:36, 423-425`, `NR_Server_Nutrients.lua:354-367`, `NR_Server_Writer.lua:173-187, 266-273`.
- The intake's monotony decay at `NR_Server_Intake.lua:894-910`.
- `K.acute.skipRecord`, which folds into the resume.
- The tests that pin offline integration (offline-audit L1 lists them).

**Interfaces:**
- Produces `K.resume.shift(record, gapH)`, which moves every stamp listed in `K.resume.STAMPS` by `gapH`.
- Produces `K.resume.STAMPS`, the single list. A test fails if a record field ending `AgeH`, `At` or `Stamp` is missing from it.
- Produces `record.body.dayStartH`, the online record-day anchor. The day closes when `onlineH − dayStartH >= 24`.
- Produces an absence flag keyed on a new player object. A stall while online is integrated in sub-steps no longer than the existing step bound.

- [ ] **Step 1:** Write the failing tests. A character is logged out for 3 game days (and for 30 min, and for 59 min), then rejoins. Every record value and every written stat (HUNGER, THIRST, FATIGUE) must be byte-equal before and after, covering:
  - the stomach and meal pool;
  - nutrients;
  - fluids;
  - the body;
  - acute (caffeine, alcohol, hangover);
  - sleep;
  - monotony;
  - drain clocks;
  - the record day.

  Further tests:
  - a 3 h stall while online integrates fully, in sub-steps, with no booked sleep lost;
  - an eat landed before the first step back decays no monotony across the gap;
  - the day closes after 24 online hours, whatever the world day.
- [ ] **Step 2:** Implement the resume step at the first touch of every sight, in `S.get`/`S.load` before any step. Remove the 60-minute return integration. Move the day close to the online anchor.
- [ ] **Step 3:** Rewrite each test that pinned the old hour (the audit lists `test_kinetics.py:181/671/724`, `test_writer_shape.py:925/934`, `test_kernel_drain.py:580`), each named in the report with its successor.
- [ ] **Step 4:** Re-record the golden under "Plan 16 Task 2: the offline freeze and the online record day". Bench. Run the gates and the full claims_check. Run the full pytest in its own call. Commit.

### Task 3: no prune, the record backup on the character, the hard-kill case (Opus; mod lane)
**Files:**
- `server/NR_Server_Store.lua`, `server/NR_Server_Options.lua`;
- the sandbox and translation JSON;
- the mod README;
- a new `server/NR_Server_Backup.lua`.

**Interfaces:**
- Consumes `K.resume.STAMPS` and the store's codec.
- Produces `BK.write(player, record)`, called only at the store's save cadence. It writes a compact encoded copy of the record's INPUTS into the player's modData key `NutritionRevamp.backup`, together with a checksum and the world age at writing.
- Produces `BK.read(player)`, which returns a validated record or nil.
- Produces the load rule:
  - when the store file is missing or corrupt, restore from the backup;
  - when the store's stamps are ahead of the world clock (a hard-kill rollback), restore from the backup;
  - otherwise the store wins.

- [ ] **Step 1:** Remove `NR.RecordKeepDays`: the option, the translations, the prune at the minute and at boot, its tests (named in the report), and the README row and limitation.
- [ ] **Step 2:** Write the failing tests:
  - a deleted store file restores exactly from the backup;
  - a store record ahead of the world restores the backup, with no double integration and no re-landed food;
  - a backup wiped or edited by the client is rejected, the store is kept, and the backup is rewritten;
  - the backup is written only at the save cadence (a call-count test).
- [ ] **Step 3:** Implement. Measure the backup's size for the default record and a 30-day record, and report it. Mirror it to the owning client; the validation covers the #1042 wipe.
- [ ] **Step 4:** Golden, bench, gates, full pytest, commit.

### Task 4: the body clock and the sleep poll (Opus; mod lane)
**Files:**
- `shared/NR_Core.lua:217-226` (`NR.read.hour` and its fallback);
- `server/NR_Server_Options.lua` (the sleep poll);
- `server/NR_Server_Nutrients.lua:121-136, 453, 475`;
- `shared/NR_Kernel_Acute.lua:446`;
- `server/NR_Server_Writer.lua:311`;
- `shared/NR_Kernel_Satiety.lua` (`K.satiety.circadian`);
- `shared/NR_Kernel_HungerCurve.lua:96-125`;
- `server/NR_Server_Strength.lua:144` and `NR_Kernel_Strength.lua:543`;
- `server/NR_Server_Metabolism.lua:198` (its unused hour read is removed);
- the test host's `getTimeOfDay`.

**Interfaces:**
- Produces `NR.sleepOn()`, true when `isServer()` and `SleepAllowed` and `SleepNeeded` are all true. It is read in the per-minute options poll (2 Java calls per server minute).
- Produces `record.acute.bodyHour`, the body-clock phase in hours:
  - it advances by integrated online time;
  - it resets to 07.0 at the end of a main sleep of at least 4 booked hours;
  - it starts at the world hour on a fresh record, and at the world hour when sleep goes from off to on;
  - its phase is kept when sleep goes from on to off.
- Produces `K.circadian.hour(record, sleepOn)`: `bodyHour` when sleep is on, nil when it is off.
- **The three consumers:** the hunger factor, the fatigue `circ` and the carry morning halving each read `K.circadian.hour`. When it is nil, the hunger factor is 1, `circ` is 0 and there is no morning halving.

- [ ] **Step 1:** Write the failing tests:
  - sleep off gives a hunger factor of 1, `circ` 0 and no halving at every world hour;
  - with sleep on, bodyHour advances with online time and is unchanged across a 3-day logout (this uses Task 2's resume);
  - a 4 h sleep resets bodyHour to 07:00, while a 1 h nap and a 0.1 h accelerated bout do not;
  - an admin toggles sleep mid-game, and the poll follows it within a minute;
  - the `readHour` fallback is `(ageH + 7) mod 24`;
  - the hour read happens once per server minute (a call-count test).
- [ ] **Step 2:** Implement. Label both game choices in code (spec § 6).
- [ ] **Step 3:** Fix the test host's `getTimeOfDay` 7 h offset. Re-pin any study oracle that read the world hour, with the cause.
- [ ] **Step 4:** Golden, bench, gates, full pytest, commit.

### Task 5: the fasting partition (Opus; mod lane; after Task 1)
**Files:**
- `shared/NR_Kernel_Partition.lua`;
- its tests;
- `tools/mod_guide_series.py:59-62` (correct the stale comment).

**Interfaces:**
- Consumes Task 1's settled rows and recommended form.
- Produces the partition in which a prolonged fast's lean share follows the Forbes split. The fat floor can be reached.

- [ ] **Step 1:** Write the failing tests on the server replay, against Task 1's rows:
  - the lean share of energy by day in a water-only fast, for the default, Obese and Gaunt bodies;
  - the fat floor reached;
  - weight lost by day 45 within the rows' band.
- [ ] **Step 2:** Implement Task 1's form. Fit discipline applies (CLAUDE.md § 6): stability checks, and report any constant at a bound.
- [ ] **Step 3:** Report each body's death cause and day. Death follows the science; nothing is tuned to the strikers' range.
- [ ] **Step 4:** Re-score Plan 13's Strength oracles on the new partition. Report every move; re-fit only if one leaves its band.
- [ ] **Step 5:** Golden, gates, full pytest, commit.

### Task 6: the server-side refusal at Overfull 4 (Opus; mod lane)
**Files:**
- `server/NR_Server_Intake.lua` (or a new `server/NR_Server_EatGuard.lua`);
- tests.

**Interfaces:**
- Produces the `ISEatFoodAction.serverStart` wrapper, which refuses at Overfull 4 through `netAction:forceComplete()`. It sends the owning player vanilla's `Tooltip_CantEatMore`.
- Produces a `serverStop` guard: a refused or cancelled eat consumes nothing.
- It never wraps `new` (CLAUDE.md § 6).
- It is a stated exception to the intake's rule of always calling the original.

- [ ] **Step 1:** Read the jar and Lua precedents named in carries.md § 2. Confirm the refusal path on 42.21 and cite it.
- [ ] **Step 2:** Write the failing tests:
  - at Overfull 4 an eat is refused and the item's uses are unchanged;
  - below level 4 the original runs unchanged;
  - a refusal never raises: wrap it in the intake's rim guard.
- [ ] **Step 3:** Implement. Write the register-facing comment that this supersedes the Plan 15 Task 11 ruling (#3599 stays the vanilla fact).
- [ ] **Step 4:** Gates, full pytest, commit.

### Task 7: replay fidelity and the evidence corrections (Opus; tools lane)
**Files:**
- `tools/replay_live.py` and its tests;
- `testing/tests/kernel/test_*x332*`, `test_*x263*` (the replay tests that `at_build.py` currently runs);
- `docs/reference/artifacts.md` (x447's reading guide);
- CLAUDE.md § 5.

**Interfaces:**
- **Drinks:** `replay_live` lands a drink per sip over its action's duration (20 ms per unit of the action length; carries § 1).
- **The cold multiplier:** `replay_live` reads a `cold` ring field as an exogenous input when present.
- **The overlay:** `replay.LIQUID_SOLID_KCAL` restores the old liquid rule for rings recorded before Plan 15 Task 14b. It is replay-only and never used by the guide.

- [ ] **Step 1:** Write the failing tests.
  - A replayed drink spreads its landing.
  - With the `cold` field fed, x456 and x457's ring THIRST matches within 0.002.
  - x332 and x263 regain their full checks at HEAD through the overlay. These are the checks carries § 4 lists.
- [ ] **Step 2:** Implement. Remove the `at_build.py` pin for these two tests if it becomes unused. Add the two § 5 rules:
  - a replay test broken by a later rule change is restored through a named replay-only overlay;
  - a night driver polls `acute.winSleptH`, never the unbroken run.
- [ ] **Step 3:** Correct x447's reading guide (the mod booked 41.0 h asleep). Re-anchor the moved pointers.
- [ ] **Step 4:** Gates, the full claims_check, the full pytest, commit.

### Task 8: harness additions (Opus; harness lane)
**Files:**
- `testing/PZTestKit/...` (appended sites only; CRLF preserved);
- `testing/pzt` if a command needs it;
- `docs/reference/harness-commands.md`, regenerated;
- `#2808` and `#1235`.

**Interfaces:**
- **`tooltip.measure` (client):** takes an item type and an option flag. It runs vanilla's measure-only tooltip pass with the mod's band on or off and replies `{height, hungerLineDrawn}` (carries § 6).
- **The ring's `cold` field:** `body.coldMult`.
- **An offline-gap helper,** if the Task 9 freeze session needs one beyond a disconnect and a reconnect: a driver-side wait under a running clock.

- [ ] **Step 1:** Implement, appending at the end of each file. Run `tools/luabalance.py` on the HEAD copies, then the working tree. Run `tools/bus_inventory.py` to regenerate the command table. Update #2808 and #1235.
- [ ] **Step 2:** Add offline tests of the reply shapes.
- [ ] **Step 3:** Commit, in its own commit, before any run that uses it.

### Task 9: live sessions (Opus; live; after Tasks 2–8)
**Files:**
- `testing/experiments/x461_*.py` to `x466_*.py`, on a new `x46_lib.py` built on xlib;
- the profiles;
- the artifacts.

**Sessions** (each under 10 minutes, booting the STAGED copy):
- **x461, water beside a meal:** a 667 kcal plate, then 500 mL of water at once. Then x363's water, milk and solid sequence, with the `cold` field. This restores the guide's SE1 live lines and settles #3947.
- **x462, the tooltip hide:** `tooltip.measure` with the hide on and off.
- **x463, the offline freeze:** a logout for 3 or more game days, then a rejoin; every value unchanged. Plus a hard-kill arm: the store is restored from the character's backup.
- **x464, the body clock:** with sleep on, a full sleep resets bodyHour to 07:00. With sleep off, there is no rhythm.
- **x465, a fast-forwarded night:** every player asleep; the night books with no loss to a stall.
- **x466, the server refusal:** a directly queued eat at Overfull 4 is refused, and the item is untouched.

- [ ] **Step 1:** Write the drivers offline, with a failing case for every grade, predictions from a HEAD replay of each exact schedule (the first sight included), and preboot against the real staged copy. Stop for the driver review.
- [ ] **Step 2:** Run the sessions one at a time, under every § 5 rule. Commit each artifact with its row, guide and do-not-cite rows.
- [ ] **Step 3:** The live-evidence review, then a fix round.

### Task 10: registers and pages (Opus; docs lane)
- [ ] **Step 1:** Write one delta.
  - **Supersede** the rows these changes overturn:
    - the 60-minute return integration;
    - RecordKeepDays;
    - the world-hour rhythm rows;
    - the partition and fast-death rows;
    - #3599's ruling text;
    - x447's reading.
  - **Mint** the C/inference mechanism rows and the M rows for x461–x466, and update the owner sentences.
  - The trial apply runs on a `git archive` copy. Then the whole-delta review, a fix round, and the controller's apply.

### Task 11: the guide (Opus)
- [ ] **Step 1:** Update `tools/mod_guide_series.py` and the page for:
  - the fasting outcomes;
  - the restored SE1 live lines;
  - the offline rule;
  - the body clock and the sleep-off servers;
  - the server refusal;
  - the corrected limitations.
- [ ] **Step 2:** Run `--write`, then `--check`. Run the page tests and a review.

### Task 12: pre-upload checks and the re-stage (Opus; live, last)
- [ ] **Step 1:** Re-stage `release/NutritionRevamp` from HEAD (`tools/release_pack.py stage`).
- [ ] **Step 2:** Run boot A on fixture two: set one `[sandbox.NR]` value in the server's options file and read it back on the server, the admin and bob. This doubles as the clean release join.
- [ ] **Step 3:** Run boot B: a one-byte comment change in one Lua file on bob's client, which should get the checksum kick.
- [ ] **Step 4:** Commit the artifacts, rows and guides.

### Task 13: the close (controller)
- [ ] Run the whole-pass review, one consolidated fix wave and its re-review.
- [ ] Update the README, CHANGELOG and COMPATIBILITY.
- [ ] Run every § 3 gate and the full pytest, update the CLAUDE.md baseline and the memory files, and push.
- [ ] Re-publish the guide, and hand the staged copy to Angus.

## Self-review
| Spec section | Task |
|---|---|
| § 1.1, 1.2 | 2 |
| § 1.3, 1.4 | 3 |
| § 1.5 | 10, 11 (limitations) |
| § 1.6 | 2, 3, 9 (x463) |
| § 2 | 4, 9 (x464, x465) |
| § 3.1 | 1 |
| § 3.2–3.4 | 5, 11 |
| § 3.5 | 5 |
| § 4.1 | 6, 9 (x466) |
| § 4.2, 4.4 | 10, 11 |
| § 4.3 | 7, 11 |
| § 5.1, 5.4 | 7 |
| § 5.2 | 8 |
| § 5.3 | 9 |
| § 5.5 | 12 |
| § 5.6 | 10, 11, 13 |

**Interfaces and order:**
- Task 2's `K.resume` is consumed by Tasks 3 and 4.
- Task 1 precedes Task 5.
- Task 8 precedes Task 9.
- Task 12 runs on the final bytes, after Task 11.
