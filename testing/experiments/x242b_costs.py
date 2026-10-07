"""x242b-costs -- Plan 10c Task H2b (live): the phases run x242 (x242-20261007-151339, driver fadf200) never reached,
because the host's memory reaper killed it at the start of its phase C (ruling H2-1: x242 stands for its phases A
and B; the unrun phases are this new experiment, never an edit of x242's driver nor a re-run of A or B). What a
day-close minute, a seven-close catch-up, first sight and one mirror send cost (bench C); what the client tooltip's
entry costs (D); H6's arm E (the global store's save at 0, 100, 500 and 2000 seeded records, and a client's
ModData.request of the store at 2, 60 and 500 records); and the ghost calibration (ghost.bench, unfed then fed; F).
On the SAME staged instrument copy x242 booted (release/hitch-x242/NutritionRevamp/Contents/mods/NutritionRevamp, the
tree at 9578eb9 staged by `python tools/release_pack.py stage mod/NutritionRevamp --out release/hitch-x242`,
MANIFEST.json sha256 c86e295a...b389; the five instrumented server files kept as testing/spikes/instruments/
x242_NR_Server_<Name>.lua, their sha256 checked equal to the staged copy and to x242's artifact before the boot;
release/ is gitignored; mod/ is never booted). One boot of profile x24-costs-b (a copy of x24-costs: fixture two,
admin -debug then bob release, Nutrition false, DayLength 1). ONE artifact, `costs.json`, plus the staged
MANIFEST.json copied byte-identical beside it. The phase code is COPIED from x242_costs.py (which is never edited);
the instrument it drives is described in x242_costs.py's docstring (NutritionRevamp.server.bench: cArm/cText,
profStart/profStop/profReset/accText; NR_H6.seed/clear/count/request/rx; NR_H2C.arm/hit/miss). Written BEFORE the
boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

PHASES (order S0, C, D, E, F, E3, Z; no in-play window, no phase A, B or G -- the session is kept short because x242
was killed for memory):
  S0  ready marks, verify rows, players, time; wait until both real records exist and the minute ran MIN_RUNS times.
  C   bench C, C_N sets with the profile off (the brackets only); then CS, CS_N sets with the profile and sub-blocks on
      (the burst sources by sub-block). Back to back.
  D   the client bench on admin and bob: NR_H2C.arm Base.Apple, bench.global NR_H2C.hit D_N x D_REPEAT, NR_H2C.miss
      D_N x D_REPEAT, NR_H2C.hit D_BIG x1.
  E   H6's arm E without its 500-record request: E1 (the save) at SAVE_SEEDS: NR_H6.seed n, then two RCON saves
      SAVE_GAP_S apart (the first save of the process is E1(0) k=1), each with tick.ring and perf.local armed before
      it and read after, the server-log lines it wrote (Saving GlobalModData -> Saving finish, Saving took, SaveAll
      took, Pausing clients) and global_mod_data.bin's size; E2 (the request) at 2 and 60 records (seeded = total -
      2): bob calls NR_H6.request, the ring around it, bob's NR_H6.rx and the server's and bob's log lines after.
      Order: E1(0), E2(2), E2(60), E1(100), E1(500), E1(2000); then NR_H6.clear.
  F   the ghost calibration in its own phase: ghost.load GHOST_N burst, ghost.bench BENCH_N, ghost.bench read until
      done; ghost.stop; ghost.load GHOST_N burst feed, ghost.bench BENCH_N, read until done; ghost.stop.
  E3  E2 at 500 records (NR_H6.seed 498, bob's request, as E2), then NR_H6.clear and one cleanup save. Written into
      phases.E.E2["500"] so the grading reads it beside the 2 and 60 requests.
  Z   the mod-error check.

DEVIATIONS: E2 at 500 runs after F (the H2b amendments allow it): it is expected to raise a parse exception on the
requesting client, which may cost the session bob, and ghost.load makes its ghosts from the online players, so F
needs both clients to match its predecessor's shape. E3 reads no player's behaviour, so the rule that no behaviour
reading follows ghost.bench holds. C1's comparison is against x242's phase A pooled in-play minute, read from x242's
committed artifact at start-up (meta.x242_A), since this session has no phase A.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured; the same as x242's for these
phases):
  C1    typ per run within 0.5..2x x242's phase A pooled in-play __run per run.
  Cclose  the day-close minute costs at most 3x the typical minute (close / typ <= 3; the plan's rule).
  Ccatch  the seven-close catch-up costs at most 25 ms.
  Cfs   first sight (fsLoad + fsBody + fsHooks) costs at most 2 ms (the plan's rule).
  Csend 60 mirror sends (60 x send) cost more than 5 ms (the plan's rule fires).
  D     the tooltip entry's same-item path costs at most 50 us a call (the plan's rule).
  F     ghostZeroDt 0, realZeroDt 0, no failure, no reason, in both benches; the fed ratio within 0.8..1.25.
  E1    the second save at 500 seeded records adds more than 25 ms of GlobalModData save over n = 0 (H6's rule fires);
        global_mod_data.bin grows by 0.7..1.3x store_size.py's 10821.8 bytes a record over n = 0.
  E2    at 2 and 60 records the table arrives (isTable, keys = the record count); at 500 no event arrives and the
        server log carries an exception line after the request. The request at 60 costs more than 5 ms of server
        frame over the ring's median period (H6's rule fires).
  Z     no mod error line; admin not parked.

KNOWN BENCH LIMITS (x242's report): first sight's fsHooks skips Fast's re-hoist while admin's handle exists; the
benches write admin's Java state (cost readings only).

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


PROFILE = "x24-costs-b"
PREFIX = "x242b"
SESSION = ("Plan 10c Task H2b: the phases x242 never reached (ruling H2-1) -- the interleaved burst-source bench, the "
           "client tooltip bench, H6's arm E (the store's save and request) and the ghost calibration -- on the staged "
           "copy at 9578eb9 with the x242 instruments; one boot of " + PROFILE)
ARTIFACT = "costs.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/hitch-x242/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGE_SERVER = STAGE_MOD + "/common/media/lua/server"
STAGED_AT = "9578eb9"
MANIFEST_SHA256 = "c86e295a3ef4c70bde57ab436c9dc3919172dd81db2a8a71164659d62415b389"
X242_ARTIFACT = "testing/artifacts/x242-20261007-151339/costs.json"
INSTR = ("Bench", "Nutrients", "Metabolism", "Effects", "Strength")
INSTR_DIR = "testing/spikes/instruments"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
STORE_SIZE = "testing/spikes/out/store-size.json"
NR = "NutritionRevamp"
BENCH = "NutritionRevamp.server.bench"
REC = "NutritionRevamp.server.store.records"
STEPS = ("bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight")
HEALS = ("nutrients/heal.pre", "nutrients/heal.post", "metabolism/heal.pre", "metabolism/heal.post",
         "effects/heal.pre", "effects/heal.post", "strength/heal")
APPLE = "Base.Apple"
S0_WAIT_S = 90.0
MIN_RUNS = 4
C_N = 1000
CS_N = 200
C_CAP_S = 600.0
D_N = 1000
D_REPEAT = 3
D_BIG = 10000
GHOST_N = 20
BENCH_N = 40
BENCH_CAP_S = 180.0
SAVE_SEEDS = (0, 100, 500, 2000)
REQ_TOTALS = (2, 60, 500)
REALS = 2
SAVE_GAP_S = 30
REQ_WAIT_S = 10
RING_SAVE_N = 600
PERF_SAVE_N = 300
RING_REQ_N = 300
RESULT_WAIT_S = 30.0
POLL_S = 0.4
PAGE = 150
LOG_LIMIT = 400
BAND_TYP = (0.5, 2.0)
CLOSE_X = 3.0
CATCH_MS = 25.0
FS_MS = 2.0
SEND60_MS = 5.0
TOOLTIP_US = 50.0
FED_BAND = (0.8, 1.25)
SAVE_ADD_MS = 25.0
BIN_BAND = (0.7, 1.3)
REQ_MS = 5.0
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|fast: |options: |effects: .* failed|"
                         r"nutrients: .* failed|metabolism: .* failed|non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
# the save and request lines; no probe this driver sends carries any of these words (the bus echo is dropped first)
SAVE_RX = re.compile(r"Saving|SaveAll|Pausing clients|GlobalModData|global_mod_data|Exception|IllegalMonitor|"
                     r"BufferOverflow|receiveRequest", re.I)
ST_RX = re.compile(r"f:(\d+) st:([\d,]+)>\s*(.*)$")

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
    "C1": {"typ ms per run / x242 A's __run ms per run": list(BAND_TYP)},
    "Cclose": {"close / typ": f"<= {CLOSE_X}"},
    "Ccatch": {"catch ms per run": f"<= {CATCH_MS}"},
    "Cfs": {"fsLoad + fsBody + fsHooks ms": f"<= {FS_MS}"},
    "Csend": {"60 x send ms": f"> {SEND60_MS}"},
    "D": {"hit us per call (each client, each repeat)": f"<= {TOOLTIP_US}"},
    "F": {"ghostZeroDt": 0, "realZeroDt": 0, "failures": 0, "fed ratio": list(FED_BAND)},
    "E1": {"second save GlobalModData ms at 500 minus at 0": f"> {SAVE_ADD_MS}",
           "bin growth per seeded record / 10821.8": list(BIN_BAND)},
    "E2": {"2 and 60": "table arrives with keys = records", "500": "no event; an exception line in the server log",
           "request frame ms over median period at 60": f"> {REQ_MS}"},
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
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release/hitch-x242",
             "predecessor": {"run_id": "x242-20261007-151339", "driver_commit": "fadf200",
                             "ruling": "H2-1: x242 stands for phases A and B; C, D, E and F are this run"},
             "instrument_note": "The same staged copy x242 booted: the five instrumented server files are kept "
                                "byte-identical as testing/spikes/instruments/x242_NR_Server_<Name>.lua (Bench, "
                                "Nutrients, Metabolism, Effects, Strength); their staged and kept sha256 are checked "
                                "equal here and against x242's artifact before the boot.",
             "cost_note": "Every reading is cost, not behaviour: the benches run copies of admin's record against "
                          "admin's real IsoPlayer (its Java writes land on admin), the ghosts likewise, and bench C "
                          "fires the first-sight hooks for admin. No behaviour row rests on this session.",
             "timer_note": "getTimestampMs is 1 ms resolution: every per-run or per-call cost is a total over many "
                           "runs divided by their count, stated with its count and its ms total; a sub-block's "
                           "bracket is two clock reads, so a block well under 1 ms reads 0 or 1 per run and only "
                           "its total over many runs is a cost."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "E2 at 500 records runs after F (phase E3): it is expected to raise a parse exception on the requesting "
        "client, which may cost the session bob, and F's ghost.load copies the online players; E3 reads no "
        "player's behaviour.",
        "C1 compares bench C's typ against x242's phase A pooled in-play __run per run (meta.x242_A), read from "
        "x242's committed artifact; this session has no in-play phase.",
        "No phase A, B or G: x242 stands for A and B (ruling H2-1), and G was dropped to keep the session short.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "summaries": {},
}
try:
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
    out["meta"]["staged_manifest_expected"] = MANIFEST_SHA256
    out["meta"]["instrument_sha256"] = {}
    with open(os.path.join(REPO, X242_ARTIFACT), encoding="utf-8") as fh:
        _x242 = json.load(fh)
    _x242_instr = (_x242.get("meta") or {}).get("instrument_sha256") or {}
    for n in INSTR:
        staged = sha256_file(os.path.join(REPO, STAGE_SERVER, f"NR_Server_{n}.lua"))
        kept = sha256_file(os.path.join(REPO, INSTR_DIR, f"x242_NR_Server_{n}.lua"))
        x242s = (_x242_instr.get(n) or {}).get("staged")
        out["meta"]["instrument_sha256"][n] = {"staged": staged, "kept": kept, "x242_staged": x242s,
                                               "equal": staged == kept == x242s}
    with open(os.path.join(REPO, STORE_SIZE), encoding="utf-8") as fh:
        _ss = json.load(fh)
    out["meta"]["store_size"] = {"per_record_mean": _ss.get("per_record_mean"),
                                 "file_bytes": {k: v.get("file_bytes") for k, v in (_ss.get("scales") or {}).get("full", {}).items()}}
except (OSError, ValueError) as e:
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


def log_size(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return None


def log_slice(p, start, rx, limit=120):
    """Lines matching rx written to p after byte offset start, the bus echo dropped first."""
    hits, skipped = [], 0
    if p is None or start is None:
        return {"lines": hits, "echo_excluded": skipped}
    try:
        with open(p, "rb") as fh:
            fh.seek(start)
            data = fh.read()
    except OSError as e:
        return {"lines": hits, "echo_excluded": skipped, "error": f"{type(e).__name__}: {e}"}
    for line in data.decode("utf-8", errors="replace").splitlines():
        if not rx.search(line):
            continue
        if ECHO_RX.search(line):
            skipped += 1
            continue
        hits.append(line.strip()[:600])
        if len(hits) >= limit:
            break
    return {"lines": hits, "echo_excluded": skipped}


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
    a["epoch_ms_before"] = r.get("epoch_ms_before")
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


def lcall(side, fn, tag, *args, timeout=30):
    return keep(step(tag, side, "lua.call", " ".join([fn] + [str(a) for a in args]), timeout=timeout))


def setp(fieldpath, value, tag):
    return keep(step(tag, SRV, "lua.setpath", f"{fieldpath} {value}"))


def rcon(cmd, tag):
    t_before, e_before = wall(), time.time()
    try:
        ok, rep = server.rcon(cmd)
    except Exception as e:                     # noqa: BLE001
        ok, rep = False, f"{type(e).__name__}: {e}"
    row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": wall(), "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "ack": {"ok": ok, "reply": str(rep)[:300]}}
    out["steps"].append(row)
    tl.mark("rcon", cmd=cmd, ok=ok)
    return {"ok": ok, "reply": str(rep)[:300], "wall": t_before, "epoch_ms_before": row["epoch_ms_before"],
            "epoch_ms_after": row["epoch_ms_after"]}


def counters(tag):
    t = gread(SRV, f"{BENCH}.ticks", f"{tag}_ticks")
    m = gread(SRV, f"{BENCH}.minutes", f"{tag}_minutes")
    return {"ticks": num(val(t)), "minutes": num(val(m)), "wall": t["wall"], "wall_after": m["wall_after"]}


def minstats(tag):
    d = {k: num(val(gread(SRV, f"{NR}.server.minute.stats.{k}", f"{tag}_min_{k}"))) for k in ("runs", "failures")}
    for k in ("minutes", "drained"):
        d[f"players_{k}"] = num(val(gread(SRV, f"{NR}.server.players.{k}", f"{tag}_p_{k}")))
    return d


def snap(tag):
    return keep(step(tag, SRV, "time.snapshot"))


def wait_minute(target, tag, cap_s):
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


def wait_age(target, tag, cap_s):
    end = time.time() + cap_s
    polls = []
    while True:
        s = snap(tag)
        a = num(s.get("worldAge"))
        polls.append({"wall": s.get("wall"), "worldAge": a, "hour": s.get("hour"), "minutes": s.get("minutes")})
        if a is not None and a >= target:
            return {"ok": True, "polls": polls}
        if time.time() >= end:
            note(f"{tag}: world age {target} not reached inside {cap_s} s (last {a})")
            return {"ok": False, "polls": polls}
        time.sleep(POLL_S)


def wait_doc(name, after):
    try:
        return server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
    except Exception as e:                     # noqa: BLE001 - a missing document is a recorded fault
        note(f"result {name}: {type(e).__name__}: {e}")
        return None


def acc_read(prefix, tag):
    r = lcall(SRV, f"{BENCH}.accText", tag, prefix)
    return {"prefix": prefix, "text": r.get("r1"), "keys": r.get("r2"), "min_failures": r.get("r3"), "ok": r.get("ok"),
            "err": r.get("err"), "wall": r.get("wall")}


def accs(prefixes, tag):
    return {p: acc_read(p, f"{tag}_acc_{i}") for i, p in enumerate(prefixes)}


def hist_read(tag):
    r = lcall(SRV, f"{BENCH}.histText", tag)
    return {"text": r.get("r1"), "sets": r.get("r2"), "minute": r.get("r3")}


def ring_read(tag):
    first = lcall(SRV, f"{BENCH}.ringText", f"{tag}_n", 1, 0)
    count = int(num(first.get("r2")) or 0)
    rows, i = [], 1
    while i <= count:
        r = lcall(SRV, f"{BENCH}.ringText", f"{tag}_{i}", i, i + PAGE - 1)
        txt = r.get("r1")
        if isinstance(txt, str) and txt:
            for part in txt.split(";"):
                f = part.split(",")
                if len(f) == 6:
                    rows.append([f[0]] + [num(x) for x in f[1:]])
        i += PAGE
    return {"count": count, "rows": rows}


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
    P["time"] = snap("S0_time")
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}
    end = time.time() + S0_WAIT_S
    polls = []
    while True:
        recs = {u: gread(SRV, f"{REC}.{u}", f"S0_rec_{u}") for u in USERS}
        runs = num(val(gread(SRV, f"{NR}.server.minute.stats.runs", "S0_runs")))
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end:
            break
        time.sleep(POLL_S)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")
    P["h6_server"] = lcall(SRV, "NR_H6.count", "S0_h6_count")


def c_run(tag, n):
    R = {"arm": lcall(SRV, f"{BENCH}.cArm", f"{tag}_arm", n, "admin")}
    end = time.time() + C_CAP_S
    polls = 0
    while True:
        r = lcall(SRV, f"{BENCH}.cText", f"{tag}_poll")
        polls += 1
        if r.get("r2") is True or time.time() >= end:
            break
        time.sleep(2.0)
    R["text"] = r.get("r1")
    R["done"] = r.get("r2")
    R["sets"] = r.get("r3")
    R["polls"] = polls
    if R["done"] is not True:
        note(f"{tag}: the bench did not finish inside {C_CAP_S} s")
    return R


def phase_C():
    P = out["phases"]["C"] = {}
    P["stop_first"] = lcall(SRV, f"{BENCH}.profStop", "C_stop0")
    P["minstats_before"] = minstats("C0")
    P["C"] = c_run("C", C_N)
    persist()
    P["cs_reset"] = lcall(SRV, f"{BENCH}.profReset", "CS_reset")
    P["cs_start"] = lcall(SRV, f"{BENCH}.profStart", "CS_start", "true")
    P["CS"] = c_run("CS", CS_N)
    P["cs_stop"] = lcall(SRV, f"{BENCH}.profStop", "CS_stop")
    P["cs_acc"] = accs(["bench:typ|", "bench:close|", "bench:catch|"], "CS")
    P["minstats_after"] = minstats("C1")
    out["world_changes"]["left_in_place"].append("C: bench copies of admin's record ran against admin's player; the "
                                                 "first-sight hooks fired for admin 1200 times; 1200 mirrors sent to "
                                                 "admin")


def phase_D():
    P = out["phases"]["D"] = {}
    P["spawn"] = {u: rcon(f'additem "{u}" "{APPLE}" 1', f"D_additem_{u}") for u in USERS}
    time.sleep(3.0)
    for u, side in (("admin", ADMIN), ("bob", BOB)):
        D = P[u] = {"arm": lcall(side, "NR_H2C.arm", f"D_arm_{u}", APPLE), "hit": [], "miss": []}
        for i in range(D_REPEAT):
            D["hit"].append(keep(step(f"D_hit_{u}_{i}", side, "bench.global", f"NR_H2C.hit {D_N}", timeout=60)))
        for i in range(D_REPEAT):
            D["miss"].append(keep(step(f"D_miss_{u}_{i}", side, "bench.global", f"NR_H2C.miss {D_N}", timeout=60)))
        D["hit_big"] = keep(step(f"D_hitbig_{u}", side, "bench.global", f"NR_H2C.hit {D_BIG}", timeout=90))
        D["stats"] = {k: num(val(gread(side, f"{NR}.client.tooltip.stats.{k}", f"D_st_{u}_{k}")))
                      for k in ("builds", "cacheHits", "errors")}


def bench_leg(tag, sched):
    L = {"load": keep(step(f"{tag}_load", SRV, "ghost.load", f"{GHOST_N} {sched}"))}
    L["arm"] = keep(step(f"{tag}_arm", SRV, "ghost.bench", str(BENCH_N)))
    end = time.time() + BENCH_CAP_S
    while True:
        r = keep(step(f"{tag}_read", SRV, "ghost.bench", "read"))
        if r.get("done") is True or time.time() >= end:
            break
        time.sleep(1.0)
    L["read"] = r
    if r.get("done") is not True:
        note(f"{tag}: ghost.bench not done inside {BENCH_CAP_S} s")
    L["stop"] = keep(step(f"{tag}_stop", SRV, "ghost.stop"))
    return L


def phase_F():
    P = out["phases"]["F"] = {}
    P["unfed"] = bench_leg("F_unfed", "burst")
    persist()
    P["fed"] = bench_leg("F_fed", "burst feed")
    out["world_changes"]["left_in_place"].append("F: ghost.bench advanced the real records and moved their pushes "
                                                 "(no behaviour reading follows)")


def bin_size():
    hits = sorted(glob.glob(os.path.join(run_dir, "server", "Saves", "**", "global_mod_data.bin"), recursive=True))
    return {os.path.relpath(h, run_dir).replace(os.sep, "/"): log_size(h) for h in hits}


def seed(n, tag):
    return lcall(SRV, "NR_H6.seed", tag, n, timeout=90)


def one_save(n, k):
    tag = f"e1_{n}_{k}"
    S = {"n": n, "k": k}
    S["ring_arm"] = keep(step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_SAVE_N)))
    S["perf_arm"] = keep(step(f"{tag}_perf_arm", SRV, "perf.local", str(PERF_SAVE_N)))
    off = log_size(server.log_path)
    S["log_offset"] = off
    S["save"] = rcon("save", f"{tag}_save")
    time.sleep(SAVE_GAP_S)
    after = time.time() - 1.0
    S["ring_read"] = keep(step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}"))
    S["perf_read"] = keep(step(f"{tag}_perf_read", SRV, "perf.local", f"read {tag}"))
    S["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
    S["perf_doc"] = wait_doc(f"perf-local-{tag}", after)
    S["log"] = log_slice(server.log_path, off, SAVE_RX)
    S["bin"] = bin_size()
    persist()
    return S


def one_request(total, tag):
    R = {"total": total}
    R["count"] = lcall(SRV, "NR_H6.count", f"{tag}_count")
    R["rx_before"] = {k: val(gread(BOB, f"NR_H6.rx.{k}", f"{tag}_rx0_{k}")) for k in ("n", "keys", "sent")}
    R["ring_arm"] = keep(step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_REQ_N)))
    off = log_size(server.log_path)
    c = clients.get("bob") if isinstance(clients, dict) else None
    con = getattr(c, "console", None)
    coff = log_size(con) if con else None
    R["log_offset"], R["console_offset"] = off, coff
    R["request"] = lcall(BOB, "NR_H6.request", f"{tag}_request")
    time.sleep(REQ_WAIT_S)
    after = time.time() - 1.0
    R["rx_after"] = {k: val(gread(BOB, f"NR_H6.rx.{k}", f"{tag}_rx1_{k}"))
                     for k in ("n", "name", "isTable", "keys", "lag", "sent", "sentAt", "at")}
    R["ring_read"] = keep(step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}"))
    R["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
    R["log"] = log_slice(server.log_path, off, SAVE_RX)
    R["console"] = log_slice(con, coff, SAVE_RX) if con else None
    R["bob_seen"] = dict(getattr(c, "seen", {})) if c is not None else None
    persist()
    return R


def phase_E():
    P = out["phases"].setdefault("E", {"E1": {}, "E2": {}})
    P["stop_first"] = lcall(SRV, f"{BENCH}.profStop", "E_stop0")

    def e1(n):
        P["E1"][str(n)] = {"seed": seed(n, f"E1_seed_{n}"), "saves": [one_save(n, 1), one_save(n, 2)]}

    def e2(total):
        P["E2"][str(total)] = {"seed": seed(total - REALS, f"E2_seed_{total}"), "req": one_request(total, f"e2_{total}")}

    e1(0)
    e2(2)
    e2(60)
    e1(100)
    e1(500)
    e1(2000)
    P["clear"] = lcall(SRV, "NR_H6.clear", "E_clear", timeout=60)
    P["clear_count"] = lcall(SRV, "NR_H6.count", "E_clear_count")
    out["world_changes"]["left_in_place"].append("E: up to 2000 synthetic records seeded into the store and cleared; "
                                                 "eight RCON saves; two client requests of the store")


def phase_E3():
    P = out["phases"].setdefault("E", {"E1": {}, "E2": {}})
    P.setdefault("E2", {})
    total = REQ_TOTALS[-1]
    P["E2"][str(total)] = {"seed": seed(total - REALS, f"E2_seed_{total}"), "req": one_request(total, f"e2_{total}")}
    P["E3_clear"] = lcall(SRV, "NR_H6.clear", "E3_clear", timeout=60)
    P["E3_clear_count"] = lcall(SRV, "NR_H6.count", "E3_clear_count")
    off = log_size(server.log_path)
    P["cleanup_save"] = rcon("save", "E3_cleanup_save")
    time.sleep(15)
    P["cleanup_log"] = log_slice(server.log_path, off, SAVE_RX)
    P["cleanup_bin"] = bin_size()
    P["ring_off"] = keep(step("E3_ring_off", SRV, "tick.ring", "off"))
    out["world_changes"]["left_in_place"].append("E3: 498 synthetic records seeded and cleared after F; one client "
                                                 "request of the store at 500 records; one cleanup save")


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["players"] = keep(step("Z_players", SRV, "players"))
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["minstats"] = minstats("Z")
    P["h6_count"] = lcall(SRV, "NR_H6.count", "Z_h6_count")


def body():
    order = (("S0", phase_S0), ("C", phase_C), ("D", phase_D), ("E", phase_E), ("F", phase_F), ("E3", phase_E3),
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


def pct(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = max(1, min(len(s), math.ceil(round(p * len(s), 9))))
    return s[k - 1]


def summ(xs):
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "p50": pct(xs, 0.5), "p99": pct(xs, 0.99), "max": max(xs) if xs else None,
            "min": min(xs) if xs else None, "mean": (sum(xs) / len(xs)) if xs else None, "sum": sum(xs) if xs else 0}


def parse_acc(text):
    """{set: {name: {ms, runs}}} from key=ms/runs;..."""
    d = {}
    if not isinstance(text, str):
        return d
    for part in text.split(";"):
        m = re.match(r"^([^|=]+)\|([^=]+)=(\-?[\d.]+)/(\-?[\d.]+)$", part.strip())
        if m:
            d.setdefault(m.group(1), {})[m.group(2)] = {"ms": float(m.group(3)), "runs": float(m.group(4))}
    return d


def merge_acc(reads):
    d = {}
    for r in (reads or {}).values():
        for s, names in parse_acc((r or {}).get("text")).items():
            d.setdefault(s, {}).update(names)
    return d


def pool(sets):
    """Sum ms and runs over several sets' accumulators."""
    P = {}
    for names in sets:
        for k, v in names.items():
            q = P.setdefault(k, {"ms": 0.0, "runs": 0.0})
            q["ms"] += v["ms"]
            q["runs"] += v["runs"]
    return P


def shares(P):
    """Per-run ms, the share of __run and of its own step, for every key of a pooled accumulator."""
    run = P.get("__run") or {}
    run_ms, run_n = run.get("ms") or 0.0, run.get("runs") or 0.0
    rows = {}
    for k, v in P.items():
        stepk = k.split("/", 1)[0] if "/" in k else None
        st = P.get(stepk) if stepk else None
        rows[k] = {"ms": v["ms"], "runs": v["runs"], "ms_per_run": (v["ms"] / v["runs"]) if v["runs"] else None,
                   "ms_per_pipeline_run": (v["ms"] / run_n) if run_n else None,
                   "share_of_run": (v["ms"] / run_ms) if run_ms else None,
                   "share_of_step": (v["ms"] / st["ms"]) if st and st.get("ms") else None}
    heal = sum((P.get(h) or {}).get("ms", 0.0) for h in HEALS)
    subs = sorted([k for k in P if "/" in k], key=lambda k: -P[k]["ms"])
    targets = [k for k in subs if (rows[k]["share_of_step"] or 0) >= 0.15]
    return {"rows": rows, "run_ms": run_ms, "run_runs": run_n, "run_ms_per_run": (run_ms / run_n) if run_n else None,
            "heal_ms": heal, "heal_share_of_run": (heal / run_ms) if run_ms else None,
            "nutrient_heals_share_of_run": (sum((P.get(h) or {}).get("ms", 0.0) for h in HEALS[:2]) / run_ms)
            if run_ms else None,
            "ranking": [[k, rows[k]["share_of_run"]] for k in subs], "refactor_targets_15pct_of_step": targets}


def ring_summary(rows):
    by = {}
    for r in rows or []:
        u, ms, mn, mc, nc, ec = r
        d = by.setdefault(u, {"all": [], "close": [], "plain": []})
        d["all"].append(ms)
        (d["close"] if (mc or 0) >= 1 else d["plain"]).append(ms)
    outd = {}
    for u, d in by.items():
        pl = summ(d["plain"])
        outd[u] = {"all": summ(d["all"]), "plain": pl, "close_runs_ms": d["close"],
                   "close_over_plain_mean": [(x / pl["mean"]) if pl["mean"] else None for x in d["close"]]}
    return outd


def parse_c(text):
    d = {"kinds": {}}
    if not isinstance(text, str):
        return d
    for part in text.split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        m = re.match(r"^(\-?[\d.]+)/(\-?[\d.]+)/(\-?[\d.]+)/(\-?[\d.]+)$", v)
        if m:
            ms, n, mx, cl = (float(m.group(i)) for i in range(1, 5))
            d["kinds"][k] = {"ms": ms, "n": n, "max": mx, "closes": cl, "ms_per": (ms / n) if n else None}
        else:
            d[k] = v
    return d


def frames_of(doc):
    F = (doc or {}).get("frames_list") or {}
    keys = ("frame", "start", "stop", "busy", "period", "endPeriod", "minute", "runs", "ghostMs")
    cols = [F.get(k) or [] for k in keys]
    n = min(len(c) for c in cols) if cols else 0
    return [dict(zip(keys, (c[i] for c in cols))) for i in range(n)]


def event_frames(doc, epoch_ms, before_ms=500, after_ms=15000):
    fr = frames_of(doc)
    per = [f["period"] for f in fr if f["period"] is not None and f["period"] >= 0]
    endp = [f["endPeriod"] for f in fr if f["endPeriod"] is not None and f["endPeriod"] >= 0]
    base_p, base_e = pct(per, 0.5), pct(endp, 0.5)
    win = [f for f in fr if f["start"] is not None and f["start"] >= 0 and epoch_ms is not None
           and epoch_ms - before_ms <= f["start"] <= epoch_ms + after_ms]
    wp = [f["period"] for f in win if f["period"] is not None and f["period"] >= 0]
    we = [f["endPeriod"] for f in win if f["endPeriod"] is not None and f["endPeriod"] >= 0]
    wb = [f["busy"] for f in win if f["busy"] is not None and f["busy"] >= 0]
    top = sorted(win, key=lambda f: -(f["period"] if f["period"] is not None else -1))[:3]
    mp, me = (max(wp) if wp else None), (max(we) if we else None)
    return {"frames": len(fr), "window_frames": len(win), "median_period": base_p, "median_endPeriod": base_e,
            "max_period": mp, "max_endPeriod": me, "max_busy": max(wb) if wb else None,
            "over_median_period": (mp - base_p) if mp is not None and base_p is not None else None,
            "over_median_endPeriod": (me - base_e) if me is not None and base_e is not None else None,
            "top3": [{k: f[k] for k in ("frame", "start", "busy", "period", "endPeriod")} for f in top]}


def st_of(line):
    m = ST_RX.search(line)
    if not m:
        return None, None, line
    return int(m.group(1)), int(m.group(2).replace(",", "")), m.group(3)


def save_lines(lines):
    D = {"gmd_ms": None, "saving_took_ms": None, "saveall_took_ms": None, "pausing": False, "exceptions": 0}
    st_g = None
    for ln in lines or []:
        f, st, msg = st_of(ln)
        if "Saving GlobalModData" in msg:
            st_g = st
        elif "Saving finish" in msg and st_g is not None and st is not None and D["gmd_ms"] is None:
            D["gmd_ms"] = st - st_g
        m = re.search(r"Saving took ([\d.]+) ms", msg)
        if m and D["saving_took_ms"] is None:
            D["saving_took_ms"] = float(m.group(1))
        m = re.search(r"SaveAll took ([\d.]+) ms", msg)
        if m and D["saveall_took_ms"] is None:
            D["saveall_took_ms"] = float(m.group(1))
        if "Pausing clients" in msg:
            D["pausing"] = True
        if re.search(r"Exception|IllegalMonitor|BufferOverflow", msg):
            D["exceptions"] += 1
    return D


def grade_all():
    ph = out["phases"]
    S = out["summaries"]
    # C
    C = ph.get("C") or {}
    pc = parse_c(g(C, "C", "text"))
    K = pc.get("kinds") or {}
    if K:
        mp = {k: v.get("ms_per") for k, v in K.items()}
        typ, close, catch = mp.get("typ"), mp.get("close"), mp.get("catch")
        fs = sum(x for x in (mp.get("fsLoad"), mp.get("fsBody"), mp.get("fsHooks")) if x is not None)
        S["C"] = {"parsed": pc, "ms_per": mp, "close_over_typ": (close / typ) if typ else None,
                  "catch_over_typ": (catch / typ) if typ else None, "close_minus_typ": (close - typ) if None not in (close, typ) else None,
                  "catch_minus_typ_per_close": ((catch - typ) / 7.0) if None not in (catch, typ) else None,
                  "first_sight_ms": fs, "send60_ms": (60 * mp["send"]) if mp.get("send") is not None else None,
                  "build60_ms": (60 * mp["build"]) if mp.get("build") is not None else None,
                  "cs": parse_c(g(C, "CS", "text")),
                  "cs_shares": {k: shares(v) for k, v in merge_acc(C.get("cs_acc")).items()}}
        a_run = g(out, "meta", "x242_A", "run_ms_per_run")
        if typ is not None and a_run:
            r = typ / a_run
            S["C"]["typ_over_A"] = r
            grade("C1", PRED["C1"], {"typ_ms": typ, "A_run_ms": a_run, "ratio": r},
                  "as_predicted" if BAND_TYP[0] <= r <= BAND_TYP[1] else "falsified", "outside 0.5..2x")
        else:
            grade("C1", PRED["C1"], {"typ_ms": typ, "A_run_ms": a_run}, "unmeasured", "no typ or A reading")
        co = S["C"]["close_over_typ"]
        grade("Cclose", PRED["Cclose"], {"close_ms": close, "typ_ms": typ, "close_over_typ": co,
                                         "closes": g(K, "close", "closes"), "n": g(K, "close", "n")},
              "unmeasured" if co is None else ("as_predicted" if co <= CLOSE_X else "falsified"), "close over 3x typ")
        grade("Ccatch", PRED["Ccatch"], {"catch_ms": catch, "closes": g(K, "catch", "closes"), "n": g(K, "catch", "n"),
                                         "max": g(K, "catch", "max")},
              "unmeasured" if catch is None else ("as_predicted" if catch <= CATCH_MS else "falsified"), "over 25 ms")
        grade("Cfs", PRED["Cfs"], {"fsLoad": mp.get("fsLoad"), "fsBody": mp.get("fsBody"), "fsHooks": mp.get("fsHooks"),
                                   "sum": fs}, "as_predicted" if fs <= FS_MS else "falsified", "over 2 ms")
        s60 = S["C"]["send60_ms"]
        grade("Csend", PRED["Csend"], {"send_ms": mp.get("send"), "send60_ms": s60, "build_ms": mp.get("build"),
                                       "payloadKeys": pc.get("payloadKeys"), "fail": pc.get("fail")},
              "unmeasured" if s60 is None else ("as_predicted" if s60 > SEND60_MS else "falsified"), "60 sends at most 5 ms")
    else:
        for k in ("C1", "Cclose", "Ccatch", "Cfs", "Csend"):
            grade(k, PRED[k], None, "unmeasured", "no bench C reading")

    # D
    D = ph.get("D") or {}
    if D:
        dd = {}
        for u in USERS:
            du = D.get(u) or {}
            dd[u] = {"arm": {k: (du.get("arm") or {}).get(k) for k in ("ok", "r1", "r2", "r3", "err")},
                     "hit_us": [num(r.get("usPerCall")) for r in du.get("hit") or []],
                     "miss_us": [num(r.get("usPerCall")) for r in du.get("miss") or []],
                     "hit_ms": [num(r.get("ms")) for r in du.get("hit") or []],
                     "miss_ms": [num(r.get("ms")) for r in du.get("miss") or []],
                     "hit_big_us": num((du.get("hit_big") or {}).get("usPerCall")),
                     "hit_big_ms": num((du.get("hit_big") or {}).get("ms")), "stats": du.get("stats")}
        S["D"] = dd
        allhit = [x for u in USERS for x in dd[u]["hit_us"]]
        armed = all((dd[u]["arm"].get("r1") is True) for u in USERS)
        if not armed or not allhit or any(x is None for x in allhit):
            grade("D", PRED["D"], dd, "unmeasured", "an arm or a bench call failed")
        else:
            grade("D", PRED["D"], dd, "as_predicted" if max(allhit) <= TOOLTIP_US else "falsified", "over 50 us")
    else:
        grade("D", PRED["D"], None, "unmeasured", "phase D not run")

    # F
    F = ph.get("F") or {}
    fu, ff = g(F, "unfed", "read") or {}, g(F, "fed", "read") or {}
    keys = ("done", "pairs", "ghostMs", "realMs", "ghostMeanMs", "realMeanMs", "ratio", "ghostFailures",
            "realFailures", "lastError", "ghostZeroDt", "realZeroDt", "waits", "minuteEvents", "suppressed", "syncs",
            "bodySyncs", "reason", "wallSpan")
    S["F"] = {"unfed": {k: fu.get(k) for k in keys}, "fed": {k: ff.get(k) for k in keys}}
    if fu.get("done") is True and ff.get("done") is True:
        clean = all(d.get("ghostZeroDt") == 0 and d.get("realZeroDt") == 0 and d.get("ghostFailures") == 0
                    and d.get("realFailures") == 0 and d.get("reason") is None for d in (fu, ff))
        fr = num(ff.get("ratio"))
        ok = clean and fr is not None and FED_BAND[0] <= fr <= FED_BAND[1]
        grade("F", PRED["F"], S["F"], "as_predicted" if ok else "falsified", "a zero dt, a failure, a reason, or the fed "
              "ratio outside 0.8..1.25")
    else:
        grade("F", PRED["F"], S["F"], "unmeasured", "a bench did not finish")

    # E
    E = ph.get("E") or {}
    e1 = {}
    for n, row in (E.get("E1") or {}).items():
        saves = []
        for s in row.get("saves") or []:
            ev = event_frames(s.get("ring_doc"), g(s, "save", "epoch_ms_before"))
            ln = save_lines(g(s, "log", "lines"))
            saves.append({"k": s.get("k"), "frames": ev, "log": ln, "bin": s.get("bin"),
                          "perf_max": g(s, "perf_read", "max")})
        e1[n] = {"seed": {k: g(row, "seed", k) for k in ("r1", "r2", "ok", "err")}, "saves": saves}
    e2 = {}
    for t, row in (E.get("E2") or {}).items():
        rq = row.get("req") or {}
        ev = event_frames(rq.get("ring_doc"), g(rq, "request", "epoch_ms_before"), 500, 8000)
        ln = save_lines(g(rq, "log", "lines"))
        n0, n1 = num(g(rq, "rx_before", "n")), num(g(rq, "rx_after", "n"))
        e2[t] = {"seed": {k: g(row, "seed", k) for k in ("r1", "r2", "ok", "err")}, "frames": ev, "log": ln,
                 "rx_after": rq.get("rx_after"), "arrived": (n1 is not None and n0 is not None and n1 > n0),
                 "request": {k: (rq.get("request") or {}).get(k) for k in ("ok", "r1", "r2", "err")},
                 "console": (rq.get("console") or {}).get("lines")}
    S["E"] = {"E1": e1, "E2": e2}
    try:
        def gmd(n, k):
            return e1[str(n)]["saves"][k - 1]["log"]["gmd_ms"]

        def binb(n, k):
            b = e1[str(n)]["saves"][k - 1]["bin"] or {}
            return next(iter(b.values())) if b else None

        add500 = (gmd(500, 2) - gmd(0, 2)) if None not in (gmd(500, 2), gmd(0, 2)) else None
        per = {}
        for n in (100, 500, 2000):
            b0, bn = binb(0, 2), binb(n, 2)
            per[n] = ((bn - b0) / n / 10821.833333333334) if None not in (b0, bn) else None
        S["E"]["gmd_add_500_vs_0"] = add500
        S["E"]["bin_per_record_over_model"] = per
        okb = all(v is not None and BIN_BAND[0] <= v <= BIN_BAND[1] for v in per.values())
        grade("E1", PRED["E1"], {"gmd_add_500_vs_0": add500, "bin_per_record_over_model": per,
                                 "gmd_ms": {n: [gmd(n, 1), gmd(n, 2)] for n in SAVE_SEEDS}},
              "unmeasured" if add500 is None else ("as_predicted" if add500 > SAVE_ADD_MS and okb else "falsified"),
              "the second save at 500 adds 25 ms or less, or the file's growth off the model")
    except (KeyError, IndexError, TypeError) as e:
        grade("E1", PRED["E1"], {"error": f"{type(e).__name__}: {e}"}, "unmeasured", "an E1 reading missing")
    try:
        r2, r60, r500 = e2["2"], e2["60"], e2["500"]
        ok2 = r2["arrived"] and g(r2, "rx_after", "isTable") is True and num(g(r2, "rx_after", "keys")) == 2
        ok60 = r60["arrived"] and g(r60, "rx_after", "isTable") is True and num(g(r60, "rx_after", "keys")) == 60
        ok500 = (not r500["arrived"]) and r500["log"]["exceptions"] > 0
        req60 = g(r60, "frames", "over_median_period")
        grade("E2", PRED["E2"], {"2": {"arrived": r2["arrived"], "rx": r2["rx_after"]},
                                 "60": {"arrived": r60["arrived"], "rx": r60["rx_after"], "frame_over_median": req60},
                                 "500": {"arrived": r500["arrived"], "exceptions": r500["log"]["exceptions"]}},
              "as_predicted" if ok2 and ok60 and ok500 and req60 is not None and req60 > REQ_MS else "falsified",
              "a table missing at 2 or 60, an event or no exception at 500, or the request at 60 within 5 ms")
    except (KeyError, TypeError) as e:
        grade("E2", PRED["E2"], {"error": f"{type(e).__name__}: {e}"}, "unmeasured", "an E2 reading missing")

    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [], "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
# x242's phase A pooled in-play minute (C1's comparison), from its committed artifact
try:
    _accA = merge_acc(((_x242.get("phases") or {}).get("A") or {}).get("acc"))
    _pa = shares(pool([_accA.get(f"u:{u}", {}) for u in USERS]))
    out["meta"]["x242_A"] = {"artifact": X242_ARTIFACT, "run_ms": _pa["run_ms"], "run_runs": _pa["run_runs"],
                             "run_ms_per_run": _pa["run_ms_per_run"]}
except Exception as e:                         # noqa: BLE001 - C1 is then unmeasured
    out["meta"]["x242_A"] = {"error": f"{type(e).__name__}: {e}"}
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if not all(v.get("equal") for v in (out["meta"].get("instrument_sha256") or {}).values()) or \
        len(out["meta"].get("instrument_sha256") or {}) != len(INSTR) or \
        out["meta"].get("staged_manifest_sha256") != MANIFEST_SHA256:
    out["error"] = ("a staged instrument file differs from its kept copy or from x242's, or the MANIFEST differs; the "
                    "session was not started")
    persist()
    print(json.dumps(out["meta"].get("instrument_sha256"), indent=1))
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
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "NutritionRevamp", "**", "NR_Server_Bench.lua"),
                                 recursive=True)):
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
