"""PZAgent_StanceMelee.lua (PZA/1.10, Plan 31 Task 2: the meet, the finish aimed at the head and the spent meet; first
cut PZA/1.8, Plan 28 Task 7a): the melee reflex skill `melee {targetId, mode, reach, shoveR, releaseR, faceR,
pressAngle, pressLo, floorR, handbackR, stall, floorSwing}`, which owns one target to the kill at the client's tick rate:
the stance beyond faceR, the facing every tick inside it, the press when the look is on the target and the target's
distance at the swing's collision event is predicted inside the reach, the press again after a swing that left it
standing (no back step), the shove only inside MinRange, the knock wait, the finish at the fallen target's head (the
floor swing within floorR, else the stomp within 0.3 tiles), never broken by a zombie beyond handbackR, the spent meet's
shove and stomp, the press leaf on the line after each result, the ends kill, handback and lost (never time), the stance
kept across a same-target re-send, and its per-tick cost. Run on the lupa host over conftest.make_mover's kinematic fake
(the zombie closing at a set speed, the player along its auto-walk at the walk's 2.0 tiles a second, the body turning
toward the written facing at #4689's 206 degrees a second, DoAttack starting an attack that reads isAttackStarted true
for N ticks, a scripted zombie attack setting the hit reaction after a windup). Each behaviour has a positive case and a
falsifier."""
import json
import math
import os

import pytest

from agent.base import pza1
from agent.base.planner import policies as P
from .conftest import (BAT_MIN_R, ROOT, TICK_MS, TURN_RATE, J, lua_file, make_cell, make_mover, make_zombie,
                       step_world, zdist)
from .test_lua_skills import acts, load, sense, start, states, tick
from .test_lua_stance import Rec

ARGS = {"targetId": 7, "mode": "strike", "reach": 1.25, "shoveR": P.SHOVE_SEND_R, "releaseR": 2.75, "faceR": P.FACE_R,
        "pressAngle": P.PRESS_ANGLE, "pressLo": P.PRESS_LO, "floorR": P.FLOOR_R, "handbackR": P.HANDBACK_R,
        "stall": P.STALL_SWINGS}
PRESSES = ("swing", "shove", "stomp", "floor")
LEAF = {"d_press", "d_collide_pred", "d_min", "look_off", "hp0", "hp1", "knock", "cut_by"}   # fix 1: d_min
COUNTS = {"swings", "shoves", "stomps", "floors", "knockdowns", "hits"}
R2 = 1 / math.sqrt(2)
SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
UPDATE_S = TICK_MS / 1000.0


def world(lua, **kw):
    """The runner and its skills loaded, a mover (player, zombie 7, world) and Sense stubbed with the zombie."""
    load(lua)
    p, z, w = make_mover(**kw)
    sense(lua, [z])
    return p, z, w


def with_head(lua, z):
    """Sense's own S.headOf (PZAgent_Sense.lua) loaded beside the stub, the stub's zombie lookup kept."""
    lua.execute("local keep = PZA.sense; _keepById, _keepNear = keep.zombieById, keep.nearestZombie")
    lua.execute(open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8").read())
    lua.execute("PZA.sense.zombieById, PZA.sense.nearestZombie = _keepById, _keepNear")


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


def leaves(lua, fs, aid="m1"):
    return [a["result"]["press"] for a in acts(lua, fs) if a["aid"] == aid and "press" in (a.get("result") or {})]


def last(lua, fs):
    return acts(lua, fs)[-1]


def calls(p):
    return [c[0] for c in p.aim["calls"]]


def walk_dir(p):
    v = [v for n, v in p.sets if n == "setAutoWalkDirection"][-1]
    return v.x, v.y


def frame_last(lua, zombies=(), arm_pain=None, objs=None):
    """PZA.sense.last as Sense leaves it (the records the crowd and hand-back reads take, the body's armPain) and
    PZA.sense.zobj."""
    g = lua.globals()
    g._objs = lua.table_from(objs or {})
    lua.execute("PZA.sense.zobj = _objs")
    recs = ", ".join("{ id = %d, dist = %r }" % (i, d) for i, d in zombies)
    pain = "nil" if arm_pain is None else repr(arm_pain)
    lua.execute("PZA.sense.last = { zombies = { %s }, body = { armPain = %s } }" % (recs, pain))


def moodles(p, levels):
    p.getMoodles = lambda s: J(getMoodleLevel=lambda s2, t: levels.get(t, 0))


# ---- the command's checks ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("over", [{"mode": "kick"}, {"mode": 3}, {"reach": "x"}, {"reach": -1}, {"floorSwing": "yes"},
                                  {"targetId": "z"}, {"faceR": None}, {"faceR": -1}, {"pressAngle": 0},
                                  {"pressAngle": 181}, {"pressLo": -0.1}, {"floorR": None}, {"handbackR": -2},
                                  {"stall": 0}, {"releaseR": 0}, {"shoveR": None}, {"stall": "x"}])
def test_melee_with_bad_args_is_rejected(lua, fs, over):
    p, z, w = world(lua)
    a = dict(ARGS)
    a.update(over)
    a = {k: v for k, v in a.items() if v is not None}
    start(lua, p, "melee", aid="m1", **a)
    assert states(acts(lua, fs)) == [("m1", "rejected", "bad args")]


def test_the_pza1_9_arguments_are_bad_args(lua, fs):
    """PZA/1.10 dropped keepR, backVx, backVy, seconds and closeR: a PZA/1.9 melee is refused, never half run."""
    p, z, w = world(lua)
    start(lua, p, "melee", aid="m1", targetId=7, mode="strike", reach=1.4, keepR=2.5, shoveR=1.1, releaseR=2.75,
          backVx=-1.0, backVy=0.0, seconds=2.5, closeR=0.0)
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
    go(lua, p2, aid="t", mode="finish")                               # nor does the finish
    assert states(acts(lua, fs)) == [("u", "rejected", "no target"), ("f", "rejected", "too far"),
                                     ("d", "rejected", "no target"), ("n", "rejected", "no weapon"),
                                     ("s", "accepted", ""), ("s", "failed", "superseded"), ("t", "accepted", "")]


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


# ---- the ends: kill, handback, lost; never time ----------------------------------------------------------------------

def test_a_target_that_dies_ends_the_melee_done_kill_with_its_counts(lua, fs):
    p, z, w = world(lua, zx=11.0, look=math.pi, turn=0.0)            # 1 tile, the look away: no press
    go(lua, p)
    run(lua, p, w, 5)
    assert not ended(lua)                                             # the falsifier: alive, it runs on
    w["zdead"], w["zhp"] = True, 0.0
    run(lua, p, w)
    a = last(lua, fs)
    assert (a["state"], a["reason"]) == ("done", "")
    r = a["result"]
    assert r["end"] == "kill" and r["kill"] is True and r["hp0"] == 1.0 and r["hp1"] == 0.0 and "why" not in r
    assert r["swings"] == 0 and r["hits"] == 0 and r["dMin"] == pytest.approx(1.0) and "press" not in r
    assert sum(r["steps"].values()) == 5
    assert lua.eval("PZA.skills.stance.held") is False and lua.eval("PZA.motor.wantAim") is False


def test_a_dead_player_fails_the_melee_dead_and_releases_the_stance(lua, fs):
    p, z, w = world(lua, zx=13.4, zspeed=1.0)                         # beyond faceR: the stance
    go(lua, p, releaseR=4.0)
    run(lua, p, w, 3)
    assert p.aim["force"] is True
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 0.0)
    run(lua, p, w)
    assert states(acts(lua, fs))[-1] == ("m1", "failed", "dead")
    assert p.aim["force"] is False and lua.eval("PZA.motor.wantAim") is False


def test_no_time_end_a_standoff_runs_on(lua, fs):
    """PZA/1.10: the melee ends kill, handback or lost, never on time: 60 s of a target faced with the look held off
    (no press, so no stall) is still running."""
    p, z, w = world(lua, zx=11.0, look=math.pi / 2, turn=0.0)
    go(lua, p)
    run(lua, p, w, int(60000 / TICK_MS))
    assert not ended(lua) and w["presses"] == [] and cur_step(lua) == "face"
    assert all(a["state"] in ("accepted", "progress") for a in acts(lua, fs))


def test_a_target_beyond_release_r_ends_done_lost_out_of_range(lua, fs):
    p, z, w = world(lua, zx=12.5, look=math.pi, turn=0.0)
    go(lua, p)
    run(lua, p, w, 2)
    assert not ended(lua)
    w["zx"] = 12.8                                                    # 2.8 > releaseR 2.75
    run(lua, p, w)
    a = last(lua, fs)
    assert (a["state"], a["result"]["end"], a["result"]["why"], a["result"]["kill"]) == ("done", "lost",
                                                                                          "out of range", False)
    assert p.aim["force"] is False


def crowd_world(lua, other_floor=False, other_d=0.5, **kw):
    p, z, w = world(lua, **kw)
    o = make_zombie(8, 10.0 + other_d, 20.0)
    if other_floor:
        o.isOnFloor = lambda s: True
    frame_last(lua, [(8, other_d), (7, zdist(w))], objs={7: z, 8: o})
    return p, z, w


def test_another_standing_zombie_within_stand_r_ends_done_handback_crowd_with_its_id_and_distance(lua, fs):
    p, z, w = crowd_world(lua, zx=12.0)
    go(lua, p)
    run(lua, p, w)
    a = last(lua, fs)
    r = a["result"]
    assert (a["state"], r["end"], r["why"], r["id"], r["d"]) == ("done", "handback", "crowd", 8, 0.5)


@pytest.mark.parametrize("floor, d", [(True, 0.5), (False, 0.7)])
def test_a_fallen_or_a_farther_other_zombie_is_no_crowd(lua, fs, floor, d):
    p, z, w = crowd_world(lua, other_floor=floor, other_d=d, zx=12.0, look=math.pi, turn=0.0)
    go(lua, p)
    run(lua, p, w, 3)
    assert not ended(lua)


def test_presses_that_lowered_nothing_end_done_lost_no_progress_at_the_stall(lua, fs):
    """`stall` (STALL_SWINGS) swings in a row that left the target unhurt and standing end it lost (the existing
    no-progress read, now the Lua's: the melee has no time end)."""
    p, z, w = world(lua, zx=11.0, attack_ticks=6)
    go(lua, p)
    run(lua, p, w, 300, stop=lambda: ended(lua))
    a = last(lua, fs)
    assert (a["state"], a["result"]["end"], a["result"]["why"]) == ("done", "lost", "no progress")
    assert a["result"]["swings"] == P.STALL_SWINGS and len(w["presses"]) == P.STALL_SWINGS


def test_a_press_that_lowered_the_health_restarts_the_stall(lua, fs):
    """The stall's falsifier: a swing that lowers the health (the fake's on_attack) restarts the run, so ten presses
    in, the melee runs on."""
    p, z, w = world(lua, zx=11.0, attack_ticks=6)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("zhp", wd["zhp"] - 0.01)
    go(lua, p)
    run(lua, p, w, 400, stop=lambda: len(w["presses"]) >= 10)
    assert len(w["presses"]) == 10 and not ended(lua)


# ---- the hit reaction ----------------------------------------------------------------------------------------------

def test_no_press_goes_on_any_tick_reading_a_hit_reaction_and_each_run_of_it_counts_one_hit(lua, fs):
    p, z, w = world(lua, zx=11.2)                                     # within the reach 1.25, the look on
    p.combat["hitReaction"] = "Bite"
    go(lua, p)
    run(lua, p, w, 12)
    assert w["presses"] == [] and cur_step(lua) == "hit"
    p.combat["hitReaction"] = ""
    run(lua, p, w)
    assert len(w["presses"]) == 1 and cur_step(lua) == "swing"       # the falsifier: the reaction gone, the press
    assert progress(lua, fs)[-1]["result"]["hits"] == 1


def test_a_hit_during_a_press_in_flight_reads_hit_counts_it_and_marks_the_leaf_cut_by_hit(lua, fs):
    """A reaction while the swing runs is the hit step, counted, the swing's end still read; the leaf's cut_by is hit
    (the reaction leaves the swing's state, #4664, before its collision no damage, #4665)."""
    p, z, w = world(lua, zx=11.0, attack_ticks=30)
    go(lua, p)
    run(lua, p, w, 3)
    assert cur_step(lua) == "swing"
    p.combat["hitReaction"] = "Bite"
    run(lua, p, w)
    assert cur_step(lua) == "hit" and progress(lua, fs)[-1]["result"]["hits"] == 1
    p.combat["hitReaction"] = ""
    run(lua, p, w, 60, stop=lambda: leaves(lua, fs))
    assert leaves(lua, fs)[0]["cut_by"] == "hit"


def test_a_target_dying_in_a_hit_reaction_ends_done_kill(lua, fs):
    p, z, w = world(lua, zx=12.3)
    go(lua, p)
    run(lua, p, w, 2)
    p.combat["hitReaction"] = "Bite"
    w["zdead"] = True
    run(lua, p, w)
    assert (last(lua, fs)["state"], last(lua, fs)["result"]["end"]) == ("done", "kill")


# ---- the meet: the facing from faceR, the look, the predicted band ---------------------------------------------------

def test_the_stance_is_released_and_the_target_faced_every_tick_from_face_r(lua, fs):
    """Beyond faceR (3.0) a closing chaser is met in the stance (aimed, `stand`); from faceR on the stance is
    released and faceThisObject written every tick (`face`), never the mouse (#4589, #4590)."""
    p, z, w = world(lua, zx=13.2, zspeed=1.0)
    go(lua, p, releaseR=4.0)
    run(lua, p, w, 3)
    assert cur_step(lua) == "stand" and p.aim["force"] is True and zdist(w) > P.FACE_R
    run(lua, p, w, 30, stop=lambda: zdist(w) <= P.FACE_R)
    n0 = len(p.faced)
    run(lua, p, w, 5)
    assert cur_step(lua) == "face" and p.aim["force"] is False and calls(p)[-1] == "nullifyAiming"
    assert len(p.faced) == n0 + 5 and all(o is z for o in p.faced[n0:])
    assert w["presses"] == [] and w["walk"] is None                  # a chaser: faced, not walked to


def test_inside_a_smaller_face_r_the_stance_holds(lua, fs):
    """The falsifier of faceR: the same chaser with faceR 2.0 is still met in the stance at 2.9 tiles."""
    p, z, w = world(lua, zx=13.2, zspeed=1.0)
    go(lua, p, releaseR=4.0, faceR=2.0)
    run(lua, p, w, 30, stop=lambda: zdist(w) <= P.FACE_R - 0.1)
    assert cur_step(lua) == "stand" and p.aim["force"] is True


def test_no_press_while_the_look_is_off_and_the_press_once_it_comes_within_press_angle(lua, fs):
    """The target faced at 1.0 tiles with the look 90 degrees off and the body not turning: no press; the body turning
    at 206 degrees a second, the press goes on the first tick the look reads within pressAngle, its leaf's look_off
    the angle read then."""
    p, z, w = world(lua, zx=11.0, look=math.pi / 2, turn=0.0)
    go(lua, p)
    run(lua, p, w, 30)
    assert w["presses"] == [] and cur_step(lua) == "face"
    w["turn"] = TURN_RATE
    offs = []
    for _ in range(60):
        run(lua, p, w)
        offs.append(abs(w["look"]) * 180 / math.pi)
        if w["presses"]:
            break
    assert len(w["presses"]) == 1
    run(lua, p, w, 30, stop=lambda: leaves(lua, fs))
    off = leaves(lua, fs)[0]["look_off"]
    assert off <= P.PRESS_ANGLE < off + TURN_RATE * UPDATE_S * 180 / math.pi + 1e-9
    assert offs[-2] > P.PRESS_ANGLE                                   # the tick before, the look read off


@pytest.mark.parametrize("cs", [1.0, 1.6])
def test_the_swing_is_pressed_at_the_predicted_collision_band_not_at_the_raw_distance(lua, fs, cs):
    """A chaser closing at 1.6 tiles a second from 2.5 tiles, the melee's reach 0.8 (under the engine's 1.25): the
    press goes once d - v * (one update + 0.25 / CombatSpeed) reads inside the reach (#4665, #4668), so at a raw
    distance beyond it (and inside the engine's reach, fix 1), and the zombie stands inside it at the collision 25 %
    into the clip."""
    p, z, w = world(lua, zx=12.5, zspeed=1.6, combat_speed=cs, attack_ticks=80)
    go(lua, p, reach=0.8)
    run(lua, p, w, 200, stop=lambda: w["presses"])
    tc = UPDATE_S + 0.25 / cs
    dp = w["presses"][0]["d"]
    assert 0.8 < dp <= 0.8 + 1.6 * tc + 1.6 * UPDATE_S and dp <= 1.25
    run(lua, p, w, math.ceil(tc / UPDATE_S))
    assert zdist(w) <= 0.8                                            # the collision inside the reach
    run(lua, p, w, 120, stop=lambda: leaves(lua, fs))
    leaf = leaves(lua, fs)[0]
    assert leaf["d_press"] == pytest.approx(dp) and leaf["d_collide_pred"] <= 0.8
    assert leaf["d_collide_pred"] == pytest.approx(dp - 1.6 * tc, abs=1e-6)


@pytest.mark.parametrize("state, raw", [("walktoward", 1.25), ("lunge-network", 1.45)])
def test_no_press_beyond_the_engine_s_raw_reach_whatever_the_prediction(lua, fs, state, raw):
    """Fix 1 (review-t2 F1): the press builds its own hit list (#4591), and an empty one makes the two-hander's attack
    a MISS that returns before the critical roll, so a chaser at 2.5 tiles a second whose predicted collision reads
    inside the reach 1.25 at a raw 1.9 tiles is not pressed at; the press goes once the raw distance is within the
    engine's reach, the unmargined MaxRange x RangeMod 1.25 (+0.2 against a lunging zombie, #4681)."""
    p, z, w = world(lua, zx=12.6, zspeed=2.5, attack_ticks=80)
    z.getRealState = lambda s: state
    go(lua, p)
    seen = []
    for _ in range(200):
        run(lua, p, w)
        if not w["presses"]:
            seen.append(zdist(w))
        else:
            break
    assert any(d < 1.95 and d - 2.5 * (UPDATE_S + 0.25) <= 1.25 for d in seen)   # predicted in, raw out: no press
    dp = w["presses"][0]["d"]
    assert raw - 2.5 * UPDATE_S < dp <= raw


def test_a_chaser_that_is_not_closing_is_pressed_at_the_raw_distance(lua, fs):
    """The prediction's falsifier: a chaser standing still at 1.3 tiles (v 0, beyond the reach) is not pressed at but
    walked to, and pressed at the reach."""
    p, z, w = world(lua, zx=11.3, zspeed=0.0)
    go(lua, p)
    run(lua, p, w, 3)
    assert w["presses"] == [] and cur_step(lua) == "close" and p.motor["autoWalk"] is True
    run(lua, p, w, 60, stop=lambda: w["presses"])
    assert 1.2 < w["presses"][0]["d"] <= 1.25 and p.aim["force"] is False


def test_an_idle_target_beyond_face_r_is_walked_to_in_the_stance_and_pressed_at_the_reach(lua, fs):
    p, z, w = world(lua, zx=13.3, chasing=False)
    go(lua, p, releaseR=4.0)
    run(lua, p, w)
    assert cur_step(lua) == "close" and p.aim["force"] is True and p.motor["autoWalk"] is True
    assert walk_dir(p) == pytest.approx((R2, R2))                    # world +x in input space
    run(lua, p, w, 200, stop=lambda: w["presses"])
    assert 1.2 < w["presses"][0]["d"] <= 1.25 and w["presses"][0]["aiming"] is False
    assert {"close", "swing"} <= set(step_seq(lua, fs))


def test_the_press_waits_facing_while_an_attack_already_runs(lua, fs):
    p, z, w = world(lua, zx=11.0)
    w["attack"] = 999                                                 # an attack the melee did not start
    go(lua, p)
    run(lua, p, w, 5)
    assert w["presses"] == [] and cur_step(lua) == "face"
    w["attack"] = 0
    run(lua, p, w)
    assert len(w["presses"]) == 1


def test_a_reach_of_0_takes_the_weapons_reach(lua, fs):
    """reach 0: the weapon's K.reachOf, 1.25 x 1.0 x 0.9 = 1.125 for the fake's bat; a still chaser at 1.2 is walked
    to, not pressed at."""
    p, z, w = world(lua, zx=11.2)
    go(lua, p, reach=0.0)
    run(lua, p, w, 3)
    assert w["presses"] == [] and cur_step(lua) == "close"
    run(lua, p, w, 60, stop=lambda: w["presses"])
    assert w["presses"][0]["d"] <= 1.125


# ---- after a press: no back step, no pause ------------------------------------------------------------------------

def test_a_swing_that_did_nothing_is_followed_by_a_press_never_a_back_step(lua, fs):
    """A swing at a standing chaser 1.0 tiles off whose result reads it standing and unhurt: the next press goes as
    soon as the swing has ended (its end and one tick), with no back step and no walk."""
    p, z, w = world(lua, zx=11.0, attack_ticks=8)
    go(lua, p)
    run(lua, p, w, 60, stop=lambda: len(w["presses"]) > 1)
    assert len(w["presses"]) == 2 and w["presses"][1]["tick"] - w["presses"][0]["tick"] <= 8 + 2
    assert "back" not in step_seq(lua, fs) and w["walk"] is None and (w["px"], w["py"]) == (10.0, 20.0)
    assert [x for x in p.sets if x[0] == "setAutoWalk"] == []


def test_a_swing_that_lowered_the_health_is_pressed_again_too(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=8)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("zhp", wd["zhp"] - 0.2)
    go(lua, p)
    run(lua, p, w, 60, stop=lambda: len(w["presses"]) > 1)
    assert len(w["presses"]) == 2 and "back" not in step_seq(lua, fs)


def test_a_knockdown_is_waited_on_never_pressed_again_until_it_lies(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=8)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    go(lua, p)
    run(lua, p, w, 40)
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"
    assert progress(lua, fs)[-1]["result"]["knockdowns"] == 1


def test_the_f15_probe_a_chaser_from_three_tiles_takes_swings_at_the_band_and_no_shove(lua, fs):
    """F15's geometry (the spec's section 1: a chaser closing at about 1.6 tiles a second, its swings pressed at 0.95
    to 0.98 reading the zombie 0.31 to 0.55 at the collision): from 3 tiles every press is a swing pressed beyond the
    reach whose predicted collision lies inside it; no shove (the zombie never closes inside MinRange before a press),
    no back step."""
    p, z, w = world(lua, zx=13.0, zspeed=1.6, attack_ticks=60)   # the press within the engine's reach (fix 1)
    go(lua, p, releaseR=4.0)
    run(lua, p, w, 400, stop=lambda: len(w["presses"]) >= 1 and not w["attack"])
    assert w["presses"] and all(not x["shove"] for x in w["presses"])
    assert BAT_MIN_R < w["presses"][0]["d"] <= 1.25 and "back" not in step_seq(lua, fs)   # fix 1: within the reach


# ---- the shove only inside MinRange -------------------------------------------------------------------------------

@pytest.mark.parametrize("d, shove", [(0.5, True), (0.7, False)])
def test_the_shove_only_inside_min_range(lua, fs, d, shove):
    """Inside the bat's MinRange 0.61 (#4372) the press is the shove; beyond it the swing."""
    p, z, w = world(lua, zx=10.0 + d)
    go(lua, p)
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is shove
    assert cur_step(lua) == ("shove" if shove else "swing")


def test_no_swing_whose_swing_state_entry_falls_inside_min_range(lua, fs):
    """The review's caveat 1: the shove verdict is taken again at the swing state's entry one update after the press,
    so a chaser at 0.622 closing at 1 tile a second (0.605 one update on, its predicted collision at 0.355 inside the
    band) is not swung at; the next tick, inside MinRange, it is shoved. A tick earlier (0.639, 0.622 one update on)
    it would have been swung at."""
    p, z, w = world(lua, zx=11.2, zspeed=1.0, look=math.pi, turn=0.0)
    go(lua, p)
    run(lua, p, w, 60, stop=lambda: zdist(w) < 0.64)
    assert w["presses"] == [] and zdist(w) - 1.0 * UPDATE_S > BAT_MIN_R
    w["look"] = 0.0                                                   # the look on, the zombie due +x
    run(lua, p, w)
    assert w["presses"] == [] and zdist(w) - 1.0 * UPDATE_S < BAT_MIN_R < zdist(w)
    run(lua, p, w)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True


# ---- the finish: aimed at the head, never broken beyond handbackR ----------------------------------------------------

def test_the_finish_faces_the_head_and_takes_the_floor_swing_within_floor_r(lua, fs):
    """A zombie on the floor at 1.0 tiles lying on its back with its body angle 0 (its head 0.5 behind along -x, at
    (10.5, 20)): the facing is pointed at the head (faceLocationF), the floor swing pressed with the head within floorR
    1.0 (the weapon's line against the head bone first, #4679)."""
    p, z, w = world(lua, zx=11.0)
    with_head(lua, z)
    w["floor"] = True
    go(lua, p, mode="finish", floorSwing=True, headAim=True)
    run(lua, p, w)
    assert p.faced[-1] == pytest.approx((10.5, 20.0)) and p.aim["force"] is False
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is False and cur_step(lua) == "floor"


def test_a_head_beyond_floor_r_is_walked_to_and_floor_swung_at_from_floor_r(lua, fs):
    """The falsifier of the head: the same zombie lying the other way (its head at (11.5, 20), 1.5 off) is walked to,
    unaimed, toward its head, and swung at once the head is within floorR."""
    p, z, w = world(lua, zx=11.0, zangle=math.pi)
    with_head(lua, z)
    w["floor"] = True
    go(lua, p, mode="finish", floorSwing=True, headAim=True)
    run(lua, p, w)
    assert w["presses"] == [] and cur_step(lua) == "stomp_walk" and p.faced[-1] == pytest.approx((11.5, 20.0))
    run(lua, p, w, 60, stop=lambda: w["presses"])
    assert len(w["presses"]) == 1 and math.hypot(11.5 - w["px"], 20.0 - w["py"]) <= P.FLOOR_R


def test_without_the_floor_swing_the_stomp_goes_within_0_3_of_the_head(lua, fs):
    p, z, w = world(lua, zx=10.9)                                     # the head at (10.4, 20), 0.4 off
    with_head(lua, z)
    w["floor"] = True
    go(lua, p, mode="finish", headAim=True)
    run(lua, p, w)
    assert w["presses"] == [] and cur_step(lua) == "stomp_walk"
    run(lua, p, w, 30, stop=lambda: w["presses"])
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True
    assert math.hypot(10.4 - w["px"], 20.0 - w["py"]) <= 0.3
    run(lua, p, w, 40, stop=lambda: leaves(lua, fs))
    assert leaves(lua, fs)[0]["d_press"] <= 0.3


def test_the_finish_repeats_until_zombie_dead_with_no_time_end(lua, fs):
    p, z, w = world(lua, zx=10.3, attack_ticks=6)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("zhp", wd["zhp"] - 0.01)   # each stomp lowers it a little
    w["floor"] = True
    go(lua, p, mode="finish")
    run(lua, p, w, 3000, stop=lambda: len(w["presses"]) >= 12)
    assert len(w["presses"]) == 12 and not ended(lua) and all(x["shove"] for x in w["presses"])
    w["zdead"] = True
    run(lua, p, w)
    assert last(lua, fs)["result"]["end"] == "kill"


@pytest.mark.parametrize("other_d, broken", [(2.5, False), (1.5, True)])
def test_a_standing_zombie_breaks_the_finish_only_inside_handback_r(lua, fs, other_d, broken):
    """Another standing zombie inside handbackR (2.0) hands back (done handback, why standing, its id and d); one
    beyond it never breaks the finish (F15's two knock-downs lost to `pair` flees)."""
    p, z, w = crowd_world(lua, other_d=other_d, zx=10.3)
    w["floor"] = True
    go(lua, p, mode="finish")
    run(lua, p, w, 3)
    if broken:
        r = last(lua, fs)["result"]
        assert (r["end"], r["why"], r["id"], r["d"]) == ("handback", "standing", 8, 1.5)
    else:
        assert not ended(lua) and len(w["presses"]) == 1


def test_a_finish_whose_target_stands_meets_it(lua, fs):
    """PZA/1.10: no `stood` failure; a finish's target that stands is met (here swung at within the reach)."""
    p, z, w = world(lua, zx=11.0)
    go(lua, p, mode="finish")
    run(lua, p, w, 2)
    assert not ended(lua) and len(w["presses"]) == 1 and w["presses"][0]["shove"] is False


def test_a_knockdown_not_yet_on_the_floor_is_waited_on_then_stomped_at_the_head(lua, fs):
    p, z, w = world(lua, zx=10.4, attack_ticks=6)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    go(lua, p, mode="shove")
    run(lua, p, w, 10)
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"
    run(lua, p, w, 20)
    assert len(w["presses"]) == 1 and cur_step(lua) == "knock_wait"   # no press while it falls
    w["floor"] = True
    run(lua, p, w, 20, stop=lambda: len(w["presses"]) > 1)
    assert len(w["presses"]) == 2 and w["presses"][1]["shove"] is True


def test_a_stomp_walk_that_gains_nothing_ends_done_lost_out_of_reach(lua, fs):
    p, z, w = world(lua, zx=11.5)
    p.setAutoWalkDirection = lambda s, v: p.sets.append(("setAutoWalkDirection", v))   # the walk never moves
    w["floor"] = True
    go(lua, p, mode="finish")
    run(lua, p, w)
    assert cur_step(lua) == "stomp_walk"
    run(lua, p, w, int(4000 / TICK_MS) + 2, stop=lambda: ended(lua))
    r = last(lua, fs)["result"]
    assert (r["end"], r["why"]) == ("lost", "out of reach")


# ---- the spent meet --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("how", ["pain", "endurance", "tired", "mode"])
def test_the_spent_meet_shoves_within_shove_r_and_never_swings(lua, fs, how):
    """The arms' pain over 10 (#4370), the endurance or tired moodle at 2 (#4371), or mode shove: a standing target at
    1.1 (inside the reach, beyond shoveR 0.9) is closed on and shoved within shoveR, never swung at."""
    p, z, w = world(lua, zx=11.1, attack_ticks=6)
    frame_last(lua, arm_pain=25.0 if how == "pain" else 2.0)
    if how in ("endurance", "tired"):
        moodles(p, {how.upper(): 2})
    go(lua, p, mode="shove" if how == "mode" else "strike")
    run(lua, p, w, 3)
    assert w["presses"] == [] and cur_step(lua) == "close"
    run(lua, p, w, 60, stop=lambda: w["presses"])
    assert w["presses"][0]["shove"] is True and w["presses"][0]["d"] <= P.SHOVE_SEND_R
    assert progress(lua, fs)[-1]["result"]["spent"] is True


def test_not_spent_the_same_target_is_swung_at(lua, fs):
    """The spent meet's falsifier: the arms' pain 10 (not over) and the moodles at 1: the swing at 1.1."""
    p, z, w = world(lua, zx=11.1)
    frame_last(lua, arm_pain=10.0)
    moodles(p, {"ENDURANCE": 1, "TIRED": 1})
    go(lua, p)
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is False


def test_the_spent_finish_stomps_and_never_floor_swings(lua, fs):
    p, z, w = world(lua, zx=10.3)
    frame_last(lua, arm_pain=40.0)
    w["floor"] = True
    go(lua, p, mode="finish", floorSwing=True)
    run(lua, p, w, 2)
    assert len(w["presses"]) == 1 and w["presses"][0]["shove"] is True and cur_step(lua) == "stomp"


# ---- the press leaf ------------------------------------------------------------------------------------------------

def test_each_press_s_result_carries_the_press_leaf_s_keys(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=8)
    go(lua, p)
    run(lua, p, w, 30, stop=lambda: leaves(lua, fs))
    leaf = leaves(lua, fs)[0]
    assert set(leaf) == LEAF
    assert (leaf["d_press"], leaf["hp0"], leaf["hp1"], leaf["knock"], leaf["cut_by"]) == (1.0, 1.0, 1.0, False, "")
    assert leaf["d_min"] == 1.0                                       # a standing target: its position (fix 1, F5)
    assert leaf["d_collide_pred"] == pytest.approx(1.0) and leaf["look_off"] == pytest.approx(0.0, abs=1e-9)
    pr = [a for a in progress(lua, fs) if "press" in a["result"]]
    assert len(pr) == 1 and set(pr[0]["result"]) == {"step", "d", "hp", "spent", "press"} | COUNTS


def test_a_kill_during_a_press_carries_its_leaf_on_the_done_line(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=30)
    go(lua, p)
    run(lua, p, w, 3)
    w["zdead"], w["zhp"] = True, 0.0
    run(lua, p, w)
    r = last(lua, fs)["result"]
    assert r["end"] == "kill" and set(r["press"]) == LEAF and r["press"]["hp1"] == 0.0


def test_a_press_superseded_in_flight_carries_its_leaf_cut_by_superseded(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=30)
    go(lua, p)
    run(lua, p, w, 3)
    start(lua, p, "steer", aid="s", vx=1, vy=0, seconds=1)
    a = [x for x in acts(lua, fs) if x["aid"] == "m1"][-1]
    assert (a["state"], a["reason"]) == ("failed", "superseded")
    assert a["result"]["press"]["cut_by"] == "superseded" and a["result"]["swings"] == 1


# ---- the stance across re-sends -------------------------------------------------------------------------------------

STANCE = {"zx": 13.4, "chasing": False}   # beyond faceR: the stance (an idle target, the close in the stance)


def test_a_same_target_resend_keeps_the_stance(lua, fs):
    p, z, w = world(lua, **STANCE)
    go(lua, p, aid="m1", releaseR=4.0)
    run(lua, p, w, 3)
    go(lua, p, aid="m2", releaseR=4.0)
    run(lua, p, w, 3)
    st = states(acts(lua, fs))
    assert ("m1", "failed", "superseded") in st and ("m2", "accepted", "") in st
    assert "nullifyAiming" not in calls(p) and p.aim["force"] is True


def test_another_target_or_another_skill_releases_the_stance(lua, fs):
    p, z, w = world(lua, **STANCE)
    z8 = make_zombie(8, 13.4, 21.0)
    sense(lua, [z, z8])
    go(lua, p, aid="m1", releaseR=4.0)
    run(lua, p, w, 2)
    go(lua, p, aid="m2", targetId=8, releaseR=4.0)
    assert calls(p)[-1] == "nullifyAiming"
    run(lua, p, w, 2)
    assert p.aim["force"] is True
    start(lua, p, "steer", aid="s", vx=1, vy=0, seconds=1)
    assert calls(p)[-1] == "nullifyAiming" and p.aim["force"] is False


def test_a_melee_superseded_by_an_aim_keeps_the_stance(lua, fs):
    p, z, w = world(lua, **STANCE)
    go(lua, p, releaseR=4.0)
    run(lua, p, w, 2)
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    run(lua, p, w, 2)
    assert "nullifyAiming" not in calls(p) and p.aim["force"] is True and lua.eval("PZA.skills.cur.type") == "aim"


def test_a_resent_melee_waits_on_a_target_falling_from_another_strike(lua, fs):
    """A melee re-sent while its target reads isKnockedDown, not yet isOnFloor, within the reach: knock_wait, no
    press, whatever the mode."""
    p, z, w = world(lua, zx=11.2)
    w["knocked"] = True
    go(lua, p)
    run(lua, p, w, 5)
    assert cur_step(lua) == "knock_wait" and w["presses"] == []


def test_an_aim_superseded_by_a_melee_keeps_the_stance(lua, fs):
    p, z, w = world(lua, zx=13.4, zspeed=1.0)
    start(lua, p, "aim", aid="aim", vx=0, vy=0, seconds=5, targetId=7)
    run(lua, p, w)
    go(lua, p, releaseR=4.0)
    run(lua, p, w, 2)
    assert ("m1", "accepted", "") in states(acts(lua, fs)) and cur_step(lua) == "stand"
    assert calls(p) == ["setForceAim"] and p.aim["force"] is True


# ---- the act lines: progress with a result, the frame's step --------------------------------------------------------

def test_a_progress_line_on_every_step_change_carries_the_step_distance_health_counts_and_spent(lua, fs):
    p, z, w = world(lua, zx=12.0, zspeed=1.5, look=math.pi / 2)
    go(lua, p)
    run(lua, p, w, 80, stop=lambda: w["presses"])
    pr = progress(lua, fs)
    assert [x["result"]["step"] for x in pr] == ["face", "swing"]
    assert all(set(x["result"]) == {"step", "d", "hp", "spent"} | COUNTS for x in pr)
    assert pr[-1]["result"]["swings"] == 1 and pr[0]["result"]["hp"] == 1.0 and pr[0]["result"]["spent"] is False
    assert pr[0]["result"]["d"] == pytest.approx(2.0 - 1.5 * TICK_MS / 1000.0)


def test_the_heartbeat_of_a_long_step_carries_the_counts_too(lua, fs):
    p, z, w = world(lua, zx=11.0, look=math.pi, turn=0.0)
    go(lua, p)
    run(lua, p, w, 70)                                                # 1.19 s of face
    pr = progress(lua, fs)
    assert len(pr) == 2 and all(x["result"]["step"] == "face" for x in pr)


def test_the_frame_act_group_carries_the_melee_step_and_decodes_through_pza1(lua, fs):
    load(lua)
    lua.execute(open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8").read())
    p, z, w = make_mover(zx=12.3, look=math.pi, turn=0.0)
    lua.globals()._cell = make_cell(zombies=[z])
    go(lua, p)
    run(lua, p, w)
    f = lua.eval("PZA.sense.frame")(p)
    assert (f.act.aid, f.act.state, f.act.step) == ("m1", "progress", "face")
    assert json.loads(lua.eval("PZA.enc.act")(f.act)) == ["m1", "progress", "face"]
    start(lua, p, "steer", aid="t", vx=1, vy=0, seconds=1)
    assert lua.eval("PZA.skills.status().step") is None               # another skill's frame carries no step


def test_every_result_key_is_in_the_schema(lua, fs):
    """Every key of every act line the melee writes (progress, done, failed; the leaf's) is in result_melee, and the
    step result's are a subset of it."""
    with open(SCHEMA, encoding="utf-8") as fh:
        defs = json.load(fh)["$defs"]
    props = defs["result_melee"]["properties"]
    p, z, w = world(lua, zx=12.0, zspeed=1.5, attack_ticks=8)
    w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    go(lua, p)
    run(lua, p, w, 200, stop=lambda: cur_step(lua) == "knock_wait")
    w["floor"] = True
    run(lua, p, w, 30)
    w["zdead"] = True
    run(lua, p, w)
    for a in acts(lua, fs):
        assert set(a["result"]) <= set(props), a
        if "press" in a["result"]:
            assert set(a["result"]["press"]) == set(props["press"]["properties"]) == LEAF
        assert a["reason"] == "" or a["reason"] in pza1.REASONS
    assert set(defs["result_melee_step"]["properties"]) <= set(props)
    assert last(lua, fs)["result"]["end"] == "kill"


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


def test_a_stop_hook_s_table_is_the_failed_line_s_result_only_where_none_was_given(lua, fs):
    """PZA/1.10 (PZAgent_Skills.lua's finish): a stop hook answering a table gives a failed line its result; a failed
    line with its own result keeps it; a hook answering nothing leaves the result empty."""
    load(lua)
    lua.execute("PZA.skills.types.blop = { check = function(args, p) return true, '', { n = 0 } end,"
                " tick = function(p, st) st.n = st.n + 1; if st.n == 2 then return 'failed', 'crowd', { id = 4 } end end,"
                " stop = function(p, st, reason) return { why = reason } end }")
    lua.execute("PZA.skills.types.blank = { check = function(args, p) return true, '', {} end,"
                " tick = function(p, st) end, stop = function(p, st, reason) end }")
    p = make_mover()[0]
    start(lua, p, "blop", aid="b1")
    start(lua, p, "blop", aid="b2")                                   # b1 superseded: the hook's table
    tick(lua, p, 2)                                                   # b2 fails crowd with its own result
    start(lua, p, "blank", aid="c1")
    start(lua, p, "blank", aid="c2")                                  # c1 superseded: the hook answers nothing
    ends = [(x["aid"], x["reason"], x["result"]) for x in acts(lua, fs) if x["state"] == "failed"]
    assert ends == [("b1", "superseded", {"why": "superseded"}), ("b2", "crowd", {"id": 4}),
                    ("c1", "superseded", {})]


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


FACE_TICK = [("p", "getBodyDamage"), ("bd", "getOverallBodyHealth"), ("z", "isDead"), ("p", "getX"), ("p", "getY"),
             ("z", "getX"), ("z", "getY"), ("p", "hasHitReaction"), ("z", "isOnFloor"), ("p", "faceThisObject"),
             ("p", "getLookAngleRadians")]


@pytest.mark.parametrize("case", ["face", "face_on", "stand", "swing_running", "knock_wait", "hit"])
def test_the_reflex_s_no_press_tick_costs(lua, fs, case):
    """The no-press ticks' Java calls, counted through the fake (the spent read once a frame, here once a second with
    no frame, outside the counted tick): face (a closing chaser inside faceR beyond the reach, the look off) 11, the
    dead check (2), isDead, the two positions (4), the hit read, isOnFloor, the facing and the look; with the look on
    the prediction adds getCombatSpeed (12); the stand beyond faceR 10 (no look: the stance's facing is the mouse's;
    isKnockedDown is read only within the reach or shoveR); a press in flight 10 (isAttackStarted and, fix 1, F2, the
    facing); the knock wait 11 (isKnockedDown); a hit reaction 10 (the facing, and its step change's progress line
    reads the target's health)."""
    kw = {"face": {"zx": 12.3, "zspeed": 0.3, "look": math.pi, "turn": 0.0},
          "face_on": {"zx": 12.3, "zspeed": 0.3},
          "stand": {"zx": 13.4, "zspeed": 0.3},
          "swing_running": {"zx": 11.0, "attack_ticks": 30},
          "knock_wait": {"zx": 10.4, "attack_ticks": 6}, "hit": {"zx": 12.3, "zspeed": 0.3}}[case]
    p, z, w = world(lua, **kw)
    if case == "knock_wait":
        w["on_attack"] = lambda wd, shove: wd.__setitem__("knocked", True)
    over = {"mode": "shove"} if case == "knock_wait" else {"releaseR": 4.0}
    go(lua, p, **over)
    before = {"face": 3, "face_on": 3, "stand": 3, "swing_running": 4, "knock_wait": 10, "hit": 3}[case]
    setup = (lambda: p.combat.__setitem__("hitReaction", "Bite")) if case == "hit" else None
    log, made = counted(lua, p, z, w, before, setup)
    assert cur_step(lua) == {"face_on": "face", "swing_running": "swing"}.get(case, case)
    want = {"face": 11, "face_on": 12, "stand": 10, "swing_running": 10, "knock_wait": 11, "hit": 10}[case]
    assert len(log) == want and made == [], sorted(log)
    if case == "face":
        assert sorted(log) == sorted(FACE_TICK)
    if case == "face_on":
        assert sorted(log) == sorted(FACE_TICK + [("p", "getCombatSpeed")])


def test_the_close_step_re_aims_its_walk_only_when_the_heading_turns(lua, fs):
    """The close (a target not closing beyond the press's distance) sets the walk's direction only when it turned:
    no Vector2 made on a straight walk."""
    p, z, w = world(lua, zx=12.3, chasing=False)
    go(lua, p)
    log, made = counted(lua, p, z, w, 3)
    assert cur_step(lua) == "close" and made == [], sorted(log)
    assert ("p", "setAutoWalkDirection") not in log


def test_the_spent_read_runs_once_a_frame(lua, fs):
    """The moodles are read once a frame (Sense's S.last), not every tick: three ticks on one frame read getMoodles
    once; a new frame reads it again."""
    p, z, w = world(lua, zx=12.3, zspeed=0.3, look=math.pi, turn=0.0)
    n = {"moodles": 0}

    def mo(s):
        n["moodles"] += 1
        return J(getMoodleLevel=lambda s2, t: 0)
    p.getMoodles = mo
    frame_last(lua, arm_pain=0.0)
    go(lua, p)
    run(lua, p, w, 3)
    assert n["moodles"] == 1
    frame_last(lua, arm_pain=0.0)
    run(lua, p, w)
    assert n["moodles"] == 2


# ---- the faults (test_lua_faults.py's pattern, for the largest per-tick body the harness runs: review 4.4) ---------

PCALL_COUNTER = ("pcallFails = 0; local raw = pcall; pcall = function(...) local r = { raw(...) };"
                 " if not r[1] then pcallFails = pcallFails + 1 end; return unpack(r) end")
P_MEMBERS = ("getBodyDamage", "DistToProper", "hasHitReaction", "isAttackStarted", "faceThisObject", "setForceAim",
             "nullifyAiming", "DoAttack", "setDoShove", "setAutoWalk", "setAutoWalkDirection", "setForceRun",
             "setForceSprint", "getPrimaryHandItem", "getX", "getY", "getLookAngleRadians", "getCombatSpeed")
Z_MEMBERS = ("isDead", "getX", "getY", "isOnFloor", "isKnockedDown", "getTarget", "getHealth")
OUT_TICK = 200   # the fault scenario's zombie leaves releaseR here should nothing have ended it


def fault_run(lua, fs, p, z, w, fault=None):
    """The fault scenario: a target at 1.2 tiles in the reach, standing still and chasing; the swings (an attack of 6
    ticks each) that leave it standing and unhurt to the stall (done lost, no progress), else at OUT_TICK the target
    moved beyond releaseR (done lost, out of range); fault() applied after the first tick. Answers the end line."""
    go(lua, p)
    run(lua, p, w)
    if fault is not None:
        fault()
    run(lua, p, w, OUT_TICK, stop=lambda: ended(lua))
    if not ended(lua):
        w["zx"] = 14.0
        run(lua, p, w, 100, stop=lambda: ended(lua))
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
    """The scenario every fault case perturbs, unperturbed: done lost (no progress) after the stall's three swings,
    with no raise caught anywhere."""
    p, z, w = world(lua, zx=11.2, zspeed=0.0, attack_ticks=6)
    lua.execute(PCALL_COUNTER)
    end = fault_run(lua, fs, p, z, w)
    assert (end["state"], end["result"]["end"], end["result"]["why"]) == ("done", "lost", "no progress")
    assert end["result"]["swings"] == P.STALL_SWINGS
    assert lua.eval("PZA.skills.errors") == 0 and lua.globals().pcallFails == 0
    assert_released(lua, p)


# each player member absent from the start: the members the first tick checks fail not loaded; a missing weapon
# reader is the check's no weapon; the player's position not loaded; every other member is read index-first and
# skipped, so the run ends done (the stall, or out of range)
ABSENT_P = {"setForceAim": ("failed", "not loaded"), "nullifyAiming": ("failed", "not loaded"),
            "faceThisObject": ("failed", "not loaded"), "DoAttack": ("failed", "not loaded"),
            "setDoShove": ("failed", "not loaded"), "setAutoWalk": ("failed", "not loaded"),
            "setAutoWalkDirection": ("failed", "not loaded"), "getPrimaryHandItem": ("rejected", "no weapon"),
            "getX": ("failed", "not loaded"), "getY": ("failed", "not loaded")}


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
# unreadable position fails the check no target; every other read is fail-closed, so the run ends done
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


# each member raising from the second tick on: the runner catches it (S-12) and the melee ends failed interrupted, its
# stop hook releasing the stance; a member the skill calls under its own pcall (the press, the shove flag, the
# release) or never calls again after the first tick in this scenario (the check's DistToProper, the walk's setters,
# the stance's and the run latches' setters, set once on the first tick inside faceR) runs on to its done
RAISE_DONE_P = {"DoAttack", "setDoShove", "nullifyAiming", "DistToProper", "setAutoWalk", "setAutoWalkDirection",
                "setForceAim", "setForceRun", "setForceSprint"}
RAISE_DONE_Z = {"getTarget"}   # read only before two positions are kept


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
    want = ("done", "") if member in RAISE_DONE_Z else ("failed", "interrupted")
    assert (end["state"], end["reason"]) == want, member
    if want[0] == "failed":
        assert lua.eval("PZA.skills.errors") >= 1
    assert_released(lua, p)


# ---- fix 1 (review-t2): the facing through the swing, the refused press, the aim at the position, d_min, the walk ----

def test_the_facing_is_written_every_tick_of_a_swing_in_flight_and_of_the_hit_step(lua, fs):
    """F2: the collision's dot (#4681) and the bite's facing skip (#4688) read the look, which turns toward the last
    facing written (#4689): a zombie moving sideways during the swing is faced on every tick of it, and on the hit
    step."""
    p, z, w = world(lua, zx=11.0, attack_ticks=40)
    go(lua, p)
    run(lua, p, w)
    assert cur_step(lua) == "swing"
    n0 = len(p.faced)
    for k in range(20):
        w["zy"] += 0.02
        run(lua, p, w)
        assert cur_step(lua) == "swing" and len(p.faced) == n0 + k + 1 and p.faced[-1] is z, k
    assert w["face_to"] == pytest.approx(math.atan2(w["zy"] - 20.0, 1.0), abs=0.05)
    p.combat["hitReaction"] = "Bite"
    n1 = len(p.faced)
    run(lua, p, w, 3)
    assert cur_step(lua) == "hit" and len(p.faced) == n1 + 3


def test_a_refused_press_is_read_on_the_next_tick_and_pressed_again(lua, fs):
    """F3: pressedAttack sets attackStarted at the press, so a press reading isAttackStarted false on the next tick was
    refused: it ends on that tick, counts in no stall, and the press goes again at once, never waited out for
    K.SWING_MS; the run's first refusal writes its leaf (cut_by refused, `refusals` 1), the later ones none."""
    p, z, w = world(lua, zx=11.0, attack_ticks=0)                     # the fake's attack never starts: refused
    go(lua, p)
    run(lua, p, w, 5)
    assert [x["tick"] for x in w["presses"]] == [1, 2, 3, 4, 5] and not ended(lua)
    lv = leaves(lua, fs)
    assert len(lv) == 1 and lv[0]["cut_by"] == "refused"
    first = [a for a in progress(lua, fs) if "press" in a["result"]][0]
    assert first["result"]["refusals"] == 1


def test_a_refusal_run_writes_a_line_at_its_end_with_its_count(lua, fs):
    """The residual: two refusals, then an accepted press: the tick the press reads started writes a line carrying
    `refusals` 2, the run's count, and the run restarts."""
    p, z, w = world(lua, zx=11.0, attack_ticks=0)
    go(lua, p)
    run(lua, p, w, 2)                                                 # press 1, its refusal and press 2
    w["attack_ticks"] = 8                                             # press 3 (tick 3) is accepted
    run(lua, p, w, 2)
    counts_ = [a["result"].get("refusals") for a in progress(lua, fs)]
    assert counts_.count(2) == 1 and lua.eval("PZA.skills.cur.st.refusals") == 0 and len(w["presses"]) == 3


def test_a_sustained_refusal_writes_a_few_act_lines_a_second(lua, fs):
    """The residual: the engine refusing every press for a second (60 ticks) writes at most 6 act lines for the melee
    (about 60 before it), while it still presses again on the tick after each refusal outside the waits."""
    p, z, w = world(lua, zx=11.0, attack_ticks=0)
    go(lua, p)
    run(lua, p, w, 60)
    lines = [a for a in acts(lua, fs) if a["aid"] == "m1"]
    assert len(lines) <= 6 and len(w["presses"]) >= 5, [(a["state"], a.get("result", {}).get("step")) for a in lines]


def test_after_refuse_max_refusals_the_press_waits_facing_then_retries(lua, fs):
    """The residual: after K.REFUSE_MAX (5) refusals in a row the press waits K.REFUSE_WAIT_MS (half K.SWING_MS),
    step refused, the facing written on every tick of it, then presses again."""
    p, z, w = world(lua, zx=11.0, attack_ticks=0)
    go(lua, p)
    assert (lua.eval("PZA.skills.REFUSE_MAX"), lua.eval("PZA.skills.REFUSE_WAIT_MS"),
            lua.eval("PZA.skills.REFUSE_END")) == (5, lua.eval("PZA.skills.SWING_MS") / 2, 15)
    run(lua, p, w, 5)
    n0 = len(p.faced)
    wait_ticks = int(lua.eval("PZA.skills.REFUSE_WAIT_MS") / TICK_MS)
    for k in range(wait_ticks - 1):
        run(lua, p, w)
        assert len(w["presses"]) == 5 and cur_step(lua) == "refused" and len(p.faced) == n0 + k + 1, k
    run(lua, p, w, 3, stop=lambda: len(w["presses"]) > 5)
    assert len(w["presses"]) == 6 and w["presses"][5]["tick"] - w["presses"][4]["tick"] >= wait_ticks


def test_refuse_end_refusals_in_a_row_end_the_melee_lost_refused(lua, fs):
    p, z, w = world(lua, zx=11.0, attack_ticks=0)
    go(lua, p)
    run(lua, p, w, 400, stop=lambda: ended(lua))
    r = last(lua, fs)["result"]
    assert (r["end"], r["why"], r["refusals"]) == ("lost", "refused", 15) and len(w["presses"]) == 15


def test_an_accepted_press_is_never_read_refused(lua, fs):
    """F3's falsifier: a press the engine started holds its step to its end."""
    p, z, w = world(lua, zx=11.0, attack_ticks=8)
    go(lua, p)
    run(lua, p, w, 5)
    assert len(w["presses"]) == 1 and cur_step(lua) == "swing"


@pytest.mark.parametrize("head_aim", [False, True])
def test_the_finish_aims_at_the_head_only_with_head_aim(lua, fs, head_aim):
    """F4, the controller's ruling: without headAim (the default until the lying direction is calibrated) the finish
    faces the zombie's position (faceThisObject) and measures the floor swing's floorR and the stomp's 0.3 to it; with
    it, the head estimate (faceLocationF at (10.5, 20)). A zombie on its back at 1.2 tiles (its head estimate at 0.7)
    is floor-swung at only with headAim; without it the walk goes toward the zombie."""
    p, z, w = world(lua, zx=11.2)
    with_head(lua, z)
    w["floor"] = True
    go(lua, p, mode="finish", floorSwing=True, headAim=head_aim)
    run(lua, p, w)
    if head_aim:
        assert p.faced[-1] == pytest.approx((10.7, 20.0)) and len(w["presses"]) == 1
    else:
        assert p.faced[-1] is z and w["presses"] == [] and cur_step(lua) == "stomp_walk"
        run(lua, p, w, 30, stop=lambda: w["presses"])
        assert w["presses"] and w["presses"][0]["d"] <= P.FLOOR_R


@pytest.mark.parametrize("head_aim, want", [(True, 0.5), (False, 1.0)])
def test_the_floor_press_s_d_min_is_the_nearer_of_the_head_and_the_position(lua, fs, head_aim, want):
    """F5: the leaf's d_min, the distance the shove test reads, is the nearest of the target's readable points: for a
    fallen one with headAim the nearer of the head estimate (0.5) and its position (1.0); without headAim its
    position."""
    p, z, w = world(lua, zx=11.0, attack_ticks=6)
    with_head(lua, z)
    w["floor"] = True
    go(lua, p, mode="finish", floorSwing=True, headAim=head_aim)
    run(lua, p, w, 20, stop=lambda: leaves(lua, fs))
    assert leaves(lua, fs)[0]["d_min"] == pytest.approx(want)


def test_a_flickering_closing_read_cannot_run_the_melee_forever(lua, fs):
    """F6: one walk bound a melee, the walking ticks of every walking step summed: a target at 1.6 tiles whose closing
    read flickers about K.MELEE_CLOSING_V (it steps 0.012 tiles toward and away each tick) alternates the walk and the
    face; the player's walk never moves it, so the melee ends lost (out of reach) once the walking ticks reach
    K.STOMP_APPROACH_MS, both steps having run."""
    p, z, w = world(lua, zx=11.6, zspeed=0.0)
    p.setAutoWalkDirection = lambda s, v: p.sets.append(("setAutoWalkDirection", v))   # the walk never moves
    go(lua, p)
    for k in range(1200):
        w["zx"] += 0.012 if k % 2 else -0.012
        run(lua, p, w)
        if ended(lua):
            break
    r = last(lua, fs)["result"]
    assert (r["end"], r["why"]) == ("lost", "out of reach")
    assert {"close", "face"} <= set(step_seq(lua, fs))
