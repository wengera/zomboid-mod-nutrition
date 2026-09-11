# Mod anatomy — `mod.info`, folders, load order, and what the engine actually reads

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-11 · slice 12 (P2a), runs
`x121-20260911-030023`, `x122-20260911-032326`, `x123-20260911-034426` /
`x123b-20260911-034500`, `x124-20260911-035819`, `x125-20260911-042055`,
`x126-20260911-045205`.
Evidence grades: **C** read from bytecode/Lua/scripts, **M** measured on the live
dedicated server + client (run id given), **W** wiki mirror (secondary). The jar chain in
§ Code map was re-derived for this document; it supersedes the `searchForModInfo` reading
this library carried until 2026-09-11.

## Summary

1. **A mod folder answers to exactly one id, and the id comes from one file:** the version
   dir's `mod.info` if it exists, otherwise `common/mod.info`. Never the folder name, never
   the mod root, and never both — a folder carrying two `mod.info` files with two ids is
   addressable only by the version dir's.
2. **`Mods=` resolves ids, not paths.** Resolution runs as a whole pass *before* any mod
   loads; a miss prints `required mod "<id>" not found` and the mod is dropped. The 52
   installed workshop folders whose name differs from their id (`data/mod-inventory.json`,
   swept **2026-09-10 17:47**) load normally, and `harness.install`'s rename to
   `<mods_dir>/<mod id>` is a convenience, not a requirement.
3. **`common/` and the build's version dir both load, and the version dir wins** a
   same-relative-path collision — one `HashMap.put` over another into `activeFileMap`. A
   version dir that ships only a `mod.info` costs the mod nothing; `common/` still runs.
4. **Lua runs vanilla-first, then per mod `common/` then version dir**, each block sorted
   case-insensitively and deduped by relative path — so a mod file at a vanilla relative path
   replaces vanilla's body *in vanilla's slot*, and `require` resolves through the same map.
5. **Translations merge instead of shadowing, load per side, and are `.json` only on
   42.20.4.** A B41 `ItemName_EN.txt` is never opened; a dedicated server resolves no item
   display name at all; and `getText` cannot reach the item-name table under any key form.

## Model

### 1. `mod.info` — the keys, and who acts on them

`ChooseGameInfo.readModInfoAux` (`@139-@1411 L203-L330`) is a line scanner: for each line it
tests `line.contains("<key>=")` in a fixed branch order and, on a hit, `String.replace`s the
token away and stores the rest. It recognises **17 keys** (plus `type=` nested inside a
`pack=` block) and silently ignores every other line.

Census below: `python tools/mod_lint.py`'s 230 installed mod folders, every `mod.info` found
under each (including out-of-chain copies), **2026-09-11**. "Mods" = folders where at least
one `mod.info` carries the key.

| Key | Mods | What acts on it | Ev |
|---|---:|---|---|
| `id` | 229 | the only handle that exists. `Mods=` entries, `require=` entries and `ChooseGameInfo.Mods` are all keyed on it; `loadMod` prints `loading <id>` | C + M (`testing/artifacts/x123-20260911-034426/platform-folder.json` → `boots.drift`) |
| `name` | 229 | display only (mod selector). `Translator.readModTranslation @0-@61 L404-L417` lets a mod's own `Mod.json` translate it | C |
| `description` | 227 | display only; same translation path | C |
| `poster` | 224 | resolved against the version dir first, then `common/` (`@221-@265 L212-L215`); a path ending `poster.png` is gated out of the `overrides` print | C |
| `icon` | 203 | display only | C |
| `require` | 135 | **load order + availability.** `loadModAndRequired @80-@105 L936-L939` loads every required id first; `Mod.isAvailableRequired @0-@105 L680-L700` makes the *requiring* mod unavailable if any required id is missing or version-gated | C |
| `author` / `authors` | 176 / 11 | `author` is parsed and displayed; **`authors` is not a key** — 11 folders ship it and it is dropped | C |
| `versionMin` | 154 | **a hard gate, not a note.** `Mod.isAvailableSelf @0-@48 L667-L676` returns false when `versionMin > build`, `getAvailableModDetails` then returns null, and the mod reports as `required mod "<id>" not found` | C |
| `versionMax` | 13 | same gate, other end | C |
| `category` | 108 | display only (mod selector filter) | C |
| `modversion` | 45 | display only. **`modVersion` and `version` are not keys** — 2 folders each, dropped | C |
| `pack` (+ `type=`) / `tiledef` | 16 / 12 | `addPack` / `addTileDef`; consumed by `loadModPackFiles` / `loadModTileDefs`, which warn `pack file "<f>" needed by <id> not found` | C |
| `incompatible` | 12 | **display only.** `getIncompatible` is called from exactly two places in the whole jar-plus-Lua tree, **both mod-selector UI**: `media/lua/client/OptionScreens/ModSelector/ModSelectorModel.lua:120` and `.../ModSelector/ModInfoPanelInteractionParam.lua:58`; no jar class but the declaring `ChooseGameInfo$Mod` so much as names it. A server's `Mods=` ignores it | C |
| `url` | 5 | display only | C |
| `loadModBefore` / `loadModAfter` | 1 / 1 | **advisory, client UI only.** `getLoadBefore` / `getLoadAfter` are read only by `ModLoadOrderPanel.lua:52,68,222,258` and `ModOrderListBox.lua:50,60` — they arrange the selector's list. The server loads in literal `Mods=` order | C |
| `tags`, `pzversion`, `texts`, `supports`, `zoomX/Y/S` | 15 / 10 / 1 / 1 / 1 | **not parsed at all.** No branch tests them | C |
| the keys **we** declare | 7 mods, 8 ids (A–G; mod D declares two) | every slice-12 experiment mod ships exactly `name` + `id` + `description` + `modversion` + `versionMin` and nothing else; all seven ids resolved and every mod loaded | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `mods_not_found` empty; `testing/artifacts/x122-20260911-032326/platform-loader.json` → `summary.mods_not_found`) |

**Load-order declarations, ranked by what the engine does with them:** `require=` is the only
one the loader acts on (it loads dependencies first and gates availability). `loadModAfter=` /
`loadModBefore=` move rows in the client's mod selector and nothing else. `incompatible=`
colours a row. On a dedicated server the order is exactly the order of `Mods=`, with each
entry's `require=` closure inserted ahead of it.

**Parser hazards, both C.** The branch test is `contains`, not `startsWith`, and the strip is
`replace`, not a prefix cut — so a value containing an *earlier* branch's token is eaten by
that branch (`url=https://x/name=1` is parsed as a `name`), and every occurrence of the token
disappears from the value. Keys are case-sensitive, which is why `modVersion=` is dropped.

### 2. Where a `mod.info` may live, and which one supplies the id

**The rule, measured: resolution is by `mod.info` id, never by folder name; one id per mod
folder, the version dir's `mod.info` supplying it.**

| Reading | Result | Ev |
|---|---|---|
| a folder renamed to match **neither** id, `Mods=` naming the **version dir's** id (`TKX_LoaderVersion`) | loads: `loading TKX_LoaderVersion` at server log 94, the `overrides` line at 95, `TKX_LoaderWhich == "version"`, both tree markers resolved, both media roots walked under the renamed folder | M (`testing/artifacts/x123-20260911-034426/platform-folder.json` → `boots.drift`) |
| the same folder, `Mods=` naming the **`common/mod.info`** id (`TKX_LoaderCommon`) | fails: `required mod "TKX_LoaderCommon" not found` at server log 93, zero `loading` / `overrides` lines, all three probe globals unresolved, no media tree walked | M (same file → `boots.common_id`, run `x123b-20260911-034500`) |
| id resolution is a pass that completes **before** any mod loads | boot (b)'s `not found` WARN precedes the first `loading` line; boot (a)'s `loading` lines follow `Mods=` order exactly | M (n = 2 boots, same file) |
| the mechanism | `ChooseGameInfo.readModInfoAux @32-@120 L184-L195` opens `<versionDir>/mod.info` if it exists and `<commonDir>/mod.info` otherwise, and parses **only that one file** | C (§ Code map) |

**Operational form, and the bound.** For the requested-id lookup only the version dir's
`mod.info` id is addressable; a folder carrying **both** `mod.info` files answers to one id.
The measurement is n = 1 probe per boot, one build, the **dedicated-server** path
(`Mods=` → `ZomboidFileSystem.loadModAndRequired`); the client's own mod-list call site was
not exercised. A folder whose **only** `mod.info` is `common/mod.info` is untested as a *probe*
— though **4** installed mods have that shape (`3388721641/AutoCook`, `3413255058/RemoveAllItems`,
`3520263838/EN_Newburbs`, `3717099183/WorkingKnowledge`, counted 2026-09-11). Of those,
**AutoCook has booted** — **M** (`testing/artifacts/td3-20260911-001948/teardown-autocook.json`
→ `loading_lines`: three `loading AutoCook` lines, server 94 and client 84/167) — and **the
other three rest on the jar fallback**, **C**: `versionDir` names a directory that ships no
`mod.info`, so `readModInfoAux` takes `<commonDir>/mod.info`.

**This closes `docs/testing/profiles.md` § Open questions 1.** The lint's model —
newest version folder first, then `common/` — is **vindicated for this lookup**; the plan's
jar reading, that `searchForModInfo` "registers every `mod.info` it meets and returns the
first whose id matches", describes **no live call site at all** (§ Code map, the
re-derivation). `mod_lint.info_chain` is still a *superset* of the engine's chain: it tries
every version folder and the mod root, the engine tries one version folder and `common/`.
Across the 230 installed folders the two pick the **same file on 229** and differ on exactly
one — see § Discrepancies.

### 3. Version dirs and `common/`

`getModVersionDirName(<mod>)` (`@0-@102 L569-L583`) lists the mod folder and keeps the entry
name whose parsed version is **≥ `ChooseGameInfo.minRequiredVersion` (`GameVersion(42,0)`,
`<clinit> @40-@52 L42`) and ≤ the running build**, defaulting to `"42"` when nothing
qualifies. `getGameVersionIntFromName @0-@65 L666-L675` parses `major*1000 + min(minor,999)`
— so the **third component is ignored** (`42.20.1` and `42.20` both score 42020) and a
non-numeric entry scores 0 and is skipped. All **C**.

The merge rule itself is restated from [`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md)
§ Architecture, which holds the four jar sites (`loadMod`'s two `activeFileMap.put` passes at
`L758` / `L773`, `getAbsolutePath @0-@19 L483-L484`, `LuaManager.LoadDirBase`, and
`Translator.tryFillMapFromMods`). What slice 12 adds:

| Reading | Result | Ev |
|---|---|---|
| the version dir wins a same-relative-path collision and `common/` still ran — **n = 2** now (AutoCook, a workshop mod, plus a mod we control) | `TKX_LoaderWhich == "version"` on both sides with `TKX_LoaderCommonTree` **and** `TKX_LoaderVersionTree` resolving | M (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `summary.L2_which`, `summary.L2_trees`; and run `td3-20260911-001948`) |
| the loader prints **one line per shadowed file per Lua state**, tail = the lower-cased relative path | server 1 line, client 2, all `mod "TKX_LoaderVersion" overrides media/lua/shared/tkx_loader_which.lua` | M (same file → `phases.L2.reading.overrides_tails`) |
| a mod that shadows nothing **and ships `common/`** prints no `overrides` line at all | `overrides_any` 1 line on the server and 2 on the client, all from `TKX_LoaderVersion`; `TKX_CommonOnly`, which ships `common/media` and collides with nothing, printed none | M (same file → `greps.overrides_any`) |
| **a version dir holding only a `mod.info` and no `media/` costs the mod nothing** — the new arm | `loading TKX_CommonOnly` (server 96, client 86/166), `TKX_CommonOnly.version` resolves on both sides off `common/media`, no `required mod … not found` | M (same file → `phases.L3.reading`) |
| a mod with **no** `common/` prints an `overrides` line with an **empty tail** — one per such mod per Lua state | **three** empty tails per state (server 95/97/100, client 85/87/90 and 169/171/174), one each for `TKX_ZWatermelon`, `TKX_ItemOverride` and `TKX_EatHook`, none of which ships `common/`; `TKX_ItemOverride`'s real `itemname.json` line sits at 98 beside its empty one, and `PZTestKit` — also `common/`-less and loaded first — seeds the `""` key and prints none | M for one of the three (`testing/artifacts/x124-20260911-035819/platform-order.json` → `greps.script_files`, whose pattern spells the other two mod names with underscores and so misses them); all three read directly from that run's logs, `testing/runs/x124-20260911-035819/server/server-console.txt` and `clients/admin/console.txt`, which `.gitignore:44` keeps out of the repo — so the committed half of this row is the mechanism, **C** (slice 11, run `td3-20260911-001948`: `loadMod L754-L755` / `L769-L770` with `getRelativeFile` returning `""` — reading in [`../mods-survey/teardowns/longtermpreservation4220.md`](../mods-survey/teardowns/longtermpreservation4220.md)) |
| the wiki's statement of the order — common, then closest versioning folder, overwriting | agrees with the measurement | W ([mod-structure mirror](../../references/wiki-mirrors/mod-structure.md), page version 42.20.0, fetched 2026-09-10) |

**KEEP 10's bound now reads "a version dir that ships colliding files, or none at all."** The
untested arm that remains is a version dir shipping `media/` that collides with *nothing*.

Two cautions. The `common/`-enumerated-first lines in the logs are the
`AdvancedAnimator.loadModMedia` media walk, **not** the `activeFileMap` pass — corroborating
only, never cited as the map pass. And "one `overrides` line per file per Lua state" is why
the client prints twice: the client runs two Lua states and the count is 2 × n.

### 4. `Mods=` and the folder name

`harness.install` copies every profile source to `<mods_dir>/<mod id>`
(`testing/pzt/harness.py:27-32`), so a run's `mods/` listing always shows ids. Slice 12
produced the counterfactual that slice 09 recorded as out of reach: a folder renamed to
`TKX_DriftedFolder`, matching neither of its ids, loaded when `Mods=` named the version dir's
id — **M**, `boots.drift`. The rename is therefore a convenience, and the **52 installed
workshop folders whose name drifts from their declared id** (`data/mod-inventory.json`, swept
**2026-09-10 17:47**; the lint's `folder-id` INFO counts 51, having no id to compare on the
52nd — the pair falls to 51 and 50 after the 2026-09-11 04:47 workshop change § 7 records)
load by id in normal play.

**This closes `docs/testing/profiles.md` § Open questions 6, second half.** The one thing the
boot does *not* license: `folder_check.installed_id_folder_present` was `false` in both boots,
so "the folder was never scanned" is not separable from "scanned and rejected" — the mod not
loading already entails that its media roots were never mapped.

### 5. Translations

Two layouts exist in the wild and **only one is read on 42.20.4**:
`<dir>/media/lua/shared/Translate/<LANG>/<File>.json` (B42) and
`<dir>/media/lua/shared/Translate/<LANG>/<File>_<LANG>.txt` (B41). `Translator.tryFillMapFromFile`
(`@4-@36 L357-L358`) formats `%s/media/lua/shared/Translate/%s/%s.json` and opens **nothing
else**; `tryFillMapFromMods @0-@97 L376-L391` walks each mod's `getCommonDir()` (`@41-@63 L382-L384`)
then `getVersionDir()` (`@66-@88 L386-L388`) through it, and the file reader **merges into a
shared map** rather than replacing it (`tryFillMapFromFile @107-@118 L364`) — vanilla's
keys survive, the mod's are added, and translations are the one thing in a mod tree that does
**not** shadow. All **C**.

| Reading | Result | Ev |
|---|---|---|
| a B42 `ItemName.json` name resolves on the **client** | `getDisplayName() == "TKX Fibre Bar Json"` against `getFullType() == "TKX.FibreBarJson"` | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M4.items."TKX.FibreBarJson".witness.client.fields`) |
| a B41 `ItemName_EN.txt` name does **not** | `getDisplayName() == getFullType() == "TKX.FibreBarNamed"`, the untranslated signature, on both sides | M (same file → `phases.M4.items."TKX.FibreBarNamed"`) |
| a **dedicated server** resolves no item display name at all, JSON included | server `getDisplayName() == "TKX.FibreBarJson"` for the same item and the same tick the client read the translated name | M (same file → `phases.M4.items."TKX.FibreBarJson".witness.server.fields`) |
| `getText` cannot reach item names under **either** key form | bare `Base.Apple` / `TKX.FibreBarJson` / `TKX.FibreBarNamed` and the `ItemName_`-prefixed controls all return a genuine miss (`miss: true`, `text == key`, no `null`, no `error`) on both sides. **Bound:** every reply in that phase missed, so the run carries no in-run positive control — the route's soundness rests on slice 10's client-side `IGUI_` hit (`291f977`), a different session, and the **C** row at the foot of this table is what makes the misses explicable rather than merely unexplained | M (`testing/artifacts/x124-20260911-035819/platform-order.json` → `phases.O5` / `verdicts.P19`, `falsified`) |
| a dedicated server's `text.get` **answers** (miss, not `null`, not `error`) | the server half of the command is readable; across x121 + x124 no server-side `getText` has ever returned a hit on any of 9 keys — which says the ROUTE answers, not that the server's table is populated | M (same file → `phases.O5` server replies) |
| why | `Translator.getTextInternal @0-@830 L420-L498` is a **prefix router** over 25 key prefixes (`UI_`, `IGUI_`, `ContextMenu_`, `Moodles_`, `Tooltip_`, `Attributes_`, …) and `ItemName_` is not one of them; the item map is reached only by `getDisplayItemName(fullType) @0-@38 L589-L595`, which looks up the **raw full type** with ` ` and `-` folded to `_` | C |

**This retires slice 09's hypothesis ambiguity:** (iii), that a B41 `_EN.txt` still loads, is
dead; (ii), that only the JSON layout is read, is confirmed. Two rules follow. Never branch on
an item display name server-side — a dedicated server has none. And a translation-only mod
gate must use a `UI_` / `IGUI_` key (slice 10's precedent), never an item name: the
`ItemName.json` table is loaded and working, and is simply not addressable from Lua's
`getText`.

### 6. `require` and Lua load order

`LuaManager.LoadDirBase(String, boolean)` builds the execution list in this order, all **C**:
vanilla's own block first, sorted case-insensitively (`@364-@373 L1203-L1204`); then **per
mod** the `commonDir` block (`@136-@229 L1169-L1181`) and the `versionDir` block
(`@239-@332 L1184-L1196`), each sorted case-insensitively (`@342-@348 L1198`). It then walks
that list through a `HashSet` (`@386-@393 L1208`): a **relative path already seen is skipped**
(`@425-@435 L1211-L1212`), and the survivor is resolved with
`ZomboidFileSystem.getAbsolutePath` — literally `activeFileMap.get(rel.toLowerCase())` — and
run (`@446-@485 L1216-L1222`).

Two consequences worth internalising:

- **A mod file at a vanilla relative path replaces vanilla's body in vanilla's slot.** The
  *path* is deduped at vanilla's position in the list, but the *file* that executes is
  whatever `activeFileMap` holds, which the mod's `put` overwrote. So the replacement runs
  early — before every mod's own block — not where the mod sits in `Mods=`.
- **`require` resolves against the same map.** There is no per-mod search path; a `require`
  hits the one absolute path `activeFileMap` currently holds for that relative path.

**And a mod's `media/lua/server/` files execute in the MP client's Lua state.** Three
independent witnesses in one session: `TKX_Nutrient.side` read `"server"` **on the client**
(the client-only file had written `"client"` to the same global), `TKX_Nutrient.ticks` read 58
on the client against 38 on the server, and `TKX_EatHook.wrapped` was `true` client-side —
**M**, n = 1 session, incidental, mechanism untraced
(`testing/artifacts/x121-20260911-030023/platform-overrides.json` →
`phases.M7.mod_globals.client` for the two `TKX_Nutrient` globals;
`phases.M5.globals.client` and `verdicts.M5b.observed.wrapped` for `wrapped`, which is a
phase-M5 reading and not an M7 one).
**Rule: guard `server/` files with `isServer()`. A "server" file is not a server-only file.**
The probe that would trace it: a `server/` file printing `isServer()` / `isClient()` at file
scope on both sides, read alongside the `LuaManager` load path for the client's two states.

### 7. What `mod_lint` checks, and why

`tools/mod_lint.py` runs nine L0 rules before any server boots. Slice 12 promoted three of
them from model to engine reading.

| Rule | Level | Standing after slice 12 | Ev |
|---|---|---|---|
| `version-dir` | ERROR | model, deliberately strict: the engine tolerates a mod with no version dir at all (`getModVersionDirName` returns `"42"`, that path does not exist, and `common/` carries both the id and the media). No installed mod ships that shape — all 230 have one — so the rule has never fired on the corpus, and it stays an ERROR for *our* mods, where a missing version dir is a packaging mistake | C |
| `mod-info` | ERROR | engine reading, widened: the engine needs a `mod.info` in the build's version dir **or** `common/`, and warns `can't find mod.info in mod dir` otherwise | C |
| `mod-info-place` | WARN | **now a bounded engine reading.** The version dir's `mod.info` is the one that supplies the id; `common/` is the fallback | M (`testing/artifacts/x123-20260911-034426/platform-folder.json` → `boots.common_id`, run `x123b-20260911-034500`) + C |
| `id` | ERROR | engine reading — an unparsed or missing `id=` leaves `Mod.id` at its constructor default `undefined_id` (`<init> @82-@85 L502`) | C |
| `id-agree` | ERROR | **stricter than the engine needs, and kept.** The engine opens one file, so a disagreement cannot change today's id; but the flagged file becomes authoritative the moment the version dir's `mod.info` is removed or the build moves past that version dir | C |
| `id-drift` | WARN | unchanged — an out-of-chain copy no resolver can reach | C |
| `media` | WARN | **an intent check, not a load failure** — slice 12 measured a version dir with a `mod.info` and no `media/` loading its whole `common/` payload | M (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `phases.L3.reading`) |
| `loadstring` | ERROR | unchanged — removed from the engine in 42.20.x | C |
| `folder-id` | INFO | **now an engine reading, and correctly informational** — the folder name is never consulted | M (`testing/artifacts/x123-20260911-034426/platform-folder.json` → `boots.drift`) |

The two rules the plan called models are now split: `mod-info-place` is a reading (bounded to
the dedicated-server requested-id lookup) and `media` is a reading that says the opposite of
a failure. `media_root`'s "newest version folder present" stays a model in one respect only —
it ignores the engine's `≤ build` ceiling, which is invisible on a corpus whose version dirs
top out at `42.20.1` (`data/mod-inventory.json`, swept **2026-09-10 17:47**).

Sweep, reproduced **2026-09-11 04:27**: `84 finding(s): 3 ERROR, 30 WARN, 51 INFO across 230
mod(s)` — 51 `folder-id`, 24 `media`, 6 `mod-info-place`, and the three errors on the two
known mods. Unchanged from the 2026-09-10 sweep — and **moved twenty minutes later**: at
**2026-09-11 04:47** Steam rewrote `3161951724/76chevyKseriesExpanded`'s `42.20/mod.info`,
fixing the id typo `76chevyKserieseExpanded` → `76chevyKseriesExpanded`, so a sweep after that
reads `83 finding(s): 3 ERROR, 30 WARN, 50 INFO` and the drifted-folder count is 51, not 52
(**C**, file mtime + re-sweep, 2026-09-11). Quote a sweep with its stamp: the tree is live.

### The seven experiment mods

All seven live under `testing/experiments/`, are `versionMin=42.0.0`, and are test-profile only.

| Mod | Id(s) | Profile | Session(s) | What it measured | Ev |
|---|---|---|---|---|---|
| A | `TKX_ItemOverride` | `x12-overrides`, `x12-order`, `x12-order2` | 1, 4, 5 | script override shapes, three translation states, the Watermelon collision | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json`) |
| B | `TKX_EatHook` | `x12-overrides`, `x12-order`, `x12-order2` | 1, 4, 5 | `OnEat` on both sides, the `ISEatFoodAction.complete()` wrapper, the second Watermelon body | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M5a`, `phases.M5b`) |
| C | `TKX_Nutrient` | `x12-overrides` | 1 | modData routes, and incidentally the `server/`-file finding of § 6 | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M6`, `phases.M7`, `phases.M9`) |
| D | `TKX_LoaderVersion` (`42.20/`) and `TKX_LoaderCommon` (`common/`) | `x12-loader` | 2, 3 | the merge direction, the `overrides` tails, the folder drift, the requested-id discriminator | M (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `summary.L2_which`; `testing/artifacts/x123-20260911-034426/platform-folder.json` → `boots.drift`, `boots.common_id`) |
| E | `TKX_CommonOnly` | `x12-loader` | 2, 3 | a version dir holding only a `mod.info` | M (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `phases.L3.reading`) |
| F | `TKX_ZWatermelon` | `x12-order`, `x12-order2` | 4, 5 | a Watermelon body whose id sorts last; gated at tier (c) | M (`testing/artifacts/x124-20260911-035819/platform-order.json` → `phases.O1`; `testing/artifacts/x125-20260911-042055/platform-order2.json` → `phases.O1`) |
| G | `TKX_PcallProbe` | `x12-pcall` | 6 | whether `pcall` catches a Kahlua nil call, and whether the handler body and the handler registered behind it survive one | M (`testing/artifacts/x126-20260911-045205/platform-pcall.json` → `phases.reads.client.values`, `phases.reads.server.values`, `verdicts.P21_client` / `verdicts.P21_server`) |

## Code map — the `Mods=` chain, re-derived

Every offset dumped from the 42.20.4 jar on **2026-09-11** and re-located by content. This
chain replaces the `searchForModInfo` model.

| Step | Site | What it does |
|---|---|---|
| 1 | `ZomboidFileSystem.loadMods @0-@79 L957-L969` | **two passes.** Pass 1 calls `loadModAndRequired(id, this.mods)` for every requested id; pass 2 calls `loadMod(id)` for everything pass 1 accepted. Every `not found` therefore precedes every `loading` line |
| 2 | `ZomboidFileSystem.loadModAndRequired @43-@47 L928` | `ChooseGameInfo.getAvailableModDetails(id)`. On null: `GameServer.ServerMods.remove(id)` (`@58-@65 L931`) and the warn `required mod "<id>" not found` (`@66-@78 L933`, constant #1680). On success, recurses over `require=` (`@80-@105 L936-L939`) then appends the id (`@106-@111 L942`) |
| 3 | `ChooseGameInfo.getAvailableModDetails @0-@19 L149-L153` | `getModDetails(id)`, and requires `Mod.isAvailable()` — which is where `versionMin` / `versionMax` / a missing `require=` turn into "not found" |
| 4 | `ChooseGameInfo.getModDetails @0-@142 L121-L145` | the id → dir lookup. Negative cache `MissingMods` (`@0-@11 L121`), positive cache `Mods` (`@12-@32 L124-L125`), then `ZomboidFileSystem.getModDir(id)` = `modIdToDir.get(id)` (`getModDir @0-@13 L976`). **If the map has no entry**: `getAllModFolders` (`@49-@55 L130`), then for **every** mod folder `readModInfo(folder)` (`@66-@77 L132`) and `setModIdToDir(mod.getId(), folder)` (`@84-@102 L134`) — **one id registered per folder** — returning as soon as the id matches (`@104-@117 L135-L136`) |
| 5 | `ZomboidFileSystem.getAllModFolders @0-@224 L633-L663` | the folder list, cached in `modFolders`, built over `modFoldersOrder` (default `workshop,steam,mods`, `@25-@32 L636`), each root walked by `getAllModFoldersAux` (`@181-@190 L657`) |
| 6 | `ZomboidFileSystem.getAllModFoldersAux @124-@151 L602` | **discovery only.** A directory is a mod folder iff `<dir>/common/mod.info` exists (tested **first**) **or** `<dir>/<getModVersionDirName(dir)>/mod.info` does. A gate, not the id read — which is why "common first" here never contradicted the version-first id read |
| 7 | `ChooseGameInfo.readModInfo @0-@101 L157-L175` | `readModInfoAux(dir)`, then `Mods.put(id, mod)` when the id is new (`@27-@39 L164`). On a **duplicate id across two folders** it keeps whichever folder comes **earlier** in `getAllModFolders`' list (`@50-@99 L167-L171`) — so a `mods/` copy never beats a workshop copy of the same id |
| 8 | `ChooseGameInfo.readModInfoAux @32-@120 L184-L195` | **the answer.** `Mod.<init> @132-@193 L520-L528` set `commonDir = <dir>/common` and `versionDir = <dir>/getModVersionDirName(<dir>)`. This method builds `<versionDir>/mod.info` (concat constant #634 `'\x01\x01mod.info'`) and uses it **if it exists** (`@37-@74 L186-L190`), else `<commonDir>/mod.info` (`@77-@97 L191-L192`), else warns `can't find mod.info in mod dir: "<dir>"` and returns null (`@107-@120 L194-L195`). It parses **that one file** and nothing else |
| 9 | `ZomboidFileSystem.loadMod @0-@41 L739-L745` | `getModDir(id)`, print `loading <id>` (constant #1668), `getModInfoForDir(dir)` — the **same** `Mod` object, from `modDirToMod` (`@0-@40 L980-L985`) — then the two `activeFileMap` passes at `L758` / `L773` |

**Where `searchForModInfo` sits: nowhere.** `ZomboidFileSystem.searchForModInfo @0-@173
L708-L735` is referenced by **nothing but its own recursive call** (`@57-@62 L715`). A
whole-jar scan for the name finds it only in `ZomboidFileSystem`'s constant pool, and a
per-method `refs` sweep of every `ZomboidFileSystem` method finds the reference only inside
`searchForModInfo` itself. It is **unreachable on 42.20.4**. Its two distinctive behaviours —
a plain `modIdToDir.put` at `@130-@149 L727` (against `setModIdToDir`'s `putIfAbsent`,
`@0-@11 L704`) and "the first `mod.info` whose id matches, in `File.list()` order" — therefore
describe no live call site. The earlier C claim is **re-scoped to dead code, not deleted**:
it was a correct reading of the method and a wrong reading of the platform. Note also that
even its leaf branch delegates to `ChooseGameInfo.readModInfo(file.getParent())`
(`@97-@104 L722`), i.e. back into step 8.

## MP behaviour

| Fact | What it rests on | Ev |
|---|---|---|
| **A profile is a server-side decision the client inherits.** The server's `Mods=` is authoritative on join; the client's own mod list is not consulted for what a joined session runs | both sides are seeded from **one** source map (`testing/pzt/profile.py:132` `resolve_mod` → `sources[mod_id]` → `testing/pzt/harness.py:27-32` `install`), which is what makes a per-side divergence a harness bug rather than a platform fact. Not separated in these runs — the harness installs the same map on both sides | C (our harness at the two paths named; the engine half is § Code map steps 1–2, where the requested list is `GameServer.ServerMods`) |
| **Everything in § 1–§ 4 was measured on the dedicated-server path** | the client's own mod-list call site — `ChooseGameInfo.getModDetails` reached from the selector rather than from `loadMods` — was never exercised; the chain above is shared, but that is a code reading (§ Open questions 1) | C (§ Code map steps 1 and 4: `ZomboidFileSystem.loadMods @0-@79 L957-L969`, `ChooseGameInfo.getModDetails @0-@142 L121-L145`) |
| **Scripts and translations load per side and never sync.** Anything keyed on a display name is therefore a client-only value | a value written in an item script is identical on both sides for free; a translation table is built independently on each side, and the dedicated server's item-name table is effectively empty (§ 5) | M — the script half from [patterns.md](patterns.md) § Measured MP sync facts KEEP 11, run `td1-20260910-192457`, cited not re-graded; the translation half is § 5's rows (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M4`) |
| **Lua state count differs by side.** The server runs one Lua state, the client two, so a mod's file-scope side effects run **twice** on a client | the doubled `overrides` and `loading` lines in every client log this slice produced | M (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `summary.L1_loading`, `summary.L2_overrides`) |
| **A mod's `server/` tree runs on the client too** (§ 6). In MP the single most consequential anatomy fact in this document: a file under `media/lua/server/` is a naming convention, not a deployment boundary | three globals read **on the client** that only the mod's `server/`-tree file writes | M (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M7.mod_globals.client`, plus `phases.M5.globals.client` for `wrapped`; n = 1 session, incidental, mechanism untraced) |

## Discrepancies

1. **`mod_lint.info_chain` vs the engine chain — one mod in 230.** The lint tries every
   version folder newest-first, then `common/`, then the mod root; the engine tries
   `getModVersionDirName`'s single pick, then `common/`, and never the root. Recomputed over
   the installed corpus **2026-09-11**: they choose the **same file on 229 folders** and
   differ on `3396446795/MoodleFramework`, which ships `42.0/`, `42.13/`, `42.20/` and
   `common/` with `mod.info` in `42.0/` and `common/` only — the lint opens `42.0/mod.info`,
   the engine opens `common/mod.info`. **Both declare `id=MoodleFramework`, so no id moves**,
   and `id-agree` is the net that keeps that a fact rather than luck. **C** (recomputation
   over the read-only workshop tree).
2. **The other five `mod-info-place` WARNs are not discrepancies.** AutoCook, RemoveAllItems,
   EN_Newburbs, gasmask and WorkingKnowledge all ship `mod.info` in `common/` and in no
   version dir, so the lint and the engine open the same file. `gasmask` also ships a root
   `mod.info` with the same id, which neither reader ever opens. **C**.
3. **The plan's jar reading of question 1 was wrong as stated**, and so was this library's:
   `getAllModFoldersAux` testing `common/mod.info` first is real but is *discovery*, and
   `searchForModInfo`'s id-matching precision is real but describes dead code. Both were
   correct readings of the wrong method. **C**.
4. **A tie in `getModVersionDirName` resolves by `File.list()` order, not by precision.** The
   comparison is `v >= best`, so on a tie the **last** entry listed wins; `42.20` and
   `42.20.1` score identically. On NTFS's sorted listing the later name wins, which happens to
   agree with `mod_lint.version_dirs`' tuple sort — agreement by coincidence, not by design.
   **C**.
5. **The wiki's B42 page says each version folder has "its own `mod.info`"**
   ([mirror](../../references/wiki-mirrors/mod-structure.md), page version 42.20.0). True as
   a permission, misleading as a plan: only one of them is ever read, and shipping two with
   different ids makes the other unaddressable. **W** against **C + M**.

## Open questions

1. **The client's own mod-list call site.** Everything in § 2 is the dedicated-server path.
   The selector reaches `ChooseGameInfo.getModDetails` too, so the chain is shared by code
   reading — but a client-side boot with a drifted folder has not been run.
2. **A folder carrying *only* `common/mod.info` as a purpose-built probe.** 4 installed mods
   have the shape; one of them, AutoCook, has booted (**M**, `td3-20260911-001948`), the other
   three rest on the jar fallback (**C**), and slice 12's discriminator carried both files.
   One boot closes it.
3. **A version dir that ships `media/` colliding with nothing.** KEEP 10's remaining untested
   arm; both measured arms had a collision or an empty version dir.
4. **Why a mod's `server/` tree executes in the client's Lua state** — the outcome is M, the
   mechanism is untraced. Named probe in § 6.
5. **Whether `loadModAfter=` / `loadModBefore=` reach a dedicated server at all.** The jar and
   the vanilla Lua tree say no; nothing has booted a pair that disagrees about order.
6. **What a duplicate id across two mod roots actually does in practice** —
   `readModInfo`'s earlier-folder tie-break (step 7) is C only, and `setModIdToDir`'s
   `putIfAbsent` and `Mods.put`'s replacement can in principle disagree about which folder a
   given id ends up pointing at.

## Inputs for the wall map (slice 13)

One line per entry area: what classifies it today, and what would settle the rest.

| Area | Verdict | Evidence, and the next probe | Ev |
|---|---|---|---|
| New nutrient fields | **CAN WITH A WORKAROUND** | per-side modData holds without a transmit, and a server→client `transmitModData()` **wipes and replaces** the receiver's table (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M6`, `phases.M9`); FILTER 10 is the rule. Unsettled: the server→client **item**-modData direction — un-run | M |
| Eat hooks | **CAN** | `OnEat` fires on both sides at fraction 1 (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M5a`); `ISEatFoodAction.complete()` runs server-only and a Lua wrapper of it runs **before** `Eat`, installing silently on the client too (`phases.M5b`) | M |
| The weight formula | **CANNOT** client-side, **CAN** for direction | `Nutrition.updateWeight`'s `GameClient.client` skip sits before `setWeight` (C, re-quoted from [`../vanilla/body-stats.md`](../vanilla/body-stats.md) § MP behaviour, not re-dumped here); the three direction flags are set ahead of it and agreed across sides on both non-trivial arms (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M8.arms[*].reading` and `summary.M8_flags`). `nutrition.set calories −100` is **not clamped** (−102.5664 read back on the server, −102.10 on the client, same key) | M |
| Moodles | **UNKNOWN** | MoodleFramework "whole on 42.20.4" is **C** derived from the merge rule — nothing has booted it, and it is the one corpus mod whose `mod.info` chain differs between the lint and the engine (§ Discrepancies 1). Probe: boot it under a profile and read one `MF_Config.lua` global | C |
| Sync — item stats | **CAN** | the server→client table in [patterns.md](patterns.md) § Measured MP sync facts (runs `td1-20260910-192457`, `td1b-20260910-202029`): 43 fields, `hungChange` faithful, `thirstChange` halved per hop, aging fields absent | M |
| Sync — player stats | **CANNOT** client-side | `Nutrition` and `CharacterStat` are server-authoritative and pushed at 1 Hz; a client write is gone inside 1.5 s (patterns.md, runs `exp01-20260910-000351`, `exp03-20260910-045523`) | M |
| Sync — modData | **CAN WITH A WORKAROUND** | client→server transmit **wipes** — n = 2, `td2-20260910-231655` plus `testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M9`; one owner per value, or keep it server-side | M |
| The cooking pipeline | **UNKNOWN** | stays **C**: nothing on the bus reaches a right-click or executes `craftRecipe`. The measured neighbour is `Food.update`'s strict `heat > 1.6f` gate and its `sendItemStats` carrier | C |
| Traits | **CANNOT** be read client-side with confidence | the band traits are not in `PlayerStatsPacket` and no other packet was traced (body-stats open question 10); `HasTrait(String)` no longer exists on 42.20.4 | C |
| Translations | **CAN**, client-only, JSON-only | § 5: `ItemName.json` resolves on the client, `_EN.txt` never, a dedicated server resolves no name (`testing/artifacts/x121-20260911-030023/platform-overrides.json` → `phases.M4`), and `getText` cannot reach the table (`testing/artifacts/x124-20260911-035819/platform-order.json` → `phases.O5`). Gate on a `UI_` / `IGUI_` key | M |
| The merge rules | **CAN** | version dir wins, `common/` supplies the rest, n = 2 with `td3-20260911-001948`, plus the empty-version-dir arm (`testing/artifacts/x122-20260911-032326/platform-loader.json` → `summary.L2_which`, `phases.L3.reading`). Remaining arm: a version dir shipping `media/` that collides with nothing | M |
| Lua limits — the nil-call guard | **CAN**, guard kept for visibility, not for survival | `pcall` **catches** a Kahlua nil call on both sides — `ok` `false`, `err` `tried to call nil java.lang.RuntimeException`, and both the handler's own tail and the handler registered behind it advanced (client 3 / 3, server 15 / 15) — so this library's "a nil call escapes `pcall`" half is **falsified**. The catch is silent (the message names no global, line or file; the engine logs nothing), which is why the `TK.call` / `tkxCall` index-first guards stay. **Bound:** the probe measured `pcall(<nil function argument>)` only; an unguarded raise's effect on the rest of a handler and on the chain behind it, and the nested-origin shape `pcall(function() SomeNil() end)`, are session 7 (`x127`). [lua-api.md](lua-api.md) and [patterns.md](patterns.md) own the rule text and are not re-graded here | M (`testing/artifacts/x126-20260911-045205/platform-pcall.json` → `phases.reads.client.values`, `phases.reads.server.values`, `verdicts.P21_client` / `verdicts.P21_server`) |

**The three checks this slice records rather than claims.**

1. **The id-vs-script-path boot** — the reversed-`Mods=` check this slice opened is now
   **closed** by session 5. Across three boots (x121 111, x124 999, x125 999) script bodies
   replay in a **sorted, `Mods=`-independent** order with per-key last-wins, and
   `Mods=`-last-wins, first-in-`Mods=`-wins and alphabetical-first are all falsified — **M**,
   n = 2 permutations of the same bodies plus x121's independent kills, over 4 mod bodies
   (`testing/artifacts/x125-20260911-042055/platform-order2.json` → `phases.O1`,
   `verdicts.P20`). The sort key is the **stored script path** (`ScriptManager$38.compare` and
   `ScriptManager.searchFolders`, **C**, read in [item-overrides.md](item-overrides.md), which
   owns this row). What no boot separates is sort-by-**id** from sort-by-**path** — or from
   folder name or `mod.info` display name: all four sort identically in every boot. The check
   is a mod whose id sorts last while its script file sorts first. Not run. For the frozen
   profiles: `testing/profiles/x12-overrides.toml`'s comment that "`Mods=` order is LOAD order,
   and it is load-bearing here" is now known **wrong for script bodies**; `Mods=` order still
   governs the loader's own `loading <id>` lines.
2. **The CleanUI × `triggerEvent` two-order boot**, carried from
   [`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md)
   § Compatibility notes: CleanUI's live tree on 42.20.4 is `42.19/`, which does ship the
   fork, so the collision is live and the runtime half stays **C**.
3. **The server→client item-modData direction.** Slice 12 measured the player-modData
   directions; item modData across the same hop is untested.

## Sources

- **Measured runs (slice 12, 2026-09-11), the artifacts every M row above cites:**
  [`x121-20260911-030023`](../../testing/artifacts/x121-20260911-030023/platform-overrides.json)
  (overrides / eat hook / nutrient),
  [`x122-20260911-032326`](../../testing/artifacts/x122-20260911-032326/platform-loader.json)
  (the loader),
  [`x123-20260911-034426`](../../testing/artifacts/x123-20260911-034426/platform-folder.json)
  (boot **a**, folder drift, and boot **b**, run id `x123b-20260911-034500`, the requested-id
  discriminator, under `boots.common_id`),
  [`x124-20260911-035819`](../../testing/artifacts/x124-20260911-035819/platform-order.json)
  (script-body order) and
  [`x125-20260911-042055`](../../testing/artifacts/x125-20260911-042055/platform-order2.json)
  (the ordering discriminator, cited in § Inputs for the wall map and for mod F's second boot;
  the rule itself is [item-overrides.md](item-overrides.md)'s row),
  [`x126-20260911-045205`](../../testing/artifacts/x126-20260911-045205/platform-pcall.json)
  (the nil-`pcall` probe, cited in § Inputs for the wall map and mod G's row; the rule text is
  [lua-api.md](lua-api.md)'s and [patterns.md](patterns.md)'s — note the run's citable-claims
  file first named its keys as `readings.*` / `verdicts.P21`, which the artifact does not carry; its
  § Corrections (2026-09-11) supersede them with the artifact's keys, `phases.reads.<side>.values` and `verdicts.P21_client` / `verdicts.P21_server`); and
  [`td3-20260911-001948`](../../testing/artifacts/td3-20260911-001948/teardown-autocook.json)
  → `loading_lines`, the one `common/`-only corpus mod that has booted (§ 2). **Not committed:**
  § 3's three empty `overrides` tails are read from `testing/runs/x124-20260911-035819/`'s
  server and client console logs, which `.gitignore:44` excludes; the artifact holds one of the
  three. Earlier runs cited by their owning docs, not re-graded here:
  `td1-20260910-192457`, `td1b-20260910-202029`, `td2-20260910-231655`, `td3`'s merge-rule
  rows, `exp01`–`exp03`, spike S6.
- **Jar (C), 42.20.4 `b0bbce05d5`, dumped 2026-09-11:** `zombie/ZomboidFileSystem`
  (`loadMods`, `loadModAndRequired`, `loadModsAux`, `loadMod`, `getModDir`, `setModIdToDir`,
  `getAllModFolders`, `getAllModFoldersAux`, `getModVersionDirName`,
  `getGameVersionIntFromName`, `getModInfoForDir`, `getAbsolutePath`, `searchForModInfo`),
  `zombie/gameStates/ChooseGameInfo` (`getModDetails`, `getAvailableModDetails`,
  `readModInfo`, `readModInfoAux`, `<clinit>`) and `ChooseGameInfo$Mod` (`<init>`,
  `isAvailable`, `isAvailableSelf`, `isAvailableRequired`), `zombie/Lua/LuaManager.LoadDirBase`,
  `zombie/core/Translator` (`tryFillMapFromFile`, `tryFillMapFromMods`, `getTextInternal`,
  `getDisplayItemName`, `readModTranslation`). Toolchain: `C:\Users\Angus\pz-b42`
  (`./pz.sh dump|methods|refs`) plus a constant-pool read for the string literals.
- **Vanilla Lua (C):** `media/lua/client/OptionScreens/ModSelector/ModLoadOrderPanel.lua`,
  `ModOrderListBox.lua`, `ModSelectorModel.lua`, `ModInfoPanelParam.lua`,
  `ModInfoPanelInteractionParam.lua` — the only readers of `loadModAfter` / `loadModBefore` /
  `incompatible` / `versionMin` / `versionMax`.
- **Corpus (C):** `python tools/mod_lint.py` over the 230 installed workshop mod folders,
  swept 2026-09-11 04:27 (84 findings: 3 ERROR, 30 WARN, 51 INFO; 83 after the 04:47 workshop change recorded in § 7); `data/mod-inventory.json`; the
  `mod.info` key census and the lint-vs-engine chain comparison of § Discrepancies 1, both
  computed the same day against the read-only workshop tree.
- **Wiki (W):** [`../../references/wiki-mirrors/mod-structure.md`](../../references/wiki-mirrors/mod-structure.md),
  page version 42.20.0, fetched 2026-09-10.
- **Neighbouring docs:** [patterns.md](patterns.md) (KEEP 10/11, FILTER 10/11, the measured MP
  sync tables), [README.md](README.md) (hard-won platform facts),
  [item-overrides.md](item-overrides.md) (the item pass and the script-body order),
  [lua-api.md](lua-api.md) (the Lua surface),
  [`../mods-survey/teardowns/autocook.md`](../mods-survey/teardowns/autocook.md) (the four
  merge-rule jar sites),
  [`../mods-survey/teardowns/longtermpreservation4220.md`](../mods-survey/teardowns/longtermpreservation4220.md)
  (the empty-tail `overrides` line),
  [`../testing/profiles.md`](../testing/profiles.md) (open questions 1 and 6, both closed by
  § 2 and § 4), [`../vanilla/eating-pipeline.md`](../vanilla/eating-pipeline.md),
  [`../vanilla/food-item-model.md`](../vanilla/food-item-model.md) and
  [`../vanilla/body-stats.md`](../vanilla/body-stats.md) (the `updateWeight` client skip
  re-quoted in § Inputs for the wall map).
- **Tooling:** `tools/mod_lint.py` (the nine rules; `info_chain` and the `mod-info-place`
  WARN reworded in this slice's commit), `testing/pzt/mods.py` `mod_id_of` and
  `testing/tests/test_mods_resolution.py` (the second reader, which shares `info_chain`'s
  superset model and is **not** changed here), `tools/doc_lint.py`.
