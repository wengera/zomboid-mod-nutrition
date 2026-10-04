# Plan 1 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the nutrition mod's skeleton so that every later plan drops formulas into a tested kernel and adapters into a proven runtime: the mod folder and its lints, the offline kernel test harness with total line coverage, the server store and the command bus with a read-only client mirror, the sandbox options and their read timing, the `Hook.CalculateStats` takeover handler reproducing vanilla's seven stat updaters with no nutrition term yet, the takeover/overlay mode switch, the test profiles, and the live experiments the spec gates this plan on (X7, X28, X4, the handler's live verification X34 with X32/X35/X46 riding it, and the persistence and compatibility readings X41, X42, X43, X44, X49a, X49b).

**Architecture:** Three Lua layers with one direction of dependency (spec § 4.1): a pure Kahlua-safe kernel in `common/media/lua/shared/NR_Kernel*.lua` (tables in, tables out, no Java object ever crosses into it), server adapters in `common/media/lua/server/` behind a nil-checked runtime side test, and a client layer that holds a read-only mirror. Two server clocks: the fast clock is the takeover handler on `Hook.CalculateStats`, per player per update, allocation-free, writing the seven stats from the kernel's deltas and reproducing the seven non-stat side effects; the slow clock is `EveryOneMinute`, which walks the online list, initialises a player on first sight, drops a departed one, and drains the per-player minute work across the following ticks. Durable state is one global modData table `NutritionRevamp.players` keyed by username, cached server-side, inputs only, derived on read. Every live reading goes through the existing harness (`pzt`, PZTestKit, profiles, drivers in the house shape) after the harness changes this plan lands first.

**Tech Stack:** Kahlua (Project Zomboid's Lua 5.1 dialect: no `goto`, no `%d` on a float, no `#` on a Java list, methods not fields); Python 3.13 stdlib tools under `tools/`; `lupa` 2.8 (`lupa.lua51`) hosting the kernel offline under pytest; the harness (`testing/pzt`, `testing/PZTestKit`, `testing/profiles`, `testing/experiments/_template.py`); the claims register and its tools.

**Spec:** `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` — § 2 rulings 5 and 8, § 4.1 (runtime shape), § 4.8 (bus, mirror, persistence), § 4.9 (mod id `NutritionRevamp`, prefix `NR`, bus module `NutritionRevamp`, layout), § 4.10 (the four test tiers), § 5 row 1 (this plan's scope, gates and harness changes), § 6 (performance), § 7 items 13, 22–29, 39, 41, § 8 (experiments). The platform reading it rests on: `docs/facts/character-stats.md` (the seven updaters, the tick order, the fatigue reset), `docs/facts/endurance-fatigue-sleep.md` and `docs/facts/body-and-weight.md` (the decoded rates), `docs/platform/lua-platform.md#hooks`, `docs/platform/sandbox-options.md`, `docs/platform/server-lifecycle.md`, `docs/platform/mp-model.md#command-bus`, `docs/platform/harness.md`, `docs/platform/lessons.md#rules`, `docs/areas/body-effects.md#rules`, `docs/areas/mp-sync.md#rules`, `docs/areas/testing-your-mod.md`, `docs/areas/packaging.md#rules`; the experiment specs `docs/reference/experiments.md` rows X4, X7, X28, X32, X34, X35, X41, X42, X43, X44, X46, X49a, X49b; and the jar read this plan commissioned, `docs/superpowers/research/jar-calculatestats-updaters.md` (Task 8 quotes it).

## Global Constraints

- **Mod tree.** The mod lives at `mod/NutritionRevamp/` in this repository: `42.20.4/mod.info` (the only `mod.info`; `id=NutritionRevamp`; `versionMin=42.20.4`; no `versionMax`, no `require=`), `42.20.4/media/sandbox-options.txt`, and everything else under `common/media/lua/{shared,server,client}/`. No file sits at a vanilla relative path; every Lua file is named `NR_<Role>[_<Part>].lua`; the one global is `NutritionRevamp` (alias `NR` inside each file), with sub-tables `kernel`, `server`, `client`, `log`. Line endings LF (`.gitattributes` gains `mod/** text eol=lf`); the join checksum drops CR bytes, so endings never matter to the gate and LF keeps the tree diff-clean.
- **The kernel is pure.** A file under `shared/` named `NR_Kernel*.lua` holds only functions assigned to `NutritionRevamp.kernel` (or a sub-table of it) and constants; it never names a Java global (`getPlayer`, `getOnlinePlayers`, `SandboxVars`, `Events`, `Hook`, `CharacterStat`, …), never uses `pcall`, `pairs` over a Java object, `#` on anything but a Lua table it built, `goto`, or `string.format` with `%d`. `tools/kahlua_lint.py` enforces the dialect rules on every Lua file of the mod and the experiment mods; `tools/hotpath_lint.py` enforces the fast-path rules inside `-- @fastpath` regions and the kernel-shape rule on `NR_Kernel*.lua`.
- **Fast-path rules** (spec § 6) inside a `-- @fastpath` … `-- @endfastpath` region: no table constructor, no string concatenation, no `pcall`/`xpcall`/`error`/`assert`, no `string.`/`tostring`/`table.`, no `^`/`math.exp`/`math.pow`/`math.log`, no `for` loop, and no method call on a receiver outside the file's `-- @hoisted` list. **Ruling:** exactly one protected call is allowed per player per tick, the rim guard around the whole handler body that spec § 4.1 itself prescribes, marked `-- @rimguard` on its line; the kernel has none — cost if wrong: one `pcall` frame per player per tick, microseconds, against a frozen stat update on the first raise.
- **A handler that cannot raise.** Every Java member the fast path reads is indexed once per player at first sight into a hoisted handle table (`NR.server.fast.h[username]`), checked non-nil there, and called without re-indexing per tick; a handle that was nil at hoist time disables the term that needs it and is logged once. On any failure counted by the rim guard the handler writes vanilla's own shapes with unit coefficients (which in this plan is the same arithmetic) and increments `NutritionRevamp.server.fast.failures`.
- **Server side test.** Every `server/` file's top-level work runs inside `if NutritionRevamp.isServer() then … end` evaluated at event time, never at file scope, because the file also runs in the client's Lua state (`lessons.md` rule #0855/#1075); `isServer` and `isClient` are nil-checked before the protected call that reads them (#0937).
- **Sandbox values are read at event time.** `SandboxVars.NR` is read at `OnServerStarted` (server) / `OnGameStart` (client) and re-read on every slow tick, never at file scope (sandbox-options rules #2460, #2466); the sub-table, never a leaf, is what a file may hold.
- **Persistence.** `ModData.getOrCreate("NutritionRevamp.players")` on `OnInitGlobalModData` and again whenever the table is found missing (#2417); keyed by `getUsername()`, never the online id (#2410); never transmitted (#2416); the server cache writes through on change; a record holds a version field and inputs only.
- **Bus.** Module name `NutritionRevamp`; client→server `mirror.request` (no payload); server→client `mirror` (a flat table of strings, numbers and booleans). The client never writes a mod value back and never reads the engine for a mirrored value.
- **Vanilla parity is the deliverable of the handler.** With no nutrition term, the takeover handler reproduces the seven updaters' arithmetic exactly as the jar read states it (`docs/superpowers/research/jar-calculatestats-updaters.md`, quoted in Task 8), including the seven non-stat side effects (`body-effects.md` rule #2700) and dropping the tripping angle; endurance is NOT integrated by the handler in this plan (the player's own endurance model runs outside the hook, #2235) — the handler only stamps the last-endurance value and honours the unlimited-endurance cheat, exactly as the skipped stub does; the stored-value endurance write and the external-delta fold are Plan 5's and are stubbed as named no-op entry points here. Overlay mode registers nothing and writes nothing per tick in this plan.
- **A number with no row does not ship** (spec § 0) — this plan ships no science number; every engine constant the handler uses carries the claims-register id it rests on in a trailing comment (`-- #0470`), and a constant the register lacks is minted by the documentation delta of the task that lands it.
- **Harness changes land first, each in its own commit**, under CLAUDE.md § 5: `python tools/luabalance.py <lua files>` (HEAD copies first, then the working tree) green, `python tools/bus_inventory.py` regenerating `docs/reference/harness-commands.md`, `python tools/bus_inventory.py --check` in sync, `python -m pytest tools/tests testing/tests -q` green; the next acceptance run is the smoke test. A driver (`testing/experiments/*.py`) is never edited after its run.
- **Live sessions.** One live game session at a time, repository-wide; `python testing/pzt doctor` before every boot; never `-safemode`; a stray `ProjectZomboid64.exe` predating a session is Angus's own client and is never killed; a raising probe is gated server-side with the profile's `[client] timeout` set low; every artifact is copied byte-identical to `testing/artifacts/<run-id>/` with its row in `docs/reference/artifacts.md` and its keys in `docs/reference/do-not-cite.csv` (empty allowed); a reading that comes back trivial, unmeasured or falsified is written as such and never re-run for a prettier number.
- **Register.** The claims register is read-only for implementers: a task that settles or mints a claim writes a delta file `.superpowers/sdd/2026-10-04-plan-1-foundations/task-N-claims-delta.tsv` in `tools/claims_delta.py`'s format (header `op id claim grade pointer bound status successor kind source owner reason`; provisional ids `T<N>.<n>`), the controller applies it with `--pages` at the task's close in the same commit as the artifact and the page sentences, and `python tools/claims_check.py --staged` → 0 before that commit. A settled open row keeps its id and goes `open -> settled` with its pointer `artifact:<run-id>/<file> <key>` and its bound filled; its line leaves `docs/areas/open-questions.md`, and its rows in `docs/reference/experiments.md` and the wall map's experiment table are marked `run <run-id>`.
- **Gates before every commit** (CLAUDE.md § 3, plus this plan's): `python tools/claims_check.py --staged` → 0 for any `docs/` path; `python tools/page_lint.py <pages>` → 0 for any page touched; `python tools/science_check.py --staged` → 0 and `python tools/science_check.py --scan mod` → 0 (no `S` id is cited in this plan, so the scan passes empty); `python tools/mod_lint.py mod/NutritionRevamp` → 0 ERROR; `python tools/kahlua_lint.py mod testing/experiments` → 0; `python tools/hotpath_lint.py mod` → 0; `python -m pytest tools/tests testing/tests -q` green at **429** or more (the Plan 0b close count; the count never drops; Task 17 writes the new count into CLAUDE.md § 3).
- **Commits:** pathspec commits, succinct subjects, no Claude attribution, never `--amend`, implementers never push; the controller pushes at the close. **Subagent sizing** (CLAUDE.md § 6, Angus 2026-10-04): the model is named on every dispatch and in each task's header below — Sonnet for a tool or harness task whose code and tests this plan spells out and for root-file edits; Opus for the kernel and adapter Lua, every live session, every evidence read, every reviewer of those, and the whole-pass review; scoped re-reviews of small fix diffs Sonnet.
- **Rulings this plan takes** (each is a ledger line and a `Ruling:` row at the close): (1) the version dir is `42.20.4`, the verified build, which the resolver scores as `42.20` (#0826) and which no later build is named by; (2) `mod/` is the mod's root in this repository and `--scan mod` is the science checker's argument; (3) the kernel style rule — every kernel function is a field of `NutritionRevamp.kernel`, no local functions, no closures — exists so that `debug.getinfo(f, "L").activelines` over the kernel table is the exact executable-line set the 100 % coverage gate compares against; (4) one rim `pcall` per player per tick (above); (5) X42 and X44 run in this plan because the spec § 4.9 puts the three free live experiments inside Plan 1's acceptance work and each is a standalone reading of a neighbour against vanilla stores, while X43 is written trivial from a dated desk re-read unless the live tree has wired the branch; (6) X13's harness addition `drink.action` lands here (spec § 5 row 1 names it) and X13's session stays Plan 2's.
- **Environment.** Bash cwd resets between calls (`cd /c/Users/Angus/repos/project_zomboid` first); Windows Python takes `C:/Users/...` paths; long text and anything with apostrophes goes through the Write tool; `PYTHONIOENCODING=utf-8` when a checker's output is piped; `tools/README.md` is a CRLF survivor edited with `newline=""` preserving its endings; the install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder are read-only; the jar toolchain `C:\Users\Angus\pz-b42` is read-only and verifies every Java claim.

## Execution order

Tasks 1–3 serial (the tree, the lints, the kernel harness) → Tasks 4 and 5 in parallel (store/bus/players; options/self-report — disjoint files) → Task 6 (harness Python: nested sandbox merge, reuse boot) → Task 7 (harness Lua commands) → Task 8 (the takeover handler and the mode switch; depends on the jar read) → Task 9 (profiles and the two probe mods) → Task 10 (the acceptance run, serial, live) → live experiments serial, one session each: Task 11 (X34 + X35 + X32 + X46), Task 12 (X7 + X41), Task 13 (X28 + X49a + X49b), Task 14 (X4), Task 15 (X42, X44 live; X43 desk) → Task 16 (documentation delta: pages, router, gates, tools page) → Task 17 (the close: whole-pass review, fix wave, gates, memory, push). Each live task's documentation (artifact row, do-not-cite, register delta, page sentences) is part of that task and lands in its commit.

## File structure

| path | responsibility | task |
|---|---|---|
| `mod/NutritionRevamp/42.20.4/mod.info`, `mod/NutritionRevamp/42.20.4/media/sandbox-options.txt`, `mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json`, `mod/NutritionRevamp/common/media/lua/shared/NR_Core.lua`, `.gitattributes` | the mod folder, its id, its options declaration, its labels, its one global and the guard helpers | 1 |
| `tools/kahlua_lint.py`, `tools/hotpath_lint.py`, `tools/tests/test_kahlua_lint.py`, `tools/tests/test_hotpath_lint.py`, `tools/README.md`, `docs/reference/tools.md` | the dialect lint and the fast-path lint | 2 |
| `testing/tests/kernel/conftest.py`, `testing/tests/kernel/test_kernel_core.py`, `testing/tests/kernel/test_zz_coverage.py`, `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel.lua`, `tools/README.md` (lupa line) | the lupa host, the coverage collector and gate, the kernel namespace | 3 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Mirror.lua`, `mod/NutritionRevamp/common/media/lua/server/NR_Server_Store.lua`, `…/server/NR_Server_Players.lua`, `…/server/NR_Server_Bus.lua`, `…/client/NR_Client_Mirror.lua`, `testing/tests/kernel/test_kernel_mirror.py` | the global-modData store, the slow clock's player walk, the bus and the client mirror | 4 |
| `mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua`, `…/client/NR_Client_Options.lua` | the sandbox read at event time, the poll, the boot self-report | 5 |
| `testing/pzt/server.py`, `testing/pzt/profile.py`, `testing/pzt/session.py`, `testing/tests/test_profile.py`, `testing/tests/test_session_reuse.py`, `testing/profiles/README.md` | nested `[sandbox.<Prefix>]` merge and validation; `make_server(reuse=True)` | 6 |
| `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/*.lua`, `docs/reference/harness-commands.md` (generated) | `stats.all`, `trait.push`, `globalmoddata.set`, `globalmoddata.transmit`, `bench.global`, `tick.rate`, `drink.action` | 7 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Fast.lua`, `…/server/NR_Server_Fast.lua`, `testing/tests/kernel/test_kernel_fast.py` | the seven-updater reproduction (kernel) and the hook adapter with the mode switch | 8 |
| `testing/profiles/nr-accept.toml`, `nr-takeover.toml`, `nr-overlay.toml`, `x13-calcstats.toml`, `x13-nutrition-off.toml`, `x13-weight-drift.toml`, `x13-persist.toml`, `x13-traits.toml`, `x13-swtraits.toml`, `x13-ssread.toml`; `testing/experiments/TKX_CalcStats/`, `testing/experiments/TKX_TraitProbe/`, `testing/experiments/TKX_SSRead/` | the profiles and the probe mods | 9 |
| `testing/artifacts/run-<id>/report.json`, `docs/reference/artifacts.md`, `docs/reference/do-not-cite.csv` | the acceptance run | 10 |
| `testing/experiments/x131_calcrepro.py`, `testing/artifacts/x131-<id>/…`, register delta, `docs/facts/character-stats.md`, `docs/facts/endurance-fatigue-sleep.md`, `docs/platform/lua-platform.md`, `docs/areas/open-questions.md`, `docs/reference/experiments.md`, `docs/reference/wall-map.md` | X34, X35, X32, X46 | 11 |
| `testing/artifacts/scenario-<id>/…` (three runs), register delta, `docs/facts/eating-pipeline.md`, `docs/facts/body-and-weight.md`, `docs/areas/new-nutrients.md`, `docs/areas/testing-your-mod.md` | X7, X41 | 12 |
| `testing/experiments/x131_persist.py`, artifacts, register delta, `docs/platform/server-lifecycle.md`, `docs/areas/mp-sync.md`, `docs/areas/new-nutrients.md`, `docs/areas/testing-your-mod.md` | X28, X49a, X49b | 13 |
| `testing/experiments/x131_traits.py`, artifact, register delta, `docs/platform/mp-model.md`, `docs/areas/mp-sync.md`, `docs/reference/wall-map.md` | X4 | 14 |
| `testing/experiments/x131_swtraits.py`, `testing/experiments/x131_ss_track.py`, artifacts, register delta, `docs/facts/other-mods/*.md`, `docs/areas/packaging.md` | X42, X43, X44 | 15 |
| `CLAUDE.md` (§ 1 router row, § 3 gates, § 7), `README.md`, `docs/reference/tools.md`, `docs/areas/testing-your-mod.md`, `docs/areas/packaging.md`, `docs/platform/lessons.md` | the documentation delta | 16 |
| ledger, memory, `CLAUDE.md` § 3 count line | the close | 17 |

---

### Task 1: The mod folder and its one global — Sonnet implementer, Sonnet reviewer

**Files:**
- Create: `mod/NutritionRevamp/42.20.4/mod.info`
- Create: `mod/NutritionRevamp/42.20.4/media/sandbox-options.txt`
- Create: `mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json`
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Core.lua`
- Modify: `.gitattributes` (append one line)

**Interfaces:**
- Produces: the global `NutritionRevamp` with `version`, `build`, `kernel`, `server`, `client`, `log`; `NutritionRevamp.isServer()`, `NutritionRevamp.isClient()` (nil-checked, evaluated per call, never cached); `NutritionRevamp.call(obj, name, ...) -> present, result...` (the index-first guard); `NutritionRevamp.log.say(level, msg)` with `NutritionRevamp.log.level` (1 quiet, 2 normal, 3 verbose; default 2). The sandbox options `NR.Mode` (enum, 1 Takeover, 2 Overlay, default 1) and `NR.LogLevel` (enum, 1–3, default 2).

- [ ] **Step 1: Write the mod.info**

`mod/NutritionRevamp/42.20.4/mod.info` (five keys, the only ones the loader reads that this mod needs, #0816; `versionMin` is a hard gate, #0812):

```
name=Nutrition Revamp
id=NutritionRevamp
description=Realism nutrition overhaul for Build 42 dedicated servers: nutrients beyond the four macros, a two-compartment body and effects pinned to published evidence. Foundations build: no nutrition term yet.
modversion=0.1.0
versionMin=42.20.4
```

- [ ] **Step 2: Write the sandbox declaration**

`mod/NutritionRevamp/42.20.4/media/sandbox-options.txt` — every pair comma-terminated (#2462), block comments only (#2463), every option on a page (#2464), one dot in the id (#2433):

```
VERSION = 1,

/* NutritionRevamp sandbox options, prefix NR. The reader erases newlines: every key = value
   pair ends in a comma, the last before a brace included. Comment with block comments only. */

option NR.Mode
{
    type = enum, numValues = 2, default = 1,
    page = NutritionRevamp, translation = NR_Mode, valueTranslation = NR_ModeValues,
}

option NR.LogLevel
{
    type = enum, numValues = 3, default = 2,
    page = NutritionRevamp, translation = NR_LogLevel, valueTranslation = NR_LogLevelValues,
}
```

- [ ] **Step 3: Write the labels**

`mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json` — the B42 translation layout is `Translate/<LANG>/<File>.json` and translations merge into vanilla's map rather than shadowing it (#0839, #0841); the key shapes are `Sandbox_<page>`, `Sandbox_<translation>`, `Sandbox_<translation>_tooltip`, `Sandbox_<valueTranslation>_option<N>` (#2438), copied from vanilla's own `media/lua/shared/Translate/EN/Sandbox.json` in the install:

```json
{
    "Sandbox_NutritionRevamp": "Nutrition Revamp",
    "Sandbox_NR_Mode": "Stat update mode",
    "Sandbox_NR_Mode_tooltip": "Takeover: the mod replaces the vanilla stat update on the server through the CalculateStats hook. Overlay: the vanilla update runs and the mod writes after it. Choose Overlay when another mod claims the hook.",
    "Sandbox_NR_ModeValues_option1": "Takeover",
    "Sandbox_NR_ModeValues_option2": "Overlay",
    "Sandbox_NR_LogLevel": "Server log detail",
    "Sandbox_NR_LogLevel_tooltip": "How much Nutrition Revamp prints to the server console.",
    "Sandbox_NR_LogLevelValues_option1": "Quiet",
    "Sandbox_NR_LogLevelValues_option2": "Normal",
    "Sandbox_NR_LogLevelValues_option3": "Verbose"
}
```

- [ ] **Step 4: Write the core file**

`mod/NutritionRevamp/common/media/lua/shared/NR_Core.lua` loads first among the mod's shared files by name (`NR_Core` sorts before `NR_Kernel`), so every other `NR_` file assumes the global exists:

```lua
-- NR_Core.lua -- the mod's one global, its version, the side test and the index-first guard.
-- Loads first in shared/ by name; every other NR_ file assumes NutritionRevamp exists.
-- Plain assignment on every load: a reload of this file resets the sub-tables, so no sentinel
-- for a wrapped vanilla function may live here (lua-platform rule #0943).
NutritionRevamp = {
    version = "0.1.0",
    build = "42.20.4",
    kernel = {},   -- pure functions, tables in and tables out, no Java (NR_Kernel*.lua)
    server = {},   -- server adapters (server/NR_Server_*.lua), gated by NutritionRevamp.isServer()
    client = {},   -- the read-only mirror (client/NR_Client_*.lua)
    log = { level = 2 },
}
local NR = NutritionRevamp

-- The side test, nil-checked before the protected call that reads it (#0937), evaluated per
-- call and never cached at file scope: a Lua state can load this file before the side is
-- decided, and a mod's server/ files run in the client's state too (#0855).
function NR.isServer()
    if isServer == nil then return false end
    local ok, v = pcall(isServer)
    return ok and v == true
end

function NR.isClient()
    if isClient == nil then return false end
    local ok, v = pcall(isClient)
    return ok and v == true
end

-- The index-first guard (#0934, #0935): index the member, then call it. Returns
-- (present, result...). A caught nil call names nothing, so the guard is what makes an absent
-- member visible. Never used inside a @fastpath region, which hoists its handles instead.
function NR.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

-- Console lines on whichever side runs this. level 1 quiet (the boot self-report only),
-- 2 normal, 3 verbose. The level is set from the sandbox option at event time (NR_Server_Options).
function NR.log.say(level, msg)
    if level <= NR.log.level then print("[NutritionRevamp] " .. tostring(msg)) end
end
```

- [ ] **Step 5: Pin the tree's line endings**

Append to `.gitattributes` (LF file, three lines today):

```
mod/** text eol=lf
```

- [ ] **Step 6: Run the layout lint and the balance check**

Run: `cd /c/Users/Angus/repos/project_zomboid && python tools/mod_lint.py mod/NutritionRevamp && python tools/luabalance.py mod/NutritionRevamp/common/media/lua/shared/NR_Core.lua`
Expected: the lint's count line shows `0 ERROR` (a `media` WARN or INFO is acceptable and never fails the gate), exit 0; the balance check prints zero deltas and zero negative-depth lines. `python -c "import json; json.load(open('mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json', encoding='utf-8'))"` exits 0.

- [ ] **Step 7: Commit**

```bash
git add mod/NutritionRevamp .gitattributes
git commit -m "Mod: the NutritionRevamp folder, options declaration, labels and core" -- mod/NutritionRevamp .gitattributes
```

---

### Task 2: The dialect lint and the fast-path lint — Sonnet implementer, Sonnet reviewer

**Files:**
- Create: `tools/kahlua_lint.py`, `tools/hotpath_lint.py`
- Create: `tools/tests/test_kahlua_lint.py`, `tools/tests/test_hotpath_lint.py`
- Modify: `tools/README.md` (two bullets under a new `## Mod lints` heading, CRLF preserved), `docs/reference/tools.md` (two bullets in the tools list, reference profile)

**Interfaces:**
- Consumes: nothing of the mod but its files.
- Produces: `python tools/kahlua_lint.py <path …>` and `python tools/hotpath_lint.py <path …>`, each printing `path:line: rule: detail` per finding and `N findings` last, exit 1 on any finding; module API `lint(paths) -> [Finding(path, line, rule, detail)]`. Rules below.

Both tools share one Lua tokeniser shape: a `strip(src)` that blanks comments and string literals while keeping newlines, in the shape `tools/luabalance.py` already uses (`LONG_OPEN`, the `--` line comment, quoted strings), so a rule never fires on a word inside a comment or a string.

- [ ] **Step 1: Write the failing tests for the dialect lint**

`tools/tests/test_kahlua_lint.py`:

```python
import os, sys, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import kahlua_lint as kl


def lint_text(tmp_path, text, name="X.lua"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return [(f.line, f.rule) for f in kl.lint([str(p)])]


def test_goto_and_labels_are_findings(tmp_path):
    out = lint_text(tmp_path, """
        local x = 1
        goto done
        ::done::
    """)
    assert out == [(3, "goto"), (4, "goto")]


def test_percent_d_in_format_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local s = string.format("%d items", n)
        local t = string.format("%.0f items", n)
    """)
    assert out == [(2, "format-d")]


def test_length_of_a_call_result_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local n = #players:getItems()
        local m = #getOnlinePlayers()
        local k = #list
    """)
    assert out == [(2, "java-length"), (3, "java-length")]


def test_pairs_over_a_call_result_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        for k, v in pairs(p:getModData()) do end
        for k, v in pairs(t) do end
    """)
    assert out == [(2, "java-pairs")]


def test_words_inside_comments_and_strings_do_not_fire(tmp_path):
    out = lint_text(tmp_path, """
        -- goto is not in Kahlua; string.format("%d") raises
        local s = "goto ::x:: %d"
        local long = [[
          goto
        ]]
    """)
    assert out == []


def test_loadstring_is_a_finding(tmp_path):
    assert lint_text(tmp_path, 'local f = loadstring("return 1")\n') == [(1, "loadstring")]


def test_directories_are_walked_and_only_lua_files_read(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "ok.lua").write_text("local x = 1\n", encoding="utf-8")
    (tmp_path / "a" / "bad.lua").write_text("goto x\n", encoding="utf-8")
    (tmp_path / "a" / "note.txt").write_text("goto x\n", encoding="utf-8")
    found = kl.lint([str(tmp_path / "a")])
    assert [os.path.basename(f.path) for f in found] == ["bad.lua"]


def test_cli_exit_code_and_count_line(tmp_path, capsys):
    p = tmp_path / "x.lua"
    p.write_text("goto x\n", encoding="utf-8")
    assert kl.main([str(p)]) == 1
    assert capsys.readouterr().out.strip().splitlines()[-1] == "1 findings"
    p.write_text("local x = 1\n", encoding="utf-8")
    assert kl.main([str(p)]) == 0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_kahlua_lint.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'kahlua_lint'`.

- [ ] **Step 3: Write the dialect lint**

`tools/kahlua_lint.py`:

```python
#!/usr/bin/env python3
"""Kahlua dialect lint for the mod's Lua and the experiment mods (CLAUDE.md § 5 Kahlua rules).

    python tools/kahlua_lint.py mod testing/experiments

Prints `path:line: rule: detail` per finding and `N findings` last; exits 1 on any finding.
Comments and string literals are blanked first (the shape tools/luabalance.py uses), so a rule
never fires on a word inside either.

| rule          | fires on                                                                 |
|---------------|--------------------------------------------------------------------------|
| `goto`        | the keyword `goto` or a `::label::` -- Kahlua has neither (#0938)        |
| `format-d`    | `%d`, `%i`, `%x`, `%X`, `%o`, `%c` inside a `string.format` call -- the dialect raises on a float (#0939) |
| `java-length` | `#` applied to a call result (`#x:getItems()`, `#getOnlinePlayers()`): a Java list has no length (#0940) |
| `java-pairs`  | `pairs(` or `ipairs(` whose argument is a call result: iterating a Java object raises (#0941) |
| `loadstring`  | `loadstring(` -- removed in 42.20.x (#0960)                              |

Stdlib only; read-only.
"""
import argparse, collections, os, re, sys

Finding = collections.namedtuple("Finding", "path line rule detail")

LONG_OPEN = re.compile(r"(--)?\[(=*)\[")
GOTO_RX = re.compile(r"(?<![\w.])goto\s+\w+|::\s*\w+\s*::")
FORMAT_RX = re.compile(r"string\.format\s*\(")
FORMAT_D_RX = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[dixXoc]")
LENGTH_CALL_RX = re.compile(r"#\s*[\w.]+(?::\w+)?\s*\(")
PAIRS_CALL_RX = re.compile(r"\bi?pairs\s*\(\s*[\w.]+(?::\w+)?\s*\(")
LOADSTRING_RX = re.compile(r"\bloadstring\s*\(")


def strip(src):
    """Blank comments and string literals, keeping every newline (luabalance.py's shape).
    String bodies are replaced by spaces so column positions and %d inside them vanish."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        m = LONG_OPEN.match(src, i)
        if m and (m.group(1) or src[i] == "["):
            close = "]" + m.group(2) + "]"
            j = src.find(close, m.end())
            j = n if j < 0 else j + len(close)
            out.append("\n" * src.count("\n", i, j))
            i = j
            continue
        if src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(c + " " * max(0, j - i - 1) + c)
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def lint_text(path, text):
    found = []
    for n, line in enumerate(strip(text).split("\n"), 1):
        if GOTO_RX.search(line):
            found.append(Finding(path, n, "goto", "Kahlua has no goto and no labels"))
        if FORMAT_RX.search(line):
            # the original line's literals are blanked, so look at the raw line's format string
            raw = text.split("\n")[n - 1]
            if FORMAT_D_RX.search(raw):
                found.append(Finding(path, n, "format-d", "integer conversion of a Lua number raises; use %.0f"))
        if LENGTH_CALL_RX.search(line):
            found.append(Finding(path, n, "java-length", "# on a call result: a Java list has no length; walk size()/get(i)"))
        if PAIRS_CALL_RX.search(line):
            found.append(Finding(path, n, "java-pairs", "pairs over a call result: a Java object raises; walk size()/get(i)"))
        if LOADSTRING_RX.search(line):
            found.append(Finding(path, n, "loadstring", "removed on 42.20.x"))
    return found


def lua_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.lower().endswith(".lua"):
                        yield os.path.join(root, f)
        elif p.lower().endswith(".lua"):
            yield p


def lint(paths):
    found = []
    for path in lua_files(paths):
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            found.extend(lint_text(path.replace("\\", "/"), fh.read()))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    found = lint(a.paths)
    for f in found:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(found)} findings")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the dialect lint tests**

Run: `python -m pytest tools/tests/test_kahlua_lint.py -q`
Expected: 8 passed. Then `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` → `0 findings` (the harness and the experiment mods already obey the rules; a finding there is a real one and is fixed in this task by the narrowest edit, noted in the report).

- [ ] **Step 5: Write the failing tests for the fast-path lint**

`tools/tests/test_hotpath_lint.py`:

```python
import os, sys, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import hotpath_lint as hl


def lint_text(tmp_path, text, name="NR_Server_Fast.lua"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return [(f.line, f.rule) for f in hl.lint([str(p)])]


REGION = """
    -- @hoisted stats, K
    local function tick(h, p)
        -- @fastpath
        local v = h.stats:get(h.HUNGER)
        local d = K.hunger_delta(p.in, p.out)
        h.stats:set(h.HUNGER, v + d)
        -- @endfastpath
    end
"""


def test_a_clean_region_has_no_findings(tmp_path):
    assert lint_text(tmp_path, REGION) == []


def test_each_forbidden_shape_is_named(tmp_path):
    out = lint_text(tmp_path, """
        -- @hoisted h
        -- @fastpath
        local t = { a = 1 }
        local s = "a" .. "b"
        local ok = pcall(f)
        local u = tostring(x)
        local w = string.format("%f", x)
        local e = math.exp(x)
        local q = x ^ 2
        for i = 1, 3 do end
        local z = p:getStats()
        -- @endfastpath
    """)
    assert out == [(4, "alloc"), (5, "concat"), (6, "pcall"), (7, "string"), (8, "string"),
                   (9, "math"), (10, "math"), (11, "loop"), (12, "unhoisted-call")]


def test_rimguard_allows_exactly_one_pcall(tmp_path):
    out = lint_text(tmp_path, """
        -- @fastpath
        local ok = pcall(body, h, p)   -- @rimguard
        local ok2 = pcall(body, h, p)  -- @rimguard
        -- @endfastpath
    """)
    assert out == [(4, "pcall")]


def test_code_outside_a_region_is_free(tmp_path):
    assert lint_text(tmp_path, 'local t = { a = "x" .. "y" }\nlocal ok = pcall(f)\n') == []


def test_unterminated_region_is_a_finding(tmp_path):
    assert lint_text(tmp_path, "-- @fastpath\nlocal x = 1\n") == [(1, "region")]


def test_kernel_files_allow_only_kernel_fields(tmp_path):
    out = lint_text(tmp_path, """
        local K = NutritionRevamp.kernel
        K.fast = K.fast or {}
        function K.fast.hunger(p) return p.x end
        local function helper() return 1 end
        function other() return 2 end
        K.fast.cb = function() return 3 end
    """, name="NR_Kernel_Fast.lua")
    assert out == [(5, "kernel-shape"), (6, "kernel-shape"), (7, "kernel-shape")]


def test_kernel_files_may_not_name_java_globals(tmp_path):
    out = lint_text(tmp_path, """
        local K = NutritionRevamp.kernel
        function K.bad(p) return getPlayer() end
        function K.bad2(p) return SandboxVars.NR.Mode end
        function K.ok(p) return p.mode end
    """, name="NR_Kernel_X.lua")
    assert out == [(3, "kernel-java"), (4, "kernel-java")]
```

- [ ] **Step 6: Run them to verify they fail**

Run: `python -m pytest tools/tests/test_hotpath_lint.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'hotpath_lint'`.

- [ ] **Step 7: Write the fast-path lint**

`tools/hotpath_lint.py`:

```python
#!/usr/bin/env python3
"""Fast-path and kernel-shape lint for the nutrition mod (spec § 6 fast-path rules, § 4.1 kernel).

    python tools/hotpath_lint.py mod

Inside a `-- @fastpath` ... `-- @endfastpath` region (any Lua file) a line may not:
  alloc           open a table constructor `{`
  concat          concatenate strings `..`
  pcall           call pcall/xpcall/error/assert -- except ONE line per region carrying `-- @rimguard`
  string          call string.* / tostring / tonumber / table.*
  math            use `^`, math.exp, math.pow, math.log, math.sqrt
  loop            open a for/while/repeat loop
  unhoisted-call  call a method `name:method(` on a receiver not in the file's `-- @hoisted a, b` list
                  (a receiver written `x.y:z(` is checked on its first segment)
  region          a @fastpath with no @endfastpath, or an @endfastpath with no open region
A file named `NR_Kernel*.lua` (the pure kernel) additionally may not:
  kernel-shape    define a function other than `function NutritionRevamp.kernel.<path>(` /
                  `function K.<path>(` (K the local alias) -- no `local function`, no bare
                  globals, no anonymous functions assigned to fields -- so that
                  debug.getinfo(f, "L").activelines over the kernel table is the whole
                  executable-line set the coverage gate compares against (Plan 1 ruling 3)
  kernel-java     name a Java-side global: getPlayer, getOnlinePlayers, getSpecificPlayer,
                  SandboxVars, getSandboxOptions, Events, Hook, CharacterStat, MoodleType,
                  CharacterTrait, ModData, getGameTime, getWorld, isServer, isClient,
                  sendServerCommand, sendClientCommand, print
Comments and strings are blanked first (kahlua_lint.strip). Stdlib only; read-only.
"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kahlua_lint import strip, lua_files

Finding = collections.namedtuple("Finding", "path line rule detail")

HOISTED_RX = re.compile(r"--\s*@hoisted\s+(.*)$")
RULES = [
    ("alloc", re.compile(r"\{"), "table constructor allocates per tick"),
    ("concat", re.compile(r"\.\."), "string concatenation allocates per tick"),
    ("pcall", re.compile(r"\b(?:x?pcall|error|assert)\s*\("), "protected call per tick (one @rimguard allowed per region)"),
    ("string", re.compile(r"\b(?:string\.\w+|tostring|tonumber|table\.\w+)\s*\("), "string or table library call per tick"),
    ("math", re.compile(r"\^|\bmath\.(?:exp|pow|log|sqrt)\s*\("), "exponential or power per tick: compute on the slow clock"),
    ("loop", re.compile(r"^\s*(?:for|while|repeat)\b"), "loop per tick"),
]
METHOD_CALL_RX = re.compile(r"([A-Za-z_]\w*)(?:\.[A-Za-z_]\w*)*:\w+\s*\(")
KERNEL_FUNC_RX = re.compile(r"^\s*function\s+(NutritionRevamp\.kernel|K)\.[\w.]+\s*\(")
ANY_FUNC_RX = re.compile(r"^\s*(?:local\s+)?function\b|=\s*function\s*\(")
JAVA_GLOBALS = ("getPlayer", "getOnlinePlayers", "getSpecificPlayer", "SandboxVars", "getSandboxOptions",
                "Events", "Hook", "CharacterStat", "MoodleType", "CharacterTrait", "ModData", "getGameTime",
                "getWorld", "isServer", "isClient", "sendServerCommand", "sendClientCommand", "print")
JAVA_RX = re.compile(r"(?<![\w.])(?:%s)\b" % "|".join(JAVA_GLOBALS))


def lint_text(path, text):
    found, raw_lines = [], text.split("\n")
    lines = strip(text).split("\n")
    hoisted = set()
    for raw in raw_lines:
        m = HOISTED_RX.search(raw)
        if m:
            hoisted.update(w.strip() for w in m.group(1).split(",") if w.strip())
    in_region, region_start, rimguard_used = False, 0, False
    kernel = os.path.basename(path).startswith("NR_Kernel")
    for n, (line, raw) in enumerate(zip(lines, raw_lines), 1):
        if "@fastpath" in raw and "@endfastpath" not in raw:
            if in_region:
                found.append(Finding(path, n, "region", "@fastpath inside an open region"))
            in_region, region_start, rimguard_used = True, n, False
            continue
        if "@endfastpath" in raw:
            if not in_region:
                found.append(Finding(path, n, "region", "@endfastpath with no open region"))
            in_region = False
            continue
        if in_region:
            for rule, rx, detail in RULES:
                if rx.search(line):
                    if rule == "pcall" and "@rimguard" in raw and not rimguard_used:
                        rimguard_used = True
                        continue
                    found.append(Finding(path, n, rule, detail))
            for m in METHOD_CALL_RX.finditer(line):
                if m.group(1) not in hoisted:
                    found.append(Finding(path, n, "unhoisted-call", f"method call on {m.group(1)!r}, not in @hoisted"))
        if kernel:
            if ANY_FUNC_RX.search(line) and not KERNEL_FUNC_RX.search(line):
                found.append(Finding(path, n, "kernel-shape", "a kernel function is `function NutritionRevamp.kernel.<path>(` or `function K.<path>(`"))
            if JAVA_RX.search(line):
                found.append(Finding(path, n, "kernel-java", "the kernel never names a Java-side global"))
    if in_region:
        found.append(Finding(path, region_start, "region", "@fastpath never closed"))
    return found


def lint(paths):
    found = []
    for path in lua_files(paths):
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            found.extend(lint_text(path.replace("\\", "/"), fh.read()))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    found = lint(a.paths)
    for f in found:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(found)} findings")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 8: Run the fast-path lint tests and both lints on the tree**

Run: `python -m pytest tools/tests/test_hotpath_lint.py tools/tests/test_kahlua_lint.py -q && python tools/hotpath_lint.py mod && python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit`
Expected: 15 passed; `0 findings` twice. (`NR_Core.lua` has no region and is not a kernel file.)

- [ ] **Step 9: Document the two tools**

`tools/README.md`: add a `## Mod lints` heading after `## Intake pipeline`'s block with two bullets in the file's bullet shape (`- \`kahlua_lint.py\` — \`python tools/kahlua_lint.py mod testing/experiments\` …` naming the five rules; `- \`hotpath_lint.py\` — …` naming the regions, the rimguard exception and the two kernel rules). Edit with `newline=""` and keep every existing line ending. `docs/reference/tools.md`: two bullets in the tools list in the page's shape (one sentence each, no numbers, no register tag needed because they describe the tools' own behaviour); `python tools/page_lint.py docs/reference/tools.md` → 0.

- [ ] **Step 10: Gates and commit**

Run: `python -m pytest tools/tests testing/tests -q` (expected 444 passed = 429 + 15) · `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged` → 0 after `git add`.

```bash
git add tools/kahlua_lint.py tools/hotpath_lint.py tools/tests/test_kahlua_lint.py tools/tests/test_hotpath_lint.py tools/README.md docs/reference/tools.md
git commit -m "Tools: the Kahlua dialect lint and the fast-path lint" -- tools/kahlua_lint.py tools/hotpath_lint.py tools/tests/test_kahlua_lint.py tools/tests/test_hotpath_lint.py tools/README.md docs/reference/tools.md
```

---

### Task 3: The kernel test harness under lupa with total line coverage — Sonnet implementer, Opus reviewer

**Files:**
- Create: `testing/tests/kernel/__init__.py` (empty), `testing/tests/kernel/conftest.py`, `testing/tests/kernel/test_kernel_core.py`, `testing/tests/kernel/test_zz_coverage.py`
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel.lua`
- Modify: `tools/README.md` (one line under `## Mod lints`: the lupa requirement)

**Interfaces:**
- Consumes: `NR_Core.lua` (Task 1).
- Produces: pytest fixture `host` (a `LuaHost`: `host.rt` the `lupa.lua51.LuaRuntime`; `host.K` the `NutritionRevamp.kernel` table; `host.call(path, *args)` calling a kernel function by dotted path; `host.table(dict)` converting a Python dict to a Lua table; `host.py(lua_table)` converting back) and the session-scoped coverage accumulator `COVERAGE` the last test asserts on. `NutritionRevamp.kernel.version` and `NutritionRevamp.kernel.clamp(x, lo, hi)`.

Design: `lupa` 2.8 ships a Lua 5.1 runtime as `lupa.lua51` (`pip download lupa` resolved `lupa-2.8-cp313-cp313-win_amd64.whl` on this machine on 2026-10-04); Kahlua is a Lua 5.1 dialect, so the kernel runs under PUC 5.1 unchanged apart from the dialect gaps the lint already forbids. Coverage: a Lua line hook (`debug.sethook(fn, "l")`) records `(chunkname, line)` into a Lua table; the executable-line set is `debug.getinfo(f, "L").activelines` for the chunk function of every kernel file and for every function reachable from `NutritionRevamp.kernel` (recursively through sub-tables), which is exact because the kernel-shape lint allows no other function. `test_zz_coverage.py` sorts last in its directory and asserts the two sets are equal per kernel file, so a kernel line no test reaches fails the suite (spec § 4.10 tier 2: 100 % of kernel lines).

- [ ] **Step 1: Install lupa and record the requirement**

Run: `python -m pip install lupa==2.8 && python -c "import lupa.lua51 as L; r = L.LuaRuntime(); print(r.eval('_VERSION'))"`
Expected: `Lua 5.1`. Add to `tools/README.md` under `## Mod lints`: a bullet `- The kernel tests under \`testing/tests/kernel/\` need \`lupa\` 2.8 (\`python -m pip install lupa==2.8\`): the mod's pure kernel runs offline under its Lua 5.1 runtime, and the suite fails rather than skips without it.`

- [ ] **Step 2: Write the kernel namespace file**

`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel.lua`:

```lua
-- NR_Kernel.lua -- the pure kernel's namespace and its shared helpers. Tables in, tables out,
-- no Java object ever crosses into a kernel function (spec § 4.1); every function here is a
-- field of NutritionRevamp.kernel so the coverage gate can enumerate it (Plan 1 ruling 3).
local K = NutritionRevamp.kernel
K.version = NutritionRevamp.version

-- Clamp x into [lo, hi]. Every Stats write passes the stat's own clamp in Java (#2208); the
-- kernel clamps too so a delta it hands out never asks the engine to clamp.
function K.clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end

-- max(a, b) and min(a, b) without math.*, which the fast-path lint forbids per tick.
function K.max(a, b)
    if a > b then return a end
    return b
end

function K.min(a, b)
    if a < b then return a end
    return b
end
```

- [ ] **Step 3: Write the host and the coverage collector**

`testing/tests/kernel/conftest.py`:

```python
"""The lupa host for the mod's pure kernel (spec § 4.10 tier 2).

Loads NR_Core.lua and every NR_Kernel*.lua under a Lua 5.1 runtime with a line hook that records
every executed (chunk, line). The executable-line set is debug.getinfo(f, "L").activelines over
the chunk function of each kernel file and every function reachable from NutritionRevamp.kernel;
test_zz_coverage.py asserts the two sets agree per file. A kernel function that is not a field of
the kernel table is invisible to that enumeration, which is why tools/hotpath_lint.py forbids one.
"""
import glob, os, pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
CORE = os.path.join(SHARED, "NR_Core.lua")


def kernel_files():
    return sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))


COLLECTOR = r"""
NR_COV = NR_COV or {}
debug.sethook(function(ev, line)
    local info = debug.getinfo(2, "S")
    if info == nil then return end
    local f = NR_COV[info.source]
    if f == nil then f = {}; NR_COV[info.source] = f end
    f[line] = true
end, "l")
"""

ACTIVE = r"""
-- active lines of every function reachable from the kernel table plus the given chunk functions
function NR_ACTIVE(chunks)
    local out = {}
    local function add(f)
        local info = debug.getinfo(f, "SL")
        if info == nil or info.activelines == nil then return end
        local t = out[info.source]
        if t == nil then t = {}; out[info.source] = t end
        for line in pairs(info.activelines) do t[line] = true end
    end
    for _, f in ipairs(chunks) do add(f) end
    local seen = {}
    local function walk(tbl)
        if seen[tbl] then return end
        seen[tbl] = true
        for _, v in pairs(tbl) do
            if type(v) == "function" then add(v) elseif type(v) == "table" then walk(v) end
        end
    end
    walk(NutritionRevamp.kernel)
    return out
end
"""


class LuaHost:
    def __init__(self):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(COLLECTOR)
        self.chunks = []
        for path in [CORE] + kernel_files():
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            chunk = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))
            self.chunks.append(chunk)
            chunk()
        self.rt.execute(ACTIVE)
        self.G = self.rt.globals()
        self.K = self.G.NutritionRevamp.kernel

    def call(self, path, *args):
        fn = self.K
        for seg in path.split("."):
            fn = fn[seg]
        return fn(*args)

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = self.table(v) if isinstance(v, dict) else v
        return t

    def py(self, t):
        if lua51.lua_type(t) != "table":
            return t
        return {k: self.py(v) for k, v in t.items()}

    def executed(self):
        return {src: set(lines.keys()) for src, lines in self.G.NR_COV.items()}

    def active(self):
        chunks = self.rt.table(*self.chunks)
        return {src: set(lines.keys()) for src, lines in self.G.NR_ACTIVE(chunks).items()}


@pytest.fixture(scope="session")
def host():
    return LuaHost()
```

- [ ] **Step 4: Write the first kernel tests and the coverage gate**

`testing/tests/kernel/test_kernel_core.py`:

```python
def test_kernel_version_is_the_mod_version(host):
    assert host.K.version == host.G.NutritionRevamp.version == "0.1.0"


def test_clamp_min_max(host):
    assert host.call("clamp", 0.5, 0.0, 1.0) == 0.5
    assert host.call("clamp", -1.0, 0.0, 1.0) == 0.0
    assert host.call("clamp", 2.0, 0.0, 1.0) == 1.0
    assert host.call("max", 1, 2) == 2 and host.call("max", 3, 2) == 3
    assert host.call("min", 1, 2) == 1 and host.call("min", 3, 2) == 2


def test_the_core_side_tests_are_false_offline(host):
    # isServer/isClient are nil in the host, so the nil-checked side test answers false on both.
    assert host.G.NutritionRevamp.isServer() is False
    assert host.G.NutritionRevamp.isClient() is False


def test_the_guard_reports_absence_without_raising(host):
    present, value = host.G.NutritionRevamp.call(None, "getX")
    assert (present, value) == (False, None)
    present, value = host.G.NutritionRevamp.call(host.table({}), "getX")
    assert (present, value) == (False, None)
```

`testing/tests/kernel/test_zz_coverage.py` (sorts last; pytest collects a directory's files in sorted order):

```python
"""The 100 % kernel line-coverage gate (spec § 4.10 tier 2). Runs last in this directory."""


def test_every_kernel_line_executed(host):
    active, executed = host.active(), host.executed()
    missing = {}
    for src, lines in active.items():
        if not src.startswith("@NR_Kernel"):
            continue                       # NR_Core.lua is the runtime's, not the kernel's
        gap = sorted(lines - executed.get(src, set()))
        if gap:
            missing[src] = gap
    assert not missing, f"kernel lines never executed by a test: {missing}"
    assert any(src.startswith("@NR_Kernel") for src in active), "no kernel file was loaded"
```

- [ ] **Step 5: Run the kernel tests**

Run: `python -m pytest testing/tests/kernel -q`
Expected: 5 passed. Then delete one assertion temporarily (for example the `-1.0` clamp line) and re-run: `test_every_kernel_line_executed` must FAIL naming `@NR_Kernel.lua` and the `return lo` line; restore the assertion and re-run to green. State both runs in the report.

- [ ] **Step 6: Gates and commit**

Run: `python tools/hotpath_lint.py mod && python tools/kahlua_lint.py mod && python -m pytest tools/tests testing/tests -q`
Expected: `0 findings` twice; 449 passed (444 + 5).

```bash
git add testing/tests/kernel mod/NutritionRevamp/common/media/lua/shared/NR_Kernel.lua tools/README.md
git commit -m "Kernel: the lupa host, the coverage gate and the kernel namespace" -- testing/tests/kernel mod/NutritionRevamp/common/media/lua/shared/NR_Kernel.lua tools/README.md
```

---

### Task 4: The store, the slow clock's player walk, the bus and the client mirror — Opus implementer, Opus reviewer

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Mirror.lua`
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Store.lua`, `…/server/NR_Server_Players.lua`, `…/server/NR_Server_Bus.lua`
- Create: `mod/NutritionRevamp/common/media/lua/client/NR_Client_Mirror.lua`
- Create: `testing/tests/kernel/test_kernel_mirror.py`

**Interfaces:**
- Consumes: `NutritionRevamp.isServer()`, `NR.call`, `NR.log.say` (Task 1); `K.clamp` (Task 3).
- Produces (server): `NR.server.store.get(username) -> record` (creating from `NR.server.store.new(username, worldAgeHours)` when absent), `NR.server.store.reset(username, worldAgeHours)` (a fresh record, the old one replaced), `NR.server.store.records` (the cached table, the same object the global modData holds); `NR.server.players.online` (username → `IsoPlayer` for the last walk), `NR.server.players.onFirstSight(username, player)` and `.onDeparture(username)` hook lists later plans append to; `NR.server.bus.sendMirror(player, record)`; `NR.server.players.minute()` the slow tick and `NR.server.players.drain()` the per-tick queue drain. Produces (kernel): `K.mirror.build(record, meta) -> flat table` with `meta = {mode, version, build}`. Produces (client): `NR.client.mirror` the installed table and `NR.client.requestMirror()`.
- Record shape (version 1, inputs only): `{ v = 1, username = <string>, firstSeen = <worldAgeHours>, lastSeen = <worldAgeHours>, resets = <count>, dead = <boolean> }`. Later plans add input fields and bump `v`; nothing derived is stored (lessons rule #1068).

- [ ] **Step 1: Write the failing mirror tests**

`testing/tests/kernel/test_kernel_mirror.py`:

```python
import pytest


def rec(host, **kw):
    r = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False}
    r.update(kw)
    return host.table(r)


def test_mirror_is_flat_scalars_only(host):
    m = host.py(host.call("mirror.build", rec(host), host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    assert m == {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False,
                 "mode": 1, "version": "0.1.0", "build": "42.20.4"}
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_copies_rather_than_aliases_the_record(host):
    r = rec(host)
    m = host.call("mirror.build", r, host.table({"mode": 2, "version": "x", "build": "y"}))
    m["lastSeen"] = 99
    assert r["lastSeen"] == 2.25


def test_mirror_meta_is_required(host):
    with pytest.raises(Exception):
        host.call("mirror.build", rec(host), None)
```

Run: `python -m pytest testing/tests/kernel -q` → FAIL (`mirror` is nil).

- [ ] **Step 2: Write the mirror kernel**

`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Mirror.lua`:

```lua
-- NR_Kernel_Mirror.lua -- the flat scalar table the server sends a client (spec § 4.8): every
-- value a string, number or boolean, copied from the record, never the record itself.
local K = NutritionRevamp.kernel
K.mirror = {}

-- record: the stored inputs; meta: { mode, version, build }. Returns a new flat table.
function K.mirror.build(record, meta)
    local m = {}
    m.v = record.v
    m.username = record.username
    m.firstSeen = record.firstSeen
    m.lastSeen = record.lastSeen
    m.resets = record.resets
    m.dead = record.dead
    m.mode = meta.mode
    m.version = meta.version
    m.build = meta.build
    return m
end
```

Run: `python -m pytest testing/tests/kernel -q` → 8 passed (the coverage gate included).

- [ ] **Step 3: Write the store**

`mod/NutritionRevamp/common/media/lua/server/NR_Server_Store.lua`:

```lua
-- NR_Server_Store.lua -- the durable per-player store: one global modData table keyed by
-- username (server-lifecycle rules #2410, #2417; spec § 4.8), cached server-side, inputs only,
-- never transmitted (#2416) and never player modData (#1042). Runs in both Lua states; every
-- write below is behind NutritionRevamp.isServer().
local NR = NutritionRevamp
NR.server.store = { name = "NutritionRevamp.players", records = nil }
local S = NR.server.store

-- ModData.getOrCreate creates the table when the file did not hold it; OnInitGlobalModData's
-- boolean says the WORLD is new, not the table (#2417), so the table is fetched whenever it is
-- found missing, not only on a new world.
function S.attach()
    if S.records ~= nil then return S.records end
    if ModData == nil then return nil end
    local ok, t = NR.call(ModData, "getOrCreate", S.name)
    if ok and t ~= nil then S.records = t end
    return S.records
end

function S.new(username, worldAgeHours)
    return { v = 1, username = username, firstSeen = worldAgeHours, lastSeen = worldAgeHours,
             resets = 0, dead = false }
end

function S.get(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local r = t[username]
    if r == nil then
        r = S.new(username, worldAgeHours)
        t[username] = r
        NR.log.say(3, "store: new record for " .. tostring(username))
    end
    return r
end

-- A respawn: the character is new, the record starts fresh, the reset count carries over so
-- a later reading can tell a returning player from a new one.
function S.reset(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local old = t[username]
    local r = S.new(username, worldAgeHours)
    r.resets = (old and old.resets or 0) + 1
    t[username] = r
    NR.log.say(2, "store: reset record for " .. tostring(username) .. " (reset " .. tostring(r.resets) .. ")")
    return r
end

if Events ~= nil and Events.OnInitGlobalModData ~= nil then
    Events.OnInitGlobalModData.Add(function(isNewGame)
        if not NR.isServer() then return end
        S.records = nil
        S.attach()
        NR.log.say(2, "store attached (new world: " .. tostring(isNewGame) .. ")")
    end)
end
```

- [ ] **Step 4: Write the bus**

`mod/NutritionRevamp/common/media/lua/server/NR_Server_Bus.lua`:

```lua
-- NR_Server_Bus.lua -- the server half of the command bus (mp-model #0932, lessons #1065):
-- module "NutritionRevamp"; the client asks "mirror.request" with no payload and the server
-- answers "mirror" with the flat table K.mirror.build makes. The server never trusts a payload
-- it did not send; in this plan the one client command carries none.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.bus = { module = "NutritionRevamp" }
local B = NR.server.bus

function B.meta()
    local o = NR.server.options
    return { mode = o and o.mode or 1, version = NR.version, build = NR.build }
end

function B.sendMirror(player, record)
    if player == nil or record == nil then return false end
    if sendServerCommand == nil then return false end
    local ok = pcall(sendServerCommand, player, B.module, "mirror", K.mirror.build(record, B.meta()))
    if not ok then NR.log.say(2, "bus: sendServerCommand failed for " .. tostring(record.username)) end
    return ok
end

if Events ~= nil and Events.OnClientCommand ~= nil then
    Events.OnClientCommand.Add(function(module, command, player, args)
        if module ~= B.module then return end
        if not NR.isServer() then return end
        if command == "mirror.request" then
            local okU, username = NR.call(player, "getUsername")
            if not okU or username == nil then return end
            local okT, gt = pcall(getGameTime)
            local okA, age = NR.call(okT and gt or nil, "getWorldAgeHours")
            local r = NR.server.store.get(username, okA and age or 0)
            if r ~= nil then B.sendMirror(player, r) end
        end
    end)
end
```

- [ ] **Step 5: Write the player walk**

`mod/NutritionRevamp/common/media/lua/server/NR_Server_Players.lua`:

```lua
-- NR_Server_Players.lua -- the slow clock (spec § 4.1): EveryOneMinute snapshots the online
-- list, initialises a player on first sight (the server fires no join event, #2412), drops a
-- player who left (no disconnect event either, #2403), reads death off the dead flag, and queues
-- the per-player minute work so OnTick drains one player per frame (the stagger). OnNewGame
-- fires server-side for every character a client creates, respawns included (#2411): the record
-- is reset there. Java lists are walked with size()/get(i) (#0940).
local NR = NutritionRevamp
NR.server.players = { online = {}, queue = {}, queueHead = 1, onFirstSight = {}, onDeparture = {},
                      minutes = 0, drained = 0 }
local P = NR.server.players

local function worldAge()
    if getGameTime == nil then return 0 end
    local ok, gt = pcall(getGameTime)
    local okA, age = NR.call(ok and gt or nil, "getWorldAgeHours")
    if okA and type(age) == "number" then return age end
    return 0
end

local function fire(list, username, player, record)
    for i = 1, #list do
        local ok, err = pcall(list[i], username, player, record)
        if not ok then NR.log.say(2, "players: hook failed: " .. tostring(err)) end
    end
end

-- One player's minute work. Plan 1: refresh lastSeen and the dead flag; later plans append to
-- P.onMinute. Called from the OnTick drain, one player per tick.
P.onMinute = {}
function P.work(username, player)
    local r = NR.server.store.get(username, worldAge())
    if r == nil then return end
    r.lastSeen = worldAge()
    local okD, dead = NR.call(player, "isDead")
    if okD and dead == true and r.dead ~= true then
        r.dead = true
        NR.log.say(2, "players: " .. tostring(username) .. " is dead; record kept until respawn")
    end
    fire(P.onMinute, username, player, r)
end

function P.minute()
    if getOnlinePlayers == nil then return end
    local ok, list = pcall(getOnlinePlayers)
    if not ok or list == nil then return end
    local okS, n = NR.call(list, "size")
    if not okS or type(n) ~= "number" then return end
    P.minutes = P.minutes + 1
    local seen = {}
    local i = 0
    while i < n do
        local okG, player = NR.call(list, "get", i)
        if okG and player ~= nil then
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                seen[username] = player
                if P.online[username] == nil then
                    local r = NR.server.store.get(username, worldAge())
                    NR.log.say(2, "players: first sight of " .. tostring(username))
                    fire(P.onFirstSight, username, player, r)
                    if r ~= nil then NR.server.bus.sendMirror(player, r) end
                end
                P.queue[#P.queue + 1] = username
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
    P.queueHead = 1
end

-- The stagger: one queued player per tick; a cheap early-out when the queue is empty, which is
-- what keeps this off the expensive tier (lessons #1071, #1080).
function P.drain()
    local username = P.queue[P.queueHead]
    if username == nil then
        if #P.queue > 0 then P.queue = {}; P.queueHead = 1 end
        return
    end
    P.queueHead = P.queueHead + 1
    local player = P.online[username]
    if player ~= nil then
        P.drained = P.drained + 1
        P.work(username, player)
    end
end

if Events ~= nil then
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function() if NR.isServer() then P.minute() end end)
    end
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function() if NR.isServer() then P.drain() end end)
    end
    if Events.OnNewGame ~= nil then
        Events.OnNewGame.Add(function(player, square)
            if not NR.isServer() then return end
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                local r = NR.server.store.reset(username, worldAge())
                if r ~= nil then NR.server.bus.sendMirror(player, r) end
            end
        end)
    end
end
```

- [ ] **Step 6: Write the client mirror**

`mod/NutritionRevamp/common/media/lua/client/NR_Client_Mirror.lua`:

```lua
-- NR_Client_Mirror.lua -- the client's read-only copy of the server's mirror (spec § 4.8). It
-- installs what the server sends and never writes back; a client write to a field no packet
-- carries would only drift (#0129). The request is sent once at OnGameStart and again by
-- whatever opens the panel in a later plan.
local NR = NutritionRevamp
NR.client.mirror = nil
NR.client.received = 0

function NR.client.requestMirror()
    if not NR.isClient() then return false end
    if sendClientCommand == nil or getPlayer == nil then return false end
    local okP, p = pcall(getPlayer)
    if not okP or p == nil then return false end
    local ok = pcall(sendClientCommand, p, "NutritionRevamp", "mirror.request", {})
    return ok
end

if Events ~= nil then
    if Events.OnServerCommand ~= nil then
        Events.OnServerCommand.Add(function(module, command, args)
            if module ~= "NutritionRevamp" or command ~= "mirror" then return end
            if not NR.isClient() then return end
            NR.client.mirror = args
            NR.client.received = NR.client.received + 1
        end)
    end
    if Events.OnGameStart ~= nil then
        Events.OnGameStart.Add(function() NR.client.requestMirror() end)
    end
end
```

- [ ] **Step 7: Lints, balance, tests**

Run: `python tools/kahlua_lint.py mod && python tools/hotpath_lint.py mod && python tools/luabalance.py mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Mirror.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Store.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Players.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Bus.lua mod/NutritionRevamp/common/media/lua/client/NR_Client_Mirror.lua && python -m pytest tools/tests testing/tests -q`
Expected: `0 findings` twice, balanced, 452 passed (449 + 3). The `#P.queue` and `#list` uses are on Lua tables the mod built, which the `java-length` rule does not flag (it fires on call results only).

- [ ] **Step 8: Commit**

```bash
git add mod/NutritionRevamp testing/tests/kernel/test_kernel_mirror.py
git commit -m "Mod: the global-modData store, the slow clock walk, the bus and the client mirror" -- mod/NutritionRevamp testing/tests/kernel/test_kernel_mirror.py
```

---

### Task 5: Sandbox options read at event time and the boot self-report — Sonnet implementer, Sonnet reviewer

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua`, `mod/NutritionRevamp/common/media/lua/client/NR_Client_Options.lua`

**Interfaces:**
- Consumes: `NR.log`, `NR.isServer`, `NR.isClient` (Task 1); `NR.server.players.onMinute` (Task 4).
- Produces: `NR.server.options = { mode = 1|2, logLevel = 1|2|3, readAt = <string> }`, `NR.server.readOptions() -> options` (re-reads `SandboxVars.NR`; called at `OnServerStarted` and appended to `onMinute` so an admin apply is followed within a minute, #2466), `NR.server.options.changed` hook list (functions `(old, new)`), the self-report line `NR.selfReport() -> string` printed at `OnServerStarted` (server) and `OnGameStart` (client), in the shape packaging rule #2716 asks for: `NutritionRevamp v0.1.0 build 42.20.4 side=server mode=takeover log=2 frameworks=none`.

- [ ] **Step 1: Write the server options file**

`mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua`:

```lua
-- NR_Server_Options.lua -- the mod's sandbox options, read at event time (sandbox-options rule
-- #2460): every mod Lua file runs before the operator's values reach SandboxVars, so a read at
-- file scope sees the declared default. No change event exists (#2466), so the options are
-- re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
NR.server.options = { mode = 1, logLevel = 2, readAt = "default", changed = {} }
local O = NR.server.options

local MODE_NAMES = { "takeover", "overlay" }

local function readLeaf(tbl, key, default, lo, hi)
    if tbl == nil then return default end
    local v = tbl[key]
    if type(v) ~= "number" then return default end
    if v < lo or v > hi then return default end
    return v
end

function NR.server.readOptions(where)
    local sv = SandboxVars and SandboxVars.NR or nil
    local oldMode, oldLog = O.mode, O.logLevel
    O.mode = readLeaf(sv, "Mode", 1, 1, 2)
    O.logLevel = readLeaf(sv, "LogLevel", 2, 1, 3)
    O.readAt = where or "poll"
    NR.log.level = O.logLevel
    if oldMode ~= O.mode or oldLog ~= O.logLevel then
        for i = 1, #O.changed do
            local ok, err = pcall(O.changed[i], { mode = oldMode, logLevel = oldLog }, O)
            if not ok then NR.log.say(2, "options: changed hook failed: " .. tostring(err)) end
        end
    end
    return O
end

function NR.modeName(mode)
    return MODE_NAMES[mode] or ("mode" .. tostring(mode))
end

function NR.selfReport(side)
    return "NutritionRevamp v" .. NR.version .. " build " .. NR.build .. " side=" .. tostring(side)
        .. " mode=" .. NR.modeName(O.mode) .. " log=" .. tostring(O.logLevel) .. " frameworks=none"
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        NR.server.readOptions("OnServerStarted")
        NR.log.say(1, NR.selfReport("server"))
    end)
end

-- The poll rides the slow clock; onMinute is a per-player list, so the read is keyed off the
-- first queued player of each minute by comparing the minute counter.
local lastMinute = -1
NR.server.players.onMinute[#NR.server.players.onMinute + 1] = function()
    if NR.server.players.minutes ~= lastMinute then
        lastMinute = NR.server.players.minutes
        NR.server.readOptions("poll")
    end
end
```

- [ ] **Step 2: Write the client options file**

`mod/NutritionRevamp/common/media/lua/client/NR_Client_Options.lua`:

```lua
-- NR_Client_Options.lua -- the client reads the same options after the join sync has landed
-- (OnGameStart, #2446) for its log level, and prints the self-report once.
local NR = NutritionRevamp
NR.client.options = { mode = 1, logLevel = 2 }

if Events ~= nil and Events.OnGameStart ~= nil then
    Events.OnGameStart.Add(function()
        if not NR.isClient() then return end
        local sv = SandboxVars and SandboxVars.NR or nil
        if sv ~= nil then
            if type(sv.Mode) == "number" then NR.client.options.mode = sv.Mode end
            if type(sv.LogLevel) == "number" then NR.client.options.logLevel = sv.LogLevel end
        end
        NR.log.level = NR.client.options.logLevel
        print("[NutritionRevamp] NutritionRevamp v" .. NR.version .. " build " .. NR.build
              .. " side=client mode=" .. tostring(NR.client.options.mode)
              .. " log=" .. tostring(NR.client.options.logLevel) .. " frameworks=none")
    end)
end
```

- [ ] **Step 3: Lints, balance, commit**

Run: `python tools/kahlua_lint.py mod && python tools/hotpath_lint.py mod && python tools/luabalance.py mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua mod/NutritionRevamp/common/media/lua/client/NR_Client_Options.lua && python -m pytest testing/tests/kernel -q`
Expected: `0 findings` twice, balanced, kernel tests green (these files are adapters; the coverage gate reads kernel files only).

```bash
git add mod/NutritionRevamp
git commit -m "Mod: sandbox options read at event time and the boot self-report" -- mod/NutritionRevamp
```

---

### Task 6: Harness Python — the nested sandbox merge and the reuse boot — Sonnet implementer, Sonnet reviewer

**Files:**
- Modify: `testing/pzt/server.py` (`sandbox_keys`, `merge_sandbox_vars`), `testing/pzt/profile.py` (`check_sandbox`, the `[sandbox]` loader), `testing/pzt/session.py` (`make_server`), `testing/profiles/README.md` (one paragraph)
- Modify: `testing/tests/test_profile.py` (new tests); Create: `testing/tests/test_session_reuse.py`

**Interfaces:**
- Produces: a profile may carry `[sandbox.<Prefix>]` tables (TOML nested tables), validated against the options declared in each profile mod's `media/sandbox-options.txt` (version dir first, then `common/`; `profile.declared_mod_options(mod_dir) -> {"Prefix.Name": type}`), merged into the restored server file as a nested block at four spaces with leaves at eight (`server.merge_sandbox_vars(path, overrides)` now accepts dict values), appended before the closing brace when the file has no such block; `make_server(run_dir, rec, ..., reuse=False)`: with `reuse=True` the fixture is not restored and the run directory's existing `server/` cache is booted again (X28, X49b).

Background: the server writes a mod prefix as a nested Lua table at four spaces with its options at eight (#2455); a file predating the mod gains the block at boot (#2452); an option missing from the file keeps its current value (#2453); the harness's merge today matches top-level keys only and would append a dotted key as invalid Lua (#2458). The nested merge writes exactly the shape the server writes, so the server's boot-time rewrite keeps it.

- [ ] **Step 1: Write the failing tests**

Append to `testing/tests/test_profile.py`:

```python
# ---- nested (mod) sandbox options ---------------------------------------------------------

NESTED_SANDBOX = ("SandboxVars = {\r\n"
                  "    VERSION = 6,\r\n"
                  "    Zombies = 6,\r\n"
                  "    NR = {\r\n"
                  "        Mode = 1,\r\n"
                  "        LogLevel = 2,\r\n"
                  "    },\r\n"
                  "}\r\n")

OPTIONS_TXT = ("VERSION = 1,\n"
               "option NR.Mode { type = enum, numValues = 2, default = 1, page = NutritionRevamp, translation = NR_Mode, }\n"
               "option NR.LogLevel { type = enum, numValues = 3, default = 2, page = NutritionRevamp, translation = NR_LogLevel, }\n")


def _mod_with_options(root):
    d = os.path.join(root, "NutritionRevamp")
    _write(os.path.join(d, "42.20.4", "mod.info"), "name=NR\nid=NutritionRevamp\n")
    _write(os.path.join(d, "42.20.4", "media", "sandbox-options.txt"), OPTIONS_TXT)
    return d


def test_declared_mod_options_reads_the_version_dir_file(tmp_path):
    d = _mod_with_options(str(tmp_path))
    assert profile.declared_mod_options(d) == {"NR.Mode": "enum", "NR.LogLevel": "enum"}


def test_declared_mod_options_falls_back_to_common(tmp_path):
    d = os.path.join(str(tmp_path), "M")
    _write(os.path.join(d, "42", "mod.info"), "id=M\n")
    _write(os.path.join(d, "common", "media", "sandbox-options.txt"), "VERSION = 1,\noption M.X { type = boolean, default = true, page = M, }\n")
    assert profile.declared_mod_options(d) == {"M.X": "boolean"}


def test_merge_rewrites_a_nested_leaf_in_place(tmp_path):
    p = _write(str(tmp_path / "s.lua"), NESTED_SANDBOX)
    applied, appended = server.merge_sandbox_vars(p, {"NR": {"Mode": 2}})
    text = open(p, encoding="utf-8", newline="").read()
    assert applied == ["NR.Mode"] and appended == []
    assert "        Mode = 2,\r\n" in text and "        LogLevel = 2,\r\n" in text
    assert text.count("\r\n") == NESTED_SANDBOX.count("\r\n")


def test_merge_appends_a_missing_nested_block_before_the_closing_brace(tmp_path):
    p = _write(str(tmp_path / "s.lua"), SANDBOX)
    applied, appended = server.merge_sandbox_vars(p, {"NR": {"Mode": 2, "LogLevel": 3}})
    text = open(p, encoding="utf-8", newline="").read()
    assert applied == [] and appended == ["NR.LogLevel", "NR.Mode"]
    assert text.endswith("    NR = {\r\n        LogLevel = 3,\r\n        Mode = 2,\r\n    },\r\n}\r\n")


def test_merge_appends_a_missing_leaf_inside_an_existing_block(tmp_path):
    p = _write(str(tmp_path / "s.lua"), NESTED_SANDBOX)
    applied, appended = server.merge_sandbox_vars(p, {"NR": {"Extra": True}})
    text = open(p, encoding="utf-8", newline="").read()
    assert appended == ["NR.Extra"]
    assert "        LogLevel = 2,\r\n        Extra = true,\r\n    },\r\n" in text


def test_a_nested_profile_block_validates_against_the_mods_declarations(tmp_path):
    d = _mod_with_options(str(tmp_path))
    toml = f'[[mods]]\nid = "NutritionRevamp"\npath = {json.dumps(d)}\n[sandbox]\nZombies = 4\n[sandbox.NR]\nMode = 2\n'
    with workspace(toml):
        p = profile.load("p")
        assert p.sandbox == {"Zombies": 4, "NR": {"Mode": 2}}


def test_a_nested_key_no_mod_declares_is_an_error(tmp_path):
    d = _mod_with_options(str(tmp_path))
    toml = f'[[mods]]\nid = "NutritionRevamp"\npath = {json.dumps(d)}\n[sandbox.NR]\nModee = 2\n'
    with workspace(toml):
        with pytest.raises(profile.ProfileError, match="NR.Modee"):
            profile.load("p")


def test_a_nested_prefix_no_mod_declares_is_an_error(tmp_path):
    toml = '[sandbox.ZZ]\nMode = 2\n'
    with workspace(toml):
        with pytest.raises(profile.ProfileError, match="ZZ"):
            profile.load("p")
```

`testing/tests/test_session_reuse.py`:

```python
"""make_server(reuse=True) boots the run directory's existing server cache instead of restoring
the fixture into it (X28, X49b: a second boot on the same run dir). Pure Python: no game."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pzt import session


class Calls:
    restored = []


def test_reuse_skips_the_restore_and_keeps_the_record_ports(monkeypatch, tmp_path):
    rec = {"name": "default", "server": {"name": "pzt", "mods": ["PZTestKit"], "port": 27261, "rcon_port": 27015}}
    monkeypatch.setattr(session.fx, "restore_server", lambda name, run_dir: Calls.restored.append(name) or os.path.join(run_dir, "server"))
    monkeypatch.setattr(session.Server, "seed", lambda self, sandbox=None: None)
    run_dir = str(tmp_path)
    os.makedirs(os.path.join(run_dir, "server", "Server"))
    s = session.make_server(run_dir, rec, reuse=True)
    assert Calls.restored == []
    assert s.cache == os.path.abspath(os.path.join(run_dir, "server"))
    assert (s.name, s.port, s.rcon_port, s.mods) == ("pzt", 27261, 27015, ["PZTestKit"])


def test_reuse_refuses_a_run_dir_with_no_server_cache(tmp_path):
    rec = {"name": "default", "server": {"name": "pzt", "mods": ["PZTestKit"], "port": 1, "rcon_port": 2}}
    try:
        session.make_server(str(tmp_path), rec, reuse=True)
    except SystemExit as e:
        assert "reuse" in str(e)
    else:
        raise AssertionError("expected SystemExit")
```

Run: `python -m pytest testing/tests/test_profile.py testing/tests/test_session_reuse.py -q` → FAIL (`declared_mod_options` missing; merge returns `"NR"` as a top-level key; `make_server` has no `reuse`).

- [ ] **Step 2: Extend the merge**

In `testing/pzt/server.py`, replace `merge_sandbox_vars` with a version that handles dict values; keep `SANDBOX_KEY_RX`, `sandbox_keys` and `TRAILING_COMMENT_RX` unchanged and add:

```python
NESTED_OPEN_RX = re.compile(r"^ {4}(\w+) = \{\s*$")
NESTED_LEAF_RX = re.compile(r"^ {8}(\w+) = ")
NESTED_CLOSE = "    },"


def merge_sandbox_vars(path, overrides):
    """Rewrite only the named options, keeping every other line as the fixture had them.
    A top-level override `{"DayLength": 1}` rewrites the four-space key; a nested override
    `{"NR": {"Mode": 2}}` rewrites the eight-space leaf inside the `    NR = {` block the server
    writes for a mod prefix (#2455), appends a missing leaf at the block's end, and appends a
    missing block before the file's closing brace. -> (applied, appended), each a sorted list of
    dotted names for nested keys; CRLF preserved."""
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    flat = {k: lua_value(v) for k, v in overrides.items() if not isinstance(v, dict)}
    nested = {k: {lk: lua_value(lv) for lk, lv in v.items()} for k, v in overrides.items() if isinstance(v, dict)}
    applied, out, block, leaves_written_at_close = [], [], None, []
    for line in text.splitlines():
        if block is None:
            m = SANDBOX_KEY_RX.match(line)
            if m and m.group(1) in flat:
                note = TRAILING_COMMENT_RX.search(line)
                out.append(f"    {m.group(1)} = {flat.pop(m.group(1))},{note.group(0) if note else ''}")
                applied.append(m.group(1))
                continue
            mo = NESTED_OPEN_RX.match(line)
            if mo and mo.group(1) in nested:
                block = mo.group(1)
            out.append(line)
            continue
        if line == NESTED_CLOSE:
            for leaf in sorted(nested[block]):
                out.append(f"        {leaf} = {nested[block][leaf]},")
                leaves_written_at_close.append(f"{block}.{leaf}")
            nested.pop(block)
            block = None
            out.append(line)
            continue
        ml = NESTED_LEAF_RX.match(line)
        if ml and ml.group(1) in nested[block]:
            note = TRAILING_COMMENT_RX.search(line)
            out.append(f"        {ml.group(1)} = {nested[block].pop(ml.group(1))},{note.group(0) if note else ''}")
            applied.append(f"{block}.{ml.group(1)}")
            continue
        out.append(line)
    appended = sorted(flat) + sorted(f"{p}.{leaf}" for p, leaves in nested.items() for leaf in leaves)
    appended += sorted(n for n in leaves_written_at_close if n not in applied)
    if flat or nested:
        closes = [i for i, l in enumerate(out) if l == "}"]
        if not closes:
            raise SystemExit(f"sandbox merge: {path} has no closing '}}' at column 0, so "
                             f"{', '.join(appended)} cannot be appended -- is this a "
                             "SandboxVars.lua the server wrote?")
        extra = [f"    {k} = {flat[k]}," for k in sorted(flat)]
        for prefix in sorted(nested):
            extra.append(f"    {prefix} = {{")
            extra.extend(f"        {leaf} = {nested[prefix][leaf]}," for leaf in sorted(nested[prefix]))
            extra.append(NESTED_CLOSE)
        out[closes[-1]:closes[-1]] = extra
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nl.join(out) + nl)
    return sorted(applied), appended
```

(A leaf the file's existing block lacks is written at that block's close inside the loop and counted in `appended`; a block the file lacks is appended whole before the closing brace; the tests above are the contract.)

- [ ] **Step 3: Extend the profile loader**

In `testing/pzt/profile.py`: add

```python
OPTION_RX = re.compile(r"\boption\s+([A-Za-z_]\w*\.[A-Za-z_]\w*)\s*\{([^}]*)\}", re.S)
TYPE_RX = re.compile(r"\btype\s*=\s*(\w+)")


def declared_mod_options(mod_dir):
    """{'Prefix.Name': type} from the mod's media/sandbox-options.txt: the version dir's copy
    wins outright and common/ is read only when the version dir ships none (#2422). The reader
    concatenates lines without newlines and strips /* */ only (#2425, #2426); this parser
    tolerates both shapes because it reads option blocks by their braces."""
    from .mods import _version_key  # the newest version dir, as mods.mod_id_of picks it
    candidates = []
    for name in sorted(os.listdir(mod_dir)) if os.path.isdir(mod_dir) else []:
        if re.match(r"^42(\.\d+){0,2}$", name):
            candidates.append(os.path.join(mod_dir, name))
    candidates.sort(key=lambda d: tuple(int(x) for x in os.path.basename(d).split(".")), reverse=True)
    paths = [os.path.join(d, "media", "sandbox-options.txt") for d in candidates]
    paths.append(os.path.join(mod_dir, "common", "media", "sandbox-options.txt"))
    for p in paths:
        if os.path.exists(p):
            text = re.sub(r"/\*.*?\*/", "", open(p, encoding="utf-8", errors="replace").read(), flags=re.S)
            out = {}
            for m in OPTION_RX.finditer(text):
                t = TYPE_RX.search(m.group(2))
                out[m.group(1)] = t.group(1) if t else "unknown"
            return out
    return {}
```

and change `check_sandbox(name, sandbox, path, mod_dirs=())` so that: top-level (non-dict) keys validate as today; each dict value under key `Prefix` validates every leaf `Leaf` against the union of `declared_mod_options(d)` over `mod_dirs`, raising `ProfileError(f"profile '{name}': [sandbox.{Prefix}] '{Prefix}.{Leaf}' is declared by no mod in this profile ...")` with the three closest declared names, and raising for a prefix no declaration carries. In `load`, pass the resolved mod source folders (`sources.values()`, plus `HARNESS_MODS` paths) as `mod_dirs`, and allow dict values through the `[sandbox]` key check (`_check_keys` treats a nested table as a value). `declared_mod_options` must not import a private name if `mods._version_key` is awkward — inline the tuple sort as shown and drop the import line.

- [ ] **Step 4: Add the reuse boot**

In `testing/pzt/session.py` change `make_server`'s signature to `make_server(run_dir, rec=None, port=None, rcon_port=None, mods=None, name="pzt", sandbox=None, workshop=True, workshop_items=(), mod_sources=None, mod_skip=(), reuse=False)` and its body's first branch to:

```python
    if rec:
        srv = rec["server"]
        if reuse:
            cache = os.path.join(run_dir, "server")
            if not os.path.isdir(os.path.join(cache, "Server")):
                raise SystemExit(f"make_server(reuse=True): {cache} holds no server cache to boot again; "
                                 "a reuse boot follows a first boot on the same run_dir")
        else:
            cache = fx.restore_server(rec["name"], run_dir)
        name, mods = srv["name"], mods or srv["mods"]
        port, rcon_port = port or srv["port"], rcon_port or srv["rcon_port"]
```

`Server.seed` already keeps an existing world (it rewrites the ini's ports and mods and re-installs the mods folder), so a reuse boot needs nothing else.

- [ ] **Step 5: Document and test**

`testing/profiles/README.md`: one paragraph after the schema prose: `[sandbox.<Prefix>]` tables set a mod's own options; each leaf must be declared in a profile mod's `media/sandbox-options.txt`; the merge writes the server's own nested shape; the fixture's file need not carry the block. Run: `python -m pytest tools/tests testing/tests -q` → 462 passed (452 + 10). `python tools/bus_inventory.py --check` → in sync (no Lua changed).

- [ ] **Step 6: Commit**

```bash
git add testing/pzt/server.py testing/pzt/profile.py testing/pzt/session.py testing/tests/test_profile.py testing/tests/test_session_reuse.py testing/profiles/README.md
git commit -m "Harness: nested [sandbox.Prefix] merge and validation; make_server(reuse=True)" -- testing/pzt/server.py testing/pzt/profile.py testing/pzt/session.py testing/tests/test_profile.py testing/tests/test_session_reuse.py testing/profiles/README.md
```

---

### Task 7: Harness Lua — the seven commands this plan's readings need — Opus implementer, Opus reviewer

**Files:**
- Modify: `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua` (`stats.all`, `bench.global`, `tick.rate`), `…/server/PZTestKit_Server.lua` (`trait.push`, `globalmoddata.set`, `globalmoddata.transmit`), `…/client/PZTestKit_Client.lua` (`drink.action`)
- Regenerate: `docs/reference/harness-commands.md`

**Interfaces** (each site carries its `-- @args` / `-- @reply` / `-- @purpose` block above `TK.register`, the generator's contract):
- `stats.all <user>` (server) / `stats.all` (client): `{side, user, worldAge, mult, wall, stats = {<id> = <value> for all 24 registered stats>}, missing = [...]}` — every `CharacterStat` static of the registry table in `docs/facts/character-stats.md#registry`, read through `getStats():get(CharacterStat.<FIELD>)` under the guard; a field the build lacks lands in `missing`.
- `trait.push <user> [mask]` (server): calls `sendSyncPlayerFields(player, mask or 2)`; reply `{user, mask, sent, traitList, held}`; the global is server-gated and returns silently (#2602), so `sent` records only that the call ran.
- `globalmoddata.set <name> <key> <value>` (server): `ModData.getOrCreate(name)[key] = value` with the number/boolean/string coercion `moddata.set` uses; reply `{name, key, value, keyCount, keys}`. `globalmoddata.transmit <name>` (server): `ModData.transmit(name)`; reply `{name, transmitted}`.
- `bench.global <dotted.fn> <n>` (shared): resolves a Lua global function by dotted path through the same walk `lua.global` uses, calls it `n` times inside one `getTimestampMs()` bracket, reply `{side, name, n, ms, usPerCall}`; refuses a non-function (`{error}`) and `n` above 100000.
- `tick.rate <seconds>` (shared): counts `OnTick` fires over the wall window and answers `{side, seconds, ticks, ticksPerSecond, worldMinutesPerSecond}` — the result is asynchronous: the command arms a counter and the reply names the result document `tick-rate.json` to wait for with `wait_result`, in the shape `test.run` uses.
- `drink.action <fullType> [percentage]` (client): the twin of `eat.action`: `findOrSpawn`, `ISDrinkFluidAction:new(player, item, percentage or 1.0)`, `ISTimedActionQueue.add`, reply `{queued, percentage, spawned, itemId, filledRatioBefore, before}` with `before` the nutrition snapshot; the outcome is asynchronous (poll `nutrition.get`).

- [ ] **Step 1: Write the seven sites**

Shapes to copy: `stats.get` (`PZTestKit_Server.lua:187`) for a player snapshot; `trait.set` (`:280`) for a trait reply with `held`; `moddata.set` (`:159`) for the value coercion and key census; `eat.action` (`PZTestKit_Client.lua:487`) for the queued action; `lua.global` (`PZTestKit_Core.lua:861`) for the dotted walk; `time.snapshot` (`:573`) for the clock. Every Java member call goes through `TK.call`. For `stats.all` the registry list is a Lua table of the 24 field names (`ANGER … ZOMBIE_INFECTION`) iterated with `ipairs`; `CharacterStat[field]` nil → `missing`. For `tick.rate`: `Events.OnTick.Add` once at file load with a counter that runs only while armed; the command records the wall start and the world age, arms for `seconds`, and the handler writes `tick-rate.json` through `TK.writeResult` (the result writer the test layer uses) when the window closes.

- [ ] **Step 2: Balance, lint, inventory, tests**

Run: `git stash -q && python tools/luabalance.py testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua; git stash pop -q && python tools/luabalance.py <the same three>` (the HEAD copies first, then the working tree — both balanced), `python tools/kahlua_lint.py testing/PZTestKit` → 0, `python tools/bus_inventory.py` (regenerates the table; it must grow by exactly eight rows: `stats.all` ×2 sides, `bench.global` ×1 shared, `tick.rate` ×1 shared, `trait.push`, `globalmoddata.set`, `globalmoddata.transmit`, `drink.action`), `python tools/bus_inventory.py --check` → in sync, `python -m pytest tools/tests testing/tests -q` green. The CRLF survivors `PZTestKit_Core.lua` and `PZTestKit_Server.lua` keep their endings (edit with `newline=""`; `file <path>` before and after).

- [ ] **Step 3: Commit**

```bash
git add testing/PZTestKit docs/reference/harness-commands.md
git commit -m "Harness: stats.all, trait.push, globalmoddata.set/transmit, bench.global, tick.rate, drink.action" -- testing/PZTestKit docs/reference/harness-commands.md
```

The next acceptance run (Task 10) is this commit's smoke test; `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged` → 0 (the generated table is under `docs/reference/`).

---

### Task 8: The takeover handler — the seven updaters reproduced, and the mode switch — Opus implementer, Opus reviewer

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Fast.lua`
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Fast.lua`
- Create: `testing/tests/kernel/test_kernel_fast.py`

**Interfaces:**
- Consumes: `K.clamp`, `K.max`, `K.min` (Task 3); `NR.server.options`, `NR.server.options.changed` (Task 5); `NR.server.players.onFirstSight`, `.onDeparture`, `.onMinute` (Task 4).
- Produces (kernel): `K.fast.step(inp, out, c)` — reads the per-tick input table `inp`, writes the seven stats' new values and the side-effect requests into `out`, `c` the constants table; allocation-free (both tables are owned by the caller and reused); every field below. `K.fast.defaults()` returns a fresh constants table with the shipped `defines.lua` values. `K.fast.input()` and `K.fast.output()` return fresh zeroed tables of the exact field sets (used once per player at hoist time, and by the tests).
- Produces (server): `NR.server.fast.install()` / `.uninstall()` (add or remove the one closure on `Hook.CalculateStats`), `NR.server.fast.handler(character)` the registered closure, `NR.server.fast.h[username]` the hoisted handle table per player, `NR.server.fast.stats` = `{ calls, failures, disabledAt, sentinelCalls, perPlayer = {username = {calls, failures}} }`, `NR.server.fast.mode` the mode the adapter is running (`1` takeover registered, `2` overlay). Player-modData key `NR_sentinel` (read on the slow clock into `h.sentinel`) makes the handler write `ENDURANCE = 0.4242` every tick, which is X35's arm.

**The arithmetic the kernel reproduces**, from `docs/superpowers/research/jar-calculatestats-updaters.md` (every constant's jar section in brackets; `M` = `getMultiplier()`, `D` = `getDeltaMinutesPerDay()`, `SD` = `getStatsDecreaseMultiplier()`; game-seconds this update = `M × D`, § 9):

| updater | arm | new value | § |
|---|---|---|---|
| endurance stub | always | `lastEndurance := ENDURANCE`; `ENDURANCE := 1` when unlimited-endurance cheat | 7 |
| tripping | — | dropped: nothing reads the angle (#2225) | 5 |
| thirst | asleep, not ghost | `THIRST += thirstSleepingIncrease × SD × M × D × trait` | 1 |
| thirst | awake, not ghost | `THIRST += thirstIncrease × SD × M × run × D × trait × thermoFluids`; `trait` = 2 (High Thirst) × 0.5 (Low Thirst); `run` = 1.2 only when the character is the process's local instance and running, which on a dedicated server is read as 1.0 | 1 |
| thirst | always | `autoDrink()` called after the add, outside both gates | 1 |
| stress | not Deaf | `STRESS += soundStress(x,y,z) × StressFromSoundsMultiplier` | character-stats#updaters, dump @22–@58 |
| stress | parts bitten > 0 / scratched > 0 / infected or fake-infected | each: `STRESS += StressFromBiteOrScratch × M × D` | dump @63–@191 |
| stress | Hemophobic | `STRESS += totalBlood × StressFromHemophobic × (M / 0.8) × D` | dump @199–@245 |
| stress | always | `ANGER −= AngerDecrease × M × D` | dump @253–@276 |
| wake, awake | always | `STRESS −= StressDecrease × M × D` | 2 |
| wake, awake | always | `FATIGUE += FatigueIncrease × SD × max(0.3, 1 − ENDURANCE) × M × D × sleepTrait × thermoFatigue ÷ rest`; `sleepTrait` 0.7 Needs Less Sleep, 1.3 Needs More Sleep (tested second); `rest` 1.5 sitting on ground/furniture or resting | 2 |
| wake, awake | exercising, FOOD_EATEN 0 / > 0 | `HUNGER += (HungerIncreaseWhenExercise / 3 or HungerIncreaseWhenExercise) × SD × appetite × M × D`; `appetite` = `(1 − HUNGER) × 1.5 (Hearty Appetite) × 0.75 (Light Eater)` | 2 |
| wake, awake | not exercising, FOOD_EATEN 0 / > 0 | `HUNGER += HungerIncrease × SD × appetite × M × D` / `HungerIncreaseWhenWellFed × SD × M × D` (no appetite; 0 shipped) | 2 |
| wake, awake | idleness | timer mirror: same square → `timer += M × D` while `timer ≤ 3600`, else `timer = 0`; in combat (`veryClose > 0 or chasing ≥ 3`) → `IDLENESS = 0`; else idle with a square → `+IdleIncrease × M × D` when same square and `timer ≥ 1800`, and `+IdleIncrease / 3 × M × D` when in a room (both may apply); else unless sitting → `−IdleDecrease × M × D`; each through the clamp | 2 |
| wake, asleep (player) | always | `ENDURANCE += ImobileEnduranceIncrease × EndRegen × recoveryMod × M × f`, `f = 2` or `2 × D` when every local player is asleep | 3 |
| wake, asleep | FATIGUE > 0 | `dt = 1 / minutesPerDay / 60 × M / 2` (game-hours); `timeOfSleep += dt`; once `timeOfSleep > delayToSleep`: `FATIGUE −= dt / (7 × t) × 0.3 × f × bed` at or below 0.3, else `dt / (5 × t) × 0.7 × f × bed`; `f` 0.5 Insomniac × 1.4 Night Owl; `t` 0.75 Needs Less / 1.18 Needs More; bed factor by bed type | 3, endurance-fatigue-sleep#sleep |
| wake, asleep | FOOD_EATEN 0 / > 0 | `HUNGER += HungerIncreaseWhileAsleep × SD × appetite × M × D` / `HungerIncreaseWhenWellFed × SD × HungerIncreaseWhileAsleep × SD × M × D` (0 shipped) | 3 |
| morale | always | `ns = clamp(STRESS + NICOTINE_WITHDRAWAL, 0, 1)`; `m = (1 − ns − 0.5) × 1e-4`; `if m > 0 then m += 0.5`; `MORALE += clamp(m, 0, 1)` | 4 |
| fitness | always | `FITNESS = fitnessLevel / 5 − 1` | 6 |

Two engine fields the handler cannot read force mirrors, each a **ruling** carried to the close: (7) `timeOfSleep` and `delayToActuallySleep` have public setters and no getters (§ 3), so the adapter keeps a per-player mirror — at the awake→asleep transition `timeOfSleep := timeOfDay` (what `SleepingEvent.setPlayerFallAsleep` writes) and `delayToSleep := timeOfDay + d × SLEEP_DELAY_FRACTION`, `d` the deterministic part of `doDelayToSleep` (0.3, or 1.0 Insomniac; `+ (1 + 0.2 × PAIN level)` in pain; `× 1.2` under any STRESS moodle; `×` bed factor 1.3/1.25/0.8/0.6/1.6/1.45/1.0; `× 0.5` Night Owl; capped at 2.0) with `SLEEP_DELAY_FRACTION = 0.5` standing for the mean of `Rand.Next(0, d)` — a game choice, labelled, since the vanilla value is random; the mirror is written back through `setTimeOfSleep` each asleep tick so the engine's field tracks the mod's; cost if wrong: the first minutes of a sleep restore fatigue a little early or late, which X34's asleep arm reads as a bounded residual. (8) `idleSquareTime` has a getter and no setter and its updater is private (§ 2), so the handler keeps its own timer for the 1800-second gate, and `BodyDamage.UpdateBoredom`, which reads the engine's frozen field, sees a timer that no longer advances under takeover — a documented divergence Plan 5's mood channel owns; cost if wrong: indoor boredom accrues differently under takeover, which the handler's `limitations` list and the self-report state.

- [ ] **Step 1: Write the failing kernel tests**

`testing/tests/kernel/test_kernel_fast.py` — the expected values are computed in Python from the same formulas, so a test is a second reading of the jar report rather than of the Lua:

```python
import math, pytest

C = dict(thirstIncrease=8.0e-6, thirstSleepingIncrease=1.0e-6, hungerIncrease=9.6e-6, hungerIncreaseWhenWellFed=0.0,
         hungerIncreaseWhileAsleep=1.0e-6, hungerIncreaseWhenExercise=1.92e-5, fatigueIncrease=3.45e-5,
         stressDecrease=3.0e-5, stressFromSoundsMultiplier=2.0e-5, stressFromBiteOrScratch=5.0e-5,
         stressFromHemophobic=3.333e-7, angerDecrease=1.0e-4, idleIncrease=5.0e-4, idleDecrease=6.0e-3,
         imobileEnduranceIncrease=3.1e-5, sleepDelayFraction=0.5)

BASE = dict(M=0.8, D=0.5, sd=1.0, asleep=False, ghost=False, hunger=0.2, thirst=0.1, fatigue=0.1, endurance=0.9,
            stress=0.05, anger=0.02, idleness=0.0, morale=1.0, nicotine=0.0, highThirst=False, lowThirst=False,
            heartyAppetite=False, lightEater=False, needsLess=False, needsMore=False, hemophobic=False, deaf=False,
            insomniac=False, nightOwl=False, sitting=False, foodEaten=0, exercising=False, running=False,
            thermoFatigue=1.0, thermoFluids=1.0, soundStress=0.0, partsBitten=0, partsScratched=0, infected=False,
            fakeInfected=False, totalBlood=0.0, veryClose=0, chasing=0, currentlyIdle=False, hasSquare=True,
            sameSquare=True, inRoom=False, idleTimer=0.0, bedFactor=1.0, timeOfSleep=0.0, delayToSleep=0.0,
            timeOfDay=8.0, minutesPerDay=60.0, endRegen=1.0, recoveryMod=1.0, allAsleep=False, fitnessLevel=5,
            unlimitedEndurance=False, painLevel=0, stressMoodle=0, sleepTransition=False)


def run(host, **kw):
    inp = dict(BASE); inp.update(kw)
    out = host.K.fast.output()
    host.K.fast.step(host.table(inp), out, host.table(C))
    return host.py(out)


def test_awake_idle_vanilla_rates(host):
    o = run(host)
    s = 0.8 * 0.5                                  # game-seconds this update
    assert o["thirst"] == pytest.approx(0.1 + 8.0e-6 * s, rel=1e-12)
    assert o["hunger"] == pytest.approx(0.2 + 9.6e-6 * (1 - 0.2) * s, rel=1e-12)
    assert o["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s, rel=1e-12)      # deficit 0.1 floored to 0.3
    assert o["stress"] == pytest.approx(0.05 - 3.0e-5 * s, rel=1e-12)
    assert o["anger"] == pytest.approx(0.02 - 1.0e-4 * s, rel=1e-12)
    assert o["morale"] == 1.0 and o["fitness"] == 0.0
    assert o["lastEndurance"] == 0.9 and o["endurance"] == 0.9
    assert o["autoDrink"] is True and o["resetIdleness"] is False


def test_thirst_traits_and_thermo(host):
    s = 0.4
    assert run(host, highThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 2 * s, rel=1e-12)
    assert run(host, lowThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 0.5 * s, rel=1e-12)
    assert run(host, highThirst=True, lowThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * s, rel=1e-12)
    assert run(host, thermoFluids=1.5)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 1.5 * s, rel=1e-12)
    assert run(host, running=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 1.2 * s, rel=1e-12)
    assert run(host, ghost=True)["thirst"] == 0.1                      # the ghost gate; autoDrink still runs
    assert run(host, ghost=True)["autoDrink"] is True


def test_hunger_arms(host):
    s, a = 0.4, 0.8
    assert run(host, exercising=True)["hunger"] == pytest.approx(0.2 + 1.92e-5 / 3 * a * s, rel=1e-12)
    assert run(host, exercising=True, foodEaten=2)["hunger"] == pytest.approx(0.2 + 1.92e-5 * a * s, rel=1e-12)
    assert run(host, foodEaten=1)["hunger"] == 0.2                      # well fed: the shipped constant is 0
    assert run(host, heartyAppetite=True)["hunger"] == pytest.approx(0.2 + 9.6e-6 * a * 1.5 * s, rel=1e-12)
    assert run(host, lightEater=True)["hunger"] == pytest.approx(0.2 + 9.6e-6 * a * 0.75 * s, rel=1e-12)
    assert run(host, sd=2.0)["hunger"] == pytest.approx(0.2 + 9.6e-6 * 2.0 * a * s, rel=1e-12)


def test_fatigue_awake_terms(host):
    s = 0.4
    assert run(host, endurance=0.2)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.8 * s, rel=1e-12)
    assert run(host, needsLess=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 0.7, rel=1e-12)
    assert run(host, needsLess=True, needsMore=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 1.3, rel=1e-12)
    assert run(host, sitting=True, thermoFatigue=2.0)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 2.0 / 1.5, rel=1e-12)


def test_stress_terms(host):
    s = 0.4
    o = run(host, soundStress=3.0, partsBitten=1, partsScratched=2, infected=True, hemophobic=True, totalBlood=10.0)
    expect = 0.05 + 3.0 * 2.0e-5 + 3 * (5.0e-5 * s) + 10.0 * 3.333e-7 * (0.8 / 0.8) * 0.5 - 3.0e-5 * s
    assert o["stress"] == pytest.approx(expect, rel=1e-12)
    assert run(host, soundStress=3.0, deaf=True)["stress"] == pytest.approx(0.05 - 3.0e-5 * s, rel=1e-12)
    assert run(host, fakeInfected=True)["stress"] == pytest.approx(0.05 + 5.0e-5 * s - 3.0e-5 * s, rel=1e-12)


def test_idleness_arms(host):
    s = 0.4
    o = run(host, veryClose=1, idleness=0.5)
    assert o["resetIdleness"] is True and o["idleness"] == 0.0
    o = run(host, currentlyIdle=True, idleTimer=1800.0, inRoom=True, idleness=0.1)
    assert o["idleness"] == pytest.approx(0.1 + 5.0e-4 * s + 5.0e-4 / 3 * s, rel=1e-12)
    assert o["idleTimer"] == pytest.approx(1800.0 + s)
    o = run(host, currentlyIdle=True, idleTimer=10.0, idleness=0.1)
    assert o["idleness"] == 0.1
    o = run(host, currentlyIdle=False, sitting=False, idleness=0.1)
    assert o["idleness"] == pytest.approx(0.1 - 6.0e-3 * s, rel=1e-12)
    assert run(host, sameSquare=False, idleTimer=50.0)["idleTimer"] == 0.0
    assert run(host, idleTimer=3600.5)["idleTimer"] == 3600.5          # saturated: no advance above 3600


def test_asleep_arms(host):
    s = 0.4
    o = run(host, asleep=True, thirst=0.1, hunger=0.2, fatigue=0.5, endurance=0.5, timeOfSleep=9.0, delayToSleep=8.5, bedFactor=1.1)
    dt = 1.0 / 60.0 / 60.0 * 0.8 / 2.0
    assert o["thirst"] == pytest.approx(0.1 + 1.0e-6 * s, rel=1e-12)
    assert o["hunger"] == pytest.approx(0.2 + 1.0e-6 * 0.8 * s, rel=1e-12)
    assert o["endurance"] == pytest.approx(0.5 + 3.1e-5 * 1.0 * 1.0 * 0.8 * 2.0, rel=1e-12)
    assert o["fatigue"] == pytest.approx(0.5 - dt / 5.0 * 0.7 * 1.1, rel=1e-12)
    assert o["timeOfSleep"] == pytest.approx(9.0 + dt, rel=1e-12)
    assert o["stress"] == 0.05                                           # no awake decay while asleep
    o = run(host, asleep=True, fatigue=0.2, timeOfSleep=9.0, delayToSleep=8.5, needsMore=True, insomniac=True)
    assert o["fatigue"] == pytest.approx(0.2 - dt / (7.0 * 1.18) * 0.3 * 0.5, rel=1e-12)
    o = run(host, asleep=True, fatigue=0.5, timeOfSleep=8.0, delayToSleep=8.5)
    assert o["fatigue"] == 0.5                                            # the delay gate holds
    assert run(host, asleep=True, allAsleep=True, endurance=0.5)["endurance"] == pytest.approx(0.5 + 3.1e-5 * 0.8 * 2.0 * 0.5, rel=1e-12)


def test_sleep_transition_seeds_the_mirrors(host):
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, insomniac=True, painLevel=2, stressMoodle=1, bedFactor=0.6, nightOwl=True)
    d = min(2.0, (1.0 + (1 + 0.2 * 2)) * 1.2 * 0.6 * 0.5)
    assert o["timeOfSleep"] == pytest.approx(22.0 + 1.0 / 60.0 / 60.0 * 0.8 / 2.0, rel=1e-12)
    assert o["delayToSleep"] == pytest.approx(22.0 + d * 0.5, rel=1e-12)


def test_morale_and_fitness(host):
    assert run(host, stress=0.9)["morale"] == 1.0                        # add of 0 at ns >= 0.5, morale stays
    assert run(host, morale=0.2, stress=0.0)["morale"] == pytest.approx(min(1.0, 0.2 + 0.5 + 0.5 * 1e-4), rel=1e-9)
    assert run(host, fitnessLevel=0)["fitness"] == -1.0 and run(host, fitnessLevel=10)["fitness"] == 1.0


def test_endurance_stub_and_sentinel(host):
    assert run(host, unlimitedEndurance=True, endurance=0.3)["endurance"] == 1.0
    assert run(host, endurance=0.3)["lastEndurance"] == 0.3


def test_every_stat_stays_in_bounds_and_zero_dt_changes_nothing(host):
    o = run(host, M=0.0)
    for k in ("hunger", "thirst", "fatigue", "stress", "anger", "idleness", "endurance"):
        assert o[k] == BASE[k]
    o = run(host, thirst=0.9999999, hunger=0.9999999, stress=0.9999999, soundStress=1e9, M=1e6)
    for k in ("hunger", "thirst", "stress", "fatigue", "idleness", "morale"):
        assert 0.0 <= o[k] <= 1.0
    assert -1.0 <= o["fitness"] <= 1.0


def test_defaults_match_defines(host):
    d = host.py(host.K.fast.defaults())
    assert d == C
```

Run: `python -m pytest testing/tests/kernel -q` → FAIL (`fast` is nil).

- [ ] **Step 2: Write the kernel**

`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Fast.lua` (every line of it is inside the coverage gate; the field sets are the contract the adapter fills):

```lua
-- NR_Kernel_Fast.lua -- the fast clock's arithmetic: the seven updaters IsoGameCharacter.calculateStats
-- runs when Hook.CalculateStats does not answer true, reproduced from
-- docs/superpowers/research/jar-calculatestats-updaters.md with no nutrition term (Plan 1, vanilla
-- parity). Pure: `inp`, `out` and `c` are tables the adapter owns and reuses; nothing here allocates
-- per call and nothing names a Java global. Constants carry their register id or jar section.
local K = NutritionRevamp.kernel
K.fast = {}
local F = K.fast
local clamp, max = K.clamp, K.max

-- The shipped defines.lua values (jar report "Shared constants" table; media/lua/shared/defines.lua).
-- Outside the fast-path region: called once at install, never per tick.
function F.defaults()
    return {
        thirstIncrease = 8.0e-6,                 -- #0476; defines.lua:9
        thirstSleepingIncrease = 1.0e-6,         -- #0477; :10
        hungerIncrease = 9.6e-6,                 -- #0470; :14
        hungerIncreaseWhenWellFed = 0.0,         -- #0473; :15
        hungerIncreaseWhileAsleep = 1.0e-6,      -- #0472; :17
        hungerIncreaseWhenExercise = 1.92e-5,    -- #0471; :16
        fatigueIncrease = 3.45e-5,               -- #2270; :19
        stressDecrease = 3.0e-5,                 -- jar § 2; :21
        stressFromSoundsMultiplier = 2.0e-5,     -- #2231; :27
        stressFromBiteOrScratch = 5.0e-5,        -- #2231; :28
        stressFromHemophobic = 3.333e-7,         -- #2231; :29
        angerDecrease = 1.0e-4,                  -- #2231; :32
        idleIncrease = 5.0e-4,                   -- jar § 2; :55
        idleDecrease = 6.0e-3,                   -- jar § 2; :56
        imobileEnduranceIncrease = 3.1e-5,       -- #2258; :7
        sleepDelayFraction = 0.5,                -- Plan 1 ruling 7: the mean of Rand.Next(0, d); a game choice
    }
end

-- The input table the adapter fills every tick (one per player, allocated once at hoist time).
function F.input()
    return { M = 0, D = 0, sd = 1, asleep = false, ghost = false,
             hunger = 0, thirst = 0, fatigue = 0, endurance = 1, stress = 0, anger = 0, idleness = 0, morale = 1, nicotine = 0,
             highThirst = false, lowThirst = false, heartyAppetite = false, lightEater = false, needsLess = false,
             needsMore = false, hemophobic = false, deaf = false, insomniac = false, nightOwl = false,
             sitting = false, foodEaten = 0, exercising = false, running = false,
             thermoFatigue = 1, thermoFluids = 1, soundStress = 0, partsBitten = 0, partsScratched = 0,
             infected = false, fakeInfected = false, totalBlood = 0, veryClose = 0, chasing = 0,
             currentlyIdle = false, hasSquare = false, sameSquare = false, inRoom = false, idleTimer = 0,
             bedFactor = 1, timeOfSleep = 0, delayToSleep = 0, timeOfDay = 0, minutesPerDay = 60,
             endRegen = 1, recoveryMod = 1, allAsleep = false, fitnessLevel = 0, unlimitedEndurance = false,
             painLevel = 0, stressMoodle = 0, sleepTransition = false }
end

-- The output table: the seven stats' new values plus the side-effect requests and the mirrors.
function F.output()
    return { hunger = 0, thirst = 0, fatigue = 0, endurance = 1, lastEndurance = 1, stress = 0, anger = 0,
             idleness = 0, resetIdleness = false, morale = 1, fitness = 0, autoDrink = true,
             idleTimer = 0, timeOfSleep = 0, delayToSleep = 0 }
end

-- @fastpath
-- One update. s = M × D is the game-seconds elapsed (jar § 9). Every write below passes K.clamp so the
-- adapter hands the engine a value the stat's own clamp leaves alone (#2208).
function F.step(inp, out, c)
    local M, D, sd = inp.M, inp.D, inp.sd
    local s = M * D

    -- 7. the endurance stub: stamp, then the cheat (#2215)
    out.lastEndurance = inp.endurance
    local endurance = inp.endurance
    if inp.unlimitedEndurance then endurance = 1 end

    -- 1. thirst (#0476, #0477, #0486, #0478, #0560)
    local thirst = inp.thirst
    if not inp.ghost then
        local trait = 1
        if inp.highThirst then trait = trait * 2 end
        if inp.lowThirst then trait = trait * 0.5 end
        if inp.asleep then
            thirst = thirst + c.thirstSleepingIncrease * sd * M * D * trait
        else
            local run = 1
            if inp.running then run = 1.2 end
            thirst = thirst + c.thirstIncrease * sd * M * run * D * trait * inp.thermoFluids
        end
    end
    out.thirst = clamp(thirst, 0, 1)
    out.autoDrink = true                                     -- #2250: called on every pass, outside both gates

    -- stress updater (#2220, #2230, #2226, #2231)
    local stress = inp.stress
    if not inp.deaf then stress = stress + inp.soundStress * c.stressFromSoundsMultiplier end
    if inp.partsBitten > 0 then stress = stress + c.stressFromBiteOrScratch * s end
    if inp.partsScratched > 0 then stress = stress + c.stressFromBiteOrScratch * s end
    if inp.infected or inp.fakeInfected then stress = stress + c.stressFromBiteOrScratch * s end
    if inp.hemophobic then stress = stress + inp.totalBlood * c.stressFromHemophobic * (M / 0.8) * D end
    out.anger = clamp(inp.anger - c.angerDecrease * s, 0, 1)

    -- wake state
    local hunger, fatigue, idleness = inp.hunger, inp.fatigue, inp.idleness
    local appetite = 1 - inp.hunger                          -- #0474, rebuilt: getAppetiteMultiplier is protected
    if inp.heartyAppetite then appetite = appetite * 1.5 end
    if inp.lightEater then appetite = appetite * 0.75 end
    out.resetIdleness = false
    out.idleTimer = inp.idleTimer
    out.timeOfSleep = inp.timeOfSleep
    out.delayToSleep = inp.delayToSleep
    if inp.asleep then
        -- 3. IsoPlayer.updateStats_Sleeping: endurance (#2261), fatigue (#2276, #2277), hunger (#0472, #0473)
        local f = 2
        if inp.allAsleep then f = 2 * D end
        endurance = endurance + c.imobileEnduranceIncrease * inp.endRegen * inp.recoveryMod * M * f
        local dt = 1 / inp.minutesPerDay / 60 * M / 2         -- game-hours this update (jar § 3, § 9)
        if inp.sleepTransition then                           -- Plan 1 ruling 7: the two mirrors
            local d = 0.3
            if inp.insomniac then d = 1.0 end
            if inp.painLevel > 0 then d = d + (1 + 0.2 * inp.painLevel) end
            if inp.stressMoodle > 0 then d = d * 1.2 end
            d = d * inp.bedFactor
            if inp.nightOwl then d = d * 0.5 end
            if d > 2.0 then d = 2.0 end
            out.timeOfSleep = inp.timeOfDay
            out.delayToSleep = inp.timeOfDay + d * c.sleepDelayFraction
        end
        if fatigue > 0 then
            local ff = 1
            if inp.insomniac then ff = ff * 0.5 end
            if inp.nightOwl then ff = ff * 1.4 end
            out.timeOfSleep = out.timeOfSleep + dt
            if out.timeOfSleep > out.delayToSleep then
                local t = 1
                if inp.needsLess then t = t * 0.75 elseif inp.needsMore then t = t * 1.18 end
                if fatigue <= 0.3 then
                    fatigue = fatigue - dt / (7 * t) * 0.3 * ff * inp.bedFactor
                else
                    fatigue = fatigue - dt / (5 * t) * 0.7 * ff * inp.bedFactor
                end
            end
        end
        if inp.foodEaten == 0 then
            hunger = hunger + c.hungerIncreaseWhileAsleep * sd * appetite * s
        else
            hunger = hunger + c.hungerIncreaseWhenWellFed * sd * c.hungerIncreaseWhileAsleep * sd * s
        end
    else
        -- 2. updateStats_Awake: stress decay, fatigue, hunger, idleness (jar § 2; #2270, #2271, #0470, #0471, #0473)
        stress = stress - c.stressDecrease * s
        local endDef = max(0.3, 1 - inp.endurance)
        local sleepTrait = 1
        if inp.needsLess then sleepTrait = 0.7 end
        if inp.needsMore then sleepTrait = 1.3 end
        local rest = 1
        if inp.sitting then rest = 1.5 end
        fatigue = fatigue + c.fatigueIncrease * sd * endDef * s * sleepTrait * inp.thermoFatigue / rest
        if inp.exercising then
            if inp.foodEaten == 0 then
                hunger = hunger + c.hungerIncreaseWhenExercise / 3 * sd * appetite * s
            else
                hunger = hunger + c.hungerIncreaseWhenExercise * sd * appetite * s
            end
        else
            if inp.foodEaten == 0 then
                hunger = hunger + c.hungerIncrease * sd * appetite * s
            else
                hunger = hunger + c.hungerIncreaseWhenWellFed * sd * s
            end
        end
        -- the idle-square timer mirror (Plan 1 ruling 8), then idleness
        if inp.sameSquare then
            if out.idleTimer <= 3600 then out.idleTimer = out.idleTimer + s end
        else
            out.idleTimer = 0
        end
        if inp.veryClose > 0 or inp.chasing >= 3 then
            idleness = 0
            out.resetIdleness = true
        elseif inp.currentlyIdle and inp.hasSquare then
            if inp.sameSquare and out.idleTimer >= 1800 then idleness = clamp(idleness + c.idleIncrease * s, 0, 1) end
            if inp.inRoom then idleness = clamp(idleness + c.idleIncrease / 3 * s, 0, 1) end
        elseif not inp.sitting then
            idleness = clamp(idleness - c.idleDecrease * s, 0, 1)
        end
    end
    out.hunger = clamp(hunger, 0, 1)
    out.fatigue = clamp(fatigue, 0, 1)
    out.stress = clamp(stress, 0, 1)
    out.idleness = clamp(idleness, 0, 1)
    out.endurance = clamp(endurance, 0, 1)

    -- 4. morale (jar § 4): never lowered, pinned at 1 within two updates
    local ns = clamp(inp.stress + inp.nicotine, 0, 1)
    local m = (1 - ns - 0.5) * 1e-4
    if m > 0 then m = m + 0.5 end
    out.morale = clamp(inp.morale + clamp(m, 0, 1), 0, 1)

    -- 6. fitness (#2223)
    out.fitness = clamp(inp.fitnessLevel / 5 - 1, -1, 1)
end
-- @endfastpath
```

Run: `python -m pytest testing/tests/kernel -q` → all green including the coverage gate (every branch above is reached by a test; if the gate names a line, add the test that reaches it rather than deleting the line). `python tools/hotpath_lint.py mod` → 0 (only `F.step` sits inside the region; `F.defaults`, `F.input` and `F.output` construct tables and run once per player at hoist time, outside it).

- [ ] **Step 3: Write the adapter**

`mod/NutritionRevamp/common/media/lua/server/NR_Server_Fast.lua`. The reads it makes per tick are the engine getters the jar report's § 12 marks public; each is indexed once per player at hoist time into `h` and called through the hoisted handle (`h.stats:get(h.HUNGER)` is a method call on a hoisted receiver, which the lint allows). Members the build lacks are recorded in `h.missing` and their term disabled.

```lua
-- NR_Server_Fast.lua -- the fast clock: the Hook.CalculateStats takeover handler (spec § 4.1).
-- Registration is itself the takeover (#2238): the hook answers true for any registrant, the
-- handler's return is discarded, and a raise leaves the seven stats frozen for that update -- so
-- the body runs inside one rim guard (Plan 1 ruling 4) and, after three consecutive failures for
-- a player, the handler removes itself and vanilla resumes (ruling 9, logged at level 1).
-- Every Java member is hoisted once per player (#0935); the per-tick body re-indexes nothing.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.fast = { h = {}, mode = 2, closure = nil, registered = false,
                   stats = { calls = 0, failures = 0, disabledAt = nil, sentinelCalls = 0, perPlayer = {} },
                   limitations = { "idle-square timer mirrored (engine field frozen under takeover; boredom reads it)",
                                   "sleep delay mirrored with sleepDelayFraction (vanilla draws it at random)",
                                   "tripping angle dropped (nothing reads it)" } }
local FAST = NR.server.fast
local C = K.fast.defaults()

-- The ZomboidGlobals Lua table is what the Java constants are loaded from (defines.lua); a server
-- that edits it is followed. Read once at install, never per tick.
local GLOBAL_KEYS = { thirstIncrease = "ThirstIncrease", thirstSleepingIncrease = "ThirstSleepingIncrease",
    hungerIncrease = "HungerIncrease", hungerIncreaseWhenWellFed = "HungerIncreaseWhenWellFed",
    hungerIncreaseWhileAsleep = "HungerIncreaseWhileAsleep", hungerIncreaseWhenExercise = "HungerIncreaseWhenExercise",
    fatigueIncrease = "FatigueIncrease", stressDecrease = "StressDecrease",
    stressFromSoundsMultiplier = "StressFromSoundsMultiplier", stressFromBiteOrScratch = "StressFromBiteOrScratch",
    stressFromHemophobic = "StressFromHemophobic", angerDecrease = "AngerDecrease",
    idleIncrease = "IdleIncrease", idleDecrease = "IdleDecrease", imobileEnduranceIncrease = "ImobileEnduranceIncrease" }

local function readConstants()
    local zg = ZomboidGlobals
    if type(zg) ~= "table" then return end
    for field, key in pairs(GLOBAL_KEYS) do
        if type(zg[key]) == "number" then C[field] = zg[key] end
    end
end

local BED = { badBed = 0.9, badBedPillow = 0.95, averageBedPillow = 1.05, goodBed = 1.1, goodBedPillow = 1.15,
              floor = 0.6, floorPillow = 0.75 }                       -- #2276
local DELAY_BED = { badBed = 1.3, badBedPillow = 1.25, goodBed = 0.8, goodBedPillow = 0.6, floor = 1.6,
                    floorPillow = 1.45, averageBedPillow = 1.0 }     -- jar § 3 doDelayToSleep

-- Hoist: one table of handles per player, filled at first sight. A member that is nil here disables
-- its term (recorded in h.missing) rather than raising later.
local function hoist(username, p)
    local h = { username = username, p = p, inp = K.fast.input(), out = K.fast.output(), missing = {},
                sentinel = false, wasAsleep = false, calls = 0, fails = 0 }
    local function want(obj, name)
        if obj == nil then h.missing[#h.missing + 1] = name; return nil end
        local m = obj[name]
        if m == nil then h.missing[#h.missing + 1] = name end
        return m
    end
    h.stats = p:getStats()
    h.get, h.set = want(h.stats, "get"), want(h.stats, "set")
    h.setLastEndurance = want(h.stats, "setLastEndurance")
    h.resetStat = want(h.stats, "reset")
    h.getNumVeryClose, h.getNumChasing = want(h.stats, "getNumVeryCloseZombies"), want(h.stats, "getNumChasingZombies")
    h.traits = p:getCharacterTraits()
    h.traitGet = want(h.traits, "get")
    h.moodles = p:getMoodles()
    h.moodleLevel = want(h.moodles, "getMoodleLevel")
    h.bd = p:getBodyDamage()
    h.thermo = h.bd and h.bd:getThermoregulator() or nil
    h.getFatigueMult, h.getFluidsMult = want(h.thermo, "getFatigueMultiplier"), want(h.thermo, "getFluidsMultiplier")
    h.partsBitten, h.partsScratched = want(h.bd, "getNumPartsBitten"), want(h.bd, "getNumPartsScratched")
    h.isInfected, h.isFakeInfected = want(h.bd, "IsInfected"), want(h.bd, "IsFakeInfected")
    h.isAsleep, h.isGhost = want(p, "isAsleep"), want(p, "isGhostMode")
    h.isSitGround, h.isSitFurniture, h.isResting = want(p, "isSitOnGround"), want(p, "isSittingOnFurniture"), want(p, "isResting")
    h.IsRunning, h.isPlayerMoving, h.isCurrentState = want(p, "IsRunning"), want(p, "isPlayerMoving"), want(p, "isCurrentState")
    h.isCurrentlyIdle, h.getCurrentSquare, h.getLastSquare = want(p, "isCurrentlyIdle"), want(p, "getCurrentSquare"), want(p, "getLastSquare")
    h.getTotalBlood, h.getBedType, h.getPerkLevel = want(p, "getTotalBlood"), want(p, "getBedType"), want(p, "getPerkLevel")
    h.isUnlimited, h.autoDrink, h.setTimeOfSleep = want(p, "isUnlimitedEndurance"), want(p, "autoDrink"), want(p, "setTimeOfSleep")
    h.getRecoveryMod, h.getX, h.getY, h.getZ = want(p, "getRecoveryMod"), want(p, "getX"), want(p, "getY"), want(p, "getZ")
    h.gt = getGameTime and getGameTime() or nil
    h.getMult, h.getDMPD, h.getMPD, h.getTOD = want(h.gt, "getMultiplier"), want(h.gt, "getDeltaMinutesPerDay"), want(h.gt, "getMinutesPerDay"), want(h.gt, "getTimeOfDay")
    h.so = getSandboxOptions and getSandboxOptions() or nil
    h.getSD, h.getEndRegen = want(h.so, "getStatsDecreaseMultiplier"), want(h.so, "getEnduranceRegenMultiplier")
    h.wsm = getWorldSoundManager and getWorldSoundManager() or nil
    h.getStressFromSounds = want(h.wsm, "getStressFromSounds")
    h.swipe = SwipeStatePlayer and SwipeStatePlayer.instance and SwipeStatePlayer.instance() or nil
    h.fitnessPerk = Perks and Perks.Fitness or nil
    -- the enum handles (CharacterStat, MoodleType, CharacterTrait are exposed, #2248)
    h.HUNGER, h.THIRST, h.FATIGUE, h.ENDURANCE = CharacterStat.HUNGER, CharacterStat.THIRST, CharacterStat.FATIGUE, CharacterStat.ENDURANCE
    h.STRESS, h.ANGER, h.IDLENESS, h.MORALE = CharacterStat.STRESS, CharacterStat.ANGER, CharacterStat.IDLENESS, CharacterStat.MORALE
    h.NICOTINE, h.FITNESS = CharacterStat.NICOTINE_WITHDRAWAL, CharacterStat.FITNESS
    h.FOOD_EATEN, h.PAIN, h.STRESSM = MoodleType.FOOD_EATEN, MoodleType.Pain, MoodleType.Stress
    h.T = { highThirst = CharacterTrait.HIGH_THIRST, lowThirst = CharacterTrait.LOW_THIRST,
            heartyAppetite = CharacterTrait.HEARTY_APPETITE, lightEater = CharacterTrait.LIGHT_EATER,
            needsLess = CharacterTrait.NEEDS_LESS_SLEEP, needsMore = CharacterTrait.NEEDS_MORE_SLEEP,
            hemophobic = CharacterTrait.HEMOPHOBIC, deaf = CharacterTrait.DEAF,
            insomniac = CharacterTrait.INSOMNIAC, nightOwl = CharacterTrait.NIGHT_OWL }
    if #h.missing > 0 then
        NR.log.say(1, "fast: " .. username .. " missing members: " .. table.concat(h.missing, ", ") .. " -- their terms are disabled")
    end
    FAST.stats.perPlayer[username] = { calls = 0, failures = 0 }
    return h
end

-- @hoisted h, inp, out, stats, traitGet, moodleLevel, K
-- @fastpath
local function body(h)
    local p, inp, out, stats = h.p, h.inp, h.out, h.stats
    local get = h.get
    inp.M = h.getMult(h.gt)
    inp.D = h.getDMPD(h.gt)
    inp.minutesPerDay = h.getMPD(h.gt)
    inp.timeOfDay = h.getTOD(h.gt)
    inp.sd = h.getSD(h.so)
    inp.endRegen = h.getEndRegen(h.so)
    inp.hunger = get(stats, h.HUNGER)
    inp.thirst = get(stats, h.THIRST)
    inp.fatigue = get(stats, h.FATIGUE)
    inp.endurance = get(stats, h.ENDURANCE)
    inp.stress = get(stats, h.STRESS)
    inp.anger = get(stats, h.ANGER)
    inp.idleness = get(stats, h.IDLENESS)
    inp.morale = get(stats, h.MORALE)
    inp.nicotine = get(stats, h.NICOTINE)
    local asleep = h.isAsleep(p)
    inp.sleepTransition = asleep and not h.wasAsleep
    h.wasAsleep = asleep
    inp.asleep = asleep
    inp.ghost = h.isGhost(p)
    local T, tg = h.T, h.traitGet
    inp.highThirst = tg(h.traits, T.highThirst)
    inp.lowThirst = tg(h.traits, T.lowThirst)
    inp.heartyAppetite = tg(h.traits, T.heartyAppetite)
    inp.lightEater = tg(h.traits, T.lightEater)
    inp.needsLess = tg(h.traits, T.needsLess)
    inp.needsMore = tg(h.traits, T.needsMore)
    inp.hemophobic = tg(h.traits, T.hemophobic)
    inp.deaf = tg(h.traits, T.deaf)
    inp.insomniac = tg(h.traits, T.insomniac)
    inp.nightOwl = tg(h.traits, T.nightOwl)
    inp.sitting = h.isSitGround(p) or h.isSitFurniture(p) or h.isResting(p)
    inp.foodEaten = h.moodleLevel(h.moodles, h.FOOD_EATEN)
    inp.painLevel = h.moodleLevel(h.moodles, h.PAIN)
    inp.stressMoodle = h.moodleLevel(h.moodles, h.STRESSM)
    inp.exercising = (h.IsRunning(p) and h.isPlayerMoving(p)) or (h.swipe ~= nil and h.isCurrentState(p, h.swipe))
    inp.running = false                                   -- the local-instance test is false on a dedicated server (jar § 1)
    inp.thermoFatigue = h.getFatigueMult and h.getFatigueMult(h.thermo) or 1
    inp.thermoFluids = h.getFluidsMult and h.getFluidsMult(h.thermo) or 1
    inp.soundStress = h.getStressFromSounds and h.getStressFromSounds(h.wsm, h.getX(p), h.getY(p), h.getZ(p)) or 0
    inp.partsBitten = h.partsBitten and h.partsBitten(h.bd) or 0
    inp.partsScratched = h.partsScratched and h.partsScratched(h.bd) or 0
    inp.infected = h.isInfected and h.isInfected(h.bd) or false
    inp.fakeInfected = h.isFakeInfected and h.isFakeInfected(h.bd) or false
    inp.totalBlood = h.getTotalBlood(p)
    inp.veryClose = h.getNumVeryClose(stats)
    inp.chasing = h.getNumChasing(stats)
    inp.currentlyIdle = h.isCurrentlyIdle(p)
    local sq = h.getCurrentSquare(p)
    inp.hasSquare = sq ~= nil
    inp.sameSquare = sq ~= nil and sq == h.getLastSquare(p)
    inp.inRoom = sq ~= nil and sq:isInARoom()
    inp.idleTimer = out.idleTimer
    inp.timeOfSleep = out.timeOfSleep
    inp.delayToSleep = out.delayToSleep
    inp.bedFactor = BED[h.getBedType(p)] or 1
    inp.recoveryMod = h.getRecoveryMod(p)
    inp.allAsleep = IsoPlayer.allPlayersAsleep()
    inp.fitnessLevel = h.getPerkLevel(p, h.fitnessPerk)
    inp.unlimitedEndurance = h.isUnlimited(p)

    K.fast.step(inp, out, C)

    h.setLastEndurance(stats, out.lastEndurance)
    local set = h.set
    set(stats, h.THIRST, out.thirst)
    set(stats, h.STRESS, out.stress)
    set(stats, h.ANGER, out.anger)
    set(stats, h.HUNGER, out.hunger)
    set(stats, h.FATIGUE, out.fatigue)
    set(stats, h.IDLENESS, out.idleness)
    set(stats, h.MORALE, out.morale)
    set(stats, h.FITNESS, out.fitness)
    if asleep then
        set(stats, h.ENDURANCE, out.endurance)            -- the sleep regeneration arm the hook skips (jar § 3)
        h.setTimeOfSleep(p, out.timeOfSleep)
    elseif inp.unlimitedEndurance then
        set(stats, h.ENDURANCE, 1)
    end
    if h.sentinel then                                    -- X35's arm: the endurance write the push should carry
        set(stats, h.ENDURANCE, 0.4242)
        FAST.stats.sentinelCalls = FAST.stats.sentinelCalls + 1
    end
    h.autoDrink(p)                                        -- #2250: vanilla calls it on every pass
end
-- @endfastpath

-- The hook hands the character and nothing else (jar § 8); its username is the key into the hoisted
-- handles. getUsername is a Java member on an object this file did not hoist, so it is read behind
-- the guard, outside the region; the body's rim guard is the one pcall the region allows.
local function keyOf(character)
    local ok, username = pcall(character.getUsername, character)
    if ok then return username end
    return nil
end

-- @fastpath
local function handler(character)
    local username = keyOf(character)
    if username == nil then return end
    local h = FAST.h[username]
    if h == nil then return end                           -- a character the slow clock has not seen yet
    h.calls = h.calls + 1
    FAST.stats.calls = FAST.stats.calls + 1
    local ok, err = pcall(body, h)                        -- @rimguard
    if ok then
        h.fails = 0
        return
    end
    h.fails = h.fails + 1
    FAST.stats.failures = FAST.stats.failures + 1
    FAST.stats.perPlayer[username].failures = h.fails
    FAST.lastError = err
    if h.fails >= 3 then FAST.disable(username) end
end
-- @endfastpath

-- Outside the region: the failure is logged with its message (string concatenation) on the slow
-- clock, which reads FAST.lastError and the per-player failure counts once a minute.
```

The `keyOf` call inside the region is a plain Lua function call (no `:`), which the lint allows; `FAST.disable(username)` is likewise a table-field call rather than a method call. The slow-clock hook added below logs `FAST.lastError` at level 2 once per minute while it is non-nil and clears it, so the per-tick body never builds a string.

```lua
function FAST.install()
    if FAST.registered then return true end
    if Hook == nil or Hook.CalculateStats == nil or Hook.CalculateStats.Add == nil then
        NR.log.say(1, "fast: Hook.CalculateStats is absent; takeover unavailable")
        return false
    end
    readConstants()
    FAST.closure = FAST.closure or function(character) handler(character) end
    Hook.CalculateStats.Add(FAST.closure)                 -- a dot, never a colon (jar § 11)
    FAST.registered, FAST.mode = true, 1
    NR.log.say(1, "fast: takeover handler registered")
    return true
end

function FAST.uninstall()
    if not FAST.registered then return end
    if Hook ~= nil and Hook.CalculateStats ~= nil and Hook.CalculateStats.Remove ~= nil then
        Hook.CalculateStats.Remove(FAST.closure)          -- the same closure object (jar § 11)
    end
    FAST.registered, FAST.mode = false, 2
    NR.log.say(1, "fast: takeover handler removed")
end

function FAST.disable(username)
    FAST.stats.disabledAt = "three consecutive failures for " .. tostring(username)
    FAST.uninstall()
    NR.log.say(1, "fast: DISABLED (" .. FAST.stats.disabledAt .. "); vanilla stat update resumed")
end

-- Mode: 1 takeover registers; 2 overlay registers nothing (and in this plan writes nothing).
local function applyMode(opts)
    if FAST.stats.disabledAt ~= nil then return end
    if opts.mode == 1 then FAST.install() else FAST.uninstall() end
end

NR.server.players.onFirstSight[#NR.server.players.onFirstSight + 1] = function(username, player)
    if player ~= nil then FAST.h[username] = hoist(username, player) end
end
NR.server.players.onDeparture[#NR.server.players.onDeparture + 1] = function(username)
    FAST.h[username] = nil
end
-- X35's sentinel flag and the per-player failure count are read on the slow clock, never per tick.
NR.server.players.onMinute[#NR.server.players.onMinute + 1] = function(username, player)
    local h = FAST.h[username]
    if h == nil then return end
    local okMd, md = NR.call(player, "getModData")
    h.sentinel = okMd and md ~= nil and (md.NR_sentinel == 1 or md.NR_sentinel == "1")
    FAST.stats.perPlayer[username].calls = h.calls
    if FAST.lastError ~= nil then
        NR.log.say(2, "fast: handler failed (" .. tostring(FAST.stats.failures) .. " so far): " .. tostring(FAST.lastError))
        FAST.lastError = nil
    end
end
NR.server.options.changed[#NR.server.options.changed + 1] = function(old, new) applyMode(new) end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        applyMode(NR.server.options)
    end)
end
```

`NR_Server_Options.lua`'s `OnServerStarted` handler runs before this file's (both register at file scope; `NR_Server_Fast` sorts before `NR_Server_Options`, so register this file's handler to read options itself: call `NR.server.readOptions("OnServerStarted")` at the top of the handler above before `applyMode`, which makes the order irrelevant). Self-report: extend `NR.selfReport` in `NR_Server_Options.lua` to append `" hook=" .. tostring(NR.server.fast and NR.server.fast.registered)` and `" limitations=" .. #NR.server.fast.limitations`.

- [ ] **Step 4: Lints, balance, tests**

Run: `python tools/kahlua_lint.py mod && python tools/hotpath_lint.py mod && python tools/luabalance.py mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Fast.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Fast.lua && python -m pytest tools/tests testing/tests -q`
Expected: `0 findings` twice (the hoist function uses `table.concat` and `#` on Lua tables outside any region; the `body` region's only method calls are on `h.*`, `stats`, `traitGet`, `moodleLevel`, `K` receivers named in `@hoisted`, and `sq:isInARoom()` — add `sq` to the hoisted list, it is a local the body reads from a hoisted handle), balanced, 474 passed (462 + 12).

- [ ] **Step 5: Commit**

```bash
git add mod/NutritionRevamp testing/tests/kernel/test_kernel_fast.py
git commit -m "Mod: the CalculateStats takeover handler reproducing the seven updaters; the mode switch" -- mod/NutritionRevamp testing/tests/kernel/test_kernel_fast.py
```

---

### Task 9: Profiles and the three probe mods — Sonnet implementer, Sonnet reviewer

**Files:**
- Create: `testing/profiles/nr-accept.toml`, `nr-takeover.toml`, `nr-overlay.toml`, `x13-calcstats.toml`, `x13-nutrition-off.toml`, `x13-nutrition-on.toml`, `x13-weight-drift.toml` (identical to `x13-nutrition-off.toml` but described for X41), `x13-persist.toml`, `x13-traits.toml`, `x13-swtraits.toml`, `x13-ssread.toml`
- Create: `testing/experiments/TKX_CalcStats/42.20/mod.info`, `…/media/lua/shared/TKX_CalcStats.lua`, `…/media/lua/server/TKX_CalcStats_Server.lua`, `…/media/lua/client/TKX_CalcStats_Client.lua`; `testing/experiments/TKX_TraitProbe/42.20/mod.info`, `…/media/scripts/TKX_TraitProbe_character_traits.txt`, `…/media/registries.lua`, `…/media/lua/shared/TKX_TraitProbe.lua`, `…/media/lua/server/TKX_TraitProbe_Server.lua`; `testing/experiments/TKX_SSRead/42.20/mod.info`, `…/media/lua/client/TKX_SSRead.lua`
- Modify: `testing/profiles/README.md` (one line per profile, in the file's running-prose shape)

**Interfaces:** every profile pins `fixture = "default"`, lists `PZTestKit` first, names the mod by `path = "mod/NutritionRevamp"` (repo-relative) and carries `[[verify]]` rows certain to pass if the mod loaded (`#2050`): server `lua.global PZTestKit.version` first (the walk control, #1760), then server `lua.global NutritionRevamp.version` expecting `"0.1.0"`, then the same pair on the client (#1825).

- [ ] **Step 1: The mod's profiles**

`nr-accept.toml`: the four rows above, `run = { hold = 60 }`, no sandbox block. `nr-takeover.toml`: the same plus `[sandbox] DayLength = 1` (a game-hour is 37.5 s, X34's cadence) and `[sandbox.NR] Mode = 1`, `[client] timeout = 240`. `nr-overlay.toml`: as takeover with `[sandbox.NR] Mode = 2`. The nested block is what Task 6 made settable.

- [ ] **Step 2: `TKX_CalcStats` (X32, X46)**

`shared/TKX_CalcStats.lua`: `TKX_CalcStats = { version = 1, calls = 0, callsA = 0, callsB = 0, side = "?" }` by plain assignment. `server/TKX_CalcStats_Server.lua`: nil-checked `isServer()`; three closures — `noop` (bumps `calls`, returns nothing), `A` (bumps `callsA`, returns true), `B` (bumps `callsB`, returns false) — and an `OnTick` watcher that walks `getOnlinePlayers()` with `size()`/`get(i)`, reads player-modData keys `TKX_calc`, `TKX_hookA`, `TKX_hookB` (string or number `1` → wanted), and adds or removes each closure through `Hook.CalculateStats.Add` / `.Remove` (dot call, the same closure object) when the wanted state differs from the installed flag it keeps; the no-handler arm therefore has an empty callback list (experiments.md X32: "a flag read inside a registered handler cannot make the no-handler arm"). `client/TKX_CalcStats_Client.lua`: adds `noop` at file scope when `isClient()` is true, so the client's `calls` answers the both-sides half. `mod.info`: `name=TKX CalcStats`, `id=TKX_CalcStats`, `description=Plan 1 experiment: Hook.CalculateStats registrant counts (X32, X46). Test profiles only.`, `modversion=1.0`, `versionMin=42.0.0`.

`x13-calcstats.toml`: PZTestKit + `TKX_CalcStats` (`path = "testing/experiments/TKX_CalcStats"`), `[sandbox] DayLength = 1`, `[client] timeout = 240`, verify: server `lua.global TKX_CalcStats.version` expecting `1`, client the same.

- [ ] **Step 3: `TKX_TraitProbe` (X4's registered-trait arm; X42's grant)**

`media/registries.lua` (the shape SomewhatTraits uses at `media/registries.lua:48`): `TKX_TraitProbe_Traits = { probe = CharacterTrait.register("TKX:Probe") }`. `media/scripts/TKX_TraitProbe_character_traits.txt`:

```
module TKX
{
    character_trait_definition TKX:Probe
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = TKX:Probe,
        Cost = 0,
        UIName = UI_trait_TKXProbe,
        UIDescription = UI_trait_TKXProbe_Desc,
    }
}
```

`shared/TKX_TraitProbe.lua`: `TKX_TraitProbe = { version = 1, grants = 0, removes = 0, lastId = "" }`. `server/TKX_TraitProbe_Server.lua`: nil-checked `isServer()`; an `OnTick` watcher reading player-modData key `TKX_grant` (a string: a registry id such as `TKX:Probe` or `SWTraits:SWAdaptiveMetabolism`, or `-<id>` to remove); resolves it with `CharacterTrait.get(ResourceLocation.of(id))` behind the index-first guard (fallback `CharacterTrait[id]` for a vanilla static name), adds or removes through `getCharacterTraits():add/remove`, stamps `TKX_TraitProbe.lastId`, bumps the counter, clears the key, and when key `TKX_push` is `1` calls `sendSyncPlayerFields(player, 2)` and clears that too. `mod.info` as above with id `TKX_TraitProbe`.

`x13-traits.toml`: PZTestKit + `TKX_TraitProbe`, no sandbox, verify: server `lua.global TKX_TraitProbe.version` expecting `1`, server `lua.global TKX_TraitProbe_Traits.probe` expecting `"resolved": true`. `x13-swtraits.toml`: PZTestKit, then `SomewhatTraits` and `SomewhatTraitsCore` (`workshop_id = "3498347699"` with `id` picking each), then `TKX_TraitProbe`; the fixture's day length; verify: server `lua.global SWTraits.traits` expecting `"resolved": true`, server `lua.global TKX_TraitProbe.version`.

- [ ] **Step 4: `TKX_SSRead` (X44)**

Exactly the shape experiments.md row X44 specifies: a `client/` file that `require("ss.stats")` and `require("ISSSBar")`, sets `shown = true` on the four macro bars at file scope, wraps `SSBar:prepareBarInfo` with a sentinel held in the global `TKX_SSRead_Installed` to copy each macro bar's text from `self.barInfo` into `TKX_SS = { calls = 0, calories = "", carbs = "", lipids = "", proteins = "" }`. `x13-ssread.toml`: PZTestKit + `simpleStatus` (`workshop_id = "2867431511"`) + `TKX_SSRead`, no sandbox, verify: client `text.get IGUI_SS_BARTITLE_HAPPY` expecting `"Happiness"` (the teardown profile's gate), client `lua.global TKX_SS.calls`.

- [ ] **Step 5: The nutrition-off, weight-drift and persist profiles**

`x13-nutrition-off.toml`: PZTestKit only, `[sandbox] Nutrition = false` (the key exists in the fixture's own file, experiments.md X7), `run = { hold = 5 }`, verify: server `lua.global SandboxVars.Nutrition` expecting `"value": false`. `x13-nutrition-on.toml`: PZTestKit only, no sandbox, verify server `lua.global SandboxVars.Nutrition` expecting `"value": true`. `x13-weight-drift.toml`: a copy of `x13-nutrition-off.toml` whose `description` names X41. `x13-persist.toml`: PZTestKit only, no sandbox, `[client] timeout = 240`, verify: server `lua.global PZTestKit.version`.

- [ ] **Step 6: Validate every profile without booting**

Run, per profile: `python -c "import sys; sys.path.insert(0,'testing'); from pzt import profile; print(profile.load('<name>'))"` → the one-line repr with the resolved mods and sandbox (the nested `NR` table shows in `sandbox=`). `python tools/mod_lint.py testing/experiments/TKX_CalcStats testing/experiments/TKX_TraitProbe testing/experiments/TKX_SSRead` → 0 ERROR; `python tools/kahlua_lint.py testing/experiments` → 0; `python tools/luabalance.py <every new .lua>` balanced.

- [ ] **Step 7: Commit**

```bash
git add testing/profiles testing/experiments/TKX_CalcStats testing/experiments/TKX_TraitProbe testing/experiments/TKX_SSRead
git commit -m "Profiles and probe mods for Plan 1: the mod's three profiles, X7/X41, X28, X4, X32/X46, X42, X44" -- testing/profiles testing/experiments/TKX_CalcStats testing/experiments/TKX_TraitProbe testing/experiments/TKX_SSRead
```

---

### Task 10: The acceptance run — Opus implementer (live), Opus reviewer

**Files:**
- Create: `testing/artifacts/run-<id>/report.json` (byte-identical copy)
- Modify: `docs/reference/artifacts.md` (one row), `docs/reference/do-not-cite.csv` (keys or none)
- Create: `.superpowers/sdd/2026-10-04-plan-1-foundations/task-10-claims-delta.tsv`

- [ ] **Step 1: Doctor, then the run**

Run: `python testing/pzt doctor` (exit 0; a stray `ProjectZomboid64.exe` is reported and never killed) then `python testing/pzt run --profile nr-accept`.
Expected: exit 0; the four verification rows pass; the server console (the run's `server-stdout.log`) carries exactly one `[NutritionRevamp] NutritionRevamp v0.1.0 build 42.20.4 side=server mode=takeover log=2 frameworks=none hook=true …` line and `fast: takeover handler registered`; the client console carries the client self-report; the error classifier counts zero non-baseline server errors; during the 60-second hold the driver's own bus reads `lua.global NutritionRevamp.server.fast.stats.calls` (server) show a count rising between two reads 10 s apart and `…failures` reading 0, and `stats.all admin` shows hunger and thirst rising tick to tick (the takeover is moving the stats). Record these five reads in the artifact's `notes` by re-running the hold as a tiny driver if `pzt run`'s hold has no bus slot: copy `_template.py` to `testing/experiments/x131_accept.py` with one phase making those reads; its artifact is the one committed.

- [ ] **Step 2: Evidence and the register delta**

Copy the artifact byte-identical to `testing/artifacts/<run-id>/`; add its row to `docs/reference/artifacts.md` (run id · file · "Plan 1 acceptance: the mod loads on both sides, the takeover handler registers and the stats move" · reading guide); `do-not-cite.csv` rows for any key the driver wrote before a read landed. Delta: two `add` rows — `T10.1` "The NutritionRevamp mod loads in both Lua states under the acceptance profile and its takeover handler registers at `OnServerStarted` (grade M, pointer `artifact:<run-id>/<file> verify`)", `T10.2` "With the takeover handler registered the server's hunger and thirst stats advance between reads ten seconds apart (grade M, pointer `artifact:<run-id>/<file> notes.statsMove`)"; owner `areas/testing-your-mod.md#mod-profiles` with a sentence each added to that section's prose (the acceptance profile row's "what it proves" now has a measurement). The controller applies the delta.

- [ ] **Step 3: Commit**

Gates: `claims_check --staged` → 0, `page_lint docs/areas/testing-your-mod.md` → 0. `git commit -m "Plan 1 acceptance run: the mod loads and the takeover moves the stats" -- testing/artifacts/<run-id> docs/reference/artifacts.md docs/reference/do-not-cite.csv docs/areas/testing-your-mod.md docs/reference/claims.tsv docs/areas/open-questions.md testing/experiments/x131_accept.py`.

---

### Task 11: X34 with X35, X32 and X46 riding — the handler's live verification — Opus implementer (live), Opus reviewer

**Files:**
- Create: `testing/experiments/x131_calcrepro.py` (house shape, copied from `_template.py`), `testing/artifacts/x131-calcrepro-<id>/calcrepro.json`
- Modify: `docs/reference/artifacts.md`, `docs/reference/do-not-cite.csv`, `docs/facts/character-stats.md` (§ Open rows → settled sentences), `docs/facts/endurance-fatigue-sleep.md` (§ Open), `docs/platform/lua-platform.md` (#2100's sentence), `docs/areas/open-questions.md` (X32, X34, X35, X46 lines leave), `docs/reference/experiments.md` and `docs/reference/wall-map.md` (rows marked `run <run-id>`), `docs/platform/lessons.md` (the stat-hook rule gains its measured bound)
- Create: `task-11-claims-delta.tsv`

The session, three boots on the restored fixture at `DayLength = 1` (a game-hour is 37.5 s wall), each boot ≈ 8 game-hours ≈ 5 min plus boot and teardown:

| boot | profile | arm | what it reads |
|---|---|---|---|
| A | `nr-overlay` | the vanilla updaters run (the mod loaded, nothing registered) — **the control** | `stats.all admin` (server) every game-hour for 8 game-hours: 3 h idle standing, 1 h running (`player.walk 40 0 run` from the client, then `player.stop`), 2 h asleep (`player.sleep admin true`, then `false`), 2 h idle; `time.snapshot` beside each; `lua.global NutritionRevamp.server.fast.registered` must read `false` |
| B | `nr-takeover` | the handler reproduces the seven updaters | the same schedule, same tags; `…fast.registered` `true`; `…fast.stats.failures` `0` at every read; **X35**: `moddata.set admin NR_sentinel 1` at the start of the last idle hour, then ten client-first paired `stats.get` / `stats.get admin` reads ≥ 1 s apart, then `moddata.set admin NR_sentinel 0`, `lua.global NutritionRevamp.server.fast.stats.sentinelCalls` on both sides |
| C | `x13-calcstats` | **X32**: the no-op handler freezes the updaters; **X46**: the second registrant | `moddata.set admin TKX_calc 1`; `stats.all admin` across 3 game-minutes (thirst must stop); `TKX_calc 0`, 3 minutes (thirst resumes); then `TKX_hookA 1`, 3 minutes; `TKX_hookB 1` (both), 3 minutes; `TKX_hookA 0` (B alone, returning false), 3 minutes; `TKX_hookB 0`; `lua.global TKX_CalcStats.calls/callsA/callsB` on both sides client-first at each arm's end |

Predictions and falsifiers, written into the driver before the session:
- **X34** (`#2081`): for each of hunger, thirst, fatigue, stress, anger, idleness, morale, fitness, endurance, the arm-B hourly series tracks arm A's within a per-stat band: `max(2 % of A's own hourly delta, 1e-4)` for the moving stats, exact equality for `morale` (1.0) and `fitness` (0.0 at Fitness 5); the asleep arm's fatigue may differ by the sleep-delay mirror (ruling 7) and is graded on its slope after the first asleep hour. Falsifier: any stat outside its band in two consecutive hours; a `failures` count above 0; `disabledAt` non-nil. The stress arm is a first measurement of the terms (#2220) and is written as such.
- **X35** (`#2082`): in the sentinel window the client's endurance reads `0.4242 ± 1e-6` at every one of the ten pairs (the push carries the handler's write) — falsifier: any pair whose client value differs by more than vanilla's one-tick drain or regeneration from 0.4242; `sentinelCalls` server > 0, client 0.
- **X32** (`#2100`): with `TKX_calc` set, thirst's three-minute slope is 0 ± 1e-6 and the moodle recompute shows no change; with it cleared, the slope returns to the vanilla awake rate (8.0e-6 × 0.4 game-seconds per update ≈ 3.2e-6 per update; per game-minute at a 15-minute day: compute in the driver from `time.snapshot`); `TKX_CalcStats.calls` server > 0 and client = 0 (the hook never fires on a client, #2236) — a client count above 0 is the finding.
- **X46** (`#2086`): with A alone thirst freezes; with A and B both freeze and `callsA ≈ callsB`; with B alone (returning false) thirst stays frozen — a thaw under B alone falsifies #2238/#2240 and is the finding that would change the takeover ruling.

- [ ] **Step 1: Write the driver** in the house shape (`_template.py` copied; `PROFILE` switches per boot through three `make_server` calls on fresh run dirs within one session; every read wall-bracketed; `field_count` asserts on each `stats.all` (24 stats expected; `missing` must be empty); predictions, observations and verdicts per arm with the four-word vocabulary). `python testing/pzt doctor` first. The driver is never edited after its run.
- [ ] **Step 2: Run** `python testing/experiments/x131_calcrepro.py`; expected wall ≈ 25 min; the artifact lands under `testing/runs/…` and is copied byte-identical to `testing/artifacts/x131-calcrepro-<id>/`.
- [ ] **Step 3: Evidence**: artifacts row with its reading guide; do-not-cite rows for any snapshot inside a push window (#1488); the delta: `status` for `#2081`, `#2082`, `#2100`, `#2086` → `settled` with pointers `artifact:x131-calcrepro-<id>/calcrepro.json <verdict key>` and bounds `M; n=1; one fixture; DayLength 1; 8 game-hours per arm`, plus `add` rows for the stress-term first measurement and for any falsified prediction (a falsified reading is a row too); page sentences rewritten to the settled form on the owner pages; the lessons rule on the stat hook gains the measured tag beside its inference tag; experiments.md and wall-map rows marked `run x131-calcrepro-<id>`; open-questions lines removed; `page_lint` on every page touched → 0; `claims_check --staged` → 0.
- [ ] **Step 4: Commit** `-- testing/experiments/x131_calcrepro.py testing/artifacts/x131-calcrepro-<id> docs/reference/artifacts.md docs/reference/do-not-cite.csv docs/reference/claims.tsv docs/facts/character-stats.md docs/facts/endurance-fatigue-sleep.md docs/platform/lua-platform.md docs/platform/lessons.md docs/areas/open-questions.md docs/reference/experiments.md docs/reference/wall-map.md` with subject `X34/X35/X32/X46: the takeover handler reproduces the seven updaters on a live server`.

---

### Task 12: X7 and X41 — which arms the vanilla option freezes, and weight drift — Opus implementer (live), Opus reviewer

Three scenario runs in one live window, each its own `pzt scenario` session (the runner boots and tears down per run): `python testing/pzt scenario nutrition_3day_fast --profile x13-nutrition-off --speed 30`, `python testing/pzt scenario nutrition_3day_gain --profile x13-nutrition-off --speed 30`, `python testing/pzt scenario nutrition_3day_fast --profile x13-nutrition-on --speed 30` (the in-session control, experiments.md X41). The fixture's 90-minute day at speed 30 is the harness's measured cadence ceiling (#1814), so the suspect flag must stay clear on all three; a run with the flag set is written `unmeasured` and not re-run for a prettier number.

Predictions: **X7** (`#1277`): with the option off, the macro stores, `calories` and `weight` are each flat across 72 game-hours (band 1e-3 kg on weight, 1e-3 on each store), the three arms freezing independently; the gain run's doses still land in `calories` (intake is not gated, #0555) and are then not drained. **X41** (`#2090`): the fast-off run's hourly weight never moves more than 0.001 kg from its first sample; the fast-on control loses weight as the decoded model says (its evaluator passes) — a flat control makes the off arm unreadable and the row is written `unmeasured`.

- [ ] Steps: doctor → the three runs → copy the three scenario artifacts byte-identical → artifacts rows → delta: `status` `#1277` and `#2090` → settled with pointers into the scenario JSON's hourly samples, bounds `M; one fixture; 3 game-days; speed 30`; page sentences on `docs/facts/eating-pipeline.md#sandbox` (what the option gates, now measured), `docs/facts/body-and-weight.md#sandbox` (the weight-arrow line gains its measured neighbour), `docs/areas/new-nutrients.md` and `docs/areas/testing-your-mod.md` (their open lines on X7 settle); experiments.md and wall-map rows marked; open-questions lines removed; gates; commit `X7/X41: the vanilla option freezes the three arms; weight does not drift with it off`.

---

### Task 13: X28, X49a, X49b — persistence — Opus implementer (live), Opus reviewer

`testing/experiments/x131_persist.py`, profile `x13-persist`, four boots in one session using `make_server(..., reuse=True)` (Task 6):

| boot | what happens | reads |
|---|---|---|
| 1 | write: server `moddata.set admin TKX_persist 1`, client `moddata.set TKX_persist_c 1` + `moddata.transmit`, server `globalmoddata.set TKX_persist k 1` + `globalmoddata.transmit TKX_persist`; **X49a** arms: (a) ten game-minutes with no further write, the driver `stat`-ing `global_mod_data.bin` under the run dir's save folder every 5 s and grepping the console for `Saving GlobalModData`; (b) the write above, then ten game-minutes; (c) RCON `save` (the positive control), which must move the file's mtime and log once; then a clean teardown (`quit`) | `witness.moddata player:admin TKX_persist` and `witness.moddata global:TKX_persist k` on both sides client-first after the write |
| 2 | `reuse=True`: boot the same run dir | both witnesses: present says the key survived a clean save and reload (**X28**, `#1294`) |
| 3 | write `globalmoddata.set TKX_restart k 2` + transmit, wait one game-minute, **kill the server process** (no `quit`), then `reuse=True` boot | `witness.moddata global:TKX_restart k`: present says the value reached the file before the unclean stop (**X49b**, `#2098`); absent says it did not |
| 4 | a fresh restore of the golden fixture (the control) | both witnesses must **miss** — which proves the run dir, not the fixture, carried the keys |

Predictions: X28 — both scopes present after boot 2 (the code reading: the player blob carries character modData, #2394; global modData is a per-world file, #2397); the two scopes take different engine paths and either may fail alone, which is the finding. X49a (`#2097`) — the file's mtime moves on `save` and on the server's own `SaveWorldEveryMinutes` cadence read from the run's ini; whether the mod's transmit moves it is the reading. X49b — written as the artifact says, present or absent, with no prediction favoured.

- [ ] Steps: doctor → run → artifact byte-identical → artifacts row (the run dir's `global_mod_data.bin` mtime series is in the JSON) → delta: `status` `#1294`, `#2097`, `#2098` → settled (or `open` with the run named in `bound` for an arm that came back unmeasured), page sentences on `docs/platform/server-lifecycle.md#global-moddata` and `#open`, `docs/areas/mp-sync.md#global-moddata`, `docs/areas/new-nutrients.md`, `docs/areas/testing-your-mod.md`; experiments.md and wall-map rows marked; open-questions lines removed; gates; commit `X28/X49a/X49b: modData survives a reload; the global file's save cadence`.

---

### Task 14: X4 — the trait push — Opus implementer (live), Opus reviewer

`testing/experiments/x131_traits.py`, profile `x13-traits`, one boot. Three arms, each: make the server's list differ first (no run has yet held a non-empty trait list on either side, #2595), then time the client's arrival by polling client `stats.get` every 0.25 s for up to 5 s after the server write and recording the first poll whose `traitList` carries the name:

1. **control, no push**: server `trait.set admin HeartyAppetite add`; poll — predicted to arrive within one second on the experience packet (#2608); `trait.set … remove` after.
2. **the mod's push**: `trait.set admin LightEater add` immediately followed by `trait.push admin 2`; poll — predicted to arrive sooner than arm 1's time; the difference is the reading.
3. **a registered trait**: `moddata.set admin TKX_grant TKX:Probe` (the probe mod grants `TKX:Probe` on its next tick) then `moddata.set admin TKX_push 1`; poll for `tkx:probe` (names read back lowercased, #0550); predicted to behave as arm 2; a name that never arrives on the client is the finding that a registered trait's definition does not reach the receiver's resolver.

Each arm's server-side list is read first through `stats.get admin` to prove the write landed. Delta: `status` `#2099` → settled with the three arrival times in `bound`; the wall map's G4 verdict row gains `run <id>`; page sentences on `docs/platform/mp-model.md#sync-globals`, `docs/areas/mp-sync.md#server-pushes` and the rule line's tag; open-questions X4 removed; commit `X4: a server trait write reaches the owning client within the push cadence`.

---

### Task 15: X42, X44 live; X43 desk — the free compatibility readings — Opus implementer (live), Opus reviewer

- **X43** (`#2092`): a dated desk re-read of `D:\SteamLibrary\steamapps\workshop\content\108600\2503622437` 's live tree: `grep -rn "checkProteinLevelMulti" <tree>` and the `fetchMultipliers` block; if the branch is still unwired, the row goes `settled` as a trivial reading ("not wired on the live `42.20.1/` tree read on <date>: no caller, the branch block-commented") with the pointer `data:workshop/content/108600 grep checkProteinLevelMulti, <date>` in the grammar's workshop form; if wired, the row stays open with the harness change `exercise.do` named in `bound` as the next step.
- **X42** (`#2091`): driver `x131_swtraits.py`, profile `x13-swtraits`; arms as experiments.md row X42: grant `SWTraits:SWAdaptiveMetabolism` through `TKX_grant`, then `nutrition.set admin weight 75` and `nutrition.get admin` polled every 2 s for 60 s (calories should rise by about `60 / dayLengthMinutes × 0.5` per write at most once per 5 s per the read), then `weight 85` (calories should fall), then the trait removed (`-SWTraits:SWAdaptiveMetabolism`) as the control (no movement beyond vanilla's drain). Reads the cadence and the per-write step.
- **X44** (`#2093`): driver `x131_ss_track.py`, profile `x13-ssread`; server `nutrition.set admin calories 1500` then `proteins 120`, each read back with `nutrition.get admin`; client-first `lua.global TKX_SS.calories` and `TKX_SS.proteins` beside client `nutrition.get` at 1, 2 and 4 s after each write; predicted: the bar text equals the client's mirrored value rounded to one decimal within one push (#1483), never the server's instantaneous value.

Delta: `status` for `#2091`, `#2092`, `#2093`; page sentences on the mods' own pages under `docs/facts/other-mods/` (create a short page for SomewhatTraitsCore in the catalog's shape if none exists; simpleStatus's page exists) and on `docs/areas/packaging.md#resident-stack`; experiments.md and wall-map rows marked; commit `X42/X43/X44: the three free compatibility readings`.

---

### Task 16: The documentation delta — Sonnet implementer, Sonnet reviewer

**Files:** `CLAUDE.md` (§ 1 a router row `| work on the mod's code | [areas/testing-your-mod](docs/areas/testing-your-mod.md) → [platform/lessons#rules](docs/platform/lessons.md#rules) → the mod's tree \`mod/NutritionRevamp/\` | \`nutrition-testing-your-mod\` |` and the § 1 first paragraph naming the mod tree; § 3 three new gate lines: `python tools/mod_lint.py mod/NutritionRevamp` → 0 ERROR, `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` → 0 and `python tools/hotpath_lint.py mod` → 0 before any commit touching `mod/` or an experiment mod; the `science_check --scan mod` clause made concrete; § 7 a line on `lupa`), `README.md` (the tree line for `mod/`), `docs/reference/tools.md` (the two lints, already in Task 2 — verify; the kernel harness paragraph), `docs/areas/testing-your-mod.md#mod-profiles` (the profiles table's first three rows now name real files), `docs/areas/packaging.md` (the layout as shipped: `42.20.4` and `common/`, with the version-dir ruling), `docs/platform/lessons.md` (two new rule lines resting on this plan's measured rows: the dot-call registration of a `Hook.*` handler, jar § 11; the sleep endurance arm the hook skips, jar § 3 — each a `rule` row via the delta with a C pointer copied from the row it rests on), `docs/superpowers/research/jar-calculatestats-updaters.md` (its 40 `## Claims candidates` lines become `add` rows in `task-16-claims-delta.tsv`, owner pages `facts/character-stats.md#updaters`, `facts/endurance-fatigue-sleep.md#sleep`, `facts/body-and-weight.md#hunger-thirst`, `platform/lua-platform.md#hooks`, with one tagged sentence each; `#0480` goes `superseded` by the autoDrink reading, `#2261`'s sentence gains the "inside a skipped updater" clause).

- [ ] Steps: write the rows and sentences; `page_lint` on every page touched → 0; `claims_check --staged` → 0; `python -m pytest tools/tests testing/tests -q` green; commit `Docs: the mod tree in the router and gates; the stat-updater claims; two hook rules`.

---

### Task 17: The close (controller)

- [ ] **Step 1: Whole-pass review.** One fresh Opus reviewer, read-only: the mod tree against spec § 4.1, § 4.8, § 4.9 and § 6 (the hot path by eye beside the lint, the one rim guard, the hoisting), the kernel against the jar report term by term, every live artifact against its predictions, every settled row's pointer resolving into its artifact, the pages' settled sentences, the gates; findings → one consolidated fix wave (fresh implementers) → scoped re-review.
- [ ] **Step 2: Gates.** `python tools/claims_check.py` (full) → 0; `python tools/science_check.py` → 0 and `--scan mod` → 0; `python tools/mod_lint.py mod/NutritionRevamp` → 0 ERROR; `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` → 0; `python tools/hotpath_lint.py mod` → 0; `python tools/page_lint.py` on every page touched → 0; `python tools/bus_inventory.py --check` in sync; `python tools/reference_gen.py cited-by --check` and `contradictions --check` in sync; `python -m pytest tools/tests testing/tests -q` green with the count written into `CLAUDE.md` § 3 with today's date.
- [ ] **Step 3: Record.** Rulings 1–9 of this plan as `Ruling:` lines in the ledger and, where they bind later agents, as rules in `CLAUDE.md` (the mod tree and its gates; subagent sizing already there) or on `platform/lessons.md` (the hook registration shapes); the memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` (Plan 1 closed at `<commit>`; what the mod does; the experiments' verdicts in one line each; the resume point: Plan 2 Intake's writing-plans, with X13's session first on `drink.action`); the project memory pointer; the ledger's last line `Plan 1: complete`.
- [ ] **Step 4: Push.** `git push origin main`. Nothing under `docs/superpowers/` is removed by this plan; the jar report stays as a source until the program's close.

---

## Self-review (run by the controller before dispatch)

- **Spec coverage.** § 5 row 1: skeleton and lint → Tasks 1, 2; kernel test harness (`lupa`, pytest, coverage hook) → Task 3; bus protocol and store → Task 4; sandbox options file and read timing → Tasks 1, 5; the takeover handler reproducing the seven updaters with no nutrition terms → Task 8; mode switch → Task 8; profiles → Task 9; the gates X7, X28, X4, the handler's live verification → Tasks 12, 13, 14, 11; the harness changes it lands first (nested-key sandbox merge, the timing instrument, `drink.action`, a trait-push probe) → Tasks 6, 7; § 4.9's three free live experiments → Task 15; § 6's instrument → `bench.global` and `tick.rate` (Task 7) and the acceptance read of the handler's cost is deferred to the first plan that adds a term (ruled: with unit coefficients the budget comparison is vanilla against vanilla). § 4.10 tier 1 → Task 2; tier 2 → Tasks 3, 8; tiers 3–4 → Tasks 10–15 as far as a mod with no nutrition term can exercise them.
- **Placeholder scan.** No "TBD"; every step carries its code or its exact commands and predictions; the experiment tasks name the profile, the arms, the predictions, the falsifiers, the rows settled and the pages touched.
- **Type consistency.** `K.fast.step(inp, out, c)` and the field sets of `F.input()`/`F.output()` match the adapter's `body` and the tests' `BASE`/`C`; `NR.server.store.get(username, worldAgeHours)` is called with two arguments everywhere; `NR.server.players.onFirstSight/onDeparture/onMinute` take `(username, player, record)`; `make_server(..., reuse=True)` is the name Tasks 6 and 13 share; the profile names in Tasks 9–15 agree; the pytest counts run 429 → 444 → 449 → 452 → 462 → 474.
