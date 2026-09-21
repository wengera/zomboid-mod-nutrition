# Coverage part G1d — the food and recipe datasets

Sources: `docs/vanilla/food-dataset-notes.md` (80 candidates) and `docs/vanilla/recipes-dataset-notes.md` (147 candidates); 227 candidates in all, from `.superpowers/sdd/restructure-1-register/candidates-G1d.tsv`. Rows `#0601`–`#0785`, contiguous.

A row that carries two `source` cells appears on both sections' lines; it is one row and is counted once in `## Totals`. "collapsed into" means the candidate's content is carried by a row minted elsewhere (a dataset table collapsed to one `table` row, a code-map pointer folded into the mechanism row it points at, a question-table answer folded into the section that answers it).

## The group's placement rules, as applied

- Per-food and per-recipe values are not rows: the dataset is the pointer (`data:data/food-items.json 2026-09-10`). A value enters only as a worked example, a control or a measured subject — `Base.Pop2`, `Base.RatKing`, `Base.Icecream`, the six named craft deltas.
- The datasets' fidelity facts are rows about the game. `facts/food-item-model.md#dataset-fidelity` (proposed) holds 13: the live census, the ten spot checks by check type, the absent-against-zero read-backs, the fluid join and the three-drink probe. `facts/cooking-and-recipes.md#dataset-fidelity` (proposed) holds only 5 — `#0679`, `#0680`, `#0726`, `#0727`, `#0762` — because the per-use probe's four measured rows (`#0709`–`#0712`) sit with `#0713` on the existing `facts/cooking-and-recipes.md#uses`, whose anchor-plan wording is "recipe IO and the uses-not-items rule, measured per use".
- The 31 craft deltas are one `table` row (`#0743`) plus one row per named exception (`#0744`–`#0749`, `#0705`).
- Column semantics, the four `kind` buckets and the CSV/JSON split are `count` / `mechanism` rows on `reference/datasets.md`, with `snapshot 2026-09-10` as the bound's first token on every count off the dated scan.
- Where the brief and the anchor plan differ, the anchor plan wins (harvest amendments § 1): the four `kind` buckets and the selection rule went to `reference/datasets.md#kinds` and the CSV/JSON split to `#schemas` rather than to `#columns`, both being exact anchor-plan matches. The per-litre chain went to `facts/eating-pipeline.md#fluid-path` for the same reason ("the drink path and the per-litre chain"); the measured drink readings stayed on `facts/food-item-model.md#dataset-fidelity`. The `ReplaceOn*` links are owned by `facts/spoilage.md#sealed` (amendment § 1, not `#replace-on-rotten`).
- Pointer forms (controller ruling R16): a single-line shipped-script or translation fact is `lua:<path relative to the game media/ directory>:<line> "<anchor text>"`, every line re-located by content in the read-only 42.20.4 install before it was quoted; `data:` is kept for whole-file corpus counts over `media/scripts/**` and for the generated datasets under `data/`.

---

### docs/vanilla/food-dataset-notes.md

- § preamble (the H1 block, lines 1–16) — candidates 4 → rows #0601; dropped: 3 (lines 4–6 are the evidence-grade legend, no rows)
- § Summary — candidates 2 → rows #0601–#0604 (both candidate lines are Summary item 5 and fold into #0601; #0602–#0604 come from Summary items 1–3, which carry no grade idiom and so are not candidates)
- § The five questions, answered — candidates 5 → rows #0605, #0606, #0607, #0608, #0609 (Q1 also feeds #0618 and #0640, Q4 also feeds #0613); collapsed into: 1 (Q3's per-litre answer → #0623, #0628–#0633)
- § The four buckets and the selection rule — candidates 5 → rows #0610, #0611, #0612, #0613, #0614, #0615, #0616, #0617 (#0610 comes from the section's intro prose, lines 60–62; the live-census half of the four counts is #0608)
- § Empty is not zero — candidates 5 → rows #0618, #0619, #0620, #0621 (the 61-empty-container count is #0627)
- § nutrition_source, nutrition_basis, and the fluid join — candidates 5 → rows #0622, #0623, #0624, #0625, #0626, #0627 (the 14 part-fill containers are #0658)
- § Per litre, not per item — candidates 11 → rows #0628, #0629, #0630, #0631, #0632, #0633, #0634, #0635, #0636, #0637, #0638
- § The CSV/JSON split — candidates 1 → rows #0617, #0639, #0640, #0641
- § Code map — candidates 16 → rows #0642, #0643, #0644, #0645, #0630; collapsed into: 8 (food.txt → #0611; drainable.txt → #0612; the 15 container files → #0613; the three fluid files → #0614; `ScriptManager` census route → #0608; `Item.getItemType` → #0616; `FluidDefinitionScript` loader and getters → #0628, #0629, #0654; `IsoGameCharacter.DrinkFluid` → #0633, #0649); dropped: 4 (the scanner's build half — the selection rule is #0610 and the joins #0622–#0627, no fact of its own; `Item.DoParam` / `Item.InstanceItem` — routed to food-item-model.md and explicitly not re-derived here; the harness row — a command inventory owned by docs/testing/README.md; the experiments row — script pointers, no claim)
- § MP behaviour — candidates 7 → rows #0646, #0647, #0648, #0649, #0650, #0651; dropped: 2 (the server-owned-instance row and the zero-valued-packet-field row both restate food-item-model.md § MP behaviour from slice 02 and are that source's rows)
- § Discrepancies — candidates 9 → rows #0653, #0654, #0655, #0656, #0657, #0658, #0659, #0660, #0661; superseded: #0652 (-> #0623), #0662 (-> #0634); collapsed into: 1 (row 6's ten spot checks → #0609 and #0604). Sites: 6 harvested (rows 2, 3, 4, 5, 7, 8), 2 superseded (rows 1 and 9), 1 collapsed (row 6) = 9; the 2 superseded rows come from those 2 sites, one row each
- § Open questions — candidates 10 → rows #0605, #0663, #0664, #0665, #0666, #0667, #0668, #0669, #0670, #0671, #0672, #0673, #0674, #0675 (open question 4's five unit traps are #0666–#0670); dropped: 1 (the first half of "Closed by this slice" is narrative — that slice 01's open question 11 was closed; the current statements are #0634 and #0662)

File total: 80 candidate sites = 58 harvested + 10 collapsed into rows elsewhere + 2 superseded + 10 dropped + 0 unverified. Those 2 superseded sites yield the file's 2 superseded rows, `#0652` and `#0662`.

### docs/vanilla/recipes-dataset-notes.md

- § preamble (the H1 block, lines 1–17) — candidates 5 → rows #0676; dropped: 3 (lines 4–6 are the evidence-grade legend, no rows)
- § Summary — candidates 1 → rows #0676, #0677 (#0677 comes from Summary item 1, which carries no grade idiom and so is not a candidate)
- § The seven questions, answered — candidates 7 → rows #0678, #0679, #0680, #0727; collapsed into: 5 (Q1 → #0682, #0683 and the § craftRecipe rows; Q3 → #0718–#0723; Q4 → #0741, #0742, #0743, #0752, #0755; Q5 → #0728; Q7 → #0757–#0760)
- § craftRecipe — the format — candidates 11 → rows #0681, #0682, #0683, #0684, #0685, #0686, #0687, #0688, #0689, #0690, #0691 (#0681 comes from the section's intro prose, lines 63–66); collapsed into: 1 (the legacy-recipe row → #0678)
- § The IO line grammar — candidates 5 → rows #0692, #0693, #0694, #0695, #0696, #0697 (#0692 is the fenced grammar block, which is not a candidate)
- § The delta rule — what an input amount actually costs — candidates 17 → rows #0698, #0699, #0700, #0701, #0702, #0703, #0704, #0705, #0706, #0707, #0708, #0709, #0710, #0711, #0712, #0713, #0714, #0715, #0716, #0717 (#0698 comes from the delta-formula prose, lines 110–113, and #0712 from the 96-of-96 line)
- § Resolution rules — how an item reaches an evolved recipe — candidates 8 → rows #0718, #0719, #0720, #0721, #0722, #0723, #0724, #0725, #0726, #0727 (#0718 comes from the section's intro prose, lines 164–166); collapsed into: 1 (the unmatched-keys row → #0725, one reading off `meta.counts`)
- § The evolved summation — candidates 7 → rows #0729, #0730, #0731, #0732, #0733, #0734; collapsed into: 1 (the verbatim-application row → #0728)
- § The CSV/JSON split — candidates 1 → rows #0735, #0736, #0737, #0738
- § Code map — candidates 19 → rows #0645, #0739, #0740; collapsed into: 13 (`recipe_scan` craft half → #0692, #0698, #0704; evolved half → #0718, #0728, #0751; `food_scan` → #0768; `ScriptManager` lists → #0679; `Item.OnScriptsLoaded` → #0719, #0720; `Item.DoParam` → #0722; `EvolvedRecipe.addItem` → #0728–#0731; `EvolvedRecipe.Load` / `.getResultItem` → #0766, #0767; `CraftRecipe.LoadIO` → #0695; `CraftRecipeData` → #0700, #0703, #0708; `ItemUser.UseItem` → #0699, #0704, #0714; `Food` use getters → #0701; `Food.updateRotting` → #0754, #0757); dropped: 3 (`data/food-items.json` — a pointer to the joined item dataset, whose rows are food-dataset-notes'; the harness row — a command inventory owned by docs/testing/README.md; the experiments row — script pointers, no claim)
- § Plain cooking is a zero delta — MakeToast worked through — candidates 1 → rows #0741, #0742
- § The 31 resolvable craft deltas, largest |kcal| first — candidates 32 → rows #0750; collapsed into: 31 (the 31 delta rows → the `table` row #0743, with the exceptions the prose singles out as #0744 `open_mac_and_cheese`, #0745 `MakeMeatPatty`, #0746 the four corn mills, #0747 `ScoopIceCream`, #0748 the 8 `InheritFood` splits, #0749 the 3 cigarette rows and #0705 `UnpackCigarettes`' round-up)
- § The ReplaceOn* links — 3 + 8, and 152 more — candidates 6 → rows #0739, #0751, #0752, #0753, #0754, #0755, #0756, #0653 (#0751 comes from the section's intro prose, lines 327–330, and #0739 from the cooked-swap prose, lines 332–334; #0653 is the `Base.MugRed` row minted on food-dataset-notes and carrying this file as a second source)
- § MP behaviour — candidates 7 → rows #0646, #0647, #0651, #0757, #0758, #0759, #0760; dropped: 1 (the client-side-instance row restates food-item-model.md § A zero-valued packet field can arrive carrying another item's value and is that source's row)
- § Discrepancies — candidates 10 → rows #0681, #0688, #0761, #0762, #0763, #0764, #0765, #0766, #0767, #0768, #0769, #0770, #0773; superseded: #0771 (-> #0750), #0772 (-> #0743), #0774 (-> #0773), #0775 (-> #0753), #0776 (-> #0728); collapsed into: 1 (row 1's output-less recipes → #0686). Sites: 6 harvested (rows 2–7), 3 superseded (rows 8, 9, 10), 1 collapsed (row 1) = 10; the 5 superseded rows come from 4 of those sites — row 7 yields #0771 beside its current row #0770 and row 8 yields both #0772 and #0774 beside #0773
- § Open questions — candidates 10 → rows #0714, #0732, #0777, #0778, #0779, #0780, #0781, #0782, #0783, #0784, #0785

File total: 147 candidate sites = 84 harvested + 53 collapsed into rows elsewhere + 3 superseded + 7 dropped + 0 unverified. Those 3 superseded sites, plus the superseded halves of 2 harvested sites (§ Discrepancies rows 7 and 8), yield the file's 5 superseded rows: `#0771`, `#0772`, `#0774`, `#0775`, `#0776`.

---

## Anchors proposed

- `facts/food-item-model.md#dataset-fidelity` — the measured checks of `data/food-items.*` against the running game: the `ScriptManager` census on two boots, the ten spot checks by check type, the absent-against-zero read-backs, the fluid join and the three-drink per-litre probe. Named by the task brief; the anchor plan has no such anchor, and no existing `facts/food-item-model.md` anchor covers a dataset-against-game measurement.
- `facts/cooking-and-recipes.md#dataset-fidelity` — the same for `data/recipes.*` and `data/evolved-recipes.*`, five rows: the craft / evolved / legacy census (`#0679`), the ten craft spot checks (`#0680`) and their offline replay (`#0762`), and the five live evolved lists (`#0726`) with their offline set-equality (`#0727`). The per-use probe's own rows are not here: `#0709`–`#0713` sit on the existing `facts/cooking-and-recipes.md#uses`, which the anchor plan already describes as "recipe IO and the uses-not-items rule, measured per use".

No other anchor outside `docs/superpowers/plans/restructure-anchors.md` is used.

## Totals

185 rows, `#0601`–`#0785`, contiguous.

By kind: `mechanism` 86, `count` 59, `rule` 15, `open` 15, `bound` 7, `table` 2, `tool` 1.

By grade: `C` 143, `M` 42.

By status: `settled` 163, `open` 15, `superseded` 7, `unverified` 0.

By owner: `reference/datasets.md#columns` 23, `facts/cooking-and-recipes.md#type-change` 18, `facts/cooking-and-recipes.md#uses` 18, `reference/datasets.md#counts` 18, `facts/eating-pipeline.md#fluid-path` 16, `facts/food-item-model.md#dataset-fidelity` 13, `facts/cooking-and-recipes.md#evolved-join` 9, `reference/datasets.md#schemas` 9, `facts/cooking-and-recipes.md#evolved` 8, `reference/datasets.md#open` 7, `facts/cooking-and-recipes.md#open` 6, `facts/spoilage.md#sealed` 6, `reference/datasets.md#kinds` 6, `facts/cooking-and-recipes.md#dataset-fidelity` 5, `facts/cooking-and-recipes.md#walls` 3, `platform/harness.md#artifacts-discipline` 3, `reference/tools.md#food-scan` 3, `platform/harness.md#driver-rules` 2, `platform/harness.md#probes` 2, `platform/loader-and-scripts.md#craft-recipe-grammar` 2, `platform/loader-and-scripts.md#per-side-load` 2, `reference/tools.md#recipe-scan` 2, `facts/eating-pipeline.md#open` 1, `platform/lessons.md#rules` 1, `platform/loader-and-scripts.md#name-resolution` 1, `reference/tools.md#open` 1.

Candidates accounted for: 227 candidate sites = 142 harvested + 63 collapsed into rows elsewhere + 5 superseded + 17 dropped + 0 unverified. Those 5 superseded sites, plus the superseded halves of 2 harvested sites in `recipes-dataset-notes.md` § Discrepancies, give the register's 7 `superseded` rows: `#0652`, `#0662`, `#0771`, `#0772`, `#0774`, `#0775`, `#0776`.
