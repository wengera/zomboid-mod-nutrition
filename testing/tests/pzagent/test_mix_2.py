"""The composition mix_2 (Plan 31 Task 13: `planner/mix_2/`, `Survive(control="mix_2")`): the doctrine's arbiter with
the tactician's guards fighting to the kill, its re-pin, the dress that waits for nothing standing or crawling within
KEEP_R, the crawler's finish, and the ladder's lone-idle seek; no string, no Strike. Every rule mix_2 adds or changes
has a test here that fails without it (the mutation pass in the task's report); the replay over the committed rings is
`test_mix_2_replay.py`. What mix_2 imports of the doctrine unchanged (the arbiter, the Avoid, the Door, the Order, the
resume) keeps the doctrine's own tests in `test_doctrine.py`; the few here show it still runs under mix_2."""
from agent.base.planner import survive as S
from agent.base.planner.doctrine import intents as DI
from agent.base.planner.doctrine.situation import Memory
from agent.base.planner.doctrine.source import Resume
from agent.base.planner.goals import ExploreToward
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2 import situation as SI
from agent.base.planner.mix_2.assess import line_switches, mix_of
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.mix_2.intents import INTENTS
from agent.base.planner.mix_2.seek import Reach

from .fakemod import MELEE_CAPS
from .test_doctrine import GROUP_EAST, avoid_rig, hold_bandage, bleed, other_end, trial_score
from .test_policies import BAT, Rig, grid, zombie
from .test_survive import last, tick
from .test_survive_g import zd

CAPS = tuple(MELEE_CAPS)
HIT = "HitReaction"   # a non-empty `me.hitReaction` (PZA/1.4)


# ================================================================ the fixtures
def rig(tmp_path, goal=None, ground=True):
    from .test_survive_g import Src
    r = Rig(tmp_path, caps=CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(goal), control="mix_2")
    if ground:
        r.scan(grid(80, 125, 180, 220))
    return r, sv


def world(tmp_path, zs=(), weapon=BAT, **frame):
    r = Rig(tmp_path, caps=CAPS)
    r.scan(grid(80, 125, 180, 220))
    r.frame(zombies=list(zs), weapon=weapon, **frame)
    return r


def idle(zid, x, y):
    return zd(zid, x, y, has_target=False)


def fallen(zid, x, y):
    return dict(idle(zid, x, y), onFloor=True)


def crawler(zid, x, y):
    return dict(idle(zid, x, y), onFloor=True, crawler=True)


def always(zid, z):
    return True


def wants(r, mem=None, now=None, seek=always):
    return SI.read(r.world, mem or Memory(), r.clock() if now is None else now, seek)


def head(ws):
    """(kind, p, piece, target) of the first want."""
    w = ws[0]
    return w.kind, w.p, SI.piece_of(w), w.target


def mix(tmp_path):
    return last(tmp_path)["inputs"]["mix_2"]


# ================================================================ the priorities and the pieces
def test_the_six_priorities_keep_the_doctrine_s_numbers_with_the_guard_at_p0():
    assert K.PRIORITY_NAMES == ("guard", "dress", "avoid", "fight", "door", "order")
    assert (K.P_GUARD, K.P_DRESS, K.P_AVOID, K.P_FIGHT, K.P_DOOR, K.P_ORDER) == tuple(range(6))
    assert set(INTENTS) == {"fight", "dress", "avoid", "door", "order"}   # no Strike: the guards are Fights
    assert INTENTS["avoid"] is DI.Avoid and INTENTS["door"] is DI.Door and INTENTS["order"] is DI.Order


def test_the_constants_are_the_pieces_own_unchanged():
    from agent.base.planner import policies as P
    from agent.base.planner.tactician import executors as X
    assert (K.SWING_GUARD_R, K.FIGHT_REACH, K.KEEP_R, K.MELEE_RELEASE_R, K.SEEK_R) == (
        X.SWING_GUARD_R, P.FIGHT_REACH, P.KEEP_R, P.MELEE_RELEASE_R, P.ENGAGE_R)
    assert K.SEEK_R == DK.ENGAGE_R and DK.DRESS_CLEAR_R == K.KEEP_R


# ================================================================ P0: the guards (pure)
def test_a_standing_zombie_within_the_swing_radius_is_the_swing_guard_aware_or_not(tmp_path):
    for i, z in enumerate((idle(1, 100.8, 200.0), zombie(1, 100.8, 200.0))):
        r = world(tmp_path / str(i), [z, zombie(2, 104.0, 200.0)])
        assert head(wants(r)) == ("fight", K.P_GUARD, "swing", 1)


def test_the_strike_is_gone_a_zombie_beyond_the_swing_radius_is_p3_s_reach(tmp_path):
    """D struck once at its strike radius (1.55 with the bat); mix_2's P0 swing is at SWING_GUARD_R 1.0 only, and the
    idle zombie inside KEEP_R is T's `reach` rule at P3, fought to the kill."""
    r = world(tmp_path, [idle(1, 101.3, 200.0)])
    ws = wants(r)
    assert head(ws) == ("fight", K.P_FIGHT, "reach", 1) and [w.kind for w in ws] == ["fight", "order"]


def test_the_reach_rule_is_armed_only(tmp_path):
    r = world(tmp_path, [idle(1, 101.3, 200.0)], weapon=None)
    assert [w.kind for w in wants(r, seek=None)] == ["order"]


def test_a_hit_reaction_takes_the_nearest_standing_zombie_within_the_release(tmp_path):
    r = world(tmp_path, [zombie(1, 102.0, 200.0), zombie(2, 102.6, 200.0)], hit_reaction=HIT)
    assert head(wants(r)) == ("fight", K.P_GUARD, "hit", 1)
    r2 = world(tmp_path / "b", [zombie(1, 102.0, 200.0)])
    assert head(wants(r2))[:3] == ("fight", K.P_FIGHT, "reach")


def test_a_crawler_within_keep_r_is_a_p0_finish(tmp_path):
    r = world(tmp_path, [crawler(9, 102.3, 200.0)])
    assert head(wants(r)) == ("fight", K.P_GUARD, "crawler", 9)


def test_the_crawler_s_finish_comes_after_the_swing_and_before_a_standing_one_beyond_the_handback_radius(tmp_path):
    r = world(tmp_path, [crawler(9, 101.5, 200.0), idle(1, 100.9, 200.0)])
    assert head(wants(r)) == ("fight", K.P_GUARD, "swing", 1)
    r2 = world(tmp_path / "b", [crawler(9, 101.5, 200.0), zombie(1, 102.2, 200.0)])
    assert head(wants(r2)) == ("fight", K.P_GUARD, "crawler", 9)


def test_the_crawler_s_guard_yields_to_a_standing_zombie_within_the_meet_s_handback_radius(tmp_path):
    """Fix 1 (review-t13-mix2 F2a; trial 10's lines 98, 99 and 116: 15436 standing at 1.25 to 1.52 tiles by the
    crawler): the meet hands a finish back while a standing zombie is within HANDBACK_R, so the guard yields and P3's
    `reach` takes the standing one."""
    r = world(tmp_path, [crawler(9, 101.0, 200.0), idle(1, 101.4, 200.3)])
    ws = wants(r)
    assert head(ws) == ("fight", K.P_FIGHT, "reach", 1) and all(w.p != K.P_GUARD for w in ws)


def test_a_fallen_zombie_is_finished_only_with_none_standing_within_keep_r(tmp_path):
    r = world(tmp_path, [fallen(5, 101.5, 200.0)])
    assert head(wants(r)) == ("fight", K.P_GUARD, "fallen", 5)
    r2 = world(tmp_path / "b", [fallen(5, 101.5, 200.0), zombie(1, 102.2, 200.0)])
    ws = wants(r2)
    assert head(ws) == ("fight", K.P_FIGHT, "reach", 1) and all(w.p != K.P_GUARD for w in ws)


def test_a_fallen_zombie_beyond_fight_reach_is_d_s_downed_finish_at_p3(tmp_path):
    r = world(tmp_path, [fallen(5, 102.6, 200.0)])
    assert head(wants(r)) == ("fight", K.P_FIGHT, "downed", 5)


def test_a_backed_off_zombie_is_in_no_guard_and_a_skip_holds_off_the_finishes_only(tmp_path):
    r = world(tmp_path, [idle(1, 100.8, 200.0)])
    assert all(w.p != K.P_GUARD for w in wants(r, Memory(backoff={1: 3})))
    now = r.clock()
    assert head(wants(r, Memory(skip={1: now + 5.0}))) == ("fight", K.P_GUARD, "swing", 1)
    r2 = world(tmp_path / "b", [crawler(9, 102.3, 200.0)])
    assert all(w.p != K.P_GUARD for w in wants(r2, Memory(skip={9: now + 5.0})))


# ================================================================ P1: the dress waits (pure)
def test_a_bleeding_part_with_nothing_within_keep_r_is_dressed_first(tmp_path):
    r = world(tmp_path, [zombie(1, 106.0, 200.0)], wounds=bleed())
    hold_bandage(r)
    ws = wants(r)
    assert [w.kind for w in ws] == ["dress", "fight", "order"] and SI.piece_of(ws[0]) == "dress"


def test_a_crawler_within_keep_r_holds_the_dress_off_as_a_standing_one_does(tmp_path):
    now = None
    for i, zs in enumerate(([crawler(9, 102.3, 200.0)], [idle(1, 102.3, 200.0)])):
        r = world(tmp_path / str(i), zs, wounds=bleed())
        hold_bandage(r)
        now = r.clock()
        mem = Memory(skip={9: now + 5.0, 1: now + 5.0})   # skipped: no guard and no fight, the dress alone read
        assert "dress" not in [w.kind for w in wants(r, mem)], zs
    r = world(tmp_path / "c", [crawler(9, 103.0, 200.0)], wounds=bleed())
    hold_bandage(r)
    assert wants(r)[0].kind == "dress"   # beyond KEEP_R: the dress goes


# ================================================================ P3: the fight, the seek (pure)
def test_one_standing_aware_zombie_near_while_armed_is_fought_whatever_the_health(tmp_path):
    a = head(wants(world(tmp_path / "a", [zombie(1, 105.0, 200.0)], health=100.0)))
    b = head(wants(world(tmp_path / "b", [zombie(1, 105.0, 200.0)], health=1.0)))
    assert a == b == ("fight", K.P_FIGHT, "fight", 1)


def test_one_idle_zombie_listed_within_engage_r_is_sought_armed(tmp_path):
    r = world(tmp_path, [idle(1, 108.0, 200.0)])
    assert head(wants(r)) == ("fight", K.P_FIGHT, "seek", 1)


def test_two_idle_zombies_listed_are_never_sought(tmp_path):
    r = world(tmp_path, [idle(1, 108.0, 200.0), idle(2, 93.0, 200.0)])
    assert [w.kind for w in wants(r)] == ["order"]


def test_the_seek_counts_a_second_zombie_behind_a_wall_and_needs_its_reach(tmp_path):
    r = Rig(tmp_path, caps=CAPS)
    r.scan(grid(80, 125, 180, 220, at={(103, y): {"blockW": True, "edgeW": True} for y in range(195, 206)}))
    r.frame(zombies=[idle(1, 96.0, 200.0), idle(2, 106.0, 200.0)])   # 2 behind the wall at x=103
    assert [w.kind for w in wants(r)] == ["order"]
    r2 = world(tmp_path / "b", [idle(1, 108.0, 200.0)])
    assert [w.kind for w in wants(r2, seek=lambda zid, z: False)] == ["order"]
    assert [w.kind for w in wants(r2, seek=None)] == ["order"]
    r3 = world(tmp_path / "c", [idle(1, 108.0, 200.0)], weapon=None)
    assert [w.kind for w in wants(r3)] == ["order"]


def test_the_seek_s_reach_is_the_ladder_s_engageable(tmp_path):
    """`seek.Reach` runs `engage.Engage._engageable` over its own flood: an idle zombie on the far side of a building's
    walls is not engaged (`_side`), one on the character's side in the open is."""
    r = world(tmp_path, [idle(1, 108.0, 200.0)])
    reach = Reach(r.world, r.clock)
    z = r.world.zombies[1]
    assert reach.engageable(1, z) is True and reach.unsought == {}


def test_an_aware_zombie_is_fought_before_an_idle_one_is_sought(tmp_path):
    r = world(tmp_path, [idle(1, 104.0, 200.0), zombie(2, 107.0, 200.0)])
    assert head(wants(r)) == ("fight", K.P_FIGHT, "fight", 2)


def test_a_group_with_no_refuge_is_the_stand_and_a_named_refuge_the_avoid(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    ws = wants(r)
    assert head(ws) == ("fight", K.P_FIGHT, "stand", 1) and ws[0].why["stand"] is True
    r2, _ = avoid_rig(tmp_path / "b")
    ws2 = wants(r2)
    assert ws2[0].kind == "avoid" and SI.piece_of(ws2[0]) == "avoid" and ws2[0].target["label"] == "avoid_refuge"


# ================================================================ the intents on the fake mod
def test_mix_2_loads_by_name_and_names_its_piece_on_its_own_key(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame()
    tick(r, sv)
    d = last(tmp_path)
    assert sv.control == "mix_2" and set(sv.control_state) == {"mix_2"}
    assert "doctrine" not in d["inputs"] and d["inputs"]["mix_2"]["piece"] == "order"
    assert d["inputs"]["mix_2"]["pieces"] == ["order"] and d["inputs"]["intent"]["kind"] == "travel"
    assert set(d["inputs"]["mix_2"]) >= {"intent", "p", "why", "state", "target", "n", "preempted_by", "resumed",
                                         "ended", "slot", "wants", "piece", "pieces"}


def test_no_tactical_model_the_goal_source_is_the_doctrine_s_resume(tmp_path):
    r, sv = rig(tmp_path)
    r.frame()
    tick(r, sv)
    assert isinstance(sv.goals.source, Resume) and sv.DOOR_HELD is False
    assert not (tmp_path / "plays.log").exists()   # the tactician's play log: no play, no call


def test_the_swing_guard_sends_the_melee_at_p0_on_the_threat_branch(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[idle(1, 100.8, 200.0)])
    a = tick(r, sv)
    d = last(tmp_path)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, "strike")
    assert d["branch"] == "threat" and d["inputs"]["intent"] == {"kind": "fight", "target": 1}
    assert (d["inputs"]["mix_2"]["p"], d["inputs"]["mix_2"]["piece"]) == (K.P_GUARD, "swing")


def test_a_guard_fights_to_the_kill_never_one_press(tmp_path):
    """D's Strike ended `done press` on its first span; mix_2's guard is a Fight: after a press that did not kill, the
    same intent sends the melee at the same zombie again."""
    r, sv = rig(tmp_path)
    zs = [idle(1, 100.8, 200.0)]
    r.frame(zombies=zs)
    tick(r, sv)
    n0 = mix(tmp_path)["n"]
    r.answer("progress", "done")   # the span ends: no kill
    r.advance(0.5)
    r.frame(zombies=[idle(1, 101.6, 200.0)])   # knocked back past the swing radius
    a = tick(r, sv)
    m = mix(tmp_path)
    assert m["n"] == n0 and m["p"] == K.P_GUARD and m["ended"] is None
    assert (a.type, a.args["targetId"]) == ("melee", 1)


def test_a_fight_repins_to_a_nearer_standing_zombie_within_keep_r(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 102.4, 200.0)])
    tick(r, sv)
    assert mix(tmp_path)["piece"] == "reach"
    r.answer("accepted")
    r.frame(zombies=[zombie(1, 102.4, 200.0), zombie(2, 98.2, 200.0)])
    a = tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["why"] == "repin" and m["ended"]["p"] == K.P_FIGHT
    assert m["repin"] == {"id": 2, "by": "second_standing", "pin": 1, "end": "done"}   # fix 1, F3: on the line
    assert (m["target"], m["piece"]) == (2, "reach") and (a.type, a.args["targetId"]) == ("melee", 2)


def test_a_finish_repins_to_a_standing_zombie_in_the_swing_radius(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[fallen(5, 101.5, 200.0)])
    a = tick(r, sv)
    assert (a.type, a.args["mode"]) == ("melee", "finish") and mix(tmp_path)["piece"] == "fallen"
    r.answer("accepted")
    r.frame(zombies=[fallen(5, 101.5, 200.0), idle(2, 99.1, 200.0)])
    a = tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["why"] == "repin" and (m["target"], m["piece"], m["p"]) == (2, "swing", K.P_GUARD)
    assert m["repin"] == {"id": 2, "by": "swing", "pin": 5, "end": "done"}
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 2, "strike")


def test_a_hit_reaction_repins_a_finish_to_the_standing_zombie_within_the_release(tmp_path):
    """T's `hit` guard takes any play: the finish of a fallen zombie ends `done repin` once a hit reaction reads with
    a standing zombie within MELEE_RELEASE_R (beyond KEEP_R here, so neither the swing nor `second_standing` reads)."""
    r, sv = rig(tmp_path)
    r.frame(zombies=[fallen(5, 101.5, 200.0), zombie(2, 102.9, 200.0)])
    tick(r, sv)
    assert mix(tmp_path)["piece"] == "fallen"
    r.answer("accepted")
    r.frame(zombies=[fallen(5, 101.5, 200.0), zombie(2, 102.6, 200.0)], hit_reaction=HIT)
    a = tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["why"] == "repin" and (m["target"], m["piece"], m["p"]) == (2, "hit", K.P_GUARD)
    assert m["repin"] == {"id": 2, "by": "hit", "pin": 5, "end": "done"}
    assert (a.type, a.args["targetId"]) == ("melee", 2)


def test_the_meet_s_handback_ends_the_finish_done_repin_and_the_standing_one_is_fought(tmp_path):
    """T's pattern (the read's section 2: knock down the nearest, turn to the next standing one, then finish the
    fallen): the meet hands a finish back for a standing zombie within its HANDBACK_R, beyond the swing radius and with
    the pin down (so neither guard nor `second_standing` reads it); the Fight ends `done repin` and P3's `reach` takes
    the standing one."""
    r, sv = rig(tmp_path)
    r.frame(zombies=[fallen(5, 101.5, 200.0)])
    a = tick(r, sv)
    assert (a.type, a.args["mode"]) == ("melee", "finish")
    other_end(r, 2, 1.8)
    r.frame(zombies=[fallen(5, 101.5, 200.0), zombie(2, 101.7, 200.6)])
    a = tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["why"] == "repin" and (m["target"], m["piece"]) == (2, "reach")
    assert m["repin"] == {"id": 2, "by": "handback", "n": 1, "pin": 5, "end": "done"}
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 2, "strike")


def test_the_crawler_is_finished_before_the_dress(tmp_path):
    r, sv = rig(tmp_path)
    hold_bandage(r)
    r.frame(zombies=[crawler(9, 101.5, 200.0)], wounds=bleed())
    a = tick(r, sv)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 9, "finish")
    assert mix(tmp_path)["piece"] == "crawler" and "dress" not in mix(tmp_path)["wants"]


def test_a_running_dress_fails_crawler_near(tmp_path):
    r, sv = rig(tmp_path)
    hold_bandage(r)
    r.frame(wounds=bleed())
    a = tick(r, sv)
    assert a.type == "stop" and mix(tmp_path)["intent"] == "dress"
    mix_of(sv).mem.skip[9] = r.clock() + 10.0   # skipped: the crawler's guard holds off, the dress's own test reads it
    r.answer()
    r.frame(zombies=[crawler(9, 102.3, 200.0)], wounds=bleed())
    tick(r, sv)
    assert mix(tmp_path)["ended"] == {"intent": "dress", "p": K.P_DRESS, "end": "failed", "why": "crawler near"}


def test_the_seek_closes_on_the_lone_idle_zombie_with_the_doctrine_s_close_leg(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[idle(1, 108.0, 200.0)])
    a = tick(r, sv)
    d = last(tmp_path)
    assert a.type == "walkTo" and a.args["gait"] == "walk" and a.args["x"] > 100.0
    assert d["inputs"]["mix_2"]["piece"] == "seek" and d["inputs"]["mix_2"]["state"] == "close"
    assert d["inputs"]["intent"] == {"kind": "fight", "target": 1} and d["branch"] == "threat"


def test_no_string_a_pair_arriving_together_is_met_in_the_stance(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 106.0, 200.0), zombie(2, 106.5, 200.5)])
    a = tick(r, sv)
    d = last(tmp_path)
    assert (a.type, a.args["vx"], a.args["vy"]) == ("aim", 0.0, 0.0) and d["inputs"]["mix_2"]["state"] == "stand"
    assert "play" not in d["inputs"]
    TS = trial_score()
    assert TS._retreat_label(d) is None and "fight" in TS._labels(d)


def test_a_dress_preempts_the_goal_and_the_goal_resumes_after(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame()
    tick(r, sv)
    goal = sv.goals.current
    hold_bandage(r)
    r.frame(wounds=bleed())
    a = tick(r, sv)
    m = mix(tmp_path)
    assert a.type == "stop" and m["piece"] == "dress" and m["preempted_by"] == {"was": "order", "p": K.P_ORDER}
    r.answer()
    r.frame()
    tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["intent"] == "dress" and m["resumed"] is True and m["resumed_goal"] == "ExploreToward"
    assert sv.goals.current is not None and sv.goals.current.args() == goal.args()


def test_an_avoid_runs_to_its_refuge_with_the_scorecard_s_retreat_label(tmp_path):
    from .test_survive_ag import SHUT, door_ground
    from .test_survive_g import Src
    r = Rig(tmp_path, caps=CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None), control="mix_2")
    r.scan(door_ground(SHUT))
    me = (10774.0, 10633.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(i, x, y, me=me) for i, x, y in GROUP_EAST])
    a = tick(r, sv)
    d = last(tmp_path)
    assert a.type == "walkTo" and a.args["gait"] == "run" and d["inputs"]["branches"]["threat"]["flee"] == "group"
    assert d["inputs"]["mix_2"]["piece"] == "avoid" and trial_score()._retreat_label(d) == "avoid_refuge"


def test_line_switches_reads_a_same_priority_switch_off_mix_2_s_key():
    rows = [{"inputs": {"mix_2": {"n": 1, "p": 3, "ended": None}}},
            {"inputs": {"mix_2": {"n": 2, "p": 3, "ended": None}}},
            {"inputs": {"mix_2": {"n": 3, "p": 3, "ended": {"why": "repin"}}}},
            {"inputs": {"doctrine": {"n": 9, "p": 3}}}]
    assert line_switches(rows) == 1


def test_the_fight_never_ends_on_health(tmp_path):
    r, sv = rig(tmp_path)
    for i in range(20):
        r.frame(zombies=[zombie(1, 106.0 - 0.2 * i, 200.0)], health=1.0)
        tick(r, sv)
        r.advance(0.5)
    m = mix_of(sv)
    assert m.arbiter.current.kind == "fight" and not m.arbiter.ends


# ================================================================ fix 1 (review-t13-mix2)
def test_the_tick_is_d_s_but_for_its_named_lines():
    """The drift guard on the copied `tick` (F5): `Mix2.tick` is `Doctrine.tick` with D's module-level read replaced by
    `self.read()` and the lines marked `# mix_2` (the re-pin's record for the line) added; nothing else differs."""
    import inspect
    import textwrap
    from agent.base.planner.doctrine.assess import Doctrine
    from agent.base.planner.mix_2.assess import Mix2

    def body(f):
        src = textwrap.dedent(inspect.getsource(f))
        out, doc = [], False
        for ln in src.splitlines():
            t = ln.strip()
            if t.startswith('"""'):
                doc = not (t.endswith('"""') and len(t) > 3) and not doc
                continue
            if doc:
                doc = not t.endswith('"""')
                continue
            out.append(ln.rstrip())
        return out
    d = [ln.replace("situation.read(self.world, self.mem, self.now())", "self.read()") for ln in body(Doctrine.tick)]
    m = [ln for ln in body(Mix2.tick) if "# mix_2" not in ln]
    assert m == d
    assert sum("# mix_2" in ln for ln in body(Mix2.tick)) == 3


def seek_rig(tmp_path, zs):
    r, sv = rig(tmp_path)
    r.frame(zombies=zs)
    a = tick(r, sv)
    assert mix(tmp_path)["piece"] == "seek" and a.type == "walkTo"
    r.answer("accepted")
    return r, sv


def test_a_seek_ends_lapsed_when_more_idle_zombies_list_beyond_danger_r(tmp_path):
    """F1, probe 1's shape: a seek at an idle zombie 8 tiles off; five more idle zombies list at 8 tiles: the seek's
    own predicate no longer holds and the pin is beyond DANGER_R, so the Fight ends `done lapsed` and the arbiter's
    next answer (the order: two or more idle, none sought) takes the tick."""
    r, sv = seek_rig(tmp_path, [idle(1, 108.0, 200.0)])
    more = [idle(10 + i, 100.0 + 8.0 * c, 200.0 + 8.0 * s_) for i, (c, s_) in
            enumerate(((-1, 0), (0, 1), (0, -1), (-0.6, 0.8), (-0.6, -0.8)))]
    r.frame(zombies=[idle(1, 108.0, 200.0)] + more)
    tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"] == {"intent": "fight", "p": K.P_FIGHT, "end": "done", "why": "lapsed"} and m["intent"] == "order"


def test_a_seek_ends_lapsed_when_its_pin_is_no_longer_engageable(tmp_path):
    r, sv = seek_rig(tmp_path, [idle(1, 108.0, 200.0)])
    mix_of(sv).reach.engageable = lambda zid, z: False   # the ladder's `_engageable` turned false mid-seek
    r.frame(zombies=[idle(1, 108.0, 200.0)])
    tick(r, sv)
    assert mix(tmp_path)["ended"]["why"] == "lapsed" and mix(tmp_path)["intent"] == "order"


def test_an_aware_newcomer_ends_the_seek_and_d_s_fight_takes_it(tmp_path):
    r, sv = seek_rig(tmp_path, [idle(1, 108.0, 200.0)])
    r.frame(zombies=[idle(1, 108.0, 200.0), zombie(2, 94.0, 200.0)])
    tick(r, sv)
    m = mix(tmp_path)
    assert m["ended"]["why"] == "lapsed" and (m["intent"], m["piece"], m["target"]) == ("fight", "fight", 2)


def test_a_seek_inside_danger_r_runs_on_when_its_predicate_lapses(tmp_path):
    """Trial 2's 245-251 s shape: 9815 lists idle at 8.2 tiles while the seek's pin 9812 stands at 3.8, inside
    DANGER_R: the Fight runs on."""
    r, sv = seek_rig(tmp_path, [idle(1, 105.5, 200.0)])
    n0 = mix(tmp_path)["n"]
    r.frame(zombies=[idle(1, 103.8, 200.0), idle(2, 91.8, 200.0)])
    tick(r, sv)
    m = mix(tmp_path)
    assert m["n"] == n0 and m["ended"] is None and m["piece"] == "seek" and "seek" not in m["pieces"]


def test_a_crawler_finish_handed_back_for_a_standing_zombie_goes_to_the_standing_one(tmp_path):
    """F2a, probe 4's shape (a): a crawler pinned at P0, a standing zombie arriving between SWING_GUARD_R and the
    meet's HANDBACK_R: the meet hands the finish back, and the next Fight is the standing one's (P3's `reach`), never
    the crawler's again."""
    r, sv = rig(tmp_path)
    r.frame(zombies=[crawler(9, 101.0, 200.0)])
    a = tick(r, sv)
    assert (a.type, a.args["targetId"], mix(tmp_path)["piece"]) == ("melee", 9, "crawler")
    other_end(r, 1, 1.5)
    zs = [crawler(9, 101.0, 200.0), idle(1, 101.4, 200.6)]
    for i in range(4):
        r.frame(zombies=zs)
        a = tick(r, sv)
        m = mix(tmp_path)
        assert (m["target"], m["piece"]) == (1, "reach") and (a is None or a.args.get("targetId") == 1), m
        if i == 0:
            assert m["repin"]["by"] == "handback" and (a.type, a.args["targetId"]) == ("melee", 1)
            r.answer("accepted")


def test_the_handback_loop_at_one_pin_is_bounded_at_handback_max(tmp_path):
    """F2b, probe 4's shape (b): two standing zombies within the meet's STAND_R 0.6, the pin the nearer, the meet
    handing back before every press: the swing guard names the pin again after each re-pin until HANDBACK_MAX
    handbacks in a row, then the pin is held and the Fight ends `failed handback`, the arbiter's next answer (the
    other zombie) taking the tick. Five handbacks in a row at one pin never happen."""
    r, sv = rig(tmp_path)
    zs = [idle(1, 100.4, 200.0), idle(2, 100.0, 200.5)]
    r.frame(zombies=zs)
    tick(r, sv)
    runs, ends = [], []
    for _ in range(10):
        pin = mix(tmp_path)["target"]
        other_end(r, 2 if pin == 1 else 1, 0.5)
        r.frame(zombies=zs)
        tick(r, sv)
        m = mix(tmp_path)
        rp = m.get("repin")
        if rp is not None and rp["by"] == "handback":
            runs.append(rp["pin"])
            ends.append(rp["end"])
    streak, best = 0, 0
    for i, pin in enumerate(runs):
        streak = streak + 1 if i and runs[i - 1] == pin else 1
        best = max(best, streak)
    assert best == K.HANDBACK_MAX and "failed" in ends, (runs, ends)
    assert runs[:K.HANDBACK_MAX] == [1] * K.HANDBACK_MAX and runs[K.HANDBACK_MAX] == 2
    assert 1 in mix_of(sv).mem.hold or 1 in mix_of(sv).mem.skip


def test_a_handback_count_clears_when_a_fight_at_the_pin_ends_otherwise(tmp_path):
    r, sv = rig(tmp_path)
    zs = [idle(1, 100.4, 200.0), idle(2, 100.0, 200.5)]
    r.frame(zombies=zs)
    tick(r, sv)
    for _ in range(K.HANDBACK_MAX - 1):
        other_end(r, 2, 0.5)
        r.frame(zombies=zs)
        tick(r, sv)
    assert mix_of(sv).handbacks == {1: K.HANDBACK_MAX - 1}
    r.event("zombie_dead", id=1)
    r.frame(zombies=zs[1:])
    tick(r, sv)
    assert 1 not in mix_of(sv).handbacks



def test_a_seek_whose_lone_pin_drifts_just_past_seek_r_runs_on(tmp_path):
    """The seek's hysteresis (fix 1, F1; trial 4's 6073 at 9.2 to 9.6 tiles): the end reads the pin at any distance
    inside DISENGAGE_R, so a lone idle pin just past SEEK_R keeps its Fight."""
    r, sv = seek_rig(tmp_path, [idle(1, 108.8, 200.0)])
    n0 = mix(tmp_path)["n"]
    r.frame(zombies=[idle(1, 109.4, 200.0)])
    tick(r, sv)
    m = mix(tmp_path)
    assert m["n"] == n0 and m["ended"] is None and m["piece"] == "seek"
