"""base/grades/e15.py (Plan 26 Task 7b), offline: `grade_e15` and its three readings of survival iteration 18 (the
window inner square P26-I, the window stall and the interrupted end P26-J and P26-M, the stand's crowd end P26-K and
P26-K2), each on a fabricated log where it counts and a clean one where it reads zero, a mutant per reading, every
`grade_e14` key unchanged under `grade_e15` on test_gates_e13's fixtures, and the real checks on E17
(`e_day_17-20261102-180459`) and E16 (`e_day_16-20261102-125450`): every older key equal to the committed
`e_grade.txt`'s and the new readings as the grade reads them there."""
import json
import os

import pytest

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e15 as G
from agent.drivers import e_grade_14 as EG14
from . import test_grades_e14 as T14
from .test_gates_e7 import aline, zf
from .test_gates_e13 import _act, mline, sqr
from .test_grades_e14 import actl, row

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E16 = os.path.join(TESTING, "artifacts", "e_day_16-20261102-125450")
E17 = os.path.join(TESTING, "artifacts", "e_day_17-20261102-180459")
NEW = ("window_inner", "window_stall", "stand_crowd")


def grade(actions=(), results=(), log=None, frames=(), goals=()):
    return G.grade_e15(T14.artifact(actions, results, goals), decision_lines=log, lines=list(frames))


# ================================================================ P26-I, the window inner square
def inner_fixture(solid_trans=True, solid=False, barricaded=False, mapped=True, framed=True):
    """A shed (building 2, room squares x 3..6 on y 0) with a window on the west edge of (3, 0) whose outside square
    (2, 0) is open ground; the window square itself is the inside one (`World.window_way`), reading `solidTrans` (a
    counter). The player stands on (4, 0). Four trapped lines (a `many` hold's `trapped`, a `doorway` stand exit
    reading `trapped`), one `many` line that is no hold, a `doorway` line whose exit is a window, a `fight` and a
    window step naming the counter's window (an older build's: `offered`)."""
    trapped = {"flee": "many", "trapped": 1, "shelter": None, "refused": []}
    stand = {"flee": "doorway", "doorway_left": "inside", "doorway_exit": {"end": "inside", "exit": "trapped"}}
    log = [aline(0, 1.0, trapped, None, sent=False),
           aline(1, 2.0, stand, None, sent=False),
           aline(2, 3.0, {"flee": "many", "shelter": 2, "refused": []}, None, sent=False),
           aline(3, 4.0, {"flee": "doorway", "doorway_exit": {"end": "inside", "exit": "window"}}, None, sent=False),
           aline(4, 5.0, {"fight": True, "target": 1}, None, sent=False),
           aline(5, 6.0, trapped, None, sent=False),
           aline(6, 7.0, {"flee": "doorway", "exit": 2, "outer": [2, 0, 0], "window": [3, 0], "smash": True,
                          "step": "window", "shelter": None, "refused": []}, _act("window", x=3, y=0))]
    squares = [sqr(2, 0)]
    squares.append(sqr(3, 0, room="shed", building=2, edgeW=True, blockW=True, solid=solid, solidTrans=solid_trans,
                       window={"open": False, "locked": True, "barricaded": barricaded}))
    squares += [sqr(x, 0, room="shed", building=2) for x in range(4, 7)] + [sqr(x, 0) for x in range(7, 9)]
    frames = [zf(t, x=4.5, y=0.5) for t in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5)] if framed else []
    maps = [mline(-1, squares)] if mapped else []
    return grade(log=log, frames=frames + maps)["window_inner"]


def test_the_window_inner_counts_the_trapped_lines_while_a_window_of_the_players_building_has_an_unstandable_inner():
    g = inner_fixture()
    assert g["read"] is True and g["lines"] == 3 and g["windows"] == [(3, 0)] and g["unread"] == 0
    assert g["offered"] == 1       # the window step naming the counter's window


def test_a_solid_inner_square_counts_too_and_a_standable_or_barricaded_window_or_a_missing_map_does_not():
    assert inner_fixture(solid_trans=False, solid=True)["lines"] == 3
    assert (inner_fixture(solid_trans=False)["lines"], inner_fixture(solid_trans=False)["offered"]) == (0, 0)
    assert (inner_fixture(barricaded=True)["lines"], inner_fixture(barricaded=True)["offered"]) == (0, 0)
    g = inner_fixture(mapped=False)
    assert (g["lines"], g["offered"], g["windows"], g["unread"]) == (0, 0, [], 3)
    g = inner_fixture(framed=False)
    assert (g["lines"], g["offered"], g["unread"]) == (0, 0, 3)


def test_the_window_inner_reads_zero_without_a_trapped_line_and_unread_without_a_log():
    log = [aline(0, 1.0, {"flee": "many", "shelter": 2, "refused": []}, None, sent=False)]
    assert grade(log=log)["window_inner"] == {"read": True, "lines": 0, "offered": 0, "windows": [], "unread": 0}
    assert grade(log=None)["window_inner"] == {"read": False}


# ================================================================ P26-J and P26-M, the window stall and the interrupt
def stall_fixture(flag=True):
    """Two window runs after the same hold, a climb dropped for its stall (w1 still running when the refused set grew
    at the trapped hold, ended 5.0 against the line at 3.0) and a climb that failed `locked` at 11.5 before the hold's
    line at 12.0 (a refusal, no stall); then w3 interrupted at 21.0, sent again at 21.5 (w4) and interrupted again at
    22.5 (the exit refused), and a goal's window interrupted (not counted)."""
    win = lambda outer, win_, refused: {"flee": "doorway", "exit": 7, "outer": outer, "window": win_, "smash": False,
                                        "step": "window", "shelter": None, "refused": refused}
    hold = lambda refused: {"flee": "many", "trapped": 1, "shelter": None, "refused": refused}
    w1 = [[2, 0, 0]]
    w2 = [[2, 0, 0], [2, 5, 0]]
    log = [aline(0, 1.0, win([2, 0, 0], [3, 0], []), _act("window", x=3, y=0)),
           aline(1, 2.0, win([2, 0, 0], [3, 0], []), None, sent=False),
           aline(2, 3.0, hold(w1 if flag else []), None, sent=False),
           aline(3, 10.0, win([2, 5, 0], [3, 5], w1), _act("window", x=3, y=5)),
           aline(4, 11.0, win([2, 5, 0], [3, 5], w1), None, sent=False),
           aline(5, 12.0, hold(w2), None, sent=False)]
    acts = [row("w1", "window", 1.0, state="failed", reason="superseded", ended=5.0, x=3, y=0, smash=False),
            row("w2", "window", 10.0, state="rejected", reason="locked", ended=11.5, x=3, y=5, smash=False),
            row("w3", "window", 20.0, state="failed", reason="interrupted", ended=21.0, x=3, y=9, smash=False),
            row("w4", "window", 21.5, state="failed", reason="interrupted", ended=22.5, x=3, y=9, smash=False),
            row("w5", "window", 30.0, state="failed", reason="interrupted", ended=31.0, branch="goal", x=3, y=9)]
    lines = [actl("w3", "window", "failed", 21.0, reason="interrupted"), actl("w4", "window", "failed", 22.5,
                                                                              reason="interrupted")]
    return grade(acts, [], log, lines)["window_stall"]


def test_the_window_stall_counts_the_climb_still_running_when_the_refused_set_grew_and_the_interrupted_ends():
    g = stall_fixture()
    assert g["read"] is True and g["stalled"] == 1 and g["windows"] == [(3, 0)]
    assert (g["interrupted"], g["resent"], g["refused_after_interrupt"]) == (2, 1, 1)


def test_a_refused_set_that_did_not_grow_is_no_stall_and_a_log_without_the_window_acts_reads_zero():
    g = stall_fixture(flag=False)
    assert (g["stalled"], g["windows"]) == (0, [])
    assert (g["interrupted"], g["resent"], g["refused_after_interrupt"]) == (2, 1, 1)
    clean = grade(log=[aline(0, 1.0, {"fight": True}, None, sent=False)])["window_stall"]
    assert clean == {"read": True, "stalled": 0, "windows": [], "interrupted": 0, "resent": 0,
                     "refused_after_interrupt": 0}
    assert grade(log=None)["window_stall"] == {"read": False}


def test_an_interrupted_end_sent_again_late_or_at_another_square_is_no_resend():
    acts = [row("w3", "window", 20.0, state="failed", reason="interrupted", ended=21.0, x=3, y=9, smash=False),
            row("w4", "window", 21.0 + G.RESEND_S + 1.0, ended=40.0, x=3, y=9, smash=False),
            row("w5", "window", 50.0, state="failed", reason="interrupted", ended=51.0, x=4, y=9, smash=False),
            row("w6", "window", 51.5, ended=53.0, x=3, y=9, smash=False)]
    g = grade(acts, [], [aline(0, 1.0, {"fight": True}, None, sent=False)])["window_stall"]
    assert (g["interrupted"], g["resent"], g["refused_after_interrupt"]) == (2, 0, 2)


# ================================================================ P26-K and P26-K2, the stand's crowd end
def crowd_fixture(flag=True):
    """The shed of `inner_fixture` (room squares x 3..6, outside beyond) with the player on (4, 0): three stand ends
    `crowd` (n 4 and exit close, with the close sent on the tick; n 5 and exit window; n 4 and exit close, close sent),
    one `inside` end that is no crowd. A zombie stands on a room square 3 s after the first close and outside after the
    last."""
    close = _act("interact", x=3, y=0, kind="close")
    end = lambda n, how, **kw: dict({"flee": "doorway", "doorway_left": "crowd", "doorway_crowd": {"n": n},
                                     "doorway_exit": {"end": "crowd", "exit": how}}, **kw)
    left = "crowd" if flag else "quiet"
    log = [aline(0, 0.0, dict(end(4, "close"), doorway_left=left), close),
           aline(1, 50.0, dict(end(5, "window"), doorway_left=left), _act("walkTo", x=2.5, y=0.5)),
           aline(2, 100.0, dict(end(4, "close"), doorway_left=left), close),
           aline(3, 150.0, {"flee": "doorway", "doorway_left": "inside",
                            "doorway_exit": {"end": "inside", "exit": "window"}}, None, sent=False)]
    squares = [sqr(x, 0, room="shed", building=2) for x in range(3, 7)] + [sqr(x, 0) for x in range(7, 12)]
    frames = [zf(t, x=4.5, y=0.5, zombies=[{"id": 1, "x": zx + 0.5, "y": 0.5}]) for t, zx in
              ((-0.5, 9), (3.0, 5), (50.5, 9), (99.5, 9), (103.0, 9), (125.0, 5), (150.5, 9))]
    return grade(log=log, frames=frames + [mline(-1, squares)])["stand_crowd"]


def test_the_stand_crowd_counts_the_crowd_ends_their_sizes_their_exits_the_closes_and_the_zombies_inside_after():
    g = crowd_fixture()
    assert g["read"] is True and g["lines"] == 3 and g["n_hist"] == {"4": 2, "5": 1}
    assert g["by_exit"] == {"close": 2, "window": 1} and g["closes"] == 2
    # the first close is followed by a zombie on a room square 3 s on; the second by one outside at 3 s and, 25 s on
    # (within CLOSE_INSIDE_S), one on a room square
    assert g["inside_after_close"] == 2 and g["unread"] == 0


def test_a_zombie_inside_only_after_the_window_is_not_counted_and_a_log_without_a_crowd_end_reads_zero():
    zero = {"read": True, "lines": 0, "n_hist": {}, "by_exit": {}, "closes": 0, "inside_after_close": 0, "unread": 0}
    assert crowd_fixture(flag=False) == zero
    assert grade(log=None)["stand_crowd"] == {"read": False}


def test_the_stand_crowd_reads_unread_when_the_close_has_no_mapped_frame_after_it():
    close = _act("interact", x=3, y=0, kind="close")
    log = [aline(0, 0.0, {"flee": "doorway", "doorway_left": "crowd", "doorway_crowd": {"n": 4},
                          "doorway_exit": {"end": "crowd", "exit": "close"}}, close)]
    g = grade(log=log, frames=[zf(-0.5, x=4.5, y=0.5)])["stand_crowd"]
    assert (g["lines"], g["closes"], g["inside_after_close"], g["unread"]) == (1, 1, 0, 1)


# ================================================================ grade_e15 over grade_e14
@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e15_reads_every_grade_e14_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e14 = G14.grade_e14(a, decision_lines=seen["log"], lines=seen["frames"])
    e15 = G.grade_e15(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e15["grade"] == "grade_e15" and all(e15[k]["read"] is True for k in NEW)
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e14.items() if k not in skip} == {k: v for k, v in e15.items() if k not in skip}
    assert e15["report_lines"][:-len(NEW)] == e14["report_lines"]


def test_grade_e15_without_a_decision_log_reads_the_new_keys_unread():
    g = grade(log=None)
    assert all(g[k] == {"read": False} for k in NEW) and g["grade"] == "grade_e15"


def test_report_lines_e15_names_gate_e15_then_one_line_per_rule_marked_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True}, None, sent=False)])
    tail = g["report_lines"][-len(NEW):]
    for line, tag in zip(tail, ("P26-I", "P26-J", "P26-K")):
        assert ("(%s" % tag) in line and len(line) > 0
    assert "[inference]" in tail[0] and "[inference]" in tail[1] and "[reading]" in tail[2]
    off = grade(log=None)["report_lines"][-len(NEW):]
    assert all("no decision log read" in line for line in off)
    renamed = G.report_lines_e15(dict(g, gate={"pass": True}))
    assert not any(line.startswith(("gate_e13 ", "gate_e14 ")) for line in renamed)
    assert G.gate_e15([]) == E.gate_e13([])


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/e15.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "e15_mutant"}
    exec(compile(src[:start] + new + src[end:], "e15_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    ("_unstood", lambda b: b.replace('or inner.get("solidTrans")', ""),
     lambda: inner_fixture()["lines"] == 3),
    ("_unstood", lambda b: b.replace('w.get("barricaded") is True', "False"),
     lambda: inner_fixture(barricaded=True)["lines"] == 0),
    ("e_window_inner", lambda b: b.replace("if step and (win[0], win[1]) in found:", "if step:"),
     lambda: inner_fixture(solid_trans=False)["offered"] == 0),
    ("_held", lambda b: b.replace('"trapped" in w or ', ""),
     lambda: inner_fixture()["lines"] == 3),
    ("_held", lambda b: b.replace('w.get("flee") in HELD_FLEES and ', ""),
     lambda: inner_fixture()["lines"] == 3 and _a_fight_line_is_no_hold()),
    ("_stalled", lambda b: b.replace("if outer in now:", "if outer not in now:"),
     lambda: stall_fixture()["stalled"] == 1),
    ("_stalled", lambda b: b.replace("ended_ms > wall_ms", "True"),
     lambda: stall_fixture()["stalled"] == 1),
    ("e_window_stall", lambda b: b.replace('reason != "interrupted"', "reason is None"),
     lambda: stall_fixture()["interrupted"] == 2 and _a_timeout_is_no_interrupt()),
    ("e_window_stall", lambda b: b.replace("<= RESEND_S", "<= 1000.0"),
     lambda: _an_interrupted_end_sent_again_late_is_no_resend()),
    ("e_stand_crowd", lambda b: b.replace('w.get("doorway_left") != "crowd"', 'w.get("doorway_left") is None'),
     lambda: crowd_fixture()["lines"] == 3),
    ("e_stand_crowd", lambda b: b.replace('== "close"', '== "open"'),
     lambda: crowd_fixture()["closes"] == 2),
    ("_inside_after", lambda b: b.replace("(wall + CLOSE_INSIDE_S)", "(wall + 1.0)"),
     lambda: crowd_fixture()["inside_after_close"] == 2),
]


def _a_fight_line_is_no_hold():
    """A `fight` why (no `flee` key) carrying `trapped` is no hold: the Flee writes it on its own lines only."""
    log = [aline(0, 1.0, {"fight": True, "trapped": 1}, None, sent=False)]
    frames = [zf(0.5, x=4.5, y=0.5)]
    squares = [sqr(3, 0, room="shed", building=2, edgeW=True, solidTrans=True,
                   window={"open": False, "locked": True, "barricaded": False}), sqr(2, 0),
               sqr(4, 0, room="shed", building=2)]
    return grade(log=log, frames=frames + [mline(-1, squares)])["window_inner"]["lines"] == 0


def _a_timeout_is_no_interrupt():
    acts = [row("w3", "window", 20.0, state="failed", reason="timeout", ended=21.0, x=3, y=9, smash=False)]
    return grade(acts, [], [aline(0, 1.0, {"fight": True}, None, sent=False)])["window_stall"]["interrupted"] == 0


def _an_interrupted_end_sent_again_late_is_no_resend():
    acts = [row("w3", "window", 20.0, state="failed", reason="interrupted", ended=21.0, x=3, y=9, smash=False),
            row("w4", "window", 21.0 + G.RESEND_S + 1.0, ended=40.0, x=3, y=9, smash=False)]
    return grade(acts, [], [aline(0, 1.0, {"fight": True}, None, sent=False)])["window_stall"]["resent"] == 0


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


# ================================================================ the real checks: E17 and E16
def _committed(path):
    text = open(os.path.join(path, "e_grade.txt"), encoding="utf-8").read()
    return json.loads(text[text.index("\n{\n"):])


def _real(path, name):
    p = os.path.join(path, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % path)
    g = G.grade_e15(EG14.load(p), None, EG14.load_log(p), state_dir=EG14._dir(p))
    return g, json.loads(json.dumps(EG14.finite(g), sort_keys=True, allow_nan=False))


def test_grade_e15_on_e17_keeps_every_grade_e14_key_as_the_committed_e_grade_txt_and_reads_the_new_keys():
    g, mine = _real(E17, "e_day_17.json")
    assert g["grade"] == "grade_e15" and all(g[k]["read"] is True for k in NEW)
    committed = _committed(E17)
    for k in NEW:
        mine.pop(k)
    mine["grade"] = "grade_e14"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed
    # E17 ran iteration 17: its stand's window way out named the kitchen counter's window (10720, 10634) on all 32
    # window-step lines (`offered`, the reading P26-I makes zero); no line read the trapped hold, so `lines` is 0; no
    # stall read, no interrupted end, no crowd end; its one window climb failed `dead`
    assert g["window_inner"] == {"read": True, "lines": 0, "offered": 32, "windows": [(10720, 10634)], "unread": 0}
    assert g["window_exit"]["planned_lines"] == g["window_inner"]["offered"]
    assert g["window_stall"] == {"read": True, "stalled": 0, "windows": [], "interrupted": 0, "resent": 0,
                                 "refused_after_interrupt": 0}
    assert g["stand_crowd"] == {"read": True, "lines": 0, "n_hist": {}, "by_exit": {}, "closes": 0,
                                "inside_after_close": 0, "unread": 0}


def test_grade_e15_on_e16_keeps_every_grade_e13_key_through_grade_e14_and_reads_the_new_keys_zero():
    g, mine = _real(E16, "e_day_16.json")
    assert g["grade"] == "grade_e15" and all(g[k]["read"] is True for k in NEW)
    assert g["window_inner"] == {"read": True, "lines": 0, "offered": 0, "windows": [], "unread": 0}
    assert g["window_stall"]["stalled"] == 0
    assert g["stand_crowd"]["lines"] == 0 and g["stand_crowd"]["closes"] == 0
    for k in NEW + T14.NEW:
        mine.pop(k)
    mine["grade"] = "grade_e13"
    mine["report_lines"] = mine["report_lines"][:-(len(NEW) + len(T14.NEW))]
    assert mine == _committed(E16)
