"""PZAgent_StanceMelee.lua (PZA/1.8, Plan 28 Task 7a; survival iteration 22, cut 1 of the maneuver layer): the melee
reflex skill `melee {targetId, mode, reach, keepR, shoveR, releaseR, backVx, backVy, seconds, floorSwing}`, which owns
one target from the combat stance to the kill at the client's tick rate, its reflexes in order (first match wins: dead,
the hit reaction, a strike running, out of range and crowd, the time, the target fallen, the knock wait, the shove, the
swing, the back leg after a miss, the close, the stand), its progress lines carrying a result, the frame's act.step,
the stance kept across a same-target re-send, and its per-tick cost. Run on the lupa host over conftest.make_mover's
kinematic fake (the zombie closing at a set speed, the player along its auto-walk at the walk's 2.0 tiles a second,
DoAttack starting an attack that reads isAttackStarted true for N ticks, a scripted zombie attack setting the hit
reaction after a windup). Each reflex has a positive case and a falsifier; the mutants of the task report (each reflex
a tick late, its distance test inverted, its order swapped with its neighbour's) each fail one of them."""
import json
import math
import os

import pytest

from agent.base import pza1
from .conftest import ROOT, TICK_MS, J, make_cell, make_mover, make_zombie, step_world, zdist, lua_file
from .test_lua_skills import acts, load, sense, start, states, tick
from .test_lua_stance import Rec

ARGS = {"targetId": 7, "mode": "strike", "reach": 1.4, "keepR": 2.5, "shoveR": 1.1, "releaseR": 2.75,
        "backVx": -1.0, "backVy": 0.0, "seconds": 2.5}
STRIKES = ("face", "swing", "shove", "stomp", "floor")
R2 = 1 / math.sqrt(2)
SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")


def world(lua, **kw):
    """The runner and its skills loaded, a mover (player, zombie 7, world) and Sense stubbed with the zombie."""
    load(lua)
    p, z, w = make_mover(**kw)
    sense(lua, [z])
    return p, z, w


def go(lua, p, aid="m1", **over):
    a = dict(ARGS)
    a.update(over)
    start(lua, p, "melee", aid=aid, **a)


def run(lua, p, w, n=1, stop=None):
    """n client ticks: the fake engine's update, the clock, then the runner's tick (OnTick); stops early when stop()."""
    for _ in range(n):
        step_world(w, p)
        lua.globals()._clock["ms"] += TICK_MS
        tick(lua, p)
        if stop is not None and stop():
            return


def cur_step(lua):
    return lua.eval("PZA.skills.cur and PZA.skills.cur.st.step")


def ended(lua):
    return lua.eval("PZA.skills.cur") is None


def progress(lua, fs, aid="m1"):
    return [a for a in acts(lua, fs) if a["aid"] == aid and a["state"] == "progress"]


def step_seq(lua, fs, aid="m1"):
    return [a["result"]["step"] for a in progress(lua, fs, aid)]


def last(lua, fs):
    return acts(lua, fs)[-1]


def calls(p):
    return [c[0] for c in p.aim["calls"]]


def walk_dir(p):
    v = [v for n, v in p.sets if n == "setAutoWalkDirection"][-1]
    return v.x, v.y


# ---- the command's checks ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("over", [{"mode": "kick"}, {"mode": 3}, {"seconds": 0}, {"reach": "x"}, {"reach": -1},
                                  {"floorSwing": "yes"}, {"targetId": "z"}, {"backVx": None}])
def test_melee_with_bad_args_is_rejected(lua, fs, over):
    p, z, w = world(lua)
    a = dict(ARGS)
    a.update(over)
    a = {k: v for k, v in a.items() if v is not None}
    start(lua, p, "melee", aid="m1", **a)
    assert states(acts(lua, fs)) == [("m1", "rejected", "bad args")]


def test_an_unknown_or_dead_target_is_no_target_a_far_one_too_far_and_a_strike_without_a_weapon_no_weapon(lua, fs):
    p, z, w = world(lua, zx=15.0)                                     # 5 tiles off, beyond releaseR 2.75
    go(lua, p, aid="u", targetId=99)
    go(lua, p, aid="f")
    w["zdead"] = True
    go(lua, p, aid="d")
    w["zdead"], w["zx"] = False, 11.0
    p2, _, _ = make_mover(weapon=None)
    p2.getX, p2.getY = p.getX, p.getY
    go(lua, p2, aid="n")
    go(lua, p2, aid="s", mode="shove")                                # the shove needs no weapon
    assert states(acts(lua, fs)) == [("u", "rejected", "no target"), ("f", "rejected", "too far"),
                                     ("d", "rejected", "no target"), ("n", "rejected", "no weapon"),
                                     ("s", "accepted", "")]


@pytest.mark.parametrize("missing", ["setForceAim", "nullifyAiming", "faceThisObject", "DoAttack", "setDoShove",
                                     "setAutoWalk", "setAutoWalkDirection"])
def test_the_melee_needs_its_members_on_its_first_tick_or_fails_not_loaded(lua, fs, missing):
    p, z, w = world(lua)
    setattr(p, missing, None)
    go(lua, p)
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "not loaded") and lua.eval("PZA.skills.errors") == 0


def test_the_melee_without_vector2_fails_not_loaded(lua, fs):
    p, z, w = world(lua)
    lua.globals().Vector2 = None
    go(lua, p)
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "not loaded")


# ---- 1: dead ---------------------------------------------------------------------------------------------------------

def test_a_target_that_dies_ends_the_melee_done_dead_with_a_kill_and_its_counts(lua, fs):
    p, z, w = world(lua, zx=12.0)
    go(lua, p)
    run(lua, p, w, 5)
    assert not ended(lua)                                             # the falsifier: alive, it runs on
    w["zdead"], w["zhp"] = True, 0.0
    run(lua, p, w)
    a = last(lua, fs)
    assert (a["state"], a["reason"]) == ("done", "")
    r = a["result"]
    assert r["end"] == "dead" and r["kill"] is True and r["hp0"] == 1.0 and r["hp1"] == 0.0
    assert r["swings"] == 0 and r["hits"] == 0 and r["dMin"] == pytest.approx(2.0)
    assert r["steps"] == {"stand": 5}
    assert lua.eval("PZA.skills.stance.held") is False and lua.eval("PZA.motor.wantAim") is False


def test_a_dead_player_fails_the_melee_dead_and_releases_the_stance(lua, fs):
    p, z, w = world(lua)
    go(lua, p)
    run(lua, p, w, 3)
    assert p.aim["force"] is True
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 0.0)
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "dead")
    assert p.aim["force"] is False and lua.eval("PZA.motor.wantAim") is False


# ---- 2: the hit reaction -----------------------------------------------------------------------------------------

def test_no_press_goes_on_any_tick_reading_a_hit_reaction_and_each_run_of_it_counts_one_hit(lua, fs):
    p, z, w = world(lua, zx=11.2)                                     # within the reach 1.4
    p.combat["hitReaction"] = "Bite"
    go(lua, p)
    run(lua, p, w, 12)
    assert w["presses"] == [] and cur_step(lua) == "hit"
    p.combat["hitReaction"] = ""
    run(lua, p, w)                                                    # the face
    assert w["presses"] == [] and cur_step(lua) == "face"
    p.combat["hitReaction"] = "Bite"                                  # a second reaction between the face and the press
    run(lua, p, w, 3)
    assert w["presses"] == []
    p.combat["hitReaction"] = ""
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1
    assert progress(lua, fs)[-1]["result"]["hits"] == 2


def test_without_a_hit_reaction_the_press_comes_on_the_second_tick(lua, fs):
    """The falsifier of the hit hold: the same geometry with no reaction presses a tick after the face."""
    p, z, w = world(lua, zx=11.2)
    go(lua, p)
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["tick"] == 2 and w["presses"][0]["shove"] is False


# ---- 3: a strike running -----------------------------------------------------------------------------------------

def test_no_second_press_while_the_strike_runs_and_its_knockdown_is_read_at_its_end(lua, fs):
    p, z, w = world(lua, zx=11.2, attack_ticks=20)

    def knock(wd, shove):
        wd["knocked"] = True
    w["on_attack"] = knock
    go(lua, p)
    run(lua, p, w, 15)
    assert len(w["presses"]) == 1 and cur_step(lua) == "swing"
    run(lua, p, w, 8)                                                 # the attack ends; the result read a tick after
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"
    assert progress(lua, fs)[-1]["result"]["knockdowns"] == 1


def test_a_strike_that_leaves_the_target_standing_and_unhurt_is_a_miss_and_the_back_leg_follows(lua, fs):
    p, z, w = world(lua, zx=11.3, attack_ticks=10)
    go(lua, p)
    run(lua, p, w, 14)
    assert len(w["presses"]) == 1 and cur_step(lua) == "back"
    assert step_seq(lua, fs) == ["face", "swing", "back"]              # the back leg on the result's own tick


def test_a_strike_that_hurt_the_target_is_no_miss_and_the_swing_goes_again(lua, fs):
    """The falsifier of the miss: a health fall leaves the target hurt, so no back leg, the swing again."""
    p, z, w = world(lua, zx=11.3, attack_ticks=10)

    def hurt(wd, shove):
        wd["zhp"] -= 0.2
    w["on_attack"] = hurt
    go(lua, p)
    run(lua, p, w, 14)
    assert cur_step(lua) in ("face", "swing") and "back" not in step_seq(lua, fs)


def test_a_hit_during_a_running_strike_reads_hit_and_counts_it(lua, fs):
    """The order of 2 before 3: a reaction while the swing runs is the hit step, counted, the swing's end still read."""
    p, z, w = world(lua, zx=11.2, attack_ticks=30)
    go(lua, p)
    run(lua, p, w, 3)
    assert cur_step(lua) == "swing"
    p.combat["hitReaction"] = "Bite"
    run(lua, p, w)
    assert cur_step(lua) == "hit" and progress(lua, fs)[-1]["result"]["hits"] == 1


def test_a_target_dying_in_a_hit_reaction_ends_done_dead(lua, fs):
    """The order of 1 before 2."""
    p, z, w = world(lua, zx=12.3)
    go(lua, p)
    run(lua, p, w, 2)
    p.combat["hitReaction"] = "Bite"
    w["zdead"] = True
    run(lua, p, w)
    assert (last(lua, fs)["state"], last(lua, fs)["result"]["end"]) == ("done", "dead")


# ---- 4: out of range and crowd -----------------------------------------------------------------------------------

def test_a_target_beyond_release_r_fails_out_of_range(lua, fs):
    p, z, w = world(lua, zx=12.5)
    go(lua, p)
    run(lua, p, w, 2)
    assert not ended(lua)
    w["zx"] = 12.8                                                    # 2.8 > releaseR 2.75
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "out of range") and p.aim["force"] is False


def crowd_world(lua, other_floor=False, other_d=0.5):
    p, z, w = world(lua, zx=12.0)
    o = make_zombie(8, 10.0 + other_d, 20.0)
    if other_floor:
        o.isOnFloor = lambda s: True
    g = lua.globals()
    g._o, g._z = o, z
    lua.execute("PZA.sense.zobj = { [7] = _z, [8] = _o }")
    lua.execute("PZA.sense.last = { zombies = { { id = 8, dist = %r }, { id = 7, dist = 2.0 } } }" % other_d)
    return p, z, w


def test_another_standing_zombie_within_stand_r_fails_crowd_with_its_id_and_distance(lua, fs):
    p, z, w = crowd_world(lua)
    go(lua, p)
    run(lua, p, w)
    a = last(lua, fs)
    assert (a["state"], a["reason"]) == ("failed", "crowd") and a["result"] == {"id": 8, "d": 0.5}


@pytest.mark.parametrize("floor, d", [(True, 0.5), (False, 0.7)])
def test_a_fallen_or_a_farther_other_zombie_is_no_crowd(lua, fs, floor, d):
    p, z, w = crowd_world(lua, other_floor=floor, other_d=d)
    go(lua, p)
    run(lua, p, w, 3)
    assert not ended(lua)


def test_a_strike_running_beyond_release_r_is_held_to_its_end_then_out_of_range(lua, fs):
    """The order of 3 before 4: a swing in flight is never cut by the range."""
    p, z, w = world(lua, zx=11.2, attack_ticks=20)
    go(lua, p)
    run(lua, p, w, 3)
    w["zx"] = 13.0
    run(lua, p, w)
    assert not ended(lua) and cur_step(lua) == "swing"
    run(lua, p, w, 30, stop=lambda: ended(lua))
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "out of range")


def test_out_of_range_at_the_time_end_fails_out_of_range(lua, fs):
    """The range read before the time end (4's order)."""
    p, z, w = world(lua, zx=12.3)
    go(lua, p, seconds=1.0)
    run(lua, p, w)
    lua.globals()._clock["ms"] += 1000
    w["zx"] = 13.0
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "out of range")


def test_the_time_end_comes_before_a_fallen_targets_stomp(lua, fs):
    """The time end before 5."""
    p, z, w = world(lua, zx=10.4)
    go(lua, p, seconds=1.0, mode="finish")
    w["floor"] = True
    run(lua, p, w)                                                    # the stomp's face
    assert cur_step(lua) == "stomp"
    lua.globals()._clock["ms"] += 1000
    run(lua, p, w)
    assert last(lua, fs)["result"]["end"] == "time" and w["presses"] == []


# ---- 5: the target fallen --------------------------------------------------------------------------------------

def test_the_stomp_faces_on_the_first_tick_reading_on_floor_and_presses_the_shove_pair_the_next(lua, fs):
    p, z, w = world(lua, zx=10.4, zspeed=0.0)
    go(lua, p, mode="finish", floorSwing=False)
    w["floor"] = True
    run(lua, p, w)
    assert cur_step(lua) == "stomp" and w["presses"] == [] and p.faced[-1] is z
    assert p.aim["force"] is False                                    # the press goes unaimed
    run(lua, p, w)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True and w["presses"][0]["aiming"] is False


def test_with_floor_swing_and_a_weapon_in_reach_the_fallen_target_takes_the_floor_swing(lua, fs):
    """The falsifier of the stomp: floorSwing true with a weapon and the target in reach swings the weapon (no shove
    flag)."""
    p, z, w = world(lua, zx=11.0)
    go(lua, p, mode="finish", floorSwing=True)
    w["floor"] = True
    run(lua, p, w, 2)
    assert cur_step(lua) == "floor" and len(w["presses"]) == 1 and w["presses"][0]["shove"] is False


def test_a_fallen_target_beyond_stomp_r_is_walked_to_unaimed_and_then_stomped(lua, fs):
    p, z, w = world(lua, zx=11.2)
    go(lua, p, mode="finish")
    w["floor"] = True
    run(lua, p, w)
    assert cur_step(lua) == "stomp_walk" and p.motor["autoWalk"] is True and p.aim["force"] is False
    assert walk_dir(p) == pytest.approx((R2, R2))                    # world +x in input space
    run(lua, p, w, 40, stop=lambda: len(w["presses"]) > 0)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True and w["presses"][0]["d"] < 0.5


def test_a_stomp_walk_past_its_budget_fails_out_of_reach(lua, fs):
    p, z, w = world(lua, zx=11.2)
    p.setAutoWalkDirection = lambda s, v: p.sets.append(("setAutoWalkDirection", v))   # the walk never moves
    go(lua, p, mode="finish", seconds=10)
    w["floor"] = True
    run(lua, p, w)
    lua.globals()._clock["ms"] += 4000
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "out of reach")


def test_a_finish_whose_target_stands_fails_stood(lua, fs):
    p, z, w = world(lua, zx=11.0)
    go(lua, p, mode="finish")
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "stood")


# ---- 6: the knock wait -----------------------------------------------------------------------------------------

def test_a_knockdown_not_yet_on_the_floor_is_waited_on_then_stomped_on_the_first_floor_tick(lua, fs):
    p, z, w = world(lua, zx=10.4, attack_ticks=6)

    def knock(wd, shove):
        wd["knocked"] = True
    w["on_attack"] = knock
    go(lua, p, mode="shove")
    run(lua, p, w, 10)
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"
    run(lua, p, w, 20)
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"   # no press while it falls
    w["floor"] = True
    run(lua, p, w)
    assert cur_step(lua) == "stomp"
    run(lua, p, w)
    assert len(w["presses"]) == 2 and w["presses"][1]["shove"] is True


# ---- 7: the shove ------------------------------------------------------------------------------------------------

def test_shove_mode_shoves_at_shove_r_and_never_beyond(lua, fs):
    p, z, w = world(lua, zx=11.3, chasing=False)
    go(lua, p, mode="shove")
    run(lua, p, w, 3)
    assert w["presses"] == [] and cur_step(lua) == "close"            # beyond shoveR 1.1: closed on, not shoved
    w["zx"] = 11.05
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True


def test_a_chasing_target_closing_to_shove_r_is_shoved_in_strike_mode(lua, fs):
    """P28-B1 inside the reflex: with the reach (0.8) under shoveR, a chasing target closing inside 1.1 is shoved."""
    p, z, w = world(lua, zx=11.6, zspeed=1.2, chasing=True)
    go(lua, p, reach=0.8)
    run(lua, p, w, 60, stop=lambda: len(w["presses"]) > 0)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True and w["presses"][0]["d"] <= 1.1


def test_an_idle_target_at_the_same_distance_is_not_shoved(lua, fs):
    """The falsifier of the early shove: an idle target inside shoveR in strike mode is not chasing: closed on and
    swung at within the reach, never shoved."""
    p, z, w = world(lua, zx=11.0, chasing=False)
    go(lua, p, reach=0.8)
    run(lua, p, w, 30, stop=lambda: len(w["presses"]) > 0)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is False and w["presses"][0]["d"] <= 0.8


def test_after_a_miss_the_shove_goes_at_point_blank(lua, fs):
    """P28-B2 inside the reflex: a swing that left the target standing and unhurt, then the back leg, then the shove
    when the target closes to shoveR."""
    p, z, w = world(lua, zx=11.3, zspeed=0.0, attack_ticks=8)
    go(lua, p, seconds=10)
    run(lua, p, w, 40, stop=lambda: cur_step(lua) == "back")
    assert cur_step(lua) == "back"
    w["zspeed"] = 4.0                                                 # it follows faster than the walk
    run(lua, p, w, 80, stop=lambda: len(w["presses"]) > 1)
    assert [x["shove"] for x in w["presses"]] == [False, True] and w["presses"][1]["d"] <= 1.1
    assert "back" in step_seq(lua, fs)


def test_a_chasing_target_lunging_inside_shove_r_in_one_tick_is_shoved_not_swung(lua, fs):
    """The order of 7 before 8 (P28-B1): F11's chaser read 1.29 then 0.63 a planner tick later; here 1.6 then 1.0 in one
    client tick, inside the reach and shoveR, chasing and closing: the shove."""
    p, z, w = world(lua, zx=11.6, chasing=True)
    go(lua, p)
    run(lua, p, w, 2)
    assert cur_step(lua) == "stand"
    w["zx"] = 11.0
    run(lua, p, w, 2)
    assert cur_step(lua) == "shove" and len(w["presses"]) == 1 and w["presses"][0]["shove"] is True


# ---- 8: the swing ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("speed", [0.5, 1.2, 2.0])
def test_the_swing_faces_inside_the_reach_and_presses_once_a_tick_later_unaimed(lua, fs, speed):
    p, z, w = world(lua, zx=12.6, zspeed=speed)
    go(lua, p)
    faces = []
    for _ in range(200):
        run(lua, p, w)
        if cur_step(lua) == "face" and not faces:
            faces.append(zdist(w))
        if w["presses"]:
            break
    one = speed * TICK_MS / 1000.0
    assert len(w["presses"]) == 1 and len(faces) == 1
    assert ARGS["reach"] - one - 1e-9 <= faces[0] <= ARGS["reach"]
    assert w["presses"][0]["d"] >= ARGS["reach"] - 2 * one - 1e-9 and w["presses"][0]["aiming"] is False
    assert w["presses"][0]["shove"] is False


def test_the_press_waits_facing_while_an_attack_already_runs(lua, fs):
    """A melee started while the engine's attack runs (a superseded attack's swing): the face, then no press while
    isAttackStarted reads true (the engine would drop it, #4292), the press on the first tick after."""
    p, z, w = world(lua, zx=11.2)
    w["attack"] = 10
    go(lua, p)
    run(lua, p, w, 8)
    assert w["presses"] == [] and cur_step(lua) == "face"
    run(lua, p, w, 3, stop=lambda: len(w["presses"]) > 0)
    assert len(w["presses"]) == 1 and w["presses"][0]["tick"] == 10


def test_a_chasing_target_held_beyond_the_reach_is_never_swung_at(lua, fs):
    """The falsifier of the swing's distance test: a target that stays at 1.6 (beyond the reach 1.4) and chases is
    stood against, never pressed."""
    p, z, w = world(lua, zx=11.6, zspeed=0.0, chasing=True)
    go(lua, p)
    run(lua, p, w, 60)
    assert w["presses"] == [] and cur_step(lua) == "stand"


def test_a_reach_of_0_takes_the_weapons_reach(lua, fs):
    """reach 0 lets the Lua use K.reachOf (the bat's 1.25 x 0.9 = 1.125)."""
    p, z, w = world(lua, zx=11.2)
    go(lua, p, reach=0)
    run(lua, p, w, 4)
    assert w["presses"] == [] and cur_step(lua) == "stand"
    w["zx"] = 11.12                                                   # inside 1.125, outside shoveR 1.1
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is False


# ---- 9: the back leg ---------------------------------------------------------------------------------------------

def test_after_a_miss_the_back_leg_walks_the_heading_in_the_stance_facing_the_target_until_keep_r(lua, fs):
    p, z, w = world(lua, zx=11.3, zspeed=0.0, attack_ticks=8)
    go(lua, p, backVx=0.0, backVy=-1.0, seconds=10)
    run(lua, p, w, 12)
    assert cur_step(lua) == "back" and p.motor["autoWalk"] is True and p.aim["force"] is True
    assert walk_dir(p) == pytest.approx((R2, -R2))                   # world (0, -1) in input space
    n = len(p.faced)
    run(lua, p, w, 5)
    assert len(p.faced) == n + 5 and all(f is z for f in p.faced[n:])
    run(lua, p, w, 120, stop=lambda: cur_step(lua) != "back")
    assert zdist(w) >= ARGS["keepR"] and cur_step(lua) == "stand" and p.motor["autoWalk"] is False


def test_a_back_heading_of_zero_stands_in_the_stance(lua, fs):
    p, z, w = world(lua, zx=11.3, zspeed=0.0, attack_ticks=8)
    go(lua, p, backVx=0.0, backVy=0.0)
    run(lua, p, w, 14)
    assert cur_step(lua) == "back" and p.motor["autoWalk"] is False and p.aim["force"] is True


def test_an_idle_target_missed_is_backed_off_from_not_closed_on(lua, fs):
    """The order of 9 before 10: after a miss an idle target in the reach's band is backed off from, never walked to."""
    p, z, w = world(lua, zx=11.3, zspeed=0.0, chasing=False, attack_ticks=8)
    go(lua, p, seconds=10)
    run(lua, p, w, 13)
    assert cur_step(lua) == "back" and walk_dir(p) == pytest.approx((-R2, -R2))   # world (-1, 0), away from it


# ---- 10: the close; 11: the stand ----------------------------------------------------------------------------------

def test_an_idle_target_beyond_the_reach_is_closed_on_at_a_walk_in_the_stance_and_swung_at_within_it(lua, fs):
    p, z, w = world(lua, zx=12.3, chasing=False)
    go(lua, p)
    run(lua, p, w)
    assert cur_step(lua) == "close" and p.motor["autoWalk"] is True and p.aim["force"] is True
    assert walk_dir(p) == pytest.approx((R2, R2)) and lua.eval("PZA.motor.wantRun") is False
    run(lua, p, w, 100, stop=lambda: len(w["presses"]) > 0)
    assert len(w["presses"]) == 1 and w["presses"][0]["d"] <= ARGS["reach"] and w["presses"][0]["aiming"] is False
    assert step_seq(lua, fs)[:3] == ["close", "face", "swing"]


def test_a_chasing_target_beyond_the_reach_is_stood_against_facing_it_with_no_walk(lua, fs):
    """The falsifier of the close: a chasing target is let come (the stand), never walked to."""
    p, z, w = world(lua, zx=12.3, chasing=True, zspeed=0.0)
    go(lua, p)
    run(lua, p, w, 6)
    assert cur_step(lua) == "stand" and ("setAutoWalk", True) not in p.sets and p.aim["force"] is True
    assert p.faced == [z] * 6


# ---- 12: the time ------------------------------------------------------------------------------------------------

def test_seconds_passed_with_no_strike_ends_done_time_and_releases_the_stance(lua, fs):
    p, z, w = world(lua, zx=12.3, zspeed=0.0)
    go(lua, p, seconds=1.0)
    run(lua, p, w, 3)
    assert not ended(lua)
    lua.globals()._clock["ms"] += 1000
    run(lua, p, w)
    a = last(lua, fs)
    assert (a["state"], a["result"]["end"], a["result"]["kill"]) == ("done", "time", False)
    assert calls(p)[-1] == "nullifyAiming" and lua.eval("PZA.skills.stance.held") is False


def test_a_running_strike_holds_the_time_end_until_it_ends(lua, fs):
    p, z, w = world(lua, zx=11.2, attack_ticks=30)
    go(lua, p, seconds=0.1)
    run(lua, p, w, 2)                                                 # the face, the press
    lua.globals()._clock["ms"] += 1000
    run(lua, p, w, 5)
    assert not ended(lua) and cur_step(lua) == "swing"
    run(lua, p, w, 40, stop=lambda: ended(lua))
    assert last(lua, fs)["result"]["end"] == "time" and last(lua, fs)["result"]["swings"] == 1


# ---- the stance across re-sends -----------------------------------------------------------------------------------

def test_a_same_target_resend_keeps_the_stance(lua, fs):
    p, z, w = world(lua, zx=12.3)
    go(lua, p, aid="m1")
    run(lua, p, w, 3)
    go(lua, p, aid="m2")
    run(lua, p, w, 3)
    assert states(acts(lua, fs))[-2:] == [("m1", "failed", "superseded"), ("m2", "accepted", "")] or \
        ("m1", "failed", "superseded") in states(acts(lua, fs))
    assert "nullifyAiming" not in calls(p) and p.aim["force"] is True


def test_another_target_or_another_skill_releases_the_stance(lua, fs):
    p, z, w = world(lua, zx=12.3)
    z8 = make_zombie(8, 12.0, 21.0)
    sense(lua, [z, z8])
    go(lua, p, aid="m1")
    run(lua, p, w, 2)
    go(lua, p, aid="m2", targetId=8)
    assert calls(p)[-1] == "nullifyAiming"
    run(lua, p, w, 2)
    assert p.aim["force"] is True
    start(lua, p, "steer", aid="s", vx=1, vy=0, seconds=1)
    assert calls(p)[-1] == "nullifyAiming" and p.aim["force"] is False


def test_an_aim_superseded_by_a_melee_keeps_the_stance(lua, fs):
    p, z, w = world(lua, zx=12.3)
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    run(lua, p, w)
    go(lua, p)
    run(lua, p, w, 2)
    assert ("m1", "accepted", "") in states(acts(lua, fs)) and cur_step(lua) == "stand"
    assert calls(p) == ["setForceAim"] and p.aim["force"] is True


# ---- the act lines: progress with a result, the frame's step --------------------------------------------------------

def test_a_progress_line_on_every_step_change_carries_the_step_distance_health_and_counts(lua, fs):
    p, z, w = world(lua, zx=12.0, zspeed=1.5)
    go(lua, p)
    run(lua, p, w, 40, stop=lambda: len(w["presses"]) > 0)
    pr = progress(lua, fs)
    assert [x["result"]["step"] for x in pr] == ["stand", "face", "swing"]
    keys = {"step", "d", "hp", "swings", "shoves", "stomps", "floors", "knockdowns", "hits"}
    assert all(set(x["result"]) == keys for x in pr)
    assert pr[-1]["result"]["swings"] == 1 and pr[0]["result"]["hp"] == 1.0
    assert pr[0]["result"]["d"] == pytest.approx(2.0 - 1.5 * TICK_MS / 1000.0)


def test_the_heartbeat_of_a_long_step_carries_the_counts_too(lua, fs):
    p, z, w = world(lua, zx=12.3)
    go(lua, p, seconds=5)
    run(lua, p, w, 70)                                                # 1.19 s of stand
    pr = progress(lua, fs)
    assert len(pr) == 2 and all(x["result"]["step"] == "stand" for x in pr)


def test_the_frame_act_group_carries_the_melee_step_and_decodes_through_pza1(lua, fs):
    load(lua)
    lua.execute(open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8").read())
    p, z, w = make_mover(zx=12.3)
    lua.globals()._cell = make_cell(zombies=[z])
    go(lua, p)
    run(lua, p, w)
    f = lua.eval("PZA.sense.frame")(p)
    assert (f.act.aid, f.act.state, f.act.step) == ("m1", "progress", "stand")
    assert json.loads(lua.eval("PZA.enc.act")(f.act)) == ["m1", "progress", "stand"]
    assert pza1.GROUPS["act"] == ("aid", "state", "step") and pza1.PRIOR["act"] == 2
    line = [None] * len(pza1.ORDER["frame"])
    line[0], line[pza1.ORDER["frame"].index("act")], line[pza1.ORDER["frame"].index("zombies")] = "frame", ["a", "done"], []
    assert pza1.decode(line)["act"] == {"aid": "a", "state": "done", "step": None}      # a PZA/1.7 frame's act
    start(lua, p, "steer", aid="t", vx=1, vy=0, seconds=1)
    assert lua.eval("PZA.skills.status().step") is None               # another skill's frame carries no step


def test_a_done_result_and_a_progress_result_keys_are_in_the_schema(lua, fs):
    p, z, w = world(lua, zx=12.0, zspeed=1.5)
    go(lua, p, seconds=1.0)
    run(lua, p, w, 120, stop=lambda: ended(lua))
    with open(SCHEMA, encoding="utf-8") as fh:
        defs = json.load(fh)["$defs"]
    for a in acts(lua, fs):
        assert set(a["result"]) <= set(defs["result_melee"]["properties"]), a
        assert a["reason"] == "" or a["reason"] in pza1.REASONS
    assert set(defs["result_melee_step"]["properties"]) <= set(defs["result_melee"]["properties"])


# ---- the runner: a skill's own progress result, a failure's result -------------------------------------------------

def test_a_tick_answering_progress_emits_a_progress_line_now_with_its_result(lua, fs):
    load(lua)
    lua.execute("PZA.skills.types.blip = { check = function(args, p) return true, '', { n = 0 } end,"
                " tick = function(p, st) st.n = st.n + 1; if st.n == 2 then return 'progress', { n = st.n } end;"
                " if st.n == 3 then return 'failed', 'crowd', { id = 4 } end end }")
    p = make_mover()[0]
    start(lua, p, "blip")
    tick(lua, p, 3)
    a = acts(lua, fs)
    assert [(x["state"], x["result"]) for x in a] == [("accepted", {}), ("progress", {"n": 2}), ("failed", {"id": 4})]
    assert a[2]["reason"] == "crowd" and "snapshot" not in a[1]


# ---- the cost ------------------------------------------------------------------------------------------------------

def counted(lua, p, z, w, ticks_before, setup=None):
    """Runs the melee ticks_before ticks, then counts every Java member read on one tick through Rec wrappers."""
    for _ in range(ticks_before):
        step_world(w, p)
        lua.globals()._clock["ms"] += TICK_MS
        tick(lua, p)
    if setup is not None:
        setup()
    log = []
    bd = p.getBodyDamage(p)
    p.getBodyDamage = lambda s: Rec(bd, log, "bd")
    lua.globals()._zr = Rec(z, log, "z")
    lua.execute("PZA.skills.cur.st.z = _zr")                          # the skill's own handle on the target
    made = []
    v2 = lua.globals().Vector2
    lua.globals().Vector2 = J(new=lambda x, y: made.append((x, y)) or v2.new(x, y))
    step_world(w, p)
    lua.globals()._clock["ms"] += TICK_MS
    tick(lua, Rec(p, log, "p"))
    return log, made


@pytest.mark.parametrize("case", ["stand", "back", "swing_running", "knock_wait", "hit"])
def test_the_reflex_makes_at_most_ten_java_calls_a_tick_with_no_press(lua, fs, case):
    """The architecture review's section 4.1 budget (8-10 a tick with both strikes idle), counted through the fake:
    the stand reads the dead check (2), the target's isDead (1), DistToProper (1), hasHitReaction (1), isOnFloor (1),
    getTarget (1, the close or stand choice) and the facing (1): 8."""
    kw = {"stand": {"zx": 12.3}, "back": {"zx": 11.3, "attack_ticks": 8}, "swing_running": {"zx": 11.2},
          "knock_wait": {"zx": 10.4, "attack_ticks": 6}, "hit": {"zx": 12.3}}[case]
    p, z, w = world(lua, **kw)
    if case == "knock_wait":
        w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    over = {"mode": "shove"} if case == "knock_wait" else {}
    go(lua, p, **over)
    before = {"stand": 3, "back": 12, "swing_running": 4, "knock_wait": 10, "hit": 3}[case]
    setup = (lambda: p.combat.__setitem__("hitReaction", "Bite")) if case == "hit" else None
    log, made = counted(lua, p, z, w, before, setup)
    assert cur_step(lua) == {"swing_running": "swing"}.get(case, case)
    assert len(log) <= 10 and made == [], sorted(log)
    if case == "stand":
        assert sorted(log) == sorted([("p", "getBodyDamage"), ("bd", "getOverallBodyHealth"), ("z", "isDead"),
                                      ("p", "DistToProper"), ("p", "hasHitReaction"), ("z", "isOnFloor"),
                                      ("z", "getTarget"), ("p", "faceThisObject")])


def test_the_close_step_re_aims_its_walk_only_when_the_heading_turns(lua, fs):
    """The close (an idle target beyond the reach) reads the two positions to steer at a walk (4 calls beyond the
    stand's 8, the getTarget read included), and sets the walk's direction only when it turned: 12 a tick at a still
    target, no Vector2 made."""
    p, z, w = world(lua, zx=12.3, chasing=False)
    go(lua, p)
    log, made = counted(lua, p, z, w, 3)
    assert cur_step(lua) == "close" and made == [] and len(log) == 12, sorted(log)


# ---- the faults (test_lua_faults.py's pattern, for the largest per-tick body the harness runs: review section 4.4) ------

PCALL_COUNTER = ("pcallFails = 0; local raw = pcall; pcall = function(...) local r = { raw(...) };"
                 " if not r[1] then pcallFails = pcallFails + 1 end; return unpack(r) end")
P_MEMBERS = ("getBodyDamage", "DistToProper", "hasHitReaction", "isAttackStarted", "faceThisObject", "setForceAim",
             "nullifyAiming", "DoAttack", "setDoShove", "setAutoWalk", "setAutoWalkDirection", "setForceRun",
             "setForceSprint", "getPrimaryHandItem", "getX", "getY")
Z_MEMBERS = ("isDead", "getX", "getY", "isOnFloor", "isKnockedDown", "getTarget", "getHealth")


def fault_run(lua, fs, p, z, w, fault=None):
    """The fault scenario: a target at 1.2 tiles in the reach, standing still and chasing; the swing (face, press, an
    attack of 6 ticks), its miss, the back leg to keepR, the stand, the time at 3 s; fault() applied after the first
    tick. Answers the end line."""
    go(lua, p, seconds=3)
    run(lua, p, w)
    if fault is not None:
        fault()
    run(lua, p, w, 400, stop=lambda: ended(lua))
    ends = [a for a in acts(lua, fs) if a["aid"] == "m1" and a["state"] in ("rejected", "failed", "done")]
    assert len(ends) == 1, states(acts(lua, fs))
    return ends[0]


def assert_released(lua, p, autowalk=True):
    """The stance released, the Motor's wants cleared and (unless the auto-walk's own setter is the fault) the
    auto-walk off, the runner idle."""
    assert ended(lua) and lua.eval("PZA.skills.stance.held") is False and lua.eval("PZA.motor.wantAim") is False
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    if autowalk:
        assert p.motor["autoWalk"] is False


def test_the_fault_scenario_runs_its_whole_course_clean(lua, fs):
    """The scenario every fault case perturbs, unperturbed: done time after the swing, its miss, the back leg and the
    stand, with no raise caught anywhere."""
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6)
    lua.execute(PCALL_COUNTER)
    end = fault_run(lua, fs, p, z, w)
    assert (end["state"], end["result"]["end"]) == ("done", "time") and end["result"]["swings"] == 1
    assert {"face", "swing", "back", "stand"} <= set(step_seq(lua, fs))
    assert lua.eval("PZA.skills.errors") == 0 and lua.globals().pcallFails == 0
    assert_released(lua, p)


# each player member absent from the start: the members the first tick checks fail not loaded; a missing weapon
# reader is the check's no weapon; every other member is read index-first and skipped, so the run ends done time
ABSENT_P = {"setForceAim": ("failed", "not loaded"), "nullifyAiming": ("failed", "not loaded"),
            "faceThisObject": ("failed", "not loaded"), "DoAttack": ("failed", "not loaded"),
            "setDoShove": ("failed", "not loaded"), "setAutoWalk": ("failed", "not loaded"),
            "setAutoWalkDirection": ("failed", "not loaded"), "getPrimaryHandItem": ("rejected", "no weapon")}


@pytest.mark.parametrize("member", P_MEMBERS)
def test_a_player_member_absent_ends_as_pinned_with_no_raise(lua, fs, member):
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6)
    setattr(p, member, None)
    lua.execute(PCALL_COUNTER)
    end = fault_run(lua, fs, p, z, w)
    assert (end["state"], end["reason"]) == ABSENT_P.get(member, ("done", "")), member
    assert lua.eval("PZA.skills.errors") == 0 and lua.globals().pcallFails == 0
    assert_released(lua, p, autowalk=member != "setAutoWalk")


# each target member absent from the start (the planar distance through the positions, no DistToProper): an
# unreadable position fails the check no target; every other read is fail-closed, so the run ends done time
ABSENT_Z = {"getX": ("rejected", "no target"), "getY": ("rejected", "no target")}


@pytest.mark.parametrize("member", Z_MEMBERS)
def test_a_target_member_absent_ends_as_pinned_with_no_raise(lua, fs, member):
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6, dist_member=False)
    setattr(z, member, None)
    lua.execute(PCALL_COUNTER)
    end = fault_run(lua, fs, p, z, w)
    assert (end["state"], end["reason"]) == ABSENT_Z.get(member, ("done", "")), member
    assert lua.eval("PZA.skills.errors") == 0 and lua.globals().pcallFails == 0
    assert_released(lua, p)


def raising(name):
    def f(*a):
        raise RuntimeError("java raised: " + name)
    return f


# each member raising from the second tick on: the runner catches it (S-12) and the melee ends failed interrupted,
# its stop hook releasing the stance; a member the skill calls under its own pcall (the press, the shove flag, the
# release) or never calls after its first tick runs on to done time with the raise counted where it was caught
RAISE_DONE_P = {"DoAttack", "setDoShove", "nullifyAiming", "getX", "getY"}


@pytest.mark.parametrize("member", P_MEMBERS)
def test_a_player_member_raising_never_propagates_and_releases_the_stance(lua, fs, member):
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6)
    end = fault_run(lua, fs, p, z, w, fault=lambda: setattr(p, member, raising(member)))
    want = ("done", "") if member in RAISE_DONE_P else ("failed", "interrupted")
    assert (end["state"], end["reason"]) == want, member
    if want[0] == "failed":
        assert lua.eval("PZA.skills.errors") >= 1
    assert_released(lua, p, autowalk=member not in ("setAutoWalk",))


@pytest.mark.parametrize("member", Z_MEMBERS)
def test_a_target_member_raising_never_propagates_and_releases_the_stance(lua, fs, member):
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6, dist_member=False)
    end = fault_run(lua, fs, p, z, w, fault=lambda: setattr(z, member, raising(member)))
    assert (end["state"], end["reason"]) == ("failed", "interrupted"), member
    assert lua.eval("PZA.skills.errors") >= 1
    assert_released(lua, p)
