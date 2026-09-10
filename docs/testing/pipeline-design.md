# Integration testing pipeline — design

**Goal:** a command (`pzt run`) that installs a mod build into a real PZ
dedicated server + real game clients on this machine, drives scripted
scenarios, and produces a pass/fail report with sync-correctness assertions —
confidently enough that "it passed" means "it works on the server."

**Posture (brainstorm 2026-09-13):** aim for true e2e with driven clients;
engineer fragility down layer by layer; runs locally now with server-only
layers portable to Linux CI; tests authored in lua (harness mod) and
orchestrated in python.

## Confirmed facts the design stands on

| Fact | Source |
|---|---|
| Client auto-connects with `+connect ip:port` / `+password` (or `-Dargs.server.connect/.password`) — no server-browser UI needed | wiki Startup parameters (42.20.4); literal in `MainScreenState`, `LuaManager$GlobalObject` |
| Lua can join directly: `serverConnect(...)` exposed on the lua global object; `canConnect()`, `forceDisconnect()` also exposed | jar `LuaManager$GlobalObject` methods |
| Multiple client instances: `-cachedir` per instance + `-nosteam`; `-nosound -novoip`; `-debug`, `-debuglog=All`, `-modfolders`. **Not `-safemode`**: it stalls model loading and turns a 17 s world load into ~120 s (spike S2) | wiki Startup parameters; S2 |
| Dedicated server: `ProjectZomboidServer.bat` (java `zombie.network.GameServer`); args `-servername -adminpassword -adminusername -port -ip -cachedir -nosteam -debuglog -statistic` | install dir + wiki |
| Server RCON exists (`zombie/network/RCONServer`, `RCONPort`/`RCONPassword` in ServerOptions) | jar |
| Admin commands are classes: additem, teleportto, setaccesslevel, servermsg, godmode, **reloadlua/reloadalllua** (hot reload) | jar `zombie/commands/serverCommands/*` |
| `GameTime.setMultiplier(F)` exists → accelerated simulation; nutrition ticks scale with game-world seconds | jar `zombie/GameTime`; Nutrition.updateWeight |
| Structured output from lua: `getFileWriter` (ini/cfg/txt/log/json) and unlimited `getModFileWriter`; spool+`.ready`-marker handoff pattern already proven server-side by DataLogger (on the approved list) | wiki; DataLogger.lua:409-419 |
| MP character creation is lua UI (`CoopCharacterCreation*.lua`); characters persist per account server-side | lua client/OptionScreens |
| Server world lives in `Zomboid/Server/<name>.ini`, `Zomboid/db/<name>.db`, `Zomboid/Saves/Multiplayer/<name>/`; client caches per `-cachedir` | local dirs |
| `loadstring` is gone — no runtime code shipping; tests must be files in the harness mod | wiki 42.20.x news |

## Layers

```
L0  static      luacheck/LuaLS (Umbrella stubs), script-DSL parse, mod.info/layout lint   seconds, CI
L1  boot        dedicated server boots with mod → clean console.txt (no lua errors,
                no checksum/definition mismatch), clean shutdown                            ~1 min, CI
L2  server sim  harness-server lua scenarios: spawn/mutate world & items, run
                accelerated time, assert via JSON spool                                     minutes, CI
L3  e2e         1–2 real clients auto-join; harness-client executes scripted
                player actions; server asserts authoritative state                          minutes, local
L4  sync        "sync witness": client reports its view of an object, server
                diffs against authority (fields, modData) → the ItemQuality class
                of bug becomes a failing test                                                rides on L3
```

Every layer's failure is a hard fail of the run; `pzt run --upto L2` for fast
loops, full stack on demand / nightly.

## Components

### PZTestKit — the harness mod (lua)

Ships only in test profiles (never in the released mod). Depends on the mod
under test via `mod.info require=`.

- **shared/**: test registry `TK.test(name, {tags, timeoutMin, fn})`,
  assertion lib (`TK.eq`, `TK.near`, `TK.within`, `TK.eventually(pred,
  gameMinutes)`), step scheduler driven by `EveryOneMinute`/`OnTick` with
  budgets, and the **result writer** — JSON per test to
  `<cachedir>/Lua/PZTestKit/results/<run-id>/<test>.json` then a `.ready`
  marker (DataLogger's atomic handoff).
- **server/**: `OnServerStarted` → load run manifest (written by orchestrator
  into a `.json` the mod reads via `getFileReader`), execute L2 scenarios,
  serve **witness requests** (`OnClientCommand PZTestKit witness`) by
  returning authoritative snapshots, host world-mutation helpers (spawn
  items/zombies/containers at coords, set time, `GameTime:setMultiplier`).
- **client/**: on `OnGameStart` → identify itself (client N from manifest),
  wait for spawn, run L3 steps: equip/eat/craft/move via the same lua
  actions the UI uses (ISTimedActionQueue), then send `witness` snapshots
  and step results to the server via `sendClientCommand`. Join automation:
  `+connect` handles connection; harness completes account/character
  screens via the lua handlers **or** (preferred) reuses pre-created
  characters so those screens never appear.

### `pzt` — the orchestrator (python, stdlib + one RCON client)

- **Profile builder**: from `pzt.toml` — server name, ports, mods list
  (`Mods=`/`WorkshopItems=` in the ini), sandbox vars (fixed seed, fast
  spoilage etc.), client count, layer ceiling. Writes ini + SandboxVars.lua.
- **Fixture manager**: **golden world** snapshot (server dirs + db + client
  cachedirs with pre-created test accounts/characters). Restore before each
  run → deterministic start, no character-creation UI at all.
- **Process manager**: launch server (`java ... zombie.network.GameServer
  -nosteam -servername pzt -adminpassword ... -cachedir ...`), wait for
  "server started" in console, launch clients with `-nosteam -cachedir
  <c1> -nosound -novoip -debug +connect 127.0.0.1:<port> +password <pw>`
  (JVM started directly, no launcher exe → no UAC prompt); kill trees on
  timeout.
- **Log watcher**: tails server/client console.txt for lua error signatures,
  definition-integrity warnings (the KBW MP checksum class), and harness
  markers; every error is attached to the failing test.
- **RCON driver**: admin commands mid-run (`additem`, `teleportto`,
  `setaccesslevel`, `reloadlua` for iterate-without-reboot, `save`, `quit`).
- **Collector/reporter**: gathers result JSON from every cachedir, builds
  JUnit XML + markdown summary; exit code = pass/fail.

### Sync witness (L4) — the assertion that would have caught ItemQuality

`witness.*` commands on a client send its local view over
`sendClientCommand`; the server's `OnClientCommand` handler replies with its
authoritative view over `sendServerCommand`; the client compares and writes a
`witness_*` result (implemented in S6). There is **no client→server item
field sync API** (`sendItemStats` is `GameServer.sendItemStats`, server →
owning client), so a client-side edit of an inventory item's fields or
modData is invisible to the server until something server-side replaces the
item — the witness is exactly what surfaces that. Player modData needs
`transmitModData()`. Witness kinds so far: player modData, nutrition values,
one inventory item (condition, conditionMax, modData); the client commands are
`witness.sync.moddata` (renamed from `witness.moddata` in slice 08, when the
shared reflective command took that name — the `kind` on the wire and the
`witness_moddata_<key>.json` result are unchanged), `witness.nutrition` and
`witness.item`.

**Slice 08 added a second, *reflective* witness at L4 — one that needs no
per-mod command and no round trip**: `witness.fields` / `witness.moddata`, in
`shared/PZTestKit_Core.lua`, read any zero-argument getter or modData key — a
whole-table census included — on **either** side. So a teardown asks the two
sides the same question and compares two independent replies, instead of
shipping a new Lua comparator per mod; a `missing` name means the build does not
expose the member, which a comparator would have died on. Both commands answered
live on both sides on 42.20.4
(`testing/artifacts/exp08-20260910-152944/witness-probe.json`, n = 1); the
shapes, the `<id>` grammar and the reading rules are in
[README.md](README.md) § Command bus.

## Fragility budget — where it bites and what we do

| Risk | Mitigation |
|---|---|
| Client windows on a desktop (no true headless) | `-nosound -novoip`, small window (normal rendering — `-safemode` is ~7× slower to load); Windows session must stay unlocked; CI runs L0–L2 only |
| First-join UI screens (account, character) | Golden fixture with pre-created accounts/characters — screens never render; lua fallback for the rare reset |
| Timing/races (spawn not ready, chunk not loaded) | Every step is `eventually(pred, budget)`; no sleeps; world-ready barrier = harness handshake, not a timer |
| Game/mod updates changing behavior | Run pins game build; harness self-reports versions; a `smoke` suite runs after every Steam update |
| Port/cachedir collisions between runs | Unique run-id per run; distinct ports; teardown verifies process exit |
| `-nosteam` ignores the workshop folder | The **profile builder** copies every mod a `testing/profiles/<name>.toml` names into the run cache's `mods/`, on both sides, from one source map ([profiles.md](profiles.md)). There is no alternative: S3 proved both workshop roots are gated on Steam mode, there is **no** server `-modfolders`, and `WorkshopItems=` needs Steam and is written empty |
| Time acceleration side effects in MP | Only in L2/L3 with explicit multiplier; nutrition tests assert against game-seconds, not wall-clock |

## Spikes (each is a one-session verification, in order)

- **S1 Boot loop** ✅ — done 2026-09-09, see [spikes.md](spikes.md): cold
  start 57 s to `*** SERVER STARTED ****`, RCON honored from a pre-seeded ini,
  `quit` on stdin exits 0 in 8 s, 15 MB fixture footprint, vanilla noise
  baseline captured in `pzt/server.py`.
- **S2 Auto-join** ✅ — done 2026-09-09, see [spikes.md](spikes.md): fully
  automated join (harness mod fills the connect popup and drives the three
  character-creation screens), characters persist across joins, admin
  `-debug` client skips the logo; **in-world ≈ 30 s** from launch once
  `-safemode` was dropped (it alone cost ~100 s of world load).
- **S3 Mods under -nosteam** ✅ 2026-09-09: both workshop roots are gated on
  Steam mode, so only `<cachedir>/mods` is searched — copy strategy
  (`pzt/mods.py`). A mod the game cannot find is a **WARN** and the session
  runs without it; `pzt run` now fails on `required mod "X" not found`.
- **S4 Result channel** ✅ 2026-09-09: `getFileWriter` accepts subfolders of
  `<cachedir>/Lua` and `.json`; a complete JSON object is the ready signal
  (`.ready` is not an allowed extension; `getModFileWriter` writes into the
  mod folder instead). Client 0.3 s, server 1.5 s.
- **S5 Time acceleration** ✅ 2026-09-09: RCON `settimespeed <x>` sets the
  server multiplier and broadcasts `SetMultiplierPacket`; at 30× both sides
  ran ~32× and calorie burn scaled with it. Always restore through the same
  command (a server-only reset leaves clients accelerated and drifting).
- **S6 Witness round-trip** ✅ 2026-09-09: the witness catches client-side
  player modData (fixed by `transmitModData()`), client-side item field/
  modData edits (never reach the server — no client→server API) and
  client-created items (absent server-side, still after 60 s); nutrition is
  computed on the **server** and mirrored to the client at 1 Hz (direction
  corrected in slice 01 — run `exp01-20260910-000351`, see
  [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md) § MP behaviour).
- **S7 reloadlua iteration** ✅ 2026-09-09: server `reloadlua <file>` (RCON)
  re-runs one file with globals intact; clients reload their own copy via
  `reloadLuaFile(<absolute path>)` (bare names do nothing); `reloadalllua`
  throws ~31 Lua errors on a dedicated server — not usable.

## Roadmap

- **T0** ✅ 2026-09-09 (measurements in [spikes.md](spikes.md)): `testing/pzt/`
  package with `provision` (golden fixture: server world + client cachedirs,
  gitignored blobs + tracked `fixture.json`), `boot` (13 s), `attach` (player
  ready 34 s, no creation screens), `run` (boot + attach + hold + teardown +
  report); harness command bus (`ping`, `quit`). `testing/profiles/` comes
  with T1.
- **T1** ✅ 2026-09-10 — L0+L1: lint + boot validation against the *current*
  modlist, on other people's mods before ours exists. Shipped: `tools/mod_lint.py`
  (nine static layout rules; the 230-folder installed corpus scores **84
  findings — 3 ERROR, 30 WARN, 51 INFO at 2026-09-10 13:47** in ~13 s, exit 1 —
  a live tree, so quote a sweep with its date and see
  [profiles.md](profiles.md) § L0 for what moved) and the **profile
  builder** — `testing/profiles/<name>.toml` + `pzt run --profile` /
  `pzt scenario --profile`, which overlay a named mod set and `[sandbox]`
  overrides onto a restored fixture, fail fast when a mod did not load, and prove
  the mod took *effect* with `[[verify]]` bus probes. Schema, the `-nosteam` copy
  rule, the missing-mod path and the sweep: [profiles.md](profiles.md) — which
  supersedes the `pzt.toml` / `WorkshopItems=` sketch under *Components* above
  (the file is per-combination TOML under `testing/profiles/`, and
  `WorkshopItems=` needs Steam, so it is written empty). **Three live runs**:
  `run-20260910-133657` (`--profile mod-under-test --hold 5`) **PASS**, 93 s —
  both `trait.check` probes `ok=true` on the server *and* the client, and
  `[sandbox] DayLength = 1` survived the server's boot-time rewrite beside the
  fixture's own `Zombies = 6` at 189/184 keys, one line of `diff`;
  `run-20260910-133916` (`--profile missing-mod`) **FAIL**, 23 s, exit 1, **no
  client ever launched**; `scenario-20260910-134012` (`smoke_clock --profile
  mod-under-test --speed 30`) **PASS**, 63 s, artifact `profile` field set — and
  `cadence_suspect` at 0.22 ticks per game-minute, the finding that
  `DayLength = 1` × `--speed 30` overruns the game-minute scheduler (keep
  `24 × speed / day_minutes ≲ 8`). Boot cost: 36.6 s on the session's first boot,
  13.7 s / 14.0 s on the two after it. The **gap is measured; its cause is not** —
  the first boot of the session is the suspected reason, and no spike measured it.
  T0's own warm figure for a restored fixture is 13.4 s, which the two later boots
  reproduce; S1's 57.2 s is a first-*ever* cold start that includes world and db
  creation, so neither number is a profile cost.
- **T2** ✅ 2026-09-10 — L2: server scenarios + result channel + RCON. Shipped:
  the harness **test layer** (`shared/PZTestKit_Test.lua` — `TK.test`, a
  game-minute scheduler on `EveryOneMinute`, `test.list` / `test.run` /
  `test.status` on the bus), scenarios under `server/scenarios/`, and
  `pzt scenario <name> [--side server|client] [--speed N]` with Python
  evaluators. API and runner: [README.md](README.md) § Scenarios and the test
  layer — it supersedes the `TK.test(name, {tags, timeoutMin, fn})` sketch under
  *Components* above (and the `.ready` marker there, which S4 ruled out).
  **Three live runs**, ~10 min wall each (593 s from server launch to the result
  doc, 603 s including teardown — both runner-clock marks from the gitignored run
  reports; the committed artifacts carry the test window alone,
  `cadence.wall_s` 540.4–540.6 s), 73 hourly samples over 72.0 game-hours,
  `EveryOneMinute` at 1.000 ticks per game-minute, 0 server errors:
  `scenario-20260910-054012` (gain) **+2.526 kg measured vs +2.551 predicted**,
  tolerance 0.383 — **PASS**; `scenario-20260910-055029` (fast) **−1.426 vs
  −1.412**, tolerance 0.212 — **PASS**; `scenario-20260910-052624`, the first,
  unwatered attempt — **FAIL**, subject dead of thirst at game-hour 35
  (`setCalories` is not food). Full numbers and findings:
  [../vanilla/nutrition-core.md](../vanilla/nutrition-core.md) § Verified on
  server. **The prior this roadmap carried — "3 game-days at 4000 cal gains
  ≥3 kg" — does not survive the clamps**: `setCalories` tops out at 3 700, which
  swallowed 4 790 of the 12 000 kcal fed, so the model predicts **+2.55 kg** over
  three game-days and the server measured **+2.53**.
- **T3** L3/L4: one driven client, witness suite, relog round-trip.
- **T4** two clients (multi-player interactions), nightly full run, CI job for
  L0–L2 on a Linux dedicated server image.

## Prior art to lean on

DataLogger (approved list) — spool/ready handoff, admin `OnClientCommand`
plumbing; wiki *Testing mods in multiplayer* (manual two-instance procedure
we're automating; page is B41-era); wiki *Startup parameters* (mirrored:
[startup-parameters](../../references/wiki-mirrors/startup-parameters.md));
"PZ AI agent" / "Pythoid" in wiki Modding projects — check for driven-client
prior art (spike S2 adjunct).
