# `x141b2-20261005-144202` reading guide

**`x141b2-20261005-144202/body2.json`** — produced by `testing/experiments/x141b2_body.py` on HEAD `a13ffee` with the driver itself still untracked; it is committed unedited beside the artifact
(677.9 s wall; 2 516 925 bytes, sha256 `03ce8865…aa49b5f649`, byte-for-byte identical to the run copy). **Plan 3, the second acceptance boot on the fixed tree**:
one boot of `x14-body` (PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on + TKX_MetWatch, `Nutrition = false`) at DayLength 1, one admin character.
Mod `ca9ab9f` clean, harness Lua `e4fb101` clean, `doctor_clean` true; `verify` 6/6 `ok`; `phase_errors` empty; `client_lua_error` false.
The 7 server error lines are the `AdvancedAnimator` boot baseline, one harness command-file collision (`pzt-cmd.txt` in use) and the two
`ISEatFoodAction.new` raises of the E arm (below). **Skew-free.**

How to read it. Every bus call is a row of `steps`; `stats.get` acks are stored trimmed to the driver's `STAT_KEYS`. The body record is
read whole with `witness.moddata global:NutritionRevamp.players admin.body` (raw numbers). `FAST.cycles` are the sample cycles at RCON
`settimespeed 5` (a server and a client `stats.get`, the body read; the weight counters every third), `FAST.watches` the two boundary
windows (server and client `stats.get` alternating from 0.3 game hours before the boundary to 8 s after it; the boundary epoch is
ESTIMATED from the cycles' (age, wall) pairs), `FAST.lot` the day-1 interlude at speed 1 (the lot edit, then the band edit).
`logs.precondition_lines` and `logs.readtype_lines` count the whole server log's matches.

- **The subject** is the default fixture's female admin: fm 22.400000000000002, lm 57.599999999999994; first sight at world age 3.07.
- **P (as predicted)**: `SandboxVars.Nutrition` read false on both sides, `options.nutritionOn` false, `preconditionWarnings` 0, no
  "expects SandboxVars.Nutrition" line; the self-report ends `nutritionOn=false`; the run's `pzt_SandboxVars.lua` holds `Nutrition = false`.
- **C (as predicted)**: 5 s after the body was first readable, with no harness `requestMirror`, the client mirror read `body_fm`
  22.400000000000002, `body_weight` 80, `body_band` normal; `received` 1; `firstSightMirrors` 1. The mod's own OnGameStart request also
  exists; with one mirror received the run does not tell which send it was.
- **A0 (server half as predicted; client half non-discriminating)**: all 55 day-0 cycles (world age 3.8–23.1) read the three flags false
  on the server and on the client. The client read the three flags false at EVERY read of the session (A1, L).
- **A1 (server as predicted; client falsified)**: close 1 at world age 24 left fm 22.2363, lm 57.4171 (w 79.6534, `mass7[7]` 79.6534,
  `eb7[7]` −1877.7); the server read `decWeight` true 0.46 s after the boundary estimate and at every later read; the client read it
  false at every read. The server's three flags equal `K.body.flags(K.body.trend(mass7, w))` at every cycle (0 mismatches). The client
  weight followed the server: new weight 0.65 s (close 1) and 1.33 s (close 2) after the boundary estimate, 1.44 s after the lot edit.
- **L (server as predicted; client falsified)**: `globalmoddata.setpath NutritionRevamp.players admin.body.fm 23.836289` answered ok
  (before 22.2363, after 23.8363); trend +0.179; the server read inc and lot true, dec false 0.84 s after the set (speed 1) and at all
  13 reads over 10 s; the client read 81.2534 but all three flags false.
- **B (as predicted)**: the band edit set fm 17.682865 (w 75.10); close 2 at world age 48 left w 74.4716, band `underweight`;
  `bandChanges` 0 → 1, `pushes` 0 → 1, Strength `writes`/`pushes` 0 throughout. The server's first read with UNDERWEIGHT came 134 ms after
  the boundary estimate; the client's `trait.watch` tick at 61 ms after it (before the server's poll); `bandRepairs` 0 at 36 and 75
  slow minutes later; UNDERWEIGHT on both sides then.
- **F blend (as predicted)**: at all 123 record reads `mirrorLast[1]` and `energyState` equal the hours-since-close form exactly (0 error);
  at the 68 reads where the clock form differs by more than 5 kcal (by about 550 kcal on day 1) none matched it.
- **E (unmeasured)**: both eats answered `validStart` true with `spawned` client, then raised server-side in `ISEatFoodAction.new`
  (`getContainer` of nil): the item existed only on the client, so nothing landed (fill ~1e-8, hunger 1 at E 1.608).
- **M (as predicted)**: with the mirror on a server `nutrition.set admin calories 500` read back −2117.2 at the first read; `sandbox.var
  NR.LegacyMirror false` answered ok (before true, after false); `options.legacyMirror` read false (readAt poll); `mirrorWrites` held
  3153 while `minutes` went 3161 → 3188; the same write of 500 held at 500 on the server and the client at all 8 reads over 13.4 s.
- **G (unmeasured)**: `exercise.do pushups 20` answered `queued` with `queueLen` 3 (the two failed eats still queued); `reps` stayed 0;
  0 readType lines, which is non-discriminating with no rep.
- **Z (falsified as a smoke test)**: `zombie.near 2` answered ok false, spawned 0 of 2, no raise, on this fixture (`Zombies = 6`).
- **Controls**: thirst and fatigue pinned 0 every third cycle; no food-timer write; health 72.9 at the fast's end.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one female admin character. |
| `verdicts.A0.verdict` as a client reading | `as_predicted` | The client read the flags false at every read of the session, so its day-0 half discriminates nothing. |
| `verdicts.E.observed.rows[*].match` | `true` | Nothing landed; at fill ~0 both forms read 1. |
| `verdicts.G.observed.log_total_at_end` as the fix's proof | 0 | No rep ran. |
| `phases.FAST.watches[*].boundary_epoch_ms_est` as a stamp | — | Estimated from the cycles' (age, wall) pairs. |
