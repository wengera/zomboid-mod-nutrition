# `x161b-20261006-065751` reading guide

**`x161b-20261006-065751/body.json`** — produced by `testing/experiments/x161_body.py` on HEAD `036bcab` (mod `9288c31`, harness Lua `d3554be`, probe `c9b76d0`, all clean) with the driver itself untracked at the run; it is committed unedited beside the artifact
(1341.8 s wall; 7133662 bytes, sha256 `d96e6c38…8f4a944b`, byte-for-byte identical to the run copy). **Plan 5 Task 14, acceptance 2 (traits, healing, bleeding, infection, cold, thermal, toxicity, drains, the PANIC hold, the thirst cap)**: one boot of `x16-body`, `SleepAllowed` and `SleepNeeded` true in the server ini at seed, after ready and after the stop;
`Nutrition = false`, DayLength 1, OnsetSpeed 30, Severity 1, one admin character (female, fat 22.4 kg, lean 57.6 kg). `doctor_clean` true and clean after; `verify` 12/12 `ok`; `client_lua_error` false and `server_error_count` 0; the effects adapter 2761 minutes with 0 errors, the nutrients adapter 2782 with 0 errors, the handler 12585 calls with 0 failures. **Skew-free.**

How to read it. Every bus call is a row of `steps`; the arms are in `phases` (their replies and the tags of the reads they took), with `phase_walls` and `mod_error_checks` (empty `found` after every arm). `recs` are one- or two-call record reads (31 dotted scalars, plus 31 more when the tag carries `_m` reads in `worldAge2`), `full` the 21 whole record reads; `stats_all`, `stats_get`, `health_reads`, `regen_reads`, `temps` (`temp.core`), `chains` (`witness.chain`), `part_reads` and `part_writes` (`bodypart.get` and `.set`), `stat_writes`, `edits` (`globalmoddata.setpath`) and `sandbox` hold every reply in order with its `phase` and `tag`; `watches` the six TKX_StatWatch windows (`G1`, `G3`, `K1`, `K2`, `L`, `H`), each damage-tag counter reset to -1 before its window; `mirror_checks` three client mirror requests. Tags are not all unique: the `stats_get` and `steps` tags `A1_s<i>` repeat across arms A1, A3 and A4 (the driver's helper named them for A1), `health_reads` carries `I_h0` twice (indices 52, the read before the edit, and 53, the window's first) and `edits` carries `BR_w0` twice; read those by position. A record read lists a `false` leaf among `missing` (the witness walk turns `false` into nil), so `own.nv` and `own.ss` false are read off `full[*].effects.own`. The harness's trait checks `phases.A.remove.before/after` and `phases.A.foreign_rm.before/after` read false by a quirk (`TK.hasTraitName` lower-cases NIGHT_VISION to night_vision, the list key being nightvision): read `traitList` or the `stats_get` trait lists. `summaries` are the driver's offline kernel recomputes (lupa at `9288c31`): `compose` the composer and the drain on every whole read, and the arms' fits; slopes are fitted against the wall clock and converted by the window's world age. `.superpowers/sdd/2026-10-06-plan-5-effects/task-14-analysis.py` reproduces the post-run arithmetic (the PANIC matches and client lags, the client infection brackets, the night-vision bracket). The held sleep's ~20x clock ran 49.53 game hours in 93.3 s.

- **A (night vision)**: granted at 14.00073130130767 days, the client inside the preceding read's round trip; put back after a removal; withdrawn at grade 2; a foreign trait kept; the counter falls on carotene alone.
- **B (Short Sighted)**: on the client 252 ms after the edit's request, the sight range 6 to 2; off at Severity 0.5 and at grade 3.
- **C, D0, D1, E (folds)**: scratch 0.6785 of the idle rate, bleed 0.8002, infection 2.3055.
- **H, I (drains)**: health at 1.0010 and 1.0055 times the iron and scurvy rates; the kill dial off stops the drain.
- **BR (bruise)**: one bruise in 49.53 game hours against 1.03 expected.
- **K (PANIC)**: held at each target from the first sample that left 0 (raw_8 at the first); the fall at 0.1796 a tick to the lower target.
- **L (thirst)**: THIRST at 0.8299999833106995 at every server read.
- **F, G (unmeasured halves)**: catchACold never rose under the climate override; the core never crossed the thermal target.
- **J (cost)**: `bench_fast` 3.01 (discarded), 4.44 and 3.64 microseconds per call; 10.104 ticks per second.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `watches[*].result.dmg.*.count`, `watches[*].result.dmg.*.sum` | -1 | The driver's reset sentinel: -1 means the tag never fired in that window, not a count. |
| `recs[*].effects.own.nv`, `recs[*].effects.own.ss` | null | The witness walk turns a `false` leaf into nil, so a false flag reads null; read `full[*].effects.own`. |
| `phases.A.withdrawn`, `phases.B.sev05_removed`, `phases.B.g3_removed` | false | The driver's stop test waited for `own` false, which a record read never shows; the removals are the server's trait list (`stats_get`). |
| `summaries.BR.p_ge1_per_day` | 0.3934693402873666 | The Poisson form 1 - e^-0.5 the driver used, not I-F4's per-minute product 0.39352200042286156. |
| `summaries.G.G2.offset_last5_mean`, `summaries.G.G3.offset_last5_mean`, `summaries.G.G4.offset_last5_mean` | -0.34945526123046877, -0.141107177734375, -0.10855484008789062 | Not a steady offset: G2 is mid-squat and G3, G4 run with no target; the resting reading is `summaries.G.G1.offset_last5_mean`. |
| `logs.server_luaerr`, `logs.client_luaerr` | 40 and 24 lines | The first 40 server lines the driver kept (its cap, `logs.limits.luaerr`) and the client's 24, not counts: the full run log matched 147 times (118 harness echoes of the driver's error reads, 24 `AdvancedAnimator` lines, 5 `IsoPropertyType` lines); none is a mod error. |
