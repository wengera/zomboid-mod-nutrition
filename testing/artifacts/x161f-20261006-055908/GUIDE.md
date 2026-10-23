# `x161f-20261006-055908` reading guide

**`x161f-20261006-055908/fatigue.json`** — produced by `testing/experiments/x161_fatigue.py` on HEAD `4cd19f7` (mod `4cd19f7`, harness Lua `d3554be`, probe `c9b76d0`, all clean) with the driver itself untracked at the run; it is committed unedited beside the artifact
(1113.9 s wall; 7600483 bytes, sha256 `1321af70…7530391c`, byte-for-byte identical to the run copy). **Plan 5 Task 13, acceptance 1 (fatigue, endurance, mood, aim, intoxication)**: one boot of `x16-fatigue`, `SleepAllowed` and `SleepNeeded` true in the server ini at seed, after ready and after the stop;
`Nutrition = false`, DayLength 1, OnsetSpeed 30, Severity 1, one admin character (female, fat 22.4 kg, lean 57.6 kg). `doctor_clean` true; `verify` 12/12 `ok`; `client_lua_error` false and `server_error_count` 0; the effects adapter 1794 minutes with 0 errors, the nutrients adapter 1805 with 0 errors, the handler 10281 calls with 0 failures. This run is the smoke test of `lua.setpath` (`d3554be`). **Skew-free.**

How to read it. Every bus call is a row of `steps`; the arms are in `phases` (their replies and the tags of the reads they took), with `phase_walls` and `mod_error_checks` (empty `found` at every arm). `stats_all` holds every `stats.all` reply of both sides in order with its `phase` and `tag`; `recs` the one-call record reads (30 scalars each, dotted keys flat) and `full` the 27 whole record reads (acute, fluids and effects tables, the body scalars, the 27 nutrient tables); `brackets` the background triples (a record read, a server `stats.all`, a record read) and `bg` the client read beside each; `edits`, `luasets` and `sandbox` the writes; `watches` the eight TKX_StatWatch windows (`A`, `E`, `G`, `G2`, `H`, `F1`, `F2`, `F3`), each damage-tag counter reset to -1 before its window; `mirror_checks` three client mirror requests. `summaries` are the driver's offline kernel recomputes (lupa at `4cd19f7`): `compose` the effects composer on every whole read, `B` the crossing replay and the sleep steps, `C` the fatigue-offset recompute, `D` the window slopes and ratios, `E`, `G`, `H`, `I`, `J`, `K` the arms' fits. The bracket comparison of the FATIGUE writer and of INTOXICATION is post-run arithmetic on `brackets` (the driver's own same-minute test found no bracket inside one slow minute). The ~20x clock of the held sleep ran about 9.57 game hours in 20 s. `zombie.near` spawned no zombie, so the three shots had no target.

- **A (the writer, the caps)**: FATIGUE equal to the float32 of `S + circ + fOff` at all 31 one-minute brackets and between the two records at 129 of 130 two-minute ones; HUNGER held at 0.69, no `HUNGRY` tag; THIRST at most 0.7298415899276733 over the 406 server `stats.all` reads and 0.7347381711006165 at a server `stats.get` (`stats_get[5]`).
- **K (cost)**: `bench_fast` 3.12 (discarded), 3.2 and 3.77 microseconds per call; 10.103 ticks per second.
- **D (the fold)**: `lua.setpath` flipped both flags and back; squat ratios 0.979 and 1.063, resting ratios 0.984 and 0.813 against rmod 1.009 and 0.947; one client copy equal to a handler-written value mid-regeneration.
- **E, E2 (stress)**: up at 0.0720 per game hour to 0.06, held; down at 0.108 after the store came back.
- **G, G2 (food sickness)**: up at 22.30 per game hour to 55, POISON 0; down at 2.70 with the excess dial off.
- **J (Severity)**: the targets 0 at Severity 0, restored at 1.
- **H (beer)**: the per-tick maximum the float32 of the peak target 2.8494; each sip visible for one update.
- **B, SL, C**: crossings within 0.085 to 0.104 game hours of the replay; the held sleep's S fell on the asleep minutes only; `fOff` equal to the kernel's at all 54 coffee reads.
- **F (mood)**: PANIC at about 0.064 throughout; UNHAPPINESS up at 22.0 per game hour, held, released once to 4.1667.
- **I (aim)**: mirror and stub at 1.325; the delay 25.00 at all 1801 samples.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `watches[*].result.dmg.*.count`, `watches[*].result.dmg.*.sum` | -1 | The driver's reset sentinel: -1 means the tag never fired in that window, not a count. |
| `summaries.A.identity` | `same_minute` 0 | The driver's same-minute test compared the first record only and no bracket fell inside one slow minute; the reading is the post-run bracket arithmetic on `brackets`. |
| `summaries.H.pairs` | e.g. `eq_f32` false | The server read was taken before the record read in each poll round, so it carries an earlier minute's target; read `brackets`. |
| `summaries.B.sleep[*].S_pred`, `summaries.B.sleep[*].ratio_pred` | e.g. 0.5710596734818129 | A wholly asleep step; about 15 per cent of the interval's minutes stepped awake; `ratio_pred` is cited only as the falsified wholly-asleep prediction (#3076 does). |
| `summaries.D.x35_client_match_fold_on` | 12 of 73 | Counted over all of phase D, the fold-off windows and the trivial value 1 included. |
| `summaries.D.kernel_fold_rest` | e.g. 2.7599272630962624e-05 | A synthetic per-read delta, not a per-tick one. |
| `summaries.F.unhappy_rise_slope_per_h`, `summaries.E.stress.slope_per_h_all` | -2.802308852215408, 0.0056028670251019805 | Fitted across a release or a hold, not a rise; cite the rise fits. |
| `phases.I.result.shots` | 3 | The shots had no target (`zombie.near` spawned none). |
| `summaries.A.first_effects` | — | Pairs `full[0]`'s mAcc with `recs[0]`'s wall and age. |
| `logs.server_luaerr`, `logs.client_luaerr` | 40 and 38 lines | The first 40 server lines the driver kept (its cap, `logs.limits.luaerr`) and the client's 38, not counts: the full run log matched 141 times (112 harness echoes of the driver's error reads, 24 `AdvancedAnimator` lines, 5 `IsoPropertyType` lines); none is a mod error. |
