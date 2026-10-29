"""PZAgent_Tend.lua (PZA/1.5, ruling P24-G; Plan 24 Task 9): the care skills bandage (vanilla's ISApplyBandage on the
worst or a named part), rip (vanilla's OnNewCraft on the RipClothing recipe) and wash (vanilla's ISWashClothing at a
water source), each skill's accept, progress, done and every refusal on the lupa host under the fake player."""
import pytest

from .conftest import J, make_cell, make_player
from .test_lua_skills import OFF, acts, load, start, states, tick


def ended(lua):
    return lua.eval("PZA.skills.cur") is None


def tend_item(p, ft, iid, **members):
    """An inventory item of full type ft and id iid, with `members` as its Java members (each a value answered); its
    getContainer the player's main inventory (PZA/1.5.1: a `getContainer` member overrides it, a bag)."""
    inv = p.getInventory(p)
    it = J(getFullType=lambda s: ft, getID=lambda s: iid, getWeight=lambda s: 0.1, IsFood=lambda s: False,
           getFluidContainer=lambda s: None, getHungerChange=lambda s: 0.0, getContainer=lambda s: inv)
    for k, v in members.items():
        setattr(it, k, (lambda val: lambda s, *a: val(*a) if callable(val) else val)(v))
    p.held.append(it)
    return it


def make_part(i, bleeding=False, bleeding_time=0.0, bandaged=False, life=0.0, deep=False, scratched=False,
              infected=False, health=100.0):
    st = {"bandaged": bandaged, "life": life, "bleeding": bleeding}
    part = J(getHealth=lambda s: health, bleeding=lambda s: st["bleeding"], getBleedingTime=lambda s: bleeding_time,
             bandaged=lambda s: st["bandaged"], getBandageLife=lambda s: st["life"],
             isBandageDirty=lambda s: st["life"] <= 0, deepWounded=lambda s: deep, scratched=lambda s: scratched,
             isCut=lambda s: False, bitten=lambda s: False, isInfectedWound=lambda s: infected, getIndex=lambda s: i,
             getDeepWoundTime=lambda s: 5.0 if deep else 0.0, getScratchTime=lambda s: 5.0 if scratched else 0.0,
             getCutTime=lambda s: 0.0, getBiteTime=lambda s: 0.0)
    part.st = st
    return part


def with_parts(p, parts):
    bd = p.getBodyDamage(p)
    bd.getBodyParts = lambda s: J(size=lambda s2: len(parts), get=lambda s2, i: parts[i])
    return parts


def apply_bandage(lua, p, part, item):
    """What the server's ISApplyBandage.complete does, as the client sees it: the item gone, the part bandaged."""
    p.held.remove(item)
    part.st["bandaged"] = True
    part.st["life"] = 0.0 if "Dirty" in item.getFullType(item) else 3.5


# ---- bandage --------------------------------------------------------------------------------------------------------

def test_bandage_of_the_worst_part_picks_the_bleeding_deep_wound_and_is_done_once_applied(lua, fs):
    load(lua)
    p = make_player()
    parts = with_parts(p, [make_part(0), make_part(1, bleeding=True, bleeding_time=9.0),
                           make_part(2, bleeding=True, bleeding_time=3.0, deep=True), make_part(3, scratched=True)])
    rag = tend_item(p, "Base.RippedSheets", 50, isCanBandage=True)
    start(lua, p, "bandage", itemId=50)
    tick(lua, p)
    g = lua.globals()
    assert [(b[2], b[3], b[4]) for b in g._bandages] == [(rag, parts[2], True)] and g._bandages[0][0] is p
    assert g._bandages[0][1] is p and g._queue.cleared >= 1
    tick(lua, p, 3)
    assert not ended(lua)
    apply_bandage(lua, p, parts[2], rag)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"part": 2, "dirty": False, "life": 3.5}
    assert list(p.sets[-3:]) == OFF


def test_the_worst_without_a_deep_wound_is_the_longest_bleeding_then_a_dirty_bandage_then_a_scratch(lua, fs):
    load(lua)
    g = lua.globals()
    cases = [
        ([make_part(0, scratched=True), make_part(1, bleeding=True, bleeding_time=2.0),
          make_part(2, bleeding=True, bleeding_time=7.0)], 2),
        ([make_part(0, scratched=True), make_part(1, bandaged=True, life=0.0, scratched=True),
          make_part(2, bandaged=True, life=2.0, scratched=True)], 1),
        ([make_part(0), make_part(1, scratched=True)], 1),
    ]
    for k, (parts, want) in enumerate(cases):
        p = make_player()
        with_parts(p, parts)
        tend_item(p, "Base.Bandage", 60, isCanBandage=True)
        start(lua, p, "bandage", aid="b%d" % k, itemId=60)
        tick(lua, p)
        assert g._bandages[-1][3] is parts[want], k


def test_a_bandaged_part_has_its_bandage_taken_off_first(lua, fs):
    load(lua)
    p = make_player()
    parts = with_parts(p, [make_part(0, bandaged=True, life=0.0, scratched=True)])
    rag = tend_item(p, "Base.RippedSheets", 50, isCanBandage=True)
    start(lua, p, "bandage", itemId=50, part=0)
    tick(lua, p)
    assert [(b[2], b[3], b[4]) for b in lua.globals()._bandages] == [(None, parts[0], False), (rag, parts[0], True)]


def test_a_dirty_rag_is_reported_dirty(lua, fs):
    load(lua)
    p = make_player()
    parts = with_parts(p, [make_part(0, bleeding=True, bleeding_time=4.0)])
    rag = tend_item(p, "Base.RippedSheetsDirty", 51, isCanBandage=True)
    start(lua, p, "bandage", itemId=51)
    tick(lua, p)
    apply_bandage(lua, p, parts[0], rag)
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"] == {"part": 0, "dirty": True, "life": 0.0}


def test_bandage_refusals(lua, fs):
    load(lua)
    p = make_player()
    with_parts(p, [make_part(0), make_part(1)])
    tend_item(p, "Base.RippedSheets", 50, isCanBandage=True)
    tend_item(p, "Base.Hammer", 51, isCanBandage=False)
    start(lua, p, "bandage", aid="none", itemId=99)
    start(lua, p, "bandage", aid="nv", itemId=51)
    start(lua, p, "bandage", aid="nw", itemId=50)
    start(lua, p, "bandage", aid="range", itemId=50, part=17)
    start(lua, p, "bandage", aid="type", itemId=50, part="arm")
    start(lua, p, "bandage", aid="id", itemId="x")
    assert states(acts(lua, fs)) == [("none", "rejected", "none held"), ("nv", "rejected", "not valid"),
                                     ("nw", "rejected", "no wound"), ("range", "rejected", "bad args"),
                                     ("type", "rejected", "bad args"), ("id", "rejected", "bad args")]


def test_a_named_part_is_bandaged_whatever_its_wounds(lua, fs):
    load(lua)
    p = make_player()
    parts = with_parts(p, [make_part(0), make_part(1)])
    tend_item(p, "Base.Bandage", 50, isCanBandage=True)
    start(lua, p, "bandage", itemId=50, part=1)
    tick(lua, p)
    assert lua.globals()._bandages[-1][3] is parts[1]


def test_a_bandage_never_applied_is_interrupted_and_without_its_action_not_loaded(lua, fs):
    load(lua)
    p = make_player()
    with_parts(p, [make_part(0, bleeding=True, bleeding_time=1.0)])
    tend_item(p, "Base.Bandage", 50, isCanBandage=True)
    start(lua, p, "bandage", aid="slow", itemId=50)
    tick(lua, p)
    lua.globals()._clock["ms"] += 20001
    tick(lua, p)
    lua.globals().ISApplyBandage = None
    start(lua, p, "bandage", aid="nl", itemId=50)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] == "failed"] == [("slow", "failed", "interrupted"),
                                                                      ("nl", "failed", "not loaded")]
    assert lua.eval("PZA.skills.errors") == 0


def test_a_raising_bandage_constructor_is_not_valid(lua, fs):
    load(lua)
    p = make_player()
    with_parts(p, [make_part(0, bleeding=True, bleeding_time=1.0)])
    tend_item(p, "Base.Bandage", 50, isCanBandage=True)

    def boom(*a):
        raise RuntimeError("vanilla raised")
    lua.globals().ISApplyBandage = J(new=boom)
    start(lua, p, "bandage", itemId=50)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not valid")


# ---- rip ------------------------------------------------------------------------------------------------------------

def cotton(p, iid=70, worn=False, tags=("RIP_CLOTHING_COTTON",)):
    return tend_item(p, "Base.Tshirt_DefaultTEXTURE", iid, isWorn=worn, hasTag=lambda t: t in tags)


def test_rip_runs_vanillas_on_new_craft_and_counts_the_rags_and_the_dirty(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player()
    shirt = cotton(p)
    start(lua, p, "rip", itemId=70)
    tick(lua, p)
    assert [(c[0], c[1].name, c[2], c[3]) for c in g._crafts] == [(shirt, "RipClothing", 0, False)]
    tick(lua, p, 3)
    assert not ended(lua)
    p.held.remove(shirt)
    tend_item(p, "Base.RippedSheets", 71)
    tend_item(p, "Base.RippedSheets", 72)
    tend_item(p, "Base.RippedSheetsDirty", 73)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"rags": 3, "dirty": 1}


def test_rip_refuses_worn_denim_leather_and_not_cotton_items(lua, fs):
    load(lua)
    p = make_player()
    cotton(p, 70, worn=True)
    cotton(p, 71, tags=("RIP_CLOTHING_DENIM",))
    cotton(p, 72, tags=("RIP_CLOTHING_LEATHER",))
    cotton(p, 73, tags=())
    for aid, iid in (("w", 70), ("d", 71), ("l", 72), ("n", 73), ("h", 99)):
        start(lua, p, "rip", aid=aid, itemId=iid)
    assert states(acts(lua, fs)) == [("w", "rejected", "worn"), ("d", "rejected", "needs tool"),
                                     ("l", "rejected", "needs tool"), ("n", "rejected", "not cotton"),
                                     ("h", "rejected", "none held")]
    assert lua.globals()._crafts == []


def test_rip_whose_craft_vanilla_refused_is_not_valid_and_without_its_path_not_loaded(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player()
    cotton(p)
    g._craft["queue"] = False                                    # canPerformCurrentRecipe refused: nothing queued
    start(lua, p, "rip", aid="r", itemId=70)
    tick(lua, p)
    g.ISInventoryPaneContextMenu = None
    start(lua, p, "rip", aid="n", itemId=70)
    tick(lua, p)
    g.ItemTag = None
    start(lua, p, "rip", aid="t", itemId=70)
    assert [s for s in states(acts(lua, fs)) if s[1] in ("failed", "rejected")] == [
        ("r", "failed", "not valid"), ("n", "failed", "not loaded"), ("t", "rejected", "not loaded")]


def test_a_rip_that_never_lands_is_interrupted(lua, fs):
    load(lua)
    p = make_player()
    cotton(p)
    start(lua, p, "rip", itemId=70)
    tick(lua, p)
    lua.globals()._clock["ms"] += 20001
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")


# ---- wash -----------------------------------------------------------------------------------------------------------

def sink(amount=10000.0, tainted=False, infinite=True):
    st = {"amount": amount}
    o = J(_cls="IsoObject", hasWater=lambda s: st["amount"] > 0, hasFluid=lambda s: st["amount"] > 0,
          getFluidAmount=lambda s: st["amount"], isTaintedWater=lambda s: tainted,
          isWaterInfinite=lambda s: infinite)
    o.st = st
    return o


def water_world(lua, src, x=11, y=20):
    objs = [J(_cls="IsoObject"), src]
    sq = J(getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
           isSolid=lambda s: False, isSolidTrans=lambda s: False)
    squares = {(x, y, 0): sq}
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if (dx, dy) != (0, 0):
                squares[(x + dx, y + dy, 0)] = J(isSolid=lambda s: False, isSolidTrans=lambda s: False)
    lua.globals()._cell = make_cell(squares=squares)
    return sq


def dirty_rag(p, iid=80, blood=0.5):
    return tend_item(p, "Base.RippedSheetsDirty", iid, isCanBandage=True, getItemAfterCleaning="Base.RippedSheets",
                     getBloodLevel=blood)


def test_wash_beside_a_sink_queues_vanillas_wash_without_soap_and_is_done_when_the_rag_is_clean(lua, fs):
    load(lua)
    g = lua.globals()
    src = sink()
    water_world(lua, src)
    p = make_player()
    rag = dirty_rag(p)
    start(lua, p, "wash", itemId=80, x=11, y=20)
    tick(lua, p)
    assert g._washes == [(p, src, rag, 0.5, 0, True)]
    tick(lua, p, 2)
    p.held.remove(rag)
    tend_item(p, "Base.RippedSheets", 81)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"water": 6}       # ceil(4 + 3 x 0.5)


def test_wash_with_soap_held_passes_no_soap_false(lua, fs):
    load(lua)
    g = lua.globals()
    water_world(lua, sink())
    p = make_player()
    dirty_rag(p)
    inv = p.getInventory(p)
    inv.getSoapList = lambda s, a, b: J(isEmpty=lambda s2: False)
    start(lua, p, "wash", itemId=80, x=11, y=20)
    tick(lua, p)
    assert g._washes[-1][5] is False


def test_wash_from_afar_walks_next_to_the_source_first(lua, fs):
    load(lua)
    g = lua.globals()
    water_world(lua, sink(), x=14, y=20)
    p = make_player()
    dirty_rag(p)
    start(lua, p, "wash", itemId=80, x=14, y=20)
    tick(lua, p)
    assert g._queue.adds[-1].Type == "ISWalkToTimedAction" and g._washes == []


def test_wash_refusals(lua, fs):
    load(lua)
    water_world(lua, sink(amount=5.0))
    p = make_player()
    dirty_rag(p, 80, blood=0.5)                                 # needs 6
    dirty_rag(p, 81, blood=0.0)                                 # needs 4
    tend_item(p, "Base.RippedSheets", 82, getItemAfterCleaning="")
    for aid, kw in (("nw", {"itemId": 80, "x": 11, "y": 20}), ("ok", {"itemId": 81, "x": 11, "y": 20}),
                    ("nd", {"itemId": 82, "x": 11, "y": 20}), ("ns", {"itemId": 81, "x": 30, "y": 20}),
                    ("bad", {"itemId": 81, "x": "a", "y": 20}), ("nh", {"itemId": 99, "x": 11, "y": 20})):
        start(lua, p, "wash", aid=aid, **kw)
    assert states(acts(lua, fs)) == [("nw", "rejected", "no water"), ("ok", "accepted", ""),
                                     ("nd", "rejected", "not dirty"),
                                     ("ns", "rejected", "no source"), ("bad", "rejected", "bad args"),
                                     ("nh", "rejected", "none held")]


def test_a_square_without_a_water_object_is_no_source(lua, fs):
    load(lua)
    water_world(lua, J(_cls="IsoObject", hasWater=lambda s: False))
    p = make_player()
    dirty_rag(p)
    start(lua, p, "wash", itemId=80, x=11, y=20)
    assert states(acts(lua, fs)) == [("a1", "rejected", "no source")]


def test_a_wash_that_never_lands_is_interrupted_and_without_its_action_not_loaded(lua, fs):
    load(lua)
    water_world(lua, sink())
    p = make_player()
    dirty_rag(p)
    start(lua, p, "wash", aid="slow", itemId=80, x=11, y=20)
    tick(lua, p)
    lua.globals()._clock["ms"] += 40001
    tick(lua, p)
    lua.globals().ISWashClothing = None
    start(lua, p, "wash", aid="nl", itemId=80, x=11, y=20)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] == "failed"] == [("slow", "failed", "interrupted"),
                                                                      ("nl", "failed", "not loaded")]


def test_a_care_skill_after_an_aim_releases_the_stance(lua, fs):
    load(lua)
    p = make_player()
    with_parts(p, [make_part(0, bleeding=True, bleeding_time=1.0)])
    tend_item(p, "Base.Bandage", 50, isCanBandage=True)
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5)
    tick(lua, p)
    start(lua, p, "bandage", aid="b", itemId=50)
    assert [c[0] for c in p.aim["calls"]] == ["setForceAim", "nullifyAiming"]


@pytest.mark.parametrize("typ,args", [("bandage", {"itemId": 50}), ("rip", {"itemId": 70}),
                                      ("wash", {"itemId": 80, "x": 11, "y": 20})])
def test_a_player_dying_mid_care_fails_it_dead(lua, fs, typ, args):
    load(lua)
    water_world(lua, sink())
    p = make_player()
    with_parts(p, [make_part(0, bleeding=True, bleeding_time=1.0)])
    tend_item(p, "Base.Bandage", 50, isCanBandage=True)
    cotton(p)
    dirty_rag(p)
    start(lua, p, typ, **args)
    tick(lua, p)
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 0.0)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "dead")


# ---- fill -----------------------------------------------------------------------------------------------------------

def vessel(p, iid=90, amount=0.0, capacity=1.0, can_add=True, ft="Base.WaterBottle"):
    from .conftest import make_fluid
    fc = make_fluid(amount=amount, capacity=capacity, can_add=can_add)
    tend_item(p, ft, iid, getFluidContainer=fc)
    return fc


def test_fill_an_empty_bottle_at_a_sink_queues_vanillas_take_water_and_is_done_when_full(lua, fs):
    load(lua)
    g = lua.globals()
    src = sink()
    water_world(lua, src)
    p = make_player()
    fc = vessel(p)
    start(lua, p, "fill", itemId=90, x=11, y=20)
    tick(lua, p)
    assert [(t[2], t[3]) for t in g._takes] == [(src, False)] and g._takes[0][0] is p
    tick(lua, p, 2)
    assert not ended(lua)
    fc.st["amount"] = 1.0                                       # the server's fill, synced
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"amount": 1.0, "added": 1.0, "fluid": "Water", "tainted": False}
    assert list(p.sets[-3:]) == OFF


def test_a_part_filled_water_bottle_is_topped_up_and_done_once_the_amount_holds_still(lua, fs):
    load(lua)
    water_world(lua, sink())
    p = make_player()
    fc = vessel(p, amount=0.25)
    start(lua, p, "fill", itemId=90, x=11, y=20)
    tick(lua, p)
    fc.st["amount"] = 0.6                                       # risen, not full (the inventory weight capped it)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1499
    tick(lua, p)
    assert not ended(lua)
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"]["added"] == pytest.approx(0.35)


def test_a_tainted_source_passes_tainted_to_the_action(lua, fs):
    load(lua)
    water_world(lua, sink(tainted=True))
    p = make_player()
    vessel(p)
    start(lua, p, "fill", itemId=90, x=11, y=20)
    tick(lua, p)
    assert lua.globals()._takes[-1][3] is True


def test_fill_refusals(lua, fs):
    load(lua)
    water_world(lua, J(_cls="IsoObject", hasWater=lambda s: True, getFluidAmount=lambda s: 0.0))   # drained
    p = make_player()
    vessel(p, 90)
    vessel(p, 91, amount=1.0)                                   # full
    vessel(p, 92, can_add=False)                                # takes no water
    vessel(p, 93, capacity=10.0, ft="Base.BucketEmpty")         # over the drink menu's 3 litres
    tend_item(p, "Base.Hammer", 94)                             # no fluid container
    for aid, kw in (("nw", {"itemId": 90, "x": 11, "y": 20}), ("full", {"itemId": 91, "x": 11, "y": 20}),
                    ("nc", {"itemId": 92, "x": 11, "y": 20}), ("big", {"itemId": 93, "x": 11, "y": 20}),
                    ("ham", {"itemId": 94, "x": 11, "y": 20}), ("ns", {"itemId": 90, "x": 30, "y": 20}),
                    ("bad", {"itemId": 90, "x": "a", "y": 20}), ("nh", {"itemId": 99, "x": 11, "y": 20})):
        start(lua, p, "fill", aid=aid, **kw)
    assert states(acts(lua, fs)) == [("nw", "rejected", "no water"), ("full", "rejected", "full"),
                                     ("nc", "rejected", "not a container"), ("big", "rejected", "not a container"),
                                     ("ham", "rejected", "not a container"), ("ns", "rejected", "no source"),
                                     ("bad", "rejected", "bad args"), ("nh", "rejected", "none held")]


def test_a_fill_from_afar_walks_first_and_one_that_never_rises_is_interrupted(lua, fs):
    load(lua)
    g = lua.globals()
    water_world(lua, sink(), x=14, y=20)
    p = make_player()
    vessel(p)
    start(lua, p, "fill", aid="far", itemId=90, x=14, y=20)
    tick(lua, p)
    assert g._queue.adds[-1].Type == "ISWalkToTimedAction" and g._takes == []
    water_world(lua, sink())
    start(lua, p, "fill", aid="slow", itemId=90, x=11, y=20)
    tick(lua, p)
    g._clock["ms"] += 30001
    tick(lua, p)
    g.ISTakeWaterAction = None
    start(lua, p, "fill", aid="nl", itemId=90, x=11, y=20)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] == "failed"] == [
        ("far", "failed", "superseded"), ("slow", "failed", "interrupted"), ("nl", "failed", "not loaded")]


# ---- PZA/1.5.1 (Task 9 fix 1): an item in a bag, rip's hasActionType, the shared helpers ------------------------------

def test_bandage_and_wash_refuse_an_item_in_a_bag_and_fill_takes_one(lua, fs):
    """Review minor 3: K.itemById finds an item in a bag, but the server's ISApplyBandage and ISWashClothing refuse
    one not in the main inventory; ISTakeWaterAction:isValid asks only that the item has a container."""
    load(lua)
    water_world(lua, sink())
    p = make_player()
    with_parts(p, [make_part(0, bleeding=True, bleeding_time=3.0)])
    bag = J(_cls="ItemContainer")
    tend_item(p, "Base.Bandage", 50, isCanBandage=True, getContainer=bag)
    tend_item(p, "Base.RippedSheetsDirty", 51, isCanBandage=True, getItemAfterCleaning="Base.RippedSheets",
              getBloodLevel=0.0, getContainer=bag)
    loose = tend_item(p, "Base.Bandage", 52, isCanBandage=True)
    loose.getContainer = None                                   # the member absent: fails closed
    from .conftest import make_fluid
    tend_item(p, "Base.WaterBottle", 53, getFluidContainer=make_fluid(amount=0.0), getContainer=bag)
    start(lua, p, "bandage", aid="b", itemId=50)
    start(lua, p, "wash", aid="w", itemId=51, x=11, y=20)
    start(lua, p, "bandage", aid="n", itemId=52)
    start(lua, p, "fill", aid="f", itemId=53, x=11, y=20)
    assert states(acts(lua, fs)) == [("b", "rejected", "in bag"), ("w", "rejected", "in bag"),
                                     ("n", "rejected", "in bag"), ("f", "accepted", "")]


def test_a_rip_without_has_action_type_fails_not_loaded(lua, fs):
    """Review minor 7: the queue check failed open when hasActionType was absent."""
    load(lua)
    p = make_player()
    cotton(p)
    lua.globals().ISTimedActionQueue.hasActionType = None
    start(lua, p, "rip", itemId=70)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")

