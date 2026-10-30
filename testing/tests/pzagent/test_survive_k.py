"""Survival 10, the goal layer (Plan 24 Task 24; PZA/1.6.1 on the planner): the `clothing` loot and the view's `worn`,
the window past a stuck door and the goal descriptions' want order. The wear rule is `test_survive_j.py`. The fake mod
over the PZA/1.6 skills."""
import json

from agent.base import items as I
from agent.base import world as W
from agent.base.planner import goals as G
from agent.base.planner import view as V
from agent.base.pza1 import Window

from .test_night import CLOSED, OPEN, house
from .test_policies import Rig, zombie
from .test_survive import last, make, tick
from .test_survive_g import hold
from .test_survive_j import CAPS_15, PANTS, JACKET, cloth, rig, wl


# ================================================================ 3. the loot
def pile(r, items, x=111, y=201):
    sq = house(1, 110)
    for s in sq:
        if (s["x"], s["y"]) == (x, y):
            s["containers"] = [{"type": "wardrobe", "n": len(items), "items": list(items)}]
    r.scan(sq)


def test_the_loot_wants_clothing_after_the_containers_and_before_the_food(tmp_path):
    """Task 24 item 3: the wants run water, container, clothing, food, bandage, weapon; the container holding a jacket
    and an apple is looted for `clothing` first, with the Lua's filter."""
    r, sv = rig(tmp_path)
    pile(r, ["Base.Apple", "Base.Jacket_Leather"])
    r.frame(x=111.5, y=201.5)
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    cmd = g.step(r.world, r.acts, r.clock)
    assert (cmd.TYPE, cmd.kind, cmd.filter) == ("interact", "loot", "clothing")


def test_a_build_without_wear_loots_the_food_first_as_before(tmp_path):
    """The gate: no `wear` in the hello's caps (a PZA/1.5 build) wants no clothing, whatever the container holds."""
    r, sv = rig(tmp_path, caps=CAPS_15)
    pile(r, ["Base.Apple", "Base.Jacket_Leather"])
    r.frame(x=111.5, y=201.5)
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    cmd = g.step(r.world, r.acts, r.clock)
    assert cmd.filter == "food" and "clothing" not in G.wanted_uses(r.world)
    assert V._holds(r.world, [(111, 201, 0, 0)]) == {"food": 1}


def test_no_container_answers_a_clothing_loot_on_a_build_without_wear(tmp_path):
    """The gate is the build's: `nearest_unlooted("clothing")` and `open_uses` answer clothing only where `wear` is in the
    hello's caps (an older build's loot refuses the filter)."""
    for caps, want in ((None, True), (CAPS_15, False)):
        d = tmp_path / ("w" if want else "n")
        d.mkdir()
        r, sv = rig(d, caps=caps)
        pile(r, ["Base.Jacket_Leather"])
        r.frame(x=111.5, y=201.5)
        assert (r.world.nearest_unlooted("clothing") is not None) is want
        assert ("clothing" in G.open_uses(r.world, None, (111, 201, 0, 0))) is want


def test_clothing_is_no_longer_wanted_once_three_unworn_garments_are_held(tmp_path):
    """The hoard bound CLOTHING_HELD_N (3): a worn garment does not count; a container's garments are told by name only,
    so the wear rule judges each once held."""
    r, _ = rig(tmp_path)
    cloth(r, 20, worn=True)
    for i in (21, 22):
        cloth(r, i)
    r.frame()
    assert "clothing" in G.wanted_uses(r.world) and G.CLOTHING_HELD_N == 3
    cloth(r, 23)
    assert "clothing" not in G.wanted_uses(r.world)


def test_the_garment_guess_and_the_holds_of_a_container(tmp_path):
    for t in ("Base.Jacket_Leather", "Base.Hoodie_Black", "Base.Trousers_Denim", "Base.Boots_Army", "Base.Hat_Army",
              "Base.Vest_BulletPolice", "Base.Gloves_Leather", "Base.Tshirt_White"):
        assert I.garment(t) and I.holds_use(t, "clothing") and I.use_of(t) == "other", t
    for t in ("Base.Apple", "Base.Bandage", "Base.Nails", "Base.Hammer", "Base.WaterBottle", None, ""):
        assert not I.garment(t), t
    assert I.holds_use("Base.Apple", "food") and not I.holds_use("Base.Apple", "clothing")
    r, _ = rig(tmp_path)
    pile(r, ["Base.Jacket_Leather", "Base.Apple"])
    assert V._holds(r.world, [(111, 201, 0, 0)]) == {"clothing": 1, "food": 1}


def test_a_loot_for_clothing_that_ends_done_marks_the_container_for_clothing_only(tmp_path):
    r, sv = rig(tmp_path)
    pile(r, ["Base.Apple", "Base.Jacket_Leather"])
    r.frame(x=111.5, y=201.5)
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    cmd = g.step(r.world, r.acts, r.clock)
    g.sent(cmd, r.acts.send(cmd))
    r.answer()
    g.kit.observe(r.world, r.acts)
    assert r.world.containers[(111, 201, 0, 0)]["looted"] == {"clothing"}


def test_the_view_tells_the_model_the_worn_defence_per_location(tmp_path):
    """Task 24 item 3: the view's `worn` rows [loc, bite, scratch, holes] by location; None while unknown; rendered."""
    r, sv = make(tmp_path)
    r.frame()
    assert V.view(r.world, sv)["worn"] is None
    r.frame(worn=[wl(PANTS, 4.04, 5.0), wl(JACKET, 10.0, 20.0, holes=2)])
    v = V.view(r.world, sv)
    assert v["worn"] == [[JACKET, 10.0, 20.0, 2], [PANTS, 4.0, 5.0, 0]]
    assert "worn: [[" in V.render(v) and "worn" in V.KEYS


def test_a_worn_garment_is_never_the_spare_but_an_unworn_one_is(tmp_path):
    """Task 24: the load branch's and the flee's `spare` skips the garment on the back (a drop would undo the wear)."""
    from agent.base.planner import policies as P
    r, sv = rig(tmp_path)
    cloth(r, 20, worn=True, weight=6.0)
    r.event("item_added", itemId=21, fullType="Base.Hammer_Old", weight=2.0, use="other")
    r.frame()
    assert P.spare(r.world) == 21
    cloth(r, 22, weight=3.0)
    assert P.spare(r.world) == 22


# ================================================================ 4. the window past a stuck door
def with_window(sq, x=110, y=200, win=CLOSED, **cont):
    """house(1, 110)'s squares with a window record on the west edge of (x, y) (a wall edge already), and the
    FRIDGE at (111, 201)."""
    for s in sq:
        if (s["x"], s["y"]) == (x, y):
            s["window"] = dict(win)
        if (s["x"], s["y"]) == (111, 201):
            s["containers"] = [{"type": "fridge", "n": 1, "items": ["Base.Apple"]}]
    return sq


def stuck_door_rig(tmp_path, win=CLOSED, extra=(), health=100.0, zombies=()):
    """building 1 with its one door marked stuck from outside and a window at (110, 200), the player outside."""
    r, sv = make(tmp_path)
    r.scan(with_window(house(1, 110), win=win) + list(extra))
    r.frame(x=108.5, y=201.5, health=health, zombies=list(zombies))
    for _ in range(2):
        r.world.note_door_fail((110, 201, 0), "locked")
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    g.begin(r.world, r.acts, r.clock)
    return r, sv, g


def test_the_buildings_exterior_windows_are_told_from_the_maps_edges(tmp_path):
    r, _, _ = stuck_door_rig(tmp_path)
    assert r.world.windows(1) == [(110, 200, 0)]
    sq = with_window(house(1, 110), x=111, y=201)           # a window between two rooms: interior, never one
    for s in sq:
        if (s["x"], s["y"]) == (111, 201):
            s["edgeW"] = True
    r2 = Rig(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path)
    r2.scan(sq)
    assert r2.world.windows(1) == []


def test_every_door_marked_routes_the_loot_through_a_window_first(tmp_path):
    """Task 24 item 4: the building's doors all marked from outside and a window known: the goal sends `Window` (no
    smash) before any loot; the view no longer reads the building blocked."""
    r, sv, g = stuck_door_rig(tmp_path)
    assert N_blocked(r.world)
    cmd = g.choose(r.world, r.acts, r.clock)
    assert isinstance(cmd, Window) and (cmd.x, cmd.y, cmd.smash) == (110, 200, False)
    assert g.why["route"] == "window" and g.running
    b = next(b for b in V.view(r.world, sv)["buildings"] if b["id"] == 1)
    assert b["blocked"] is False
    r.world.note_window_fail((110, 200, 0), "fell")
    assert next(b for b in V.view(r.world, sv)["buildings"] if b["id"] == 1)["blocked"] is True


def N_blocked(world):
    from agent.base.planner import night as N
    return N.door_blocked(world, 1, 0)


def test_a_locked_window_is_smashed_only_with_no_other_building_near_no_zombie_and_health(tmp_path):
    """Task 24 item 4 / ruling 6: a locked window waits unless the character has no other building within BUILDING_R,
    no zombie listed within SMASH_ZOMBIE_R and health at or above SMASH_MIN_HEALTH; then `smash` is true."""
    locked = dict(CLOSED, locked=True)
    cases = {
        "alone": (dict(), True),
        "low_health": (dict(health=59.0), False),
        "zombie_near": (dict(zombies=[dict(zombie(1, 120.0, 201.5, me=(108.5, 201.5)), hasTarget=False)]), False),
        "other_building": (dict(extra=house(2, 130)), False),
    }
    for name, (kw, smash) in cases.items():
        d = tmp_path / name
        d.mkdir()
        r, sv, g = stuck_door_rig(d, win=locked, **kw)
        cmd = g.choose(r.world, r.acts, r.clock)
        if smash:
            assert isinstance(cmd, Window) and cmd.smash is True, name
        else:
            assert cmd is None and (g.state, g.reason) == ("failed", "no door"), name


def test_an_unlocked_shut_window_is_preferred_to_a_locked_one_and_never_smashed(tmp_path):
    """Ruling 6: the unlocked shut window is tried (opened, then climbed: no noise) though the locked one is nearer."""
    sq = with_window(house(1, 110), x=110, y=200, win=dict(CLOSED, locked=True))
    for s in sq:
        if (s["x"], s["y"]) == (110, 202):
            s["window"] = dict(CLOSED)
    r, sv = make(tmp_path)
    r.scan(sq)
    r.frame(x=108.5, y=200.5)
    for _ in range(2):
        r.world.note_door_fail((110, 201, 0), "locked")
    cmd = G.window_pick(r.world, 1)
    assert cmd == (110, 202, 0, False)


def test_an_open_window_is_first(tmp_path):
    sq = with_window(house(1, 110), x=110, y=200, win=CLOSED)
    for s in sq:
        if (s["x"], s["y"]) == (110, 202):
            s["window"] = dict(OPEN)
    r, sv = make(tmp_path)
    r.scan(sq)
    r.frame(x=108.5, y=200.5)
    assert G.window_pick(r.world, 1) == (110, 202, 0, False)


def test_a_window_that_failed_locked_is_smashed_on_the_next_try_and_other_failures_leave_it_out(tmp_path):
    """The goal's window failed `locked` (a perma-lock): marked; the next goal's pick smashes it when the smash is
    allowed; a `fell` or `not valid` end leaves it out for DOOR_RETRY_MIN."""
    r, sv, g = stuck_door_rig(tmp_path)
    cmd = g.choose(r.world, r.acts, r.clock)
    assert cmd.smash is False
    g.sent(cmd, r.acts.send(cmd))
    r.fake.answer({"window": ["accepted", {"state": "failed", "reason": "locked"}]})
    r.pump()
    g.observe(r.world, r.acts, r.clock)
    assert r.world.window_fail((110, 200, 0)) == "locked" and g.running
    assert G.window_pick(r.world, 1) == (110, 200, 0, True)
    r.world.note_window_fail((110, 200, 0), "not valid")
    assert G.window_pick(r.world, 1) is None
    r.frame(x=108.5, y=201.5, game_min=480.0 + W.DOOR_RETRY_MIN)
    assert G.window_pick(r.world, 1) == (110, 200, 0, False)


def test_a_barricaded_window_is_never_tried_and_a_build_without_window_fails_no_door(tmp_path):
    r, sv, g = stuck_door_rig(tmp_path, win=dict(CLOSED, barricaded=True))
    assert g.choose(r.world, r.acts, r.clock) is None and (g.state, g.reason) == ("failed", "no door")
    d = tmp_path / "b"
    d.mkdir()
    r2, sv2 = make(d, caps=CAPS_15)
    r2.scan(with_window(house(1, 110)))
    r2.frame(x=108.5, y=201.5)
    for _ in range(2):
        r2.world.note_door_fail((110, 201, 0), "locked")
    assert G.window_pick(r2.world, 1) is None


def test_inside_the_building_no_window_route_is_taken(tmp_path):
    """Ruling 5: the route is for a character outside; inside, a locked front door unlocks on the open (the Lua's), so
    a loot goes on and the window is not tried."""
    r, sv, g = stuck_door_rig(tmp_path)
    r.frame(x=111.5, y=201.5)
    g.route_due = True
    cmd = g.choose(r.world, r.acts, r.clock)
    assert not isinstance(cmd, Window) and g.route_due is False


def test_a_window_done_ends_the_route_and_logs_cut_and_wounds(tmp_path):
    """Task 24 item 4: a window that ended done leaves the route (the character stands inside), the result's `cut` and
    `wounds` logged on the goal's why."""
    r, sv, g = stuck_door_rig(tmp_path)
    cmd = g.choose(r.world, r.acts, r.clock)
    g.sent(cmd, r.acts.send(cmd))
    r.fake.answer({"window": ["accepted", {"state": "done", "result": {"smashed": False, "opened": True,
                                                                         "cut": True, "wounds": 1}}]})
    r.pump()
    g.observe(r.world, r.acts, r.clock)
    assert g.window is None and g.route_due is False and g.running
    assert (g.why["ended"], g.why["cut"], g.why["wounds"]) == ("window", True, 1)


def test_the_care_branch_reads_the_wounds_after_a_window_whatever_cut_says(tmp_path):
    """The window result's `cut` is unreliable in multiplayer: a window that ended done with `cut` false but a bleeding
    part in the next frame is bandaged by the care branch (the frame's body parts are the truth), the goal superseded."""
    r, sv = make(tmp_path)
    r.scan(with_window(house(1, 110)))
    hold(r, 10, "Base.Bandage")
    r.frame(x=108.5, y=201.5)
    for _ in range(2):
        r.world.note_door_fail((110, 201, 0), "locked")
    tick(r, sv)
    assert r.cmd() == ("window", {"x": 110, "y": 200}) and sv.goals.current.TYPE == "LootBuilding"
    r.fake.answer({"window": ["accepted", {"state": "done", "result": {"smashed": False, "opened": True,
                                                                         "cut": False, "wounds": 0}}]})
    r.pump()
    part = {"i": 4, "h": 70.0, "bleeding": True, "bleedingTime": 6.0, "bandaged": False, "bandageLife": None,
            "bandageDirty": None, "deep": False, "infected": False}
    r.frame(x=111.5, y=201.5, wounds={"parts": [part], "bleeding": 1})
    tick(r, sv)
    assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 4})


def test_the_first_loot_failed_not_adjacent_with_every_door_marked_still_routes_through_the_window(tmp_path):
    r, sv, g = stuck_door_rig(tmp_path)
    g.route_due = False
    g.route_due = True
    cmd = g.choose(r.world, r.acts, r.clock)
    assert isinstance(cmd, Window)


# ================================================================ 5. goals.json
def test_lootbuildings_description_states_the_want_order_of_stock_wants():
    """Task 24 item 5: the description's parenthesis lists STOCK_WANTS in order (water, container, clothing, food, bandage,
    weapon); the schema tool does not own this file (hand edited)."""
    with open(G.SCHEMA_PATH, encoding="utf-8") as f:
        d = json.load(f)
    entry = next(e for e in d["oneOf"] if e["properties"]["type"]["const"] == "LootBuilding")
    text = entry["description"]
    inner = text[text.index("(") + 1:text.index(")")]
    words = [w.strip() for w in inner.split(":")[0].split(",")]
    assert tuple(words) == G.STOCK_WANTS


def test_the_doors_spent_through_the_machine_the_window_route_follows_and_without_it_the_goal_fails(tmp_path):
    """Task 24 item 4 end to end: the loot stands against door 1 (`not adjacent`), door 1 and door 2 both fail `locked`
    through the shelter machine, the machine shuns; with a window known the next send is the `Window`, on a build
    without `window` the goal fails `no door` as before."""
    from .test_night import two_door_house
    for caps, want in ((None, "window"), (CAPS_15, "fail")):
        d = tmp_path / want
        d.mkdir()
        r, sv = make(d, caps=caps)
        sqs = two_door_house(exterior2=CLOSED)
        for s in sqs:
            if (s["x"], s["y"]) == (112, 202):
                s["containers"] = [{"type": "fridge", "n": 1, "items": ["Base.Apple"]}]
            if (s["x"], s["y"]) == (110, 200):
                s["window"] = dict(CLOSED)
        r.scan(sqs)
        r.frame(x=109.5, y=201.5)
        tick(r, sv)
        assert r.cmd()[1]["kind"] == "loot"
        r.answer({"state": "failed", "reason": "not adjacent"})
        for door in (201, 202):
            r.frame(x=109.5, y=201.5)
            tick(r, sv)
            assert r.cmd() == ("interact", {"x": 110, "y": door, "kind": "open", "filter": "all", "maxWeight": 0.0})
            r.answer({"state": "failed", "reason": "locked"})
        r.frame(x=109.5, y=201.5)
        tick(r, sv)
        if want == "window":
            assert r.cmd() == ("window", {"x": 110, "y": 200}) and last(d)["inputs"]["branches"]["goal"]["route"] == "window"
        else:
            assert [a.type for a in r.acts.history].count("window") == 0
            assert sv.goals.history[-1]["reason"] == "no door"
