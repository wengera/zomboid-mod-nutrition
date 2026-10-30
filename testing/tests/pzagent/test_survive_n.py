"""Survival 11 (survival iteration 10; Plan 24 Task 27; PZA/1.7's `me.loadedWidth` and `unwear`): ruling P24-AI (the goal's legs read off
the client's loaded window, `goals.leg_max`: 8 x floor(width / 16) - 8 tiles, LEG_MAX 40 with no width read; P24-AC's
30 superseded) and ruling P24-AJ (the rag stock's second path: a bleeding part with nothing to dress it and nothing
unworn to rip takes the unwear of the worn cotton garment covering the least, never shoes or trousers, on the stock's
idle quiet tick, then the rip of that same garment once it reads unworn). The fake mod over PZA/1.7."""
import math

import pytest

from agent.base import pza1
from agent.base.planner import care as C
from agent.base.planner import goals as G
from agent.base.world import World

from .fakemod import DEFAULT_FRAME
from .test_policies import Rig, all_sends_valid, zombie
from .test_survive import last, make, tick
from .test_survive_g import care_frame, care_why, part
from .test_survive_i import far_runner, step
from .test_survive_j import rec


def wframe(r, width, x=100.5, y=200.5):
    """A frame carrying `me.loadedWidth` `width` (None: the Lua's unchanged null)."""
    r.fake.frame(me=dict(DEFAULT_FRAME["me"], x=x, y=y, loadedWidth=width))
    r.pump()


# ================================================================ P24-AI: the loaded-window legs
@pytest.mark.parametrize("width,leg", [(104, 40.0), (152, 64.0), (None, 40.0), (120, 48.0), (16, 10.0)])
def test_leg_max_reads_the_loaded_window(tmp_path, width, leg):
    """#4375: 40 at 104 tiles (1280 x 720), 64 at 152 (1920 x 1080); absent, the constant 40; never under LEG_MIN."""
    r = Rig(tmp_path)
    wframe(r, width)
    assert G.leg_max(r.world) == leg and r.world.loaded_width == width
    assert (G.LEG_MAX, G.LEG_CHUNK) == (40.0, 8)


def test_the_width_is_kept_across_null_frames(tmp_path):
    """The Lua sends `me.loadedWidth` on the first frame and when it changes (null otherwise): the World keeps the last."""
    r = Rig(tmp_path)
    wframe(r, 152)
    wframe(r, None)
    r.frame()
    assert r.world.loaded_width == 152 and G.leg_max(r.world) == 64.0
    assert G.leg_max(World()) == G.LEG_MAX


def test_a_far_walk_s_legs_follow_the_window(tmp_path):
    """P24-AI: ExploreToward(200, 200) from (100.5, 200.5) at a 152-tile window: legs of 64 tiles (the square centre
    63 tiles on), the full length again after a done leg; halved to 32 on `no square`."""
    r = Rig(tmp_path)
    wframe(r, 152)
    g = G.ExploreToward(200, 200)
    runner = far_runner(r, g)
    cmd = step(r, runner)
    assert (cmd.x, cmd.y) == (163.5, 200.5) and g.why["legLen"] == 64.0
    r.answer({"state": "failed", "reason": "no square"})
    r.frame(x=100.5, y=200.5)
    cmd = step(r, runner)
    assert g.why["legLen"] == 32.0 and math.hypot(cmd.x - 100.5, cmd.y - 200.5) <= 32.0
    r.answer()
    r.frame(x=cmd.x, y=cmd.y)
    step(r, runner)
    assert g.why["legLen"] == 64.0


def test_the_leg_reads_the_window_at_each_full_leg(tmp_path):
    """A window that changes (a resize) is read at the next full leg."""
    r = Rig(tmp_path)
    wframe(r, 104)
    g = G.ExploreToward(300, 200)
    runner = far_runner(r, g)
    cmd = step(r, runner)
    assert g.why["legLen"] == 40.0
    r.answer()
    wframe(r, 152, x=cmd.x, y=cmd.y)
    step(r, runner)
    assert g.why["legLen"] == 64.0


# ================================================================ P24-AJ: unwear then rip
TSHIRT, SHIRT = "base:tshirt", "base:shirt"


def worn(r, iid, ft, loc, bite, scratch, rip="cotton"):
    """A worn garment of a PZA/1.7 build (the item record's `worn`, `rip` and clothing record)."""
    r.event("item_added", itemId=iid, fullType=ft, weight=0.2, use="clothing", rip=rip, worn=True,
            clothing=rec(loc=loc, bite=bite, scratch=scratch, worn=True))


def unwear_rig(tmp_path, garments=None, caps=None):
    """A PZA/1.7 hello, worn garments (default: a T-shirt 20 covering 3, a shirt 21 covering 7, trousers 22 and shoes
    23 covering 1), no dressing held, part 9 bleeding, no zombie."""
    r, sv = make(tmp_path, caps=caps)
    r.fake.hello(mod="1.7.0", **({} if caps is None else {"caps": list(caps)}))
    r.pump()
    for g in garments if garments is not None else (
            (20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0), (21, "Base.Shirt_FormalWhite", SHIRT, 2.0, 5.0),
            (22, "Base.Trousers", "base:pants", 0.5, 0.5), (23, "Base.Shoes_Black", "base:shoes", 0.5, 0.5)):
        worn(r, *g)
    r.frame()
    bleed(r)
    return r, sv


def bleed(r, **k):
    care_frame(r, [part(9, bleeding=True, bleedingTime=14.7)], **k)


def unworn(r, iid, loc=TSHIRT):
    """The unwear's done and the Lua's item_changed reading the garment unworn (`markWear`)."""
    r.fake.answer({"unwear": ["accepted", {"state": "done", "result": {"itemId": iid, "loc": loc}}]})
    r.pump()
    r.event("item_changed", itemId=iid, use="clothing", rip="cotton", clothing=rec(loc=loc, bite=1.0, scratch=2.0))


def test_the_unwear_never_list():
    assert all(C.UNWEAR_NEVER.search(loc) for loc in ("base:shoes", "base:pants", "base:pantsextra", "base:boots"))
    assert not any(C.UNWEAR_NEVER.search(loc) for loc in (TSHIRT, SHIRT, "base:socks", "base:underwearbottom"))


def test_the_chain_unwears_the_least_covering_cotton_garment_then_rips_it(tmp_path):
    """P24-AJ: nothing to dress part 9 and nothing unworn to rip: the idle quiet tick unwears the T-shirt (covering 3,
    less than the shirt's 7; never the trousers or the shoes), its line the care branch's (`stock` `unwear`); while
    its done is read but the garment still reads worn nothing else is unworn; once the item_changed reads it unworn
    the bleeding step rips that same garment (`no_rag`)."""
    r, sv = unwear_rig(tmp_path)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path)["stock"] == {"reason": "unwear", "item": 20, "loc": TSHIRT, "cover": 3.0}
    r.fake.answer({"unwear": ["accepted", {"state": "done", "result": {"itemId": 20, "loc": TSHIRT}}]})
    r.pump()
    bleed(r)
    tick(r, sv)
    assert not any(a.type in ("unwear", "rip") and a.args["itemId"] == 21 for a in r.acts.history)
    assert sum(1 for a in r.acts.history if a.type == "unwear") == 1
    r.event("item_changed", itemId=20, use="clothing", rip="cotton", clothing=rec(loc=TSHIRT, bite=1.0, scratch=2.0))
    if r.acts.current is not None:
        r.answer()
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 20}) and care_why(tmp_path)["reason"] == "no_rag"
    assert sv.care.unworn_item is None
    all_sends_valid(r)


def test_the_rip_takes_the_unworn_garment_before_any_other(tmp_path):
    """P24-AJ: the rip is on the same item: with a lower-id unworn cotton garment looted meanwhile, the unworn one
    goes first."""
    r, sv = unwear_rig(tmp_path)
    tick(r, sv)
    unworn(r, 20)
    r.event("item_added", itemId=5, fullType="Base.Tshirt_Blue", weight=0.2, use="clothing", rip="cotton",
            clothing=rec(loc=TSHIRT, bite=1.0, scratch=1.0))
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 20})


def test_never_under_a_threat_held(tmp_path):
    """P24-AJ: a zombie at 4 tiles: the threat answers; one idle at 9.5 tiles is no quiet tick: no unwear."""
    r, sv = unwear_rig(tmp_path)
    bleed(r, zombies=[zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat"
    (tmp_path / "b").mkdir()
    r2, sv2 = unwear_rig(tmp_path / "b")
    bleed(r2, zombies=[dict(zombie(1, 109.5, 200.0), hasTarget=False)])
    tick(r2, sv2)
    for rr in (r, r2):
        assert not any(a.type == "unwear" for a in rr.acts.history)


def test_never_the_shoes_or_the_trousers_and_none_without_a_wound(tmp_path):
    r, sv = unwear_rig(tmp_path, garments=((22, "Base.Trousers", "base:pants", 0.5, 0.5),
                                           (23, "Base.Shoes_Black", "base:shoes", 0.5, 0.5)))
    tick(r, sv)
    assert not any(a.type == "unwear" for a in r.acts.history) and care_why(tmp_path).get("want") == "bandage"
    (tmp_path / "b").mkdir()
    r2, sv2 = unwear_rig(tmp_path / "b")
    care_frame(r2, [part(9)])
    tick(r2, sv2)
    assert not any(a.type == "unwear" for a in r2.acts.history)


def test_a_denim_or_unclassed_garment_is_never_unworn(tmp_path):
    r, sv = unwear_rig(tmp_path, garments=((24, "Base.Shirt_Denim", SHIRT, 1.0, 1.0, "denim"),))
    tick(r, sv)
    assert not any(a.type == "unwear" for a in r.acts.history)


def test_one_unwear_per_item_per_wear_retry_min(tmp_path):
    """P24-AJ: WEAR_RETRY_MIN applies: an unwear the Lua stopped is not re-sent on that garment for 10 game minutes
    (Survive's failed-command cooldown, FAILED_COOLDOWN_TICKS ticks, passed meanwhile)."""
    from agent.base.planner import survive as S
    r, sv = unwear_rig(tmp_path, garments=((20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0),))
    tick(r, sv)
    r.answer({"state": "failed", "reason": "stopped"})
    for k in range(S.FAILED_COOLDOWN_TICKS + 2):
        bleed(r, game_min=483.0 + 0.5 * k)
        tick(r, sv)
        if r.acts.current is not None:
            r.answer()
    assert sum(1 for a in r.acts.history if a.type == "unwear") == 1
    bleed(r, game_min=490.5)   # past 490 (worldAge's hours read back as 489.99... minutes at 490)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})


def test_a_build_without_unwear_unwears_nothing(tmp_path):
    caps = tuple(t for t in pza1.ACTION_TYPES if t != "unwear")
    r, sv = unwear_rig(tmp_path, caps=caps)
    tick(r, sv)
    assert not any(a.type == "unwear" for a in r.acts.history) and care_why(tmp_path).get("want") == "bandage"
