"""PZA/1.7 (Plan 24 Task 9 fix 11) on the lupa host: the frame's body.armPain and body.strain and me.loadedWidth (jar-reads-2
sections 11 and 13), and the actions unwear (section 14, vanilla's ISUnequipAction), shove and stomp (section 12, the shove
key's pair setDoShove then DoAttack). The fake vanilla queue never runs an action: a test moves the world as the engine
would."""
import json

import pytest

from agent.base import pza1
from .conftest import J, make_cell, make_player, make_weapon, make_zombie
from .test_lua_clothing import garment, hold
from .test_lua_sense import frame, load, missing
from .test_lua_skills import acts, mover, sense, start, states, tick

ARMS = ("Hand_L", "ForeArm_L", "UpperArm_L", "Hand_R", "ForeArm_R", "UpperArm_R")


def fz(zid, x, y, floor=False, health=1.0, dead=False):
    """A zombie whose isOnFloor, getHealth and isDead read .st."""
    st = {"floor": floor, "health": health, "dead": dead}
    z = make_zombie(zid, x, y)
    z.isOnFloor, z.getHealth, z.isDead = (lambda s: st["floor"]), (lambda s: st["health"]), (lambda s: st["dead"])
    z.st = st
    return z


# ---- the frame: body.armPain, body.strain ---------------------------------------------------------------------------

def arm_player(lua, pain=None, stiff=None, **missing_members):
    """A player whose BodyDamage.getBodyPart(BodyPartType.X) answers an arm part with getPain and getStiffness from the
    dicts (default 0), and the global BodyPartType naming the arm parts; a member named in missing_members is dropped."""
    pain, stiff = pain or {}, stiff or {}
    p = make_player()
    parts = {}
    for n in ARMS:
        part = J(getPain=lambda s, n=n: pain.get(n, 0.0), getStiffness=lambda s, n=n: stiff.get(n, 0.0))
        for m in missing_members:
            setattr(part, m, None)
        parts[n] = part
    p.getBodyDamage(p).getBodyPart = lambda s, t: parts[t]
    lua.globals().BodyPartType = J(**{n: n for n in ARMS})
    return p, parts


def test_the_body_carries_the_summed_arm_pain_and_each_arms_largest_strain(lua):
    load(lua)
    p, _ = arm_player(lua, pain={"Hand_L": 1.5, "UpperArm_R": 12.0, "ForeArm_R": 0.25},
                      stiff={"Hand_L": 1.0, "ForeArm_L": 2.5, "UpperArm_L": 0.5, "ForeArm_R": 7.126})
    b = frame(lua, p)["body"]
    assert b["armPain"] == 13.75
    assert (b["strain"]["l"], b["strain"]["r"]) == (2.5, 7.13)           # the largest of three parts, rounded to 0.01


def test_a_rested_arm_reads_zero_and_the_six_parts_are_fetched_once(lua):
    load(lua)
    p, _ = arm_player(lua)
    calls = []
    inner = p.getBodyDamage(p).getBodyPart
    p.getBodyDamage(p).getBodyPart = lambda s, t: calls.append(t) or inner(s, t)
    for _ in range(3):
        b = frame(lua, p)["body"]
    assert b["armPain"] == 0 and (b["strain"]["l"], b["strain"]["r"]) == (0, 0)
    assert calls == list(ARMS)                                             # one fetch of each, then cached


def test_the_arm_fields_follow_the_parts_as_the_stiffness_decays(lua):
    load(lua)
    p, parts = arm_player(lua, stiff={"Hand_R": 4.0})
    state = {"v": 4.0}
    parts["Hand_R"].getStiffness = lambda s: state["v"]
    assert frame(lua, p)["body"]["strain"]["r"] == 4.0
    state["v"] = 3.9
    assert frame(lua, p)["body"]["strain"]["r"] == 3.9


def test_an_unchanged_arm_leaves_the_body_group_elided_and_a_change_sends_it(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    p, parts = arm_player(lua, stiff={"Hand_R": 4.0})
    state = {"v": 4.0}
    parts["Hand_R"].getStiffness = lambda s: state["v"]

    def emit():
        f = frame(lua, p)
        f.cost = lua.table_from({})
        lua.eval("PZA.emitFrame")(f)
    emit()
    emit()
    state["v"] = 3.5
    emit()
    lua.execute("PZA.link.flush()")
    out = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].split("\n") if l.startswith('["frame"')]
    body = [arr[8] for arr in out]
    assert body[0][5:] == [0, [0, 4.0]] and body[1] is True and body[2][5:] == [0, [0, 3.5]]
    d = pza1.decode(out[0])
    assert d["body"]["armPain"] == 0 and d["body"]["strain"] == {"l": 0, "r": 4.0}


def test_absent_arm_members_leave_the_fields_null_and_are_named_missing(lua):
    load(lua)
    p, _ = arm_player(lua, getStiffness=None)
    b = frame(lua, p)["body"]
    assert b["armPain"] == 0 and b["strain"] is None and "getStiffness" in missing(lua)
    load(lua)
    p, _ = arm_player(lua, getPain=None)
    b = frame(lua, p)["body"]
    assert b["armPain"] is None and b["strain"] is not None and "getPain" in missing(lua)
    load(lua)
    p = make_player()
    lua.globals().BodyPartType = None
    b = frame(lua, p)["body"]
    assert b["armPain"] is None and b["strain"] is None and "BodyPartType.Hand_L" in missing(lua)
    load(lua)
    p, _ = arm_player(lua)
    p.getBodyDamage(p).getBodyPart = None
    b = frame(lua, p)["body"]
    assert b["armPain"] is None and "getBodyPart" in missing(lua)


def test_a_raising_arm_read_costs_the_two_fields_alone(lua):
    load(lua)
    p, parts = arm_player(lua)
    parts["Hand_L"].getPain = lambda s: 1 / 0
    f = frame(lua, p)
    assert f["body"]["armPain"] is None and f["body"]["health"] == 100.0
    assert "raise:body:arms" in missing(lua) and lua.eval("PZA.sense.frameErrors") == 1


# ---- the frame: me.loadedWidth ----------------------------------------------------------------------------------------

def width_cell(lua, state):
    cell = make_cell()
    cell.getChunkMap = lambda s, i: J(getWidthInTiles=lambda s2: state["w"]) if i == 0 else None
    lua.globals()._cell = cell


def test_the_loaded_width_is_carried_on_the_first_frame_and_when_it_changes(lua):
    load(lua)
    state = {"w": 104}
    width_cell(lua, state)
    p = make_player()
    assert frame(lua, p)["me"]["loadedWidth"] == 104
    seen = [frame(lua, p)["me"]["loadedWidth"] for _ in range(99)]
    assert seen == [None] * 99                                             # unchanged: elided
    state["w"] = 152
    got = [frame(lua, p)["me"]["loadedWidth"] for _ in range(100)]
    assert [w for w in got if w is not None] == [152]                      # re-read within one WIDTH_EVERY
    assert [frame(lua, p)["me"]["loadedWidth"] for _ in range(5)] == [None] * 5


def test_an_absent_chunk_map_member_leaves_the_width_null_and_named(lua):
    load(lua)
    cell = make_cell()
    cell.getChunkMap = None
    lua.globals()._cell = cell
    f = frame(lua, make_player())
    assert f["me"]["loadedWidth"] is None and "getChunkMap" in missing(lua)
    load(lua)
    cell = make_cell()
    cell.getChunkMap = lambda s, i: J()
    lua.globals()._cell = cell
    assert frame(lua, make_player())["me"]["loadedWidth"] is None and "getWidthInTiles" in missing(lua)


def test_the_width_encodes_through_the_link_and_old_logs_decode_without_the_new_fields(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    width_cell(lua, {"w": 104})
    p, _ = arm_player(lua, stiff={"Hand_R": 2.0})
    f = frame(lua, p)
    f.cost = lua.table_from({})
    lua.eval("PZA.emitFrame")(f)
    lua.execute("PZA.link.flush()")
    line = [l for l in fs.files["pzagent/admin/state.log"].split("\n") if l.startswith('["frame"')][0]
    d = pza1.decode(json.loads(line))
    assert d["me"]["loadedWidth"] == 104 and d["body"]["strain"] == {"l": 0, "r": 2.0}
    old = json.loads(line)
    old[6], old[8] = old[6][:20], old[8][:5]                               # a PZA/1.6.1 writer's arities
    d = pza1.decode(old)
    assert d["me"]["loadedWidth"] is None and d["body"]["armPain"] is None and d["body"]["strain"] is None


# ---- unwear {itemId} ------------------------------------------------------------------------------------------------

def unwear_host(lua, loc="base:shirt", equipped=False, moving=False, walk_locs=("base:hat",), fresh=True):
    """A player wearing a garment (90) at loc, held in the main inventory; ISUnequipAction:new records into g._unequips;
    ISWearClothing.WalkBodyLocations lists walk_locs; the worn list's contains and the inventory's contains read the
    lists. A second host in one test passes fresh=False: the same Lua state and act file."""
    if fresh:
        load(lua)
        lua.execute("PZA.link.init('admin')")
    g = lua.globals()
    unequips = []
    g._unequips = unequips
    g.ISUnequipAction = J(new=lambda cls, p, item, t=None: unequips.append((p, item, t)) or J(
        Type="ISUnequipAction", item=item))
    g.ISWearClothing = J(WalkBodyLocations=lua.table_from(list(walk_locs)))
    p = make_player()
    it = hold(p, garment(90, loc=loc, worn=True))
    it.isEquipped = lambda s: equipped
    p.worn.append((loc, it))
    wl = p.worn
    p.getWornItems = lambda s: J(size=lambda s2: len(wl), contains=lambda s2, x: any(i is x for _, i in wl),
                                 get=lambda s2, i: J(getLocation=lambda s3: wl[i][0], getItem=lambda s3: wl[i][1]))
    p.getInventory(p).contains = lambda s, x: any(i is x for i in p.held)
    p.isPlayerMoving = lambda s: moving
    return p, it


def take_off(p, it):
    """The server's complete: the location empties, the garment stays in the inventory."""
    it.st["worn"] = False
    p.worn[:] = [(l, i) for l, i in p.worn if i is not it]


def test_unwear_queues_iso_unequip_action_and_is_done_once_the_garment_reads_unworn(lua, fs):
    p, it = unwear_host(lua)
    g = lua.globals()
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    assert g._unequips == [(p, it, 50)] and g._queue.adds[-1].Type == "ISUnequipAction"
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "accepted", "")
    take_off(p, it)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"itemId": 90, "loc": "base:shirt"}


def test_unwear_refusals(lua, fs):
    p, it = unwear_host(lua)
    other = hold(p, garment(91, loc="base:jacket"))                          # held, not worn
    start(lua, p, "unwear", aid="nh", itemId=999)
    start(lua, p, "unwear", aid="ba", itemId="x")
    start(lua, p, "unwear", aid="nw", itemId=91)
    it.isEquipped = lambda s: True
    start(lua, p, "unwear", aid="he", itemId=90)
    it.isEquipped = lambda s: False
    p.isPlayerMoving = lambda s: True
    start(lua, p, "unwear", aid="mo", itemId=90)
    assert states(acts(lua, fs)) == [("nh", "rejected", "none held"), ("ba", "rejected", "bad args"),
                                     ("nw", "rejected", "not worn"), ("he", "rejected", "held"),
                                     ("mo", "rejected", "moving")]
    assert other.st["worn"] is False and lua.globals()._unequips == []


def test_a_walk_location_garment_is_taken_off_beside_a_walk_and_an_absent_list_refuses(lua, fs):
    p, it = unwear_host(lua, loc="base:hat", moving=True)
    start(lua, p, "unwear", itemId=90)
    assert states(acts(lua, fs)) == [("a1", "accepted", "")]
    p, it = unwear_host(lua, loc="base:hat", moving=True, fresh=False)
    lua.globals().ISWearClothing = J()                                       # no WalkBodyLocations: fail-closed
    start(lua, p, "unwear", aid="a2", itemId=90)
    assert states(acts(lua, fs))[-1] == ("a2", "rejected", "moving")


def test_unwear_whose_action_left_the_queue_with_the_garment_worn_is_stopped_after_the_settle(lua, fs):
    p, it = unwear_host(lua)
    g = lua.globals()
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    g._queue.queue[:] = []                                                   # a run stopped the action
    tick(lua, p)
    g._clock["ms"] += 1999
    tick(lua, p)
    assert lua.eval("PZA.skills.cur") is not None
    g._clock["ms"] += 1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "stopped")


def test_unwear_dropped_when_the_garment_left_the_inventory(lua, fs):
    p, it = unwear_host(lua)
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    take_off(p, it)
    p.held.remove(it)                                                        # no room: setWornItem put it on the floor
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "dropped")


def test_unwear_still_worn_within_its_budget_is_interrupted(lua, fs):
    p, it = unwear_host(lua)
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    lua.globals()._clock["ms"] += 10001
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")


def test_unwear_without_the_action_class_or_the_worn_list_fails_not_loaded(lua, fs):
    p, it = unwear_host(lua)
    lua.globals().ISUnequipAction = None
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")
    p, it = unwear_host(lua, fresh=False)
    p.getWornItems = None
    start(lua, p, "unwear", aid="a2", itemId=90)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a2", "failed", "not loaded")


def test_unwear_marks_the_garment_for_the_next_worn_read_and_an_item_changed(lua, fs):
    p, it = unwear_host(lua)
    start(lua, p, "unwear", itemId=90)
    tick(lua, p)
    lua.execute("PZA.sense.wornDirty = false")
    take_off(p, it)
    tick(lua, p)
    assert lua.eval("PZA.sense.wornDirty") is True and lua.eval("PZA.sense.recheckIds[90]") is not None


@pytest.mark.parametrize("typ", ["unwear"])
def test_the_new_types_are_in_hello_caps_and_the_schema(lua, typ):
    load(lua)
    assert typ in list(lua.eval("PZA.skills.types").keys())
    assert typ in pza1.ACTION_TYPES and typ in lua.eval("PZA.schema.actions").keys()


# ---- zombie.onFloor ---------------------------------------------------------------------------------------------------

def test_a_zombie_on_the_floor_carries_on_floor_true_and_a_standing_one_none(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[fz(1, 12.0, 20.0, floor=True), fz(2, 13.0, 20.0), fz(3, 14.0, 20.0)])
    zs = {z["id"]: dict(z) for z in frame(lua, make_player())["zombies"].values()}
    assert zs[1]["onFloor"] is True and "onFloor" not in zs[2] and "onFloor" not in zs[3]


def test_the_fallen_zombie_follows_its_state_from_frame_to_frame(lua):
    load(lua)
    z = fz(1, 12.0, 20.0)
    lua.globals()._cell = make_cell(zombies=[z])
    p = make_player()
    assert frame(lua, p)["zombies"][1]["onFloor"] is None
    z.st["floor"] = True                                                     # a shove knocked it down
    assert frame(lua, p)["zombies"][1]["onFloor"] is True
    z.st["floor"] = False                                                    # it got up
    assert frame(lua, p)["zombies"][1]["onFloor"] is None


def test_an_absent_is_on_floor_member_leaves_the_field_none_and_is_named_missing(lua):
    load(lua)
    z = fz(1, 12.0, 20.0, floor=True)
    z.isOnFloor = None
    lua.globals()._cell = make_cell(zombies=[z])
    f = frame(lua, make_player())
    assert f["zombies"][1]["onFloor"] is None and "isOnFloor" in missing(lua)


def test_on_floor_encodes_through_the_link_and_an_old_zombie_record_decodes_without_it(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    lua.globals()._cell = make_cell(zombies=[fz(1, 12.0, 20.0, floor=True), fz(2, 13.0, 20.0)])
    f = frame(lua, make_player())
    f.cost = lua.table_from({})
    lua.eval("PZA.emitFrame")(f)
    lua.execute("PZA.link.flush()")
    line = [l for l in fs.files["pzagent/admin/state.log"].split("\n") if l.startswith('["frame"')][0]
    arr = json.loads(line)
    d = pza1.decode(arr)
    assert [z["onFloor"] for z in d["zombies"]] == [True, None]
    old = json.loads(line)
    old[-2] = [r[:7] for r in old[-2]]                                       # a PZA/1.6.1 writer's seven fields
    assert [z["onFloor"] for z in pza1.decode(old)["zombies"]] == [None, None]
