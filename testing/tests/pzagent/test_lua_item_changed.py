"""PZAgent_Sense.lua's item_changed (PZA/1.5.1, Plan 24 Task 9 fix 1, review major 1): an item's use was read once, at
its first sight, so a bottle a fill filled read container and one drunk empty read water for good. A fill, a consume,
a wash or a rip ending on a held item marks it (PZAgent_Tend.lua's end hooks), and the next events calls read it
again: an item_changed{itemId, use, fluid, amount} when its use or its settled fluid amount changed, the inventory's
entry taking the new use. On the lupa host under the fake player, the skills run by the runner and the events read by
S.events as Main reads them."""
import json

from agent.base import pza1
from .conftest import make_fluid, make_player
from .test_lua_sense import events, frame, load
from .test_lua_skills import LIVE, acts, start, states, tick
from .test_lua_tend import sink, tend_item, water_world


def changed(ev):
    return [e for e in ev if e["event"] == "item_changed"]


def bottle(p, iid=90, amount=0.0, ft="Base.WaterBottle"):
    fc = make_fluid(amount=amount, capacity=1.0)
    tend_item(p, ft, iid, getFluidContainer=fc)
    return fc


def seen(lua, p):
    """The inventory's first sight (S.lastInv seeded, as Main does after hello) and the first frame."""
    lua.eval("PZA.sense.firstSight(...)", p)
    return frame(lua, p)


def use_of(lua, iid):
    return lua.eval("PZA.sense.lastInv[%d].use" % iid)


def test_a_fill_turns_its_empty_bottle_from_container_to_water_in_one_item_changed(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    water_world(lua, sink())
    p = make_player()
    fc = bottle(p)
    prev = seen(lua, p)
    assert use_of(lua, 90) == "container"
    start(lua, p, "fill", itemId=90, x=11, y=20)
    tick(lua, p)
    fc.st["amount"] = 1.0                                       # the server's fill, synced
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")
    ev, prev = events(lua, p, prev)
    assert changed(ev) == [{"event": "item_changed", "gameMin": 450, "itemId": 90, "use": "water", "fluid": "Water",
                            "amount": 1.0}]
    assert use_of(lua, 90) == "water"
    lua.globals()._clock["ms"] += 1000
    ev, prev = events(lua, p, prev)
    ev2, _ = events(lua, p, prev)
    assert changed(ev) == [] and changed(ev2) == [] and lua.eval("PZA.sense.recheckIds[90]") is None


def test_a_consume_drunk_to_empty_turns_water_to_container_once_the_drink_settles(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    fc = bottle(p, amount=0.5)
    prev = seen(lua, p)
    assert use_of(lua, 90) == "water"
    start(lua, p, "consume", itemId=90)
    tick(lua, p)
    fc.st["amount"] = 0.3                                       # the drink's first sip lands: consume is done
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")
    g = lua.globals()
    ev, prev = events(lua, p, prev)
    assert changed(ev) == []                                    # still water, the drink running on
    fc.st["amount"] = 0.0
    ev, prev = events(lua, p, prev)
    assert changed(ev) == []                                    # not settled yet
    g._clock["ms"] += 999
    ev, prev = events(lua, p, prev)
    assert changed(ev) == []
    g._clock["ms"] += 1
    ev, prev = events(lua, p, prev)
    assert changed(ev) == [{"event": "item_changed", "gameMin": 450, "itemId": 90, "use": "container",
                            "amount": 0.0}]                    # empty: no primary fluid, so no fluid key
    assert use_of(lua, 90) == "container"
    g._clock["ms"] += 5000
    ev, _ = events(lua, p, prev)
    assert changed(ev) == [] and lua.eval("PZA.sense.recheckIds[90]") is None


def test_a_part_drunk_bottle_still_water_reports_its_settled_amount_once(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    fc = bottle(p, amount=0.5)
    prev = seen(lua, p)
    start(lua, p, "consume", itemId=90)
    tick(lua, p)
    fc.st["amount"] = 0.25
    tick(lua, p)
    g = lua.globals()
    out = []
    for _ in range(4):
        ev, prev = events(lua, p, prev)
        out += changed(ev)
        g._clock["ms"] += 600
    assert out == [{"event": "item_changed", "gameMin": 450, "itemId": 90, "use": "water", "fluid": "Water",
                    "amount": 0.25}]


def test_a_failed_or_superseded_fill_marks_its_item_too_and_an_unchanged_item_says_nothing(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    water_world(lua, sink())
    p = make_player()
    fc = bottle(p)
    prev = seen(lua, p)
    start(lua, p, "fill", aid="f1", itemId=90, x=11, y=20)
    tick(lua, p)
    fc.st["amount"] = 0.4                                       # part filled, then the fill superseded
    start(lua, p, "stop", aid="s")
    assert lua.eval("PZA.sense.recheckIds[90]") is not None
    ev, prev = events(lua, p, prev)
    assert [(e["use"], e["amount"]) for e in changed(ev)] == [("water", 0.4)]
    p2 = make_player()
    tend_item(p2, "Base.Plank", 91)
    lua.eval("PZA.sense.firstSight(...)", p2)
    lua.eval("PZA.sense.recheck(91, nil)")
    ev, _ = events(lua, p2, frame(lua, p2))
    assert changed(ev) == [] and lua.eval("PZA.sense.recheckIds[91]") is None   # no fluid: one use read, done


def test_a_marked_item_gone_is_dropped_and_its_item_removed_says_so(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    fc = bottle(p, amount=0.5)
    prev = seen(lua, p)
    lua.eval("PZA.sense.recheck(90, 0.5)")
    p.held[:] = [it for it in p.held if it.getID(it) != 90]
    ev, _ = events(lua, p, prev)
    assert changed(ev) == [] and [e["event"] for e in ev if e["itemId"] == 90] == ["item_removed"]
    assert lua.eval("PZA.sense.recheckIds[90]") is None


def test_the_item_changed_event_is_the_schemas_and_decodes_through_pza1(lua, fs):
    load(lua)
    kinds = lua.eval("PZA.schema.events")
    assert list(kinds["item_changed"].values()) == ["itemId", "use", "fluid", "amount", "worn", "rip"]   # 1.5.2
    assert pza1.EVENT_KINDS[-1] == "item_changed" and pza1.EVENT_FIELDS["item_changed"] == ("itemId", "use", "fluid",
                                                                                            "amount", "worn", "rip")
    lua.execute("PZA.link.init('admin')")
    lua.execute("PZA.emit('event', { event = 'item_changed', gameMin = 451, itemId = 90, use = 'water',"
                " fluid = 'Water', amount = 1.0 })")
    lua.execute("PZA.emit('event', { event = 'item_changed', gameMin = 452, itemId = 90, use = 'container',"
                " amount = 0 })")
    lua.execute("PZA.link.flush()")
    got = [pza1.decode(json.loads(l)) for l in fs.files[LIVE].split("\n") if l.strip()]
    got = [o for o in got if o.get("kind") == "event"]
    assert [(o["event"], o["itemId"], o["use"], o.get("fluid"), o["amount"]) for o in got] == [
        ("item_changed", 90, "water", "Water", 1.0), ("item_changed", 90, "container", None, 0)]
    assert "in bag" in pza1.REASONS


def test_a_bandage_consumes_its_item_so_the_diff_says_item_removed_and_no_item_changed(lua, fs):
    """A bandage needs no mark: its item leaves the inventory, which the diff reports as item_removed."""
    from .test_lua_tend import apply_bandage, make_part, with_parts
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    parts = with_parts(p, [make_part(0, bleeding=True, bleeding_time=3.0)])
    rag = tend_item(p, "Base.RippedSheets", 50, isCanBandage=True)
    prev = seen(lua, p)
    start(lua, p, "bandage", itemId=50)
    tick(lua, p)
    apply_bandage(lua, p, parts[0], rag)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")
    ev, _ = events(lua, p, prev)
    assert [(e["event"], e["itemId"]) for e in ev if e["event"].startswith("item_")] == [("item_removed", 50)]


# ---- PZA/1.5.2 (Task 9 fix 4, review-t10 minor 7): the inventory record's worn and rip class ------------------------

def garment(p, ft, iid, worn=False, tags=()):
    """A garment answering isWorn `worn` and hasTag(t) for t in `tags` (the ItemTag constants' names, as the fake
    ItemTag carries them)."""
    return tend_item(p, ft, iid, isWorn=worn, hasTag=lambda t: t in tags)


def test_the_first_sight_carries_worn_and_the_rip_class_and_elides_them_when_false_or_absent(lua, fs):
    """A worn shirt reads worn and cotton, an unworn denim jacket denim and not worn, a leather one leather, a plank
    neither; the inventory's entry carries both, as the item_added line does."""
    load(lua)
    p = make_player()
    garment(p, "Base.Tshirt_DefaultTEXTURE", 70, worn=True, tags=("RIP_CLOTHING_COTTON",))
    garment(p, "Base.Jacket_Denim", 71, tags=("RIP_CLOTHING_DENIM",))
    garment(p, "Base.Jacket_Leather", 72, tags=("RIP_CLOTHING_LEATHER",))
    tend_item(p, "Base.Plank", 73)
    ev = {e["itemId"]: dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values() if e["itemId"] >= 70}
    assert ev[70]["worn"] is True and ev[70]["rip"] == "cotton"
    assert "worn" not in ev[71] and ev[71]["rip"] == "denim"
    assert "worn" not in ev[72] and ev[72]["rip"] == "leather"
    assert "worn" not in ev[73] and "rip" not in ev[73]
    assert lua.eval("PZA.sense.lastInv[70].worn") is True and lua.eval("PZA.sense.lastInv[70].rip") == "cotton"
    assert lua.eval("PZA.sense.lastInv[73].rip") is None


def test_a_later_item_added_carries_them_too_and_without_item_tag_no_rip_is_read(lua, fs):
    load(lua)
    p = make_player()
    prev = seen(lua, p)
    garment(p, "Base.Tshirt_DefaultTEXTURE", 70, tags=("RIP_CLOTHING_COTTON",))
    ev, prev = events(lua, p, prev)
    added = [dict(e) for e in ev if e["event"] == "item_added"]
    assert [(e["itemId"], e.get("worn"), e.get("rip")) for e in added] == [(70, None, "cotton")]
    lua.globals().ItemTag = None
    garment(p, "Base.Tshirt_DefaultTEXTURE", 74, worn=True, tags=("RIP_CLOTHING_COTTON",))
    ev, _ = events(lua, p, prev)
    added = [dict(e) for e in ev if e["event"] == "item_added"]
    assert [(e["itemId"], e.get("worn"), e.get("rip")) for e in added] == [(74, True, None)]


def test_an_item_changed_carries_the_items_worn_read_again(lua, fs):
    """A canteen worn on the belt, filled: its item_changed carries worn, read again with its use."""
    load(lua)
    lua.execute("PZA.link.init('admin')")
    water_world(lua, sink())
    p = make_player()
    fc = make_fluid(amount=0.0, capacity=1.0)
    tend_item(p, "Base.Canteen", 90, getFluidContainer=fc, isWorn=True)
    prev = seen(lua, p)
    start(lua, p, "fill", itemId=90, x=11, y=20)
    tick(lua, p)
    fc.st["amount"] = 1.0
    tick(lua, p)
    ev, _ = events(lua, p, prev)
    assert changed(ev) == [{"event": "item_changed", "gameMin": 450, "itemId": 90, "use": "water", "fluid": "Water",
                            "amount": 1.0, "worn": True}]
    assert lua.eval("PZA.sense.lastInv[90].worn") is True


def test_worn_and_rip_are_the_schemas_and_an_old_line_decodes_without_them(lua, fs):
    load(lua)
    assert pza1.EVENT_FIELDS["item_added"][-2:] == ("worn", "rip")
    assert pza1.EVENT_FIELDS["item_changed"][-2:] == ("worn", "rip")
    assert lua.eval("PZA.VERSION") == "1.5.6"
    lua.execute("PZA.link.init('admin')")
    lua.execute("PZA.emit('event', { event = 'item_added', gameMin = 451, itemId = 70,"
                " fullType = 'Base.Tshirt_DefaultTEXTURE', weight = 0.1, use = 'other', worn = true, rip = 'cotton' })")
    lua.execute("PZA.link.flush()")
    got = [pza1.decode(json.loads(l)) for l in fs.files[LIVE].split("\n") if l.strip()]
    got = [o for o in got if o.get("kind") == "event"]
    assert [(o["itemId"], o["worn"], o["rip"]) for o in got] == [(70, True, "cotton")]
    old = pza1.decode({"kind": "event", "seq": 1, "tick": 1, "wallMs": 1, "event": "item_added", "gameMin": 1,
                       "itemId": 3, "fullType": "Base.Plank", "weight": 1.0, "use": "other"})
    assert old.get("worn") is None and old.get("rip") is None
