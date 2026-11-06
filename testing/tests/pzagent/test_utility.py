"""The situation utility (Plan 31 Task 11 U, `agent.base.planner.utility`): its terms, its scores, its commitment, its
vetoes and its executors, each rule pinned by a case that fails without it. Pure cases build a `features.Situation`
directly; the end-to-end cases run `Survive(control="utility")` on the fake mod (`test_policies.Rig`)."""
import dataclasses
import math

import pytest

from agent.base.planner.policies import SEEK_SKIP_S, UNREACHABLE_S
from agent.base.planner.survive import Survive
from agent.base.planner.utility import acts as A
from agent.base.planner.utility import core
from agent.base.planner.utility import execute as X
from agent.base.planner.utility import features as F
from agent.base.planner.utility import models as M
from agent.base.planner.utility import select as S
from agent.base.planner.utility import weights as W

from .fakemod import MELEE_CAPS
from .test_policies import Rig, square
from .test_survive import decisions
from .test_survive_g import hold, part


# ================================================================ the synthetic situation
def zed(zid, d, standing=True, aware=True, attacking=False, health=None, closing=0.0, deg=0.0):
    x, y = 100.0 + d * math.cos(math.radians(deg)), 200.0 + d * math.sin(math.radians(deg))
    return F.Zed(zid, x, y, d, standing, aware, aware, attacking, health, closing)


def sit(zeds=(), armed=True, pain=0.0, endurance=1.0, fatigue=0.0, bleeding=(), moving=False, hit_onset=False,
        new_bleeding=()):
    return F.Situation(now=0.0, x=100.0, y=200.0, z=0, armed=armed, reach=1.2, health=100.0, arm_pain=pain,
                       endurance=endurance, fatigue=fatigue, moving=moving, aiming=False, hit_reaction="",
                       attackers=0, zeds=tuple(sorted(zeds, key=lambda q: q.d)), bleeding=tuple(bleeding),
                       on_room=False, building=None, hit_onset=hit_onset, new_bleeding=tuple(new_bleeding))


def fight(z):
    return A.Candidate("fight", "fight:%s" % z.id, target=z.id, zed=z)


def dress(i=1, item=("bandage", 9, "bandage"), ride=False, bt=5.0):
    return A.Candidate("dress", "dress:%d" % i, target=i, part=F.Part(i, bt, 50.0), item=item, ride=ride)


def door(d=6.0):
    return A.Filter("door", (110, 200, 0), (100.0 + d, 200.5), 7, d)


def retreat(f=None):
    f = f or door()
    return A.Candidate("retreat", f.key, target=[f.square[0], f.square[1]], filter=f)


CTX = A.Context()
TRAVEL = A.Candidate("travel", "travel")
SNEAK = A.Candidate("sneak", "sneak")


def total(c, s, ctx=CTX, weights=None):
    return S.weighted(S.terms(c, s, ctx), weights)[0]


# ================================================================ the models' structure
def test_the_pain_divisor_is_one_to_ten_and_the_pain_over_ten_above():
    assert M.pain_divisor(0.0) == M.pain_divisor(10.0) == 1.0
    assert M.pain_divisor(40.0) == 4.0 and M.pain_divisor(1000.0) == M.PAIN_CAP


def test_the_moodle_levels_and_their_multipliers():
    assert [M.endurance_level(e) for e in (1.0, 0.75, 0.5, 0.25, 0.10, 0.0)] == [0, 1, 2, 3, 4, 4]
    assert [M.tired_level(f) for f in (0.6, 0.61, 0.71, 0.81, 0.91)] == [0, 1, 2, 3, 4]
    assert M.moodle_mult(0.6, 0.65) == 0.5 * 0.5


def test_the_hazard_falls_with_the_distance_and_is_zero_unread():
    m = M.FITTED
    assert m.hazard(0.5) > m.hazard(1.0) > m.hazard(2.0) > 0.0
    assert m.hazard(None) == 0.0


def test_a_press_s_chance_falls_with_the_arms_pain_but_the_finish_s_does_not():
    m = M.FITTED
    assert m.p_press(False, 40.0, 1.0, 0.0) == pytest.approx(m.p_press(False, 0.0, 1.0, 0.0) / 4.0)
    assert m.p_press(True, 40.0, 1.0, 0.0) == m.p_press(True, 0.0, 1.0, 0.0)
    assert m.p_press(False, 0.0, 0.6, 0.0) == pytest.approx(m.p_press(False, 0.0, 1.0, 0.0) * 0.5)


# ================================================================ the terms, each one's sign and effect
def test_the_kill_term_is_the_fight_s_kill_chance_and_rises_with_it():
    near = sit([zed(1, 1.0)])
    t = S.terms(fight(near.zeds[0]), near, CTX)
    assert 0.0 < t["kill"] <= 1.0
    weak = sit([zed(1, 1.0)], endurance=0.3)   # the endurance moodle at 2: the spent meet, its knock route
    assert S.terms(fight(weak.zeds[0]), weak, CTX)["kill"] < t["kill"]


def test_the_hit_term_is_negative_and_another_aware_zombie_near_makes_it_more_so():
    one = sit([zed(1, 1.0)])
    two = sit([zed(1, 1.0), zed(2, 0.8, deg=90.0)])
    a = S.terms(fight(one.zeds[0]), one, CTX)["hit"]
    b = S.terms(fight(two.zed(1)), two, CTX)["hit"]
    assert a < 0.0 and b < a


def test_the_chase_term_is_a_standing_aware_zombie_s_while_armed_only():
    s = sit([zed(1, 3.0), zed(2, 3.0, aware=False), zed(3, 2.0, standing=False)])
    assert S.terms(fight(s.zed(1)), s, CTX)["chase"] == 1.0
    assert S.terms(fight(s.zed(2)), s, CTX)["chase"] == 0.0
    assert S.terms(fight(s.zed(3)), s, CTX)["chase"] == 0.0
    unarmed = sit([zed(1, 3.0)], armed=False)
    assert S.terms(fight(unarmed.zed(1)), unarmed, CTX)["chase"] == 0.0


def test_the_bleed_term_credits_the_dress_and_charges_every_other_act_by_its_span():
    s = sit([], bleeding=[F.Part(1, 5.0, 50.0), F.Part(2, 3.0, 60.0)])
    assert S.terms(dress(), s, CTX)["bleed"] == pytest.approx(S.BLEED_HORIZON_M - S.DRESS_HELD_S / 60.0)
    assert S.terms(TRAVEL, s, CTX)["bleed"] == pytest.approx(-2 * S.ROUTE_S / 60.0)
    assert S.terms(TRAVEL, sit([]), CTX)["bleed"] == 0.0


def test_the_goal_term_is_the_goal_s_the_needs_and_the_rest_s():
    s = sit([], endurance=0.4)
    assert S.terms(TRAVEL, s, CTX)["goal"] == S.GOAL_VALUE
    assert S.terms(A.Candidate("needs", "needs:need"), s, CTX)["goal"] == S.NEED_VALUE
    assert S.terms(A.Candidate("rest", "rest"), s, CTX)["goal"] == S.REST_VALUE * 2


def test_the_regress_term_charges_a_retreat_its_tiles_off_the_way():
    s = sit([zed(1, 3.0)])
    assert S.terms(retreat(door(6.0)), s, CTX)["regress"] == pytest.approx(-0.6)
    assert S.terms(TRAVEL, s, CTX)["regress"] == 0.0


def test_the_drag_down_is_one_event_when_a_third_aware_zombie_comes_within_reach_inside_the_span():
    """Fix 1 (review-t11-utility M2): #4290's event, three attacking together, priced once, never per zombie."""
    two = [zed(1, 1.0), zed(2, 3.5, closing=1.0, deg=90.0)]
    three = two + [zed(3, 5.5, closing=1.0, deg=180.0)]   # within KEEP_R after 3.0 s
    four = three + [zed(4, 6.5, closing=1.0, deg=270.0)]
    assert S.drag(two, 10.0) == 0.0
    assert S.drag(three, 10.0) == S.drag(four, 10.0) == S.DRAG_HITS
    assert S.drag(three, 2.5) == 0.0   # the third comes within reach after the span
    assert S.drag(three, 10.0, filtered=True) == 0.0
    assert S.drag(three, 10.0, drag_hits=6.0) == 6.0


def test_no_drag_down_on_a_fight_whose_target_is_already_in_reach():
    s = sit([zed(1, 2.0), zed(2, 3.5, closing=1.0, deg=90.0), zed(3, 4.0, closing=1.0, deg=180.0)])
    zero = S.terms(fight(s.zed(1)), s, CTX, drag_hits=0.0)["hit"]
    assert S.terms(fight(s.zed(1)), s, CTX, drag_hits=6.0)["hit"] == zero
    far = S.terms(fight(s.zed(3)), s, CTX, drag_hits=0.0)["hit"]
    assert S.terms(fight(s.zed(3)), s, CTX, drag_hits=6.0)["hit"] == pytest.approx(far - 6.0)


def test_a_walk_is_priced_with_an_aware_chaser_closing_on_it():
    """Fix 1 (M1): the travel's hit term reads an aware chaser at its closing speed, never holding its distance."""
    s = sit([zed(1, 3.0, closing=1.5)])
    held_off = S.exposure(list(s.zeds), S.ROUTE_S, M.FITTED, filtered=True)
    assert -S.terms(TRAVEL, s, A.Context(goal="travel"))["hit"] > held_off


def test_an_unaware_zombie_counts_its_share_and_a_fallen_one_is_read_no_nearer_than_the_press():
    m = M.FITTED
    assert S.exposure([zed(1, 1.0, aware=False)], 1.0, m) == pytest.approx(S.UNAWARE_FACTOR * m.hazard(1.0))
    assert S.exposure([zed(1, 0.1, standing=False)], 1.0, m) == pytest.approx(
        S.FALLEN_FACTOR * m.hazard(S.MELEE_D))


def test_the_sneak_scores_above_the_travel_past_unaware_zombies():
    s = sit([zed(1, 5.0, aware=False)])
    assert total(SNEAK, s) > total(TRAVEL, s) + 0.1


def test_a_retreat_saves_hits_only_from_a_group_and_scores_under_the_floor_from_one():
    one = sit([zed(1, 3.0, closing=1.0)])
    group = sit([zed(i, 3.0 + 0.2 * i, closing=1.0, deg=60.0 * i) for i in range(1, 5)])
    assert total(retreat(), one) <= S.RETREAT_FLOOR
    assert S.terms(retreat(), group, CTX)["hit"] > 0.0 and total(retreat(), group) > S.RETREAT_FLOOR


# ================================================================ the doctrine at the fitted weights
@pytest.mark.parametrize("d", [0.8, 1.5, 3.0, 5.5])
def test_a_lone_chaser_scores_the_fight_over_every_other_act(d):
    s = sit([zed(1, d, closing=1.0)], pain=0.0)
    c = fight(s.zeds[0])
    others = [TRAVEL, retreat(), A.Candidate("loot", "loot")]
    assert all(total(c, s) > total(o, s) for o in others)


def test_a_lone_chaser_scores_the_fight_spent_too():
    s = sit([zed(1, 1.5, closing=1.0)], pain=60.0)
    assert total(fight(s.zeds[0]), s) > max(total(TRAVEL, s), total(retreat(), s))


def test_a_bleeding_part_with_nothing_near_scores_the_dress_over_the_goal_and_the_needs():
    s = sit([], bleeding=[F.Part(1, 5.0, 50.0)])
    for o in (TRAVEL, A.Candidate("needs", "needs:need"), A.Candidate("rest", "rest")):
        assert total(dress(), s) > total(o, s)
    torn = dress(item=("unwear", 20, "base:tshirt", 3.0))
    assert total(torn, s) > total(TRAVEL, s)


def test_the_flipped_chase_sign_loses_the_lone_chaser_s_fight(monkeypatch):
    s = sit([zed(1, 5.5, closing=1.0)])
    monkeypatch.setitem(S.TERM_SIGN, "chase", -1.0)
    assert total(fight(s.zeds[0]), s) < total(TRAVEL, s) + 3.0


# ================================================================ the commitment
def scores(**totals):
    return {k.replace("_", ":"): (v, {}) for k, v in totals.items()}


TRAVEL_C, FIGHT_C = A.Candidate("travel", "travel"), A.Candidate("fight", "fight:1", target=1)


def held(sel, key_kind, now=0.0):
    sel.key, sel.kind, sel.since, sel.last = key_kind[0], key_kind[1], now, now


def test_nothing_held_takes_the_best():
    sel = S.Selector()
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=2.0), 0.0)
    assert c is FIGHT_C and info["select"] == "new" and info["runner_up"] == "travel"
    assert info["margin"] == pytest.approx(1.5)


def test_a_rival_under_the_margin_keeps_the_held_act_and_one_over_it_takes_it():
    sel = S.Selector()
    held(sel, ("travel", "travel"))
    small = S.delta(0.5) - 0.01
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=0.5 + small), 10.0)
    assert c is TRAVEL_C and info["held_by"] == "margin"
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=0.5 + S.delta(0.5) + 0.01), 11.0)
    assert c is FIGHT_C and info["select"] == "beat"


def test_the_margin_has_its_floor_at_a_held_act_scoring_zero():
    sel = S.Selector()
    held(sel, ("travel", "travel"))
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.0, fight_1=0.25), 10.0)
    assert S.DELTA0 == 0.3 and c is TRAVEL_C and info["held_by"] == "margin"


def test_the_margin_at_zero_switches_on_any_better_rival(monkeypatch):
    monkeypatch.setattr(S, "DELTA0", 0.0)
    monkeypatch.setattr(S, "DELTA_FRAC", 0.0)
    sel = S.Selector()
    held(sel, ("travel", "travel"))
    c, _ = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=0.51), 10.0)
    assert c is FIGHT_C


def test_inside_the_minimum_span_a_better_rival_waits_and_after_it_takes_the_act():
    sel = S.Selector()
    held(sel, ("travel", "travel"))
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=5.0), S.SPAN_S["travel"] - 0.5)
    assert c is TRAVEL_C and info["held_by"] == "span"
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=5.0), S.SPAN_S["travel"] + 0.5)
    assert c is FIGHT_C


def test_between_selections_the_held_act_is_kept_whatever_beats_it():
    sel = S.Selector()
    held(sel, ("travel", "travel"), now=-10.0)
    sel.last = 0.0
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=9.0), S.SELECT_S - 0.1)
    assert c is TRAVEL_C and info["held_by"] == "cadence"


@pytest.mark.parametrize("why", S.INTERRUPTS)
def test_each_interrupt_rescores_at_once_and_lifts_the_span(why):
    sel = S.Selector()
    held(sel, ("travel", "travel"))
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=5.0), 0.2, interrupts=[why])
    assert c is FIGHT_C and info["interrupts"] == [why]


def test_an_interrupt_never_lifts_a_retreat_s_span_to_its_filter():
    sel = S.Selector()
    r = retreat()
    held(sel, (r.key, "retreat"))
    c, info = sel.decide([r, FIGHT_C], {r.key: (0.5, {}), "fight:1": (9.0, {})}, 30.0, interrupts=["hit"])
    assert c is r and info["held_by"] == "span"


def test_the_held_act_s_end_takes_the_best_whatever_its_span():
    sel = S.Selector()
    held(sel, ("fight:1", "fight"))
    c, info = sel.decide([TRAVEL_C, FIGHT_C], scores(travel=0.5, fight_1=0.2), 0.5, ended=True)
    assert c is TRAVEL_C and info["select"] == "end"


def test_a_vetoed_candidate_is_never_chosen():
    sel = S.Selector()
    vetoed = dataclasses.replace(FIGHT_C, veto="unreachable")
    c, _ = sel.decide([TRAVEL_C, vetoed], scores(travel=0.5, fight_1=9.0), 0.0)
    assert c is TRAVEL_C


def test_a_retreat_at_or_under_the_floor_is_never_chosen():
    sel = S.Selector()
    r = retreat()
    c, info = sel.decide([r], {r.key: (S.RETREAT_FLOOR, {})}, 0.0)
    assert c is None and info["select"] == "none"


def test_a_held_retreat_runs_to_its_filter_though_its_score_falls_under_the_floor():
    sel = S.Selector()
    r = retreat()
    c, _ = sel.decide([r, TRAVEL_C], {r.key: (5.0, {}), "travel": (0.5, {})}, 0.0)
    assert c is r
    c, info = sel.decide([r, TRAVEL_C], {r.key: (-0.3, {}), "travel": (0.5, {})}, 5.0)
    assert c is r and info["held_by"] == "span"


def test_a_fallback_takes_only_an_act_above_its_floor():
    sel = S.Selector()
    rest = A.Candidate("rest", "rest")
    c, _ = sel.decide([rest], {"rest": (0.0, {})}, 0.0, ended=True, floor=S.FALLBACK_FLOOR)
    assert c is None


# ================================================================ the generators and the vetoes
class _World:
    """The few World reads the generators make, over an empty map."""

    def __init__(self, inventory=None, caps=("bandage", "rip", "unwear")):
        self.map, self.inventory, self.caps = {}, inventory or {}, caps
        self.zombies = {}

    def marked_doors(self, side=None):
        return frozenset()

    def building_boxes(self):
        return {}

    def can(self, t):
        return t in self.caps

    def marked(self, reason):
        return set()

    def world_minutes(self):
        return 0.0

    def item_fields(self):
        return True

    def line_clear(self, *a, **k):
        return True

    def edge_steps(self, a, b):
        return []


BANDAGE = {9: {"fullType": "Base.Bandage", "use": "bandage"}}


def test_a_fight_at_a_zombie_the_planner_marks_unreachable_is_vetoed():
    s = sit([zed(1, 2.0)])
    cands = A.generate(s, A.Context(unreachable=frozenset({1})), _World())
    assert next(c for c in cands if c.kind == "fight").veto == "unreachable"
    assert next(c for c in A.generate(s, CTX, _World()) if c.kind == "fight").veto is None


def test_the_three_nearest_standing_and_every_fallen_one_within_finish_r_are_fought():
    zs = [zed(i, 1.0 + i, deg=40.0 * i) for i in range(1, 6)] + [zed(9, 4.0, standing=False, deg=200.0)]
    keys = {c.key for c in A.generate(sit(zs), CTX, _World()) if c.kind == "fight"}
    assert keys == {"fight:1", "fight:2", "fight:3", "fight:9"}


def test_the_held_fight_s_target_keeps_its_candidate_past_engage_r():
    s = sit([zed(1, 9.5)])
    assert not [c for c in A.generate(s, CTX, _World()) if c.kind == "fight"]
    assert [c for c in A.generate(s, A.Context(held_target=1), _World()) if c.kind == "fight"]


def test_a_dress_with_nothing_to_dress_is_vetoed_nothing_and_cooled_after_a_failure():
    s = sit([], bleeding=[F.Part(3, 5.0, 50.0)])
    c = next(c for c in A.generate(s, CTX, _World()) if c.kind == "dress")
    assert c.veto == "nothing"
    c = next(c for c in A.generate(s, A.Context(dress_cooled=True), _World(BANDAGE)) if c.kind == "dress")
    assert c.veto == "cooled"


def test_an_upper_part_rides_a_moving_act_and_a_leg_part_never_does():
    w = _World(BANDAGE)
    moving = A.Context(held_kind="travel")
    up = next(c for c in A.generate(sit([], bleeding=[F.Part(3, 5.0, 50.0)], moving=True), moving, w)
              if c.kind == "dress")
    assert up.ride is True and up.veto is None
    leg = next(c for c in A.generate(sit([], bleeding=[F.Part(12, 5.0, 50.0)], moving=True), moving, w)
               if c.kind == "dress")
    assert leg.ride is False and leg.note == "leg" and leg.veto is None
    still = next(c for c in A.generate(sit([], bleeding=[F.Part(3, 5.0, 50.0)]), moving, w) if c.kind == "dress")
    assert still.ride is False


def test_the_sneak_is_offered_only_with_a_standing_zombie_near_and_none_aware():
    w = _World()
    def kinds(zs):
        return {c.kind for c in A.generate(sit(zs), A.Context(goal="travel"), w)}
    assert "sneak" in kinds([zed(1, 5.0, aware=False)])
    assert "sneak" not in kinds([zed(1, 5.0, aware=False), zed(2, 7.0, deg=90.0)])
    assert "sneak" not in kinds([zed(1, 5.0, aware=False, standing=False)])
    assert "sneak" not in kinds([])


def test_the_needs_are_offered_only_with_no_standing_zombie_within_danger_r():
    w = _World()
    ctx = A.Context(needs="need")
    assert "needs" in {c.kind for c in A.generate(sit([zed(1, 7.0)]), ctx, w)}
    assert "needs" not in {c.kind for c in A.generate(sit([zed(1, 5.0)]), ctx, w)}


def test_the_rest_is_offered_only_spent_with_no_zombie_listed():
    w = _World()
    assert "rest" in {c.kind for c in A.generate(sit([], endurance=0.6), CTX, w)}
    assert "rest" not in {c.kind for c in A.generate(sit([], endurance=0.9), CTX, w)}
    assert "rest" not in {c.kind for c in A.generate(sit([zed(1, 11.0)], endurance=0.6), CTX, w)}


def test_no_retreat_is_generated_while_standing_on_the_filter_it_retreated_to():
    s = sit([zed(1, 3.0)])
    cands = A.generate(s, A.Context(at_filter=door()), _World())
    assert not [c for c in cands if c.kind == "retreat"]


GOAL = A.Context(goal="travel", needs="need")


def group(*ds, closing=1.0):
    return [zed(i, d, closing=closing, deg=50.0 * i) for i, d in enumerate(ds, 1)]


def test_a_group_arriving_takes_away_the_walk_and_the_needs_and_offers_the_stand():
    """Fix 1 (review-t11-utility M1, the refuge ruling): no open-ground leg from an arriving group."""
    kinds = {c.kind for c in A.generate(sit(group(4.0, 7.0, 9.0)), GOAL, _World())}
    assert "stand" in kinds and not kinds & {"travel", "loot", "sneak", "needs"}
    two = {c.kind for c in A.generate(sit(group(4.0, 7.0)), GOAL, _World())}
    assert "travel" in two and "stand" not in two


def test_the_stand_faces_the_nearest_aware_zombie_and_goes_while_one_is_in_reach():
    (st,) = [c for c in A.generate(sit(group(4.0, 7.0, 9.0)), GOAL, _World()) if c.kind == "stand"]
    assert st.key == "stand:1" and st.target == 1
    assert not [c for c in A.generate(sit(group(2.0, 7.0, 9.0)), GOAL, _World()) if c.kind == "stand"]


def test_the_stand_reads_a_wall_at_its_back():
    class Walled(_World):
        def line_clear(self, *a, **k):
            return False
    (open_,) = [c for c in A.generate(sit(group(4.0, 7.0, 9.0)), GOAL, _World()) if c.kind == "stand"]
    (walled,) = [c for c in A.generate(sit(group(4.0, 7.0, 9.0)), GOAL, Walled()) if c.kind == "stand"]
    s = sit(group(4.0, 7.0, 9.0))
    assert not open_.back and walled.back
    assert S.terms(walled, s, GOAL)["hit"] == pytest.approx(S.BACK_FACTOR * S.terms(open_, s, GOAL)["hit"])


def test_the_stand_takes_the_arrivals_one_at_a_time_and_pays_no_drag_down():
    s = sit(group(3.0, 4.0, 5.0))
    st = A.Candidate("stand", "stand:1", target=1, zed=s.zed(1))
    f = fight(s.zed(1))
    assert S.terms(st, s, GOAL, drag_hits=6.0) == S.terms(st, s, GOAL, drag_hits=0.0)
    assert S.terms(st, s, GOAL)["hit"] > S.terms(f, s, GOAL)["hit"]


def test_the_dress_is_vetoed_with_an_aware_zombie_in_reach():
    s = sit([zed(1, 2.0)], bleeding=[F.Part(3, 5.0, 50.0)])
    (d,) = [c for c in A.generate(s, CTX, _World(BANDAGE)) if c.kind == "dress"]
    assert d.veto == "in_reach"
    far = sit([zed(1, 3.0)], bleeding=[F.Part(3, 5.0, 50.0)])
    assert next(c for c in A.generate(far, CTX, _World(BANDAGE)) if c.kind == "dress").veto is None


def test_the_reach_interrupt_chooses_afresh_and_lifts_even_a_retreat_s_span():
    sel = S.Selector()
    r = retreat()
    held(sel, (r.key, "retreat"))
    sc = {r.key: (5.0, {}), "fight:1": (5.5, {})}   # under the margin delta(5.0) = 1.3
    c, info = sel.decide([r, FIGHT_C], sc, 0.5, interrupts=["hit"])
    assert c is r and info["held_by"] == "span"
    c, info = sel.decide([r, FIGHT_C], sc, 0.6, interrupts=["reach"])
    assert c is FIGHT_C and info["select"] == "fresh"


# ================================================================ the Task 2 API switch
def test_the_melee_inputs_fit_today_s_class_with_no_back_leg_and_no_swing_close():
    i = X.melee_inputs("strike", 1.5, True)
    assert (i.mode, i.reach, i.floor_swing) == ("strike", 1.5, True)
    if "back" in {f.name for f in dataclasses.fields(type(i))}:
        assert i.back == (0.0, 0.0) and i.close_r == 0.0


def test_the_melee_inputs_fit_task_2_s_three_field_class():
    @dataclasses.dataclass(frozen=True)
    class Meet:
        mode: str
        reach: float
        floor_swing: bool
    assert X.melee_inputs("shove", 1.4, False, cls=Meet) == Meet("shove", 1.4, False)


class _EndedMelee:
    """A maneuver that ended `end` (`end_why` PZA/1.10's, absent before it) with a kill read or none."""

    def __init__(self, end, why=None, kills=()):
        self.end, self.kills = end, list(kills)
        if why is not None:
            self.end_why = why

    def observe(self):
        pass

    def take_kills(self):
        out, self.kills = self.kills, []
        return out

    def take_span(self):
        return None

    def over(self):
        return self.end

    def log(self):
        return {"maneuver": "melee"}


@pytest.mark.parametrize("end, why, ended, marked", [
    ("dead", None, "dead", None), ("kill", None, "dead", None),
    ("crowd", None, "crowd", None), ("handback", "standing", "crowd", None),
    ("out of reach", None, "out of reach", "seek"), ("lost", "out of reach", "out of reach", "seek"),
    ("lost", "no progress", "no progress", "unreachable"), ("lost", "out of range", None, None),
    ("superseded", None, None, None)])
def test_the_melee_s_ends_under_either_api(tmp_path, end, why, ended, marked):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)])
    sv.tick(r.world, r.acts)
    u = sv.control_state[core.STATE_KEY]
    ex = u.ex
    ex.m = ex.owner.m = _EndedMelee(end, why, kills=[7] if end in ("dead", "kill") else [])
    ex.observe(F.read(r.world, r.clock()))
    assert ex.ended == ended and ex.m is None
    until = u.unreach.get(7)
    if marked is None:
        assert until is None
    else:
        assert until == pytest.approx(r.clock() + (SEEK_SKIP_S if marked == "seek" else UNREACHABLE_S))
    assert (7 in r.world.killed) == (end in ("dead", "kill"))


# ================================================================ end to end on the fake mod
def chaser(zid, dx, dy=0.0, **k):
    return dict({"id": zid, "x": 100.0 + dx, "y": 200.0 + dy, "dist": math.hypot(dx, dy), "hasTarget": True,
                 "crawler": False, "health": 1.5, "onFloor": None, "known": True, "state": "walktoward"}, **k)


def build(tmp_path, caps=MELEE_CAPS):
    r = Rig(tmp_path, caps=caps)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="utility")
    return r, sv


def test_the_control_loads_by_name_and_keeps_its_state_on_control_state(tmp_path):
    r, sv = build(tmp_path)
    r.frame()
    sv.tick(r.world, r.acts)
    assert isinstance(sv.control_state[core.STATE_KEY], core.Utility)


@pytest.mark.parametrize("health", [100.0, 20.0])
def test_a_lone_chaser_within_keep_r_is_met_by_the_melee_whatever_the_health(tmp_path, health):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)], health=health)
    sv.tick(r.world, r.acts)
    typ, args = r.cmd()
    assert typ == "melee" and args["targetId"] == 7 and args["mode"] == "strike"
    (line,) = decisions(tmp_path)
    assert line["branch"] == "threat" and line["inputs"]["intent"] == {"kind": "fight", "target": 7}
    u = line["inputs"]["utility"]
    assert u["act"] == "fight:7" and u["select"] == "new" and "fight:7" in u["scores"]
    assert (line["inputs"]["x"], line["inputs"]["y"]) == (100.0, 200.0)


def test_the_melee_under_today_s_api_sends_no_back_leg_and_no_swing_close(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)])
    sv.tick(r.world, r.acts)
    _, args = r.cmd()
    if "backVx" in args:
        assert (args["backVx"], args["backVy"], args.get("closeR", 0.0)) == (0.0, 0.0, 0.0)


def test_spent_by_the_arms_pain_the_melee_goes_in_shove_mode(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)], wounds={"armPain": 40.0})
    sv.tick(r.world, r.acts)
    assert r.cmd()[0] == "melee" and r.cmd()[1]["mode"] == "shove"


def test_a_chaser_beyond_keep_r_is_met_in_the_stance_standing_facing_it(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 4.0)])
    sv.tick(r.world, r.acts)
    typ, args = r.cmd()
    assert typ == "aim" and (args["vx"], args["vy"], args["targetId"]) == (0.0, 0.0, 7)


def test_an_unaware_zombie_near_is_walked_to_in_the_stance(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 4.0, hasTarget=False, known=False, state="idle")])
    sv.tick(r.world, r.acts)
    typ, args = r.cmd()
    assert typ == "aim" and args["vx"] == pytest.approx(1.0) and args["targetId"] == 7


def test_the_melee_s_kill_is_read_onto_the_threat_why_and_counted(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)])
    sv.tick(r.world, r.acts)
    r.fake.answer({"melee": ["accepted", {"state": "done", "result": {"end": "dead", "kill": True}}]})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=[])
    sv.tick(r.world, r.acts)
    line = decisions(tmp_path)[-1]
    assert line["inputs"]["branches"]["threat"]["kill"] == 7 and 7 in r.world.killed


def test_a_bleeding_part_with_nothing_near_and_a_bandage_held_is_dressed_stop_first(tmp_path):
    r, sv = build(tmp_path)
    hold(r, 9, "Base.Bandage")
    r.frame(wounds={"parts": [part(3, bleeding=True, bleedingTime=5.0)], "bleeding": 1})
    sv.tick(r.world, r.acts)
    assert r.cmd()[0] == "stop"
    line = decisions(tmp_path)[-1]
    assert line["branch"] == "care" and line["inputs"]["intent"]["kind"] == "dress"
    assert line["inputs"]["utility"]["act"] == "dress:3"


def test_a_bleeding_part_with_nothing_to_dress_marks_the_bandage_want(tmp_path):
    r, sv = build(tmp_path)
    r.frame(wounds={"parts": [part(3, bleeding=True, bleedingTime=5.0)], "bleeding": 1})
    sv.tick(r.world, r.acts)
    assert "bandage" in sv.need_marks
    assert decisions(tmp_path)[-1]["inputs"]["utility"]["vetoes"] == {"dress:3": "nothing"}


def house(r):
    """Building 7: rooms x 110..112, y 200..202, one door on the west edge of (110, 201) to the open (109, 201)."""
    sq = []
    for x in range(95, 114):
        for y in range(195, 207):
            room = 110 <= x <= 112 and 200 <= y <= 202
            k = {"room": "r1", "building": 7} if room else {}
            if (x, y) == (110, 201):
                k.update(door={"open": False, "locked": False, "barricaded": False}, edgeW=True)
            sq.append(square(x, y, **k))
    r.scan(sq)


def test_a_group_coming_takes_the_retreat_to_the_door_filter_at_a_run(tmp_path):
    r, sv = build(tmp_path)
    house(r)
    r.frame(zombies=[chaser(1, -3.0), chaser(2, -3.2, 2.0), chaser(3, -3.2, -2.0), chaser(4, -4.0)])
    sv.tick(r.world, r.acts)
    typ, args = r.cmd()
    assert typ == "walkTo" and args["gait"] == "run" and (args["x"], args["y"]) == (111.5, 201.5)
    line = decisions(tmp_path)[-1]
    assert line["branch"] == "threat" and line["inputs"]["branches"]["threat"]["flee"] == "retreat:door"
    assert line["inputs"]["intent"] == {"kind": "retreat:door", "target": [110, 201]}


def test_the_door_filter_is_generated_and_none_while_standing_on_a_filter(tmp_path):
    r = Rig(tmp_path)
    house(r)
    r.frame(zombies=[chaser(1, -3.0)])
    s = F.read(r.world, 0.0)
    (f,) = A.filters(r.world, s)
    assert f.square == (110, 201, 0) and f.target == (111.5, 201.5) and f.building == 7
    assert [c.key for c in A.generate(s, CTX, r.world) if c.kind == "retreat"] == [f.key]
    assert not [c for c in A.generate(s, A.Context(at_filter=f), r.world) if c.kind == "retreat"]


def test_no_filter_with_an_aware_zombie_nearer_its_door_or_one_in_its_building(tmp_path):
    r = Rig(tmp_path)
    house(r)
    r.frame(zombies=[chaser(1, 8.0, 1.0)])   # by the door, nearer it than the player
    assert A.filters(r.world, F.read(r.world, 0.0)) == []
    r.frame(zombies=[chaser(1, 11.5, 1.5, hasTarget=False, known=False)])   # inside building 7
    assert A.filters(r.world, F.read(r.world, 0.0)) == []


def test_a_lone_chaser_by_the_same_door_is_fought_never_retreated_from(tmp_path):
    r, sv = build(tmp_path)
    house(r)
    r.frame(zombies=[chaser(1, -3.0)])
    sv.tick(r.world, r.acts)
    line = decisions(tmp_path)[-1]
    assert line["inputs"]["utility"]["kind"] == "fight"
    assert "flee" not in (line["inputs"]["branches"].get("threat") or {})


def test_the_line_logs_every_candidate_s_terms_the_runner_up_and_the_margin(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)])
    sv.tick(r.world, r.acts)
    u = decisions(tmp_path)[-1]["inputs"]["utility"]
    total_, terms = u["scores"]["fight:7"]
    assert total_ == pytest.approx(sum(terms.values()), abs=1e-5)
    assert set(terms) <= set(S.TERMS) and u["runner_up"] is not None and u["margin"] > 0.0
    assert set(u) >= {"act", "kind", "target", "scores", "vetoes", "runner_up", "margin", "held_by", "select",
                      "interrupts", "end"}


def test_the_weights_are_the_registry_s_and_the_line_s_terms_are_weighted(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(7, 1.6)])
    sv.tick(r.world, r.acts)
    _, terms = decisions(tmp_path)[-1]["inputs"]["utility"]["scores"]["fight:7"]
    assert terms["chase"] == pytest.approx(W.WEIGHTS["C"].value, abs=1e-6)


# ================================================================ the cross-frame readings and the interrupts
def test_the_tracks_read_a_closing_speed_and_the_two_body_onsets(tmp_path):
    r = Rig(tmp_path)
    t = F.Tracks()
    bleeding = {"parts": [part(3, bleeding=True)], "bleeding": 1}
    r.frame(zombies=[chaser(7, 4.0)])
    t.update(r.world, 0.0)
    r.frame(zombies=[chaser(7, 3.0)], hit_reaction="Bite", wounds=bleeding)
    t.update(r.world, 1.0)
    assert t.closing[7] == pytest.approx(1.0) and t.hit_onset is True and t.new_bleeding == (3,)
    r.frame(zombies=[chaser(7, 3.0)], hit_reaction="Bite", wounds=bleeding)
    t.update(r.world, 2.0)
    assert t.hit_onset is False and t.new_bleeding == () and t.closing[7] == pytest.approx(0.5)


def _interrupts(tmp_path, before, after):
    r, sv = build(tmp_path)
    r.frame(**before)
    sv.tick(r.world, r.acts)
    r.advance(0.5)
    r.frame(**after)
    sv.tick(r.world, r.acts)
    return decisions(tmp_path)[-1]["inputs"]["utility"]["interrupts"]


def test_a_hit_reaction_onset_is_an_interrupt(tmp_path):
    z = [chaser(7, 4.0)]
    assert "hit" in _interrupts(tmp_path, {"zombies": z}, {"zombies": z, "hit_reaction": "Bite"})


def test_a_part_newly_bleeding_is_an_interrupt(tmp_path):
    w = {"parts": [part(3, bleeding=True)], "bleeding": 1}
    assert "bleeding" in _interrupts(tmp_path, {}, {"wounds": w})


def test_a_standing_zombie_other_than_the_target_entering_near_r_is_an_interrupt(tmp_path):
    a = [chaser(7, 2.0), chaser(8, 3.0, 2.0)]
    b = [chaser(7, 2.0), chaser(8, 1.0, 0.5)]
    assert "near" in _interrupts(tmp_path, {"zombies": a}, {"zombies": b})
    sub = tmp_path / "target"
    sub.mkdir()
    assert "near" not in _interrupts(sub, {"zombies": [chaser(7, 2.0)]}, {"zombies": [chaser(7, 1.2)]})


def test_an_aware_zombie_entering_reach_is_an_interrupt(tmp_path):
    a = [chaser(7, 1.6), chaser(8, -4.0)]
    b = [chaser(7, 1.6), chaser(8, -2.0)]
    assert "reach" in _interrupts(tmp_path, {"zombies": a}, {"zombies": b})
    sub = tmp_path / "target"
    sub.mkdir()
    assert "reach" not in _interrupts(sub, {"zombies": [chaser(7, 2.0)]}, {"zombies": [chaser(7, 1.8)]})


def test_a_group_arriving_with_no_filter_is_met_by_the_stand_never_a_walk(tmp_path):
    r, sv = build(tmp_path)
    r.frame(zombies=[chaser(1, -4.0), chaser(2, -6.0, 3.0), chaser(3, -7.0, -3.0), chaser(4, -9.0)])
    sv.tick(r.world, r.acts)
    typ, args = r.cmd()
    assert typ == "aim" and (args["vx"], args["vy"], args["targetId"]) == (0.0, 0.0, 1)
    line = decisions(tmp_path)[-1]
    assert line["inputs"]["intent"] == {"kind": "meet:stand", "target": 1} and line["branch"] == "threat"
    assert not {k for k in line["inputs"]["utility"]["scores"]} & {"travel", "loot", "sneak"}


def test_the_goal_is_a_candidate_only_with_a_goal_running_or_pending_and_names_its_square(tmp_path, monkeypatch):
    """Fix 1 (m6): the runner asked to propose when it holds nothing, the goal's args' square its target."""
    r, sv = build(tmp_path)
    r.frame()
    u = core.Utility(sv)
    sv.control_state[core.STATE_KEY] = u
    monkeypatch.setattr(sv, "_goal", lambda: None)
    sv.goals.current, sv.goals.pending = None, False
    assert u._goal_read(False) == (None, None) and u.take_goal_answer() == (None, {})

    class Running:
        pass
    monkeypatch.setattr(sv.goals, "line", lambda: {"type": "ExploreToward", "args": {"x": 110, "y": 205}})
    sv.goals.current = Running()
    assert u._goal_read(False) == ("travel", (110, 205))
    sv.goals.current = None
    assert u._goal_read(True) == (None, None) and u.take_goal_answer() is None   # a group arriving: not asked


def test_a_goal_answer_is_an_interrupt_once(tmp_path, monkeypatch):
    r, sv = build(tmp_path)
    answer = {"line": {"type": "ExploreToward", "args": {"x": 1, "y": 2}}}
    monkeypatch.setattr(sv.goals, "line", lambda: answer["line"])
    r.frame()
    sv.tick(r.world, r.acts)
    answer["line"] = {"type": "LootBuilding", "args": {"building": 3}}
    for _ in range(2):
        r.advance(0.5)
        r.frame()
        sv.tick(r.world, r.acts)
    lines = decisions(tmp_path)
    assert "goal" in lines[1]["inputs"]["utility"]["interrupts"]
    assert "goal" not in lines[2]["inputs"]["utility"]["interrupts"]
