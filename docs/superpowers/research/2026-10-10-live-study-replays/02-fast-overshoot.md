# F-1: the 36 h fast's overshoot through the full server pipeline (Plan 11f)

Investigator: claude-opus-5-5, read-only, 2026-10-10. Everything ran on a scratch copy of HEAD ca8848c
(`git -c core.autocrlf=false archive HEAD`, under the session scratchpad `11f-f1/`). The scripts sit beside it in
`f1work/` (`inv.py`, `sw.py`, `other.py`, `grid.py`, `bands.py`, `variants.py`). Each switch is a Lua monkeypatch made
on the `ServerReplay` host after it is built. No tracked file was edited and no game was booted.

## 1. The finding in one paragraph

The 1.348 has three causes, and none of them is a bug in the satiety kernels.

1. **A defect in the replay tool (about a sixth of the gap).** `ServerReplay.add_user` sets the stand-in's
   thermoregulator rate to `K.energy.COMPENDIUM.Default`, 1.3 (`tools/replay_live.py:538`). The server reads that rate
   in the engine's own units, and `K.energy.classOf(1.3)` returns `DrivingCar`, which bills 1.4 MET. A live idle
   player's rate is 1.50 (#2875). That classifies as `Default` and bills 1.3. So the replayed 70 kg man spends
   2,059.6 kcal a day against the 1,948.7 kcal maintenance the meals supply. That is a standing deficit of about
   111 kcal a day, and it also drags `fm` below `fmRef`.
2. **The stomach (the largest share).** The shipped path books energy into the trailing-24 h window only as it
   empties from the stomach (`ctx.absorbed`). The oracle books the whole meal at the eat. The fast arm's breakfast is
   about 1,000 kcal and takes hours to empty. At 13:00 and 20:00 the window still reads most of the fast's deficit:
   the fast arm's es reads 1.090 and 1.013 where the oracle reads 1.065 and 1.008. So lunch and dinner come out
   bigger. The fed arm is at steady state, so the same delay roughly cancels there.
3. **The partition, through fatDep.** A day of fasting takes `fm` from 9.039 to 8.973 kg. The energy state's
   `0.5 x fatDep` adds about +0.007 at 08:00 on day 2, plus a little more on day 3. Over the same day the lean loss
   (60.90 to 60.18 kg) lowers the resting expenditure, which pulls the ratio down a little and partly offsets the
   fatDep rise.

Adaptive thermogenesis (AT; `at` stays below 0.001), the training close and the time the request mapping reads es
each contribute nothing measurable.

With all three switched off (rate 1.5, no stomach, no partition), the server path reproduces the oracle
bit-for-bit: 1.3039 / 0.9855, the fed arm 1,963 / 1,937 kcal and the fast arm 2,560 kcal.

## 2. Each switch (the 36 h fast, `O.fast_plans()`, 70 kg man, responder 1)

The ratios are fast arm over fed arm on days W+2 and W+3, with kcal from `RL.intake_by_day`. "Fast es" is the energy
state at the day-2 meals (08:00, 13:00, 20:00).

| Switch (one at a time, from the shipped path as replayed) | r2 | r3 | fed d2 / d3 | fast d2 / d3 | fast es at the day-2 meals |
|---|---|---|---|---|---|
| baseline: full pipeline, stand-in rate 1.3 | **1.3478** | 0.9620 | 2002 / 1970 | 2699 / 1895 | 1.1441, 1.0902, 1.0126 |
| rate 1.5 (a live idle player: Default class, bills 1.3) | 1.3419 | 0.9742 | 1965 / 1940 | 2637 / 1890 | 1.1341, 1.0813, 1.0115 |
| no stomach delay (eat booked into the body at the eat minute) | 1.3196 | 0.9764 | 2000 / 1964 | 2639 / 1918 | 1.1433, 1.0749, 1.0102 |
| no fatDep in es (partition kept) | 1.3400 | 0.9724 | 1970 / 1944 | 2640 / 1890 | 1.1371, 1.0839, 1.0077 |
| no lean loss (fm still moves) | 1.3507 | 0.9643 | 2002 / 1970 | 2704 / 1900 | 1.1444, 1.0908, 1.0135 |
| no partition (`K.partition.day` a no-op: fm and lm frozen) | 1.3430 | 0.9730 | 1971 / 1945 | 2647 / 1892 | 1.1375, 1.0846, 1.0086 |
| no AT (`atStep` returns 0) | 1.3477 | 0.9620 | 2003 / 1971 | 2699 / 1896 | unchanged |
| no training close (training, strength, TAC, neural all no-ops) | 1.3478 | 0.9620 | 2002 / 1970 | 2699 / 1895 | unchanged |
| es recomputed fresh at the eat (no one-minute stamp lag) | 1.3478 | 0.9620 | 2002 / 1970 | 2699 / 1895 | unchanged |

The table has no separate row for the trailing-24 h ring against the oracle's booking. Both paths use the same
`K.body.trail` window, so the only difference between them is when the kcal land in it, and that is the stomach row.
The request mapping reads `record.body.energyState` as stamped at the end of the previous minute, the same lag the
oracle's `o.es` has.

### Combinations, and each cause's share

| Combination | r2 | r3 | fed d2 / d3 | fast d2 / d3 |
|---|---|---|---|---|
| rate 1.5 + no stomach | 1.3155 | 0.9821 | 1963 / 1937 | 2583 / 1902 |
| rate 1.5 + no partition | 1.3300 | 0.9767 | 1959 / 1937 | 2606 / 1892 |
| rate 1.5 + no fatDep | 1.3273 | 0.9759 | 1959 / 1937 | 2600 / 1891 |
| no stomach + no partition (rate 1.3) | 1.3150 | 0.9857 | 1975 / 1944 | 2597 / 1916 |
| rate 1.5 + no stomach + no partition | **1.3039** | 0.9855 | 1963 / 1937 | 2560 / 1909 |
| ... + no AT + no training | 1.3039 | 0.9855 | 1963 / 1937 | 2560 / 1909 |

A Shapley split of the 0.0439 gap (1.3478 to 1.3039) over the three factors that matter:

- stomach: **-0.027**
- rate: -0.0085
- partition: -0.0082

The rate and the partition interact. At rate 1.3 the fed arm loses fat as well, so fatDep partly cancels between the
arms. At rate 1.5 only the fast arm has any fatDep.

**The shipped behaviour** is the replay with the tool's rate fixed: **1.342 / 0.974**, which is 1.118x S1613 and
still outside 1.1x. Of its 0.038 distance from the oracle's 1.304:

- the stomach: about +0.026 (1.3419 to 1.3155)
- the partition's fatDep: about +0.012 (1.3419 to 1.3300)

### The glycogen log's energy state (the oracle pins 1.0 / 1.087 / 1.13 at 12 / 24 / 36 h of the fast)

| Path | 12 h | 24 h | 36 h |
|---|---|---|---|
| server path, rate 1.3 | 1.0046 | 1.0975 | 1.1441 |
| server path, rate 1.5 | 1.0008 | 1.0874 | 1.1341 |

## 3. The other energy replays through the same full pipeline

| Replay | Oracle pin | Server path, rate 1.3 (the tool as committed) | Server path, rate 1.5 (shipped) |
|---|---|---|---|
| steady eater, days 2-4 over maintenance | 1.0075 / 0.994 / 0.9978 | 1.0129 / 1.0021 / 1.0100 | 1.0083 / 0.9956 / 1.0007 |
| steady eater, es over day 5 | 1.0004 to 1.0005 | 1.0030 to 1.0038 | 1.0007 to 1.0011 |
| six meals against three, es live | 0.994 | 0.9945 | 0.9874 |

At rate 1.5 every reading stays inside its band: STEADY_TOL is 0.03, and the six-against-three band is [0.9, 1.3].
None reproduces its pin to four places.

- **The steady eater's drift is the stomach's.** The 20:00 dinner empties after midnight, and the window is
  hour-slotted. Rate 1.5 with no stomach reads 1.0075 / 0.994 / 0.9981.
- **The rate 1.3 column shows the tool's 111 kcal a day of phantom expenditure.**
- **Six against three: the server path is not the oracle's composition.** On the server path the warm-up eats also
  fill the stomach and the pool, and the writer carries its other factors. The rate 1.3 column's 0.9945 matches the
  0.994 pin only by coincidence: rate 1.5 reads 0.9874.

## 4. The evidence the options are judged against

- **S1613 (Johnstone 2002):** 12.2 against 10.2 MJ, s.e.d. 1.0 MJ, P = 0.049, n = 24, crossover, no certainty
  rating.
  - The 95 % CI of the difference is 2.0 ± 2.07 x 1.0 MJ (t at 23 degrees of freedom), about -0.1 to 4.1 MJ. As a
    ratio over 10.2 MJ that is about **0.99 to 1.40**.
  - The 1.1x band (1.091 to 1.32) is narrower than the study's own uncertainty.
  - 1.342 is a difference of 3.5 MJ, about 1.5 s.e.d. above the mean and inside the CI.
  - On compensation the model runs high. The shipped path makes up about 672 kcal of a 1,949 kcal missed day (34 %).
    The study made up about 2.0 MJ of a fasting deficit of about 12 MJ (17 %), and the oracle's own 1.304 is 30 %.
- **S1614 (Clayton 2016):** day 3 not different (P = 0.557). Every reading here is 0.96 to 0.99, inside 1.1x.
- **Ruling 11d-3:** the fast is a diagnostic replay. "A failure is a finding about the deficit floor to rule on, not
  to patch."
- **Ruling 9c-1:** refit only if every band holds (S1613 within 1.1x, S1614, King steady, Karl BAL and DEF, Whybrow,
  the meal replays). Otherwise S1613 joins #3622 as a named non-reproduction.
- **Rulings 9d-1 and 9d-2:** the energy ladder is 1.10 / 1.25 / 1.40 / 1.55. Under the trailing window the fasting
  plateau sits at es of about 1.13 (rate 1.5 path: 1.134, plus fatDep as the fast goes on).

## 5. The options

### (a) Refit BALANCE_SPAN_KCAL and DEFICIT_FLOOR against the full pipeline

This was swept with the shipped path at rate 1.5 (full-pipeline r2), and the other bands were read on the offline
oracles at the same constants:

| span / floor | full r2 | oracle r2 | Karl DEF (≥ 17.33 to pass) | King (< 3.3 mm) | S1255 (mm) |
|---|---|---|---|---|---|
| 7500 / 1.0 (shipped) | 1.342 | 1.304 | 19.3 | 2.43 | 13.5 |
| 7700 / 1.0 | 1.336 | | 18.1 | | |
| 7800 / 1.0 | 1.332 | | 17.6 | | |
| 7900 / 1.0 | 1.329 | | 17.0 (fails) | | |
| 8000 / 1.0 | 1.326 | | 16.5 (fails) | | |
| 8500 / 1.0 | 1.312 | 1.279 | 14.0 (fails) | 2.14 | 11.9 |
| 9000 / 1.0 | 1.299 | 1.268 | 11.8 (fails) | 2.02 | 11.3 |
| 7500 / 0.8 | 1.298 | 1.270 | 11.7 (fails) | 1.99 | 11.4 |

**Downside: no point holds both bands.** Karl DEF needs a span at or below about 7,830. The full-pipeline fast needs
one at or above about 8,200. A lower floor costs Karl more than a longer span does.

So under ruling 9c-1, (a) cannot ship. The one escape is that Karl's oracle is itself offline: it injects expenditure
and runs no partition. Karl's DEF arm through the full pipeline was not measured here. It might read higher, as the
fast does, but a refit resting on that would need Karl replayed through the server path first.

**Pins that would move:** every deficit-drive pin. That means the fast's 1.304 / 0.986, [1963, 1937] and 2560; its es
log; the steady eater; S1255's 13.5 mm; King's 2.43 mm; Karl's -57.0 / +19.3 and the not-vigorous -45.0 / +55.2; the
golden trace; and the View's ladder reasoning from ruling 9d-2.

### (b) Make the energy oracles run the full pipeline, so the pins are the shipped behaviour

The fast, the steady eater and six-against-three move onto `ServerReplay` with the rate fixed.

**Downsides:**

- (b) does not settle the number. S1613 then reads 1.342, which is 1.118x and fails the 1.1x band test. Under ruling
  11d-3 that failure must still be ruled through (a), (c) or (d).
- The oracle loses its plain-arithmetic transparency. A pin then rests on the adapters, the stand-ins and the replay
  tool, and this finding shows the tool can carry a defect of its own.
- The server replay takes about a second per arm. That cost is negligible.

**Pins that would move:**

- the fast: 1.304 / 0.986 to 1.342 / 0.974; [1963, 1937] to [1965, 1940]; 2560 to 2637
- the fast's es log: [1.0, 1.087, 1.13] to [1.001, 1.087, 1.134]
- the steady eater: [1.0075, 0.994, 0.9978] to [1.0083, 0.9956, 1.0007], and es 1.0004-1.0005 to 1.0007-1.0011
- six against three, es live: 0.994 to 0.987

The held 0.969 is an es-held satiety-only reading, so it could stay offline. The glycogen g values would also need a
re-read on the server path; they were not measured here.

### (c) A mechanism change

The tool's rate is a tool defect, not a mechanism, and it is fixed under any option. Two mechanism variants were
measured.

**(c1) The deficit drive books eaten kcal at the eat.** This adds an appetite ledger in the window. The partition and
the day accumulators stay on the absorbed kcal. Measured as "rate 1.5 + no stomach" with the partition on, it reads
r2 1.3155 / r3 0.9821, which is 1.096x and inside the band by 0.004. The steady eater reads 1.0075 / 0.994 / 0.9981,
on its pins.

Downsides:

- It is physiologically weaker than what ships. `ctx.absorbed` is gastric emptying, the moment intestinal nutrient
  sensing (ghrelin suppression, the incretins) begins. Booking at ingestion would let the drive feel a meal still
  sitting in the stomach.
- It adds a trail key, persisted state and a golden-trace move.
- Its margin is thin.
- It is a game choice with no science row.

**(c2) Gut energy added to eb24h.** Measured, and rejected. r2 reads 1.3197 (1.0998x), but the steady eater's es
falls to 0.965 after dinner. Last night's dinner, still being absorbed into the window, is counted again beside
tonight's meal in the gut, so the steady eater fails STEADY_TOL.

Not a mechanism fix, but a sensitivity worth knowing. Sizing each meal from the written HUNGER instead of the request
mapping (2,600 kcal x HUNGER, the satiety side included) reads r2 1.475 with the fed arm at 2,135 kcal. The labelled
mapping (ruling 11c-31) moves the reading more than any cause above.

### (d) Accept 1.342 (shipped; 1.348 as replayed) as within S1613's own uncertainty

The study's 95 % CI of the ratio is about 0.99 to 1.40. 1.342 is inside it, at about +1.4 s.e.d.

Downsides:

- It loosens a band Angus set (1.1x, ruling 9c-1), and it does so after the fact.
- The model sits in the CI's upper third. Its compensation share (34 %) is twice the study's (17 %), so the deficit
  drive is strong whichever band is used.
- One n = 24 crossover sets the CI. A second study would narrow it.

## 6. Recommendation

**Recommended: (d), carried out through (b), with the replay tool's rate fixed first.**

1. **Fix the tool unconditionally.** The default stand-in rate becomes `K.energy.CLASS_MET.Default`, 1.5, the engine
   value a live idle player reads (#2875), in place of `COMPENDIUM.Default`.
   - This is a Plan 11f tool defect, not a mod change.
   - Every server-path replay at the default rate has billed an idle player at 1.4 MET. Live-mode replays of a ring
     are affected too, because the activity class is not read from the ring (task 2 report, concern 4). Expect an es
     and eb24 drift of about +0.003 over a few days against a live ring until this is fixed.
   - The `test_the_36_h_fast_through_the_server_adapters_is_the_named_gap` pin moves from (1.348, 0.962) to
     (1.342, 0.974).
2. **Run the fast and the steady eater through the server path** and pin the shipped readings (the list under (b)).
   The fit was done on a simplification the mod does not ship. That gap is the root of F-1, and pinning the shipped
   path stops it reopening.
3. **Rule on S1613 under 11d-3** as reproduced within the study's 95 % CI (about 0.99 to 1.40) and outside the 1.1x
   fit band. Both are named in the test and on #3622.

The alternatives were rejected for these reasons:

- **(a):** it cannot hold Karl DEF.
- **(c1):** it buys 0.004 of margin by moving the deficit drive to a less defensible signal time, and adds state.
- **(c2):** it breaks the steady eater.

**The weak spot of the recommendation:** it accepts a model whose compensation share is twice the study's. If Angus
holds the 1.1x band, the only way to ship inside it is (c1), with the downsides above, or (a) once Karl has been
replayed through the full pipeline (not measured here).
