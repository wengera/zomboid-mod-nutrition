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


# ---- shove {targetId} and stomp {targetId} --------------------------------------------------------------------------

def shove_host(lua, zombies, weapon=None, flag=True, fresh=True):
    """A player at (10, 20) holding `weapon`, the zombies listed (Sense's zombieById and zobj), setDoShove recording into
    p.shoves. A second host in one test passes fresh=False: the same Lua state and act file."""
    if fresh:
        load(lua)
        lua.execute("PZA.link.init('admin')")
        lua.globals().PZA.tick = 0
    sense(lua, zombies)
    lua.eval("PZA.sense").zobj = lua.table_from({z.getOnlineID(z): z for z in zombies})
    lua.globals()._cell = make_cell(zombies=zombies)
    p = make_player(weapon=weapon)
    p.shoves = []
    if flag:
        p.setDoShove = lambda s, v: p.shoves.append(v)
    return p


def swing(lua, p, started_ticks=1):
    """The engine's swing: attackStarted true for started_ticks ticks, then false."""
    for _ in range(started_ticks):
        p.attack["started"] = True
        tick(lua, p)
    p.attack["started"] = False


def test_shove_faces_the_target_sets_the_flag_presses_the_attack_and_reports_the_knockdown(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z], weapon=make_weapon())
    start(lua, p, "shove", targetId=7)
    tick(lua, p)
    assert p.shoves == [True] and list(p.attacks) == [0] and list(p.faced) == [z]
    swing(lua, p)
    tick(lua, p)                                                             # the swing ended: one frame more
    z.st["floor"] = True                                                     # the knock-down lands
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"knockdown": True, "attackStarted": True, "targetDead": False}
    assert p.shoves == [True, False] and list(p.attacks) == [0]


def test_a_shove_that_staggers_reports_no_knockdown(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z])
    start(lua, p, "shove", targetId=7)
    tick(lua, p)
    swing(lua, p, 2)
    tick(lua, p, 2)
    assert acts(lua, fs)[-1]["result"] == {"knockdown": False, "attackStarted": True, "targetDead": False}


def test_a_shove_the_engine_dropped_is_done_after_the_swing_budget_and_clears_the_flag(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z])
    start(lua, p, "shove", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1500
    tick(lua, p, 2)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"]["attackStarted"] is False
    assert p.shoves == [True, False]


def test_shove_refusals(lua, fs):
    near, far, dead = fz(7, 11.0, 20.0), fz(8, 12.0, 20.0), fz(9, 11.0, 20.0, dead=True)
    p = shove_host(lua, [near, far, dead])
    start(lua, p, "shove", aid="nt", targetId=99)
    start(lua, p, "shove", aid="de", targetId=9)
    start(lua, p, "shove", aid="ba", targetId="7")
    start(lua, p, "shove", aid="tf", targetId=8)
    p.combat["hitReaction"] = "HitReactionFront"
    start(lua, p, "shove", aid="bu", targetId=7)
    p.combat["hitReaction"] = ""
    p.attack["started"] = True
    start(lua, p, "shove", aid="sw", targetId=7)
    assert states(acts(lua, fs)) == [("nt", "rejected", "no target"), ("de", "rejected", "no target"),
                                     ("ba", "rejected", "bad args"), ("tf", "rejected", "too far"),
                                     ("bu", "rejected", "busy"), ("sw", "rejected", "busy")]
    assert p.shoves == [] and list(p.attacks) == []


def test_a_target_that_stepped_out_of_reach_before_the_first_tick_fails_too_far(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z])
    start(lua, p, "shove", targetId=7)
    z.getX = lambda s: 12.0
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "too far") and p.shoves == [] and list(p.attacks) == []


def test_a_player_without_the_shove_members_fails_not_loaded(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z], flag=False)
    start(lua, p, "shove", targetId=7)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded") and list(p.attacks) == []


def test_a_shove_superseded_mid_swing_leaves_the_flag_to_the_engines_exit(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z])
    start(lua, p, "shove", targetId=7)
    tick(lua, p)
    p.attack["started"] = True
    tick(lua, p)
    start(lua, p, "stop", aid="s")
    assert p.shoves == [True]                                                # the swing state's exit clears it
    p.attack["started"] = False
    start(lua, p, "shove", aid="s2", targetId=7)
    tick(lua, p)
    start(lua, p, "stop", aid="s3")
    assert p.shoves == [True, True, False]                                   # nothing running: cleared at once


def test_a_shove_under_a_held_stance_releases_it_like_any_skill_but_attack(lua, fs):
    z = fz(7, 11.0, 20.0)
    p = shove_host(lua, [z])
    lua.execute("PZA.skills.stance.held = true")
    start(lua, p, "shove", targetId=7)
    assert lua.eval("PZA.skills.stance.held") is False


def stomp_host(lua, zombies, weapon=None, x=10.0, fresh=True):
    p = shove_host(lua, zombies, weapon=weapon, fresh=fresh)
    pos = mover(p, x, 20.0)
    return p, pos


def test_stomp_walks_to_under_half_a_tile_then_presses_the_shove_pair_and_reports_the_hit(lua, fs):
    z = fz(7, 10.8, 20.0, floor=True, health=0.8)
    p, pos = stomp_host(lua, [z], weapon=make_weapon())
    start(lua, p, "stomp", targetId=7)
    tick(lua, p)
    assert ("setAutoWalk", True) in p.sets and p.shoves == [] and list(p.attacks) == []
    assert lua.eval("PZA.motor.wantRun") is False
    pos["x"] = 10.4                                                          # 0.4 off: under 0.5
    tick(lua, p)
    assert p.shoves == [True] and list(p.attacks) == [0] and list(p.faced) == [z]
    assert ("setAutoWalk", False) in p.sets
    swing(lua, p)
    z.st["health"] = 0.2                                                     # the stomp landed
    tick(lua, p, 2)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"hit": True, "attackStarted": True, "targetDead": False}
    assert p.shoves == [True, False]


def test_a_stomp_that_did_no_damage_reports_no_hit_and_a_kill_reports_it(lua, fs):
    z = fz(7, 10.3, 20.0, floor=True, health=0.8)
    p, _ = stomp_host(lua, [z])
    start(lua, p, "stomp", targetId=7)
    tick(lua, p)
    swing(lua, p)
    tick(lua, p, 2)
    assert acts(lua, fs)[-1]["result"]["hit"] is False
    z2 = fz(8, 10.3, 20.0, floor=True, health=0.8)
    p, _ = stomp_host(lua, [z2], fresh=False)
    start(lua, p, "stomp", aid="k", targetId=8)
    tick(lua, p)
    swing(lua, p)
    z2.st["dead"] = True
    tick(lua, p, 2)
    assert acts(lua, fs)[-1]["result"] == {"hit": True, "attackStarted": True, "targetDead": True}


def test_stomp_refusals(lua, fs):
    fallen, standing = fz(7, 11.5, 20.0, floor=True), fz(8, 11.5, 21.0)
    p, _ = stomp_host(lua, [fallen, standing])
    start(lua, p, "stomp", aid="nt", targetId=99)
    start(lua, p, "stomp", aid="ba", targetId="7")
    start(lua, p, "stomp", aid="up", targetId=8)                             # the target stands: not valid
    p.combat["hitReaction"] = "HitReactionFront"
    start(lua, p, "stomp", aid="bu", targetId=7)
    assert states(acts(lua, fs)) == [("nt", "rejected", "no target"), ("ba", "rejected", "bad args"),
                                     ("up", "rejected", "not valid"), ("bu", "rejected", "busy")]


def test_stomp_is_refused_standing_while_a_standing_zombie_is_within_the_weapons_min_range(lua, fs):
    fallen, near, further = fz(7, 12.0, 20.0, floor=True), fz(8, 10.9, 20.0), fz(9, 11.5, 20.0)
    bat = make_weapon()
    bat.getMinRange = lambda s: 1.0
    p, _ = stomp_host(lua, [fallen, near], weapon=bat)
    start(lua, p, "stomp", aid="st", targetId=7)
    assert states(acts(lua, fs)) == [("st", "rejected", "standing")]
    p, _ = stomp_host(lua, [fallen, further], weapon=bat, fresh=False)                    # 1.5 off: outside the 1.0
    start(lua, p, "stomp", aid="ok", targetId=7)
    assert states(acts(lua, fs))[-1] == ("ok", "accepted", "")
    p, _ = stomp_host(lua, [fallen, fz(10, 10.5, 20.0, floor=True)], weapon=bat, fresh=False)    # a fallen one near does not count
    start(lua, p, "stomp", aid="fl", targetId=7)
    assert states(acts(lua, fs))[-1] == ("fl", "accepted", "")
    p, _ = stomp_host(lua, [fallen, fz(11, 10.5, 20.0)], fresh=False)                     # bare-handed: STAND_R 0.6 stands in
    start(lua, p, "stomp", aid="bh", targetId=7)
    assert states(acts(lua, fs))[-1] == ("bh", "rejected", "standing")


def test_a_zombie_that_closes_in_before_the_swing_fails_standing(lua, fs):
    fallen, other = fz(7, 10.8, 20.0, floor=True), fz(8, 12.0, 21.0)
    p, pos = stomp_host(lua, [fallen, other], weapon=make_weapon())
    start(lua, p, "stomp", targetId=7)
    tick(lua, p)
    other.getX, other.getY = (lambda s: 10.3), (lambda s: 20.2)
    pos["x"] = 10.4
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "standing") and p.shoves == [] and list(p.attacks) == []


def test_stomp_that_never_closes_in_fails_out_of_reach_after_its_walk_budget(lua, fs):
    z = fz(7, 12.0, 20.0, floor=True)
    p, _ = stomp_host(lua, [z])
    start(lua, p, "stomp", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 3999
    tick(lua, p)
    assert lua.eval("PZA.skills.cur") is not None
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "out of reach") and list(p.attacks) == []
    assert ("setAutoWalk", False) in p.sets                                  # the runner's end sends the auto-walk off


def test_stomp_without_the_auto_walk_or_the_shove_pair_fails_not_loaded(lua, fs):
    z = fz(7, 12.0, 20.0, floor=True)
    p, _ = stomp_host(lua, [z])
    p.setAutoWalkDirection = None
    start(lua, p, "stomp", targetId=7)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")
    z = fz(7, 10.2, 20.0, floor=True)
    p = shove_host(lua, [z], flag=False, fresh=False)
    start(lua, p, "stomp", aid="a2", targetId=7)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a2", "failed", "not loaded") and list(p.attacks) == []


@pytest.mark.parametrize("typ", ["unwear", "shove", "stomp"])
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
