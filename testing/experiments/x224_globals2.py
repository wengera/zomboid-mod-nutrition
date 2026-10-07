"""x224-globals2 -- Plan 10 Task S1b (live): the zeroed-rates route's unmeasured seats.

One boot of profile x22-globals2 (PZTestKit + the FROZEN 1.0.0 spike copy release/spike-1.0.0/.../NutritionRevamp with
[sandbox.NR] Mode = 2 and Severity = 1.5 + TKX_GlobalsProbe2; fixture two, admin -debug then bob release; Nutrition
false; DayLength 4, a game minute 3.75 s wall at speed 1; SleepAllowed and SleepNeeded true). ONE artifact,
`globals2.json`. Shape: x221_globals.py (step, keep, gread, lcall, persist, run_phase, grade, make_server +
attach_clients, the echo-excluding log greps, the artifact copied by the driver). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). The amendments are
.superpowers/sdd/2026-10-07-plan-10-spikes-and-refactor/task-S1b-amendments.md (uncommitted); Ruling S1-1 (amended).

THE PROBE (testing/experiments/TKX_GlobalsProbe2/42.20/media/lua/shared/TKX_GlobalsProbe2.lua):
  file scope   TKX_G2.fileScopeNR / fileScopeDayLength: SandboxVars.NR (type; Mode; Severity) before the server's sandbox.
  OnGameBoot   bootNR, bootNRMode, bootNRSeverity, bootDayLength, bootGate (what a Mode-2 gate would decide), then the
               six non-zero rise keys zeroed (bootSet), unconditionally.
  OnServerStarted  startedNR*, startedTable (the Lua table after Load: a mirror).
  EveryOneMinute (server): every online player gets HUNGER TKX_GP2.wH (0.3), THIRST TKX_GP2.wT (0.05, under the 0.1
               auto-drink gate; the driver raises it with lua.setpath), FATIGUE TKX_GP2.wF (0.1). A ring row per write:
               `seq|minute|user|asleep|preH,preT,preF|postH,postT,postF|dH,dT,dF|worldAgeH|ms|tick`, d = pre minus that
               player's previous post.
  OnTick (server): GP.tick counts every tick; TKX_GP2.arm(user, fullType|-, maxTicks) samples one player per tick:
               `seq|tick|minute|worldAgeH|ms|H,T,F|litres|IsRunning,isPlayerMoving,isSprinting,inSwipe|asleep|foodEaten`.
  cost arm     TKX_GP2.benchPick(name); bench.global TKX_GP2.benchUpdate (the public IsoPlayer.update(): calculateStats
               is protected and the seven updaters private or protected, read with a class-file parse this session),
               benchNoop, benchHookFn; TKX_GP2.hookOn / hookOff register and remove an empty Hook.CalculateStats
               handler (Event.trigger @0-@223 answers true whenever a callback is registered, so calculateStats
               @49-@59 L10204-L10205 returns before the updaters for every character).

PHASES (order S0, A, W, E, X, U, Z):
  S0  ready marks, players, time.snapshot, autodrink.probe admin and bob, the frozen copy's mode and hook flag
      (NutritionRevamp.server.options.mode, NutritionRevamp.server.fast.registered), stats.all admin.
  A   seat 1: every TKX_G2 field on the server; the boot fields on admin's client.
  W   seat 2, auto-drink: RCON additem admin Base.CanteenMilitaryFull (Water only, 0.9 L; x151w's route), resolved on
      admin's client; autodrink.set admin true; autodrink.probe; arm the sampler on admin and the canteen; wait for a
      write; lua.setpath TKX_GP2.wT W_THIRST; autodrink.probe admin every W_DT_S for W_S (about five writes);
      lua.setpath TKX_GP2.wT 0.05; the sampler's rows and the writer's rows of the window.
  E   seat 3, an eat between writes: RCON additem admin Base.Apple, resolved on admin's client; arm the sampler on
      admin; stats.get admin every E_DT_S for E_PRE_S; eat.action Base.Apple 1 on admin's client (the real
      ISEatFoodAction, completed by the server); stats.get admin every E_DT_S for E_S; the sampler and writer rows.
  X   seat 4, the exercise arm: arm the sampler on admin for the whole phase; X1 player.sprint SPRINT_DX 0 SPRINT_S
      (admin), then player.stop; X2 exercise.do squats SQUAT_MIN; X3 RCON createhorde 1 admin, attack.melee
      MELEE_SWINGS polled every 2 s for up to MELEE_WAIT_S until a zombie is within 2 tiles, then MELEE_TAIL_S; the
      sampler and writer rows; per-tick arm flags read on the server's copy.
  U   seat 5, the updaters' cost on bob: benchPick bob; bench.global benchNoop and benchHookFn; a sizing run of
      benchUpdate (U_SIZE_N); then U_PAIRS pairs of [hook off: stats.setany bob STRESS 0.5, benchUpdate N, stats.all
      bob] and [hookOn, STRESS 0.5, benchUpdate N, stats.all bob, hookOff]; hookOff again in a finally.
  Z   the probe-error check: server error lines naming the probe file (echo excluded), writeErrors, sampleErrors,
      hooked false, admin parked.
  After teardown the server log is grepped for the probe file, Lua errors and the frozen copy's self-report (`hook=`).

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  A   the server's OnGameBoot handler reads SandboxVars.NR a table with Mode 2 and Severity 1.5 (the server's sandbox
      is loaded at doMinimumInit @423-@498 before OnGameBoot @525, #3364), bootSide server, bootGate "zero (Mode 2)";
      the file scope reads NR absent or at the defaults (Mode 1, Severity 1.0), never 2 and 1.5. The frozen copy's
      fast.registered false (Mode 2). Falsifier: bootNRMode not 2 or bootNRSeverity not 1.5 on the server.
  W   with THIRST written to 0.3 and 0.9 L of water carried, vanilla's autoDrink (called from updateThirst on every
      update outside its gate, #2250) fires within a few ticks of the write: the canteen falls by min(amount,
      2 x 0.3) = 0.6 L and THIRST to about 0 (#2939's branch); the drop survives, flat, until the next write (the
      rates are zero), so the writer's pre-write read shows it (dT = the drop); the next write's 0.3 drinks the
      remaining 0.3 L (the container branch, THIRST about 0.15); the third write holds 0.3 with no water left.
      Falsifier: the litres never fall with THIRST written at 0.3 (auto-drink does not fire under zeroed rates), or
      THIRST changes between a drink and the next write.
  E   the eat lands between two writes as one HUNGER drop on the server (the apple's hunger change) on a tick with no
      write; HUNGER stays flat at the dropped value until the next write, whose pre-read shows dH = the drop and
      whose post is 0.3 again (the write overwrites the eat). Falsifier: HUNGER moves between the drop and the next
      write, or the next write does not restore 0.3. Unmeasured if no drop is seen (the eat did not land).
  X   HUNGER flat between writes on every tick of the phase (every sampler step with no minute change has dH = 0,
      every writer delta 0). The server's copy is predicted to read IsRunning false throughout (#2877), so the run
      branch of the exercise arm does not engage; the swing branch (SwipeStatePlayer) is unknown. Verdict:
      as_predicted if flat and the arm's condition (IsRunning and moving, or in SwipeStatePlayer) held on >= 1 tick;
      trivial if flat and it never held; falsified on any HUNGER rise between writes.
  U   benchUpdate runs (the update is reachable from Lua); with the hook registered STRESS does not fall across the
      bench (the updaters skipped) and without it it falls; usPerCall(hook off) > usPerCall(hook on) in every pair,
      and the difference (the updaters' cost, less the empty handler's) is between 0.5 and 50 us per player per
      update. Falsifier: the stress witness fails (the hook does not skip) or off <= on in every pair. Trivial if
      every difference is within the bench's resolution (2 ms over the run). Unmeasured if benchUpdate raises.
  Z   no probe error line, writeErrors "0", sampleErrors "0", hooked "false", admin not parked.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
import hashlib
import json
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
from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

PROFILE = "x22-globals2"
PREFIX = "x224"
SESSION = ("Plan 10 Task S1b: the zeroed-rates route's unmeasured seats -- the NR sandbox options read at the "
           "server's OnGameBoot, auto-drink under zeroed rates and a per-minute THIRST write, an eat between two "
           "writes, the exercise hunger arm, and the cost of the updaters a CalculateStats hook skips; one boot of "
           + PROFILE + " on the frozen 1.0.0 spike copy in Mode 2")
ARTIFACT = "globals2.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROBE_DIR = "testing/experiments/TKX_GlobalsProbe2"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
FROZEN_ROOT = "release/spike-1.0.0/NutritionRevamp"
FROZEN_MOD = FROZEN_ROOT + "/Contents/mods/NutritionRevamp"
FROZEN_AT = "42784ff"
GP = "TKX_GP2"
TARGET = {"hunger": 0.3, "thirst": 0.05, "fatigue": 0.1}
FLOAT_TOL = 1e-6
FLAT_TOL = 1e-7
GAME_MIN_S = 3.75             # DayLength 4 at speed 1 (37.46 ticks a game minute, x222)
CANTEEN = "Base.CanteenMilitaryFull"
APPLE = "Base.Apple"
SPAWN_TRIES = 8
SPAWN_WAIT = 1.5
W_THIRST = 0.3
W_S = 20.0
W_DT_S = 0.5
W_TICKS = 600
E_DT_S = 0.5
E_PRE_S = 2.0
E_S = 25.0
E_TICKS = 600
SPRINT_DX = 40
SPRINT_S = 15
SQUAT_MIN = 3
MELEE_SWINGS = 5
MELEE_WAIT_S = 30.0
MELEE_TAIL_S = 12.0
X_TICKS = 2000
U_SIZE_N = 20
U_TARGET_MS = 300.0
U_MIN_N = 50
U_MAX_N = 5000
U_PAIRS = 3
U_NOOP_N = 100000
U_HOOKFN_N = 20000
U_STRESS = 0.5
U_BAND_US = (0.5, 50.0)
RES_MS = 2.0
RING_PAGE = 30
SAMPLE_PAGE = 60
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
LOG_RX = re.compile(r"TKX_GlobalsProbe2|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
PROBE_ERR_RX = re.compile(r"TKX_GlobalsProbe2\.lua")
HOOK_RX = re.compile(r"hook=")

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


def tree_digest(root):
    """sha256 over the sorted relative paths and each file's sha256: one value for the frozen tree."""
    h, n = hashlib.sha256(), 0
    base = os.path.join(REPO, root)
    for d, _dirs, files in sorted(os.walk(base)):
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, base).replace(os.sep, "/")
            h.update((rel + ":" + sha256_file(p) + "\n").encode("utf-8"))
            n += 1
    return {"sha256": h.hexdigest(), "files": n}


PRED = {
    "A": {"bootNRMode": "2", "bootNRSeverity": "1.5", "bootSide": "server", "bootGate": "zero (Mode 2)",
          "fileScope": "NR absent or defaults (never Mode 2 with Severity 1.5)", "fast.registered": False},
    "W": {"first write at 0.3": "canteen -0.6 L, THIRST about 0", "drop survives to the next write": True,
          "pre-write dT": "equals the drop", "second write": "the remaining 0.3 L, THIRST about 0.15",
          "third write": "0.3 held, no water"},
    "E": {"eat": "one HUNGER drop on a tick with no write", "until the next write": "flat",
          "next write": "dH = the drop, post 0.3"},
    "X": {"HUNGER between writes": "flat on every tick", "IsRunning on the server": "false throughout (#2877)",
          "verdict rule": "as_predicted if the arm engaged on >= 1 tick, trivial if never"},
    "U": {"benchUpdate": "runs", "stress witness": "falls hook off, holds hook on",
          "off - on": f"> 0 in every pair, within {U_BAND_US} us"},
    "Z": {"probe_error": "none", "writeErrors": "0", "sampleErrors": "0", "hooked": "false",
          "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "users": list(prof.users),
    "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                "clients": {u: {"debug": (rec_fx.get("clients") or {}).get(u, {}).get("debug")}
                            for u in (rec_fx.get("clients") or {})}},
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
    "probe_dirty": git_dirty(PROBE_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"amendments": ".superpowers/sdd/2026-10-07-plan-10-spikes-and-refactor/task-S1b-amendments.md "
                           "(uncommitted)",
             "frozen_mod": FROZEN_MOD, "frozen_at": FROZEN_AT,
             "zeroed_in_OnGameBoot": ["ThirstIncrease", "ThirstSleepingIncrease", "HungerIncrease",
                                      "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise", "FatigueIncrease"],
             "targets": TARGET,
             "ring_row": "seq|minute|user|asleep|preH,preT,preF|postH,postT,postF|dH,dT,dF|worldAgeH|ms|tick",
             "sample_row": "seq|tick|minute|worldAgeH|ms|H,T,F|litres|IsRunning,isPlayerMoving,isSprinting,inSwipe|"
                           "asleep|foodEaten",
             "jar_access": {"IsoGameCharacter.calculateStats": "protected", "IsoPlayer.calculateStats": "protected",
                            "updateEndurance": "private", "updateTripping": "private", "updateThirst": "private",
                            "updateStress": "private", "updateStats_WakeState": "protected",
                            "updateMorale": "private", "updateFitness": "private", "IsoPlayer.update": "public",
                            "IsoGameCharacter.autoDrink": "public",
                            "read_with": "a session-scoped class-file parse over the toolchain's cp module"}},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "DayLength 4, not S1's 1: at DayLength 1 a game minute is 0.625 s and a 0.5 s poll cannot land between two "
        "writes; at DayLength 4 a minute is 3.75 s. A per-tick server sampler rides beside the 0.5 s polls.",
        "All six rise keys are zeroed in OnGameBoot (S1 split them across file scope and OnGameBoot); the gate a "
        "Mode-driven zeroing would take is recorded, not acted on, so seats 2-5 do not depend on seat 1.",
        "Severity 1.5 is set beside Mode 2 so both OnGameBoot reads tell the server's value from the default.",
        "The THIRST target is 0.05 outside phase W (under the 0.1 auto-drink gate), so the canteen drinks only in W.",
        "Seat 5 times the public IsoPlayer.update() (the whole character update) with and without an empty "
        "CalculateStats hook, on bob, last: calculateStats and the updaters are not reachable from Lua. The "
        "difference bounds the updaters' cost; the extra updates also advance bob's other per-frame state.",
        "Seat 4 adds squats (exercise.do) and melee swings (createhorde + attack.melee) beside the sprint: the jar's "
        "arm is IsRunning and moving, or SwipeStatePlayer (updateStats_Awake @177-@208 L10267).",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}
try:
    out["meta"]["frozen_manifest_sha256"] = sha256_file(os.path.join(REPO, FROZEN_ROOT, "MANIFEST.json"))
    out["meta"]["frozen_tree"] = tree_digest(FROZEN_MOD)
except OSError as e:
    out["meta"]["frozen_hash_error"] = f"{type(e).__name__}: {e}"


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


def sread(side, user, tag):
    args = user if side == SRV else ""
    a = keep(step(tag, side, "stats.get", args))
    return {k: a.get(k) for k in ("hunger", "thirst", "fatigue", "endurance", "asleep", "running", "sprinting",
                                  "moving", "worldAge", "mult", "wall", "wall_after", "side", "raw", "error")}


def adprobe(tag):
    a = keep(step(tag, SRV, "autodrink.probe", USER))
    return {k: a.get(k) for k in ("thirst", "litres", "item", "autoDrink", "containers", "wall", "wall_after",
                                  "ok", "reason", "raw")}


def poll(fn, seconds, dt, tag):
    rows, end = [], time.time() + seconds
    while time.time() < end:
        t_next = time.time() + dt
        rows.append(fn(tag))
        rest = t_next - time.time()
        if rest > 0:
            time.sleep(rest)
    return rows


def spawn(full_type, why):
    """RCON additem, then poll admin's CLIENT until the instance resolves there (x151w's route)."""
    a = rcon(f'additem "{USER}" "{full_type}" 1', f"spawn_{why}")
    row = {"type": full_type, "why": why, "rcon": a, "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", ADMIN, "witness.fields", f"item {USER}/{full_type} getID"))
        res = seen.get("resolved")
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": (seen.get("fields") or {}).get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    return row


def parse_ring(text):
    rows = []
    if not isinstance(text, str) or not text:
        return rows
    for ln in text.split("\n"):
        f = ln.split("|")
        if len(f) != 10:
            if ln:
                rows.append({"raw": ln})
            continue
        pre = [num(x) for x in f[4].split(",")]
        post = [num(x) for x in f[5].split(",")]
        d = [num(x) for x in f[6].split(",")] if f[6] != "na" else [None, None, None]
        rows.append({"seq": num(f[0]), "minute": num(f[1]), "user": f[2], "asleep": f[3] == "true",
                     "pre": pre, "post": post, "d": d, "age": num(f[7]), "ms": num(f[8]), "tick": num(f[9])})
    return rows


def parse_samples(text):
    rows = []
    if not isinstance(text, str) or not text:
        return rows
    for ln in text.split("\n"):
        f = ln.split("|")
        if len(f) != 10:
            if ln:
                rows.append({"raw": ln})
            continue
        htf = [num(x) for x in f[5].split(",")]
        fl = f[7].split(",")
        rows.append({"seq": num(f[0]), "tick": num(f[1]), "minute": num(f[2]), "age": num(f[3]), "ms": num(f[4]),
                     "H": htf[0] if htf else None, "T": htf[1] if len(htf) > 1 else None,
                     "F": htf[2] if len(htf) > 2 else None, "litres": num(f[6]),
                     "run": fl[0] == "true" if fl else None, "moving": len(fl) > 1 and fl[1] == "true",
                     "sprint": len(fl) > 2 and fl[2] == "true", "swipe": fl[3] if len(fl) > 3 else None,
                     "asleep": f[8] == "true", "fe": num(f[9])})
    return rows


def ring_since(seq0, tag):
    rows, lo, total = [], (int(seq0) if seq0 is not None else 0) + 1, None
    for _ in range(40):
        r = lcall(SRV, f"{GP}.ringText", f"{tag}_ring{lo}", lo, lo + RING_PAGE - 1)
        total = num(r.get("r2"))
        rows.extend(parse_ring(r.get("r1")))
        if total is None or lo + RING_PAGE - 1 >= total:
            break
        lo += RING_PAGE
    return {"seq_end": total, "rows": rows}


def samples_since(seq0, tag):
    rows, lo, total = [], (int(seq0) if seq0 is not None else 0) + 1, None
    for _ in range(80):
        r = lcall(SRV, f"{GP}.sampleText", f"{tag}_smp{lo}", lo, lo + SAMPLE_PAGE - 1)
        total = num(r.get("r2"))
        rows.extend(parse_samples(r.get("r1")))
        if total is None or lo + SAMPLE_PAGE - 1 >= total:
            break
        lo += SAMPLE_PAGE
    return {"seq_end": total, "rows": rows}


def seqs(tag):
    r = lcall(SRV, f"{GP}.seqs", f"{tag}_seqs")
    return {"ring": num(r.get("r1")), "sample": num(r.get("r2")), "tick": num(r.get("r3"))}


def wait_write(tag, cap_s=8.0):
    """Block until the writer's ring advances (a write has just run), so a target change lands right after one."""
    s0 = seqs(f"{tag}_w0")["ring"]
    end = time.time() + cap_s
    while time.time() < end:
        time.sleep(0.25)
        s1 = seqs(f"{tag}_w1")["ring"]
        if s0 is not None and s1 is not None and s1 > s0:
            return {"ring0": s0, "ring1": s1, "wall": wall()}
    return {"ring0": s0, "ring1": None, "wall": wall(), "timeout": True}


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
G_FIELDS = ("version", "side", "fileScopeNR", "fileScopeDayLength", "fileScopeAt", "bootFired", "bootSide", "bootAt",
            "bootDayLength", "bootNR", "bootNRMode", "bootNRSeverity", "bootGate", "bootTableBefore", "bootSet",
            "startedNR", "startedNRMode", "startedNRSeverity", "startedTable", "startedAt", "minutes", "writes",
            "writeErrors", "lastErr", "sampleErrors", "sampleLastErr", "hooked", "hookAdds", "hookRemoves", "hookErr")


def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = keep(step("S0_time", SRV, "time.snapshot"))
    P["autodrink"] = {u: keep(step(f"S0_autodrink_{u}", SRV, "autodrink.probe", u)) for u in ("admin", "bob")}
    P["nr"] = {f: gread(SRV, f"NutritionRevamp.{f}", f"S0_nr_{f}")
               for f in ("version", "server.options.mode", "server.options.severity", "server.fast.registered")}
    P["stats_all"] = keep(step("S0_stats_all", SRV, "stats.all", USER))
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in (ADMIN, BOB)}


def phase_A():
    P = out["phases"]["A"] = {}
    P["server"] = {f: gread(SRV, f"TKX_G2.{f}", f"A_srv_{f}") for f in G_FIELDS}
    P["admin"] = {f: gread(ADMIN, f"TKX_G2.{f}", f"A_adm_{f}")
                  for f in ("side", "fileScopeNR", "bootFired", "bootSide", "bootNR", "bootNRMode", "bootNRSeverity",
                            "bootDayLength", "startedNRMode", "startedTable")}


def phase_W():
    P = out["phases"]["W"] = {}
    P["spawn"] = spawn(CANTEEN, "W")
    P["autodrink_on"] = keep(step("W_ad_on", SRV, "autodrink.set", f"{USER} true"))
    P["probe0"] = adprobe("W_probe0")
    P["seqs0"] = seqs("W0")
    P["arm"] = lcall(SRV, f"{GP}.arm", "W_arm", USER, CANTEEN, W_TICKS)
    P["wait"] = wait_write("W")
    try:
        P["raise"] = keep(step("W_raise", SRV, "lua.setpath", f"{GP}.wT {W_THIRST}"))
        P["probes"] = poll(adprobe, W_S, W_DT_S, "W_probe")
    finally:
        P["lower"] = keep(step("W_lower", SRV, "lua.setpath", f"{GP}.wT {TARGET['thirst']}"))
        out["world_changes"]["thirst_target"] = "raised to 0.3 for W, lowered to 0.05 after"
    time.sleep(GAME_MIN_S + 0.5)
    P["probe1"] = adprobe("W_probe1")
    P["disarm"] = lcall(SRV, f"{GP}.disarm", "W_disarm")
    P["samples"] = samples_since(g(P, "seqs0", "sample"), "W")
    P["ring"] = ring_since(g(P, "seqs0", "ring"), "W")
    out["world_changes"]["left_in_place"].append("a CanteenMilitaryFull in admin's inventory (drunk in W)")


def phase_E():
    P = out["phases"]["E"] = {}
    P["spawn"] = spawn(APPLE, "E")
    P["seqs0"] = seqs("E0")
    P["arm"] = lcall(SRV, f"{GP}.arm", "E_arm", USER, "-", E_TICKS)
    P["pre"] = poll(lambda t: sread(SRV, USER, t), E_PRE_S, E_DT_S, "E_pre")
    P["eat_wall"] = wall()
    P["eat"] = keep(step("E_eat", ADMIN, "eat.action", f"{APPLE} 1"))
    P["reads"] = poll(lambda t: sread(SRV, USER, t), E_S, E_DT_S, "E_read")
    P["disarm"] = lcall(SRV, f"{GP}.disarm", "E_disarm")
    P["samples"] = samples_since(g(P, "seqs0", "sample"), "E")
    P["ring"] = ring_since(g(P, "seqs0", "ring"), "E")


def phase_X():
    P = out["phases"]["X"] = {}
    P["seqs0"] = seqs("X0")
    P["arm"] = lcall(SRV, f"{GP}.arm", "X_arm", USER, "-", X_TICKS)
    P["marks"] = {}
    P["marks"]["sprint"] = {"wall": wall(), "seqs": seqs("X1")}
    P["sprint"] = keep(step("X_sprint", ADMIN, "player.sprint", f"{SPRINT_DX} 0 {SPRINT_S}"))
    P["sprint_reads"] = poll(lambda t: sread(SRV, USER, t), SPRINT_S + 2.0, 1.0, "X_sprint_read")
    P["stop1"] = keep(step("X_stop1", ADMIN, "player.stop"))
    P["marks"]["squats"] = {"wall": wall(), "seqs": seqs("X2")}
    P["squats"] = keep(step("X_squats", ADMIN, "exercise.do", f"squats {SQUAT_MIN}"))
    P["squat_reads"] = poll(lambda t: sread(SRV, USER, t), SQUAT_MIN * GAME_MIN_S + 6.0, 1.0, "X_squat_read")
    P["stop2"] = keep(step("X_stop2", ADMIN, "player.stop"))
    P["marks"]["melee"] = {"wall": wall(), "seqs": seqs("X3")}
    P["horde"] = [rcon(f"createhorde 1 {USER}", "X_horde")]
    out["world_changes"]["left_in_place"].append("zombies spawned by createhorde near admin in X")
    attacks, end, started_at = [], time.time() + MELEE_WAIT_S, None
    while time.time() < end:
        a = keep(step("X_attack", ADMIN, "attack.melee", str(MELEE_SWINGS)))
        attacks.append(a)
        if a.get("armed") or a.get("ok") is True or a.get("target"):
            started_at = time.time()
            break
        time.sleep(2.0)
    if started_at is None:
        P["horde"].append(rcon(f"createhorde 1 {USER}", "X_horde2"))
        end = time.time() + MELEE_WAIT_S / 2.0
        while time.time() < end:
            a = keep(step("X_attack2", ADMIN, "attack.melee", str(MELEE_SWINGS)))
            attacks.append(a)
            if a.get("armed") or a.get("ok") is True or a.get("target"):
                started_at = time.time()
                break
            time.sleep(2.0)
    P["attacks"] = attacks
    if started_at is not None:
        try:
            P["melee_result"] = clients["admin"].bus.wait_result("attack-melee", timeout=MELEE_SWINGS * 2 + 10,
                                                                 after=started_at - 1.0)
        except Exception as e:                 # noqa: BLE001
            P["melee_result"] = {"error": f"{type(e).__name__}: {e}"}
        time.sleep(MELEE_TAIL_S)
    else:
        note("no zombie came within 2 tiles; the swing arm was not driven")
    P["marks"]["end"] = {"wall": wall(), "seqs": seqs("X4")}
    P["disarm"] = lcall(SRV, f"{GP}.disarm", "X_disarm")
    P["samples"] = samples_since(g(P, "seqs0", "sample"), "X")
    P["ring"] = ring_since(g(P, "seqs0", "ring"), "X")


def bench(tag, fn, n, timeout=120):
    return keep(step(tag, SRV, "bench.global", f"{GP}.{fn} {n}", timeout=timeout))


def stress(tag):
    a = keep(step(tag, SRV, "stats.all", "bob"))
    return {"stress": num(g(a, "stats", "Stress")), "worldAge": num(a.get("worldAge")), "wall": a.get("wall")}


def phase_U():
    P = out["phases"]["U"] = {}
    P["pick"] = lcall(SRV, f"{GP}.benchPick", "U_pick", "bob")
    P["noop"] = bench("U_noop", "benchNoop", U_NOOP_N)
    P["hookfn"] = bench("U_hookfn", "benchHookFn", U_HOOKFN_N)
    P["size"] = bench("U_size", "benchUpdate", U_SIZE_N)
    us = num(P["size"].get("usPerCall"))
    if P["size"].get("error") or us is None:
        P["n"] = None
        note("the sizing run of benchUpdate raised or returned no figure; the pairs are not run")
        return
    n = U_MAX_N if us <= 0 else int(max(U_MIN_N, min(U_MAX_N, U_TARGET_MS * 1000.0 / us)))
    P["n"] = n
    pairs = []
    try:
        for i in range(U_PAIRS):
            row = {}
            row["off_set"] = keep(step(f"U_off_set{i}", SRV, "stats.setany", f"bob STRESS {U_STRESS}"))
            row["off_s0"] = stress(f"U_off_s0_{i}")
            row["off"] = bench(f"U_off{i}", "benchUpdate", n)
            row["off_s1"] = stress(f"U_off_s1_{i}")
            row["hook_on"] = lcall(SRV, f"{GP}.hookOn", f"U_hookon{i}")
            row["on_set"] = keep(step(f"U_on_set{i}", SRV, "stats.setany", f"bob STRESS {U_STRESS}"))
            row["on_s0"] = stress(f"U_on_s0_{i}")
            row["on"] = bench(f"U_on{i}", "benchUpdate", n)
            row["on_s1"] = stress(f"U_on_s1_{i}")
            row["hook_off"] = lcall(SRV, f"{GP}.hookOff", f"U_hookoff{i}")
            pairs.append(row)
            persist()
    finally:
        P["pairs"] = pairs
        P["final_off"] = lcall(SRV, f"{GP}.hookOff", "U_hookoff_final")
        P["hooked"] = gread(SRV, "TKX_G2.hooked", "U_hooked")
        out["world_changes"]["hook"] = "an empty CalculateStats hook registered and removed per pair; removed again"
        out["world_changes"]["bob"] = "bob's update() called extra times on the server in U"


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_probe_error_lines"] = [e[:400] for e in errs if PROBE_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    for f in ("writeErrors", "lastErr", "sampleErrors", "sampleLastErr", "minutes", "writes", "hooked", "hookAdds",
              "hookRemoves", "hookErr"):
        P[f] = gread(SRV, f"TKX_G2.{f}", f"Z_{f}")
    P["fast_registered"] = gread(SRV, "NutritionRevamp.server.fast.registered", "Z_fast_registered")
    P["admin_parked"] = parked()


def body():
    order = (("S0", phase_S0), ("A", phase_A), ("W", phase_W), ("E", phase_E), ("X", phase_X), ("U", phase_U),
             ("Z", phase_Z))
    for name, fn in order:
        run_phase(name, fn)
        if parked() and name != "Z":
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return


def read_logs(every):
    L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "probe": PROBE_ERR_RX.pattern, "hook": HOOK_RX.pattern,
                                    "echo_excluded": ECHO_RX.pattern}, "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        probe, probe_echo = grep_noecho(server.log_path, PROBE_ERR_RX, LOG_LIMIT)
        hook, hook_echo = grep_noecho(server.log_path, HOOK_RX, 20)
        L["server"] = {"lines": raw, "echo_lines_excluded": echoed, "probe_lines": probe,
                       "probe_echo_excluded": probe_echo, "hook_lines": hook, "hook_echo_excluded": hook_echo}
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


def steps_of(rows):
    """Consecutive sampler pairs: (a, b, same_minute)."""
    good = [r for r in rows if r.get("tick") is not None and r.get("H") is not None]
    return [(a, b, a.get("minute") == b.get("minute")) for a, b in zip(good, good[1:])]


def admin_ring(rows):
    return [r for r in rows if r.get("user") == USER and r.get("d") and r["d"][0] is not None]


def grade_A():
    A = out["phases"].get("A") or {}
    if not A:
        grade("A", PRED["A"], None, "unmeasured", "phase A not run")
        return
    sv = {f: val(A["server"].get(f)) for f in A.get("server", {})}
    reg = val(g(out, "phases", "S0", "nr", "server.fast.registered"))
    obs = {"server": sv, "admin": {f: val(r) for f, r in (A.get("admin") or {}).items()}, "fast.registered": reg,
           "options.mode": val(g(out, "phases", "S0", "nr", "server.options.mode")),
           "options.severity": val(g(out, "phases", "S0", "nr", "server.options.severity"))}
    if sv.get("bootFired") in (None, "0") or sv.get("bootSide") != "server":
        grade("A", PRED["A"], obs, "unmeasured", "bootNRMode not 2 or bootNRSeverity not 1.5 on the server",
              {"note": "the OnGameBoot handler did not run on the server"})
        return
    mode_ok = str(sv.get("bootNRMode")) in ("2", "2.0")
    sev_ok = num(sv.get("bootNRSeverity")) == 1.5
    fs = str(sv.get("fileScopeNR") or "")
    fs_ok = not ("Mode=2" in fs and "Severity=1.5" in fs)
    v = "as_predicted" if (mode_ok and sev_ok and fs_ok and reg is False) else "falsified"
    grade("A", PRED["A"], obs, v, "bootNRMode not 2 or bootNRSeverity not 1.5 on the server",
          {"checks": {"mode": mode_ok, "severity": sev_ok, "fileScope_not_server_values": fs_ok,
                      "fast_registered_false": reg is False}})


def grade_W():
    W = out["phases"].get("W") or {}
    rows = g(W, "samples", "rows") or []
    st = steps_of(rows)
    if not st:
        grade("W", PRED["W"], {"spawn": W.get("spawn"), "arm": W.get("arm")}, "unmeasured", "no sampler rows")
        return
    drinks = []
    for i, (a, b, same) in enumerate(st):
        la, lb = num(a.get("litres")), num(b.get("litres"))
        if la is not None and lb is not None and lb < la - 1e-6:
            # what THIRST did from this drink until the next minute change
            after = []
            for (c, d, s2) in st[i + 1:]:
                if not s2:
                    break
                after.append(d.get("T"))
            span = (max(after) - min(after)) if after else None
            drinks.append({"tick_before": a.get("tick"), "tick": b.get("tick"), "minute": b.get("minute"),
                           "same_minute_as_prev_sample": same, "litres_before": la, "litres_after": lb,
                           "dLitres": lb - la, "T_before": a.get("T"), "T_after": b.get("T"),
                           "dT": (b.get("T") - a.get("T")) if None not in (a.get("T"), b.get("T")) else None,
                           "samples_until_next_write": len(after), "T_span_until_next_write": span})
    ring = admin_ring(g(W, "ring", "rows") or [])
    ring_rows = [{"seq": r.get("seq"), "minute": r.get("minute"), "tick": r.get("tick"), "pre": r.get("pre"),
                  "post": r.get("post"), "d": r.get("d")} for r in ring]
    # T changes between two samples of one minute that are not a drink
    other = [{"tick": b.get("tick"), "T0": a.get("T"), "T1": b.get("T")} for (a, b, same) in st
             if same and None not in (a.get("T"), b.get("T")) and abs(b["T"] - a["T"]) > FLAT_TOL
             and not (num(a.get("litres")) is not None and num(b.get("litres")) is not None
                      and num(b.get("litres")) < num(a.get("litres")) - 1e-6)]
    obs = {"drinks": drinks, "ring": ring_rows, "other_T_changes_within_a_minute": other[:20],
           "n_samples": len(rows), "probe0": W.get("probe0"), "probe1": W.get("probe1"),
           "probes": [{k: p.get(k) for k in ("thirst", "litres", "wall")} for p in (W.get("probes") or [])],
           "spawn_resolved": g(W, "spawn", "resolved"), "arm": W.get("arm"), "raise": W.get("raise"),
           "lower": W.get("lower")}
    if not drinks:
        v = "falsified" if (g(W, "spawn", "resolved") and W.get("raise")) else "unmeasured"
    else:
        survived = all(d["T_span_until_next_write"] is not None and d["T_span_until_next_write"] <= FLAT_TOL
                       for d in drinks)
        v = "as_predicted" if (survived and not other) else "falsified"
    grade("W", PRED["W"], obs, v, "the litres never fall with THIRST written at 0.3, or THIRST changes between a drink "
          "and the next write", {"note": "the writer's pre-write read (ring d) is compared with each drink's T_after "
                                         "by hand in the memo"})


def grade_E():
    E = out["phases"].get("E") or {}
    rows = g(E, "samples", "rows") or []
    st = steps_of(rows)
    if not st:
        grade("E", PRED["E"], {"eat": E.get("eat")}, "unmeasured", "no sampler rows")
        return
    drops = []
    for i, (a, b, same) in enumerate(st):
        if same and None not in (a.get("H"), b.get("H")) and abs(b["H"] - a["H"]) > FLAT_TOL:
            after, nxt = [], None
            for (c, d, s2) in st[i + 1:]:
                if not s2:
                    nxt = d
                    break
                after.append(d.get("H"))
            span = (max(after) - min(after)) if after else None
            drops.append({"tick": b.get("tick"), "minute": b.get("minute"), "H_before": a.get("H"),
                          "H_after": b.get("H"), "dH": b["H"] - a["H"], "fe_after": b.get("fe"),
                          "samples_until_next_write": len(after), "H_span_until_next_write": span,
                          "H_after_next_write": nxt.get("H") if nxt else None,
                          "next_write_tick": nxt.get("tick") if nxt else None})
    ring = admin_ring(g(E, "ring", "rows") or [])
    ring_rows = [{"seq": r.get("seq"), "minute": r.get("minute"), "tick": r.get("tick"), "pre": r.get("pre"),
                  "post": r.get("post"), "d": r.get("d")} for r in ring]
    obs = {"drops_within_a_minute": drops, "ring": ring_rows, "n_samples": len(rows), "eat": E.get("eat"),
           "eat_wall": E.get("eat_wall"), "spawn_resolved": g(E, "spawn", "resolved"),
           "reads": [{k: r.get(k) for k in ("hunger", "wall")} for r in (E.get("reads") or [])]}
    if not drops:
        grade("E", PRED["E"], obs, "unmeasured", "HUNGER moves between the drop and the next write, or the next write "
              "does not restore 0.3", {"note": "no HUNGER change within a minute: the eat did not land in the window"})
        return
    ok = (len(drops) >= 1 and all(d["dH"] < 0 for d in drops)
          and all(d["H_span_until_next_write"] is not None and d["H_span_until_next_write"] <= FLAT_TOL for d in drops)
          and all(d["H_after_next_write"] is not None and abs(d["H_after_next_write"] - TARGET["hunger"]) <= FLOAT_TOL
                  for d in drops))
    grade("E", PRED["E"], obs, "as_predicted" if ok else "falsified",
          "HUNGER moves between the drop and the next write, or the next write does not restore 0.3",
          {"note": "more than one drop within a minute (a partial eat) is listed and read by hand"})


def grade_X():
    X = out["phases"].get("X") or {}
    rows = g(X, "samples", "rows") or []
    st = steps_of(rows)
    if not st:
        grade("X", PRED["X"], {"arm": X.get("arm")}, "unmeasured", "no sampler rows")
        return
    rises = [{"tick": b.get("tick"), "H0": a.get("H"), "H1": b.get("H")} for (a, b, same) in st
             if same and b["H"] - a["H"] > FLAT_TOL]
    moves = [{"tick": b.get("tick"), "H0": a.get("H"), "H1": b.get("H")} for (a, b, same) in st
             if same and abs(b["H"] - a["H"]) > FLAT_TOL]
    good = [r for r in rows if r.get("tick") is not None]
    run_moving = sum(1 for r in good if r.get("run") and r.get("moving"))
    swipe = sum(1 for r in good if r.get("swipe") == "true")
    engaged = run_moving + swipe
    ring = admin_ring(g(X, "ring", "rows") or [])
    ring_dH = [r["d"][0] for r in ring]
    obs = {"n_samples": len(good), "ticks_run": sum(1 for r in good if r.get("run")),
           "ticks_moving": sum(1 for r in good if r.get("moving")), "ticks_sprint": sum(1 for r in good if r.get("sprint")),
           "ticks_run_and_moving": run_moving, "ticks_swipe": swipe,
           "swipe_values": sorted({str(r.get("swipe")) for r in good}),
           "H_rises_within_a_minute": rises[:20], "H_moves_within_a_minute": moves[:20],
           "H_min": min((r["H"] for r in good if r.get("H") is not None), default=None),
           "H_max": max((r["H"] for r in good if r.get("H") is not None), default=None),
           "ring_n": len(ring), "ring_max_abs_dH": max((abs(x) for x in ring_dH), default=None),
           "marks": X.get("marks"), "sprint": X.get("sprint"), "squats": X.get("squats"),
           "attacks": X.get("attacks"), "melee_result": X.get("melee_result"), "horde": X.get("horde")}
    flat = not moves and all(abs(x) <= FLAT_TOL for x in ring_dH)
    if not flat:
        v = "falsified"
    elif engaged >= 1:
        v = "as_predicted"
    else:
        v = "trivial"
    grade("X", PRED["X"], obs, v, "any HUNGER rise between writes",
          {"note": "a fall within a minute (none expected here) is listed in H_moves and read by hand"})


def grade_U():
    U = out["phases"].get("U") or {}
    pairs = U.get("pairs") or []
    if not pairs:
        grade("U", PRED["U"], {"size": U.get("size"), "pick": U.get("pick"), "n": U.get("n")}, "unmeasured",
              "the stress witness fails or off <= on in every pair")
        return
    rows = []
    for p in pairs:
        off_us, on_us = num(g(p, "off", "usPerCall")), num(g(p, "on", "usPerCall"))
        so0, so1 = num(g(p, "off_s0", "stress")), num(g(p, "off_s1", "stress"))
        sn0, sn1 = num(g(p, "on_s0", "stress")), num(g(p, "on_s1", "stress"))
        rows.append({"off_us": off_us, "on_us": on_us, "off_ms": num(g(p, "off", "ms")), "on_ms": num(g(p, "on", "ms")),
                     "diff_us": (off_us - on_us) if None not in (off_us, on_us) else None,
                     "off_error": g(p, "off", "error"), "on_error": g(p, "on", "error"),
                     "off_stress_fall": (so0 - so1) if None not in (so0, so1) else None,
                     "on_stress_fall": (sn0 - sn1) if None not in (sn0, sn1) else None,
                     "hook_on": {k: g(p, "hook_on", k) for k in ("r1", "r2", "r3", "err")},
                     "hook_off": {k: g(p, "hook_off", k) for k in ("r1", "r2", "r3", "err")}})
    n = U.get("n")
    obs = {"n": n, "pairs": rows, "noop_us": num(g(U, "noop", "usPerCall")), "hookfn_us": num(g(U, "hookfn", "usPerCall")),
           "size": U.get("size"), "pick": U.get("pick"), "final_off": U.get("final_off"), "hooked": val(U.get("hooked"))}
    if any(r["off_error"] or r["on_error"] for r in rows) or any(r["diff_us"] is None for r in rows):
        grade("U", PRED["U"], obs, "unmeasured", "the stress witness fails or off <= on in every pair",
              {"note": "a bench raised or returned no figure"})
        return
    witness = all(r["off_stress_fall"] is not None and r["on_stress_fall"] is not None
                  and r["off_stress_fall"] > r["on_stress_fall"] + 1e-6 and abs(r["on_stress_fall"]) <= 1e-4
                  for r in rows)
    diffs = [r["diff_us"] for r in rows]
    res_us = RES_MS * 1000.0 / n if n else None
    if not witness or all(d <= 0 for d in diffs):
        v = "falsified"
    elif res_us is not None and all(abs(d) <= res_us for d in diffs):
        v = "trivial"
    elif all(d > 0 for d in diffs) and all(U_BAND_US[0] <= d <= U_BAND_US[1] for d in diffs):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("U", PRED["U"], obs, v, "the stress witness fails or off <= on in every pair",
          {"resolution_us": res_us, "note": "a positive difference outside the band is recorded as falsified against "
                                             "the band and read by hand"})


def grade_Z():
    Z = out["phases"].get("Z") or {}
    if not Z:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")
        return
    obs = {"server_probe_error_lines": Z.get("server_probe_error_lines") or [],
           **{f: val(Z.get(f)) for f in ("writeErrors", "lastErr", "sampleErrors", "sampleLastErr", "minutes", "writes",
                                         "hooked", "hookAdds", "hookRemoves", "hookErr", "fast_registered")},
           "admin_lua_error": out.get("admin_lua_error")}
    ok = (not obs["server_probe_error_lines"] and str(obs["writeErrors"]) == "0" and str(obs["sampleErrors"]) == "0"
          and str(obs["hooked"]) == "false" and not obs["admin_lua_error"])
    grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified",
          "a probe error line, writeErrors, sampleErrors, the hook left on, admin parked")


def grade_all():
    for fn in (grade_A, grade_W, grade_E, grade_X, grade_U, grade_Z):
        try:
            fn()
        except Exception as e:                 # noqa: BLE001 - one grader's fault keeps the others
            out.setdefault("grade_errors", {})[fn.__name__] = f"{type(e).__name__}: {e}"


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
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "grade_errors": out.get("grade_errors"),
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
