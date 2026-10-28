"""The planner's policies (Plan 22 Task 10): Fight, Flee, Explore and LootHouse over the typed Actions, end to end on
the fake mod (FakeMod writes the lines, FileTransport reads them, World and Actions are pumped, cmd.txt carries the
sends). One action at a time: a policy sends nothing while its own action is current and decides again on its end."""
import json
import math

import pytest

from agent.base.actions import Actions
from agent.base.planner import policies as P
from agent.base.planner.policies import UNREACHABLE_S, Explore, Fight, Flee, LootHouse
from agent.base.transport.files import FileTransport
from agent.base.world import World

from . import fakemod
from .fakemod import DEFAULT_FRAME, FakeMod, bad_args

BAT = {"type": "Base.BaseballBat", "cond": 0.9, "reach": 1.2, "ammo": None}


def zombie(zid, x, y, me=(100.0, 200.0)):
    return {"id": zid, "x": x, "y": y, "dist": math.hypot(x - me[0], y - me[1]), "hasTarget": True,
            "crawler": False, "health": 1.0}


def square(x, y, **k):
    """A PZA/1.2 square at (x, y): fakemod's open outdoor square (its four edges False), light 0.75, `k` laid over."""
    return fakemod.square(**dict({"x": x, "y": y, "light": 0.75}, **k))


def grid(x0, x1, y0, y1, at=None):
    """Every square of x0..x1 by y0..y1, open; `at[(x, y)]` a dict of fields laid over that square."""
    at = at or {}
    return [square(x, y, **at.get((x, y), {})) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


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
              game_min=480.0, wounds=None, load_max=8.0):
        me = dict(DEFAULT_FRAME["me"], x=x, y=y)
        stats = dict(DEFAULT_FRAME["stats"], hunger=hunger, thirst=thirst)
        body = dict(DEFAULT_FRAME["body"], health=health, **(wounds or {}))
        load = dict(DEFAULT_FRAME["load"], level=level, max=load_max)
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


# I2 (the whole-pass review): run 1's 103 attacks, every one `done` with `attackStarted` true, zombie 32404's health
# 1.167 on all 1530 frames listing it -- a target within FIGHT_REACH behind a locked door held the fight forever.
def zh(zid, x, y, health):
    return dict(zombie(zid, x, y), health=health)


def swing_at(r, f, zid, x, health, started=True):
    """Step the fight, expect an attack on zid, answer it done with `started`, then a frame with the target at
    `health`."""
    f.step()
    assert r.cmd() == ("attack", {"targetId": zid})
    r.answer({"state": "done", "result": swing(started)})
    r.frame(zombies=[zh(zid, x, 200.0, health)])


def test_the_no_progress_constants():
    assert (P.STALL_SWINGS, P.UNREACHABLE_S) == (3, 20.0)


def test_three_started_swings_that_take_no_health_make_the_target_unreachable(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.167)])
    f = Fight(r.world, r.acts, r.clock)
    for _ in range(3):
        swing_at(r, f, 7, 101.0, 1.167)
    a = f.step()                                             # the fourth decision
    assert a is None or a.args.get("targetId") != 7
    assert len([x for x in r.acts.history if x.type == "attack"]) == 3
    assert f.why["unreachable"] == [7]
    r.advance(P.UNREACHABLE_S - 0.5)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.167)])
    assert f.step() is None                                  # still inside UNREACHABLE_S
    r.advance(1.0)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.167)])
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7})            # past it: tried again


def test_an_unreachable_target_falls_through_to_another(tmp_path):
    r = Rig(tmp_path)
    two = lambda: [zh(7, 101.0, 200.0, 1.167), zh(8, 101.5, 201.0, 1.0)]
    r.frame(zombies=two())
    f = Fight(r.world, r.acts, r.clock)
    for _ in range(3):
        f.step()
        assert r.cmd() == ("attack", {"targetId": 7})
        r.answer({"state": "done", "result": swing(True)})
        r.frame(zombies=two())
    f.step()
    assert r.cmd() == ("attack", {"targetId": 8})


def test_swings_whose_target_loses_health_keep_the_fight(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.0)])
    f = Fight(r.world, r.acts, r.clock)
    for h in (0.9, 0.9, 0.8, 0.8, 0.8, 0.7):                 # a fall within every three swings
        swing_at(r, f, 7, 101.0, h)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and len(r.acts.history) == 7


def test_a_done_swing_not_started_does_not_count(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.0)])
    f = Fight(r.world, r.acts, r.clock)
    swing_at(r, f, 7, 101.0, 1.0)
    swing_at(r, f, 7, 101.0, 1.0, started=False)
    swing_at(r, f, 7, 101.0, 1.0)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7})            # two started swings only: still fighting
    r.answer({"state": "done", "result": swing(True)})
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.0)])
    a = f.step()
    assert a is None or a.args.get("targetId") != 7          # the third started swing


def test_the_unreachable_memory_is_shared_with_a_later_fight(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zh(7, 101.0, 200.0, 1.0)])
    memo = {}
    f = Fight(r.world, r.acts, r.clock, unreachable=memo)
    for _ in range(3):
        swing_at(r, f, 7, 101.0, 1.0)
    f.step()
    assert set(memo) == {7}
    assert Fight(r.world, r.acts, r.clock, unreachable=memo).step() is None


def test_a_nil_id_zombie_is_never_a_target(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[dict(zombie(7, 101.0, 200.0), id=None)])
    f = Fight(r.world, r.acts, r.clock)
    assert f.step() is None and r.acts.history == []
    r.frame(zombies=[dict(zombie(7, 101.0, 200.0), id=None), zombie(8, 103.0, 200.0)])
    f.step()
    assert r.cmd() == ("walkTo", {"x": 103, "y": 200, "gait": "run"})


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


@pytest.mark.parametrize("end", [{"state": "failed", "reason": "superseded"}, {"state": "failed", "reason": "dead"},
                                 "rejected"])
def test_a_scan_that_ends_other_than_done_is_retried(tmp_path, end):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    assert r.cmd() == ("scan", {"r": 10})
    assert e.step() is None                                  # running: not re-sent
    if end == "rejected":
        r.fake.act(r.acts.history[-1].aid, "rejected", "scan", reason="not loaded")
        r.pump()
    else:
        r.answer(end)
    e.step()
    assert r.cmd() == ("scan", {"r": 10}) and [a.type for a in r.acts.history] == ["scan", "scan"]
    r.answer()
    e.step()
    assert [a.type for a in r.acts.history] == ["scan", "scan"]   # done: the place is scanned, no edge yet


def test_a_scan_dropped_after_its_done_line_is_scanned_again(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()                                               # done {queued}: the place is scanned
    aid = r.acts.history[-1].aid
    r.scan([square(100, 200)])
    r.frame()
    e.step()
    assert r.cmd()[0] == "walkTo"
    r.answer()
    r.event("scan_dropped", scanId=1, aid=aid, part=2, parts=3, reason="java raised")   # S-32: the job cut short
    assert r.acts.history[0].state == "done"                 # a finished action stays finished
    e.step()
    assert r.cmd() == ("scan", {"r": 10}) and [a.type for a in r.acts.history] == ["scan", "walkTo", "scan"]
    r.answer()
    r.event("scan_dropped", scanId=1, aid=aid, part=2, parts=3, reason="java raised")   # the old aid again: no effect
    e.step()
    assert [a.type for a in r.acts.history].count("scan") == 2


def test_a_scan_that_times_out_is_retried(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.advance(31.0)                                          # past the default 30 s deadline
    r.frame()
    e.step()
    assert r.acts.history[0].state == "timeout" and [a.type for a in r.acts.history] == ["scan", "scan"]


# I4 (the whole-pass review): run 1 re-sent a walkTo that failed `stuck` to the same edge 20 times.
def test_the_stuck_ttl_constant():
    from agent.base import world as W
    assert W.STUCK_TTL_MIN == 60


@pytest.mark.parametrize("reason", ["stuck", "no path", "no square"])
def test_a_stuck_edge_is_not_chosen_again_until_its_ttl_passes(tmp_path, reason):
    r = Rig(tmp_path)
    r.frame(game_min=480.0)
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    r.scan([square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(game_min=480.0)
    e.step()
    first = r.cmd()
    assert first == ("walkTo", {"x": 99, "y": 200, "gait": "walk"})
    r.answer({"state": "failed", "reason": reason})
    r.frame(game_min=481.0)
    e.step()
    assert r.cmd()[0] == "walkTo" and r.cmd() != first             # a different edge
    assert r.world.stuck == {(99, 200): 481.0}
    r.answer({"state": "failed", "reason": "superseded"})            # not a stuck reason: nothing remembered
    assert set(r.world.stuck) == {(99, 200)}
    r.frame(game_min=481.0 + 59.0)
    e.step()
    assert r.cmd() != first                                          # inside the TTL
    r.answer()
    r.frame(game_min=481.0 + 60.0)
    e.step()
    assert r.cmd() == first                                          # the TTL passed: the edge again


def test_a_walk_that_ends_done_or_fails_otherwise_is_not_remembered(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    r.scan([square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame()
    e.step()
    r.answer({"state": "failed", "reason": "interrupted"})
    r.frame()
    e.step()
    assert r.cmd() == ("walkTo", {"x": 99, "y": 200, "gait": "walk"}) and r.world.stuck == {}


@pytest.mark.parametrize("x, place", [(105.0, 110), (115.0, 120), (104.9, 100), (114.9, 110)])
def test_a_place_is_a_uniform_half_up_grid(tmp_path, x, place):
    r = Rig(tmp_path)
    r.frame(x=x, y=x + 100.0)
    assert Explore(r.world, r.acts, r.clock).place() == (place, place + 100)


def test_explore_with_no_edge_sends_nothing(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    assert e.step() is None and len(r.acts.history) == 1


# ================================================================ LootHouse
CRATE = {"type": "crate", "n": 1, "items": ["Base.Bandage"]}   # a `bandage` container (`items.use_of`)
FRIDGE = {"type": "fridge", "n": 1, "items": ["Base.Apple"]}
SHELF = {"type": "shelf", "n": 1, "items": ["Base.Nails"]}       # an `other` container: never a loot's want


def test_loothouse_loots_the_nearest_unlooted_and_marks_it_when_the_loot_ends(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE]), square(106, 200, containers=[dict(CRATE, type="cupboard")])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "bandage", "maxWeight": 8.0})
    assert lh.step() is None
    r.answer({"state": "failed", "reason": "not adjacent"})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] is True
    assert r.cmd() == ("interact", {"x": 106, "y": 200, "kind": "loot", "filter": "bandage", "maxWeight": 8.0})
    all_sends_valid(r)


def test_loothouse_takes_its_want_as_the_filter(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE]), square(106, 200, containers=[FRIDGE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="food")
    lh.step()
    assert r.cmd() == ("interact", {"x": 106, "y": 200, "kind": "loot", "filter": "food", "maxWeight": 8.0})


# Plan 23 Task 11 (P23-7, P23-8): every loot is capped at the carry ratio and filtered by one use, never `all`.
def test_the_loot_ratio_constant_and_wants():
    assert P.LOAD_RATIO_MAX == 1.0 and P.LOOT_WANTS == ("food", "water", "weapon", "bandage")


@pytest.mark.parametrize("load_max, cap", [(8.0, 8.0), (12.5, 12.5), (None, 0.0), (0.0, 0.0)])
def test_the_loot_carries_the_cap_off_the_frames_max_weight(tmp_path, load_max, cap):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[FRIDGE])])
    r.frame(load_max=load_max)
    lh = LootHouse(r.world, r.acts, r.clock, want="food")
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "food", "maxWeight": cap})
    assert lh.why["cap"] == cap
    all_sends_valid(r)


@pytest.mark.parametrize("want", [None, "all", "other"])
def test_a_loot_without_one_of_the_four_wants_is_never_sent(tmp_path, want):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE, FRIDGE, SHELF])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want=want)
    assert lh.step() is None and r.acts.history == []
    assert lh.why["want"] == want and lh.why["container"] is None


def test_a_loot_wanting_a_use_no_container_holds_sends_nothing(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[SHELF])])
    r.frame()
    assert LootHouse(r.world, r.acts, r.clock, want="water").step() is None and r.acts.history == []


def test_a_superseded_loot_keeps_its_container(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    lh.step()
    r.answer({"state": "failed", "reason": "superseded"})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] is False
    assert r.cmd()[0] == "interact" and len(r.acts.history) == 2


def test_loothouse_never_loots_at_level_three_and_drops_the_heaviest_other_item_until_two(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    for iid, ft, wt in [(601, "Base.BaseballBat", 9.0), (602, "Base.Plank", 3.0), (603, "Base.Nails", 0.5),
                        (604, "Base.TinnedSoup", 5.0), (605, "Base.Crowbar", 4.0), (606, "Base.WaterBottle", 6.0)]:
        r.event("item_added", itemId=iid, fullType=ft, weight=wt)
    r.frame(level=3)
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
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
    assert lh.step() is None                                 # level 2: no loot (spec § 9 (1)) and no drop
    r.frame(level=1)
    lh.step()
    assert r.cmd()[0] == "interact"
    all_sends_valid(r)


# I1 (the whole-pass review): spec § 9 (1), "a policy stops looting before level 3" -- a loot with filter `all` at
# level 2 took run 1 and run 2 to level 3 and 4 in one interact.
def test_the_load_guard_constants_name_the_levels():
    assert (P.LOOT_MAX_LEVEL, P.DROP_AT, P.DROP_TO) == (1, 3, 2)
    assert not hasattr(P, "LOAD_STOP")


@pytest.mark.parametrize("level, want", [(0, "interact"), (1, "interact"), (2, None), (3, "drop"), (4, "drop")])
def test_loothouse_loots_only_at_level_0_or_1_and_drops_at_3_or_above(tmp_path, level, want):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(level=level)
    a = LootHouse(r.world, r.acts, r.clock, want="bandage").step()
    assert (a.type if a is not None else None) == want
    if want is None:
        assert r.acts.history == []


def test_drops_bring_the_level_to_two_and_then_nothing_is_sent_until_it_is_under_two(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    for iid, wt in [(602, 3.0), (603, 2.0), (604, 1.0)]:
        r.event("item_added", itemId=iid, fullType="Base.Plank", weight=wt)
    r.frame(level=3)
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    lh.step()
    assert r.cmd() == ("drop", {"itemId": 602})
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.frame(level=2)                                         # the drop brought it to 2
    for _ in range(3):
        assert lh.step() is None                             # no loot, no further drop
        r.frame(level=2)
    assert [a.type for a in r.acts.history] == ["drop"]
    r.frame(level=1)
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "bandage", "maxWeight": 8.0})


# ================================================================ every policy's sends
def test_every_send_of_every_policy_is_valid_against_action_args(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(x, y, containers=[CRATE] if (x, y) == (101, 201) else []) for x in range(99, 102)
            for y in range(199, 202)])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    zs = [zombie(1, 103.3, 200.7), zombie(2, 101.2, 200.1)]
    loot = lambda w, a, c: LootHouse(w, a, c, want="bandage")
    for policy in (Fight, Flee, Explore, loot):
        for level in (0, 3):
            r.frame(zombies=zs, level=level)
            p = policy(r.world, r.acts, r.clock)
            for _ in range(3):
                if p.step() is not None:
                    r.answer()
                r.frame(zombies=zs, level=level)
    assert {a.type for a in r.acts.history} >= {"walkTo", "attack", "steer", "scan", "interact", "drop"}
    all_sends_valid(r)


def test_explore_says_it_scans_per_place_grid():
    """N3 (the whole-pass review): spec § 6's "once at a new building or on request" is read as the place grid."""
    assert "per 10-tile place" in P.__doc__ and "new building" in P.__doc__


# P9 (the wave's Minor 3): an attack whose approach walk cannot queue ends `failed` at once; the target is unreachable.
@pytest.mark.parametrize("reason", ["no path", "no square", "stuck"])
def test_an_attack_failed_for_its_approach_marks_the_target_unreachable(tmp_path, reason):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7})
    r.answer({"state": "failed", "reason": reason})
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f.step()
    assert f.unreachable == {7: r.clock() + UNREACHABLE_S}
    for _ in range(39):                                      # every planner tick of 20 s: never an Attack on 7
        r.advance(0.5)
        r.frame(zombies=[zombie(7, 101.0, 200.0)])
        assert f.step() is None
    assert [a.type for a in r.acts.history].count("attack") == 1


def test_an_attack_failed_otherwise_does_not_mark_the_target(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    r.answer({"state": "failed", "reason": "interrupted"})
    r.frame(zombies=[zombie(7, 101.0, 200.0)])
    assert f.step() is not None and r.cmd() == ("attack", {"targetId": 7})
    assert f.unreachable == {}


# ================================================================ Plan 23 Task 10: the pinned target, the line, the reposition
# Plan 22 run 1 swung 103 attacks at zombie 32404 behind a locked door: the Fight now pins one target, reads the line
# to it off the map's blocked edges, repositions once to a clear neighbour, and marks the target unreachable on a
# second blocked read.
def test_fight_keeps_its_pinned_target_when_a_nearer_zombie_appears(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.5, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and f.target == 7 and f.why["pinned"] is True
    r.answer({"state": "done", "result": swing(True)})
    r.frame(zombies=[zombie(7, 101.5, 200.0), zombie(8, 100.8, 200.0)])   # 8 is nearer
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and f.why["target"] == 7


def test_a_dead_pinned_target_is_dropped_and_the_fight_re_pins_the_nearest(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.5, 200.0), zombie(8, 101.8, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7})
    r.answer({"state": "done", "result": swing(True)})
    r.event("zombie_dead", id=7)
    r.frame(zombies=[zombie(8, 101.8, 200.0)])
    f.step()
    assert r.cmd() == ("attack", {"targetId": 8}) and f.target == 8


def test_a_pinned_target_beyond_disengage_r_is_dropped(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.5, 200.0), zombie(8, 103.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    r.answer({"state": "done", "result": swing(True)})
    r.frame(zombies=[zombie(7, 111.0, 200.0), zombie(8, 103.0, 200.0)])   # 7 at 11 tiles: beyond DISENGAGE_R
    f.step()
    assert P.DISENGAGE_R == 10.0 and f.target == 8 and r.cmd() == ("walkTo", {"x": 103, "y": 200, "gait": "run"})


def test_the_target_keyword_pins_from_the_start(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0), zombie(9, 104.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock, target=9)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 104, "y": 200, "gait": "run"}) and f.why["target"] == 9
    assert f.why["pinned"] is True


def behind_wall_n(at=None):
    """An open grid around the player's square (100, 200), whose north edge is a wall: zombie 7 stands just north of
    it at (100.5, 199.5), within FIGHT_REACH, the line to it crossing the wall."""
    return grid(96, 104, 196, 204, {(100, 200): {"blockN": True}, **(at or {})})


def test_a_target_behind_a_wall_gets_one_reposition_walk_to_the_clear_neighbour_then_an_attack(tmp_path):
    r = Rig(tmp_path)
    r.scan(behind_wall_n())
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 99, "y": 199, "gait": "run"})
    assert f.why["line"] is False and f.why["reposition"] == [99, 199, 0] and f.repositioned is True
    r.answer()
    r.frame(x=99.5, y=199.5, zombies=[zombie(7, 100.5, 199.5)])
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and f.why["line"] is True and f.why["reposition"] is None
    assert [a.type for a in r.acts.history] == ["walkTo", "attack"]
    all_sends_valid(r)


def test_a_second_blocked_read_after_the_reposition_marks_the_target_unreachable(tmp_path):
    r = Rig(tmp_path)
    r.scan(behind_wall_n())
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd()[0] == "walkTo"
    r.answer()
    r.frame(zombies=[zombie(7, 100.5, 199.5)])               # the walk ended, the player still behind the wall
    assert f.step() is None
    assert f.unreachable == {7: r.clock() + UNREACHABLE_S} and f.target is None
    assert [a.type for a in r.acts.history] == ["walkTo"]


def test_a_target_with_no_clear_neighbour_is_marked_unreachable(tmp_path):
    r = Rig(tmp_path)
    walls = {(x, y): {"solid": True} for x in (99, 100, 101) for y in (198, 199, 200) if (x, y) not in
             ((100, 199), (100, 200))}
    r.scan(behind_wall_n(walls))
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    f = Fight(r.world, r.acts, r.clock)
    assert f.step() is None
    assert f.unreachable == {7: r.clock() + UNREACHABLE_S} and r.acts.history == []
    assert f.why["line"] is False and f.why["reposition"] is None


def walled_south():
    """Zombie 7's square (100, 199) closed on every side but the north: its only open neighbour is (100, 198), on the
    far side of the target from a player south of it, the line from (100, 201) crossing the solid (100, 200)."""
    solid = {(x, y): {"solid": True} for x in (99, 100, 101) for y in (199, 200) if (x, y) != (100, 199)}
    return grid(96, 104, 196, 204, solid)


# Task 10's review (M2), ruling P23-Q: `reachable_adjacent` lists the squares open to the target, not to the player; a
# reposition square farther than REPOSITION_R from the player (a detour round a building) is never a reflex.
def test_the_reposition_radius_constant():
    assert P.REPOSITION_R == 2.5


@pytest.mark.parametrize("py, walks", [(201.0, True), (201.4, False)])   # (100, 198)'s centre at 2.5 and 2.9 tiles
def test_a_reposition_square_beyond_reposition_r_of_the_player_is_never_walked_to(tmp_path, py, walks):
    r = Rig(tmp_path)
    r.scan(walled_south())
    r.frame(x=100.5, y=py, zombies=[zombie(7, 100.5, 199.5, me=(100.5, py))])
    f = Fight(r.world, r.acts, r.clock)
    a = f.step()
    assert f.why["line"] is False
    if walks:
        assert a is not None and r.cmd() == ("walkTo", {"x": 100, "y": 198, "gait": "run"})
        assert f.why["reposition"] == [100, 198, 0]
    else:
        assert a is None and r.acts.history == [] and f.unreachable == {7: r.clock() + UNREACHABLE_S}
        assert f.why["reposition"] is None and f.why["marked"] == 7


def test_a_line_over_an_unmapped_end_is_not_read(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)])               # no scan: the map holds neither end
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and f.why["line"] is None


# Task 9's review (Minor): an item marked empty reads `other` through `world.by_use()`, so an empty bottle is spare.
def test_spare_drops_an_empty_marked_bottle(tmp_path):
    r = Rig(tmp_path)
    for iid, ft, wt in [(601, "Base.BaseballBat", 9.0), (602, "Base.Nails", 0.5), (606, "Base.WaterBottle", 6.0)]:
        r.event("item_added", itemId=iid, fullType=ft, weight=wt)
    r.frame(level=3)
    lh = LootHouse(r.world, r.acts, r.clock)
    assert lh.spare() == 602
    r.world.mark_empty(606)
    assert lh.spare() == 606
