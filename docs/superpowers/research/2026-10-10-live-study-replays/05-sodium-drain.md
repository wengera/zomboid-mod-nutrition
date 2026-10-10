# F-T5-1: the basal sodium drain (Plan 11f)

Investigator: claude-opus-5-5, read-only, 2026-10-10. Everything ran on a scratch copy of HEAD 68897e7
(`git -c core.autocrlf=false archive HEAD`, under the session scratchpad `11f-na/`). The scripts sit beside it:

- `sim.py` and `sim2.py`: the 10- and 16-day fluids simulation on the scratch copy's real `K.fluids`;
- `xcheck.py`: the full server pipeline through `tools/replay_live.py`'s `replay_arm`;
- the scratch copy's `NR_Kernel_Fluids.lua`, left mutated at `BASAL_NA_FRAC = 0.0193` for the pin census in § 6.

No tracked file was edited, no game was booted, and no subagent ran.

## 1. Verdict

**Yes, this is a real defect, and a large one.** It is not a quirk of the study foods.

- The kernel charges basal urine as isotonic sodium at a fixed rate. That is 336.7 mmol/d for a man and
  245.7 mmol/d for a woman, whatever the intake, and no renal conservation ever offsets it.
- Any diet under about 337 mmol/d (7.7 g sodium, about 19.6 g of salt a day) therefore drains the sodium pool
  without limit. With vanilla autodrink holding water near balance, the character walks down the hyponatraemia ladder
  and dies.
- On a typical vanilla canned-food diet (120 mmol/d), the lethal band arrives at 157 h. Death follows about 6 h
  later, around game day 6.8.
- At 223 mmol/d, a salty diet, the band arrives at 296 h, around day 12.6.
- Nothing in the 3585-test suite runs a multi-day sodium balance. The five tests that touch the term pin its
  per-minute arithmetic only.

## 2. The sodium path, end to end

**Intake.**
- `K.fluids.intake` (`NR_Kernel_Fluids.lua:152-156`) adds absorbed sodium mg / 23 to `f.na` at absorption 1.0.
  It is called from `NR_Server_Nutrients.lua:410` with the stomach's per-minute `absorbed` vector.
- Food sodium comes from the generated `NR_Data_Nutrients.lua`, per item: for example `Base.TinnedSoup` 1093 mg,
  `Base.TunaTin` 777.5 mg, `Base.BreadSlices` 326.8 mg, `Base.CerealBowl` 1.68 mg.
- `Base.Salt` has no vector. `data/food-nutrients.json` maps it `no_nutrition_reason: "spice_only"` with `sodium`
  null, so salting a dish adds no sodium.

**Losses.** `K.fluids.losses` (`NR_Kernel_Fluids.lua:170-188`) is called at `NR_Server_Nutrients.lua:418`.
- Basal water is `basalG = AI[sex] / 1440 * dtM` (`:172`), with `AI = {3700, 2700}` g/d (`:27-30`; S0088's
  total-water intake used as turnover, open S1093).
- **The defect line** is `:180`: `f.na = f.na - basalG / 1000 * F.BASAL_NA_FRAC * F.OSM_REF`, with
  `BASAL_NA_FRAC = 0.65` (`:106`) and `OSM_REF = 140` (`:24`).
  That gives 3.7 L × 0.65 × 140 = **336.7 mmol/d** (male) and 2.7 × 0.65 × 140 = 245.7 mmol/d (female).
  - The rate is a fixed basal constant. It is not a fraction of the pool and not water-driven: the term follows
    `AI`, not the water actually drunk or held.
  - The urine water itself (65 % of 3.7 L = 2.4 L/d) is also fixed. Urine volume never flexes with intake except
    through the surplus clearance below.
- Sweat sodium is `:181`, `sweatL * f.naSweat`. `sweatLh` (`:159-163`) is 0 below `SWEAT_MET_LO = 3` MET, so a
  sedentary player sweats none. The live chain's 6-hourly drop was exactly 84.175 mmol, a quarter of 336.7, so sweat
  was zero there too.

**Clearance.** `K.fluids.clearance` (`:191-196`) removes a sodium *surplus* first-order at `NA_TAU_H = 24` h (open
S1096). Its comment, "a deficit is conserved" (`:65`), is the only conservation: it stops excretion of a negative
balance on top of the basal charge. Nothing ever lowers the basal charge itself.

**Concentration.**
- `K.fluids.conc` (`:206-212`) is the Edelman form: `(p0 + na + k) / p0 × t0 / tbw`, with
  `p0 = 140 × 0.73 × lm` (open S1092).
- `naPlasma = 140 × c` (`:215-217`, written at `NR_Server_Nutrients.lua:439-440`). For the 80 kg reference
  (lm 65.6), p0 is 6704 mmol.
- A balance of −1341 mmol at euhydration takes plasma sodium below 112.

**Grades and effects.**
- `K.fluids.hyponatGrade` (`:251-263`) uses the ladder `HYPONAT = {135, 120, 112}` (`:96-100`; S0102 and S1047, 112 a
  game choice).
- Effect rows are `NR_Data_Effects.lua:468-475`: grade 2 is SICK 55, grade 3 is SICK 85.
- The band feeds `K.effects.bands` at `NR_Kernel_Effects.lua:258`.

**Death.**
- `K.effects.drain` (`NR_Kernel_Effects.lua:589-625`) picks code 5 at grade 3 (`:609-611`), at
  `DRAIN_RATE[5] = 0.2778`/min, which is 100 health in 6 h (`:133`; open S1171).
- `NR_Server_Effects.lua` applies it as `ReduceGeneralHealth`.
- In the live chain, grade 3 began at age 108.12 (`first_age_of_grade`) and death came at 113.78: 5.7 h, the drain.

**Thirst.**
- `K.fluids.thirstTarget` (`:236-248`) caps thirst at `HYPO_CAP = 0.11` below 135 mmol/L (`:90`).
- Vanilla `autoDrink` fires above a hard-coded 0.1 (#2770). The cap therefore sits *above* the autodrink threshold,
  and "drink to thirst protects" does not stop drinking. In the simulation, thirst sat at 0.11 and autodrink kept
  drinking 2.7–3.7 L/d through grades 1–3.
- The live chain shows the same: `live_thirst_rows_at_hypo_cap` is 2322 rows.
- This is a second, smaller defect. It matters again after the fix, because dilutional hyponatraemia is the
  mechanism that should remain.

**Where the 0.65 came from.**
- Plan 4 ruling T11-3 (`.superpowers/sdd/2026-10-05-plan-4-kinetics/progress.md:38`) added the line to stop 10 h of
  water deprivation over-reading osmotic thirst. Without it, the reading is c ≈ 1.033 and thirst ≈ 0.45; with it,
  c ≈ 1.011 and thirst ≈ 0.32.
- Its cost-if-wrong was priced as "one knot of osmotic thirst". The multi-day sodium balance was never priced.
- The motive was a thirst-calibration problem (open S1099 and S1093) solved by draining a pool.

## 3. The 10-day simulation

**Method.**
- The scratch copy's real `K.fluids.new`, `intake`, `losses`, `clearance`, `dehydPct`, `conc`, `naPlasma`,
  `thirstTarget` and `hyponatGrade` run each game minute.
- Body: male, lm 65.6, fm 14.4, sedentary MET 1.3 (so sweat 0), thermoFluids 1, no cold, no alcohol.
- Three meals at 08:00, 13:00 and 19:00. Each meal's water, sodium and potassium are absorbed evenly over 120 min.
- Water to thirst is vanilla autodrink: while awake (07–23), when thirst exceeds 0.1, drink `2 × thirst` L, absorbed
  over 30 min (`LITRES_PER_THIRST = 2`, `NR_Server_Nutrients.lua:104`).

**Simulation caveat.**
- The mod's osmotic term reads the pool's `c`, which does not include the stomach's pending water. Only the volume
  term gets the pending water (ruling T1-1).
- A literal per-minute autodrink therefore re-fires while a drink is still in the stomach whenever `c > 1`.
- The tables use `c` computed with pending water included (`pendc`). The current-code rows are the same either way,
  within 0.2 mmol/L. The A rows are not (see § 6).

**Cross-check through the full server pipeline.**
- `xcheck.py` runs `replay_arm` on `ServerReplay`, the whole minute ORDER: 120.4 mmol sodium and 2 L water a day for
  2 days.
- `fluids.na` reads −225.6 at minute 1440 and −438.4 at 2880. The kernel's expectation is −216.3 and −432.6. The
  difference is meal absorption still pending, and day 2's increment is −212.8 against −216.3.
- So the full pipeline charges the same 336.7 mmol/d.

**Diets** (male, mmol/d of sodium absorbed):
- (a) zero sodium: a sodium-, potassium- and water-free energy source, like the TKX study foods.
- (b) typical vanilla, 2158 kcal, **120.4 mmol/d** (2769 mg):
  - breakfast: CerealBowl, 2 × EggScrambled, Apple;
  - lunch: TunaTin, 2 × BreadSlices;
  - dinner: TinnedBeans, Chicken, Corn, BreadSlices, Peanuts.
- (c) salty, 2259 kcal, **222.9 mmol/d**:
  - breakfast: CerealBowl, 2 × EggScrambled, HamSlice;
  - lunch: TunaTin, 2 × BreadSlices, Apple;
  - dinner: TinnedSoup, TinnedBeans, Chicken, BreadSlices.

**Reading the tables.**
- The columns are: Na in, urine out (basal plus surplus clearance) and sweat out, all mmol for that day; the sodium
  pool `f.na` and plasma sodium at day end; the worst grade that day.
- Sweat is 0.0 every day in every diet (sedentary), so it has no column.
- The pool `f.k` settles at +82 (b) and +85 (c) mmol, potassium's 24 h surplus. It props the osmotic pool up.

**Current code**

Diet (a), zero sodium:

| day | Na in | urine | f.na | plasma Na | grade |
|---|---|---|---|---|---|
| 1 | 0 | 336.7 | −336.7 | 134.8 | 1 |
| 2 | 0 | 336.7 | −673.4 | 127.8 | 1 |
| 3 | 0 | 336.7 | −1010.1 | 120.7 | 1 |
| 5 | 0 | 336.7 | −1683.5 | 106.3 | 3 |
| 7 | 0 | 336.7 | −2356.9 | 92.1 | 3 |
| 10 | 0 | 336.7 | −3367.0 | 70.6 | 3 |

Diet (b), typical vanilla:

| day | Na in | urine | f.na | plasma Na | grade |
|---|---|---|---|---|---|
| 1 | 120.4 | 336.7 | −216.3 | 138.4 | 0 |
| 2 | 120.4 | 336.7 | −432.6 | 134.5 | 1 |
| 3 | 120.4 | 336.7 | −648.9 | 130.1 | 1 |
| 5 | 120.4 | 336.7 | −1081.4 | 120.8 | 1 |
| 7 | 120.4 | 336.7 | −1514.0 | 112.0 | 3 |
| 10 | 120.4 | 336.7 | −2162.9 | 97.9 | 3 |

Diet (c), salty:

| day | Na in | urine | f.na | plasma Na | grade |
|---|---|---|---|---|---|
| 1 | 222.9 | 336.7 | −113.8 | 140.1 | 0 |
| 2 | 222.9 | 336.7 | −227.6 | 138.8 | 0 |
| 3 | 222.9 | 336.7 | −341.4 | 136.8 | 0 |
| 5 | 222.9 | 336.7 | −569.0 | 131.6 | 1 |
| 7 | 222.9 | 336.7 | −796.7 | 126.8 | 1 |
| 10 | 222.9 | 336.7 | −1138.1 | 120.1 | 2 |

In the current code, the first hour of each grade (16-day run) is:

| diet | grade 1 | grade 2 | grade 3 | death (+6 h) |
|---|---|---|---|---|
| (a) | 23.0 h | 79.3 h | 103.4 h | about 109 h, day 4.6 |
| (b) | 35.1 h | 127.2 h | 157.2 h | about 163 h, day 6.8 |
| (c) | 79.4 h | 223.4 h | 295.9 h | about 302 h, day 12.6 |

- Arm (a) matches the live chain: grades 1/2/3 at 29.1, 84.1 and 108.1 h after the chain start, and death at 113.78.
- Under thirst-driven drinking, water holds at −0.63 to −0.82 kg. The 0.11 cap never stops autodrink: 2.5–3.7 L
  are drunk daily through grade 3.

**With option B, the proposed fix (§ 7)**

| diet | day 1 urine / f.na / plasma | day 3 | day 10 | grade, days 1–10 | drunk L/d |
|---|---|---|---|---|---|
| (a) 0 | 10.0 / −10 / 140.9 | 10.0 / −30 / 141.1 | 10.0 / −100 / 141.1 | 0 | 3.3–3.6 |
| (b) 120.4 | 39.2 / +81 / 140.9 | 109.3 / +123 / 140.6 | 120.4 / +129 / 140.9 | 0 | 2.9–3.5 |
| (c) 222.9 | 72.4 / +151 / 140.7 | 202.4 / +227 / 140.7 | 222.9 / +239 / 140.9 | 0 | 2.7–3.9 |

- Urine sodium rises to meet intake: about 33 % on day 1, 91 % by day 3 and 99.9 % by day 7, the 24 h tau.
- Plasma stays within 140.4–141.1 at day ends.
- The retained surplus shows as +1.2 kg of water at 120 mmol/d and +2.0 kg at 223 mmol/d: water follows sodium.

## 4. The physiology, and the gaps in the register

What the register holds on sodium:
- S0389, S0390 and S0391: the AI 65 mmol/d, the CDRR 100 mmol/d, and no EAR.
- S0394, S0518 and S0517: sweat.
- S0396: the hormonal counter-regulation on a low-sodium diet (renin +55 %, aldosterone +127 %), direction only.
- S0102, S0397, S0520, S0711 and S1047: hyponatraemia is dilutional, from drinking in excess of losses, with its
  bands.
- S1045 and S1046: dose anchors.

The open rows are:
- S0564: the sodium repletion constant;
- S1092: the Edelman coefficients;
- S1093: the obligatory water loss;
- S1096: the tau of a sodium surplus;
- S1099: the osmotic thirst and the cap below 135;
- S1171: time to death.

What the register lacks, and the model needs:
1. **Renal sodium tracks intake at steady state.** About 90–95 % of the sodium eaten appears in 24 h urine, the rest
   faecal and dermal. No row says so. The model instead charges a constant 337.
2. **The time course of renal adaptation to a step in intake.** Excretion relaxes to the new intake over about 3–5
   days: a first-order kinetic, with a cumulative balance of a few hundred mmol. This would settle S1096 and S0564.
3. **The minimal urinary sodium on a very low intake.** Urine sodium falls to roughly 1–20 mmol/d within days. The
   floor is the obligatory loss, faecal and skin, a few mmol/d. No row gives it.
4. **Plasma sodium is defended by water, not by sodium excretion.** Plasma Na barely moves across a wide range of
   salt intake, because ADH and thirst retain or shed water with the sodium (extracellular expansion). Only a weekly
   balance and free-water handling decide plasma sodium. No row gives the per-intake plasma constancy or the
   extracellular-volume change per mmol retained.
5. **Urine volume is not fixed.** The concentrating and diluting range, and the obligatory urine volume for a solute
   load, would replace the fixed 2.4 L/d isotonic urine (S1093 open). The maximal free-water clearance would test
   `CLEAR_GH` 320 g/h (S0521's 4 h after-load figure).
6. **The plasma-sodium rise per % of pure water loss, and the osmotic thirst threshold.** These re-price T11-3's
   original motive inside the thirst function (S1099) instead of the sodium pool.

**Harvest candidates.** These are named for a harvester to resolve against the record. None is verified here, and
none may be cited from this page:
- Strauss MB et al 1958, Arch Intern Med, "Surfeit and deficit of sodium: a kinetic concept of sodium excretion" (the
  first-order excretion kinetic, the adaptation days);
- Hollenberg NK 1980, Kidney Int, "Set point for sodium homeostasis" (cumulative balance on a step);
- McCance RA 1936, Proc R Soc B, experimental sodium chloride deficiency in man (urine sodium near zero);
- Oliver WJ et al 1975, Circulation, the Yanomamo (urinary sodium about 1 mmol/d);
- Heer M et al 2000, Am J Physiol Renal, sodium 50–550 mmol/d (plasma Na constancy, body-water change);
- Rakova N et al 2013, Cell Metab, Mars-520 (long-term balance, the urinary recovery fraction);
- Lucko AM et al 2018, Nutrients (the percent of dietary sodium excreted in 24 h urine);
- IOM 2005, the water and electrolytes DRI (the minimal obligatory sodium loss, about 8 mmol/d, to be verified);
- a free-water clearance or ADH source, such as Robertson GL on the osmotic thirst and AVP thresholds.

## 5. Post-death stepping

**The mechanism.**
- `P.work` (`NR_Server_Players.lua:33-45`) sets `r.dead = true` on the first minute `isDead` reads true, then runs the
  whole minute pipeline anyway (`NR.server.minute.run`, `NR_Server_Minute.lua:31-45`).
- Only `NR_Server_Effects.lua` guards on it: `:303` for the trait writes and `:542` for the health, regeneration,
  fold and bruise writes. It names this as a stated limitation at `:56`: "a dead character's record is stepped but no
  trait, body or health write is made".
- Kinetics, metabolism, nutrients, strength, weight, writer and store still run. Strength, weight and writer still
  call setters on the dead `IsoPlayer`.
- `OnNewGame` resets the record at respawn (`NR_Kernel_Store.lua:159` clears `dead`).

**The cost.** A dead player still listed by `getOnlinePlayers` costs one full player-minute, the same as a live one.
It adds no load beyond the design count, because the player is counted online either way. It is wasted work, though,
and the stats packet keeps flowing to a death-screen client.

**Corrupt state.** None that survives. The record is reset on respawn, and the dead body's object is never adopted
(`:91-95`, #3358).

**What it does corrupt is evidence.**
- x273's slot files are the record **about 18 h after death**: `satiety.t` 131.72 against death at 113.78.
- At 14.03 mmol/h, the balance at death was about −1553 mmol, not −1804. The post-mortem drain was −251 mmol.
- The water deficit of −3550 g is also post-mortem: the dead body stopped drinking while basal loss ran on.
- The candidate row 6's "the dead record reads naPlasma 110.17" must say "18 h after death". The death-time value is
  about 111, the 112.12 h six-hourly reading (111.35) carried forward 1.7 h.

**Fix (optional, small).** In `P.work`, return after stamping `r.dead` and `lastSeen`, and skip `minute.run`. If the
mirror must show the death, run only `bus` and `store`.
- Downside: the stated limitation and any test that steps a dead record move (`test_players_shape.py` and
  `test_effects_shape.py`'s dead-record cases).
- Downside: the night-vision machine stops for the dead.

## 6. What pins the 337 today, and what a fix moves

**The census.** On the scratch copy with `BASAL_NA_FRAC` set to 0.0193 (10 mmol/d), the full suite read
**5 failed, 3580 passed**:
- `test_kernel_fluids.py::test_basal_ten_hours_at_rest`: lines 139–147, −140.29 mmol in 10 h, c and thirst;
- `test_kernel_fluids.py::test_sweat_losses_one_minute`: line 186;
- `test_nutrients_shape.py::test_ten_hours_at_rest`: line 497, and the `expected_thirst` mirror;
- `test_nutrients_shape.py::test_sweat_reads_the_thermoregulator_fluids_multiplier`: line 580;
- `test_golden_trace.py`: 240 leaves move, `fluids.na`, `fluids.c`, `fluids.naPlasma`, `fluids.thirstTarget` and
  `written.THIRST`, × 6 players × 8 snapshots. The rest of the trace is unchanged. That needs a named re-record
  (Plan 11d ruling T2-1).

**No test runs a sodium balance longer than 10 h,** which is why this shipped.

**The register.**
- #2961 quotes "the basal sodium draw to the last digit". It is a live reading on mod cac63cc and stays true on its
  build, but its bound wants a note.
- Every `repo:` pointer into `NR_Kernel_Fluids.lua` after the edited lines re-anchors.

## 7. The fix

### Option 0: the obligatory loss only

`BASAL_NA_FRAC` 0.65 → about 0.019, a 10 mmol/d obligatory loss. That is one constant, plus a new science row.

**What it does.** The drain stops. In the simulation (A, with that term carried as a separate 10 mmol/d), urine
sodium tracks intake through the existing surplus clearance:
- 39 / 109 / 120 mmol on days 1, 3 and 10 at 120 in;
- the pool settles at `f.na ≈ (I − 10) × 1 d` (+129 at 120 in, +239 at 223 in).

**Downside 1: the surplus reads as hypertonic.**
- With `f.k` at +82, `c` sits at about 1.02–1.03 and plasma at 142.7.
- The osmotic term then holds thirst at 0.43–0.47 all day. Excess water is cleared at 320 g/h zero-order, so the
  player drinks **8.6–9.0 L/d**: a polydipsia artifact.
- The live sim confirms it under either drinking model.

**Downside 2.** It also reverts T11-3's purpose: 10 h of dry rest goes back to thirst ≈ 0.45.

**Moves:** the 5 pins and the 240 golden leaves above.

### Option A′: an adaptive excretion state

`U = U_OBL + e`, where `de/dt = (I_abs − e) / τ_a`, with τ_a about 1 d. A new stored `fluids.naEx` carries `e`; the
surplus clearance stays.

**What it does.** At steady state `f.na → −U_OBL × τ` (about 0), so `c` stays near 1 and there is no polydipsia. A
step cut in intake leaves a transient deficit of `ΔI × τ_a` (120 mmol, plasma about −2.5, grade 0) that recovers.

**Downsides:**
- A new persisted field: the store schema, `GUARD_FLUIDS`, the heal and the golden.
- Plasma still moves with every transient that the body buffers with water.
- K needs the same treatment, or `f.k`'s +82 surplus still lifts `c` by 1.2 %. That alone puts the osmotic term
  near 0.1, the autodrink edge.

### Option B (recommended): the obligatory loss plus "water follows sodium"

Option 0's constant, plus a derived euhydration set point,
`weu = 1000 × t0 × (f.na + f.k) / p0` g, used in `K.fluids.clearance` (clear water above `weu`, not above 0) and
`K.fluids.dehydPct` (the deficit against `weu`). `conc` is unchanged.

**What it does.**
- No new stored field. The change stays inside `NR_Kernel_Fluids.lua`, because `f.water` has no reader outside it.
- A sodium surplus is retained isotonically: +1.2 kg of water at 120 mmol/d.
- Plasma holds at 140.4–141.1 on every diet.
- Water drunk is a normal 2.7–3.9 L/d.
- A zero-sodium diet loses 100 mmol over 10 days as about 0.7 L of extracellular contraction, not as hyponatraemia.
- Hyponatraemia still arises from its real causes, S0102 and S1047: drinking faster than `CLEAR_GH`, or replacing
  sweat sodium with plain water.
- Water deprivation still concentrates plasma (`weu` does not move with water).

**Downsides:**
1. `CLEAR_GH` (320 g/h, from S0521) becomes the load-bearing hyponatraemia constant and wants a free-water-clearance
   row.
2. T11-3's motive returns: 10 h of dry rest reads thirst about 0.45. It should be re-priced in the thirst function
   (S1099, S1093 harvests), not by draining sodium.
3. A long sodium deficit never shows as a deficiency effect. The extracellular contraction is invisible because
   `dehydPct` is measured against `weu`. That is acceptable while the mod ships no salt-depletion effect, but it is
   a stated limit.
4. The golden moves more: `water`, `dehydPct` and `viewPct` on top of option 0's leaves.
5. Each touched pin above needs recomputing. The `test_kernel_fluids.py` clearance test (lines 215–231) gains a
   `weu` case.

### Also, separately

- **`HYPO_CAP` 0.11 → below 0.1** (for example 0.09), so the hypotonic suppression actually stops vanilla autodrink
  (#2770's 0.1 literal). It is open S1099 either way.
  - Downside: a hyponatraemic player who is also volume-depleted gets no autodrink. That is the intended physiology.
- **Map `Base.Salt`.** It is `spice_only` with null sodium, so a player cannot salt-load. That matters less once the
  drain is gone.

### Science rows to mint before shipping any option

From the § 4 harvest:
- **U_OBL**, the minimal obligatory sodium loss (IOM 2005 or McCance), for option 0's constant;
- **the renal adaptation tau** (Strauss, Hollenberg; settles S1096 and S0564);
- **the 24 h urinary recovery fraction** (Lucko, Rakova), the steady-state check;
- **plasma-sodium constancy and isotonic retention across intakes** (Heer), for option B's `weu`;
- **the maximal free-water clearance**, for `CLEAR_GH`.

The constant's comment must also stop citing ruling T11-3 as its basis.
