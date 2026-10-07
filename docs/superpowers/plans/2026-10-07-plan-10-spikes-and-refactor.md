# Plan 10 — Research Spikes and the Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer the six open questions the 2026-10-07 review left under the fixes, so Plan 11 fixes the right things the right way, and restructure the server adapters without changing their behaviour, so Plan 11's fixes land on a pipeline whose order, hand-offs and arithmetic are explicit and tested.

**Architecture:** Two independent tracks run side by side. The **spike track** (S1–S6) asks one question each, by jar read, offline simulation or a live session on fixture `two`, and writes its answer as register rows plus one section of a decision memo. Live spikes boot a copy of 1.0.0 staged at the plan's commit, so they never read the tree the refactor edits. The **refactor track** (R0–R4) first records a golden trace: the full state of six stand-in players over 240 slow minutes, through eats, a death, a respawn and a departure. Every refactor commit then reproduces that trace byte for byte. The refactors are: one helper set; an explicit minute orchestrator with a per-minute context in place of hand-off globals; the remaining adapter arithmetic moved into covered kernels; and the store kernel made pure. The plan closes with the decision memo, which Angus reviews before Plan 11 is written from its draft.

**Tech Stack:** the mod's Lua (Kahlua subset; `lupa` 2.8 Lua 5.1 host), Python 3 (pytest; the offline simulation), the jar toolchain `C:\Users\Angus\pz-b42` (read-only), the harness (`pzt`, fixture `two`, `bench.global`, `globalmoddata.*`, `lua.*`), the claims register and its delta tools.

**Spec:** the review record of 2026-10-07 (the architecture review; ultra slices 1–2; the local xhigh adapter review; the local item-pass review), copied verbatim into this plan's ledger by Task 0; the fixes draft `docs/superpowers/plans/2026-10-07-plan-11-review-fixes-DRAFT.md` (what Plan 11 will do, and which of its tasks wait on which spike); the design spec `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` § 4.1 (the slow clock), § 4.3 (the takeover, and the overlay fallback), § 4.9 (the join checksum), § 6 (performance), § 7 item 37 (the gastric half-time).

## Global Constraints

Everything in Plan 9's Global Constraints holds (`docs/superpowers/plans/2026-10-06-plan-9-packaging-release.md`), and through it Plans 1–8's. Plan 10 adds:

- **A spike changes nothing that ships.** Its probe code lives under `testing/experiments/` (a `TKX_` mod, a driver, a profile) or in an offline script under `testing/spikes/`. The one exception is S2's bench entries, appended to `NR_Server_Bench.lua`, which the bench already owns.
- **A spike answers its stated questions and stops.** Each answer is a register row (M for a live reading, C for a jar or code reading, with its grade honest) and a section of the decision memo. An answer that comes back unmeasured is written as unmeasured and never re-run to make it prettier.
- **A refactor changes no behaviour.** The golden trace (R0) is reproduced byte for byte by every refactor commit, and `python -m pytest testing/tests -q` stays green. A refactor that cannot keep the trace stops and reports; it does not update the trace. A known bug stays in: the respawn dead-mark, the stomach dump on a failed clock read and the stagger starvation are Plan 11's to fix, test-first.
- **Kernel files are pure and one statement per line;** the 100 % line gate holds.
- **Every `mod/` edit shifts `repo:mod/` pointers.** The implementer runs the full `PYTHONIOENCODING=utf-8 python tools/claims_check.py` and lists each `pointer-line` finding, and never edits `docs/reference/claims.tsv`; the controller re-anchors per wave.
- **The `mod/` gates on every mod commit:** `mod_lint` 0 ERROR, `kahlua_lint` 0, `hotpath_lint` 0, `science_check --scan mod` 0, `release_pack check` 0 ERROR.
- **Live:** one session at a time; `python testing/pzt doctor` first; fixture `two`; `Nutrition = false`; never `-safemode`; a driver is never edited after its run; artifacts byte-identical with their register rows.
- **Pytest floor 2544.**
- **Rulings this plan takes** (each a ledger line and a `Ruling:` row at the close):
  1. **Two tracks in parallel.** The spike track (S1–S6) and the refactor track (R0 → R1 → R2 → R3 → R4) run concurrently on disjoint files. Desk spikes S4 and S5 run any time. The live spikes run one session at a time, in the order S2+S3 → S1 → S6, and S6's harness commit lands before its session.
  2. **Live spikes boot a staged 1.0.0 frozen at the plan's commit** (`release/spike-1.0.0/`, staged once by Task 0). The rule that a live boot never overlaps a `mod/` edit protects the tree a boot loads, and these boots load the frozen copy, never `mod/`. So the refactor track may edit `mod/` while a spike session runs. S2's bench entries go into the frozen copy, and into `mod/` only through the refactor track's own commits.
  3. **The golden trace is the refactor's oracle.** It is recorded once from 1.0.0 (R0) and never re-recorded in this plan.
  4. **`NR_Server_Fast.lua` is not refactored in this plan.** S1 decides whether its per-tick body survives, so its arithmetic moves to a kernel in Plan 11 or is removed there.
  5. **The decision memo is the plan's deliverable for Angus:** `docs/superpowers/specs/2026-10-07-plan-11-decisions.md`. Each spike gets a verdict, a recommendation and its consequence for the Plan 11 draft. The takeover fork (S1) is Angus's call. Plan 11 is written after his review.
  6. **Not this plan:** any fix the review found (Plan 11, test-first); the Workshop code reads (blocked on the subscription); stripping register ids from shipped comments, which is a documentation choice rather than a refactor (left for Angus's call in the memo).

## Execution order

Task 0 → { spike track: S4 ∥ S5 (desk, any time); S2+S3 (one live session) → S1 (live) → S6 (harness commit, then live) } ∥ { refactor track: R0 → R1 → R2 → R3 → R4 } → Task D (the decision memo) → Task Z (the close). Model sizing: every spike, R0, R2 and R3 is Opus. R1 and R4 are Sonnet. Reviewers: Opus for S1–S6, R0, R2 and R3; Sonnet for R1 and R4.

## File structure

| path | responsibility | task |
|---|---|---|
| `release/spike-1.0.0/` (gitignored; staged by Task 0) | the frozen 1.0.0 the live spikes boot | 0 |
| `testing/experiments/TKX_GlobalsProbe/`, `testing/profiles/x22-globals.toml`, `testing/experiments/x221_globals.py`, `testing/artifacts/x221-*/` | S1, the zeroed-drains alternative | S1 |
| `release/spike-1.0.0/.../NR_Server_Bench.lua` (the frozen copy only), `testing/profiles/x22-clock.toml`, `testing/experiments/x222_clock_cost.py`, `testing/artifacts/x222-*/` | S2 the real cost, S3 the clock and lifecycle facts | S2+S3 |
| `testing/spikes/satiety_sim.py`, `testing/spikes/out/satiety-*.csv` | S4, hunger feel and the satiety default | S4 |
| (desk only; register rows) | S5, food instance semantics | S5 |
| `testing/pzt/profile.py`, `testing/pzt/client.py`, `testing/pzt/harness.py` (a per-client mod override), `testing/tests/test_pzt_client_override.py`, `testing/profiles/x22-luasum.toml`, `testing/experiments/x223_luasum.py`, `testing/artifacts/x223-*/` | S6, the Lua checksum arm | S6 |
| `testing/tests/kernel/server_host.py`, `testing/tests/kernel/golden_trace.py`, `testing/tests/kernel/test_golden_trace.py`, `testing/tests/kernel/golden/trace-1.0.0.json` | R0, the oracle | R0 |
| `mod/.../shared/NR_Core.lua` (append), the server adapters' local helpers | R1, one helper set | R1 |
| `mod/.../server/NR_Server_Minute.lua` (new), `NR_Server_Players.lua` (`P.work`), every adapter's minute registration, `NR_Server_Nutrients.lua` (the Effects call), `NR_Server_Kinetics.lua` (the hand-offs), `NR_Server_Reconcile.lua` (the splice); `testing/tests/kernel/test_minute_pipeline.py` | R2, the explicit pipeline | R2 |
| `mod/.../shared/NR_Kernel_Intake.lua` (new), `NR_Kernel_Heal.lua` (new), `NR_Server_Intake.lua`, `NR_Server_Metabolism.lua`; `test_kernel_intake.py`, `test_kernel_heal.py` | R3, the adapter math into kernels | R3 |
| `mod/.../shared/NR_Kernel_Store.lua`, its callers; `test_kernel_store.py` | R4, a pure store kernel | R4 |
| `docs/superpowers/specs/2026-10-07-plan-11-decisions.md`, `docs/superpowers/plans/2026-10-07-plan-11-review-fixes-DRAFT.md` (annotated) | the memo | D |

(`mod/...` is `mod/NutritionRevamp/common/media/lua`.)

---

### Task 0: The workspace and the frozen build — controller

- [ ] `scripts/sdd-workspace docs/superpowers/plans/2026-10-07-plan-10-spikes-and-refactor.md`. The ledger's first block copies the four review reports verbatim from the session.
- [ ] `python tools/release_pack.py stage mod/NutritionRevamp --out release/spike-1.0.0` at the plan's commit. Ledger the staged `MANIFEST.json` sha256 and the commit hash; every live spike's artifact names both.

---

### Task S1: The zeroed-drains alternative to the takeover — Opus implementer (desk + live), Opus reviewer

**Questions** (the memo section answers each by number):
1. **Where the rates come from.** Vanilla's per-tick hunger, thirst and fatigue rise read which Java fields, and where are those fields set? Read `zombie.ZomboidGlobals.Load` and the updaters in the `CalculateStats` path the takeover replaced (the Plan 1 jar read lists them: `docs/reference/jar-method-notes.md`, the CalculateStats updaters section).
2. **Whether a mod can set them on a dedicated server, and when.** Candidates: editing the Lua `ZomboidGlobals` table before `Load` copies it; a later re-call of `ZomboidGlobals.Load()` from Lua; any exposed setter. For each route, record whether it is reachable from mod Lua (an exposed global or method) and when it runs relative to `OnGameBoot`, `OnInitGlobalModData` and `OnServerStarted`.
3. **Whether zeroing works.** With the three rise rates at zero, does vanilla's update leave HUNGER, THIRST and FATIGUE flat, awake and asleep, while every other updater still runs? Name each other rate a sleeping or exercising character uses, such as fatigue's recovery while asleep.
4. **Whether a per-minute write holds.** Does a server write of HUNGER, THIRST and FATIGUE once a game minute hold between minutes, and does it reach the owner's client?
5. **What the takeover does that this route cannot.** The takeover reads the stomach into HUNGER every tick, holds a mood floor, an UNHAPPINESS release, a temperature offset and an INTOXICATION decay, and brackets auto-drink. For each, say whether a per-minute write under vanilla's update reproduces it, approximates it with a stated one-minute lag, or loses it.
6. **What Overlay could become** if this route works.

- [ ] **Step 1: The jar read** (`cd /c/Users/Angus/pz-b42`; read `WORKSPACE.md` first; `./pz.sh grep|methods|refs|dump`). Answer Questions 1, 2 and 5 with class, method and line for every claim. Write `task-S1-desk.md` in the workspace. Stop and report if Question 2 has no reachable route: the live arm then has nothing to test, and the memo records "not reachable" with the jar lines.
- [ ] **Step 2: The probe mod** `testing/experiments/TKX_GlobalsProbe/42.20/{mod.info, media/lua/shared/TKX_GlobalsProbe.lua}`.
  - Apply the reachable route at the earliest event the jar read allows. Record in a string-valued global `TKX_G` what was set, when, and the values read back.
  - Each game minute, on the server, write HUNGER = 0.3, THIRST = 0.2 and FATIGUE = 0.1 to every online player, through the same stat setters the takeover uses (read `NR_Server_Fast.lua`'s hoist for the exact calls).
  - Kahlua rules apply. `kahlua_lint testing/experiments` must report 0.
  - The profile `testing/profiles/x22-globals.toml`: fixture `two`, `clients = ["admin", "bob"]`, PZTestKit + TKX_GlobalsProbe only (NOT the mod), `[sandbox] Nutrition = false`, `DayLength = 1`, `[server] SleepAllowed = true`, `SleepNeeded = true`.
- [ ] **Step 3: The driver** `testing/experiments/x221_globals.py` (the `x193`/`x201` session shape; the server-log pattern excludes the probe names). Phases:
  - **A:** `TKX_G` on the server, showing the route taken and the values read back.
  - **B:** a 0.5 s read of `admin`'s three stats on the server for 30 real seconds, spanning at least one write minute. Record the values between writes and the one after a write.
  - **C:** the client's own copy of the three stats on `admin` and `bob`, read in a pair with the server's.
  - **D:** `admin` asleep through the harness's sleep route (read `harness-commands.md`; x151s is the precedent). Read FATIGUE across 60 real seconds.
  - **E:** the same B read under the harness's high time speed, restored afterwards.
  - Commit the probe, profile and driver BEFORE the run. Run once, then commit the artifact, its `artifacts.md` row and its `do-not-cite` rows.
- [ ] **Step 4: The delta** `task-S1-claims-delta.tsv` (C rows for the jar reads, M rows n=1 for the live phases) and the memo section `task-S1-memo.md`. The section answers Questions 1–6 and recommends one of: keep the takeover; switch to zeroed drains plus per-minute writes; or a hybrid. It names which Plan 11 draft tasks change (3, 6, 13). Return the commits, the run id and the recommendation in one line.

---

### Task S2+S3: The real cost, the clock and the lifecycle — Opus implementer (live), Opus reviewer

**S2 questions:**
1. What does the takeover handler cost per player per tick?
2. What does one player's slow-minute work cost?
3. What is the server's tick rate with two clients, under the takeover and under Overlay?
4. What player counts do 1, 2 and 5 % of a 100 ms tick allow?

**S3 questions:**
1. How many `OnTick` calls fall between two `EveryOneMinute` calls at `DayLength = 1`, and at the default day length?
2. Under the harness's high time speed and under an all-asleep fast-forward, how many `EveryOneMinute` calls fire per tick?
3. On a driven respawn, what is the order of `OnNewGame` firing, the new `IsoPlayer` appearing in `getOnlinePlayers`, and the dead one leaving it?
4. Does a client quit and rejoin inside one game minute produce a new `IsoPlayer` under the same username? Measure it only if the harness can quit and re-attach one client; otherwise write it as unmeasured.
5. Does the version dir's `media/sandbox-options.txt` load? Set `[sandbox.NR] Severity = 1.5` and read `NutritionRevamp.server.options.severity`.

- [ ] **Step 1: Instruments in the frozen copy only** (ruling 2). Append to `release/spike-1.0.0/Contents/mods/NutritionRevamp/common/media/lua/server/NR_Server_Bench.lua`:
  - the `NR.server.bench.handler` and `NR.server.bench.minute` entries, written as in the Plan 11 draft's Task 13 Step 1;
  - a tick counter: `NR.server.bench.ticks`, incremented on `OnTick`;
  - a minute counter: `NR.server.bench.minutes`, incremented on `EveryOneMinute`;
  - a ring of the last 64 `(ticks, minutes)` pairs, read through `lua.global`.

  Record the edited file's sha256 in the artifact. `mod/` is not touched. The profile `testing/profiles/x22-clock.toml` boots `release/spike-1.0.0/Contents/mods/NutritionRevamp` by path with `Severity = 1.5`.
- [ ] **Step 2: The driver** `testing/experiments/x222_clock_cost.py`, one session. Phases:
  - **A:** read the options severity (S3.5).
  - **B:** take the counters' ring across 20 game minutes at `DayLength = 1` (S3.1).
  - **C:** set high time speed for 30 s and read the ring, then restore. Put both players to sleep for an all-asleep fast-forward and read the ring again (S3.2).
  - **D:** run `bench.global NutritionRevamp.server.bench.handler 1000` and `bench.global NutritionRevamp.server.bench.minute 200` with the tick rate over the same window (S2.1–2.2). Then switch to Overlay through the sandbox route (`sandbox.set NR.Mode 2` if the table has it; read it) and read the tick rate again (S2.3).
  - **E:** x192's driven respawn on `admin`, reading the online list and a `TKX`-free event log every tick for 5 s around the accept (S3.3). Use the bench file's ring if needed: add an `OnNewGame` stamp to it in Step 1.
  - **F:** S3.4 if the harness supports it.

  For the default-day-length half of S3.1, use a second boot with no `DayLength` override, B only, so this task makes two sessions in sequence. Commit before each run, and commit the artifacts after.
- [ ] **Step 3: The delta and memo section.**
  - S2: each figure with its window, and a player budget table for 1, 2 and 5 % of a tick. Name the rows `#2822`, `#2823` and `#2824` as mismeasured, and propose their narrowing for Plan 11's docs.
  - S3: the tick-per-minute figures, which confirm or correct the draft's ruling 2 and its sizing from the last minute's ticks; the respawn order, which confirms or corrects ruling 4; the reconnect; and the options load, which settles or bounds X22's first half.

---

### Task S4: Hunger feel and the satiety default — Opus implementer (desk + offline), Opus reviewer

**Questions:**
1. What is vanilla's awake and asleep hunger rise per game hour at default settings, and what are the hunger values of its four moodle levels?
2. What hunger does a typical vanilla meal remove?
3. Over a game day of three such meals at `DayLength = 1` (one real hour), how long does a vanilla character spend at each moodle level, against the mod's model at `HALF_TIME_H` 2, 3, 4, 5 and 6?
4. Can any half-time match vanilla's feel? Or does the mod's exponential emptying need a decoupled satiety term, for example hunger reading the energy balance as well as the fill?

- [ ] **Step 1:** Read Questions 1–2 from `docs/facts/character-stats.md`, `docs/facts/eating-pipeline.md` and `docs/facts/food-item-model.md`, citing each number's row. Where a number is not on a page, read it from the jar and cite the method and line.
- [ ] **Step 2:** Write `testing/spikes/satiety_sim.py`, an offline script under lupa. It loads the kernels the way `testing/tests/kernel/conftest.py` does and simulates both models over a game day in one-game-minute steps.
  - **Vanilla:** a linear rise at Question 1's rate, with each meal's HungerChange subtracted at 07:00, 12:00 and 19:00.
  - **The mod:** `K.stomach` fed each meal's bulk through `K.stomach.add`, with the bulk derived as `NR_Server_Intake` derives it (read it), and hunger computed as `K.fast.hungerTarget(fill, 1)`.

  Write one CSV per half-time (`testing/spikes/out/satiety-<T>.csv`: minute, vanilla hunger, mod hunger, each model's moodle level) and a summary table of minutes per level. The script is deterministic and committed with its outputs.
- [ ] **Step 3: The memo section.** Give the table, recommend a default `NR.SatietyHalfTime`, and say whether a decoupled satiety term is needed, with its design in one paragraph if so. Name the Plan 11 draft task it changes (Task 9). Add C rows for the vanilla figures read in Step 1 if any are new.

---

### Task S5: Food instance semantics — Opus implementer (desk), Opus reviewer

**Questions**, each answered from the jar with class, method and line:
1. Does a partial eat lower the item's stored calories, and its stored hunger?
2. How does `Fishing.onCreateFish` set a caught fish's macros, BaseHunger and weight? Read `media/lua/shared/Fishing/fishing_properties.lua` in the install, read-only.
3. How does butchering set a cut's calories and hunger against its script values?
4. What do a split output, such as one of four wieners, and a `ReplaceOnCooked` item hold against their scripts?
5. Which recipe flags carry food values from inputs to outputs, `InheritFood` and its kin?

- [ ] **Step 1:** The reads.
- [ ] **Step 2:** For each item family (plain, partial, fish, butchered, split, replaced, crafted), state the scale that keeps the micronutrients proportional to the macros Eat delivers, as a formula over values readable at eat time.
- [ ] **Step 3:** The delta (C rows) and the memo section. The section replaces the Plan 11 draft's Task 7 Step 1 with its answer and names any family the draft's `K.vector.instanceScale` mishandles.

---

### Task S6: The Lua checksum arm — Opus implementer (harness + live), Opus reviewer

**Questions:**
1. Does a client whose copy of one mod `.lua` file differs by one byte from the server's join, get disconnected, or join with the difference?
2. What do both sides' consoles print?
3. Does a line-ending-only difference behave like the script arm's, where it is forgiven (#1182)?

- [ ] **Step 1: The harness change** (its own commit, under CLAUDE.md § 4.5 and § 5).
  - Add a profile key that gives one fixture client a different source for one mod: `[client_overrides.bob] NutritionRevamp = "path"`.
  - Read `testing/pzt/profile.py` for how keys are validated, `client.py` `seed()` for how a client's mods are installed, and `harness.py` `install()`.
  - The override applies only to the named user's cache. Profiles without the key are unchanged.
  - Tests first, in `testing/tests/test_pzt_client_override.py`: the parsed profile carries the override; `seed()` installs the override path for `bob` and the normal path for `admin`; an override naming an unknown user or an unlisted mod is a `ProfileError`.
  - Gates: `pytest testing/tests -q`; `bus_inventory --check` in sync, since this change adds no Lua command. Commit `Harness: a per-client mod source override (client_overrides)`.
- [ ] **Step 2: The live arm.**
  - **Copies:** copy the frozen 1.0.0 twice into `release/spike-luasum-a/` and `release/spike-luasum-b/`. In copy a, change one byte in a comment of `NR_Core.lua`. In copy b, convert one `.lua` file to CRLF.
  - **Profile** `x22-luasum.toml`: fixture `two`; the server and `admin` boot the frozen copy; `bob` gets copy a in boot 1 and copy b in boot 2, so this is two sessions in sequence.
  - **Driver** `x223_luasum.py`: per boot, record whether `bob` reaches ready, the server's connection and kick lines (the probe names excluded), `bob`'s console tail, and the checksum lines.
  - **Expected failure:** a disconnected client is the reading, so the driver records it and does not fail on it. This follows the raising-probe precedent for an expected failure.
  - **Commits:** the profile and driver before the run; the artifacts after.
- [ ] **Step 3: The delta and memo section:** the answers to Questions 1–3, and what the README's update procedure should say, which Plan 11's Task 12 then adopts.

---

### Task R0: The golden trace — Opus implementer, Opus reviewer

**Files:**
- Create: `testing/tests/kernel/server_host.py`, `golden_trace.py`, `test_golden_trace.py`, `golden/trace-1.0.0.json`

**Interfaces:**
- `server_host.Host`, as specified in the Plan 11 draft's Task 1 Step 2. Write it here, with the `dead` argument and the `deadFlag` field.
- `golden_trace.run(host) -> dict`: the trace.
- `golden_trace.serialize(trace) -> str`: deterministic JSON, sorted keys, floats as `repr` of the Lua number via `%.17g`.

- [ ] **Step 1: Write the scenario** `golden_trace.run`, fully deterministic.
  - **Randomness:** stub `ZombRandFloat` and every other random global to a seeded linear congruential generator in the env. Grep `ZombRand` and `math.random` across `mod/` and stub each one found.
  - **Players:** six, `g1` to `g6`, with distinct starting macros.
  - **Clock:** at `T.age = 100.0`, run 240 slow minutes. Each minute advances the age 1/60 h and runs `h.minute()` then `h.tick(25)`.
  - **Events:**
    - At minutes 10, 70 and 130, each player lands a meal through `IN.land(record, username, vec)`. Read its contract. Use a fixed vector per player built from `NR.data` lookups such as `Base.Apple`, `Base.Bread` and `Base.TinnedBeans`, chosen by reading the data loader.
    - At minute 60, `g2` drinks: land a water vector.
    - At minute 100, `g3` dies (`deadFlag = true`). At minute 101, `OnNewGame` fires for a new `g3` object, which replaces the old one in the online list.
    - At minute 150, `g4` departs. At minute 180, it returns as a new object.
    - At minute 200, the effects bus is asked for one `mirror.request` by `g5`.
  - **Snapshots:** every 30 minutes, record the full serialised record of every player, then `NR.server.*.stats` for every adapter that has one, then the count of `sendServerCommand` calls by command name.
  - **Output:** return `{ "snapshots": [...], "printed_count": n }`.
- [ ] **Step 2:** Record `golden/trace-1.0.0.json` from the current tree. Then write `test_golden_trace.py`, which asserts `serialize(run(Host())) == open(golden).read()`. Run it twice to show it is deterministic.
- [ ] **Step 3: Sensitivity check.** On a scratch edit, change one constant in a kernel the minute pipeline uses, for example `K.stomach.FULL_BULK` from 8.0 to 8.1. Confirm the test FAILS, then revert the edit. Quote both runs in the report: an oracle that cannot fail is no oracle.
- [ ] **Step 4:** Commit `Tests: the golden trace of 1.0.0, the refactor's oracle (six players, 240 slow minutes, eats, a drink, a death and respawn, a departure and return, a mirror request)`. The test, the host, the scenario and the JSON go in one commit.

---

### Task R1: One helper set, semantics kept — Sonnet implementer, Sonnet reviewer

**Files:** `mod/.../shared/NR_Core.lua` (append), and every adapter with a local copy. The sites are listed in the Plan 11 draft's Task 1 Files block.

- [ ] **Step 1:** Append `NR.worldAge`, `NR.finite`, `NR.num`, `NR.obj` and `NR.flag` to `NR_Core.lua`, exactly as in the Plan 11 draft's Task 1 Step 5. Write the helper tests `test_core_helpers.py` from that same draft step, and run them; the first run FAILS.
- [ ] **Step 2: Replace each local copy with a shim that keeps that file's failure meaning.**
  - Kinetics, Intake, Fast and Players: `local function worldAge() return NR.worldAge() or 0 end`, keeping the 0 behaviour, which is Plan 11's to fix.
  - Metabolism, Nutrients and Strength: `local worldAge = NR.worldAge`.
  - `finite`, `num`, `obj` and `flag` become aliases, except where a local's signature or default differs. Read each one. A differing local keeps its own body and gets a comment naming the difference.
  - `IN.isFinite = NR.finite`.
- [ ] **Step 3:** Run the golden trace (unchanged), `pytest testing/tests -q`, the gates and the full `claims_check`, listing the shifts.
- [ ] **Step 4:** Commit `Refactor: one helper set in NR_Core, each adapter's failure meaning kept (golden trace unchanged)`.

---

### Task R2: The explicit minute pipeline — Opus implementer, Opus reviewer

**Files:**
- Create: `mod/.../server/NR_Server_Minute.lua`, `testing/tests/kernel/test_minute_pipeline.py`
- Modify: `NR_Server_Players.lua` (`P.work` calls the pipeline instead of `fire(P.onMinute, …)`); every adapter's `P.onMinute[#P.onMinute + 1] = …` registration (Bus :113, Fast :563, Kinetics :119, Metabolism :486, Nutrients :531, Strength :279, Weight :211, Options :107); `NR_Server_Reconcile.lua` (`RC.insertBefore` at :184 goes); `NR_Server_Nutrients.lua:499-505` (the hand call of `EFF.minute`); `NR_Server_Kinetics.lua` (`KIN.lastAbsorbed` and `KIN.lastMealCa` become context fields); `NR_Server_Metabolism.lua` and `NR_Server_Nutrients.lua`, the readers of those hand-offs.

**Interfaces:**
- `NR.server.minute.ORDER`, the declared step names in run order.
- `NR.server.minute.register(name, fn)`, where `fn(username, player, record, ctx)`.
- `NR.server.minute.run(username, player, record)`.
- `ctx`: one table reused per call and cleared at the start of each player's run. Fields: `absorbed` and `mealCa` (Kinetics); `body`, `dtM` and `ageH` (Nutrients, for Effects).

- [ ] **Step 1: Write the failing test** `test_minute_pipeline.py`:

```python
from server_host import Host

def test_the_declared_order_is_the_order_that_runs():
    h = Host()
    M = h.NR.server.minute
    order = [M.ORDER[i] for i in range(1, len(M.ORDER) + 1)]
    assert order == ["bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight"]
    ran = h.rt.eval("{}")
    for name in order:
        M.register(name, h.rt.eval("function(t, n) return function() t[#t + 1] = n end end")(ran, name))
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    assert [ran[i] for i in range(1, len(ran) + 1)][-len(order):] == order

def test_no_adapter_appends_to_the_old_list():
    h = Host()
    assert len(h.NR.server.players.onMinute) == 0

def test_a_step_that_raises_does_not_stop_the_steps_after_it():
    h = Host()
    M = h.NR.server.minute
    M.register("kinetics", h.rt.eval("function() error('boom') end"))
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    assert h.record("a").body is not None                 # metabolism still ran after the raising step
```

(The second test's register-twice semantics: `register` REPLACES the step's function. State that in the module.) Run it; it FAILS.

- [ ] **Step 2: Write `NR_Server_Minute.lua`:**

```lua
-- NR_Server_Minute.lua -- the slow minute's pipeline (Plan 10 Task R2): one declared order, one context table,
-- each step guarded so a raise is logged and the steps after it still run. Adapters register by name at load;
-- NR_Server_Players' P.work calls run. The order is the order 1.0.0 ran in (the Reconcile splice and the Nutrients
-- hand call of Effects made explicit); the golden trace holds it byte for byte.
local NR = NutritionRevamp
NR.server.minute = {
    ORDER = { "bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight" },
    steps = {},
    ctx = {},
    stats = { runs = 0, failures = 0 },
}
local MIN = NR.server.minute

-- A step's function: fn(username, player, record, ctx). Registering a name again replaces its function.
function MIN.register(name, fn)
    MIN.steps[name] = fn
end

function MIN.run(username, player, record)
    local ctx = MIN.ctx
    for k in pairs(ctx) do ctx[k] = nil end
    MIN.stats.runs = MIN.stats.runs + 1
    for i = 1, #MIN.ORDER do
        local fn = MIN.steps[MIN.ORDER[i]]
        if fn ~= nil then
            local ok, err = pcall(fn, username, player, record, ctx)
            if not ok then
                MIN.stats.failures = MIN.stats.failures + 1
                NR.log.say(2, "minute: " .. MIN.ORDER[i] .. " failed for " .. tostring(username) .. ": " .. tostring(err))
            end
        end
    end
end
```

- [ ] **Step 3: Move every registration to `MIN.register`** at the same event each used (`OnServerStarted`), so `P.onMinute` stays empty. The Reconcile splice goes: its step is named in `ORDER`.
  - **Effects:** the Effects step reads `ctx.body`, `ctx.dtM` and `ctx.ageH`, which Nutrients stamps where it called `effects.minute` by hand. Nutrients stops calling it.
  - **Kinetics:** writes `ctx.absorbed` and `ctx.mealCa` instead of `KIN.lastAbsorbed[username]` and `KIN.lastMealCa[username]`. Metabolism and Nutrients read the context, and the per-username tables go.
  - **Each adapter's own `pcall`:** an adapter that already wraps its body in its own `pcall` keeps it, so its own failure counters and logs are unchanged and the trace holds. `MIN.run`'s guard is the outer net.
  - **The options poll:** `pollFromPlayers` is dead because it never registers (the Plan 11 draft's Task 2 Step 9). Leave it untouched here, since it is a fix, and say so.
- [ ] **Step 4:** `P.work` ends with `NR.server.minute.run(username, player, r)` in place of `fire(P.onMinute, username, player, r)`, and the empty `P.onMinute = {}` stays for any third party.
- [ ] **Step 5:** Run the pipeline test (PASS), then the golden trace, which must be UNCHANGED. If the trace moves, find the order or hand-off difference and fix the refactor, never the trace. Then run `pytest testing/tests -q`, update `test_server_reconcile_shape.py`'s order test to read `MIN.ORDER` rather than the old list (the same order), and run the gates and the full `claims_check`, listing the shifts.
- [ ] **Step 6:** Commit `Refactor: the slow minute's explicit pipeline (declared order, one context, the Reconcile splice and the Effects hand call made explicit; golden trace unchanged)`.

---

### Task R3: The adapter math into kernels — Opus implementer, Opus reviewer

**Files:**
- Create: `mod/.../shared/NR_Kernel_Intake.lua`, `NR_Kernel_Heal.lua`, `testing/tests/kernel/test_kernel_intake.py`, `test_kernel_heal.py`
- Modify: `NR_Server_Intake.lua` (`IN.fractionOf` :115, `IN.macrosEaten` :328, `IN.assemble` :353, and the pure parts of the share arithmetic around :95-128), `NR_Server_Metabolism.lua` (`heal` :284-365)

- [ ] **Step 1: Classify.** For each named function, list each line as pure (numbers and tables in and out) or engine (a Java read, a log, a global). The pure part moves. The engine reads stay in the adapter and are passed in as arguments.
  - `IN.assemble` takes a lookup and templates. If they are pure tables (`NR.data`), they pass in. If they call the engine, the adapter resolves them first.
  - `heal` repairs non-finite record fields to neutral values, marks names and logs. The pure part is `K.heal.body(body, ageH) -> badNames | nil`, and the log stays in the adapter.
- [ ] **Step 2: Write the failing kernel tests first.**
  - Port every existing behaviour assertion about these functions from `test_intake_shape.py` and `test_metabolism_shape.py` into the kernel tests, calling the kernel functions directly: `K.intake.fractionOf`, `K.intake.macrosEaten`, `K.intake.assemble` and `K.heal.body`.
  - Add a property test for each function over generated inputs, using a seeded loop of 500 cases and no new dependency. For `fractionOf` the result lies in [0, 1]. For `macrosEaten` the result is non-negative and monotone in `share`. For `heal.body`, a body with every field NaN comes back all finite, with every field named.
  - Run them; they FAIL because the module is missing.
- [ ] **Step 3: Move the code.** The kernels are written one statement per line, and the adapters keep thin wrappers under the same names (`IN.fractionOf = K.intake.fractionOf` where the signature is unchanged), so every caller and shape test still works.
- [ ] **Step 4:** Run the kernel tests (PASS), the 100 % coverage gate, the golden trace (UNCHANGED), `pytest testing/tests -q`, the gates and the full `claims_check`, listing the shifts.
- [ ] **Step 5:** Commit `Refactor: the intake share, macro and assembly arithmetic and the body heal into covered kernels (golden trace unchanged)`.

---

### Task R4: A pure store kernel — Sonnet implementer, Sonnet reviewer

**Files:** `mod/.../shared/NR_Kernel_Store.lua:291-296` and the store kernel functions that read `NutritionRevamp.data.records`; their callers (`NR_Server_Store.lua`, and any other: `grep -rn 'store\.\(load\|recompute\|new\)' mod/`); `testing/tests/kernel/test_kernel_store.py`.

- [ ] **Step 1: Write the failing test.** Call the kernel functions with an explicit `records` argument that differs from the global, and assert the argument's records are the ones used. It FAILS on the current global read.
- [ ] **Step 2: Implement.** Each kernel function that read the global takes `records` as its last parameter. A nil argument does NOT fall back to the global, because a kernel never reads global data; every caller passes `NR.data.records`.
- [ ] **Step 3:** Run the kernel tests, coverage, the golden trace (UNCHANGED), the gates and the full `claims_check`.
- [ ] **Step 4:** Commit `Refactor: the store kernel takes its records as an argument (golden trace unchanged)`.

---

### Controller: the register per wave

- [ ] After each spike's run and after R1–R4: apply the deltas (the fill step for any status row), the suffixed-tag rewrite over the touched pages, `--fix-tags` and `cited-by --write`. Then apply every reported pointer shift. One register commit per wave, with the full `claims_check` at 0 before it.

---

### Task D: The decision memo — controller writes, Opus reviews

- [ ] **Step 1:** Write `docs/superpowers/specs/2026-10-07-plan-11-decisions.md`, one section per spike (S1–S6), each with:
  - the question;
  - the answer, with its register rows;
  - the recommendation;
  - the Plan 11 draft tasks it changes, and how.

  Then three sections:
  - **The takeover fork:** S1's options, with S2's cost beside each, marked for Angus's decision.
  - **What the refactor changed for Plan 11:** the draft's code samples that assumed `P.onMinute`, `KIN.lastAbsorbed` or the local helpers, re-based on R1–R4's interfaces.
  - **Angus's other calls:** the comment ids; the satiety default; the prune default.
- [ ] **Step 2:** Annotate the Plan 11 draft's header with a pointer to the memo and a list of the tasks each decision rewrites. Its body is NOT rewritten in this plan.
- [ ] **Step 3:** An Opus reviewer checks the memo against the register rows and artifacts: every answer must be at its rows, and no recommendation may go beyond what the spike read. Fix and re-review.

---

### Task Z: The close — controller

- [ ] Run the whole-pass review (Opus, read-only) and a line-level Opus bug review of the plan's `mod/` diff, which must show no behaviour change, so the bug review's target is any change the golden trace does not cover. Then one consolidated fix wave and its re-review, and every § 3 gate.
- [ ] Update CLAUDE.md: § 3's count, plus a § 6 rule: "a refactor of the server adapters is proven by the golden trace (`testing/tests/kernel/test_golden_trace.py`) reproduced byte for byte; the trace is re-recorded only by a plan that names the behaviour change it records".
- [ ] Update the memory block in both scopes, run `git push origin main`, and write the Rulings block in the ledger, then `Plan 10: complete`.
- [ ] The close report points Angus at the decision memo. Plan 11 is written from the draft and the memo only after his review.

## Self-Review

- **Spikes cover the review's open questions:**
  - S1: the takeover alternative and what Overlay could be.
  - S2: the mismeasured cost.
  - S3: the clock facts behind the stagger fix, the respawn and reconnect order, and the options load.
  - S4: hunger feel.
  - S5: the fish and partial-eat semantics behind the micronutrient fix.
  - S6: the Lua checksum arm behind the update procedure.
- **Refactors cover the review's structure findings:**
  - R1: the eight helper copies.
  - R2: the implicit order, the splice, the hand call and the hand-off globals.
  - R3: the intake and heal arithmetic outside the gate.
  - R4: the kernel reading global state.
  - Not refactored here: Fast's in-adapter math (ruling 4, it waits on S1). Stripping the comment ids is not a refactor (ruling 6, Angus's call).
- **Placeholders:**
  - The spikes are research, so their steps name the questions, the sources, the instruments and the exact outputs. Their answers are the deliverable.
  - The refactors carry code for the new module and the tests. The moved code is the existing code, named by file and line, so it is not reproduced here.
  - R0's meal vectors are chosen by reading the data loader. The scenario's events, counts and timings are fixed.
- **Interface consistency:**
  - `server_host.Host`, from R0, is used by R2 and later by Plan 11.
  - `NR.worldAge`, `finite`, `num`, `obj` and `flag`, from R1, are used by R2 and R3 and by Plan 11.
  - `NR.server.minute.ORDER`, `register` and `run`, and the context fields `absorbed`, `mealCa`, `body`, `dtM` and `ageH`, all from R2.
  - `K.intake.fractionOf`, `macrosEaten` and `assemble`, and `K.heal.body`, from R3.
  - The store kernel's `records` parameter, from R4.
  - The bench entries `NR.server.bench.handler`, `minute`, `ticks` and `minutes`, from S2, live in the frozen copy only.
