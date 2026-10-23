# `x141s-20261005-105131` reading guide

**`x141s-20261005-105131/strength_gate.json`** — produced by `testing/experiments/x141_strength_gate.py` on HEAD `e6255ba` with the driver itself still untracked; it is committed unedited beside the artifact
(396.2 s wall; 146 651 bytes, sha256 `1210942a…5362e8538`, byte-for-byte identical to the run copy). **The strength gate, Plan 3 Task 3**:
one boot of `x14-strength` (PZTestKit + NutritionRevamp Mode 1 + TKX_XpEvents + TKX_XpBurst) at the fixture's 90-minute day,
one admin character. Mod `e6255ba` clean, probe mods `2bf87a6`, harness Lua `b246196` clean, `doctor_clean` true; `verify` 4/4 `ok`,
`server_error_count` 0, `client_lua_error` false, `TKX_XpBurst_Installed` and `TKX_XpEvents_Installed` true on the server. The first
live use of `perk.level`, `xp.grant`, `xp.sync` and `witness.chain`; each answered in the shape its row names. **Skew-free.**

How to read it. Every bus call is a row of `steps` with its own wall bracket; the phases are in `phases` (`S0` setup, `S1` grant, `A`
the write and the push window, `R` the forced rust pass, `Y` the admin sync, `B` X39, `D` X48, `C` X40); every `xp.grant` reply is
also in `grants` (`xpBefore`/`xpAfter`/`levelBefore`/`levelAfter`, same server tick), every TKX_XpEvents read in `events` (strings),
every client-first `stats.get` pair in `trait_pairs`. `anticheat.settings` holds the run's own `AntiCheat*` ini values.

- **The starting state**: Strength XP 37500 at level 5 — 37500 is the level-5 cumulative total (#2102), not level 6's as the
  task amendments assumed, so the `S1` grant (+100) crossed nothing and no band trait was ever present: every `traitList` on both
  sides is empty. Server proteins were set 0 before the first grant (`phases.S0.prot_set`).
- **X50 write (`verdicts.X50-write`)**: `perk.level admin Strength 3` replied `before 5, after 3, xp 37600` — the level moved, the XP
  did not.
- **X50 push (`verdicts.X50-push`)**: the server read level 3 and XP 37600 at all 16 `A` samples over 30 s; the client's
  `getPerkLevel(Perks.Strength)` read 3 at its first sample, whose reply came 1.77 s after the write was requested (`steps`
  `a_write`, `a0_client`), and at every later one; the client's XP read 37600 at the window's end.
- **X50 rust (`verdicts.X50-rust`)**: `moddata.set` wrote `strengthUpTimer` as the string "30000"; two ten-minute passes later
  (9:40 and 9:50 game time, `phases.R.clock_polls`) the key read 30020 as a number and `strengthMod` 25 (from 0); the XP fell 37600 →
  37599, the AddXP event fired once with amount -1 and level 3, and the level stayed 3, both sides.
- **X50 sync (`verdicts.X50-sync`, trivial)**: before `xp.sync` the client already read level 3 and XP 37599, equal to the server;
  `called` true; the server read 3 / 37599 at all six samples over 10 s and no event counter moved. The sync could not be told from
  no sync.
- **X50 remap (re-graded from the raw pairs)**: the written level 3 sits in FEEBLE's band (2–4, `XpUpdate.lua`), yet FEEBLE never
  appeared on either side's `traitList` at the three `A` pairs, at `R` or at `Y`, and `levelperk_count` never appeared: the debug
  write ran no remap. The driver graded `trivial` because it keyed on STOUT, which the starting level never gave.
- **X39 AddXP (re-graded)**: the three `B` grants moved `addxp_Strength_count` 2 → 5 with `lastAmount` 10 and `lastLevel` 3; the rust
  step's -1 also fired the event (count 1 → 2 in `R`). The LevelPerk arm was never exercised: no grant crossed a level, so
  `levelperk_*` never appeared. The driver's `falsified` is that unexercised arm, not a finding.
- **X48 (`verdicts.X48`)**: D1, server proteins 199.95 and client copy 199.97: `xp.grant 100` raised XP by 150. D2, server proteins
  0: the client's own `nutrition.set proteins 200` replied 200 and the grant went out in the next bus call (`d2_gap_s` 0.0, reply
  0.51 s later): XP rose by 100; the client then read -0.04 (reverted). For a server-side grant the server's own store gates the
  branch. Between `B` and `D1` the XP fell 37629 → 37627.5 with one extra AddXP event: a second rust step (the three `B` grants had
  pulled the timer back to a new 1200 bucket, #2156) scaled ×1.5 by the 200 protein store — an inference from the counts, no read
  of that step's amount.
- **X40 (`verdicts.X40`)**: under `AntiCheatXP=2` the checker-free burst landed +1000 XP within about 5 s of `fire` (requested 4.0 s after its ack, answered 4.8 s; `phases.C.landed`);
  over the next 80 s five client pings all answered, and no line matching `AC_RX` was written to the server stdout or the client
  console; the checker-refreshing control grant (+1000) gave the same. The user is the admin, whose role carries the
  anti-cheat kick exemption on the desk reading, and the check's own log is on the multiplayer debug channel, so "no line, no kick"
  says nothing about whether the check tripped internally.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character. |
| `verdicts.X50-remap.verdict`, `summary.verdicts.X50-remap` | `trivial` | Keyed on STOUT, which the level-5 start never gave; FEEBLE's absence at level 3 is the reading — see the re-grade above. |
| `verdicts.X39-AddXP.verdict`, `summary.verdicts.X39-AddXP` | `falsified` | The LevelPerk half was never exercised (no crossing); the AddXP half is as predicted. |
| `verdicts.X39-AddXP.observed.levelperk_delta_over_crossing` | 0 | No crossing happened. |
| `verdicts.X40.verdict`, `summary.verdicts.X40` | `falsified` | The prediction left out the admin role's kick exemption and the debug channel of the check's log; read "no kick and no line for the admin". |
| `constants.TARGET_XP`, `constants.L6_TOTAL` | 37600, 37500 | 37500 is the level-5 total, not level 6's. |
| `verdicts.X50-push.observed.client_first_3_after_write_s` | 0.0 | The driver subtracted the wrong wall; the client's first read was answered 1.77 s after the request (`steps.a_write.wall_before`, `steps.a0_client.wall_after`). |
| `verdicts.X50-write`, `summary.verdicts.X50-write` | `as_predicted` | The prediction read `before=6` and the level read 5, so the grade carries the ladder error; read `phases.A.write`. |
