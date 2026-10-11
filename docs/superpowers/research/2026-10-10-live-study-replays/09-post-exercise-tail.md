# 09. The post-exercise billing tail (F-T6-2, candidate C-17)

Plan 11f, ruling T6-2: a read-only investigation of the tail, beside an EPOC science harvest. Written 2026-10-11 against HEAD `762bf65` (mod files last changed at `983ebd6`), the 42.21 jar (`4a0e9546ec`) and the committed x292–x296 artifacts. No game was booted, and no tracked file was edited. The rows are in [09-epoc-rows.tsv](09-epoc-rows.tsv) (provisional S9.1–S9.25; `python tools/science_check.py --part` reads 0).

**In short.**
- The tail is the engine's own smoothing of its metabolic rate. `Thermoregulator.updateMetabolicRate` moves the rate toward its target as a first-order lag, rising with a step factor of 0.001 and falling with 0.0004 per update, both scaled by `GameTime.getMultiplier()`.
- The mod's choice is to read that smoothed rate as the player's activity, and to bill it at a Compendium MET (Metabolic Equivalent of Task) above a 1.3 idle.
- Measured on five tails, the fall has a time constant of 1.35–1.38 game hours at x29's `DayLength = 1`; the rise has 0.56 h. Both match the jar's coefficients.
- Because the step is fixed in real time (about 51 s falling and 21 s rising at speed 1), the tail in game hours scales with the day length. At the fixture's `DayLength = 4` it would be about six times shorter, so x29's profile magnifies it six-fold.
- EPOC (excess post-exercise oxygen consumption, the real after-exercise burn) is about 5–15 % of the exercise's oxygen cost after moderate-to-hard aerobic work (S9.2's 6–15 %, S9.4's 15.2 %, S9.6's mean 4.8 %; the denominators differ, § 3). After resistance work and calisthenics it is tens of kcal over 1–2 h. Live bills 2.3–2.7× the bout window after the window.
- **Recommended fix:** bill a running Fitness exercise at its class, bill the idle class while the rate is falling, and add an EPOC pool sized from the rows (§ 5).

## 1. The mechanism

### 1a. How the mod bills expenditure

- `MET.readActivity` reads the thermoregulator's rate, divides out the load factor, and buckets it to the nearest engine class (`mod/NutritionRevamp/common/media/lua/server/NR_Server_Metabolism.lua:182-184`, `local okR, rate = NR.call(thermo, "getMetabolicRate")` then `className = K.energy.classOf(K.energy.stripLoad(rate, loadKg, maxW))`). The header states the design (lines 11-16, ruling T5-2): the RATE classifies because the target reads -1 on a server [#2875, #2908].
- `K.energy.classOf` (`NR_Kernel_Energy.lua:165`) picks the `CLASS_LIST` name (line 62) whose engine value in `K.energy.CLASS_MET` (lines 31-55, the `Metabolics` table [#2632]) is nearest, and a tie goes to the lower name.
- `K.energy.activityMet` (`NR_Kernel_Energy.lua:182`) bills that class's Compendium MET (`K.energy.COMPENDIUM`, lines 91-115). The result lands in `body.met` (`NR_Server_Metabolism.lua:385-388`).
- `K.energy.minute` banks `ex = max(met - COMPENDIUM.Default, 0) * (fm + lm) / 60 * dtM` into `body.exKcalDay` and the trail (`NR_Kernel_Energy.lua:232`), against an idle of 1.3.
- The lag L takes in that minute's exercise kcal (`NR_Server_Metabolism.lua:396`).
- `body.met` also drives sweat, the glycogen draw and the writer's vigour test (`NR_Server_Nutrients.lua:408`, `NR_Server_Writer.lua:164-166`).
- The exercise flag `getFitness():getCurrentExe()` is read on the server (`NR_Server_Metabolism.lua`, in `readActivity`) and is non-nil there during a set [#2901]. It feeds only the training band and the writer's vigour kind; it never sets the billed class.

The bucket edges matter. The nearest-class edges sit halfway between engine values. Default (engine 1.5, billed 1.3) meets LightDomestic (engine 1.6, billed 1.6) at a rate of **1.55**. So the rate must come back to within 0.05 MET of its 1.5 asymptote before the minute bills idle. The edges a falling rate crosses are 4.75 (bills 5→4), 3.55 (4→3), 3.15 (3→3.8), 3.05 (3.8→3), 2.75 (3→2.5), 2.25 (2.5→2.0), 1.95 (2.0→1.9), 1.75 (1.9→1.6) and 1.55 (1.6→1.3).

### 1b. The engine's rate update (jar read, 42.21)

These are read with `./pz.sh dump zombie.characters.BodyDamage.Thermoregulator updateMetabolicRate` and `getSimulationMultiplier`. The tableswitch was decoded from the class bytes, because the dump prints no switch table.

- `updateMetabolicRate` builds the target from `Default` and the class floors (the floors are #2633, #2634 and #2649). If the rate is not already equal to the target, it moves the rate by a fixed fraction of the gap:
  - L831–L833 store `metabolicTarget - metabolicRate` and test its sign.
  - L835 (rising): `metabolicRate += delta * getSimulationMultiplier(Multiplier.MetabolicRateInc)`.
  - L838 (falling): `metabolicRate += delta * getSimulationMultiplier(Multiplier.MetabolicRateDec)`.
  - L851 then resets the target to -1 [#2908].
- `getSimulationMultiplier(Multiplier)` (L651–L685) returns `GameTime.getMultiplier()` times a per-kind constant, times the static `simulationMultiplier`. That static is 1.0, set in `<clinit>` L46, and only the class's own `setSimulationMultiplier` writes it.
- The enum order is from `Thermoregulator$Multiplier.<clinit>` L637–L647: Default 0, MetabolicRateInc 1, MetabolicRateDec 2, and so on. The switch sends ordinal 1 to L654 (`0.001`) and ordinal 2 to L657 (`0.0004`).
- **So the rate is an asymmetric first-order lag of the target.** Per update it moves 0.001·m of the gap when rising and 0.0004·m when falling, with m = `GameTime.getMultiplier()`. The fall's time constant is 2.5 times the rise's.
- `GameTime.getMultiplier()` (L982–L1003) is the product `multiplier · fpsMultiplier · multiplierBias · perObjectMultiplier · slomo · 0.8`. It carries the time-speed setting and the frame-rate normalisation but no day-length term, except under the server's own fast-forward option (L988–L989).
- The harness reads it on the server as about 4.79 at speed 1 under both day lengths: x141a at `DayLength = 4` (`activity_gate.json`, the alternating step acks read 0.8 and 4.785–4.802) and x292 at `DayLength = 1` (`lag-1.json` `phases.S.time.mult` 4.566, `phases.D.q0.mult` 4.150). This side attribution of the two values is an inference.

**Engine or mod?** The decay is vanilla: it is the thermal model's metabolic heat input, smoothed, and it runs whether or not any mod reads it. Billing it as exercise is the mod's choice: ruling T5-2 and rule #2905, "read activity on a server from the thermoregulator's metabolic rate alone". The mod's bucketing adds to the engine's area (§ 2c). The comment at `NR_Server_Metabolism.lua:12` and the limitations string at line 34 say the rate "lags activity by tens of seconds". That holds in real seconds at speed 1, but in game time at `DayLength = 1` the lag is 0.56 h rising and 1.35 h falling.

## 2. The measured tail

**Method.**
- The source is the server minute rings of x292–x296 (`testing/artifacts/x29[2-6]-*/minute-ring-admin-*.json`, `rows_list[].age` and `body.met`), together with each session's `lag-N.json` `readings.bouts[].sets[]` (`age_queued`, `age_end`, `rate_max`) and `speeds`.
- Each change of the billed MET between consecutive rows is a crossing of one bucket edge (§ 1a).
- For each falling crossing I regressed ln(edge − 1.5) on its age. Its slope is −1/τ for a first-order approach to 1.5.
- For the two single-set bouts (B0, B3) I regressed ln(6.0 − edge) on the time since the set started, for an approach to Fitness 6.0.
- A ring row reads what the previous drain billed, so every crossing carries the same one-minute offset, which does not move a slope.
- The scripts were run from the scratchpad and are not committed. Their figures are my arithmetic on the committed files, not register values.

### 2a. Time constants

| tail | crossings | τ_fall (game h) | r² |
|---|---|---|---|
| x292 B0 | 9 | 1.380 | 0.9999 |
| x293 B2 | 9 | 1.354 | 0.9996 |
| x294 B3 | 9 | 1.346 | 0.9996 |
| x295 B5 | 9 | 1.360 | 0.9997 |
| x296 B6 | 10 | 1.352 | 0.9994 |

- **The rise** fits τ_rise = 0.558 h (B0) and 0.562 h (B3), with r² ≥ 0.9993. The intercepts put the starting rate at 1.41–1.45, near the idle 1.5.
- **The ratio** τ_rise/τ_fall is 0.41, against the jar's 0.0004/0.001 = 0.40.
- **The jar's coefficients predict both constants.**
  - The x29 profile states 6.27 ticks per game minute at speed 1 (`testing/profiles/x29-exercise.toml:40`, from x222). With m = 4.79, the fall is 0.0004 × 4.79 × 6.27 = 0.0120 of the gap per game minute, so τ_fall = 83 game min = 1.39 h. The rise gives 33 min = 0.555 h.
  - The measured 1.35–1.38 h and 0.56 h agree.
- **Speed mode does not matter.** The tails span both the driver's `one` and `fast` speed modes, yet each fits one exponential. The step is therefore invariant under the time-speed multiplier, as `getMultiplier`'s `multiplier` factor implies.
- **The rise checks too.**
  - After a 1.03 h set the predicted rate is 1.5 + 4.5·(1 − e^(−1.03/0.558)) = 5.29. B3's polls read `rate_max` 5.328 (`lag-3.json` `readings.bouts[0].sets[0].rate_max`).
  - The time to reach the HeavyWork edge of 5.75 is 0.558·ln(4.5/0.25) = 1.61 h, against B0's vigorous episode at about 1.59 h (F-T6-3).
  - The server's exercise target is the flat Fitness 6.0 [#2633, #2634]; `ISFitnessAction`'s per-exercise target (9.0) is client-side.

### 2b. Duration and kcal (from the set's end)

| bout | window kcal (age0 → set end) | tail kcal (set end → first 1.3 row) | tail h | tail / window |
|---|---|---|---|---|
| x293 B2 | 176.0 | 468.7 | 5.77 | 2.66 |
| x294 B3 | 208.9 | 565.7 | 6.09 | 2.71 |
| x295 B5 | 184.2 | 450.7 | 5.73 | 2.45 |
| x296 B6 | 196.5 | 444.9 | 5.67 | 2.26 |
| x292 B0 | 209.5 | 777.2 | 6.87 | 3.71 |

- **Excluded rows.** B0 and B3 overran (F-T6-4), so part of their "tail" is still exercise; B0 includes the 6.0-billed vigorous minutes. B1 and B4 were cut off by the session end. Across a restart the rate does not decay offline (F-T6-5), which is why the task-6 report's day-1 back-to-idle time is 6.9 h.
- **The duration fits the exponential.** From an end rate of 5.0–5.3, τ_fall·ln((r_end − 1.5)/0.05) = 1.36 × 4.25–4.33 = 5.8–5.9 h, against the measured 5.67–6.09.
- **The tail by billed class** (x296 B6, kcal): 5.0: 19.5 · 4.0: 132.0 · 3.8: 15.8 · 3.0: 84.2 · 2.5: 67.0 · 2.0: 38.4 · 1.9: 39.9 · 1.6: 48.2.
  - The last, 1.6 band lasts τ·ln(0.25/0.05) = 2.2 h and bills 0.3 MET above idle. The engine's own excess over that span is 0.05–0.25 MET.

### 2c. Engine area against the mod's bucketing

- The engine's own excess above its 1.5 asymptote after the set is (r_end − 1.5)·τ_fall = 3.53 × 1.35 ≈ 4.8 MET·h. At the body's 80 kg that is about 381 kcal for B6, against 444.9 billed.
- So about 85 % of the tail is the engine's smoothing area. The remaining ≈ 15 % comes from the mod's 1.3 idle against the engine's 1.5, plus nearest-class rounding.
- The rise works the other way. The window bills 176–209 kcal, where the set's target (Fitness, Compendium 6.0, for 1.03 h) would bill (6.0 − 1.3) × 80 × 1.03 ≈ 387 kcal.
- The fall's constant is 2.5 times the rise's, so the lag does not conserve area. A bout bills ≈ 620–660 kcal (window plus tail), about 1.6–1.7 times what its target would bill. Of that, about 70 % lands after the set.

### 2d. The day length

- The step per update is fixed in real time at speed 1: m ≈ 4.79 at about 10 server updates a second. The time constants are therefore fixed in real seconds: τ_fall ≈ 1.36 h × 37.5 s = 51 s, and τ_rise ≈ 21 s.
- In game time they scale with the day length:

| `DayLength` | real seconds per game hour | τ_fall | τ_rise |
|---|---|---|---|
| 1 (15-min day, x29) | 37.5 | 1.36 h | 0.56 h |
| 4 (90-min day, the fixture [#0893]) | 225 | ≈ 0.23 h (14 game min) | ≈ 0.09 h (6 game min) |

- At `DayLength = 4` the same bout would rise to near its target within about 20 game minutes and leave a tail of about 1 game hour. On the arithmetic of § 2c that tail is about 70–80 kcal of billing.
- x141a's walk arm agrees with the real-time reading. A 30-s walk at `DayLength = 4` climbed to a poll maximum of 2.53 (buckets 2.6) toward 3.1 [#2875]; a 21-s τ_rise predicts 1.5 + 1.6·(1 − e^(−30/21)) = 2.72.
- **This scaling is inference.** It rests on the jar read and on two `mult` readings; no x29 run at `DayLength = 4` measured it.
- The defect therefore exists at every day length, but its size in game hours and kcal is a function of the server's day length. A mod that bills game-time kcal from a real-time-smoothed signal inherits that dependence.

## 3. EPOC: the evidence

The rows are S9.1–S9.24 settled and S9.25 open. Every citation was resolved through Europe PMC: the title, first author, year, journal, volume and pages were matched against the record, and the Bahr 1987 abstract was cross-read in PubMed. Every value is quoted from the record's abstract.

**Moderate and hard continuous aerobic exercise**
- **As a share of the exercise's cost.**
  - EPOC is 6–15 % of the net total O2 cost, even where it is prolonged (LaForgia 2006 review, S9.2).
  - After 20–80 min at 70 % VO2max, the 12-h EPOC is 15.2 ± 2.0 % (± unlabelled) of the total exercise O2 consumption, which the abstract does not call net or gross, with no difference across durations (Bahr 1987, S9.4).
  - In trained men the 8-h EPOC is 1.0–8.9 %, mean 4.8 %, of the net total O2 cost (net exercise O2 plus the EPOC itself) across 30–70 % VO2max and 20–80 min (Gore and Withers 1990, S9.6).
  - Intensity explains five times more of the variance than duration (S9.7).
- **Duration depends on intensity.** After 80 min it lasts 0.3 h at 29 % VO2max, 3.3 h at 50 % and 10.5 h at 75 % (Bahr and Sejersted 1991, S9.5). After three cycling bouts in trained triathletes (high-intensity short, low-intensity short and low-intensity long; the abstract gives no doses) it lasts 20–33 min and costs 12–29 kcal (Sedlock 1989, S9.8).
- **The ceiling.** Knab 2011's chamber study measured 190 ± 71.4 kcal over 14 h after 45 min at about 73 % VO2max, 37 % of the bout's 519 kcal (S9.10). It is the highest relative figure here, and it comes from a vigorous bout.
- **Feeding.** EPOC did not differ fed or fasted (21.1 against 20.9 L over 7 h, NS at n = 6; S9.11).
- **Averaged across studies.** In the studies comparing it with high-intensity intervals, moderate continuous exercise averages about 101 kJ (≤ 3 h) and 159 kJ (> 3 h) of EPOC; in those comparing it with sprint intervals its ≤ 3 h average is about 151 kJ (Panissa 2021 systematic review, S9.3: averages, not a pooled estimate, with no interval and no exercise dose). At 4.184 kJ/kcal that is roughly 24–38 kcal (my arithmetic, not a row).

**Resistance exercise and calisthenics.** EPOC is larger per unit of exercise O2 than after steady aerobic work (S9.19, S9.22), but small in absolute terms:
- About 19 kcal in the hour after 42 min of moderate lifting (S9.14).
- 37.00–51.51 kcal in the hour after circuit training (S9.16).
- A 6.2 L O2 rise over 2 h, back to control in the last 30 min (S9.17).
- A greater EPOC for heavier loads (S9.18).
- The longest reports follow 90–100 min of strenuous lifting: oxygen uptake raised through the whole 2–3 h measured (11–12 % in S9.15's last 6 min), and a next-morning resting metabolic rate 4.2–9.4 % above the previous morning's, with no control day behind those two readings (S9.15, S9.21). Schuenke 2002 is an uncontrolled outlier to 38 h (S9.20).

Bodyweight work is the closest match to the game's burpees and squats:
- After full-body calisthenics, expenditure above baseline is 1.7 kcal/min at 0–5 min and 0.5 at 6–10 min, and at 31–60 min it reads −0.1 ± 0.3 (no unit printed beside it), at or below baseline (Lee 2025, S9.23; the calisthenics value is the first of each printed pair, read from the sentence order).
- Bodyweight HIFT leaves an EPOC of 11.6 L over 60 min, no different from kettlebell complexes, with oxygen uptake raised for 30–60 min and "55 extra calories expended" (Sturdy and Astorino 2024, S9.24; 11.6 L is read as HIFT from the abstract's KC-then-HIFT naming order).

**Size for the game's bout.** These are my arithmetic, not a row.
- A 1.03-h Fitness set billed at its target is ≈ 387 kcal of net exercise (§ 2c).
- The aerobic share range of 5–15 % (oxygen shares whose denominators differ, § 3, applied here to kcal) gives ≈ 20–60 kcal. The resistance and calisthenics rows give tens of kcal, mostly within the first 30–60 min. Knab's vigorous ceiling of 37 % would be ≈ 140 kcal over 14 h.
- Live bills 445–469 kcal after a clean bout (§ 2b). That is about 7–23 times the 20–60 kcal derived above, and about 3 times Knab's ceiling.

## 4. Fix options

Pins and gates that every option meets:
- the x29 row-10 lag grade, which must be re-run (ruling T6-2);
- `tools/replay_live.py` and `testing/tests/kernel/test_replay_live_energy.py`, because the replay's stand-in feeds a rate;
- x29's lib, which derives activity events from the ring's `body.met`. A fix that decouples the billed MET from the rate needs the raw stripped rate as a ring path. That is a harness and lib change, landed before the run (§ 5 of CLAUDE.md).

The golden trace (`testing/tests/kernel/golden_trace.py`) has constant per-player rates and `getCurrentExe` nil, so a rule that changes only falling-rate or exercising minutes leaves its bills unchanged. A new persisted `record.body` field moves the trace's full-record snapshot, unless the field is created lazily, absent until the first exercise.

**A. Invert the lag: bill the engine's target, recovered from the rate.**
- **The rule.** target_k = r_{k−1} + (r_k − r_{k−1}) / (1 − e^(−Δt/τ)), with τ = τ_rise if the rate rose and τ_fall if it fell. Classify and bill the target; then add an EPOC term (as in B).
- **Strength.** It is exact for the measured lag (r² ≥ 0.9994) and conserves the target's area. It fixes both the tail and the rise's under-billing (C-2's set-length dependence) for every activity, not only Fitness.
- **Downsides.**
  - The fall's divisor is about 84 at a one-minute sample (`DayLength = 1`), so any rate the first-order model does not explain is amplified 84 times: a target change inside the minute, a frame-rate stall under load, or the moving flag's intermittency (#2877). A sub-minute walk would then bill as a spike.
  - It hard-codes the engine's 0.001/0.0004 and the server's ticks per game minute. τ in game time depends on `DayLength` and on the server holding its update rate, so it must be derived at run time from `GameTime` (the minutes per day) and re-checked on every build (`tools/jar_recheck.py`).
  - It needs a persisted or adapter-local previous rate.
- **What moves.** Pins in `test_kernel_energy.py` (new inverse function), `test_metabolism_shape.py`, the replay's rate history, and register rule #2905 (the classification reads the target, not the rate). The golden trace is unchanged at constant rates if the first sight takes r_{k−1} = r_k.
- **Test before shipping.** It is the most accurate option but the least robust, and it should first be graded offline on rings that carry the raw rate.

**B. A falling-rate gate plus an EPOC pool.**
- **The rule.** When the stripped rate fell since the last minute (by more than a small ε), no exercise is current and the player is not moving, bill the idle class (Default, 1.3). Separately, an EPOC pool accrues a fraction f of each exercise minute's net kcal and releases it with a game-time constant.
- **Strength.** It is simple and robust. It ignores the engine's constants except the sign of the change. The tail goes to idle plus a science-sized EPOC at every day length.
- **Downsides.**
  - The rise's under-billing stays: a Fitness set still bills 176–209 kcal where its target is ≈ 387 (C-2 stays open).
  - A genuine step down to a lighter non-idle activity while standing (from chopping to carpentry) bills idle until the rate settles, about τ_fall·ln(gap/ε).
  - Moving minutes keep the decaying class (the walk floor still applies) unless the gate also caps a moving minute at the walking class.
  - f and the pool's time constant are game choices, resting on S9.2, S9.4, S9.6, S9.10, S9.14–S9.24 and the open S9.25.
- **What moves.** A new kernel function and its tests; a lazily created pool field such as `body.epoc` (the golden trace is unmoved if lazy, because the trace never exercises); an adapter-local previous rate; replay parity; the x29 row-10 re-run; and the `NR_Server_Metabolism.lua:12/34` comments.

**C. Bill a current Fitness exercise at its class, gate the fall, and add the EPOC pool (B plus the exercise flag).**
- **The rule.** While `getFitness():getCurrentExe()` is non-nil on the server (already read; #2901), bill the class `Fitness` (Compendium 6.0, an engine value with no Compendium row). Otherwise apply B's gate.
- **Strength.** It fixes both halves of the measured defect for the activity that produced it: the set bills its class from the first minute, and the tail bills idle plus EPOC. It reuses a read the adapter already makes.
- **Downsides.**
  - Only Fitness carries a server-side flag. Walking, chopping and combat keep the rise lag, and B's gate alone handles their tails.
  - `getCurrentExe` cannot say which exercise (#2901), so every exercise bills 6.0. Burpees, which the Compendium would put higher, and light stretches bill alike. That is a C-2 question.
  - Billing 6.0 makes every set "vigorous" in `W.vigorous` (`NR_Server_Writer.lua:162-166`: `met >= COMPENDIUM.HeavyWork` with `ctx.exercising`). The acute hunger suppression S then rises during every bout, where live x29 sets never reached it (F-T6-3). This is arguably what S1502's −33 % during a 60-min bout describes, but it moves x29's row 9 and every live reading of S during exercise.
  - Sweat (`NR_Server_Nutrients.lua:408`) rises during sets and falls in the tail; the net sodium draw on the burpee chain falls (F-T6-6).
- **What moves.** Everything under B; register rule #2905's "metabolic rate alone" (a supersede or amend: the exercise flag now classes a minute); the x29 rows 9 and 10 re-runs; the replay's `exercising` event (the replay already models it: `tools/replay_live.py:323-328, 716-717`).

**D. Clamp the tail without the flag or a pool: cap the billed MET at a decaying share of the bout.** I list it to reject it: it needs bout bookkeeping, as C does, without C's accuracy during the set.

**E. Leave the billing and document the day-length dependence.** At the fixture's `DayLength = 4` the tail falls to about 1 game hour and ≈ 70–80 kcal (§ 2d). That is still above the EPOC evidence and still a function of a server setting; a community server at a short day would bill several times a bout's true cost. This is not recommended.

## 5. Recommendation

**C**: bill a running Fitness exercise at the `Fitness` class, bill idle while the rate falls with no exercise and no movement, and add a lazily created EPOC pool.

- **The pool's two constants are game choices resting on the rows.**
  - The fraction f ≈ 0.10 of the minute's net exercise kcal is a game choice. It lies inside S9.2's 6–15 %, below S9.4's 15.2 %, above S9.6's trained mean of 4.8 % and below S9.10's vigorous 37 %. The rows' denominators differ (S9.6's net total O2 cost includes the EPOC, S9.4's total exercise O2 is not called net or gross, and S9.10's is net exercise kcal), so the comparison is approximate.
  - The release time constant ≈ 0.5 game h is a game choice with no fitted constant behind it (S9.25 stays open). It releases about 86 % of a pool within 1 h and about 98 % within 2 h (my arithmetic: 1 − e^(−2) and 1 − e^(−4)). The rows bound it only loosely. Expenditure is at or below baseline by 31–60 min after calisthenics (S9.23), and oxygen uptake stays raised for 30–60 min after HIFT (S9.24). After resistance work it returns to control in the last 30 min of 2 h (S9.17) and is still above control at 105–120 min after heavy sets (S9.18). After long or vigorous aerobic work it stays raised for 12–14 h (S9.4, S9.10). The constant therefore fits the bodyweight rows and front-loads the release after resistance and hard aerobic work.
- **Why C.**
  - It removes the measured defect at every day length, from one read the adapter already makes, with no engine constant in the mod.
  - It keeps the mod in control of its own expenditure model, in line with Angus's criteria: long-term operability and control of our mod over vanilla quirks.
  - Its new state is one lazy field, so the golden trace does not move.
- **Its weak spot.**
  - Non-Fitness activities keep the engine's rise lag. A short walk under-bills its first τ_rise, which is 0.56 game h at `DayLength = 1`, about 33 game minutes.
  - Every exercise bills 6.0.
  - Every set now trips the acute vigour term.
  - Option A would fix the rise lag for every activity, and should be graded offline once a ring carries the raw rate. If it proves stable, it can replace C's flag later.
- **Order of work.** Lane M, after the sedentary tasks 7–9, per ruling T6-2:
  1. Add a ring path for the raw stripped rate (harness and lib commit).
  2. Make the kernel and adapter change, with tests and replay parity.
  3. Amend rule #2905.
  4. Re-run x29 rows 9 and 10.

## 6. Register candidates (for the controller; none minted here)

- **A C row: the rate step.** "`Thermoregulator.updateMetabolicRate` moves the metabolic rate toward its target by the gap times `getSimulationMultiplier(MetabolicRateInc)` when rising and `(MetabolicRateDec)` when falling, which are `GameTime.getMultiplier()` × 0.001 and × 0.0004 (× the static `simulationMultiplier`, 1.0), so the rate is an asymmetric first-order lag whose fall is 2.5 times slower than its rise." Pointers: `jar:Thermoregulator.updateMetabolicRate @378–@453 L831–L838`; `jar:Thermoregulator.getSimulationMultiplier @0–@154 L651–L685`; `jar:Thermoregulator$Multiplier.<clinit> L637–L647`. This answers the "how far the rate moves toward its target per update" gap at `docs/facts/body-and-weight.md:416`.
- **An M row: the measured lag.** "On a dedicated server at `DayLength = 1`, the billed MET after a Fitness set falls through the class edges as a single exponential toward 1.5 with a time constant of 1.346–1.380 game hours (five tails, r² ≥ 0.9994), and rises toward Fitness 6.0 with 0.558–0.562 h." The pointers would be ring paths of x292–x296. A ring row's `body.met` is a billed class, so the grade is a fit of edge crossings. Its numbers are this note's arithmetic and need an artifact (a grade script output) before they can be cited.
- **A C/inference row: the scaling.** "The rate's time constants are fixed in real seconds at speed 1, so in game time they scale with `DayLength`." This rests on the C row and on the two `mult` readings. It stays open until a run at `DayLength = 4` measures it.

## 7. What could not be found

- No record read here fits a time constant to the rapid or prolonged EPOC components (S9.25, open). The durations bound the shape only.
- No study measured EPOC after a game-like hour of repeated burpee or squat sets. The nearest are S9.23 (nine bodyweight exercises, 4 × 15) and S9.24 (6 sets of bodyweight HIFT).
- The units of Bahr 1987's three magnitudes (printed with a % sign in both records) and Bahr 1992's volumes (no unit in the abstract) were not confirmed from the full texts. The rows cite only the ratio (S9.4) and the durations (S9.9).
- The server's update rate under load was not measured here. A frame-rate drop changes τ in game time only if `fpsMultiplier` fails to compensate, and this matters only to option A.
