"""Plan 35 Task 2 (the footwork; the spec `docs/superpowers/specs/2026-11-10-plan-35-the-footwork-design.md` §§ 3.2 and
3.3): the planner holds the engagement, with no switch since Task 8 (the deletion):

- the work (`dispatch.FightDispatch._work_inputs`): every melee carries its `work` arguments (PZA/1.13, Plan 35 Task 1:
  workR WORK_R, crawlerR WORK_CRAWLER_R, bandLo WORK_BAND_LO, the withdraw bias, floorHealth FLEE_HEALTH, pile true),
  whatever the hello's mod;
- the hold (`dispatch.FightDispatch._engaged`, `threat.Threat._engage_holds`): the running melee with `work` holds
  against the Fight's give-ways (the crawler first's, the pair's re-pin) and the threat branch's rows (the drag guard,
  the `many` flee, the care's commitment), logged `engage_hold` {rule} on the threat rows; the reflex meets the pile
  and the crawlers; the hand-backs `floor` and `clear` give the next choose to the ladder; under FLEE_HEALTH the rows
  run as before;
- the withdraw: the fighting retreat's heading (`Fight.retreat`) is the withdraw bias with GROUP_LEAVE_N or more
  standing within GROUP_ENTRY_R (`Fight.group_n`), re-sent only once it leaves its WITHDRAW_RESEND_DEG sector.

Every fixture is synthetic (shapes of the Plan 34 trials and the spec's § 1 probe, never a replay), the fake mod. Task 8
dropped the switch-off arms (the Plan 33/34 answers the hold replaced) with the rules they pinned."""
import math

import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers import Melee
from agent.base.planner.maneuvers.melee import MeleeInputs, WorkInputs, withdraw_sector
from agent.base.world import World

from .fakemod import MELEE_CAPS
from .test_policies import Rig
from .test_survive import last, threat_why, tick
from .test_survive_ak import ME, WEST_V, zm
from .test_survive_an import SMOKE, SMOKE_ME, accept, sz
from .test_survive_g import care_frame, hold, part
from .test_survive_q import z

WORK_ARGS = {"workR": 3.5, "crawlerR": 1.2, "bandLo": 0.4, "floorHealth": 40.0, "pile": True}   # the spec's values
WORK_KEYS = ("workR", "crawlerR", "bandLo", "withdrawX", "withdrawY", "floorHealth", "pile")


def heading(deg):
    return (math.cos(math.radians(deg)), math.sin(math.radians(deg)))


def rig(tmp_path, mod="1.13", caps=MELEE_CAPS):
    """A Rig whose hello announces `mod` (the fake mod's default "fake" reads no version) and `caps`."""
    r = Rig(tmp_path, caps=caps)
    r.fake.hello(mod=mod, caps=list(caps))
    r.pump()
    return r


def fight(tmp_path, zs, mod="1.13", retreat=None, target=None, group_n=0, off=(), me=ME):
    """A Fight on a `rig` at `me` over one frame of `zs`, its rules the defaults but Plan 33 Task 2's `crawler_first`
    and those in `off`, `retreat`, `group_n` and the stance set as Survive sets them, pinned on `target`."""
    r = rig(tmp_path, mod)
    r.frame(x=me[0], y=me[1], zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = f.rules - {"crawler_first"} - set(off)
    f.retreat, f.stance, f.target, f.group_n = retreat, True, target, group_n
    return r, f


def again(r, f, zs, me=ME):
    r.frame(x=me[0], y=me[1], zombies=zs)
    f.observe()


def work_of(a):
    return {k: a.args[k] for k in WORK_KEYS if k in a.args}


ONE = [zm(1, ME[0] + 1.8, ME[1])]   # one standing zombie 1.8 tiles east: the stance's enter leg, the melee's place


# ================================================================ the constants
def test_the_switches_and_the_constants():
    """Plan 35 Task 8: no T20_SWITCHES, no FOOTWORK, ENGAGE_HOLD or WITHDRAW switch and no Fight rule of their names
    (the engagement is the only behaviour), `World.mod_at_least` gone; the four constants."""
    assert not hasattr(S, "T20_SWITCHES") and "T20_SWITCHES" not in S.__all__
    assert not any(hasattr(T.Threat, n) for n in ("FOOTWORK", "ENGAGE_HOLD", "WITHDRAW"))
    assert not {"footwork", "engage_hold", "withdraw"} & set(F.FIGHT_RULES)
    assert not hasattr(World, "mod_at_least")
    assert (P.WORK_R, P.WORK_CRAWLER_R, P.WORK_BAND_LO, P.WITHDRAW_RESEND_DEG) == (3.5, 1.2, 0.4, 30.0)


# ================================================================ the work arguments
@pytest.mark.parametrize("mod", ["1.13", "1.11"])
def test_a_1_13_build_gets_the_seven_work_fields(tmp_path, mod):
    """A hello at 1.13, and (Task 8: no version gate) one at 1.11: the melee carries workR 3.5, crawlerR 1.2, bandLo
    0.4, floorHealth 40 and pile true, no withdraw (no retreat); once accepted it is the engagement."""
    r, f = fight(tmp_path, ONE, mod=mod)
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS and "withdraw" not in f.why["melee"]
    accept(r, a, "face")
    assert f._engaged() is True


def test_the_withdraw_bias_is_the_retreat_heading_with_a_group(tmp_path):
    """Under the fighting retreat (west) with GROUP_LEAVE_N standing within GROUP_ENTRY_R (`group_n` 3): withdrawX -1,
    withdrawY 0 beside the five, logged on the melee's why as `withdraw` [-1, 0]."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    assert a.type == "melee" and work_of(a) == dict(WORK_ARGS, withdrawX=-1.0, withdrawY=0.0)
    assert f.why["melee"]["withdraw"] == [-1.0, 0.0]


def test_no_withdraw_under_the_group_count_or_with_the_rule_off(tmp_path):
    """Two standing within GROUP_ENTRY_R: the retreat's heading is no bias (the reflex's own sum)."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=2)
    a = f.step()
    assert work_of(a) == WORK_ARGS


def test_the_work_s_behaviour_reads_the_withdraw_by_its_sector():
    """`WorkInputs.behaviour`: the withdraw heading floored to WITHDRAW_RESEND_DEG sectors (west, 180 degrees, is
    sector 6; 200 too; 215 is 7), None with none; `MeleeInputs.behaviour` without work is the 3-tuple it was."""
    assert MeleeInputs("strike", 1.5, True).behaviour() == ("meet", 1.5, True)
    assert withdraw_sector(None) is None and withdraw_sector(WEST_V) == 6
    assert withdraw_sector(heading(200)) == 6 and withdraw_sector(heading(215)) == 7
    w = WorkInputs(3.5, 1.2, 0.4, heading(200), 40.0, True)
    assert w.behaviour() == WorkInputs(3.5, 1.2, 0.4, WEST_V, 40.0, True).behaviour()
    assert w.behaviour() != WorkInputs(3.5, 1.2, 0.4, heading(215), 40.0, True).behaviour()


@pytest.mark.parametrize("turn, resend", [(200, False), (215, True)])
def test_the_withdraw_re_sends_only_past_its_sector(tmp_path, turn, resend):
    """The engaged melee under the retreat (west); the retreat turns to `turn` degrees: 20 degrees (inside the sector)
    holds and sends nothing; 35 degrees (past it) gives way and the choose re-sends the melee alone (`resend`
    "inputs", the new withdraw on the wire and the why), no ladder leg."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    accept(r, a, "face")
    f.retreat = heading(turn)
    again(r, f, ONE)
    assert f.busy() is (not resend)
    if resend:
        b = f.step()
        assert b.type == "melee" and f.why["melee"]["resend"] == "inputs"
        assert (b.args["withdrawX"], b.args["withdrawY"]) == pytest.approx(heading(turn))
        assert f.why["melee"]["withdraw"] == pytest.approx(list(heading(turn)))


def test_the_re_send_beyond_keep_r_is_the_melee_never_the_ladder_s_stand(tmp_path):
    """The engaged melee's target stepped back to 2.6 tiles (beyond KEEP_R, within MELEE_RELEASE_R), the retreat
    turned past its sector: the choose is the melee's re-send (`_engage_resend`), never a ladder leg."""
    far = [zm(1, ME[0] + 2.6, ME[1])]
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    accept(r, a, "face")
    f.retreat = heading(240)
    again(r, f, far)
    assert f.busy() is False
    b = f.step()
    assert b.type == "melee" and b.args["targetId"] == 1 and f.why["melee"]["resend"] == "inputs"


def test_no_withdraw_re_send_while_a_press_is_in_flight(tmp_path):
    """The retreat turned past the sector while the melee's swing is in flight: it holds (its result read first)."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    accept(r, a, "swing")
    f.retreat = heading(240)
    again(r, f, ONE)
    assert f.busy() is True


# ================================================================ the hold at the dispatch point
CROWD = [zm(1, ME[0] + 0.5, ME[1]), zm(2, ME[0], ME[1] + 0.6), zm(3, ME[0] - 0.8, ME[1])]   # three within 0.9


@pytest.mark.parametrize("mod", ["1.13", "1.11"])
def test_the_crowd_gate_is_off_under_the_engagement(tmp_path, mod):
    """Three standing within 0.9 tiles (the Lua's K.MELEE_CROWD_R): the melee goes with `pile` (the reflex meets the
    pile) whatever the hello's mod; Task 8 deleted the crowd gate (`_crowded`)."""
    r, f = fight(tmp_path, CROWD, mod=mod, target=1)
    a = f.step()
    assert a.type == "melee" and a.args["pile"] is True


def test_the_smoke_frame_s_crawlers_take_the_melee_with_work_not_the_back_leg(tmp_path):
    """The smoke trial's frame (two crawlers within 1.2 tiles beside the standing 9128): the melee at 9128 with `work`
    (the reflex steps off the crawlers; Task 8 deleted Plan 34 fix B's back leg)."""
    r, f = fight(tmp_path, SMOKE, me=SMOKE_ME)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9128) and work_of(a) == WORK_ARGS


# ================================================================ the hold in the Fight's busy
def test_a_crawler_arriving_at_the_engaged_melee_is_held(tmp_path):
    """A crawler arriving at 1.1 tiles beside a running strike melee whose last step is `face`: engaged, it holds and
    nothing is sent (the reflex steps off the crawlers)."""
    first = [sz(2, SMOKE_ME[0] + 1.5, SMOKE_ME[1]), sz(3, SMOKE_ME[0], SMOKE_ME[1] + 1.6, crawler=True)]
    r, f = fight(tmp_path, first, me=SMOKE_ME)
    a = f.step()
    accept(r, a, "face")
    again(r, f, first + [sz(4, SMOKE_ME[0] - 1.1, SMOKE_ME[1], crawler=True)], me=SMOKE_ME)
    assert f.busy() is True


def test_a_standing_zombie_behind_the_engaged_melee_takes_no_break(tmp_path):
    """Under the retreat (west) a standing zombie comes 1.3 tiles south of the engaged strike melee at 1: it holds (the
    reflex steps back between its presses; Task 8 deleted RETREAT_MELEE's break)."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    accept(r, a, "face")
    again(r, f, ONE + [zm(2, ME[0], ME[1] + 1.3)])
    assert f.busy() is True


def test_the_pair_s_re_pin_never_cuts_the_engaged_melee(tmp_path):
    """A second standing zombie comes 0.9 tiles off, nearer than the melee's target at 1.8 by more than PAIR_SWITCH_R:
    engaged, the melee holds whatever its pin (the reflex re-pins)."""
    r, f = fight(tmp_path, ONE)
    a = f.step()
    accept(r, a, "face")
    again(r, f, ONE + [zm(2, ME[0], ME[1] - 0.9)])
    assert f.busy() is True


# ================================================================ fix 5: the corner Fight and the point-blank legs
def test_the_corner_fight_dispatches_the_melee_with_work(tmp_path):
    """Plan 35 fix 5 (the street-1 trial `x_trial-ladder-20261110-095321`, decision lines 152 to 161: the corner's
    Fight sent raw attacks and a shove at 32487 and 32488 at 0.45 to 0.66 tiles): two standing at 0.5 tiles corner the
    character (`cornered`, a `walk` corner): the corner Fight sends the melee with `work` at its pin, logged
    `engage_dispatch` {from "corner"} (Task 8 deleted the corner's raw `attack`)."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    r.frame(zombies=[z(1, 100.5), z(2, 100.0, 200.5)])
    tick(r, sv)
    why = threat_why(tmp_path)
    a = r.acts.history[-1]
    assert why["cornered"] == 1
    assert a.type == "melee" and work_of(a) == WORK_ARGS and why["melee"]["engage_dispatch"] == {"from": "corner"}


def test_a_point_blank_fight_s_circle_leg_is_the_melee(tmp_path):
    """Plan 35 fix 5 (the same trial's lines 178 to 219: the Fight kept from the corner, `point_blank` still set, sent
    its wounded backpedal's circling `back` legs as aims at 0.74 to 1.4 tiles): a Fight with `point_blank` whose ladder
    answers the circle leg at 1.2 tiles (the arms' pain 40.8, `wounded`): the melee with `work`, logged
    `engage_dispatch` {from "point_blank_leg"}."""
    r = rig(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + 1.2, ME[1])], wounds={"armPain": 40.8})
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = f.rules - {"crawler_first"}
    f.stance, f.point_blank, f.target = True, True, 1
    a = f.step()
    assert f.why["leg"] == "back" and "circle" in f.why and "wounded" in f.why
    assert a.type == "melee" and work_of(a) == WORK_ARGS
    assert f.why["melee"]["engage_dispatch"] == {"from": "point_blank_leg"}


def test_a_leg_melee_legs_lacks_is_a_dispatch_point_under_the_engagement(tmp_path):
    """Plan 35 fix 5 (2), tested at the method directly (no planner-level case found sends a leg outside MELEE_LEGS at
    a pin within KEEP_R; P26-7f): `_melee_mode` at an aim whose why reads leg `toward` at a standing pin 2.0 tiles off:
    the strike mode, `engage_dispatch` source "point_blank_leg"."""
    from agent.base.pza1 import Aim
    r, f = fight(tmp_path, [zm(1, ME[0] + 2.0, ME[1])], target=1)
    f.why = {"leg": "toward", "target": 1}
    mode = f._melee_mode(Aim(1.0, 0.0, P.AIM_LEG_S, targetId=1))
    assert mode == "strike" and f._m_from == "point_blank_leg"


# ================================================================ fix 6: an approach walk gives way within KEEP_R
CHASERS = [zm(1, ME[0] + 7.96, ME[1]), zm(2, ME[0] + 9.0, ME[1] + 1.0), zm(3, ME[0] + 9.9, ME[1] - 1.0)]   # line 25


def walking(tmp_path):
    """The arena trial's line 25 (`x_trial-ladder-20261110-100118`): the Fight out of the stance (three chasers over
    MAX_FIGHT) pinned on 1 at 7.96 tiles sends its approach walk (a9), accepted."""
    r, f = fight(tmp_path, CHASERS, target=1)
    f.stance = False
    a = f.step()
    assert a.type == "walkTo" and f.why["leg"] == "walk"
    accept(r, a)
    return r, f, a


def test_an_approach_walk_gives_way_to_the_melee_at_a_pin_within_keep_r(tmp_path):
    """Plan 35 fix 6 (lines 25 to 42: a9 held 16 s with 3648 and 3651 at 0.3 to 0.8 tiles, six bites): the walk
    running, the pin come to 0.5 tiles: `busy` gives way and the melee with `work` goes at the pin."""
    r, f, a = walking(tmp_path)
    again(r, f, [zm(1, ME[0] + 0.5, ME[1]), zm(2, ME[0] + 0.8, ME[1] + 0.3), CHASERS[2]])
    assert f.busy() is False
    b = f.step()
    assert (b.type, b.args["targetId"]) == ("melee", 1) and work_of(b) == WORK_ARGS


def test_a_walk_at_a_pin_beyond_reach_within_keep_r_is_the_melee(tmp_path):
    """The pin at 2.3 tiles (beyond FIGHT_REACH, within KEEP_R) and not chasing (so no chaser stance's leg): the walk
    gives way and the ladder's next approach walk is the melee in its place, logged `engage_dispatch` {from "walk"}."""
    r, f, a = walking(tmp_path)
    again(r, f, [zm(1, ME[0] + 2.3, ME[1], hasTarget=False), CHASERS[1], CHASERS[2]])
    assert f.busy() is False
    b = f.step()
    assert b.type == "melee" and f.why["ladder"] == "attack"
    assert f.why["melee"]["engage_dispatch"] == {"from": "walk"}


def test_a_walk_at_a_pin_beyond_keep_r_holds(tmp_path):
    """The pin come to 3.0 tiles (beyond KEEP_R): the walk holds as before."""
    r, f, a = walking(tmp_path)
    again(r, f, [zm(1, ME[0] + 3.0, ME[1]), CHASERS[1], CHASERS[2]])
    assert f.busy() is True


# ================================================================ fix 7: the door fight and the doorway stand
def test_the_door_fight_dispatches_the_melee_with_work(tmp_path):
    """Plan 35 fix 7 (the trial `x_trial-ladder-20261110-104053`, decision lines 337 to 357: the sheltered door fight's
    raw attacks at 22774 and 22776 at 0.42 to 0.76 tiles): a Fight with `only` {1} (the door's targets), its pin at 0.6
    tiles: the melee with `work`, logged `engage_dispatch` {from "door"}."""
    r, f = fight(tmp_path, [zm(1, ME[0] + 0.6, ME[1])], target=1)
    f.only = {1}
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS and f.why["melee"]["engage_dispatch"] == {"from": "door"}


def test_the_door_fight_never_sends_the_melee_outside_only(tmp_path):
    """The `only` set restricts the target: a melee whose reflex re-pinned to 2, outside `only` {1}, is retired (`busy`
    False) and the next choose sends a new melee at the pin 1; `_melee_mode` refuses a command at a zombie outside
    it."""
    from agent.base.pza1 import Attack
    zs = [zm(1, ME[0] + 0.6, ME[1]), zm(2, ME[0], ME[1] + 0.7)]
    r, f = fight(tmp_path, zs, target=1)
    f.only = {1}
    a = f.step()
    assert a.type == "melee" and a.args["targetId"] == 1
    accept(r, a)
    r.fake.act(a.aid, "progress", "melee", result={"step": "repin", "target": 2})
    r.pump()
    again(r, f, zs)
    assert f.busy() is False and f.m is None
    b = f.step()
    assert (b.type, b.args["targetId"]) == ("melee", 1)
    f.target = 2
    assert f._melee_mode(Attack(2)) is None


def doorway_fight(tmp_path):
    from agent.base.planner.doorway import Doorway
    r = rig(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + 1.4, ME[1])])
    plan = {"building": 1, "doors": [(101, 200, 0)], "door_i": 0, "post": (100, 200, 0), "way": None}
    f = Doorway(r.world, r.acts, r.clock, plan)
    f.rules = f.rules - {"crawler_first"}
    return r, f


def test_the_doorway_stand_dispatches_the_melee_with_work(tmp_path):
    """Plan 35 fix 7: the doorway stand (`doorway.Doorway`) with a standing zombie 1.4 tiles off in reach (beyond
    POINT_BLANK_R: the swing): the melee with `work` in its swing's place, logged `engage_dispatch` {from "doorway"},
    held while it runs and re-sent once its inputs change (the meet spent: mode `shove`)."""
    r, f = doorway_fight(tmp_path)
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS
    assert f.why["melee"]["engage_dispatch"] == {"from": "doorway"}
    accept(r, a, "face")
    again(r, f, [zm(1, ME[0] + 1.4, ME[1])])
    assert f.busy() is True
    f.spent = ("arms",)
    assert f.busy() is False
    b = f.step()
    assert (b.type, b.args["mode"]) == ("melee", "shove") and f.why["melee"]["resend"] == "inputs"


# ================================================================ fix 8: a lost melee in KEEP_R keeps the engagement
LOST_PILE = [zm(1, ME[0] + 2.4, ME[1]), zm(2, ME[0] + 0.5, ME[1]), zm(3, ME[0], ME[1] + 0.8)]   # 25246, 25245, 25201


def lost(r, f, a, target, why="no progress"):
    """`a` ends `done` `lost` `why` with the reflex's last target `target` (its re-pin), then one observe."""
    r.fake.act(a.aid, "done", "melee", result={"end": "lost", "why": why, "kill": False, "target": target})
    r.pump()
    f.observe()


def lost_rig(tmp_path, mod="1.13", zs=LOST_PILE, scan=None):
    """The proof round's death (`x_trial-ladder-20261111-112648`, decision lines 365 to 366): under the leave's retreat
    the Fight's melee at 1 (2.4 tiles), its reflex re-pinned to 2 (0.5 tiles, lunging), 3 at 0.8; the melee accepted,
    its progress line naming the re-pin, `busy` read once as Survive reads it."""
    r = rig(tmp_path, mod)
    if scan:
        r.scan(scan)
    r.frame(x=ME[0], y=ME[1], zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = f.rules - {"crawler_first"}
    f.retreat, f.stance, f.target, f.group_n = WEST_V, True, 1, 3
    f.m = Melee(r.world, r.acts, r.clock, 1)
    f.m.inputs = f._melee_inputs("strike", r.world.zombies[1])
    a = f.send(f.m.step())
    accept(r, a)
    r.fake.act(a.aid, "progress", "melee", result={"step": "repin", "target": 2})
    r.pump()
    f.observe()
    f.busy()   # Survive's read of the running melee
    return r, f, a


def test_a_lost_melee_at_point_blank_marks_it_and_keeps_the_engagement_on_the_next(tmp_path):
    """Plan 35 fixes 8 and 8b (rule 1; rule 2's point-blank lift dropped by the controller's ruling on the fix 8
    report, concern 1): the melee ends `lost` `no progress` with its reflex on 2 at 0.5 tiles: 2 (the stalled zombie,
    `span_id`) is marked whatever its distance, 1 (the planner's pin the reflex left) is not, `_m_ladder` is not set,
    and the next choose sends the melee with `work` at 3 (0.8 tiles), logged
    `engage_dispatch` {from "lost"}."""
    r, f, a = lost_rig(tmp_path)
    lost(r, f, a, 2)
    assert f.marked() == {2} and f._m_ladder is False
    b = f.step()
    assert (b.type, b.args["targetId"]) == ("melee", 3)
    assert work_of(b) == dict(WORK_ARGS, withdrawX=-1.0, withdrawY=0.0)
    assert f.why["melee"]["engage_dispatch"] == {"from": "lost"} and f.why["melee_end"]["why"] == "no progress"


def test_a_lost_melee_on_the_one_zombie_in_contact_presses_it_again(tmp_path):
    """Plan 35 fix 8b: the stalled 2 at 0.5 is the only standing zombie within KEEP_R (1 at 3.0): marked, but P27-N's
    point-blank pin takes it as before (the Lua's stall and re-pin own it): the next melee goes at 2, logged
    `engage_dispatch` {from "lost"}."""
    r, f, a = lost_rig(tmp_path, zs=[zm(1, ME[0] + 3.0, ME[1]), zm(2, ME[0] + 0.5, ME[1])])
    lost(r, f, a, 2)
    assert f.marked() == {2} and f._m_ladder is False
    b = f.step()
    assert (b.type, b.args["targetId"]) == ("melee", 2) and f.why["melee"]["engage_dispatch"] == {"from": "lost"}


def test_a_kill_end_in_contact_sends_the_melee_not_the_regain_back_leg(tmp_path):
    """Plan 35 fix 8b (concern 3 of the fix 8 report): the melee ends `kill` on 2 (at 0.5) with 3 standing at 0.8: the
    next choose sends the melee with `work` at 3, logged `engage_dispatch` {from "kill"} (Task 8 deleted the regain's
    back leg the name recalls)."""
    r, f, a = lost_rig(tmp_path)
    r.fake.act(a.aid, "done", "melee", result={"end": "kill", "kill": True, "target": 2})
    r.pump()
    again(r, f, [LOST_PILE[0], LOST_PILE[2]])
    b = f.step()
    assert (b.type, b.args["targetId"]) == ("melee", 3) and f.why["melee"]["engage_dispatch"] == {"from": "kill"}


@pytest.mark.parametrize("mod", ["1.13", "1.11"])
def test_no_unreachable_flee_from_a_marked_zombie_lunging_in_contact(tmp_path, mod):
    """Plan 35 fix 8b (the street-1 trial `x_trial-ladder-20261111-114439`, decision lines 306 to 313: 27900, the one
    standing zombie left, marked unreachable and lunging at 1.11 tiles; the threat plan fled `unreachable` to a shelter
    and the bite landed under the walk): the mark of the nearest standing zombie within KEEP_R is lifted and the Fight
    dispatches the melee with `work` at it, logged `engage_dispatch` {from "unreachable", target 1} on the threat why,
    whatever the hello's mod (Task 8: no gate)."""
    r = rig(tmp_path, mod)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    sv.unreachable[1] = r.clock() + P.UNREACHABLE_S
    r.frame(zombies=[z(1, 101.1)])
    tick(r, sv)
    why = threat_why(tmp_path)
    a = r.acts.history[-1]
    assert a.type == "melee" and "workR" in a.args and "flee" not in why
    assert why["engage_dispatch"] == {"from": "unreachable", "target": 1} and 1 not in sv.unreachable


def test_a_lost_melee_with_nobody_within_keep_r_gives_the_choose_to_the_ladder(tmp_path):
    """Rule 3: `lost` `no progress` with no standing zombie within KEEP_R (the reflex's 2 at 2.6, the rest beyond):
    the mark as today (on the reflex's 2, beyond POINT_BLANK_R) and `_m_ladder` set."""
    zs = [zm(1, ME[0] + 2.7, ME[1]), zm(2, ME[0] + 2.6, ME[1] + 0.3), zm(3, ME[0] - 4.0, ME[1])]
    r, f, a = lost_rig(tmp_path, zs=zs)
    lost(r, f, a, 2)
    assert 2 in f.marked() and f._m_ladder is True


# ================================================================ the hand-backs
def done(r, a, why, **res):
    r.fake.act(a.aid, "done", "melee", result=dict({"end": "handback", "why": why, "kill": False}, **res))
    r.pump()


@pytest.mark.parametrize("why", ["floor", "clear"])
def test_the_floor_and_clear_hand_backs_give_the_next_choose_to_the_ladder(tmp_path, why):
    """`done handback` why `floor` (the body at the floor) or `clear` (nothing left to meet): the engagement ends, the
    next choose is the ladder's (no melee, and the crowd's re-pin, `_melee_crowd`, never read), logged `melee_end` {end
    "handback", why}; nothing is marked unreachable."""
    r, f = fight(tmp_path, ONE)
    a = f.step()
    accept(r, a, "face")
    f._melee_crowd = lambda m: pytest.fail("a work hand-back re-pinned")
    done(r, a, why, id=2, d=1.0)
    again(r, f, ONE)
    assert f._engaged() is False and f.busy() is False
    b = f.step()
    assert b.type != "melee" and f.target == 1 and not f.marked()
    assert f.why["melee_end"]["end"] == "handback" and f.why["melee_end"]["why"] == why


# ================================================================ the hold in the threat branch
GROUP = [z(1, 101.8), z(2, 100.0, 202.3), z(3, 100.0, 197.4)]   # the target 1.8 east, two more at 2.3 and 2.6


def engaged(tmp_path, mod="1.13", leave=False, scan=None, **frame):
    """A Survive (GROUP_LEAVE `leave`, off as `test_survive.make` sets it) on a `rig` announcing `mod`, `scan` squares
    scanned: its first line fights the one zombie 1.8 tiles east with the melee (accepted, its last
    step `face`); the line after reads `frame`."""
    r = rig(tmp_path, mod)
    if scan:
        r.scan(scan)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = leave
    r.frame(zombies=[z(1, 101.8)])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee" and sv.mode == "fight"
    accept(r, a, "face")
    r.advance(0.5)
    r.frame(**frame)
    tick(r, sv)
    return r, sv, a


def test_a_many_read_at_the_engaged_melee_is_held(tmp_path):
    """Three standing within DANGER_R, the nearest the melee's target at 1.8 (beyond POINT_BLANK_OVER_R): engaged, the
    threat branch holds the melee (no send), logged `engage_hold` {rule "many"}; with ENGAGE_HOLD off, the `many` flee
    as before (its run steer superseding the melee)."""
    r, sv, a = engaged(tmp_path, zombies=GROUP)
    why = threat_why(tmp_path)
    assert r.acts.history[-1] is a and why.get("fight") is True and why["engage_hold"] == {"rule": "many"}
    assert why["holding"] == a.aid


DRAGGED = [z(1, 101.8), z(2, 100.0, 200.6), z(3, 99.3, 200.0)]   # three standing round the player


def test_the_drag_guard_at_the_engaged_melee_is_held_for_one_tick(tmp_path):
    """The frame reads two attackers (the drag guard's DRAG_DOWN_N - 1) on one threat tick only (the count flickers
    frame to frame): engaged, the melee holds (the reflex meets the pile), logged `engage_hold` {rule "drag"}, no
    `engage_yield`; with ENGAGE_HOLD off, the guard's run (`group` "drag", the pin)."""
    r, sv, a = engaged(tmp_path, zombies=DRAGGED, attackers=2)
    why = threat_why(tmp_path)
    assert "engage_yield" not in why
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "drag"} and "group" not in why


def test_two_attackers_on_two_ticks_keep_the_hold(tmp_path):
    """Plan 35 fix 4 (the controller's ruling, reversing fix 3's drag lapse; the trial `x_trial-ladder-20261110-094757`,
    decision line 191: the lapse's guard run superseded the melee holding three at 0.4 to 1.2 tiles, the first bite 0.6
    s later): a pin that two attackers on this threat tick and the one before keep the hold: engaged, the melee holds,
    logged `engage_hold` {rule "drag"}, no `engage_yield`; with ENGAGE_HOLD off, the guard as before (`group` "drag",
    the pin of the rule before Plan 35)."""
    r, sv, a = engaged(tmp_path, zombies=DRAGGED, attackers=2)
    r.advance(0.5)
    r.frame(zombies=DRAGGED, attackers=2)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert "engage_yield" not in why
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "drag"} and "group" not in why


def care_engaged(tmp_path, dist, parts):
    """`engaged`'s two lines with a rag held and `parts` on the second, the melee's target then at `dist` tiles."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    hold(r, 11, "Base.RippedSheets")
    r.frame(zombies=[z(1, 101.8)])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee"
    accept(r, a, "face")
    r.advance(0.5)
    care_frame(r, parts, zombies=[z(1, 100.0 + dist)])
    tick(r, sv)
    return r, sv, a


BLEED = [part(7, bleeding=True, bleedingTime=5.0)]
SCRATCH = [part(7, wound=True)]   # a wound that does not bleed (a scratch's Dress wanted)


def test_a_bleed_with_nobody_within_keep_r_yields_the_engagement_to_the_dressing(tmp_path):
    """Plan 35 fix 2 (the controller's ruling; Angus's dress first): part 7 bleeding, a rag held, the melee's target
    stepped back to 3.2 tiles (no standing zombie within KEEP_R; beyond CARE_HOLD_R, so the commitment yields rather
    than walks its leg): engaged, the care's commitment answers as before, its Dress's stop superseding the melee,
    logged `engage_yield` {rule "bleed"}; with ENGAGE_HOLD off (the pin of the rule before it) the same yield, no
    `engage_yield`."""
    r, sv, a = care_engaged(tmp_path, 3.2, BLEED)
    why = threat_why(tmp_path)
    assert last(tmp_path)["branch"] == "care" and r.acts.history[-1].type == "stop"
    assert why["care_commit"]["phase"] == "yield" and "engage_hold" not in why
    assert why.get("engage_yield") == {"rule": "bleed"}


def test_a_bleed_at_the_engaged_melee_s_leg_distance_takes_the_commitment_s_leg(tmp_path):
    """The same with the target at 2.6 (beyond KEEP_R, within CARE_HOLD_R): the commitment's one distance leg as before
    (Plan 32 Task 5 (c)), engaged or not; engaged, logged `engage_yield` {rule "bleed"}."""
    r, sv, a = care_engaged(tmp_path, 2.6, BLEED)
    why = threat_why(tmp_path)
    assert why["care_commit"]["phase"] == "leg" and r.acts.history[-1].type == "steer"
    assert why.get("engage_yield") == {"rule": "bleed"}


def test_a_bleed_with_a_zombie_within_keep_r_keeps_the_fight(tmp_path):
    """The bleed with the target at 1.5 (within KEEP_R): the Fight's (CARE_COMMIT's rule (a)), engaged or not: the melee
    holds, no care send, no `engage_yield` (the trial `x_trial-ladder-20261110-084643`'s lines 291 to 306)."""
    r, sv, a = care_engaged(tmp_path, 1.5, BLEED)
    why = threat_why(tmp_path)
    assert last(tmp_path)["branch"] == "threat" and r.acts.history[-1] is a and "engage_yield" not in why


def test_the_bleed_s_yield_within_keep_r_is_held(tmp_path):
    """The bleed with the target at 2.2 (within KEEP_R, beyond FIGHT_REACH): P26-D's bleed yield (`_bleed_free`) would
    dress between swings; engaged, a standing zombie within KEEP_R keeps the hold (logged `engage_hold` {rule "care"},
    no `engage_yield`); with ENGAGE_HOLD off, the bleed's yield as before (`care_yield` {why "bleed"}, the pin), the
    melee superseded (in this fixture by the goal's scan: the care sends nothing on that tick)."""
    r, sv, a = care_engaged(tmp_path, 2.2, BLEED)
    why = threat_why(tmp_path)
    assert "engage_yield" not in why
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "care"}


def test_with_no_bleed_the_care_s_commitment_at_the_engaged_melee_is_held(tmp_path):
    """A scratch (no part bleeding), the target at 3.2: engaged, the melee holds, logged `engage_hold` {rule "care"},
    no `engage_yield`; with ENGAGE_HOLD off, CARE_COMMIT's yield to the scratch's Dress (Plan 32 Task 5 (c)'s answer,
    the pin) superseding the melee."""
    r, sv, a = care_engaged(tmp_path, 3.2, SCRATCH)
    why = threat_why(tmp_path)
    assert "engage_yield" not in why
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "care"} and "care_commit" not in why


FIVE = [z(1, 101.8), z(2, 100.0, 202.3), z(3, 100.0, 197.4), z(4, 98.0, 200.0), z(5, 102.0, 202.5)]   # five standing


FOUR = FIVE[:4]


def test_above_retreat_max_n_the_leave_s_run_lapses_the_hold(tmp_path):
    """Plan 35 fix 3: GROUP_LEAVE on, five standing within GROUP_ENTRY_R (above RETREAT_MAX_N, the `run` leg's own
    count), the nearest the melee's target at 1.8: the hold lapses and the leave's run goes as before Plan 35 (the
    `many` flee), logged `engage_yield` {rule "many"}; with ENGAGE_HOLD off, the same run (Plan 33 Task 3 fix 4's
    answer, the pin), no `engage_yield`."""
    r, sv, a = engaged(tmp_path, leave=True, zombies=FIVE)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "run" and why.get("flee") == "many" and r.acts.history[-1] is not a
    assert "engage_hold" not in why and why.get("engage_yield") == {"rule": "many"}


def test_the_spent_leave_s_run_at_four_is_held(tmp_path):
    """Four standing within GROUP_ENTRY_R with the meet spent (the arms' pain 15, over STRAIN_SOFT: SPENT_LEAVE's run
    at GROUP_LEAVE_N), no drag-down read: engaged, the melee holds, logged `engage_hold` {rule "leave"}, no
    `engage_yield`; with ENGAGE_HOLD off, the leave's run (Plan 34 Task 3c's answer, the pin)."""
    r, sv, a = engaged(tmp_path, leave=True, zombies=FOUR, wounds={"armPain": 15.0})
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "run" and "engage_yield" not in why
    b = r.acts.history[-1]   # the melee kept (re-sent in mode `shove` for the spent meet), no leg
    assert b.type == "melee" and b.args["targetId"] == 1 and why["engage_hold"] == {"rule": "leave"}


def test_the_leave_strung_out_at_the_engaged_melee_is_held(tmp_path):
    """GROUP_LEAVE on: three standing take the leave (its retreat, the Fight's: the melee re-sent with the withdraw
    bias); then a line reads two within GROUP_ENTRY_R: the leave ends `strung` on it (Task 8 deleted STRUNG_HOLD's
    held lines) and the engaged melee is re-sent without the bias, no leg in its place."""
    trio = GROUP
    r, sv, a = engaged(tmp_path, leave=True, zombies=trio)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "retreat" and why.get("fight") is True
    b = r.acts.history[-1]
    assert b.type == "melee" and "withdrawX" in b.args
    accept(r, b, "face")
    r.advance(0.5)
    r.frame(zombies=trio[:2] + [z(3, 100.0, 210.0)])   # the third 10 tiles off, beyond GROUP_ENTRY_R
    tick(r, sv)
    why = threat_why(tmp_path)
    assert sv.leave is None and why["group_leave"]["end"] == "strung"
    c = r.acts.history[-1]   # the melee re-sent with no withdraw (two standing): no leg in its place
    assert c.type == "melee" and "withdrawX" not in c.args


def test_a_corner_at_the_engaged_melee_inside_is_held(tmp_path):
    """On a room square the melee's target closes to 0.8 tiles (within CORNERED_R): engaged, no corner Fight (the
    reflex meets it), logged `engage_hold` {rule "cornered"}; with ENGAGE_HOLD off, the `inside` corner's Fight (P23-AJ
    2's answer) superseding the melee."""
    from .test_policies import grid
    r, sv, a = engaged(tmp_path, scan=grid(96, 104, 196, 204, at={(x, y): {"room": "kitchen", "building": 1}
                                                                      for x in range(96, 105)
                                                                      for y in range(196, 205)}),
                       zombies=[z(1, 100.8)])
    why = threat_why(tmp_path)
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "cornered"} and "cornered" not in why


def test_no_still_read_over_the_engaged_melee(tmp_path, monkeypatch):
    """The still read (P30-E: its approach leg or its pass) is never read while the melee is engaged."""
    def still(self, held, fight):
        assert not fight._engaged(), "the still read when engaged"
    monkeypatch.setattr(S.Survive, "_still_read", still)
    r, sv, a = engaged(tmp_path, zombies=[z(1, 102.0)])
    assert r.acts.history[-1] is a and threat_why(tmp_path).get("fight") is True


STEPPED = [z(1, 102.6), z(2, 100.0, 204.0)]   # the target stepped back to 2.6 (beyond KEEP_R), a second at 4.0


def test_the_pair_flee_at_the_engaged_melee_is_held(tmp_path):
    """Plan 35 fix 1 (the controller's ruling on concern 4): two standing within DANGER_R, the health 55 (under
    FLEE_HEALTH_PAIR, above the floor), the melee's target stepped back to 2.6 (beyond KEEP_R, so POINT_BLANK_FIGHT
    does not keep it): engaged, the melee holds, logged `engage_hold` {rule "pair"}; with ENGAGE_HOLD off, the Plan 23
    `pair` flee as before (the pin of the rule before it) superseding the melee."""
    r, sv, a = engaged(tmp_path, zombies=STEPPED, health=55.0)
    why = threat_why(tmp_path)
    assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "pair"} and why.get("fight") is True


def test_the_strain_flee_at_the_engaged_melee_is_held(tmp_path):
    """Plan 35 fix 1: the endurance spent (0.4, under STRAIN_ENDURANCE: the hold and a real exhaustion, two standing
    within DANGER_R), the melee's target stepped back to 2.6 (beyond KEEP_R, no wounded fight): engaged, the melee
    holds, re-sent in mode `shove` (the reflex's spent meet), logged `engage_hold` {rule "strain"}; with ENGAGE_HOLD
    off, the P24-AG `strain` flee as before (the pin of the rule before it) superseding the melee."""
    r, sv, a = engaged(tmp_path, zombies=STEPPED, endurance=0.4)
    why = threat_why(tmp_path)
    b = r.acts.history[-1]   # the same melee re-sent in mode `shove` (the hold's spent meet), no leg
    assert (b.type, b.args["targetId"], b.args["mode"]) == ("melee", 1, "shove")
    assert why["engage_hold"] == {"rule": "strain"} and why.get("fight") is True


def test_under_the_floor_the_many_flee_runs_as_before(tmp_path):
    """The many read at the engaged melee with the health at 39 (under FLEE_HEALTH, the reflex's floor): the hold gives
    way, the `many` flee as before, no `engage_hold`."""
    r, sv, a = engaged(tmp_path, zombies=GROUP, health=39.0)
    why = threat_why(tmp_path)
    assert why.get("flee") == "many" and "engage_hold" not in why and r.acts.history[-1] is not a

