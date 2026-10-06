"""x191-gate-race -- Plan 8 Task 5, live 1, ONE boot of profile `x19-gate` (PZTestKit + NutritionRevamp + TKX_DeclaredFood;
Nutrition false; DayLength 1; NO [sandbox.NR] block, so the Bands default of ruling T13-1 is read live for the first time,
ruling T13-3). ONE artifact `gate.json`. Shape: x183_interface.py (step, persist, run_phase, mod_error, both logs grepped,
the artifact copied by the driver). Written BEFORE the boot with every prediction in it and never edited after the run
(CLAUDE.md s5, B3-1/B3-2).

BUILD UNDER TEST (Task 5 build block): HEAD 0df50bb, mod/ quiescent: Task 3's kernels (NR_Kernel_Store.lua,
NR_Kernel_Reconcile.lua, the NR_Kernel_View.lua requirements fix) at 1cf2a44 + bbfa4cc; Task 4's adapters (NR_Server_Store.lua
through K.store.load, NR_Server_Reconcile.lua, the band mark in NR_Server_Bus/Weight) at 2d4dc4d + 0df50bb. The harness:
event.trigger (7a8e9e9) and lua.callm (d65703f; reply shapes 0ff30f4) -- this boot is their smoke test.

ARMS (the plan's Task 5 with the amendments; the order is S0, A, BC, D, E, Z -- see deviations):
  S0 the load: server error count, the client debugger marker, TK/NR versions both sides; the Bands default:
     client view.level / view.optionLevel / view.hasTrait, server options.visibilityMode; the store on the Plan 8
     build: server kernel.store.VERSION, lua.call NutritionRevamp.server.store.get admin (r1_keys), witness.moddata
     global:NutritionRevamp.players admin.v / admin.username / admin.reconcile.count, store.stats, reconcile.stats,
     NutritionRevamp.server.store.records.admin.reconcile.count; received; the mod-error check.
  A  the Nutritionist-gate race (#3241, ruling 12), three legs, every paired read client first:
     A1 the client-local add: client witness.chain getCharacterTraits.getKnownTraits(.size) and the server's
        witness.chain admin ... before; trait.local NUTRITIONIST add (no sync); then for READ_S (5 s) from the add's
        reply, back-to-back pairs (client size, then server size; each bus read takes about 0.5 s, so the pairs ARE the
        0.5 s steps); then lua.call NutritionRevamp.client.requestMirror and received polled to +1 (0.5 s steps, cap
        3 s); AT that arrival: view.hasTrait, view.level, view.stats.traitReads, view.stats.rebuilds, received, the
        client list (size and string form), then the server's size.
        The branches: LOST = a client size read after the add back at the pre-add size before the arrival (the
        server's copy restored the client's list -- #3068's restore of a client-only removal, #2759's route); MISSED =
        the client list held the trait at every read through the arrival and hasTrait read false (the view's read
        missed it); NEITHER = the list held and hasTrait read true; OTHER = anything else (stated).
     A2 the synced leg: trait.local NUTRITIONIST remove (the client copy restored, a no-op when A1 lost it), then the
        server's trait.add.push admin NUTRITIONIST (the add and sendSyncPlayerFields in one tick); the same 5 s of
        paired size reads; requestMirror; at the arrival the same reads.
     A3 the restore: the server's trait.set admin NUTRITIONIST remove then trait.push admin (the trait-block push);
        the same paired reads for 5 s; requestMirror; at the arrival the same reads -- the level back at 2 for B/C.
  BC the key press and the wheel, one open period (#3247, #3248):
     B1 panel.stats (keyPresses, opens, closes, requests, requestFailures, fits, errors) and lua.callm
        NutritionRevamp.client.panel.instances.0 getIsVisible before; event.trigger OnKeyPressed 39 (client); received
        polled to +1; the stats and getIsVisible again.
     C  view.level and view.stats.overflowRows after the open's fit (a SETTLE_S wait); if overflowRows is 0 the panel is
        moved down (lua.callm instances.0 setY 400: the cap is the screen height below the panel's top) and a
        requestMirror rebuild re-fits it, overflowRows read again; the panel's scrollY and overflowPx are Lua fields
        under a numeric key that lua.global cannot index, so each is read through lua.setpath's `before` (a write of 0
        followed at once by a write of the read value back -- a read that leaves the field as it found it); then
        lua.callm instances.0 onMouseWheel 1 -> r1 and scrollY; lua.callm instances.0 onMouseWheel -1 -> r1 and
        scrollY; the panel moved back to y 200 when it was moved.
     B2 event.trigger OnKeyPressed 39 again; the stats and getIsVisible.
  D  the character-info tab (#3246's method half): vanilla keeps the window at ISCharacterInfoWindow.instance
     (ISCharacterInfoWindow.lua:341), a string-keyed global path, so lua.global and lua.callm reach its nrView:
     tab.stats, the window's height, the tab panel's y and height, the view's y, height and scrollY before; lua.callm
     ISCharacterInfoWindow.instance.nrView render; the same reads after (renders +1; the window's height re-asserted by
     setHeightAndParentHeight: panel.height = nrView.y + nrView.height, window.height = panel.y + panel.height);
     lua.callm ... nrView onMouseWheel 1 then -1 with scrollY read (lua.global, string keys) after each.
     onTabTornOff(view, window) takes two UI tables, which no scalar argument can pass: UNMEASURED, stated.
  E  tick.rate 20 x 3, server and client armed in the same windows, against x183b's server 10.003 / 10.053 / 10.002.
  Z  the stats again, the reconcile count again (0 on an idle admin through the boot: T4 review residual e), the
     store stats, the mod-error check.
  After teardown: the server log grepped with the PZTK bus echo lines excluded (CLAUDE.md s5: the harness echoes every
  probe's reply into the server log, x183's arm I falsified twice by its own grep): the mod's own [NutritionRevamp]
  lines, the migration line `store: migrated`, `reconcile:` lines, and Lua error markers.

PREDICTIONS (graded in `verdicts` with as_predicted / falsified / trivial / unmeasured):
  S0  server_error_count 0; no client lua_error; view.level 2, view.optionLevel 2, hasTrait false; server
      options.visibilityMode 2 (no NR.VisibilityMode key: the Bands default); received >= 1; kernel.store.VERSION 2;
      the record's v 2 and username admin; store.stats.created 1, migrations 0, failures 0; reconcile count 0;
      reconcile.stats.errors 0; NO `store: migrated` line in the server log (the fixture's record is created at v2).
  A1  LOST: the client's list loses the local add before the mirror's arrival (#3068: a client-only removal was undone
      at the first read 455 ms after the command, so the server's copy is predicted to restore an add the same way, in
      well under READ_S); the server's size never moves; hasTrait false and level 2 at the arrival.
  A2  the client's list gains the trait within about 1 s of the push (#2759: 0.42-0.56 s) and keeps it; the server's
      traitList holds nutritionist; hasTrait true and view.level 3 at the arrival.
  A3  the client's list loses it within about 1.2 s (#2759's removals 0.47-1.14 s); hasTrait false and level 2.
  B   keyPresses 0 -> 1, opens +1, requests +1, getIsVisible r1 true, received +1 within 3 s; the second press:
      keyPresses 2, closes +1, getIsVisible r1 false; panel errors 0. (#3247 settled for the Lua-triggered press; the
      engine's own key path is not exercised: triggerEvent reaches Lua handlers only.)
  C   overflowRows at level 2 not predicted at the start position (about 28 rows against a room of about 496 px: a
      borderline fit); after the move (if needed) overflowRows >= 1; onMouseWheel 1 r1 true and scrollY > 0
      (min(3 lines, overflowPx)); onMouseWheel -1 r1 true and scrollY 0. The pixels stay unmeasured.
  D   tab renders +1 and tab errors 0 (the render runs under the mod's own pcall; a raise outside the frame would count
      an error and is a reading); after the render panel.height == nrView.y + nrView.height and window.height ==
      panel.y + panel.height; the wheel: r1 true and scrollY > 0 when the tab's rows overflow, then 0.
  E   server ticks per second within 0.5/s of x183b's (10.003, 10.053, 10.002); client > 0.
  Z   reconcile count 0; reconcile.stats.landed 0; no new store failures; no mod error.
A parked -debug client (the lua_error marker) is the primary reading: the remaining arms are skipped, the session torn
down, both logs grepped.

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
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, make_client,                 # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x19-gate"
PREFIX = "x191"
SESSION = ("Plan 8 Task 5, live 1: the Nutritionist-gate race (#3241), the key press through event.trigger (#3247), the "
           "panel wheel and the tab render through lua.callm (#3248, #3246), the Bands default and the store's version "
           "on the Plan 8 build; one boot of " + PROFILE)
ARTIFACT = "gate.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
STORE = "NutritionRevamp.players"
NR = "NutritionRevamp"
INST = "NutritionRevamp.client.panel.instances.0"
TAB = "ISCharacterInfoWindow.instance"
TRAIT = "NUTRITIONIST"
CHAIN_SIZE = "getCharacterTraits.getKnownTraits.size"
CHAIN_LIST = "getCharacterTraits.getKnownTraits"
X183B_RUN = "x183b-20261006-175149"
X183B_TICKS = (10.003483800328473, 10.052752065293122, 10.002488181139586)  # interface.json verdicts.H.observed.server_tps
KEY = 39                                   # Keyboard.KEY_SEMICOLON, the panel's default bind (ruling T5-1)
READ_S = 5.0                               # the paired list reads after each trait edit (ruling 12)
POLL_S = 0.5                               # the received poll step
POLL_CAP_S = 3.0                           # the received poll cap
SETTLE_S = 1.5                             # after an arrival, for the next prerender's fit
MOVE_Y = 400                               # the panel's top when the start position fits every row
START_Y = 200                              # NR_Client_Panel.lua START_Y
TICK_S = 20
TICK_N = 3
LOG_RX = re.compile(r"NR_|NutritionRevamp|TKX|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
LOG_LIMIT = 160
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LINE_RX = re.compile(r"\[NutritionRevamp\]")
MIGRATE_RX = re.compile(r"store: migrated")
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
PANEL_KEYS = ("keyPresses", "opens", "closes", "requests", "requestFailures", "fits", "renders", "errors")
TAB_KEYS = ("added", "tornOff", "saves", "renders", "errors", "noView")
VIEW_KEYS = ("rebuilds", "traitReads", "listenerErrors", "errors", "overflowRows")
STORE_KEYS = ("loads", "migrations", "created", "failures")
RC_KEYS = ("minutes", "landed", "skipped", "noStore", "errors", "seeded", "credits")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


PRED = {
    "S0": {"server_error_count": 0, "client_lua_error": False, "view.level": 2, "view.optionLevel": 2,
           "view.hasTrait": False, "server options.visibilityMode": 2, "received": ">= 1", "kernel.store.VERSION": 2,
           "record.v": 2, "record.username": USER, "store.created": 1, "store.migrations": 0, "store.failures": 0,
           "reconcile.count": 0, "reconcile.errors": 0, "migration_line": "absent"},
    "A1": {"branch": "LOST", "server_size_moves": False, "hasTrait": False, "view.level": 2,
           "basis": "#3068: a client-only trait removal was undone at the first read 455 ms after the command"},
    "A2": {"client_gains_within_s": "about 1 (#2759 0.42-0.56 s)", "server_traitList_has": "nutritionist",
           "hasTrait": True, "view.level": 3},
    "A3": {"client_loses_within_s": "about 1.2 (#2759 removals 0.47-1.14 s)", "hasTrait": False, "view.level": 2},
    "B": {"keyPresses": "0 -> 1 -> 2", "opens_delta": 1, "requests_delta": 1, "visible_after_press1": True,
          "received_delta": ">= 1 within 3 s", "closes_delta": 1, "visible_after_press2": False, "errors": 0},
    "C": {"overflowRows_start": "not predicted (about 28 rows against about 496 px)", "overflowRows_used": ">= 1",
          "wheel_plus_r1": True, "scrollY_after_plus": "> 0 (min(3 lines, overflowPx))", "wheel_minus_r1": True,
          "scrollY_after_minus": 0, "pixels": "unmeasured"},
    "D": {"renders_delta": 1, "errors_delta": 0, "panel.height": "nrView.y + nrView.height",
          "window.height": "panel.y + panel.height", "wheel": "r1 true and scrollY > 0 when the rows overflow, then 0",
          "onTabTornOff": "unmeasured (two UI-table arguments)"},
    "E": {"server_tps": f"within 0.5/s of {X183B_TICKS} ({X183B_RUN})", "client_tps": "> 0"},
    "Z": {"reconcile.count": 0, "reconcile.landed": 0, "store.failures": 0, "mod_error": "none"},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(),
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_DeclaredFood"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "baseline": {"tick_run": X183B_RUN, "tick_path": "interface.json verdicts.H.observed.server_tps",
                 "ticks": list(X183B_TICKS)},
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool))
                  and k not in ("REPO", "LUA_DIR", "MOD_DIR")},
    "predictions": PRED,
    "deviations": [
        "The arms run S0, A, BC, D, E, Z: the race first (ruling 12, this plan's first live arm), then A3 removes the "
        "trait on the server so the key press and the wheel read the panel at the Bands level 2 the amendments name.",
        "The paired list reads are back-to-back bus reads (client, then server) for READ_S seconds: each read takes "
        "about 0.5 s, so a pair is about 1 s and a client read lands about every 1 s, not every 0.5 s.",
        "witness.chain's grammar takes zero- or one-literal-argument getters and no enum, so the list is read as "
        "getCharacterTraits.getKnownTraits.size (and its string form at the arrival), not through hasTrait(enum).",
        "lua.global indexes by string only, so the panel instance's scrollY and overflowPx (numeric key 0) are read "
        "through client lua.setpath's `before`: a write of 0, then at once a write of the read value back.",
        "If the start position fits every level-2 row (overflowRows 0) the panel is moved to y 400 through lua.callm "
        "setY and re-fitted by one requestMirror rebuild, so the wheel has rows to scroll; it is moved back after.",
        "The tab's onTabTornOff(view, window) takes two UI tables, which lua.callm's scalar arguments cannot pass: "
        "the tear-off stays unmeasured.",
        "The tab's render is called outside the UI frame (from the bus handler); the draw calls it makes there are the "
        "engine's to accept or raise, and a raise is caught by the tab's own pcall and counted in tab.stats.errors.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["the admin character without NUTRITIONIST after A3 (server and client)",
                                        "the panel closed at y 200"]},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "mod_error_checks": [],
}


def grep_noecho(log, rx, limit):
    """grep_file with the bus's echo lines dropped BEFORE the limit counts (a limit is a break, not a window): returns
    (kept lines, echo lines skipped)."""
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
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    v = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    """A reply kept whole plus its walls."""
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def gread(side, name, tag):
    """One lua.global read, kept whole: {resolved, type, value | keyCount | failedAt, wall}."""
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "wall": r["wall_before"], "wall_after": r["wall_after"], "resolved": a.get("resolved"),
           "type": a.get("type")}
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


def parked():
    return bool(clients) and "lua_error" in getattr(clients[0], "seen", {})


def stats(surface, keys, tag):
    return {k: gread(client, f"{NR}.client.{surface}.stats.{k}", f"{tag}_{surface}_{k}") for k in keys}


def sval(snap, k):
    return num(val((snap or {}).get(k)))


def received(tag):
    return num(val(gread(client, f"{NR}.client.received", tag)))


def csize(tag):
    r = step(tag, client, "witness.chain", CHAIN_SIZE)
    a = keep(r)
    a["size"] = num(a.get("value"))
    return a


def ssize(tag):
    r = step(tag, server, "witness.chain", f"{USER} {CHAIN_SIZE}")
    a = keep(r)
    a["size"] = num(a.get("value"))
    return a


def clist(tag):
    return keep(step(tag, client, "witness.chain", CHAIN_LIST))


def slist(tag):
    return keep(step(tag, server, "witness.chain", f"{USER} {CHAIN_LIST}"))


def poll_received(before, tag):
    rows, end, i = [], time.time() + POLL_CAP_S, 0
    while True:
        row = gread(client, f"{NR}.client.received", f"{tag}_p{i}")
        rows.append(row)
        i += 1
        v = num(val(row))
        if before is not None and v is not None and v > before:
            return rows, row["wall"]
        if time.time() >= end:
            return rows, None
        time.sleep(POLL_S)


def setpath_read(path_, tag):
    """Reads a client Lua field under a numeric key through lua.setpath's `before`: a write of 0, then the read value
    written straight back. Returns {before, restored, first, second}."""
    first = keep(step(f"{tag}_w0", client, "lua.setpath", f"{path_} 0"))
    before = first.get("before")
    restored = None
    if first.get("ok") and before is not None and before != "nil":
        restored = keep(step(f"{tag}_wb", client, "lua.setpath", f"{path_} {before}"))
    return {"before": before, "value": num(before), "first": first, "restored": restored}


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
        why.append({"client": "lua_error seen (parked in the debugger)"})
    counts = {}
    for s in ("panel", "view", "tab"):
        e = num(val(gread(client, f"{NR}.client.{s}.stats.errors", f"chk_{after}_{s}_err")))
        counts[s] = e
        if (e or 0) > 0:
            why.append({f"{s}.errors": e,
                        f"{s}.lastError": val(gread(client, f"{NR}.client.{s}.lastError", f"chk_{after}_{s}_le"))})
    ne = num(val(gread(server, f"{NR}.server.nutrients.stats.errors", f"chk_{after}_nerr")))
    re_ = num(val(gread(server, f"{NR}.server.reconcile.stats.errors", f"chk_{after}_rerr")))
    if (ne or 0) > 0:
        why.append({"server.nutrients.errors": ne,
                    "lastError": val(gread(server, f"{NR}.server.nutrients.lastError", f"chk_{after}_nle"))})
    if (re_ or 0) > 0:
        why.append({"server.reconcile.errors": re_,
                    "lastError": val(gread(server, f"{NR}.server.reconcile.lastError", f"chk_{after}_rle"))})
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


def store_reads(tag):
    R = {"moddata": keep(step(f"{tag}_md", server, "witness.moddata",
                              f"global:{STORE} {USER}.v {USER}.username {USER}.reconcile.count {USER}.resets")),
         "store_stats": {k: gread(server, f"{NR}.server.store.stats.{k}", f"{tag}_ss_{k}") for k in STORE_KEYS},
         "reconcile_stats": {k: gread(server, f"{NR}.server.reconcile.stats.{k}", f"{tag}_rs_{k}") for k in RC_KEYS},
         "records_count": gread(server, f"{NR}.server.store.records.{USER}.reconcile.count", f"{tag}_rc"),
         "records_v": gread(server, f"{NR}.server.store.records.{USER}.v", f"{tag}_rv")}
    return R


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["tk_version"] = {"client": gread(client, "TK.version", "S0_tkv_c"), "server": gread(server, "TK.version", "S0_tkv_s")}
    P["nr_version"] = {"client": gread(client, f"{NR}.version", "S0_v_c"), "server": gread(server, f"{NR}.version", "S0_v_s")}
    P["view_level"] = gread(client, f"{NR}.client.view.level", "S0_level")
    P["view_optionLevel"] = gread(client, f"{NR}.client.view.optionLevel", "S0_optlevel")
    P["view_hasTrait"] = gread(client, f"{NR}.client.view.hasTrait", "S0_hastrait")
    P["server_visibilityMode"] = gread(server, f"{NR}.server.options.visibilityMode", "S0_s_vis")
    P["client_sandbox_NR"] = gread(client, "SandboxVars.NR.VisibilityMode", "S0_c_sbx")
    P["received"] = gread(client, f"{NR}.client.received", "S0_received")
    P["key"] = lcall(client, f"{NR}.client.modOptions.key", "S0_key")
    P["store_VERSION"] = gread(server, f"{NR}.kernel.store.VERSION", "S0_VERSION")
    P["store_get"] = lcall(server, f"{NR}.server.store.get {USER}", "S0_get")
    P["store"] = store_reads("S0")
    P["view_stats"] = stats("view", VIEW_KEYS, "S0")
    P["panel_stats"] = stats("panel", PANEL_KEYS, "S0")
    P["tab_stats"] = stats("tab", TAB_KEYS, "S0")
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["server_errors_at_S0"] = list(server.errors)
    P["mod_error"] = mod_error("S0")
    P["parked"] = parked()


def view_reads(tag):
    return {"hasTrait": gread(client, f"{NR}.client.view.hasTrait", f"{tag}_has"),
            "level": gread(client, f"{NR}.client.view.level", f"{tag}_lvl"),
            "traitReads": gread(client, f"{NR}.client.view.stats.traitReads", f"{tag}_tr"),
            "rebuilds": gread(client, f"{NR}.client.view.stats.rebuilds", f"{tag}_rb")}


def race_leg(L, tag, action):
    """One leg: the before reads, the action, READ_S of paired size reads, the request, the arrival reads."""
    L["before"] = {"client_size": csize(f"{tag}_c0"), "server_size": ssize(f"{tag}_s0"),
                   "client_list": clist(f"{tag}_cl0"), "view": view_reads(f"{tag}_v0")}
    L["action"] = action()
    t_act = time.time()
    L["action_wall_after"] = wall()
    pairs, i = [], 0
    while time.time() - t_act < READ_S:
        c = csize(f"{tag}_c{i + 1}")
        s = ssize(f"{tag}_s{i + 1}")
        pairs.append({"i": i, "client": c, "server": s,
                      "client_since_action_s": round(c["wall"] - L["action_wall_after"], 3),
                      "server_since_action_s": round(s["wall"] - L["action_wall_after"], 3)})
        i += 1
    L["pairs"] = pairs
    rb = received(f"{tag}_rcv0")
    L["received_before"] = rb
    L["request"] = lcall(client, f"{NR}.client.requestMirror", f"{tag}_req")
    L["received_poll"], L["arrival_wall"] = poll_received(rb, f"{tag}_rcv")
    L["at_arrival"] = {"view": view_reads(f"{tag}_va"), "received": received(f"{tag}_rcv1"),
                       "client_size": csize(f"{tag}_ca"), "client_list": clist(f"{tag}_cla"),
                       "server_size": ssize(f"{tag}_sa"), "server_list": slist(f"{tag}_sla")}
    L["mod_error"] = mod_error(tag)


def phase_A():
    P = out["phases"]["A"] = {}
    P["A1"] = {}
    race_leg(P["A1"], "A1", lambda: keep(step("A1_add", client, "trait.local", f"{TRAIT} add")))
    persist()
    P["A2"] = {}

    def a2():
        rm = keep(step("A2_local_rm", client, "trait.local", f"{TRAIT} remove"))
        push = keep(step("A2_push", server, "trait.add.push", f"{USER} {TRAIT}"))
        return {"local_remove": rm, "push": push}
    race_leg(P["A2"], "A2", a2)
    persist()
    P["A3"] = {}

    def a3():
        rm = keep(step("A3_set_rm", server, "trait.set", f"{USER} {TRAIT} remove"))
        push = keep(step("A3_push", server, "trait.push", USER))
        return {"set_remove": rm, "push": push}
    race_leg(P["A3"], "A3", a3)
    P["parked"] = parked()


def visible(tag):
    return mcall(client, f"{INST} getIsVisible", tag)


def phase_BC():
    P = out["phases"]["BC"] = {}
    B = P["B"] = {}
    B["before"] = stats("panel", PANEL_KEYS, "B0")
    B["visible_before"] = visible("B0_vis")
    B["level"] = gread(client, f"{NR}.client.view.level", "B0_lvl")
    rb = received("B1_rcv0")
    B["received_before1"] = rb
    B["press1"] = keep(step("B1_press", client, "event.trigger", f"OnKeyPressed {KEY}"))
    B["received_poll1"], B["arrival_wall1"] = poll_received(rb, "B1_rcv")
    B["after1"] = stats("panel", PANEL_KEYS, "B1")
    B["visible_after1"] = visible("B1_vis")
    B["mod_error1"] = mod_error("B1")
    if parked():
        return
    # C: the wheel inside the same open period
    C = P["C"] = {"moved": False}
    time.sleep(SETTLE_S)
    C["level"] = gread(client, f"{NR}.client.view.level", "C_lvl")
    C["rows"] = gread(client, f"{NR}.client.view.rows", "C_rows")
    C["overflowRows_start"] = gread(client, f"{NR}.client.view.stats.overflowRows", "C_over0")
    C["height_start"] = mcall(client, f"{INST} getHeight", "C_h0")
    C["y_start"] = mcall(client, f"{INST} getY", "C_y0")
    if (num(val(C["overflowRows_start"])) or 0) <= 0:
        C["moved"] = True
        C["setY"] = mcall(client, f"{INST} setY {MOVE_Y}", "C_setY")
        rb2 = received("C_rcv0")
        C["refit_request"] = lcall(client, f"{NR}.client.requestMirror", "C_req")
        C["refit_poll"], C["refit_arrival_wall"] = poll_received(rb2, "C_rcv")
        time.sleep(SETTLE_S)
        C["overflowRows_moved"] = gread(client, f"{NR}.client.view.stats.overflowRows", "C_over1")
        C["height_moved"] = mcall(client, f"{INST} getHeight", "C_h1")
        C["y_moved"] = mcall(client, f"{INST} getY", "C_y1")
    C["overflowPx"] = setpath_read(f"{INST}.overflowPx", "C_opx")
    C["scrollY0"] = setpath_read(f"{INST}.scrollY", "C_sy0")
    C["wheel_plus"] = mcall(client, f"{INST} onMouseWheel 1", "C_wp")
    C["scrollY1"] = setpath_read(f"{INST}.scrollY", "C_sy1")
    C["wheel_minus"] = mcall(client, f"{INST} onMouseWheel -1", "C_wm")
    C["scrollY2"] = setpath_read(f"{INST}.scrollY", "C_sy2")
    C["fits"] = gread(client, f"{NR}.client.panel.stats.fits", "C_fits")
    if C["moved"]:
        C["setY_back"] = mcall(client, f"{INST} setY {START_Y}", "C_setYb")
    C["mod_error"] = mod_error("C")
    if parked():
        return
    # B2: the second press closes
    B["press2"] = keep(step("B2_press", client, "event.trigger", f"OnKeyPressed {KEY}"))
    time.sleep(0.5)
    B["after2"] = stats("panel", PANEL_KEYS, "B2")
    B["visible_after2"] = visible("B2_vis")
    B["mod_error2"] = mod_error("B2")
    P["parked"] = parked()


def tab_reads(tag):
    return {"stats": stats("tab", TAB_KEYS, tag),
            "lastError": gread(client, f"{NR}.client.tab.lastError", f"{tag}_le"),
            "window_height": gread(client, f"{TAB}.height", f"{tag}_wh"),
            "window_visible": mcall(client, f"{TAB} getIsVisible", f"{tag}_wv"),
            "panel_y": gread(client, f"{TAB}.panel.y", f"{tag}_py"),
            "panel_height": gread(client, f"{TAB}.panel.height", f"{tag}_ph"),
            "view_y": gread(client, f"{TAB}.nrView.y", f"{tag}_vy"),
            "view_height": gread(client, f"{TAB}.nrView.height", f"{tag}_vh"),
            "view_scrollY": gread(client, f"{TAB}.nrView.scrollY", f"{tag}_vs")}


def phase_D():
    P = out["phases"]["D"] = {}
    P["instance"] = gread(client, TAB, "D_inst")
    P["nrView"] = gread(client, f"{TAB}.nrView", "D_view")
    P["before"] = tab_reads("D0")
    P["render"] = mcall(client, f"{TAB}.nrView render", "D_render")
    time.sleep(0.5)
    P["after"] = tab_reads("D1")
    P["wheel_plus"] = mcall(client, f"{TAB}.nrView onMouseWheel 1", "D_wp")
    P["scrollY1"] = gread(client, f"{TAB}.nrView.scrollY", "D_sy1")
    P["wheel_minus"] = mcall(client, f"{TAB}.nrView onMouseWheel -1", "D_wm")
    P["scrollY2"] = gread(client, f"{TAB}.nrView.scrollY", "D_sy2")
    P["tornOff"] = "unmeasured: onTabTornOff(view, window) takes two UI tables; lua.callm passes scalars only"
    P["mod_error"] = mod_error("D")
    P["parked"] = parked()


def phase_E():
    P = out["phases"]["E"] = {"windows": []}
    for i in range(TICK_N):
        after = time.time()
        arm_s = ack(step(f"E{i}_arm_s", server, "tick.rate", str(TICK_S)))
        arm_c = ack(step(f"E{i}_arm_c", client, "tick.rate", str(TICK_S)))
        w = {"i": i, "arm_server": arm_s, "arm_client": arm_c}
        for side, node, arm in (("server", server, arm_s), ("client", client, arm_c)):
            res = None
            if arm.get("armed"):
                try:
                    res = node.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 25, after=after)
                except (RuntimeError, TimeoutError, OSError) as e:
                    res = {"error": f"{type(e).__name__}: {e}"}
            w[f"result_{side}"] = res
        P["windows"].append(w)
        persist()


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["view_stats"] = stats("view", VIEW_KEYS, "Z")
    P["panel_stats"] = stats("panel", PANEL_KEYS, "Z")
    P["tab_stats"] = stats("tab", TAB_KEYS, "Z")
    P["view_level"] = gread(client, f"{NR}.client.view.level", "Z_level")
    P["received"] = gread(client, f"{NR}.client.received", "Z_received")
    P["store"] = store_reads("Z")
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["mod_error"] = mod_error("Z")


def body():
    run_phase("S0", phase_S0)
    if parked():
        out["abort"] = "client parked in the debugger by first sight: a mod file raised at boot"
        return
    run_phase("A", phase_A)
    if parked():
        out["abort"] = "client parked in the debugger during the race arm"
        return
    run_phase("BC", phase_BC)
    if parked():
        out["abort"] = "client parked in the debugger during the key press or wheel arm"
        return
    run_phase("D", phase_D)
    if parked():
        out["abort"] = "client parked in the debugger during the tab arm"
        return
    run_phase("E", phase_E)
    run_phase("Z", phase_Z)


# ---------------------------------------------------------------- grading
def tps(res):
    return (res or {}).get("ticksPerSecond") if isinstance(res, dict) else None


def leg_obs(L):
    pre = (L.get("before") or {}).get("client_size", {}).get("size")
    spre = (L.get("before") or {}).get("server_size", {}).get("size")
    pairs = L.get("pairs") or []
    cs = [(p["client"].get("size"), p["client_since_action_s"]) for p in pairs]
    ss = [(p["server"].get("size"), p["server_since_action_s"]) for p in pairs]
    A = L.get("at_arrival") or {}
    V = A.get("view") or {}
    return {"client_size_before": pre, "server_size_before": spre, "client_sizes": cs, "server_sizes": ss,
            "request_r1": (L.get("request") or {}).get("r1"), "request_wall": (L.get("request") or {}).get("wall"),
            "received_before": L.get("received_before"), "received_at_arrival": A.get("received"),
            "arrival_wall": L.get("arrival_wall"),
            "client_size_at_arrival": (A.get("client_size") or {}).get("size"),
            "client_list_at_arrival": (A.get("client_list") or {}).get("value"),
            "server_size_at_arrival": (A.get("server_size") or {}).get("size"),
            "server_list_at_arrival": (A.get("server_list") or {}).get("value"),
            "hasTrait": val(V.get("hasTrait")), "level": num(val(V.get("level"))),
            "traitReads": [num(val(((L.get("before") or {}).get("view") or {}).get("traitReads"))),
                           num(val(V.get("traitReads")))],
            "rebuilds": [num(val(((L.get("before") or {}).get("view") or {}).get("rebuilds"))),
                         num(val(V.get("rebuilds")))]}


def grade_all():
    ph = out["phases"]
    S = ph.get("S0") or {}
    if S:
        st = S.get("store") or {}
        md = ((st.get("moddata") or {}).get("values") or {})
        logs = out.get("logs") or {}
        mig = logs.get("migration_lines")
        obs = {"server_error_count": out.get("server_error_count"), "client_lua_error": out.get("client_lua_error"),
               "view.level": num(val(S.get("view_level"))), "view.optionLevel": num(val(S.get("view_optionLevel"))),
               "view.hasTrait": val(S.get("view_hasTrait")),
               "server options.visibilityMode": num(val(S.get("server_visibilityMode"))),
               "client SandboxVars.NR.VisibilityMode": val(S.get("client_sandbox_NR")),
               "received": num(val(S.get("received"))), "key": (S.get("key") or {}).get("r1"),
               "kernel.store.VERSION": num(val(S.get("store_VERSION"))),
               "store.get r1_keys": (S.get("store_get") or {}).get("r1_keys"),
               "record.v": num(md.get(f"{USER}.v")), "record.username": md.get(f"{USER}.username"),
               "record.reconcile.count": num(md.get(f"{USER}.reconcile.count")),
               "records.v (lua.global)": num(val(st.get("records_v"))),
               "records.reconcile.count (lua.global)": num(val(st.get("records_count"))),
               "store.stats": {k: sval(st.get("store_stats"), k) for k in STORE_KEYS},
               "reconcile.stats": {k: sval(st.get("reconcile_stats"), k) for k in RC_KEYS},
               "migration_lines": mig}
        ss, rs = obs["store.stats"], obs["reconcile.stats"]
        bands = (obs["view.level"] == 2 and obs["view.optionLevel"] == 2 and obs["view.hasTrait"] is False
                 and obs["server options.visibilityMode"] == 2)
        store_ok = (obs["kernel.store.VERSION"] == 2 and obs["record.v"] == 2 and obs["record.username"] == USER
                    and ss.get("created") == 1 and ss.get("migrations") == 0 and ss.get("failures") == 0
                    and (obs["record.reconcile.count"] or 0) == 0 and rs.get("errors") == 0
                    and mig is not None and len(mig) == 0)
        load_ok = (obs["server_error_count"] == 0 and obs["client_lua_error"] is False
                   and (obs["received"] or 0) >= 1)
        grade("S0", PRED["S0"], obs, "as_predicted" if (bands and store_ok and load_ok) else "falsified",
              "a server error or parked client, a level / option other than 2, a record version other than 2, a "
              "migration, a store failure, a reconcile count above 0 or a migration line",
              {"bands_verdict": "as_predicted" if bands else "falsified",
               "store_verdict": "as_predicted" if store_ok else "falsified",
               "load_verdict": "as_predicted" if load_ok else "falsified"})
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "no first-sight reads")
    A = ph.get("A") or {}
    if A.get("A1"):
        o = leg_obs(A["A1"])
        act = A["A1"].get("action") or {}
        o["add_reply"] = {k: act.get(k) for k in ("ok", "enumFound", "before", "after", "listBefore", "listAfter")}
        pre = o["client_size_before"]
        poll = [s for s, _ in o["client_sizes"] if s is not None]
        lost_reads = [(s, t) for s, t in o["client_sizes"] if s is not None and pre is not None and s <= pre]
        held_all = (pre is not None and len(poll) > 0 and all(s > pre for s in poll)
                    and o["client_size_at_arrival"] is not None and o["client_size_at_arrival"] > pre)
        o["first_lost_since_add_s"] = lost_reads[0][1] if lost_reads else None
        o["server_size_moved"] = any(s is not None and s != o["server_size_before"] for s, _ in o["server_sizes"])
        if o["arrival_wall"] is None or o["hasTrait"] is None:
            branch, verdict = "UNMEASURED", "unmeasured"
        elif lost_reads and o["hasTrait"] is False:
            branch = "LOST"
        elif held_all and o["hasTrait"] is False:
            branch = "MISSED"
        elif held_all and o["hasTrait"] is True:
            branch = "NEITHER"
        else:
            branch = "OTHER"
        o["branch"] = branch
        if branch != "UNMEASURED":
            verdict = "as_predicted" if (branch == "LOST" and o["level"] == 2 and not o["server_size_moved"]) \
                else "falsified"
        grade("A1", PRED["A1"], o, verdict,
              "the list holding the add through the arrival, the server's list moving, or hasTrait true",
              {"branch": branch})
    else:
        grade("A1", PRED["A1"], None, "unmeasured", "leg A1 not run")
    for leg, want_has, want_lvl in (("A2", True, 3), ("A3", False, 2)):
        if A.get(leg):
            o = leg_obs(A[leg])
            act = A[leg].get("action") or {}
            if leg == "A2":
                o["push_traitList"] = (act.get("push") or {}).get("traitList")
                o["local_remove"] = {k: (act.get("local_remove") or {}).get(k) for k in ("ok", "before", "after")}
            else:
                o["set_remove_traitList"] = (act.get("set_remove") or {}).get("traitList")
                o["push_traitList"] = (act.get("push") or {}).get("traitList")
            pre = o["client_size_before"]
            first = None
            for s, t in o["client_sizes"]:
                if s is not None and pre is not None and ((s > pre) if want_has else (s < pre)):
                    first = t
                    break
            o["first_changed_since_action_s"] = first
            if o["arrival_wall"] is None or o["hasTrait"] is None:
                grade(leg, PRED[leg], o, "unmeasured", "no mirror arrival or no trait read")
            else:
                ok = o["hasTrait"] is want_has and o["level"] == want_lvl and first is not None
                grade(leg, PRED[leg], o, "as_predicted" if ok else "falsified",
                      "the client list not changing within the read window, or hasTrait / level other than predicted")
        else:
            grade(leg, PRED[leg], None, "unmeasured", f"leg {leg} not run")
    BC = ph.get("BC") or {}
    B = BC.get("B") or {}
    if B.get("after1"):
        b0, b1, b2 = B.get("before") or {}, B.get("after1") or {}, B.get("after2") or {}
        obs = {"level": num(val(B.get("level"))),
               "keyPresses": [sval(b0, "keyPresses"), sval(b1, "keyPresses"), sval(b2, "keyPresses")],
               "opens": [sval(b0, "opens"), sval(b1, "opens"), sval(b2, "opens")],
               "closes": [sval(b0, "closes"), sval(b1, "closes"), sval(b2, "closes")],
               "requests": [sval(b0, "requests"), sval(b1, "requests"), sval(b2, "requests")],
               "errors": [sval(b0, "errors"), sval(b1, "errors"), sval(b2, "errors")],
               "visible": [(B.get("visible_before") or {}).get("r1"), (B.get("visible_after1") or {}).get("r1"),
                           (B.get("visible_after2") or {}).get("r1")],
               "press_replies": [{k: (B.get(p) or {}).get(k) for k in ("ok", "event", "nargs", "err")}
                                 for p in ("press1", "press2")],
               "received_before1": B.get("received_before1"), "arrival_wall1": B.get("arrival_wall1"),
               "press1_wall": (B.get("press1") or {}).get("wall")}
        kp, op, cl, rq, vis = obs["keyPresses"], obs["opens"], obs["closes"], obs["requests"], obs["visible"]
        try:
            ok = (kp[0] == 0 and kp[1] == 1 and kp[2] == 2 and op[1] - op[0] == 1 and rq[1] - rq[0] == 1
                  and cl[2] - cl[1] == 1 and vis[0] is False and vis[1] is True and vis[2] is False
                  and B.get("arrival_wall1") is not None and obs["errors"][2] == 0)
        except TypeError:
            ok = False
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified",
              "a press not counted, the panel not opening then closing, no mirror within 3 s, or a panel error",
              {"engine_key_path": "unmeasured (triggerEvent reaches the Lua handlers only)"})
    else:
        grade("B", PRED["B"], None, "unmeasured", "arm B not run")
    C = BC.get("C") or {}
    if C:
        over0 = num(val(C.get("overflowRows_start")))
        over1 = num(val(C.get("overflowRows_moved"))) if C.get("moved") else over0
        obs = {"level": num(val(C.get("level"))), "rows": (C.get("rows") or {}).get("keyCount"),
               "overflowRows_start": over0, "moved": C.get("moved"), "overflowRows_used": over1,
               "height_start": (C.get("height_start") or {}).get("r1"), "y_start": (C.get("y_start") or {}).get("r1"),
               "height_moved": (C.get("height_moved") or {}).get("r1"), "y_moved": (C.get("y_moved") or {}).get("r1"),
               "overflowPx": (C.get("overflowPx") or {}).get("value"),
               "scrollY": [(C.get(k) or {}).get("value") for k in ("scrollY0", "scrollY1", "scrollY2")],
               "wheel_plus": {k: (C.get("wheel_plus") or {}).get(k) for k in ("ok", "r1", "err", "failedAt", "type")},
               "wheel_minus": {k: (C.get("wheel_minus") or {}).get(k) for k in ("ok", "r1", "err", "failedAt", "type")}}
        sy = obs["scrollY"]
        if (over1 or 0) <= 0:
            grade("C", PRED["C"], obs, "unmeasured", "no overflow to scroll even after the move")
        else:
            ok = (obs["wheel_plus"]["r1"] is True and (sy[1] or 0) > 0 and obs["wheel_minus"]["r1"] is True
                  and sy[2] == 0)
            grade("C", PRED["C"], obs, "as_predicted" if ok else "falsified",
                  "the wheel not taken with overflow present, scrollY not moving, or not returning to 0",
                  {"pixels": "unmeasured (no on-screen read of the clipped rows)"})
    else:
        grade("C", PRED["C"], None, "unmeasured", "arm C not run")
    D = ph.get("D") or {}
    if D.get("after"):
        b, a = D.get("before") or {}, D.get("after") or {}

        def g(R, k):
            return num(val(R.get(k)))
        obs = {"instance_type": (D.get("instance") or {}).get("type"), "nrView_type": (D.get("nrView") or {}).get("type"),
               "render": {k: (D.get("render") or {}).get(k) for k in ("ok", "err", "failedAt", "type")},
               "renders": [sval(b.get("stats"), "renders"), sval(a.get("stats"), "renders")],
               "errors": [sval(b.get("stats"), "errors"), sval(a.get("stats"), "errors")],
               "lastError": val(a.get("lastError")),
               "window_height": [g(b, "window_height"), g(a, "window_height")],
               "window_visible": (b.get("window_visible") or {}).get("r1"),
               "panel_y": [g(b, "panel_y"), g(a, "panel_y")], "panel_height": [g(b, "panel_height"), g(a, "panel_height")],
               "view_y": [g(b, "view_y"), g(a, "view_y")], "view_height": [g(b, "view_height"), g(a, "view_height")],
               "wheel_plus": {k: (D.get("wheel_plus") or {}).get(k) for k in ("ok", "r1", "err")},
               "wheel_minus": {k: (D.get("wheel_minus") or {}).get(k) for k in ("ok", "r1", "err")},
               "scrollY": [num(val(D.get("scrollY1"))), num(val(D.get("scrollY2")))]}
        try:
            h_ok = (obs["panel_height"][1] == obs["view_y"][1] + obs["view_height"][1]
                    and obs["window_height"][1] == obs["panel_y"][1] + obs["panel_height"][1])
        except TypeError:
            h_ok = False
        try:
            r_ok = obs["renders"][1] - obs["renders"][0] == 1 and obs["errors"][1] - obs["errors"][0] == 0
        except TypeError:
            r_ok = None
        obs["height_reasserted"] = h_ok
        if r_ok is None:
            grade("D", PRED["D"], obs, "unmeasured", "a tab count did not read")
        else:
            grade("D", PRED["D"], obs, "as_predicted" if (r_ok and h_ok) else "falsified",
                  "no render counted, a tab error, or the heights not re-asserted",
                  {"render_verdict": "as_predicted" if r_ok else "falsified",
                   "height_verdict": "as_predicted" if h_ok else "falsified",
                   "tornOff": "unmeasured (two UI-table arguments)"})
    else:
        grade("D", PRED["D"], None, "unmeasured", "arm D not run")
    E = ph.get("E") or {}
    ws = E.get("windows") or []
    st = [tps(w.get("result_server")) for w in ws]
    ct = [tps(w.get("result_client")) for w in ws]
    if not any(v is not None for v in st + ct):
        grade("E", PRED["E"], None, "unmeasured", "no tick-rate result")
    else:
        sn = [v for v in st if isinstance(v, (int, float))]
        base = sum(X183B_TICKS) / len(X183B_TICKS)
        obs = {"server_tps": st, "client_tps": ct, "server_ratio_to_x183b": [v / base for v in sn]}
        ok = len(sn) == TICK_N and all(abs(v - base) < 0.5 for v in sn) and all(
            isinstance(v, (int, float)) and v > 0 for v in ct)
        grade("E", PRED["E"], obs, "as_predicted" if ok else "falsified",
              "a server window more than 0.5/s off x183b's mean, or a client window absent or zero")
    Z = ph.get("Z") or {}
    if Z:
        st = Z.get("store") or {}
        md = ((st.get("moddata") or {}).get("values") or {})
        obs = {"record.reconcile.count": num(md.get(f"{USER}.reconcile.count")),
               "records.reconcile.count (lua.global)": num(val(st.get("records_count"))),
               "reconcile.stats": {k: sval(st.get("reconcile_stats"), k) for k in RC_KEYS},
               "store.stats": {k: sval(st.get("store_stats"), k) for k in STORE_KEYS},
               "mod_error": (Z.get("mod_error") or []), "view_level": num(val(Z.get("view_level")))}
        rs, ss = obs["reconcile.stats"], obs["store.stats"]
        ok = ((obs["record.reconcile.count"] or 0) == 0 and rs.get("landed") == 0 and ss.get("failures") == 0
              and not obs["mod_error"])
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified",
              "a reconciled intake on an idle admin, a store failure or a mod error")
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
    client, _ = make_client(run_dir, USER, server, rec_fx)
    out["client_start_wall"] = wall()
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                   "client_markers_s": dict(getattr(client, "seen", {})),
                   "server_started_wall": out.get("server_started_wall"),
                   "client_start_wall": out.get("client_start_wall"),
                   "session_ready_wall": out.get("session_ready_wall")}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)), "client": sorted(set(client.mods_not_found))}
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
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        out["client_seen"] = dict(getattr(clients[0], "seen", {})) if clients else None
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
            raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
            mod_lines, _ = grep_noecho(server.log_path, MOD_LINE_RX, LOG_LIMIT)
            out["logs"] = {"server": raw,
                           "server_echo_lines_excluded": echoed,
                           "mod_lines": mod_lines,
                           "migration_lines": [ln for ln in mod_lines if MIGRATE_RX.search(ln)],
                           "reconcile_lines": [ln for ln in mod_lines if "reconcile:" in ln],
                           "limits": {"log": LOG_LIMIT},
                           "patterns": {"log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern,
                                        "mod": MOD_LINE_RX.pattern, "migrate": MIGRATE_RX.pattern}}
            if clients:
                out["logs"]["client"], out["logs"]["client_echo_lines_excluded"] = grep_noecho(
                    clients[0].console, LOG_RX, LOG_LIMIT)
                out["logs"]["client_mod_lines"], _ = grep_noecho(clients[0].console, MOD_LINE_RX, LOG_LIMIT)
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
                  "branch": (out.get("verdicts", {}).get("A1") or {}).get("branch"),
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
