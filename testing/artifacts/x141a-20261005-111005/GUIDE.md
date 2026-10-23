# `x141a-20261005-111005` reading guide

**`x141a-20261005-111005/activity_gate.json`** — produced by `testing/experiments/x141_activity_gate.py` on HEAD `b5a39cb` with the driver itself still untracked; it is committed unedited beside the artifact
(606.2 s wall; 1 034 301 bytes, sha256 `a8214c4d…0276b222`, byte-for-byte identical to the run copy). **The activity gate, Plan 3 Task 5**:
one boot of `x14-activity` (PZTestKit + NutritionRevamp Mode 1 + TKX_MetWatch + TKX_XpEvents) at the fixture's 90-minute day,
one admin character. Mod `e6255ba` clean, probe mods `a4f02be`, harness Lua `b246196` clean, `doctor_clean` true; `verify` 6/6 `ok`.
The first live use of `exercise.do`, `action.read`, `player.sprint`, `attack.melee`, `inventory.add` and `TKX_MetWatch`; each answered
in the shape its row names. **Skew-free.**

How to read it. Every bus call is a row of `steps` with its own wall bracket; the arms are in `phases` (`S0` setup, `I` idle, `W` walk,
`RD` book read, `E` eat, `X` squats, `R` walk asked to run, `SP` sprint leg 1 with leg 2 under `phases.SP.leg2`, `L` loaded walk, `M` melee),
each with `polls` (four `witness.chain` reads per poll, client first then server: `getMetabolicTarget`, `getMetabolicRate`, plus the action
table and regularity where named) and `metwatch` (the server's per-tick TKX_MetWatch window at 10 ticks/s: `samples`, the readable `hist`,
the first 50 ticks parsed in `raw`, `new_hist_keys`). `arm_summaries` rolls each arm up; `events` holds every TKX_XpEvents read (strings);
`stats_pairs` every client-first `stats.get` pair. `witness.moddata` walks a dotted key as a path, so the fractional histogram keys
(`hist_rate_2.5`) cannot be read back: their presence is in `new_hist_keys`, their values in `raw` and the polls.

- **X37 (`verdicts.X37`, falsified — the server classifies)**: `getMetabolicTarget` read -1 at every read on both sides and every
  server tick (the client's one exception, 6.0 during the squats, is `ISFitnessAction:update` setting it per frame on the client); the
  target is reset after each update, so the readable value is `getMetabolicRate`. The server's rate held 1.50 at all 300 idle ticks,
  climbed 1.50 → 2.53 over the 30 s walk window (a bounded approach toward Walking5kmh 3.1), held about 3.1 on the walk asked to run,
  climbed 2.99 → 4.97 through the squats (toward Fitness 6.0, with `mv` false at every tick) and reached 3.52 on the walk under 61.1 kg of
  planks (the load factor above 3.1). The client's rate tracked the server's within about 0.3 at every pair, the server's read ahead.
  The sprint class was never reached on either side (leg 1 did not move; leg 2 read about 2.7).
- **Flags (`verdicts.FLAG`)**: the server's `isPlayerMoving` was true in 226/301 walk ticks, 222/300 run ticks, 234/300 loaded
  ticks and 53/141 sprint-leg-2 ticks; its `isRunning` and `isSprinting` were false at every tick of every arm, while the client's sprint
  trace read sprinting and running true at all 56 samples. `stats.get` agreed on both sides (`running`/`sprinting` false).
- **X38 (`verdicts.X38`, falsified — unreadable)**: through `action.read`, `eat.action` and `exercise.do` the client's
  `getCharacterActions` held one action whose table read `caloriesModifier` 0.5, 1 and 3; the server's held none — `size` 0 at
  every poll and `noaction` at every one of the 772 MetWatch ticks across the three arms.
- **X36 (`verdicts.X36`, re-graded)**: regularity(squats) went 0 → 0.80 on both sides over the set, in 0.08 steps on the server's per-tick
  read, and at one pair the server read 0.64 while the client read 0.56. The rise is `exerciseRepeat` → `incRegularity`, run on the server;
  `Fitness.update` (the decay path) was not exercised in a session this short, so the driver's `as_predicted` is the rep path only.
- **X39 rep (`verdicts.X39-rep`)**: the set fired `AddXP` 10 times for Fitness (last amount 4) and 10 times for Strength (last
  amount 0) on the server — one of each per 0.08 regularity step.
- **X39 hit (`verdicts.X39-hit`)**: RCON `createhorde 1 admin` answered an empty reply and a zombie was within 2 tiles 2.8 s later; of five
  `DoAttack(0)` swings `OnWeaponHitXp` fired twice (last hit count 1), Strength `AddXP` +4 and Fitness +2; the zombie survived. The
  per-swing `DoAttack` returns all read `false` and are not a hit count.
- **Errors**: the 13 `ArrayIndexOutOfBounds … Vector.get` exceptions on the server are the 13 server `witness.chain …get(0)` reads
  on an empty action stack; the client's one (it sets `client_lua_error`) is the S0 probe of the same chain. The rest of `server_error_count`
  (51 lines) is boot baseline.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character. |
| `verdicts.X36.verdict`, `summary.verdicts.X36` as "`Fitness.update` ticks" | `as_predicted` | The rise is the rep path (`exerciseRepeat`); the decay tick in `Fitness.update` was not exercised. |
| `arm_summaries.*.metwatch_raw_target`, `.metwatch_raw_rate`, `verdicts.X37.observed.*.raw_rate_max` as a window value | — | The first 50 ticks (5 s) of each window only; read the polls and `new_hist_keys`. |
| `phases.M.result.returns` as hits | `false` ×5 | `DoAttack`'s return is not a hit; `hitxp_count` is. |
| `client_lua_error`, `server_error_count` as mod faults | `true`, 51 | The probe's own `get(0)` on an empty stack plus boot baseline. |
