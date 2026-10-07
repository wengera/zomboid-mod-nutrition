"""x221-globals -- Plan 10 Task S1 (live): the zeroed-drains alternative to the Hook.CalculateStats takeover.

One boot of profile x22-globals (PZTestKit + TKX_GlobalsProbe, NOT NutritionRevamp; fixture two, admin -debug then
bob release; Nutrition false; DayLength 1, a game minute 0.625 s at speed 1; SleepAllowed and SleepNeeded true).
ONE artifact, `globals.json`. Shape: x222_clock_cost.py (step, keep, gread, lcall, persist, run_phase, grade,
make_server + attach_clients, the echo-excluding log greps, the artifact copied by the driver). Written BEFORE the
boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE PROBE (testing/experiments/TKX_GlobalsProbe/42.20/media/lua/shared/TKX_GlobalsProbe.lua; the desk read is
.superpowers/sdd/2026-10-07-plan-10-spikes-and-refactor/task-S1-desk.md):
  route 1, file scope (inside LoadDirBase, before ZomboidGlobals.Load):  ThirstIncrease = 0, ThirstSleepingIncrease = 0
  route 2, Events.OnGameBoot (GameServer.doMinimumInit @525-@528 L1516, one instruction before Load @531 L1517):
           HungerIncrease, HungerIncreaseWhileAsleep, HungerIncreaseWhenExercise, FatigueIncrease = 0
  TKX_G (strings): fileScope, fileScopeDayLength, bootFired, bootSide, bootSet, bootDayLength, bootTableBefore,
           startedTable (the Lua table after Load: a mirror), minutes, writes, writeErrors, lastErr, on.
  EveryOneMinute (server): for every online player, read HUNGER/THIRST/FATIGUE (pre), write 0.3/0.2/0.1 through
           stats:set(CharacterStat.X, v) (the takeover's setter), read back (post). A ring row per player per
           minute: `seq|minute|user|asleep|preH,preT,preF|postH,postT,postF|dH,dT,dF|worldAgeH|ms`, where d = pre
           minus that player's previous post = what vanilla's update (and any event) did over one game minute.
  TKX_GP.ringText(a, b), aggText(), resetAgg() (lua.call); TKX_GP.on (lua.setpath) pauses the writer;
  TKX_GP.benchPick(name) then bench.global TKX_GP.benchNoop / benchSet / benchGetSet / benchMinute (the cost arm).

PHASES (order S0, A, B, B2, C, D, E, F, Z):
  S0  ready marks, verify rows, players, time.snapshot, autodrink.probe admin and bob (a water source would make
      vanilla auto-drink fire whenever THIRST > 0.1, so the thirst drift is read against it), stats.all admin.
  A   Q2: every TKX_G field on the server, and fileScope/bootFired/bootSide/bootSet/startedTable on admin's client.
  B   Q3/Q4 awake, writes on: resetAgg; server stats.get admin every B_DT_S for B_S real seconds; then the ring
      rows of the window and aggText. Values between writes (the 0.5 s reads) and after a write (the ring's post).
  B2  Q3, the rate check with the writer paused: lua.setpath TKX_GP.on false; stats.setany admin STRESS 0.5 (the
      awake updater's stress decay is the witness that the other updaters still run); stats.all admin; stats.get
      admin every 1 s for B2_S; stats.all admin; lua.setpath TKX_GP.on true.
  C   Q4 sync: B... C_PAIRS client-first pairs per user (client stats.get on the user's own client, then server
      stats.get <user>), C_GAP_S apart, for admin and bob.
  D   Q3 asleep: resetAgg; stats.all admin; player.sleep.hold admin D_HOLD_S; server stats.get admin every 1 s for
      D_S; one client-first pair at the middle; aggText and the ring; hold cancelled (0), player.sleep admin false;
      stats.all admin.
  E   Q3/Q4 under high time speed: resetAgg; rcon settimespeed E_SPEED; server stats.get admin every B_DT_S for E_S;
      aggText and the ring; rcon settimespeed 1 (in a finally); time.snapshot.
  F   Q7 cost: benchPick admin; bench.global TKX_GP.benchNoop F_NOOP_N x1, benchSet F_N x3, benchGetSet F_N x3,
      benchMinute F_MIN_N x1 (last: it advances the ring); resetAgg after.
  Z   the probe-error check: server error lines naming TKX_GlobalsProbe.lua (echo excluded), TKX_G.writeErrors and
      lastErr, admin parked.
  After teardown the server log is grepped for the probe file and Lua errors (echo lines dropped first; CLAUDE.md
  s5: no command this driver sends names `TKX_GlobalsProbe.lua`).

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  A   server: fileScope `ThirstIncrease=0;ThirstSleepingIncrease=0`; bootFired "1"; bootSide "server"; bootSet all
      four keys 0; bootDayLength "1" (the server's sandbox is loaded before OnGameBoot, doMinimumInit L1501-L1511);
      fileScopeDayLength not "1" (the file scope runs before the server's sandbox load); startedTable all seven 0.
      Falsifier: bootFired "0" on the server, or bootDayLength not "1".
  B   with the writer on, awake: every ring delta for admin and bob is exactly 0 for HUNGER and FATIGUE, and for
      THIRST unless an auto-drink sip is seen (THIRST below the post and the probe's container litres fell); every
      0.5 s server read equals the written float (0.3/0.2/0.1 to 1e-6). Falsifier: a non-zero hunger or fatigue
      delta, or a positive thirst delta (a rise: the zeroing did not land).
  B2  writer paused: HUNGER, THIRST, FATIGUE flat across B2_S (max - min <= 1e-7 each) while STRESS falls by
      3e-5 per game-second x the window's game-seconds within a factor of 2 (updateStats_Awake @0-@30 L10242).
      Vanilla's unzeroed rise over the same window would be about 9.6e-6 x 0.7, 8e-6 and 1.035e-5 per game-second,
      ~1e-2 each over ~30 game minutes, so flat is not trivial. Falsifier: any of the three rising.
  C   each pair's client value equals the server's (to 1e-6) for all three stats, admin and bob. Falsifier: a
      client value that differs in every pair (the write does not reach the owner).
  D   asleep (the hold's isAsleep true): HUNGER and THIRST ring deltas exactly 0; FATIGUE deltas <= 0 with at least
      one < 0 (vanilla's sleep recovery, IsoPlayer.updateStats_Sleeping @368/@403, is literals, not a ZomboidGlobals
      rate), each |dF| <= 2e-3 per game minute; the writer restores 0.1 each minute. Falsifier: a hunger or thirst
      rise asleep. Unmeasured if the asleep reads are not true.
  E   at settimespeed E_SPEED, awake: HUNGER and FATIGUE deltas exactly 0, THIRST as in B; ring rows keep pace with
      minutes (one row per player per EveryOneMinute). Falsifier: a non-zero hunger or fatigue delta.
  F   benchSet below 20 us per call (one minute's three-stat write cheaper than one takeover tick, ~20 us per player
      per tick, x222); benchGetSet below 40 us. Falsifier: either at or above 125 us (the takeover's per-minute
      cost at DayLength 1, 20 x 6.27).
  Z   no probe error line, writeErrors "0", admin not parked.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
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

PROFILE = "x22-globals"
PREFIX = "x221"
SESSION = ("Plan 10 Task S1: the zeroed-drains alternative to the takeover -- the ZomboidGlobals hunger, thirst and "
           "fatigue rise rates zeroed before ZomboidGlobals.Load (thirst at file scope, hunger and fatigue in the "
           "server's OnGameBoot) and a per-minute server write of HUNGER 0.3, THIRST 0.2, FATIGUE 0.1; awake, paused, "
           "client sync, asleep, high time speed and the write's cost; one boot of " + PROFILE)
ARTIFACT = "globals.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROBE_DIR = "testing/experiments/TKX_GlobalsProbe"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
GP = "TKX_GP"
TARGET = {"hunger": 0.3, "thirst": 0.2, "fatigue": 0.1}
FLOAT_TOL = 1e-6
FLAT_TOL = 1e-7
B_S = 30.0
B_DT_S = 0.5
B2_S = 20.0
STRESS_SET = 0.5
STRESS_RATE = 3.0e-5          # StressDecrease per game-second (defines.lua:21; updateStats_Awake @0-@30 L10242)
C_PAIRS = 5
C_GAP_S = 1.0
D_HOLD_S = 75
D_S = 60.0
DF_MAX = 2.0e-3
E_SPEED = 30
E_S = 30.0
F_NOOP_N = 100000
F_N = 10000
F_MIN_N = 2000
F_REPEAT = 3
SET_BAND_US = 20.0
GETSET_BAND_US = 40.0
TAKEOVER_MIN_US = 125.0       # 20 us per player per tick (x222) x 6.27 ticks per game minute at DayLength 1
RING_PAGE = 30
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
LOG_RX = re.compile(r"TKX_GlobalsProbe|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
PROBE_ERR_RX = re.compile(r"TKX_GlobalsProbe\.lua")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


PRED = {
    "A": {"fileScope": "ThirstIncrease=0;ThirstSleepingIncrease=0", "bootFired": "1", "bootSide": "server",
          "bootSet": "HungerIncrease=0;HungerIncreaseWhileAsleep=0;HungerIncreaseWhenExercise=0;FatigueIncrease=0",
          "bootDayLength": "1", "fileScopeDayLength": "not 1", "startedTable": "all seven keys 0"},
    "B": {"ring deltas awake": "hunger 0 and fatigue 0 exactly; thirst 0 unless an auto-drink sip",
          "server reads": f"equal to the written float within {FLOAT_TOL}"},
    "B2": {"hunger, thirst, fatigue": f"flat (max - min <= {FLAT_TOL})",
           "stress fall": f"{STRESS_RATE} x game-seconds within a factor of 2"},
    "C": {"client vs server": f"equal within {FLOAT_TOL} in every pair, admin and bob"},
    "D": {"asleep": True, "hunger, thirst deltas": 0, "fatigue deltas": f"<= 0, at least one < 0, |dF| <= {DF_MAX}"},
    "E": {"ring deltas awake": "hunger 0 and fatigue 0 exactly; thirst as in B", "rows per minute": "one per player"},
    "F": {"benchSet us per call": f"< {SET_BAND_US}", "benchGetSet us per call": f"< {GETSET_BAND_US}",
          "falsifier": f">= {TAKEOVER_MIN_US}"},
    "Z": {"probe_error": "none", "writeErrors": "0", "admin_lua_error": False},
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
    "meta": {"desk": ".superpowers/sdd/2026-10-07-plan-10-spikes-and-refactor/task-S1-desk.md (uncommitted)",
             "routes": {"file scope": ["ThirstIncrease", "ThirstSleepingIncrease"],
                        "OnGameBoot": ["HungerIncrease", "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise",
                                       "FatigueIncrease"]},
             "targets": TARGET,
             "ring_row": "seq|minute|user|asleep|preH,preT,preF|postH,postT,postF|dH,dT,dF|worldAgeH|ms"},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The plan says to apply the reachable route at the earliest event the jar read allows (file scope). The probe "
        "splits the keys across both reachable routes -- thirst at file scope, hunger and fatigue in the server's "
        "OnGameBoot -- because a mod that chooses the route from a sandbox option can only do so in OnGameBoot (the "
        "server's sandbox is loaded after the file scopes); each key group's drift witnesses its own route.",
        "Phase B2 (the writer paused) is added to the plan's phases: it reads the zeroed rates without the writer.",
        "The cost arm (F, the amendments' Question 7) times the write with bench.global over one player's hoisted "
        "stats object; the vanilla update's own cost is not measurable here (the server's 10-tick lock, x222).",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}


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
    """One stats.get: the three stats, asleep, worldAge, mult and the bracketing walls."""
    args = user if side == SRV else ""
    a = keep(step(tag, side, "stats.get", args))
    return {k: a.get(k) for k in ("hunger", "thirst", "fatigue", "endurance", "asleep", "worldAge", "mult", "wall",
                                  "wall_after", "side", "raw", "error")}


def poll_reads(user, seconds, dt, tag):
    rows, end = [], time.time() + seconds
    while time.time() < end:
        t_next = time.time() + dt
        rows.append(sread(SRV, user, tag))
        rest = t_next - time.time()
        if rest > 0:
            time.sleep(rest)
    return rows


def parse_ring(text):
    rows = []
    if not isinstance(text, str) or not text:
        return rows
    for ln in text.split("\n"):
        f = ln.split("|")
        if len(f) != 9:
            if ln:
                rows.append({"raw": ln})
            continue
        pre = [num(x) for x in f[4].split(",")]
        post = [num(x) for x in f[5].split(",")]
        d = [num(x) for x in f[6].split(",")] if f[6] != "na" else [None, None, None]
        rows.append({"seq": num(f[0]), "minute": num(f[1]), "user": f[2], "asleep": f[3] == "true",
                     "pre": pre, "post": post, "d": d, "age": num(f[7]), "ms": num(f[8])})
    return rows


def ring_since(seq0, tag):
    """Every ring row after seq0, paged RING_PAGE rows per call."""
    rows, lo, total = [], (int(seq0) if seq0 is not None else 0) + 1, None
    for _ in range(40):
        r = lcall(SRV, f"{GP}.ringText", f"{tag}_ring{lo}", lo, lo + RING_PAGE - 1)
        total = num(r.get("r2"))
        rows.extend(parse_ring(r.get("r1")))
        if total is None or lo + RING_PAGE - 1 >= total:
            break
        lo += RING_PAGE
    return {"seq_end": total, "rows": rows}


def seq_now(tag):
    r = lcall(SRV, f"{GP}.aggText", f"{tag}_seq")
    return num(r.get("r2")), num(r.get("r3"))


def agg(tag):
    r = lcall(SRV, f"{GP}.aggText", f"{tag}_agg")
    d = {}
    if isinstance(r.get("r1"), str):
        for part in r["r1"].split(";"):
            if ":" not in part:
                continue
            u, rest = part.split(":", 1)
            d[u] = {k: num(v) for k, v in (kv.split("=", 1) for kv in rest.split(",") if "=" in kv)}
    return {"text": r.get("r1"), "seq": r.get("r2"), "minutes": r.get("r3"), "by_user": d}


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
G_FIELDS = ("version", "side", "fileScope", "fileScopeAt", "fileScopeDayLength", "bootFired", "bootAt", "bootSide",
            "bootSet", "bootDayLength", "bootTableBefore", "startedTable", "startedAt", "minutes", "writes",
            "writeErrors", "lastErr", "on", "targets")


def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = keep(step("S0_time", SRV, "time.snapshot"))
    P["autodrink"] = {u: keep(step(f"S0_autodrink_{u}", SRV, "autodrink.probe", u)) for u in ("admin", "bob")}
    P["stats_all"] = keep(step("S0_stats_all", SRV, "stats.all", "admin"))
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in (ADMIN, BOB)}


def phase_A():
    P = out["phases"]["A"] = {}
    P["server"] = {f: gread(SRV, f"TKX_G.{f}", f"A_srv_{f}") for f in G_FIELDS}
    P["admin"] = {f: gread(ADMIN, f"TKX_G.{f}", f"A_adm_{f}")
                  for f in ("side", "fileScope", "fileScopeDayLength", "bootFired", "bootSide", "bootSet",
                            "bootDayLength", "startedTable")}


def phase_B():
    P = out["phases"]["B"] = {}
    P["reset"] = lcall(SRV, f"{GP}.resetAgg", "B_reset")
    P["seq0"], P["min0"] = seq_now("B0")
    P["time0"] = keep(step("B_time0", SRV, "time.snapshot"))
    P["reads"] = poll_reads("admin", B_S, B_DT_S, "B_read")
    P["time1"] = keep(step("B_time1", SRV, "time.snapshot"))
    P["agg"] = agg("B")
    P["ring"] = ring_since(P["seq0"], "B")
    P["autodrink_after"] = {u: keep(step(f"B_autodrink_{u}", SRV, "autodrink.probe", u)) for u in ("admin", "bob")}


def phase_B2():
    P = out["phases"]["B2"] = {}
    P["pause"] = keep(step("B2_pause", SRV, "lua.setpath", f"{GP}.on false"))
    try:
        time.sleep(1.5)
        P["stress_set"] = keep(step("B2_stress", SRV, "stats.setany", f"admin STRESS {STRESS_SET}"))
        P["all0"] = keep(step("B2_all0", SRV, "stats.all", "admin"))
        P["reads"] = poll_reads("admin", B2_S, 1.0, "B2_read")
        P["all1"] = keep(step("B2_all1", SRV, "stats.all", "admin"))
        P["bob"] = sread(SRV, "bob", "B2_bob")
    finally:
        P["resume"] = keep(step("B2_resume", SRV, "lua.setpath", f"{GP}.on true"))
        out["world_changes"]["writer"] = "paused for B2, resumed after"
    P["on"] = gread(SRV, "TKX_G.on", "B2_on")


def phase_C():
    P = out["phases"]["C"] = {}
    time.sleep(2.0)
    for u, side in (("admin", ADMIN), ("bob", BOB)):
        pairs = []
        for i in range(C_PAIRS):
            c = sread(side, u, f"C_{u}_client_{i}")
            s = sread(SRV, u, f"C_{u}_server_{i}")
            pairs.append({"client": c, "server": s})
            time.sleep(C_GAP_S)
        P[u] = pairs


def phase_D():
    P = out["phases"]["D"] = {}
    P["reset"] = lcall(SRV, f"{GP}.resetAgg", "D_reset")
    P["all0"] = keep(step("D_all0", SRV, "stats.all", "admin"))
    P["hold"] = keep(step("D_hold", SRV, "player.sleep.hold", f"admin {D_HOLD_S}"))
    try:
        time.sleep(2.0)
        P["seq0"], P["min0"] = seq_now("D0")
        P["time0"] = keep(step("D_time0", SRV, "time.snapshot"))
        half = poll_reads("admin", D_S / 2.0, 1.0, "D_read")
        mid = {"client": sread(ADMIN, "admin", "D_mid_client"), "server": sread(SRV, "admin", "D_mid_server")}
        rest = poll_reads("admin", D_S / 2.0, 1.0, "D_read")
        P["reads"] = half + rest
        P["mid_pair"] = mid
        P["time1"] = keep(step("D_time1", SRV, "time.snapshot"))
        P["agg"] = agg("D")
        P["ring"] = ring_since(P["seq0"], "D")
        P["all1"] = keep(step("D_all1", SRV, "stats.all", "admin"))
    finally:
        P["cancel"] = keep(step("D_cancel", SRV, "player.sleep.hold", "admin 0"))
        P["wake"] = keep(step("D_wake", SRV, "player.sleep", "admin false"))
        out["world_changes"]["sleep"] = "admin's hold cancelled and admin set awake after D"
    time.sleep(2.0)
    P["after"] = sread(SRV, "admin", "D_after")


def phase_E():
    P = out["phases"]["E"] = {}
    P["reset"] = lcall(SRV, f"{GP}.resetAgg", "E_reset")
    P["seq0"], P["min0"] = seq_now("E0")
    P["time0"] = keep(step("E_time0", SRV, "time.snapshot"))
    P["speed"] = rcon(f"settimespeed {E_SPEED}", "E_speed")
    try:
        P["time_fast"] = keep(step("E_time_fast", SRV, "time.snapshot"))
        P["reads"] = poll_reads("admin", E_S, B_DT_S, "E_read")
        P["time1"] = keep(step("E_time1", SRV, "time.snapshot"))
    finally:
        P["restore"] = rcon("settimespeed 1", "E_restore")
        out["world_changes"]["settimespeed"] = "restored to 1 after E"
    P["agg"] = agg("E")
    P["seq1"], P["min1"] = seq_now("E1")
    P["ring"] = ring_since(max(P["seq0"] or 0, (P["seq1"] or 0) - 200), "E")
    P["time2"] = keep(step("E_time2", SRV, "time.snapshot"))


def phase_F():
    P = out["phases"]["F"] = {}
    P["pick"] = lcall(SRV, f"{GP}.benchPick", "F_pick", "admin")
    rows = {"noop": [], "set": [], "getset": [], "minute": []}
    rows["noop"].append(keep(step("F_noop", SRV, "bench.global", f"{GP}.benchNoop {F_NOOP_N}", timeout=60)))
    for i in range(F_REPEAT):
        rows["set"].append(keep(step(f"F_set_{i}", SRV, "bench.global", f"{GP}.benchSet {F_N}", timeout=60)))
    for i in range(F_REPEAT):
        rows["getset"].append(keep(step(f"F_getset_{i}", SRV, "bench.global", f"{GP}.benchGetSet {F_N}", timeout=60)))
    rows["minute"].append(keep(step("F_minute", SRV, "bench.global", f"{GP}.benchMinute {F_MIN_N}", timeout=60)))
    P["bench"] = rows
    P["reset"] = lcall(SRV, f"{GP}.resetAgg", "F_reset")


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_probe_error_lines"] = [e[:400] for e in errs if PROBE_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["writeErrors"] = gread(SRV, "TKX_G.writeErrors", "Z_writeErrors")
    P["lastErr"] = gread(SRV, "TKX_G.lastErr", "Z_lastErr")
    P["minutes"] = gread(SRV, "TKX_G.minutes", "Z_minutes")
    P["writes"] = gread(SRV, "TKX_G.writes", "Z_writes")
    P["admin_parked"] = parked()


def body():
    order = (("S0", phase_S0), ("A", phase_A), ("B", phase_B), ("B2", phase_B2), ("C", phase_C), ("D", phase_D),
             ("E", phase_E), ("F", phase_F), ("Z", phase_Z))
    for name, fn in order:
        run_phase(name, fn)
        if parked() and name != "Z":
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return


def read_logs(every):
    L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "probe": PROBE_ERR_RX.pattern,
                                    "echo_excluded": ECHO_RX.pattern}, "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        probe, probe_echo = grep_noecho(server.log_path, PROBE_ERR_RX, LOG_LIMIT)
        L["server"] = {"lines": raw, "echo_lines_excluded": echoed, "probe_lines": probe,
                       "probe_echo_excluded": probe_echo}
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


def ring_summary(rows, users=("admin", "bob")):
    """Per user: rows, rows with a delta, the max |d| per stat and the thirst deltas' signs; asleep split."""
    s = {}
    for u in users:
        mine = [r for r in rows if r.get("user") == u and r.get("d") and r["d"][0] is not None]
        for state, part in (("awake", [r for r in mine if not r["asleep"]]), ("asleep", [r for r in mine if r["asleep"]])):
            if not part:
                continue
            dh = [r["d"][0] for r in part]
            dt = [r["d"][1] for r in part]
            df = [r["d"][2] for r in part]
            posts = [r["post"] for r in part]
            s.setdefault(u, {})[state] = {
                "n": len(part), "max_abs_dH": max(abs(x) for x in dh), "max_abs_dT": max(abs(x) for x in dt),
                "max_abs_dF": max(abs(x) for x in df), "dT_pos": sum(1 for x in dt if x > 0),
                "dT_neg": sum(1 for x in dt if x < 0), "dF_neg": sum(1 for x in df if x < 0),
                "dF_pos": sum(1 for x in df if x > 0), "dF_min": min(df), "dF_max": max(df),
                "dF_mean": sum(df) / len(df), "minutes": sorted(set(r["minute"] for r in part if r["minute"] is not None)),
                "posts_distinct": sorted({tuple(p) for p in posts if None not in p})[:5]}
            s[u][state]["minutes"] = [s[u][state]["minutes"][0], s[u][state]["minutes"][-1],
                                      len(s[u][state]["minutes"])] if s[u][state]["minutes"] else []
    return s


def reads_summary(reads):
    out_ = {}
    for k in ("hunger", "thirst", "fatigue"):
        vs = [num(r.get(k)) for r in reads if num(r.get(k)) is not None]
        if vs:
            out_[k] = {"n": len(vs), "min": min(vs), "max": max(vs), "span": max(vs) - min(vs),
                       "max_dev_target": max(abs(v - TARGET[k]) for v in vs)}
    asl = [r.get("asleep") for r in reads]
    out_["asleep_true"] = sum(1 for a in asl if a is True or str(a).lower() == "true")
    out_["n"] = len(reads)
    ages = [num(r.get("worldAge")) for r in reads if num(r.get("worldAge")) is not None]
    if len(ages) >= 2:
        out_["worldAge_span_h"] = ages[-1] - ages[0]
    return out_


def grade_all():
    ph = out["phases"]
    A = ph.get("A") or {}
    if A:
        sv = {f: val(A["server"].get(f)) for f in A.get("server", {})}
        zero7 = all(x.endswith("=0") or x.endswith("=0.0") for x in str(sv.get("startedTable") or "").split(";")) \
            and str(sv.get("startedTable") or "").count("=") == 7
        obs = {"server": sv, "admin": {f: val(r) for f, r in (A.get("admin") or {}).items()}}
        if sv.get("bootFired") in (None, "0") or sv.get("bootSide") != "server":
            grade("A", PRED["A"], obs, "falsified" if sv.get("bootFired") == "0" else "unmeasured",
                  "bootFired 0 on the server, or bootDayLength not 1")
        else:
            ok = (str(sv.get("bootDayLength")) == "1" and str(sv.get("fileScopeDayLength")) != "1" and zero7
                  and "=0" in str(sv.get("fileScope")) and str(sv.get("bootSet")).count("=0") == 4)
            grade("A", PRED["A"], obs, "as_predicted" if ok else "falsified",
                  "bootFired 0 on the server, or bootDayLength not 1",
                  {"note": "the Lua table reads are a mirror; the drift in B, B2, D and E is the Java-side witness"})
    else:
        grade("A", PRED["A"], None, "unmeasured", "phase A not run")

    B = ph.get("B") or {}
    rs = ring_summary(g(B, "ring", "rows") or [])
    if rs:
        aw = {u: rs[u].get("awake") for u in rs}
        obs = {"ring": rs, "reads": reads_summary(B.get("reads") or []), "agg": g(B, "agg", "by_user"),
               "autodrink_before": {u: {k: g(ph, "S0", "autodrink", u, k) for k in ("thirst", "litres", "item", "autoDrink")}
                                    for u in ("admin", "bob")},
               "autodrink_after": {u: {k: g(B, "autodrink_after", u, k) for k in ("thirst", "litres", "item", "autoDrink")}
                                   for u in ("admin", "bob")}}
        ok_hf = all(a and a["max_abs_dH"] == 0 and a["max_abs_dF"] == 0 for a in aw.values())
        no_rise = all(a and a["dT_pos"] == 0 for a in aw.values())
        rd = obs["reads"]
        reads_ok = all(rd.get(k, {}).get("max_dev_target", 1) <= FLOAT_TOL for k in ("hunger", "fatigue"))
        verdict = "as_predicted" if (ok_hf and no_rise and reads_ok) else "falsified"
        grade("B", PRED["B"], obs, verdict, "a non-zero hunger or fatigue delta, or a positive thirst delta",
              {"note": "thirst falls (dT_neg) are read against the auto-drink probe's litres before and after"})
    else:
        grade("B", PRED["B"], None, "unmeasured", "no ring rows")

    B2 = ph.get("B2") or {}
    rd2 = reads_summary(B2.get("reads") or [])
    if rd2.get("n"):
        s0 = num(g(B2, "all0", "stats", "Stress"))
        s1 = num(g(B2, "all1", "stats", "Stress"))
        a0, a1 = num(g(B2, "all0", "worldAge")), num(g(B2, "all1", "worldAge"))
        game_s = (a1 - a0) * 3600.0 if None not in (a0, a1) else None
        pred_fall = STRESS_RATE * game_s if game_s is not None else None
        fall = (s0 - s1) if None not in (s0, s1) else None
        flat = all(rd2.get(k, {}).get("span", 1) <= FLAT_TOL for k in ("hunger", "thirst", "fatigue"))
        obs = {"reads": rd2, "stress0": s0, "stress1": s1, "stress_fall": fall, "game_seconds": game_s,
               "predicted_fall": pred_fall, "all0": g(B2, "all0", "stats"), "all1": g(B2, "all1", "stats"),
               "stress_set": B2.get("stress_set"), "pause": B2.get("pause"), "resume": B2.get("resume")}
        stress_ok = (fall is not None and pred_fall and pred_fall / 2 <= fall <= pred_fall * 2)
        if flat and stress_ok:
            v = "as_predicted"
        elif not flat:
            v = "falsified"
        else:
            v = "falsified"
        grade("B2", PRED["B2"], obs, v, "any of the three rising (or the stress witness outside its band)")
    else:
        grade("B2", PRED["B2"], None, "unmeasured", "no B2 reads")

    C = ph.get("C") or {}
    if C:
        res, all_ok, any_pair = {}, True, False
        for u in ("admin", "bob"):
            rows = []
            for p in C.get(u) or []:
                c, s = p.get("client") or {}, p.get("server") or {}
                d = {}
                for k in ("hunger", "thirst", "fatigue"):
                    cv, sv_ = num(c.get(k)), num(s.get(k))
                    d[k] = (cv - sv_) if None not in (cv, sv_) else None
                rows.append({"client": {k: c.get(k) for k in ("hunger", "thirst", "fatigue", "wall")},
                             "server": {k: s.get(k) for k in ("hunger", "thirst", "fatigue", "wall")}, "diff": d})
                if all(v is not None for v in d.values()):
                    any_pair = True
                    if any(abs(v) > FLOAT_TOL for v in d.values()):
                        all_ok = False
            res[u] = rows
        if not any_pair:
            grade("C", PRED["C"], res, "unmeasured", "no complete pair")
        else:
            grade("C", PRED["C"], res, "as_predicted" if all_ok else "falsified",
                  "a client value that differs in every pair",
                  {"note": "a difference in some pairs only is a lag reading, recorded as falsified against the "
                           "every-pair prediction and read by hand"})
    else:
        grade("C", PRED["C"], None, "unmeasured", "phase C not run")

    D = ph.get("D") or {}
    rsD = ring_summary(g(D, "ring", "rows") or [], users=("admin",))
    rdD = reads_summary(D.get("reads") or [])
    if D:
        sl = g(rsD, "admin", "asleep")
        obs = {"ring": rsD, "reads": rdD, "mid_pair": D.get("mid_pair"), "agg": g(D, "agg", "by_user"),
               "all0": g(D, "all0", "stats"), "all1": g(D, "all1", "stats"), "hold": D.get("hold"),
               "after": D.get("after")}
        if not sl or not rdD.get("asleep_true"):
            grade("D", PRED["D"], obs, "unmeasured", "the asleep reads were not true")
        else:
            ok = (sl["max_abs_dH"] == 0 and sl["dT_pos"] == 0 and sl["max_abs_dT"] == 0 and sl["dF_pos"] == 0
                  and sl["dF_neg"] >= 1 and abs(sl["dF_min"]) <= DF_MAX)
            grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified", "a hunger or thirst rise asleep")
    else:
        grade("D", PRED["D"], None, "unmeasured", "phase D not run")

    E = ph.get("E") or {}
    rsE = ring_summary(g(E, "ring", "rows") or [])
    if rsE:
        aw = {u: rsE[u].get("awake") for u in rsE}
        obs = {"ring": rsE, "reads": reads_summary(E.get("reads") or []), "agg": g(E, "agg", "by_user"),
               "minutes": (E.get("min0"), E.get("min1")), "seq": (E.get("seq0"), E.get("seq1")),
               "mult_fast": g(E, "time_fast", "mult"), "speed_ack": E.get("speed"), "restore_ack": E.get("restore"),
               "mult_after": g(E, "time2", "mult")}
        ok = all(a and a["max_abs_dH"] == 0 and a["max_abs_dF"] == 0 and a["dT_pos"] == 0 for a in aw.values())
        grade("E", PRED["E"], obs, "as_predicted" if ok else "falsified", "a non-zero hunger or fatigue delta")
    else:
        grade("E", PRED["E"], None, "unmeasured", "no ring rows")

    F = ph.get("F") or {}
    if F:
        bench = F.get("bench") or {}
        us = {k: [num(r.get("usPerCall")) for r in bench.get(k) or [] if not r.get("error")] for k in bench}
        obs = {"usPerCall": us, "errors": {k: [r.get("error") for r in bench.get(k) or [] if r.get("error")]
                                           for k in bench}, "pick": F.get("pick"),
               "ms": {k: [r.get("ms") for r in bench.get(k) or []] for k in bench}}
        sets, gs = [x for x in us.get("set") or [] if x is not None], [x for x in us.get("getset") or [] if x is not None]
        if not sets or not gs:
            grade("F", PRED["F"], obs, "unmeasured", "no bench reading")
        else:
            ms = max(sets)
            mg = max(gs)
            if ms >= TAKEOVER_MIN_US or mg >= TAKEOVER_MIN_US:
                v = "falsified"
            elif ms < SET_BAND_US and mg < GETSET_BAND_US:
                v = "as_predicted"
            else:
                v = "falsified"
            grade("F", PRED["F"], obs, v, f">= {TAKEOVER_MIN_US} us per call",
                  {"note": "a figure between the band and the falsifier is recorded as falsified against the band"})
    else:
        grade("F", PRED["F"], None, "unmeasured", "phase F not run")

    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_probe_error_lines": Z.get("server_probe_error_lines") or [],
               "writeErrors": val(Z.get("writeErrors")), "lastErr": val(Z.get("lastErr")),
               "minutes": val(Z.get("minutes")), "writes": val(Z.get("writes")),
               "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_probe_error_lines"] and str(obs["writeErrors"]) == "0" and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a probe error line, writeErrors, admin parked")
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
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
