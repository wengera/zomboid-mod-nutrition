# `x244b-20261007-181148` reading guide

**`x244b-20261007-181148/notice.json`**, **`x244b-20261007-181148/MANIFEST.json`**, **`x244b-20261007-181148/gc.log`** and the 14 **`x244b-20261007-181148/posring/world-posring-<arm>_<user>.json`** — produced by `testing/experiments/x244b_notice.py`, written before the boot and committed at `71271bc` with the profile `testing/profiles/x24-notice-b.toml`, then edited once before its boot and committed at `dbb78a8` (after x244a's run: the S0 RCON teleport and the empty-series guard in the rule), unedited since, on HEAD `dbb78a8` (harness Lua `e15a9ca`, clean; harness Python `ed4ac93`; `mod/` not booted)
(1003.2 s wall; `notice.json` 1379939 bytes, sha256 `f79a7f92…4fa9d52a`, `gc.log` 308634 bytes, sha256 `d35afc63…ac45395e`, the client ring documents 4121497 bytes in all; every file byte-for-byte identical to the run copies, copied by the driver; `MANIFEST.json` sha256 `c86e295a…2415b389`). **Plan 10c Task H4 session b, N = 60 at the 37-tick spacing.** Phase M set `time.multiplier 0.1674` live (the reply read the multiplier back as 0.8010; `TK.H0.tpmSeen` 37 ticks a game minute, 0.242 world minutes a wall second, `phases.M`). Every verify row ok; `server_error_count` 0; `admin` not parked; free memory fell to 0.78 GB. Phase order S0, M, I, `burst1`, `b15_1`, `burst2`, `b15_2`, `b15_3`, `burst3`, Z.

How to read it. As `x244a-20261007-174509`'s guide. Each arm holds 26 or 27 minute frames, so a minute-frame p99 is its max (`do-not-cite.csv`), the client rule's per-minute rates rest on 26 or 27 minute frames, and the control shift is about 1867 ms. **The RCON teleport did nothing**: both `teleport "bob" "admin"` and `teleport bob admin` replied an empty string and the players stayed 247.9 tiles apart (`phases.S0.teleports`), so as in session a the client reading is admin's far-player stream, and bob's series is empty (graded `unmeasured` here). C and RULE are falsified for that reason.

| arm | frames (minute) | busy p50 / p99 / max | minute busy p50 / max | end-to-end period p99 / max | longest window | adds: period p99, longest window | busy a game minute over idle | ghost ms a minute event | starved / minute events | ghost ms a run |
|---|---|---|---|---|---|---|---|---|---|---|
| I | 1033 (27) | 1 / 4 / 6 | 3 / 6 | 104 / 106 | 106 | — | (50.2 absolute) | — | — | — |
| burst1 | 1032 (26) | 1 / 52 / 72 | 50 / 72 | 150 / 174 | 173 | 46, 67 | 39.66 | 48.66 | 0 / 29 | 0.839 |
| b15_1 | 1033 (27) | 1 / 18 / 25 | 16 / 25 | 117 / 123 | 123 | 13, 17 | 35.41 | 49.61 | 0 / 28 | 0.855 |
| burst2 | 1017 (26) | 1 / 49 / 68 | 49 / 68 | 149 / 168 | 169 | 45, 63 | 29.05 | 47.72 | 0 / 29 | 0.823 |
| b15_2 | 1020 (27) | 1 / 18 / 20 | 16 / 20 | 116 / 123 | 123 | 12, 17 | 26.41 | 49.62 | 0 / 29 | 0.856 |
| b15_3 | 1033 (27) | 1 / 17 / 22 | 15 / 22 | 116 / 123 | 123 | 12, 17 | 31.00 | 50.64 | 0 / 28 | 0.873 |
| burst3 | 1026 (26) | 1 / 48 / 56 | 46 / 56 | 147 / 153 | 153 | 43, 47 | 20.01 | 44.83 | 0 / 29 | 0.773 |

| arm | client | frames in span | client frame p50 / p99 / max | stamp gaps n, p50 / p99 / max | stamp gaps >= 100 ms: lined / control | move gaps n, p50 / p99 / max | move gaps >= 100 ms: lined / control | all move gaps lined / control |
|---|---|---|---|---|---|---|---|---|
| I | admin | 6223 | 17 / 19 / 23 | 224, 399 / 817 / 817 | 39 / 37 | 0, None / None / None | 0 / 0 | 0 / 0 |
| I | bob | 6222 | 17 / 19 / 20 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst1 | admin | 6247 | 17 / 19 / 22 | 288, 201 / 817 / 818 | 42 / 40 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst1 | bob | 6246 | 17 / 19 / 27 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_1 | admin | 6223 | 17 / 19 / 22 | 223, 400 / 817 / 817 | 39 / 40 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_1 | bob | 6222 | 17 / 19 / 21 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst2 | admin | 6127 | 17 / 19 / 22 | 216, 400 / 817 / 817 | 39 / 36 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst2 | bob | 6126 | 17 / 18 / 20 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_2 | admin | 6144 | 17 / 19 / 22 | 260, 316 / 817 / 817 | 42 / 41 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_2 | bob | 6144 | 17 / 18 / 20 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_3 | admin | 6211 | 17 / 19 / 30 | 264, 299 / 816 / 818 | 42 / 40 | 0, None / None / None | 0 / 0 | 0 / 0 |
| b15_3 | bob | 6210 | 17 / 18 / 27 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst3 | admin | 6179 | 17 / 19 / 22 | 234, 400 / 817 / 818 | 40 / 37 | 0, None / None / None | 0 / 0 | 0 / 0 |
| burst3 | bob | 6179 | 17 / 18 / 33 | 0, None / None / None | 0 / 0 | 0, None / None / None | 0 / 0 | 0 / 0 |

- **The client rule on admin's far-player stream**: no draw showed lined-up gaps beyond the control (39–42 against 36–41); the stamp gaps' max read 817–818 ms in every arm, the idle arm's included. No client frame reached 100 ms (max 20–33 ms).
- **Decision 6, three draws**: `burst` added 43–46 ms at the period p99 and 47–67 ms to the longest window (153–173 ms); `budget15` added 12–13 ms and 17 ms (123 ms) in every draw; no ghost starved. Ghost ms a minute event: `burst` 44.83–48.66 (mean 47.07), `budget15` 49.61–50.64 (mean 49.96), a ratio of 1.061; the busy a game minute over idle gives 1.046, but that figure moved from 20.01 to 39.66 between the burst draws, which is the idle drift at 37 ticks a minute, not the load (`x243c` and the H3 review).
- **The GC log**: 158 pauses, the largest 0.529 ms; inside the arms at most 0.058 ms; 31 allocation stalls, the longest 216.502 ms, at 33.79 to 34.19 s of JVM uptime (`gc.events.25.up_ms` to `gc.events.59.up_ms`), during boot, before any arm.
- **Verdicts**: I, F, A6, B15P, B15S, TOT, S, G and Z as predicted; C and RULE falsified (bob's empty ring; the far-player stream).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters, one host, both clients on the server's host; ghost records are cost, not behaviour. |
| `session`, `predictions`, `constants`, `deviations`, `world_changes`, `meta.*_note`, `meta.staging`, `verdicts.*.predicted`, `summaries.decision6.budget15_ruling2.empty_check_clause` | the driver's tables and text | Written before the run; not readings. |
| `summaries.<arm>.busy_minute.p99`, `summaries.<arm>.ghostMs_minute.p99` | the max | Nearest rank over 26 or 27 minute frames: the p99 is not reachable; read `.max`. |
| `summaries.clients.<arm>.bob.stamp`, `summaries.clients.<arm>.bob.move`, `summaries.clients.<arm>.admin.move`, `summaries.client_rule.bob`, `summaries.client_rule.session_outcome`, `verdicts.RULE.observed.bob`, `verdicts.RULE.observed.session` | empty series; `unmeasured`; `mixed` | As in session a. |
| `summaries.*.n_eq_band`, `summaries.*.ghost_over_fed_calibration`; the `avg` keys; the replies, copies and headers under `phases.<arm>` | — | As in session a (each listed in `do-not-cite.csv`). |
