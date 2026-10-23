# `x223b-20261007-085832` reading guide

**`x223b-20261007-085832/luasum.json`** and its three log files — produced by the same driver, `--boot b`, unedited since its commit at `c494d70`, on HEAD `3f58043` (an unrelated `mod/`-and-kernel commit landed between the boots; harness Python `aaa51f4`; harness Lua `fadf698`, clean; `mod/` not booted)
(215.4 s wall; `luasum.json` 31592 bytes, sha256 `0c46ea9b…8a67940b5`, byte-for-byte identical to the run copy; each log file byte-identical to its `Logs/` original, renamed only by the prefix). **Plan 10 Task S6, boot b**: the session of `x223a` with `bob`'s `NR_Core.lua` rewritten with CRLF line endings; the same ini, roles, `doctor_clean`, lint, verify, error and mod-error readings as `x223a`.

How to read it. As `x223a`. `phases.boot.deployed_NR_Core`: the server's and `admin`'s copies the frozen 3272 bytes with 0 CRs; `bob`'s 3333 bytes with 61 CRs, sha256 `7270f640…af0b13693`, and its CR-dropped MD5 `1283f1708c35f2e5ec01349c3414a594`, equal to the frozen file's; `meta.tree_diff` one differing file of 65.

- `bob` reached ready 44.7 s after its launch (`client_seen`), answered `lua.global NutritionRevamp.version` `"1.0.0"` at wall 108.111 and again at 201.125, 93.014 s later (`reads`), and the server's `players` read `["admin", "bob"]` at both (`players_at_bob_ready`, `players_at_end`).
- The server's user log: `"bob" fully connected (10911,10037,0)` at 09:00:19.186, and its connection index 1 (`bob`) next disconnected at the teardown, 09:01:58.357; `bob`'s connection log runs `login-queue-done` 09:00:18.063 and `player-connect` 09:00:19.145, its only `force-disconnect` the teardown's `exit` at 09:01:58.343.
- No `will be kicked`, no `Anti-cheat` line and no `Timed out connection because checksum` line in the server log; `db.userlog` empty; `bob`'s console carries `client: DoLuaChecksum start` and `client: DoLuaChecksum end`, as `admin`'s does.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one changed file, one host. |
| `predictions`, `constants`, `deviations`, `meta.edit`, `meta.changed_file`, `meta.harness_commit`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `verdicts.b.verdict` | `falsified` | A defect of the driver's grade, not a reading: its mismatch pattern matched `luaChecksum: 6191c643…` on the server and `client: DoLuaChecksum start/end` on `bob`, which are not mismatch lines; with those excluded the observations are the prediction's. Cite `reads`, the user log and `logs.server_mismatch.hits`. |
| `verdicts.b.observed.server_mismatch_lines`, `verdicts.b.observed.bob_mismatch_lines`, `verdicts.b.observed.admin_mismatch_lines` | 1, 2, 2 | Counts of the pattern's matches named above, not of mismatches. |
| `verdicts.b.observed.bob_disconnect_evidence` | `true` | Matched `SafetyDisconnectDelay` and `BanKickGlobalSound` settings-table lines; `bob` was not disconnected before teardown. |
| `live.bob.hits` | the settings-table lines | A wide pattern's matches; not checksum lines. |
