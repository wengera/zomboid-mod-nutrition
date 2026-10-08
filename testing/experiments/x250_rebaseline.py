"""x250-rebaseline -- Plan 11a Task R Step 8 (live): the 42.21 smoke. The harness self-check, idle frames under
tick.ring and perf.local, and x231's phase A (the slow minute by step in play), on the STAGED copy of the tree at
457f39f (release/rebaseline-x250/NutritionRevamp/Contents/mods/NutritionRevamp, staged by this round's Step 8 with
`python tools/release_pack.py stage mod/NutritionRevamp --out release/rebaseline-x250`; release/ is gitignored; mod/
is never booted) whose server/NR_Server_Bench.lua is overwritten by testing/spikes/instruments/x231_NR_Server_Bench.lua
(x231's P1+P3 instruments, sha256 c20f645d...0d8d, equal to x231's `meta.bench_sha256`; the server Lua is unchanged
since dc619d0 bar the two regenerated shared/NR_Data_*.lua header dates). Build 42.21.0 (4a0e9546ec), Steam buildid
25485521; both fixtures re-provisioned on it (bd6a9db). One boot of profile x25-rebaseline (fixture two, admin -debug
then bob release, Nutrition false, DayLength 1, sleep on). ONE artifact, `rebaseline.json`, plus the staged
MANIFEST.json copied byte-identical beside it. Shape: x231_perf.py (its helpers copied, its run prefix and profile
constants renamed to x250's, its echo-excluding log greps, the artifact copied by the driver); phase I is x241's
(tick.ring and perf.local, their result documents waited for and kept whole). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENTS:
  the staged copy's NR_Server_Bench.lua (x231's; server only, every handler gated on NR.isServer()):
    NutritionRevamp.server.bench.ticks / .minutes   +1 on every OnTick / EveryOneMinute
    .profStart() / .profStop() / .profReset() / .profText()   the per-step timers (x231's docstring is the contract)
  the harness (server side): tick.ring <n> / read <tag> / off and perf.local <n> / read <tag> / now (x241's).

PHASES (order S0, I, A, Z):
  S0  the ready marks, the verify rows, the players list, the time, the mode, fast.registered, perf.local now (as
      x231's S0 plus x241's perf.local now); then the harness self-check: `test.list` on the server, on `client`
      (admin) and on `client:bob`, and `lua.global TK.version` on the same three sides.
  I   idle: MIN.stats and the players counters; tick.ring RING_N, perf.local PERF_N; IDLE_S wall seconds with NO bus
      traffic; tick.ring read idle, perf.local read idle; the two result documents waited for and kept whole;
      tick.ring off.
  A   x231's phase A unchanged (its constants and calls copied byte for byte: two apples each by RCON additem;
      profReset + profStart at minute m0; at m0+20 eat.action Base.Apple 1 on admin and bob; at m0+30 player.walk
      WALK_DX 0 on both, at m0+35 player.walk -WALK_DX 0, at m0+40 player.stop; at m0+70 the second eat; at m0+80
      player.sleep.hold admin SLEEP_HOLD_S, at m0+110 the hold cancelled and admin set awake; at m0+120 profStop,
      profText; MIN.stats and P.minutes/drained before and after; nutrition.get on both around each meal), plus the
      bench counters NutritionRevamp.server.bench.ticks and .minutes read at phase A's start and end (A_bench).
  Z   the mod-error check (server errors naming the mod's files; admin's lua_error marker).
  After teardown the server log is grepped, echo lines dropped first (CLAUDE.md s5: no probe this driver sends
  carries `minute: `, `hook failed`, `fast: ` or `options: `), for the mod's minute-failure and mode lines.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured; x231's grades):
  A   every one of the nine steps ran in phase A (runs > 0 for each); the whole minute (__run) costs between 100 and
      2000 us per run in play; MIN.stats.failures does not rise. Falsifier: a step with no runs, a per-run cost
      outside the band, a failure.
  T   the ticks a game minute over phase A (the bench counters at its start and end) lie in 6.0..6.6 (#3346: 6.270 at
      DayLength 1). Falsifier: outside the band.
  SC  the self-check answers on all three sides: test.list answers a list (or the documented empty {}) and
      lua.global TK.version resolves, on server, client and client:bob. Falsifier: any side not answering.
  I   the frame instrument answers on 42.21: the idle tick-ring and perf-local documents come back with at least one
      frame and one sample. Falsifier: a document missing or empty.
  Z   no mod error line; admin not parked.

READINGS (not graded): __run's us a run beside #3387's 1558.33 as a ratio (another build and another session: no
threshold); the idle ring's period and endPeriod p99 (and busy) and perf.local's per-window max p99.

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

PROFILE = "x25-rebaseline"
PREFIX = "x250"
SESSION = ("Plan 11a Task R Step 8: the 42.21 smoke -- the harness self-check on three sides, 60 s of idle frames "
           "under tick.ring and perf.local, and x231's phase A (the slow minute by step in play: meals, a walk, a "
           "sleep) with the bench counters around it, on the staged copy at 457f39f with x231's instrument; one boot "
           "of " + PROFILE)
ARTIFACT = "rebaseline.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
SELF_SIDES = (SRV, "client", BOB)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/rebaseline-x250/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
BENCH_FILE = STAGE_MOD + "/common/media/lua/server/NR_Server_Bench.lua"
INSTRUMENT = "testing/spikes/instruments/x231_NR_Server_Bench.lua"
X231_BENCH_SHA256 = "c20f645d833db5d581042ccb84297cd9802d2fe4da1ce43de8b2f096385f0d8d"
STAGED_AT = "457f39f"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
GAME_JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
APP_MANIFEST = r"D:\SteamLibrary\steamapps\appmanifest_108600.acf"
NR = "NutritionRevamp"
BENCH = "NutritionRevamp.server.bench"
STEPS = ("bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight")
APPLE = "Base.Apple"
A_MINUTES = 120
A_EAT = (20, 70)
A_WALK = (30, 35, 40)
A_SLEEP = (80, 110)
WALK_DX = 12
SLEEP_HOLD_S = 25
EAT_READ_S = 8.0
A_CAP_S = 150.0
SPAWN_WAIT_S = 3.0
RING_N = 3000
PERF_N = 1000
IDLE_S = 60
RESULT_WAIT_S = 30.0
POLL_S = 0.3
LOG_LIMIT = 400
RUN_BAND_US = (100.0, 2000.0)
TPM_BAND = (6.0, 6.6)
REF_RUN_US = 1558.33                       # #3387: x231's __run us a run in play (42.20.4)
REF_TPM = 6.270                            # #3346: ticks a game minute at DayLength 1 (42.20.4)
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|fast: |options: ")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

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
    "A": {"steps with runs": 9, "__run us per run": list(RUN_BAND_US), "failures rise": 0},
    "T": {"ticks per game minute over phase A": list(TPM_BAND)},
    "SC": {"test.list answers": list(SELF_SIDES), "TK.version resolves": list(SELF_SIDES)},
    "I": {"tick-ring-idle frames": ">= 1", "perf-local-idle samples": ">= 1"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"), "build": rec_fx.get("build"),
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
             "bench_file": BENCH_FILE, "instrument": INSTRUMENT, "x231_bench_sha256": X231_BENCH_SHA256,
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/rebaseline-x250",
             "build_expected": "42.21.0 (4a0e9546ec), Steam buildid 25485521",
             "bench_note": "Every reading here is cost, not behaviour, except the self-check and the clock: phase A "
                           "is x231's phase A on 42.21, read beside #3387 and #3346. No behaviour row rests on "
                           "this session.",
             "timer_note": "getTimestampMs is 1 ms resolution: every per-run cost is a total over many runs divided "
                           "by their count, and is stated with its count and its ms total.",
             "call_counter_note": "the Java-call counter counts NR.call (and NR.num/obj/flag, which call it by "
                                  "table lookup); direct colon calls are not counted at run time."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "Phase A is x231's; x231's phases B, D, C2 and C are not run (the smoke reads the slow minute in play and "
        "the clock only).",
        "Phase I is x241's idle arm at IDLE_S = 60 s (x241 ran 120 s), with tick.ring off after it.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "readings": {},
}
try:
    out["meta"]["bench_sha256"] = sha256_file(os.path.join(REPO, BENCH_FILE))
    out["meta"]["instrument_sha256"] = sha256_file(os.path.join(REPO, INSTRUMENT))
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
except OSError as e:
    out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"
try:
    out["meta"]["jar_bytes"] = os.path.getsize(GAME_JAR)
    out["meta"]["jar_sha256"] = sha256_file(GAME_JAR)
    with open(APP_MANIFEST, encoding="utf-8", errors="replace") as fh:
        m = re.search(r'"buildid"\s+"(\d+)"', fh.read())
    out["meta"]["steam_buildid"] = m.group(1) if m else None
except OSError as e:
    out["meta"]["install_read_error"] = f"{type(e).__name__}: {e}"


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


def lcall(side, fn, tag, *args):
    return keep(step(tag, side, "lua.call", " ".join([fn] + [str(a) for a in args])))


def counters(tag):
    t = gread(SRV, f"{BENCH}.ticks", f"{tag}_ticks")
    m = gread(SRV, f"{BENCH}.minutes", f"{tag}_minutes")
    return {"ticks": num(val(t)), "minutes": num(val(m)), "wall": t["wall"], "wall_after": m["wall_after"]}


def minstats(tag):
    return {k: num(val(gread(SRV, f"{NR}.server.minute.stats.{k}", f"{tag}_min_{k}"))) for k in ("runs", "failures")} | \
        {f"players_{k}": num(val(gread(SRV, f"{NR}.server.players.{k}", f"{tag}_p_{k}"))) for k in ("minutes", "drained")}


def wait_minute(target, tag, cap_s):
    """Poll the bench minute counter until it reaches `target`; returns the last counters read."""
    end = time.time() + cap_s
    last = None
    while True:
        last = counters(tag)
        if last["minutes"] is not None and last["minutes"] >= target:
            return last
        if time.time() >= end:
            note(f"{tag}: minute {target} not reached inside {cap_s} s (last {last['minutes']})")
            return last
        time.sleep(POLL_S)


def parse_prof(text):
    d = {}
    if not isinstance(text, str):
        return d
    for part in text.split(";"):
        m = re.match(r"^(\w+)=(\-?[\d.]+)/(\-?[\d.]+)/(\-?[\d.]+)$", part.strip())
        if m:
            ms, runs, calls = float(m.group(2)), float(m.group(3)), float(m.group(4))
            d[m.group(1)] = {"ms": ms, "runs": runs, "calls": calls,
                             "us_per_run": (1000.0 * ms / runs) if runs else None,
                             "calls_per_run": (calls / runs) if runs else None}
    return d


def prof_read(tag):
    r = lcall(SRV, f"{BENCH}.profText", f"{tag}_profText")
    return {"text": r.get("r1"), "min_runs": r.get("r2"), "min_failures": r.get("r3"), "ok": r.get("ok"),
            "err": r.get("err"), "wall": r.get("wall"), "parsed": parse_prof(r.get("r1"))}


def rcon(cmd, tag):
    t_before = wall()
    try:
        ok, rep = server.rcon(cmd)
    except Exception as e:                     # noqa: BLE001
        ok, rep = False, f"{type(e).__name__}: {e}"
    row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": wall(), "ack": {"ok": ok, "reply": str(rep)[:300]}}
    out["steps"].append(row)
    tl.mark("rcon", cmd=cmd, ok=ok)
    return row["ack"]


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
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    P["registered"] = gread(SRV, f"{NR}.server.fast.registered", "S0_reg")
    P["perf_now"] = keep(step("S0_perf_now", SRV, "perf.local", "now"))
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}
    sc = P["self_check"] = {"test_list": {}, "tk_version": {}}
    for s in SELF_SIDES:
        r = step(f"S0_test_list_{who(s)}", s, "test.list")
        sc["test_list"][s] = {"ack": r["ack"], "ack_shape": r.get("ack_shape", "dict"), "wall": r["wall_before"]}
        sc["tk_version"][s] = gread(s, "TK.version", f"S0_tk_version_{who(s)}")


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
    P["ring_off"] = keep(step("I_ring_off", SRV, "tick.ring", "off"))


def spawn_apples(tag):
    rows = {}
    for u in USERS:
        rows[u] = rcon(f'additem "{u}" "{APPLE}" 2', f"{tag}_additem_{u}")
    time.sleep(SPAWN_WAIT_S)
    seen = {}
    for u, side in (("admin", ADMIN), ("bob", BOB)):
        seen[u] = keep(step(f"{tag}_seen_{u}", side, "witness.fields", f"item {u}/{APPLE} getID"))
    return {"rcon": rows, "seen": seen}


def nut(tag):
    return {u: keep(step(f"{tag}_nut_{u}", SRV, "nutrition.get", u)) for u in USERS}


def phase_A():
    P = out["phases"]["A"] = {}
    P["spawn"] = spawn_apples("A")
    P["minstats_before"] = minstats("A0")
    P["reset"] = lcall(SRV, f"{BENCH}.profReset", "A_reset")
    P["start"] = lcall(SRV, f"{BENCH}.profStart", "A_start")
    m0 = num(P["start"].get("r3"))
    if m0 is None:
        m0 = counters("A_m0")["minutes"]
    P["m0"] = m0
    P["actions"] = []

    def act(offset, label, fn):
        c = wait_minute(m0 + offset, f"A_wait_{label}", A_CAP_S)
        row = {"offset": offset, "label": label, "minutes": c["minutes"], "ticks": c["ticks"], "wall": wall()}
        row["result"] = fn()
        P["actions"].append(row)
        persist()

    act(A_EAT[0] - 1, "nut0", lambda: nut("A_nut0"))
    act(A_EAT[0], "eat1", lambda: {u: keep(step(f"A_eat1_{u}", s, "eat.action", f"{APPLE} 1"))
                                   for u, s in (("admin", ADMIN), ("bob", BOB))})
    act(A_EAT[0] + 5, "nut1", lambda: nut("A_nut1"))
    act(A_WALK[0], "walk_out", lambda: {u: keep(step(f"A_walk1_{u}", s, "player.walk", f"{WALK_DX} 0"))
                                        for u, s in (("admin", ADMIN), ("bob", BOB))})
    act(A_WALK[1], "walk_back", lambda: {u: keep(step(f"A_walk2_{u}", s, "player.walk", f"{-WALK_DX} 0"))
                                         for u, s in (("admin", ADMIN), ("bob", BOB))})
    act(A_WALK[2], "stop", lambda: {u: keep(step(f"A_stop_{u}", s, "player.stop"))
                                    for u, s in (("admin", ADMIN), ("bob", BOB))})
    act(A_EAT[1], "eat2", lambda: {u: keep(step(f"A_eat2_{u}", s, "eat.action", f"{APPLE} 1"))
                                   for u, s in (("admin", ADMIN), ("bob", BOB))})
    act(A_EAT[1] + 5, "nut2", lambda: nut("A_nut2"))
    act(A_SLEEP[0], "sleep", lambda: keep(step("A_sleep", SRV, "player.sleep.hold", f"admin {SLEEP_HOLD_S}")))
    act(A_SLEEP[0] + 15, "asleep_mid", lambda: keep(step("A_asleep_mid", SRV, "witness.chain", "admin isAsleep")))
    act(A_SLEEP[1], "wake", lambda: {"cancel": keep(step("A_hold0", SRV, "player.sleep.hold", "admin 0")),
                                     "wake": keep(step("A_wake", SRV, "player.sleep", "admin false"))})
    act(A_MINUTES, "stop_prof", lambda: lcall(SRV, f"{BENCH}.profStop", "A_stop"))
    P["prof"] = prof_read("A")
    P["minstats_after"] = minstats("A1")
    P["asleep_after"] = keep(step("A_asleep_after", SRV, "witness.chain", "admin isAsleep"))
    out["world_changes"]["left_in_place"].append("admin and bob each ate two apples and walked out and back in A")


def phase_A_bench():
    """x231's phase A unchanged, between two reads of the bench counters (the ticks a game minute over A)."""
    B = out["phases"]["A_bench"] = {}
    B["start"] = counters("A_bench0")
    try:
        phase_A()
    finally:
        B["end"] = counters("A_bench1")


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()
    P["minstats"] = minstats("Z")


def body():
    order = (("S0", phase_S0), ("I", phase_I), ("A", phase_A_bench), ("Z", phase_Z))
    for name, fn in order:
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


def answered_list(entry):
    a = (entry or {}).get("ack")
    if isinstance(a, list):
        return True
    return isinstance(a, dict) and not a                     # the documented empty answer, {}


def grade_all():
    ph = out["phases"]
    R = out["readings"]

    A = ph.get("A") or {}
    pa = g(A, "prof", "parsed") or {}
    a_run = g(pa, "__run", "us_per_run")
    if pa:
        f0, f1 = g(A, "minstats_before", "failures"), g(A, "minstats_after", "failures")
        obs = {"prof": pa, "steps_with_runs": sum(1 for s in STEPS if (g(pa, s, "runs") or 0) > 0),
               "failures_before": f0, "failures_after": f1, "m0": A.get("m0"),
               "actions": [{k: r.get(k) for k in ("offset", "label", "minutes", "ticks", "wall")}
                           for r in A.get("actions") or []]}
        ok = (obs["steps_with_runs"] == len(STEPS) and a_run is not None
              and RUN_BAND_US[0] <= a_run <= RUN_BAND_US[1] and f0 is not None and f1 == f0)
        grade("A", PRED["A"], obs, "as_predicted" if ok else "falsified",
              "a step with no runs, a per-run cost outside the band, a failure")
    else:
        grade("A", PRED["A"], None, "unmeasured", "no profile read")
    R["run_us_vs_3387"] = {"x250_us_per_run": a_run, "x250_ms": g(pa, "__run", "ms"), "x250_runs": g(pa, "__run", "runs"),
                           "x231_us_per_run": REF_RUN_US,
                           "ratio": (a_run / REF_RUN_US) if a_run is not None else None}

    AB = ph.get("A_bench") or {}
    s, e = AB.get("start") or {}, AB.get("end") or {}
    if None not in (s.get("ticks"), e.get("ticks"), s.get("minutes"), e.get("minutes")) and e["minutes"] > s["minutes"]:
        dt, dm = e["ticks"] - s["ticks"], e["minutes"] - s["minutes"]
        tpm = dt / dm
        obs = {"start": s, "end": e, "ticks": dt, "minutes": dm, "ticks_per_minute": tpm, "ref_3346": REF_TPM}
        grade("T", PRED["T"], obs, "as_predicted" if TPM_BAND[0] <= tpm <= TPM_BAND[1] else "falsified",
              "outside the band")
    else:
        grade("T", PRED["T"], {"start": s, "end": e}, "unmeasured", "no bench counters around phase A")

    S0 = ph.get("S0") or {}
    sc = S0.get("self_check") or {}
    if sc:
        lists = {k: answered_list(v) for k, v in (sc.get("test_list") or {}).items()}
        vers = {k: bool((v or {}).get("resolved")) for k, v in (sc.get("tk_version") or {}).items()}
        obs = {"test_list_answered": lists, "tk_version_resolved": vers,
               "tk_version_values": {k: (v or {}).get("value") for k, v in (sc.get("tk_version") or {}).items()}}
        ok = (all(lists.get(x) for x in SELF_SIDES) and all(vers.get(x) for x in SELF_SIDES))
        grade("SC", PRED["SC"], obs, "as_predicted" if ok else "falsified", "a side not answering")
    else:
        grade("SC", PRED["SC"], None, "unmeasured", "phase S0 not run")

    I = ph.get("I") or {}
    ring_i, perf_i = I.get("ring_doc"), I.get("perf_doc")
    fr = frames_of(ring_i)
    ns = len(((perf_i or {}).get("samples_list") or {}).get("max") or [])
    if ring_i is not None or perf_i is not None:
        busy = [f["busy"] for f in fr if f["busy"] is not None and f["busy"] >= 0]
        per = [f["period"] for f in fr if f["period"] is not None and f["period"] >= 0]
        endp = [f["endPeriod"] for f in fr if f["endPeriod"] is not None and f["endPeriod"] >= 0]
        pmax = [x for x in (((perf_i or {}).get("samples_list") or {}).get("max") or []) if x is not None]
        R["idle"] = {"frames": len(fr), "busy": summ(busy), "period": summ(per), "endPeriod": summ(endp),
                     "over110": sum(1 for x in per if x > 110), "minute_frames": sum(1 for f in fr if f["minute"] == 1),
                     "perf_samples": ns, "perf_window_max": summ(pmax),
                     "perf": {k: (I.get("perf_read") or {}).get(k) for k in ("samples", "max", "min", "avg", "cur")}}
        ok = len(fr) >= 1 and ns >= 1
        grade("I", PRED["I"], {"frames": len(fr), "perf_samples": ns}, "as_predicted" if ok else "falsified",
              "a document missing or empty")
    else:
        grade("I", PRED["I"], None, "falsified" if I else "unmeasured", "a document missing or empty")

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
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
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
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "NutritionRevamp", "common", "media", "lua",
                                              "server", "NR_Server_Bench.lua"), recursive=True)):
        deployed[os.path.relpath(cand, run_dir).replace(os.sep, "/")] = sha256_file(cand)
    out["meta"]["deployed_bench_sha256"] = deployed
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
                  "readings": {"run_us_vs_3387": out.get("readings", {}).get("run_us_vs_3387"),
                               "idle_period_p99": g(out.get("readings", {}), "idle", "period", "p99"),
                               "idle_endPeriod_p99": g(out.get("readings", {}), "idle", "endPeriod", "p99")},
                  "tpm": g(out, "verdicts", "T", "observed", "ticks_per_minute"),
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
