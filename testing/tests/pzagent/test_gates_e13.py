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
NEW = ("stand_drag", "stand_inside", "stand_exit", "blocked_edge", "edge_out", "stand_order", "dirty_rip")


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


def test_grade_e13_on_e15_changes_only_the_grade_name_the_seven_readings_and_the_report():
    o, log = _e15()
    e12 = E.grade_e12(o, decision_lines=log, state_dir=E15)
    e13 = E.grade_e13(o, decision_lines=log, state_dir=E15)
    skip = ("grade", "report_lines") + NEW
    assert e13["grade"] == "grade_e13" and all(e13[k]["read"] is True for k in NEW)
    assert {k: v for k, v in e12.items() if k not in skip} == {k: v for k, v in e13.items() if k not in skip}
    keep = lambda r: [l for l in r if not l.startswith("gate_e")]
    assert keep(e13["report_lines"])[:len(keep(e12["report_lines"]))] == keep(e12["report_lines"])
    assert len(e13["report_lines"]) == len(e12["report_lines"]) + 7


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
    # the 203 sends whose straight line crossed the fence row's blocked edge (the review of Task 15) read through the planner's
    # own edge read: five of them walk round the run (the seek goes on by design), 100 stand under the pull's exemption read off
    # the stance (a route read with the stance held) and 98 are no exemption's (iteration 15 had no edge read: nonzero by
    # construction, and 0 on E16)
    assert (be["walked_round"], be["exempt"], be["across"], be["unread"]) == (5, {"stance_route": 100}, 98, 0)
    assert be["across_by"] == {"fight_aim": 27, "fight_walk": 24, "goal_walk": 1, "goal_loot": 29, "need_fill": 17}
    assert be["walked_round"] + sum(be["exempt"].values()) + be["across"] == 203
    # every one of the 13 stuck repositions of the dead stretch crossed the fence row's blocked edge (the old mark's cycle there)
    assert (be["cycle_across"], be["cycles_across"]) == (13, 12)
    # the fix round's readings: none of iteration 16's keys, no mark, no stand, no care line with `dirty`
    assert g["edge_out"] == {"read": True, "marks": 0, "out_lines": 0, "unreachable_flees": 216, "flees_with_mark": 0, "only_out": 0}
    assert g["stand_order"] == {"read": True, "drag_under_health": 0, "with_exit": 0, "health_ends": 0, "health_dragged": 0}
    assert g["dirty_rip"]["lines"] == 0 and g["stand_exit"]["max_attackers"] == g["stand_exit"]["health_drop"] == []


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
    for t, f in enumerate(frames):
        f["body"]["health"] = {1: 90, 2: 80, 3: 50, 7: 60, 8: 55, 9: 70}.get(t, 100)
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
    # the most attackers per exit: 3 on the frame at 2 (the first exit's last), 4 on the frame at 7, inside the second exit's
    # window (the care took the tick the threat's why lacks a flee on; the frame at 3, 5 attackers, lies past the first exit's
    # outside reading), 0 for the third; the health fall over the same windows: 100 -> 80, 100 -> 60, 70 -> 70
    assert g["max_attackers"] == [3, 4, 0] and g["health_drop"] == [20, 40, 0]


def test_the_stand_exit_counts_a_close_inside_the_window_and_not_the_one_after_it():
    g = exit_fixture(close=True)
    assert (g["closes"], g["close_sends"]) == (1, 2)


def test_the_stand_exit_reads_the_frames_unread_without_a_map_and_zero_without_the_why():
    g = exit_fixture(mapped=False)
    assert g["outside_lines"] == [None, None, None] and g["unread"] == 3
    assert g["max_attackers"] == [5, 4, 0]       # with no map the window never reaches outside: it runs to the line the flee ends on
    z = grade(log=[aline(0, 0.0, {"flee": "doorway", "doorway_left": "quiet"}, None, sent=False)])["stand_exit"]
    assert (z["lines"], z["by_end"], z["by_exit"], z["closes"], z["exit_missing"], z["outside_lines"]) == (0, {}, {}, 0, 0, [])
    assert z["max_attackers"] == [] and z["health_drop"] == []
    assert grade(log=None)["stand_exit"] == {"read": False}


def test_the_map_view_reads_the_latest_record_of_a_square_as_of_a_wall_and_restarts_when_it_falls():
    mv = E._MapView([mline(1, [sqr(1, 1, room="a"), sqr(2, 2)]), mline(5, [sqr(1, 1)]), {"kind": "frame"}])
    assert mv.at(T0 + 0) == {} and mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"
    assert mv.at(T0 + 6)[(1, 1, 0)]["room"] is None and (2, 2, 0) in mv.map
    assert mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"     # a wall earlier than the cursor restarts the sweep
    assert mv.at(None) == {} and mv.at(T0 + 6)[(1, 1, 0)]["room"] is None     # no wall reads no map, not the one the call before left


def _shell_holds():
    ln = {"wall": T0 + 5.0}
    mv = E._MapView([mline(1, [sqr(5, 10, blockN=True)]), mline(9, [sqr(5, 10)])])
    widths = E._widths(([(T0 + 2.0) * 1000, (T0 + 4.0) * 1000, (T0 + 8.0) * 1000],
                        [{"me": {"loadedWidth": 104}}, {"me": {"loadedWidth": None}}, {"me": {"loadedWidth": 152}}]))
    sh = E._shell_at(E.World(), mv, widths, ln, (5.5, 11.5, 0))
    return (sh.map[(5, 10, 0)]["blockN"] is True and sh.me == {"x": 5.5, "y": 11.5, "z": 0} and sh.loaded_width == 104
            and E._width_at(widths, T0 + 1.0) is None and E._width_at(widths, T0 + 9.0) == 152 and E._width_at(widths, None) is None
            and E._widths(([1.0], [{"me": {"loadedWidth": True}}])) == ([], [])
            and E._widths(([1.0], [{"me": {"loadedWidth": 0}}])) == ([], [])
            and E._widths(([1.0], [{"me": {"loadedWidth": 48.0}}])) == ([], []))


def test_the_edge_shell_gives_the_planner_s_edge_read_the_map_the_player_and_the_loaded_width_as_of_a_line():
    assert _shell_holds()


def test_the_planner_s_edge_read_decides_what_crosses_a_hoppable_edge_a_room_wall_and_an_unmapped_step_do_not():
    from agent.base.planner import edges
    col = lambda kw={}: {(5, y, 0): sqr(5, y, **kw.get(y, {})) for y in range(5, 12)}

    def read(mp, a=(5.5, 11.5), b=(5.5, 8.5), z=0):
        sh = E.World()
        sh.map, sh.me = mp, {"x": a[0], "y": a[1], "z": z}
        return edges.edge_read(sh, a, b, 10.0)
    assert read(col({10: {"blockN": True}}))["edge"] == ((5, 10, 0), "N")
    assert read(col({10: {"blockN": True, "hopN": True}})) is None
    assert read(col({10: {"blockN": True, "room": "kitchen"}})) is None
    assert read(col({10: {"blockN": True}}), z=1) is None


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
           bline(16, 16.0, "need", {"fill": {"source": [5, 8], "vessel": 1, "blocked_edge": ROUTE, "walk": [8, 9]}},
                 _act("walkTo", x=8.5, y=9.5, gait="walk")),
           bline(17, 17.0, "need", {"fill": {"source": [5, 8], "vessel": 1}}, _act("fill", itemId=1, x=5, y=int(zy - 0.5))),
           f(18, 18.0, {"target": 11, "advance": True}, _act("walkTo", x=5.5, y=zy, gait="run")),
           f(19, 19.0, {"target": 11, "marked": 11}, None, False)]
    stuck = lambda a: dict(a, state="failed", reason="stuck")
    acts = [act("a3", "walkTo", 3.0, x=8.5, y=9.5, gait="run"), stuck(act("a4", "walkTo", 4.0, x=8.5, y=9.5, gait="run")),
            stuck(act("a5", "walkTo", 5.0, x=5.5, y=zy, gait="run")), stuck(act("a7", "walkTo", 7.0, x=5.5, y=zy, gait="run")),
            act("a15", "walkTo", 15.0, x=8.5, y=9.5, gait="walk"),
            dict(act("a16", "walkTo", 16.0, x=8.5, y=9.5, gait="walk"), state="failed", reason="no path"),
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
    assert g["doors"] == [(8, 10)] and (g["refuse_marks"], g["refuse_routed"], g["refuse_targets"]) == (1, 0, 1)
    # a route walk per site (Task 15 fix 1, minor 2): the threat's two, the goal's leg walk and the need's walk
    assert g["route_walks"] == {"threat:done": 1, "threat:stuck": 1, "goal:done": 1, "need:no path": 1}
    assert (g["goal_ends"], g["goal_types"], g["cooled_refused"]) == (1, {"LootBuilding": 1}, 1)


def test_the_blocked_edge_counts_iteration_15s_cycle_marks_and_the_most_at_one_zombie():
    g = edge_fixture()
    assert g["old_marks"] == {"9": 2, "10": 1, "11": 1} and (g["cycle_marks"], g["cycles"], g["cycle_target"]) == (2, 2, "9")
    assert (g["cycle_across"], g["cycles_across"]) == (2, 2)      # both stuck repositions crossed the wall


def test_the_blocked_edge_counts_the_sends_that_still_went_across_and_not_the_routed_ones():
    g = edge_fixture()
    # the aim, the four fight walks (the seeks and two repositions), the goal's walk and loot, the fill: eight; the route walks
    # (their own blocked_edge) cross the wall at the door's x as well and are not counted
    assert g["across"] == 8 and g["across_by"] == {"fight_aim": 1, "fight_walk": 4, "goal_walk": 1, "goal_loot": 1, "need_fill": 1}
    assert (g["unread"], g["exempt"], g["walked_round"]) == (0, {}, 0)


def test_the_blocked_edge_across_reads_zero_with_every_target_on_the_players_side():
    g = edge_fixture(cross=False)
    assert g["across"] == 0 and g["across_by"] == {} and g["unread"] == 0 and g["exempt"] == {} and g["walked_round"] == 0
    assert g["sites"]["threat:route"] == 2          # the other keys are the fixture's own and do not move
    assert (g["cycle_marks"], g["cycle_across"], g["cycles_across"]) == (2, 0, 0)     # the old mark fires; no known edge there


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


# ---- the planner's own edge read: what it reads as no crossing, and the exemptions the unexplained rest is split from
def wall_squares(door=False, hop=False, end=None, xs=range(5, 13)):
    """A wall along y 10 (the north edges of its squares) over `xs`, y 7 to 13: an unlocked door record at (8, 10) with `door`,
    the hop flag with `hop`, the run ending (open edges) from x `end` on."""
    out = []
    for x in xs:
        for y in range(7, 14):
            kw = {}
            if y == 10 and (end is None or x < end):
                kw["blockN"] = True
                kw["hopN"] = hop
                if door and x == 8:
                    kw.update(door={"locked": False}, edgeN=True)
            out.append(sqr(x, y, **kw))
    return out


def one(line, squares=None, frames=(), acts=()):
    """The blocked_edge reading of a log of `line` alone: the player at (5.5, 11.5), zombie 7 at (5.5, 8.5) across the wall."""
    fs = [zf(0.0, [{"id": 7, "x": 5.5, "y": 8.5, "dist": 3.0}], x=5.5, y=11.5)] + list(frames)
    return grade(list(acts), [], [line], fs + [mline(-1, wall_squares() if squares is None else squares)])["blocked_edge"]


def fight(extra=None, a=None):
    return aline(0, 0.0, dict({"fight": True, "target": 7}, **(extra or {})), a or _act("aim", targetId=7))


def test_a_send_across_a_wall_with_no_door_and_no_exemption_is_the_unexplained_count():
    g = one(fight())
    assert (g["across"], g["across_by"], g["exempt"], g["walked_round"]) == (1, {"fight_aim": 1}, {}, 0)
    g = one(fight(), squares=wall_squares(door=True))      # the planner would have routed it through the door at (8, 10)
    assert (g["across"], g["exempt"]) == (1, {})


def test_a_send_across_a_run_the_planner_walks_round_is_counted_beside_not_as_the_unexplained():
    g = one(fight(), squares=wall_squares(end=6))      # the run ends at x 6: the nearest way is its end
    assert (g["across"], g["walked_round"], g["exempt"], g["unread"]) == (0, 1, {}, 0)
    g = one(fight(), squares=wall_squares(hop=True))   # a hoppable stretch is no known blocked edge at all
    assert (g["across"], g["walked_round"], g["exempt"]) == (0, 0, {})


@pytest.mark.parametrize("extra,name", [
    ({"cornered": 7, "corner_kind": "walk"}, "cornered"), ({"cornered": 0}, "cornered"),
    ({"corner": {"kind": "swing", "shoved": 7, "n": 1}}, "cornered"), ({"sheltered": True}, "door_fight"),
    ({"finish": 7, "kind": "stomp", "dist": 1.0}, "finish"), ({"finish_first": {"target": 7, "dist": 1.0}}, "finish_first"),
    ({"fence_wait": {"target": 7, "fence": [5, 10], "dist": 3.0, "leg": "stand"}}, "fence_wait")])
def test_a_fight_send_the_planner_s_edge_answer_never_reaches_is_exempt_by_the_why_that_names_it(extra, name):
    for door in (False, True):
        g = one(fight(extra), squares=wall_squares(door=door))
        assert (g["across"], g["exempt"]) == (0, {name: 1}), (extra, door)


def test_the_pull_and_the_held_stance_exempt_a_route_read_and_never_a_refusal():
    g = one(fight({"pull": [5.0, 5.0], "stance": True, "leg": "pull"}), squares=wall_squares(door=True))
    assert (g["across"], g["exempt"]) == (0, {"pull": 1})
    g = one(fight({"stance": True, "leg": "stand"}), squares=wall_squares(door=True))      # no why of the pull's own: inference
    assert (g["across"], g["exempt"]) == (0, {"stance_route": 1})
    for extra in ({"pull": [5.0, 5.0], "stance": True}, {"stance": True}):     # a wall with no door is refused, pull or not
        g = one(fight(extra))
        assert (g["across"], g["exempt"]) == (1, {}), extra
    assert one(fight({"pull": False, "stance": False}), squares=wall_squares(door=True))["across"] == 1


def test_a_goal_outside_the_three_p25_x_goals_is_exempt_by_its_name_and_one_of_theirs_is_not():
    loot = lambda goal, **kw: bline(0, 0.0, "goal", dict({"goal": goal}, **kw), _act("interact", x=5, y=8, kind="loot"))
    assert E.EDGE_GOALS == ("ExploreToward", "LootBuilding", "Shelter")
    g = one(loot("Stock"))
    assert (g["across"], g["exempt"]) == (0, {"goal:Stock": 1})
    g = one(loot("LootBuilding"))
    assert (g["across"], g["across_by"], g["exempt"]) == (1, {"goal_loot": 1}, {})
    walk = bline(0, 0.0, "goal", {"goal": "Rest"}, _act("walkTo", x=5.5, y=8.5, gait="walk"))
    assert one(walk)["exempt"] == {"goal:Rest": 1}
    assert one(bline(0, 0.0, "need", {"fill": {"source": [5, 8], "vessel": 1}}, _act("fill", itemId=1, x=5, y=8)))["across_by"] == {
        "need_fill": 1}


def test_a_goal_walk_reads_the_goals_whole_target_and_a_loot_its_container_not_the_leg_or_the_door():
    leg = _act("walkTo", x=5.5, y=11.0, gait="walk")        # the leg's end stays on the player's side of the wall
    assert one(bline(0, 0.0, "goal", {"goal": "ExploreToward"}, leg))["across"] == 0
    g = one(bline(0, 0.0, "goal", {"goal": "ExploreToward", "toward": [5, 8], "leg": [5.5, 11.0]}, leg))
    assert (g["across"], g["across_by"]) == (1, {"goal_walk": 1})
    near = _act("interact", x=5, y=11, kind="loot")
    assert one(bline(0, 0.0, "goal", {"goal": "LootBuilding"}, near))["across"] == 0
    assert one(bline(0, 0.0, "goal", {"goal": "LootBuilding", "container": [5, 8, 0, 0]}, near))["across"] == 1


def test_a_fight_walk_reads_its_target_the_planner_read_not_the_walks_own_end():
    g = one(fight(a=_act("walkTo", x=5.5, y=11.0, gait="run")))
    assert (g["across"], g["across_by"]) == (1, {"fight_walk": 1})
    assert one(fight({"target": 99}, a=_act("walkTo", x=5.5, y=11.0, gait="run")))["across"] == 0      # unlisted: the walk's end


def test_the_reach_of_the_edge_read_is_the_fights_for_a_fight_and_the_loaded_width_s_leg_for_a_goal():
    # a run of blocked edges from x 5 to 24 and open from 25: the nearest way is its end, 20 tiles from the crossing
    sq = wall_squares(end=25, xs=range(5, 31))
    loot = bline(0, 0.0, "goal", {"goal": "LootBuilding"}, _act("interact", x=5, y=8, kind="loot"))
    assert one(fight(), squares=sq)["across"] == 1                  # a Fight reads DISENGAGE_R: no way within it, a wall
    g = one(loot, squares=sq)
    assert (g["across"], g["walked_round"]) == (0, 1)               # a goal reads LEG_MAX with no width: the end is within it
    narrow = zf(-0.5, x=5.5, y=11.5)
    narrow["me"]["loadedWidth"] = 48                                # leg_max 16: the end lies beyond it
    g = one(loot, squares=sq, frames=[narrow])
    assert (g["across"], g["walked_round"]) == (1, 0)


def test_a_candidate_with_no_wall_position_or_target_is_unread_and_not_counted():
    assert one(aline(0, 0.0, {"fight": True, "target": 99}, _act("aim", targetId=99)))["unread"] == 1      # no such zombie
    ln = fight()
    del ln["wall"]
    g = one(ln)
    assert (g["unread"], g["across"]) == (1, 0)


def test_a_refusal_whose_rerun_routed_a_second_zombie_counts_once_as_a_route_and_beside_the_refusals():
    log = [aline(0, 0.0, {"fight": True, "target": 8, "marked": 7, "blocked_edge": ROUTE}, _act("walkTo", x=8.5, y=9.5), sent=True),
           aline(1, 1.0, {"fight": True, "target": 7, "marked": 7, "blocked_edge": EDGE}, None, sent=False)]
    g = grade(log=log)["blocked_edge"]
    assert g["sites"] == {"threat:route": 1, "threat:refuse": 1} and (g["refuse_marks"], g["refuse_routed"]) == (1, 1)
    assert g["refuse_targets"] == 1 and g["route_walks"] == {"threat:running": 1}


# ================================================================ Task 14 fix 1, the zombie across its edge out of the hold
def zm(i, x, y):
    return {"id": i, "x": x, "y": y, "dist": 3.0}


def out_fixture(flag=True):
    """Zombie 7 refused across the wall at (5, 10) N (the player at (5.5, 11.5), the zombie at y 8.5), then unreachable flees
    with and without it alone in the hold, the mode setting the radius, the mark released on the player's side and by time."""
    ttl = E.World.ZOMBIE_TTL_S
    mark = {"fight": True, "target": 7, "marked": 7, "blocked_edge": EDGE if flag else ROUTE}
    flee = lambda n, t, **kw: aline(n, t, {"flee": "unreachable"}, None, sent=False, **kw)
    log = [aline(0, 0.0, mark, None, sent=False),
           flee(1, 1.0),                                    # only 7 listed, across: left out of the hold
           flee(2, 2.0),                                    # 7 and 8, 8 on the player's side
           flee(3, 3.0),                                    # 7 and 9 (8 tiles off): mode None, radius DANGER_R: 9 beyond it
           flee(4, 4.0, mode="flee"),                       # the same with a threat mode: radius DISENGAGE_R, 9 inside
           flee(5, 5.0),                                    # 7 on the player's side: the mark is released
           flee(6, 6.0),                                    # 7 across again, no mark: not out
           flee(7, 7.0 + ttl + 5.0),                        # long after: 7 not listed
           aline(8, 8.0 + ttl + 5.0, {"fight": True}, None, sent=False)]
    fs = [zf(0.0, [zm(7, 5.5, 8.5)], x=5.5, y=11.5), zf(1.0, [zm(7, 5.5, 8.5)], x=5.5, y=11.5),
          zf(2.0, [zm(7, 5.5, 8.5), zm(8, 5.5, 12.5)], x=5.5, y=11.5), zf(3.0, [zm(7, 5.5, 8.5), zm(9, 5.5, 3.5)], x=5.5, y=11.5),
          zf(4.0, [zm(7, 5.5, 8.5), zm(9, 5.5, 3.5)], x=5.5, y=11.5), zf(5.0, [zm(7, 5.5, 12.5)], x=5.5, y=11.5),
          zf(6.0, [zm(7, 5.5, 8.5)], x=5.5, y=11.5), zf(7.0 + ttl + 5.0, [], x=5.5, y=11.5)]
    return grade(log=log, frames=fs)["edge_out"]


def test_the_edge_out_reading_counts_the_flees_with_a_mark_standing_and_the_ones_with_only_marked_zombies_held():
    g = out_fixture()
    assert g["read"] is True and g["marks"] == 1 and g["unreachable_flees"] == 7
    assert g["flees_with_mark"] == 4         # lines 1 to 4: the mark stands; released at line 5
    assert g["only_out"] == 2                # lines 1 (7 alone) and 3 (9 beyond the DANGER_R radius); line 2 holds 8, line 4 holds 9
    assert g["out_lines"] == 5               # lines 0 to 4 list a marked zombie across within the radius


def ttl_fixture():
    ttl = E.World.ZOMBIE_TTL_S
    mark = {"fight": True, "target": 7, "marked": 7, "blocked_edge": EDGE}
    flee = lambda n, t: aline(n, t, {"flee": "unreachable"}, None, sent=False)
    walls = [0.0, 1.0, float(ttl), ttl + 6.0, 2.0 * ttl + 7.0]
    log = [aline(0, walls[0], mark, None, sent=False)] + [flee(n, w) for n, w in enumerate(walls[1:], 1)]
    fs = [zf(w, [] if n == 1 else [zm(7, 5.5, 8.5)], x=5.5, y=11.5) for n, w in enumerate(walls)]
    return grade(log=log, frames=fs)["edge_out"]


def test_the_edge_out_mark_stands_while_the_zombie_is_listed_within_the_ttl_and_is_freed_after_it():
    # line 1 lists nobody (the mark stands, no zombie is held); line 2 re-lists 7 across, TTL seconds after line 0; line 3 six
    # seconds after line 2 (the listing renewed the mark's age); line 4 TTL + 1 s after line 3: the World dropped the zombie
    # and `_release_edges` its mark, so it is held again
    g = ttl_fixture()
    assert g["unreachable_flees"] == 4 and g["flees_with_mark"] == 3 and g["only_out"] == 2 and g["out_lines"] == 3


def test_the_edge_out_reading_is_zero_without_a_refusal_with_a_routed_mark_and_unread_without_a_log():
    g = out_fixture(flag=False)      # the `marked` beside a route marks a second zombie's edge: no mark is rebuilt from it
    assert (g["marks"], g["flees_with_mark"], g["only_out"], g["out_lines"]) == (0, 0, 0, 0) and g["unreachable_flees"] == 7
    assert grade(log=None)["edge_out"] == {"read": False}


# ================================================================ Task 14 fix 1, the stand's drag before health
def order_fixture(flag=True):
    """Drag ends with health under FLEE_HEALTH (the order's case) and health ends with attackers at DRAG_DOWN_N - 1 or more on
    the frame beside them (what the order forbids); `flag` False is the same log with healthy drags and few attackers."""
    def ln(n, left, health, extra=None):
        line = aline(n, float(n), dict({"flee": "doorway", "doorway_left": left}, **(extra or {})), None, sent=False)
        line["inputs"]["health"] = health
        return line
    h = 35.0 if flag else 80.0
    ex = {"doorway_drag": 2, "doorway_exit": {"end": "drag", "exit": "door"}}
    log = [ln(-1, "health", 35.0),      # before every frame: no attackers to read
           ln(0, "drag", h, ex), ln(1, "drag", h, {"doorway_drag": 2}), ln(2, "drag", 80.0, ex),
           ln(9, "drag", 40.0, ex),          # at FLEE_HEALTH exactly: not under it
           ln(3, "health", 35.0), ln(4, "health", 35.0), ln(5, "health", 35.0), ln(6, "wound", 20.0),
           aline(8, 8.0, {"flee": "doorway", "doorway_left": "drag", "doorway_drag": 2}, None, sent=False)]
    log[-1]["inputs"]["health"] = None
    fs = [zf(2.9, attackers=0), zf(3.0, attackers=2 if flag else 1), zf(4.0, attackers=1), zf(5.0, attackers=3 if flag else 0)]
    return grade(log=log, frames=fs)["stand_order"]


def test_the_stand_order_counts_the_drag_ends_under_flee_health_and_the_health_ends_that_were_drags():
    g = order_fixture()
    assert g["read"] is True and (g["drag_under_health"], g["with_exit"], g["health_ends"]) == (2, 1, 4)
    # the health ends at lines 3 (2 attackers) and 5 (3) are the ones the order forbids; line 4 reads 1 and the first line has
    # no frame; a drag end with no health reading (the last line) is no drag under health
    assert g["health_dragged"] == 2


def test_the_stand_order_reads_zero_on_a_log_where_no_drag_ends_under_health_and_no_health_end_had_the_count_and_unread_without_a_log():
    g = order_fixture(flag=False)
    assert g == {"read": True, "drag_under_health": 0, "with_exit": 0, "health_ends": 4, "health_dragged": 0}
    assert grade(log=None)["stand_order"] == {"read": False}


# ================================================================ P25-Y, the rip or the unwear under a dirty rag
def dirty_fixture(flag=True):
    log = []

    def care(why, sent=True, branch="care", n=None):
        n = len(log) if n is None else n
        log.append(bline(n, float(n), branch, why, _act("bandage", part=1), sent=sent))
    d = lambda extra: dict(extra, dirty=99) if flag else dict(extra)
    clean = lambda part, kind="rag": {"reason": "bleeding", "part": part, "item": 11, "kind": kind, "bleedingTime": 4.0}
    care(d({"reason": "no_rag", "part": 3, "item": 10}))                                 # 0: a rip, then its rag's bandage
    care(clean(3))
    care(d({"reason": "unwear", "part": 5, "item": 12, "loc": 4, "cover": 1}))           # 2: an unwear at a part bled 12 s
    care(clean(5, "dirty"))                                                              # a dirty rag's bandage: not a clean one
    care(d({"reason": "no_rag", "part": 7, "item": 14}), sent=False)                     # 4: unsent, the part not in the frame
    care({"stock": {"reason": "unwear"}, "dirty": 98}, sent=False)                       # the idle stock's line: left out
    care(d({"reason": "no_rag", "part": 2, "item": 16}), sent=False)                     # 6: unsent, bled exactly DIRTY_RAG_MIN
    care(clean(2))
    care(d({"reason": "no_rag", "part": 4, "item": 15}))                                 # 8: its bandage is past the rip's window
    care(clean(4), sent=False)                                                           # an unsent bandage: not a bandage
    log.append(aline(len(log), float(len(log)), {"fight": True}, None, sent=False,
                     care=dict({"reason": "no_rag", "part": 3, "dirty": 5})))            # another branch's care why: left out
    log.extend(aline(len(log) + i, float(len(log) + i), {"fight": True}, None, sent=False) for i in range(44))
    care(clean(4))                                                                       # 46 lines after the rip at 8
    care(d({"reason": "unwear", "part": 6, "item": 17, "loc": 4, "cover": 1}))
    log.extend(aline(len(log) + i, float(len(log) + i), {"fight": True}, None, sent=False) for i in range(49))
    care(clean(6, "bandage"))                                                            # 50 lines after the unwear
    care(d({"reason": "unwear", "part": 3, "item": 19, "loc": 4, "cover": 1}))
    log.extend(aline(len(log) + i, float(len(log) + i), {"fight": True}, None, sent=False) for i in range(59))
    care(clean(3))                                                                       # 60 lines after the unwear
    f = zf(-1.0)
    f["body"]["parts"] = [{"i": 2, "bleedingTime": 10.0}, {"i": 3, "bleedingTime": 4.0}, {"i": 4, "bleedingTime": 5.0},
                          {"i": 5, "bleedingTime": 12.0}, {"i": 6, "bleedingTime": 3.0}]
    return grade(log=log, frames=[f])["dirty_rip"]


def test_the_dirty_rip_counts_the_care_lines_with_the_dirty_why_the_bleed_over_the_limit_and_the_bandage_after():
    g = dirty_fixture()
    assert g["read"] is True and (g["lines"], g["rip"], g["unwear"], g["sent"]) == (7, 4, 3, 5)
    assert (g["bleed_over"], g["unread"]) == (1, 1)         # part 5 bled 12 s (past DIRTY_RAG_MIN 10); part 7 not in the frame
    # the sent rip at part 3 is followed by its rag's bandage; part 5's unwear by a dirty bandage (no); part 4's rip has an unsent
    # bandage next and the sent one 46 lines on, past the rip's window (UNWEAR_SEQ_LINES, 40); part 6's unwear has its bandage 50
    # lines on and part 3's 60, inside the unwear's window (twice that); the unsent rips at parts 7 and 2 count none
    assert g["bandaged"] == 3


def test_the_dirty_rip_reads_zero_without_the_why_and_unread_without_a_log():
    g = dirty_fixture(flag=False)
    assert (g["lines"], g["rip"], g["unwear"], g["sent"], g["bleed_over"], g["unread"], g["bandaged"]) == (0,) * 7
    assert grade(log=None)["dirty_rip"] == {"read": False}


# ================================================================ the report
def test_the_report_names_the_seven_rules_and_marks_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])
    r = g["report_lines"]
    assert g["grade"] == "grade_e13" and set(g) >= set(NEW)
    for t in ("stand drag end (P25-U) [reading]", "stand inside end (P25-V) [reading]", "stand way out (P25-W) [reading]",
              "blocked edges (P25-X) [reading]", "edge marks out of the hold (P25-X amended, EDGE_OUT_OF_HOLD) [reading]",
              "stand drag before health (Task 14 fix 1, STAND_DRAG_EARLY) [reading]", "dirty rag rip (P25-Y, DIRTY_RAG_RIP) [reading]"):
        assert any(l.startswith(t) for l in r), t
    assert sum("[inference" in l for l in r) >= 12
    be = next(l for l in r if l.startswith("blocked edges"))
    assert "must read 0 with the switch on" in be and "[inference off the map and the frames]" in be and "E15: 12" in be
    # the report says what must read 0 (no exemption explains it) and what is counted beside it (the exemptions, the walked round)
    assert "no exemption of the planner explains" in be and "explained by an exemption" in be and "walked round by design" in be
    assert "stance_route" in be and "nonzero is no failure" in be and "must read 0 where the edge read stands" in be
    we = next(l for l in r if l.startswith("stand way out"))
    assert "must read 0" in we and "until the frame reads outside the building [inference]" in we
    assert "per exit the most attackers" in we and "the fall of body health over it [inference]" in we
    eo = next(l for l in r if l.startswith("edge marks out"))
    assert "must read 0 with the switch on" in eo and "[inference off the marks the refusals took and the frames]" in eo
    assert not any(l.startswith("gate_e11 ") or l.startswith("gate_e12 ") for l in r)
    nolog = grade(log=None)["report_lines"]
    for t in ("stand drag end (P25-U): no decision log read", "stand inside end (P25-V): no decision log read",
              "stand way out (P25-W): no decision log read", "blocked edges (P25-X): no decision log read",
              "edge marks out of the hold (P25-X amended): no decision log read",
              "stand drag before health (Task 14 fix 1): no decision log read", "dirty rag rip (P25-Y): no decision log read"):
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
    ("e_stand_exit", lambda b: b.replace('r.get("branch") != "care"', "True"), lambda: exit_fixture()["max_attackers"] == [3, 4, 0], None),
    ("e_stand_exit", lambda b: b.replace("if reached is None and out_:", "if out_:"), lambda: exit_fixture()["outside_lines"] == [2, None, None]
     and _reached_first_holds(), None),
    ("e_stand_exit", lambda b: b.replace("reached - i", "reached"), lambda: exit_fixture()["outside_lines"] == [2, None, None], None),
    ("e_stand_exit", lambda b: b.replace("rows[reached if reached is not None else last]", "rows[min(len(rows), i + EXIT_WINDOW_LINES) - 1]"),
     lambda: exit_fixture()["max_attackers"] == [3, 4, 0], None),
    ("e_stand_exit", lambda b: b.replace("round(w1 - w0, 3)", "round(w0 - w1, 3)"), lambda: exit_fixture()["outside_s"][0] == 2.0, None),
    ("e_stand_exit", lambda b: b.replace("unread += 0 if readable else 1", "unread += 0"), lambda: exit_fixture(mapped=False)["unread"] == 3, None),
    ("e_stand_exit", lambda b: b.replace("readable = readable or out_ is not None", "readable = True"),
     lambda: exit_fixture(mapped=False)["unread"] == 3, None),
    ("e_stand_exit", lambda b: b.replace("bisect.bisect_right(walls, (_n(hi.get(\"wall\")) or 0.0) * 1000.0)",
                                         "bisect.bisect_right(walls, 1e15)"), lambda: exit_fixture()["max_attackers"] == [3, 4, 0], None),
    ("e_stand_exit", lambda b: b.replace("bisect.bisect_left(walls, (_n(ln.get(\"wall\")) or 0.0) * 1000.0)", "0"),
     lambda: exit_fixture()["max_attackers"] == [3, 4, 0] and _attackers_start_holds(), None),
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
    ("e_stand_exit", lambda b: b.replace('top = max(top, _n(_d(f.get("me")).get("attackers")) or 0)', 'top = min(top, _n(_d(f.get("me")).get("attackers")) or 0)'),
     lambda: exit_fixture()["max_attackers"] == [3, 4, 0], None),
    ("e_stand_exit", lambda b: b.replace("attackers.append(top)", "attackers.append(0)"), lambda: exit_fixture()["max_attackers"] == [3, 4, 0], None),
    ("e_stand_exit", lambda b: b.replace("round(max(h0 - min(hs), 0.0), 3)", "round(max(min(hs) - h0, 0.0), 3)"),
     lambda: exit_fixture()["health_drop"] == [20, 40, 0], None),
    ("e_stand_exit", lambda b: b.replace("round(max(h0 - min(hs), 0.0), 3)", "round(h0 - min(hs), 3) + 1"),
     lambda: exit_fixture()["health_drop"] == [20, 40, 0], None),
    ("e_stand_exit", lambda b: b.replace("h0 = hs[0] if h0 is None and hs else h0", "h0 = hs[0] if hs else h0"), lambda: _health_start_holds(), None),
    ("e_stand_exit", lambda b: b.replace("h0 = hs[0] if h0 is None and hs else h0", "pass"), lambda: _health_start_holds(), None),
    ("e_stand_exit", lambda b: b.replace('h = _n(_d(f.get("body")).get("health"))', "h = None"), lambda: exit_fixture()["health_drop"] == [20, 40, 0], None),
    ("e_stand_inside", lambda b: b.replace("            return {}\n", "            return self.map\n"), lambda: _map_view_holds(), "_MapView"),
    ("_widths", lambda b: b.replace("and v > 0]", "and v >= 0]"), lambda: _shell_holds(), None),
    ("_widths", lambda b: b.replace("not isinstance(v, bool) and ", ""), lambda: _shell_holds(), None),
    ("_widths", lambda b: b.replace("isinstance(v, int) and not", "True and not"), lambda: _shell_holds(), None),
    ("_width_at", lambda b: b.replace("if i >= 0 else None", "if True else None"), lambda: _shell_holds(), None),
    ("_width_at", lambda b: b.replace("bisect.bisect_right(ws, wall * 1000.0) - 1", "bisect.bisect_right(ws, wall * 1000.0)"), lambda: _shell_holds(), None),
    ("_shell_at", lambda b: b.replace("mv.at(wall)", "mv.at(None)"), lambda: _shell_holds(), None),
    ("_shell_at", lambda b: b.replace("_width_at(widths, wall)", "None"), lambda: _shell_holds(), None),
    ("_shell_at", lambda b: b.replace('{"x": me[0], "y": me[1], "z": me[2]}', '{"x": me[1], "y": me[0], "z": me[2]}'), lambda: _shell_holds(), None),
    ("_set", lambda b: b.replace("v is not None and v is not False", "bool(v)"), lambda: one(fight({"cornered": 0}))["exempt"] == {"cornered": 1}, None),
    ("_set", lambda b: b.replace("v is not None and v is not False", "v is not None"),
     lambda: one(fight({"pull": False, "stance": False}), squares=wall_squares(door=True))["across"] == 1, None),
    ("_pair", lambda b: b.replace("len(v) >= 2", "len(v) >= 3"),
     lambda: one(bline(0, 0.0, "goal", {"goal": "ExploreToward", "toward": [5, 8]}, _act("walkTo", x=5.5, y=11.0, gait="walk")))["across"] == 1, None),
    ("_pair", lambda b: b.replace("isinstance(v, list) and ", ""), lambda: _pair_holds(), None),
    ("_pair", lambda b: b.replace("_n(v[0]) + add, _n(v[1]) + add", "_n(v[0]), _n(v[1])"), lambda: _pair_holds(), None),
    ("_zombie_at", lambda b: b.replace('z.get("id") == zid', "True"), lambda: edge_fixture()["across"] == 8 and _aim_id_holds(), None),
    ("_zombie_at", lambda b: b.replace(' and _n(z.get("y")) is not None', ""), lambda: _zombie_xy_holds(), None),
    ("_across_dest", lambda b: b.replace('t == "aim"', 't == "xx"'), lambda: edge_fixture()["across_by"].get("fight_aim") == 1, None),
    ("_across_dest", lambda b: b.replace('_zombie_at(L, ln, L.why(ln).get("target")) or xy', "xy"),
     lambda: one(fight(a=_act("walkTo", x=5.5, y=11.0, gait="run")))["across"] == 1, None),
    ("_across_dest", lambda b: b.replace('_zombie_at(L, ln, L.why(ln).get("target")) or xy', '_zombie_at(L, ln, L.why(ln).get("target"))'),
     lambda: edge_fixture()["across"] == 8, None),
    ("_across_dest", lambda b: b.replace('br == "goal" and t == "walkTo"', 'br == "goal" and t == "xx"'),
     lambda: edge_fixture()["across_by"].get("goal_walk") == 1, None),
    ("_across_dest", lambda b: b.replace('_pair(gw.get("toward")) or xy', "xy"),
     lambda: one(bline(0, 0.0, "goal", {"goal": "ExploreToward", "toward": [5, 8]}, _act("walkTo", x=5.5, y=11.0, gait="walk")))["across"] == 1, None),
    ("_across_dest", lambda b: b.replace('_pair(gw.get("container"), 0.5) or xy', "xy"),
     lambda: one(bline(0, 0.0, "goal", {"goal": "LootBuilding", "container": [5, 8, 0, 0]}, _act("interact", x=5, y=11, kind="loot")))["across"] == 1, None),
    ("_across_dest", lambda b: b.replace('args.get("kind") == "loot"', 'args.get("kind") == "xx"'),
     lambda: edge_fixture()["across_by"].get("goal_loot") == 1, None),
    ("_across_dest", lambda b: b.replace('t == "fill"', 't == "xx"'), lambda: edge_fixture()["across_by"].get("need_fill") == 1, None),
    ("_across_dest", lambda b: b.replace('L.is_fight(ln) and t == "walkTo"', 't == "walkTo"'),
     lambda: edge_fixture()["across"] == 8 and _flee_walk_not_across(), None),
    ("_across_dest", lambda b: b.replace('ln.get("sent") is not True', "False"), lambda: _unsent_not_across(), None),
    ("_exemption", lambda b: b.replace('if read["via"] is None:', "if False:"),
     lambda: one(fight({"pull": [5.0, 5.0], "stance": True}))["across"] == 1, None),
    ("_exemption", lambda b: b.replace('"pull" if _set(w.get("pull"))', '"xx" if _set(w.get("pull"))'),
     lambda: one(fight({"pull": [5.0, 5.0], "stance": True, "leg": "pull"}), squares=wall_squares(door=True))["exempt"] == {"pull": 1}, None),
    ("_exemption", lambda b: b.replace('else "stance_route" if _set(w.get("stance")) else None', 'else "stance_route"'),
     lambda: one(fight(), squares=wall_squares(door=True))["across"] == 1, None),
    ("_exemption", lambda b: b.replace('else "stance_route" if _set(w.get("stance")) else None', "else None"),
     lambda: one(fight({"stance": True}), squares=wall_squares(door=True))["exempt"] == {"stance_route": 1}, None),
    ("_exemption", lambda b: b.replace('return None if g in EDGE_GOALS else "goal:%s" % g', "return None"),
     lambda: one(bline(0, 0.0, "goal", {"goal": "Stock"}, _act("interact", x=5, y=8, kind="loot")))["exempt"] == {"goal:Stock": 1}, None),
    ("_exemption", lambda b: b.replace('return None if g in EDGE_GOALS else "goal:%s" % g', 'return "goal:%s" % g'),
     lambda: one(bline(0, 0.0, "goal", {"goal": "LootBuilding"}, _act("interact", x=5, y=8, kind="loot")))["across"] == 1, None),
    ("_exemption", lambda b: b.replace('kind.startswith("goal")', 'kind.startswith("xx")'),
     lambda: one(bline(0, 0.0, "goal", {"goal": "Stock"}, _act("interact", x=5, y=8, kind="loot")))["exempt"] == {"goal:Stock": 1}, None),
    ("_exemption", lambda b: b.replace('kind.startswith("fight")', 'kind.startswith("xx")'),
     lambda: one(fight({"sheltered": True}))["exempt"] == {"door_fight": 1}, None),
    ("_edge_sites", lambda b: b.replace('(("cornered", "cornered"), ', "("), lambda: _exempt_key_holds("cornered", "cornered"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace('("corner", "cornered"), ', ""), lambda: _exempt_key_holds("corner", "cornered"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace('("sheltered", "door_fight"), ', ""), lambda: _exempt_key_holds("sheltered", "door_fight"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace('("finish", "finish"),\n', "\n"), lambda: _exempt_key_holds("finish", "finish"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace('("finish_first", "finish_first"), ', ""), lambda: _exempt_key_holds("finish_first", "finish_first"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace('("fence_wait", "fence_wait"))', ")"), lambda: _exempt_key_holds("fence_wait", "fence_wait"), "EDGE_EXEMPT_KEYS"),
    ("_edge_sites", lambda b: b.replace("issubclass(c, _gp._Legs)", "True"), lambda: E.EDGE_GOALS == ("ExploreToward", "LootBuilding", "Shelter"), "EDGE_GOALS"),
    ("_own_edge", lambda b: b.replace('br in ("threat", "goal", "need")', 'br in ("threat",)'), lambda: edge_fixture()["own"] == edge_fixture()["sites"], None),
    ("_own_edge", lambda b: b.replace('br == "need" and isinstance(w.get("fill"), dict)', "False"),
     lambda: edge_fixture()["own"] == edge_fixture()["sites"], None),
    ("_edge_sites", lambda b: b.replace('("goal", _bw(ln, "goal")),', ""), lambda: edge_fixture()["sites"].get("goal:drop") == 1, None),
    ("_edge_sites", lambda b: b.replace('("need", _d(_bw(ln, "need").get("fill")))', '("need", {})'),
     lambda: edge_fixture()["sites"].get("need:route") == 1, None),
    ("_edge_sites", lambda b: b.replace('("threat", _bw(ln, "threat")),', ""), lambda: edge_fixture()["sites"].get("threat:route") == 2, None),
    ("e_blocked_edge", lambda b: b.replace("kind is None or isinstance(b, dict)", "kind is None"), lambda: edge_fixture()["across"] == 8, None),
    ("e_blocked_edge", lambda b: b.replace("across[kind] = across.get(kind, 0) + 1", "pass"), lambda: edge_fixture()["across"] == 8, None),
    ("e_blocked_edge", lambda b: b.replace("exempt[why] = exempt.get(why, 0) + 1", "pass"),
     lambda: one(fight({"sheltered": True}))["exempt"] == {"door_fight": 1}, None),
    ("e_blocked_edge", lambda b: b.replace("if why is not None:", "if False:"), lambda: one(fight({"sheltered": True}))["across"] == 0, None),
    ("e_blocked_edge", lambda b: b.replace('DISENGAGE_R if kind.startswith("fight") else _gp.leg_max(sh)', "_gp.leg_max(sh)"), lambda: _reach_holds(), None),
    ("e_blocked_edge", lambda b: b.replace('DISENGAGE_R if kind.startswith("fight") else _gp.leg_max(sh)', "DISENGAGE_R"), lambda: _reach_holds(), None),
    ("e_blocked_edge", lambda b: b.replace("walked += 1 if _edges._crossed(sh, (me[0], me[1]), dest) is not None else 0", "walked += 0"),
     lambda: one(fight(), squares=wall_squares(end=6))["walked_round"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace("_edges._crossed(sh, (me[0], me[1]), dest) is not None else 0", "_edges._crossed(sh, (me[0], me[1]), dest) is None else 0"),
     lambda: one(fight(), squares=wall_squares(end=6))["walked_round"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace(' or _n(ln.get("wall")) is None:\n            unread += 1', ":\n            unread += 1"),
     lambda: _no_wall_unread_holds(), None),
    ("e_blocked_edge", lambda b: b.replace('doors.add(tuple(b["door"]))', "pass"), lambda: edge_fixture()["doors"] == [(8, 10)], None),
    ("e_blocked_edge", lambda b: b.replace('b.get("action") == "route" and isinstance', 'b.get("action") == "xx" and isinstance'),
     lambda: edge_fixture()["doors"] == [(8, 10)], None),
    ("e_blocked_edge", lambda b: b.replace('routed += 1 if w["blocked_edge"].get("action") == "route" else 0', "routed += 0"),
     lambda: _rerun_routed_holds(), None),
    ("e_blocked_edge", lambda b: b.replace('marks += 0 if w["blocked_edge"].get("action") == "route" else 1', "marks += 0"),
     lambda: edge_fixture()["refuse_marks"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('marks += 0 if w["blocked_edge"].get("action") == "route" else 1', "marks += 1"),
     lambda: _rerun_routed_holds(), None),
    ("e_blocked_edge", lambda b: b.replace('targets.add(repr(w["marked"]))', "pass"), lambda: edge_fixture()["refuse_targets"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('"done" if row.get("state") == "done" else str(row.get("reason"))', '"done"'),
     lambda: edge_fixture()["route_walks"] == ROUTE_WALKS, None),
    ("e_blocked_edge", lambda b: b.replace('b.get("action") == "route" and _sent(ln, "walkTo")', "False"),
     lambda: edge_fixture()["route_walks"] == ROUTE_WALKS, None),
    ("e_blocked_edge", lambda b: b.replace('k = "%s:%s" % (ln.get("branch"), end)', "k = end"),
     lambda: edge_fixture()["route_walks"] == ROUTE_WALKS, None),
    ("e_blocked_edge", lambda b: b.replace('g.get("reason") == "blocked edge"', 'g.get("reason") == "shunned"'),
     lambda: edge_fixture()["goal_types"] == {"LootBuilding": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('g.get("state") == "failed" and ', ""), lambda: edge_fixture()["goal_ends"] == 1 and _goal_state_holds(), None),
    ("e_blocked_edge", lambda b: b.replace("in ended else 0", "in ended or True else 0"), lambda: edge_fixture()["cooled_refused"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('r.get("args")], sort_keys=True, default=str) in ended', 'None], sort_keys=True, default=str) in ended'),
     lambda: edge_fixture()["cooled_refused"] == 1, None),
    ("e_blocked_edge", lambda b: b.replace('row.get("reason") == "stuck"', 'row.get("reason") == "xx"'), lambda: edge_fixture()["cycles"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace('row.get("state") == "failed" and ', ""), lambda: edge_fixture()["cycles"] == 2 and _done_reposition_holds(), None),
    ("e_blocked_edge", lambda b: b.replace("if t in pending:", "if True:"), lambda: edge_fixture()["cycle_marks"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("(1 if pending.pop(t) else 0)", "(0 if pending.pop(t) else 1)"), lambda: edge_fixture()["cycle_across"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("(1 if pending.pop(t) else 0)", "(pending.pop(t) and 0)"), lambda: edge_fixture()["cycle_across"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("to) is not None\n", "to) is None\n"), lambda: edge_fixture()["cycle_across"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace('"cycles_across": max(cycle_x.values(), default=0)', '"cycles_across": 0'),
     lambda: edge_fixture()["cycles_across"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace('not isinstance(w.get("blocked_edge"), dict):\n            t = repr', "True:\n            t = repr"),
     lambda: edge_fixture()["old_marks"] == {"9": 2, "10": 1, "11": 1}, None),
    ("e_blocked_edge", lambda b: b.replace('w.get("reposition") is not None and zid is not None', "zid is not None"),
     lambda: edge_fixture()["cycle_marks"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("max(cycle.items(), key=lambda p: (p[1], p[0]))", "min(cycle.items(), key=lambda p: (p[1], p[0]))"),
     lambda: edge_fixture()["cycles"] == 2 and _two_targets_cycle(), None),
    ("e_blocked_edge", lambda b: b.replace("cycle[t] = cycle.get(t, 0) + 1", "cycle[t] = 1"), lambda: edge_fixture()["cycles"] == 2, None),
    ("e_blocked_edge", lambda b: b.replace("unread += 1", "unread += 0"), lambda: _unread_holds(), None),
    ("e_edge_out", lambda b: b.replace('be.get("action") == "refuse"', 'be.get("action") != "refuse"'), lambda: out_fixture()["marks"] == 1, None),
    ("e_edge_out", lambda b: b.replace('be.get("action") == "refuse"', "True"), lambda: out_fixture(flag=False)["marks"] == 0, None),
    ("e_edge_out", lambda b: b.replace('len(be["edge"]) == 3', 'len(be["edge"]) == 4'), lambda: out_fixture()["marks"] == 1, None),
    ("e_edge_out", lambda b: b.replace('be["edge"][2])', '"W")'), lambda: out_fixture()["flees_with_mark"] == 4, None),
    ("e_edge_out", lambda b: b.replace("                    del marks[zid]\n", "                    pass\n"), lambda: out_fixture()["flees_with_mark"] == 4, None),
    ("e_edge_out", lambda b: b.replace("wall - seen[zid] > World.ZOMBIE_TTL_S", "False"), lambda: ttl_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace("wall - seen[zid] > World.ZOMBIE_TTL_S", "wall - seen[zid] > 0"), lambda: ttl_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace("                seen[zid] = wall\n                if me", "                if me"), lambda: ttl_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace('DISENGAGE_R if _d(ln.get("inputs")).get("mode") is not None else DANGER_R', "DANGER_R"),
     lambda: out_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace('DISENGAGE_R if _d(ln.get("inputs")).get("mode") is not None else DANGER_R', "DISENGAGE_R"),
     lambda: out_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace("only_out += 1 if inr and all(", "only_out += 1 if all("), lambda: out_fixture()["only_out"] == 2, None),
    ("e_edge_out", lambda b: b.replace("with_mark += 1 if marks else 0", "with_mark += 1"), lambda: out_fixture()["flees_with_mark"] == 4, None),
    ("e_edge_out", lambda b: b.replace("out_lines += 1 if any(zid in marks for zid in inr) else 0", "out_lines += 0"), lambda: out_fixture()["out_lines"] == 5, None),
    ("e_edge_out", lambda b: b.replace('w.get("flee") == "unreachable"', 'w.get("flee") != "unreachable"'), lambda: out_fixture()["unreachable_flees"] == 7, None),
    ("e_edge_out", lambda b: b.replace('taken.add(repr(w["marked"]))', "pass"), lambda: out_fixture()["marks"] == 1, None),
    ("e_stand_order", lambda b: b.replace("h < FLEE_HEALTH", "h <= FLEE_HEALTH"), lambda: order_fixture()["drag_under_health"] == 2, None),
    ("e_stand_order", lambda b: b.replace("h is not None and h < FLEE_HEALTH", "h < FLEE_HEALTH"), lambda: order_fixture()["drag_under_health"] == 2, None),
    ("e_stand_order", lambda b: b.replace('w.get("doorway_left") == "drag" and', 'w.get("doorway_left") != "health" and'),
     lambda: order_fixture()["drag_under_health"] == 2, None),
    ("e_stand_order", lambda b: b.replace('with_exit += 1 if isinstance(w.get("doorway_exit"), dict) else 0', "with_exit += 1"),
     lambda: order_fixture()["with_exit"] == 1, None),
    ("e_stand_order", lambda b: b.replace('elif w.get("doorway_left") == "health":', 'elif w.get("doorway_left") == "wound":'),
     lambda: order_fixture()["health_ends"] == 4, None),
    ("e_stand_order", lambda b: b.replace("att >= DRAG_DOWN_N - 1", "att > DRAG_DOWN_N - 1"), lambda: order_fixture()["health_dragged"] == 2, None),
    ("e_stand_order", lambda b: b.replace("att >= DRAG_DOWN_N - 1", "att >= DRAG_DOWN_N"), lambda: order_fixture()["health_dragged"] == 2, None),
    ("e_stand_order", lambda b: b.replace("att is not None and ", ""), lambda: order_fixture()["health_dragged"] == 2, None),
    ("e_dirty_rip", lambda b: b.replace('and "stock" not in _bw(ln, "care")', ""), lambda: dirty_fixture()["lines"] == 7, None),
    ("e_dirty_rip", lambda b: b.replace('if ln.get("branch") == "care"', "if True"), lambda: dirty_fixture()["lines"] == 7, None),
    ("e_dirty_rip", lambda b: b.replace('"dirty" in s[2]', '"item" in s[2]'), lambda: dirty_fixture()["lines"] == 7, None),
    ("e_dirty_rip", lambda b: b.replace("bt > DIRTY_RAG_MIN", "bt >= DIRTY_RAG_MIN"), lambda: dirty_fixture()["bleed_over"] == 1, None),
    ("e_dirty_rip", lambda b: b.replace("unread += 1 if bt is None else 0", "unread += 0"), lambda: dirty_fixture()["unread"] == 1, None),
    ("e_dirty_rip", lambda b: b.replace("over += 1 if bt is not None and bt > DIRTY_RAG_MIN else 0", "over += 0"), lambda: dirty_fixture()["bleed_over"] == 1, None),
    ("e_dirty_rip", lambda b: b.replace('DIRTY_SEQ_LINES if c.get("reason") == "unwear" else DIRTY_SEQ_LINES // 2',
                                        'DIRTY_SEQ_LINES // 2 if c.get("reason") == "unwear" else DIRTY_SEQ_LINES'),
     lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace("DIRTY_SEQ_LINES // 2", "DIRTY_SEQ_LINES"), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('k.get("kind") in ("bandage", "rag")', "True"), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('k.get("part") == c.get("part")', "True"), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('k.get("reason") == "bleeding"', 'k.get("reason") == "xx"'), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('ln.get("sent") is True and any(', "any("), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('s.get("sent") is True and k.get', "k.get"), lambda: dirty_fixture()["bandaged"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('s[2].get("reason") == "no_rag"', 's[2].get("reason") == "xx"'), lambda: dirty_fixture()["rip"] == 4, None),
    ("e_dirty_rip", lambda b: b.replace('s[2].get("reason") == "unwear"', 's[2].get("reason") == "xx"'), lambda: dirty_fixture()["unwear"] == 3, None),
    ("e_dirty_rip", lambda b: b.replace('s[1].get("sent") is True', "True"), lambda: dirty_fixture()["sent"] == 5, None),
]


ROUTE_WALKS = {"threat:done": 1, "threat:stuck": 1, "goal:done": 1, "need:no path": 1}


def _pair_holds():
    return E._pair((1, 2)) is None and E._pair([1, 2]) == (1, 2) and E._pair([1, 2], 0.5) == (1.5, 2.5) and E._pair([1]) is None


def _zombie_xy_holds():
    """A zombie the frame lists without a y is no position: the aim reads unread."""
    log = [aline(0, 0.0, {"fight": True, "target": 7}, _act("aim", targetId=7))]
    fs = [zf(0.0, [{"id": 7, "x": 5.5, "y": None, "dist": 3.0}], x=5.5, y=11.5), mline(-1, wall_squares())]
    return grade(log=log, frames=fs)["blocked_edge"]["unread"] == 1


def _exempt_key_holds(key, name):
    g = one(fight({key: True}))
    return (g["across"], g["exempt"]) == (0, {name: 1})


def _reach_holds():
    """A run ending 20 tiles from the crossing is no way within a Fight's DISENGAGE_R (a wall: unexplained) and one within the
    goal legs' LEG_MAX (walked round)."""
    sq = wall_squares(end=25, xs=range(5, 31))
    loot = bline(0, 0.0, "goal", {"goal": "LootBuilding"}, _act("interact", x=5, y=8, kind="loot"))
    a, b = one(fight(), squares=sq), one(loot, squares=sq)
    return a["across"] == 1 and (b["across"], b["walked_round"]) == (0, 1)


def _no_wall_unread_holds():
    """A line with no wall but a position and a target is unread, not read against a map of no wall."""
    ln = bline(0, 0.0, "goal", {"goal": "LootBuilding"}, _act("interact", x=5, y=8, kind="loot"))
    ln["inputs"].update(x=5.5, y=11.5)
    del ln["wall"]
    g = one(ln)
    return g["unread"] == 1 and g["across"] == 0


def _rerun_routed_holds():
    log = [aline(0, 0.0, {"fight": True, "target": 8, "marked": 7, "blocked_edge": ROUTE}, _act("walkTo", x=8.5, y=9.5), sent=True),
           aline(1, 1.0, {"fight": True, "target": 7, "marked": 7, "blocked_edge": EDGE}, None, sent=False)]
    g = grade(log=log)["blocked_edge"]
    return (g["refuse_marks"], g["refuse_routed"]) == (1, 1)


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
    return grade(log=log, frames=f)["stand_exit"]["max_attackers"] == [1]


def _map_view_holds():
    mv = E._MapView([mline(1, [sqr(1, 1, room="a"), sqr(2, 2)]), mline(5, [sqr(1, 1)])])
    ok = mv.at(T0 + 0) == {} and mv.at(T0 + 1)[(1, 1, 0)]["room"] == "a"
    ok = ok and mv.at(T0 + 6)[(1, 1, 0)]["room"] is None
    ok = ok and mv.at(T0 + 2)[(1, 1, 0)]["room"] == "a"
    return ok and mv.at(None) == {}


def _inputs_pos_holds():
    """A line's own inputs x, y win over the frame's me."""
    log = [aline(0, 0.0, {"fight": True, "target": 1}, _act("aim", targetId=1))]
    log[0]["inputs"].update(x=5.5, y=11.5)
    f = [zf(0, [{"id": 1, "x": 5.5, "y": 8.5, "dist": 3.0}], x=9.5, y=8.0)]       # the frame's me stands elsewhere, beside the zombie
    wall = [mline(-1, [sqr(5, y, **({"blockN": True} if y == 10 else {})) for y in range(7, 13)])]
    return grade(log=log, frames=f + wall)["blocked_edge"]["across"] == 1


def _health_start_holds():
    """The health fall starts at the frame at the tick, else at the first frame of the window."""
    ex = {"flee": "doorway", "doorway_left": "wound", "doorway_exit": {"end": "wound", "exit": "door"}}
    log = lambda: [aline(0, 1.5, ex, None, sent=False), aline(1, 3.0, {"flee": "doorway"}, None, sent=False)]
    mid = [zf(1.0), zf(2.0), zf(3.0)]
    for f, h in zip(mid, (100.0, 70.0, 80.0)):
        f["body"]["health"] = h
    first = grade(log=log(), frames=mid)["stand_exit"]["health_drop"] == [30.0]        # the frame before the tick reads 100
    late = [zf(2.0), zf(3.0)]
    for f, h in zip(late, (70.0, 50.0)):
        f["body"]["health"] = h
    return first and grade(log=log(), frames=late)["stand_exit"]["health_drop"] == [20.0]


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
