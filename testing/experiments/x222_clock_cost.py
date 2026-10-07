"""x222-clock-cost -- Plan 10 Task S2+S3 (live): the real per-player cost, the clock and the lifecycle facts, on the
FROZEN 1.0.0 spike copy (release/spike-1.0.0/NutritionRevamp/Contents/mods/NutritionRevamp, staged by Task 0 at
42784ff, MANIFEST.json sha256 b22ba31b...207a9; release/ is gitignored) whose server/NR_Server_Bench.lua carries the
S2+S3 entries appended (the bench handler and minute of the Plan 11 draft's Task 13 Step 1; the tick and minute
counters; a 64-slot ring sampled at each EveryOneMinute; a minutes-per-tick histogram; an online-list watch and an
OnNewGame stamp). The edited file's sha256 is recorded in `meta`; mod/ is never booted (Plan 10 ruling 2).

Two boots, in sequence, one at a time (two sessions):
  python testing/experiments/x222_clock_cost.py            profile x22-clock (DayLength 1, Severity 1.5, sleep on),
                                                            run prefix x222, phases S0 A B C D F E Z
  python testing/experiments/x222_clock_cost.py --default  profile x22-clock-default (the fixture's DayLength 4),
                                                            run prefix x222d, phases S0 A B Z
ONE artifact per boot, `clock.json`, plus the staged MANIFEST.json copied byte-identical beside it. Shape:
x201_release.py (step, keep, gread, persist, run_phase, grade, make_server + attach_clients, the echo-excluding log
greps, the artifact copied by the driver) with x192_persist_mod.py's respawn sequence and x132_cost.py's tick_rate.
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENT (the frozen copy's NR_Server_Bench.lua, server only, every handler gated on NR.isServer()):
  NutritionRevamp.server.bench.ticks / .minutes   +1 on every OnTick / EveryOneMinute
  .ringText()   (lua.call) the last <= 64 EveryOneMinute samples, oldest first, `ticks,minutes,worldAgeHours,wallMs;`
  .histText()   (lua.call) EveryOneMinute calls between two consecutive OnTick calls: h0..h4, h5 (five or more), hmax
  .resetHist()  (lua.call) zeroes the histogram
  .watch(n)     (lua.call) arms the online-list watch for n ticks: on any tick whose signature differs from the last,
                an event `ticks|minutes|wallMs|online|n=<size> [user#objId:A|D,...] mod{user=#objId,...}` (objId: a
                small integer per Java object, from a Lua table keyed by the object; `mod{}` is the mod's own
                NutritionRevamp.server.players.online)
  OnNewGame     an event `...|newgame|user#objId <toString> <the online signature at that moment>`; .newGameN counts
  .evText(a, b) (lua.call) events a..b as lines; r2 is the event count
  .handler() / .minute()  bench.global targets: FAST.handler(p) / P.work(u, p) on the first online player (cached)

PHASES (boot 1 order S0, A, B, C, D, F, E, Z; boot 2 S0, A, B, Z):
  S0  the ready marks, the verify rows, the players list.
  A   S3.5: on the server NutritionRevamp.server.options.severity, .readAt, SandboxVars.NR.Severity, the version.
  B   S3.1: bench ticks/minutes read, then polled until >= B_MINUTES (22) more minutes have fired (cap B_CAP_S),
      then ringText, histText (reset at B's start), and a tick.rate window of B_TICK_S on the server.
  C   S3.2: (C1) the high time speed: resetHist, ticks/minutes, `settimespeed 30` by RCON, tick.rate C_S armed, the
      window, histText, ringText, ticks/minutes, `settimespeed 1`, time.snapshot read back. (C2) the all-asleep
      fast-forward: player.sleep.hold admin and bob for C_SLEEP_S, resetHist, ticks/minutes, tick.rate armed, the
      window with asleep reads (stats.get) at its middle, histText, ringText; both holds cancelled (0) and both
      players set awake (player.sleep false); time.snapshot after.
  D   S2.1-2.3: FAST.registered and stats.calls; tick.rate D_TICK_S (takeover, baseline); then tick.rate D_TICK_S armed
      and inside it bench.global NutritionRevamp.server.bench.handler 1000 x3 and .minute 200 x3 and
      NutritionRevamp.bench_fast 100000 x1 (the #2822 instrument, same session); the window's result; bench.u (the
      player benched); FAST.stats.calls over a timed window (handler calls per tick). Overlay: sandbox.var NR.Mode 2,
      wait D_MODE_WAIT_S (the options poll rides EveryOneMinute), options.mode and FAST.registered read, tick.rate
      D_TICK_S, FAST.stats.calls over the window; then sandbox.var NR.Mode 1 and FAST.registered read again.
  F   S3.4: the reconnect of bob. time.multiplier F_MULT (slows the game clock so a game minute spans the reconnect;
      time.snapshot twice F_PROBE_S apart reads the rate it gives), watch armed for F_WATCH_TICKS, minutes read, bob
      quits (graceful), a NEW bob client from a fresh fixture restore (<run>/cbob2, as x192's c1b) attaches, minutes
      read, players list, the events; time.multiplier 1 and time.snapshot after. A refusal at any step leaves the
      arm unmeasured with the step named.
  E   S3.3: the driven respawn on admin (x192's sequence): watch armed for E_WATCH_TICKS; newGameN read;
      health.reduce admin 110; witness.chain admin isDead polled; the post-death UI polled; onRespawn; the screens
      polled; clickNext at the cap if the spawn list is still up; accept; newGameN polled to +1 (cap E_RESPAWN_CAP_S);
      E_SETTLE_S of settle; the events; then the record's dead flag and resets on the server three times
      E_DEAD_GAP_S apart (finding 2's reading, recorded and not graded).
  Z   the mod-error check (server errors naming the mod's files; admin's lua_error marker).
  After teardown the server log is grepped (echo lines dropped first; CLAUDE.md s5: no probe this driver sends
  carries `first sight`, ` left`, `is dead`, `reset record` or `fast:`) for the mod's players/store/fast lines.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  A   severity 1.5 on the server (the version dir's options file loaded and the operator's value reached the read).
      Falsifier: 1.0 (the default: the option is undeclared or unread).
  B   boot 1 (DayLength 1, a game minute 0.625 s at the server's 10-tick cap): mean OnTick calls per game minute in
      [4, 8], every ring gap >= 1 tick (h2..h5 = 0 at speed 1). Boot 2 (DayLength 4, a game minute 3.75 s): mean in
      [30, 45]. Falsifier: a mean outside the band, or a gap of 0 ticks at speed 1.
  C1  at settimespeed 30 more than one EveryOneMinute fires inside one tick: hmax >= 2 and mean minutes per tick > 1.
      Falsifier: hmax <= 1 (the clock delivers at most one minute per tick). Restored mult read back.
  C2  with both players held asleep the server fast-forwards (GameServer.main sets fastForward when every live
      player is asleep and SleepAllowed): world minutes per wall second above 3x boot 1's speed-1 rate, and hmax >= 2.
      Falsifier: the rate stays at the speed-1 rate with both asleep reads true. Unmeasured if the asleep reads are
      not both true at the window's middle.
  D   the handler costs between 20 and 300 us per call; the minute between 50 and 5000 us per call; the tick rate
      within 5 % of 10 in every window (the server's lock caps it); after the switch FAST.registered false and
      options.mode 2. Handler calls per tick under takeover ~2 (one per player per tick), ~0 under overlay.
      Falsifier: a figure outside its band (recorded as the figure; the band is the review's estimate).
  F   bob's rejoin brings a NEW IsoPlayer under the same username (a new objId for `bob` in the online list), and
      no EveryOneMinute fires during the reconnect when the multiplier read-back shows the slowed clock.
      Falsifier: the same objId. Unmeasured if the new client never reaches ready.
  E   order: the dead admin object stays in getOnlinePlayers after death (marked D); OnNewGame fires with a new
      object; the new object enters the list at or before the OnNewGame tick and the dead one leaves it; the mod's
      P.online still names the dead object at the OnNewGame tick and moves to the new one at the next minute.
      Falsifier: OnNewGame before the new object is in the list, or the dead object leaving the list at death.
      Unmeasured if no death or no post-death UI.
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
from pzt.session import (Timeline, attach_clients, make_client,  # noqa: E402
                         make_server, teardown, verify)

DEFAULT_BOOT = "--default" in sys.argv[1:]
PROFILE = "x22-clock-default" if DEFAULT_BOOT else "x22-clock"
PREFIX = "x222d" if DEFAULT_BOOT else "x222"
SESSION = ("Plan 10 Task S2+S3: the clock (OnTick per EveryOneMinute at "
           + ("the fixture's DayLength 4" if DEFAULT_BOOT else "DayLength 1, under settimespeed 30 and an all-asleep "
              "fast-forward") + ")"
           + ("" if DEFAULT_BOOT else ", the options-file load, the real per-player cost (the takeover handler and "
              "the slow-minute work) with the tick rate under takeover and overlay, a reconnect and a driven respawn")
           + " on the frozen 1.0.0 spike copy; one boot of " + PROFILE)
ARTIFACT = "clock.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/spike-1.0.0/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
BENCH_FILE = STAGE_MOD + "/common/media/lua/server/NR_Server_Bench.lua"
FROZEN_AT = "42784ff"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
NR = "NutritionRevamp"
BENCH = "NutritionRevamp.server.bench"
USER = "admin"
EXPECT_SEVERITY = 1.5
B_MINUTES = 22
B_CAP_S = 150.0 if DEFAULT_BOOT else 45.0
B_TICK_S = 10
B_BAND = (30.0, 45.0) if DEFAULT_BOOT else (4.0, 8.0)
C_SPEED = 30
C_S = 20
C_SLEEP_S = 30
C_SLEEP_WINDOW_S = 20
D_TICK_S = 15
D_HANDLER_N = 1000
D_MINUTE_N = 200
D_FAST_N = 100000
D_REPEAT = 3
D_MODE_WAIT_S = 6.0
D_CALLS_S = 5.0
HANDLER_BAND_US = (20.0, 300.0)
MINUTE_BAND_US = (50.0, 5000.0)
TICK_CAP = 10.0
F_MULT = 0.01
F_PROBE_S = 5.0
F_WATCH_TICKS = 4000
E_WATCH_TICKS = 3000
DEATH_CAP_S = 20.0
UI_CAP_S = 30.0
CREATE_CAP_S = 15.0
E_RESPAWN_CAP_S = 60.0
E_SETTLE_S = 5.0
E_DEAD_GAP_S = 2.0
KILL_HEALTH = 110
POLL_S = 0.5
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"players: first sight of |players: \w+ left|players: \w+ is dead|store: reset record|"
                         r"fast: |options: ")
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
    "A": {"server options.severity": EXPECT_SEVERITY},
    "B": {"mean ticks per game minute": list(B_BAND), "gaps of 0 ticks at speed 1": 0},
    "C1": {"hmax": ">= 2", "mean minutes per tick": "> 1", "mult restored": True},
    "C2": {"world minutes per wall second": "> 3x boot 1's speed-1 rate", "hmax": ">= 2",
           "asleep reads": "both true at the window's middle"},
    "D": {"handler us per call": list(HANDLER_BAND_US), "minute us per call": list(MINUTE_BAND_US),
          "ticks per second": f"within 5 % of {TICK_CAP} in every window", "overlay": "registered false, mode 2",
          "handler calls per tick": "~2 takeover, ~0 overlay"},
    "F": {"bob's objId after the rejoin": "new", "EveryOneMinute calls during the reconnect": "0 if the slowed "
          "clock read back"},
    "E": {"dead object in the list after death": True, "OnNewGame object": "new",
          "new object in the list at the OnNewGame tick": True, "dead object leaves the list": "by the OnNewGame tick",
          "mod P.online at the OnNewGame tick": "the dead object"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "boot": "default" if DEFAULT_BOOT else "clock", "users": list(prof.users),
    "profile": prof.report(),
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
    "meta": {"staged_mod": STAGE_MOD, "frozen_at": FROZEN_AT, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "bench_file": BENCH_FILE,
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/spike-1.0.0",
             "bench_note": "bench.global ...handler advances the benched player's stats by one tick's game time per "
                           "call and ...minute runs one whole slow minute per call: the reading is cost, not "
                           "behaviour."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The Overlay tick rate is taken in this session through the sandbox route (sandbox.var NR.Mode 2, which the "
        "mod's options poll applies at the next EveryOneMinute), not in a third boot.",
        "S3.4's 'inside one game minute' is approached by slowing the game clock (time.multiplier) so one game minute "
        "spans the reconnect; whether the multiplier took is read back and the minutes counter says whether a minute "
        "fell inside the reconnect.",
        "The phase order is F before E so the respawn (which replaces admin's object and the bench's cached player) "
        "comes last.",
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


def counters(tag):
    """The bench's ticks and minutes, read in one pass (two reads; their walls bracket them)."""
    t = gread(SRV, f"{BENCH}.ticks", f"{tag}_ticks")
    m = gread(SRV, f"{BENCH}.minutes", f"{tag}_minutes")
    return {"ticks": num(val(t)), "minutes": num(val(m)), "wall": t["wall"], "wall_after": m["wall_after"]}


def parse_ring(text):
    rows = []
    if not isinstance(text, str) or not text:
        return rows
    for part in text.split(";"):
        f = part.split(",")
        if len(f) != 4:
            continue
        rows.append({"ticks": num(f[0]), "minutes": num(f[1]), "age": num(f[2]), "ms": num(f[3])})
    return rows


def ring_stats(rows, skip_first=True):
    """Gaps in ticks between consecutive EveryOneMinute samples: count, mean, min, max, the zero-gap count."""
    gaps = []
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if a["ticks"] is None or b["ticks"] is None:
            continue
        gaps.append(b["ticks"] - a["ticks"])
    if not gaps:
        return {"n": 0}
    hist = {}
    for g in gaps:
        hist[str(int(g))] = hist.get(str(int(g)), 0) + 1
    span_ms = None
    if rows[0]["ms"] and rows[-1]["ms"]:
        span_ms = rows[-1]["ms"] - rows[0]["ms"]
    return {"n": len(gaps), "mean": sum(gaps) / len(gaps), "min": min(gaps), "max": max(gaps),
            "zero_gaps": sum(1 for g in gaps if g == 0), "hist": hist, "span_ms": span_ms,
            "minutes_span": (rows[-1]["minutes"] - rows[0]["minutes"]) if rows[0]["minutes"] is not None else None,
            "age_span_h": (rows[-1]["age"] - rows[0]["age"]) if rows[0]["age"] is not None else None}


def parse_hist(text):
    d = {}
    if isinstance(text, str):
        for k, v in re.findall(r"(h\w+)=(\S+)", text):
            d[k] = num(v)
    return d


def ring(tag):
    r = lcall(SRV, f"{BENCH}.ringText", f"{tag}_ring")
    rows = parse_ring(r.get("r1"))
    return {"call": {k: r.get(k) for k in ("ok", "r2", "r3", "err", "failedAt", "wall", "wall_after")},
            "text": r.get("r1"), "rows": rows, "stats": ring_stats(rows)}


def hist(tag):
    r = lcall(SRV, f"{BENCH}.histText", f"{tag}_hist")
    return {"text": r.get("r1"), "ticks": r.get("r2"), "minutes": r.get("r3"), "hist": parse_hist(r.get("r1")),
            "ok": r.get("ok"), "err": r.get("err"), "wall": r.get("wall")}


def events(tag, start=1):
    """Every event from `start` on, paged 40 lines per call."""
    lines, i, total = [], start, None
    for _ in range(20):
        r = lcall(SRV, f"{BENCH}.evText", f"{tag}_ev{i}", i, i + 39)
        total = num(r.get("r2"))
        txt = r.get("r1")
        if isinstance(txt, str) and txt:
            lines.extend(txt.split("\n"))
        if total is None or i + 39 >= total:
            break
        i += 40
    rows = []
    for ln in lines:
        f = ln.split("|", 4)
        if len(f) == 5:
            rows.append({"ticks": num(f[0]), "minutes": num(f[1]), "ms": num(f[2]), "kind": f[3], "text": f[4]})
        else:
            rows.append({"raw": ln})
    return {"count": total, "rows": rows}


def tick_rate(side, label, seconds, during=None):
    """Arm tick.rate, run `during()` inside the window if given, then wait for the result document."""
    after = time.time()
    arm = ack(step(f"{label}_tick_arm", side, "tick.rate", str(seconds)))
    inside = during() if during is not None else None
    result = None
    if arm.get("armed"):
        try:
            result = node(side).bus.wait_result(arm.get("result") or "tick-rate", timeout=seconds + 30, after=after)
        except (RuntimeError, TimeoutError, OSError) as e:
            result = {"error": f"{type(e).__name__}: {e}"}
    return {"arm": arm, "result": result, "inside": inside,
            "ticksPerSecond": result.get("ticksPerSecond") if isinstance(result, dict) else None,
            "worldMinutesPerSecond": result.get("worldMinutesPerSecond") if isinstance(result, dict) else None}


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
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}


def phase_A():
    P = out["phases"]["A"] = {}
    P["severity"] = gread(SRV, f"{NR}.server.options.severity", "A_severity")
    P["readAt"] = gread(SRV, f"{NR}.server.options.readAt", "A_readAt")
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "A_mode")
    P["sandboxvars_severity"] = gread(SRV, "SandboxVars.NR.Severity", "A_sv_severity")
    P["sandboxvars_mode"] = gread(SRV, "SandboxVars.NR.Mode", "A_sv_mode")
    P["version"] = gread(SRV, f"{NR}.version", "A_version")
    P["client_sandboxvars_severity"] = {who(s): gread(s, "SandboxVars.NR.Severity", f"A_{who(s)}_sv_severity")
                                        for s in CLIENT_SIDES}


def phase_B():
    P = out["phases"]["B"] = {}
    P["reset"] = lcall(SRV, f"{BENCH}.resetHist", "B_reset")
    P["start"] = counters("B_start")
    P["time_start"] = keep(step("B_time0", SRV, "time.snapshot"))
    m0 = P["start"]["minutes"]
    polls, end = [], time.time() + B_CAP_S
    while True:
        c = counters("B_poll")
        polls.append(c)
        if m0 is not None and c["minutes"] is not None and c["minutes"] - m0 >= B_MINUTES:
            break
        if time.time() >= end:
            note("B: the minute target was not reached inside the cap")
            break
        time.sleep(2.0)
    P["polls"] = polls
    P["end"] = polls[-1] if polls else None
    P["ring"] = ring("B")
    P["hist"] = hist("B")
    P["time_end"] = keep(step("B_time1", SRV, "time.snapshot"))
    P["tick_rate"] = tick_rate(SRV, "B", B_TICK_S)
    P["players_stats"] = {k: gread(SRV, f"{NR}.server.players.{k}", f"B_p_{k}") for k in ("minutes", "drained")}


def phase_C():
    P = out["phases"]["C"] = {"C1": {}, "C2": {}}
    C1 = P["C1"]
    C1["time_before"] = keep(step("C1_time0", SRV, "time.snapshot"))
    C1["players_before"] = {k: gread(SRV, f"{NR}.server.players.{k}", f"C1_p0_{k}") for k in ("minutes", "drained")}
    C1["reset"] = lcall(SRV, f"{BENCH}.resetHist", "C1_reset")
    C1["start"] = counters("C1_start")
    C1["speed"] = rcon(f"settimespeed {C_SPEED}", "C1_speed")
    try:
        C1["time_fast"] = keep(step("C1_time_fast", SRV, "time.snapshot"))
        C1["tick_rate"] = tick_rate(SRV, "C1", C_S)
        C1["hist"] = hist("C1")
        C1["end"] = counters("C1_end")
        C1["ring"] = ring("C1")
        C1["players_after"] = {k: gread(SRV, f"{NR}.server.players.{k}", f"C1_p1_{k}") for k in ("minutes", "drained")}
    finally:
        C1["restore"] = rcon("settimespeed 1", "C1_restore")
        out["world_changes"]["settimespeed"] = "restored to 1 after C1"
    C1["time_after"] = keep(step("C1_time1", SRV, "time.snapshot"))
    persist()
    if parked():
        return
    C2 = P["C2"]
    C2["holds"] = {u: keep(step(f"C2_hold_{u}", SRV, "player.sleep.hold", f"{u} {C_SLEEP_S}")) for u in ("admin", "bob")}
    try:
        time.sleep(2.0)
        C2["reset"] = lcall(SRV, f"{BENCH}.resetHist", "C2_reset")
        C2["start"] = counters("C2_start")
        C2["time_start"] = keep(step("C2_time0", SRV, "time.snapshot"))

        def middle():
            time.sleep(C_SLEEP_WINDOW_S / 2.0)
            return {u: keep(step(f"C2_asleep_{u}", SRV, "witness.chain", f"{u} isAsleep")) for u in ("admin", "bob")}
        C2["tick_rate"] = tick_rate(SRV, "C2", C_SLEEP_WINDOW_S, during=middle)
        C2["hist"] = hist("C2")
        C2["end"] = counters("C2_end")
        C2["ring"] = ring("C2")
        C2["time_end"] = keep(step("C2_time1", SRV, "time.snapshot"))
    finally:
        C2["cancel"] = {u: keep(step(f"C2_cancel_{u}", SRV, "player.sleep.hold", f"{u} 0")) for u in ("admin", "bob")}
        C2["wake"] = {u: keep(step(f"C2_wake_{u}", SRV, "player.sleep", f"{u} false")) for u in ("admin", "bob")}
        out["world_changes"]["sleep"] = "both holds cancelled and both players set awake after C2"
    time.sleep(3.0)
    C2["time_after"] = keep(step("C2_time2", SRV, "time.snapshot"))
    C2["asleep_after"] = {u: keep(step(f"C2_asleep_after_{u}", SRV, "witness.chain", f"{u} isAsleep"))
                          for u in ("admin", "bob")}


def fast_calls(tag):
    return num(val(gread(SRV, f"{NR}.server.fast.stats.calls", tag)))


def calls_window(tag):
    """FAST.stats.calls and the bench tick counter across D_CALLS_S: handler calls per tick."""
    c0, k0 = fast_calls(f"{tag}_calls0"), counters(f"{tag}_k0")
    time.sleep(D_CALLS_S)
    c1, k1 = fast_calls(f"{tag}_calls1"), counters(f"{tag}_k1")
    per = None
    if None not in (c0, c1, k0["ticks"], k1["ticks"]) and k1["ticks"] > k0["ticks"]:
        per = (c1 - c0) / (k1["ticks"] - k0["ticks"])
    return {"calls0": c0, "calls1": c1, "ticks0": k0["ticks"], "ticks1": k1["ticks"], "calls_per_tick": per}


def phase_D():
    P = out["phases"]["D"] = {}
    P["registered_before"] = gread(SRV, f"{NR}.server.fast.registered", "D_reg0")
    P["players"] = keep(step("D_players", SRV, "players"))
    P["calls_takeover"] = calls_window("D_tk")
    P["tick_baseline"] = tick_rate(SRV, "D_base", D_TICK_S)

    def benches():
        rows = {"handler": [], "minute": [], "bench_fast": []}
        for i in range(D_REPEAT):
            rows["handler"].append(keep(step(f"D_handler_{i}", SRV, "bench.global",
                                             f"{BENCH}.handler {D_HANDLER_N}", timeout=60)))
        for i in range(D_REPEAT):
            rows["minute"].append(keep(step(f"D_minute_{i}", SRV, "bench.global",
                                            f"{BENCH}.minute {D_MINUTE_N}", timeout=60)))
        rows["bench_fast"].append(keep(step("D_fast_0", SRV, "bench.global", f"{NR}.bench_fast {D_FAST_N}",
                                            timeout=60)))
        return rows
    P["tick_bench"] = tick_rate(SRV, "D_bench", D_TICK_S, during=benches)
    P["bench_user"] = gread(SRV, f"{BENCH}.u", "D_bench_u")
    P["fast_stats"] = {k: gread(SRV, f"{NR}.server.fast.stats.{k}", f"D_fs_{k}")
                       for k in ("calls", "failures", "byCharHits", "disabledAt")}
    persist()
    # Overlay through the sandbox route
    P["mode_set"] = keep(step("D_mode2", SRV, "sandbox.var", "NR.Mode 2"))
    time.sleep(D_MODE_WAIT_S)
    P["overlay_mode"] = gread(SRV, f"{NR}.server.options.mode", "D_mode_read")
    P["overlay_registered"] = gread(SRV, f"{NR}.server.fast.registered", "D_reg_overlay")
    P["calls_overlay"] = calls_window("D_ov")
    P["tick_overlay"] = tick_rate(SRV, "D_overlay", D_TICK_S)
    P["mode_restore"] = keep(step("D_mode1", SRV, "sandbox.var", "NR.Mode 1"))
    time.sleep(D_MODE_WAIT_S)
    P["restored_mode"] = gread(SRV, f"{NR}.server.options.mode", "D_mode_read2")
    P["restored_registered"] = gread(SRV, f"{NR}.server.fast.registered", "D_reg_restored")
    out["world_changes"]["mode"] = "NR.Mode set to 2 for the overlay reading, then back to 1"


def phase_F():
    global clients
    P = out["phases"]["F"] = {}
    P["mult_set"] = keep(step("F_mult", SRV, "time.multiplier", str(F_MULT)))
    P["time0"] = keep(step("F_time0", SRV, "time.snapshot"))
    time.sleep(F_PROBE_S)
    P["time1"] = keep(step("F_time1", SRV, "time.snapshot"))
    try:
        P["ev_start"] = num(lcall(SRV, f"{BENCH}.evText", "F_evn", 1, 0).get("r2"))
        P["watch"] = lcall(SRV, f"{BENCH}.watch", "F_watch", F_WATCH_TICKS)
        time.sleep(1.0)
        P["before"] = counters("F_before")
        old = clients.get("bob")
        P["quit_wall"] = wall()
        try:
            P["quit_rc"] = old.quit() if old is not None else None
        except Exception as e:                 # noqa: BLE001
            P["quit_error"] = f"{type(e).__name__}: {e}"
        P["quit_done_wall"] = wall()
        P["after_quit"] = counters("F_after_quit")
        P["players_after_quit"] = keep(step("F_players_q", SRV, "players"))
        base = os.path.join(run_dir, "cbob2")
        os.makedirs(base, exist_ok=True)
        c, restored = make_client(base, "bob", server, rec_fx)
        started.append(c)
        P["new_client"] = {"base": os.path.relpath(base, run_dir), "restored": restored, "start_wall": wall()}
        c.start()
        tl.mark("client_launch", user="bob2", restored=restored)
        try:
            took = c.wait_ready(timeout=prof.client_timeout)
            tl.mark("client_ready", user="bob2", took=took)
            P["new_client"]["ready_wall"] = wall()
            clients = dict(clients)
            clients["bob"] = c
        except Exception as e:                 # noqa: BLE001
            P["new_client"]["ready_error"] = f"{type(e).__name__}: {e}"
        time.sleep(3.0)
        P["after_rejoin"] = counters("F_after_rejoin")
        P["players_after_rejoin"] = keep(step("F_players_r", SRV, "players"))
        P["bob_version"] = gread(BOB, f"{NR}.version", "F_bob_version")
        P["events"] = events("F", int(P["ev_start"] or 0) + 1)
        P["time2"] = keep(step("F_time2", SRV, "time.snapshot"))
    finally:
        P["mult_restore"] = keep(step("F_mult1", SRV, "time.multiplier", "1"))
        out["world_changes"]["multiplier"] = "time.multiplier set back to 1 after F"
    P["time3"] = keep(step("F_time3", SRV, "time.snapshot"))


def phase_E():
    P = out["phases"]["E"] = {}
    s, c = SRV, ADMIN
    P["ev_start"] = num(lcall(s, f"{BENCH}.evText", "E_evn", 1, 0).get("r2"))
    P["watch"] = lcall(s, f"{BENCH}.watch", "E_watch", E_WATCH_TICKS)
    P["newGameN0"] = num(val(gread(s, f"{BENCH}.newGameN", "E_ng0")))
    P["record_before"] = {k: gread(s, f"{NR}.server.store.records.{USER}.{k}", f"E_rec0_{k}") for k in ("dead", "resets")}
    P["reduce"] = keep(step("E_reduce", s, "health.reduce", f"{USER} {KILL_HEALTH}"))
    P["reduce_wall"] = wall()
    polls, end, dead_wall = [], time.time() + DEATH_CAP_S, None
    while True:
        r = keep(step("E_isDead", s, "witness.chain", f"{USER} isDead"))
        polls.append({"wall": r.get("wall"), "value": r.get("value"), "ok": r.get("ok"), "error": r.get("error")})
        if str(r.get("value")).lower() == "true":
            dead_wall = r.get("wall")
            break
        if time.time() >= end:
            break
        time.sleep(POLL_S)
    P["isDead_polls"], P["isDead_wall"] = polls, dead_wall
    P["after_death"] = counters("E_after_death")
    persist()
    if parked():
        P["unmeasured"] = "admin parked at the death"
        P["events"] = events("E", int(P["ev_start"] or 0) + 1)
        return
    ui_polls, end, ui_wall = [], time.time() + UI_CAP_S, None
    while True:
        r = keep(step("E_ui", c, "lua.callm", "ISPostDeathUI.instance.0 getIsVisible"))
        ui_polls.append({"wall": r.get("wall"), "ok": r.get("ok"), "r1": r.get("r1"), "failedAt": r.get("failedAt"),
                         "err": r.get("err")})
        if r.get("ok"):
            ui_wall = r.get("wall")
            break
        if time.time() >= end:
            break
        time.sleep(1.0)
    P["ui_polls"], P["ui_wall"] = ui_polls, ui_wall
    if ui_wall is None:
        P["unmeasured"] = "the post-death UI never appeared at ISPostDeathUI.instance.0"
        P["events"] = events("E", int(P["ev_start"] or 0) + 1)
        return
    P["onRespawn"] = keep(step("E_onRespawn", c, "lua.callm", "ISPostDeathUI.instance.0 onRespawn"))
    scr, end = [], time.time() + CREATE_CAP_S
    while True:
        row = {"wall": wall(),
               "spawn": keep(step("E_spawn_vis", c, "lua.callm", "CoopMapSpawnSelect.instance getIsVisible")).get("r1"),
               "profession": keep(step("E_prof_vis", c, "lua.callm",
                                       "CharacterCreationProfession.instance getIsVisible")).get("r1"),
               "main": keep(step("E_main_vis", c, "lua.callm", "CharacterCreationMain.instance getIsVisible")).get("r1")}
        scr.append(row)
        if row["main"] is True and row["spawn"] is not True and row["profession"] is not True:
            break
        if time.time() >= end:
            break
        time.sleep(1.0)
    P["screens"] = scr
    if scr and scr[-1].get("spawn") is True:
        P["clickNext"] = keep(step("E_clickNext", c, "lua.callm", "CoopMapSpawnSelect.instance clickNext"))
        time.sleep(3.0)
    P["accept"] = keep(step("E_accept", c, "lua.callm", "CoopCharacterCreation.instance accept"))
    P["accept_wall"] = wall()
    ng, end = [], time.time() + E_RESPAWN_CAP_S
    while True:
        v = num(val(gread(s, f"{BENCH}.newGameN", "E_ng")))
        ng.append({"wall": wall(), "newGameN": v})
        if v is not None and P["newGameN0"] is not None and v > P["newGameN0"]:
            break
        if time.time() >= end:
            break
        time.sleep(POLL_S)
    P["newGame_polls"] = ng
    time.sleep(E_SETTLE_S)
    P["after_respawn"] = counters("E_after_respawn")
    P["events"] = events("E", int(P["ev_start"] or 0) + 1)
    P["players_after"] = keep(step("E_players", s, "players"))
    reads = []
    for i in range(3):
        reads.append({"wall": wall(), **{k: val(gread(s, f"{NR}.server.store.records.{USER}.{k}", f"E_rec{i}_{k}"))
                                         for k in ("dead", "resets")},
                      "minutes": counters(f"E_rec{i}")["minutes"]})
        time.sleep(E_DEAD_GAP_S)
    P["record_after"] = reads


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()


def body():
    order = (("S0", phase_S0), ("A", phase_A), ("B", phase_B), ("Z", phase_Z)) if DEFAULT_BOOT else \
        (("S0", phase_S0), ("A", phase_A), ("B", phase_B), ("C", phase_C), ("D", phase_D), ("F", phase_F),
         ("E", phase_E), ("Z", phase_Z))
    for name, fn in order:
        run_phase(name, fn)
        if parked() and name not in ("Z", "F"):
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
    if A:
        sev = num(val(A.get("severity")))
        obs = {"severity": sev, "readAt": val(A.get("readAt")), "SandboxVars.NR.Severity": val(A.get("sandboxvars_severity")),
               "mode": val(A.get("mode"))}
        if sev is None:
            grade("A", PRED["A"], obs, "unmeasured", "no severity read")
        elif DEFAULT_BOOT:
            grade("A", {"server options.severity": 1.0}, obs, "as_predicted" if abs(sev - 1.0) < 1e-9 else "falsified",
                  "a severity other than the default with no override")
        else:
            grade("A", PRED["A"], obs, "as_predicted" if abs(sev - EXPECT_SEVERITY) < 1e-9 else "falsified",
                  "severity 1.0: the option undeclared or unread")
    else:
        grade("A", PRED["A"], None, "unmeasured", "phase A not run")

    B = ph.get("B") or {}
    st = g(B, "ring", "stats") or {}
    if st.get("n"):
        obs = {"ring": {k: st.get(k) for k in ("n", "mean", "min", "max", "zero_gaps", "hist", "span_ms",
                                               "minutes_span", "age_span_h")},
               "hist": g(B, "hist", "hist"), "ticksPerSecond": g(B, "tick_rate", "ticksPerSecond"),
               "worldMinutesPerSecond": g(B, "tick_rate", "worldMinutesPerSecond")}
        ok = B_BAND[0] <= st["mean"] <= B_BAND[1] and st.get("zero_gaps") == 0
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified", "a mean outside the band or a zero gap")
    else:
        grade("B", PRED["B"], None, "unmeasured", "no ring read")

    if DEFAULT_BOOT:
        pass
    else:
        C = ph.get("C") or {}
        C1 = C.get("C1") or {}
        h1 = g(C1, "hist", "hist") or {}
        s1, e1 = C1.get("start") or {}, C1.get("end") or {}
        if h1 and s1.get("ticks") is not None and e1.get("ticks") is not None:
            dt, dm = e1["ticks"] - s1["ticks"], e1["minutes"] - s1["minutes"]
            obs = {"hist": h1, "ticks": dt, "minutes": dm, "minutes_per_tick": (dm / dt) if dt else None,
                   "ring": {k: g(C1, "ring", "stats", k) for k in ("n", "mean", "zero_gaps", "hist")},
                   "worldMinutesPerSecond": g(C1, "tick_rate", "worldMinutesPerSecond"),
                   "ticksPerSecond": g(C1, "tick_rate", "ticksPerSecond"),
                   "speed_ack": C1.get("speed"), "restore_ack": C1.get("restore"),
                   "mult_fast": g(C1, "time_fast", "mult"), "mult_after": g(C1, "time_after", "mult"),
                   "mult_before": g(C1, "time_before", "mult")}
            ok = (h1.get("hmax") or 0) >= 2 and obs["minutes_per_tick"] is not None and obs["minutes_per_tick"] > 1
            grade("C1", PRED["C1"], obs, "as_predicted" if ok else "falsified", "hmax <= 1")
        else:
            grade("C1", PRED["C1"], None, "unmeasured", "no histogram or counters")
        C2 = C.get("C2") or {}
        h2 = g(C2, "hist", "hist") or {}
        s2, e2 = C2.get("start") or {}, C2.get("end") or {}
        asleep = {u: g(C2, "tick_rate", "inside", u, "value") for u in ("admin", "bob")}
        base_rate = g(B, "tick_rate", "worldMinutesPerSecond")
        rate = g(C2, "tick_rate", "worldMinutesPerSecond")
        if h2 and s2.get("ticks") is not None and e2.get("ticks") is not None:
            dt, dm = e2["ticks"] - s2["ticks"], e2["minutes"] - s2["minutes"]
            obs = {"hist": h2, "ticks": dt, "minutes": dm, "minutes_per_tick": (dm / dt) if dt else None,
                   "worldMinutesPerSecond": rate, "speed1_worldMinutesPerSecond": base_rate,
                   "ticksPerSecond": g(C2, "tick_rate", "ticksPerSecond"), "asleep_mid": asleep,
                   "holds": {u: {k: g(C2, "holds", u, k) for k in ("armed", "after", "error")} for u in ("admin", "bob")},
                   "ring": {k: g(C2, "ring", "stats", k) for k in ("n", "mean", "zero_gaps", "hist")},
                   "mult_start": g(C2, "time_start", "mult"), "mult_end": g(C2, "time_end", "mult"),
                   "mult_after": g(C2, "time_after", "mult")}
            both = all(str(v).lower() == "true" for v in asleep.values())
            fast = rate is not None and base_rate is not None and rate > 3 * base_rate
            if not both and not fast:
                grade("C2", PRED["C2"], obs, "unmeasured", "the asleep reads were not both true")
            else:
                grade("C2", PRED["C2"], obs, "as_predicted" if (fast and (h2.get("hmax") or 0) >= 2) else "falsified",
                      "no fast-forward with both asleep")
        else:
            grade("C2", PRED["C2"], None, "unmeasured", "no histogram or counters")

        D = ph.get("D") or {}
        if D:
            tb = D.get("tick_bench") or {}
            ins = tb.get("inside") or {}
            hu, mu, fu = us_list(ins.get("handler")), us_list(ins.get("minute")), us_list(ins.get("bench_fast"))
            rates = {k: g(D, k, "ticksPerSecond") for k in ("tick_baseline", "tick_bench", "tick_overlay")}
            obs = {"handler_usPerCall": hu, "minute_usPerCall": mu, "bench_fast_usPerCall": fu,
                   "handler_ms": [num(r.get("ms")) for r in ins.get("handler") or []],
                   "minute_ms": [num(r.get("ms")) for r in ins.get("minute") or []],
                   "bench_errors": [r.get("error") for k in ("handler", "minute", "bench_fast")
                                    for r in ins.get(k) or [] if r.get("error")],
                   "bench_user": val(D.get("bench_user")), "ticksPerSecond": rates,
                   "calls_per_tick": {"takeover": g(D, "calls_takeover", "calls_per_tick"),
                                      "overlay": g(D, "calls_overlay", "calls_per_tick")},
                   "registered": {"before": val(D.get("registered_before")), "overlay": val(D.get("overlay_registered")),
                                  "restored": val(D.get("restored_registered"))},
                   "overlay_mode": val(D.get("overlay_mode")), "restored_mode": val(D.get("restored_mode"))}
            if not hu or not mu:
                grade("D", PRED["D"], obs, "unmeasured", "a bench call failed")
            else:
                ok = (all(HANDLER_BAND_US[0] <= x <= HANDLER_BAND_US[1] for x in hu)
                      and all(MINUTE_BAND_US[0] <= x <= MINUTE_BAND_US[1] for x in mu)
                      and all(r is not None and abs(r - TICK_CAP) <= 0.05 * TICK_CAP for r in rates.values())
                      and obs["registered"]["overlay"] is False and num(obs["overlay_mode"]) == 2)
                grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified", "a figure outside its band")
        else:
            grade("D", PRED["D"], None, "unmeasured", "phase D not run")

        F = ph.get("F") or {}
        if F:
            rows = g(F, "events", "rows") or []
            bob_ids = []
            for r in rows:
                if r.get("kind") == "online":
                    for m in re.finditer(r"bob(#\d+):", r.get("text", "")):
                        if m.group(1) not in bob_ids:
                            bob_ids.append(m.group(1))
            dmin = None
            if g(F, "before", "minutes") is not None and g(F, "after_rejoin", "minutes") is not None:
                dmin = F["after_rejoin"]["minutes"] - F["before"]["minutes"]
            obs = {"bob_object_ids_seen": bob_ids, "minutes_during_reconnect": dmin,
                   "mult_set": F.get("mult_set"), "time0": F.get("time0"), "time1": F.get("time1"),
                   "ready": "ready_wall" in (F.get("new_client") or {}), "quit_rc": F.get("quit_rc"),
                   "online_events": [r.get("text") for r in rows if r.get("kind") == "online"][:20]}
            if not obs["ready"]:
                grade("F", PRED["F"], obs, "unmeasured", "the new bob client never reached ready")
            else:
                ok = len(bob_ids) >= 2
                grade("F", PRED["F"], obs, "as_predicted" if ok else "falsified", "the same objId after the rejoin")
        else:
            grade("F", PRED["F"], None, "unmeasured", "phase F not run")

        E = ph.get("E") or {}
        if E and not E.get("unmeasured"):
            rows = g(E, "events", "rows") or []
            obs = {"events": [{k: r.get(k) for k in ("ticks", "minutes", "ms", "kind", "text")} for r in rows][:40],
                   "isDead_wall": E.get("isDead_wall"), "accept_wall": E.get("accept_wall"),
                   "accept": {k: g(E, "accept", k) for k in ("ok", "err", "failedAt")},
                   "newGame_polls_last": (E.get("newGame_polls") or [None])[-1],
                   "record_after": E.get("record_after")}
            newgame = [r for r in rows if r.get("kind") == "newgame"]
            grade("E", PRED["E"], obs, "as_predicted" if newgame else "unmeasured",
                  "graded by hand from the event order (the order is the reading); no OnNewGame event is unmeasured",
                  {"note": "the verdict here says only whether OnNewGame fired; the order is read off the events"})
        else:
            grade("E", PRED["E"], E.get("unmeasured") if E else None, "unmeasured",
                  (E or {}).get("unmeasured") or "phase E not run")

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
