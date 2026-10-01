---
name: nutrition-item-pass
description: Rebalancing vanilla food items — a partial `module Base` `item` block per record of `data/food-items.json` re-basing `Calories`, `Carbohydrates`, `Proteins`, `Lipids`, `HungerChange` or `ThirstChange`, the per-key merge, the replay sorted by script path rather than `Mods=`, `template_` and mod-unique script basenames, script value types and `InvalidParameterException`, script units against instance getters, drinks and their fluids, the script checksum, or declaring the mod's own foods in its own module.
---
## Read first
- docs/areas/item-pass.md
- docs/platform/loader-and-scripts.md
- docs/facts/food-item-model.md

## Rules quoted
- Restate only the keys the pass re-bases in a partial item block: every key the block omits keeps its vanilla value, which is what lets a pass over every record of `data/food-items.json` ship minimal blocks and leave icons, models, evolved recipes and spoilage tracking upstream — measured on one float macro of one food [#1017/M/n=1].
- Ship one `module Base` block per item: per-key last-wins makes the pass robust to the replay order for every key it does not touch and contested only on the keys two mods both declare [#1057/M/n=1].
- Do not derive body order from `Mods=`: bodies replay sorted by the stored script path, so a mod's position in `Mods=` decides nothing about which body wins a key [#1055/M/n=2].
- Keep `template_` out of a script file's basename: the replay comparator pre-sorts every `template_`-prefixed basename ahead of every other file before it compares paths at all [#1233/C/C-only].
- Give the pass's script files a mod-unique basename: two mods at one relative script path lose one file's blocks entirely — a code reading, since the across-two-mods arm is unmeasured [#1050/C/C-only].
- Keep every value on a known key well formed: a malformed value raises `InvalidParameterException` and aborts the load, and a line with no equals sign dies on the split [#1188/C/C-only].
- Write every re-based value in the script's own units: the dataset carries hunger and thirst raw, as the script writes them, while an instance divides them by a hundred, and a drink row's nutrition is its fluid's per-litre figure rather than a key on the container's own block [#0323, #0626/C/snapshot, #1893, #2068/C/inference].
- Ship byte-identical script files on both sides of a multiplayer session: the gate hashes file content with every CR byte dropped, so a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only, #1231/C/C-only].
- Build a fresh instance through the `instanceItem` global to read a type's vanilla macros when no instance is at hand: the global reaches the item factory, which the exposer leaves out [#2679/C/C-only, #2680/C/C-only, #2741/C/inference].

## Also
- docs/facts/eating-pipeline.md#modifiers — what an eat does with a re-based value, and the scale between a script and an instance.
- docs/reference/datasets.md — the food dataset's columns, units and counts.
- docs/areas/packaging.md — the script files' paths and the join checksum they ship under (skill `nutrition-packaging`).
