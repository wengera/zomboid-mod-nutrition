# `x132r-20261005-072441` reading guide

**`x132r-20261005-072441/residual.json`** — produced by `testing/experiments/x132_residual.py` at commit `a02e8d9`
(484.3 s wall; 196 600 bytes, sha256 `d81241f2…80684213`, byte-for-byte identical to the run copy). **The Plan 1
residual arms, session 2, two boots**: `boots.A` under `nr-overlay` (Mode 2, `registered` false) and
`boots.B` under `x13-residual` (Mode 1 takeover beside TKX_CalcStats, `registered` true), both at
DayLength 1. Mod `9f53324`, TKX_CalcStats `8783438`, harness Lua `7710d2d` clean, `doctor_clean true` before
each boot; `verify` 4/4 and 6/6 `ok`, `server_error_count` 0, `client_lua_error` false,
`field_count_failures` and `non_finite` empty, the fast handler's `failures` 0. A first launch of this driver
(`x132r-20261005-072422`) was stopped while boot A's server was starting, before any reading; its run dir
is not evidence. **Skew-free.**

How to read it. Every read is a client-first `stats.get` pair in `boots.*.pairs`, tagged by `window`: `W1`
idle 30 s, `W2` run 30 s (`player.run 20 0`, re-issued reversed whenever the client read not moving;
acks in `boots.*.runs`), `W3` settle, `W4` asleep (`player.sleep.hold admin 60` at `boots.*.sleep_hold`,
pairs every 5 s for 62 s), `W5` after `player.sleep admin false`. Then `boots.*.x4`, six Hearty Appetite
trials alternating push and no-push. Rates are least-squares slopes against the server's own world age.

- **X4 push (`verdicts.X4-push`, settled)**: push arrivals (client first-tick stamp minus the server's
  `wallAfter`) 30, 28, 18 ms (A) and 32, 17, 30 ms (B); no-push arrivals bracketed by the driver's epoch
  around `trait.set` 116–628, 53–570, 62–574 ms (A) and 156–663, 370–1 133, 304–565 ms (B); the trait on
  both sides' `traitList` after every add; removals seen by polling within 0.8–1.6 s.
- **The asleep hold (re-graded from the raw pairs)**: the server's `asleep` read true at the first twelve
  `W4` reads of each boot and false at the last two, which fell after the hold's 60 s deadline
  (`boots.*.sleep_hold.deadlineWall`); the client's `asleep` read false at all fourteen. Over the twelve
  in-hold reads thirst rose at 0.007385 per game-hour (A) and 0.007400 (B), difference 1.5e-5 against the
  band 1.48e-4; awake (`W1`) both read 0.0288. Fatigue read 0 and endurance 1 throughout `W4` in both boots;
  hunger rose 0.0076 per game-hour (A) and 0.133 (B, the stomach-fill model) — recorded, not graded. The twelve in-hold reads show the flag set at sample time; about 15 % of stat updates still ran awake (f = 0.150, a refit from the thirst and hunger slopes, not an artifact key), so the in-hold slopes are an ≈85/15 asleep/awake mix and not the asleep rate.
- **The run arm (`verdicts.X34-running`, unmeasured, correctly)**: every `player.run` ack read
  `setRunning`, `setForceRun` and `setPathfindRunning` true and `clientRunning` true at the call, yet every
  later read was `running false` on both sides (16 of 16 per boot) with `moving` true at 14; thirst's W2/W1
  ratio 1.0000 in both — a walk.
- **X35 (`verdicts.X35`, unmeasured by design)**: no handler writes the 0.4242 sentinel; the `W2`
  endurance pairs (1.0 throughout) are recorded only.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 2` boots, one fixture at DayLength 1, one admin character, rested at the start. |
| `verdicts.X34-asleep.verdict`, `summary.verdicts.X34-asleep` | `unmeasured` | The driver required every `W4` read asleep, but its 62 s window outran the 60 s hold by two reads; read `boots.*.pairs` (`W4`) and the re-grade above. |
| `verdicts.X34-asleep.observed.per_boot.*.thirst`, `.fatigue_all`, `.fatigue_second_half`, `.hunger`, `.endurance`, `.held`, `.thirst_vs_0477`, `verdicts.X34-asleep.observed.thirst_band`, `.fatigue_band` | slopes 0.0081 / 0.0082 and derived | The fits include the two awake reads after the hold ended; refit over the in-hold reads. |
| `verdicts.X4-push.observed.nopush_ms_range` as a latency | 53–1 133 ms | A bracket around the command's round trip, not an arrival time; only its lower bound is compared. |
