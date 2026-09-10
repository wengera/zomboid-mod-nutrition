# Vanilla systems — code-level maps

Everything cited to 42.20.4 code (jar via pzdis, lua, generated scripts).
Every doc ends with an **MP behavior** section.

## Documents

| Doc | Covers | Status |
|---|---|---|
| [eating-pipeline.md](eating-pipeline.md) | Food item → `Stats` / `Nutrition`: the `Eat` algorithm, every modifier in one table, partial eating, drinks, the sandbox toggle, `OnEat`/`EatType`/`Eattime`, eating time, MP authority | **done** — slice 01 (P1a), code map + measured matrix |
| [nutrition-core.md](nutrition-core.md) | Nutrition class: calories→weight, macro effects, store clamps, traits, XP gates | **done** — the `updateCalories` burn model moved to [body-stats.md](body-stats.md) (slice 03), which also closed this doc's `characterHaveWeightTrouble`, Nutritionist and sandbox open questions |
| [food-item-model.md](food-item-model.md) | The food item itself: all 114 `food.txt`/`drainable.txt` script keys, the aging model (fresh → stale → rotten, fridge/freezer/frozen), cooking transitions, evolved-recipe nutrition summation, packaged/canned, poison, and item-state ownership in MP | **done** — slice 02 (P1c), code map + measured lifecycle run |
| eating-cooking.md | Evolved recipes, cooking XP, batch cooking | pending — slice 06 (the recipe *dataset*). The `ISEatFoodAction` → `Eat` pipeline that was planned here lives in [eating-pipeline.md](eating-pipeline.md); the evolved-recipe *mechanism* (summation, gating, cooking XP) is in [food-item-model.md](food-item-model.md) |
| food-sources.md | Farming/foraging/trapping/fishing/butchering yield data paths | pending (foraging partly done in pz-b42) |
| [body-stats.md](body-stats.md) | The body side: the five-branch passive calorie burn, hunger/thirst decay with their sandbox and trait multipliers, the HUNGRY/THIRST/FOOD_EATEN moodle thresholds and everything they drive, the weight bands and every effect of the band traits, MP ownership per stat | **done** — slice 03 (P1b), code map + measured run `exp03-20260910-045523` (was planned as `stats-moodles.md`) |
| mp-sync-model.md | SyncItemFieldsPacket fields, modData transmission, client/server authority per system | pending — slice 12 (P2a). What is settled so far: item fields and player modData in [../testing/spikes.md](../testing/spikes.md) §S6, `Nutrition` + hunger/thirst authority in [eating-pipeline.md](eating-pipeline.md) § MP behaviour |

## Key already-established facts (see nutrition-core.md for citations)

- Weight moves on stored calories vs. weight-scaled thresholds; carbs/lipids
  >400/>700 multiply GAIN rate ×2/×3; protein never touches weight.
- The protein/lipid `getRecoveryMod` deficit penalties (below −1000/−1500) are
  **dead code**: the stores clamp at −500, so neither threshold is reachable.
  Protein has no live effect in vanilla at all (slice 03). The clamp has **no
  bypass**: the packet write path `Nutrition.load @0–@41 L217–L221` calls the
  same `setProteins` (`@13 L218`), which pins to `[−500, 1000]`
  (`setProteins @0–@21 L305–L309`), so no route into the store is unclamped
  (checked on the 42.20.4 jar, 2026-09-10; also
  [eating-pipeline.md](eating-pipeline.md) § Code map).
- `setCondition`-style java setters clamp hard — pattern repeats across
  systems; assume clamping until proven otherwise. Confirmed for nutrition in
  slice 01: calories `[-2200, 3700]`, macros `[-500, 1000]`, measured exactly.
- **Rot is a view, not a mutation** (slice 02, measured): aging writes only
  `age`/`lastAged`/`heat`/`freezingTime`, so a food item's stored macros never
  change with age — only the read-time getters do. Frozen food ages at exactly
  ×0. See [food-item-model.md](food-item-model.md).
- **Cooking skill is the one skill that touches nutrition**: an evolved recipe
  banks `macro × (1 + cookLvl/15) × share` in the dish, i.e. ×1.1667 macros per
  unit of dish hunger at Cooking 10, with ~17 % of the calories created from
  nothing (slice 02, measured).
- **`Nutrition` is server-authoritative in MP** (slice 01, measured): a
  client-side write is overwritten within a second by the 1 Hz push, and the
  eat itself completes on the server. Same for hunger and thirst. Every MP
  section in this directory should be read against
  [eating-pipeline.md](eating-pipeline.md) § MP behaviour.
- **Weight is server-only, and so are its traits** (slice 03, measured): a client
  reaches `updateWeight()` but a `GameClient.client` skip before `setWeight`
  makes it compute the delta and discard it, so `applyTraitFromWeight` never
  fires client-side. See [body-stats.md](body-stats.md) § MP behaviour.
