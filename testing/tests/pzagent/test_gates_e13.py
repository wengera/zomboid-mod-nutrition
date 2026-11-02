"""base/gates_e.py pass 13 (Plan 25 Task 15), offline: `grade_e13` and its four readings of survival iteration 16 (the stand's
early drag end P25-U, its inside end P25-V, the way out P25-W, the known blocked edges P25-X), each on a fixture decision log
where it reads zero and one where it counts, a mutant per reading, `grade_e12` unchanged on E15 under `grade_e13`, and
`e_grade_13.py`."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated, act, aline, zf
from .test_gates_e11 import bline

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E15 = os.path.join(TESTING, "artifacts", "e_day_15-20261102-091322")
NEW = ("stand_drag", "stand_inside", "stand_exit", "blocked_edge")


def grade(actions=(), results=(), log=None, frames=(), goals=(), stop="day_cap"):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    a["stop"]["reason"] = stop
    if goals:
        a["loop"]["goals"] = list(goals)
    return E.grade_e13(a, decision_lines=log, lines=list(frames))


def _act(type_, **args):
    return {"type": type_, "args": args}


# ================================================================ the committed artifact
def _load(name):
    p = os.path.join(E15, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E15)
    return p


def _e15():
    with open(_load("e_day_15.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(_load("decision.log"), encoding="utf-8") if l.strip()]
    return o, log


def test_grade_e13_on_e15_changes_only_the_grade_name_the_four_readings_and_the_report():
    o, log = _e15()
    e12 = E.grade_e12(o, decision_lines=log, state_dir=E15)
    e13 = E.grade_e13(o, decision_lines=log, state_dir=E15)
    skip = ("grade", "report_lines") + NEW
    assert e13["grade"] == "grade_e13" and all(e13[k]["read"] is True for k in NEW)
    assert {k: v for k, v in e12.items() if k not in skip} == {k: v for k, v in e13.items() if k not in skip}
    keep = lambda r: [l for l in r if not l.startswith("gate_e")]
    assert keep(e13["report_lines"])[:len(keep(e12["report_lines"]))] == keep(e12["report_lines"])
    assert len(e13["report_lines"]) == len(e12["report_lines"]) + 4


def test_grade_e13_on_e15_reads_the_iteration_16_keys_zero_and_iteration_15s_cycle_at_its_pinned_values():
    o, log = _e15()
    g = E.grade_e13(o, decision_lines=log, state_dir=E15)
    # E15 ran iteration 15: none of the iteration 16 whys existed
    assert (g["stand_drag"]["lines"], g["stand_inside"]["lines"], g["stand_exit"]["lines"]) == (0, 0, 0)
    assert g["stand_exit"]["closes"] == g["stand_exit"]["exit_missing"] == g["stand_exit"]["close_sends"] == 0
    be = g["blocked_edge"]
    assert be["sites"] == {} and be["own"] == {} and be["refuse_marks"] == 0 and be["goal_ends"] == 0
    # the dead stretch: twelve marks at 8064 each preceded by a reposition that failed `stuck`, one at 8036
    assert (be["cycles"], be["cycle_target"], be["cycle_marks"]) == (12, "8064", 13)
    assert be["old_marks"] == {"8036": 1, "8064": 12}
    # the seeks across the fence row's blocked edge that iteration 15 sent (inference off the map): nonzero by construction
    assert be["across"] > 0 and set(be["across_by"]) <= {"fight_aim", "fight_walk", "goal_walk", "goal_loot", "need_fill"}


def test_grade_e12_on_e15_still_reproduces_the_committed_report_byte_for_byte_through_e_grade_12():
    p = _load("e_day_15.json")
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", "e_grade_12.py"), p],
                       capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(_load("e_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want


# ================================================================ P25-U, the stand's early drag end
def drag_fixture(flag=True):
    d = lambda extra: dict({"flee": "doorway"}, **extra) if flag else {"flee": "doorway"}
    ex = {"end": "drag", "exit": "door"}
    log = [aline(0, 0.0, d({"doorway_left": "drag", "doorway_drag": 2, "doorway_exit": ex}), _act("walkTo", x=1.5, y=1.5)),
           aline(1, 1.0, {"flee": "doorway", "exit": 3}, None, sent=False),
           aline(2, 5.0, d({"doorway_left": "drag", "doorway_drag": 3.0, "doorway_exit": dict(ex, exit="trapped")}), None, sent=False),
           aline(3, 6.0, {"flee": "doorway"}, None, sent=False),
           aline(4, 10.0, d({"doorway_left": "drag", "doorway_drag": 1}), None, sent=False),
           aline(5, 11.0, {"fight": True, "target": 1}, None, sent=False),
           aline(6, 12.0, d({"doorway_left": "drag"}), None, sent=False),
           aline(16, 12.2, d({"doorway_left": "drag", "doorway_drag": 2.5}), None, sent=False),
           aline(17, 12.4, d({"doorway_left": "drag", "doorway_drag": True}), None, sent=False),
           aline(7, 13.0, d({"doorway_left": "quiet"}), None, sent=False),
           bline(8, 14.0, "care", {"reason": "bandage"}, None, sent=False,
                 others={"threat": d({"doorway_left": "drag", "doorway_drag": 2})} if flag else {"threat": {"flee": "doorway"}}),
           aline(9, 15.0, {"flee": "unreachable"}, None, sent=False)]
    return grade(log=log)["stand_drag"]


def test_the_stand_drag_end_counts_the_ends_the_attackers_the_exit_and_the_line_after_each():
    g = drag_fixture()
    assert g["read"] is True and g["lines"] == 7 and g["attackers"] == {"2": 2, "3": 1, "1": 1}
    assert (g["no_count"], g["under"], g["with_exit"]) == (3, 1, 2)       # no count, 2.5 and True are not integer counts
    # 0 -> the way out running (a `doorway` flee with the Flee's `exit`); 2 -> the close; 4 -> a fight line; the three ends
    # without a count -> each a `doorway` flee; the care-branch line (carrying the threat's drag end) -> an `unreachable` flee
    assert g["next"] == {"walk_out": 1, "doorway": 4, "flee": 1, "other": 1, "open": 0}


def test_the_stand_drag_end_reads_the_last_line_open_and_zero_without_the_why_or_a_log():
    log = [aline(0, 0.0, {"flee": "doorway", "doorway_left": "drag", "doorway_drag": 2}, None, sent=False)]
    assert grade(log=log)["stand_drag"]["next"]["open"] == 1
    g = drag_fixture(flag=False)
    assert (g["lines"], g["attackers"], g["no_count"], g["under"], g["with_exit"]) == (0, {}, 0, 0, 0)
    assert grade(log=None)["stand_drag"] == {"read": False}


# ================================================================ P25-V, the stand's inside end
def inside_fixture(flag=True):
    d = lambda extra: dict({"flee": "doorway"}, **extra) if flag else {"flee": "doorway"}
    ex = {"end": "inside", "exit": "opening"}
    log = [aline(0, 0.0, d({"doorway_left": "inside", "doorway_inside": {"id": 4, "square": [113, 200]}, "doorway_exit": ex}),
                 _act("walkTo", x=1.5, y=1.5)),
           aline(1, 1.0, {"flee": "doorway", "exit": 3}, None, sent=False),
           aline(2, 5.0, d({"doorway_left": "inside", "doorway_inside": {"id": 4, "square": [113, 201]}}), None, sent=False),
           aline(3, 6.0, d({"doorway_left": "inside", "doorway_inside": {"id": 5, "square": [113, 201]}}), None, sent=False),
           aline(4, 7.0, d({"doorway_left": "inside"}), None, sent=False),
           aline(5, 8.0, d({"doorway_left": "inside", "doorway_inside": {"square": [1, 2]}}), None, sent=False),
           aline(6, 9.0, d({"doorway_left": "inside", "doorway_inside": {"id": 6, "square": [1]}}), None, sent=False),
           aline(7, 10.0, d({"doorway_left": "inside", "doorway_inside": {"id": 6, "square": ["x", 2]}}), None, sent=False),
           aline(8, 11.0, d({"doorway_left": "drag", "doorway_drag": 2}), None, sent=False)]
    return grade(log=log)["stand_inside"]


def test_the_stand_inside_end_counts_the_ends_the_zombies_named_the_bad_dicts_and_the_line_after():
    g = inside_fixture()
    assert g["read"] is True and (g["lines"], g["ids"], g["no_inside"], g["malformed"], g["with_exit"]) == (7, 2, 1, 3, 1)
    assert g["next"] == {"walk_out": 1, "doorway": 6, "flee": 0, "other": 0, "open": 0}


def test_the_stand_inside_end_reads_zero_without_the_why_and_unread_without_a_log():
    g = inside_fixture(flag=False)
    assert (g["lines"], g["ids"], g["no_inside"], g["malformed"], g["with_exit"]) == (0,) * 5
    assert grade(log=None)["stand_inside"] == {"read": False}


# ================================================================ P25-W, the way out
def sqr(x, y, **kw):
    s = {"x": x, "y": y, "z": 0, "solid": False, "solidTrans": False, "room": None, "building": None, "door": None,
         "blockN": False, "blockW": False, "hopN": False, "hopW": False}
    s.update(kw)
    return s


def mline(t, squares):
    return {"kind": "map", "wallMs": int((T0 + t) * 1000), "squares": squares}


def exit_fixture(close=False, mapped=True):
    ex = lambda end, how: {"end": end, "exit": how}
    walk = {"flee": "doorway", "exit": 2}
    c = _act("interact", x=3, y=0, kind="close")
    log = [aline(90, -0.5, {"fight": True, "target": 1}, None, sent=False),               # a prelude: the first exit is not line 0
           aline(0, 0.0, {"flee": "doorway", "doorway_left": "wound", "doorway_wound": [3], "doorway_exit": ex("wound", "door")},
                 _act("walkTo", x=5.5, y=0.5)),
           aline(1, 1.0, walk, None, sent=False),
           aline(2, 2.0, walk, c if close else None, sent=close),
           aline(3, 3.0, walk, c if close else None, sent=False),      # a close not sent: never counted
           aline(4, 4.0, {"fight": True, "target": 1}, None, sent=False),
           aline(5, 5.0, {"flee": "doorway"}, c, sent=True),     # after the window: a quiet end's close, not counted
           aline(6, 6.0, {"flee": "doorway", "doorway_left": "drag", "doorway_drag": 2, "doorway_exit": ex("drag", "trapped")},
                 None, sent=False),
           bline(7, 7.0, "care", {"reason": "bandage"}, _act("bandage", part=3), sent=True,
                 others={"threat": {"trapped": 1}}),       # the care took the trapped tick: the threat why has no flee
           bline(8, 8.0, "goal", {"goal": "Rest"}, None, sent=False),
           aline(9, 9.0, {"flee": "doorway", "doorway_left": "inside", "doorway_inside": {"id": 4, "square": [1, 0]},
                          "doorway_exit": ex("wound", "steer")}, None, sent=False),
           aline(10, 10.0, {"flee": "doorway", "doorway_left": "inside"}, None, sent=False),      # an exit end with no doorway_exit
           aline(11, 11.0, {"flee": "doorway", "doorway_left": "quiet"}, None, sent=False)]      # a close end: not an exit end
    frames = [zf(t, x=2.5 if t < 1 or t >= 6 else 3.5 if t < 2 else 4.5 if t < 3 else 5.5, y=0.5,
                 attackers={1: 2, 2: 3, 3: 5, 7: 4}.get(t, 0)) for t in range(12)]
    squares = [sqr(x, 0, room="kitchen") for x in range(4)] + [sqr(x, 0) for x in range(4, 9)]
    maps = [mline(-1, squares)] if mapped else []
    acts = [act("w1", "walkTo", 0.0, x=5.5, y=0.5)]
    return grade(acts, [], log, frames + maps)["stand_exit"]


def test_the_stand_exit_counts_the_exits_the_mismatches_the_missing_the_closes_and_the_way_to_the_open():
    g = exit_fixture()
    assert g["read"] is True and g["lines"] == 3
    assert g["by_end"] == {"wound": 2, "drag": 1} and g["by_exit"] == {"door": 1, "trapped": 1, "steer": 1}
    assert g["by_pair"] == {"wound:door": 1, "drag:trapped": 1, "wound:steer": 1}
    assert (g["end_mismatch"], g["exit_missing"]) == (1, 1)
    assert g["next"] == {"walk_out": 1, "doorway": 1, "flee": 0, "other": 1, "open": 0}
    assert (g["closes"], g["close_sends"]) == (0, 1)
    # the first exit's frames read inside at 0 and 1, outside at 2 (two lines on); the others stay inside the kitchen
    assert g["outside_lines"] == [2, None, None] and g["outside_s"] == [2.0, None, None] and g["unread"] == 0
    # the most attackers: 4 on the frame at 7, inside the second exit's window (the care took the tick the threat's why lacks a
    # flee on); the frame at 3 (5 attackers) lies past the first exit's outside reading
    assert g["max_attackers"] == 4


def test_the_stand_exit_counts_a_close_inside_the_window_and_not_the_one_after_it():
    g = exit_fixture(close=True)
    assert (g["closes"], g["close_sends"]) == (1, 2)


def test_the_stand_exit_reads_the_frames_unread_without_a_map_and_zero_without_the_why():
    g = exit_fixture(mapped=False)
    assert g["outside_lines"] == [None, None, None] and g["unread"] == 3
    z = grade(log=[aline(0, 0.0, {"flee": "doorway", "doorway_left": "quiet"}, None, sent=False)])["stand_exit"]
    assert (z["lines"], z["by_end"], z["by_exit"], z["closes"], z["exit_missing"], z["outside_lines"]) == (0, {}, {}, 0, 0, [])
    assert grade(log=None)["stand_exit"] == {"read": False}


def test_the_map_view_reads_the_latest_record_of_a_square_as_of_a_wall_and_restarts_when_it_falls():
    mv = E._MapView([mline(1, [sqr(1, 1, room="a"), sqr(2, 2)]), mline(5, [sqr(1, 1)]), {"kind": "frame"}])
    assert mv.at(T0 + 0) == {} and mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"
    assert mv.at(T0 + 6)[(1, 1, 0)]["room"] is None and (2, 2, 0) in mv.map
    assert mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"     # a wall earlier than the cursor restarts the sweep
    assert mv.at(None) is mv.map


def test_the_crossed_edge_reads_a_blocked_outdoor_edge_not_a_hoppable_one_a_room_wall_or_an_unmapped_step():
    col = lambda kw={}: {(5, y, 0): sqr(5, y, **kw.get(y, {})) for y in range(5, 12)}
    wall = col({10: {"blockN": True}})
    assert E._crossed_edge(wall, 0, (5.5, 11.5), (5.5, 8.5)) == [5, 10, "N"]
    assert E._crossed_edge(wall, 0, (5.5, 8.5), (5.5, 11.5)) == [5, 10, "N"]       # either direction
    assert E._crossed_edge(wall, 0, (5.5, 11.5), (5.5, 10.5)) is None             # the wall is not between them
    assert E._crossed_edge(col({10: {"blockN": True, "hopN": True}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
    assert E._crossed_edge(col({10: {"blockN": True, "room": "kitchen"}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
    assert E._crossed_edge(col({9: {"room": "kitchen"}, 10: {"blockN": True}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
    assert E._crossed_edge({k: v for k, v in wall.items() if k != (5, 9, 0)}, 0, (5.5, 11.5), (5.5, 8.5)) is None
    assert E._crossed_edge(wall, 1, (5.5, 11.5), (5.5, 8.5)) is None              # another floor
    west = {(x, 5, 0): sqr(x, 5, **({"blockW": True} if x == 4 else {})) for x in range(2, 8)}
    assert E._crossed_edge(west, 0, (6.5, 5.5), (2.5, 5.5)) == [4, 5, "W"]
    diag = {(x, y, 0): sqr(x, y, **({"blockN": True} if (x, y) == (6, 5) else {})) for x in (5, 6) for y in (4, 5)}
    assert E._crossed_edge(diag, 0, (5.5, 5.5), (6.5, 4.5)) == [6, 5, "N"]        # a diagonal step read through its corner legs
    assert E._crossed_edge({(x, y, 0): sqr(x, y) for x in (5, 6) for y in (4, 5)}, 0, (5.5, 5.5), (6.5, 4.5)) is None


# ================================================================ P25-X, the known blocked edges
EDGE = {"edge": [5, 10, "N"], "door": None, "action": "refuse"}
ROUTE = dict(EDGE, door=[8, 10], action="route")


def edge_fixture(cross=True):
    """A wall at (5, 10) N between the player (5.5, 11.5) and a zombie at (5.5, 8.5), the goal and fill targets beyond it
    (`cross`), else all on the player's side (5.5, 12.5): the seeks the ruling refuses, the refusal, the routes, the goal
    dropped and cooled, and iteration 15's cycle (a reposition that failed `stuck`, then the mark)."""
    zy = 8.5 if cross else 12.5
    f = lambda n, t, w, a=None, s=True: aline(n, t, dict({"fight": True}, **w), a, sent=s)
    log = [f(0, 0.0, {"target": 7}, _act("aim", targetId=7)),
           f(1, 1.0, {"target": 7, "advance": True}, _act("walkTo", x=5.5, y=zy, gait="run")),
           f(2, 2.0, {"target": 7, "marked": 7, "blocked_edge": EDGE}, None, False),
           f(3, 3.0, {"target": 7, "blocked_edge": ROUTE}, _act("walkTo", x=8.5, y=9.5, gait="run")),
           f(4, 4.0, {"target": 7, "blocked_edge": ROUTE}, _act("walkTo", x=8.5, y=9.5, gait="run")),
           f(5, 5.0, {"target": 9, "reposition": [5, 9, 0]}, _act("walkTo", x=5.5, y=zy, gait="run")),
           f(6, 6.0, {"target": 9, "marked": 9}, None, False),
           f(7, 7.0, {"target": 9, "reposition": [5, 9, 0]}, _act("walkTo", x=5.5, y=zy, gait="run")),
           f(8, 8.0, {"target": 9, "marked": 9}, None, False),
           f(9, 9.0, {"target": 10, "marked": 10}, None, False),
           bline(10, 10.0, "goal", {"goal": "LootBuilding", "blocked_edge": dict(EDGE, action="drop")}, None, sent=False),
           bline(11, 11.0, "goal", {"refused": {"type": "LootBuilding", "args": {"building": 2}}}, None, sent=False),
           bline(12, 12.0, "goal", {"refused": {"type": "LootBuilding", "args": {"building": 3}}}, None, sent=False),
           bline(13, 13.0, "goal", {"goal": "ExploreToward"}, _act("walkTo", x=5.5, y=zy, gait="walk")),
           bline(14, 14.0, "goal", {"goal": "LootBuilding"}, _act("interact", x=5, y=int(zy - 0.5), kind="loot")),
           bline(15, 15.0, "goal", {"goal": "ExploreToward", "blocked_edge": ROUTE, "leg": [8.5, 9.5]},
                 _act("walkTo", x=8.5, y=9.5, gait="walk")),
           bline(16, 16.0, "need", {"fill": {"source": [5, 8], "vessel": 1, "blocked_edge": ROUTE}}, None, sent=False),
           bline(17, 17.0, "need", {"fill": {"source": [5, 8], "vessel": 1}}, _act("fill", itemId=1, x=5, y=int(zy - 0.5))),
           f(18, 18.0, {"target": 11, "advance": True}, _act("walkTo", x=5.5, y=zy, gait="run")),
           f(19, 19.0, {"target": 11, "marked": 11}, None, False)]
    stuck = lambda a: dict(a, state="failed", reason="stuck")
    acts = [act("a3", "walkTo", 3.0, x=8.5, y=9.5, gait="run"), stuck(act("a4", "walkTo", 4.0, x=8.5, y=9.5, gait="run")),
            stuck(act("a5", "walkTo", 5.0, x=5.5, y=zy, gait="run")), stuck(act("a7", "walkTo", 7.0, x=5.5, y=zy, gait="run")),
            stuck(act("a18", "walkTo", 18.0, x=5.5, y=zy, gait="run"))]     # a seek walk that failed `stuck` but is no reposition
    goals = [{"type": "LootBuilding", "args": {"building": 2}, "state": "failed", "reason": "blocked edge"},
             {"type": "Shelter", "args": {"building": 4}, "state": "failed", "reason": "shunned"},
             {"type": "LootBuilding", "args": {"building": 3}, "state": "done", "reason": None}]
    frames = [zf(t, [{"id": 7, "x": 5.5, "y": zy, "dist": 3.0}], x=5.5, y=11.5) for t in range(21)]
    squares = [sqr(x, y, **({"blockN": True} if y == 10 else {})) for x in range(5, 10) for y in range(7, 14)]   # a wall along y 10
    return grade(acts, [], log, frames + [mline(-1, squares)], goals)["blocked_edge"]


def test_the_blocked_edge_counts_the_sites_the_routes_the_refusal_the_goal_end_and_the_cooled_refusal():
    g = edge_fixture()
    assert g["read"] is True
    assert g["sites"] == {"threat:refuse": 1, "threat:route": 2, "goal:drop": 1, "goal:route": 1, "need:route": 1}
    assert g["own"] == g["sites"]
    assert g["doors"] == [(8, 10)] and (g["refuse_marks"], g["refuse_targets"]) == (1, 1)
    assert g["route_walks"] == {"done": 1, "stuck": 1}
    assert (g["goal_ends"], g["goal_types"], g["cooled_refused"]) == (1, {"LootBuilding": 1}, 1)


def test_the_blocked_edge_counts_iteration_15s_cycle_marks_and_the_most_at_one_zombie():
    g = edge_fixture()
    assert g["old_marks"] == {"9": 2, "10": 1, "11": 1} and (g["cycle_marks"], g["cycles"], g["cycle_target"]) == (2, 2, "9")


def test_the_blocked_edge_counts_the_sends_that_still_went_across_and_not_the_routed_ones():
    g = edge_fixture()
    # the aim, the four fight walks (the seeks and two repositions), the goal's walk and loot, the fill: eight; the route walks
    # (their own blocked_edge) cross the wall at the door's x as well and are not counted
    assert g["across"] == 8 and g["across_by"] == {"fight_aim": 1, "fight_walk": 4, "goal_walk": 1, "goal_loot": 1, "need_fill": 1}
    assert g["unread"] == 0


def test_the_blocked_edge_across_reads_zero_with_every_target_on_the_players_side():
    g = edge_fixture(cross=False)
    assert g["across"] == 0 and g["across_by"] == {} and g["unread"] == 0
    assert g["sites"]["threat:route"] == 2          # the other keys are the fixture's own and do not move


def test_the_blocked_edge_reads_zero_on_a_log_of_iteration_15_s_shape_without_a_cycle_or_an_edge():
    log = [aline(0, 0.0, {"fight": True, "target": 1}, _act("aim", targetId=1)),
           aline(1, 1.0, {"fight": True, "target": 1, "marked": 1}, None, sent=False),
           bline(2, 2.0, "goal", {"goal": "Rest"}, None, sent=False)]
    g = grade(log=log, frames=[zf(0.0, [{"id": 1, "x": 5.5, "y": 8.5, "dist": 3.0}], x=5.5, y=11.5)])["blocked_edge"]
    assert (g["sites"], g["own"], g["doors"], g["refuse_marks"], g["route_walks"], g["goal_ends"], g["cooled_refused"]) == (
        {}, {}, [], 0, {}, 0, 0)
    assert (g["cycle_marks"], g["cycles"], g["cycle_target"], g["across"]) == (0, 0, None, 0)
    assert g["old_marks"] == {"1": 1} and g["unread"] == 0      # no map line: no edge is known, the aim reads across nothing
    assert grade(log=None)["blocked_edge"] == {"read": False}


def test_a_stuck_reposition_is_read_off_the_action_row_not_the_line_and_a_done_one_is_no_cycle():
    log = [aline(0, 0.0, {"fight": True, "target": 9, "reposition": [5, 9, 0]}, _act("walkTo", x=1.5, y=1.5), sent=True),
           aline(1, 1.0, {"fight": True, "target": 9, "marked": 9}, None, sent=False)]
    g = grade([act("a0", "walkTo", 0.0, x=1.5, y=1.5)], [], log)["blocked_edge"]       # the walk ended `done`
    assert g["old_marks"] == {"9": 1} and g["cycle_marks"] == 0 and g["cycles"] == 0


# ================================================================ the report
def test_the_report_names_the_four_rules_and_marks_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])
    r = g["report_lines"]
    assert g["grade"] == "grade_e13" and set(g) >= set(NEW)
    for t in ("stand drag end (P25-U) [reading]", "stand inside end (P25-V) [reading]", "stand way out (P25-W) [reading]",
              "blocked edges (P25-X) [reading]"):
        assert any(l.startswith(t) for l in r), t
    assert sum("[inference" in l for l in r) >= 12
    be = next(l for l in r if l.startswith("blocked edges"))
    assert "must read 0 with the switch on" in be and "[inference off the map and the frames]" in be and "E15: 12" in be
    we = next(l for l in r if l.startswith("stand way out"))
    assert "must read 0" in we and "until the frame reads outside the building [inference]" in we
    assert not any(l.startswith("gate_e11 ") or l.startswith("gate_e12 ") for l in r)
    nolog = grade(log=None)["report_lines"]
    for t in ("stand drag end (P25-U): no decision log read", "stand inside end (P25-V): no decision log read",
              "stand way out (P25-W): no decision log read", "blocked edges (P25-X): no decision log read"):
        assert t in nolog
    assert E.gate_e13([art()]) == E.gate_e12([art()])


# ================================================================ a mutant per reading
# (the function edited, the edit, the fixture assertion it must fail, the attribute to patch when it is not the function)
MUTANTS = [
    ("_end_lines", lambda b: b.replace('== end', '!= end'), lambda: drag_fixture()["attackers"] == {"2": 2, "3": 1, "1": 1}, None),
    ("_end_lines", lambda b: b.replace('L.why(ln).get("doorway_left") == end', 'L.why(ln).get("doorway_left") is not None'),
     lambda: drag_fixture()["lines"] == 7, None),
    ("_kind_after", lambda b: b.replace('"walk_out" if "exit" in w else "doorway"', '"doorway"'),
     lambda: drag_fixture()["next"]["walk_out"] == 1, None),
    ("_kind_after", lambda b: b.replace('w.get("flee") == "doorway"', 'w.get("flee") is not None'),
     lambda: drag_fixture()["next"]["doorway"] == 4, None),
    ("_kind_after", lambda b: b.replace('"open"', '"other"'), lambda: grade(log=[aline(0, 0.0, {"flee": "doorway", "doorway_left": "drag",
                                                                                              "doorway_drag": 2}, None, sent=False)]
                                                                       )["stand_drag"]["next"]["open"] == 1, None),
    ("e_stand_drag", lambda b: b.replace("c < DRAG_DOWN_N - 1", "c < DRAG_DOWN_N"), lambda: drag_fixture()["under"] == 1, None),
    ("e_stand_drag", lambda b: b.replace("c < DRAG_DOWN_N - 1", "c < 0"), lambda: drag_fixture()["under"] == 1, None),
    ("e_stand_drag", lambda b: b.replace('"doorway_drag"', '"doorway_xx"'), lambda: drag_fixture()["attackers"] == {"2": 2, "3": 1, "1": 1}, None),
    ("e_stand_drag", lambda b: b.replace('_end_lines(L, "drag")', '_end_lines(L, "inside")'), lambda: drag_fixture()["lines"] == 7, None),
    ("e_stand_drag", lambda b: b.replace('isinstance(L.why(ln).get("doorway_exit"), dict)', "False"),
     lambda: drag_fixture()["with_exit"] == 2, None),
    ("_int", lambda b: b.replace("n == int(n)", "True"), lambda: drag_fixture()["attackers"] == {"2": 2, "3": 1, "1": 1}, None),
    ("_int", lambda b: b.replace("int(n) if n is not None", "int(n) if True"), lambda: _int_bool_is_none(), None),
    ("e_stand_inside", lambda b: b.replace('"inside"', '"drag"'), lambda: inside_fixture()["lines"] == 7, None),
    ("e_stand_inside", lambda b: b.replace('ids.add(repr(d["id"]))', 'ids.add(1)'), lambda: inside_fixture()["ids"] == 2, None),
    ("e_stand_inside", lambda b: b.replace("len(sq) == 2", "len(sq) >= 1"), lambda: inside_fixture()["malformed"] == 3, None),
    ("e_stand_inside", lambda b: b.replace('d.get("id") is None or ', ""), lambda: inside_fixture()["malformed"] == 3, None),
    ("e_stand_inside", lambda b: b.replace('all(_n(x) is not None for x in sq)', "True"), lambda: inside_fixture()["malformed"] == 3, None),
    ("e_stand_inside", lambda b: b.replace("none += 1", "none += 0"), lambda: inside_fixture()["no_inside"] == 1, None),
    ("e_stand_inside", lambda b: b.replace('isinstance(L.why(ln).get("doorway_exit"), dict)', "True"),
     lambda: inside_fixture()["with_exit"] == 1, None),
    ("e_stand_exit", lambda b: b.replace("w.get(\"doorway_left\") in STAND_EXIT_ENDS", "w.get(\"doorway_left\") is not None"),
     lambda: exit_fixture()["exit_missing"] == 1, None),
    ("e_stand_exit", lambda b: b.replace("mismatch += 1 if ex.get(\"end\") != w.get(\"doorway_left\") else 0", "pass"),
     lambda: exit_fixture()["end_mismatch"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('by_exit[str(ex.get("exit"))] = by_exit.get(str(ex.get("exit")), 0) + 1', "pass"),
     lambda: exit_fixture()["by_exit"] == {"door": 1, "trapped": 1, "steer": 1}, None),
    ("e_stand_exit", lambda b: b.replace('by_end[str(ex.get("end"))] = by_end.get(str(ex.get("end")), 0) + 1', "pass"),
     lambda: exit_fixture()["by_end"] == {"wound": 2, "drag": 1}, None),
    ("e_stand_exit", lambda b: b.replace('k = "%s:%s" % (ex.get("end"), ex.get("exit"))', 'k = "x"'),
     lambda: exit_fixture()["by_pair"] == {"wound:door": 1, "drag:trapped": 1, "wound:steer": 1}, None),
    ("e_stand_exit", lambda b: b.replace('kind") == "close"', 'kind") == "open"'), lambda: exit_fixture(close=True)["closes"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('_sent(r, "interact") and', "True and"), lambda: exit_fixture(close=True)["closes"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('rw.get("flee") is None or ', ""), lambda: exit_fixture(close=True)["closes"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('j > i and (', 'False and ('), lambda: exit_fixture(close=True)["closes"] == 1, None),
    ("e_stand_exit", lambda b: b.replace("EXIT_WINDOW_LINES", "1"), lambda: exit_fixture(close=True)["closes"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('r.get("branch") != "care"', "True"), lambda: exit_fixture()["max_attackers"] == 4, None),
    ("e_stand_exit", lambda b: b.replace("if reached is None and out_:", "if out_:"), lambda: exit_fixture()["outside_lines"] == [2, None, None]
     and _reached_first_holds(), None),
    ("e_stand_exit", lambda b: b.replace("reached - i", "reached"), lambda: exit_fixture()["outside_lines"] == [2, None, None], None),
    ("e_stand_exit", lambda b: b.replace("rows[reached if reached is not None else last]", "rows[min(len(rows), i + EXIT_WINDOW_LINES) - 1]"),
     lambda: exit_fixture()["max_attackers"] == 4, None),
    ("e_stand_exit", lambda b: b.replace("round(w1 - w0, 3)", "round(w0 - w1, 3)"), lambda: exit_fixture()["outside_s"][0] == 2.0, None),
    ("e_stand_exit", lambda b: b.replace("unread += 0 if readable else 1", "unread += 0"), lambda: exit_fixture(mapped=False)["unread"] == 3, None),
    ("e_stand_exit", lambda b: b.replace("readable = readable or out_ is not None", "readable = True"),
     lambda: exit_fixture(mapped=False)["unread"] == 3, None),
    ("e_stand_exit", lambda b: b.replace("bisect.bisect_right(walls, (_n(hi.get(\"wall\")) or 0.0) * 1000.0)",
                                         "bisect.bisect_right(walls, 1e15)"), lambda: exit_fixture()["max_attackers"] == 4, None),
    ("e_stand_exit", lambda b: b.replace("bisect.bisect_left(walls, (_n(ln.get(\"wall\")) or 0.0) * 1000.0)", "0"),
     lambda: exit_fixture()["max_attackers"] == 4 and _attackers_start_holds(), None),
    ("e_stand_exit", lambda b: b.replace('nxt[_kind_after(L, i)] += 1', "pass"), lambda: exit_fixture()["next"]["walk_out"] == 1, None),
    ("e_stand_exit", lambda b: b.replace('"close_sends": sum(1 for r in rows if _sent(r, "interact")', '"close_sends": sum(0 for r in rows if _sent(r, "interact")'),
     lambda: exit_fixture()["close_sends"] == 1, None),
    ("e_stand_exit", lambda b: b.replace("mv = _MapView(lines)", "mv = _MapView([])"), lambda: exit_fixture()["outside_lines"] == [2, None, None], None),
    ("e_stand_inside", lambda b: b.replace("self.rows[self.i][0] <= ms", "self.rows[self.i][0] < ms"), lambda: _map_view_holds(), "_MapView"),
    ("e_stand_inside", lambda b: b.replace("self.rows[self.i - 1][0] > ms", "False"), lambda: _map_view_holds(), "_MapView"),
    ("e_stand_inside", lambda b: b.replace('self.map[(s["x"], s["y"], s.get("z") or 0)] = s', 'self.map.setdefault((s["x"], s["y"], s.get("z") or 0), s)'),
     lambda: _map_view_holds(), "_MapView"),
    ("_outside", lambda b: b.replace("is None else s.get(\"room\") is None", "is None else s.get(\"room\") is not None"),
     lambda: exit_fixture()["outside_lines"] == [2, None, None], None),
    ("_frame_me", lambda b: b.replace('_n(_d(ln.get("inputs")).get("x"))', "None"), lambda: _inputs_pos_holds(), None),
    ("_edge_wall", lambda b: b.replace('rec.get("block" + side) is True', 'rec.get("block" + side) is not None'), lambda: _crossed_holds(), None),
    ("_edge_wall", lambda b: b.replace('rec.get("hop" + side) is not True', "True"), lambda: _crossed_holds(), None),
    ("_edge_wall", lambda b: b.replace('sp.get("room") is not None or sq.get("room") is not None', "False"), lambda: _crossed_holds(), None),
    ("_edge_wall", lambda b: b.replace('holder, side = (p, "N") if q[1] < p[1] else (q, "N")', 'holder, side = (p, "N")'), lambda: _crossed_holds(), None),
    ("_edge_wall", lambda b: b.replace('holder, side = (p, "W") if q[0] < p[0] else (q, "W")', 'holder, side = (p, "W")'), lambda: _crossed_holds(), None),
    ("_crossed_edge", lambda b: b.replace("for c in ((q[0], p[1], z), (p[0], q[1], z)):", "for c in ():"), lambda: _crossed_holds(), None),
    ("_crossed_edge", lambda b: b.replace("for u, v in ((p, c), (c, q)):", "for u, v in ((p, c),):"), lambda: _crossed_holds(), None),
    ("_across_dest", lambda b: b.replace('t == "aim"', 't == "xx"'), lambda: edge_fixture()["across_by"].get("fight_aim") == 1, None),
    ("_across_dest", lambda b: b.replace('"fight_walk", xy', '"fight_walk", None'), lambda: edge_fixture()["across"] == 8, None),
    ("_across_dest", lambda b: b.replace('br == "goal" and t == "walkTo"', 'br == "goal" and t == "xx"'),
     lambda: edge_fixture()["across_by"].get("goal_walk") == 1, None),
    ("_across_dest", lambda b: b.replace('args.get("kind") == "loot"', 'args.get("kind") == "xx"'),
     lambda: edge_fixture()["across_by"].get("goal_loot") == 1, None),
    ("_across_dest", lambda b: b.replace('t == "fill"', 't == "xx"'), lambda: edge_fixture()["across_by"].get("need_fill") == 1, None),
    ("_across_dest", lambda b: b.replace("L.is_fight(ln) and t == \"walkTo\"", "t == \"walkTo\""),
     lambda: edge_fixture()["across"] == 8 and _flee_walk_not_across(), None),
    ("_across_dest", lambda b: b.replace('ln.get("sent") is not True', "False"), lambda: _unsent_not_across(), None),
    ("_across_dest", lambda b: b.replace('z.get("id") == zid', "True"), lambda: edge_fixture()["across"] == 8 and _aim_id_holds(), None),
    ("_own_edge", lambda b: b.replace('br in ("threat", "goal", "need")', 'br in ("threat",)'), lambda: edge_fixture()["own"] == edge_fixture()["sites"], None),
    ("_own_edge", lambda b: b.replace('br == "need" and isinstance(w.get("fill"), dict)', "False"),
     lambda: edge_fixture()["own"] == edge_fixture()["sites"], None),
    ("_edge_sites", lambda b: b.replace('("goal", _bw(ln, "goal")),', ""), lambda: edge_fixture()["sites"].get("goal:drop") == 1, None),
    ("_edge_sites", lambda b: b.replace('("need", _d(_bw(ln, "need").get("fill")))', '("need", {})'),
     lambda: edge_fixture()["sites"].get("need:route") == 1, None),
    ("_edge_sites", lambda b: b.replace('("threat", _bw(ln, "threat")),', ""), lambda: edge_fixture()["sites"].get("threat:route") == 2, None),
    ("e_blocked_edge", lambda b: b.replace('isinstance(_own_edge(ln), dict)', "False"), lambda: edge_fixture()["across"] == 8, None),
    ("e_blocked_edge", lambda b: b.replace("is not None:\n            across[kind]", "is None:\n            across[kind]"),
     lambda: edge_fixture()["across"] == 8, None),
    ("e_blocked_edge", lambda b: b.replace("doors.add(tuple(b[\"door\"]))", "pass"), lambda: edge_fixture()["doors"] == [(8, 10)], None),
    ("e_blocked_edge", lambda b: b.replace('b.get("action") == "route" and isinstance', 'b.get("action") == "xx" and isinstance'),
     lambda: edge_fixture()["doors"] == [(8, 10)], None),
    ("e_blocked_edge", lambda b: b.replace("marks += 1", "marks += 0"), lambda: edge_fixture()["refuse_marks"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace("targets.add(repr(w[\"marked\"]))", "pass"), lambda: edge_fixture()["refuse_targets"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('"done" if row.get("state") == "done" else str(row.get("reason"))', '"done"'),
     lambda: edge_fixture()["route_walks"] == {"done": 1, "stuck": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('and _sent(ln, "walkTo"):\n            row = L.action(ln)\n            end', 'and False:\n            row = L.action(ln)\n            end'),
     lambda: edge_fixture()["route_walks"] == {"done": 1, "stuck": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('g.get("reason") == "blocked edge"', 'g.get("reason") == "shunned"'),
     lambda: edge_fixture()["goal_types"] == {"LootBuilding": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('g.get("state") == "failed" and ', ""), lambda: edge_fixture()["goal_ends"] == 1 and _goal_state_holds(), None),
    ("e_blocked_edge", lambda b: b.replace("in ended else 0", "in ended or True else 0"), lambda: edge_fixture()["cooled_refused"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('r.get("args")], sort_keys=True, default=str) in ended', 'None], sort_keys=True, default=str) in ended'),
     lambda: edge_fixture()["cooled_refused"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('row.get("reason") == "stuck"', 'row.get("reason") == "xx"'), lambda: edge_fixture()["cycles"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace('row.get("state") == "failed" and ', ""), lambda: edge_fixture()["cycles"] == 2 and _done_reposition_holds(), None),
    ("e_blocked_edge", lambda b: b.replace("pending.pop(t, False)", "True"), lambda: edge_fixture()["cycle_marks"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("not isinstance(w.get(\"blocked_edge\"), dict):\n            t = repr", "True:\n            t = repr"),
     lambda: edge_fixture()["old_marks"] == {"9": 2, "10": 1, "11": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('w.get("reposition") is not None and zid is not None', "zid is not None"),
     lambda: edge_fixture()["cycle_marks"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("max(cycle.items(), key=lambda p: (p[1], p[0]))", "min(cycle.items(), key=lambda p: (p[1], p[0]))"),
     lambda: edge_fixture()["cycles"] == 2 and _two_targets_cycle(), None),
    ("e_blocked_edge", lambda b: b.replace('cycle[t] = cycle.get(t, 0) + 1', 'cycle[t] = 1'), lambda: edge_fixture()["cycles"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("unread += 1", "unread += 0"), lambda: _unread_holds(), None),
]


def _int_bool_is_none():
    return E._int(True) is None and E._int(2.0) == 2 and E._int(2.5) is None and E._int("x") is None


def _two_targets_cycle():
    """Two zombies cycled, three and one times: `cycles` is the most (3), not the least."""
    log = []
    n = 0
    for zid, k in ((9, 3), (10, 1)):
        for _ in range(k):
            log.append(aline(n, float(n), {"fight": True, "target": zid, "reposition": [5, 9, 0]}, _act("walkTo", x=1.5 + n, y=1.5)))
            log.append(aline(n + 1, n + 0.5, {"fight": True, "target": zid, "marked": zid}, None, sent=False))
            n += 1
    acts = [dict(act("a%d" % i, "walkTo", float(i), x=1.5 + i, y=1.5), state="failed", reason="stuck") for i in range(n)]
    g = grade(acts, [], log)["blocked_edge"]
    return (g["cycles"], g["cycle_target"], g["cycle_marks"]) == (3, "9", 4)


def _care_window_holds():
    """A care-branch line inside the way out whose threat why has no flee does not end the window; a goal-branch one does."""
    return exit_fixture()["lines"] == 3


def _reached_first_holds():
    """The outside reading is the FIRST line that reads outside (2), not the last (3, when the player is still out)."""
    return exit_fixture()["outside_lines"][0] == 2


def _attackers_start_holds():
    """Frames before the exit tick do not count: a frame at 0 with 9 attackers lies before an exit tick at 1."""
    log = [aline(0, 0.0, {"fight": True}, None, sent=False),
           aline(1, 1.0, {"flee": "doorway", "doorway_left": "wound", "doorway_exit": {"end": "wound", "exit": "door"}}, None, sent=False)]
    f = [zf(0, x=2.5, y=0.5, attackers=9), zf(1, x=2.5, y=0.5, attackers=1)]
    return grade(log=log, frames=f)["stand_exit"]["max_attackers"] == 1


def _map_view_holds():
    mv = E._MapView([mline(1, [sqr(1, 1, room="a"), sqr(2, 2)]), mline(5, [sqr(1, 1)])])
    ok = mv.at(T0 + 0) == {} and mv.at(T0 + 1)[(1, 1, 0)]["room"] == "a"
    ok = ok and mv.at(T0 + 6)[(1, 1, 0)]["room"] is None
    return ok and mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"


def _inputs_pos_holds():
    """A line's own inputs x, y win over the frame's me."""
    log = [aline(0, 0.0, {"fight": True, "target": 1}, _act("aim", targetId=1))]
    log[0]["inputs"].update(x=5.5, y=11.5)
    f = [zf(0, [{"id": 1, "x": 5.5, "y": 8.5, "dist": 3.0}], x=9.5, y=8.0)]       # the frame's me stands elsewhere, beside the zombie
    wall = [mline(-1, [sqr(5, y, **({"blockN": True} if y == 10 else {})) for y in range(7, 13)])]
    return grade(log=log, frames=f + wall)["blocked_edge"]["across"] == 1


def _crossed_holds():
    col = lambda kw={}: {(5, y, 0): sqr(5, y, **kw.get(y, {})) for y in range(5, 12)}
    wall = col({10: {"blockN": True}})
    west = {(x, 5, 0): sqr(x, 5, **({"blockW": True} if x == 4 else {})) for x in range(2, 8)}
    diag = {(x, y, 0): sqr(x, y, **({"blockN": True} if (x, y) == (6, 5) else {})) for x in (5, 6) for y in (4, 5)}
    return (E._crossed_edge(wall, 0, (5.5, 11.5), (5.5, 8.5)) == [5, 10, "N"]
            and E._crossed_edge(wall, 0, (5.5, 8.5), (5.5, 11.5)) == [5, 10, "N"]
            and E._crossed_edge(col({10: {"blockN": True, "hopN": True}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
            and E._crossed_edge(col({10: {"blockN": True, "room": "kitchen"}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
            and E._crossed_edge(col({10: {"blockN": False}}), 0, (5.5, 11.5), (5.5, 8.5)) is None
            and E._crossed_edge({k: v for k, v in wall.items() if k != (5, 9, 0)}, 0, (5.5, 11.5), (5.5, 8.5)) is None
            and E._crossed_edge(west, 0, (6.5, 5.5), (2.5, 5.5)) == [4, 5, "W"]
            and E._crossed_edge(west, 0, (2.5, 5.5), (6.5, 5.5)) == [4, 5, "W"]
            and E._crossed_edge(diag, 0, (5.5, 5.5), (6.5, 4.5)) == [6, 5, "N"]
            and E._crossed_edge(wall, 0, (5.5, 8.5), (5.5, 10.5)) == [5, 10, "N"]       # a south step keeps the edge on its far square
            and E._crossed_edge(wall, 0, (5.5, 10.5), (5.5, 11.5)) is None
            and E._crossed_edge(west, 0, (3.5, 5.5), (4.5, 5.5)) == [4, 5, "W"]         # an east step the same
            and E._crossed_edge(west, 0, (4.5, 5.5), (5.5, 5.5)) is None)


def _flee_walk_not_across():
    """A `walkTo` of a threat line that is no fight line (the flee's steer-walk) is no seek across."""
    log = [aline(0, 0.0, {"flee": "unreachable"}, _act("walkTo", x=5.5, y=8.5, gait="run"))]
    f = [zf(0, x=5.5, y=11.5)]
    wall = [mline(-1, [sqr(5, y, **({"blockN": True} if y == 10 else {})) for y in range(7, 13)])]
    return grade(log=log, frames=f + wall)["blocked_edge"]["across"] == 0


def _unsent_not_across():
    log = [aline(0, 0.0, {"fight": True, "target": 1}, _act("walkTo", x=5.5, y=8.5), sent=False)]
    f = [zf(0, x=5.5, y=11.5)]
    wall = [mline(-1, [sqr(5, y, **({"blockN": True} if y == 10 else {})) for y in range(7, 13)])]
    return grade(log=log, frames=f + wall)["blocked_edge"]["across"] == 0


def _aim_id_holds():
    """An aim reads its own target's position, not the first zombie's: zombie 1 beside the player, zombie 7 across the wall."""
    log = [aline(0, 0.0, {"fight": True, "target": 7}, _act("aim", targetId=7))]
    f = [zf(0, [{"id": 1, "x": 5.5, "y": 12.5, "dist": 1.0}, {"id": 7, "x": 5.5, "y": 8.5, "dist": 3.0}], x=5.5, y=11.5)]
    wall = [mline(-1, [sqr(5, y, **({"blockN": True} if y == 10 else {})) for y in range(7, 14)])]
    return grade(log=log, frames=f + wall)["blocked_edge"]["across"] == 1


def _goal_state_holds():
    """A goal row ended with reason "blocked edge" but not `failed` is no goal end."""
    g = grade(log=[], goals=[{"type": "LootBuilding", "args": {"building": 2}, "state": "done", "reason": "blocked edge"}])
    return g["blocked_edge"]["goal_ends"] == 0


def _done_reposition_holds():
    log = [aline(0, 0.0, {"fight": True, "target": 9, "reposition": [5, 9, 0]}, _act("walkTo", x=1.5, y=1.5)),
           aline(1, 1.0, {"fight": True, "target": 9, "marked": 9}, None, sent=False)]
    row = dict(act("a0", "walkTo", 0.0, x=1.5, y=1.5), state="done", reason="stuck")
    return grade([row], [], log)["blocked_edge"]["cycles"] == 0


def _unread_holds():
    """A candidate with no frame to read its position from counts `unread` and is not counted across."""
    log = [aline(0, 0.0, {"fight": True, "target": 7}, _act("aim", targetId=7))]
    g = grade(log=log, frames=[])["blocked_edge"]
    return g["unread"] == 1 and g["across"] == 0


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds, attr = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(E, attr or fn_name, _mutated(fn_name, edit)[attr or fn_name])
    try:
        survives = holds()
    except Exception:       # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % fn_name


# ================================================================ e_grade_13.py
def test_e_grade_13_is_e_grade_12s_command_line_over_grade_e13(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_13.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "\nkills sources: " in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e13"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e13 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script, *args], capture_output=True, cwd=TESTING).returncode == 2


def test_e_grade_13_is_e_grade_12_with_only_the_grade_names_changed():
    a = open(os.path.join(TESTING, "agent", "drivers", "e_grade_12.py"), encoding="utf-8").read()
    b = open(os.path.join(TESTING, "agent", "drivers", "e_grade_13.py"), encoding="utf-8").read()
    body = b[b.index("\nimport json"):]
    assert body.replace("e_grade_13", "e_grade_12").replace("grade_e13", "grade_e12").replace("gate_e13", "gate_e12").replace(
        "report_lines_e13", "report_lines_e12") == a[a.index("\nimport json"):]
