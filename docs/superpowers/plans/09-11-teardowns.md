# Slices 09–11 — P3b–d Teardowns ×3 — Implementation Plan (one template, run three times)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three mod teardowns whose **MP section is measured, not inferred**: install the mod on the golden fixture through a profile, lint it, read every line of its Lua and scripts, then probe the *same* state on the server and on the client around the mod's own key action with the wave-3 witness commands — and write `docs/mods-survey/teardowns/<mod>.md` with every section of the shipped template filled, stamped, graded and sourced.

**Architecture:** One template executed three times. Slice 08 supplies the picks; Task 1 resolves the subject and reads it cold; Task 2 writes `testing/profiles/teardown-<mod>.toml` (the mod under test on `default`, `[[verify]]` probes that read the mod's *own* effect); Task 3 boots that profile from a Python driver on `testing/experiments/_common.py` and takes paired server/client witness snapshots around the action, writing one artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json`; Task 4 writes the doc; Task 5 lints, updates the ledgers and commits. Nothing here modifies the game install or the workshop folder — profiles copy.

**Tech Stack:** Python 3.13 stdlib, `pzt` (`profile`, `session`, `bus`), `PZTestKit` harness Lua, `tools/mod_lint.py`, `tools/doc_lint.py`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim row; brief commits without attribution (`Slice 09: …`); **one live server+client session at a time**; never `-safemode`; the game install and the workshop folder are **read-only**; take the default at every decision point and log it in `docs/decisions.md`; stdlib only; `cd` into the repo in every shell call (the cwd resets between calls).

---

## Header

- Slices **09 / 10 / 11** · Phase P3b–d · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: 07 (profiles, `mod_lint`), 08 (the picks + the witness commands) · Estimate: 2 h each, 6 h total.
- **This file is a template.** Run Tasks 1–5 once per mod: slice 09 = pass 1 (`N` = 1), slice 10 = pass 2, slice 11 = pass 3. One commit, one progress row and one artifact per pass.
- **Naming, fixed:** `<MOD>` = the id the mod's `mod.info` **declares**; `<ITEM>` = its workshop item id; `<mod>` = `<MOD>` lowercased with any vendor prefix dropped and non-alphanumerics stripped (`SKITTLE_LongTermPreservation4220` → `longtermpreservation4220`, `simpleStatus` → `simplestatus`). Files: `testing/profiles/teardown-<mod>.toml`, `testing/experiments/td<N>_<mod>.py`, `docs/mods-survey/teardowns/<mod>.md`, artifact `testing/artifacts/td<N>-<stamp>/`.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. Jar toolchain (rarely needed here): `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump`.
- **Profiles (slice 07).** `testing/profiles/<name>.toml`: `fixture`, `[[mods]]` (`id` / `workshop_id` / `path` / `copy = false`), `[sandbox]` (merged into the fixture's 189-key `SandboxVars.lua`, never replaced), `[server]`/`[client]`/`[run]`, and `verify` — bus probes run between `session_ready` and the hold, `expect` matched as a **substring of `json.dumps(parsed ack)`** (`testing/pzt/session.py:162-183`). Everything is resolved and validated before a process starts (`testing/pzt/profile.py`). Run: `python testing/pzt run --profile <name> [--hold N]`; a mod named in `Mods=` that never reaches `<cachedir>/mods` fails the run right after `server_started` (`mods_not_found` + `mod_missing_line` marks). Read `testing/profiles/mod-under-test.toml` — this plan's profiles are that file with the subject swapped.
- **Mod ids are not folder names.** `pzt/mods.workshop_index()` keys on the id in `mod.info` (229 mods indexed). Measured now: item `3774789651`'s folder is `LongTermPreservation4220` while its `42.20/mod.info` declares `id=SKITTLE_LongTermPreservation4220`, so `index["LongTermPreservation4220"]` is `None` and only the declared id works in `Mods=`. `data/mod-inventory.json` **is** authoritative for ids at HEAD, and the rule is: `mod_id` is the **engine-resolved** id — `mod_inventory.resolve()` imports `mod_lint`'s `version_dirs` / `info_chain` / `read_info`, so it reads the newest `42[.x[.y]]/` folder's `mod.info` first, then `common/`, then the root — and it is **`""`** when the mod declares none anywhere (1 row of 230), never the folder name; the folder name is kept beside it as `mod_id_fallback`. LTP's row therefore reads `mod_id: "SKITTLE_LongTermPreservation4220"`, `name: "Long Term Preservation [42.20]"`, `author: "Skittles"`. **52 of the 230 rows drift** from their folder name, so never key a profile on `folder`. *(pass 3)* **How `common/` and the version folder merge is now measured, not modelled:** the version directory's file **wins** a same-relative-path collision, `common/` supplies everything the version directory does not ship, and both end up in **one** Lua state — outcome **M** (`td3-20260911-001948`, five agreeing readings), mechanism **C** (`ZomboidFileSystem.loadMod` maps `commonDir` then `versionDir` with an unconditional `activeFileMap.put`, `L758`/`L773`; `LuaManager.LoadDirBase` dedupes by relative path with **vanilla's** block first; `Translator.tryFillMapFromMods` **merges** rather than reading that map, so a mod's translation file at a vanilla path does not cost vanilla its strings). **The bound travels with the rule:** it is measured on a mod whose `getVersionDir()` resolves to a tree that **ships colliding files**, n = 1. Two consequences a Task 1 needs on the first read — `common/` is never dead weight (it can hold the mod's only event registration), and a **shadowed** `common/` copy is **unexecuted code**, which is where a B41-era call can sit for a year without ever raising. The five readings are in `docs/mods-survey/teardowns/autocook.md` § Architecture.
- **Harness.** Global `TK` in `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`; `TK.register(name, fn(argv, kv))`, `TK.result(name, tbl)` → `<cachedir>/Lua/pzt-results/<name>.json`, and **every Java member goes through `TK.call(obj, "method", …)` → `(present, value)`** because Kahlua's "tried to call nil" escapes `pcall` and kills the whole event handler. No `goto`; never `%d` on a Lua number. Command inventory: `docs/testing/README.md`.
- **Wave-3 witness (slice 08's deliverable, shipped — consume it by name):** `witness.fields <player|item> <id> <getter,…>` and `witness.moddata [player[:<user>]|item:<id>|global:<name>] <key…>` (keys space-separated), registered in `shared/PZTestKit_Core.lua` so **both sides answer them**, documented in `docs/testing/README.md` § Command bus — which is the authority. **Both answer INLINE**, as a table on every path but the `argv[1]` usage gate. The client's older S6 round-trip was **renamed `witness.sync.moddata`** in the same slice to stop it shadowing the shared command on the client: that one, and its neighbours `witness.nutrition` / `witness.item`, still ack `"sent"`, send the question with `sendClientCommand`, and land the reply in `Events.OnServerCommand` where the client compares and writes `TK.result("witness_<kind>…")` (`client/PZTestKit_Client.lua:94-107,472-521`; `server/PZTestKit_Server.lua:394-430`). The Task-3 driver's `probe()` keeps its ack-then-result-doc branch for those, but against the two shipped commands the branch is **dormant** — they never ack `"sent"`.
- **Commands available on the bus** (all in `docs/testing/README.md`): client `eat.action <type>` (queues the real timed action; completes server-side), `moddata.set <k> <v>` + `moddata.transmit`, `text.get <translation key>` (since `291f977`), `item.spawn`, `stats.get`; server `stats.get <user>`, `nutrition.get/set <user> …`, `item.get/set <user> <type> …`, `item.use`, `drink`, `items.count`, `fluid.script <id>`, `recipes.count`, `recipes.craft <name>`, `recipes.evolved <name>`, `sandbox.set`, `trait.set`, `perk.set`, `perk.xp <user> <PerkName>`, `moddata.set <user> <k> <v>` (since `291f977`); and on **both sides** `item.script <type>`, `lua.global <name>[.<field>…]` (since `d8cc34e`) and the two `witness.*` commands. **The three newest are passes 2/3's and each exists for a reason a later pass will meet again:** `text.get` answers `{key, text, miss, side}` and a **miss returns the key itself**, which turns a mod's own prefixed translation key into a **tier-(a)** load probe for a mod that ships no scripts (pass 2 moved (b) → (a) on one); the server `moddata.set` is the exact twin of the client's and is what makes `transmitModData()`'s whole-table wipe **measurable** rather than inferred (plant a key on the server, watch it vanish); `lua.global` walks `_G` by dotted path on either side. Pass 2 also put `incWeight` / `incWeightLot` / `decWeight` into every `nutrition.get` / `stats.get` reply on both sides. (`item.script` was **client-only** when this plan was written — pass 1 mirrored it into `shared/` as `TK.scriptValues` in `37e411e`, and the reply now carries `side`. Reading it on both sides is what attributes a runtime desync to the packet rather than to a script mismatch: measured identical field for field, run `td1-20260910-192457`.) Items are spawned **server-side** with RCON `additem "<user>" "<fullType>" 1` (a client-side `AddItem` is invisible to the server — spike S6).
- **`recipes.craft <name>` READS a recipe script; it does not craft.** It answers the block's category, time, inputs and outputs off `media/scripts`, and **nothing on the shipped bus executes a `craftRecipe`** — there is no `CraftRecipeData` route. Consequence for every pass: a mod's `onCreate` / `onTest` / `OnCooked` **recipe** hooks are unreachable through a craft and stay **C** unless another route fires them. The routes that do execute something are: RCON `additem`, server `item.update` / `item.set` (which call `sendItemStats` and fire the `OnCooked`-class item hooks), `item.use`, `drink`, client `eat.action`, `moddata.set` + `moddata.transmit`, and `nutrition.set`.
- **MP facts the teardown measures against** (`docs/modding/patterns.md` § Measured MP sync facts): the **server** owns `Nutrition`, hunger/thirst, weight and item aging; a client write to any of them is overwritten inside ~1.5 s by the 1 Hz `PlayerStatsPacket`; `player:getModData()` reaches the server **only** after `player:transmitModData()`; a client's `sendItemStats` is a no-op; `ItemStatsPacket` **puts 43 fields on the wire, of which 39 are item state** — the other four are 2 addressing (`containerId`, `id`) and 2 presence flags (`isFluidContainer`, `isFood`), never applied to the item; see `docs/vanilla/food-item-model.md` § MP behaviour for the reconciliation and the pass-1 teardown's § MP handling for the names. The packet also reuses cached packets, so a zero-valued field can arrive carrying the previous packet's value.
- **Item state on a dedicated server ticks about every 5 s, not every frame** (M, runs `td1-20260910-192457` / `td1b-20260910-202029`): `InventoryItem.calculateTimeMultiplier`'s server arm is real-time-delta driven and clamped at 6 s. Two consequences for any probe design here — a timed read must not assume per-frame item updates, and a **bus call cannot be made the cause** of a server-side item transition (the tick wins the race; each bus call costs ~1 s round trip and the game-minute gate reopens every ~3.7 real seconds at the fixture's `DayLength = 4`). Whether the **client's** copy of a server-spawned item moves at all is **RESOLVED per arm** (pass 3, `td3-20260911-001948`): the carrier is the per-game-minute `sendItemStats` inside `Food.update`'s **cooking branch**, and the **1.6 heat gate is the discriminator**. Pinned *below* it (`heat 1.2`) the client's copy was **bit-frozen** — `1.2000000476837158` at both reads, **12.54 s** apart — while the server's decayed to the 1.0 floor; pinned *above* it (`heat 2.0`) the client's copy moved and stayed **bit-identical** to the server's (2 → 1.697029948234558 over 10.5 s, `td2-20260910-231655`); and pass 1's freeze (11.1 s, `td1-20260910-192457`) is the same below-gate arm. **M per arm** (n = 1 in each of three arms, three sessions), **mechanism C**. The refinement is what a probe design needs: below the gate the client's copy does not tick **at all** — it holds the last push — so a timed client read measures the **push schedule**, never a local simulation. Bounds: one item, one 12.54 s window, one fixture, with frozen/non-cookable items and every other push path untested. All three readings and the grading are in `docs/modding/patterns.md` § Measured MP sync facts.
- **Cadence ceiling.** `Events.EveryOneMinute` ceilings around 10 dispatches/wall-second: keep **`24 × speed / day_minutes ≲ 8`**. The fixture's `DayLength = 4` is **90 real minutes per game day** (`docs/testing/profiles.md`: `1` = 15 min, `4` = 1 h 30 m) — that is what `day_minutes` means in the formula, and the arithmetic only balances that way — so `--speed 30` sits exactly at 8.0; `DayLength = 1` (15 min) at `--speed 30` measured `ticks_per_world_min: 0.22`, `cadence_suspect: true` (`testing/artifacts/scenario-20260910-134012/scenario-smoke_clock.json`). **Teardown profiles therefore ship no `[sandbox]` block.**
- **Lint gates.** `python tools/mod_lint.py <path|workshop-id>` (L0 layout; ERROR fails); `python tools/doc_lint.py <dirs>` — `docs/mods-survey/teardowns` is a **stamped dir** (`tools/doc_lint.py:8`), so each teardown needs `Verified against: 42.20.4` in the text, a non-empty `## Sources`, no `TODO`/`TBD`, and a C/M/W grade in every row of any table with an `Ev` header column. `python tools/doc_lint.py docs/mods-survey` reported **4 findings** when this plan was written — the two seeded teardowns (`beyondten.md`, `itemquality.md`) had neither stamp nor `## Sources`. **Pass 1 backfilled them (`f8c6ceb`), so passes 2 and 3 start from `0 finding(s)` and expect 0 after their own doc.**
- **Evidence.** Measured JSON is committed byte-for-byte under `testing/artifacts/<run-id>/` with a row in `testing/artifacts/README.md`; full run dirs stay in gitignored `testing/runs/`.

## Questions (per mod; the teardown is done when each has a cited answer)

1. **Identity & build**: declared id vs folder name, workshop item, every version dir and the one B42 actually loads, `require=` dependencies, file mtimes, `mod_lint` verdict.
2. **What it does**, player-facing, in five lines.
3. **Architecture**: entry points (`Events.*`, timed-action derivations, context-menu hooks), data model (modData keys / sandbox options / item scripts / recipes), the client/server/shared split, and the files that matter.
4. **Overrides**: which vanilla functions it monkey-patches and which vanilla script blocks it redefines (name collisions against `media/scripts/`), and whether the patches are idempotent.
5. **Storage & wire**: exactly which modData keys on which object, and every `transmitModData` / `sendClientCommand` / `sendServerCommand` / `sendItemStats` site.
6. **MP, measured**: around the mod's key action, which side's copy of each field and modData key changes, whether the other side sees it, and within what window — plus where authority lives and whether the mod depends on an unsynced field (the ItemQuality failure mode).
7. **Compatibility**: load-order sensitivity, the API surface it patches, and collisions with the resident stack (the Girth mods' 228 command sites (2026-09-10), CleanUI's UI surfaces) and with our nutrition mod.
8. **Verdict**: what we adopt, what we avoid, dependency candidate or not.

## Method

### Task 1: Fix the subject and read it cold (no live server)

**Files:** Create `.superpowers/sdd/09-11-teardowns/<mod>-notes.md`.

- [ ] **Step 1: Resolve the subject.** Read `docs/mods-survey/nutrition-mods.md` § the pick and the slice-08 rows of `docs/decisions.md`; take the **first pick in slice 08's stated order that has no `docs/mods-survey/teardowns/<mod>.md` yet**. Default when that list is missing, shorter than three, or ambiguous: the queue in `docs/mods-survey/approved-modlist.md` § Teardown queue — **`SKITTLE_LongTermPreservation4220`** (item `3774789651`), **`simpleStatus`** (item `2867431511`), **`AutoCook`** (item `3388721641`), which is the order `docs/decisions.md:106` records. (Before pass 1 this line also said the queue "is also the three open questions in `docs/modding/patterns.md` § Open pattern questions"; it no longer is — pass 1 struck the LTP question, so that list is now `simpleStatus`, `MoodleFramework` and the Girth-namespacing question.) Write the resolved order into `docs/decisions.md` once (pass 1), then follow it.
- [ ] **Step 2: Identity (C).**

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/mod_lint.py <ITEM>
ls "D:/SteamLibrary/steamapps/workshop/content/108600/<ITEM>/mods"
python -c "import sys; sys.path.insert(0,'testing'); from pzt import mods; \
  print(mods.mod_id_of(r'D:\SteamLibrary\steamapps\workshop\content\108600\<ITEM>\mods\<FOLDER>'))"
```

  Expected: `mod_lint` exits 0 with at most INFO/WARN rows. Measured **2026-09-10**, for the three mods the passes actually lint: `3774789651` (pass 1) → `1 finding(s): 0 ERROR, 0 WARN, 1 INFO`, `folder-id: folder 'LongTermPreservation4220' != id 'SKITTLE_LongTermPreservation4220'`; `2867431511` (pass 2) → `1 finding(s): 0 ERROR, 0 WARN, 1 INFO`, `folder-id: folder 'SimpleStatus' != id 'simpleStatus'`; `3388721641` (pass 3, **AutoCook**) → `1 finding(s): 0 ERROR, 1 WARN, 0 INFO`, `mod-info-place: mod.info is common/mod.info, not 42.13/mod.info (B42 reads the version folder first)`. `mod_id_of` prints the id that goes in the profile. An **ERROR** row is a stop: record it and go to the next pick (decision points).
- [ ] **Step 3: Census and read (C).** `find <mod folder> -type f | sort`, `wc -l` on every `.lua`, then one sweep for the architecture signals:

```bash
grep -rnE "Events\.[A-Za-z]+\.Add|sendClientCommand|sendServerCommand|OnClientCommand|OnServerCommand|\
getModData|transmitModData|ModData\.|getNutrition|setCalories|setProteins|setLipids|setCarbohydrates|\
HungerChange|SandboxVars\.|ISBaseTimedAction:derive|^\s*function IS" "<live version dir>"
```

  Read **every** Lua file the sweep touches, end to end, plus every `media/scripts/**/*.txt` block. For each script block, check the name against vanilla: `grep -rl "item <BlockName>" "D:/SteamLibrary/steamapps/common/ProjectZomboid/media/scripts"` — a hit means an override, and its vanilla values come from `data/food-items.json` / `data/recipes.json` rather than a re-read.
- [ ] **Step 4: Cross-check the inventory row.** `python -c "import json;print([m for m in json.load(open('data/mod-inventory.json',encoding='utf-8')) if m['workshop_id']=='<ITEM>'])"` — record `signals`, `top_events`, `lua_kb`, `class`, and any disagreement with Step 3. The row's `layout` is `mod_lint.media_root`'s answer (`mod_inventory.resolve()` imports it, along with `version_dirs` / `info_chain` / `read_info`), so it and the lint cannot disagree by construction. Two live caveats instead: a zero in `stats`/`signals` is trustworthy only when `media_at` does **not** list `common/media` *(pass 3: the gap measured on one real subject — AutoCook's row misses **7 of 10 Lua files, 1 238 of 2 155 lines**, the mod's only event registration, its only vanilla patch and its whole translation set, and its `top_events: []` is correct for what the scan reads while being false about the mod)*, and `script_item_blocks` counts **every** item definition (clothing and vehicles included), so food is counted by hand off the `Type = Food` blocks.
- [ ] **Step 5: Notes.** Write `<mod>-notes.md` with one section per question 1–5 and 7, every claim carrying `mod-relative/path.lua:line`, plus a **Probe plan**: the getters the mod reads (question 5 → `FIELDS`), the modData keys it writes (→ `KEYS`), and the **one key action** Task 3 will trigger, chosen from this menu:

| What Task 1 found | Action Task 3 triggers | Read back |
|---|---|---|
| hooks eating / reads `Nutrition` | client `eat.action Base.Apple` (completes server-side) | fields on both sides at t0 and t+3 s |
| recipes / new items / script overrides | RCON `additem "<user>" "<Base.ModItem>" 1`, then server `item.update`/`item.set` on it (that is what fires the `OnCooked`-class hooks; `recipes.craft <ModRecipe>` only **reads** the script and executes nothing). **Read the guard state BEFORE the last `item.set` that opens the gate**, never after: the server's own item tick fires the transition on its own schedule, so a guard read taken after the flip grades "the server's tick won" as "`additem` spawned it already transitioned" | server `item.get` vs client `witness.fields item <id> …` |
| writes player modData | client `moddata.set <key> <v>` then `moddata.transmit` | `witness.moddata <KEYS>` on both sides, before and after the transmit |
| `OnPlayerUpdate` / `EveryOneMinute` simulation | RCON `settimespeed 30`, hold ≥ 60 s wall, restore `settimespeed 1` | snapshots each 20 s; `24 × 30 / 90 = 8.0`, at the ceiling |
| pure client UI, no state of its own | server `nutrition.set <user> calories 2000` | the fields the mod renders, on both sides, at t0 and t+3 s — the mirror it depends on |

- [ ] **Step 6: No commit.** `.superpowers/` is gitignored, so the notes file is the working read and a commit here would be empty. Task 1's deliverables are the notes and the report; the first commit of a pass is Task 2's profile.

### Task 2: The profile (no live server)

**Files:** Create `testing/profiles/teardown-<mod>.toml`.

- [ ] **Step 1: Write the profile** (this is `mod-under-test.toml` with the subject swapped; bare keys must precede the first table header):

```toml
# testing/profiles/teardown-<mod>.toml — slice 09-11 pass N: <MOD> under test on the golden
# fixture. No [sandbox] block: DayLength stays the fixture's 4 (90 REAL minutes per game day; that
# is the day_minutes term), which is what
# keeps 24 x speed / day_minutes <= 8 if the session accelerates time.
fixture = "default"
description = "PZTestKit + <MOD> (workshop <ITEM>) — teardown N."
run = { hold = 20 }
verify = [
  { side = "server", cmd = "<probe>", args = "<args>", expect = '<substring of the JSON reply>' },
  { side = "client", cmd = "<probe>", args = "<args>", expect = '<substring of the JSON reply>' },
]

[[mods]]
id = "PZTestKit"              # harness, copied from the repo (paths.HARNESS_MODS)

[[mods]]
id = "<MOD>"                  # the id mod.info DECLARES — never the folder name
workshop_id = "<ITEM>"
```

- [ ] **Step 2: Choose the `[[verify]]` probes**, in this order — a clean boot is *not* evidence the mod loaded (spike S3-A): (a) a bus probe that reads the mod's own state — `recipes.craft <ModRecipe>` and `item.script <Base.ModItem>` (both **script readers**: they prove the mod's definitions loaded, and neither executes anything), `items.count` (a `byType` delta), `witness.moddata <key>`; (b) if the mod has no readable state, leave `verify = []` and prove it in Task 3 by grepping the mod's own boot print out of the run's `clients/<user>/console.txt` / `server-stdout.log` with `session.grep_file`; (c) if it prints nothing either, the evidence is the copied folder under `<run>/server/mods/<FOLDER>` plus an empty `mods_not_found`, and the doc says "loaded; effect not directly readable" as an open question. Log (b) or (c) in `docs/decisions.md`.
- [ ] **Step 3: Validate offline** — `cd /c/Users/Angus/repos/project_zomboid && python -c "import sys;sys.path.insert(0,'testing');from pzt import profile;print(profile.load('teardown-<mod>'))"` → Expected `<Profile teardown-<mod> fixture=default mods=PZTestKit;<MOD> sandbox={}>`, **no java process started**. (`Profile.__repr__` prints exactly that string since `a16ad09`; before it the class had none and the expected output above was unproducible.) A wrong id raises `ProfileError` naming the 229 indexed mods; a mod with a `require=` dependency needs that dependency as its own `[[mods]]` entry **before** the subject (`Mods=` order is load order).
- [ ] **Step 4: Commit** — `git commit -m "Slice 0N: teardown-<mod> profile"`.

### Task 3: The measured MP session (LIVE — one session at a time)

**Files:** Create `testing/experiments/td<N>_<mod>.py`.

- [ ] **Step 1: Pre-flight** — `python testing/pzt doctor` → Expected: no PZ java processes, ports 27261/27262/27015 free, fixture `default` present and build-matched, workshop index ~229, exit 0. Do **not** boot on a FAIL.
- [ ] **Step 2: Acceptance run** — `python testing/pzt run --profile teardown-<mod> --hold 5` → Expected: a `profile name=teardown-<mod> fixture=default mods=PZTestKit;<MOD>` mark first, `server_started` ≈ 15 s, `client_ready` ≈ 35 s, every `verify … ok=True`, `RESULT: PASS`, exit 0, ≈ 1 min 15 s. Record the run id for the doc's Sources. A `verify` miss means the mod did not take effect: check `testing/runs/<run-id>/server/mods/` for the copied folder and grep `server-stdout.log` for `<MOD>` before changing anything.
- [ ] **Step 3: Write the driver** — **copy the shape of `testing/experiments/td1_longtermpreservation4220.py`** (pass 1's shipped driver, 518 lines at `e3afaa0`, 541 after the driver minors `4239c5d`; its follow-up micro-session `td1b_longtermpreservation4220.py` is the shape for a second, smaller round). Read it top to bottom before writing anything: it boots through the profile the same way the s05 shape does (`testing/experiments/s05_food_scan.py`), and it is the worked answer to every structural question this step used to pose as a skeleton.

  **What a pass changes, and it is a short list:** the **subject** (`MOD`, `PROFILE`, `ITEM`, and the `td<N>` run-id prefix passed to `new_run_dir`); **`FIELDS`** — the comma-joined, whitespace-free getter token, with `FIELD_COUNT` updated to match; **the scopes** — `ITEM_SCOPE` / `PLAYER_SCOPE` and their two **per-scope** exclusion sets; and **the action** — the one bus call that is `t_action`, with the guard read placed *before* it.

  **What the shipped driver has that this plan's old skeleton lacked** — take all of it:

  - **Provenance in `out`:** `harness_lua_commit` and `harness_lua_dirty` (the harness Lua's own commit and whether it was dirty at run time) and `doctor_clean` (the pre-flight verdict), beside `commit` and `acceptance_run`. An artifact that cannot say which harness produced it cannot be re-read later.
  - **Per-scope censuses with per-scope exclusion sets** (`census_row(reply, side, vanilla=...)`): the item set is `{customName}`, the player set is the four vanilla fitness keys plus `hotbar`. Applying the item set to a player census reports vanilla's own keys as findings.
  - **Client-first snapshot order, with the reason in the docstring:** every server `item.set` / `item.update` fires `sendItemStats` on its way out, so the client half of a baseline must be taken before anything is pushed, and after the action the earliest client read is the one that bounds the mirror window.
  - **A wall-bracketed `step()`** that records `wall_before` / `wall_after` / `took` around each sequenced bus call and lifts `serverWorldAge` / `gameMinute` out of the ack, so a game-minute rollover between two steps is measured rather than assumed.
  - **`field_count == FIELD_COUNT` asserted on every witness reply** (`field_count_ok`), which is what catches a `FIELDS` token silently truncated by a stray space.
  - **The re-ask-once guard:** `TK.writeKV` writes the ack file non-atomically, so a table reply can degrade to a raw string; a non-dict reply is re-asked exactly once and **both** readings are kept (`_probe.reasked`, `_probe.first_reply`).

  Two fragments of the ORIGINAL skeleton are kept here verbatim (byte-identical to `e3192d1`; the shipped driver has its own `probe()` docstring and `finally` block, which differ) because they are the parts most easily got wrong — the dormant-branch note that explains why `probe()` looks over-built, and the teardown-and-copy shape that makes the artifact survive a wedged session:

```python
def probe(side, cmd, args):
    """One witness read. `witness.fields` / `witness.moddata` answer INLINE (a table on every
    path but the argv[1] usage gate). The ack-then-result-doc branch below is the older
    client-witness shape -- `witness.sync.moddata`, `witness.nutrition`, `witness.item` -- and
    is DORMANT against these two; it is kept so a fallback to those needs no code change."""
    ...

except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    save(path, out, tl, server)
    try:
        teardown(tl, server, clients)
    finally:
        hard_kill(server, clients)
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "teardown-<mod>.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.copyfile(path, dest)
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
```

- [ ] **Step 4: Run it** — `python testing/experiments/td<N>_<mod>.py` → Expected: ≈ 3 min, three snapshots each carrying a `server` and a `client` block, `wrote …/teardown-<mod>.json`, the artifact copied. Any world change the action made (`settimespeed`) is restored in the same `try` before teardown. Record the run id.
- [ ] **Step 5: Read the result into claims.** For every field and key: which side moved, whether the other followed, and by when (`baseline` → `t0` → `t+3s`). A field that moved on the client and never on the server is an **unsynced-field authority** hazard (`docs/modding/patterns.md` FILTER 1) — say so. Do not re-run to make a number prettier; a surprising reading is the finding.
- [ ] **Step 6: Commit** — `git commit -m "Slice 0N: <MOD> measured MP session"` (driver + artifact).

### Task 4: The teardown doc

**Files:** Create `docs/mods-survey/teardowns/<mod>.md`; Modify `docs/mods-survey/README.md`, `docs/mods-survey/approved-modlist.md`, `docs/modding/patterns.md`, `testing/artifacts/README.md`.

- [ ] **Step 1: Fill the template.** `docs/mods-survey/teardown-template.md` is the fenced block to copy; every one of its parts is required — the three header bullets **Workshop ID / mod ID(s)**, **Build examined (date + version folder used)**, **Author · dependencies · license/permissions posture**, then `## What it does (player-facing)`, `## Architecture` (entry points, data model, client/server split, files that matter), `## MP handling` (what syncs, how, where authority lives, observed or latent desync risks), `## Techniques worth stealing` (with `file:line`), `## Pitfalls / anti-patterns` (and the rule we derive), `## Compatibility notes` (load order, patched API surface, conflicts), `## Verdict for our mod`. Add the two the template predates and `doc_lint` requires here: a **`**Verified against: 42.20.4 (`b0bbce05d5`)**`** line under the title with the date, and a final **`## Sources`** (the run ids and `testing/artifacts/<run-id>/…` paths, the mod files by path:line, the `data/mod-inventory.json` row, the workshop item id, any wiki mirror). Cite mod files as `mod-relative/path.lua:line` and pin the build (workshop id + folder mtime), as the template says.
- [ ] **Step 2: Grade `## MP handling` as a table** with an `Ev` column — one row per field/key measured, `M` with the run id for anything the session read, `C` for anything only read off the code, `W` for workshop/wiki claims. `doc_lint` enforces a C/M/W in every row of a table whose header contains `Ev`.
- [ ] **Step 3: Survey updates** — `docs/mods-survey/README.md`: move the mod from *queued* to a `[<Mod>](teardowns/<mod>.md)` row with why-chosen and status **done**; `approved-modlist.md`: drop it from § Teardown queue and add it to the *Done* line; `docs/modding/patterns.md`: close the § Open pattern question this mod answers (or restate it sharper), and add a KEEP/FILTER row if the teardown earned one; `testing/artifacts/README.md`: a Contents row `td<N>-<stamp>` / `teardown-<mod>.json` / `testing/experiments/td<N>_<mod>.py` / cited-by the new doc, plus a skew note if any fix round followed the run.
- [ ] **Step 4 (pass 1 only): Backfill the seeded teardowns.** Add the stamp line and a `## Sources` section to `docs/mods-survey/teardowns/beyondten.md` and `itemquality.md` — sources are the mod folders (`3765241705/BeyondTen`, `3624538051/ItemQuality`), `data/mod-inventory.json`, and for ItemQuality the pz-b42 `findings/crafted-weapon-quality.md` its own text already names. Do not restate their findings; those two were read, not measured, and stay C.
- [ ] **Step 5: Commit** — `git commit -m "Slice 0N: <MOD> teardown"`.

### Task 5: Lint and ledgers

- [ ] **Step 1: Gates** — `cd /c/Users/Angus/repos/project_zomboid && python tools/doc_lint.py docs/mods-survey docs/modding` → Expected `0 finding(s)` (0 since pass 1 backfilled the two seeded teardowns); `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → `0 finding(s)` whenever the pass rippled into those files; `python tools/mod_lint.py <ITEM>` → 0 ERROR; `python -m pytest tools/tests testing/tests -q` → green (281 at the end of pass 1).
- [ ] **Step 2: Ledgers** — `docs/progress.md`: write the resume note under the row (what landed, the run ids, what remains) and the **ripples** for the later passes and for slices 12–14 (a technique for 12/13, a jar-locked or unsynced surface for the wall map, a compat constraint for 14). `docs/decisions.md`: the pick order as applied, the `[[verify]]` tier used, any witness fallback or grammar ruling, any harness addition (one row each), any scoping ruling, any skipped pick.
- [ ] **Step 3: Commit `Slice 0N: ledgers` — and stop.** **No `git push`, and do not flip the board row to `done`.** The row stays `in progress` with the resume note until the pass's whole-branch review has run; the controller flips it and pushes at the pass close. Then return to Task 1 for the next mod, or, after pass 3, hand off to wave 4 (slices 12–14 plans).

## Worked example — the template applied to `simpleStatus` (written 2026-09-10 from the corpus; run and checked in pass 2, 2026-09-11)

The values below were read from the installed corpus while this plan was written; they are what Tasks 1–2 produce for this subject. **Pass 2 then ran it for real (2026-09-10/11) and checked all 17 of them: 13 agreed, 3 disagreed and 1 was wrong and load-bearing.** Every correction is folded into the bullets below and marked *(pass 2)* — read this section as verified, not as predicted, and treat the same way any future worked example that has not yet been run.

- **Task 1 Step 2.** `python tools/mod_lint.py 2867431511` → `2867431511/SimpleStatus: INFO: folder-id: folder 'SimpleStatus' != id 'simpleStatus'`, `1 finding(s): 0 ERROR, 0 WARN, 1 INFO`, exit 0. `mod_id_of` → `simpleStatus`. Version dirs `42`, `42.14`, `42.15`, `42.16`; B42 loads **`42.16`**, whose `mod.info` reads `id=simpleStatus`, `name=Simple Status`, `modversion=2.260406.1`, no `require=`. *(pass 2: `common/` is **not** a version dir — `mod_lint.version_dirs` returns 4 — and here it is an **empty directory**, 0 files, no `common/mod.info`; the item also ships a root-level `media/` tree of 47 files in the flat B41 layout, which `media_at` does list. Count the version dirs with the linter, and never read a `common/` entry in `media_at` as evidence that anything is in it.)*
- **Task 1 Step 3.** `42.16` ships **7 client Lua files, 1 580 lines**, no server and no shared **code** (`42.16/media/lua/shared/Translate/` holds 13 JSON, which is data). *(pass 2: it was **`42.15`** that dropped `server/ss.save.config.lua`, together with `client/ss.events.lua`, and the config store moved from **global** `ModData` with a server-side `OnInitGlobalModData` / `OnReceiveGlobalModData` pair to **per-player** modData at that version, not at `42.16`. A version-history claim has to be diffed against the version dir that actually changed.)* Reads `player:getNutrition():getCalories/getCarbohydrates/getLipids/getProteins/getWeight` at `ss.stats.lua:280,294,308,238,381` and the weight-direction flags `isIncWeight`/`isIncWeightLot`/`isDecWeight` at `ss.stats.lua:404-411`; hooks only `Events.OnCreatePlayer` and `Events.OnKeyPressed` (`ss.main.lua:82-83`); stores its UI config under **one** modData key, `player:getModData()["SimpleStatusConfig"]`, written by `savePlayerData` followed by `player:transmitModData()` (`ISSSBar.lua:18-36`, write `:34`, transmit `:35` — *(pass 2: the function begins at `:18`; `:15` is a comment and `:16-17` are `---@param` annotations)*) and read back at `ss.main.lua:15`; zero `sendClientCommand`, zero monkey-patching. Cadence answer for `docs/modding/patterns.md` § Open pattern questions: `SSBar:prerender()` calls `prepareBarInfo()` **every UI frame**, which calls `bar.valueFn(self.player)` (`ISSSBar.lua:451-470`, the unconditional call at `:464`, `:171`) — per-frame, uncached, client-side only, and *(pass 2)* it **understates**: `:236-238` re-enter `valueFn` up to three more times per bar per frame — up to **four** Java round trips per bar per frame against a source that moves at 1 Hz.
- **Task 1 Step 4.** Inventory row (item `2867431511`): `signals` `food_nutrition: 12`, `mod_data: 4`, `transmit_mod_data: 1`, `ui_panel: 1`, `events_add: 2`, `require_line: 2`; `lua_kb: 46`; `class: systems(light-lua)`; `layout: 42.16` — agrees with the census.
- **Task 2.** `verify` falls to tier (b) **on the bus as it stood**: the mod has no state a bus command can read at join (`SimpleStatusConfig` exists only after a player changes the bar), so `verify = []` and the took-effect evidence is its own print — which is **three** prints, in execution order `ss.main.lua:62` → `:13` → `:79`, grepped out of `testing/runs/<run-id>/clients/admin/console.txt` with one compiled regex each (`session.grep_file` takes a compiled pattern, so the brackets must be escaped). *(pass 2: this is where the tier moved. Task 3's harness commit added a client `text.get`, and the profile gained one **tier-(a)** row — `text.get IGUI_SS_BARTITLE_HAPPY` expecting `"Happiness"` (`IG_UI.json:7`; vanilla declares no `IGUI_SS_` key and a miss returns the key itself, so the row cannot pass unless the mod's translations loaded). `ok=True` on `run-20260910-230752`; the console grep was kept beside it. **A mod with no scripts is not automatically tier (b) — check its translation keys first.**)*

```toml
# testing/profiles/teardown-simplestatus.toml
fixture = "default"
description = "PZTestKit + simpleStatus (workshop 2867431511) — teardown 2."
run = { hold = 20 }
verify = []                   # tier (b) as Task 2 shipped it (a42c8b4): proof is the mod's own
                              # console line (ss.main.lua:62). Task 3's harness commit 291f977
                              # replaced this with a tier-(a) row:
                              #   { side = "client", cmd = "text.get",
                              #     args = "IGUI_SS_BARTITLE_HAPPY", expect = '"Happiness"' },

[[mods]]
id = "PZTestKit"

[[mods]]
id = "simpleStatus"           # declared id; the folder is 'SimpleStatus'
workshop_id = "2867431511"
```

- **Task 3.** Action menu row 5 (pure client UI): `FIELDS = "getInventoryWeight,getMaxWeight,isDead,isGodMod,getUsername"`, `KEYS = "player:admin SimpleStatusConfig"` (space-separated, explicit scope), action `ask(server, "nutrition.set", f"{USER} calories 2000")`. *(pass 2, and this was the worked example's one **wrong** value: `FIELDS` first read `getCalories,getCarbohydrates,getLipids,getProteins,getWeight` — the five macros the mod renders — but those getters live on `zombie/characters/BodyDamage/Nutrition` and `witness.fields`'s `player` subject resolves to the **`IsoPlayer`**, so every one of them would have landed in `missing` with `fields` empty, exactly as slice 08 measured for `getCalories`. **The macros are not a `witness.fields` question at all** — they come from `stats.get` / `nutrition.get` on each side, which is also where pass 2's weight-direction flags arrive. `FIELDS` is for getters that genuinely sit on the subject; the five above are the ones pass 2 used, and they double as controls that must not drift.)* What it measures is the mirror the mod is built on — the server-owned store arriving on the client inside the 1 Hz push — plus, as a second phase, `moddata.set SimpleStatusConfig …` + `moddata.transmit` on the client with `witness.moddata` on both sides on either side of the transmit, which is the boundary `ISSSBar.lua:35` depends on.
- **Expected verdict shape.** Adopt: nothing structural. Avoid: a per-frame uncached read of a server-owned store as *our* update path. Compatibility: it renders the same six numbers our mod will change, so an item-pass balance change is visible to users through this bar; it is a UI neighbour, not a dependency.

## Deliverables (per mod)

- `testing/profiles/teardown-<mod>.toml`
- `testing/experiments/td<N>_<mod>.py` + artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json` + its `testing/artifacts/README.md` row
- `docs/mods-survey/teardowns/<mod>.md` (stamped, graded, every template section filled, `## Sources`)
- Updates: `docs/mods-survey/README.md`, `docs/mods-survey/approved-modlist.md`, `docs/modding/patterns.md`, both ledgers
- `.superpowers/sdd/09-11-teardowns/<mod>-notes.md` (the working read; not a deliverable doc)

## Acceptance checks

1. `python testing/pzt run --profile teardown-<mod> --hold 5` → `RESULT: PASS`, exit 0, every `[[verify]]` probe `ok=True` (or the tier-(b)/(c) substitute recorded in `docs/decisions.md`).
2. `python tools/mod_lint.py <ITEM>` → 0 ERROR.
3. The artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json` exists and holds ≥ 3 snapshots, each with a `server` **and** a `client` block for the same fields and keys.
4. Every section of `docs/mods-survey/teardown-template.md` is filled in `docs/mods-survey/teardowns/<mod>.md`, and its `## MP handling` table has an `Ev` column with at least one **M** row citing the run id.
5. `python tools/doc_lint.py docs/mods-survey docs/modding` → `0 finding(s)` (0 before the pass as well, since pass 1's backfill); `python -m pytest tools/tests testing/tests -q` green.
6. Questions 1–8 each have a cited answer in the doc.

## Expected decision points (defaults)

- **Slice 08's picks are missing, fewer than three, or ambiguous** → the `approved-modlist.md` queue order, which is what `docs/decisions.md:106` records: `SKITTLE_LongTermPreservation4220` (3774789651) → `simpleStatus` (2867431511) → `AutoCook` (3388721641), with the fall-through `SkillRecoveryJournal` (2503622437) → `MoodleFramework` (3396446795) → `SomewhatTraitsCore` (3498347699). Log it once. *(pass 3: the queue is now **exhausted** — all three picks are torn down and no pass consumed a fall-through — so that list is re-labelled the **future-picks** list in `docs/mods-survey/README.md` and `approved-modlist.md`, which is where a fourth run of this template takes its subject. Two of the three carry a pass-3 reason: MoodleFramework is **whole on 42.20.4** under the merge rule slice 11 measured, and `SomewhatTraitsCore` is still the corpus's only **player** macro write.)*
- **A pick fails `mod_lint` with an ERROR, or is not installed** → skip to the next pick, record why in the catalog doc and `docs/decisions.md`; only if the queue runs out does the slice go `blocked` with the exact workshop id to subscribe.
- **The mod declares `require=`** → add each dependency as its own `[[mods]]` entry **before** the subject and lint it too. A dependency that is not installed blocks that pick, not the slice: move to the next pick.
- **Sandbox** → no `[sandbox]` block. `DayLength` stays the fixture's 4; if a teardown must run game-hours, use `--speed ≤ 30` and keep `24 × speed / day_minutes ≲ 8`.
- **Slice 08's witness commands answer in a different shape, or are absent** → they ship and they answer inline, but `probe()` still takes both shapes; if one is unusable, fall back to server `stats.get`/`nutrition.get`/`item.get` and the shipped client `witness.sync.moddata <key>` (renamed from `witness.moddata` in slice 08 so it no longer shadows the shared command) / `witness.item` / `witness.nutrition`, keep the rows **M**, and record the substitution in `docs/decisions.md`. **Pass 1 closed the parked scope-gate defect** (`witness.moddata item:` / `global:` with a trailing colon and no name was read as a modData key on the default `player` scope): fixed in `37e411e` as a lookup table, because Lua patterns have no alternation and `^(player|item|global):?$` cannot be written as one.
- **The harness is not frozen** (standing rule, 2026-09-10, superseding this plan's original "do not add commands to the harness in this slice"). A pass may add the harness surface its probe plan needs, under three conditions: every Java member is jar-confirmed first (`./pz.sh methods|dump`), the additions land in **their own commit ahead of** the session commit with `docs/testing/README.md` updated in it, and the acceptance run is their smoke test. Pass 1 added five (`37e411e`) and one more mid-pass (`903ccaa`); each is a `docs/decisions.md` row. What still does **not** belong in a pass is a change that reshapes every existing artifact — pass 1 found `TK.json`'s `%.6f` float rendering and deliberately left it for the start of pass 2.
- **The mod's action has no bus route** → measure its *read* path instead (menu row 5): a server-side write, then both sides' copies of the fields the mod renders. The MP claim is then about the mirror the mod depends on, which is the fact our mod needs.
- **The session logs non-baseline server errors caused by the mod** → that is the finding: keep the run, quote the lines in `## Pitfalls / anti-patterns`, and do not tune the profile to hide them.
- **The mod is too big for the 2 h box** (CleanUI is 1 MB of Lua) → read only the files the Task-1 sweep flags on the nutrition/food surface, say exactly that in `## Architecture`, and log the scoping. Never deliver a thin doc silently; a slice past twice its estimate is split into a new catalog entry.
- **A modData key holds a table** → the witness compares stringified values; record the shape from the code and the presence/equality from the run, and note the limitation rather than claiming a deep diff.
- **The mod overrides vanilla script blocks** → the vanilla side of the diff comes from `data/food-items.json` / `data/recipes.json`, not from re-parsing `media/scripts/`.

## Done protocol

- `docs/progress.md`: resume note while a pass is open; **ripples** for slices 12–14 — a technique the platform reference should prove (12), a jar-locked or unsynced surface for the wall map (13), a compatibility constraint for the feasibility notes (14) — and for the passes still to run. Row 09 / 10 / 11 → `done` (date, commit range, one-line outcome naming the mod and the run id) is the **controller's** edit at the pass close, not Task 5's.
- `docs/decisions.md`: the resolved pick order, each `[[verify]]` tier used, any witness fallback, any harness addition (one row each), any scoping ruling, any skipped pick.
- `docs/testing/README.md`: whenever a pass adds or changes a harness command, in the same commit as the Lua.
- `testing/artifacts/README.md`: one Contents row per pass, plus a skew note when a fix round followed that pass's live run.
- Commits per pass, subject line only, no attribution; **the pass does not push**. The controller pushes at the pass close, after the whole-branch review. Wave 3 is complete when 08–11 are all `done`; the next session writes the wave-4 plans (12–14) before continuing.
