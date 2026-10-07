"""x231-perf -- Plan 10b Task P1+P3 (live): the slow minute by step, and the cost of no per-tick work, on the STAGED
copy of the tree at dc619d0 (release/perf-dc619d0/NutritionRevamp/Contents/mods/NutritionRevamp, staged by Task 0,
MANIFEST.json sha256 c86e295a...b389; release/ is gitignored; mod/ is never booted, Plan 10b's Global Constraints)
whose server/NR_Server_Bench.lua carries the P1+P3 instruments appended. The edited file's sha256 is recorded in
`meta`. One boot of profile x23-perf (fixture two, admin -debug then bob release, Nutrition false, DayLength 1, sleep
on). ONE artifact, `perf.json`, plus the staged MANIFEST.json copied byte-identical beside it. Shape: x222_clock_cost.py
(step, keep, gread, lcall, persist, run_phase, grade, make_server + attach_clients, the echo-excluding log greps, the
artifact copied by the driver). Written BEFORE the boot with every prediction in it and never edited after the run
(CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENT (the staged copy's NR_Server_Bench.lua, server only, every handler gated on NR.isServer()):
  NutritionRevamp.server.bench.ticks / .minutes   +1 on every OnTick / EveryOneMinute (the phases pace on .minutes)
  .profStart() / .profStop() / .profReset()       (lua.call) the per-step timers. The first profStart wraps each
        registered step of NutritionRevamp.server.minute (ORDER: bus fast reconcile kinetics metabolism nutrients
        effects strength weight), NR.server.minute.run (key __run) and NR.server.players.work (key __work); a wrapped
        call adds its getTimestampMs delta, its NR.call count delta and 1 run while prof.on. NR.call is wrapped by a
        counter at file load; NR.num/obj/flag reach it by table lookup, so all four are counted. Direct colon calls on
        Java objects are not counted (the memo counts them by reading the adapters).
  .profText()   (lua.call) `name=ms/runs/calls;...`, r2 = MIN.stats.runs, r3 = MIN.stats.failures
  .holdOn / .panicTarget / .tempTarget / .holdUser (lua.setpath) the once-a-minute hold: on every EveryOneMinute,
        for every online player, PANIC set to panicTarget and TEMPERATURE to tempTarget through stats:set (the
        NR_Server_Fast hoist's route); for holdUser a write ring (tick, minute, pre panic, pre temp, post panic,
        post temp, wall ms) and on every OnTick a tick ring (tick, minute, panic, temp). .holdReset(), .holdText(kind,
        from, to) (kind t or w; r2 the ring's count).
  .burstOn / .rrM (lua.setpath) the burst: on every EveryOneMinute, P.work for every online player (rrM 0, B.burst)
        or for ceil(N / rrM) players in a persistent rotation (B.burstRR). The live OnTick drain stays on.
        .burstReset(), .burstText() (events, players, ms, maxMs, the per-event ms histogram e0..e5, rot).
  .handler / .minute   bench.global targets: FAST.handler(p) / P.work(u, p) on the first online player by name.

PHASES (order S0, A, B, D, C2, C, Z):
  S0  the ready marks, the verify rows, the players list, the time.
  A   P1 in play: two apples spawned to each player by RCON additem; profReset + profStart at minute m0; at m0+20
      eat.action Base.Apple 1 on admin and bob; at m0+30 player.walk WALK_DX 0 on both, at m0+35 player.walk -WALK_DX
      0, at m0+40 player.stop on both; at m0+70 the second eat on both; at m0+80 player.sleep.hold admin
      SLEEP_HOLD_S (about 30 game minutes at 0.625 s), at m0+110 the hold cancelled and admin set awake; at m0+120
      profStop, profText. MIN.stats and P.minutes/drained before and after; nutrition.get on both before the first
      meal and EAT_READ_S after each.
  B   P1 under settimespeed 30: profReset + profStart, RCON settimespeed 30, B_S wall seconds, RCON settimespeed 1,
      profStop, profText; the bench counters either side (ticks, minutes) and time.snapshot.
  D   continuity with #3354 (Plan 10 S2's measure, an unchanged world age per call): bench.global
      ...bench.minute D_MINUTE_N x D_REPEAT, ...bench.handler D_HANDLER_N x D_REPEAT, NutritionRevamp.bench_fast
      D_FAST_N x1, all with prof off; then profReset + profStart, ...bench.minute D_MINUTE_N x1, profStop, profText
      (D2: the per-step split at an unchanged world age).
  C2  the burst, takeover mode, the drain left on: burstReset, rrM 0, burstOn true for C2_MINUTES game minutes,
      burstOn false, burstText; then burstReset, rrM RR_M, burstOn for C2_MINUTES, off, burstText. MIN.stats around.
  C   the once-a-minute hold, Overlay: sandbox.var NR.Mode 2, C_MODE_WAIT_S, options.mode and fast.registered read;
      stats.all admin and temp.core admin; panicTarget PANIC_T, tempTarget TEMP_T, holdUser admin; C1 (DayLength 1):
      holdReset, holdOn true for C_MINUTES game minutes, holdOn false, both rings paged. C4 (DayLength 4): sandbox.set
      DayLength 4 (the live config), then the ticks per game minute over C_PROBE_S of wall from the bench counters;
      if under C4_MIN_TPM the live change did not take and time.multiplier C4_MULT (6.27 / 37.46, x222's two
      measured rates) is set instead and the ticks per minute read again (the route used is recorded); holdReset,
      holdOn for C_MINUTES game minutes (cap C4_CAP_S), off, both rings paged; then DayLength 1 and multiplier 1
      restored, temp.core admin, NR.Mode 1 restored.
  Z   the mod-error check (server errors naming the mod's files; admin's lua_error marker).
  After teardown the server log is grepped, echo lines dropped first (CLAUDE.md s5: no probe this driver sends
  carries `minute: `, `hook failed`, `fast: ` or `options: `), for the mod's minute-failure and mode lines.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  A   every one of the nine steps ran (runs > 0 for each); the whole minute (__run) costs between 100 and 2000 us per
      run in play; MIN.stats.failures does not rise. The per-step split and the Java share are readings, not graded.
      Falsifier: a step with no runs, a per-run cost outside the band, a failure.
  B   under settimespeed 30 the per-run __run cost is within a factor 3 of A's (each run integrates about 4.7 game
      minutes instead of one). Falsifier: outside the factor.
  D   bench.minute between 200 and 800 us per call (#3354: 345-395); handler between 10 and 60 us (#3353: 18-21).
      Falsifier: a figure outside its band.
  C2  the burst costs between 100 and 2000 us per player per event; the round-robin (N = 2, m = 5: ceil(2/5) = 1
      player per event) costs about half the burst per event. Falsifier: a per-player figure outside the band.
  C1  PANIC falls between two writes (the pre-write read is under PANIC_T at every write after the first) and the
      sawtooth amplitude at DayLength 1 is under 0.1. TEMPERATURE: the write does not hold (the pre-write read
      differs from TEMP_T by more than 0.01 at most writes) -- the thermoregulator owns it. Falsifier: no fall, or
      TEMPERATURE held at the target. Graded on PANIC; TEMPERATURE is reported.
  C4  the amplitude per game minute at DayLength 4 is within a factor 2 of DayLength 1's (vanilla's decay is per game
      time). Falsifier: outside the factor. Unmeasured if neither route reached at least C4_MIN_TPM ticks a minute.
  Z   no mod error line; admin not parked.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
import glob
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
from pzt.session import (Timeline, attach_clients, make_server,  # noqa: E402
                         teardown, verify)

PROFILE = "x23-perf"
PREFIX = "x231"
SESSION = ("Plan 10b Task P1+P3: the slow minute by step in play (meals, a walk, a sleep) and under settimespeed 30, "
           "the bench minute at an unchanged world age, the EveryOneMinute burst and round-robin, and the "
           "once-a-minute PANIC/TEMPERATURE hold at DayLength 1 and 4 under Overlay, on the staged copy at dc619d0; "
           "one boot of " + PROFILE)
ARTIFACT = "perf.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/perf-dc619d0/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
BENCH_FILE = STAGE_MOD + "/common/media/lua/server/NR_Server_Bench.lua"
STAGED_AT = "dc619d0"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
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
B_SPEED = 30
B_S = 60
D_MINUTE_N = 1000
D_HANDLER_N = 1000
D_FAST_N = 100000
D_REPEAT = 3
C2_MINUTES = 60
C2_CAP_S = 80.0
RR_M = 5
C_MODE_WAIT_S = 6.0
PANIC_T = 0.5
TEMP_T = 37.5
C_MINUTES = 20
C1_CAP_S = 40.0
C_PROBE_S = 10.0
C4_MIN_TPM = 20.0
C4_MULT = round(6.27 / 37.46, 4)
C4_CAP_S = 150.0
PAGE = 80
POLL_S = 0.3
LOG_LIMIT = 400
RUN_BAND_US = (100.0, 2000.0)
B_FACTOR = 3.0
MINUTE_BAND_US = (200.0, 800.0)
HANDLER_BAND_US = (10.0, 60.0)
BURST_BAND_US = (100.0, 2000.0)
C1_AMP_MAX = 0.1
C4_FACTOR = 2.0
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
    "B": {"__run us per run vs A": f"within a factor {B_FACTOR}"},
    "D": {"minute us per call": list(MINUTE_BAND_US), "handler us per call": list(HANDLER_BAND_US)},
    "C2": {"burst us per player per event": list(BURST_BAND_US), "round-robin per event": "about half the burst"},
    "C1": {"panic falls between writes": True, "panic amplitude": f"< {C1_AMP_MAX}",
           "temperature": "not held (reported, not graded)"},
    "C4": {"amplitude per game minute vs DayLength 1": f"within a factor {C4_FACTOR}"},
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
             "bench_file": BENCH_FILE,
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/perf-dc619d0",
             "bench_note": "Every reading here is cost, not behaviour: bench.global ...minute runs one whole slow "
                           "minute per call at an unchanged world age; the burst runs each player's minute from "
                           "EveryOneMinute while the OnTick drain also runs it; the hold writes PANIC and "
                           "TEMPERATURE on every online player. No behaviour row rests on this session.",
             "timer_note": "getTimestampMs is 1 ms resolution: every per-run or per-call cost is a total over many "
                           "runs divided by their count, and is stated with its count and its ms total.",
             "call_counter_note": "the Java-call counter counts NR.call (and NR.num/obj/flag, which call it by "
                                  "table lookup); direct colon calls are not counted at run time."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The plan's Step 1 wraps the steps at OnServerStarted; NR_Server_Bench.lua loads before every adapter, so "
        "its OnServerStarted handler would run before they register. The wrap runs at the first profStart instead "
        "(long after OnServerStarted) and records the names it wrapped.",
        "Phase A's walk is player.walk out and back (WALK_DX tiles), not a sprint.",
        "Phase C has no panic source (the harness has no panic command short of zombie.near): the hold writes the "
        "floor only, as the plan allows.",
        "Phase C4 tries the live DayLength change first and falls back to time.multiplier (the ticks per game minute "
        "decide which route took; the route is recorded).",
        "Phase order A, B, D, C2, C: Overlay (C) last, so every other phase runs in the takeover mode.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}
try:
    out["meta"]["bench_sha256"] = sha256_file(os.path.join(REPO, BENCH_FILE))
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


def parse_kv(text):
    d = {}
    if isinstance(text, str):
        for k, v in re.findall(r"(\w+)=(\S+)", text):
            d[k] = num(v)
    return d


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


def hold_stats(wr, tr):
    """The sawtooth: per write after the first, the pre-write panic and temp (what one minute's decay left), the
    amplitude (target - pre), the ticks since the previous write, and the per-tick panic fall inside each gap."""
    w = [r for r in wr.get("rows", []) if len(r) == 7]
    t = [r for r in tr.get("rows", []) if len(r) == 4]
    gaps = []
    for i in range(1, len(w)):
        prev, cur = w[i - 1], w[i]
        ticks = (cur[0] - prev[0]) if cur[0] is not None and prev[0] is not None else None
        inside = [r for r in t if prev[0] is not None and cur[0] is not None and prev[0] <= r[0] <= cur[0]]
        per_tick = []
        for j in range(1, len(inside)):
            if inside[j][2] is not None and inside[j - 1][2] is not None:
                per_tick.append(inside[j - 1][2] - inside[j][2])
        gaps.append({"ticks": ticks, "pre_panic": cur[2], "pre_temp": cur[3],
                     "amp_panic": (prev[4] - cur[2]) if cur[2] is not None and prev[4] is not None else None,
                     "amp_temp": (prev[5] - cur[3]) if cur[3] is not None and prev[5] is not None else None,
                     "panic_fall_per_tick": per_tick})
    amps = [g["amp_panic"] for g in gaps if g["amp_panic"] is not None]
    tamps = [g["amp_temp"] for g in gaps if g["amp_temp"] is not None]
    ticks = [g["ticks"] for g in gaps if g["ticks"]]
    falls = [x for g in gaps for x in g["panic_fall_per_tick"]]
    return {"writes": len(w), "gaps": gaps,
            "amp_panic_mean": (sum(amps) / len(amps)) if amps else None,
            "amp_panic_max": max(amps) if amps else None, "amp_panic_min": min(amps) if amps else None,
            "amp_temp_mean": (sum(tamps) / len(tamps)) if tamps else None,
            "amp_temp_max": max(tamps) if tamps else None, "amp_temp_min": min(tamps) if tamps else None,
            "ticks_per_gap_mean": (sum(ticks) / len(ticks)) if ticks else None,
            "panic_fall_per_tick_mean": (sum(falls) / len(falls)) if falls else None,
            "temp_pre_off_target": sum(1 for g in gaps if g["pre_temp"] is not None and abs(g["pre_temp"] - TEMP_T) > 0.01),
            "panic_pre_under_target": sum(1 for g in gaps if g["pre_panic"] is not None and g["pre_panic"] < PANIC_T)}


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
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}


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


def phase_B():
    P = out["phases"]["B"] = {}
    P["minstats_before"] = minstats("B0")
    P["reset"] = lcall(SRV, f"{BENCH}.profReset", "B_reset")
    P["start_counters"] = counters("B_c0")
    P["start"] = lcall(SRV, f"{BENCH}.profStart", "B_start")
    P["speed"] = rcon(f"settimespeed {B_SPEED}", "B_speed")
    try:
        P["time_fast"] = keep(step("B_time_fast", SRV, "time.snapshot"))
        time.sleep(B_S)
    finally:
        P["restore"] = rcon("settimespeed 1", "B_restore")
        out["world_changes"]["settimespeed"] = "restored to 1 after B"
    P["stop"] = lcall(SRV, f"{BENCH}.profStop", "B_stop")
    P["end_counters"] = counters("B_c1")
    P["prof"] = prof_read("B")
    P["minstats_after"] = minstats("B1")
    P["time_after"] = keep(step("B_time1", SRV, "time.snapshot"))


def phase_D():
    P = out["phases"]["D"] = {}
    P["registered"] = gread(SRV, f"{NR}.server.fast.registered", "D_reg")
    rows = {"minute": [], "handler": [], "bench_fast": []}
    for i in range(D_REPEAT):
        rows["minute"].append(keep(step(f"D_minute_{i}", SRV, "bench.global", f"{BENCH}.minute {D_MINUTE_N}",
                                        timeout=60)))
    for i in range(D_REPEAT):
        rows["handler"].append(keep(step(f"D_handler_{i}", SRV, "bench.global", f"{BENCH}.handler {D_HANDLER_N}",
                                         timeout=60)))
    rows["bench_fast"].append(keep(step("D_fast_0", SRV, "bench.global", f"{NR}.bench_fast {D_FAST_N}", timeout=60)))
    P["bench"] = rows
    P["bench_user"] = gread(SRV, f"{BENCH}.u", "D_bench_u")
    P["reset"] = lcall(SRV, f"{BENCH}.profReset", "D2_reset")
    P["start"] = lcall(SRV, f"{BENCH}.profStart", "D2_start")
    P["minute_prof"] = keep(step("D2_minute", SRV, "bench.global", f"{BENCH}.minute {D_MINUTE_N}", timeout=60))
    P["stop"] = lcall(SRV, f"{BENCH}.profStop", "D2_stop")
    P["prof"] = prof_read("D2")


def burst_leg(tag, rr):
    L = {"rrM": rr}
    L["minstats_before"] = minstats(f"{tag}0")
    L["reset"] = lcall(SRV, f"{BENCH}.burstReset", f"{tag}_reset")
    L["set_rr"] = setp(f"{BENCH}.rrM", rr, f"{tag}_rr")
    c0 = counters(f"{tag}_c0")
    L["start_counters"] = c0
    L["on"] = setp(f"{BENCH}.burstOn", "true", f"{tag}_on")
    try:
        L["end_counters"] = wait_minute((c0["minutes"] or 0) + C2_MINUTES, f"{tag}_wait", C2_CAP_S)
    finally:
        L["off"] = setp(f"{BENCH}.burstOn", "false", f"{tag}_off")
    r = lcall(SRV, f"{BENCH}.burstText", f"{tag}_text")
    L["text"] = r.get("r1")
    L["parsed"] = parse_kv(r.get("r1"))
    L["minstats_after"] = minstats(f"{tag}1")
    return L


def phase_C2():
    P = out["phases"]["C2"] = {}
    P["registered"] = gread(SRV, f"{NR}.server.fast.registered", "C2_reg")
    P["burst"] = burst_leg("C2b", 0)
    persist()
    P["rr"] = burst_leg("C2r", RR_M)
    P["rr_restore"] = setp(f"{BENCH}.rrM", 0, "C2_rr0")


def hold_leg(tag, minutes, cap_s):
    L = {}
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
    L["stats"] = hold_stats(L["w"], L["t"])
    return L


def tpm(tag, seconds):
    a = counters(f"{tag}_a")
    time.sleep(seconds)
    b = counters(f"{tag}_b")
    if None in (a["ticks"], b["ticks"], a["minutes"], b["minutes"]) or b["minutes"] == a["minutes"]:
        return {"a": a, "b": b, "ticks_per_minute": None}
    return {"a": a, "b": b, "ticks_per_minute": (b["ticks"] - a["ticks"]) / (b["minutes"] - a["minutes"])}


def phase_C():
    P = out["phases"]["C"] = {}
    P["mode_set"] = keep(step("C_mode2", SRV, "sandbox.var", "NR.Mode 2"))
    out["world_changes"]["mode"] = "NR.Mode set to 2 for C"
    time.sleep(C_MODE_WAIT_S)
    P["overlay_mode"] = gread(SRV, f"{NR}.server.options.mode", "C_mode_read")
    P["overlay_registered"] = gread(SRV, f"{NR}.server.fast.registered", "C_reg")
    P["stats_all0"] = keep(step("C_stats_all0", SRV, "stats.all", "admin"))
    P["temp_core0"] = keep(step("C_temp_core0", SRV, "temp.core", "admin"))
    P["targets"] = {"panic": setp(f"{BENCH}.panicTarget", PANIC_T, "C_pt"),
                    "temp": setp(f"{BENCH}.tempTarget", TEMP_T, "C_tt"),
                    "user": setp(f"{BENCH}.holdUser", "admin", "C_hu")}
    P["tpm1"] = tpm("C1_tpm", C_PROBE_S / 2.0)
    P["C1"] = hold_leg("C1", C_MINUTES, C1_CAP_S)
    P["temp_core1"] = keep(step("C_temp_core1", SRV, "temp.core", "admin"))
    persist()
    try:
        P["daylength_set"] = keep(step("C4_daylength", SRV, "sandbox.set", "DayLength 4"))
        out["world_changes"]["daylength"] = "DayLength set to 4 for C4"
        time.sleep(1.0)
        P["tpm4_daylength"] = tpm("C4_tpm_dl", C_PROBE_S)
        route = "DayLength"
        r4 = P["tpm4_daylength"].get("ticks_per_minute")
        if r4 is None or r4 < C4_MIN_TPM:
            P["mult_set"] = keep(step("C4_mult", SRV, "time.multiplier", str(C4_MULT)))
            out["world_changes"]["multiplier"] = f"time.multiplier {C4_MULT} for C4"
            time.sleep(1.0)
            P["tpm4_mult"] = tpm("C4_tpm_mult", C_PROBE_S)
            route = "time.multiplier"
            r4 = P["tpm4_mult"].get("ticks_per_minute")
        P["c4_route"] = route
        if r4 is None or r4 < C4_MIN_TPM:
            P["C4_unmeasured"] = f"neither route reached {C4_MIN_TPM} ticks per game minute"
        else:
            P["C4"] = hold_leg("C4", C_MINUTES, C4_CAP_S)
    finally:
        P["daylength_restore"] = keep(step("C4_daylength1", SRV, "sandbox.set", "DayLength 1"))
        P["mult_restore"] = keep(step("C4_mult1", SRV, "time.multiplier", "1"))
        out["world_changes"]["daylength"] = "DayLength set to 4 for C4, then back to 1; time.multiplier 1"
    P["temp_core2"] = keep(step("C_temp_core2", SRV, "temp.core", "admin"))
    P["mode_restore"] = keep(step("C_mode1", SRV, "sandbox.var", "NR.Mode 1"))
    out["world_changes"]["mode"] = "NR.Mode set to 2 for C, then back to 1"
    P["tpm_after"] = tpm("C_tpm_after", C_PROBE_S / 2.0)


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()
    P["minstats"] = minstats("Z")


def body():
    order = (("S0", phase_S0), ("A", phase_A), ("B", phase_B), ("D", phase_D), ("C2", phase_C2), ("C", phase_C),
             ("Z", phase_Z))
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


def us_list(rows):
    return [num(r.get("usPerCall")) for r in rows or [] if not r.get("error")]


def grade_all():
    ph = out["phases"]
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

    B = ph.get("B") or {}
    pb = g(B, "prof", "parsed") or {}
    b_run = g(pb, "__run", "us_per_run")
    if b_run is not None and a_run:
        obs = {"prof": pb, "ratio_to_A": b_run / a_run, "start": B.get("start_counters"), "end": B.get("end_counters"),
               "mult_fast": g(B, "time_fast", "mult")}
        ok = (1.0 / B_FACTOR) <= obs["ratio_to_A"] <= B_FACTOR
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified", "outside the factor")
    else:
        grade("B", PRED["B"], {"prof": pb}, "unmeasured", "no __run reading in A or B")

    D = ph.get("D") or {}
    if D:
        mu, hu, fu = (us_list(g(D, "bench", k)) for k in ("minute", "handler", "bench_fast"))
        obs = {"minute_usPerCall": mu, "handler_usPerCall": hu, "bench_fast_usPerCall": fu,
               "minute_ms": [num(r.get("ms")) for r in g(D, "bench", "minute") or []],
               "handler_ms": [num(r.get("ms")) for r in g(D, "bench", "handler") or []],
               "bench_user": val(D.get("bench_user")), "prof_D2": g(D, "prof", "parsed"),
               "minute_prof_usPerCall": num(g(D, "minute_prof", "usPerCall"))}
        if not mu or not hu:
            grade("D", PRED["D"], obs, "unmeasured", "a bench call failed")
        else:
            ok = (all(MINUTE_BAND_US[0] <= x <= MINUTE_BAND_US[1] for x in mu)
                  and all(HANDLER_BAND_US[0] <= x <= HANDLER_BAND_US[1] for x in hu))
            grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified", "a figure outside its band")
    else:
        grade("D", PRED["D"], None, "unmeasured", "phase D not run")

    C2 = ph.get("C2") or {}
    bp, rp = g(C2, "burst", "parsed") or {}, g(C2, "rr", "parsed") or {}
    if bp.get("events") and bp.get("players"):
        b_us = 1000.0 * bp["ms"] / bp["players"]
        b_ev = 1000.0 * bp["ms"] / bp["events"]
        r_ev = (1000.0 * rp["ms"] / rp["events"]) if rp.get("events") else None
        r_us = (1000.0 * rp["ms"] / rp["players"]) if rp.get("players") else None
        obs = {"burst": bp, "rr": rp, "burst_us_per_player": b_us, "burst_us_per_event": b_ev,
               "rr_us_per_event": r_ev, "rr_us_per_player": r_us,
               "rr_over_burst_per_event": (r_ev / b_ev) if r_ev is not None and b_ev else None}
        ok = BURST_BAND_US[0] <= b_us <= BURST_BAND_US[1]
        grade("C2", PRED["C2"], obs, "as_predicted" if ok else "falsified", "a per-player figure outside the band")
    else:
        grade("C2", PRED["C2"], {"burst": bp, "rr": rp}, "unmeasured", "no burst events")

    C = ph.get("C") or {}
    s1 = g(C, "C1", "stats") or {}
    if s1.get("writes"):
        obs = {k: s1.get(k) for k in ("writes", "amp_panic_mean", "amp_panic_max", "amp_panic_min", "amp_temp_mean",
                                      "amp_temp_max", "amp_temp_min", "ticks_per_gap_mean", "panic_fall_per_tick_mean",
                                      "temp_pre_off_target", "panic_pre_under_target")}
        obs["overlay_mode"] = val(C.get("overlay_mode"))
        obs["overlay_registered"] = val(C.get("overlay_registered"))
        ngaps = len(s1.get("gaps") or [])
        amp = s1.get("amp_panic_max")
        if ngaps == 0:
            grade("C1", PRED["C1"], obs, "unmeasured", "one write only")
        else:
            falls = s1.get("panic_pre_under_target") == ngaps
            ok = falls and amp is not None and amp < C1_AMP_MAX
            v = "as_predicted" if ok else ("trivial" if (amp is not None and amp <= 0) else "falsified")
            grade("C1", PRED["C1"], obs, v, "no fall between writes, or an amplitude at or above the bound")
    else:
        grade("C1", PRED["C1"], None, "unmeasured", "no write ring")
    s4 = g(C, "C4", "stats") or {}
    if s4.get("writes") and s1.get("amp_panic_mean"):
        a4 = s4.get("amp_panic_mean")
        obs = {k: s4.get(k) for k in ("writes", "amp_panic_mean", "amp_panic_max", "amp_panic_min", "amp_temp_mean",
                                      "amp_temp_max", "amp_temp_min", "ticks_per_gap_mean", "panic_fall_per_tick_mean",
                                      "temp_pre_off_target", "panic_pre_under_target")}
        obs["route"] = C.get("c4_route")
        obs["ratio_to_C1"] = (a4 / s1["amp_panic_mean"]) if a4 is not None else None
        r = obs["ratio_to_C1"]
        ok = r is not None and (1.0 / C4_FACTOR) <= r <= C4_FACTOR
        grade("C4", PRED["C4"], obs, "as_predicted" if ok else "falsified", "outside the factor")
    else:
        grade("C4", PRED["C4"], {"route": C.get("c4_route"), "unmeasured": C.get("C4_unmeasured")}, "unmeasured",
              C.get("C4_unmeasured") or "no C4 write ring or no C1 amplitude")

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
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
