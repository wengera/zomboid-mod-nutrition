"""x193-two-clients -- Plan 8 Task 7, live 3, ONE boot of profile `x19-two` on fixture `two` with TWO clients: `admin`
(-debug) and `bob` (a RELEASE client, no -debug: fixture two's record `clients.bob.debug = false`), attached one at a
time through pzt.session.attach_clients (each ready before the next launches). PZTestKit + NutritionRevamp (by path) +
TKX_DeclaredFood; Nutrition false; DayLength 1 (a game-minute = 0.625 s wall); no [sandbox.NR] block (the Bands
default). ONE artifact `two.json`. Shape: x191_gate_race.py (step, keep, gread, persist, run_phase, mod_error, the
echo-excluding log greps, the artifact copied by the driver), with every side named through pzt.bus.resolve_side
(`server`, `client:bob`, `client:admin`). Written BEFORE the boot with every prediction in it and never edited after the
run (CLAUDE.md s5, B3-1/B3-2). A two-client run is one session (ruling 16).

BUILD UNDER TEST (Task 7 build block): HEAD 81b244d, mod/ quiescent at 0df50bb (Task 3's kernels at 1cf2a44 + bbfa4cc,
Task 4's adapters at 2d4dc4d + 0df50bb: NR_Server_Reconcile.lua, the band mark, the store's in-place load); the harness
Lua at 0ff30f4 (event.trigger, lua.callm); Task 1's fixture two and the named-client driver side at 3ce7119.

READ ORDER: every paired read is `client:bob` first, `client:admin` second, the server third (the amendments' fixed
order); an arm whose reading is server-only says so.

ARMS (the order run is S0, A, B, E, C, D, F, G, Z -- see deviations):
  S0 the load: the ready times (timeline client_ready marks); on bob, then admin: TK.version, NutritionRevamp.version,
     the mirror's username, received, view.level, view.hasTrait, NR_ClientTooltip_Installed.original,
     lua.call isDebugEnabled / getDebug / getLuaDebuggerErrorCount, the panel stats; on the server: NutritionRevamp
     .version, the players list, both records' v and reconcile.count (lua.global on the store's cache), one
     witness.moddata census of the global table, the store and reconcile stats; the mod-error check.
  A  the forced deficiency on bob (route: the mirror's recipient, #2603): before -- bob's and admin's received,
     nut_vitC_g and username, the server's bus.effects.stats.pushes and both records' vitC g/p; the server's
     globalmoddata.setpath NutritionRevamp players bob.nutrients.vitC.p 0.05; WAIT_A_S; the records' vitC g/p; then
     bob's received polled (POLL_A_S steps, cap PUSH_CAP_S: the effects push is held to one per player per 60 s of
     server wall clock, PUSH_GAP_MS, and bob's last push may be recent); at the arrival: bob's nut_vitC_g, username,
     received; admin's nut_vitC_g, username, received; the server's pushes. If the cap passes with no arrival the push
     is graded falsified and bob pulls one mirror (requestMirror) so the recipient half is still read (stated).
  B  the global table on no client (#2416, #2398): on bob then admin, lua.call ModData.exists NutritionRevamp.players
     (a non-creating read, FIRST) and then witness.moddata global:NutritionRevamp.players bob admin (the harness's
     census calls ModData.getOrCreate, which CREATES an empty local table when absent: an empty census, keyCount 0, is
     the miss); on the server the same two reads with bob.username admin.username.
  E  bob's panel: before -- bob's panel stats and received, admin's panel stats; event.trigger OnKeyPressed 39 on
     client:bob; bob's received polled (cap POLL_CAP_S); after -- bob's panel stats, the panel's getIsVisible
     (lua.callm NutritionRevamp.client.panel.instances.0), the view's level, its six class levels (view.classes.<cls>,
     string keys), the rows' key count, and the deficiency row's text key (rows[3].text: a numeric index lua.global
     cannot take, so it is read through client lua.setpath's `before` -- a write of 0 and at once the read value
     written back, x191's read), the mirror's username; admin's panel stats and class levels; the server's bob vitC.g.
     A second press on bob closes the panel (keyPresses 2, closes 1, getIsVisible false).
  C  the trait push to its owner (#2603, #2759): before -- the known-trait list sizes on bob's client, admin's client,
     and the server's copies of bob and admin (witness.chain getCharacterTraits.getKnownTraits.size); the server's
     trait.add.push bob NUTRITIONIST; then READ_S of reads, each round bob's size, admin's size, the server's bob
     size; bob pulls one mirror; at its arrival bob's view.hasTrait and view.level, admin's view.hasTrait, view.level
     and received. Admin's client copy of bob: the harness's client-side subjects are the local player only (subjectOf
     in PZTestKit_Core.lua returns getPlayer() on a client; witness.chain reads the local player), so it is UNREADABLE
     and the arm states so: the not-on-admin half rests on admin's own list and view, plus #2603's code reading.
  D  reconciliation (ruling 6; a server-only arm): before -- one census of bob's record (reconcile, lastIntake,
     stomach.buffer, nutrients: one witness.moddata call, one snapshot), nutrition.get bob (the four vanilla stores),
     the reconcile stats, admin's reconcile.count; the server's nutrition.set bob calories <before + RISE_KCAL> (the
     vanilla calorie store raised by another writer, no eat); bob's reconcile.count polled back to back (cap
     LAND_CAP_S); at the landing one census of bob's record again, nutrition.get bob, the reconcile and kinetics stats,
     admin's count; FOLLOW_S later the census again (the count still 1: no double landing after the legacy mirror's
     write rebased the baseline) and the stats.
  F  the release client: on bob then admin, lua.global TK.version and NutritionRevamp.version (the harness's file bus,
     not the debugger), lua.call isDebugEnabled / getDebug (Core.debug, and the server-debug fallback) and
     getLuaDebuggerErrorCount (KahluaThread.errorCount); NR_ClientTooltip_Installed.original; the client markers each
     Client object saw.
  G  tick.rate TICK_S x TICK_N, the server, bob and admin armed in the same windows, against x183b's server ticks.
  Z  the counters again on bob, admin and the server; both records' reconcile.count; the mod-error check.
  After teardown: the server log and both client consoles grepped with the bus's `PZTK: ` echo lines dropped first
  (CLAUDE.md s5): the mod's [NutritionRevamp] lines, the first-sight lines, `reconcile:` lines, Lua error markers.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  S0  server_error_count 0; admin no lua_error marker; both ready; bob's mirror username "bob", admin's "admin";
      received >= 1 on each; view.level 2 on each; bob's NR_ClientTooltip_Installed.original type function; bob
      isDebugEnabled false, admin true; getLuaDebuggerErrorCount 0 on each; both records v 2 and reconcile.count 0;
      the census holds admin and bob; store failures 0; reconcile errors 0; a `players: first sight of` line for each.
  A   setpath ok (after 0.05); bob's record vitC.g 4 after WAIT_A_S; admin's vitC.g 1; bob's received rises within
      PUSH_CAP_S with pushes +1 or more; at the arrival bob's nut_vitC_g 4 and username bob; admin's nut_vitC_g 1 and
      username admin, admin's received unchanged across the arm.
  B   ModData.exists false on bob and on admin; each client's census keyCount 0 with bob and admin missing; the server's
      exists true and its census keyCount >= 2 with both usernames read.
  E   event.trigger ok; bob keyPresses 0 -> 1, opens 0 -> 1, requests +1, getIsVisible true, received +1 within
      POLL_CAP_S; view.level 2; classes.deficiency 3 (nut_vitC_g 4 -> g - 1); rows[3].text
      "UI_NR_Class_deficiency_3"; admin's opens 0 and classes.deficiency 0; the second press: keyPresses 2, closes 1,
      getIsVisible false; panel errors 0 on both.
  C   the reply's traitList holds nutritionist; bob's client size +1 at its first read after the push; admin's own
      size unchanged; the server's bob size +1, admin's unchanged; at bob's pulled mirror hasTrait true and level 3;
      admin's hasTrait false and level 2. Admin's copy of bob: unreadable (stated).
  D   bob's reconcile.count 0 -> 1 within LAND_CAP_S; lastIntake.source "reconciled" with the kernel's note;
      lastIntake.calories about RISE_KCAL (within 10 kcal: the legacy write may move the store between the read and
      the set) and carbs, lipids, proteins 0; the stomach buffer's calories up by more than 450 (one minute's emptying
      at a 2 h half-time takes about 0.6 % of the buffer); no non-macro buffer key rose; no nutrients.*.p rose on bob that did not
      also rise on admin over the same window (an endogenous source moves both; the intake only bob's);
      reconcile.stats.landed +1; admin's count 0; FOLLOW_S later bob's count still 1 and landed unchanged. The vanilla
      store after the landing is recorded, not graded (the legacy mirror rewrites it every minute).
  F   bob: TK.version 1 and NutritionRevamp.version resolved over the bus; isDebugEnabled false and getDebug false;
      getLuaDebuggerErrorCount 0; the tooltip sentinel's original a function. admin: isDebugEnabled true.
  G   server ticks per second within 0.5/s of x183b's (10.003, 10.053, 10.002); both clients > 0.
  Z   mod_error none; admin reconcile.count 0, bob 1; store failures 0.
A parked -debug admin (the lua_error marker) stops the remaining arms; bob cannot park (no debugger).

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
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients,              # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x19-two"
PREFIX = "x193"
SESSION = ("Plan 8 Task 7, live 3: two clients on one server -- each mirror its own, a forced deficiency on bob, the "
           "global table on no client, the trait push to its owner, a server-side calorie rise reconciled, bob's panel, "
           "the release client, the tick rate; one boot of " + PROFILE)
ARTIFACT = "two.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)                     # the fixed read order: bob, admin, then the server
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
STORE = "NutritionRevamp.players"
NR = "NutritionRevamp"
REC = "NutritionRevamp.server.store.records"
INST = "NutritionRevamp.client.panel.instances.0"
TRAIT = "NUTRITIONIST"
CHAIN_SIZE = "getCharacterTraits.getKnownTraits.size"
CHAIN_LIST = "getCharacterTraits.getKnownTraits"
X183B_RUN = "x183b-20261006-175149"
X183B_TICKS = (10.003483800328473, 10.052752065293122, 10.002488181139586)  # interface.json verdicts.H.observed.server_tps
KEY = 39                                   # Keyboard.KEY_SEMICOLON, the panel's default bind (ruling T5-1)
VITC_P = 0.05                              # arm A's forced pool (x183/x192: g 4 within seconds)
WAIT_A_S = 2.0                             # about three slow minutes
POLL_A_S = 1.0                             # bob's received poll step in arm A
PUSH_CAP_S = 90.0                          # PUSH_GAP_MS 60 s plus margin
POLL_S = 0.5
POLL_CAP_S = 3.0
READ_S = 3.0                               # arm C's rounds after the push
RISE_KCAL = 500                            # arm D's calorie rise
LAND_CAP_S = 10.0
FOLLOW_S = 3.0                             # about five slow minutes after the landing
DEF_ROW = 3                                # K.view.CLASSES order: energy, hydration, deficiency, ...
CLASSES = ("energy", "hydration", "deficiency", "excess", "stimulant", "sleep")
MACROS = ("calories", "carbs", "lipids", "proteins")
TICK_S = 20
TICK_N = 3
LOG_RX = re.compile(r"NR_|NutritionRevamp|TKX|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
LOG_LIMIT = 200
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LINE_RX = re.compile(r"\[NutritionRevamp\]")
FIRST_SIGHT_RX = re.compile(r"players: first sight of ")
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
PANEL_KEYS = ("keyPresses", "opens", "closes", "requests", "requestFailures", "errors")
STORE_KEYS = ("loads", "migrations", "created", "failures")
RC_KEYS = ("minutes", "landed", "skipped", "noStore", "errors", "seeded", "credits")

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
    "S0": {"server_error_count": 0, "admin_lua_error": False, "both_ready": True,
           "mirror.username": {"bob": "bob", "admin": "admin"}, "received": ">= 1 on each", "view.level": 2,
           "bob tooltip original": "function", "isDebugEnabled": {"bob": False, "admin": True},
           "getLuaDebuggerErrorCount": 0, "record.v": 2, "reconcile.count": 0, "census": "admin and bob",
           "store.failures": 0, "reconcile.errors": 0, "first_sight_lines": ["admin", "bob"]},
    "A": {"setpath.after": VITC_P, "bob record vitC.g": 4, "admin record vitC.g": 1,
          "bob received rises within_s": PUSH_CAP_S, "pushes_delta": ">= 1", "bob nut_vitC_g": 4,
          "bob username": "bob", "admin nut_vitC_g": 1, "admin username": "admin", "admin received": "unchanged"},
    "B": {"client exists": False, "client census keyCount": 0, "client missing": ["bob", "admin"],
          "server exists": True, "server census": ">= 2 keys, both usernames"},
    "E": {"trigger ok": True, "keyPresses": "0 -> 1 -> 2", "opens": "0 -> 1", "requests_delta": 1,
          "visible after press 1": True, "received_delta": ">= 1 within 3 s", "view.level": 2,
          "classes.deficiency": 3, "rows[3].text": "UI_NR_Class_deficiency_3", "admin opens": 0,
          "admin classes.deficiency": 0, "closes after press 2": 1, "visible after press 2": False, "errors": 0},
    "C": {"traitList has": "nutritionist", "bob client size": "+1 at the first read", "admin client size": "unchanged",
          "server bob size": "+1", "server admin size": "unchanged", "bob hasTrait/level": [True, 3],
          "admin hasTrait/level": [False, 2], "admin copy of bob": "unreadable (stated)"},
    "D": {"count": "0 -> 1 within LAND_CAP_S", "lastIntake.source": "reconciled",
          "lastIntake.calories": f"{RISE_KCAL} +- 10", "lastIntake.carbs/lipids/proteins": 0,
          "buffer.calories rise": "> 450", "non-macro buffer keys risen": 0,
          "nutrients p risen on bob and not on admin": 0,
          "landed_delta": 1, "admin count": 0, "follow count": 1, "follow landed_delta": 0,
          "vanilla store after": "recorded, not graded"},
    "F": {"bob TK.version": 1, "bob NR.version": "resolved", "bob isDebugEnabled": False, "bob getDebug": False,
          "bob getLuaDebuggerErrorCount": 0, "bob tooltip original": "function", "admin isDebugEnabled": True},
    "G": {"server_tps": f"within 0.5/s of {X183B_TICKS} ({X183B_RUN})", "client_tps": "> 0 on each"},
    "Z": {"mod_error": "none", "admin reconcile.count": 0, "bob reconcile.count": 1, "store.failures": 0},
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
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_DeclaredFood"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "baseline": {"tick_run": X183B_RUN, "tick_path": "interface.json verdicts.H.observed.server_tps",
                 "ticks": list(X183B_TICKS)},
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple))
                  and k not in ("REPO", "LUA_DIR", "MOD_DIR")},
    "predictions": PRED,
    "deviations": [
        "The arms run S0, A, B, E, C, D, F, G, Z: bob's panel (E) is read at the Bands level 2 before the trait push "
        "(C) turns bob's view to level 3.",
        "Arm D raises the calorie store alone (nutrition.set takes one field per call and a bus round trip is about one "
        "slow minute, so a second write for the carbs could land in the next minute and be read as a separate, "
        "calorie-less movement); the landing is therefore calories only and the carbs, lipids and proteins land 0.",
        "Arm C: admin's client copy of bob is unreadable through the harness (its client-side subjects are the local "
        "player only), so the not-on-admin half reads admin's own list and view.",
        "Arm B: the client census calls ModData.getOrCreate, which creates an empty local table, so the non-creating "
        "lua.call ModData.exists is read first and the census's miss is keyCount 0.",
        "Arm E reads the deficiency row's text key through lua.setpath's before (a write of 0 and the value written "
        "straight back), since lua.global indexes by string only.",
        "Arm A's push may be held by the bus's 60 s gap since bob's last effects push; bob's received is polled up to "
        "PUSH_CAP_S, and only if no push arrives does bob pull one mirror (stated in the artifact).",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": ["bob's vitamin C pool forced to 0.05", "bob holding NUTRITIONIST",
                                        "bob's reconciled 500 kcal intake", "bob's panel closed"]},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "mod_error_checks": [],
}


def grep_noecho(log, rx, limit):
    """The bus's echo lines dropped BEFORE the limit counts: (kept lines, echo lines skipped)."""
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:300])
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


def lcall(side, args, tag):
    return keep(step(tag, side, "lua.call", args))


def mcall(side, args, tag):
    return keep(step(tag, side, "lua.callm", args))


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
    c = clients.get("admin")
    return c is not None and "lua_error" in getattr(c, "seen", {})


def panel_stats(side, tag):
    return {k: gread(side, f"{NR}.client.panel.stats.{k}", f"{tag}_{who(side)}_panel_{k}") for k in PANEL_KEYS}


def sv(snap, k):
    return num(val((snap or {}).get(k)))


def received(side, tag):
    return gread(side, f"{NR}.client.received", f"{tag}_{who(side)}_recv")


def mirror_reads(side, tag):
    return {k: gread(side, f"{NR}.client.mirror.{k}", f"{tag}_{who(side)}_m_{k}")
            for k in ("username", "nut_vitC_g", "nut_vitC_p", "resets")}


def rec_read(user, field, tag):
    return gread(SRV, f"{REC}.{user}.{field}", f"{tag}_rec_{user}_{field}")


def census(user, keys, tag):
    """One witness.moddata call on the server: the named dotted keys of one record, one snapshot."""
    args = " ".join(f"{user}.{k}" for k in keys)
    return keep(step(f"{tag}_census_{user}", SRV, "witness.moddata", f"global:{STORE} {args}"))


def csize(side, tag):
    a = keep(step(f"{tag}_{who(side)}_size", side, "witness.chain", CHAIN_SIZE))
    a["size"] = num(a.get("value"))
    return a


def ssize(user, tag):
    a = keep(step(f"{tag}_srv_{user}_size", SRV, "witness.chain", f"{user} {CHAIN_SIZE}"))
    a["size"] = num(a.get("value"))
    return a


def poll_received(side, before, cap, step_s, tag):
    rows, end, i = [], time.time() + cap, 0
    while True:
        row = received(side, f"{tag}_p{i}")
        rows.append(row)
        i += 1
        v = num(val(row))
        if before is not None and v is not None and v > before:
            return rows, row["wall"]
        if time.time() >= end:
            return rows, None
        time.sleep(step_s)


def setpath_read(side, path_, tag):
    """A client Lua field under a numeric key read through lua.setpath's `before`: a write of 0, then the read value
    written straight back. Returns {before, value, first, restored}."""
    first = keep(step(f"{tag}_w0", side, "lua.setpath", f"{path_} 0"))
    before = first.get("before")
    restored = None
    if first.get("ok") and before is not None and before != "nil":
        restored = keep(step(f"{tag}_wb", side, "lua.setpath", f"{path_} {before}"))
    return {"before": before, "value": before, "first": first, "restored": restored}


def debug_reads(side, tag):
    return {"isDebugEnabled": lcall(side, "isDebugEnabled", f"{tag}_{who(side)}_isdbg"),
            "getDebug": lcall(side, "getDebug", f"{tag}_{who(side)}_getdbg"),
            "luaErrorCount": lcall(side, "getLuaDebuggerErrorCount", f"{tag}_{who(side)}_errc")}


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def mod_error(after):
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    if parked():
        why.append({"admin": "lua_error seen (parked in the debugger)"})
    counts = {}
    for side in CLIENT_SIDES:
        for s in ("panel", "view", "tab"):
            e = num(val(gread(side, f"{NR}.client.{s}.stats.errors", f"chk_{after}_{who(side)}_{s}_err")))
            counts[f"{who(side)}.{s}"] = e
            if (e or 0) > 0:
                why.append({f"{who(side)}.{s}.errors": e,
                            "lastError": val(gread(side, f"{NR}.client.{s}.lastError",
                                                   f"chk_{after}_{who(side)}_{s}_le"))})
    ne = num(val(gread(SRV, f"{NR}.server.nutrients.stats.errors", f"chk_{after}_nerr")))
    re_ = num(val(gread(SRV, f"{NR}.server.reconcile.stats.errors", f"chk_{after}_rerr")))
    if (ne or 0) > 0:
        why.append({"server.nutrients.errors": ne,
                    "lastError": val(gread(SRV, f"{NR}.server.nutrients.lastError", f"chk_{after}_nle"))})
    if (re_ or 0) > 0:
        why.append({"server.reconcile.errors": re_,
                    "lastError": val(gread(SRV, f"{NR}.server.reconcile.lastError", f"chk_{after}_rle"))})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "client_error_counts": counts,
                                    "server_nutrients_errors": ne, "server_reconcile_errors": re_, "found": why})
    return why


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


def rc_stats(tag):
    return {k: gread(SRV, f"{NR}.server.reconcile.stats.{k}", f"{tag}_rs_{k}") for k in RC_KEYS}


def store_stats(tag):
    return {k: gread(SRV, f"{NR}.server.store.stats.{k}", f"{tag}_ss_{k}") for k in STORE_KEYS}


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {"clients": {}}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    for side in CLIENT_SIDES:
        C = P["clients"][who(side)] = {}
        C["tk_version"] = gread(side, "TK.version", f"S0_{who(side)}_tkv")
        C["nr_version"] = gread(side, f"{NR}.version", f"S0_{who(side)}_nrv")
        C["mirror"] = mirror_reads(side, "S0")
        C["received"] = received(side, "S0")
        C["view_level"] = gread(side, f"{NR}.client.view.level", f"S0_{who(side)}_level")
        C["view_hasTrait"] = gread(side, f"{NR}.client.view.hasTrait", f"S0_{who(side)}_has")
        C["tooltip_original"] = gread(side, "NR_ClientTooltip_Installed.original", f"S0_{who(side)}_tt")
        C["debug"] = debug_reads(side, "S0")
        C["panel_stats"] = panel_stats(side, "S0")
        C["seen"] = dict(getattr(node(side), "seen", {}))
    S = P["server"] = {}
    S["nr_version"] = gread(SRV, f"{NR}.version", "S0_srv_nrv")
    S["players"] = keep(step("S0_players", SRV, "players"))
    for u in ("bob", "admin"):
        S[f"{u}_v"] = rec_read(u, "v", "S0")
        S[f"{u}_rc"] = rec_read(u, "reconcile.count", "S0")
    S["census"] = keep(step("S0_census", SRV, "witness.moddata",
                            f"global:{STORE} bob.v bob.username bob.reconcile.count admin.v admin.username "
                            f"admin.reconcile.count"))
    S["store_stats"] = store_stats("S0")
    S["reconcile_stats"] = rc_stats("S0")
    S["server_errors_at_S0"] = list(server.errors)
    P["mod_error"] = mod_error("S0")
    P["parked"] = parked()


def phase_A():
    P = out["phases"]["A"] = {}
    B0 = P["before"] = {}
    for side in CLIENT_SIDES:
        B0[who(side)] = {"received": received(side, "A0"), "mirror": mirror_reads(side, "A0")}
    B0["server"] = {"pushes": gread(SRV, f"{NR}.server.bus.effects.stats.pushes", "A0_pushes"),
                    "bob_g": rec_read("bob", "nutrients.vitC.g", "A0"), "bob_p": rec_read("bob", "nutrients.vitC.p", "A0"),
                    "admin_g": rec_read("admin", "nutrients.vitC.g", "A0")}
    P["setpath"] = keep(step("A_setpath", SRV, "globalmoddata.setpath", f"{STORE} bob.nutrients.vitC.p {VITC_P}"))
    time.sleep(WAIT_A_S)
    P["after_wait"] = {"bob_g": rec_read("bob", "nutrients.vitC.g", "A1"), "bob_p": rec_read("bob", "nutrients.vitC.p", "A1"),
                       "admin_g": rec_read("admin", "nutrients.vitC.g", "A1"),
                       "pushes": gread(SRV, f"{NR}.server.bus.effects.stats.pushes", "A1_pushes")}
    before = num(val(B0["bob"]["received"]))
    rows, arrival = poll_received(BOB, before, PUSH_CAP_S, POLL_A_S, "A_poll")
    P["poll"] = rows
    P["arrival_wall"] = arrival
    P["route"] = "push" if arrival is not None else None
    if arrival is None:
        note("arm A: no push within PUSH_CAP_S; bob pulls one mirror")
        P["request"] = lcall(BOB, f"{NR}.client.requestMirror", "A_request")
        rows2, arrival2 = poll_received(BOB, before, POLL_CAP_S, POLL_S, "A_poll2")
        P["poll2"] = rows2
        P["arrival2_wall"] = arrival2
        P["route"] = "request" if arrival2 is not None else "none"
    AT = P["at_arrival"] = {}
    for side in CLIENT_SIDES:
        AT[who(side)] = {"mirror": mirror_reads(side, "A2"), "received": received(side, "A2")}
    AT["server"] = {"pushes": gread(SRV, f"{NR}.server.bus.effects.stats.pushes", "A2_pushes"),
                    "bob_g": rec_read("bob", "nutrients.vitC.g", "A2"),
                    "admin_g": rec_read("admin", "nutrients.vitC.g", "A2")}
    P["mod_error"] = mod_error("A")
    P["parked"] = parked()


def phase_B():
    P = out["phases"]["B"] = {}
    for side in CLIENT_SIDES:
        P[who(side)] = {"exists": lcall(side, f"ModData.exists {STORE}", f"B_{who(side)}_exists"),
                        "census": keep(step(f"B_{who(side)}_census", side, "witness.moddata",
                                            f"global:{STORE} bob admin"))}
    P["server"] = {"exists": lcall(SRV, f"ModData.exists {STORE}", "B_srv_exists"),
                   "census": keep(step("B_srv_census", SRV, "witness.moddata",
                                       f"global:{STORE} bob.username admin.username"))}


def view_reads(side, tag):
    return {"level": gread(side, f"{NR}.client.view.level", f"{tag}_{who(side)}_lvl"),
            "hasTrait": gread(side, f"{NR}.client.view.hasTrait", f"{tag}_{who(side)}_has"),
            "classes": {c: gread(side, f"{NR}.client.view.classes.{c}", f"{tag}_{who(side)}_cls_{c}")
                        for c in CLASSES}}


def phase_E():
    P = out["phases"]["E"] = {}
    P["before"] = {"bob": {"panel": panel_stats(BOB, "E0"), "received": received(BOB, "E0")},
                   "admin": {"panel": panel_stats(ADMIN, "E0")}}
    P["press1"] = keep(step("E_press1", BOB, "event.trigger", f"OnKeyPressed {KEY}"))
    rb = num(val(P["before"]["bob"]["received"]))
    P["poll"], P["arrival_wall"] = poll_received(BOB, rb, POLL_CAP_S, POLL_S, "E_poll")
    A = P["after1"] = {}
    A["bob"] = {"panel": panel_stats(BOB, "E1"),
                "visible": mcall(BOB, f"{INST} getIsVisible", "E1_bob_vis"),
                "view": view_reads(BOB, "E1"),
                "rows": gread(BOB, f"{NR}.client.view.rows", "E1_bob_rows"),
                "row_def_text": setpath_read(BOB, f"{NR}.client.view.rows.{DEF_ROW}.text", "E1_bob_row3"),
                "row_def_cls": setpath_read(BOB, f"{NR}.client.view.rows.{DEF_ROW}.cls", "E1_bob_row3cls"),
                "username": gread(BOB, f"{NR}.client.mirror.username", "E1_bob_user")}
    A["admin"] = {"panel": panel_stats(ADMIN, "E1"), "view": view_reads(ADMIN, "E1")}
    A["server"] = {"bob_g": rec_read("bob", "nutrients.vitC.g", "E1")}
    P["press2"] = keep(step("E_press2", BOB, "event.trigger", f"OnKeyPressed {KEY}"))
    time.sleep(0.5)
    P["after2"] = {"bob": {"panel": panel_stats(BOB, "E2"), "visible": mcall(BOB, f"{INST} getIsVisible", "E2_bob_vis")},
                   "admin": {"panel": panel_stats(ADMIN, "E2")}}
    P["mod_error"] = mod_error("E")
    P["parked"] = parked()


def phase_C():
    P = out["phases"]["C"] = {}
    P["before"] = {"bob": csize(BOB, "C0"), "admin": csize(ADMIN, "C0"),
                   "server_bob": ssize("bob", "C0"), "server_admin": ssize("admin", "C0"),
                   "bob_view": view_reads(BOB, "C0"), "admin_view": view_reads(ADMIN, "C0"),
                   "bob_received": received(BOB, "C0"), "admin_received": received(ADMIN, "C0")}
    P["push"] = keep(step("C_push", SRV, "trait.add.push", f"bob {TRAIT}"))
    push_wall = P["push"]["wall_after"]
    rounds, i = [], 0
    end = time.time() + READ_S
    while True:
        b = csize(BOB, f"C_r{i}")
        a = csize(ADMIN, f"C_r{i}")
        s = ssize("bob", f"C_r{i}")
        rounds.append({"i": i, "bob": b, "admin": a, "server_bob": s,
                       "bob_since_push_s": round(b["wall"] - push_wall, 3)})
        i += 1
        if time.time() >= end:
            break
    P["rounds"] = rounds
    P["bob_list"] = keep(step("C_bob_list", BOB, "witness.chain", CHAIN_LIST))
    P["admin_list"] = keep(step("C_admin_list", ADMIN, "witness.chain", CHAIN_LIST))
    P["server_admin_after"] = ssize("admin", "C1")
    rb = num(val(P["before"]["bob_received"]))
    P["request"] = lcall(BOB, f"{NR}.client.requestMirror", "C_request")
    P["poll"], P["arrival_wall"] = poll_received(BOB, rb, POLL_CAP_S, POLL_S, "C_poll")
    P["at_arrival"] = {"bob": view_reads(BOB, "C2"), "admin": view_reads(ADMIN, "C2"),
                       "admin_received": received(ADMIN, "C2")}
    P["admin_copy_of_bob"] = ("unreadable: the harness's client-side subjects are the local player only (subjectOf, "
                              "PZTestKit_Core.lua) and witness.chain reads the local player")
    P["mod_error"] = mod_error("C")
    P["parked"] = parked()


D_KEYS = ("reconcile", "lastIntake", "stomach.buffer", "nutrients")


def phase_D():
    P = out["phases"]["D"] = {}
    P["before"] = {"census": census("bob", D_KEYS, "D0"), "admin_census": census("admin", ("nutrients",), "D0"),
                   "store": keep(step("D0_store", SRV, "nutrition.get", "bob")),
                   "rc_stats": rc_stats("D0"), "admin_rc": rec_read("admin", "reconcile.count", "D0"),
                   "kin_minutes": gread(SRV, f"{NR}.server.kinetics.stats.minutes", "D0_kin")}
    c0 = num((P["before"]["store"] or {}).get("calories"))
    if c0 is None:
        P["skipped"] = "no calorie store read"
        return
    target = c0 + RISE_KCAL
    P["target"] = target
    P["set"] = keep(step("D_set", SRV, "nutrition.set", f"bob calories {target}"))
    polls, landed, end, i = [], None, time.time() + LAND_CAP_S, 0
    while True:
        row = rec_read("bob", "reconcile.count", f"D_p{i}")
        polls.append(row)
        i += 1
        if (num(val(row)) or 0) >= 1:
            landed = row["wall"]
            break
        if time.time() >= end:
            break
    P["poll"], P["landed_wall"] = polls, landed
    P["at_landing"] = {"census": census("bob", D_KEYS, "D1"), "admin_census": census("admin", ("nutrients",), "D1"),
                       "store": keep(step("D1_store", SRV, "nutrition.get", "bob")),
                       "rc_stats": rc_stats("D1"), "admin_rc": rec_read("admin", "reconcile.count", "D1"),
                       "kin_minutes": gread(SRV, f"{NR}.server.kinetics.stats.minutes", "D1_kin")}
    time.sleep(FOLLOW_S)
    P["follow"] = {"census": census("bob", D_KEYS, "D2"), "store": keep(step("D2_store", SRV, "nutrition.get", "bob")),
                   "rc_stats": rc_stats("D2"), "admin_rc": rec_read("admin", "reconcile.count", "D2"),
                   "kin_minutes": gread(SRV, f"{NR}.server.kinetics.stats.minutes", "D2_kin")}
    P["mod_error"] = mod_error("D")
    P["parked"] = parked()


def phase_F():
    P = out["phases"]["F"] = {}
    for side in CLIENT_SIDES:
        P[who(side)] = {"tk_version": gread(side, "TK.version", f"F_{who(side)}_tkv"),
                        "nr_version": gread(side, f"{NR}.version", f"F_{who(side)}_nrv"),
                        "debug": debug_reads(side, "F"),
                        "tooltip_original": gread(side, "NR_ClientTooltip_Installed.original", f"F_{who(side)}_tt"),
                        "seen": dict(getattr(node(side), "seen", {}))}
    P["server"] = {"debug": debug_reads(SRV, "F")}


def phase_G():
    P = out["phases"]["G"] = {"windows": []}
    sides = (SRV, BOB, ADMIN)
    for i in range(TICK_N):
        after = time.time()
        w = {"i": i}
        arms = {}
        for side in sides:
            arms[side] = ack(step(f"G{i}_arm_{who(side)}", side, "tick.rate", str(TICK_S)))
            w[f"arm_{who(side)}"] = arms[side]
        for side in sides:
            res = None
            if arms[side].get("armed"):
                try:
                    res = node(side).bus.wait_result(arms[side].get("result") or "tick-rate", timeout=TICK_S + 25,
                                                     after=after)
                except (RuntimeError, TimeoutError, OSError) as e:
                    res = {"error": f"{type(e).__name__}: {e}"}
            w[f"result_{who(side)}"] = res
        P["windows"].append(w)
        persist()


def phase_Z():
    P = out["phases"]["Z"] = {}
    for side in CLIENT_SIDES:
        P[who(side)] = {"panel": panel_stats(side, "Z"), "received": received(side, "Z"),
                        "view_level": gread(side, f"{NR}.client.view.level", f"Z_{who(side)}_lvl"),
                        "seen": dict(getattr(node(side), "seen", {}))}
    P["server"] = {"bob_rc": rec_read("bob", "reconcile.count", "Z"), "admin_rc": rec_read("admin", "reconcile.count", "Z"),
                   "store_stats": store_stats("Z"), "rc_stats": rc_stats("Z")}
    P["mod_error"] = mod_error("Z")


def body():
    for name, fn in (("S0", phase_S0), ("A", phase_A), ("B", phase_B), ("E", phase_E), ("C", phase_C),
                     ("D", phase_D), ("F", phase_F), ("G", phase_G), ("Z", phase_Z)):
        run_phase(name, fn)
        if parked() and name not in ("G", "Z"):
            out["abort"] = f"admin parked in the debugger after arm {name}"
            run_phase("Z", phase_Z)
            return


# ---------------------------------------------------------------- grading
def tps(res):
    return (res or {}).get("ticksPerSecond") if isinstance(res, dict) else None


def census_vals(c):
    return (c or {}).get("values") or {}


def flat(v, prefix="", outd=None):
    outd = {} if outd is None else outd
    if isinstance(v, list):
        v = {str(i + 1): x for i, x in enumerate(v)}
    if isinstance(v, dict):
        for k, x in v.items():
            flat(x, f"{prefix}.{k}" if prefix else str(k), outd)
    else:
        outd[prefix] = v
    return outd


def grade_all():
    ph = out["phases"]
    S = ph.get("S0") or {}
    if S:
        Cs = S.get("clients") or {}
        Sv = S.get("server") or {}
        cv = census_vals(Sv.get("census"))
        fs = [ln for ln in (out.get("logs") or {}).get("mod_lines", []) if FIRST_SIGHT_RX.search(ln)]
        obs = {"server_error_count": out.get("server_error_count"), "admin_lua_error": out.get("admin_lua_error"),
               "ready": S.get("ready"),
               "mirror.username": {u: val((Cs.get(u) or {}).get("mirror", {}).get("username")) for u in ("bob", "admin")},
               "received": {u: num(val((Cs.get(u) or {}).get("received"))) for u in ("bob", "admin")},
               "view.level": {u: num(val((Cs.get(u) or {}).get("view_level"))) for u in ("bob", "admin")},
               "tooltip_original": {u: (Cs.get(u) or {}).get("tooltip_original", {}).get("type") for u in ("bob", "admin")},
               "isDebugEnabled": {u: ((Cs.get(u) or {}).get("debug") or {}).get("isDebugEnabled", {}).get("r1")
                                  for u in ("bob", "admin")},
               "luaErrorCount": {u: ((Cs.get(u) or {}).get("debug") or {}).get("luaErrorCount", {}).get("r1")
                                 for u in ("bob", "admin")},
               "record.v": {u: num(val(Sv.get(f"{u}_v"))) for u in ("bob", "admin")},
               "reconcile.count": {u: num(val(Sv.get(f"{u}_rc"))) for u in ("bob", "admin")},
               "census": cv, "store.failures": sv(Sv.get("store_stats"), "failures"),
               "reconcile.errors": sv(Sv.get("reconcile_stats"), "errors"), "first_sight_lines": fs}
        ready_n = len([it for it in (S.get("ready") or []) if it.get("phase") == "client_ready"])
        ok = (obs["server_error_count"] == 0 and not obs["admin_lua_error"] and ready_n == 2
              and obs["mirror.username"] == {"bob": "bob", "admin": "admin"}
              and all((v or 0) >= 1 for v in obs["received"].values())
              and obs["view.level"] == {"bob": 2, "admin": 2}
              and obs["tooltip_original"].get("bob") == "function"
              and obs["isDebugEnabled"] == {"bob": False, "admin": True}
              and obs["luaErrorCount"] == {"bob": 0, "admin": 0}
              and obs["record.v"] == {"bob": 2, "admin": 2} and obs["reconcile.count"] == {"bob": 0, "admin": 0}
              and str(cv.get("bob.username")) == "bob" and str(cv.get("admin.username")) == "admin"
              and obs["store.failures"] == 0 and obs["reconcile.errors"] == 0
              and any("of bob" in ln for ln in fs) and any("of admin" in ln for ln in fs))
        grade("S0", PRED["S0"], obs, "as_predicted" if ok else "falsified",
              "a client not ready, a mirror carrying the other user, no mirror, a debug flag the other way, a Lua "
              "error count, a record not at v 2 or a reconcile count on an idle player", {"ready_count": ready_n})
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "arm S0 not run")

    A = ph.get("A") or {}
    if A.get("at_arrival"):
        AT, B0, AW = A["at_arrival"], A.get("before") or {}, A.get("after_wait") or {}
        obs = {"setpath": A.get("setpath"), "bob_g_after_wait": num(val(AW.get("bob_g"))),
               "bob_p_after_wait": num(val(AW.get("bob_p"))), "admin_g_after_wait": num(val(AW.get("admin_g"))),
               "route": A.get("route"), "arrival_wall": A.get("arrival_wall"),
               "setpath_wall": (A.get("setpath") or {}).get("wall_after"),
               "pushes": [num(val((B0.get("server") or {}).get("pushes"))), num(val(AW.get("pushes"))),
                          num(val((AT.get("server") or {}).get("pushes")))],
               "bob": {"received": [num(val((B0.get("bob") or {}).get("received"))),
                                    num(val((AT.get("bob") or {}).get("received")))],
                       "nut_vitC_g": [num(val(((B0.get("bob") or {}).get("mirror") or {}).get("nut_vitC_g"))),
                                      num(val(((AT.get("bob") or {}).get("mirror") or {}).get("nut_vitC_g")))],
                       "username": val(((AT.get("bob") or {}).get("mirror") or {}).get("username"))},
               "admin": {"received": [num(val((B0.get("admin") or {}).get("received"))),
                                      num(val((AT.get("admin") or {}).get("received")))],
                         "nut_vitC_g": [num(val(((B0.get("admin") or {}).get("mirror") or {}).get("nut_vitC_g"))),
                                        num(val(((AT.get("admin") or {}).get("mirror") or {}).get("nut_vitC_g")))],
                         "username": val(((AT.get("admin") or {}).get("mirror") or {}).get("username"))},
               "server_bob_g_at_arrival": num(val((AT.get("server") or {}).get("bob_g"))),
               "server_admin_g_at_arrival": num(val((AT.get("server") or {}).get("admin_g")))}
        if obs["arrival_wall"] is not None and obs["setpath_wall"] is not None:
            obs["push_after_setpath_s"] = round(obs["arrival_wall"] - obs["setpath_wall"], 3)
        p = obs["pushes"]
        ok = (num((A.get("setpath") or {}).get("after")) == VITC_P and obs["bob_g_after_wait"] == 4
              and obs["admin_g_after_wait"] == 1 and obs["route"] == "push"
              and p[0] is not None and p[2] is not None and p[2] - p[0] >= 1
              and obs["bob"]["nut_vitC_g"][1] == 4 and obs["bob"]["username"] == "bob"
              and obs["admin"]["nut_vitC_g"][1] == 1 and obs["admin"]["username"] == "admin"
              and obs["admin"]["received"][0] == obs["admin"]["received"][1])
        grade("A", PRED["A"], obs, "as_predicted" if ok else "falsified",
              "no push to bob within the cap, bob's mirror not at 4, admin's mirror moved or carrying another user")
    else:
        grade("A", PRED["A"], None, "unmeasured", "arm A not run")

    Bp = ph.get("B") or {}
    if Bp.get("server"):
        obs = {}
        for u in ("bob", "admin"):
            C = Bp.get(u) or {}
            cen = C.get("census") or {}
            obs[u] = {"exists": (C.get("exists") or {}).get("r1"), "exists_reply": C.get("exists"),
                      "keyCount": cen.get("keyCount"), "keys": cen.get("keys"), "missing": cen.get("missing"),
                      "values": cen.get("values")}
        scen = Bp["server"].get("census") or {}
        obs["server"] = {"exists": (Bp["server"].get("exists") or {}).get("r1"), "keyCount": scen.get("keyCount"),
                         "keys": scen.get("keys"), "values": scen.get("values")}
        ok = all(obs[u]["exists"] is False and obs[u]["keyCount"] == 0
                 and sorted(obs[u]["missing"] or []) == ["admin", "bob"] for u in ("bob", "admin"))
        ok = ok and obs["server"]["exists"] is True and (obs["server"]["keyCount"] or 0) >= 2 \
            and (obs["server"]["values"] or {}).get("bob.username") == "bob" \
            and (obs["server"]["values"] or {}).get("admin.username") == "admin"
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified",
              "a client holding the table or a record in it; the server missing a record")
    else:
        grade("B", PRED["B"], None, "unmeasured", "arm B not run")

    E = ph.get("E") or {}
    if E.get("after1"):
        b0 = (E.get("before") or {}).get("bob", {}).get("panel")
        a0 = (E.get("before") or {}).get("admin", {}).get("panel")
        b1 = E["after1"]["bob"]
        b2 = (E.get("after2") or {}).get("bob") or {}
        obs = {"press1": E.get("press1"), "press2": E.get("press2"),
               "bob": {k: [sv(b0, k), sv(b1["panel"], k), sv(b2.get("panel"), k)] for k in PANEL_KEYS},
               "admin": {k: [sv(a0, k), sv(E["after1"]["admin"]["panel"], k),
                             sv(((E.get("after2") or {}).get("admin") or {}).get("panel"), k)] for k in PANEL_KEYS},
               "bob_received": [num(val((E.get("before") or {}).get("bob", {}).get("received"))),
                                num(val((E.get("poll") or [{}])[-1]))],
               "arrival_wall": E.get("arrival_wall"),
               "bob_visible": [(b1.get("visible") or {}).get("r1"), (b2.get("visible") or {}).get("r1")],
               "bob_level": num(val(b1["view"]["level"])),
               "bob_classes": {c: num(val(b1["view"]["classes"].get(c))) for c in CLASSES},
               "admin_classes": {c: num(val(E["after1"]["admin"]["view"]["classes"].get(c))) for c in CLASSES},
               "bob_rows": b1.get("rows"),
               "bob_row3_text": (b1.get("row_def_text") or {}).get("value"),
               "bob_row3_cls": (b1.get("row_def_cls") or {}).get("value"),
               "bob_row3_restored": ((b1.get("row_def_text") or {}).get("restored") or {}).get("after"),
               "bob_username": val(b1.get("username"))}
        bb = obs["bob"]
        ok = ((E.get("press1") or {}).get("ok") is True and bb["keyPresses"][:3] == [0, 1, 2]
              and bb["opens"][:2] == [0, 1] and bb["requests"][1] is not None and bb["requests"][0] is not None
              and bb["requests"][1] - bb["requests"][0] == 1 and obs["bob_visible"] == [True, False]
              and obs["arrival_wall"] is not None and obs["bob_level"] == 2
              and obs["bob_classes"]["deficiency"] == 3 and obs["bob_row3_text"] == "UI_NR_Class_deficiency_3"
              and obs["admin"]["opens"][1] == 0 and obs["admin_classes"]["deficiency"] == 0
              and bb["closes"][2] == 1 and (bb["errors"][2] or 0) == 0)
        grade("E", PRED["E"], obs, "as_predicted" if ok else "falsified",
              "bob's panel not toggled by the Lua-triggered key, its rows not bob's, or admin's panel moved")
    else:
        grade("E", PRED["E"], None, "unmeasured", "arm E not run")

    Cp = ph.get("C") or {}
    if Cp.get("push"):
        b4 = Cp.get("before") or {}
        rounds = Cp.get("rounds") or []
        AT = Cp.get("at_arrival") or {}
        obs = {"push": {k: Cp["push"].get(k) for k in ("added", "sent", "traitList", "wallBefore", "wallAfter")},
               "sizes_before": {"bob": (b4.get("bob") or {}).get("size"), "admin": (b4.get("admin") or {}).get("size"),
                                "server_bob": (b4.get("server_bob") or {}).get("size"),
                                "server_admin": (b4.get("server_admin") or {}).get("size")},
               "rounds": [{"i": r["i"], "bob": r["bob"].get("size"), "admin": r["admin"].get("size"),
                           "server_bob": r["server_bob"].get("size"), "bob_since_push_s": r["bob_since_push_s"]}
                          for r in rounds],
               "server_admin_after": (Cp.get("server_admin_after") or {}).get("size"),
               "bob_list": (Cp.get("bob_list") or {}).get("value"),
               "admin_list": (Cp.get("admin_list") or {}).get("value"),
               "arrival_wall": Cp.get("arrival_wall"),
               "bob_view": [val(AT.get("bob", {}).get("hasTrait")), num(val(AT.get("bob", {}).get("level")))],
               "admin_view": [val(AT.get("admin", {}).get("hasTrait")), num(val(AT.get("admin", {}).get("level")))],
               "admin_received": [num(val(b4.get("admin_received"))), num(val(AT.get("admin_received")))],
               "admin_copy_of_bob": Cp.get("admin_copy_of_bob")}
        sb = obs["sizes_before"]
        r0 = obs["rounds"][0] if obs["rounds"] else {}
        tl_ = obs["push"].get("traitList")
        has = "nutritionist" in json.dumps(tl_).lower()
        ok = (has and sb["bob"] is not None and r0.get("bob") == sb["bob"] + 1
              and all(r["admin"] == sb["admin"] for r in obs["rounds"])
              and r0.get("server_bob") == (sb["server_bob"] or 0) + 1
              and obs["server_admin_after"] == sb["server_admin"]
              and obs["bob_view"] == [True, 3] and obs["admin_view"] == [False, 2])
        grade("C", PRED["C"], obs, "as_predicted" if ok else "falsified",
              "bob's list not gaining the trait, admin's own list or view moving, the server's copies disagreeing")
    else:
        grade("C", PRED["C"], None, "unmeasured", "arm C not run")

    D = ph.get("D") or {}
    if D.get("at_landing"):
        v0 = census_vals((D.get("before") or {}).get("census"))
        v1 = census_vals(D["at_landing"].get("census"))
        v2 = census_vals((D.get("follow") or {}).get("census"))
        buf0, buf1 = flat(v0.get("bob.stomach.buffer") or {}), flat(v1.get("bob.stomach.buffer") or {})
        nut0, nut1 = flat(v0.get("bob.nutrients") or {}), flat(v1.get("bob.nutrients") or {})
        risen_buf = sorted(k for k in buf1 if k not in MACROS and (num(buf1.get(k)) or 0) > (num(buf0.get(k)) or 0))
        risen_p = sorted(k for k in nut1 if k.endswith(".p") and (num(nut1.get(k)) or 0) > (num(nut0.get(k)) or 0))
        an0 = flat(census_vals((D.get("before") or {}).get("admin_census")).get("admin.nutrients") or {})
        an1 = flat(census_vals(D["at_landing"].get("admin_census")).get("admin.nutrients") or {})
        risen_p_admin = sorted(k for k in an1 if k.endswith(".p") and (num(an1.get(k)) or 0) > (num(an0.get(k)) or 0))
        risen_p_bob_only = sorted(k for k in risen_p if k not in risen_p_admin)
        li = v1.get("bob.lastIntake") or {}
        rs0, rs1, rs2 = (D.get("before") or {}).get("rc_stats"), D["at_landing"].get("rc_stats"), \
            (D.get("follow") or {}).get("rc_stats")
        obs = {"store_before": {k: (D.get("before") or {}).get("store", {}).get(k) for k in MACROS},
               "target": D.get("target"), "set_reply": {k: (D.get("set") or {}).get(k) for k in MACROS},
               "set_wall": (D.get("set") or {}).get("wall_after"), "landed_wall": D.get("landed_wall"),
               "count": [num(((v0.get("bob.reconcile") or {}).get("count"))), num(((v1.get("bob.reconcile") or {})
                                                                                 .get("count"))),
                         num(((v2.get("bob.reconcile") or {}).get("count")))],
               "lastIntake": li, "lastIntake_before": v0.get("bob.lastIntake"),
               "buffer_calories": [num(buf0.get("calories")), num(buf1.get("calories")),
                                   num(flat(v2.get("bob.stomach.buffer") or {}).get("calories"))],
               "buffer_macros_at_landing": {k: num(buf1.get(k)) for k in MACROS},
               "buffer_macros_before": {k: num(buf0.get(k)) for k in MACROS},
               "risen_non_macro_buffer_keys": risen_buf, "risen_nutrient_p": risen_p,
               "risen_nutrient_p_admin": risen_p_admin, "risen_nutrient_p_bob_only": risen_p_bob_only,
               "landed": [sv(rs0, "landed"), sv(rs1, "landed"), sv(rs2, "landed")],
               "minutes": [sv(rs0, "minutes"), sv(rs1, "minutes"), sv(rs2, "minutes")],
               "kin_minutes": [num(val((D.get("before") or {}).get("kin_minutes"))),
                               num(val(D["at_landing"].get("kin_minutes"))),
                               num(val((D.get("follow") or {}).get("kin_minutes")))],
               "admin_rc": [num(val((D.get("before") or {}).get("admin_rc"))), num(val(D["at_landing"].get("admin_rc"))),
                            num(val((D.get("follow") or {}).get("admin_rc")))],
               "store_at_landing": {k: D["at_landing"].get("store", {}).get(k) for k in MACROS},
               "store_follow": {k: (D.get("follow") or {}).get("store", {}).get(k) for k in MACROS},
               "baseline": [((v0.get("bob.reconcile") or {}).get("baseline")),
                            ((v1.get("bob.reconcile") or {}).get("baseline"))]}
        if obs["landed_wall"] is not None and obs["set_wall"] is not None:
            obs["landed_after_set_s"] = round(obs["landed_wall"] - obs["set_wall"], 3)
        bc = obs["buffer_calories"]
        lc = num(li.get("calories"))
        ok = (obs["count"][0] == 0 and obs["count"][1] == 1 and obs["count"][2] == 1
              and li.get("source") == "reconciled" and lc is not None and abs(lc - RISE_KCAL) <= 10
              and all((num(li.get(k)) or 0) == 0 for k in ("carbs", "lipids", "proteins"))
              and bc[0] is not None and bc[1] is not None and bc[1] - bc[0] > 450
              and not risen_buf and not risen_p_bob_only
              and obs["landed"][0] is not None and obs["landed"][1] == obs["landed"][0] + 1
              and obs["landed"][2] == obs["landed"][1] and obs["admin_rc"] == [0, 0, 0])
        grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified",
              "no landing, a landing not marked reconciled, a nutrient key moved up, a double landing, admin counted")
    else:
        grade("D", PRED["D"], None, "unmeasured", "arm D not run" if not D.get("skipped") else D.get("skipped"))

    F = ph.get("F") or {}
    if F.get("bob"):
        fb, fa = F["bob"], F.get("admin") or {}
        obs = {"bob": {"tk_version": num(val(fb.get("tk_version"))), "nr_version": val(fb.get("nr_version")),
                       "nr_version_resolved": (fb.get("nr_version") or {}).get("resolved"),
                       "isDebugEnabled": (fb.get("debug") or {}).get("isDebugEnabled", {}).get("r1"),
                       "getDebug": (fb.get("debug") or {}).get("getDebug", {}).get("r1"),
                       "luaErrorCount": (fb.get("debug") or {}).get("luaErrorCount", {}).get("r1"),
                       "tooltip_original": (fb.get("tooltip_original") or {}).get("type"), "seen": fb.get("seen")},
               "admin": {"isDebugEnabled": (fa.get("debug") or {}).get("isDebugEnabled", {}).get("r1"),
                         "getDebug": (fa.get("debug") or {}).get("getDebug", {}).get("r1"),
                         "luaErrorCount": (fa.get("debug") or {}).get("luaErrorCount", {}).get("r1"),
                         "seen": fa.get("seen")},
               "server": {k: (v or {}).get("r1") for k, v in ((F.get("server") or {}).get("debug") or {}).items()}}
        ob = obs["bob"]
        ok = (ob["tk_version"] == 1 and ob["nr_version_resolved"] is True and ob["isDebugEnabled"] is False
              and ob["getDebug"] is False and ob["luaErrorCount"] == 0 and ob["tooltip_original"] == "function"
              and obs["admin"]["isDebugEnabled"] is True)
        grade("F", PRED["F"], obs, "as_predicted" if ok else "falsified",
              "the bus not answering on bob, bob reading as a debug client, a Lua error on bob, the tooltip not hooked")
    else:
        grade("F", PRED["F"], None, "unmeasured", "arm F not run")

    G = ph.get("G") or {}
    if G.get("windows"):
        st = [tps(w.get("result_server")) for w in G["windows"]]
        bt = [tps(w.get("result_bob")) for w in G["windows"]]
        at = [tps(w.get("result_admin")) for w in G["windows"]]
        obs = {"server_tps": st, "bob_tps": bt, "admin_tps": at, "baseline": list(X183B_TICKS)}
        lo, hi = min(X183B_TICKS) - 0.5, max(X183B_TICKS) + 0.5
        if any(v is None for v in st):
            verdict = "unmeasured"
        else:
            ok = (all(lo <= v <= hi for v in st) and all((v or 0) > 0 for v in bt + at))
            verdict = "as_predicted" if ok else "falsified"
        grade("G", PRED["G"], obs, verdict, "a server rate outside the band with two clients attached")
    else:
        grade("G", PRED["G"], None, "unmeasured", "arm G not run")

    Z = ph.get("Z") or {}
    if Z:
        Zs = Z.get("server") or {}
        obs = {"bob_rc": num(val(Zs.get("bob_rc"))), "admin_rc": num(val(Zs.get("admin_rc"))),
               "store.failures": sv(Zs.get("store_stats"), "failures"),
               "rc_stats": {k: sv(Zs.get("rc_stats"), k) for k in RC_KEYS}, "mod_error": Z.get("mod_error") or [],
               "admin_lua_error": out.get("admin_lua_error")}
        ok = (not obs["mod_error"] and obs["admin_rc"] == 0 and obs["bob_rc"] == 1 and obs["store.failures"] == 0)
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error, a count on admin, a store failure")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "arm Z not run")


if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if out["mod_dirty"]:
    out["error"] = "mod/ not quiescent (git status --short mod/ not empty); the session was not started"
    persist()
    print(out["error"])
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
        adm = clients.get("admin") if isinstance(clients, dict) else None
        out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
        out["client_seen"] = {getattr(c, "username", str(i)): dict(getattr(c, "seen", {})) for i, c in enumerate(every)}
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
            raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
            mod_lines, _ = grep_noecho(server.log_path, MOD_LINE_RX, LOG_LIMIT)
            out["logs"] = {"server": raw, "server_echo_lines_excluded": echoed, "mod_lines": mod_lines,
                           "first_sight_lines": [ln for ln in mod_lines if FIRST_SIGHT_RX.search(ln)],
                           "reconcile_lines": [ln for ln in mod_lines if "reconcile:" in ln],
                           "limits": {"log": LOG_LIMIT},
                           "patterns": {"log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern,
                                        "mod": MOD_LINE_RX.pattern, "first_sight": FIRST_SIGHT_RX.pattern},
                           "clients": {}}
            for c in every:
                u = getattr(c, "username", "?")
                lines, ech = grep_noecho(c.console, LOG_RX, LOG_LIMIT)
                mlines, _ = grep_noecho(c.console, MOD_LINE_RX, LOG_LIMIT)
                out["logs"]["clients"][u] = {"lines": lines, "echo_lines_excluded": ech, "mod_lines": mlines}
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
