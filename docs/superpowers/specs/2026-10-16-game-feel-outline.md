# Game feel: bringing Nutrition Revamp closer to the game — design outline

Status: outline. Angus decided every item in the 2026-10-16 game-feel review. This outline groups those decisions into workstreams for the next spec and plan. The decision log, with Angus's words for each item, is `.superpowers/sdd/game-feel-review/decisions.md`; the review's evidence is `report.md` and `seesaw.md` beside it. Every number below comes from the review's offline replays at HEAD 92bdd753 and is a starting value for the plan to confirm.

## The rule (Angus, 2026-10-16)
"going with moving subjective things closer to vanilla and objective things to be science supported"

- **Subjective follows vanilla:**
  - pacing;
  - how often something comes up;
  - effect sizes;
  - when a crisis lands;
  - how signals are presented.
- **Objective follows science:**
  - which effects happen, their order and relative severity;
  - their triggers;
  - real energy and water needs.
- **The bends:** where the two conflict, the guide states the bend.
- **The refinement (item 4):** survival difficulty that comes from real physiology is where the mod should be tougher than vanilla ("make the literal survivor experience tougher where it should be").
- **Health drains signal damage, not lethality:**
  - a state drains health early, at vanilla's pacing, as the body takes damage;
  - the drain stops at a floor that deepens on science's clock;
  - the floor reaches 0 only at the state's real death time. Every state that kills in reality kills then, with no toggle.
  - Angus: "once it actually would kill you, that healh drain should be where it ends at 0"; "deficiencies which make sense to kill you should just kill you, I dont think we need to toggle those off".

## Workstream A: hunger and eating (items 3, 11, 4, 10a, 10b)
1. **A calibrated hunger writer (item 3).** The study-fitted satiety model stays underneath and decides relative fullness: meal size, protein, bulk and time of day. The value written to HUNGER passes through a calibration curve:
   - a satisfying meal (about a third of the day's kcal) reads about 0;
   - Peckish returns at about 4 h and Hungry at about 6–8 h, vanilla's three-meal cadence;
   - snacks read as snacks.
   The study tests read the model before the curve.
2. **Fullness between weight and volume (item 11):**
   - stomach fill = weight + β × (plate volume − weight), with a volume-per-gram column per food from USDA cup and gram weights;
   - β is fitted from volume-at-same-calories studies (air-whipped shakes, popcorn against crisps, soup against a casserole), or is a game choice within their range;
   - drunk water counts lower toward Overfull (item 5).
3. **Overfull consequences (item 11):** slowed and lower endurance at level 3; nauseous at level 4, with eating refused there, mirroring vanilla's "can't eat more". A vomit chance at level 4 is to be designed.
4. **Well Fed restored (item 3):**
   - with a full meal reading about 0, vanilla's FOOD_EATEN timer should fill again (#0503, #3597; the hunger freeze is #0473);
   - verify it, choose between vanilla's timer and the mod's fullness as the driver, and keep it distinct from Overfull.
5. **Real energy needs are kept (item 4):**
   - about 2,000 kcal a day at rest; no metabolism option;
   - the tooltip's vanilla hunger line is replaced by "fills you for about N h" and the kcal.
6. **No morning dip while fasting (item 10a):** the circadian dip applies only when fed.
7. **A dead zone at each hunger moodle threshold (item 10b).**

## Workstream B: starvation and dehydration as body damage (items 2, 5)
1. **Lifting the caps:**
   - the 0.69 hunger cap lifts at true starvation, so vanilla's Starving moodle shows by about day 1.5;
   - the 0.83 thirst cap lifts at Parched, by about vanilla's 29 h.
2. **A drain-and-floor model:**
   - **Drain:** a health drain at the mod's own per-game-day rate, independent of day length. It reaches a first floor at about vanilla's death time: about 2.5–4 days for starvation, about 35 h for dehydration.
   - **Floors:** the floor deepens over time on science's clock and reaches 0 at the real death time:
     - dehydration about 3 days;
     - starvation about 6–9 weeks;
     - beriberi in weeks;
     - scurvy and pellagra in months.
   - **No toggle:** `NR.DeficienciesCanKill` is removed (the mod is unreleased, so there is no migration).
   - **Every lethal deficiency state** moves to this model, its death time from science.
   - **Open:** the final floor curves and drain rates.
3. **Effects in science's order, at vanilla's sizes:**
   - **Starvation:** weakness, then cold and healing, then infection and mood. Appetite eases after about day 3 in a real fast, but the Starving signal stays on screen (the stated bend).
   - **Dehydration:** 2 % fatigue and endurance; 3–4 % weakness and heat intolerance; 6 %+ dizziness and confusion (panic moves here from 1.5 %); 10 %+ collapse.
4. **The water base:**
   - basal loss becomes the real minimum turnover, about 2–2.5 L a day total (about 1.5 L drunk and about 0.7 L from food), near vanilla's 1.4 L;
   - it replaces `K.fluids.AI` 3700/2700 g, the adequate intake;
   - sweat with work and heat stays on top.
5. **Vanilla's thirst settings honoured:** the High Thirst and Low Thirst traits (about ×1.5–2 and ×0.5) and the stat-decrease option scale water loss.
6. **A general drain lands on overall health,** not on one body part. This needs a check against vanilla's injury model.

## Workstream C: moodles and signals (items 1, 8, 10c, 10d, 10e)
1. **Remove the Energy moodle (item 1).** The energy state stays as an internal driver.
2. **Remove the Hydration moodle (item 10e).** Vanilla's Thirsty, reaching Parched, is the signal, and dehydration % stays on the panel.
3. **The Deficiency moodle reads only nutrients that have an effect (item 8),** and a test keeps its list in step with the effects table. The panel shows every grade.
4. **A dead zone on the monotony mood floor (item 10c).**
5. **An option to hide level 1 of Stimulant, Sleep and Excess (item 10d).**
6. **Panel lines:**
   - "weakened by starvation" and a body-condition line (item 2);
   - a weight trend, "losing", "steady" or "gaining" (item 6);
   - dehydration % (item 10e).

## Workstream D: coffee, beer and sleep (item 9)
- **Science:** caffeine absorption, clearance, tolerance and withdrawal; alcohol clearance at about one drink an hour and the hangover's timing; sleep debt and its hunger effect.
- **Game sizes (the default):** a cup's peak relief about 2× vanilla's; about 6 intoxication per beer, stacking; a mild hangover. These are labelled game choices.
- **A new option** (a name like `NR.StimulantRealism`): Game or Realistic. Realistic restores today's strengths.

## Kept as they are (decided)
- **Weight at science's pace** (item 6). Active survival loses about 3.5–6 kg a month, and a band shifts in one to two months. Gains the panel trend line.
- **Strength at 4 years to level 10** (item 7). Detraining stays science (S0618), with its options documented.

## Research passes (science register harvests, before minting)
- **The starvation timeline:** hunger strikers, the Minnesota study, deaths at about 45–75 days, the phase order of effects.
- **Minimum water turnover** and the food-water share. The register holds the adequate intake (S0088) and the minimum daily losses (S1688), but no turnover row.
- **β:** volume against fullness at matched calories.
- **Later:** vitamin K deficiency onset and effects (item 8).

## Checks before design is final (jar reads or short live runs)
- whether vanilla's FOOD_EATEN refusal and Well Fed fill under the mod's writer, and what Well Fed grants beyond the hunger freeze;
- how a general health drain behaves across vanilla's body parts and its regeneration tiers;
- whether vanilla's own starvation and thirst drains run once the caps lift, and how the mod's floor wins over them.

## Verification (the plan's live sessions)
- a starvation run to the first floor, then recovery on eating;
- a no-water run to the first floor;
- an overeating run: 1 kg of broccoli stops partway, and Overfull 4 refuses;
- a three-meal day: moodle cadence against vanilla's, and Well Fed showing;
- a thirst trait on and off.

## Follow-on edits
- **The guide:** H1, S1, S2, S5c, S6, the moodle lists, notes 10f and 10g, and every chart a change moves. `mod_guide_data.py --check` catches the data side.
- **The README, COMPATIBILITY and CHANGELOG.**
- **The register:** rows describing the caps, the Energy and Hydration moodles, the water base and the stimulant strengths are superseded with successors.
- **Guide hooks:** the golden trace re-records under named causes, and the study oracles are re-pointed at the model's pre-curve value.

## Suggested order
1. Research passes and the checks.
2. Workstream B, the engine of the floors and caps.
3. Workstream A, the writer and fullness.
4. Workstream C.
5. Workstream D.
6. The live runs.
7. The guide and docs.

B before A, because the calibrated writer must hand off to the cap lift at the top end.
