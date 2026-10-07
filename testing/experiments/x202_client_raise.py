"""x202-client-raise -- Plan 9 Task 5, live 2: X23, the RELEASE client's unguarded raise. ONE boot of profile
`x20-raise` on fixture `two` with TWO clients: `admin` (-debug) and `bob` (a RELEASE client, no -debug: fixture two's
record `clients.bob.debug = false`), attached one at a time through pzt.session.attach_clients (each ready before the
next launches). PZTestKit + the STAGED 1.0.0 build (release/NutritionRevamp/Contents/mods/NutritionRevamp, as x201)
+ TKX_ClientRaise (testing/experiments/TKX_ClientRaise, a client/ file: a custom event TKX_ClientRaise with H0
`before` ++, H1 an UNGUARDED `TKX_DefinitelyNilClient()` then `raw_tail` ++, H2 `behind` ++; the two flags read once
at OnGameStart). Nutrition false; DayLength 1. ONE artifact `raise.json`. Shape: x201_release.py (step, keep, gread,
persist, run_phase, grade, the echo-excluding log greps, make_server + attach_clients, the artifact copied by the
driver). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2). A two-client run is one session.

A RAISING PROBE (CLAUDE.md s5, lessons.md#rules, #1963): the profile's one [[verify]] row is on the SERVER; its
[client] timeout is 60; `pzt run` on it is expected to fail (the -debug admin parks), so this driver runs the session
itself and the grade comes off the artifact. The raise happens only when the harness fires the event, after both
clients are ready, so the attach wait never meets a raise; the driver passes ATTACH_TIMEOUT (x201's 180 s: x201's
clients took 38.3 s and 40.8 s launch-to-ready) to attach_clients rather than the profile's 60 s, so a slow join is
not mistaken for the probe's effect (a deviation, recorded in `deviations`).

THE JAR READING UNDER TEST (desk read, pz.sh dump, build 42.20.4): KahluaUtil.fail(String) @0-@12 L95 reads the
static Core.debug and, when set and on the Lua thread, prints the stack (L96) and calls UIManager.debugBreakpoint
(@50 L97) before throwing the RuntimeException at @53-@61 L100; debugBreakpoint @0-@6 L1173-L1174 returns at once
unless the static UIManager.showLuaDebuggerOnError, whose only writer is setShowLuaDebuggerOnError (@0-@1 L1165),
called by GameWindow.enter @271-@278 L772-L773 (true, right after OnGameBoot) and by GameWindow.frameStep L835-L838
(the debug-only 'Toggle Lua Debugger' key) and vanilla's DebugToolstrip.lua:29. So the flag the release client
lacks is Core.debug, not showLuaDebuggerOnError; the probe reads both (Core.getDebug()Z @0 L737 returns Core.debug).

READ ORDER: bob first, admin second, the server third. Every bus reply's status is recorded per read (a timeout is a
reading: the client stopped answering).

PHASES:
  A  liveness and the flags, before any raise: on bob then admin, lua.global TKX_CR.version (the file ran),
     TKX_CR.registered (the custom event registered), TKX_CR.debugFlag, TKX_CR.showFlag, and the three counters'
     baseline; lua.call UIManager.isShowLuaDebuggerOnError on each (a second read of the same static, at read time);
     the server's players list and its NutritionRevamp.version.
  B  the release client's raise: bob's console and the server log sized (byte offsets) first; `event.trigger
     TKX_ClientRaise` on client:bob (reply recorded); then TKX_CR.before / raw_tail / behind read on bob in rounds
     started every ROUND_S (2 s) for B_WINDOW_S (30 s), each read with B_READ_TIMEOUT (10 s) and its status recorded;
     then the server's players list; bob's console after the offset: the last TAIL_N (40) non-echo lines, every line
     matching FLAG_RX (ERROR, STACK, LuaDebugger, fail, tried to call, Exception, LuaError) quoted, the echo lines
     counted; the server log after its offset, the echo lines and the lines naming the probe (PROBE_RX) dropped.
  C  the -debug control: admin's console sized; the SAME trigger on client:admin with C_TIMEOUT (10 s); then
     C_ROUNDS (3) rounds of the three counters on admin, each read with C_TIMEOUT; admin's lua_error marker; admin's
     console after the offset (tail and flagged lines as in B). A parked debugger is the expected reading; nothing
     tries to un-park it.
  D  bob's connection after both: D_WAIT_S (30 s) after C ends, the server's players list again; bob's version and
     three counters read once more; bob's process alive; bob's `kicked` and `lua_error` markers.

PREDICTIONS (graded in `verdicts`, as_predicted / falsified / unmeasured):
  A        version 1 on bob and admin; registered "true" on both; counters "0","0","0" on both.
  X23      (bob, the release client) the trigger reply ok; every post-trigger read answered; before "1", raw_tail "0",
           behind "1" (the raise aborted H1's body, H2 ran, no park); bob in the players list after B and in D;
           bob's process alive in D; no `kicked` marker. Falsified: raw_tail "1" (the body was not aborted), behind
           "0" (the chain behind stopped), a read that times out (the client stopped answering), bob absent from the
           list. Unmeasured: bob never answered phase A.
  X23_admin (the -debug control, #1963 on a second mod shape) the trigger reply times out or every post-trigger read
           times out, and admin's `lua_error` marker is seen: the debug client parked. Falsified: admin answers
           after the trigger.
  X23_flags debugFlag "false" on bob and "true" on admin; showFlag "true" on both (set after OnGameBoot on every
           client, per the jar reading above). Recorded per side; a flag "unset" is unmeasured for that side.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. The admin
client the harness launched is torn down by the harness's own teardown (quit, then kill on timeout) -- the one kill
allowed; a ProjectZomboid64.exe predating the session is never touched.
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
from pzt.session import (Timeline, attach_clients,              # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x20-raise"
PREFIX = "x202"
SESSION = ("Plan 9 Task 5, live 2: X23 -- a custom client event whose middle handler raises unguarded, fired on the "
           "release client bob and then on the -debug admin; bob's counters, bus replies, connection and console; "
           "the debug and debugger-on-error flags per side; one boot of " + PROFILE)
ARTIFACT = "raise.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
PROBE_DIR = "testing/experiments/TKX_ClientRaise"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
EVENT = "TKX_ClientRaise"
COUNTERS = ("before", "raw_tail", "behind")
ATTACH_TIMEOUT = 180
ROUND_S = 2.0
B_WINDOW_S = 30.0
B_READ_TIMEOUT = 10
B_TRIGGER_TIMEOUT = 20
C_TIMEOUT = 10
C_ROUNDS = 3
D_WAIT_S = 30.0
TAIL_N = 40
FLAG_RX = re.compile(r"ERROR|STACK|LuaDebugger|fail|tried to call|Exception|LuaError", re.I)
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
PROBE_RX = re.compile(r"TKX_ClientRaise|TKX_CR|TKX_DefinitelyNilClient")   # the driver's own probe names
LINE_CAP = 600

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
    "A": {"version": {"bob": 1, "admin": 1}, "registered": {"bob": "true", "admin": "true"},
          "counters": {"bob": ["0", "0", "0"], "admin": ["0", "0", "0"]}},
    "X23": {"trigger_ok": True, "post_trigger_reads": "all answered", "before": "1", "raw_tail": "0", "behind": "1",
            "bob_in_players_after_B": True, "bob_in_players_D": True, "bob_alive_D": True, "bob_kicked": False},
    "X23_admin": {"parked": True, "trigger_or_reads": "time out", "lua_error_marker": True},
    "X23_flags": {"debugFlag": {"bob": "false", "admin": "true"}, "showFlag": {"bob": "true", "admin": "true"}},
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
    "mod_dirty": git_dirty(MOD_DIR)[0],
    "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
    "probe_dirty": git_dirty(PROBE_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "attach_clients is passed ATTACH_TIMEOUT (180 s, x201's) rather than the profile's [client] timeout of 60 s: "
        "the raise happens only when the driver fires the event after both clients are ready, so the low timeout "
        "(which protects `pzt run` from a parked client) has nothing to guard during the attach.",
        "Phase A also reads UIManager.isShowLuaDebuggerOnError through lua.call on each client (a read of a static "
        "getter, never the setter), beside the probe's own OnGameStart read.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}


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


def status(a):
    """`answered`, `timeout` or `error` for one reply."""
    if not isinstance(a, dict):
        return "answered" if a is not None else "error"
    e = a.get("error")
    if isinstance(e, str) and e.startswith("TimeoutError"):
        return "timeout"
    if isinstance(e, str) and (e.startswith("RuntimeError") or e.startswith("OSError")
                               or e.startswith("PermissionError")):
        return "error"
    return "answered"


def gread(side, name, tag, timeout=30):
    r = step(tag, side, "lua.global", name, timeout=timeout)
    a = ack(r)
    row = {"name": name, "side": side, "wall": r["wall_before"], "wall_after": r["wall_after"],
           "took": r["took"], "status": status(r.get("ack")), "resolved": a.get("resolved"), "type": a.get("type")}
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


def who(side):
    return side.split(":", 1)[1] if side.startswith("client:") else side


def client_of(side):
    return clients.get(who(side)) if isinstance(clients, dict) else None


def seen_of(side):
    c = client_of(side)
    return dict(getattr(c, "seen", {})) if c is not None else {}


def size_of(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return None


def read_after(p, offset):
    """The lines of p after a byte offset (the whole file when the offset is unknown or past the end)."""
    try:
        with open(p, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if offset is not None and offset <= len(data):
        data = data[offset:]
    return data.decode("utf-8", errors="replace").splitlines()


def tail_block(lines, drop_probe=False):
    """The last TAIL_N non-echo lines, every flagged non-echo line, the echo count; probe lines dropped when asked."""
    if lines is None:
        return {"read": False}
    kept, echo, probe = [], 0, 0
    for ln in lines:
        if ECHO_RX.search(ln):
            echo += 1
            continue
        if drop_probe and PROBE_RX.search(ln):
            probe += 1
            continue
        kept.append(ln.rstrip()[:LINE_CAP])
    flagged = [ln for ln in kept if FLAG_RX.search(ln)]
    return {"read": True, "line_count": len(lines), "echo_lines_excluded": echo, "probe_lines_excluded": probe,
            "tail": kept[-TAIL_N:], "flagged": flagged[:TAIL_N], "flagged_count": len(flagged)}


def players():
    r = step(f"{cur_phase['name']}_players", SRV, "players")
    a = r.get("ack")
    names = a if isinstance(a, list) else None
    return {"wall": r["wall_before"], "raw": a, "names": names,
            "has": {u: (isinstance(names, list) and u in names) or (f'"{u}"' in json.dumps(a)) for u in ("admin", "bob")}}


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


def counters(side, tag, timeout):
    return {k: gread(side, f"TKX_CR.{k}", f"{tag}_{k}", timeout=timeout) for k in COUNTERS}


# ---------------------------------------------------------------- phases
def phase_A():
    P = out["phases"]["A"] = {}
    for side in CLIENT_SIDES:
        u = who(side)
        P[u] = {"version": gread(side, "TKX_CR.version", f"A_{u}_version"),
                "registered": gread(side, "TKX_CR.registered", f"A_{u}_registered"),
                "debugFlag": gread(side, "TKX_CR.debugFlag", f"A_{u}_debugFlag"),
                "showFlag": gread(side, "TKX_CR.showFlag", f"A_{u}_showFlag"),
                "counters": counters(side, f"A_{u}", 30),
                "show_call": keep(step(f"A_{u}_show_call", side, "lua.call", "UIManager.isShowLuaDebuggerOnError")),
                "seen": seen_of(side)}
    P["players"] = players()
    P["server_version"] = gread(SRV, "NutritionRevamp.version", "A_srv_version")


def phase_B():
    P = out["phases"]["B"] = {}
    bob = client_of(BOB)
    P["console_offset"] = size_of(bob.console) if bob is not None else None
    P["server_log_offset"] = size_of(server.log_path) if server is not None else None
    P["seen_before"] = seen_of(BOB)
    trig = step("B_bob_trigger", BOB, "event.trigger", EVENT, timeout=B_TRIGGER_TIMEOUT)
    P["trigger"] = keep(trig)
    P["trigger_status"] = status(trig.get("ack"))
    P["trigger_wall"] = trig["wall_before"]
    rounds, start = [], time.time()
    while time.time() - start < B_WINDOW_S:
        r0 = time.time()
        rounds.append({"t_since_trigger": round(r0 - start, 3),
                       "reads": counters(BOB, f"B_bob_r{len(rounds)}", B_READ_TIMEOUT)})
        persist()
        rest = ROUND_S - (time.time() - r0)
        if rest > 0:
            time.sleep(rest)
    P["rounds"] = rounds
    P["players"] = players()
    P["seen_after"] = seen_of(BOB)
    P["bob_alive"] = bool(getattr(bob, "alive", False)) if bob is not None else None
    P["console"] = tail_block(read_after(bob.console, P["console_offset"])) if bob is not None else {"read": False}
    P["server_log"] = (tail_block(read_after(server.log_path, P["server_log_offset"]), drop_probe=True)
                       if server is not None else {"read": False})


def phase_C():
    P = out["phases"]["C"] = {}
    adm = client_of(ADMIN)
    P["console_offset"] = size_of(adm.console) if adm is not None else None
    P["seen_before"] = seen_of(ADMIN)
    trig = step("C_admin_trigger", ADMIN, "event.trigger", EVENT, timeout=C_TIMEOUT)
    P["trigger"] = keep(trig)
    P["trigger_status"] = status(trig.get("ack"))
    rounds = []
    for i in range(C_ROUNDS):
        rounds.append({"round": i, "reads": counters(ADMIN, f"C_admin_r{i}", C_TIMEOUT)})
        persist()
    P["rounds"] = rounds
    P["seen_after"] = seen_of(ADMIN)
    P["admin_alive"] = bool(getattr(adm, "alive", False)) if adm is not None else None
    P["console"] = tail_block(read_after(adm.console, P["console_offset"])) if adm is not None else {"read": False}


def phase_D():
    P = out["phases"]["D"] = {}
    time.sleep(D_WAIT_S)
    P["waited_s"] = D_WAIT_S
    P["players"] = players()
    P["version"] = gread(BOB, "TKX_CR.version", "D_bob_version")
    P["counters"] = counters(BOB, "D_bob", B_READ_TIMEOUT)
    bob = client_of(BOB)
    P["bob_alive"] = bool(getattr(bob, "alive", False)) if bob is not None else None
    P["seen"] = seen_of(BOB)
    P["console_since_B"] = (tail_block(read_after(bob.console, out["phases"].get("B", {}).get("console_offset")))
                            if bob is not None else {"read": False})


def body():
    for name, fn in (("A", phase_A), ("B", phase_B), ("C", phase_C), ("D", phase_D)):
        run_phase(name, fn)


# ---------------------------------------------------------------- grading
def leaf(v):
    return v if isinstance(v, (str, int, float, bool)) or v is None else json.dumps(v, default=str)[:300]


def grade_all():
    ph = out["phases"]
    A = ph.get("A") or {}
    a_ok = {}
    if A:
        obs = {}
        for u in ("bob", "admin"):
            Au = A.get(u) or {}
            obs[f"{u}_version"] = leaf(val(Au.get("version")))
            obs[f"{u}_registered"] = leaf(val(Au.get("registered")))
            for k in COUNTERS:
                obs[f"{u}_{k}"] = leaf(val((Au.get("counters") or {}).get(k)))
            a_ok[u] = val(Au.get("version")) == 1
        ok = (all(a_ok.values()) and all(obs[f"{u}_registered"] == "true" for u in ("bob", "admin"))
              and all(obs[f"{u}_{k}"] == "0" for u in ("bob", "admin") for k in COUNTERS))
        grade("A", PRED["A"], obs, "as_predicted" if ok else ("unmeasured" if not any(a_ok.values()) else "falsified"),
              "a client whose version does not answer, the event unregistered, a counter already moved")
    else:
        grade("A", PRED["A"], None, "unmeasured", "phase A not run")

    B, D = ph.get("B") or {}, ph.get("D") or {}
    if not a_ok.get("bob"):
        grade("X23", PRED["X23"], {"bob_answered_A": False}, "unmeasured",
              "bob never answered phase A: the release client's outcome cannot be read")
    elif not B:
        grade("X23", PRED["X23"], None, "unmeasured", "phase B not run")
    else:
        reads = [rd for rnd in (B.get("rounds") or []) for rd in (rnd.get("reads") or {}).values()]
        n_ans = sum(1 for rd in reads if rd.get("status") == "answered" and rd.get("resolved"))
        n_to = sum(1 for rd in reads if rd.get("status") == "timeout")
        last = {}
        for rnd in (B.get("rounds") or []):
            for k, rd in (rnd.get("reads") or {}).items():
                if rd.get("status") == "answered" and rd.get("resolved"):
                    last[k] = rd.get("value")
        values_seen = {k: sorted({str(rd.get("value")) for rnd in (B.get("rounds") or [])
                                  for kk, rd in (rnd.get("reads") or {}).items()
                                  if kk == k and rd.get("status") == "answered" and rd.get("resolved")})
                       for k in COUNTERS}
        Dc = D.get("counters") or {}
        obs = {"trigger_status": B.get("trigger_status"), "trigger_ok": leaf((B.get("trigger") or {}).get("ok")),
               "trigger_err": leaf((B.get("trigger") or {}).get("err")),
               "rounds": len(B.get("rounds") or []), "reads_total": len(reads), "reads_answered": n_ans,
               "reads_timed_out": n_to,
               "before_last": leaf(last.get("before")), "raw_tail_last": leaf(last.get("raw_tail")),
               "behind_last": leaf(last.get("behind")),
               "before_values": leaf(values_seen["before"]), "raw_tail_values": leaf(values_seen["raw_tail"]),
               "behind_values": leaf(values_seen["behind"]),
               "bob_in_players_after_B": leaf(((B.get("players") or {}).get("has") or {}).get("bob")),
               "bob_alive_after_B": leaf(B.get("bob_alive")),
               "console_flagged_count": leaf((B.get("console") or {}).get("flagged_count")),
               "bob_lua_error_marker": "lua_error" in (B.get("seen_after") or {}),
               "bob_kicked_marker": "kicked" in (D.get("seen") or B.get("seen_after") or {}),
               "bob_in_players_D": leaf(((D.get("players") or {}).get("has") or {}).get("bob")),
               "bob_alive_D": leaf(D.get("bob_alive")),
               "D_version": leaf(val(D.get("version"))),
               "D_before": leaf(val(Dc.get("before"))), "D_raw_tail": leaf(val(Dc.get("raw_tail"))),
               "D_behind": leaf(val(Dc.get("behind")))}
        if n_ans == 0 and n_to == 0:
            verdict = "unmeasured"
        else:
            ok = (obs["trigger_status"] == "answered" and obs["trigger_ok"] is True and n_ans == len(reads)
                  and values_seen["before"] == ["1"] and values_seen["raw_tail"] == ["0"]
                  and values_seen["behind"] == ["1"] and obs["bob_in_players_after_B"] is True
                  and obs["bob_in_players_D"] is True and obs["bob_alive_D"] is True and not obs["bob_kicked_marker"])
            verdict = "as_predicted" if ok else "falsified"
        grade("X23", PRED["X23"], obs, verdict,
              "raw_tail 1 (body not aborted), behind 0 (chain stopped), a read timing out (bob stopped answering), "
              "bob absent from the players list or dead")

    C = ph.get("C") or {}
    if not a_ok.get("admin"):
        grade("X23_admin", PRED["X23_admin"], {"admin_answered_A": False}, "unmeasured", "admin never answered A")
    elif not C:
        grade("X23_admin", PRED["X23_admin"], None, "unmeasured", "phase C not run")
    else:
        reads = [rd for rnd in (C.get("rounds") or []) for rd in (rnd.get("reads") or {}).values()]
        n_ans = sum(1 for rd in reads if rd.get("status") == "answered" and rd.get("resolved"))
        n_to = sum(1 for rd in reads if rd.get("status") == "timeout")
        last = {}
        for rnd in (C.get("rounds") or []):
            for k, rd in (rnd.get("reads") or {}).items():
                if rd.get("status") == "answered" and rd.get("resolved"):
                    last[k] = rd.get("value")
        obs = {"trigger_status": C.get("trigger_status"), "reads_total": len(reads), "reads_answered": n_ans,
               "reads_timed_out": n_to, "before_last": leaf(last.get("before")),
               "raw_tail_last": leaf(last.get("raw_tail")), "behind_last": leaf(last.get("behind")),
               "lua_error_marker_before": "lua_error" in (C.get("seen_before") or {}),
               "lua_error_marker_after": "lua_error" in (C.get("seen_after") or {}),
               "admin_alive": leaf(C.get("admin_alive")),
               "console_flagged_count": leaf((C.get("console") or {}).get("flagged_count"))}
        parked = (obs["trigger_status"] == "timeout" or (n_ans == 0 and n_to > 0)) and obs["lua_error_marker_after"]
        answered_after = obs["trigger_status"] == "answered" and n_ans > 0
        verdict = "as_predicted" if parked else ("falsified" if answered_after else "unmeasured")
        grade("X23_admin", PRED["X23_admin"], obs, verdict, "admin answering after the trigger")

    if A:
        obs = {}
        for u in ("bob", "admin"):
            Au = A.get(u) or {}
            obs[f"{u}_debugFlag"] = leaf(val(Au.get("debugFlag")))
            obs[f"{u}_showFlag"] = leaf(val(Au.get("showFlag")))
            sc = Au.get("show_call") or {}
            obs[f"{u}_show_call_r1"] = leaf(sc.get("r1"))
            obs[f"{u}_show_call_ok"] = leaf(sc.get("ok"))
        vals = [obs[f"{u}_{f}"] for u in ("bob", "admin") for f in ("debugFlag", "showFlag")]
        if all(v in (None, "unset") for v in vals):
            verdict = "unmeasured"
        else:
            ok = (obs["bob_debugFlag"] == "false" and obs["admin_debugFlag"] == "true"
                  and obs["bob_showFlag"] == "true" and obs["admin_showFlag"] == "true")
            verdict = "as_predicted" if ok else "falsified"
        grade("X23_flags", PRED["X23_flags"], obs, verdict, "a debug flag true on bob, a show flag false on a client")
    else:
        grade("X23_flags", PRED["X23_flags"], None, "unmeasured", "phase A not run")


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if out["mod_dirty"] or out["probe_dirty"]:
    out["error"] = "mod/ or the probe not quiescent (git status --short not empty); the session was not started"
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
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started, timeout=ATTACH_TIMEOUT)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                   "client_markers_s": {u: dict(getattr(c, "seen", {})) for u, c in clients.items()},
                   "client_debug": {u: getattr(c, "debug", None) for u, c in clients.items()},
                   "server_started_wall": out.get("server_started_wall"),
                   "session_ready_wall": out.get("session_ready_wall")}
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
            teardown(tl, server, every)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, every)
        out["client_seen"] = {getattr(c, "username", str(i)): dict(getattr(c, "seen", {})) for i, c in enumerate(every)}
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
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
                  "error": out.get("error"), "body_error": out.get("body_error"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
