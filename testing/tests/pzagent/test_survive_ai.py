"""Plan 32 Task 5 (the coward fix; Angus's direction of 2026-11-08 watching F17, memories `finish-actions-gain-distance`,
`stand-and-fight-dress-first`, `combat-approach-not-flee`): `survive.T16_SWITCHES`, four planner rules on by default,
each with its replay test on the live session F17's decision lines (`f_goals_17-20261108-172833`, its `decision.log`
over `state.log` and its rotation `state.1.log`, read together as the artifact's GUIDE.md § 0 says: seq 1-15921 then
15922-16588) and its unit tests on the fake mod; each replay is `replay_decisions.replay`, open loop: it checks the
decisions at the situations the run recorded, never an outcome.

- (a) POINT_BLANK_FIGHT (`threat.Threat._point_blank`): a standing zombie within KEEP_R is fought whatever flee reason
  the plan would take (`many`, `pair`, `strain`, `held`, `flip`, `unarmed`, the group steer's default `many`); the
  exceptions: the health under FLEE_HEALTH_FLOOR, and a running retreat to a named structure (the Flee's shelter plan or
  way out, `steps`; the sheltered Flee's, the doorway stand and the drag-down guard's rows keep their own rules). F17's
  line 145 (the group steer's `flee:many` at 0.1848981257193573 tiles from 16101, the tick after the `attack` at it,
  the first wound's seq 1613-1621) replays as the fight at 16101.
- (b) PAIR_NEAREST (the Fight's `pair_nearest` rule, `fight.Fight._pair_pin`).
- (c) CARE_COMMIT (`care_yield.CareYield._care_commit`).
- (d) STRAIN_BOUND (`hold.Hold._strain_flees`).
"""
import functools
import json
import os
import shutil
import tempfile

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import care as C
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import Rig, zombie
from .test_survive import last, make, threat_why, tick
from .test_survive_ah import scratch, scratch_rig
from .test_survive_ah import zombie as ah_zombie

F17 = os.path.join(R.ARTIFACTS, "f_goals_17-20261108-172833")
T16 = S.T16_SWITCHES


@functools.lru_cache(maxsize=12)
def _f17(switches):
    """F17 replayed (every line) with `switches` ((name, value) pairs) set on the fresh Survive, as JSON."""
    if not os.path.isfile(os.path.join(F17, "state.1.log")):
        pytest.skip("%s is not checked out" % F17)
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "state.log"), "wb") as out:
            for name in ("state.log", "state.1.log"):   # GUIDE.md § 0: state.log first, then its rotation
                with open(os.path.join(F17, name), "rb") as src:
                    shutil.copyfileobj(src, out)
        shutil.copy(os.path.join(F17, "decision.log"), os.path.join(d, "decision.log"))

        def mutate(sv):
            for name, v in switches:
                setattr(sv, name, v)
        return json.dumps(R.replay(d, mutate=mutate))


def f17(**switches):
    """F17's replayed decision lines (list index line - 1) with `switches` set. Pinned with Plan 33 Task 2's
    CRAWLER_FIRST off (`T17_SWITCHES`) and Plan 33 Task 3's group rules off (`T18_SWITCHES`, fix 1: GROUP_LEAVE's
    entry at GROUP_ENTRY_R reaches F17's lines) and Plan 34's CRAWLER_CLEAR off (ruling P34-A fix B: F17's fallen
    16230 within CRAWLER_AVOID_R beside the standing 16232 is backpedalled from), named changes that move F17's lines,
    unless a case sets them; and with Plan 34 Task 3c fix 1's POINT_BLANK_OVER_R at KEEP_R (the rule before it: its
    `many` and `health` point-blank fights between 1.5 and 2.5 tiles), a named change that moves F17's lines."""
    switches = dict({k: False for k in S.T18_SWITCHES}, **switches)
    switches.setdefault("CRAWLER_FIRST", False)
    switches.setdefault("CRAWLER_CLEAR", False)
    switches.setdefault("POINT_BLANK_OVER_R", P.KEEP_R)
    return json.loads(_f17(tuple(sorted(switches.items()))))


def only(name=None):
    """The T16 switches all off but `name`."""
    return {k: k == name for k in T16}


@functools.lru_cache(maxsize=1)
def record():
    with open(os.path.join(F17, "decision.log"), encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def action(row):
    return (row.get("action") or {}).get("type")


def flee_counts(rows):
    out = {}
    for r in rows:
        why = threat(r).get("flee")
        if why:
            out[why] = out.get(why, 0) + 1
    return out


def test_the_t16_switches():
    """`survive.T16_SWITCHES`, each on by default (`Plan 32 Task 5: the coward rules on by default`)."""
    assert T16 == ("POINT_BLANK_FIGHT", "PAIR_NEAREST", "CARE_COMMIT", "STRAIN_BOUND")
    assert all(getattr(S.Survive, k) is True for k in T16)


def test_with_the_four_off_f17_replays_as_recorded():
    """The replay's own baseline: with the four off, F17 replays to its record's flee counts (`f_grade.txt`'s `fleeing`
    reasons: strain 158, held 80, unreachable 46, pair 36, many 29, flip 21, health 14, held_inside 4, broken 1) and
    line 145's steer."""
    rows = f17(**only())
    assert flee_counts(rows) == flee_counts(record()) == {"strain": 158, "held": 80, "unreachable": 46, "pair": 36,
                                                          "many": 29, "flip": 21, "health": 14, "held_inside": 4,
                                                          "broken": 1}
    assert rows[144]["action"] == record()[144]["action"] and action(rows[144]) == "steer"


def rig(tmp_path, zombies, on=("POINT_BLANK_FIGHT",), **frame):
    """A Survive on a fresh Rig with the T16 switches in `on` set on and the others off (each rule read alone), one
    frame. Pinned with Plan 34 Task 3c fix 1's POINT_BLANK_OVER_R at KEEP_R (the rule before it, a named change: the
    `health` pair at 2.2 tiles below is fought by the rule before it, fled by it)."""
    r, sv = make(tmp_path)
    sv.POINT_BLANK_OVER_R = P.KEEP_R
    for name in T16:
        setattr(sv, name, name in on)
    r.frame(zombies=zombies, **frame)
    return r, sv


# ================================================================ (a) no flee at point blank
def test_f17_line_145_s_many_steer_at_point_blank_is_the_fight_at_16101():
    """(a), F17's first wound: line 144 attacked 16101 at 0.26690008755765005 tiles; line 145's group steer (`group`
    "hold": five held within DISENGAGE_R, one standing within DANGER_R, `many_near` {n 1}) fled `many` at
    0.1848981257193573. With POINT_BLANK_FIGHT alone on line 145 is the fight pinned on 16101, logged
    `point_blank_fight` {target 16101, over "many"}, holding its send in the bite's hit reaction (`hitReaction` "Bite":
    the engine starts no swing in one); off, the record's steer."""
    on = f17(**only("POINT_BLANK_FIGHT"))[144]
    why = threat(on)
    assert on["branch"] == "threat" and on["action"] is None and why.get("flee") is None and why.get("fight") is True
    assert why["point_blank_fight"] == {"target": 16101, "dist": 0.1848981257193573, "over": "many"}
    assert why["target"] == 16101 and why["hitReaction"] == "Bite"
    off = f17(**only())[144]
    assert action(off) == "steer" and threat(off)["flee"] == "many"


def near_flees(rows):
    """The decision lines (1-based) that flee with the nearest listed zombie within KEEP_R (`inputs.nearest`)."""
    return [k for k, r in enumerate(rows, 1) if threat(r).get("flee") and (r["inputs"].get("nearest") or 99.0) <= P.KEEP_R]


def test_f17_s_flees_at_point_blank_fall_from_43_to_12():
    """(a) over the whole of F17, open loop: with POINT_BLANK_FIGHT alone on the flee lines fall from 389 to 331 (`many`
    29 to 9, `held` 80 to 56, `pair` 36 to 27, `flip` 21 to 17, `health` 14 to 13) and those with the nearest listed
    zombie within KEEP_R from 43 to 12; each of the 12 left reads no standing target a Fight may take within KEEP_R (the
    nearest across a blocked line or marked unreachable, `unreachable` lines 461-462 and 528-533 at 0.51 to 2.26 tiles;
    the `many` lines 269 and 276; the `health` lines 790 and 805), so none logs `point_blank_fight`."""
    on, off = f17(**only("POINT_BLANK_FIGHT")), f17(**only())
    assert len(near_flees(off)) == 43 and sum(flee_counts(off).values()) == 389
    assert flee_counts(on) == {"strain": 158, "held": 56, "unreachable": 46, "pair": 27, "many": 9, "flip": 17,
                               "health": 13, "held_inside": 4, "broken": 1}
    left = near_flees(on)
    assert left == [269, 276, 461, 462, 528, 529, 530, 531, 532, 533, 790, 805]
    assert all("point_blank_fight" not in threat(on[k - 1]) for k in left)


@pytest.mark.parametrize("health, fought", [(50.0, True), (P.FLEE_HEALTH_FLOOR, True), (19.0, False)])
def test_a_pair_flee_at_point_blank_is_fought_above_the_floor(tmp_path, health, fought):
    """(a) on the fake mod: two zombies within DANGER_R under FLEE_HEALTH_PAIR read `pair` (under FLEE_HEALTH,
    `health`); the nearer standing 2.2 tiles off (within KEEP_R, beyond CORNERED_R's walk corner) makes it the fight at
    it (logged `point_blank_fight` {over "pair" or "health"}), down to FLEE_HEALTH_FLOOR; under it the flee stays."""
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0), zombie(2, 100.0, 204.0)], health=health)
    tick(r, sv)
    why = threat_why(tmp_path)
    if fought:
        assert why.get("flee") is None and why["point_blank_fight"]["target"] == 1
        assert why["point_blank_fight"]["over"] == ("pair" if health >= P.FLEE_HEALTH else "health")
        assert why["target"] == 1 and sv.fight.target == 1
    else:
        assert why.get("flee") == "health" and "point_blank_fight" not in why


def test_with_point_blank_fight_off_the_pair_at_point_blank_flees(tmp_path):
    """The falsifier: the same two with the rule off flee `pair`."""
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0), zombie(2, 100.0, 204.0)], on=(), health=50.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "pair" and r.cmd()[0] == "steer"


def test_a_fallen_zombie_or_one_beyond_keep_r_makes_no_point_blank_fight(tmp_path):
    """(a)'s reads: the zombie within KEEP_R must stand (one `onFloor` is no point-blank fight), and one at 2.6 tiles
    (beyond KEEP_R 2.5) leaves the `pair` flee as it was."""
    fallen = dict(zombie(1, 102.2, 200.0), onFloor=True)
    r, sv = rig(tmp_path, [fallen, zombie(2, 100.0, 204.0)], health=50.0)
    tick(r, sv)
    assert "point_blank_fight" not in threat_why(tmp_path)
    (tmp_path / "far").mkdir()
    r2, sv2 = rig(tmp_path / "far", [zombie(1, 102.6, 200.0), zombie(2, 100.0, 204.0)], health=50.0)
    tick(r2, sv2)
    assert threat_why(tmp_path / "far").get("flee") == "pair"


def test_a_running_retreat_to_a_named_structure_is_kept_at_point_blank(tmp_path):
    """(a)'s refuge exception: the reason `steps` (a `many` episode's shelter plan or way out running) is never
    fought, whatever stands within KEEP_R; any other reason is (`_point_blank` read directly: the Flee's walk to a
    named structure is the refuge ruling's retreat)."""
    r, sv = rig(tmp_path, [zombie(1, 101.5, 200.0)], health=80.0)
    assert sv._point_blank("steps") is None and sv.point_blank_fight is None
    got = sv._point_blank("held")
    assert got == {"target": 1, "dist": 1.5, "over": "held"}
    sv.POINT_BLANK_FIGHT = False
    assert sv._point_blank("held") is None


# ================================================================ (b) the pair: the nearer standing faced and shoved first
def fight_rig(tmp_path, zs, rule=True):
    """A Fight on a fresh Rig over one frame of `zs`, its rules the defaults with `pair_nearest` on or off; pinned
    with Plan 33 Task 2's `crawler_first` off (a named change: a fallen zombie within CRAWLER_R beside a standing one
    is that rule's) and Plan 34's `crawler_clear` off (ruling P34-A fix B, a named change: a fallen zombie within
    CRAWLER_AVOID_R beside the pair's standing pin is backpedalled from)."""
    r = Rig(tmp_path)
    r.frame(zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = (f.rules | {"pair_nearest"}) if rule else (f.rules - {"pair_nearest"})
    f.rules = f.rules - {"crawler_first", "crawler_clear"}
    return r, f


def at(zid, x, floor=False):
    return dict(zombie(zid, x, 200.0), onFloor=floor)


def test_pair_nearest_is_a_fight_rule():
    assert "pair_nearest" in F.FIGHT_RULES and P.PAIR_SWITCH_R == 0.3


def test_a_standing_zombie_within_keep_r_beside_a_fallen_one_is_the_target_not_the_floor_swing(tmp_path):
    """(b), F17's seq 7432-7495 on the fake mod: 16230 lay fallen at 0.3 tiles and 16232 stood at 1.17; the Fight's
    finish (P24-AL, P27-G's floor swing) attacked the fallen one while the standing one bit. With the rule on the
    standing one is the target (logged `pair_nearest` {target, n 2, standing 1}) and nothing goes at the fallen one;
    off, the floor swing at it as before."""
    zs = [at(1, 101.3), at(2, 100.3, floor=True)]
    r, f = fight_rig(tmp_path, zs)
    cmd = f.choose()
    assert f.target == 1 and f.why["pair_nearest"] == {"target": 1, "n": 2, "standing": 1}
    assert getattr(cmd, "targetId", 1) == 1
    (tmp_path / "off").mkdir()
    r2, f2 = fight_rig(tmp_path / "off", zs, rule=False)
    cmd2 = f2.choose()
    assert (cmd2.TYPE, cmd2.targetId) == ("attack", 2) and "pair_nearest" not in f2.why


@pytest.mark.parametrize("x2, want", [(101.6, 2), (101.85, 1)])
def test_the_pin_switches_only_when_the_other_is_nearer_by_pair_switch_r(tmp_path, x2, want):
    """(b)'s hysteresis: two standing within KEEP_R, the pin on 1 at 2.0 tiles; 2 at 1.6 tiles (0.4 nearer, past
    PAIR_SWITCH_R) takes the pin, 2 at 1.85 (0.15 nearer) leaves it on 1."""
    r, f = fight_rig(tmp_path, [at(1, 102.0), at(2, x2)])
    f.target = 1
    f.choose()
    assert f.target == want and f.why["pair_nearest"]["target"] == want


def test_with_one_within_keep_r_the_pair_rule_reads_nothing(tmp_path):
    """One standing within KEEP_R and the other at 3.0: no pair read (the Fight's own target rules)."""
    r, f = fight_rig(tmp_path, [at(1, 101.5), at(2, 103.0)])
    f.choose()
    assert "pair_nearest" not in f.why


def test_f17_s_pair_holds_16232_where_the_record_traded_targets():
    """(b) on F17's lines 752 to 766 (seq 7423-7512): the record's targets traded between 16230 (fallen from line 751,
    attacked on lines 752, 758, 762 and 766) and 16232 (standing, shoved on 760 and 764) while 16232 bit. With
    PAIR_NEAREST alone on, every threat line from 753 to 766 whose frame lists both within KEEP_R and 16232 standing
    pins 16232 (`pair_nearest` {target 16232}), and no attack goes at 16230 on them; off, the record's trade."""
    on, off = f17(**only("PAIR_NEAREST")), f17(**only())
    lines = [k for k in range(753, 767) if threat(on[k - 1]).get("pair_nearest")]
    assert lines and all(threat(on[k - 1])["pair_nearest"]["target"] == 16232 for k in lines)
    assert not any(action(on[k - 1]) == "attack" and on[k - 1]["action"]["args"]["targetId"] == 16230 for k in lines)
    assert [k for k in range(752, 767) if action(off[k - 1]) == "attack"
            and off[k - 1]["action"]["args"]["targetId"] == 16230] == [752, 758, 762, 766]


# ================================================================ (d) the strain flee bounded to a real exhaustion
def test_strain_endurance_is_the_endurance_moodle_s_second_level():
    """(d)'s line: STRAIN_ENDURANCE 0.5, the ENDURANCE moodle's level 2 edge (#3926: level 1 while above 0.5, level 2 at
    0.5 or under), under ENDURANCE_T (0.75, level 1, the hold's start)."""
    assert P.STRAIN_ENDURANCE == 0.5 < P.ENDURANCE_T


def strain_rig(tmp_path, endurance, zombies, on=("STRAIN_BOUND",)):
    return rig(tmp_path, zombies, on=on, endurance=endurance)


@pytest.mark.parametrize("endurance, flee", [(0.7, None), (0.45, "strain")])
def test_two_standing_within_danger_r_flee_strain_only_under_a_real_exhaustion(tmp_path, endurance, flee):
    """(d): two standing within DANGER_R under the endurance hold: at 0.7 (level 1, F17's 158 lines read 0.643 to
    0.741) no `strain` flee (logged `strain_bound` {endurance, standing 2}), the fight; at 0.45 (level 2) the flee."""
    r, sv = strain_rig(tmp_path, endurance, [zombie(1, 104.0, 200.0), zombie(2, 100.0, 204.0)])
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why.get("flee") == flee
    if flee is None:
        assert why["strain_bound"] == {"endurance": endurance, "standing": 2} and why.get("fight") is True


def test_exactly_one_standing_within_danger_r_is_never_fled_strain(tmp_path):
    """(d): at 0.45 (a real exhaustion) with exactly one standing within DANGER_R and a second chaser listed at 9 tiles
    (so P27-C's hold fight does not take it), no `strain` flee (`strain_bound` {standing 1}); with the rule off, the
    flee as before."""
    zs = [zombie(1, 104.0, 200.0), zombie(2, 109.0, 200.0)]
    r, sv = strain_rig(tmp_path, 0.45, zs)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why.get("flee") != "strain" and why["strain_bound"] == {"endurance": 0.45, "standing": 1}
    (tmp_path / "off").mkdir()
    r2, sv2 = strain_rig(tmp_path / "off", 0.45, zs, on=())
    tick(r2, sv2)
    assert threat_why(tmp_path / "off").get("flee") == "strain"


def test_f17_s_158_strain_lines_fall_to_none():
    """(d) on F17: every one of its 158 `strain` lines (from line 1173) read the endurance hold alone at endurance
    0.6427835822105408 to 0.7410425543785095, the moodle's first level; with STRAIN_BOUND alone on none flees `strain`,
    each of them logging `strain_bound`; off, the 158."""
    on, off = f17(**only("STRAIN_BOUND")), f17(**only())
    lines = [k for k, r in enumerate(off, 1) if threat(r).get("flee") == "strain"]
    assert len(lines) == 158 and lines[0] == 1173
    ends = [threat(off[k - 1])["strain"]["endurance"] for k in lines]
    assert min(ends) == 0.6427835822105408 and max(ends) == 0.7410425543785095
    assert {threat(off[k - 1])["strain"]["kind"] for k in lines} == {"endurance"}
    assert flee_counts(on).get("strain") is None
    assert all("strain_bound" in threat(on[k - 1]) for k in lines if on[k - 1]["branch"] == "threat")


# ================================================================ (c) one leg, then finish
def test_the_care_leg_s_constants():
    """(c)'s leg: to CARE_HOLD_R + CARE_MARGIN (3.0 + 0.5 tiles), at most CARE_LEG_S (6.0 s), at a walk."""
    assert (C.CARE_HOLD_R, C.CARE_MARGIN, C.CARE_LEG_S) == (3.0, 0.5, 6.0)


def commit_rig(tmp_path, on=True):
    """The scratch rig of Plan 31 Task 15a (`test_survive_ah.scratch_rig`: a PZA/1.7 hello, the worn cotton T-shirt
    alone held, part 9 scratched) with CARE_COMMIT `on`."""
    r, sv = scratch_rig(tmp_path)
    sv.CARE_COMMIT = on
    return r, sv


def step(r, sv, dx, chasing=True):
    """Half a second on, one frame with zombie 7 `dx` tiles east of the player and part 9 scratched, one tick."""
    r.advance(0.5)
    r.frame(zombies=[ah_zombie(7, dx, chasing=chasing)], wounds={"parts": [scratch()], "bleeding": 0})
    tick(r, sv)


def test_a_scratch_wanted_with_a_chaser_inside_care_hold_r_takes_one_walk_away_then_the_dress(tmp_path):
    """(c): the scratch's Dress wanted with a chaser 2.8 tiles off (inside CARE_HOLD_R, beyond KEEP_R): the threat branch
    sends one walk directly away from it (`steer` west, CARE_LEG_S, `walk`), logged `care_commit` {phase "leg"}; the leg
    holds while the chaser stays under CARE_HOLD_R + CARE_MARGIN (3.2 tiles: `phase` "hold"), and once it reads 3.6 the
    leg is spent and the care's Dress takes the tick (its stop), the threat yielding (`phase` "yield")."""
    r, sv = commit_rig(tmp_path)
    step(r, sv, 2.8)
    assert r.cmd() == ("steer", {"vx": -1.0, "vy": 0.0, "seconds": C.CARE_LEG_S, "gait": "walk"})
    assert last(tmp_path)["branch"] == "threat" and threat_why(tmp_path)["care_commit"]["phase"] == "leg"
    assert threat_why(tmp_path)["care_commit"]["key"] == ["wound", 9]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    n = len(r.acts.history)
    step(r, sv, 3.2)
    assert len(r.acts.history) == n and threat_why(tmp_path)["care_commit"]["phase"] == "hold"
    step(r, sv, 3.6)
    assert r.cmd() == ("stop", {}) and last(tmp_path)["branch"] == "care"
    assert threat_why(tmp_path)["care_commit"]["phase"] == "yield"


def test_the_committed_dress_holds_inside_care_hold_r_and_gives_way_only_inside_keep_r(tmp_path):
    """(c): once the Dress runs it holds the threat branch's yield while the chaser closes to 2.6 tiles (inside
    CARE_HOLD_R, where the yield before it gave way, `test_survive_ah`'s fix 1), and gives way at 2.4 (inside KEEP_R: the
    Dress's own end, the threat branch's tick); the chaser back at 2.8 (inside CARE_HOLD_R) takes the action's one leg,
    none having been sent for it (the Dress started beyond CARE_HOLD_R)."""
    r, sv = commit_rig(tmp_path)
    step(r, sv, 3.8, chasing=False)
    assert r.cmd() == ("stop", {}) and last(tmp_path)["branch"] == "care"
    r.answer()
    seen = []
    for dx in (3.4, 3.0, 2.6):
        step(r, sv, dx)
        seen.append((dx, last(tmp_path)["branch"]))
    assert seen == [(3.4, "care"), (3.0, "care"), (2.6, "care")]
    step(r, sv, 2.4)
    assert last(tmp_path)["branch"] == "threat" and "care_commit" not in threat_why(tmp_path)
    assert not any(a.type == "steer" for a in r.acts.history)
    step(r, sv, 2.8)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["care_commit"]["phase"] == "leg"


def test_never_a_second_leg_for_the_same_dress(tmp_path):
    """(c): the leg spent (its seconds passed, the chaser still at 3.2), the Dress takes the tick; the chaser into KEEP_R
    ends it; back at 2.8 the Dress resumes with no second leg (one `steer` sent in all)."""
    r, sv = commit_rig(tmp_path)
    step(r, sv, 2.8)
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(C.CARE_LEG_S)
    step(r, sv, 3.2)
    assert r.cmd() == ("stop", {}) and last(tmp_path)["branch"] == "care"
    step(r, sv, 2.3)
    assert last(tmp_path)["branch"] == "threat"
    step(r, sv, 2.8)
    assert sum(1 for a in r.acts.history if a.type == "steer") == 1
    assert threat_why(tmp_path)["care_commit"]["phase"] == "yield"


def test_with_care_commit_off_no_leg_is_sent(tmp_path):
    """The falsifier: with the rule off, the chaser at 2.8 tiles closing refuses the scratch's yield (Plan 31 Task
    15a's `_wound_yields`) and nothing logs `care_commit`."""
    r, sv = commit_rig(tmp_path, on=False)
    step(r, sv, 3.0)
    step(r, sv, 2.8)
    assert "care_commit" not in threat_why(tmp_path) and not any(a.type == "stop" for a in r.acts.history)


def test_a_rip_is_never_sent_on_the_move_and_an_unwear_of_a_shirt_neither():
    """(c)'s on-the-move clause read against the engine: RipClothing is a handcraft whose stopOnWalk is `not
    craftRecipe:isCanWalk()` (lua:shared/Entity/TimedActions/ISHandcraftAction.lua:405) and its recipe names no CanWalk
    key (media/scripts/generated/recipes/recipes.txt:217-232; CraftRecipe.Load @1345-@1363 L517-L518 sets canWalk only
    from one), so a rip stops on a walk; an unwear runs beside a walk only for a garment in
    ISWearClothing.WalkBodyLocations (lua:shared/TimedActions/ISWearClothing.lua:176-202, the accessories), where no
    cotton garment the Dress takes (`care.COTTON_RX`: shirts, T-shirts, tank tops, dresses, skirts, socks, underwear)
    sits. So the Dress keeps its stop before both, and PZAgent_Tend.lua's `moving` rejection stands as it is."""
    for name in ("Base.Tshirt_White", "Base.Shirt_FormalWhite", "Base.TankTop_Black", "Base.Socks_Ankle",
                 "Base.Boxers_White"):
        assert C.COTTON_RX.search(name)


def sends_after(rows, types=("rip",)):
    """(line, the next sending line, its branch) of each sent action of `types`."""
    sent = [(k, r) for k, r in enumerate(rows, 1) if r["sent"] and r["action"]]
    return [(k, sent[i + 1][0] if i + 1 < len(sent) else None, sent[i + 1][1]["branch"] if i + 1 < len(sent) else None)
            for i, (k, r) in enumerate(sent) if r["action"]["type"] in types]


def over_commit(rows):
    """The threat branch's sending lines right after a line whose care commitment yielded."""
    return [k for k in range(2, len(rows) + 1)
            if (threat(rows[k - 2]).get("care_commit") or {}).get("phase") == "yield"
            and rows[k - 1]["branch"] == "threat" and rows[k - 1]["sent"]]


def test_f17_s_rips_are_no_longer_superseded_by_the_threat_branch_beyond_keep_r():
    """(c) on F17, open loop: off, 15 rips sent (the record's: lines 283 to 422), 14 of them followed by a threat-branch
    send, its flee legs and stance legs (the record's 14 failed rips, each superseded). With CARE_COMMIT alone on the
    scratch's Dress (part 1) starts at line 277 and holds the yield: 3 rips go (lines 287, 297 and 407; the replay binds
    the first two to the record's own, whose recorded supersede the Dress answers with its stop again, the open loop's
    limit), and the threat branch sends after a committed yield only on lines 284, 380, 404, 410 and 437, each with the
    nearest listed zombie within KEEP_R (the Dress's own end), and on 159 and 789, the tick after a Dress ended done.
    No leg is sent: on F17's lines the care's want first reads the nearest standing zombie beyond CARE_HOLD_R."""
    on, off = f17(**only("CARE_COMMIT")), f17(**only())
    rips_off = sends_after(off)
    assert len(rips_off) == 15 and sum(1 for _, _, b in rips_off if b == "threat") == 14
    assert [k for k, _, _ in sends_after(on)] == [287, 297, 407]
    assert threat(on[276])["care_commit"] == {"key": ["wound", 1], "near": threat(on[276])["care_commit"]["near"],
                                              "phase": "yield"} and action(on[276]) == "stop"
    over = over_commit(on)
    assert over == [159, 284, 380, 404, 410, 437, 789]
    assert [k for k in over if on[k - 1]["inputs"]["nearest"] > P.KEEP_R] == [159, 789]
    assert not any((threat(r).get("care_commit") or {}).get("phase") == "leg" for r in on)


# ================================================================ the four together, on by default
def test_f17_with_the_four_on_by_default_flees_on_203_of_its_389_lines():
    """F17 replayed at the defaults (the four on), open loop: its 389 flee lines fall to 203 (`strain` 158 to none,
    `many` 29 to 7, `pair` 36 to 26, `health` 14 to 13, `flip` 21 to 26, `held` 80, `unreachable` 46, `held_inside` 4
    and `broken` 1 as recorded), its flee lines with the nearest listed within KEEP_R 43 to 12, and 3 rips go (lines
    287, 297 and 407) where the record sent 15."""
    rows = f17()
    assert flee_counts(rows) == {"held": 80, "unreachable": 46, "flip": 26, "pair": 26, "health": 13, "many": 7,
                                 "held_inside": 4, "broken": 1}
    assert sum(flee_counts(rows).values()) == 203 and len(near_flees(rows)) == 12
    assert [k for k, _, _ in sends_after(rows)] == [287, 297, 407]
