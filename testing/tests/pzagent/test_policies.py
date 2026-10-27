"""The planner's policies (Plan 22 Task 10): Fight, Flee, Explore and LootHouse over the typed Actions, end to end on
the fake mod (FakeMod writes the lines, FileTransport reads them, World and Actions are pumped, cmd.txt carries the
sends). One action at a time: a policy sends nothing while its own action is current and decides again on its end."""
import json
import math

import pytest

from agent.base.actions import Actions
from agent.base.planner import policies as P
from agent.base.planner.policies import Explore, Fight, Flee, LootHouse
from agent.base.transport.files import FileTransport
from agent.base.world import World

from .fakemod import DEFAULT_FRAME, FakeMod, bad_args

BAT = {"type": "Base.BaseballBat", "cond": 0.9, "reach": 1.2, "ammo": None}


def zombie(zid, x, y, me=(100.0, 200.0)):
    return {"id": zid, "x": x, "y": y, "dist": math.hypot(x - me[0], y - me[1]), "hasTarget": True,
            "crawler": False, "health": 1.0}


def square(x, y, **k):
    d = {"x": x, "y": y, "z": 0, "solid": False, "solidTrans": False, "light": 0.75, "room": None, "building": None,
         "door": None, "window": None, "containers": [], "floor": []}
    d.update(k)
    return d


def swing(started):
    return {"swings": 1, "attackStarted": started, "meleeDelay": 0.0, "targetDead": False}


class Rig:
    """The fake mod, the transport, a World and Actions in one state dir, on one injected clock."""

    def __init__(self, tmp_path, now=1000.0):
        self.t = {"now": now}
        self.clock = lambda: self.t["now"]
        self.dir = tmp_path
        self.fake = FakeMod(str(tmp_path), clock=self.clock)
        self.tr = FileTransport(str(tmp_path), clock=self.clock)
        self.world = World()
        self.acts = Actions(self.tr, clock=self.clock)
        self.fake.hello()
        self.pump()

    def pump(self):
        lines = self.tr.lines()
        for ln in lines:
            self.world.apply(ln)
        self.acts.pump(lines)

    def frame(self, x=100.0, y=200.0, zombies=(), weapon=BAT, health=100.0, hunger=0.1, thirst=0.1, level=0,
              game_min=480.0):
        me = dict(DEFAULT_FRAME["me"], x=x, y=y)
        stats = dict(DEFAULT_FRAME["stats"], hunger=hunger, thirst=thirst)
        body = dict(DEFAULT_FRAME["body"], health=health)
        load = dict(DEFAULT_FRAME["load"], level=level)
        self.fake.frame(me=me, stats=stats, body=body, load=load, weapon=weapon, zombies=list(zombies),
                        gameMin=game_min)
        self.pump()

    def event(self, kind, **k):
        self.fake.event(kind, **k)
        self.pump()

    def scan(self, squares):
        self.fake.map_full(squares)
        self.pump()

    def answer(self, *script):
        """Answer the last cmd: accepted then each scripted end (default done)."""
        cmd = json.loads((self.dir / "cmd.txt").read_text(encoding="utf-8"))
        ends = list(script) or ["done"]
        self.fake.answer({cmd["type"]: ["accepted"] + ends})
        self.pump()
        return cmd

    def cmd(self):
        c = json.loads((self.dir / "cmd.txt").read_text(encoding="utf-8"))
        return c["type"], c["args"]

    def advance(self, s):
        self.t["now"] += s


def all_sends_valid(rig):
    """Every action the rig's Actions sent is valid against ACTION_ARGS by the fake mod's own check."""
    assert rig.acts.history
    for a in rig.acts.history:
        assert bad_args({"seq": 1, "aid": a.aid, "type": a.type, "args": a.args}) == "", a
        assert a.state != "rejected", a


# ================================================================ Fight
def test_fight_walks_at_a_run_to_the_zombie_square_beyond_reach_then_attacks_within_it(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 105.6, 200.2)])
    f = Fight(r.world, r.acts, r.clock)
    a = f.step()
    assert a is not None and r.cmd() == ("walkTo", {"x": 105, "y": 200, "gait": "run"})
    r.frame(zombies=[zombie(7, 104.0, 200.0)])
    assert f.step() is None                                  # its walk is current: nothing sent
    r.answer()
    r.frame(zombies=[zombie(7, 101.5, 200.0)])
    assert f.step() is not None and r.cmd() == ("attack", {"targetId": 7})
    assert len(r.acts.history) == 2
    all_sends_valid(r)


def test_fight_picks_the_nearest_zombie(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(3, 104.0, 200.0), zombie(9, 101.0, 200.0)])
    Fight(r.world, r.acts, r.clock).step()
    assert r.cmd() == ("attack", {"targetId": 9})


def test_two_swings_not_started_in_a_row_force_one_approach_walk(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd()[0] == "attack"
    r.answer({"state": "done", "result": swing(False)})
    f.step()
    assert r.cmd()[0] == "attack"                            # one miss: attack again
    r.answer({"state": "done", "result": swing(True)})
    f.step()
    r.answer({"state": "done", "result": swing(False)})
    f.step()
    assert r.cmd()[0] == "attack"                            # a start in between: the count began again
    r.answer({"state": "done", "result": swing(False)})
    f.step()
    assert r.cmd() == ("walkTo", {"x": 101, "y": 200, "gait": "run"})   # two in a row: re-approach
    r.answer()
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7})
    all_sends_valid(r)


@pytest.mark.parametrize("dist, stalls", [(5.0, True), (2.74, True), (1.5, False)])   # 2.74: run 1's standoff
def test_the_stall_clock_reads_true_after_fight_max_s_unbroken_out_of_reach(tmp_path, dist, stalls):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 100.0 + dist, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    r.advance(P.FIGHT_MAX_S)
    r.frame(zombies=[zombie(7, 100.0 + dist, 200.0)])
    f.step()
    assert f.stalled is False                                # at FIGHT_MAX_S exactly: not yet
    r.advance(1.0)
    r.frame(zombies=[zombie(7, 100.0 + dist, 200.0)])
    f.step()
    assert f.stalled is stalls


def test_a_tick_within_reach_restarts_the_stall_clock(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    r.advance(15.0)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f.step()
    assert f.fight_s() == 0.0
    r.advance(0.5)
    r.frame(zombies=[zombie(7, 102.3, 200.0)])               # knocked back
    f.step()
    assert f.fight_s() == 0.5
    r.advance(15.0)
    r.frame(zombies=[zombie(7, 102.3, 200.0)])
    f.step()
    assert f.fight_s() == 15.5 and f.stalled is False
    r.advance(5.0)
    r.frame(zombies=[zombie(7, 102.3, 200.0)])
    f.step()
    assert f.stalled is True                                 # 20.5 s unbroken out of reach


def test_fight_with_no_zombie_sends_nothing(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    assert Fight(r.world, r.acts, r.clock).step() is None and r.acts.history == []


# ================================================================ Flee
def test_flee_steers_from_the_centroid_through_the_player_at_a_run(tmp_path):
    r = Rig(tmp_path)
    zs = [zombie(1, 103.0, 200.0), zombie(2, 103.0, 202.0)]
    r.frame(zombies=zs)
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    typ, args = r.cmd()
    n = math.hypot(-3.0, -1.0)
    assert typ == "steer" and args["gait"] == "run" and args["seconds"] == P.FLEE_S == 3.0
    assert args["vx"] == pytest.approx(-3.0 / n) and args["vy"] == pytest.approx(-1.0 / n)
    assert math.hypot(args["vx"], args["vy"]) == pytest.approx(1.0)
    assert f.step() is None                                  # the steer is current
    r.answer()
    r.event("zombie_dead", id=2)
    r.frame(x=97.0, y=200.0, zombies=[zombie(1, 100.0, 203.0, me=(97.0, 200.0))])
    f.step()                                                 # re-aimed on the steer's end
    typ, args = r.cmd()
    n = math.hypot(-3.0, -3.0)
    assert args["vx"] == pytest.approx(-3.0 / n) and args["vy"] == pytest.approx(-3.0 / n)
    all_sends_valid(r)


def test_flee_sprints_when_the_nearest_is_within_sprint_r(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(1, 101.5, 200.0), zombie(2, 105.0, 200.0)])
    Flee(r.world, r.acts, r.clock).step()
    typ, args = r.cmd()
    assert args["gait"] == "sprint" and args["vx"] == pytest.approx(-1.0) and args["vy"] == pytest.approx(0.0)


def test_flee_reads_the_threat_list_it_is_given(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(1, 100.0, 203.0), zombie(2, 100.0, 180.0)])
    f = Flee(r.world, r.acts, r.clock)
    f.threats = [r.world.zombies[1]]
    f.step()
    _, args = r.cmd()
    assert args["vx"] == pytest.approx(0.0) and args["vy"] == pytest.approx(-1.0)


# ================================================================ Explore
def test_explore_scans_once_at_a_place_then_walks_to_the_unexplored_edge(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    assert r.cmd() == ("scan", {"r": P.SCAN_R}) and P.SCAN_R == 10
    r.answer()
    r.scan([square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame()
    e.step()
    assert r.cmd() == ("walkTo", {"x": 99, "y": 200, "gait": "walk"})
    assert e.step() is None                                  # walking
    r.answer()
    r.frame(x=99.0)
    e.step()
    assert r.cmd()[0] == "walkTo"                            # the same place: no second scan
    assert [a.type for a in r.acts.history].count("scan") == 1
    r.answer()
    r.frame(x=116.0)
    e.step()
    assert r.cmd() == ("scan", {"r": 10})                    # a new place: scanned once
    all_sends_valid(r)


def test_explore_with_no_edge_sends_nothing(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    assert e.step() is None and len(r.acts.history) == 1


# ================================================================ LootHouse
CRATE = {"type": "crate", "n": 1, "items": ["Base.Nails"]}
FRIDGE = {"type": "fridge", "n": 1, "items": ["Base.Apple"]}


def test_loothouse_loots_the_nearest_unlooted_and_marks_it_when_the_loot_ends(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE]), square(106, 200, containers=[FRIDGE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock)
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "all"})
    assert lh.step() is None
    r.answer({"state": "failed", "reason": "not adjacent"})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] is True
    assert r.cmd() == ("interact", {"x": 106, "y": 200, "kind": "loot", "filter": "all"})
    all_sends_valid(r)


def test_loothouse_takes_its_want_as_the_filter(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE]), square(106, 200, containers=[FRIDGE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="food")
    lh.step()
    assert r.cmd() == ("interact", {"x": 106, "y": 200, "kind": "loot", "filter": "food"})


def test_a_superseded_loot_keeps_its_container(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock)
    lh.step()
    r.answer({"state": "failed", "reason": "superseded"})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] is False
    assert r.cmd()[0] == "interact" and len(r.acts.history) == 2


def test_loothouse_never_loots_at_level_three_and_drops_the_heaviest_other_item_until_two(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    for iid, ft, wt in [(601, "Base.BaseballBat", 9.0), (602, "Base.Plank", 3.0), (603, "Base.Nails", 0.5),
                        (604, "Base.TinnedSoup", 5.0), (605, "Base.Crowbar", 4.0), (606, "Base.WaterBottleFull", 6.0)]:
        r.event("item_added", itemId=iid, fullType=ft, weight=wt)
    r.frame(level=3)
    lh = LootHouse(r.world, r.acts, r.clock)
    lh.step()
    assert r.cmd() == ("drop", {"itemId": 602})               # not the bat, the crowbar, the soup or the water
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.frame(level=3)
    lh.step()
    assert r.cmd() == ("drop", {"itemId": 603})
    r.answer()
    r.event("item_removed", itemId=603, fullType="Base.Nails")
    r.frame(level=3)
    assert lh.step() is None                                 # nothing left to drop, and no loot at level 3
    assert [a.type for a in r.acts.history] == ["drop", "drop"]
    r.frame(level=2)
    lh.step()
    assert r.cmd()[0] == "interact"
    all_sends_valid(r)


# ================================================================ every policy's sends
def test_every_send_of_every_policy_is_valid_against_action_args(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(x, y, containers=[CRATE] if (x, y) == (101, 201) else []) for x in range(99, 102)
            for y in range(199, 202)])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    zs = [zombie(1, 103.3, 200.7), zombie(2, 101.2, 200.1)]
    for policy in (Fight, Flee, Explore, LootHouse):
        for level in (0, 3):
            r.frame(zombies=zs, level=level)
            p = policy(r.world, r.acts, r.clock)
            for _ in range(3):
                if p.step() is not None:
                    r.answer()
                r.frame(zombies=zs, level=level)
    assert {a.type for a in r.acts.history} >= {"walkTo", "attack", "steer", "scan", "interact", "drop"}
    all_sends_valid(r)
