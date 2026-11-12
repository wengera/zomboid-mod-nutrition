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
WORK = {"workR": 3.5, "crawlerR": 1.2, "bandLo": 0.4, "floorHealth": 0.0, "reach": 1.475}   # fix 2: the live reach
# (the smoke x_trial-ladder-20261110-084643 sent 1.475): the band, reach - bandLo, 1.075; the step goes in [0.9, 1.075)
BAND_X = 10.95   # the target 0.95 tiles east: inside the band, beyond K.WORK_POINT_BLANK_R
WORK_LEAF = {"heading", "turn", "clear", "gap", "n", "crawler", "held", "pile", "step_for", "retreat", "stall_held", "repin_for",
             "nan_heading", "shove_for"}   # Plan 36 Task 1 fix 1: nan_heading; Task 2b: shove_for   # fix 2: held; fix 3: pile; fix 5: step_for
LOOK_OFF = {"look": math.pi, "turn": 0.0, "snap": False}   # the look held away: the meet never presses


def load_work(lua):
    lua.execute(open(lua_file("client/PZAgent_StanceWork.lua"), encoding="utf-8").read())


def make_square(x, y, solid=False, trans=False, blocked=(), hops=(), doors=None, objs=None):
    """A square of the open grid: isSolid, isSolidTrans, isBlockedTo(other) true for an other whose (x, y) is in
    blocked, has(flag) true for a flag named in hops; with doors (a set of (x, y)), getDoorTo(other) a door for an
    other in it and None otherwise (absent without doors, as a build lacking the member); with objs, getObjects the
    list of them (Plan 36 Task 1: the room ring's door reads)."""
    sq = J(x=x, y=y)
    sq.isSolid = lambda s: solid
    sq.isSolidTrans = lambda s: trans
    sq.isBlockedTo = lambda s, o: (o.x, o.y) in blocked
    sq.has = lambda s, f: f in hops
    if doors is not None:
        sq.getDoorTo = lambda s, o: J(_cls="IsoDoor") if (o.x, o.y) in doors else None
    if objs is not None:
        sq.getObjects = lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i])
    return sq


def grid(lua, solid=(), blocked=(), hops=None, missing=(), edges=None, doors=None, objs=None):
    """The cell's squares x 0..20, y 10..30 at z 0, open but those named: solid squares, the player's square (10, 20)
    blocked to the squares in blocked, hops {(x, y): (flag, ...)}, and the squares in missing absent; Plan 36 Task 1:
    edges {(x, y): {(x, y), ...}} more squares' blocked neighbours, doors {(x, y): {(x, y), ...}} each square's
    getDoorTo answers (every square takes the member once doors is given), objs {(x, y): [object, ...]}."""
    hops, edges, objs = hops or {}, edges or {}, objs or {}
    sq = {}
    for x in range(0, 21):
        for y in range(10, 31):
            if (x, y) in missing:
                continue
            blk = set(blocked if (x, y) == (10, 20) else ()) | set(edges.get((x, y), ()))
            sq[(x, y, 0)] = make_square(x, y, solid=(x, y) in solid, blocked=blk, hops=hops.get((x, y), ()),
                                        doors=None if doors is None else set(doors.get((x, y), ())),
                                        objs=objs.get((x, y)))
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


def records(lua, recs, objs, attackers=None):
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
    me = "" if attackers is None else ", me = { attackers = %d }" % attackers   # fix 3: the frame's me.attackers
    lua.execute("PZA.sense.last = { zombies = { %s }, body = {}%s }" % (", ".join(parts), me))


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
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.step") == "work"
    vx, vy = walk_world(w)
    assert vx == pytest.approx(-1.0, abs=1e-6) and vy == pytest.approx(0.0, abs=1e-6)
    assert p.aim["force"] is True and w["px"] < 10.0
    assert work_of(lua, "turn") == 0 and work_of(lua, "clear") is True


def test_beyond_the_band_no_step_the_face(lua, fs):
    """The falsifier: the target at 1.2 (beyond the band's 1.075): the meet's face, no walk."""
    p, z, w = world(lua, zx=11.2, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 5)
    assert step_seq(lua, fs) == ["face"] and w["px"] == 10.0
    assert not [n for n, v in p.sets if n == "setAutoWalkDirection"]


def test_without_work_the_same_gap_faces(lua, fs):
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    go(lua, p)
    run(lua, p, w, 5)
    assert step_seq(lua, fs) == ["face"] and w["px"] == 10.0


def test_the_press_goes_before_the_step(lua, fs):
    """The look on: the meet presses (the swing or the protective shove) where the footwork would step."""
    p, z, w = world(lua, zx=BAND_X, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert w["presses"] and step_seq(lua, fs)[0] in ("swing", "shove")


def test_the_withdraw_bias_turns_the_heading(lua, fs):
    """A withdraw vector north (0, 1) at weight 1.0 beside the target's repulsion 1/0.7^2 west: the heading between
    them, north of west."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, withdrawX=0.0, withdrawY=1.0)
    run(lua, p, w, 2)
    want = bearing(-1 / 0.95 ** 2, 1.0)
    assert work_of(lua, "heading") == pytest.approx(want, abs=1e-6)
    vx, vy = walk_world(w)
    assert bearing(vx, vy) == pytest.approx(want, abs=0.01)


# ---- the heading: off a blocked square, a hop, a crawler -----------------------------------------------------------------

@pytest.mark.parametrize("how", ["solid", "blocked", "hop", "missing"])
def test_the_heading_turns_off_a_square_that_is_not_clear(lua, fs, how):
    """West of the player (the square (9, 20)) solid, blocked from the player's square, behind a hoppable west edge
    of the player's square, or unreadable: the first clear candidate is 30 degrees off."""
    p, z, w = world(lua, zx=BAND_X, squares=False, **LOOK_OFF)
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
    p, z, w = world(lua, zx=BAND_X, squares=False, **LOOK_OFF)
    grid(lua, hops={(10, 20): ("HoppableN",)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") == 0


def test_the_heading_turns_off_a_crawler(lua, fs):
    """A crawler at (7.9, 20), 2.1 tiles west (beyond crawlerR and, Plan 36 Task 2b re-pin, beyond K.CRAWLER_BUFFER_R's
    2.0, whose buffer step would otherwise go; inside its term's 2.4): the sum still points west, but the probe points
    west lie within crawlerR of it; the first clear candidate is 30 degrees off (at 1.4 tiles it read 60)."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    c = crawler(8, 7.9, 20.0)
    records(lua, [target_rec(w), {"id": 8, "dist": 2.1, "crawler": True, "onFloor": True, "x": 7.9, "y": 20.0}],
            {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 2)
    assert abs(work_of(lua, "turn")) == 30 and work_of(lua, "crawlerD") == pytest.approx(2.1, abs=0.05)


def test_without_the_crawler_the_heading_holds(lua, fs):
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") == 0 and work_of(lua, "crawlerD") is None


def test_the_heading_turns_off_a_fallen_zombie(lua, fs):
    """A fallen zombie's record at (9.2, 20.0): within K.WORK_FALLEN_R of both probe points west."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    f = make_zombie(9, 9.2, 20.0)
    f.isOnFloor = lambda s: True
    records(lua, [target_rec(w), {"id": 9, "dist": 0.8, "onFloor": True, "x": 9.2, "y": 20.0}], {7: z, 9: f})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") != 0 and work_of(lua, "clear") is True


def test_no_clear_heading_is_cornered_and_no_walk(lua, fs):
    """Every square around the player solid (the player at its square's centre, so every probe at 1.0 leaves it): the
    step cornered, no auto-walk."""
    p, z, w = world(lua, px=10.5, py=20.5, zx=11.45, zy=20.5, squares=False, **LOOK_OFF)
    grid(lua, solid={(x, y) for x in range(8, 13) for y in range(18, 23) if (x, y) != (10, 20)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.step") == "cornered" and work_of(lua, "clear") is False
    assert not [n for n, v in p.sets if n == "setAutoWalkDirection"]


def test_the_heading_is_re_chosen_every_work_ticks(lua, fs):
    """The heading read once, then again K.WORK_TICKS ticks on: the player's square read once a choose."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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


# ---- Plan 36 Task 1: the room ring (K.workClearAlong, K.workRoom; me.room, PZA/1.14) --------------------------------

def standing(x, y):
    """A player standing at (x, y) on floor 0 (the ring's reads: getX, getY, getZ)."""
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)


def clear_along(lua, p, heading, max_tiles=3.0):
    return tuple(lua.eval("PZA.skills.workClearAlong")(p, heading, max_tiles))


def ring_of(lua, p):
    r = lua.eval("PZA.skills.workRoom")(p)
    return list(r.h.values()), list(r.stop.values()), r


def ring_world(lua, **kw):
    """The footwork loaded (world()), the grid built by the test."""
    return world(lua, squares=False, **kw)


def test_a_wall_whose_square_the_1_5_step_enters_reads_1_0_clear_and_wall(lua, fs):
    """The player at (10.6, 20.5), the square (12, 20) solid: the steps east reach 11.1, 11.6 (square 11) and 12.1
    (square 12) at 1.5: 1.0 clear, wall."""
    ring_world(lua)
    grid(lua, solid={(12, 20)})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (1.0, "wall")


def test_a_wall_on_the_player_s_next_square_reads_0_and_an_unreadable_square_a_wall(lua, fs):
    ring_world(lua)
    grid(lua, solid={(11, 20)}, missing={(10, 22)})
    p = standing(10.6, 20.5)
    assert clear_along(lua, p, 0) == (0.0, "wall")
    assert clear_along(lua, p, 90) == (1.0, "wall")              # 21.0, 21.5 (21), 22.0 (22, absent) at 1.5


def test_open_to_3_0_reads_3_0_and_open(lua, fs):
    ring_world(lua)
    grid(lua)
    p = standing(10.5, 20.5)
    for heading in (0, 45, 90, 135, 180, 225, 270, 315):
        assert clear_along(lua, p, heading) == (3.0, "open")
    assert clear_along(lua, p, 0, 1.0) == (1.0, "open")


@pytest.mark.parametrize("hop, at, heading, want", [
    ({(12, 20): ("HoppableW",)}, (10.6, 20.5), 0, (1.0, "hop")),      # the x edge east: the eastern square's flag
    ({(11, 20): ("HoppableW",)}, (11.4, 20.5), 180, (0.0, "hop")),    # going west: the square left is the eastern one
    ({(10, 22): ("HoppableN",)}, (10.5, 20.6), 90, (1.0, "hop")),     # the y edge south: the southern square's flag
    ({(12, 20): ("HoppableN",)}, (10.6, 20.5), 0, (3.0, "open")),     # the falsifier: a north edge never crossed east
])
def test_a_hoppable_crossed_edge_reads_hop(lua, fs, hop, at, heading, want):
    ring_world(lua)
    grid(lua, hops=hop)
    assert clear_along(lua, standing(*at), heading) == want


def test_a_blocked_edge_with_a_door_reads_door_and_without_one_wall(lua, fs):
    """(11, 20) blocked to (12, 20): getDoorTo answering a door there reads door at 1.0; answering None, wall."""
    ring_world(lua)
    grid(lua, edges={(11, 20): {(12, 20)}}, doors={(11, 20): {(12, 20)}})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (1.0, "door")
    grid(lua, edges={(11, 20): {(12, 20)}}, doors={})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (1.0, "wall")


def test_without_get_door_to_a_door_object_on_either_square_reads_door(lua, fs):
    """A build lacking getDoorTo: an IsoDoor among the entered square's objects reads door; a container, wall."""
    ring_world(lua)
    grid(lua, edges={(11, 20): {(12, 20)}}, objs={(12, 20): [J(_cls="IsoDoor")]})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (1.0, "door")
    grid(lua, edges={(11, 20): {(12, 20)}}, objs={(12, 20): [J(_cls="IsoObject")]})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (1.0, "wall")


def test_an_open_door_is_crossed_clear(lua, fs):
    """A door that does not block (isBlockedTo false, getDoorTo a door): no stop."""
    ring_world(lua)
    grid(lua, doors={(11, 20): {(12, 20)}})
    assert clear_along(lua, standing(10.6, 20.5), 0) == (3.0, "open")


def test_the_ring_reads_the_eight_headings_in_order_from_the_world_s_x(lua, fs):
    """The ring's h[i] and stop[i] are K.workClearAlong's at K.WORK_ROOM_HEADINGS[i], 0, 45, ..., 315 degrees from
    the world's +x (atan2(y, x), me.fwdAngle's convention: 90 is +y): east a wall reading 1.0, south a hop (the step at
    2.5 crossing into (10, 23)) reading 2.0, west a door (the step at 1.0 crossing into (9, 20)) reading 0.5, north
    open."""
    ring_world(lua)
    grid(lua, solid={(12, 20)}, hops={(10, 23): ("HoppableN",)}, edges={(10, 20): {(9, 20)}},
         doors={(10, 20): {(9, 20)}})
    p = standing(10.6, 20.5)
    assert list(lua.eval("PZA.skills.WORK_ROOM_HEADINGS").values()) == [0, 45, 90, 135, 180, 225, 270, 315]
    h, stop, r = ring_of(lua, p)
    assert [(h[i], stop[i]) for i in range(8)] == [clear_along(lua, p, 45 * i) for i in range(8)]
    assert (h[0], stop[0]) == (1.0, "wall") and (h[2], stop[2]) == (2.0, "hop") and (h[4], stop[4]) == (0.5, "door")
    assert (h[6], stop[6]) == (3.0, "open")
    assert (r.sx, r.sy, r.z) == (10, 20, 0) and lua.eval("PZA.skills.room.stop[5]") == "door"


@pytest.mark.parametrize("vec, index", [((1.0, 0.0), 1), ((0.0, 1.0), 3), ((-1.0, 0.0), 5), ((0.0, -1.0), 7),
                                        ((0.92, 0.38), 1), ((0.92, -0.38), 1), ((0.7, 0.72), 2), ((-0.7, -0.72), 6)])
def test_a_heading_maps_to_the_nearest_ring_heading(lua, fs, vec, index):
    ring_world(lua)
    assert lua.eval("PZA.skills.workRoomIndex")(*vec) == index


def test_the_footwork_turns_off_a_heading_the_ring_reads_short(lua, fs):
    """The target east inside the band, the ring west reading 0.0 (a wall on (9, 20), the step at 0.5 from (10.4,
    20.5) entering it): the sum's heading west is not taken (under K.WORK_ROOM_NEED), the step turned; with the wall at
    (8, 20) the ring reads 1.0 and the step goes west (turn 0)."""
    p, z, w = ring_world(lua, px=10.4, py=20.5, zx=11.35, zy=20.5, **LOOK_OFF)
    grid(lua, solid={(9, 20)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") != 0 and work_of(lua, "clear") is True
    p, z, w = ring_world(lua, px=10.4, py=20.5, zx=11.35, zy=20.5, **LOOK_OFF)
    grid(lua, solid={(8, 20)})
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "turn") == 0


def test_the_melee_s_ring_is_read_again_on_a_new_square_or_after_work_room_ticks(lua, fs):
    """The ring read at the first choose (K.roomReads 1); a choose forced on the same square one tick on reuses it; a
    choose on another square reads it again; a choose at K.WORK_TICKS of the melee's ticks since the last read (fix
    1's budget ruling: the re-choose cadence) reads it again, one tick fewer reuses it."""
    p, z, w = ring_world(lua, px=10.5, py=20.5, zx=11.45, zy=20.5, **LOOK_OFF)
    grid(lua)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.roomReads") == 1 and lua.eval("PZA.skills.WORK_ROOM_TICKS") == 3
    force = "PZA.skills.cur.st.work.sinceChoose = PZA.skills.WORK_TICKS"
    lua.execute(force)
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0 and lua.eval("PZA.skills.roomReads") == 1
    w["px"], w["zx"] = 9.6, 10.55                                      # the player on square 9, the gap kept
    records(lua, [target_rec(w)], {7: z})
    lua.execute(force)
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0 and lua.eval("PZA.skills.roomReads") == 2
    assert lua.eval("PZA.skills.cur.st.work.room.sx") == 9
    lua.execute(force + "; PZA.skills.cur.st.work.roomTicks = 4")    # 5 at the choose: reused
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0 and lua.eval("PZA.skills.roomReads") == 2
    lua.execute(force + "; PZA.skills.cur.st.work.roomTicks = 5")    # 6 (K.WORK_TICKS) at the choose: read again
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0 and lua.eval("PZA.skills.roomReads") == 3


def test_the_frame_s_ring_reuses_the_last_within_work_room_ticks_on_its_square(lua, fs):
    """K.workRoomNow: the last ring (K.room) on the same square within K.WORK_ROOM_TICKS client ticks (PZA.tick), else a
    new read stamped with the tick."""
    ring_world(lua)
    grid(lua)
    p = standing(10.5, 20.5)
    lua.execute("PZA.tick = 100")
    now = lua.eval("PZA.skills.workRoomNow")
    r = now(p)
    assert r.tick == 100 and lua.eval("PZA.skills.roomReads") == 1
    lua.execute("PZA.tick = 102")
    assert now(p).tick == 100 and lua.eval("PZA.skills.roomReads") == 1
    lua.execute("PZA.tick = 103")
    assert now(p).tick == 103 and lua.eval("PZA.skills.roomReads") == 2
    assert now(standing(11.5, 20.5)).sx == 11 and lua.eval("PZA.skills.roomReads") == 3


def test_the_ring_on_the_open_grid_costs_its_square_and_edge_reads(lua, fs):
    """The ring's own cost with the position passed (the choose's call), the player at (10.5, 20.5) on the open grid:
    getGridSquare once a square met (the player's own included), isSolid and isSolidTrans once a square entered, one
    has per crossed axis and isBlockedTo per edge crossed; each counted, the total pinned."""
    ring_world(lua)
    grid(lua)
    log = []
    cell = lua.globals()._cell
    inner = cell.getGridSquare
    cell.getGridSquare = lambda s, x, y, zz: (lambda sq: None if sq is None else Rec(sq, log, "sq"))(inner(s, x, y, zz))
    lua.globals()._cell = Rec(cell, log, "cell")
    lua.eval("PZA.skills.workRoom")(Rec(standing(10.5, 20.5), log, "p"), 10.5, 20.5, 0)
    count = {}
    for _, m in log:
        count[m] = count.get(m, 0) + 1
    # each cardinal enters 3 squares across 3 edges, one axis each (12 squares, 12 edges, 12 has); each diagonal's
    # steps (0.3536 a step on each axis from 10.5) cross both axes at once at 1.0 and 2.0, entering 2 squares across 2
    # edges with two has each (8 squares, 8 edges, 16 has); the player's square read once (getGridSquare only): 21
    # squares, 20 entered, 20 edges
    assert count == {"getGridSquare": 21, "isSolid": 20, "isSolidTrans": 20, "has": 28, "isBlockedTo": 20}, count
    assert len(log) == 109


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


def test_a_crawler_with_a_standing_zombie_in_the_shove_range_is_not_the_target(lua, fs):
    """The falsifier: the target standing at 0.5 (inside MinRange, fix 5's widened rule): the crawler is left (the
    forced step goes instead)."""
    p, z, w = world(lua, zx=10.5, **LOOK_OFF)
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
    seq = step_seq(lua, fs)   # fix 7: three stomps that lowered nothing re-pin to the standing one (rule 3), never before
    assert seq[0] == "repin" and (seq.count("repin") == 1 or seq[1:seq.index("repin", 1)].count("stomp") >= 3)
    pr = progress(lua, fs)
    k = next((i for i, a in enumerate(pr) if i > 0 and a["result"]["step"] == "repin"), len(pr))
    assert all(a["result"].get("target") == 8 for a in pr[:k]) and len(w["presses"]) >= 2


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

def test_the_pile_is_met_in_the_reflex_the_step_out_first_no_hand_back(lua, fs):
    """Three standing within K.MELEE_CROWD_R with pile: no crowd hand-back. Plan 36 Task 2b (7b, re-pinned under the
    named change: Plan 35 fix 3 shoved first): the step out first, K.WORK_STEP_TICKS ticks of `work` with step_for
    pile_out and no press, away from the three (west)."""
    p, z, w = three_world(lua, attack_ticks=6, **LOOK_OFF)
    load_work(lua)
    grid(lua)
    p.getZ = lambda s: 0
    gow(lua, p, pile=True)
    run(lua, p, w, 30)
    assert lua.eval("PZA.skills.cur") is not None                     # no hand-back
    assert step_seq(lua, fs)[0] == "work" and w["presses"] == []
    assert progress(lua, fs)[0]["result"]["work"]["step_for"] == "pile_out" and w["walk"][0] < 0
    assert all(a["state"] != "done" for a in acts(lua, fs) if a["aid"] == "m1")
    assert lua.eval("PZA.skills.cur.st.steps.work") == lua.eval("PZA.skills.WORK_STEP_TICKS") == 30


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
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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
    p, z, w = world(lua, zx=BAND_X, attack_ticks=20)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, bandLo=1.25)
    run(lua, p, w, 10)
    assert w["presses"] and work_of(lua, "contact") == 0


def test_every_progress_line_carries_contact_and_the_work_leaf(lua, fs):
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 70)
    pr = progress(lua, fs)
    assert pr and all("contact" in a["result"] and "work" in a["result"] for a in pr)
    assert all(set(a["result"]["work"]) <= WORK_LEAF for a in pr)
    stepped = [a["result"]["work"] for a in pr if a["result"]["step"] == "work"]   # fix 5: a stepping tick's own
    assert stepped and all({"clear", "n", "heading", "step_for"} <= set(x) for x in stepped)
    assert all("clear" not in a["result"]["work"] for a in pr if a["result"]["step"] != "work")
    assert stepped[0]["n"] == 1 and stepped[0]["gap"] > 0 and stepped[0]["step_for"] == "gap"


def test_the_done_line_carries_contact_the_leaf_and_the_steps(lua, fs):
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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


def test_the_core_announces_1_15(lua, fs):
    assert lua.eval("PZA.VERSION") == "1.15"   # Plan 36 Task 2a: PZA/1.15, backswing, moving_back and air


# ---- the re-send ------------------------------------------------------------------------------------------------------

def test_a_same_target_resend_keeps_the_footwork_state_and_takes_the_new_work_fields(lua, fs):
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
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
    p, z, w = world(lua, zx=BAND_X, zspeed=2.0, **LOOK_OFF)          # a chaser at the walk's pace: the gap held
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
    step_world(w, p)                                                  # the counted tick's update
    lua.globals()._p = p                                              # Plan 36 Task 1: the ring read fresh on the
    lua.execute("local w = PZA.skills.cur.st.work; w.room, w.roomTicks = PZA.skills.workRoom(_p), 0")   # tick's square
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
    lua.globals()._clock["ms"] += TICK_MS
    tick(lua, Rec(p, log, "p"))
    assert lua.eval("PZA.skills.cur.st.step") == "work" and lua.eval("PZA.skills.cur.st.work.sinceChoose") == 0
    # 25: the melee's face tick (the dead check 2, isDead, the two positions 4, the hit read, isOnFloor, isKnockedDown
    # within the reach, the snap, the look: 12), the stance re-held for the step (nullifyAiming at the meet's release,
    # setForceAim at the step: 2), the re-choose (getZ, the five others' positions 10; Plan 36 Task 1: the squares are
    # the room ring's, fresh here, read at a choose when due and counted in its own test); none of the five is within
    # the near read's candidates (the reach + K.MELEE_CROWD_SLACK), the floor off (0); fix 2: the nearest's
    # getRealState (the attack read, 1): 26
    assert len(log) == 26 and len(log) < 40, sorted(log)
    assert lua.eval("PZA.skills.roomReads") == 2                     # the pre-read ring reused at the choose


# ---- fix 1: the live shape (x_trial-ladder-20261110-081250 and -081935: the step never went) -------------------------

def test_inside_the_band_the_step_goes_between_presses_with_the_look_on(lua, fs):
    """The smokes' shape: a chaser inside the reach less bandLo with the look on. The meet pressed swing after swing
    (a7: 193 swing ticks, the gap 0.73, no idle tick) and the footwork, reached only at the meet's stand and face,
    never ran. Fix 1: at a press's result with the nearest standing inside the band, the step `work` goes before the
    next press (the spec's item 1: the step and the press alternate as the swing clip and the gap allow)."""
    p, z, w = world(lua, zx=BAND_X, zspeed=0.0, attack_ticks=20)   # fix 2: beyond K.WORK_POINT_BLANK_R
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 60)
    seq = step_seq(lua, fs)
    assert seq[:3] == ["swing", "work", "swing"] and len(w["presses"]) >= 2   # the press, the step, the press
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
    assert "clear" not in leaf and "n" not in leaf and leaf["gap"] > 1.075   # beyond the band (the close walk)


# ---- fix 2: no step at point blank or into a lunge (x_trial-ladder-20261110-084643, a73's wound) ---------------------

def a73_world(lua):
    """a73's shape at its wound (frames 2608 to 2618): the target 7 struck at 0.96 tiles east, a second standing
    zombie 8 attacking at 0.59 tiles south. The step went at the gap 0.59 (the leaf's), ahead of the meet's re-pin to
    8 and its press, and the bite landed at 0.73 eleven ticks into it."""
    p, z, w = world(lua, zx=10.96, zspeed=0.0, attack_ticks=6)
    o8 = make_zombie(8, 10.0, 19.41)
    o8.getRealState = lambda s: "attack"
    records(lua, [{"id": 8, "dist": 0.59, "x": 10.0, "y": 19.41}, target_rec(w)], {7: z, 8: o8})
    return p, z, w


def test_no_step_with_the_nearest_standing_at_point_blank(lua, fs):
    p, z, w = a73_world(lua)
    gow(lua, p)
    run(lua, p, w, 40)
    seq = step_seq(lua, fs)
    assert "work" not in seq and "repin" in seq and lua.eval("PZA.skills.cur.st.id") == 8
    assert len(w["presses"]) >= 2 and work_of(lua, "held") == "point_blank"
    assert lua.eval("PZA.skills.WORK_POINT_BLANK_R") == 0.9


def test_beyond_point_blank_inside_the_band_the_step_still_goes(lua, fs):
    """The falsifier: the second zombie gone, the target at 0.95 (inside the band, beyond 0.9): the step goes."""
    p, z, w = world(lua, zx=10.95, zspeed=0.0, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 20)
    assert "work" in step_seq(lua, fs) and work_of(lua, "held") is None


def test_the_step_goes_against_a_lunging_chaser_and_ends_at_once_on_an_attack(lua, fs):
    """Fix 4 (the controller's ruling: live, `lunge` is every chaser's state at any distance, x_trial-ladder-20261110-
    091352): the step goes at 0.95 against a chaser reading `lunge-network`, no hold; once its state reads `attack`
    the step ends at once and the meet presses; the leaf says held attack, never lunge."""
    p, z, w = world(lua, zx=10.95, zspeed=2.0, attack_ticks=6, **LOOK_OFF)   # a chaser at the walk's pace
    state = {"v": "lunge-network"}
    z.getRealState = lambda s: state["v"]
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 10, stop=lambda: lua.eval("PZA.skills.cur.st.step") == "work")
    assert lua.eval("PZA.skills.cur.st.step") == "work" and work_of(lua, "held") is None
    state["v"] = "attack"
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.step") != "work" and work_of(lua, "held") == "attack"
    n = len(step_seq(lua, fs))
    run(lua, p, w, 10)
    assert "work" not in step_seq(lua, fs)[n:]


def test_a_lunge_state_is_never_written_as_held(lua, fs):
    """The falsifier of the dropped hold: a lunging chaser in the band for 30 ticks never reads held lunge."""
    p, z, w = world(lua, zx=10.95, zspeed=2.0, attack_ticks=6, **LOOK_OFF)
    z.getRealState = lambda s: "lunge"
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 30)
    assert "work" in step_seq(lua, fs)
    assert all(a["result"].get("work", {}).get("held") != "lunge" for a in acts(lua, fs) if a.get("result"))


# ---- Plan 36 Task 2b (items 5 and 7b; fix 3's trigger and its shove-first loop deleted, their five tests with it): the
# step out at point blank, a shove always followed by the step, the shove a chosen knock-down against several ---------

def pile_world(lua, others, attackers=0, tx=10.55, **kw):
    """The target 7 at tx east, more standing zombies at the distances `others` (north and south of the player)."""
    p, z, w = world(lua, zx=tx, attack_ticks=6, **kw)
    recs, objs = [target_rec(w)], {7: z}
    for i, dd in enumerate(others):
        y = 20.0 + dd if i % 2 == 0 else 20.0 - dd
        o = make_zombie(20 + i, 10.0, y)
        recs.append({"id": 20 + i, "dist": dd, "x": 10.0, "y": y})
        objs[20 + i] = o
    records(lua, recs, objs, attackers=attackers)
    return p, z, w


def test_three_at_point_blank_under_the_withdraw_step_out_not_shove(lua, fs):
    """7b (the Task 3 trio smoke's a34: three at 0.5 tiles, the withdraw sent, shove-repin-shove for 4 s while four
    bites landed): three standing at 0.5 with the withdraw west: the step out (step_for pile_out) on the first tick,
    no shove before it; the point-blank hold does not hold it."""
    p, z, w = pile_world(lua, (0.5, 0.5), tx=10.5, attackers=2)
    gow(lua, p, pile=True, withdrawX=-1.0, withdrawY=0.0)
    run(lua, p, w, 10)
    seq = step_seq(lua, fs)
    assert seq[0] == "work" and w["presses"] == [] and "shove" not in seq
    assert progress(lua, fs)[0]["result"]["work"]["step_for"] == "pile_out" and work_of(lua, "pileWhy") == "pile_out"
    assert w["walk"][0] < 0                                          # away from the three's centroid (east)


def test_a_shove_s_next_tick_is_the_step_out_never_a_repin_and_another_shove(lua, fs):
    """Item 5's chosen knock-down: one standing inside point blank (the target at 0.55) and a second within the reach
    (1.2): the target shoved (shove_for knockdown on its line); the tick after its result steps out (pile_out)."""
    p, z, w = pile_world(lua, (1.2,))
    gow(lua, p, pile=True)
    run(lua, p, w, 12)
    seq = step_seq(lua, fs)
    assert seq[0] == "shove" and w["presses"][0]["shove"] is True
    assert seq[1] == "work" and "repin" not in seq[:2]
    pr = progress(lua, fs)
    assert pr[0]["result"]["work"].get("shove_for") == "knockdown"
    assert pr[1]["result"]["work"]["step_for"] == "pile_out" and work_of(lua, "pileWhy") == "shove"
    assert len([x for x in w["presses"] if x["shove"]]) == 1


def test_a_lone_target_at_point_blank_is_no_chosen_knock_down(lua, fs):
    """The falsifier: the target alone at 0.55 (inside MinRange): the meet's protective shove, no shove_for, and its
    result is still followed by the step out."""
    p, z, w = pile_world(lua, ())
    gow(lua, p, pile=True)
    run(lua, p, w, 12)
    pr = progress(lua, fs)
    assert pr[0]["result"]["step"] == "shove" and "shove_for" not in pr[0]["result"]["work"]
    assert pr[1]["result"]["step"] == "work" and pr[1]["result"]["work"]["step_for"] == "pile_out"


def test_the_step_out_lasts_work_step_ticks_then_the_press(lua, fs):
    p, z, w = pile_world(lua, (0.6,), tx=10.5, **LOOK_OFF)
    gow(lua, p, pile=True)
    run(lua, p, w, 31)
    assert lua.eval("PZA.skills.cur.st.steps.work") == lua.eval("PZA.skills.WORK_STEP_TICKS")
    assert work_of(lua, "pileState") == "press"


def test_with_no_way_out_the_pile_presses(lua, fs):
    """Every ring heading walled (the player's square boxed in): no step out, the meet presses (its shove)."""
    p, z, w = pile_world(lua, (0.6,), tx=10.5, squares=False)
    grid(lua, solid={(x, y) for x in range(8, 13) for y in range(18, 23) if (x, y) != (10, 20)})
    gow(lua, p, pile=True)
    run(lua, p, w, 3)
    assert "pile_out" not in [a["result"]["work"].get("step_for") for a in progress(lua, fs)]
    assert w["presses"] and w["presses"][0]["shove"] is True


# ---- Plan 36 Task 2b item 6: the nearest attacker faced ---------------------------------------------------------------

def test_inside_point_blank_the_attacker_is_re_pinned_to(lua, fs):
    """The target 7 at 0.85 standing idle; 8 at 0.8 reading attack, the engine's attackers 1: the reflex re-pins to 8
    (repin_for attacker), though it is not nearer by K.MELEE_REPIN_SLACK."""
    p, z, w = world(lua, zx=10.85, **LOOK_OFF)
    z.getRealState = lambda s: "idle"
    o8 = make_zombie(8, 10.0, 20.8)
    o8.getRealState = lambda s: "attack"
    records(lua, [target_rec(w), {"id": 8, "dist": 0.8, "x": 10.0, "y": 20.8}], {7: z, 8: o8}, attackers=1)
    gow(lua, p)
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.id") == 8
    assert progress(lua, fs)[-1]["result"]["work"].get("repin_for") == "attacker"


def test_with_no_attacker_counted_no_re_pin_within_the_slack(lua, fs):
    p, z, w = world(lua, zx=10.85, **LOOK_OFF)
    o8 = make_zombie(8, 10.0, 20.8)
    o8.getRealState = lambda s: "attack"
    records(lua, [target_rec(w), {"id": 8, "dist": 0.8, "x": 10.0, "y": 20.8}], {7: z, 8: o8}, attackers=0)
    gow(lua, p)
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.id") == 7


# ---- Plan 36 Task 2b item 4: the step keyed to the next landing hit, the stagger in ------------------------------------

def test_a_staggered_target_beyond_the_reach_gets_the_step_in(lua, fs):
    """The target at 1.75 (beyond the reach 1.475, within it + K.WORK_STAGGER_R) reading staggerback: one step toward
    it (east), step_for stagger_in, the walk not of kind work (stopped at the press)."""
    p, z, w = world(lua, zx=11.75, **LOOK_OFF)
    z.getRealState = lambda s: "staggerback"
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert step_seq(lua, fs)[0] == "work" and work_of(lua, "stepFor") == "stagger_in" and w["walk"][0] > 0
    assert lua.eval("PZA.skills.cur.st.walk") == "in"


def test_a_target_beyond_the_reach_not_staggered_gets_no_step_in(lua, fs):
    p, z, w = world(lua, zx=11.75, **LOOK_OFF)
    z.getRealState = lambda s: "idle"
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert "stagger_in" not in [(a["result"].get("work") or {}).get("step_for") for a in progress(lua, fs)]


def test_the_retreat_s_back_step_holds_at_the_reach_edge(lua, fs):
    """A target standing still at 1.3 (inside the reach) under the withdraw, the look held off (no press): the back
    step goes while the predicted landing distance is within the reach less K.WORK_EDGE_SLACK, then is withheld (held
    reach, the meet's face: no close walk inside the reach): the gap ends at the reach's edge, not beyond it."""
    p, z, w = world(lua, zx=11.3, zspeed=0.0, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0)
    run(lua, p, w, 90)
    gap = math.hypot(w["zx"] - w["px"], w["zy"] - w["py"])
    seq = step_seq(lua, fs)
    assert seq[0] == "work" and "close" not in seq and work_of(lua, "held") == "reach" and seq[-1] == "face"
    assert 1.475 - 0.1 <= gap <= 1.475


def test_the_landing_reads_the_closing_and_under_backswing_the_walk(lua, fs):
    """K.workLanding at its method: the gap less the closing speed times the flight time; under backswing plus the
    walk's speed kept from the last walking tick."""
    melee_world(lua)
    load_work(lua)
    lua.execute("_st = { id = 7, px = 10.0, py = 20.0, zx = 11.0, zy = 20.0, dtS = 0.0, hist = {}, walk = nil, "
                "backV = 0, work = { tc = 0.25, backswing = false } }")
    land = lambda: lua.eval("PZA.skills.workLanding(nil, _st, 1.0, 7)")
    assert land() == pytest.approx(1.0)
    lua.execute("_st.hist = { { t = 0, x = 11.5, y = 20.0 }, { t = 500, x = 11.0, y = 20.0 } }")   # 1 tile a second
    assert land() == pytest.approx(0.75)
    lua.execute("_st.work.backswing = true; _st.walk = 'work'; _st.backV = 2.0")
    assert land() == pytest.approx(1.25)
    lua.execute("_st.walk = nil; _st.backV = 0")
    assert land() == pytest.approx(1.25)                             # the walk's speed kept on a standing tick


# ---- fix 5: a crawler within crawlerR forces the step and is stomped first inside the shove range (the run 103609) ----

def crawler_world(lua, tx, cx, cy, **kw):
    """a56's shape (frames 2747 to 2805): a standing target 7 at (tx, 20.0), the crawler 8 at (cx, cy) (crawler and
    onFloor true in the frame), its position a test may move (`cpos`)."""
    p, z, w = world(lua, zx=tx, attack_ticks=6, **kw)
    cpos = {"x": cx, "y": cy}
    c = crawler(8, cx, cy)
    c.getX, c.getY = (lambda s: cpos["x"]), (lambda s: cpos["y"])

    def recs():
        cd = math.hypot(cpos["x"] - w["px"], cpos["y"] - w["py"])
        records(lua, [target_rec(w), {"id": 8, "dist": cd, "crawler": True, "onFloor": True, "x": cpos["x"],
                                      "y": cpos["y"]}], {7: z, 8: c})
    recs()
    return p, z, w, cpos, recs


def test_a_crawler_within_the_buffer_takes_the_perpendicular_step_whatever_the_point_blank_hold(lua, fs):
    """Plan 36 Task 2b item 7 (re-pinned under the named change: fix 5 stepped away from the crawler, step_for
    crawler): the standing target at 0.4 east and the crawler at 0.95 north: the step perpendicular to the crawler's
    bearing, the ring open both ways, to the side away from the target (west), step_for crawler_buffer, no hold."""
    p, z, w, cpos, recs = crawler_world(lua, 10.4, 10.0, 20.95)
    gow(lua, p)
    run(lua, p, w, 3)
    assert step_seq(lua, fs)[0] == "work" and work_of(lua, "stepFor") == "crawler_buffer"
    assert w["walk"][0] < -0.99 and work_of(lua, "held") is None
    leaf = progress(lua, fs)[-1]["result"]["work"]
    assert leaf["step_for"] == "crawler_buffer" and "held" not in leaf


def test_a_crawler_under_the_feet_leaves_a_heading_away_from_it(lua, fs):
    """a56's crawler at 0.17 tiles (frames 2747 to 2772) vetoed every probe point within crawlerR of it, so every
    heading read cornered: a probe point moving away from a crawler is no longer vetoed by it."""
    p, z, w, cpos, recs = crawler_world(lua, 10.4, 10.0, 20.17)
    gow(lua, p)
    run(lua, p, w, 3)
    assert "cornered" not in step_seq(lua, fs) and work_of(lua, "stepFor") == "crawler_buffer"   # Plan 36 Task 2b


def test_a_crawler_beyond_crawler_r_inside_the_buffer_takes_the_step(lua, fs):
    """Plan 36 Task 2b: the crawler at 1.6 north (beyond crawlerR's 1.2, inside K.CRAWLER_BUFFER_R's 2.0), the target
    at 1.3: the buffer step before the next press; with the crawler at 2.1 none."""
    p, z, w, cpos, recs = crawler_world(lua, 11.3, 10.0, 21.6, **LOOK_OFF)
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "stepFor") == "crawler_buffer"
    p2, z2, w2, c2, r2 = crawler_world(lua, 11.3, 10.0, 22.1, **LOOK_OFF)
    gow(lua, p2, aid="m2")
    run(lua, p2, w2, 2)
    assert "crawler_buffer" not in [(a["result"].get("work") or {}).get("step_for") for a in progress(lua, fs, "m2")]


def test_a_crawler_in_its_bite_with_a_standing_zombie_near_is_buffered_not_stomped(lua, fs):
    """The crawler at 0.5 north (inside K.CRAWLER_BITE_R) and the standing target at 0.6 (within K.MELEE_CROWD_R): no
    re-pin to the crawler (the stomp waits for nothing standing within 0.9), the buffer step."""
    p, z, w, cpos, recs = crawler_world(lua, 10.6, 10.0, 20.5, **LOOK_OFF)
    gow(lua, p)
    run(lua, p, w, 2)
    assert lua.eval("PZA.skills.cur.st.id") == 7 and work_of(lua, "stepFor") == "crawler_buffer"


def test_a_crawler_with_no_standing_zombie_in_the_shove_range_is_stomped_first(lua, fs):
    """The crawler at 0.9 and the standing target at 1.3 (inside the reach, beyond MinRange): re-pinned to the
    crawler and stomped (the shove pair at the floor)."""
    p, z, w, cpos, recs = crawler_world(lua, 11.3, 10.0, 20.9)
    gow(lua, p)
    run(lua, p, w, 90, stop=lambda: w["presses"])
    assert step_seq(lua, fs)[0] == "repin" and lua.eval("PZA.skills.cur.st.id") == 8
    assert w["presses"] and w["presses"][0]["shove"] is True


def test_the_leaf_s_crawler_is_this_tick_s(lua, fs):
    """The leaf's crawler is the nearest crawler's distance read this tick, absent with none within crawlerR x 2."""
    p, z, w, cpos, recs = crawler_world(lua, 11.2, 10.0, 22.0, **LOOK_OFF)   # 2.0: within crawlerR x 2
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "crawlerD") == pytest.approx(2.0, abs=0.05)
    cpos["y"] = 22.3
    recs()
    run(lua, p, w, 1)
    assert work_of(lua, "crawlerD") == pytest.approx(2.3, abs=0.05)
    cpos["y"] = 24.0                                                  # 4.0: beyond crawlerR x 2
    recs()
    run(lua, p, w, 1)
    assert work_of(lua, "crawlerD") is None


# ---- fix 6: the fighting retreat under a withdraw bias (the run 104702: four standing at 1.0 to 1.4 tiles for 60 frames
# while the character stood shoving, pace 0, then the drag-down) -----------------------------------------------------

def retreat_world(lua, **kw):
    """Three standing closing: the target 7 at 1.6 tiles east chasing at 2.5 tiles a second (faster than the walk),
    two more at 1.8 north-east and 2.0 south-east (the frame's records)."""
    p, z, w = world(lua, zx=11.6, zspeed=2.5, attack_ticks=12, **kw)
    o8, o9 = make_zombie(8, 11.3, 21.5), make_zombie(9, 11.3, 18.4)
    records(lua, [target_rec(w), {"id": 8, "dist": 1.98, "x": 11.3, "y": 21.5},
                  {"id": 9, "dist": 2.06, "x": 11.3, "y": 18.4}], {7: z, 8: o8, 9: o9})
    return p, z, w


def test_under_a_withdraw_bias_the_step_is_the_default_and_the_press_the_exception(lua, fs):
    """The step every idle tick while the target closes from 1.6; the swing once it is within the reach and closing;
    the swing staggers it (#4686: the fake's chase stops at the press), not closing, and the step resumes."""
    p, z, w = retreat_world(lua)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("zspeed", 0.0)
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0)
    run(lua, p, w, 90)
    seq = step_seq(lua, fs)
    # Plan 36 Task 2b item 4 (re-pinned under the named change): the first tick reads no closing speed (one sample),
    # the landing the gap 1.6 beyond the reach: the step withheld, then the step once the chase is read
    assert seq[:2] == ["face", "work"] and "swing" in seq           # the step, the press once in reach
    i = seq.index("swing")
    assert "work" in seq[i + 1:]                                   # the step again after the swing
    assert w["presses"] and all(x["d"] <= 1.6 for x in w["presses"])
    leaves = [a["result"]["work"] for a in progress(lua, fs) if a["result"]["step"] == "work"]
    assert leaves and all(x.get("step_for") == "retreat" and x.get("retreat") is True for x in leaves)


def test_under_the_retreat_no_point_blank_hold(lua, fs):
    """The target at 0.95 standing still (not closing): under the retreat the step goes, no hold."""
    p, z, w = world(lua, zx=10.7, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0)
    run(lua, p, w, 3)
    assert step_seq(lua, fs)[0] == "work" and work_of(lua, "held") is None and work_of(lua, "stepFor") == "retreat"


def test_without_the_withdraw_vector_the_band_behaviour_stands(lua, fs):
    """The falsifier: the same three closing with no withdraw: no step before the first press (the target beyond the
    band), the leaf never reads retreat."""
    p, z, w = retreat_world(lua)
    gow(lua, p)
    run(lua, p, w, 90)
    seq = step_seq(lua, fs)
    assert seq[0] != "work" and "swing" in seq and "work" not in seq[:seq.index("swing")]
    assert all("retreat" not in (a["result"].get("work") or {}) for a in progress(lua, fs))


# ---- fix 7: the stall deferred in shove range; a press beyond reach neither counts nor resets (the run 112648, a112) ---

def test_a_stall_with_the_target_in_shove_range_is_deferred_then_ends_once_it_is_beyond(lua, fs):
    """a112: three swings that lowered nothing reach the stall (3) with the target at 0.7 (inside shoveR 0.9): no done
    lost, the meet presses on, the leaf reads stall_held; once the target stands beyond shoveR with the counter still
    at the stall, the melee ends lost, no progress."""
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 120, stop=lambda: lua.eval("PZA.skills.cur.st.nothing") >= 3)
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur") is not None and lua.eval("PZA.skills.cur.st.nothing") >= 3
    n = len(w["presses"])
    run(lua, p, w, 40)
    assert lua.eval("PZA.skills.cur") is not None and len(w["presses"]) > n
    assert any((a["result"].get("work") or {}).get("stall_held") is True for a in progress(lua, fs))
    w["zx"] = 11.3                                                    # beyond shoveR, within the release
    records(lua, [target_rec(w)], {7: z})
    run(lua, p, w, 30, stop=lambda: lua.eval("PZA.skills.cur") is None)
    r = last(lua, fs)["result"]
    assert (last(lua, fs)["state"], r["end"], r["why"]) == ("done", "lost", "no progress")


def test_at_the_stall_beyond_shove_range_another_standing_zombie_is_re_pinned(lua, fs):
    """Rule 3: at the stall with the target beyond shoveR and another standing zombie within workR, the re-pin."""
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    o8 = make_zombie(8, 10.0, 22.5)
    records(lua, [target_rec(w), {"id": 8, "dist": 2.5, "x": 10.0, "y": 22.5}], {7: z, 8: o8})
    gow(lua, p)
    run(lua, p, w, 120, stop=lambda: lua.eval("PZA.skills.cur.st.nothing") >= 3)
    w["zx"] = 11.3
    records(lua, [target_rec(w), {"id": 8, "dist": 2.5, "x": 10.0, "y": 22.5}], {7: z, 8: o8})
    run(lua, p, w, 20, stop=lambda: lua.eval("PZA.skills.cur.st.id") == 8)   # a press may still be in flight
    assert lua.eval("PZA.skills.cur") is not None and lua.eval("PZA.skills.cur.st.id") == 8
    assert "repin" in step_seq(lua, fs)


def test_without_work_the_stall_ends_lost_in_shove_range_as_before(lua, fs):
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    go(lua, p)
    run(lua, p, w, 200, stop=lambda: lua.eval("PZA.skills.cur") is None)
    r = last(lua, fs)["result"]
    assert (r["end"], r["why"]) == ("lost", "no progress")


def test_a_press_whose_d_min_stayed_beyond_reach_neither_counts_nor_resets(lua, fs):
    """Rule 2: reach 1.0 (the bat's engine reach 1.25), a chaser at 1.2 closing at 2.0: the swing goes at the
    predicted collision (d_min 1.2, beyond the reach) and lowers nothing: st.nothing stays at its value."""
    p, z, w = world(lua, zx=11.2, zspeed=2.0, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, reach=1.0)
    lua.execute("PZA.skills.cur.st.nothing = 1")
    run(lua, p, w, 12, stop=lambda: len(w["presses"]) >= 1 and lua.eval("PZA.skills.cur.st.strike") is None)
    lf = leaves(lua, fs)
    assert lf and lf[0]["d_min"] > 1.0 and lua.eval("PZA.skills.cur.st.nothing") == 1


def test_a_press_within_reach_that_lowered_nothing_counts(lua, fs):
    p, z, w = world(lua, zx=10.9, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, reach=1.0)
    run(lua, p, w, 12, stop=lambda: len(w["presses"]) >= 1 and lua.eval("PZA.skills.cur.st.strike") is None)
    lf = leaves(lua, fs)
    assert lf and lf[0]["d_min"] <= 1.0 and lua.eval("PZA.skills.cur.st.nothing") == 1


def test_at_the_stall_in_shove_range_another_standing_zombie_is_re_pinned_first(lua, fs):
    """Fix 7b (a112's second reading: the stalled target lunging at 0.50 across an unmapped fence while 25201 climbed
    over and bit): the stalled target at 0.7 (inside shoveR) and another standing zombie at 2.5: the re-pin to it,
    never stall_held, and the re-pin's line reads repin_for stall."""
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    o8 = make_zombie(8, 10.0, 22.5)
    records(lua, [target_rec(w), {"id": 8, "dist": 2.5, "x": 10.0, "y": 22.5}], {7: z, 8: o8})
    gow(lua, p)
    run(lua, p, w, 150, stop=lambda: lua.eval("PZA.skills.cur.st.id") == 8)
    assert lua.eval("PZA.skills.cur") is not None and lua.eval("PZA.skills.cur.st.id") == 8
    assert all((a["result"].get("work") or {}).get("stall_held") is not True for a in progress(lua, fs))
    rp = [a for a in progress(lua, fs) if a["result"]["step"] == "repin"]
    assert rp and rp[-1]["result"]["work"].get("repin_for") == "stall"
    run(lua, p, w, 30)                                                # the stalled 7 at 0.7 is never re-pinned back
    assert lua.eval("PZA.skills.cur.st.id") == 8


def test_at_the_stall_a_crawler_is_no_other_standing_zombie(lua, fs):
    """The stalled target at 0.7 and only a crawler (isCrawling) at 2.5 standing-read: no re-pin, the hold."""
    p, z, w = world(lua, zx=10.7, attack_ticks=6)
    c = make_zombie(8, 10.0, 22.5)
    c.isCrawling = lambda s: True
    records(lua, [target_rec(w), {"id": 8, "dist": 2.5, "x": 10.0, "y": 22.5}], {7: z, 8: c})
    gow(lua, p)
    run(lua, p, w, 150, stop=lambda: lua.eval("PZA.skills.cur.st.nothing") >= 3)
    run(lua, p, w, 20)
    assert lua.eval("PZA.skills.cur.st.id") == 7
    assert any((a["result"].get("work") or {}).get("stall_held") is True for a in progress(lua, fs))


# ---- Plan 36 Task 1 fix 1: Kahlua's % and the ring index (x_trial-ladder-20261111-175926 parked the client) ----------

def _operand_left(src, i):
    """The start of the binary operator's left operand ending before src[i] (spaces skipped): a balanced (...) group
    with its dotted callee, or a dotted name or number."""
    j = i
    while j > 0 and src[j - 1] == " ":
        j -= 1
    if src[j - 1] == ")":
        depth, k = 0, j - 1
        while True:
            if src[k] == ")":
                depth += 1
            elif src[k] == "(":
                depth -= 1
                if depth == 0:
                    break
            k -= 1
        j = k
    while j > 0 and (src[j - 1].isalnum() or src[j - 1] in "_."):
        j -= 1
    return j


def _operand_right(src, i):
    """The end of the binary operator's right operand starting after src[i]: a dotted name or number, with a call's
    balanced (...) when one follows."""
    j = i
    while src[j] == " ":
        j += 1
    while src[j].isalnum() or src[j] in "_.":
        j += 1
    if src[j] == "(":
        depth = 0
        while True:
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
    return j


def kahlua_mod(src):
    """The Lua source with every code (not comment) binary ` % ` rewritten to _kmod(a, b), Kahlua's truncating modulo
    (the 42.22.2 jar: KahluaThread.primitiveMath @111-@127 L1355-L1356, a - (int)(a / b) * b), which lupa's Lua 5.1
    floors instead: a test host that reads % as the client does."""
    out = []
    for line in src.split("\n"):
        code, sep, comment = line.partition("--")
        while " % " in code:
            i = code.index(" % ")
            a, b = _operand_left(code, i), _operand_right(code, i + 3)
            code = code[:a] + "_kmod(%s, %s)" % (code[a:i], code[i + 3:b].strip()) + code[b:]
        out.append(code + sep + comment)
    return "\n".join(out)


def kahlua_host(lua):
    lua.execute("function _kmod(a, b) if b == 0 then return 0 / 0 end local q = a / b "
                "if q >= 0 then q = math.floor(q) else q = math.ceil(q) end return a - q * b end")


def load_work_kahlua(lua):
    kahlua_host(lua)
    lua.execute(kahlua_mod(open(lua_file("client/PZAgent_StanceWork.lua"), encoding="utf-8").read()))


def test_the_kahlua_host_truncates_as_the_jar_does(lua):
    kahlua_host(lua)
    assert lua.eval("_kmod(-164.7, 360)") == pytest.approx(-164.7) and lua.eval("-164.7 % 360") == pytest.approx(195.3)
    assert lua.eval("_kmod(7, 3)") == 1 and lua.eval("_kmod(-4, 8)") == -4
    assert kahlua_mod("x = math.floor(((deg % 360) + 22.5) / 45) % 8 + 1 -- 25 % kept") == \
        "x = _kmod(math.floor(((_kmod(deg, 360)) + 22.5) / 45), 8) + 1 -- 25 % kept"


@pytest.mark.parametrize("vec, index", [((1.0, 0.0), 1), ((0.0, 1.0), 3), ((-1.0, 0.0), 5), ((0.0, -1.0), 7),
                                        ((-0.96, -0.26), 5), ((-0.7, -0.72), 6), ((0.92, -0.38), 1),
                                        ((0.92, -0.39), 8), ((-1.0, -1e-12), 5)])
def test_on_the_kahlua_host_every_heading_indexes_the_ring(lua, fs, vec, index):
    """The trial's away heading (-1.1, -0.3), atan2 -164.7 degrees, indexed -3 on Kahlua's truncating %: every vector
    indexes 1 to 8 on the client's arithmetic."""
    melee_world(lua)
    load_work_kahlua(lua)
    assert lua.eval("PZA.skills.workRoomIndex")(*vec) == index


def test_the_trial_s_geometry_steps_on_the_kahlua_host(lua, fs):
    """x_trial-ladder-20261111-175926's frames 286 to 289: the character standing, one zombie lunging in south-east
    of it (+1.10, +0.30 at 1.13 tiles there; here inside the band at 0.95), the ring open on every heading: the first
    choose's away heading points west-north-west (atan2 below -90) and the step goes, no raise."""
    p, z, w = melee_world(lua, px=10.2, py=20.9, zx=10.2 + 0.9165, zy=20.9 + 0.25, **LOOK_OFF)
    load_work_kahlua(lua)
    grid(lua)
    p.getZ = lambda s: 0
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 2)
    assert lua.eval("PZA.skills.cur.st.step") == "work" and work_of(lua, "clear") is True
    assert work_of(lua, "heading") < -90 and work_of(lua, "turn") == 0


@pytest.mark.parametrize("ring", ["nil", "{}", "{ h = {} }", "{ h = { 1, 2, 3 } }", "{ h = { 3, 3, 3, 3, 0 / 0, 3, 3, 3 } }"])
def test_a_ring_entry_it_lacks_reads_closed_never_a_nil_comparison(lua, fs, ring):
    melee_world(lua)
    load_work(lua)
    v = lua.eval("PZA.skills.workRoomOpen(%s, -1, 0)" % ring)
    assert v == 0.0
    assert lua.eval("PZA.skills.workRoomOpen(nil, 0 / 0, 1)") == 0.0
    assert lua.eval("PZA.skills.workRoomIndex(0 / 0, 1)") is None


def test_a_non_finite_sum_is_no_heading_and_the_leaf_names_it(lua, fs):
    """A withdraw vector of NaN (no planner sends one; the guard's own case, tested at the choose): no ring index read,
    the step cornered, the leaf's nan_heading."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, withdrawX=0.0, withdrawY=1.0)
    lua.execute("PZA.skills.cur.st.work.withdrawY = 0 / 0")
    run(lua, p, w, 2)
    assert lua.eval("PZA.skills.cur.st.step") == "cornered" and work_of(lua, "nanHeading") is True
    leaf = progress(lua, fs)[-1]["result"]["work"]
    assert leaf.get("nan_heading") is True


def test_the_melee_never_holds_a_nil_ring(lua, fs):
    """A read that answers none (K.workRoom nil): the last ring kept, else an all-closed one (0.0, wall)."""
    p, z, w = world(lua, zx=BAND_X, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    lua.execute("_realRoom = PZA.skills.workRoom; PZA.skills.workRoom = function() return nil end")
    gow(lua, p)
    run(lua, p, w, 1)
    assert list(lua.eval("PZA.skills.cur.st.work.room.stop").values()) == ["wall"] * 8
    assert lua.eval("PZA.skills.cur.st.step") == "cornered"
    lua.execute("PZA.skills.workRoom = _realRoom; PZA.skills.cur.st.work.room = nil")
    lua.execute("PZA.skills.cur.st.work.sinceChoose = PZA.skills.WORK_TICKS")
    run(lua, p, w, 1)
    kept = lua.eval("PZA.skills.cur.st.work.room.h[5]")
    lua.execute("PZA.skills.workRoom = function() return nil end")
    lua.execute("PZA.skills.cur.st.work.sinceChoose, PZA.skills.cur.st.work.roomTicks = PZA.skills.WORK_TICKS, 99")
    run(lua, p, w, 1)
    assert lua.eval("PZA.skills.cur.st.work.room.h[5]") == kept == 3.0


# ---- Plan 36 Task 2a (PZA/1.15): the press on the back step (backswing), the leaf's moving_back and air ----------------

def _press_walks(p, w, also=None):
    """w's on_attack recording the auto-walk at each DoAttack (the fake's motor flag: setAutoWalk's last value)."""
    seen = []

    def on_attack(wd, shove):
        seen.append(p.motor["autoWalk"])
        if also is not None:
            also(wd, shove)
    w["on_attack"] = on_attack
    return seen


def _stagger(wd, shove):
    wd["zspeed"] = 0.0   # the swing staggers the chaser (#4686), as the retreat's own test


@pytest.mark.parametrize("over", [{"backswing": "yes"}, {"backswing": 1}])
def test_a_backswing_that_is_no_boolean_is_bad_args(lua, fs, over):
    p, z, w = world(lua, zx=11.0)
    a = dict(ARGS)
    a.update(WORK)
    a.update(over)
    start(lua, p, "melee", aid="m1", **a)
    assert states(acts(lua, fs)) == [("m1", "rejected", "bad args")]


def test_backswing_is_a_work_argument_needing_work_r(lua, fs):
    """backswing alone (no workR) is a work field given without the footwork's numbers: bad args."""
    p, z, w = world(lua, zx=11.0)
    go(lua, p, backswing=True)
    assert states(acts(lua, fs)) == [("m1", "rejected", "bad args")]


def test_backswing_is_kept_on_the_work_state_false_when_absent(lua, fs):
    p, z, w = world(lua, zx=11.0)
    gow(lua, p, backswing=True)
    assert states(acts(lua, fs)) == [("m1", "accepted", "")] and work_of(lua, "backswing") is True
    gow(lua, p, aid="m2")
    assert work_of(lua, "backswing") is False


def test_backswing_absent_stops_the_walk_on_the_press_s_own_tick_as_before(lua, fs):
    """A pin of today's order (Plan 36 Task 2a, named so): under the retreat the step walks until the press, and with
    backswing absent the walk is stopped on the press's own tick (setAutoWalk(false), then DoAttack(0)): the step line
    before the swing reads work, the auto-walk reads false at DoAttack, the leaf's moving_back false, back_presses 0."""
    p, z, w = retreat_world(lua)
    seen = _press_walks(p, w, _stagger)
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0)
    run(lua, p, w, 90)
    seq = step_seq(lua, fs)
    i = seq.index("swing")
    assert seq[i - 1] == "work"                                      # the press launched off the back step
    assert seen and seen[0] is False                                 # the walk stopped on the press's tick
    assert all(x["moving_back"] is False for x in leaves(lua, fs))
    assert progress(lua, fs)[-1]["result"]["back_presses"] == 0


def test_backswing_keeps_the_back_step_walking_through_the_press(lua, fs):
    """The same retreat with backswing true: the auto-walk still reads true at DoAttack and through the press's ticks,
    the leaf's moving_back true and back_presses counted."""
    p, z, w = retreat_world(lua)
    seen = _press_walks(p, w, _stagger)
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0, backswing=True)
    run(lua, p, w, 90, stop=lambda: len(w["presses"]) >= 1)
    seq = step_seq(lua, fs)
    assert seq[-2:] == ["work", "swing"] and seen == [True]
    run(lua, p, w, 3)
    assert lua.eval("PZA.skills.cur.st.strike ~= nil") and p.motor["autoWalk"] is True   # held through the press
    run(lua, p, w, 60)
    lv = leaves(lua, fs)
    assert lv and lv[0]["moving_back"] is True and lv[0]["air"] is False
    r = progress(lua, fs)[-1]["result"]
    assert r["back_presses"] == sum(1 for x in seen if x) >= 1 and r["air_presses"] == 0


def test_backswing_with_no_step_walking_is_no_moving_back(lua, fs):
    """The falsifier: backswing true, the target static inside the band beyond point blank: the first press comes off
    the face step with no walk (moving_back false)."""
    p, z, w = world(lua, zx=10.95, zspeed=0.0, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p, backswing=True)
    run(lua, p, w, 60)
    lv = leaves(lua, fs)
    assert step_seq(lua, fs)[:2] == ["swing", "work"] and lv[0]["moving_back"] is False


def test_air_launch_at_its_method_a_swing_beyond_the_reach(lua, fs):
    """K.meleePressAir (the leaf's air_launch since the addendum) tested at its method (no meet path reaches it:
    swingPress presses a swing only with its predicted distance within the reach): a swing or a floor swing beyond
    reachOf reads true, within it false, a shove or a stomp never, an unread prediction false."""
    p, z, w = world(lua, zx=10.95, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)                                                       # reach 1.475
    run(lua, p, w, 1)
    lua.globals()._p = p

    def air(kind, pred):
        return lua.eval("PZA.skills.meleePressAir(_p, PZA.skills.cur.st, %r, %s)" % (kind, pred))
    assert air("swing", 1.6) is True and air("floor", 1.6) is True
    assert air("swing", 1.475) is False and air("swing", 1.2) is False
    assert air("shove", 1.6) is False and air("stomp", 1.6) is False and air("swing", "nil") is False


def _press_at(lua, p, d):
    """A swing sent through the melee's own press at the running state, its prediction and distance d (no meet path
    presses beyond the reach: the press tested at its method)."""
    lua.globals()._p = p
    lua.execute('PZA.skills.meleeWork.press(_p, PZA.skills.cur.st, "swing", %r, %r, 0, "face", %r)' % (d, d, d))


def test_a_swing_whose_target_stayed_beyond_the_reach_and_landed_nothing_reads_air(lua, fs):
    """The addendum's air, read at the result: the target static at 1.6 tiles (the reach 1.475) through the whole
    flight, the swing landing nothing: air and air_launch true, air_presses 1."""
    p, z, w = world(lua, zx=11.6, zspeed=0.0, attack_ticks=6, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 1)
    _press_at(lua, p, 1.6)
    run(lua, p, w, 10)
    leaf = leaves(lua, fs)[0]
    assert leaf["air"] is True and leaf["air_launch"] is True
    assert progress(lua, fs)[-1]["result"]["air_presses"] == 1


def test_a_swing_beyond_the_reach_that_landed_reads_no_air(lua, fs):
    """The falsifier: the same swing lowering the target's health is no air (it landed), air_launch still true."""
    p, z, w = world(lua, zx=11.6, zspeed=0.0, attack_ticks=6, **LOOK_OFF)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("zhp", wd["zhp"] - 0.4)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 1)
    _press_at(lua, p, 1.6)
    run(lua, p, w, 10)
    leaf = leaves(lua, fs)[0]
    assert leaf["air"] is False and leaf["air_launch"] is True
    assert progress(lua, fs)[-1]["result"]["air_presses"] == 0


def test_a_target_closing_into_the_reach_over_the_flight_reads_no_air(lua, fs):
    """The second falsifier: launched at 1.6 with the target closing at 2.5 tiles a second over a 12-tick flight (into
    the reach before the result), the swing landing nothing: no air (the flight's least distance within the reach)."""
    p, z, w = world(lua, zx=11.6, zspeed=2.5, attack_ticks=12, **LOOK_OFF)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 1)
    _press_at(lua, p, 1.6)
    run(lua, p, w, 14)
    leaf = leaves(lua, fs)[0]
    assert leaf["air"] is False and lua.eval("PZA.skills.cur.st.dMin") < 1.475


def test_air_at_the_result_is_no_shove_and_no_refused_press(lua, fs):
    """K.meleeAirAt at its method: a shove, a refused swing, a knocked-down target and an unread health never read air;
    the swing beyond the reach over its flight with nothing landed does."""
    melee_world(lua)
    load_work(lua)

    def air(s, leaf):
        return lua.eval("PZA.skills.meleeAirAt(%s, %s)" % (s, leaf))
    base = "kind = 'swing', hp0 = 1.0, dFly = 1.6, reachAt = 1.475"
    assert air("{ %s }" % base, "{ hp1 = 1.0 }") is True
    assert air("{ kind = 'shove', hp0 = 1.0, dFly = 1.6, reachAt = 1.475 }", "{ hp1 = 1.0 }") is False
    assert air("{ %s, refused = true }" % base, "{ hp1 = 1.0 }") is False
    assert air("{ %s }" % base, "{ hp1 = 1.0, knock = true }") is False
    assert air("{ %s }" % base, "{ }") is False
    assert air("{ kind = 'swing', hp0 = 1.0, dFly = 1.4, reachAt = 1.475 }", "{ hp1 = 1.0 }") is False


def test_the_back_step_s_speed_is_tracked_and_added_only_under_backswing_with_the_step_walking(lua, fs):
    """K.meleeTrack: the player 0.05 tiles farther from the target over one 50 ms tick reads 1.0 tile a second away
    (a step toward reads 0); K.meleeBackAway adds it only with backswing and the step's walk (st.walk work)."""
    melee_world(lua)
    load_work(lua)
    lua.execute("_st = { zx = 12.0, zy = 20.0, work = { backswing = true }, walk = 'work' }")
    lua.execute("PZA.skills.meleeTrack(_st, 10.0, 20.0, 2.0, 1000)")
    assert lua.eval("_st.backV") == 0
    lua.execute("PZA.skills.meleeTrack(_st, 9.95, 20.0, 2.05, 1050)")
    assert lua.eval("_st.backV") == pytest.approx(1.0)
    assert lua.eval("PZA.skills.meleeBackAway(_st)") == pytest.approx(1.0)
    lua.execute("_st.walk = nil")
    assert lua.eval("PZA.skills.meleeBackAway(_st)") == 0
    lua.execute("_st.walk = 'work'; _st.work.backswing = false")
    assert lua.eval("PZA.skills.meleeBackAway(_st)") == 0
    lua.execute("PZA.skills.meleeTrack(_st, 10.0, 20.0, 2.0, 1100)")
    assert lua.eval("_st.backV") == 0                                 # a step toward the target is no gain


def test_under_backswing_the_retreat_s_prediction_adds_the_back_step(lua, fs):
    """The retreat with backswing: the first swing's d_collide_pred lies above the off arm's reading of the same
    shape by the back step's gain (the player walking away at the press), so it is pressed no earlier."""
    def first(bs):
        from .conftest import make_lua, FakeFS
        fs2 = FakeFS()
        l2 = make_lua(fs2)
        p, z, w = retreat_world(l2)
        w["on_attack"] = _stagger
        gow(l2, p, withdrawX=-1.0, withdrawY=0.0, backswing=bs)
        run(l2, p, w, 90, stop=lambda: len(w["presses"]) >= 1)
        run(l2, p, w, 30)
        leaf = leaves(l2, fs2)[0]
        return leaf["d_press"] - leaf["d_collide_pred"]
    assert first(True) < first(False)                                 # the gain read against the closing


def test_the_meet_s_presses_within_the_reach_read_no_air(lua, fs):
    p, z, w = world(lua, zx=10.95, zspeed=0.0, attack_ticks=6)
    records(lua, [target_rec(w)], {7: z})
    gow(lua, p)
    run(lua, p, w, 40)
    lv = leaves(lua, fs)
    assert lv and all(x["air"] is False for x in lv) and progress(lua, fs)[-1]["result"]["air_presses"] == 0


def test_the_backswing_fields_are_in_the_schema_and_the_generated_melee():
    with open(SCHEMA, encoding="utf-8") as fh:
        defs = json.load(fh)["$defs"]
    assert defs["args_melee"]["properties"]["backswing"]["default"] is False
    for res in ("result_melee", "result_melee_step"):
        props = defs[res]["properties"]
        assert {"air_presses", "back_presses"} <= set(props)
        assert {"moving_back", "air", "air_launch"} <= set(props["press"]["properties"])
    base = dict(targetId=7, mode="strike", reach=1.25, shoveR=0.9, releaseR=2.75, faceR=3.0, pressAngle=41.0,
                pressLo=0.0, floorR=1.0, handbackR=2.0, stall=3, workR=3.5, crawlerR=1.2, bandLo=0.4, floorHealth=0.0)
    assert "backswing" not in pza1.Melee(**base).args()
    assert pza1.Melee(backswing=True, **base).args()["backswing"] is True


# ---- Plan 36 Task 2b: the cadence's press on the moving back step, the buffer's open side ------------------------------

def test_under_backswing_the_retreat_s_next_press_rides_the_back_step(lua, fs):
    """Item 4 (the probe's ruling: the press on the moving back step): the retreat with backswing, the target chasing
    at 2.5 tiles a second (never staggered: it keeps closing): after a press's result the back step goes
    K.WORK_RIDE_TICKS ticks, then the next press is launched with the walk held (moving_back)."""
    p, z, w = retreat_world(lua)
    gow(lua, p, withdrawX=-1.0, withdrawY=0.0, backswing=True)
    run(lua, p, w, 150, stop=lambda: len(w["presses"]) >= 2)
    run(lua, p, w, 20)
    lv = leaves(lua, fs)
    assert len(lv) >= 2 and lv[1]["moving_back"] is True
    seq = step_seq(lua, fs)
    i = seq.index("swing")
    assert "work" in seq[i + 1:seq.index("swing", i + 1)]           # the step between the two presses


def test_the_buffer_step_takes_the_ring_s_open_side(lua, fs):
    """The crawler at 0.95 north and the target at 0.4 east; the squares west of the player walled: the buffer step
    goes east (the ring's open side), not west."""
    p, z, w, cpos, recs = crawler_world(lua, 10.4, 10.0, 20.95, squares=False)
    grid(lua, solid={(9, y) for y in range(15, 26)})
    gow(lua, p)
    run(lua, p, w, 2)
    assert work_of(lua, "stepFor") == "crawler_buffer" and w["walk"][0] > 0.99


# ---- Plan 36 Task 2 fix 1 (x_trial-ladder-20261111-202744: the -debug client parked at 86.7 s in stepTo,
# "missing argument #1 to 'atan2'": a same-target re-send arrived during the pile's step out; keepState copied the
# step's state and count but not its heading) -----------------------------------------------------------------------

def _no_raise(lua, fs):
    fails = [a for a in acts(lua, fs) if a["state"] == "failed" and a["reason"] != "superseded"]   # a re-send's
    assert fails == [] and lua.eval("PZA.skills.errors or 0") == 0, fails


def test_a_same_target_re_send_during_the_step_out_keeps_its_heading(lua, fs):
    """The run's shape: the pile's step out running (three at point blank, the withdraw east), the planner re-sends
    the melee at the same target with the withdraw turned north (resend inputs): the step out goes on along its own
    heading, no raise (before the fix the next tick's stepTo read a nil heading and the runner failed it)."""
    p, z, w = pile_world(lua, (0.5, 0.5), tx=10.5, attackers=2)
    gow(lua, p, pile=True, withdrawX=1.0, withdrawY=0.0)
    run(lua, p, w, 3)
    assert work_of(lua, "pileState") == "step"
    hx = work_of(lua, "outHx")
    gow(lua, p, aid="m2", pile=True, withdrawX=0.0, withdrawY=1.0)
    run(lua, p, w, 3)
    _no_raise(lua, fs)
    assert work_of(lua, "outHx") == hx and step_seq(lua, fs, "m2")[0] == "work"


@pytest.mark.parametrize("hx, hy", [("nil", "nil"), ("0 / 0", "1"), ("1", "nil"), ("1 / 0", "0")])
def test_step_to_with_no_finite_heading_steps_nowhere_and_names_it(lua, fs, hx, hy):
    """stepTo's own guard: the pile's step state forced onto a nil or non-finite heading: no step (the step ends into
    the press window), no raise, the leaf's nan_heading."""
    p, z, w = pile_world(lua, (0.5, 0.5), tx=10.5, attackers=2, **LOOK_OFF)
    gow(lua, p, pile=True)
    run(lua, p, w, 1)
    lua.execute("local w = PZA.skills.cur.st.work; w.pileState, w.pileTicks, w.outHx, w.outHy = 'step', 0, %s, %s"
                % (hx, hy))
    run(lua, p, w, 1)
    _no_raise(lua, fs)
    assert work_of(lua, "pileState") != "step"
    assert any((a["result"].get("work") or {}).get("nan_heading") for a in progress(lua, fs))


def test_a_crawler_buffer_with_no_open_side_stomps_a_biting_crawler(lua, fs):
    """Fix 1: the crawler at 0.5 north (inside its bite) and the standing target at 0.6, every side walled: no buffer
    heading, so the crawler is stomped (the re-pin), whatever stands near; no raise."""
    p, z, w, cpos, recs = crawler_world(lua, 10.6, 10.0, 20.5, squares=False, **LOOK_OFF)
    grid(lua, solid={(x, y) for x in range(8, 13) for y in range(18, 23) if (x, y) != (10, 20)})
    gow(lua, p)
    run(lua, p, w, 2)
    _no_raise(lua, fs)
    assert lua.eval("PZA.skills.cur.st.id") == 8


def test_a_crawler_buffer_with_no_open_side_beyond_the_bite_yields(lua, fs):
    """The crawler at 1.6 (beyond its bite), every side walled: no buffer step, the next rule (no raise, no re-pin)."""
    p, z, w, cpos, recs = crawler_world(lua, 11.3, 10.0, 21.6, squares=False, **LOOK_OFF)
    grid(lua, solid={(x, y) for x in range(8, 13) for y in range(18, 23) if (x, y) != (10, 20)})
    gow(lua, p)
    run(lua, p, w, 2)
    _no_raise(lua, fs)
    assert lua.eval("PZA.skills.cur.st.id") == 7
    assert "crawler_buffer" not in [(a["result"].get("work") or {}).get("step_for") for a in progress(lua, fs)]
