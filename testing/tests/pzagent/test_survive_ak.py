"""Plan 33 Task 3 (the group's entry and the drag guard; F18, `f_goals_18-20261108-235005`: the drag-down death at game
minute 617 under a group of three walked in while the finish stalled): `survive.T18_SWITCHES`, three planner rules on
`threat.Threat` (`planner/group.py`), each with its replay test on F18's decision lines (`decision.log` over
`state.log`, open loop: `replay_decisions.replay` checks the decisions at the situations the run recorded, never an
outcome) and its unit tests on the fake mod.

- GROUP_LEAVE (`group.ThreatGroup._group_leave`): GROUP_LEAVE_N (3, fix 3) standing zombies closing within
  GROUP_ENTRY_R in the open with nothing at the back within WALL_R, whatever stands in reach (the FIGHT_REACH exception
  dropped), not under FLEE_HEALTH_FLOOR: one shove at a zombie within STAND_MIN_R on the first line, then the Flee's walk
  to a known door within LEAVE_DOOR_R (the doorway stand there), else the fighting retreat (the Fight's backpedal away
  from the group's centroid, no run). On F18 it first fires at line 358 (13651, 13648, 13653), the retreat; line 174 is
  withheld by a wall at the back.
- DRAG_GUARD_FIGHT (`group.ThreatGroup._drag_fight`): the drag-down guard's flee under a hit reaction or STUCK_FRAMES
  unmoving frames shoves the standing zombie in front, at most DRAG_SHOVES_PER_EPISODE times a stuck episode (fix 2),
  the run sent after it until the character has moved STUCK_FREE_R from the episode's start; F18's guard line 402
  sends the shove and the lines after it the run.
- SIDE_CLEAR (`group.ThreatGroup._side_clear`): no run steer within SIDE_R of a standing zombie over SIDE_LOOK; with no
  clear heading (F18's line 402) the least-bad run (fix 2: the heading whose nearest standing zombie along the leg is
  farthest), never a shove.

Fix 2 (Plan 33 round one, trial 3: arm N died on `street-1` standing in a pile of three, the guard's and SIDE_CLEAR's
shoves sent tick after tick under the hit reactions, never a run): one shove a stuck episode, then the run; SIDE_CLEAR's
least-bad heading in place of its shove.
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
    assert (P.STUCK_FREE_R, P.DRAG_SHOVES_PER_EPISODE) == (1.0, 1)   # fix 2
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


def test_after_the_episode_s_one_shove_the_guard_runs_whatever_the_reaction_reads(tmp_path):
    """Fix 2: the episode's one shove sent, the next guard tick (the reaction still read) sends the guard's run, the
    shove still running dropped for it (logged `drag_fight` {spent 1, why "hit"}); no second shove while the character
    has not moved STUCK_FREE_R, a rejected shove's end included."""
    k = guard(("DRAG_GUARD_FIGHT",))
    zs = k.pop("zombies")
    r, sv = rig(tmp_path, zs, **k)
    tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1})
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=zs, attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    assert threat_why(tmp_path)["drag_fight"] == {"spent": 1, "why": "hit"}
    r.fake.answer({"shove": ["rejected busy"], "steer": ["done"]})
    r.pump()
    for _ in range(3):
        r.advance(0.5)
        r.frame(x=100.6, y=200.5, zombies=zs, attackers=2, hit_reaction="Bite")
        tick(r, sv)
        assert threat_why(tmp_path)["drag_fight"] == {"spent": 1, "why": "hit"}
        r.fake.answer({"steer": ["done"]})
        r.pump()
    assert [a.type for a in r.acts.history].count("shove") == 1


def test_stuck_frames_under_a_running_steer_turn_the_guard_s_run_into_the_shove(tmp_path):
    """No hit reaction: the guard runs (the steer); once STUCK_FRAMES frames have read `moving` false under that running
    steer, the next guard tick shoves (`why` "stuck") and opens the episode at the character's place; a frame reading
    the character moving ends no episode (fix 2), the run follows; moved STUCK_FREE_R from the episode's start, the
    episode ends and a new read (here the hit reaction) may shove once again."""
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
    assert sv.drag_episode == {"at": (100.5, 200.5), "shoves": 1}
    r.fake.answer({"shove": ["done"]})
    r.pump()
    r.frame(x=100.9, y=200.5, zombies=zs, attackers=2, hit_reaction="Bite")
    r.world.me["moving"] = True
    r.advance(0.5)
    tick(r, sv)
    assert sv.drag_episode is not None and r.cmd()[0] == "steer"   # 0.4 tiles: the episode stands, the run
    r.fake.answer({"steer": ["done"]})
    r.pump()
    moved = [dict(zz, x=zz["x"] + 1.0) for zz in zs]
    r.frame(x=101.5, y=200.5, zombies=moved, attackers=2, hit_reaction="Bite")
    r.advance(0.5)
    tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1}) and sv.drag_episode == {"at": (101.5, 200.5), "shoves": 1}


def pile(dx=0.0):
    """The trial's pile: four standing round the player at (100.5 + dx, 200.5) facing +x, at 0.6 to 0.7 tiles."""
    me = (100.5 + dx, 200.5)
    return [z(1, 101.1 + dx, 200.5, me=me), z(2, 99.85 + dx, 200.6, me=me), z(3, 100.5 + dx, 201.2, me=me),
            z(4, 100.4 + dx, 199.8, me=me)]


def test_a_pile_shoves_once_then_runs_the_least_bad_heading_until_moved(tmp_path):
    """Fix 2, the trial's pile (four standing round the character, a hit reaction on every frame, the three rules on):
    the first tick shoves the one in front; every next tick, the character unmoved, sends the guard's run, which no
    heading passes clear, as SIDE_CLEAR's least-bad heading (`side_clear` {turn, near, least_bad}: the distance along
    the leg to its nearest standing zombie, the largest over the turns); no second shove until the character has moved
    STUCK_FREE_R; past it, the next read shoves once again."""
    r, sv = rig(tmp_path, pile(), on=T17, attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1})
    named = [(e["id"], e) for e in pile()]
    for i in range(4):
        r.advance(0.5)
        r.frame(x=100.5, y=200.5, zombies=pile(), attackers=2, hit_reaction="Bite")
        tick(r, sv)
        why = threat_why(tmp_path)
        last = r.acts.history[-1]
        assert last.type == "steer" and last.args["gait"] == "run", i
        assert why["drag_fight"] == {"spent": 1, "why": "hit"}
        sc = why["side_clear"]
        assert set(sc) == {"turn", "near", "least_bad"} and sc["near"], i
        v = (last.args["vx"], last.args["vy"])
        v0 = P._rotate(v, -sc["turn"])
        assert G.side_dist(r.world, v, named) == pytest.approx(sc["least_bad"])
        assert all(G.side_dist(r.world, P._rotate(v0, t), named) <= sc["least_bad"] + 1e-9
                   for t in (0,) + G.SIDE_TURNS)
        r.fake.answer({"steer": ["done"]})
        r.pump()
    assert [a.type for a in r.acts.history].count("shove") == 1
    r.advance(0.5)
    r.frame(x=101.6, y=200.5, zombies=pile(1.1), attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert r.cmd() == ("shove", {"targetId": 1}) and [a.type for a in r.acts.history].count("shove") == 2


def test_with_no_standing_zombie_within_shove_r_the_guard_runs(tmp_path):
    """The shove needs a target within SHOVE_R: three standing at 1.3 tiles (the frame's attackers count aside) leave
    the guard's run."""
    zs = [z(1, 101.8, 200.5), z(2, 99.2, 200.5), z(3, 100.5, 201.8)]
    r, sv = rig(tmp_path, zs, on=("DRAG_GUARD_FIGHT",), attackers=2, hit_reaction="Bite")
    tick(r, sv)
    assert r.cmd()[0] == "steer" and "drag_fight" not in threat_why(tmp_path)


def test_f18_s_guard_lines_send_one_shove_then_the_run():
    """F18, open loop, DRAG_GUARD_FIGHT alone (fix 2): line 402 (two attackers, the hit reaction "Bite") sends the shove
    at 13653 (0.5086990833343952 tiles, the nearest standing in front) where the record ran; the episode's one shove
    spent, line 403 sends the guard's run (the shove dropped for it) and no guard line after 402 sends a shove, each
    logging `drag_fight` {spent 1, why "hit"} (every guard frame read a hit reaction; the open loop never moves the
    character, so the episode stands)."""
    rows = f18(**only("DRAG_GUARD_FIGHT"))
    assert rows[401]["action"] == {"type": "shove", "args": {"targetId": 13653}}
    assert threat(rows[401])["drag_fight"] == {"target": 13653, "dist": 0.5086990833343952, "why": "hit"}
    assert action(rows[402]) == "steer" and rows[402]["action"]["args"]["gait"] == "run"
    for k in GUARD[1:]:
        why = threat(rows[k - 1])
        assert action(rows[k - 1]) in (None, "steer"), k
        assert why["drag_fight"] == {"spent": 1, "why": "hit"} and why["group"] == "drag", k


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


def test_with_no_clear_heading_the_least_bad_run_is_sent(tmp_path):
    """Fix 2: eight standing round the player at 0.8 tiles, every heading passes one, so the run takes the heading
    (the wanted one or a SIDE_TURNS turn of it) whose nearest standing zombie along the leg is farthest (logged
    `side_clear` {turn, near, least_bad}), its seconds and gait kept; never a shove."""
    ring = [z(i + 1, 100.5 + 0.8 * math.cos(math.radians(45 * i + 10)),
              200.5 + 0.8 * math.sin(math.radians(45 * i + 10))) for i in range(8)]
    r, sv = rig(tmp_path, ring, on=("SIDE_CLEAR",), attackers=2)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    sc = why["side_clear"]
    assert set(sc) == {"turn", "near", "least_bad"} and sc["turn"] in (0,) + G.SIDE_TURNS
    named = [(i + 1, zz) for i, zz in enumerate(ring)]
    v = heading(r)
    v0 = P._rotate(v, -sc["turn"])
    assert G.side_dist(r.world, v, named) == pytest.approx(sc["least_bad"])
    assert all(G.side_dist(r.world, P._rotate(v0, t), named) <= sc["least_bad"] + 1e-9 for t in (0,) + G.SIDE_TURNS)
    assert G.side_hits(r.world, v, named)   # no heading clear: the least bad passes one


def test_side_dist_reads_the_nearest_passed_zombie_along_the_leg():
    """`side_dist`: the projection along the leg of the nearest zombie `side_hits` names; SIDE_LOOK + SIDE_R with
    none."""
    class W:
        me = {"x": 0.0, "y": 0.0}
    zs = [(1, {"x": 2.0, "y": 0.9}), (2, {"x": -0.5, "y": 0.2}), (4, {"x": 3.5, "y": 0.5})]
    assert G.side_dist(W(), (1.0, 0.0), zs) == pytest.approx(2.0)
    assert G.side_dist(W(), (0.0, -1.0), zs) == P.SIDE_LOOK + P.SIDE_R


def test_a_walk_steer_is_never_turned(tmp_path):
    """SIDE_CLEAR reads a run only: a walk steer passing a standing zombie is answered as it is."""
    from agent.base.pza1 import Steer
    r, sv = rig(tmp_path, [z(1, 101.5, 200.6)], on=("SIDE_CLEAR",))
    walk = (sv, Steer(1.0, 0.0, 3.0, "walk"))
    assert sv._side_clear(walk) is walk
    run = (sv, Steer(1.0, 0.0, 3.0, "run"))
    assert sv._side_clear(run)[1].TYPE == "steer" and sv._side_clear(run)[1] != run[1]


def test_f18_s_line_402_has_no_clear_heading_and_runs_the_least_bad():
    """F18, open loop, SIDE_CLEAR alone (fix 2): line 402's run (0.2351089324902877, 0.9719690272139733) passes 13653;
    with four standing within 0.92 tiles no SIDE_TURNS heading is clear, so the least-bad heading's run is sent in its
    place (`side_clear` {turn, near [13653], least_bad}); no guard line sends a shove."""
    rows = f18(**only("SIDE_CLEAR"))
    assert action(rows[401]) == "steer" and rows[401]["action"]["args"]["gait"] == "run"
    sc = threat(rows[401])["side_clear"]
    assert sc["near"] == [13653] and set(sc) == {"turn", "near", "least_bad"} and sc["least_bad"] > 0.0
    assert all(action(rows[k - 1]) != "shove" for k in GUARD)


# ================================================================ GROUP_LEAVE
WEST = ((96.9, 200.6), (97.0, 199.9), (100.5, 210.4))   # the trio's first line: 3.6 and 3.55 tiles west and 9.9 south of (100.5, 200.5) (the third beyond ENGAGE_R inside DISENGAGE_R and not behind the pair, so the pair is fought and no flee runs before the leave)
NEAR = ((97.6, 200.7), (97.65, 199.95), (100.5, 206.3))   # the next: 2.91, 2.90 and 5.8, all closing within GROUP_ENTRY_R


def pair(at, **k):
    """The zombies of a line, ids 1, 2, 3 (a pair when `at` holds two: Plan 33 Task 3 fix 3, GROUP_LEAVE_N 3)."""
    return [z(i, x, y, **k) for i, (x, y) in enumerate(at, 1)]


def closing(tmp_path, on=("GROUP_LEAVE",), second=NEAR, scan=None, x=100.5, y=200.5, **frame):
    """Two ticks: the trio at WEST, then at `second`; `scan` squares scanned first."""
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


def test_a_closing_trio_in_the_open_is_left_by_a_fighting_retreat_from_its_centroid(tmp_path):
    """GROUP_LEAVE, no door known (the fighting retreat, Angus 2026-11-09, memory `fighting-retreat`): the second line's
    three closing within GROUP_ENTRY_R keep the Fight on the nearest standing zombie, its stance leg `aim` (no steer,
    no run) with `targetId` that zombie and the back vector away from the three's centroid, logged `group_leave`
    {closing [1, 2, 3], leg "retreat"} and `group_retreat` {leg, closing, centroid_away}."""
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
    assert (cmd[1]["vx"], cmd[1]["vy"]) == pytest.approx(away) and why["leg"] == "back"


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
    [106, 201, 0]} (the Flee, not the Fight)."""
    r, sv = closing(tmp_path, scan=shifted_house(-4))
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


def test_a_standing_zombie_within_stand_min_r_is_shoved_on_the_first_line_then_the_retreat_follows(tmp_path):
    """The leave's first line with a standing zombie within STAND_MIN_R (0.61, the engine's shove distance): one shove
    at it (the Flee's, `leave_leg` "shove"), the retreat from the next line; it shoves once only."""
    r, sv = closing(tmp_path, second=((100.0, 200.7), (97.65, 199.95), (100.5, 206.3)))
    why = threat_why(tmp_path)
    assert why["flee"] == "leave" and why["group_leave"]["leg"] == "shove" and why["group_leave"]["target"] == 1
    assert r.cmd() == ("shove", {"targetId": 1})
    r.advance(0.5)
    r.frame(x=100.5, y=200.5, zombies=pair(((100.0, 200.7), (97.65, 199.95), (100.5, 205.9))))
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "retreat" and why.get("shove") is None and sv.mode == "fight"


def test_under_the_health_floor_the_leave_is_not_taken(tmp_path):
    """The FLEE_HEALTH_FLOOR exception: under it the health flee stands, no leave read."""
    closing(tmp_path, health=P.FLEE_HEALTH_FLOOR - 1.0)
    why = threat_why(tmp_path)
    assert why.get("flee") != "leave" and "group_leave" not in why   # the trio within DANGER_R is `many` under the floor


def test_a_wall_at_the_back_withholds_the_leave(tmp_path):
    """`back_cover`: a known blocked edge 0.5 tiles east of the player (the W edge of square (101, 200)), on its back
    side away from the pair, withholds the leave (`withheld` "cover"); the same edge west of a pair coming from the east
    (in front of the player) does not."""
    wall = [square(101, 200, blockW=True)]
    closing(tmp_path, scan=wall)
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
    `group_leave` {end "strung"}); the tick then decides by the other rules."""
    r, sv = closing(tmp_path)
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
    leave line sends a steer or a run."""
    rows = f18(**only("GROUP_LEAVE"))
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


def test_f18_with_the_three_on_by_default_its_guard_shoves_once_then_runs_the_least_bad():
    """F18, open loop, the three on (the defaults; fix 2): the guard's line 402 shoves 13653 (DRAG_GUARD_FIGHT reads
    first, so no run reaches SIDE_CLEAR), line 403 sends the run through SIDE_CLEAR (turned or least bad), no guard line
    after 402 sends a shove, and the leaves fire as GROUP_LEAVE's alone (the retreat, 358)."""
    rows = f18(**{k: True for k in T17})
    assert rows[401]["action"] == {"type": "shove", "args": {"targetId": 13653}}
    assert action(rows[402]) == "steer" and "side_clear" in threat(rows[402])
    assert all(action(rows[k - 1]) != "shove" for k in GUARD[1:])
    assert [k for k, r in enumerate(rows, 1) if threat(r).get("group_leave", {}).get("leg") == "retreat"
            and "closing" in threat(r)["group_leave"]] == [358]


