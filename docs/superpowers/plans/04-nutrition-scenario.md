# Slice 04 — T2 Accelerated nutrition scenario — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A repeatable, unattended test that runs a character through three accelerated game-days at a fixed daily calorie intake on the live server, samples nutrition hourly, and checks the measured weight trajectory against the decoded weight model — plus the harness test layer and `pzt scenario` runner every later scenario reuses.

**Architecture:** A shared harness module `PZTestKit_Test.lua` provides `TK.test`, `TK.eventually`, assertions and a game-time scheduler on `EveryOneMinute`; scenario files under `testing/PZTestKit/PZTestKit/42/media/lua/client/scenarios/` register tests; `pzt scenario <name>` boots the fixture, attaches the admin client, sets `settimespeed`, sends `test.run <name>` over the bus, waits for `test_<name>.json`, restores speed, tears down, and evaluates the model prediction in Python from the samples.

**Tech Stack:** harness Lua (Kahlua), `pzt`, Python 3.13 (stdlib).

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades; brief commits without attribution; one live session at a time; defaults + `docs/decisions.md`; scenario must finish in **< 15 min wall** unattended; always restore time speed with `settimespeed 1` (broadcast) — never a server-only reset (spike S5).

---

## Header

- Slice: **04** · Phase T2 · Depends on: 01 (predictions section, `nutrition.set`), 02 (`setCalories` clamps) · Estimate: 3 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; board `docs/progress.md`; ledger `docs/decisions.md`; spec above.
- Weight model (`docs/vanilla/nutrition-core.md`, cited to `Nutrition.updateWeight`): gain when `calories > 1000 + (weight−80)×40` at `1.3e-5 kg/game-s × min(1, calories/4000)` (×2 if carbs or lipids > 400, ×3 if > 700); loss when `calories < min(0,(weight−70)×30)` at `8.5e-6 × min(1, |calories|/2500)`. Slice 01's `eating-pipeline.md` has the `setCalories` clamps and the "Inputs for the 3-day scenario" section; slice 03 (if done) has the rest burn rate.
- Nutrition is computed on the **client** (S6): the scenario runs client-side on the admin client; the server mirrors.
- Time: `settimespeed 30` → 1 game-hour ≈ 8 s wall (measured 8.0–8.9 game-min per wall-s in S5); 72 game-hours ≈ 10 min. Both sides accelerate; restore with `settimespeed 1`.
- Bus + results: `Client.send(cmd, args)`; results are JSON files in `<cachedir>/Lua/pzt-results/<name>.json` (`bus.wait_result(name, timeout, after)`); harness `TK.result(name, table)`; JSON encoder `TK.json`.
- Harness files: `testing/PZTestKit/PZTestKit/42/media/lua/{shared,client,server}/`; `pzt` CLI: `testing/pzt/cli.py`, session helpers `testing/pzt/session.py`, spikes pattern `testing/pzt/spikes.py`.

## Questions

1. Does the measured weight change over 3 game-days at +4000 kcal/day (and, second run, at 0 intake) match the model applied to the measured hourly calorie samples, within ±15 %?
2. Is `EveryOneMinute` a reliable game-time scheduler at 30× (does it fire ~once per game-minute, i.e. ~4 Hz wall)?
3. What is the scenario's wall time and is the run green without a human (click-through, speed restore, teardown)?

## Method

> **Superseded by the slice's rulings** (`docs/decisions.md`, 2026-09-10, and the SDD ledger
> `.superpowers/sdd/04-nutrition-scenario/progress.md`). The design below was written before
> slices 01 and 03 established that the **server** owns `Nutrition`, and two of its decisions
> did not survive that:
>
> 1. **Scenarios run server-side, not client-side.** The test layer stays in
>    `shared/PZTestKit_Test.lua`, but the scenario files live under
>    `server/scenarios/PZTestKit_Scenario_{Smoke,Nutrition}.lua`, `test.run` goes on the
>    **server** bus, and `pzt scenario` gained `--side server|client` (default **server**).
>    `t.player` is resolved by username out of `getOnlinePlayers()` — there is no `getPlayer()`
>    on a dedicated server — so the admin client is still attached, as the live player.
>    **Every line in this plan that says *client* is obsolete, above this note as well as
>    below it**, specifically: the **Architecture** paragraph at the top (`:7`), which puts the
>    scenario files under `client/scenarios/` — and which also names the polling helper
>    `TK.eventually`, where the shipped one is the context method `t:eventually(pred,
>    budgetMinutes, label)`; the Cold-start context line "Nutrition is computed on the
>    **client** (S6)" (`:27`), whose direction slice 01 reversed; and the corresponding lines
>    in Tasks 1/2/3 below.
> 2. **Daily intake is two +2 000 doses 12 game-hours apart**, not one +4 000: `setCalories`
>    clamps at 3 700, so a single dose would measure the clamp rather than the intake (the
>    plan's own decision point, taken). Even split, the ceiling still swallowed 4 790 of the
>    12 000 kcal — accounted for in the doc.
>
> The code sketches below are what was proposed, not what shipped; the shipped API is
> documented in [`docs/testing/README.md`](../../testing/README.md) § Scenarios and the test
> layer, and the results in
> [`docs/vanilla/nutrition-core.md`](../../vanilla/nutrition-core.md) § Verified on server.

### Task 1: Test layer (`PZTestKit_Test.lua`, shared)

**Files:** Create `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Test.lua`; Modify `PZTestKit_Core.lua` (nothing required — the test file uses `TK.*`; it must load after Core: name it `PZTestKit_Test.lua`, Lua files in a folder load alphabetically and `Core` < `Test`).

**Interfaces (produces):**
- `TK.test(name, spec)` — registers `spec = { timeoutMin = <game minutes>, run = function(t) ... end }`. The `run` function receives a test context `t` with: `t:log(msg)`, `t:sample(tbl)` (appends to `t.samples`), `t:at(gameMinutes, fn)` (schedule `fn` at a game-minute offset from test start), `t:every(gameMinutes, fn)` (repeat), `t:done(pass, detail)` (finish now), `t:eventually(pred, gameMinutes, label)` (poll `pred` every game-minute; fail after the budget), `t:assert(cond, msg)`, `t:near(a, b, tol, msg)`.
- Scheduler: `Events.EveryOneMinute` advances `TK.tests.clock` (game minutes since the test started) and runs due callbacks; on completion or timeout writes `TK.result("test_" .. name, { pass = bool, detail = str, samples = t.samples, log = t.log, startedWorldAge = …, endedWorldAge = …, gameMinutes = … })`.
- Bus commands: `test.list` → registered names; `test.run <name>` → starts it (ack `started` / `unknown` / `already running`); `test.status` → `{running, clock, name}`.

- [x] **Step 1: Write the module**

```lua
-- PZTestKit test layer: game-time scheduled tests, one JSON result per test.
TK.tests = TK.tests or { registry = {}, running = nil, clock = 0, due = {} }
local T = TK.tests

local Ctx = {}
Ctx.__index = Ctx
function Ctx:log(msg) self.logLines[#self.logLines + 1] = string.format("[%dm] %s", T.clock, tostring(msg)) end
function Ctx:sample(tbl) tbl.gameMinute = T.clock; tbl.worldAge = getGameTime():getWorldAgeHours(); self.samples[#self.samples + 1] = tbl end
function Ctx:at(minutes, fn) T.due[#T.due + 1] = { at = T.clock + minutes, fn = fn } end
function Ctx:every(minutes, fn)
    local function tick() if T.running == self then fn(); self:at(minutes, tick) end end
    self:at(minutes, tick)
end
function Ctx:assert(cond, msg) if not cond then self.failures[#self.failures + 1] = tostring(msg) end; return cond end
function Ctx:near(a, b, tol, msg)
    local ok = a ~= nil and b ~= nil and math.abs(a - b) <= tol
    return self:assert(ok, string.format("%s: %s vs %s (tol %s)", tostring(msg), tostring(a), tostring(b), tostring(tol)))
end
function Ctx:eventually(pred, budgetMinutes, label)
    local deadline = T.clock + budgetMinutes
    local function poll()
        if T.running ~= self then return end
        if pred() then self:log("eventually ok: " .. tostring(label)); return end
        if T.clock >= deadline then self:assert(false, "eventually timed out: " .. tostring(label)); self:done(false, "timeout: " .. tostring(label)); return end
        self:at(1, poll)
    end
    poll()
end
function Ctx:done(pass, detail)
    if T.running ~= self then return end
    T.running = nil
    T.due = {}
    local ok = pass and #self.failures == 0
    TK.result("test_" .. self.name, { pass = ok, detail = detail or "", failures = self.failures,
        samples = self.samples, log = self.logLines, gameMinutes = T.clock,
        startedWorldAge = self.startedWorldAge, endedWorldAge = getGameTime():getWorldAgeHours() })
    TK.log(string.format("test %s %s (%d game-min)", self.name, ok and "PASS" or "FAIL", T.clock))
end

function TK.test(name, spec) T.registry[name] = spec end

local function start(name)
    local spec = T.registry[name]
    if not spec then return "unknown" end
    if T.running then return "already running " .. T.running.name end
    local ctx = setmetatable({ name = name, samples = {}, logLines = {}, failures = {},
                               startedWorldAge = getGameTime():getWorldAgeHours() }, Ctx)
    T.running, T.clock, T.due = ctx, 0, {}
    ctx:at(spec.timeoutMin or 600, function() ctx:done(false, "test timeout") end)
    local ok, err = pcall(spec.run, ctx)
    if not ok then ctx:done(false, "run() error: " .. tostring(err)) end
    return "started"
end

local function onMinute()
    if not T.running then return end
    T.clock = T.clock + 1
    local due, rest = {}, {}
    for _, d in ipairs(T.due) do if d.at <= T.clock then due[#due + 1] = d else rest[#rest + 1] = d end end
    T.due = rest
    for _, d in ipairs(due) do
        local ok, err = pcall(d.fn)
        if not ok and T.running then T.running:assert(false, "callback error: " .. tostring(err)) end
    end
end
if Events.EveryOneMinute then Events.EveryOneMinute.Add(onMinute) end

TK.register("test.list", function() local out = {}; for k in pairs(T.registry) do out[#out + 1] = k end; return out end)
TK.register("test.run", function(argv) return start(argv[1]) end)
TK.register("test.status", function() return { running = T.running and T.running.name or false, clock = T.clock } end)
TK.log("test layer loaded")
```

- [x] **Step 2: Add a trivial scenario to prove the scheduler** — `client/scenarios/PZTestKit_Scenario_Smoke.lua`:

```lua
TK.test("smoke_clock", { timeoutMin = 30, run = function(t)
    t:every(5, function() t:sample({ calories = getPlayer():getNutrition():getCalories() }) end)
    t:at(20, function() t:assert(#t.samples >= 3, "expected >= 3 samples, got " .. #t.samples); t:done(true, "clock ok") end)
end })
```

(Confirm the client loads `client/scenarios/*.lua` — the loader is recursive; if not, move the file up a level.)

- [x] **Step 3: Commit** — `git commit -m "Slice 04: harness test layer"`

### Task 2: `pzt scenario`

**Files:** Create `testing/pzt/scenario.py`; Modify `testing/pzt/cli.py` (subparser `scenario <name> [--speed 30] [--timeout 900]`).

**Interfaces (produces):** `python testing/pzt scenario <name>` → exit 0 iff the test result has `pass == true` and the Python-side evaluation (if any, `EVALUATORS[name]`) passes; prints the timeline; writes `runs/scenario-*/report.json` with the result doc and evaluation.

- [x] **Step 1: Write it**

```python
"""pzt scenario <name>: run one harness test on the fixture session at accelerated time."""
import json, os, time
from . import fixture as fx
from .bus import parse_ack
from .paths import new_run_dir
from .session import Timeline, make_client, make_server, say, teardown, write_report

EVALUATORS = {}   # name -> function(result_doc) -> (ok: bool, detail: dict); filled by scenario modules

def evaluate(name, doc):
    fn = EVALUATORS.get(name)
    return fn(doc) if fn else (True, {})

def run(a):
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("scenario")
    tl = Timeline(); say(f"run: {run_dir}")
    server = make_server(run_dir, rec); clients = []; result = "FAIL"; doc = None; ev = {}
    try:
        server.start(timeout=a.server_timeout); tl.mark("server_started", t=server.t_started)
        c, _ = make_client(run_dir, "admin", server, rec); c.start(); clients.append(c)
        tl.mark("client_ready", t=c.wait_ready(timeout=a.client_timeout))
        names = parse_ack(c.send("test.list"))[1]
        if a.name not in (names or []):
            raise RuntimeError(f"unknown test {a.name}; registered: {names}")
        ok, rep = server.rcon(f"settimespeed {a.speed}"); tl.mark("settimespeed", x=a.speed, reply=rep[:40])
        t0 = time.time()
        tl.mark("test_run", ack=c.send("test.run", a.name))
        doc = c.bus.wait_result(f"test_{a.name}", timeout=a.timeout, after=t0 - 0.2)
        tl.mark("test_result", passed=doc.get("pass"), game_minutes=doc.get("gameMinutes"), detail=doc.get("detail"))
        ok, ev = evaluate(a.name, doc); tl.mark("evaluation", ok=ok, **{k: v for k, v in ev.items() if not isinstance(v, (list, dict))})
        result = "PASS" if (doc.get("pass") and ok) else "FAIL"
    except (RuntimeError, TimeoutError) as e:
        tl.mark("error", detail=str(e)[:200])
    finally:
        try:
            server.rcon("settimespeed 1"); tl.mark("settimespeed", x=1)
        finally:
            teardown(tl, server, clients)
            for c in clients: c.kill()
            server.kill()
    write_report(run_dir, {"run_id": run_id, "result": result, "timeline": tl.items, "test": doc, "evaluation": ev,
                           "server_errors": server.errors[:20]})
    say(f"\nRESULT: {result}   (report: {os.path.join(run_dir, 'report.json')})")
    return 0 if result == "PASS" else 1
```

Register in `cli.py`: `p = sub.add_parser("scenario"); p.add_argument("name"); p.add_argument("--fixture", default="default"); p.add_argument("--speed", type=int, default=30); p.add_argument("--timeout", type=int, default=900); common_server(p); common_client(p); p.set_defaults(fn=scenario.run)` and import `from . import scenario`; import the evaluator module(s) at the bottom of `scenario.py` (`from . import scenarios_nutrition  # noqa: registers evaluators`) after Task 3 creates it.

- [x] **Step 2: Run the smoke scenario** — `python testing/pzt scenario smoke_clock --speed 30` → Expected: PASS, `game_minutes` ≈ 20 within ~1 min wall (Q2: ≥ 3 samples ⇒ `EveryOneMinute` fires at game-time cadence).
- [x] **Step 3: Commit** — `git commit -m "Slice 04: pzt scenario runner"`

### Task 3: The 3-day nutrition scenario + evaluator

**Files:** Create `testing/PZTestKit/PZTestKit/42/media/lua/client/scenarios/PZTestKit_Scenario_Nutrition.lua`, `testing/pzt/scenarios_nutrition.py`.

- [x] **Step 1: Lua scenario**

```lua
-- 3 accelerated game-days at a fixed daily intake; hourly samples; the model check runs in python.
local function setup(t, intake)
    local n = getPlayer():getNutrition()
    n:setWeight(80); n:setCalories(0); n:setCarbohydrates(0); n:setLipids(0); n:setProteins(0)
    t:log("setup weight=80 calories=0 intake=" .. intake)
end
local function register(name, intake)
    TK.test(name, { timeoutMin = 72 * 60 + 30, run = function(t)
        setup(t, intake)
        local n = getPlayer():getNutrition()
        t:every(60, function() t:sample({ calories = n:getCalories(), weight = n:getWeight(),
            carbs = n:getCarbohydrates(), lipids = n:getLipids(), proteins = n:getProteins() }) end)
        if intake > 0 then
            t:every(24 * 60, function() n:setCalories(n:getCalories() + intake); t:log("fed +" .. intake) end)
        end
        t:at(72 * 60, function() t:done(true, "3 game-days complete") end)
    end })
end
register("nutrition_3day_gain", 4000)
register("nutrition_3day_fast", 0)
```

- [x] **Step 2: Python evaluator** (`scenarios_nutrition.py`): integrate the model over the samples.

```python
"""Model check for the nutrition_3day_* scenarios (weight model: docs/vanilla/nutrition-core.md)."""
from .scenario import EVALUATORS

GAIN_RATE, LOSS_RATE = 1.3e-5, 8.5e-6      # kg per game-second (Nutrition.updateWeight)

def rate(calories, weight, carbs, lipids):
    gain_thr = 1000 + (weight - 80) * 40
    loss_thr = min(0.0, (weight - 70) * 30)
    if calories > gain_thr:
        r = GAIN_RATE * min(1.0, calories / 4000.0)
        if carbs > 700 or lipids > 700: r *= 3
        elif carbs > 400 or lipids > 400: r *= 2
        return r
    if calories < loss_thr:
        return -LOSS_RATE * min(1.0, abs(calories) / 2500.0)
    return 0.0

def evaluate(doc, tolerance=0.15):
    s = doc.get("samples") or []
    if len(s) < 3:
        return False, {"reason": "too few samples", "n": len(s)}
    predicted = s[0]["weight"]
    for a, b in zip(s, s[1:]):
        dt = (b["worldAge"] - a["worldAge"]) * 3600.0          # game-seconds between samples
        predicted += rate(a["calories"], predicted, a["carbs"], a["lipids"]) * dt
    measured_delta = s[-1]["weight"] - s[0]["weight"]
    predicted_delta = predicted - s[0]["weight"]
    tol = max(abs(predicted_delta) * tolerance, 0.05)
    ok = abs(measured_delta - predicted_delta) <= tol
    return ok, {"samples": len(s), "measured_delta_kg": round(measured_delta, 3),
                "predicted_delta_kg": round(predicted_delta, 3), "tolerance_kg": round(tol, 3),
                "game_hours": round(s[-1]["worldAge"] - s[0]["worldAge"], 2)}

EVALUATORS["nutrition_3day_gain"] = evaluate
EVALUATORS["nutrition_3day_fast"] = evaluate
```

Note: the model integrates with the *predicted* weight (thresholds depend on it), sample-to-sample; hourly sampling is the resolution — state it in the doc.

- [x] **Step 3: Run both** — `python testing/pzt scenario nutrition_3day_gain` and `... nutrition_3day_fast`. Expected: each ≈ 10–11 min wall, `pass=true`; evaluation within tolerance. If the evaluation fails, that is the finding: record measured vs predicted, check the samples for clamping (`setCalories` clamp from slice 01/02), re-read `updateWeight` for a term the doc missed, and document.
- [x] **Step 4: Commit** — `git commit -m "Slice 04: 3-day nutrition scenario and model check"`

### Task 4: Doc

- [x] **Step 1:** add a **"Verified on server"** section to `docs/vanilla/nutrition-core.md`: the two runs (ids, wall time, game-hours, measured vs predicted, tolerance), what the check does and does not cover (no burn-rate assertion; hourly resolution), and an `Ev` M row in the model table. Update `docs/testing/README.md` (scenario command, test layer API) and `docs/testing/pipeline-design.md` roadmap (T2 ✅ with the numbers).
- [x] **Step 2:** lint → 0; commit `Slice 04: T2 verified on server`.

## Deliverables

- `PZTestKit_Test.lua`, `scenarios/PZTestKit_Scenario_{Smoke,Nutrition}.lua`
- `testing/pzt/scenario.py`, `scenarios_nutrition.py`, `cli.py` (scenario subcommand)
- results under `testing/runs/scenario-*/`; docs updated as above

## Acceptance checks

1. `python testing/pzt scenario smoke_clock` → PASS in < 2 min.
2. `python testing/pzt scenario nutrition_3day_gain` and `_fast` → PASS (or documented finding) each in < 15 min wall, no human input.
3. `python tools/doc_lint.py` → 0; `python testing/pzt run --hold 5` → PASS.

## Expected decision points (defaults)

- `EveryOneMinute` not firing at 30× cadence → fall back to `OnTick` with `getGameTime():getWorldAgeHours()` deltas as the clock (same API).
- A `setCalories` clamp below 4000/day intake → feed in two +2000 doses 12 h apart; record.
- Evaluation outside tolerance → do not loosen the tolerance; document the discrepancy and open a question for slice 03/P5.

## Done protocol

- `docs/progress.md` 04 → done (+ ripple: the test-layer API is now the L2/L3 base for all later slices); wave 1 complete → write wave-2 plans (05, 06, 07) before continuing; `docs/decisions.md`; push.

## Acceptance results (2026-09-10)

Every step above ran (the ticks are the record); this section is the outcome of the three
acceptance checks. Live runs: Task 2's `smoke_clock` (twice — at ship and again after the
T1+T2 fix round) and Task 3's three 3-day scenarios, all on the golden fixture `default`,
build 42.20.4, side **server**, subject `admin`, `settimespeed 30`. Commits: `3b1ac80` (test
layer), `4b964d3` (`pzt scenario`), `707c878` (scenario + evaluator), `dd84a37` (T1+T2 fix
round), `ef64241` (T3 fix round), plus this task's doc commit.

1. `python testing/pzt scenario smoke_clock` → **PASS in 64.7 s**, and **PASS in 63.1 s** on
   the re-run after the fix round — both well inside the 2-minute budget. This is also **Q2's
   answer: yes.** `EveryOneMinute` drives the game-minute clock on the *dedicated server* at
   30×, measured at 1.015 ticks per game-minute in the first smoke run, 0.983 in the second
   and **1.000 in all three 3-day runs** (7.99–8.00 game-minutes per wall second). The
   `OnTick` fallback in the decision points below was never needed.
2. `python testing/pzt scenario nutrition_3day_gain` / `nutrition_3day_fast` → three
   unattended runs, no human input, **≈593 s wall from server launch to the result doc** (603 s
   including teardown) each — inside the 15-minute budget — **73 hourly samples over 72.0
   game-hours** and **0 server error lines** in every one. (Those two are runner-clock marks
   from the run reports under `testing/runs/`, which are gitignored; the committed artifacts
   carry the test window alone — `cadence.wall_s` 540.4–540.6 s, `test.run` to the result doc —
   and the ~53 s difference is boot and client attach.)

   | Run id | Scenario | Measured Δ | Predicted Δ | Tol | Verdict |
   |---|---|---|---|---|---|
   | `scenario-20260910-052624` | gain, hunger/thirst not pinned | +1.073 kg (+1.045 over the 34 alive hours) | +2.688 (+1.057 alive) | 0.403 | **FAIL** — subject died at game-hour 35 |
   | `scenario-20260910-054012` | gain, hunger/thirst pinned | **+2.526 kg** | +2.551 | 0.383 | **PASS** |
   | `scenario-20260910-055029` | fast, no intake | **−1.426 kg** | −1.412 | 0.212 | **PASS** |

   **Q1: yes** — both passing runs sit inside 1 % of the model integrated over their own
   calorie traces, and the residuals are the check's own hourly-quadrature bias (a midpoint
   re-integration collapses them to −0.0003 / −0.0002 kg), not model error. **Q3:** ≈10 min
   wall per run, green with no human — click-through, `settimespeed` restore and teardown all
   automatic. The FAIL is the documented finding, not a loosened tolerance (the decision point
   below was honoured): `setCalories` is not food, the unwatered subject died of thirst at
   game-hour 35, and `Nutrition.update` stops on a corpse. Full write-up:
   [`docs/vanilla/nutrition-core.md`](../../vanilla/nutrition-core.md) § Verified on server;
   the three result JSONs are committed under `testing/artifacts/<run id>/`.
3. `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → **0
   findings** across the trees this slice touched; the 4 pre-existing findings in
   `docs/mods-survey/teardowns/` remain deferred by the standing ruling in
   [`docs/decisions.md`](../../decisions.md). `python testing/pzt run --hold 5` → **MET**:
   `run-20260910-065745` (06:57, on a tree carrying both slice-04 harness commits `dd84a37`
   and `ef64241`) reports **PASS with 0 server error lines**. By the 2026-09-10 ruling in the
   same ledger, that run *is* this check — it is the "next live run after the slice-04 harness
   edits" the ruling folded it into. The one exercise deferred alongside it,
   `nutrition.applytraits`, has since run as well: `accept03-20260910-065854` called it and the
   server answered `applied: true` at weight 80, no band trait held (as expected in the
   75–85 open interval). Both run directories are local under `testing/runs/` (gitignored).
   Caveat: the slice's final fix wave touched the harness again after those runs, so they cover
   the tree at `ef64241`; the `pzt scenario smoke_clock` run taken after that commit is what
   re-covers the test layer.

Two plan assumptions did not survive, both recorded above under § Method: client-side
scenarios (the server owns `Nutrition`) and the one-dose-a-day feed (the 3 700 clamp). A
third — the Task 3 dispatch's prior that the gain run would put on 0.5–1 kg, and the T2
roadmap example "3 game-days at 4000 cal gains ≥3 kg" in
[`docs/testing/pipeline-design.md`](../../testing/pipeline-design.md) (corrected there) — was
simply wrong in size: the model predicts **+2.55 kg** under the clamp and the server measured
**+2.53**.
