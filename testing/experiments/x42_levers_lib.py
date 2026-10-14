"""x42_levers_lib -- the session engine of the Plan 13 Task 0 driver (x421_levers.py): the live engine checks of the
lean-mass Strength redesign before any build. One boot of profile x42-levers (fixture two: admin -debug, then bob, the
release user-role client; PZTestKit and the probe mod TKX_TraitLevers by its path; no NutritionRevamp, so no mod/ file
is booted; Nutrition false, DayLength 1). Built on testing/experiments/xlib.py (Plan 12 Task 4): the bus step with its
dead-bus handling, the phase runner, the wall budget, the grade recorder and the finish/copy skeleton are xlib's; the
two-client launch and the verify gate are x411_smoke.py's; the respawn route is x192_persist_mod.py's (Plan 8 Task 6:
health.reduce <user> 110, the client's ISPostDeathUI.instance.0 onRespawn and CoopCharacterCreation.instance accept
through lua.callm, the spawn list's clickNext when it is still up).

THE NINE CHECKS (the plan's Task 0 Step 5; the stop table is its Step 6). The subject is bob, the user-role client.
  1  the restated base:obese block replaces vanilla's on both sides: trait.def Obese on the server and on bob's client
     reads cost -10, free false, no Fitness boost, Overweight among the exclusions.
  2  the Lua list edits bind: trait.def Underweight reads no Fitness boost; trait.def Overweight lists Obese and not
     Athletic, on both sides; TKX_TraitLevers.edits holds no error on the server or either client.
  3  the client sees the server's definitions after the join: bob's trait.def answers equal the server's (cost, free,
     boosts, exclusions, grants) for the three traits; the marker description on the client is a reading only.
  4  OnNewGame writes reach the client: bob dies and respawns; once the server's TKX_TraitLevers.newGame.count rises,
     a same-second pair (the server's stats.get and perk.xp beside bob's client stats.get and perk.xp, each pair's two
     reads within PAIR_GAP_MAX_S of wall clock) is taken PAIR_DELAYS_S after the rise. The grade is the first pair
     (the CreatePlayer reply has landed by then): the client's weight 77.7, OUT_OF_SHAPE present and STRONG absent,
     the client's Strength level the server handler's stepped level. Later pairs are readings.
  5  an illegal pick list reaches OnNewGame: before the second respawn bob's client arms creation.picks Strong Stout
     Obese Overweight (over budget and mutually exclusive); the server's recorded known-trait list (newGame.before)
     holds all four.
  6  vanilla's band swap fires on the handler's LevelPerk step (ruling 13-8): the band trait after the step is the
     stepped level's band on both sides (server: newGame.after; client: the first pair), no other Strength band held;
     and a perk.level (setPerkLevelDebug) write to a level of another band shows no swap on either side after
     DEBUG_WAIT_S, as #2870 did. `route_swaps` names the 13-8 route's own reading.
  7  AddXP sees every Strength source: the probe's recorder is emptied before each source window, and each window's
     server AddXP events for bob are read back: pushups (exercise.do), a melee hit on a spawned target with the
     harness's baseball bat (attack.melee), loaded movement above half the max weight (inventory.add, player.walk) for
     WALK_S of wall clock. Each source needs at least one positive Strength event. The tree and barricade sources are
     ruled out (ruling 13-27).
  8  the level-10 park keeps AddXP firing: perk.set bob Strength 10, perk.park bob Strength 9, xp.grant bob Strength
     100: one Strength event whose amount is 100 times the protein factor of the store read beside it (#2112: 1.5 for
     50 < store < 300, 0.7 below -300) times the sandbox multiplier (MultiplierConfig.Global when GlobalToggle, else
     .Strength); the level stays 10 (the grant's reply and the listener's own read).
  9  the pin under the anti-cheat: on bob's user-role connection with the run's AntiCheatXP = 2, perk.set bob Strength
     7, then the ruling 13-9 pair (perk.park bob Strength 7, xp.grant bob Strength 30000), then PIN_WATCH_S of wall
     clock (two check intervals, #2860) polling the server's players list: bob stays online and the server log shows
     no anti-cheat line after the pair.

DEVIATIONS FROM THE BRIEF'S LITERAL VALUES (named before the run):
  - check 7's set is asked for PUSHUP_M game minutes, not 1: ISFitnessAction ends at startMS + timeToExe * 60000 of the
    game calendar (ISFitnessAction.lua:46, :212), one game minute is 0.625 s of wall clock at DayLength 1, and a
    pushup rep is 1300 ms (serverStart's period, :137), so a one-minute set ends before its first rep;
  - the melee target is spawned beside bob by the probe's TKX_TraitLevers.zombieNear (lua.call): the harness's
    zombie.near spawns beside the FIRST online player, which is admin in this session.

Reply shapes the lib reads are the harness's own (@reply lines): trait.def {ok, side, trait, field, cost, free, xpBoosts,
exclusive, granted, label, description}; creation.picks {ok, armed, picks}; perk.park {ok, perk, levelBefore, levelAfter,
xpBefore, xpAfter [, target]}; perk.xp {perk, side, xp, level}; stats.get {weight, traitList, ...}; lua.read {ok, side,
root, n, values, tables, types, missing}; lua.callm {ok, side, path, method, nargs, r1, r2, r3}; lua.call {ok, side,
path, nargs, r1, r2, r3}; witness.chain {ok, value, hops, failedAt}; health.reduce {ok, side, requested, before, after,
health, parts}; perk.set {perk, requested, side, before, ..., after, route}; perk.level {perk, requested, side, before,
after, xp}; xp.grant {ok, perk, amount, side, xpBefore, xpAfter, levelBefore, levelAfter}; exercise.do {ok, exercise,
minutes, queued, queueLen}; attack.melee {ok, target, swings, weapon, result, file} | {ok, reason}; inventory.add {ok,
fullType, count, side, invWeight, maxWeight}; player.walk {dx, dy, run, from, target, queued, ...}; players a list or {}.

FROZEN WITH ITS FIRST RUN: once x421 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

import xlib as X                                                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
SRV = "server"
LIB_FILE = "x42_levers_lib.py"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
PROBE_DIR = "testing/experiments/TKX_TraitLevers"
USER = "bob"
CLI = "client:bob"
ADMIN_CLI = "client"
PROBE = "TKX_TraitLevers"
MIN_FREE_GB = 12.0
POLL_S = 0.5
DEATH_CAP_S = 20.0
UI_CAP_S = 30.0
CREATE_CAP_S = 15.0
NEWGAME_CAP_S = 60.0
PAIR_DELAYS_S = (3.0, 10.0, 30.0)     # after the server's newGame.count rises
PAIR_GAP_MAX_S = 1.0
DEBUG_WAIT_S = 5.0
WEIGHT_TARGET = 77.7
WEIGHT_TOL = 0.05
PUSHUP_M = 30                          # game minutes asked of the pushup set (18.75 s of wall clock at DayLength 1)
SET_CAP_S = 60.0
MELEE_SWINGS = 3
MELEE_WAIT_S = 8.0
ZOMBIE_WAIT_S = 2.0
LOAD_ITEM = "Base.Plank"
LOAD_ADD = 2
LOAD_MAX_ADDS = 12
LOAD_SHARE = 0.6                       # load above this share of the max weight (vanilla's gate is 0.5)
WALK_S = 60.0
WALK_DX = 6
WALK_LEG_S = 5.0
GRANT = 100.0
PIN_LEVEL = 7
PIN_GRANT = 30000.0
PIN_WATCH_S = 130.0                    # two 60000 ms check intervals and a margin (#2860)
PIN_POLL_S = 5.0
REL_TOL = 1e-4
EVENT_FIELDS = ("user", "perk", "amount", "ms", "protein", "fitness", "level", "xp")
EVENT_CAP = 200
BANDS = ("weak", "feeble", "stout", "strong")
ILLEGAL_PICKS = ("Strong", "Stout", "Obese", "Overweight")
TRAITS = ("Obese", "Underweight", "Overweight")
MARKER = "TKX-TRAITLEVERS-MARKER"
ECHO_RX = re.compile(r"PZTK: ")
AC_RX = re.compile(r"xp growth is too high|update failed|AntiCheatXP|anticheat|anti-cheat|kick|doKickUser|doLogUser|"
                   r"suspicious", re.I)
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"TKX_TraitLevers|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)


# ---------------------------------------------------------------- pure helpers (shared with the tests)
def norm(name):
    """A trait name in one spelling: lower case, the registry prefix and every space or underscore dropped
    (out of shape, OUT_OF_SHAPE and base:out of shape all read outofshape)."""
    s = str(name).lower().split(":")[-1]
    return re.sub(r"[\s_]", "", s)


def names(v):
    """A reply's list of names (a JSON array, {} for an empty Lua table, or a comma-joined string) as a set."""
    if isinstance(v, str):
        return {norm(x) for x in v.split(",") if x.strip()}
    if isinstance(v, dict):
        v = list(v.values())
    if isinstance(v, list):
        return {norm(x) for x in v}
    return set()


def band_of(level):
    """The Strength band vanilla's LevelPerk listener holds for a level (XpUpdate.lua:208-216); None at 5."""
    lv = X.num(level)
    if lv is None:
        return None
    if lv <= 1:
        return "weak"
    if lv <= 4:
        return "feeble"
    if lv == 5:
        return None
    if lv <= 8:
        return "stout"
    return "strong"


def band_ok(traits, level):
    """The held Strength bands are exactly the level's band (none at 5)."""
    held = {b for b in BANDS if b in traits}
    want = band_of(level)
    return held == ({want} if want else set()), sorted(held), want


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


def sandbox_mult(values):
    """The sandbox Strength multiplier AddXP applies (XP.AddXP @757-@823): Global when GlobalToggle, else Strength."""
    tog = values.get("SandboxVars.MultiplierConfig.GlobalToggle")
    if tog is True or str(tog).lower() == "true":
        return X.num(values.get("SandboxVars.MultiplierConfig.Global"))
    return X.num(values.get("SandboxVars.MultiplierConfig.Strength"))


def close(a, b, rel=REL_TOL):
    a, b = X.num(a), X.num(b)
    if a is None or b is None:
        return False
    return abs(a - b) <= rel * max(1.0, abs(b))


def def_view(r):
    """The comparable part of a trait.def reply."""
    if not isinstance(r, dict) or r.get("ok") is not True:
        return None
    boosts = r.get("xpBoosts") if isinstance(r.get("xpBoosts"), dict) else {}
    return {"cost": X.num(r.get("cost")), "free": r.get("free"),
            "xpBoosts": {str(k): X.num(v) for k, v in boosts.items()},
            "exclusive": sorted(names(r.get("exclusive"))), "granted": sorted(names(r.get("granted")))}


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


# ---------------------------------------------------------------- the grades (pure; each has a failing case in the tests)
def grade_obese(defs):
    """Check 1 off {side: trait.def reply} for Obese."""
    obs, ok = {}, True
    for side, r in defs.items():
        v = def_view(r)
        row = {"read": v is not None}
        if v is None:
            ok = False
            obs[side] = row
            continue
        row.update(cost=v["cost"], free=v["free"], fitness_boost=v["xpBoosts"].get("Fitness"),
                   overweight_excluded="overweight" in v["exclusive"])
        row["ok"] = (v["cost"] == -10 and v["free"] is False and "Fitness" not in v["xpBoosts"]
                     and row["overweight_excluded"])
        ok = ok and row["ok"]
        obs[side] = row
    return ("as_predicted" if ok and defs else "falsified"), obs


def grade_edits(under, over, edits):
    """Check 2: {side: reply} for Underweight and Overweight, and {side: lua.read reply} of the probe's edits."""
    obs, ok = {}, bool(under) and bool(over) and bool(edits)
    for side in sorted(set(under) | set(over)):
        u, o = def_view(under.get(side)), def_view(over.get(side))
        row = {"underweight_read": u is not None, "overweight_read": o is not None}
        if u is None or o is None:
            ok = False
            obs[side] = row
            continue
        row.update(underweight_fitness=u["xpBoosts"].get("Fitness"), overweight_exclusive=o["exclusive"])
        row["ok"] = ("Fitness" not in u["xpBoosts"] and "obese" in o["exclusive"] and "athletic" not in o["exclusive"])
        ok = ok and row["ok"]
        obs[side] = row
    errs = {}
    for side, rep in edits.items():
        vals = (rep or {}).get("values") or {}
        n = X.num(vals.get("TKX_TraitLevers.edits.errors"))
        each = {k: vals.get(f"TKX_TraitLevers.edits.{k}.ok") for k in ("underweightFitness", "overweightAthletic",
                                                                      "overweightObese")}
        errs[side] = {"errors": n, "each_ok": each}
        if n != 0 or not all(v is True for v in each.values()):
            ok = False
    obs["edits"] = errs
    return ("as_predicted" if ok else "falsified"), obs


def grade_equal(server_defs, client_defs, client_desc):
    """Check 3: the client's definitions equal the server's for each trait; the marker is a reading."""
    obs, ok = {}, bool(server_defs)
    for t in sorted(server_defs):
        s, c = def_view(server_defs.get(t)), def_view(client_defs.get(t))
        eq = s is not None and c is not None and s == c
        obs[t] = {"equal": eq, "server": s, "client": c}
        ok = ok and eq
    obs["marker_on_client"] = isinstance(client_desc, str) and MARKER in client_desc
    obs["client_description"] = client_desc
    return ("as_predicted" if ok else "falsified"), obs


def pair_view(p):
    """A same-second pair's comparable reads."""
    sc, cc = p.get("server_stats") or {}, p.get("client_stats") or {}
    sx, cx = p.get("server_xp") or {}, p.get("client_xp") or {}
    gaps = [abs(X.num(cc.get("wall")) - X.num(sc.get("wall")))
            if X.num(cc.get("wall")) is not None and X.num(sc.get("wall")) is not None else None,
            abs(X.num(cx.get("wall")) - X.num(sx.get("wall")))
            if X.num(cx.get("wall")) is not None and X.num(sx.get("wall")) is not None else None]
    return {"delay": p.get("delay"), "gap": max(g for g in gaps if g is not None) if any(g is not None for g in gaps)
            else None, "server_weight": X.num(sc.get("weight")), "client_weight": X.num(cc.get("weight")),
            "server_traits": sorted(names(sc.get("traitList"))), "client_traits": sorted(names(cc.get("traitList"))),
            "server_level": X.num(sx.get("level")), "client_level": X.num(cx.get("level")),
            "server_xp": X.num(sx.get("xp")), "client_xp": X.num(cx.get("xp"))}


def grade_newgame(ng, pairs):
    """Check 4: the handler's after state reached the client by the first pair."""
    if not ng or not pairs:
        return "unmeasured", {"newGame": bool(ng), "pairs": len(pairs or [])}
    after = ng.get("after") or {}
    lvl = X.num(after.get("strength"))
    views = [pair_view(p) for p in pairs]
    rows = []
    for v in views:
        ct = set(v["client_traits"])
        row = {"delay": v["delay"], "gap": v["gap"], "weight": v["client_weight"],
               "weight_ok": v["client_weight"] is not None and abs(v["client_weight"] - WEIGHT_TARGET) <= WEIGHT_TOL,
               "out_of_shape": "outofshape" in ct, "strong_absent": "strong" not in ct,
               "level": v["client_level"], "level_ok": lvl is not None and v["client_level"] == lvl,
               "pair_ok": v["gap"] is not None and v["gap"] <= PAIR_GAP_MAX_S}
        row["ok"] = row["weight_ok"] and row["out_of_shape"] and row["strong_absent"] and row["level_ok"]
        rows.append(row)
    first = rows[0]
    obs = {"server_after": {"weight": after.get("weight"), "strength": lvl, "traits": after.get("traitsStr")},
           "pairs": rows, "first_ok": first["ok"], "later_ok": [r["ok"] for r in rows[1:]]}
    if not first["pair_ok"]:
        return "unmeasured", obs
    return ("as_predicted" if first["ok"] else "falsified"), obs


def grade_illegal(ng2, fired):
    """Check 5: the server's known-trait list before the handler holds every illegal pick."""
    if not ng2 or not fired or X.num(fired.get("count")) in (None, 0):
        return "unmeasured", {"newGame": bool(ng2), "fired": fired}
    before = names((ng2.get("before") or {}).get("traitsStr"))
    want = {norm(p) for p in ILLEGAL_PICKS}
    obs = {"before_traits": sorted(before), "want": sorted(want), "missing": sorted(want - before), "fired": fired}
    return ("as_predicted" if want <= before else "falsified"), obs


def grade_band(ng, first_pair, debug):
    """Check 6: the handler's LevelPerk step holds the stepped level's band on both sides; the debug write swaps none."""
    if not ng or not first_pair:
        return "unmeasured", {"newGame": bool(ng), "pair": bool(first_pair)}
    after = ng.get("after") or {}
    lvl = X.num(after.get("strength"))
    s_ok, s_held, want = band_ok(names(after.get("traitsStr")), lvl)
    v = pair_view(first_pair)
    c_ok, c_held, _ = band_ok(set(v["client_traits"]), lvl)
    route = s_ok and c_ok and (ng.get("writes") or {}).get("step") in ("LevelPerk", "LoseLevel")
    obs = {"stepped_level": lvl, "want_band": want, "server_bands": s_held, "client_bands": c_held,
           "client_level": v["client_level"], "step": (ng.get("writes") or {}).get("step"), "route_swaps": route}
    if not debug or not debug.get("pair"):
        obs["debug"] = "unmeasured"
        return ("as_predicted" if route else "falsified"), obs
    dv = pair_view(debug["pair"])
    before_band = debug.get("band_before")
    target_band = band_of(debug.get("level"))
    swapped = {side: (target_band in set(dv[f"{side}_traits"])) or (before_band is not None and before_band not in
                                                                     set(dv[f"{side}_traits"]))
               for side in ("server", "client")}
    obs["debug"] = {"level": debug.get("level"), "band_before": before_band, "target_band": target_band,
                    "server_traits": dv["server_traits"], "client_traits": dv["client_traits"], "swapped": swapped,
                    "server_level": dv["server_level"], "client_level": dv["client_level"]}
    obs["debug_no_swap"] = not any(swapped.values())
    return ("as_predicted" if route and obs["debug_no_swap"] else "falsified"), obs


def grade_sources(windows):
    """Check 7: each source window holds at least one positive Strength AddXP event for the user."""
    if not windows:
        return "unmeasured", {}
    obs, ok, measured = {}, True, True
    for name, w in windows.items():
        ev = strength_events(w.get("events") or [])
        row = {"events": len(ev), "amounts": [X.num(e.get("amount")) for e in ev][:20],
               "fitness_flags": sorted({bool(e.get("fitness")) for e in ev}), "all_events": len(w.get("events") or []),
               "dropped": w.get("dropped"), "ran": w.get("ran")}
        if not w.get("ran"):
            measured = False
        row["ok"] = len(ev) > 0
        ok = ok and row["ok"]
        obs[name] = row
    obs["silent_sources"] = sorted(k for k, v in obs.items() if isinstance(v, dict) and not v.get("ok"))
    if not measured and not ok:
        return "unmeasured", obs
    return ("as_predicted" if ok else "falsified"), obs


def grade_park(park):
    """Check 8: one Strength event of the full grant (after the protein factor and the sandbox multiplier) at level 10."""
    ev = strength_events(park.get("events") or [], positive=False)
    grant = park.get("grant") or {}
    mult = park.get("mult")
    obs = {"events": [{k: e.get(k) for k in ("amount", "protein", "level", "xp")} for e in ev], "mult": mult,
           "grant": {k: grant.get(k) for k in ("ok", "xpBefore", "xpAfter", "levelBefore", "levelAfter")},
           "park": {k: (park.get("park") or {}).get(k) for k in ("ok", "levelBefore", "levelAfter", "xpBefore",
                                                                "xpAfter")},
           "level_after_read": park.get("level_after")}
    if not ev:
        obs["why"] = "no Strength AddXP event after the grant"
        return "falsified", obs
    e = ev[-1]
    pf = protein_factor(e.get("protein"))
    want = GRANT * pf * mult if (pf is not None and X.num(mult) is not None) else None
    obs.update(expected=want, protein_factor=pf, amount=X.num(e.get("amount")))
    ok = (len(ev) == 1 and want is not None and close(e.get("amount"), want)
          and X.num(grant.get("levelAfter")) == 10 and X.num(e.get("level")) == 10
          and X.num(park.get("level_after")) == 10)
    return ("as_predicted" if ok else "falsified"), obs


def grade_pin(pin):
    """Check 9: bob stays online across PIN_WATCH_S after the pair and the log shows no anti-cheat line."""
    role = str(pin.get("role") or "").lower()
    ac = pin.get("anticheat_xp")
    polls = pin.get("polls") or []
    obs = {"role": pin.get("role"), "access": pin.get("access"), "anticheat_xp": ac, "polls": len(polls),
           "online_all": bool(polls) and all(p.get("online") for p in polls), "ac_lines": pin.get("ac_lines") or [],
           "span_s": pin.get("span_s"), "grant": pin.get("grant"), "park": pin.get("park")}
    if role in ("admin", "moderator", "gm", "observer") or str(ac) != "2":
        obs["why"] = "not a user-role connection under AntiCheatXP=2"
        return "unmeasured", obs
    if (X.num(pin.get("span_s")) or 0) < 120.0 or not polls:
        obs["why"] = "the watch was shorter than two check intervals"
        return "unmeasured", obs
    return ("as_predicted" if obs["online_all"] and not obs["ac_lines"] else "falsified"), obs


# ---------------------------------------------------------------- the session
class Levers:
    """The scenario over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs, log_path=None, ini_path=None):
        self.xs = xs
        self.out = xs.out
        self.log_path = log_path
        self.ini_path = ini_path
        self.D = self.out.setdefault("checks", {})

    # -- plumbing
    def k(self, tag, side, cmd, args=""):
        return self.xs.keep(self.xs.step(tag, side, cmd, args))

    def lread(self, tag, side, root, paths):
        return self.k(tag, side, "lua.read", " ".join([root] + list(paths)))

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end:
            self.xs.check()
            self.xs.sleep(min(POLL_S, max(0.0, t_end - self.xs.clock())))

    def log_mark(self):
        try:
            return os.path.getsize(self.log_path) if self.log_path else 0
        except OSError:
            return 0

    def lines_since(self, rx, mark, limit=60):
        if not self.log_path:
            return []
        out = []
        try:
            with open(self.log_path, encoding="utf-8", errors="replace") as fh:
                fh.seek(mark)
                for line in fh:
                    if rx.search(line) and not ECHO_RX.search(line):
                        out.append(line.strip()[:400])
                        if len(out) >= limit:
                            break
        except OSError:
            pass
        return out

    # -- phase S: the setting
    def phase_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["time"] = self.xs.snap("S_time")
        P["role"] = self.k("S_role", SRV, "witness.chain", f"{USER} getRole.getName")
        P["access"] = self.k("S_access", SRV, "witness.chain", f"{USER} getAccessLevel")
        P["mult"] = self.lread("S_mult", SRV, "_G", ["SandboxVars.MultiplierConfig.Global",
                                                     "SandboxVars.MultiplierConfig.GlobalToggle",
                                                     "SandboxVars.MultiplierConfig.Strength", "SandboxVars.Nutrition",
                                                     "SandboxVars.DayLength"])
        ini = {}
        if self.ini_path:
            try:
                with open(self.ini_path, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        m = re.match(r"^(AntiCheat\w*)=(.*)$", line.strip())
                        if m:
                            ini[m.group(1)] = m.group(2)
            except OSError as e:
                ini["error"] = f"{type(e).__name__}: {e}"
        P["ini"] = ini

    # -- phase D: checks 1-3
    def phase_D(self):
        P = self.D["defs"] = {"server": {}, "bob": {}, "admin": {}}
        for t in TRAITS:
            P["server"][t] = self.k(f"D_{t}_s", SRV, "trait.def", t)
            P["bob"][t] = self.k(f"D_{t}_bob", CLI, "trait.def", t)
            P["admin"][t] = self.k(f"D_{t}_adm", ADMIN_CLI, "trait.def", t)
        paths = ["TKX_TraitLevers.edits.errors"] + [f"TKX_TraitLevers.edits.{k}.{f}" for k in
                                                   ("underweightFitness", "overweightAthletic", "overweightObese")
                                                   for f in ("ok", "ret", "err")]
        self.D["edits"] = {"server": self.lread("D_edits_s", SRV, "_G", paths),
                           "bob": self.lread("D_edits_bob", CLI, "_G", paths),
                           "admin": self.lread("D_edits_adm", ADMIN_CLI, "_G", paths)}

    # -- the respawn route (x192's)
    def mcall(self, tag, args):
        return self.k(tag, CLI, "lua.callm", args)

    def newgame_count(self, tag):
        a = self.lread(tag, SRV, "_G", ["TKX_TraitLevers.newGame.count"])
        return X.num((a.get("values") or {}).get("TKX_TraitLevers.newGame.count")) or 0

    def respawn(self, label):
        R = {"label": label}
        R["count_before"] = self.newgame_count(label + "_ng0")
        R["reduce"] = self.k(label + "_reduce", SRV, "health.reduce", f"{USER} 110")
        polls, end = [], self.xs.clock() + DEATH_CAP_S
        R["dead"] = False
        while True:
            r = self.k(label + "_isDead", SRV, "witness.chain", f"{USER} isDead")
            polls.append({"wall": r.get("wall"), "value": r.get("value")})
            if str(r.get("value")).lower() == "true":
                R["dead"] = True
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + POLL_S)
        R["dead_polls"] = polls
        if not R["dead"]:
            R["unmeasured"] = "the server never read bob dead"
            return R
        end = self.xs.clock() + UI_CAP_S
        R["ui"] = None
        while True:
            r = self.mcall(label + "_ui", "ISPostDeathUI.instance.0 getIsVisible")
            if r.get("ok"):
                R["ui"] = {"wall": r.get("wall"), "r1": r.get("r1")}
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + 1.0)
        if R["ui"] is None:
            R["unmeasured"] = "the post-death UI never appeared at ISPostDeathUI.instance.0"
            return R
        R["onRespawn"] = self.mcall(label + "_onRespawn", "ISPostDeathUI.instance.0 onRespawn")
        scr, end = [], self.xs.clock() + CREATE_CAP_S
        while True:
            row = {"wall": self.xs.wall(),
                   "coop": self.k(label + "_coop", CLI, "lua.global", "CoopCharacterCreation.instance").get("type"),
                   "spawn": self.mcall(label + "_spawn", "CoopMapSpawnSelect.instance getIsVisible").get("r1"),
                   "profession": self.mcall(label + "_prof", "CharacterCreationProfession.instance getIsVisible").get(
                       "r1"),
                   "main": self.mcall(label + "_main", "CharacterCreationMain.instance getIsVisible").get("r1")}
            scr.append(row)
            if row["main"] is True and row["spawn"] is not True and row["profession"] is not True:
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + 1.0)
        R["screens"] = scr
        if scr and scr[-1].get("spawn") is True:
            R["clickNext"] = self.mcall(label + "_clickNext", "CoopMapSpawnSelect.instance clickNext")
            self.sleep_until(self.xs.clock() + 3.0)
        R["accept"] = self.mcall(label + "_accept", "CoopCharacterCreation.instance accept")
        R["accept_wall"] = self.xs.wall()
        end = self.xs.clock() + NEWGAME_CAP_S
        R["landed"] = False
        while True:
            n = self.newgame_count(label + "_ng")
            if n > R["count_before"]:
                R["landed"], R["landed_wall"], R["count_after"] = True, self.xs.wall(), n
                R["landed_clock"] = self.xs.clock()
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + POLL_S)
        if not R["landed"]:
            R["unmeasured"] = "the server's newGame.count never rose"
        return R

    def read_newgame(self, tag):
        keys = ["count", "user", "squareNil", "writes.step", "writes.stepCall.ok", "writes.weight.ok",
                "writes.addOutOfShape.ok", "writes.removeStrong.ok", "writes.stepCall.ret"]
        for part in ("before", "after"):
            keys += [f"{part}.{f}" for f in ("traitsStr", "weight", "strength", "strengthXp", "fitness", "fitnessXp",
                                              "hasStrong", "hasStout", "hasOutOfShape", "ms")]
        a = self.lread(tag, SRV, "TKX_TraitLevers.newGame", keys)
        vals = a.get("values") or {}
        ng = {"before": {}, "after": {}, "writes": {}}
        for k, v in vals.items():
            head, _, rest = k.partition(".")
            if head in ("before", "after") and rest:
                ng[head][rest] = v
            elif head == "writes" and rest:
                ng["writes"][rest] = v
            else:
                ng[k] = v
        ng["writes"]["step"] = ng["writes"].get("step")
        ng["missing"] = a.get("missing")
        return ng

    def pair(self, tag, delay=None):
        p = {"delay": delay}
        p["server_stats"] = self.k(tag + "_s_stats", SRV, "stats.get", USER)
        p["client_stats"] = self.k(tag + "_c_stats", CLI, "stats.get")
        p["server_xp"] = self.k(tag + "_s_xp", SRV, "perk.xp", f"{USER} Strength")
        p["client_xp"] = self.k(tag + "_c_xp", CLI, "perk.xp", "Strength")
        return p

    def after_respawn(self, label, R, delays=PAIR_DELAYS_S):
        """The handler's record, then one same-second pair at each delay after the server's newGame.count rose."""
        R["newGame"] = self.read_newgame(label + "_newgame")
        t_land = R.get("landed_clock")
        if t_land is None:
            t_land = self.xs.clock()
        pairs = []
        for i, d in enumerate(delays):
            self.sleep_until(t_land + d)
            pairs.append(self.pair(f"{label}_P{i + 1}", delay=d))
        R["pairs"] = pairs
        return R

    # -- phase N1: the first respawn (checks 4 and 6), then the debug write (check 6's second half)
    def phase_N1(self):
        R = self.D["N1"] = self.respawn("N1")
        if R.get("landed"):
            self.after_respawn("N1", R)

    def phase_B(self):
        N1 = self.D.get("N1") or {}
        ng = N1.get("newGame") or {}
        lvl = X.num((ng.get("after") or {}).get("strength"))
        if lvl is None:
            self.D["B"] = {"unmeasured": "no stepped level"}
            return
        target = 3 if band_of(lvl) != "feeble" else 7
        B = self.D["B"] = {"level": target, "band_before": band_of(lvl)}
        B["write"] = self.k("B_perk_level", SRV, "perk.level", f"{USER} Strength {target}")
        self.sleep_until(self.xs.clock() + DEBUG_WAIT_S)
        B["pair"] = self.pair("B_P", delay=DEBUG_WAIT_S)

    # -- phase N2: the illegal pick list (check 5)
    def phase_N2(self):
        A = self.D["N2_arm"] = self.k("N2_picks", CLI, "creation.picks", " ".join(ILLEGAL_PICKS))
        if A.get("armed") is not True:
            self.D["N2"] = {"unmeasured": "creation.picks did not arm"}
            return
        R = self.D["N2"] = self.respawn("N2")
        fired = self.lread("N2_fired", CLI, "_G", ["TK.picksFired.count", "TK.picksFired.wall", "TK.picksFired.error"]
                           + [f"TK.picksFired.listAfter.{i}" for i in range(1, 7)])
        vals = fired.get("values") or {}
        R["fired"] = {"count": vals.get("TK.picksFired.count"), "error": vals.get("TK.picksFired.error"),
                      "listAfter": [vals[f"TK.picksFired.listAfter.{i}"] for i in range(1, 7)
                                    if f"TK.picksFired.listAfter.{i}" in vals]}
        if R.get("landed"):
            self.after_respawn("N2", R, delays=PAIR_DELAYS_S[:1])

    # -- the recorder
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

    # -- phase S7: the Strength sources (check 7)
    def phase_S7(self):
        W = self.D["S7"] = {}
        # pushups
        self.xp_reset("S7_push_reset")
        w = W["pushups"] = {"ran": False}
        w["ask"] = self.k("S7_push", CLI, "exercise.do", f"pushups {PUSHUP_M}")
        seen, end = False, self.xs.clock() + SET_CAP_S
        polls = []
        while self.xs.clock() < end:
            r = self.k("S7_push_exe", SRV, "witness.chain", f"{USER} getFitness.getCurrentExe")
            v = r.get("value")
            polls.append({"wall": r.get("wall"), "value": v})
            if v not in (None, "nil", "") and r.get("ok") is not False:
                seen = True
            elif seen:
                break
            self.sleep_until(self.xs.clock() + 1.0)
        w["exe_polls"] = polls[:4] + polls[-4:] if len(polls) > 8 else polls
        w["exe_seen"] = seen
        w["ran"] = seen
        w.update(self.xp_read("S7_push_read"))
        # melee
        self.xp_reset("S7_melee_reset")
        w = W["melee"] = {"ran": False}
        w["zombie"] = self.k("S7_zombie", SRV, "lua.call", f"TKX_TraitLevers.zombieNear {USER}")
        self.sleep_until(self.xs.clock() + ZOMBIE_WAIT_S)
        w["attack"] = self.k("S7_attack", CLI, "attack.melee", str(MELEE_SWINGS))
        w["ran"] = w["attack"].get("ok") is True
        self.sleep_until(self.xs.clock() + MELEE_WAIT_S)
        w.update(self.xp_read("S7_melee_read"))
        # loaded movement
        self.xp_reset("S7_walk_reset")
        w = W["walk"] = {"ran": False, "adds": []}
        for i in range(LOAD_MAX_ADDS):
            a = self.k(f"S7_load{i}", SRV, "inventory.add", f"{USER} {LOAD_ITEM} {LOAD_ADD}")
            w["adds"].append({k: a.get(k) for k in ("ok", "invWeight", "maxWeight", "error", "raw")})
            iw, mw = X.num(a.get("invWeight")), X.num(a.get("maxWeight"))
            if iw is not None and mw and iw > LOAD_SHARE * mw:
                w["loaded"] = True
                break
        w["walks"] = []
        if w.get("loaded"):
            self.xp_reset("S7_walk_reset2")
            t_end = self.xs.clock() + WALK_S
            sign = 1
            while self.xs.clock() < t_end:
                r = self.k("S7_walk", CLI, "player.walk", f"{sign * WALK_DX} 0")
                w["walks"].append({k: r.get(k) for k in ("queued", "wall", "error", "raw")})
                sign = -sign
                self.sleep_until(min(t_end, self.xs.clock() + WALK_LEG_S))
            w["ran"] = any(x.get("queued") for x in w["walks"])
            w["moved_s"] = WALK_S
        w.update(self.xp_read("S7_walk_read"))
        w["load_after"] = self.k("S7_load_after", SRV, "stats.get", USER).get("maxWeight")

    # -- phase S8: the level-10 park (check 8)
    def phase_S8(self):
        P = self.D["S8"] = {}
        P["set"] = self.k("S8_set10", SRV, "perk.set", f"{USER} Strength 10")
        P["park"] = self.k("S8_park9", SRV, "perk.park", f"{USER} Strength 9")
        P["reset"] = self.xp_reset("S8_reset")
        P["grant"] = self.k("S8_grant", SRV, "xp.grant", f"{USER} Strength {GRANT:g}")
        rd = self.xp_read("S8_read")
        P["events"] = rd["events"]
        P["n"] = rd["n"]
        P["level_after"] = self.k("S8_level", SRV, "perk.xp", f"{USER} Strength").get("level")
        mult = (self.D.get("S") or {}).get("mult") or {}
        P["mult"] = sandbox_mult(mult.get("values") or {})

    # -- phase S9: the pin under the anti-cheat (check 9)
    def phase_S9(self):
        P = self.D["S9"] = {}
        S = self.D.get("S") or {}
        P["role"] = (S.get("role") or {}).get("value")
        P["access"] = (S.get("access") or {}).get("value")
        P["anticheat_xp"] = (S.get("ini") or {}).get("AntiCheatXP")
        P["set"] = self.k("S9_set", SRV, "perk.set", f"{USER} Strength {PIN_LEVEL}")
        mark = self.log_mark()
        t0 = self.xs.clock()
        P["park"] = self.k("S9_park", SRV, "perk.park", f"{USER} Strength {PIN_LEVEL}")
        P["grant"] = self.k("S9_grant", SRV, "xp.grant", f"{USER} Strength {PIN_GRANT:g}")
        polls = []
        end = t0 + PIN_WATCH_S
        while self.xs.clock() < end:
            self.sleep_until(min(end, self.xs.clock() + PIN_POLL_S))
            r = self.xs.step("S9_players", SRV, "players", log=False)
            lst = r.get("ack")
            online = isinstance(lst, list) and USER in lst
            polls.append({"wall": r.get("wall_before"), "online": online})
        P["polls"] = polls
        P["span_s"] = round(self.xs.clock() - t0, 1)
        P["ac_lines"] = self.lines_since(AC_RX, mark)
        P["after"] = self.k("S9_after", SRV, "perk.xp", f"{USER} Strength")

    def body(self, phases=None):
        for name, fn in (phases or (("S", self.phase_S), ("D", self.phase_D), ("N1", self.phase_N1),
                                    ("B", self.phase_B), ("N2", self.phase_N2), ("S7", self.phase_S7),
                                    ("S8", self.phase_S8), ("S9", self.phase_S9))):
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.xs.run_phase(name, fn)

    # -- the grade
    def grade_all(self):
        D, xs = self.D, self.xs
        defs = D.get("defs") or {}
        sv, bob = defs.get("server") or {}, defs.get("bob") or {}
        v, o = grade_obese({"server": sv.get("Obese"), "bob": bob.get("Obese")})
        xs.grade("1", v, o, "a side reads cost 0, free true, a Fitness boost or no Overweight exclusion")
        edits = D.get("edits") or {}
        v, o = grade_edits({"server": sv.get("Underweight"), "bob": bob.get("Underweight")},
                           {"server": sv.get("Overweight"), "bob": bob.get("Overweight")}, edits)
        xs.grade("2", v, o, "a Fitness boost on Underweight, Athletic or no Obese on Overweight, or an edit error")
        v, o = grade_equal(sv, bob, (bob.get("Obese") or {}).get("description"))
        o["admin_equal"] = {t: def_view((defs.get("admin") or {}).get(t)) == def_view(sv.get(t)) for t in TRAITS}
        xs.grade("3", v, o, "a client definition that differs from the server's")
        N1 = D.get("N1") or {}
        pairs = N1.get("pairs") or []
        v, o = grade_newgame(N1.get("newGame"), pairs)
        o["respawn"] = {k: N1.get(k) for k in ("dead", "landed", "unmeasured", "count_before", "count_after")}
        xs.grade("4", v, o, "the first pair's client weight, OUT_OF_SHAPE, STRONG or Strength level off the server's")
        N2 = D.get("N2") or {}
        v, o = grade_illegal(N2.get("newGame"), N2.get("fired"))
        o["respawn"] = {k: N2.get(k) for k in ("dead", "landed", "unmeasured")}
        xs.grade("5", v, o, "an illegal pick missing from the server's known traits before the handler")
        v, o = grade_band(N1.get("newGame"), pairs[0] if pairs else None, D.get("B"))
        xs.grade("6", v, o, "the stepped level's band missing on a side, or the debug write swapping the band")
        v, o = grade_sources(D.get("S7") or {})
        xs.grade("7", v, o, "a source window with no positive Strength AddXP event")
        v, o = grade_park(D.get("S8") or {})
        xs.grade("8", v, o, "no event, an amount off the full grant, or the level leaving 10")
        v, o = grade_pin(D.get("S9") or {})
        xs.grade("9", v, o, "bob kicked or an anti-cheat line after the pair")


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
           "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
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
    lv = None
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
        lv = Levers(xs, log_path=server.log_path, ini_path=server.ini)
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            lv.body()
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "ac": AC_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, LOG_RX, 200, ECHO_RX,
                                                                         NEVER_RX)
                L["server_ac"], _ = X.grep_noecho(server.log_path, AC_RX, 200, ECHO_RX, NEVER_RX)
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 60, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if lv is not None:
                lv.grade_all()

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
