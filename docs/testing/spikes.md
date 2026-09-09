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

## S3 — Mods under -nosteam
## S4 — Result channel
## S5 — Time acceleration in MP
## S6 — Witness round-trip
## S7 — reloadlua iteration
