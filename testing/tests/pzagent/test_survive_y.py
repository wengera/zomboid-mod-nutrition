"""Survival 19 (survival iteration 17; Plan 26 Task 2; E16, `e_day_16-20261102-125450`, F7,
`f_goals_8-20261102-093241`, and F5, `f_goals_6-20261030-192251`; rows #4453, #4501, #4509-#4511). The fake mod over
PZA/1.7.1, on E16's building 1 as its kept map read it at line 469 (the guide's § 3: the six `garagestorage` room
squares x 10710..10711 by y 10595..10597, the door on the west edge of the outdoor square (10712, 10596), the window on
the west edge of the room square (10710, 10596), the strip x 10709 fenced on its west edges, blocked and hoppable).

- P26-A, the window way out (`WINDOW_EXIT`): a building's windows are ways out after its doors and openings
  (`night.window_exits`, `policies.exit_plan`); the Flee walks to the window's inside square and sends `Window(x, y,
  smash)` once, reads the climb's end (`done` and the frame outside: `left`; any failure: the window's failure noted
  and the exit refused); `exit_kind` answers "window". E16's `inside` end read `trapped` with both zombies on the door's
  inside square and the window 2.3458507024507074 tiles from the nearest of them.
- P26-B, the stand's second way out (`STAND_SECOND_EXIT`): the doorway stand's pick refuses a free door whose building
  has no other way out on its floor (`one_exit`).
- P26-C, the inside corner's shove (`INSIDE_SHOVE`): an `inside` corner with two or more at point blank shoves, never
  swings (E16's a105 to a109), logged `corner` {kind, send, near_n}.
- P26-D, the bleed under the threat branch (`THREAT_BLEED`; F7's lines 1654 to 1680): a fight's tick with nothing in
  reach yields to a dressing, and the `pair` and `held` legs ride the bleed as the `many` leg does; `care_yield`.
- P26-E, the worn wear (`WEAR_WORN`; F5's guide L109): a wear rejected `worn` marks its garment worn.
"""
import math

import pytest

from agent.base.planner import edges as ED
from agent.base.planner import flee as FL
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner.care import FLEE_CARE_S

from agent.base.pza1 import Shove

from .test_night import CLOSED, OPEN
from .test_policies import Rig, grid
from .test_survive import last, make, threat_why, tick
from .test_survive_g import care_frame, hold, part

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


def shed(door=OPEN, window=SHUT_W, north_door=None, extra_windows=()):
    """E16's building 1 (the module docstring): every edge of the six room squares blocked but the door's (open: the
    stand's open a98) and the window's (a shut window blocks its edge); the strip x 10709 fenced; open ground x 10705 to
    10716 by y 10592 to 10600. `north_door` (a door record) puts a second exterior door on the north edge of the room
    square (10711, 10595); `extra_windows` rows `(room square, window record)` more windows on the west edge."""
    at = {}
    for x, y in ROOMS:
        at[(x, y)] = {"room": "garagestorage", "building": 1, "blockN": y == 10595, "edgeN": y == 10595,
                      "blockW": x == 10710, "edgeW": x == 10710}
    at[WIN[:2]]["window"] = dict(window)
    for sq, rec in extra_windows:
        at[sq]["window"] = dict(rec)
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


def test_the_iteration_17_switches_and_constants():
    assert S.T7_SWITCHES == ("WINDOW_EXIT", "STAND_SECOND_EXIT", "INSIDE_SHOVE", "THREAT_BLEED", "WEAR_WORN")
    assert all(getattr(S.Survive, name) is True for name in S.T7_SWITCHES)
    assert "T7_SWITCHES" in S.__all__ and P.INSIDE_CROWD_N == 2


def test_edges_crossed_is_the_public_name_of_the_frozen_grades_crossed():
    assert ED.crossed is ED._crossed and "crossed" in ED.__all__


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


def test_an_unlocked_window_goes_before_a_nearer_locked_one(tmp_path):
    """Ruling P26-7d: on line 469's frame two windows pass, the nearer (10710, 10596) locked (a smash) and a farther
    shut one one square south (10710, 10597): the farther unlocked one is the way out, as `goals.window_pick` ranks
    (no noise, no cut); with both unlocked the nearer goes."""
    south = (10710, 10597)
    r = e16_rig(tmp_path, window=LOCKED_W, extra_windows=((south, SHUT_W),))
    e = P.exit_plan(r.world, list(r.world.zombies.values()), windows=True)
    assert (e["window"], e["smash"]) == (south + (0,), False)
    d = tmp_path / "both"
    d.mkdir()
    r = e16_rig(d, extra_windows=((south, SHUT_W),))
    e = P.exit_plan(r.world, list(r.world.zombies.values()), windows=True)
    assert (e["window"], e["smash"]) == (WIN, False)


def test_the_window_filter_and_the_failure_leg_are_the_goal_layer_s_for_both_callers(tmp_path):
    """Ruling P26-7c: `windows.usable_windows` (the one filter of `window_pick` and `night.window_exits`) reads the
    record's `locked` or a try that ended `locked`, and leaves out a barricaded window and a dead one;
    `windows.note_window_end` (the one failure leg) notes an unsmashed `locked` end `locked`, a smash's or a second
    `locked` `failed`, a second WINDOW_REPEAT end `failed`."""
    from agent.base.actions import Action
    from agent.base.planner import windows as WN
    r = e16_rig(tmp_path)
    assert WN.usable_windows(r.world, 1, 0) == [(WIN, False)] and WN.usable_windows(r.world, 1, 1) == []
    ends = [Action(aid="a%d" % i, type="window", args=args, deadline_s=30.0, sent_wall=0.0, state=state, reason=reason)
            for i, (args, state, reason) in enumerate((({"x": 10710, "y": 10596}, "rejected", "locked"),
                                                       ({"x": 10710, "y": 10596, "smash": True}, "rejected", "locked"),
                                                       ({"x": 10710, "y": 10596}, "failed", "no path")))]
    assert WN.note_window_end(r.world, WIN, ends[0]) == "locked" and r.world.window_fail(WIN) == "locked"
    assert WN.usable_windows(r.world, 1, 0) == [(WIN, True)]
    assert WN.note_window_end(r.world, WIN, ends[0]) == "failed" and WN.usable_windows(r.world, 1, 0) == []
    r2 = e16_rig(tmp_path / "smash")
    assert WN.note_window_end(r2.world, WIN, ends[1]) == "failed"
    r3 = e16_rig(tmp_path / "repeat")
    assert [WN.note_window_end(r3.world, WIN, ends[2]) for _ in range(2)] == ["no path", "failed"]


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
    """A `Window` ended `rejected` "not valid" (one of `windows.WINDOW_DEAD`): the World notes the window's failure
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


def test_a_window_refused_locked_unsmashed_is_offered_again_as_a_smash_and_a_refused_smash_is_refused(tmp_path):
    """Ruling P26-7c: the shut window's open (`Window` without `smash`) ended `rejected` `locked`: the World notes the
    window `locked` and the exit ends with its outside square not refused, so the next choose walks nothing (the player
    stands on the inside square) and sends `Window(10710, 10596, smash=True)`; that smash ended `rejected` `locked`
    again is a dead window: the exit refused, the trapped hold."""
    r = e16_rig(tmp_path, me=(10710.5, 10596.5))
    f = flee_on(r)
    f.step()
    assert r.cmd() == ("window", {"x": 10710, "y": 10596})
    r.fake.answer({"window": [{"state": "rejected", "reason": "locked"}]})
    r.pump()
    r.frame(x=10710.5, y=10596.5, zombies=zs(E16_469, (10710.5, 10596.5)))
    f.step()
    assert r.world.window_fail(WIN) == "locked" and WIN_OUT not in f.refused
    assert r.cmd() == ("window", {"x": 10710, "y": 10596, "smash": True}) and f.exit["smash"] is True
    assert [a.type for a in r.acts.history] == ["window", "window"]
    r.fake.answer({"window": [{"state": "rejected", "reason": "locked"}]})
    r.pump()
    r.frame(x=10710.5, y=10596.5, zombies=zs(E16_469, (10710.5, 10596.5)))
    f.step()
    assert r.world.window_fail(WIN) == "failed" and WIN_OUT in f.refused and f.exit is None
    assert [a.type for a in r.acts.history] == ["window", "window"] and f.why["trapped"] == 1


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


# ================================================================ P26-B: the stand's second way out
EAST = [(1, 10718.5, 10596.5), (2, 10719.0, 10599.0), (3, 10719.0, 10594.0)]   # three east of the shed, within DANGER_R


def pick_line(tmp_path, window_exit=True, second_exit=True, **shed_k):
    """E16's line 440 (the `many` flee's pick from outside, the door closed): the player on open ground two tiles east
    of the door, three zombies east of it within DANGER_R; one tick: (r, sv, the threat why)."""
    r, sv = make(tmp_path)
    sv.WINDOW_EXIT, sv.STAND_SECOND_EXIT = window_exit, second_exit
    r.scan(shed(door=CLOSED, **shed_k))
    me = (10714.5, 10596.5)
    r.frame(x=me[0], y=me[1], zombies=zs(EAST, me))
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "many"
    return r, sv, w


def test_the_shed_with_its_window_has_a_second_way_out_and_its_door_is_taken_for_the_stand(tmp_path):
    """A one-door building with a window (E16's shed as its map read it, the window a way out by P26-A): `ok`, the stand
    plan made at its door."""
    r, sv, w = pick_line(tmp_path)
    assert w["doorway_pick"] == "ok" and sv.flee.plan["stand"] is True and sv.flee.plan["doors"] == [DOOR]
    assert "doorway_one_exit" not in w


def test_a_one_door_shed_with_no_usable_window_is_refused_one_exit_and_no_plan_is_made(tmp_path):
    """The shed's window barricaded (no way out by P26-A), or windows no way out at all (`WINDOW_EXIT` off, as E16 ran):
    its one door is refused `one_exit`, the Flee picks nothing (the open-ground flee) and the line says why."""
    for name, k in (("barred", {"window": BARRED_W}), ("windows_off", {"window_exit": False})):
        d = tmp_path / name
        d.mkdir()
        r, sv, w = pick_line(d, **k)
        assert w["doorway_pick"] == "one_exit" and sv.flee.plan is None and not sv.flee.picked, name
        assert [v[3] for v in sv.flee.door_verdicts(sv.flee._threats())] == ["one_exit"]
        assert w["doorway_one_exit"] == {"building": 1, "door": [DOOR[0], DOOR[1]]}, name   # the refused building


def test_a_two_door_building_stands_and_the_switch_off_stands_in_the_one_door_shed(tmp_path):
    """A second exterior door on the shed's north wall (its window barricaded): `ok`. With `STAND_SECOND_EXIT` off the
    one-door shed stands as before."""
    for name, k in (("two_doors", {"window": BARRED_W, "north_door": CLOSED}),
                    ("off", {"window": BARRED_W, "second_exit": False})):
        d = tmp_path / name
        d.mkdir()
        r, sv, w = pick_line(d, **k)
        assert w["doorway_pick"] == "ok" and sv.flee.plan["stand"] is True, name
        assert "doorway_one_exit" not in w, name


def test_a_shelter_pick_that_is_no_stand_keeps_the_one_door_shed(tmp_path):
    """The rule reads the stand's pick only (`stand_ok`): a flee whose pick is a plain shelter (closed behind it) may
    take a one-door building."""
    r = Rig(tmp_path)
    r.scan(shed(door=CLOSED, window=BARRED_W))
    me = (10714.5, 10596.5)
    r.frame(x=me[0], y=me[1], zombies=zs(EAST, me))
    f = flee_on(r)
    assert [v[3] for v in f.door_verdicts(f.threats)] == ["ok"]
    f.stand_ok = True
    assert [v[3] for v in f.door_verdicts(f.threats)] == ["one_exit"]


def stand_on_shed(tmp_path, window_exit=True, crowd=False):
    """E16's stand on the shed, run through the shelter steps (the closed door, the approach square, the open, the walk
    to the post (10710, 10596)) with the stand's aim sent; then line 469's frame (the player on the door's inside
    square, 24164 and 24134 on it, `me.attackers` 1) ticked with `WINDOW_EXIT` as given: (r, sv, the threat why).
    Named change, ruling P26-K (Plan 26 Task 7): line 469's five within DANGER_R end the stand `crowd` ahead of
    `inside`, so the stand runs with `STAND_CROWD` off (`crowd` False) unless asked, its `inside` end the one read."""
    r, sv, _ = pick_line(tmp_path)
    sv.STAND_CROWD = crowd
    r.answer()
    approach = (DOOR[0] + 0.5, DOOR[1] + 0.5)
    r.frame(x=approach[0], y=approach[1], zombies=zs(EAST, approach))
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "open"
    r.answer()
    r.scan(shed(door=OPEN))
    r.frame(x=approach[0], y=approach[1], zombies=zs(EAST, approach))
    tick(r, sv)
    post = (10710.5, 10596.5)
    assert r.cmd() == ("walkTo", {"x": post[0], "y": post[1], "gait": "run"})
    r.answer()
    r.frame(x=post[0], y=post[1], zombies=zs(EAST, post))
    assert tick(r, sv).type == "aim" and sv.flee.plan["step"] == "stand" and sv.flee.plan["post"] == WIN
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    sv.WINDOW_EXIT = window_exit
    r.frame(x=ME[0], y=ME[1], zombies=zs(E16_469, ME), attackers=1)
    tick(r, sv)
    return r, sv, threat_why(tmp_path)


def test_the_stand_s_inside_end_walks_out_by_the_window_and_with_windows_off_holds_trapped(tmp_path):
    """E16's `inside` end on line 469's frame (24164 and 24134 on the door's inside square, the stand at the post
    (10710, 10596)): the stand ends `inside` and, the door's way out taken, walks out by the window (the walk to the
    centre of its square, `doorway_exit` {end inside, exit window}); with windows off (`WINDOW_EXIT`, as E16 ran) the
    end reads `trapped`."""
    r, sv, w = stand_on_shed(tmp_path)
    assert w["doorway_left"] == "inside" and w["doorway_exit"] == {"end": "inside", "exit": "window"}
    assert r.cmd() == ("walkTo", {"x": 10710.5, "y": 10596.5, "gait": "run"})
    assert w["window"] == [10710, 10596] and w["flee"] == "doorway" and sv.flee.walking_out == "inside"
    d = tmp_path / "off"
    d.mkdir()
    r, sv, w = stand_on_shed(d, window_exit=False)
    assert w["doorway_left"] == "inside" and w["doorway_exit"] == {"end": "inside", "exit": "trapped"}
    assert w["trapped"] == 1 and "window" not in w


# ================================================================ P26-C: the inside corner's shove
# the corner's attacks from E16's `inside` end: (me, zombies within 1.5 tiles but the third of line 478, 1.63 tiles off,
# left out so no group reads), each line's frame
E16_478 = ((10711.677734375, 10596.525390625),   # a109's line: two within POINT_BLANK_R (0.3875, 0.4582)
           [(24160, 10711.771484375, 10596.1494140625), (24134, 10712.12890625, 10596.60546875)])
E16_470 = ((10711.4208984375, 10596.5126953125),   # a105's line: one within it (0.4976), the second at 1.0273
           [(24134, 10711.8720703125, 10596.72265625), (24164, 10712.4013671875, 10596.2060546875)])


def corner_tick(tmp_path, line, inside_shove=True, floor=(), attackers=1):
    """A Survive on the shed, the player on the door's inside square with `line`'s zombies (`floor`: the ids lying
    on the floor): one tick, the `inside` corner's Fight. (r, sv, the threat why). Named change, ruling P27-G (Plan 27
    Task 5): `FLOOR_FINISH` off (P24-AL's stomp of the fallen first, the module's pin, is the rule before it)."""
    me, rows = line
    r, sv = make(tmp_path)
    sv.INSIDE_SHOVE = inside_shove
    sv.FLOOR_FINISH = False
    r.scan(shed())
    zombies = [dict(z, onFloor=True) if z["id"] in floor else z for z in zs(rows, me)]
    r.frame(x=me[0], y=me[1], zombies=zombies, attackers=attackers)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["corner_kind"] == "inside"
    return r, sv, w


def test_two_at_point_blank_in_the_inside_corner_are_shoved_never_swung_at(tmp_path):
    """E16's a109 geometry: 24160 at 0.3875 and 24134 at 0.4582 tiles, both on the door's inside square: the corner
    shoves its target (the nearest) in place of E16's attack, logged `corner` {kind inside, send shove, near_n 2}."""
    r, sv, w = corner_tick(tmp_path, E16_478)
    assert r.cmd() == ("shove", {"targetId": 24160}) and w["shove"] == "crowd"
    assert w["corner"] == {"kind": "inside", "send": "shove", "near_n": 2}


def test_one_at_point_blank_keeps_the_swing(tmp_path):
    """E16's a105 geometry: 24134 at 0.4976, 24164 at 1.0273 (beyond POINT_BLANK_R), `me.attackers` 1: the attack
    stands, logged with its count."""
    r, sv, w = corner_tick(tmp_path, E16_470)
    assert r.cmd() == ("attack", {"targetId": 24134}) and "shove" not in w
    assert w["corner"] == {"kind": "inside", "send": "attack", "near_n": 1}


def test_the_crowd_s_shove_is_sent_only_to_a_wire_id_within_the_shove_s_reach(tmp_path):
    """Ruling P26-7a: the corner's Fight (a109's two at point blank, so a crowd of 2) keeps a pinned target while
    another zombie holds the corner, and `me.attackers` alone may make the crowd (`_inside_crowd`), so its target may
    stand anywhere to FIGHT_REACH. At 1.7 tiles (beyond the Lua's SHOVE_R 1.5, which refuses a shove `too far`, and a
    SWING_SKIP_S cool-down before the swing) `_crowd_shove` answers None and the swing stands; at SHOVE_R it shoves;
    never at a target whose id is no int (a nil read keys None)."""
    r, sv, w = corner_tick(tmp_path, E16_478)
    f = sv.fight
    assert f.crowd == 2 and w["shove"] == "crowd"
    f.why = {}
    assert f._crowd_shove(24160, 1.7) is None and "shove" not in f.why
    assert f._crowd_shove(24160, P.SHOVE_R) == Shove(24160) and f.why["shove"] == "crowd"
    assert f._crowd_shove(True, 1.0) is None and f._crowd_shove(None, 1.0) is None


def test_attackers_count_toward_the_crowd_and_no_other_corner_reads_one(tmp_path):
    """The count is the zombies within POINT_BLANK_R or the frame's `me.attackers`, the greater (two attackers with one
    listed at point blank read two); a corner of another kind, the switch off or a build without the shove reads
    none."""
    me, rows = E16_470
    r, sv = make(tmp_path)
    r.scan(shed())
    r.frame(x=me[0], y=me[1], zombies=zs(rows, me), attackers=2)
    sv.corner_kind = "inside"
    assert sv._inside_crowd() == 2
    sv.corner_kind = "stuck"
    assert sv._inside_crowd() is None
    sv.corner_kind, sv.INSIDE_SHOVE = "inside", False
    assert sv._inside_crowd() is None


def test_a_fallen_one_in_reach_is_stomped_first(tmp_path):
    """Both of a109's zombies on the floor: the finish names the nearest, so the stomp goes before any shove, logged
    `corner` {kind inside, send stomp, near_n 2}. With a standing one at point blank beside the fallen, the finish's own
    order shoves the standing one first (P24-AL's `shove` "first"), the send logged a shove."""
    r, sv, w = corner_tick(tmp_path, E16_478, floor=(24160, 24134))
    assert r.cmd() == ("stomp", {"targetId": 24160})
    assert w["corner"] == {"kind": "inside", "send": "stomp", "near_n": 2}
    d = tmp_path / "standing"
    d.mkdir()
    r, sv, w = corner_tick(d, E16_478, floor=(24134,))
    assert r.cmd() == ("shove", {"targetId": 24160}) and w["shove"] == "first" and w["corner"]["send"] == "shove"


def test_with_the_switch_off_the_inside_corner_swings_at_two_as_e16_did(tmp_path):
    r, sv, w = corner_tick(tmp_path, E16_478, inside_shove=False)
    assert r.cmd() == ("attack", {"targetId": 24160}) and "corner" not in w


# ================================================================ P26-D: the bleed under the threat branch
# F7's line 1660 (seq 18310): the `held` flee's steer leg running from 14192 (5.218586445147157 tiles, chasing) and
# 14190 (8.611335877250424), part 2 bleeding since the bite at seq 18234
F7_1660 = ((10809.80078125, 10676.4365234375),
           [(14192, 10806.0029296875, 10672.857421875), (14190, 10803.58984375, 10670.4716796875)])
F7_1655 = (10805.5654296875, 10672.421875)   # line 1655's position, where the `pair` flee's steer went
PART2 = part(2, h=77.04804229736328, bleeding=True, bleedingTime=8.344533920288086, infected=True)


def bleed_flee(tmp_path, bleed=True, kind="pair", at_1660=True):
    """A clean rag held, part 2 bleeding: the `pair` flee from 14192 at 1.8 tiles (within FIGHT_REACH, beyond
    CORNERED_R) and 14190 (line 1655's), its steer sent and running. For `kind` "held" a second tick follows (F7's
    line 1658: 14192 at 2.5 tiles, within RIDE_MANY_R, so no ride, and 14190 held beyond DANGER_R): the flee goes on as
    `held` (the Fight's line not taken on one chaser held with another listed behind it). Then F7's line 1660 frame,
    ticked (the last decision's `flee_reason` the leg's kind), unless `at_1660` is False (the `held` flee's second tick
    the last)."""
    r, sv = make(tmp_path)
    sv.THREAT_BLEED = bleed
    hold(r, 10, "Base.RippedSheets")
    me0 = F7_1655
    care_frame(r, [PART2], x=me0[0], y=me0[1],
               zombies=zs([(14192, me0[0] - 1.8, me0[1]), (14190, 10801.361328125, 10668.34765625)], me0))
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "pair" and r.cmd()[0] == "steer"
    r.answer("progress")
    if kind == "held":
        care_frame(r, [PART2], x=me0[0], y=me0[1],
                   zombies=zs([(14192, me0[0] - 2.5, me0[1]), (14190, me0[0] - 8.0, me0[1] - 3.0)], me0))
        tick(r, sv)
        assert threat_why(tmp_path)["flee"] == "held" and sv.flee_reason == "held"
        assert not any(a.type == "bandage" for a in r.acts.history)
        r.answer("progress")
    if not at_1660:
        return r, sv
    me, rows = F7_1660
    care_frame(r, [PART2], x=me[0], y=me[1], zombies=zs(rows, me))
    tick(r, sv)
    return r, sv


@pytest.mark.parametrize("kind", ["pair", "held"])
def test_f7_s_line_1660_rides_the_bandage_on_the_pair_and_held_flee_s_leg(tmp_path, kind):
    """F7 line 1660's geometry with a dressing held: the chaser at 5.218586445147157 tiles (under RIDE_R, so P24-U's
    ride was refused) is beyond RIDE_MANY_R, so a `pair` flee's leg (F7's line 1656 to 1658) or a `held` one (its line
    1659 to 1661, the decision line 1660 names) rides the bleed as a `many` leg would: the care sends the rag on part
    2 with keepMoving, logged `care_yield` {why bleed, near}. A bleed leg of `("pair",)` alone fails the `held` case."""
    r, sv = bleed_flee(tmp_path, kind=kind)
    w = threat_why(tmp_path)
    assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 2, "keepMoving": True})
    assert w["care"] is True and w["ride"] is True
    assert w["care_yield"] == {"why": "bleed", "near": P.zdist(r.world, r.world.zombies[14192])}
    assert w["care_yield"]["near"] == pytest.approx(5.218586445147157)


def test_the_bleed_leg_reads_the_distance_rule_alone_never_the_many_episode_s_clock(tmp_path):
    """Ruling P26-7e: a `held` leg with `many_since` set long ago (past FLEE_CARE_S) and two parts bleeding
    (FLEE_CARE_N) does not ride with the nearest within RIDE_MANY_R: `_rides_many`'s clock clause is the `many`
    episode's. At 2.5 tiles from the nearest (F7's line 1658 geometry) the threat branch answers, no bandage."""
    r, sv = bleed_flee(tmp_path, kind="held", at_1660=False)
    sv.many_since = r.clock() - 10 * FLEE_CARE_S
    me = F7_1655
    care_frame(r, [PART2, part(5, h=77.0, bleeding=True, bleedingTime=8.0)], x=me[0], y=me[1],
               zombies=zs([(14192, me[0] - 2.5, me[1]), (14190, me[0] - 8.0, me[1] - 3.0)], me))
    tick(r, sv)
    assert sv.flee_reason == "held" and last(tmp_path)["branch"] == "threat"
    assert not any(a.type == "bandage" for a in r.acts.history)


def test_with_the_switch_off_line_1660_holds_the_threat_branch_as_f7_did(tmp_path):
    r, sv = bleed_flee(tmp_path, bleed=False)
    assert last(tmp_path)["branch"] == "threat" and not any(a.type == "bandage" for a in r.acts.history)


def fight_ticks(tmp_path, dist, items=(("Base.RippedSheets", 10),), bleed=True, ticks=2, stock_early=True):
    """A fresh Survive, `items` held (added after the first frame), part 2 bleeding, one chasing zombie `dist` tiles
    east, closing a tenth of a tile a tick: `ticks` ticks, the first making the Fight (P24-P's closing read refuses
    the yield on every one). `stock_early` is Survive's `STOCK_EARLY` (ruling P27-K1, Plan 27 Task 5)."""
    r, sv = make(tmp_path)
    sv.THREAT_BLEED = bleed
    sv.STOCK_EARLY = stock_early
    r.frame()
    for ft, iid in items:
        hold(r, iid, ft, use="other")
    for k in range(ticks):
        care_frame(r, [PART2], zombies=zs([(1, 100.0 + dist - 0.1 * k, 200.0)], (100.0, 200.0)))
        tick(r, sv)
        if k == 0:
            assert sv.mode == "fight" and last(tmp_path)["branch"] == "threat"
    return r, sv


def test_a_zombie_within_fight_reach_keeps_the_threat_branch(tmp_path):
    """The Fight has a target in reach (1.7 then 1.6 tiles, beyond POINT_BLANK_R): no bandage mid-fight."""
    r, sv = fight_ticks(tmp_path, 1.7)
    assert last(tmp_path)["branch"] == "threat" and not any(a.type == "bandage" for a in r.acts.history)
    assert "care_yield" not in threat_why(tmp_path)


def test_a_closing_chaser_beyond_fight_reach_leaves_room_for_the_bandage(tmp_path, monkeypatch):
    """One chaser closing from 4.5 tiles (P24-P's closing read refuses it): on the Fight's second tick nothing within
    FIGHT_REACH, the nearest beyond POINT_BLANK_R, a dressing held: the bandage (standing), logged `care_yield`; with
    the switch off the threat branch as before.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = fight_ticks(tmp_path, 4.5)
    assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 2})
    assert threat_why(tmp_path)["care_yield"] == {"why": "bleed", "near": pytest.approx(4.4)}
    d = tmp_path / "off"
    d.mkdir()
    r, sv = fight_ticks(d, 4.5, bleed=False)
    assert last(d)["branch"] == "threat" and not any(a.type == "bandage" for a in r.acts.history)


def test_the_bleed_s_room_takes_a_dressing_never_a_rip(tmp_path):
    """F7's own state: no clean dressing held (its rags dirty under DIRTY_RAG_MIN), a cotton garment to rip: the
    bleeding step's send would be the rip (`tends_wound`), which the bleed's yield never takes on a tick P24-P
    refuses. Named change, ruling P27-K1 (Plan 27 Task 5): pinned with `STOCK_EARLY` off (on, the yield takes the
    wound's rip as a dressing: `test_survive_ab`)."""
    r, sv = fight_ticks(tmp_path, 4.5, items=(("Base.Tshirt_WhiteTINT", 11),), stock_early=False)
    assert sv.care.tends_wound() and not sv.care.dresses_wound()
    assert last(tmp_path)["branch"] == "threat" and not any(a.type in ("bandage", "rip") for a in r.acts.history)


# ================================================================ P26-E: the worn wear
JEANS = {"bite": 10, "bullet": 0, "cond": 10, "condMax": 10, "holes": 0, "loc": "base:pants", "scratch": 20}   # F5's


def wear_rig(tmp_path, worn_on=True):
    """F5's a85 geometry (its guide's L109): a PZA/1.7 hello ("1.7", as F5's), the looted `Trousers_JeanBaggy` held
    with its clothing record, the record reading unworn while the character wears them (nothing worn at
    `base:pants` in `me.worn`, so the pick reads a gain), no zombie: the stock's idle tick sends their wear."""
    r, sv = make(tmp_path)
    sv.WEAR_WORN = worn_on
    r.fake.hello(mod="1.7")
    r.pump()
    r.frame(worn=[])
    r.event("item_added", itemId=21, fullType="Base.Trousers_JeanBaggy", weight=0.6, use="clothing",
            clothing=dict(JEANS, worn=False))
    return r, sv


def wears(r):
    return [a for a in r.acts.history if a.type == "wear"]


def refuse_or_answer(r):
    """The running action answered as F5's Lua did: a wear `rejected` `worn`, anything else (the goal's) `done`."""
    cur = r.acts.current
    if cur is not None and cur.type == "wear":
        r.fake.answer({"wear": [{"state": "rejected", "reason": "worn"}]})
        r.pump()
    elif cur is not None:
        r.answer()


def test_a_wear_rejected_worn_marks_the_garment_worn_and_is_never_sent_again(tmp_path):
    """F5: a85, a96, a105, a116 and a124 each re-sent the trousers' wear, each `rejected` `worn`. The first refusal
    marks the record worn (`World.mark_worn`), so over three WEAR_RETRY_MIN spans the stock sends no second wear; off
    (`WEAR_WORN`), the wear goes again each WEAR_RETRY_MIN, as F5's did."""
    from agent.base.planner import care as C
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = wear_rig(d, on)
        tick(r, sv)
        assert r.cmd() == ("wear", {"itemId": 21}) and last(d)["inputs"]["branches"]["care"]["stock"]["item"] == 21
        for k in range(1, 3 * int(C.WEAR_RETRY_MIN)):   # a frame a game minute, past the failed send's cooling too
            refuse_or_answer(r)
            r.frame(worn=[], game_min=480.0 + k)
            tick(r, sv)
        assert len(wears(r)) == (1 if on else 3), on
        assert (r.world.inventory[21].get("worn") is True) is on


def test_the_stock_line_counts_the_marked_garment_it_leaves_out(tmp_path):
    """A second garment (a hat) held after the refusal: its wear goes, the line counting the marked trousers
    (`skipped_worn` 1)."""
    from agent.base.planner import care as C
    r, sv = wear_rig(tmp_path)
    tick(r, sv)
    r.fake.answer({"wear": [{"state": "rejected", "reason": "worn"}]})
    r.pump()
    r.event("item_added", itemId=22, fullType="Base.Hat_BaseballCap", weight=0.1, use="clothing",
            clothing={"bite": 0, "bullet": 0, "cond": 5, "condMax": 5, "holes": 0, "loc": "base:hat", "scratch": 5,
                      "worn": False})
    r.frame(worn=[], game_min=480.0 + C.CARE_RETRY_MIN + 1.0)
    tick(r, sv)
    stock = last(tmp_path)["inputs"]["branches"]["care"]["stock"]
    assert r.cmd() == ("wear", {"itemId": 22}) and stock["skipped_worn"] == 1


def test_f5_s_cause_a_1_7_hello_s_item_changed_marks_the_worn_garment_and_the_pick_leaves_it(tmp_path):
    """F5's own cause, read off its record (the task's report): a6's `item_changed` at seq 654 stated `worn` true, but
    F5's World read the hello's "1.7" as older than PZA/1.5.2 (`item_fields`, the defect ruling P25-O fixed after the
    session), so the item record never took the `worn` the line stated and the pick read the trousers unworn. At HEAD
    the line marks the record worn and the stock sends no wear, the P26-E mark aside."""
    r, sv = wear_rig(tmp_path, worn_on=False)
    assert r.world.item_fields()
    r.event("item_changed", itemId=21, use="clothing", worn=True, clothing=dict(JEANS, worn=True))
    r.frame(worn=[{"loc": "base:pants", "bite": 10, "scratch": 20, "holes": 0, "cond": 10}])
    tick(r, sv)
    assert r.world.inventory[21]["worn"] is True and wears(r) == []
