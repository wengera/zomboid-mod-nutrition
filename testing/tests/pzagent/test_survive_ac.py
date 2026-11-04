"""Survival 23 (survival iteration 21; Plan 28 Task 3; F11, `f_goals_12-20261103-144240`, its `GUIDE.md` §§ 2, 3 and 5:
the seven bites, five after a shove at point blank that knocked nothing down, the ten `out_of_reach` lines while 14725
closed from 7.712846482962758 tiles after the corner's break, the 22 shoves and no swing at 14725 under the arms' pain,
the stomp a145 at 14725 refused `busy` while a144 ran at 14630, then 14725 left lying 2.5172987398919933 tiles off, the
scratched parts 4, 6 and 8 never dressed; rows #4580, #4581, #4583 and #4585; the jar read's shove reach, #4592). The
fake mod over PZA/1.7.2 (the part record's `wound`); each test's geometry is simplified from the line its docstring
names.

- P28-D, a `busy` rejection is no refusal (`BUSY_RETRY`): a shove or a stomp `rejected` `busy` leaves no
  `swing_refused` record; the next send of that kind at that id is logged `busy_retry` {target, kind}.
- P28-C, the floor swing under the arms' pain (`FLOOR_PAIN`): the swing at a fallen zombie within FIGHT_REACH barred by
  a hold or a shove-only Fight, never by `arms_hurt` alone (logged `floor_finish` {.., pain}); the non-stance Fight's
  walk to a zombie beyond FIGHT_REACH at a walk (logged `leg` "walk").
- P28-A, the wound dressed (`WOUND_DRESS`): a part reading `wound`, not bleeding and not bandaged, dressed with the best
  clean dressing while more than WOUND_RESERVE are held and no zombie is within DANGER_R (logged `reason` "wound"),
  else `wound_held` {part, clean}; nothing to dress it beyond the reserve and no garment marks the want `bandage`.
"""
import math

import pytest

from agent.base.planner import care as C
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base import pza1
from agent.base.pza1 import Shove, Stomp

from .test_policies import Rig, square
from .test_survive import last, make, threat_why, tick
from .test_survive_g import care_frame, care_why, garment, hello152, hold, part
from .test_survive_q import DONE_SHOVE, GROUP3, STIFF, fr, z


def fight(r, **k):
    """A Fight on the rig (every rule of `fight.FIGHT_RULES` on), `k` set on it."""
    f = F.Fight(r.world, r.acts, r.clock)
    for name, v in k.items():
        setattr(f, name, v)
    return f


def end(r, a, state, reason="", result=None):
    """Action `a` ends `state` (`reason`, `result`) by its act line."""
    r.fake.act(a.aid, state, a.type, reason=reason, result=result)
    r.pump()


def accept(r, a):
    r.fake.act(a.aid, "accepted", a.type)
    r.pump()


# ================================================================ P28-D: a `busy` rejection is no refusal
F11_LYING = 2.5172987398919933   # a146's 14725 read fallen this far off on lines 642-651, nothing within 6 tiles


def busy_rig(tmp_path, reason="busy"):
    """F11's a144 to a146 simplified (lines 630 to 642): a Fight cornered as F11's was (`point_blank`) sent the stomp
    a145 at 14725, fallen 1.2 tiles off, while its attack a144 at 14630 ran; the stomp's end is `rejected` `reason`;
    then 14630 reads dead (its corpse listed 0.5 tiles off) and 14725 fallen F11_LYING tiles off, no standing zombie
    within KEEP_R. Returns (r, f) before the next step."""
    r = Rig(tmp_path)
    r.frame(zombies=[z(14725, 101.2, floor=True)])
    f = fight(r, point_blank=True)
    end(r, f.send(Stomp(14725)), "rejected", reason)
    r.advance(0.5)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True), z(14630, 99.5, floor=True)])
    f.dead[14630] = r.clock() + P.UNREACHABLE_S
    return r, f


def test_f11_s_stomp_rejected_busy_goes_again_on_the_next_tick(tmp_path):
    """F11's line 642: 14725 lies F11_LYING tiles off (beyond FIGHT_REACH, within FINISH_R) with nobody standing near,
    and the stomp a145 refused `busy` while a144 ran: no refusal is recorded at 14725, so the finish rule lists it and
    the stomp goes again (its walk in), logged `busy_retry` {target 14725, kind "stomp"}, the latch cleared."""
    r, f = busy_rig(tmp_path)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 14725})
    assert f.why["busy_retry"] == {"target": 14725, "kind": "stomp"} and f.why["downed"] == 14725
    assert ("stomp", 14725) not in f.swing_refused and f._busy_retry is None


def test_with_busy_retry_off_the_busy_stomp_is_refused_and_the_drifted_pin_holds_out_of_reach(tmp_path):
    """The same with the `busy_retry` rule off (Survive's `BUSY_RETRY`): the refusal holds the stomp off 14725 for
    SWING_SKIP_S, the finish rule leaves it out beyond FIGHT_REACH, and the cornered Fight sends nothing
    (`out_of_reach`), F11's lines 642 to 651."""
    r, f = busy_rig(tmp_path)
    f.rules = f.rules - {"busy_retry"}
    assert f.step() is None and f.why["out_of_reach"] is True and "busy_retry" not in f.why
    assert ("stomp", 14725) in f.swing_refused


def test_a_stomp_rejected_not_valid_is_refused_for_swing_skip_s_as_before(tmp_path):
    """A stomp `rejected` `not valid` says something about the target: no stomp at it for SWING_SKIP_S (P24-AL), then
    the stomp, never logged `busy_retry`."""
    r, f = busy_rig(tmp_path, "not valid")
    assert f.step() is None and f.why["out_of_reach"] is True and "busy_retry" not in f.why
    r.advance(P.SWING_SKIP_S - 1.0)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True)])
    assert f.step() is None
    r.advance(1.0)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True)])
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 14725}) and "busy_retry" not in f.why


def test_a_shove_rejected_busy_goes_again(tmp_path):
    """A shove at a chaser at point blank under the arms' pain 30 (P24-AG's) rejected `busy`: the next tick shoves
    again, logged `busy_retry` {target, kind "shove"}; with the rule off the refusal holds the shove off and the
    wounded fight's backpedal goes (P24-AP)."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r = Rig(d)
        fr(r, [z(9, 100.9)], 30.0)
        f = fight(r)
        if not on:
            f.rules = f.rules - {"busy_retry"}
        a = f.step()
        assert (a.type, a.args) == ("shove", {"targetId": 9})
        end(r, a, "rejected", "busy")
        r.advance(0.5)
        fr(r, [z(9, 100.9)], 30.0)
        b = f.step()
        if on:
            assert (b.type, b.args) == ("shove", {"targetId": 9}) and f.why["busy_retry"] == {"target": 9,
                                                                                            "kind": "shove"}
        else:
            assert b.type == "aim" and f.why["leg"] == "back" and "busy_retry" not in f.why


def test_the_busy_latch_clears_on_any_other_end_at_that_id(tmp_path):
    """The latch (`_busy_retry`) is cleared by the next send of its kind at its id, and also by any other end read at
    that id (amendment 4): the stomp rejected `busy`, then a shove at 14725 ended done: the latch is gone."""
    r, f = busy_rig(tmp_path)
    f.observe()
    assert f._busy_retry == ("stomp", 14725)
    f.send(Shove(14725))
    r.answer(DONE_SHOVE)
    f.observe()
    assert f._busy_retry is None


def test_the_busy_retry_switch():
    assert "BUSY_RETRY" in S.T11_SWITCHES and T.Threat.BUSY_RETRY is True and "busy_retry" in F.FIGHT_RULES


# ================================================================ P28-C: the floor swing under the arms' pain
def test_f11_s_fallen_zombie_at_point_blank_under_the_arms_pain_takes_the_floor_swing(tmp_path):
    """F11's a136 (line 610): 14630 read fallen 0.9 tiles off, the arms' pain 30 (P24-AP's STRAIN_HARD passed), the
    bat held, no hold: the Fight's finish is the swing at it, logged `floor_finish` {target, health, pain 30}, where the
    stomp went (each landed stomp took 0.0756 to 0.5496 of its health, #4583); with `FLOOR_PAIN` off the stomp."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.FLOOR_PAIN = on
        fr(r, [z(14630, 100.9, floor=True)], 30.0)
        a = tick(r, sv)
        w = threat_why(d)
        assert w["fight"] is True
        if on:
            assert (a.type, a.args) == ("attack", {"targetId": 14630})
            assert w["floor_finish"] == {"target": 14630, "health": 1.0, "pain": 30.0} and "stomp" not in w
        else:
            assert (a.type, a.args) == ("stomp", {"targetId": 14630}) and "floor_finish" not in w


@pytest.mark.parametrize("hold", [{"spent": ("endurance",)}, {"shove_only": "low"}])
def test_a_hold_or_a_shove_only_fight_still_stomps_the_fallen(tmp_path, hold):
    """The swing at a fallen zombie stays barred by a hold (R2: the endurance hold halves a swing, #4371) and by a
    shove-only Fight (P25-S's low fight; its full swing not due): the stomp."""
    r = Rig(tmp_path)
    fr(r, [z(14630, 100.9, floor=True)], 30.0)
    f = fight(r, **hold)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 14630}) and "floor_finish" not in f.why
    assert f.floor_swing_barred() is True


def test_a_standing_zombie_under_the_arms_pain_is_never_swung_at(tmp_path):
    """P24-AP stands for a standing zombie: one 1.2 tiles off (in reach, beyond point blank) under the arms' pain 30
    takes the wounded backpedal, never an attack; the floor swing's bar alone is lifted (`floor_swing_barred` false
    while `no_swing` reads true)."""
    r = Rig(tmp_path)
    fr(r, [z(1, 101.2)], 30.0)
    f = fight(r)
    a = f.step()
    assert a.type == "aim" and f.why["leg"] == "back" and f.why["wounded"] == 30.0
    assert f.no_swing() is True and f.floor_swing_barred() is False


def test_with_floor_pain_off_the_floor_swing_s_bar_is_no_swing(tmp_path):
    """`floor_swing_barred` falls back to `no_swing` with the rule off: the arms' pain 30 alone bars it then."""
    r = Rig(tmp_path)
    fr(r, [], 30.0)
    f = fight(r)
    assert f.floor_swing_barred() is False
    f.rules = f.rules - {"floor_pain"}
    assert f.floor_swing_barred() is True


def test_the_many_flee_s_finish_swings_at_a_fallen_zombie_under_the_arms_pain(tmp_path):
    """P27-G's flee finish under the arms' pain 30: a zombie fallen 1.8 tiles off (beyond CORNERED_R, within
    FIGHT_REACH), GROUP3 chasing 7.5 off (the `many` flee): the finish is the attack, kind `floor_finish`, logged
    {target, health, pain 30}; with `FLOOR_PAIN` off the stomp."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.FLOOR_PAIN = on
        sv.LISTING_FALLEN = False   # P27-I off: GROUP3 makes `many` with the fallen one counted
        fr(r, [z(1, 101.8, floor=True)] + GROUP3, 30.0)
        a = tick(r, sv)
        w = threat_why(d)
        assert w["flee"] == "many"
        if on:
            assert (a.type, a.args) == ("attack", {"targetId": 1}) and w["kind"] == "floor_finish"
            assert w["floor_finish"] == {"target": 1, "health": 1.0, "pain": 30.0}
        else:
            assert (a.type, a.args) == ("stomp", {"targetId": 1})


@pytest.mark.parametrize("hold", [{"strain": STIFF}, {"endurance": 0.6897225379943848}])
def test_the_flee_s_finish_under_a_hold_still_stomps(tmp_path, hold):
    """The same `many` flee with a hold beside the pain (the arms' stiffness past STIFF_HARD, or E18's endurance
    0.6897225379943848, R2): the hold bars the swing at the fallen one, the stomp goes."""
    r, sv = make(tmp_path)
    sv.LISTING_FALLEN = False
    fr(r, [z(1, 101.8, floor=True)] + GROUP3, 30.0, **hold)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "many" and sv._fight_spent() and (a.type, a.args) == ("stomp", {"targetId": 1})
    assert "floor_finish" not in w


def test_the_non_stance_fight_walks_to_a_zombie_beyond_fight_reach(tmp_path):
    """The spec's 1 (b) (ruling P27-9; E20's a190 ran 1.762922801715824 tiles into 3189, #4571): the approach-and-swing
    Fight's walk to a zombie beyond FIGHT_REACH goes at a walk, logged `leg` "walk"; with the rule off at a run."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r = Rig(d)
        r.frame(zombies=[z(7, 105.6, 200.2)])
        f = fight(r)
        if not on:
            f.rules = f.rules - {"floor_pain"}
        f.step()
        assert r.cmd() == ("walkTo", {"x": 105.5, "y": 200.5, "gait": "walk" if on else "run"})
        assert (f.why.get("leg") == "walk") is on


def test_the_floor_pain_switch():
    assert "FLOOR_PAIN" in S.T11_SWITCHES and T.Threat.FLOOR_PAIN is True and "floor_pain" in F.FIGHT_RULES


# ================================================================ P28-A: the wound dressed
F11_P4 = 82.38700103759766   # F11's part 4, scratched, never bleeding, never dressed (#4581, #4585)
RAGS2 = ((11, "Base.RippedSheets"), (12, "Base.RippedSheets"))


def wound4(**k):
    """F11's part 4: scratched (`wound` true), not bleeding, unbandaged, its health F11_P4."""
    return part(4, h=F11_P4, wound=True, **k)


def care_rig(tmp_path, items, parts, near_n=0):
    """A Care on a fresh rig holding `items` [(id, fullType)], the frame's parts `parts`, `near_n` set."""
    r = Rig(tmp_path)
    for iid, ft in items:
        hold(r, iid, ft)
    care_frame(r, parts)
    c = C.Care(r.world, r.acts, r.clock)
    c.near_n = near_n
    return r, c


def test_f11_s_scratched_part_4_is_dressed_with_two_clean_rags_held(tmp_path):
    """F11's part 4 (`wound` true, never bleeding: its health fell to 0 undressed, #4581), two clean rags held, no
    zombie within DANGER_R: `Bandage(rag, part=4)`, logged {reason "wound", part 4, item, kind "rag", h}."""
    r, c = care_rig(tmp_path, RAGS2, [wound4()])
    cmd = c.choose()
    assert (cmd.TYPE, cmd.args()) == ("bandage", {"itemId": 11, "part": 4})
    assert c.why == {"reason": "wound", "part": 4, "item": 11, "kind": "rag", "h": F11_P4}


def test_one_clean_rag_is_kept_for_a_bleed_and_logged_wound_held(tmp_path):
    """One clean rag held (WOUND_RESERVE): nothing sent, logged `wound_held` {part 4, clean 1}."""
    r, c = care_rig(tmp_path, RAGS2[:1], [wound4()])
    assert c.choose() is None and c.why["wound_held"] == {"part": 4, "clean": 1}


def test_one_clean_rag_and_no_garment_wants_a_bandage(tmp_path):
    """One clean rag, no garment to rip: the want `bandage` (`wants_dressing`); a cotton garment held to rip: no want
    (the stock's rip comes first)."""
    r, c = care_rig(tmp_path, RAGS2[:1], [wound4()])
    assert c.wants_dressing() is True
    (tmp_path / "shirt").mkdir()
    r2 = Rig(tmp_path / "shirt")
    hello152(r2)
    r2.frame()
    hold(r2, 11, "Base.RippedSheets")
    garment(r2, 22, ft="Base.Tshirt_WhiteTINT", rip="cotton")
    care_frame(r2, [wound4()])
    assert C.Care(r2.world, r2.acts, r2.clock).wants_dressing() is False


def test_a_zombie_within_danger_r_holds_the_dressing(tmp_path):
    """A zombie within DANGER_R (Survive's `near_n` 1, one 5 tiles off): nothing sent."""
    r, c = care_rig(tmp_path, RAGS2, [wound4()], near_n=1)
    assert c.choose() is None and c.why.get("reason") != "wound"


def test_a_bleeding_part_is_bandaged_first(tmp_path):
    """Part 1 bleeding beside part 4: the bleeding step's bandage of part 1 goes first."""
    r, c = care_rig(tmp_path, RAGS2, [wound4(), part(1, bleeding=True, bleedingTime=5.0, wound=True)])
    cmd = c.choose()
    assert cmd.args()["part"] == 1 and c.why["reason"] == "bleeding"


def test_a_bleeding_part_with_only_a_dirty_rag_held_wants_no_bandage(tmp_path):
    """A part both bleeding and scratched (bleedingTime 5.0, under DIRTY_RAG_MIN) with a dirty rag held and no garment:
    no want (the bleed's own rule: the dirty rag is washed first); the wound step reads only a part not bleeding, so it
    adds none."""
    r, c = care_rig(tmp_path, ((13, "Base.RippedSheetsDirty"),),
                    [part(1, bleeding=True, bleedingTime=5.0, wound=True)])
    assert c.wants_dressing() is False


def test_an_older_log_s_part_with_no_wound_field_is_not_dressed(tmp_path):
    """A part whose record carries no `wound` (decoded None, a log before PZA/1.7.2): nothing sent, nothing held."""
    r, c = care_rig(tmp_path, RAGS2, [part(4, h=F11_P4)])
    assert c.choose() is None and "wound_held" not in c.why


def test_a_clean_bandage_goes_before_a_rag(tmp_path):
    """A clean bandage and a clean rag held: the bandage, kind "bandage"."""
    r, c = care_rig(tmp_path, ((10, "Base.Bandage"), (12, "Base.RippedSheets")), [wound4()])
    cmd = c.choose()
    assert cmd.args()["itemId"] == 10 and c.why["kind"] == "bandage"


def test_the_lowest_health_part_is_dressed_first_then_the_least_index(tmp_path):
    """Parts 6 and 8 scratched beside part 4 (F11's three, #4581): the lowest `h` first, ties to the least index."""
    r, c = care_rig(tmp_path, RAGS2, [wound4(), part(8, h=51.0, wound=True), part(6, h=51.0, wound=True)])
    assert c.choose().args()["part"] == 6


def test_survive_dresses_the_wound_on_a_quiet_care_tick_and_not_with_wound_dress_off(tmp_path):
    """The care branch of a Survive with no zombie listed: part 4 dressed (the care line's `reason` "wound"); a part so
    dressed is left out until a newer frame (`fresh`, as a bleed's); with `WOUND_DRESS` off nothing is sent."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.WOUND_DRESS = on
        for iid, ft in RAGS2:
            hold(r, iid, ft)
        care_frame(r, [wound4()])
        a = tick(r, sv)
        if on:
            assert (a.type, a.args["part"]) == ("bandage", 4) and care_why(d)["reason"] == "wound"
            r.answer()
            sv.care.observe()
            assert 4 in sv.care.fresh and sv.care.choose() is None
        else:
            assert a is None or a.type != "bandage"
            assert care_why(d).get("reason") != "wound"


def test_the_wound_dress_switch_and_reserve():
    assert "WOUND_DRESS" in S.T11_SWITCHES and S.Survive.WOUND_DRESS is True and P.WOUND_RESERVE == 1
