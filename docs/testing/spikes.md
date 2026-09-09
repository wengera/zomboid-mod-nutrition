# Spike log

## S1 — Boot loop ✅ 2026-09-09 (game 42.20.4 `b0bbce05d5`)

Script: `testing/pzt/boot.py` (first real `pzt` module). Run:
`s1-20260909-122037`, isolated `-cachedir`, ports 27261/27262, RCON 27015,
no mods, vanilla world generated from scratch.

| Measure | Result |
|---|---|
| Cold start → `*** SERVER STARTED ****` (Network log) | **57.2 s** (1,856 log lines; includes first-run world/db creation) |
| RCON | `RCON: listening on port 27015` — pre-seeded `RCONPort`/`RCONPassword` in `Server/<name>.ini` are honored and preserved when the server rewrites the ini with defaults; Source-RCON auth + `servermsg` accepted (empty reply body) |
| Shutdown via `quit` on stdin | graceful: "Saving finish" → ObjectID persistence → UdpEngine termination → "Shutdown handling finished"; exit code 0, **8 s** |
| Error-shaped lines on a clean vanilla boot | 57, three signatures, all baseline noise (allowlisted): WorldGen `IsoPropertyType.lookupOrDefaultStr` exceptions ×5, `FluidContainerScript` name sanitizing ×2, `BrokenFences` missing ThumpSound ×50 |
| Cache footprint after one boot | **15 MB** — `Server/{pzt.ini, pzt_SandboxVars.lua, pzt_spawnpoints.lua, pzt_spawnregions.lua}`, `db/pzt.db`, `Saves/Multiplayer/pzt/`, `server-console.txt` |

Facts that change the design:
- The server's own log file in the cachedir is **`server-console.txt`** (not `console.txt`).
- `-adminpassword` bootstraps the `admin` account non-interactively ("Administrator account 'admin' created" / "password changed via -adminpassword option").
- UPnP router detection runs unless `UPnP=false` is seeded (it did not hang this time; seeded off for all future runs).
- `-nosteam` works cleanly (`ZNetNoSteam64`, "SteamUtils started without Steam").
- A whole server fixture is ~15 MB → golden-world snapshot/restore per run is trivially cheap.

**Repeat run** `s1-20260909-122330` (hardened script, fresh cachedir):
started in **13.6 s**, RCON ok, clean exit in 8 s — PASS. Breakdown of the
speedup vs run 1: `UPnP=false` removed a 12 s router-detection wait
(run 1 log: 171,468 → 183,477 ms), the rest is OS/JIT cache warmth. So the
realistic per-run boot cost for L1/L2 is **~15 s**, not a minute. Four more
vanilla noise signatures surfaced once the big three were filtered (WorldGen
exception detail lines for ladder/WindowShape properties, Piano recipe icon,
a Muldraugh mannequin zone, a duplicate basement RoomDef) — allowlisted; a
clean vanilla boot now scores **0 errors**, so any nonzero count is a real
finding.

Open follow-ups: warm-start with a *reused* world dir (golden-fixture path);
RCON `quit` as alternative shutdown (`servermsg` succeeded; `quit` untested).

## S2 — Auto-join (next)
## S3 — Mods under -nosteam
## S4 — Result channel
## S5 — Time acceleration in MP
## S6 — Witness round-trip
## S7 — reloadlua iteration
