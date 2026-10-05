"""x141-activity-gate -- Plan 3 Task 5, the activity gate session: X37 (#2088, does the server's
thermoregulator classify a connected player's activity), X38 (#2089, is the current action's
caloriesModifier readable server-side), X36 (#2083, does Fitness.update tick on the server), X39's
rep and hit arms (#2084; the AddXP arm was Task 3's) and #0591's moving arm (does any movement
flag reach the server). ONE boot, profile `x14-activity` (PZTestKit + NutritionRevamp Mode 1 +
TKX_MetWatch + TKX_XpEvents), the fixture's 90-minute day (a game minute is 3.75 s wall). The run
id prefix is `x141a`. Copied from `x141_strength_gate.py` (provenance, client-first pairs,
wall-bracketed steps, predictions/verdicts, `to_num`, the persist/step shape).

THE TWO SERVER VIEWS. (1) `TKX_MetWatch`, armed per window with `globalmoddata.set TKX_MetWatch arm
<s>`, samples every server tick: flat keys `hist_<field>_<value>`, `raw_1..raw_50`, `samples`,
`windowMs`, `status`. `witness.moddata` walks a DOTTED key as a nested path, so a histogram key
whose value has a decimal point (`hist_target_1.5`) cannot be read back; the non-dotted ones
(`hist_mv_true`, `hist_calmod_noaction`, ...) can, and `finish` only overwrites the keys a window
saw, so every readable hist key in the census is reset to 0 before each window. The fractional
target/rate values come from `raw_1..raw_50` (the first 50 ticks of the window, parsed) and from
(2) direct paired polls through the whole window: client `witness.chain` FIRST, then server
`witness.chain admin`, of `getBodyDamage.getThermoregulator.getMetabolicTarget` and `...Rate`.

SCHEDULE (one window per arm, `player.stop` and server endurance 1 at each arm's start so the
endurance lift term `(1 - endurance) x 3 x energy` is 0 everywhere):

  S0  setup   markers; the TKX_XpEvents census + values; both sides' regularity(squats); a
              client-first stats.get pair; one probe of every chain used below, both sides.
  I   idle    30 s window, no activity: the control.
  W   walk    `player.walk +-20 0`, re-issued in the other direction whenever the client's
              isPlayerMoving reads false; 30 s window.
  RD  read    `action.read` (Base.Book, spawned client-side); 30 s window; the polls add the
              first action's table on both sides (`getCharacterActions.get(0).getTable`).
  E   eat     `eat.action Base.Apple 1`; 15 s window; the same action-table polls.
  X   exercise regularity both sides + events; `exercise.do squats 8` (8 GAME minutes = 30 s
              wall at the fixture's day; the server's squat rep period is 3000 ms,
              ISFitnessAction.lua serverStart, so ~10 reps); 32 s window; then regularity both
              sides + events.
  R   run     `player.walk +-20 0 run` re-issued; 30 s window.
  SP  sprint  `player.sprint 40 0 14` then `player.sprint -40 0 14` (the client trace
              player-sprint.json each); 30 s window.
  L   load    `inventory.add admin Base.Plank 20` (server); `player.walk +-20 0`; 30 s window.
  M   melee   RCON `createhorde 1 admin` (spawns within +-10 tiles of the player,
              CreateHordeCommand.Command); `attack.melee 5` polled every 2 s for 50 s until a
              zombie is within 2 tiles (one more `createhorde 1 admin` at 50 s if none came);
              events before/after; attack-melee.json.

PREDICTIONS AND FALSIFIERS (written before the run):

  X37   If the server classifies, its target/rate sits at Default 1.5 idle and reaches
        Walking5kmh 3.1 or above while walking (6.9 running, 9.5 sprinting, 6.0 / the exercise's
        metabolics exercising). Prediction (#2088 open; #0591 the server rarely saw moving): the
        server sits at Default -- >= 95 % of every moving window's server samples at 1.5 while
        the client's own chain reads 3.1/6.9/9.5. Falsifier: a server moving window with a mass
        at >= 3.1. `unmeasured` for an arm whose client never read moving / never read off 1.5.
        The target is reset to -1 at the end of each update (C, X37 row), so the rate is graded
        when the target reads -1.
  X38   During `action.read` the server's first action table reads caloriesModifier 0.5 (#2720)
        -> readable. Falsifier: `noaction` / an `unreadable:<hop>` at every read while the
        client's own chain reads the ISReadABook table. The eat arm: 1 (the default), compared.
  X36   The server's regularity(squats) rises after the set (Fitness.update/exerciseRepeat run
        on the server, #2183 +~0.08 per rep). Falsifier: the server value unchanged while the
        client's rises (client-only). `unmeasured` if neither side moves (no rep ran).
  X39r  AddXP fires on the server per rep (Strength/Fitness counts move during the set, #2184).
        Falsifier: no AddXP count moves while the server's regularity rises.
  X39h  OnWeaponHitXp fires on the server per landed swing (hitxp_count moves, #2193).
        Falsifier: swings land (zombie damaged/dead) and hitxp_count does not move. `unmeasured`
        if no zombie ever came within 2 tiles.
  FLAG  The server's isPlayerMoving/isRunning/isSprinting (MetWatch hist_mv/run/spr, stats.get)
        during W/R/SP. Prediction (#0591/#2810): moving rarely, running/sprinting never, while the
        client trace reads them true. Falsifier: a server `true` count for run or spr.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
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

PROFILE = "x14-activity"
SESSION = ("X37 server metabolic classification, X38 server caloriesModifier, X36 server regularity, "
           "X39 rep and hit arms, #0591 moving flags: one boot of x14-activity at the fixture's "
           "90-minute day")
ARTIFACT = "activity_gate.json"
USER = "admin"
ACCEPTANCE_RUN = "x141s-20261005-105131"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

TARGET_HOP = "getBodyDamage.getThermoregulator.getMetabolicTarget"
RATE_HOP = "getBodyDamage.getThermoregulator.getMetabolicRate"
ACTION_HOP = "getCharacterActions.get(0).getTable"
ACTSIZE_HOP = "getCharacterActions.size"
REG_HOP = "getFitness.getRegularity(squats)"
MOVING_HOP = "isPlayerMoving"
WINDOW_S = 30
EAT_WINDOW_S = 15
EX_MINUTES = 8
EX_WINDOW_S = 32
WALK_DX = 20
SPRINT_DX, SPRINT_S = 40, 14
PLANK_COUNT = 20
MELEE_SWINGS = 5
ZOMBIE_WAIT_S, ZOMBIE_POLL_S = 50.0, 2.0
DONE_WAIT_S = 15.0
WM = "TKX_MetWatch"
XE = "TKX_XpEvents"
DEFAULT_MET = 1.5
WALK_MET = 3.1

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
HORDE_RX = re.compile(r"horde|createhorde|Zombie", re.IGNORECASE)
LUAERR_LIMIT, HORDE_LIMIT = 40, 20


def to_num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:20]
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
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def chain(tag, side, hop):
    args = hop if side is client else f"{USER} {hop}"
    r = step(tag, side, "witness.chain", args)
    a = ack(r)
    v = a.get("value")
    return {"tag": tag, "side": "client" if side is client else "server", "wall": r["wall_before"],
            "ok": a.get("ok"), "value": to_num(v), "raw": v, "failedAt": a.get("failedAt"),
            "error": a.get("error"), "reply": r["ack"] if not isinstance(r["ack"], dict) else None}


def stats_pair(tag):
    rc = step(f"{tag}_stats_client", client, "stats.get", "")
    rs = step(f"{tag}_stats_server", server, "stats.get", USER)
    keys = ("moving", "running", "sprinting", "endurance", "fatigue", "asleep", "maxWeight", "worldAge")
    c_, s_ = ack(rc), ack(rs)
    p = {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "client": {k: c_.get(k) for k in keys}, "server": {k: s_.get(k) for k in keys}}
    out["stats_pairs"].append(p)
    return p


def md_read(tag, scope, keys):
    """witness.moddata global:<scope> in chunks of <= 30 keys; values merged (strings)."""
    vals, missing, census = {}, [], None
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        r = step(f"{tag}_{j}", server, "witness.moddata", f"global:{scope} " + " ".join(ch))
        a = ack(r)
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
        if census is None and isinstance(a.get("keys"), list):
            census = a["keys"]
    return {"values": vals, "missing": missing, "census": census or []}


def census_names(census):
    return [str(k).rsplit(":", 1)[0] for k in census]


def events(tag):
    first = md_read(f"{tag}_census", XE, ["levelperk_count"])
    names = [n for n in census_names(first["census"]) if "." not in n]
    full = md_read(tag, XE, names) if names else first
    e = {"tag": tag, "wall": wall(), "values": full["values"], "census": first["census"]}
    out["events"].append(e)
    return e


def ev_num(e, key):
    return to_num((e or {}).get("values", {}).get(key)) or 0.0


def wm_status(tag):
    r = step(tag, server, "witness.moddata", f"global:{WM} status samples windowMs arm")
    return (ack(r).get("values") or {})


def parse_raw(s):
    d = {}
    for part in str(s).split(" "):
        if "=" in part:
            k, v = part.split("=", 1)
            n = to_num(v)
            d[k] = n if n is not None else v
    return d


def window_reset(tag):
    """Zero every readable (non-dotted) hist key the census holds, so a key this window never
    sees cannot carry the last window's count."""
    st = md_read(f"{tag}_pre", WM, ["status"])
    names = census_names(st["census"])
    zeroed = []
    for n in names:
        if n.startswith("hist_") and "." not in n:
            step(f"{tag}_zero", server, "globalmoddata.set", f"{WM} {n} 0")
            zeroed.append(n)
    return {"census_before": st["census"], "zeroed": zeroed}


def window_arm(tag, seconds):
    r = step(f"{tag}_arm", server, "globalmoddata.set", f"{WM} arm {seconds}")
    arm_wall = r["wall_after"]
    armed_seen = None
    end = wall() + 5.0
    while wall() < end:
        s = wm_status(f"{tag}_armchk")
        if s.get("status") == "armed":
            armed_seen = wall()
            break
        time.sleep(0.4)
    return {"arm_wall": arm_wall, "armed_seen_wall": armed_seen, "seconds": seconds}


def window_collect(tag, arm, pre):
    end = arm["arm_wall"] + arm["seconds"] + DONE_WAIT_S
    done = None
    while wall() < end:
        s = wm_status(f"{tag}_donechk")
        if s.get("status") == "done":
            done = s
            break
        time.sleep(1.0)
    first = md_read(f"{tag}_census", WM, ["samples", "windowMs", "status"])
    names = census_names(first["census"])
    hist = [n for n in names if n.startswith("hist_") and "." not in n]
    hv = md_read(f"{tag}_hist", WM, hist) if hist else {"values": {}}
    raws = md_read(f"{tag}_raw", WM, [f"raw_{i}" for i in range(1, 51)])
    raw = []
    for i in range(1, 51):
        v = raws["values"].get(f"raw_{i}")
        if v is not None:
            raw.append(parse_raw(v))
    samples = to_num(first["values"].get("samples"))
    if samples is not None:
        raw = raw[:int(samples)]
    before = set(census_names(pre.get("census_before") or []))
    new_keys = sorted(n for n in names if n.startswith("hist_") and n not in before)
    return {"done": done, "samples": samples, "windowMs": to_num(first["values"].get("windowMs")),
            "status": first["values"].get("status"),
            "hist": {k: to_num(v) for k, v in hv["values"].items()},
            "new_hist_keys": new_keys, "census_after": first["census"], "raw": raw}


def poll_once(i, tag, extra_hops=(), keep_moving=None):
    s = {"i": i}
    s["client_target"] = chain(f"{tag}{i}_ct", client, TARGET_HOP)
    s["client_rate"] = chain(f"{tag}{i}_cr", client, RATE_HOP)
    s["server_target"] = chain(f"{tag}{i}_st", server, TARGET_HOP)
    s["server_rate"] = chain(f"{tag}{i}_sr", server, RATE_HOP)
    for name, hop in extra_hops:
        s[f"client_{name}"] = chain(f"{tag}{i}_c{name}", client, hop)
        s[f"server_{name}"] = chain(f"{tag}{i}_s{name}", server, hop)
    if keep_moving is not None:
        mv = chain(f"{tag}{i}_cmv", client, MOVING_HOP)
        s["client_moving"] = mv["raw"]
        if str(mv["raw"]).lower() != "true":
            s["reissue"] = keep_moving()
    return s


def run_window(P, key, seconds, start_fn=None, extra_hops=(), keep_moving=None, after_fn=None):
    """One arm: stop, endurance 1, reset hist keys, start the activity, arm, poll paired chains
    until the window ends, collect MetWatch."""
    A = P[key] = {}
    A["stop"] = ack(step(f"{key}_stop", client, "player.stop", ""))
    A["endurance_set"] = ack(step(f"{key}_end1", server, "stats.set", f"{USER} endurance 1"))
    time.sleep(1.0)
    A["pre"] = window_reset(key)
    A["stats_start"] = stats_pair(f"{key}_start")
    A["start"] = start_fn() if start_fn else None
    A["start_wall"] = wall()
    time.sleep(1.0)
    A["arm"] = window_arm(key, seconds)
    A["polls"] = []
    i = 0
    end = A["arm"]["arm_wall"] + seconds
    mid_done = False
    while wall() < end - 1.0:
        A["polls"].append(poll_once(i, key, extra_hops, keep_moving))
        if not mid_done and wall() > A["arm"]["arm_wall"] + seconds / 2:
            A["stats_mid"] = stats_pair(f"{key}_mid")
            mid_done = True
        i += 1
    A["stats_end"] = stats_pair(f"{key}_end")
    A["metwatch"] = window_collect(key, A["arm"], A["pre"])
    if after_fn:
        A["after"] = after_fn()
    A["stop_end"] = ack(step(f"{key}_stop_end", client, "player.stop", ""))
    persist()
    return A


def walker(key, run=False):
    state = {"dir": 1, "n": 0}
    issued = []

    def go():
        dx = WALK_DX * state["dir"]
        state["dir"] = -state["dir"]
        state["n"] += 1
        r = step(f"{key}_walk{state['n']}", client, "player.walk", f"{dx} 0" + (" run" if run else ""))
        a = ack(r)
        rec = {"n": state["n"], "dx": dx, "wall": r["wall_before"], "queued": a.get("queued"),
               "error": a.get("error"), "clientMoving": a.get("clientMoving"),
               "clientRunning": a.get("clientRunning"), "setRunning": a.get("setRunning")}
        issued.append(rec)
        return rec
    return go, issued


def body():
    P = out["phases"]
    # ---------------- S0 setup ----------------
    S0 = P["S0"] = {}
    S0["metwatch_installed"] = ack(step("mw_installed", server, "lua.global", "TKX_MetWatch_Installed"))
    S0["events_installed"] = ack(step("ev_installed", server, "lua.global", "TKX_XpEvents_Installed"))
    S0["events0"] = events("s0_events")
    S0["reg_client"] = chain("s0_reg_c", client, REG_HOP)
    S0["reg_server"] = chain("s0_reg_s", server, REG_HOP)
    S0["stats"] = stats_pair("s0")
    S0["probe"] = {h: {"client": chain(f"s0_probe_c_{h}", client, h), "server": chain(f"s0_probe_s_{h}", server, h)}
                   for h in (TARGET_HOP, RATE_HOP, ACTSIZE_HOP, ACTION_HOP)}
    S0["wm_status0"] = wm_status("s0_wm")
    persist()

    act_hops = (("actsize", ACTSIZE_HOP), ("action", ACTION_HOP))

    # ---------------- I idle ----------------
    run_window(P, "I", WINDOW_S)
    # ---------------- W walk ----------------
    go, issued = walker("W")
    run_window(P, "W", WINDOW_S, start_fn=go, keep_moving=go)
    P["W"]["walks"] = issued
    # ---------------- RD read ----------------
    run_window(P, "RD", WINDOW_S,
               start_fn=lambda: ack(step("RD_read", client, "action.read", "Base.Book")),
               extra_hops=act_hops)
    # ---------------- E eat ----------------
    run_window(P, "E", EAT_WINDOW_S,
               start_fn=lambda: ack(step("E_eat", client, "eat.action", "Base.Apple 1")),
               extra_hops=act_hops)
    # ---------------- X exercise ----------------
    X = {}
    X["events0"] = events("x_events0")
    X["reg_client0"] = chain("x_reg_c0", client, REG_HOP)
    X["reg_server0"] = chain("x_reg_s0", server, REG_HOP)

    def ex_start():
        return ack(step("X_exercise", client, "exercise.do", f"squats {EX_MINUTES}"))

    def ex_after():
        time.sleep(3.0)
        return {"reg_client1": chain("x_reg_c1", client, REG_HOP),
                "reg_server1": chain("x_reg_s1", server, REG_HOP),
                "events1": events("x_events1")}
    run_window(P, "X", EX_WINDOW_S, start_fn=ex_start,
               extra_hops=(("action", ACTION_HOP), ("reg", REG_HOP)), after_fn=ex_after)
    P["X"].update(X)
    # ---------------- R run ----------------
    go, issued = walker("R", run=True)
    run_window(P, "R", WINDOW_S, start_fn=go, keep_moving=go)
    P["R"]["walks"] = issued
    # ---------------- SP sprint ----------------
    SP = {"sprints": []}

    def sp_start():
        e = time.time()
        a = ack(step("SP_sprint1", client, "player.sprint", f"{SPRINT_DX} 0 {SPRINT_S}"))
        SP["sprints"].append({"ack": a, "epoch": e})
        return a
    run_window(P, "SP", WINDOW_S, start_fn=sp_start)
    P["SP"].update(SP)
    traces = []
    for s in SP["sprints"]:
        try:
            traces.append(client.bus.wait_result("player-sprint", timeout=25, after=s["epoch"]))
        except Exception as e:                 # noqa: BLE001
            traces.append({"error": f"{type(e).__name__}: {e}"})
    P["SP"]["trace1"] = traces[0] if traces else None
    # the second sprint leg: a second window would double the arm; the second leg runs inside the
    # first window's remaining time only if the first trace returned before it ended -- it did not
    # (14 s leg, 30 s window), so a second leg + short window follows.
    e2 = time.time()
    P["SP"]["sprint2"] = ack(step("SP_sprint2", client, "player.sprint", f"{-SPRINT_DX} 0 {SPRINT_S}"))
    pre2 = window_reset("SP2")
    arm2 = window_arm("SP2", SPRINT_S)
    polls2 = []
    i = 0
    while wall() < arm2["arm_wall"] + SPRINT_S - 1.0:
        polls2.append(poll_once(i, "SP2"))
        i += 1
    P["SP"]["stats_leg2"] = stats_pair("SP2_end")
    P["SP"]["leg2"] = {"pre": pre2, "arm": arm2, "polls": polls2,
                       "metwatch": window_collect("SP2", arm2, pre2)}
    try:
        P["SP"]["trace2"] = client.bus.wait_result("player-sprint", timeout=25, after=e2)
    except Exception as e:                     # noqa: BLE001
        P["SP"]["trace2"] = {"error": f"{type(e).__name__}: {e}"}
    persist()
    # ---------------- L loaded walk ----------------
    L0 = {"add": ack(step("L_add", server, "inventory.add", f"{USER} Base.Plank {PLANK_COUNT}"))}
    go, issued = walker("L")
    run_window(P, "L", WINDOW_S, start_fn=go, keep_moving=go)
    P["L"].update(L0)
    P["L"]["walks"] = issued
    # ---------------- M melee ----------------
    M = P["M"] = {}
    M["stop"] = ack(step("M_stop", client, "player.stop", ""))
    M["events0"] = events("m_events0")
    M["rcon"] = []
    ok, rep = server.rcon(f"createhorde 1 {USER}")
    M["rcon"].append({"wall": wall(), "cmd": f"createhorde 1 {USER}", "ok": ok, "reply": str(rep)[:300]})
    M["attempts"] = []
    started = None
    t_start = wall()
    second = False
    while started is None and wall() < t_start + 2 * ZOMBIE_WAIT_S:
        if not second and wall() > t_start + ZOMBIE_WAIT_S:
            ok, rep = server.rcon(f"createhorde 1 {USER}")
            M["rcon"].append({"wall": wall(), "cmd": f"createhorde 1 {USER}", "ok": ok, "reply": str(rep)[:300]})
            second = True
        e = time.time()
        r = step("M_attack", client, "attack.melee", str(MELEE_SWINGS))
        a = ack(r)
        M["attempts"].append({"wall": r["wall_before"], "ok": a.get("ok"), "reason": a.get("reason"),
                              "target": a.get("target"), "weapon": a.get("weapon")})
        if a.get("ok") is True:
            started = e
            break
        time.sleep(ZOMBIE_POLL_S)
    if started is not None:
        try:
            M["result"] = client.bus.wait_result("attack-melee", timeout=40, after=started)
        except Exception as ex:                # noqa: BLE001
            M["result"] = {"error": f"{type(ex).__name__}: {ex}"}
        time.sleep(2.0)
    else:
        note("no zombie came within 2 tiles in the melee window; the hit arm is unmeasured")
    M["events1"] = events("m_events1")
    M["stats_end"] = stats_pair("M_end")
    persist()


def series(polls, key):
    return [p[key]["value"] for p in polls if isinstance(p.get(key), dict) and p[key]["value"] is not None]


def frac_at(vals, x, tol=0.05):
    if not vals:
        return None
    return round(sum(1 for v in vals if abs(v - x) <= tol) / len(vals), 3)


def arm_summary(A):
    polls = A.get("polls", [])
    mw = A.get("metwatch") or {}
    raw = mw.get("raw") or []
    out_ = {}
    for side in ("client", "server"):
        for g in ("target", "rate"):
            v = series(polls, f"{side}_{g}")
            out_[f"{side}_{g}"] = {"n": len(v), "min": min(v) if v else None, "max": max(v) if v else None,
                                   "at_default": frac_at(v, DEFAULT_MET), "values": v}
    for g in ("target", "rate"):
        v = [r[g] for r in raw if isinstance(r.get(g), float)]
        out_[f"metwatch_raw_{g}"] = {"n": len(v), "min": min(v) if v else None, "max": max(v) if v else None,
                                     "at_default": frac_at(v, DEFAULT_MET)}
    h = mw.get("hist") or {}
    out_["metwatch_flags"] = {k: h.get(k) for k in sorted(h) if k.startswith(("hist_mv", "hist_run", "hist_spr"))}
    out_["metwatch_calmod"] = {k: h.get(k) for k in sorted(h) if k.startswith("hist_calmod")}
    out_["metwatch_new_keys"] = mw.get("new_hist_keys")
    out_["metwatch_samples"] = mw.get("samples")
    out_["client_moving"] = [p.get("client_moving") for p in polls if "client_moving" in p]
    return out_


def eff(s, side):
    """The graded series for a side: the target, unless it reads -1/unreadable, then the rate."""
    t = s[f"{side}_target"]
    if t["n"] and (t["max"] is not None and t["max"] >= 0):
        return "target", t
    return "rate", s[f"{side}_rate"]


def grade_all():
    P = out["phases"]
    summ = out["arm_summaries"] = {k: arm_summary(P[k]) for k in ("I", "W", "RD", "E", "X", "R", "SP", "L")
                                   if k in P}
    if "SP" in P and "leg2" in P["SP"]:
        summ["SP2"] = arm_summary(P["SP"]["leg2"])
    # ---- X37 ----
    obs = {}
    moving_arms = [k for k in ("W", "R", "SP", "SP2", "L") if k in summ]
    server_moves, client_moves = False, False
    for k in ["I"] + moving_arms + [k for k in ("X",) if k in summ]:
        if k not in summ:
            continue
        sg, sv = eff(summ[k], "server")
        cg, cv = eff(summ[k], "client")
        obs[k] = {"server_graded": sg, "server_max": sv["max"], "server_at_default": sv["at_default"],
                  "client_graded": cg, "client_max": cv["max"], "client_at_default": cv["at_default"],
                  "raw_target_max": summ[k]["metwatch_raw_target"]["max"],
                  "raw_rate_max": summ[k]["metwatch_raw_rate"]["max"]}
        if k in moving_arms:
            if sv["max"] is not None and sv["max"] >= WALK_MET - 0.05:
                server_moves = True
            if cv["max"] is not None and cv["max"] >= WALK_MET - 0.05:
                client_moves = True
    if not obs or "I" not in obs:
        v = "unmeasured"
    elif server_moves:
        v = "falsified"
    elif not client_moves:
        v = "unmeasured"
    elif all((obs[k]["server_at_default"] or 0) >= 0.95 for k in moving_arms if k in obs):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X37", "server sits at Default 1.5 (>= 95 % of moving-window samples) while the client reads "
                 ">= 3.1", obs, v, "a server moving window reaching >= 3.1; unmeasured if the client never did")
    # ---- X38 ----
    obs = {}
    readable = False
    for k in ("RD", "E", "X"):
        A = P.get(k) or {}
        sv = [p.get("server_action", {}).get("raw") for p in A.get("polls", [])]
        cv = [p.get("client_action", {}).get("raw") for p in A.get("polls", [])]
        scm = [x.get("caloriesModifier") if isinstance(x, dict) else None for x in sv]
        ccm = [x.get("caloriesModifier") if isinstance(x, dict) else None for x in cv]
        sfail = [p.get("server_action", {}).get("failedAt") for p in A.get("polls", [])]
        obs[k] = {"server_calmod": scm, "client_calmod": ccm, "server_failedAt": sfail,
                  "metwatch_calmod": (summ.get(k) or {}).get("metwatch_calmod"),
                  "metwatch_new_keys": (summ.get(k) or {}).get("metwatch_new_keys")}
        if k == "RD" and any(to_num(x) == 0.5 for x in scm):
            readable = True
    rd = obs.get("RD", {})
    if not P.get("RD"):
        v = "unmeasured"
    elif readable:
        v = "as_predicted"
    elif any(to_num(x) == 0.5 for x in rd.get("client_calmod", [])):
        v = "falsified"
    else:
        v = "unmeasured"
    grade("X38", "server first-action caloriesModifier reads 0.5 during action.read", obs, v,
          "server noaction/unreadable while the client reads the ISReadABook table (0.5)")
    # ---- X36 ----
    X = P.get("X") or {}
    a_ = X.get("after") or {}
    rs0, rs1 = (X.get("reg_server0") or {}).get("value"), (a_.get("reg_server1") or {}).get("value")
    rc0, rc1 = (X.get("reg_client0") or {}).get("value"), (a_.get("reg_client1") or {}).get("value")
    obs = {"server_before": rs0, "server_after": rs1, "client_before": rc0, "client_after": rc1,
           "exercise_ack": X.get("start")}
    s_up = rs0 is not None and rs1 is not None and rs1 > rs0 + 1e-6
    c_up = rc0 is not None and rc1 is not None and rc1 > rc0 + 1e-6
    if s_up:
        v = "as_predicted"
    elif c_up:
        v = "falsified"
    else:
        v = "unmeasured"
    grade("X36", "server regularity(squats) rises over the set", obs, v,
          "server unchanged while the client rises (client-only); unmeasured if neither moves")
    # ---- X39 rep ----
    e0, e1 = X.get("events0"), a_.get("events1")
    deltas = {}
    if e0 and e1:
        for k in sorted(set(e1["values"]) | set(e0["values"])):
            if k.endswith("_count"):
                deltas[k] = ev_num(e1, k) - ev_num(e0, k)
    obs = {"count_deltas": deltas, "after": (e1 or {}).get("values"), "server_reg_rose": s_up}
    moved = any(d > 0 for k, d in deltas.items() if k.startswith(("addxp_Strength", "addxp_Fitness")))
    if not e0 or not e1:
        v = "unmeasured"
    elif moved:
        v = "as_predicted"
    elif s_up:
        v = "falsified"
    else:
        v = "unmeasured"
    grade("X39-rep", "AddXP Strength/Fitness counts move on the server during the set", obs, v,
          "no AddXP count moves while the server's regularity rises")
    # ---- X39 hit ----
    M = P.get("M") or {}
    m0, m1 = M.get("events0"), M.get("events1")
    deltas = {}
    if m0 and m1:
        for k in sorted(set(m1["values"]) | set(m0["values"])):
            if k.endswith("_count"):
                deltas[k] = ev_num(m1, k) - ev_num(m0, k)
    res = M.get("result") or {}
    obs = {"count_deltas": deltas, "hitxp_lastHitCount": (m1 or {}).get("values", {}).get("hitxp_lastHitCount"),
           "attack_result": res, "attempts": len(M.get("attempts", [])), "rcon": M.get("rcon")}
    if not any(a.get("ok") is True for a in M.get("attempts", [])):
        v = "unmeasured"
    elif deltas.get("hitxp_count", 0) > 0:
        v = "as_predicted"
    elif res.get("targetDead") is True:
        v = "falsified"
    else:
        v = "trivial"
    grade("X39-hit", "hitxp_count moves per landed swing", obs, v,
          "swings land (target dead) and hitxp_count does not move; unmeasured with no zombie; "
          "trivial when no swing is known to have landed")
    # ---- FLAG ----
    obs = {}
    srv_run = 0.0
    for k in moving_arms:
        f = summ[k]["metwatch_flags"]
        obs[k] = {"metwatch": f, "stats": [(p.get("server") or {}) for p in
                                            [P.get(k, {}).get("stats_mid")] if p]}
        srv_run += (f.get("hist_run_true") or 0) + (f.get("hist_spr_true") or 0)
    obs["sprint_trace1"] = (P.get("SP") or {}).get("trace1")
    obs["sprint_trace2"] = (P.get("SP") or {}).get("trace2")
    v = "falsified" if srv_run > 0 else ("as_predicted" if moving_arms else "unmeasured")
    grade("FLAG", "server run/spr flags never true in W/R/SP/L while the client trace reads them", obs, v,
          "a server run or spr true count")


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x141a-dry-run", None) if DRY_RUN else new_run_dir("x141a")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_MetWatch",
                                "testing/experiments/TKX_XpEvents"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"WINDOW_S": WINDOW_S, "EAT_WINDOW_S": EAT_WINDOW_S, "EX_MINUTES": EX_MINUTES,
                  "EX_WINDOW_S": EX_WINDOW_S, "WALK_DX": WALK_DX, "SPRINT_DX": SPRINT_DX, "SPRINT_S": SPRINT_S,
                  "PLANK_COUNT": PLANK_COUNT, "MELEE_SWINGS": MELEE_SWINGS, "ZOMBIE_WAIT_S": ZOMBIE_WAIT_S,
                  "DEFAULT_MET": DEFAULT_MET, "WALK_MET": WALK_MET},
    "deviations": [
        "First live use of exercise.do, action.read, player.sprint, attack.melee, inventory.add and TKX_MetWatch "
        "(Task 4, no acceptance run since): the profile's verify rows and each command's reply are the smoke test.",
        "exercise.do runs 8 game minutes, not the amendments' 2: at the fixture's 90-minute day 2 game minutes is "
        "7.5 s wall, about two reps at the server's 3000 ms squat period; 8 minutes is ~30 s, the other windows' length.",
        "Server endurance is set to 1 at every arm's start so the endurance lift on the target is 0 throughout.",
        "TKX_MetWatch's dotted hist keys (fractional values) cannot be read by witness.moddata; the fractional "
        "target/rate come from raw_1..raw_50 and the paired witness.chain polls.",
        "The sprint arm runs as two legs (two player.sprint calls, max 20 s each): a 30 s window over leg 1 and a "
        "14 s window over leg 2.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["20 planks in the server inventory", "a book and an apple spawned client-side",
                                        "squats regularity raised", "a zombie spawned by RCON"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "events": [], "stats_pairs": [],
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None)
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec)
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out.get("mods_not_found"),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        if server is not None:
            out["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                           "server_horde": grep_file(server.log_path, HORDE_RX, HORDE_LIMIT),
                           "limits": {"luaerr": LUAERR_LIMIT, "horde": HORDE_LIMIT}}
            if clients:
                out["logs"].update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)})
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error"),
                  "body_error": out.get("body_error")}, indent=1)[:7000])
