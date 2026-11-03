"""base/grades/e17.py (Plan 27 Task 6), offline: `grade_e17` and its nine readings of survival iteration 20 (the stuck
walk's mark and the leave P27-F, the floor finish P27-G, the fallen target sought P27-H, the listing's left-out
zombies P27-I, the shove-only fight's close and the hold's idle zombie P27-J, the early rag stock P27-K1, the low
fight's exit and the inside corner's yield P27-K2, the spent replace held P27-K3 and the divided swing withdrawn
P27-L), each on a fabricated log where it counts and a clean one where it reads zero, the unread case, a mutant per
reading, every `grade_e16` key unchanged under `grade_e17` on test_gates_e13's fixtures, the module's frozen copies of
the live names (ruling P26-Q), and the real checks on E19 (`e_day_19-20261103-072904`) and E18
(`e_day_18-20261102-224036`): every inherited key equal to the committed `e_grade.txt`'s, through the function and
through `e_grade_17.py` (its printed lines the committed ones then the new ones), and the new readings as the grade
reads them."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e16 as G16
from agent.base.grades import e17 as G
from agent.drivers import e_grade_17 as EG17
from . import test_grades_e14 as T14
from .test_gates_e7 import T0, aline, zf
from .test_gates_e13 import _act
from .test_grades_e14 import actl, row

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E18 = os.path.join(TESTING, "artifacts", "e_day_18-20261102-224036")
E19 = os.path.join(TESTING, "artifacts", "e_day_19-20261103-072904")
E20 = os.path.join(TESTING, "artifacts", "e_day_20-20261103-121340")
NEW = G.NEW
NEW16 = G16.NEW
TAGS = ("P27-F", "P27-G", "P27-H", "P27-I", "P27-J", "P27-K1", "P27-K2", "P27-K3", "P27-L")


def grade(actions=(), results=(), log=None, frames=()):
    return G.grade_e17(T14.artifact(actions, results), decision_lines=log, lines=list(frames))


def res(aid, **r):
    return {"aid": aid, "type": "x", "state": "done", "result": r}


def inputs(ln, **kw):
    """The line `ln` with `kw` set on its `inputs` (threats, health, nearest, x, y)."""
    ln["inputs"].update(kw)
    return ln


def frame(t, minute=None, bitten=None, **kw):
    """`zf` with `worldAge` (hours) and the body's `bitten` set when given."""
    f = zf(t, **kw)
    if minute is not None:
        f["worldAge"] = 8.0 + minute / 60.0
    if bitten is not None:
        f["body"]["bitten"] = bitten
    return f


def gline(n, wall_off, goal, action=None, sent=False, x=10.5, y=10.5):
    """A goal-branch line whose goal why (`inputs.branches.goal`, the runner's) is `goal`, at the position x, y."""
    ln = aline(n, wall_off, {}, action, sent=sent, branch="goal")
    ln["inputs"]["branches"]["goal"] = dict(goal)
    return inputs(ln, x=x, y=y)


def swing(t, started=True):
    """A state-log `swing` event `t` seconds into the loop."""
    return {"kind": "event", "event": "swing", "attackStarted": started, "meleeDelay": 0, "seq": int(t * 10),
            "tick": int(t * 60), "wallMs": int((T0 + t) * 1000)}


def filler(start, n, why=None):
    """`n` threat lines from index `start`, one a second, carrying `why` (a `strain` flee by default), nothing sent."""
    return [aline(start + i, float(start + i), dict(why or {"flee": "strain"}), None, sent=False) for i in range(n)]


CLEAN = [aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)]


# ================================================================ P27-F, the stuck walk's mark and the leave
def stuck_fixture(flag=True):
    """A walk stuck on square (10, 10) with its first edge north (game minute 0), the leaves after it (the walk away
    north at (10, 0), a loot, a walk back to a building at (30, 5)), a Rest proposed on the square at minute 10
    (counted), at minute 40 (beyond STUCK_MARK_MIN) and on another square, and a second mark with no edge at (50, 50)
    (minute 42) with a Rest on (50, 50) logged just before that mark (its frame reads minute 42, but the mark is not
    yet logged: not counted). The frames stand on (10, 10) from minute 0 to 10 and from 40, on (11, 10) at 12, on
    (50, 50) from 42 to 45: 15 game minutes on a live mark."""
    mark = (lambda sq, edge, goal: {"stuck_mark": {"edge": edge, "square": sq, "goal": {"type": goal, "args": {}}}}) \
        if flag else (lambda *a: {})
    leave = (lambda t, args: {"leave": {"why": "stuck", "target": {"type": t, "args": args}}}) if flag \
        else (lambda *a: {})
    walk = {"goal": "ExploreToward", "proposed": "ExploreToward"}
    log = [gline(0, 0.0, dict({"goal": "ExploreToward", "state": "failed"}, **mark([10, 10], [10, 11, "N"],
                                                                                   "ExploreToward"))),
           gline(1, 1.0, dict(walk, **leave("ExploreToward", {"x": 10, "y": 0}))),
           gline(2, 2.0, dict({"goal": "LootBuilding", "proposed": "LootBuilding"},
                              **leave("LootBuilding", {"building": 3}))),
           gline(3, 3.0, dict(walk, **leave("ExploreToward", {"x": 30, "y": 5}))),
           gline(4, 4.0, {"goal": "Rest", "proposed": "Rest"}),
           gline(5, 5.0, {"goal": "Rest", "proposed": "Rest"}),
           gline(6, 6.0, {"goal": "Rest", "proposed": "Rest"}, x=12.5),
           gline(7, 6.98, {"goal": "Rest", "proposed": "Rest"}, x=50.5, y=50.5),
           gline(8, 7.0, dict({"goal": "LootBuilding"}, **mark([50, 50], None, "LootBuilding")), x=50.5, y=50.5)]
    frames = [frame(t, minute=m, x=x, y=y) for t, m, x, y in
              ((-0.05, 0, 10.5, 10.5), (0.95, 1, 10.5, 10.5), (1.95, 2, 10.5, 10.5), (2.95, 3, 10.5, 10.5),
               (3.95, 10, 10.5, 10.5), (4.5, 12, 11.5, 10.5), (4.95, 40, 10.5, 10.5), (5.95, 41, 12.5, 10.5),
               (6.95, 42, 50.5, 50.5), (7.5, 45, 50.5, 50.5))]
    return grade(log=log, frames=frames)["stuck_leave"]


def test_the_stuck_leave_counts_the_marks_the_leaves_by_way_the_rests_on_a_mark_and_the_minutes_there():
    g = stuck_fixture()
    assert g["read"] is True and g["marks"] == {"ExploreToward": 1, "LootBuilding": 1} and g["edged"] == 1
    assert g["leaves"] == {"walk": 1, "loot": 1, "explore": 1}
    assert g["rests_on_marked"] == 1 and g["minutes_on_marked_square"] == pytest.approx(15.0)


def test_the_stuck_leave_reads_zero_without_the_why_and_unread_without_a_log():
    zero = {"read": True, "marks": {}, "edged": 0, "leaves": {"walk": 0, "loot": 0, "explore": 0},
            "rests_on_marked": 0, "minutes_on_marked_square": 0.0}
    assert stuck_fixture(flag=False) == zero
    assert grade(log=CLEAN)["stuck_leave"] == zero
    assert grade(log=None)["stuck_leave"] == {"read": False}


def test_the_walk_away_reads_its_edge_s_axis():
    mark = (0, (10, 10), [11, 10, "W"], "ExploreToward", 0.0)
    assert G._away(mark) == ((0, 10), (20, 10)) and G._away((0, (10, 10), None, "x", 0.0)) == ()
    assert G._way({"target": {"type": "ExploreToward", "args": {"x": 20, "y": 10}}}, [mark]) == "explore"
    assert G._way({"target": {"type": "ExploreToward", "args": {"x": 10, "y": 20}}}, [mark]) == "walk"
    assert G._way({"target": {"type": "ExploreToward", "args": {"x": 20, "y": 10}}}, []) == "walk"


def _leave_log():
    edge = lambda x, y: {"stuck_mark": {"edge": [x, y + 1, "N"], "square": [x, y], "goal": {"type": "ExploreToward"}}}
    leave = {"leave": {"why": "stuck", "target": {"type": "ExploreToward", "args": {"x": 10, "y": 0}}}}
    log = [gline(0, 0.0, edge(10, 10)), gline(1, 1.0, edge(50, 50), x=50.5, y=50.5),
           gline(2, 2.0, leave), gline(3, 3.0, leave, x=30.5, y=30.5), gline(4, 4.0, leave)]
    frames = [frame(t, minute=m) for t, m in ((-0.05, 0), (0.95, 1), (1.95, 2), (2.95, 3), (3.95, 31))]
    return log, frames


def test_a_leave_is_told_by_the_mark_live_on_the_square_the_line_stands_on_not_the_latest_mark():
    """Mark A at (10, 10) (edge north) and the later mark B at (50, 50); a walk to (10, 0) from (10, 10) is A's walk
    away ("explore"), the same walk from the unmarked (30, 30) is a "walk", and one from (10, 10) after A's window
    ran out is a "walk"."""
    log, frames = _leave_log()
    assert grade(log=log, frames=frames)["stuck_leave"]["leaves"] == {"walk": 2, "loot": 0, "explore": 1}


# ================================================================ P27-G, the floor finish
def floor_fixture(flag=True):
    """Four floor swings sent (at 4 with a swing event and a stomp at 4 after it; at 5 with a swing event, killing it;
    at 6 rejected `busy` with only an unstarted swing event in its act, a stomp at 99 after both; the flee's at 8 with
    a swing event and a stomp at 8 beyond FOLLOW_LINES), one logged and not sent, a `strike_runs` hold and a care line
    carrying the why."""
    ff = (lambda zid: {"floor_finish": {"target": zid, "health": 1.5}}) if flag else (lambda zid: {})
    fight = lambda zid: dict({"fight": True, "target": zid}, **ff(zid))
    log = [aline(0, 1.0, fight(4), _act("attack", targetId=4)),
           aline(1, 1.5, {"fight": True, "target": 4, "finish": 4}, _act("stomp", targetId=4)),
           aline(2, 3.0, fight(5), _act("attack", targetId=5)),
           aline(3, 5.0, fight(6), _act("attack", targetId=6)),
           aline(4, 6.0, fight(7), _act("attack", targetId=7), sent=False),
           aline(4, 6.5, {"flee": "many", "finish": 99, "kind": "stomp"}, _act("stomp", targetId=99)),
           aline(5, 7.0, {"strike_runs": {"target": 6, "aid": "f4"}} if flag else {}, None, sent=False),
           aline(6, 8.0, dict({"flee": "many", "finish": 8, "kind": "floor_finish", "dist": 1.5}, **ff(8)),
                 _act("attack", targetId=8)),
           aline(7, 8.5, fight(9), _act("attack", targetId=9), branch="care")]
    log += filler(9, G.FOLLOW_LINES)
    log += [aline(30, 30.0, {"flee": "many", "finish": 8, "kind": "stomp"}, _act("stomp", targetId=8))]
    acts = [row("f1", "attack", 1.0, ended=1.8, targetId=4), row("f2", "stomp", 1.5, targetId=4),
            row("f3", "attack", 3.0, ended=3.5, targetId=5),
            row("f4", "attack", 5.0, state="rejected", reason="busy", ended=5.1, targetId=6),
            row("f5", "attack", 8.0, targetId=8), row("f6", "attack", 8.5, branch="care", targetId=9),
            row("f7", "stomp", 30.0, targetId=8)]
    events = [swing(1.3), swing(3.2), swing(5.05, started=False), swing(8.4)]
    results = [res("f1", hit=True), res("f3", hit=True, targetDead=True), res("f5", hit=True)]
    return grade(acts, results, log, events)["floor_finish"]


def test_the_floor_finish_counts_the_swings_sent_landed_their_kills_the_holds_and_the_stomps_after():
    g = floor_fixture()
    assert g == {"read": True, "lines": 5, "sent": 4, "landed": 3, "kills": 1, "strike_holds": 1, "stomps_after": 1}


def test_the_floor_finish_reads_zero_without_the_why_and_unread_without_a_log():
    assert floor_fixture(flag=False) == {"read": True, "lines": 0, "sent": 0, "landed": 0, "kills": 0,
                                         "strike_holds": 0, "stomps_after": 0}
    assert grade(log=None)["floor_finish"] == {"read": False}


# ================================================================ P27-H, the fallen target sought
def fallen_fixture(flag=True):
    """A walk to 9 (four ticks) killed two lines on, one left (10, five ticks), a walk to 12 after two ticks (`short`)
    killed beyond FOLLOW_LINES (another zombie, 14, killed within them), a care line carrying the why and a walk to 15
    logged and not sent."""
    fs = (lambda zid, t, **kw: {"fallen_seek": dict({"target": zid, "dist": 7.5, "ticks": t}, **kw)}) if flag \
        else (lambda *a, **kw: {})
    w = lambda zid, t, **kw: dict({"target": zid, "pinned": True, "dist": 7.5}, **fs(zid, t, **kw))
    log = [aline(0, 1.0, w(9, 4), _act("walkTo", x=20.5, y=10.5)),
           aline(1, 2.0, {"fight": True, "target": 9}, None, sent=False),
           aline(2, 3.0, {"fight": True, "target": 9}, _act("stomp", targetId=9)),
           aline(3, 4.0, dict({"fight": True}, **w(10, 5, left=True)), _act("attack", targetId=11)),
           aline(4, 5.0, w(12, 2), _act("walkTo", x=22.5, y=10.5)),
           aline(5, 5.5, w(13, 4), _act("walkTo", x=23.5, y=10.5), branch="care"),
           aline(6, 6.0, {"fight": True, "target": 14}, _act("stomp", targetId=14))]
    log += filler(7, G.FOLLOW_LINES)
    log += [aline(40, 40.0, {"fight": True, "target": 12}, _act("stomp", targetId=12)),
            aline(41, 41.0, w(15, 4), _act("walkTo", x=24.5, y=10.5), sent=False)]
    acts = [row("w1", "walkTo", 1.0, x=20.5, y=10.5), row("k1", "stomp", 3.0, targetId=9),
            row("a1", "attack", 4.0, targetId=11), row("w2", "walkTo", 5.0, x=22.5, y=10.5),
            row("w3", "walkTo", 5.5, branch="care", x=23.5, y=10.5), row("k3", "stomp", 6.0, targetId=14),
            row("k2", "stomp", 40.0, targetId=12)]
    return grade(acts, [res("k1", hit=True, targetDead=True), res("k2", hit=True, targetDead=True),
                        res("k3", hit=True, targetDead=True)],
                 log)["fallen_seek"]


def test_the_fallen_seek_counts_the_walks_the_left_the_ticks_and_the_kills_after():
    g = fallen_fixture()
    assert g == {"read": True, "lines": 4, "walks": 2, "left": 1, "ticks": {"4": 2, "5": 1, "2": 1}, "short": 1,
                 "kills_after": 1}


def test_the_fallen_seek_reads_zero_without_the_why_and_unread_without_a_log():
    assert fallen_fixture(flag=False) == {"read": True, "lines": 0, "walks": 0, "left": 0, "ticks": {}, "short": 0,
                                          "kills_after": 0}
    assert grade(log=None)["fallen_seek"] == {"read": False}


# ================================================================ P27-I, the listing's left-out zombies
def zs(*spec):
    """Frame zombies at (x, 10) with `hasTarget` (the player at (10, 10))."""
    return [{"id": 100 + i, "x": x, "y": 10.0, "dist": abs(x - 10.0), "hasTarget": t} for i, (x, t) in enumerate(spec)]


def listing_fixture(flag=True):
    """Five lines carrying `listing`: two fallen left out of a listing of four (two idle within DANGER_R, two chasing
    beyond it, one chasing beyond LISTED_R: `many_avoided`); one across out of six (five left); one fallen out of four
    on a `many` flee line; one fallen out of four of which two are idle beyond DANGER_R (two counted); a care line's
    with nothing listed; one fallen out of three chasing within LISTED_R and one beyond it (three counted)."""
    lo = (lambda f, a: {"listing": {"fallen": f, "across": a}}) if flag else (lambda f, a: {})
    four = zs((13.0, False), (14.0, False), (18.0, True), (19.0, True), (25.0, True))
    log = [aline(0, 1.0, dict({"flee": "held"}, **lo(2, 0)), None, sent=False),
           aline(1, 2.0, dict({"fight": True, "target": 100}, **lo(0, 1)), None, sent=False),
           aline(2, 3.0, dict({"flee": "many"}, **lo(1, 0)), None, sent=False),
           aline(3, 4.0, dict({"flee": "held"}, **lo(1, 0)), None, sent=False),
           aline(4, 5.0, dict({"flee": "strain"}, **lo(1, 1)), None, sent=False, branch="care"),
           aline(5, 6.0, dict({"flee": "held"}, **lo(1, 0)), None, sent=False)]
    frames = [zf(0.9, four), zf(1.9, four + zs((12.0, True), (17.0, True))), zf(2.9, four),
              zf(3.9, zs((13.0, False), (14.0, False), (17.0, False), (18.0, False))), zf(4.9),
              zf(5.9, zs((13.0, True), (14.0, True), (18.0, True), (25.0, True)))]
    return grade(log=log, frames=frames)["listing"]


def test_the_listing_counts_the_fallen_and_across_left_out_and_the_many_the_clause_avoided():
    assert listing_fixture() == {"read": True, "lines": 6, "fallen": 6, "across": 2, "many_avoided": 1}


def test_the_listing_reads_zero_without_the_why_and_unread_without_a_log():
    assert listing_fixture(flag=False) == {"read": True, "lines": 0, "fallen": 0, "across": 0, "many_avoided": 0}
    assert grade(log=None)["listing"] == {"read": False}


# ================================================================ P27-J, the shove-only fight's close
def close_fixture(flag=True):
    """A walk to 3 (six ticks) shoved on the next line, one left (4), a walk to 5 after three ticks (`short`) with a
    shove at another zombie after it, a rest at an idle zombie, a plain rest and a walk to 7 logged and not sent."""
    sc = (lambda zid, t, **kw: {"shove_close": dict({"target": zid, "dist": 3.2, "ticks": t}, **kw)}) if flag \
        else (lambda *a, **kw: {})
    w = lambda zid, t, **kw: dict({"target": zid, "pinned": True, "dist": 3.2}, **sc(zid, t, **kw))
    rest = {"endurance": 0.5, "since_min": 1.0}
    log = [aline(0, 1.0, w(3, 6), _act("walkTo", x=12.5, y=10.5)),
           aline(1, 2.0, {"fight": True, "target": 3}, _act("shove", targetId=3)),
           aline(2, 3.0, dict({"fight": True}, **w(4, 6, left=True)), None, sent=False),
           aline(3, 4.0, w(5, 3), _act("walkTo", x=13.5, y=10.5)),
           aline(4, 5.0, {"fight": True, "target": 6}, _act("shove", targetId=6)),
           aline(5, 6.0, {"flee": "strain", "rest": dict(rest, **({"idle": 27031} if flag else {}))}, None,
                 sent=False),
           aline(6, 7.0, {"flee": "strain", "rest": dict(rest)}, None, sent=False),
           aline(7, 8.0, w(7, 6), _act("walkTo", x=14.5, y=10.5), sent=False)]
    acts = [row("w1", "walkTo", 1.0, x=12.5, y=10.5), row("s1", "shove", 2.0, targetId=3),
            row("w2", "walkTo", 4.0, x=13.5, y=10.5), row("s2", "shove", 5.0, targetId=6)]
    return grade(acts, [], log)["shove_close"]


def test_the_shove_close_counts_the_walks_the_left_the_idle_rests_and_the_shoves_after():
    assert close_fixture() == {"read": True, "lines": 4, "walks": 2, "left": 1, "short": 1, "idle_rests": 1,
                               "shoves_after": 1}


def test_the_shove_close_reads_zero_without_the_why_and_unread_without_a_log():
    assert close_fixture(flag=False) == {"read": True, "lines": 0, "walks": 0, "left": 0, "short": 0,
                                         "idle_rests": 0, "shoves_after": 0}
    assert grade(log=None)["shove_close"] == {"read": False}


# ================================================================ P27-K1, the early rag stock
def stock_fixture(flag=True):
    """The stock's early rip with no clean dressing (ended at 4.0; the care's `held` reads 0 rags at 2.0 and 3 at 5.0:
    `rags_after`), the goal walk's with one rag (rejected; 1 read after), the care yield's with two held (`full`) and
    one logged and not sent, and a last rip (ended at 12.0) whose next `held` reads a bandage and no rag (`rags_after`:
    a bandage is a clean dressing)."""
    se = (lambda r, b, br: {"stock_early": {"rags": r, "bandages": b, "branch": br}}) if flag else (lambda *a: {})
    stock = lambda r, b, br: {"stock": dict({"reason": "stock", "item": 50, "dressings": r + b, "stock": 2},
                                           **se(r, b, br))}
    held = lambda rag: {"bleeding": [], "spent": [], "held": {"bandage": 0, "dirty": 0, "rag": rag}}
    log = [aline(0, 1.0, {}, _act("rip", itemId=50), branch="care", care=stock(0, 0, "stock")),
           aline(1, 2.0, {}, None, sent=False, branch="care", care=held(0)),
           aline(2, 5.0, {}, None, sent=False, branch="care", care=held(3)),
           aline(3, 6.0, {}, _act("rip", itemId=51), branch="care", care=stock(1, 0, "goal")),
           aline(4, 7.0, {}, None, sent=False, branch="care", care=held(1)),
           aline(5, 8.0, {}, _act("rip", itemId=52), branch="care",
                 care=dict({"bleeding": [7]}, **se(1, 1, "yield"))),
           aline(6, 10.0, {}, _act("rip", itemId=53), sent=False, branch="care", care=stock(0, 1, "stock")),
           aline(7, 11.0, {}, _act("rip", itemId=54), branch="care", care=stock(0, 0, "stock")),
           aline(8, 13.0, {}, None, sent=False, branch="care",
                 care={"bleeding": [], "spent": [], "held": {"bandage": 1, "dirty": 0, "rag": 0}})]
    acts = [row("r1", "rip", 1.0, ended=4.0, branch="care", itemId=50),
            row("r2", "rip", 6.0, state="rejected", reason="busy", ended=6.5, branch="care", itemId=51),
            row("r3", "rip", 8.0, ended=9.0, branch="care", itemId=52),
            row("r4", "rip", 11.0, ended=12.0, branch="care", itemId=54)]
    return grade(acts, [], log)["stock_early"]


def test_the_stock_early_counts_the_rips_by_branch_the_yields_the_full_ones_and_the_rags_after():
    assert stock_fixture() == {"read": True, "lines": 5, "rips": {"stock": 2, "goal": 1, "yield": 1}, "yields": 1,
                               "full": 1, "rags_after": 2}


def test_the_stock_early_reads_zero_without_the_why_and_unread_without_a_log():
    assert stock_fixture(flag=False) == {"read": True, "lines": 0, "rips": {}, "yields": 0, "full": 0,
                                         "rags_after": 0}
    assert grade(log=None)["stock_early"] == {"read": False}


# ================================================================ P27-K2, the low fight's exit and the corner's yield
def low_fixture(flag=True):
    """An exit after three misses followed by the `health` flee and a bite 4 s on; the corner's yield on the flee's
    own line (health 15) with its bite 15 s on (beyond BITE_AFTER_S); an exit after two misses (`short`) with the
    flee only beyond FOLLOW_LINES; a yield at health 25 (`above_floor`) with a bite 5 s on; a break corner (no
    yield), then a `low_exit` why on a care-branch line (not read) and a corner yielding something other than
    `health`."""
    le = (lambda m: {"low_exit": {"target": 4, "missed": m}}) if flag else (lambda m: {})
    cy = {"corner": {"yield": "health"}} if flag else {}
    log = [aline(0, 1.0, dict({"fight": True, "low_fight": True, "target": 4}, **le(3)), None, sent=False),
           aline(1, 1.5, {"flee": "health"}, _act("walkTo", x=1.5, y=1.5)),
           inputs(aline(2, 20.0, dict({"flee": "health"}, **cy), _act("walkTo", x=1.5, y=1.5)), health=15.0),
           aline(3, 40.0, dict({"fight": True, "low_fight": True, "target": 4}, **le(2)), None, sent=False)]
    log += filler(4, G.FOLLOW_LINES)
    log += [aline(30, 62.0, {"flee": "health"}, None, sent=False),
            inputs(aline(31, 80.0, dict({"flee": "held"}, **cy), None, sent=False), health=25.0),
            aline(32, 81.0, {"fight": True, "corner": {"kind": "break", "shoved": 4, "n": 2}}, None, sent=False),
            aline(33, 90.0, dict({"fight": True, "low_fight": True, "target": 4}, **le(3)), None, sent=False,
                  branch="care"),
            inputs(aline(34, 91.0, {"flee": "held", "corner": {"yield": "fight"}}, None, sent=False), health=10.0)]
    frames = [frame(t, bitten=b) for t, b in ((0.9, 0), (5.0, 1), (19.9, 1), (35.0, 2), (39.9, 2), (45.0, 2),
                                              (79.9, 2), (85.0, 3))]
    return grade(log=log, frames=frames)["low_exit"]


def test_the_low_exit_counts_the_exits_the_yields_the_flee_after_and_the_bites_after():
    assert low_fixture() == {"read": True, "exits": 2, "short": 1, "corner_yields": 2, "above_floor": 1,
                             "flee_after": 2, "bites_after": 2}


def test_the_low_exit_reads_zero_without_the_why_and_unread_without_a_log():
    assert low_fixture(flag=False) == {"read": True, "exits": 0, "short": 0, "corner_yields": 0, "above_floor": 0,
                                       "flee_after": 0, "bites_after": 0}
    assert grade(log=None)["low_exit"] == {"read": False}


# ================================================================ P27-K3, the spent replace held
BLED7 = [{"i": 7, "bleeding": True, "bleedingTime": 12.0}]


def spent_fixture(flag=True):
    """Two holds on part 7 (the first on a frame reading it bleeding, the second on one reading part 3 bleeding), its
    replace after them and a second replace with no hold between, a hold on part 4 reading no chaser (`unchased`) and
    a replace of part 9, never held, and an unsent spent replace of part 4, held and not yet replaced."""
    sh = (lambda p, c: {"spent_held": {"part": p, "chasing": c}}) if flag else (lambda *a: {})
    care = lambda p, c: dict({"bleeding": [], "spent": [p], "held": {"bandage": 1, "dirty": 0, "rag": 0}}, **sh(p, c))
    spent = lambda p: {"reason": "spent", "part": p, "item": 5, "kind": "bandage", "life": 0, "dirty": False}
    log = [aline(0, 1.0, {}, None, sent=False, branch="care", care=care(7, 1)),
           aline(1, 2.0, {}, None, sent=False, branch="care", care=care(7, 2)),
           aline(2, 3.0, {}, _act("bandage", itemId=5, part=7), branch="care", care=spent(7)),
           aline(3, 4.0, {}, _act("bandage", itemId=6, part=7), branch="care", care=spent(7)),
           aline(4, 5.0, {}, None, sent=False, branch="care", care=care(4, 0)),
           aline(5, 6.0, {}, _act("bandage", itemId=8, part=9), branch="care", care=spent(9)),
           aline(6, 7.0, {}, _act("bandage", itemId=9, part=4), sent=False, branch="care", care=spent(4))]
    frames = [zf(0.9, parts=BLED7), zf(1.9, parts=[{"i": 3, "bleeding": True}]), zf(4.9)]
    return grade(log=log, frames=frames)["spent_held"]


def test_the_spent_held_counts_the_holds_by_part_the_unchased_the_replaces_after_and_the_bleeding_ones():
    assert spent_fixture() == {"read": True, "holds": 3, "parts": {"7": 2, "4": 1}, "unchased": 1,
                               "replaces_after": 1, "bleeding_while_held": 1}


def test_the_spent_held_reads_zero_without_the_why_and_unread_without_a_log():
    assert spent_fixture(flag=False) == {"read": True, "holds": 0, "parts": {}, "unchased": 0, "replaces_after": 0,
                                         "bleeding_while_held": 0}
    assert grade(log=None)["spent_held"] == {"read": False}


# ================================================================ P27-L, the divided swing withdrawn
def wounded_fixture(flag=True):
    """A divided swing sent and one held (both `wounded_swing`), a P25-L break after the misses, a plain two-zombie
    break (no `misses`) and a care line carrying the why."""
    ws = {"wounded_swing": 3} if flag else {}
    mb = {"misses": 3} if flag else {}
    log = [aline(0, 1.0, dict({"fight": True, "target": 4}, **ws), _act("attack", targetId=4)),
           aline(1, 1.5, dict({"fight": True, "target": 4, "holding": "w1"}, **ws), None, sent=False),
           aline(2, 3.0, {"fight": True, "corner": dict({"kind": "break", "shoved": 4, "n": 1}, **mb)},
                 _act("steer", x=1, y=1)),
           aline(3, 4.0, {"fight": True, "corner": {"kind": "break", "shoved": 4, "n": 2}}, _act("steer", x=1, y=1)),
           aline(4, 5.0, dict({"fight": True, "target": 4}, **ws), _act("attack", targetId=4), branch="care")]
    return grade(log=log)["wounded_swing_off"]


def test_the_wounded_swing_off_counts_the_divided_swings_that_went_and_the_p25_l_breaks():
    assert wounded_fixture() == {"read": True, "lines": 2, "swings": 1, "breaks": 1}


def test_the_wounded_swing_off_reads_zero_without_the_why_and_unread_without_a_log():
    assert wounded_fixture(flag=False) == {"read": True, "lines": 0, "swings": 0, "breaks": 0}
    assert grade(log=CLEAN)["wounded_swing_off"] == {"read": True, "lines": 0, "swings": 0, "breaks": 0}
    assert grade(log=None)["wounded_swing_off"] == {"read": False}


# ================================================================ grade_e17 over grade_e16
@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e17_reads_every_grade_e16_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e16 = G16.grade_e16(a, decision_lines=seen["log"], lines=seen["frames"])
    e17 = G.grade_e17(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e17["grade"] == "grade_e17" and all(e17[k]["read"] is True for k in NEW)
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e16.items() if k not in skip} == {k: v for k, v in e17.items() if k not in skip}
    assert e17["report_lines"][:-len(NEW)] == e16["report_lines"]


def test_grade_e17_without_a_decision_log_reads_the_new_keys_unread():
    g = grade(log=None)
    assert all(g[k] == {"read": False} for k in NEW) and g["grade"] == "grade_e17"
    assert all(g[k] == {"read": False} for k in NEW16)
    assert G.readings_e17({}, None, []) == {k: {"read": False} for k in NEW}


def test_report_lines_e17_names_gate_e17_then_one_line_per_reading_marked_reading_or_inference():
    g = grade(log=CLEAN)
    tail = g["report_lines"][-len(NEW):]
    assert tail == G.lines_e17(g)
    for line, tag in zip(tail, TAGS):
        assert ("(%s)" % tag) in line and "[reading]" in line
    assert sum("[inference]" in line for line in tail) == 8
    off = grade(log=None)["report_lines"][-len(NEW):]
    assert all("no decision log read" in line for line in off)
    renamed = G.report_lines_e17(dict(g, gate={"pass": True}))
    assert any(line.startswith("gate_e17 ") for line in renamed)
    assert not any(line.startswith(("gate_e13 ", "gate_e14 ", "gate_e15 ", "gate_e16 ")) for line in renamed)
    assert G.gate_e17([]) == E.gate_e13([])


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
    assert (ns["DANGER_R"], ns["LISTED_R"], ns["FLEE_HEALTH_FLOOR"], ns["MANY_LISTED_N"], ns["SHOVE_FAIL_N"],
            ns["STUCK_MARK_MIN"], ns["STUCK_LEAVE_R"], ns["FALLEN_SEEK_TICKS"], ns["SHOVE_CLOSE_TICKS"],
            ns["RAG_STOCK"]) == (6.0, 12.0, 20.0, 4, 3, 30.0, 10.0, 4, 6, 2)
    assert (ns["REST_GOAL"], ns["LOOT_GOAL"], ns["EXPLORE_GOAL"]) == ("Rest", "LootBuilding", "ExploreToward")
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/e17.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "e17_mutant"}
    exec(compile(src[:start] + new + src[end:], "e17_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    # P27-F
    ("_live_marks", lambda b: b.replace("mk[4] <= m < mk[4] + STUCK_MARK_MIN", "mk[4] <= m"),
     lambda: stuck_fixture()["rests_on_marked"] == 1),
    ("_way", lambda b: b.replace("any(to in _away(mk) for mk in live)", "False"),
     lambda: stuck_fixture()["leaves"] == {"walk": 1, "loot": 1, "explore": 1}),
    ("e_stuck_leave", lambda b: b.replace("_live_marks(marks, _line_square(ln), _line_min(L, ln), upto=i)",
                                          "[m for m in marks if m[0] <= i][-1:]"),
     lambda: grade(log=_leave_log()[0], frames=_leave_log()[1])["stuck_leave"]["leaves"]["explore"] == 1),
    ("_away", lambda b: b.replace('e[2] == "N"', 'e[2] == "W"'),
     lambda: stuck_fixture()["leaves"] == {"walk": 1, "loot": 1, "explore": 1}),
    ("_marked_minutes", lambda b: b.replace(" or not _live(marks, sq[:2], _frame_min(f0))", ""),
     lambda: stuck_fixture()["minutes_on_marked_square"] == pytest.approx(15.0)),
    ("e_stuck_leave", lambda b: b.replace('gw.get("proposed") == REST_GOAL', 'gw.get("goal") is not None'),
     lambda: stuck_fixture()["rests_on_marked"] == 1),
    ("e_stuck_leave", lambda b: b.replace(", upto=i)", ")"), lambda: stuck_fixture()["rests_on_marked"] == 1),
    # P27-G
    ("_swung", lambda b: b.replace("hi = end if end is not None else w + SWING_WINDOW_S * 1000.0", "hi = w + 1e9"),
     lambda: floor_fixture()["landed"] == 3),
    ("_swing_walls", lambda b: b.replace(' and ln.get("attackStarted") is True', ""),
     lambda: floor_fixture()["landed"] == 3),
    ("e_floor_finish", lambda b: b.replace('E._sent(r, "stomp") and _target(r) == zid', 'E._sent(r, "stomp")'),
     lambda: floor_fixture()["stomps_after"] == 1),
    ("_after", lambda b: b.replace("i + 1 + FOLLOW_LINES", "len(rows)"), lambda: floor_fixture()["stomps_after"] == 1),
    ("e_floor_finish", lambda b: b.replace('if ln.get("branch") != "threat":', "if False:"),
     lambda: floor_fixture()["lines"] == 5),
    # P27-H
    ("e_fallen_seek", lambda b: b.replace('if fs.get("left") is True:', "if False:"),
     lambda: fallen_fixture()["left"] == 1),
    ("e_fallen_seek", lambda b: b.replace("t < FALLEN_SEEK_TICKS", "t < 0"), lambda: fallen_fixture()["short"] == 1),
    ("e_fallen_seek", lambda b: b.replace('if not E._sent(ln, "walkTo"):', "if False:"),
     lambda: fallen_fixture()["walks"] == 2),
    ("e_fallen_seek", lambda b: b.replace("L.killed(r) == zid", "L.killed(r) is not None"),
     lambda: fallen_fixture()["kills_after"] == 1),
    # P27-I
    ("_listed_p24", lambda b: b.replace(' or z.get("hasTarget") is True', " or True"),
     lambda: listing_fixture()["many_avoided"] == 1),
    ("_listed_p24", lambda b: b.replace("d <= LISTED_R and ", ""), lambda: listing_fixture()["many_avoided"] == 1),
    ("e_listing", lambda b: b.replace('w.get("flee") != "many" and ', ""),
     lambda: listing_fixture()["many_avoided"] == 1),
    ("e_listing", lambda b: b.replace("before >= MANY_LISTED_N > before - k", "before >= MANY_LISTED_N"),
     lambda: listing_fixture()["many_avoided"] == 1),
    # P27-J
    ("e_shove_close", lambda b: b.replace('E._sent(r, "shove") and _target(r) == zid', 'E._sent(r, "shove")'),
     lambda: close_fixture()["shoves_after"] == 1),
    ("e_shove_close", lambda b: b.replace('and "idle" in w["rest"]', ""), lambda: close_fixture()["idle_rests"] == 1),
    ("e_shove_close", lambda b: b.replace("t < SHOVE_CLOSE_TICKS", "t < 0"), lambda: close_fixture()["short"] == 1),
    ("e_shove_close", lambda b: b.replace('if not E._sent(ln, "walkTo"):', "if False:"),
     lambda: close_fixture()["walks"] == 2),
    # P27-K1
    ("e_stock_early", lambda b: b.replace("had >= RAG_STOCK", "had > 100"), lambda: stock_fixture()["full"] == 1),
    ("e_stock_early", lambda b: b.replace(" if (E._n(r.get(\"wall\")) or 0.0) * 1000.0 >= end", ""),
     lambda: stock_fixture()["rags_after"] == 2),
    ("_stock_early", lambda b: b.replace('s = E._d(c.get("stock")).get("stock_early")', "s = None"),
     lambda: stock_fixture()["lines"] == 5),
    ("_held_clean", lambda b: b.replace(' + (E._n(h.get("bandage")) or 0)', ""),
     lambda: stock_fixture()["rags_after"] == 2),
    # P27-K2
    ("e_low_exit", lambda b: b.replace("m < SHOVE_FAIL_N", "m < 0"), lambda: low_fixture()["short"] == 1),
    ("e_low_exit", lambda b: b.replace("h >= FLEE_HEALTH_FLOOR", "h > 1000"),
     lambda: low_fixture()["above_floor"] == 1),
    ("e_low_exit", lambda b: b.replace("health(ln) or ", ""), lambda: low_fixture()["flee_after"] == 2),
    ("_bitten_after", lambda b: b.replace("w + BITE_AFTER_S * 1000.0", "w + 1e9"),
     lambda: low_fixture()["bites_after"] == 2),
    ("e_low_exit", lambda b: b.replace('w.get("low_exit") if ln.get("branch") == "threat" else None',
                                       'w.get("low_exit")'), lambda: low_fixture()["exits"] == 2),
    ("e_low_exit", lambda b: b.replace('c.get("yield") == "health"', 'c.get("yield") is not None'),
     lambda: low_fixture()["corner_yields"] == 2),
    # P27-K3
    ("e_spent_held", lambda b: b.replace("pending.discard(p)", "pass"), lambda: spent_fixture()["replaces_after"] == 1),
    ("e_spent_held", lambda b: b.replace("ch <= 0", "ch < 0"), lambda: spent_fixture()["unchased"] == 1),
    ("e_spent_held", lambda b: b.replace(' and E._sent(ln, "bandage")', ""),
     lambda: spent_fixture()["replaces_after"] == 1),
    ("_bleeding", lambda b: b.replace('p.get("i") == part and ', ""),
     lambda: spent_fixture()["bleeding_while_held"] == 1),
    # P27-L
    ("e_wounded_swing_off", lambda b: b.replace('["miss_breaks"]', '["break"]'),
     lambda: wounded_fixture()["breaks"] == 1),
    ("e_wounded_swing_off", lambda b: b.replace('E._sent(ln, "attack")', "True"),
     lambda: wounded_fixture()["swings"] == 1),
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


# ================================================================ the real checks: E19 and E18
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _real(path, name):
    p = os.path.join(path, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % path)
    g = G.grade_e17(EG17.load(p), None, EG17.load_log(p), state_dir=EG17._dir(p))
    return g, json.loads(json.dumps(EG17.finite(g), sort_keys=True, allow_nan=False))


ZERO = {
    "stuck_leave": {"read": True, "marks": {}, "edged": 0, "leaves": {"walk": 0, "loot": 0, "explore": 0},
                    "rests_on_marked": 0, "minutes_on_marked_square": 0.0},
    "floor_finish": {"read": True, "lines": 0, "sent": 0, "landed": 0, "kills": 0, "strike_holds": 0,
                     "stomps_after": 0},
    "fallen_seek": {"read": True, "lines": 0, "walks": 0, "left": 0, "ticks": {}, "short": 0, "kills_after": 0},
    "listing": {"read": True, "lines": 0, "fallen": 0, "across": 0, "many_avoided": 0},
    "shove_close": {"read": True, "lines": 0, "walks": 0, "left": 0, "short": 0, "idle_rests": 0, "shoves_after": 0},
    "stock_early": {"read": True, "lines": 0, "rips": {}, "yields": 0, "full": 0, "rags_after": 0},
    "low_exit": {"read": True, "exits": 0, "short": 0, "corner_yields": 0, "above_floor": 0, "flee_after": 0,
                 "bites_after": 0},
    "spent_held": {"read": True, "holds": 0, "parts": {}, "unchased": 0, "replaces_after": 0,
                   "bleeding_while_held": 0},
    "wounded_swing_off": {"read": True, "lines": 0, "swings": 0, "breaks": 0},
}


def test_grade_e17_on_e19_keeps_every_grade_e16_key_as_the_committed_e_grade_txt_and_reads_every_new_key_0():
    """E19 ran survival iteration 19 (no iteration 20 why exists on it, and it sent no divided swing nor a P25-L
    break): every new key reads 0."""
    g, mine = _real(E19, "e_day_19.json")
    assert g["grade"] == "grade_e17" and all(g[k] == ZERO[k] for k in NEW)
    _, committed = _committed(E19, "e_grade.txt")
    for k in NEW:
        mine.pop(k)
    mine["grade"] = "grade_e16"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed


def test_grade_e17_on_e18_keeps_every_grade_e15_key_as_the_committed_e_grade_txt_and_reads_the_new_keys():
    """E18 ran survival iteration 18 with P26-L1's divided swing on: its six `wounded_swing` lines and three swings
    sent at 30468 (grade_e16's `wounded_swings`) are `wounded_swing_off`'s, no P25-L break; every other new key 0."""
    g, mine = _real(E18, "e_day_18.json")
    assert g["grade"] == "grade_e17"
    for k in NEW:
        assert g[k] == (dict(ZERO[k], lines=6, swings=3) if k == "wounded_swing_off" else ZERO[k]), k
    assert (g["wounded_swings"]["lines"], g["wounded_swings"]["sent"]) == (6, 3)
    _, committed = _committed(E18, "e_grade.txt")
    for k in NEW + NEW16:
        mine.pop(k)
    mine["grade"] = "grade_e15"
    mine["report_lines"] = mine["report_lines"][:-len(NEW) - len(NEW16)]
    assert mine == committed


@pytest.mark.parametrize("path,name,old,extra", [(E19, "e_day_19.json", "grade_e16", ()),
                                                 (E18, "e_day_18.json", "grade_e15", NEW16)], ids=("E19", "E18"))
def test_e_grade_17_prints_the_committed_e_grade_txt_s_lines_then_the_new_ones(path, name, old, extra):
    """`e_grade_17.py` on the committed artifact: the committed `e_grade.txt`'s report lines byte for byte (CRLF
    folded), then the later passes' lines, then the JSON whose inherited keys equal the committed."""
    p = os.path.join(path, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % path)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_17.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    raw = r.stdout.replace(b"\r\n", b"\n")
    want_raw = open(os.path.join(path, "e_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    head = want_raw[:want_raw.index(b"\n{\n") + 1]
    assert raw.startswith(head)
    text = raw.decode("utf-8")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(path, "e_grade.txt")
    added = len(NEW) + len(extra)
    assert printed[:-added] == want_lines and len(printed) == len(want_lines) + added
    assert got["grade"] == "grade_e17" and printed[-len(NEW):] == got["report_lines"][-len(NEW):]
    for k in NEW + tuple(extra):
        got.pop(k)
    got["grade"] = old
    got["report_lines"] = got["report_lines"][:-added]
    assert got == want


def test_e_grade_17_on_e20_reproduces_the_committed_e_grade_txt_byte_for_byte():
    """Ruling P26-Q: `e_grade_17.py` on the committed E20 artifact (the first session graded through `grade_e17`)
    reproduces its committed `e_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the
    grade chain (`grade_e16`, `grade_e15`, `grade_e14`) fails here."""
    p = os.path.join(E20, "e_day_20.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E20)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_17.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(E20, "e_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want


def test_e_grade_17_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5: a driver's refusal is tested without invoking it on a bad argument): its
    main answers usage, exit 2, on no path or more than two outside `--chain`."""
    src = open(EG17.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e17 import gate_e17, grade_e17, report_lines_e17" in src
    assert "usage: e_grade_17.py" in src and "e16" not in src[src.index('"""', 3):]
