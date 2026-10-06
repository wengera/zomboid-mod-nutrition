"""x181-moodleframework -- Plan 7 Task 4, gate X29, LIVE. Does MoodleFramework load whole on 42.20.4, does its
MF_Config.lua execute, and does a moodle registered through it render on a dedicated-server client, beside a
widget of the probe's own (ISUIElement:derive + addToUIManager, no framework call)? ONE boot of profile
`x18-moodleframework` (PZTestKit + MoodleFramework by workshop_id 3396446795 + TKX_MF, the probe of ff0e50f /
9de2bc6). The run id prefix is `x181`; ONE artifact `moodleframework.json`. Shape: x172_itempass.py (step,
persist, run_phase, mod_error, both logs grepped, the artifact copied by the driver).

THE LIVE TREE, RE-READ AND DATED BEFORE THE BOOT (2026-10-06 15:22 -0400, `ls -la --time-style=full-iso` and
`find -printf` of D:/SteamLibrary/steamapps/workshop/content/108600/3396446795/mods/MoodleFramework/):
  42.0/    dir mtime 2026-08-12 00:03:05 -- mod.info (232 B, id=MoodleFramework), media/lua/client/MF_Config.lua
           (1848 B, md5 559f9a62eb288ef78e452edfc329e631), MF_ISMoodle.lua (28847 B, md5 7383a3c7...),
           media/lua/shared/Translate/EN/UI.json + UI_EN.txt, two PNGs; files 2026-08-12 00:02.
  42.13/   dir mtime 2026-08-12 00:03:05 -- media/lua/client/MF_ISMoodle.lua only (29255 B, md5 88f12d7f...).
  42.20/   dir mtime 2026-08-15 23:36:11 -- media/lua/client/MF_ISMoodle.lua only (28611 B, md5 c787a70a...,
           FILE mtime 2026-09-07 21:54); NO mod.info and NO MF_Config.lua.
  common/  dir mtime 2026-09-07 21:54:59 -- mod.info (323 B, 2026-09-07 21:54: name=Moodle Framework,
           id=MoodleFramework, versionMin=42.0, modversion=2.8), media/lua/client/MF_Config.lua (1848 B, md5
           559f9a62... -- byte-identical to 42.0/'s), MF_ISMoodle.lua (28847 B, md5 7383a3c7... = 42.0/'s),
           the same translation tree and PNGs.
THE RESOLVER'S PICK (#1558, #0825): the newest 42[.x] folder at or below 42.20.4 is `42.20/`, so its
MF_ISMoodle.lua wins the same-path collision and `common/` supplies everything 42.20/ does not ship -- the
MF_Config.lua that sets `MF.key = "MoodleFramework"` (common/media/lua/client/MF_Config.lua:4) and defines
MF.hasBorder / MF.hasBackground / MF.hasBGColor, which 42.20/'s render() calls. 42.20/ ships no mod.info, so
#1558's chain reads common/mod.info (id=MoodleFramework, 2026-09-07) -- the facts page's "its mod.info sits
in 42.0/" (#1614) predates the common/mod.info this tree now carries: a drift noted here, not fixed. Leg (ii)
is therefore ALSO a reading of the version-folder resolution: MF.key non-nil on the client = common/'s
config file executed beside 42.20/'s moodle file.

LEGS (experiments.md X29; the amendments' order):
  F  first sight: TKX_MF.detected / created / moodleFound / errors / lastError / ownOnUI / moodlesUI and
     lua.global TKX_MF.moodle (a table) -- the precondition of every later write (T1 reviewer warning b).
  (i)   the server console's `loading MoodleFramework` line (limit 4 = 2 x the predicted 1) and the client's
        (limit 8 = 2 x the predicted 2, the client loads its mods twice as x172's console shows); client
        lua.global MF (table), MF.createMoodle (function), MF.getMoodle (function); server lua.global MF
        and MF.createMoodle (unresolved = nil: #2536's missing MP surface).
  (ii)  client lua.global MF.key ("MoodleFramework"), TKX_MF.cfgKey (same, read at OnGameBoot),
        MF.hasBorder / MF.hasBackground / MF.overrideGray (functions only MF_Config.lua defines); server MF.key.
  (iii) the control then the render: client moddata.set TKX_mf 0.5 -> 3 s -> TKX_MF.level / gbn / onUI /
        lastSet, renders and ownRenders read twice 3 s apart; moddata.set TKX_mf 0.95 -> 3 s -> the same
        reads twice 3 s apart, plus the moodle instance's own fields (addedToUIManager, x, y, width, height)
        and the wrap sentinel TKX_MF_Wrapped; then moddata.set TKX_mf 0.5 again (the back-off: the widget
        leaves the UI manager, renders static again).
  X  the exposure fact: client lua.global MoodlesUI, MoodlesUI.getInstance, TKX_MF.moodlesUI and the stack
     box TKX_MF.stackBox.x/.y/.w/.h (read at OnCreatePlayer and again inside apply).
  L  the harness smoke test of 2f0d3d7 (CLAUDE.md s5): client and server `lua.call getTimestampMs` (zero
     args), client `lua.call MF.getMoodle TKX 0` (two args, a table return -> r1_keys), client
     `lua.call MoodlesUI.getInstance` (a userdata return -> r1_type); client `lua.setpath
     TKX_MF.setpathSmoke 7` then lua.global read back. Their reply shapes are recorded raw.
  T  tick.rate 20 armed on the server and on the client in the same window (one window, both sides).

PREDICTIONS (written before the boot; graded in `verdicts` with as_predicted / falsified / trivial /
unmeasured):
  F    detected true, created true, moodleFound true, errors 0, ownOnUI true, TKX_MF.moodle a table.
  i    server loading-line count 1, client 2; client MF table, MF.createMoodle function; server MF nil.
  ii   client MF.key "MoodleFramework", cfgKey "MoodleFramework", MF.hasBorder function; server MF.key nil.
  iii  control 0.5: level 0, gbn 0, onUI nil-or-false (the flag is never set before the first non-neutral
       value), renders delta 0 across 3 s, ownRenders delta > 0 and the first ownRenders read > 0 (the own
       widget is on the UI manager from OnCreatePlayer); render 0.95: level 4 (>= threasholdGood4 0.9,
       MF_ISMoodle.lua:18's setThresholds), gbn 1, onUI true, renders delta > 0, ownRenders delta > 0;
       back-off 0.5: level 0, gbn 0, onUI false, renders delta 0.
  X    MoodlesUI resolved, TKX_MF.moodlesUI true, stackBox x/y/w/h all numbers (#2509's "if" cleared).
  L    lua.call getTimestampMs ok with a numeric r1 on both sides; MF.getMoodle r1_keys > 0; getInstance
       r1_type userdata; setpath ok with after 7.
  T    server ticks per second near x161b's 10.10 (body.json phases.J.tick.result.ticksPerSecond); client
       ticks per second > 0 (no baseline: the first client tick reading).
The framework raising at boot or in render (a parked -debug client, the lua_error marker) IS the X29 answer:
then the remaining steps are skipped and the session is torn down with both logs grepped.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. The experiments.md row names the
profile `x13-moodleframework.toml`; the shipped profile is `x18-moodleframework.toml` (the plan's naming).
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
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x18-moodleframework"
SESSION = ("Plan 7 Task 4, gate X29: MoodleFramework loads whole (i), MF_Config.lua executes (ii), a framework "
           "moodle and the probe's own ISUIElement render on a dedicated-server client (iii), the MoodlesUI exposure "
           "fact, the lua.call / client lua.setpath smoke test; one boot of x18-moodleframework")
ARTIFACT = "moodleframework.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MF_TREE = "D:/SteamLibrary/steamapps/workshop/content/108600/3396446795/mods/MoodleFramework"
TREE_READ = "2026-10-06 15:22 -0400"
X161B_RUN = "x161b-20261006-065751"
X161B_TICK = 10.104011887072808            # body.json phases.J.tick.result.ticksPerSecond (10 s window)
SETTLE_S = 3.0                             # after each moddata.set, before the first read
GAP_S = 3.0                                # between the two render-count reads
CONTROL_V = "0.5"
RENDER_V = "0.95"
PRED_LEVEL_RENDER = 4
PRED_GBN_RENDER = 1
TICK_S = 20
LOAD_PRED_SERVER = 1
LOAD_PRED_CLIENT = 2
LOAD_LIMIT_SERVER = 4                      # >= 2 x predicted
LOAD_LIMIT_CLIENT = 8
LOAD_RX = re.compile(r"loading MoodleFramework")
LOG_RX = re.compile(r"MoodleFramework|MF_ISMoodle|MF_Config|TKX_MF|TKX|LuaError|STACK TRACE|lua error|"
                    r"attempted index|Exception", re.I)
LOG_LIMIT = 80
MOD_ERR_RX = re.compile(r"MF_ISMoodle|MF_Config|TKX_MF")
TK_FIELDS = ("detected", "created", "moodleFound", "errors", "lastError", "ownOnUI", "moodlesUI", "cfgKey",
             "lastSet", "level", "gbn", "onUI", "renders", "ownRenders")
BOX = ("x", "y", "w", "h")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x181")
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


PRED = {
    "F": {"detected": True, "created": True, "moodleFound": True, "errors": 0, "ownOnUI": True,
          "moodle_type": "table"},
    "i": {"server_loading_lines": LOAD_PRED_SERVER, "client_loading_lines": LOAD_PRED_CLIENT,
          "client_MF": "table", "client_createMoodle": "function", "server_MF": "nil"},
    "ii": {"client_MF.key": "MoodleFramework", "cfgKey": "MoodleFramework", "client_MF.hasBorder": "function",
           "server_MF.key": "nil"},
    "iii_control": {"level": 0, "gbn": 0, "onUI": "nil or false", "renders_delta": 0, "ownRenders_delta": "> 0",
                    "ownRenders_first": "> 0"},
    "iii_render": {"level": PRED_LEVEL_RENDER, "gbn": PRED_GBN_RENDER, "onUI": True, "renders_delta": "> 0",
                   "ownRenders_delta": "> 0"},
    "iii_backoff": {"level": 0, "gbn": 0, "onUI": False, "renders_delta": 0},
    "X": {"MoodlesUI": "resolved", "moodlesUI": True, "stackBox": "x, y, w, h all numbers"},
    "L": {"getTimestampMs": "ok, numeric r1, both sides", "MF.getMoodle": "ok, r1_keys > 0",
          "MoodlesUI.getInstance": "ok, r1_type userdata", "setpath": "ok, after 7"},
    "T": {"server_tps": f"near {X161B_TICK} ({X161B_RUN})", "client_tps": "> 0"},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_MF"),
    "probe_dirty": git_dirty("testing/experiments/TKX_MF")[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "mf_tree": {"path": MF_TREE, "read": TREE_READ, "resolver_pick": "42.20/",
                "folders": {"42.0": "2026-08-12 00:03", "42.13": "2026-08-12 00:03", "42.20": "2026-08-15 23:36",
                            "common": "2026-09-07 21:54"},
                "config_file": "common/media/lua/client/MF_Config.lua (42.20/ ships none)",
                "mod_info": "common/mod.info (42.20/ ships none; 42.0/mod.info also present)"},
    "baseline": {"tick_run": X161B_RUN, "tick_path": "body.json phases.J.tick.result.ticksPerSecond",
                 "tick": X161B_TICK},
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str))
                  and k not in ("REPO", "LUA_DIR")},
    "predictions": PRED,
    "deviations": [
        "The experiments.md X29 row names x13-moodleframework.toml and x131_moodleframework.py; the shipped "
        "profile is x18-moodleframework.toml and the driver x181_moodleframework.py (the plan's naming).",
        "TKX_MF calls MF.createMoodle at OnGameBoot (behind the type test, #2547), not at file scope as the row "
        "words it; the widget of its own is built at OnCreatePlayer, not on the TKX_mf key.",
        "A back-off write (TKX_mf 0.5 after 0.95) is added after the render leg: the widget leaving the UI "
        "manager is the row's control read the other way.",
        "tick.rate is armed on both sides in one 20 s window.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["client player modData key TKX_mf (a string)", "TKX_MF.setpathSmoke"]},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "mod_error_checks": [],
}


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
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


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


def tk_snapshot(tag):
    return {k: gread(client, f"TKX_MF.{k}", f"{tag}_{k}") for k in TK_FIELDS}


def counts(tag):
    return {"renders": gread(client, "TKX_MF.renders", f"{tag}_r"),
            "ownRenders": gread(client, "TKX_MF.ownRenders", f"{tag}_o")}


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
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    if parked():
        why.append({"client": "lua_error seen (parked in the debugger)"})
    tk = gread(client, "TKX_MF.errors", f"chk_{after}_tkerr")
    tle = gread(client, "TKX_MF.lastError", f"chk_{after}_tkle")
    if (num(val(tk)) or 0) > 0 or val(tle) is not None:
        why.append({"TKX_MF.errors": val(tk), "TKX_MF.lastError": val(tle)})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why})
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


# ---------------------------------------------------------------- phases
def phase_F():
    P = out["phases"]["F"] = {}
    P["tk_version"] = gread(client, "TK.version", "F_tkv")
    P["tkx"] = tk_snapshot("F")
    P["moodle"] = gread(client, "TKX_MF.moodle", "F_moodle")
    P["own"] = gread(client, "TKX_MF.own", "F_own")
    P["stackBox_at_create"] = {k: gread(client, f"TKX_MF.stackBox.{k}", f"F_box_{k}") for k in BOX}
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["server_errors_at_F"] = list(server.errors)
    P["mod_error"] = mod_error("F")
    P["parked"] = parked()


def phase_i():
    P = out["phases"]["i"] = {}
    P["client"] = {n: gread(client, n, f"i_c_{n}") for n in ("MF", "MF.createMoodle", "MF.getMoodle",
                                                            "MF.ISMoodle", "MF.MoodlesStorage")}
    P["server"] = {n: gread(server, n, f"i_s_{n}") for n in ("MF", "MF.createMoodle")}
    P["server_loading_lines_now"] = grep_file(server.log_path, LOAD_RX, LOAD_LIMIT_SERVER)
    P["client_loading_lines_now"] = grep_file(client.console, LOAD_RX, LOAD_LIMIT_CLIENT)


def phase_ii():
    P = out["phases"]["ii"] = {}
    P["client"] = {n: gread(client, n, f"ii_c_{n}") for n in ("MF.key", "MF.hasBorder", "MF.hasBackground",
                                                             "MF.hasBGColor", "MF.overrideGray", "MF.color")}
    P["cfgKey"] = gread(client, "TKX_MF.cfgKey", "ii_cfgKey")
    P["server"] = {"MF.key": gread(server, "MF.key", "ii_s_key")}


def write_and_read(label, v):
    P = out["phases"][label] = {"value": v}
    r = step(f"{label}_set", client, "moddata.set", f"TKX_mf {v}")
    P["set_reply"] = r["ack"]
    P["set_wall"] = r["wall_after"]
    time.sleep(SETTLE_S)
    P["state"] = {k: gread(client, f"TKX_MF.{k}", f"{label}_{k}")
                  for k in ("lastSet", "level", "gbn", "onUI", "errors", "lastError")}
    P["moodle_fields"] = {k: gread(client, f"TKX_MF.moodle.{k}", f"{label}_m_{k}")
                          for k in ("addedToUIManager", "x", "y", "width", "height", "name")}
    P["read1"] = counts(f"{label}_1")
    time.sleep(GAP_S)
    P["read2"] = counts(f"{label}_2")
    for k in ("renders", "ownRenders"):
        a, b = num(val(P["read1"][k])), num(val(P["read2"][k]))
        P[f"{k}_delta"] = (b - a) if (a is not None and b is not None) else None
        P[f"{k}_window_s"] = round(P["read2"][k]["wall"] - P["read1"][k]["wall"], 3)
    P["mod_error"] = mod_error(label)
    P["parked"] = parked()


def phase_iii():
    out["phases"]["iii_pre"] = {"moodle": gread(client, "TKX_MF.moodle", "iii_pre_moodle"),
                                "created": gread(client, "TKX_MF.created", "iii_pre_created"),
                                "wrapped": gread(client, "TKX_MF_Wrapped", "iii_pre_wrapped"),
                                "moodle_render": gread(client, "TKX_MF.moodle.render", "iii_pre_mrender")}
    write_and_read("iii_control", CONTROL_V)
    if parked():
        note("client parked after the control write; the render and back-off legs are skipped")
        return
    write_and_read("iii_render", RENDER_V)
    if parked():
        note("client parked after the render write; the back-off leg is skipped")
        return
    write_and_read("iii_backoff", CONTROL_V)


def phase_X():
    P = out["phases"]["X"] = {}
    P["MoodlesUI"] = gread(client, "MoodlesUI", "X_cls")
    P["getInstance"] = gread(client, "MoodlesUI.getInstance", "X_gi")
    P["moodlesUI_flag"] = gread(client, "TKX_MF.moodlesUI", "X_flag")
    P["stackBox"] = {k: gread(client, f"TKX_MF.stackBox.{k}", f"X_box_{k}") for k in BOX}
    P["stackBox_table"] = gread(client, "TKX_MF.stackBox", "X_box")


def phase_L():
    P = out["phases"]["L"] = {}
    P["client_ts"] = step("L_c_ts", client, "lua.call", "getTimestampMs")["ack"]
    P["server_ts"] = step("L_s_ts", server, "lua.call", "getTimestampMs")["ack"]
    P["client_getMoodle"] = step("L_c_gm", client, "lua.call", "MF.getMoodle TKX 0")["ack"]
    P["client_getInstance"] = step("L_c_gi", client, "lua.call", "MoodlesUI.getInstance")["ack"]
    P["client_missing"] = step("L_c_miss", client, "lua.call", "TKX_MF.noSuchFn")["ack"]
    P["client_setpath"] = step("L_c_sp", client, "lua.setpath", "TKX_MF.setpathSmoke 7")["ack"]
    P["client_setpath_read"] = gread(client, "TKX_MF.setpathSmoke", "L_c_sp_read")


def phase_T():
    P = out["phases"]["T"] = {}
    after = time.time()
    arm_s = ack(step("T_arm_s", server, "tick.rate", str(TICK_S)))
    arm_c = ack(step("T_arm_c", client, "tick.rate", str(TICK_S)))
    P["arm_server"], P["arm_client"] = arm_s, arm_c
    for side, node, arm in (("server", server, arm_s), ("client", client, arm_c)):
        res = None
        if arm.get("armed"):
            try:
                res = node.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 25, after=after)
            except (RuntimeError, TimeoutError, OSError) as e:
                res = {"error": f"{type(e).__name__}: {e}"}
        P[f"result_{side}"] = res


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["tkx_final"] = tk_snapshot("Z")
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["mod_error"] = mod_error("Z")


def body():
    run_phase("F", phase_F)
    if parked():
        out["abort"] = "client parked in the debugger by first sight: the framework or the probe raised at boot"
        return
    run_phase("i", phase_i)
    run_phase("ii", phase_ii)
    run_phase("L", phase_L)
    run_phase("iii", phase_iii)
    if parked():
        out["abort"] = "client parked in the debugger during leg (iii)"
        return
    run_phase("X", phase_X)
    run_phase("T", phase_T)
    run_phase("Z", phase_Z)


# ---------------------------------------------------------------- grading
def tps(res):
    return (res or {}).get("ticksPerSecond") if isinstance(res, dict) else None


def grade_all():
    ph = out["phases"]
    logs = out.get("logs") or {}
    F = ph.get("F") or {}
    if F:
        tk = F.get("tkx") or {}
        obs = {k: val(tk.get(k)) for k in ("detected", "created", "moodleFound", "errors", "ownOnUI")}
        obs["moodle_type"] = (F.get("moodle") or {}).get("type")
        ok = (obs["detected"] is True and obs["created"] is True and obs["moodleFound"] is True
              and num(obs["errors"]) == 0 and obs["ownOnUI"] is True and obs["moodle_type"] == "table")
        grade("F", PRED["F"], obs, "as_predicted" if ok else "falsified",
              "any of detected/created/moodleFound/ownOnUI not true, errors > 0, or TKX_MF.moodle not a table")
    else:
        grade("F", PRED["F"], None, "unmeasured", "no first-sight reads")
    I = ph.get("i") or {}
    if I:
        c, s = I.get("client") or {}, I.get("server") or {}
        obs = {"server_loading_lines": len(logs.get("server_load") or []),
               "client_loading_lines": len(logs.get("client_load") or []),
               "client_MF": (c.get("MF") or {}).get("type"),
               "client_createMoodle": (c.get("MF.createMoodle") or {}).get("type"),
               "server_MF_resolved": (s.get("MF") or {}).get("resolved"),
               "server_MF_failedAt": (s.get("MF") or {}).get("failedAt")}
        ok = (obs["server_loading_lines"] >= 1 and obs["client_MF"] == "table"
              and obs["client_createMoodle"] == "function" and obs["server_MF_resolved"] is False)
        exact = obs["server_loading_lines"] == LOAD_PRED_SERVER and obs["client_loading_lines"] == LOAD_PRED_CLIENT
        grade("i", PRED["i"], obs, "as_predicted" if ok else "falsified",
              "no loading line on the server, MF or MF.createMoodle of the wrong type on the client, or MF "
              "resolved on the server", {"line_counts_exact": exact})
    else:
        grade("i", PRED["i"], None, "unmeasured", "leg (i) not run")
    II = ph.get("ii") or {}
    if II:
        c = II.get("client") or {}
        obs = {"client_MF.key": val(c.get("MF.key")), "cfgKey": val(II.get("cfgKey")),
               "client_MF.hasBorder": (c.get("MF.hasBorder") or {}).get("type"),
               "server_MF.key_resolved": ((II.get("server") or {}).get("MF.key") or {}).get("resolved")}
        ok = (obs["client_MF.key"] == "MoodleFramework" and obs["cfgKey"] == "MoodleFramework"
              and obs["client_MF.hasBorder"] == "function" and obs["server_MF.key_resolved"] is False)
        grade("ii", PRED["ii"], obs, "as_predicted" if ok else "falsified",
              "MF.key nil or other on the client, cfgKey not read at OnGameBoot, MF.hasBorder not a function")
    else:
        grade("ii", PRED["ii"], None, "unmeasured", "leg (ii) not run")
    for label, pred in (("iii_control", PRED["iii_control"]), ("iii_render", PRED["iii_render"]),
                        ("iii_backoff", PRED["iii_backoff"])):
        L = ph.get(label)
        if not L:
            grade(label, pred, None, "unmeasured", "the leg was not run (a parked client or an earlier fault)")
            continue
        st = L.get("state") or {}
        obs = {"level": num(val(st.get("level"))), "gbn": num(val(st.get("gbn"))), "onUI": val(st.get("onUI")),
               "onUI_resolved": (st.get("onUI") or {}).get("resolved"), "lastSet": val(st.get("lastSet")),
               "renders_1": val(L["read1"]["renders"]), "renders_2": val(L["read2"]["renders"]),
               "renders_delta": L.get("renders_delta"), "ownRenders_1": val(L["read1"]["ownRenders"]),
               "ownRenders_2": val(L["read2"]["ownRenders"]), "ownRenders_delta": L.get("ownRenders_delta"),
               "window_s": L.get("renders_window_s"), "parked": L.get("parked")}
        if obs["renders_delta"] is None or obs["level"] is None:
            grade(label, pred, obs, "unmeasured", "a level or a render count did not read")
            continue
        od = obs["ownRenders_delta"] or 0
        if label == "iii_render":
            ok = (obs["level"] == PRED_LEVEL_RENDER and obs["gbn"] == PRED_GBN_RENDER and obs["onUI"] is True
                  and obs["renders_delta"] > 0 and od > 0)
            fals = "level not 4, gbn not 1, onUI not true, or the render count static across the window"
        elif label == "iii_control":
            ok = (obs["level"] == 0 and obs["gbn"] == 0 and obs["onUI"] in (None, False)
                  and obs["renders_delta"] == 0 and od > 0 and (num(obs["ownRenders_1"]) or 0) > 0)
            fals = "level or gbn non-zero, onUI true, the framework count climbing, or the own count static"
        else:
            ok = (obs["level"] == 0 and obs["gbn"] == 0 and obs["onUI"] is False and obs["renders_delta"] == 0)
            fals = "the widget still on the UI manager or its count still climbing after the value went neutral"
        grade(label, pred, obs, "as_predicted" if ok else "falsified", fals)
    X = ph.get("X") or {}
    if X:
        box = {k: val((X.get("stackBox") or {}).get(k)) for k in BOX}
        obs = {"MoodlesUI_resolved": (X.get("MoodlesUI") or {}).get("resolved"),
               "MoodlesUI_type": (X.get("MoodlesUI") or {}).get("type"),
               "getInstance_type": (X.get("getInstance") or {}).get("type"),
               "moodlesUI": val(X.get("moodlesUI_flag")), "stackBox": box}
        nums = all(num(v) is not None for v in box.values())
        ok = obs["MoodlesUI_resolved"] is True and obs["moodlesUI"] is True and nums
        grade("X", PRED["X"], obs, "as_predicted" if ok else "falsified",
              "MoodlesUI unresolved on the client, or the stack box missing a number")
    else:
        grade("X", PRED["X"], None, "unmeasured", "the exposure reads were not run")
    Lc = ph.get("L") or {}
    if Lc:
        def okr(a):
            return isinstance(a, dict) and a.get("ok") is True
        obs = {k: Lc.get(k) for k in ("client_ts", "server_ts", "client_getMoodle", "client_getInstance",
                                      "client_missing", "client_setpath")}
        ok = (okr(obs["client_ts"]) and okr(obs["server_ts"]) and num((obs["client_ts"] or {}).get("r1")) is not None
              and okr(obs["client_setpath"]) and num(val(Lc.get("client_setpath_read"))) == 7)
        grade("L", PRED["L"], obs, "as_predicted" if ok else "falsified",
              "lua.call not ok or no numeric r1, or lua.setpath not writing 7")
    else:
        grade("L", PRED["L"], None, "unmeasured", "the smoke steps were not run")
    T = ph.get("T") or {}
    st, ct = tps(T.get("result_server")), tps(T.get("result_client"))
    if st is None and ct is None:
        grade("T", PRED["T"], None, "unmeasured", "no tick-rate result on either side")
    else:
        grade("T", PRED["T"], {"server_tps": st, "client_tps": ct,
                               "server_ratio_to_x161b": (st / X161B_TICK) if isinstance(st, (int, float)) else None},
              "as_predicted" if (isinstance(ct, (int, float)) and ct > 0) else "falsified",
              "client tps absent or zero")


if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
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
            out["logs"] = {"server": grep_file(server.log_path, LOG_RX, LOG_LIMIT),
                           "server_load": grep_file(server.log_path, LOAD_RX, LOAD_LIMIT_SERVER),
                           "limits": {"log": LOG_LIMIT, "server_load": LOAD_LIMIT_SERVER,
                                      "client_load": LOAD_LIMIT_CLIENT},
                           "patterns": {"log": LOG_RX.pattern, "load": LOAD_RX.pattern}}
            if clients:
                out["logs"]["client"] = grep_file(clients[0].console, LOG_RX, LOG_LIMIT)
                out["logs"]["client_load"] = grep_file(clients[0].console, LOAD_RX, LOAD_LIMIT_CLIENT)
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
