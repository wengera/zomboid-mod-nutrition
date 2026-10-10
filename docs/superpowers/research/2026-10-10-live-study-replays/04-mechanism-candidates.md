# Live study replays, 04: mechanism candidates

Angus, 2026-10-10: "As we try to see if the actual observable effects and timings match what we find in studies, keep an eye out for if simulating something else would potentially even simplify getting to an accurate output or otherwise just make it noteably more accurate with it, something to note and think on as you proceed and report".

This is a running list, kept by the controller through Plan 11f. Each entry records:
- **Seen:** what was observed;
- **Candidate:** what simulating it would replace or improve;
- **Evidence:** the evidence it would rest on;
- **Gain:** the expected gain, either simpler or more accurate.

An entry is a candidate for a later design plan, not a decision. Rows in the science register back an entry only once it is harvested.

## C-1: post-meal satiety hormones and gastric emptying
- **Seen:**
  - Karl 2021's well-fed arm suppresses hunger about −55 % in the study (−45 % in the model at the refit). The paper attributes this to slowed gastric emptying and gut hormones.
  - The model's post-meal hunger never falls below about 0.08, so BAL saturates at the balance clamp.
  - Fitting BAL pulled `BALANCE_SPAN_KCAL` down to 3100, about 20 % below the fit without BAL (3800).
- **Candidate:** a post-prandial satiety signal that rises with absorbed nutrient load and decays over hours (a GLP-1/PYY-like term).
- **Gain:**
  - It would carry BAL's suppression.
  - The deficit drive could then be fitted to the deficit studies alone, which is simpler and less entangled.
  - Large meals and surplus days would read more accurately.
- **Evidence to harvest:** time courses of GLP-1, PYY and CCK after meals of known size and composition, and gastric-emptying rates by meal size.

## C-2: graded exercise intensity in place of the 6.0 MET vigorous bar
- **Seen:**
  - Karl twin K "not vigorous" (MediumWork at matched kcal) overshoots, reading DEF +40.8 against the 39 band.
  - Twin K's DEF swings from 20.5 to 35.9 depending only on which billing class stands for an 8.3 MET walk.
  - The writer's acute suppression switches on at a binary threshold.
- **Candidate:** acute suppression and the exercise bypass scaled continuously by intensity (MET or %VO2max), with no on/off bar.
- **Gain:**
  - It removes the twin-billing sensitivity and the non-vigorous overshoot.
  - It is simpler: one curve, not a class bar plus a ramp.
- **Evidence:** the acute-exercise appetite meta-analyses already in the register (S1500, S1502 and others), which report intensity effects.

## C-3: absorption-timed versus ingestion-timed energy for the deficit signal
- **Seen:**
  - F-1: booking intake into the trailing window as the stomach empties delayed the post-fast breakfast's credit. This drove the 36 h fast overshoot, before the refit.
  - The refit absorbed it into the constants.
- **Candidate:** read the deficit drive's balance from both an oral or cephalic signal at ingestion and absorbed energy, weighted.
- **Gain:** the refit may then not need to compensate for timing, and post-fast meals would read more accurately.
- **Evidence:** studies of hunger during early refeeding and of sham feeding.

## C-4: meal-time effects beyond the circadian hunger factor
- **Seen:**
  - In Task 4, the same snack contrasts read very differently by lunch time. Marmonier's protein-minus-carbohydrate delay reads 40.6 min at an 18:19 lunch and 19.3 min at 12:49, against the study's 26.
  - The circadian factor multiplies hunger, so the absolute gaps scale with time of day.
- **Candidate:** a time-of-day effect on satiation or gastric emptying (a slower evening emptying is reported), and not only on the hunger level.
- **Gain:** contrasts that are more stable across the day. Without one, accuracy would depend on when players eat.
- **Evidence to harvest:** circadian variation in gastric emptying and diet-induced thermogenesis.

## C-5: the idle day's expenditure
- **Seen:**
  - A live idle day bills about 1.344 × REE (x261), which is in the sedentary range.
  - Twin construction needed body-size gymnastics because the Default class is a single flat MET.
- **Candidate:** no change needed yet. It stays a note in case activity-class granularity limits later fits.
