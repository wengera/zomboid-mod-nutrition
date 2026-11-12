"""Survival 24 (survival iteration 22; Plan 28 Task 7b; the architecture review `arch-review-cerebellum.md` §§ 3.5 and
4.2, cut 1 of the maneuver layer; Task 7a's reflex skill `melee`, PZA/1.8). The fake mod over PZA/1.8, its hello
announcing `melee` only where a test asks (`fakemod.MELEE_CAPS`); each test's geometry is the review's cases.

- The `Maneuver` base (`planner/maneuvers/base.py`): one named physical sequence with its own state, one command at a
  time; `observe()` reads its own actions' ends (each once, an earlier one's late end too) and its current action's
  progress lines, `step()` the next command or None, `over()` None while it runs else its end (`superseded` once
  another sender took the slot), `why` its own fields, logged as `{maneuver: name, ...}`.
- `Melee` (`planner/maneuvers/melee.py`) and the `MELEE` switch: with `melee` announced and the rule on, where the
  Fight's ladder would send an in-reach `aim` leg (`enter`, `back`, `stand` within KEEP_R), an `attack`, a `shove`, a
  `stomp` or a floor swing at its pin within MELEE_RELEASE_R, the Fight starts or continues its `Melee` instead
  (`fight.Fight.m`): each argument from its source (`mode` strike, shove under `_hold_bars` (P28-H: the arms' pain
  alone no longer selects it), finish at a fallen pin; `reach` the frame's `weapon.reach` plus ATTACK_MARGIN, 0
  without one; PZA/1.10's meet arguments off the policies table: `faceR` FACE_R, `pressAngle` PRESS_ANGLE, `pressLo`
  PRESS_LO, `floorR` FLOOR_R, `handbackR` HANDBACK_R, `stall` STALL_SWINGS), sent once a target and re-sent only when
  its inputs change (`resend` "inputs", never while a press is in flight; Plan 31 Task 2: the meet has no back leg and
  no time end); its ends mapped (`lost` to the ladder's path, out of reach and no progress marking the target,
  `handback` to a re-pin to the nearer, a span with strikes and no health fall to the no-progress mark, a kill read
  once); a flee's hand-over supersedes it; the corner, the door fight and the doorway stand keep the ladder; without
  the cap or with the rule off the ladder as before.
"""
import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers import Maneuver, Melee
from agent.base.pza1 import Attack, Scan

from .fakemod import MELEE_CAPS
from .test_policies import BAT, Rig, square
from .test_survive import make, threat_why, tick
from .test_lua_skills import load
from .test_survive_q import fr, z


class Scanner(Maneuver):
    """A maneuver of one command a turn: a scan of radius 4, re-sent while its owner calls `step`."""
    name = "scanner"

    def __init__(self, world, actions, clock):
        super().__init__(world, actions, clock)
        self.ends, self.lines = [], []

    def step(self):
        return None if self.over() is not None or self.running() else Scan(4)

    def ended(self, a, current):
        self.ends.append((a.aid, a.state, a.reason, current))

    def progressed(self, line):
        self.lines.append(line["result"])


def send(r, m):
    """`m`'s next command sent through the rig's Actions as its owner would, `m.sent` told."""
    cmd = m.step()
    a = r.acts.send(cmd)
    m.sent(cmd, a)
    return a


def act(r, a, state, reason="", result=None):
    r.fake.act(a.aid, state, a.type, reason=reason, result=result)
    r.pump()


# ================================================================ the Maneuver base
def test_a_maneuver_that_sent_nothing_runs_nothing_and_has_no_end(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    m.observe()
    assert (m.action, m.running(), m.over(), m.drained(), m.why, m.n) == (None, False, None, True, {}, 0)
    assert m.log() == {"maneuver": "scanner"}


def test_observe_reads_its_current_action_s_end_once(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    assert m.action is a and m.running() and not m.drained() and m.n == 1 and m.step() is None
    act(r, a, "accepted")
    m.observe()
    assert m.ends == [] and m.running()
    act(r, a, "done", result={})
    m.observe()
    m.observe()
    assert m.ends == [(a.aid, "done", "", True)] and not m.running() and m.drained() and m.over() is None


def test_an_earlier_action_s_late_end_is_read_as_not_current(tmp_path):
    """The maneuver's second send supersedes its first in the Lua; the first's end (here a late `done`, the line
    written before the second reached the Lua) is still read, once, marked not current."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    b = r.acts.send(Scan(4))
    m.sent(Scan(4), b)
    act(r, a, "done", result={"kill": True})
    m.observe()
    assert m.ends == [(a.aid, "done", "", False)] and m.action is b and m.running() and m.over() is None
    assert m.n == 2 and not m.drained()


def test_another_sender_s_command_ends_the_maneuver_superseded(tmp_path):
    """One command at a time: once another sender's action is current, the maneuver's own (not yet ended) no longer
    runs, and its end is `superseded` at once (the Lua's `failed superseded` line read later, still once)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    r.acts.send(Scan(2))
    m.observe()
    assert not m.running() and m.over() == "superseded" and m.step() is None and not m.drained()
    act(r, a, "failed", "superseded")
    m.observe()
    assert m.ends == [(a.aid, "failed", "superseded", True)] and m.drained() and m.over() == "superseded"


def test_progress_lines_of_the_current_action_are_read_once_each(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    act(r, a, "progress", result={"step": "stand"})
    m.observe()
    m.observe()
    act(r, a, "progress", result={"step": "face"})
    act(r, a, "progress", result={"step": "swing"})
    m.observe()
    assert m.lines == [{"step": "stand"}, {"step": "face"}, {"step": "swing"}]


def test_a_new_send_s_progress_lines_are_read_from_its_first(tmp_path):
    """The progress read follows the current action: after a second send (more lines read on the first than the
    second has), the second's first progress line is read."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    act(r, a, "progress", result={"step": "stand"})
    act(r, a, "progress", result={"step": "back"})
    m.observe()
    b = r.acts.send(Scan(4))
    m.sent(Scan(4), b)
    act(r, b, "accepted")
    act(r, b, "progress", result={"step": "close"})
    m.observe()
    assert m.lines == [{"step": "stand"}, {"step": "back"}, {"step": "close"}]


# ================================================================ Melee and the MELEE switch: the dispatch and its args
STRIKE_R = BAT["reach"] + P.ATTACK_MARGIN      # the rig's bat's reach and ATTACK_MARGIN (`FightReach.reach_r`)
DONE_LOST = {"end": "lost", "why": "out of range", "kill": False, "swings": 0, "shoves": 0, "stomps": 0, "floors": 0,
             "knockdowns": 0, "hits": 0, "hp0": 1.0, "hp1": 1.0, "dMin": 1.2, "steps": {"face": 25}}   # PZA/1.10


def rig(tmp_path, name, caps=MELEE_CAPS):
    """A Rig in its own sub-directory `name` of `tmp_path` (several rigs a test)."""
    d = tmp_path / name
    d.mkdir()
    return Rig(d, caps=caps)


def fight(r, stance=True, **k):
    """A Fight on the rig, the standing fight's `stance` set (Survive's `_stance_ok`), `k` set on it."""
    f = F.Fight(r.world, r.acts, r.clock)
    f.stance = stance
    for name, v in k.items():
        setattr(f, name, v)
    return f


def done(r, a, **res):
    act(r, a, "done", result=dict(DONE_LOST, **res))


def want(target, mode="strike", reach=STRIKE_R, floor=True):
    """A melee's wire args (PZA/1.10, Plan 31 Task 2): `floorSwing` left off when False (`pza1._Cmd.args`); Plan 35
    Task 8: every melee carries its `work` arguments (PZA/1.13: no withdraw outside the fighting retreat)."""
    out = {"targetId": target, "mode": mode, "reach": reach, "shoveR": P.SHOVE_SEND_R, "releaseR": P.MELEE_RELEASE_R,
           # headAim HEAD_AIM, False until calibrated, so left off the wire (`pza1._Cmd.args`; fix 1, review-t2 F4)
           "faceR": P.FACE_R, "pressAngle": P.PRESS_ANGLE, "pressLo": P.PRESS_LO, "floorR": P.FLOOR_R,
           "handbackR": P.HANDBACK_R, "stall": P.STALL_SWINGS, "workR": P.WORK_R, "crawlerR": P.WORK_CRAWLER_R,
           "bandLo": P.WORK_BAND_LO, "floorHealth": P.FLEE_HEALTH, "pile": True}
    if floor:
        out["floorSwing"] = True
    return out


def test_the_meet_constants_are_the_policies_table_s():
    """PZA/1.10 (Plan 31 Task 2): FACE_R 3.0 (the spec's), PRESS_ANGLE acos(0.75) (the bat's MinAngle, #4591, #4681),
    PRESS_LO 0 (the collision tests no lower distance, #4682), FLOOR_R 1.0 (WeaponLength 0.5 + 0.5, #4679), HANDBACK_R
    2.0 (the spec's), the release KEEP_R + KEEP_MARGIN (the backpedal's own give-way); the time span, its re-send
    margin, the planner's walk bound and P30-A's swing close gone with the Lua's time end and back leg."""
    import math
    assert (P.FACE_R, P.PRESS_LO, P.FLOOR_R, P.HANDBACK_R) == (3.0, 0.0, 1.0, 2.0)
    assert P.PRESS_ANGLE == math.degrees(math.acos(0.75)) and P.MELEE_RELEASE_R == P.KEEP_R + P.KEEP_MARGIN == 2.75
    assert not any(hasattr(P, n) for n in ("MELEE_S", "MELEE_RESEND_MARGIN_S", "MELEE_WALK_S", "SWING_CLOSE_R"))


def test_a_standing_fight_s_target_within_keep_r_starts_melee_with_each_argument_from_its_source(tmp_path):
    """A chaser 2.0 tiles off (within FIGHT_REACH, the stance not held): where the ladder sends the `enter` leg, the
    melee goes: `mode` strike, `reach` the bat's 1.2 plus ATTACK_MARGIN, `shoveR` SHOVE_SEND_R (P28-H), `releaseR`
    MELEE_RELEASE_R, the meet's `faceR`, `pressAngle`, `pressLo`, `floorR`, `handbackR` and `stall` off the policies
    table, `floorSwing` true; logged `maneuver` {maneuver melee, target, mode, sends 1} beside the ladder's own why."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    assert (a.type, a.args) == ("melee", want(9))
    assert f.why["leg"] == "enter" and f.why["ladder"] == "aim" and f.why["melee"] == {"mode": "strike", "pain": None}
    assert f.why["maneuver"] == {"maneuver": "melee", "target": 9, "mode": "strike", "sends": 1, "step": None,
                                 "d": None}
    assert isinstance(f.m, Melee) and f.m.action is a and f.m.target == 9


def test_the_mode_is_shove_under_a_shove_only_fight_or_a_hold(tmp_path):
    """`mode` shove where the Fight holds a bar (`_hold_bars`, P28-H): a shove-and-stomp Fight (`shove_only`
    "unarmed") or
    a hold (`spent`): the ladder's backpedal (`_wounded_leg`) is the melee's dispatch point there; both bar the floor
    swing too (`floor_swing_barred`, P28-C), so `floorSwing` is left off."""
    for k in ({"shove_only": "unarmed"}, {"spent": ("arms",)}):
        r = rig(tmp_path, sorted(k)[0])
        fr(r, [z(9, 102.0)])
        f = fight(r, **k)
        a = f.step()
        assert (a.type, a.args) == ("melee", want(9, mode="shove", floor=False)), k
        assert f.why["leg"] == "back" and f.why["ladder"] == "aim"


def test_an_armed_hold_sends_the_melee_in_shove_mode_and_no_swing_bars_the_ladder_alone(tmp_path):
    """Fix 1, review-t15a M1 (the controller's ruling, Angus's stand and fight): under the endurance hold (`spent`) or
    a low or hold shove-and-stomp Fight, the bat held and the arms unhurt, the melee goes in mode `shove` (the Lua's
    spent meet: the shove, then the swing after a shove that knocked nothing down, `test_lua_melee`'s armed hold
    case), and `no_swing` (the ladder's own bar) reads True: the Fight's ladder sends no swing of its own."""
    for i, k in enumerate(({"spent": ("endurance",)}, {"shove_only": "hold"}, {"shove_only": "low"})):
        r = rig(tmp_path, "case%d" % i)
        fr(r, [z(9, 101.0)])
        f = fight(r, **k)
        a = f.step()
        assert (a.type, a.args["mode"]) == ("melee", "shove") and r.world.weapon is not None, k
        assert f.no_swing() is True, k


def test_the_reach_is_zero_without_the_frame_s_weapon_reach_or_with_attack_reach_off(tmp_path):
    """`reach` 0 (the Lua's `K.reachOf`) where `FightReach.reach_r` reads none: no weapon in the frame, or the
    `attack_reach` rule off."""
    r = rig(tmp_path, "bare")
    r.frame(zombies=[z(9, 102.0)], weapon=None)
    a = fight(r).step()
    assert a.args["reach"] == 0.0 and a.args["mode"] == "strike"
    r = rig(tmp_path, "rule")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    f.rules = f.rules - {"attack_reach"}
    assert f.step().args["reach"] == 0.0


def test_the_melee_sends_no_back_heading_no_seconds_and_no_close_r(tmp_path):
    """PZA/1.10: the args are the meet's; the back leg's heading, the time span and P30-A's closeR are gone, whatever
    the `circle` and `swing_close` rules read."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    a = fight(r).step()
    assert a.type == "melee" and set(a.args) == set(want(9))
    assert not {"keepR", "backVx", "backVy", "seconds", "closeR"} & set(a.args)


def test_the_back_leg_within_keep_r_is_the_melee_and_the_stand_beyond_it_the_ladder_s(tmp_path):
    """The dispatch point's edge: at 2.3 tiles (beyond FIGHT_REACH, inside KEEP_R) the ladder's `back` leg is the
    melee; at 2.6 (beyond KEEP_R) its `stand` leg goes as before, no maneuver."""
    r = rig(tmp_path, "in")
    fr(r, [z(9, 102.3)])
    f = fight(r)
    a = f.step()
    assert a.type == "melee" and f.why["leg"] == "back"
    r = rig(tmp_path, "out")
    fr(r, [z(9, 102.6)])
    f = fight(r)
    a = f.step()
    assert (a.type, f.why["leg"]) == ("aim", "stand") and "maneuver" not in f.why and f.m is None


def test_the_attack_and_the_shove_at_the_pin_are_the_melee(tmp_path):
    """The approach-and-swing Fight's `attack` at its pin 1.0 tiles off is the melee (mode strike); the shove at a
    chaser at point blank under the arms' pain 30 (P24-AG) is the melee in mode strike (ruling P28-H: the arms' pain
    no longer selects shove mode; the Lua's rule 8 shoves within K.STAND_R in strike mode)."""
    r = rig(tmp_path, "attack")
    fr(r, [z(9, 101.0)])
    f = fight(r, stance=False)
    a = f.step()
    assert (a.type, a.args) == ("melee", want(9)) and f.why["ladder"] == "attack"
    r = rig(tmp_path, "shove")
    fr(r, [z(9, 100.9)], 30.0)
    f = fight(r, stance=False)
    a = f.step()
    assert (a.type, a.args["mode"], f.why["ladder"]) == ("melee", "strike", "shove")   # P28-H: the pain alone strikes


def test_the_floor_swing_and_the_stomp_at_a_fallen_pin_are_the_melee_in_finish_mode(tmp_path):
    """The finish of the pin itself fallen 1.2 tiles off (P27-G's floor swing; under a hold P28-C bars it and the
    stomp goes) is the melee in mode finish, `floorSwing` read off `floor_swing_barred`."""
    for k, ladder, floor in (({}, "attack", True), ({"spent": ("arms",)}, "stomp", False)):
        r = rig(tmp_path, ladder)
        fr(r, [z(9, 101.2, floor=True)])
        f = fight(r, **k)
        a = f.step()
        assert (a.type, a.args["mode"], f.why["ladder"]) == ("melee", "finish", ladder)
        assert a.args.get("floorSwing", False) is floor and f.why["downed"] == 9


def test_the_finish_of_a_fallen_zombie_other_than_the_pin_keeps_the_ladder(tmp_path):
    """The finish's choice of another fallen zombie stays above the dispatch point: pin 9 standing 3.0 tiles off,
    zombie 8 fallen 1.2 off: the ladder's floor swing at 8 goes as before."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 103.0), z(8, 101.2, floor=True)])
    f = fight(r, target=9)
    a = f.step()
    assert (a.type, a.args) == ("attack", {"targetId": 8}) and "maneuver" not in f.why and f.m is None


def test_a_send_beyond_the_release_keeps_the_ladder(tmp_path):
    """A stomp at the fallen pin 3.5 tiles off (the finish's reach FINISH_R, its walk in) lies beyond
    MELEE_RELEASE_R, where the Lua would refuse the melee `too far`: the ladder's stomp goes."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 103.5, floor=True)])
    a = fight(r).step()
    assert (a.type, a.args) == ("stomp", {"targetId": 9})


# ================================================================ the cap, the switch, the Fights keeping the ladder
def test_without_the_cap_or_with_the_rule_off_the_ladder_as_before(tmp_path):
    """No hello announcing `melee` (the fake's DEFAULT_HELLO), or the `melee` rule off (Survive's MELEE): the `enter`
    leg goes as before."""
    r = rig(tmp_path, "cap", caps=None)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    assert (a.type, f.why["leg"]) == ("aim", "enter") and f.m is None and "maneuver" not in f.why
    r = rig(tmp_path, "off")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    f.rules = f.rules - {"melee"}
    a = f.step()
    assert (a.type, f.why["leg"]) == ("aim", "enter") and f.m is None


def test_the_melee_switch_is_iteration_22_s_and_drops_its_rule(tmp_path):
    """`MELEE` on `threat.Threat`, on by default, the first (and only) name of `survive.T12_SWITCHES`; off, the
    Fight's `rules` lack `melee`."""
    assert T.Threat.MELEE is True and S.T12_SWITCHES == ("MELEE",) and "melee" in F.FIGHT_RULES
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    on = sv._fight_rules()
    sv.MELEE = False
    assert "melee" in on and sv._fight_rules() == on - {"melee"}


# ================================================================ the re-sends
def test_a_running_melee_is_held_with_no_re_send_while_its_inputs_hold(tmp_path):
    """PZA/1.10: one send a target. Accepted and running, the melee is held (`busy`) on every tick for 20 s, the
    target moving, with no re-send: the meet has no time end, and its heading is the Lua's."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    for k in range(40):
        r.advance(0.5)
        fr(r, [z(9, 101.5, 200.0 + 0.01 * k)])
        assert f.busy() and f.step() is None and f.m.action is a and f.m.n == 1, k


def test_a_change_of_mode_re_sends_once_with_resend_inputs(tmp_path):
    """A hold read (`spent`, `_hold_bars`) turns the mode to shove: the running melee is re-sent at the same target (the
    Lua keeps the stance across it) with mode shove and the floor swing barred, logged `melee` {resend "inputs"},
    `maneuver` sends 2; strike and finish are one meet (the target's posture picks the finish), so a pin falling sends
    nothing."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 101.2, floor=True)])
    assert f.busy() and f.step() is None                                # strike to finish: no re-send
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    f.spent = ("arms",)
    assert not f.busy()
    b = f.step()
    assert (b.type, b.args) == ("melee", want(9, mode="shove", floor=False))
    assert f.why["melee"]["resend"] == "inputs" and f.why["maneuver"]["sends"] == 2 and f.m.action is b


# ================================================================ the ends
def test_lost_out_of_range_takes_the_ladder_s_path_for_one_choose(tmp_path):
    """`done lost` (why out of range), logged `melee_end` {.., end lost, why}, the target not marked. Task 8 fix 1 (a
    named change): with the target still within KEEP_R the next choose is the melee again, logged `engage_dispatch`
    {from "lost"} (the ladder's `back` leg before it); beyond KEEP_R the ladder's `stand`, as before."""
    r = rig(tmp_path, "lag")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 102.3)])
    b = f.step()
    assert b.type == "melee" and f.why["melee"]["engage_dispatch"] == {"from": "lost"}
    assert f.why["melee_end"]["end"] == "lost" and f.why["melee_end"]["why"] == "out of range"
    assert 9 not in f.unreachable
    r = rig(tmp_path, "far")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 102.6)])
    b = f.step()
    assert (b.type, f.why["leg"]) == ("aim", "stand")


def test_too_far_takes_the_ladder_s_path_as_out_of_range_does(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "rejected", "too far")
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    b = f.step()   # Task 8 fix 1 (a named change): in contact the melee again, where the ladder sent its `enter` leg
    assert b.type == "melee" and f.why["melee_end"]["end"] == "too far"
    assert f.why["melee"]["engage_dispatch"] == {"from": "too far"}


def test_a_handback_re_pins_to_the_other_zombie_the_lua_reports_nearer(tmp_path):
    """`done handback` {why crowd, id, d}: the other standing zombie the engine's press would take (within K.STAND_R
    0.6, where the Lua hands back) is pinned when it is nearer than the target, and the next melee goes at it. Fix 1
    (review-t7b M1): the geometry the Lua reports, 8 closing from 0.9 tiles to 0.55 while pin 9 stands 1.0 off."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9)
    act(r, a, "accepted")
    done(r, a, end="handback", why="crowd", id=8, d=0.55)
    r.advance(0.5)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.55)])
    b = f.step()
    assert (b.type, b.args["targetId"], f.target) == ("melee", 8, 8) and f.why["melee_end"]["end"] == "handback"


def old_gate(self, zid, z):
    """The crowd gate before Plan 31 Task 15a fix 1 (review-t7b M1): another standing zombie within STAND_MIN_R."""
    return self._standing_near(P.STAND_MIN_R, (zid,)) is not None


OLD_GATE = ("agent.base.planner.dispatch.FightDispatch._crowded", old_gate)


def test_a_finish_whose_pin_stands_holds_its_melee(tmp_path):
    """PZA/1.10: no `stood` end; the finish's pin rising is met by the same melee (the Lua's meet), held with no
    re-send: finish and strike are one behaviour."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.2, floor=True)])
    f = fight(r)
    a = f.step()
    assert a.args["mode"] == "finish"
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 101.2)])
    assert f.busy() and f.step() is None and f.m.n == 1


def test_a_build_that_cannot_run_the_melee_falls_back_to_the_ladder_for_the_fight(tmp_path):
    """`failed not loaded` (a member the skill needs absent): no melee for the rest of the Fight (`melee_off`), as a
    failed stance leg ends the stand (minor 11): the ladder's legs from then on."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "failed", "not loaded")
    for _ in range(2):
        r.advance(0.5)
        fr(r, [z(9, 102.0)])
        b = f.step()
        assert (b.type, f.melee_off) == ("aim", "not loaded")
        act(r, b, "failed", "superseded")


def test_spans_with_strikes_and_no_health_fall_reach_the_no_progress_mark(tmp_path):
    """A `done` span with strikes (swings, floor swings, stomps) and `hp1` not under `hp0` counts its strikes in the
    no-progress streak STALL_SWINGS reads: the third such strike marks the target unreachable, and the Fight sends
    nothing at it; a span whose health fell restarts the streak. Task 8 fix 1 (a named change): each `done lost` (out
    of range) with the target within KEEP_R is followed by the next melee at once (the ladder's leg before it)."""
    for falls in (False, True):
        r = rig(tmp_path, str(falls))
        fr(r, [z(9, 102.0)])
        f = fight(r)
        for k in range(P.STALL_SWINGS):
            a = f.step()
            assert a is not None and a.type == "melee", k
            act(r, a, "accepted")
            done(r, a, swings=1, hp1=0.8 if (falls and k == 1) else 1.0)
            r.advance(0.5)
            fr(r, [z(9, 102.0)])
        b = f.step()
        if falls:
            assert b.type == "melee" and f.no_progress == 1 and 9 not in f.unreachable
        else:
            assert b is None and 9 in f.unreachable and f.target is None


def test_a_kill_is_read_once(tmp_path):
    """A `done` {end kill, kill true}: the Fight's `kill` names the target on that observe, the World counts it once,
    and it is read dead for UNREACHABLE_S, unpinned."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, end="kill", why=None, kill=True, swings=2, hp1=0.0)
    r.advance(0.5)
    fr(r, [])
    f.step()
    assert f.kill == 9 and r.world.kills == 1 and 9 in f.dead and f.target is None
    assert f.why["melee_end"]["end"] == "kill" and "why" not in f.why["melee_end"]
    f.observe()
    assert f.kill is None and r.world.kills == 1


def test_a_kill_of_the_zombie_the_reflex_re_pinned_names_it(tmp_path):
    """Plan 31 Task 15a: the reflex re-pinned from 9 to the nearer 8 (two standing within 0.6 tiles: the line's
    `target` 8, `repins` 1) and killed it: the Fight's kill is 8, read dead, and 9 is not."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, end="kill", why=None, kill=True, target=8, repins=1, hp1=0.0)
    r.advance(0.5)
    fr(r, [z(9, 101.0)])
    f.step()
    assert f.kill == 8 and r.world.kills == 1 and 8 in f.dead and 9 not in f.dead


def test_a_re_pinned_span_counts_on_the_zombie_it_read(tmp_path):
    """Task 15a: a `done` span with strikes and no health fall after a re-pin to 8 counts in 8's no-progress streak,
    never in the pin 9's (read at the observe: Plan 35 Task 8, the next choose in contact is the melee at the pin,
    whose send starts 9's streak)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, end="lost", why="no progress", target=8, repins=1, swings=2, hp0=1.0, hp1=1.0)
    r.advance(0.5)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.9)])
    f.observe()
    assert f._streak_id == 8 and f.no_progress == 2


def test_a_crowd_handback_keeps_its_count_and_distances(tmp_path):
    """Task 15a: the crowd end (three standing within 0.6 tiles) carries n and ds beside the nearest other's id and d;
    the maneuver keeps them in `handback`."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 100.5), z(8, 100.0, 200.9), z(7, 100.0, 199.1)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    m = f.m
    done(r, a, end="handback", why="crowd", id=8, d=0.45, n=3, ds=[0.45, 0.5, 0.5])
    m.observe()
    assert m.handback == {"id": 8, "d": 0.45, "n": 3, "ds": [0.45, 0.5, 0.5]} and m.end_why == "crowd"


def test_a_kill_on_the_melee_a_re_send_superseded_is_read_too(tmp_path):
    """The race the base's late-end read covers: the first melee ends `done` {kill} after its re-send (a mode change)
    left (the line written before the re-send reached the Lua), and the re-send is rejected `no target`: the kill
    counts once."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    f.spent = ("arms",)
    b = f.step()
    assert b.type == "melee"
    done(r, a, end="kill", why=None, kill=True)
    act(r, b, "rejected", "no target")
    r.advance(0.5)
    fr(r, [])
    f.step()
    assert f.kill == 9 and r.world.kills == 1 and f.m is None


def test_a_kill_on_a_melee_the_ladder_s_send_replaced_is_read_too(tmp_path):
    """The Fight's own next command that is no melee (an attack at another fallen zombie) retires the maneuver, whose
    melee's late `done` {kill} is still read (`_spent_m`). Plan 35 Task 8: the running melee holds until a re-send is
    due (no finish give-way), so the ladder's attack is sent directly."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    f.rules = f.rules - {"pair_nearest"}
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 102.0), z(8, 101.2, floor=True)])
    f.observe()
    b = f.send(Attack(8))
    assert b.type == "attack" and f.m is None
    done(r, a, end="kill", why=None, kill=True)
    r.advance(0.5)
    fr(r, [z(8, 101.2, floor=True)])
    f.observe()
    assert f.kill == 9 and r.world.kills == 1 and f._spent_m == []


# ================================================================ busy, the hand-over and the log


def test_the_survive_tick_logs_the_maneuver_s_step_while_it_holds_and_a_flee_hand_over_supersedes_it(tmp_path):
    """Survive's threat branch: the standing fight's melee sent; a progress line read, the holding tick logs
    `maneuver` {.., step, d} from it; at health 15 (under FLEE_HEALTH_FLOOR, no low fight) the flee's leg goes at once,
    superseding it. Pinned with DISPOSITION off (a named change, Plan 37 Task 3: the selector's `break` at the floor
    keeps the Fight until the reflex's `floor` hand-back, `test_disposition.py`)."""
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    sv.DISPOSITION = False
    fr(r, [z(9, 102.0)])
    a = tick(r, sv)
    assert a.type == "melee" and threat_why(tmp_path)["maneuver"]["mode"] == "strike"
    act(r, a, "accepted")
    act(r, a, "progress", result={"step": "stand", "d": 1.9, "hp": 1.0, "swings": 0, "shoves": 0, "stomps": 0,
                                  "floors": 0, "knockdowns": 0, "hits": 0})
    r.advance(0.5)
    fr(r, [z(9, 101.9)])
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["holding"] == a.aid and (w["maneuver"]["step"], w["maneuver"]["d"]) == ("stand", 1.9)
    r.advance(0.5)
    fr(r, [z(9, 101.9)], health=15.0)
    b = tick(r, sv)
    assert b is not None and b.type != "melee" and sv.mode == "flee" and sv.fight is None
    assert r.acts.current is b


# ================================================================ the mutation pass's cases (Plan 28 Task 7b)
def test_the_fence_wait_s_leg_within_keep_r_keeps_the_ladder(tmp_path):
    """The fence wait stays above the dispatch point: a chaser 2.0 tiles off across the fence at x 102 (P25-F's yard),
    its `stand` leg within KEEP_R goes as the ladder's aim, logged `fence_wait`, no maneuver."""
    from .test_survive_t import fence_rig
    r, sv = fence_rig(tmp_path, 102.5, caps=MELEE_CAPS)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["fence_wait"]["leg"] == "stand" and "maneuver" not in w and sv.fight.m is None


def test_the_ladder_s_backpedal_at_a_fallen_pin_keeps_the_ladder(tmp_path):
    """Under a hold with the stomp refused at the fallen pin (`swing_refused`), the finish's backpedal (P24-AP's leg,
    `_wounded_leg`) is no melee: a finish there would press the refused stomp."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.2, floor=True)])
    f = fight(r, spent=("arms",))
    f.swing_refused[("stomp", 9)] = r.clock() + P.SWING_SKIP_S
    a = f.step()
    assert (a.type, f.why["leg"]) == ("aim", "back") and f.m is None and "maneuver" not in f.why





def test_floor_swing_is_off_with_the_floor_finish_rule_off(tmp_path):
    """`floorSwing` needs P27-G's rule (`floor_finish`, the floor swing ahead of the stomp): off, the ladder stomps the
    fallen pin and the melee's finish goes without it."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.2, floor=True)])
    f = fight(r)
    f.rules = f.rules - {"floor_finish"}
    a = f.step()
    assert (a.type, a.args["mode"], f.why["ladder"]) == ("melee", "finish", "stomp") and "floorSwing" not in a.args


def test_no_weapon_takes_the_ladder_s_path_for_one_choose(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "rejected", "no weapon")
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    b = f.step()   # Task 8 fix 1b: `no weapon` hands the ladder the choose whatever the contact
    assert (b.type, f.why["melee_end"]["end"]) == ("aim", "no weapon") and f.melee_off is None


@pytest.mark.parametrize("state, reason", [("failed", "not loaded"), ("rejected", "bad args"),
                                           ("rejected", "unknown type")])
def test_each_end_of_a_build_that_cannot_run_the_melee_turns_it_off(tmp_path, state, reason):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    act(r, f.step(), state, reason)
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    assert f.step().type == "aim" and f.melee_off == reason


def test_a_span_whose_health_is_unreadable_restarts_the_streak_and_one_with_no_strike_leaves_it(tmp_path):
    """The streak's edges: a span reading no `hp1` restarts it (as the ladder's unreadable health does); a span with
    no strike neither counts nor restarts it, its health unreadable too; one span's swings, floor swings and stomps
    all count."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    for res, n in (({"swings": 2}, 2), ({"swings": 1, "hp1": None}, 0), ({"swings": 1}, 1), ({"hp1": None}, 1)):
        a = f.step()
        if a.type == "aim":   # the ladder's one choose after a `lost` end
            act(r, a, "done", result={})
            r.advance(0.5)
            fr(r, [z(9, 102.0)])
            a = f.step()
        act(r, a, "accepted")
        done(r, a, **res)
        r.advance(0.5)
        fr(r, [z(9, 102.0)])
        f.observe()
        assert f.no_progress == n, res
    a = f.step()
    act(r, a, "done", result={})
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    a = f.step()
    act(r, a, "accepted")
    done(r, a, swings=0, floors=1, stomps=1)
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    assert f.step() is None and 9 in f.unreachable





def test_a_melee_whose_send_another_sender_superseded_sends_nothing_and_ends(tmp_path):
    """`Melee.step` unobserved: once another sender's action is current, its running melee no longer runs, and the
    step ends it `superseded` instead of re-sending."""
    from agent.base.planner.maneuvers.melee import MeleeInputs
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Melee(r.world, r.acts, r.clock, 9)
    m.inputs = MeleeInputs("strike", 0.0, False)
    a = send(r, m)
    act(r, a, "accepted")
    r.acts.send(Scan(2))
    assert m.step() is None and m.over() == "superseded" and m.resend is None


def test_a_choose_after_another_sender_s_command_starts_a_new_melee(tmp_path):
    """The Fight's dispatch on a choose its observe did not precede: the running maneuver's step finds its melee
    superseded, so the maneuver is retired and a new one sends (no re-send logged)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    first = f.m
    r.acts.send(Scan(2))
    cmd = f.choose()
    assert cmd.TYPE == "melee" and f.m is not first and first in f._spent_m and "resend" not in f.why["melee"]


def test_a_melee_is_the_swing_after_a_shove(tmp_path):
    """P24-AH's once a swing (`_shoved`, the last swing-like send a shove): a melee clears it as the ladder's attack
    does, so the finish's shove of a standing zombie at point blank beside the fallen pin goes first (the ladder's,
    at a zombie that is not the pin). Named change, Plan 32 Task 5 (b): pinned with the Fight's `pair_nearest` rule off
    (two within KEEP_R pin the standing one, whose shove is then the pin's)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    f.rules = f.rules - {"pair_nearest"}
    f._shoved = True
    a = f.step()
    act(r, a, "accepted")
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 101.2, floor=True), z(8, 100.0, 200.9)])
    b = f.step()
    assert (b.type, b.args) == ("shove", {"targetId": 8}) and f.why["shove"] == "first"


# ================================================================ fix 1 (review-t7b): the minors
def test_lost_out_of_reach_marks_the_fallen_target_and_takes_the_ladder(tmp_path):
    """Fix 1 (review-t7b m1): `done lost` why out of reach (the walk to a fallen target's head did not close, the Lua's
    K.STOMP_APPROACH_MS bound) leaves the target unreachable for SEEK_SKIP_S, as the ladder's failed stomp walk is
    left, and the next choose is the ladder's; why no progress leaves it for UNREACHABLE_S, the ladder's own mark."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.4, floor=True)])
    f = fight(r)
    a = f.step()
    assert (a.type, a.args["mode"]) == ("melee", "finish")
    act(r, a, "accepted")
    done(r, a, why="out of reach")
    r.advance(0.5)
    fr(r, [z(9, 102.4, floor=True)])
    assert f.step() is None and f.unreachable[9] == r.clock() + P.SEEK_SKIP_S
    assert (f.why["melee_end"]["end"], f.why["melee_end"]["why"]) == ("lost", "out of reach") and f.m is None
    r = rig(tmp_path, "stall")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, why="no progress", swings=3)
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    assert f.step() is None and f.unreachable[9] == r.clock() + P.UNREACHABLE_S





def test_interrupted_timeout_and_no_target_back_off_to_the_ladder(tmp_path):
    """Fix 1 (review-t7b m2): a melee ended `interrupted`, `timeout` or `no target` leaves its target to the ladder for
    MELEE_BACKOFF_TICKS planner ticks (Survive's FAILED_COOLDOWN_TICKS), logged `melee_end` {.., backoff}. Task 8 fix 1
    (a named change): only with nobody standing within KEEP_R; with the target within it (2.0 tiles here) no backoff is
    set and the next choose is the melee, logged `engage_dispatch` {from: the end}."""
    assert P.MELEE_BACKOFF_TICKS == S.FAILED_COOLDOWN_TICKS
    for state, reason in (("failed", "interrupted"), ("timeout", ""), ("rejected", "no target")):
        r = rig(tmp_path, state)
        fr(r, [z(9, 102.0)])
        f = fight(r)
        a = f.step()
        if state == "timeout":
            a.state = "timeout"
        else:
            act(r, a, state, reason)
        r.advance(0.5)
        fr(r, [z(9, 102.0)])
        b = f.step()
        assert f.why["melee_end"]["end"] == (reason or "timeout") and "backoff" not in f.why["melee_end"]
        assert b.type == "melee" and f.why["melee"]["engage_dispatch"] == {"from": reason or "timeout"}





def test_a_maneuver_without_kills_or_a_span_is_observed_whole(tmp_path):
    """Plan 28 close fix 1 (review-close item 14): `_observe_maneuver` takes kills and a span off every maneuver, so the
    base defines them (`[]`, None) and a subclass that overrides neither is observed with no AttributeError and no kill
    read, running and retired."""
    class Bare(Maneuver):
        name = "bare"

        def step(self):
            return None

    r = rig(tmp_path, "done")
    f = fight(r)
    dead = []
    f._read_dead = dead.append
    f.m = Bare(r.world, r.acts, r.clock)
    f._spent_m = [Bare(r.world, r.acts, r.clock)]
    f._observe_maneuver()
    assert dead == [] and f.m.take_kills() == [] and f.m.take_span() is None


def test_the_decision_line_carries_the_ladder_the_press_leaf_and_the_end(tmp_path):
    """Fix 1 (review-t7b m3): Survive's decision line (the threat branch's why) carries `ladder` on the dispatching
    tick, the last press leaf in `maneuver` once a line carried one (PZA/1.10), and `melee_end` {.., end, why} on the
    choose after an end."""
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "melee" and w["ladder"] == "aim" and "resend" not in w["melee"] and "melee_end" not in w
    act(r, a, "accepted")
    leaf = {"d_press": 1.2, "d_collide_pred": 0.8, "d_min": 1.2, "look_off": 12.5, "hp0": 1.0, "hp1": 0.8,
            "knock": False, "cut_by": ""}
    act(r, a, "progress", result={"step": "face", "d": 1.5, "hp": 0.8, "swings": 1, "shoves": 0, "stomps": 0,
                                  "floors": 0, "knockdowns": 0, "hits": 0, "spent": False, "press": leaf})
    r.advance(0.5)
    fr(r, [z(9, 101.5)])
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["maneuver"]["press"] == leaf and w["maneuver"]["spent"] is False
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 102.6)])
    c = tick(r, sv)
    w = threat_why(tmp_path)
    assert c.type == "aim" and (w["melee_end"]["end"], w["melee_end"]["why"]) == ("lost", "out of range")
    assert w["melee_end"]["sends"] == 1


def test_the_fake_s_default_caps_are_the_pza1_7_build_s_literal_list():
    """Fix 1 (review-t7b m4): `fakemod.DEFAULT_HELLO`'s caps are a literal list (`CAPS_17`), the schema's types as they
    stood before PZA/1.8's `melee`; `MELEE_CAPS` adds it."""
    from . import fakemod
    from agent.base import pza1
    pre = pza1.ACTION_TYPES[:pza1.ACTION_TYPES.index("melee")]
    assert tuple(fakemod.DEFAULT_HELLO["caps"]) == fakemod.CAPS_17 == pre
    assert fakemod.MELEE_CAPS == list(fakemod.CAPS_17) + ["melee"]


def test_the_re_send_waits_for_a_press_in_flight(tmp_path):
    """Fix 1 (review-t7c M1): a mode change read while a swing is in flight (its progress line's step `swing`) holds
    the re-send, so the Lua reads the press's result; the first tick after it (its step `face`) re-sends."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.4)
    act(r, a, "progress", result={"step": "swing", "d": 1.0})
    r.advance(0.1)
    fr(r, [z(9, 101.0)])
    f.spent = ("arms",)
    assert f.step() is None and f.busy() and f.m.action is a
    r.advance(0.2)
    act(r, a, "progress", result={"step": "face", "d": 1.1})
    r.advance(0.1)
    fr(r, [z(9, 101.1)])
    b = f.step()
    assert b.type == "melee" and b.args["mode"] == "shove" and f.why["melee"]["resend"] == "inputs"


def test_a_handback_with_the_frame_behind_still_gives_the_ladder_the_choose(tmp_path):
    """Fix 1 (review-t7b M1): the Lua reads the other zombie live, the frame up to a tenth of a second behind it, the
    next frame still listing 8 beyond STAND_MIN_R (0.9 tiles). Task 8 fix 1 (a named change, reversing M1's "never a
    fresh melee on the geometry the Lua refused" under `work`, whose pile meets the crowd): the handback in contact is
    followed by the melee at the pin, never a ladder leg."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 100.4), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, end="handback", why="crowd", id=8, d=0.55)
    r.advance(0.5)
    fr(r, [z(9, 100.4), z(8, 100.0, 200.9)])
    b = f.step()
    assert b.type == "melee" and f.why["melee_end"]["end"] == "handback"
    assert f.why["melee"]["engage_dispatch"] == {"from": "handback"}





# ================================================================ Task 7e (ruling P28-H, from E22's reading)
def test_the_shove_is_sent_inside_its_reach(tmp_path):
    """P28-H 1: the melee's `shoveR` is SHOVE_SEND_R (0.9), inside the engine's shove reach SHOVE_R (1.1, #4592), which
    stays the planner's refusal bound: E22's eight shoves at 1.068 to 1.100 tiles knocked nothing down."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    a = fight(r).step()
    assert a.args["shoveR"] == P.SHOVE_SEND_R == 0.9 and P.SHOVE_SEND_R < P.SHOVE_R == 1.1


def test_the_arms_pain_alone_keeps_the_melee_in_strike_mode(tmp_path):
    """P28-H 3: at `body.armPain` 30 (over STRAIN_HARD, P24-AP's bar on the ladder's swing) the ladder's backpedal at a
    chaser 2.0 tiles off is the melee in mode `strike` (the swing at the reach, where T86 read every swing landing),
    logged `melee` {mode, pain}; the floor swing stays allowed (P28-C). A hold or a shove-only Fight under the same
    pain still shoves."""
    r = rig(tmp_path, "pain")
    fr(r, [z(9, 102.0)], 30.0)
    f = fight(r)
    a = f.step()
    assert (a.type, a.args["mode"], f.why["leg"]) == ("melee", "strike", "back") and a.args["floorSwing"] is True
    assert f.why["melee"] == {"mode": "strike", "pain": 30.0} and f.why["wounded"] == 30.0
    for k in ({"spent": ("arms",)}, {"shove_only": "low"}):
        r = rig(tmp_path, sorted(k)[0])
        fr(r, [z(9, 102.0)], 30.0)
        f = fight(r, **k)
        a = f.step()
        assert (a.type, a.args["mode"]) == ("melee", "shove") and f.why["melee"] == {"mode": "shove", "pain": 30.0}, k


def test_lost_no_progress_alone_marks_the_target_for_unreachable_s(tmp_path):
    """Fix 1 (review-t2 F7): a `done lost` why no progress whose span counts no strike (so the no-progress streak does
    not mark it) still leaves the target unreachable for UNREACHABLE_S, the dispatch's own branch
    (`LOST_UNREACHABLE`); why out of range leaves it unmarked."""
    for why, marked in (("no progress", True), ("out of range", False)):
        r = rig(tmp_path, why.replace(" ", "_"))
        fr(r, [z(9, 102.0)])
        f = fight(r)
        a = f.step()
        act(r, a, "accepted")
        done(r, a, why=why, swings=0)
        r.advance(0.5)
        fr(r, [z(9, 102.0)])
        f.step()
        assert (9 in f.unreachable) is marked, why
        if marked:
            assert f.unreachable[9] == r.clock() + P.UNREACHABLE_S and f.no_progress == 0
    assert P.HEAD_AIM is False


def test_the_press_leaf_s_body_off_and_facing_are_kept_where_the_leaf_carries_them(tmp_path):
    """Plan 32 Task 4: the melee maneuver keeps the leaf's body_off and facing (the body off the bearing at the press
    and the press mode) when the line carries them, and adds no key to a leaf without them (a PZA/1.10 log's
    decision lines unchanged)."""
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    a = tick(r, sv)
    act(r, a, "accepted")
    leaf = {"d_press": 1.2, "d_collide_pred": 0.8, "d_min": 1.2, "look_off": 1.5, "hp0": 1.0, "hp1": 0.8,
            "knock": False, "cut_by": "", "body_off": 2.5, "facing": "unaimed_snap"}
    act(r, a, "progress", result={"step": "face", "d": 1.5, "hp": 0.8, "swings": 1, "shoves": 0, "stomps": 0,
                                  "floors": 0, "knockdowns": 0, "hits": 0, "spent": False, "press": leaf})
    r.advance(0.5)
    fr(r, [z(9, 101.5)])
    tick(r, sv)
    assert threat_why(tmp_path)["maneuver"]["press"] == leaf
    old = {k: v for k, v in leaf.items() if k not in ("body_off", "facing")}
    act(r, a, "progress", result={"step": "face", "d": 1.5, "hp": 0.8, "swings": 2, "shoves": 0, "stomps": 0,
                                  "floors": 0, "knockdowns": 0, "hits": 0, "spent": False, "press": old})
    r.advance(0.5)
    fr(r, [z(9, 101.5)])
    tick(r, sv)
    assert threat_why(tmp_path)["maneuver"]["press"] == old
