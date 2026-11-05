"""Survival 26 (iteration 24, Plan 30 Task 3; the spec `2026-11-05-plan-30-the-intent-design.md` § 2 item 3): the six
rules of `survive.T14_SWITCHES`, each with its killing test, on E23's (`e_day_23-20261105-095110`), F14's
(`f_goals_15-20261105-092752`) and fabricated fixtures, each fixture's line named where it is the artifact's.

- P30-B (`GOAL_CONTINUE`, the goal runner): `test_goals.py`'s Plan 30 block; the switch here.
- P30-D (`SNEAK`, `sneak.SneakGait`): the gait near a zombie with no target, upright at a chaser, in a flee and for a
  press, the posture the tick's one command.
"""
from agent.base.planner import survive as S
from agent.base.planner.goals import ExploreToward

from .fakemod import CAPS_17
from .test_policies import Rig, grid
from .test_survive import last, tick
from .test_survive_g import Src, zd


def test_the_iteration_24_switches():
    """`survive.T14_SWITCHES`, each on `Survive` (or a class it derives) and on by default."""
    assert S.T14_SWITCHES == ("GOAL_CONTINUE", "SNEAK")
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
