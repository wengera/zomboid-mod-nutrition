# Plan 11b — The 1.0.1 Live Phase and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the 1.0.1 build of Plan 11a live — the mod's own budgeted queue against `budget15` at both spacings, the hybrid's holds, the store, the prune, the closed leak, a real hand craft through Task 17's wrapper and the PANIC moodle itself — release 1.0.1, and write every finding into the library.

**Architecture:** One harness commit first (a craft command and a moodle-level read), then live sessions on the staged copy under CLAUDE.md § 5, each driver committed before its boot and each artifact committed byte-identical with its register rows; the release changes only the version, the operator documents and the release tool's Lua arm; the documentation task mints the plan's readings through delta files the controller applies.

**Tech Stack:** the harness (`pzt`, PZTestKit, fixture `two`), the drivers under `testing/experiments/`, `tools/release_pack.py`, the claims register and its delta tools.

**Spec:** `docs/superpowers/specs/2026-10-07-plan-11-decisions.md` (the same sections Plan 11a argues from), and Plan 11a, `docs/superpowers/plans/2026-10-08-plan-11a-build.md`, whose Global Constraints and seventeen rulings hold here unchanged; this plan adds the live and release constraints below.

## Global Constraints

Everything in Plan 11a's Global Constraints and rulings holds, except its "No live boot" line. In addition:

- **This plan starts only after Plan 11a closes:** its ledger reads `Plan 11a: complete` and its close is pushed (Task 0).
- **Live (CLAUDE.md § 5):** one session at a time; `python testing/pzt doctor` before every boot; at least **12 GB** free, read and ledgered before the boot; a driver longer than about **15 minutes** of wall time is split into sessions, each with its own driver; the STAGED copy boots (`python tools/release_pack.py stage mod/NutritionRevamp --out release/<dir>`), never `mod/`; `Nutrition = false`; the harness commit lands before the driver commit, and the driver and profile are committed before the boot; a driver is never edited after its run; a falsified or unmeasured reading is written as such and never re-run to make a number prettier; the artifact commit carries its `artifacts.md` row, its `do-not-cite.csv` rows and the re-anchor of every `repo:docs/reference/artifacts.md:` pointer the row shifts; no live boot overlaps an offline edit under `mod/`; a stray `ProjectZomboid64.exe` predating a session is Angus's — never kill it; a driver's server-log pattern excludes its own probe names.
- **The build is 42.21** (Plan 11a ruling 17, Task R; decision memo item 8): the fixtures are provisioned on 42.21.0 and the sessions run on it; every artifact's reading guide names the build and revision the server log prints at its boot (`version=42.21.0 4a0e9546ec`) and the jar file's sha256 prefix read at its boot (`e1a69eb743` at Task R). A register row a task cites that Task R did not re-read is re-read on 42.21 before it is relied on (CLAUDE.md § 2).
- **Ghost arms are equal:** every ghost run, in every arm, runs the writer dry and its store step skipped (Plan 11a ruling 15, Task 19); the reading guide of every shoot-out artifact says so.
- **The version is 1.0.1** from Task 3 on: `NR_Core.lua` `version = "1.0.1"` and the version folder's `mod.info` (`42.20.4/` until Task 3 re-decides its name) `modversion=1.0.1` agree; before Task 3 the verify rows read `"1.0.0"`.
- **Deltas:** a task with a reading writes `.superpowers/sdd/2026-10-08-plan-11b-live-release/task-<N>-claims-delta.tsv` (provisional ids `T113<N>.<n>`: Task 2's are `T1132.n`, Task 4's `T1134.n`, Task 5's `T1135.n` — the form `claimslib.PROVISIONAL_ID_RX` accepts, `^T\d+\.\d+$`, in a block no Plan 11a id uses: 11a's are `T1101`–`T1120` and Task R's `T1199`) and dry-runs it with `python tools/claims_delta.py apply <delta> --pages <page> [<page> ...] --dry-run` (the delta file first: `--pages` takes every word after it); the controller applies it.
- **Owner cells** in every delta use the register's form, `<layer>/<page>.md#<anchor>` with no `docs/` prefix (`claimslib.OWNER_RX`), e.g. `platform/performance.md#costs`.
- **The artifact commit (every live task):** the driver copies the artifact byte-identical under `testing/artifacts/<run-id>/`; the implementer writes its `docs/reference/artifacts.md` row and `docs/reference/do-not-cite.csv` rows, stages the new artifact files only (`git add -- testing/artifacts/<run-id>/`), runs the full `PYTHONIOENCODING=utf-8 python tools/claims_check.py` and lists every `repo:docs/reference/artifacts.md:` pointer the row shifts (`#1254`, `#1504` and any the checker names); the controller writes those re-anchors into the register (implementers never edit it, CLAUDE.md § 6) and makes **one** pathspec commit of the artifact files, `artifacts.md`, `do-not-cite.csv` and `docs/reference/claims.tsv`, so the checker is never red between commits (CLAUDE.md § 6, Plan 10).
- **Models (CLAUDE.md § 6):** as Plan 11a.

## Rulings this plan takes

1. **The PANIC flicker is read, not inferred:** acceptance reads the PANIC moodle's level on the client every tick with the new `moodle.watch` command beside the floor's hold, and grades the floor by the moodle's transitions, not by the 1.26 margin. — Plan 11a's draft left the flicker inferred from #3400 and #2369. — Cost if wrong: none; the inference stays as the fallback reading if the command comes back unmeasured.
2. **Task 17's wrapper is checked live once:** one real hand craft of a recipe the generated table scales, through `craft.run`, read server-side. — The wrapper's seat (J3) is a desk read; a live craft settles it. — Cost if wrong: an unscaled craft ships, documented.
3. **A driver re-asserts a target it set:** where a driver sets a record field the Effects rebuild owns (`effects.panicTarget`, `effects.tempOffset`), it sets it again every poll and reads it back every game minute; a minute whose read-back is not the set value is not graded, and a session with fewer than ten graded minutes reads unmeasured. — `K.effects.compose` can rebuild those fields each minute. — Cost if wrong: a few minutes lost to the grade.

## File structure

| path | responsibility | task |
|---|---|---|
| `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua`, `server/PZTestKit_Server.lua` (append only), `docs/reference/harness-commands.md` (generated) | `craft.run`, `moodle.watch`, `moodle.level` | 1 |
| `testing/profiles/x25-shootout-{a,b,c}.toml`, `testing/experiments/x251{a,b,c}_shootout.py`, `testing/artifacts/x251*/`, `docs/reference/{artifacts.md,do-not-cite.csv}`, `docs/platform/performance.md` (the readings' sentences) | the live shoot-out | 2 |
| `NR_Core.lua`, `42.20.4/mod.info`, `README.md`, `CHANGELOG.md`, `COMPATIBILITY.md`, `tools/release_pack.py`, `tools/tests/test_release_pack.py`, `test_kernel_core.py`, `testing/tests/test_mod_shipped_docs.py` | release 1.0.1 | 3 |
| `testing/profiles/x25-accept{,-b}.toml`, `testing/experiments/x252{a,b}_accept.py`, `testing/experiments/TKX_NmsStub/42/mod.info`, `testing/artifacts/x252*/`, the readings' sentences on `docs/areas/{body-effects,mp-sync,packaging,eat-and-cook-hooks}.md`, `docs/platform/{server-lifecycle,performance}.md` | live acceptance | 4 |
| `docs/platform/{lessons,performance,lua-platform,server-lifecycle}.md`, `docs/areas/{new-nutrients,mp-sync,body-effects,eat-and-cook-hooks,ui-and-moodles,testing-your-mod,packaging,item-pass,open-questions}.md`, `docs/reference/{experiments,tools}.md`, the skills quoting a touched rule, `CLAUDE.md` | the documentation | 5 |
| the ledger, `CLAUDE.md`, the memory files | the close | 6 |

## Execution order

Strictly serial; every task after Task 0 starts when the one before it has its `Task N: complete` line: Task 0 (controller) → Task 1 (Opus; the harness commit) → Task 2 (Opus, live; three sessions) → Task 3 (Sonnet implementer, Opus reviewer; the release) → Task 4 (Opus, live; two sessions) → Task 5 (Opus; the documentation) → Task 6 (the close). The `mod/` tree is quiescent from Task 1 to the end of Task 4 apart from Task 3's own commit, which lands between two live tasks; no live boot overlaps it. The controller applies each task's delta in its own register commit after the task's review.

---

### Task 0: The gate — controller

- [ ] **Step 1:** Read `.superpowers/sdd/2026-10-08-plan-11a-build/progress.md`: its last lines must read `Plan 11a: complete`, and `git log origin/main -1` must be at or after its close commit. If either fails, stop: this plan does not start.
- [ ] **Step 2:** `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\scripts\sdd-workspace docs/superpowers/plans/2026-10-08-plan-11b-live-release.md`. The ledger `.superpowers/sdd/2026-10-08-plan-11b-live-release/progress.md` opens with the plan's name, the three rulings above, the build (42.21, Plan 11a ruling 17; read again now: the jar's sha256 prefix and the buildid in `appmanifest_108600.acf` — if either moved since Plan 11a's Task R, stop and ask Angus), Plan 11a Task R's list of tasks here to amend (each amendment written and ledgered before its task runs), the pytest count (`python -m pytest tools/tests testing/tests -q`, at Plan 11a's close count), the golden sha256 and the next register id.

---

### Task 1: The harness — a hand craft and the moodle level — Opus implementer, Opus reviewer

A harness change lands before the run that uses it, in its own commit (CLAUDE.md § 5's standing rule: the harness is improved when that makes a measurement better). Task 2's first session is its smoke test; Task 4 uses both commands.

**Files:**
- Modify: `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua` (append at the end only), `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua` (CRLF: edit with `newline=''`; append at the end only)
- Regenerate: `docs/reference/harness-commands.md` (`python tools/bus_inventory.py`); update `#2808`'s claim text and quote and `#1235`'s quote if the table's count line changes

**Interfaces:**
- Consumes: the client file's `C` (:10), `TK.register`, `TK.call`; the server file's `findPlayer(username)` (:25), `TK.side`; `ScriptManager.getCraftRecipe(String)` (`./pz.sh methods zombie.scripting.ScriptManager`), `ISHandcraftAction:new(character, craftRecipe, containers, isoObject, craftBench, manualInputs, items, recipeItem, variableInputRatio, eatPercentage)` (`media/lua/shared/Entity/TimedActions/ISHandcraftAction.lua:391`), `ItemContainer.getCountTypeRecurse(String)`, `Moodles.getMoodleLevel(MoodleType)` and `MoodleType.PANIC` (`./pz.sh dump zombie.scripting.objects.MoodleType '<clinit>'`: `putstatic MoodleType.PANIC`).
- Produces: the client commands `craft.run <recipeName> <outputFullType> | read` and `moodle.watch <MoodleType> <seconds> | read`; the server command `moodle.level <user> <MoodleType>`.

- [ ] **Step 1: Read** both files' ends, `findPlayer`, the client's `findOrSpawn` comment (:282-:292: a client-spawned item is invisible to the server, so a craft's inputs are spawned server-side with RCON `additem`, as `testing/experiments/s01_eat_matrix.py` does), and `ISHandcraftAction.lua` whole (`new`, `start`, `serverStart`, `complete`, `performRecipe`).
- [ ] **Step 2: The client commands**, appended to `PZTestKit_Client.lua`:

```lua
-- ---- Plan 11b Task 1: a hand craft through the vanilla timed action (X31; Plan 11a Task 17's live check) ---------
-- craft.run <recipeName> <outputFullType> queues ISHandcraftAction for the named craftRecipe over the local
-- inventory, as the crafting window does, with the logic choosing the inputs (manualInputs false): the server
-- completes it and runs performRecipe there (ISHandcraftAction:complete under isServer). The inputs must already be
-- in the inventory on both sides (spawn them server-side with RCON additem). craft.run read replies the queue time,
-- the output count before, and the output count now.
C.craft = nil

function C.countOf(fullType)
    local p = getPlayer()
    local _, inv = TK.call(p, "getInventory")
    local _, n = TK.call(inv, "getCountTypeRecurse", fullType)
    return n
end

-- @args <recipeName> <outputFullType> | read
-- @reply {ok, queued, recipe, output, before, maxTime [, reason]} | {ok, recipe, output, before, now, queuedAt, at} | string
-- @purpose Test-only: queues the vanilla hand-craft timed action for one craftRecipe over the local inventory (the server completes it); read replies the output's inventory count before and now.
TK.register("craft.run", function(argv)
    if argv[1] == "read" then
        local K = C.craft
        if K == nil then return { ok = false, reason = "not armed" } end
        return { ok = true, recipe = K.recipe, output = K.output, before = K.before, now = C.countOf(K.output),
                 queuedAt = K.t0, at = getTimestampMs() }
    end
    local name, output = argv[1], argv[2]
    if name == nil or output == nil then return "usage: craft.run <recipeName> <outputFullType> | read" end
    if getScriptManager == nil or ISHandcraftAction == nil or ISTimedActionQueue == nil or ArrayList == nil then
        return { ok = false, reason = "no getScriptManager/ISHandcraftAction/ISTimedActionQueue/ArrayList" }
    end
    local _, recipe = TK.call(getScriptManager(), "getCraftRecipe", name)
    if recipe == nil then return { ok = false, reason = "no craftRecipe " .. tostring(name) } end
    local p = getPlayer()
    local containers = ArrayList.new()
    containers:add(p:getInventory())
    local act = ISHandcraftAction:new(p, recipe, containers, nil, nil, false, nil, nil, 1, 0)
    C.craft = { recipe = name, output = output, before = C.countOf(output), t0 = getTimestampMs() }
    ISTimedActionQueue.add(act)
    return { ok = true, queued = true, recipe = name, output = output, before = C.craft.before, maxTime = act.maxTime }
end)

-- ---- Plan 11b Task 1: a moodle's level on the local player, every tick (ruling 1) --------------------------------
-- moodle.watch <MoodleType> <seconds> samples getMoodles():getMoodleLevel(MoodleType[<name>]) on every OnTick for
-- the window and records each change of level with the wall ms; read replies the samples count, the minimum, the
-- maximum, the transitions and the level now. A name MoodleType does not carry replies a reason.
C.mw = nil

function C.mwTick()
    local W = C.mw
    if W == nil or W.done then return end
    local p = getPlayer()
    if p == nil then return end
    local _, moodles = TK.call(p, "getMoodles")
    local _, lv = TK.call(moodles, "getMoodleLevel", W.type)
    local now = getTimestampMs()
    if type(lv) == "number" then
        W.samples = W.samples + 1
        if W.min == nil or lv < W.min then W.min = lv end
        if W.max == nil or lv > W.max then W.max = lv end
        if W.last ~= nil and lv ~= W.last then
            W.changes[#W.changes + 1] = { at = now, from = W.last, to = lv }
        end
        W.last = lv
    end
    if now - W.t0 >= W.ms then W.done = true end
end

if Events ~= nil and Events.OnTick ~= nil then Events.OnTick.Add(function() C.mwTick() end) end

-- @args <MoodleType> <seconds> | read
-- @reply {ok, armed, moodle, seconds} | {ok, moodle, done, samples, min, max, transitions, changes, level} | string
-- @purpose Test-only: samples one moodle's level on the local player every tick for a wall window and records each level change; read replies the range and the transitions.
TK.register("moodle.watch", function(argv)
    if argv[1] == "read" then
        local W = C.mw
        if W == nil then return { ok = false, reason = "not armed" } end
        return { ok = true, moodle = W.name, done = W.done, samples = W.samples, min = W.min, max = W.max,
                 transitions = #W.changes, changes = W.changes, level = W.last }
    end
    local name, secs = argv[1], tonumber(argv[2])
    if name == nil or secs == nil or secs <= 0 then return "usage: moodle.watch <MoodleType> <seconds> | read" end
    if MoodleType == nil or MoodleType[name] == nil then return { ok = false, reason = "no MoodleType." .. tostring(name) } end
    C.mw = { name = name, type = MoodleType[name], ms = secs * 1000, t0 = getTimestampMs(), samples = 0,
             changes = {}, done = false }
    return { ok = true, armed = true, moodle = name, seconds = secs }
end)
```

- [ ] **Step 3: The server command**, appended to `PZTestKit_Server.lua` (with its CRLF endings):

```lua
-- ---- Plan 11b Task 1: a moodle's level on a named player, read on the server ------------------------------------
-- @args <user> <MoodleType>
-- @reply {ok, side, user, moodle, level [, reason]} | string
-- @purpose Test-only: reads one moodle's level on a named online player server-side (getMoodles():getMoodleLevel), the server half beside the client's moodle.watch.
TK.register("moodle.level", function(argv)
    local user, name = argv[1], argv[2]
    if user == nil or name == nil then return "usage: moodle.level <user> <MoodleType>" end
    local p = findPlayer(user)
    if p == nil then return { ok = false, side = TK.side, user = user, reason = "no online player" } end
    if MoodleType == nil or MoodleType[name] == nil then
        return { ok = false, side = TK.side, user = user, reason = "no MoodleType." .. tostring(name) }
    end
    local _, moodles = TK.call(p, "getMoodles")
    local _, lv = TK.call(moodles, "getMoodleLevel", MoodleType[name])
    return { ok = true, side = TK.side, user = user, moodle = name, level = lv }
end)
```

- [ ] **Step 4: The checks.** `python tools/luabalance.py <the HEAD copies of both files>` then the working-tree copies (green); `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` (0: `#W.changes` is a Lua table); `python tools/bus_inventory.py` (three new rows), `python tools/bus_inventory.py --check` (in sync); the `#2808`/`#1235` update if the count line moved; `PYTHONIOENCODING=utf-8 python tools/claims_check.py` full (0).
- [ ] **Step 5: Commit** `Harness: craft.run queues a vanilla hand craft; moodle.watch and moodle.level read a moodle's level` -- the two harness files, the regenerated table and the register lines if they moved.

---

### Task 2: The live shoot-out of the mod's scheduler — Opus implementer (live), Opus reviewer

Starts after Task 1; the `mod/` tree is quiescent for the whole task. Its first session is the smoke test of Plan 11a Task 19's harness commit and of Task 1's.

**Files:**
- Create (committed before each boot): `testing/profiles/x25-shootout-a.toml`, `x25-shootout-b.toml`, `x25-shootout-c.toml`, `testing/experiments/x251a_shootout.py`, `x251b_shootout.py`, `x251c_shootout.py`
- Create (after each run): `testing/artifacts/x251a-<stamp>/`, `x251b-<stamp>/`, `x251c-<stamp>/` (byte-identical); rows in `docs/reference/artifacts.md` and `docs/reference/do-not-cite.csv`; the readings' tagged sentences on `docs/platform/performance.md`; `task-2-claims-delta.tsv` (workspace)

**Interfaces:**
- Consumes (Plan 11a Task 19 and this plan's harness): `ghost.load <N> mod feed`, `ghost.modq`, `ghost.stats`, `ghost.stop`, `tick.ring`, `perf.local`, `bench.global`, `action.latency`, `time.multiplier`, `foodtimer.set`, `lua.global`, the gclog profile key; `NutritionRevamp.server.players.{served,meanMs,budgetMs,runCap,ticksLast}`.

- [ ] **Step 1: Stage.** `python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x251` (the staged copy the profiles name by `path`; `release/` is gitignored); record the MANIFEST sha256 in the report.
- [ ] **Step 2: The profiles**, each `x24-shootout-a.toml`'s shape (fixture `two`, `clients = ["admin", "bob"]`, `run = { hold = 20 }`, `[server] gclog = true`, `[client] timeout = 180`, `[sandbox] Nutrition = false`), the `NutritionRevamp` mod by `path = "release/plan11-x251/NutritionRevamp/Contents/mods/NutritionRevamp"`, the verify rows reading `NutritionRevamp.version` on the server and both clients (`"value": "1.0.0"` — the release bump is Task 3) and `TK.H0.RING_MAX`; `x25-shootout-a` and `-c` set `DayLength = 1`, `x25-shootout-b` `DayLength = 1` too (its driver sets `time.multiplier 0.1674` for the 37-tick spacing, #3394: set the day length in the profile, never at run time, and use the multiplier for the spacing as H3 and H4 did). Each file's header comment names its run, its driver, the staged copy and Nutrition false.
- [ ] **Step 3: The drivers** — copy `testing/experiments/x244c_notice.py`'s session shape (its readings, its ring and perf handling, its idle arm, its A-B alternation, its grading helpers) into each new driver; the run prefix and profile constants name the driver's own file and profile (CLAUDE.md § 5). Every prediction is written in the driver before the run. Each session stays under about 15 minutes of wall time. **Both arms carry the same dry seams:** every ghost run, under `mod` and under `budget15`, runs the writer dry and skips the store step for ghost names (Plan 11a ruling 15: Task 19 wrapped `H0.work`, which every scheduler and the bench call); each driver reads `lua.global NutritionRevamp.server.store.file.stats.writes` at each arm's start and end and grades a rise above the two real players' own saves (at most one a real minute each) as a broken seam that voids the arm, and each artifact's reading guide states the seams. **The batching differs, and the guides say so:** `budget15` times its ghost runs in one batch a tick (`H0.budgetBody` inside one `H0.batch`), while the `mod` arm's ghosts run one at a time from the mod's own `P.runOne`, interleaved with the real players; Plan 11a Task 19 keeps one batch open across a drain's contiguous ghost runs (`H0.modRun`, `H0.modWrap`), so a `mod` tick pays one batch, or two when a real player's run or a one-shot task falls between its ghosts. Each `mod` artifact's reading guide states this as a possible small bias against `mod` (at most one extra swap and two clock reads per real player a tick) and the driver records, per arm, the batch count a minute event beside the ghost runs (`ghost.stats`' `runs` and `minuteEvents`, and the number of drains, `NutritionRevamp.server.players.served` against ticks), so a reader can size it.
  - **x251a (DayLength 1, N = 60):** idle (about 1020 frames), then `mod1`, `budget15_1`, `mod2`, `budget15_2`, `mod3`, `budget15_3`; a `mod` arm is `ghost.load 60 mod feed` → `ghost.modq on` → `ghost.stats reset` → about 1020 frames with `tick.ring` and `perf.local` → `ghost.stats` → `ghost.modq off` → `ghost.stop`; a `budget15` arm is `ghost.load 60 budget15 feed` and the same reads. Beside each arm read `NutritionRevamp.server.players.served`, `.meanMs`, `.budgetMs`, `.runCap` and `.ticksLast` at the arm's start and end.
  - **x251b (37 ticks a game minute):** `time.multiplier 0.1674` first (read back), then the same seven arms.
  - **x251c (DayLength 1):** (1) the **empty-check bench**: `time.multiplier 0.0001`, wait 3 s for the queue to empty, read `served` and `lua.global NutritionRevamp.server.players.ticks` (the tick count `P.minute` turns into `ticksLast`), `bench.global NutritionRevamp.server.players.tick 100000`, read `served` again (unchanged, or the bench is marked invalid), then restore the tick count it inflated by 100000 — `lua.setpath NutritionRevamp.server.players.ticks <the value read before the bench>` — and read it back, then restore the multiplier; the driver also drops the next two minute events' `ticksLast`, `budgetMs` and `runCap` from every reading (the bench's calls could still sit in `ticksPrev` if the restore misses a tick), and waits those two minute events before phase (2) arms anything; (2) the **own-action latency** on `admin`: for each of `idle`, `burst` (`ghost.load 60 burst feed`) and `mod` (`ghost.load 60 mod feed` + `ghost.modq on`), `foodtimer.set admin 0`, then `action.latency Base.Apple 3` on `client:admin` and poll `action.latency read` until done; (3) the **fast clock**: `settimespeed` 30 for one arm with `ghost.load 60 mod feed` + `ghost.modq on` (staleness and frame period; the scenario's speed restore after).
  - **The grading** (pre-registered in each driver): ruling 2's thresholds for each `mod` arm against the session's idle arm — p99 end-to-end add ≤ 20 ms, longest-window add ≤ 25 ms, no starved ghost-minute — and the total on the ghosts' batch-timed ms a minute event ≤ 1.1× the paired `budget15` arm's (rule #3499); the empty check ≤ 0.1 ms a frame from the bench's µs a call; the latency samples' medians and maxima per arm, compared burst against mod (no threshold: a reading); the fast-clock arm's maximum staleness in game minutes.
  - Commit the profiles and the three drivers BEFORE the first boot: `Harness: the x25 shoot-out profiles and the x251 drivers (the mod's scheduler against budget15 at both spacings; the empty check, own-action latency and a fast clock)`.
- [ ] **Step 4: Run each session.** Before each boot: `python testing/pzt doctor`; read free memory (`powershell -c "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"`), and boot only with at least 12 GB free (ledger the figure); one session at a time; a stray `ProjectZomboid64.exe` predating the session is Angus's — never kill it. Run `python testing/pzt run --profile x25-shootout-a` with the driver per `docs/platform/harness.md#procedure`, then b, then c. A host kill before any reading is not a run (rerun unchanged); a reading that comes back trivial or falsified is written as such and never re-run.
- [ ] **Step 5: Each artifact, committed by the controller** (the Global Constraints' artifact commit): the implementer leaves the artifact byte-identical under `testing/artifacts/<run-id>/` and staged (`git add -- testing/artifacts/<run-id>/`), its `artifacts.md` row written (run id · file · what it measured · its reading guide, which states every arm's populations, the seams, the batching difference, the empty-check tick restore, the drift caveat of #3483 and any deviation), its `do-not-cite.csv` rows written (the trivial and the raw keys), and the list of `repo:docs/reference/artifacts.md:` pointers the row shifts (the full checker names them); the controller adds those re-anchors to the register and makes the one commit of all four, `x251a: the mod's budgeted queue against budget15 at N = 60, DayLength 1` (and b, c likewise), one run per commit.
- [ ] **Step 6: The delta.** `task-2-claims-delta.tsv`: one `add` row per reading (provisional `T1132.n`, grade `M`, bound `n=1 run <run-id>: …`) with the artifact path pointer and an unrounded number at that path — the mod arms' p99 and max adds per draw, their starvation, their total over budget15's, the queue's `budgetMs` and `runCap` at N = 60 at each spacing, the empty check's µs a call, the latency medians per arm, the fast-clock staleness — owner cells `platform/performance.md#costs` and `platform/performance.md#measure` (the register's form), each with its sentence on `docs/platform/performance.md` tagged `[T1132.n]` — and a `status` row narrowing performance.md's Open items on the mod's own scheduler, the adaptive budget and the empty check (each `status` bound starting with the register's current bound byte for byte: CLAUDE.md § 6). A reviewer checks every do-not-cite key and its parents by hand (CLAUDE.md § 4.9).

---
### Task 3: Release 1.0.1 — Sonnet implementer, Opus reviewer

Starts after Task 2. The reviewer is Opus: this task changes the join-checksum hashing (Appendix F), which decides whether an update is a server event. The build is 42.21 (Plan 11a ruling 17), so the version folder's name (`42.20.4/` today, which 42.21 loads as its best folder at or below the build, Plan 11a Task R Step 11) and `versionMin` are re-decided first, by `docs/areas/packaging.md`'s rule, and the decision is ledgered; a renamed folder moves every path below that names `42.20.4/` (this task's Files, `test_mod_shipped_docs.py`, `release_pack`'s expectations, Task 4's `TKX_NmsStub` `versionMin`) in this task's commit, and the full `claims_check` lists the `repo:mod/NutritionRevamp/42.20.4/` pointers it shifts for the controller.

**Files:** `mod/.../shared/NR_Core.lua` (`version`), `mod/NutritionRevamp/42.20.4/mod.info` (`modversion`, `description`), `mod/NutritionRevamp/README.md`, `mod/NutritionRevamp/CHANGELOG.md`, `mod/NutritionRevamp/COMPATIBILITY.md`, `tools/release_pack.py` (`_hash_file`, the stage message), `tools/tests/test_release_pack.py`, `testing/tests/kernel/test_kernel_core.py` (its version literal), `testing/tests/test_mod_shipped_docs.py` (only where an assertion pins changed text)

- [ ] **Step 1: The release tool (test first).** In `tools/tests/test_release_pack.py` (its `mod` fixture, `put`, `CORE` and `rp`), the last line of `test_manifest_gate_hash` pins today's rule that a Lua file carries no gate hash; it becomes `assert "gate_sha256" not in rp.manifest(mod)["common/media/ui/NutritionRevamp/a.png"]` (a PNG stays ungated), and the file gains:

```python
def test_manifest_gate_hash_covers_lua(mod):
    lua = mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua"
    put(lua, CORE.replace("\n", "\r\n"))
    crlf = rp.manifest(mod)["common/media/lua/shared/NR_Core.lua"]
    put(lua, CORE)
    lf = rp.manifest(mod)["common/media/lua/shared/NR_Core.lua"]
    assert crlf["gate_sha256"] == lf["gate_sha256"]          # a CRLF-only change gates nothing (Appendix F)
    assert crlf["sha256"] != lf["sha256"]


def test_a_one_byte_lua_comment_change_is_a_server_event(mod):
    old = rp.manifest(mod)
    put(mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua", CORE + "-- x\n")
    assert rp.diff(old, rp.manifest(mod))["script_changed"] == ["common/media/lua/shared/NR_Core.lua"]


def test_the_cli_names_a_lua_change_a_server_event(mod, tmp_path, capsys):
    old_dir, new_dir = tmp_path / "old", tmp_path / "new"
    assert rp.main(["stage", str(mod), "--out", str(old_dir)]) == 0
    put(mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua", CORE + "-- x\n")
    capsys.readouterr()
    assert rp.main(["stage", str(mod), "--out", str(new_dir), "--previous",
                    str(old_dir / "NutritionRevamp" / "MANIFEST.json")]) == 0
    assert "SERVER EVENT: 1 script or Lua file(s) changed" in capsys.readouterr().out
```

  and `test_cli_check_and_stage`'s last line reads `assert "SERVER EVENT: 1 script or Lua file(s) changed" in capsys.readouterr().out` (`stage` writes `<out>/NutritionRevamp/MANIFEST.json` and `main` answers 0, as that test already relies on). Run `python -m pytest tools/tests/test_release_pack.py -q` — FAIL: the three new tests and `test_cli_check_and_stage`; the PNG line of `test_manifest_gate_hash` passes on the current tool and is a follow-up pin. Quote. In `_hash_file`: `if (rel.endswith(".txt") and "media/scripts/" in rel) or (rel.endswith(".lua") and "media/lua/" in rel):` (Appendix F: the Lua arm gates exactly like the script arm, #3374–#3378); the stage message becomes `"SERVER EVENT: %d script or Lua file(s) changed"`; the module docstring says so. Run — PASS.
- [ ] **Step 2: The version.** `version = "1.0.1"`, `modversion=1.0.1`, the core test's literal.
- [ ] **Step 3: CHANGELOG** gains `## 1.0.1 — <date of this commit>` above 1.0.0: "Every code release changes Lua files, so this release is a server event: update the server first, then clients." then one line each — hunger, thirst and fatigue are now written once a game minute by the mod after vanilla's rates are set to zero at server start (Managed mode), replacing the per-tick stat takeover; Overlay (Mode 2) leaves vanilla's rates and stats; the mode is read at start and a change needs a restart; other mods reading vanilla's rates read zero, and `NutritionRevamp.vanillaRate(key)` gives the saved values; hunger follows vanilla's own timing with a calorie deficit making a character hungrier, and a bulky meal sates a little more (`NR.SatietyBulk`, 0.25); players are no longer skipped when more players are online than there are ticks in a game minute or under a fast clock (the queue carries unserved players forward under a budget sized to the minute); a respawn no longer leaves the new character's record marked dead, and the respawn count counts respawns only; a failed clock read no longer empties the stomach or stamps a record at age 0; nutrition records now live in files under the server's Lua cache folder instead of global modData, which any client could request (the old table is migrated once and removed), and a player unseen for `NR.RecordKeepDays` real days (30) loses the record; combat strength training counts one hit per target and ignores firearms; the energy, thirst, caffeine and sleep moodles update when their level changes, and each player's updates are spread over the minute; micronutrients follow the calories an eat delivers (caught fish, fillets, crafted food); a pack of hot dogs opens into the energy it holds, a hot dog includes its bun, and recipes that would create energy scale their outputs on the server (a client's tooltip may still show the unscaled values); the food tooltip stops after ten errors in a row and survives a re-entrant render; a warning is logged at server start when Nutrition Makes Sense is also loaded. The operator notes from Plan 10's refactor: a minute step that raises logs `minute: <step> failed for <user>` and is counted; a third-party `P.onMinute` listener now runs after the pipeline. In the 1.0.0 section, replace "a drink taken from the world's water is not captured" with "a drink from the world's water lands as water, up to the action's planned litres".
- [ ] **Step 4: README.** The options table: `NR.Mode` "1 (Managed) — Managed: vanilla's hunger, thirst and fatigue rates are set to zero at server start and the mod writes those stats once a game minute. Overlay: vanilla's rates and stats stand; the mod tracks nutrients and writes only its effects. Read once at server start; a change needs a restart.", plus `NR.RecordKeepDays` (30, 0 to 3650) and `NR.SatietyBulk` (0.25, 0.25 to 0.5); the sentence "The server re-reads the options every in-game minute…" gains "except `NR.Mode`, which is read at start". The "Takeover and overlay" section becomes "Managed and Overlay" with the restart-only mode, the writer outage note ("with the rates at zero a stopped writer stops hunger rather than falling back to vanilla"), the zero rates other mods read and `NutritionRevamp.vanillaRate`. A new section "Where the records live": the folder `Lua/NutritionRevamp/<server name>/` under the server's cache directory, one pair of slot files a player and an index, the one-time migration from global modData, pruning, and "after a hard kill the world rolls back to its last save while the record files keep the latest minute's state"; that a pruned player's two files are emptied, not deleted (Lua cannot delete a file); and that the folder is keyed by the server name, so a world wiped under the same name finds the old files and every returning player's record (its respawn count included) carries over — delete the folder by hand for a fresh start. The self-report example lines show `v1.0.1`, `mode=managed`, `rates=zeroed` and `limitations=` the writer's count. "Updates and the join checksum" takes Appendix F's text verbatim (the spec, "What the README's update procedure should say"). A line in the compatibility pointer that Nutrition Makes Sense draws a boot warning.
- [ ] **Step 5: COMPATIBILITY.md.** The release line reads 1.0.1; the QualityCooking row's "under takeover its stat writes are discarded" becomes "its hunger and fatigue adds are scaled by the rates the mod zeroes (#2564), so they add nothing in Managed mode; its endurance add stands"; the "Nutrition Tweaker Enhanced and nine endurance tweaks" and "hunger and thirst tweaks that only edit `ZomboidGlobals`" rows become "a tweak to vanilla's hunger, thirst or fatigue rates is saved at start and then set to zero in Managed mode, so it has no effect there (the mod's model sets those stats); endurance tweaks stand"; the "eat and drink action replacers" row is unchanged; the four neighbour rows from Plan 11a Task 1 stay.
- [ ] **Step 6: mod.info's description** drops "Followed as rate tunings: Nutrition Tweaker Enhanced, endurance and ZomboidGlobals tweaks" and "Redundant: ApocalipseBR Nutrition Sync Fix (disable its sync module)", adds "Hunger, thirst and fatigue rate tweaks have no effect in the default Managed mode." and "Every update that changes a script or Lua file is a server event", and keeps the incompatible list.
- [ ] **Step 7: Run** `python tools/release_pack.py check mod/NutritionRevamp` (0 ERROR), `python -m pytest tools/tests/test_release_pack.py testing/tests/test_mod_shipped_docs.py testing/tests/kernel/test_kernel_core.py -q`, the `mod/` gates, the full `claims_check` (list shifts). Re-stage: `python tools/release_pack.py stage mod/NutritionRevamp --out release --previous release/plan11-x251/NutritionRevamp/MANIFEST.json` (the copy Task 2 staged) and paste the diff (it must print `SERVER EVENT`).
- [ ] **Step 8: Commit** `Release 1.0.1: the version, the release notes, the operator guide and the compatibility table; the release tool hashes Lua files for the join checksum` -- the touched files.

---
### Task 4: Live acceptance of 1.0.1 — Opus implementer (live), Opus reviewer

Starts after Task 3; the `mod/` tree is quiescent for the whole task.

**Files:**
- Create (committed before each boot): `testing/profiles/x25-accept.toml`, `testing/profiles/x25-accept-b.toml`, `testing/experiments/x252a_accept.py`, `testing/experiments/x252b_accept.py`, `testing/experiments/TKX_NmsStub/42/mod.info` (an empty stand-in whose only content is `name=TKX NMS stub`, `id=NutritionMakesSense`, `versionMin=42.20.4`, so the server's activated-mods list carries Nutrition Makes Sense's id without loading its code, which is all rights reserved and is never copied)
- Create (after each run): `testing/artifacts/x252a-<stamp>/`, `x252b-<stamp>/`; their `artifacts.md` and `do-not-cite.csv` rows; the readings' tagged sentences on their owner pages (Step 5); `task-4-claims-delta.tsv`

- [ ] **Step 1: The profiles.** Both stage `python tools/release_pack.py stage mod/NutritionRevamp --out release` and name `release/NutritionRevamp/Contents/mods/NutritionRevamp`; fixture `two`, both clients, `Nutrition = false`, `DayLength = 1`, `[server] SleepAllowed = true, SleepNeeded = true` (x151s: a sleep reading needs both); verify rows read `NutritionRevamp.version` `"1.0.1"` on the server and both clients. `x25-accept-b` adds `[sandbox.NR] Mode = 2` and a second `[[mods]]` `id = "NutritionMakesSense"`, `path = "testing/experiments/TKX_NmsStub"` after NutritionRevamp (an experiment mod installed only through this profile, CLAUDE.md § 5; run `python tools/mod_lint.py testing/experiments/TKX_NmsStub` first, since `pzt run` lints every `path=` folder and stops on an ERROR).
- [ ] **Step 2: The drivers** (copy `x201_release.py`'s session shape and `x192_persist_mod.py`'s restart sequence; every reading at a path; the server-log patterns exclude the probe names, CLAUDE.md § 5). **x252a (Managed):**
  - **A, the self-reports:** both lines read `v1.0.1`, `mode=managed`, `rates=zeroed`; `lua.call NutritionRevamp.vanillaRate HungerIncrease` reads 9.6e-6 (42.20.4's value, #0470; the value Plan 11a Task R re-read on 42.21 if it moved); `lua.global ZomboidGlobals.HungerIncrease` reads 0; the server log holds the zeroing line and no Nutrition Makes Sense warning.
  - **B, the hybrid holds:** 30 s of `stats.all admin` reads every 0.2 s: HUNGER, THIRST and FATIGUE change only at the writer's ticks (between two consecutive writes every read equals the last write). The floor holds use ruling 3: the driver sets `lua.setpath NutritionRevamp.server.store.records.admin.effects.panicTarget 10` again at every 0.2 s poll and reads it back once a game minute with `lua.global NutritionRevamp.server.store.records.admin.effects.panicTarget`; a minute whose read-back is not 10 is not graded (`K.effects.compose` can rebuild the field), and fewer than ten graded minutes reads unmeasured. **Each hold is sized to its moodle watch:** the hold starts with the first set, and is *established* at the first graded read-back; only then does the driver arm `moodle.watch PANIC 60` on admin's client, and it keeps re-asserting the target at every 0.2 s poll until `moodle.watch read` answers `done` and for one poll after, so the whole 60 s watch window (about 96 game minutes at DayLength 1, at 0.625 s a game minute) lies inside the hold. The driver reads the client's wall clock (`time.snapshot`'s `wall` on `client:admin`) when the hold is established and again when it ends, and counts a transition only when its `at` lies between the two; a change outside them is dropped and named, and a watch that answered `done` after the hold ended is not graded. Over every graded minute of the hold PANIC never reads under 10 − 1.2556 − 0.01, and the watch reads 0 transitions inside the hold (10 sits 4 above the threshold 6). Then the same sized hold at `panicTarget 6.6` — within 1.26 of the threshold — with its own `moodle.watch PANIC 60`: the transitions it counts inside the hold are the flicker #3400 predicts, recorded as a reading (no threshold), with `moodle.level admin PANIC` read on the server at each graded minute beside it. TEMPERATURE: `…effects.tempOffset 0.5`, re-set and read back the same way, and TEMPERATURE's pre-write reads sit within 0.05 °C of the target after the first ten graded writes.
  - **C, the auto-drink fold:** `fluid.fill admin Base.WaterBottle Water 1.0`, lower admin's water pool by `lua.setpath NutritionRevamp.server.store.records.admin.fluids.water <value>` (the pool's key in `K.fluids.new`; read it there first) until `fluids.thirstTarget` exceeds 0.1; then over 10 game minutes: `NutritionRevamp.server.writer.stats.sips` rises, the pool rises at the minute after each sip, and the bottle's litres fall by no more than the pool deficit plus one sip (no re-drink spiral).
  - **D, an eat between writes:** `eat.action Base.Apple` on admin's client; HUNGER drops at once; the next write's HUNGER sits at or below the pre-eat value less 0.8 × the apple's relief (the satiety scalar kept the eat).
  - **E, the scheduler:** `ghost.load 20 mod feed` + `ghost.modq on` for 3 game minutes: `ghost.stats` starvation 0; `NutritionRevamp.server.players.served` rises by at least 22 a minute event; then off and stop.
  - **F, the store and the restart:** `lua.global NutritionRevamp.server.store.file.stats.writes` > 0; `lua.global NutritionRevamp.server.store.file.gen.admin` reads a number of at least 1 (a `lua.call` answers a table only by its key count, so the slot's generation is read as a scalar); the restart sequence from `x192_persist_mod.py`; after it, admin's record keeps its `body.fm` within 0.01 kg and `store.stats.created` stays 0 for admin.
  - **G, the prune:** read the server's wall ms `T_q` (`time.snapshot`'s `wall` on the server; read its unit off the reply — the prune takes ms) and `NutritionRevamp.server.players.served`, then `quit` on bob. Wait at least two game minutes, polling every 0.5 s, until bob's departure has run in the queue: `lua.global NutritionRevamp.server.players.online.bob` reads nil (the minute event saw him go and queued his `store:bob` flush), `served` has risen past its value at the quit, and `lua.global NutritionRevamp.server.store.file.lastWrite.bob` reads at least `T_q` (the departure task's slot write; 60 s without all three is written unmeasured, with the reads). Only then `lua.call NutritionRevamp.server.store.prune <T_q + 31 × 86400000> 30` answers 1, and `…store.records.bob`, `…store.file.index.bob` and `…store.file.lastWrite.bob` read nil. Wait one more minute event (`served` rises again) and read the three once more: still nil — no queued write refilled the slot. Then bob rejoins and his record's `resets` reads 0 and `firstSeen` the rejoin's age.
  - **I, a hand craft through the wrapper (ruling 2):** read `lua.global NutritionRevamp.data.recipes.factor.<recipe>` for the first recipe Plan 11a Task 16 left in the generated table (its report names them) and its input and output types from `data/recipes.json`; spawn the inputs server-side (`server.rcon('additem "admin" "<input>" <n>')`, as `s01_eat_matrix.py` does); read `lua.global NutritionRevamp.server.craft.stats.scaled`; on admin's client `craft.run <recipe> <output>` and poll `craft.run read` every 0.5 s until `now > before` (60 s: unmeasured); then `stats.scaled` has risen by 1 and `item.get admin <output>` reads calories equal to the output's re-based script calories × the factor within 0.01 (read the script value with `item.script <output>` on the server first). A craft that does not complete is written unmeasured with the client's reply.
  - **H, the leak is closed:** `lua.call ModData.exists NutritionRevamp.players` on the server reads false; on bob's client `event.watch OnReceiveGlobalModData`, `lua.call ModData.request NutritionRevamp.players`, 5 s, `event.watch OnReceiveGlobalModData read` — 0 firings.
  **x252b (Overlay, the Nutrition Makes Sense id beside it):** the server log carries exactly one `Nutrition Makes Sense is loaded` warning; `NutritionRevamp.server.writer.zeroed` reads false and `ZomboidGlobals.HungerIncrease` 9.6e-6; admin's HUNGER rises between two server reads 60 game minutes apart while no writer HUNGER set happens (`writer.stats.writes` rises, but the HUNGER read is vanilla's). Nothing else is graded under Nutrition Makes Sense.
  - Commit the profiles and drivers BEFORE the first boot: `Harness: the x25 acceptance profiles and the x252 drivers`.
- [ ] **Step 3: Run** each session under Task 2 Step 4's rules (doctor, 12 GB free and ledgered, one at a time, under about 15 minutes each).
- [ ] **Step 4: Each artifact, committed by the controller** from the implementer's staged files — the artifact, its `artifacts.md` row, its `do-not-cite.csv` rows and the register re-anchor, all in one commit (the Global Constraints' artifact commit; Task 2 Step 5's shape): `x252a: 1.0.1 on fixture two — the zeroed rates, the writer's holds, the sip fold, an eat between writes, the queue, the store, the restart, the prune, a hand craft and the closed leak` and `x252b: Overlay and the Nutrition Makes Sense warning`.
- [ ] **Step 5: The delta** `task-4-claims-delta.tsv`: one `add` row per phase reading (provisional `T1134.n`, grade `M`, bound `n=1 run <run-id>: …`), each with its tagged sentence on its owner page, the owner cells in the register's form — the zeroing, the holds and the PANIC moodle reading `areas/body-effects.md#takeover` (the section the hybrid replaces; Task 5 renames it if it rewrites the heading, with a `retarget` row), the store, restart, prune and leak `areas/mp-sync.md#global-moddata` and `platform/server-lifecycle.md#player-store`, the queue `platform/performance.md#scheduling`, the warning `areas/packaging.md#resident-stack`, the craft `areas/eat-and-cook-hooks.md#cook-seat`; `python tools/page_lint.py` on those pages (0); `status` rows for the rows the release supersedes (the takeover's hold rows and #3417's leak as "closed in 1.0.1 by moving the store", with `successor` where a new row replaces a claim — CLAUDE.md § 4.4).

---
### Task 5: The documentation and the durable findings — Opus implementer, Opus reviewer

Starts after Task 4. Angus's standing preference: every finding goes in the library.

**Files:** `docs/reference/tools.md` (the two new tools), `docs/platform/lessons.md`, `docs/platform/performance.md`, `docs/platform/lua-platform.md`, `docs/platform/server-lifecycle.md`, `docs/areas/new-nutrients.md`, `docs/areas/mp-sync.md`, `docs/areas/body-effects.md`, `docs/areas/eat-and-cook-hooks.md`, `docs/areas/ui-and-moodles.md`, `docs/areas/testing-your-mod.md`, `docs/areas/packaging.md`, `docs/areas/item-pass.md`, `docs/areas/open-questions.md`, `docs/reference/experiments.md`, the skills under `.claude/skills/` that quote a touched `## Rules` line, `task-5-claims-delta.tsv`

- [ ] **Step 1: Collect.** Every Plan 11 delta the controller has applied (Plan 11a's `task-R`, `task-1`, `-2`, `-16`; this plan's `task-2`, `-4`; each landed with its own sentences, so this task adds the prose around them, never a second sentence for the same row), and every finding in the task reports not yet minted: from Plan 11a, the heal-once guard list and its accepted window (Task 12), the sip fold, the dry and skip seams and ghost arms that carry them alike (Tasks 14, 19), the store's slot design, the migration guard, the emptied slots, the world-wipe carry-over and the hard-kill caveat (Task 11), the recipe classes and recipe_scan's accounting (Task 16), the craft seat (Task 17 and this plan's live craft), the tooltip guards (Task 18), and the for-in coverage measurement (the Global Constraints); from this plan, the PANIC moodle reading (Task 4 B). A finding that rests only on the mod's own code is a `C/inference` row on the mod's line (ruling T12-1).
- [ ] **Step 2: The pages.**
  - `docs/platform/performance.md`: around the sentences Task 2 wrote, what the mod's own scheduler reading means (x251a/b: the adds, starvation, the total over budget15 and the batching caveat, the adaptive budget's `budgetMs` and `runCap` at N = 60), the empty check's cost, the own-action latency, the fast-clock reading; `## Open` loses the items x251 answered and keeps the rest (CLAUDE.md § 4.3); `## Procedure` step 5 says a mod's own queue is measured with `ghost.load <N> mod` and `ghost.modq on`.
  - `docs/platform/lessons.md` `## Rules` gains, each with its mechanism row in the delta (a `rule` row per CLAUDE.md § 6, its pointer copied from a row it rests on): "Save a `ZomboidGlobals` value before zeroing it and publish the saved value, because every other mod's Lua reads the zero (#2564)"; "Heal a record once, before the step, and guard only the fields a later step reads in the same minute, because a heal after the step cannot catch an input NaN and a full heal after it costs a quarter of the minute (Appendix J)"; "Keep per-player state a server must protect in server-local files written from the player's own scheduled slot, because global modData is requestable by any client and its save serialises every table on the main loop (#3417, #3467)"; "Fold an auto-drink sip into the next THIRST write when the rates are zeroed, because vanilla drinks twice the target at every write otherwise (#3382)"; "Never read a mod sandbox option in a client's `OnGameBoot` (#3381)". The snapshot rule "Keep every durable mod value in character, item or global modData" gets a `status` row narrowing it to "… or a server-local file" with this plan's store rows named.
  - `docs/platform/lua-platform.md` and `docs/platform/server-lifecycle.md`: the file route (J2), the boot-side and `OnGameBoot` facts, the respawn order through the queue.
  - `docs/areas/body-effects.md`: the hybrid (the mode, the writer, what it reproduces, approximates and loses — Appendix A § 5 as updated by x252), the satiety scalar, the endurance rmod fold; the takeover's sentences move to a "Before 1.0.1" note or are superseded with successors.
  - `docs/areas/mp-sync.md` and `docs/areas/new-nutrients.md`: the store's home, the migration, the pruning, the request leak closed.
  - `docs/areas/eat-and-cook-hooks.md`: the craft seat and its #1074 limit; the laddered relief at the eat.
  - `docs/areas/item-pass.md`: Plan 11a Task 16 wrote the recipe classes and the mapping fixes with their rows; this task adds only what the live craft (Task 4 I) showed, and any item-pass finding Plan 11a Task R listed for the 42.21 foods.
  - `docs/reference/tools.md` (its reference profile under `page_lint`): a section for `tools/jar_recheck.py` (Plan 11a Task R: what it reads, its statuses, that the verdict stays a reader's) and one for `tools/recipe_conservation.py` (Plan 11a Task 16: the classes, recipe_scan's accounting, `--write`/`--check`), each sentence tagged with a `C` row on the tool's own line (ruling T12-1's form).
  - `docs/areas/ui-and-moodles.md`: the tooltip guards.
  - `docs/areas/testing-your-mod.md`: a rule that a per-player queue is tested with more stand-in players than its per-minute budget and under a fast clock, and that a refactor of the adapters keeps the golden trace byte for byte; a rule that a kernel `for … in pairs` loop whose body ends in an `if … end` moves the `if` into a helper, because the Lua 5.1 line hook never executes that `end` (measured 2026-10-08, a `C/inference` row on `K.store.addExpired`'s comment); and that the kernel shape tests are CRLF files edited with `newline=''`.
  - `docs/areas/packaging.md`: 1.0.1, the Lua arm of the join checksum in the release tool, the Nutrition Makes Sense warning.
  - `docs/areas/open-questions.md` and `docs/reference/experiments.md`: lines settled by x251 and x252 leave or are marked `run <run-id>`.
  - Every skill quoting a touched rule line re-synced byte-identically (CLAUDE.md § 4.6).
  - The stale-sentence sweep (the memo's Refactor follow-ups): `grep -rn "P.onMinute\|EFF.minute\|NR_Server_Fast\|takeover\|Hook.CalculateStats" docs/areas docs/platform docs/facts mod/NutritionRevamp --include=*.md --include=*.lua` — every sentence that says an adapter appends to `P.onMinute`, that Nutrients calls `EFF.minute` by hand, or that the mod's stats run through the takeover is rewritten to the 1.0.1 build or tagged as history.
  - The delta carries a `status` row narrowing `#0143`'s bound with Appendix E's finding (every spawn and craft writer read sets base hunger equal to hunger; the row stays open on `ItemStatsPacket.applyItemStats`), its bound starting with the register's current bound byte for byte.
- [ ] **Step 3: Gates.** `python tools/page_lint.py <every touched page>` 0; `python tools/claims_delta.py apply <delta> --pages <every touched page> --dry-run` clean; `python tools/reference_gen.py cited-by --check` and `contradictions --check` in sync; `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged` 0 after the controller's apply.
- [ ] **Step 4: Commit** `Docs: Plan 11 as built and measured (performance, lessons, the platform and area pages, open questions, experiments, the skills)` -- the touched pages and skills; the controller applies the delta and re-anchors in its own commit.

---
### Task 6: The close — controller (Opus reviews)

- [ ] **Step 1: Reviews.** A whole-pass review (Opus, read-only) of this plan's commits against the spec's seven decisions and item 8, Plan 11a's seventeen rulings and this plan's three, sentence by sentence on the pages; and a line-level Opus bug review of `git diff <Plan 11a's close commit>..HEAD -- mod/ testing/PZTestKit/ tools/release_pack.py` (Angus prefers local Opus reviews: the memory's `review-local-over-ultra.md`).
- [ ] **Step 2:** One consolidated fix wave (a fresh implementer per file set, each fix test-first) and its scoped re-review.
- [ ] **Step 3: Every § 3 gate,** each in its own call: `python tools/claims_check.py --staged`, `python tools/science_check.py --scan mod`, `python tools/mod_lint.py mod/NutritionRevamp`, `python tools/release_pack.py check mod/NutritionRevamp`, `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit`, `python tools/hotpath_lint.py mod`, `python tools/page_lint.py` on the touched pages, `python tools/reference_gen.py cited-by --check`, `python tools/reference_gen.py contradictions --check`, `python tools/bus_inventory.py --check`, `PYTHONIOENCODING=utf-8 python tools/claims_check.py` (full, 0), `python tools/food_nutrients.py --check`, `python tools/recipe_conservation.py --check`, `python -m pytest tools/tests testing/tests -q` (no failure, at or above Plan 11a's close count; write the new count into CLAUDE.md § 3's pytest line with the date).
- [ ] **Step 4:** CLAUDE.md: § 3's count; § 3 gains `python tools/recipe_conservation.py --check` in sync before any commit that touches `data/recipes.json`, `data/food-nutrients.*`, `NR_Data_Recipes.lua` or the tool; any process ruling this plan took that a later agent must know becomes a § 6 rule. The memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` index, and this project's `MEMORY.md`: Plans 11a and 11b closed, the close commit, the register's last id, the pytest count, what is Angus's.
- [ ] **Step 5:** `git push origin main`; the ledger's Rulings block and `Plan 11b: complete`.
- [ ] **Step 6: The list for Angus:** the β default (0.25) and the light-menu reading it rests on; the prune default (30 real days) and the store's hard-kill caveat; the scheduler's live reading at N = 60 against budget15 and what it means at 20, 40 and 60 players; the own-action latency reading; the recipes left as destroyers; the Workshop upload of 1.0.1 (staged by the tool; `preview.png`, 256×256, still his); E7, the populated-server reading, still his.

## Self-Review

**Spec coverage** (the writing brief's live and release parts; the build parts are Plan 11a's):
- 10. The harness route and the shoot-out — Plan 11a Task 19 (the route, the dry and skip seams in every arm) and Task 2 here (both spacings against `budget15`, the empty-check bench, the own-action latency, a fast-clock arm; the arms' seams checked by the store-write count; the live rules in Task 2 Step 4).
- 11. Live acceptance — Task 4 (the holds with re-asserted, read-back targets; the PANIC moodle read on the client and the server; the queue, the store, the restart, the prune, a real hand craft through Plan 11a Task 17's wrapper, the closed leak through a client `ModData.request`).
- 12. Documentation — Task 5 (performance.md's scheduler reading, the lessons rules, every finding of both plans, the stale-sentence sweep, `#0143`, the for-in coverage rule).
- 13. Release 1.0.1 — Task 3 (Appendix F's update text, R2-1's operator notes, the release tool's Lua arm test-first, the store's emptied slots and world-wipe carry-over in the README).
- 14. The close — Task 6.
- Decision 6's open items: 1 (Plan 11a Task 9's budget, Task 2's reading), 2 (x251c's bench), 3 (x251c's latency), 6 and 7 (first sight and the close ride the queue; a mass reconnect is spread by construction but not read live), 8 (the budget formula; x251c's fast arm), 9 (Plan 11a Task 19). Items 4 and 5 are Angus's (Plan 11a ruling 14).

**Placeholder scan.** Task 1's harness code and Task 3's release-tool tests are written out (the release tests ran red then green against a scratch copy of the tool, 2026-10-08); the drivers of Tasks 2 and 4 are specified phase by phase with every command, reading and grade, because a driver is written against the live bus and committed before its boot — each phase names its commands and its pass condition.

**Type consistency.** `craft.run`, `moodle.watch` (client) and `moodle.level` (server) (Task 1) are used by Task 4; `ghost.load <N> mod`, `ghost.modq`, `action.latency` (Plan 11a Task 19) by Tasks 2 and 4; `NutritionRevamp.server.players.{served,meanMs,budgetMs,runCap,ticksLast}` (Plan 11a Task 9), `NutritionRevamp.server.store.file.{stats.writes,gen}` and `prune` (Plan 11a Task 11), `NutritionRevamp.server.writer.{zeroed,stats}` and `NutritionRevamp.vanillaRate` (Plan 11a Task 14), `NutritionRevamp.server.craft.stats.scaled` and `NutritionRevamp.data.recipes.factor` (Plan 11a Tasks 16 and 17) by Tasks 2 and 4.

**Spec items not covered, with the reason:** vanilla's own updaters at 20 or more real players, the populated-server frame (E7), real network latency and zombies — none is reachable with two clients on one host and no zombies in fixture `two` (Angus's, Plan 11a ruling 14); DayLength 4 set as the option rather than by `time.multiplier` (#3394: the profile route for the 37-tick spacing stays the multiplier, as H3 and H4 ran); a mass reconnect's frame (first sight rides the budgeted queue, so it is spread by construction, but no session reconnects sixty clients).

**Fixed in revision 2 (the re-review of 2026-10-08 and Angus's build ruling):** the build is 42.21 (Plan 11a ruling 17 and Task R), named in the Global Constraints, Task 0 and Task 3, whose version-folder and `versionMin` decision is now unconditional; the provisional ids are `T113<N>.n`, which `PROVISIONAL_ID_RX` accepts and no Plan 11a id uses; every owner cell is in the register's form; every artifact is committed by the controller in one commit with its rows and re-anchor, from the implementer's staged files; the PANIC holds are sized to their 60 s moodle watches and count transitions only inside the hold; the prune waits for bob's departure flush to run and checks the slot stays empty a minute later; the x251c empty-check bench restores the tick count it inflated and drops the next two minutes' budget readings; the shoot-out's reading guides state the `mod` arm's per-drain batching against `budget15`'s per-tick batch; Tasks 2 and 4 write their readings' sentences with their rows; Task 5 documents the two new tools.
