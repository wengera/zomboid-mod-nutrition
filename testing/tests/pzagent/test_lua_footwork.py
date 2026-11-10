"""PZAgent_StanceWork.lua (PZA/1.13, Plan 35 Task 1; the spec `2026-11-10-plan-35-the-footwork-design.md` section 3.1):
the footwork reflex the melee skill runs between presses behind its optional `work` arguments (workR, crawlerR, bandLo,
withdrawX, withdrawY, floorHealth, pile): the gap read against the reach less bandLo, the heading (the repulsion sum
turned to the first clear square at 0.6 and 1.0 tiles: not solid, not blocked from the player's square, no hoppable
edge, no crawler within crawlerR of the point, no fallen zombie within K.WORK_FALLEN_R), the stance walk along it, the
crawler as a target, the pile met in the reflex (the shove, the step, the next press; no crowd hand-back), the floor and
clear hand-backs, the contact count and the work leaf; with `work` absent the melee runs as before, byte for byte. Run on
the lupa host over conftest.make_mover's kinematic fake (test_lua_melee.py's world), the cell's squares an open grid
the tests block square by square. Each behaviour has a positive case and a falsifier."""
import json
import math
import os

import pytest

from agent.base import pza1
from .conftest import ROOT, TICK_MS, J, lua_file, make_cell, make_mover, make_zombie, step_world
from .test_lua_melee import (ARGS, frame_last, go, last, leaves, progress, run, step_seq, three_world,
                             world as melee_world)
from .test_lua_skills import acts, load, sense, start, states, tick
from .test_lua_stance import Rec

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
WORK = {"workR": 3.5, "crawlerR": 1.2, "bandLo": 0.4, "floorHealth": 0.0}
WORK_LEAF = {"heading", "turn", "clear", "gap", "n", "crawler"}
LOOK_OFF = {"look": math.pi, "turn": 0.0, "snap": False}   # the look held away: the meet never presses


def load_work(lua):
    lua.execute(open(lua_file("client/PZAgent_StanceWork.lua"), encoding="utf-8").read())


def make_square(x, y, solid=False, trans=False, blocked=(), hops=()):
    """A square of the open grid: isSolid, isSolidTrans, isBlockedTo(other) true for an other whose (x, y) is in
    blocked, has(flag) true for a flag named in hops."""
    sq = J(x=x, y=y)
    sq.isSolid = lambda s: solid
    sq.isSolidTrans = lambda s: trans
    sq.isBlockedTo = lambda s, o: (o.x, o.y) in blocked
    sq.has = lambda s, f: f in hops
    return sq


def grid(lua, solid=(), blocked=(), hops=None, missing=()):
    """The cell's squares x 0..20, y 10..30 at z 0, open but those named: solid squares, the player's square (10, 20)
    blocked to the squares in blocked, hops {(x, y): (flag, ...)}, and the squares in missing absent."""
    hops = hops or {}
    sq = {}
    for x in range(0, 21):
        for y in range(10, 31):
            if (x, y) in missing:
                continue
            sq[(x, y, 0)] = make_square(x, y, solid=(x, y) in solid, blocked=blocked if (x, y) == (10, 20) else (),
                                        hops=hops.get((x, y), ()))
    cell = make_cell(squares=sq)
    lua.globals()._cell = cell
    return cell


def world(lua, squares=True, **kw):
    """test_lua_melee.py's world (the runner, the skills, a mover and Sense stubbed), the footwork loaded, the open
    grid, and the frame's records holding the target."""
    p, z, w = melee_world(lua, **kw)
    load_work(lua)
    if squares:
        grid(lua)
    p.getZ = lambda s: 0
    return p, z, w


def records(lua, recs, objs):
    """PZA.sense.last's zombie records ({id, dist[, crawler][, onFloor][, x, y]} each) and PZA.sense.zobj."""
    g = lua.globals()
    g._objs = lua.table_from(objs)
    lua.execute("PZA.sense.zobj = _objs")
    parts = []
    for r in recs:
        fields = ["id = %d" % r["id"], "dist = %r" % r["dist"]]
        for k in ("crawler", "onFloor"):
            if r.get(k):
                fields.append("%s = true" % k)
        for k in ("x", "y"):
            if k in r:
                fields.append("%s = %r" % (k, r[k]))
        parts.append("{ " + ", ".join(fields) + " }")
    lua.execute("PZA.sense.last = { zombies = { %s }, body = {} }" % ", ".join(parts))


def target_rec(w, zid=7):
    return {"id": zid, "dist": math.hypot(w["zx"] - w["px"], w["zy"] - w["py"]), "x": w["zx"], "y": w["zy"]}


def gow(lua, p, aid="m1", work=None, **over):
    a = dict(WORK)
    a.update(work or {})
    a.update(over)
    go(lua, p, aid=aid, **a)


def work_of(lua, key):
    return lua.eval("PZA.skills.cur and PZA.skills.cur.st.work and PZA.skills.cur.st.work.%s" % key)


def crawler(zid, x, y):
    o = make_zombie(zid, x, y)
    o.isCrawling = lambda s: True
    o.isOnFloor = lambda s: True
    return o


def walk_world(w):
    """The fake's world walk direction (setAutoWalkDirection's input vector mapped back, normalised)."""
    return w["walk"]


def bearing(vx, vy):
    return math.degrees(math.atan2(vy, vx))


# ---- the arguments ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("over", [{"workR": -1}, {"workR": "x"}, {"crawlerR": None}, {"bandLo": -0.1},
                                  {"floorHealth": "low"}, {"withdrawX": 1.0}, {"withdrawY": 0.0},
                                  {"withdrawX": "a", "withdrawY": 0.0}, {"pile": "yes"}, {"workR": None}])
def test_bad_work_args_are_rejected(lua, fs, over):
    """The work table typed: workR, crawlerR, bandLo and floorHealth numbers at or above 0 (each needed once any work
    field is given), withdrawX and withdrawY numbers or absent together, pile a boolean or absent."""
    p, z, w = world(lua, zx=11.0)
    a = dict(ARGS)
    a.update(WORK)
    a.update(over)
    a = {k: v for k, v in a.items() if v is not None}
    start(lua, p, "melee", aid="m1", **a)
    assert states(acts(lua, fs)) == [("m1", "rejected", "bad args")]


def test_good_work_args_are_accepted_and_kept_on_the_state(lua, fs):
    p, z, w = world(lua, zx=11.0)
    gow(lua, p, withdrawX=0.0, withdrawY=1.0, pile=True, floorHealth=40.0)
    assert states(acts(lua, fs)) == [("m1", "accepted", "")]
    assert (work_of(lua, "workR"), work_of(lua, "crawlerR"), work_of(lua, "bandLo")) == (3.5, 1.2, 0.4)
    assert (work_of(lua, "withdrawX"), work_of(lua, "withdrawY"), work_of(lua, "pile")) == (0.0, 1.0, True)
    assert work_of(lua, "floorHealth") == 40.0


def test_without_work_args_the_state_has_no_work(lua, fs):
    p, z, w = world(lua, zx=11.0)
    go(lua, p)
    assert lua.eval("PZA.skills.cur.st.work") is None


# ---- the gap: the step inside the band, the stand beyond ---------------------------------------------------------------

def test_the_step_goes_inside_the_band_away_from_the_nearest(lua, fs):
    """The target at 0.7 tiles (inside the reach 1.25 less bandLo 0.4), the look held away so the meet presses
    nothing: the step `work`, the stance held (force-aim) and the auto-walk along the heading away from it (west)."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.step") == "work"
    vx, vy = walk_world(w)
    assert vx == pytest.approx(-1.0, abs=1e-6) and vy == pytest.approx(0.0, abs=1e-6)
    assert p.aim["force"] is True and w["px"] < 10.0
    assert work_of(lua, "turn") == 0 and work_of(lua, "clear") is True


def test_beyond_the_band_no_step_the_face(lua, fs):
    """The falsifier: the target at 1.0 (beyond 0.85): the meet's face, no walk."""
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 5)
    assert step_seq(lua, fs) == ["face"] and w["px"] == 10.0
    assert not [n for n, v in p.sets if n == "setAutoWalkDirection"]


def test_without_work_the_same_gap_faces(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    go(lua, p)
    run(lua, p, w, 5)
    assert step_seq(lua, fs) == ["face"] and w["px"] == 10.0


def test_the_press_goes_before_the_step(lua, fs):
    """The look on: the meet presses (the swing or the protective shove) where the footwork would step."""
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert w["presses"] and step_seq(lua, fs)[0] in ("swing", "shove")


def test_the_withdraw_bias_turns_the_heading(lua, fs):
    """A withdraw vector north (0, 1) at weight 1.0 beside the target's repulsion 1/0.7^2 west: the heading between
    them, north of west."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, withdrawX=0.0, withdrawY=1.0)
    run(lua, p, w, 2)
    want = bearing(-1 / 0.49, 1.0)
    assert work_of(lua, "heading") == pytest.approx(want, abs=1e-6)
    vx, vy = walk_world(w)
    assert bearing(vx, vy) == pytest.approx(want, abs=0.01)


# ---- the heading: off a blocked square, a hop, a crawler -----------------------------------------------------------------

@pytest.mark.parametrize("how", ["solid", "blocked", "hop", "missing"])
def test_the_heading_turns_off_a_square_that_is_not_clear(lua, fs, how):
    """West of the player (the square (9, 20)) solid, blocked from the player's square, behind a hoppable west edge
    of the player's square, or unreadable: the first clear candidate is 30 degrees off."""
    p, z, w = world(lua, zx=10.7, squares=False, **LOOK_OFF)
    kw = {"solid": {"solid": {(9, 20)}}, "blocked": {"blocked": {(9, 20)}},
          "hop": {"hops": {(10, 20): ("HoppableW",)}}, "missing": {"missing": {(9, 20)}}}[how]
    grid(lua, **kw)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    turn = 90 if how == "hop" else 30   # the hoppable west edge of the player's own square bars every westward crossing
    assert abs(work_of(lua, "turn")) == turn and work_of(lua, "clear") is True
    vx, vy = walk_world(w)
    assert abs(bearing(vx, vy)) == pytest.approx(180.0 - turn, abs=0.01)


def test_a_hop_on_another_edge_does_not_turn_the_heading(lua, fs):
    """The falsifier: a hoppable north edge on the player's square is never crossed going west."""
    p, z, w = world(lua, zx=10.7, squares=False, **LOOK_OFF)
    grid(lua, hops={(10, 20): ("HoppableN",)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") == 0


def test_the_heading_turns_off_a_crawler(lua, fs):
    """A crawler at (8.6, 20), 1.4 tiles west (beyond crawlerR, inside its term's 2.4): the sum still points west,
    but the probe points west lie within crawlerR of it; the first clear candidate is 60 degrees off."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    c = crawler(8, 8.6, 20.0)
    records(lua, [target_rec(w), {"id": 8, "dist": 1.4, "crawler": True, "onFloor": True, "x": 8.6, "y": 20.0}],
            {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 2)
    assert abs(work_of(lua, "turn")) == 60 and work_of(lua, "crawlerD") == pytest.approx(1.4)


def test_without_the_crawler_the_heading_holds(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") == 0 and work_of(lua, "crawlerD") is None


def test_the_heading_turns_off_a_fallen_zombie(lua, fs):
    """A fallen zombie's record at (9.2, 20.0): within K.WORK_FALLEN_R of both probe points west."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    f = make_zombie(9, 9.2, 20.0)
    f.isOnFloor = lambda s: True
    records(lua, [target_rec(w), {"id": 9, "dist": 0.8, "onFloor": True, "x": 9.2, "y": 20.0}], {7: z, 9: f})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") != 0 and work_of(lua, "clear") is True


def test_no_clear_heading_is_cornered_and_no_walk(lua, fs):
    """Every square around the player solid (the player at its square's centre, so every probe at 1.0 leaves it): the
    step cornered, no auto-walk."""
    p, z, w = world(lua, px=10.5, py=20.5, zx=11.2, zy=20.5, squares=False, **LOOK_OFF)
    grid(lua, solid={(x, y) for x in range(8, 13) for y in range(18, 23) if (x, y) != (10, 20)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.step") == "cornered" and work_of(lua, "clear") is False
    assert not [n for n, v in p.sets if n == "setAutoWalkDirection"]


def test_the_heading_is_re_chosen_every_work_ticks(lua, fs):
    """The heading read once, then again K.WORK_TICKS ticks on: the player's square read once a choose."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    reads = []
    cell = lua.globals()._cell
    inner = cell.getGridSquare
    cell.getGridSquare = lambda s, x, y, zz: reads.append((x, y)) or inner(s, x, y, zz)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, reach=2.0)                                             # the band 1.6: the step holds 7 ticks
    run(lua, p, w, 1)
    first = len(reads)
    run(lua, p, w, 4)
    assert len(reads) == first and first > 0
    run(lua, p, w, 2)
    assert len(reads) > first
    assert lua.eval("PZA.skills.WORK_TICKS") == 6


# ---- the crawler as a target ---------------------------------------------------------------------------------------------

def test_a_crawler_within_crawler_r_with_no_standing_in_reach_is_the_target(lua, fs):
    """The target 7 at 2.0 (beyond the reach), a crawler 8 at 0.8: re-pinned to the crawler (step repin, target 8),
    then the finish's stomp at it."""
    p, z, w = world(lua, zx=12.0, zspeed=0.3, attack_ticks=6)
    c = crawler(8, 9.2, 20.0)
    records(lua, [target_rec(w), {"id": 8, "dist": 0.8, "crawler": True, "onFloor": True, "x": 9.2, "y": 20.0}],
            {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 80, stop=lambda: w["presses"])
    seq = step_seq(lua, fs)
    assert "repin" in seq and lua.eval("PZA.skills.cur.st.id") == 8
    assert w["presses"] and w["presses"][0]["shove"] is True   # the stomp: the shove pair at the floor


def test_a_crawler_with_a_standing_zombie_in_reach_is_not_the_target(lua, fs):
    """The falsifier: the target standing at 1.0 (within the reach): the crawler is left."""
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    c = crawler(8, 9.2, 20.0)
    records(lua, [target_rec(w), {"id": 8, "dist": 0.8, "crawler": True, "onFloor": True, "x": 9.2, "y": 20.0}],
            {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 5)
    assert "repin" not in step_seq(lua, fs) and lua.eval("PZA.skills.cur.st.id") == 7


def test_after_a_crawler_pin_a_standing_zombie_beyond_the_reach_does_not_break_the_stomp(lua, fs):
    """The crawler pinned; the standing 7 at 2.0 within handbackR 2.0 + but beyond the reach: no re-pin back."""
    p, z, w = world(lua, zx=11.9, zspeed=0.3, attack_ticks=6)
    c = crawler(8, 9.2, 20.0)
    records(lua, [target_rec(w), {"id": 8, "dist": 0.8, "crawler": True, "onFloor": True, "x": 9.2, "y": 20.0}],
            {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 40, stop=lambda: lua.eval("PZA.skills.cur") is None)
    assert step_seq(lua, fs).count("repin") == 1
    assert all(a["result"].get("target") == 8 for a in progress(lua, fs)) and len(w["presses"]) >= 2


# ---- the finish with work: the re-pin instead of the standing hand-back ---------------------------------------------------

def test_a_standing_zombie_at_a_finish_is_re_pinned_with_work(lua, fs):
    """The target fallen at 1.0, a standing zombie 8 at 1.5 (inside handbackR): with work no hand-back, the re-pin."""
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    w["floor"] = True
    o8 = make_zombie(8, 10.0, 21.5)
    records(lua, [{"id": 8, "dist": 1.5, "x": 10.0, "y": 21.5}, dict(target_rec(w), onFloor=True)], {7: z, 8: o8})
    gow(lua, p)
    run(lua, p, w, 2)
    assert step_seq(lua, fs)[0] == "repin" and lua.eval("PZA.skills.cur.st.id") == 8


def test_without_work_the_standing_zombie_at_a_finish_hands_back(lua, fs):
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    w["floor"] = True
    o8 = make_zombie(8, 10.0, 21.5)
    records(lua, [{"id": 8, "dist": 1.5, "x": 10.0, "y": 21.5}, dict(target_rec(w), onFloor=True)], {7: z, 8: o8})
    go(lua, p)
    run(lua, p, w)
    r = last(lua, fs)["result"]
    assert (r["end"], r["why"], r["id"]) == ("handback", "standing", 8)


# ---- the pile -----------------------------------------------------------------------------------------------------------

def test_the_pile_is_met_in_the_reflex_the_shove_then_the_step_no_hand_back(lua, fs):
    """Three standing within K.MELEE_CROWD_R with pile: no crowd hand-back; the shove at the nearest (knock_p on its
    leaf), at its result the step `pile` along the heading, then the meet's next press."""
    p, z, w = three_world(lua, attack_ticks=6, **LOOK_OFF)
    load_work(lua)
    grid(lua)
    p.getZ = lambda s: 0
    gow(lua, p, pile=True)
    run(lua, p, w, 30)
    seq = step_seq(lua, fs)
    assert lua.eval("PZA.skills.cur") is not None                     # no hand-back
    assert seq[0] == "shove" and w["presses"][0]["shove"] is True
    assert seq.index("pile") > 0 and "knock_p" in leaves(lua, fs)[0]
    assert all(a["state"] != "done" for a in acts(lua, fs) if a["aid"] == "m1")
    assert lua.eval("PZA.skills.cur.st.steps.pile") == 6


def test_without_pile_the_crowd_hands_back(lua, fs):
    p, z, w = three_world(lua, **LOOK_OFF)
    load_work(lua)
    grid(lua)
    p.getZ = lambda s: 0
    gow(lua, p)
    run(lua, p, w)
    r = last(lua, fs)["result"]
    assert (last(lua, fs)["state"], r["end"], r["why"]) == ("done", "handback", "crowd") and w["presses"] == []


def test_a_hit_reaction_in_the_pile_hands_nothing_back(lua, fs):
    p, z, w = three_world(lua, **LOOK_OFF)
    load_work(lua)
    grid(lua)
    p.getZ = lambda s: 0
    gow(lua, p, pile=True)
    p.combat["hitReaction"] = "Bite"
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.step") == "hit" and lua.eval("PZA.skills.cur") is not None


# ---- the hand-backs: floor and clear ------------------------------------------------------------------------------------

@pytest.mark.parametrize("health, ends", [(30.0, True), (40.0, True), (50.0, False)])
def test_the_floor_hands_back_at_or_under_floor_health(lua, fs, health, ends):
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: health)
    gow(lua, p, floorHealth=40.0)
    run(lua, p, w, 3)
    if ends:
        r = last(lua, fs)["result"]
        assert (last(lua, fs)["state"], r["end"], r["why"]) == ("done", "handback", "floor")
    else:
        assert lua.eval("PZA.skills.cur") is not None


def test_the_floor_reads_the_frame_s_health_first(lua, fs):
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    lua.execute("PZA.sense.last.body.health = 35")
    gow(lua, p, floorHealth=40.0)
    run(lua, p, w)
    assert last(lua, fs)["result"]["why"] == "floor"


def test_a_floor_of_0_never_hands_back(lua, fs):
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 1.0)
    gow(lua, p, floorHealth=0.0)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur") is not None


def test_the_floor_hands_back_under_a_hit_reaction(lua, fs):
    p, z, w = world(lua, zx=11.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 30.0)
    p.combat["hitReaction"] = "Bite"
    gow(lua, p, floorHealth=40.0)
    run(lua, p, w)
    assert last(lua, fs)["result"]["why"] == "floor"


def clear_world(lua, other=None):
    """The target a crawler lying 2.0 tiles east (beyond crawlerR 0.5 here), no standing zombie within releaseR
    (or `other`, a standing one at that distance north, beyond handbackR)."""
    p, z, w = world(lua, zx=12.0, chasing=False)
    w["floor"] = True
    z.isCrawling = lambda s: True
    recs = [dict(target_rec(w), crawler=True, onFloor=True)]
    objs = {7: z}
    if other is not None:
        o = make_zombie(8, 10.0, 20.0 + other)
        recs.append({"id": 8, "dist": other, "x": 10.0, "y": 20.0 + other})
        objs[8] = o
    records(lua, recs, objs)
    return p, z, w


def test_clear_hands_back_after_work_clear_ticks_with_nothing_standing(lua, fs):
    p, z, w = clear_world(lua)
    gow(lua, p, crawlerR=0.5, releaseR=2.75)
    run(lua, p, w, 29)
    assert lua.eval("PZA.skills.cur") is not None
    run(lua, p, w, 1)
    r = last(lua, fs)["result"]
    assert (last(lua, fs)["state"], r["end"], r["why"]) == ("done", "handback", "clear")


def test_a_standing_zombie_within_release_r_is_no_clear(lua, fs):
    p, z, w = clear_world(lua, other=2.5)
    gow(lua, p, crawlerR=0.5, releaseR=2.75)
    run(lua, p, w, 40)
    assert lua.eval("PZA.skills.cur") is not None


def test_a_fallen_target_that_is_no_crawler_is_never_clear(lua, fs):
    """A knocked-down zombie is the finish's kill: no clear however long the walk to it."""
    p, z, w = clear_world(lua)
    z.isCrawling = lambda s: False
    records(lua, [dict(target_rec(w), onFloor=True)], {7: z})
    gow(lua, p, crawlerR=0.5, releaseR=2.75)
    run(lua, p, w, 40)
    assert all(a["result"].get("why") != "clear" for a in acts(lua, fs) if a.get("result"))


# ---- the contact count and the work leaf ---------------------------------------------------------------------------------

def test_contact_counts_the_ticks_with_the_nearest_standing_inside_1_0_and_no_press(lua, fs):
    """bandLo the reach (no step), the look away (no press): every tick with the target at 0.7 counts."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, bandLo=1.25)
    run(lua, p, w, 10)
    assert work_of(lua, "contact") == 10


def test_contact_counts_nothing_beyond_1_0(lua, fs):
    p, z, w = world(lua, zx=11.1, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, bandLo=1.25)
    run(lua, p, w, 10)
    assert work_of(lua, "contact") == 0


def test_contact_counts_no_tick_of_a_press_in_flight(lua, fs):
    """The look on, a swing of 20 ticks: those ticks (the press's own included) are not contact."""
    p, z, w = world(lua, zx=10.7, attack_ticks=20)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, bandLo=1.25)
    run(lua, p, w, 10)
    assert w["presses"] and work_of(lua, "contact") == 0


def test_every_progress_line_carries_contact_and_the_work_leaf(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 70)
    pr = progress(lua, fs)
    assert pr and all("contact" in a["result"] and "work" in a["result"] for a in pr)
    assert all(set(a["result"]["work"]) <= WORK_LEAF and {"clear", "n"} <= set(a["result"]["work"]) for a in pr)
    leaf = pr[-1]["result"]["work"]
    assert leaf["n"] == 1 and leaf["gap"] > 0 and set(leaf) == WORK_LEAF - {"crawler"}


def test_the_done_line_carries_contact_the_leaf_and_the_steps(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 5)
    w["zdead"] = True
    run(lua, p, w)
    r = last(lua, fs)["result"]
    assert r["end"] == "kill" and "contact" in r and "work" in r and r["steps"]["work"] >= 1


def test_every_work_key_is_in_the_schema(lua, fs):
    with open(SCHEMA, encoding="utf-8") as fh:
        defs = json.load(fh)["$defs"]
    props, step = defs["result_melee"]["properties"], defs["result_melee_step"]["properties"]
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 5)
    w["zdead"] = True
    run(lua, p, w)
    for a in acts(lua, fs):
        assert set(a["result"]) <= set(props), a
        if a["state"] == "progress":
            assert set(a["result"]) <= set(step), a
        if "work" in a["result"]:
            assert set(a["result"]["work"]) <= set(props["work"]["properties"])
    assert set(props["work"]["properties"]) == WORK_LEAF and set(step["work"]["properties"]) == WORK_LEAF
    assert "contact" in props and "contact" in step
    for s in ("work", "cornered", "pile"):
        assert s in step["step"]["description"]
    for why in ("floor", "clear"):
        assert why in props["why"]["description"]


def test_the_generated_melee_carries_the_work_fields_and_leaves_them_off_the_wire_when_absent():
    m = pza1.Melee(targetId=7, mode="strike", reach=1.25, shoveR=0.9, releaseR=2.75, faceR=3.0, pressAngle=41.0,
                   pressLo=0.0, floorR=1.0, handbackR=2.0, stall=3)
    assert set(m.args()) == {"targetId", "mode", "reach", "shoveR", "releaseR", "faceR", "pressAngle", "pressLo",
                             "floorR", "handbackR", "stall"}
    m2 = pza1.Melee(targetId=7, mode="strike", reach=1.25, shoveR=0.9, releaseR=2.75, faceR=3.0, pressAngle=41.0,
                    pressLo=0.0, floorR=1.0, handbackR=2.0, stall=3, workR=3.5, crawlerR=1.2, bandLo=0.4,
                    withdrawX=0.0, withdrawY=1.0, floorHealth=40.0, pile=True)
    a = m2.args()
    assert (a["workR"], a["crawlerR"], a["bandLo"], a["withdrawX"], a["withdrawY"], a["floorHealth"], a["pile"]) == (
        3.5, 1.2, 0.4, 0.0, 1.0, 40.0, True)


def test_the_core_announces_1_13(lua, fs):
    assert lua.eval("PZA.VERSION") == "1.13"


# ---- the re-send ------------------------------------------------------------------------------------------------------

def test_a_same_target_resend_keeps_the_footwork_state_and_takes_the_new_work_fields(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, aid="m1")
    run(lua, p, w, 3)
    heading = work_of(lua, "heading")
    assert heading is not None
    gow(lua, p, aid="m2", withdrawX=0.0, withdrawY=1.0, floorHealth=20.0)
    assert ("m2", "accepted", "") in states(acts(lua, fs))
    assert work_of(lua, "heading") == heading and work_of(lua, "withdrawY") == 1.0 and work_of(lua, "floorHealth") == 20.0
    assert p.aim["force"] is True


def test_another_target_s_resend_starts_a_fresh_footwork(lua, fs):
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    z8 = make_zombie(8, 10.0, 21.0)
    sense(lua, [z, z8])
    records(lua, [target_rec(w), {"id": 8, "dist": 1.0, "x": 10.0, "y": 21.0}], {7: z, 8: z8})
    gow(lua, p, aid="m1")
    run(lua, p, w, 3)
    gow(lua, p, aid="m2", targetId=8)
    assert work_of(lua, "heading") is None


# ---- work absent: the melee as before, byte for byte -----------------------------------------------------------------

def _scenario(lua, fs, with_work_file, case):
    if case == "chaser":
        p, z, w = melee_world(lua, zx=13.0, zspeed=1.2, attack_ticks=8)
        w["on_attack"] = lambda wd, shove: wd.__setitem__("zhp", wd["zhp"] - 0.4)
        if with_work_file:
            load_work(lua)
        go(lua, p)
        run(lua, p, w, 120)
    elif case == "crowd":
        p, z, w = three_world(lua)
        if with_work_file:
            load_work(lua)
        go(lua, p)
        run(lua, p, w, 3)
    else:   # the finish with a standing zombie inside handbackR
        p, z, w = melee_world(lua, zx=11.0)
        w["floor"] = True
        if with_work_file:
            load_work(lua)
        o8 = make_zombie(8, 10.0, 21.5)
        frame_last(lua, [(8, 1.5), (7, 1.0)], objs={7: z, 8: o8})
        go(lua, p)
        run(lua, p, w, 3)
    lua.execute("PZA.link.flush()")
    return [json.dumps(a, sort_keys=True) for a in acts(lua, fs)], list(w["presses"]), list(p.sets)


@pytest.mark.parametrize("case", ["chaser", "crowd", "finish"])
def test_work_absent_runs_the_melee_as_before_byte_for_byte(fs, case):
    """The same scenario on two hosts, one with PZAgent_StanceWork.lua loaded and one without, the melee sent with no
    work fields: the act lines, the presses and the setters are identical."""
    from .conftest import make_lua, FakeFS
    fs2 = FakeFS()
    a = _scenario(make_lua(fs), fs, False, case)
    b = _scenario(make_lua(fs2), fs2, True, case)
    assert a[0] and a[0] == b[0]
    assert [{k: v for k, v in x.items()} for x in a[1]] == [{k: v for k, v in x.items()} for x in b[1]]
    assert [(n, repr(v) if not hasattr(v, "x") else (v.x, v.y)) for n, v in a[2]] == \
           [(n, repr(v) if not hasattr(v, "x") else (v.x, v.y)) for n, v in b[2]]


# ---- the cost --------------------------------------------------------------------------------------------------------

def test_a_stepping_tick_at_a_re_choose_stays_under_40_java_calls(lua, fs):
    """The footwork's step at its heading's re-choose with the target and five more standing within workR: every Java
    member read on the tick, counted through Rec wrappers, under the spec's 40."""
    p, z, w = world(lua, zx=10.7, zspeed=3.0, **LOOK_OFF)          # a chaser keeping inside the band
    others = {}
    recs = [target_rec(w)]
    for i, (x, y) in enumerate([(12.5, 21.0), (12.5, 19.0), (11.5, 22.5), (11.5, 17.5), (13.0, 20.0)]):
        o = make_zombie(20 + i, x, y)
        others[20 + i] = o
        recs.append({"id": 20 + i, "dist": math.hypot(x - 10.0, y - 20.0), "x": x, "y": y})
    objs = {7: z}
    objs.update(others)
    records(lua, recs, objs)
    gow(lua, p)
    run(lua, p, w, 6)                                                 # the 7th tick re-chooses (the 1st chose)
    log = []
    bd = p.getBodyDamage(p)
    p.getBodyDamage = lambda s: Rec(bd, log, "bd")
    lua.globals()._zr = Rec(z, log, "z")
    lua.execute("PZA.skills.cur.st.z = _zr")
    for zid, o in others.items():
        lua.globals()._o = Rec(o, log, "o%d" % zid)
        lua.execute("PZA.sense.zobj[%d] = _o" % zid)
    cell = lua.globals()._cell
    inner = cell.getGridSquare
    cell.getGridSquare = lambda s, x, y, zz: (lambda sq: None if sq is None else Rec(sq, log, "sq"))(inner(s, x, y, zz))
    lua.globals()._cell = Rec(cell, log, "cell")
    step_world(w, p)
    lua.globals()._clock["ms"] += TICK_MS
    tick(lua, Rec(p, log, "p"))
    assert lua.eval("PZA.skills.cur.st.step") == "work" and lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0
    # 31: the melee's face tick (the dead check 2, isDead, the two positions 4, the hit read, isOnFloor, isKnockedDown
    # within the reach, the snap, the look: 12), the stance re-held for the step (nullifyAiming at the meet's release,
    # setForceAim at the step: 2), the re-choose (getZ, the player's and one probe square 2, the five others' positions
    # 10, the square's isSolid, isSolidTrans, isBlockedTo and its crossed hop flag 4); none of the five is within the
    # near read's candidates (the reach + K.MELEE_CROWD_SLACK), the floor off (0)
    assert len(log) == 31 and len(log) < 40, sorted(log)


# ---- fix 1: the live shape (x_trial-ladder-20261110-081250 and -081935: the step never went) -------------------------

def test_inside_the_band_the_step_goes_between_presses_with_the_look_on(lua, fs):
    """The smokes' shape: a chaser inside the reach less bandLo with the look on. The meet pressed swing after swing
    (a7: 193 swing ticks, the gap 0.73, no idle tick) and the footwork, reached only at the meet's stand and face,
    never ran. Fix 1: at a press's result with the nearest standing inside the band, the step `work` goes before the
    next press (the spec's item 1: the step and the press alternate as the swing clip and the gap allow)."""
    p, z, w = world(lua, zx=10.75, zspeed=1.0, attack_ticks=20)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 60)
    seq = step_seq(lua, fs)
    assert seq[:3] == ["swing", "work", "swing"] and len(w["presses"]) == 2   # the press, the step, the press
    assert work_of(lua, "clear") is True and work_of(lua, "n") == 1


def test_without_work_the_same_chaser_is_pressed_with_no_step(lua, fs):
    p, z, w = world(lua, zx=10.75, zspeed=1.0, attack_ticks=20)
    records(lua, [target_rec(w)], {7: z})
    go(lua, p)
    run(lua, p, w, 60)
    assert "work" not in step_seq(lua, fs) and w["presses"]


def test_a_knocked_down_target_is_no_contact_and_takes_no_step(lua, fs):
    """The smokes' contact 9 and 18 were a7's and a14's knock_wait ticks (9 and 18): a target the press knocked down
    is no standing zombie for the gap, the contact or the step."""
    p, z, w = world(lua, zx=10.8, attack_ticks=6)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 30)
    assert "knock_wait" in step_seq(lua, fs) and "work" not in step_seq(lua, fs)
    assert work_of(lua, "contact") == 0


def test_the_leaf_carries_no_clear_until_a_heading_was_chosen(lua, fs):
    """The smokes' leaves read clear false, n 0 on every line though no heading was ever chosen: the leaf now says
    nothing of clear and n until a choose has run."""
    p, z, w = world(lua, zx=11.5, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 3)
    leaf = progress(lua, fs)[-1]["result"]["work"]
    assert "clear" not in leaf and "n" not in leaf and leaf["gap"] == pytest.approx(1.5)
