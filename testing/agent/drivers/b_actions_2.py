"""b_actions_2 -- Plan 21b Stage B pass 2 (spec § 4.2): the actions' go/no-go again, after pass 1 (run
b_actions-20261026-183143, NO-GO on `completed` alone, 0 of 5). One boot of agent-nozombies (fixture `agent0`, admin
-debug, PZTestKit + PZAgent, zombies none); a fixed goal sequence, no policy.

WHY A PASS 2 (pass 1's readings.reps, the scan squares of its scanId 1 and testing/artifacts/<PASS1_RUN>/GUIDE.md):
  - the fixture and the pick (`loot ... no match`, reps 1-4): the agent0 house's containers within r = 15 hold one
    edible food item (Base.Oatmeal in the microwave at 10998,9698, looted in rep 1) and their fluid containers are a
    Base.DrinkingGlass (counter 10999,9696) and two Base.Bleach (counter 11000,9701), none of which world.WATER_RX
    matches; no square holds both a food item and a fluid container, so a repetition whose food and water loots land
    on ONE pick can never complete there, and pass 1's pick, ranking by name regexes that matched nothing, went
    nearest-first;
  - the neighbour rule (`goto ... stuck` and both `loot ... not adjacent`, rep 5): beside() skipped only `solid`
    squares and chose the stove square 10998,9697 (`solid false, solidTrans true`, a `stove` container entry); the
    Lua's adjacentTo had the same rule and is fixed in its own commit (approach skips solidTrans squares).

THE CHANGES (everything else is b_actions.py's, imported and subclassed, never changed):
  1. beside_free(): the pick's 8-neighbour nearest the player among those whose `solid` is not true, whose `solidTrans`
     is not true and which carry no container entry (a square with a container is furniture); None when none is free.
  2. two picks per repetition, each over the scan's container squares not picked for that kind in an earlier
     repetition: the food pick (a square holding an edible food id of data/food-items.json, b_actions.food_ids, the eat
     pick's set) and the water pick (a square holding a water-like item: world.WATER_RX or DRINKWARE_RX, never
     NEVER_WATER_RX's Bleach, which the drink goal refuses as poison). Each ranks 2 when its square also holds the other
     kind (the two picks can share one walk), 1 otherwise; nearest the player within the rank. The row records
     pick_food and pick_water (each {x, y, z, dist, tier, items, food, water}: food and water the matched fullTypes in
     container order, repeats kept; None when missing) and door_food / door_water in place of pass 1's pick and door.
  3. the wide scan (b_actions.SCAN_R_WIDE, 25) runs when either pick is missing from the near scan (note
     `no_stocked_container_in_scan`); a missing pick is then taken over the wide scan, and one still missing is noted
     `no_food_pick` / `no_water_pick` with its goto and loot steps recorded `skipped` (the row then cannot
     complete). Pass 1's path stays: no container square at all -> `no_container_in_scan`, the wide scan, and
     `no_container_in_wide_scan` stops the row. A wide scan that returns nothing is noted `wide_scan_failed`.
THE SEQUENCE: scan [-> scan 25] -> (open on the line) -> goto beside the food pick -> loot food -> (open on the line
from where the character stands) -> goto beside the water pick (one goto when both picks are the same square, and no
second open) -> loot water -> eat -> drink -> goto spawn. The eat reset and watch and the gate (grades.gate_b, through
b_grade.py as is) are pass 1's. On agent0 the house holds one edible food item, so `completed` may stay under
grades.COMPLETE_MIN unless the wide scan finds stocked neighbours; the run is the reading either way.

READ AGAIN: pass 1's reps 2-4 looted from about two tiles (the goto counts done within 1.0 tile and the Lua's approach
accepted it); no change here, the run reads it again.

Clocks: as pass 1 (a line's wallMs is the client's PZA.now(); a key ending in PyMs and server_eat's wallMs are this
process's time.time() in ms). The grade never subtracts one from the other.

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. b_actions.py is frozen and imported, never changed; the
phases inherited from it read its own constants, named in CONSTANTS here for the artifact.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.drivers import b_actions as BA             # noqa: E402  (the frozen pass-1 file: Actions and the helpers)
from agent.world import WATER_RX                      # noqa: E402

KEY = "b_actions_2"
DRIVER = "b_actions_2.py"
PROFILE = BA.PROFILE
ARTIFACT = "b_actions_2.json"
PASS1_RUN = "b_actions-20261026-183143"
USER = BA.USER
MIN_FREE_GB = BA.MIN_FREE_GB
BUDGET_S = BA.BUDGET_S
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

# drinkware the loot's water filter takes (a FluidContainer component): Base.DrinkingGlass and the Mug<Name> ids
# (Base.Mugl, Base.MugWhite, Base.MugSpiffo ...); an id with an underscore after Mug is not matched
DRINKWARE_RX = re.compile(r"\.(DrinkingGlass|Mug[A-Za-z]*)\b")
NEVER_WATER_RX = re.compile(r"\.Bleach\b")            # a fluid container the drink goal refuses as poison
AGENT_LUA = BA.AGENT_LUA
PASS1_DRIVER = "testing/agent/drivers/b_actions.py"
CLIENT_ERR_RX = BA.CLIENT_ERR_RX
STEP_ORDER = BA.STEP_ORDER            # the order when both picks are one square (one open, one goto)

CONSTANTS = {"PASS1_RUN": PASS1_RUN, "DRINKWARE_RX": DRINKWARE_RX.pattern, "NEVER_WATER_RX": NEVER_WATER_RX.pattern,
             "WATER_RX": WATER_RX.pattern}
CONSTANTS["inherited_from_b_actions"] = dict(BA.CONSTANTS)

parse_argv = BA.parse_argv
_seq = BA._seq


def new_out():
    out = BA.new_out()
    out["pass1_run"] = PASS1_RUN
    return out


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua, b_actions.py and this driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["pass1_driver_dirty"] = git_dirty(PASS1_DRIVER)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["pass1_driver_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


# ================================================================ pure helpers (the picks and the beside-square)
def water_like(ft):
    """A fullType the water pick takes: world.WATER_RX or DRINKWARE_RX, never NEVER_WATER_RX."""
    ft = str(ft)
    return bool((WATER_RX.search(ft) or DRINKWARE_RX.search(ft)) and not NEVER_WATER_RX.search(ft))


def matched(sq, ids=None):
    """The square's container items split into (food, water): edible food ids of the food dataset, and water_like
    fullTypes; each a list in container order, repeats kept."""
    ids = BA.food_ids() if ids is None else ids
    items = [str(i) for i in BA._items(sq)]
    return [i for i in items if i in ids], [i for i in items if water_like(i)]


def has_container(scan):
    return any(_seq(s.get("containers")) for s in _seq((scan or {}).get("squares")))


def pick_kind(scan, px, py, kind, exclude=(), ids=None):
    """The `kind` ("food" or "water") pick: among the scan's container squares not in `exclude` holding a matched item
    of that kind, rank 2 when the square also holds the other kind, 1 otherwise; nearest (px, py) within the rank.
    None when no square holds one."""
    best = None
    for s in _seq((scan or {}).get("squares")):
        if not _seq(s.get("containers")) or (s.get("x"), s.get("y"), s.get("z")) in exclude:
            continue
        food, water = matched(s, ids)
        mine, other = (food, water) if kind == "food" else (water, food)
        if not mine:
            continue
        d = math.hypot(s["x"] + 0.5 - px, s["y"] + 0.5 - py)
        key = (-(2 if other else 1), d)
        if best is None or key < best[0]:
            best = (key, s, food, water)
    if best is None:
        return None
    key, s, food, water = best
    return {"x": s["x"], "y": s["y"], "z": s.get("z"), "dist": key[1], "tier": -key[0],
            "items": len(BA._items(s)), "food": food, "water": water}


def free_square(s):
    """A square the walk can stand on: not solid, not solidTrans, no container entry."""
    return (s is not None and s.get("solid") is not True and s.get("solidTrans") is not True
            and not _seq(s.get("containers")))


def beside_free(scan, px, py, pick):
    """The pick's free 8-neighbour in the scan (free_square) nearest (px, py); None when none is free."""
    sq = BA.by_xy(scan, pick.get("z"))
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            s = sq.get((pick["x"] + dx, pick["y"] + dy))
            if not free_square(s):
                continue
            d = math.hypot(s["x"] + 0.5 - px, s["y"] + 0.5 - py)
            if best is None or d < best[0]:
                best = (d, s["x"], s["y"])
    return None if best is None else (best[1], best[2])


def same_square(a, b):
    return a is not None and b is not None and (a["x"], a["y"], a.get("z")) == (b["x"], b["y"], b.get("z"))


# ================================================================ the sequence
class Actions2(BA.Actions):
    """Pass 1's Actions with two picks (food, water), the wide scan when either is missing and the free
    beside-square; the hello, spawn, scan, goal, eat-reset and eat-watch steps are pass 1's."""

    def __init__(self, xs, link, **kw):
        super().__init__(xs, link, **kw)
        self.picked_kind = {"food": set(), "water": set()}

    def choose(self, row):
        """(scan, pick_food, pick_water, px, py) for this repetition, the notes on the row; None stops the repetition
        (pass 1's path: no container square in either scan). The player's x, y are read after the near scan, as pass
        1 read them; `scan` is the one the doors and beside-squares are planned over (the wide one when it ran)."""
        near = self.scan(row, BA.SCAN_R)
        me = self.world.me
        px, py = me.get("x"), me.get("y")

        def picks(scan, have=(None, None)):
            return tuple(have[i] or pick_kind(scan, px, py, k, self.picked_kind[k])
                         for i, k in enumerate(("food", "water")))
        if not has_container(near):
            row["notes"].append("no_container_in_scan")
            wide = self.scan(row, BA.SCAN_R_WIDE)
            if not has_container(wide):
                row["notes"].append("no_container_in_wide_scan")
                return None
            scan, (pf, pw) = wide, picks(wide)
        else:
            scan, (pf, pw) = near, picks(near)
            if pf is None or pw is None:
                row["notes"].append("no_stocked_container_in_scan")
                wide = self.scan(row, BA.SCAN_R_WIDE)
                if wide is None:
                    row["notes"].append("wide_scan_failed")
                else:
                    scan, (pf, pw) = wide, picks(wide, (pf, pw))
        if pf is None:
            row["notes"].append("no_food_pick")
        if pw is None:
            row["notes"].append("no_water_pick")
        return scan, pf, pw, px, py

    def here(self, px, py):
        """The character's x, y off the latest frame; (px, py) when it carries none."""
        me = self.world.me
        x, y = me.get("x"), me.get("y")
        return (x, y) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else (px, py)

    def leg(self, row, scan, px, py, pick, kind, walk=True):
        """One pick's steps: the open on the line from (px, py), the goto beside it (unless walk is False: the
        character already stands beside it) and `loot x y <kind>`; a missing pick's goto and loot recorded skipped."""
        row["door_" + kind] = None
        if pick is None:
            self.skip(row, "goto", "", "no %s pick" % kind)
            self.skip(row, "loot", kind, "no %s pick" % kind)
            return
        self.picked_kind[kind].add((pick["x"], pick["y"], pick["z"]))
        if walk:
            door = BA.door_between(scan, px, py, pick)
            row["door_" + kind] = door
            if door is not None:
                if door["open"]:
                    row["notes"].append("door_already_open_" + kind)
                else:
                    self.goal(row, "open", "%d %d" % (door["x"], door["y"]))
            nb = beside_free(scan, px, py, pick)
            if nb is None:
                self.skip(row, "goto", "", "no free neighbour")
            else:
                self.goal(row, "goto", "%s %s" % (str(nb[0] + 0.5), str(nb[1] + 0.5)))
        self.goal(row, "loot", "%d %d %s" % (pick["x"], pick["y"], kind))

    def _rep(self, row, spawn, a0):
        for k in ("pick", "door"):
            row.pop(k, None)
        row["pick_food"] = row["pick_water"] = None
        got = self.choose(row)
        if got is None:
            return
        scan, pf, pw, px, py = got
        row["pick_food"], row["pick_water"] = pf, pw
        self.leg(row, scan, px, py, pf, "food")
        one = same_square(pf, pw)
        if one:
            row["notes"].append("one_square_for_both_picks")
        wx, wy = (px, py) if pf is None else self.here(px, py)
        self.leg(row, scan, wx, wy, pw, "water", walk=not one)
        ft, src = BA.eat_choice(self.added[a0:])
        row["eat_pick"] = {"fullType": ft, "from": src, "added": list(self.added[a0:])}
        self.eat_reset(row)
        se = row["server_eat"]
        se["before"] = self.body_row()
        se["client_before"] = self.frame_hunger()
        step = self.goal(row, "eat", ft)
        self.eat_watch(row, step)
        self.goal(row, "drink")
        self.goal(row, "goto", "%s %s" % (str(spawn["x"]), str(spawn["y"])))
        row["completed"] = all(s.get("state") == "done" for s in row["steps"])


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    BA.memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    act = None
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=BA.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            act = Actions2(xs, DL.link_for(clients, USER))
            act.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = BA.client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if act is not None:
            act.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
