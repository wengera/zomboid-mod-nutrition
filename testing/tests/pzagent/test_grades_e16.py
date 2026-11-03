"""base/grades/e16.py (Plan 27 Task 2), offline: `grade_e16` and its nine readings of survival iteration 19 (the
finish under a flee P27-A, the `many` tail P27-B, the hold's lone fight P27-C and its rest P27-C2, the spent dressing
kept P27-D, the low swing P27-E, P26-L1's swings, the window climbs' still time and P26-O's unwear), each on a
fabricated log where it counts and a clean one where it reads zero, the unread case, a mutant per reading, every
`grade_e15` key unchanged under `grade_e16` on test_gates_e13's fixtures, the module's frozen copies of the live names
(ruling P26-Q), and the real checks on E18 (`e_day_18-20261102-224036`): every `grade_e15` key equal to the committed
`e_grade.txt`'s, through the function and through `e_grade_16.py`, and the new readings as the grade reads them."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e15 as G15
from agent.base.grades import e16 as G
from agent.drivers import e_grade_16 as EG16
from . import test_grades_e14 as T14
from .test_gates_e7 import aline, zf
from .test_gates_e13 import _act
from .test_grades_e14 import actl, row

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E18 = os.path.join(TESTING, "artifacts", "e_day_18-20261102-224036")
NEW = G.NEW
TAGS = ("P27-A", "P27-B", "P27-C", "P27-C2", "P27-D", "P27-E", "P26-L1", "WINDOW_STALL_S", "P26-O")


def grade(actions=(), results=(), log=None, frames=()):
    return G.grade_e16(T14.artifact(actions, results), decision_lines=log, lines=list(frames))


def res(aid, **r):
    return {"aid": aid, "type": "x", "state": "done", "result": r}


def inputs(ln, **kw):
    """The line `ln` with `kw` set on its `inputs` (threats, health, nearest)."""
    ln["inputs"].update(kw)
    return ln


def frame(t, endurance=None, minute=None, **kw):
    """`zf` with `stats.endurance` and `worldAge` (hours) set when given."""
    f = zf(t, **kw)
    if endurance is not None:
        f["stats"]["endurance"] = endurance
    if minute is not None:
        f["worldAge"] = 8.0 + minute / 60.0
    return f


CLEAN = [aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)]


# ================================================================ P27-A, the finish under a flee
def finish_fixture(flag=True):
    """Four finishes sent under the `strain`, `many`, `pair` and `strain` flees (a kill, a hit, a stomp rejected `not
    valid`, a stomp superseded by the flee's next leg), one logged and not sent, P24-AQ's plain `finish` and a care
    line carrying the threat's why (neither counted)."""
    ff = (lambda reason, struck, clear: {"flee_finish": {"reason": reason, "struck": struck, "clear": clear}}) if flag \
        else (lambda *a: {})
    why = lambda flee, zid, *a: dict({"flee": flee, "finish": zid, "kind": "stomp", "dist": 2.5}, **ff(*a))
    log = [aline(0, 1.0, why("strain", 7, "strain", False, 5.0), _act("stomp", targetId=7)),
           aline(1, 2.0, why("many", 8, "many", True, None), _act("stomp", targetId=8)),
           aline(2, 3.0, why("pair", 9, "pair", False, 2.9), _act("stomp", targetId=9)),
           aline(3, 4.0, why("strain", 10, "strain", False, 4.0), _act("stomp", targetId=10)),
           aline(4, 5.0, why("strain", 12, "strain", False, 4.0), _act("stomp", targetId=12), sent=False),
           aline(5, 6.0, {"flee": "many", "finish": 11, "kind": "stomp", "dist": 2.0}, _act("stomp", targetId=11)),
           aline(6, 7.0, why("strain", 13, "strain", False, 4.0), _act("stomp", targetId=13), branch="care")]
    acts = [row("s1", "stomp", 1.0, targetId=7), row("s2", "stomp", 2.0, targetId=8),
            row("s3", "stomp", 3.0, state="rejected", reason="not valid", targetId=9),
            row("s4", "stomp", 4.0, state="failed", reason="superseded", targetId=10),
            row("s5", "stomp", 6.0, targetId=11), row("s6", "stomp", 7.0, targetId=13)]
    results = [res("s1", hit=True, targetDead=True), res("s2", hit=True, targetDead=False),
               res("s5", hit=True, targetDead=True)]
    return grade(acts, results, log)["flee_finish"]


def test_the_flee_finish_counts_the_finishes_sent_by_reason_their_kills_the_struck_and_the_refused():
    g = finish_fixture()
    assert g["read"] is True and g["lines"] == 5
    assert g["sent"] == {"strain": 2, "many": 1, "pair": 1}
    assert (g["kills"], g["landed"], g["struck"], g["unstruck"], g["refused"]) == (1, 2, 1, 3, 1)
    assert g["clear_within"] == 1          # the `pair` finish's 2.9 tiles


def test_a_flee_finish_reason_outside_flee_finish_reasons_is_read_other():
    log = [aline(0, 1.0, {"flee": "health", "finish": 7, "kind": "stomp", "dist": 2.5,
                          "flee_finish": {"reason": "health", "struck": False, "clear": None}},
                 _act("stomp", targetId=7))]
    assert grade([row("s1", "stomp", 1.0, targetId=7)], [], log)["flee_finish"]["sent"] == {"other": 1}


def test_the_flee_finish_reads_zero_without_the_why_and_unread_without_a_log():
    zero = {"read": True, "lines": 0, "sent": {}, "kills": 0, "landed": 0, "struck": 0, "unstruck": 0, "refused": 0,
            "clear_within": 0}
    assert finish_fixture(flag=False) == zero
    assert grade(log=CLEAN)["flee_finish"] == zero
    assert grade(log=None)["flee_finish"] == {"read": False}


# ================================================================ P27-B, the `many` episode's tail
def tail_fixture(flag=True):
    """Three tail ends, each TAIL_AFTER_LINES and one `strain` lines from the next: one on a fight line that kills (A),
    one followed by a new `many` episode and then a fight (B: logged short and crowded, the checks' own case), one
    followed by the `strain` flee alone (C)."""
    mt = (lambda t, s, p: {"many_tail": {"ticks": t, "standing": s, "pressing": p}}) if flag else (lambda *a: {})
    fill = [({"flee": "strain"}, None)] * (G.TAIL_AFTER_LINES + 1)
    whys = ([({"flee": "many"}, None), (dict({"fight": True, "target": 5}, **mt(4, 1, 1)), _act("attack", targetId=5)),
             ({"fight": True, "target": 5}, None)] + fill
            + [(dict({"flee": "strain"}, **mt(3, 2, 1)), None), ({"flee": "many"}, None),
               ({"fight": True, "target": 6}, None)] + fill
            + [(dict({"flee": "strain"}, **mt(4, 0, 0)), None), ({"flee": "strain"}, None)])
    log = [aline(i, float(i), w, a, sent=a is not None) for i, (w, a) in enumerate(whys)]
    acts = [row("k1", "attack", 1.0, targetId=5)]
    return grade(acts, [res("k1", hit=True, targetDead=True)], log)["many_tail"]


def tail_far_fixture():
    """One end, then TAIL_AFTER_LINES `strain` lines, then a fight: beyond the window, no lone fight."""
    log = [aline(0, 0.0, {"flee": "strain", "many_tail": {"ticks": 4, "standing": 1, "pressing": 0}}, None,
                 sent=False)]
    log += [aline(i, float(i), {"flee": "strain"}, None, sent=False) for i in range(1, G.TAIL_AFTER_LINES + 1)]
    log += [aline(99, 99.0, {"fight": True, "target": 2}, None, sent=False)]
    return grade(log=log)["many_tail"]


def test_the_many_tail_counts_the_ends_the_lone_fights_after_the_kills_and_the_re_entries():
    g = tail_fixture()
    assert g["read"] is True and g["ends"] == 3
    assert (g["lone_fights_after"], g["kills_after"], g["re_entries"]) == (1, 1, 1)
    assert (g["short"], g["crowded"]) == (1, 1)


def test_the_many_tail_reads_zero_without_the_why_a_far_fight_and_unread_without_a_log():
    g = tail_fixture(flag=False)
    assert g == {"read": True, "ends": 0, "lone_fights_after": 0, "kills_after": 0, "re_entries": 0, "short": 0,
                 "crowded": 0}
    assert tail_far_fixture()["lone_fights_after"] == 0
    assert grade(log=None)["many_tail"] == {"read": False}


# ================================================================ P27-C, the hold's lone fight
def hold_fixture(flag=True):
    """A run of three `hold_fight` lines (a shove, a stomp that kills, nothing sent), an ordinary fight's swing, a
    second run of one carrying a swing, and a care line with the key (not counted)."""
    hf = {"hold_fight": True} if flag else {}
    f = lambda **kw: dict({"fight": True, "target": 3}, **hf, **kw)
    log = [aline(0, 1.0, f(), _act("shove", targetId=3)),
           aline(1, 2.0, f(), _act("stomp", targetId=3)),
           aline(2, 3.0, f(), None, sent=False),
           aline(3, 4.0, {"fight": True, "target": 4}, _act("attack", targetId=4)),
           aline(4, 5.0, f(), _act("attack", targetId=3)),
           aline(5, 6.0, f(), None, sent=False, branch="care")]
    acts = [row("h1", "shove", 1.0, targetId=3), row("h2", "stomp", 2.0, targetId=3),
            row("h3", "attack", 4.0, targetId=4), row("h4", "attack", 5.0, targetId=3)]
    return grade(acts, [res("h2", hit=True, targetDead=True)], log)["hold_fight"]


def test_the_hold_fight_counts_its_lines_runs_sends_and_kills():
    g = hold_fixture()
    assert g == {"read": True, "lines": 4, "runs": 2, "shoves": 1, "stomps": 1, "attacks": 1, "kills": 1}


def test_the_hold_fight_reads_zero_without_the_why_and_unread_without_a_log():
    assert hold_fixture(flag=False) == {"read": True, "lines": 0, "runs": 0, "shoves": 0, "stomps": 0, "attacks": 0,
                                        "kills": 0}
    assert grade(log=None)["hold_fight"] == {"read": False}


# ================================================================ P27-C2, the hold's rest
def rest_fixture(flag=True):
    """Three adjacent rest ticks (the endurance 0.50 to 0.51 over two game minutes), a fight, three adjacent walk ticks
    of the endurance hold with no zombie within DANGER_R (0.51 to 0.514 over two), a rest tick with a zombie within
    DANGER_R (`near`) and a walk tick with two (not the comparison's)."""
    strain = {"flee": "strain", "strain": {"kind": "endurance", "endurance": 0.5}}
    rest = dict(strain, rest={"endurance": 0.5, "since_min": 0}) if flag else dict(strain)
    walk = dict(strain, hold_walk=True)
    log = [inputs(aline(i, float(i), rest, None, sent=False), threats=0) for i in range(3)]
    log += [aline(3, 2.5, {"fight": True, "target": 1}, None, sent=False)]
    log += [inputs(aline(i + 4, 3.0 + i, walk, _act("walkTo", x=1.5, y=1.5)), threats=0) for i in range(3)]
    log += [inputs(aline(7, 6.0, rest, None, sent=False), threats=1),
            inputs(aline(8, 7.0, walk, None, sent=False), threats=2)]
    frames = [frame(t - 0.1, endurance=e, minute=m) for t, e, m in
              ((0.0, 0.50, 0), (1.0, 0.505, 1), (2.0, 0.51, 2), (3.0, 0.51, 3), (4.0, 0.512, 4), (5.0, 0.514, 5),
               (6.0, 0.514, 6), (7.0, 0.515, 7))]
    return grade(log=log, frames=frames)["hold_rest"]


def test_the_hold_rest_counts_the_rest_ticks_and_reads_the_endurance_rise_standing_against_walking():
    g = rest_fixture()
    assert g["read"] is True and (g["ticks"], g["near"], g["walk_ticks"]) == (4, 1, 3)
    st, wk = g["standing"], g["walking"]
    assert st["read"] is True and (st["frames"], st["pairs"]) == (3, 2) and st["minutes"] == pytest.approx(2.0)
    assert st["rise_per_min"] == pytest.approx(0.005)
    assert wk["read"] is True and (wk["frames"], wk["pairs"]) == (3, 2) and wk["rise_per_min"] == pytest.approx(0.002)


def test_the_hold_rest_reads_no_side_with_fewer_than_two_frames_and_unread_without_a_log():
    g = rest_fixture(flag=False)
    assert (g["ticks"], g["near"], g["standing"]) == (0, 0, {"read": False}) and g["walking"]["read"] is True
    g = grade(log=CLEAN)["hold_rest"]
    assert g == {"read": True, "ticks": 0, "near": 0, "walk_ticks": 0, "standing": {"read": False},
                 "walking": {"read": False}}
    assert grade(log=None)["hold_rest"] == {"read": False}


def test_the_game_minutes_wrap_at_midnight_off_gamemin_without_worldage():
    a, b = {"gameMin": 1439}, {"gameMin": 1}
    assert G._world_min(a, b) == 2 and G._world_min({}, b) is None
    assert G._world_min({"worldAge": 1.0}, {"worldAge": 1.5}) == pytest.approx(30.0)


# ================================================================ P27-D, the spent dressing kept
def kept_fixture(flag=True):
    """Two kept lines on the neck (9) at the health 82 then 80, one on part 4 at a short bleed (8.0: `short`), a spent
    re-dress sent and one held (not sent)."""
    kept = lambda part, bt: dict({"bleeding": [], "spent": [part], "held": {"rag": 1}},
                                 **({"spent_kept": {"part": part, "bleedingTime": bt, "dirty": True}} if flag else {}))
    spent = {"reason": "spent", "part": 7, "item": 5, "kind": "rag", "life": 0, "dirty": True}
    log = [inputs(aline(0, 1.0, {}, None, sent=False, branch="care", care=kept(9, 15.4)), health=82.0),
           inputs(aline(1, 2.0, {}, None, sent=False, branch="care", care=kept(9, 15.0)), health=80.0),
           inputs(aline(2, 3.0, {}, None, sent=False, branch="care", care=kept(4, 8.0)), health=79.0),
           inputs(aline(3, 4.0, {}, _act("bandage", itemId=5, part=7), branch="care", care=spent), health=78.0),
           inputs(aline(4, 5.0, {}, _act("bandage", itemId=5, part=7), sent=False, branch="care", care=spent),
                  health=78.0)]
    return grade(log=log)["spent_kept"]


def test_the_spent_kept_counts_the_kept_lines_by_part_the_health_across_them_and_the_re_dresses():
    g = kept_fixture()
    assert g["read"] is True and g["lines"] == 3 and g["parts"] == {"9": 2, "4": 1}
    assert g["health_across"] == {"9": [82.0, 80.0], "4": [79.0, 79.0]}
    assert (g["short"], g["redressed"]) == (1, 1)


def test_the_spent_kept_reads_zero_without_the_why_and_unread_without_a_log():
    assert kept_fixture(flag=False) == {"read": True, "lines": 0, "parts": {}, "health_across": {}, "short": 0,
                                        "redressed": 1}
    assert grade(log=None)["spent_kept"] == {"read": False}


# ================================================================ P27-E, the low swing; P26-L1's swings
def zframe(t, health, **kw):
    return zf(t, zombies=[{"id": 4, "x": 10.5, "y": 10.5, "health": health}], **kw)


def low_fixture(flag=True):
    """A low swing at 4 after three misses that hits (the target 1.2 to 0.6 across it), one after two that is rejected
    with no frame listing the target after it (`short`), one logged and not sent."""
    ls = (lambda missed: {"low_swing": {"target": 4, "missed": missed}}) if flag else (lambda m: {})
    w = lambda m: dict({"fight": True, "low_fight": True, "target": 4}, **ls(m))
    log = [aline(0, 1.0, w(3), _act("attack", targetId=4)),
           aline(1, 3.0, w(2), _act("attack", targetId=4)),
           aline(2, 5.0, w(3), None, sent=False)]
    acts = [row("a1", "attack", 1.0, ended=1.8, targetId=4),
            row("a2", "attack", 3.0, state="rejected", reason="busy", ended=4.0, targetId=4)]
    frames = [zframe(0.9, 1.2), actl("a1", "attack", "done", 1.8, {"hit": True}), zframe(2.0, 0.6), zf(4.5)]
    return grade(acts, [res("a1", hit=True)], log, frames)["low_swing"]


def test_the_low_swing_counts_the_swings_sent_landed_the_target_s_health_across_and_the_short_ones():
    g = low_fixture()
    assert g["read"] is True and (g["lines"], g["sent"], g["landed"], g["short"]) == (3, 2, 1, 1)
    assert g["health_before_after"] == [[1.2, 0.6], [0.6, None]]


def test_the_low_swing_reads_zero_without_the_why_and_unread_without_a_log():
    assert low_fixture(flag=False) == {"read": True, "lines": 0, "sent": 0, "landed": 0, "health_before_after": [],
                                       "short": 0}
    assert grade(log=None)["low_swing"] == {"read": False}


BLED = [{"i": 7, "bleeding": True, "bleedingTime": 12.0}]


def wounded_fixture(flag=True):
    """P26-L1's swings at 4 (three misses) at 1.0 and 2.5 that hit with the target's health unchanged (E18's 30468),
    a wound on part 7 read at 3.0 and 4.0 (within WOUND_AFTER_S of both ends, 1.8 and 3.0: each counted once) and
    still at 8.5 (beyond), and a logged line not sent."""
    ws = {"wounded_swing": 3} if flag else {}
    log = [aline(0, 1.0, dict({"fight": True, "target": 4}, **ws), _act("attack", targetId=4)),
           aline(1, 1.5, dict({"fight": True, "target": 4, "holding": "w1"}, **ws), None, sent=False),
           aline(2, 2.5, dict({"fight": True, "target": 4}, **ws), _act("attack", targetId=4))]
    acts = [row("w1", "attack", 1.0, ended=1.8, targetId=4), row("w2", "attack", 2.5, ended=3.0, targetId=4)]
    frames = [zframe(0.9, 3.5), actl("w1", "attack", "done", 1.8, {"hit": True}), zframe(2.0, 3.5),
              actl("w2", "attack", "done", 3.0, {"hit": True}), zframe(3.0, 3.5, parts=BLED),
              zframe(4.0, 3.5, parts=BLED), zframe(8.5, 3.5, parts=BLED)]
    return grade(acts, [res("w1", hit=True), res("w2", hit=True)], log, frames)["wounded_swings"]


def test_the_wounded_swings_count_the_swings_sent_landed_the_health_across_and_the_wound_frames_after():
    g = wounded_fixture()
    assert g["read"] is True and (g["lines"], g["sent"], g["landed"]) == (3, 2, 2)
    assert g["health_before_after"] == [[3.5, 3.5], [3.5, 3.5]]
    assert (g["wound_frames_after"], g["wounded"]) == (2, 2)


def test_the_wounded_swings_read_zero_without_the_why_and_unread_without_a_log():
    assert wounded_fixture(flag=False) == {"read": True, "lines": 0, "sent": 0, "landed": 0,
                                           "health_before_after": [], "wound_frames_after": 0, "wounded": 0}
    assert grade(log=None)["wounded_swings"] == {"read": False}


# ================================================================ the window climbs' still time
def window_fixture():
    """w1: accepted at 1.0, done at 3.5, the player on one square to 2.5 and on the next from it (the longest still run
    1.5 s); w2: accepted at 10.0, done at 14.0, never moving (4.0 s: `over`); w3: accepted at 20.0 and still running,
    its last frame at 21.0."""
    lines = [actl("w1", "window", "accepted", 1.0), actl("w1", "window", "progress", 2.0),
             actl("w1", "window", "done", 3.5, {"opened": True}),
             actl("w2", "window", "accepted", 10.0), actl("w2", "window", "done", 14.0),
             actl("w3", "window", "accepted", 20.0)]
    frames = [zf(t, x=x, y=0.5) for t, x in ((1.1, 4.5), (1.5, 4.5), (2.0, 4.6), (2.5, 3.5), (3.0, 3.5), (3.4, 3.5))]
    frames += [zf(t, x=4.5, y=0.5) for t in (10.1, 12.0, 13.9, 20.1, 21.0)]
    return grade(log=CLEAN, frames=lines + frames)["window_still"]


def test_the_window_still_reads_each_climb_s_accept_to_done_and_its_longest_still_run():
    g = window_fixture()
    assert g["read"] is True and g["over"] == 1
    assert g["climbs"] == [{"aid": "w1", "state": "done", "accept_done_s": 2.5, "still_s": 1.5},
                           {"aid": "w2", "state": "done", "accept_done_s": 4.0, "still_s": 4.0},
                           {"aid": "w3", "state": "running", "accept_done_s": None, "still_s": 1.0}]


def test_the_window_still_reads_no_climb_without_window_acts_and_unread_without_a_log():
    assert grade(log=CLEAN)["window_still"] == {"read": True, "climbs": [], "over": 0}
    assert grade(log=None)["window_still"] == {"read": False}


# ================================================================ P26-O, the unwear's live reading
def unwear_fixture():
    """u1 done and ripped after (r1); u2 and u3 rejected `held` (F9's three were); u4 failed, its terminal act line
    reading `interrupted` over the row's `stopped`; u5 done with its item ripped only before it (r2) and another item
    ripped after it (r3)."""
    acts = [row("r2", "rip", 0.5, branch="care", itemId=7),
            row("u1", "unwear", 1.0, ended=2.0, branch="care", itemId=5),
            row("r1", "rip", 3.0, branch="care", itemId=5),
            row("u2", "unwear", 4.0, state="rejected", reason="held", branch="care", itemId=6),
            row("u3", "unwear", 4.5, state="rejected", reason="held", branch="care", itemId=6),
            row("u4", "unwear", 5.0, state="failed", reason="stopped", branch="care", itemId=8),
            row("u5", "unwear", 5.5, ended=6.0, branch="care", itemId=7),
            row("r3", "rip", 7.0, branch="care", itemId=99)]
    lines = [actl("u4", "unwear", "failed", 5.5, reason="interrupted")]
    return grade(acts, [], CLEAN, lines)["unwear_live"]


def test_the_unwear_live_counts_the_unwears_their_ends_by_reason_and_the_rip_after_a_done_one():
    assert unwear_fixture() == {"read": True, "sent": 5, "done": 2, "rejected": {"held": 2},
                                "failed": {"interrupted": 1}, "rip_after": 1}


def test_the_unwear_live_reads_zero_without_an_unwear_and_unread_without_a_log():
    assert grade(log=CLEAN)["unwear_live"] == {"read": True, "sent": 0, "done": 0, "rejected": {}, "failed": {},
                                               "rip_after": 0}
    assert grade(log=None)["unwear_live"] == {"read": False}


# ================================================================ grade_e16 over grade_e15
@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e16_reads_every_grade_e15_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e15 = G15.grade_e15(a, decision_lines=seen["log"], lines=seen["frames"])
    e16 = G.grade_e16(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e16["grade"] == "grade_e16" and all(e16[k]["read"] is True for k in NEW)
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e15.items() if k not in skip} == {k: v for k, v in e16.items() if k not in skip}
    assert e16["report_lines"][:-len(NEW)] == e15["report_lines"]


def test_grade_e16_without_a_decision_log_reads_the_new_keys_unread():
    g = grade(log=None)
    assert all(g[k] == {"read": False} for k in NEW) and g["grade"] == "grade_e16"
    assert G.readings_e16({}, None, []) == {k: {"read": False} for k in NEW}


def test_report_lines_e16_names_gate_e16_then_one_line_per_reading_marked_reading_or_inference():
    g = grade(log=CLEAN)
    tail = g["report_lines"][-len(NEW):]
    assert tail == G.lines_e16(g)
    for line, tag in zip(tail, TAGS):
        assert ("(%s)" % tag) in line and "[reading]" in line
    assert sum("[inference]" in line for line in tail) == 6
    off = grade(log=None)["report_lines"][-len(NEW):]
    assert all("no decision log read" in line for line in off)
    renamed = G.report_lines_e16(dict(g, gate={"pass": True}))
    assert not any(line.startswith(("gate_e13 ", "gate_e14 ", "gate_e15 ")) for line in renamed)
    assert G.gate_e16([]) == E.gate_e13([])


# ================================================================ ruling P26-Q: the frozen copies
def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            names.append(n.module or "")
            names += ["%s.%s" % (n.module, a.name) for a in n.names]
        elif isinstance(n, ast.Import):
            names += [a.name for a in n.names]
    return names


def test_the_module_imports_no_live_planner_or_world_name_and_holds_its_own_copies():
    names = _imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in names), names
    assert not any(n.startswith("agent.base") and n.split(".")[-1] in ("planner", "world") for n in names), names
    ns = vars(G)
    assert (ns["DANGER_R"], ns["FINISH_CLEAR_R"], ns["MANY_TAIL_TICKS"], ns["SPENT_REDRESS_BT"], ns["SHOVE_FAIL_N"],
            ns["WINDOW_STALL_S"], ns["FLEE_FINISH_REASONS"]) == (6.0, 3.0, 4, 10.0, 3, 3.0, ("strain", "pair", "many"))
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/e16.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "e16_mutant"}
    exec(compile(src[:start] + new + src[end:], "e16_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    ("e_flee_finish", lambda b: b.replace('if ln.get("branch") != "threat" or not', "if not"),
     lambda: finish_fixture()["lines"] == 5),
    ("e_flee_finish", lambda b: b.replace('row.get("reason") != "superseded"', "True"),
     lambda: finish_fixture()["refused"] == 1),
    ("e_flee_finish", lambda b: b.replace("c <= FINISH_CLEAR_R", "c < 0"),
     lambda: finish_fixture()["clear_within"] == 1),
    ("e_flee_finish", lambda b: b.replace('ff.get("struck") is True', 'ff.get("struck") is not None'),
     lambda: finish_fixture()["struck"] == 1),
    ("e_many_tail", lambda b: b.replace('if j > i and L.why(rows[j]).get("flee") == "many":', "if False:"),
     lambda: tail_fixture()["re_entries"] == 1 and tail_fixture()["lone_fights_after"] == 1),
    ("e_many_tail", lambda b: b.replace("t < MANY_TAIL_TICKS", "t < 0"), lambda: tail_fixture()["short"] == 1),
    ("e_many_tail", lambda b: b.replace("i + 1 + TAIL_AFTER_LINES", "len(rows)"),
     lambda: tail_far_fixture()["lone_fights_after"] == 0),
    ("e_hold_fight", lambda b: b.replace('L.why(ln).get("hold_fight") is True', 'L.why(ln).get("fight") is True'),
     lambda: hold_fixture()["lines"] == 4),
    ("e_hold_fight", lambda b: b.replace("runs += 0 if prev else 1", "runs += 1"), lambda: hold_fixture()["runs"] == 2),
    ("_clear", lambda b: b.replace("return t == 0", "return True"), lambda: rest_fixture()["near"] == 1),
    ("_rise", lambda b: b.replace("if b != a + 1:", "if False:"),
     lambda: rest_fixture()["standing"]["frames"] == 3),
    ("_walk_line", lambda b: b.replace(" and _clear(ln))", ")"), lambda: rest_fixture()["walk_ticks"] == 3),
    ("_world_min", lambda b: b.replace("round(a1 * 60.0, 6) - round(a0 * 60.0, 6)", "a1 - a0"),
     lambda: rest_fixture()["standing"]["rise_per_min"] == pytest.approx(0.005)),
    ("e_spent_kept", lambda b: b.replace("bt <= SPENT_REDRESS_BT", "bt < 0"), lambda: kept_fixture()["short"] == 1),
    ("e_spent_kept", lambda b: b.replace("across.setdefault(p, [h, h])[1] = h", "across.setdefault(p, [h, h])"),
     lambda: kept_fixture()["health_across"]["9"] == [82.0, 80.0]),
    ("e_spent_kept", lambda b: b.replace('and E._sent(ln, "bandage")', ""), lambda: kept_fixture()["redressed"] == 1),
    ("e_low_swing", lambda b: b.replace("< SHOVE_FAIL_N", "< 0"), lambda: low_fixture()["short"] == 1),
    ("_target_health", lambda b: b.replace("frames[lo:]", "frames"),
     lambda: low_fixture()["health_before_after"] == [[1.2, 0.6], [0.6, None]]),
    ("_swing_lines", lambda b: b.replace('E._sent(ln, "attack")', "True"), lambda: low_fixture()["sent"] == 2),
    ("_wound_frames", lambda b: b.replace("+ WOUND_AFTER_S * 1000.0", "+ 1000.0 * 1000.0"),
     lambda: wounded_fixture()["wound_frames_after"] == 2),
    ("_wound_frames", lambda b: b.replace("if n > n0 or bled - bled0:", "if n > n0:"),
     lambda: wounded_fixture()["wound_frames_after"] == 2),
    ("e_wounded_swings", lambda b: b.replace("len(set().union(*found))", "sum(len(c) for c in found)"),
     lambda: wounded_fixture()["wound_frames_after"] == 2),
    ("_still_s", lambda b: b.replace("best = max(best, w - start)", "best = best"),
     lambda: window_fixture()["climbs"][0]["still_s"] == 1.5),
    ("_still_s", lambda b: b.replace("elif sq != sq0:", "elif False:"),
     lambda: window_fixture()["climbs"][0]["still_s"] == 1.5),
    ("e_window_still", lambda b: b.replace('c["still_s"] >= WINDOW_STALL_S', 'c["still_s"] > 100'),
     lambda: window_fixture()["over"] == 1),
    ("e_unwear_live", lambda b: b.replace('(E._n(r.get("sentS")) or 0.0) >= t', "True"),
     lambda: unwear_fixture()["rip_after"] == 1),
    ("e_unwear_live", lambda b: b.replace("if end is not None else", "if False else"),
     lambda: unwear_fixture()["failed"] == {"interrupted": 1}),
    ("e_unwear_live", lambda b: b.replace('E._d(r.get("args")).get("itemId") == iid and ', ""),
     lambda: unwear_fixture()["rip_after"] == 1),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(G, fn_name, _mutated(fn_name, edit)[fn_name])
    try:
        survives = holds()
    except Exception:       # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % fn_name


# ================================================================ the real checks: E18
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _real():
    p = os.path.join(E18, "e_day_18.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E18)
    g = G.grade_e16(EG16.load(p), None, EG16.load_log(p), state_dir=EG16._dir(p))
    return g, json.loads(json.dumps(EG16.finite(g), sort_keys=True, allow_nan=False))


E18_READ = {
    # no iteration 19 line exists on E18 (it ran iteration 18): every P27 why reads 0
    "flee_finish": {"read": True, "lines": 0, "sent": {}, "kills": 0, "landed": 0, "struck": 0, "unstruck": 0,
                    "refused": 0, "clear_within": 0},
    "many_tail": {"read": True, "ends": 0, "lone_fights_after": 0, "kills_after": 0, "re_entries": 0, "short": 0,
                  "crowded": 0},
    "hold_fight": {"read": True, "lines": 0, "runs": 0, "shoves": 0, "stomps": 0, "attacks": 0, "kills": 0},
    "low_swing": {"read": True, "lines": 0, "sent": 0, "landed": 0, "health_before_after": [], "short": 0},
    # P26-O landed after E18: no unwear sent
    "unwear_live": {"read": True, "sent": 0, "done": 0, "rejected": {}, "failed": {}, "rip_after": 0},
}


def test_grade_e16_on_e18_keeps_every_grade_e15_key_as_the_committed_e_grade_txt_and_reads_the_new_keys():
    g, mine = _real()
    assert g["grade"] == "grade_e16" and all(g[k]["read"] is True for k in NEW)
    for k, v in E18_READ.items():
        assert g[k] == v, k
    # the rest: no rest tick (P27-C2 after E18), the endurance hold's 158 walk lines with none within DANGER_R the
    # comparison (E18's walk: 0.025 of endurance over 19.37 game minutes)
    hr = g["hold_rest"]
    assert (hr["ticks"], hr["near"], hr["walk_ticks"], hr["standing"]) == (0, 0, 158, {"read": False})
    wk = hr["walking"]
    assert wk["read"] is True and (wk["frames"], wk["pairs"]) == (158, 144)
    assert wk["minutes"] == pytest.approx(19.370151) and wk["rise_per_min"] == pytest.approx(0.0012896227508023405)
    # the spent dressing: no kept line, the seven spent re-dresses E18 sent
    assert g["spent_kept"] == {"read": True, "lines": 0, "parts": {}, "health_across": {}, "short": 0,
                               "redressed": 7}
    # P26-L1's three divided swings at 30468 (aids a132 to a134), each landed, the target's listed health
    # 3.568000078201294 unchanged across them; the bite on part 7 at wall 1793678763.673 read after all three
    assert g["wounded_swings"] == {"read": True, "lines": 6, "sent": 3, "landed": 3,
                                   "health_before_after": [[3.568000078201294, 3.568000078201294]] * 3,
                                   "wound_frames_after": 49, "wounded": 3}
    # the two window climbs (a232, a251), both under WINDOW_STALL_S
    assert g["window_still"] == {"read": True, "over": 0, "climbs": [
        {"aid": "a232", "state": "done", "accept_done_s": 2.379, "still_s": 2.379},
        {"aid": "a251", "state": "done", "accept_done_s": 1.512, "still_s": 1.265}]}
    _, committed = _committed(E18, "e_grade.txt")
    for k in NEW:
        mine.pop(k)
    mine["grade"] = "grade_e15"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed


def test_e_grade_16_on_e18_prints_the_committed_e_grade_txt_s_lines_then_the_new_ones():
    """`e_grade_16.py` on the committed E18 artifact: the committed `e_grade.txt`'s report lines, then the nine new
    lines, then the JSON whose grade_e15 keys equal the committed (CRLF folded)."""
    p = os.path.join(E18, "e_day_18.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E18)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_16.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(E18, "e_grade.txt")
    assert printed[:-len(NEW)] == want_lines and len(printed) == len(want_lines) + len(NEW)
    assert got["grade"] == "grade_e16" and printed[-len(NEW):] == got["report_lines"][-len(NEW):]
    for k in NEW:
        got.pop(k)
    got["grade"] = "grade_e15"
    got["report_lines"] = got["report_lines"][:-len(NEW)]
    assert got == want


def test_e_grade_16_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5: a driver's refusal is tested without invoking it on a bad argument): its
    main answers usage, exit 2, on no path or more than two outside `--chain`."""
    src = open(EG16.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e16 import gate_e16, grade_e16, report_lines_e16" in src
