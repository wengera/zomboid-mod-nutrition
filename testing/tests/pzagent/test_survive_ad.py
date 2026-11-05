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
  alone no longer selects it), finish at a fallen pin;
  `reach` the frame's `weapon.reach` plus ATTACK_MARGIN, 0 without one; the `back` heading with P28-E's arc, fresh at
  each send), re-sent MELEE_RESEND_MARGIN_S before MELEE_S runs out (`resend` "early") and after a `done time`
  (`resend` "time"); its ends mapped (`out of range` to the ladder's path, `crowd` to a re-pin to the nearer,
  `stood` to the ladder, a span with strikes and no health fall to the no-progress mark, a kill read once); a flee's
  hand-over supersedes it; the corner, the door fight and the doorway stand keep the ladder; without the cap or with
  the rule off the ladder as before.
"""
import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers import Maneuver, Melee
from agent.base.pza1 import Scan

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
ARC = P._rotate((-1.0, 0.0), P.CIRCLE_TURN)   # the `back` heading from a lone zombie due east, P28-E's first side
STRIKE_R = BAT["reach"] + P.ATTACK_MARGIN      # the rig's bat's reach and ATTACK_MARGIN (`FightReach.reach_r`)
DONE_TIME = {"end": "time", "kill": False, "swings": 0, "shoves": 0, "stomps": 0, "floors": 0, "knockdowns": 0,
             "hits": 0, "hp0": 1.0, "hp1": 1.0, "dMin": 1.2, "steps": {"stand": 25}}


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
    act(r, a, "done", result=dict(DONE_TIME, **res))


def want(target, mode="strike", reach=STRIKE_R, back=ARC, floor=True):
    """A melee's wire args: `floorSwing` left off when False (`pza1._Cmd.args`)."""
    out = {"targetId": target, "mode": mode, "reach": reach, "keepR": P.KEEP_R, "shoveR": P.SHOVE_SEND_R,
           "releaseR": P.MELEE_RELEASE_R, "backVx": back[0], "backVy": back[1], "seconds": P.MELEE_S, "closeR": 0.0}
    if floor:
        out["floorSwing"] = True
    return out


def test_the_melee_constants_are_the_policies_table_s():
    """MELEE_S 2.5 (between AIM_LEG_S and the re-send's cost), its re-send MELEE_RESEND_MARGIN_S 0.5 before it (one
    planner tick at the drivers' PLANNER_HZ 2), the release KEEP_R + KEEP_MARGIN (the backpedal's own give-way)."""
    assert (P.MELEE_S, P.MELEE_RESEND_MARGIN_S) == (2.5, 0.5)
    assert P.AIM_LEG_S < P.MELEE_S and P.MELEE_RELEASE_R == P.KEEP_R + P.KEEP_MARGIN == 2.75


def test_a_standing_fight_s_target_within_keep_r_starts_melee_with_each_argument_from_its_source(tmp_path):
    """A chaser 2.0 tiles off (within FIGHT_REACH, the stance not held): where the ladder sends the `enter` leg, the
    melee goes: `mode` strike, `reach` the bat's 1.2 plus ATTACK_MARGIN, `keepR` KEEP_R, `shoveR` SHOVE_SEND_R (P28-H),
    `releaseR` MELEE_RELEASE_R, `seconds` MELEE_S, `floorSwing` true, the `back` heading the circle's arc off the
    straight away heading; logged `maneuver` {maneuver melee, target, mode, sends 1} beside the ladder's own why."""
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


def test_the_back_heading_is_straight_with_circle_off_or_a_second_zombie_within_keep_r(tmp_path):
    """P28-E's arc only from a lone standing zombie within KEEP_R with `circle` on; else the straight away heading."""
    for i, (zs, rules) in enumerate((([z(9, 102.0)], {"circle"}), ([z(9, 102.0), z(7, 100.0, 202.2)], set()))):
        r = rig(tmp_path, str(i))
        fr(r, zs)
        f = fight(r, target=9)
        f.rules = f.rules - rules
        a = f.step()
        assert a.type == "melee" and (a.args["backVx"], a.args["backVy"]) == (-1.0, 0.0)
        assert "circle" not in f.why


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


def test_the_corner_and_the_door_fight_keep_the_ladder(tmp_path):
    """Cut 1 leaves the corner (`point_blank`) and the door fight (`only`) to the ladder: their attack goes."""
    for k in ({"point_blank": True}, {"only": {9}}):
        r = rig(tmp_path, sorted(k)[0])
        fr(r, [z(9, 101.0)])
        f = fight(r, **k)
        f.target = 9
        a = f.step()
        assert (a.type, a.args) == ("attack", {"targetId": 9}) and f.m is None, k


def test_the_melee_switch_is_iteration_22_s_and_drops_its_rule(tmp_path):
    """`MELEE` on `threat.Threat`, on by default, the first (and only) name of `survive.T12_SWITCHES`; off, the
    Fight's `rules` lack `melee`."""
    assert T.Threat.MELEE is True and S.T12_SWITCHES == ("MELEE",) and "melee" in F.FIGHT_RULES
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    on = sv._fight_rules()
    sv.MELEE = False
    assert "melee" in on and sv._fight_rules() == on - {"melee"}


# ================================================================ the re-sends
def test_the_melee_is_re_sent_early_with_a_fresh_heading_before_its_seconds_run_out(tmp_path):
    """Held (`busy`) until MELEE_S - MELEE_RESEND_MARGIN_S after its accept, then re-sent at the same target (the Lua
    keeps the stance across it) with the `back` heading recomputed: the zombie moved due south, the arc turns off
    north; logged `melee` {resend "early"}, `maneuver` sends 2."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(P.MELEE_S - P.MELEE_RESEND_MARGIN_S - 0.5)
    fr(r, [z(9, 100.0, 202.0)])
    assert f.step() is None and f.busy()
    r.advance(0.5)
    fr(r, [z(9, 100.0, 202.0)])
    b = f.step()
    assert (b.type, b.args) == ("melee", want(9, back=P._rotate((0.0, -1.0), P.CIRCLE_TURN)))
    assert f.why["melee"]["resend"] == "early" and f.why["maneuver"]["sends"] == 2 and f.m.action is b


def test_a_done_time_re_sends_while_the_target_stands(tmp_path):
    """A `done` `time` with the target standing: the next step re-sends (the stance taken again), logged `melee`
    {resend "time"}."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    b = f.step()
    assert b.type == "melee" and f.why["melee"]["resend"] == "time" and f.m.n == 2


# ================================================================ the ends
def test_out_of_range_takes_the_ladder_s_path_for_one_choose(tmp_path):
    """`failed out of range`: the next choose is the ladder's whatever it sends (the frame may still read the target
    within KEEP_R: its `back` leg), logged `melee_end` {.., end}; the choose after that leg's end dispatches again;
    beyond KEEP_R the ladder's `stand`."""
    r = rig(tmp_path, "lag")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    act(r, a, "failed", "out of range")
    r.advance(0.5)
    fr(r, [z(9, 102.3)])
    b = f.step()
    assert (b.type, f.why["leg"]) == ("aim", "back") and f.why["melee_end"]["end"] == "out of range"
    assert f.m is None and "maneuver" not in f.why
    act(r, b, "done", result={})
    r.advance(0.5)
    fr(r, [z(9, 102.3)])
    assert f.step().type == "melee"
    r = rig(tmp_path, "far")
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "failed", "out of range")
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
    b = f.step()
    assert (b.type, f.why["leg"]) == ("aim", "enter") and f.why["melee_end"]["end"] == "too far"


def test_crowd_re_pins_to_the_other_zombie_the_lua_reports_nearer(tmp_path):
    """`failed crowd` {id, d}: the other standing zombie the engine's press would take (within K.STAND_R 0.6, where
    the Lua fails it) is pinned when it is nearer than the target, and the next melee goes at it. Fix 1 (review-t7b
    M1): the geometry the Lua reports, 8 closing from 0.9 tiles to 0.55 while pin 9 stands 1.0 off."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9)
    act(r, a, "accepted")
    act(r, a, "failed", "crowd", result={"id": 8, "d": 0.55})
    r.advance(0.5)
    fr(r, [z(9, 101.0), z(8, 100.0, 200.55)])
    b = f.step()
    assert (b.type, b.args["targetId"], f.target) == ("melee", 8, 8) and f.why["melee_end"]["end"] == "crowd"


def test_a_crowd_end_that_re_pins_nothing_gives_the_ladder_its_press(tmp_path):
    """Fix 1 (review-t7b M1, the loop's probe): pin 9 at 0.4 tiles, 8 closing to 0.55 (the Lua's `crowd`, 8 not the
    nearer): no fresh melee on that geometry. The crowd end hands the next choose to the ladder (`_m_ladder`), and while
    8 stands within STAND_MIN_R of the player no melee is dispatched (`_melee_mode`): over six ticks the ladder's leg
    and its swing go as with the rule off, never a melee that the Lua would fail `crowd` with no press."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 100.4), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9)
    act(r, a, "accepted")
    act(r, a, "failed", "crowd", result={"id": 8, "d": 0.55})
    sends = []
    for k in range(6):
        r.advance(0.5)
        fr(r, [z(9, 100.4), z(8, 100.0, 200.55)])
        b = f.step()
        if k == 0:
            assert f.why["melee_end"]["end"] == "crowd" and f.target == 9
        if b is not None:
            sends.append((b.type, b.args.get("targetId")))
            act(r, b, "accepted")
            if b.type != "aim":
                act(r, b, "done", result={"attackStarted": True, "knockdown": False, "targetDead": False})
    assert ("attack", 9) in sends and not any(t == "melee" for t, _ in sends) and f.m is None


def test_no_melee_while_another_standing_zombie_is_within_stand_min_r(tmp_path):
    """Fix 1 (review-t7b M1): a second standing zombie within STAND_MIN_R of the player keeps the ladder's command (its
    P24-AH rules own that tick, the Lua's press would take that zombie); a fallen one there, or one beyond it, does
    not."""
    for i, (other, melee) in enumerate(((z(8, 100.0, 200.55), False), (z(8, 100.0, 200.55, floor=True), True),
                                        (z(8, 100.0, 200.7), True))):
        r = rig(tmp_path, str(i))
        fr(r, [z(9, 101.0), other])
        f = fight(r, target=9)
        a = f.step()
        assert (a.type == "melee") is melee, other


def test_a_marked_attacker_at_point_blank_re_pins_through_a_running_melee_on_its_tick(tmp_path):
    """Fix 1 (review-t7b M2): a running melee at pin 9 (1.5 tiles off) gives way to P27-N's pin-first on the tick a
    marked zombie at 0.8 tiles is read attacking (`_pin_marked`, its target not among `_pin_free`), so the Fight pins
    it at +0.5 s as the ladder does, not at the re-send; the pin itself marked at point blank holds the melee."""
    r = rig(tmp_path, "other")
    fr(r, [z(9, 101.5)])
    f = fight(r)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9)
    act(r, a, "accepted")
    r.advance(0.5)
    f.unreachable[8] = r.clock() + P.UNREACHABLE_S
    fr(r, [z(9, 101.5), z(8, 100.0, 200.8)], attackers=1, hit_reaction="Bite")
    assert not f.busy()
    f.step()
    assert f.target == 8 and f.why["pin"] == {"why": "point_blank"}
    r = rig(tmp_path, "self")
    fr(r, [z(9, 100.8)])
    f = fight(r)
    a = f.step()
    assert (a.type, a.args["targetId"]) == ("melee", 9)
    act(r, a, "accepted")
    r.advance(0.5)
    f.unreachable[9] = r.clock() + P.UNREACHABLE_S
    fr(r, [z(9, 100.8)], attackers=1, hit_reaction="Bite")
    assert f.busy() and f.step() is None and f.target == 9


def test_a_finish_whose_target_stood_takes_the_ladder_and_the_strike(tmp_path):
    """A finish failed `stood` (the pin rose): the ladder reads it standing, and the next melee is a strike."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.2, floor=True)])
    f = fight(r)
    a = f.step()
    assert a.args["mode"] == "finish"
    act(r, a, "failed", "stood")
    r.advance(0.5)
    fr(r, [z(9, 101.2)])
    b = f.step()
    assert (b.type, b.args["mode"], f.why["melee_end"]["end"]) == ("melee", "strike", "stood") and f.m.n == 1


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
    nothing at it; a span whose health fell restarts the streak."""
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
    """A `done` {end dead, kill true}: the Fight's `kill` names the target on that observe, the World counts it once,
    and it is read dead for UNREACHABLE_S, unpinned."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    done(r, a, end="dead", kill=True, swings=2, hp1=0.0)
    r.advance(0.5)
    fr(r, [])
    f.step()
    assert f.kill == 9 and r.world.kills == 1 and 9 in f.dead and f.target is None
    assert f.why["melee_end"]["end"] == "dead"
    f.observe()
    assert f.kill is None and r.world.kills == 1


def test_a_kill_on_the_melee_an_early_re_send_superseded_is_read_too(tmp_path):
    """The race the base's late-end read covers: the first melee ends `done` {kill} after its early re-send left
    (the line written before the re-send reached the Lua), and the re-send is rejected `no target`: the kill counts
    once."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(P.MELEE_S - P.MELEE_RESEND_MARGIN_S)
    fr(r, [z(9, 102.0)])
    b = f.step()
    assert b.type == "melee"
    done(r, a, end="dead", kill=True)
    act(r, b, "rejected", "no target")
    r.advance(0.5)
    fr(r, [])
    f.step()
    assert f.kill == 9 and r.world.kills == 1 and f.m is None


def test_a_kill_on_a_melee_the_ladder_s_send_replaced_is_read_too(tmp_path):
    """The Fight's own next command that is no melee (the finish of another fallen zombie) retires the maneuver, whose
    melee's late `done` {kill} is still read (`_spent_m`)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 102.0), z(8, 101.2, floor=True)])
    b = f.step()
    assert b.type == "attack" and f.m is None
    done(r, a, end="dead", kill=True)
    r.advance(0.5)
    fr(r, [z(8, 101.2, floor=True)])
    f.observe()
    assert f.kill == 9 and r.world.kills == 1 and f._spent_m == []


# ================================================================ busy, the hand-over and the log
def test_a_running_melee_gives_way_to_the_finish_of_another_fallen_zombie_and_holds_while_its_pin_falls(tmp_path):
    """`busy` holds a running melee as it holds a leg: it gives way once the finish would take another fallen zombie
    (above the dispatch point), and holds while its own pin falls (the Lua's floor reflexes take it)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(0.5)
    fr(r, [z(9, 101.2, floor=True)])
    assert f.busy() and f.step() is None
    r.advance(0.5)
    fr(r, [z(9, 102.0), z(8, 101.2, floor=True)])
    assert not f.busy()


def test_a_running_melee_gives_way_once_its_target_is_no_longer_the_pin(tmp_path):
    """Another zombie pinned (a re-pin above the dispatch point): the running melee at the old pin gives way."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0), z(7, 100.0, 203.0)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    assert f.busy()
    f.target = 7
    assert not f.busy()


def test_the_survive_tick_logs_the_maneuver_s_step_while_it_holds_and_a_flee_hand_over_supersedes_it(tmp_path):
    """Survive's threat branch: the standing fight's melee sent; a progress line read, the holding tick logs
    `maneuver` {.., step, d} from it; at health 15 (under FLEE_HEALTH_FLOOR, no low fight) the flee's leg goes at once,
    superseding it."""
    r, sv = make(tmp_path, caps=MELEE_CAPS)
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


def test_boxed_in_the_back_heading_is_zero(tmp_path):
    """No clear heading west, north or south of the player (the solid squares round it, the target due east): the
    `back` heading is (0, 0), the Lua standing in the stance after a miss."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    r.scan([square(x, y, solid=True) for x, y in ((99, 199), (99, 200), (99, 201), (100, 199), (100, 201))])
    r.frame(x=100.5, y=200.5, zombies=[dict(z(9, 102.5, 200.5), dist=2.0)])
    a = fight(r).step()
    assert a.type == "melee" and (a.args["backVx"], a.args["backVy"]) == (0.0, 0.0)


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
    b = f.step()
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
        act(r, a, "accepted")
        done(r, a, **res)
        r.advance(0.5)
        fr(r, [z(9, 102.0)])
        f.observe()
        assert f.no_progress == n, res
    a = f.step()
    act(r, a, "accepted")
    done(r, a, swings=0, floors=1, stomps=1)
    r.advance(0.5)
    fr(r, [z(9, 102.0)])
    assert f.step() is None and 9 in f.unreachable


def test_the_re_send_is_timed_from_the_accept(tmp_path):
    """The early re-send reads the running melee's accept wall: accepted 0.5 s after its send, it is held until
    MELEE_S - MELEE_RESEND_MARGIN_S after the accept."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    a = f.step()
    r.advance(0.5)
    act(r, a, "accepted")
    r.advance(P.MELEE_S - P.MELEE_RESEND_MARGIN_S - 0.25)
    fr(r, [z(9, 102.0)])
    assert f.step() is None
    r.advance(0.25)
    fr(r, [z(9, 102.0)])
    assert f.step().type == "melee" and f.why["melee"]["resend"] == "early"


def test_a_melee_whose_send_another_sender_superseded_sends_nothing_and_ends(tmp_path):
    """`Melee.step` unobserved: once another sender's action is current, its running melee no longer runs, and the
    step ends it `superseded` instead of re-sending."""
    from agent.base.planner.maneuvers.melee import MeleeInputs
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Melee(r.world, r.acts, r.clock, 9)
    m.inputs = MeleeInputs("strike", 0.0, (0.0, 0.0), False)
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
    at a zombie that is not the pin)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    f = fight(r)
    f._shoved = True
    a = f.step()
    act(r, a, "accepted")
    done(r, a)
    r.advance(0.5)
    fr(r, [z(9, 101.2, floor=True), z(8, 100.0, 200.9)])
    b = f.step()
    assert (b.type, b.args) == ("shove", {"targetId": 8}) and f.why["shove"] == "first"


# ================================================================ fix 1 (review-t7b): the minors
def test_out_of_reach_marks_the_fallen_target_and_takes_the_ladder(tmp_path):
    """Fix 1 (review-t7b m1): `failed out of reach` (the stomp's walk to a fallen target did not close) leaves the
    target unreachable for SEEK_SKIP_S, as the ladder's failed stomp walk is left, and the next choose is the
    ladder's."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.4, floor=True)])
    f = fight(r)
    a = f.step()
    assert (a.type, a.args["mode"]) == ("melee", "finish")
    act(r, a, "accepted")
    act(r, a, "failed", "out of reach")
    r.advance(0.5)
    fr(r, [z(9, 102.4, floor=True)])
    assert f.step() is None and f.unreachable[9] == r.clock() + P.SEEK_SKIP_S
    assert f.why["melee_end"]["end"] == "out of reach" and f.m is None


def test_the_walk_to_a_fallen_target_is_bounded_across_the_sends(tmp_path):
    """Fix 1 (review-t7b m1): the Lua's `seconds` (MELEE_S) end a melee before its walk's own bound
    (K.STOMP_APPROACH_MS) and each send restarts that walk, so the maneuver keeps the walk's clock: a `done` whose last
    step is still `stomp_walk` MELEE_WALK_S after the walk's first progress line ends it `out of reach`, the target
    marked; a walk that reached its stomp in between restarts the clock."""
    for reached in (False, True):
        r = rig(tmp_path, str(reached))
        fr(r, [z(9, 102.4, floor=True)])
        f = fight(r)
        a = f.step()
        act(r, a, "accepted")
        act(r, a, "progress", result={"step": "stomp_walk", "d": 2.4})
        f.observe()
        r.advance(P.MELEE_S)
        done(r, a)
        fr(r, [z(9, 102.4, floor=True)])
        b = f.step()
        assert b.type == "melee" and f.why["melee"]["resend"] == "time"
        act(r, b, "accepted")
        act(r, b, "progress", result={"step": "stomp" if reached else "stomp_walk", "d": 1.6})
        act(r, b, "progress", result={"step": "stomp_walk", "d": 1.6})
        r.advance(P.MELEE_WALK_S - P.MELEE_S)
        done(r, b)
        fr(r, [z(9, 102.4, floor=True)])
        c = f.step()
        if reached:
            assert c.type == "melee" and 9 not in f.unreachable
        else:
            assert c is None and f.why["melee_end"]["end"] == "out of reach" and 9 in f.unreachable


def test_interrupted_timeout_and_no_target_back_off_to_the_ladder(tmp_path):
    """Fix 1 (review-t7b m2): a melee ended `interrupted`, `timeout` or `no target` leaves its target to the ladder for
    MELEE_BACKOFF_TICKS planner ticks (Survive's FAILED_COOLDOWN_TICKS), logged `melee_end` {.., backoff}; the tick
    after them dispatches again."""
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
        for k in range(1, P.MELEE_BACKOFF_TICKS + 2):
            r.advance(0.5)
            fr(r, [z(9, 102.0)])
            b = f.step()
            if k == 1:
                assert f.why["melee_end"]["end"] == (reason or "timeout") and f.why["melee_end"]["backoff"] == 10
            assert (b.type == "melee") is (k > P.MELEE_BACKOFF_TICKS), (reason, k)
            if b.type != "melee":
                act(r, b, "done", result={})


def test_the_melee_walk_bound_is_the_lua_s_stomp_approach(lua):
    """Plan 28 close fix 1 (review-close item 13): `MELEE_WALK_S` (the planner-side bound on the walk to a fallen target
    across re-sends, fix 1's residual `c2b6bae2`) mirrors the stance skill's `K.STOMP_APPROACH_MS`, read here off the
    loaded Lua; a tune of one side without the other breaks that bound."""
    load(lua)
    assert P.MELEE_WALK_S * 1000 == lua.eval("PZA.skills.STOMP_APPROACH_MS")


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


def test_the_decision_line_carries_the_ladder_the_re_send_and_the_end(tmp_path):
    """Fix 1 (review-t7b m3): Survive's decision line (the threat branch's why) carries `ladder` on the dispatching
    tick, `melee` {resend "early"} on the early re-send, and `melee_end` {.., end} on the choose after an end."""
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.0)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "melee" and w["ladder"] == "aim" and "resend" not in w["melee"] and "melee_end" not in w
    act(r, a, "accepted")
    r.advance(P.MELEE_S - P.MELEE_RESEND_MARGIN_S)
    fr(r, [z(9, 102.0)])
    b = tick(r, sv)
    assert b.type == "melee" and threat_why(tmp_path)["melee"]["resend"] == "early"
    act(r, b, "accepted")
    act(r, b, "failed", "out of range")
    r.advance(0.5)
    fr(r, [z(9, 102.6)])
    c = tick(r, sv)
    w = threat_why(tmp_path)
    assert c.type == "aim" and w["melee_end"]["end"] == "out of range" and w["melee_end"]["sends"] == 2


def test_the_fake_s_default_caps_are_the_pza1_7_build_s_literal_list():
    """Fix 1 (review-t7b m4): `fakemod.DEFAULT_HELLO`'s caps are a literal list (`CAPS_17`), the schema's types as they
    stood before PZA/1.8's `melee`; `MELEE_CAPS` adds it."""
    from . import fakemod
    from agent.base import pza1
    pre = pza1.ACTION_TYPES[:pza1.ACTION_TYPES.index("melee")]
    assert tuple(fakemod.DEFAULT_HELLO["caps"]) == fakemod.CAPS_17 == pre
    assert fakemod.MELEE_CAPS == list(fakemod.CAPS_17) + ["melee"]


def test_the_early_re_send_waits_for_a_strike_in_flight(tmp_path):
    """Fix 1 (review-t7c M1): a swing pressed 1.9 s after the accept (its progress line's step `swing`) holds the
    early re-send past MELEE_S - MELEE_RESEND_MARGIN_S, so the Lua reads the strike's end; the first tick after the
    strike (its step `back`) re-sends."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 101.0)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    r.advance(1.9)
    act(r, a, "progress", result={"step": "swing", "d": 1.0})
    r.advance(0.1)
    fr(r, [z(9, 101.0)])
    assert f.step() is None and f.busy() and f.m.action is a
    r.advance(0.2)
    act(r, a, "progress", result={"step": "back", "d": 1.1})
    r.advance(0.1)
    fr(r, [z(9, 101.1)])
    b = f.step()
    assert b.type == "melee" and f.why["melee"]["resend"] == "early"


def test_a_crowd_end_with_the_frame_behind_still_gives_the_ladder_the_choose(tmp_path):
    """Fix 1 (review-t7b M1): the Lua reads the other zombie live, the frame up to a tenth of a second behind it; with
    the next frame still listing 8 beyond STAND_MIN_R (0.9 tiles, so the guard reads nothing), the crowd end alone
    hands that choose to the ladder: its leg, never a fresh melee on the geometry the Lua refused."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 100.4), z(8, 100.0, 200.9)])
    f = fight(r, target=9)
    a = f.step()
    act(r, a, "accepted")
    act(r, a, "failed", "crowd", result={"id": 8, "d": 0.55})
    r.advance(0.5)
    fr(r, [z(9, 100.4), z(8, 100.0, 200.9)])
    b = f.step()
    assert b.type == "aim" and f.why["melee_end"]["end"] == "crowd" and f.m is None


def test_the_walk_s_bound_fires_across_early_re_sends(tmp_path):
    """Fix 1's residual (review-t7b re-review): a finish melee walking to a fallen pin it cannot reach is re-sent early
    every MELEE_S - MELEE_RESEND_MARGIN_S, before any `done`; the walk's bound is read on the observe, summed across the
    re-sends, so by MELEE_WALK_S of `stomp_walk` the target is unreachable for SEEK_SKIP_S and the ladder takes the
    next choose."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    fr(r, [z(9, 102.4, floor=True)])
    f = fight(r)
    a = f.step()
    act(r, a, "accepted")
    act(r, a, "progress", result={"step": "stomp_walk", "d": 2.4})
    t0, resends = r.clock(), 0
    while r.clock() - t0 < P.MELEE_WALK_S - 0.25:
        r.advance(0.5)
        fr(r, [z(9, 102.4, floor=True)])
        b = f.step()
        assert 9 not in f.unreachable and f.m is not None
        if b is not None:
            assert b.type == "melee" and f.why["melee"]["resend"] == "early"
            resends += 1
            act(r, b, "accepted")
            act(r, b, "progress", result={"step": "stomp_walk", "d": 2.4})
    r.advance(0.5)
    fr(r, [z(9, 102.4, floor=True)])
    assert f.step() is None and f.unreachable[9] == r.clock() + P.SEEK_SKIP_S
    assert resends >= 1 and f.why["melee_end"]["end"] == "out of reach" and f.m is None


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
