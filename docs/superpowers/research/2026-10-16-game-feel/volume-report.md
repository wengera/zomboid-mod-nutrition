# Fullness between weight and volume: the β harvest

Harvest for the game-feel outline (`docs/superpowers/specs/2026-10-16-game-feel-outline.md`, Workstream A item 2): stomach fill = weight + β × (plate volume − weight), with weight in grams and volume in millilitres. The mod's capacities are in grams of water (730 g soft, S1250; 1100 g hard, S1253), so a food with 1 mL/g reads the same at any β.

The register already holds most of the volume literature. Those rows are cited here and are not duplicated:
- S1233 (Rolls 1998, milk drinks of 300, 450 and 600 mL at equal energy);
- S1483 (Rolls 2000, the same shakes made bigger with air at equal weight);
- S1484 (Osterholt 2007, a more or less aerated snack);
- S1485 (Murray 2015, MRI of whipped foams);
- S1231 (Rolls 1999, soup against a casserole with water);
- S1465 (Himaya and Louis-Sylvestre 1998, chunky against strained soup);
- S1466 (Flood and Rolls 2007, soup forms);
- S1468 (Rolls 2004, salad by energy density and portion);
- S1471 (Rouhani 2017, pooled energy density);
- S1472 and S1473 (energy density over days);
- S1226 (Holt 1995, the satiety index tracking serving weight);
- S1232 (Marciani 2012, gastric sieving);
- S1357 (Marciani 2001, fullness linear in gastric volume);
- S1234 and S1235 (MRI liquid meals);
- S1250 and S1253 (the capacities);
- S1481 and S1482 (balloon distension).

The part file `.superpowers/sdd/game-feel-research/volume-part.tsv` adds seven rows, S13.1 to S13.7. Five are settled and two are open.

The brief's "Rolls 2004, popcorn against potato chips" was not found as a Rolls paper. The Rolls 2004 study in the register is the salad study (S1468). The popcorn-against-chips trial is Nguyen 2012 (S13.1).

## 1. Volume at matched energy

Three kinds of evidence move volume while holding energy fixed.

**Volume with weight (water added).** Rolls 1998 (S1233) gave 2088 kJ milk drinks at 300, 450 and 600 mL. Lunch intake fell by 560 kJ from 300 to 600 mL: 5263 − 4703, with the preload's energy constant. That is 17.6 % of the 300 mL lunch (5263 − 2088 = 3175 kJ).

Rolls 2000 says in its background that the earlier volume work added water. So the extra 300 mL there was also about 300 g of weight. That makes it the weight-and-volume arm.

Bell 2003 (S13.2) found the same direction for sensory-specific satiety. Doubling volume at equal energy lowered pleasantness, and doubling energy at equal volume added nothing.

**Volume without weight (air, liquids).** Rolls 2000 (S1483) used shakes of equal weight and equal energy, made 300, 450 or 600 mL by whipping in air. Lunch fell by 402 kJ (3368 to 2966; 11.9 %).

Murray 2015 (S1485) shows by MRI why the air can count: a whipped foam enters the stomach as foam and raises gastric volume. A stable foam stays there longer.

**Volume without weight (air, chewed solids).** Osterholt 2007 (S1484) used a snack at 5.7 kcal/g, aerated to 1.00 or 0.45 kcal/mL (5.7 or 12.7 mL/g). People ate 21 % less weight of the airier version. Their volume eaten was 73 % greater, and their hunger and fullness did not differ.

Rolls 2014 (S13.7) crushed wheat flakes to 80, 60 or 40 % of their volume at the same weight. People poured a smaller volume but a greater weight of the crushed cereal, judged the calories alike, and ate 34 % more energy at that breakfast. Volume set the portion taken by eye; no later meal was measured.

Nguyen 2012 (S13.1) compared 6 cups (27 g, 100 kcal) of popcorn with 1 cup (28 g, 150 kcal) of chips: near-equal weight and about 6 times the volume. Six cups of popcorn gave less hunger than every other condition. Read from the combined intakes minus each snack's energy (a reading, not reported as such), the meal after the snack fell by 77 kcal after 6 cups of popcorn and 63 kcal after chips, against control. The energy differs between the arms, and the intake SDs are near 280 kcal.

**Weight is the basis the evidence already supports.** People eat a constant weight of food across energy densities (Bell 1998, S1472). The satiety index tracks serving weight, r = 0.66 (S1226). Water inside a food satiates where the same water drunk beside it does not (S1231, S1465).

The mod's mass-based fill already captures this. β only adds what volume does beyond weight.

## 2. What survives chewing

- **No measurement located (open row S13.5).** No study measures how much of a chewed porous solid's plate volume survives into the bolus or the stomach: the voids between florets, the air cells of bread crumb, the expansion of popcorn. The bread-mastication studies (Le Bleis 2013; Pentikäinen 2014) measure particle size, moisture and consistency, not bolus porosity.
- **Physical reasoning, not a row.** A swallowed bolus is a saliva-wetted paste, so the packing voids of a plate of broccoli are gone. Most crumb air in bread or popcorn is crushed out.
- **The stomach tracks meal volume plus secretion, sub-proportionally.** For liquid meals, gastric content volume is meal plus secretion. Its ratio to meal volume shrinks as the meal grows (Kwiatek 2009, S13.3). Fullness is linear in total gastric volume for nutrient meals (S1357).
- **Gastric air is shown for foams only.** The MRI evidence that ingested air stays in the stomach is for whipped liquid foams (S1485).
- **So the effect of chewed bulk is mainly oral and visual.** It acts through satiation (S1484: the airy snack ended eating at a lower weight), through the portion taken by eye (S13.7: crushed cereal, poured by volume, raised the weight eaten) and through sensory-specific satiety (S13.2), not through gastric fill.
- **No satiety preload trial for chewed solids (open row S13.6).** No trial varies a chewed solid's volume at matched weight and energy and measures later intake. Rolls 2014 (S13.7) varies it at constant weight but measures the self-served portion at the same meal.

## 3. Estimating β

All three estimates assume intake suppression is linear in fill, so one gram of fill counts the same in each arm. Each is a reading of register values, not a register row. The β the mod ships is a game choice resting on the rows named.

**(a) Liquid foam, Rolls 2000 against Rolls 1998** (S1483 over S1233; same lab, same 2088 kJ preload, same 300 to 600 mL step).
- In 1998 the extra 300 mL arrived as about 300 g, so Δfill = 300 g and the response was 560 kJ.
- In 2000 it arrived as air, so Δfill = β × 300 and the response was 402 kJ.
- β_foam = 402 / 560 = **0.72**, or 0.68 on the percentage reductions (11.9 % / 17.6 %).
- Caveats: two different groups of lean men (20 and 28), and the 1998 drinks' weight is inferred from the 2000 paper's background.

**(b) Chewed aerated snack, Osterholt 2007** (S1484). This assumes eating stopped at equal fill, which the equal hunger and fullness ratings support.
- Airier version: 0.79 × (1 + β × (12.67 − 1)).
- Denser version: 1 × (1 + β × (5.70 − 1)).
- Setting them equal: 0.79 + 9.22 β = 1 + 4.70 β, so **β = 0.21 / 4.52 = 0.046**.

**(c) Popcorn against chips, Nguyen 2012** (S13.1). The reductions in the later meal are each snack's combined intake, minus the snack's energy, minus control's 716:
- 1 cup popcorn: −33 kcal;
- 6 cups popcorn: −77 kcal;
- 1 cup chips: −63 kcal.

Volumes are 1 cup = 236.6 mL and 6 cups = 1419.5 mL. Fitting the 6-cup-against-chips ratio gives β = 0.006, and the 1-cup-against-chips ratio gives β = 0.087. Both rest on means whose SDs are about four times the differences, with an energy confound (100 against 150 kcal). They bound β as small, and the point value carries no weight.

**Recommendation.**
- **β = 0.05 for chewed solid food, range 0 to 0.1.** That is (b)'s point, with (c)'s spread.
- **0.15 is the highest defensible game choice.** Above it, airy foods become absurd: 22 g of popcorn would read as 120 g at 0.15 and 476 g at 0.7.
- **A separate β_foam ≈ 0.7 (range 0.5 to 1.0) only for whipped or aerated liquids.** The mod maps none today. Carbonated water's gas is outside this evidence.
- **Apply β to the satiety mass, not the physical stomach.** Because the chewed-bulk effect is satiation rather than gastric volume (section 2), the closest fit is β on the satiety mass (`K.stomach.satietyMass`), leaving the physical fill and the 730 and 1100 g caps on mass. If the owner wants one fill, β = 0.05 moves the caps negligibly for all but the airiest foods.
- **S13.7 does not move β.** Rolls 2014 measured how much people pour and eat when the same weight looks smaller, a portion-selection effect, not the fullness a fixed amount gives. It supports reading chewed bulk as a cue for the eye and the satiety mass, not gastric fill, and gives no number for β. The recommendation stands.
- **β will not make broccoli fill much more.** Cooked broccoli has only 0.52 mL/g of excess volume, so its fill comes almost entirely from its weight, which the mod already counts. Bread, popcorn, puffed cereal and leaves are where β shows. Raw chopped broccoli, which the mod's Broccoli item maps to, has 1.60 mL/g of excess and gains 8 % at β = 0.05.

## 4. The volume data source

**The source: SR Legacy food_portion (S13.4).** It is in `tools/.fdc/FoodData_Central_sr_legacy_food_csv_2018-04.zip`, already fetched and hashed by `tools/fdc_fetch.py`. Each row of `food_portion.csv` carries `fdc_id`, `amount`, `modifier` (for example `cup, chopped` or `cup cubes`), `measure_unit_id` (9999, "undetermined", on every one of the 14449 rows, so the unit lives in the modifier text) and `gram_weight`.

**Coverage.** Of the 361 FDC ids `data/food-nutrients.json` maps, 346 carry some portion and 201 carry a volume measure (cup, fl oz, tbsp, tsp, mL, litre, pint or quart).

**Proposed mapping.**
1. **Add the column.** Add `ml_per_g` to the mapping CSVs under `data/food-nutrient-map/`, with `volume_source` beside it. A value is either `fdc_portion:<seq_num>`, read from the record's own `fdc_id`, or `fdc_portion:<fdc_id>:<seq_num>`, read from a state-matched id.
2. **Compute it.** `ml_per_g = amount × unit_mL / gram_weight`, with 1 cup = 236.588 mL, 1 fl oz = 29.574 mL, 1 tbsp = 14.787 mL and 1 tsp = 4.929 mL. Parse the count out of the modifier. One water row reads `serving 8 fl oz` at 237 g; a naive parse gives 0.125 mL/g where it should give 1.0.
3. **Prefer the plain cup.** Choose the cut as served (chopped vegetables, `not packed` pasta). Avoid `crumbs` and `crushed`.
4. **Match the state.** Some items are mapped to a raw or dry id but eaten cooked, such as `WaterPotPasta` (dry pasta, 2.6 mL/g) and `WaterPotRice` (raw rice, 1.28 mL/g). Their volume must come from the cooked id: pasta cooked 169737, 1 cup spaghetti not packed = 124 g, 1.91 mL/g; rice cooked 168878, 1 cup = 158 g, 1.50 mL/g.
5. **Fill the gaps.** Fluids, and records whose food has no volume measure (for example plain potato chips, 169677, and French bread, 172675), take 1.0 or a labelled family judgement.
6. **Keep the dataset regenerable.** `tools/food_nutrients.py --build` would carry `ml_per_g` through to `per_100g`-adjacent cells and the generated Lua, as it does every mapping cell. Nothing is edited by hand.

**A cup is a packing volume.** It includes the air between pieces and varies with the cut: bread is 5.26 mL/g as crumbs and 6.76 mL/g as cubes. That is the plate volume the outline asks for, and section 2 explains why a small β is right for it.

## 5. Worked examples

All cases use fill = w + β (V − w), at the recommended β = 0.05, the game-choice ceiling 0.15 and the foam value 0.7 for contrast.

| food | w (g) | mL/g (source) | V (mL) | fill at β 0.05 | at 0.15 | at 0.7 |
|---|---|---|---|---|---|---|
| 1 kg boiled broccoli (169967, the mod's CannedBroccoli) | 1000 | 1.517 (0.5 cup chopped = 78 g) | 1517 | 1026 | 1077 | 1362 |
| 1 kg raw broccoli, the mod's Broccoli (170379) | 1000 | 2.600 (1 cup chopped = 91 g) | 2600 | 1080 | 1240 | 2120 |
| a can of bolognese, the mod's 540 g (172099) | 540 | 0.962 (1 cup = 246 g) | 519 | 539 | 537 | 526 |
| a slice of white bread (174924) | 29 | 6.76 (1 cup cubes = 35 g) | 196 | 37 | 54 | 146 |
| the mod's BreadSlices item (174924) | 66.7 | 6.76 | 451 | 86 | 124 | 336 |
| the mod's Popcorn item (173141) | 22.4 | 29.95 (1 cup = 7.9 g) | 671 | 55 | 120 | 476 |
| 500 mL of water (173647) | 500 | 1.000 (1 L = 1000 g) | 500 | 500 | 500 | 500 |

- **Broccoli** is already 1.4 times the soft cap by weight; β changes it by 3 % at 0.05.
- **Bolognese** is denser than water, so its fill falls slightly below its weight.
- **Bread** gains 29 % at β = 0.05.
- **Popcorn** gains about 2.4 times.
- **Water** is unchanged at every β.
