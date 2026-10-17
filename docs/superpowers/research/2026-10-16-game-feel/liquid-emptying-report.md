# Water drunk with or after a meal: how fast it leaves the stomach

Date: 2026-10-17. Asked by: the Plan 15 close review, finding M1 (`.superpowers/sdd/2026-10-16-plan-15-game-feel/close-review.md`): on the guide's ordinary day, a 667 kcal plate and 500 g of water reach Overfull 4.
Part file: `.superpowers/sdd/2026-10-16-plan-15-game-feel/liquid-science.tsv`, rows S16.1–S16.13 (12 settled, 1 open). The controller mints them from S2265 in file order.
Each citation was resolved against its PubMed record (title, authors, journal, volume, pages, DOI) through the E-utilities. Where only the abstract was read, the row's `range` cell says so. Three full texts were read: Großmann 2025 (PMC12320173), Cuomo 2011 (PMC3213184) and the Greifswald group's 2023 workshop slides, which give the meals of Grimm 2017 and Koziolek 2014. The full texts of Grimm 2017, Koziolek 2014, Marciani 2012 and Moore 1981 are paywalled. Collins 1991 and Siegel 1988 are scanned PDFs, and they were not read.

## 0. The answer in brief

- **Water drunk with or soon after an ordinary solid meal leaves the stomach about as fast as water drunk fasting:** a half-time of about 5–15 min, emptied within about 20–30 min.
  - It leaves by a fast route along the stomach wall to the antrum (the "Magenstrasse", gastric sieving) and does not wait for the meal.
- **The model's 85 min is too slow by roughly a factor of 6 to 15.** Its slowing per kcal was fitted to Camps 2016's shakes (S1234), where the energy is dissolved in the liquid itself. A 500 kcal shake does empty in about 70 min. A glass of water beside a 500 kcal plate does not.
- **The minimal fix is to slow the liquid lane only by the kcal that arrived as drink, not by the plate's kcal.** In the ordinary-day episode this cuts the time at Overfull 4 from 23 min to 5 min. No study-fitted satiety oracle misses, and the fit's loss is unchanged at 0.5782.

## 1. Fasting (question 1a)

| study | method, n | drink | half-time | shape |
|---|---|---|---|---|
| Mudie 2014 (S1245) | MRI, 12 healthy, fasted | 240 mL water | 13 ± 1 min (SEM); back to baseline at 45 min | — |
| Grimm 2018 (S16.6) | MRI, pooled from 5 studies, n = 22 | 240 mL water | 85 ± 13 % emptied at 30 min (about 11 min if mono-exponential: inference, 30 × ln 2 / ln(1/0.15)) | — |
| Ziessman 2009 (S16.7) | scintigraphy, 30 healthy | 300 mL water | upper limit of normal 19 min (mean + 2 SD), 22 min (mean + 3 SD) | best-fit exponential |

**Fasting water is first-order, with no lag, and a half-time of about 10–15 min.** The model's `WATER_HALF_MIN = 13` (S1245) is right.

## 2. With a meal (question 1b)

| study | method, n | meal and liquid | liquid emptying |
|---|---|---|---|
| Houghton 1988 (S16.1) | scintigraphy and manometry, 15 healthy | solid-liquid meal, liquid normal saline (or 25 % dextrose) | **saline median t½ 8 min**, against 40 min for 25 % dextrose; exponential; the solid stayed in the fundus until about 80 % of the liquid had gone |
| Collins 1991 (S16.2) | dual isotope, 8 + 7 healthy | 100 g ground beef/liver with 200 mL saline (or 25 % dextrose) | the saline dispersed at once and emptied after a minimal lag; the solid sat in a proximal reservoir; dextrose was held in the distal stomach |
| Moore 1984 (S1246) | dual isotope, 9 healthy | 50, 300 or 900 g lettuce-and-water meals at 68, 208 or 633 kcal | **liquid emptying uninfluenced by the meal's kcal** |
| Siegel 1988 (S16.8) | dual isotope, 24 normal | egg or chicken liver, with water | after the solid's lag (31 and 62 min), the solids emptied at rates identical to the liquid's; liquid fitted by a power exponential |
| Moore 1981 (S1272) | dual isotope, 10 | 300 g, 900 g and a self-selected 1692 g meal | liquid-phase marker t½ 40, 81 and 178 min; curvilinear (the contrary reading, § 4) |

**Water taken as the liquid of a solid meal empties exponentially, with no or little lag, at about its fasting rate:** Houghton's 8 min against Mudie's 13. Energy dissolved in the liquid slows it (Houghton's 40 min for dextrose; Camps 2016, S1234). The meal's solid kcal does not (Moore 1984).

## 3. Shortly after a meal (question 1c)

| study | method, n | meal, then water | water emptying |
|---|---|---|---|
| Koziolek 2014 (S16.4) | MRI, 12 healthy (7 M, 5 F) | FDA high-fat breakfast (about 964 kcal), 240 mL water 30 min after its start | went straight to the antrum and emptied quickly; the chyme meanwhile had a 50–90 min lag, then 1.7 mL/min |
| Grimm 2017 (S16.3) | MRI, healthy (n not in abstract) | three meals of 460–491 kcal (FDA, chocolate mousse, low-fat breakfast), water after | **as fast as fasted**; solid texture and more solids favoured the fast route; fat negligible; a second dose 60 min later emptied the same way |
| Großmann 2025 (S16.5) | MRI, 12 healthy, randomised crossover | 596 kcal light meal (toast, yoghurt, juice), then 50, 100 or 150 mL water 30 min later | **mostly emptied within 20 min**; first-order k ≈ 0.10, 0.15, 0.13 /min, which is t½ ≈ 6.9, 4.6 and 5.3 min (ln 2 / k; the authors say "handle with care"); chyme 3–4 mL/min beside it |

**Water drunk 15–60 min after a 460–964 kcal meal empties with a half-time of about 5–15 min.** The water emptying is first-order. The chyme beside it sits through its own lag, then empties at a few mL/min.

## 4. Does the meal slow the water, and does the water separate? (question 2: the key question)

**Yes, it separates, and the meal slows it little or not at all, provided the meal is particulate solids and the water is drunk as a drink.**

- **The fast route.** On MRI, water drunk after a meal runs along the lesser curvature to the antrum and the pylorus (Koziolek 2014; Grimm 2017). On scintigraphy, it disperses around a solid that sits in the proximal reservoir (Collins 1991; Houghton 1988). The drink leaves before the meal: Houghton's solid waited until about 80 % of the saline had gone.
- **Texture decides the split.**
  - A solid texture and more solid matter favour the fast route (Grimm 2017).
  - A rice pudding separates into a liquid layer over a particulate layer, and the liquid leaves first. A whole-meal bread bolus is homogeneous and holds its water: t½ 132 ± 8 against 104 ± 7 min (Marciani 2013, S16.9).
  - Blending a chicken-and-vegetable meal with its glass of water into a soup abolishes the sieving and slows the fall in gastric volume (Marciani 2012, S1232).
- **Energy in the drink slows the drink.**
  - 25 % dextrose: 40 min against 8 min for saline (S16.1).
  - Shakes: 26.5 min at 100 kcal, 69.5 min at 500 kcal (S1234).
  - A 100 kcal glucose drink after a meal still takes the fast route, though it spreads more slowly than water (Großmann 2026, S16.10).
- **The contrary reading is Moore 1981 (S1272).** Its liquid-phase marker slowed with meal size: 40, 81 and 178 min for the 300 g, 900 g and 1692 g meals.
  - Its meals were self-selected and varied in composition, and the abstract does not say the liquid was plain water.
  - A scintigraphic liquid marker also labels the water that mixes into the chyme.
  - Read with the MRI studies, it says part of the water stays with a large meal. It does not say that a glass of water drunk beside a normal plate waits 80 min.
  - **No study gives the split between the fast route and mixing for an ordinary plate; the open row S16.13 names that gap.**
- **So the real stomach behaves like the model's two lanes,** with one difference. The model's food water already rides in the solid lane, as soup water should (S1232). What the model gets wrong is the drink lane: it slows the drink by the plate's kcal, and that slowing belongs only to energy dissolved in the drink.

## 5. What the model does now (question 3)

**The rule** (`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stomach.lua`):
- `K.stomach.liquidHalfMin(E) = WATER_HALF_MIN + LIQUID_PER_KCAL × E`, with `WATER_HALF_MIN = 13` (S1245, Mudie 2014) and `LIQUID_PER_KCAL = 0.12`. E is the solid lane's kcal at the step.
- `0.12` is labelled inference (ruling 11c-5): (69.5 − 26.5) / 400 ≈ 0.11, from Camps 2016's thin 100 and 500 kcal shakes over water's 13 min (S1234 over S1245). It was fitted to liquids carrying their own energy.
- `K.stomach.drain` applies it to the drunk-water lane whatever put the kcal in the solid lane: a drink's energy (`ingestLiquid` sends it there) or a plate's.

**Measured with the kernel** (lupa host, HEAD 1cce7238, `K.stomach` stepped one minute at a time; scratch scripts, nothing committed):

| case | liquid-lane half-emptying |
|---|---|
| 667 kcal, 700 g meal, 500 g water at the same minute | 80 min |
| the same, water 10 min after | 77 min |
| instantaneous t½ through the meal | 93 min at 667 kcal, 74 min at 1 h, 57 min at 2 h, 30 min at 4 h |

**The close review's episode, reproduced on `tools/replay_live.py`'s `ServerReplay`** through `tools/mod_guide_series.server_run`: a 514 kcal plate at 07:00, then a 667 kcal plate and a 500 g autodrop at 08:00.
- Peak 1215 g at the drink.
- 23 min at Overfull 4 and 26 min at level 3 in that episode.
- The close review's 47 min a day adds the later episodes at 10:00 and 14:00.
- The guide's own day without the seed plate (`request_meals(1) + autodrops(1)`) never reaches level 3. Its peak is 973 g at 20:00, where a plate and a drink coincide.

**Which oracle was the constant fitted to?** Ruling 11c-5 fitted it by hand to S1234 (Camps 2016). No gut oracle scores the liquid lane's half-time directly. The oracles that read the drunk-water lane, through `K.satiety.LIQUID_WEIGHT`, are:
- S1231's casserole-with-water arm (`rolls_cw`, `rolls_cw_minus_cas`, `rolls_drop`);
- S1233's milk-volume arms (`rolls98_*`);
- S1247's liquid preloads (`callahan_*`), in `testing/tests/kernel/gut_oracles.py`, fitted by `tools/fit_gut_satiety.py`.

## 6. Volumes after a real meal and the 1100 g ceiling (question 4)

| study | what | volume | fullness |
|---|---|---|---|
| Cuomo 2011 (S16.11) | 300 mL water, then a sandwich meal at about 110 kcal per 5 min to **maximum satiety** (783 ± 77 kcal), MRI, 10 healthy | total gastric volume above fasting **456 ± 54 mL** at maximum satiety (510 ± 85 mL for the liquid meal); 282 ± 13 mL just after the water | maximum satiety (5 of 5) at under half a litre above fasting |
| Fruehauf 2009 (S16.12) | 800 mL, 300 kcal liquid meal, 8 healthy, upright MRI | initial gastric content **810 ± 52 mL** | symptoms not in the abstract |
| Kwiatek 2009 (S2211) | 200–800 mL liquid meals by tube, 16 healthy | content less than meal volume at t0, the ratio falling with volume | intragastric pressure rose under 4 mmHg |
| van Dyck 2016 (S1250) | water drunk fast to maximum fullness, 99 women | 734 mL (SD 317) drunk | maximum fullness |
| Kindt 2008, Tack 2003 (S1251, S1252) | slow nutrient drink to maximal satiety | 937–1048 mL drunk; 1508 kcal, about 1 L at 1.5 kcal/mL | maximal satiety; the volume, not the kcal, limits it |
| Geliebter 1988 (S1253) | water balloon at 100 mL/min with pauses, 4 lean | **1100 ± 185 mL (SE)** | maximal discomfort (10 of 10) |

**How often do healthy people pass about 1.1 L after a meal and a drink?**
- No study read here reports a healthy subject's intragastric volume above about 1 L after an ordinary meal.
- People who eat to maximum satiety stop at under 0.5 L above fasting (Cuomo), because the drink has largely left by then.
- Even an 800 mL meal infused at once reads about 0.8 L.
- Volumes past 1 L appear only when a drink is taken fast and in bulk, in the drinking tests, and those subjects rate fullness as maximal.

**Is S1253's 1100 mL a fair proxy for "can't eat more"?**
- **As the ceiling of maximal discomfort, yes.** The balloon was filled slowly with pauses, so it includes accommodation. At that ceiling, nausea and refusal are the right effects.
- **As where an ordinary meal stops, no.** Satiation ends a meal far below it (S16.11, S1250).
- The mod already starts its Overfull levels at 730 g and keeps level 4 for 1100 g, which matches this reading.
- **The capacity is not what puts an ordinary plate and a glass of water at level 4. The water's residency is:** at HEAD the drink lane still holds 80 % of its water 25 min later, where the stomach holds less than a quarter.

## 7. The recommendation (question 5)

**Change the liquid lane so that it is slowed only by the kcal that arrived as drink.** This is a separation term with no new constant. Leave every other constant alone.

- **The change.**
  - Keep a counter `stomach.liqKcal` of the energy `ingestLiquid` sends to the buffer.
  - In `K.stomach.drain`, use `E_liq = min(liqKcal, buffer.calories)` in place of the buffer's kcal: `half = WATER_HALF_MIN + LIQUID_PER_KCAL × E_liq`.
  - Shrink the counter with the solid fraction each step (`liqKcal ← E_liq × (1 − f)`), so it leaves with the energy it rode in.
  - Lay the counter in `K.stomach.new` and add `"stomach.liqKcal"` to `K.store.INPUTS` beside `stomach.volX`.
  - Cost: two float operations a player-minute (Rule 6: negligible, but bench it as any hot-path change).
- **What it keeps.** A drink alone behaves as before, since all its kcal is drink kcal: Camps's shakes (S1234), the Rolls 1998 milks and the Callahan preloads read exactly as at HEAD. Plain water beside a plate now empties at Mudie's 13 min. That sits between Houghton's 8 min and Ziessman's upper normal of 19–22 min, and above Großmann's 5–7 min.
- **What it rests on.** S1245, S16.1, S16.3, S16.5 and S1246 for the plate's kcal not slowing the water; S1234, S16.1 and S16.10 for a drink's own kcal slowing it. S16.13 stays open on the split.
- **A hedge, if Angus wants one.** Add a separate per-kcal slowing by the plate's kcal (`SOLID_PER_KCAL`) of 0.02 min/kcal. That gives a 26 min half-time after 667 kcal, standing for the share of water that mixes into a large meal (Moore 1981). No row sizes it, so it would be a game choice. The evidence favours 0.

**The predicted top-fullness time on the ordinary day** (the close review's episode; the server-replay rows above, with the rule installed by a scratch override):

| rule | peak | minutes at Overfull 4 | level 3 | level 2 | level 1 |
|---|---|---|---|---|---|
| HEAD (t½ 13 + 0.12 × plate kcal) | 1215 g | **23** | 26 | 28 | 30 |
| recommended (t½ 13 + 0.12 × drink kcal) | 1215 g | **5** | 6 | 8 | 13 |
| hedge, plus 0.02 × plate kcal | 1215 g | 10 | 12 | 15 | 18 |

- Over the close review's day this is about 10 min at Overfull 4 instead of 47: an estimate scaling its 47 by 5/23, not a separate replay.
- The peak itself stays, because the 500 g autodrop lands in one minute. A drink spread over its drinking time, or the review's option (a) (count the drink lane at `LIQUID_WEIGHT` for the refusal and nausea), would remove the last 5 minutes too.
- Other cases:
  - a 1000 kcal plate with 500 g of water: 15 min at level 4 becomes 3;
  - the guide's day without the seed plate: 99 min at level 1 becomes 18, with 0 at levels 3–4 either way.

**The oracles** (`tools/fit_gut_satiety.evaluate`, every gut oracle on a fresh host; HEAD against the rule):

| oracle | HEAD | recommended | band | miss |
|---|---|---|---|---|
| rolls_cw | 1659 kJ | 1720 kJ | 1.1× of 1657 | 0 → 0 |
| rolls_cw_minus_cas (S1231's null) | −130.0 (at the band's lower edge) | −68.8 | −130 to +166 (study +18) | 0 → 0, moves toward the study |
| rolls_drop | 409 | 470 | 1.1× of 448 (407–493) | 0 → 0 |
| nguyen_popcorn_below_chips | −0.0054 | −0.0060 | — | 0 → 0 |
| every other oracle (Rolls 1998 milks, Callahan, Tieken, Diekmann, Belza, Karl, Marmonier, Melanson, Moore reading, stability) | unchanged | unchanged | | |
| **loss** | **0.5782** | **0.5782** | | |

- **No study-fitted oracle regresses.** The only oracle at risk is `rolls_drop`: its 470 sits 23 kJ under its 493 upper edge.
- `rolls_cw_minus_cas` leaves the lower edge where it held `LIQUID_WEIGHT` from above (ruling T6c-5). A later refit could raise `LIQUID_WEIGHT` toward S1233's volume slope (`rolls98_slope`, the named non-reproduction at 0.038 against 0.130). That refit is an opportunity, not part of this change. If a refit brings `rolls98_slope` inside its band, the named non-reproduction is promoted to a target, per the CLAUDE.md rule.
- **What not to do.** Setting `LIQUID_PER_KCAL = 0` (the crude fix) gives the same day as the recommendation. But it breaks the drink-alone oracles:
  - `rolls98_600` leaves its band (miss 0.042);
  - `rolls98_slope` falls from 0.038 to 0.010;
  - `rolls98_ordering` falls to 0.005;
  - the loss rises from 0.578 to 0.834;
  - Camps's 500 kcal shake would empty in 13 min against 69.5.

**What else moves when it lands:**
- `test_kernel_stomach_lanes.py`'s `liquidHalfMin` assertions (its signature, or a new test of the drink-kcal counter);
- the golden trace, wherever a drink follows food (re-record under the named cause);
- `docs/mod-guide/data.json` (`tools/mod_guide_data.py --write`);
- the register rows that state the liquid lane's rule (supersede them with the new mechanism);
- the stomach comment at `NR_Kernel_Stomach.lua:183-191` and the writer's limitation string.

## 8. Sources not reachable

- **Grimm 2017 and Koziolek 2014 (ACS):** abstracts only; the meals come from the group's slides (`cersi.umd.edu`, Weitschies 2023 workshop).
- **Marciani 2012 (J Nutr, S1232):** the Elsevier copy returned 403; abstract only (already in the register).
- **Collins 1991 and Siegel 1988:** scanned PDFs behind PMC's download gate; abstracts only.
- **Almutairi 2023** (Clin Nutr Open Sci 51:35-43) was checked: it images porridge motion, not water emptying, so it is not cited.
