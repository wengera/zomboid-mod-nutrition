"""Plan 33 Task 3 (the group's entry and the drag guard; F18, `f_goals_18-20261108-235005`: the drag-down death at game
minute 617 under a group of three walked in while the finish stalled): `survive.T18_SWITCHES`' GROUP_LEAVE on
`threat.Threat` (`planner/group.py`), with its replay test on F18's decision lines (`decision.log` over `state.log`, open
loop: `replay_decisions.replay` checks the decisions at the situations the run recorded, never an outcome) and its unit
tests on the fake mod.

- GROUP_LEAVE (`group.ThreatGroup._group_leave`): GROUP_LEAVE_N (3, fix 3) standing zombies closing within
  GROUP_ENTRY_R in the open with nothing at the back within WALL_R, whatever stands in reach (the FIGHT_REACH exception
  dropped), not under FLEE_HEALTH_FLOOR: the Flee's walk to a known door within LEAVE_DOOR_R (the doorway stand there),
  else the fighting retreat (the Fight on the nearest standing zombie, the heading away from the group's centroid the
  reflex's withdraw bias, no run). On F18 it first fires at line 358 (13651, 13648, 13653), the retreat; line 174 is
  withheld by a wall at the back.

Plan 35 Task 8 (the deletion; the reflex owns contact) deleted DRAG_GUARD_FIGHT (the guard's shove in its run's place),
SIDE_CLEAR (the run steer turned off a standing zombie), the leave's first-line shove and the retreat's back legs, with
their tests (named in the task report). Plan 37 Task 3 deleted fix 4's `run` leg above RETREAT_MAX_N with the
constant and its two tests (named in the task report), took GROUP_LEAVE out of T18_SWITCHES (the disposition selector
owns the entry where it runs; GROUP_LEAVE stays `Threat`'s seam, `T17` here naming it) and pins F18's replay, whose
hello announces `melee`, with DISPOSITION off (a named change: the leave is the row where the selector does not run).
"""
import functools
import json
import math
import os

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import fight as F
from agent.base.planner import group as G
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_night import CLOSED, two_door_house
from .test_policies import Rig, square, zombie
from .test_survive import make, threat_why, tick

F18 = os.path.join(R.ARTIFACTS, "f_goals_18-20261108-235005")
T17 = S.T18_SWITCHES + ("GROUP_LEAVE",)   # Plan 37 Task 3: the leave's seam, out of T18_SWITCHES


@functools.lru_cache(maxsize=8)
def _f18(switches):
    """F18 replayed (every line) with `switches` ((name, value) pairs) set on the fresh Survive, as JSON."""
    if not os.path.isfile(os.path.join(F18, "state.log")):
        pytest.skip("%s is not checked out" % F18)

    def mutate(sv):
        for name, v in switches:
            setattr(sv, name, v)
    return json.dumps(R.replay(F18, mutate=mutate))


def f18(**switches):
    """F18's replayed decision lines (list index line - 1) with `switches` set."""
    return json.loads(_f18(tuple(sorted(switches.items()))))


def only(*names):
    """The T17 switches all off but `names`."""
    return {k: k in names for k in T17}


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def action(row):
    return (row.get("action") or {}).get("type")


def test_the_t17_switches_and_constants():
    """`survive.T18_SWITCHES`, empty since Plan 37 Task 3 (Plan 35 Task 8 deleted DRAG_GUARD_FIGHT and SIDE_CLEAR with
    their constants; Plan 37 Task 3 took GROUP_LEAVE out, on by default as `Threat`'s seam, and deleted RETREAT_MAX_N),
    and the constants at `policies.py`'s end."""
    assert S.T18_SWITCHES == () and T17 == ("GROUP_LEAVE",)
    assert all(getattr(S.Survive, k) is True for k in T17)
    assert not any(hasattr(S.Survive, k) for k in ("DRAG_GUARD_FIGHT", "SIDE_CLEAR"))
    assert P.WALL_R == 1.5
    assert not any(hasattr(P, k) for k in ("STUCK_FRAMES", "SIDE_R", "SIDE_LOOK", "STUCK_FREE_R",
                                           "DRAG_SHOVES_PER_EPISODE", "RETREAT_RESEND_DEG"))
    assert not hasattr(P, "LEAVE_R") and not hasattr(P, "LEAVE_S")   # fix 4: unused since fix 3, deleted
    assert not hasattr(P, "RETREAT_MAX_N")   # fix 4's, deleted at Plan 37 Task 3
    assert P.GROUP_ENTRY_R == P.DANGER_R == 6.0   # fix 1: DANGER_R's value, its own constant


def rig(tmp_path, zombies, on=(), x=100.5, y=200.5, **frame):
    """A Survive on a fresh Rig with the T17 switches in `on` set on and the others off, one frame."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name in on)
    r.frame(x=x, y=y, zombies=zombies, **frame)
    return r, sv


def z(zid, x, y, me=(100.5, 200.5), **k):
    return dict(zombie(zid, x, y, me=me), **k)


# ================================================================ the drag pile
def guard(on, hit="Bite"):
    """Three standing round the player at (100.5, 200.5) facing +x: 2 behind it at 0.55, 1 in front at 0.6, 3 beside
    at 0.7; the frame reads two attackers (the guard's DRAG_DOWN_N - 1)."""
    return dict(zombies=[z(1, 101.1, 200.5), z(2, 99.95, 200.5), z(3, 100.5, 201.2)], attackers=2,
                hit_reaction=hit, on=on)


# ================================================================ GROUP_LEAVE
WEST = ((96.9, 200.6), (97.0, 199.9), (100.5, 210.4))   # the trio's first line: 3.6 and 3.55 tiles west and 9.9 south of (100.5, 200.5) (the third beyond ENGAGE_R inside DISENGAGE_R and not behind the pair, so the pair is fought and no flee runs before the leave)
NEAR = ((97.6, 200.7), (97.65, 199.95), (100.5, 206.3))   # the next: 2.91, 2.90 and 5.8, all closing within GROUP_ENTRY_R


def pair(at, **k):
    """The zombies of a line, ids 1, 2, 3 (a pair when `at` holds two: Plan 33 Task 3 fix 3, GROUP_LEAVE_N 3)."""
    return [z(i, x, y, **k) for i, (x, y) in enumerate(at, 1)]


def closing(tmp_path, on=("GROUP_LEAVE",), second=NEAR, scan=None, x=100.5, y=200.5, off=(), **frame):
    """Two ticks: the trio at WEST, then at `second`; `scan` squares scanned first; the Plan 34 switches named in `off`
    (`survive.T19_SWITCHES`) set off (a test of an earlier rule pinned with the later rule's switch off)."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name in on)
    for name in off:
        setattr(sv, name, False)
    if scan:
        r.scan(scan)
    r.frame(x=x, y=y, zombies=pair(WEST), **frame)
    tick(r, sv)
    r.advance(0.5)
    r.frame(x=x, y=y, zombies=pair(second), **frame)
    tick(r, sv)
    return r, sv


def test_a_closing_trio_in_the_open_is_left_by_a_fighting_retreat_from_its_centroid(tmp_path):
    """GROUP_LEAVE, no door known (the fighting retreat, Angus 2026-11-09, memory `fighting-retreat`): the second line's
    three closing within GROUP_ENTRY_R keep the Fight on the nearest standing zombie, its stance leg `aim` (no steer,
    no run) with `targetId` that zombie and the back vector away from the three's centroid, logged `group_leave`
    {closing [1, 2, 3], leg "retreat"} and `group_retreat` {leg, closing, centroid_away}. Plan 35 Task 8: the
    nearest at 2.90 tiles lies beyond KEEP_R, so the stance's own leg goes (the stand facing it; the retreat's back
    leg is deleted, the heading the reflex's withdraw bias)."""
    r, sv = closing(tmp_path)
    why = threat_why(tmp_path)
    assert why["fight"] is True and "flee" not in why and sv.mode == "fight"
    assert sorted(why["group_leave"]["closing"]) == [1, 2, 3] and why["group_leave"]["leg"] == "retreat"
    cx, cy = sum(p[0] for p in NEAR) / 3, sum(p[1] for p in NEAR) / 3
    d = math.hypot(100.5 - cx, 200.5 - cy)
    away = ((100.5 - cx) / d, (200.5 - cy) / d)
    assert why["group_retreat"]["leg"] == "retreat" and why["group_retreat"]["centroid_away"] == pytest.approx(away)
    cmd = r.cmd()
    assert cmd[0] == "aim" and cmd[1]["targetId"] == 2 and cmd[1]["seconds"] == P.AIM_LEG_S   # 2 is the nearest
    assert (cmd[1]["vx"], cmd[1]["vy"]) == (0.0, 0.0) and why["leg"] == "stand"


def test_with_group_leave_off_the_trio_is_fought(tmp_path):
    """The falsifier: the same two lines with the rule off make no leave (the trio within DANGER_R is the fight)."""
    closing(tmp_path, on=())
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave" and "group_leave" not in why


def test_a_closing_pair_is_not_left_but_fought(tmp_path):
    """Plan 33 Task 3 fix 3 (trial 1 of round two: the leave at two closing left the pairs Plan 32 fought and killed
    under PAIR_NEAREST): the trio's first two zombies alone, both closing within GROUP_ENTRY_R and none within
    FIGHT_REACH, are no leave (GROUP_LEAVE_N 3): no `group_leave` why, the other rules take the pair."""
    assert P.GROUP_LEAVE_N == 3
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name == "GROUP_LEAVE")
    r.frame(x=100.5, y=200.5, zombies=pair(WEST[:2]))
    tick(r, sv)
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=pair(NEAR[:2]))
    tick(r, sv)
    why = threat_why(tmp_path)
    assert sv.leave is None and why.get("flee") != "leave" and "group_leave" not in why


def shifted_house(dx):
    sqs = two_door_house(exterior2=CLOSED)
    for q in sqs:
        q["x"] += dx
    return sqs


def test_a_known_door_within_leave_door_r_is_the_leave_s_target_and_its_stand(tmp_path):
    """GROUP_LEAVE with a known door within LEAVE_DOOR_R (6.0): house 1 moved 4 tiles west, its west door at (106, 201),
    the approach square's centre 5.0 tiles east, a second exterior door on its floor: the leave is the Flee's walk to
    that approach square at a run, its plan a doorway stand (P24-AO), logged `group_leave` {leg "door", door
    [106, 201, 0]} (the Flee, not the Fight). Named change, Plan 34 Task 2 (LEAVE_DOOR_RACE): the trio's nearest
    stands 2.90 tiles off, within DOOR_RACE_R, so the case is pinned with `LEAVE_DOOR_RACE` off (on, `door_refused`
    "race": `test_survive_am`)."""
    r, sv = closing(tmp_path, scan=shifted_house(-4), off=("LEAVE_DOOR_RACE",))
    why = threat_why(tmp_path)
    assert why["flee"] == "leave" and why["group_leave"]["leg"] == "door"
    assert why["group_leave"]["door"] == [106, 201, 0] and why["group_retreat"]["leg"] == "door"
    assert r.cmd() == ("walkTo", {"x": 105.5, "y": 201.5, "gait": "run"})
    assert sv.flee.plan["building"] == 1 and sv.flee.plan.get("stand") is True


def test_a_door_beyond_leave_door_r_is_not_walked_to(tmp_path):
    """House 1 as built (its approach square 9.0 tiles off, beyond LEAVE_DOOR_R; LEAVE_R 20 is no longer the walk's
    radius): the leave is the retreat, the Fight's backpedal away from the group, never a walk."""
    r, sv = closing(tmp_path, scan=shifted_house(0))
    why = threat_why(tmp_path)
    assert why["fight"] is True and why["group_leave"]["leg"] == "retreat" and r.cmd()[0] == "aim"


def test_a_standing_zombie_within_fight_reach_no_longer_withholds_the_leave(tmp_path):
    """The FIGHT_REACH exception is dropped (round two, trial 2: it defeated the leave exactly when it was needed): the
    second line's 1 at 1.9 tiles (within FIGHT_REACH, beyond STAND_MIN_R) with three closing is a retreat leg."""
    r, sv = closing(tmp_path, second=((98.6, 200.6), (97.65, 199.95), (100.5, 206.3)))
    why = threat_why(tmp_path)
    assert "withheld" not in why["group_leave"] and why["group_leave"]["leg"] == "retreat"


def test_under_the_health_floor_the_leave_is_not_taken(tmp_path):
    """The FLEE_HEALTH_FLOOR exception: under it the health flee stands, no leave read."""
    closing(tmp_path, health=P.FLEE_HEALTH_FLOOR - 1.0)
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave" and "group_leave" not in why   # the trio within DANGER_R is `many` under the floor


def test_a_wall_at_the_back_withholds_the_leave(tmp_path):
    """`back_cover`: a known blocked edge 0.5 tiles east of the player (the W edge of square (101, 200)), on its back
    side away from the pair, withholds the leave (`withheld` "cover"); the same edge west of a pair coming from the east
    (in front of the player) does not. Pinned with Plan 34's LEAVE_ENTRY off (a named change, Task 3b, ruling P34-G:
    the rule logs the back read beside the entry and the leave enters; `test_survive_ao.py` reads it on)."""
    wall = [square(101, 200, blockW=True)]
    closing(tmp_path, scan=wall, off=("LEAVE_ENTRY",))
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave"
    assert why["group_leave"] == {"withheld": "cover", "closing": [2, 1, 3], "cover": {"kind": "wall", "at": [101, 200, "W"]}}
    assert G.back_cover(type("W", (), {"me": {"x": 100.5, "y": 200.5, "z": 0}, "map": {(101, 200, 0): wall[0]}})(),
                        (-1.0, 0.0)) is None


def test_a_trio_not_closing_is_not_left(tmp_path):
    """Three within GROUP_ENTRY_R standing off (the same distances on both lines) are no closing trio."""
    r, sv = make(tmp_path)
    sv.GROUP_LEAVE = True
    for _ in range(2):
        r.frame(x=100.5, y=200.5, zombies=pair(NEAR))
        tick(r, sv)
        r.advance(0.5)
    why = threat_why(tmp_path)
    assert "group_leave" not in why and why.get("flee") != "leave"


def test_the_leave_ends_when_the_trio_strings_out(tmp_path):
    """The running leave (the run) ends on the line reading fewer than two standing within GROUP_ENTRY_R (logged
    `group_leave` {end "strung"}); the tick then decides by the other rules. Pinned with Plan 34's STRUNG_HOLD off (a
    named change: the rule holds the leave STRUNG_LINES lines; `test_survive_an.py` reads it on)."""
    r, sv = closing(tmp_path, off=("STRUNG_HOLD",))
    assert sv.leave is not None
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=pair(((94.0, 200.6), (97.65, 199.95), (100.5, 214.0))))
    tick(r, sv)
    why = threat_why(tmp_path)
    assert sv.leave is None and why["group_leave"] == {"end": "strung", "n": 1} and why.get("flee") != "leave"


def test_f18_s_first_leave_is_the_retreat_at_line_358():
    """F18, open loop, GROUP_LEAVE alone (fix 3 and its addenda: GROUP_LEAVE_N 3, the FIGHT_REACH exception dropped, the
    leave a fighting retreat): the three closing standing zombies within GROUP_ENTRY_R first read without a wall at the
    back at line 358 (13651, 13648, 13653; 1.05 tiles to the nearest, none within STAND_MIN_R, so no shove): the leave is
    the retreat (`group_leave` {leg "retreat"}, `group_retreat` away from the centroid), held on 359 to 361 while three
    stand within GROUP_ENTRY_R and ended `strung` on 362 (two). Line 174, the group's earlier three closing
    (13652, 13649, 13651), is withheld `cover` (a wall at the back, {"kind": "wall", "at": [10752, 10642, "N"]}). No
    leave line sends a steer or a run. Pinned with LEAVE_ENTRY off (a named change, Task 3b, ruling P34-G:
    the rule enters line 174's leave against the wall and the leave with three already on the character), and with
    SPENT_LEAVE off (a named change, Task 3c, ruling P34-I: the meet reads spent at line 358, so the rule's leg there
    is the run; Plan 37 Task 3 deleted SPENT_LEAVE with the run). Pinned with DISPOSITION off (a named change, Plan 37
    Task 3: F18's hello announces `melee`, so the selector owns the entry there)."""
    rows = f18(**only("GROUP_LEAVE"), LEAVE_ENTRY=False, DISPOSITION=False)
    gl = {k: threat(r)["group_leave"] for k, r in enumerate(rows, 1) if "group_leave" in threat(r)}
    assert sorted(gl) == [174, 358, 359, 360, 361, 362]
    assert gl[174]["withheld"] == "cover" and gl[174]["closing"] == [13652, 13649, 13651]
    assert gl[358] == {"closing": [13651, 13648, 13653], "leg": "retreat"}
    assert all(gl[k]["leg"] == "retreat" and gl[k]["n"] == 3 for k in (359, 360, 361))
    assert gl[362] == {"end": "strung", "n": 2}
    away = threat(rows[357])["group_retreat"]["centroid_away"]
    assert math.hypot(*away) == pytest.approx(1.0) and threat(rows[357])["group_retreat"]["leg"] == "retreat"
    assert all(action(r) != "steer" for k, r in enumerate(rows, 1) if 358 <= k <= 361)
    assert all(threat(r).get("flee") != "leave" for r in rows)


# ================================================================ fix 4: the retreat retargets and always sends its leg
# Plan 33 round three (P31-T trials, not evidence): street-1, `x_trial-ladder-20261109-042558`, lines 98 to 100 held the
# pin 99 at 4.40 tiles while 117 closed to 0.96, its retreat lines sent nothing under hit reactions while the standing
# count rose to eight and the character died; the agent fixture, `x_trial-ladder-20261109-040825`, lines 209 to 212 held
# a walk toward a pin 8.93 tiles off while the trio closed to 0.27.
ME = (100.5, 200.5)
WEST_V = (-1.0, 0.0)   # a retreat heading: due west


def zm(zid, x, y, **k):
    return z(zid, x, y, me=ME, **k)


def fight4(tmp_path, zs, retreat=WEST_V, stance=True, target=None, scan=None, caps=None, **frame):
    """A Fight on a fresh Rig (the player at ME, `caps` the hello's) over one frame of `zs`, its rules the defaults
    (Plan 33 Task 2's `crawler_first` off), `retreat` and `stance` set as Survive sets them, pinned on `target`."""
    r = Rig(tmp_path, caps=caps)
    if scan:
        r.scan(scan)
    r.frame(x=ME[0], y=ME[1], zombies=zs, **frame)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = f.rules - {"crawler_first"}
    f.retreat, f.stance, f.target = retreat, stance, target
    return r, f


# ---- (a) the pin
def test_a_far_pin_gives_way_to_a_standing_zombie_closing_within_keep_r_under_pair_nearest(tmp_path):
    """Fix 4 (a), outside the retreat: the pin 1 standing 4.4 tiles east (beyond KEEP_R) and 2 closing to 0.96 within
    it: the pair rule counts the far pin, so the nearer standing one takes it (`pair_nearest` {target 2, n 2,
    standing 2}); with the rule off the pin holds on 1 (the trial's lines 98 to 100)."""
    zs = [zm(1, 104.9, 200.5), zm(2, 99.54, 200.5)]
    r, f = fight4(tmp_path, zs, retreat=None, target=1)
    f.choose()
    assert f.target == 2 and f.why["pair_nearest"] == {"target": 2, "n": 2, "standing": 2}
    (tmp_path / "off").mkdir()
    r2, f2 = fight4(tmp_path / "off", zs, retreat=None, target=1)
    f2.rules = f2.rules - {"pair_nearest"}
    f2.choose()
    assert f2.target == 1 and "pair_nearest" not in f2.why


def test_a_far_pin_alone_or_beside_a_fallen_one_is_no_pair(tmp_path):
    """The far pin is counted only beside a standing zombie within KEEP_R: alone it is no pair, and beside a fallen
    one within KEEP_R the finish keeps its place (no `pair_nearest`)."""
    r, f = fight4(tmp_path, [zm(1, 104.9, 200.5)], retreat=None, target=1)
    assert f._pair_read() is None
    (tmp_path / "b").mkdir()
    r2, f2 = fight4(tmp_path / "b", [zm(1, 104.9, 200.5), zm(2, 99.54, 200.5, onFloor=True)], retreat=None, target=1)
    assert f2._pair_read() is None


def test_a_fallen_pin_beyond_keep_r_gives_way_to_a_standing_zombie_within_it(tmp_path):
    """Fix 5 (round four, trial 2's lines 249 to 253: the pin fallen at 3.3 tiles held on a stand leg while a standing
    one lunged to 0.43 and bit): the pin 1 on the floor 3.3 tiles east and 2 standing at 1.2 within KEEP_R: the pair
    rule counts the fallen pin (never picks it), so 2 takes the pin (`pair_nearest` {target 2, n 2, standing 1}); with
    the rule off the pin holds on 1."""
    zs = [zm(1, 103.8, 200.5, onFloor=True), zm(2, 101.7, 200.5)]
    r, f = fight4(tmp_path, zs, retreat=None, target=1)
    f.choose()
    assert f.target == 2 and f.why["pair_nearest"] == {"target": 2, "n": 2, "standing": 1}
    (tmp_path / "off").mkdir()
    r2, f2 = fight4(tmp_path / "off", zs, retreat=None, target=1)
    f2.rules = f2.rules - {"pair_nearest"}
    f2.choose()
    assert f2.target == 1 and "pair_nearest" not in f2.why


def test_under_the_retreat_the_pin_moves_to_the_nearest_standing_zombie_of_the_group(tmp_path):
    """Fix 4 (a): under the retreat a trio east at 2.5, 3.5 and 4.5 tiles with the pin on the farthest (3): the pin
    moves to the nearest standing one (1), logged `retreat_pin` {target 1, from 3} and `retreat` true; a fallen one
    nearer still is not the pin."""
    zs = [zm(1, 103.0, 200.5), zm(2, 104.0, 200.5), zm(3, 105.0, 200.5), zm(4, 101.5, 200.5, onFloor=True)]
    r, f = fight4(tmp_path, zs, target=3)
    cmd = f.choose()
    assert f.target == 1 and f.why["retreat_pin"] == {"target": 1, "from": 3} and f.why["retreat"] is True
    assert cmd.TYPE == "aim" and cmd.targetId == 1 and f.why["leg"] == "back"
    (tmp_path / "fresh").mkdir()
    r2, f2 = fight4(tmp_path / "fresh", zs)   # a fresh Fight's first pin is no move: no `retreat_pin`
    f2.choose()
    assert f2.target == 1 and "retreat_pin" not in f2.why and f2.why["retreat"] is True


def test_under_the_retreat_a_nearer_one_by_less_than_pair_switch_r_keeps_the_pin(tmp_path):
    """The retreat pin's hysteresis (PAIR_SWITCH_R 0.3, the pair rule's): 1 at 2.5 tiles, the pin on 2 at 2.7 (0.2
    farther): the pin holds on 2, no `retreat_pin` logged; 2 at 2.9 (0.4 farther) gives it to 1."""
    r, f = fight4(tmp_path, [zm(1, 103.0, 200.5), zm(2, 103.2, 200.5), zm(3, 105.0, 200.5)], target=2)
    f.choose()
    assert f.target == 2 and "retreat_pin" not in f.why
    (tmp_path / "b").mkdir()
    r2, f2 = fight4(tmp_path / "b", [zm(1, 103.0, 200.5), zm(2, 103.4, 200.5), zm(3, 105.0, 200.5)], target=2)
    f2.choose()
    assert f2.target == 1 and f2.why["retreat_pin"] == {"target": 1, "from": 2}


def test_under_the_retreat_a_running_leg_at_another_than_the_retreat_pin_gives_way(tmp_path):
    """`busy` reads the retreat pin as it reads the pair's: a running aim at the far pin gives way once a standing
    one reads PAIR_SWITCH_R nearer."""
    r, f = fight4(tmp_path, [zm(1, 104.5, 200.5)], target=1)
    f.step()
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    assert f.busy() is True
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 104.5, 200.5), zm(2, 103.0, 200.5)])
    f.observe()
    assert f.busy() is False


# ---- (c) the band
FIVE_WEST = WEST + ((96.9, 201.3), (96.95, 199.3))   # two more beside the pair, 3.6 and 3.7 tiles west
FIVE_NEAR = NEAR + ((97.6, 201.4), (97.7, 199.3))    # ... closing to 3.04 and 3.05


def band(tmp_path, n, off=()):
    """Two ticks of the first `n` of FIVE: their first line, then closing within GROUP_ENTRY_R; the Plan 34 switches
    named in `off` set off."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name == "GROUP_LEAVE")
    for name in off:
        setattr(sv, name, False)
    r.frame(x=100.5, y=200.5, zombies=pair(FIVE_WEST[:n]))
    tick(r, sv)
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=pair(FIVE_NEAR[:n]))
    tick(r, sv)
    return r, sv


def test_a_drag_guard_line_logs_no_stale_group_retreat(tmp_path):
    """Fix 4: the leave's outputs are cleared at the tick's start (`_group_read`), so a line the drag guard answers
    before the leave's row (the trial's lines 117 to 152 carried the last retreat's `group_retreat`) logs none."""
    r, sv = band(tmp_path, 4)
    assert "group_retreat" in threat_why(tmp_path)
    r.advance(0.5)
    k = guard(("GROUP_LEAVE",))
    r.frame(x=100.5, y=200.5, zombies=k["zombies"], attackers=k["attackers"], hit_reaction=k["hit_reaction"])
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why["group"] == "drag" and "group_retreat" not in why and sv.retreat is None
