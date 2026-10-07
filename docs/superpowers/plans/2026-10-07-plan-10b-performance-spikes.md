# Plan 10b — Performance Spikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find out where the mod's server time actually goes and which performance refactors are worth making, before Plan 11 is written. Four questions:
- What does each step of one player's slow minute cost, in real play, and how much of it is Java calls?
- Can the minute run every 5 or 10 game minutes instead of every one, with negligible drift?
- Can the mod do no per-tick work at all? Measure the panic and temperature sawtooth when they are written once a minute, and the burst cost of the slow minute driven from `EveryOneMinute` instead of an `OnTick` drain.
- If Java reads dominate, does caching them pay?

**Architecture:** Measurement only, with no change to `mod/`.
- **The live spikes** boot a copy of the current tree staged at the plan's commit, as Plan 10 ruling 2 did. Their instruments live in that copy only: per-step timers wrapped around `NR.server.minute`'s registered steps, a Java-call counter wrapped around `NR.call`, a per-minute panic and temperature writer, and an `EveryOneMinute`-driven variant of the player drain.
- **The offline spike** reuses the golden-trace machinery (`testing/tests/kernel/golden_trace.py`, `server_host.Host`). It runs the same scenario with the minute fired every k game minutes and measures the drift against k = 1.
- **The outputs:** register rows, a "Performance" section in the decision memo (`docs/superpowers/specs/2026-10-07-plan-11-decisions.md`), and an updated cost column for Decision 1.

**Tech Stack:** the mod's Lua (Kahlua; read-only here); Python 3 with pytest and lupa 2.8 for the offline drift study; the harness (`pzt`, fixture `two`, `bench.global`, `lua.global`, `lua.call`, `settimespeed`, the eat and sleep routes); the claims register and its delta tools.

**Spec:** the decision memo (`docs/superpowers/specs/2026-10-07-plan-11-decisions.md`), Decision 1 and Appendix C.
- S2's cost readings: the takeover handler costs 19.33 µs per player per tick (#3353). One player's slow minute costs about 377 µs, measured at zero elapsed time, so it is a lower bound (#3354). The fast kernel step costs 4.36 µs (#3356).
- S1b's reading: vanilla's updaters cost about 1–11 µs per player per update (#3386).
- The clock facts: a game minute is 6.27 ticks at DayLength 1 and 37.46 at DayLength 4 (#3346, #3347). A fast clock fires at most one minute event per tick (#3348).

## Global Constraints

Plan 10's Global Constraints hold (`docs/superpowers/plans/2026-10-07-plan-10-spikes-and-refactor.md`). Plan 10b adds:

- **No edit under `mod/`.** Every instrument lives in the staged copy `release/perf-<HEAD>/` (gitignored) and is recorded in the artifact by sha256. The offline drift study patches the clock in the test host, never the mod.
- **Timings aggregate.** Mod Lua has no clock finer than `getTimestampMs` (1 ms). This 42.20.4 jar exposes no nanosecond clock to Lua. So every per-step or per-call cost is a total over many calls divided by their count, and each reading states its count and its ms total.
- **A reading is cost, not behaviour.** A bench that calls a step outside its minute advances state; the artifact says so, and no behaviour row rests on it.
- **Live:** one session at a time. Run `python testing/pzt doctor` first. Use fixture `two` with `Nutrition = false`. A driver is never edited after its run. An unmeasured reading is written as such.
- **A spike answers its questions and stops.** Each answer is register rows plus a memo section, as in Plan 10.
- **Pytest floor 2634.**
- **Rulings this plan takes:**
  1. **Order.** Task 0 first. Then P2 (offline) runs alongside P1+P3 (one live session). P4 runs only if P1's trigger fires, and gets its own session. Then Task M (the memo update), then Task Z (the close).
  2. **The staged copy** is the current tree at the plan's commit. The refactored code is behaviour-identical to 1.0.0 (Plan 10's golden trace), so its costs are the costs Plan 11 starts from.
  3. **P4's trigger.** P4 runs only when Java calls (counted through `NR.call`, `NR.num`, `NR.obj`, `NR.flag` and the adapters' direct method calls) account for at least half of one or more step's measured time, by the estimate in P1 Step 4. Otherwise P4 is written "not triggered", with P1's numbers.
  4. **The coarse minute's acceptance band.** A k is "safe" when, over the golden scenario, no discrete state differs from k = 1: grades, bands, traits written, deaths, `allReplete`, the effects key. The continuous state must also differ by at most 1 % of the field's range over the run, or 1e-3 absolute for fields under 0.1. Anything else is a finding and is reported, never tuned away.
  5. **Not this plan:** making any change to the mod, which is Plan 11's job, nor recommending one beyond what a reading supports.
  6. **The design target is no per-tick work** (Angus, 2026-10-07; the lessons rule against simulation on `OnTick`, #1071, #1080). The takeover hook is per-tick by nature, so this plan measures no takeover variant. P3 instead measures what the mod gives up and what it pays when nothing runs per tick.

## Execution order

Task 0 → { P2 (Opus, offline) ∥ P1+P3 (Opus, one live session) } → P4 (Opus, live; only if triggered) → Task M (controller writes; Opus review) → Task Z (close). Reviews: Opus for each spike.

## File structure

| path | responsibility | task |
|---|---|---|
| `release/perf-<HEAD>/` (gitignored) | the staged copy with the instruments | 0, P1, P3, P4 |
| `testing/experiments/x231_perf.py`, `testing/profiles/x23-perf.toml`, `testing/artifacts/x231-*/` | P1 and P3's session | P1+P3 |
| `testing/spikes/coarse_minute.py`, `testing/spikes/out/coarse-*.json`, `coarse-summary.md` | P2's drift study | P2 |
| `testing/experiments/x232_cache.py`, `testing/profiles/x23-cache.toml`, `testing/artifacts/x232-*/` | P4's session, if triggered | P4 |
| `docs/superpowers/specs/2026-10-07-plan-11-decisions.md` (a new "Performance" section; Decision 1's cost lines) | the memo | M |
| the pages the rows own (`docs/areas/testing-your-mod.md#walls`, `docs/areas/body-effects.md#takeover`, `docs/platform/lua-platform.md` if the per-call figures belong there) | the rows' sentences | P1–P4 |

---

### Task 0: Workspace and staging — controller

- [ ] `scripts/sdd-workspace docs/superpowers/plans/2026-10-07-plan-10b-performance-spikes.md`. The ledger's first line names the plan, and its first block copies Decision 1's cost lines and Appendix C's S2 section.
- [ ] `python tools/release_pack.py stage mod/NutritionRevamp --out release/perf-<HEAD>`. Ledger the manifest sha256 and HEAD.

---

### Task P1+P3: The slow minute by step, and the cost of no per-tick work — Opus implementer (live), Opus reviewer

**Files:**
- Modify, in the staged copy only: `release/perf-<HEAD>/NutritionRevamp/Contents/mods/NutritionRevamp/common/media/lua/server/NR_Server_Bench.lua` (append).
- Create: `testing/profiles/x23-perf.toml`, `testing/experiments/x231_perf.py`; after the run, `testing/artifacts/x231-<stamp>/perf.json`.

**Interfaces (all in the staged copy's bench file):**
- `NR.server.bench.prof = { on = false, ms = {}, runs = {}, calls = {} }`, keyed by step name.
- `NR.server.bench.profStart()` and `NR.server.bench.profStop()`.
- `B.minuteHold`, `B.burst` and `B.burstRR(m)`, with their switches `B.holdOn` and `B.burstOn` and targets `B.panicTarget` and `B.tempTarget`.
- The existing `NR.server.bench.handler()` and `NR.server.bench.minute()`, re-added as in Plan 10 S2.

- [ ] **Step 1: The per-step timers.** Append to the staged copy's bench file. The wrap runs at `OnServerStarted`, after every adapter has registered:

```lua
-- Plan 10b P1: per-step timing of the slow minute. Wraps each registered step once, at OnServerStarted after the
-- adapters register. A step's time is accumulated in ms over every run while prof.on is true; the per-run cost is
-- ms / runs. getTimestampMs is 1 ms resolution, so the readings are totals over many runs.
NR.server.bench = NR.server.bench or {}
local B = NR.server.bench
B.prof = { on = false, ms = {}, runs = {}, calls = {}, wrapped = false }
local function now() return getTimestampMs and getTimestampMs() or 0 end
local calls = 0
local realCall = NR.call
function NR.call(o, name, ...) calls = calls + 1 return realCall(o, name, ...) end
function B.profStart() B.prof.on = true end
function B.profStop() B.prof.on = false end
local function wrap()
    if B.prof.wrapped then return end
    local MIN = NR.server.minute
    for i = 1, #MIN.ORDER do
        local name = MIN.ORDER[i]
        local fn = MIN.steps[name]
        if fn ~= nil then
            B.prof.ms[name], B.prof.runs[name], B.prof.calls[name] = 0, 0, 0
            MIN.steps[name] = function(u, p, r, ctx)
                if not B.prof.on then return fn(u, p, r, ctx) end
                local c0, t0 = calls, now()
                local a, b = fn(u, p, r, ctx)
                B.prof.ms[name] = B.prof.ms[name] + (now() - t0)
                B.prof.calls[name] = B.prof.calls[name] + (calls - c0)
                B.prof.runs[name] = B.prof.runs[name] + 1
                return a, b
            end
        end
    end
    B.prof.wrapped = true
end
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function() if NR.isServer() then wrap() end end)
end
```

Read whether the adapters reach Java through `NR.call`, `NR.num`, `NR.obj` and `NR.flag` (which route through `NR.call`) or through direct colon calls. Count the direct calls per step by reading each adapter's minute function; they cannot be counted at run time. State the share each route carries in the report.

- [ ] **Step 2: The no-per-tick entries** (rule 6). Append these to the same staged copy:
  - `B.minuteHold()`: an `EveryOneMinute` handler, server-gated, active only while `B.holdOn` is true. Once per game minute, for every online player, it writes `CharacterStat.PANIC` to `B.panicTarget` and `CharacterStat.TEMPERATURE` to `B.tempTarget` through the stats setters `NR_Server_Fast.lua` uses (read its handles). A ring records each write's pre-write value, the per-tick decay between writes for the first player, and the time of each write.
  - `B.burst()`: an `EveryOneMinute` handler, active only while `B.burstOn` is true. It runs `NR.server.minute.run` for every online player in one event, the shape of a drain with no `OnTick`, and accumulates the event's total ms and player count. Bracket it with `getTimestampMs`; with two players and 1 ms resolution, report the total over many events, ms ÷ events.
  - A round-robin variant `B.burstRR(m)`: one event processes ⌈N ÷ m⌉ players in a persistent rotation, so each player runs every m game minutes. Its elapsed-time integration is the kernels' own.
  - Leave the live `OnTick` drain in place while these run. They measure cost and decay shape only, and their state changes are noted in the artifact as cost-not-behaviour.
- [ ] **Step 3: The profile and the driver.** `x23-perf.toml` uses the `x22-clock.toml` shape: fixture `two`, two clients, `DayLength = 1`, the staged copy by path, and `Nutrition = false`. The driver `x231_perf.py` runs these phases:
  - **A. In-play profile.** Call `profStart`, then play 120 game minutes at speed 1. Within that window:
    - each player eats two meals through the eat route at game minutes 20 and 70;
    - `admin` sleeps through game minutes 80–110 (the sleep route);
    - both players walk for minutes 30–40.

    Then call `profStop` and read `B.prof` (flatten it to scalars if `lua.global` cannot return tables). This gives real minutes, with elapsed time, meals, sleep and movement.
  - **B. The same profile under `settimespeed 30` for 60 wall seconds.** Each run's elapsed time is then about 4.7 game minutes, the fast-clock shape.
  - **C. The once-a-minute hold.** In Overlay mode (`sandbox.var NR.Mode 2`, so the takeover is not registered and vanilla's updaters run), set `B.panicTarget` to 0.5 and `B.tempTarget` to 37.5, turn `B.holdOn` on, and give `admin` a panic source if the harness has one (read the table); otherwise write the floor only. Read the ring across 20 game minutes at DayLength 1, then at DayLength 4. The reading is panic's and temperature's decay per tick between writes and the sawtooth amplitude at each day length.
  - **C2. The burst.** With the minute work's own drain left on, turn `B.burstOn` on for 60 game minutes at DayLength 1 and read ms ÷ events ÷ players. Repeat with `B.burstRR(5)`. Then measure the tick-time spike a burst causes: the event's total ms against the 100 ms tick, at the measured per-player cost, extrapolated to 20 and 40 players and labelled as extrapolation.
  - **D. The per-call baseline.** Run 1000 calls of `bench.minute` at an unchanged world age (S2's measure), for continuity with #3354.

  Commit the profile and the driver BEFORE the run. Every reading sits at a path, and the server-log pattern excludes the probe names.
- [ ] **Step 4: The analysis.** In the memo section, compute these from A and B:
  - each step's mean ms per run, and its share of the minute;
  - Java calls per run per step;
  - an estimate of the Java share. Use S2's 4.36 µs pure step against the handler's 19.33 µs as the per-call calibration, giving roughly (19.33 − 4.36) ÷ (the handler's counted Java calls) µs per Java call. Say plainly that this is an estimate.

  From C, give panic's and temperature's sawtooth under a once-a-minute write (amplitude and shape, per day length). Say whether a player would notice: read the moodle thresholds for panic from `docs/facts/character-stats.md`, and judge whether the swing crosses one. Also say whether the takeover's temperature target ever held (Decision 1 marks it unmeasured, X81).

  From C2, give the burst's cost per player per event, the spike at 20 and 40 players, and the round-robin's spike. Give the all-in per-player per-game-minute cost of a design with no per-tick work: S1's writer (#3373), plus vanilla's updaters (#3386), plus the minute work, divided by the round-robin period if one is used.

  State P4's trigger result.
- [ ] **Step 5: Commit the artifact,** byte-identical, with its `artifacts.md` row, which re-anchors in the same commit every `artifacts.md` pointer the row shifts (CLAUDE.md § 6), and its `do-not-cite` rows. Write the delta `task-P1P3-claims-delta.tsv` (M rows, n=1, provisional ids `T108.n`), the memo section `task-P1P3-memo.md` and the report.

---

### Task P2: Running the minute less often — Opus implementer (offline), Opus reviewer

**Files:**
- Create: `testing/spikes/coarse_minute.py`, `testing/spikes/out/coarse-k{1,2,5,10,15,30}.json`, `testing/spikes/out/coarse-summary.md`.

**Interfaces:**
- Consumes: `golden_trace.run`'s scenario and serialisation (`testing/tests/kernel/golden_trace.py`), and `server_host.Host`.
- Produces: `coarse_minute.run_k(k) -> dict` (the same snapshot shape as `golden_trace.run`), and `coarse_minute.compare(base, other) -> dict` (per-field drift and every discrete difference).

- [ ] **Step 1: Read** `golden_trace.py` whole: the scenario's per-minute loop at `run` (:569 and after), its event schedule (meals, the drink, the NaN injection, the death, the departure) and its snapshot times.
- [ ] **Step 2: Write `run_k(k)`.** Re-run the same scenario, but fire the slow minute (`h.minute()` then `h.tick(TICKS)`) only every k game minutes:
  - the world age still advances one game minute per loop step;
  - events still land at their own minute;
  - snapshots are taken at the same minutes.

  It is the same scenario as the golden trace, with the minute decimated. Import the golden module's helpers rather than copying them. Where a helper fixes the cadence, parameterise it in `coarse_minute.py` without editing `golden_trace.py`.
- [ ] **Step 3: Write `compare(base, other)`** over the serialised snapshots:
  - For every numeric leaf: the absolute difference, and the difference relative to the leaf's range over the k = 1 run.
  - For every discrete leaf (grade, band, trait set, dead, `allReplete`, `effects.key` and any integer counter): equality.
  - Report the worst 20 leaves by relative drift, and every discrete mismatch.
- [ ] **Step 4: Run k = 1, 2, 5, 10, 15 and 30.**
  - k = 1 must reproduce the golden trace byte for byte. That is the harness's own sanity check; if it fails, fix the harness and say so.
  - Write each run's JSON and a summary table: for each k, the max relative drift, the discrete mismatches, and the fields that fail ruling 4's band.
  - The script is deterministic: run it twice and compare.
- [ ] **Step 5: The memo section.**
  - The largest safe k under ruling 4, and why the first unsafe k fails, naming the fields.
  - The cost saving: the minute's cost ÷ k, using P1's per-minute figure, or S2's 377 µs if P1 is not in.
  - What a coarse minute does to the player: hunger read from the stomach fill (stamped per minute) moves in steps of k minutes; the bus push gap; the moodles' lag. Name the decision-memo coupling with Decision 2.
  - Commit the script and outputs: `Spike P2: the slow minute run every k game minutes against every one`.
  - Rows: C/arith rows on the drift (provisional `T109.n`) owned by `docs/areas/testing-your-mod.md#walls`, with their pointers into `testing/spikes/out/coarse-summary.md`.

---

### Task P4: Caching the dominant step's Java reads — Opus implementer (live), Opus reviewer — ONLY IF TRIGGERED (ruling 3)

**Files:**
- Modify, in a second staged copy `release/perf-cache-<HEAD>/` only: the dominant step's adapter.
- Create: `testing/profiles/x23-cache.toml`, `testing/experiments/x232_cache.py`; after the run, `testing/artifacts/x232-<stamp>/cache.json`.

- [ ] **Step 1:** From P1's table, pick the step with the largest Java share. List its Java reads, each with the rate at which its value changes, taken from the jar (a trait list, a perk level, a body-part table, a thermoregulator).
- [ ] **Step 2: In the second copy only,** cache the reads that change no more often than per minute.
  - The cache holds a per-player table of handles and values, refreshed every 10th minute and at first sight.
  - The rule the cached value follows is written in the copy's comment.
  - Behaviour must not change for the measured scenario. Run the golden trace against the copy's Lua files under lupa: point `server_host`'s `SERVER` at the copy; never edit the repo's files. Report whether it still reproduces. A drift is a finding, and the cached read is the cause.
- [ ] **Step 3: One live session.** Run P1's phase A profile on the cached copy, interleaved with the uncached copy through two profiles (`x23-cache.toml`, `x23-perf.toml`) run back to back in the same harness session where possible, else in two sessions. Read the step's ms per run, cached against uncached.
- [ ] **Step 4:** The artifact, rows `T110.n`, the memo section, and the report.

---

### Task M: The decision memo's performance section — controller writes, Opus reviews

- [ ] Add a "Performance" section to `docs/superpowers/specs/2026-10-07-plan-11-decisions.md`, after "The refactor":
  - P1's per-step table and the Java share;
  - P2's safe k and its player-visible cost;
  - P3's fork costs;
  - P4's result, or "not triggered".
  - Then a ranked list of performance refactors for Plan 11. Each item names the reading that supports it and its expected saving per player per game minute.
- [ ] Rewrite Decision 1 for the no-per-tick target (rule 6). The takeover option leaves the table. The hybrid's per-tick hold becomes a once-a-minute panic and temperature write. Give the measured sawtooth and the design's all-in cost from P3, and the drain's move from `OnTick` to an `EveryOneMinute` round-robin from C2 and P2.
- [ ] Update the "Re-basing the draft" list for Task 13, since the measurements are now done.
- [ ] An Opus reviewer checks every number against its row, and that no recommendation goes beyond its reading. Run the fix round and its re-review.

---

### Task Z: The close — controller

- [ ] **Reviews:** the whole-pass review (Opus, read-only) against this plan; no line-level bug review, since this plan does not touch `mod/`. Then one consolidated fix wave and its re-review.
- [ ] **Gates:** every § 3 gate, and CLAUDE.md § 3's count.
- [ ] **Records:** update the memory in both scopes, then `git push origin main`, then write the Rulings block and the § 7 list in the ledger, then `Plan 10b: complete`.

## Self-Review

- **Coverage:** every spike Angus asked for has a task.
  - Profile the minute by step: P1.
  - Run it less often: P2.
  - No per-tick work (rule 6): P3 measures the once-a-minute panic and temperature sawtooth and the `EveryOneMinute` burst and round-robin, folded into P1's session to save a boot.
  - Java-read caching: P4, gated on P1 by ruling 3.
- **Placeholders:**
  - `<HEAD>` and `<stamp>` are filled at dispatch and at run time.
  - P3's trimmed handler is built by copying and editing the staged body. The edit is named exactly (the six reads dropped, the seven moved), so the copy is concrete.
  - P4's cached reads depend on P1's ranking. That is the point of its trigger, and the selection rule is stated.
- **Interfaces:** `B.prof`, `profStart`, `profStop`, `minuteHold`, `burst` and `burstRR` (P1+P3). `run_k` and `compare` (P2).
