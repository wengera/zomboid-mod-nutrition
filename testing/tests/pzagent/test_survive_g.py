"""Survival 6 (Plan 24 Task 10, ruling P24-G, Angus's direction of 2026-10-29 after F2's shots): the standing fight
(the combat stance with the backpedal, its stand-off fallback), on the fake mod over the PZA/1.5 skills Task 9 landed.
The decision goldens (`test_replay_decisions.py`) stay unmoved: their artifacts' hellos announce no PZA/1.5 skill, and
the planner sends one only to a build whose caps carry it (`World.can`)."""
import math

from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner.care import water_sources

from .test_policies import CAPS_14, all_sends_valid, square, zombie
from .test_survive import last, make, threat_why, tick


def zd(zid, x, y, has_target=True, health=1.0):
    """A zombie record at (x, y) with `hasTarget` and `health` set (the stance's closing read and its progress)."""
    return dict(zombie(zid, x, y), hasTarget=has_target, health=health)


def stance_args(r):
    t, a = r.cmd()
    assert t == "aim", (t, a)
    return a


# ================================================================ the constants
def test_the_stance_constants():
    assert (P.AIM_LEG_S, P.STAND_MAX_S, P.CLOSE_MIN) == (2.0, 20.0, 0.1)
    assert S.BRANCHES[0] == "threat"


# ================================================================ the stance against one
def test_one_zombie_closing_at_four_tiles_is_met_in_the_stance_backpedalling_then_swung_at_within_reach(tmp_path):
    """P24-G 1: one held at 4 tiles, armed, full health: `aim` facing it for AIM_LEG_S with the away vector (west,
    the zombie east of the player) as the backpedal; the leg holds while the zombie closes beyond FIGHT_REACH, and
    gives way to the `attack` from the stance once it is within reach."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert a == {"vx": -1.0, "vy": 0.0, "seconds": 2.0, "targetId": 1, "bearing": -1.0}
    w = threat_why(tmp_path)
    assert w["fight"] is True and w["stance"] is True and w["closing"] is True and w["back"] == [-1.0, 0.0]
    sends = len(r.acts.history)
    r.advance(0.5)
    r.frame(zombies=[zd(1, 103.0, 200.0)])
    assert tick(r, sv) is None and len(r.acts.history) == sends            # the leg holds beyond reach
    assert threat_why(tmp_path)["holding"] == r.acts.history[-1].aid
    r.advance(0.5)
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1})                           # the swing from the stance
    all_sends_valid(r)


def test_a_stance_leg_ended_re_aims_and_reads_closing_off_the_zombies_own_move(tmp_path):
    """Each AIM_LEG_S the stance re-aims; the backpedal goes while the target moved CLOSE_MIN or more toward the player
    since the last leg's send (its own move, never the distance the backpedal kept), else it stands (0, 0)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    r.answer()
    r.advance(2.0)
    r.frame(x=99.0, zombies=[zd(1, 103.0, 200.0)])                          # 4.0 tiles still: it closed by 1.0
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["closing"] is True
    r.answer()
    r.advance(2.0)
    r.frame(x=99.0, zombies=[zd(1, 103.05, 200.0)])                         # it stood: no backpedal
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"]) == (0.0, 0.0) and threat_why(tmp_path)["closing"] is False
    assert threat_why(tmp_path)["back"] is None


def test_a_first_leg_on_a_zombie_with_no_target_stands(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"], a["targetId"]) == (0.0, 0.0, 1)


def test_the_backpedal_never_steps_into_a_wall_or_over_a_fence(tmp_path):
    """The backpedal reads the steer probe (`policies.clear_heading`: `line_clear` over STEER_PROBE, which reads a
    hoppable fence blocked, P24-G 4: the stance never vaults): a fence on the player's west edge turns the heading by
    STEER_TURNS to the first clear one (+30 degrees)."""
    r, sv = make(tmp_path)
    sqs = [square(x, y) for x in range(95, 106) for y in range(195, 206)]
    sqs = [dict(s, blockW=True, hopW=True) if (s["x"], s["y"]) == (100, 200) else s for s in sqs]
    r.scan(sqs)
    r.frame(x=100.5, y=200.5, zombies=[zd(1, 104.5, 200.5)])
    tick(r, sv)
    a = stance_args(r)
    turns = [P._rotate((-1.0, 0.0), t) for t in P.STEER_TURNS]
    first = next(v for v in turns if P.clear_heading(r.world, v))
    assert not P.clear_heading(r.world, (-1.0, 0.0)) and (a["vx"], a["vy"]) == first and first != (-1.0, 0.0)


def test_two_zombies_at_full_health_are_met_in_the_stance_backing_from_both(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0)])
    tick(r, sv)
    a = stance_args(r)
    assert a["targetId"] in (1, 2) and abs(a["vx"] + math.sqrt(0.5)) < 1e-9 and abs(a["vy"] + math.sqrt(0.5)) < 1e-9


def test_two_zombies_under_flee_health_pair_are_fled_not_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0)], health=55.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "pair"


def test_three_zombies_are_fled_never_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0), zd(3, 103.0, 203.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"


def test_one_zombie_under_flee_health_is_fled_never_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)], health=35.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "health"


def test_unarmed_the_stance_is_never_taken(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unarmed"


def test_a_running_stance_gives_way_to_the_flee_when_a_third_comes(tmp_path):
    """The flee from three supersedes the stance leg (the Lua releases the stance on supersede)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0), zd(3, 103.0, 203.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.mode == "flee"


def test_a_pza_1_4_build_is_never_sent_the_stance(tmp_path):
    """`World.can`: a hello whose caps lack `aim` (every decision golden's artifact) keeps the approach walk."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"})
    assert "stance" not in threat_why(tmp_path) and not r.world.can("aim") and r.world.can("attack")


# ================================================================ the stand-off fallback
def stand_legs(r, sv, n, x=104.0, health=1.0, dt=2.0):
    """`n` stance legs answered done, each AIM_LEG_S of clock, the zombie standing at `x` with `health`."""
    for _ in range(n):
        r.answer()
        r.advance(dt)
        r.frame(zombies=[zd(1, x, 200.0, has_target=False, health=health)])
        tick(r, sv)


def test_a_stand_with_no_progress_in_stand_max_s_falls_back_to_the_approach_and_swing(tmp_path):
    """P24-G 1: a fence stand-off (the zombie standing 4 tiles off, never closing) never becomes a stance stand-off:
    after STAND_MAX_S without its health falling the Fight walks to it as before (`standoff`), and the stall clock
    (FIGHT_MAX_S, the stalled flee) starts only then."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    stand_legs(r, sv, 9)                                                    # 18 s
    assert r.cmd()[0] == "aim" and last(tmp_path)["inputs"]["fight_s"] == 2.0   # one leg's clock, never accrued
    stand_legs(r, sv, 1)                                                    # 20 s: the fallback
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"}) and sv.fight.standoff
    assert "stance" not in threat_why(tmp_path)
    r.answer()
    r.advance(1.0)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    assert last(tmp_path)["inputs"]["fight_s"] == 1.0                       # the approach's stall clock runs


def test_a_falling_target_health_restarts_the_stand_clock(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    stand_legs(r, sv, 8)                                                    # 16 s
    stand_legs(r, sv, 1, health=0.6)                                        # a hit landed: the clock restarts
    assert threat_why(tmp_path)["stand_s"] == 0.0
    stand_legs(r, sv, 9, health=0.6)                                        # 18 s more: still standing
    assert r.cmd()[0] == "aim" and not sv.fight.standoff
    stand_legs(r, sv, 1, health=0.6)
    assert r.cmd()[0] == "walkTo" and sv.fight.standoff


def test_a_kill_restarts_the_stand_on_the_next_target(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False), zd(2, 100.0, 204.5, has_target=False)])
    tick(r, sv)
    assert stance_args(r)["targetId"] == 1
    stand_legs(r, sv, 0)
    for _ in range(9):
        r.answer()
        r.advance(2.0)
        r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False), zd(2, 100.0, 204.5, has_target=False)])
        tick(r, sv)
    r.answer()
    r.event("zombie_dead", id=1)
    r.advance(2.0)
    r.frame(zombies=[zd(2, 100.0, 204.5, has_target=False)])
    tick(r, sv)
    assert stance_args(r)["targetId"] == 2 and threat_why(tmp_path)["stand_s"] == 0.0 and not sv.fight.standoff


def test_the_corner_keeps_its_swing_and_never_stands(tmp_path):
    """The corner rules stay: a cornered Fight (`point_blank`) never takes the stance (`Fight.standing`)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    f = P.Fight(r.world, r.acts, r.clock, target=1)
    f.stance, f.point_blank = True, True
    assert not f.standing()
    f.point_blank, f.only = False, {1}
    assert not f.standing()
    f.only = None
    assert f.standing()


def test_two_held_under_flee_health_pair_with_one_within_danger_r_fight_by_the_approach_not_the_stance(tmp_path):
    """The pair rule reads the DANGER_R count (one here, so the hysteresis fights); the stance reads the held count:
    two held at health 50 (under FLEE_HEALTH_PAIR) is no standing fight: the running stance leg gives way to the
    approach walk once the hold radius (DISENGAGE_R while the fight runs) holds the second."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 92.0, 200.0)], health=50.0)
    tick(r, sv)
    assert r.cmd()[0] == "aim"                                              # one held within DANGER_R
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 92.0, 200.0)], health=50.0)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"}) and threat_why(tmp_path)["fight"] is True
    assert last(tmp_path)["inputs"]["held"] == 2


def test_trapped_on_a_room_square_the_fight_keeps_the_approach_never_the_stance(tmp_path):
    """The corner rules stay for a trapped character (`_trapped`: a room square, no way out, nothing to adopt): the
    held zombie inside the closed room is walked to and swung at, never backpedalled from inside the walls."""
    from .test_survive import closed_room
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (100.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[dict(zombie(1, 104.5, 204.5, me=me), health=1.0)])
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and sv._trapped(sv._within(S.DANGER_R), True)


def test_a_standing_fight_reads_no_walk_so_the_look_behind_its_target_does_not_flee(tmp_path):
    """P24-A (b) reads the fight's walk: the stance does not walk beyond reach, so zombie 2 listed behind zombie 1
    (the E5 case of `test_survive`'s P24-A (b) test, there pinned on a PZA/1.4 build) does not turn it to a flee; after
    the stand-off fallback the Fight walks, and the look behind reads again."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "aim" and w["fight"] is True and "behind" not in w
    sv.fight.standoff = True
    r.answer()
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2]


# ================================================================ the care branch (P24-G 2)
from agent.base.planner import care as C   # noqa: E402  (the care tests' module, beside the stance's)


def part(i, **k):
    """A PZA/1.5 part record: index `i`, health 80, no bleeding, unbandaged (bandageLife and bandageDirty None as the
    Lua leaves them on an unbandaged part), `k` laid over."""
    return dict({"i": i, "h": 80.0, "bleeding": False, "bleedingTime": 0.0, "bandaged": False, "bandageLife": None,
                 "bandageDirty": None, "deep": False, "infected": False}, **k)


def hold(r, iid, full_type, use="bandage", weight=0.1):
    r.event("item_added", itemId=iid, fullType=full_type, weight=weight, use=use)


def care_frame(r, parts, **k):
    r.frame(wounds={"parts": parts, "bleeding": sum(1 for p in parts if p.get("bleeding"))}, **k)


def care_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["care"]


def test_the_care_constants_and_the_item_kinds():
    assert (C.CARE_RETRY_MIN, C.DIRTY_RAG_MIN, C.WASH_R) == (2.0, 10.0, 15.0)
    kinds = {t: C.care_kind(t) for t in ("Base.Bandage", "Base.AlcoholBandage", "Base.Bandaid", "Base.RippedSheets",
                                         "Base.AlcoholRippedSheets", "Base.DenimStrips", "Base.RippedSheetsDirty",
                                         "Base.BandageDirty", "Base.DenimStripsDirty", "Base.RagFilter",
                                         "Base.BandageBox", "Base.Tshirt_WhiteTINT")}
    assert kinds == {"Base.Bandage": "bandage", "Base.AlcoholBandage": "bandage", "Base.Bandaid": "bandage",
                     "Base.RippedSheets": "rag", "Base.AlcoholRippedSheets": "rag", "Base.DenimStrips": "rag",
                     "Base.RippedSheetsDirty": "dirty", "Base.BandageDirty": "dirty", "Base.DenimStripsDirty": "dirty",
                     "Base.RagFilter": None, "Base.BandageBox": None, "Base.Tshirt_WhiteTINT": None}
    assert [C.rippable(t) for t in ("Base.Tshirt_WhiteLongSleeveTINT", "Base.Shirt_FormalWhite", "Base.Socks_Long",
                                    "Base.Shirt_Denim", "Base.Shorts_LongDenim", "Base.Hat_BucketHat",
                                    "Base.Jacket_Leather")] == [True, True, True, False, False, False, False]


def test_the_care_branch_runs_between_the_threat_and_the_need():
    assert S.BRANCHES == ("threat", "care", "need", "load", "night", "goal")


def bleeding_rig(tmp_path, items, bleeding_time=5.0, deep=False, caps=None):
    r, sv = make(tmp_path, caps=caps)
    r.frame()
    for iid, ft in items:
        hold(r, iid, ft)
    care_frame(r, [part(5, bleeding=True, bleedingTime=bleeding_time, deep=deep)], thirst=0.5)
    return r, sv


def test_a_bleeding_part_takes_a_bandage_before_a_clean_rag_before_a_dirty_one(tmp_path):
    """P24-G 2: the best held item: a bandage, then a clean rag; the bandage goes on the part by index; the need
    (thirst 0.5) waits behind the care branch."""
    r, sv = bleeding_rig(tmp_path, [(12, "Base.RippedSheetsDirty"), (11, "Base.RippedSheets"), (10, "Base.Bandage")])
    hold(r, 30, "Base.WaterBottle", use="water")                                  # the need would drink it
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path) == {"reason": "bleeding", "part": 5, "item": 10, "kind": "bandage", "bleedingTime": 5.0,
                                  "deep": False}
    (tmp_path / "b").mkdir()
    r2, sv2 = bleeding_rig(tmp_path / "b", [(12, "Base.RippedSheetsDirty"), (11, "Base.RippedSheets")])
    tick(r2, sv2)
    assert r2.cmd() == ("bandage", {"itemId": 11, "part": 5})
    all_sends_valid(r2)


def test_a_dirty_rag_goes_on_only_past_dirty_rag_min_of_bleeding_time(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(12, "Base.RippedSheetsDirty")], bleeding_time=10.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"                                    # 10.0: not past the rule
    (tmp_path / "b").mkdir()
    r2, sv2 = bleeding_rig(tmp_path / "b", [(12, "Base.RippedSheetsDirty")], bleeding_time=10.5)
    tick(r2, sv2)
    assert r2.cmd() == ("bandage", {"itemId": 12, "part": 5}) and care_why(tmp_path / "b")["kind"] == "dirty"


def test_the_deep_wound_is_bandaged_first_then_the_longest_bleeding(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 10, "Base.Bandage")
    hold(r, 11, "Base.Bandage")
    care_frame(r, [part(3, bleeding=True, bleedingTime=20.0), part(7, bleeding=True, bleedingTime=5.0, deep=True),
                   part(9, bleeding=True, bleedingTime=30.0)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 7})
    r.answer()
    r.event("item_removed", itemId=10, fullType="Base.Bandage")
    care_frame(r, [part(3, bleeding=True, bleedingTime=20.0),
                   part(7, bandaged=True, bandageLife=3.0, bandageDirty=False),
                   part(9, bleeding=True, bleedingTime=30.0)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 9})


def test_with_no_rag_an_unworn_cotton_garment_is_ripped_never_one_of_the_first_sight(tmp_path):
    """P24-G 2: no bandage item of any kind held, the bleeding part waits on a rip of a cotton garment; the T-shirt
    the character stood in (the inventory's first sight, between the hello and the first frame) is never asked."""
    r, sv = make(tmp_path)
    hold(r, 20, "Base.Tshirt_WhiteLongSleeveTINT", use="other")                   # the first sight: worn
    r.frame()
    assert r.world.first_sight == {20}
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")                            # a looted shirt
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21}) and care_why(tmp_path) == {"reason": "no_rag", "part": 5, "item": 21}
    all_sends_valid(r)


def test_a_rip_refused_worn_marks_the_item_and_it_is_never_asked_again(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    care_frame(r, [])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21})                                    # no rag held: one rip for rags
    r.answer({"state": "failed", "reason": "worn"})
    for _ in range(3):
        r.advance(1.0)
        care_frame(r, [], game_min=485.0)
        tick(r, sv)
    assert r.world.marked("unrippable") == {21: 485.0} and sum(a.type == "rip" for a in r.acts.history) == 1


def test_a_dirty_rag_is_washed_at_a_known_source_within_wash_r_with_no_zombie_near(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True}),
            square(130, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [])
    tick(r, sv)
    assert r.cmd() == ("wash", {"itemId": 12, "x": 105, "y": 200})
    w = care_why(tmp_path)
    assert w["reason"] == "dirty_rag" and w["item"] == 12 and w["source"] == [105, 200]
    all_sends_valid(r)


def test_no_wash_with_a_zombie_within_disengage_r_or_no_source_within_wash_r(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [], zombies=[zd(1, 108.0, 200.0, has_target=False)])            # 8 tiles: no threat, not quiet
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.scan([square(116, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])   # 16 tiles
    r2.frame()
    hold(r2, 12, "Base.RippedSheetsDirty")
    care_frame(r2, [])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care"


def test_a_spent_bandage_is_replaced_with_a_clean_rag(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 11, "Base.RippedSheets")
    care_frame(r, [part(4, bandaged=True, bandageLife=0.0, bandageDirty=True)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 4}) and care_why(tmp_path)["reason"] == "spent"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame()
    hold(r2, 12, "Base.RippedSheetsDirty")                                         # no clean one: kept on
    care_frame(r2, [part(4, bandaged=True, bandageLife=0.0, bandageDirty=True)])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care"


def test_the_care_branch_yields_to_a_threat_within_danger_r(tmp_path):
    """The threat branch runs first: a zombie within DANGER_R answers it (the stance) and the running bandage is
    superseded by that send."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd()[0] == "bandage"
    bandage = r.acts.history[-1]
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.acts.current is not bandage


def test_a_refused_bandage_item_waits_care_retry_min(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage"), (11, "Base.RippedSheets")])
    tick(r, sv)
    r.answer({"state": "failed", "reason": "not valid"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=480.5)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 5})                      # 10 held out
    r.answer({"state": "failed", "reason": "not valid"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=481.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"                                     # both held out
    r.advance(10.0)
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=482.5)    # 2 minutes after 10's refusal
    for _ in range(10):                                                           # the failed-command cooldown's ticks
        tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})


def test_a_pza_1_4_build_is_sent_no_care(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")], caps=CAPS_14)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"


def test_a_part_record_without_the_care_fields_reads_no_wound(tmp_path):
    """A PZA/1.4 part (`i`, `h` only: the decoded care fields None) is no bleeding part."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 10, "Base.Bandage")
    care_frame(r, [{"i": 5, "h": 60.0}])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"


# ================================================================ the one mark store (ruling P24-I)
def test_the_world_keeps_one_mark_an_item_with_its_reason_and_the_old_views_read_it(tmp_path):
    """P24-I (the Task 4b review's minor 6): `World.marks` {id: (reason, world minute)} replaces the three stores;
    `empty_ids`, `refused` and `no_effect_ids` are its views, the latest mark wins, an item's removal drops its mark,
    and `to_json` keeps its three fields (a World that never marked one serialises as before)."""
    import json
    from agent.base.world import MARK_REASONS, World
    w = World()
    w.apply({"kind": "frame", "gameMin": 480, "worldAge": 8.0, "wallMs": 0})
    for iid, ft in ((1, "Base.WaterBottle"), (2, "Base.Apple"), (3, "Base.Disinfectant"), (4, "Base.Shirt_FormalWhite")):
        w.apply({"kind": "event", "event": "item_added", "itemId": iid, "fullType": ft, "weight": 0.1})
    base = json.loads(w.to_json())
    assert "emptyIds" not in base and "refusedIds" not in base and "noEffectIds" not in base
    w.mark_empty(1)
    w.mark_refused(2)
    w.mark_no_effect(3)
    w.mark(4, "unrippable")
    assert w.marks == {1: ("empty", 480.0), 2: ("refused", 480.0), 3: ("no_effect", 480.0), 4: ("unrippable", 480.0)}
    assert (w.empty_ids, w.refused, w.no_effect_ids) == ({1}, {2: 480.0}, {3})
    d = json.loads(w.to_json())
    assert (d["emptyIds"], d["refusedIds"], d["noEffectIds"]) == ([1], [2], [3]) and "unrippable" not in w.to_json()
    w.mark_no_effect(1)
    assert w.empty_ids == set() and w.no_effect_ids == {1, 3}
    w.apply({"kind": "event", "event": "item_removed", "itemId": 3, "fullType": "Base.Disinfectant"})
    assert 3 not in w.marks and w.no_effect_ids == {1}
    assert MARK_REASONS[:4] == ("empty", "refused", "no_effect", "unrippable")
    try:
        w.mark(2, "lost")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown reason is refused")


def test_a_mark_never_fixes_the_gamemin_fallbacks_origin():
    """A mark other than `refused` reads the minute without `world_minutes`' first-read side effect (a frame with
    no worldAge: the fallback's origin is fixed by the first timer that reads it, never by a mark)."""
    from agent.base.world import World
    w = World()
    w.apply({"kind": "frame", "gameMin": 600, "wallMs": 0})
    w.apply({"kind": "event", "event": "item_added", "itemId": 1, "fullType": "Base.WaterBottle", "weight": 0.1})
    w.mark_empty(1)
    assert w.marks[1] == ("empty", None) and w._gm0 is None


def test_the_first_sight_is_the_inventory_between_a_hello_and_the_first_frame():
    from agent.base.world import World
    w = World()
    w.apply({"kind": "hello", "caps": []})
    w.apply({"kind": "event", "event": "item_added", "itemId": 1, "fullType": "Base.Socks_Long", "weight": 0.1})
    w.apply({"kind": "frame", "gameMin": 480, "wallMs": 0})
    w.apply({"kind": "event", "event": "item_added", "itemId": 2, "fullType": "Base.Socks_Long", "weight": 0.1})
    assert w.first_sight == {1}
    w.apply({"kind": "hello", "caps": []})
    assert w.first_sight == set()


def test_no_garment_is_ripped_while_a_rag_is_held(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    hold(r, 11, "Base.RippedSheets")
    care_frame(r, [])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care" and not any(a.type == "rip" for a in r.acts.history)


# ================================================================ the water chain (P24-G 3)
from agent.base.planner import view as V   # noqa: E402
from agent.base.planner.goals import ExploreToward, GoalRunner   # noqa: E402
from .test_policies import Rig   # noqa: E402


def need_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["need"]


def source(x, y, tainted=False, amount=20.0, infinite=False):
    return square(x, y, water={"amount": amount, "tainted": tainted, "infinite": infinite})


def thirsty(r, **k):
    r.frame(thirst=0.2, **k)


def test_the_water_chain_constants():
    assert (S.FILL_R, S.FILL_RETRY_MIN, S.THIRST_T) == (25.0, 2.0, 0.12)


def test_a_clean_water_item_is_drunk_before_a_tainted_one_and_a_tainted_one_without(tmp_path):
    """Step 1: the need drinks a held `water` item, a clean one first (one the World knows tainted, `tainted_ids`,
    only with no clean one held), whatever their ids."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 1, "Base.WaterBottle", use="water")
    hold(r, 2, "Base.WaterBottle", use="water")
    r.world.mark(1, "tainted")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 2})
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame()
    hold(r2, 1, "Base.WaterBottle", use="water")
    r2.world.mark(1, "tainted")
    thirsty(r2)
    tick(r2, sv2)
    assert r2.cmd() == ("consume", {"itemId": 1})


def test_no_water_held_a_vessel_is_filled_at_the_nearest_clean_source_then_drunk(tmp_path):
    """Step 2: no `water` item, a `container` held: `fill` at the nearest known source (the Lua walks there); its
    done marks the vessel `filled`, which `by_use` reads water, and the next tick drinks it."""
    r, sv = make(tmp_path)
    r.scan([source(110, 200), source(104, 200, amount=0.0), source(120, 200)])     # the dry one is no source
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200}) and last(tmp_path)["branch"] == "need"
    w = need_why(tmp_path)
    assert w["item"] is None and w["mark"] is None and w["fill"]["vessel"] == 5 and w["fill"]["tainted"] is False
    all_sends_valid(r)
    assert tick(r, sv) is None                                                   # its fill is current: held
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    r.advance(S.FILL_SETTLE_S)                  # 9 fix 2: no item_changed came: the settle time reads it filled
    thirsty(r)
    tick(r, sv)
    assert r.world.marks[5][0] == "filled" and r.world.by_use()["water"] == [5]
    assert r.cmd() == ("consume", {"itemId": 5})


def test_a_tainted_source_is_filled_from_only_with_no_clean_one_within_fill_r(tmp_path):
    r, sv = make(tmp_path)
    r.scan([source(105, 200, tainted=True, infinite=True), source(124, 200)])     # clean at 24.5 tiles
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 124, "y": 200})
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.scan([source(105, 200, tainted=True, infinite=True), source(130, 200)])    # clean at 30.5: beyond FILL_R
    r2.frame()
    hold(r2, 5, "Base.PopEmpty", use="container")
    thirsty(r2)
    tick(r2, sv2)
    assert r2.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200}) and need_why(tmp_path / "b")["fill"]["tainted"]
    r2.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "TaintedWater", "tainted": True}})
    r2.advance(S.FILL_SETTLE_S)
    thirsty(r2)
    tick(r2, sv2)
    assert r2.world.marks[5][0] == "tainted" and r2.world.tainted_ids() == {5} and r2.cmd() == ("consume", {"itemId": 5})


def test_a_fill_refused_for_its_water_leaves_the_source_out(tmp_path):
    r, sv = make(tmp_path)
    r.scan([source(105, 200), source(110, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200})
    r.answer({"state": "failed", "reason": "no water"})
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 6, "x": 110, "y": 200})


def test_no_vessel_held_the_container_want_is_marked_for_the_goal_layer(tmp_path):
    """Step 3: no water and no vessel held: the water want and the container want are marked (`need_marks`), the
    view lists both in `needs_wanted`, and a known empty vessel in a container is named in `stock_uses`."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200), square(102, 200, containers=[{"type": "counter", "n": 1, "items": ["Base.PopEmpty"]}])])
    thirsty(r)
    tick(r, sv)
    w = need_why(tmp_path)
    assert w["mark"] == "water" and w["fill"] == {"want": "container"} and set(sv.need_marks) == {"water", "container"}
    v = V.view(r.world, sv)
    assert v["needs_wanted"] == ["water", "container"] and "container" in v["stock_uses"]
    hold(r, 7, "Base.WaterBottle", use="water")
    thirsty(r)
    tick(r, sv)
    assert "container" not in sv.need_marks and "water" not in sv.need_marks


def test_a_vessel_with_no_source_known_marks_the_water_want_only(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert need_why(tmp_path)["fill"] == {"vessel": 5, "source": None} and set(sv.need_marks) == {"water"}


def test_a_pza_1_4_build_is_sent_no_fill(tmp_path):
    r, sv = make(tmp_path, caps=CAPS_14)
    r.scan([source(105, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert not any(a.type == "fill" for a in r.acts.history) and "fill" not in need_why(tmp_path)


# ================================================================ the climb in routes (P24-G 4)
class Src:
    NAME = "test"

    def __init__(self, goal):
        self.goal = goal

    def propose(self, view):
        g, self.goal = self.goal, None
        return g


def fenced(hop=True):
    """A yard x 98..112, y 196..204, a fence on the west edge of the squares x 102 (blocked, hoppable unless `hop`
    is False: a wall)."""
    return [square(x, y, blockW=(x == 102), hopW=(x == 102 and hop)) for x in range(98, 113) for y in range(196, 205)]


def walk_stuck(r, g, me=(101.5, 200.5)):
    r.frame(x=me[0], y=me[1])
    runner = GoalRunner(Src(g), r.clock)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())   # the place is scanned already
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd()[0] == "walkTo"
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=me[0], y=me[1])
    return runner, runner.tick(r.world, r.acts)


def test_a_walk_stuck_at_a_hoppable_edge_climbs_it_then_walks_on(tmp_path):
    """P24-G 4: the explicit climb only where the walk failed `stuck` and the route's next edge (the line's first
    step from the player's square) is hoppable: `climb` of the fence's square (the edge's holder, x 102), then the
    walk again once the climb ends done."""
    r = Rig(tmp_path)
    r.scan(fenced())
    g = ExploreToward(110, 200)
    runner, cmd = walk_stuck(r, g)
    assert g.state == "running" and (cmd.TYPE, cmd.args()) == ("climb", {"x": 102, "y": 200})
    runner.send(cmd)
    r.answer()
    r.frame(x=102.5, y=200.5)
    cmd = runner.tick(r.world, r.acts)
    assert (cmd.TYPE, cmd.args()) == ("walkTo", {"x": 110, "y": 200, "gait": "walk"})
    all_sends_valid(r)


def test_a_walk_stuck_at_a_wall_or_far_from_the_fence_never_climbs(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced(hop=False))
    g = ExploreToward(110, 200)
    _, cmd = walk_stuck(r, g)
    assert cmd is None and (g.state, g.reason) == ("failed", "stuck")
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    r2.scan(fenced())
    g2 = ExploreToward(110, 200)
    _, cmd = walk_stuck(r2, g2, me=(99.5, 200.5))                                # the fence two squares on
    assert cmd is None and (g2.state, g2.reason) == ("failed", "stuck")


def test_a_failed_climb_fails_the_goal_and_a_pza_1_4_build_never_climbs(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced())
    g = ExploreToward(110, 200)
    runner, cmd = walk_stuck(r, g)
    runner.send(cmd)
    r.answer({"state": "failed", "reason": "fell"})
    r.frame(x=101.5, y=200.5)
    runner.tick(r.world, r.acts)
    assert (g.state, g.reason) == ("failed", "fell")
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b", caps=CAPS_14)
    r2.scan(fenced())
    g2 = ExploreToward(110, 200)
    _, cmd = walk_stuck(r2, g2)
    assert cmd is None and (g2.state, g2.reason) == ("failed", "stuck")


def test_hop_ahead_reads_the_first_step_its_holder_and_a_diagonal_through_an_open_corner(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced() + [square(101, 195, blockN=True, hopN=True)])
    r.frame(x=101.5, y=200.5)
    w = r.world
    assert w.hop_ahead((101.5, 200.5), (110.5, 200.5)) == (102, 200)               # east: the holder is the far square
    assert w.hop_ahead((102.5, 200.5), (95.5, 200.5)) == (102, 200)                # west: the holder is its own square
    assert w.hop_ahead((101.5, 200.5), (110.5, 209.5)) == (102, 200)               # a diagonal through (101, 201)
    assert w.hop_ahead((100.5, 200.5), (110.5, 200.5)) is None                     # the fence one square on
    assert w.hop_ahead((103.5, 200.5), (110.5, 200.5)) is None                     # no fence on the line


def test_no_route_ever_vaults_the_steer_probe_reads_a_hoppable_edge_blocked(tmp_path):
    """The sprint's legs and the stance's backpedal read `clear_heading` (`line_clear`, which never climbs): a
    heading over a hoppable fence is blocked, so a flee leg turns off it (Task 1b's rule, kept)."""
    r = Rig(tmp_path)
    r.scan(fenced())
    r.frame(x=101.5, y=200.5)
    assert not P.clear_heading(r.world, (1.0, 0.0)) and P.clear_heading(r.world, (-1.0, 0.0))
    assert r.world.reachable((101, 200, 0), (104, 200, 0))                        # a walk's flood climbs it


def test_the_world_applies_item_changed_and_drops_a_vessel_mark(tmp_path):
    """PZA/1.5.1's `item_changed` (Task 9 fix 1): the held item's use, fluid and amount from then on; a vessel-state
    mark (`filled`, `tainted`, `empty`) gives way to the engine's read, the others stay."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.Disinfectant", use="other")
    r.world.mark(5, "filled")
    r.world.mark_no_effect(6)
    r.event("item_changed", itemId=5, use="other", fluid="TaintedWater", amount=0.5)
    r.event("item_changed", itemId=6, use="other", amount=0.2)
    assert r.world.inventory[5]["use"] == "other" and r.world.inventory[5]["fluid"] == "TaintedWater"
    assert 5 not in r.world.marks and r.world.marks[6][0] == "no_effect" and r.world.tainted_ids() == {5}
    r.event("item_changed", itemId=5, use="container", amount=0.0)
    assert "fluid" not in r.world.inventory[5] and r.world.by_use()["container"] == [5]


def test_a_tainted_drink_refused_marks_it_undrinkable_and_no_tainted_source_is_filled_again(tmp_path):
    """The Lua refuses tainted water (`W.drinkable`): one fill from the tainted source, one refused drink, then the
    vessel reads `other` and the chain marks the want rather than loop fill-and-refuse."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200, tainted=True, infinite=True)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200})
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "TaintedWater", "tainted": True}})
    r.advance(S.FILL_SETTLE_S)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5})
    r.answer({"state": "failed", "reason": "not valid"})
    thirsty(r)
    tick(r, sv)
    assert r.world.marks[5][0] == "undrinkable" and sv.tainted_refused and 5 not in r.world.by_use()["container"]
    assert sum(a.type == "fill" for a in r.acts.history) == 1 and need_why(tmp_path)["fill"]["source"] is None


# ================================================================ Task 9 fix 2: the planner's side of item_changed
def test_item_changed_moves_a_vessel_between_container_and_water_and_clears_its_mark(tmp_path):
    """Item 1: a fill's event moves a `container` to `water` (the amount and fluid kept) and clears an `empty` mark; a
    drink to empty moves `water` back to `container`; an id not held is ignored."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    r.world.mark_empty(5)
    r.event("item_changed", itemId=5, use="water", fluid="Water", amount=0.5)
    assert r.world.by_use()["water"] == [5] and 5 not in r.world.marks
    assert r.world.inventory[5]["amount"] == 0.5 and r.world.inventory[5]["fluid"] == "Water"
    r.event("item_changed", itemId=5, use="container", amount=0.0)
    assert r.world.by_use()["container"] == [5] and r.world.by_use()["water"] == []
    before = dict(r.world.inventory)
    r.event("item_changed", itemId=99, use="water", fluid="Water", amount=1.0)
    assert r.world.inventory == before and 99 not in r.world.changes and r.world.missing_items == 0


def test_mark_empty_moves_a_drinkable_vessel_to_container_not_other(tmp_path):
    """Item 2: for the ticks before the event arrives (and on a log without it) an emptied bottle is a vessel."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.WaterBottle", use="water")
    hold(r, 6, "Base.Disinfectant", use="other")
    r.world.mark_empty(5)
    r.world.mark_empty(6)
    u = r.world.by_use()
    assert u["container"] == [5] and u["water"] == [] and u["other"] == [6]


def fill_rig(tmp_path, sources=(110,)):
    r, sv = make(tmp_path)
    r.scan([source(x, 200, infinite=True) for x in sources])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd()[0] == "fill"
    return r, sv


def test_a_done_fill_waits_for_its_item_changed_before_the_drink(tmp_path):
    """Item 3: done at t0: the need holds (settling), then drinks once the vessel's event reads it water."""
    assert S.FILL_SETTLE_S == 2.0
    r, sv = fill_rig(tmp_path)
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    thirsty(r)
    assert tick(r, sv) is None and need_why(tmp_path) == {"settling": 5} and 5 not in r.world.marks
    r.advance(1.0)
    thirsty(r)
    assert tick(r, sv) is None and need_why(tmp_path) == {"settling": 5}
    r.event("item_changed", itemId=5, use="water", fluid="Water", amount=0.5)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5}) and 5 not in r.world.marks and not sv.fills


def test_a_done_fill_with_no_event_reads_filled_after_fill_settle_s(tmp_path):
    r, sv = fill_rig(tmp_path)
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    thirsty(r)
    tick(r, sv)
    r.advance(S.FILL_SETTLE_S - 0.5)
    thirsty(r)
    assert tick(r, sv) is None and 5 not in r.world.marks
    r.advance(0.5)
    thirsty(r)
    tick(r, sv)
    assert r.world.marks[5][0] == "filled" and r.cmd() == ("consume", {"itemId": 5})


def test_a_tainted_fill_marks_its_source_square_tainted_and_the_next_fill_takes_another(tmp_path):
    """Item 3: a fill that read TaintedWater (the event, use other) from a source the map read clean puts that square
    in the World's `tainted_sources`; `water_sources` then reads it tainted and the next fill takes the clean one."""
    r, sv = make(tmp_path)
    r.scan([source(110, 200), source(120, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200})
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "TaintedWater"}})
    r.event("item_changed", itemId=5, use="other", fluid="TaintedWater", amount=0.5)
    thirsty(r)
    tick(r, sv)
    assert r.world.tainted_sources == {(110, 200, 0)} and r.world.tainted_ids() == {5}
    assert [(s[1], s[2].get("tainted")) for s in water_sources(r.world, math.inf)] == [((110, 200, 0), True),
                                                                                       ((120, 200, 0), False)]
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5})
    r.answer({"state": "failed", "reason": "not valid"})
    thirsty(r)
    tick(r, sv)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 6, "x": 120, "y": 200})


def test_the_event_after_a_drink_leaves_the_no_effect_mark_of_the_consume_check(tmp_path):
    """Item 3: the no-effect check is anchored on the consume's done; the drink's item_changed lands about a second
    later and clears no `no_effect` mark."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 7, "Base.WaterBottle", use="water")
    thirsty(r, game_min=480.0)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 7})
    r.answer("done")
    thirsty(r, game_min=482.0)                      # no fall in thirst
    tick(r, sv)
    r.event("item_changed", itemId=7, use="water", fluid="Water", amount=0.9)
    thirsty(r, game_min=483.0)
    tick(r, sv)
    assert r.world.marks[7][0] == "no_effect" and r.world.by_use()["other"] == [7]


def test_a_bandage_refused_in_bag_is_retried_after_care_retry_min(tmp_path):
    """Item 4: the item stays usable once moved out of the bag; the planner has no move action, so it only retries."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})
    r.answer({"state": "failed", "reason": "in bag"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=480.5)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care" and 10 not in r.world.marks
    r.advance(10.0)
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=482.5)
    for _ in range(10):
        tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})


def test_a_wash_refused_in_bag_is_retried_and_leaves_its_source(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [])
    tick(r, sv)
    assert r.cmd() == ("wash", {"itemId": 12, "x": 105, "y": 200})
    r.answer({"state": "failed", "reason": "in bag"})
    care_frame(r, [], game_min=480.5)
    tick(r, sv)
    assert not sv.care.dry and 12 not in r.world.marks and last(tmp_path)["branch"] != "care"
    r.advance(10.0)
    care_frame(r, [], game_min=482.5)
    for _ in range(10):
        tick(r, sv)
    assert r.cmd() == ("wash", {"itemId": 12, "x": 105, "y": 200})


def test_the_ripped_sheets_read_bandage_a_sealed_can_other_and_the_choice_order_holds(tmp_path):
    """Item 5: `RippedSheets` and the other CanBandage items count `bandage`, `Base.Pop2` (sealed) `other`; within the
    `bandage` use the care branch still reads the name: bandage > clean rag > dirty rag."""
    r, sv = make(tmp_path)
    r.frame()
    for iid, ft in ((1, "Base.RippedSheets"), (2, "Base.RippedSheetsDirty"), (3, "Base.Bandage"),
                    (4, "Base.DenimStrips"), (5, "Base.Pop2")):
        r.event("item_added", itemId=iid, fullType=ft, weight=0.1)       # no `use` on the line: the dataset answers
    care_frame(r, [part(5, bleeding=True, bleedingTime=20.0)])
    v = V.view(r.world, sv)
    assert v["inventory_by_use"]["bandage"] == 4 and v["inventory_by_use"]["other"] == 1
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 3, "part": 5})
    for iid in (3, 1, 4):                                                # then the clean rags, the dirty one last
        r.event("item_removed", itemId=iid)
        r.answer("done")
        care_frame(r, [part(5, bleeding=True, bleedingTime=20.0)])
        tick(r, sv)
        assert r.cmd()[1]["itemId"] == {3: 1, 1: 4, 4: 2}[iid]
