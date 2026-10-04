"""x131-calcrepro -- X34 with X35, X32 and X46 riding: the takeover handler's live verification.

The run id prefix is `x131c` (run id `x131c-<date>-<time>`): the register's run-id pattern
(a lowercase alphanumeric prefix, then eight and six digits) refuses a hyphen in the prefix, so `x131-calcrepro-<id>` could not be
named by a `run:` pointer. A first launch under that prefix was stopped while boot A's client was
still joining, before any reading was taken; its run dir is not evidence.

Plan 1 Task 11. Copied from `_template.py` (house shape) and from the acceptance drivers
`x131_accept.py` / `x131_accept_b.py` (the probe and step wrappers, the trace regex). ONE live
session of THREE boots, each on a fresh run sub-directory restored from the golden fixture, each
torn down before the next, all at `DayLength = 1` (a game-hour is 37.5 s wall at time speed 1;
the speed is never changed):

  A  `nr-overlay`    the control: the mod loaded in overlay mode, nothing registered on the hook,
                     so vanilla's seven updaters run. `NutritionRevamp.server.fast.registered`
                     must read false.
  B  `nr-takeover`   the takeover handler registered (`registered` true) and reproducing the seven
                     updaters. X35 rides this boot after its eighth sample.
  C  `x13-calcstats` the probe mod TKX_CalcStats: X32 (a no-op registrant) and X46 (a second
                     registrant), key-driven arms.

Schedule of A and B (segment k runs from sample t(k-1) to sample t(k); t0 is taken at the first
whole game-hour on the clock after the session is ready, so A's and B's samples fall at the same
clock hours when the two boots take similar time):

  segments 1-3 idle standing (`player.stop` before t0)
  segment  4   running: client `player.walk 40 0 run`, re-issued in the opposite direction
               whenever the client reads not moving, then `player.stop` just before t4
  segments 5-6 asleep: server `player.sleep admin true` after t4, `player.sleep admin false`
               after t6
  segments 7-8 idle standing

At every sample: `time.snapshot` polls until the world age reaches the target (the hour boundary
is DETECTED, never slept), then server `stats.all admin` (the graded read; `field_count` 24 stats
and an empty `missing` list asserted), server `stats.get admin` (asleep / running / calories /
moodles), and `lua.global NutritionRevamp.server.fast.stats.failures`, `...stats.disabledAt`,
`...fast.lastError`. Every read is wall-bracketed.

Deviation from the brief, decided before the run: X35's sentinel window sits AFTER B's eighth
sample (in a ninth idle stretch) rather than inside the eighth hour, so that X34's eighth-hour
endurance is not overwritten by the sentinel. A runs the same pair reads in the same place with no
sentinel (the off-arm control and the cross-side skew at rest). The C arms run 20 s wall each
(about 32 game-minutes, above the brief's three game-minutes), because a server read costs about
1.3 s wall (2 game-minutes) and three game-minutes would hold two reads.

PREDICTIONS AND FALSIFIERS (written before the run):

  X34 (#2081). For hunger, thirst, fatigue, stress, anger, idleness, morale, fitness and endurance,
      B's per-segment rate (delta over the segment divided by the segment's own world-age span,
      i.e. per game-hour) tracks A's within a per-stat band `max(2 % of |A's rate|, 1e-4)` per
      game-hour; morale and fitness are graded on EXACT level equality at every sample while A's
      level does not move (the band is used if it does); the asleep fatigue is graded on segment 6
      only (the sleep-delay mirror, ruling 7, makes segment 5 differ). Boredom, unhappiness, panic,
      discomfort and temperature are recorded, not graded. Falsifier: any graded stat outside its
      band in two consecutive segments; B's `failures` above 0 at any sample; `disabledAt`
      non-nil. A stat flat in both arms is `trivial`, never `as_predicted`. The stress arm is the
      first measurement of the stress terms (#2220): A's stress per segment is written down as
      vanilla's measured rate beside B's.
  X35 (#2082). With `NR_sentinel` = 1 the server's endurance reads 0.4242 once the slow clock
      reads the key; then ten client-first resting pairs and six running pairs (client
      `stats.get` then server `stats.get admin`, >= 1 s apart): the client's endurance reads
      0.4242 +- 1e-6 at every pair (the push carries the handler's write). Falsifier: any pair
      outside the post-push window whose client value differs from 0.4242 by more than 1e-6 (the
      running pairs are the discriminating half; a resting-only agreement is `trivial`).
      `sentinelCalls` server > 0, client 0. Off-arm control: after `NR_sentinel` = 0 the client's
      endurance leaves 0.4242 within the four following pairs (the client reads are live mirrors).
  X32 (#2100). C arm `calc` (`TKX_calc` = 1): thirst frozen, |delta| <= 1e-6 over the arm while
      the calorie store still moves (the macro drain runs: `Nutrition.update` is not among the
      seven); `none` arms before and after: thirst rises at the vanilla awake rate 8.0e-6 per
      game-second (#0476) within +-10 %, fitted against `stats.all`'s own world age.
      `TKX_CalcStats.calls` rises on the server during the calc arm and reads 0 on the client at
      every read (the hook never fires on a client, #2236) -- a client count above 0 is the
      finding. Falsifier: thirst moving under `calc`, or frozen under `none`.
  X46 (#2086). A alone: frozen (positive control). A+B: frozen and callsA ~ callsB (increments
      within 10 % or 3 calls). B alone, returning false: frozen and callsB rising with callsA flat
      -- a thaw falsifies #2238/#2240 and would change the takeover ruling. Neither: thaw (the
      negative control).

What follows is the template's own docstring, kept as the house shape this driver obeys.

The driver template -- copy it, do not run it as it stands.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_...`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
"""
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

from _common import ask, doctor, git_dirty, git_say, hard_kill, num   # noqa: E402
from pzt import fixture as fx, profile                                # noqa: E402
from pzt.paths import new_run_dir                                     # noqa: E402
from pzt.session import (Timeline, make_client, make_server,         # noqa: E402
                         teardown, verify)

PROFILES = {"A": "nr-overlay", "B": "nr-takeover", "C": "x13-calcstats"}
SESSION = ("X34 + X35 + X32 + X46: the Hook.CalculateStats takeover handler against vanilla's "
           "seven updaters over 8 game-hours (A overlay control, B takeover, X35 sentinel in B), "
           "then the TKX_CalcStats registrant arms (C)")
ARTIFACT = "calcrepro.json"
USER = "admin"
ACCEPTANCE_RUN = "x131b-20261004-175911"

# ---- constants ------------------------------------------------------------------------------
STAT_FIELD_COUNT = 24                  # TK.STAT_REGISTRY rows
GAME_HOUR_WALL_S = 37.5                # DayLength 1: 24 game-hours in 900 s
HOURS = 8
SEGMENTS = {1: "idle", 2: "idle", 3: "idle", 4: "run", 5: "asleep", 6: "asleep", 7: "idle", 8: "idle"}
GRADED = ["Hunger", "Thirst", "Fatigue", "Stress", "Anger", "Idleness", "Morale", "Fitness",
          "Endurance"]
EXACT = ("Morale", "Fitness")
RECORDED = ["Boredom", "Unhappiness", "Panic", "Discomfort", "Temperature"]
BAND_FRAC, BAND_FLOOR = 0.02, 1e-4     # per game-hour
FLAT = 1e-7                            # a level change at or below this is "did not move"
WALK_DX = 40
SENTINEL, SENT_TOL = 0.4242, 1e-6
X35_REST_PAIRS, X35_RUN_PAIRS, X35_OFF_PAIRS = 10, 6, 4
PAIR_GAP_S = 1.0
THIRST_PER_GAME_SECOND = 8.0e-6        # #0476
THAW_BAND = 0.10
FREEZE_TOL = 1e-6
ARM_WALL_S = 20.0
C_MIN_AFTER_READY_S = 40.0             # the server copy of player modData settles ~30 s after join
LOG_LIMIT = 40
TRACE_LIMIT = 40
NR_RX = re.compile(re.escape("[NutritionRevamp]"))
TRACE_RX = re.compile(r"Lua\(\(MOD:Nutrition ?Revamp\)\)|Lua\(\(MOD:[^)]*\)\)\.\w+\((?:NR_|NutritionRevamp|TKX_)"
                      r"|Lua\(\(MOD:TKX[^)]*\)\)")
STACK_RX = re.compile(r"STACK TRACE")
FAST = "NutritionRevamp.server.fast"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "boot": cur.get("label"), "note": msg})


def persist():
    """Write the artifact (never raises): the timeline and each boot's server error list."""
    try:
        out["timeline"] = list(tl.items)
        for label, srv in servers.items():
            if srv is not None:
                out["boots"][label]["server_errors"] = srv.errors[:20]
                out["boots"][label]["server_error_count"] = len(srv.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - teardown path, never raise
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30, keep=True):
    """One sequenced bus call with its own wall bracket; recorded in the current boot."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "wall_before": t_before, "wall_after": t_after, "took": round(t_after - t_before, 3),
           "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    if keep:
        cur["B"]["steps"].append(row)
    return row


def gv(r):
    a = r["ack"] if isinstance(r, dict) and "ack" in r else r
    return a.get("value") if isinstance(a, dict) else None


def answered(r):
    a = r["ack"] if isinstance(r, dict) and "ack" in r else r
    return isinstance(a, dict) and "resolved" in a


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def grep_numbered(path_, rx, limit):
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:240]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                       # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def stats_of(row):
    a = row["ack"] if isinstance(row, dict) else None
    return a if isinstance(a, dict) and isinstance(a.get("stats"), dict) else None


def fc_ok(s):
    return s is not None and len(s["stats"]) == STAT_FIELD_COUNT and not s.get("missing")


def sleep_until(target_wall):
    while wall() < target_wall:
        time.sleep(min(0.25, max(0.0, target_wall - wall())))


def wait_age(target, tag, cap_s=6.0):
    """Poll `time.snapshot` until the world age reaches `target` (hours). The sleep between polls
    is sized from the rate measured between the last two polls (the clock can run fast while the
    player sleeps) and capped. Returns the last snapshot row; every poll is kept."""
    polls, last = [], None
    deadline = wall() + 6 * GAME_HOUR_WALL_S
    rate = 1.0 / GAME_HOUR_WALL_S                       # game-hours per wall second
    while True:
        r = step(f"{tag}_poll", cur["server"], "time.snapshot", "", keep=False)
        a = r["ack"] if isinstance(r["ack"], dict) else {}
        age = num(a.get("worldAge"))
        polls.append({"wall": r["wall_before"], "worldAge": age, "hour": a.get("hour"),
                      "minutes": a.get("minutes"), "mult": a.get("mult")})
        if age is not None and last is not None and last[1] is not None and r["wall_before"] > last[0]:
            measured = (age - last[1]) / (r["wall_before"] - last[0])
            if measured > 0:
                rate = measured
        last = (r["wall_before"], age)
        if age is not None and age >= target:
            cur["B"]["polls"].append({"tag": tag, "target": target, "polls": polls})
            return r
        if wall() > deadline:
            cur["B"]["polls"].append({"tag": tag, "target": target, "polls": polls, "timeout": True})
            raise TimeoutError(f"world age never reached {target} for {tag}")
        remaining = (target - age) / rate if age is not None else 2.0
        time.sleep(max(0.2, min(remaining - 1.5, cap_s)))


def sample(k, target):
    """One hourly sample: the boundary detected, then the graded read and its companions."""
    ts = wait_age(target, f"t{k}", cap_s=1.0 if SEGMENTS.get(k + 1) == "asleep" or
                  SEGMENTS.get(k) == "asleep" else 6.0)
    srv = cur["server"]
    st = step(f"t{k}_stats_all", srv, "stats.all", USER)
    sg = step(f"t{k}_stats_get", srv, "stats.get", USER)
    fl = step(f"t{k}_failures", srv, "lua.global", FAST + ".stats.failures")
    da = step(f"t{k}_disabledAt", srv, "lua.global", FAST + ".stats.disabledAt")
    le = step(f"t{k}_lastError", srv, "lua.global", FAST + ".lastError")
    s = stats_of(st)
    g = sg["ack"] if isinstance(sg["ack"], dict) else {}
    row = {"k": k, "target_age": target, "segment_ending": SEGMENTS.get(k),
           "time_snapshot": ts["ack"], "wall": st["wall_before"],
           "worldAge": s.get("worldAge") if s else None, "mult": s.get("mult") if s else None,
           "stats": s["stats"] if s else None, "missing": s.get("missing") if s else None,
           "field_count_ok": fc_ok(s),
           "body": {key: g.get(key) for key in ("asleep", "running", "sprinting", "moving",
                                                 "calories", "endurance", "fatigue", "moodles",
                                                 "worldAge")},
           "failures": gv(fl), "disabledAt": da["ack"], "lastError": le["ack"]}
    cur["B"]["samples"].append(row)
    tl.mark("sample", boot=cur["label"], k=k, age=row["worldAge"])
    persist()
    return row


def run_segment(target, est_end_wall):
    """Segment 4: keep the client running until about 2 s before the boundary, then stop."""
    c = cur["client"]
    walks = cur["B"]["walks"]
    dx = WALK_DX
    r = step("run_walk_0", c, "player.walk", f"{dx} 0 run")
    walks.append({"wall": r["wall_before"], "dx": dx, "ack": r["ack"]})
    n = 0
    while wall() < est_end_wall - 2.5:
        time.sleep(2.0)
        g = step("run_check", c, "stats.get", "", keep=False)
        a = g["ack"] if isinstance(g["ack"], dict) else {}
        walks.append({"wall": g["wall_before"], "check": {key: a.get(key) for key in
                                                           ("moving", "running", "endurance")}})
        if a.get("moving") is False:
            dx = -dx
            n += 1
            r = step(f"run_walk_{n}", c, "player.walk", f"{dx} 0 run")
            walks.append({"wall": r["wall_before"], "dx": dx, "ack": r["ack"]})
    r = step("run_stop", c, "player.stop", "")
    walks.append({"wall": r["wall_before"], "stop": r["ack"]})


def hourly_body(label):
    """A and B: the eight-hour schedule."""
    srv, c, B = cur["server"], cur["client"], cur["B"]
    B["samples"], B["polls"], B["walks"] = [], [], []
    reg = step("registered", srv, "lua.global", FAST + ".registered")
    calls0 = step("calls_start", srv, "lua.global", FAST + ".stats.calls")
    miss = step("hoist_missing", srv, "lua.global", f"{FAST}.h.{USER}.missing")
    B["registered"] = gv(reg)
    B["registered_ack"] = reg["ack"]
    B["hoist_missing"] = miss["ack"]
    step("stop_t0", c, "player.stop", "")
    ts = step("t0_clock", srv, "time.snapshot", "")
    age_now = num(ts["ack"].get("worldAge")) if isinstance(ts["ack"], dict) else None
    if age_now is None:
        raise RuntimeError("time.snapshot carried no worldAge")
    base = math.ceil(age_now + 0.05)
    B["t0_target_age"] = base
    for k in range(0, HOURS + 1):
        target = base + k
        if k == 4:
            last = B["samples"][-1]
            est_end = last["wall"] + (target - (num(last["worldAge"]) or (target - 1))) * GAME_HOUR_WALL_S
            run_segment(target, est_end)
        sample(k, target)
        if k == 4:
            r = step("sleep_on", srv, "player.sleep", f"{USER} true")
            B["sleep_on"] = r["ack"]
        if k == 6:
            r = step("sleep_off", srv, "player.sleep", f"{USER} false")
            B["sleep_off"] = r["ack"]
    calls1 = step("calls_end", srv, "lua.global", FAST + ".stats.calls")
    B["calls"] = {"start": gv(calls0), "end": gv(calls1)}
    x35_window(label)


def pair(tag):
    c, srv = cur["client"], cur["server"]
    rc = step(f"{tag}_client", c, "stats.get", "")
    rs = step(f"{tag}_server", srv, "stats.get", USER)
    ac = rc["ack"] if isinstance(rc["ack"], dict) else {}
    as_ = rs["ack"] if isinstance(rs["ack"], dict) else {}
    return {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
            "skew_s": round(rs["wall_before"] - rc["wall_before"], 3),
            "client": {key: ac.get(key) for key in ("endurance", "running", "moving", "asleep", "worldAge")},
            "server": {key: as_.get(key) for key in ("endurance", "running", "moving", "asleep", "worldAge")}}


def pairs(tag, n, bucket):
    last = None
    for i in range(n):
        if last is not None:
            sleep_until(last + PAIR_GAP_S)
        p = pair(f"{tag}{i}")
        last = p["client_wall"]
        bucket.append(p)
        persist()


def x35_window(label):
    """B: the sentinel window after t8. A: the same reads with no sentinel (control)."""
    srv, c = cur["server"], cur["client"]
    X = cur["B"]["x35"] = {"rest": [], "run": [], "off": [], "arrival": []}
    if label == "B":
        r = step("x35_set_on", srv, "moddata.set", f"{USER} NR_sentinel 1")
        X["set_on"] = {"wall": r["wall_before"], "ack": r["ack"]}
        deadline = wall() + 20.0
        while wall() < deadline:
            g = step("x35_arrival", srv, "stats.get", USER, keep=False)
            e = num(g["ack"].get("endurance")) if isinstance(g["ack"], dict) else None
            X["arrival"].append({"wall": g["wall_before"], "server_endurance": e})
            if e is not None and abs(e - SENTINEL) <= SENT_TOL:
                X["server_on_wall"] = g["wall_before"]
                break
        X["push_window_end_wall"] = wall() + 1.5
        sleep_until(X["push_window_end_wall"])
    pairs("x35_rest", X35_REST_PAIRS, X["rest"])
    r = step("x35_run_walk", c, "player.walk", f"{WALK_DX} 0 run")
    X["run_walk"] = r["ack"]
    sleep_until(wall() + 1.5)
    pairs("x35_run", X35_RUN_PAIRS, X["run"])
    r = step("x35_run_stop", c, "player.stop", "")
    X["run_stop"] = r["ack"]
    sc = step("x35_sentinelCalls_client", c, "lua.global", FAST + ".stats.sentinelCalls")
    ss = step("x35_sentinelCalls_server", srv, "lua.global", FAST + ".stats.sentinelCalls")
    X["sentinelCalls"] = {"client": sc["ack"], "server": ss["ack"]}
    if label == "B":
        r = step("x35_set_off", srv, "moddata.set", f"{USER} NR_sentinel 0")
        X["set_off"] = {"wall": r["wall_before"], "ack": r["ack"]}
        sleep_until(wall() + 3.0)
        pairs("x35_off", X35_OFF_PAIRS, X["off"])
    persist()


def counters(tag):
    c, srv = cur["client"], cur["server"]
    res = {}
    for side_name, side in (("client", c), ("server", srv)):
        for f in ("calls", "callsA", "callsB"):
            r = step(f"{tag}_{f}_{side_name}", side, "lua.global", f"TKX_CalcStats.{f}")
            res[f"{side_name}.{f}"] = gv(r)
    return res


C_ARMS = [
    ("c0_none", [], "thaw"),
    ("c1_calc", [("TKX_calc", "1")], "freeze"),
    ("c2_calc_off", [("TKX_calc", "0")], "thaw"),
    ("c3_A", [("TKX_hookA", "1")], "freeze"),
    ("c4_AB", [("TKX_hookB", "1")], "freeze"),
    ("c5_B", [("TKX_hookA", "0")], "freeze"),
    ("c6_none", [("TKX_hookB", "0")], "thaw"),
]


def c_body():
    srv, c, B = cur["server"], cur["client"], cur["B"]
    B["arms"] = {}
    side_c = step("side_client", c, "lua.global", "TKX_CalcStats.side")
    side_s = step("side_server", srv, "lua.global", "TKX_CalcStats.side")
    B["sides"] = {"client": gv(side_c), "server": gv(side_s)}
    prev = counters("c_start")
    B["counters_start"] = prev
    for name, sets, expect in C_ARMS:
        if name == "c1_calc":
            sleep_until(B["session_ready_wall"] + C_MIN_AFTER_READY_S)
        arm = B["arms"][name] = {"sets": [], "expect": expect, "reads": []}
        for key, val in sets:
            r = step(f"{name}_set_{key}", srv, "moddata.set", f"{USER} {key} {val}")
            arm["sets"].append({"key": key, "value": val, "wall": r["wall_before"], "ack": r["ack"]})
        sleep_until(wall() + 1.0)
        prev = counters(f"{name}_start")
        arm["counters_start"] = prev
        g0 = step(f"{name}_get_start", srv, "stats.get", USER)
        start = wall()
        while wall() < start + ARM_WALL_S:
            st = step(f"{name}_stats_all", srv, "stats.all", USER)
            s = stats_of(st)
            arm["reads"].append({"wall": st["wall_before"],
                                 "worldAge": s.get("worldAge") if s else None,
                                 "thirst": s["stats"].get("Thirst") if s else None,
                                 "hunger": s["stats"].get("Hunger") if s else None,
                                 "field_count_ok": fc_ok(s), "missing": s.get("missing") if s else None})
        g1 = step(f"{name}_get_end", srv, "stats.get", USER)
        for tag, g in (("start", g0), ("end", g1)):
            a = g["ack"] if isinstance(g["ack"], dict) else {}
            arm[f"body_{tag}"] = {key: a.get(key) for key in ("calories", "thirst", "hunger",
                                                               "moodles", "worldAge")}
        cnt = counters(f"{name}_end")
        arm["counters_end"] = cnt
        arm["counters_delta"] = {k: (num(cnt.get(k)) - num(prev.get(k)))
                                 if num(cnt.get(k)) is not None and num(prev.get(k)) is not None else None
                                 for k in cnt}
        persist()


def grade_x34():
    A = out["boots"].get("A", {}).get("samples") or []
    Bs = out["boots"].get("B", {}).get("samples") or []
    P = out["phases"]["X34"] = {"band": f"max({BAND_FRAC} x |A rate|, {BAND_FLOOR}) per game-hour",
                                "per_stat": {}, "stress_first_measurement": {}}
    if len(A) < HOURS + 1 or len(Bs) < HOURS + 1:
        grade("X34", "B tracks A per stat", {"samples": {"A": len(A), "B": len(Bs)}}, "unmeasured",
              "any graded stat outside its band in two consecutive segments; failures > 0; disabledAt set")
        return
    P["clock"] = {"A": [(s["time_snapshot"] or {}).get("hour") if isinstance(s["time_snapshot"], dict) else None
                        for s in A],
                  "B": [(s["time_snapshot"] or {}).get("hour") if isinstance(s["time_snapshot"], dict) else None
                        for s in Bs]}
    falsified, trivial, ok_stats = [], [], []
    for stname in GRADED + RECORDED:
        rows = []
        movedA = movedB = False
        for k in range(1, HOURS + 1):
            a0, a1, b0, b1 = A[k - 1], A[k], Bs[k - 1], Bs[k]
            vals = [x["stats"].get(stname) if x["stats"] else None for x in (a0, a1, b0, b1)]
            ages = [num(x["worldAge"]) for x in (a0, a1, b0, b1)]
            if any(v is None for v in vals) or any(v is None for v in ages):
                rows.append({"k": k, "unmeasured": True})
                continue
            hA, hB = ages[1] - ages[0], ages[3] - ages[2]
            dA, dB = vals[1] - vals[0], vals[3] - vals[2]
            rA, rB = dA / hA, dB / hB
            movedA = movedA or abs(dA) > FLAT
            movedB = movedB or abs(dB) > FLAT
            band = max(BAND_FRAC * abs(rA), BAND_FLOOR)
            excluded = stname == "Fatigue" and k == 5
            row = {"k": k, "segment": SEGMENTS[k], "A": {"v0": vals[0], "v1": vals[1], "h": hA, "rate": rA},
                   "B": {"v0": vals[2], "v1": vals[3], "h": hB, "rate": rB},
                   "diff_rate": rB - rA, "band": band, "level_diff_end": vals[3] - vals[1],
                   "in_band": abs(rB - rA) <= band, "excluded": excluded}
            rows.append(row)
        graded_rows = [r for r in rows if not r.get("unmeasured") and not r.get("excluded")]
        exact_mode = None
        if stname in EXACT:
            levelsA = [x["stats"].get(stname) for x in A]
            levelsB = [x["stats"].get(stname) for x in Bs]
            if not movedA:
                exact_mode = "level"
                for r in graded_rows:
                    r["in_band"] = r["A"]["v1"] == r["B"]["v1"] and r["A"]["v0"] == r["B"]["v0"]
                    r["band"] = 0.0
            else:
                exact_mode = "rate band (A moved)"
            P_exact = {"levelsA": levelsA, "levelsB": levelsB, "mode": exact_mode}
        else:
            P_exact = None
        oob = [r["k"] for r in graded_rows if not r["in_band"]]
        consec = any((k + 1) in oob for k in oob)
        if len(graded_rows) < 2:
            v = "unmeasured"
        elif not movedA and not movedB:
            v = "trivial"
        elif consec:
            v = "falsified"
        else:
            v = "as_predicted"
        entry = {"rows": rows, "out_of_band_segments": oob, "in_band_count": len(graded_rows) - len(oob),
                 "graded_count": len(graded_rows), "moved": {"A": movedA, "B": movedB},
                 "verdict": v, "graded": stname in GRADED}
        if P_exact is not None:
            entry["exact"] = P_exact
        P["per_stat"][stname] = entry
        if stname in GRADED:
            if v == "falsified":
                falsified.append(stname)
            elif v == "trivial":
                trivial.append(stname)
            elif v == "as_predicted":
                ok_stats.append(stname)
    P["stress_first_measurement"] = {
        "A_rates_per_game_hour": [r.get("A", {}).get("rate") for r in P["per_stat"]["Stress"]["rows"]],
        "B_rates_per_game_hour": [r.get("B", {}).get("rate") for r in P["per_stat"]["Stress"]["rows"]],
        "segments": [SEGMENTS[k] for k in range(1, HOURS + 1)]}
    fails = [s.get("failures") for s in Bs]
    dis = [s.get("disabledAt") for s in Bs]
    dis_set = [d for d in dis if isinstance(d, dict) and d.get("resolved") is True]
    regA = out["boots"]["A"].get("registered")
    regB = out["boots"]["B"].get("registered")
    fcs = [s["field_count_ok"] for s in A + Bs]
    P["integrity"] = {"B_failures": fails, "B_disabledAt_resolved": len(dis_set),
                      "registered": {"A": regA, "B": regB}, "field_count_ok_all": all(fcs)}
    if regA is not False or regB is not True:
        v = "unmeasured"
    elif falsified or any((num(f) or 0) > 0 for f in fails) or dis_set:
        v = "falsified"
    elif not ok_stats:
        v = "trivial"
    else:
        v = "as_predicted"
    grade("X34", "for each graded stat B's per-segment rate is within max(2 % |A rate|, 1e-4) per "
                 "game-hour of A's (morale and fitness exact while A's level is constant; asleep "
                 "fatigue graded on segment 6 only); B failures 0 and disabledAt unset throughout",
          {"as_predicted": ok_stats, "trivial": trivial, "falsified": falsified,
           "in_out": {s: [P["per_stat"][s]["in_band_count"], len(P["per_stat"][s]["out_of_band_segments"])]
                      for s in GRADED},
           "integrity": P["integrity"]},
          v, "any graded stat outside its band in two consecutive segments; failures > 0; "
             "disabledAt set; registered not false in A / not true in B")
    grade("X34-field_count", f"{STAT_FIELD_COUNT} stats and an empty missing list on every stats.all of A and B",
          {"all_ok": all(fcs), "n": len(fcs)}, "as_predicted" if all(fcs) else "falsified",
          "a read with another count or a non-empty missing list")


def grade_x35():
    Bb = out["boots"].get("B", {})
    X = Bb.get("x35")
    if not X:
        grade("X35", "client endurance 0.4242 at every sentinel pair", None, "unmeasured", "-")
        return
    def off(p):
        e = num(p["client"].get("endurance"))
        return None if e is None else e - SENTINEL
    rest = [off(p) for p in X["rest"]]
    run = [off(p) for p in X["run"]]
    offs = [off(p) for p in X["off"]]
    srv_rest = [num(p["server"].get("endurance")) for p in X["rest"]]
    srv_run = [num(p["server"].get("endurance")) for p in X["run"]]
    running_seen = any(p["server"].get("running") is True or p["client"].get("running") is True
                       for p in X["run"])
    sc = X.get("sentinelCalls", {})
    sc_c, sc_s = gv(sc.get("client") or {}), gv(sc.get("server") or {})
    P = out["phases"]["X35"] = {"rest_client_offsets": rest, "run_client_offsets": run,
                                "off_client_offsets": offs, "server_rest": srv_rest,
                                "server_run": srv_run, "running_seen": running_seen,
                                "sentinelCalls": {"client": sc_c, "server": sc_s},
                                "server_on_wall": X.get("server_on_wall"),
                                "push_window_end_wall": X.get("push_window_end_wall")}
    if any(o is None for o in rest + run) or not rest:
        v = "unmeasured"
    else:
        rest_ok = all(abs(o) <= SENT_TOL for o in rest)
        run_ok = all(abs(o) <= SENT_TOL for o in run)
        control_ok = any(o is not None and abs(o) > SENT_TOL for o in offs)
        calls_ok = (num(sc_s) or 0) > 0 and num(sc_c) in (0, None)
        P.update({"rest_ok": rest_ok, "run_ok": run_ok, "off_control_left": control_ok, "calls_ok": calls_ok})
        if not rest_ok or not run_ok:
            v = "falsified"
        elif not running_seen or not control_ok:
            v = "trivial"
        elif calls_ok:
            v = "as_predicted"
        else:
            v = "falsified"
    grade("X35", "client endurance reads 0.4242 +- 1e-6 at all ten resting and six running pairs "
                 "after the push window; sentinelCalls server > 0, client 0; the client leaves 0.4242 "
                 "after the sentinel is cleared", P, v,
          "a pair whose client endurance differs from 0.4242 by more than 1e-6 (the push landed "
          "between vanilla's update and the handler); a resting-only agreement or a client that "
          "never leaves 0.4242 off-arm is trivial")


def thirst_fit(reads):
    pts = [(r["worldAge"] * 3600.0, r["thirst"]) for r in reads
           if num(r.get("worldAge")) is not None and num(r.get("thirst")) is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx else None
    return {"n": n, "slope_per_game_s": slope, "delta": pts[-1][1] - pts[0][1],
            "game_s": pts[-1][0] - pts[0][0], "thirst_first": pts[0][1], "thirst_last": pts[-1][1],
            "ratio_to_vanilla": slope / THIRST_PER_GAME_SECOND if slope is not None else None}


def grade_c():
    C = out["boots"].get("C", {})
    arms = C.get("arms") or {}
    P = out["phases"]["C"] = {"arms": {}}
    state = {}
    for name, _, expect in C_ARMS:
        arm = arms.get(name)
        if not arm:
            state[name] = "unmeasured"
            continue
        fit = thirst_fit(arm["reads"])
        cal0 = num((arm.get("body_start") or {}).get("calories"))
        cal1 = num((arm.get("body_end") or {}).get("calories"))
        macro_moved = cal0 is not None and cal1 is not None and cal0 != cal1
        if fit is None:
            obs = "unmeasured"
        elif fit["thirst_last"] >= 1.0:
            obs = "clamped"
        elif abs(fit["delta"]) <= FREEZE_TOL:
            obs = "frozen"
        elif fit["slope_per_game_s"] > 0 and abs(fit["ratio_to_vanilla"] - 1.0) <= THAW_BAND:
            obs = "thaw"
        else:
            obs = "moving-off-rate"
        state[name] = obs
        P["arms"][name] = {"expect": expect, "observed": obs, "fit": fit, "macro_moved": macro_moved,
                           "calories": [cal0, cal1], "counters_delta": arm.get("counters_delta"),
                           "counters_end": arm.get("counters_end"),
                           "moodles": [(arm.get("body_start") or {}).get("moodles"),
                                       (arm.get("body_end") or {}).get("moodles")]}
    P["state"] = state

    def d(name, key):
        return num(((arms.get(name) or {}).get("counters_delta") or {}).get(key))

    # X32
    client_calls = [num(((arms.get(n) or {}).get("counters_end") or {}).get("client.calls")) for n, _, _ in C_ARMS]
    x32_obs = {"c0_none": state.get("c0_none"), "c1_calc": state.get("c1_calc"),
               "c2_calc_off": state.get("c2_calc_off"),
               "server_calls_delta_c1": d("c1_calc", "server.calls"),
               "server_calls_delta_c2": d("c2_calc_off", "server.calls"),
               "client_calls_end_each_arm": client_calls,
               "macro_moved_c1": (P["arms"].get("c1_calc") or {}).get("macro_moved")}
    if any(state.get(n) in (None, "unmeasured") for n in ("c0_none", "c1_calc", "c2_calc_off")):
        v32 = "unmeasured"
    elif state["c1_calc"] == "frozen" and state["c0_none"] == "thaw" and state["c2_calc_off"] == "thaw" \
            and (d("c1_calc", "server.calls") or 0) > 0 and x32_obs["macro_moved_c1"]:
        v32 = "as_predicted"
    elif "clamped" in (state["c0_none"], state["c1_calc"], state["c2_calc_off"]):
        v32 = "trivial"
    else:
        v32 = "falsified"
    grade("X32", "calc arm: thirst frozen (|delta| <= 1e-6) while calories move and server calls rise; "
                 "none arms before and after: thirst at 8.0e-6 per game-second +-10 %", x32_obs, v32,
          "thirst moving under calc, or frozen under none")
    if all(cc is None for cc in client_calls):
        v32c = "unmeasured"
    elif all((cc or 0) == 0 for cc in client_calls if cc is not None):
        v32c = "as_predicted"
    else:
        v32c = "falsified"
    grade("X32-client", "TKX_CalcStats.calls reads 0 on the client at every arm end (the hook never "
                        "fires on a multiplayer client, #2236)", {"client_calls_end_each_arm": client_calls},
          v32c, "a client count above 0")
    # X46
    dA, dB = d("c4_AB", "server.callsA"), d("c4_AB", "server.callsB")
    ab_close = dA is not None and dB is not None and abs(dA - dB) <= max(3, 0.10 * max(dA, dB))
    b_alone_rising = (d("c5_B", "server.callsB") or 0) > 0 and (d("c5_B", "server.callsA") or 0) == 0
    x46_obs = {"c3_A": state.get("c3_A"), "c4_AB": state.get("c4_AB"), "c5_B": state.get("c5_B"),
               "c6_none": state.get("c6_none"), "c4_callsA_delta": dA, "c4_callsB_delta": dB,
               "c4_calls_close": ab_close, "c5_callsB_delta": d("c5_B", "server.callsB"),
               "c5_callsA_delta": d("c5_B", "server.callsA"),
               "c3_callsA_delta": d("c3_A", "server.callsA")}
    if any(state.get(n) in (None, "unmeasured") for n in ("c3_A", "c4_AB", "c5_B", "c6_none")):
        v46 = "unmeasured"
    elif state["c5_B"] != "frozen" and state["c5_B"] != "clamped":
        v46 = "falsified"
    elif state["c3_A"] == "frozen" and state["c4_AB"] == "frozen" and state["c5_B"] == "frozen" \
            and state["c6_none"] == "thaw" and ab_close and b_alone_rising:
        v46 = "as_predicted"
    elif "clamped" in (state["c3_A"], state["c4_AB"], state["c5_B"], state["c6_none"]):
        v46 = "trivial"
    else:
        v46 = "falsified"
    grade("X46", "A alone frozen; A+B frozen with callsA ~ callsB; B alone (returning false) frozen with "
                 "callsB rising and callsA flat; neither: thaw", x46_obs, v46,
          "a thaw under B alone (returns are not discarded), or a frozen none arm, or A+B moving")


def boot(label):
    prof = profs[label]
    sub = os.path.join(run_dir, f"boot-{label}")
    os.makedirs(sub, exist_ok=True)
    B = out["boots"][label] = {"profile": prof.name, "run_subdir": f"boot-{label}", "steps": [],
                               "sandbox": prof.sandbox}
    cur.clear()
    cur.update({"label": label, "B": B})
    tl.mark("boot", label=label, profile=prof.name)
    clients = []
    server = None
    try:
        server = make_server(sub, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None)
        servers[label] = server
        cur["server"] = server
        server.start(timeout=prof.server_timeout)
        tl.mark("server_started", label=label)
        B["build"] = server.build
        c, _ = make_client(sub, USER, server, rec)
        cur["client"] = c
        c.start()
        clients.append(c)
        c.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", label=label)
        B["session_ready_wall"] = wall()
        B["verify"] = verify(prof, server, clients, tl)
        B["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                               "client": sorted(set(c.mods_not_found))}
        persist()
        if label in ("A", "B"):
            hourly_body(label)
        else:
            c_body()
    except Exception as e:                     # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        persist()
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                logs = {"server_nr_lines": grep_numbered(server.log_path, NR_RX, LOG_LIMIT),
                        "server_trace_lines": grep_numbered(server.log_path, TRACE_RX, TRACE_LIMIT),
                        "server_stack_lines": grep_numbered(server.log_path, STACK_RX, TRACE_LIMIT),
                        "server_log": os.path.relpath(server.log_path, run_dir)}
                if clients:
                    logs.update({"client_nr_lines": grep_numbered(clients[0].console, NR_RX, LOG_LIMIT),
                                 "client_trace_lines": grep_numbered(clients[0].console, TRACE_RX, TRACE_LIMIT),
                                 "client_stack_lines": grep_numbered(clients[0].console, STACK_RX, TRACE_LIMIT),
                                 "client_console": os.path.relpath(clients[0].console, run_dir)})
                B["logs"] = logs
            B["wall_end"] = wall()
            persist()


profs = {k: profile.load(v) for k, v in PROFILES.items()}
rec = None if DRY_RUN else fx.load(profs["A"].fixture)
run_id, run_dir = ("x131c-dry-run", None) if DRY_RUN else new_run_dir("x131c")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
servers, cur = {}, {}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": {k: p.report() for k, p in profs.items()},
    "mods": {k: list(p.mods) for k, p in profs.items()},
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_CalcStats"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"GAME_HOUR_WALL_S": GAME_HOUR_WALL_S, "HOURS": HOURS, "SEGMENTS": SEGMENTS,
                  "GRADED": GRADED, "EXACT": EXACT, "RECORDED": RECORDED, "BAND_FRAC": BAND_FRAC,
                  "BAND_FLOOR": BAND_FLOOR, "SENTINEL": SENTINEL, "SENT_TOL": SENT_TOL,
                  "THIRST_PER_GAME_SECOND": THIRST_PER_GAME_SECOND, "THAW_BAND": THAW_BAND,
                  "FREEZE_TOL": FREEZE_TOL, "ARM_WALL_S": ARM_WALL_S, "WALK_DX": WALK_DX},
    "world_changes": {"restored": "each boot restores the golden fixture into its own sub-directory",
                      "left_in_place": []},
    "boots": {}, "notes": [], "phases": {}, "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)

try:
    for label in ("A", "B", "C"):
        boot(label)
    try:
        grade_x34()
    except Exception as e:                     # noqa: BLE001
        out["grade_error_x34"] = f"{type(e).__name__}: {e}"
        out["grade_tb_x34"] = traceback.format_exc()[-2000:]
    try:
        grade_x35()
    except Exception as e:                     # noqa: BLE001
        out["grade_error_x35"] = f"{type(e).__name__}: {e}"
        out["grade_tb_x35"] = traceback.format_exc()[-2000:]
    try:
        grade_c()
    except Exception as e:                     # noqa: BLE001
        out["grade_error_c"] = f"{type(e).__name__}: {e}"
        out["grade_tb_c"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": {k: [v.get("ok") for v in b.get("verify", [])] for k, b in out["boots"].items()},
        "mods_not_found": {k: b.get("mods_not_found") for k, b in out["boots"].items()},
        "boot_errors": {k: b.get("error") for k, b in out["boots"].items()},
        "server_error_count": {k: b.get("server_error_count") for k, b in out["boots"].items()},
        "client_lua_error": {k: b.get("client_lua_error") for k, b in out["boots"].items()},
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    for srv in servers.values():
        try:
            hard_kill(srv, [])
        except Exception:                      # noqa: BLE001
            pass
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
