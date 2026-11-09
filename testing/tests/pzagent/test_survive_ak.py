"""Plan 33 Task 3 (the group's entry and the drag guard; F18, `f_goals_18-20261108-235005`: the drag-down death at game
minute 617 under a group of three walked in while the finish stalled): `survive.T18_SWITCHES`, three planner rules on
`threat.Threat` (`planner/group.py`), each with its replay test on F18's decision lines (`decision.log` over
`state.log`, open loop: `replay_decisions.replay` checks the decisions at the situations the run recorded, never an
outcome) and its unit tests on the fake mod.

- GROUP_LEAVE (`group.ThreatGroup._group_leave`): two standing zombies closing within GROUP_ENTRY_R (fix 1) in the
  open with nothing at the back within WALL_R: the `leave` flee to the nearest known door within LEAVE_R (the doorway
  stand there), else a run from their centroid for LEAVE_S; never with a standing zombie within FIGHT_REACH (fix 1)
  nor under FLEE_HEALTH_FLOOR. On F18 it fires first at line 201 (13652, 13649) and, on the group of three's approach,
  at line 342 (13651, 13648), then 349, 352 and 362 (13648, 13653).
- DRAG_GUARD_FIGHT (`group.ThreatGroup._drag_fight`): the drag-down guard's flee under a hit reaction or STUCK_FRAMES
  unmoving frames shoves the standing zombie in front; F18's guard lines 402 to 415 send a shove, never a steer.
- SIDE_CLEAR (`group.ThreatGroup._side_clear`): no run steer within SIDE_R of a standing zombie over SIDE_LOOK; F18's
  line 402 has no clear heading and sends the shove.
"""
import functools
import json
import math
import os

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import group as G
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_night import CLOSED, two_door_house
from .test_policies import square, zombie
from .test_survive import make, threat_why, tick

F18 = os.path.join(R.ARTIFACTS, "f_goals_18-20261108-235005")
T17 = S.T18_SWITCHES
GUARD = range(402, 416)   # F18's drag-down guard lines (the GUIDE § 6: `flee:many`, `group` "drag", 402 to 415)
RECORD_STEERS = [402, 405, 408, 410, 413]   # the five run steers the guard sent


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


@functools.lru_cache(maxsize=1)
def record():
    with open(os.path.join(F18, "decision.log"), encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def action(row):
    return (row.get("action") or {}).get("type")


def test_the_t17_switches_and_constants():
    """`survive.T18_SWITCHES`, each on by default (`Plan 33 Task 3: GROUP_LEAVE, DRAG_GUARD_FIGHT and SIDE_CLEAR on by
    default`), and the constants at `policies.py`'s end."""
    assert T17 == ("GROUP_LEAVE", "DRAG_GUARD_FIGHT", "SIDE_CLEAR")
    assert all(getattr(S.Survive, k) is True for k in T17)
    assert (P.WALL_R, P.LEAVE_R, P.LEAVE_S, P.STUCK_FRAMES, P.SIDE_R, P.SIDE_LOOK) == (1.5, 20.0, 4.0, 10, 1.0, 3.0)
    assert P.GROUP_ENTRY_R == P.DANGER_R == 6.0   # fix 1: DANGER_R's value, its own constant


def test_with_the_three_off_f18_replays_as_recorded():
    """The replay's baseline (`replay_decisions.align` takes the last of two frames reading one hour, F18's line 131):
    with the three off, F18's guard lines replay to the record's actions, the five run steers among them."""
    rows, rec = f18(**only()), record()
    assert len(rows) == len(rec) == 415
    for k in GUARD:
        assert rows[k - 1]["action"] == rec[k - 1]["action"], k
        assert threat(rows[k - 1])["flee"] == "many" and threat(rows[k - 1])["group"] == "drag"
    assert [k for k in GUARD if action(rows[k - 1]) == "steer"] == RECORD_STEERS


def rig(tmp_path, zombies, on=(), x=100.5, y=200.5, **frame):
    """A Survive on a fresh Rig with the T17 switches in `on` set on and the others off, one frame."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name in on)
    r.frame(x=x, y=y, zombies=zombies, **frame)
    return r, sv


def z(zid, x, y, me=(100.5, 200.5), **k):
    return dict(zombie(zid, x, y, me=me), **k)


# ================================================================ DRAG_GUARD_FIGHT
def guard(on, hit="Bite"):
    """Three standing round the player at (100.5, 200.5) facing +x: 2 behind it at 0.55, 1 in front at 0.6, 3 beside
    at 0.7; the frame reads two attackers (the guard's DRAG_DOWN_N - 1)."""
    return dict(zombies=[z(1, 101.1, 200.5), z(2, 99.95, 200.5), z(3, 100.5, 201.2)], attackers=2,
                hit_reaction=hit, on=on)


def test_the_guard_under_a_hit_reaction_shoves_the_zombie_in_front(tmp_path):
    """DRAG_GUARD_FIGHT: under a hit reaction the guard's flee sends a shove at the nearest standing zombie within
    SHOVE_R in front (1, at 0.6: 2 is nearer at 0.55 but behind), logged `drag_fight` {target, dist, why "hit"} beside
    the guard's `flee` and `group` "drag"; off, the run steer."""
    k = guard(("DRAG_GUARD_FIGHT",))
    r, sv = rig(tmp_path, k.pop("zombies"), **k)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert r.cmd() == ("shove", {"targetId": 1})
    assert why["group"] == "drag" and why["flee"] and why["drag_fight"] == {"target": 1, "dist": pytest.approx(0.6),
                                                                            "why": "hit"}
    (tmp_path / "off").mkdir()
    k = guard(())
    r2, sv2 = rig(tmp_path / "off", k.pop("zombies"), **k)
    tick(r2, sv2)
    assert r2.cmd()[0] == "steer" and r2.cmd()[1]["gait"] == "run"
    assert "drag_fight" not in threat_why(tmp_path / "off")


def test_the_guard_s_shove_is_held_while_it_runs_and_sent_again_after_its_end(tmp_path):
    """The shove running is held (no second send); after it ends (rejected `busy` under the reaction, as the Lua
    answers a shove in one) the next guard tick sends it again: never a run while the latch holds."""
    k = guard(("DRAG_GUARD_FIGHT",))
    zs = k.pop("zombies")
    r, sv = rig(tmp_path, zs, **k)
    tick(r, sv)
    n = len(r.acts.history)
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=zs, attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert len(r.acts.history) == n and threat_why(tmp_path)["holding"] == r.acts.history[-1].aid
    r.fake.answer({"shove": ["rejected busy"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=zs, attackers=2, hit_reaction="")
    tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1}) and threat_why(tmp_path)["drag_fight"]["why"] == "latched"


def test_stuck_frames_under_a_running_steer_turn_the_guard_s_run_into_the_shove(tmp_path):
    """No hit reaction: the guard runs (the steer); once STUCK_FRAMES frames have read `moving` false under that running
    steer, the next guard tick shoves (`why` "stuck"); a frame reading the character moving releases the latch."""
    k = guard(("DRAG_GUARD_FIGHT",), hit="")
    zs = k.pop("zombies")
    r, sv = rig(tmp_path, zs, **k)
    tick(r, sv)
    assert r.cmd()[0] == "steer"
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    for i in range(2):   # the first tick under the running steer starts the count, the second reads it full
        for _ in range(P.STUCK_FRAMES):
            r.frame(x=100.5, y=200.5, zombies=zs, attackers=2)
        r.advance(0.5)
        tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1}) and threat_why(tmp_path)["drag_fight"]["why"] == "stuck"
    assert sv.drag_latch is True
    r.fake.answer({"shove": ["done"]})
    r.pump()
    r.frame(x=100.5, y=200.5, zombies=zs, attackers=2)
    r.world.me["moving"] = True
    r.advance(0.5)
    tick(r, sv)
    assert sv.drag_latch is False and r.cmd()[0] == "steer" and "drag_fight" not in threat_why(tmp_path)


def test_with_no_standing_zombie_within_shove_r_the_guard_runs(tmp_path):
    """The shove needs a target within SHOVE_R: three standing at 1.3 tiles (the frame's attackers count aside) leave
    the guard's run."""
    zs = [z(1, 101.8, 200.5), z(2, 99.2, 200.5), z(3, 100.5, 201.8)]
    r, sv = rig(tmp_path, zs, on=("DRAG_GUARD_FIGHT",), attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert r.cmd()[0] == "steer" and "drag_fight" not in threat_why(tmp_path)


def test_f18_s_guard_lines_send_the_shove_never_a_run():
    """F18, open loop, DRAG_GUARD_FIGHT alone: line 402 (two attackers, the hit reaction "Bite") sends the shove at
    13653 (0.5086990833343952 tiles, the nearest standing in front) where the record ran; every guard line after it
    holds that shove or sends one, each logging `drag_fight` with `why` "hit" (every guard frame read a hit reaction),
    and none sends a steer."""
    rows = f18(**only("DRAG_GUARD_FIGHT"))
    assert rows[401]["action"] == {"type": "shove", "args": {"targetId": 13653}}
    assert threat(rows[401])["drag_fight"] == {"target": 13653, "dist": 0.5086990833343952, "why": "hit"}
    for k in GUARD:
        why = threat(rows[k - 1])
        assert action(rows[k - 1]) in (None, "shove"), k
        assert why["drag_fight"]["why"] == "hit" and why["group"] == "drag", k


# ================================================================ SIDE_CLEAR
def test_side_hits_reads_the_leg_ahead_within_side_r():
    """`side_hits`: a zombie ahead within SIDE_R of the leg's first SIDE_LOOK tiles is passed; one behind or abeam
    (projection 0 or less), one beyond SIDE_R of the segment or past its end beyond SIDE_R is not."""
    class W:
        me = {"x": 0.0, "y": 0.0}
    zs = [(1, {"x": 2.0, "y": 0.9}), (2, {"x": -0.5, "y": 0.2}), (3, {"x": 1.0, "y": 1.1}), (4, {"x": 3.5, "y": 0.5}),
          (5, {"x": 3.9, "y": 0.5})]
    assert G.side_hits(W(), (1.0, 0.0), zs) == [1, 4]


def side_guard(on):
    """The guard's run (two attackers, no hit reaction) away from 1 and 2 standing west at 0.6 and 0.7; 3 stands at
    (101.9, 200.95), 1.47 tiles off, by the run's line east (its away vector, the met window left out)."""
    return [z(1, 99.9, 200.5), z(2, 99.85, 200.25), z(3, 101.9, 200.95)], dict(on=on, attackers=2)


def heading(r):
    a = r.cmd()[1]
    return a["vx"], a["vy"]


def test_a_run_into_a_standing_zombie_at_the_side_is_turned_to_the_nearest_clear_heading(tmp_path):
    """SIDE_CLEAR: off, the guard's run passes 3 within SIDE_R; on, it is turned by a SIDE_TURNS step to the first
    heading passing no standing zombie (logged `side_clear` {turn, near [3]}), its seconds and gait kept."""
    zs, k = side_guard(())
    r, sv = rig(tmp_path, zs, **k)
    r.world.met_window = lambda *a, **kw: None   # the episode's first leg reads no met window: the away vector alone
    tick(r, sv)
    v0 = heading(r)
    named = [(1, zs[0]), (2, zs[1]), (3, zs[2])]
    assert G.side_hits(r.world, v0, named) == [3]
    (tmp_path / "on").mkdir()
    zs, k = side_guard(("SIDE_CLEAR",))
    r2, sv2 = rig(tmp_path / "on", zs, **k)
    r2.world.met_window = lambda *a, **kw: None
    tick(r2, sv2)
    why = threat_why(tmp_path / "on")
    turn = why["side_clear"]["turn"]
    assert why["side_clear"]["near"] == [3] and turn in G.SIDE_TURNS
    v1 = heading(r2)
    want = P._rotate(v0, turn)
    assert v1 == pytest.approx(want) and not G.side_hits(r2.world, v1, named)
    assert r2.cmd()[1]["seconds"] == P.FLEE_S and r2.cmd()[1]["gait"] == "run"
    assert all(G.side_hits(r2.world, P._rotate(v0, t), named) for t in G.SIDE_TURNS[:G.SIDE_TURNS.index(turn)])


def test_with_no_clear_heading_the_shove_is_sent(tmp_path):
    """Eight standing round the player at 0.8 tiles: every heading passes one, so the run is replaced by the shove at
    the nearest standing in front (logged `side_clear` {turn None, shove})."""
    ring = [z(i + 1, 100.5 + 0.8 * math.cos(math.radians(45 * i + 10)),
              200.5 + 0.8 * math.sin(math.radians(45 * i + 10))) for i in range(8)]
    r, sv = rig(tmp_path, ring, on=("SIDE_CLEAR",), attackers=2)
    tick(r, sv)
    why = threat_why(tmp_path)
    t = sv._front_shove_target()
    assert r.cmd() == ("shove", {"targetId": t[0]}) and why["side_clear"]["turn"] is None
    assert why["side_clear"]["shove"] == t[0] and t[1]["x"] > 100.5   # in front: the facing +x


def test_a_walk_steer_is_never_turned(tmp_path):
    """SIDE_CLEAR reads a run only: a walk steer passing a standing zombie is answered as it is."""
    from agent.base.pza1 import Steer
    r, sv = rig(tmp_path, [z(1, 101.5, 200.6)], on=("SIDE_CLEAR",))
    walk = (sv, Steer(1.0, 0.0, 3.0, "walk"))
    assert sv._side_clear(walk) is walk
    run = (sv, Steer(1.0, 0.0, 3.0, "run"))
    assert sv._side_clear(run)[1].TYPE == "steer" and sv._side_clear(run)[1] != run[1]


def test_f18_s_line_402_has_no_clear_heading_and_shoves():
    """F18, open loop, SIDE_CLEAR alone: line 402's run (0.2351089324902877, 0.9719690272139733) passes 13653; with
    four standing within 0.92 tiles no SIDE_TURNS heading is clear, so the shove at 13653 is sent in its place; no guard
    line sends a steer."""
    rows = f18(**only("SIDE_CLEAR"))
    assert rows[401]["action"] == {"type": "shove", "args": {"targetId": 13653}}
    assert threat(rows[401])["side_clear"] == {"turn": None, "near": [13653], "shove": 13653}
    assert all(action(rows[k - 1]) != "steer" for k in GUARD)


# ================================================================ GROUP_LEAVE
WEST = ((96.9, 200.6), (97.0, 199.9))   # the pair's first line: 3.6 and 3.55 tiles west of (100.5, 200.5)
NEAR = ((97.6, 200.7), (97.65, 199.95))   # the next: 2.91 and 2.90, both closing within GROUP_ENTRY_R


def pair(at, **k):
    return [z(1, at[0][0], at[0][1], **k), z(2, at[1][0], at[1][1], **k)]


def closing(tmp_path, on=("GROUP_LEAVE",), second=NEAR, scan=None, x=100.5, y=200.5, **frame):
    """Two ticks: the pair at WEST, then at `second`; `scan` squares scanned first."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name in on)
    if scan:
        r.scan(scan)
    r.frame(x=x, y=y, zombies=pair(WEST), **frame)
    tick(r, sv)
    r.advance(0.5)
    r.frame(x=x, y=y, zombies=pair(second), **frame)
    tick(r, sv)
    return r, sv


def test_a_closing_pair_in_the_open_with_no_door_known_is_left_by_a_run_from_its_centroid(tmp_path):
    """GROUP_LEAVE, no door known: the second line's two closing within GROUP_ENTRY_R send the `leave` flee's run, away
    from their centroid (east here) for LEAVE_S at a run, logged `group_leave` {closing [1, 2], leg "steer"}."""
    r, sv = closing(tmp_path)
    why = threat_why(tmp_path)
    assert why["flee"] == "leave" and sorted(why["group_leave"]["closing"]) == [1, 2]
    assert why["group_leave"]["leg"] == "steer" and why["group_leave"]["turn"] == 0
    cmd = r.cmd()
    assert cmd[0] == "steer" and cmd[1]["seconds"] == P.LEAVE_S and cmd[1]["gait"] == "run"
    cx, cy = (NEAR[0][0] + NEAR[1][0]) / 2, (NEAR[0][1] + NEAR[1][1]) / 2
    d = math.hypot(100.5 - cx, 200.5 - cy)
    assert (cmd[1]["vx"], cmd[1]["vy"]) == pytest.approx(((100.5 - cx) / d, (200.5 - cy) / d))


def test_with_group_leave_off_the_pair_is_fought(tmp_path):
    """The falsifier: the same two lines with the rule off make no leave (the pair within DANGER_R is the fight)."""
    closing(tmp_path, on=())
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave" and "group_leave" not in why


def test_a_known_door_within_leave_r_is_the_leave_s_target_and_its_stand(tmp_path):
    """GROUP_LEAVE with a known door: house 1's west door at (110, 201), its approach square's centre 9.5 tiles east
    (within LEAVE_R), a second exterior door on its floor: the leave is the Flee's walk to that approach square at a
    run, its plan a doorway stand (P24-AO), logged `group_leave` {leg "door", door [110, 201, 0]}."""
    r, sv = closing(tmp_path, scan=two_door_house(exterior2=CLOSED))
    why = threat_why(tmp_path)
    assert why["flee"] == "leave" and why["group_leave"]["leg"] == "door"
    assert why["group_leave"]["door"] == [110, 201, 0]
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "run"})
    assert sv.flee.plan["building"] == 1 and sv.flee.plan.get("stand") is True


def test_a_door_beyond_leave_r_is_not_walked_to(tmp_path):
    """The house at x0 125 (its approach square 24 tiles off, within the shelter flee's SHELTER_FLEE_R but beyond
    LEAVE_R): the leave runs from the centroid instead."""
    sqs = two_door_house(exterior2=CLOSED)
    for s in sqs:
        s["x"] += 15
    r, sv = closing(tmp_path, scan=sqs)
    why = threat_why(tmp_path)
    assert why["flee"] == "leave" and why["group_leave"]["leg"] == "steer" and r.cmd()[0] == "steer"


def test_a_standing_zombie_within_fight_reach_withholds_the_leave(tmp_path):
    """The FIGHT_REACH exception (fix 1): the second line's 1 at 1.9 tiles (within FIGHT_REACH) withholds the leave
    (logged `group_leave` {withheld "fight_reach"}): POINT_BLANK_FIGHT and the meet stand; one at 2.4 (within KEEP_R,
    beyond FIGHT_REACH) is outrun, the leave taken."""
    closing(tmp_path, second=((98.6, 200.6), (97.65, 199.95)))
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave" and why["group_leave"]["withheld"] == "fight_reach"
    (tmp_path / "keep").mkdir()
    closing(tmp_path / "keep", second=((98.1, 200.6), (97.65, 199.95)))
    assert threat_why(tmp_path / "keep")["flee"] == "leave"


def test_under_the_health_floor_the_leave_is_not_taken(tmp_path):
    """The FLEE_HEALTH_FLOOR exception: under it the health flee stands, no leave read."""
    closing(tmp_path, health=P.FLEE_HEALTH_FLOOR - 1.0)
    why = threat_why(tmp_path)
    assert why.get("flee") == "health" and "group_leave" not in why


def test_a_wall_at_the_back_withholds_the_leave(tmp_path):
    """`back_cover`: a known blocked edge 0.5 tiles east of the player (the W edge of square (101, 200)), on its back
    side away from the pair, withholds the leave (`withheld` "cover"); the same edge west of a pair coming from the east
    (in front of the player) does not."""
    wall = [square(101, 200, blockW=True)]
    closing(tmp_path, scan=wall)
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave"
    assert why["group_leave"] == {"withheld": "cover", "closing": [2, 1], "cover": {"kind": "wall", "at": [101, 200, "W"]}}
    assert G.back_cover(type("W", (), {"me": {"x": 100.5, "y": 200.5, "z": 0}, "map": {(101, 200, 0): wall[0]}})(),
                        (-1.0, 0.0)) is None


def test_a_pair_not_closing_is_not_left(tmp_path):
    """Two within GROUP_ENTRY_R standing off (the same distances on both lines) are no closing pair."""
    r, sv = make(tmp_path)
    sv.GROUP_LEAVE = True
    for _ in range(2):
        r.frame(x=100.5, y=200.5, zombies=pair(NEAR))
        tick(r, sv)
        r.advance(0.5)
    why = threat_why(tmp_path)
    assert "group_leave" not in why and why.get("flee") != "leave"


def test_the_leave_ends_when_the_pair_strings_out(tmp_path):
    """The running leave (the run) ends on the line reading fewer than two standing within GROUP_ENTRY_R (logged
    `group_leave` {end "strung"}); the tick then decides by the other rules."""
    r, sv = closing(tmp_path)
    assert sv.leave is not None
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=pair(((94.0, 200.6), (97.65, 199.95))))
    tick(r, sv)
    why = threat_why(tmp_path)
    assert sv.leave is None and why["group_leave"] == {"end": "strung", "n": 1} and why.get("flee") != "leave"


def test_f18_s_leave_fires_on_the_group_s_approach():
    """F18, open loop, GROUP_LEAVE alone (fix 1: GROUP_ENTRY_R 6.0, the exception at FIGHT_REACH): the leave fires first
    at line 201 (13652 and 13649 closing within 6 tiles, none standing within FIGHT_REACH: a run from their centroid for
    LEAVE_S) and, as the group of three came in, at line 342 (13651 at 2.25 tiles and 13648 at 5.83 both nearer than on
    line 341, the crawler 13649 under the feet fallen), then 349, 352 and 362 (13648 and 13653), each a run (no door
    known within LEAVE_R) ending on the line a standing zombie read within FIGHT_REACH; no leave line reads a standing
    zombie within FIGHT_REACH."""
    rows = f18(**only("GROUP_LEAVE"))
    fresh = [k for k, r in enumerate(rows, 1)
             if threat(r).get("flee") == "leave" and "closing" in threat(r).get("group_leave", {})]
    assert fresh == [201, 342, 349, 352, 362]
    g = threat(rows[341])["group_leave"]
    assert g["closing"] == [13651, 13648] and g["leg"] == "steer" and action(rows[341]) == "steer"
    assert rows[341]["action"]["args"]["seconds"] == P.LEAVE_S and rows[341]["action"]["args"]["gait"] == "run"
    assert threat(rows[342])["group_leave"]["end"] == "fight_reach"
    assert all(g.get("withheld") in (None, "fight_reach", "cover") for g in
               (threat(r).get("group_leave", {}) for r in rows))


def test_f18_with_the_three_on_by_default_its_guard_shoves_and_no_line_runs_into_the_group():
    """F18, open loop, the three on (the defaults): the guard's line 402 shoves 13653 (DRAG_GUARD_FIGHT reads first, so
    no run reaches SIDE_CLEAR), no guard line sends a steer, and the leaves fire as GROUP_LEAVE's alone (201, 342, 349,
    352, 362)."""
    rows = f18(**{k: True for k in T17})
    assert rows[401]["action"] == {"type": "shove", "args": {"targetId": 13653}}
    assert all(action(rows[k - 1]) != "steer" for k in GUARD)
    assert [k for k, r in enumerate(rows, 1) if threat(r).get("flee") == "leave"
            and "closing" in threat(r).get("group_leave", {})] == [201, 342, 349, 352, 362]
