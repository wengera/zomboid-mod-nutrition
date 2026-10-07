"""x241-smoke -- Plan 10c Task H0 Step 4 (live): the smoke run of the harness's frame-time instrument and synthetic
ghost load (harness ed4ac93 + f06d2e6: tick.ring, perf.local, ghost.load / ghost.stats / ghost.stop and the opt-in
gc log), on the STAGED copy of the tree at 9578eb9 (release/hitch-9578eb9/NutritionRevamp/Contents/mods/
NutritionRevamp, staged by Task 0, MANIFEST.json sha256 c86e295a...b389; release/ is gitignored; mod/ is never
booted) with NO instrument added. One boot of profile x24-smoke (fixture two, admin -debug then bob release,
Nutrition false, DayLength 1, gclog true). ONE artifact, `smoke.json`, plus the staged MANIFEST.json copied
byte-identical beside it. Shape: x231_perf.py (step, keep, gread, run_phase, grade, make_server + attach_clients, the
echo-excluding log greps, the artifact copied by the driver). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENT (the harness, server side; its comment block in PZTestKit_Server.lua is the contract):
  tick.ring <n> / read <tag>   every server frame stamped at OnTickEvenPaused and at OnTick (getTimestampMs, 1 ms):
        busy (start -> OnTick), period (start -> next start), endPeriod (OnTick -> next OnTick), the minute flag, the
        ghost runs and ghost ms in the frame; `read` replies p50/p99/max and writes tick-ring-<tag>.json.
  perf.local <n> / read <tag> / now   getPerformanceLocal()'s per-window min/max/avg update period and the current
        period (`fps`), sampled once per engine window (a change in any of the four or memory-used), each sample
        tagged with the ring's frame number; `read` writes perf-local-<tag>.json.
  ghost.load <N> burst / ghost.stats / ghost.stop   N - 2 ghost records (deep copies of admin's and bob's store
        records, harness-held), each run through NutritionRevamp.server.minute.run against its real carrier on every
        EveryOneMinute, the mirror send suppressed; ghost.stats counts runs, starvation, staleness, runs per frame,
        the suppressed sends and the store-leak guard.
  gclog   -Xlog:gc* to <run>/gc.log (the profile's [server] gclog = true).

PHASES (order S0, I, B, Z):
  S0  the ready marks, the verify rows, players, time, perf.local now; wait (cap S0_WAIT_S) until both real players
      have a store record (lua.global ...store.records.<u>) and the mod's minute has run at least MIN_RUNS times.
  I   idle: MIN.stats and players counters; tick.ring RING_N, perf.local PERF_N; IDLE_S wall seconds with NO bus
      traffic; tick.ring read idle, perf.local read idle; the two result documents waited for and kept whole.
  B   the N = 20 burst: ghost.load GHOST_N burst, then tick.ring RING_N and perf.local PERF_N (armed after the load, so
      every ring frame has the ghosts loaded); BURST_S wall seconds with no bus traffic; ghost.stats, tick.ring read
      burst, perf.local read burst, ghost.stop; the result documents kept whole; MIN.stats after.
  Z   the mod-error check (server errors naming the mod's files; admin's lua_error marker).
  After teardown: the server log is grepped (echo lines dropped first, CLAUDE.md s5) and gc.log is summarised.

DEVIATION FROM THE PLAN'S STEP 4: the plan reads the burst "for 3 game minutes". At DayLength 1 a game minute is
0.625 s, so 3 game minutes is about 1.9 s of wall and 3 minute frames, below what a p99 can be read from (and inside
one 2 s bus poll). The burst arm therefore runs BURST_S = 120 s of wall (about 190 game minutes, the same wall as the
idle arm), and the first 3 minute frames are reported separately from the frame list (B.first3).

ANALYSIS (in grade_all, off the artifact's own rows):
  X0  per engine window: sample k (seen at ring frame f_k) covers the ring frames f_{k-1} .. f_k - 1; the window's
      Lua max is the largest endPeriod over those frames. A window whose frame count exceeds 1.5 x the median is a
      merged window (two engine windows read identically) and is left out. Agreement: |p99(engine window max) -
      p99(Lua window max)| <= 2 ms (review-platform X0); the per-window |difference| p50/p99/max is reported beside.
  B   the minute frames' busy (the burst frames) against 20 x 1.583 ms = 31.66 ms (#3387, the plan's figure) and
      18 x 1.583 = 28.494 ms (the ghosts alone: the real players stay on the mod's own one-a-tick drain, not in the
      burst frame); the ghost ms per minute frame; the first 3 minute frames.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  I    idle: ring busy p99 <= 5 ms and max <= 20 ms; period p50 within 99..101 ms; no period over 110 ms is not
       predicted (reported). Falsifier: busy outside the bounds, or period p50 outside the band.
  X0i  idle: the engine's window max and the ring's window max agree within 2 ms at p99. Falsifier: > 2 ms.
  X0b  burst: the same agreement under the burst. Falsifier: > 2 ms.
  B    the burst minute frames' busy p50 lies within 0.5x..2x of 28.494 ms (14.247..56.988 ms). Falsifier: outside.
  S    ghosts do not starve under the burst: starvedEvents 0, neverRun 0, failures 0, storeGhostKeys 0, and the mod's
       MIN.stats.failures does not rise across B. Falsifier: any of them.
  G    gclog: gc.log exists in the run dir with at least one line. Falsifier: absent or empty.
  Z    no mod error line; admin not parked.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, make_server,  # noqa: E402
                         teardown, verify)

PROFILE = "x24-smoke"
PREFIX = "x241"
SESSION = ("Plan 10c Task H0 Step 4: the smoke run of tick.ring, perf.local, ghost.load and the gc log -- 120 s idle, "
           "then 120 s of the N = 20 ghost burst -- on the staged copy at 9578eb9 with no instrument; one boot of "
           + PROFILE)
ARTIFACT = "smoke.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/hitch-9578eb9/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_AT = "9578eb9"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
NR = "NutritionRevamp"
S0_WAIT_S = 90.0
MIN_RUNS = 4
RING_N = 3000
PERF_N = 1000
IDLE_S = 120
BURST_S = 120
GHOST_N = 20
SCHED = "burst"
RUN_MS = 1.583                      # #3387: one player's in-play minute, ms
PLAN_BURST_MS = 20 * RUN_MS         # the plan's comparison, 31.66 ms
GHOST_BURST_MS = (GHOST_N - 2) * RUN_MS
B_BAND = (0.5, 2.0)
IDLE_BUSY_P99_MAX = 5
IDLE_BUSY_MAX = 20
IDLE_PERIOD_BAND = (99, 101)
X0_MS = 2.0
MERGED_FACTOR = 1.5
RESULT_WAIT_S = 30.0
POLL_S = 0.5
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|fast: |options: |effects: .* failed")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
GC_PAUSE_RX = re.compile(r"Pause[^\n]*?(\d+(?:\.\d+)?)ms")
GC_STALL_RX = re.compile(r"Allocation Stall", re.I)

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


PRED = {
    "I": {"busy p99 ms": f"<= {IDLE_BUSY_P99_MAX}", "busy max ms": f"<= {IDLE_BUSY_MAX}",
          "period p50 ms": list(IDLE_PERIOD_BAND)},
    "X0i": {"|p99 engine window max - p99 ring window max| ms": f"<= {X0_MS}"},
    "X0b": {"|p99 engine window max - p99 ring window max| ms": f"<= {X0_MS}"},
    "B": {"burst minute-frame busy p50 ms": [round(B_BAND[0] * GHOST_BURST_MS, 3), round(B_BAND[1] * GHOST_BURST_MS, 3)]},
    "S": {"starvedEvents": 0, "neverRun": 0, "failures": 0, "storeGhostKeys": 0, "MIN.stats.failures rise": 0},
    "G": {"gc.log": "exists with at least one line"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                "clients": {u: {"debug": (rec_fx.get("clients") or {}).get(u, {}).get("debug")}
                            for u in (rec_fx.get("clients") or {})}},
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"staged_mod": STAGE_MOD, "staged_at": STAGED_AT, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/hitch-9578eb9",
             "instrument_note": "No instrument is added to the staged copy; every instrument is the harness's own "
                                "(tick.ring, perf.local, ghost.*), whose file's sha256 is harness_server_sha256.",
             "ghost_note": "Every ghost reading is cost, not behaviour: a ghost runs the real pipeline against a real "
                           "IsoPlayer (admin or bob), so its Java writes land on that player. No behaviour row rests "
                           "on this session.",
             "timer_note": "getTimestampMs is 1 ms resolution: a frame's busy and period are whole milliseconds; the "
                           "engine's update period is measured by the engine (System.currentTimeMillis, also 1 ms)."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The burst arm runs BURST_S = 120 s of wall (about 190 game minutes at DayLength 1) instead of the plan's 3 "
        "game minutes (1.9 s, 3 minute frames, inside one bus poll); the first 3 minute frames are reported apart.",
        "The ring and perf.local for the burst arm are armed after ghost.load replies, so every ring frame of that arm "
        "has the ghosts loaded; the load's own frame is outside the ring.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "summaries": {},
}
try:
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
except OSError as e:
    out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"


def grep_noecho(log, rx, limit):
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:600])
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return hits, skipped


def note(msg):
    out["notes"].append({"wall": wall(), "phase": cur_phase["name"], "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def node(side):
    return resolve_side(side, server, clients)


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    try:
        n = node(side)
        v = ask(n, cmd, args, timeout=timeout)
    except Exception as e:                     # noqa: BLE001 - an unknown side is a recorded fault
        v = {"error": f"{type(e).__name__}: {e}"}
    t_after = wall()
    row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    out["steps"].append(row)
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["side"] = a.get("side", r["side"])
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def gread(side, name, tag):
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "side": side, "wall": r["wall_before"], "wall_after": r["wall_after"],
           "resolved": a.get("resolved"), "type": a.get("type")}
    for k in ("value", "keyCount", "failedAt", "stoppedOn", "error"):
        if k in a:
            row[k] = a.get(k)
    if not isinstance(r.get("ack"), dict):
        row["raw"] = r.get("ack")
    return row


def val(row):
    if not isinstance(row, dict) or not row.get("resolved"):
        return None
    return row.get("value")


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def who(side):
    return side.split(":", 1)[1] if side.startswith("client:") else side


def parked():
    c = clients.get("admin") if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def minstats(tag):
    d = {k: num(val(gread(SRV, f"{NR}.server.minute.stats.{k}", f"{tag}_min_{k}"))) for k in ("runs", "failures")}
    for k in ("minutes", "drained"):
        d[f"players_{k}"] = num(val(gread(SRV, f"{NR}.server.players.{k}", f"{tag}_p_{k}")))
    for k in ("pushes", "deferred", "failed", "marks"):
        d[f"bus_{k}"] = num(val(gread(SRV, f"{NR}.server.bus.effects.stats.{k}", f"{tag}_bus_{k}")))
    return d


def wait_doc(name, after):
    try:
        return server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
    except Exception as e:                     # noqa: BLE001 - a missing document is a recorded fault
        note(f"result {name}: {type(e).__name__}: {e}")
        return None


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = keep(step("S0_time", SRV, "time.snapshot"))
    P["perf_now"] = keep(step("S0_perf_now", SRV, "perf.local", "now"))
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}
    end = time.time() + S0_WAIT_S
    polls = []
    while True:
        recs = {u: gread(SRV, f"{NR}.server.store.records.{u}", f"S0_rec_{u}") for u in USERS}
        runs = num(val(gread(SRV, f"{NR}.server.minute.stats.runs", "S0_runs")))
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end:
            break
        time.sleep(POLL_S)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")


def phase_I():
    P = out["phases"]["I"] = {}
    P["min_before"] = minstats("I_before")
    P["ring_arm"] = keep(step("I_ring_arm", SRV, "tick.ring", str(RING_N)))
    P["perf_arm"] = keep(step("I_perf_arm", SRV, "perf.local", str(PERF_N)))
    P["window_start_wall"] = wall()
    time.sleep(IDLE_S)
    P["window_end_wall"] = wall()
    after = time.time() - 1.0
    P["ring_read"] = keep(step("I_ring_read", SRV, "tick.ring", "read idle"))
    P["perf_read"] = keep(step("I_perf_read", SRV, "perf.local", "read idle"))
    P["ring_doc"] = wait_doc("tick-ring-idle", after)
    P["perf_doc"] = wait_doc("perf-local-idle", after)
    P["min_after"] = minstats("I_after")


def phase_B():
    P = out["phases"]["B"] = {}
    P["min_before"] = minstats("B_before")
    P["load"] = keep(step("B_load", SRV, "ghost.load", f"{GHOST_N} {SCHED}"))
    P["ring_arm"] = keep(step("B_ring_arm", SRV, "tick.ring", str(RING_N)))
    P["perf_arm"] = keep(step("B_perf_arm", SRV, "perf.local", str(PERF_N)))
    P["window_start_wall"] = wall()
    time.sleep(BURST_S)
    P["window_end_wall"] = wall()
    after = time.time() - 1.0
    P["stats"] = keep(step("B_stats", SRV, "ghost.stats"))
    P["ring_read"] = keep(step("B_ring_read", SRV, "tick.ring", "read burst"))
    P["perf_read"] = keep(step("B_perf_read", SRV, "perf.local", "read burst"))
    P["stop"] = keep(step("B_stop", SRV, "ghost.stop"))
    P["ring_doc"] = wait_doc("tick-ring-burst", after)
    P["perf_doc"] = wait_doc("perf-local-burst", after)
    P["min_after"] = minstats("B_after")
    P["ring_off"] = keep(step("B_ring_off", SRV, "tick.ring", "off"))


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["players"] = keep(step("Z_players", SRV, "players"))
    errs = [e for e in (server.errors if server is not None else []) if MOD_ERR_RX.search(json.dumps(e, default=str))]
    P["server_mod_error_lines"] = errs[:20]
    P["admin_parked"] = parked()


def body():
    for name, fn in (("S0", phase_S0), ("I", phase_I), ("B", phase_B), ("Z", phase_Z)):
        run_phase(name, fn)
        if parked() and name != "Z":
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return


def read_logs(every):
    L = out["logs"] = {"patterns": {"life": MOD_LIFE_RX.pattern, "log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern},
                       "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        life, life_echo = grep_noecho(server.log_path, MOD_LIFE_RX, LOG_LIMIT)
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        L["server"] = {"life_lines": life, "life_echo_excluded": life_echo, "lines": raw, "echo_lines_excluded": echoed}
    for c in every:
        u = getattr(c, "username", "?")
        lines, ech = grep_noecho(c.console, LOG_RX, 60)
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, run_dir), "lines": lines,
                                               "echo_lines_excluded": ech})


def read_gc():
    p = os.path.join(run_dir, "gc.log")
    G = out["gc"] = {"path": "gc.log (run dir)", "exists": os.path.isfile(p)}
    if not G["exists"]:
        return
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        G["error"] = f"{type(e).__name__}: {e}"
        return
    pauses = [float(m.group(1)) for ln in lines for m in [GC_PAUSE_RX.search(ln)] if m]
    G.update({"bytes": os.path.getsize(p), "lines": len(lines), "head": lines[:12],
              "pause_lines": len(pauses), "pause_max_ms": max(pauses) if pauses else None,
              "pause_sum_ms": sum(pauses) if pauses else None,
              "stall_lines": sum(1 for ln in lines if GC_STALL_RX.search(ln)),
              "pause_samples": [ln for ln in lines if GC_PAUSE_RX.search(ln)][:12]})


# ---------------------------------------------------------------- grading
def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def pct(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = max(1, min(len(s), math.ceil(round(p * len(s), 9))))
    return s[k - 1]


def summ(xs):
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "p50": pct(xs, 0.5), "p99": pct(xs, 0.99), "max": max(xs) if xs else None,
            "min": min(xs) if xs else None, "mean": (sum(xs) / len(xs)) if xs else None}


def frames_of(doc):
    F = (doc or {}).get("frames_list") or {}
    keys = ("frame", "start", "stop", "busy", "period", "endPeriod", "minute", "runs", "ghostMs")
    cols = [F.get(k) or [] for k in keys]
    n = min(len(c) for c in cols) if cols else 0
    return [dict(zip(keys, (c[i] for c in cols))) for i in range(n)]


def x0(ring_doc, perf_doc):
    frames = frames_of(ring_doc)
    S = (perf_doc or {}).get("samples_list") or {}
    sf, smax = S.get("frame") or [], S.get("max") or []
    by = {f["frame"]: f for f in frames}
    wins = []
    for k in range(1, min(len(sf), len(smax))):
        lo, hi = sf[k - 1], sf[k] - 1
        fr = [by[i] for i in range(int(lo), int(hi) + 1) if i in by]
        eps = [f["endPeriod"] for f in fr if f["endPeriod"] is not None and f["endPeriod"] >= 0]
        if len(fr) != (hi - lo + 1) or not eps:
            continue                            # a window not wholly inside the ring
        wins.append({"k": k, "frames": len(fr), "engine_max": smax[k], "ring_max": max(eps)})
    if not wins:
        return {"windows": 0}
    med = sorted(w["frames"] for w in wins)[len(wins) // 2]
    kept = [w for w in wins if w["frames"] <= MERGED_FACTOR * med]
    em, rm = [w["engine_max"] for w in kept], [w["ring_max"] for w in kept]
    diffs = [abs(w["engine_max"] - w["ring_max"]) for w in kept]
    pe, pr = pct(em, 0.99), pct(rm, 0.99)
    return {"windows": len(wins), "kept": len(kept), "merged_dropped": len(wins) - len(kept), "median_frames": med,
            "engine_max": summ(em), "ring_max": summ(rm), "abs_diff": summ(diffs),
            "signed_diff_mean": (sum(w["engine_max"] - w["ring_max"] for w in kept) / len(kept)) if kept else None,
            "p99_gap": (abs(pe - pr) if pe is not None and pr is not None else None),
            "max_gap": abs(max(em) - max(rm)) if em and rm else None,
            "first": kept[:5]}


def grade_all():
    ph = out["phases"]
    S = out["summaries"]
    I = ph.get("I") or {}
    ring_i = I.get("ring_doc")
    if ring_i:
        fr = frames_of(ring_i)
        busy = [f["busy"] for f in fr if f["busy"] is not None and f["busy"] >= 0]
        per = [f["period"] for f in fr if f["period"] is not None and f["period"] >= 0]
        endp = [f["endPeriod"] for f in fr if f["endPeriod"] is not None and f["endPeriod"] >= 0]
        S["I"] = {"frames": len(fr), "busy": summ(busy), "period": summ(per), "endPeriod": summ(endp),
                  "over110": sum(1 for x in per if x > 110), "minute_frames": sum(1 for f in fr if f["minute"] == 1),
                  "minute_busy": summ([f["busy"] for f in fr if f["minute"] == 1 and f["busy"] is not None and f["busy"] >= 0]),
                  "perf": {k: (I.get("perf_read") or {}).get(k) for k in ("samples", "max", "min", "avg", "cur")}}
        b, p = S["I"]["busy"], S["I"]["period"]
        ok = (b["p99"] is not None and b["p99"] <= IDLE_BUSY_P99_MAX and b["max"] <= IDLE_BUSY_MAX
              and p["p50"] is not None and IDLE_PERIOD_BAND[0] <= p["p50"] <= IDLE_PERIOD_BAND[1])
        grade("I", PRED["I"], S["I"], "as_predicted" if ok else "falsified", "busy above the bounds or period p50 off")
        S["X0i"] = x0(ring_i, I.get("perf_doc"))
        gap = S["X0i"].get("p99_gap")
        if gap is None:
            grade("X0i", PRED["X0i"], S["X0i"], "unmeasured", "no aligned window")
        else:
            grade("X0i", PRED["X0i"], S["X0i"], "as_predicted" if gap <= X0_MS else "falsified", "> 2 ms at p99")
    else:
        grade("I", PRED["I"], None, "unmeasured", "no idle ring document")
        grade("X0i", PRED["X0i"], None, "unmeasured", "no idle ring document")

    B = ph.get("B") or {}
    ring_b = B.get("ring_doc")
    if ring_b:
        fr = frames_of(ring_b)
        mins = [f for f in fr if f["minute"] == 1]
        rest = [f for f in fr if f["minute"] != 1]
        S["B"] = {"frames": len(fr), "minute_frames": len(mins),
                  "busy_all": summ([f["busy"] for f in fr if f["busy"] is not None and f["busy"] >= 0]),
                  "busy_minute": summ([f["busy"] for f in mins if f["busy"] is not None and f["busy"] >= 0]),
                  "busy_other": summ([f["busy"] for f in rest if f["busy"] is not None and f["busy"] >= 0]),
                  "ghostMs_minute": summ([f["ghostMs"] for f in mins]),
                  "runs_minute": summ([f["runs"] for f in mins]),
                  "period": summ([f["period"] for f in fr if f["period"] is not None and f["period"] >= 0]),
                  "endPeriod": summ([f["endPeriod"] for f in fr if f["endPeriod"] is not None and f["endPeriod"] >= 0]),
                  "over110": sum(1 for f in fr if f["period"] is not None and f["period"] > 110),
                  "first3": [{k: f[k] for k in ("frame", "busy", "period", "endPeriod", "runs", "ghostMs")} for f in mins[:3]],
                  "plan_burst_ms": PLAN_BURST_MS, "ghost_burst_ms": GHOST_BURST_MS,
                  "perf": {k: (B.get("perf_read") or {}).get(k) for k in ("samples", "max", "min", "avg", "cur")}}
        bm = S["B"]["busy_minute"]
        if bm["p50"] is not None:
            S["B"]["busy_minute_p50_over_plan"] = bm["p50"] / PLAN_BURST_MS
            S["B"]["busy_minute_max_over_plan"] = bm["max"] / PLAN_BURST_MS
            S["B"]["busy_minute_p50_over_ghosts"] = bm["p50"] / GHOST_BURST_MS
            lo, hi = B_BAND[0] * GHOST_BURST_MS, B_BAND[1] * GHOST_BURST_MS
            grade("B", PRED["B"], S["B"], "as_predicted" if lo <= bm["p50"] <= hi else "falsified", "outside the band")
        else:
            grade("B", PRED["B"], S["B"], "unmeasured", "no minute frame in the burst ring")
        S["X0b"] = x0(ring_b, B.get("perf_doc"))
        gap = S["X0b"].get("p99_gap")
        if gap is None:
            grade("X0b", PRED["X0b"], S["X0b"], "unmeasured", "no aligned window")
        else:
            grade("X0b", PRED["X0b"], S["X0b"], "as_predicted" if gap <= X0_MS else "falsified", "> 2 ms at p99")
    else:
        grade("B", PRED["B"], None, "unmeasured", "no burst ring document")
        grade("X0b", PRED["X0b"], None, "unmeasured", "no burst ring document")

    st = B.get("stats") or {}
    if st.get("ok"):
        f0, f1 = g(B, "min_before", "failures"), g(B, "min_after", "failures")
        obs = {k: st.get(k) for k in ("ghosts", "runs", "failures", "lastError", "ms", "usPerRun", "minuteEvents",
                                      "starvedEvents", "starvedMinutes", "maxStaleMinutes", "neverRun",
                                      "maxStaleGameMinutes", "maxRunsPerFrame", "meanRunsPerRunFrame",
                                      "meanRunsPerFrame", "suppressed", "syncs", "storeGhostKeys", "wallSinceLoad",
                                      "gameMinutesSinceLoad")}
        obs["min_failures_before"], obs["min_failures_after"] = f0, f1
        obs["cleared_at_stop"] = g(B, "stop", "cleared")
        ok = (st.get("starvedEvents") == 0 and st.get("neverRun") == 0 and st.get("failures") == 0
              and st.get("storeGhostKeys") == 0 and f0 is not None and f1 == f0)
        S["S"] = obs
        grade("S", PRED["S"], obs, "as_predicted" if ok else "falsified", "a starved ghost, a failure or a store leak")
    else:
        grade("S", PRED["S"], st or None, "unmeasured", "no ghost.stats reply")

    gc = out.get("gc") or {}
    ok = bool(gc.get("exists")) and (gc.get("lines") or 0) > 0
    grade("G", PRED["G"], {k: gc.get(k) for k in ("exists", "bytes", "lines", "pause_lines", "pause_max_ms",
                                                  "stall_lines")}, "as_predicted" if ok else "falsified",
          "gc.log absent or empty")

    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [], "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
lint_errors = lint_paths(prof.sources)
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    print(json.dumps(lint_errors, indent=1))
    sys.exit(1)

try:
    shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
except OSError as e:
    out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
    out["server_cmd_gclog"] = [a for a in (getattr(server, "cmd", None) or []) if a.startswith("-Xlog")]
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_cmd_gclog"] = [a for a in (getattr(server, "cmd", None) or []) if a.startswith("-Xlog")]
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot_info"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                        "client_debug": {u: getattr(c, "debug", None) for u, c in clients.items()}}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             **{u: sorted(set(c.mods_not_found)) for u, c in clients.items()}}
    deployed = {}
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "PZTestKit", "**", "PZTestKit_Server.lua"),
                                 recursive=True)):
        deployed[os.path.relpath(cand, run_dir).replace(os.sep, "/")] = sha256_file(cand)
    out["meta"]["deployed_harness_server_sha256"] = deployed
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    every = list(started)
    try:
        if server is not None:
            teardown(tl, server, [c for c in every if c.alive])
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, every)
        adm = clients.get("admin") if isinstance(clients, dict) else None
        out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
        out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                              for i, c in enumerate(every)]
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        try:
            read_logs(every)
        except Exception as e:                 # noqa: BLE001
            out["logs_error"] = f"{type(e).__name__}: {e}"
        try:
            read_gc()
        except Exception as e:                 # noqa: BLE001
            out["gc_error"] = f"{type(e).__name__}: {e}"
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            if os.path.isfile(os.path.join(run_dir, MANIFEST_NAME)):
                shutil.copyfile(os.path.join(run_dir, MANIFEST_NAME), os.path.join(dest_dir, MANIFEST_NAME))
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
