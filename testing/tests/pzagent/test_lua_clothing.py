"""PZA/1.6 (Plan 24 Task 9 fix 9, review-t18 ruling 5): the clothing on the lupa host. The item use `clothing` (an item
whose class is Clothing, W.useOf) with its `clothing` record {loc, bite, scratch, bullet, cond, condMax, holes, worn} on
item_added and item_changed; the loot filter `clothing`; me.worn, the worn locations with their summed bite and scratch
defence, elided while unchanged; the portal's `locked` read fail-closed and the door event's `locked`; and the `wear`
skill (vanilla's ISWearClothing), whose end marks the garment and the one it replaced for an item_changed. The jar reads
are docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md section 10."""
import json

from agent.base import pza1
from .conftest import J, make_cell, make_player
from .test_lua_item_changed import changed, seen
from .test_lua_sense import events, frame, load, load_map, missing, watch_cycle
from .test_lua_skills import acts, box_world, citem, start, states, tick
from .test_lua_tend import tend_item


def garment(iid=None, loc="base:jacket", bite=15.0, scratch=30.0, bullet=0.0, cond=8, cond_max=10, holes=0,
            worn=False, ft="Base.Jacket_Padded"):
    """A Clothing item (an inventory item when iid is given, else a container's): its defences, condition and holes
    answer the arguments, isWorn reads st["worn"] (st on .st)."""
    st = {"worn": worn, "cond": cond, "holes": holes}
    it = J(_cls="Clothing", getFullType=lambda s: ft, getWeight=lambda s: 1.0, IsFood=lambda s: False,
           getFluidContainer=lambda s: None, getHungerChange=lambda s: 0.0, getBodyLocation=lambda s: loc,
           getBiteDefense=lambda s: bite if st["cond"] > 0 else 0.0,
           getScratchDefense=lambda s: scratch if st["cond"] > 0 else 0.0,
           getBulletDefense=lambda s: bullet, getCondition=lambda s: st["cond"],
           getConditionMax=lambda s: cond_max, getHolesNumber=lambda s: st["holes"], isWorn=lambda s: st["worn"])
    if iid is not None:
        it.getID = lambda s: iid
    it.st = st
    return it


def hold(p, it):
    it.getContainer = lambda s: p.getInventory(p)
    p.held.append(it)
    return it


def item_events(ev, kind="item_added"):
    return [e for e in ev if e["event"] == kind]


# ---- the clothing use and its record ---------------------------------------------------------------------------------

def test_a_garment_reads_use_clothing_with_its_record_worn_and_unworn(lua):
    load(lua)
    p = make_player()
    hold(p, garment(70, worn=True, loc="base:tshirt", bite=0.0, scratch=10.0, cond=5, cond_max=5, holes=1,
                    ft="Base.Tshirt_DefaultTEXTURE"))
    hold(p, garment(71))
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    by = {e["itemId"]: e for e in ev}
    assert by[70]["use"] == "clothing" and by[70].get("worn") is True
    assert dict(by[70]["clothing"]) == {"loc": "base:tshirt", "bite": 0, "scratch": 10, "bullet": 0, "cond": 5,
                                         "condMax": 5, "holes": 1, "worn": True}
    assert by[71]["use"] == "clothing" and "worn" not in by[71]
    assert dict(by[71]["clothing"]) == {"loc": "base:jacket", "bite": 15, "scratch": 30, "bullet": 0, "cond": 8,
                                         "condMax": 10, "holes": 0, "worn": False}


def test_a_non_clothing_item_carries_no_clothing_record(lua):
    load(lua)
    p = make_player(items=("Base.Hammer", "Base.Tshirt_DefaultTEXTURE"))   # make_item: no class, so not Clothing
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    assert [e["use"] for e in ev] == ["other", "other"] and all("clothing" not in e for e in ev)


def test_a_garment_at_condition_0_reads_its_defences_0(lua):
    load(lua)
    p = make_player()
    hold(p, garment(70, cond=0))
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    c = dict(ev[0]["clothing"])
    assert (c["bite"], c["scratch"], c["cond"]) == (0, 0, 0)


def test_an_absent_member_leaves_its_field_out_and_the_record_still_goes(lua):
    load(lua)
    p = make_player()
    it = hold(p, garment(70))
    it.getHolesNumber, it.getBodyLocation = None, None
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    c = dict(ev[0]["clothing"])
    assert "holes" not in c and "loc" not in c and c["bite"] == 15


def test_the_item_added_line_encodes_and_decodes_with_its_clothing(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    hold(p, garment(70))
    for e in lua.eval("PZA.sense.firstSight(...)", p).values():
        lua.eval("PZA.emit")("event", e)
    lua.execute("PZA.link.flush()")
    line = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].split("\n") if l.strip()][-1]
    d = pza1.decode(line)
    assert d["event"] == "item_added" and d["use"] == "clothing" and d["clothing"]["loc"] == "base:jacket"


# ---- the loot filter -------------------------------------------------------------------------------------------------

def test_the_clothing_filter_takes_a_garment_and_not_a_weapon(lua, fs):
    load(lua)
    g = lua.globals()
    jacket, axe = garment(), citem("Base.Axe", "HandWeapon")
    box_world(lua, [jacket, axe, citem("Base.Bread", "Food")])
    start(lua, make_player(), "interact", x=11, y=20, kind="loot", filter="clothing")
    tick(lua, make_player())
    adds = g._queue.adds
    assert [a.Type for a in adds] == ["ISInventoryTransferAction"] and adds[0].item is jacket
    assert lua.eval("PZA.schema.filters.clothing") is True and "clothing" in pza1.FILTERS


def test_the_clothing_filter_with_no_garment_is_no_match(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    box_world(lua, [citem("Base.Axe", "HandWeapon")])
    p = make_player()
    start(lua, p, "interact", x=11, y=20, kind="loot", filter="clothing")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "no match")


# ---- me.worn ---------------------------------------------------------------------------------------------------------

def worn_player():
    shirt = garment(70, loc="base:tshirt", bite=0.0, scratch=10.0, worn=True)
    jacket = garment(71, loc="base:jacket", bite=15.0, scratch=30.0, worn=True)
    ring = garment(72, loc="base:right_ringfinger", bite=0.0, scratch=0.0, worn=True)
    ring2 = garment(73, loc="base:right_ringfinger", bite=1.0, scratch=2.0, worn=True)
    bag = J(_cls="InventoryContainer", getFullType=lambda s: "Base.Bag_Schoolbag")
    return make_player(worn=[("base:tshirt", shirt), ("base:back", bag), ("base:jacket", jacket),
                             ("base:right_ringfinger", ring), ("base:right_ringfinger", ring2)]), jacket


def worn_of(f):
    w = f["me"]["worn"]
    return None if w is None else [dict(r) for r in w.values()]


def test_the_first_frame_carries_the_worn_locations_summed_a_bag_left_out(lua):
    load(lua)
    p, _ = worn_player()
    assert worn_of(frame(lua, p)) == [{"loc": "base:tshirt", "bite": 0, "scratch": 10},
                                      {"loc": "base:jacket", "bite": 15, "scratch": 30},
                                      {"loc": "base:right_ringfinger", "bite": 1, "scratch": 2}]


def test_me_worn_is_elided_while_unchanged_and_sent_again_when_it_changes(lua):
    load(lua)
    p, jacket = worn_player()
    assert worn_of(frame(lua, p)) is not None
    for _ in range(25):
        assert worn_of(frame(lua, p)) is None                    # unchanged: elided, read every WORN_EVERY frames
    jacket.st["cond"] = 0                                        # a garment at condition 0 defends nothing
    sent = [worn_of(frame(lua, p)) for _ in range(10)]           # read again within one WORN_EVERY
    got = [w for w in sent if w is not None]
    assert len(got) == 1 and got[0][1] == {"loc": "base:jacket", "bite": 0, "scratch": 0}


def test_an_item_or_damage_event_reads_the_worn_list_on_the_next_frame(lua):
    load(lua)
    p, _ = worn_player()
    prev = seen(lua, p)
    g = lua.globals()
    g.getPlayer = lambda: p                                      # the damage hook keeps the local player's records
    frame(lua, p)                                                # the read count past the first
    del p.worn[2]                                                # the jacket off, and it leaves the inventory
    g._damageHandlers[0](p, "ZOMBIE", 1.0)                       # a damage event prompts the read
    ev, cur = events(lua, p, prev)
    assert [e["event"] for e in ev] == ["damage"] and lua.eval("PZA.sense.wornDirty") is True
    f = frame(lua, p)
    assert [r["loc"] for r in worn_of(f)] == ["base:tshirt", "base:right_ringfinger"]


def test_nothing_worn_is_an_empty_list_and_no_worn_items_member_is_nil_and_missing(lua):
    load(lua)
    f = frame(lua, make_player())
    assert worn_of(f) == [] and missing(lua) == []
    p = make_player()
    p.getWornItems = None
    load(lua)
    f = frame(lua, p)
    assert f["me"]["worn"] is None and "getWornItems" in missing(lua)


def test_the_worn_list_encodes_through_the_link_and_decodes_through_pza1(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p, _ = worn_player()
    f = frame(lua, p)
    f.cost = lua.table_from({})
    lua.eval("PZA.emitFrame")(f)
    lua.execute("PZA.link.flush()")
    line = [l for l in fs.files["pzagent/admin/state.log"].split("\n") if l.startswith('["frame"')][0]
    d = pza1.decode(json.loads(line))
    assert d["me"]["worn"][1] == {"loc": "base:jacket", "bite": 15, "scratch": 30}


# ---- the portal's locked, fail-closed, and the door event's locked ---------------------------------------------------

def portal_square(st, x, y, cls="IsoDoor", **locks):
    door = J(_cls=cls, IsOpen=lambda s: st["open"], isBarricaded=lambda s: False)
    for k, v in locks.items():
        setattr(door, k, (lambda val: lambda s: val)(v))
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0,
             getObjects=lambda s: J(size=lambda s2: 1, get=lambda s2, i: door))


def scan_portal(lua, sq, kind="door"):
    """The scanned square's portal locked, and whether isLocked was named missing."""
    lua.globals()._cell = make_cell(squares={(11, 20, 0): sq})
    s = lua.eval("PZA.map.scan(...)", make_player(x=11.5, y=20.5), 0)
    q = [q for q in s["squares"].values() if q["x"] == 11][0]
    return q[kind]["locked"], "isLocked" in list(s["missing"].values())


def test_the_locked_read_is_any_lock_member_and_fail_closed_when_none_reads(lua):
    load(lua)
    load_map(lua)
    st = {"open": False}
    assert scan_portal(lua, portal_square(st, 11, 20, isLocked=False, isLockedByKey=False)) == (False, False)
    assert scan_portal(lua, portal_square(st, 11, 20, isLocked=False, isLockedByKey=True))[0] is True
    assert scan_portal(lua, portal_square(st, 11, 20, isLocked=True))[0] is True
    thump = portal_square(st, 11, 20, "IsoThumpable", isLocked=False, isLockedByPadlock=True)
    thump.getObjects(thump).get(None, 0).isDoor = lambda s: True
    assert scan_portal(lua, thump)[0] is True
    assert scan_portal(lua, portal_square(st, 11, 20)) == (True, True)          # none readable: locked, named
    win = portal_square(st, 11, 20, "IsoWindow", isLocked=False, isPermaLocked=True)
    assert scan_portal(lua, win, "window")[0] is True
    win = portal_square(st, 11, 20, "IsoWindow", isLocked=False, isPermaLocked=False)
    assert scan_portal(lua, win, "window")[0] is False


def test_the_door_event_carries_the_records_locked(lua):
    load(lua)
    load_map(lua)
    st = {"open": False}
    lua.globals()._cell = make_cell(squares={(12, 20, 0): portal_square(st, 12, 20, isLocked=True)})
    p = make_player()
    prev = frame(lua, p)
    watch_cycle(lua, p)
    ev, prev = events(lua, p, prev)
    st["open"] = True
    watch_cycle(lua, p)
    ev, _ = events(lua, p, prev)
    doors = [e for e in ev if e["event"] == "door"]
    assert doors == [{"event": "door", "gameMin": 450, "x": 12, "y": 20, "z": 0, "open": True, "locked": True}]


# ---- wear {itemId} ---------------------------------------------------------------------------------------------------

def wear_host(lua, worn=None):
    """A player holding a jacket (90, base:jacket, not worn) and, when `worn`, wearing an old jacket (91) at
    base:jacket; isWorn of the new one reads its st["worn"], which the test flips as the server's wear lands."""
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p = make_player()
    new = hold(p, garment(90))
    old = None
    if worn:
        old = hold(p, garment(91, bite=2.0, scratch=5.0, worn=True))
        p.worn.append(("base:jacket", old))
    return p, new, old


def test_wear_queues_iso_wear_clothing_and_is_done_once_the_garment_reads_worn(lua, fs):
    p, new, old = wear_host(lua, worn=True)
    g = lua.globals()
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    assert g._wears == [(p, new, 50)] and g._queue.adds[-1].Type == "ISWearClothing"
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "accepted", "")
    new.st["worn"], old.st["worn"] = True, False
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"itemId": 90, "loc": "base:jacket",
                                                                     "replaced": 91}


def test_wear_marks_the_garment_and_the_replaced_one_for_an_item_changed(lua, fs):
    p, new, old = wear_host(lua, worn=True)
    prev = seen(lua, p)
    for _ in range(3):
        prev = frame(lua, p)                                     # the worn list read and sent, then elided
    assert worn_of(prev) is None
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    new.st["worn"], old.st["worn"] = True, False                 # the server's wear lands
    p.worn[0] = ("base:jacket", new)
    tick(lua, p)
    ev, prev = events(lua, p, prev)
    assert worn_of(prev) == [{"loc": "base:jacket", "bite": 15, "scratch": 30}]   # the wear's end prompted the read
    ch = {e["itemId"]: e for e in changed(ev)}
    assert set(ch) == {90, 91}
    assert ch[90]["worn"] is True and dict(ch[90]["clothing"])["worn"] is True and ch[90]["use"] == "clothing"
    assert "worn" not in ch[91] and dict(ch[91]["clothing"])["worn"] is False
    assert lua.eval("PZA.sense.lastInv[90].worn") is True and lua.eval("PZA.sense.recheckIds[90]") is None
    ev, _ = events(lua, p, prev)
    assert changed(ev) == []


def test_wear_with_nothing_at_the_location_reports_no_replaced(lua, fs):
    p, new, _ = wear_host(lua)
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    new.st["worn"] = True
    tick(lua, p)
    a = acts(lua, fs)
    assert a[-1]["state"] == "done" and a[-1]["result"] == {"itemId": 90, "loc": "base:jacket"}


def test_wear_refusals(lua, fs):
    p, new, old = wear_host(lua, worn=True)
    tend_item(p, "Base.Axe", 92)
    start(lua, p, "wear", aid="nh", itemId=999)
    start(lua, p, "wear", aid="ba", itemId="x")
    start(lua, p, "wear", aid="nv", itemId=92)
    start(lua, p, "wear", aid="wo", itemId=91)
    new.getBodyLocation = None
    start(lua, p, "wear", aid="nl", itemId=90)
    new.getBodyLocation = lambda s: "base:jacket"
    p.combat["hitReaction"] = "HitReactionFront"
    start(lua, p, "wear", aid="bu", itemId=90)
    assert states(acts(lua, fs)) == [("nh", "rejected", "none held"), ("ba", "rejected", "bad args"),
                                     ("nv", "rejected", "not valid"), ("wo", "rejected", "worn"),
                                     ("nl", "rejected", "not valid"), ("bu", "rejected", "busy")]


def test_wear_moves_a_garment_in_a_bag_out_first_and_reports_moved(lua, fs):
    p, new, _ = wear_host(lua)
    bag = J(getType=lambda s: "Bag_Schoolbag")
    new.getContainer = lambda s: bag
    g = lua.globals()
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISInventoryTransferAction", "ISWearClothing"]
    assert g._queue.adds[0].src is bag
    new.st["worn"] = True
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"]["moved"] is True


def test_wear_not_worn_within_its_budget_is_interrupted_and_still_marks(lua, fs):
    p, new, _ = wear_host(lua)
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    lua.globals()._clock["ms"] += 15001
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")
    assert lua.eval("PZA.sense.recheckIds[90]") is not None


def test_wear_without_the_vanilla_class_fails_not_loaded(lua, fs):
    p, _, _ = wear_host(lua)
    lua.globals().ISWearClothing = None
    start(lua, p, "wear", itemId=90)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")


def test_wear_is_in_the_hello_caps_and_the_schema(lua):
    load(lua)
    assert lua.eval("PZA.skills.types.wear") is not None and "wear" in pza1.ACTION_TYPES
    assert pza1.Wear(itemId=5).args() == {"itemId": 5}
