"""x260b-chain -- Plan 11f Task 3 session 2 (live): the first live restart of the mod's file store. Session 1's
(x260_cadence.py) `<run>/server` folder is COPIED into this run's folder and booted again with
`make_server(reuse=True)` (research 01-harness-facts s2: each session its own run folder, so a failed session never
damages the saved state), with a fresh client restore. The record, P, the trail, nicH, the monotony table and the
world clock are compared across the restart; 30 game minutes are run on; the departure flush ends it, as in session 1.
One boot of profile x26-chain (x26-cadence byte for byte below its header but the description: fixture default,
admin -debug, Nutrition false, DayLength 1, the staged copy at 983ebd6 plus TKX_StudyFoods). Written BEFORE the boot
with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x260b_chain.py <session 1 run dir or run id (testing/runs/<id>)>

THE INSTRUMENTS: as session 1 (harness H1 lua.read and H2 minute.ring; 10f25f3, 6c98c5c).

PHASES (order PRE, A, L, G, R, D, Z; then the slot files and the replay):
  PRE (before the boot, no game process): session 1's cadence.json read (its last ring rows, its slot reading, its
      last snapshot, its player.json); session 1's <run>/server copied whole to <run>/server; the copied slot files'
      sha256 against session 1's recorded ones, and the newest complete slot line parsed (the line the store loads).
  A   the server booted on the copy, BEFORE the client: time.snapshot (the clock continued: the world saved at
      session 1's clean quit); lua.read record:admin (no record expected: the store loads at first sight);
      minute.ring admin start <paths> (session 1's record and global paths, the trail kcal slots of the six hours
      from three before the boot's hour), so the ring sees the first sight.
  L   the client attached (fresh fixture restore); the verify rows; then lua.read record:admin polled from the
      first moment until the record is present (cap LOAD_CAP_S): the compared paths (satiety P S L t nicH, the 25
      trail kcal slots and body.trail.at, monotony's Mixed650 n and last, firstSeen, resets, body.sex, body.fm,
      body.lm, kineticsAge, lastSeen, body.inDay); stats.all admin; time.snapshot.
  G   GO_MIN game minutes at speed 1 waited on the world age; lua.read record:admin again.
  R   minute.ring admin read, page after page; each document copied byte-identical.
  D   the departure flush as session 1: RCON settimespeed 1, time.snapshot q0, client quit, poll online.admin absent
      and store.file.lastWrite.admin >= q0 (cap FLUSH_CAP_S), the flushed line, the ring tail and stop. The clean
      server quit (teardown) follows.
  After: this session's slot files copied; the replay: tools/replay_live.replay_live over this session's ring from
      session 1's newest slot line (the record the store loaded), start-stats from session 1's last online ring row
      (the stats the player save holds), session 1's player.json, no events.

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / trivial / unmeasured):
  CLOCK  the boot's world age is at or after session 1's last reading (the later of its D_end_t snapshot and its
         ring's last row) and within CLOCK_MAX_M game minutes of it (the seconds to session 1's quit and world save;
         a world not saved would read the fixture's age, hours earlier). Falsifier: earlier, or later by more.
  LOAD   the first record read after the load: firstSeen, resets and body.sex equal the slot line's; monotony's
         Mixed650 n and last equal; every trail kcal slot equals the slot line's except the slots of the hours from
         floor(slot t) to floor(read t); satiety.t >= the slot's t; satiety.P <= the slot's P and > 0 when the slot's
         P > 0 (P only decays without an eat); nicH >= the slot's. Falsifier: any one not so.
  SEED   writer.stats.seeded reads 0 on every ring row of this session (the loaded P is present, so the writer never
         re-seeds P from HUNGER: no seed jump). Falsifier: a non-zero row.
  REPLAY the replay from the slot line over this session's ring passes the plan's tolerances (HUNGER 0.002, es
         0.005, L 0.5 %). Falsifier: a finding (named, never tuned).
  F      the departure flush as session 1.
  Z      no mod error line on the server; admin not parked.

READINGS (not graded): HUNGER across the restart (session 1's last online row, this session's first online row
before the first write, its first row after it, and the replay's); the record drift session 1's stop could lose
(session 1's newest slot t against its last online row) and this session's own; the restart's gap in game minutes
(the first drain's dt, clamped by the mod at 60).

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. Free host
memory is read before the boot and the boot refused under MEM_MIN_GB (CLAUDE.md s5).
"""
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
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

PROFILE = "x26-chain"
PREFIX = "x260b"
SESSION = ("Plan 11f Task 3 session 2: the first live restart of the file store -- session 1's server folder copied "
           "and booted again (reuse=True), the record, P, the trail, nicH, monotony and the clock compared, 30 game "
           "minutes run on, the departure flush; one boot of " + PROFILE)
ARTIFACT = "chain.json"
S1_ARTIFACT = "cadence.json"
MANIFEST_NAME = "MANIFEST.json"
USER = "admin"
SRV = "server"
CLI = "client"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/x260-cadence/NutritionRevamp"
STAGED_AT = "983ebd6"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_CORE = LUA_DIR + "/shared/PZTestKit_Core.lua"
GAME_JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
NR = "NutritionRevamp"
MEM_MIN_GB = 12.0
GO_MIN = 30
LOAD_CAP_S = 40.0
FLUSH_CAP_S = 90.0
WAIT_SLACK_S = 60.0
RESULT_WAIT_S = 30.0
POLL_S = 0.3
LOG_LIMIT = 400
TRAIL_HOURS = 6
CLOCK_MAX_M = 60.0
TOL_EXTRA = {"satiety.P": ("rel", 0.005), "satiety.S": ("abs", 1e-6), "stomachFill": ("abs", 0.002)}
RING_RECORD = ("satiety.P", "satiety.S", "satiety.L", "satiety.t", "satiety.nicH", "body.energyState", "body.met",
               "acute.debtH", "stomachFill", "stomach.liquid", "stomach.buffer.calories", "stomach.buffer.water",
               "body.inDay", "body.trail.at", "monotony", "monotony.t.[TKX.Mixed650].n", "kineticsAge", "lastSeen")
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.seeded",
                "_G.NutritionRevamp.server.players.served", "_G.NutritionRevamp.server.players.ticksLast",
                "_G.NutritionRevamp.server.intake.stats.eats", "_G.NutritionRevamp.server.intake.stats.landed",
                "_G.NutritionRevamp.server.store.file.stats.writes",
                "_G.NutritionRevamp.server.store.file.lastWrite.admin")
COMPARE = (("satiety.P", "satiety.S", "satiety.L", "satiety.t", "satiety.nicH", "body.trail.at") +
           tuple(f"body.trail.kcal.{i}" for i in range(1, 26)) +
           ("monotony.t.[TKX.Mixed650].n", "monotony.t.[TKX.Mixed650].last", "firstSeen", "resets", "body.sex",
            "body.fm", "body.lm", "kineticsAge", "lastSeen", "body.inDay", "stomach.buffer.calories",
            "stomach.liquid"))
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin",
               "NutritionRevamp.server.store.file.stats.writes")
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}
START_STATS = ("HUNGER", "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS")
SEEDED = "_G.NutritionRevamp.server.writer.stats.seeded"
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|store: |writer: |players: first sight")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

if len(sys.argv) < 2:
    print(__doc__.split("USAGE: ")[1].splitlines()[0])
    sys.exit(2)
S1_DIR = sys.argv[1] if os.path.isdir(sys.argv[1]) else os.path.join(REPO, "testing", "runs", sys.argv[1])
prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
copied = []


def wall():
    return round(time.time() - t0, 3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def free_gb():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip().splitlines()[-1])
    except Exception as e:                     # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def stray_clients():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ProjectZomboid64.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=60)
        return [ln for ln in r.stdout.splitlines() if "ProjectZomboid64" in ln]
    except Exception as e:                     # noqa: BLE001
        return [f"{type(e).__name__}: {e}"]


PRED = {
    "CLOCK": {"boot age - session 1 last reading age, game minutes": [0, CLOCK_MAX_M]},
    "LOAD": {"firstSeen, resets, body.sex": "equal the slot line", "monotony Mixed650 n, last": "equal",
             "trail kcal slots": "equal but the hours floor(slot t)..floor(read t)", "satiety.t": ">= slot",
             "satiety.P": "<= slot and > 0 when the slot's > 0", "nicH": ">= slot"},
    "SEED": {"writer.stats.seeded on every ring row": 0},
    "REPLAY": {"diff ok": True, "tolerances": "HUNGER 0.002, es 0.005, L 0.5 %"},
    "F": {"online.admin": "absent", "lastWrite.admin >= q0": True, "within s": FLUSH_CAP_S},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"), "build": rec_fx.get("build")},
    "argv": sys.argv[1:], "session1_dir": S1_DIR,
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
    "acceptance_run": "session 1 (x260) is the harness's acceptance run; this session reuses H1 and H2",
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "host": {"free_gb_before_boot": free_gb(), "mem_min_gb": MEM_MIN_GB, "stray_clients": stray_clients()},
    "meta": {"staged_mod": STAGE_ROOT + "/Contents/mods/NutritionRevamp", "staged_at": STAGED_AT,
             "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "chain_note": "session 1's <run>/server copied whole into this run folder and booted with "
                           "make_server(reuse=True); the client is a fresh fixture restore (restore_client refuses "
                           "an existing folder); the character persists server-side",
             "phase_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute"},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED", "S1_DIR")},
    "predictions": PRED,
    "deviations": [],
    "world_changes": {"restored": "session 1's server folder copied; the admin client restored from fixture default",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "readings": {},
}
try:
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    out["meta"]["harness_core_sha256"] = sha256_file(os.path.join(REPO, HARNESS_CORE))
    out["meta"]["jar_bytes"] = os.path.getsize(GAME_JAR)
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


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parked():
    c = clients.get(USER) if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def lread(side, root, paths, tag):
    return keep(step(tag, side, "lua.read", " ".join([root] + list(paths))))


def gread(name, tag):
    return keep(step(tag, SRV, "lua.global", name))


def snap(tag):
    a = keep(step(tag, SRV, "time.snapshot"))
    return {k: a.get(k) for k in ("worldAge", "hour", "minutes", "mult", "wall", "wall_after")} | {"tag": tag}


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


def wait_age(target, tag, cap_s):
    end = time.time() + cap_s
    last = None
    while True:
        last = snap(tag)
        a = num(last.get("worldAge"))
        if a is not None and a >= target:
            return last
        if time.time() >= end:
            note(f"{tag}: world age {target} not reached inside {cap_s} s (last {a})")
            return last
        time.sleep(POLL_S)


def wait_doc(name, after):
    try:
        return server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
    except Exception as e:                     # noqa: BLE001
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
    except Exception as e:                     # noqa: BLE001
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def rec_get(rec, dotted):
    """A value from a decoded slot record by lua.read's grammar (a [..] segment literal; a numeric segment tries the
    string key, then a list index)."""
    segs = re.findall(r"\[([^\]]*)\]|([^.\[\]]+)", dotted)
    node_ = rec
    for br, plain in segs:
        key = br or plain
        if isinstance(node_, dict):
            if key in node_:
                node_ = node_[key]
            elif not br and re.fullmatch(r"\d+", key) and int(key) in node_:
                node_ = node_[int(key)]
            else:
                return None
        elif isinstance(node_, list) and not br and re.fullmatch(r"\d+", key):
            i = int(key) - 1
            if 0 <= i < len(node_):
                node_ = node_[i]
            else:
                return None
        else:
            return None
    return node_


def parse_slots(root):
    files = []
    best = None
    for f in sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", "p_*_*.json"), recursive=True)):
        row = {"path": f, "bytes": os.path.getsize(f), "sha256": sha256_file(f)}
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
            line = text.splitlines()[-1] if text.strip() else ""
            doc = json.loads(line) if line else None
            rec = (doc or {}).get("rec") or {}
            row.update({"gen": (doc or {}).get("gen"), "done": (doc or {}).get("done"),
                        "satiety_t": (rec.get("satiety") or {}).get("t"), "lastSeen": rec.get("lastSeen")})
            if row["done"] and (best is None or (row["gen"] or -1) > (best["gen"] or -1)):
                best = row
                best["_line"] = line
                best["_rec"] = rec
        except (OSError, ValueError, IndexError) as e:
            row["parse_error"] = f"{type(e).__name__}: {e}"
        files.append(row)
    return files, best


def stats_of(a):
    st = a.get("stats") or {}
    o = {}
    for k, cam in STAT_NAMES.items():
        v = st.get(k, st.get(cam))
        if num(v) is not None:
            o[k] = v
    return o


def read_ring_files(d, files):
    rows = {}
    for f in files:
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in doc.get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)]


# ---------------------------------------------------------------- session 1 and the copy
S1 = {}


def phase_PRE():
    P = out["phases"]["PRE"] = {}
    with open(os.path.join(S1_DIR, S1_ARTIFACT), encoding="utf-8") as fh:
        s1 = json.load(fh)
    S1["doc"] = s1
    P["s1_run_id"] = s1.get("run_id")
    P["s1_verdicts"] = {k: v.get("verdict") for k, v in (s1.get("verdicts") or {}).items()}
    P["s1_server_stop_wall"] = s1.get("server_stop_wall")
    P["s1_teardown_marks"] = [it for it in (s1.get("timeline") or []) if it.get("phase") in
                              ("client_quit", "server_stopped")]
    P["s1_ring_paths"] = g(s1, "phases", "H", "ring_paths")
    P["s1_last_snap"] = g(s1, "phases", "D", "end_snap")
    P["s1_slots"] = g(s1, "slots")
    rows = read_ring_files(S1_DIR, g(s1, "readings", "ring_files") or [])
    on = [r for r in rows if r.get("on") is not False and not r.get("norec")]
    S1["rows"] = rows
    S1["last_on"] = on[-1] if on else None
    P["s1_ring_rows"] = len(rows)
    P["s1_last_online_row"] = S1["last_on"]
    P["s1_last_row"] = rows[-1] if rows else None
    try:
        with open(os.path.join(S1_DIR, "player.json"), encoding="utf-8") as fh:
            S1["player"] = json.load(fh)
    except (OSError, ValueError) as e:
        S1["player"] = None
        note(f"PRE: session 1's player.json: {type(e).__name__}: {e}")
    P["s1_player"] = S1["player"]
    src = os.path.join(S1_DIR, "server")
    if not os.path.isdir(os.path.join(src, "Server")):
        raise RuntimeError(f"session 1 has no server cache at {src}")
    t_c = time.time()
    shutil.copytree(src, os.path.join(run_dir, "server"))
    P["copy_seconds"] = round(time.time() - t_c, 2)
    files, best = parse_slots(os.path.join(run_dir, "server"))
    s1_sha = {os.path.basename(r.get("path", "")): r.get("sha256") for r in (g(s1, "slots", "files") or [])}
    P["slots"] = [{k: v for k, v in r.items() if not k.startswith("_")} | {"rel": os.path.relpath(r["path"], run_dir)
                  .replace(os.sep, "/"), "equals_s1": s1_sha.get(os.path.basename(r["path"])) == r["sha256"]}
                  for r in files]
    if best is None:
        raise RuntimeError("no complete slot file in the copy")
    S1["slot_line"] = best["_line"]
    S1["slot_rec"] = best["_rec"]
    P["newest"] = os.path.basename(best["path"])
    P["newest_gen"] = best.get("gen")
    P["slot_satiety_t"] = best.get("satiety_t")
    P["slot_values"] = {p: rec_get(best["_rec"], p) for p in COMPARE}
    with open(os.path.join(run_dir, "start.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(best["_line"])
    copied.append("start.json")
    st = {k: S1["last_on"][k] for k in START_STATS if S1["last_on"] and num(S1["last_on"].get(k)) is not None}
    with open(os.path.join(run_dir, "start-stats.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)
    copied.append("start-stats.json")
    if S1["player"] is not None:
        with open(os.path.join(run_dir, "player.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(S1["player"], fh, indent=1, sort_keys=True)
        copied.append("player.json")
    P["start_stats"] = st


# ---------------------------------------------------------------- phases
def phase_A():
    P = out["phases"]["A"] = {}
    P["boot_snap"] = snap("A_boot_t")
    P["record_before_client"] = lread(SRV, f"record:{USER}", ["satiety.P", "satiety.t"], "A_rec0")
    a = num(P["boot_snap"].get("worldAge")) or 0.0
    h0 = int(math.floor(a)) - 3
    slots = [f"body.trail.kcal.{(h0 + i) % 25 + 1}" for i in range(TRAIL_HOURS)]
    paths = list(RING_RECORD) + slots + list(RING_GLOBALS)
    P["ring_paths"] = paths
    P["ring_start"] = keep(step("A_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))


def phase_L():
    P = out["phases"]["L"] = {}
    end = time.time() + LOAD_CAP_S
    tries = 0
    first = None
    while time.time() < end:
        r = lread(SRV, f"record:{USER}", COMPARE, "L_poll")
        tries += 1
        if r.get("ok") is True:
            first = r
            break
        time.sleep(POLL_S)
    P["tries"] = tries
    P["first"] = first
    P["first_snap"] = snap("L_first_t")
    P["stats"] = keep(step("L_stats", SRV, "stats.all", USER))
    P["counters"] = lread(SRV, "_G", ["NutritionRevamp.server.writer.stats.seeded",
                                      "NutritionRevamp.server.writer.stats.writes",
                                      "NutritionRevamp.server.store.stats.loads",
                                      "NutritionRevamp.server.store.stats.created",
                                      "NutritionRevamp.server.store.file.stats.reads",
                                      "NutritionRevamp.server.store.file.stats.readFailures"], "L_counters")


def phase_G():
    P = out["phases"]["G"] = {}
    P["start"] = snap("G_start")
    a0 = num(P["start"].get("worldAge"))
    P["end"] = wait_age(a0 + GO_MIN / 60.0, "G_wait", GO_MIN * 0.625 * 1.5 + WAIT_SLACK_S)
    P["end_rec"] = lread(SRV, f"record:{USER}", COMPARE, "G_end_rec")


def read_pages(tag, start_from=None):
    pages = []
    frm = start_from
    for _ in range(12):
        after = time.time() - 1.0
        args = f"{USER} read" + ("" if frm is None else f" {frm}")
        r = keep(step(f"{tag}_read", SRV, "minute.ring", args, timeout=60))
        pg = {"reply": r}
        name = r.get("result")
        if isinstance(name, str) and name:
            doc = wait_doc(name, after)
            pg["doc_rows"] = len((doc or {}).get("rows_list") or [])
            src = os.path.join(server.bus.results_dir, name + ".json")
            if doc is not None and os.path.isfile(src):
                shutil.copyfile(src, os.path.join(run_dir, name + ".json"))
                copied.append(name + ".json")
                pg["file"] = name + ".json"
        pages.append(pg)
        if not r.get("ok") or not r.get("more") or r.get("next") is None:
            break
        frm = r.get("next")
    return pages


def phase_R():
    P = out["phases"]["R"] = {}
    P["pages"] = read_pages("R")
    last = P["pages"][-1]["reply"] if P["pages"] else {}
    P["next"] = last.get("next")


def phase_D():
    P = out["phases"]["D"] = {}
    P["rcon_one"] = rcon("settimespeed 1", "D_rcon_one")
    P["q0"] = snap("D_q0")
    q0 = num(P["q0"].get("wall"))
    P["pre"] = lread(SRV, "_G", FLUSH_PATHS, "D_pre")
    c = clients.get(USER) if isinstance(clients, dict) else None
    tq = wall()
    P["quit_rc"] = c.quit() if c is not None else None
    P["quit_walls"] = [tq, wall()]
    tl.mark("client_quit", user=USER, rc=P["quit_rc"])
    end = time.time() + FLUSH_CAP_S
    P["flushed"] = False
    polls = []
    while time.time() < end:
        a = lread(SRV, "_G", FLUSH_PATHS, "D_poll")
        vals, miss = a.get("values") or {}, a.get("missing") or {}
        tabs, typs = a.get("tables") or {}, a.get("types") or {}
        on = FLUSH_PATHS[0]
        present = on in vals or on in tabs or on in typs
        lw = num(vals.get(FLUSH_PATHS[1]))
        polls.append({"wall": a.get("wall"), "online_present": present, "online_missing": miss.get(on),
                      "lastWrite": lw, "writes": vals.get(FLUSH_PATHS[2])})
        if not present and lw is not None and q0 is not None and lw >= q0:
            P["flushed"] = True
            P["flushed_wall"] = a.get("wall")
            break
        time.sleep(POLL_S)
    P["polls"] = polls[:5] + polls[-5:] if len(polls) > 10 else polls
    P["poll_count"] = len(polls)
    P["last"] = gread(f"{NR}.server.store.file.last.{USER}", "D_last")
    P["end_snap"] = snap("D_end_t")
    P["tail"] = read_pages("D_tail", (out["phases"].get("R") or {}).get("next"))
    P["stop"] = keep(step("D_ring_stop", SRV, "minute.ring", f"{USER} stop"))


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()


def body_after_client():
    order = (("L", phase_L), ("G", phase_G), ("R", phase_R), ("D", phase_D), ("Z", phase_Z))
    for name, fn in order:
        if parked() and name not in ("Z", "D"):
            out["abort"] = f"admin parked in the debugger before phase {name}"
            run_phase("D", phase_D)
            run_phase("Z", phase_Z)
            return
        run_phase(name, fn)


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


def read_slots_after():
    S = out["slots"] = {}
    files, best = parse_slots(os.path.join(run_dir, "server"))
    S["files"] = []
    for r in files:
        dest = "slot-" + os.path.basename(r["path"])
        shutil.copyfile(r["path"], os.path.join(run_dir, dest))
        copied.append(dest)
        S["files"].append({k: v for k, v in r.items() if not k.startswith("_")} |
                          {"rel": os.path.relpath(r["path"], run_dir).replace(os.sep, "/"), "copy": dest})
    S["newest"] = ("slot-" + os.path.basename(best["path"])) if best else None
    S["newest_satiety_t"] = best.get("satiety_t") if best else None


# ---------------------------------------------------------------- grading
def ring_rows():
    files = [p.get("file") for p in (g(out, "phases", "R", "pages") or []) + (g(out, "phases", "D", "tail") or [])]
    files = [f for f in files if f]
    return read_ring_files(run_dir, files), files


def run_replay(rows, files):
    RP = out["replay"] = {}
    with open(os.path.join(run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(run_dir, "start-stats.json"), encoding="utf-8") as fh:
        start_stats = json.load(fh)
    player = S1.get("player")
    events = []
    with open(os.path.join(run_dir, "events.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(events, fh)
    copied.append("events.json")
    RP["inputs"] = {"ring": files, "events": events, "player": player, "start_stats": start_stats,
                    "start": "start.json (session 1's newest slot line)",
                    "cli": "python tools/replay_live.py live --ring " + " ".join(files) +
                           " --events events.json --start start.json --start-stats start-stats.json" +
                           (" --player player.json" if player is not None else "") + " --out replay.json"}
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import replay_live as RL                    # noqa: E402 - the replay tool, loaded after the session
    rr, rpaths = RL.load_ring([os.path.join(run_dir, f) for f in files])
    t_r = time.time()
    rows_out, be = RL.replay_live(rr, events, start, paths=rpaths, user=USER, player=player,
                                  start_stats=start_stats)
    d = RL.diff(rows_out, rr)
    dx = RL.diff(rows_out, rr, TOL_EXTRA)
    RP["seconds"] = round(time.time() - t_r, 2)
    doc = {"mode": "live", "offset": be.R.offset, "rows": rows_out, "diff": d, "eats": be.eats, "diff_extra": dx}
    with open(os.path.join(run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n")
    copied.append("replay.json")
    RP["offset"] = be.R.offset
    RP["rows"] = len(rows_out)
    RP["diff"] = {k: d.get(k) for k in ("fields", "classes", "ok")} | {"findings": d.get("findings", [])[:40],
                                                                       "findings_n": len(d.get("findings", []))}
    RP["diff_extra"] = {k: dx.get(k) for k in ("fields", "classes", "ok")} | \
                       {"findings": dx.get("findings", [])[:40], "findings_n": len(dx.get("findings", []))}
    by_s = {r["s"]: r for r in rows_out}
    on = [r for r in rr if r.get("on") is not False and not r.get("norec")]
    RP["first_online_rows"] = [{"s": r["s"], "age": r["age"], "HUNGER_live": r.get("HUNGER"),
                                "HUNGER_replay": (by_s.get(r["s"]) or {}).get("HUNGER"),
                                "P_live": r.get("satiety.P"), "P_replay": (by_s.get(r["s"]) or {}).get("satiety.P"),
                                "marks": {k: (by_s.get(r["s"]) or {}).get(k) for k in
                                          ("gap", "suspect", "offline", "between", "gapM", "clampM")}}
                               for r in on[:4]]
    grade("REPLAY", PRED["REPLAY"], {"ok": d.get("ok"), "fields": d.get("fields"), "classes": d.get("classes"),
                                     "findings_n": len(d.get("findings", []))},
          "as_predicted" if d.get("ok") else "falsified", "a finding")


def grade_all():
    ph = out["phases"]
    R = out["readings"]
    rows, files = ring_rows()
    R["ring_rows"] = len(rows)
    R["ring_files"] = files
    PRE = ph.get("PRE") or {}
    A = ph.get("A") or {}
    s1_ages = [x for x in (num(g(PRE, "s1_last_snap", "worldAge")), num(g(PRE, "s1_last_row", "age"))) if x is not None]
    s1_last = max(s1_ages) if s1_ages else None
    boot = num(g(A, "boot_snap", "worldAge"))
    if s1_last is not None and boot is not None:
        dm = (boot - s1_last) * 60
        grade("CLOCK", PRED["CLOCK"], {"s1_last_age": s1_last, "boot_age": boot, "game_minutes": dm,
                                       "s1_last_snapshot_age": g(PRE, "s1_last_snap", "worldAge"),
                                       "s1_last_online_row_age": g(PRE, "s1_last_online_row", "age"),
                                       "s1_last_row_age": g(PRE, "s1_last_row", "age")},
              "as_predicted" if 0 <= dm <= CLOCK_MAX_M else "falsified", "earlier, or later by more")
    else:
        grade("CLOCK", PRED["CLOCK"], None, "unmeasured", "no snapshot on either side")

    L = ph.get("L") or {}
    first = L.get("first") or {}
    sv = PRE.get("slot_values") or {}
    if first.get("ok") is True and sv:
        vals = first.get("values") or {}
        t_slot, t_read = num(sv.get("satiety.t")), num(vals.get("satiety.t"))
        hours = set()
        if t_slot is not None and t_read is not None:
            for h in range(int(math.floor(t_slot)), int(math.floor(t_read)) + 1):
                hours.add(h % 25 + 1)
        checks = {}
        for k in ("firstSeen", "resets", "body.sex", "monotony.t.[TKX.Mixed650].n", "monotony.t.[TKX.Mixed650].last"):
            checks[k] = {"slot": sv.get(k), "read": vals.get(k), "ok": sv.get(k) == vals.get(k)}
        trail_bad = {}
        for i in range(1, 26):
            k = f"body.trail.kcal.{i}"
            a_, b_ = num(sv.get(k)), num(vals.get(k))
            if a_ != b_ and i not in hours:
                trail_bad[k] = {"slot": a_, "read": b_}
        checks["trail_kcal_outside_hours"] = {"allowed_slots": sorted(hours), "differ": trail_bad, "ok": not trail_bad}
        checks["satiety.t"] = {"slot": t_slot, "read": t_read,
                               "ok": t_slot is not None and t_read is not None and t_read >= t_slot - 1e-9}
        p_s, p_r = num(sv.get("satiety.P")), num(vals.get("satiety.P"))
        checks["satiety.P"] = {"slot": p_s, "read": p_r, "ok": p_s is not None and p_r is not None and
                               p_r <= p_s + 1e-9 and (p_r > 0 or p_s <= 0)}
        n_s, n_r = num(sv.get("satiety.nicH")), num(vals.get("satiety.nicH"))
        checks["satiety.nicH"] = {"slot": n_s, "read": n_r,
                                  "ok": (n_s is None and n_r is None) or (n_s is not None and n_r is not None
                                                                          and n_r >= n_s - 1e-9)}
        ok = all(c.get("ok") for c in checks.values())
        grade("LOAD", PRED["LOAD"], {"checks": checks, "read_wall": first.get("wall"), "tries": L.get("tries"),
                                     "read_age": g(L, "first_snap", "worldAge"),
                                     "gap_game_minutes": ((t_read - t_slot) * 60) if None not in (t_slot, t_read)
                                     else None},
              "as_predicted" if ok else "falsified", "any one check not so")
    else:
        grade("LOAD", PRED["LOAD"], {"first": first, "slot_values": bool(sv)}, "unmeasured",
              "the record never read, or no slot line")

    seeded = [(r["s"], r.get(SEEDED)) for r in rows if num(r.get(SEEDED)) is not None]
    if seeded:
        nz = [x for x in seeded if x[1] != 0]
        grade("SEED", PRED["SEED"], {"rows": len(seeded), "nonzero": nz[:10]},
              "as_predicted" if not nz else "falsified", "a non-zero row")
    else:
        grade("SEED", PRED["SEED"], None, "unmeasured", "no ring row read the counter")

    on = [r for r in rows if r.get("on") is not False and not r.get("norec")]
    s1_on = PRE.get("s1_last_online_row") or {}
    R["hunger_across"] = {"s1_last_online": {k: s1_on.get(k) for k in ("s", "age", "HUNGER", "satiety.P", "satiety.t")},
                          "s2_first_online": [{k: r.get(k) for k in ("s", "age", "HUNGER", "satiety.P", "satiety.t",
                                                                    "drained", SEEDED)} for r in on[:4]]}
    R["s1_drift"] = {"s1_newest_slot_t": PRE.get("slot_satiety_t"), "s1_last_online_row_age": s1_on.get("age"),
                     "lost_game_minutes": ((s1_on["age"] - PRE["slot_satiety_t"]) * 60)
                     if (num(s1_on.get("age")) is not None and num(PRE.get("slot_satiety_t")) is not None) else None}
    sl = out.get("slots") or {}
    if on and num(sl.get("newest_satiety_t")) is not None:
        R["s2_drift"] = {"newest_slot_t": sl["newest_satiety_t"], "last_online_row_age": on[-1]["age"],
                         "lost_game_minutes": (on[-1]["age"] - sl["newest_satiety_t"]) * 60}

    D = ph.get("D") or {}
    if D:
        obs = {"flushed": D.get("flushed"), "q0_wall": g(D, "q0", "wall"), "flushed_wall": D.get("flushed_wall"),
               "quit_rc": D.get("quit_rc"), "polls": D.get("poll_count")}
        grade("F", PRED["F"], obs, "as_predicted" if D.get("flushed") else "falsified", "the cap passes")
    else:
        grade("F", PRED["F"], None, "unmeasured", "phase D not run")

    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [], "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")
    return rows, files


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if not isinstance(out["host"]["free_gb_before_boot"], float) or out["host"]["free_gb_before_boot"] < MEM_MIN_GB:
    out["error"] = f"free host memory {out['host']['free_gb_before_boot']} GB under {MEM_MIN_GB}: not booted (CLAUDE.md s5)"
    persist()
    print(out["error"])
    sys.exit(1)
lint_errors = lint_paths(prof.sources)
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    print(json.dumps(lint_errors, indent=1))
    sys.exit(1)
run_phase("PRE", phase_PRE)
if "PRE" in out["phase_errors"]:
    out["error"] = "phase PRE failed: no boot"
    persist()
    print(json.dumps(out["phase_errors"], indent=1))
    sys.exit(1)
try:
    shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
    copied.append(MANIFEST_NAME)
except OSError as e:
    out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini, reuse=True)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    run_phase("A", phase_A)
    clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             **{u: sorted(set(c.mods_not_found)) for u, c in clients.items()}}
    persist()
    try:
        body_after_client()
    except Exception as e:                     # noqa: BLE001
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
            out["server_stop_wall"] = wall()
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, every)
        adm = clients.get(USER) if isinstance(clients, dict) else None
        out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
        out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                              for i, c in enumerate(every)]
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        out["host"]["free_gb_after"] = free_gb()
        try:
            read_logs(every)
        except Exception as e:                 # noqa: BLE001
            out["logs_error"] = f"{type(e).__name__}: {e}"
        try:
            read_slots_after()
        except Exception as e:                 # noqa: BLE001
            out["slots_error"] = f"{type(e).__name__}: {e}"
        rows_, files_ = [], []
        try:
            rows_, files_ = grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        persist()
        try:
            if rows_:
                run_replay(rows_, files_)
        except Exception as e:                 # noqa: BLE001
            out.setdefault("replay", {})["error"] = f"{type(e).__name__}: {e}"
            out["replay"]["traceback"] = traceback.format_exc()[-3000:]
            grade("REPLAY", PRED["REPLAY"], None, "unmeasured", "the replay raised")
        out["copied"] = sorted(set(copied))
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            for f in sorted(set(copied)):
                if os.path.isfile(os.path.join(run_dir, f)):
                    shutil.copyfile(os.path.join(run_dir, f), os.path.join(dest_dir, f))
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "hunger_across": g(out, "readings", "hunger_across"),
                  "s1_drift": g(out, "readings", "s1_drift"), "s2_drift": g(out, "readings", "s2_drift"),
                  "replay_ok": g(out, "replay", "diff", "ok"), "replay_error": g(out, "replay", "error"),
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir},
                 indent=1, default=str)[:6000])
