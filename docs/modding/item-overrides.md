# Item overrides — the five routes a mod has into a vanilla item's nutrition

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-11 · slice 12 (P2a). Measured on five
experiment mods we wrote (`testing/experiments/TKX_*`), driven by four live sessions:
`x121-20260911-030023` (the routes), `x124-20260911-035819` (replay order),
`x122-20260911-032326` and `x123-20260911-034426` (the loader).
Evidence grades: **C** read from bytecode / Lua / scripts, **M** measured on the live dedicated
server + real client (run id and artifact key given), **W** wiki mirror (secondary).

## Summary

1. A second `item` block with a name the engine already holds does **not** create a second item
   and does **not** reset the first. Each body assigns only the keys it names, so redefinition is
   a **per-key merge with last-body-wins** — measured, and exactly what the jar says once you read
   what `reset()` actually does (nothing: `Item` inherits an empty method).
2. That makes a **partial** block the cheap route: restate the keys you want changed and every key
   you omit keeps its vanilla value. The plan for this slice predicted the opposite (a wholesale
   `ResetExisting` reset) and was **falsified** — see § Discrepancies 1.
3. Script values are correct on both sides **for free**: item scripts load per side and never
   sync. Everything a mod does in *Lua* to an item instance has to cross `ItemStatsPacket`'s 39
   item-state fields, and four of the fields a spoilage/cooking mod cares about are not in it.
4. A new item in the mod's own module collides with nothing, but without an `ItemName.json` entry
   it reads `getDisplayName() == getFullType()` and `getActualWeightUnmodded() == 0` — and a
   **dedicated server resolves no mod display name at all**, so never branch on names server-side.
5. Which mod's body lands last is **not** `Mods=` order (falsified, n = 2 boots). The jar names the
   ordering key as the lower-cased *relative script path*; four rival rules are still
   unseparated by measurement. § Load order between two mods has the state of it.

---

## Model

### The five routes

| # | Route | What it does | Ev |
|---|---|---|---|
| R1 | **Full restatement** of a vanilla block in `module Base` | every script key of that item is re-declared; the item record count does not change | **M** (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M2.items."Base.Apple"`, `phases.M1.items_count`) |
| R2 | **Partial block** in `module Base` | only the named keys change; every omitted key stays at vanilla | **M** (same file → `phases.M2.items."Base.Orange"`, `phases.M1.scripts."Base.Orange"`) |
| R3 | **New item in the mod's own module** | no collision possible; costs the display name unless the mod ships `ItemName.json` | **M** (same file → `phases.M1.items_count.foodByModule`, `phases.M4.items`) + **C** (the LTP precedent, run `td1-20260910-192457`) |
| R4 | **Lua hooks on the instance** — `OnEat`, a wrapper of `ISEatFoodAction:complete`, `OnCooked` | per-instance edits at eat/cook time, bounded by what `ItemStatsPacket` carries | **M** (same file → `phases.M5.globals`) + **C** (`IsoGameCharacter.Eat`, `EatOnClient`) |
| R5 | **Item modData** + `syncItemFields()` | arbitrary new fields (a custom nutrient) on one instance | **M** (same file → `phases.M7.before` / `phases.M7.after`) |

R1–R3 are script routes and are free of sync cost. R4–R5 are Lua routes and are not.

### What a second `item` block actually does

Four jar sites, read 2026-09-11 on 42.20.4, and one of them overturns the plan's prediction.

| Site | What it does | Ev |
|---|---|---|
| `ScriptBucket.CreateFromTokenPP @88-@159 L168-L175` | when `loadData` already holds the name, the parsed body is **appended** to the existing object's `LoadData.scriptBodies` (`@137-@146 L173`); no second object is created | **C** |
| `ScriptBucket.LoadScripts @140-@216 L252-L259` | `var5 = (mode == Reload) ? 0 : 1` (`@140-@152 L252`); then for each body `i`: `if (scriptType.hasFlag(ResetExisting) && i >= var5) script.reset();` (`@183-@205 L256-L257`) followed by `script.Load(name, body)` (`@208-@216 L259`). On `Init` the reset therefore **is** called before every body but the first | **C** |
| `ScriptType.<clinit> @644-@705 L84-L98` | `ScriptType.Item.flags` = `EnumSet.of(Clear, CacheFullType, ResetExisting, RemoveLoadError, SeekImports, AllowNewScriptDiscoveryOnReload)` (`@644-@684 L84`) minus `AllowNewScriptDiscoveryOnReload` (`@690-@697 L96`), assigned at `@698-@705 L98`. `Item` does carry `ResetExisting` | **C** |
| `BaseScriptObject.reset()V @0 L194` | **the body is a bare `return`.** `Item` declares no `reset`, and neither does its superclass `GameEntityScript` (`Item → GameEntityScript → BaseScriptObject`), so the virtual call above resolves to this empty method | **C** |
| `Item.Load @22-@147 L1433-L1449` | `ScriptParser.parse(body)`, then for each `key = value` element `Item.DoParam(key, value)`. Nothing clears a field the body does not name | **C** |

So the chain is real but inert: the engine *does* call `reset()` before the second and every later
body, and for an `item` that call does nothing at all. Combined with `Load`'s per-key `DoParam`,
the result is a **field merge across bodies, in replay order, last writer wins per key** — which
is what the run measured (§ R2). Mechanism closed; no open read left here.

One side effect, unmeasured: `Item.InitLoadPP @0-@78 L1411-L1421` runs once per appended body,
re-stamping `Item.fileName` (a redefined item reports the **last** mod's script file) and
allocating a fresh net id into `netIdToItem` / `netItemToId` for the same `moduleDotType`. Ev **C**.

---

## The routes in detail

### R1 — Redefine a vanilla name in `module Base`

Ship `module Base { item Apple { …all 17 keys… } }` with the one key you want changed. Mod A's
block is `testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt:3-22`
— the vanilla `Apple` block copied verbatim (**17** keys, not 18) with `Calories = 400.0` at `:13`.

| Reading | Client | Server | Ev |
|---|---|---|---|
| `Base.Apple` `getCalories` (vanilla 95.0) | 400 | 400 | **M** (`x121-20260911-030023` → `phases.M2.items."Base.Apple".witness`) |
| `getCarbohydrates` / `getLipids` / `getProteins` / `getHungChange` | 25.13 / 0.31 / 0.47 / −0.16 | identical | **M** (same key) |
| `foodByModule.Base` after three `module Base` redefinitions | — | **722**, delta 0 against the `exp05-20260910-084109` baseline (2026-09-11) | **M** (`phases.M1.items_count`; n = 3 boots with `x124` `phases.O3`) |

Two facts fall out. A redefinition **replaces, it does not add** — the `Base` food count never
moves. And the two sides agree for free, because item scripts are parsed per side and never
sync (KEEP 11, `docs/modding/patterns.md` § Measured MP sync facts).

The script *object* is a poor witness: `item.script` answers the seven shelf-life/cooking keys but
reports `Calories`, `Carbohydrates`, `Lipids`, `Proteins` **absent** on both sides — a known Kahlua
gap, re-confirmed here (`phases.M1.script_access`, Ev **M**). Only an instance getter discriminates.

### R2 — The partial block, and why the trap is not where the plan put it

Mod A's `Orange` block is four lines —
`tkx_item_override.txt:24-29`: `DisplayCategory`, `ItemType`, `Calories = 400.0`, and nothing
else. Vanilla Orange carries `HungerChange = -12`, `ThirstChange = -8`, `Calories = 65`,
`Carbohydrates = 16.27`, `Lipids = 0.3`, `Proteins = 1.0`, `DaysFresh = 6`,
`DaysTotallyRotten = 9`.

| Reading after the narrowed block | Client | Server | Ev |
|---|---|---|---|
| `getCalories` | **400** (mod) | **400** (mod) | **M** (`x121-20260911-030023` → `phases.M2.items."Base.Orange".witness`) |
| `getCarbohydrates` / `getLipids` / `getProteins` / `getHungChange` | 16.27 / 0.30 / 1.0 / −0.12 — **all vanilla** | identical | **M** (same key) |
| script `DaysFresh` / `DaysTotallyRotten` / `HungerChange` / `ThirstChange` | 6 / 9 / −12 / −8 — **all vanilla** | identical | **M** (`phases.M1.scripts."Base.Orange"`) |
| instance `offAge` / `offAgeMax` | — | 6 / 9 — the vanilla shelf life, never restated | **M** (`phases.M2.items."Base.Orange".server_item_get`) |

**The rule for an item pass: a partial block is SAFE for the keys it names and leaves everything
else at vanilla.** You do not have to restate every key. That is the opposite of what this slice's
plan predicted, and it is the single most consequential finding for a pass over the **1 005** item
records in `data/food-items.json` (`docs/vanilla/food-dataset-notes.md` § Summary): the pass can
ship minimal blocks carrying only the macros it re-bases, and every other key — icons, models,
evolved recipes, spoilage — stays whatever upstream says, including whatever a *later* game patch
changes it to.

**Bounds.** n = 1 item, one build, one key type (a float macro on a `base:food`). The block kept
`DisplayCategory` and `ItemType` on purpose, so **the arm where `ItemType` is omitted is
untested** — a block that drops it might still merge, or might fail to instantiate as a `Food`;
nothing here says which. The cheap probe is the same Orange block minus `ItemType`, reading
`items.count`'s `foodByModule.Base` (721 would show the item left the food pool) and the five
instance getters. Handed to slice 13.

**No precedent to copy.** Across the nine `script_nutrition` mods of the 230-mod corpus, measured
against the 5 092 distinct `module Base` item names vanilla declares, there is exactly **one**
name collision in the set — `Horse` redefining `Base.Rope`
(`docs/mods-survey/nutrition-mods.md` § Discrepancies 5, Ev **C**). Seven of the nine declare
`module Base`; only two define an item under it at all. So a 1 005-item pass has no shipped
example to imitate, and the merge mechanism above is the whole foundation it rests on.

### R3 — A new item in the mod's own module

`module TKX { item FibreBar / FibreBarNamed / FibreBarJson }`
(`tkx_item_override.txt:55-104`), three identical food blocks differing only in their translation
state. No collision is possible, and the item pool grows by exactly three.

| Reading | Value | Ev |
|---|---|---|
| `foodByModule.TKX` / `foodByModule.Base` (2026-09-11) | **3** / **722** (unchanged) | **M** (`x121-20260911-030023` → `phases.M1.items_count.foodByModule`) |
| `TKX.FibreBarJson` (entry in `42.20/media/lua/shared/Translate/EN/ItemName.json`) | client `getDisplayName` **"TKX Fibre Bar Json"**, `getActualWeightUnmodded` **0.3** | **M** (`phases.M4.items."TKX.FibreBarJson"`) |
| `TKX.FibreBarNamed` (entry in the B41 `ItemName_EN.txt` table) | client `getDisplayName == getFullType`, `getActualWeightUnmodded` **0** | **M** (`phases.M4.items."TKX.FibreBarNamed"`) |
| `TKX.FibreBar` (no entry anywhere) | client `getDisplayName == getFullType`, `getActualWeightUnmodded` **0** | **M** (`phases.M4.items."TKX.FibreBar"`) |
| all three on a **dedicated server** | `getDisplayName == getFullType`, `getActualWeightUnmodded` 0 — **the JSON one included** | **M** (`phases.M4.items.*.witness.server`) |

Three consequences.

**Ship `ItemName.json`, not the B41 `.txt`.** 42.20.4 loads the B42 JSON layout with bare
`Module.Name` keys (the filename supplies the `ItemName_` prefix); the B41 `ItemName_EN =
{ ItemName_TKX.FibreBarNamed = … }` table produced no name at all. n = 1 each.

**Never branch on a display name server-side.** A dedicated server resolved none of the three,
including the one the client resolved off the very same script and translation file. Anything
gated on `getDisplayName()` behaves differently on the two sides by construction.

**An untranslated item trips the slice-09 guard.** `getActualWeightUnmodded()` returns 0 whenever
`getDisplayName().equals(getFullType())` — established inside vanilla on
`Base.FruitSaladClay` (run `td2-20260910-231655`, `appendix.A1`) and reproduced here on our own
items. It matters because `ItemStatsPacket.setData` fills the wire's weight field from
`getActualWeightUnmodded()`, so a nameless new item ships **weight 0** to every client
(`docs/modding/patterns.md` § Measured MP sync facts → *The other direction*, Ev **C** for the
packet field). `getActualWeight()` itself stayed 0.3 on both sides here, because `isCustomWeight`
was false and the getter took its script-weight arm (`Food.getActualWeight @215-@287 L902-L908`;
the guarded `InventoryItem` route at `@288 L910` is the other arm), Ev **C**.

**`getText` is not the route to a mod's item names.** Bare and prefixed key forms both missed on
both sides while `getDisplayName()` off the instance answered correctly — the `ItemName.json`
table is loaded and working but unreachable through the `getText` global (**M**,
`testing/artifacts/x124-20260911-035819/platform-order.json` → `phases.O5`; n = 2 sessions for
the prefixed form, n = 1 for the bare form; no in-run positive control, so soundness leans on
slice 10's client-side IGUI hit). A translation-only gate must use an IGUI key, never an item name.

**The precedent.** LongTermPreservation4220 does exactly this at scale: 14 new food items with a
full macro set in its own `module Skittles`, **zero** name collisions against vanilla's 5 092
names, shelf life pinned in the script rather than in Lua. Its script half is correct on both
sides for free; everything it does in Lua is what desyncs
(`docs/mods-survey/teardowns/longtermpreservation4220.md` § Techniques worth stealing, run
`td1-20260910-192457`, Ev **C+M**). Cost of the route: our pass over `module Base` will not touch
those 14 foods, so on a server running both, 14 items keep upstream numbers while vanilla's are
re-based.

### R4 — Lua hooks on the instance

Three interception points, two of them measured here.

**`OnEat`** is a script key naming a **global** Lua function — the engine resolves it by name
through `LuaManager.getFunctionObject(food.getOnEat())`, so a local or a table member is never
found. Mod C sets `OnEat = TKX_OnEatProbe` on `Base.Banana`
(`testing/experiments/TKX_EatHook/42.20/media/scripts/tkx_eat_hook.txt:22`) and defines the probe
in a **shared/** file (`.../media/lua/shared/TKX_EatHook.lua:41`) so both Lua states hold it.

| Reading after one eat at fraction 1 | Client | Server | Ev |
|---|---|---|---|
| `TKX_EatHook.calls` | **1** | **1** | **M** (`x121-20260911-030023` → `phases.M5.globals`) |
| `TKX_EatHook.completes` | **0** | **1** | **M** (same key) |
| `TKX_EatHook.order` | `"onEat "` | `"complete onEat "` | **M** (same key) |
| `TKX_EatHook.lastCalories`, read inside the hook | **890.4** | **890.4** | **M** (same key; the eat started from 786.86) |
| `TKX_EatHook.wrapped` / `wrapAt` | true / `"file"` | true / `"file"` | **M** (same key) |

So: **`OnEat` fires on both sides**, once, at the full fraction. It fires **after** every stat,
nutrition and mood write and **before** the item is consumed — `Eat` writes the numbers, sends
`SyncPlayerStats` / `sendSyncPlayerFields` / `EatFood` (`@645-@732 L5805-L5808`), dispatches
`OnEat` (`@762-@802 L5811-L5814`), then consumes at `@803 L5819` (Ev **C**,
`docs/vanilla/eating-pipeline.md` § Model → *`OnEat`, `EatType`, `Eattime`*). The client's copy is
a different call site — `IsoGameCharacter.EatOnClient @0-@57 L5725-L5736`, driven by
`EatFoodPacket.processClient`, whose
`parse` has already run `Nutrition.load` — which is why the hook read the **same post-intake
890.4** on both sides. `EatOnClient` applies no numbers of its own, so a hook there is a
notification, not an intake point.

**A Lua wrapper of `ISEatFoodAction:complete`** is the place to sit if you need the item *before*
`Eat` consumes it. It ran **server-only** (`completes` 1 / 0) and **before** `Eat`
(`order` = `"complete onEat"`). The wrapper is installed from a `server/` file
(`.../media/lua/server/TKX_EatHook_Server.lua:54`, sentinel at `:31`, re-tried on
`Events.OnServerStarted` at `:70`) — and it reports `wrapped = true` on the **client** as well,
silently, because a mod's `media/lua/server/` files execute in the MP client's Lua state. That
finding is `docs/modding/anatomy.md`'s row, with its bound (n = 1 session, mechanism untraced);
cite it there rather than from here.

**`OnCooked`** is the third point, and slice 09 measured it: the dispatch inside `Food.update` is
**not** server-gated (`@627-@718 L462-L467`, Ev **C**), and LTP's server-side hook rewrote the
crafted instance's fields with its prints landing in the **server** console (Ev **M**, run
`td1-20260910-192457`; `docs/mods-survey/teardowns/longtermpreservation4220.md` § MP handling).

**The limit that binds all three.** Whatever a hook writes to an item reaches the other side only
through `ItemStatsPacket` — 43 packet fields of which 2 are addressing and 2 are presence flags,
leaving **39 item-state values** (`setData @0-@566 L153-L229`, `write @0-@875 L233-L363`, Ev
**C**; `docs/vanilla/food-item-model.md` § MP behaviour). `offAge`, `offAgeMax`, `isCookable` and
`isCustomWeight` are **not** among them and never arrive — measured, the client held `offAge 53`
against the server's 1e9 and `isCookable true` against `false` across two snapshots 11.1 s apart
(**M**, run `td1-20260910-192457`). And a cooked food's `thirstChange` is **halved once per
server→client hop**, because `setData` sends the cooked-ladder getter while `applyItemStats`
stores it as the raw field (**M**, runs `td1-20260910-192457`, `td1b-20260910-202029`). Design the
hook so the client never needs the fields that do not travel.

### R5 — Item modData, the new-nutrient route

Mod B walks the player's inventory once per `EveryOneMinute`, and on each `Base.Cheese` instance
writes `imd.TKX_fibre = 12.5` followed by `item:syncItemFields()`
(`testing/experiments/TKX_Nutrient/42.20/media/lua/server/TKX_Nutrient_Server.lua:28-29`).

| Reading | Client | Server | Ev |
|---|---|---|---|
| `Base.Cheese` item-modData census, `beyondVanilla` | `["TKX_fibre"]` | `["TKX_fibre"]` | **M** (`x121-20260911-030023` → `phases.M7.before`, `phases.M7.after`; identical at both snapshots) |
| which VM performed the write (`TKX_Nutrient.itemWrites`) | **1** | **0** | **M** (`phases.M7.mod_globals`) |

**Per-item custom nutrients are not a CANNOT** — a custom key on an item's modData was visible on
both sides. But read the second row before reusing it: the write and the `syncItemFields()` both
ran in the **client's** Lua state, so what this measures is the **client→server** direction. The
**server→client** direction via `syncItemFields()` is **unmeasured** here, and the artifact's
`verdicts.M7` over-claims it — do not cite that key. The probe that closes it is the same mod with
its `server/` file guarded by `isServer()`, so only the server VM writes.

**Player modData is the other half, and it is hostile.** Both directions are destructive:

| Direction | What the receiver does | Ev |
|---|---|---|
| server → client `transmitModData()` | **replaces** the client's table: the client lost `hotbar` and `TKX_eat_onEat_client`, gained the server's `TKX_eat_onEat_server` | **M** (`x121-20260911-030023` → `phases.M6.late` vs `phases.M6.after_transmit`; n = 1, graded after setting aside the one key the client's own file rewrote afterwards) |
| client → server `transmitModData()` | **wipes**: a key planted server-side only (`TKX_ServerOnly`) was gone 1.27 s after the client transmit | **M** (`phases.M9.transmit_wipe`; the wipe half at n = 2 with run `td2-20260910-231655`) |

So player modData is a shared channel that either side can flatten. Keep server-authoritative
per-player nutrient state out of it — a server-side table plus `sendServerCommand`, or global
modData (`docs/modding/patterns.md` FILTER 10).

**Two keys any item-modData census must exclude**, or it will report vanilla as a finding:
`customName`, which `InventoryItem.setCustomName` writes into modData from `InventoryItem.load`
as a deserialization side effect (**M**, run `exp08-20260910-152944`), and `Tooltip`, which
`Item.InstanceItem @3505-@3510` passes to `InventoryItem.setTooltip`, whose first act is
`getModData():rawset('Tooltip', …)` — so any script `Tooltip =` line is an item-modData key on
every side that instantiates the item (**C**, jar). The exclusion set is chosen **per scope**: a
player census excludes the four vanilla fitness keys and `hotbar` instead
(`docs/decisions.md`, 2026-09-10, slice 09 row).

---

## Load order between two mods

Two different collisions, resolved by two different mechanisms. Keep them apart.

### (a) Two mods ship the same relative script path

The file list the parser walks is keyed on the **lower-cased path relative to the mod's version
directory** — `media/scripts/foo.txt` for every mod, and `media/scripts/…` for vanilla too
(`ScriptManager.searchFolders @93-@122 L1208-L1210` stores
`getRelativeFile(base, abs).toLowerCase(ENGLISH)`; `getRelativeFile @0-@90 L1011-L1026` is
`base.relativize(lowercasedAbsUri).getPath()`). Those strings are then resolved back through
`ZomboidFileSystem.getAbsolutePath @0-@19 L483-L484`, a plain `activeFileMap` lookup, and the
walk drops any relative path it has already seen (`ScriptManager.Load @562-@619 L1509-L1515`, a
`HashSet`). `activeFileMap` holds **one** absolute path per relative path, filled by
`ZomboidFileSystem.loadMod`'s two unconditional `put`s (`@205-@216 L758` for `common/`,
`@396-@407 L773` for the version dir). Ev **C** throughout.

Consequence: **two mods shipping `media/scripts/items.txt` do not both load — one file wins and
the other's blocks are never parsed**, and the loader prints a `mod "<id>" overrides <relpath>`
line when it happens. Within one mod that collision is measured (the version dir wins, `common/`
still runs; **M**, run `x122-20260911-032326`, keys `summary.L2_which` / `L2_trees` /
`phases.L2.reading.overrides_tails`), and the loader prints only on a real collision
(`greps.overrides_any` 1 of 2 mods). **Across two mods it is C only** — no session has shipped the
same relative script path from two mods. Practical rule for the item pass: give the pass's script
files a mod-unique basename and the question never arises.

### (b) Two mods redefine the same item name in different files

Then both files parse, both bodies append (§ *What a second `item` block actually does*), and the
question is which body replays last.

**What the jar says (C).** `ScriptManager.Load @97-@536 L1440-L1502` builds the vanilla list
first, then walks `ZomboidFileSystem.getModIDs()` (`@105-@111 L1441`; `getModIDs @0-@4 L972`
returns the `mods` list as stored, unsorted), appending each mod's `common/` then version-dir
script files (`@234-@242 L1456`, `@415-@423 L1474`). It then sorts **both** lists with
`ScriptManager$38` (`@524-@535 L1500-L1501`) and appends the mod list to the vanilla list
(`PZArrayUtil.addAll @0-@45 L1365-L1369`, dest-then-src). `ScriptManager$38.compare @0-@72
L1489-L1497` puts basenames starting `template_` first and otherwise returns
`a.compareTo(b)` on the **full stored path strings** — which are the lower-cased *relative* paths
from (a). So the ordering key the jar names contains no mod id, no folder name and no `Mods=`
position: it is the script file's path under `media/`, pooled across every mod, with vanilla's
bodies always first.

**What the runs measured (M).** Two boots, both consistent with that and with three other rules:

| Boot | `Mods=` order | Bodies for `Base.Watermelon` | Read on both sides | Ev |
|---|---|---|---|---|
| `x121-20260911-030023` | `TKX_ItemOverride`, `TKX_Nutrient`, `TKX_EatHook` | 111 (`tkx_item_override.txt:43`), 777 (`tkx_eat_hook.txt:37`) | **111** — the mod **earlier** in `Mods=` | **M** (`phases.M3.watermelon.witness`) |
| `x124-20260911-035819` | `TKX_ZWatermelon`, `TKX_ItemOverride`, `TKX_EatHook` | 999 (`tkx_zwatermelon.txt:15`), 111, 777 | **999** — the mod **first** in `Mods=`, last alphabetically | **M** (`testing/artifacts/x124-20260911-035819/platform-order.json` → `phases.O1.witness`, `verdicts.P18`) |

`Mods=`-order-last-wins is **falsified**, n = 2 boots. But the rule is **not settled**:
alphabetical-by-id, alphabetical-by-folder, alphabetical-by-script-path and
first-in-`Mods=`-wins all predict 999 here and 111 there, because our three ids, three folder
names and three script basenames sort identically and `Mods=` was deliberately reversed. Do not
write "alphabetical by mod id" and do not write "`Mods=` position is irrelevant" — the review of
session 4 struck both.

The loader's own `loading <id>` lines **do** walk `Mods=` order (server lines 94/97/99 in `x121`,
94/96/99 in `x124`, **M**), which is a separate order from the body replay and is the reason the
two are easy to confuse.

**The checks that close it.** Session 5 (`x125`) was running when this was written: the same three
mods with `Mods=` order `TKX_ItemOverride, TKX_ZWatermelon, TKX_EatHook`, where 999 / 111 / 777
separate alphabetical-last, first-in-`Mods=` and `Mods=`-last. That still leaves
id-vs-folder-vs-path confounded, and the jar read above says the answer is **path**; the boot that
would make it **M** is a mod whose **id sorts last while its script basename sorts first**
(e.g. id `TKX_ZZ`, file `aaa_watermelon.txt`). Handed to slice 13.

**What is safe to rely on today.** Per-key last-wins is settled (§ R2): whichever body lands last
wins only the keys it names. So a pass that ships one `module Base` block per item is robust to the
ordering question for every key it does *not* touch, and contested only on the keys two mods both
declare.

---

## MP behaviour

| Fact | Ev |
|---|---|
| Item **scripts** load per side and never sync, so a script-declared value is identical on both sides for free (KEEP 11) | **M** (`x121-20260911-030023` → `phases.M2`, both sides equal on every reading; and run `td1-20260910-192457` `item_script`) |
| Lua edits to an item cross only through `ItemStatsPacket`'s **39** item-state fields; `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` never arrive; a cooked food's `thirstChange` halves per server→client hop | **M** (runs `td1-20260910-192457`, `td1b-20260910-202029`); **C** for the field count (`setData @0-@566 L153-L229`) |
| `Nutrition` is server-authoritative; a client write is overwritten inside ~1.5 s by the 1 Hz `PlayerStatsPacket` | **M** (runs `exp01-20260910-003929`, `exp03-20260910-045523`) |
| The three weight-direction flags **agree across sides on non-trivial arms** and are not clamped: calories driven to 1500 read `isIncWeight`/`isIncWeightLot`/`isDecWeight` **T/F/F** on both sides; driven to −100 they read **F/F/T** on both sides with the value read back at −102.57 (no clamp) | **M** (`x121-20260911-030023` → `phases.M8.arms`, `m8.restore`) |

That last row closes the question slice 11 carried (the flags had only ever agreed in
`updateWeight`'s trivial arm). The rows it settles live in
`docs/modding/patterns.md` § Measured MP sync facts (the `setWeight` row's slice-10 half) and
`docs/mods-survey/teardowns/autocook.md` § MP handling → *The flags AutoCook actually gates on*;
Task 10 of this slice updates both.

---

## Discrepancies

| # | What was expected | What is actually the case | Ev |
|---|---|---|---|
| 1 | A second `item` block is a **wholesale reset**: `ScriptType.Item` carries `ResetExisting` and `LoadScripts` calls `reset()` before every body but the first, so a partial block rebuilds the item from that block alone (this slice's plan, § Cold-start context) | **Falsified.** The `reset()` call happens exactly as predicted, and does nothing: `BaseScriptObject.reset()V @0 L194` is an empty `return` and neither `Item` nor `GameEntityScript` overrides it. `Item.Load` assigns per key. Result: a per-key merge. Measured first (`x121` `verdicts.M2b`), then re-derived on the jar 2026-09-11 | **M** + **C** |
| 2 | Script bodies replay in **alphabetical-by-mod-id** order (the pre-review reading of session 4) | Superseded by the session-4 review: four rules — by id, by folder, by script path, and first-in-`Mods=` — all fit both boots. `Mods=`-order-last-wins is falsified (n = 2). The **jar** names the key as the lower-cased relative script path (**C**); the rule stays **open** by measurement | **M** for the numbers, **C** for the ordering site |
| 3 | The vanilla `Base.Apple` block has 18 keys (this slice's plan) | **17** — counted in `media/scripts/generated/items/food.txt` and reproduced in mod A's restatement | **C** |
| 4 | `getText` / the harness's `text.get` can read a mod's item name | It cannot, under either key form, on either side, while `getDisplayName()` off the instance answers correctly. Every display-name row here rests on `getDisplayName` | **M** (`x124-20260911-035819` → `phases.O5`) |

---

## Open questions

1. **A partial block that omits `ItemType`.** Untested; our R2 block kept it. Probe: the same
   Orange block minus `ItemType`, read `foodByModule.Base` plus the five instance getters.
2. **The replay ordering key** — id vs folder vs script path. `x125` discriminates
   alphabetical-last from first-in-`Mods=`; the id-vs-path closer is a mod whose id sorts last and
   whose script basename sorts first. The jar's answer (path) is **C** and wants a boot.
3. **Two mods at the same relative script path.** The `activeFileMap` mechanism is **C**; no run
   has shipped the collision across two mods. The sharpest arm is a mod file at a **vanilla**
   relative path (`media/scripts/generated/items/food.txt`), which the same read predicts is
   dropped entirely.
4. **`syncItemFields()` server→client.** R5 measured client→server only. Probe: the same mod with
   its `server/` file guarded by `isServer()`.
5. **Does the merge survive a `reloadlua` / script reload?** `LoadScripts`'s `var5` is 0 on
   `ScriptLoadMode.Reload`, so on a reload `reset()` runs before the **first** body too — still a
   no-op for an `item`, but `ResetOnceOnReload` and `PreReload` take other paths that this slice
   did not read.
6. **Redefinition and the net id.** `Item.InitLoadPP` allocates a fresh `netItemToId` entry per
   appended body. Whether a stale id is ever put on the wire is unread.

---

## Sources

**Sessions and artifacts (M).**
`testing/artifacts/x121-20260911-030023/platform-overrides.json` — routes R1–R5, keys `phases.M1`,
`phases.M2`, `phases.M3`, `phases.M4`, `phases.M5`, `phases.M6`, `phases.M7`, `phases.M8`,
`phases.M9`, `m8`, `greps.loading`.
`testing/artifacts/x124-20260911-035819/platform-order.json` — replay order and the `getText`
route, keys `phases.O1`, `phases.O3`, `phases.O5`, `verdicts.P18`, `greps.loading`.
`testing/artifacts/x122-20260911-032326/platform-loader.json` — the same-relative-path collision
inside one mod, keys `summary.L2_which`, `L2_trees`, `phases.L2.reading.overrides_tails`,
`greps.overrides_any`.
Earlier runs cited by id, not re-graded here: `td1-20260910-192457`, `td1b-20260910-202029`,
`td2-20260910-231655`, `exp01-20260910-003929`, `exp03-20260910-045523`, `exp05-20260910-084109`,
`exp08-20260910-152944`.

**Experiment mods (the exact blocks the readings came from).**
`testing/experiments/TKX_ItemOverride/42.20/media/scripts/tkx_item_override.txt`,
`.../TKX_ItemOverride/42.20/media/lua/shared/Translate/EN/ItemName.json` and `ItemName_EN.txt`,
`testing/experiments/TKX_EatHook/42.20/media/scripts/tkx_eat_hook.txt`,
`.../TKX_EatHook/42.20/media/lua/shared/TKX_EatHook.lua`,
`.../TKX_EatHook/42.20/media/lua/server/TKX_EatHook_Server.lua`,
`testing/experiments/TKX_Nutrient/42.20/media/lua/server/TKX_Nutrient_Server.lua`,
`testing/experiments/TKX_ZWatermelon/42.20/media/scripts/tkx_zwatermelon.txt`.

**Jar reads (C), 42.20.4, 2026-09-11** (`C:\Users\Angus\pz-b42`, `./pz.sh dump|methods`).
`zombie/scripting/ScriptBucket` — `CreateFromTokenPP`, `LoadScripts`;
`zombie/scripting/ScriptType` — `<clinit>`;
`zombie/scripting/objects/BaseScriptObject` — `reset`;
`zombie/scripting/objects/Item` — `Load`, `InitLoadPP` (class chain
`Item → zombie/scripting/entity/GameEntityScript → BaseScriptObject`, no intermediate `reset`);
`zombie/scripting/ScriptManager` — `Load`, `loadScripts`, `searchFolders`;
`zombie/scripting/ScriptManager$38` — `compare`;
`zombie/util/list/PZArrayUtil` — `addAll`;
`zombie/ZomboidFileSystem` — `getModIDs`, `getRelativeFile`, `getAbsolutePath`.
Earlier jar reads quoted from the docs that own them, not re-derived here:
`IsoGameCharacter.Eat` / `EatOnClient` and `EatFoodPacket`
([`../vanilla/eating-pipeline.md`](../vanilla/eating-pipeline.md));
`ItemStatsPacket.setData` / `write`, `Food.getActualWeight`, `Food.update`'s `OnCooked` dispatch,
`Item.InstanceItem` → `InventoryItem.setTooltip`
([`../vanilla/food-item-model.md`](../vanilla/food-item-model.md));
`ZomboidFileSystem.loadMod`'s two `activeFileMap` passes
([`patterns.md`](patterns.md) KEEP 10).

**Library cross-references.**
[`patterns.md`](patterns.md) § Measured MP sync facts (the sync rows, FILTER 10, KEEP 10/11),
[`anatomy.md`](anatomy.md) (mod layout; the `server/`-Lua-in-the-client-VM row),
[`../vanilla/eating-pipeline.md`](../vanilla/eating-pipeline.md) § `OnEat`, `EatType`, `Eattime`,
[`../vanilla/food-item-model.md`](../vanilla/food-item-model.md) § MP behaviour,
[`../vanilla/food-dataset-notes.md`](../vanilla/food-dataset-notes.md) (the 1 005 item records),
[`../mods-survey/nutrition-mods.md`](../mods-survey/nutrition-mods.md) § Discrepancies 5,
[`../mods-survey/teardowns/longtermpreservation4220.md`](../mods-survey/teardowns/longtermpreservation4220.md)
§ Techniques worth stealing and § MP handling,
[`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md) § MP handling →
*The flags AutoCook actually gates on*,
`docs/decisions.md` (the per-scope modData exclusion sets).
