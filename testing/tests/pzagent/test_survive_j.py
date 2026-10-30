"""Survival 10 (Plan 24 Task 24; PZA/1.6.1 on the planner): the clothing record and `me.worn` in the World and the wear
rule (review-t9-fix9's ruling 5 and its amendment for the worn entry's holes and condition). The `clothing` loot, the
window past a stuck door and the goal descriptions' want order are `test_survive_k.py`. The fake mod over the PZA/1.6
skills."""
import pytest

from agent.base import pza1
from agent.base.planner import care as C

from .test_policies import all_sends_valid, zombie
from .test_survive import decisions, last, make, tick
from .test_survive_g import care_why, hold

CAPS_15 = tuple(t for t in pza1.ACTION_TYPES if t not in ("wear", "window"))   # a PZA/1.5 build: no wear, no window
JACKET = "base:jacket"
PANTS = "base:pants"


def rec(loc=JACKET, bite=10.0, scratch=20.0, cond=80, holes=0, cond_max=100, **k):
    """A PZA/1.6 item `clothing` record."""
    return dict({"loc": loc, "bite": bite, "scratch": scratch, "bullet": 0.0, "cond": cond, "condMax": cond_max,
                 "holes": holes, "worn": False}, **k)


def wl(loc=JACKET, bite=10.0, scratch=20.0, holes=0, cond=80):
    """A PZA/1.6.1 `me.worn` entry."""
    return {"loc": loc, "bite": bite, "scratch": scratch, "holes": holes, "cond": cond}


def cloth(r, iid, ft="Base.Jacket_Leather", weight=1.0, worn=False, **k):
    """A held garment with its clothing record (an `item_added` of a PZA/1.6.1 build)."""
    c = rec(**k)
    if worn:
        c["worn"] = True
    fields = {"worn": True} if worn else {}
    r.event("item_added", itemId=iid, fullType=ft, weight=weight, use="clothing", clothing=c, **fields)


def rig(tmp_path, worn=(), caps=None):
    """A PZA/1.6.1 build (the item record's fields), `me.worn` read as `worn`, an idle quiet scene with two clean
    dressings held (so the rag stock rips nothing) and no goal's open ground to walk."""
    r, sv = make(tmp_path, caps=caps)
    r.fake.hello(mod="1.6.1", **({} if caps is None else {"caps": list(caps)}))
    r.pump()
    hold(r, 10, "Base.Bandage")
    hold(r, 11, "Base.Bandage")
    r.frame(worn=list(worn))
    return r, sv


def sends(r, typ):
    return [a for a in r.acts.history if a.type == typ]


# ================================================================ 1. the World: the clothing record and me.worn
def test_the_clothing_record_is_kept_on_the_item_and_an_item_changed_replaces_it(tmp_path):
    """Task 24 item 1: an item_added's `clothing` lands on the item; an item_changed of a 1.6 log replaces it (the
    engine's re-read after a hit: more holes), and one that leaves it out drops it."""
    r, _ = rig(tmp_path)
    cloth(r, 20, holes=0)
    assert r.world.inventory[20]["clothing"]["holes"] == 0 and r.world.inventory[20]["use"] == "clothing"
    r.event("item_changed", itemId=20, use="clothing", clothing=rec(holes=2, cond=60))
    assert r.world.inventory[20]["clothing"]["holes"] == 2 and r.world.inventory[20]["clothing"]["cond"] == 60
    r.event("item_changed", itemId=20, use="clothing")
    assert "clothing" not in r.world.inventory[20]


def test_an_older_hellos_item_changed_leaves_the_clothing_record_alone(tmp_path):
    """The record is replaced only on a build that states it (`item_fields`, 1.5.2 or later)."""
    r, _ = make(tmp_path)           # the fake's default mod "fake": the pre-1.5.2 guess
    r.event("item_added", itemId=20, fullType="Base.Jacket_Leather", weight=1.0, use="clothing", clothing=rec())
    r.event("item_changed", itemId=20, use="clothing")
    assert r.world.inventory[20]["clothing"]["bite"] == 10.0


def test_me_worn_is_kept_across_null_frames_and_unknown_until_one_carries_it(tmp_path):
    """Task 24 item 1 (ruling 8): the Lua sends me.worn only when it changes, a null frame meaning unchanged: the World
    keeps the last non-null list, an empty list is nothing worn (known), and None before any frame carried one is
    unknown, never nothing worn."""
    r, _ = make(tmp_path)
    r.frame()
    assert r.world.worn is None and r.world.worn_total() == 0.0
    r.frame(worn=[wl(bite=5.0, scratch=7.0)])
    assert r.world.worn == [wl(bite=5.0, scratch=7.0)] and r.world.worn_total() == 12.0
    r.frame()
    r.frame()
    assert r.world.worn == [wl(bite=5.0, scratch=7.0)]
    r.frame(worn=[])
    assert r.world.worn == [] and r.world.worn_total() == 0.0


def test_an_item_changed_that_reads_a_worn_item_unworn_is_logged(tmp_path):
    """Task 24 (ruling 2): the garments a wear took off are the items whose item_changed sets worn false."""
    r, _ = rig(tmp_path)
    cloth(r, 20, worn=True)
    r.frame()
    r.event("item_changed", itemId=20, use="clothing", clothing=rec())
    assert list(r.world.unworn) == [(20, r.world.frame_n)] and "worn" not in r.world.inventory[20]


# ================================================================ 2. the wear rule
def test_the_wear_constants():
    assert (C.WEAR_RETRY_MIN, C.WEAR_QUIET_R, C.WEAR_SETTLE_FRAMES) == (10.0, 8.0, 2)


@pytest.mark.parametrize("cand,worn,want", [
    (rec(bite=20, scratch=30), None, 50.0),                                   # over nothing worn: its whole defence
    (rec(bite=0, scratch=0), None, None),                                     # no defence adds nothing
    (rec(bite=20, scratch=30), wl(bite=10, scratch=20), 20.0),                # beats an intact entry
    (rec(bite=10, scratch=20), wl(bite=10, scratch=20), None),                # equal: no
    (rec(bite=15, scratch=15), wl(bite=10, scratch=20), 0.0),                 # equal sum, higher bite: the tie
    (rec(bite=5, scratch=25), wl(bite=10, scratch=20), None),                 # equal sum, lower bite: no
    (rec(bite=5, scratch=5), wl(bite=10, scratch=20), None),                  # worse: no
    (rec(bite=40, scratch=40, holes=1), wl(bite=10, scratch=20), None),       # a holed candidate: never
    (rec(bite=40, scratch=40, cond=0), wl(bite=10, scratch=20), None),        # a spent candidate: never
    (rec(bite=40, scratch=40, holes=None), wl(bite=10, scratch=20), None),    # holes unread: never
    (rec(bite=10, scratch=20), wl(bite=10, scratch=20, holes=1), 30.0),       # a holed worn entry: equal swaps it
    (rec(bite=11, scratch=20), wl(bite=10, scratch=20, holes=2), 31.0),       # ... and better
    (rec(bite=5, scratch=20), wl(bite=10, scratch=20, holes=1), None),        # ... a lower nominal does not
    (rec(bite=5, scratch=5), wl(bite=10, scratch=20, cond=0), None),          # a spent worn entry: nominal still bars
    (rec(bite=10, scratch=20), wl(bite=10, scratch=20, cond=0), 30.0),
    (rec(bite=10, scratch=20), wl(bite=10, scratch=20, cond=None), None),     # cond unread, no holes: intact
])
def test_the_wear_gain(cand, worn, want):
    """Task 24 item 2: `c.cond > 0`, `c.holes == 0`, bite + scratch beats the worn entry (0 where none), ties to the
    higher bite; a worn entry with holes (or spent) is swapped for an intact candidate of equal or better nominal."""
    assert C.wear_gain(cand, worn) == want


def test_a_better_jacket_is_worn_and_the_goal_does_not_run(tmp_path):
    """Task 24 item 2: no threat, nothing running, worn known, a held jacket beating the worn one: the care branch
    wears it (its why `wear`, under `stock`); the best of two candidates is taken."""
    r, sv = rig(tmp_path, worn=[wl(bite=5, scratch=5)])
    cloth(r, 20, bite=20.0, scratch=20.0)
    cloth(r, 21, bite=30.0, scratch=20.0)
    cloth(r, 22, bite=1.0, scratch=1.0)
    r.frame()
    tick(r, sv)
    assert r.cmd() == ("wear", {"itemId": 21}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path)["stock"] == {"reason": "wear", "item": 21, "loc": JACKET, "gain": 40.0}
    all_sends_valid(r)


@pytest.mark.parametrize("c,w", [
    (dict(bite=1.0, scratch=1.0), wl()),                  # worse
    (dict(bite=40.0, scratch=40.0, holes=1), wl()),       # holed
    (dict(bite=40.0, scratch=40.0, cond=0), wl()),        # spent
])
def test_a_worse_holed_or_spent_garment_is_not_worn(tmp_path, c, w):
    r, sv = rig(tmp_path, worn=[w])
    cloth(r, 20, **c)
    r.frame()
    tick(r, sv)
    assert not sends(r, "wear")


def test_a_garment_over_a_bare_location_is_worn_and_the_other_location_is_left_alone(tmp_path):
    r, sv = rig(tmp_path, worn=[wl(loc=PANTS, bite=30, scratch=30)])
    cloth(r, 20, loc=JACKET, bite=3.0, scratch=4.0)
    cloth(r, 21, loc=PANTS, bite=3.0, scratch=4.0)
    r.frame()
    tick(r, sv)
    assert r.cmd() == ("wear", {"itemId": 20})


def test_a_holed_worn_garment_is_swapped_for_an_intact_one_of_equal_defence(tmp_path):
    """The 9 fix 10 amendment: the worn entry's holes defend nothing, so an intact equal garment swaps it."""
    r, sv = rig(tmp_path, worn=[wl(bite=10, scratch=20, holes=2)])
    cloth(r, 20, bite=10.0, scratch=20.0)
    r.frame()
    tick(r, sv)
    assert r.cmd() == ("wear", {"itemId": 20}) and care_why(tmp_path)["stock"]["gain"] == 30.0


def test_nothing_is_worn_while_me_worn_is_unknown(tmp_path):
    """Ruling 8: no frame has carried me.worn, so nothing is read as worn and nothing is put on."""
    r, sv = make(tmp_path)
    r.fake.hello(mod="1.6.1")
    r.pump()
    hold(r, 10, "Base.Bandage")
    hold(r, 11, "Base.Bandage")
    cloth(r, 20)
    r.frame()
    assert r.world.worn is None
    tick(r, sv)
    assert not sends(r, "wear")


@pytest.mark.parametrize("kw", [dict(attackers=1), dict(hit_reaction="HitReaction")])
def test_no_wear_while_attacked_or_reeling(tmp_path, kw):
    """Ruling 3: a wear runs 50 ticks and stops on a run; never while an attacker or a hit reaction reads."""
    r, sv = rig(tmp_path, worn=[wl(bite=1, scratch=1)])
    cloth(r, 20)
    r.frame(**kw)
    tick(r, sv)
    assert not sends(r, "wear")


def test_no_wear_with_a_zombie_inside_eight_tiles_or_a_threat_held_and_one_beyond_it_is_quiet(tmp_path):
    """Ruling 3 and the brief: no zombie seen within about 8 squares, and a threat within DANGER_R is the threat
    branch's. A zombie at 12 tiles leaves the tick quiet."""
    for zx, want in ((103.0, False), (107.0, False), (112.0, True)):
        d = tmp_path / str(int(zx))
        d.mkdir()
        r, sv = rig(d, worn=[wl(bite=1, scratch=1)])
        cloth(r, 20)
        r.frame(zombies=[dict(zombie(1, zx, 200.0), hasTarget=False)])
        tick(r, sv)
        assert bool(sends(r, "wear")) is want, zx


def test_the_wear_quiet_radius_is_its_own_eight_tiles_beside_the_stocks_quiet(tmp_path):
    """The care's own read (a wear is 50 action ticks, stopped by a run): with `quiet` set by hand (the stock's own
    DISENGAGE_R test aside), a zombie listed within WEAR_QUIET_R bars the wear and one beyond it does not."""
    for zx, want in ((106.0, False), (109.0, True)):
        d = tmp_path / str(int(zx))
        d.mkdir()
        r, sv = rig(d, worn=[wl(bite=1, scratch=1)])
        cloth(r, 20)
        r.frame(zombies=[dict(zombie(1, zx, 200.0), hasTarget=False)])
        sv.care.world, sv.care.actions, sv.care.quiet = r.world, r.acts, True
        cmd, why = sv.care.stock()
        assert (cmd is not None) is want, zx


def test_the_wear_needs_the_build_to_announce_it(tmp_path):
    r, sv = rig(tmp_path, worn=[wl(bite=1, scratch=1)], caps=CAPS_15)
    cloth(r, 20)
    r.frame()
    tick(r, sv)
    assert not sends(r, "wear")


def test_one_wear_per_item_per_ten_game_minutes(tmp_path):
    """Task 24: the same item is not worn again within WEAR_RETRY_MIN (10) game minutes of its send (a wear that ended
    done and left it unworn, here; a failed one is also cooled ten ticks by the planner's own rule)."""
    r, sv = rig(tmp_path, worn=[wl(bite=1, scratch=1)])
    cloth(r, 20)
    r.frame(game_min=480.0)
    tick(r, sv)
    assert r.cmd() == ("wear", {"itemId": 20})
    r.answer()
    settle(r, sv, n=3, game_min=485.0)
    assert len(sends(r, "wear")) == 1
    assert sv.care.wear_at == {20: 480.0}
    settle(r, sv, n=1, game_min=490.0)
    assert len(sends(r, "wear")) == 2


def test_the_rag_stock_goes_before_the_wear(tmp_path):
    """The stock's order: an unworn cotton garment is ripped for the rag stock before any wear."""
    r, sv = make(tmp_path)
    r.fake.hello(mod="1.6.1")
    r.pump()
    r.event("item_added", itemId=30, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
            clothing=rec(loc="base:tshirt", bite=1.0, scratch=1.0))
    cloth(r, 20, bite=30.0, scratch=30.0)
    r.frame(worn=[wl(bite=1, scratch=1)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 30})


def settle(r, sv, n=4, **frame):
    """`n` quiet frames and ticks, any action the goal started answered first (the wear checks need frames, and the stock
    needs an idle tick)."""
    for _ in range(n):
        if r.acts.current is not None:
            r.answer()
        r.frame(**frame)
        tick(r, sv)


def wear_done(r, sv, iid=20, replaced=None, worn_after=None, off=None):
    """Send the wear of `iid`, answer it done (with `replaced`), then the engine's reads: the `off` ids item_changed
    unworn ({id: its record}) and `worn_after` the new me.worn (the frame after the done)."""
    tick(r, sv)
    assert r.cmd() == ("wear", {"itemId": iid})
    r.fake.answer({"wear": ["accepted", {"state": "done", "result": dict({"itemId": iid, "loc": JACKET},
                                                                        **({} if replaced is None else {"replaced": replaced}))}]})
    r.pump()
    for o, c in off.items():
        r.event("item_changed", itemId=o, use="clothing", clothing=c)
    r.frame(worn=worn_after)
    tick(r, sv)


def test_a_wear_that_lowers_the_worn_defence_wears_the_removed_garments_again_and_never_the_candidate(tmp_path):
    """Ruling 2: a wear can take off garments at exclusive locations that `replaced` does not name. A jacket 21 and a hat
    22 are worn; wearing 20 (a jacket exclusive with the hat) takes both off; the summed defence fell (70 to 20), so 22
    is put on again (21 is the replaced one) and 20 is marked and never worn again."""
    r, sv = rig(tmp_path, worn=[wl(JACKET, 5, 5), wl("base:hat", 30, 30)])
    cloth(r, 21, worn=True, bite=5.0, scratch=5.0)
    cloth(r, 22, ft="Base.Hat_Army", worn=True, loc="base:hat", bite=30.0, scratch=30.0)
    cloth(r, 20, bite=10.0, scratch=10.0)
    r.frame()
    wear_done(r, sv, replaced=21, worn_after=[wl(JACKET, 10, 10)], off={21: rec(bite=5.0, scratch=5.0), 22: rec("base:hat", 30.0, 30.0)})
    assert sv.care.wearing["before"] == 70.0
    settle(r, sv, n=3)
    assert set(r.world.marked("wear_loses")) == {20}
    assert [a.args["itemId"] for a in sends(r, "wear")] == [20, 22]
    assert {"reason": "rewear", "item": 22} in [d["inputs"]["branches"].get("care", {}).get("stock")
                                                for d in decisions(tmp_path)]
    r.answer()
    settle(r, sv, n=3, game_min=520.0, worn=[wl(JACKET, 10, 10), wl("base:hat", 30, 30)])
    assert [a.args["itemId"] for a in sends(r, "wear")] == [20, 22]      # 20 is marked: never again
    assert not sends(r, "drop")


@pytest.mark.parametrize("level,want", [(1, True), (0, False)])
def test_a_wear_that_does_not_lower_the_defence_drops_the_replaced_garment_under_load(tmp_path, level, want):
    """Ruling 4: `replaced` stays in the inventory and adds weight: dropped when the wear held and the load is above
    level 0; at level 0 it is kept."""
    r, sv = rig(tmp_path, worn=[wl(JACKET, 5, 5)])
    cloth(r, 21, worn=True, bite=5.0, scratch=5.0)
    cloth(r, 20, bite=30.0, scratch=30.0)
    r.frame(level=level)
    wear_done(r, sv, replaced=21, worn_after=[wl(JACKET, 30, 30)],
              off={21: rec(bite=5.0, scratch=5.0)})
    settle(r, sv, n=3, level=level)
    assert any(a.type == "drop" and a.args == {"itemId": 21} for a in r.acts.history) is want
    assert not r.world.marked("wear_loses")
