"""The Dress maneuver (Plan 31 Task 8; the spec `2026-11-05-plan-31-the-rebuild-design.md` § 4 item 3; Angus's direction
of 2026-11-05, memory `stand-and-fight-dress-first`): `maneuvers.Dress(part)`, one commitment from the stop to the
dressing of one bleeding part, under the maneuver contract (`maneuvers.base.Maneuver`), and the ladder's care branch
dispatching it behind Survive's `DRESS_MANEUVER` (off: the goldens' rule). The fake mod over PZA/1.7.

The reading behind it (F15, `f_goals_16-20261105-164332`, its `f_grade.txt` line 60: "9 unwears sent, 0 done, rejected
{'moving': 9}"; line 14: "bandage sent 3 done 1"): every unwear of the only cotton garment went out while a flee's leg
ran, so the Dress stops first and sends no unwear until a frame reads `me.moving` false.
"""
import pytest

from agent.base.planner import care as C
from agent.base.planner import dispatch as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner.maneuvers import Dress, Maneuver, Melee
from agent.base.planner.maneuvers import dress as DM

from .fakemod import DEFAULT_FRAME
from .test_policies import Rig, all_sends_valid
from .test_survive import last, make, tick
from .test_survive_g import part
from .test_survive_j import rec

TSHIRT = "base:tshirt"


# ================================================================ the fixtures
def hello17(r):
    """A PZA/1.7 hello (the item record's `worn` and `rip`, the `unwear` skill among the default caps)."""
    r.fake.hello(mod="1.7.0")
    r.pump()


def frame(r, parts, moving=False, zombies=()):
    """A frame with `parts` (the body's part records), `me.moving` and `zombies`."""
    me = dict(DEFAULT_FRAME["me"], moving=moving)
    body = dict(DEFAULT_FRAME["body"], parts=list(parts), bleeding=sum(1 for p in parts if p.get("bleeding")))
    r.fake.frame(me=me, body=body, zombies=list(zombies))
    r.pump()


def bleed(r, i=1, bt=5.0, **k):
    frame(r, [part(i, bleeding=True, bleedingTime=bt)], **k)


def dressed(r, i=1, **k):
    """Part `i` bandaged, its bleeding flag cleared (the schema: a bandage clears it)."""
    frame(r, [part(i, bandaged=True, bandageLife=3.0, bandageDirty=False)], **k)


def zombie(zid, dx, on_floor=False):
    """A listed zombie `dx` tiles east of the fake frame's player (100, 200)."""
    return {"id": zid, "x": 100.0 + dx, "y": 200.0, "dist": abs(dx), "hasTarget": True, "crawler": False,
            "health": 1.0, "onFloor": on_floor}


def hold(r, iid, ft):
    r.event("item_added", itemId=iid, fullType=ft, weight=0.1, use="bandage")


def worn_shirt(r, iid=20):
    """The worn cotton T-shirt (PZA/1.7's item record: worn, cotton, its clothing record)."""
    r.event("item_added", itemId=iid, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
            worn=True, clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0, worn=True))


def unworn_shirt(r, iid=20):
    """The Lua's item_changed reading the T-shirt unworn (`markWear`)."""
    r.event("item_changed", itemId=iid, use="clothing", rip="cotton", clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0))


def rig(tmp_path, i=1, moving=False):
    r = Rig(tmp_path)
    hello17(r)
    bleed(r, i, moving=moving)
    return r


def drive(r, m):
    """One owner tick: `observe`, `step`, its command sent through the rig's Actions and `sent` told; the Action or
    None."""
    m.observe()
    cmd = m.step()
    if cmd is None:
        return None
    a = r.acts.send(cmd)
    m.sent(cmd, a)
    return a


def end(r, a, state="done", reason="", result=None):
    r.fake.act(a.aid, "accepted", a.type)
    r.fake.act(a.aid, state, a.type, reason=reason, result={} if result is None and state == "done" else result)
    r.pump()


# ================================================================ the contract
def test_dress_is_a_maneuver_registered_beside_melee():
    assert issubclass(Dress, Maneuver) and Dress.name == "dress"
    assert D.MANEUVERS == {"melee": Melee, "dress": Dress}
    assert DM.KEEP_R is P.KEEP_R and DM.ENDS == ("done", "failed", "superseded")


def test_the_stop_goes_first_and_no_unwear_while_me_moving_reads_true(tmp_path):
    """F15's nine `moving` refusals: the first command is the stop; while the frames read `me.moving` true after
    its end nothing is sent; the first frame reading it false sends the unwear of the worn cotton T-shirt."""
    r = rig(tmp_path, moving=True)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    a = drive(r, m)
    assert a.type == "stop" and m.over() is None
    end(r, a)
    for _ in range(3):
        bleed(r, moving=True)
        assert drive(r, m) is None and m.why["phase"] == "still"
    bleed(r, moving=False)
    b = drive(r, m)
    assert (b.type, b.args) == ("unwear", {"itemId": 20})
    assert [x.type for x in r.acts.history] == ["stop", "unwear"]
    all_sends_valid(r)


def test_a_stop_that_leaves_the_character_moving_is_sent_again_and_bounded(tmp_path):
    """STILL_FRAMES frames still moving after a stop's end send the stop again; past DRESS_MOVED such waits the Dress
    ends failed `moving`, having sent only stops, each STILL_FRAMES frames after the last one's end."""
    r = rig(tmp_path, moving=True)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    gaps, n = [], 0
    for _ in range(100):
        a = drive(r, m)
        if a is not None:
            gaps.append(n)
            end(r, a)
            n = 0
        if m.over() is not None:
            break
        bleed(r, moving=True)
        n += 1
    assert m.over() == "failed" and m.why["fail"] == "moving"
    assert [x.type for x in r.acts.history] == ["stop"] * (DM.DRESS_MOVED + 1)
    assert gaps == [0] + [DM.STILL_FRAMES] * DM.DRESS_MOVED and n == DM.STILL_FRAMES


def test_the_unwear_then_the_rip_then_the_bandage_with_the_rag(tmp_path):
    """Nothing held: the unwear of the worn T-shirt, the wait for its item_changed, the rip of that garment, the wait
    for its rag, the bandage of the part with it; each command's end read before the next."""
    r = rig(tmp_path)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))                                   # the stop
    bleed(r)
    a = drive(r, m)
    assert (a.type, a.args) == ("unwear", {"itemId": 20}) and drive(r, m) is None   # its end not yet read
    end(r, a, result={"itemId": 20, "loc": TSHIRT})
    bleed(r)
    assert drive(r, m) is None and m.why["phase"] == "unworn"   # the garment still reads worn
    unworn_shirt(r)
    bleed(r)
    b = drive(r, m)
    assert (b.type, b.args) == ("rip", {"itemId": 20})
    end(r, b, result={"rags": 1, "dirty": 0})
    r.event("item_removed", itemId=20, fullType="Base.Tshirt_White")
    bleed(r)
    assert drive(r, m) is None and m.why["phase"] == "rag"
    hold(r, 41, "Base.RippedSheets")
    bleed(r)
    c = drive(r, m)
    assert (c.type, c.args) == ("bandage", {"itemId": 41, "part": 1})
    assert [x.type for x in r.acts.history] == ["stop", "unwear", "rip", "bandage"]
    all_sends_valid(r)


def test_the_rip_when_no_dressing_is_held(tmp_path):
    """An unworn cotton garment held and no dressing: the rip of it, no unwear."""
    r = rig(tmp_path)
    r.event("item_added", itemId=22, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
            clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0))
    worn_shirt(r, 20)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    a = drive(r, m)
    assert (a.type, a.args) == ("rip", {"itemId": 22})
    assert not any(x.type == "unwear" for x in r.acts.history)


def test_the_held_bandage_is_used_with_no_rip(tmp_path):
    """A clean bandage held beside a rag and a rippable garment: the bandage on the part, then done on the frame
    that reads the part's bleeding false; no rip, no unwear."""
    r = rig(tmp_path)
    hold(r, 11, "Base.RippedSheets")
    hold(r, 10, "Base.Bandage")
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    a = drive(r, m)
    assert (a.type, a.args) == ("bandage", {"itemId": 10, "part": 1}) and m.why["item"] == 10
    end(r, a, result={"part": 1, "dirty": False, "life": 3.0})
    dressed(r)
    assert drive(r, m) is None and m.over() == "done"
    assert [x.type for x in r.acts.history] == ["stop", "bandage"]


def test_an_unwashed_rag_is_taken_while_the_part_bleeds(tmp_path):
    """The dirty rag alone held, the part's bleedingTime under DIRTY_RAG_MIN (the care branch's time rule would
    refuse it): the Dress takes it, no garment torn."""
    r = Rig(tmp_path)
    hello17(r)
    bleed(r, bt=2.0)
    hold(r, 12, "Base.RippedSheetsDirty")
    worn_shirt(r)
    assert C.dressing_pick(C.held_dressings(r.world), 2.0) is None                     # the care branch's rule
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r, bt=2.0)
    a = drive(r, m)
    assert (a.type, a.args) == ("bandage", {"itemId": 12, "part": 1}) and m.why["kind"] == "dirty"


def test_the_end_is_done_when_the_part_s_bleeding_reads_false(tmp_path):
    """No end while the part reads bleeding after the bandage's done; `done` on the first frame reading it false; a
    Dress of a part already not bleeding ends done at once with nothing sent."""
    r = rig(tmp_path)
    hold(r, 10, "Base.Bandage")
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    end(r, drive(r, m))
    bleed(r)
    assert drive(r, m) is None and m.over() is None and m.why["phase"] == "settle"
    frame(r, [part(1, bleeding=False, bleedingTime=4.0, bandaged=True)])
    m.observe()
    assert m.over() == "done" and m.step() is None
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    hello17(r2)
    dressed(r2)
    m2 = Dress(r2.world, r2.acts, r2.clock, part=1)
    assert drive(r2, m2) is None and m2.over() == "done" and r2.acts.history == []


def test_failed_with_nothing_held_and_nothing_to_tear(tmp_path):
    r = rig(tmp_path)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    assert drive(r, m) is None and m.over() == "failed" and m.why["fail"] == "nothing"


@pytest.mark.parametrize("dx,on_floor,ends", [(2.4, False, True), (P.KEEP_R, False, True), (2.6, False, False),
                                              (5.0, False, False), (1.0, True, False)])
def test_superseded_only_by_a_standing_zombie_within_keep_r(tmp_path, dx, on_floor, ends):
    """A standing zombie at 2.4 tiles or at KEEP_R ends the Dress `superseded`; one at 2.6 or 5.0, or one lying on the
    floor at 1.0, leaves it running (its bandage still sent)."""
    r = rig(tmp_path)
    hold(r, 10, "Base.Bandage")
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r, zombies=[zombie(7, dx, on_floor)])
    a = drive(r, m)
    if ends:
        assert a is None and m.over() == "superseded"
    else:
        assert a.type == "bandage" and m.over() is None


def test_another_sender_s_command_is_no_end_the_dress_resumes_at_the_stop(tmp_path):
    """One commitment: a flee's leg sent over the Dress's unwear supersedes it in the Lua, but the Dress does not end;
    its next step sends the stop again (`lost` 1), then the unwear once still."""
    r = rig(tmp_path)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    a = drive(r, m)
    assert a.type == "unwear"
    leg = r.acts.send(P.WalkTo(110.5, 200.5, "run"))
    m.observe()
    assert m.over() is None and m.why["lost"] == 1
    r.fake.act(a.aid, "failed", "unwear", reason="superseded")
    end(r, leg)
    bleed(r, moving=True)
    b = drive(r, m)
    assert b.type == "stop" and m.over() is None
    end(r, b)
    bleed(r)
    assert drive(r, m).type == "unwear"


def test_an_unwear_refused_moving_stops_again_and_keeps_the_garment(tmp_path):
    """A `moving` refusal is the character's motion, never the garment's: back to the stop, the same unwear after it."""
    r = rig(tmp_path)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    a = drive(r, m)
    r.fake.act(a.aid, "rejected", "unwear", reason="moving")
    r.pump()
    bleed(r)
    b = drive(r, m)
    assert b.type == "stop"
    end(r, b)
    bleed(r)
    assert (drive(r, m).args, m.held_out) == ({"itemId": 20}, {})


def test_a_rip_refused_for_good_marks_the_garment_and_picks_the_next(tmp_path):
    r = rig(tmp_path)
    for iid in (22, 23):
        r.event("item_added", itemId=iid, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
                clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0))
    m = Dress(r.world, r.acts, r.clock, part=1)
    end(r, drive(r, m))
    bleed(r)
    a = drive(r, m)
    assert a.args == {"itemId": 22}
    r.fake.act(a.aid, "rejected", "rip", reason="not cotton")
    r.pump()
    bleed(r)
    assert drive(r, m).args == {"itemId": 23} and 22 in r.world.marked("unrippable")


# ================================================================ the ride
def test_an_upper_body_part_rides_the_walk_with_a_held_dressing(tmp_path):
    """`ride=True` at a part above the legs: no stop, the bandage with keepMoving, the caller's walk kept; it runs
    while the walk leg is current (a riding bandage leaves the leg its slot)."""
    r = rig(tmp_path, i=5, moving=True)
    hold(r, 10, "Base.Bandage")
    leg = r.acts.send(P.WalkTo(110.5, 200.5, "walk"))
    m = Dress(r.world, r.acts, r.clock, part=5, ride=True)
    a = drive(r, m)
    assert (a.type, a.args) == ("bandage", {"itemId": 10, "part": 5, "keepMoving": True}) and m.ride
    leg2 = r.acts.send(P.WalkTo(111.5, 200.5, "walk"))   # the caller's re-aimed leg
    bleed(r, i=5, moving=True)
    assert m.running() and drive(r, m) is None and m.over() is None
    assert not r.acts.done(leg) or not r.acts.done(leg2)


@pytest.mark.parametrize("i", [C.LEG_FIRST, 13, 16])
def test_the_legs_and_feet_never_ride(tmp_path, i):
    r = rig(tmp_path, i=i, moving=True)
    hold(r, 10, "Base.Bandage")
    m = Dress(r.world, r.acts, r.clock, part=i, ride=True)
    assert not m.ride and drive(r, m).type == "stop"


def test_a_ride_with_nothing_held_drops_the_ride_and_stops_to_tear(tmp_path):
    r = rig(tmp_path, i=5, moving=True)
    worn_shirt(r)
    m = Dress(r.world, r.acts, r.clock, part=5, ride=True)
    a = drive(r, m)
    assert a.type == "stop" and not m.ride


def test_a_ride_the_engine_stopped_goes_on_standing(tmp_path):
    """A riding bandage failed `stopped` (a run, an aim, a hit): the ride is dropped, the stop sent, the bandage
    again standing (no keepMoving)."""
    r = rig(tmp_path, i=5, moving=True)
    hold(r, 10, "Base.Bandage")
    m = Dress(r.world, r.acts, r.clock, part=5, ride=True)
    a = drive(r, m)
    end(r, a, state="failed", reason="stopped")
    bleed(r, i=5, moving=True)
    b = drive(r, m)
    assert b.type == "stop" and not m.ride
    end(r, b)
    bleed(r, i=5)
    assert drive(r, m).args == {"itemId": 10, "part": 5}


# ================================================================ the item choice (care.py's pure reads)
def test_the_care_item_choice_is_pure_and_in_the_dress_order(tmp_path):
    r = Rig(tmp_path)
    hello17(r)
    r.frame()
    worn_shirt(r)
    assert C.dress_pick(r.world, 5.0) == ("unwear", 20, TSHIRT, 3.0)
    assert C.dress_pick(r.world, 5.0, unwear_at={20: r.world.world_minutes()}) is None
    r.event("item_added", itemId=22, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
            clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0))
    assert C.dress_pick(r.world, 5.0) == ("rip", 22)
    hold(r, 12, "Base.RippedSheetsDirty")
    assert C.dress_pick(r.world, 5.0) == ("bandage", 12, "dirty")
    assert C.dress_pick(r.world, 5.0, dirty_ok=False) == ("rip", 22)
    hold(r, 10, "Base.Bandage")
    assert C.dress_pick(r.world, 5.0) == ("bandage", 10, "bandage")
    assert C.dress_pick(r.world, 5.0, held_out={10: r.world.world_minutes()}) == ("bandage", 12, "dirty")


# ================================================================ the ladder's care branch behind DRESS_MANEUVER
def dress_rig(tmp_path, on=True):
    r, sv = make(tmp_path)
    hello17(r)
    worn_shirt(r)
    r.frame()
    bleed(r, i=9, bt=14.7, moving=True)
    sv.DRESS_MANEUVER = on
    return r, sv


def care(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["care"]


def test_the_switch_is_off_by_default_and_off_the_care_branch_sends_as_before(tmp_path):
    """Off (the ladder's goldens): the bleeding step's own unwear goes on the first tick, moving or not (the rule F15
    ran)."""
    assert S.Survive.DRESS_MANEUVER is False
    r, sv = dress_rig(tmp_path, on=False)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and care(tmp_path)["reason"] == "unwear"
    assert sv.care.dress is None


def test_on_the_care_branch_dispatches_the_dress_and_holds_its_tick_while_it_waits(tmp_path):
    """On: the stop first (the care's line, `dress` its log), the tick held while `me.moving` reads true after the
    stop's end (no lower branch: the thirst's drink waits), the unwear once still, its end logged once."""
    r, sv = dress_rig(tmp_path)
    r.event("item_added", itemId=30, fullType="Base.WaterBottle", weight=0.5, use="water")
    tick(r, sv)
    assert r.cmd() == ("stop", {}) and last(tmp_path)["branch"] == "care"
    assert care(tmp_path)["reason"] == "dress" and care(tmp_path)["dress"]["part"] == 9
    r.answer()
    r.fake.frame(me=dict(DEFAULT_FRAME["me"], moving=True),
                 body=dict(DEFAULT_FRAME["body"], parts=[part(9, bleeding=True, bleedingTime=14.7)], bleeding=1),
                 stats=dict(DEFAULT_FRAME["stats"], thirst=0.5))
    r.pump()
    tick(r, sv)
    assert last(tmp_path)["branch"] == "care" and last(tmp_path)["action"] is None
    assert care(tmp_path)["dress"]["phase"] == "still"
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and last(tmp_path)["sent"]
    r.answer({"state": "done", "result": {"itemId": 20, "loc": TSHIRT}})
    unworn_shirt(r)
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 20})
    r.answer({"state": "done", "result": {"rags": 1, "dirty": 1}})
    r.event("item_removed", itemId=20, fullType="Base.Tshirt_White")
    hold(r, 41, "Base.RippedSheetsDirty")
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 41, "part": 9})
    r.answer({"state": "done", "result": {"part": 9, "dirty": True, "life": 0.0}})
    dressed(r, i=9)
    tick(r, sv)
    assert care(tmp_path)["dress_end"]["end"] == "done" and sv.care.dress is None
    tick(r, sv)
    assert "dress_end" not in care(tmp_path)
    all_sends_valid(r)


def test_on_a_ride_tick_the_care_rides_the_worst_part_above_the_legs(tmp_path):
    """The threat's ride (`ride_now`, P24-U) with a deep leg wound the worst and a hand bleeding: the Dress goes on the
    hand, riding (keepMoving, no stop), as the bleeding step's own ride; the leg waits for a standing tick."""
    r = Rig(tmp_path)
    hello17(r)
    hold(r, 10, "Base.Bandage")
    frame(r, [part(13, bleeding=True, bleedingTime=20.0, deep=True), part(5, bleeding=True, bleedingTime=3.0)],
          moving=True)
    c = C.Care(r.world, r.acts, r.clock)
    c.dress_cls, c.ride_now = Dress, True
    r.acts.send(P.WalkTo(110.5, 200.5, "walk"))
    c.observe()
    cmd = c.choose()
    assert (cmd.TYPE, cmd.args()) == ("bandage", {"itemId": 10, "part": 5, "keepMoving": True})
    assert c.owns(cmd) and c.why["dress"]["ride"] is True
    c.send(cmd)
    assert c.dress.action is c.last and c.sends == {}


def test_on_a_cooled_dress_send_is_still_sent(tmp_path):
    """A Dress's re-sent unwear after a `moving` refusal is the Dress's own retry (bounded by DRESS_SENDS), never
    cooled for FAILED_COOLDOWN_TICKS as a branch's repeated failure is."""
    r, sv = dress_rig(tmp_path)
    tick(r, sv)
    r.answer()
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})
    r.answer({"state": "rejected", "reason": "moving"})
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("stop", {})
    r.answer()
    bleed(r, i=9, bt=14.7)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and last(tmp_path)["inputs"]["cooled"] is None
