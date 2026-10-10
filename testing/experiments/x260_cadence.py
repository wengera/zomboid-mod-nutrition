"""x260-cadence -- Plan 11f Task 3 session 1 (live): the cadence gate S0 at speed 1 and at `settimespeed 5`, the
harness smoke test of H1 (`lua.read`) and H2 (`minute.ring`) -- this run is their acceptance run --, one
TKX_StudyFoods Mixed650 eaten by `eat.action` and its booking read in the ring, the replay of this session's ring
and event log through tools/replay_live.py, and the departure-flush sequence. One boot of profile x26-cadence
(fixture default, admin -debug, Nutrition false, DayLength 1) on the STAGED copy of the tree at cbdf8df
(release/x260-cadence/NutritionRevamp/Contents/mods/NutritionRevamp, staged with
`python tools/release_pack.py stage mod/NutritionRevamp --out release/x260-cadence`; release/ is gitignored; mod/ is
never booted) plus TKX_StudyFoods by its path. Build 42.21.0 (4a0e9546ec). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). Session 2 (x260b_chain.py) boots a copy
of this run's server folder again.

THE INSTRUMENTS (harness, commits 10f25f3 and 6c98c5c; Plan 11f Task 1):
  lua.read <root> <path...>  (H1, both sides): record:admin is NutritionRevamp.server.store.records.admin, read
      directly; _G reads the globals.
  minute.ring admin start <paths> | read [<from>] | stop  (H2, server): one row per EveryOneMinute event, sampled
      INSIDE the event, before the mod's queue drains that minute (row k reads what drain k-1 left); the row's
      s, ev, drained, age, dtM, hour, min, on, the six stats, norec and the paths.
  bench.global TK.MR.benchRow <n>: one ring row sampled per call into a scratch table (the rings untouched).

PHASES (order S, H, C1, C5, W, E, R, D; then, after the clean server quit, the slot files and the replay):
  S   the ready marks, the verify rows, players, time.snapshot, the mode, nutrition.get admin, stats.all admin,
      inventory weights (a zero-count read is not possible: read off the eat's inventory.add reply in E).
  H   H1 smoke: lua.read record:admin on the ring's record paths (every one checked before the ring is armed) and
      the full trail (body.trail.at, kcal.1..25, ee.1..25) plus satiety and identity fields; lua.read _G on the
      server and on the client. H2: minute.ring admin start <RING paths> (the record paths below, the trail kcal
      slots of the six game hours from the arming hour, and eight globals); then bench.global TK.MR.benchRow 1000.
  C1  speed 1: lua.read _G counters (writer.stats.writes, players.minutes/served/drained/ticksLast) and
      time.snapshot; C1_MIN game minutes waited on the world age; the counters again.
  C5  RCON `settimespeed 5` (the broadcast admin path harness.md names), time.snapshot; C5_MIN game minutes waited
      on the world age; the counters; RCON `settimespeed 1`, time.snapshot.
  W   the start record for the replay: at speed 1, poll store.file.lastWrite.admin until it advances (cap
      SAVE_CAP_S), then at once lua.global NutritionRevamp.server.store.file.last.admin (the inputs-only JSON line
      the save wrote), stats.all admin (the stand-in's starting stats) and time.snapshot (the read age). No eat
      precedes the read, so the read age is the record's own age.
  E   `time.multiplier 0.1674` (server; research s3.6, #3394: 37 ticks a game minute), time.snapshot;
      RCON additem "admin" "TKX.Mixed650" 1 and witness.fields on the client until it resolves (cap
      SPAWN_CAP_S; never seen: no eat); foodtimer.set admin 0; lua.read _G intake.stats.eats/landed (before);
      eat.action TKX.Mixed650 1 on the client; poll landed until it rises (cap EAT_CAP_S), stamping the world age;
      lua.read record:admin satiety/stomach/inDay/monotony after; SLOW_MIN game minutes at the slow clock; RCON
      `settimespeed 1`, time.snapshot; TAIL_MIN game minutes at speed 1.
  R   minute.ring admin read, page after page (720 rows each) until `more` is false; each page's result document
      waited for and copied byte-identical into the run folder.
  D   the departure flush: speed is 1 (RCON settimespeed 1 again, harmless); time.snapshot (q0: the server wall ms
      before the quit); the client `quit`; poll lua.read _G NutritionRevamp.server.players.online.admin and
      NutritionRevamp.server.store.file.lastWrite.admin until online.admin is absent and lastWrite >= q0 (cap
      FLUSH_CAP_S); lua.global store.file.last.admin (the flushed line); time.snapshot; the ring's tail page and
      minute.ring admin stop. Then the clean server quit (teardown) saves the world.
  After: the slot files p_*_{a,b}.json under the server's Lua/NutritionRevamp/<name>/ read and copied byte-identical
      (the newest complete one's satiety.t is the slot's world age, against the ring's last online row); then the
      replay: tools/replay_live.replay_live over this run's ring pages, from the W start record (start-stats from
      W's stats.all, the player from S's reads), with the eat keyed by the first ring row whose intake.stats
      .landed shows it; the diff under the plan's tolerances (HUNGER 0.002, es 0.005, L 0.5 %) and, as readings, P, S and
      stomachFill. The replay's inputs are written as files so the CLI reproduces it.

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / trivial / unmeasured):
  H1  lua.read record:admin answers ok with every record path of the ring in `values` or `tables` (monotony's
      Mixed650 entry may be missing before the eat); lua.read _G answers on server and client. Falsifier: ok false,
      or a ring record path (other than the Mixed650 entry) missing.
  H2  minute.ring start answers ok with armed; at R every page reads back; errors 0; rows recorded >= the game
      minutes elapsed - 2. Falsifier: a start refused, a page missing, an error, too few rows.
  S0  at speed 5: writer writes per player per game minute >= 0.99 (ring rows' writer.stats.writes delta over the
      rows' game minutes) and dtM <= 1.05 on >= 99 % of the window's rows. Falsifier: either short. (Speed 1 read
      the same way, as a reading.)
  EAT intake.stats.landed rises by 1 within EAT_CAP_S; in the ring, at the landing row: landed +1, satiety.P up, the
      stomach buffer's calories up by >= 600, monotony's Mixed650 n present. Falsifier: any missing.
  F   the departure flush: online.admin absent and lastWrite >= q0 within FLUSH_CAP_S. Falsifier: the cap passes.
  Z   no mod error line on the server; admin not parked.

READINGS (not graded): the benchRow us per call (one watched user: per row); ticksLast at each speed; the dtM and
drained-delta histograms; the slot's world age against the ring's last online row (the record drift a stop could
lose, in game minutes); the replay's diff (live vs replay-of-live; any gap is a finding, and the tool is never
tuned to this run).

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

PROFILE = "x26-cadence"
PREFIX = "x260"
SESSION = ("Plan 11f Task 3 session 1: the cadence gate S0 at speed 1 and settimespeed 5, the H1/H2 smoke, one "
           "TKX_StudyFoods Mixed650 eaten by eat.action and replayed, and the departure flush, on the staged copy at "
           "cbdf8df; one boot of " + PROFILE)
ARTIFACT = "cadence.json"
MANIFEST_NAME = "MANIFEST.json"
USER = "admin"
SRV = "server"
CLI = "client"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/x260-cadence/NutritionRevamp"
STAGED_AT = "cbdf8df"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_CORE = LUA_DIR + "/shared/PZTestKit_Core.lua"
STUDY_FOODS = "testing/experiments/TKX_StudyFoods/common/media/scripts/tkx_study_foods.txt"
GAME_JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
APP_MANIFEST = r"D:\SteamLibrary\steamapps\appmanifest_108600.acf"
NR = "NutritionRevamp"
FOOD = "TKX.Mixed650"
FOOD_KCAL = 650
MEM_MIN_GB = 12.0
BENCH_N = 1000
C1_MIN = 20
C5_MIN = 120
SPEED = 5
SLOW_MULT = 0.1674
SLOW_MIN = 10
TAIL_MIN = 60
SAVE_CAP_S = 80.0
SPAWN_CAP_S = 15.0
EAT_CAP_S = 60.0
FLUSH_CAP_S = 90.0
WAIT_SLACK_S = 60.0
RESULT_WAIT_S = 30.0
POLL_S = 0.3
LOG_LIMIT = 400
TRAIL_HOURS = 6
WPM_MIN = 0.99
DTM_MAX = 1.05
DTM_SHARE = 0.99
TOL_EXTRA = {"satiety.P": ("rel", 0.005), "satiety.S": ("abs", 1e-6), "stomachFill": ("abs", 0.002)}
RING_RECORD = ("satiety.P", "satiety.S", "satiety.L", "satiety.t", "satiety.nicH", "body.energyState", "body.met",
               "acute.debtH", "stomachFill", "stomach.liquid", "stomach.buffer.calories", "stomach.buffer.water",
               "body.inDay", "body.trail.at", "monotony", "monotony.t.[TKX.Mixed650].n", "kineticsAge", "lastSeen")
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.seeded",
                "_G.NutritionRevamp.server.players.served", "_G.NutritionRevamp.server.players.ticksLast",
                "_G.NutritionRevamp.server.intake.stats.eats", "_G.NutritionRevamp.server.intake.stats.landed",
                "_G.NutritionRevamp.server.store.file.stats.writes",
                "_G.NutritionRevamp.server.store.file.lastWrite.admin")
OPTIONAL_BEFORE_EAT = ("monotony.t.[TKX.Mixed650].n", "monotony")
H1_EXTRA = ("firstSeen", "resets", "body.sex", "body.fm", "body.lm", "monotony.t.[TKX.Mixed650].last")
COUNTERS = ("NutritionRevamp.server.writer.stats.writes", "NutritionRevamp.server.writer.stats.seeded",
            "NutritionRevamp.server.players.minutes", "NutritionRevamp.server.players.served",
            "NutritionRevamp.server.players.drained", "NutritionRevamp.server.players.ticksLast",
            "NutritionRevamp.server.minute.stats.runs", "NutritionRevamp.server.minute.stats.failures")
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin",
               "NutritionRevamp.server.store.file.stats.writes")
EAT_PATHS = ("NutritionRevamp.server.intake.stats.eats", "NutritionRevamp.server.intake.stats.landed",
             "NutritionRevamp.server.intake.stats.failures")
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|store: |writer: ")
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
copied = []                                   # run-folder files copied to the artifact folder beside ARTIFACT


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
    "H1": {"lua.read record:admin ok": True, "ring record paths resolved": "all but the Mixed650 monotony entry",
           "lua.read _G answers": [SRV, CLI]},
    "H2": {"start ok and armed": True, "pages read back": "all", "errors": 0, "rows": ">= game minutes - 2"},
    "S0": {"writes per player per game minute at speed 5": f">= {WPM_MIN}",
           "share of speed-5 rows with dtM <= 1.05": f">= {DTM_SHARE}"},
    "EAT": {"landed rises": 1, "satiety.P": "up", "stomach.buffer.calories rise": ">= 600",
            "monotony Mixed650 n": "present"},
    "F": {"online.admin": "absent", "lastWrite.admin >= q0": True, "within s": FLUSH_CAP_S},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "users": list(prof.users), "profile": prof.report(),
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
    "study_foods_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_StudyFoods"),
    "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
    "acceptance_run": "this run: the first live use of H1 lua.read and H2 minute.ring (10f25f3, 6c98c5c)",
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "host": {"free_gb_before_boot": free_gb(), "mem_min_gb": MEM_MIN_GB, "stray_clients": stray_clients()},
    "meta": {"staged_mod": STAGE_ROOT + "/Contents/mods/NutritionRevamp", "staged_at": STAGED_AT,
             "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/x260-cadence",
             "build_expected": "42.21.0 (4a0e9546ec), Steam buildid 25485521",
             "phase_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute: "
                           "row k reads the state drain k-1 left (harness H2's comment block)",
             "s0_note": "writes per game minute are the ring rows' writer.stats.writes delta over the rows' world-age "
                        "span in the window; one player online, so per player is per server"},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [],
    "world_changes": {"restored": "fixture default restored into the run dir (server and the admin client cache)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "readings": {},
}
try:
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    out["meta"]["harness_core_sha256"] = sha256_file(os.path.join(REPO, HARNESS_CORE))
    out["meta"]["study_foods_sha256"] = sha256_file(os.path.join(REPO, STUDY_FOODS))
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
    a = keep(step(tag, SRV, "lua.global", name))
    return a


def snap(tag):
    a = keep(step(tag, SRV, "time.snapshot"))
    return {k: a.get(k) for k in ("worldAge", "hour", "minutes", "mult", "wall", "wall_after")} | {"tag": tag}


def counters(tag):
    a = lread(SRV, "_G", COUNTERS, tag)
    vals = a.get("values") or {}
    return {"values": {k: vals.get(k) for k in COUNTERS},
            "missing": a.get("missing"), "wall": a.get("wall"), "snap": snap(tag + "_t")}


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
    """Poll time.snapshot until the world age reaches `target` (hours); returns the last snapshot."""
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


def stats_of(a):
    """The six ring stats out of a stats.all reply (keyed by the registry's id or its enum name)."""
    st = a.get("stats") or {}
    o = {}
    for k, cam in STAT_NAMES.items():
        v = st.get(k, st.get(cam))
        if num(v) is not None:
            o[k] = v
    return o


def ring_paths(h0):
    slots = [f"body.trail.kcal.{(h0 + i) % 25 + 1}" for i in range(TRAIL_HOURS)]
    return list(RING_RECORD) + slots + list(RING_GLOBALS)


# ---------------------------------------------------------------- phases
def phase_S():
    P = out["phases"]["S"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S_players", SRV, "players"))
    P["time"] = snap("S_time")
    P["mode"] = gread(f"{NR}.server.writer.mode", "S_mode")
    P["nutrition"] = keep(step("S_nutrition", SRV, "nutrition.get", USER))
    P["stats"] = keep(step("S_stats", SRV, "stats.all", USER))
    P["seen"] = dict(getattr(node(CLI), "seen", {}))


def phase_H():
    P = out["phases"]["H"] = {}
    s = snap("H_time")
    h0 = int(math.floor(num(s.get("worldAge")) or 0.0))
    paths = ring_paths(h0)
    P["arm_hour"] = h0
    P["ring_paths"] = paths
    rec_paths = [p for p in paths if not p.startswith("_G.")]
    P["h1_record"] = lread(SRV, f"record:{USER}", rec_paths + list(H1_EXTRA), "H_h1_record")
    trail = ["body.trail.at"] + [f"body.trail.kcal.{i}" for i in range(1, 26)] + \
            [f"body.trail.ee.{i}" for i in range(1, 26)]
    P["h1_trail"] = lread(SRV, f"record:{USER}", trail, "H_h1_trail")
    P["h1_globals_server"] = lread(SRV, "_G", [p[3:] for p in RING_GLOBALS] + ["NutritionRevamp.version"],
                                   "H_h1_globals_srv")
    P["h1_globals_client"] = lread(CLI, "_G", ["NutritionRevamp.version", "TK.version"], "H_h1_globals_cli")
    P["h1_bad"] = lread(SRV, f"record:{USER}", ["satiety.[unclosed"], "H_h1_bad")
    P["ring_start"] = keep(step("H_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))
    P["ring_start_snap"] = snap("H_ring_start_t")
    P["bench"] = keep(step("H_bench", SRV, "bench.global", f"TK.MR.benchRow {BENCH_N}", timeout=60))


def phase_C1():
    P = out["phases"]["C1"] = {}
    P["before"] = counters("C1_before")
    a0 = num(P["before"]["snap"].get("worldAge"))
    P["end"] = wait_age(a0 + C1_MIN / 60.0, "C1_wait", C1_MIN * 0.625 * 1.5 + WAIT_SLACK_S)
    P["after"] = counters("C1_after")


def phase_C5():
    P = out["phases"]["C5"] = {}
    P["before"] = counters("C5_before")
    P["rcon_fast"] = rcon(f"settimespeed {SPEED}", "C5_rcon_fast")
    P["fast_snap"] = snap("C5_fast_t")
    a0 = num(P["fast_snap"].get("worldAge"))
    P["end"] = wait_age(a0 + C5_MIN / 60.0, "C5_wait", C5_MIN * 0.625 / SPEED * 3 + WAIT_SLACK_S)
    P["after"] = counters("C5_after")
    P["rcon_slow"] = rcon("settimespeed 1", "C5_rcon_slow")
    P["slow_snap"] = snap("C5_slow_t")


def phase_W():
    P = out["phases"]["W"] = {}
    first = lread(SRV, "_G", FLUSH_PATHS, "W_lw0")
    lw0 = num((first.get("values") or {}).get(FLUSH_PATHS[1]))
    P["lastWrite_before"] = lw0
    end = time.time() + SAVE_CAP_S
    polls = 0
    P["saved"] = False
    while time.time() < end:
        a = lread(SRV, "_G", FLUSH_PATHS[1:], "W_poll")
        polls += 1
        lw = num((a.get("values") or {}).get(FLUSH_PATHS[1]))
        if lw is not None and (lw0 is None or lw > lw0):
            P["saved"] = True
            P["lastWrite"] = lw
            P["saw_wall"] = a.get("wall")
            break
        time.sleep(POLL_S)
    P["polls"] = polls
    P["last"] = gread(f"{NR}.server.store.file.last.{USER}", "W_last")
    P["stats"] = keep(step("W_stats", SRV, "stats.all", USER))
    P["read"] = snap("W_read_t")
    txt = P["last"].get("value")
    if isinstance(txt, str):
        try:
            doc = json.loads(txt)
            rec = doc.get("rec") if isinstance(doc, dict) else None
            P["start_age"] = ((rec or {}).get("satiety") or {}).get("t")
            P["start_gen"] = doc.get("gen") if isinstance(doc, dict) else None
            with open(os.path.join(run_dir, "start.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(txt)
            copied.append("start.json")
        except ValueError as e:
            note(f"W: the saved line does not decode: {e}")
    st = stats_of(P["stats"])
    with open(os.path.join(run_dir, "start-stats.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)
    copied.append("start-stats.json")


def phase_E():
    P = out["phases"]["E"] = {}
    P["slow"] = keep(step("E_slow", SRV, "time.multiplier", str(SLOW_MULT)))
    P["slow_snap"] = snap("E_slow_t")
    P["add"] = rcon(f'additem "{USER}" "{FOOD}" 1', "E_additem")
    P["seen"] = None
    end_seen = time.time() + SPAWN_CAP_S
    while time.time() < end_seen:
        w = keep(step("E_seen", CLI, "witness.fields", f"item {USER}/{FOOD} getID"))
        if isinstance(w.get("resolved"), str) and w.get("resolved"):
            P["seen"] = w
            break
        time.sleep(1.0)
    if P["seen"] is None:
        note("E: the client never saw the RCON-added item; the eat is not queued (a client-spawned item is invisible "
             "to the server, #2917)")
        return
    P["foodtimer"] = keep(step("E_foodtimer", SRV, "foodtimer.set", f"{USER} 0"))
    P["before"] = lread(SRV, "_G", EAT_PATHS, "E_before")
    P["before_rec"] = lread(SRV, f"record:{USER}", list(RING_RECORD) + list(H1_EXTRA), "E_before_rec")
    e0 = num((P["before"].get("values") or {}).get(EAT_PATHS[1]))
    P["landed_before"] = e0
    P["eats_before"] = num((P["before"].get("values") or {}).get(EAT_PATHS[0]))
    P["eat"] = keep(step("E_eat", CLI, "eat.action", f"{FOOD} 1"))
    out["world_changes"]["left_in_place"].append(f"admin ate one {FOOD} (spawned by inventory.add)")
    end = time.time() + EAT_CAP_S
    P["landed"] = False
    polls = 0
    while time.time() < end:
        a = lread(SRV, "_G", EAT_PATHS, "E_poll")
        polls += 1
        e = num((a.get("values") or {}).get(EAT_PATHS[1]))
        if e is not None and e0 is not None and e > e0:
            P["landed"] = True
            P["landed_read"] = a
            P["landed_snap"] = snap("E_landed_t")
            break
        time.sleep(POLL_S)
    P["polls"] = polls
    P["after_rec"] = lread(SRV, f"record:{USER}", list(RING_RECORD) + list(H1_EXTRA), "E_after_rec")
    P["after_nut"] = keep(step("E_after_nut", SRV, "nutrition.get", USER))
    a0 = num((P.get("landed_snap") or snap("E_nolanding_t")).get("worldAge"))
    P["slow_end"] = wait_age(a0 + SLOW_MIN / 60.0, "E_slow_wait", SLOW_MIN * 4.0 * 1.5 + WAIT_SLACK_S)
    P["rcon_one"] = rcon("settimespeed 1", "E_rcon_one")
    P["one_snap"] = snap("E_one_t")
    a1 = num(P["one_snap"].get("worldAge"))
    P["tail_end"] = wait_age(a1 + TAIL_MIN / 60.0, "E_tail_wait", TAIL_MIN * 0.625 * 1.5 + WAIT_SLACK_S)
    P["end_rec"] = lread(SRV, f"record:{USER}", list(RING_RECORD) + list(H1_EXTRA), "E_end_rec")


def read_pages(tag, start_from=None):
    """minute.ring admin read from `start_from` (default the oldest) page after page; each page's document copied."""
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
    P["store_stats"] = lread(SRV, "_G", ["NutritionRevamp.server.store.file.stats.writes",
                                         "NutritionRevamp.server.store.file.stats.writeFailures",
                                         "NutritionRevamp.server.store.file.stats.repaired",
                                         "NutritionRevamp.server.store.file.stats.deferred",
                                         "NutritionRevamp.server.store.stats.loads",
                                         "NutritionRevamp.server.store.stats.created"], "D_store_stats")


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()


def body():
    order = (("S", phase_S), ("H", phase_H), ("C1", phase_C1), ("C5", phase_C5), ("W", phase_W), ("E", phase_E),
             ("R", phase_R), ("D", phase_D), ("Z", phase_Z))
    for name, fn in order:
        if parked() and name not in ("Z", "D"):
            out["abort"] = f"admin parked in the debugger before phase {name}"
            run_phase("Z", phase_Z)
            run_phase("D", phase_D)
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


def read_slots():
    """The slot files after the clean quit, each copied byte-identical; the newest complete one parsed."""
    S = out["slots"] = {"files": []}
    if server is None:
        return
    root = os.path.join(run_dir, "server")
    found = sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", "p_*_*.json"), recursive=True))
    best = None
    for f in found:
        rel = os.path.relpath(f, run_dir).replace(os.sep, "/")
        row = {"path": rel, "bytes": os.path.getsize(f), "mtime": os.path.getmtime(f), "sha256": sha256_file(f)}
        dest = "slot-" + os.path.basename(f)
        shutil.copyfile(f, os.path.join(run_dir, dest))
        copied.append(dest)
        row["copy"] = dest
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
            row["lines"] = len(text.splitlines())
            doc = json.loads(text.splitlines()[-1]) if text.strip() else None
            rec = (doc or {}).get("rec") or {}
            row.update({"gen": (doc or {}).get("gen"), "done": (doc or {}).get("done"),
                        "satiety_t": (rec.get("satiety") or {}).get("t"), "lastSeen": rec.get("lastSeen"),
                        "kineticsAge": rec.get("kineticsAge"), "satiety_P": (rec.get("satiety") or {}).get("P")})
            if row["done"] and (best is None or (row["gen"] or -1) > (best["gen"] or -1)):
                best = row
        except (OSError, ValueError, IndexError) as e:
            row["parse_error"] = f"{type(e).__name__}: {e}"
        S["files"].append(row)
    S["newest"] = best["copy"] if best else None
    S["newest_row"] = best
    idx = sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", "index_*.json"), recursive=True))
    S["index_files"] = [{"path": os.path.relpath(f, run_dir).replace(os.sep, "/"), "bytes": os.path.getsize(f)}
                        for f in idx]


# ---------------------------------------------------------------- grading
def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def ring_rows():
    files = [p.get("file") for p in (g(out, "phases", "R", "pages") or []) + (g(out, "phases", "D", "tail") or [])]
    rows = {}
    for f in files:
        if not f:
            continue
        try:
            with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in doc.get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)], [f for f in files if f]


def window(rows, a0, a1):
    return [r for r in rows if num(r.get("age")) is not None and a0 < r["age"] <= a1 + 1e-9]


def hist(xs, nd=2):
    h = {}
    for x in xs:
        k = str(round(x, nd))
        h[k] = h.get(k, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: float(kv[0])))


def cadence(rows):
    W = "_G.NutritionRevamp.server.writer.stats.writes"
    on = [r for r in rows if r.get("on") is not False]
    if len(on) < 2:
        return {"rows": len(on)}
    w0, w1 = num(on[0].get(W)), num(on[-1].get(W))
    span = (on[-1]["age"] - on[0]["age"]) * 60
    dts = [r["dtM"] for r in on[1:] if num(r.get("dtM")) is not None]
    dr = [on[i + 1]["drained"] - on[i]["drained"] for i in range(len(on) - 1)
          if num(on[i].get("drained")) is not None and num(on[i + 1].get("drained")) is not None]
    ev = [on[i + 1]["ev"] - on[i]["ev"] for i in range(len(on) - 1)
          if num(on[i].get("ev")) is not None and num(on[i + 1].get("ev")) is not None]
    tk = [r.get("_G.NutritionRevamp.server.players.ticksLast") for r in on
          if num(r.get("_G.NutritionRevamp.server.players.ticksLast")) is not None]
    wpm = ((w1 - w0) / span) if (w0 is not None and w1 is not None and span > 0) else None
    return {"rows": len(on), "first_s": on[0]["s"], "last_s": on[-1]["s"], "game_minutes": span,
            "writes": (w1 - w0) if (w0 is not None and w1 is not None) else None, "writes_per_game_minute": wpm,
            "rows_per_game_minute": (len(on) - 1) / span if span > 0 else None,
            "dtM_hist": hist(dts), "dtM_max": max(dts) if dts else None,
            "dtM_le_1_05_share": (sum(1 for x in dts if x <= DTM_MAX) / len(dts)) if dts else None,
            "drained_delta_hist": hist(dr, 0), "ev_delta_hist": hist(ev, 0), "ticksLast_hist": hist(tk, 0)}


def run_replay(rows, files):
    """tools/replay_live over this run's ring, from W's start record; inputs written as files for the CLI."""
    RP = out["replay"] = {}
    W = g(out, "phases", "W") or {}
    E = g(out, "phases", "E") or {}
    S = g(out, "phases", "S") or {}
    if not os.path.isfile(os.path.join(run_dir, "start.json")):
        RP["error"] = "no start record (phase W)"
        return
    with open(os.path.join(run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(run_dir, "start-stats.json"), encoding="utf-8") as fh:
        start_stats = json.load(fh)
    eats_path = "_G.NutritionRevamp.server.intake.stats.landed"
    e0 = E.get("landed_before")
    events = []
    land = next((r for r in rows if e0 is not None and num(r.get(eats_path)) is not None and r[eats_path] > e0), None)
    if land is not None:
        events.append({"s": land["s"], "kind": "eat", "food": FOOD})
    RP["landing_row"] = land["s"] if land else None
    RP["landing_age_polled"] = g(E, "landed_snap", "worldAge")
    nut = S.get("nutrition") or {}
    sex = g(E, "before_rec", "values", "body.sex") or g(out, "phases", "H", "h1_record", "values", "body.sex")
    player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
              "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
    if num(g(E, "add", "invWeight")) is not None:
        player["inv"] = num(g(E, "add", "invWeight"))
    if num(g(E, "add", "maxWeight")) is not None:
        player["maxW"] = num(g(E, "add", "maxWeight"))
    for name, obj in (("events.json", events), ("player.json", player)):
        with open(os.path.join(run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True)
        copied.append(name)
    RP["inputs"] = {"ring": files, "events": events, "player": player, "start_stats": start_stats,
                    "start": "start.json", "start_age": W.get("start_age"), "read_age": g(W, "read", "worldAge"),
                    "cli": "python tools/replay_live.py live --ring " + " ".join(files) +
                           " --events events.json --start start.json --start-stats start-stats.json "
                           "--player player.json --out replay.json"}
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import replay_live as RL                    # noqa: E402 - the replay tool, loaded after the session
    rr, rpaths = RL.load_ring([os.path.join(run_dir, f) for f in files])
    t_r = time.time()
    rows_out, be = RL.replay_live(rr, events, start, paths=rpaths, user=USER, player=player,
                                  start_stats=start_stats)
    d = RL.diff(rows_out, rr)
    dx = RL.diff(rows_out, rr, TOL_EXTRA)
    RP["seconds"] = round(time.time() - t_r, 2)
    doc = {"mode": "live", "offset": be.R.offset, "rows": rows_out, "diff": d, "eats": be.eats,
           "diff_extra": dx, "dropped": getattr(be, "dropped", None)}
    with open(os.path.join(run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n")
    copied.append("replay.json")
    RP["offset"] = be.R.offset
    RP["rows"] = len(rows_out)
    RP["eats"] = be.eats
    RP["diff"] = {k: d.get(k) for k in ("fields", "classes", "ok")} | {"findings": d.get("findings", [])[:40],
                                                                       "findings_n": len(d.get("findings", []))}
    RP["diff_extra"] = {k: dx.get(k) for k in ("fields", "classes", "ok")} | \
                       {"findings": dx.get("findings", [])[:40], "findings_n": len(dx.get("findings", []))}


def grade_all():
    ph = out["phases"]
    R = out["readings"]
    rows, files = ring_rows()
    R["ring_rows"] = len(rows)
    R["ring_files"] = files

    H = ph.get("H") or {}
    rec = H.get("h1_record") or {}
    if rec:
        miss = rec.get("missing") or {}
        need = [p for p in H.get("ring_paths", []) if not p.startswith("_G.") and p not in OPTIONAL_BEFORE_EAT]
        bad = {p: miss.get(p) for p in need if p in miss}
        srv_ok = bool(g(H, "h1_globals_server", "ok"))
        cli_ok = bool(g(H, "h1_globals_client", "ok"))
        obs = {"ok": rec.get("ok"), "n": rec.get("n"), "missing_needed": bad, "missing_all": miss,
               "server_globals_ok": srv_ok, "client_globals_ok": cli_ok,
               "client_values": g(H, "h1_globals_client", "values"), "bad_path_reply": H.get("h1_bad")}
        ok = rec.get("ok") is True and not bad and srv_ok and cli_ok
        grade("H1", PRED["H1"], obs, "as_predicted" if ok else "falsified",
              "ok false, a ring record path missing, or a side not answering")
    else:
        grade("H1", PRED["H1"], None, "unmeasured", "phase H not run")

    st = H.get("ring_start") or {}
    pages = (g(ph, "R", "pages") or []) + (g(ph, "D", "tail") or [])
    if st:
        errs = [num(g(p, "reply", "errors")) for p in pages]
        a_first = num(g(H, "ring_start_snap", "worldAge"))
        on_rows = [r for r in rows if r.get("on") is not False]
        span = ((on_rows[-1]["age"] - a_first) * 60) if (on_rows and a_first is not None) else None
        missing_pages = [p for p in pages if not p.get("file")]
        obs = {"start_ok": st.get("ok"), "armed": st.get("armed"), "probe_missing": g(st, "probe", "missing"),
               "pages": len(pages), "pages_missing": len(missing_pages), "errors": errs,
               "gErrors": [g(p, "reply", "gErrors") for p in pages], "rows": len(rows),
               "online_rows": len(on_rows), "game_minutes_since_start": span,
               "overwritten": [g(p, "reply", "overwritten") for p in pages]}
        ok = (st.get("ok") is True and bool(st.get("armed")) and pages and not missing_pages
              and all((e or 0) == 0 for e in errs) and span is not None and len(on_rows) >= span - 2)
        grade("H2", PRED["H2"], obs, "as_predicted" if ok else "falsified",
              "a start refused, a page missing, an error, too few rows")
    else:
        grade("H2", PRED["H2"], None, "unmeasured", "the ring was never started")
    bench = H.get("bench") or {}
    R["benchRow"] = {"n": bench.get("n"), "ms": bench.get("ms"), "usPerCall": bench.get("usPerCall"),
                     "watched_users": 1, "us_per_row": bench.get("usPerCall"), "error": bench.get("error")}

    C1, C5 = ph.get("C1") or {}, ph.get("C5") or {}
    if C1:
        a0, a1 = num(g(C1, "before", "snap", "worldAge")), num(g(C1, "after", "snap", "worldAge"))
        if a0 is not None and a1 is not None:
            R["speed1"] = cadence(window(rows, a0, a1)) | {"window_age": [a0, a1]}
        R["speed1_bus"] = {"before": g(C1, "before", "values"), "after": g(C1, "after", "values")}
    if C5:
        a0, a1 = num(g(C5, "fast_snap", "worldAge")), num(g(C5, "after", "snap", "worldAge"))
        R["speed5_bus"] = {"before": g(C5, "before", "values"), "after": g(C5, "after", "values"),
                           "mult_fast": g(C5, "fast_snap", "mult"), "mult_after": g(C5, "slow_snap", "mult"),
                           "rcon": [g(C5, "rcon_fast"), g(C5, "rcon_slow")]}
        if a0 is not None and a1 is not None:
            c = R["speed5"] = cadence(window(rows, a0, a1)) | {"window_age": [a0, a1]}
            wpm, share = c.get("writes_per_game_minute"), c.get("dtM_le_1_05_share")
            if wpm is not None and share is not None:
                ok = wpm >= WPM_MIN and share >= DTM_SHARE
                grade("S0", PRED["S0"], {"writes_per_game_minute": wpm, "dtM_le_1_05_share": share,
                                         "rows": c.get("rows"), "game_minutes": c.get("game_minutes")},
                      "as_predicted" if ok else "falsified", "writes per game minute < 0.99 or the dtM share < 0.99")
            else:
                grade("S0", PRED["S0"], c, "unmeasured", "no ring rows in the speed-5 window")
        else:
            grade("S0", PRED["S0"], None, "unmeasured", "no world ages around the speed-5 window")
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "phase C5 not run")

    E = ph.get("E") or {}
    if E:
        eats_path = "_G.NutritionRevamp.server.intake.stats.landed"
        e0 = E.get("landed_before")
        land = next((r for r in rows if e0 is not None and num(r.get(eats_path)) is not None and r[eats_path] > e0),
                    None)
        prev = None
        if land is not None:
            prev = next((r for r in reversed(rows) if r["s"] < land["s"]), None)
        obs = {"landed_polled": E.get("landed"), "landing_age_polled": g(E, "landed_snap", "worldAge"),
               "landing_row": land and land["s"], "landed_before": e0, "eats_before": E.get("eats_before")}
        ok = False
        if land is not None and prev is not None:
            def d(k):
                a, b = num(prev.get(k)), num(land.get(k))
                return (b - a) if (a is not None and b is not None) else None
            obs.update({"row_before": prev["s"], "landed_delta": d(eats_path),
                        "eats_delta": d("_G.NutritionRevamp.server.intake.stats.eats"), "P_delta": d("satiety.P"),
                        "buffer_kcal_delta": d("stomach.buffer.calories"), "buffer_water_delta":
                        d("stomach.buffer.water"), "stomachFill_delta": d("stomachFill"), "inDay_delta": d("body.inDay"),
                        "monotony_n": land.get("monotony.t.[TKX.Mixed650].n"),
                        "HUNGER_before": prev.get("HUNGER"), "HUNGER_landing_row": land.get("HUNGER")})
            ok = (obs["landed_delta"] == 1 and (obs["P_delta"] or 0) > 0 and (obs["buffer_kcal_delta"] or 0) >= 600
                  and obs["monotony_n"] is not None)
        obs["after_rec"] = g(E, "after_rec", "values")
        grade("EAT", PRED["EAT"], obs, "as_predicted" if ok else ("falsified" if E.get("eat") else "unmeasured"),
              "landed not +1, P not up, the buffer short of 600 kcal, no monotony entry")
    else:
        grade("EAT", PRED["EAT"], None, "unmeasured", "phase E not run")

    D = ph.get("D") or {}
    if D:
        obs = {"flushed": D.get("flushed"), "q0_wall": g(D, "q0", "wall"), "flushed_wall": D.get("flushed_wall"),
               "quit_rc": D.get("quit_rc"), "polls": D.get("poll_count")}
        grade("F", PRED["F"], obs, "as_predicted" if D.get("flushed") else "falsified", "the cap passes")
    else:
        grade("F", PRED["F"], None, "unmeasured", "phase D not run")

    slots = out.get("slots") or {}
    best = slots.get("newest_row") or {}
    on_rows = [r for r in rows if r.get("on") is not False and not r.get("norec")]
    if best and on_rows:
        last = on_rows[-1]
        R["drift"] = {"slot": best.get("copy"), "slot_satiety_t": best.get("satiety_t"),
                      "slot_lastSeen": best.get("lastSeen"), "last_online_row": last["s"],
                      "last_online_row_age": last["age"],
                      "lost_game_minutes": ((last["age"] - best["satiety_t"]) * 60)
                      if num(best.get("satiety_t")) is not None else None,
                      "last_online_row_satiety_t": last.get("satiety.t"),
                      "flush_line_satiety_t": None}
        txt = g(D, "last", "value")
        if isinstance(txt, str):
            try:
                R["drift"]["flush_line_satiety_t"] = (json.loads(txt).get("rec") or {}).get("satiety", {}).get("t")
            except ValueError:
                pass

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

try:
    shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
    copied.append(MANIFEST_NAME)
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
            read_slots()
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
                  "speed5": {k: g(out, "readings", "speed5", k) for k in ("writes_per_game_minute",
                                                                            "dtM_le_1_05_share", "rows")},
                  "benchRow": g(out, "readings", "benchRow"),
                  "drift": g(out, "readings", "drift"),
                  "replay_ok": g(out, "replay", "diff", "ok"), "replay_error": g(out, "replay", "error"),
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir},
                 indent=1, default=str)[:6000])
