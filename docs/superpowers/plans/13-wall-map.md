# Slice 13 — P2b Moddability wall map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One document, `docs/modding/wall-map.md`, that answers *"can our nutrition mod do X on 42.20.4 in MP?"* for every design area the charter names — new nutrient fields, eat hooks, the weight formula, moodles, sync (item stats / player stats / modData), the cooking pipeline, traits, translations, the merge rules, the item pass — with each capability classified **CANNOT / CAN / CAN WITH A WORKAROUND / UNKNOWN**, the mechanism that decides it, the evidence graded C/M/W and traced to the slice, artifact or jar site that established it, the workaround where one exists, and the residual risk it leaves. Nothing in this slice is new measurement: it is a **classification pass** over what waves 1–3 measured, slice 12 proved, and the jar says — plus a named, costed experiment for every hole.

**Architecture:** Five offline tasks. Task 1 re-reads the **locked** surfaces on the 42.20.4 jar with `./pz.sh` so every `CANNOT` rests on a member list or an absence rather than on memory. Task 2 harvests every already-established claim out of waves 1–3 and slice 12, one line per capability with its citation re-located by content. Task 3 turns each remaining hole into a **named experiment** (`X1…`) with a profile, a driver, an action and the reading that would decide it. Task 4 writes the doc. Task 5 lints, ripples into the neighbouring docs, writes both ledgers — **no push, no board flip**.

**Tech Stack:** `./pz.sh` (pzdis) in `C:\Users\Angus\pz-b42`, `python tools/doc_lint.py`, `grep`, Markdown. **No live server.**

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md` (row 13)

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades **C/M/W** on every claim row; brief commits (`Slice 13: …`), no attribution, **pathspec commits** (`git commit -m … -- <paths>`), never `--amend`; the game install and the workshop folder are **read-only**; take the default at every decision point and log it in `docs/decisions.md`; fresh implementer per task and per fix round; `cd` into the repo in every shell call (the cwd resets between calls).
- **This slice does not boot the game.** Its acceptance needs no measurement — live measurement is slice 12's job, and a wall map's job is to *name* the experiments that remain. See § Expected decision points for the single, logged exception.

---

## Header

- Slice **13** · Phase P2b · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: **12** (`docs/modding/{anatomy,lua-api,item-overrides}.md` + artifacts `testing/artifacts/x12*/`) · Unblocks: **14** · Estimate: 2 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`; house doc standard and the eight-part plan template in the spec § Evidence and documentation standard. Jar toolchain: `cd /c/Users/Angus/pz-b42 && ./pz.sh grep|methods|refs|dump` (`WORKSPACE.md` there; a whole-jar `grep` walks ~23.7k classes and is slow but proves a list exhaustive; `dump` on `IsoGameCharacter` takes minutes).
- **The doc you are writing is a stamped dir.** `docs/modding` is in `doc_lint.STAMPED_DIRS` (`tools/doc_lint.py:8`), so `wall-map.md` needs `Verified against: 42.20.4` in the text, a non-empty `## Sources`, no placeholder marker (`PLACEHOLDER_RX`, `tools/doc_lint.py:7`), and — in **every** table whose header contains a cell exactly `Ev` — a C/M/W in that column of **every** row. The check is `re.search(r"\b[CMW]\b", cell)`: `M (run td2-…)` passes, **`M4` and `Cannot` do not** (no word boundary). Keep the grade a standalone letter.
- **Verdict vocabulary, fixed** (do not invent a fifth): **CANNOT** — the behaviour is decided inside the jar on a path no Lua reaches *and* no mod-side construction reproduces the effect; **CAN** — an evidenced mod-side mechanism exists; **CAN WITH A WORKAROUND** — the direct route is closed but a named construction achieves the effect at a stated cost (the Workaround cell names it, the Residual risk cell names what it does not achieve); **UNKNOWN** — the evidence does not decide it. **Every `UNKNOWN` row's Ev cell ends with `-> X<N>`** naming a row in § Named experiments; any other row may carry `-> X<N>` too, meaning "stated on C, this is what would raise it to M". ASCII arrow `->`, not `→` — it is grepped.
- **Waves 1–3 are the evidence base and a plan that contradicts them is wrong.** The server owns `Nutrition`, hunger/thirst, weight, traits, item aging and the Cooking perk; a client write is overwritten within ~1.5 s by the 1 Hz `PlayerStatsPacket`; `player:getModData()` reaches the server only after `transmitModData()`, which sends the **whole** table and the receiver **wipes and replaces**; `ItemStatsPacket` puts **43** fields on the wire of which **39** are item state (not `isCookable`/`offAge`/`offAgeMax`/`lastCookMinute`/`customWeight`) and reuses cached packets so a zero-valued conditional field arrives stale; a cooked food's `thirstChange` halves once per server→client hop and converges; `Food.update` pushes `sendItemStats` once per game minute only while `heat > 1.6f`, and below that gate the client's copy was measured **bit-frozen**; `getActualWeightUnmodded` returns 0 when `getDisplayName() == getFullType()`. Canonical rows: `docs/modding/patterns.md` § Measured MP sync facts (both directions), KEEP 1–11, FILTER 1–11.
- **The mod-loading rules (slice 11, C from the jar + M on AutoCook, run `td3-20260911-001948`):** `ZomboidFileSystem.loadMod @0-@431 L739-L778` runs `common/` then the version dir into `activeFileMap` with unconditional `put` at `L758`/`L773` — the **version dir wins** a colliding relative path, bounded to a mod whose version dir actually ships colliding files; `getAbsolutePath @0-@19 L483-L484` *is* the resolution and is pre-seeded with vanilla's whole `media/` tree; `LuaManager.LoadDirBase @0-@540 L1141-L1232` dedupes by relative path through a `HashSet`, vanilla's block first, resolving through that map; `Translator.tryFillMapFromMods @0-@97 L376-L391` **merges** translation JSONs instead of shadowing; the loader prints one `mod "<id>" overrides <relpath>` line per shadowed file; `searchForModInfo L708-L735` returns the first `mod.info` whose id matches in `File.list()` order (the id-read order across `common/` vs version dirs is **open** — slice 12 settles it). `HasTrait(String)` and `getTypeString()` are **removed** on 42.20.4; `loadstring` is removed in 42.20.x.
- **Two doors waves 1–3 found that the map must not miss.** `LuaHookManager.TriggerHook("CalculateStats", character)` returning true skips `updateThirst`, `updateStats_WakeState`, endurance, stress, morale and fitness for that tick (`calculateStats @49–@59 L10204-L10205`, C) — the cleanest vanilla interception point on the body side. And every hunger/thirst constant is a **Lua** global in `media/lua/shared/defines.lua` read into `ZomboidGlobals` at load (C), which the merge rules make replaceable at its own relative path.
- **Slice 12 is the upstream dependency and it is consumed by name:** `docs/modding/anatomy.md` (mod anatomy, the merge rule with its bound, the id-read order, `Mods=` and the folder question, translations, `require`), `docs/modding/lua-api.md` (the curated `Events.*` / `Nutrition` / `Food` / `InventoryItem` / `IsoPlayer` surface, the command bus as an API, what Kahlua cannot do, removed APIs), `docs/modding/item-overrides.md` (script merge rules — `module Base` redefinition vs `item` block override vs `OnCooked`/`OnEat` hooks vs modData, each proven by an experiment), and the experiment artifacts under `testing/artifacts/x12*/` with their rows in `testing/artifacts/README.md`. **Task 2 Step 1 is the manifest step** that maps each expected experiment to the run id that actually exists; § The slice-12 dependency rule says what to do when one is missing or inconclusive.
- **Harness reach, because it bounds what any experiment in § Named experiments may promise** (`docs/testing/README.md` § Command bus is the authority): server `nutrition.get/set`, `stats.get`, `item.get/set/update/use`, `perk.xp`, `moddata.set`, `recipes.count/craft/evolved` (**readers** — nothing on the bus executes a craft), `items.count`, `item.script`, `sandbox.set`, `trait.set`, `perk.set`; client `eat.action`, `moddata.set/transmit`, `stats.get`, `text.get <IGUI key>` (a miss returns the key itself; both sides since `ad683fe`), `item.script`; both sides `witness.fields <player|item> <id> <getter,…>` (zero-arg getters on the `IsoPlayer`/`InventoryItem` — **not** the `Nutrition` macros; ≤ 32), `witness.moddata` (keys **space**-separated behind an explicit scope), `lua.global <dotted name>` (never calls). Items spawn server-side with RCON `additem`. `TK.json` renders numbers with `tostring` since `291f977`; artifacts older than that are `%.6f`. Cadence ceiling `24 × speed / day_minutes ≲ 8`; the fixture's `DayLength = 4` is **90 REAL minutes** per game day.
- **Ripples addressed to this slice are not optional.** `docs/progress.md` § Ripples carries findings written *for* slice 13 by name — the zero-valued packet field (from 02), "writes an item field outside the packet" as an unsynced surface (from 09), the cooked-thirst halving (from 09), the `transmitModData` wipe (from 10), "nothing in 12/13 should describe client-side item simulation until it has run" (from 10, since resolved per arm in slice 11). Task 2 Step 4 checks every one of them became a row.
- **Nothing here is new work for the neighbouring docs.** `docs/feasibility/*` is slice 14. The teardowns are closed. This slice edits `docs/modding/README.md` and `docs/modding/patterns.md` only, and only to point at the new file and to close or sharpen an open pattern question it settles.

## Questions (the slice is done when each has a cited answer in the doc)

1. For each of the ten design areas, which capabilities are **jar-locked**, and what exactly is the lock — a missing setter, a side guard, a fixed serialization, a packet field list, a Java enum?
2. For each locked capability, is there a mod-side construction that reaches the same *effect*, and what does that construction **not** achieve?
3. Which capabilities are already **measured** (M) rather than read (C), and which run id owns each?
4. Which capabilities does slice 12 settle, and by which artifact key?
5. What remains **UNKNOWN**, and for each, what is the one experiment — profile, driver, action, deciding reading — that would settle it, at what cost?
6. Where does an *evidence* limit masquerade as a platform wall (no craft route on the bus, no `triggerEvent`, one fixture, `n = 1`)? Those belong in their own section, not in the map.
7. Where do the map's verdicts contradict the wiki mirrors or this repo's own older prose (`docs/modding/README.md` § Planned documents, § Hard-won platform facts)?
8. Which verdicts are bounded — to MP on a dedicated server, to one fixture, to a mod whose version dir ships colliding files — and does every such row say so?
9. Which walls change the **shape** of the mod rather than a detail, and are they called out for slice 14?
10. Does every ripple in `docs/progress.md` addressed to slice 13 appear as a row?

## Method

### Task 1: Re-read the locked surfaces on the jar (no live server)

**Files:** Create `.superpowers/sdd/13-wall-map/jar-locks.md`.

Every `CANNOT` in the map must cite a member list or a proven absence read **today**, not a remembered one. `.superpowers/` is gitignored, so this task commits nothing.

- [ ] **Step 1: The locked objects.** Run each and paste the answer into the notes under a `J<N>` heading:

```bash
cd /c/Users/Angus/pz-b42
./pz.sh methods zombie/characters/BodyDamage/Nutrition          # J1
./pz.sh methods zombie/characters/IsoGameCharacter | grep -iE "nutrition|moodle|trait|stats"   # J2
./pz.sh methods zombie/scripting/objects/MoodleType             # J3 — NOT zombie/characters/Moodles/
./pz.sh methods zombie/characters/Moodles/MoodleStat            # J3
./pz.sh methods zombie/characters/Moodles/Moodles               # J3
./pz.sh methods zombie/scripting/objects/CharacterTrait         # J4 — NOT zombie/characters/
./pz.sh methods zombie/characters/traits/CharacterTraits        # J4 — NOT zombie/characters/
./pz.sh methods zombie/network/packets/ItemStatsPacket          # J5
./pz.sh methods zombie/network/packets/character/PlayerStatsPacket   # J5
./pz.sh grep loadstring                                         # J6
./pz.sh grep setNutrition                                       # J1
```

  **Expected, and the absence is the finding:** **J1** — `Nutrition` exposes `getCalories/setCalories` and the three macro pairs, `getWeight/setWeight`, `update`, `updateCalories`, `updateWeight`, `applyTraitFromWeight`, `applyWeightFromTraits`, `characterHaveWeightTrouble`, `canAddFitnessXp`, `save`, `load` — and **no** `getModData`, no generic field accessor, no extension point; `grep setNutrition` finds **no** setter on `IsoGameCharacter`, so Lua cannot substitute a different object for the one the engine constructs. That pair of absences *is* wall-map row A1. **J2** — `getNutrition`, `getMoodles`, `getCharacterTraits`, `getStats` are getters only. **J3** — **the moodle surface is a registry that takes registrations, and the task is to record them, not to confirm an absence.** `MoodleType` lives at `zombie/scripting/objects/MoodleType` and carries `register(String)`, `registerBase(String)` and `register(boolean, String)` alongside its 27 statics; `MoodleStat` carries `register(MoodleType, F, F, F, F, F)` **as well as** `get(MoodleType)` and the five threshold setter pairs; `Moodles` carries `getMoodleLevel` (`@0–@16 L40`). `MoodleType` is also **Lua-exposed** — this repo's own harness reads `MoodleType.FOOD_EATEN` at `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua:436 (was :461 before ad683fe)`. So write down the exact **registration members and their signatures** (what `register` returns, what the boolean arm means, whether `MoodleStat.register` must be called too) and the exact `MoodleStat` mutators: rows D1 and D2 both turn on them, and D1 is an **open** question in this plan, not a wall. **J4** — `CharacterTrait` lives at `zombie/scripting/objects/CharacterTrait`, is an enum-shaped registry whose statics are what `getAppetiteMultiplier @13–@31 L10323-L10324` tests, and carries a `register` of its own (the mechanism row G1 cites); `CharacterTraits` lives at `zombie/characters/traits/CharacterTraits`. Note whether any effect reads a **string** rather than a static (if none does, a script- or `register`-added trait can exist and be selectable but carry no Java effect — row G1). **J5** — `ItemStatsPacket`'s whole method list is `<init>`, `setData`, `write`, `parse`, `processServer`, `processClient`, `applyItemStats` (no reset, no extension); `PlayerStatsPacket.write @0–@74 L31–L40` is an unconditional full snapshot. **J6** — `loadstring` returns nothing outside dead string constants.
- [ ] **Step 2: The hook and constant doors.** `./pz.sh dump zombie/characters/IsoGameCharacter calculateStats` → confirm `LuaHookManager.TriggerHook("CalculateStats", …)` at `@49–@59 L10204-L10205` and that a `true` return skips the rest of the method. `./pz.sh grep TriggerHook` → the full hook inventory (expect `"CalculateStats"` and `"AutoDrink"` among them); any hook on the intake or weight path that this library has not named is a **new CAN row** — record it. Then `grep -n "Hunger\|Thirst" "D:/SteamLibrary/steamapps/common/ProjectZomboid/media/lua/shared/defines.lua" | head -30` to confirm the `ZomboidGlobals` constants are Lua and replaceable at a vanilla relative path.
- [ ] **Step 3: The item/script surfaces.** `./pz.sh dump zombie/inventory/types/Food update` (the cooking branch's `heat > 1.6f` gate at `@49-@71 L372-L373` and the per-game-minute `sendItemStats` at `@86-@103 L377-L379`); `./pz.sh dump zombie/inventory/types/Food getActualWeight` (the `isCustomWeight` arm split at `@215-@287 L902-L908` / `@288 L910`); `./pz.sh grep checksum | grep -i script` — the map claims "no script checksum gate was found on 42.20.4", so the grep is the evidence for row J3 and a hit overturns it.
- [ ] **Step 4: Write the notes.** One `J<N>` section per reading, each with the exact command, the answer, and a one-line "what this locks / opens". Where a reading **differs** from what this plan predicts, the reading wins and the difference is called out — later tasks read the notes, not this plan.
- [ ] **Step 5: No commit** (`.superpowers/` is gitignored). Task 1's deliverable is the notes plus the report.

### Task 2: Harvest every established claim (no live server)

**Files:** Create `.superpowers/sdd/13-wall-map/evidence-harvest.md`.

- [ ] **Step 1: The slice-12 manifest.** `ls testing/artifacts | grep -i '^x12'`, then read `testing/artifacts/README.md`'s x12 rows and the `## Sources` of `docs/modding/{anatomy,lua-api,item-overrides}.md`. Write a table mapping each expected experiment — (a) the `Base.Apple` calorie override, (b) a mod-side new-nutrient field on item **and** player modData with its sync measured, (c) an eat hook, (d) the id-read-order experiment, (e) the folder≠id experiment — to the run id that actually exists, its key inside the JSON, and whether the slice-12 doc calls it conclusive. Do **not** assume the suffix letters; map by what the slice-12 docs cite. Anything on that run's *do not cite* list counts as **inconclusive**.
- [ ] **Step 2: The doc sweep.** Read, in this order, and pull one harvest line per claim — `capability id | claim | grade | citation (file:line, jar site, or run id + key)`:
  `docs/modding/patterns.md` (both § Measured MP sync facts tables, KEEP 1–11, FILTER 1–11, § Open pattern questions) · the three teardowns `docs/mods-survey/teardowns/{longtermpreservation4220,simplestatus,autocook}.md` (§ Architecture, § MP handling, § Techniques worth stealing, § Pitfalls) · `docs/vanilla/{nutrition-core,eating-pipeline,body-stats,food-item-model}.md` (§ Model, § Code map, § MP behaviour, § Open questions) · `docs/vanilla/{food-dataset-notes,recipes-dataset-notes}.md` (the item-pass surface) · `docs/testing/README.md` § Command bus and `docs/testing/profiles.md` § Open questions · `docs/progress.md` § Ripples · slice 12's three docs · `docs/modding/README.md`. **Every `path:NN` cite is re-located by content** before it is copied — open the file, find the line, and if it moved, use the new number.
- [ ] **Step 3: Fill the row inventory.** The map's rows are fixed below so the executor classifies rather than invents. Each cell is *predicted from the corpus while this plan was written*: **verify it, and the current reading wins.** Mark each row `confirmed` / `corrected (…)` / `no evidence -> X<N>` in the harvest.

  **Read `.superpowers/sdd/wave-4/not-settled.md` before you fill a single cell.** It is the slice-11 whole-pass review's list of what waves 1–3 did **not** establish, and a map row that promotes any of it to settled is the one defect this slice can inflict on 14. The six that touch rows below: (1) the **merge rule** is bounded to a version dir that actually ships colliding files (n = 1, AutoCook); (2) **MoodleFramework "whole on 42.20.4"** is **C derived from that rule** — nothing has booted it, and the `MF_Config.lua`-executes step is C too; (3) the **carrier** is M *per arm*, n = 1 each, one cookable item, one 12.54 s window, one fixture — its honest form is "`Food.update` did not advance the client copy in this window", never "client copies cannot tick"; (4) **`mod.info` resolution order is open** — three unreconciled models, `searchForModInfo` id-matching precision C only; (5) the **transmit WIPE half** is a single pass-2 reading (pass 3 corroborated wipe-and-**REPLACE** only) — slice 12's M9 is what takes it to n = 2; (6) the **cooking pipeline stays C** — nothing on the bus reaches a right-click or executes `craftRecipe`. The rule: where a predicted verdict would encode one of these as settled, either mark it **UNKNOWN -> X\<N\>** naming the experiment, or keep the verdict and put the **bound in the evidence cell** (a `CAN WITH A WORKAROUND` row puts it in Residual risk as well). A bound that is written down is not a hole; a bound that is dropped is.

| # | Capability (what our mod wants to do) | Predicted verdict · where the evidence is |
|---|---|---|
| A1 | Add a field to the Java `Nutrition` object | **CANNOT** · Task 1 J1 (no `setNutrition`; `save/load @0 L209/L217` is a fixed five-float list) |
| A2 | Keep a parallel per-player nutrient store server-side | **CAN** · patterns KEEP 1–2; eating-pipeline § MP behaviour shapes (a)/(b)/(c) |
| A3 | Keep that store in **player modData** instead | **CAN WITH A WORKAROUND** · FILTER 10 whole-table wipe, M `td2-20260910-231655` |
| A4 | Put per-item nutrient values in the **item script** | **CAN** · KEEP 11, M `td1-20260910-192457` (per-side load, never synced, identical for free) |
| A5 | Put a **custom key** inside a vanilla item script block | **UNKNOWN -> X6** · script macro fields are not Lua-readable at all, M `exp01-20260910-000351` |
| A6 | Put per-item nutrient values in **item modData** | **CAN WITH A WORKAROUND** · `SyncItemFieldsPacket.processModData` wipes and replaces; exclude `customName` + `Tooltip` (slice 08/09 ripples) |
| A7 | Persist the parallel store across save/load | **CAN** · KEEP 1 (engine save path) |
| B1 | Run the mod's intake math where `Eat` runs | **CAN** · eating-pipeline § MP behaviour (the eat completes server-side) |
| B2 | Intercept **before** vanilla's numbers land | **CANNOT** · `OnEat` fires after every stat/nutrition/mood write, `Eat @762–@802 L5811–L5814` |
| B3 | Correct after the fact from `OnEat` | **CAN WITH A WORKAROUND** · same site: the hook may mutate `hungChange`/`calories` and `multiplyFoodValues` sees the mutation |
| B4 | Have one `OnEat` handler fire **once** in MP | **CANNOT -> X8** · `EatOnClient @0–@57 L5725–L5736` re-fires `OnEat` on every `EatFoodPacket` receiver with no numeric effect. **Slice 12's M5 measures exactly this** — if the manifest shows it settled, the row keeps its verdict on M and X8 is struck |
| B5 | Wrap `ISEatFoodAction:complete` client-side | **CANNOT** (MP) · `LuaTimedActionNew.complete @31 L162` skips the Lua complete on a client |
| B6 | Handle a partial / cancelled eat | **CAN** · `ISEatFoodAction:serverStop` `:141–153` and its two guards |
| B7 | Hook the **drink** path the same way | **UNKNOWN -> X13** · `DrinkFluid`; `ISDrinkFluidAction` `:26–29`, `:40–46`; no `OnEat` twin named anywhere — Task 1 Step 2's hook inventory decides |
| B8 | Skip vanilla's whole stat tick and run our own | **CAN** · `TriggerHook("CalculateStats") @49–@59 L10204-L10205` |
| C1 | Change the thresholds or rates inside `updateWeight` | **CANNOT** · Task 1 J1; the only nutrition sandbox lever is `Nutrition` on/off (slice 01) |
| C2 | Replace the weight model wholesale | **CAN WITH A WORKAROUND -> X7** · `Nutrition = false` gates `Nutrition.update()` — drain **and** burn **and** weight, so all three must be reproduced |
| C3 | Write weight from Lua | **CAN** (server only) · M `exp03-20260910-045523` |
| C4 | Let the **client** compute weight | **CANNOT** · `updateWeight @317–@320 L198` skip, C + M |
| C5 | Read the weight-direction flags client-side | **CAN** · M `td2-20260910-231655`; the flag threshold is carbs **or** lipids > **400**, not 700. **Bound:** the three flags agreed only in `updateWeight`'s **trivial** arm (calories 798 -> 783, thresholds 0/1000) — the gain and loss arms are unrun, so "the sides agree" is not yet a finding here (`-> X9`'s sibling; slice 12's M8 takes the arms) |
| C6 | Apply the weight-band traits on demand | **CAN** · `applyTraitFromWeight()` is public, Lua-reachable and instant, M `exp03-20260910-045523` |
| D1 | Register a **new** `MoodleType` | **UNKNOWN -> X3** · Task 1 J3: the jar *does* carry `MoodleType.register(String)` / `registerBase(String)` / `register(boolean,String)` and `MoodleStat.register(MoodleType,F,F,F,F,F)`, and `MoodleType` is Lua-exposed (`PZTestKit_Client.lua:436 (was :461 before ad683fe)`), so the registration path exists — what is unknown is whether a **Lua** registration survives the load order and **renders**. Do **not** carry this as `CANNOT`: plan 14 would inherit a wall that is not there. Moodles being absent from `media/scripts` says only that the route is not the script DSL |
| D2 | Retune an existing moodle's thresholds at runtime | **CAN -> X2** · `MoodleStat.get` + `setLowestThreshold` (C); Lua reach and per-player-vs-global scope unmeasured |
| D3 | Change what a moodle **does** | **CANNOT** · `BodyDamage.UpdateStrength @2–@121 L2062–L2078` and `.Update`; the constants are `<init>` fields |
| D4 | Render a mod nutrient as a moodle | **CAN WITH A WORKAROUND** · MoodleFramework being "whole on 42.20.4" is **C derived from the merge rule** — **nothing has booted it**, and its `MF_Config.lua`-executes step is C for the same reason; its API surface and MP behaviour stay unread (patterns § Open pattern questions). Residual risk carries all three; the workaround is adoption, not a measurement |
| D5 | Get a moodle to the other side | **CAN** (nothing to sync) · `Moodles.Update` has no side guard and moodles are absent from `PlayerStatsPacket` — each side recomputes |
| E1 | Add a field to `ItemStatsPacket` | **CANNOT** · Task 1 J5; 43 fields / 39 item state, C + M slice 09 |
| E2 | Depend on an item field the packet omits | **CANNOT** · FILTER 1; `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` never arrive, M `td1-20260910-192457` |
| E3 | Get a per-item mod value to the client anyway | **CAN WITH A WORKAROUND** · script (KEEP 11) or the command bus keyed on `getID` (same instance both sides, M) |
| E4 | Trust a zero-valued packet field | **CANNOT** · the cached-packet leak, C + M `exp02-20260910-030433` |
| E5 | Trust a cooked food's `thirstChange` client-side | **CANNOT** · halves once per hop, converges, M `td1`/`td1b` |
| E6 | Trust a live item field's client copy to tick | **CANNOT** · M **per arm**, n = 1 each. Honest form, and the row must use it: *`Food.update` did not advance the client copy in this window* — one cookable item, one 12.54 s window, one fixture, below the strict `heat > 1.6f` gate, where the copy read bit-frozen. **Not** "client copies cannot tick": frozen and non-cookable items and every other push path are untested |
| E7 | Push a player stat client → server | **CANNOT** · 1 Hz `PlayerStatsPacket` overwrite within ~1.5 s, M |
| E8 | Push an item field client → server | **CANNOT** · `sendItemStats` is a silent no-op on a client, M spike S6 |
| E9 | Keep server-authoritative state in player modData | **CAN WITH A WORKAROUND** · FILTER 10 — someone else's transmit destroys it, M `td2-20260910-231655` |
| E10 | Transmit **part** of player modData | **CANNOT** · whole-table wipe-and-replace, C (`ObjectModDataPacket.write`, `KahluaTableImpl.load @5-@6 L333`). **M is uneven across the two halves:** REPLACE is corroborated (pass 3), the **WIPE** half rests on a single pass-2 reading with no server-only key planted — slice 12's M9 plants one and takes it to n = 2, so cite that artifact if it exists and carry the n = 1 bound if it does not |
| E11 | Move mod state over the command bus | **CAN** · KEEP 2; residual risk — our module names share the bus with the Girth stack's 228 command sites |
| F1 | Rewrite a crafted instance from `OnCooked` | **CAN** (server-side) · M `td1-20260910-192457`, LTP `recipe_meats.lua:45-49`. **Bound:** the **cooking pipeline itself stays C** — nothing on the bus reaches a right-click or executes `craftRecipe` (`recipes.craft` is a reader), so the hook's own registration and firing are read, not driven end to end |
| F2 | Change the evolved-recipe Cooking-perk scaling | **CANNOT** · Java; `(1 + lvl/15)` and `(1 − 0.03·lvl)`, slice 02 |
| F3 | Change the cooking gates or timers globally | **CANNOT** · Task 1 Step 3, `Food.update`'s `heat > 1.6f` and minute gate |
| F4 | Set per-item cook times | **CAN** · script keys `MinutesToCook` / `MinutesToBurn`, slice 02 |
| F5 | Control spice behaviour (`allowSpice`) | **UNKNOWN -> X9** · the flag gate is on the wave-4 open list |
| G1 | Add a **new** trait | **CAN WITH A WORKAROUND -> X10** · the mechanism is `zombie/scripting/objects/CharacterTrait.register` (Task 1 J4), which is what `media/scripts/generated/characters/character_traits.txt` drives, but the *effects* read `CharacterTrait` **statics** — so a registered trait exists and is selectable and carries no Java effect |
| G2 | Change a vanilla appetite trait's multiplier | **CANNOT** · `getAppetiteMultiplier @13–@31 L10323-L10324` |
| G3 | Add or remove a trait from Lua | **CAN** (server) · harness `trait.set`, M |
| G4 | Rely on a weight-band trait client-side | **UNKNOWN -> X4** · body-stats open question 10; both trait lists were empty in the only run that could have shown it |
| G5 | Call `HasTrait(String)` / `getTypeString()` | **CANNOT** (removed on 42.20.4) · C, slice 11; an unguarded Kahlua nil call aborts the rest of the handler body that reached it and names nothing, while `pcall` does catch it (corrected 2026-09-17 after slice 12 — see `.superpowers/sdd/13-wall-map/slice-12-outcomes.md`) |
| H1 | Ship mod translations beside vanilla's | **CAN** · `Translator.tryFillMapFromMods @0-@97 L376-L391` **merges**, C; `td3` M3 is consistent but non-discriminating |
| H2 | **Override** a vanilla translation key | **UNKNOWN -> X5** · the Translator merges rather than shadowing; `td3` M3 did not discriminate |
| H3 | Use a B41-layout `ItemName_EN.txt` | **UNKNOWN -> X1** · display-name hypothesis (ii); the block was a write into the read-only mod tree, and `testing/experiments/` removed it. **Slice 12's M4 measures exactly this** — if the manifest shows it settled, this row becomes M citing that artifact and X1 is struck |
| H4 | Ship a food absent from the translation table | **CANNOT** (it silently breaks weight) · `getActualWeightUnmodded` → 0 when `getDisplayName() == getFullType()`, M `td2` appendix A1 |
| I1 | Replace a vanilla Lua file at its own relative path | **CAN** · four jar sites; `LoadDirBase` dedupes vanilla-first through `activeFileMap`, so mod order does not matter |
| I2 | Retune the hunger/thirst constants by replacing `defines.lua` | **CAN WITH A WORKAROUND** · `ZomboidGlobals` is Lua read at load (C); it replaces the **whole** file, so two mods collide destructively and vanilla's future edits vanish |
| I3 | Ship `common/` beside a version folder | **CAN** (version wins) · M `td3-20260911-001948`, bounded to a version dir that ships colliding files |
| I4 | Rely on the `mod.info` id-read order | **UNKNOWN -> X11** · `searchForModInfo L708-L735`, `File.list()` order; slice 12 experiment (d) |
| I5 | Install under a folder whose name ≠ the declared id | **UNKNOWN -> X12** · profiles.md § Open questions 6, second half; slice 12 experiment (e) |
| I6 | `require` across the merged map | **CAN** · resolves through the same `activeFileMap`, C |
| I7 | `loadstring` | **CANNOT** (removed 42.20.x) · Task 1 J6; corpus count zero |
| I8 | Coexist with a second mod shadowing the same file | **CAN WITH A WORKAROUND** · `activeFileMap.put` is unconditional, last write wins in `File.list()`/mod order; residual risk — the loader's `overrides` print is the only visible signal |
| J1 | Redefine a vanilla `module Base` food block | **CAN** · slice 12 experiment (a); grade from its artifact, else C + W (the Mod_structure mirror) `-> X` |
| J2 | Do it across the 722 `base:food` items (1 005 dataset rows once drainables and fluid containers are counted; `data/README.md`) | **CAN WITH A WORKAROUND** · no corpus precedent (one collision in 230 mods: `Horse` redefining `Base.Rope`); the scale, not the mechanism, is the risk |
| J3 | Survive an MP script mismatch between server and client | **CAN** (no checksum gate found) · Task 1 Step 3's grep + `item.script` identical field-for-field on both sides, M `td1` |

- [ ] **Step 4: Ripple check.** `grep -n "slice 13\|13's wall map\|wall map" docs/progress.md` and confirm every ripple addressed to slice 13 maps onto a row above. Add a row for any that does not. Record the mapping in the harvest — Task 5's acceptance check re-runs this grep.
- [ ] **Step 5: No commit** (gitignored notes).

#### The slice-12 dependency rule

Applied per row, and stated once in the doc so a reader can see which rows rest on slice 12:

- **The artifact exists and settles the row** → grade `M`, cite `(x-run-id, key <k>)` and the slice-12 doc section.
- **The artifact exists but the reading is inconclusive** — the slice-12 doc says so, or the key is on that run's *do not cite* list → classify on what remains (C from the jar, or M from a wave-1–3 run), state the verdict anyway, append `-> X<N>`, and let the experiment row carry the **discriminating** probe the slice-12 doc itself names.
- **The artifact is missing** — slice 12 did not run it, ran a different one, or its docs are absent → classify from C alone, state the verdict, append `-> X<N>`, and write a full experiment spec (profile · driver · action · deciding reading · cost).
- A missing or inconclusive upstream artifact **never** stops the map, never produces a bare `UNKNOWN`, and never makes this slice boot the game. Log which of the three branches each affected row took in `docs/decisions.md` (one row for the set, not one per capability).

### Task 3: Name an experiment for every hole (no live server)

**Files:** Create `.superpowers/sdd/13-wall-map/gaps.md`.

- [ ] **Step 1: Collect the holes.** Every row the harvest marked `no evidence` or `-> X<N>`, plus every row whose verdict rests on C across an MP boundary that a session could measure.
- [ ] **Step 2: Write one spec per hole**, in the § Named experiments shape — `| Id | Row(s) | The question | Shape: profile · driver · action | The reading that decides it | Est |`. **Constraints on a spec, all mandatory:** it names an existing profile or a new `testing/profiles/<name>.toml` in `mod-under-test.toml`'s shape; its driver is `testing/experiments/td3_autocook.py`'s shape (client-first reads, driver-side wall brackets, provenance keys `harness_lua_commit`/`harness_lua_dirty`/`doctor_clean`, per-scope exclusion sets, the re-ask-once guard, `field_count == N`); its action is a bus call that actually exists (§ Command bus) or a harness addition under the standing rule; it states a reading that **discriminates** — "both sides agree" is not a result unless the sides were first made to differ; and it fits **one session** (≈3 min live, `≤ 2` h with the write-up). A hole needing more than that is split and said so.
- [ ] **Step 3: The seed set**, to be confirmed, merged or struck against the harvest — do not invent an `X` id for something already measured. **The strike rule, and it applies to four of these, not two:** slice 12 was sent to measure exactly the questions behind **X1** (its M4, the two translation layouts), **X8** (its M5, `OnEat` on an MP client), **X11** and **X12** (its `x122` L1 and its `x123` session) — so **strike any of the four whose question the slice-12 manifest of Task 2 Step 1 shows settled**, and keep only the ones the manifest shows missing or inconclusive. The manifest decides, not this list; a struck row's capability row cites slice 12's artifact instead of an `X` id.
  **X1** H3 — does 42.20.4 load a B41-layout `ItemName_EN.txt`? An experiment mod under `testing/experiments/` declaring two new foods, one named only in `ItemName.json` and one only in `ItemName_EN.txt`; read `getDisplayName` + `getActualWeightUnmodded` on both sides. **Strike if slice 12's M4 settled it** — that phase ships exactly these three items and reads exactly these getters; the write into `testing/experiments/` (rather than the read-only workshop tree) was what unblocked the question, and slice 12 already took it.
  **X2** D2 — is `MoodleStat` reachable from Lua, and is a threshold change per-player or global? `lua.global` + a harness read of `MoodleStat.get(MoodleType.HUNGRY)`, then a write, then `stats.get` on both sides.
  **X3** D1 — can a mod add a `MoodleType`? Decided by Task 1 J3 on the code; if J3 shows any registration member, X3 exercises it, else X3 becomes the MoodleFramework adoption read (its API surface is still unread).
  **X4** G4 — do weight-band traits reach the client? Server `trait.set admin Obese add`, then `stats.get` on both sides; body-stats open question 10 requires a **non-empty** trait list on the server.
  **X5** H2 — does a mod JSON displace a vanilla translation key? An experiment mod redefining one vanilla key, then client `text.get` on that key and on a control.
  **X6** A5 — what does the script parser do with an unknown key inside a food block? A mod block carrying `Vitamins = 12` beside real keys; `items.count` + `item.script` on both sides plus the server log — does the block still load with its known keys intact?
  **X7** C2 — what exactly stops at `Nutrition = false`? `sandbox.set Nutrition false` + a `nutrition_3day_*` scenario; the deciding reading is which of drain / burn / weight froze.
  **X8** B4 — does an `OnEat` handler fire on an MP client after a server eat? An experiment mod registering `OnEat` on both sides writing a counter to modData; `eat.action`; read both counters. **Strike if slice 12's M5 settled it** — that phase is this experiment, with `TKX_EatHook`'s shared-state `OnEat` probe and its per-side modData keys.
  **X9** F5 — the `allowSpice` flag gate; the flag agreement is on the not-settled list (only the `updateWeight` trivial arm agreed), so this needs the gain/loss arms. **X10** G1 — does a `CharacterTrait.register`-added trait carry any Java effect? **X11**/**X12** I4/I5 — slice 12's id-read-order and folder≠id experiments; **strike both if slice 12's artifacts settled them**. **X13** B7 — is there a drink-side hook at all, and does it fire server-side?
- [ ] **Step 4: Cost and owner.** Each spec carries an estimate and an owner — *slice 14*, *the mod's own build-out*, or *a standalone wave-5 slice*. The map is not a work queue for slice 13.
- [ ] **Step 5: No commit** (gitignored notes).

### Task 4: Write `docs/modding/wall-map.md`

**Files:** Create `docs/modding/wall-map.md`.

- [ ] **Step 1: Skeleton.** House shape, in this order: title; `**Verified against: 42.20.4 (`b0bbce05d5`)**` + today's date + which slices contributed; `## Summary` (five lines — what the map is, what a verdict means, the biggest three walls, the biggest three doors, what it is bounded to); `## How to read this map` (the four verdicts as defined in the cold-start context, the `Ev` grammar `<grade> · <slice> · <jar site | run id + key>`, the `-> X<N>` rule, and the bound: **every verdict is about 42.20.4 on a dedicated server; single-player is not claimed**); `## The map` with one sub-table per area **A New nutrient fields · B Eat hooks · C The weight formula · D Moodles · E Sync · F The cooking pipeline · G Traits · H Translations · I The merge rules and loading · J The item pass**; `## MP behaviour`; `## Named experiments`; `## What the library cannot yet measure`; `## Discrepancies`; `## Open questions`; `## Sources`.
- [ ] **Step 2: The map tables.** Columns, identical in all ten: `| # | Capability | Verdict | Mechanism | Workaround | Residual risk | Ev |`. Rules: a `CANNOT` cell's Mechanism names the jar site; a `CAN WITH A WORKAROUND` row **must** have a non-empty Workaround **and** a non-empty Residual risk; a `CAN` row's Residual risk may read `—` only when there genuinely is none; `Ev` is last and carries a standalone C/M/W. Prefer the shortest true citation — a run id plus a key beats a paragraph, and the canonical prose already lives in `patterns.md` and the teardowns, so **link, do not restate numbers** that another doc owns.
- [ ] **Step 3: `## MP behaviour`** (the house skeleton requires it, and here it is the cross-cutting statement, not a repeat): every verdict above is an MP verdict; the owning side per surface in one short table (player stats · nutrition · weight · traits · item state · item aging · script data · translations · moodles); the three viable shapes for mod state — server-side mutation over the command bus, player modData with an explicit transmit, or accepting client-only semantics — and which rows each shape's hazards attach to (E9/E10 for modData, E7/E8 for the push directions).
- [ ] **Step 4: `## What the library cannot yet measure`** — keep evidence limits out of the map proper: nothing on the bus executes a craft (`recipes.craft` is a **reader**), so a recipe's `onCreate`/`onTest` hooks stay C; there is no `triggerEvent` on the bus, so the pcall-vs-Kahlua-nil-call question inside an event dispatch is unmeasured; `witness.fields` reads zero-argument getters on the `IsoPlayer`/`InventoryItem` only (the `Nutrition` macros are not a `witness.fields` question) and caps at 32; one fixture, `DayLength = 4`, cadence ceiling `24 × speed / day_minutes ≲ 8`; most measured rows are `n = 1` session; artifacts older than `291f977` render floats `%.6f`, so no bit-level claim can rest on them.
- [ ] **Step 5: `## Discrepancies`** — at minimum reconcile the two packets (`ItemStatsPacket`, 43 fields, is the **item-stats** wire; `SyncItemFieldsPacket`, which `docs/modding/README.md` § Hard-won platform facts describes carrying condition/modData but not `conditionMax`, is a different packet and the ItemQuality case study's one) so a reader cannot conflate them; and any row where the Mod_structure / Mod_data / Networking mirrors disagree with the jar — **code wins**, the mirror preserves the wiki's version.
- [ ] **Step 6: `## Sources`** — jar (pzdis, 42.20.4 `b0bbce05d5`) with the class list from Task 1; the wave-1–3 docs by path; the three teardowns; the artifacts by run id with their `testing/artifacts/<run-id>/<file>.json` paths; slice 12's three docs and its artifacts; the wiki mirrors cited; `.superpowers/sdd/13-wall-map/{jar-locks,evidence-harvest,gaps}.md` named as the working reads (not deliverables).
- [ ] **Step 7: Commit** — `git commit -m "Slice 13: moddability wall map" -- docs/modding/wall-map.md`.

### Task 5: Lint, ripples, ledgers

**Files:** Modify `docs/modding/README.md`, `docs/modding/patterns.md`, `docs/progress.md`, `docs/decisions.md`; **conditionally** `testing/artifacts/README.md` (see § Done protocol — a Cited-by cell, or a full row only if the logged live session was taken).

- [ ] **Step 1: Neighbour edits.** `docs/modding/README.md` — replace the `moddability-walls.md` row of § Planned documents with a link to the shipped `wall-map.md`, and correct any § Hard-won platform facts bullet the map overturns (keep the bullet, mark what changed). `docs/modding/patterns.md` — add a one-line pointer to the map beside § Measured MP sync facts, and close or restate sharper any § Open pattern question the map settles (do **not** re-open one it does not). Nothing else in `docs/` is this slice's to edit.
- [ ] **Step 2: Gates.**

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/doc_lint.py docs/modding
python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey
python -m pytest tools/tests testing/tests -q
```

  Expected: `0 finding(s)` on both lint runs (the repo has been at 0 for these dirs since slice 09's backfill) and a green pytest (282 at the end of slice 10; do not let the count go **down**).
- [ ] **Step 3: The map's own mechanical checks.**

```bash
cd /c/Users/Angus/repos/project_zomboid && python - <<'PY'
import re, sys
VOCAB = ("CAN WITH A WORKAROUND", "CANNOT", "UNKNOWN", "CAN")   # longest first: CAN last
t = open('docs/modding/wall-map.md', encoding='utf-8').read()
m = re.search(r'^## The map\b.*?(?=^## |\Z)', t, re.M | re.S)   # the map proper, not every table
if not m:
    print('no "## The map" section'); sys.exit(1)
def cells(l):
    return [c.strip() for c in l.strip('|').split('|')]
rows = [l for l in m.group(0).splitlines()
        if l.startswith('|') and not re.match(r'^\|\s*:?-', l)
        and cells(l)[:2] != ['#', 'Capability']]          # body rows only, no headers
def verdict(l):
    c = re.sub(r'[*`]', '', cells(l)[2]).strip() if len(cells(l)) > 2 else ''
    return next((v for v in VOCAB if c == v or c.startswith(v + ' ')), None)
verdicts = [verdict(l) for l in rows]
counts = {v: verdicts.count(v) for v in VOCAB if verdicts.count(v)}
off = [cells(l)[0] for l, v in zip(rows, verdicts) if v is None]
refs = set(re.findall(r'->\s*(X\d+)', t))
defs = set(re.findall(r'^\|\s*\**(X\d+)\**\s*\|', t, re.M))
bad_unknown = [l for l in rows if 'UNKNOWN' in l and '-> X' not in l]
print('experiments referenced', sorted(refs), 'defined', sorted(defs))
print('dangling', sorted(refs - defs), 'unused', sorted(defs - refs))
print('UNKNOWN rows with no experiment:', len(bad_unknown))
print('verdict counts:', counts, '| sum', sum(counts.values()), '| map rows', len(rows))
if off:
    print('OUT-OF-VOCABULARY VERDICT in row(s):', off)
sys.exit(1 if (refs - defs) or bad_unknown or off else 0)
PY
grep -n "slice 13\|wall map" docs/progress.md
```

  Expected: no dangling `X` reference, no unused one, **0** `UNKNOWN` rows without an experiment, and the printed verdict counts **summing to the map's row total** — the script asserts that sum itself and **exits 1**, naming the offending row ids, when a row carries a word outside the fixed four-word vocabulary. Every progress-board ripple addressed to 13 must be traceable to a row (check by eye against the harvest's Step-4 mapping).
- [ ] **Step 4: Ledgers.** `docs/progress.md` — write the **resume note** under row 13 (what landed, the row and experiment counts, the gates' numbers, what remains) and the **ripples** listed in § Done protocol. `docs/decisions.md` — the rows listed in § Done protocol, one per decision, dated, slice 13.
- [ ] **Step 5: Commit and stop.** `git commit -m "Slice 13: wall-map ripples and ledgers" -- docs/modding/README.md docs/modding/patterns.md docs/progress.md docs/decisions.md` — adding `testing/artifacts/README.md` to the pathspec only if § Done protocol's condition applied. **No `git push`, and do not flip row 13 to `done`** — the row stays `in progress` with the resume note until the whole-branch review has run; the controller flips it and pushes at the slice close. Then hand off to slice 14 (`docs/superpowers/plans/14-feasibility-notes.md`).

## Deliverables

- `docs/modding/wall-map.md` — stamped, `## Sources` non-empty, ten graded sub-tables with an `Ev` column, `## Named experiments`, `## What the library cannot yet measure`, `## Discrepancies`, `## Open questions`.
- Updates: `docs/modding/README.md` (the planned-doc row and any overturned fact), `docs/modding/patterns.md` (pointer + any question the map closes), `docs/progress.md` (resume note + ripples), `docs/decisions.md` (the rows below), and **conditionally** `testing/artifacts/README.md` (§ Done protocol).
- Working reads, not deliverables (gitignored): `.superpowers/sdd/13-wall-map/{jar-locks,evidence-harvest,gaps}.md`.

## Acceptance checks

1. `python tools/doc_lint.py docs/modding` → `0 finding(s)`; `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey` → `0 finding(s)`; `python -m pytest tools/tests testing/tests -q` green, count not below 282.
2. Every row of every `## The map` sub-table carries a verdict from the fixed four-word vocabulary and a standalone C/M/W in its `Ev` cell (`doc_lint` enforces the grade; Task 5 Step 3 enforces the vocabulary).
3. **No row reads `UNKNOWN` without a `-> X<N>`**, every `-> X<N>` resolves to a row in `## Named experiments`, and no experiment row is unreferenced (Task 5 Step 3's script exits 0).
4. All ten design areas have at least one row: new nutrient fields, eat hooks, the weight formula, moodles, sync, the cooking pipeline, traits, translations, the merge rules, the item pass.
5. Every ripple in `docs/progress.md` addressed to slice 13 is a row in the map.
6. Every `CAN WITH A WORKAROUND` row has a non-empty Workaround **and** a non-empty Residual risk cell; every `CANNOT` row names a jar site in its Mechanism.
7. Every row that cites slice 12 names the artifact run id and key, or says which branch of § The slice-12 dependency rule it took.
8. Questions 1–10 each have a cited answer in the doc.

## Expected decision points (defaults)

- **Slice 12's docs or artifacts are missing, partial, or inconclusive** → apply § The slice-12 dependency rule; classify from the evidence that remains, never write a bare `UNKNOWN`, never block, never boot the game to fill the hole. One `docs/decisions.md` row for the set.
- **A row cannot be classified even from C** (the jar read is ambiguous and no doc decides it) → it is `UNKNOWN` with an `X` spec, **not** a live session. The single exception, and it must be logged: a row where one bus call on an existing profile would settle it *and* the answer changes the mod's shape (A5, C2, G4 are the candidates) may take **one** session under the standing rule — `python testing/pzt doctor` first, one live session at a time, the artifact committed with a `testing/artifacts/README.md` row, and the slice split rather than run twice.
- **The jar read disagrees with this plan's predicted verdict** → the reading wins, the row is corrected, and the disagreement goes in the harvest and in `docs/decisions.md`. This plan's row inventory is a prediction written from the corpus, not a finding.
- **A capability does not fit one area** → file it under the area whose *mechanism* decides it, not the one it feels like (a nutrient field carried on an item is **E** sync, not **A**), and cross-reference from the other area's table.
- **The row inventory grows past ~60 rows** → merge rows that share one mechanism and one verdict rather than dropping any; a row per jar site, not a row per phrasing. If it still overflows, the overflow is a new catalog entry, not a thinner doc (spec guard rail: a slice past twice its estimate is split).
- **An open question belongs to a vanilla model rather than to moddability** (`Thermoregulator.getEnergyMultiplier ≈ 1`, the weight-direction flags under both arms) → it stays in the doc that owns it and is **not** given an `X` id here; § Open questions links to it. The `X` table carries only experiments that settle a wall-map row.
- **A verdict would rest on the absence of a corpus precedent** (J2 at scale) → that is `CAN WITH A WORKAROUND` with the absence as the residual risk, graded **C**, never `CANNOT`. "Nobody has done it" is not a wall.
- **`doc_lint` flags a grade on a row whose Ev cell reads `M4` or similar** → the grade must be a standalone letter; rewrite as `M (…)`. Do not widen `STAMPED_DIRS` or touch `tools/doc_lint.py` — same ruling slices 07 and 08 took.
- **A neighbouring doc's older prose is overturned** → correct it in place in the same commit, keep the original claim visible as "previously stated", and add a ripple. Do not silently delete.

## Done protocol

- `docs/progress.md`: resume note under row 13 (what landed, the map's row and experiment counts, the two lint zeros and the pytest count, what remains = the whole-branch review). **Ripples for slice 14:** (a) the map's `CANNOT` rows are the hard constraints its feasibility notes must design around — new nutrient fields, the weight formula, moodles, the two packet walls; (b) the `CAN WITH A WORKAROUND` rows' *residual risk* cells are the risk register for every note; (c) `## Named experiments` is the open-work list — slice 14 says which of the `X` rows a design would have to settle before it is buildable, and which can stay open; (d) `## What the library cannot yet measure` bounds what any feasibility claim may assert. Row 13 → `done` is the **controller's** edit at the slice close, not Task 5's.
- `docs/decisions.md` rows: slice 13 is **offline** (no live session; classification only) and why; the four-word verdict vocabulary and the `-> X<N>` convention; the slice-12 dependency rule and which branch each affected row took; the area assignment rule (mechanism decides, not feel); every row where the jar read overturned this plan's prediction; the ruling that an absent corpus precedent is never a `CANNOT`; any live session taken under the exception above.
- `docs/modding/README.md` and `docs/modding/patterns.md` are updated in the same commit as the ledgers.
- `testing/artifacts/README.md`: **conditionally, and only in the two cases that can arise.** (a) If the single live session of § Expected decision points was taken, its artifact gets a full Contents row (run id / file / driver / cited-by) plus any *do not cite* rows, in that session's own commit and named in the Task 5 commit's pathspec. (b) Otherwise the map mints no artifact and this file is **not** touched for new rows — but where the map cites an existing artifact heavily, append `slice 13 docs/modding/wall-map.md` to that row's **Cited by** cell and nothing else. Slice 13 never edits another row's evidence.
- Commits: `Slice 13: moddability wall map` (Task 4) and `Slice 13: wall-map ripples and ledgers` (Task 5, whose pathspec gains `testing/artifacts/README.md` only when the case above applies), subject line only, no attribution, pathspec'd. **The slice does not push and does not flip the board.** Wave 4 continues with slice 14.
---

## Corrections applied (2026-09-17, Task 5)

This plan's row inventory and experiment seeds were written **from the corpus before slice 12
ran**, and the plan says so itself — *"This plan's row inventory is a prediction written
from the corpus, not a finding"*, with *"the jar read disagrees with this plan's predicted
verdict → the reading wins"* as its own expected decision point. The reading won **eighteen
times** — the sixteen seed rows this section first listed, plus **F5** and **B7**, added
2026-09-17 at the whole-slice review because `wall-map.md` § Discrepancies carries them and this
table did not. **Twelve** of the eighteen are verdict-level overturns (fourteen row ids across
§ Discrepancies' twelve rows); the other four — **B4**, **E10**, **I3** and **J2** — kept the
verdict they were predicted with and gained a **bound or a grade**, written into their own cells in
the map rather than into § Discrepancies. **The plan text above is left as written**; this section
is the authoritative delta.
The reader-facing version is `docs/modding/wall-map.md` § Discrepancies; the evidence is in
`.superpowers/sdd/13-wall-map/` — `jar-locks.md` (Task 1), `evidence-harvest.md` (Task 2),
`gaps.md` (Task 3), gitignored and kept for review.

### Seed rows overridden (§ Task 2 Step 3)

| Plan row | Predicted | Shipped in the map | The reading that overrode it |
|---|---|---|---|
| **J3** (the item-pass row, § Task 2 Step 3 — not Task 1's § J3, which is the moodle surface) | **CAN** — "no checksum gate found" | **CANNOT** `-> X16` | there is one, and it is a **content** hash: `ScriptManager.Load @680 L1525` feeds **every loaded script file, mod files included** to `NetChecksum$Checksummer.addFile @0–@107 L39–L56` — `Files.readAllBytes`, an in-place compaction dropping every **CR** byte, one running MD5 — compared at `ChecksumPacket.parseServer @72–@84 L231`. A mismatch is a **disconnect** (`NetChecksum$Comparer.update @62–@85 L213–L215`) with a 60 s server-side AntiCheat arm, and a role holding `Capability.BypassLuaChecksum` clears it. **No arm has ever been measured** |
| **D1** | **UNKNOWN** `-> X3`, with "do **not** carry this as CANNOT" | **CANNOT** (X3 struck) | registration is fine — the **level** is pinned at 0. `Moodle.Update()Z @0–@6 L93` presets the level to `MinMoodleLevel.ordinal()` and the 27 `if_acmpne` tests are **not** `else if`s, so an unmatched type falls through to the shared tail `@3291–@3293 L571`, which calls the **private** `updateMoodleLevel(0)` every tick; `moodleLevel` has no setter. Also **26** vanilla statics, not 27 |
| **D2** | **CAN** `-> X2` — "`MoodleStat.get` + `setLowestThreshold`" | **CANNOT**, merged as D2+D3 | the five threshold setter pairs are public **and unreachable**: `MoodleStat` is absent from `LuaManager$Exposer.exposeAll()` (dumped in full, 3 055 lines — `Moodle`, `Moodles`, `MoodleType`, `Registry`, `MoodlesUI` are all there) and no exposed method returns one. X2 is re-scoped to a one-line `lua.global MoodleStat` exposure probe with two hit-controls |
| **A5** | **UNKNOWN** `-> X6` — "script macro fields are not Lua-readable at all" | **CAN** (X6 struck) | the prediction confused the **script object's** macro getters (true) with **default modData** (a different table, readable): `Item.DoParam`'s default arm `@11805–@11895 L2992–L3003` `rawset`s the unrecognised key into `Item.defaultModData` and `Item.InstanceItem @3477 L1868` copies that table onto **every** instance — `item:getModData().Fibre` |
| **B2** | **CANNOT** — "`OnEat` fires after every stat / nutrition / mood write" | **CAN WITH A WORKAROUND** | `OnEat` does fire late, but it is not the only seam: a **server-side Lua wrapper of `ISEatFoodAction.complete` runs before `Eat`** — `order == "complete onEat "`, `completes` 1 server / 0 client (`x121-20260911-030023` → `phases.M5.globals`) |
| **B4** | **CANNOT** `-> X8` | **CANNOT** as B4+B5, graded **M** (X8 struck) | the plan's own strike rule fired: slice 12's M5 measured exactly this. `OnEat` fires on both sides (`calls` 1/1), but the client's call is `IsoGameCharacter.EatOnClient @0–@57 L5725–L5736`, which applies **no** numbers — a notification, not a double-apply; merged with B5, whose `LuaTimedActionNew.complete @31 L162` skips the Lua complete on a client |
| **C5** | **CAN**, bounded — "the flags agreed only in the **trivial** arm" (`-> X9`'s sibling) | **CAN**, both non-trivial arms agree (X9a struck) | `x121` `m8` drove both: **+1500** kcal reads T/F/F and **−100** kcal reads F/F/T identically on both sides, and `nutrition.set calories −100` is **not clamped at 0**. The bound narrows rather than lifts: `incWeightLot: true` was never produced anywhere in the artifact `-> X25` |
| **E10** | **CANNOT**, with the WIPE half at n = 1 | **CANNOT**, wipe half at **n = 2** | `x121` `phases.M9` planted a server-only key and it was gone **1.27 s** after the client transmit, which is the second subject the plan asked for (`td2-20260910-231655` was the first); the server→client replace stays n = 1 (`phases.M6`) |
| **G5** | verdict **CANNOT**; mechanism "an unguarded Kahlua nil call … while `pcall` does catch it" was still being corrected as the plan was written | verdict **unchanged**; the mechanism is rewritten and two new rows carry it | `pcall` **catches** a nil call on both sides (`x126-20260911-045205`) — map row **I13**; unguarded, it aborts the rest of **its own handler's body** while the handlers behind it still run (`x127-20260911-052049`, server VM) — map row **I14**. And no log ever names the missing global, so a dormant call inside a shadowed `common/` copy is invisible until that tree becomes the live one |
| **H3** | **UNKNOWN** `-> X1` | **CANNOT**, graded **M** (X1 struck) | `Translator.tryFillMapFromFile @4–@36 L357–L358` formats `%s/media/lua/shared/Translate/%s/%s.json` and **opens nothing else**; `x121` `phases.M4` read the B41-table item as `getDisplayName == getFullType` on **both** sides while its `ItemName.json` sibling in the same mod resolved on the client |
| **I3** | **CAN** (version wins), bounded to a version dir that ships colliding files, n = 1 | **CAN** at **n = 2**, with the empty-version-dir arm | `x122-20260911-032326` (`summary.L2_which`, `L2_trees`, `phases.L3.reading`) is a second subject and adds the arm the bound did not have: a version dir holding **only** a `mod.info` costs the mod nothing. Still untested: a version dir shipping `media/` that collides with *nothing* `-> X22` |
| **I4** | **UNKNOWN** `-> X11` — "`searchForModInfo L708-L735`, `File.list()` order" | **CAN** as I4+I5 (X11 struck) | `ZomboidFileSystem.searchForModInfo @0–@173 L708–L735` is **dead code**, referenced by nothing but its own recursive call. The live chain is `loadMods → … → readModInfoAux @32–@120 L184–L195`, which opens the **version dir's** `mod.info` if it exists, else `common/`'s, and parses that one file (`x123b-20260911-034500`). Bounded to the dedicated-server `Mods=` path `-> X21` |
| **I5** | **UNKNOWN** `-> X12` | **CAN**, merged into I4+I5 (X12 struck) | `x123-20260911-034426` `boots.drift`: a folder matching **neither** declared id loaded under the version dir's id — which is why **51** drifting workshop folders load in normal play (dated 2026-09-11) |
| **J1** | **CAN**, "grade from its artifact, else C + W", with a **wholesale reset** assumed | **CAN**, graded **M**, and the reset prediction **inverted** | `BaseScriptObject.reset()V @0 L194` is a **bare `return`**, so `LoadScripts`' per-body reset is inert and `Item.Load @22–@147 L1433–L1449` assigns **per key**: a partial block **merges** (`x121` `phases.M2.items."Base.Orange"`, `verdicts.M2b`) and a redefinition **replaces rather than adds** (`module Base` stayed at **722**). The whole item pass rests on this. The `ItemType`-omitted arm stays untested `-> X15` |
| **J2** | **CAN WITH A WORKAROUND** — "the scale, not the mechanism, is the risk" | **CAN WITH A WORKAROUND**, workaround rewritten | the verdict stands, and the ledger's ruling stands with it — an **absent corpus precedent is never a `CANNOT`**, it is a residual risk. The row now names **six** live risks: no precedent (one collision across 230 mods, swept 2026-09-10 17:47), the same-relative-script-path drop (I10), the replay order (J4), the `HungerChange` / weight coupling and the `serverStop` guard a rebalanced value can trip (B6 `-> X33`), the byte-identical-script requirement (J3), and mod-added foods sitting outside a `module Base` pass |
| **F5** *(added 2026-09-17, whole-slice review)* | **UNKNOWN** `-> X9` — "the `allowSpice` flag gate is on the wave-4 open list" | **CAN** (X9 split; **X9b** re-scoped to a desk read) | the vanilla surface is the **`Spice` script bool** (109 items) → `Item.spice` → `Food.setSpice` (`InstanceItem @675–@678 L1570`), which routes the ingredient down `EvolvedRecipe.addItem @582–@775 L336–L359`'s spice branch: no hunger, no macro transfer, no `MaxItems` charge, once per dish. The plan's "`allowSpice` flag gate" is **AutoCook's own Lua method**, not a vanilla one. What is left is the branch's effect beyond the herbal-tea sums `-> X9b` |
| **B7** *(added 2026-09-17, whole-slice review)* | **UNKNOWN** `-> X13` — "no `OnEat` twin named anywhere; Task 1 Step 2's hook inventory decides" | **UNKNOWN** `-> X13`, the verdict unchanged and the mechanism closed | the hook inventory **is** closed: `LuaHookManager.AddEvents @0–@40 L127–L135` declares **8** hooks and **6** are ever fired — none of them `Eat`, `Drink`, `Consume`, `Digest` or `Nutrition`, and `UseItem` / `WeaponSwingHitPoint` are never triggered anywhere in the jar. So X13 is re-scoped to the drink **wrapper** route only, by analogy with B2 |
| **G1** | **CAN WITH A WORKAROUND** `-> X10` — "the mechanism is `CharacterTrait.register`", saved and synced | **CAN WITH A WORKAROUND** as G1+G6 (X10 merged into X4) | `register` is right but insufficient: **selectability comes from `CharacterTraitDefinition.addCharacterTraitDefinition`**, public static and Lua-exposed `@667` — the call `media/scripts/generated/characters/character_traits.txt` drives. "Synced" is downgraded to **untraced**: `CharacterTraits` declares `write`/`read`, `PlayerStatsPacket` does not carry them, and no packet that does has been traced `-> X4`. `register(String)` is also the **one public arm** (`registerBase` and `register(boolean,String)` are `private static`), and the `base:` namespace is banned |

### Experiment ids

- **Struck as already settled (7):** **X1** (H3), **X3** (D1 — struck *as a render
  experiment*; D1 is CANNOT from the jar and only a load-order timing bound remains, which
  needs no boot), **X6** (A5), **X8** (B4), **X9a** (C5's sibling), **X11** (I4), **X12** (I5).
  The plan's **X9 carried two questions** and Task 2's fix round split it: **X9a** (the
  weight-flag arms — struck) and **X9b** (the `EvolvedRecipe.useSpice` read — kept,
  because it decides F5's residual risk).
- **Re-scoped (4):** **X2** → a one-line `MoodleStat` exposure probe riding another
  session; **X9b** → a 20-minute **desk read**, no boot; **X10** → merged into **X4**
  (the effect question is answered from the jar; what is left is the sync question, which is
  X4's); **X13** → the drink **wrapper** route only, since the hook-inventory half is
  answered — `LuaHookManager.AddEvents @0–@40 L127–L135` declares 8 hooks, 6 are
  ever fired, and **there is no `OnEat` twin**.
- **New:** X14–X19 (Task 2) and X20–X33 (Task 3). **26 live ids**, every one with a
  profile, a driver, a deciding reading, a cost and an **owner**.

### Counts, cites and two falsified cold-start claims

- **The inventory is 62 rows, not the 56 this plan and the task briefs quote.** 13 new rows
  (A8, E12, G6, H5, H6, I9, I10, I11, I12, J4, J5 and the two Lua-layer rows) took it to **75**,
  and the map ships **64** after eleven same-mechanism merges that keep **both** ids
  (`A2+A7`, `B4+B5`, `C3+C6`, `D2+D3`, `E1+E2`, `E7+E12`, `F2+F3`, `G1+G6`, `H5+H6`, `I1+I6`,
  `I4+I5`). Nothing was dropped.
- The two Lua-layer rows are **I13** (`pcall` catches a nil call) and **I14** (the unguarded
  raise). They are written `L1` / `L2` in the harvest to keep them apart from `lua-api.md`'s own
  `L1`–`L16`, and the map assigns them area-I ids.
- **The harness cite moved.** `testing/PZTestKit/PZTestKit/42/media/lua/client/
  PZTestKit_Client.lua:436 (was :461 before ad683fe)` — quoted in § Task 1 J3 and in
  seed row D1 — is now **`:440`** (`local eatenType = MoodleType and
  MoodleType.FOOD_EATEN`), re-located by content 2026-09-17. It moved in slice 12's harness
  comment residuals (`7dcb37a` / `96a777f`).
- **Task 2 Step 4 addressed 21 ripples to 13 and mapped all 21** — one (`:95`, the `-debug`
  client) to § What the library cannot yet measure rather than to a row, and one (`:100`, the
  `versionMin` / `versionMax` gate) forcing a **new** row, **I12**. The first pass mapped 20
  against a pre-close board; slice 12's close appended the qualifying clause that surfaced the
  21st, the `(from 01)` Kahlua ripple. **That 21 is `evidence-harvest.md` § Step 4's own count of
  the ripples it addressed — it is not the output of the grep this plan writes**, and an earlier
  draft of this section quoted it as "22 hits from § Task 2 Step 4's grep at `0da3372`", which does
  not reproduce: that grep (`slice 13\|13's wall map\|wall map`) returns **6** lines at `0da3372`
  and **11** at HEAD. The harvest widened it with `\|(from 12)` to reach the slice-12 ripples and
  counted **22** lines at `55a9bbd` — the board row plus the 21 bullets — which is **27** at HEAD
  now that slice 13's own ripples match the same pattern. Quote the harvest's mapping, never a hit
  count (corrected 2026-09-17).
- **Two claims in § Cold-start context are falsified** and are corrected wherever they are
  quoted: `searchForModInfo` does **not** "return the first `mod.info` whose id matches"
  — it is dead code (I4+I5 above) — and "a Kahlua nil call is uncatchable" is wrong
  in both halves (G5 above).
