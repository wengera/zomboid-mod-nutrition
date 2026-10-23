# `x131p-20261004-192310` reading guide

**`x131p-20261004-192310/persist.json`** — produced by `testing/experiments/x131_persist.py` at commit
`8211b15` with the harness Lua clean (`harness_lua_dirty` false) and `doctor_clean` true. Plan 1 Task 13:
**X28**, **X49a** and **X49b** in one live session of five server boots, profile `x13-persist`
(PZTestKit only, the fixture's own sandbox: DayLength 4, one game-minute 3.75 s wall). Every boot's
`[[verify]]` row passed, no mod was missing, `server_error_count` 0 and `client_lua_error` false on all
five; the clean quits returned rc 0, boot 3's kill rc 1. sha256 `6c775023…801b30a7` (198 727 bytes),
byte-for-byte identical to its run copy. **Skew-free**: the driver was written before the run and not
edited after it.

How to read it. `boots.<label>` is one server process: `1` (a fresh restore into `<run>/server`), `2`, `3`
and `3r` (reuse boots of the same `<run>/server`), `4` (a fresh restore into `<run>/boot4/server`, the
control); every boot's client is a fresh fixture restore. `boots.<label>.witness.<tag>` holds one
client-first pair of `witness.moddata` reads: `player` (the census of admin's modData and the keys
`TKX_persist`, server-written; `TKX_persist_c`, client-written and transmitted; `TKX_quit`) and
`global:<table>` (the key `k`). A global table is read on the server only once the run has written it in
that world. `mtime_series` is the sampler's every-5 s `stat` of the current server's
`global_mod_data.bin` (294 rows, tagged by boot and phase); `file_changes` keeps each change with the
whole file as hex; `save_log_lines` stamps each `Saving GlobalModData` line with the wall time the sampler
first saw it. `verdicts.<phase>.observed` is the graded reading.

- **X49a**: `ini.SaveWorldEveryMinutes` `0`. Arm (a), no write, `boots.1.windows.a`: 375 s wall, 99.99
  game-minutes, no change and no log line. Arm (b), the X28 writes and `globalmoddata.transmit
  TKX_persist`, `boots.1.windows.b`: 100.24 game-minutes, no change and no log line. Arm (c), RCON `save`
  (`World saved`) at wall 823.4: the file went 39 → 73 bytes at 824.5 with one log line. Every clean quit
  (boots 1, 2, 3r, 4) moved the file once with one log line; no boot start moved it.
- **X28**: boot 2's server read `TKX_persist` `1`, `TKX_persist_c` `1` and `global:TKX_persist k` `1`;
  boot 3 read them again; boot 4 missed all three on both sides. The client's copy at boot 2 held both
  player keys, while in boot 1 it never held the server-written one; the client never held the global
  table (no handler installs it).
- **Quit-only arm** (`verdicts.quit-only`): `TKX_quit` written on the server in both scopes in boot 2 with
  no save and no transmit, then a clean quit; boot 3 read both.
- **X49b**: `globalmoddata.set TKX_restart k 2` + transmit at wall 1018.5 (world age 6.3032 h), read back
  on the server; the server killed at 1024.6 (6.3210 h, 1.07 game-minutes, 6.09 s wall later) with no
  file change and no log line between. Boot 3r read `TKX_restart k` absent on both sides; boot 4 missed it.
  Boot 3r's first read sat at world age 6.2836 h against boot 3's 6.2767 h: the kill lost the world's
  progress back to boot 2's quit.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one player, one build, the world autosave off. |
| `db_scans` | every `has` false | The scan read `db/pzt.db`, the server's account database; the player store is `Saves/Multiplayer/pzt/players.db`, which this run never scanned. Read `verdicts.X28-player.observed`. |
| `file_changes[4].has.TKX_restart` | `true` | Boot 3r's server read of `global:TKX_restart` created the empty table through `getOrCreate`, and the quit saved it: a table name, not the value. Read `verdicts.X49b.observed`. |
| `file_changes[6].has` | all three `true` | Boot 4's control reads created the three empty tables, which its quit saved: the control file's names are the witness's own. |
