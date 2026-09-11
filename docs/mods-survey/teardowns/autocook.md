# Teardown: Auto Cook (`AutoCook`)

**Verified against: 42.20.4 (`b0bbce05d5`)** — mod read cold 2026-09-10 (no server), then
measured 2026-09-11 on one dedicated-MP session with a real client:
`td3-20260911-001948` (acceptance `run-20260911-001251`).

- **Workshop ID / mod ID(s):** item **`3388721641`**, one mod, declared id **`AutoCook`**
  (`common/mod.info:3`) — and the folder is `AutoCook` too, so unlike passes 1 and 2 there is
  **no id/folder drift** to guard. `mod_lint` verdict, re-run 2026-09-10: exit 0,
  `0 ERROR / 1 WARN / 0 INFO` — `mod-info-place: mod.info is common/mod.info, not 42.13/mod.info`
  (see § Compatibility notes, which is where that WARN's own text turns out to be the questionable
  half). Workshop page (W): *Auto Cook*, 129.161 KB, posted Dec 21, 2024 @ 8:53am, **updated
  Sep 6 @ 9:04pm** — <https://steamcommunity.com/sharedfiles/filedetails/?id=3388721641>, fetched
  2026-09-10 17:46 into
  [`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json).
- **Build examined (date + version folder used):** **`42.13/`**, the newer of **two** version
  folders (`42.13`, `42`) and the one `mod_lint.media_root` resolves — confirmed on the run, from
  the loader's own output (§ Architecture, M1). Beside them the item ships a **`common/` that is
  the bigger tree** (14 files / 74 462 B against `42.13/`'s 42 604 B) and a `42/` that holds
  **two PNGs and nothing else** — no `media/`, no `mod.info`. Whole item: **19 files /
  129 161 B**, CRLF throughout, four files with no final newline. File mtimes come in **two**
  stamps — 16 files at `2026-08-12 00:02` (the Steam download) and **three at
  `2026-09-07 21:54`**: `common/mod.info`, `common/media/lua/client/AutoCook_RISCookMenuInsertion.lua`
  and `42.13/media/lua/client/AutoCook.lua`, i.e. the v1.6 update itself, which the item-directory
  stamp (`workshop_item_mtime 2026-08-12T00:03:05`) does not show. Inventory figures below are
  [`data/mod-inventory.json`](../../../data/mod-inventory.json), swept 2026-09-10 17:47:
  `layout 42.13`, `version_dirs ["42.13","42"]`, `mod_info_at common/mod.info`,
  `media_at ["42.13/media","common/media"]`, `stats {lua_client: 3}`, `lua_kb 41`,
  `bytes 129 161`, **`script_item_blocks 0`**, `script_modules []`, `script_nutrition_keys {}`,
  `sandbox_options false`, `top_events []`, and the four signals `mod_data 9`, `require_line 5`,
  `food_nutrition 4`, `global_write_vanilla 21`.
- **Author · dependencies · license/permissions posture:** author **`Tchernobill`**
  (`common/mod.info:4`), `modversion=1.6` (`:5`), `versionMin=42.0.0` (`:6`). The file has
  **9 keys and no `require=`, `incompatible=`, `loadModAfter=` or `loadModBefore=`** — empty
  dependency list, nothing to install beside it, and no declared load-order constraint of any
  kind. No licence or readme file ships in the item and the fetched Workshop record carries no
  licence field, so the posture is default Steam Workshop terms: **read it, do not vendor it.**
  Nothing here is copied into our mod; only patterns are taken.

Grades: **C** = code/script/jar reading (each carries a `path:line` or a jar dump), **M** =
measured on the run named in the cell, **W** = Workshop page or wiki mirror. **Mod-relative paths
are tree-qualified** — `42.13/…` and `common/…` name *different physical files*, and in this
subject that difference is the whole point; they are relative to
`3388721641/mods/AutoCook/`. Vanilla Lua and scripts are relative to the game install; vanilla
Java is cited as `Class.method @offset L<source line>` from the 42.20.4 jar.

## What it does (player-facing)

1. **Right-click a cooking base item** — a bowl, pot, pan — and the context menu gains
   **"Auto Cook &lt;recipe&gt;"** for every evolved recipe that item can start
   (`common/media/lua/client/AutoCook_RISCookMenuInsertion.lua:86-87`).
2. **Picking it queues the whole meal.** For each ingredient the mod chooses one item, walks it
   into your inventory if it is elsewhere, runs the **real vanilla** `ISAddItemInRecipe` timed
   action, then queues a one-tick `ISContinue` that calls back and picks the next
   (`42.13/media/lua/client/AutoCook.lua:96-179`). Simulated cooking time is unchanged; only the
   clicking is.
3. **Which ingredient it picks is a "diet"** — five cooking modes (freshness, leftovers, weight
   loss, weight gain, nutritionist) chosen from a **new "Cook" tab in the character info window**
   (`common/media/lua/client/AutoCook_Diets.lua:21-27`;
   `42.13/media/lua/client/ISCharacterCook.lua:398`).
4. **The same tab holds six settings** — duplicate-ingredient cap, food variety, use-rotten,
   complete-started-recipes, spice count and "smart spices"
   (`42.13/media/lua/client/ISCharacterCook.lua:25,26,27,30,34,35`), persisted per character in
   player modData. A seventh, `AutoCraftIngredients`, is commented out at `:28`.
5. **Smart spices and the nutritionist mode read the character's live `Nutrition`** — weight, the
   weight-direction flags, lipids/carbs/proteins — to decide whether to add a spice and which food
   to prefer (`42.13/media/lua/client/AutoCook.lua:211-227`, `:328-351`;
   `common/media/lua/client/AutoCook_Diets.lua:134-145`). Every one of those is a
   **server-owned** value read off the client's mirror.

## Architecture

### The census — two media trees, and the mod is only whole across both

| Tree | Files | `.lua` lines | Bytes | What | Ev |
|---|---:|---:|---:|---|---|
| `42.13/media/lua/client/` | 3 `.lua` | **917** (395 + 124 + 398) | 42 604 | `AutoCook.lua`, `AutoCook_AutoCraftRecipes.lua`, `ISCharacterCook.lua` | C |
| `common/media/lua/client/` | 7 `.lua` | **1 238** (362 + 124 + 145 + 117 + 398 + 50 + 42) | 56 469 | the same three **plus** `AutoCook_Diets.lua`, `AutoCook_RISCookMenuInsertion.lua`, `ISCharacterInfoWindow_AddTab.lua`, `ISContinue.lua` | C |
| `common/media/lua/shared/Translate/EN/` | 4 | 81 | 5 588 | `ContextMenu.json` + `UI.json` (live) and `ContextMenu_EN.txt` + `UI_EN.txt` (B41, never parsed) | C |
| `common/` root | `mod.info`, 2 PNG | — | 12 405 | — | C |
| `42/` | 2 PNG | — | 12 095 | icon + poster only; **no `media/`, no `mod.info`** | C |

**Ten `.lua` files, 2 155 lines, read end to end 2026-09-10.** No `media/scripts` in any tree, no
`server/` or `shared/` Lua, no `sandbox-options.txt`. The three files that exist in **both** trees
were read in full in the `42.13/` copy and their `common/` copies covered by an exhaustive `diff`.

**The inventory's own numbers cover the live folder only, and for this subject that is most of the
mod.** `signals` / `stats` / `lua_kb` are computed over `mod_lint.media_root`'s folder
(`tools/mod_inventory.py` `resolve()`), so `stats {lua_client: 3}` and `lua_kb 41` hide **7 of 10
Lua files, 1 238 of 2 155 lines, the mod's only event registration, its only vanilla patch and its
entire translation set** — all of which live in `common/`. `bytes 129 161` uses a different
denominator (the whole item) and agrees with the folder. **`media_at` is the flag**: two entries
means the row's other numbers are a partial view (C, 2026-09-10).

### The merge rule — the headline, and it is now measured

The catalog carried this as **W** from the wiki mirror — *"1. Common folder. 2. Closest versioning
folder to the game version (overwrites common files which are present in it)"*
([Mod_structure mirror](../../../references/wiki-mirrors/mod-structure.md), page version 42.20.0),
recorded as [`../nutrition-mods.md`](../nutrition-mods.md) § Open questions 1. AutoCook is the
corpus's sharpest test of it because **the direction is load-bearing**: the three files the
version folder shadows are exactly the three the author ported to B42, and the `common/` copies
still call two members that **no longer exist on 42.20.4** (§ Pitfalls, D1/D2). Under the wiki
rule the mod works; under the inverse it raises at file load and at `prerender`.

**The mechanism, from the 42.20.4 jar (C).** Four call sites, and the fourth is what makes the
rule observable:

1. `ZomboidFileSystem.loadMod` (`@0-@431 L739-L778`) runs **two passes in this order** —
   pass A over `mod.getCommonDir()` (`@73-@85 L750`) with an **unconditional**
   `activeFileMap.put(rel, abs)` at `@205-@216 **L758**`, then pass B, the identical loop over
   `mod.getVersionDir()` (`@240-@424 L763-L776`), with the same unconditional `put` at
   `@396-@407 **L773**`. `HashMap.put` overwrites, so the version dir's file wins a same-relative-
   path collision and `common/` supplies everything the version dir does not ship. Before each
   overwriting `put` the loader prints **`mod "<id>" overrides <rel>`** — constant #1670,
   `'mod "\x01" overrides \x01'` — through `DebugType.Mod.println`, gated on the key already
   existing and the path not ending `mod.info` / `poster.png` (`@133-@181 L754-L755`,
   `@324-@372 L769-L770`). **One line per shadowed file, with the path appended.**
2. `ZomboidFileSystem.getAbsolutePath(rel)` is `activeFileMap.get(rel.toLowerCase())` and nothing
   else (`@0-@19 L483-L484`) — the map *is* the resolution. It is pre-seeded with vanilla's whole
   **media** tree before any mod loads (`init` sets `workdir = new File(base, "media")` at
   `@16-@36 L151` and `searchFolders(workdir)` at `@165-@173 L163`), which is why a mod file at a
   vanilla relative path shadows vanilla's and prints the line. Scope note: only paths under
   `media/` are pre-seeded, so only those can be shadowed — every relative path AutoCook ships is
   under `media/`.
3. `LuaManager.LoadDirBase(subdir)` (`@0-@540 L1141-L1232`) builds the execution list vanilla-first
   (`PZArrayUtil.addAll(vanillaList, modList)`, `@371-@373`), then **per mod** `commonDir` then
   `versionDir` (`@136-@229 L1169-L1181`, `@239-@332 L1184-L1196`), each mod's block sorted
   case-insensitively (`@342-@348 L1198`), and walks the list through a `HashSet`
   (`@386-@445 L1208-L1214`): **a relative path already seen is skipped**, and the survivor is
   resolved with `getAbsolutePath` (`@446-@453 L1216`) and run (`@480-@485 L1222`). A doubled
   relative path therefore executes **once, from the file `activeFileMap` holds**.
4. `Translator.tryFillMapFromMods` (`@0-@97 L376-L391`) walks the same pair in the same order —
   `getCommonDir()` (`@41-@63 L382-L384`) then `getVersionDir()` (`@66-@88 L386-L388`) — but
   through `tryFillMapFromFile`, which formats `%s/media/lua/shared/Translate/%s/%s.json` itself
   (`@4-@29 L357-L358`) and **merges into a shared map** (`@107-@118 L364`). Translations do
   **not** shadow: vanilla's keys survive and the mod's are added.

**The session read the outcome four ways, and a fifth fell out of the census. All five agree:
version-wins.**

| # | Reading | What it answers | Outcome | Ev |
|---|---|---|---|---|
| **M1** | the loader's own `overrides` lines, server log lines **95–99** | which relative paths the version dir took from `common/`, and which `common/` took from vanilla | **exactly 5**, in order: `media/lua/shared/translate/en/contextmenu.json`, `…/ui.json` (pass A, over **vanilla**), then `media/lua/client/autocook.lua`, `…/autocook_autocraftrecipes.lua`, `…/ischaractercook.lua` (pass B, over **`common/`**). **No `.png` tail ⇒ `getVersionDir()` resolved to `42.13/`**, not `42/` | M — `td3-20260911-001948`, `M1_overrides.server_log` |
| **M2** | `witness.moddata player:admin *` on the **client** at `session_ready + 1.044 s` | did `common/` run at all | `keyCount 6`, `AutoCook:table` present with no user input ⇒ `addCharacterPageTab` ran, and that function is defined **only** in `common/…/ISCharacterInfoWindow_AddTab.lua:2`. **`common/` ran and the require chain completed — this names NEITHER direction** | M — `snapshots[0].client.census_player` |
| **M3** | `text.get UI_AutoCookMode` + two vanilla controls | did the Translator read `common/…/UI.json`, and did the mod's same-named JSONs displace vanilla's | `"Cooking diet: "`, `miss false`, byte-exact including the trailing space; `ContextMenu_Destroy` → `Destroy` and `UI_Yes` → `Yes` both intact. **Consistent with version-wins and non-discriminating** — both JSONs exist only in `common/` | M — `M3_translations` |
| **M4** | `lua.global` × 11 names × 2 sides | **which physical `AutoCook.lua` executed** | `AutoCook.acceptIngredient` and `AutoCook.baseAcceptsSpice` both **resolved as functions on the client** — and they are defined **only** by `42.13/…/AutoCook.lua:245` and `:234`. `AutoCook.selectPreferedFood` (from the common-only file `common/…/AutoCook_Diets.lua:21`) resolved too, and `ISContinue` (`common/…/ISContinue.lua:4`) rules out "`common/` never ran". **Version-wins, unambiguously** | M — `M4_globals.client` |
| **M4b** | `_G.AutoCook` `keyCount` | an arithmetic cross-check nobody planned | **49** = 23 file-scope scalars (`AutoCook.lua:6-28`, identical in both copies) + 15 functions of `42.13/…/AutoCook.lua` + 4 of `42.13/…/AutoCook_AutoCraftRecipes.lua` + 7 of `common/…/AutoCook_Diets.lua`. **A common-wins state reads 47** (its copy defines 13, not 15) | M — `summary.M4_autocook_keyCount_client` |

**The negative that would have shown the inverse is also measured, and it is bounded.** A
common-wins state would have executed `common/…/AutoCook.lua:39`'s `player:HasTrait("Nutritionist")`
— a member removed in 42.20.4 — and Kahlua's "tried to call nil" is uncatchable
(`PZTestKit_Core.lua:118-122`, run `exp01-20260909-235420`). The console grep
`tried to call nil|HasTrait|getTypeString` returned **0** on the client and **0** on the server
(M — `nilcall_lines`). **What that proves is exactly one line's worth:** `common/…/AutoCook.lua:39`
did not run, and it is load-bearing because the line *before* it (`:38`, the modData write)
demonstrably did execute on this fresh character. It does **not** cover
`common/…/ISCharacterCook.lua:50` or `:221` — both sit inside `prerender`, which never runs
unless the Cook tab is opened, and nothing on the bus opens it. Treat the zero as a reading about
`AutoCook.lua`, not about the whole `common/` tree.

**The rule, graded honestly.** The **outcome is M** — one session on 42.20.4, with two independent
halves: M1 reads the loader's *map* and M4 (+M4b) reads the resulting *Lua state*, and neither
depends on the other. The **mechanism is C**, from the four jar sites above. M2 is "neither
direction" and M3 is non-discriminating; quoting either as a merge-rule reading overstates it.
**Bound the statement to its subject**: this measures a mod whose `getVersionDir()` resolves to a
tree that **ships colliding files**. Nothing here measures a mod whose version dir is absent, is
empty, or ships only files `common/` does not have.

> **The rule, as a sentence we can reuse:** for a mod shipping `common/` beside a version folder,
> the **version folder's file wins a same-relative-path collision**, `common/` supplies everything
> the version folder does not ship, and both end up in **one** Lua state — with translations the
> exception, because the `Translator` merges rather than resolving through `activeFileMap`.
> **M** for the outcome (`td3-20260911-001948`), **C** for the mechanism.

**What this closes.** [`../nutrition-mods.md`](../nutrition-mods.md) § Open questions 1 (the merge
rule itself) and § Open questions 3 (*is `MoodleFramework` whole on 42.20.4?* — **yes**, by the
same four call sites: `3396446795/mods/MoodleFramework` ships `MF_ISMoodle.lua` in `42.0/`,
`42.13/`, `42.20/` and `common/` but `MF_Config.lua` in `42.0/` and `common/` only; on 42.20.4
pass B overwrites only `mf_ismoodle.lua`, and `mf_config.lua`, having no version-dir counterpart,
survives and executes — **C**, from the rule, not a second measurement). The engine-facing
statement also lands in [`../../modding/README.md`](../../modding/README.md) § Hard-won platform
facts and in `tools/mod_lint.py`'s `media_root` docstring.

**The author states the rule too, from inside the subject.**
`common/…/AutoCook_RISCookMenuInsertion.lua:62-66` branches on
`if autoCook.acceptIngredient then … else itemCount = items:size()`, with a comment that older
version folders do not ship the acceptance test. `acceptIngredient` exists **only** in
`42.13/…/AutoCook.lua:245`. That file is written on the assumption that a `common/` file runs
beside whichever version folder won — **W-grade corroboration** of the reading above, from the mod
itself.

### Entry points — three, all client, and the two that matter live in `common/`

| # | Entry point | Where | Fires | Ev |
|---|---|---|---|---|
| 1 | `Events.OnPreFillInventoryObjectContextMenu.Add(onAddAutoCookContextOption)` | **`common/…/AutoCook_RISCookMenuInsertion.lua:117`** | on every inventory right-click; vanilla triggers it at `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:374` with `(playerNum, context, items)` | C |
| 2 | `addCharacterPageTab("Cook", ISCharacterCook)` | called at `42.13/…/ISCharacterCook.lua:398`; the function itself is **`common/…/ISCharacterInfoWindow_AddTab.lua:2`** | at file load; wraps three `ISCharacterInfoWindow` methods | C |
| 3 | `if isDebugEnabled() then AutoCook:init(getPlayer()) end` | `42.13/…/AutoCook.lua:393-395` | **debug builds only** — dead on a normal client | C |

**There is no `Events.*.Add` in the live `42.13/` folder at all** — the inventory's
`top_events: []` is right, and it is right *because the registration is in `common/`*. That is the
structural shape worth naming: **a `common/`-hosted entry point with a version-folder
implementation**. It is a legitimate pattern (it is how this author avoids re-shipping 1 238 lines
per build), and it has a cost for anyone reading the corpus from the inventory: the row for a mod
like this looks inert.

**The chain that runs at spawn, with no user input** (this is what made the mod measurable at all):

```
ISPlayerData.createPlayerData(id)                media/lua/client/ISUI/PlayerData/ISPlayerData.lua:168
  ISPlayerDataObject:new(id)                     …/ISPlayerDataObject.lua:93-95
    ISCharacterInfoWindow:new() :initialise() :addToUIManager()
      ISUIElement:addToUIManager -> :instantiate()          …/ISUI/ISUIElement.lua:1365-1368
        ISUIElement:instantiate  -> self:createChildren()   ISUIElement.lua:1007
          ISCharacterInfoWindow:createChildren   <- WRAPPED, common/…/ISCharacterInfoWindow_AddTab.lua:7
            pageType:new(...) ; :initialise()               …_AddTab.lua:10-11
            self.panel:addView(getText("UI_Cook"), view)    …_AddTab.lua:13
              ISTabPanel:addView -> self:addChild(view)     …/ISUI/ISTabPanel.lua:494
                ISUIElement:addChild -> otherElement:instantiate()   ISUIElement.lua:1455-1457
                  ISCharacterCook:createChildren            42.13/…/ISCharacterCook.lua:15
                    AutoCook.init(self, self.char)          42.13/…/ISCharacterCook.lua:17
                      player:getModData().AutoCook = {}     42.13/…/AutoCook.lua:38
```

So `player:getModData().AutoCook` exists **the moment the character info window is built**, not
when the tab is opened — measured at `session_ready + 1.044 s` (M2). `ISCharacterCook:initialise`
(`:10-13`) does *not* call `createChildren`; the instantiate inside `addChild` does.

### Data model — one nested modData key, and on a fresh character it is empty

| Store | Key | Written by | Transmitted? | Ev |
|---|---|---|---|---|
| `IsoPlayer:getModData()` | **`AutoCook`** — a nested table, created **empty** | `42.13/…/AutoCook.lua:38` | **never by this mod** (0 `transmitModData`) | C |
| … `.CookMode` | integer 1-5 | `42.13/…/ISCharacterCook.lua:238` (`onComboSelectCookMode`) | never | C |
| … `.MaxDuplicate`, `.MaxSpices` | integer | `…/ISCharacterCook.lua:339` (`onNumberInput`, only when `button ~= nil`) | never | C |
| … `.PrioritizeVariety`, `.UseRotten`, `.CompleteExistingMeal`, `.SmartSpices` | boolean | `…/ISCharacterCook.lua:258` (`onTickChange`) | never | C |
| … `.AutoCraftIngredients` | forced `false` **on every load after the first** — `42.13/…/AutoCook.lua:45` sits in `init`'s **`else`** branch, the "load from modData" path taken only when the key already exists | `42.13/…/AutoCook.lua:45` | never | C, with the **M** correction below |
| `_G.AutoCook` | 23 file-scope scalars + the functions of three files | file scope, `42.13/…/AutoCook.lua:6-28` and the definitions in both trees | n/a (a Lua global) | **M** — `keyCount 49`, `td3-20260911-001948` |
| sandbox options | **none** — no `sandbox-options.txt`, no `SandboxVars.` reference in either tree | — | — | C |
| item / recipe scripts | **none** — `script_item_blocks: 0`, no `media/scripts` in any tree | — | — | C |

**The measured correction.** On a fresh character the modData table is **`{}`** and **all eight
dotted leaves are missing** — `CookMode`, `MaxSpices`, `UseRotten`, `SmartSpices`,
`PrioritizeVariety`, `MaxDuplicate`, `CompleteExistingMeal`, `AutoCraftIngredients` land in
`missing` at **every** snapshot on the client, and on the server from the transmit onward
(M — `snapshots[].{client,server}.autocook_keys`). The real values live **only on the Lua
global**: `AutoCook.CookMode` read `1`, `AutoCook.MaxSpices` read `-1`, `AutoCook.Verbose` read
`false` through `lua.global` (M — `M4_globals.client`). `CookMode 1` rather than `5` also says the
fixture character is **not** a Nutritionist. So a cold read that calls `:45` "forced `false` on
every load" is wrong about the first load, which is the only one this mod ever performs on a new
character.

`AutoCook:init` (`42.13/…/AutoCook.lua:30-54`) is the only reader: on first run it creates the
empty table and, for a Nutritionist, sets `AutoCook.CookMode = 5` **on the global only, never into
modData** (`:38-41`); on later runs it copies every modData key onto the global (`:46-49`). The
settings are therefore **per client, not per character** (§ Pitfalls, D6).

### Client / server / shared split — "no server presence" is now measured

**Everything is client.** Across both trees: **10 client `.lua`, 0 server, 0 shared** (the only
`shared/` content is the four translation files, which are data). There is **no
`sendClientCommand`, no `sendServerCommand`, no `OnClientCommand`, no `OnServerCommand`, no
`transmitModData`, no `sendItemStats`** anywhere — the sweep returns zero for all seven (C).

The run turned that from an inference into a reading: **every** AutoCook global is absent
server-side. `ISContinue`, `addCharacterPageTab`, `ISCharacterCook` and `AutoCook` all answered
`resolved: false` with `failedAt` naming the **first** segment, while the control `TK.version`
answered `1` on **both** sides in the same batch — so the walk itself is proven working on the
server and the absences are the mod's, not the command's
(M — `M4_globals.server`, `td3-20260911-001948`).

### Version history — what `42.13/` actually changed

The three shadowed files, diffed in full (`common` → `42.13`), C 2026-09-10:

* **`AutoCook.lua`** (+33 lines): the B42 trait API at `:39`; a new `usedItemId` recorded in
  `addToReturnContainer` (`:185`) and used to re-resolve an item by id in
  `returnItemsToOriginalContainer` (`:195-207`), because the craft replaces the Java instance while
  the id survives; two new functions `AutoCook.baseAcceptsSpice` (`:234-238`) and
  `AutoCook:acceptIngredient` (`:245-256`); and `chooseItem` rewritten to call the latter
  (`:269-282`) instead of inlining the five filters (`common`'s `:229-246`).
* **`AutoCook_AutoCraftRecipes.lua`** (1 line): `getTypeString() == 'Food'` →
  `isItemType(ItemType.Food)` at `:39`.
* **`ISCharacterCook.lua`** (3 lines): the trait API at `:50` and `:221`, plus a **bug fix** at
  `:245` — `common` removes `self[settingId]` where `42.13` removes `self[viewID]`.

`42/` contributes no Lua. So the history is: `common/` is the B41-era shared baseline, `42.13/` is
the B42 delta, and the delta is only three files **because the merge rule lets the rest be
shared** — which is exactly why `42.13/…/AutoCook.lua` being the copy that ran is the finding and
not a formality.

## MP handling

**Where authority lives: entirely on the server, and the mod does not participate.** AutoCook has
**no networking of its own** — 0 command-bus sites, 0 `sendItemStats`, 0 `transmitModData`, and no
server Lua for any of them to run in. Its whole MP contract is **reading** two server-owned stores
from the client's mirror (`Nutrition`, and inventory-item fields) and **queueing vanilla timed
actions** that do their own syncing.

Everything below is one live dedicated server plus one real client, same character (`getUsername`
`admin` and four more `IsoPlayer` getters agreeing on both sides at every snapshot,
`field_count_ok true` on all eight side-readings), run **`td3-20260911-001948`** — 179.4 s wall,
`session_ready` at 86.77 s, `server_error_count 0`, `client_lua_error false`, no `error` key, 0
re-asks. Walls are seconds after `session_ready` unless stated; **the client half of every pair
was read first.**

| # | Field / key measured | Side(s) | Reading | Ev |
|---|---|---|---|---|
| 1 | `player:getModData().AutoCook` at join | client | **present** at **+1.044 s**, `keyCount 6` (`AutoCook`, `hotbar`, and the four vanilla fitness/strength keys), `beyondVanilla ["AutoCook"]` | M — `td3-20260911-001948`, `snapshots[0].client.census_player` |
| 2 | the same key, server-side, before any transmit | server | **absent** — the server holds **no `AutoCook` key at all**: it is in `missing` at both `baseline_join` (+3.073 s, `keyCount 0`) and `baseline_late` (+42.102 s, `keyCount 4`) | M — `snapshots[0..1].server.autocook_keys` |
| 3 | the eight `AutoCook.*` leaves | client | **all eight `missing` at every snapshot**; the table itself renders `{}` — a fresh character's settings live only on the Lua global | M — `snapshots[].client.autocook_keys` |
| 4 | the server's own player modData, timed | server | **`keyCount 0` at +3.073 s**, **4 at +42.102 s** — the four vanilla fitness/strength keys are written **server-side lazily**, reproducing pass 2 exactly. A server `keyCount` is only a reading beside its wall offset | M — `baseline_timing` |
| 5 | `moddata.set AutoCookProbe 7` on the client, then a census pair | both | **did not cross.** The server census opened **0.51 s after the ack** and closed 1.77 s after it, still at `keyCount 4` — a client modData write reaches the server only after `transmitModData()` | M — `phase2[0]`, `steps[plant_client]` |
| 6 | `moddata.transmit` | both | **`AutoCookProbe` and the nested `AutoCook` table both crossed**, and the server census became **exactly** the client's, `hotbar` included: `probe_key_crossed true`, `autocook_crossed true`, `server_census_equals_client true`. The server census at **transmit + 2.04 s** already showed all 7 keys | M — `transmit_reading`, `t_action` |
| 7 | `AutoCook` on the **server** after the transmit | server | `{}` — an empty table, with the same eight leaves `missing`. The wipe-and-replace carried the nested table's *shape*, and the shape is empty | M — `snapshots[2..3].server.autocook_keys` |
| 8 | `text.get UI_AutoCookMode` and two vanilla controls | client | `"Cooking diet: "` (`miss false`, trailing space intact); `ContextMenu_Destroy` → `Destroy`; `UI_Yes` → `Yes`. The mod's same-named JSONs do **not** cost vanilla its strings | M — `M3_translations` |
| 9 | every AutoCook Lua global | server | **absent**, with `TK.version` → `1` on both sides as the control | M — `M4_globals.server` |
| 10 | `incWeight` / `incWeightLot` / `decWeight` | both | **agree (`false`) at all four snapshots — under the trivial arm only.** See "the flags" below | M — `snapshots[].{client,server}.nutrition` |
| 11 | a server-pinned `Base.Steak` at `heat 1.2`, read twice 12.54 s apart | both | **client bit-frozen, server decayed 1.2 → 1.0.** See "the carrier" below | M — `carrier` |

### The transmit, and what it means for a mod that never transmits

```
+48.0 s  client  moddata.set AutoCookProbe 7   -> "set AutoCookProbe"  (0.255 s)
+48.2 s  ── census pair: client 7 keys, server 4
+50.1 s  client  moddata.transmit              -> "transmitted"        (0.257 s)   <- t_action
```

Three things at once, and only the third is new:

1. **The client's own write did not cross on its own** (row 5) — corroborating spike S6 and
   [`../../modding/patterns.md`](../../modding/patterns.md)'s modData row.
2. **Pass 2's wipe-and-replace reading gets its second subject.** The server census became exactly
   the client's and the **nested** `AutoCook` table crossed whole (the server's dotted read answers
   `AutoCook: {}` where it answered `missing` before). This is **corroboration**, not a discovery;
   pass 2's `n = 1` is now `n = 2`. This session planted no *server-only* key, so it does not
   re-measure the **wipe** half — that stays pass 2's reading.
3. **The subject-specific fact, and it is the MP headline for this mod.** AutoCook has **9**
   `getModData()` sites per tree and **0** `transmitModData`, so it never causes the crossing
   itself — but its "client-only" settings are private only until **something else** on that
   client transmits. **One `transmitModData()` by any other mod pushes the whole `AutoCook` table
   to the server.** Here it was our probe; on a real server it is a simpleStatus bar drag
   ([`simplestatus.md`](simplestatus.md) § MP handling, seven such call sites).

**Read the tag names, not the clock.** `t+3s` is a nominal name: the tag actually landed at
**transmit + 7.58 s**, because the `t0` snapshot itself took 7.58 s to walk both sides. The
server census inside `t0` sat at **transmit + 2.04 s** and already showed all seven keys, so the
crossing is bounded at ≤ 2.04 s and nothing here measures it more tightly. Cross-side read skew at
`t+3s` was **1.78 s** (client bracket 144.525→144.781, server 146.309→146.567); nothing in a
modData census decays, so that gap is pure latency and both sides had already converged.

### The carrier — pass 1's freeze and pass 2's moving copy, reconciled

Pass 1 measured a client item copy **frozen** across 11.1 s while the server's decayed; pass 2
measured a client copy that **moved**, bit-identically to the server's. The reconciling hypothesis
was the **1.6 cooking gate**, and the probe it named was one pin *below* it. This session ran that
probe, on a carried follow-up rather than on anything AutoCook owns.

RCON `additem "admin" "Base.Steak" 1` → visible on the client at the first 2.5 s poll
(`admin/Base.Steak #829047872`) → server `item.set admin Base.Steak heat 1.2` (ack
`heat 1.2000000476837158`, `cookingTime 0`, `cooked false`, `sync "sendItemStats(item)"`) → the
same three getters on both sides, twice, **12.54 s apart**:

| side | read 1 (wall) | `getHeat` | `getCookingTime` | read 2 (wall) | `getHeat` | `getCookingTime` | moved? | Ev |
|---|---:|---|---|---:|---|---|---|---|
| **client** | 154.154 | `1.2000000476837158` | `0` | 166.695 | `1.2000000476837158` | `0` | **no** | M — `td3-20260911-001948`, `carrier.client_read_1` / `_2` |
| **server** | 154.415 | `1.2000000476837158` | `0` | 166.955 | **`1`** | `0` | **yes** (`getHeat`) | M — `carrier.server_read_1` / `_2` |

**Reading: the carrier is `Food.update`'s cooking-branch `sendItemStats`.** Pass 2 pinned the same
item at `heat 2.0`, **above** the gate, and its client copy moved in lock step; this session pinned
**1.2**, **below** it, and the client copy is frozen to the bit while the server's decays to the
1.0 floor. Mechanism (C, jar): `Food.update @86-@103 L377-L379` fires
`GameServer.sendItemStats(this)` once per **game minute** while the cooking branch is live, gated
at `@49-@71 L372-L373` on `isCookable && !isFrozen() && heat > 1.6f`.
**Graded M per arm** — `n = 1` in each arm, across two sessions — **mechanism C.**

**What it refines, and what it does not settle.** The below-gate arm shows the client copy did not
tick **at all**. `updateTemperature` runs unconditionally inside `Food.update`, so the honest
statement is "**`Food.update` did not advance the client's held copy in this window**" — which
**refines** [`../../modding/patterns.md`](../../modding/patterns.md)'s "a client copy *can* tick"
clause rather than confirming it. Still open: one item, one 12.54 s window, one fixture; frozen and
non-cookable items are untested, and so is every other push path. **The operative rule is
unchanged: a client-side reader of a live item field may be reading a push, not a simulation, and
must not assume either.**

Two controls inside the same probe:

* **The pin's own push did arrive.** `item.set` fires `sendItemStats` on its way out and both
  sides read the identical `1.2000000476837158` at read 1 — so the freeze is not "the client never
  saw the value".
* **The item-scope modData census** (the `{customName, Tooltip}` exclusion set, applied here and
  nowhere else): client `keyCount 1` — `customName` — and server `keyCount 0`, `beyondVanilla`
  empty on both. That reproduces slice 08's finding that `InventoryItem.setCustomName` writes
  `customName` from `InventoryItem.load`: a deserialization side effect on the side that
  deserialized, not mod data.
* `getContainer` is compared **within** each side only (client `parent:IsoPlayer{ … ID:5 }`,
  server `ID:1`): present and stable across the window on both. `ItemContainer.toString()` ends in
  a per-JVM identity hash, so the full strings must never be compared across sides.

### The flags AutoCook actually gates on — agreement under the trivial arm, unsettled

`AutoCook:allowSpice` reads `getNutrition():getWeight()`, `:isIncWeight()` and `:isDecWeight()` at
`42.13/…/AutoCook.lua:214-219`, and those two flags are **not** in `PlayerStatsPacket`
(`Nutrition.save` writes the five macros only). The static read called that a measurable desync
risk. **It is neither confirmed nor falsified here.** All three flags read `false` on **both**
sides at all four snapshots — but the character sat in `Nutrition.updateWeight`'s **none** arm the
whole session: weight 80 ⇒ gain threshold `1000 + (80−80)·40 = 1000`, loss threshold
`min(0, (80−70)·30) = 0`, and calories ran 798.45 → 782.90, strictly between them. **Both sides
answer `false` in that arm whether or not the client recomputes anything**, so the agreement is
trivial. Settling it needs a session that drives calories above 1000 or below 0 and re-reads both
sides — **a slice-12 item**, recorded here rather than claimed
(M for the readings — `snapshots[].{client,server}.nutrition`; the *inference* stays open).

### What else it reads that the server owns

| Site | Reads | Owner | Ev |
|---|---|---|---|
| `42.13/…/AutoCook.lua:214-219` | `getWeight`, `isIncWeight`, `isDecWeight` — the smart-spice gate | **server** | C |
| `42.13/…/AutoCook.lua:329-346` | `getWeight` / `getLipids` / `getCarbohydrates` / `getProteins` — the nutritionist filter | **server** | C |
| `42.13/…/ISCharacterCook.lua:71-101` | the same five, for the tab's warnings | **server** | C |
| `common/…/AutoCook_Diets.lua:83,136-141` | `getProteins`, `getWeight` — the diet comparators | **server** | C |
| `common/…/AutoCook_Diets.lua:5-11,112-118` | `getOffAge`, `getOffAgeMax`, `getAge` — the freshness diet | **server, and never synced** (slice 09) | C |
| `common/…/AutoCook_Diets.lua:32-35,57-60` | `getCalories`, `getHungChange` — the leftovers diet | server; `hungChange` is packet-carried, the derived thirst getter is not faithful | C |
| `42.13/…/AutoCook_AutoCraftRecipes.lua:39` | `item:getHungerChange() < 0` on a **script** item | script, not instance — identical on both sides for free | C |

So **every decision this mod takes is taken on the client, from the client's mirror of
server-authoritative state**. `Nutrition` is pushed at 1 Hz and at eat time, so the macro reads are
right and late by under a second (pass 2 measured exactly that). The **item** reads are the
exposed ones: `offAge` / `offAgeMax` never cross (slice 09, measured), and the carrier probe above
says a held item's live fields move on the client only while something is pushing them. The
freshness and leftovers diets therefore rank ingredients on values that, on a dedicated server, may
be the last pushed ones rather than live ones — **an inference under C**, sharpened but not settled
by this session.

## Techniques worth stealing

- **Split a mod across `common/` + a version folder, and put the parts that do not change in
  `common/`.** This mod's B42 port is **three files and ~40 lines**; the other seven files and
  1 238 lines are shared unchanged across every build it supports. The merge rule that makes it
  work is now measured (§ Architecture), so this is a technique we can rely on rather than copy on
  faith. **The dependency to write down:** it works because the version folder's copy wins a
  same-path collision — which means the `common/` copy of any shadowed file is *dead code on this
  build* and can rot silently (§ Pitfalls 1).
- **A `common/`-hosted entry point with a version-folder implementation**
  (`common/…/AutoCook_RISCookMenuInsertion.lua:117` registering an event whose handlers call into
  `42.13/…/AutoCook.lua`). One registration, one per-build implementation, no duplicated event
  wiring.
- **Queue the game's own timed action instead of reimplementing it.** `AutoCook:continue`
  (`42.13/…/AutoCook.lua:96-179`) builds a real `ISAddItemInRecipe` and then a one-tick
  `ISContinue` (`common/…/ISContinue.lua:4,28`) that calls back for the next ingredient. Cooking
  time, interruption and the crafting rules stay vanilla's; only the clicking is automated. **This
  is the shape our own automation should take if we ever add any** — it inherits every MP guarantee
  the vanilla action already has.
- **A prefixed translation key as a load probe.** Vanilla declares **zero** `UI_AutoCook*` or
  `ContextMenu_AutoCook_*` keys and a miss returns the key itself, so `text.get UI_AutoCookMode`
  is a tier-(a) `[[verify]]` row for a mod that ships no scripts and writes no server state
  (the same trick pass 2 used, second subject).
- **Save-and-call wrapping of a vanilla UI method**
  (`common/…/ISCharacterInfoWindow_AddTab.lua:6-14`) — it composes with any other tab-adding mod,
  which a wholesale replacement would not. Take the shape; **not** the non-idempotence
  (§ Pitfalls 3).
- **A generic tab registrar rather than a bespoke one.** `addCharacterPageTab(tabName, pageType)`
  keys on `UI_<tabName>` / `UI_<tabName>Panel` translations (`…_AddTab.lua:12-13`), so adding a
  page is one call. It is a de-facto public extension point — and unnamespaced, which is the
  pitfall (§ Pitfalls 4).

## Pitfalls / anti-patterns

1. **Dead copies in `common/` that call APIs the build removed.** `common/…/AutoCook.lua:39` and
   `common/…/ISCharacterCook.lua:50,221` call `HasTrait(String)`, and
   `common/…/AutoCook_AutoCraftRecipes.lua:39` calls `getTypeString()` — **both members are gone on
   42.20.4** (`IsoGameCharacter` exposes only `hasTrait(CharacterTrait)`; neither
   `zombie/inventory/InventoryItem` nor `zombie/scripting/objects/Item` has `getTypeString`). They
   are harmless **only because the version folder wins**, which this session measured and which no
   line of the mod asserts. A Kahlua nil call is uncatchable, so the failure mode is not a
   degraded feature, it is the whole require chain dying at file load. **Rule: a file in `common/`
   that a version folder shadows is unexecuted code on that build — treat it as unmaintained, and
   never let your live path depend on a merge direction you have not read out of the engine.**
   (C, with the bounded **M** negative in § Architecture: zero `HasTrait` raises proves `:39` did
   not run, not that the whole `common/` tree is inert.)
2. **A `nil` return used as both "reject" and "no opinion", where the caller reads it as neither.**
   `selectForStrength` can return `nil` (`common/…/AutoCook_Diets.lua:104`, deliberately, to avoid
   over-protein), and `chooseItem`'s `evoItem = self:selectPreferedFood(evoItem, item)`
   (`42.13/…/AutoCook.lua:304`) assigns it. The consequence is **not** that the candidate is
   skipped: on the next iteration of the same loop (`:301-308`) `:303`'s `if item and evoItem` is
   false, so control falls to `elseif item then evoItem = item` (`:305-306`), which **accepts the
   next candidate outright, with no comparison at all**. And if the nil survives the loop, `:288`'s
   `if not evoItem and …` still lets the following bucket be considered. **Rule: never encode a
   decision in `nil` when the caller's fallback path is "take whatever is next" — use an explicit
   sentinel, or return `(value, reason)`.** (C.)
3. **Three non-idempotent vanilla wrappers.** `common/…/ISCharacterInfoWindow_AddTab.lua` wraps
   `ISCharacterInfoWindow:createChildren` (`:6-14`), `:onTabTornOff` (`:16-23`) and `:SaveLayout`
   (`:29-48`), each capturing the *current* value into a local and replacing the method — so a
   **second** execution of the file, or a second `addCharacterPageTab("Cook", …)`, stacks a second
   wrapper: two Cook tabs, and `,Cook` appended twice to the saved layout. The only in-game route
   is a Lua reload, which is why this session was run under an explicit **no `lua.reload`**
   constraint. **Rule: wrap with a sentinel (`if target == MOD._wrapper then return end`), the way
   BeyondTen does — the cost is three lines and it makes reload-safety a property instead of a
   hope.** (C.)
4. **Unnamespaced globals at an extension point.** `addCharacterPageTab`, `ISContinue`,
   `ISCharacterCook` and `AutoCook` are four bare `_G` names (C: none collides with vanilla — all
   four are absent from the game's whole `media/lua`, grepped 2026-09-10 — and `keyCount 49` says
   they are real at runtime). `addCharacterPageTab` is the sharp one: any other mod defining a
   function of that name replaces this one wholesale, and `42.13/…/ISCharacterCook.lua:398` would
   then call the *other* mod's implementation. **Rule: namespace everything, and if you ship a
   registrar, ship it on your own table.**
5. **Settings that are global to the client, not to the character.** `init` copies every persisted
   modData key onto `_G.AutoCook` (`42.13/…/AutoCook.lua:46-49`), so a second character on the same
   client inherits the first one's diet until its own `init` runs. Worse, the Nutritionist default
   `CookMode = 5` is written to the global **only** (`:39-41`) and never into modData, so it is
   re-derived every load and is silently lost as a persisted value. **Rule: per-character state
   belongs in that character's modData in both directions — if you mirror it onto a global for
   speed, the global is a cache and the modData is the truth.** (C; measured corollary — a fresh
   character's `AutoCook` modData is **`{}`** while the live settings sit on the global, so a
   modData census of this mod reads as "installed, unconfigured" no matter what the player picked
   on a previous character.)
6. **Client-only state that is private only until a neighbour transmits.** The mod never calls
   `transmitModData`, and its settings still reached the server the first time something else on
   that client did (row 6). **Rule: "we never transmit" is not a privacy or a size guarantee for
   anything in player modData — the whole table is one other mod's UI event away from the wire.**
   (**M** — `td3-20260911-001948`, `transmit_reading`.)
7. **Fifty lines of dead crafting path behind a hard-disabled flag.** `AutoCraftIngredients` is
   `false` at `42.13/…/AutoCook.lua:24`, re-forced at `:45`, and its tick box is commented out at
   `ISCharacterCook.lua:28` — yet `:114-136` and `:149-154` remain, carrying the only uses of
   `AutoCook.AutoCraftItemCache` and `ISCraftAction`. Cosmetic, recorded because it reads like a
   live feature. Beside it: `AutoCook:allowSpice()` is declared with **no parameters**
   (`42.13/…/AutoCook.lua:211`) and called as `self:allowSpice(item)` (`:252`), so the argument is
   discarded; `AutoCook.init` is invoked with a **dot** on a method declared with a colon
   (`ISCharacterCook.lua:17`), harmless only because `init` never touches `self`; and
   `AutoCook_AutoCraftRecipes.lua:10`'s unparenthesised `and`/`or` means `isEnabled()` is never
   consulted on a non-debug client. (All C.)
8. **B41 leftovers that cost nothing and mislead.** `common/…/ContextMenu_EN.txt` and `UI_EN.txt`
   carry the same 38 strings as the JSON pair in B41 table syntax and are **never parsed on B42** —
   `Translator.tryFillMapFromFile` opens `.json` and nothing else. 5 KB of inert weight; the risk
   is a maintainer editing the wrong one. (C.)

## Compatibility notes

- **Load order is irrelevant to whether this mod works, and the mod declares no order at all.** No
  `require=`, no `loadModAfter=`/`loadModBefore=`, no `incompatible=` (`common/mod.info`, 9 keys).
  The one ordering-sensitive surface is *outbound*: two mods both defining `addCharacterPageTab`
  collide on the name and the later loader wins.
- **Patched API surface: three vanilla Lua methods**, all on `ISCharacterInfoWindow`
  (`media/lua/client/XpSystem/ISUI/ISCharacterInfoWindow.lua:103,182,291`). No Java surface, no
  script blocks, no events removed, and **zero** vanilla script-block redefinitions — the mod ships
  no `media/scripts` at all.
- **CleanUI (`3437629766`) — one half closed cold, the other half open with a named check.**
  1. **The wrappers are safe.** CleanUI ships **no** `client/XpSystem/ISUI/ISCharacterInfoWindow.lua`
     in any of its trees and the string `addCharacterPageTab` appears **nowhere** in the item (both
     zero hits, whole item, 2026-09-10). AutoCook's three wrappers have nothing to fight. **C,
     settled.**
  2. **What CleanUI does replace is AutoCook's only entry point** —
     `client/ISUI/ISInventoryPaneContextMenu.lua`, where vanilla's
     `triggerEvent("OnPreFillInventoryObjectContextMenu", …)` (vanilla `:374`) becomes
     `CleanUI_safeTriggerInventoryContextEvent(…)` at `:669`, a file-local
     `pcall(triggerEvent, …)` with a printed `[CleanUI] triggerEvent failed for <name>: <err>` on
     failure (`:25-33`). **The collision is version-dependent**: CleanUI ships seven trees
     (`42.12 42.13 42.14 42.15 42.16 42.19 common`) and that file exists in only **three** of them
     — `42.15/`, `42.16/`, `42.19/` (`find -iname`, whole item, 2026-09-11). On a 42.12–42.14
     resolution it does not arise at all.
  3. **The load-order question dissolves.** `activeFileMap.put` is unconditional and CleanUI is the
     only mod in our corpus at that relative path, so its copy wins over vanilla's in **both** mod
     orders; and `LoadDirBase` runs vanilla's block **first** (`PZArrayUtil.addAll(vanillaList,
     modList)` `@371-@373`), so the surviving list entry is vanilla's slot resolved through
     `getAbsolutePath` — CleanUI's bytes execute **before** every mod file, AutoCook's
     `Events.…Add` included. Mod order changes nothing about which file runs or whether the
     listener registers in time. Order would matter only if a **second** mod shipped the same path;
     none in our corpus does.
  4. **What stays open is the runtime half**: whether that `pcall` would actually contain a Kahlua
     nil call raised *inside* `triggerEvent`'s dispatch. Direct nil calls are **measured**
     non-recoverable by `pcall` (`PZTestKit_Core.lua:118-122`, run `exp01-20260909-235420`); the
     raised-inside-dispatch step is **C, inferred**. Two further consequences: with CleanUI
     resident a raising listener shows as `[CleanUI] triggerEvent failed …` rather than a raw Lua
     error, so any driver's nil-call regex must add it; and CleanUI's copy is a 42.19 **fork** of a
     vanilla file, so it silently reverts any vanilla `createMenu` change since — for every mod on
     that event, not just this one. **The check that settles it** (recorded, deliberately not run —
     this pass's fixture is PZTestKit + AutoCook only): a three-mod profile booted **twice** with
     the two mod orders, reading the `mod "CleanUI" overrides …isinventorypanecontextmenu.lua` tail
     in both, `lua.global CleanUI_FixingHelper CleanUIConfig addCharacterPageTab AutoCook
     AutoCook.acceptIngredient`, and the client console for both failure signatures (zero
     expected). **Slice-12/14 item.**
- **An explicit compatibility shim for a mod we do not have.**
  `common/…/AutoCook_RISCookMenuInsertion.lua:4-6` does
  `if ActiveMods.getById("currentGame"):isModActive("AuthenticZStudderFix") then
  require('ISUI/InventoryPaneContextMenuFix') end`. That `require` target does **not** exist in
  vanilla — it ships with that mod — so this is a **load-order-sensitive `require` inside a
  file-scope `if`**. The guard itself is sound (it is the same call vanilla makes at
  `media/lua/client/OptionScreens/MainScreen.lua:1007`) and the branch is dead in our corpus. (C.)
- **The Girth stack.** 0 command-bus sites against its 228, so no collision there (slice-08
  catalog, 2026-09-10).
- **The `mod-info-place` WARN is dated, and the jar disagrees with its explanation — bounded.**
  `ZomboidFileSystem.getAllModFoldersAux` accepts a folder as a mod when `<mod>/common/mod.info`
  exists — **checked first** (`@124-151 L602`) — *or* `<mod>/<versionDir>/mod.info` does, and only
  then resolves the two `media` roots (`@200-219 L607`, `@221-239 L608`). So for *discovery* the
  common placement is tested first, and the WARN's text as this pass read it ("B42 reads the
  version folder first") is contradicted **at that call site**. *(Dated follow-up, 2026-09-11:
  slice 10's final fix wave acted on this finding — the WARN now names the lint's own model and
  points at open question 1 instead of asserting an engine read order, and the bounded jar
  statement went into [`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 1.
  Nothing measured here changes.)* That is the folder-acceptance test, **not the id read**: which
  `mod.info` supplies the id comes from `ZomboidFileSystem.searchForModInfo`, and the precision
  there is that it returns the first `mod.info` **whose id matches the requested id**, in
  `File.list()` order (`L709` / `L730`) — *not* simply the first `mod.info` found; every one passed
  over is still registered into `modIdToDir` and appended to the caller's list. **Do not state an
  id-read order on the strength of this subject**: AutoCook ships exactly one `mod.info` and cannot
  discriminate. Both readings are evidence for
  [`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 1, which stays open.
  (C, jar, 2026-09-11.)
- **Overlap with our own nutrition mod.** AutoCook adds **no items, no recipes, no script blocks
  and no sandbox options**, so a rebalance of `module Base` food macros changes what it *chooses*
  and nothing it *defines*. The coupling runs the other way: our mod must not break
  `RecipeManager.getEvolvedRecipe`, `recipe:getItemsCanBeUse`, `recipe:isCookable`,
  `EvolvedRecipe.addItem`'s spice rule, or `Nutrition`'s five macros and three direction flags —
  AutoCook reads all of them (`common/…/AutoCook_RISCookMenuInsertion.lua:9,48`;
  `42.13/…/AutoCook.lua:111,251,216-219`). And if we add nutrients, its diets will not see them:
  its "nutritionist" mode will optimise against a partial model, silently.

## Verdict for our mod

**Not a dependency, not a conflict — a structural exemplar and a downstream consumer.** AutoCook
is the mod that made the corpus's oldest open question answerable, and it is the mod whose
behaviour our item pass changes without ever touching it.

**Adopt:**

- **The two-tree layout, now on measured ground.** `common/` for everything build-independent, a
  version folder for the per-build delta, and the version folder wins a collision. Write the
  dependency down where the layout is decided, and treat a shadowed `common/` file as unexecuted.
- **The `common/`-hosted entry point with a version-folder implementation** — one registration, one
  per-build body.
- **Queueing the game's own timed actions** rather than reimplementing them, if we ever automate
  anything.
- **A prefixed translation key as a tier-(a) load probe**, for any part of our mod that ships no
  scripts and writes no server state.

**Avoid:**

- **Non-idempotent vanilla wrappers** (Pitfalls 3) — use BeyondTen's sentinel.
- **Bare `_G` names at an extension point** (Pitfalls 4).
- **A `nil` return meaning two different things** (Pitfalls 2).
- **Per-client globals standing in for per-character state** (Pitfalls 5).
- **Assuming anything in player modData is private because we never transmit** (Pitfalls 6) — one
  neighbour's UI event puts the whole table on the wire.

**What stays C, and must not be upgraded on the strength of a green run.** The cooking pipeline
itself was never reached. Its only entry is a context-menu option
(`common/…/AutoCook_RISCookMenuInsertion.lua:87`) whose handler runs on a **right-click**, and
nothing on the shipped bus clicks, presses a key or calls `triggerEvent`. `AutoCook:chooseItem`,
`filterFood`, `allowSpice`, `acceptIngredient` and all five diets are **C** — read, not run. What
the session measured is the **load-time state and the read side**: the merge rule, the modData key
and its emptiness, the translation merge, the server's total absence of AutoCook globals, the timed
server-modData baseline, the transmit crossing, and the carried carrier probe.

**Carry forward:** three items, all recorded here rather than claimed. (a) `AutoCook:allowSpice`'s
weight-direction gate is **unsettled** — the agreement observed is under `updateWeight`'s trivial
`none` arm; a slice-12 session that drives calories outside `[0, 1000]` settles it.
(b) The CleanUI runtime half needs the two-order, three-mod profile above (slice 12/14). (c) The
carrier reading is one arm, one item, one window: frozen and non-cookable items and every other
push path are untested, and the operative rule for any client-side reader stays "you may be reading
a push, not a simulation".

## Sources

**Measured run** (the `default` fixture, build 42.20.4, one dedicated server + one real client;
the full run directories stay local under the gitignored `testing/runs/`):

- **`run-20260911-001251`** — acceptance, `pzt run --profile teardown-autocook --hold 5`,
  `RESULT: PASS`, exit 0, **both** tier-(a) `[[verify]]` rows `ok=True`, 95.3 s. **Provenance, not
  evidence:** its `report.json` lives under the gitignored `testing/runs/`, so it is not checkable
  from a clone ([`../../decisions.md`](../../decisions.md), the slice-01 row). The session re-asked
  both probes itself, and those readings — `verify[0]` and `verify[1]` — are what this doc cites.
  Anchor note: both rows read green at **`session_ready + 0.5 s`** and **`+ 1.0 s`** (the run's own
  timeline), not at `client_ready`, which is ~2.3 s earlier.
- **`td3-20260911-001948`** — the session. Artifact
  [`testing/artifacts/td3-20260911-001948/teardown-autocook.json`](../../../testing/artifacts/td3-20260911-001948/teardown-autocook.json)
  (64 170 B; 179.4 s wall; `server_error_count 0`, `client_lua_error false`, no `error` key), driver
  `testing/experiments/td3_autocook.py` at commit `3f4b646`, harness Lua at `d8cc34e`
  (`harness_lua_dirty false`, `doctor_clean true`, `acceptance_run run-20260911-001251`). Keys
  cited: `M1_overrides` (`server_log` / `client_console`), `mod_log_lines_server`, `loading_lines`,
  `nilcall_lines`, `M3_translations`, `M4_globals` (`client` / `server`), `snapshots[]`
  (`census_player`, `autocook_keys`, `fields`, `nutrition`), `baseline_timing`, `phase2[]`,
  `steps[]`, `t_action`, `transmit_reading`, `carrier` (`pin`, the four reads, `client_moved`,
  `server_moved`, `item_census`), `verify`, `summary`, `timeline`. Provenance, reading guides and
  the **do not cite** list:
  [`../../../testing/artifacts/README.md`](../../../testing/artifacts/README.md).
- **Profile:** `testing/profiles/teardown-autocook.toml` (harness + `[[mods]] id = "AutoCook",
  workshop_id = "3388721641"`, **no `[sandbox]` block**), committed at `7dfd3a6` with **two
  tier-(a) `[[verify]]` rows** — `text.get UI_AutoCookMode` expecting `"Cooking diet: "`, and
  `witness.moddata player:admin *` expecting `"AutoCook:table"`. Its comment block was corrected in
  `d8cc34e` (the second row proves `common/` ran and the chain completed; it does **not** name the
  winning copy).
- **Harness command this session depends on**, added in **`d8cc34e`** with
  [`../../testing/README.md`](../../testing/README.md) § Command bus updated in the same commit:
  **`lua.global <name>[.<field>...]`** (shared, both sides answer), the `_G` reader that made M4
  possible. It **never calls what it finds** — four functions were read on this run and none was
  invoked. Earlier commands used here came from `291f977` (`text.get`, the `tostring` float
  rendering, the three weight-direction flags, server `moddata.set`), `903ccaa` and `37e411e`.

**The mod itself** (read-only; `3388721641/mods/AutoCook/`, 19 files / 129 161 B, three of them
stamped 2026-09-07 21:54 and the rest 2026-08-12 00:02): `common/mod.info`;
`42.13/media/lua/client/{AutoCook,AutoCook_AutoCraftRecipes,ISCharacterCook}.lua`;
`common/media/lua/client/{AutoCook,AutoCook_AutoCraftRecipes,AutoCook_Diets,
AutoCook_RISCookMenuInsertion,ISCharacterCook,ISCharacterInfoWindow_AddTab,ISContinue}.lua`;
`common/media/lua/shared/Translate/EN/{ContextMenu,UI}.json` and the two B41 `_EN.txt` files;
`42/` (two PNGs). CleanUI `3437629766` was read cold for the collision analysis
(`42.19/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:25-33,669,1250`, and the seven-tree
`find -iname` census re-run 2026-09-11).

**Datasets:** [`data/mod-inventory.json`](../../../data/mod-inventory.json) — the `AutoCook` row
(230 mod folders swept 2026-09-10 17:47);
[`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json) — the
`3388721641` result (fetched 2026-09-10 17:46, **W**).

**Vanilla (C, read 2026-09-10):** `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:25-60,374`;
`media/lua/client/XpSystem/ISUI/ISCharacterInfoWindow.lua:103,182,291`;
`media/lua/client/ISUI/PlayerData/{ISPlayerData.lua:168,ISPlayerDataObject.lua:93-95}`;
`media/lua/client/ISUI/ISUIElement.lua:13-19,1007,1365-1368,1455-1457`;
`media/lua/client/ISUI/ISTabPanel.lua:494`; `media/lua/client/ISUI/ISXuiBuilder.lua:10-35` (the
`_G`-walk idiom `lua.global` follows); `media/lua/shared/Translate/EN/{ContextMenu,UI}.json` (the
key-collision check — the mod's 38 keys collide with **zero** vanilla keys).

**Engine (C, 42.20.4 jar dumps, 2026-09-10 and 2026-09-11):**
`ZomboidFileSystem.init @16-@36 L151`, `@165-@173 L163`, `@252-@268 L172`;
`ZomboidFileSystem.loadMod @0-@431 L739-L778` (the two passes, the two unconditional
`activeFileMap.put`s at `L758` / `L773`, the print gate at `L754-L755` / `L769-L770`);
`ZomboidFileSystem.getAbsolutePath @0-@19 L483-L484`;
`ZomboidFileSystem.getRelativeFile @31-@56 L1013-L1021` (the empty-URI return that explains an
empty `overrides` tail); `ZomboidFileSystem.getAllModFoldersAux @124-151 L602`, `@200-219 L607`,
`@221-239 L608`; `ZomboidFileSystem.searchForModInfo L708-L735` (`File.list()` at `L709`, the
id-matching return at `L730`); the `ZomboidFileSystem` constant pool (#1668 `'loading \x01'`,
#1670 `'mod "\x01" overrides \x01'`);
`LuaManager.LoadDirBase @0-@540 L1141-L1232` (vanilla-first `PZArrayUtil.addAll @371-@373`, the
per-mod common-then-version blocks, the case-insensitive sort at `L1198`, the `HashSet` dedupe at
`L1208-L1214`); `Translator.tryFillMapFromMods @0-@97 L376-L391` and
`tryFillMapFromFile @4-@29 L357-L358`, `@107-@118 L364`;
`Food.update @49-@103 L372-L379` (the `heat > 1.6f` cooking gate and the per-game-minute
`sendItemStats`), `Food.updateTemperature`; `Nutrition.save` (the five floats) and
`Nutrition.updateWeight` (the thresholds and the three flag writes);
`KahluaTableImpl.load @0-@6 L332-L333` (wipe-before-rawset); `ItemContainer.toString @0-@16 L3513`
and `IsoObject.toString @42 L5982`; the `IsoGameCharacter` / `InventoryItem` /
`zombie.scripting.objects.Item` method lists (the absence of `HasTrait(String)` and
`getTypeString`).

**Neighbouring library docs:** [`../../modding/patterns.md`](../../modding/patterns.md)
(§ Measured MP sync facts — the client-copy row this teardown **resolves per arm**, and the merge-
rule KEEP it sharpens; § Open pattern questions),
[`longtermpreservation4220.md`](longtermpreservation4220.md) (the freeze this session's carrier
probe reconciles, and the `overrides`-line correction this pass supplied),
[`simplestatus.md`](simplestatus.md) (the moving copy at the other end of the same question, and
the seven `transmitModData` call sites that make Pitfalls 6 concrete),
[`../nutrition-mods.md`](../nutrition-mods.md) (§ Open questions 1 and 3, both closed here; the
catalog row for this mod), [`../approved-modlist.md`](../approved-modlist.md) (the corpus and the
queue), [`../../modding/README.md`](../../modding/README.md) § Hard-won platform facts (the
merge-rule line),
[`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 1 (the `mod.info`
resolution order, strengthened and still open),
[`../../testing/README.md`](../../testing/README.md) § Command bus (`lua.global`, and the
client-console `2 × n` grep note this session produced),
[`../../vanilla/body-stats.md`](../../vanilla/body-stats.md) § MP behaviour (open question 10, the
weight-band traits the direction flags depend on).
