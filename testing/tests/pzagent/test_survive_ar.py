"""Plan 35 Task 2 (the footwork; the spec `docs/superpowers/specs/2026-11-10-plan-35-the-footwork-design.md` §§ 3.2 and
3.3): the planner holds the engagement. `survive.T20_SWITCHES` on `threat.Threat`, each a Fight rule of its name
lower-cased:

- FOOTWORK (`dispatch.FightDispatch._work_inputs`): the melee carries its `work` arguments (PZA/1.13, Plan 35 Task 1:
  workR WORK_R, crawlerR WORK_CRAWLER_R, bandLo WORK_BAND_LO, the withdraw bias, floorHealth FLEE_HEALTH, pile true) to
  a build whose hello announces mod 1.13 or later (`World.mod_at_least`); a 1.11 hello (every golden's) sends none.
- ENGAGE_HOLD (`dispatch.FightDispatch._engaged`, `threat.Threat._engage_holds`): the running melee with `work` holds
  against the Fight's give-ways (the crawler clear, RETREAT_MELEE's break, RETREAT_REGAIN's back leg, the pair's
  re-pin) and the threat branch's rows (the drag guard, the `many` flee, the care's commitment), logged `engage_hold`
  {rule}; the crowd gate and the crawler clear's exemption are off at the dispatch point; the hand-backs `floor` and
  `clear` give the next choose to the ladder; under FLEE_HEALTH the rows run as before.
- WITHDRAW: the fighting retreat's heading (`Fight.retreat`) is the withdraw bias with GROUP_LEAVE_N or more standing
  within GROUP_ENTRY_R (`Fight.group_n`), re-sent only once it leaves its WITHDRAW_RESEND_DEG sector.

Every fixture is synthetic (shapes of the Plan 34 trials and the spec's § 1 probe, never a replay), the fake mod; each
hold is pinned with its switch off to the Plan 33/34 answer it replaces (a test of an earlier rule pinned with the
later rule's switch off)."""
import math

import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers.melee import MeleeInputs, WorkInputs, withdraw_sector
from agent.base.world import World

from .fakemod import MELEE_CAPS
from .test_policies import Rig
from .test_survive import last, threat_why, tick
from .test_survive_ak import ME, WEST_V, zm
from .test_survive_an import SMOKE, SMOKE_ME, accept, sz
from .test_survive_ap import HALF, PILE, at, progress
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


# ================================================================ the switches, the constants, the version read
def test_the_switches_and_the_constants():
    """`survive.T20_SWITCHES` after T19 in `__all__`, each on `threat.Threat` (and so `survive.Survive`) on by
    default and a Fight rule of its name lower-cased, dropped by its own switch alone; the four constants."""
    assert S.T20_SWITCHES == ("FOOTWORK", "ENGAGE_HOLD", "WITHDRAW") and "T20_SWITCHES" in S.__all__
    assert all(getattr(T.Threat, n) is True and getattr(S.Survive, n) is True for n in S.T20_SWITCHES)
    assert {"footwork", "engage_hold", "withdraw"} <= set(F.FIGHT_RULES)
    on = type("On", (), {n: getattr(S.Survive, n) for n in [r.upper() for r in F.FIGHT_RULES]})()
    every = T.Threat._fight_rules(on)
    for name in S.T20_SWITCHES:
        setattr(on, name, False)
        assert T.Threat._fight_rules(on) == every - {name.lower()}, name
        setattr(on, name, True)
    assert (P.WORK_R, P.WORK_CRAWLER_R, P.WORK_BAND_LO, P.WITHDRAW_RESEND_DEG) == (3.5, 1.2, 0.4, 30.0)


@pytest.mark.parametrize("mod, at_13, at_152", [("1.13", True, True), ("1.13.1", True, True), ("2.0", True, True),
                                                ("1.11", False, True), ("1.12.9", False, True), ("1.7", False, True),
                                                ("1.5.1", False, False), ("fake", False, False), (None, False, False)])
def test_mod_at_least_compares_the_dotted_numbers(mod, at_13, at_152):
    """`World.mod_at_least`: number by number, a missing third read as 0; False with no hello or an unparsable mod;
    `item_fields` (1.5.2 or later, ruling P25-O) is its reading at "1.5.2"."""
    w = World()
    if mod is not None:
        w.apply({"kind": "hello", "mod": mod, "caps": []})
    assert w.mod_at_least("1.13") is at_13 and w.item_fields() is at_152


# ================================================================ FOOTWORK: the work arguments
def test_a_1_11_build_gets_the_melee_with_no_work(tmp_path):
    """The goldens' builds (a hello at 1.11): the melee as before, no `work` field on the wire, `Melee.work` None, no
    engagement."""
    r, f = fight(tmp_path, ONE, mod="1.11")
    a = f.step()
    assert a.type == "melee" and work_of(a) == {} and f.m.work is None and f._engaged() is False


def test_a_1_13_build_gets_the_seven_work_fields(tmp_path):
    """A hello at 1.13: the melee carries workR 3.5, crawlerR 1.2, bandLo 0.4, floorHealth 40 and pile true, no
    withdraw (no retreat); once accepted it is the engagement."""
    r, f = fight(tmp_path, ONE)
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS and "withdraw" not in f.why["melee"]
    accept(r, a, "face")
    assert f._engaged() is True


def test_with_footwork_off_a_1_13_build_gets_no_work(tmp_path):
    """FOOTWORK off (the rule before it): the melee as before on a 1.13 build, so nothing is engaged."""
    r, f = fight(tmp_path, ONE, off=("footwork",))
    a = f.step()
    assert work_of(a) == {}
    accept(r, a, "face")
    assert f._engaged() is False


def test_the_withdraw_bias_is_the_retreat_heading_with_a_group(tmp_path):
    """Under the fighting retreat (west) with GROUP_LEAVE_N standing within GROUP_ENTRY_R (`group_n` 3): withdrawX -1,
    withdrawY 0 beside the five, logged on the melee's why as `withdraw` [-1, 0]."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3)
    a = f.step()
    assert a.type == "melee" and work_of(a) == dict(WORK_ARGS, withdrawX=-1.0, withdrawY=0.0)
    assert f.why["melee"]["withdraw"] == [-1.0, 0.0]


@pytest.mark.parametrize("group_n, off", [(2, ()), (3, ("withdraw",))])
def test_no_withdraw_under_the_group_count_or_with_the_rule_off(tmp_path, group_n, off):
    """Two standing within GROUP_ENTRY_R, or WITHDRAW off: the retreat's heading is no bias (the reflex's own sum)."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=group_n, off=off)
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
    turned past its sector: the choose is the melee's re-send (`_engage_resend`), where the ladder reads the retreat's
    stand leg beyond KEEP_R (Plan 34 RETREAT_GAP) and would supersede it."""
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


# ================================================================ ENGAGE_HOLD at the dispatch point
CROWD = [zm(1, ME[0] + 0.5, ME[1]), zm(2, ME[0], ME[1] + 0.6), zm(3, ME[0] - 0.8, ME[1])]   # three within 0.9


@pytest.mark.parametrize("mod, off, melee", [("1.13", (), True), ("1.13", ("engage_hold",), False),
                                             ("1.11", (), False)])
def test_the_crowd_gate_is_off_under_the_engagement(tmp_path, mod, off, melee):
    """Three standing within MELEE_CROWD_R: on a 1.13 build under ENGAGE_HOLD the melee goes with `pile` (the reflex
    meets the pile); with the rule off, or on a 1.11 build, the crowd gate as before (the ladder's own send, no
    melee: Plan 31 Task 15a fix 1's pin)."""
    r, f = fight(tmp_path, CROWD, mod=mod, target=1, off=off)
    a = f.step()
    assert (a.type == "melee") is melee
    if melee:
        assert a.args["pile"] is True


def test_the_smoke_frame_s_crawlers_take_the_melee_with_work_not_the_back_leg(tmp_path):
    """The smoke trial's frame (two crawlers within CRAWLER_AVOID_R beside the standing 9128): under the engagement the
    crawler clear's back leg is the melee's place (its exemption off: the reflex steps off the crawlers), the melee
    at 9128 with `work`; with ENGAGE_HOLD off, Plan 34 fix B's back leg (`test_survive_an.py`)."""
    r, f = fight(tmp_path, SMOKE, me=SMOKE_ME)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9128) and work_of(a) == WORK_ARGS
    (tmp_path / "off").mkdir()
    r2, f2 = fight(tmp_path / "off", SMOKE, me=SMOKE_ME, off=("engage_hold",))
    b = f2.step()
    assert b.type == "aim" and "crawler_clear" in f2.why


# ================================================================ ENGAGE_HOLD in the Fight's busy
@pytest.mark.parametrize("on", [True, False])
def test_a_crawler_arriving_at_the_engaged_melee_is_held(tmp_path, on):
    """`test_survive_an.py`'s crawler arriving at 1.1 tiles beside a running strike melee whose last step is `face`:
    engaged, it holds, logged `engage_hold` {rule "crawler_clear"}, and nothing is sent; with ENGAGE_HOLD off (Plan 34
    fix B's answer) it gives way and the backpedal goes."""
    first = [sz(2, SMOKE_ME[0] + 1.5, SMOKE_ME[1]), sz(3, SMOKE_ME[0], SMOKE_ME[1] + 1.6, crawler=True)]
    r, f = fight(tmp_path, first, me=SMOKE_ME, off=() if on else ("engage_hold",))
    a = f.step()
    accept(r, a, "face")
    again(r, f, first + [sz(4, SMOKE_ME[0] - 1.1, SMOKE_ME[1], crawler=True)], me=SMOKE_ME)
    assert f.busy() is on
    if on:
        assert f.why["engage_hold"] == {"rule": "crawler_clear"}
    else:
        cmd = f.choose()
        assert cmd.TYPE == "aim" and "crawler_clear" in f.why


@pytest.mark.parametrize("on", [True, False])
def test_a_standing_zombie_behind_the_engaged_melee_takes_no_break(tmp_path, on):
    """Under the retreat (west) a standing zombie comes within RETREAT_BACK_R (1.3 tiles south) of the engaged strike
    melee at 1: it holds, logged `engage_hold` {rule "retreat_melee"}; with ENGAGE_HOLD off, RETREAT_MELEE's break
    and its back leg (Plan 34 Task 3's answer)."""
    r, f = fight(tmp_path, ONE, retreat=WEST_V, group_n=3, off=() if on else ("engage_hold",))
    a = f.step()
    accept(r, a, "face")
    again(r, f, ONE + [zm(2, ME[0], ME[1] + 1.3)])
    assert f.busy() is on
    if on:
        assert f.why["engage_hold"] == {"rule": "retreat_melee"}
    else:
        b = f.step()
        assert b.type == "aim" and f.why["leg"] == "back" and "retreat_break" in f.why


@pytest.mark.parametrize("on", [True, False])
def test_the_regain_s_back_leg_never_cuts_the_engaged_melee(tmp_path, on):
    """`test_survive_ap.py`'s pile under the retreat: the point-blank press (the shove-mode melee, the meet spent)
    pressed once and resolved (`face`), the nearest at 0.5: engaged, it holds, logged `engage_hold` {rule
    "retreat_regain"}; with ENGAGE_HOLD off, RETREAT_REGAIN's back leg in its place (Plan 34 Task 3c's answer)."""
    r, f = fight(tmp_path, at(PILE), retreat=WEST_V, target=1, group_n=3, off=() if on else ("engage_hold",))
    f.spent = ("arms",)
    a = f.step()
    assert (a.type, a.args["mode"]) == ("melee", "shove") and f.why["retreat_regain"]["phase"] == "press"
    accept(r, a, "shove")
    progress(r, a, "face")
    again(r, f, at(HALF))
    assert f.busy() is on
    if on:
        assert f.why["engage_hold"] == {"rule": "retreat_regain"} and f.step() is None
    else:
        b = f.step()
        assert b.type == "aim" and f.why["retreat_regain"]["phase"] == "back"


@pytest.mark.parametrize("on", [True, False])
def test_the_pair_s_re_pin_never_cuts_the_engaged_melee(tmp_path, on):
    """A second standing zombie comes 0.9 tiles off, nearer than the melee's target at 1.8 by more than PAIR_SWITCH_R:
    engaged, the melee holds whatever its pin (the reflex re-pins); with ENGAGE_HOLD off, the pair's give-way (Plan 32
    Task 5 (b)'s answer)."""
    r, f = fight(tmp_path, ONE, off=() if on else ("engage_hold",))
    a = f.step()
    accept(r, a, "face")
    again(r, f, ONE + [zm(2, ME[0], ME[1] - 0.9)])
    assert f.busy() is on


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


# ================================================================ ENGAGE_HOLD in the threat branch
GROUP = [z(1, 101.8), z(2, 100.0, 202.3), z(3, 100.0, 197.4)]   # the target 1.8 east, two more at 2.3 and 2.6


def engaged(tmp_path, on=True, mod="1.13", leave=False, scan=None, **frame):
    """A Survive (GROUP_LEAVE `leave`, off as `test_survive.make` sets it) on a `rig` announcing `mod`, ENGAGE_HOLD
    `on`, `scan` squares scanned: its first line fights the one zombie 1.8 tiles east with the melee (accepted, its last
    step `face`); the line after reads `frame`."""
    r = rig(tmp_path, mod)
    if scan:
        r.scan(scan)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE, sv.ENGAGE_HOLD = leave, on
    r.frame(zombies=[z(1, 101.8)])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee" and sv.mode == "fight"
    accept(r, a, "face")
    r.advance(0.5)
    r.frame(**frame)
    tick(r, sv)
    return r, sv, a


@pytest.mark.parametrize("on", [True, False])
def test_a_many_read_at_the_engaged_melee_is_held(tmp_path, on):
    """Three standing within DANGER_R, the nearest the melee's target at 1.8 (beyond POINT_BLANK_OVER_R): engaged, the
    threat branch holds the melee (no send), logged `engage_hold` {rule "many"}; with ENGAGE_HOLD off, the `many` flee
    as before (its run steer superseding the melee)."""
    r, sv, a = engaged(tmp_path, on, zombies=GROUP)
    why = threat_why(tmp_path)
    if on:
        assert r.acts.history[-1] is a and why.get("fight") is True and why["engage_hold"] == {"rule": "many"}
        assert why["holding"] == a.aid
    else:
        assert why.get("flee") == "many" and r.acts.history[-1] is not a and "engage_hold" not in why


@pytest.mark.parametrize("on", [True, False])
def test_the_drag_guard_at_the_engaged_melee_is_held(tmp_path, on):
    """The frame reads two attackers (the drag guard's DRAG_DOWN_N - 1): engaged, the melee holds (the reflex meets the
    pile), logged `engage_hold` {rule "drag"}; with ENGAGE_HOLD off, the guard's run (`group` "drag")."""
    zs = [z(1, 101.8), z(2, 100.0, 200.6), z(3, 99.3, 200.0)]
    r, sv, a = engaged(tmp_path, on, zombies=zs, attackers=2)
    why = threat_why(tmp_path)
    if on:
        assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "drag"} and "group" not in why
    else:
        assert why.get("group") == "drag" and r.acts.history[-1] is not a


@pytest.mark.parametrize("on", [True, False])
def test_the_care_s_commitment_at_the_engaged_melee_is_held(tmp_path, on):
    """Part 7 bleeding, a rag held, the melee's target stepped back to 2.6 tiles (beyond KEEP_R, within CARE_HOLD_R):
    engaged, no care leg and no yield (the melee holds), logged `engage_hold` {rule "care"}; with ENGAGE_HOLD off,
    CARE_COMMIT's one distance leg (Plan 32 Task 5 (c)'s answer) superseding the melee."""
    parts = [part(7, bleeding=True, bleedingTime=5.0)]
    rr = rig(tmp_path)
    sv = S.Survive(rr.world, rr.acts, str(tmp_path / "decision.log"), rr.clock)
    sv.GROUP_LEAVE, sv.ENGAGE_HOLD = False, on
    hold(rr, 11, "Base.RippedSheets")
    rr.frame(zombies=[z(1, 101.8)])
    tick(rr, sv)
    a = rr.acts.history[-1]
    assert a.type == "melee"
    accept(rr, a, "face")
    rr.advance(0.5)
    care_frame(rr, parts, zombies=[z(1, 102.6)])
    tick(rr, sv)
    why = threat_why(tmp_path)
    if on:
        assert rr.acts.history[-1] is a and why["engage_hold"] == {"rule": "care"} and "care_commit" not in why
    else:
        assert why["care_commit"]["phase"] == "leg" and rr.acts.history[-1].type == "steer"


FIVE = [z(1, 101.8), z(2, 100.0, 202.3), z(3, 100.0, 197.4), z(4, 98.0, 200.0), z(5, 102.0, 202.5)]   # five standing


@pytest.mark.parametrize("on", [True, False])
def test_the_leave_s_run_at_the_engaged_melee_is_held(tmp_path, on):
    """GROUP_LEAVE on, five standing within GROUP_ENTRY_R, the nearest the melee's target at 1.8 (within KEEP_R: the
    leave's entry, LEAVE_ENTRY): above RETREAT_MAX_N its leg is the `many` run; engaged, the melee holds, logged
    `engage_hold` {rule "leave"}; with ENGAGE_HOLD off, the leave's run (Plan 33 Task 3 fix 4's answer)."""
    r, sv, a = engaged(tmp_path, on, leave=True, zombies=FIVE)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "run"
    if on:
        assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "leave"} and why.get("fight") is True
    else:
        assert why.get("flee") == "many" and r.acts.history[-1] is not a


@pytest.mark.parametrize("on", [True, False])
def test_the_leave_strung_out_at_the_engaged_melee_is_held(tmp_path, on):
    """GROUP_LEAVE on: three standing take the leave (its retreat, the Fight's: the melee re-sent with the withdraw
    bias); then three lines read two within GROUP_ENTRY_R: engaged, the leave holds (`_strung_holds`, logged
    `engage_hold` {rule "strung"}, the count not run) and the melee is re-sent without the bias, no leg in its place;
    with ENGAGE_HOLD off, STRUNG_HOLD's `strung` end on the third (Plan 34's answer)."""
    trio = GROUP
    r, sv, a = engaged(tmp_path, on, leave=True, zombies=trio)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "retreat" and why.get("fight") is True
    b = r.acts.history[-1]
    assert b.type == "melee" and "withdrawX" in b.args
    accept(r, b, "face")
    for _ in range(3):
        r.advance(0.5)
        r.frame(zombies=trio[:2] + [z(3, 100.0, 210.0)])   # the third 10 tiles off, beyond GROUP_ENTRY_R
        tick(r, sv)
    why = threat_why(tmp_path)
    if on:
        assert sv.leave is not None and why["engage_hold"] == {"rule": "strung"}
        c = r.acts.history[-1]   # the melee re-sent with no withdraw (two standing): no leg in its place
        assert c.type == "melee" and "withdrawX" not in c.args
    else:
        assert sv.leave is None and why["group_leave"]["end"] == "strung"


@pytest.mark.parametrize("on", [True, False])
def test_a_corner_at_the_engaged_melee_inside_is_held(tmp_path, on):
    """On a room square the melee's target closes to 0.8 tiles (within CORNERED_R): engaged, no corner Fight (the
    reflex meets it), logged `engage_hold` {rule "cornered"}; with ENGAGE_HOLD off, the `inside` corner's Fight (P23-AJ
    2's answer) superseding the melee."""
    from .test_policies import grid
    r, sv, a = engaged(tmp_path, on, scan=grid(96, 104, 196, 204, at={(x, y): {"room": "kitchen", "building": 1}
                                                                      for x in range(96, 105)
                                                                      for y in range(196, 205)}),
                       zombies=[z(1, 100.8)])
    why = threat_why(tmp_path)
    if on:
        assert r.acts.history[-1] is a and why["engage_hold"] == {"rule": "cornered"} and "cornered" not in why
    else:
        assert why.get("cornered") == 1 and r.acts.history[-1] is not a


def test_no_still_read_over_the_engaged_melee(tmp_path, monkeypatch):
    """The still read (P30-E: its approach leg or its pass) is never read while the melee is engaged."""
    def still(self, held, fight):
        assert not fight._engaged(), "the still read when engaged"
    monkeypatch.setattr(S.Survive, "_still_read", still)
    r, sv, a = engaged(tmp_path, zombies=[z(1, 102.0)])
    assert r.acts.history[-1] is a and threat_why(tmp_path).get("fight") is True


def test_under_the_floor_the_many_flee_runs_as_before(tmp_path):
    """The many read at the engaged melee with the health at 39 (under FLEE_HEALTH, the reflex's floor): the hold gives
    way, the `many` flee as before, no `engage_hold`."""
    r, sv, a = engaged(tmp_path, zombies=GROUP, health=39.0)
    why = threat_why(tmp_path)
    assert why.get("flee") == "many" and "engage_hold" not in why and r.acts.history[-1] is not a


def test_a_1_11_build_s_many_read_flees_as_before(tmp_path):
    """The goldens' build (a hello at 1.11, ENGAGE_HOLD on): no work, no engagement, the `many` flee as before."""
    r, sv, a = engaged(tmp_path, mod="1.11", zombies=GROUP)
    why = threat_why(tmp_path)
    assert "workR" not in a.args and why.get("flee") == "many" and "engage_hold" not in why
    assert last(tmp_path)["branch"] == "threat"
