# Coverage part — G1b (`docs/vanilla/food-item-model.md`)

Sub-block `#0201–#0450`; written `#0201–#0389` (189 rows, 61 ids left). Candidates file:
`.superpowers/sdd/restructure-1-register/candidates-G1b.tsv` (275 candidates: 239 table rows, 36 graded paragraphs).

### docs/vanilla/food-item-model.md

- § Food item model & lifecycle (the title block) — candidates 2 → rows: none; dropped: 2 (both are the `Evidence grades:` legend, which states no fact about the game — legend, no rows, per harvest-amendments § 5)
- § Summary — candidates 0 → rows: none (the five numbered points restate §§ The three state axes, Aging, Cooking, Evolved recipes and MP behaviour; every fact is harvested in its own section)
- § The three state axes — candidates 5 → rows #0201–#0210, #0328
  - the 3-row axis table is one row per axis (#0201 age, #0202 cooking, #0203 freezing): the table's own anchor pairs stored state with derived predicate, so each row is one reading of one class dump
  - the cross-axis paragraph (`:52`) is #0204, written once for both the coupling sentence here and the burnt short-circuit sentence at `:256`
  - the two-dead-setters blockquote (`:55–:70`) is #0205 (`setRotten` writes an unread field), #0206 (`isRotten()` derives from `age`, measured), #0207 (`setFrozen` undone on a server), #0208 (it sticks on a client, with the two client-side routes into `updateAge`), #0209 (`rotItem` sets both), #0210 (the working routes, a `rule` row) and #0328 (the server-gated container hooks, shared with § MP behaviour)
- § Key reference — all 114 script keys — candidates 118 → rows #0211–#0218, #0243, #0266–#0267, #0269, #0273, #0286, #0296, #0306–#0307, #0318, #0320, #0324
  - the 114 table candidates collapse into the one `table` row #0215 (the page carries the table verbatim under `facts/food-item-model.md#script-keys`), per the task brief
  - exceptions lifted out because the prose singles them out: #0217 `IsWaterSource` and #0218 `RainFactor` (the two dead keys), #0306 `Packaged` and #0307 `CannedFood` (parsed but unread on the instance — written once under § Packaging), #0318 `Poison` and #0320 `UseForPoison` (no Java and no vanilla-Lua reader — written once under § Poison), #0324 (`InstanceItem`'s ÷100 scale and the `CantBeFrozen` inversion — written once under § Code map)
  - the `C+M` keys' measured surprises are the measured rows of the later sections and are not repeated here: #0243 `ReplaceOnRotten`, #0266 `ReplaceOnCooked`, #0267 `RemoveNegativeEffectOnCooked`, #0269 `BadInMicrowave`, #0273 `GoodHot`/`BadCold`, #0286 `EvolvedRecipe`, #0296 `Spice`
  - the loader prose (`:74–:80`, `:215–:217`) is #0211–#0214, owned by `platform/loader-and-scripts.md` because the parser holds for every item type, not only food (placement rule, procedure § 4); the file-level block and line counts are #0216 on `reference/datasets.md#counts`
- § Aging — candidates 35 → rows #0204, #0219–#0255
  - the formula block (`:221–:254`) is the one `order` row #0219, per the task brief
  - the 13-row constants table is #0220–#0234 (`C+M` cells written as one row with two pointers: #0220 the rate, #0222 the frozen multiplier, #0231 the `frozen` flip points)
  - the 6-row container-temperature table is kept together as one row (#0237): it is the branch ladder of one method read off one dump, not a dataset table
  - the 4-row measured getter table is #0246 (macros identical at four ages), #0247 (stored against read-time hunger) and #0248 (the stale band) — three different sentences off one run key
  - the 6-row measured rate table is #0220, #0222, #0231, #0249, #0250 and #0251; #0251 is the thaw-rate `open` row, written once for this table row and for § Open questions 2, bound `uncommitted: exp02-20260910-025434 …`, per the task brief
  - paragraphs: `:257` → #0204; `:280` → #0234; `:305` → #0238–#0240; `:312` → #0243–#0244; `:349` and `:350` → #0254 (rot is a view, not a mutation) and #0255 (the mod consequence, bound `inference`)
- § Cooking — candidates 24 → rows #0256–#0278
  - the cook block (`:359–:391`) is the one `order` row #0257, per the task brief
  - the 18-row key/accessor/constant table is #0258–#0275; #0275 merges the stove ramp, its arithmetic 60-degree threshold and the microwave jump into one row because the source gives no bytecode offset for the getter
  - the 4-row measured step table is #0261–#0264 (rate, residual factor, cook transition, burn transition) plus the fixture row #0276
  - paragraphs: `:432` → #0261, #0262, #0277 (cooking leaves stored nutrition alone); `:441` → #0278 (`heat` cannot be pinned)
- § Evolved recipes — candidates 25 → rows #0279–#0305; superseded: #0305 (-> #0293)
  - the summation block (`:460–:478`) is the one `order` row #0283
  - the 11-row term table is #0286–#0300; #0289 (the 17 over-asking keys across 59 of 6 881 dataset rows) is owned by `reference/datasets.md#counts`
  - the 11-row measured table is #0301–#0304 plus the measured halves of #0290, #0291, #0292 and #0295
  - the correction blockquote (`:523–:528`) is the `superseded` row #0305 (the plan notes' `1.667×` statement with its own pointer) with successor #0293
- § Packaging, cans and `ReplaceOnUse` — candidates 7 → rows #0306–#0316; superseded: #0313 (-> #0312)
  - the 6-row mechanism table is #0306–#0311; the counts are split out as #0312 (the five re-counted numbers), #0314 (the opening-recipe and threshold distribution) and #0315 (the `Packaged` against `DaysFresh` split and the 225 never-ageing blocks), all on `reference/datasets.md#counts`
  - the re-count parenthetical (`:547–:551`) is the `superseded` row #0313 (the plan notes' 129 / 22 / 89) with successor #0312
  - the `:545` paragraph is #0315 and the `rule` row #0316 (key off the sentinel, never off `isPackaged()`)
- § Poison — candidates 5 → rows #0317–#0322
  - the 4-row key table is #0317–#0320; the closing paragraph is #0321 (the poison transfer and its side effects) and #0322 (the sandbox gate, with both Lua sites re-located)
- § Code map — candidates 17 → rows #0323–#0327, #0335
  - the 17 table candidates collapse into the one `table` row #0323, a field-list-shaped navigation table whose every other row restates a mechanism harvested in its own section
  - lifted out because no other section carries them: #0324 (`InstanceItem`'s scale and inversion), #0325 (what actually calls `InventoryItem.update()`), #0326 (the one Lua-to-Java bridge into the summation), #0327 (the three context-menu sites); #0335 is the packet-field count, written once for this cell and for § MP behaviour
- § MP behaviour — candidates 3 → rows #0242, #0245, #0328–#0338, #0381
  - `:605` → #0328–#0331 plus #0242 and #0245, which are written once and carry both § Aging and § MP behaviour as sources
  - `:613` → #0332–#0334
  - `:641` → #0338: the plan notes' 39-entry enumeration reaches the same total through two offsetting grouping differences, so it is a reconciliation, not a dated correction, and no `superseded` row is written for it
  - the ungraded prose at `:615–:633` supplies #0335 (43 fields, 39 item-state values, the two presence flags), #0336 (`isCustomName` is ordinary state) and #0337 (the receiver applies 40 of 43); `cooked`'s unsettled standing is the `open` row #0381
- § A zero-valued packet field can arrive carrying another item's value — candidates 21 → rows #0339–#0363; unverified: #0357
  - the 12-row per-field table collapses into the one `table` row #0349 plus one row per measured desync — #0350 `age`, #0351 `calories`, #0352 `burnt`, #0353 `cookingTime`, #0354 `heat`, #0355 the Cooking perk — per the task brief; the code-only rows (`cooked`, `offAge`/`offAgeMax`/`freezingTime`/`lastAged`, `frozen`, the macros, the packet-carried group, the `rotten` field) stay inside #0349
  - the cached-packet leak mechanism is #0342–#0345 on `platform/mp-model.md#cached-packet`, per the task brief; the packet's own field contract stays on `facts/wire-packets.md`
  - the 6-row guard table carries no `Ev` column and so produced no candidate; it is the `table` row #0340
  - paragraphs: `:667` → #0344, #0345; `:684` → #0346, #0347; `:691` → #0348 (the measured cross-item leak); `:716` → #0356, #0357 (the `unverified` rule row, bound `uncommitted: exp02-20260910-025434 …`); `:726` → #0358, #0359; `:729` → #0360; `:731` → #0361; `:737` → #0362; `:743` → #0363
- § Discrepancies vs the wiki — candidates 10 → rows #0364–#0374
  - one `contradiction` row per mirror row, claim = the code-side fact, a `wiki:` pointer for the mirror and the mirror's words in the bound; rot facts are owned by `facts/spoilage.md#walls` (#0364, #0365, #0366, #0367, #0372), evolved-recipe facts by `facts/cooking-and-recipes.md#walls` (#0368–#0371) and the script-value fact by `facts/food-item-model.md#walls` (#0373)
  - rows 3, 7 and 10 confirm the mirror rather than contradicting it; they are still `contradiction` rows per the task brief, with the bound reading `mirror right:` instead of `mirror wrong:`
  - the closing paragraph (`:762–:765`, no `Ev` marker and so no candidate) is the `bound` row #0374 on `reference/tools.md#wiki-mirror`
- § Open questions — candidates 3 → rows #0251, #0375–#0388
  - `:777` → #0375 (the 1.5 % gap); `:795` → #0376 (the breadth of the packet leak); `:835` → #0386 (the threshold counts), #0387 (`item RatKing`) and the `open` row #0388
  - the nine remaining numbered questions carry no inline grade marker and so produced no candidate; each is written as an `open` row anyway: #0251 (thaw rate, shared with § Aging), #0377 (container multipliers), #0378 (single-player aging), #0379 (the syncing aging call), #0380 (client rot display cadence), #0381 (`cooked` is C not M, shared with § MP behaviour), #0382 (enum labels), #0383 (vestigial fields), #0384 and #0385 (the two evolved-recipe corners; #0385 is X9b and is owned by `areas/open-questions.md#x9b`)
- § Sources — candidates 0 → rows #0389 (the run's artifact carries no fixture or build key — a `bound` row on `platform/harness.md#artifacts-discipline`); the rest of the section is a source list and carries no claim of its own

## Anchors proposed

- `facts/food-item-model.md#code-map` — the code map: the 17 classes, methods and Lua sites that carry the food item model and the role of each, as one table (the `table` row #0323); the anchor plan gives `facts/food-item-model.md` no home for a navigation table

## Totals

Rows: **189**, `#0201`–`#0389`, contiguous.

By kind: `mechanism` 135 · `open` 13 · `count` 11 · `contradiction` 10 · `rule` 7 · `bound` 6 · `table` 4 · `order` 3.

By grade: `C` 138 · `M` 50 · `W` 1.

By status: `settled` 173 · `open` 13 · `superseded` 2 · `unverified` 1.

By owner page: `facts/spoilage.md` 57 · `facts/cooking-and-recipes.md` 55 · `facts/food-item-model.md` 23 · `facts/wire-packets.md` 20 · `platform/mp-model.md` 15 · `reference/datasets.md` 7 · `platform/loader-and-scripts.md` 4 · `platform/harness.md` 2 · `areas/item-pass.md` 1 · `areas/open-questions.md` 1 · `platform/lua-platform.md` 1 · `reference/tools.md` 1 · (no owner, both `superseded`) 2.

Candidates accounted for: **275** = harvested 273 (of which 143 collapse into the three `table` rows #0215, #0323 and #0349, and 6 are kept together as the one container-temperature ladder row #0237) + dropped 2 (the two `Evidence grades:` legend lines). Superseded rows: 2 (#0305, #0313), both written from correction sites inside harvested candidates. Unverified rows: 1 (#0357). No candidate is left unaccounted.
