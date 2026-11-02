"""Survival 19 (survival iteration 17; Plan 26 Task 2; E16, `e_day_16-20261102-125450`, F7,
`f_goals_8-20261102-093241`, and F5, `f_goals_6-20261030-192251`; rows #4453, #4499-#4511). The fake mod over
PZA/1.7.1, on E16's building 1 as its kept map read it at line 469 (the guide's § 3: the six `garagestorage` room
squares x 10710..10711 by y 10595..10597, the door on the west edge of the outdoor square (10712, 10596), the window on
the west edge of the room square (10710, 10596), the strip x 10709 fenced on its west edges, blocked and hoppable).

- P26-A, the window way out (`WINDOW_EXIT`): a building's windows are ways out after its doors and openings
  (`night.window_exits`, `policies.exit_plan`); the Flee walks to the window's inside square and sends `Window(x, y,
  smash)` once, reads the climb's end (`done` and the frame outside: `left`; any failure: the window's failure noted
  and the exit refused); `exit_kind` answers "window". E16's `inside` end read `trapped` with both zombies on the door's
  inside square and the window 2.3458507024507074 tiles from the nearest of them.
"""
import math

from agent.base.planner import flee as FL
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.pza1 import Window

from .test_night import CLOSED, OPEN
from .test_policies import Rig, grid
from .test_survive import last, make, threat_why, tick

LOCKED_W = {"open": False, "locked": True, "barricaded": False}
SHUT_W = {"open": False, "locked": False, "barricaded": False}   # the window's record from seq 3632 to the log's end
BARRED_W = {"open": False, "locked": False, "barricaded": True}
ROOMS = [(x, y) for x in (10710, 10711) for y in (10595, 10596, 10597)]
WIN = (10710, 10596, 0)     # the window square: its record on its own west edge (the `Window` action's (x, y))
WIN_OUT = (10709, 10596, 0)   # the outdoor square west of it, the climb's landing
DOOR = (10712, 10596, 0)    # the door, kept on the outdoor square's west edge
ME = (10711.6396484375, 10596.466796875)   # line 469's frame (seq 4222), on the door's inside square (10711, 10596)
# line 469's frame: 24164 and 24134 on the door's inside square, 24125 on (10713, 10595), 24160 and 24161 east
E16_469 = [(24164, 10711.8427734375, 10596.3798828125), (24134, 10711.9921875, 10596.849609375),
           (24125, 10713.73046875, 10595.2919921875), (24160, 10714.556640625, 10598.79296875),
           (24161, 10716.033203125, 10600.5)]


def zs(rows, me):
    """Zombie records (standing, chasing) for `(id, x, y)` rows, `dist` from `me`."""
    return [{"id": zid, "x": x, "y": y, "dist": math.hypot(x - me[0], y - me[1]), "hasTarget": True,
             "crawler": False, "health": 1.0, "onFloor": None} for zid, x, y in rows]


def shed(door=OPEN, window=SHUT_W, north_door=None):
    """E16's building 1 (the module docstring): every edge of the six room squares blocked but the door's (open: the
    stand's open a98) and the window's (a shut window blocks its edge); the strip x 10709 fenced; open ground x 10705 to
    10716 by y 10592 to 10600. `north_door` (a door record) puts a second exterior door on the north edge of the room
    square (10711, 10595)."""
    at = {}
    for x, y in ROOMS:
        at[(x, y)] = {"room": "garagestorage", "building": 1, "blockN": y == 10595, "edgeN": y == 10595,
                      "blockW": x == 10710, "edgeW": x == 10710}
    at[WIN[:2]]["window"] = dict(window)
    if north_door is not None:
        at[(10711, 10595)].update(door=dict(north_door), blockN=not north_door["open"])
    for y in (10595, 10596, 10597):   # the east wall, kept on x 10712's west edges; the door's edge open with the door
        at[(10712, y)] = {"edgeW": True, "blockW": not (y == 10596 and door["open"])}
    at[DOOR[:2]]["door"] = dict(door)
    for x in (10710, 10711):          # the south wall, kept on y 10598's north edges
        at[(x, 10598)] = {"edgeN": True, "blockN": True}
    for y in range(10592, 10601):     # the fence west of the window: blocked, hoppable
        at[(10709, y)] = {"edgeW": True, "blockW": True, "hopW": True}
    return grid(10705, 10716, 10592, 10600, at)


def e16_rig(tmp_path, window=SHUT_W, rows=E16_469, me=ME, **shed_k):
    r = Rig(tmp_path)
    r.scan(shed(window=window, **shed_k))
    r.frame(x=me[0], y=me[1], zombies=zs(rows, me))
    return r


# ================================================================ P26-A: the window way out
def test_the_e16_shed_reads_one_window_and_its_open_door_s_opening(tmp_path):
    """The map of the guide's § 3 as the World reads it: one window square, its pair (the room square it is kept on,
    the outdoor square west of it), and the open door's step as the one opening."""
    r = e16_rig(tmp_path)
    assert r.world.windows(1) == [WIN]
    assert r.world.window_way(WIN, 1) == (WIN, WIN_OUT)
    assert r.world.openings(1) == [((10711, 10596, 0), DOOR)]


def test_e16_s_inside_end_has_the_window_for_its_way_out_and_none_with_the_switch_off(tmp_path):
    """E16's line 469: the door's opening refused (24164 and 24134 within EXIT_CLEAR_R of its outside square's centre),
    the window's outside square's centre 2.3458507024507074 tiles from 24164; `exit_plan` answers the window (its
    inside square the walk's target, `smash` false for a shut unlocked one), `exit_kind` "window"; with windows off
    (`WINDOW_EXIT` off) no way out, as E16 read it (`trapped`)."""
    r = e16_rig(tmp_path)
    ts = list(r.world.zombies.values())
    c = P.centre(WIN_OUT)
    assert math.hypot(r.world.zombies[24164]["x"] - c[0], r.world.zombies[24164]["y"] - c[1]) == 2.3458507024507074
    e = P.exit_plan(r.world, ts, windows=True)
    assert (e["window"], e["inner"], e["outer"], e["door"], e["smash"]) == (WIN, WIN, WIN_OUT, None, False)
    assert (e["building"], e["step"], e["target"], e["sent"]) == (1, "window", WIN, False)
    assert P.exit_kind(r.world, e) == "window"
    assert P.exit_plan(r.world, ts) is None


def test_a_locked_window_is_a_way_out_to_smash(tmp_path):
    r = e16_rig(tmp_path, window=LOCKED_W)
    assert P.exit_plan(r.world, list(r.world.zombies.values()), windows=True)["smash"] is True


def test_a_barricaded_or_dead_window_and_a_build_without_the_window_are_no_way_out(tmp_path):
    for name, window, fail, caps in (("barred", BARRED_W, None, None), ("dead", SHUT_W, "not valid", None),
                                     ("caps", SHUT_W, None, ("walkTo", "attack"))):
        d = tmp_path / name
        d.mkdir()
        r = Rig(d, caps=caps)
        r.scan(shed(window=window))
        r.frame(x=ME[0], y=ME[1], zombies=zs(E16_469, ME))
        if fail is not None:
            r.world.note_window_fail(WIN, fail)
        assert P.exit_plan(r.world, list(r.world.zombies.values()), windows=True) is None, name


def test_a_door_that_passes_goes_before_a_nearer_window(tmp_path):
    """The rank: a window is the way out only when no door or opening passes. On the window's own square, one zombie
    north of the shed: the door's opening (2.0 tiles off) passes and goes, never the window (1.0 tile off)."""
    me = (10710.5, 10596.5)
    r = e16_rig(tmp_path, rows=[(1, 10711.5, 10590.5)], me=me)
    e = P.exit_plan(r.world, list(r.world.zombies.values()), windows=True)
    assert e.get("window") is None and (e["inner"], e["outer"], e["step"]) == ((10711, 10596, 0), DOOR, "walk")
    assert P.exit_kind(r.world, e) == "door"


def flee_on(r):
    f = FL.Flee(r.world, r.acts, r.clock)
    f.threats = list(r.world.zombies.values())
    return f


def test_the_flee_walks_to_the_window_s_inside_square_then_sends_the_climb_once(tmp_path):
    """E16's line 469 geometry: the Flee's choose takes the window, walks at a run to the centre of its inside square
    (10710.5, 10596.5) from the door's inside square, then sends `Window(10710, 10596, smash=False)` once, logged
    {exit, outer, window, smash, step}; while the climb runs nothing more."""
    r = e16_rig(tmp_path)
    f = flee_on(r)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 10710.5, "y": 10596.5, "gait": "run"})
    w = f.why
    assert (w["exit"], w["outer"], w["window"]) == (1, [10709, 10596, 0], [10710, 10596])
    assert w["smash"] is False and w["step"] == "window"
    r.answer()
    me = (10710.5, 10596.5)
    r.frame(x=me[0], y=me[1], zombies=zs(E16_469, me))
    f.step()
    assert r.cmd() == ("window", {"x": 10710, "y": 10596})   # `smash` false: the bool's default, left off the wire
    assert f.exit["sent"] is True and P.exit_kind(r.world, f.exit) == "window"
    r.fake.answer({"window": ["accepted"]})
    r.pump()
    r.frame(x=me[0], y=me[1], zombies=zs(E16_469, me))
    assert f.step() is None and sum(1 for a in r.acts.history if a.type == "window") == 1


def test_a_climb_done_with_the_frame_outside_leaves_the_building_and_the_flee_steers(tmp_path):
    r = e16_rig(tmp_path, me=(10710.5, 10596.5))
    f = flee_on(r)
    f.step()
    assert r.cmd()[0] == "window"
    r.answer()
    out = (10709.5, 10596.5)
    r.frame(x=out[0], y=out[1], zombies=zs(E16_469, out))
    f.step()
    assert f.exit is None and f.left == {1} and r.cmd()[0] == "steer"


def test_a_climb_done_with_the_frame_still_inside_refuses_the_window(tmp_path):
    r = e16_rig(tmp_path, me=(10710.5, 10596.5))
    f = flee_on(r)
    f.step()
    r.answer()
    r.frame(x=10710.5, y=10596.5, zombies=zs(E16_469, (10710.5, 10596.5)))
    f.step()
    assert WIN_OUT in f.refused and f.exit is None and f.why["trapped"] == 1


def test_a_climb_that_fails_notes_the_window_and_refuses_it_the_next_choose_holds_trapped(tmp_path):
    """A `Window` ended `rejected` "not valid" (one of `goals.WINDOW_DEAD`): the World notes the window's failure
    (`window_fail`), its outside square refused for the episode; the next choose has no way out (the door's opening
    refused for the zombies on its square, the adoption dropped): the trapped hold."""
    r = e16_rig(tmp_path, me=(10710.5, 10596.5))
    f = flee_on(r)
    f.step()
    r.fake.answer({"window": [{"state": "rejected", "reason": "not valid"}]})
    r.pump()
    r.frame(x=10710.5, y=10596.5, zombies=zs(E16_469, (10710.5, 10596.5)))
    f.step()
    assert r.world.window_fail(WIN) == "not valid" and WIN_OUT in f.refused and f.exit is None
    assert f.why["trapped"] == 1 and f.why["refused"] == [[10709, 10596, 0]] and f.adopted and f.plan is None


def test_a_superseded_climb_is_sent_again(tmp_path):
    r = e16_rig(tmp_path, me=(10710.5, 10596.5))
    f = flee_on(r)
    f.step()
    r.fake.answer({"window": ["accepted", {"state": "failed", "reason": "superseded"}]})
    r.pump()
    r.frame(x=10710.5, y=10596.5, zombies=zs(E16_469, (10710.5, 10596.5)))
    f.step()
    assert [a.type for a in r.acts.history] == ["window", "window"]


def test_e16_s_trapped_group_walks_out_by_the_window_and_with_the_switch_off_holds_trapped(tmp_path):
    """Survive on line 469's frame (no stand running): the group within the hold (`group` hold) on a room square;
    with a way out known (the window) the room is no trap, so the flee walks to the window; off (`WINDOW_EXIT`), the
    trapped hold E16 read."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.WINDOW_EXIT = on
        r.scan(shed())
        r.frame(x=ME[0], y=ME[1], zombies=zs(E16_469, ME), attackers=1)
        tick(r, sv)
        w = threat_why(d)
        if on:
            assert r.cmd() == ("walkTo", {"x": 10710.5, "y": 10596.5, "gait": "run"})
            assert w["window"] == [10710, 10596] and w["step"] == "window" and "trapped" not in w
        else:
            assert w.get("trapped") == 1 and "window" not in w
