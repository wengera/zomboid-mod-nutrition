# `x244c-20261007-182845` reading guide

**`x244c-20261007-182845/notice.json`**, **`x244c-20261007-182845/MANIFEST.json`**, **`x244c-20261007-182845/gc.log`** and the 14 **`x244c-20261007-182845/posring/world-posring-<arm>_<user>.json`** — produced by `testing/experiments/x244c_notice.py`, written before the boot and committed at `6df7f07` with the profile `testing/profiles/x24-notice-c.toml` before the run, unedited since, on HEAD `6df7f07` (harness Lua `e15a9ca`, clean; harness Python `ed4ac93`; `mod/` not booted)
(917.7 s wall; `notice.json` 1399415 bytes, sha256 `1c669df4…6967dcbb`, `gc.log` 344952 bytes, sha256 `38b331ef…1ef3ee85`, the client ring documents 5014089 bytes in all; every file byte-for-byte identical to the run copies, copied by the driver; `MANIFEST.json` sha256 `c86e295a…2415b389`). **Plan 10c Task H4 session c, `DayLength` 1, N = 60, with the two players near each other** (a third session the H4 amendments do not list: sessions a and b never brought the players together; ruling H4-1 named one more session as its cost if wrong). In S0, admin's client called `lua.call DebugContextMenu.onTeleportValid nil 10913 10037 0` (the debug menu's own `/teleportto`, sent through `SendCommandToServer` as admin), which put admin 1.58 tiles from bob (`phases.S0.teleports`, `phases.S0.distance_after`); the RCON fallback was not needed. Every verify row ok; `server_error_count` 0; `admin` not parked; free memory fell to 1.09 GB. Phase order S0, I, `burst1`, `b15_1`, `burst2`, `b15_2`, `b15_3`, `burst3`, Z.

How to read it. As `x244a-20261007-174509`'s guide, with both clients now holding the other player in every frame (`summaries.clients.<arm>.<user>.other_present` 1.0). The remote player's position changes in almost every client frame (the move gaps' p50 is one client frame, 17 ms), while the `getLastRemoteUpdate()` stamp still advances only about every 200 or 400 ms, so the stamp is not the movement stream (inference: the stamp is set by `PlayerPacket.processClient`, and the per-frame motion is the client's own interpolation). The move gaps include the pacing's own stops (each walk ends, and the next is queued at least 500 ms later), which are random against the minute frames; the control column is what separates a minute-frame effect from them. The mod's 07:00 day close fell inside `burst3` (interpolated from `phases.S0.time` and `phases.Z.time`, inference): its frame nearest that time read 72 ms busy; the arm's 74 ms frame came about 25 s earlier. `notice.json`'s `deviations` list names the no-zombie fixture and the pacing but omits the S0 teleport, which is recorded in `phases.S0.teleports` (the artifact itself is not edited).

| arm | frames (minute) | busy p50 / p99 / max | minute busy p50 / max | end-to-end period p99 / max | longest window | adds: period p99, longest window | busy a game minute over idle | ghost ms a minute event | starved / minute events | ghost ms a run |
|---|---|---|---|---|---|---|---|---|---|---|
| I | 1019 (162) | 1 / 10 / 16 | 3 / 16 | 108 / 116 | 116 | — | (10.9 absolute) | — | — | — |
| burst1 | 1019 (149) | 1 / 58 / 68 | 49 / 68 | 159 / 169 | 169 | 51, 53 | 44.24 | 46.59 | 0 / 154 | 0.803 |
| b15_1 | 1020 (161) | 12 / 20 / 24 | 16 / 24 | 121 / 126 | 129 | 13, 13 | 48.34 | 50.67 | 0 / 166 | 0.874 |
| burst2 | 1018 (149) | 1 / 58 / 66 | 47 / 66 | 156 / 165 | 164 | 48, 48 | 41.46 | 45.24 | 0 / 154 | 0.780 |
| b15_2 | 1020 (161) | 11 / 21 / 30 | 16 / 30 | 121 / 127 | 127 | 13, 11 | 42.60 | 47.15 | 0 / 166 | 0.813 |
| b15_3 | 1016 (161) | 10 / 20 / 27 | 16 / 27 | 120 / 128 | 128 | 12, 12 | 41.94 | 46.42 | 0 / 165 | 0.800 |
| burst3 | 1019 (151) | 1 / 54 / 74 | 46 / 74 | 154 / 176 | 176 | 46, 60 | 39.09 | 44.22 | 0 / 156 | 0.762 |

| arm | client | frames in span | client frame p50 / p99 / max | stamp gaps n, p50 / p99 / max | stamp gaps >= 100 ms: lined / control | move gaps n, p50 / p99 / max | move gaps >= 100 ms: lined / control | all move gaps lined / control |
|---|---|---|---|---|---|---|---|---|
| I | admin | 6144 | 17 / 20 / 23 | 215, 400 / 817 / 818 | 181 / 180 | 5095, 17 / 135 / 667 | 46 / 41 | 1749 / 1852 |
| I | bob | 6144 | 17 / 19 / 29 | 216, 400 / 801 / 817 | 194 / 183 | 5142, 17 / 149 / 584 | 48 / 45 | 1853 / 1825 |
| burst1 | admin | 6126 | 17 / 19 / 23 | 283, 201 / 816 / 817 | 211 / 231 | 5278, 17 / 51 / 733 | 32 / 31 | 2084 / 2084 |
| burst1 | bob | 6126 | 17 / 19 / 32 | 216, 400 / 801 / 817 | 192 / 180 | 5174, 17 / 66 / 716 | 34 / 36 | 2062 / 1999 |
| b15_1 | admin | 6144 | 17 / 19 / 22 | 256, 399 / 801 / 816 | 214 / 210 | 5364, 17 / 68 / 502 | 35 / 28 | 1944 / 2063 |
| b15_1 | bob | 6144 | 17 / 19 / 27 | 221, 400 / 801 / 817 | 200 / 185 | 5209, 17 / 68 / 567 | 40 / 38 | 1977 / 1917 |
| burst2 | admin | 6120 | 17 / 19 / 22 | 288, 201 / 801 / 816 | 212 / 227 | 5145, 17 / 132 / 634 | 40 / 41 | 2057 / 2016 |
| burst2 | bob | 6120 | 17 / 19 / 20 | 289, 201 / 801 / 817 | 235 / 218 | 5141, 17 / 100 / 850 | 43 / 36 | 2019 / 2026 |
| b15_2 | admin | 6144 | 17 / 20 / 21 | 257, 399 / 801 / 816 | 206 / 210 | 5260, 17 / 66 / 553 | 36 / 31 | 1933 / 1984 |
| b15_2 | bob | 6144 | 17 / 19 / 21 | 284, 201 / 801 / 801 | 244 / 224 | 5225, 17 / 66 / 834 | 37 / 35 | 1976 / 1960 |
| b15_3 | admin | 6109 | 17 / 19 / 21 | 258, 399 / 816 / 817 | 208 / 206 | 5238, 17 / 116 / 518 | 44 / 38 | 1937 / 1999 |
| b15_3 | bob | 6109 | 17 / 19 / 20 | 216, 400 / 816 / 817 | 197 / 184 | 5216, 17 / 50 / 634 | 37 / 37 | 1940 / 1978 |
| burst3 | admin | 6138 | 17 / 19 / 23 | 214, 400 / 816 / 817 | 175 / 182 | 5272, 17 / 50 / 616 | 39 / 30 | 2050 / 2165 |
| burst3 | bob | 6138 | 17 / 18 / 21 | 261, 383 / 801 / 817 | 226 / 205 | 5205, 17 / 83 / 783 | 37 / 37 | 2075 / 2085 |

- **The client rule**: on both clients no `burst` and no `budget15` draw showed lined-up stamp gaps of 100 ms or more at half the minute frames beyond twice the control (lined 175–244 against control 180–231); the move gaps of 100 ms or more lined up 32–43 times under `burst` against 30–41 in the control, and 35–44 under `budget15` against 28–38, with the idle arm at 46–48 against 41–45; no client frame reached 100 ms (max 20–32 ms). Outcome: `not noticeable at this load` on both clients (`summaries.client_rule`). **Resolution of this test:** every stamp gap was at least 167 ms (`summaries.clients.<arm>.<user>.stamp.gaps.min`), so the 100 ms count equals every gap (`stamp.ge_gap` = `stamp.gaps.n`), and the minute windows cover about a third of the time (`minute_window_coverage`), so a gap that long overlaps a window about 70 % of the time in the control too: the stamp comparison could not show a doubling. The reading rests on the move series (which resolves an effect present at about half the minute frames or more) and on the near-player stamp grid: stamps stayed within one or two client frames of the 200 ms grid in every arm (at most 18 ms off on admin and 33 on bob in the burst arms, 34 on bob in any arm), including about 135 to 180 gaps per client in a burst arm that spanned a frame with 30 ms or more of busy. No zombies were present (zombie columns read -1); the other player only.
- **Decision 6, three draws**: `burst` added 46–51 ms at the period p99 and 48–60 ms to the longest window (164–176 ms); `budget15` added 12–13 ms and 11–13 ms (127–129 ms); no ghost starved. Ghost ms a minute event: `burst` 44.22–46.59 (mean 45.35), `budget15` 46.42–50.67 (mean 48.08), a ratio of 1.060; the busy a game minute over idle gives 1.065.
- **The GC log**: 176 pauses, the largest 0.06 ms; inside the arms at most 0.048 ms; 28 allocation stalls, the longest 235.469 ms, at 33.05 to 33.51 s of JVM uptime (`gc.events.25.up_ms` to `gc.events.56.up_ms`), during boot, before any arm.
- **Verdicts**: I, F, C, A6, B15P, B15S, TOT, S, G and Z as predicted; RULE falsified (the prediction was `evidence for (b)`; the reading is `not noticeable at this load`).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters, one host, both clients on the server's host (loopback, no network latency or loss); ghost records are cost, not behaviour; the client reading covers the other player's motion and packet stamps only. |
| `session`, `predictions`, `constants`, `deviations`, `world_changes`, `meta.*_note`, `meta.staging`, `verdicts.*.predicted`, `summaries.decision6.budget15_ruling2.empty_check_clause` | the driver's tables and text | Written before the run; not readings. |
| `summaries.*.n_eq_band`, `summaries.*.ghost_over_fed_calibration`; the `avg` keys; the replies, copies and headers under `phases.<arm>` | — | As in session a (each listed in `do-not-cite.csv`). |
