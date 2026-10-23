# `x222d-20261007-080709` reading guide

**`x222d-20261007-080709/clock.json`** and **`x222d-20261007-080709/MANIFEST.json`** — produced by `testing/experiments/x222_clock_cost.py --default`, the same driver unedited after x222's run, on HEAD `e94c36e` (harness Lua `fadf698`, clean; `mod/` not booted)
(252.3 s wall; `clock.json` 80431 bytes, sha256 `50167734…b5438d72608`; `MANIFEST.json` as x222's; both byte-for-byte identical to the run copies). **Plan 10 Task S2+S3, the default-day half of S3.1**: profile `x22-clock-default`, the same frozen copy (`meta.bench_sha256` `8eec9f2f…`), the fixture's own DayLength 4 (1 hour 30 minutes, the value every vanilla preset but SixMonthsLater ships), no `[sandbox.NR]` block, sleep off; every verify row ok; `server_error_count` 0.

- **A**: `options.severity` 1 and `SandboxVars.NR.Severity` 1 (the default, no override: the control for x222's 1.5).
- **B**: 50 ring gaps, mean 37.46 ticks per game minute (28 of 38, 20 of 37, one 29 and one 40), none of 0; `ring.stats` max 40; 10.011 ticks and 0.2665 world minutes per wall second.
- **Z**: no mod error line.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one host. |
| `predictions`, `constants`, `deviations`, `world_changes`, `meta.staged_mod`, `meta.staged_manifest`, `meta.staging_command`, `meta.bench_note`, `meta.frozen_at`, `meta.bench_file`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings (the deviations name x222's phases, which this boot did not run). |
| `phases.B.hist`, `verdicts.B.observed.hist` | `h0` 876, `h1` 24 | Spans the poll window, not the ring's minutes; cite `phases.B.ring.stats`. |
