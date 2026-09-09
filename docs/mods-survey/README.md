# Mod survey

Two tiers: a **broad catalog** of nutrition/food-adjacent mods (what exists,
one-line assessment, compat risk on a busy MP server), and **deep teardowns**
([template](teardown-template.md)) of the mods with the most to teach us.

## Teardowns

| Mod | Why chosen | Status |
|---|---|---|
| [ItemQuality](teardowns/itemquality.md) (Girth's Quest System module) | Per-item modded stats + the definitive MP-sync failure case study | **seeded** from prior investigation |
| [BeyondTen](teardowns/beyondten.md) | Parallel-stat architecture done right: modData reservoirs, wrapper patterns, reapply-on-event | **seeded** from prior investigation |
| LongTermPreservation4220 | Domain twin — spoilage/preservation model + item-override mechanism | queued (see [approved-modlist](approved-modlist.md)) |
| simpleStatus | Nutrition UI: read/refresh cadence | queued |
| MoodleFramework | Dependency evaluation for new-nutrient moodles | queued |
| AutoCook | Cooking-pipeline hook points | queued |
| CleanUI | Error-hygiene exemplar + food-UI territory map | queued |

**Inventory of the full approved corpus:** [approved-modlist.md](approved-modlist.md)
(230 mods scanned; dataset in `data/mod-inventory.json`). Distilled dos/don'ts:
[../modding/patterns.md](../modding/patterns.md).

Catalog pass (P3) sources: Steam Workshop search (nutrition, vitamins, thirst,
food overhaul, cooking expanded, spoilage), the 159 locally installed mods
(scan for Food item edits / Nutrition API calls), wiki Modding projects list.

## Candidate leads to chase in P3

- Workshop search terms: "nutrition", "vitamin", "malnutrition", "diet",
  "hydration", "food overhaul", "cooking overhaul", "realistic needs".
- Local install: grep workshop lua for `getNutrition\(|setCalories|Proteins`
  to find anything on the server already touching the system.
- Known adjacent from our sessions: damnlib (KI5) OnCreate patterns,
  ChuckleberryFinn mods (wrapping style, error handling), Elyon Lib
  (networking), Moodle Framework / "Moodles in lua" (UI for new stats).
