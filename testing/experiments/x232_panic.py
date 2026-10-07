"""x232-panic -- Plan 10b addendum Task P3b (live): the PANIC sawtooth under a once-a-minute write at a realistic
target. x231 (Task P1+P3) held PANIC at 0.5 on a 0-100 scale, so its amplitude was the clipped target (trivial,
do-not-cite); #3392 read the fall per tick off that clipped ring (0.17969 a tick at DayLength 1, 0.030086 a tick at
time.multiplier 0.1674) and put about 1.12 a game minute on it by arithmetic. This run measures the sawtooth at a
target of 10 (C1, C2) and, named here before the run, at 6.5 inside the first PANIC window (C3, C3s).

The staged copy is release/perf-dc619d0/NutritionRevamp/Contents/mods/NutritionRevamp (MANIFEST.json sha256
c86e295a...b389), unchanged since x231; its server/NR_Server_Bench.lua (sha256 c20f645d...0f8d, equal to
testing/spikes/instruments/x231_NR_Server_Bench.lua) carries the instruments. No instrument is added: B.minuteHold
does the job. mod/ is never booted. One boot of profile x23-panic (fixture two, admin -debug then bob release,
Nutrition false, DayLength 1). ONE artifact, `panic.json`, plus the staged MANIFEST.json copied byte-identical
beside it. Shape: x231_perf.py (step, keep, gread, lcall, setp, counters, wait_minute, hold_pages, hold_leg, tpm,
run_phase, grade, make_server + attach_clients, the echo-excluding log greps, the artifact copied by the driver).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENT (the staged copy's NR_Server_Bench.lua, server only, every handler gated on NR.isServer()):
  NutritionRevamp.server.bench.ticks / .minutes   +1 on every OnTick / EveryOneMinute (the legs pace on .minutes)
  .holdOn / .panicTarget / .tempTarget / .holdUser (lua.setpath) the once-a-minute hold: on every EveryOneMinute,
        for every online player, PANIC set to panicTarget and TEMPERATURE to tempTarget through stats:set (each
        write inside its own pcall); for holdUser a write ring (tick, minute, pre panic, pre temp, post panic, post
        temp, wall ms) and on every OnTick a tick ring (tick, minute, panic, temp). .holdReset(), .holdText(kind,
        from, to) (kind t or w; r2 the ring's count).
  tempTarget is set to nil here, so the TEMPERATURE write fails inside its pcall and the thermoregulator keeps the
  stat (x231 held it at 37.5; this run does not).

THE MOODLE: no harness command reads the PANIC moodle. stats.get's moodles block reads five MoodleType members
(TK.MOODLES in shared/PZTestKit_Core.lua: HUNGRY, THIRST, FOOD_EATEN, HEAVY_LOAD, ENDURANCE), and stats.all reads
the CharacterStat values only. The moodle level is therefore UNREAD; the driver infers a level per tick-ring sample
from the stat against #2369's PANIC thresholds 6, 30, 65 and 80 (the level is the count of thresholds at or under
the value; which side of a boundary the engine puts an equal value on is not read), and every inferred figure is
labelled inferred.

PHASES (order S0, C, Z; C runs its legs C1, C3, C2, C3s so the clock changes once):
  S0  the ready marks, the verify rows, the players list, the time, the mode.
  C   sandbox.var NR.Mode 2 (Overlay, as x231 phase C), C_MODE_WAIT_S, options.mode and fast.registered read;
      stats.all admin; tempTarget nil, holdUser admin; a tick-rate probe at DayLength 1.
      C1  (DayLength 1 spacing) panicTarget PANIC_T: holdReset, holdOn true for C_MINUTES game minutes, holdOn
          false, both rings paged.
      C3  (DayLength 1 spacing) the same at panicTarget PANIC_T3.
      then time.multiplier SLOW_MULT (x231's DayLength-4 substitute, #3394: the live DayLength set does not take)
      and a tick-rate probe;
      C2  (slow spacing) panicTarget PANIC_T, the same hold (cap SLOW_CAP_S).
      C3s (slow spacing) panicTarget PANIC_T3, the same hold.
      then time.multiplier 1, stats.all admin, NR.Mode 1 restored, a tick-rate probe.
  Z   the mod-error check (server errors naming the mod's files; admin's lua_error marker).

THE SAWTOOTH (summary per leg, `phases.C.<leg>.stats`): per write after the first, the gap is the tick-ring samples
with a tick AFTER the previous write's tick and AT OR BEFORE this write's tick (the x231 summary sliced from the
previous write's tick inclusive and mixed in the pre-write read; this slice fixes that). The gap's first sample is
the value after the write, its last the value the minute's decay left before this write (the floor). The falls are
the differences of consecutive samples in the gap where both are above 0 (a fall clipped at 0 is not counted).
The shape: linear if the fall per tick is constant (its coefficient of variation small), proportional if the fall
over the value before it is constant; both coefficients are reported. The amplitude is the post-write value of the
previous write minus this write's pre-write value.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  C1  the fall is linear in the value (#3392's 0.5 ring fell a constant 0.17969 a tick): the fall per tick at 10 is
      within FALL_TOL of 0.17969, its coefficient of variation under LIN_CV_MAX and under the proportional one; the
      floor stays above 6 at every write, so every sample's inferred level is 1 (no inferred flicker). Falsifier: a
      fall per tick outside the tolerance (a decay that scales with the value), a coefficient at or over the bound,
      or a floor at or under 6. Unmeasured if no gap.
  C2  the decay is per game time: the fall per tick within FALL_TOL of 0.030086 (#3392's slow-clock figure), the
      amplitude per gap within a factor AMP_FACTOR of C1's, the floor above 6 at every write (no inferred flicker
      at the slow spacing either). Falsifier: either outside its band, or a floor at or under 6.
  C3  at 6.5 the floor drops under 6 at every write after the first, so the inferred level goes 1 -> 0 -> 1 every
      game minute (an inferred flicker; the moodle is not read). Falsifier: a gap whose samples all stay at or
      above 6.
  C3s the same at the slow spacing, and the share of samples under 6 within SHARE_TOL (absolute) of C3's (a
      per-game-time decay crosses 6 at the same fraction of the minute). Falsifier: a gap with no sample under 6,
      or the share outside the tolerance.
  Z   no mod error line; admin not parked.

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

PROFILE = "x23-panic"
PREFIX = "x232"
SESSION = ("Plan 10b addendum Task P3b: the PANIC sawtooth under a once-a-minute write at target 10 (and 6.5) under "
           "Overlay, at the DayLength 1 spacing and at time.multiplier 0.1674, on the staged copy at dc619d0; one "
           "boot of " + PROFILE)
ARTIFACT = "panic.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/perf-dc619d0/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
BENCH_FILE = STAGE_MOD + "/common/media/lua/server/NR_Server_Bench.lua"
INSTRUMENT_COPY = "testing/spikes/instruments/x231_NR_Server_Bench.lua"
STAGED_AT = "dc619d0"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
NR = "NutritionRevamp"
BENCH = "NutritionRevamp.server.bench"
C_MODE_WAIT_S = 6.0
PANIC_T = 10
PANIC_T3 = 6.5
C_MINUTES = 20
DL1_CAP_S = 40.0
SLOW_MULT = 0.1674
SLOW_CAP_S = 150.0
C_PROBE_S = 10.0
THRESHOLDS = (6, 30, 65, 80)
FALL_DL1 = 0.17969
FALL_SLOW = 0.030086
FALL_TOL = 0.10
LIN_CV_MAX = 0.10
AMP_FACTOR = 1.5
SHARE_TOL = 0.25
PAGE = 80
POLL_S = 0.3
LOG_LIMIT = 400
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
    "C1": {"fall per tick vs 0.17969": f"within {FALL_TOL}", "fall per tick CV": f"< {LIN_CV_MAX} and < the "
           "proportional CV", "floor": "> 6 at every write", "inferred level": "1 at every sample"},
    "C2": {"fall per tick vs 0.030086": f"within {FALL_TOL}", "amplitude per gap vs C1": f"within a factor "
           f"{AMP_FACTOR}", "floor": "> 6 at every write"},
    "C3": {"floor": "< 6 at every write after the first", "inferred level": "1 -> 0 -> 1 every game minute"},
    "C3s": {"floor": "< 6 at every write after the first", "share of samples under 6 vs C3": f"within {SHARE_TOL}"},
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
             "bench_file": BENCH_FILE, "instrument_copy": INSTRUMENT_COPY,
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/perf-dc619d0",
             "moodle_note": "The PANIC moodle is not read: no harness command reads it. Every level in this "
                            "artifact is inferred from the stat against the thresholds 6, 30, 65 and 80 (#2369)."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The brief's C2 (slow spacing) runs after C3 at DayLength 1, so the clock changes once (C1, C3, C2, C3s).",
        "tempTarget is set to nil, so the hold's TEMPERATURE write fails inside its pcall; x231 held it at 37.5.",
        "The PANIC moodle is not read (no harness command reads it); its level is inferred from the stat.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}
try:
    out["meta"]["bench_sha256"] = sha256_file(os.path.join(REPO, BENCH_FILE))
    out["meta"]["instrument_copy_sha256"] = sha256_file(os.path.join(REPO, INSTRUMENT_COPY))
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


def lcall(side, fn, tag, *args):
    return keep(step(tag, side, "lua.call", " ".join([fn] + [str(a) for a in args])))


def setp(fieldpath, value, tag):
    return keep(step(tag, SRV, "lua.setpath", f"{fieldpath} {value}"))


def counters(tag):
    t = gread(SRV, f"{BENCH}.ticks", f"{tag}_ticks")
    m = gread(SRV, f"{BENCH}.minutes", f"{tag}_minutes")
    return {"ticks": num(val(t)), "minutes": num(val(m)), "wall": t["wall"], "wall_after": m["wall_after"]}


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


def hold_pages(kind, tag):
    first = lcall(SRV, f"{BENCH}.holdText", f"{tag}_{kind}_n", kind, 1, 0)
    count = int(num(first.get("r2")) or 0)
    rows, i = [], 1
    while i <= count:
        r = lcall(SRV, f"{BENCH}.holdText", f"{tag}_{kind}_{i}", kind, i, i + PAGE - 1)
        txt = r.get("r1")
        if isinstance(txt, str) and txt:
            for part in txt.split(";"):
                f = [num(x) for x in part.split(",")]
                rows.append(f)
        i += PAGE
    return {"count": count, "rows": rows}


def level(v):
    """The INFERRED PANIC moodle level: the count of #2369's thresholds at or under the value (not read)."""
    if v is None:
        return None
    return sum(1 for t in THRESHOLDS if v >= t)


def mean_sd(xs):
    if not xs:
        return None, None
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) if len(xs) > 1 else 0.0
    return m, sd


def sawtooth(wr, tr, target):
    """The sawtooth per gap (see the docstring): the slice is (previous write tick, this write tick]."""
    w = sorted([r for r in wr.get("rows", []) if len(r) == 7 and r[0] is not None], key=lambda r: r[0])
    t = sorted([r for r in tr.get("rows", []) if len(r) == 4 and r[0] is not None and r[2] is not None],
               key=lambda r: r[0])
    gaps = []
    for i in range(1, len(w)):
        prev, cur = w[i - 1], w[i]
        sl = [r for r in t if prev[0] < r[0] <= cur[0]]
        vals = [r[2] for r in sl]
        falls, ratios = [], []
        for j in range(1, len(vals)):
            a, b = vals[j - 1], vals[j]
            if a > 0 and b > 0:
                falls.append(a - b)
                ratios.append((a - b) / a)
        lv = [level(v) for v in vals]
        gaps.append({"write_tick": cur[0], "prev_write_tick": prev[0], "ticks": cur[0] - prev[0],
                     "post_write_prev": prev[4], "pre_write": cur[2], "amp": (prev[4] - cur[2])
                     if prev[4] is not None and cur[2] is not None else None,
                     "samples": vals, "first_sample": vals[0] if vals else None,
                     "last_sample": vals[-1] if vals else None, "falls": falls,
                     "under_6": sum(1 for v in vals if v < THRESHOLDS[0]),
                     "inferred_levels": sorted(set(x for x in lv if x is not None)),
                     "inferred_level_changes": sum(1 for j in range(1, len(lv)) if lv[j] != lv[j - 1])})
    falls = [x for g in gaps for x in g["falls"]]
    ratios = []
    for g in gaps:
        vals = g["samples"]
        for j in range(1, len(vals)):
            if vals[j - 1] > 0 and vals[j] > 0:
                ratios.append((vals[j - 1] - vals[j]) / vals[j - 1])
    fm, fsd = mean_sd(falls)
    rm, rsd = mean_sd(ratios)
    amps = [g["amp"] for g in gaps if g["amp"] is not None]
    floors = [g["pre_write"] for g in gaps if g["pre_write"] is not None]
    ticks = [g["ticks"] for g in gaps]
    nsamp = sum(len(g["samples"]) for g in gaps)
    nunder = sum(g["under_6"] for g in gaps)
    am, _ = mean_sd(amps)
    tm, _ = mean_sd(ticks)
    return {"target": target, "writes": len(w), "gaps_n": len(gaps), "gaps": gaps,
            "post_writes": [r[4] for r in w],
            "fall_per_tick_mean": fm, "fall_per_tick_sd": fsd, "fall_per_tick_n": len(falls),
            "fall_per_tick_min": min(falls) if falls else None, "fall_per_tick_max": max(falls) if falls else None,
            "fall_per_tick_cv": (fsd / fm) if fm else None,
            "ratio_per_tick_mean": rm, "ratio_per_tick_cv": (rsd / rm) if rm else None,
            "amp_mean": am, "amp_min": min(amps) if amps else None, "amp_max": max(amps) if amps else None,
            "floor_min": min(floors) if floors else None, "floor_max": max(floors) if floors else None,
            "ticks_per_gap_mean": tm, "ticks_per_gap_min": min(ticks) if ticks else None,
            "ticks_per_gap_max": max(ticks) if ticks else None,
            "fall_per_game_minute_mean": (fm * tm) if fm is not None and tm is not None else None,
            "samples_n": nsamp, "samples_under_6": nunder,
            "share_under_6": (nunder / nsamp) if nsamp else None,
            "gaps_with_under_6": sum(1 for g in gaps if g["under_6"] > 0),
            "inferred_levels_seen": sorted(set(x for g in gaps for x in g["inferred_levels"])),
            "inferred_level_changes": sum(g["inferred_level_changes"] for g in gaps)}


def hold_leg(tag, target, minutes, cap_s):
    L = {"target": target}
    L["target_set"] = setp(f"{BENCH}.panicTarget", target, f"{tag}_pt")
    L["reset"] = lcall(SRV, f"{BENCH}.holdReset", f"{tag}_reset")
    c0 = counters(f"{tag}_c0")
    L["start_counters"] = c0
    L["on"] = setp(f"{BENCH}.holdOn", "true", f"{tag}_on")
    try:
        L["end_counters"] = wait_minute((c0["minutes"] or 0) + minutes + 1, f"{tag}_wait", cap_s)
    finally:
        L["off"] = setp(f"{BENCH}.holdOn", "false", f"{tag}_off")
    L["w"] = hold_pages("w", tag)
    L["t"] = hold_pages("t", tag)
    L["stats"] = sawtooth(L["w"], L["t"], target)
    persist()
    return L


def tpm(tag, seconds):
    a = counters(f"{tag}_a")
    time.sleep(seconds)
    b = counters(f"{tag}_b")
    if None in (a["ticks"], b["ticks"], a["minutes"], b["minutes"]) or b["minutes"] == a["minutes"]:
        return {"a": a, "b": b, "ticks_per_minute": None}
    return {"a": a, "b": b, "ticks_per_minute": (b["ticks"] - a["ticks"]) / (b["minutes"] - a["minutes"])}


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


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = keep(step("S0_time", SRV, "time.snapshot"))
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    P["registered"] = gread(SRV, f"{NR}.server.fast.registered", "S0_reg")
    P["hold_defaults"] = {k: gread(SRV, f"{BENCH}.{k}", f"S0_{k}")
                          for k in ("holdOn", "panicTarget", "tempTarget", "holdUser", "HOLD_MAX")}
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}


def phase_C():
    P = out["phases"]["C"] = {}
    P["mode_set"] = keep(step("C_mode2", SRV, "sandbox.var", "NR.Mode 2"))
    out["world_changes"]["mode"] = "NR.Mode set to 2 for C"
    time.sleep(C_MODE_WAIT_S)
    P["overlay_mode"] = gread(SRV, f"{NR}.server.options.mode", "C_mode_read")
    P["overlay_registered"] = gread(SRV, f"{NR}.server.fast.registered", "C_reg")
    P["stats_all0"] = keep(step("C_stats_all0", SRV, "stats.all", "admin"))
    P["setup"] = {"temp": setp(f"{BENCH}.tempTarget", "nil", "C_tt"),
                  "user": setp(f"{BENCH}.holdUser", "admin", "C_hu")}
    P["tpm1"] = tpm("C_tpm1", C_PROBE_S / 2.0)
    cur_phase["name"] = "C1"
    P["C1"] = hold_leg("C1", PANIC_T, C_MINUTES, DL1_CAP_S)
    cur_phase["name"] = "C3"
    P["C3"] = hold_leg("C3", PANIC_T3, C_MINUTES, DL1_CAP_S)
    cur_phase["name"] = "C"
    try:
        P["mult_set"] = keep(step("C_mult", SRV, "time.multiplier", str(SLOW_MULT)))
        out["world_changes"]["multiplier"] = f"time.multiplier {SLOW_MULT} for C2 and C3s"
        time.sleep(1.0)
        P["tpm_slow"] = tpm("C_tpm_slow", C_PROBE_S)
        cur_phase["name"] = "C2"
        P["C2"] = hold_leg("C2", PANIC_T, C_MINUTES, SLOW_CAP_S)
        cur_phase["name"] = "C3s"
        P["C3s"] = hold_leg("C3s", PANIC_T3, C_MINUTES, SLOW_CAP_S)
    finally:
        cur_phase["name"] = "C"
        P["mult_restore"] = keep(step("C_mult1", SRV, "time.multiplier", "1"))
        out["world_changes"]["multiplier"] = f"time.multiplier {SLOW_MULT} for C2 and C3s, then 1"
    P["stats_all1"] = keep(step("C_stats_all1", SRV, "stats.all", "admin"))
    P["mode_restore"] = keep(step("C_mode1", SRV, "sandbox.var", "NR.Mode 1"))
    out["world_changes"]["mode"] = "NR.Mode set to 2 for C, then back to 1"
    P["tpm_after"] = tpm("C_tpm_after", C_PROBE_S / 2.0)


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()


def body():
    order = (("S0", phase_S0), ("C", phase_C), ("Z", phase_Z))
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


OBS_KEYS = ("target", "writes", "gaps_n", "fall_per_tick_mean", "fall_per_tick_sd", "fall_per_tick_n",
            "fall_per_tick_min", "fall_per_tick_max", "fall_per_tick_cv", "ratio_per_tick_mean", "ratio_per_tick_cv",
            "amp_mean", "amp_min", "amp_max", "floor_min", "floor_max", "ticks_per_gap_mean", "ticks_per_gap_min",
            "ticks_per_gap_max", "fall_per_game_minute_mean", "samples_n", "samples_under_6", "share_under_6",
            "gaps_with_under_6", "inferred_levels_seen", "inferred_level_changes")


def obs_of(s):
    return {k: s.get(k) for k in OBS_KEYS}


def within(x, ref, tol):
    return x is not None and ref and abs(x - ref) <= tol * ref


def grade_all():
    C = out["phases"].get("C") or {}
    s1 = g(C, "C1", "stats") or {}
    if s1.get("gaps_n"):
        o = obs_of(s1)
        o["overlay_mode"] = val(C.get("overlay_mode"))
        o["overlay_registered"] = val(C.get("overlay_registered"))
        o["ticks_per_minute_probe"] = g(C, "tpm1", "ticks_per_minute")
        cv, pcv = s1.get("fall_per_tick_cv"), s1.get("ratio_per_tick_cv")
        ok = (within(s1.get("fall_per_tick_mean"), FALL_DL1, FALL_TOL) and cv is not None and cv < LIN_CV_MAX
              and pcv is not None and cv < pcv and s1.get("floor_min") is not None and s1["floor_min"] > THRESHOLDS[0])
        grade("C1", PRED["C1"], o, "as_predicted" if ok else "falsified",
              "a fall per tick outside the tolerance, a CV at or over the bound or over the proportional one, "
              "or a floor at or under 6")
    else:
        grade("C1", PRED["C1"], obs_of(s1) if s1 else None, "unmeasured", "no gap")
    s2 = g(C, "C2", "stats") or {}
    if s2.get("gaps_n"):
        o = obs_of(s2)
        o["ticks_per_minute_probe"] = g(C, "tpm_slow", "ticks_per_minute")
        r = (s2["amp_mean"] / s1["amp_mean"]) if s2.get("amp_mean") is not None and s1.get("amp_mean") else None
        o["amp_ratio_to_C1"] = r
        ok = (within(s2.get("fall_per_tick_mean"), FALL_SLOW, FALL_TOL) and r is not None
              and (1.0 / AMP_FACTOR) <= r <= AMP_FACTOR and s2.get("floor_min") is not None
              and s2["floor_min"] > THRESHOLDS[0])
        grade("C2", PRED["C2"], o, "as_predicted" if ok else "falsified",
              "a fall per tick or an amplitude ratio outside its band, or a floor at or under 6")
    else:
        grade("C2", PRED["C2"], obs_of(s2) if s2 else None, "unmeasured", "no gap")
    s3 = g(C, "C3", "stats") or {}
    if s3.get("gaps_n"):
        ok = s3.get("gaps_with_under_6") == s3["gaps_n"]
        grade("C3", PRED["C3"], obs_of(s3), "as_predicted" if ok else "falsified", "a gap with no sample under 6")
    else:
        grade("C3", PRED["C3"], obs_of(s3) if s3 else None, "unmeasured", "no gap")
    s4 = g(C, "C3s", "stats") or {}
    if s4.get("gaps_n"):
        o = obs_of(s4)
        a, b = s4.get("share_under_6"), s3.get("share_under_6")
        o["share_diff_to_C3"] = (a - b) if a is not None and b is not None else None
        ok = (s4.get("gaps_with_under_6") == s4["gaps_n"] and o["share_diff_to_C3"] is not None
              and abs(o["share_diff_to_C3"]) <= SHARE_TOL)
        grade("C3s", PRED["C3s"], o, "as_predicted" if ok else "falsified",
              "a gap with no sample under 6, or the share outside the tolerance")
    else:
        grade("C3s", PRED["C3s"], obs_of(s4) if s4 else None, "unmeasured", "no gap")
    Z = out["phases"].get("Z") or {}
    if Z:
        o = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [], "admin_lua_error": out.get("admin_lua_error")}
        ok = not o["server_mod_error_lines"] and not o["admin_lua_error"]
        grade("Z", PRED["Z"], o, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
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
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
