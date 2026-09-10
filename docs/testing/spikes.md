# Spike log

## S1 — Boot loop ✅ 2026-09-09 (game 42.20.4 `b0bbce05d5`)

Script: `testing/pzt/boot.py` (spike script, since folded into `pzt/server.py`). Run:
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

Follow-ups, both closed: warm start from a *restored* fixture world takes
**13.4 s** (`run-20260909-140444`, see T0 below) — no slower than a fresh
world; loading its `map_meta.bin` echoes the vanilla duplicate-room defect as
four `IsoMetaGrid.load > invalid room metaID` lines (baselined). RCON `quit`
as alternative shutdown: verified (clean exit 0) — the orchestrator can stop a
server it does not own the stdin of.

## S2 — Auto-join (in progress, 2026-09-09)

Driver: `testing/pzt/join.py` (spike script, since folded into
`pzt/client.py`; launches a real client into an isolated
cachedir with `-nosteam -nosound -novoip [-debug] +connect ip:port`,
tails its `console.txt`, kills after an observation window). Harness mod:
`testing/PZTestKit/PZTestKitClient/` (auto-fills the join popup, auto-creates
a character, logs `PZTK:` lines).

Facts established so far:

| Fact | Detail |
|---|---|
| `+connect` skips the server browser entirely | Client lands straight on **ServerConnectPopup** ("You are about to connect to: ip : port") with Server Password / Account Username / Account Password fields |
| No username launch arg exists | Only `args.server.connect` / `args.server.password` in the jar; account credentials must come from lua (or a saved-server row) |
| The Connect button's exact call | `ConnectToServer.instance:connect(popup, "", user, pass, ip, "", port, serverPassword, useSteamRelay=false, doHash=true, authType=1)` → java `serverConnect(...)` (ServerConnectPopup.lua:203) |
| First-launch T&C screen | Persisted as `termsOfServiceVersion=1` in `<cachedir>/options.ini`; seeding that line before launch is honored (flag survived the game rewriting options.ini) |
| Client state markers | `console.txt` logs `STATE: enter/exit zombie.gameStates.<X>` (TermsOfServiceState, MainScreenState, ConnectToServerState, GameLoadingState, IngameState) — used as the driver's timeline |
| Enabled-mods file | `<cachedir>/mods/default.txt`, ScriptParser block format: `mods { mod = <ModID>, }` (`ActiveModsFile.fromString`) |
| **First-launch mods reset** | `ZomboidFileSystem.resetDefaultModsForNewRelease`: if `mods/reset-mods-42_00.txt` is missing, the game writes it and **wipes default.txt** — this silently disabled the harness on the first automated attempt. Fix: seed the marker (fixed sentence content) alongside the list |
| Saved servers/accounts | `<cachedir>/db/ServerList.db` (SQLite): `server(name, ip, port, serverPassword…)` + `account(serverId, username, password, isSavePassword, authType…)`; `ServerConnectPopup:setServer` prefills the form from a matching row — a zero-lua fallback for credentials |
| Character creation | MP flow is lua (`CoopCharacterCreation`, `CoopMapSpawnSelect`): pick region via `listbox.selected` + `clickNext()`, then `CoopCharacterCreation:accept()` |
| **B42 mod discovery reads `mod.info` from inside the version folder** | `ZomboidFileSystem.getModVersionDirName` picks the best `42[.x]/` dir for the running build, then `getModInfoForDir` parses `<mod>/<verdir>/mod.info`. ItemQuality ships ONLY `42/mod.info`; a mod with only a root `mod.info` + bare `42/` is silently ignored (no log line). Attempt #3 failed on exactly this. |
| Auto-connect never presses Connect | `MainScreen.lua:1802`: `getServerAddressFromArgs()` → `bootstrapConnectPopup:connect(ip, port, getServerPasswordFromArgs())` → `ServerConnectPopup:setServer` (prefills from saved-server DB). The click itself must come from the harness. |
| UAC prompt on client launch | Comes from `ProjectZomboid64.exe`; `--launcher java` (the default) starts `jre64\bin\java.exe` directly with the launcher's JSON config instead (as the server does) |
| `-debug` clients are refused for non-admin accounts | `UI_OnConnectFailed_DebugNotAllowed` ("Debug connection is not allowed for non admin."). Join without `-debug` (driver default) or use an admin test account |
| **MP character creation flow (not the Coop* screens)** | `MapSpawnSelect` → `CharacterCreationProfession` → `CharacterCreationMain` → `LoadingQueueState`. Each screen's NEXT is `onOptionMouseDown({internal="NEXT"})`: spawn `clickNext()` needs a valid `listbox.selected`; profession NEXT has no checks; appearance NEXT runs `initPlayer()`, saves the account's first/last name, and enters the world. Names are prefilled from `MainScreen.instance.desc` |
| Account creation is implicit | Connecting with unknown credentials on an `Open=true` `-nosteam` server creates the account (`pzt_c1` appeared without any extra step) |
| **Skipping the TIS logo** | `GameWindow.initShared`: `TISLogoState` is added unless `Core.debug && DebugOptions.uiDisableLogoState` — key `UI.DisableLogoState` in `<cachedir>/debug-options.ini` (`ConfigFile` key=value; `UI.DisableWelcomeMessage` lives alongside). So the ~20 s logo is skippable only for `-debug` clients, which servers accept only for **admin** accounts → drive the primary test client as the server's bootstrap admin (`-adminpassword`). No non-debug launch arg exists for it. |

**Result (attempt #8, run `s2-20260909-132605` → server `s1-20260909-132530`): ✅ fully automated join.**
Timeline: launch → harness loaded 10 s → T&C auto-skipped, main menu 40 s →
manifest read, popup filled, `connect()` fired 43 s → **Lua reloaded with the
server's mod list at 50 s** (harness loads a second time) → spawn regions
listed (4), NEXT → profession NEXT → appearance NEXT at 59 s → world loading
("game loading took 98 seconds") → server: `Connected new client … ID # 0`,
`CreatePlayerPacket.processServer > position:10819,9437,0`. Total ≈ 200 s
cold, dominated by first-time world load.

Attempt log: #1 manual observation (form reached); #2 harness never loaded
(mods reset marker); #3 harness never discovered (no `42/mod.info`); #4
connect refused (`-debug` non-admin); #5 connected, stuck at spawn select
(harness targeted Coop* screens); #6/#7 still stuck — harness lost at join
because **the client resets Lua with the SERVER's `Mods=` list on connect**,
dropping locally-enabled mods; #8 harness server-listed → success.

**Design consequences:**
- The harness mod must be in the server's `Mods=` (and present in both the
  server's and each client's `mods/` folder). `Server.seed()` does this.
- Client-side state must survive a mid-flow Lua reset: stages are keyed on
  screen visibility + idempotent step flags, manifest re-read from disk.
- Golden client cachedir = `options.ini` (T&C flag), `mods/` (harness +
  `default.txt` + reset marker), `db/ServerList.db` (saved credentials),
  `Lua/pzt-join.txt` (manifest). ~1 MB. Second joins skip character
  creation entirely (account + character persist server-side).
- Budget for L3 (admin `-debug` client, normal rendering): ~10 s to connect,
  ~5 s creation (skipped from a fixture), world load ~17 s, click → **player
  ready ≈ 35 s** per client launch.

**Admin-mode run** (`s2-20260909-133311`, `--username admin --debug
--exit-on-spawn`, logo skip seeded): harness 10 s → main menu **16 s** (logo
skipped; was ~40 s) → connect 18 s → Lua reload 24 s → spawn/profession/
appearance NEXT by **33 s** → `game loading took 113 seconds` → in-world at
**148 s**, early exit fired. `-debug` accepted for the admin account, so the
primary driven client should always be the bootstrap admin. World load is now
~75% of wall time — the T3 target.

World-load phase breakdown (client `Logs/*DebugLog.txt` timestamps, gaps >4 s):
**81 s inside `loadAnimalDefinitions`** (B42 animal definition loading on
join), 21 s between `SafeMode is on` and `IsoMetaGrid.Create` (asset
streaming), 4–5 s each for model loading and `bWaitForAssetLoadingToFinish2`.
Everything else is sub-second. So the fix for L3 latency is whatever makes
animal definitions load fast, not the join flow, which is now ~33 s.

**Warm rerun** (`--reuse-cache` on the admin client dir, same server):
character creation **skipped entirely** (existing character loaded — the
golden-fixture behaviour works), join at 19 s, Lua reload 24 s, but
`game loading took 120 seconds` — identical cost, so the phase is neither
disk-cache nor world-creation bound. The server log shows it idle for the
whole window: the cost is entirely client-side.

**Root cause: `-safemode`.** In the jar, `loadAnimalDefinitions` is Lua-table
parsing plus `ModelManager.getLoadedModel` for each animal type's five body
models (body/fleece/headless/skeleton/skel-no-head); under `-safemode` those
model loads stall. Run `s2-20260909-134516` (same admin cachedir, **no
`-safemode`**, fresh server so character creation ran again): harness 8 s →
connect 10 s → Lua reload 14 s → spawn/profession/appearance NEXT by 15 s →
**`game loading took 17 seconds`** at **32 s** from launch.
`loadAnimalDefinitions` dropped from 81 s to under a second. Driver default is
now normal rendering; `--safemode` is opt-in for GPU-less hosts (and would
need this cost budgeted).

**Correction (found while building T0):** every "in-world" above really means
"world loaded, sitting on the **Click to Start** screen". `GameLoadingState.update`
polls `Mouse.isButtonDown` / `GameKeyboard.isKeyDownRaw` before entering
`IngameState`; nothing in the client console or the harness fires until then
(`OnGameStart` and the player object come *after* the click). `pzt` posts a
left click to the client's own window (`PostMessage`, matched by pid, no focus
change), which GLFW delivers like real input: loaded 32.3 s → click 32.6 s →
`OnGameStart` 33.3 s → player ready 34.3 s.

RCON `quit` (the S1 open follow-up) verified on this server: auth + `quit`
→ clean "Shutdown handling finished", exit 0.
## T0 — provision / boot / attach split ✅ 2026-09-09

`testing/pzt/` package (`server.py`, `client.py`, `fixture.py`, `harness.py`,
`win32.py`, `cli.py`; the S1/S2 spike scripts folded in). Usage in
[README.md](README.md).

**Provision** (`prov-20260909-140115` → fixture `default`, 10.9 MB): fresh
server started in 13.9 s with a *partial* `pzt_SandboxVars.lua` (only
`VERSION = 6` + `Zombies = 6`) — the server fills the rest with defaults and
rewrites the full file, so overrides need no template. Admin client created
the world + character, was clicked into the world, executed `quit` over the
command bus (`getCore():quitToDesktop()` → clean disconnect, rc 0), server
`quit` rc 0, snapshot of server (`Server/`, `db/`, `Saves/`, `options.ini`)
and client (`options.ini`, `db/ServerList.db`, `Lua/`, `Saves/`,
`debug-options.ini`) cachedirs — `mods/` deliberately excluded and
re-installed at boot/attach so a fixture never pins a stale harness.

**Run** (`run-20260909-140444`, fixture restored into a fresh run dir):

| Phase | t (s) |
|---|---|
| server started (restored world) | 13.4 |
| client launch → harness loaded | +8.6 |
| connect → Lua reload with server mod list | +10.6 / +15.2 |
| world loaded (no creation screens) | +32.3 |
| click posted → `OnGameStart` → player ready | +32.6 / +33.3 / **+34.3** |
| `ping` round-trip over the command bus | 0.3 |
| graceful client quit / server stop | rc 0 / rc 0 |
| **total incl. 10 s hold** | **68.6** |

Facts: a client's window is owned by the `java.exe` pid we spawn (pid match
works); `PostMessage` clicks need no focus; the harness survives the join-time
Lua reset (last executed command seq is recovered from `pzt-ack.txt`);
`Saves/Multiplayer/<ip>_<port>_<md5(user)>` is the client's chunk cache, keyed
by port, so booting a fixture on its recorded port keeps it warm.

## S3 — Mods under -nosteam ✅ 2026-09-09

`pzt spike S3` (runs `s3-20260909-143715` / `-143818`). Subject: KeenPerception
(workshop item 3685392864 — 1 KB of *shared* Lua, no dependencies, visible
effect: removes the Keen Hearing ↔ Deaf trait exclusivity) added to the
fixture server's `Mods=`.

| Variant | Server | Client |
|---|---|---|
| A — mod exists only in the Steam workshop folder | `WARN … ZomboidFileSystem.loadModAndRequired> required mod "KeenPerception" not found`; **boots normally, 0 errors** | same WARN; **joins and spawns normally** (ready 34.8 s); mod inactive (`trait.check`: exclusivity intact) |
| B — copied into `<cachedir>/mods/` on both sides | `loading KeenPerception`; mod active | `loading KeenPerception` (menu + post-join reload); mod active |

Facts:
- Bytecode: `ZomboidFileSystem.getAllModFolders` (order `workshop,steam,mods`)
  resolves `workshop` via `getStagedItemModsFolders` and `steam` via
  `getInstalledItemModsFolders`, **both gated on `SteamUtils.isSteamModeEnabled`**
  → under `-nosteam` only `<cachedir>/mods` is searched. There is no server
  `-modfolders` (the string exists only in `MainScreenState`), and
  `WorkshopItems=` needs Steam too. Copying is the only option.
- **A missing mod is a WARN, not a failure.** Server boots, client joins,
  everything runs without it. `pzt` now records `required mod "X" not found`
  as `mods_not_found` on both drivers and `pzt run` fails on it — otherwise a
  broken profile passes vacuously.
- The copy strategy is the seed of the T1 profile builder: `pzt/mods.py`
  indexes `steamapps/workshop/content/108600/*/mods/*` by the `id=` in their
  (version-folder) `mod.info` and copies by folder name; `harness.install`
  places harness mods from the repo and everything else from that index.
- Every copied mod adds the `AdvancedAnimator … NoSuchFileException` probe
  noise for its optional `AnimSets`/`actiongroups` folders (baselined), and
  clients log `WARN:MISSING in SettingsTable: WorkshopItems` — harmless.

## S4 — Result channel ✅ 2026-09-09

`pzt spike S4` (run `spike-20260909-143930`). `TK.result(name, table)` in the
harness writes `<cachedir>/Lua/pzt-results/<name>.json` via
`getFileWriter("pzt-results/<name>.json", true, false)`; `pzt` (`bus.py`)
collects and `wait_result()` blocks on one.

| Side | Command → file | Latency |
|---|---|---|
| client | `result s4_client hello` → `clients/admin/Lua/pzt-results/s4_client.json` | **0.27 s** |
| server | `result s4_server hello` → `server/Lua/pzt-results/s4_server.json` | **1.5 s** (server bus polls every 20 ticks) |

Facts:
- `LuaManager$GlobalObject.getFileWriter` roots at `<cachedir>/Lua/`, rejects
  `..` (`hasRelativePath`), **accepts subfolders** (creates them), and checks
  the extension against `LuaManager.ALLOWED_FILE_EXTENSIONS` (ini/cfg/txt/log/
  **json**). So `.ready` marker files are not possible — and not needed: a
  file that parses as a complete JSON object (`"complete": true` is the last
  key the harness writes) is the ready signal; a partial write never parses.
- `getModFileWriter(modId, name, …)` writes into the **mod's own folder**
  (`ChooseGameInfo.getModDetails(id).getCommonDir()`), not the cachedir — not
  what we want for run artefacts.
- The same `getFileReader`/`getFileWriter` pair is the command bus on both
  sides (`pzt-cmd.txt` / `pzt-ack.txt`); the dedicated server polls it from
  `OnTick` (fires fine on the server) and `EveryOneMinute`.
- JSON is encoded by a 40-line encoder in `PZTestKit_Core.lua` (Kahlua has no
  json lib); Java objects fall back to their `toString()`.
## S5 — Time acceleration in MP ✅ 2026-09-09

`pzt spike S5` (runs `spike-20260909-143930`, re-run `spike-20260909-144417`).
Mechanism (jar): admin command **`settimespeed <x>`** = `GameTime.getInstance()
.setMultiplier(x)` on the server **plus a `SetMultiplierPacket` to every
client** (`processClient` applies it). Works over RCON; no debug flag needed.
(RCON `help`, by contrast, throws `MissingFormatArgumentException` inside the
server's translator and logs two error lines — don't call it.)

| Measure (run 1) | Server | Client |
|---|---|---|
| baseline rate | 0.25 game-min per wall-second (a game day = 96 min real) | 0.25 |
| after `settimespeed 30` | **8.0 game-min/s (32×)** | **8.7 game-min/s (35×)** — the packet reached the client |
| `getMultiplier()` | 4.80 → 143.9 | 0.80 → 115.2 (the getter is scaled, not the argument you passed — compare ratios, not values) |
| player calories (client) | | −4.35 kcal in 18 s at 1× vs **−238.9 kcal in 31 s at 30×** (≈32×): nutrition ticks scale with game time |
| player weight | | unchanged over a minute (expected: weight moves on the daily calorie balance) |

Lesson from run 1: restoring with the server-only Lua `setMultiplier(1)`
left the client at 30× and the two clocks drifted **3.4 game-hours apart
within a minute** with no correction. Always change speed through
`settimespeed` (broadcast).

Re-run with `settimespeed` both ways: baseline 0.26 / 0.26 game-min/s,
30× → **8.0 (server) / 8.9 (client)**, calories −238.8 kcal in 31 s; after
`settimespeed 1` the server returned to 0.26 and the client's clock ran
**backwards** for the next window (−5.6 game-min/s: it snapped back onto the
server's clock, which it had overtaken at 35× vs 32×), ending **0.13 game-h**
apart. So a multiplier change re-syncs the client clock; steady state does
not. `getMultiplier()` ratios: server ×29.9, client ×143.8 (the client keeps
a different internal scale — never compare raw getter values across sides).
RCON replies to `settimespeed` are sometimes empty; verify via the snapshot.
## S6 — Witness round-trip ✅ 2026-09-09

`pzt spike S6` (runs `spike-20260909-143930`, re-run `spike-20260909-144417`).
Client `witness.*` → `sendClientCommand(player, "PZTestKit", "witness", …)`;
server `OnClientCommand` answers with its own view via `sendServerCommand`;
the client compares, logs `PZTK: witness <kind> match=…` and writes
`witness_<kind>.json`. Round-trip ≈ 1 s.

| Probe | Client view | Server view | Match |
|---|---|---|---|
| player modData `pzt_probe` set client-side | `v1` | **nil** | ✗ caught |
| … after `player:transmitModData()` | `v1` | `v1` | ✓ |
| nutrition (calories / weight / carbs / lipids / proteins) | 498.64 / 80 / −65.65 / −21.20 / −16.13 | 498.43 / 80 / −65.70 / −21.21 / −16.14 | ✓ within 0.2 kcal — the 0.2 kcal is **mirror lag, not client authority**: the *server* computes and pushes at 1 Hz (direction corrected 2026-09-10, see the Facts below) |
| item spawned by the server (`additem`) | id 2130049510, 10/10 | **same id**, found, 10/10; player inventory = 8 items server-side | ✓ the server holds the player's inventory |
| … after client-side `setConditionMax(5)`, `setCondition(3)`, modData `pzt_tag`, `sendItemStats(item)` | 3/5, `tag1` | **10/10, nil** | ✗ caught — nothing reached the server |
| item created client-side (`inventory:AddItem("Base.Carrots")`) | id 592978320 | **not found**, inventory still 8 | ✗ caught |
| both item probes again **60 s later** (re-run) | 3/5 `tag1`; carrot present | still 10/10 nil; carrot still absent | ✗ — no periodic inventory sync catches up |

Facts:
- The Lua global `sendItemStats` is `GameServer.sendItemStats` (packet
  `ItemStats`, server → the owning player's connection); on a client it is a
  silent no-op. `SyncItemFieldsPacket` is likewise server-originated. **There
  is no client→server "push my item's fields" API**: a mod that edits an
  inventory item's fields or modData client-side (food nutrition values,
  condition, custom modData) desyncs silently — mutate on the server
  (`sendClientCommand` → server edits → `sendItemStats`) or accept
  client-only semantics. This is the ItemQuality class of bug, now a failing
  witness.
- Player modData is not auto-synced; `IsoPlayer:transmitModData()` pushes
  it (works in 42.20.4 MP).
- `additem` over RCON: `additem "user" "Module.Item" [n]` → "Item … Added in
  admin's inventory." — items reach the client with server-assigned ids.
- **Nutrition direction, corrected 2026-09-10 (slice 01).** This spike read the
  0.2 kcal agreement as "the client computes, the server mirrors". It is the
  other way round: the **server** computes nutrition (an MP client skips the
  macro drain and `updateCalories` entirely, and never runs
  `ISEatFoodAction:complete()`) and pushes the whole `Nutrition` object at eat
  time and once a second; the 0.2 kcal is the sampling skew of that 1 Hz mirror
  against a ~0.26 kcal/s drain. Measured in run `exp01-20260910-000351`: a
  client-side `setCalories(3000)` never reached the server and reverted within
  3 s, while a server-side write reached the client within 3 s; hunger and
  thirst behave identically (run `exp01-20260910-003929`). The measurement in
  the table stands — only its interpretation changed. Full chain and citations:
  [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md) § MP behaviour.
## S7 — reloadlua iteration ✅ 2026-09-09

`pzt spike S7 --reloadalllua` (run `spike-20260909-143930`). The harness's
`TK.version` constant was edited on disk (in the run's own copy of the mod)
and reloaded.

| Step | Result |
|---|---|
| RCON `reloadlua PZTestKit_Core.lua` (server) | "Lua file reloaded"; `version` 1 → 2, `TK.ticks` **continued** (1140 → 1174) and the command bus kept its seq — state in globals survives (`TK = TK or {}`) |
| client after the server reload | untouched (`version` 1): `reloadlua` is server-local, no packet to clients |
| client `reloadLuaFile("PZTestKit_Core.lua")` | returns nil, **no effect** |
| client `reloadLuaFile("<absolute path to the client's copy>")` | `version` → 3 — the global wants the full path |
| RCON `reloadalllua` (server) | "Lua files reloaded", server stays up, state survives — but re-running every file on the dedicated server throws **~31 Lua errors** (`Lua(Vanilla).ISStyle> Exception thrown` + stack traces: UI files executed server-side) |

Consequences: the fast authoring loop is `reloadlua <file>` on the server plus
`reloadLuaFile(<abs path>)` through the client command bus (`lua.reload`),
one file at a time; `reloadalllua` is not usable on a dedicated server. The
`ReloadLuaCommand` matches the argument with `endsWith` against the loaded
file list and `LuaManager.RunLua`s it — nothing else (no re-registration of
events: a file that `Events.X.Add`s on load will add a second handler, so
harness/mod files must guard against double registration if they are meant
to be reloaded).
