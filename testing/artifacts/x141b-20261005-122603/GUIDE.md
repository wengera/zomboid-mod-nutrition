# `x141b-20261005-122603` reading guide

**`x141b-20261005-122603/body.json`** — produced by `testing/experiments/x141_body.py` on HEAD `9768ce0` with the driver itself still untracked; run with vanilla `Nutrition` ON against the design precondition (a profile defect, corrected at 3fa45b3): vanilla's per-tick nutrition update ran beside the mod's minute writes, which is the source of the weight residuals (≤ 1e-4 kg) and the store offsets; it is committed unedited beside the artifact
(2022.8 s wall; 14 120 452 bytes, sha256 `4272c248…e828999a`, byte-for-byte identical to the run copy). **Plan 3 acceptance 1, Task 18**:
one boot of `x14-body` (PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on + TKX_MetWatch) at DayLength 1, one admin character.
Mod `9768ce0` clean, probe mod `a4f02be`, harness Lua `b246196` clean, `doctor_clean` true; `verify` 6/6 `ok`; `phase_errors` empty;
`client_lua_error` false; the 10 server error lines are `AdvancedAnimator` boot baseline. **Skew-free.**

How to read it. Every bus call is a row of `steps`; the phases are in `phases` (`A`, `G1`, `D`, `FAST`, `F`, `E1`, `G2`, `E0`). The body
record is read whole with `witness.moddata global:NutritionRevamp.players admin.body` (a table-valued key comes back raw with full-precision
numbers; `phases.A.scalars` shows the same keys as strings). `FAST.cycles` are the ~1-game-hour sample cycles at RCON `settimespeed 5`,
`FAST.bodies` every body read, `FAST.closes` the first read of each `dayIndex`, `FAST.watches` the nine boundary windows (a client
`stats.get` every ~0.5 s from 0.4 game hours before the boundary to 10 s after it, with one server read 0.33–0.90 s after the boundary
estimate; `boundary_epoch_ms_est` is ESTIMATED from the server's `(worldAge, wall)` pairs). `prediction_live` is the header's arithmetic
re-run from the first-sight record; `prediction_apriori` the header's two 80 kg cases.

- **The subject is female** (`body.sex` 2): fm 22.4, lm 57.6, `l0` 5, `traitCarry` 1, `r` 0.748, first sight at world age 3.10. World age 0
  is 07:00 on this fixture (`speed_changes[0]`: world age 7.03 at 14:02), so `dayIndex` closes at 07:00 game time.
- **A (`verdicts.A`, re-graded as predicted)**: fm + lm = 80 exactly = `K.body.split(80, female, no build)`. The grader's `falsified` compared
  the split against the server's drifted weight read (79.99999793, read a few game minutes after first sight) and is wrong. The client mirror
  carried `body_*` zeros (sent at first sight, before the body existed) until the mod's own `requestMirror` was called once; after it,
  `body_fm`/`body_lm`/`body_weight` equal the record's.
- **B (`verdicts.B`, as predicted)**: nine closes; every closed day's balance negative (−1875.6 for the 20.9 h first day, then −2152 down
  to −2072); fm and lm fell at every close and each close's dFM/dLM equals the partition law on the pre-close masses and `eb7[7]` to 1e-6 kg;
  the per-close loss ran 3.5–4.4 % above `prediction_live` (the cold multiplier read 1.020–1.023 against the prediction's 1, about 34 kcal/d
  on REE); 80.00 → 75.67 kg; AT 0 → 0.0061; `energyState` 1.45 → 1.52. Server weight = fm + lm within 1e-3 at 747/747 same-day reads and the
  client's within 1e-3 at 747/747. `dec_after_first_close_both` is NON-DISCRIMINATING: `decWeight` read true on both sides at all 66 day-0
  cycles too, where the mod's 7-day trend is exactly 0 and it writes false — the flags the sides read are vanilla's own `updateWeight`
  writes (the `Nutrition` option is on), not the mod's. `incWeightLot` never true: X25 (#1291) not exercised.
- **Cadence (`cadence`)**: at all nine closes the server's post-close weight was already readable 0.33–0.90 s after the boundary estimate, and the
  client's first read of the new weight came 1.06–1.75 s after the estimate; the client read before it sat 1.0 s earlier (0.05–0.75 s after the boundary estimate, still reading the old weight) (the server read
  blocked the poll), so these are upper bounds only. `decWeight` true on the client at every first read.
- **C (`verdicts.C`, unmeasured)**: no band change — the female subject reached 75.67 kg at the ninth close (the header's female case:
  no crossing within nine closes); `bandChanges` and `bandRepairs` 0 throughout, `pushes` 0.
- **D (`verdicts.D`, as predicted)**: `nutrition.set admin weight 120` answered 120 (the write landed); the first server read, 2.04 game
  minutes later, read 79.99998 and every read over 90 s read fm + lm within 1e-4 (raw maximum 7.5e-5); the client never read 120.
- **F (`verdicts.F`, unmeasured)**: both eats answered `validStart` false with `moodleFoodEaten` 4: the driver's own health control (the
  health-from-food timer written to 20000) holds the FOOD_EATEN moodle at its top level, and vanilla refuses an eat there. The four reads
  show hunger 1 at fill ~1e-33 with `energyState` 1.52 — the form's empty-stomach value, not the floor.
- **E1 (`verdicts.E1`, calories arm as predicted; macro arms trivial)**: the server's calorie store sat within 1.2 kcal of `mirrorLast[1]` and
  of the map recomputed from the record (−1465); proteins/carbs/lipids read −400/−300/−70 within 0.25 — the maps' zero-intake values, since
  no eat landed. `mirrorWrites` tracked `minutes`.
- **E0 (`verdicts.E0`, unmeasured)**: `sandbox.set NR.LegacyMirror false` took the `SandboxOptions:set` route and the option read false, but
  `SandboxVars.NR.LegacyMirror` stayed true and so did `options.legacyMirror` after a poll; `mirrorWrites` kept pace with `minutes`. The apple
  eat was refused as in F.
- **G (`verdicts.G`, as predicted)**: `bench_fast` 3.40/3.08/3.20 µs at the start and 3.06/3.17/3.08 after the fast (Plan 2: 3.06); `tick.rate`
  10.00/10.11 and 10.11/10.00 (Plan 2: 10.01).
- **Controls**: thirst and fatigue pinned to 0 every cycle; the food timer written to 20000 every third cycle; health stayed ≥ 99.99.
  The client's `worldAge` in `stats.get` ran a game day behind the server's and stepped backwards during the fast; nothing is graded on it.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one female admin character. |
| `verdicts.A.verdict`, `summary.verdicts.A`, `verdicts.A.observed.ok_split` | `falsified`, `false` | The split was compared with a drifted later weight read; at 80 kg it matches exactly. |
| `verdicts.B.observed.dec_after_first_close_both` as the mod's flag | `true` | Vanilla's `updateWeight` writes the flags every tick; the day-0 reads are true where the mod writes false. |
| `cadence[*].latency_ms_from_boundary_est` as a latency | 1055.8–1752.6 | Upper bounds against an estimated boundary; the poll before each was 1.0 s earlier. |
| `verdicts.F.observed.reads[*].match`, `.match_no_floor` | `true` | Fill was ~0 (no eat landed); both forms read 1 there. |
| `verdicts.E1.verdict` as the macro mirror | `as_predicted` | No intake landed; proteins/carbs/lipids sat at the zero-intake maps. |
| `prediction_apriori.male80` | — | The subject is female. |
| `FAST.*.client.worldAge`, `FAST.watches[*].client[*].worldAge` | — | The client's world age ran behind and stepped backwards at speed 5. |
