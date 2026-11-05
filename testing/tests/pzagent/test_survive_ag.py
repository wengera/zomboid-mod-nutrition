"""Survival 26 (iteration 24, Plan 30 Task 3; the spec `2026-11-05-plan-30-the-intent-design.md` § 2 item 3): the six
rules of `survive.T14_SWITCHES`, each with its killing test, on E23's (`e_day_23-20261105-095110`), F14's
(`f_goals_15-20261105-092752`) and fabricated fixtures, each fixture's line named where it is the artifact's.

- P30-A (`SWING_CLOSE`, the Lua's swing close): `test_lua_melee.py`'s P30-A block (the reflex); the melee's
  `closeR` and the maneuver's `swing_close` here.
- P30-B (`GOAL_CONTINUE`, the goal runner): `test_goals.py`'s Plan 30 block; the switch here.
- P30-C (`DOOR_HELD`, `door_held.py`): a zombie behind a closed door, a locked gate or a window within DOOR_HELD_R
  decided on one tick: the stance at the door's post, the open and the meet, or the leave.
- P30-E (`STILL`, `still.ThreatStill`): a held zombie at a steady distance with the character unmoved for STILL_S
  resolved into the stance's approach, or the goal's walk.
- P30-F (`DRESS_RIDE`, `threat.Threat._dress_waits`): a dressing on a fast bleed waited on by the flee, superseded
  only within KEEP_R.
- P30-D (`SNEAK`, `sneak.SneakGait`): the gait near a zombie with no target, upright at a chaser, in a flee and for a
  press, the posture the tick's one command.
"""
import pytest

from agent.base.planner import survive as S
from agent.base.planner.goals import ExploreToward

from .fakemod import CAPS_17
from .test_policies import Rig, grid, square, zombie
from .test_survive import last, threat_why, tick
from .test_survive_g import Src, zd


def test_the_iteration_24_switches():
    """`survive.T14_SWITCHES`, each on `Survive` (or a class it derives) and on by default."""
    assert S.T14_SWITCHES == ("SWING_CLOSE", "GOAL_CONTINUE", "DOOR_HELD", "SNEAK", "STILL", "DRESS_RIDE")
    assert all(getattr(S.Survive, n) is True for n in S.T14_SWITCHES)


# ================================================================ P30-D: the sneak gait (`SNEAK`, `sneak.SneakGait`)
# No live case yet (the first sneak session is F15): the fixtures are the test's own, on PZA/1.9's fields (Task 1's
# `me.sneaking`, the zombie's `hasTarget`), the character at (100, 200) on an open ground.
SNEAK_CAPS = tuple(CAPS_17) + ("sneak",)


def sneak_rig(tmp_path, caps=SNEAK_CAPS, goal=None):
    r = Rig(tmp_path, caps=caps)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(goal))
    r.scan(grid(85, 135, 185, 215))
    return r, sv


def postures(r):
    return [(a.type, a.args) for a in r.acts.postures]


def line(tmp_path):
    return last(tmp_path)


def test_an_idle_zombie_at_6_tiles_sneaks_the_seek_s_stance_with_one_sneak_true(tmp_path):
    """P30-D: an idle zombie (no target) 6 tiles off: the Fight's seek sends its stance leg first (a posture never
    goes beside a command), then on the tick the leg runs `Sneak(True)` is the tick's one command, logged `sneak` {on
    true, near 1, sent, deferred None}; while the frame still reads `me.sneaking` false it is never sent again; once the
    frame reads it the gait holds with nothing sent."""
    r, sv = sneak_rig(tmp_path)
    idle = [zd(1, 106.0, 200.0, has_target=False)]
    r.frame(zombies=idle)
    a = tick(r, sv)
    assert a.type == "aim" and postures(r) == [] and line(tmp_path)["inputs"]["sneak"] == {"on": True, "near": 1}
    r.answer("accepted")
    r.frame(zombies=idle)
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args) == ("sneak", {"on": True}) and d["action"] == {"type": "sneak", "args": {"on": True}}
    assert d["inputs"]["sneak"] == {"on": True, "near": 1, "sent": True, "deferred": None} and d["sent"] is True
    r.answer()
    for _ in range(3):
        r.frame(zombies=idle)
        tick(r, sv)
    assert postures(r) == [("sneak", {"on": True})]
    r.frame(zombies=idle, sneaking=True)
    tick(r, sv)
    assert postures(r) == [("sneak", {"on": True})] and sv._sneak_a is None


def stand_sneaking(tmp_path):
    """`test_an_idle_zombie...`'s character, its frame reading `me.sneaking` true, the Fight's leg ended done."""
    r, sv = sneak_rig(tmp_path)
    idle = [zd(1, 106.0, 200.0, has_target=False)]
    r.frame(zombies=idle)
    tick(r, sv)
    r.answer("accepted")
    r.frame(zombies=idle)
    tick(r, sv)
    r.answer()
    r.frame(zombies=idle, sneaking=True)
    tick(r, sv)
    r.acts.history[-1].state = "done"   # the stance leg's end (the test's own)
    return r, sv


def test_the_same_zombie_now_chasing_stands_the_character_up_before_the_stance(tmp_path):
    """P30-D: the zombie (5 tiles) now reads a target: `Sneak(False)` in place of the threat's command (deferred, its
    type logged), then on the next tick, the frame upright, the Fight's stance leg."""
    r, sv = stand_sneaking(tmp_path)
    r.frame(zombies=[zd(1, 105.0, 200.0)], sneaking=True)
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args) == ("sneak", {}) and d["inputs"]["sneak"]["on"] is False
    assert d["inputs"]["sneak"]["deferred"] == "aim" and d["branch"] == "threat"
    r.answer()
    r.frame(zombies=[zd(1, 104.5, 200.0)])
    a = tick(r, sv)
    assert a.type == "aim" and postures(r)[-1] == ("sneak", {})


def test_no_zombie_within_sneak_r_stays_upright_and_sends_no_posture(tmp_path):
    from agent.base.planner.policies import SNEAK_R
    r, sv = sneak_rig(tmp_path, goal=ExploreToward(130, 200))
    r.frame(zombies=[zd(1, 100.0 - SNEAK_R - 1.5, 200.0, has_target=False)])
    for _ in range(3):
        tick(r, sv)
        r.answer("accepted")
        r.frame(zombies=[zd(1, 100.0 - SNEAK_R - 1.5, 200.0, has_target=False)])
    assert postures(r) == [] and line(tmp_path)["inputs"]["sneak"] == {"on": False, "near": 0}


def test_three_idle_zombies_at_7_5_tiles_sneak_the_goal_s_walk(tmp_path):
    """P30-D: three idle zombies 7.5 tiles off (beyond DANGER_R, too many to seek): the goal's walk runs at a walk and
    `Sneak(True)` goes on the next tick while it runs."""
    r, sv = sneak_rig(tmp_path, goal=ExploreToward(130, 200))
    sv.goals.kit.bind(r.world, r.acts)
    r.frame()
    sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
    three = [zd(i, 100.0 - 7.5, 199.0 + i, has_target=False) for i in (1, 2, 3)]
    r.frame(zombies=three)
    a = tick(r, sv)
    assert (a.type, a.args["gait"], line(tmp_path)["branch"]) == ("walkTo", "walk", "goal")
    r.answer("accepted")
    r.frame(zombies=three)
    a = tick(r, sv)
    assert (a.type, a.args) == ("sneak", {"on": True}) and line(tmp_path)["inputs"]["sneak"]["near"] == 3
    assert r.acts.current.type == "walkTo"   # the walk goes on, crouched


def test_a_flee_stands_up_first_and_runs(tmp_path):
    """P30-D: sneaking, three idle zombies at 3 tiles make the `many` flee: `Sneak(False)` in place of its leg, then its
    leg at a run whatever the flag."""
    r, sv = stand_sneaking(tmp_path)
    many = [zd(i, 103.0, 199.0 + i, has_target=False) for i in (1, 2, 3)]
    r.frame(zombies=many, sneaking=True)
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args) == ("sneak", {}) and d["inputs"]["branches"]["threat"].get("flee") == "many"
    r.answer()
    r.frame(zombies=many)
    a = tick(r, sv)
    assert a.type in ("steer", "walkTo") and a.args["gait"] == "run"


def test_a_build_without_sneak_sends_no_posture_and_logs_none(tmp_path):
    r, sv = sneak_rig(tmp_path, caps=CAPS_17)
    idle = [zd(1, 106.0, 200.0, has_target=False)]
    for _ in range(3):
        r.frame(zombies=idle)
        tick(r, sv)
        r.answer("accepted")
    assert postures(r) == [] and "sneak" not in line(tmp_path)["inputs"]


def test_with_sneak_off_no_posture_goes(tmp_path):
    r, sv = sneak_rig(tmp_path)
    sv.SNEAK = False
    idle = [zd(1, 106.0, 200.0, has_target=False)]
    for _ in range(3):
        r.frame(zombies=idle)
        tick(r, sv)
        r.answer("accepted")
    assert postures(r) == [] and "sneak" not in line(tmp_path)["inputs"]


def test_a_sneaking_walk_at_a_run_goes_at_a_walk_but_a_flee_s_keeps_its_run(tmp_path):
    """P30-D's gait: sneaking with an idle zombie near, a non-flee walk the tick sends at a run goes at the walk (the
    sneak gait); the flee's own command is never re-gaited (its want is upright: the posture goes first)."""
    from agent.base.pza1 import WalkTo
    r, sv = stand_sneaking(tmp_path)
    r.frame(zombies=[zd(1, 106.0, 200.0, has_target=False)], sneaking=True)
    sv.mode, sv.flee = None, None
    posture, cmd = sv._sneak_posture(S.Decision("threat", object(), WalkTo(104.5, 200.5, "run"), {}))
    assert posture is None and (cmd.x, cmd.y, cmd.gait) == (104.5, 200.5, "walk")
    flee = object()
    sv.flee = flee
    posture, cmd = sv._sneak_posture(S.Decision("threat", flee, WalkTo(90.5, 200.5, "run"), {}))
    assert posture.TYPE == "sneak" and posture.on is False and cmd is None


# ================================================================ P30-A: the swing close (`SWING_CLOSE`, the closeR)
def test_the_melee_carries_close_r_swing_close_r_and_zero_with_the_rule_off(tmp_path):
    """P30-A: the Fight's melee sends `closeR` SWING_CLOSE_R (1.0) with its `swing_close` rule on (Survive's
    SWING_CLOSE, in `_fight_rules`); off, 0 (the Lua's rule off: the swing at the reach, as E23's)."""
    from agent.base.planner import fight as F
    from agent.base.planner import policies as P
    from .fakemod import MELEE_CAPS
    from .test_survive_q import fr, z
    assert P.SWING_CLOSE_R == 1.0 and "swing_close" in F.FIGHT_RULES
    for on, close in ((True, 1.0), (False, 0.0)):
        r = Rig(tmp_path / str(on), caps=MELEE_CAPS)
        fr(r, [z(9, 102.0)])
        f = F.Fight(r.world, r.acts, r.clock)
        f.stance = True
        if not on:
            f.rules = f.rules - {"swing_close"}
        a = f.step()
        assert (a.type, a.args["closeR"]) == ("melee", close), on
    off = type("Off", (), {n: getattr(S.Survive, n) for n in [r.upper() for r in F.FIGHT_RULES]})()
    off.SWING_CLOSE = False
    assert "swing_close" not in S.Survive._fight_rules(off)


def test_the_maneuver_logs_the_swing_close_counts_off_its_progress(tmp_path):
    """P30-A's why: the progress line's `held` and `again` logged `swing_close` {held, pressed_again} on the
    maneuver's log (Task 4's reader)."""
    from agent.base.planner.maneuvers import Melee
    from .fakemod import MELEE_CAPS
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Melee(r.world, r.acts, r.clock, 9)
    m.progressed({"result": {"step": "stand", "d": 1.3, "swings": 1, "held": 2, "again": 1}})
    assert m.log()["swing_close"] == {"held": 2, "pressed_again": 1}
    m.progressed({"result": {"step": "stand", "d": 1.3}})
    assert "swing_close" not in m.log()


# ================================================================ P30-C: the door held (`DOOR_HELD`, `door_held.py`)
# F14 (`f_goals_15-20261105-092752`), decision lines 146 and 147: the character at (10732.5732421875, 10641.6025390625),
# 32307 chasing at (10732.5, 10642.4755859375), 0.876 then 0.906 tiles off, behind the gate's door record at
# (10732, 10642) (`{"open": false, "locked": true, "barricaded": false}`, the fence row on y 10642 blocked north and not
# hoppable, x 10729 to 10735 read); the goal ExploreToward (10727, 10645) of line 141, past the gate. The map round it
# is the test's own (the row blocked x 10729..10738 with its run's end open at x 10728, so the goal's walk goes round
# it, P25-X's read finding the way; open ground y 10634..10646, so the view's edge lies south, past the gate).
F14_GATE_ME = (10732.5732421875, 10641.6025390625)
F14_GATE_Z = (32307, 10732.5, 10642.4755859375)
LOCKED = {"open": False, "locked": True, "barricaded": False}
SHUT = {"open": False, "locked": False, "barricaded": False}


def gate_ground(fence_from=10729):
    """The gate's ground; `fence_from` the row's first blocked square (its run's open end west of it)."""
    out = []
    for x in range(10726, 10739):
        for y in range(10634, 10647):
            if y == 10642 and x >= fence_from:
                out.append(square(x, y, blockN=True, edgeN=True, door=LOCKED if x == 10732 else None))
            else:
                out.append(square(x, y))
    return out


def gate_rig(tmp_path, on=True, goal=(10727, 10645), fence_from=10729):
    from agent.base.planner.goals import ExploreToward
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(ExploreToward(*goal)))
    sv.DOOR_HELD = on
    r.scan(gate_ground(fence_from))
    r.frame(x=F14_GATE_ME[0] - 4.0, y=F14_GATE_ME[1] - 4.0)
    sv.goals.kit.bind(r.world, r.acts)
    sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
    tick(r, sv)   # the goal taken, its walk sent (line 141's)
    r.answer("accepted")
    return r, sv


def test_f14_s_chaser_behind_the_locked_gate_is_left_and_no_walk_goes_into_the_gate(tmp_path):
    """P30-C: F14's line 146: 32307 0.876 tiles off behind the locked gate: `door_held` {door (10732, 10642), kind
    "locked gate", n_behind 1, decision "leave"}; the zombie edge-marked, the goal past the gate ended `failed "door
    held"`, cooled, its target marked; on the next tick no walk goes south past the gate (the goal pending, the view's
    edge past the gate refused by the continue)."""
    r, sv = gate_rig(tmp_path)
    zid, zx, zy = F14_GATE_Z
    me = F14_GATE_ME
    r.frame(x=me[0], y=me[1], zombies=[zombie(zid, zx, zy, me=me)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["door_held"] == {"door": [10732, 10642], "kind": "locked gate", "n_behind": 1, "decision": "leave"}
    assert sv.edge_marks[zid] == ((10732, 10642, 0), "N")
    assert sv.goals.history[-1]["state"] == "failed" and sv.goals.history[-1]["reason"] == "door held"
    assert (10727, 10645) in r.world.stuck
    r.frame(x=me[0], y=me[1], zombies=[zombie(zid, zx, zy, me=me)])
    a = tick(r, sv)
    assert a is None or not (a.type == "walkTo" and a.args["y"] > 10642)
    assert "door_held" not in threat_why(tmp_path)   # logged on the tick it is decided


def test_a_goal_past_the_gate_s_line_whose_way_clears_the_fence_s_end_is_kept(tmp_path):
    """Fix 1, review-t3 M1: the leave ends only a goal whose way goes through the gate (its line meeting the gate, or
    the gate's own run of fence): a target south of the gate's line, (10726, 10642), whose line from the character
    clears the row's open end (the test's own row, blocked from x 10731) is kept running, the leave read beside it."""
    r, sv = gate_rig(tmp_path, goal=(10726, 10642), fence_from=10731)
    zid, zx, zy = F14_GATE_Z
    me = F14_GATE_ME
    r.frame(x=me[0], y=me[1], zombies=[zombie(zid, zx, zy, me=me)])
    tick(r, sv)
    assert threat_why(tmp_path)["door_held"]["decision"] == "leave"
    assert sv.goals.current is not None and sv.goals.current.running and sv.goals.history == []
    assert (10726, 10642) not in r.world.stuck


def test_with_door_held_off_the_goal_walks_on_into_the_gate_as_f14_did(tmp_path):
    r, sv = gate_rig(tmp_path, on=False)
    zid, zx, zy = F14_GATE_Z
    me = F14_GATE_ME
    r.frame(x=me[0], y=me[1], zombies=[zombie(zid, zx, zy, me=me)])
    tick(r, sv)
    assert "door_held" not in threat_why(tmp_path) and sv.goals.current is not None
    assert sv.goals.current.args() == {"x": 10727, "y": 10645}


# F14's lines 1081 to 1105 (the character on the bedroom square (10769, 10633), 32448 at (10770.400390625, 10633.5)
# 0.90 tiles off behind the door on the west edge of (10770, 10633), its record locked as PZA/1.6 reads it fail-closed:
# the reposition ran through it) in the test's own shape: a building of room squares x 10760..10769, y 10630..10636, its
# door on the west edge of the outdoor square (10770, 10633), open ground x 10770..10778.
def door_ground(door=SHUT):
    out = []
    for x in range(10760, 10779):
        for y in range(10630, 10637):
            if x <= 10769:
                out.append(square(x, y, room="bedroom", building=5))
            elif x == 10770:
                out.append(square(x, y, blockW=True, edgeW=True, door=door if y == 10633 else None))
            else:
                out.append(square(x, y))
    return out


def door_rig(tmp_path, me, zs, health=60.0, caps=None, door=SHUT):
    from .fakemod import MELEE_CAPS
    r = Rig(tmp_path, caps=MELEE_CAPS if caps is None else caps)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None))
    r.scan(door_ground(door))
    r.frame(x=me[0], y=me[1], zombies=[zombie(i, x, y, me=me) for i, x, y in zs], health=health)
    return r, sv


def test_one_zombie_behind_a_closed_door_at_3_tiles_takes_the_stance_at_the_post_then_opens_then_meets(tmp_path):
    """P30-C (F14's line 1081 in shape, the character outdoors, health 60): one zombie 3.5 tiles off inside behind the
    closed door: `door_held` {kind "door", n_behind 1, decision "stance_open"}; the stance's leg toward the post (the
    square beyond the door's outdoor square, (10771, 10633)) facing it; at the post `Interact` open on the door's
    square; the door read open with the zombie still across, the stance stands facing it; once it is through, the
    Fight's melee at it."""
    me = (10773.0, 10633.5)
    r, sv = door_rig(tmp_path, me, [(9, 10769.5, 10633.5)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert w["door_held"] == {"door": [10770, 10633], "kind": "door", "n_behind": 1, "decision": "stance_open"}
    assert (a.type, a.args["targetId"], w["door_step"], w["leg"]) == ("aim", 9, "post", "door_post")
    assert a.args["vx"] == -1.0 and a.args["vy"] == 0.0 and a.args["seconds"] == pytest.approx(0.75)
    r.answer()
    me = (10771.6, 10633.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)], health=60.0)
    a = tick(r, sv)
    assert (a.type, a.args) == ("interact", {"x": 10770, "y": 10633, "kind": "open", "filter": "all",
                                             "maxWeight": 0.0})
    r.answer()
    r.event("door", x=10770, y=10633, z=0, open=True, locked=False)
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)], health=60.0)
    a = tick(r, sv)
    assert (a.type, a.args["vx"], a.args["vy"], threat_why(tmp_path)["door_step"]) == ("aim", 0.0, 0.0, "meet")
    r.answer()
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10770.6, 10633.5, me=me)], health=60.0)
    a = tick(r, sv)
    assert a.type == "melee" and a.args["targetId"] == 9


@pytest.mark.parametrize("zs, health", [([(9, 10769.5, 10633.5), (10, 10769.2, 10633.6)], 60.0),
                                        ([(9, 10769.5, 10633.5)], 15.0)])
def test_two_behind_or_the_health_under_the_floor_leave_the_door(tmp_path, zs, health):
    """P30-C: two zombies behind the closed door, or one with the health at 15 (under FLEE_HEALTH_FLOOR 20): `leave`;
    every zombie behind edge-marked across the door's edge and the door marked held (the routes' wall)."""
    me = (10773.0, 10633.5)
    r, sv = door_rig(tmp_path, me, zs, health=health)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["door_held"] == {"door": [10770, 10633], "kind": "door", "n_behind": len(zs), "decision": "leave"}
    assert all(sv.edge_marks[i] == ((10770, 10633, 0), "W") for i, _, _ in zs)
    assert (10770, 10633, 0) in r.world.marked_doors()


def test_inside_a_locked_building_door_is_opened_on_one_zombie_as_f14_s_line_1081(tmp_path):
    """P30-C inside (F14's geometry: the character on the bedroom square, 32448 0.90 tiles off outside behind the door
    whose record reads locked, fail-closed): a player inside unlocks it, so `stance_open`, the inside hold giving way;
    the post the room square one on from the threshold (10768, 10633)."""
    me = (10769.5, 10633.48828125)
    r, sv = door_rig(tmp_path, me, [(32448, 10770.400390625, 10633.5)], door=LOCKED)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert w["door_held"]["decision"] == "stance_open" and w["door_held"]["kind"] == "door"
    assert a.type == "aim" and w["post"] == [10768, 10633]


def test_inside_two_behind_leave_nothing_to_the_inside_hold(tmp_path):
    """P30-C inside: a `leave` is the inside hold's (no `door_held`, no mark): a sheltered character never walks out
    on a group at its door."""
    me = (10769.5, 10633.48828125)
    r, sv = door_rig(tmp_path, me, [(1, 10770.4, 10633.5), (2, 10771.4, 10633.5)], door=LOCKED)
    tick(r, sv)
    assert "door_held" not in threat_why(tmp_path) and not sv.edge_marks


def test_a_window_between_is_left(tmp_path):
    """P30-C: a zombie behind a window (F14's 32308, lines 281 to 315, 2.005 tiles off) is a `leave` outdoors."""
    from agent.base.planner.door_held import portal_between
    r = Rig(tmp_path)
    r.scan([square(10770, 10633, blockW=True, edgeW=True, window=LOCKED), square(10769, 10633, room="kitchen",
                                                                              building=5)])
    r.frame(x=10770.5, y=10633.5)
    assert portal_between(r.world, (10770.5, 10633.5), (10769.2, 10633.5)) == (((10770, 10633, 0), "W"), "window")


# ================================================================ P30-E: the still read (`STILL`, `still.ThreatStill`)
# F14 (`f_goals_15-20261105-092752`), decision lines 281 to 315: the melee stood out of reach at 32308, 2.005 tiles off
# (its progress lines' d 2.0050714015960693), the character at (10743.74, 10638.49), for 16.5 s. The fixture is the
# shape on open ground (the window F14's zombie stood behind is P30-C's `leave` now), the zombie chasing and not coming,
# the health 60, a tick 0.5 s.
F14_STILL_D = 2.0050714015960693


def still_rig(tmp_path, zs, health=60.0):
    from .fakemod import MELEE_CAPS
    r = Rig(tmp_path, caps=MELEE_CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None))
    r.scan(grid(90, 115, 190, 210))
    return r, sv


def stand_on(r, sv, ticks, me=(100.0, 200.0), zs=((32308, 100.0 + F14_STILL_D, 200.0, True),), health=60.0):
    """`ticks` planner ticks 0.5 s apart, each frame the character at `me` and the zombies `zs` ((id, x, y,
    chasing)); every send answered accepted, a melee with its `stand` progress line. The last action and the threat
    why."""
    a = None
    for _ in range(ticks):
        recs = [dict(zombie(zid, x, y, me=me), hasTarget=chasing) for zid, x, y, chasing in zs]
        r.frame(x=me[0], y=me[1], zombies=recs, health=health)
        a = tick(r, sv)
        if a is not None:
            r.answer("accepted")
            if a.type == "melee":
                r.fake.act(a.aid, "progress", "melee", result={"step": "stand", "d": F14_STILL_D})
                r.pump()
        r.advance(0.5)
    return a, threat_why(r.dir)


def test_f14_s_melee_standing_out_of_reach_for_6_s_turns_into_the_stance_s_approach(tmp_path):
    """P30-E: F14's shape: the melee standing at 32308 2.005 tiles off, the character unmoved, the distance steady:
    at STILL_S (6 s) the read resolves `approach` (alone within DANGER_R, health 60), the stance's leg toward it (the
    Fight's `toward` leg), logged `still` {target, d, resolved}; before it, the melee stands."""
    from agent.base.planner.policies import STILL_S
    r, sv = still_rig(tmp_path, ())
    n = int(STILL_S / 0.5)
    a, w = stand_on(r, sv, n)
    assert "still" not in w and any(x.type == "melee" for x in r.acts.history)
    a, w = stand_on(r, sv, 1, me=(100.0, 200.0))
    assert w["still"] == {"target": 32308, "d": F14_STILL_D, "resolved": "approach"}
    assert a is not None and a.type in ("aim", "walkTo") and (a.args.get("vx", 1.0) > 0.0 or a.args.get("x", 0) > 100)


def test_the_same_with_a_second_zombie_within_danger_r_turns_into_the_goal_s_walk(tmp_path):
    """P30-E: a second zombie 5 tiles off (within DANGER_R, the test's own): `goal`: the still zombie left (unreachable
    for UNREACHABLE_S), the threat branch passing, its why `still` {resolved "goal"} with the held count."""
    from agent.base.planner.policies import STILL_S
    r, sv = still_rig(tmp_path, ())
    zs = ((32308, 100.0 + F14_STILL_D, 200.0, True), (2, 100.0, 205.0, False))
    a, w = stand_on(r, sv, int(STILL_S / 0.5) + 1, zs=zs)
    row = last(tmp_path)
    assert w == {"still": {"target": 32308, "d": F14_STILL_D, "resolved": "goal"}, "held": 2}
    assert row["branch"] != "threat" and sv.mode is None and sv.unreachable[32308] > r.clock()


def test_the_character_moving_reads_no_still(tmp_path):
    """P30-E's falsifier: the character and the zombie moving together (the distance steady, the character 0.3 tiles a
    tick): no `still` in 8 s."""
    r, sv = still_rig(tmp_path, ())
    for k in range(16):
        y = 200.0 + 0.3 * k
        a, w = stand_on(r, sv, 1, me=(100.0, y), zs=((32308, 100.0 + F14_STILL_D, y, True),))
        assert "still" not in w, k


def test_a_chaser_closing_with_the_character_unmoved_reads_no_still(tmp_path):
    """P30-E's distance test: a chaser closing from 5.5 tiles at 0.15 a tick (the character unmoved) reads no `still`
    in 7 s (its distance falls past STILL_DRIFT_R)."""
    r, sv = still_rig(tmp_path, ())
    for i in range(14):
        a, w = stand_on(r, sv, 1, zs=((7, 105.5 - 0.15 * i, 200.0, True),))
        assert "still" not in w, i


def test_with_still_off_the_melee_stands_on(tmp_path):
    from agent.base.planner.policies import STILL_S
    r, sv = still_rig(tmp_path, ())
    sv.STILL = False
    a, w = stand_on(r, sv, int(STILL_S / 0.5) + 4)
    assert "still" not in w and sv.mode == "fight"


# ================================================================ P30-F: the dressing under a fast bleed (`DRESS_RIDE`)
# E23 (`e_day_23-20261105-095110`): the bite at game minute 594 bled part 9 from 98.43 to 55.45 by game minute 597
# (about 14 a game minute; the body's health 98.90239715576172 to 49.206119537353516 over 3.7356948852539062 game
# minutes, #4648); the riding bandage a44 (decision line 241) was superseded by the flee's next steer a45 (line 245),
# a46 (line 248) by its walk a47 (line 252), a49 (line 254) landed. The fixture is the shape with
# `test_survive_g.flee_leg_rig`'s `health` flee (health 30, `LOW_FIGHT` and `HEALTH_NEAR` off there): the flee's leg
# from a chaser 5.5 tiles off, the ride started with it 7 tiles off (beyond RIDE_R), then the leg's end with the chaser
# at `x` tiles and the part's health falling `fall` a game minute (a tick a tenth of a game minute).
def fast_bleed(tmp_path, x, fall, ride_on=True):
    from .test_survive_g import care_frame, hold, part
    from agent.base.planner import care as C
    from .test_survive import make
    r, sv = make(tmp_path)
    sv.LOW_FIGHT, sv.HEALTH_NEAR, sv.DRESS_RIDE = False, False, ride_on
    hold(r, 10, "Base.Bandage")
    h = [80.0]

    def frame(zx, gm):
        care_frame(r, [part(6, h=h[0], bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 100.0 + zx, 200.0)],
                   health=30.0, game_min=gm)
    frame(5.5, 600.0)
    leg = tick(r, sv)
    assert leg.type == "steer" and threat_why(tmp_path)["flee"] == "health"
    r.answer("progress")
    h[0] -= fall * 0.1
    frame(7.0, 600.1)
    ride = tick(r, sv)
    assert (ride.type, ride.args) == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})
    r.fake.act(ride.aid, "accepted", "bandage")
    r.fake.act(leg.aid, "done", "steer", result={})
    r.pump()
    h[0] -= fall * 0.2
    frame(x, 600.3)
    assert C.RIDE_R < 7.0
    return r, sv, ride, tick(r, sv)


def test_e23_s_fast_bleed_rides_through_the_flee_from_a_chaser_at_5_tiles(tmp_path):
    """P30-F: the part's health falling 13 a game minute, the leg ended with the chaser 5 tiles off (within DANGER_R,
    beyond KEEP_R): the flee sends no new leg, logged `dress_ride` {part 6, rate 13}; the dressing runs on."""
    r, sv, ride, a = fast_bleed(tmp_path, 5.0, 13.0)
    w = threat_why(tmp_path)
    assert a is None and w["flee"] == "health" and w["dress_ride"]["part"] == 6
    assert w["dress_ride"]["rate"] == pytest.approx(13.0) and r.acts.current is ride


def test_a_fast_bleed_with_the_chaser_within_keep_r_is_superseded_by_the_flee(tmp_path):
    from agent.base.planner.policies import KEEP_R
    r, sv, ride, a = fast_bleed(tmp_path, KEEP_R - 0.5, 13.0)
    assert (a.type, a.args["gait"]) == ("steer", "run") and "dress_ride" not in threat_why(tmp_path)


def test_a_slow_bleed_is_superseded_as_under_p29_d(tmp_path):
    """P30-F's rate test: the part's health falling 1 a game minute (under BLEED_FAST), the chaser 5 tiles off
    (within DANGER_R): the flee's steer supersedes the dressing, as P29-D left it."""
    r, sv, ride, a = fast_bleed(tmp_path, 5.0, 1.0)
    assert (a.type, a.args["gait"]) == ("steer", "run") and "dress_ride" not in threat_why(tmp_path)


def test_with_dress_ride_off_the_fast_bleed_is_superseded_as_e23_s_were(tmp_path):
    r, sv, ride, a = fast_bleed(tmp_path, 5.0, 13.0, ride_on=False)
    assert (a.type, a.args["gait"]) == ("steer", "run") and "dress_ride" not in threat_why(tmp_path)


def test_the_bleed_rate_reads_the_kept_samples_and_none_under_their_span(tmp_path):
    """`CareYield._bleed_rate`: the fall a game minute from the oldest kept sample to this tick's; None under
    BLEED_SPAN_MIN of samples; a sample older than BLEED_WINDOW_MIN dropped."""
    from agent.base.planner.policies import BLEED_SPAN_MIN, BLEED_WINDOW_MIN
    from .test_survive_g import care_frame, part
    from .test_survive import make
    r, sv = make(tmp_path)
    for gm, h in ((600.0, 90.0), (600.1, 89.0)):
        care_frame(r, [part(6, h=h)], game_min=gm)
        sv._read_bleed()
    assert BLEED_SPAN_MIN > 0.1 and sv._bleed_rate(6) is None
    care_frame(r, [part(6, h=86.0)], game_min=600.4)
    sv._read_bleed()
    assert sv._bleed_rate(6) == pytest.approx(10.0)
    care_frame(r, [part(6, h=80.0)], game_min=600.0 + BLEED_WINDOW_MIN + 0.3)
    sv._read_bleed()
    assert [s[1] for s in sv._part_h[6]] == [86.0, 80.0] and sv._bleed_rate(6) == pytest.approx(6.0 / 0.9)
