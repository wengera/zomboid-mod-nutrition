# `x171c-20261006-091054` reading guide

**`x171c-20261006-091054/checksum.json`** and its nine log files — produced by `testing/experiments/x171_checksum.py` on HEAD `598f619` (probes `8ca63d0`, clean) with the driver itself untracked at the run; committed unedited beside the artifact
(579.3 s wall; `checksum.json` 47405 bytes, sha256 `9167edcb…bdf76809`, byte-for-byte identical to the run copy; each log file byte-identical to `testing/runs/x171c-20261006-091054/<boot>/server/Logs/` or `<boot>/clients/admin/Logs/`, renamed only by the `server-`/`client-` prefix). **Plan 6 Task 8, X16**: three boots of the default fixture, build 42.20.4, `DoLuaChecksum` true and `AntiCheatChecksum` 2 in the server ini; the server holds `TKX_ChecksumA` in every boot and the client's copy is passed per side. `kick` and `cr` demote the account to the `user` role by RCON `setaccesslevel` before the client starts (the whitelist row reads role 2) and run the client without `-debug`; `bypass` keeps the fixture's `admin` role (role 7) — the three-boot shape is an implementer addition, because the jar's `admin` role holds `BypassLuaChecksum`. `doctor_clean` true before each boot; `server_error_count` 0 in each. `pzt run` was not run: a profile cannot give the client its own source.

How to read it. `phases.<boot>` holds `files` (both installed copies with size, CR count, sha256 and the CR-stripped MD5), `setaccesslevel`, `server_log` and `client_log` (the server stdout and the client `console.txt`, each line stamped with the driver's wall clock), `reads` (`lua.global TK.version` at ready and at the window's end), `client_seen` and `client_events`, and `db` (the server's `userlog` table and the account's whitelist row, read after the stop). The kick's reason string and the server's disconnect are not in the JSON: they are in `kick/client-2026-10-06_09-11_connections.txt` (lines 11–13) and `kick/server-2026-10-06_09-10_user.txt` (lines 5–7).

- **kick**: server warning and anti-cheat line at driver wall 39.756 (`action="Kick"`); client force-disconnect 09:11:34.358 with `checksum-File doesn't match the one on the server:` naming `media/scripts/tkx_checksum.txt`, 0.290 s after the anti-cheat line; no timeout line in the 157.806 s watched after it; one `LuaChecksum` userlog row; the client never reached `in_game`.
- **cr**: the CRLF copy's CR-stripped MD5 equals the server copy's; connected, `TK.version` 1 at walls 320.015 and 410.452; no checksum-mismatch line (no `will be kicked ... checksums do not match` warning, no `Anti-cheat="ChecksumUpdate"` line, no getReason string; the `Checksum: Warning`, `scriptChecksum:`, `luaChecksum:` and `DoLuaChecksum` lines are present as in every boot); userlog empty.
- **bypass**: connected under `admin`, `TK.version` 1 at walls 478.877 and 569.313; no checksum-mismatch line (no `will be kicked ... checksums do not match` warning, no `Anti-cheat="ChecksumUpdate"` line, no getReason string; the `Checksum: Warning`, `scriptChecksum:`, `luaChecksum:` and `DoLuaChecksum` lines are present as in every boot); userlog empty.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot per arm, one probe file, one fixture. |
| `predictions`, `reasons_jar` | the driver's strings | Written before the run; the kick-timing prediction is falsified. |
| `phases.*.reason_hits`, `summary.*.reasons_client` | 0 everywhere | The driver searched `console.txt` and the server stdout; the reason is written only to the client's `Logs/` connections file. |
| `phases.kick.client_alive_at_end` | true | The process stayed alive in its loading state after the force-disconnect; it is not a connection. |
