# Live study replays, 04: mechanism candidates

Angus, 2026-10-10: "As we try to see if the actual observable effects and timings match what we find in studies, keep an eye out for if simulating something else would potentially even simplify getting to an accurate output or otherwise just make it noteably more accurate with it, something to note and think on as you proceed and report".

This is a running list, kept by the controller through Plan 11f and Plan 11g. Each entry records:
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
- **Status: built in Plan 11g, in another form** (spec `docs/superpowers/specs/2026-10-12-gut-satiety-design.md`, § 7; Angus, 2026-10-12):
  - **What was built:** the meal pool M, fed in full at the eat and cleared first-order by the kinetics step (P's feed, renamed and refit; `fit-11g-20261012d`, loss 0.5782), with the stomach's fullness F counted past the 730 g comfortable maximum up to the 1100 g hard capacity (S1250, S1253). A well-fed stomach past 730 g now sates more than one at it, which carries Karl 2021's well-fed arm: BAL reads -54.5 % under the satiety fit (S1892's band -64 to -46 %).
  - **What was withdrawn, and why:** the harvest (S1799-S1894) pointed at a gut signal fed by what the stomach empties, and Task 4 built it as the gut stage G. Its fit went flat (`fit-11g-20261012`: G_STEEP 0.019723, a near-constant offset; the Task 6 review: the fasting rise about 4 times slower than P's, an evening request swinging about 10 h on a 2 % hunger factor, Karl's troughs not deepening). The stomach's energy-limited emptying already carries the meal's size and duration into F, so a feed at emptying counted them a second time and the fit flattened it. A spike over six model forms drove the eat-feed share to 1 in every fit (`.superpowers/sdd/2026-10-12-plan-11g-gut-satiety/task-6b-spike-report.md`). The hormone mechanism the evidence describes is real; the oracles at hand do not need a delayed feed.
  - **What followed:** the deficit drive was refit on the deficit studies alone, Karl's BAL arm held as a constraint (`fit-11g-deficit-20261012`: BALANCE_SPAN_KCAL 3100 to 3970.55; BAL -49.2 %), as this entry's gain proposed.
  - **Not reached:** Karl's post-meal troughs (0.536 / 0.432 / 0.457 of REST against the study's 0.215 / 0.209 / 0.106), the hunger nadir at minute 1 against about 15 (C-27), and Tieken's liquid against solid, a stomach mechanism (liquid emptying faster than solid) and not a satiety signal.

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

## C-6: renal sodium conservation (found by x271–x273; fixed in Task 5b)
- **Seen:** basal urine sodium was a fixed 337 mmol/d whatever the intake, so every diet drained and the character died (F-T5-1).
- **Status:** fixed. Urine now tracks intake with the measured adaptation time constant, and water follows sodium (S1665–S1697).
- **Left as candidates:**
  - sodium stored without water at high intake (S1673, S1677);
  - potassium in the set point, which has no row;
  - the zero-sodium plasma dip of about −3 mmol/L (S1680) that the set point flattens.

## C-7: salt and spices reach the body
- **Seen:** `Base.Salt` carries no sodium. Salting a dish lands the spice in `Food.spices` (#0296, #2652), which the intake never reads.
- **Candidate:** read `Food.spices` at the eat, at a per-use dose from the spice branch (#0381, open), and add a hypernatraemia rung for eating salt straight.
- **Gain:** players can salt their food, which matters once sodium balance is real.

## C-8: thirst reads the stomach's pending water
- **Seen:** after the Task 5b fix, the osmotic thirst term reads the pool without the liquid lane's pending water, so autodrink re-fires until the lane empties: 4.0–5.4 L/d against about 3.7 before.
- **Candidate:** the thirst view counts water still in the stomach (oropharyngeal and gastric satiation of thirst is real physiology).
- **Gain:** realistic drinking volumes, and a simpler, more accurate thirst model.

## C-9: volume thirst overrides the hypotonic cap
- **Seen (Task 5b fix 1):** during heat work with no dietary sodium and plain water, the hypotonic cap stops drinking once plasma falls below 135, while 8 L/d of sweat continues. Dehydration reaches 21 % by day 10, and the drain would kill from about day 6.
- **Candidate:** a volume-driven thirst term that partly overrides the osmotic cap as ECF contracts (S1724, S1731). The cut-off itself is open (S1695).
- **Gain:** a salt-free heavy worker is not killed by thirst suppression alone.

## C-10: water turnover scaled to energy
- **Seen:** drinking at rest sits on the top edge of the 2.0–3.0 L/d band by construction, because the turnover is the flat 3.7 L/d AI (S0088).
- **Candidate:** turnover scaled to energy expenditure, 0.20–0.35 L/MJ (S1710).
- **Gain:** resting and active water needs both read accurately, simpler than a flat figure plus activity corrections.

## C-11: food water in thirst satiation
- **Seen:** the view's c counts the solid buffer's water at full weight, alongside drinks.
- **Candidate:** a weight on food water, resting on S1704. A weight below 1 would be a game choice.

## C-12: a slow, low-sweat depletion arm
- **Seen:** the heat oracle cannot see the volume-defence onset, because mutant B1 survives it.
- **Candidate:** a slow sodium-depletion scenario (S1721) to grade the onset.

## C-15: sweat-gland lag and heat acclimatisation
- **Seen (Task 5b fix 3):**
  - With no stored state, the deficit-driven sweat sodium becomes detectable 6.3 h into a deficit, against about 12 h onset (S1773) and a 1–4 day gland lag (S1748).
  - A replete worker who acclimatises to heat does not adapt (S1755, S1739, S1743, S1744).
- **Candidate:** one stored exponential moving average with a time constant in days, driven by both deficit and heat exposure.
- **Gain:** a correct onset and acclimatisation in one field.

## C-16: drink bout size
- **Seen (x281–x284):** every auto-drink is twice the 0.1 trigger, 0.2 L, about 13 times a day spread across 24 awake hours.
- **Candidate:** drink toward the set point in realistic bouts (S1700: about 70 % of a deficit drunk at once; S1703).
- **Gain:** realistic drinking patterns.

## C-17: the post-exercise billing tail
- **Seen (x292–x296):** after each bout the server bills 1.6–2.0 MET for about 6.9 h, as the engine's rate decays. A day's exercise kcal is therefore 2.4–3.3× the bout's, and the lag (L) mostly takes in the tail.
- **Candidate:** bill post-exercise expenditure at its measured size, excess post-exercise oxygen consumption (EPOC), not at the engine's rate decay.
- **Gain:** accurate expenditure on exercise days, and a lag that reads the exercise itself.
- **Evidence to harvest:** the magnitude and duration of EPOC by intensity and duration.

## C-18: sleep debt booked at waking
- **Seen (x301–x302):** debt books at the 24 h window's close, which is phased by the record's creation (10:06 here). The breakfast after a short night reads no debt; the breakfast after the recovery night still reads the short night's full debt.
- **Candidate:** book debt at the end of the main sleep bout, or at a fixed clock hour.
- **Gain:** the hunger factor follows the night that caused it.

## C-19: one-night debt repayment
- **Seen:** a 1.85 h debt is repaid only 0.107 h by a following rested night (N3), so it persists.
- **Candidate:** a decay, or repayment by recovery sleep, sized from the sleep-restriction recovery literature. This needs a science row first.

## C-20: seed a first-seen nicotine anchor from the engine's timer
- **Seen (x321–x323):** a first-seen or healed anchor starts fully faded (T2-F). The engine's `getTimeSinceLastSmoke` reads 10 at about 85 game h, apparently held there.
- **Candidate:** seed the anchor from the engine's timer when the mod first sees a smoker in withdrawal.
- **Needs first:** a jar read of the timer's hold and its day-length units, and a science row.

## C-21: monotony's BOREDOM add and vanilla's panic reset
- **Seen (x331–x333):** vanilla resets BOREDOM every tick while PANIC is above 5 (`BodyDamage.UpdateBoredom`). The test character's PANIC sat at about 5.7–6.3, so the add was wiped on 6 of 8 eats.
- **Candidate:** find the PANIC source. Then either accept the wipe as vanilla behaviour or drop the BOREDOM add.

## C-22: bound the UNHAPPINESS climb (Angus chose a self-limiting floor, 2026-10-11)
- **Seen:** UNHAPPINESS never falls on its own, so a one-food diet's adds pile up: one eat a day reaches 100 by day 10, three by day 2.
- **Status:** being built. Monotony becomes a floor target, bounded and self-releasing through the existing effects floor (`K.hybrid`, #3119).

## C-23: place setany events off the before-snapshot, and grade BOREDOM with a drift estimate
- **Seen:** a harness-lib defect (F-T9-3, F-T9-2), not a mod mechanism. It belongs in future libs.

## C-24: the panic-floor flicker
- **Seen (x331–x333):** the dehydration PANIC floor of 7 (`NR_Data_Effects.lua:210-213`) decays under 6 between once-a-minute writes (5.74 live; vanilla decay about 1.12 per game minute, #3400, #3401). The level-1 panic moodle therefore flickers.
- **Candidate:** a floor value or write timing that holds the moodle level. A tuned floor depends on clock speed, and writing more often is per-tick work (Rule 6).

## C-25: monotony's BOREDOM floor and vanilla's idle rise
- **Seen (x341–x343, floor design):** vanilla's idle rise adds about 1.8-2.0 BOREDOM per game hour on top of the floor (F-T9r-4; no grade leaf yet). A one-food player idling (assumed indoors) would cross Bored level 2 (50) in about 10-11 idle hours, and vanilla then adds UNHAPPINESS through its boredom term.
- **Candidate:** lower the BOREDOM cap, or count the floor against vanilla's idle path.
- **Downside:** a lower cap loses the level-1 Bored moodle Angus chose (2026-10-11). Raise this with Angus at the close.

## C-26: decide a falling metabolic rate on the raw engine rate
- **Seen (x351–x353, F-T6r-3):** 13 still post-set minutes at eats and sips billed 1.6–2.0 where idle was due. The engine's rate lags toward base × load factor, so dividing the lagged rate by the instantaneous, lower load factor hid the fall.
- **Status:** built (2a411e4e, ruling C26-1). Unmeasured live; owed to Plan 11b.

## C-27: an ingestion-paced feed of the meal pool
- **Seen (x361, x363; Plan 11g Task 8):** the hunger nadir lands at minute 1 after every eat, live and on the replay (C650 1.12 min, C400 1.01 min; x363's solid 1.63 min and the milk's graded nadir 2.0 min), where the studies put it at about 15 min (S1833, the one stated in text; harvest 11 reads 15-30 min, inference). It is the eat feed's accepted downside (spec § 7).
- **Candidate:** feed M over the meal's eating or gastric-accommodation minutes rather than at once, or add an oral and gastric-distension phase that peaks at about 15-30 min.
- **Evidence:** harvest 11's nadir rows (S1799-S1838) and C-1.
- **Gain:** more accurate early time courses, at one constant.

## C-28: a class change pushes past the 60 s gap
- **Seen (x364, F-3; Plan 11g Task 8):** the client's energy level lags a server level change by up to the bus's 60 s wall-clock push gap. Level 1 reached the client about 36 s of wall after the server's change (the client still at 0 at 186.79 s and at 1 by 188.84 s; the server changed between 149.67 and 152.22 s), about 5 game hours at speed 5. At speed 1 the gap is up to about 1.6 game hours at DayLength 1, the test's 15-minute day.
- **Candidate:** send a change of a moodle class level (rare: a few a day per player) at the next slow minute regardless of the push gap; ordinary effects pushes keep the gap, and the per-player push offset stays.
- **Gain:** the moodle tracks the server within a minute. The cost is a handful of extra sends a day per player (Rule 6: event-driven, not per tick).

## C-29: a new record's trailing window
- **Seen (x364, F-4; Plan 11g Task 8):** a fresh record's trailing 24 h intake window starts empty, so its energy state climbs from first sight. The 80 kg admin reached energy level 1 8.37 h after first sight and level 2 20.86 h after it (arithmetic on the ring's change ages and `start.json`'s `rec.firstSeen`).
- **Status: not a defect; named a limitation** (ruling T8-1, `a24436a9`: a writer limitation with an equivalence test). An empty window reads exactly as one seeded at balance and spread evenly over its first 24 h, since eb24h(t) = -ee_rate x t in both, and a spawn's 8.4 h unfed sits inside a skipped-meal range (about 5-18 h). No oracle covers a fresh record's first day, because every oracle warms up first.
- **The inconsistency left:** M seeds from vanilla HUNGER (a recently fed body), while the window reads an even eater.
- **Candidate (Angus's choice at the close):** a lumped seed, placing the M seed's equivalent kcal in the window's current hour. Downsides: fictitious kcal reach the legacy calorie mirror, the energy state reads below 1 for the first hours, and a step comes at 24 h.

## Decisions (Angus, 2026-10-13)
- **C-27:** left as is. The hunger nadir stays at minute 1 after an eat, a named miss against the studies' 15 minutes.
- **C-29:** left as is. A fresh record's empty energy window stays a named limitation, with its equivalence test.
- **C-25:** accepted. Vanilla's idle BOREDOM rise on top of the monotony floor is how the game already treats idleness.
- **C-2:** to be built. Each Fitness exercise is billed at its own intensity from the activity tables, so light work costs less and suppresses hunger less.
