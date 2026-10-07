# Plan 11 — The Review Fixes Implementation Plan (DRAFT)

> **DRAFT, not for execution.** Written 2026-10-07 as Plan 10, then held back so research spikes and a behaviour-preserving refactor run first (`docs/superpowers/plans/2026-10-07-plan-10-spikes-and-refactor.md`). Plan 11 is rewritten from this draft and the decision memo `docs/superpowers/specs/2026-10-07-plan-11-decisions.md` after Angus reviews the memo. The memo landed 2026-10-07; its "Changes to the draft" lines per spike and its five decisions for Angus govern the rewrite. Known rewrites: Task 1's helper set moves to Plan 10 R1 (its zero-age fix stays here); every code sample assuming `P.onMinute`, `KIN.lastAbsorbed` or local helpers is re-based on Plan 10 R2's pipeline; Tasks 3, 6 and 13 follow S1 and S2; Task 2 follows S3; Task 7 follows S5; Task 9 follows S4; Task 12's update procedure follows S6; plan numbering, ids and the ledger path move to Plan 11.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every confirmed defect and make every sensible improvement the 2026-10-07 whole-mod review found, so that 1.0.1 can go to the Workshop: no player is ever skipped by the slow clock, a respawn never leaves a record marked dead, one player's error never switches off the simulation for the server, a failed clock read never empties a stomach, Overlay means what its docs say, hunger has a tuned and adjustable satiety, and the item pass conserves energy through its recipes.

**Architecture:** Each defect gets a test that reproduces it before the fix — a kernel test under the lupa host for pure logic, a shape test that loads the real server adapters under Lua stand-ins for wiring, and one live session on the two-client fixture for what only the engine can show. New pure logic lands in kernel files (one statement per line, inside the 100 % line gate): the stagger (`NR_Kernel_Stagger.lua`), the class signature (`K.view.pushSignature`) and the instance scale (`K.vector.instanceScale`). Adapters stay read, call, write. One shared helper set in `NR_Core.lua` replaces the eight divergent copies whose disagreement caused the stomach bug.

**Tech Stack:** the mod's Lua (Kahlua subset; `lupa` 2.8 Lua 5.1 host for kernel and shape tests), Python 3 tools (`tools/food_nutrients.py`, `tools/release_pack.py`), the harness (`pzt`, fixture `two`), the claims register and its delta tools.

**Spec:** the review record — the architecture review, the two ultra slices, the local xhigh adapter review and the local item-pass review of 2026-10-07, summarised in the ledger of this plan's Task 0 (`.superpowers/sdd/2026-10-07-plan-10-review-fixes/progress.md`, first block, copied verbatim from the session); the design spec `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` § 4.1 (the slow clock and the stagger), § 4.3 (the takeover), § 4.6 (the item pass), § 4.8 (sync), § 4.9 (Overlay as the documented fallback), § 6 (performance), § 7 item 37 (the gastric half-time a game choice).

## Global Constraints

Everything in Plan 9's Global Constraints holds (`docs/superpowers/plans/2026-10-06-plan-9-packaging-release.md`), and through it Plans 1–8's. Plan 10 adds:

- **A defect is fixed test-first:** the test that reproduces the reviewed failure is written, run and seen to FAIL on the pre-fix code before the fix lands; the report quotes the failing run's last line. A task with no red run is sent back.
- **Kernel files are pure and one statement per line;** `python -m pytest testing/tests/kernel -q` keeps `test_zz_coverage.py` green (100 % of kernel lines).
- **Adapters read, call and write:** new arithmetic or branching on numbers goes in a kernel function; an adapter may branch on presence, side and mode.
- **Every `mod/` edit shifts `repo:mod/` pointers:** the implementer runs `PYTHONIOENCODING=utf-8 python tools/claims_check.py` (the full run) after the edit and lists each `pointer-line` finding (row, old line, new line) in the report; the implementer never edits `docs/reference/claims.tsv`; the controller re-anchors at the wave's close in one register commit.
- **The `mod/` gates on every mod commit:** `python tools/mod_lint.py mod/NutritionRevamp` 0 ERROR; `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` 0; `python tools/hotpath_lint.py mod` 0; `python tools/science_check.py --scan mod` 0; `python tools/release_pack.py check mod/NutritionRevamp` 0 ERROR.
- **The version is 1.0.1** from Task 12 on: `NR_Core.lua` `version = "1.0.1"` and `mod.info` `modversion=1.0.1` agree (the release tool checks).
- **A generated file is never edited by hand:** `tools/food_nutrients.py --write` regenerates, `--check` must be in sync.
- **Live:** one session at a time; `python testing/pzt doctor` first; fixture `two`; the STAGED copy boots, never `mod/`; `Nutrition = false`; a driver is never edited after its run; a falsified or unmeasured reading is written as such.
- **Pytest floor 2544;** the close writes the new count into CLAUDE.md § 3.
- **Rulings this plan takes** (each a ledger line and a `Ruling:` row at the close):
  1. **Order and parallelism:** Task 1 alone (it touches every server adapter) → Wave B in parallel on disjoint files: Tasks 2, 3, 4, 5, 6, 7, 8, 11 → Wave C in sequence: Task 9 → Task 10 → Task 12 → Task 13 (live) → Task 14 (docs) → Task 15 (close).
  2. **The stagger keeps its queue across minutes and sizes its share from the last minute's tick count:** a username still pending at the next minute stays at the front (never doubled — the review-t4 I1 concern), new ones append, and each tick processes `ceil(queued / ticksLastMinute)` players (all of them when the last minute had no tick, as under sleep fast-forward). The kernels integrate elapsed time by world age, so a late minute loses nothing.
  3. **The drain stays on `OnTick`** with an O(1) early-out: the work is the slow minute's, spread across ticks, not per-tick simulation; the comment stops citing #1071/#1080 as support and states the departure.
  4. **A respawn or a reconnect is a new `IsoPlayer` under a username:** `OnNewGame` stores the new object in `P.online` before firing first sight; `P.minute` fires first sight when the stored object differs from the online one (a reconnect inside one game minute); the queued work always uses `P.online[username]` at drain time, so a dead body never reaches `P.work` after its respawn.
  5. **`resets` counts respawns only:** `S.reset` increments when the old record is marked dead; a first character keeps the old count (0).
  6. **The takeover fails over server-wide (the hook is all-or-nothing, so vanilla can only run for everyone) but recovers:** a hoist failure counts toward the same three strikes per player as a body failure; a disable re-arms on the slow clock after 5, then 15, then 60 slow minutes, each attempt logged at level 1; after the third failed re-arm it stays off until restart and says so.
  7. **The per-tick body drops the six reads the kernel no longer uses** (`highThirst`, `lowThirst`, `heartyAppetite`, `lightEater`, `foodEaten`, `thermoFluids`) and moves the six trait reads and the Fitness perk level to the slow clock (stamped into `h.inp` once a minute and at the hoist).
  8. **A class change pushes:** the bus marks a player when the four live class rungs (energy, hydration, stimulant, sleep) change, read from the record each slow minute; the 60 s push gap still applies.
  9. **`mirror.request` is rate-limited to one answer per player per 5 s of server wall clock;** a denied request is counted and dropped.
  10. **Overlay is "nutrients only":** while the takeover is not registered (Overlay chosen, or the failover tripped) vanilla owns hunger, thirst, fatigue and endurance, and the mod's dehydration terms read zero; the README, the sandbox tooltip and COMPATIBILITY say exactly this.
  11. **Micronutrients scale with the instance's calories,** the same scale as the macros Eat delivers; the hunger ratio stays as the fallback when calories are unreadable or zero.
  12. **The item pass conserves energy through food→food recipes that do not inherit food values:** a generator test fails any such recipe whose output energy exceeds its input by more than 25 %, with a reasoned allowlist.
  13. **Satiety is a dial:** `NR.SatietyHalfTime` (game hours, 1–8) sets the stomach's emptying half-time; its default is the value at which a full stomach reaches vanilla's first hunger moodle in the same game hours vanilla takes from a full belly, computed in Task 9 and pinned by a test.
  14. **Records prune only when an operator asks:** `NR.RecordKeepDays` (game days, 0 = never, the default); a record not online and not seen for longer is deleted at server start and once per game day.
  15. **Not this plan:** replacing the takeover with zeroed `ZomboidGlobals` drains (a research arm first); an explicit minute orchestrator and moving the remaining adapter math into kernels (a refactor with no failing behaviour); stripping register ids from shipped comments (they are the maintainers' path to the evidence); cutting the tab, tooltip band or icon column (their open rows stand); server-side gating of the numbers by visibility; the five Workshop code reads (blocked on the subscription); the Lua checksum arm reading (needs a per-client mod source in the harness); the awake-endurance fold (X35).

## Execution order

Task 0 → Task 1 (Opus) → Wave B: Task 2 (Opus) ∥ Task 3 (Opus) ∥ Task 4 (Opus) ∥ Task 5 (Sonnet) ∥ Task 6 (Opus) ∥ Task 7 (Opus) ∥ Task 8 (Opus) ∥ Task 11 (Sonnet) → controller re-anchors the register → Task 9 (Opus) → Task 10 (Sonnet) → Task 12 (Sonnet) → Task 13 (Opus, live) → Task 14 (Sonnet; Opus review) → Task 15 (close). Reviews are read-only: Opus for Tasks 1–4, 6–9, 13; Sonnet for 5, 10, 11, 12.

## File structure

| path | responsibility | task |
|---|---|---|
| `mod/.../shared/NR_Core.lua` (append), every `server/NR_Server_*.lua` with a local `worldAge`/`finite`; `testing/tests/kernel/server_host.py` (new), `test_core_helpers.py` (new), `test_kinetics.py` | one helper set; the Kinetics zero-age fix; the shared shape-test host | 1 |
| `mod/.../shared/NR_Kernel_Stagger.lua` (new), `server/NR_Server_Players.lua`, `server/NR_Server_Store.lua` (`S.reset`), `server/NR_Server_Options.lua` (dead branch); `test_kernel_stagger.py`, `test_players_shape.py` (new) | the stagger, the respawn and reconnect, the reset count | 2 |
| `server/NR_Server_Fast.lua`; `test_fast_failover_shape.py` (new), `test_kernel_fast.py` | strikes, re-arm, the departure leak, the per-tick trim | 3 |
| `server/NR_Server_Bus.lua`, `shared/NR_Kernel_View.lua` (`pushSignature`); `test_bus_shape.py` (new), `test_kernel_view.py` | the guarded build, the request limit, the class push | 4 |
| `server/NR_Server_Training.lua`; `test_training_shape.py` | one hit per event; no ranged | 5 |
| `server/NR_Server_Nutrients.lua`, `shared/Translate/EN/Sandbox.json`, `README.md`, `COMPATIBILITY.md`; `test_nutrients_shape.py` | Overlay as nutrients only | 6 |
| `shared/NR_Kernel_Vector.lua`, `server/NR_Server_Intake.lua`; `test_kernel_vector.py`, `test_intake_shape.py` | the instance scale | 7 |
| `data/food-nutrient-map/manufactured-2.csv`, `meat-fish-egg-dairy.csv`, `tools/food_nutrients.py`, the generated files; `tools/tests/test_food_nutrients.py`, `tools/tests/test_recipe_energy.py` (new) | the hot-dog mappings, recipe conservation, the check's blind spots, header churn | 8 |
| `shared/NR_Kernel_Stomach.lua`, `server/NR_Server_Kinetics.lua`, `server/NR_Server_Options.lua`, `42.20.4/media/sandbox-options.txt`, `Translate/EN/Sandbox.json`; `test_kernel_stomach.py`, `test_satiety_default.py` (new) | the satiety dial | 9 |
| `server/NR_Server_Store.lua` (`S.prune`), `server/NR_Server_Options.lua`, `sandbox-options.txt`, `Sandbox.json`; `test_store_prune_shape.py` (new) | record pruning | 10 |
| `shared/NR_Kernel_Nutrients.lua`, `Translate/EN/Moodles.json`, `Translate/EN/UI.json`, `client/NR_Client_Effects.lua` | dead code | 11 |
| `NR_Core.lua` (version), `42.20.4/mod.info`, `README.md`, `CHANGELOG.md`; `testing/tests/test_mod_shipped_docs.py` | 1.0.1 | 12 |
| `server/NR_Server_Bench.lua` (append), `testing/profiles/x21-fixes.toml`, `testing/experiments/x211_fixes.py`, `testing/artifacts/x211-*/` | the live acceptance and the real cost | 13 |
| `docs/platform/lessons.md`, `docs/areas/testing-your-mod.md`, `docs/areas/mp-sync.md`, `docs/platform/harness.md`, `docs/reference/artifacts.md`, the skills that quote touched rules, `CLAUDE.md` | the documentation delta and the process rules | 14 |

(`mod/...` is `mod/NutritionRevamp/common/media/lua`.)

---

### Task 0: The workspace — controller

- [ ] `scripts/sdd-workspace docs/superpowers/plans/2026-10-07-plan-10-review-fixes.md`; the ledger's first block copies the four review reports' findings verbatim from the session (the architecture review, ultra slice 1, ultra slice 2 plus the local xhigh adapter review, the local item-pass review) so every implementer reads the same evidence; the review branches `review/mod-1-kernel`, `review/mod-2-adapters`, `review/mod-3-itempass` are left as they are.

---

### Task 1: One helper set, the zero-age stomach dump, the shared test host — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Core.lua` (append after the last line)
- Modify: every server adapter with a local copy — `NR_Server_Effects.lua:109-133`, `NR_Server_Fast.lua:83`, `NR_Server_Intake.lua:131,411,416`, `NR_Server_Kinetics.lua:38-44`, `NR_Server_Metabolism.lua:59-92`, `NR_Server_Nutrients.lua:94-121`, `NR_Server_Players.lua:12-18`, `NR_Server_Strength.lua:55-87`, `NR_Server_Training.lua:59`, `NR_Server_Weight.lua:54`
- Create: `testing/tests/kernel/server_host.py`, `testing/tests/kernel/test_core_helpers.py`
- Modify: `testing/tests/kernel/test_kinetics.py`

**Interfaces:**
- Produces: `NR.worldAge() -> number|nil` (nil when `getGameTime` or `getWorldAgeHours` is absent, raises or returns a non-number); `NR.finite(x) -> boolean`; `NR.num(obj, name, dflt, ...) -> number` (the guarded call's number result, `dflt` when absent, raising or non-finite); `NR.obj(o, name, ...) -> value|nil`; `NR.flag(o, name, ...) -> boolean`. Python: `server_host.Host` with `.rt`, `.G`, `.NR`, `.K`, `.T` (the `NR_T` stand-in table), `.player(name, cal, carb, lip, pro, dead=False)`, `.online(*players)` (sets `getOnlinePlayers`), `.minute()` (fires every `EveryOneMinute` listener), `.tick(n=1)` (fires every `OnTick` listener n times), `.fire(event, *args)`, `.record(name)`, `.printed()`.

- [ ] **Step 1: Read** `testing/tests/kernel/test_server_reconcile_shape.py:1-140` (the `ENV`, `PLAYER` and `Host` you generalise) and each adapter's local helper bodies listed above; note which return `0` and which return `nil` on failure (Kinetics, Intake, Fast, Players return 0; Metabolism, Nutrients, Strength return nil).

- [ ] **Step 2: Write `server_host.py`** — the `ENV` and `PLAYER` strings of `test_server_reconcile_shape.py` moved verbatim into this module (that test keeps its own copies; do not edit it), with `PLAYER` gaining a `dead` argument (`p.isDead = function(s) return dead end`) and a mutable field `p.deadFlag` read by `isDead`, plus:

```python
class Host:
    def __init__(self, extra_env=""):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(ENV + extra_env)
        for p in _shared_files():
            _load(self.rt, p)
        for p in sorted(glob.glob(os.path.join(SERVER, "NR_Server_*.lua"))):
            _load(self.rt, p)
        self.G = self.rt.globals()
        self.NR = self.G.NutritionRevamp
        self.K = self.NR.kernel
        self.T = self.G.NR_T
        self.NR.server.store.records = self.rt.table()
        for fn in self.T.adds["OnServerStarted"].values():
            fn()

    def player(self, name="admin", cal=1000.0, carb=100.0, lip=40.0, pro=60.0, dead=False):
        return self.rt.eval(PLAYER)(name, cal, carb, lip, pro, dead)

    def online(self, *players):
        lst = self.rt.table(*players)
        self.G.getOnlinePlayers = self.rt.eval(
            "function(l) return function() return { size = function(s) return #l end, "
            "get = function(s, i) return l[i + 1] end } end end")(lst)

    def fire(self, event, *args):
        for fn in self.T.adds[event].values():
            fn(*args)

    def minute(self):
        self.fire("EveryOneMinute")

    def tick(self, n=1):
        for _ in range(n):
            self.fire("OnTick")

    def record(self, name):
        return self.NR.server.store.records[name]

    def printed(self):
        return list(self.T.printed.values())
```

- [ ] **Step 3: Write the failing tests.** `test_core_helpers.py`:

```python
from .server_host import Host

def test_worldAge_is_nil_when_the_clock_read_fails():
    h = Host()
    h.G.getGameTime = h.rt.eval("function() error('boom') end")
    assert h.NR.worldAge() is None

def test_worldAge_reads_the_age():
    h = Host()
    h.T.age = 123.5
    assert h.NR.worldAge() == 123.5

def test_finite_rejects_nan_and_inf():
    h = Host()
    nan, inf = h.rt.eval("0/0"), h.rt.eval("1/0")
    assert h.NR.finite(1.0) and not h.NR.finite(nan) and not h.NR.finite(inf) and not h.NR.finite("1")

def test_num_falls_back_on_absent_raising_or_nonfinite():
    h = Host()
    o = h.rt.eval("{ a = function(s) return 2 end, b = function(s) error('x') end, c = function(s) return 0/0 end }")
    assert h.NR.num(o, "a", 7) == 2
    assert h.NR.num(o, "b", 7) == 7 and h.NR.num(o, "c", 7) == 7 and h.NR.num(o, "zz", 7) == 7
```

In `test_kinetics.py` append (the reproduction of the reviewed stomach dump):

```python
from server_host import Host

def test_a_failed_clock_read_never_empties_the_stomach_on_the_next_minute():
    h = Host()
    p = h.player("admin")
    h.online(p)
    h.T.age = 500.0
    h.minute(); h.tick(5)                       # first sight and one worked minute at age 500
    fill0 = h.record("admin").stomachFill
    good = h.G.getGameTime
    h.G.getGameTime = h.rt.eval("function() error('clock') end")
    h.minute(); h.tick(5)                       # a minute whose clock read fails
    h.G.getGameTime = good
    h.T.age = 500.0 + 1 / 60
    h.minute(); h.tick(5)                       # the next good minute: one game minute later
    assert h.record("admin").kineticsAge == 500.0 + 1 / 60
    assert h.record("admin").stomachFill > fill0 - 0.01   # one minute of emptying, not 500 hours
```

- [ ] **Step 4: Run** `python -m pytest testing/tests/kernel/test_core_helpers.py testing/tests/kernel/test_kinetics.py -q` — expected FAIL (`NR.worldAge` is nil; the stomach test fails on the fill). Quote the last line in the report.

- [ ] **Step 5: Implement.** Append to `NR_Core.lua`:

```lua
-- The shared adapter helpers (Plan 10 Task 1): one copy, one failure meaning. worldAge is nil when the
-- clock cannot be read, so a caller skips its minute instead of stamping 0 (the Kinetics stomach dump).
function NR.worldAge()
    if getGameTime == nil then return nil end
    local ok, gt = pcall(getGameTime)
    if not ok or gt == nil then return nil end
    local okA, present, age = pcall(NR.call, gt, "getWorldAgeHours")
    if okA and present and NR.finite(age) then return age end   -- as landed at Plan 10 R1 (b098533)
    return nil
end

function NR.finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

function NR.num(o, name, dflt, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if ok and present and NR.finite(v) then return v end
    return dflt
end

function NR.obj(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if ok and present then return v end
    return nil
end

function NR.flag(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    return ok and present and v == true
end
```

In each adapter, delete the local helper and alias the shared one at the top of the file (`local worldAge = NR.worldAge`, `local finite = NR.finite`, `local num = NR.num`, `local obj = NR.obj`, `local flag = NR.flag`) — keeping call sites unchanged — EXCEPT where a local helper's signature differs (`NR_Server_Intake.lua:411` `num(v)` takes a value, not an object: rename the local to `numv` with body `if NR.finite(v) then return v end; return 0` only if its callers depend on 0, else alias to a one-line `local function numv(v) return NR.finite(v) and v or 0 end`; keep `IN.isFinite` as `IN.isFinite = NR.finite`, since Kinetics reads it by name). Every caller of a former 0-returning `worldAge` (Kinetics, Intake, Fast, Players) now handles nil: in `NR_Server_Kinetics.lua` `step`, the first lines become

```lua
    local age = worldAge()
    if age == nil then
        KIN.lastAbsorbed[username] = nil
        KIN.lastMealCa[username] = nil
        return                                   -- a minute with no clock read is skipped, never stamped
    end
```

in `NR_Server_Players.lua` `P.work`, `local age = worldAge(); if age == nil then return end` before the store read (and `P.minute`'s `store.get(username, worldAge())` passes `worldAge() or 0` — a new record's firstSeen may read 0 on a failed read, nothing integrates from it); in Fast and Intake, read each site and make a nil age skip the dependent arithmetic (list each site and its handling in the report).

- [ ] **Step 6: Run** the two test files (PASS), then `python -m pytest testing/tests/kernel -q` (green, coverage included), then the `mod/` gates and the full `claims_check` (list the pointer shifts).
- [ ] **Step 7: Commit** `Adapters: one helper set in NR_Core (worldAge nil on a failed read), the Kinetics minute skipped instead of stamped 0, the shared shape-test host` -- the touched files.

---

### Task 2: The player clock — the stagger, the respawn, the reconnect, the reset count — Opus implementer, Opus reviewer

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stagger.lua`, `testing/tests/kernel/test_kernel_stagger.py`, `testing/tests/kernel/test_players_shape.py`
- Modify: `mod/.../server/NR_Server_Players.lua` (whole file body below the header), `NR_Server_Store.lua` (`S.reset`), `NR_Server_Options.lua:92-110` (the dead `pollFromPlayers` branch)

**Interfaces:**
- Consumes: `NR.worldAge` (Task 1); `server_host.Host` (Task 1).
- Produces: `K.stagger.merge(pending, head, roster) -> list` (a new list); `K.stagger.perTick(queued, ticksLastMinute) -> integer`; `P.ticks`, `P.ticksLastMinute`, `P.perTick` fields on `NR.server.players`.

- [ ] **Step 1: Write the failing kernel test** `test_kernel_stagger.py` (it fails because the file does not exist; the conftest loads every `NR_Kernel*.lua`):

```python
def lst(h, *xs):
    return h.rt.table(*xs)

def tolist(t):
    return [t[i] for i in range(1, len(t) + 1)]

def test_merge_keeps_pending_first_never_doubles_and_drops_the_departed(kernel):
    out = kernel.call("stagger.merge", lst(kernel, "a", "b", "c"), 2, lst(kernel, "a", "c", "d"))
    assert tolist(out) == ["c", "a", "d"]        # b left; c still pending stays first; a re-queued once; d new

def test_merge_with_an_empty_pending_queue_is_the_roster(kernel):
    assert tolist(kernel.call("stagger.merge", lst(kernel), 1, lst(kernel, "x", "y"))) == ["x", "y"]

def test_perTick_spreads_over_the_last_minutes_ticks(kernel):
    assert kernel.call("stagger.perTick", 30, 25) == 2
    assert kernel.call("stagger.perTick", 10, 25) == 1
    assert kernel.call("stagger.perTick", 0, 25) == 0

def test_perTick_takes_everyone_when_the_last_minute_had_no_tick(kernel):
    assert kernel.call("stagger.perTick", 7, 0) == 7      # sleep fast-forward: a minute shorter than a tick
    assert kernel.call("stagger.perTick", 7, None) == 7   # the first minute after boot
```

(Use the existing kernel fixture name from `conftest.py` — read it; if the fixture is not named `kernel`, use its name and its `.call`/`.rt` members.)

- [ ] **Step 2: Run** `python -m pytest testing/tests/kernel/test_kernel_stagger.py -q` — FAIL.

- [ ] **Step 3: Write `NR_Kernel_Stagger.lua`** (one statement per line):

```lua
-- NR_Kernel_Stagger.lua -- the slow clock's stagger (Plan 10 ruling 2): which players run their minute work and
-- how many per tick. Pure: lists in, lists and numbers out.
local K = NutritionRevamp.kernel
K.stagger = {}

-- The pending queue from position head, kept in order for every username still online and never doubled, then
-- every online username not already queued, in roster order. Returns a new list.
function K.stagger.merge(pending, head, roster)
    local out = {}
    local queued = {}
    local online = {}
    for i = 1, #roster do
        online[roster[i]] = true
    end
    for i = head, #pending do
        local u = pending[i]
        if online[u] == true and queued[u] == nil then
            out[#out + 1] = u
            queued[u] = true
        end
    end
    for i = 1, #roster do
        local u = roster[i]
        if queued[u] == nil then
            out[#out + 1] = u
            queued[u] = true
        end
    end
    return out
end

-- Players to process per tick: the queue spread over the last minute's tick count, at least one; everyone when the
-- last minute had no tick (sleep fast-forward) or no count yet (the first minute).
function K.stagger.perTick(queued, ticksLastMinute)
    if queued <= 0 then
        return 0
    end
    if ticksLastMinute == nil or ticksLastMinute < 1 then
        return queued
    end
    return K.max(1, math.ceil(queued / ticksLastMinute))
end
```

- [ ] **Step 4: Run** the kernel test — PASS; `python -m pytest testing/tests/kernel/test_zz_coverage.py -q` — PASS.

- [ ] **Step 5: Write the failing shape tests** `test_players_shape.py`:

```python
from server_host import Host

def names(n):
    return ["p%02d" % i for i in range(n)]

def test_no_player_starves_when_players_outnumber_ticks():
    h = Host()
    ps = [h.player(u) for u in names(30)]
    h.online(*ps)
    for minute in range(4):
        h.T.age = 100.0 + minute / 60
        h.minute()
        h.tick(25)                                # 25 ticks per game minute: a 1-hour day at 10 Hz
    last = [h.record(u).lastSeen for u in names(30)]
    assert min(last) >= 100.0 + 2 / 60           # every player worked within the last two minutes

def test_under_sleep_fast_forward_everyone_still_works():
    h = Host()
    ps = [h.player(u) for u in names(5)]
    h.online(*ps)
    h.T.age = 100.0
    h.minute(); h.tick(1)
    for k in range(1, 21):                        # 20 game minutes per tick
        h.T.age = 100.0 + k / 60
        h.minute()
        if k % 20 == 0:
            h.tick(1)
    h.minute(); h.tick(1)
    assert all(h.record(u).lastSeen >= 100.0 + 20 / 60 for u in names(5))

def test_a_respawn_inside_a_minute_never_marks_the_new_record_dead():
    h = Host()
    a, b = h.player("a"), h.player("b")
    h.online(a, b)
    h.minute(); h.tick(5)
    b.deadFlag = True
    h.minute()                                    # b queued with its dead body
    nb = h.player("b")
    h.fire("OnNewGame", nb, None)                 # the respawn before the drain reaches b
    h.online(a, nb)
    h.tick(5)
    assert h.record("b").dead is not True
    assert h.NR.server.players.online["b"] == nb

def test_a_reconnect_between_two_minutes_fires_first_sight_again():
    h = Host()
    seen = h.rt.eval("{}")
    h.NR.server.players.onFirstSight[len(h.NR.server.players.onFirstSight) + 1] = \
        h.rt.eval("function(t) return function(u) t[#t + 1] = u end end")(seen)
    a = h.player("a")
    h.online(a); h.minute(); h.tick(2)
    a2 = h.player("a")                            # a new IsoPlayer under the same username
    h.online(a2); h.minute(); h.tick(2)
    assert [seen[i] for i in range(1, len(seen) + 1)].count("a") == 2

def test_a_first_character_counts_no_respawn_and_a_death_counts_one():
    h = Host()
    a = h.player("a")
    h.fire("OnNewGame", a, None)
    assert h.record("a").resets == 0
    h.online(a); h.minute(); h.tick(2)
    a.deadFlag = True
    h.minute(); h.tick(2)                         # the minute marks the record dead
    h.fire("OnNewGame", h.player("a"), None)
    assert h.record("a").resets == 1
```

- [ ] **Step 6: Run** `python -m pytest testing/tests/kernel/test_players_shape.py -q` — FAIL on the starvation, respawn, reconnect and reset tests. Quote it.

- [ ] **Step 7: Implement in `NR_Server_Players.lua`.** The state table gains `ticks = 0, ticksLastMinute = nil, perTick = 1`. Replace `P.minute`, `P.drain` and the `OnNewGame` listener with:

```lua
function P.minute()
    if getOnlinePlayers == nil then return end
    local ok, list = pcall(getOnlinePlayers)
    if not ok or list == nil then return end
    local okS, n = NR.call(list, "size")
    if not okS or type(n) ~= "number" then return end
    P.minutes = P.minutes + 1
    local roster = {}
    local seen = {}
    local i = 0
    while i < n do
        local okG, player = NR.call(list, "get", i)
        if okG and player ~= nil then
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                seen[username] = player
                if P.online[username] ~= player then          -- first sight, or a new IsoPlayer (a reconnect)
                    local r = NR.server.store.get(username, NR.worldAge() or 0)
                    NR.log.say(2, "players: first sight of " .. tostring(username))
                    P.online[username] = player
                    fire(P.onFirstSight, username, player, r)
                end
                roster[#roster + 1] = username
            end
        end
        i = i + 1
    end
    for username, _ in pairs(P.online) do
        if seen[username] == nil then
            NR.log.say(2, "players: " .. tostring(username) .. " left")
            fire(P.onDeparture, username, nil, nil)
        end
    end
    P.online = seen
    P.queue = K.stagger.merge(P.queue, P.queueHead, roster)   -- ruling 2: pending kept, never doubled
    P.queueHead = 1
    P.ticksLastMinute = P.ticks
    P.ticks = 0
    P.perTick = K.stagger.perTick(#P.queue, P.ticksLastMinute)
end

-- The stagger: perTick queued players per tick (ruling 2). It rides OnTick with an O(1) early-out because the
-- work is the slow minute's, spread over the minute's ticks -- a departure from the OnTick rule (#1071, #1080),
-- which is about per-tick simulation (ruling 3).
function P.drain()
    P.ticks = P.ticks + 1
    local budget = P.perTick
    while budget > 0 do
        local username = P.queue[P.queueHead]
        if username == nil then return end
        P.queueHead = P.queueHead + 1
        local player = P.online[username]                     -- the current object: a respawned body never runs
        if player ~= nil then
            P.drained = P.drained + 1
            P.work(username, player)
        end
        budget = budget - 1
    end
end
```

(add `local K = NR.kernel` at the top), and the `OnNewGame` listener body becomes:

```lua
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                P.online[username] = player                           -- ruling 4: the new object, before any work
                local r = NR.server.store.reset(username, NR.worldAge() or 0)
                if r ~= nil then fire(P.onFirstSight, username, player, r) end
            end
```

Update the file header comment (the stagger sentence) to ruling 2's wording.

- [ ] **Step 8: Implement `S.reset`'s count** in `NR_Server_Store.lua`:

```lua
    local respawn = old ~= nil and old.dead == true              -- ruling 5: a death, not a first character
    r.resets = (old and old.resets or 0) + (respawn and 1 or 0)
```

and fix the comment above `S.reset` to say so.

- [ ] **Step 9: Delete the dead poll branch** in `NR_Server_Options.lua`: remove `lastMinute`, `pollFromPlayers` and the `if NR.server.players ~= nil ...` branch, keeping only the `EveryOneMinute` registration of `pollDirect`; rewrite the comment above it to say the options poll rides `EveryOneMinute` directly.

- [ ] **Step 10: Run** the shape tests (PASS), `python -m pytest testing/tests/kernel -q` (green), the existing `test_server_reconcile_shape.py` (green — its `first_sight` helper still works), the `mod/` gates, the full `claims_check` (list shifts).
- [ ] **Step 11: Commit** `Slow clock: the stagger keeps its queue and sizes its share from the last minute's ticks; a respawn and a reconnect are new objects; resets count deaths; the dead options branch removed`.

---

### Task 3: Takeover resilience and the per-tick trim — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Fast.lua` (`FAST.adopt` 427-439, the handler's strike 456-470, `FAST.disable` 501-505, `applyMode` 511-514, `onDeparture` 527-532, `body` 219-246, `hoist`, `onMinute`)
- Create: `testing/tests/kernel/test_fast_failover_shape.py`
- Modify: `testing/tests/kernel/test_kernel_fast.py`

**Interfaces:**
- Consumes: `server_host.Host`.
- Produces: `FAST.STRIKES = 3`; `FAST.REARM = { 5, 15, 60 }`; `FAST.rearm = { attempt = 0, offMinutes = 0 }`; `FAST.hoistFails[username]`; `FAST.stampSlow(h)`.

- [ ] **Step 1: Read** `NR_Server_Fast.lua` whole; read how `test_kernel_fast.py` drives `K.fast.step`; read the hoist for the trait handles (`h.T`, `h.traitGet`) and the perk handle.

- [ ] **Step 2: Write the failing tests.** In `test_kernel_fast.py` (the kernel no longer reads the six dropped inputs):

```python
def test_the_dropped_inputs_do_not_move_the_step(kernel):
    a, b = kernel.call("fast.input"), kernel.call("fast.input")
    for t in (a, b):
        t.M, t.D, t.sd = 1, 24, 1
    b.highThirst, b.lowThirst, b.heartyAppetite, b.lightEater = True, True, True, True
    b.foodEaten, b.thermoFluids = 3, 2.5
    oa, ob, c = kernel.call("fast.output"), kernel.call("fast.output"), kernel.call("fast.defaults")
    kernel.call("fast.step", a, oa, c); kernel.call("fast.step", b, ob, c)
    for k in ("hunger", "thirst", "fatigue", "stress", "endurance", "idleness", "morale"):
        assert oa[k] == ob[k], k
```

`test_fast_failover_shape.py` — the Host needs `Hook.CalculateStats` stand-ins; pass `extra_env`:

```python
from server_host import Host

HOOK = r"""
NR_T.hookAdds, NR_T.hookRemoves = 0, 0
Hook = { CalculateStats = { Add = function(fn) NR_T.hookAdds = NR_T.hookAdds + 1; NR_T.hook = fn end,
                            Remove = function(fn) NR_T.hookRemoves = NR_T.hookRemoves + 1; NR_T.hook = nil end } }
"""

def host():
    h = Host(extra_env=HOOK)
    return h

def test_one_hoist_failure_does_not_disable_the_takeover():
    h = host()
    F = h.NR.server.fast
    assert F.registered
    bad = h.rt.eval("{ getUsername = function(s) return 'x' end }")   # hoist raises on the missing members
    F.adopt("x", bad)
    assert F.registered and F.stats.disabledAt is None

def test_three_hoist_failures_disable_and_the_slow_clock_rearms():
    h = host()
    F = h.NR.server.fast
    bad = h.rt.eval("{ getUsername = function(s) return 'x' end }")
    for _ in range(3):
        F.adopt("x", bad)
    assert not F.registered and F.stats.disabledAt is not None
    for _ in range(5):
        h.minute()
    assert F.registered and F.stats.disabledAt is None
    assert any("re-armed" in s for s in h.printed())

def test_after_the_last_rearm_it_stays_off_and_says_so():
    h = host()
    F = h.NR.server.fast
    bad = h.rt.eval("{ getUsername = function(s) return 'x' end }")
    for wait in (5, 15, 60):
        for _ in range(3):
            F.adopt("x", bad)
        for _ in range(wait):
            h.minute()
    for _ in range(3):
        F.adopt("x", bad)
    for _ in range(200):
        h.minute()
    assert not F.registered
    assert any("stays off until restart" in s for s in h.printed())

def test_departure_forgets_the_per_player_stats():
    h = host()
    F = h.NR.server.fast
    p = h.player("a")
    h.online(p); h.minute(); h.tick(2)
    assert F.stats.perPlayer["a"] is not None
    h.online(); h.minute()
    assert F.stats.perPlayer["a"] is None and F.hoistFails["a"] is None
```

(If `FAST.adopt` hoists through a stand-in that the PLAYER table satisfies, the `bad` table missing members makes `hoist` raise; confirm by reading `hoist` and, if it tolerates missing members by design — "an optional term is disabled" — make `bad` raise inside `getUsername`'s sibling the hoist requires, e.g. `getStats = function(s) error('x') end`, and say so in the report.)

- [ ] **Step 3: Run** both files — FAIL. Quote.

- [ ] **Step 4: Implement.** Add near the top of the file's state:

```lua
FAST.STRIKES = 3                       -- ruling 6: a hoist or body failure counts; three in a row trip it
FAST.REARM = { 5, 15, 60 }             -- ruling 6: slow minutes before each re-arm attempt
FAST.rearm = { attempt = 0, offMinutes = 0 }
FAST.hoistFails = {}
```

`FAST.adopt`'s failure tail becomes:

```lua
    FAST.lastError = h
    local n = (FAST.hoistFails[username] or 0) + 1
    FAST.hoistFails[username] = n
    NR.log.say(1, "fast: hoist failed for " .. tostring(username) .. " (" .. tostring(n) .. "): " .. tostring(h))
    if n >= FAST.STRIKES then FAST.disable(username, "three hoist failures") end
    return nil
```

and on success `FAST.hoistFails[username] = nil`. The handler's strike line uses `FAST.STRIKES`. Add a server-scope minute listener (registered at file end beside the others, `Events.EveryOneMinute.Add(function() if NR.isServer() then FAST.rearmTick() end end)`):

```lua
function FAST.rearmTick()
    if FAST.stats.disabledAt == nil then return end
    local o = NR.server.options
    if o == nil or o.mode ~= 1 then return end
    local wait = FAST.REARM[FAST.rearm.attempt + 1]
    if wait == nil then
        if FAST.rearm.said ~= true then
            NR.log.say(1, "fast: the takeover stays off until restart (" .. FAST.stats.disabledAt .. ")")
            FAST.rearm.said = true
        end
        return
    end
    FAST.rearm.offMinutes = FAST.rearm.offMinutes + 1
    if FAST.rearm.offMinutes < wait then return end
    FAST.rearm.attempt = FAST.rearm.attempt + 1
    FAST.rearm.offMinutes = 0
    FAST.stats.disabledAt = nil
    FAST.hoistFails = {}
    for _, h in pairs(FAST.h) do h.fails = 0 end
    if FAST.install() then
        NR.log.say(1, "fast: takeover re-armed (attempt " .. tostring(FAST.rearm.attempt) .. ")")
    end
end
```

`onDeparture` adds `FAST.stats.perPlayer[username] = nil` and `FAST.hoistFails[username] = nil`. Fix the comment above `FAST.adopt` (the disable is server-wide and recovers) and above `applyMode`.

- [ ] **Step 5: The per-tick trim (ruling 7).** In `body`, delete the six assignments `inp.highThirst`, `inp.lowThirst`, `inp.heartyAppetite`, `inp.lightEater`, `inp.foodEaten`, `inp.thermoFluids`, and move `inp.needsLess`, `inp.needsMore`, `inp.hemophobic`, `inp.deaf`, `inp.insomniac`, `inp.nightOwl` and `inp.fitnessLevel` into a new function called from the end of `hoist` and from `onMinute`:

```lua
-- The slow-changing reads (Plan 10 ruling 7): stamped at the hoist and once a slow minute, never per tick.
function FAST.stampSlow(h)
    local inp, T, tg = h.inp, h.T, h.traitGet
    inp.needsLess = tg(h.traits, T.needsLess)
    inp.needsMore = tg(h.traits, T.needsMore)
    inp.hemophobic = tg(h.traits, T.hemophobic)
    inp.deaf = tg(h.traits, T.deaf)
    inp.insomniac = tg(h.traits, T.insomniac)
    inp.nightOwl = tg(h.traits, T.nightOwl)
    inp.fitnessLevel = h.getPerkLevel(h.p, h.fitnessPerk)
end
```

`onMinute` calls it inside a `pcall` (a raise there is logged, never fatal). Update the `@hoisted` line if a name it lists is no longer used in the region. Run `python tools/hotpath_lint.py mod` — 0.

- [ ] **Step 6: Run** both test files (PASS), `python -m pytest testing/tests/kernel -q`, the gates, the full `claims_check` (list shifts).
- [ ] **Step 7: Commit** `Takeover: three strikes for a hoist too, a re-arm after 5, 15 and 60 slow minutes, the departure leak closed, the per-tick body without its dead reads and with the slow reads on the slow clock`.

---

### Task 4: The bus — a guarded build, a request limit, the class push — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Bus.lua` (`B.sendMirror` 37-43, the `OnClientCommand` listener 45-58, `B.flushEffects`, `B.forgetEffects`)
- Modify: `mod/.../shared/NR_Kernel_View.lua` (append `K.view.pushSignature` after `K.view.classes`)
- Create: `testing/tests/kernel/test_bus_shape.py`; Modify: `testing/tests/kernel/test_kernel_view.py`

**Interfaces:**
- Produces: `K.view.pushSignature(energyState, dehydPct, caf, debtH) -> integer`; `B.REQUEST_GAP_MS = 5000`; `B.requests = { last = {}, stats = { answered = 0, denied = 0 } }`; `B.lastSig[username]`; `B.stats.buildFailed`.

- [ ] **Step 1: Write the failing tests.** `test_kernel_view.py`:

```python
def test_the_push_signature_moves_with_any_live_class(kernel):
    s0 = kernel.call("view.pushSignature", 1.0, 0.0, 0.0, 0.0)
    assert kernel.call("view.pushSignature", 1.0, 0.0, 0.0, 0.0) == s0
    for args in ((1.6, 0, 0, 0), (1.0, 5.0, 0, 0), (1.0, 0, 400.0, 0), (1.0, 0, 0, 30.0)):
        assert kernel.call("view.pushSignature", *args) != s0, args

def test_the_push_signature_reads_nil_as_zero(kernel):
    assert kernel.call("view.pushSignature", None, None, None, None) == kernel.call("view.pushSignature", 0, 0, 0, 0)
```

(Pick each moving argument from `K.view.ENERGY_AT`, `HYDRATION_AT`, `STIMULANT_AT`, `SLEEP_AT` so it crosses the first rung — read the tables and adjust the four tuples to values above their first threshold.)

`test_bus_shape.py`:

```python
from server_host import Host

SEND = r"""
NR_T.sent = {}
sendServerCommand = function(p, module, cmd, m) NR_T.sent[#NR_T.sent + 1] = cmd end
getTimestampMs = function() return NR_T.now end
NR_T.now = 1000000
"""

def test_a_mirror_build_that_raises_is_caught_and_counted():
    h = Host(extra_env=SEND)
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    h.K.mirror.build = h.rt.eval("function() error('corrupt') end")
    assert h.NR.server.bus.sendMirror(p, h.record("a")) is False
    assert h.NR.server.bus.stats.buildFailed == 1

def test_mirror_requests_inside_the_gap_are_denied():
    h = Host(extra_env=SEND)
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    n0 = len(h.T.sent)
    for _ in range(5):
        h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 1
    assert h.NR.server.bus.requests.stats.denied == 4
    h.T.now = h.T.now + 5001
    h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 2

def test_a_class_change_marks_the_player_for_a_push():
    h = Host(extra_env=SEND)
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    B = h.NR.server.bus
    h.T.now += 60001
    h.minute(); h.tick(2)                       # settle: the signature recorded
    n0 = B.effects.stats.pushes
    h.record("a").body.energyState = 1.8        # a fasting climb across the energy rungs
    h.T.now += 60001
    h.minute(); h.tick(2)
    assert B.effects.stats.pushes == n0 + 1
```

(If `record.body` is nil in the stand-in world after two minutes, seed it the way `test_metabolism_shape.py` does — read it — and say so in the report.)

- [ ] **Step 2: Run** — FAIL. Quote.

- [ ] **Step 3: Implement.** `NR_Kernel_View.lua`, appended after `K.view.classes`:

```lua
-- The live class rungs as one integer (Plan 10 ruling 8): a change in any of energy, hydration, stimulant or sleep
-- moves it. Deficiency and excess move with the nutrient epoch, which already marks a push. nil reads 0.
function K.view.pushSignature(energyState, dehydPct, caf, debtH)
    local e = K.view.rung(energyState or 0, K.view.ENERGY_AT)
    local hy = K.view.rung(dehydPct or 0, K.view.HYDRATION_AT)
    local s = K.view.rung(caf or 0, K.view.STIMULANT_AT)
    local sl = K.view.rung(debtH or 0, K.view.SLEEP_AT)
    return e * 1000 + hy * 100 + s * 10 + sl
end
```

`NR_Server_Bus.lua`: the state gains `REQUEST_GAP_MS = 5000`, `requests = { last = {}, stats = { answered = 0, denied = 0 } }`, `lastSig = {}`, `stats = { buildFailed = 0 }`; `B.sendMirror` becomes

```lua
function B.sendMirror(player, record)
    if player == nil or record == nil then return false end
    if sendServerCommand == nil then return false end
    local okB, m = pcall(K.mirror.build, record, B.meta(), NR.data and NR.data.records and NR.data.records.ORDER)
    if not okB then
        B.stats.buildFailed = B.stats.buildFailed + 1
        NR.log.say(2, "bus: mirror build failed for " .. tostring(record.username) .. ": " .. tostring(m))
        return false
    end
    local ok = pcall(sendServerCommand, player, B.module, "mirror", m)
    if not ok then NR.log.say(2, "bus: sendServerCommand failed for " .. tostring(record.username)) end
    return ok
end
```

The request branch, before the store read:

```lua
            local now = nowMs()
            local last = B.requests.last[username]
            if now ~= nil and last ~= nil and now >= last and now - last < B.REQUEST_GAP_MS then
                B.requests.stats.denied = B.requests.stats.denied + 1
                return
            end
            B.requests.last[username] = now
            B.requests.stats.answered = B.requests.stats.answered + 1
```

(move `nowMs` above the listener). In `B.flushEffects`, before the dirty test:

```lua
    local body, fl, ac = record.body, record.fluids, record.acute
    local sig = K.view.pushSignature(body and body.energyState, fl and fl.dehydPct, ac and ac.caf, ac and ac.debtH)
    if B.lastSig[username] ~= nil and B.lastSig[username] ~= sig then B.effects.dirty[username] = true end
    B.lastSig[username] = sig
```

`B.forgetEffects` also clears `B.lastSig[username]` and `B.requests.last[username]`. Add two limitation strings: the request gap, and the class push riding the next slow minute and the push gap.

- [ ] **Step 4: Run** the tests (PASS), the kernel suite (coverage green), gates, full `claims_check`.
- [ ] **Step 5: Commit** `Bus: the mirror build inside the guard, one mirror request answered per player per 5 s, a push on any live class change`.

---

### Task 5: Training — one hit per event, no ranged hits — Sonnet implementer, Sonnet reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Training.lua:146-157` (`hitStep`), the comment at `:170-173`
- Modify: `testing/tests/kernel/test_training_shape.py`

- [ ] **Step 1: Read** `test_training_shape.py` to see how it builds an owner and weapon and reads the banked volume.
- [ ] **Step 2: Write the failing tests** (in that file's style):

```python
def test_a_three_target_swing_banks_three_hits_not_nine(h):
    owner = h.owner("a", lastHitCount=3)          # the file's own owner builder; add the field if absent
    w = h.weapon(weight=1.0, ranged=False)
    for _ in range(3):                            # the server fires the event once per target
        h.NR.server.training.onHit(owner, w, None, 1.0, 1)
    assert h.banked("a", "hits") == 3

def test_a_ranged_hit_banks_nothing(h):
    owner = h.owner("a", lastHitCount=1)
    gun = h.weapon(weight=3.0, ranged=True)
    h.NR.server.training.onHit(owner, gun, None, 1.0, 1)
    assert h.banked("a", "hits") == 0
```

(`h.owner`, `h.weapon`, `h.banked` are this file's helpers — read their real names; extend the weapon stand-in with `isRanged`. If the file counts volume rather than hits, assert on `TRN.stats.hits` and on the body's strength volume, stating the expected multiple of `K.training.S_HIT`.)
- [ ] **Step 3: Run** — FAIL.
- [ ] **Step 4: Implement:**

```lua
local function hitStep(owner, weapon)
    local body = bodyOf(username(owner))
    if body == nil then return end
    local okR, ranged = NR.call(weapon, "isRanged")
    if okR and ranged == true then return end             -- vanilla grants Strength xp for melee only
    local okW, w = NR.call(weapon, "getWeight")
    local class = "moderate"
    if okW and finite(w) and w > TRN.HEAVY_WEAPON then class = "high" end
    K.training.event(body, K.training.S_HIT, class, 1)     -- the server fires once per target (WeaponHit.process)
    TRN.stats.hits = TRN.stats.hits + 1
end
```

and rewrite the `TRN.onHit` comment: the event fires once per target on the server, so each event is one hit.
- [ ] **Step 5: Run** (PASS), gates, full `claims_check`.
- [ ] **Step 6: Commit** `Training: one hit per weapon-hit event, ranged hits never bank`.

---

### Task 6: Overlay as nutrients only — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Nutrients.lua` (the fluids block around `:430-455`)
- Modify: `mod/.../shared/Translate/EN/Sandbox.json:4`, `mod/NutritionRevamp/README.md` (the mode paragraphs, lines 26-40), `mod/NutritionRevamp/COMPATIBILITY.md` (the StatsAPI and Stat Tweaks Lib rows and any row naming Overlay as a remedy)
- Modify: `testing/tests/kernel/test_nutrients_shape.py`

- [ ] **Step 1: Read** `NR_Server_Nutrients.lua:400-500` (the fluids minute: `autoDrop`, `dehydPct`, `viewPct`, `thirstTarget`) and `test_nutrients_shape.py`'s setup.
- [ ] **Step 2: Write the failing test:**

```python
def test_while_vanilla_owns_thirst_the_dehydration_terms_read_zero(h):
    h.NR.server.fast.registered = False             # Overlay, or the failover tripped
    rec = h.drive_minutes("a", 120, water_intake=0) # the file's helper: two hours with nothing drunk
    f = rec.fluids
    assert f.dehydPct == 0 and f.viewPct == 0 and f.thirstTarget is None

def test_under_the_takeover_the_terms_are_computed(h):
    h.NR.server.fast.registered = True
    rec = h.drive_minutes("a", 120, water_intake=0)
    assert rec.fluids.dehydPct > 0
```

(`drive_minutes` stands for this file's existing way of running N slow minutes for a player — use it by its real name.)
- [ ] **Step 3: Run** — FAIL.
- [ ] **Step 4: Implement** at the fluids block, after the pool's own minute and before `f.dehydPct` is computed:

```lua
    local owned = NR.server.fast ~= nil and NR.server.fast.registered == true
    if not owned then
        -- Plan 10 ruling 10: vanilla owns thirst (Overlay, or the takeover failed over); the mod's pool cannot see
        -- vanilla's auto-drink, so its dehydration terms read zero rather than drift against a thirst that is fine.
        f.dehydPct = 0
        f.viewPct = 0
        f.thirstTarget = nil
        f.autoDrop = 0
    else
        -- the existing dehydPct, viewPct and thirstTarget lines, unchanged
    end
```

(move the existing three computations into the `else`; keep everything after them as is). Add a limitation string: "while the takeover is not registered (Overlay or the failover) the dehydration terms read zero; vanilla's thirst is the only thirst".
- [ ] **Step 5: The words.** Sandbox tooltip `Sandbox_NR_Mode_tooltip`: "Takeover: the mod replaces the vanilla stat update on the server through the CalculateStats hook, deriving hunger, thirst and fatigue from its own model. Overlay: the vanilla stat update runs untouched and owns hunger, thirst, fatigue and endurance; the mod tracks nutrients, body composition and their effects, with its dehydration effects off. Choose Overlay only beside a mod that claims the same hook." (keep the existing final sentence if it says something else true; read it). README: replace every sentence saying Overlay writes after vanilla with the same meaning in operator prose; add that the takeover falls back to vanilla for everyone after repeated errors and re-arms after 5, 15 and 60 game minutes. COMPATIBILITY: the StatsAPI and Stat Tweaks Lib rows' remedy reads "Overlay (vanilla owns the stats; the mod tracks nutrients and their effects)".
- [ ] **Step 6: Run** the tests (PASS), `python -m pytest testing/tests/test_mod_shipped_docs.py -q`, gates, full `claims_check`.
- [ ] **Step 7: Commit** `Overlay: vanilla owns the stats and the dehydration terms read zero; the tooltip, README and compatibility table say so`.

---

### Task 7: Micronutrients scale with the instance's calories — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../shared/NR_Kernel_Vector.lua:102-112` (`K.vector.meat`), `mod/.../server/NR_Server_Intake.lua:386-390,468-480`
- Modify: `testing/tests/kernel/test_kernel_vector.py`, `testing/tests/kernel/test_intake_shape.py`

**Interfaces:**
- Produces: `K.vector.instanceScale(tableKcal, fullKcal, rawHunger, baseHunger) -> number`; `K.vector.scaled(vec, scale) -> vector` (a new vector).

- [ ] **Step 1: The jar read.** `cd /c/Users/Angus/pz-b42` (read `WORKSPACE.md` first; read-only): `./pz.sh methods zombie.inventory.types.Food | grep -i calor` and `./pz.sh dump zombie.inventory.types.Food <the method a partial eat calls to scale the item, e.g. multiplyFoodValues>` — establish whether a partial eat lowers the stored calories. Record the answer with its line in the report. If it does, the full-size calories are `b.cal * b.instBase / b.rawBefore` (the instance's own ratio; both hungers read before the eat; guard `rawBefore ~= 0`); if it does not, they are `b.cal`.
- [ ] **Step 2: Write the failing tests.** Kernel:

```python
def test_instance_scale_prefers_calories(kernel):
    assert kernel.call("vector.instanceScale", 159.03, 1749.33, -1.0, -0.15) == pytest.approx(1749.33 / 159.03)

def test_instance_scale_falls_back_to_hunger(kernel):
    assert kernel.call("vector.instanceScale", 0, 500, -0.3, -0.15) == pytest.approx(2.0)
    assert kernel.call("vector.instanceScale", 100, None, -0.3, -0.15) == pytest.approx(2.0)
    assert kernel.call("vector.instanceScale", 100, 0, 0, 0) == 1

def test_scaled_multiplies_every_key(kernel):
    v = kernel.call("vector.new"); v.calories, v.iron = 100, 2
    s = kernel.call("vector.scaled", v, 3)
    assert s.calories == 300 and s.iron == 6 and v.calories == 100
```

Shape (`test_intake_shape.py`, in its own fish-like case — a food whose instance calories are 11× the table's and whose base hunger is 6.67× the script's, the review's LargemouthBass numbers): after the eat, `landed.iron / landed.calories == table.iron / table.calories` within 1e-6. (Build the item with the file's own food stand-in; read it.)
- [ ] **Step 3: Run** — FAIL.
- [ ] **Step 4: Implement** in the kernel (replacing `K.vector.meat`, whose only caller is Intake — confirm with `grep -rn 'vector.meat' mod testing`):

```lua
-- The instance scale (Plan 10 ruling 11): the instance's full-size calories over the table's, so the micronutrients
-- follow the same scale as the macros Eat delivers (a caught fish's macros scale with its weight); the hunger ratio
-- is the fallback when either calorie figure is absent or zero.
function K.vector.instanceScale(tableKcal, fullKcal, rawHunger, baseHunger)
    if tableKcal ~= nil and tableKcal > 0 and fullKcal ~= nil and fullKcal > 0 then
        return fullKcal / tableKcal
    end
    if baseHunger ~= nil and baseHunger ~= 0 and rawHunger ~= nil then
        return rawHunger / baseHunger
    end
    return 1
end

function K.vector.scaled(vec, scale)
    local out = K.vector.new()
    K.vector.add(out, vec, scale)
    return out
end
```

In Intake, read `b.calFull` per Step 1's answer at the before-snapshot and replace the `K.vector.meat(...)` call with `vec = K.vector.scaled(vec, K.vector.instanceScale(vec.calories, b.calFull, b.instBase, b.scriptHunger))`; update the comment above it.
- [ ] **Step 5: Run** (PASS), the kernel suite (coverage), gates, full `claims_check`.
- [ ] **Step 6: Commit** `Intake: micronutrients scale with the instance's calories, the macros' own scale; the hunger ratio as the fallback`.

---

### Task 8: The item pass — energy through recipes, the check's blind spots, header churn — Opus implementer, Opus reviewer

**Files:**
- Modify: `data/food-nutrient-map/manufactured-2.csv:20` (`Base.HotdogPack`), `data/food-nutrient-map/meat-fish-egg-dairy.csv:40` (`Base.Hotdog`)
- Modify: `tools/food_nutrients.py` (`check_generated` 1904-1945; the `main --check` path; the Lua header writer)
- Create: `tools/tests/test_recipe_energy.py`; Modify: `tools/tests/test_food_nutrients.py`
- Regenerate: `data/food-nutrients.json`, `data/food-nutrients.csv`, `mod/.../shared/NR_Data_Nutrients.lua`, `NR_Data_Infer.lua`, `mod/.../scripts/NR_ItemPass_Food.txt`

- [ ] **Step 1: Write the recipe-energy test** (fails today on HotdogPack). Read `data/recipes.json` (`meta` plus the recipe list — find its key) and `data/food-nutrients.json` (per-item kcal). The test:

```python
import json, math, os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOW = {
    # recipe name: reason (every entry reasoned; the slice-3 review found Get6Muffins inherits food, so it is not here)
}

def load(name):
    with open(os.path.join(REPO, "data", name), encoding="utf-8") as fh:
        return json.load(fh)

def food_kcal():
    """{pz_id: per-item kcal} for every mapped food (food-nutrients.json items with a per_item vector)."""
    out = {}
    for row in load("food-nutrients.json")["items"]:
        per = row.get("per_item") or {}
        if row.get("kind") == "food" and isinstance(per.get("calories"), (int, float)):
            out[row["pz_id"]] = per["calories"]
    return out

def lines(entries):
    """[(full_type, count)] for item lines naming exactly one type, or None when any line is a tag, a category,
    a choice of types or a non-item line (such a recipe is out of this guard's reach)."""
    out = []
    for e in entries:
        if e["kind"] != "item" or len(e["types"]) != 1 or e["tags"] or e["categories"]:
            return None
        out.append((e["types"][0], e["amount"]))
    return out

def food_recipes(kcal):
    for rec in load("recipes.json")["recipes"]:
        ins, outs = lines(rec["inputs"]), lines(rec["outputs"])
        if not ins or not outs:
            continue
        if not all(t in kcal for t, _ in ins + outs):
            continue                                    # every line a mapped food, or the recipe is skipped
        flags = set(f for e in rec["inputs"] for f in e["flags"])
        yield rec["name"], flags, ins, outs

def test_no_food_recipe_creates_energy():
    kcal = food_kcal()
    bad = []
    for name, flags, ins, outs in food_recipes(kcal):
        if "InheritFood" in flags or name in ALLOW:
            continue
        e_in = sum(kcal[t] * c for t, c in ins)
        e_out = sum(kcal[t] * c for t, c in outs)
        if e_in > 0 and e_out > e_in * 1.25:
            bad.append((name, round(e_in, 1), round(e_out, 1)))
    assert bad == []
```

(The schemas are `data/recipes.json` `recipes[*].inputs/outputs[*]` with `kind`, `types`, `tags`, `categories`, `amount`, `flags`, and `data/food-nutrients.json` `items[*]` with `pz_id`, `kind`, `per_item.calories`; confirm `per_item` carries `calories` before running.) Run it — expected FAIL listing `OpenHotdogPack` (about 270 in, about 603 out). Quote it. Any other recipe it lists is investigated: a mapping error is fixed in this task, a real vanilla design (a recipe meant to add energy) goes into `ALLOW` with its reason.
- [ ] **Step 2: Fix the mappings.** `Base.HotdogPack`: the portion becomes four wieners, `208.0` g of the same FDC frankfurter (the row's mass cell and its note: "four wieners at 52 g, the pack the OpenHotdogPack recipe opens"). `Base.Hotdog`: map to the SR Legacy "hot dog, plain" sandwich (search `tools/.fdc/` or `data/fdc-extract.json` for a description containing "hotdog, plain" or "hot dog, plain"; if the extract lacks it, run `python tools/food_nutrients.py --build-extract` with the FDC zips under `tools/.fdc/` and record it) at one sandwich's portion, the note saying the MakeHotDog recipe consumes a bun and a wiener. Run `python tools/food_nutrients.py --check-map` (0), `--write`, then the test — PASS. Report the new kcal of the two items.
- [ ] **Step 3: The check's blind spots — failing tests first** in `test_food_nutrients.py`: (a) an edited value in a copy of `data/iodine-db-r4.csv` makes `check_generated(...)` (pointed at temp copies) report the extract stale; (b) a stale JSON AND a stale Lua both appear in one `check_generated` result (today it returns after the JSON); (c) `main(["--check"])` on a map that makes the emitter refuse returns a non-zero code and prints the refusal, not a traceback. Run — FAIL.
- [ ] **Step 4: Implement.** A `check_side_tables(extract_path, iodine_csv, phytate_csv, insect_csv) -> [(path, message)]` that re-reads the three CSVs through the SAME functions `--build-extract` uses (find them: grep `iodine-db-r4`, `phytate-literature`, `insect-literature` in the tool) and compares each section of the extract key by key; `check_generated` calls it first and appends its findings; drop the early `return stale` so every stale file is listed; `main`'s `--check` catches `EmitRefused` (and `BuildRefused`), prints `food_nutrients: <message>` and exits 1.
- [ ] **Step 5: Header churn.** The Lua header writer stops printing `meta.generated` (the `(generated YYYY-MM-DD; …)` clause) into `NR_Data_Nutrients.lua` and `NR_Data_Infer.lua`; the JSON keeps its date. `--write`, then `--check` in sync. Grep the register for a `repo:mod/.../NR_Data_Nutrients.lua:2` or `NR_Data_Infer.lua:2` pointer quoting the date and list it for the controller.
- [ ] **Step 6: Run** `python -m pytest tools/tests/test_food_nutrients.py tools/tests/test_recipe_energy.py -q`, `python -m pytest testing/tests/kernel -q` (the data shape tests), `python tools/food_nutrients.py --check`, the `mod/` gates, the full `claims_check`.
- [ ] **Step 7: Commit** `Item pass: a hot-dog pack opens into what it holds, a hot dog carries its bun, a recipe-energy guard; the check sees the side tables and every stale file; the Lua headers undated`.

---

### Task 11: Dead code — Sonnet implementer, Sonnet reviewer

**Files:**
- Modify: `mod/.../shared/NR_Kernel_Nutrients.lua:98-107`, `mod/.../shared/Translate/EN/Moodles.json`, `mod/.../shared/Translate/EN/UI.json`
- Modify or delete: `mod/.../client/NR_Client_Effects.lua`, `testing/tests/kernel/test_client_effects_shape.py`

- [ ] **Step 1:** In `K.nutrients.requirement`, delete the `elseif scale == "perProteinG" then r = r * ctx.pDay` branch (no record declares that scale: `grep -n 'scale = ' mod/NutritionRevamp/common/media/lua/shared/NR_Data_Records.lua`). Delete `Moodles_NR_deficiency_lvl4` and `Moodles_NR_excess_lvl4` from `Moodles.json` and `UI_NR_Class_deficiency_4` and `UI_NR_Class_excess_4` from `UI.json` (the view caps those classes at three). Run `python -m pytest testing/tests/kernel -q` — green (coverage loses the deleted lines, not gains a miss).
- [ ] **Step 2:** `grep -n 'NR_Client_Effects' docs/reference/claims.tsv`. If no row points into the file: delete it and `test_client_effects_shape.py`. If any row does: keep the file and remove its `Events.*.Add` registrations so nothing listens, with a header line saying the aim and speed effects are unapplied and the listener is off; update its shape test to assert no listener is registered; list the rows for the controller.
- [ ] **Step 3:** gates, full `claims_check` (list shifts), `python tools/release_pack.py check mod/NutritionRevamp`.
- [ ] **Step 4: Commit** `Dead code: the unused per-protein scale, the unreachable level-4 class strings, the client effects listener`.

---

### Controller: the Wave B register re-anchor

- [ ] After Tasks 2–8 and 11 are complete, apply every reported `pointer-line` shift in one register commit (`Register: Wave B pointer re-anchors`), the full `claims_check` 0 before the commit.

---

### Task 9: The satiety dial — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../shared/NR_Kernel_Stomach.lua` (`K.stomach.empty` and its caller signature), `mod/.../server/NR_Server_Kinetics.lua` (pass the half-time), `mod/.../server/NR_Server_Options.lua` (read the option), `mod/NutritionRevamp/42.20.4/media/sandbox-options.txt`, `mod/.../shared/Translate/EN/Sandbox.json`
- Create: `testing/tests/kernel/test_satiety_default.py`; Modify: `testing/tests/kernel/test_kernel_stomach.py`

**Interfaces:**
- Produces: `K.stomach.empty(stomach, dtH, halfTimeH)` (nil `halfTimeH` reads `K.stomach.HALF_TIME_H`); `NR.server.options.satietyHalfTime`; sandbox option `NR.SatietyHalfTime`.

- [ ] **Step 1: The vanilla target, from the library.** Read `docs/facts/character-stats.md` for (a) vanilla's awake hunger rise per game hour at default settings (the `HungerIncrease` global and the multipliers it names, with their rows) and (b) the hunger value at which the first hunger moodle shows. Compute `H_vanilla = threshold / rate` game hours from a hunger of 0. Write both inputs, their row ids and `H_vanilla` in the report. If either number is not on the page with a settled row, read it from the jar (`ZomboidGlobals`, the moodle threshold in `Moodles`), name the method and line, and say the default rests on a jar reading.
- [ ] **Step 2: The mod's curve.** With `energyState = 1`, the takeover's hunger is `1 - fill` and a full stomach's fill decays as `2^(-t / T)` (read `K.stomach.emptyFraction` and `compositionScale` to confirm the exponent and the composition factor at a neutral meal — if the composition scale is not 1 for the seeded buffer, carry it). The first moodle is reached when `fill = 1 - threshold`, i.e. at `t = T · log2(1 / (1 - threshold))`. Setting `t = H_vanilla` gives `T* = H_vanilla / log2(1 / (1 - threshold))`, rounded to 0.25 h.
- [ ] **Step 3: Write the failing tests.** `test_kernel_stomach.py`: `K.stomach.empty(s, dt, 4.0)` empties less than `K.stomach.empty(s, dt, 2.0)` from equal seeds, and `empty(s, dt, nil)` equals `empty(s, dt, K.stomach.HALF_TIME_H)`. `test_satiety_default.py`:

```python
import re, os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
T_STAR = None   # Step 2's value, written here as a literal with its derivation in a comment

def test_the_default_satiety_is_the_vanilla_matched_half_time():
    txt = open(os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt"), encoding="utf-8").read()
    block = re.search(r"option NR\.SatietyHalfTime\s*\{(.*?)\}", txt, re.S).group(1)
    assert float(re.search(r"default\s*=\s*([0-9.]+)", block).group(1)) == T_STAR

THRESHOLD = None   # Step 1's first-moodle hunger value, as a literal
H_VANILLA = None   # Step 1's game hours from hunger 0 to that value, as a literal

def test_a_full_stomach_reaches_the_first_moodle_at_the_vanilla_hour(kernel):
    s = kernel.call("stomach.seedFull", kernel.call("stomach.new"))
    t, step = 0.0, 0.05
    while t < 48:
        kernel.call("stomach.empty", s, step, T_STAR)
        t += step
        if 1 - kernel.call("stomach.fill", s) >= THRESHOLD:
            break
    assert abs(t - H_VANILLA) <= 0.25
```

(`T_STAR`, `THRESHOLD` and `H_VANILLA` are written as literals from Steps 1–2 before the run; a seeded stomach's buffer is the seed's, so if `compositionScale` makes the seeded half-time differ from `T`, Step 2's derivation carries the factor and says so.) Run — FAIL (the dial does not exist).
- [ ] **Step 4: Implement.** `K.stomach.empty` takes `halfTimeH` and uses `halfTimeH or K.stomach.HALF_TIME_H` in its `emptyFraction` call (one statement per line); `HALF_TIME_H`'s comment says it is the fallback and the option is `NR.SatietyHalfTime`. `sandbox-options.txt` gains (with a block comment above naming ruling 13 and the derivation):

```
option NR.SatietyHalfTime
{
    type = double, min = 1.0, max = 8.0, default = T_STAR_LITERAL,
    page = NutritionRevamp, translation = NR_SatietyHalfTime,
}
```

`Sandbox.json` gains `Sandbox_NR_SatietyHalfTime` ("Satiety half-time (game hours)") and its `_tooltip` ("How long a meal keeps a character full: the stomach empties by half in this many game hours. Higher is more filling. The default matches vanilla's time from a full belly to the first hunger moodle."). `NR_Server_Options.lua` reads it beside the others into `O.satietyHalfTime` (the same `readLeaf` pattern, clamped to [1, 8], default `K.stomach.HALF_TIME_H`); Kinetics passes `NR.server.options and NR.server.options.satietyHalfTime` to `K.stomach.empty`.
- [ ] **Step 5: Run** the tests (PASS), the kernel suite, gates, full `claims_check`.
- [ ] **Step 6: Commit** `Satiety: the stomach's half-time is the NR.SatietyHalfTime dial, defaulting to vanilla's time to the first hunger moodle`.

---

### Task 10: Record pruning — Sonnet implementer, Sonnet reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Store.lua` (append `S.prune`; the `OnServerStarted` wiring), `NR_Server_Options.lua`, `sandbox-options.txt`, `Sandbox.json`
- Create: `testing/tests/kernel/test_store_prune_shape.py`

- [ ] **Step 1: Write the failing test:**

```python
from server_host import Host

def test_prune_deletes_only_offline_records_older_than_the_keep(h=None):
    h = Host()
    S = h.NR.server.store
    for name, seen in (("old", 10.0), ("recent", 900.0), ("online", 10.0)):
        r = S.get(name, seen); r.lastSeen = seen
    h.NR.server.players.online["online"] = h.player("online")
    h.T.age = 1000.0
    assert S.prune(1000.0, 30) == 1                 # 30 game days = 720 h: only "old" is older and offline
    assert h.record("old") is None and h.record("recent") is not None and h.record("online") is not None

def test_a_keep_of_zero_prunes_nothing():
    h = Host()
    S = h.NR.server.store
    r = S.get("old", 10.0); r.lastSeen = 10.0
    assert S.prune(100000.0, 0) == 0 and h.record("old") is not None
```

Run — FAIL.
- [ ] **Step 2: Implement:**

```lua
-- Record pruning (Plan 10 ruling 14): a record not online and unseen for longer than keepDays game days is deleted.
-- keepDays 0 keeps everything (the default). Returns the count deleted.
function S.prune(nowAgeH, keepDays)
    if keepDays == nil or keepDays <= 0 or nowAgeH == nil then return 0 end
    local t = S.attach()
    if t == nil then return 0 end
    local online = NR.server.players and NR.server.players.online or {}
    local cutoff = nowAgeH - keepDays * 24
    local doomed = {}
    for username, r in pairs(t) do
        if online[username] == nil and type(r) == "table" and NR.finite(r.lastSeen) and r.lastSeen < cutoff then
            doomed[#doomed + 1] = username
        end
    end
    for i = 1, #doomed do
        t[doomed[i]] = nil
        S.forget(doomed[i])
    end
    if #doomed > 0 then NR.log.say(1, "store: pruned " .. tostring(#doomed) .. " record(s) unseen for " .. tostring(keepDays) .. " game days") end
    return #doomed
end
```

Wire it at `OnServerStarted` (after the options read) and on `Events.EveryDays` if present, each calling `S.prune(NR.worldAge(), NR.server.options and NR.server.options.recordKeepDays or 0)`. The option `NR.RecordKeepDays` (`type = integer, min = 0, max = 3650, default = 0`), its two translation strings ("Keep records for (game days)", tooltip "Delete a player's nutrition record after this many game days without them online. 0 keeps every record."), and `O.recordKeepDays` read in Options.
- [ ] **Step 3: Run** (PASS), gates, full `claims_check`.
- [ ] **Step 4: Commit** `Store: records prune after NR.RecordKeepDays game days offline, off by default`.

---

### Task 12: Release 1.0.1 — Sonnet implementer, Sonnet reviewer

**Files:** `mod/.../shared/NR_Core.lua` (`version`), `mod/NutritionRevamp/42.20.4/mod.info` (`modversion`), `mod/NutritionRevamp/README.md`, `mod/NutritionRevamp/CHANGELOG.md`, `testing/tests/kernel/test_kernel_core.py` (its version literal), `testing/tests/test_mod_shipped_docs.py` (only if a new assertion is needed)

- [ ] **Step 1:** `version = "1.0.1"`, `modversion=1.0.1`, the core test's literal.
- [ ] **Step 2: CHANGELOG** gains `## 1.0.1 — <date of this commit>` above 1.0.0: one line each — players are no longer skipped when a server has more players than ticks in a game minute or during sleep; a respawn no longer leaves the new character's record marked dead; the stat takeover recovers after a fault instead of staying off until restart, and one player's setup fault no longer switches it off; a failed clock read no longer empties the stomach; Overlay now leaves hunger, thirst, fatigue and endurance to vanilla and turns the mod's dehydration effects off; combat strength training counts one hit per target and ignores firearms; the energy, thirst, caffeine and sleep moodles update when their level changes; micronutrients from caught fish scale with the fish; a pack of hot dogs opens into the energy it holds and a hot dog includes its bun; new options: satiety half-time and record keep days. In the 1.0.0 section, replace "a drink taken from the world's water is not captured" with "a drink from the world's water lands as water, up to the action's planned litres".
- [ ] **Step 3: README:** the two new options in the options list with defaults; the Overlay and takeover paragraphs as Task 6 left them (verify); the self-report example shows `v1.0.1`.
- [ ] **Step 4:** `python tools/release_pack.py check mod/NutritionRevamp` (0 ERROR), `python -m pytest testing/tests/test_mod_shipped_docs.py testing/tests/kernel/test_kernel_core.py -q`, gates, full `claims_check`.
- [ ] **Step 5: Commit** `Release 1.0.1: the version, the release notes and the operator guide`.

---

### Task 13: Live acceptance and the real cost — Opus implementer (live), Opus reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Bench.lua` (append; commit BEFORE the run)
- Create: `testing/profiles/x21-fixes.toml`, `testing/experiments/x211_fixes.py`; after the run `testing/artifacts/x211-<stamp>/fixes.json`

- [ ] **Step 1: The bench entries** (appended to `NR_Server_Bench.lua`; read `docs/reference/harness-commands.md` for `bench.global`'s exact contract — a dotted global path, called N times with no arguments):

```lua
-- Plan 10 Task 13: the real per-player cost. handler runs the takeover handler on the first online player;
-- minute runs that player's whole slow-minute work. Each call is one tick's or one minute's work for one player.
NR.server.bench = NR.server.bench or {}
local function firstOnline()
    local B = NR.server.bench
    if B.p ~= nil then return B.p, B.u end
    local P = NR.server.players
    for u, p in pairs(P and P.online or {}) do B.p, B.u = p, u; return p, u end
    return nil, nil
end
function NR.server.bench.handler()
    local p = firstOnline()
    if p ~= nil and NR.server.fast ~= nil then NR.server.fast.handler(p) end
end
function NR.server.bench.minute()
    local p, u = firstOnline()
    if p ~= nil then NR.server.players.work(u, p) end
end
```

Gates; commit `Bench: the takeover handler and the slow-minute work on a live player` BEFORE the run.
- [ ] **Step 2: The profile** `x21-fixes.toml`: `x20-release.toml`'s shape (fixture `two`, `clients = ["admin", "bob"]`, the STAGED 1.0.1 copy by path after `python tools/release_pack.py stage mod/NutritionRevamp --out release`), `[sandbox] Nutrition = false`, `DayLength = 1`, and `[sandbox.NR] Severity = 1.5` (the options-file load reading); verify rows: the server `NutritionRevamp.version` reads `"1.0.1"`.
- [ ] **Step 3: The driver** `x211_fixes.py` (copy `x201_release.py`'s session shape; every reading at a path; the server-log pattern excludes the probe names). Phases:
  - **A** the self-reports (`v1.0.1`, `hook=true`) and `NutritionRevamp.server.options.severity` on the server reads `1.5` (the options file in the version dir loads — X22's first half for the shipped shape).
  - **B the stagger under fast-forward:** read `NutritionRevamp.server.players.perTick`, `ticksLastMinute`, `drained`; set the time speed high with the harness's time command (read `harness-commands.md`; `settimespeed` is a WORLD change the scenario restores — restore it here too) for 60 s; every 10 s read both players' records' `lastSeen` and `kineticsAge` (`globalmoddata` reads); restore the speed. The reading: both players' ages advance in every window.
  - **C the respawn:** x192's driven respawn on `admin` (read `x192_persist_mod.py` for the exact sequence: `health.reduce`, `ISPostDeathUI` `onRespawn`, the creation presses, `accept`); then for three slow minutes read `admin`'s record `dead` (must read false) and `resets` (exactly one more than before).
  - **D the request limit:** on `client:bob`, call the client's mirror-request function twice within one second (`lua.call`; find the function in `NR_Client_Mirror.lua`); read the server's `NutritionRevamp.server.bus.requests.stats.denied` before and after (one more).
  - **E the class push:** write `admin`'s record `body.energyState` across the first energy rung (`globalmoddata.setpath`), wait one push gap plus two slow minutes, read the client's received mirror `body_energyState` on `client` (it arrived without a request).
  - **F the cost:** `bench.global NutritionRevamp.server.bench.handler 1000` and `bench.global NutritionRevamp.server.bench.minute 200` on the server; record the harness's elapsed figures and the per-call microseconds; record the server's tick rate over the same window.
  - Commit the profile and driver BEFORE the run (`Harness: the x21-fixes profile and the x211 driver`).
- [ ] **Step 4: Run** (`doctor` first; one session). Commit the artifact byte-identical, its `artifacts.md` row (appended), its `do-not-cite` rows, and the delta `task-13-claims-delta.tsv` (NOT committed): M rows per phase (n=1), with owners — the options load on `areas/packaging.md`, the stagger reading and the cost on `areas/testing-your-mod.md`, the respawn on `platform/server-lifecycle.md`, the request limit and the class push on `areas/mp-sync.md`; and status rows for the performance rows the review found mismeasured (`#2822`, `#2823`, `#2824` — read them): each narrowed to what it measured (the pure step; one player at a capped tick rate) with the x211 cost row named in its bound. Commit `x211: 1.0.1 on fixture two — the options load, the stagger under fast-forward, the respawn, the request limit, the class push, the per-player cost`.

---

### Task 14: The documentation delta and the process rules — Sonnet implementer, Opus reviewer

- [ ] **Pages** (each sentence tagged with the x211 rows the controller applied, or a C/inference row on the mod's own line per ruling T12-1 where it states what a mod can do): `docs/platform/lessons.md` gains a rule and its mechanism row — "Keep a per-player stagger's queue across the clock's ticks and size its per-tick share from the last minute's tick count: a queue rebuilt each minute and drained one player per tick skips every player past the minute's tick count, and under sleep fast-forward every player but the first" (resting on the x211 B row and the stagger kernel's line); `docs/areas/testing-your-mod.md` — a rule that a per-player clock is tested with more stand-in players than ticks per minute and under a minute shorter than a tick, and the cost reading; `docs/areas/mp-sync.md` — the request limit and the class push as what a mod can do; `docs/platform/server-lifecycle.md` — a respawn's new object and the queue (the x211 C row); `docs/areas/packaging.md` — the options file in the version dir loads (x211 A), settling X22's first half for that shape (CLAUDE.md § 4.3: its Open line rewritten, the experiments row marked); the skills quoting any touched `## Rules` line re-synced byte-identically.
- [ ] **CLAUDE.md § 6** gains three process rules (root files name pages, never claims): "A plan that touches `mod/` closes with a line-level Opus bug review of the plan's whole `mod/` diff, separate from the whole-pass review: the 2026-10-07 review found twelve adapter bugs nine per-task reviews had passed"; "A per-player clock, queue or cache gets a test with more stand-in players than its per-minute budget before it ships"; "A review finding is closed only by a test that reproduced it". § 3's pytest count.
- [ ] `page_lint` 0 on every touched page; `doc_lint` 0 if the wall map is touched; `claims_delta --dry-run` clean. Commit `Docs: the review fixes as measured (lessons, testing-your-mod, mp-sync, server-lifecycle, packaging; the skills; CLAUDE.md's process rules)`.

---

### Task 15: The close — controller

- [ ] The whole-pass review (Opus, read-only) against this plan's rulings and the review record, sentence by sentence; PLUS the line-level Opus bug review of `git diff <plan commit>~1..HEAD -- mod/` (Task 14's new rule, applied to this plan first); one consolidated fix wave and its re-review; every § 3 gate; CLAUDE.md § 3's count; the memory block in both scopes; `git push origin main`; the Rulings block and the § 7 list in the ledger; `Plan 10: complete`. The § 7 list names for Angus: the satiety default and its derivation; the re-arm schedule; the prune default (off); the cost per player and what it means for a 20- and a 40-player server; the Workshop upload of 1.0.1 (staged by the tool; `preview.png` still Angus's).

## Self-Review

- **Coverage of the review:** the stagger (2), the respawn dead-mark (2), the reconnect (2), resets (2), the dead options branch (2), the OnTick comment (2, ruling 3), the takeover kill switch and its hoist path (3), the perPlayer leak (3), the dead per-tick reads and the slow reads (3), the unguarded mirror build (4), the unthrottled request (4), the stale energy and sleep moodles (4), the Kinetics zero-age dump (1), the eight helper copies (1), the quadratic hits and ranged hits (5), Overlay's docs and its auto-drink drift (6), the fish micronutrients (7), the hot-dog pack and the hot dog (8), the check's side-table blind spot, early return, traceback and header churn (8), the dead per-protein branch and level-4 strings and the client listener (11), the false water sentence (12), the mismeasured performance rows and a real cost reading (13, 14), the options-file load (13), hunger feel (9), record growth (10), the process lessons (14). Deliberately left out with reasons: ruling 15.
- **Placeholders:** the two intentional derivations are procedures with their sources named — Task 9's `T_STAR` (computed in Steps 1–2 and written as a literal before Step 3's run) and Task 7's full-size calories (decided by the Step 1 jar read, both branches given). Test helpers named "the file's own" (Tasks 5, 6, 7) point at existing test files whose helper names the implementer reads; the assertion each test makes is spelled out.
- **Type consistency:** `NR.worldAge/finite/num/obj/flag` (Task 1) are used by Tasks 2, 3, 10; `server_host.Host` and its methods (Task 1) by Tasks 2, 3, 4, 10; `K.stagger.merge/perTick` (2); `FAST.STRIKES/REARM/rearm/hoistFails/stampSlow/rearmTick` (3); `K.view.pushSignature`, `B.REQUEST_GAP_MS`, `B.requests`, `B.lastSig`, `B.stats.buildFailed` (4, read by 13 D); `K.vector.instanceScale/scaled` (7); `K.stomach.empty(stomach, dtH, halfTimeH)`, `O.satietyHalfTime` (9); `S.prune`, `O.recordKeepDays` (10); `NR.server.bench.handler/minute` (13).
