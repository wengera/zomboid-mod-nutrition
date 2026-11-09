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
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import Rig, zombie
from .test_survive import last, make, threat_why, tick

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
    """F17's replayed decision lines (list index line - 1) with `switches` set."""
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
    """`survive.T16_SWITCHES`, each off until the coward rules' commit turns them on by default."""
    assert T16 == ("POINT_BLANK_FIGHT", "PAIR_NEAREST", "STRAIN_BOUND")
    assert all(getattr(S.Survive, k) is False for k in T16)


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
    """A Survive on a fresh Rig with the T16 switches in `on` set on (the others their default), one frame."""
    r, sv = make(tmp_path)
    for name in on:
        setattr(sv, name, True)
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
    """A Fight on a fresh Rig over one frame of `zs`, its rules the defaults with `pair_nearest` on or off."""
    r = Rig(tmp_path)
    r.frame(zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = (f.rules | {"pair_nearest"}) if rule else (f.rules - {"pair_nearest"})
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
