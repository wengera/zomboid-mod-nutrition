"""PZAgent_Stance.lua (PZA/1.5, ruling P24-G; Plan 24 Task 9): the skills aim (the combat stance held by setForceAim,
facing a target or a bearing while the auto-walk moves the character: the backpedal) and climb (a hoppable fence at a
walk, vanilla's ISClimbOverFence), the stance's hand-over to an attack and its release by every other skill, on the
lupa host under the fake player (conftest.make_player's p.aim records the stance's members)."""
import math

import pytest

from .conftest import J, make_cell, make_player, make_weapon, make_zombie
from .test_lua_skills import OFF, acts, load, sense, start, states, tick

R2 = 1 / math.sqrt(2)


def ended(lua):
    return lua.eval("PZA.skills.cur") is None


def calls(p):
    return [c[0] for c in p.aim["calls"]]


def aim_world(lua, zx=12.0, zy=20.0, zid=7):
    z = make_zombie(zid, zx, zy)
    sense(lua, [z])
    lua.globals()._cell = make_cell(zombies=[z])
    return z


# ---- aim: the checks --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("args", [{"vx": 0, "vy": 0}, {"vx": 0, "vy": 0, "seconds": 0},
                                  {"vx": "a", "vy": 0, "seconds": 1}, {"vx": 0, "vy": 0, "seconds": 1, "targetId": "z"},
                                  {"vx": 0, "vy": 0, "seconds": 1, "bearing": "n"}])
def test_aim_with_bad_args_is_rejected(lua, fs, args):
    load(lua)
    start(lua, make_player(), "aim", **args)
    assert states(acts(lua, fs)) == [("a1", "rejected", "bad args")]


def test_aim_at_an_unknown_dead_or_far_target_is_rejected_no_target(lua, fs):
    load(lua)
    near, dead, far = make_zombie(7, 12.0, 20.0, dead=False), make_zombie(8, 11, 20, dead=True), make_zombie(9, 30, 20)
    sense(lua, [near, dead, far])
    p = make_player()
    for aid, zid in (("u", 99), ("d", 8), ("f", 9)):
        start(lua, p, "aim", aid=aid, vx=0, vy=0, seconds=1, targetId=zid)
    assert states(acts(lua, fs)) == [("u", "rejected", "no target"), ("d", "rejected", "no target"),
                                     ("f", "rejected", "no target")]
    assert p.aim["calls"] == []


# ---- aim: the stance, the facing and the backpedal ----------------------------------------------------------------

def test_aim_holds_the_stance_faces_the_target_each_tick_and_backpedals_at_a_walk(lua, fs):
    load(lua)
    z = aim_world(lua)
    p = make_player()
    start(lua, p, "aim", vx=-1.0, vy=0.0, seconds=2, targetId=7)
    tick(lua, p)
    g = lua.globals()
    assert calls(p) == ["setForceAim"] and p.aim["force"] is True
    assert ("setForceRun", False) in p.sets and ("setForceSprint", False) in p.sets
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    assert ("setAutoWalk", True) in p.sets
    vec = [v for n, v in p.sets if n == "setAutoWalkDirection"][-1]
    assert (vec.x, vec.y) == pytest.approx((-R2, -R2))                 # world (-1, 0) in input space
    assert g._queue.cleared >= 1 and p.faced == [z]
    tick(lua, p, 3)
    assert p.faced == [z] * 4                                         # the facing every tick
    assert [n for n, _ in p.sets].count("setAutoWalkDirection") == 1   # the vector set once
    assert not ended(lua)
    g._clock["ms"] += 2000
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"d": 0.0, "held": True, "targetDead": False, "heldFrames": 4, "ticks": 4}
    assert calls(p)[-1] == "nullifyAiming" and p.aim["force"] is False
    assert list(p.sets[-3:]) == OFF


def test_aim_at_a_bearing_faces_it_and_a_zero_vector_stands(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=1, bearing=90)
    tick(lua, p, 2)
    assert p.aim["faced"] == [pytest.approx((0.0, 1.0))] * 2           # 90 degrees: world +y, south
    assert ("setAutoWalk", True) not in p.sets and p.faced == []


def test_aim_without_a_target_or_a_bearing_keeps_the_facing(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=1, seconds=1)
    tick(lua, p, 2)
    assert p.aim["faced"] == [] and p.faced == [] and p.aim["force"] is True


def test_aim_whose_target_dies_is_done_at_once_and_released(lua, fs):
    load(lua)
    st = {"dead": False}
    z = J(getOnlineID=lambda s: 7, getX=lambda s: 12.0, getY=lambda s: 20.0, isDead=lambda s: st["dead"],
          getTarget=lambda s: None, isCrawling=lambda s: False, getHealth=lambda s: 1.0)
    sense(lua, [z])
    p = make_player()
    start(lua, p, "aim", vx=-1, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    st["dead"] = True
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"]["targetDead"] is True
    assert calls(p) == ["setForceAim", "nullifyAiming"]


def test_aim_reports_the_stance_lost_when_a_run_cleared_it(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=1)
    tick(lua, p)
    p.aim["force"] = False                                            # the engine cleared it (a run)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"]["held"] is False


def test_aim_held_falls_back_to_is_aiming_without_is_force_aim(lua, fs):
    load(lua)
    p = make_player()
    p.isForceAim = None
    p.aim["aiming"] = False
    start(lua, p, "aim", vx=0, vy=0, seconds=1)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"]["held"] is False


@pytest.mark.parametrize("missing", ["setForceAim", "nullifyAiming"])
def test_aim_without_the_stance_members_fails_not_loaded(lua, fs, missing):
    load(lua)
    p = make_player()
    setattr(p, missing, None)
    start(lua, p, "aim", vx=0, vy=0, seconds=1)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded") and lua.eval("PZA.skills.errors") == 0


def test_aim_with_a_vector_and_no_vector2_fails_not_loaded_but_a_stand_needs_none(lua, fs):
    load(lua)
    lua.globals().Vector2 = None
    p = make_player()
    start(lua, p, "aim", aid="m", vx=1, vy=0, seconds=1)
    tick(lua, p)
    start(lua, p, "aim", aid="s", vx=0, vy=0, seconds=1)
    tick(lua, p)
    assert states(acts(lua, fs)) == [("m", "accepted", ""), ("m", "failed", "not loaded"), ("s", "accepted", "")]
    assert p.aim["force"] is True


def test_a_dead_player_fails_the_aim_dead_and_releases_it(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=5)
    tick(lua, p)
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 0.0)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "dead") and p.aim["force"] is False


class Rec:
    """Records every member the Lua reads off the object it wraps (lupa indexes a J through its __getitem__)."""
    def __init__(self, inner, log, tag):
        self.__dict__["_i"], self.__dict__["_log"], self.__dict__["_tag"] = inner, log, tag

    def __getattr__(self, name):
        return getattr(self._i, name)

    def __getitem__(self, name):
        v = self._i[name]
        if v is not None:
            self._log.append((self._tag, name))
        return v


def test_the_aim_per_tick_reads_five_java_calls_with_a_target_and_allocates_nothing(lua, fs):
    """The cost the file's header claims: after the first tick, one aim tick calls getBodyDamage and
    getOverallBodyHealth (the dead check), the target's isDead, faceThisObject and isAiming (heldFrames, PZA/1.5.4),
    and makes no Vector2."""
    load(lua)
    g = lua.globals()
    log = []
    z = Rec(make_zombie(7, 12.0, 20.0), log, "z")
    sense(lua, [z])
    p = make_player()
    start(lua, p, "aim", vx=-1, vy=0, seconds=10, targetId=7)
    tick(lua, p)
    made = []
    v2 = g.Vector2
    g.Vector2 = J(new=lambda x, y: made.append((x, y)) or v2.new(x, y))
    bd = p.getBodyDamage(p)
    p.getBodyDamage = lambda s: Rec(bd, log, "bd")
    log.clear()
    tick(lua, Rec(p, log, "p"))
    assert sorted(log) == sorted([("p", "getBodyDamage"), ("bd", "getOverallBodyHealth"), ("z", "isDead"),
                                  ("p", "faceThisObject"), ("p", "isAiming")])
    assert made == [] and not ended(lua)


# ---- the stance's hand-over and release ---------------------------------------------------------------------------

def test_a_walk_superseding_the_aim_releases_the_stance(lua, fs):
    load(lua)
    lua.globals()._cell = make_cell(squares={(12, 20, 0): "target"})
    p = make_player()
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5)
    tick(lua, p)
    start(lua, p, "walkTo", aid="w", x=12, y=20)
    assert states(acts(lua, fs))[-2:] == [("aim", "failed", "superseded"), ("w", "accepted", "")]
    assert calls(p) == ["setForceAim", "nullifyAiming"] and lua.eval("PZA.skills.stance.held") is False


def test_an_attack_superseding_the_aim_swings_from_the_held_stance(lua, fs):
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=-1, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    assert calls(p) == ["setForceAim"] and p.aim["force"] is True
    tick(lua, p)
    assert p.attacks == [0] and p.aim["force"] is True                # the swing pressed while the stance holds
    lua.globals()._clock["ms"] += 1500
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("atk", "done", "")
    assert p.aim["force"] is True                                     # kept past the swing for the next aim
    lua.globals()._clock["ms"] += 1999
    tick(lua, p)
    assert p.aim["force"] is True
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    assert calls(p)[-1] == "nullifyAiming" and lua.eval("PZA.skills.stance.held") is False


def test_a_new_aim_after_the_kept_attack_keeps_the_stance_and_a_steer_releases_it(lua, fs):
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1500
    tick(lua, p)
    start(lua, p, "aim", aid="aim2", vx=0, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    assert "nullifyAiming" not in calls(p) and p.aim["force"] is True
    start(lua, p, "steer", aid="flee", vx=1, vy=0, seconds=1, gait="run")
    assert calls(p)[-1] == "nullifyAiming" and p.aim["force"] is False


def test_an_attack_out_of_reach_releases_the_stance_before_its_approach(lua, fs):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[], squares={(14, 20, 0): "zsq"})
    z = make_zombie(7, 14.0, 20.0)
    sense(lua, [z])
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    assert p.aim["force"] is True
    tick(lua, p)
    assert calls(p)[-1] == "nullifyAiming" and p.attacks == []
    assert lua.globals()._queue.adds[-1].Type == "ISWalkToTimedAction"


def test_a_rejected_command_leaves_the_aim_and_its_stance_running(lua, fs):
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    p.combat["hitReaction"] = "HitReaction"
    start(lua, p, "attack", aid="atk", targetId=7)
    start(lua, p, "walkTo", aid="bad", x="no", y=1)
    assert states(acts(lua, fs))[-2:] == [("atk", "rejected", "busy"), ("bad", "rejected", "bad args")]
    assert lua.eval("PZA.skills.cur.type") == "aim" and p.aim["force"] is True and "nullifyAiming" not in calls(p)


def test_a_raising_release_is_counted_and_never_propagates(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5)
    tick(lua, p)

    def boom(s):
        raise RuntimeError("java raised")
    p.nullifyAiming = boom
    start(lua, p, "stop", aid="s")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("s", "done", "")
    assert lua.eval("PZA.skills.errors") >= 1 and lua.eval("PZA.skills.stance.held") is False


# ---- climb ---------------------------------------------------------------------------------------------------------

def lua_queue(lua):
    """A vanilla queue as the game's is, a Lua table (the climb reads its own action in it)."""
    lua.execute("_LQ = { queue = {} }"
                " ISTimedActionQueue = { add = function(a) table.insert(_LQ.queue, a) end,"
                " clear = function(p) _LQ.queue = {} end,"
                " getTimedActionQueue = function(p) return _LQ end,"
                " hasAction = function(a) for _, x in ipairs(_LQ.queue) do if x == a then return true end end"
                " return false end }")


def queued_types(lua):
    return [lua.eval("_LQ.queue[%d].Type" % (i + 1)) for i in range(int(lua.eval("#_LQ.queue")))]


def fence_sq(x, y, north=False, tall=False, fence=True):
    flags = {"TallHoppableN" if tall else "HoppableN"} if north else {"TallHoppableW" if tall else "HoppableW"}
    objs = [J(isHoppable=lambda s: not tall, isTallHoppable=lambda s: tall)] if fence else [J(_cls="IsoObject")]
    return J(getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
             has=lambda s, f: f in flags, fence=objs[0])


def climb_world(lua, x=11, y=20, north=False, tall=False, fence=True, extra=None):
    sq = fence_sq(x, y, north, tall, fence)
    squares = {(x, y, 0): sq}
    squares.update(extra or {})
    lua.globals()._cell = make_cell(squares=squares)
    lua_queue(lua)
    return sq


def pos(p, x, y, z=0):
    st = {"x": x, "y": y, "z": z}
    p.getX, p.getY, p.getZ = (lambda s: st["x"]), (lambda s: st["y"]), (lambda s: st["z"])
    return st


@pytest.mark.parametrize("args", [{"x": 1}, {"x": "a", "y": 2}])
def test_climb_with_bad_args_is_rejected(lua, fs, args):
    load(lua)
    start(lua, make_player(), "climb", **args)
    assert states(acts(lua, fs)) == [("a1", "rejected", "bad args")]


def test_climb_of_a_square_without_a_fence_is_not_hoppable_and_of_no_square_no_square(lua, fs):
    load(lua)
    climb_world(lua, fence=False)
    p = make_player()
    start(lua, p, "climb", aid="n", x=11, y=20)
    start(lua, p, "climb", aid="q", x=40, y=20)
    assert states(acts(lua, fs)) == [("n", "rejected", "not hoppable"), ("q", "rejected", "no square")]


def test_climb_west_fence_from_its_near_square_queues_the_climb_facing_east_at_a_walk_and_is_done_across(lua, fs):
    load(lua)
    sq = climb_world(lua)
    p = make_player()
    at = pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    g = lua.globals()
    assert queued_types(lua) == ["ISClimbOverFence"]
    assert len(g._climbs) == 1 and g._climbs[0][1] is sq.fence and g._climbs[0][2] == "E"
    assert ("setForceRun", False) in p.sets and lua.eval("PZA.motor.wantRun") is False
    tick(lua, p, 3)
    assert not ended(lua)
    at["x"] = 11.4
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"tall": False, "wounds": 0}
    assert list(p.sets[-3:]) == OFF


def test_climb_north_fence_walks_to_the_near_square_first_and_faces_south(lua, fs):
    load(lua)
    climb_world(lua, north=True, extra={(11, 19, 0): J(_cls="near")})
    p = make_player()
    at = pos(p, 13.5, 17.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    assert queued_types(lua) == ["ISWalkToTimedAction", "ISClimbOverFence"]
    assert lua.eval("_LQ.queue[1].sq._cls") == "near" and lua.globals()._climbs[0][2] == "S"
    at["x"], at["y"] = 11.5, 20.2                                     # over the fence, on its far square
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")


def test_climb_from_the_far_side_of_a_north_fence_faces_north(lua, fs):
    load(lua)
    climb_world(lua, north=True)
    p = make_player()
    pos(p, 11.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    assert queued_types(lua) == ["ISClimbOverFence"] and lua.globals()._climbs[0][2] == "N"


def test_climb_without_the_near_square_fails_no_square_and_a_refused_walk_no_path(lua, fs):
    load(lua)
    climb_world(lua, north=True)
    p = make_player()
    pos(p, 11.5, 17.5)
    start(lua, p, "climb", aid="c1", x=11, y=20)
    tick(lua, p)
    climb_world(lua, north=True, extra={(11, 19, 0): J(_cls="near")})
    lua.globals().ISWalkToTimedAction = None
    start(lua, p, "climb", aid="c2", x=11, y=20)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] == "failed"] == [("c1", "failed", "no square"),
                                                                      ("c2", "failed", "no path")]


def test_a_tall_fence_reports_tall_and_the_wounds_a_climb_gave(lua, fs):
    load(lua)
    climb_world(lua, tall=True)
    p = make_player()
    at = pos(p, 10.5, 20.5)
    w = {"s": 0, "b": 0}
    bd = p.getBodyDamage(p)
    bd.getNumPartsScratched, bd.getNumPartsBleeding = (lambda s: w["s"]), (lambda s: w["b"])
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    w["s"], w["b"] = 1, 1
    at["x"] = 11.5
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"] == {"tall": True, "wounds": 2}


def test_a_fall_marked_by_the_outcome_variable_fails_fell_on_the_far_side(lua, fs):
    load(lua)
    climb_world(lua)
    p = make_player()
    at = pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    p.variables["ClimbFenceOutcome"] = "fall"
    tick(lua, p)
    at["x"] = 11.5
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "fell")


def test_a_floor_change_is_a_fall(lua, fs):
    load(lua)
    climb_world(lua)
    p = make_player()
    at = pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    at["x"], at["z"] = 11.5, -1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "fell")


def test_a_climb_gone_from_the_queue_with_the_player_on_the_near_side_fails_after_the_settle(lua, fs):
    load(lua)
    climb_world(lua)
    p = make_player()
    pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    tick(lua, p, 3)
    lua.execute("_LQ.queue = {}")                                     # performed: a tall climb that failed
    tick(lua, p)
    lua.globals()._clock["ms"] += 3999
    tick(lua, p)
    assert not ended(lua)
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "failed")


def test_a_climb_still_queued_past_its_budget_is_interrupted(lua, fs):
    load(lua)
    climb_world(lua)
    p = make_player()
    pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    lua.globals()._clock["ms"] += 20000
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")


def test_a_climb_without_its_vanilla_action_fails_not_loaded(lua, fs):
    load(lua)
    climb_world(lua)
    lua.globals().ISClimbOverFence = None
    p = make_player()
    pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded") and lua.eval("PZA.skills.errors") == 0


def test_a_climb_after_an_aim_releases_the_stance_first(lua, fs):
    load(lua)
    climb_world(lua)
    p = make_player()
    pos(p, 10.5, 20.5)
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5)
    tick(lua, p)
    start(lua, p, "climb", aid="c", x=11, y=20)
    assert calls(p) == ["setForceAim", "nullifyAiming"]
    tick(lua, p)
    assert queued_types(lua) == ["ISClimbOverFence"]


# ---- PZA/1.5.1 (Task 9 fix 1): the kept stance, the climb's done and its corner edge -----------------------------------

def test_a_rejected_attack_during_the_idle_hold_keeps_the_kept_stance(lua, fs):
    """Review minor 4 (the stance): with the stance kept after an attack and no skill running, an attack rejected busy
    during a hit reaction released it; a rejected command now changes nothing, and the hold still ends it."""
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    tick(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    tick(lua, p)
    g = lua.globals()
    g._clock["ms"] += 1500
    tick(lua, p)
    assert ended(lua) and lua.eval("PZA.skills.stance.held") is True
    p.combat["hitReaction"] = "HitReaction"
    start(lua, p, "attack", aid="busy", targetId=7)
    start(lua, p, "walkTo", aid="bad", x="no", y=1)
    assert states(acts(lua, fs))[-2:] == [("busy", "rejected", "busy"), ("bad", "rejected", "bad args")]
    assert "nullifyAiming" not in calls(p) and p.aim["force"] is True
    g._clock["ms"] += 2000
    tick(lua, p)
    assert calls(p)[-1] == "nullifyAiming"


def test_a_walk_crossing_the_edges_line_away_from_the_fence_is_not_a_climb(lua, fs):
    """Review minor 4 (the climb): the far side alone was a half-plane; done needs the player within one square of the
    fence's far square."""
    load(lua)
    climb_world(lua)
    p = make_player()
    at = pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    at["x"], at["y"] = 11.5, 25.5                                     # east of x 11, five squares down the line
    tick(lua, p)
    assert not ended(lua)
    at["x"], at["y"] = 12.5, 21.5                                     # one square off the far square (11, 20)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")


def corner_world(lua, x=11, y=20):
    flags = {"HoppableN", "HoppableW"}
    objs = [J(isHoppable=lambda s: True, isTallHoppable=lambda s: False)]
    sq = J(getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]), has=lambda s, f: f in flags)
    lua.globals()._cell = make_cell(squares={(x, y, 0): sq})
    lua_queue(lua)


def test_a_corner_square_climbs_the_edge_whose_near_square_the_player_stands_nearer(lua, fs):
    """Review minor 4 (the corner): a square with both a north and a west hop flag was always climbed north."""
    load(lua)
    corner_world(lua)
    p = make_player()
    at = pos(p, 10.5, 20.5)                                           # on the west edge's near square
    start(lua, p, "climb", aid="w", x=11, y=20)
    tick(lua, p)
    at["x"], at["y"] = 11.5, 19.5                                     # on the north edge's near square
    start(lua, p, "climb", aid="n", x=11, y=20)
    tick(lua, p)
    assert [c[2] for c in lua.globals()._climbs] == ["E", "S"]


def test_a_climb_reads_its_action_through_vanillas_has_action(lua, fs):
    """Review minor 7: inQueue is vanilla's ISTimedActionQueue.hasAction(action); absent, the action reads gone."""
    load(lua)
    climb_world(lua)
    lua.execute("ISTimedActionQueue.hasAction = nil")
    p = make_player()
    pos(p, 10.5, 20.5)
    start(lua, p, "climb", x=11, y=20)
    tick(lua, p)
    tick(lua, p)
    lua.globals()._clock["ms"] += 4000
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "failed")


# ---- PZA/1.5.4 (Plan 24 Task 9 fix 6, ruling P24-T): the stance held every frame ------------------------------------------

def engine_frame(lua, p, run_key=False):
    """One client frame on 42.21 as jar-reads-2 section 9 reads it, with the option toggleToAim false (the live client's
    options.ini): MovingObjectUpdateSchedulerUpdateBucket.update runs the player's frameStep before its update (L56-L58),
    and the input component's updateToggleToAim clears the force-aim while the toggle-aim handler is muted (L149-L151);
    the update fires OnPlayerUpdate (IsoPlayer.updateInternal2 L2446) before UpdateInputState (L2559), which clears the
    force-aim on a run key (L4393-L4394), sets the input's aiming from it (L4397-L4398) and copies that into the
    character (L2580); OnTick fires after the world update (IngameState.updateInternal L1550, L1573)."""
    p.aim["force"] = False                                            # frameStep: updateToggleToAim
    for h in lua.globals()._updHandlers:                              # OnPlayerUpdate
        h(p)
    if run_key:
        p.aim["force"] = False                                        # UpdateInputState L4394
    p.aim["aiming"] = p.aim["force"]                                  # L4398, then setIsAiming at L2580
    tick(lua, p)                                                      # OnTick


def test_the_stance_set_once_never_reaches_is_aiming_but_the_per_frame_assert_holds_it(lua, fs):
    """The E6 reading reproduced and fixed: aiming read false on every frame of every leg because the force-aim set
    in OnTick was cleared by the next frameStep before UpdateInputState read it; the Motor's OnPlayerUpdate now
    re-asserts it every frame while the stance is held, so isAiming reads true from the first update on."""
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=1, bearing=90)
    engine_frame(lua, p)                                              # the start tick (OnTick): setForceAim once
    for _ in range(5):
        engine_frame(lua, p)
        assert p.isAiming(p) is True and p.isForceAim(p) is True       # E6: false on every frame (set once only)
    assert lua.eval("PZA.motor.wantAim") is True
    assert [c for c in p.aim["calls"] if c[0] == "setForceAim"] == [("setForceAim", True)] * 6
    lua.globals()._clock["ms"] += 1000
    engine_frame(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"d": 0.0, "held": True, "targetDead": False, "heldFrames": 6, "ticks": 6}
    assert lua.eval("PZA.motor.wantAim") is False and calls(p)[-1] == "nullifyAiming"
    engine_frame(lua, p)
    assert p.isAiming(p) is False and calls(p)[-1] == "nullifyAiming"   # released: no assert after the end


def test_a_leg_under_the_auto_walk_keeps_the_stance_at_a_walk_every_frame(lua, fs):
    load(lua)
    z = aim_world(lua)
    p = make_player()
    lua.execute("PZA.motor.want('run')")                              # a run wanted before the leg
    start(lua, p, "aim", vx=-1.0, vy=0.0, seconds=1, targetId=7)
    engine_frame(lua, p)
    assert ("setAutoWalk", True) in p.sets
    n = len(p.sets)
    for _ in range(4):
        engine_frame(lua, p)
        assert p.isAiming(p) is True
    assert ("setForceRun", True) not in p.sets[n:] and ("setForceSprint", True) not in p.sets[n:]
    assert p.faced == [z] * 5
    lua.globals()._clock["ms"] += 1000
    engine_frame(lua, p)
    r = acts(lua, fs)[-1]["result"]
    assert r["held"] is True and r["heldFrames"] == 5 and r["ticks"] == 5


def test_the_motor_holds_the_stance_and_no_run_latch_while_it_is_wanted(lua, fs):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint'); PZA.motor.wantAim = true")
    lua.globals()._updHandlers[0](p)
    assert p.sets == [] and p.aim["calls"] == [("setForceAim", True)]
    lua.execute("PZA.motor.wantAim = false")
    lua.globals()._updHandlers[0](p)
    assert p.sets == [("setForceRun", True), ("setForceSprint", True)] and len(p.aim["calls"]) == 1


def test_held_frames_count_only_the_frames_is_aiming_read_true(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=1)
    engine_frame(lua, p)
    engine_frame(lua, p)
    engine_frame(lua, p, run_key=True)                                # a run key: that frame's aiming cleared
    engine_frame(lua, p, run_key=True)
    engine_frame(lua, p)                                              # re-asserted on the next frame
    lua.globals()._clock["ms"] += 1000
    engine_frame(lua, p)
    r = acts(lua, fs)[-1]["result"]
    assert r["heldFrames"] == 3 and r["ticks"] == 5 and r["held"] is True


def test_the_kept_stance_after_an_attack_is_asserted_until_the_hold_releases_it(lua, fs):
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    engine_frame(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    engine_frame(lua, p)
    assert p.attacks == [0] and p.isAiming(p) is True
    g = lua.globals()
    g._clock["ms"] += 1500
    engine_frame(lua, p)
    assert ended(lua) and lua.eval("PZA.motor.wantAim") is True and p.isAiming(p) is True
    g._clock["ms"] += 2000
    engine_frame(lua, p)
    assert lua.eval("PZA.motor.wantAim") is False
    engine_frame(lua, p)
    assert p.isAiming(p) is False


def test_a_target_dying_reports_held_frames_too(lua, fs):
    load(lua)
    st = {"dead": False}
    z = J(getOnlineID=lambda s: 7, getX=lambda s: 12.0, getY=lambda s: 20.0, isDead=lambda s: st["dead"],
          getTarget=lambda s: None, isCrawling=lambda s: False, getHealth=lambda s: 1.0)
    sense(lua, [z])
    p = make_player()
    start(lua, p, "aim", vx=0, vy=0, seconds=5, targetId=7)
    engine_frame(lua, p)
    engine_frame(lua, p)
    st["dead"] = True
    engine_frame(lua, p)
    r = acts(lua, fs)[-1]["result"]
    assert r["targetDead"] is True and r["heldFrames"] == 1 and r["ticks"] == 1


# ---- PZA/1.5.6 (Plan 24 Task 9 fix 8): the K.start wrapper's release pinned -------------------------------------------

def test_a_flee_started_from_a_kept_stance_releases_it_before_the_first_frame(lua, fs):
    """Mutant M10: the stance kept after an attack (no skill running) is released by the K.start wrapper's release(p)
    when a skill other than an aim or an attack starts; without it the flee would walk strafing under the force-aim."""
    load(lua)
    aim_world(lua, zx=11.0)
    p = make_player(weapon=make_weapon())
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    engine_frame(lua, p)
    start(lua, p, "attack", aid="atk", targetId=7)
    engine_frame(lua, p)
    lua.globals()._clock["ms"] += 1500
    engine_frame(lua, p)
    assert ended(lua) and lua.eval("PZA.motor.wantAim") is True       # done, the stance kept
    start(lua, p, "steer", aid="flee", vx=1, vy=0, seconds=1, gait="run")
    assert lua.eval("PZA.motor.wantAim") is False                     # released by the wrapper, not by a tick
    n = len(p.sets)
    engine_frame(lua, p)                                              # the flee's first tick wants the run (OnTick)
    engine_frame(lua, p)                                              # the next frame's Motor writes the latch
    assert ("setForceRun", True) in p.sets[n:] and p.isAiming(p) is False
