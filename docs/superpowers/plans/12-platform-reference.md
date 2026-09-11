# Slice 12 — P2a Platform reference — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three VERIFIED modding docs — `docs/modding/anatomy.md`, `lua-api.md`, `item-overrides.md` — in which **every mechanism is either measured by an experiment mod we wrote (M) or cited to an earlier artifact / jar read (C)**. Nothing in these three files may rest on the wiki alone except where a W row is explicitly marked as corroboration.

**Architecture:** Five tiny mods of our own under `testing/experiments/`, installed through two profiles, driven by three Python sessions. Ours is the first subject in this library we *control*, so an experiment can ship the exact file that discriminates — which is what turns the corpus's read-only open questions (the id-read order, the folder≠id counterfactual, the B41-translation-layout hypothesis, the partial-block merge rule) into readings. Tasks 1–3 build the mods, the profiles and the one harness change offline; Tasks 4–6 run the three sessions; Tasks 7–9 write the three docs; Task 10 lints and files the ledgers.

**Tech Stack:** Python 3.13 stdlib, `pzt` (`profile`, `session`, `fixture`, `bus`), `PZTestKit` harness Lua, B42 script DSL, `tools/mod_lint.py`, `tools/doc_lint.py`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md` (row 12; § Tooling per wave — Wave 4).

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim row; brief commits without attribution (`Slice 12: …`), **pathspec** (`git commit -m … -- <paths>`), never `--amend`; **one live server+client session at a time**; never `-safemode`; the game install and the workshop folder are **read-only** — every byte this slice writes goes under `testing/experiments/`, `testing/profiles/`, `testing/artifacts/` or `docs/`; take the default at every decision point and log it in `docs/decisions.md`; stdlib only; `cd` into the repo in every shell call (the cwd resets between calls); a fresh implementer per task and per fix round, with a review between tasks whose lens is C/M/W; every `~:NN` citation re-located by content before it is quoted.

---

## Header

Slice **12** · Phase P2a · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: 07 (profiles, `mod_lint`), and the wave-3 findings of 08–11 · Estimate: 3 h.

**Naming, fixed.** Experiment mods are folders under `testing/experiments/`, named for the id they declare so `mod_lint`'s `folder-id` stays quiet — except mod D, whose drift is the point. Ids are `TKX_*` (TestKit eXperiment) so nothing can collide with a workshop mod. Drivers `testing/experiments/x12<n>_<slug>.py`; artifacts `testing/artifacts/x12<n>-<stamp>/<name>.json`. Mod folder names never end `.py`, so a driver and a mod never share a `sys.path` stem.

| Mod | Folder | Declared id(s) | Ships | Profile |
|---|---|---|---|---|
| A | `testing/experiments/TKX_ItemOverride` | `TKX_ItemOverride` | `42.20/media/scripts/` + two translation files | `x12-overrides` |
| B | `testing/experiments/TKX_Nutrient` | `TKX_Nutrient` | `42.20/media/lua/{shared,server,client}/` | `x12-overrides` |
| C | `testing/experiments/TKX_EatHook` | `TKX_EatHook` | `42.20/media/lua/{shared,server}/` + `42.20/media/scripts/` | `x12-overrides` |
| D | `testing/experiments/tkx-loader-probe` | **two**: `TKX_LoaderCommon` (`common/mod.info`), `TKX_LoaderVersion` (`42.20/mod.info`) | both trees, one colliding relative path | `x12-loader` |
| E | `testing/experiments/TKX_CommonOnly` | `TKX_CommonOnly` | `42.20/mod.info` only (**no `42.20/media`**) + `common/media/lua/shared/` | `x12-loader` |

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. Jar toolchain: `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump` (`WORKSPACE.md`). Game install `D:\SteamLibrary\steamapps\common\ProjectZomboid`, workshop `D:\SteamLibrary\steamapps\workshop\content\108600` — **both read-only**.
- **Profiles (slice 07, `docs/testing/profiles.md` is the authority).** `testing/profiles/<name>.toml`: `fixture`, `[[mods]]` (`id` / `workshop_id` / **`path`** — absolute or repo-relative, which is how a mod of ours goes under test — / `copy`), `[sandbox]` (merged, never replaced), `run`, `verify`. Bare keys precede the first table header. `expect` matches as a **substring of `json.dumps(parsed ack)`**. Resolution and validation happen before a process starts; `PZTestKit` is prepended when a profile omits it; **`harness.install` copies each source to `<mods_dir>/<mod id>`, renaming the folder to the id** — the fact mod D and session x123 exist to exploit. A mod named in `Mods=` that never reaches `<cachedir>/mods` fails a `pzt run` right after `server_started`; a green boot is **not** evidence a mod loaded (S3-A).
- **Harness.** Global `TK` in `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`; `TK.register(name, fn(argv, kv))`; **every Java member through `TK.call(obj, "m", …)` → `(present, value)`** because Kahlua's "tried to call nil" escapes `pcall` and kills the whole handler. No `goto`; never `%d` on a Lua number; `#` does not work on a Java list; `TK.json` renders numbers with `tostring` since `291f977` (earlier artifacts are six-decimal). Command inventory: **`docs/testing/README.md` § Command bus is the authority** — this slice uses server `item.get/set`, `items.count`, `item.script`, `nutrition.get/set`, `moddata.set`, `stats.get`; client `eat.action <type> [fraction]`, `text.get`, `item.script`; and on both sides `witness.fields <player|item> <id> <getter,…>` (one comma-joined whitespace-free token, zero-argument getters only), `witness.moddata [player:<user>|item:<user>/<fullType>|global:<name>] <key …>` (**space**-separated keys, `*` = census) and `lua.global <dotted path>` (never calls what it finds; `TK.version` is the control that must answer `1` on both sides).
- **Items are spawned server-side** with RCON `additem "<user>" "<fullType>" 1`; a client-side `AddItem` is invisible to the server (spike S6), and `eat.action`'s own `findOrSpawn` client spawn trips a server NPE — so always RCON first, then poll for the item.
- **MP facts this slice measures against** (`docs/modding/patterns.md` § Measured MP sync facts): the SERVER owns `Nutrition`, hunger/thirst, weight, traits, item aging and the Cooking perk; a client write is overwritten within ~1.5 s by the 1 Hz `PlayerStatsPacket`; `player:getModData()` reaches the server only after `transmitModData()`, which sends the WHOLE table and the receiver **wipes and replaces**; `ItemStatsPacket` carries 43 fields (39 item state) and reuses cached packets; a cooked food's thirst halves once per server→client hop; `Food.update` pushes once per game minute only while **`heat > 1.6f`** — the gate is **strict**, never `>=` (the jar: `ldc_w 1.600000023841858; fcmpl; ifle`), and the `td3` artifact's `carrier.gate` string says `>=` and is **do not cite**; item **scripts** load per side and never sync, so a script-declared value is identical on both sides for free (KEEP 11).
- **The mod-loading rules already established (slice 11, run `td3-20260911-001948`).** `ZomboidFileSystem.loadMod` maps `common/` (pass A, `@205-@216 L758`) then the version dir (pass B, `@396-@407 L773`) into `activeFileMap` with unconditional `put` — **the version dir wins a same-relative-path collision**, bounded to a mod whose version dir actually ships colliding files; `LuaManager.LoadDirBase` dedupes by relative path with vanilla's block first; `Translator.tryFillMapFromMods` **merges** translation JSONs rather than shadowing; the loader prints one `mod "<id>" overrides <relpath>` line per shadowed file, **twice on a client console** (two Lua states), so size every client grep `limit` at ≥ 2 × predicted + headroom. `HasTrait(String)`, `getTypeString()` and `loadstring` are **removed** on 42.20.4.
- **The two jar mechanisms this slice is built on, read 2026-09-11 and to be re-confirmed by the executor before they are quoted:**
  - **A duplicate script block does not create a second object — and for an `item` it RESETS the first.** `ScriptBucket.CreateFromTokenPP @88-@159 L168-L175`: when `loadData` already holds the name, the new body is **appended to `LoadData.scriptBodies`** on the existing object. `ScriptBucket.LoadScripts @140-@208 L252-L259` then replays the bodies in order, and when the type carries `ScriptType$Flags.ResetExisting` it calls `script.reset()` before **every body but the first** (`var5 = 1` on `ScriptLoadMode.Init`). `ScriptType.<clinit> @698-@705 L98` gives `ScriptType.Item` exactly that flag. **Prediction: a second `item Apple` in `module Base` is a wholesale REPLACEMENT, not a field merge** — mod A's Orange block is the falsifiable test.
  - **`ZomboidFileSystem.searchForModInfo @0-@173 L708-L735`** walks `File.list()` order depth-first, `readModInfo`s every `mod.info` it meets, registers each into `modIdToDir` and the caller's list, and **returns the first whose id equals the requested id** — not simply the first `mod.info` found. `ChooseGameInfo.readModInfo @0-@101 L157-L175` adds a second layer: an id already mapped is only re-pointed when the new dir sorts **earlier** in `getAllModFolders()`. `getAllModFoldersAux @124-151 L602` accepts a folder as a mod when `<mod>/common/mod.info` exists — **checked before** `<mod>/<versionDir>/mod.info`. This is the open question `docs/testing/profiles.md` § Open questions 1 names for this slice, and `tools/mod_lint.py`'s `info_chain` docstring defers to it. **Note the disagreement to test:** `info_chain` believes *newest version folder first*, while `File.list()` on NTFS is alphabetical, which puts `42` above `42.20`.
- **Evidence.** Measured JSON is committed byte-for-byte under `testing/artifacts/<run-id>/` with a row in `testing/artifacts/README.md`; full run dirs stay in gitignored `testing/runs/`. `python tools/doc_lint.py <dirs>` enforces, in `docs/vanilla`, `docs/modding`, `docs/feasibility` and `docs/mods-survey/teardowns`: the `Verified against: 42.20.4` stamp, no placeholder marker (`PLACEHOLDER_RX`, `tools/doc_lint.py:7`), a non-empty `## Sources`, and a C/M/W grade in every row of any table whose header has an `Ev` column (`tools/doc_lint.py:8,44-62`). Files ending `README.md` are skipped.
- **The harness is not frozen** (standing rule, Angus 2026-09-10): add the surface a probe plan needs, with every Java member jar-confirmed first, in **its own commit ahead of** the session commit, with `docs/testing/README.md` updated in the same commit, and the acceptance run as its smoke test. This slice plans exactly one such change, and it is **Task 3** — a whole task of its own, ahead of the first session.

## Questions (the slice is done when each has a cited answer)

1. What does a B42 `mod.info` declare, which file supplies the id, and **in what order does the engine read them** when a mod ships more than one?
2. How do `common/` and the version folder combine — and does the rule hold when the version folder ships **no `media/` at all**?
3. Does `Mods=<id>` still find a mod whose `<mods_dir>` folder name differs from the id by more than case?
4. Which translation layout does 42.20.4 load — `ItemName.json` or the B41 `ItemName_EN.txt` — and are mod translations consulted on a **dedicated server**?
5. What does `mod_lint` check, and which of its nine rules are engine readings versus models?
6. How does a mod override a vanilla item's nutrition: what exactly happens to the vanilla block, and what happens to keys the mod's block omits?
7. When two mods redefine the same block, which wins?
8. Where can a mod intercept eating in MP — which sides does `OnEat` fire on, and where does a Lua wrapper of `ISEatFoodAction:complete` fire relative to it?
9. Can a mod put a **new nutrient field** on item modData and have the client see it? On player modData? In which direction, and at what cost?
10. Which `Events.*`, which `Nutrition` / `Food` / `InventoryItem` / `IsoPlayer` members, and which script hooks has this library actually exercised — and which APIs are gone on 42.20.4?
11. What can Kahlua not do, and what does that force on mod code?
12. (Carried from slice 11) Do the weight-direction flags agree across sides under a **non-trivial** arm — calories driven above 1 000 or below 0?

## Method

### Task 1: The five experiment mods (no live server)

**Files:** create the five folders of the Header table.

- [ ] **Step 1: Mod A — `TKX_ItemOverride`.** `42.20/mod.info` (`name=`, `id=TKX_ItemOverride`, `description=`, `modversion=1.0`, `versionMin=42.0.0`), and `42.20/media/scripts/tkx_item_override.txt` holding, in one file:
  - **R1, full restatement.** `module Base { item Apple { … } }` — copy the whole vanilla block from `media/scripts/generated/items/food.txt` (18 keys; `ItemType = base:food`, `Calories = 95.0`, `HungerChange = -16.0`, `Carbohydrates = 25.13`, `DaysFresh = 5`) and change **only** `Calories = 400.0`.
  - **R2, partial block — the DEFAULT shape, narrowed on purpose.** `item Orange { DisplayCategory = Food, ItemType = base:food, Calories = 400.0, }` and **nothing else**. `ItemType` and `DisplayCategory` are **kept** so that a wholesale reset still leaves something that instantiates as a `Food`; only the **nutrition** keys are dropped, and they are the discriminators. This is the `ResetExisting` test: under a reset the rebuilt Orange keeps *only* those three and loses `hungChange` (−0.12), `carbohydrates` (16.27) and `DaysFresh` (6); under a field merge it keeps all of them. Do **not** ship the bare `item Orange { Calories = 400.0, }` — dropping `ItemType` would take Orange out of `items.count`'s `foodByModule.Base` **and** make it instantiate as a plain `InventoryItem` with no food getters at all, confounding M1's count and M2's reading at once.
  - **R7, the cross-mod collision.** `item Watermelon { … Calories = 111.0 … }`, again a full restatement of the vanilla block. Mod C declares the same name with `777.0`.
  - **R3, new items in our own module.** `module TKX { item FibreBar / FibreBarNamed / FibreBarJson }`, three identical food blocks — `DisplayCategory = Food, ItemType = base:food, Weight = 0.3, Icon = Apple, HungerChange = -20.0, ThirstChange = 0.0, Calories = 250.0, Carbohydrates = 30.0, Lipids = 5.0, Proteins = 8.0, DaysFresh = 42, DaysTotallyRotten = 84,`. `Icon` is set to a vanilla texture on purpose: a missing icon is client-side log noise this slice does not want to explain away.
  - **The display-name control**, which is why the three are identical: `42.20/media/lua/shared/Translate/EN/ItemName.json` = `{ "TKX.FibreBarJson": "TKX Fibre Bar Json" }` (bare `Module.Name` keys — the filename supplies the `ItemName_` prefix; vanilla's own file is the model), and `42.20/media/lua/shared/Translate/EN/ItemName_EN.txt` = the B41 table syntax `ItemName_EN = { ItemName_TKX.FibreBarNamed = "TKX Fibre Bar Named", }` (LTP `42.20/…/ItemName_EN.txt:3` is the model). `FibreBar` gets no entry anywhere. Three items, three translation states, one reading.
- [ ] **Step 2: Mod B — `TKX_Nutrient`**, the new-nutrient-field mod. Three Lua files under `42.20/media/lua/`, each opening with its own six-line `tkxCall` (index the member, then `pcall` it) — **never** depend on the harness's `TK` at file scope, and never call a Java member unguarded:
  - `shared/TKX_Nutrient.lua`: `TKX_Nutrient = { version = 1, ticks = 0, itemWrites = 0, side = "?" }` — the `lua.global` witness and the profile's gate.
  - `server/TKX_Nutrient_Server.lua`: `Events.EveryOneMinute.Add(fn)`. Each tick, for every `getOnlinePlayers()` entry: `md.TKX_fibre = TKX_Nutrient.ticks` (**no transmit** — arm 1); if `md.TKX_transmit_now` is set, clear it and call `player:transmitModData()` (arm 2, the server→client direction, which this library has never measured); then walk the player's inventory for `Base.Cheese` and, once per instance, `item:getModData().TKX_fibre = 12.5` followed by `item:syncItemFields()` (arm 3, the per-item nutrient route). Bump `TKX_Nutrient.itemWrites`.
  - `client/TKX_Nutrient_Client.lua`: the same event writing `md.TKX_fibre_client`, no transmit — the control that says which side wrote which key.
  - The driver triggers arm 2 with the existing server command `moddata.set admin TKX_transmit_now 1`. `EveryOneMinute` fires every **3.75 real seconds** at the fixture's `DayLength = 4` and `settimespeed 1`, so no time acceleration and **no `[sandbox]` block** is needed anywhere in this slice.
- [ ] **Step 3: Mod C — `TKX_EatHook`**, two interception points and a script collision.
  - `42.20/media/scripts/tkx_eat_hook.txt`: `module Base { item Banana { …full restatement…, OnEat = TKX_OnEatProbe, } item Watermelon { …full restatement…, Calories = 777.0, } }`.
  - `shared/TKX_EatHook.lua`: `TKX_EatHook = { version = 1, calls = 0, completes = 0, order = "", lastSide = "?", lastFraction = -1, lastCalories = -1 }` and the **global** `function TKX_OnEatProbe(item, character, fraction)` the script names — `LuaManager.getFunctionObject(food.getOnEat())` resolves a global by name (`IsoGameCharacter.Eat @762-@802 L5811-L5814`), and the file is `shared/` on purpose so **both** Lua states define it. The body bumps `calls`, appends `"onEat"` to `order`, records `fraction`, reads calories through `tkxCall(character:getNutrition(), "getCalories")`, and writes `TKX_eat_onEat_<side>` into the character's modData.
  - `server/TKX_EatHook_Server.lua`: a **sentinel-guarded, save-and-call** wrapper of `ISEatFoodAction.complete` (KEEP 4 — `if ISEatFoodAction and ISEatFoodAction.complete ~= TKX_EatHook._wrapper then …`), bumping `completes` and appending `"complete"` to `order`. In MP a client never runs `complete()`; the **server** does, inside `NetTimedAction.perform` (`docs/vanilla/eating-pipeline.md` § MP behaviour), so this is where a mod that wants the item *before* `Eat` has to sit.
- [ ] **Step 4: Mod D — `tkx-loader-probe`**, the loader discriminator. Folder name matches **neither** id, on purpose.
  - `common/mod.info` → `id=TKX_LoaderCommon`; `42.20/mod.info` → `id=TKX_LoaderVersion`. Everything else in the two files identical.
  - `common/media/lua/shared/TKX_Loader_Which.lua` → `TKX_LoaderWhich = "common"`; `42.20/media/lua/shared/TKX_Loader_Which.lua` → `TKX_LoaderWhich = "version"`. **One colliding relative path**, which is what makes the loader print its `overrides` line and what gives KEEP 10 a second subject on a mod we control.
  - `common/media/lua/shared/TKX_Loader_Common.lua` → `TKX_LoaderCommonTree = 1`; `42.20/media/lua/shared/TKX_Loader_Version.lua` → `TKX_LoaderVersionTree = 1`. Neither path collides, so both must be present under either merge direction — they separate "this tree did not win" from "this tree never ran".
- [ ] **Step 5: Mod E — `TKX_CommonOnly`**, the empty-version-dir arm KEEP 10 explicitly does not cover. `42.20/mod.info` (`id=TKX_CommonOnly`) and **no `42.20/media`**; `common/media/lua/shared/TKX_CommonOnly.lua` → `TKX_CommonOnly = { version = 1 }`.
- [ ] **Step 6: Lint, and record the two deliberate findings.** `cd /c/Users/Angus/repos/project_zomboid && python tools/mod_lint.py testing/experiments/TKX_ItemOverride testing/experiments/TKX_Nutrient testing/experiments/TKX_EatHook testing/experiments/tkx-loader-probe testing/experiments/TKX_CommonOnly`. Expected: **0 ERROR on A, B, C**; mod D **1 ERROR `id-agree` + 1 INFO `folder-id`** and mod E **1 WARN `media`** — all three are the experiments, not defects. Exit 1 is therefore expected on the combined sweep; run A/B/C alone for the clean exit. Log both in `docs/decisions.md`.
- [ ] **Step 7: Commit** — `git commit -m "Slice 12: experiment mods" -- testing/experiments/TKX_ItemOverride testing/experiments/TKX_Nutrient testing/experiments/TKX_EatHook testing/experiments/tkx-loader-probe testing/experiments/TKX_CommonOnly`.

### Task 2: The two profiles (no live server)

**Files:** create `testing/profiles/x12-overrides.toml`, `testing/profiles/x12-loader.toml`.

- [ ] **Step 1: Write them.** No `[sandbox]` block in either — `DayLength` stays the fixture's 4, which is what keeps `24 × speed / day_minutes ≲ 8` and what makes `EveryOneMinute` fire every 3.75 s at speed 1.

```toml
# testing/profiles/x12-overrides.toml — slice 12: the three surface mods on the golden fixture.
# Mods= order is LOAD order, and it is load-bearing here: TKX_EatHook is LAST, so its
# `item Watermelon` body is applied after TKX_ItemOverride's (ScriptBucket.LoadScripts replays
# the bodies in order) and Calories should read 777, not 111.
fixture = "default"
description = "PZTestKit + TKX_ItemOverride + TKX_Nutrient + TKX_EatHook — slice 12 session 1."
run = { hold = 20 }
verify = [   # one tier-(a) row per mod, each certain to pass IF the mod loaded at all; nothing
             # that is a measurement is used as a gate.
  { side = "server", cmd = "item.script", args = "TKX.FibreBar",      expect = '"DaysFresh": 42' },
  { side = "server", cmd = "lua.global",  args = "TKX_Nutrient.version", expect = '"value": 1' },
  { side = "client", cmd = "lua.global",  args = "TKX_EatHook.version",  expect = '"value": 1' },
]

[[mods]]
id = "PZTestKit"
[[mods]]
id = "TKX_ItemOverride"
path = "testing/experiments/TKX_ItemOverride"
[[mods]]
id = "TKX_Nutrient"
path = "testing/experiments/TKX_Nutrient"
[[mods]]
id = "TKX_EatHook"
path = "testing/experiments/TKX_EatHook"
```

```toml
# testing/profiles/x12-loader.toml — slice 12 sessions 2 and 3: the loader probes.
# TKX_CommonOnly is deliberately UNGATED: whether a version dir with no media/ still lets
# common/ load is the measurement, and a measurement must never be a [[verify]] row.
fixture = "default"
description = "PZTestKit + the two loader probes — slice 12 sessions 2 and 3."
run = { hold = 20 }
verify = [
  # TKX_Loader_Version.lua has no common/ counterpart, so it loads under EITHER merge
  # direction — which is exactly what makes it a gate and not a discriminator.
  { side = "client", cmd = "lua.global", args = "TKX_LoaderVersionTree", expect = '"resolved": true' },
]

[[mods]]
id = "PZTestKit"
[[mods]]
id = "TKX_LoaderVersion"          # the id `mods.mod_id_of` resolves (newest version dir first)
path = "testing/experiments/tkx-loader-probe"
[[mods]]
id = "TKX_CommonOnly"
path = "testing/experiments/TKX_CommonOnly"
```

- [ ] **Step 2: Validate offline** — `python -c "import sys;sys.path.insert(0,'testing');from pzt import profile;print(profile.load('x12-overrides'));print(profile.load('x12-loader'))"` → two `<Profile … fixture=default mods=PZTestKit;… sandbox={}>` lines and **no java process**. A `ProfileError` from `_mod_id_of` on mod D or E (the folder's own `mod.info` id disagreeing with the profile's) is itself an answer to question 1 about *this repo's* resolver: record it, and resolve it by changing the profile's `id` to whatever `python -c "…from pzt import mods; print(mods.mod_id_of(r'<folder>'))"` prints — never by editing the mod.
- [ ] **Step 3: Commit** — `git commit -m "Slice 12: experiment profiles" -- testing/profiles/x12-overrides.toml testing/profiles/x12-loader.toml`.

### Task 3: The one harness change — `text.get` on both sides (no live server)

**Files:** modify `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `.../client/PZTestKit_Client.lua`, `docs/testing/README.md`.

- [ ] **Step 1: Move the registration.** **Move** the `text.get` registration from `client/PZTestKit_Client.lua:110` into `shared/PZTestKit_Core.lua` (delete the client copy — do not register the name twice, or the client's definition shadows the shared one), exactly as slice 09 mirrored `item.script`. `getText` is a Lua **global** the engine exposes (`LuaManager$GlobalObject.getText(String, Object[])`, jar-confirmed in slice 10), so it stays nil-checked and called directly rather than through `TK.call`; the shipped body already answers `{key, side, error = "no getText() on this build"}` when the global is absent, and on a dedicated server **that reply is the finding for question 4**, not a bug to fix.
- [ ] **Step 2: The balance check.** First the bracket/keyword balance check the earlier passes ran (the slice-08 scratch tool `luabalance.py`: per harness Lua file the `{}` / `()` / `[]` deltas and the block `end`-depth, all five files BALANCED, run on the HEAD copies first and then on the working tree — write the 30-line script again if the scratch copy is gone: count openers `function|if|for|while|do` at statement start against `end`, and the three bracket pairs, ignoring `--` comments and string literals). Then `grep -rn 'TK.register("text.get"' testing/PZTestKit` → **exactly one** hit, in `shared/`. Then `grep -c 'TK.register(' ` on each of the three harness Lua files and reconcile the three totals against `docs/testing/README.md` § Command bus: every registered name is documented, every documented name is registered, and no name is registered twice. A mismatch is fixed here, offline, never inside a session.
- [ ] **Step 3: The README inventory line, in the same commit.** `docs/testing/README.md` § Command bus — move `text.get <IGUI key>` out of the client list into the both-sides group, keep the "a miss returns the key itself" note, and add one sentence saying the **server** half is unproven until `x121` M4 reads it.
- [ ] **Step 4: Commit** — `git commit -m "Slice 12: harness — text.get shared" -- testing/PZTestKit docs/testing/README.md`. This lands **before** any session commit; its smoke test is Task 4 Step 2's acceptance run.

### Task 4: Session 1 — the override, nutrient and eat-hook session (LIVE)

**Files:** create `testing/experiments/x121_overrides.py`; artifact `testing/artifacts/x121-<stamp>/platform-overrides.json`.

- [ ] **Step 1: Pre-flight** — `python testing/pzt doctor` → no PZ java processes, ports 27261/27262/27015 free, fixture `default` present and build-matched, exit 0. Do **not** boot on a FAIL.
- [ ] **Step 2: Acceptance run — and Task 3's smoke test** — `python testing/pzt run --profile x12-overrides --hold 5` → a `profile name=x12-overrides fixture=default mods=PZTestKit;TKX_ItemOverride;TKX_Nutrient;TKX_EatHook` mark first, `server_started` ≈ 15 s, `client_ready` ≈ 35 s, all three `verify … ok=True`, `RESULT: PASS`, exit 0. Record the run id. A `verify` miss means a mod did not take effect: check `testing/runs/<run-id>/server/mods/` for the copied folder and grep `server-stdout.log` for the id before changing anything. A traceback naming `text.get` means Task 3's move broke the shared file — fix the harness Lua and land it as a `Slice 12: harness — …` follow-up commit, before the driver is written.
- [ ] **Step 3: Write the driver — copy the shape of `testing/experiments/td3_autocook.py` and read it top to bottom first.** Everything structural is already solved there and all of it is required here: provenance in `out` (`commit`, `harness_lua_commit`, `harness_lua_dirty`, `doctor_clean`, `acceptance_run`), **client-first** reads at every tag, a **wall-bracketed** `step()` lifting `serverWorldAge`/`gameMinute` out of each ack, `field_count == FIELD_COUNT` asserted on every `witness.fields` reply, the **re-ask-once** guard for a table reply degraded to a string, **per-scope** modData exclusion sets (`{fitnessMod, fitnessUpTimer, strengthMod, strengthUpTimer, hotbar}` for a player census, `{customName, Tooltip}` for an item one), `grep_numbered` with a `limit` of ≥ 2 × predicted, and the `try/except/finally` that saves the artifact and copies it out even when the session wedges. Artifact `testing/artifacts/x121-<stamp>/platform-overrides.json`. The phases, each with its prediction and its falsifier written into the JSON beside the reading:

| # | Phase | What it does | Prediction (P) / falsifier |
|---|---|---|---|
| M1 | script census | server `items.count`; both sides `item.script` on `Base.Apple`, `Base.Orange`, `Base.Watermelon`, `TKX.FibreBar`. **A Base `item.script` yields no macro, by design:** `TK.SCRIPT_GETTERS` (`PZTestKit_Core.lua:207-211`) comes back with all four nutrition keys **absent** on a SCRIPT item — Kahlua does not expose them (measured slice 01, re-confirmed in `td1-20260910-192457`) — so a missing `Calories` here is the known gap, **not** a defect; only the instance getters of M2/M3 discriminate | **P1** `foodByModule.TKX == 3` and the **Base food count −0** against the baseline **722** (`testing/artifacts/exp05-20260910-084109/food-scan.json:350`; 1 005 is the dataset's *total item records*, not its food count) — a redefinition replaces, it does not add. 725 falsifies it. **721** says the narrowed Orange lost its `ItemType` after all and R2 must be re-read before M2 is graded |
| M2 | R1 + R2 | RCON `additem` Apple and Orange; server `item.get admin Base.Apple`; client `witness.fields item admin/Base.Apple getCalories,getCarbohydrates,getLipids,getProteins,getHungChange` (5, client first); the same pair for Orange | **P2** Apple `getCalories` **400** on both sides, every other macro at vanilla. **P3** Orange `getCalories` 400, with the `ResetExisting` replacement showing in **either** of its two readable forms: `getHungChange` and `getCarbohydrates` at **0** — Orange still instantiates as a `Food`, the dropped keys back at their defaults, the arm the narrowed R2 block is built to produce — **or** those two getters listed in the reply's `missing` set, which means Orange instantiated as a plain `InventoryItem` because the reset took `ItemType` with it. Both readings are the same finding (a wholesale reset) and the artifact must say which one it got. The falsifier is the same either way: −0.12 / 16.27 surviving is a **field merge** |
| M3 | R7 load order | the same pair on `Base.Watermelon` | **P4** `getCalories` **777** — the body of the mod later in `Mods=` is applied last. 111 means first-wins and inverts the rule |
| M4 | R3 + display names | both sides `witness.fields item admin/TKX.FibreBar{,Named,Json} getDisplayName,getFullType,getActualWeight,getActualWeightUnmodded` (4); both sides `text.get ItemName_TKX.FibreBarJson` and `…Named` | **P5** `Json` resolves its name and keeps a non-zero `getActualWeightUnmodded`; `Named` (B41 `.txt` only) and the untranslated `FibreBar` read `getDisplayName() == getFullType()` and **0**. That splits slice 09's hypotheses (ii) and (iii): a server-side hit on `Json` kills (iii), a miss on `Named` confirms (ii) |
| M5 | eat hooks | RCON `additem` Banana; client `eat.action Base.Banana 1.0`; poll `nutrition.get` both sides until calories move; then `lua.global TKX_EatHook.calls / .completes / .order / .lastSide / .lastFraction` on **both** sides and `witness.moddata player:admin TKX_eat_onEat_server TKX_eat_onEat_client` | **P6** `calls ≥ 1` on **both** sides — the server's from `Eat @762 L5811`, the client's from `EatFoodPacket` → `EatOnClient @0-@57 L5725-L5736`, which applies **no** numbers. **P7** `completes ≥ 1` on the **server only**, and `order` begins `"complete"` — the Lua wrapper runs before `Eat`. A client `completes ≥ 1` would overturn `LuaTimedActionNew.complete @31 L162` |
| M6 | nutrient field, player scope | census pair (client first) at join and at ≥ 40 s; then server `moddata.set admin TKX_transmit_now 1`, wait 2 game minutes, census pair again | **P8** `TKX_fibre` present **server-side only** before the transmit; after the **server-side** `transmitModData()` the client's census gains it and becomes exactly the server's — the untested direction of slice 10's wipe-and-replace |
| M7 | nutrient field, item scope | RCON `additem` Cheese; both sides `witness.moddata item:admin/Base.Cheese *` before and after the mod's write, with the item exclusion set | **P9** `TKX_fibre` reaches the client through `syncItemFields()` (`SyncItemFieldsPacket.processModData` wipes and replaces). If it does not, per-item custom nutrients are a CANNOT for slice 13 |
| M8 | carried from slice 11 | server `nutrition.set admin calories 1500`, wait ≥ 5 s, `nutrition.get` on both sides; then `calories -100`, wait, read again; restore to the baseline value in the same `try` | **P10** at weight 80 the gain threshold is `1000 + (80−80)·40 = 1000`, so 1500 takes the **incWeight** arm and −100 the **decWeight** arm; both sides should agree if the client recomputes the flags. A clamp at 0 on the negative write is itself the reading |
| M9 | the transmit **WIPE** half | server `moddata.set admin TKX_ServerOnly 1` — a key the client's copy has never held — **before** any client transmit; then client `moddata.transmit`; then the census pair again (client first), the **server** side included. Artifact key `transmit_wipe`, `{before, after}` per side | **P11** the server's census has **LOST** `TKX_ServerOnly` after the client's transmit: `KahluaTableImpl.load @5-@6 L333` wipes before it rawsets, so the receiver keeps only what the sender sent. Pass 3 corroborated wipe-and-**REPLACE** only; the wipe half still rests on the single pass-2 reading, and this takes it to **n = 2**. `TKX_ServerOnly` still present server-side falsifies it and says the receiver merges. One extra ack, no new commands — the server `moddata.set` docstring (`PZTestKit_Server.lua:115-131`) describes exactly this shape, and it is the **default**: run it |

- [ ] **Step 4: Run it** — `python testing/experiments/x121_overrides.py` → ≈ 4 min, `wrote …/platform-overrides.json`, artifact copied. **World changes restored in the same `try` before teardown**: the calorie store (M8) goes back to its baseline. The only other writes are modData keys the fixture does not own and the next run does not read — `TKX_transmit_now` (M6), `TKX_ServerOnly` (M9) and the mod's own `TKX_fibre*` — so they are left in place and **named in the artifact** rather than deleted (there is no delete on the bus). `lua.reload` is never sent — mod C's `ISEatFoodAction` wrapper is sentinel-guarded but the vanilla file re-executing would still re-enter it.
- [ ] **Step 5: Read the result into claims**, then **commit** — `git commit -m "Slice 12: override/eat-hook/nutrient session" -- testing/experiments/x121_overrides.py testing/artifacts/x121-<stamp>`. Do not re-run to make a number prettier; a surprising reading is the finding.

### Task 5: Session 2 — the loader session (LIVE)

**Files:** create `testing/experiments/x122_loader.py`; artifact `testing/artifacts/x122-<stamp>/platform-loader.json`.

- [ ] **Step 1: Pre-flight and acceptance** — `python testing/pzt doctor`, then `python testing/pzt run --profile x12-loader --hold 5` → `RESULT: PASS`, the one `verify` row `ok=True`.
- [ ] **Step 2: Write and run the driver**, the `td3` shape again, same provenance and guard rules. Four readings:
  - **L1, the id read.** `grep_numbered` the server log and the client console for `loading TKX_LoaderVersion` **and** `loading TKX_LoaderCommon` (`limit = 6` server, `12` client — the client prints once per Lua state). **P12:** the engine announces the id it was asked for (`TKX_LoaderVersion`); `TKX_LoaderCommon` is registered into `modIdToDir` on the way past but is not the mod that loaded. Both lines, or the other one, rewrites `mod_lint.info_chain`'s model.
  - **L2, the merge rule, second subject.** `grep_numbered` both logs for `mod "TKX_LoaderVersion" overrides` — **P13:** exactly one line, tail `media/lua/shared/tkx_loader_which.lua` (twice on the client console). Then `lua.global TKX_LoaderWhich` on **both** sides — **P14:** `"version"`, with `TKX_LoaderCommonTree` and `TKX_LoaderVersionTree` **both** resolving, which is what separates "common lost the collision" from "common never ran".
  - **L3, the empty-version-dir arm.** `lua.global TKX_CommonOnly.version` on both sides. **P15:** resolves — pass A maps `common/media` into `activeFileMap` and pass B adds nothing, so a version dir that ships only a `mod.info` costs the mod nothing. A `resolved: false` is the opposite finding and is equally citable; it is deliberately not a `[[verify]]` gate.
  - **L4, the control.** `lua.global TK.version` on both sides must answer `1`, or the walk is broken rather than the globals absent.
- [ ] **Step 3: Commit** — `git commit -m "Slice 12: loader session" -- testing/experiments/x122_loader.py testing/artifacts/x122-<stamp>`.

### Task 6: Session 3 — the folder≠id counterfactual (LIVE, server only)

**Files:** create `testing/experiments/x123_folder.py`; artifact `testing/artifacts/x123-<stamp>/platform-folder.json`.

- [ ] **Step 1: Why this needs its own session and its own driver.** `docs/testing/profiles.md` § Open questions 6 records the second half as **out of reach from a profile**, because `harness.install` copies every profile source to `<mods_dir>/<mod id>` (`testing/pzt/harness.py:27-32`) and the fallback that keeps a folder name is unreachable on the `--profile` path. A **driver** can reach it: `make_server` installs the mods inside `s.seed()` (`testing/pzt/session.py:143`, `server.py:181-185`) and returns **before** `s.start()`. So between the two calls, rename `os.path.join(server.cache, "mods", "TKX_LoaderVersion")` to `…/TKX_DriftedFolder` — a name differing by more than case, which is what NTFS's case-insensitive lookup makes necessary — leaving `Mods=TKX_LoaderVersion` untouched. No client is attached, so the session costs ~40 s.
- [ ] **Step 2: The readings.** After `server.start()`: `server.mods_not_found`; `grep_numbered(server.log_path, …)` for `loading TKX_LoaderVersion` and for `required mod "TKX_LoaderVersion" not found`; the server bus (which polls on `OnTick` with no client present) answering `lua.global TKX_LoaderWhich` and `TK.version`. Record the directory listing of `<run>/server/mods/` verbatim as `folder_check`, the way `td1`'s did. **P16:** if the mod still loads, the loader resolves through `mod.info` (consistent with the 52 drifting workshop folders that load in normal play) and `harness.install`'s rename is a convenience; if it does not, the rename is **required** and profiles.md OQ 6 closes the other way. Either answer closes it **M**.
- [ ] **Step 3: Do not call `verify()`** — every row of `x12-loader`'s `verify` is client-side and `session.verify` would record `no client attached`, which is not evidence. Teardown with `teardown(tl, server, [])` then `hard_kill(server, [])`.
- [ ] **Step 4: Commit** — `git commit -m "Slice 12: folder-drift counterfactual" -- testing/experiments/x123_folder.py testing/artifacts/x123-<stamp>`.

### Task 7: `docs/modding/anatomy.md`

**Files:** create `docs/modding/anatomy.md`.

- [ ] **Step 1: Write it** to the house system-doc skeleton — five-line summary → model → code map → **MP behaviour** → discrepancies → open questions → `## Sources`; header line: a bold **Verified against: 42.20.4 (`b0bbce05d5`)** plus the date, in the exact spelling `doc_lint`'s `STAMP_RX` matches. Sections, each carrying an `Ev` table:
  1. **`mod.info`** — every key the corpus uses (`name`, `id`, `description`, `modversion`, `versionMin`, `require`, `incompatible`, `loadModAfter`, `loadModBefore`, `poster`, `icon`), what reads each, and which are load-order declarations. **C** from `ChooseGameInfo.readModInfoAux` and the 230-mod inventory; **M** for the five ids our own mods declared.
  2. **Where a `mod.info` may live, and which one supplies the id** — `getAllModFoldersAux @124-151 L602` (discovery accepts `common/mod.info` **first**), `searchForModInfo @0-@173 L708-L735` (`File.list()` order, returns the first **id match**, registers the rest into `modIdToDir`), `ChooseGameInfo.readModInfo @0-@101 L157-L175` (the earlier-folder tie-break). **C** for all three; **M** (`x122`, L1) for the answer, which **closes `docs/testing/profiles.md` § Open questions 1**. State plainly whether `mod_lint.info_chain`'s newest-first model matches the engine, and say so in `info_chain`'s docstring in the same task if it does not.
  3. **Version dirs and `common/`** — `getModVersionDirName` picks the best `42[.x[.y]]/` ≤ the build; the merge rule (KEEP 10) restated with its four jar sites; now **n = 2** (`td3-20260911-001948` on AutoCook, `x122` on a mod we control), and the **new** arm KEEP 10's bound excludes: a version dir that ships only a `mod.info` and no `media/` (mod E, read off `x122` L3).
  4. **`Mods=` and the folder name** — the rename `harness.install` performs, the 52 drifting workshop folders, and the counterfactual (`x123`). **M**.
  5. **Translations** — `Translator.tryFillMapFromMods @0-@97 L376-L391` merges rather than shadowing; `tryFillMapFromFile @4-@29 L357-L358` formats `<dir>/media/lua/shared/Translate/<lang>/<file>.json` and opens **nothing else**; the two layouts and which one 42.20.4 reads (`x121` M4). **M** — and this is the row that retires slice 09's hypothesis (ii)/(iii) ambiguity.
  6. **`require` and Lua load order** — `LuaManager.LoadDirBase @0-@540 L1141-L1232`: vanilla's block first, per mod `commonDir` then `versionDir`, each block sorted case-insensitively, deduped by relative path through a `HashSet`, the survivor resolved through `getAbsolutePath` = `activeFileMap.get`. Consequences: a mod file at a vanilla relative path replaces vanilla's **in vanilla's slot**, and `require` resolves against the same map.
  7. **What `mod_lint` checks and why** — the nine rules against the engine facts above, saying which two (`mod-info-place`, `media`) are models rather than readings and whether this slice's measurements promoted either.
  8. **MP behaviour** — a profile is a server-side decision the client inherits; the server's `Mods=` is authoritative on join; both sides are seeded from one source map; scripts and translations load **per side** and never sync.
- [ ] **Step 2: Commit** — `git commit -m "Slice 12: mod anatomy" -- docs/modding/anatomy.md tools/mod_lint.py`.

### Task 8: `docs/modding/item-overrides.md`

**Files:** create `docs/modding/item-overrides.md`.

- [ ] **Step 1: Write it.** Same skeleton and stamp. The spine is one `Ev` table of **five routes**, then a section each:
  - **R1 redefine a vanilla name in `module Base`** — the mechanism (`CreateFromTokenPP @88-@159 L168-L175` appends the body; `LoadScripts @140-@208 L252-L259` replays them; `ScriptType.<clinit> @698-@705 L98` gives `Item` the `ResetExisting` flag) as **C**, the Apple reading as **M** (`x121` M2).
  - **R2 the partial block, and why it is the trap** — the Orange reading (**M**). State the rule the item pass must follow: **restate every key, because the second block resets the object.** Give the corpus context: only **one** name collision exists in the whole 230-mod corpus (`Horse` redefining `Base.Rope`, `docs/mods-survey/nutrition-mods.md` § Discrepancies 5), so a 1 005-item pass has no precedent to copy and this is the mechanism it rests on.
  - **R3 a new item in the mod's own module** — no collision, the LTP precedent (**C+M**, `td1-20260910-192457`) plus our three `module TKX` items (**M**), and the display-name consequence measured in M4: an item absent from the translation table reads `getDisplayName() == getFullType()` and `getActualWeightUnmodded() == 0`, which moves `Food.getActualWeight` onto its guarded arm.
  - **R4 Lua hooks on the instance** — `OnEat` (where it fires, on which sides, in what order relative to the nutrition write; **M** from `x121` M5, **C** from `Eat @762-@802 L5811-L5814` and `EatOnClient @0-@57 L5725-L5736`), the `ISEatFoodAction:complete` wrapper (**M**), and `OnCooked` (**C+M**, slice 09). End with the limit that binds all three: whatever a hook writes reaches the other side only through `ItemStatsPacket`'s 39 item-state fields — `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` never arrive, and a cooked food's `thirstChange` halves per hop.
  - **R5 item modData** — the new-nutrient route (**M**, `x121` M7), the `syncItemFields` wipe-and-replace, and the `customName` / `Tooltip` exclusions any census must apply.
  - **Load order between two mods** — the Watermelon reading (**M**, `x121` M3) with its bound: one session, one order. **Name the check that would complete it** — the same profile booted with the two mods swapped in `Mods=` — and hand it to slice 13 rather than claiming it.
- [ ] **Step 2: Commit** — `git commit -m "Slice 12: item override routes" -- docs/modding/item-overrides.md`.

### Task 9: `docs/modding/lua-api.md`

**Files:** create `docs/modding/lua-api.md`.

- [ ] **Step 1: Write it as a CURATED reference, not an inventory.** The rule for inclusion: **this library has used it or measured it.** Sections:
  1. **Events** — one `Ev` table of the events actually exercised (`OnClientCommand`/`OnServerCommand`, `EveryOneMinute`, `EveryTenMinutes`, `OnTick`, `OnPlayerUpdate`, `OnCreatePlayer`, `OnInitGlobalModData`, `OnPreFillInventoryObjectContextMenu`, `OnKeyPressed`), each with firing side, cadence and the artifact or teardown that measured it. Carry KEEP 8's heartbeat discipline and slice 10's rule: **cache at the push cadence, not the frame cadence.**
  2. **Java members by owner** — `Nutrition` (the five macros, the three direction flags, `updateWeight`'s client skip), `Food`/`InventoryItem` (the `TK.ITEM_STATE` set, and which of them `ItemStatsPacket` carries), `IsoPlayer`/`IsoGameCharacter` (`getModData`, `transmitModData`, `hasTrait(CharacterTrait)`, `getXp()` then `XP.getXP(Perk)`), `ScriptManager`/`Item` (and the fact that the script `Item` exposes **no** macro getter to Kahlua, so the four macros are only readable off an instance). Each row: side that owns it, whether it syncs, Ev.
  3. **Script-side hooks** — `OnEat`, `OnCooked`, `OnCreate`, with the resolution rule (`LuaManager.getFunctionObject` takes a **global function name**) and the firing sides from Task 4's reading.
  4. **The command bus as the harness's own API** — a pointer to `docs/testing/README.md` § Command bus, which is the authority; do **not** restate the inventory. Say what the bus is for: the instrument, and the model for a mod's own client→server protocol (KEEP 2).
  5. **What Kahlua cannot do** — a nil call escapes `pcall` and kills the whole handler (hence `TK.call` and mod B/C's `tkxCall`); no `goto`; `%d` on a float raises; `#` does not work on a Java list; `pairs()` on a Java-backed object raises; `string.format` is Kahlua's own, so `%g` precision is not Java's; an argument-arity mismatch is as fatal as a nil call, which is why `witness.fields` takes **zero-argument getters only**.
  6. **Removed or absent on 42.20.4** — `loadstring`, `HasTrait(String)`, `getTypeString()`, `zombie/inventory/ItemUser` (not in `exposeAll`'s set), `Stats.getHunger`/`getThirst`, the script `Item` macro getters. Each with the jar reading and the mod in the corpus that still calls it (FILTER 11).
  7. **MP behaviour**, **Open questions**, **`## Sources`**.
- [ ] **Step 2: Commit** — `git commit -m "Slice 12: curated Lua API reference" -- docs/modding/lua-api.md`.

### Task 10: Lint, ledgers and the slice-13 hand-off

- [ ] **Step 1: Gates** — `python tools/doc_lint.py docs/modding docs/vanilla docs/testing docs/mods-survey references` → `0 finding(s)`; `python tools/mod_lint.py testing/experiments/TKX_ItemOverride testing/experiments/TKX_Nutrient testing/experiments/TKX_EatHook` → 0 ERROR; `python -m pytest tools/tests testing/tests -q` → green.
- [ ] **Step 2: Ripples into the docs the slice corrected** — `docs/modding/README.md` (replace the *Planned documents (P2)* table's `mod-anatomy.md` / `lua-events.md` / `item-overrides.md` rows with links to the three real files, and fold § Hard-won platform facts into them); `docs/testing/profiles.md` (**close** § Open questions 1 and the second half of § Open questions 6, each with its run id); `docs/modding/patterns.md` (KEEP 10 gains its second subject and the empty-version-dir arm; add a KEEP or FILTER row for anything R1–R5 earned); `docs/testing/README.md` (the `text.get` move, if anything about it changed after Task 3's commit); `testing/artifacts/README.md` (three Contents rows — run id / file / driver / cited-by — plus a skew note for any driver edit that landed after its run, **and the do-not-cite mechanism for any key that came back known-bad**: under each `x12*` artifact's block, a ***do not cite*** table with one row per bad key — the **key** (its JSON path), **why** it is bad (a driver bug, a stale read, a literal frozen at the wrong value the way `td3`'s `carrier.gate` froze `>=` against the jar's strict `>`), and **what to cite instead** (the corrected value, or the graded row in the owning doc). A key with no row is citable; a key with one is not. These blocks are what slices 13 and 14 read before they quote anything of ours, so a known-bad key with no row is a defect of this step).
- [ ] **Step 3: The wall-map inputs for slice 13**, listed at the end of `docs/modding/anatomy.md` under a final `## Inputs for the wall map (slice 13)` heading and mirrored as a ripple in `docs/progress.md`: for each of slice 13's nine entry areas — new nutrient fields, eat hooks, the weight formula, moodles, sync (item stats / player stats / modData), the cooking pipeline, traits, translations, the merge rules — name the artifact or jar site that classifies it CANNOT / CAN / CAN WITH A WORKAROUND, and name the experiment that would settle anything still unknown. The three un-run checks this slice deliberately records rather than claims: the **reversed `Mods=` order** boot for R7; the **CleanUI × `triggerEvent`** two-order boot carried from the AutoCook teardown § Compatibility notes; and any arm of M6–M8 whose reading came back trivial.
- [ ] **Step 4: `docs/decisions.md`** — one row each for: the five-mod / two-profile / three-session split; mod D's deliberate `id-agree` ERROR and mod E's deliberate `media` WARN; the `text.get` move as its own task ahead of the sessions; `Mods=` order chosen so `TKX_EatHook` is last; the narrowed partial-Orange block (`ItemType` + `DisplayCategory` kept) as R2's shipped default, and which of P3's two arms it produced; the M9 transmit-wipe phase and its reading; any `[[verify]]` tier substitution; any harness addition beyond Task 3.
- [ ] **Step 5: Commit `Slice 12: ledgers` — and stop.** **No `git push`, and do not flip the board row to `done`.** Row 12 stays `in progress` with a resume note until the whole-slice review has run; the controller flips it and pushes.

## Deliverables

- `docs/modding/anatomy.md`, `docs/modding/lua-api.md`, `docs/modding/item-overrides.md` — stamped, graded, each with a non-empty `## Sources`.
- Five experiment mods under `testing/experiments/` (Header table) and two profiles `testing/profiles/x12-{overrides,loader}.toml`.
- Three drivers `testing/experiments/x12{1,2,3}_*.py` and three artifacts `testing/artifacts/x12{1,2,3}-<stamp>/` with their `testing/artifacts/README.md` rows.
- Updates: `docs/modding/README.md`, `docs/modding/patterns.md`, `docs/testing/README.md`, `docs/testing/profiles.md`, `tools/mod_lint.py` (the `info_chain` docstring), both ledgers.

## Acceptance checks

1. `python testing/pzt run --profile x12-overrides --hold 5` → `RESULT: PASS`, exit 0, all three `verify` probes `ok=True`; the same for `--profile x12-loader` with its one probe.
2. The three artifacts exist and are byte-identical to the run copies; `x121`'s carries a `server` **and** a `client` block for every paired reading, with `field_count_ok` true on every `witness.fields` reply, and a `transmit_wipe` key (M9) carrying both sides' census before and after the client transmit.
3. **Task 3 landed before Task 4's session commit**: `git log --oneline` shows `Slice 12: harness — text.get shared` ahead of `Slice 12: override/eat-hook/nutrient session`, and `grep -rn 'TK.register("text.get"' testing/PZTestKit` returns exactly one hit, in `shared/`.
4. **Every mechanism asserted in the three docs maps to an M (an artifact key named in the row) or a C (a jar/Lua/script `file:line` or `Class.method @offset L<line>`).** A row with neither is a defect; a W row must say what it corroborates.
5. Questions 1–12 each have a cited answer, and each of the four open questions this slice was sent to settle is either **closed with its run id** (`profiles.md` OQ 1, OQ 6 second half, the display-name hypotheses (ii)/(iii), the partial-block merge rule) or re-stated sharper with the experiment that would settle it named.
6. `python tools/doc_lint.py docs/modding docs/vanilla docs/testing docs/mods-survey references` → `0 finding(s)`; `python tools/mod_lint.py <the three clean mods>` → 0 ERROR; `python -m pytest tools/tests testing/tests -q` green.
7. Every experiment mod is named in a profile and has a row in `docs/modding/anatomy.md`'s experiment table; the slice-13 inputs are listed.

## Expected decision points (defaults)

- **The narrowed `item Orange` block still makes the server refuse to load the script.** The narrowing — keep `DisplayCategory` and `ItemType`, drop only the nutrition keys — is already R2's **shipped default** (Task 1 Step 1), so there is no further fallback to take on the mod: record the refusal verbatim, read P3 off whichever arm survived, and grade R2 **unmeasured** if neither did. Script **load errors** that do not stop the boot are the finding, not a defect: keep the run, quote the lines, do not tune the mod to hide them.
- **Orange comes back as a plain `InventoryItem`** — the food getters land in `witness.fields`'s `missing` rather than reading 0, and the Base food count is 721 not 722 → that is P3's second arm, not a failure: the reset took `ItemType` with it despite the block declaring it. Grade the reset **M** on the `missing` set, say in the doc which arm the run produced, and correct P1's expected count in the artifact's own prose rather than re-running.
- **A `[[verify]]` row fails on the acceptance run** → tier down in this order: (a) another bus probe reading that mod's own state; (b) the mod's own console print grepped out of the run's logs; (c) the copied folder under `<run>/server/mods/` plus an empty `mods_not_found`, with the doc saying "loaded; effect not directly readable". Log the tier in `docs/decisions.md`. Never promote a measurement to a gate.
- **`profile.load` raises on mod D or E** → take the id `pzt.mods.mod_id_of` prints for that folder and put it in the profile; never edit the mod to suit the resolver, because the disagreement is part of question 1's answer.
- **The server does not expose `getText`** → `text.get`'s server reply says so; question 4's server half then rests on `witness.fields … getDisplayName` read server-side, which is sufficient. Record the absence.
- **`eat.action` does not complete** (the `FOOD_EATEN` moodle gate, or the item not found) → RCON `additem` first and poll for the item with `witness.fields item admin/<type> getID` up to three times at 2.5 s, exactly as `td3_autocook.py` does; if the eat still does not complete, fall back to the server command `eat <type> [fraction]` (direct `Eat`, no timed action), keep the rows **M**, and record that `TKX_EatHook.completes` is then untested because the wrapper was bypassed.
- **`nutrition.set admin calories -100` clamps at 0** → that is the reading; state the clamp and grade the loss arm **unmeasured** rather than inferring it.
- **Renaming the mods folder in session 3 wedges the boot** → the run still reports; keep the artifact, record `mods_not_found` and the WARN lines verbatim, and grade P16 the other way. Do not retry with a case-only rename: NTFS lookup is case-insensitive and such a run answers nothing (`profiles.md` § Why the case-only subject would not have done).
- **A session's readings come back trivial** (both sides agree because neither could have differed — the shape slice 11 hit on the weight flags) → say so in the doc, grade the row as the trivial arm, and hand the discriminating probe to slice 13 rather than quoting the agreement as evidence.
- **The slice runs past twice its estimate (6 h)** → split. The remainder becomes a new catalog entry; `lua-api.md` is the doc to defer, because 13 and 14 depend on `anatomy.md` and `item-overrides.md` first. Never deliver a thin doc silently.
- **The harness needs more than Task 3's `text.get` move** → allowed under the standing rule, with every Java member jar-confirmed (`./pz.sh methods|dump`) before it is called, the addition folded into Task 3 (or its own commit ahead of the session commit if Task 3 has already landed), the balance check re-run, `docs/testing/README.md` updated in the same commit, and the next acceptance run as its smoke test. What still does not belong here is a change that reshapes every existing artifact.

## Done protocol

- `docs/progress.md`: a resume note under row 12 while the slice is open (what landed, the run ids, what remains), and **ripples** — for slice 13, the wall-map inputs of Task 10 Step 3 and the three un-run checks; for slice 14, the item-pass mechanism (R1/R2's restate-everything rule, R3's translation consequence) and any compatibility constraint the experiments exposed. Row 12 → `done` is the **controller's** edit at the slice close, not Task 10's.
- `docs/decisions.md`: the rows of Task 10 Step 4.
- `docs/testing/README.md`: any harness command added or moved, in the same commit as the Lua — for this slice that is **Task 3**, landed before the first session.
- `testing/artifacts/README.md`: one Contents row per run, a skew note wherever a fix round followed a live run, and a ***do not cite*** table for every key that came back known-bad (Task 10 Step 2).
- Commits per task, subject line only, no attribution, pathspec; **the slice does not push**. The controller pushes at the slice close, after the whole-branch review. Slice 13 starts from `docs/modding/anatomy.md` § Inputs for the wall map.
