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
PZA15 = ("aim", "climb", "bandage", "rip", "wash", "fill")   # the PZA/1.5 skills (Task 9)
CAPS_14 = tuple(t for t in fakemod.pza1.ACTION_TYPES if t not in PZA15)   # a PZA/1.4 build's hello caps


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

    def __init__(self, tmp_path, now=1000.0, caps=None):
        """`caps` the hello's (default every type the schema names, as the fake mod's DEFAULT_HELLO; CAPS_14 a
        PZA/1.4 build, on which the planner sends none of the PZA/1.5 skills: `World.can`, ruling P24-G)."""
        self.t = {"now": now}
        self.clock = lambda: self.t["now"]
        self.dir = tmp_path
        self.fake = FakeMod(str(tmp_path), clock=self.clock)
        self.tr = FileTransport(str(tmp_path), clock=self.clock)
        self.world = World()
        self.acts = Actions(self.tr, clock=self.clock)
        self.fake.hello(**({} if caps is None else {"caps": list(caps)}))
        self.pump()

    def pump(self):
        lines = self.tr.lines()
        for ln in lines:
            self.world.apply(ln)
        self.acts.pump(lines)

    def frame(self, x=100.0, y=200.0, zombies=(), weapon=BAT, health=100.0, hunger=0.1, thirst=0.1, level=0,
              game_min=480.0, wounds=None, load_max=8.0, fatigue=0.05, hour=8.0, z=0, weight=4.5, world_age=None,
              endurance=1.0, attackers=0, hit_reaction=""):
        """`world_age` (hours) defaults to `game_min / 60`, the day-one clock, so a test that steps `game_min` steps
        the monotonic clock the planner's timers read (fix wave P, I-1); a midnight test passes both. `endurance` is
        the stats group's (DEFAULT_FRAME's 1.0; survival 3's group sprint reads it). `attackers` and `hit_reaction`
        are PZA/1.4's `me.attackers` and `me.hitReaction` (DEFAULT_FRAME's 0 and "", P24-A (h) and (i))."""
        me = dict(DEFAULT_FRAME["me"], x=x, y=y, z=z, hour=hour, attackers=attackers, hitReaction=hit_reaction)
        stats = dict(DEFAULT_FRAME["stats"], hunger=hunger, thirst=thirst, fatigue=fatigue, endurance=endurance)
        body = dict(DEFAULT_FRAME["body"], health=health, **(wounds or {}))
        load = dict(DEFAULT_FRAME["load"], level=level, max=load_max, weight=weight)
        self.fake.frame(me=me, stats=stats, body=body, load=load, weapon=weapon, zombies=list(zombies),
                        gameMin=game_min, worldAge=game_min / 60.0 if world_age is None else world_age)
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
    assert a is not None and r.cmd() == ("walkTo", {"x": 105.5, "y": 200.5, "gait": "run"})
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
    """Named change, ruling P24-A (e): the zombie stood at 1.0 tiles, within POINT_BLANK_R, where no approach walk
    goes now; it stands at 1.5."""
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.5, 200.0)])
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
    assert r.cmd() == ("walkTo", {"x": 101.5, "y": 200.5, "gait": "run"})   # two in a row: re-approach
    assert f.why["approach"] is True
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
    assert r.cmd() == ("walkTo", {"x": 103.5, "y": 200.5, "gait": "run"})


def test_fight_with_no_zombie_sends_nothing(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    assert Fight(r.world, r.acts, r.clock).step() is None and r.acts.history == []


# ================================================================ Flee
def test_flee_steers_every_leg_along_the_weighted_sum_at_a_run(tmp_path):
    """Named change, ruling P24-A (a): the first leg also runs from the densest met window's centre (both zombies
    met, their centroid (103, 201): (-3, -1) / 10), the re-aimed leg from the threats alone."""
    r = Rig(tmp_path)
    zs = [zombie(1, 103.0, 200.0), zombie(2, 103.0, 202.0)]
    r.frame(zombies=zs)
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    typ, args = r.cmd()
    wx, wy = -1.0 / 3.0 - 3.0 / 13.0, -2.0 / 13.0          # the unit vectors from each threat, weighted 1/distance
    wx, wy = wx - 3.0 / 10.0, wy - 1.0 / 10.0               # ... and the met window's centre's (P24-A (a))
    assert f.why["met"] == [103.0, 201.0, 2]
    n = math.hypot(wx, wy)
    assert typ == "steer" and args["gait"] == "run" and args["seconds"] == P.FLEE_S == 3.0
    assert args["vx"] == pytest.approx(wx / n) and args["vy"] == pytest.approx(wy / n)
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


def test_a_leg_points_away_from_the_nearer_threat_where_the_centroid_would_not(tmp_path):
    """P23-AG ruling 3 (every leg, fix round 1): threats at (-3, 0) and (+1, +1) from the player; the centroid's leg
    (+1, -0.5) runs toward the nearer one, the weighted sum of the unit vectors (each times 1/distance) away from it."""
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(1, 97.0, 200.0), zombie(2, 101.0, 201.0)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    wx, wy = 1.0 / 3.0 - 0.5, -0.5
    n0 = math.hypot(wx, wy)
    mx, my = wx + 1.0 / 1.25, wy - 0.5 / 1.25                  # named change, P24-A (a): the first leg runs from the
    n = math.hypot(mx, my)                                       # met window's centre (99, 200.5) too, at 1/distance
    assert args["vx"] == pytest.approx(mx / n) and args["vy"] == pytest.approx(my / n)
    n = n0
    assert args["vx"] * 1.0 + args["vy"] * 1.0 < 0.0             # away from the nearer threat at (+1, +1)
    assert (1.0 * 1.0 + -0.5 * 1.0) > 0.0                        # the centroid's leg would have closed on it
    assert args["gait"] == "sprint" and f.why["turn"] == 0       # unmapped ground is open to the steer (fix 2)
    r.answer()
    r.frame(x=100.0, y=199.0, zombies=[zombie(1, 97.0, 199.0, me=(100.0, 199.0)), zombie(2, 101.0, 200.0,
                                                                                         me=(100.0, 199.0))])
    f.step()                                                     # the second leg is weighted too
    _, args = r.cmd()
    assert args["vx"] == pytest.approx(wx / n) and args["vy"] == pytest.approx(wy / n)


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
    assert r.cmd() == ("walkTo", {"x": 99.5, "y": 200.5, "gait": "walk"})
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
    assert first == ("walkTo", {"x": 99.5, "y": 200.5, "gait": "walk"})
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
    assert r.cmd() == ("walkTo", {"x": 99.5, "y": 200.5, "gait": "walk"}) and r.world.stuck == {}


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
    assert r.world.containers[(102, 200, 0, 0)]["looted"] == {"bandage"}
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


# Task 11 fix 1 (review-t11 I1): the looted mark is per use, on the containers holding that use only, and a loot the
# cap stopped short marks nothing, its square waiting until the carried weight falls.
COUNTER = {"type": "counter", "n": 2, "items": ["Base.WaterBottle", "Base.Apple"]}


def test_a_container_looted_for_water_is_still_looted_for_food(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[COUNTER, CRATE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="water")
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "water", "maxWeight": 8.0})
    r.answer({"state": "done", "result": {"moved": 1, "skipped": 0}})
    lh.observe()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] == {"water"}
    assert r.world.containers[(102, 200, 0, 1)]["looted"] == set()      # the crate holds no water: not marked
    lh.want = "food"
    lh.step()
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "food", "maxWeight": 8.0})
    lh.want = "bandage"
    r.answer({"state": "done", "result": {"moved": 2, "skipped": 0}})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] == {"water", "food"}
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "bandage", "maxWeight": 8.0})


@pytest.mark.parametrize("result", [{"moved": 1, "skipped": 2}, {"moved": 0, "skipped": 1}])
def test_a_loot_the_cap_stopped_short_marks_nothing_and_waits_for_the_load_to_fall(tmp_path, result):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[FRIDGE]), square(106, 200, containers=[dict(FRIDGE, type="counter")])])
    r.frame(weight=7.5)
    lh = LootHouse(r.world, r.acts, r.clock, want="food")
    lh.step()
    assert r.cmd()[1]["x"] == 102
    r.answer({"state": "done", "result": result})
    r.frame(weight=7.5)
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] == set()       # its items may fit later
    assert lh.capped == {(102, 200, 0, "food"): 7.5} and lh.target("food") == (106, 200, 0, 0)
    assert r.cmd()[1]["x"] == 106                                        # not re-sent while the load is the same
    r.answer({"state": "done", "result": {"moved": 1, "skipped": 0}})
    r.frame(weight=7.5)
    assert lh.step() is None and lh.why["container"] is None              # 102 still waits, 106 looted
    r.frame(weight=6.0)                                                  # a drop or a meal: the load fell
    lh.step()
    assert r.cmd()[1]["x"] == 102 and lh.target("food") == (102, 200, 0, 0)
    r.answer({"state": "done", "result": {"moved": 1, "skipped": 0}})
    lh.observe()
    assert lh.capped == {} and r.world.containers[(102, 200, 0, 0)]["looted"] == {"food"}


def test_a_superseded_loot_keeps_its_container(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.frame()
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    lh.step()
    r.answer({"state": "failed", "reason": "superseded"})
    lh.step()
    assert r.world.containers[(102, 200, 0, 0)]["looted"] == set()
    assert r.cmd()[0] == "interact" and len(r.acts.history) == 2


def test_spare_is_the_heaviest_held_item_of_no_kept_use_and_loothouse_never_drops(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    for iid, ft, wt in [(601, "Base.BaseballBat", 9.0), (602, "Base.Plank", 3.0), (603, "Base.Nails", 0.5),
                        (604, "Base.Bread", 5.0), (605, "Base.Crowbar", 4.0), (606, "Base.WaterBottle", 6.0)]:
        r.event("item_added", itemId=iid, fullType=ft, weight=wt)
    r.frame(level=3)
    assert P.spare(r.world) == 602                           # not the bat, the crowbar, the bread or the water
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    assert P.spare(r.world) == 603
    r.event("item_removed", itemId=603, fullType="Base.Nails")
    assert P.spare(r.world) is None
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    assert lh.step() is None and lh.why == {"level": 3, "hold": True}   # Task 12: the drop is Survive's load branch
    r.frame(level=2)
    assert lh.step() is None                                 # level 2: no loot (spec § 9 (1))
    r.frame(level=1)
    lh.step()
    assert r.cmd()[0] == "interact" and [a.type for a in r.acts.history] == ["interact"]
    all_sends_valid(r)


# I1 (the whole-pass review): spec § 9 (1), "a policy stops looting before level 3" -- a loot with filter `all` at
# level 2 took run 1 and run 2 to level 3 and 4 in one interact.
def test_the_load_guard_constants_name_the_levels():
    assert (P.LOOT_MAX_LEVEL, P.DROP_AT, P.DROP_TO) == (1, 3, 2)
    assert not hasattr(P, "LOAD_STOP")


@pytest.mark.parametrize("level, want", [(0, "interact"), (1, "interact"), (2, None), (3, None), (4, None)])
def test_loothouse_loots_only_at_level_0_or_1_and_never_drops(tmp_path, level, want):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(level=level)
    a = LootHouse(r.world, r.acts, r.clock, want="bandage").step()
    assert (a.type if a is not None else None) == want
    if want is None:
        assert r.acts.history == []


def test_from_level_three_nothing_is_sent_until_the_level_is_under_two(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    for iid, wt in [(602, 3.0), (603, 2.0), (604, 1.0)]:
        r.event("item_added", itemId=iid, fullType="Base.Plank", weight=wt)
    lh = LootHouse(r.world, r.acts, r.clock, want="bandage")
    for level in (3, 2, 2, 2):
        r.frame(level=level)
        assert lh.step() is None                             # no loot, and no drop (Survive's load branch drops)
    assert r.acts.history == []
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
    assert {a.type for a in r.acts.history} >= {"walkTo", "attack", "steer", "scan", "interact"}   # drop: Survive's
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
    assert P.DISENGAGE_R == 10.0 and f.target == 8 and r.cmd() == ("walkTo", {"x": 103.5, "y": 200.5, "gait": "run"})


def test_the_target_keyword_pins_from_the_start(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0), zombie(9, 104.0, 200.0)])
    f = Fight(r.world, r.acts, r.clock, target=9)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"}) and f.why["target"] == 9
    assert f.why["pinned"] is True


def behind_wall_n(at=None):
    """An open grid around the player's square (100, 200), whose north edge is a wall: zombie 7 stands just north of
    it at (100.5, 199.5), within FIGHT_REACH, the line to it crossing the wall."""
    return grid(96, 104, 196, 204, {(100, 200): {"blockN": True}, **(at or {})})


def test_a_target_behind_a_wall_gets_one_reposition_walk_to_the_clear_neighbour_then_an_attack(tmp_path):
    """Survival 2 (ruling P23-AJ 5) moved the reposition from (99, 199), its centre 0.71 tiles from the player, inside
    the Lua walk's DONE_R, to (99, 198), the nearest clear neighbour whose centre lies REPOSITION_MIN or more off
    (1.58 tiles; (100, 198) ties it and loses on x)."""
    r = Rig(tmp_path)
    r.scan(behind_wall_n())
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 99.5, "y": 198.5, "gait": "run"})
    assert f.why["line"] is False and f.why["reposition"] == [99, 198, 0] and f.repositioned is True
    r.answer()
    r.frame(x=99.5, y=198.5, zombies=[zombie(7, 100.5, 199.5)])
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
    far side of the target from a player south of it, the line from (100, 201) crossing the solid (100, 200). The
    walk there at 2.5 tiles crow-fly is a detour round the solid block, accepted under ruling P23-R (the radius
    alone; no path search in the base)."""
    solid = {(x, y): {"solid": True} for x in (99, 100, 101) for y in (199, 200) if (x, y) != (100, 199)}
    return grid(96, 104, 196, 204, solid)


# Task 10's review (M2), ruling P23-Q: `reachable_adjacent` lists the squares open to the target, not to the player; a
# reposition square farther than REPOSITION_R from the player (a detour round a building) is never a reflex.
def test_the_reposition_radius_constant():
    assert P.REPOSITION_R == 2.5


@pytest.mark.parametrize("py, walks", [(201.0, True), (201.4, False)])   # (100, 198)'s centre at 2.5 and 2.9 tiles
def test_a_reposition_square_is_walked_to_within_reposition_r_crow_fly_and_never_beyond(tmp_path, py, walks):
    r = Rig(tmp_path)
    r.scan(walled_south())
    r.frame(x=100.5, y=py, zombies=[zombie(7, 100.5, 199.5, me=(100.5, py))])
    f = Fight(r.world, r.acts, r.clock)
    a = f.step()
    assert f.why["line"] is False
    if walks:
        assert a is not None and r.cmd() == ("walkTo", {"x": 100.5, "y": 198.5, "gait": "run"})
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
    assert P.spare(r.world) == 602
    r.world.mark_empty(606)
    assert P.spare(r.world) == 606


# ================================================================ survival 1 fix round 1: the steer reads the map (I4)
def fence_west(boxed=True):
    """An open grid round the player at (100.5, 201.5) with a fence between x 98 and 99 for y 196..206 (`blockW`);
    `boxed`, walls along y 196 and y 207 too (`blockN`), so every heading is blocked within AHEAD_R (fix round 3)."""
    at = {(99, y): {"blockW": True} for y in range(196, 207)}
    if boxed:
        for x in range(90, 111):
            for y in (196, 207):
                at[(x, y)] = dict(at.get((x, y), {}), blockN=True)
    return grid(90, 110, 190, 212, at)


def test_a_fence_ahead_turns_the_heading_to_the_nearest_clear_one(tmp_path):
    r = Rig(tmp_path)
    r.scan(fence_west())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    assert not r.world.line_clear(me, (me[0] - 3.0, me[1]))       # straight away: into the fence
    v = (-math.cos(math.radians(60)), -math.sin(math.radians(60)))   # 30 and -30 still cross it; 60 clears
    assert f.why["turn"] == 60
    assert (args["vx"], args["vy"]) == (pytest.approx(v[0]), pytest.approx(v[1]))
    assert r.world.line_clear(me, (me[0] + 3 * v[0], me[1] + 3 * v[1]))
    assert (P.STEER_PROBE, P.STEER_TURNS, P.STUCK_MOVE) == (3.0, (0, 30, -30, 60, -60, 90, -90), 0.5)


def test_a_leg_that_did_not_move_turns_the_next_from_the_new_away_vector(tmp_path):
    r = Rig(tmp_path)
    r.scan(grid(90, 110, 190, 212))
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    assert r.cmd()[1]["vx"] == pytest.approx(-1.0) and f.why["stuck"] is False and f.why["turn"] == 0
    r.answer()
    r.frame(x=me[0] - 0.4, y=me[1], zombies=[zombie(1, 100.1, 204.5, me=me)])   # 0.4 tiles: stuck; it came south
    f.step()
    _, args = r.cmd()                                         # away (0, -1), turned 30: never the stuck heading's 0
    assert f.why["stuck"] is True and f.why["turn"] == 30
    assert (args["vx"], args["vy"]) == (pytest.approx(0.5), pytest.approx(-math.cos(math.radians(30))))
    r.answer()
    r.frame(x=me[0] - 2.0, y=me[1] - 1.0, zombies=[zombie(1, 101.5, 200.5, me=me)])   # it moved: no turn
    f.step()
    assert f.why["stuck"] is False and f.why["turn"] == 0


def test_a_reposition_walk_targets_the_squares_centre_and_moves_the_character(tmp_path):
    """The X5-2 addendum (T18.4): the reposition named the square's corner, within the Lua walk's DONE_R (1.0) of the
    player on a square touching its own, and ended done without a step. The target (100, 201) behind the player's
    south wall; (99, 201) solid; the reposition is the diagonal (101, 201), its corner 0.71 tiles from the player."""
    r = Rig(tmp_path)
    r.scan(grid(96, 104, 196, 204, {(100, 201): {"blockN": True}, (99, 201): {"solid": True}}))
    me = (100.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(7, 100.5, 201.5, me=me)])
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert f.why["reposition"] == [101, 201, 0]
    assert r.cmd() == ("walkTo", {"x": 101.5, "y": 201.5, "gait": "run"})
    lua_done_r = 1.0                                             # PZAgent_Skills.lua K.DONE_R
    assert math.hypot(101.5 - me[0], 201.5 - me[1]) > lua_done_r >= math.hypot(101 - me[0], 201 - me[1])
    assert P.centre((101, 201)) == (101.5, 201.5) and P.centre((101.9, 201.2)) == (101.5, 201.5)


# ================================================================ survival 1 fix round 2
def test_a_heading_through_a_held_group_turns_to_the_nearest_clear_one(tmp_path):
    """T2 (E1's fight 2 at wall 31.4): the melee target 0.18 tiles behind dominates the 1/d sum, whose away vector
    runs at the far pair 9.5 tiles ahead; the heading turns off the group."""
    r = Rig(tmp_path)
    me = (100.5, 201.5)
    zs = [zombie(1, 100.32, 201.5, me=me), zombie(2, 110.0, 201.3, me=me), zombie(3, 110.0, 201.7, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    assert f.why["turn"] == 30 and f.why["ahead"] == [2, 3]
    assert (args["vx"], args["vy"]) == (pytest.approx(math.cos(math.radians(30))), pytest.approx(0.5))
    assert (P.AHEAD_R, P.AHEAD_CONE) == (9.0, 20.0)


def test_a_threat_within_sprint_r_never_refuses_a_heading(tmp_path):
    r = Rig(tmp_path)
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.0, 201.5, me=me), zombie(2, 102.0, 201.4, me=me),
                                       zombie(3, 102.0, 201.6, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()                                                     # the sum points -x; 1.5 tiles: no refusal
    assert f.why["ahead"] == [] and f.why["turn"] == 0


def test_the_steer_probe_reads_unscanned_ground_as_open(tmp_path):
    """Concern 1: at the scanned ground's edge the away vector into unscanned ground keeps its heading (an unknown
    square is no wall for the steer; the Fight's line keeps the solid-unknown rule)."""
    r = Rig(tmp_path)
    r.scan(grid(100, 110, 190, 212))                             # nothing mapped west of x 100
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    assert f.why["turn"] == 0 and args["vx"] == pytest.approx(-1.0)
    assert not r.world.line_clear(me, (97.5, 201.5)) and r.world.line_clear(me, (97.5, 201.5), unknown_open=True)
    r.scan(grid(96, 99, 190, 212, {(99, y): {"solid": True} for y in range(190, 213)}))   # a known wall still turns
    r.answer()
    r.frame(x=101.5, y=201.5, zombies=[zombie(1, 104.5, 201.5, me=(101.5, 201.5))])
    f.step()
    assert f.why["turn"] not in (0, None)


# ================================================================ survival 1 fix round 3
def test_a_heading_clear_over_ahead_r_wins_over_one_clear_only_at_steer_probe(tmp_path):
    """F3: the fence unboxed: 60 degrees is clear over 3 tiles and runs into the fence after it; 90, a 30-degree turn
    on, is clear over AHEAD_R (9 tiles) and wins."""
    r = Rig(tmp_path)
    r.scan(fence_west(boxed=False))
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    sixty = (-math.cos(math.radians(60)), -math.sin(math.radians(60)))
    assert r.world.line_clear(me, (me[0] + 3 * sixty[0], me[1] + 3 * sixty[1]), unknown_open=True)
    assert not r.world.line_clear(me, (me[0] + 7 * sixty[0], me[1] + 7 * sixty[1]), unknown_open=True)
    assert f.why["turn"] == 90 and f.why["probe"] == P.AHEAD_R
    assert (args["vx"], args["vy"]) == (pytest.approx(0.0), pytest.approx(-1.0))


def test_a_stuck_turn_never_re_chooses_the_stuck_heading(tmp_path):
    """F4: the away vector turned 30 degrees since the stuck leg; its +30 turn is the stuck heading itself, skipped
    (within 15 degrees of it); the -30 turn goes."""
    r = Rig(tmp_path)
    r.scan(grid(85, 115, 185, 218))
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    assert (r.cmd()[1]["vx"], f.why["turn"]) == (pytest.approx(-1.0), 0)
    r.answer()
    v1 = (-math.cos(math.radians(30)), math.sin(math.radians(30)))   # the away vector now: (-1, 0) turned -30
    me2 = (me[0] - 0.2, me[1])                                       # 0.2 tiles: stuck
    r.frame(x=me2[0], y=me2[1], zombies=[zombie(1, me2[0] - 3 * v1[0], me2[1] - 3 * v1[1], me=me2)])
    f.step()
    _, args = r.cmd()
    assert f.why["stuck"] is True and f.why["turn"] == -30
    assert (args["vx"], args["vy"]) == (pytest.approx(-0.5), pytest.approx(math.cos(math.radians(30))))
    assert P.STUCK_SKIP_DEG == 15.0


def long_house(door_open=True):
    """Building 1: room squares x 112..120 by y 200..202, its west door at (112, 201), and open ground x 100..111."""
    from .test_night import CLOSED, OPEN
    door = OPEN if door_open else CLOSED
    sqs = grid(100, 111, 196, 207)
    for x in range(112, 121):
        for y in range(200, 203):
            at_door = (x, y) == (112, 201)
            sqs.append(square(x, y, room="hall", building=1, door=door if at_door else None,
                              blockW=(x == 112) and not (at_door and door["open"]), blockN=(y == 200),
                              edgeW=(x == 112), edgeN=(y == 200)))
    return sqs


@pytest.mark.parametrize("inside, closes", [(118.5, False), (114.5, True)])
def test_the_re_close_goes_only_from_nearer_the_door_than_every_zombie(tmp_path, inside, closes):
    """F2: sheltered 6 tiles inside, a zombie 3 tiles outside the open door with a clear line: the interact would walk
    the character to it, so no close (fix round 1: and on a room square no steer: the trapped hold); 2 tiles inside,
    the close. (Survival 2, P23-AJ 3: the adoption that
    made the plan is gone, so the test gives the Flee a chosen shelter's done plan; its only way out runs at the
    zombie, so the drop steers.)"""
    from agent.base.planner import night as N
    r = Rig(tmp_path)
    r.scan(long_house())
    me = (inside, 201.5)
    z = zombie(1, 109.5, 201.5, me=me)
    r.frame(x=me[0], y=me[1], zombies=[z])
    f = Flee(r.world, r.acts, r.clock)
    f.threats = [r.world.zombies[1]]
    f.plan, f.picked = N.shelter_plan(r.world, 1, door=(112, 201, 0), step="done"), True
    f.step()
    assert r.world.line_clear(me, (109.5, 201.5))
    if closes:
        assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    else:
        assert r.acts.history == [] and f.why["trapped"] == 1


# ================================================================ survival 2 (ruling P23-AJ)
def diagonal_behind_west_wall(at=None):
    """The player on (100, 200), zombie 7 on (101, 199) north-east of it behind a wall on (101, 199)'s west edge,
    which blocks the diagonal line; (101, 200), the player's own east neighbour, is open to the target."""
    return grid(96, 104, 196, 204, {(101, 199): {"blockW": True}, **(at or {})})


def test_a_reposition_square_whose_centre_is_inside_reposition_min_is_never_walked_to(tmp_path):
    """Rule 5 (E2: a centre walk 0.86 tiles off ended `done` on its accept tick, unmoved, inside the Lua walk's DONE_R
    1.0): the adjacent square (101, 200), its centre 1.0 tiles off with a clear line, was the old choice; it is passed
    over and (102, 200), 2.0 off, is walked to; with only the adjacent one open the target is marked unreachable."""
    assert P.REPOSITION_MIN == 1.2
    r = Rig(tmp_path)
    r.scan(diagonal_behind_west_wall())
    me = (100.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(7, 101.5, 199.5, me=me)])
    assert r.world.reachable_adjacent((101.5, 199.5), 0)[0] == (101, 200, 0)
    assert r.world.line_clear((101.5, 200.5), (101.5, 199.5)) and not r.world.line_clear(me, (101.5, 199.5))
    f = Fight(r.world, r.acts, r.clock)
    f.step()
    assert f.why["line"] is False and f.why["reposition"] == [102, 200, 0]
    assert r.cmd() == ("walkTo", {"x": 102.5, "y": 200.5, "gait": "run"})
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    solid = {sq: {"solid": True} for sq in ((100, 198), (101, 198), (102, 198), (102, 199), (102, 200))}
    r2.scan(diagonal_behind_west_wall(solid))
    r2.frame(x=me[0], y=me[1], zombies=[zombie(7, 101.5, 199.5, me=me)])
    assert r2.world.reachable_adjacent((101.5, 199.5), 0) == [(101, 200, 0)]
    f2 = Fight(r2.world, r2.acts, r2.clock)
    assert f2.step() is None and f2.unreachable == {7: r2.clock() + UNREACHABLE_S}
    assert f2.why["reposition"] is None and r2.acts.history == []


def test_the_first_steer_preference_needs_the_three_tile_line_clear_too(tmp_path):
    """Amendment (review-survival-1-fix3.md (a)): Bresenham rasterises the 9-tile and the 3-tile lines along one
    heading over different squares; at 12 degrees the solid (101, 202) blocks the 3-tile line only. The 9-tile pass
    no longer takes a heading the 3-tile rule refuses."""
    r = Rig(tmp_path)
    r.scan(grid(85, 115, 185, 218, {(101, 202): {"solid": True}}))
    me = (100.5, 201.5)
    v = (math.cos(math.radians(12)), math.sin(math.radians(12)))
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, me[0] - 3 * v[0], me[1] - 3 * v[1], me=me)])
    assert r.world.line_clear(me, (me[0] + 9 * v[0], me[1] + 9 * v[1]), unknown_open=True)
    assert not r.world.line_clear(me, (me[0] + 3 * v[0], me[1] + 3 * v[1]), unknown_open=True)
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    assert f.why["turn"] != 0 and f.why["probe"] == P.AHEAD_R
    w = (args["vx"], args["vy"])
    for reach in (3.0, 9.0):
        assert r.world.line_clear(me, (me[0] + reach * w[0], me[1] + reach * w[1]), unknown_open=True)


def two_door_house(north=None, south=None):
    """Building 1's 3 x 3 interior x 110..112, y 200..202 in an open yard x 105..117, y 194..208: a door on the north
    edge of (111, 200) (its record on that room square, blocked while closed) and one on the south edge of (111, 202)
    (its record on the yard square (111, 203) below, where the game keeps a south wall door); both open by default."""
    from .test_night import OPEN
    north = OPEN if north is None else north
    south = OPEN if south is None else south
    at = {}
    for x in range(110, 113):
        for y in range(200, 203):
            at[(x, y)] = {"room": "kitchen", "building": 1, "blockW": x == 110, "blockN": y == 200,
                          "edgeW": x == 110, "edgeN": y == 200}
    at[(111, 200)].update(door=north, blockN=not north["open"])
    for y in range(200, 203):
        at[(113, y)] = {"blockW": True, "edgeW": True}
    for x in range(110, 113):
        at[(x, 203)] = {"blockN": True, "edgeN": True}
    at[(111, 203)] = {"door": south, "blockN": not south["open"], "edgeN": True}   # the live shape: no building
    return grid(105, 117, 194, 208, at)


def test_exit_plan_takes_the_nearest_opening_and_never_one_nearer_the_threats(tmp_path):
    from .test_night import CLOSED
    r = Rig(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    north = [zombie(1, 110.5, 197.5, me=me), zombie(2, 111.5, 197.0, me=me), zombie(3, 112.5, 197.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=north)
    ts = list(r.world.zombies.values())
    e = P.exit_plan(r.world, ts)
    assert (e["building"], e["outer"], e["door"], e["step"], e["opened"]) == (1, (111, 203, 0), None, "walk", False)
    assert e["inner"] == (111, 202, 0) and e["target"] == (111, 204, 0)   # one square on: beyond the walk's DONE_R
    assert P.exit_plan(r.world, ts, refused={(111, 203, 0)}) is None   # the north doorway runs at them
    r.scan(two_door_house(north=CLOSED))
    r.frame(x=me[0], y=me[1], zombies=[zombie(4, 111.5, 205.5, me=me)])
    e = P.exit_plan(r.world, [r.world.zombies[4]])
    assert (e["outer"], e["door"], e["step"], e["target"]) == ((111, 199, 0), (111, 200, 0), "walk", (111, 198, 0))
    r.frame(x=108.5, y=201.5, zombies=[zombie(4, 111.5, 205.5, me=me)])   # outside: no exit
    assert P.exit_plan(r.world, [r.world.zombies[4]]) is None
    r.scan(two_door_house())
    me = (111.5, 202.5)                                            # a zombie far east: both pass; the nearer goes
    r.frame(x=me[0], y=me[1], zombies=[zombie(5, 117.5, 202.5, me=me)])
    assert P.exit_plan(r.world, [r.world.zombies[5]])["outer"] == (111, 203, 0)


def test_exit_plan_refuses_an_opening_whose_line_passes_a_threat_within_exit_clear_r(tmp_path):
    """Fix round 1: the north doorway's line from (111.5, 202.4) passes 1.4 tiles from the zombie, though its
    outside square is no nearer the zombie than the player is (the old guard passes it)."""
    assert P.EXIT_CLEAR_R == 1.5
    r = Rig(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 202.4)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.9, 201.0, me=me)])
    z = r.world.zombies[1]
    assert math.hypot(z["x"] - 111.5, z["y"] - 199.5) >= P.zdist(r.world, z)
    assert P.exit_plan(r.world, [z], refused={(111, 203, 0)}) is None


def test_a_cornered_fight_never_skips_a_marked_zombie_within_mark_free_r(tmp_path):
    """Fix round 1 (the review's I3): zombie 7 marked unreachable at 1.0 tiles: a plain Fight skips it, a cornered
    one (`mark_free_r` 1.5) swings at it; beyond the radius the mark holds."""
    for free, want in ((0.0, None), (1.5, ("attack", {"targetId": 7}))):
        d = tmp_path / str(free)
        d.mkdir()
        r = Rig(d)
        r.frame(zombies=[zombie(7, 101.0, 200.0)])
        f = Fight(r.world, r.acts, r.clock, unreachable={7: r.clock() + 20.0})
        f.mark_free_r = free
        a = f.step()
        assert (r.cmd() if a is not None else None) == want
    r.frame(zombies=[zombie(7, 102.0, 200.0)])                    # 2.0 tiles: the mark holds
    f = Fight(r.world, r.acts, r.clock, unreachable={7: r.clock() + 20.0})
    f.mark_free_r = 1.5
    assert f.blocked() == {7}


def test_a_cornered_fight_swings_at_a_target_within_point_blank_r_whatever_its_line_reads(tmp_path):
    """Fix round 1 (concern 4): a zombie at 0.5 tiles behind the player's north edge (blocked): a plain Fight
    repositions; the cornered Fight (`point_blank`) attacks and marks nothing."""
    assert P.POINT_BLANK_R == 1.0
    for blank in (False, True):
        d = tmp_path / str(blank)
        d.mkdir()
        r = Rig(d)
        r.scan(behind_wall_n())
        me = (100.5, 200.1)
        r.frame(x=me[0], y=me[1], zombies=[zombie(7, 100.5, 199.6, me=me)])
        assert P.line_to(r.world, r.world.zombies[7]) is False
        f = Fight(r.world, r.acts, r.clock)
        f.point_blank = blank
        f.step()
        if blank:
            assert r.cmd() == ("attack", {"targetId": 7}) and f.why["line"] is None and f.unreachable == {}
        else:
            assert r.cmd()[0] == "walkTo" and f.why["line"] is False


def test_an_exit_whose_square_beyond_is_not_open_is_skipped(tmp_path):
    """Fix round 1 (the review's I1): a walk to the outside square itself ends `done` on the room square, a sure
    refusal; the south doorway with a solid square past it is no way out, the north one goes."""
    r = Rig(tmp_path)
    r.scan(two_door_house() + [square(111, 204, solid=True)])
    me = (111.5, 202.4)                                            # the south doorway the nearer, 1.1 tiles off
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 117.5, 202.5, me=me)])
    e = P.exit_plan(r.world, [r.world.zombies[1]])
    assert e["outer"] == (111, 199, 0) and e["target"] == (111, 198, 0)


def test_in_building_reads_a_door_kept_on_the_outdoor_square_as_the_building_s(tmp_path):
    """Survival 3 fix round 1, R2: the scan gives a south-wall door's outdoor square no building; a zombie standing
    in that doorway, (111, 203) of `two_door_house`, is in building 1 (the door fight reads it); one on the yard
    square below is not."""
    r = Rig(tmp_path)
    r.scan(two_door_house())
    r.frame(x=111.5, y=201.5)
    assert r.world.map[(111, 203, 0)].get("building") is None
    assert P.in_building(r.world, zombie(1, 111.5, 203.4), 1)
    assert not P.in_building(r.world, zombie(2, 111.5, 204.4), 1)


# ================================================================ survival 4 (ruling P23-AP 1): the stuck pairs
def stuck_walk(r, e, reason="stuck", me=(100.5, 200.5)):
    """One Explore walk sent from `me` and ended failed `reason` with the player still at `me`; returns its target."""
    r.frame(x=me[0], y=me[1], game_min=480.0)
    e.step()
    typ, args = r.cmd()
    assert typ == "walkTo"
    r.answer({"state": "failed", "reason": reason})
    r.frame(x=me[0], y=me[1], game_min=480.0)
    e.observe()
    return int(args["x"]), int(args["y"])


def test_two_unmoved_stuck_walks_make_a_stuck_run_and_drop_the_place_for_a_rescan(tmp_path):
    """A walk failed `stuck` with the player moved under STUCK_MOVE is a stuck pair from its start square; the second
    in a row makes `stuck_here` and drops the place from `scanned`, so the next choose scans it again."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    r.scan([square(x, y) for x in range(98, 104) for y in range(198, 204)])
    first = stuck_walk(r, e)
    assert r.world.stuck_run["from"] == (100, 200) and r.world.stuck_run["to"] == [first]
    assert not r.world.stuck_here() and e.place() in e.scanned
    second = stuck_walk(r, e)
    assert r.world.stuck_run["to"] == [first, second] and r.world.stuck_here()
    assert e.place() not in e.scanned
    r.frame(x=100.5, y=200.5, game_min=480.0)
    e.step()
    assert r.cmd() == ("scan", {"r": 10})


@pytest.mark.parametrize("end", ["no path", "moved", "done"])
def test_a_walk_failed_otherwise_or_that_moved_is_no_stuck_pair(tmp_path, end):
    """`no path` marks the target stuck but is no pair (the run kept); a `stuck` walk that moved the player 0.6 tiles,
    or a walk that ended done, ends the run."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    e = Explore(r.world, r.acts, r.clock)
    e.step()
    r.answer()
    r.scan([square(x, y) for x in range(98, 104) for y in range(198, 204)])
    first = stuck_walk(r, e)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    e.step()
    target = (int(r.cmd()[1]["x"]), int(r.cmd()[1]["y"]))
    if end == "done":
        r.answer()
    else:
        r.answer({"state": "failed", "reason": "stuck" if end == "moved" else end})
    r.frame(x=101.1 if end == "moved" else 100.5, y=200.5, game_min=480.0)
    e.observe()
    if end == "no path":
        assert r.world.stuck_run["to"] == [first] and target in r.world.stuck
    else:
        assert r.world.stuck_run is None


def test_the_place_is_rescanned_again_at_the_stuck_walk_cap(tmp_path):
    """Fix round 1, R2: the place is dropped from `scanned` at the STUCK_AREA_N-th pair and again at the cap's."""
    import types
    from agent.base import world as W
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    e = Explore(r.world, r.acts, r.clock)
    dropped = []
    for k in range(W.STUCK_AREA_N + W.STUCK_WALK_CAP):
        e.scanned.add(e.place())
        e._walk_ended((90 + k, 190), types.SimpleNamespace(state="failed", reason="stuck"), (100.5, 200.5))
        dropped.append(e.place() not in e.scanned)
    assert dropped == [k + 1 in (W.STUCK_AREA_N, W.STUCK_AREA_N + W.STUCK_WALK_CAP)
                       for k in range(W.STUCK_AREA_N + W.STUCK_WALK_CAP)]


# ================================================================ Plan 24 survival 5 (ruling P24-A)
def test_others_behind_reads_the_listing_beyond_the_target_within_ahead_cone(tmp_path):
    """P24-A (b): beyond the target, within AHEAD_CONE of its bearing and within LISTED_R of the player."""
    assert P.LISTED_R == 12.0 and P.AHEAD_CONE == 20.0
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 108.0, 202.0), zombie(3, 100.0, 207.0),
                     zombie(4, 102.0, 200.2), zombie(5, 113.0, 200.0), zombie(6, 111.0, 203.0)])
    t = r.world.zombies[1]
    # 2 at 8.2 tiles, 14 degrees off: behind; 3 north: no; 4 nearer than the target: no; 5 at 13: unlisted;
    # 6 at 11.4 tiles, 15.3 degrees off: behind
    assert P.others_behind(r.world, 1, t) == [2, 6]
    assert P.others_behind(r.world, 3, r.world.zombies[3]) == []


def test_a_fight_sends_no_approach_walk_at_point_blank(tmp_path):
    """P24-A (e), the close review's I3 (F1's walkTo at 0.49 tiles, lines 599 and 608): two swings not started in a
    row set the approach; with the target within POINT_BLANK_R the flag is cleared and the attack goes."""
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 100.5, 200.0)])
    f = Fight(r.world, r.acts, r.clock)
    for _ in range(2):
        f.step()
        assert r.cmd() == ("attack", {"targetId": 7})
        r.answer({"state": "done", "result": swing(False)})
    f.observe()
    assert f.approach is True
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and f.approach is False and f.why["approach"] is False


def test_no_attack_is_sent_in_a_hit_reaction_and_one_goes_on_the_frame_after_it_clears(tmp_path):
    """P24-A (i), the jar reads #4292 and #4293: a DoAttack starts no swing while the player is in a hit reaction,
    which every zombie attack reaching the damage roll sets; the Lua refuses it `busy`. While the frame's
    `me.hitReaction` names one the Fight sends nothing (`why.hitReaction`); the frame after it clears, the attack.
    A PZA/1.3 frame has no such field: read as none."""
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 101.0, 200.0)], hit_reaction="HitReaction")
    f = Fight(r.world, r.acts, r.clock)
    assert f.step() is None and f.why["hitReaction"] == "HitReaction" and not r.acts.history
    r.frame(zombies=[zombie(7, 101.0, 200.0)], hit_reaction="")
    f.step()
    assert r.cmd() == ("attack", {"targetId": 7}) and "hitReaction" not in f.why
    r.world.me.pop("hitReaction")
    assert P.hit_reaction(r.world) is None


def test_the_first_leg_runs_from_the_densest_met_window_and_the_next_does_not(tmp_path):
    """P24-A (a): five zombies met 11 tiles east a minute ago, out of the listing now; one zombie 3 tiles north. The
    first leg runs from the north one and from the met window's centre: south-west, where the threat alone steers
    due south; the re-aimed leg from the threat alone."""
    r = Rig(tmp_path)
    east = [zombie(10 + i, 111.0, 199.0 + 0.5 * i) for i in range(5)]
    r.frame(zombies=east, game_min=479.0)
    r.advance(30.0)                                          # past the World's ZOMBIE_TTL_S: unlisted, still met
    r.frame(zombies=[zombie(1, 100.0, 197.0)], game_min=480.0)
    assert set(r.world.zombies) == {1} and len(r.world.met) == 6
    f = Flee(r.world, r.acts, r.clock)
    f.step()
    _, args = r.cmd()
    cx, cy = 111.0, 200.0
    wx, wy = (100.0 - cx) / ((100.0 - cx) ** 2 + (200.0 - cy) ** 2), 1.0 / 3.0
    n = math.hypot(wx, wy)
    assert args["vx"] == pytest.approx(wx / n) and args["vy"] == pytest.approx(wy / n) and args["vx"] < 0.0
    assert f.why["met"][2] == 5
    r.answer()
    r.frame(y=202.0, zombies=[zombie(1, 100.0, 197.0, me=(100.0, 202.0))], game_min=480.1)   # the leg moved 2 tiles
    f.step()
    _, args = r.cmd()
    assert (args["vx"], args["vy"]) == (pytest.approx(0.0, abs=1e-12), pytest.approx(1.0)) and "met" not in f.why


def test_steer_now_on_a_room_square_walks_the_exit_at_a_sprint_never_a_steer(tmp_path):
    """P24-A (f), the close review's I4: Survive's group steer (`steer_now`) on a room square with a way out takes the
    exit walk at a sprint; off the room square it steers first, as before."""
    r = Rig(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    north = [zombie(1, 110.5, 197.5, me=me), zombie(2, 111.5, 197.0, me=me), zombie(3, 112.5, 197.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=north)
    f = Flee(r.world, r.acts, r.clock)
    f.steer_now = True
    f.step()
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 204.5, "gait": "sprint"}) and f.exit is not None
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    r2.scan(two_door_house())
    me = (107.5, 201.5)
    r2.frame(x=me[0], y=me[1], zombies=[zombie(1, 107.5, 198.5, me=me)])
    f2 = Flee(r2.world, r2.acts, r2.clock)
    f2.steer_now = True
    f2.step()
    assert r2.cmd()[0] == "steer"


# ================================================================ Plan 24 survival 5 fix 1 (rulings on the concerns)
@pytest.mark.parametrize("farther, behind", [(0.16, False), (0.6, True)])
def test_behind_means_in_the_cone_and_at_least_behind_margin_farther(tmp_path, farther, behind):
    """P24-A fix 1 (5): zombie 2 beside the target in the 20 degree cone, 0.16 tiles farther, is not behind it;
    0.6 tiles farther (BEHIND_MARGIN 0.5), it is."""
    assert P.BEHIND_MARGIN == 0.5
    r = Rig(tmp_path)
    d = 3.0 + farther
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 100.0 + d * math.cos(math.radians(18.0)),
                                                      200.0 + d * math.sin(math.radians(18.0)))])
    assert P.others_behind(r.world, 1, r.world.zombies[1]) == ([2] if behind else [])


def test_an_exit_is_refused_only_for_a_zombie_on_its_square_or_ahead_on_its_line_never_at_the_back(tmp_path):
    """P24-A fix 1 (3): EXIT_CLEAR_R reads the tube of P23-AP 3's cut: within 1.5 tiles of the exit's outside square,
    or ahead of the player within 1.5 of the straight line to it. A zombie 0.6 tiles behind the player (north, the
    exit south) refuses nothing; one 0.6 tiles ahead on the line does; so does one beside the outside square."""
    r = Rig(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    for zs, refused in (([zombie(1, 111.5, 200.9, me=me)], False), ([zombie(1, 111.5, 202.1, me=me)], True),
                        ([zombie(1, 112.6, 203.6, me=me)], True)):
        r.event("zombie_dead", id=1)
        r.frame(x=me[0], y=me[1], zombies=zs)
        e = P.exit_plan(r.world, list(r.world.zombies.values()), refused={(111, 199, 0)})
        assert (e is None) is refused, zs
        if e is not None:
            assert e["outer"] == (111, 203, 0)
    assert P._in_tube((0.0, 0.0), (0.0, 5.0), (0.0, -0.6), 1.5) is False
    assert P._in_tube((0.0, 0.0), (0.0, 5.0), (1.0, 0.1), 1.5) is True
    assert P._in_tube((0.0, 0.0), (0.0, 5.0), (1.2, 5.6), 1.5) is True    # past the end, near the exit's square
    assert P._in_tube((0.0, 0.0), (0.0, 5.0), (1.6, 2.0), 1.5) is False
    assert P._in_tube((0.0, 0.0), (0.0, 1.0), (0.0, -0.4), 1.5) is True   # an exit square 1 tile off: its own 1.5
