# Plan 23 — the survivor: instincts, a chained day and the goal seam

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive one character through a game day and its night on the Plan 22 base: sessions that chain on one world (a fixture snapshotted from the last run), instincts that fight with the map's edges in view, flee on wounds, eat and drink at the first moodle, never build a load, and sleep at night; a goal layer behind one seam with a scripted source and an LLM source (the installed `claude` CLI); the 60 Hz poll paced; every session graded off its artifact.

**Architecture:** The Python base `testing/agent/base/` keeps its modules and gains `planner/goals.py`, `planner/view.py`, `planner/llm.py`, `gates_e.py`, `gates_f.py`; the drivers' shared code moves into a non-frozen library `testing/agent/driverlib/`; `pzt` gains `snapshot --from-run`. PZAgent 1.2 adds the square's four edge fields, `me.hour`, a `sleep` skill and a `maxWeight` cap on `interact loot`, and polls `cmd.txt` every third tick. Every live session is a new driver on the library, graded by a versioned gate; the Plan 22 drivers, `_dlib.py`, `gates.py`'s functions and every committed artifact stay frozen.

**Tech Stack:** Kahlua (Lua 5.1 dialect) under lupa 2.8's Lua 5.1 host for the offline tests; Python 3 (`pytest`, stdlib `json`, `dataclasses`, `threading`, `subprocess`); the harness `testing/pzt`; RCON through `xlib`; detached launches polled through the persisted artifact; the `claude` CLI 2.1.310 on this host as the LLM route.

**Spec:** `docs/superpowers/specs/2026-10-28-plan-23-survivor-design.md` (§ 2 the binding principles; § 4 the chain; § 5 PZA/1.2 and the poll; § 6 the edges; § 7 the instincts; § 8 the goal layer; § 9 the instrument; § 10 the sessions; § 11 out of scope). The Plan 22 report `docs/superpowers/specs/2026-10-27-plan-22-agent-base-report.md` §§ 5, 7, 8 are the findings every change answers; the live readings are the five Plan 22 guides under `testing/artifacts/`.

## Global Constraints

- Spec § 2, binding on every task: **instincts before goals** (no goal is sent while an instinct branch answers; a pre-empted goal is `superseded`, never lost); **the frame is the truth the planner acts on** (a server read informs a grade or the view, never a reflex, and never stalls the planner); **index-first through `PZA.call`, Kahlua rules, one flush a tick, under 1 ms at 60 Hz**; **a need is the game's** (thirst above 0.12, hunger above 0.15 [#0509, #0508], fatigue above 0.6 [#2279]; nothing seeds, speeds or writes a stat); **the load is never built** (a loot stops at the weight the carry ratio allows); **nothing changes offline** (a chain's next first frame is diffed against the last session's last frame and every difference reported); **one driver file per session kind, frozen at its first boot**, the library not frozen, every artifact naming the tree's commit; **the LLM is a goal source** (a view of about 2 KB of game state in, one validated goal out, the scripted source standing in on a late, malformed or unsafe answer; it never sends an action, never sees a frame, never receives anything but game state); **every gate versioned per pass, every grade with an offline case that fails it**, `gates.py` frozen and new gates in new modules.
- Spec § 5: PZA/1.2 appends and never reorders (`x-prior` per group keeps the 1.1 arity decodable); `PZA.VERSION` "1.2", `proto` "PZA/1"; the goldens re-recorded under this named change; `L.POLL_EVERY = 3`.
- Spec § 10: X4-3 and X5-2 run before the chain (the Lua frozen before it), the chain before F1; each session at most 14 minutes of loop wall inside a 1200 s budget; the chain's sessions are `e_day.py` on `agent` → `agent-s1` → …; a death ends the chain and is written up, never re-run.
- Spec § 11, out of scope: the sidecar and any JDK; a `fill` skill or any water source but a looted container; vehicles, firearms, crafting, building, farming, the sit posture; a second client; any LLM route but the installed CLI; prompt engineering past F1's reading; the nutrition mod's code; any change to the install or the launcher.
- CLAUDE.md § 5 binds every boot: `python testing/pzt doctor` first; one live session repository-wide; never `-safemode`; ≥ 12 GB host memory free, read and ledgered; detached launches by the controller, polled across foreground calls; a driver is never edited after its run; a gate function whose output an artifact carries is versioned per pass, never edited; a harness change lands before the run that uses it, in its own commit; a live boot never overlaps an offline edit under `mod/`. Angus's 2026-10-28 direction ("the minutiae ... you are free to explore, prototype, iterate") is the standing approval for this plan's boots (ruling P23-A, ledgered at the plan's opening).
- CLAUDE.md § 6: pathspec commits only (`git add -- <new>`, `git commit -m "…" -- <paths>`); no `--amend`; no Claude attribution; implementers never push; no subagent runs `git stash`, `checkout --`, `reset`, `restore`, `add -N`, `add -f`, `add -A`, `add .` or any index-wide command; page writers never edit `docs/reference/claims.tsv` (a delta file the controller applies); the frozen drivers (`a_pipe*.py`, `b_actions*.py`, `c_survive*.py`, `p22_probe.py`, `x4_link.py`, `x4_link_2.py`, `x5_combat.py`, `d_survive.py`, every `*_grade*.py`), `_dlib.py`, `gates.py`'s existing functions and every committed artifact are never edited; `testing/artifacts/x391f-20261013-113457/` and the `.claude/worktrees/*` gitlinks are Angus's, never staged.
- Kahlua rules for every PZAgent Lua file: no `goto`, no `%d` on floats, no `#` on Java lists, no `%g`/`%G`; every Java member through `PZA.call`; a vanilla Lua class or function index-checked (`X ~= nil and X.new ~= nil`) before the call. Lints before any Lua commit: `python tools/kahlua_lint.py testing/PZAgent` 0; `python tools/luabalance.py <each touched .lua>` green (HEAD copies first, then the working tree); `python tools/hotpath_lint.py testing/PZAgent` 0; `python tools/mod_lint.py testing/PZAgent/PZAgent` 0 ERROR. Every new Lua file LF with `newline=""` handling.
- Tests: `python -m pytest testing/tests/pzagent -q > <workspace>/<task>-pytest-folder.txt 2>&1`, read back; the full `python -m pytest tools/tests testing/tests -q`, saved and read back, once per task that touches `testing/agent/`, `testing/pzt/`, `tools/` or the Lua (baseline 9481 passed, 28 skipped at the Plan 22 close; the count never drops; no test is deleted in this plan). `python tools/pza_schema.py --check` in sync before any commit touching the schema or its targets.
- Every number in a brief, a guide or a row comes from its artifact or row, never from memory; a guide names every number's JSON path or `state.log` line.

## Rulings carried in from the plan's opening

- **P23-A** Angus's direction of 2026-10-28 is the standing approval for every boot this plan names, under CLAUDE.md § 5's rules — cost if wrong: a session Angus did not want, visible in the ledger before its write-up.
- **P23-B** `goals.json` is a hand-written JSON Schema under `testing/agent/base/schema/`, the source the goal dataclasses are tested against (a test asserts each `Goal` type's fields equal its schema entry), not a generator target: a generator importing planner code would couple `tools/` to the base — cost if wrong: two files to keep in step, under one test.
- **P23-C** `x4_link_3.py` and `x5_combat_2.py` are copies of their predecessors with their constants swapped (the fix-pass form: the same phases, the same frozen gate, so the readings compare), not ports onto the library; `e_day.py` and `f_goals.py` are the library's first drivers — cost if wrong: two more copies of the helpers, retired with their drivers.
- **P23-D** A water container's emptiness is learnt from a `consume` ending `failed not valid` (the Lua refuses an empty one), recorded in `World.empty_ids`, since no line carries a fluid amount; a bottle refilled or looted again is a new id — cost if wrong: one wasted consume per empty container.
- **P23-E** The `sleep` skill copies vanilla's `ISWorldObjectContextMenu.onSleepWalkToComplete` (42.21 install, `media/lua/client/ISUI/ISWorldObjectContextMenu.lua` L1034–L1098): the safety reads (`getNumVisibleZombies`, `getNumChasingZombies`, `getNumVeryCloseZombies`), the pain and panic refusals, `ISTimedActionQueue.clear`, the hours from fatigue with the bed quality (`ISWorldObjectContextMenu.getBedQuality`, index-checked; `bed` nil is the floor), `setBed`, `setBedType`, `setForceWakeUpTime`, `setAsleepTime(0)`, `setAsleep(true)`, and on a client with `SleepAllowed` the fade; whether the dedicated server fast-forwards a lone sleeper is Task 3's jar read and the first night's reading — cost if wrong: a sleep of game hours at wall speed, which the skill's `SLEEP_MS` budget ends `failed interrupted` and the guide reports.

---

### Task 1: `pzt snapshot --from-run` — a fixture taken from a finished run, with its lineage

**Files:**
- Modify: `testing/pzt/fixture.py` (append `snapshot_from_run`), `testing/pzt/cli.py` (`cmd_snapshot` and its subparser, after `provision`'s), `docs/platform/harness.md` (one row in the `pzt` command table at L37–L41: `snapshot --from-run <run> --name <fixture> --parent <fixture> [--session N]`; `python tools/page_lint.py docs/platform/harness.md` 0)
- Test: `testing/tests/test_pzt_snapshot.py`

**Interfaces:**
- Consumes: `fixture.snapshot(name, server_cache, client_caches, record)`, `fixture.load(name)`, `fixture.fixture_dir`, `paths.RUNS`.
- Produces: `fixture.snapshot_from_run(name, run_dir, parent, session, run_id=None) -> record`: the parent's record (`load(parent)`) copied with `created` (now, ISO seconds), `parent` (the parent fixture's name), `run` (`run_id`, default the run dir's basename), `session` (int), `lineage` (the parent's `lineage` list, default `[]`, plus the parent's name), `provision_run`, `build`, `server`, `clients` kept; the server cache `<run_dir>/server`, each client cache `<run_dir>/clients/<user>` for every user in the parent's `clients`; raises `SystemExit` naming the path when `<run_dir>/server` or a parent user's client dir is absent. `cli.cmd_snapshot(a)`: `--from-run` (a run dir, or a run id resolved as `os.path.join(RUNS, id)`), `--name` (required), `--parent` (required), `--session` (int, default 1); prints `FIXTURE '<name>' snapshotted from <run>: <size_mb> MB, parent <parent>, session <n>` and returns 0.

- [ ] **Step 1: The failing tests.** `testing/tests/test_pzt_snapshot.py`:

```python
import json, os
import pytest
from pzt import fixture as fx
from pzt import cli


def _run_dir(tmp_path):
    rd = tmp_path / "runs" / "e_day-20261028-120000"
    for p in ("server/Saves/Multiplayer/pzt/map_p.bin", "server/Logs/x.txt", "server/mods/PZTestKit/mod.info",
              "clients/admin/options.ini", "clients/admin/Logs/y.txt", "clients/admin/mods/PZAgent/mod.info"):
        (rd / p).parent.mkdir(parents=True, exist_ok=True)
        (rd / p).write_text("x")
    return rd


@pytest.fixture
def fixtures(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    monkeypatch.setattr(fx, "FIXTURES", str(root))
    (root / "agent" / "cache" / "server").mkdir(parents=True)
    rec = {"name": "agent", "build": "42.21.0", "provision_run": "prov-20261026-092028",
           "server": {"sandbox": {"Zombies": "5"}, "mods": ["PZTestKit"]}, "clients": {"admin": {"debug": True}}}
    (root / "agent" / "fixture.json").write_text(json.dumps(rec))
    return root


def test_snapshot_from_run_copies_the_caches_and_writes_the_lineage(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    rec = fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    cache = fixtures / "agent-s1" / "cache"
    assert (cache / "server" / "Saves" / "Multiplayer" / "pzt" / "map_p.bin").is_file()
    assert not (cache / "server" / "Logs").exists() and not (cache / "server" / "mods").exists()
    assert (cache / "clients" / "admin" / "options.ini").is_file() and not (cache / "clients" / "admin" / "mods").exists()
    assert rec["parent"] == "agent" and rec["run"] == "e_day-20261028-120000" and rec["session"] == 1
    assert rec["lineage"] == ["agent"] and rec["server"]["sandbox"] == {"Zombies": "5"} and rec["build"] == "42.21.0"
    assert json.load(open(fixtures / "agent-s1" / "fixture.json"))["name"] == "agent-s1"


def test_a_second_link_extends_the_lineage(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    rec = fx.snapshot_from_run("agent-s2", str(rd), "agent-s1", 2, run_id="e_day-20261028-130000")
    assert rec["lineage"] == ["agent", "agent-s1"] and rec["run"] == "e_day-20261028-130000"


def test_a_run_without_a_server_cache_or_a_client_is_refused(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    import shutil
    shutil.rmtree(rd / "clients" / "admin")
    with pytest.raises(SystemExit, match="clients"):
        fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    shutil.rmtree(rd / "server")
    with pytest.raises(SystemExit, match="server"):
        fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)


def test_the_cli_resolves_a_run_id_under_runs_and_dispatches(tmp_path, fixtures, monkeypatch, capsys):
    rd = _run_dir(tmp_path)
    monkeypatch.setattr("pzt.cli.RUNS", str(tmp_path / "runs"), raising=False)
    calls = []
    monkeypatch.setattr(fx, "snapshot_from_run", lambda *a, **k: calls.append((a, k)) or {"size_mb": 9.5})
    rc = cli.main(["snapshot", "--from-run", "e_day-20261028-120000", "--name", "agent-s1", "--parent", "agent"])
    assert rc == 0 and calls[0][0] == ("agent-s1", str(rd), "agent", 1)
    assert "FIXTURE 'agent-s1' snapshotted" in capsys.readouterr().out
```

- [ ] **Step 2: Run them.** `python -m pytest testing/tests/test_pzt_snapshot.py -q > <workspace>/t1-red.txt 2>&1`; read back: FAIL (`snapshot_from_run` and `snapshot` subcommand absent).
- [ ] **Step 3: `fixture.snapshot_from_run`** appended to `fixture.py`:

```python
def snapshot_from_run(name, run_dir, parent, session, run_id=None):
    """A fixture from a finished run's caches (Plan 23 spec § 4, P23-1): the world the server saved at the session's
    stop, under the parent fixture's record with its lineage. The run's `server/` and each parent client's
    `clients/<user>/` are snapshotted with the provision's skip lists."""
    import datetime
    rec = load(parent)
    server_cache = os.path.join(run_dir, "server")
    if not os.path.isdir(server_cache):
        raise SystemExit(f"no server cache at {server_cache}: the run did not boot a server")
    client_caches = {}
    for user in rec.get("clients") or {}:
        c = os.path.join(run_dir, "clients", user)
        if not os.path.isdir(c):
            raise SystemExit(f"no client cache for {user} at {c}: the run did not attach every client of {parent}")
        client_caches[user] = c
    record = dict(rec, created=datetime.datetime.now().isoformat(timespec="seconds"), parent=rec["name"],
                  run=run_id or os.path.basename(os.path.normpath(run_dir)), session=int(session),
                  lineage=list(rec.get("lineage") or []) + [rec["name"]])
    return snapshot(name, server_cache, client_caches, record)
```

  `cli.cmd_snapshot(a)`: `run_dir = a.from_run if os.path.isdir(a.from_run) else os.path.join(RUNS, a.from_run)`; `rec = fx.snapshot_from_run(a.name, run_dir, a.parent, a.session)`; `say(f"\nFIXTURE '{a.name}' snapshotted from {run_dir}: {rec['size_mb']} MB, parent {a.parent}, session {a.session}")`; `return 0`. Import `RUNS` from `.paths`. The subparser after `provision`'s: `p = sub.add_parser("snapshot", help="snapshot a finished run's world as a new fixture (the chain's next session boots it)")` with `--from-run` (required), `--name` (required), `--parent` (required), `--session` (type int, default 1), `p.set_defaults(fn=cmd_snapshot)`. The harness.md row in the command table, in the table's voice: `| `snapshot --from-run <run> --name <fixture> --parent <fixture> [--session N]` | the run's server and client caches snapshotted as a fixture whose record names its parent, run, session and lineage, so the next session boots the world the last one left (Plan 23) | seconds |`.
- [ ] **Step 4: Green.** The test file → `t1-green.txt`; `python tools/page_lint.py docs/platform/harness.md` 0; `python -m pytest testing/tests/test_pzt_snapshot.py testing/tests/test_cli_profile.py testing/tests/test_profile.py -q` saved.
- [ ] **Step 5: Commit.** `git add -- testing/tests/test_pzt_snapshot.py` then `git commit -m "Plan 23 Task 1: pzt snapshot --from-run, a fixture from a finished run with its parent, run, session and lineage" -- testing/pzt/fixture.py testing/pzt/cli.py testing/tests/test_pzt_snapshot.py docs/platform/harness.md`.

---

### Task 2: The driver library `testing/agent/driverlib/`

**Files:**
- Create: `testing/agent/driverlib/__init__.py` (the docstring: what the library is, the frozen rule it is exempt from, that each artifact names the tree's commit), `testing/agent/driverlib/session.py`, `testing/agent/driverlib/polls.py`, `testing/agent/driverlib/record.py`, `testing/agent/driverlib/chain.py`
- Test: `testing/tests/pzagent/test_driverlib.py`

**Interfaces:**
- Consumes: `_dlib` (`wait_memory`, `state_dir`, `clear_state_dir`, `preboot`, `boot`, `bus_stats`, `REPO`, `C.git_say`, `C.git_dirty`), `xlib` (`Xs`, `free_gb`, `memory_ok`, `grep_noecho`, `BusDead`, `Budget`, `stalled`), `agent.base` (`World`, `Actions`, `FileTransport`, `pza1`, `gates.pct`).
- Produces (`session.py`): the constants `DEFAULTS` dict (`BUDGET_S 1200.0, MIN_FREE_GB 12.0, DAY_CAP_S 840, PLANNER_HZ 2, SERVER_POLL_S 60, DAMAGE_POLL_S 5, PERSIST_S 30, MEM_POLL_S 300, LIVE_MIN_FREE_GB 0.5, STOP_HEALTH 0.0, MEM_LOW_READS 2, BUS_DEAD_S 60, BUS_DEAD_POLLS 2, STORM_N 10, STORM_WINDOW_S 60, HELLO_TIMEOUT_S 60.0, FRAME_TIMEOUT_S 10.0, KIT "Base.BaseballBat", POLL_S 0.1, LAST_DECISIONS 10, KIT_TIMEOUT_S 30.0, EQUIP_TIMEOUT_S 30.0, ACT_TIMEOUT_S 10.0, SERVER_TIMEOUT_S 10.0, LAST_FRAMES 300, DEATH_WINDOW_S 300, PAIR_S 1.0, SERVER_RECORDS_KEPT 5000, PARK_RX` (d_survive's)); `parse_argv(argv, driver_file, allowed=())` (the refusal text for any argument not in `allowed`, else None; `allowed` names flags such as `--session`, each taking one value); `new_out()`, `new_frames()`; `driver_checks(driver_file, key, driver, profile, repo, git_say, git_dirty)`; `preboot(driver_file, key, driver, profile, repo)`; `memory_gate(xs, min_gb, wait=None)`; `clearing_make_client(make)`; `count_parks(consoles, admin_parked, park_rx)`; the pure helpers `players_list`, `server_stats`, `read_players`, `item_added`, `damage_last`, `frame_row`, `body_health`, `pair_frame`, `needs_row`, `in_window`; `DecisionTail`, `Fights`, `Stop`; and `class Session` (d_survive's `Day` generalised): `Session(xs, transport, planner_factory, clock, sleep, players, free, limits, poll_s, polls=None)` where `planner_factory(world, actions, log_path, clock) -> Planner`, with the phases `phase_hello`, `phase_damage_hook`, `phase_kit`, `phase_loop` (d_survive's `phase_survive`, the planner tick, the stops), `run()`, `save()`, `death_record`, `set_stop`, and two hooks a driver may override: `on_frame(line)` (nothing by default) and `extra_record() -> dict` (merged into `out["loop"]` at every save). The server reads go through `polls` (below) when given, else synchronously as d_survive's (the tests of the port run both).
- Produces (`polls.py`): `class PollThread(clock=time.time)`: `schedule(name, every_s, fn)` (fn runs on the worker at most every `every_s`), `start()`, `stop(timeout_s=5.0)`, `latest(name) -> (result, wall) | (None, None)`, `errors` (a list of `{name, wall, error}`), `pending(name) -> bool`; one worker thread, each scheduled read run in turn, an exception caught into `errors` and the schedule kept; nothing on the worker touches the World (the loop merges `latest` on its own thread).
- Produces (`record.py`): `action_rows(sent, t0)`, `loop_summary(session) -> dict` (d_survive's `save` body), `death_record(session, via, detail)`.
- Produces (`chain.py`): `lineage_diff(prev_artifact, first_frame) -> dict` with `position {prev, now, d}`, `health {prev, now}`, `stats {hunger, thirst, fatigue: {prev, now}}`, `inventory_n {prev, now}`, `game_min {prev, now}`, `ok` (every `now` within `LINEAGE_TOL` of `prev`: position 0.5 tiles, health 0.01, each stat 0.001, inventory count equal, gameMin equal), where `prev_artifact` is the last session's `out` (its `loop.last_frames[-1]`) and `first_frame` the new session's first frame; `snapshot_cmd(run_dir, name, parent, session) -> list[str]` (the `pzt snapshot` argv the controller runs).

- [ ] **Step 1: The failing tests** (`test_driverlib.py`): `parse_argv` refuses `["x"]` and `["--help"]`, accepts `[]`, accepts `["--session", "2"]` only when `allowed=("--session",)` and refuses `["--session"]` without a value; `PollThread` runs a scheduled fn on another thread (`threading.get_ident()` differs), `latest` returns the newest result and wall, a raising fn lands in `errors` and the next run still happens, `stop()` joins; `lineage_diff` on two frames equal → `ok True`, a position 1 tile off → `ok False` with `d 1.0`; `Session` ported: copy `test_d_survive.py`'s `DayMod`, `FakeBus`, `_day` fixtures into this file (the fake mod answering equip/attack/other, the server bus's `@reply` shapes) and port the loop tests `test_a_clean_day_runs_every_phase_and_stops_at_the_day_cap`, `test_the_server_is_polled_on_schedule_with_one_paired_needs_row_each`, `test_damage_watch_is_polled_since_the_last_index_and_merged_tagged_server`, `test_a_heavyload_death_keeps_its_record_and_the_frames_explain_it`, `test_a_silent_link_stops_the_loop_as_bus_dead`, `test_a_lua_error_storm_stops_the_loop`, `test_two_consecutive_low_reads_stop_on_memory_and_one_does_not`, `test_a_players_reply_without_the_user_is_a_death_with_its_record` onto `Session` with `planner_factory=Survive`; plus one test that a `polls=PollThread` session's `server_poll` never blocks the loop (the bus stub sleeps 2 s on its own thread while the loop's tick count keeps rising on the fake clock).
- [ ] **Step 2: Run them**; FAIL (no package).
- [ ] **Step 3: The library.** Port d_survive.py L96–L620 into the modules named above, generalised as the interfaces say, with the module docstrings rewritten for the library (no "copied from" lines: the library is the source now); the `Session` loop's server poll with `polls` given: at `SERVER_POLL_S` it reads `polls.latest("stats")` and `polls.latest("players")` (scheduled at the loop's start with `every_s = SERVER_POLL_S`) and `polls.latest("damage")` at `DAMAGE_POLL_S`, merging each result newer than the last merged, the `since` for the damage read taken from the loop's `since_i` under a lock-free handoff (the worker reads `session.since_i` at each call; a record merged twice is skipped by `World.damage_seen_i`).
- [ ] **Step 4: Green**; the folder; the full pytest saved.
- [ ] **Step 5: Commit.** `Plan 23 Task 2: the driver library (session, polls, record, chain): the acceptance driver's shared code as a non-frozen package with a poll thread`.

---

### Task 3: The jar reads — the square's edges, the hour, and sleep on a dedicated server (opus, research)

**Files:**
- Create: `docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md`
- Create: `<workspace>/t3-claims-delta.tsv` (the controller applies it with the note's commit: rows owned by sentences the note's findings will carry on `docs/platform/harness.md#agent` at the write-up tasks; until then the rows are minted `open` with the note as pointer, per CLAUDE.md § 4 a row is never minted before its owner sentence — so the delta is applied at Task 17's write-up, the first page edit, not here; this task only drafts it)

**Interfaces:**
- Produces: the note's §§ 1–4, each ending in a one-line finding and the `pz.sh` commands that read it: (1) `IsoGridSquare.isBlockedTo(IsoGridSquare)`, `isWallTo`, `isDoorBlockedTo`, `isWindowBlockedTo`: which edge of which square each reads for a north and a west neighbour, whether a closed door reads blocked and an open one not, whether a window reads blocked, and the diagonal rule (`isSomethingTo`); (2) `GameTime.getTimeOfDay()` (a float hour) and its relation to `getHour`/`getMinutes`; (3) the sleep path on a dedicated server with `SleepAllowed`: who clears `asleep` (the two `IsoGameCharacter.asleep` writers), what `IsoPlayer.allPlayersAsleep` and `isOnlyPlayerAsleep` gate, whether `GameServer`/`GameTime` fast-forwards when every connected player is asleep and at what multiplier, what `SleepNeeded` adds, and how the client wakes (`setForceWakeUpTime`'s reader); (4) `ISWorldObjectContextMenu.getBedQuality(playerObj, bed)` with `bed` nil, and `Stats.getNumVisibleZombies/getNumChasingZombies/getNumVeryCloseZombies` (what counts).

- [ ] **Step 1:** Read `C:\Users\Angus\pz-b42\WORKSPACE.md`; run `./pz.sh methods zombie.iso.IsoGridSquare`, `./pz.sh dump zombie.iso.IsoGridSquare isBlockedTo`, `isWallTo`, `isDoorBlockedTo`, `isWindowBlockedTo`, `isSomethingTo`; `./pz.sh dump zombie.GameTime getTimeOfDay`; `./pz.sh refs zombie.characters.IsoGameCharacter setAsleep`, `./pz.sh dump zombie.characters.IsoPlayer allPlayersAsleep`, `isOnlyPlayerAsleep`, `./pz.sh grep "allPlayersAsleep"` and dump each referencing method (`GameTime`, `IngameState`, `SleepingEvent`, `ThumpState`), `./pz.sh grep "SleepAllowed"` and `"SleepNeeded"` with their readers dumped; the vanilla Lua `ISWorldObjectContextMenu.getBedQuality` read from the install (read-only).
- [ ] **Step 2:** Write the note (each finding with its class, method and the dump's line, in the house voice of `docs/platform/jar-research.md`); draft the delta rows (grade C, kind `C-only` or `inference`, each pointer a `jar:` pointer as `docs/reference/claims.tsv`'s existing jar rows are formed — copy the form of #3926's pointer cell) into `t3-claims-delta.tsv`.
- [ ] **Step 3: Commit** the note alone: `Plan 23 Task 3: the jar reads for the square's edges, the hour and the dedicated server's sleep path`.

---

### Task 4: PZA/1.2 — the square's edges, `me.hour`, the `sleep` action and `interact`'s `maxWeight`

**Files:**
- Modify: `testing/agent/base/schema/pza1.json`; `tools/pza_schema.py` (only if a record needs `x-prior`: see Step 3); `testing/tests/pzagent/fakemod.py` (`DEFAULT_FRAME.me.hour = 8.0`; a `square(...)` helper default with the four edges `False`), every test asserting a frame's or square's shape; `testing/tests/pzagent/test_replay.py` (the five goldens re-recorded under the named change "PZA/1.2: the square's edges, me.hour, sleep, maxWeight", the hashes and frame counts updated, the docstring naming the change)
- Generated by `--write`: `shared/PZAgent_Schema.lua`, `testing/agent/base/pza1.py`, `testing/agent/base/schema/tools.json`
- Modify: `testing/PZAgent/PZAgent/42/media/lua/shared/PZAgent_Core.lua` (`PZA.VERSION = "1.2"`)
- Test: `tools/tests/test_pza_schema.py` (the new fields reach the three targets; a 12-field square array decodes with the edges None), `testing/tests/pzagent/test_pza1.py`

**Interfaces:**
- Produces: `square.x-order` + `["blockN", "blockW", "wallN", "wallW"]` (booleans: "Whether a step from this square to its north neighbour is blocked (a wall, a closed door or window, a solid object on the edge).", likewise west; "Whether a wall on the north edge blocks sight.", likewise west), `x-prior: 12` on the square record; `me.x-order` + `["hour"]` ("The game's hour of day, 0 to 24, as a number."), `x-prior` stays 11; the action `sleep` with no args, result `result_sleep {sleptH: number, fatigueBefore: number, fatigueAfter: number, bedType: string}`, reasons `not safe`, `not allowed` added to the `reason` enum; `interact` gains `maxWeight` (number, default 0: "A loot stops before the carried weight would pass this; 0 for no cap."); `pza1.Interact(x, y, kind, filter="all", maxWeight=0.0)`, `pza1.Sleep()`.

- [ ] **Step 1: Failing tests.** `test_pza_schema.py`: `test_a_square_array_at_the_prior_arity_decodes_with_the_edges_none` (a `map` line whose square arrays have 12 fields → `decode` gives `blockN is None`), `test_sleep_and_max_weight_reach_tools_json`; `test_pza1.py`: `Interact(1, 2, "loot", "food").args() == {..., "maxWeight": 0.0}`, `Sleep().TYPE == "sleep"` with `args() == {}`, `"not safe" in REASONS`.
- [ ] **Step 2: Run**; FAIL.
- [ ] **Step 3: The schema and the generator.** Edit `pza1.json` as the interface says. Check whether `load()`/`_dec` honour `x-prior` on a record: if `decode` refuses the 12-field square, extend the generator so a record's `x-prior` works as a group's does (the same rule: an arity from the prior up to the full order, trailing fields None; shorter or longer refused) and render the Python module's `PRIOR` table for records too. `python tools/pza_schema.py --write`; `--check` in sync; `PZA.VERSION = "1.2"`.
- [ ] **Step 4: The goldens.** `python -m pytest testing/tests/pzagent/test_replay.py -q` fails on the hash of nothing (the logs are 1.1 and decode under the tolerance) — if any golden changes, stop and name why in the report; the expected outcome is **no golden change** (no live log has the new fields). The fake mod's frames gain `hour`; every test asserting a square's keys gains the four edges.
- [ ] **Step 5: Green**; the folder; `tools/tests/test_pza_schema.py`; the full pytest saved.
- [ ] **Step 6: Commit** `Plan 23 Task 4: PZA/1.2 — the square's blockN, blockW, wallN, wallW, me.hour, the sleep action and interact's maxWeight; the generator's prior arity on a record`.

---

### Task 5: The Link's poll every third tick (P23-4)

**Files:**
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Link.lua` (`L.POLL_EVERY = 3`; `L.poll(tick)` returns nil without opening the file unless `tick % L.POLL_EVERY == 0`; the header's line on the poll), `PZAgent_Main.lua` (`L.poll(PZA.tick)`; the header's "the poll every tick" → "the poll every third tick (L.POLL_EVERY)")
- Test: `testing/tests/pzagent/test_lua_link.py`, `test_lua_main.py`

- [ ] **Step 1: Failing tests.** `test_the_poll_opens_cmd_txt_on_every_third_tick_only` (the fake FS's `opens` count over 30 ticks with a command waiting is 10, and the command is accepted on the first tick divisible by 3); `test_a_command_written_between_polls_is_read_at_the_next_poll_tick` (written at tick 4, its act line at tick 6); `test_main_passes_the_tick_to_the_poll`.
- [ ] **Step 2: Run**; FAIL. **Step 3:** The edit. Lints. **Step 4:** Green; the folder saved. **Step 5: Commit** `Plan 23 Task 5: the Link polls cmd.txt every third tick (L.POLL_EVERY = 3, P23-4)`.

---

### Task 6: The map's edges in the scan and the watch

**Files:**
- Modify: `PZAgent_Map.lua` (`MP.square` reads the four edges: `local okN, nsq = PZA.call(cell, "getGridSquare", x, y - 1, z)` and `wsq` at `x - 1`; `getm(missing, q, "blockN", sq, "isBlockedTo", nsq)` when `nsq ~= nil` else `q.blockN = true`… — no: an absent neighbour square is unloaded, not blocked: `q.blockN = nil` and `PZA.missing(missing, "neighbourN")`; likewise `wallN` through `isWallTo`; `MP.fingerprint` appends the four reads as `"e" .. tostring(bn) .. tostring(bw) .. tostring(wn) .. tostring(ww)`; the header's paragraph on the fingerprint and the square record), the cell passed into `MP.square(sq, missing, cell)` by both callers
- Test: `test_lua_map.py`

- [ ] **Step 1: Failing tests.** `test_square_reads_its_north_and_west_edges_off_the_neighbour_squares` (a fake cell with `(11,20)`, `(11,19)` and `(10,20)`; `isBlockedTo` answers true for the north neighbour only, `isWallTo` true for the west only → `blockN True, blockW False, wallN False, wallW True`); `test_an_absent_neighbour_leaves_the_edge_nil_and_names_it_missing`; `test_a_door_closing_changes_the_fingerprint_through_its_edge` (the north `isBlockedTo` flips → the watch queues one delta); `test_map_square_has_exactly_the_schemas_square_keys` updated.
- [ ] **Steps 2–5** as Task 5's. **Commit** `Plan 23 Task 6: the square's four edges read off isBlockedTo and isWallTo to its north and west neighbours, in the scan and the watch's fingerprint`.

---

### Task 7: `interact loot`'s weight cap and `me.hour`

**Files:**
- Modify: `PZAgent_SkillsWorld.lua` (`K.types.interact.check` reads `args.maxWeight` (a number ≥ 0, else `bad args`; absent → 0) into `st.maxWeight`; `lootPicks(st, p)` takes the picks in container order while `cap == 0 or weight + itemWeight <= cap`, `weight` the inventory's `getCapacityWeight` read once before the loop plus each queued item's `getWeight`; a pick skipped for weight counts in `st.skippedWeight`, carried in the result as `skipped`), `pza1.json` (`result_interact` gains `skipped` integer: "Items left for the weight cap."; `--write`), `PZAgent_Sense.lua` (`me.hour` from `getGameTime():getTimeOfDay()` through `PZA.call`, nil when unreadable), `conftest.py`'s `make_player` (a `getTimeOfDay` on the fake game time)
- Test: `test_lua_skills.py`, `test_lua_sense.py`

- [ ] **Step 1: Failing tests.** `test_interact_loot_stops_before_the_weight_cap_and_reports_skipped` (three items of weight 1.0, the inventory at 7.0, `maxWeight 8.5` → one queued, `moved 1`, `skipped 2`); `test_a_max_weight_of_zero_loots_everything`; `test_a_negative_max_weight_is_bad_args`; `test_the_frame_carries_the_hour`.
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 7: interact loot stops before maxWeight and reports the items skipped; me.hour from getTimeOfDay`.

---

### Task 8: The `sleep` skill (P23-E)

**Files:**
- Modify: `PZAgent_SkillsWorld.lua` (append `K.types.sleep` after `drop`): `check(args, p)`: `getStats` → `getNumVisibleZombies`, `getNumChasingZombies`, `getNumVeryCloseZombies` any above 0 → `rejected not safe`; `getMoodles():getMoodleLevel(MoodleType.PAIN) >= 2` with fatigue `<= 0.85`, or `PANIC >= 1` → `not valid`; `isClient()` true and `getServerOptions():getBoolean("SleepAllowed")` false → `not allowed`; else `st = {fatigue0, worldAge0, queuedAt = nil}`. `tick(p, st)`: on the first tick, `K.clearQueue(p)`, the hours as vanilla computes them (`ZombRand(f*10, f*13) + 1`, the bed quality through `ISWorldObjectContextMenu.getBedQuality(p, nil)` index-checked, "floor" when absent, ×0.7 for the floor, the trait reads through `hasTrait` with `CharacterTrait.INSOMNIAC`, `NEEDS_LESS_SLEEP`, `NEEDS_MORE_SLEEP` index-checked, clamped 3..16), `sleepHours = hours + getTimeOfDay()` mod 24; `setBed(nil)`, `setBedType(bedType)`, `setForceWakeUpTime(sleepHours)`, `setAsleepTime(0)`, `setAsleep(true)` each through `PZA.call`; `UIManager.setFadeBeforeUI` and `FadeOut` index-checked and under pcall (a `-debug` client's UI); `st.queuedAt = now`, `st.bedType`. Later ticks: `isAsleep` reads false → `done {sleptH = worldAge - worldAge0, fatigueBefore, fatigueAfter, bedType}`; `PZA.now() - queuedAt > K.SLEEP_MS` (3 600 000: an hour of wall) → `failed interrupted`; `isDead` → `failed dead`. The header's paragraph names vanilla's handler and lines (P23-E).
- Modify: `conftest.py`'s `make_player` (`getStats` gains the three zombie counts, `hasTrait`, `setBed`, `setBedType`, `setForceWakeUpTime`, `setAsleepTime`, `setAsleep` recording into `p.sleep`; `isAsleep` reads `p.asleep["v"]`), `test_lua_faults.py`'s `VALID` (`"sleep": ("sleep", {})`) and `VANILLA` (`ISWorldObjectContextMenu`, `UIManager`)
- Test: `test_lua_skills.py`

- [ ] **Step 1: Failing tests.** `test_sleep_with_a_zombie_visible_is_rejected_not_safe`; `test_sleep_under_pain_or_panic_is_not_valid`; `test_sleep_sets_the_wake_time_the_bed_type_and_asleep_then_is_done_when_awake` (fatigue 0.7 → hours in 3..16 before the clock; `p.sleep` records the five setters in order; `isAsleep` flipped false after the fake world age advanced 8 h → `done` with `sleptH 8` and `bedType "floor"`); `test_sleep_not_allowed_on_a_client_whose_server_forbids_it`; `test_sleep_times_out_interrupted`; the faults file's (a), (b), (d) cases over `sleep`.
- [ ] **Steps 2–5**; `test_every_emitted_reason_and_type_is_in_the_schema` still green. **Commit** `Plan 23 Task 8: the sleep skill, vanilla's onSleepWalkToComplete sequence through PZA.call (P23-E)`.

---

### Task 9: `World` — edges, the line, interiors, the inventory by use, empties

**Files:**
- Modify: `testing/agent/base/world.py`
- Create: `testing/agent/base/items.py` (the dataset index: `FOOD_IDS`, `DRINK_IDS` (items of `kind == "fluid_container"`), `WEAPON_IDS` (the dataset has none: `WEAPON_IDS` is the weapon items of `data/food-items.json`'s `items` with `item_type` starting `base:weapon` if present, else `policies.WEAPON_RX` stays the weapon rule), `use_of(full_type) -> "food" | "water" | "weapon" | "bandage" | "other"`, loaded once from `data/food-items.json` at import with `functools.lru_cache`)
- Test: `testing/tests/pzagent/test_base_world.py`, `test_items.py`

**Interfaces:**
- Produces: `World.blocked(a, b)` (two adjacent `(x, y, z)`; the edge between them off the kept map: for `b` north of `a` the square `a`'s `blockN`, south `b`'s `blockN`, west `a`'s `blockW`, east `b`'s `blockW`; a diagonal step is blocked when either orthogonal path's two edges are both blocked, or either corner square is solid; an unknown square or `None` edge counts blocked); `World.line_clear(a, b)`: Bresenham over the squares between the two positions (floats floored), false at any `solid` square or any `wallN`/`wallW` the line crosses (the wall of the square entered from the south or the east); `World.reachable_adjacent(target_xy, z)`: the 8 neighbours of the target's square, not solid, with `blocked(neighbour, target)` false, nearest the player first; `World.interiors()`: the `(x, y, z)` squares with `room` not None, grouped `{building: [squares]}`; `World.doors_of(building)`: the squares of that building with a `door`; `World.by_use()`: `{"food": [ids], "water": [ids], "weapon": [ids], "bandage": [ids], "other": [ids]}` from the inventory through `items.use_of`, `empty_ids` excluded from `water`; `World.mark_empty(item_id)`; `nearest_unlooted(want)` keyed on `items.use_of` of the container's items, `FOOD_RX`/`WATER_RX` removed from `world.py` (every import updated: `survive.py`, `policies.py`). `to_json` carries `emptyIds` sorted.

- [ ] **Step 1: Failing tests.** `blocked` on a wall edge both ways; a diagonal through a corner; `line_clear` across a `wallW` on the square entered and not across an open edge; `reachable_adjacent` leaves out the blocked side of a door square; `interiors` and `doors_of`; `by_use` with `Base.WaterBottleFull` (water), `Base.CannedBeans` (food), `Base.Bowl` (other: the bowl is a `fluid_container` in the dataset? assert whichever the dataset says, by reading it in the test, never by a literal), `mark_empty` moves an id out of `water`; `test_items.py`: `use_of("Base.Carrots") == "food"`, the four Plan 22 misses (`CannedMilk`, `TinnedSoup`, `Macandcheese`, `PowerBar`) are food, `use_of("Base.Hammer") != "food"`.
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 9: World's edges, line of sight, interiors, the inventory by the dataset's use and the empties (P23-D)`.

---

### Task 10: The threat instinct — a pinned target, the line, a reposition, the flee on wounds, the load drop

**Files:**
- Modify: `testing/agent/base/planner/policies.py` (`Fight`: `target` pinned at the first choose and kept until dead, unreachable, or beyond `DISENGAGE_R`; `choose`: `line_clear(me, target)` false → one `WalkTo` of the nearest `reachable_adjacent` square from which the line is clear (`repositioned = True`), a second blocked read marks the target unreachable; `Flee` unchanged), `survive.py` (`_flee_reason`: `pair` when `n >= 2` and (`health < FLEE_HEALTH_PAIR` or the body's `bleeding + scratched + bitten > 0`); before a flee at load level ≥ `DROP_AT`, one `Drop` of `LootHouse.spare()` (the `flee_drop` reason logged), then the flee)
- Test: `test_policies.py`, `test_survive.py`

- [ ] **Step 1: Failing tests.** A Fight keeps its target when a nearer zombie appears mid-fight; a target behind a `wallN` edge gets one reposition walk to the clear neighbour then an attack; a target with no clear neighbour is marked unreachable and Survive flees `unreachable`; two zombies within 6 at health 90 with `bleeding 1` → flee `pair`; a flee at load level 3 sends one `Drop` first (reason `flee_drop`) and the flee on the next tick.
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 10: the Fight pins its target, checks the line and repositions once; the pair rule reads wounds; a flee drops a heavy load first (P23-6)`.

---

### Task 11: The need and load instincts — the first moodle, the dataset's picks, the loot budget

**Files:**
- Modify: `survive.py` (`THIRST_T = 0.12`, `HUNGER_T = 0.15` with the rows cited in the comment; `_need` picks water from `world.by_use()["water"]` by least id, food from `["food"]` by least id; a `Consume` that ended `failed not valid` on a water id → `world.mark_empty(id)` in `_note_failures`), `policies.py` (`LootHouse`: `LOAD_RATIO_MAX = 1.0`; `choose` sends `Interact(x, y, "loot", want, maxWeight=max_weight)` with `max_weight = load.max * LOAD_RATIO_MAX` read off the frame, `want` never `all` (`"food"`, `"water"`, `"weapon"`, `"bandage"` in that order of the stock's wants: the branch's caller sets it); the level guard stays as the backstop), `__all__` and docstrings
- Test: `test_survive.py`, `test_policies.py`

- [ ] **Step 1: Failing tests.** Thirst 0.13 → `Consume` of the least water id; thirst 0.11 → nothing; a `failed not valid` consume marks the id empty and the next tick picks the other bottle; the loot carries `maxWeight 8.0` at `max 8` level 0; `all` is never sent (a test over 20 ticks of a looting World asserts every interact's filter in the four uses).
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 11: needs at the first moodle off the dataset's uses; the loot capped at the carry ratio (P23-7, P23-8)`.

---

### Task 12: The night instinct — shelter and sleep (P23-9)

**Files:**
- Create: `testing/agent/base/planner/night.py` (`class Night(Policy)`: `TIRED_T = 0.6`, `LATE_HOUR = 22.0`, `LATE_FATIGUE = 0.3`; `wants(world)`: fatigue > `TIRED_T`, or hour ≥ `LATE_HOUR` and fatigue > `LATE_FATIGUE`; `choose`: with a zombie within `DANGER_R` → None (the threat branch owns it); not inside (`world.me`'s square has no `room`) → the nearest interior square of a building with a known door: step 1 `WalkTo` the door's reachable adjacent square, step 2 `Interact(open)` if the door reads closed, step 3 `WalkTo` the interior square, step 4 `Interact(close)` on the door; inside → `Sleep()`; a step that fails marks that building `shunned` for `SHUN_MIN` 120 game minutes and the next building is tried; no known interior → `want_shelter = True` (the goal layer's `Shelter` reads it) and None)
- Modify: `survive.py` (`BRANCHES = ("threat", "need", "load", "night", "goal")` — `load` is the drop guard split out of forage, `goal` is Task 13's; until Task 13 lands, `forage` and `explore` stay after `night`), tests
- Test: `testing/tests/pzagent/test_night.py`

- [ ] **Step 1: Failing tests.** Fatigue 0.65 outside, a building with a closed door known → the four steps in order over ticks (the fake acts answering done), then `Sleep`; a zombie within 6 → no night command; hour 23 fatigue 0.35 → wants; hour 23 fatigue 0.2 → not; a failed open shuns the building and the next is tried; no interior known → `want_shelter True`.
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 12: the night instinct, shelter in a known interior then sleep (P23-9)`.

---

### Task 13: The goal layer — types, the view, the scripted source, the runner (P23-10, P23-B)

**Files:**
- Create: `testing/agent/base/schema/goals.json` (JSON Schema, `oneOf` over `ExploreToward {x: integer, y: integer}`, `LootBuilding {building: integer}`, `Shelter {building: integer}`, `Stock {kind: "water"|"food"}`, `Rest {seconds: number ≤ 120}`, each with a one-line `description`), `testing/agent/base/planner/goals.py` (`@dataclass` per type with `step(world, actions, clock) -> Command | None`, `state` ("running" | "done" | "failed" | "superseded"), `reason`, `started_wall`; `GOAL_MAX_S = 90.0`; `ExploreToward` = scan the place then walk (Explore's logic aimed at a point), `LootBuilding` = `LootHouse` over `world.containers` of that building's squares, `Shelter` = Night's four steps for a named building, `Stock(kind)` = `LootHouse` with `want = kind` over the nearest unlooted containers holding that use, `Rest` = nothing sent for its seconds (the frame keeps coming); `class GoalSource(Protocol)`: `propose(view: dict) -> Goal`; `class ScriptedSource`: `Stock` when `view["needs_wanted"]`, `Shelter` when `view["want_shelter"]` and a building with a door is known, `LootBuilding` for the nearest building with an unlooted container, else `ExploreToward` the unexplored edge, else `Rest(30)`; `validate(obj) -> Goal` against `goals.json` with a stdlib walk (type, enum, required, additionalProperties), raising `ValueError`; `class GoalRunner`: `tick(world, actions)` holds the current goal while it runs, proposes a new one from its source when none runs or `GOAL_MAX_S` passed, marks the running one `superseded` when `actions.current` is not its own), `testing/agent/base/planner/view.py` (`view(world, runner) -> dict`: `pos {x, y, z}`, `hour`, `health`, `needs {hunger, thirst, fatigue}`, `needs_wanted` (list), `load {weight, max, level}`, `weapon`, `inventory_by_use` (counts), `buildings` (each `{id, dist, containers, looted, doors, visited}`), `zombies_near` (counts within 6, 12, 25), `last_goal {type, args, state, reason}`, `events` (the last three kinds), `want_shelter`; `render(view) -> str` under 2 KB, asserted)
- Modify: `survive.py` (the `goal` branch: `self.goals = GoalRunner(source)`; `forage` and `explore` leave, their machines now goals' steps; `Survive(world, actions, log_path, clock, source=None)` with `ScriptedSource()` the default; the decision line gains `goal {type, args, state}`), the Survive tests touching forage/explore
- Test: `testing/tests/pzagent/test_goals.py`, `test_view.py`

- [ ] **Step 1: Failing tests.** Each dataclass's fields equal its `goals.json` entry's properties (P23-B); `validate` accepts each example and refuses an unknown type, a missing field, an extra field, a `Rest` over 120; the scripted source's order on four views; a goal pre-empted by a threat reads `superseded` and the same goal is proposable again; a goal past `GOAL_MAX_S` is replaced; `render` under 2048 bytes on a World with 20 buildings and 50 containers; Survive's branch order and the `goal` line in `decision.log`.
- [ ] **Steps 2–5.** **Commit** `Plan 23 Task 13: the goal layer — goals.json, the five goal types, the view, the scripted source and the runner under the instincts (P23-10, P23-B)`.

---

### Task 14: The LLM source over the `claude` CLI (P23-11)

**Files:**
- Create: `testing/agent/base/planner/llm.py` (`class LLMSource(fallback, cli=("claude", "-p", "--output-format", "json", "--model", "sonnet"), timeout_s=20.0, log_path="goals.log", clock=time.time, runner=subprocess.run)`: `propose(view)` starts one worker thread per call when none is pending (the prompt = `SYSTEM` (the goal types and their JSON shape, rendered from `goals.json`'s descriptions; "answer with one JSON object and nothing else") + `view.render`), returns the fallback's goal at once while the call is pending or on its failure, and the parsed goal on the next `propose` after the call returned within `timeout_s`; the CLI's stdout parsed as the CLI's JSON envelope (`{"result": "<text>", ...}`), the text's first `{...}` parsed and `validate`d; `calls` (a list of `{wall, latency_s, ok, goal, error, prompt_bytes}`) and each appended to `goals.log` as one JSON line; the view holds game state only (the test asserts the prompt bytes carry no key outside `view`'s))
- Test: `testing/tests/pzagent/test_llm.py` (a fake `runner` returning canned CLI envelopes: a good goal → applied on the next propose; malformed → fallback and `error`; a runner sleeping past `timeout_s` on a fake clock → fallback and `error "timeout"`; a non-zero return → fallback; the prompt's bytes equal `SYSTEM + render(view)`)

- [ ] **Steps 1–5.** **Commit** `Plan 23 Task 14: the LLM goal source over the claude CLI, threaded, validated, the scripted source standing in (P23-11)`.

---

### Task 15: The grades `gates_e.py`, `gates_f.py` and their scripts

**Files:**
- Create: `testing/agent/base/gates_e.py` (`grade_e1(out, prev=None) -> dict`: `survived` (the stop in `("day_cap", "budget")`), `game_minutes`, `needs {drink: {sent, done, stat_fell}, eat: {...}, sleep: {sent, done, sleptH, fatigue_fell}}` off `loop.actions` and the frames around each `done`, `fights {n, ended, fled, stand_offs}` off `loop.fights` (a stand-off: a fight whose `fight_ticks > 20` with the target's health unchanged in the kept frames), `load {max_ratio, guard_drops, flee_drops}`, `lineage` (`chain.lineage_diff(prev, first_frame)` when `prev`), `cost {p50, p99, max, over5}`, `death` (`gates.death_check` reused as a function on a window opened at the first frame whose `body.bleeding + scratched + bitten` rose, `first_wound_seq`), `report_lines`; `gate_e1(outs) -> {verdict, gates}` over a chain's artifacts in order: `alive_through` (24 game hours summed, no death), `drink_done ≥ 1`, `eat_done ≥ 1`, `sleep_done ≥ 1`, `death_explained` when a death, each `{ok, value, threshold}`), `testing/agent/base/gates_f.py` (`grade_f1(out)`: `grade_e1` plus `llm {calls, ok, fallbacks, latency_p50, latency_p99, goals_by_type, goal_ends}` off `loop.goals` (Task 16's record)), `testing/agent/drivers/e_grade.py` (`python e_grade.py <artifact> [<prev artifact>]`), `f_grade.py`
- Test: `testing/tests/pzagent/test_gates_e.py`, `test_gates_f.py` (every gate with a passing and a failing artifact built from `DEFAULT_FRAME`)

- [ ] **Steps 1–5.** **Commit** `Plan 23 Task 15: grade_e1 and gate_e1 over a chain, grade_f1 over an LLM session, and their scripts`.

---

### Task 16: The four drivers

**Files:**
- Create: `testing/agent/drivers/x4_link_3.py` (x4_link_2.py copied: `KEY = "x4_link_3"`, `DRIVER`, `ARTIFACT`, the docstring's first paragraph naming the paced poll (P23-4) and the edges (Task 6) by commit hash, `preboot`'s dirty check on its own file; the rest byte-identical, `gate_x4`), `testing/agent/drivers/x5_combat_2.py` (x5_combat.py copied with its constants; the Fight pinned to the spawned zombie's id (the driver passes `target=` into `Fight`, a new keyword Task 10 added) and `zombie.get` read through `driverlib.polls.PollThread`; the spawn frames' `me.zombiesSeen`/`zombiesListed` recorded per encounter (S-22)), `testing/agent/drivers/e_day.py` (the library's `Session` with `Survive(source=ScriptedSource())`; `parse_argv(allowed=("--session", "--fixture"))`: `--session N` (int ≥ 1) and `--fixture NAME` (the fixture to boot; the profile `agent.toml`'s mods and ini, its `fixture` overridden by the argument — `fx.load(name)` directly, the profile's `fixture` reported beside it); `DAY_CAP_S 840`, `BUDGET_S 1200`; `on_frame`: the first frame kept for `chain.lineage_diff` (the previous artifact's path from `--prev <artifact.json>`, a third allowed argument, optional); `extra_record`: `goals` (every goal with `{type, args, state, reason, startS, endS}` off the runner), `night` (the shelter steps and the sleep's result), `lineage`; `grade_e1` at the end), `testing/agent/drivers/f_goals.py` (e_day's form with `Survive(source=LLMSource(ScriptedSource()))`, `goals.log` copied beside the artifact, `grade_f1`)
- Test: `testing/tests/pzagent/test_x4_link_3.py` (test_x4_link_2.py with the module swapped), `test_x5_combat_2.py`, `test_e_day.py` (the static tests: the refusal, the constants, no frozen import; the loop on a FakeMod: a clean session stops at the day cap, a `--session 2 --prev <a>` session records the lineage diff, a consume done lands in `needs`, the sleep's result in `night`), `test_f_goals.py` (the fake CLI runner injected; `goals` recorded)

- [ ] **Steps 1–5**; each driver's pre-boot checks run offline against the real profile and a real run layout. **Commits** one per driver: `Plan 23 Task 16a: x4_link_3.py, the paced poll's X4 session under gate_x4`; `16b: x5_combat_2.py, the pinned fight with the reads off the poll thread`; `16c: e_day.py, the chain's session driver on the library`; `16d: f_goals.py, the LLM session driver`.

---

### Task 17: X4-3 — the boot (controller) and the write-up (a fresh opus writer)

- [ ] **Boot:** doctor; free memory read and ledgered (≥ 12 GB); `python testing/agent/drivers/x4_link_3.py` launched detached (`Start-Process`), polled in foreground calls through the persisted artifact; the artifact copied to `testing/artifacts/x4_link_3-<stamp>/` with `state.log`; `python testing/agent/drivers/x4_grade.py <artifact>` saved.
- [ ] **Write-up:** `GUIDE.md` (every number with its JSON path), the artifacts row, `do-not-cite.csv` rows, `docs/platform/harness.md#agent` sentences with provisional tags `[T17.n/M/n=1]`, the delta file (the X4-3 rows; Task 3's jar rows now that their owner sentences exist), research-notes threads settled or opened; the controller applies the delta, fills, `cited-by --write`, the full checker 0, the artifact commit then the pages commit.
- [ ] `Task 17: complete` in the ledger.

### Task 18: X5-2 — the boot (controller) and the write-up (opus)

- [ ] As Task 17's form on `x5_combat_2.py` (fixture `agent0`, the spawned zombies), `measure_x5` printed by `x5_grade`'s successor only if one exists — else the grade is `gates.measure_x5` through a one-line call saved; the guide's § on the listing diagnostic (S-22) and the pinned fight.

### Task 19: The chain E1…En — the boots (controller), the snapshots, the write-up (opus)

- [ ] **The chain table** in the ledger before the first boot: `| n | fixture | run id | stop | gameMin | snapshot | ticked |`. For each session: doctor; memory ≥ 12 GB read and ledgered; `python testing/agent/drivers/e_day.py --session <n> --fixture <agent | agent-s<n-1>> [--prev <last artifact>]` detached, polled; at its stop the artifact copied; `python testing/pzt snapshot --from-run testing/runs/<run id> --name agent-s<n> --parent <fixture> --session <n>` (its output ledgered with the size); `e_grade.py <artifact> <prev>` saved; the row ticked. The chain ends at a death (written up as the plan's reading, never re-run), at 24 game hours with a sleep done, or at 9 sessions. A defect found mid-chain is fixed in the library or the base, committed, and the chain continues on `e_day_2.py` (a copy with its constants), the split named in the ledger and both guides; the Lua is not edited mid-chain (a Lua defect ends the chain's reading and is Plan 24's).
- [ ] **Write-up:** one `GUIDE.md` per session artifact plus a chain guide `testing/artifacts/e_day-chain-<date>/GUIDE.md` (the chain's table, `gate_e1` over the artifacts, the lineage diffs, the needs answered with their frames, every fight, the night's reading: did the server fast-forward the sleep, at what rate), rows on `harness.md#agent`, the delta, research-notes.

### Task 20: F1 — the LLM session (controller boot, opus write-up)

- [ ] `f_goals.py --fixture <the chain's last fixture, else agent>` as Task 17's form; `claude --version` saved beside the artifact (the CLI's version in the guide); the guide's § on the calls (count, latency, parsed, fallbacks, each goal and its end) beside the survival reading; rows; the delta.

### Task 21: The report, the evidence layer and the close (writers on disjoint files, then the controller)

- [ ] The report `docs/superpowers/specs/2026-10-28-plan-23-survivor-report.md` (§ 1 what the base is now; § 2 the chain and the lineage; § 3 the instincts' readings; § 4 the night; § 5 the goal layer and F1; § 6 the cost (X4-3); § 7 the walls still standing; § 8 decisions; § 9 recommendation for Plan 24 with the alternatives' downsides); `docs/reference/research-notes.md#agent-link` threads; CLAUDE.md § 1's agent row (the report path added), § 3's baseline updated to the close's count; HISTORY.md's Plan 23 entry; the memory files (§ 8).
- [ ] The whole-pass review (opus), one consolidated fix wave, its re-review; § 3's gates; the full pytest saved and read; the push; `Plan 23: CLOSED`.

## Self-review against the spec

- § 4 the chain → Tasks 1, 2 (`chain.py`), 16c, 19. § 5 PZA/1.2 → Task 4; the poll → Task 5; `x4_link_3` → Tasks 16a, 17. § 6 edges → Tasks 6, 9, 10. § 7 threat → 10; need → 11; load → 7, 11; night → 8, 12. § 8 goals → 13; LLM → 14, 16d, 20. § 9 library → 2; polls → 2, 16; grades → 15. § 10 sessions → 17–20. § 13's open items are the guides' to settle or carry.
- Types: `Interact(x, y, kind, filter="all", maxWeight=0.0)` (Task 4) is what `LootHouse.choose` sends (Task 11); `Fight(world, actions, clock, unreachable=None, target=None)` (Task 10) is what `x5_combat_2.py` pins (Task 16b); `Survive(world, actions, log_path, clock, source=None)` (Task 13) is what `e_day.py` and `f_goals.py` build (Task 16); `Session(xs, transport, planner_factory, …, polls=None)` (Task 2) is what both drivers subclass; `grade_e1(out, prev)` (Task 15) is what `e_day.py` calls and `e_grade.py` prints; `chain.lineage_diff(prev_artifact, first_frame)` (Task 2) is what `grade_e1` and `e_day.py` call; `World.by_use()`, `mark_empty`, `empty_ids` (Task 9) are what Task 11's need reads; `World.line_clear`, `reachable_adjacent` (Task 9) are what Task 10's Fight reads; `Night.want_shelter` (Task 12) is what `view()` carries (Task 13).
- No placeholder: every task names its files, tests and commit; the research task's output is a note with findings and commands, not a TODO.
