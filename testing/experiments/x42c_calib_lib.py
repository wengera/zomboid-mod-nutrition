"""x42c_calib_lib -- the session engine of the Plan 13 Task 1 driver (x423_calib.py): the XP-per-set calibration and
check 7's remaining Strength sources. Started from x42b_levers_lib.py (frozen with x422-20261015-034556; its recorder
read, event rows and protein factor are copied here, not imported), built on testing/experiments/xlib.py.

One boot of profile x42-calib: fixture default (admin, the -debug client, the subject), PZTestKit and the probe mod
TKX_TraitLevers by its path for its AddXP recorder (TKX_TraitLevers.xp.ev[i] = {user, perk, amount, ms, protein,
fitness, level, xp}, capped at 200 records, xp.calls counting every call), no NutritionRevamp (no mod/ file is booted),
Nutrition false, DayLength 1, build 42.21.0.

THE XP CAP (Task 0's lesson, pushup-investigation.md): XP.AddXP returns before the AddXP event when the amount is
non-negative and the perk's experience is at or above the level-10 total (487500), so every source window opens with a
gate: perk.xp admin Strength; at or above CAP_XP the subject is set to PARK_LEVEL (perk.set: setPerkLevelDebug plus
setXPToLevel) and read again; a window whose experience is still at the cap when it opens is unmeasured.

THE WINDOWS (in this order; each opens with the gate and empties the recorder):
  P  the push-up set to exhaustion: nutrition.set admin proteins PROTEIN_SET on the server and read back (the factor-1
     window, NEUTRAL_LO <= store <= NEUTRAL_HI: XP.AddXP's Strength factor is 1.5 for 50 < store < 300 and 0.7 below
     -300, #2112); stats.setany admin ENDURANCE 1; exercise.do pushups PUSHUP_ASK_M (client); the server's exercise flag
     (getFitness.getCurrentExe) and endurance (stats.get) polled every POLL_S; the driver stops the set with
     action.cancel (client; CLAUDE.md s5) when the server's endurance reads ENDURANCE_STOP or below, or reads the end
     when the flag clears by itself; then waits for the server's flag to clear. Read: every AddXP event of the window,
     the protein store before and after, the Strength experience before and after (an independent sum: the recorder
     caps at 200 records, so a set past 100 reps would drop events; xp.calls still counts them).
  W  loaded movement: stats.setany admin ENDURANCE 1; inventory.add admin LOAD_ITEM until the server's inventory weight
     passes LOAD_SHARE x the max weight (well above capacity; vanilla's gate is 0.5, XpUpdate.lua:32-37); walk legs of
     WALK_DX tiles (player.walk, each leg after an action.cancel so the queue never stacks) for WALK_S of wall clock,
     the server's moving flag, endurance, load moodle and inventory weight read every leg poll; then action.cancel and
     a wait for the server's moving flag to clear (CLAUDE.md s5).
  M  melee: stats.setany admin ENDURANCE 1; RCON createhorde 1 admin (the server-side spawn x141a, x224 and x29 used:
     zombie.near spawned none on this fixture, #2916, and x422's probe zombieNear returned an empty list);
     attack.melee MELEE_SWINGS at the nearest zombie within 2 tiles, retried every 2 s for MELEE_FIND_S (one more
     createhorde past half of it), up to MELEE_WINDOWS windows until the target is dead; the client's attack-melee
     result read after each window.

THE GRADES (pure; each has a failing case in testing/tests/test_x42c_calib_lib.py):
  pushups  as_predicted: at least one Strength event, every amount PUSHUP_XP x the protein factor of the store read in
           the event (Fitness.incStats L320-L334: 4 for arms plus 2 for chest), no record dropped. falsified: a set that
           ran with zero Strength events, or an amount off 6 x factor (each mismatch listed, never dropped).
           unmeasured: the cap at the window's open, the set never seen on the server, the store before or after
           outside the neutral window (an event outside it is listed), records dropped.
           THE READING: xp_per_set = the sum over the set's Strength events of amount / factor; reps = the count;
           the wall seconds (the flag's first and last server reads) and the XP per real second beside it; the
           experience delta beside the sum.
  walk     as_predicted: at least one positive Strength event; falsified: none, with the window loaded past half the
           max weight and the server reading moving at MOVE_MIN_READS polls or more; unmeasured: the cap, no load, or
           fewer moving reads.
  melee    as_predicted: at least one positive Strength event; falsified: none, with a hit evidenced (a positive event of
           another perk than Strength and Fitness, or the target dead); unmeasured: the cap, no zombie in range, or no
           hit evidenced.

Reply shapes the lib reads are the harness's own (@reply lines): perk.xp {perk, user, side, xp, level, serverWorldAge};
perk.set {perk, requested, side, before, ..., after, route}; nutrition.set and nutrition.get {calories, carbs, lipids,
proteins, ...}; stats.setany {ok, stat, side, requested, before, after}; stats.get {..., proteins, endurance, moodles,
maxWeight, moving, worldAge, wall}; witness.chain {ok, value, hops, failedAt}; exercise.do {ok, exercise, minutes,
queued, queueLen}; action.cancel {ok, before, after, current, started, adding, stopped, javaBefore, javaAfter, cleared};
inventory.add {ok, fullType, count, side, invWeight, maxWeight}; player.walk {dx, dy, run, from, target, queued, ...};
attack.melee {ok, target, swings, weapon, result, file} | {ok, reason}; lua.read {ok, side, root, n, values, tables,
types, missing}; lua.call {ok, side, path, nargs, r1, r2, r3}; RCON (xlib.Xs.rcon) {ok, reply}.

FROZEN WITH ITS FIRST RUN: once x423 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

import xlib as X                                                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
SRV = "server"
LIB_FILE = "x42c_calib_lib.py"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
PROBE_DIR = "testing/experiments/TKX_TraitLevers"
USER = "admin"
CLI = "client"
MIN_FREE_GB = 12.0
POLL_S = 0.5
CAP_XP = 487500.0                      # getTotalXpForLevel(10) for Strength (#2102)
PARK_LEVEL = 5
PROTEIN_SET = 0
NEUTRAL_LO = -300.0                    # the factor-1 window: -300 <= store <= 50 (#2112)
NEUTRAL_HI = 50.0
PUSHUP_XP = 6.0                        # Fitness.incStats L320-L334: arms 4 + chest 2
PUSHUP_ASK_M = 300                     # game minutes asked (187.5 s at DayLength 1): the set ends at exhaustion first
SET_START_CAP_S = 20.0
SET_CAP_S = 260.0
ENDURANCE_STOP = 0.25
EXE_CLEAR_CAP_S = 20.0
SETTLE_S = 2.0
REL_TOL = 1e-4
LOAD_ITEM = "Base.BarBell"             # 6.0 kg (weapon.txt BarBell), x404's load
LOAD_MAX_ADDS = 15
LOAD_SHARE = 1.25                      # well above capacity (vanilla's Strength gate is 0.5 of the max weight)
WALK_S = 180.0                         # 4.8 game hours at DayLength 1 (the amendment asks at least 2)
WALK_DX = 6
WALK_LEG_S = 6.0
MOVE_MIN_READS = 20
MOVE_CLEAR_CAP_S = 15.0
LOAD_RATE_XP_S = 0.1                   # vanilla-strength-rate s3c: one roll a second, 1 in 20, +2
MELEE_SWINGS = 10
MELEE_WINDOWS = 3
MELEE_FIND_S = 60.0
MELEE_RESULT_S = 20.0
EVENT_FIELDS = ("user", "perk", "amount", "ms", "protein", "fitness", "level", "xp")
EVENT_CAP = 200
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"TKX_TraitLevers|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)


# ---------------------------------------------------------------- pure helpers (shared with the tests)
def protein_factor(store):
    """XP.AddXP's Strength protein factor (#2112): 1.5 for 50 < store < 300, then 0.7 below -300."""
    p = X.num(store)
    if p is None:
        return None
    f = 1.0
    if 50.0 < p < 300.0:
        f *= 1.5
    if p < -300.0:
        f *= 0.7
    return f


def neutral(store):
    p = X.num(store)
    return p is not None and NEUTRAL_LO <= p <= NEUTRAL_HI


def close(a, b, rel=REL_TOL):
    a, b = X.num(a), X.num(b)
    if a is None or b is None:
        return False
    return abs(a - b) <= rel * max(1.0, abs(b))


def event_rows(read_replies):
    """The recorder's events off lua.read replies of TKX_TraitLevers.xp.ev.<i>.<field> paths, in index order."""
    rows = {}
    for rep in read_replies:
        for path, v in ((rep or {}).get("values") or {}).items():
            m = re.match(r"^TKX_TraitLevers\.xp\.ev\.(\d+)\.(\w+)$", path)
            if m:
                rows.setdefault(int(m.group(1)), {"i": int(m.group(1))})[m.group(2)] = v
    return [rows[k] for k in sorted(rows)]


def strength_events(events, user=USER, positive=True):
    out = []
    for e in events:
        if e.get("user") != user or e.get("perk") != "Strength":
            continue
        amt = X.num(e.get("amount"))
        if positive and (amt is None or amt <= 0):
            continue
        out.append(e)
    return out


def other_perk_hits(events, user=USER):
    """Positive events of a perk other than Strength and Fitness: a weapon skill's hit XP, the melee hit evidence."""
    return [e for e in events if e.get("user") == user and e.get("perk") not in ("Strength", "Fitness")
            and (X.num(e.get("amount")) or 0) > 0]


def at_cap(gate):
    """A window whose Strength experience is at or above the level-10 total when it opens (or unread) is unmeasured."""
    xp = X.num((gate or {}).get("xp_open"))
    return xp is None or xp >= CAP_XP


# ---------------------------------------------------------------- the grades (pure; each has a failing case in the tests)
def grade_pushups(w):
    """The calibration set: the reading and its verdict."""
    w = w or {}
    ev_all = w.get("events") or []
    ev = strength_events(ev_all, positive=False)
    rows, mism, outside, total = [], [], [], 0.0
    for e in ev:
        pf = protein_factor(e.get("protein"))
        amt = X.num(e.get("amount"))
        want = PUSHUP_XP * pf if pf is not None else None
        ok = want is not None and close(amt, want)
        norm = (amt / pf) if (amt is not None and pf) else None
        if norm is not None:
            total += norm
        row = {"i": e.get("i"), "amount": amt, "protein": X.num(e.get("protein")), "factor": pf, "want": want,
               "ok": ok, "ms": X.num(e.get("ms"))}
        rows.append(row)
        if not ok:
            mism.append(row)
        if not neutral(e.get("protein")):
            outside.append(row)
    ms = [r["ms"] for r in rows if r["ms"] is not None]
    span_s = round((max(ms) - min(ms)) / 1000.0, 3) if len(ms) >= 2 else None
    set_s = X.num(w.get("set_s"))
    xp0, xp1 = X.num((w.get("xp_before") or {}).get("xp")), X.num((w.get("xp_after") or {}).get("xp"))
    obs = {"reps": len(ev), "xp_per_set": round(total, 6) if ev else None,
           "amount_sum": round(sum(r["amount"] or 0.0 for r in rows), 6),
           "xp_delta": (xp1 - xp0) if (xp0 is not None and xp1 is not None) else None,
           "set_s": set_s, "event_span_s": span_s,
           "xp_per_s": round(total / set_s, 6) if (ev and set_s) else None,
           "xp_per_s_span": round(total / span_s, 6) if (ev and span_s) else None,
           "mismatches": mism[:20], "n_mismatches": len(mism), "events_outside_window": outside[:20],
           "n_outside": len(outside), "store_before": w.get("store_before"), "store_after": w.get("store_after"),
           "stop_reason": w.get("stop_reason"), "exe_seen": w.get("exe_seen"), "dropped": w.get("dropped"),
           "calls": w.get("calls"), "all_events": len(ev_all),
           "fitness_events": len([e for e in ev_all if e.get("perk") == "Fitness"]),
           "gate": w.get("gate")}
    if at_cap(w.get("gate")):
        obs["why"] = "the Strength experience was at the level-10 total (or unread) when the window opened"
        return "unmeasured", obs
    if not w.get("exe_seen"):
        obs["why"] = "the server never read the set's exercise flag"
        return "unmeasured", obs
    if not (neutral(w.get("store_before")) and neutral(w.get("store_after"))):
        obs["why"] = "the protein store before or after the set was outside the neutral window"
        return "unmeasured", obs
    if (X.num(w.get("dropped")) or 0) > 0:
        obs["why"] = "the recorder dropped records past its cap: the event sum is incomplete"
        return "unmeasured", obs
    if not ev:
        obs["why"] = "the set ran and fired no Strength AddXP event"
        return "falsified", obs
    if mism:
        obs["why"] = "an amount off PUSHUP_XP x the protein factor"
        return "falsified", obs
    return "as_predicted", obs


def grade_walk(w):
    w = w or {}
    ev_all = w.get("events") or []
    ev = strength_events(ev_all)
    reads = w.get("reads") or []
    moving = [r for r in reads if r.get("moving") is True]
    loaded = [r for r in reads if X.num(r.get("invWeight")) is not None and X.num(r.get("maxWeight"))
              and X.num(r.get("invWeight")) > 0.5 * X.num(r.get("maxWeight"))]
    ms = [X.num(r.get("ms")) for r in ev]
    obs = {"events": len(ev), "amounts": [X.num(e.get("amount")) for e in ev][:30],
           "event_ms": [m for m in ms if m is not None][:30], "all_events": len(ev_all),
           "reads": len(reads), "moving_reads": len(moving), "loaded_reads": len(loaded),
           "load": w.get("load"), "walk_s": w.get("walk_s"), "legs": len(w.get("legs") or []),
           "expected_xp": round(LOAD_RATE_XP_S * X.num(w.get("walk_s")), 3) if X.num(w.get("walk_s")) else None,
           "strength_sum": round(sum(X.num(e.get("amount")) or 0.0 for e in ev), 6), "dropped": w.get("dropped"),
           "move_cleared": w.get("move_cleared"), "gate": w.get("gate")}
    if at_cap(w.get("gate")):
        obs["why"] = "the Strength experience was at the level-10 total (or unread) when the window opened"
        return "unmeasured", obs
    if ev:
        return "as_predicted", obs
    if not w.get("loaded") or len(loaded) < MOVE_MIN_READS // 2:
        obs["why"] = "the window was not loaded past half the max weight"
        return "unmeasured", obs
    if len(moving) < MOVE_MIN_READS:
        obs["why"] = "the server read the subject moving at fewer than MOVE_MIN_READS polls"
        return "unmeasured", obs
    obs["why"] = "loaded and moving on the server, and no positive Strength event"
    return "falsified", obs


def grade_melee(w):
    w = w or {}
    ev_all = w.get("events") or []
    ev = strength_events(ev_all)
    hits = other_perk_hits(ev_all)
    wins = w.get("windows") or []
    dead = any(isinstance(x.get("result"), dict) and x["result"].get("targetDead") is True for x in wins)
    obs = {"events": len(ev), "amounts": [X.num(e.get("amount")) for e in ev][:30], "all_events": len(ev_all),
           "other_perk_events": [{"perk": e.get("perk"), "amount": X.num(e.get("amount"))} for e in hits][:30],
           "windows": len(wins), "swings_made": [((x.get("result") or {}).get("swings")) for x in wins],
           "target_dead": dead, "hordes": len(w.get("hordes") or []), "misses": w.get("misses"),
           "strength_sum": round(sum(X.num(e.get("amount")) or 0.0 for e in ev), 6), "dropped": w.get("dropped"),
           "gate": w.get("gate")}
    if at_cap(w.get("gate")):
        obs["why"] = "the Strength experience was at the level-10 total (or unread) when the window opened"
        return "unmeasured", obs
    if ev:
        return "as_predicted", obs
    if not wins:
        obs["why"] = "no zombie came within 2 tiles: no swing window ran"
        return "unmeasured", obs
    if hits or dead:
        obs["why"] = "a hit evidenced and no positive Strength event"
        return "falsified", obs
    obs["why"] = "swings ran and no hit is evidenced"
    return "unmeasured", obs


# ---------------------------------------------------------------- the session
class Calib:
    """The scenario over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs):
        self.xs = xs
        self.out = xs.out
        self.D = self.out.setdefault("checks", {})

    # -- plumbing
    def k(self, tag, side, cmd, args="", log=True):
        return self.xs.keep(self.xs.step(tag, side, cmd, args, log=log))

    def lread(self, tag, side, root, paths):
        return self.k(tag, side, "lua.read", " ".join([root] + list(paths)))

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end:
            self.xs.check()
            self.xs.sleep(min(POLL_S, max(0.0, t_end - self.xs.clock())))

    def body_read(self, tag, log=False):
        a = self.k(tag, SRV, "stats.get", USER, log=log)
        return {"wall": a.get("wall"), "endurance": X.num(a.get("endurance")), "proteins": X.num(a.get("proteins")),
                "moving": a.get("moving"), "maxWeight": X.num(a.get("maxWeight")),
                "enduranceMoodle": X.num((a.get("moodles") or {}).get("endurance")),
                "heavyLoad": X.num((a.get("moodles") or {}).get("heavyLoad")), "worldAge": X.num(a.get("worldAge"))}

    def exe(self, tag, log=False):
        r = self.k(tag, SRV, "witness.chain", f"{USER} getFitness.getCurrentExe", log=log)
        v = r.get("value")
        on = v not in (None, "nil", "") and r.get("ok") is not False
        return {"wall": r.get("wall"), "value": v, "on": on}

    # -- the recorder (x42b's read)
    def xp_reset(self, tag):
        return self.k(tag, SRV, "lua.call", "TKX_TraitLevers.xpReset")

    def xp_read(self, tag):
        head = self.lread(tag + "_n", SRV, "_G", ["TKX_TraitLevers.xp.n", "TKX_TraitLevers.xp.calls",
                                                  "TKX_TraitLevers.xp.dropped"])
        hv = head.get("values") or {}
        n = int(X.num(hv.get("TKX_TraitLevers.xp.n")) or 0)
        reps = []
        per = 64 // len(EVENT_FIELDS)
        i = 1
        while i <= min(n, EVENT_CAP):
            j = min(n, i + per - 1)
            paths = [f"TKX_TraitLevers.xp.ev.{k}.{f}" for k in range(i, j + 1) for f in EVENT_FIELDS]
            reps.append(self.lread(f"{tag}_ev{i}", SRV, "_G", paths))
            i = j + 1
        return {"n": n, "calls": hv.get("TKX_TraitLevers.xp.calls"), "dropped": hv.get("TKX_TraitLevers.xp.dropped"),
                "events": event_rows(reps)}

    # -- the XP-cap gate (Task 0's lesson)
    def xp_gate(self, tag):
        g = {}
        a = self.k(tag + "_xp0", SRV, "perk.xp", f"{USER} Strength")
        g["xp_read"], g["level_read"] = X.num(a.get("xp")), X.num(a.get("level"))
        g["parked"] = False
        if g["xp_read"] is not None and g["xp_read"] >= CAP_XP:
            g["parked"] = True
            g["set"] = self.k(tag + "_set", SRV, "perk.set", f"{USER} Strength {PARK_LEVEL}")
            b = self.k(tag + "_xp1", SRV, "perk.xp", f"{USER} Strength")
            g["xp_open"], g["level_open"] = X.num(b.get("xp")), X.num(b.get("level"))
        else:
            g["xp_open"], g["level_open"] = g["xp_read"], g["level_read"]
        return g

    def rest(self, tag):
        return self.k(tag, SRV, "stats.setany", f"{USER} ENDURANCE 1")

    # -- phase S: the setting
    def phase_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.xs.snap("S_time")
        P["role"] = self.k("S_role", SRV, "witness.chain", f"{USER} getRole.getName")
        P["mult"] = self.lread("S_mult", SRV, "_G", ["SandboxVars.MultiplierConfig.Global",
                                                     "SandboxVars.MultiplierConfig.GlobalToggle",
                                                     "SandboxVars.MultiplierConfig.Strength", "SandboxVars.Nutrition",
                                                     "SandboxVars.DayLength", "TKX_TraitLevers.newGame.count",
                                                     "TKX_TraitLevers.server"])
        P["fitness"] = self.k("S_fit", SRV, "perk.xp", f"{USER} Fitness")
        P["strength"] = self.k("S_str", SRV, "perk.xp", f"{USER} Strength")
        P["body"] = self.body_read("S_body", log=True)

    # -- window P: the push-up set
    def phase_P(self):
        w = self.D["pushups"] = {"exe_seen": False}
        w["gate"] = self.xp_gate("P_gate")
        w["protein_set"] = self.k("P_protein", SRV, "nutrition.set", f"{USER} proteins {PROTEIN_SET}")
        w["store_before"] = X.num(self.k("P_store0", SRV, "nutrition.get", USER).get("proteins"))
        w["rest"] = self.rest("P_rest")
        w["body_before"] = self.body_read("P_body0", log=True)
        w["xp_before"] = self.k("P_xp_before", SRV, "perk.xp", f"{USER} Strength")
        w["reset"] = self.xp_reset("P_reset")
        w["ask"] = self.k("P_ask", CLI, "exercise.do", f"pushups {PUSHUP_ASK_M}")
        t_ask = self.xs.clock()
        polls, first_on, last_on = [], None, None
        while True:
            e = self.exe("P_exe")
            b = self.body_read("P_body")
            row = {"wall": e["wall"], "on": e["on"], "endurance": b["endurance"], "proteins": b["proteins"],
                   "moodle": b["enduranceMoodle"]}
            polls.append(row)
            if e["on"]:
                w["exe_seen"] = True
                last_on = e["wall"]
                if first_on is None:
                    first_on = e["wall"]
                    w["exe_value"] = e["value"]
                if b["endurance"] is not None and b["endurance"] <= ENDURANCE_STOP:
                    w["stop_reason"] = "endurance"
                    break
            elif w["exe_seen"]:
                w["stop_reason"] = "ended"
                break
            elif self.xs.clock() - t_ask > SET_START_CAP_S:
                w["stop_reason"] = "never_started"
                break
            if self.xs.clock() - t_ask > SET_CAP_S:
                w["stop_reason"] = "cap"
                break
            self.sleep_until(self.xs.clock() + POLL_S)
        if w["stop_reason"] in ("endurance", "cap", "never_started"):
            w["cancel"] = self.k("P_cancel", CLI, "action.cancel")
        end = self.xs.clock() + EXE_CLEAR_CAP_S
        clear = []
        w["exe_cleared"] = False
        while True:
            e = self.exe("P_clear")
            clear.append({"wall": e["wall"], "on": e["on"]})
            if e["on"]:
                last_on = e["wall"]
            else:
                w["exe_cleared"] = True
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + POLL_S)
        w["polls"] = polls
        w["clear_polls"] = clear
        w["first_on_wall"], w["last_on_wall"] = first_on, last_on
        w["set_s"] = round(last_on - first_on, 3) if (first_on is not None and last_on is not None) else None
        self.sleep_until(self.xs.clock() + SETTLE_S)
        w.update(self.xp_read("P_read"))
        w["xp_after"] = self.k("P_xp_after", SRV, "perk.xp", f"{USER} Strength")
        w["store_after"] = X.num(self.k("P_store1", SRV, "nutrition.get", USER).get("proteins"))
        w["body_after"] = self.body_read("P_body1", log=True)

    # -- window W: loaded movement
    def phase_W(self):
        w = self.D["walk"] = {"loaded": False, "load": []}
        w["gate"] = self.xp_gate("W_gate")
        w["rest"] = self.rest("W_rest")
        for i in range(LOAD_MAX_ADDS):
            a = self.k(f"W_load{i}", SRV, "inventory.add", f"{USER} {LOAD_ITEM} 1")
            w["load"].append({k: a.get(k) for k in ("ok", "invWeight", "maxWeight", "error", "raw")})
            iw, mw = X.num(a.get("invWeight")), X.num(a.get("maxWeight"))
            if iw is not None and mw and iw > LOAD_SHARE * mw:
                w["loaded"] = True
                break
        w["world_change"] = f"{len(w['load'])} x {LOAD_ITEM} left in admin's inventory"
        self.out["world_changes"]["left_in_place"].append(w["world_change"])
        w["xp_before"] = self.k("W_xp_before", SRV, "perk.xp", f"{USER} Strength")
        w["reset"] = self.xp_reset("W_reset")
        reads, legs = [], []
        t0 = self.xs.clock()
        t_end = t0 + WALK_S
        sign = 1
        while self.xs.clock() < t_end:
            c = self.k("W_cancel_leg", CLI, "action.cancel", log=False)
            r = self.k("W_walk", CLI, "player.walk", f"{sign * WALK_DX} 0", log=False)
            legs.append({"wall": r.get("wall"), "queued": r.get("queued"), "cancel_before": c.get("before"),
                         "error": r.get("error"), "raw": r.get("raw")})
            sign = -sign
            t_leg = min(t_end, self.xs.clock() + WALK_LEG_S)
            while self.xs.clock() < t_leg:
                b = self.body_read("W_body")
                iw = X.num(self.k("W_invw", SRV, "witness.chain", f"{USER} getInventoryWeight", log=False).get("value"))
                reads.append({"wall": b["wall"], "moving": b["moving"], "endurance": b["endurance"],
                              "heavyLoad": b["heavyLoad"], "maxWeight": b["maxWeight"], "invWeight": iw})
                self.sleep_until(min(t_leg, self.xs.clock() + 1.0))
        w["walk_s"] = round(self.xs.clock() - t0, 3)
        w["stop"] = self.k("W_stop", CLI, "action.cancel")
        end = self.xs.clock() + MOVE_CLEAR_CAP_S
        w["move_cleared"] = False
        while True:
            b = self.body_read("W_clear")
            if b["moving"] is not True:
                w["move_cleared"] = True
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + POLL_S)
        self.sleep_until(self.xs.clock() + SETTLE_S)
        w["reads"] = reads
        w["legs"] = legs
        w.update(self.xp_read("W_read"))
        w["xp_after"] = self.k("W_xp_after", SRV, "perk.xp", f"{USER} Strength")

    # -- window M: melee
    def phase_M(self):
        w = self.D["melee"] = {"windows": [], "hordes": [], "misses": 0}
        w["gate"] = self.xp_gate("M_gate")
        w["rest"] = self.rest("M_rest")
        w["xp_before"] = self.k("M_xp_before", SRV, "perk.xp", f"{USER} Strength")
        w["reset"] = self.xp_reset("M_reset")
        w["hordes"].append(self.xs.rcon(f"createhorde 1 {USER}", "M_horde"))
        self.out["world_changes"]["left_in_place"].append("zombies spawned by createhorde near admin in M")
        c = self.xs.clients.get(USER) if isinstance(self.xs.clients, dict) else None
        t_find = self.xs.clock()
        while len(w["windows"]) < MELEE_WINDOWS:
            self.xs.check()
            r = self.k("M_atk", CLI, "attack.melee", str(MELEE_SWINGS))
            if not r.get("ok"):
                w["misses"] += 1
                waited = self.xs.clock() - t_find
                if waited > MELEE_FIND_S:
                    self.xs.note(f"melee: no zombie within 2 tiles for {MELEE_FIND_S} s; {len(w['windows'])} window(s)")
                    break
                if waited > MELEE_FIND_S / 2 and len(w["hordes"]) < 2 + len(w["windows"]):
                    w["hordes"].append(self.xs.rcon(f"createhorde 1 {USER}", "M_horde"))
                self.sleep_until(self.xs.clock() + 2.0)
                continue
            started = self.xs.clock()
            win = {"reply": {k: r.get(k) for k in ("ok", "target", "swings", "weapon", "wall")}}
            res = None
            if c is not None and getattr(c, "bus", None) is not None:
                try:
                    res = c.bus.wait_result("attack-melee", timeout=MELEE_RESULT_S, after=started - 1.0)
                except Exception as e:             # noqa: BLE001
                    self.xs.note(f"melee: attack-melee result: {type(e).__name__}: {e}")
            else:
                self.sleep_until(started + MELEE_SWINGS * 1.2 + 2.0)
            win["result"] = res
            w["windows"].append(win)
            if isinstance(res, dict) and res.get("targetDead"):
                break
        self.sleep_until(self.xs.clock() + SETTLE_S)
        w.update(self.xp_read("M_read"))
        w["xp_after"] = self.k("M_xp_after", SRV, "perk.xp", f"{USER} Strength")

    def body(self, phases=None):
        for name, fn in (phases or (("S", self.phase_S), ("P", self.phase_P), ("W", self.phase_W),
                                    ("M", self.phase_M))):
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.xs.run_phase(name, fn)

    # -- the grade
    def grade_all(self):
        D, xs = self.D, self.xs
        v, o = grade_pushups(D.get("pushups"))
        xs.grade("pushups", v, o, "a set that ran with no Strength event or an amount off 6 x the protein factor",
                 samples=o.get("reps"))
        v, o = grade_walk(D.get("walk"))
        xs.grade("7_walk", v, o, "loaded and moving on the server with no positive Strength event")
        v, o = grade_melee(D.get("melee"))
        xs.grade("7_melee", v, o, "a hit evidenced with no positive Strength event")
        p = self.out["verdicts"]["pushups"]["observed"]
        self.out["reading"] = {"xp_per_set": p.get("xp_per_set"), "reps": p.get("reps"), "set_s": p.get("set_s"),
                               "event_span_s": p.get("event_span_s"), "xp_per_s": p.get("xp_per_s"),
                               "xp_delta": p.get("xp_delta"), "verdict": self.out["verdicts"]["pushups"]["verdict"],
                               "vanilla_strength_rate_s4": {"bout_xp": 346, "steady_xp_per_s": [1.8, 1.95]}}


# ---------------------------------------------------------------- the live run
def main(profile_name, prefix, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
           "world_changes": {"restored": "fixture default restored into the run dir (server and client caches)",
                             "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user="admin")
    xs.path = os.path.join(run_dir, artifact)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session": session_text, "driver": driver_file, "lib": LIB_FILE, "user": USER,
        "users": list(prof.users), "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
        "probe_dirty": git_dirty(PROBE_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "constants": {k: v for k, v in globals().items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
                      and isinstance(v, (int, float, str, bool, tuple)) and k not in ("REPO",)},
        "predictions": pred,
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"] or out["probe_dirty"]:
        xs.refuse("the harness Lua or the probe mod is dirty; commit before the boot (CLAUDE.md s5)")
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    cb = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        xs.mem("ready")
        xs.persist()
        cb = Calib(xs)
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            cb.body()
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, LOG_RX, 200, ECHO_RX,
                                                                         NEVER_RX)
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 60, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if cb is not None:
                cb.grade_all()

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "reading": out.get("reading"),
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
