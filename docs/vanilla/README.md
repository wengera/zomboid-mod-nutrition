# Vanilla systems — code-level maps

Everything cited to 42.20.4 code (jar via pzdis, lua, generated scripts).
Every doc ends with an **MP behavior** section.

## Documents

| Doc | Covers | Status |
|---|---|---|
| [nutrition-core.md](nutrition-core.md) | Nutrition class: calories→weight, macro effects, traits, XP gates | **seeded** from prior research; hunger + calorie-burn map TODO |
| food-item-model.md | Every nutrition-relevant Food script property (HungerChange, Calories, macros, spoilage/Age, Cooked/Rotten/Poison, FoodType, OnEat...) | TODO (P1) |
| eating-cooking.md | ISEatFoodAction pipeline, evolved recipes, cooking XP, batch cooking | TODO (P1) |
| food-sources.md | Farming/foraging/trapping/fishing/butchering yield data paths | TODO (P1; foraging partly done in pz-b42) |
| stats-moodles.md | Hunger/endurance/recovery interplay, moodle thresholds, weight traits | TODO (P1) |
| mp-sync-model.md | SyncItemFieldsPacket fields, modData transmission, client/server authority per system | TODO (P2, feeds every MP section) |

## Key already-established facts (see nutrition-core.md for citations)

- Weight moves on stored calories vs. weight-scaled thresholds; carbs/lipids
  >400/>700 multiply GAIN rate ×2/×3; protein never touches weight.
- Protein & lipid stores below −1000/−1500 halve/quarter endurance-recovery.
- `setCondition`-style java setters clamp hard — pattern repeats across
  systems; assume clamping until proven otherwise.
