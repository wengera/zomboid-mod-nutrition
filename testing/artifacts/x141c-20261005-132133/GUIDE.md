# `x141c-20261005-132133` reading guide

**`x141c-20261005-132133/clamp.json`** — produced by `testing/experiments/x141_clamp.py` on HEAD `3fa45b3` with the driver itself still untracked; it is committed unedited beside the artifact
(1653.1 s wall; 2 498 828 bytes, sha256 `a8728ca6…9776a636b`, byte-for-byte identical to the run copy). **Plan 3 acceptance 2, Task 19**:
one boot of `x14-clamp` (PZTestKit + NutritionRevamp Mode 1 + TKX_XpEvents, `Nutrition = false`) at DayLength 1, one admin character.
Mod `9768ce0` clean, probe mod `2bf87a6`, harness Lua `b246196` clean, `doctor_clean` true; `verify` 6/6 `ok`; `phase_errors` empty;
`client_lua_error` false. Of the 61 server error lines, 10 are the `AdvancedAnimator` boot baseline and the rest are one
`readType` stack trace per exercise rep (see D). **Skew-free.**

How to read it. Every bus call is a row of `steps` (acks of `stats.get`, `witness.moddata` and a few others are stored trimmed to the
keys the driver's `COMPACT` or `keep` names). The phases are in `phases` (`P0`, `C`, `H1`, `X`, `R`, `U`, `F`, `H2`, `D`, `T`, `M`).
**The instrument is not a record edit**: no harness command writes a nested global-modData key (`globalmoddata.set` writes one
top-level key) and there is no eval command, so the ceiling was driven by a timed fast, the policy's target by server `xp.grant`s
(each divided by vanilla's protein multiplier 0.7, the store reading −400), and `rmod` by the model's own fasting close. Record
scalars are read as strings with `witness.moddata global:NutritionRevamp.players admin.body.<key>`; the `*_body` reads are the whole
table (raw numbers). `trait_pairs` holds every client/server band-trait read; `events` every TKX_XpEvents read.

- **The subject** is the default fixture's female admin: fm 22.400000000000002, lm 57.599999999999994, `l0` 5, `traitCarry` 1, Strength XP
  37500 at level 5; first sight at world age 3.10; `dayIndex` 0 runs to world age 24.
- **parity (`verdicts.parity`, as predicted)**: `tac`, `dmod` and `rmod` read the string `"1"` at first sight; `pPrevKg` read `"0.8"`.
- **carry (`verdicts.carry`, as predicted)**: `getMaxWeightDelta` 1 = `body.delta` 1 = `traitCarry` × (1 + 0). `carry.set admin 2.0` answered
  `after` 2; the first read, issued as the set returned, already read 1; `carryWrites` 0 → 1. The client's `getMaxWeightDelta` read 1.
- **X (`verdicts.X-clamp`, `verdicts.X39-LevelPerk`, as predicted)**: the grant took XP 37500 → 67600 with `levelAfter` 6 in the grant's
  tick; the server read level 5 within 0.76 s (the read issued as the grant returned) and at all 11 samples over 30 s, the client 5 at all 11, XP 67600 throughout, through an
  `xp.sync` at 15 s. `writes` 0 → 1 and `pushes` 0 → 1: the clamp's remap at 5 removed a band trait, the STOUT vanilla's level-up
  listener had added. STOUT was on neither side's trait list at any read, and the client's 40 s `trait.watch stout` never saw it.
  TKX_XpEvents: `levelperk_count` 0 → 1, `lastPerk` Strength, `lastLevel` 6, `lastGained` true.
- **R (`verdicts.R-reassert`, as predicted)**: `perk.level admin Strength 3` answered before 5, after 3, XP 67600; the read 0.46 s later and
  every read over 8 s read 5; `writes` 1 → 2, `pushes` unchanged.
- **U (`verdicts.U-rise`: the grader's `falsified` is wrong; re-graded as predicted)**: the grant to 17600 put Java at 3 (`levelAfter` 3);
  vanilla's LoseLevel loop fired `LevelPerk` twice (count 1 → 3) and its listener put FEEBLE on the server, and the client's watch saw
  FEEBLE (`watch_result_drop`), with no mod write: the mod read Java 3 = desired 3 and wrote nothing (`writes` stayed 2). The record's
  `lastFallAge` 7.4168 stamps the drop minute. At drop + 2.13 h the grant back to 67600 put Java at 6 (`LevelPerk` count 3 → 6); the
  next minute wrote 3 (`writes` 3) with one push (`pushes` 2: the STOUT vanilla added, removed; never seen on the client). `shownL` rose
  3 → 4 at the minute `riseHeldH` passed 6 (last read 5.9506, then 0), Java 4, no push (`writes` 4, `pushes` 2), and 4 → 5 one hold later
  (last read 5.9663, then 0; `strAgeH` 13.418 → 19.435), FEEBLE removed with one push (`writes` 5, `pushes` 3). The grader measured
  from `age_drop`, the read about 0.016 h after the drop minute, and called 5.98 h short of 6.
- **F (`verdicts.F-fall`, as predicted)**: closes 1–3 left the record ceiling at 5 (x 5.393, 5.250, 5.112); close 4 (lm 56.373, cumDef
  7251, x 4.979) gave 4. `lastFallAge` 96.0053, 0.32 game minutes after the boundary; the server read Java 4 with XP 67600; `writes`
  5 → 6, `pushes` 3 → 4. The client's `trait.watch feeble` first saw FEEBLE at epoch 1791222153.377, about 0.09 s after the boundary
  estimated from the cycles' (age, epoch) pairs (153.29) and 0.05 s after the fall minute's (153.33). Both are estimates, not stamps.
  12 samples over 30 s at speed 1 read 4 on both sides, XP 67600 and FEEBLE on both sides, through an `xp.sync` at 12 s. The kernel
  a-priori said close 5 and x141b's measured trajectory said close 4. The pacing (one level per game hour) was not exercised, because
  the ceiling fell one level.
- **T (`verdicts.T-tac`: the grader's `falsified` comes from its own ring choice; re-graded)**: across the fast tac went 1 → 0.997619 (the loss
  branch), then +6.75e-5, +6.55e-5, +6.37e-5 (the gain branch at gnut 0.425). rmod = tac^1.2 × 0.85 (0.84757…0.84784) and dmod = tac^−0.8.
  At the close after the training set the post-close tac 0.9978776357230856 equals, bit for bit, `tacDay` on the PRE-close ring (all seven
  slots 0, target 1). `Metabolism.closeDay` reads `weekMinutes` before `K.training.closeDay` shifts the day's 27.96 band minutes into the
  ring, so a day's training reaches tac one close late. The grader read the post-shift ring (m1 27.96). No tac > 1.
- **H (`verdicts.H-rmod`, falsified)**: endurance slopes over the 46 asleep reads of each hold (endurance < 0.95) were H1 0.1808 per game
  hour at rmod 1 and H2 0.1635 at rmod 0.84777. The ratio, 0.904, falls outside the predicted [0.848, 0.860] and the falsifier band [0.80, 0.90].
  The H2 hold is slower, as an rmod applied to part of the updates makes it, but by less than the #2840 mix predicts: under f = 2 the
  ratio implies about 46 % of the regenerating weight on the asleep arm. Fatigue read 0 at every in-hold read of both holds.
- **D (`verdicts.D-reps`, as predicted on a thin sample)**: squats ran about 3–5 s of their 25 s (`getCurrentExe` was nil from the third poll)
  and gave ONE rep: Strength event 1 (amount 0), Fitness 1 (amount 4), `reps` +1, `paired` +1, vStr +0.0398, vHyp +0.0497. Push-ups ran
  about 10 s and gave 9 reps: Strength events 9 (last amount 4.2 = 6 × 0.7), Fitness events 9 at amount 0 (the Fitness event FIRES at 0),
  `reps` +9, `paired` +9, `ignored` 0, vStr +0.7178 (0.0798 a rep), vHyp +0.8973 (0.0997 a rep). Every rep's `exe.type` read raised
  `attempted index: type of non-table: Fitness$FitnessExercise` inside the adapter's pcall (the server log's stack traces), so the
  class came from the Strength amount.
- **M (`verdicts.D-hits`, unmeasured)**: two RCON `createhorde 1 admin` were sent ("Horde spawned." and an empty reply). No zombie came within 2
  tiles in 50 s, and all 21 `attack.melee` attempts answered `ok` false.
- **Controls**: thirst and fatigue pinned 0; the food timer written 20000 during the fast; endurance 0.05 before each hold and 1 after.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one female admin character. |
| `verdicts.U-rise.verdict`, `summary.verdicts.U-rise` | `falsified` | `age_drop` is the read after the drop minute; the record's `riseHeldH` reached 6 at each rise. |
| `verdicts.T-tac.verdict`, `summary.verdicts.T-tac`, `verdicts.T-tac.observed.tac_pred` | `falsified`, 0.99870 | The grader used the post-shift ring; tacDay runs before the shift. |
| `verdicts.H-rmod.observed.band` as a prediction that held | [0.848, 0.860] | The ratio read 0.904. |
| `verdicts.D-reps.observed.squats` as a rep rate | 1 rep | The squat set stopped after ~3–5 s for a reason the run does not show. |
| `phases.C.reads[*].dt` as a re-assert latency | 0.0 | The first read was issued as the set returned; it bounds nothing below. |
