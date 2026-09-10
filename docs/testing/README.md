# Testing pipeline

Automated integration testing of mods on a **real** dedicated server with
**real** driven clients. Design: [pipeline-design.md](pipeline-design.md)
(layers L0–L4, harness mod + python orchestrator, fragility budget, spikes
S1–S7, roadmap T0–T4). Verified facts and measurements per spike:
[spikes.md](spikes.md).

## `pzt` — the orchestrator (`testing/pzt/`)

Run from the repo root with `python testing/pzt <command>` (or `python -m pzt`
from `testing/`). Requires the local game install (path in `pzt/paths.py`).

| Command | What it does | Cost |
|---|---|---|
| `provision --name default` | Fresh server (fixed sandbox: `Zombies=6` = none, override with `--sandbox K=V`), the `admin` client joins, creates the world and its character, quits cleanly; server stops; snapshot → `testing/fixtures/default/` | ~2.5 min, once per game/mod-set version |
| `boot --fixture default [--hold N]` | Restore the fixture's server world into a fresh run dir and start it | ~14 s |
| `attach --fixture default --server 127.0.0.1:27261 --user admin` | Restore that user's client cache, launch the client, wait until it is in-world (no creation screens), ping it | ~35 s |
| `run --fixture default [--hold N] [--clients a,b]` | boot + attach every fixture client + hold (the test slot) + graceful teardown + `report.json` (timeline, events, collected results); exit code 0 only with zero non-baseline server errors and no client lua errors | ~1 min + hold |
| `spike S3 S4 S5 S6 S7 [--reloadalllua]` | the design spikes as scripted experiments; S3 boots its own sessions, the rest share one; findings → `runs/spike-*/findings.json` | 2–5 min |
| `doctor` | cold-start checks before booting anything: stray PZ `java.exe` (reported, never killed), ports 27261/27262/27015 free, fixture present and build-matched, workshop index reachable, pytest available; exit 1 on a FAIL | seconds |

Measured evidence that a doc cites as an **M** row is copied at slice close to
`testing/artifacts/<run-id>/` (tracked, JSON only, `.gitattributes` keeps the
blobs byte-identical); the full run directories with logs stay local under
`testing/runs/` (gitignored). Experiment scripts live in `testing/experiments/`
(`_common.py` = the shared boot/ask/save/teardown pattern).

Every invocation gets its own `testing/runs/<cmd>-<timestamp>/` with
`server-stdout.log`, `server/` (cachedir), `clients/<user>/` (cachedirs incl.
the game's `console.txt`) and `report.json` (timeline + events). Fixture
blobs (`fixtures/*/cache/`) and runs are gitignored; `fixtures/*/fixture.json`
records how a fixture was built (build, mods, sandbox, accounts, timings).

### How a driven client is controlled

- **Launch**: JVM started directly (no UAC prompt) with
  `-nosteam -cachedir <dir> -nosound -novoip [-debug] +connect ip:port`.
  Never `-safemode` (7× slower world load). The `admin` account (bootstrapped
  by the server's `-adminpassword`) runs with `-debug`, which lets the logo
  screen be skipped; other accounts sit through the ~20 s logo.
- **Join + character creation**: the `PZTestKit` harness mod (must be in
  the server's `Mods=` — the client reloads Lua with the server's list on
  join) reads `<cachedir>/Lua/pzt-join.txt`, presses CONNECT, and NEXTs
  through spawn/profession/appearance. Restored fixture clients skip creation
  entirely (the character persists server-side).
- **Click to Start**: after loading, `GameLoadingState` waits for a mouse
  click; `pzt` posts one to the client's own window (matched by pid, no
  focus change) until the harness reports `player <user> at x,y,z`.
- **Command bus** (both sides, `pzt/bus.py` ↔ `PZTestKit_Core.lua`): `pzt`
  writes `<cachedir>/Lua/pzt-cmd.txt` (`seq`, `cmd`, `args`), the harness
  executes each seq once (last seq recovered from `pzt-ack.txt` after a Lua
  reset) and answers in `pzt-ack.txt` (`ok:`/`err:` + a string or one-line
  JSON). Shared commands: `ping`, `version`, `state`, `result <name>`,
  `time.snapshot`, `trait.check`, `lua.reload <file>`; server: `time.multiplier`,
  `players`, `nutrition.get <user>`, `nutrition.set <user> <field> <v>`,
  `stats.set <user> <stat> <v> …`; client: `quit`, `player.stats`,
  `moddata.set/transmit`, `witness.moddata|nutrition|item`, `item.spawn`,
  `item.tamper`, and the slice-01 experiment commands `nutrition.get`,
  `nutrition.set`, `stats.set`, `item.script <type>`, `item.state <type> <state>`,
  `eat <type> [fraction]` (direct `Eat`, intake arithmetic), `eat.action`
  (queues the real timed action — completes on the server), `sandbox.set`.
  The server owns `Nutrition` and hunger/thirst in MP: client-side writes are
  overwritten within ~1 s (see `docs/vanilla/eating-pipeline.md`).
  Slice-02 lifecycle commands — server: `item.get <user> <type>`,
  `item.set <user> <type> <field> <v>` (+`sendItemStats`),
  `item.age.tick <user> <type>` (`updateAge(true)`),
  `item.freeze <user> <type>`, `item.update <user> <type>` (the cooking
  driver), `perk.set <user> <perk> <level>` (the authoritative one — a
  client-only perk write is overwritten by the server's copy within a
  second); client: `item.age <type> <days>`, `perk.set <perk> <level>`,
  `recipe.evolved <recipe> <base> <ingredient>…`. The server also owns item
  **aging**: `age` was **measured** not to reach the client — not on
  `sendItemStats`, not on `updateAge(true)`, not over an accelerated game day
  (`testing/artifacts/exp02-20260910-030433/`) — while
  `offAge`/`offAgeMax`/`freezingTime` being absent from `ItemStatsPacket` is
  so far only **read off the packet code** (no run has made them differ
  between the two sides). Either way those readings are taken on the server
  bus (see `docs/superpowers/plans/02-notes.md` Q8).
- **Results**: `TK.result(name, table)` writes `<cachedir>/Lua/pzt-results/
  <name>.json` as one complete JSON object (that is the ready signal — the
  writer's extension allowlist rules out `.ready` markers); `pzt` collects
  them into `report.json` and `bus.wait_result()` blocks on one.
- **Observation**: the client's `console.txt` is tailed for
  `STATE: enter …` transitions and `PZTK:` harness lines.

### Harness layout (`testing/PZTestKit/PZTestKit/`)

`mod.info` + `42/mod.info` (B42 reads the one inside the version folder),
`42/media/lua/shared/PZTestKit_Core.lua` (global `TK`: KV files, JSON, command
bus, results, shared commands), `server/PZTestKit_Server.lua` (bus polling on
`OnTick`, `OnClientCommand` witness replies), `client/PZTestKit_Client.lua`
(auto-join, client commands, `OnServerCommand` witness comparison).

### Server side

`pzt/server.py` seeds `Server/<name>.ini` (ports, RCON, `Mods=`, `Open=true`,
`UPnP=false`), installs mods into the cachedir's `mods/` (harness mods from the
repo, anything else copied from the Steam workshop folder by `pzt/mods.py` —
under `-nosteam` the game searches nothing else), starts
`zombie.network.GameServer -nosteam -adminpassword …`, waits for
`*** SERVER STARTED ****`, classifies error-shaped log lines against the
vanilla-noise baseline (stack frames attach to their head line), and stops
with `quit` on stdin (RCON `quit` as fallback).
