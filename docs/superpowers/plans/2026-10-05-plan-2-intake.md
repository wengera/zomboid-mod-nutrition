# Plan 2 — Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every eat and drink into a nutrient vector the mod owns, and move that vector through a stomach buffer, gastric emptying and absorption into a per-player pool the later plans drain and read. Three server-side wrappers capture each intake off the item before vanilla touches it; a pure kernel assembles the vector from four sources (per-type baseline, dishes, crafted outputs, animal meat, fluids), applies state multipliers, and runs the stomach-emptying-absorption chain; the slow clock drives the chain per minute and the fast clock derives hunger from stomach fill, so vanilla's eat-time hunger and thirst writes are overwritten within one push.

**Architecture:** The intake engine sits on the three Lua layers Plan 1 built (spec § 4.1). A new pure-kernel group (`NR_Kernel_Vector`, `NR_Kernel_Retention`, `NR_Kernel_Stomach`) holds all the arithmetic — meal vector in, absorbed vector out, tables in and tables out, no Java. A new server group (`NR_Server_Intake`) holds the three wrappers (`ISEatFoodAction.complete`, `ISEatFoodAction.serverStop`, `ISDrinkFluidAction:updateEat`), each sentinel-guarded in a global of its own, nil-checked on the side test, always calling the original, composing with any corpus mod that wrapped the same method. A hand-authored seed nutrient data table (`NR_Data_Nutrients`) covers the foods and fluids this plan's live sessions use; Plan 6's pipeline tool regenerates it at full coverage against the same loader interface. The stomach, emptying and absorption run on the slow clock into a per-player pool accumulator on the global-modData record; the fast clock reads one stomach-fill scalar per tick and derives HUNGER from it, with the energy-state term stubbed as a Plan 3 entry point. The client mirror gains the stomach and pool scalars.

**Tech Stack:** Kahlua (Project Zomboid's Lua 5.1 dialect: no `goto`, no `%d` on a float, no `#` on a Java list, methods not fields); `lupa` 2.8 (`lupa.lua51`) hosting the kernel offline under pytest with the line-granular coverage gate Plan 1 built; Python 3.13 stdlib tools under `tools/`; the harness (`testing/pzt`, `testing/PZTestKit`, `testing/profiles`, `testing/experiments/_template.py`); the claims register, the science register and their tools.

**Spec:** `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` — § 4.2 (intake, approved), § 4.4 (nutrient kinetics: the stomach/emptying/absorption chain this plan builds; the record engine and the records themselves are Plan 4), § 4.6 (the item pass and data pipeline, whose tool is Plan 6 and whose data-table interface this plan consumes), § 5 row 2 (this plan's scope, gates and harness change), § 6 (performance, the entry gate), § 7 items 1 (the stomach model), 18 (the item pass re-bases macros only), 19 (per-type nutrients in a Lua data table), 37 (shipped values with no settled science row — the gastric-emptying constants S0130/S0131 ship as labelled game choices), 39 (the handler-failure ruling, inherited), § 8 (experiments X13, X24, X31, X45a, X45b and the Plan 1 residual arms). The platform reading it rests on: `docs/facts/eating-pipeline.md` (the order of writes inside `Eat`, the drink path, the fraction rescale), `docs/facts/cooking-and-recipes.md` (the evolved summation, the craft split, the craft `OnCreate`, the butchering scale), `docs/facts/food-item-model.md` (the item model, the fluid blocks, reading a type's macros off an instance), `docs/areas/eat-and-cook-hooks.md` (where each seat sits and what it sees), `docs/areas/new-nutrients.md` (where a mod nutrient lives and what it survives), `docs/areas/item-pass.md` (the per-fluid table and the instance-read route), `docs/platform/loader-and-scripts.md` (script load per side), `docs/platform/lua-platform.md#script-hooks`, `docs/platform/mp-model.md#command-bus`, `docs/platform/harness.md`, `docs/platform/lessons.md#rules`; the jar read this plan's assembly rests on, `docs/superpowers/research/jar-dishes-item-nutrients.md`; the data-pipeline design, `docs/superpowers/research/food-data-pipeline.md`; the experiment specs `docs/reference/experiments.md` rows X13, X24, X31, X33, X45a, X45b, and the Plan 1 residual rows X34 (#2081), X35 (#2082), X4 (#2099); the science register `docs/reference/science.tsv` rows S0130, S0131 (gastric emptying, open), S0195, S0532, S0533 (phytate–iron), S0194, S0534, S0535 (iron bioavailability), S0197, S0199, S0156, S0205 (fat co-ingestion and carotenoids), S0332, S0357, S0358, S0413, S0418 (fractional absorption ceilings).

## Global Constraints

- **Mod tree.** Everything new lives under `mod/NutritionRevamp/` in this repository (spec § 4.9): kernel files `common/media/lua/shared/NR_Kernel_*.lua`, server files `common/media/lua/server/NR_Server_*.lua`, client files `common/media/lua/client/NR_Client_*.lua`, the seed data under `common/media/lua/shared/NR_Data_*.lua`. No file sits at a vanilla relative path; every Lua file is named `NR_<Role>[_<Part>].lua`; the one global is `NutritionRevamp` (alias `NR` inside each file). Line endings LF; the join checksum drops CR bytes.
- **The kernel is pure.** A file under `shared/` named `NR_Kernel*.lua` holds only functions assigned to `NutritionRevamp.kernel` (or a sub-table of it) and constants; it never names a Java global, never uses `pcall`, `pairs` over a Java object, `#` on anything but a Lua table it built, `goto`, or `string.format` with `%d`. `tools/kahlua_lint.py` enforces the dialect on every mod and experiment Lua file; `tools/hotpath_lint.py` enforces the fast-path rules inside `-- @fastpath` regions, the kernel-shape rule (every kernel function is `function NutritionRevamp.kernel.<path>(` or `function K.<path>(`, no locals, no closures, no anonymous functions assigned to fields), the kernel-oneline rule (one statement per line: no code after `then`/`else`/`do`/`repeat`/a function header, no `X and Y or Z` value-pick outside a conditional line) and the kernel-java rule, so `debug.getinfo(f, "L").activelines` over the kernel table is the exact line set the 100 % coverage gate compares against. A `NR_Data_*.lua` file is **not** a kernel file: it is a data table and a loader, and the loader may name Java globals behind the side test — it is linted by `kahlua_lint` but not by `hotpath_lint`'s kernel rules, so it carries a `-- not a kernel file` banner and holds no `NutritionRevamp.kernel` function.
- **The data table is the interface, not the data.** This plan ships a hand-authored **seed** `NR_Data_Nutrients` table covering only the foods and fluids its live sessions eat and drink (named in Task 4). Its schema is the contract Plan 6's pipeline (`tools/food_nutrients.py`, `data/food-nutrients.json`, spec § 4.6) regenerates at full coverage; every field the seed carries, Plan 6 fills for all ~1 005 records. A seed entry carries a `-- SEED` comment and the `pz_id` it stands for; the mod reads the table through one loader (`NR.data.nutrients.get(fullType)`), never by indexing it directly, so Plan 6 can swap the table's provenance without touching a reader. No per-type nutrient is a script key (spec § 7 item 19): a script key becomes a deep per-instance modData copy on every food in the world ([`new-nutrients.md`](../areas/new-nutrients.md) rule #1058/#2676).
- **The nutrient vector shape is fixed once.** The meal vector and the pool are one flat Lua table of named scalars — the four vanilla macros (`calories`, `carbs`, `lipids`, `proteins`) plus the mod-nutrient keys the seed declares (this plan seeds `fibre`, `water`, `vitC`, `iron`, `phytate` as the worked set; the full 22-plus set is Plan 4's records) — so a new nutrient is a new key and never a new code path. The kernel never hard-codes a nutrient name except the four macros; it iterates the vector's own keys (a Lua table it built, so `pairs` is allowed and `#` is never used on it).
- **Units are the script's, never the instance's.** A food's macros are read off a fresh instance through the `instanceItem` global or off the live item, never off `getScriptItem()` (no macro getter exists, [`food-item-model.md`](../facts/food-item-model.md#script-keys) #2679); hunger is read raw (`getHungChange`, `getBaseHunger`), the share eaten is the drop in raw hunger over base hunger ([`eating-pipeline.md`](../facts/eating-pipeline.md#getters) #0002); a fluid's numbers are per litre and the container multiplies by its litres ([`eating-pipeline.md`](../facts/eating-pipeline.md#fluid-path) #0630); the burnt divisor of 5 on the four macros is the one vanilla nutrition modifier and a correction that recomputes an eat from the item's macros applies it or overstates a burnt item ([#0019], [#0036]).
- **Wrappers.** Each of the three wrappers (spec § 4.2, [`eat-and-cook-hooks.md`](../areas/eat-and-cook-hooks.md) rules) holds its sentinel in a global of its own (not inside `NutritionRevamp`, which a reload re-creates, [#0943]), is installed idempotently testing for its own wrapper before replacing the target, saves the original and calls it on every path that does not mean to skip the eat, guards on a nil-checked `NutritionRevamp.isServer()` because the `server/` file also runs in the client VM, and composes with any corpus mod that wrapped the same method (QualityCooking saves and replaces `ISEatFoodAction.complete` and `:eat` with no sentinel, Task 1's reading). The eat wrapper acts on the server only ([#0109], [#0928]); its writes go to the server's store.
- **Server side test and event-time reads.** Every `server/` file's top-level work runs inside `if NutritionRevamp.isServer() then … end` at event time, never at file scope (#0855); `SandboxVars.NR` is read at `OnServerStarted` and on the slow tick, never at file scope (#2460).
- **Fast-path rules** (spec § 6) inside a `-- @fastpath` … `-- @endfastpath` region: no table constructor, no string concatenation, no `pcall`/`xpcall`/`error`/`assert` (one `-- @rimguard` allowed per region), no `string.`/`tostring`/`table.`, no `^`/`math.exp`/`math.pow`/`math.log`, no `for` loop, no method call on a receiver outside the file's `-- @hoisted` list. **Ruling (inherited):** exactly one protected call per player per tick, the rim guard. The per-tick hunger term this plan adds reads one stomach-fill scalar the slow clock already computed and runs no loop and no allocation; the stomach, emptying and absorption chain runs on the slow clock. Cost: one item read per eat, nothing per tick beyond the scalar hunger term (spec § 4.2).
- **Persistence.** The per-player stomach buffer and pool live on the global-modData record `NutritionRevamp.players[username]` Plan 1 built (keyed by username, inputs/state only, never transmitted, #2416; derived-on-read where a value can be derived); the client's copy arrives on the `mirror` bus command, never a transmit. A record gains a `stomach` table and a `pool` table, both of named scalars, both versioned by the record's `v` field.
- **A number with no row does not ship** (spec § 0). Every science number the kernel uses carries its `science.tsv` id in a trailing comment (`-- S0195`) and `tools/science_check.py --scan mod` → 0 finds every cited `S` id settled; a value with no settled row is a labelled game choice carrying its **open** row's id and the tag `design-phase-v1` (spec § 7 item 37) — this plan's gastric-emptying constants (S0130, S0131) are the worked case. Every engine constant carries its claims-register id (`-- #0006`).
- **Harness changes land first, each in its own commit**, under CLAUDE.md § 5: `python tools/luabalance.py <lua files>` (HEAD copies first, then the working tree) green, `python tools/bus_inventory.py` regenerating `docs/reference/harness-commands.md`, `python tools/bus_inventory.py --check` in sync, `python -m pytest tools/tests testing/tests -q` green; the next acceptance run is the smoke test. A harness Lua edit appends new sites at the end of its file and re-anchors every `repo:` pointer the shift moves in the same commit (claims_check rule 3b). A driver (`testing/experiments/*.py`) is never edited after its run.
- **Live sessions.** One live game session at a time, repository-wide; `python testing/pzt doctor` before every boot; never `-safemode`; a stray `ProjectZomboid64.exe` predating a session is Angus's own client and is never killed; a raising probe is gated server-side with the profile's `[client] timeout` set low; every artifact is copied byte-identical to `testing/artifacts/<run-id>/` with its row in `docs/reference/artifacts.md` (re-anchoring the register pointers the new row shifts) and its keys in `docs/reference/do-not-cite.csv` (empty allowed); a reading that comes back trivial, unmeasured or falsified is written as such and never re-run for a prettier number. A run-id prefix carries no hyphen (the register's run-id grammar refuses one).
- **Register.** The claims register and the science register are read-only for implementers. A task that settles or mints a claim writes a delta file `.superpowers/sdd/2026-10-05-plan-2-intake/task-N-claims-delta.tsv` in `tools/claims_delta.py`'s format (a `supersede` op's `add` row directly follows it, Plan 1 ruling); a science number is a part file the controller applies with `tools/science_delta.py` (never `tools/` or `docs/` in `--scan`; the mod plans add `--scan mod`). The controller applies the delta with `--pages` at the task's close in the same commit as the artifact and the page sentences; `python tools/claims_check.py --staged` → 0 before that commit.
- **Gates before every commit** (CLAUDE.md § 3 plus this plan's): `claims_check.py --staged` → 0 for any `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or register-rendering path; `science_check.py --staged` → 0 for any `science.tsv` touch and `science_check.py --scan mod` → 0 for any mod commit that cites an `S` id; `page_lint.py <pages>` → 0 for any contract page; `mod_lint.py mod/NutritionRevamp` → 0 ERROR; `kahlua_lint.py mod testing/experiments` → 0; `hotpath_lint.py mod` → 0; `reference_gen.py cited-by --check` and `contradictions --check` in sync after any register touch; `bus_inventory.py --check` in sync after any harness edit; `python -m pytest tools/tests testing/tests -q` green at **489** or more (the Plan 1 close count; the count never drops; the close task writes the new count into CLAUDE.md § 3).
- **Commits:** pathspec commits, succinct subjects, no Claude attribution, never `--amend`; implementers never push; the controller pushes at the close. **Subagent sizing** (CLAUDE.md § 6): the model is named on every dispatch and in each task header — Opus for every kernel and adapter Lua task, every live session, every evidence or jar read, every reviewer of those and the whole-pass review; Sonnet for a tool or harness task whose code and tests this plan spells out, for root-file and profile edits, and for scoped re-reviews of small fix diffs.
- **Rulings this plan takes** (each a ledger line and a `Ruling:` row at the close): (1) the data-pipeline tool is Plan 6; Plan 2 ships a hand-authored seed table against the same loader interface, so the intake engine is testable and demonstrable before the full data exists; (2) the gastric-emptying constants (S0130, S0131) ship as labelled game choices tagged `design-phase-v1`, their open rows named, re-read when they settle (spec § 7 item 37); (3) the absorbed-nutrient pool this plan fills is a provisional accumulator of named scalars that Plan 4's record engine replaces, so Plan 2 defines the pool's shape and the absorption that feeds it but not the per-nutrient elimination, status ladders or interactions; (4) hunger-from-stomach-fill ships with the energy-state term stubbed at a neutral value, a named Plan 3 entry point, because energy state is Plan 3's; (5) the crafted-output nutrient map is read from the consumed-type-to-count map the vanilla hand-craft action already writes onto a single output ([#2667], `ISHandcraftAction.lua`), with no new hook unless X31's craft probe shows the map is unreachable; (6) the mod's eat wrapper composes with QualityCooking's by save-and-call-original idempotency, the outermost wrap being whichever loads last (Task 1's reading, X45b's measurement).
- **Environment.** Bash cwd resets between calls (`cd /c/Users/Angus/repos/project_zomboid` first); Windows Python takes `C:/Users/...` paths; long text and anything with apostrophes goes through the Write tool; `PYTHONIOENCODING=utf-8` when a checker's output is piped; the CRLF survivors in CLAUDE.md § 7 are edited with `newline=""` preserving their endings; the install, the workshop folder and the jar toolchain `C:\Users\Angus\pz-b42` are read-only.

## Execution order

Task 1 (QualityCooking read, the X45b compat gate) and Task 2 (expose `bench_fast`) in parallel (disjoint: a desk read and a mod edit) → Task 3 (the entry-gate cost session, live, serial) → Tasks 4–7 serial (the kernel group: vector schema and seed, four-source assembly, retention, stomach/absorption — each builds on the last's kernel functions) → Tasks 8, 9, 10 serial (the eat/cancel wrappers, the drink wrapper, the crafted-output map — all touch `server/NR_Server_Intake.lua`) → Task 11 (slow-clock kinetics, fast hunger term, client mirror) → Task 12 (profiles and probe mods; the harness additions land first in their own commits) → live experiments serial, one session each: Task 13 (X13 drink wrap), Task 14 (X24 + X33 eat per portion and cancel), Task 15 (X45a co-boot and the Plan 1 residual arms) → Task 16 (documentation delta) → Task 17 (the close). Each live task's documentation (artifact row, do-not-cite, register delta, page sentences) is part of that task and lands in its commit.

## File structure

| path | responsibility | task |
|---|---|---|
| `docs/superpowers/research/qualitycooking-eat-wrap.md` (then deleted at the plan close), register delta, `docs/facts/other-mods/catalog.md` or a new `qualitycooking.md` sentence | the QualityCooking eat-wrap read and the composition ruling (X45b gate) | 1 |
| `mod/NutritionRevamp/common/media/lua/server/NR_Server_Bench.lua`, `testing/tests/kernel/test_bench.py` | `NutritionRevamp.bench_fast()` — a filled fast input run through the kernel step, for `bench.global` | 2 |
| `testing/experiments/x132_cost.py`, `testing/artifacts/x132c-<id>/…`, register delta, `docs/areas/testing-your-mod.md`, `docs/reference/experiments.md`, `docs/reference/wall-map.md` | the entry-gate cost-budget session (bench + tick.rate takeover vs overlay) | 3 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Nutrients.lua`, `…/shared/NR_Kernel_Vector.lua` (the vector shape and loader), `testing/tests/kernel/test_kernel_vector.py` | the nutrient-vector schema, the seed data table and its loader | 4 |
| `…/shared/NR_Kernel_Vector.lua` (grows), `testing/tests/kernel/test_kernel_vector.py` (grows) | the four-source assembly: baseline, dish, meat, craft, fluid | 5 |
| `…/shared/NR_Kernel_Retention.lua`, `testing/tests/kernel/test_kernel_retention.py` | the cooked/burnt/rotten/frozen state multipliers per nutrient class | 6 |
| `…/shared/NR_Kernel_Stomach.lua`, `testing/tests/kernel/test_kernel_stomach.py` | the stomach buffer, gastric emptying and absorption chain | 7 |
| `…/server/NR_Server_Intake.lua` (the eat and serverStop wrappers), `testing/tests/kernel/test_intake_shape.py` (the pure helpers) | the eat-complete and cancel wrappers, the capture → vector → stomach path | 8 |
| `…/server/NR_Server_Intake.lua` (grows: the drink wrapper) | the `ISDrinkFluidAction:updateEat` wrapper and the per-fluid vector | 9 |
| `…/server/NR_Server_Intake.lua` (grows: the craft map), `…/shared/NR_Kernel_Vector.lua` (the craft-source reader) | the crafted-output nutrient map from the consumed-type map | 10 |
| `…/server/NR_Server_Kinetics.lua`, `…/shared/NR_Kernel_Fast.lua` (the hunger term), `…/shared/NR_Kernel_Mirror.lua` (the stomach/pool scalars), `…/client/NR_Client_Mirror.lua` (grows), `testing/tests/kernel/test_kernel_fast.py` (grows), `testing/tests/kernel/test_kernel_mirror.py` (grows) | the slow-clock emptying/absorption drive, the fast hunger term, the mirror | 11 |
| `testing/profiles/x13-drink.toml`, `x13-eat.toml` (or reuse `x12-overrides.toml`), `x13-coboot.toml`, `x13-residual.toml`; `testing/experiments/TKX_DrinkHook/`; harness additions if needed | the profiles, the probe mods and the harness commands for the live sessions | 12 |
| `testing/experiments/x132_drink.py`, artifacts, register delta, `docs/facts/eating-pipeline.md`, `docs/areas/eat-and-cook-hooks.md`, `docs/reference/wall-map.md`, `docs/areas/open-questions.md`, `docs/reference/experiments.md` | X13 — the drink wrap fires | 13 |
| `testing/experiments/x132_eat.py`, artifacts, register delta, `docs/facts/eating-pipeline.md`, `docs/areas/eat-and-cook-hooks.md`, `docs/reference/wall-map.md`, open-questions, experiments | X24 (eat hook per portion) and X33 (the serverStop guard) | 14 |
| `testing/experiments/x132_coboot.py`, `testing/experiments/x132_residual.py`, artifacts, register deltas, `docs/facts/other-mods/*.md`, `docs/facts/character-stats.md`, `docs/reference/wall-map.md`, open-questions, experiments | X45a co-boot and the X34/X35/X4 residual arms | 15 |
| `CLAUDE.md` (§ 1 router rows if the intake pages move, § 3 count), `README.md`, `docs/reference/tools.md`, `docs/areas/*`, the `.claude/skills/` that quote a changed rule | the documentation delta | 16 |
| ledger, memory, `CLAUDE.md` § 3 count line | the close | 17 |

---

### Task 1: The QualityCooking eat-wrap read and the composition ruling (X45b gate) — Opus implementer, Opus reviewer

The spec's compatibility list gates Plan 2 on "QualityCooking's code read before Plan 2" (§ 5). QualityCooking (workshop `3624538051`, live tree `42/`) saves and replaces `ISEatFoodAction.complete` and `ISEatFoodAction.eat` in a `server/` file with no idempotency sentinel, each replacement calling the saved original inside its own handler. This task reads that wrap end to end, names its per-eat observable effect, and rules how the mod's own eat wrapper composes with it — so Task 8 can be written knowing which wrap is outermost and what QualityCooking does to the item and the stores on the same eat.

**Files:**
- Create: `docs/superpowers/research/qualitycooking-eat-wrap.md` (the read; deleted at the plan close, its claims minted)
- Create: `.superpowers/sdd/2026-10-05-plan-2-intake/task-1-claims-delta.tsv`
- Modify (the controller applies the delta): `docs/facts/other-mods/catalog.md` or a QualityCooking page, one sentence

**Interfaces:**
- Produces: the ruling the Task 8 brief quotes — the mod's eat wrapper saves `ISEatFoodAction.complete`, tests for its own wrapper before replacing, and calls the saved original every time, so it composes with QualityCooking's save-and-replace whichever loads last; the named per-eat observable effect of QualityCooking's wrap (the buff it writes, where it writes it, and whether it reads the eaten macros before or after the original); the register ids for X45b's facts.

- [ ] **Step 1: Read the wrap end to end.** Read, read-only, under `D:/SteamLibrary/steamapps/workshop/content/108600/3624538051/mods/QualityCooking/42/media/lua/`: `server/EventHandlers/CookingRollHandler.lua` (the two wraps and `eatWithBuff`), `shared/Utilities/CookingBuffMath.lua` (`effectiveFraction`, `Macros`, `Allocate`), `shared/Utilities/QualityCookingData.lua` (`Data.SetBuff`/`GetBuff`/`GetTier`; the buff rides `QuestSystem.PersistentData` under key `cookingBuff`, the tier and chef ride item modData under `QualityCookingTier`/`QualityCookingChef`), `server/EventHandlers/CookingBuffTicker.lua` (the minute ticker that reads the buff and runs its own endurance/fatigue/hunger effects), `shared/QualityCookingInit.lua`, `shared/Utilities/QualityCookingConfig.lua` (`Config.IsEnabled`, `Config.Log` under `Config.Debug`). Note that QualityCooking's `eatWithBuff` reads `BuffMath.Macros(food, fraction)` **before** calling the original and applies the buff **after**, so it reads the item's eaten macros before `Eat` consumes it — the same seat the mod's wrapper wants.

- [ ] **Step 2: Write the read.** `docs/superpowers/research/qualitycooking-eat-wrap.md`: every cite `lua:<path>:<lines>` read this session; the wrap's save-and-replace shape (no sentinel, saved original called inside each handler), its per-eat observable effect (a tier buff written to `QuestSystem.PersistentData` keyed by player, scaled by the eaten macros, applied after the original), its config gate (`Config.IsEnabled`), its requirements (`ItemQuality`, `QuestSystem`, `MoodleFramework`), and the composition reading: two save-and-replace wraps of one method compose, and the outermost is whichever `server/` file runs last in load order; the mod's wrapper reads the item before QualityCooking's handler only if the mod loads after it, and both read the pre-`Eat` item regardless because each calls the saved original after its own read. State the one thing a sentinel-guarded wrapper beside a sentinel-free one must do: call the saved original on every path, or QualityCooking's chain below it never runs.

- [ ] **Step 3: Write the claims delta.** Rows (grade C, bound `C-only`, pointer in the `lua:` form the register uses — read five existing `lua:` pointers in `docs/reference/claims.tsv` and copy the shape; source `docs/superpowers/research/qualitycooking-eat-wrap.md`): QualityCooking saves and replaces `complete` and `eat` with no sentinel, each calling the saved original; `eatWithBuff` reads the eaten macros before the original and applies the buff after; the buff lives in `QuestSystem.PersistentData` not item modData; the tier and chef live in item modData under named keys; two save-and-replace wraps compose and the outermost is load-order-last. One `settle` on X45b's row #2095 is **not** done here — X45b is a live measurement (Task 14's boot rides it or its own); this task settles only the code-read half, so #2095 stays open with the reading named in its bound, and Task 14 or a later boot measures the composition live. Add the compat sentence to the QualityCooking catalog page.

- [ ] **Step 4: Gates and report.** `page_lint.py` on the page touched → 0; `claims_check.py --staged` → report (provisional tags clear at the controller's apply). Do not commit the page or register (the controller applies the delta). Write `task-1-report.md`. Return: status, the delta row counts by op, the one-line composition ruling, concerns.

---

### Task 2: Expose `NutritionRevamp.bench_fast()` — Opus implementer, Sonnet reviewer

The Plan 2 entry gate is the § 6 cost budget, read as `bench.global` over `NutritionRevamp.kernel.fast.step` with a filled input (spec § 5 row 2, § 6; the Plan 1 close named it). The kernel step needs a fully-filled input and output table to run; `bench.global` calls a resolved global N times with no arguments, so the mod exposes a zero-argument `NutritionRevamp.bench_fast()` that owns one filled input, one output and the constants, and runs `kernel.fast.step` once per call. The kernel is unchanged; this is a thin server-side benchmark entry point.

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Bench.lua`
- Create: `testing/tests/kernel/test_bench.py`

**Interfaces:**
- Consumes: `NutritionRevamp.kernel.fast.step(inp, out, c)`, `K.fast.input()`, `K.fast.output()`, `K.fast.defaults()` (Plan 1, `NR_Kernel_Fast.lua`).
- Produces: `NutritionRevamp.bench_fast()` — fills a steady-state input (an awake player, mid-range stats, every optional term on) once at first call into module-level tables, then runs `kernel.fast.step(inp, out, c)` and returns the output table; callable by `bench.global NutritionRevamp.bench_fast <n>`. `NutritionRevamp.bench_fast_input()` returns the filled input table for a test to read.

- [ ] **Step 1: Write the failing test.** `testing/tests/kernel/test_bench.py` loads the kernel host (the Plan 1 `host` fixture in `conftest.py`), then additionally loads `NR_Server_Bench.lua` under a shim that defines the Java globals the file names behind the side test as nils (the file must be loadable with no engine). Assert `NutritionRevamp.bench_fast` is a function, that calling it returns a table with a numeric `hunger` between 0 and 1, and that `NutritionRevamp.bench_fast_input().asleep == false` and its `M` and `D` are > 0 (a steady-state awake tick). Run: `python -m pytest testing/tests/kernel/test_bench.py -v` → FAIL (no such file).

- [ ] **Step 2: Write `NR_Server_Bench.lua`.** A `server/` file (it runs in both VMs; it names no Java global that must be present — it only reads `NutritionRevamp.kernel`). Module-level: `local NR = NutritionRevamp; local K = NR.kernel`; one filled input `BENCH_INP`, one output `BENCH_OUT` and the constants `BENCH_C = K.fast.defaults()`, built once at file scope from `K.fast.input()`/`K.fast.output()` and then populated to a steady-state awake tick (`M = 1`, `D = 24`, `sd = 1`, `asleep = false`, mid-range stats, every optional multiplier 1, `minutesPerDay = 60`, `fitnessLevel = 5`). `function NR.bench_fast() K.fast.step(BENCH_INP, BENCH_OUT, BENCH_C); return BENCH_OUT end`. `function NR.bench_fast_input() return BENCH_INP end`. No per-call allocation: the tables are reused, so the benchmark measures the step and not a constructor. A banner comment states this file exists only for the § 6 cost reading and ships with the mod.

- [ ] **Step 3: Run the test.** Run: `python -m pytest testing/tests/kernel/test_bench.py -v` → PASS. Then the kernel coverage gate: `python -m pytest testing/tests/kernel -q` → the gate still passes (this file is not a kernel file, so it is outside the coverage enumeration; confirm the suite count rose by the new tests).

- [ ] **Step 4: Gates and commit.** `kahlua_lint.py mod` → 0; `hotpath_lint.py mod` → 0 (the file is not a `NR_Kernel*` file and has no `@fastpath` region, so no fast-path rule applies); `mod_lint.py mod/NutritionRevamp` → 0 ERROR; `luabalance.py` on the new file BALANCED; `python -m pytest tools/tests testing/tests -q` green (+ the new tests). Commit: `git commit -m "Mod: NutritionRevamp.bench_fast for the cost-budget reading" -- mod/NutritionRevamp/common/media/lua/server/NR_Server_Bench.lua testing/tests/kernel/test_bench.py`. Write `task-2-report.md`. Return: status, commit hash, kernel suite count, concerns.

---

### Task 3: The entry-gate cost-budget session — Opus implementer (live), Opus reviewer

The § 6 budget: the takeover handler costs no more per player per tick than the seven vanilla updaters it replaces. This session reads `bench.global NutritionRevamp.kernel.fast.step` (and `NutritionRevamp.bench_fast`) for the per-call cost of the step, and `tick.rate` on a takeover boot beside an overlay boot of the same fixture for the whole-handler cost in context. It is the Plan 2 entry gate: a step cost far above the vanilla updaters' budget, or a takeover tick rate materially below overlay's, is a finding that sends overlay to the shipped default — recorded, not worked around.

**Files:**
- Create: `testing/experiments/x132_cost.py` (copied from `_template.py`, the house shape)
- Create (the run writes them; committed byte-identical): `testing/artifacts/x132c-<id>/cost.json`
- Create: `.superpowers/sdd/2026-10-05-plan-2-intake/task-3-claims-delta.tsv`
- Modify (the controller applies): `docs/areas/testing-your-mod.md` (the entry-gate sentence, now settled), `docs/reference/experiments.md`, `docs/reference/wall-map.md`, `docs/reference/artifacts.md`, `docs/reference/do-not-cite.csv`

**Interfaces:**
- Consumes: `NutritionRevamp.bench_fast` (Task 2); the profiles `nr-takeover` and `nr-overlay` (Plan 1); the bus commands `bench.global`, `tick.rate` (Plan 1).
- Produces: the settled cost reading — per-call µs for `bench_fast` and for `kernel.fast.step` with a filled input, takeover vs overlay ticks-per-second and world-minutes-per-second, and the entry-gate verdict (takeover within budget → proceed as planned; otherwise the overlay-default finding).

- [ ] **Step 1: Pre-flight.** `python testing/pzt doctor` clean. Confirm `nr-takeover` and `nr-overlay` exist and `NutritionRevamp.bench_fast` resolves offline (Task 2's test). This session runs no harness change, so no acceptance smoke test is owed; name the Plan 1 acceptance run `x131d-20261004-205257` as `ACCEPTANCE_RUN`.

- [ ] **Step 2: Write the driver.** `x132_cost.py` from `_template.py`. `PROFILE = "nr-takeover"`. Phases: **P1** `bench.global NutritionRevamp.bench_fast 100000` on the server (the whole step through the mod's entry point), its `usPerCall` the headline; **P2** `bench.global NutritionRevamp.kernel.fast.step 100000` — this needs arguments the step takes, which `bench.global` cannot pass, so P2 reads `bench_fast` as the step's proxy and records that `kernel.fast.step` is not directly benchable without arguments (a method note, not a failure); **P3** `tick.rate 10` on the takeover boot (ticks/s and world-min/s); then a **second boot** under `nr-overlay` repeating `tick.rate 10` as the control. Predictions (before the run): P1 `usPerCall` is a few µs (the step is arithmetic over ~24 stats, no allocation, Plan 1 benched `defaults()` the table constructor at ~2 µs); the takeover tick rate sits within a few percent of overlay's, because the handler replaces the seven updaters rather than adding to them. Falsifiers: `usPerCall` above ~50 µs (the step is doing per-call work it should not); takeover tick rate below 90 % of overlay's (the handler's per-player cost is material). Verdicts `as_predicted | falsified | trivial | unmeasured`.

- [ ] **Step 3: Run it.** `python testing/experiments/x132_cost.py`. One live session, two boots (takeover then overlay, serial). Copy the artifact byte-identical to `testing/artifacts/x132c-<id>/cost.json`.

- [ ] **Step 4: Read and grade.** From the artifact: the per-call cost, the two tick rates, and the entry-gate verdict. If the budget holds, the plan proceeds; if not, write the overlay-default finding and flag Task 11's hunger-term and Task 17's close that the shipped default may change — do not alter the plan's other tasks (the engine is built either way; only the shipped mode and the § 6 claim change).

- [ ] **Step 5: Claims delta and gates.** Delta rows (grade M, pointer `run:x132c-<id> cost.json <key>`): the `bench_fast` per-call cost; the takeover vs overlay tick rate; the entry-gate verdict. Settle the `testing-your-mod.md` § Open sentence that made this the entry gate (its line leaves § Open; mark the experiment row). Any `bench.global` artifact key that is read-gap noise goes in `do-not-cite.csv`. The artifact row in `artifacts.md` re-anchors the pointers it shifts. `claims_check.py --staged` → 0; `page_lint.py` on the pages → 0. The controller applies the delta and commits. Write `task-3-report.md`. Return: status, run id, the cost numbers, the entry-gate verdict, concerns.

---

### Task 4: The nutrient-vector schema, the seed data table and the loader — Opus implementer, Opus reviewer

The meal vector and the pool are one flat table of named scalars; this task fixes that shape, writes the hand-authored seed nutrient table for the foods and fluids the plan's sessions use, and writes the one loader every reader goes through. The kernel iterates the vector's own keys and hard-codes only the four macros, so Plan 4 adds a nutrient by adding a key.

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Nutrients.lua` (the seed table and the loader; not a kernel file)
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Vector.lua` (the vector shape and helpers)
- Create: `testing/tests/kernel/test_kernel_vector.py`

**Interfaces:**
- Produces: `NutritionRevamp.kernel.vector.MACROS` (the ordered list `{"calories","carbs","lipids","proteins"}`); `K.vector.new()` → a fresh zeroed vector of the seed's declared keys; `K.vector.add(dst, src, scale)` → `dst[k] = dst[k] + src[k]*scale` over the union of keys, allocation-free into `dst`; `K.vector.keys()` → the declared key list (macros plus the seed's mod nutrients `fibre, water, vitC, iron, phytate`). `NutritionRevamp.data.nutrients.get(fullType)` → the seed per-item vector (per the item's `state_baseline`, macros per item and the mod nutrients per item) or nil; `NutritionRevamp.data.fluids.get(fluidTypeString)` → the per-litre vector or nil. The seed covers at least: `Base.Apple`, `Base.Steak`, `Base.Bread`, `Base.Carrots`, `Base.Lettuce`, `Base.Tomato` (for the Salad dish), `Base.MincedMeat`/`Base.MeatPatty` (for the craft case), a butchered meat type (for the meat case), and the fluids `Cola`, `JuiceGrape`, `Water` (for the drink cases). Every seed entry carries `-- SEED <pz_id>` and the numbers come from `data/food-items.json`/`data/food-nutrients.*` where they exist (macros) and from the data-pipeline report's worked rows for the mod nutrients, or a labelled judgement where the pipeline has not run.

- [ ] **Step 1: Write the failing tests.** `test_kernel_vector.py`: load the host (the `conftest.py` host already loads every `NR_Kernel*.lua`; this adds `NR_Kernel_Vector.lua`, which the glob already catches, and `NR_Data_Nutrients.lua`, which the host must be taught to load — extend the host or load the data file in the test). Assert `K.vector.new()` returns a table whose keys are exactly `K.vector.keys()` and every value 0; `K.vector.add` accumulates with a scale and leaves `dst` the same table object (no allocation); `K.vector.MACROS` has the four macros in order; the seed loader returns a vector for `Base.Apple` with `calories` ≈ 95 and a non-nil `vitC`, and nil for an unknown type; the fluid loader returns a per-litre vector for `Cola` with `calories` ≈ 400 (the per-litre figure, [#0631]) and nil for an unknown fluid. Run → FAIL.

- [ ] **Step 2: Write `NR_Kernel_Vector.lua`.** Pure kernel. `K.vector = {}`; `K.vector.MACROS = {"calories","carbs","lipids","proteins"}`; `K.vector.KEYS = {"calories","carbs","lipids","proteins","fibre","water","vitC","iron","phytate"}` (the seed's worked set; Plan 4 extends it). `function K.vector.keys() return K.vector.KEYS end`. `function K.vector.new()` builds a zeroed table over `KEYS` (a `for` over a Lua table it built — allowed outside a `@fastpath` region; this is slow-clock code). `function K.vector.add(dst, src, scale)` loops `KEYS` and adds `(src[k] or 0) * scale` into `dst[k]`. One statement per line is not required here (only `NR_Kernel*` files are linted for kernel-oneline — this is a `NR_Kernel*` file, so it **is**; write it one statement per line, multi-line `for`/`if`). No Java, no `pcall`.

- [ ] **Step 3: Write `NR_Data_Nutrients.lua`.** The banner `-- NR_Data_Nutrients.lua -- not a kernel file: the seed per-type nutrient table and its loader (spec § 4.2, § 4.6; Plan 6 regenerates it).` `local NR = NutritionRevamp; NR.data = NR.data or {}`. Two tables keyed by full type and by fluid type string, each entry a flat vector of macros-per-item and mod-nutrients-per-item (or per-litre for a fluid), every entry `-- SEED <pz_id>`. The loaders `NR.data.nutrients.get`/`NR.data.fluids.get` return a shallow copy (so a reader cannot mutate the seed) built through `K.vector.new()` then filled, or nil. Macros from `data/food-items.json`; mod nutrients from the data-pipeline report's worked values (`Base.Apple` vitamin C from SR Legacy 171688, etc.) or a labelled judgement; phytate from the report's phytate discussion where a legume/grain, 0 otherwise.

- [ ] **Step 4: Run the tests and the coverage gate.** `python -m pytest testing/tests/kernel/test_kernel_vector.py -v` → PASS. `python -m pytest testing/tests/kernel -q` → the coverage gate still at 100 % over every `NR_Kernel*` file (every `K.vector.*` function is exercised by a test; `NR_Data_Nutrients.lua` is not a kernel file and is outside the enumeration). If a kernel line is uncovered, add the test that exercises it — never lower the gate.

- [ ] **Step 5: Gates and commit.** `kahlua_lint.py mod` → 0; `hotpath_lint.py mod` → 0 (the data file holds no kernel function and no `@fastpath`; confirm the lint does not treat `NR_Data_Nutrients.lua` as a kernel file — its name starts `NR_Data`, not `NR_Kernel`); `mod_lint.py` → 0 ERROR; `luabalance.py` BALANCED; `science_check.py --scan mod` → 0 (any `S` id the seed cites is settled). Commit the mod files and tests. Write `task-4-report.md`. Return: status, commit hash, the seed's covered types and fluids, the kernel suite count, concerns.

---

### Task 5: The four-source vector assembly — Opus implementer, Opus reviewer

The nutrient vector for one intake is assembled from four sources (spec § 4.2): the per-type baseline, dishes summed from the ingredient list scaled to the dish's macro total, crafted outputs from a consumed-type map, and animal meat scaled by raw hunger against the type baseline. This task grows `NR_Kernel_Vector.lua` with the pure assembly functions; the server wrappers (Tasks 8–10) feed them the item's own numbers read off the instance.

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Vector.lua`
- Modify: `testing/tests/kernel/test_kernel_vector.py`

**Interfaces:**
- Consumes: `K.vector.new/add/keys`, `NR.data.nutrients.get`, `NR.data.fluids.get` (Task 4).
- Produces, each pure (numbers in, vector out, no Java):
  - `K.vector.baseline(fullType, shareEaten)` → the seed vector for the type times the share, or nil if the type is unseeded.
  - `K.vector.dish(extraTypes, dishMacros)` → sum of each ingredient type's baseline (one entry per appearance in `extraTypes`, module stripped where the seed is keyed by full type), then **scaled so the summed macro total matches `dishMacros`** (the dish's own macros, read off the instance), recovering the cooking share the ingredient list does not keep ([jar read](../superpowers/research/jar-dishes-item-nutrients.md) § A, spec § 4.2); the mod nutrients scale by the same factor the macros needed.
  - `K.vector.meat(typeBaseline, rawHunger, baseHunger)` → the type baseline scaled by `rawHunger / baseHunger` (the butcher factor, accepting the ±11 % per-field noise, [jar read](../superpowers/research/jar-dishes-item-nutrients.md) § D, spec § 4.2).
  - `K.vector.craft(consumedCounts, shareEaten)` → sum of each consumed type's baseline times its count times the share, over the consumed-type-to-count map the hand-craft action writes ([#2667]).
  - `K.vector.fluid(fluidTypeVector, litres)` → the per-litre fluid vector times the litres drunk.

- [ ] **Step 1: Write the failing tests.** For each function, a test with hand-computed expectations: `baseline` scales Apple's vector by 0.5; `dish` over `{"Lettuce","Tomato"}` with a dish macro total scales the ingredient sum to that total and the Salad's measured macros at Cooking 0 (`25.0 kcal`, [#0301]) fall out when `dishMacros` is the measured dish; `meat` scales a steak baseline by `rawHunger/baseHunger`; `craft` over `{MincedMeat=40}` at share 1 sums 40 MincedMeat baselines (the MeatPatty case, [#0745]); `fluid` scales Cola's per-litre vector by 0.3 litres to the per-can figure ([#0634]). Include the nil/empty cases (an unseeded type contributes nothing and is named in a `missing` list the function returns beside the vector). Run → FAIL.

- [ ] **Step 2: Write the assembly functions.** Each one statement per line, multi-line `for`/`if`, no Java, no `pcall`. `dish` sums into a scratch vector, computes the summed macro total, divides the target `dishMacros` total by it to get the scale (guarding a zero denominator → scale 1 and a `scaled=false` flag), and scales every key; it returns the vector and a `{missing=…, scaled=…}` note table. `craft` and `baseline` return the vector and a `missing` list. Keep every function allocation-free except the one scratch vector each builds (these run on the slow-clock capture path, not per tick).

- [ ] **Step 3: Run the tests and the coverage gate.** `python -m pytest testing/tests/kernel/test_kernel_vector.py -v` → PASS. `python -m pytest testing/tests/kernel -q` → coverage 100 % over the kernel (every branch of `dish`'s zero-denominator guard and every `missing` path exercised; the kernel-oneline rule forbids a one-line branch precisely so the gate can see each). 

- [ ] **Step 4: Gates and commit.** The mod lints and `luabalance` as Task 4. Commit `-- mod/.../NR_Kernel_Vector.lua testing/tests/kernel/test_kernel_vector.py`. Write `task-5-report.md`. Return: status, commit hash, the five functions, the kernel suite count, concerns.

---

### Task 6: The state multipliers (retention) — Opus implementer, Opus reviewer

State modifies the vector per nutrient class (spec § 4.2, [data-pipeline report](../superpowers/research/food-data-pipeline.md) § B): cooked applies USDA retention factors per nutrient, burnt and rotten are labelled mod judgements, frozen is ~100 % with a small long-storage vitamin-C term. The engine itself applies no cooked/burnt/rotten/frozen modifier to the four macros except `Eat`'s ÷5 for burnt ([#0036], [#0019]), so the macros carry one composition and the mod's retention ladder moves only the mod nutrients — except that the vector the mod stores for a burnt item must already carry the ÷5 the eat applied to the macros, or it double-counts. This task writes the pure retention kernel.

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Retention.lua`
- Create: `testing/tests/kernel/test_kernel_retention.py`

**Interfaces:**
- Produces: `K.retention.CLASSES` (each mod-nutrient key tagged water-soluble / fat-soluble / mineral / stable, so a retention factor applies by class); `K.retention.apply(vector, flags)` where `flags = {cooked, burnt, rotten, frozen}` → the vector with per-class factors applied, the macros left to the caller (the eat wrapper applies the ÷5 burnt on the macros to match vanilla, the retention kernel applies the mod-nutrient factors); `K.retention.FACTORS` the per-class, per-state table (cooked from the report's worked USDA factors; burnt and rotten the labelled mod judgements; frozen the long-storage term). Each factor carries its `-- SEED`/judgement provenance; a cooked factor cites the USDA retention report row, a burnt/rotten factor is a `design-phase-v1` game choice.

- [ ] **Step 1: Write the failing tests.** `K.retention.apply` on a vector with `cooked=true` scales a water-soluble nutrient (vitC) by the cooked factor and leaves a stable one (fibre) unchanged; `burnt=true` scales every mod nutrient by the punitive burnt judgement and does **not** touch the macros (the caller owns the ÷5); `rotten=true` scales vitC/folate/thiamin-class only; `frozen=true` is ~1.0 with the small vitC term; no flag is identity. Run → FAIL.

- [ ] **Step 2: Write the kernel.** One statement per line, no Java, no `pcall`. The class table and factor table are module constants with provenance comments; `apply` loops the vector's keys, looks up each key's class, applies the state's factor for that class, and clamps a factor to ≤ 1 (retention ≤ 100 %, the report's structural check). Burnt and rotten factors carry their open-row/judgement tag.

- [ ] **Step 3: Run and coverage.** Tests PASS; kernel coverage 100 %.

- [ ] **Step 4: Gates and commit.** Lints, `luabalance`, `science_check --scan mod` (the cooked factors cite USDA report rows that may be science-register rows; if they are not yet in the register, the cooked factor is a `design-phase-v1` game choice until Plan 6's pipeline mints the retention rows — state which in the report). Commit. Write `task-6-report.md`. Return: status, commit hash, concerns.

---

### Task 7: The stomach, gastric emptying and absorption — Opus implementer, Opus reviewer

The vector lands in a stomach buffer; gastric emptying moves it into absorption over hours; absorption applies bioavailability, phytate and fat co-ingestion factors; the pool receives the result (spec § 4.2, § 4.4). This task writes the pure kernel for all three, over state tables the server adapter owns. The gastric-emptying constants (S0130, S0131) are **open** science rows, so they ship as labelled game choices (spec § 7 item 37); the absorption factors cite settled rows (phytate–iron S0195/S0532/S0533, iron bioavailability S0434/S0535, fat co-ingestion for carotenoids S0197/S0199/S0156).

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stomach.lua`
- Create: `testing/tests/kernel/test_kernel_stomach.py`

**Interfaces:**
- Produces, each pure:
  - `K.stomach.ingest(stomach, vector)` → add a meal vector into the stomach buffer (one buffer of named scalars plus a `fill` total driven by the meal's bulk; bulk is the macro energy plus a fibre/water term).
  - `K.stomach.empty(stomach, dtHours)` → first-order emptying: a fraction `1 - exp(-k·dt)` of each buffered nutrient leaves the stomach this step, `k` set from the half-time (S0130, a game choice) scaled by meal composition (S0131, a game choice: energy density, fat, fibre, liquid vs solid raise or lower `k`); returns the emptied vector and mutates the stomach. `exp` is allowed here — this is slow-clock code, not a `@fastpath` region, but the kernel-java rule still forbids naming a Java global, and `math.exp` is a Lua stdlib call the kernel may use on the slow path (confirm `hotpath_lint`'s kernel rules do not forbid `math.exp` outside a `@fastpath` region — they forbid Java globals and the one-line forms, not `math.*`; verify and, if the lint does forbid it, compute the fraction without `exp` via a bounded per-minute rate).
  - `K.stomach.absorb(emptied, context)` → apply per-nutrient bioavailability, the phytate–iron interaction (iron absorption reduced by the meal's phytate, raised by its vitamin C, S0195/S0533/S0534), and fat co-ingestion for fat-soluble nutrients (S0197/S0199), returning the absorbed vector; the unabsorbed remainder is discarded (it does not re-enter the stomach).
  - `K.stomach.toPool(pool, absorbed)` → add the absorbed vector into the pool (the provisional accumulator; Plan 4's record engine replaces the pool's elimination and ladders, but the pool's shape is fixed here).
  - `K.stomach.fill(stomach)` → the current fill scalar the fast clock reads for the hunger term.

- [ ] **Step 1: Write the failing tests.** `ingest` raises `fill`; `empty` over one hour moves the expected first-order fraction and leaves the buffer the rest; a fattier meal empties slower (S0131's fat term); `absorb` reduces iron by the phytate term and raises it by vitamin C against a control; `toPool` accumulates; `fill` falls as the stomach empties. Compute each expectation by hand from the constants in the file. Run → FAIL.

- [ ] **Step 2: Write the kernel.** One statement per line, no Java global, every science number tagged (`-- S0195`), every game-choice constant tagged `-- S0130 design-phase-v1` with its open-row id. The absorption interaction is a bounded multiplier, not a loop over dose lists (spec § 6 forbids per-tick dose loops — but this is slow-clock code, so a bounded `for` over the vector's keys is allowed; keep it a single pass). 

- [ ] **Step 3: Run and coverage.** Tests PASS; kernel coverage 100 % over the stomach kernel.

- [ ] **Step 4: Science part file and gates.** If the cited settled rows (S0195, S0532, S0533, S0194, S0534, S0535, S0197, S0199, S0156, S0413, S0418, S0357, S0358) are already in `science.tsv` (they are — verify each with `grep`), no science delta is needed; `science_check.py --scan mod` → 0 confirms every cited `S` id is settled. The open rows S0130/S0131 stay open; the kernel comment names them and the `design-phase-v1` tag. Lints, `luabalance`. Commit. Write `task-7-report.md`. Return: status, commit hash, the cited settled rows and the two open game-choice rows, concerns.

---

### Task 8: The eat and cancel wrappers — Opus implementer, Opus reviewer

The server-side wrapper of `ISEatFoodAction.complete` snapshots the item before the original runs, reads it again after, computes the share eaten as the drop in raw hunger over base hunger, assembles the vector from the right source, applies retention, and lands it in the player's stomach buffer. A wrapper of `serverStop` catches cancelled eats the same way. Both compose with QualityCooking's wraps (Task 1's ruling). This is the first task that touches the engine's Java-facing edge, so every Java member is read through the index-first guard, never assumed.

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Intake.lua`
- Create: `testing/tests/kernel/test_intake_shape.py` (the pure helpers the wrapper factors out)

**Interfaces:**
- Consumes: `K.vector.*`, `K.retention.apply`, `K.stomach.ingest`, `NR.data.nutrients.get`, the store `NR.server.store.get(username, worldAge)` (Plan 1), `NR.call` (the index-first guard), `NR.isServer`.
- Produces: `NR.server.intake` with `install()`/`uninstall()` (the wrappers, idempotent, sentinel in `NR_IntakeComplete_Installed`/`NR_IntakeServerStop_Installed` globals of their own); `NR.server.intake.captureEat(character, item, before, after)` → the vector landed (factored out as a pure-ish helper that takes the read numbers, so the arithmetic is testable without the engine); `record.stomach` on the player record gains the meal.

- [ ] **Step 1: Write the failing tests for the pure helper.** `test_intake_shape.py`: the share-eaten helper (`NR.server.intake.shareEaten(rawBefore, rawAfter, baseHunger)` → `(rawBefore - rawAfter) / baseHunger`, clamped 0..1, the drop in raw hunger over base hunger) returns 0.5 for a half-eaten apple; the source-selection helper (`NR.server.intake.sourceOf(itemFacts)` → `"dish" | "meat" | "craft" | "baseline"` from the item's `haveExtraItems`, its butcher marker, its craft-map modData key, else baseline) picks `dish` when the extra-items list is non-empty, `baseline` otherwise. These helpers are server-file functions with no Java; load them in the test the way `test_bench.py` loads `NR_Server_Bench.lua`. Run → FAIL.

- [ ] **Step 2: Write the wrappers.** The file opens with the banner and the two sentinel globals (`X = X or {}`). `install()` saves `ISEatFoodAction.complete` behind `NR_IntakeComplete_Installed` iff it is not already the mod's wrapper, replaces it with a wrapper that: guards on `NR.isServer()` (returns the saved original's result on a client); reads the item's pre-`Eat` facts (full type, raw hunger, base hunger, state flags, extra-items list, craft-map modData, container's player) through `NR.call`; calls the saved original; reads the item's post-`Eat` raw hunger; computes the share; selects the source; reads the item's own macros off the live item (or a fresh instance via `instanceItem` for the type baseline); assembles the vector (`K.vector.baseline/dish/meat/craft`); applies retention (and the ÷5 burnt on the macros to match vanilla); lands it in `record.stomach` via `K.stomach.ingest`; logs at level 3. A failure anywhere is caught by one `pcall` around the capture (never around the original — the original always runs) so a mod bug never blocks an eat. The `serverStop` wrapper does the same from the cancel path, reading the share from the net action's progress where the post-read cannot (the item may be consumed), and honours the two cancel guards ([#0112]): under the guard vanilla applies nothing, so the wrapper lands nothing. Both call the saved original on every path (QualityCooking composition).

- [ ] **Step 3: Wire install.** The wrappers install at `OnServerStarted` behind the side test, beside the fast handler's install (append to the existing `OnServerStarted` handler pattern, or a new one — the order is irrelevant because each install is idempotent). Overlay mode still installs the intake wrappers (intake is owned by the mod in both modes; only the stat-tick ownership differs between takeover and overlay).

- [ ] **Step 4: Run the helper tests and the coverage gate.** `test_intake_shape.py` PASS; the kernel coverage gate unaffected (the server file is not a kernel file). The wrapper body itself is proved live in Tasks 13–14, not under lupa (it needs the engine); the pure helpers are what the unit test covers.

- [ ] **Step 5: Gates and commit.** `kahlua_lint.py mod` → 0; `hotpath_lint.py mod` → 0 (the wrapper reads the item once per eat, not per tick, and has no `@fastpath` region); `mod_lint.py` → 0 ERROR; `luabalance.py` on the new file (HEAD has none, so working tree only) BALANCED; `pytest` green. Commit `-- mod/.../NR_Server_Intake.lua testing/tests/kernel/test_intake_shape.py`. Write `task-8-report.md`. Return: status, commit hash, concerns.

---

### Task 9: The drink wrapper — Opus implementer, Opus reviewer

A drink has no eat hook and no eat packet; the only seat is a server-side wrapper of `ISDrinkFluidAction:updateEat`, which the update, the animation event and the completion all reach and which calls `DrinkFluid` once per sip ([#2689], [#0085]). The wrapper reads the container's litres and mix before the call and its litres after; the difference is the litres drunk; the per-fluid table gives the per-litre vector. A drink from a world water source goes through `ISTakeWaterAction` and never reaches this wrapper ([#2690]) — this plan leaves that route out and names it.

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Intake.lua`

**Interfaces:**
- Consumes: `K.vector.fluid`, `K.stomach.ingest`, `NR.data.fluids.get`, `NR.call`.
- Produces: `NR.server.intake` gains the `ISDrinkFluidAction:updateEat` wrapper (sentinel `NR_IntakeDrink_Installed`), which reads the container (`getFluidContainer`, `getAmount`, `createFluidSample` → `size`/`getFluid(i)`/`getPercentage(i)`, [#2685]/[#2686]) before the saved `updateEat` runs and its litres after, lands the per-fluid vector for the litres drunk into the stomach, and always calls the saved original.

- [ ] **Step 1: The litres-drunk helper test.** Extend `test_intake_shape.py`: `NR.server.intake.litresDrunk(before, after)` → `before - after` floored at 0; the per-fluid vector helper sums each sampled fluid's per-litre vector times its proportion times the litres. Run → FAIL on the new asserts.

- [ ] **Step 2: Write the wrapper.** Save `ISDrinkFluidAction.updateEat` behind its sentinel; the wrapper guards on `NR.isServer()`, samples the container litres and mix before the saved call, calls it, reads the litres after, computes the litres drunk, builds the vector from the sampled mix and the per-fluid seed, lands it in the stomach, releases the fluid sample, and returns the saved call's result. Each sip is seen once because `updateEat` is idempotent (it consumes only the gap, [#0085]); a wrapper accumulating per-call litres sums to the whole without double counting. A `-- limitation` line names the world-water route (`ISTakeWaterAction`) as out of scope ([#2690]).

- [ ] **Step 3: Run and gates.** `test_intake_shape.py` PASS; lints and `luabalance` → 0/BALANCED; `pytest` green. Commit `-- mod/.../NR_Server_Intake.lua testing/tests/kernel/test_intake_shape.py`. Write `task-9-report.md`. Return: status, commit hash, the world-water limitation, concerns.

---

### Task 10: The crafted-output nutrient map — Opus implementer, Opus reviewer

A craft moves nutrition between instances; no vanilla arm carries item modData from an input to an output ([#2656], [#2660]), so a mod nutrient crosses a craft only where the mod writes it. The shipped hand-craft action already writes a consumed-type-to-count map into a single output's modData ([#2667], `ISHandcraftAction.lua`); the mod reads that map at eat time to assemble the crafted output's vector (`K.vector.craft`). This task wires the read and, only if the map proves unreachable, adds a wrapper of `ISHandcraftAction:performRecipe`/`ISAddItemInRecipe:complete` to write the mod's own consumed-type map (the X31 craft probe decides this — Plan 2 ruling 5).

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Intake.lua`
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Vector.lua` (if a normaliser is needed for the map keys)

**Interfaces:**
- Produces: the eat wrapper's source selection reads a crafted output's consumed-type map off its modData (the vanilla key the hand-craft action writes, a `fullType → count` map on a single output) and assembles the vector via `K.vector.craft`; where the output carries no such map (a dish built through the evolved path, or a multi-output craft), the source falls back to `dish` (the extra-items list) or `baseline`. A `-- limitation` line names the evolved-dish craft and the multi-output craft as the cases the vanilla map does not cover, deferred to X31 if a creation hook is needed.

- [ ] **Step 1: Confirm the map's shape.** Re-read `ISHandcraftAction:performRecipe` (`D:/SteamLibrary/.../ISHandcraftAction.lua`): the map is written only when `items:size() == 1`, as `modData[consumedFullType] = count`. Record that a vanilla modData census key census excludes the mod's own keys and vanilla's `customName`/`Tooltip` ([#1415]).

- [ ] **Step 2: Wire the read.** In the eat wrapper's source selection (Task 8), add the craft arm: if the item's modData holds a consumed-type map (a table of `fullType → number`, none of them the mod's own or vanilla's known keys), select `craft` and pass the map to `K.vector.craft`. Add a test to `test_intake_shape.py` for the map-detection helper (`NR.server.intake.craftMap(modDataKeys) → the map or nil`, excluding `VANILLA_ITEM_KEYS` and the mod's own prefix).

- [ ] **Step 3: Decide the hook.** If Task 15's co-boot or a craft probe (X31b) is needed to confirm the map is written on the live server, note it as a dependency the live task reads; do not add a craft wrapper unless the map is shown unreachable. The default (ruling 5) is no new hook: the vanilla map is the source.

- [ ] **Step 4: Run and gates.** Tests PASS; lints/`luabalance`/`pytest` → 0/BALANCED/green. Commit. Write `task-10-report.md`. Return: status, commit hash, whether a craft hook was needed (and why), concerns.

---

### Task 11: The slow-clock kinetics, the fast hunger term and the mirror — Opus implementer, Opus reviewer

The stomach, emptying and absorption run on the slow clock into the pool; the fast clock reads one stomach-fill scalar and derives HUNGER from it, with the energy-state term stubbed; the client mirror gains the stomach and pool scalars. This is where the engine becomes visible to the player and where vanilla's eat-time hunger write is overwritten within one push (spec § 4.2).

**Files:**
- Create: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Kinetics.lua`
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Fast.lua` (the hunger term reads stomach fill)
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Mirror.lua` (the stomach/pool scalars)
- Modify: `mod/NutritionRevamp/common/media/lua/client/NR_Client_Mirror.lua` (receive and hold them)
- Modify: `testing/tests/kernel/test_kernel_fast.py`, `testing/tests/kernel/test_kernel_mirror.py`

**Interfaces:**
- Consumes: `K.stomach.empty/absorb/toPool/fill`, the player record's `stomach`/`pool`, the slow clock's per-player minute work (`NR.server.players.onMinute`, Plan 1), the fast input/output (`NR_Kernel_Fast.lua`), the mirror builder (`NR_Kernel_Mirror.lua`).
- Produces: `NR.server.kinetics` appended to `onMinute` — per player per minute, `K.stomach.empty(record.stomach, dtHours)` → `K.stomach.absorb` → `K.stomach.toPool(record.pool, …)`, then stamps `record.stomachFill = K.stomach.fill(record.stomach)` for the fast clock to read; the fast kernel's hunger term reads a `stomachFill` input and derives the per-tick HUNGER target from it with the energy-state term a stubbed neutral input (`inp.energyState = 1`, a Plan 3 entry point), replacing the pure-drain hunger of Plan 1; the mirror carries `stomachFill` and the pool's scalars; the client holds them.

- [ ] **Step 1: The hunger-term test.** In `test_kernel_fast.py`, add: with a full stomach the hunger term holds HUNGER low (the player is sated); as `stomachFill` falls the hunger target rises; the energy-state input at its neutral 1 leaves the term at its stomach-only value; the term still clamps 0..1 and still writes once per tick. The Plan 1 vanilla-parity tests change here — the hunger arm is no longer the pure drain. Keep every other updater's test unchanged (thirst, fatigue, stress, idleness, morale, fitness, endurance are untouched by this plan). Run → FAIL.

- [ ] **Step 2: Write the fast hunger term.** In `NR_Kernel_Fast.lua`, replace the Plan 1 hunger-drain arm with a stomach-fill-derived target, inside the existing `@fastpath` region, one statement per line, reading `inp.stomachFill` and `inp.energyState` (both scalars the adapter fills; `stomachFill` from `record.stomachFill`, `energyState` stubbed 1). No loop, no allocation, no new Java member — the scalars come in on the input table the adapter already fills. Keep the burnt-divisor and every other arm. The comment names the Plan 3 entry point (`energyState`).

- [ ] **Step 3: Write `NR_Server_Kinetics.lua`.** A `server/` file appended to `NR.server.players.onMinute` at `OnServerStarted` behind the side test; per player it runs the emptying/absorption/pool chain and stamps `record.stomachFill`; it reads `dtHours` from the game clock the slow clock already has. The fast adapter (`NR_Server_Fast.lua`) fills `inp.stomachFill` from `record.stomachFill` and `inp.energyState = 1` — this is a one-line edit to the fast adapter's input fill, inside its `@fastpath` region, reading a hoisted handle to the record (the record is a Lua table, not a Java object, so it is not a hoisted Java member; the adapter already holds the record per player). If the fast adapter does not currently hold the record, add it to the per-player hoist (a plain table reference, allocation-free).

- [ ] **Step 4: The mirror.** `NR_Kernel_Mirror.lua` gains `stomachFill` and the pool scalars to the flat table `K.mirror.build` returns; `test_kernel_mirror.py` asserts they are carried; `NR_Client_Mirror.lua` already installs whatever the server sends, so the client holds them with no change beyond a test that the received mirror carries the new keys.

- [ ] **Step 5: Run, coverage, gates.** `test_kernel_fast.py` and `test_kernel_mirror.py` PASS; kernel coverage 100 % (the new hunger-term branches each exercised); `hotpath_lint.py mod` → 0 (the fast region still allocates nothing, loops nothing, holds its one `@rimguard`); `kahlua_lint`/`mod_lint`/`luabalance` → 0/0/BALANCED; `pytest` green. Commit. Write `task-11-report.md`. Return: status, commit hash, the Plan 3 stub entry point, the kernel suite count, concerns.

---

### Task 12: The profiles, the probe mods and the harness additions — Sonnet implementer, Sonnet reviewer

The live sessions (Tasks 13–15) need profiles and probe mods, and three harness additions that land first in their own commits under CLAUDE.md § 5. `drink.action` already exists (Plan 1); the additions this plan may need are a `player.sleep` that holds across a game-hour, a `player.walk` run arm that actually runs, a same-tick add-and-push trait command (the Plan 1 residual needs), and `craft.run` only if Task 10 showed the craft map unreachable.

**Files:**
- Create: `testing/profiles/x13-drink.toml`, `x13-eat.toml` (or document reuse of `x12-overrides.toml`), `x13-coboot.toml`, `x13-residual.toml`
- Create: `testing/experiments/TKX_DrinkHook/` (a server-side `ISDrinkFluidAction` wrapper counter, client twin for the side comparison)
- Modify (each in its own commit, if needed): `testing/PZTestKit/PZTestKit/42/media/lua/{server,client}/*.lua` (the sleep-hold, run, trait add-and-push commands), `docs/reference/harness-commands.md` (generated)

**Interfaces:**
- Produces: the profiles each in `mod-under-test.toml`'s shape, `[[verify]]` rows tier-(a) gates only (never the measurement that is the session's point); `TKX_DrinkHook` with `version`, a server and client per-side counter on `ISDrinkFluidAction:updateEat` and `complete`; the harness commands the residual arms need, each with its `@args/@reply/@purpose` block and the command table regenerated.

- [ ] **Step 1: The profiles.** `x13-drink.toml` (PZTestKit + NutritionRevamp + TKX_DrinkHook; the fixture's day length; `[client] timeout` normal); `x13-eat.toml` or reuse `x12-overrides.toml` (PZTestKit + TKX_EatHook + the mod for the X24/X33 session — confirm the mod loads beside TKX_EatHook); `x13-coboot.toml` (PZTestKit + a probe + ItemQuality + QuestSystem + MoodleFramework + QualityCooking + BeyondTen, each live tree named and dated, for X45a/X45b); `x13-residual.toml` (PZTestKit + the mod, a short day length, for the X34/X35/X4 residual arms). Each validated against the mod's `sandbox-options.txt` via `profile.declared_mod_options` where it sets `[sandbox.NR]`.

- [ ] **Step 2: TKX_DrinkHook.** A probe mod in the experiment shape (`testing/experiments/TKX_DrinkHook/42.20/…`), a `server/` file nil-checked on `isServer()` and sentinel-guarded outside any re-created table, wrapping `ISDrinkFluidAction.complete` and `:updateEat`, each bumping a per-side global-modData counter; a `client/` twin; `TKX_DrinkHook.version = 1` for the tier-(a) gate. Kahlua rules (no goto, no `%d` on a float, no `#` on a Java list).

- [ ] **Step 3: The harness additions, each in its own commit.** Only the additions a live task needs: (a) `player.sleep.hold <user> <seconds>` — sets and re-asserts the asleep flag each server tick for the window so the client's reset is overridden (the Plan 1 reading was that a plain set does not hold); (b) `player.walk` a run arm that sets running and queues a run the server copies (the Plan 1 reading was that the run arm only walked — diagnose whether `setRunning` before the action is enough or a different action is needed); (c) `trait.add.push <user> <trait>` — add a trait and `sendSyncPlayerFields(player, 2)` in the same server tick, with the server's `getTimestampMs` stamped, so X4's push arm is separable from the experience route. Each: append at the file end, re-anchor the `repo:` pointers the shift moves, `luabalance.py` (HEAD then working tree) BALANCED, `bus_inventory.py` regenerating `harness-commands.md`, `bus_inventory.py --check` in sync, the `@args/@reply/@purpose` block present, `pytest` green; the next acceptance run (Task 13's boot) is the smoke test. If (a) or (b) proves infeasible in the time, the residual arm stays unmeasured (written as such in Task 15) — the harness is improved where it can be, never faked.

- [ ] **Step 4: `craft.run` (only if Task 10 needs it).** If Task 10's report said the craft map is unreachable without driving a real craft, add a server-side `craft.run <user> <recipe> <input…>` in its own commit (the standing rule); otherwise skip it and say so.

- [ ] **Step 5: Gates and commits.** Each harness command is its own commit; the profiles and probe mod are one commit (`kahlua_lint.py testing/experiments` → 0, `mod_lint.py` on the probe → 0 ERROR, the profiles parse). `pytest` green throughout. Write `task-12-report.md`. Return: status, the commit hashes, which additions landed and which were deferred, concerns.

---

### Task 13: X13 — the drink wrap fires — Opus implementer (live), Opus reviewer

Is the drink path interceptable the way the eat path is — does a server-side wrapper of `ISDrinkFluidAction` fire, and on which side ([#1279], [#1133])? This session queues the game's own drink action through `drink.action`, counts `TKX_DrinkHook`'s per-side fires, and confirms the mod's own drink wrapper (Task 9) landed the intake. The control is the shipped `drink` command, which moves the stores (slice 05), so a `0/0` against a control that moved the stores is a silent Lua route, not a silent fluid path.

**Files:**
- Create: `testing/experiments/x132_drink.py` (from `_template.py`)
- Create: `testing/artifacts/x132d-<id>/drink.json`
- Create: `.superpowers/sdd/2026-10-05-plan-2-intake/task-13-claims-delta.tsv`
- Modify (controller applies): `docs/facts/eating-pipeline.md`, `docs/areas/eat-and-cook-hooks.md`, `docs/reference/wall-map.md` (B7), `docs/areas/open-questions.md` (X13), `docs/reference/experiments.md`, `docs/reference/artifacts.md`, `docs/reference/do-not-cite.csv`

**Interfaces:**
- Produces: X13 settled or open-with-run — the drink wrapper's per-side fire counts, the litres and vector the mod's wrapper landed, and the verdict that the drink path is (or is not) interceptable server-side; B7 on the wall map resolved; the mod's drink-intake path proved live or its gap named.

- [ ] **Step 1: Pre-flight and smoke.** `pzt doctor` clean; the acceptance run for this session is Task 12's harness smoke boot (or `x131d` if no harness command landed for this session). Profile `x13-drink`.

- [ ] **Step 2: Write the driver.** Phases: **P1** `drink.action Base.Pop2` (a Cola can) then poll `nutrition.get` on both sides for the arrival; read `TKX_DrinkHook`'s per-side counters (`witness.moddata global:TKX_Drink`) — predict server 1 / client 0 (the eat-path result, [#0928]); **P2** the mod's own landing — read the player record's `stomach` through a bus read (a `lua.global NutritionRevamp.server.players…` or a dedicated read; if none exists, read the mirror's `stomachFill` client-side after the drink) and confirm it rose; **P3** the control: `drink Base.Pop2` (the shipped command, stores move) beside the Lua route, so a silent wrapper is distinguishable from a silent fluid path. Predictions and falsifiers per the X13 spec; `field_count` asserts on every counter read; client-first paired reads.

- [ ] **Step 3: Run, copy, grade.** Run; copy the artifact byte-identical. Grade X13: counters at server 1/client 0 → the drink path is interceptable server-side (B7 CAN); the mod's stomach rose → the drink-intake path works end to end. A `0/0` against a moving control → the Lua route is silent (B7 finding); write it as such.

- [ ] **Step 4: Claims delta, pages, gates.** Settle #1279/#1133 (B7) with the run named; settle the eating-pipeline open rows X13 touches ([#0148], [#0671]); the owner sentences move to the settled form; the X13 line leaves open-questions; the wall-map B7 verdict and experiment table are marked `run x132d-<id>`. Artifact row re-anchors. `claims_check`/`page_lint` → 0. Controller applies and commits. Write `task-13-report.md`. Return: status, run id, the counts and the verdict, concerns.

---

### Task 14: X24 and X33 — eat hook per portion and the cancel guard — Opus implementer (live), Opus reviewer

Does `OnEat` fire once per eat or once per portion ([#1290], [#0929])? And does a cancelled eat of an item under the `serverStop` guard apply nothing at all ([#0112], [#1299])? These share one boot (session S-D, X24 first because X33's eats bump X24's cumulative counters). The session also proves the mod's eat and cancel wrappers (Task 8) land the right vector per portion and nothing under the guard.

**Files:**
- Create: `testing/experiments/x132_eat.py`
- Create: `testing/artifacts/x132e-<id>/eat.json`
- Create: `.superpowers/sdd/2026-10-05-plan-2-intake/task-14-claims-delta.tsv`
- Modify (controller applies): `docs/facts/eating-pipeline.md`, `docs/areas/eat-and-cook-hooks.md`, `docs/reference/wall-map.md` (B4/B5, B6), open-questions (X24, X33), experiments, artifacts, do-not-cite

**Interfaces:**
- Produces: X24 settled (once per eat vs once per portion), X33 settled (the guard applies nothing), and the mod-side readings — the eat wrapper's vector per portion, the cancel wrapper landing nothing under the guard; B4/B5 and B6 on the wall map resolved with the run named.

- [ ] **Step 1: Pre-flight.** `pzt doctor` clean; profile `x13-eat` (or `x12-overrides` reused — confirm the mod loads beside TKX_EatHook); acceptance run named.

- [ ] **Step 2: Write the driver (S-D shape, X24 first).** **X24:** `eat.action Base.Apple 0.25` ×4 on one instance, then `eat.action Base.Apple 1` on a fresh one; between each, client-first `witness.moddata player:admin TKX_eat_onEat_server,TKX_eat_onEat_client` (`field_count == 2`), `nutrition.get` brackets to prove each action completed; counters 4/4 = once per portion, 1/1 = once per eat (deltas against the preceding read, never zero). Also read the mod's stomach rise per portion. **X33 (second):** `eat.action Base.Apple 1` then client `player.stop` partway (into `serverStop`), bracketed by client-first `nutrition.get`/`stats.get`; a second item with `item.set admin <type> hungChange -0.005` (state-modified hunger under the guard) cancelled; three arms that must differ — a completed eat (stores move fully), a cancelled normal eat (stores move by progress), a cancelled `<=1` eat (stores move by nothing and the item is not consumed). Record the mod's cancel wrapper landing nothing under the guard.

- [ ] **Step 3: Run, copy, grade.** Grade X24 (4/4 or 1/1, each action proven complete) and X33 (the three arms differ; the guard arm applies nothing). The flag for the mod: the item pass must not land a hunger value under the guard (X33's design hazard) — note it for Plan 6.

- [ ] **Step 4: Claims delta, pages, gates.** Settle #1290/#0929 (X24) and #1299 (X33) with the run named; B4/B5 and B6 marked `run x132e-<id>`; the owner sentences and open-questions lines move. Artifact row re-anchors. Gates → 0. Controller applies and commits. Write `task-14-report.md`. Return: status, run id, the X24 and X33 verdicts, the item-pass hazard, concerns.

---

### Task 15: X45a co-boot and the Plan 1 residual arms — Opus implementer (live), Opus reviewer

QualityCooking and BeyondTen co-boot beside the mod (X45a, the compatibility reading), and X45b's composition measured live against TKX_EatProbe (Task 1 read the code; this measures the wrap composes and which is outermost). The same plan closes the Plan 1 residual arms where the Task 12 harness additions allow: X34's asleep and running arms (#2081), X35's running pairs (#2082), X4's push arm (#2099). An arm the harness still cannot drive stays unmeasured, written as such.

**Files:**
- Create: `testing/experiments/x132_coboot.py`, `testing/experiments/x132_residual.py`
- Create: `testing/artifacts/x132b-<id>/coboot.json`, `testing/artifacts/x132r-<id>/residual.json`
- Create: `.superpowers/sdd/2026-10-05-plan-2-intake/task-15-claims-delta.tsv`
- Modify (controller applies): `docs/facts/other-mods/*.md` (QualityCooking, BeyondTen), `docs/facts/character-stats.md` (the X34/X35 arms), `docs/platform/mp-model.md` (X4 push), `docs/reference/wall-map.md`, open-questions, experiments, artifacts, do-not-cite

**Interfaces:**
- Produces: X45a settled (the mods co-boot), X45b settled (the mod's eat wrapper composes with QualityCooking's, the outermost named); the residual arms settled or written unmeasured with the harness limitation named.

- [ ] **Step 1: The co-boot (X45a/X45b).** Profile `x13-coboot`. Boot PZTestKit + the mod + TKX_EatProbe + ItemQuality + QuestSystem + MoodleFramework + QualityCooking + BeyondTen; read each mod's marker on both sides (`QualityCooking.Server`, `BeyondTen.VERSION`, `TKX_EatProbe.version`, the mod's `NutritionRevamp.version`), the consoles grepped for Lua errors; one `eat.action Base.Apple 1`, then read TKX_EatProbe's `.enter`/`.exit`/`.outermost` and the mod's stomach rise, so X45b's composition is measured: the sentinel wrap survives one eat with the saved original called, the eat applies once, and `.outermost` names the order. A second boot without QualityCooking is the control.

- [ ] **Step 2: The residual arms.** Profile `x13-residual`. Only the arms Task 12's harness additions can drive: X34 asleep (`player.sleep.hold`) and running (`player.walk` run arm) beside the overlay control; X35 running pairs; X4 push (`trait.add.push` with a client first-change stamp). An arm whose harness command did not land is written `unmeasured` with the limitation named — never faked.

- [ ] **Step 3: Run, copy, grade.** Two sessions (co-boot, then residual), serial, one at a time. Copy both artifacts. Grade each arm; an unmeasured arm stays open with the run named in its bound.

- [ ] **Step 4: Claims delta, pages, gates.** Settle X45a (#2094), X45b (#2095) with the runs named; settle or re-scope X34 (#2081), X35 (#2082), X4 (#2099) per what the arms measured; the catalog and character-stats sentences move; artifact rows re-anchor. Gates → 0. Controller applies and commits. Write `task-15-report.md`. Return: status, the two run ids, each arm's verdict, which residuals stayed unmeasured and why, concerns.

---

### Task 16: The documentation delta — Sonnet implementer, Opus reviewer

Every page the intake engine touches gains its sentence, the router and tools page gain any new file, and the skills that quote a changed rule re-sync. The register deltas each live task filed are already applied; this task is the prose and the cross-references, not the register.

**Files:**
- Modify: `docs/areas/eat-and-cook-hooks.md`, `docs/areas/new-nutrients.md`, `docs/areas/item-pass.md`, `docs/facts/eating-pipeline.md`, `docs/facts/cooking-and-recipes.md` (the design-side sentences the engine settles), `docs/areas/testing-your-mod.md` (the profiles the plan shipped), `docs/reference/tools.md` (no new tool this plan — confirm), `CLAUDE.md` (§ 1 router only if an intake page moved; § 3 if a gate changed), `README.md` (the tree if a new Lua role appeared), the `.claude/skills/` that quote a changed rule line

**Interfaces:**
- Produces: the pages describing the intake engine as built, every claim tagged to its register row, the gates green.

- [ ] **Step 1: The page sentences.** Each design decision the engine settled (the three wrappers, the four-source vector, the seed table, the stomach/absorption chain, the gastric-emptying game choices, hunger-from-stomach) gets one tagged sentence on its owner page, rewriting the weaker existing sentence rather than duplicating it. The `testing-your-mod.md` profiles table gains the plan's new profiles.

- [ ] **Step 2: Roots and skills.** If a router row changed (an intake page's reading order), update CLAUDE.md § 1 and the skill that routes the same way; a rule line quoted in a skill re-syncs byte-identically (the rules-dup checker fails otherwise). If no route changed, say so.

- [ ] **Step 3: Gates.** `page_lint.py` on every page → 0; `claims_check.py --staged` → 0; `doc_lint.py` if the wall map or `references/` moved; `reference_gen.py cited-by --check`/`contradictions --check` in sync; `pytest` green. The controller commits. Write `task-16-report.md`. Return: status, the pages touched, whether a route or skill changed, concerns.

---

### Task 17: The close — Opus whole-pass review, fix wave, gates, memory, push

The plan closes after a whole-pass review, one consolidated fix wave and its re-review; the controller runs § 3, pushes, and updates CLAUDE.md and the memory file.

**Files:**
- Modify: `CLAUDE.md` § 3 count line; the memory files (§ 8)
- The ledger

- [ ] **Step 1: Whole-pass review (Opus, read-only).** A fresh reviewer reads the plan's Global Constraints, the spec § 4.2/§ 4.4/§ 5 row 2, and every task's committed content (`git show <commit>:<path>`), and checks: the three wrappers compose and always call the original; the vector is assembled from the right source per intake; the retention ÷5-burnt is not double-counted against vanilla's; the stomach/absorption chain cites settled rows and labels the two game choices; the fast hunger term allocates nothing and holds its one `@rimguard`; the pool's shape is the one Plan 4 will drain; every live arm settled, open-with-run, or written unmeasured; the entry-gate cost verdict recorded and the shipped default correct for it; the Plan 2 rulings each a ledger line.

- [ ] **Step 2: One consolidated fix wave.** Disjoint implementers on disjoint files (mod Lua Opus, pages/register the controller's delta); a scoped re-review of the fix diff (Sonnet). The controller applies tiny residuals.

- [ ] **Step 3: Close gates.** `claims_check` 0; `science_check` 0 and `--scan mod` 0; `mod_lint` 0 ERROR; `kahlua_lint` 0; `hotpath_lint` 0; `page_lint` 0 on every page touched; `cited-by`/`contradictions`/`bus_inventory` in sync; `doc_lint` 0 where it applies; `pytest` green at the new count (write it into CLAUDE.md § 3; the count never drops). Register and science-register row counts recorded.

- [ ] **Step 4: Memory and push.** Update the user-scope memory (`pz-nutrition-mod-project.md` PLAN 2 CLOSED block + `MEMORY.md`), the project-scope `nutrition-mod-design-phase.md` + `MEMORY.md`; the controller pushes `main`. Delete the plan's own research file (`qualitycooking-eat-wrap.md`) per § 6, its claims minted. Write the Rulings block into the ledger and `Plan 2: complete`.

---

## Self-Review

**Spec coverage (§ 4.2, § 4.4 stomach half, § 5 row 2, § 6 entry gate, § 7 items 1/18/19/37/39, § 8 experiments):**
- The three wrappers → Tasks 8 (eat + serverStop), 9 (drink). ✓
- The four-source vector (baseline, dish, craft, meat, fluid) → Tasks 4 (schema + seed), 5 (assembly), 10 (craft map). ✓
- State multipliers (cooked/burnt/rotten/frozen, burnt/rotten judgements) → Task 6. ✓
- Stomach buffer → emptying → absorption (bioavailability, phytate, fat co-ingestion) → pool → Task 7, driven by Task 11. ✓
- Hunger from stomach fill, vanilla overwritten next tick → Task 11 (energy state stubbed, ruling 4). ✓
- Cost: one item read per eat, nothing per tick → Tasks 8/11 (the per-tick term is one scalar read) and proved by Task 3 (the entry gate). ✓
- Entry gate (§ 6 cost budget, bench + tick.rate) → Tasks 2 (expose `bench_fast`) + 3 (the session). ✓
- The data pipeline is Plan 6; the seed table is the interface → ruling 1, Task 4. ✓ (A reviewer who expects the full data in Plan 2 should read ruling 1.)
- § 7 item 37 (gastric constants as game choices) → Task 7, ruling 2. ✓
- § 7 item 39 (handler-failure, inherited) → Global Constraints. ✓
- Experiments: X13 → Task 13; X24 + X33 → Task 14; X45a + X45b → Tasks 1 (code read) + 15 (live); X31 craft probe only if needed → Task 10/12 ruling 5; Plan 1 residuals X34/X35/X4 → Tasks 12 (harness) + 15 (arms). ✓

**Placeholder scan:** every task names its files, its interfaces with signatures, and its code shape; the kernel tasks give hand-computed test expectations; no "add appropriate handling" or "similar to Task N" without the code. The live tasks reference the house driver shape (`_template.py`) and the Plan 1 driver patterns rather than re-pasting 300 lines, which is the established convention. ✓

**Type consistency:** the vector is one flat table of named scalars throughout (`K.vector.new/add/keys`, `K.vector.KEYS`); the loaders return vectors of the same keys; the stomach/pool carry the same keys; the mirror carries `stomachFill` and the pool scalars; the fast input gains `stomachFill` and `energyState`. The source-selection strings (`baseline/dish/meat/craft`) match between Task 8's helper and Task 10's craft arm. The sentinel globals are named per wrapper (`NR_IntakeComplete_Installed`, `NR_IntakeServerStop_Installed`, `NR_IntakeDrink_Installed`). ✓

**Boundary risks flagged for the executor:**
- The fast hunger term (Task 11) changes Plan 1's vanilla-parity tests — the reviewer confirms only the hunger arm changed and every other updater's test is untouched.
- The energy-state term is stubbed (ruling 4); Plan 3 fills it. The kernel comment names it.
- The pool is provisional (ruling 3); Plan 4 replaces its elimination. Its shape is fixed here.
- `math.exp` in the stomach kernel (Task 7) is on the slow path; a probe confirmed `hotpath_lint`'s kernel rules forbid only Java globals and the one-line forms, not `math.*` outside a `@fastpath` region, so `1 - math.exp(-k*dt)` passes the lint in a kernel file. The `math` rule fires only inside a `@fastpath` region, which the stomach kernel has none of.
