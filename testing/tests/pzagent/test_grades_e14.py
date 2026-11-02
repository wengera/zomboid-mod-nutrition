"""base/grades/e14.py (Plan 26 Task 4), offline: `grade_e14` and its six readings of survival iteration 17 (the window
way out P26-A, the stand's second way out P26-B, the inside corner's shove P26-C, the bleed under the threat branch
P26-D, the worn wear P26-E and the edge-out check), each on a fabricated log where it counts and a clean one where it
reads zero, a mutant per reading, every `grade_e13` key unchanged under `grade_e14` on test_gates_e13's fixtures, and
the real check on E16 (`e_day_16-20261102-125450`): the new keys zero there and every grade_e13 key equal to the
committed `e_grade.txt`'s."""
import json
import os

import pytest

from agent.base import gates_e as E
from agent.base.grades import e14 as G
from agent.drivers import e_grade_13 as EG13
from . import test_gates_e13 as T13
from .test_gates_e import art
from .test_gates_e7 import T0, act, aline, zf
from .test_gates_e11 import bline
from .test_gates_e13 import _act, mline, sqr

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E16 = os.path.join(TESTING, "artifacts", "e_day_16-20261102-125450")
NEW = ("window_exit", "one_exit", "inside_send", "threat_bleed", "wear_worn", "edge_out_check")


def artifact(actions=(), results=(), goals=()):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    if goals:
        a["loop"]["goals"] = list(goals)
    return a


def grade(actions=(), results=(), log=None, frames=(), goals=()):
    return G.grade_e14(artifact(actions, results, goals), decision_lines=log, lines=list(frames))


def row(aid, type_, sent_s, state="done", reason="", branch="threat", ended=None, **args):
    """A loop.actions row sent `sent_s` seconds into the loop, ended `ended` (default one second on)."""
    a = act(aid, type_, sent_s, **args)
    a.update(state=state, reason=reason, branch=branch, endedS=sent_s + 1.0 if ended is None else ended)
    return a


def actl(aid, type_, state, t, result=None, reason=""):
    """A state-log act line `t` seconds into the loop."""
    return {"kind": "act", "aid": aid, "type": type_, "state": state, "reason": reason, "result": dict(result or {}),
            "seq": int(t * 10), "tick": int(t * 60), "wallMs": int((T0 + t) * 1000)}


# ================================================================ P26-A, the window way out
def win(flag, **extra):
    """A Flee window step's threat why (`flee.Flee._window_step`), else (flag False) a plain doorway flee's."""
    if not flag:
        return {"flee": extra.get("flee", "doorway")}
    w = {"flee": "doorway", "exit": 7, "outer": [5, 0, 0], "window": [3, 0], "smash": False, "step": "window",
         "shelter": None, "refused": []}
    w.update(extra)
    return w


def window_fixture(flag=True, mapped=True, act_lines=True):
    """The stand's `inside` end takes the window at (3, 0): the walk, the climb (w1) done with `cut`, the frame out of
    the shed; a trapped flee's second window at (6, 0) refused `locked` unsmashed (w2) and climbed as a smash (w3) with
    the frame still in the shed; a doorway flee's third climb (w4) failed by timeout; a goal's window (w5) not
    counted."""
    ex = {"end": "inside", "exit": "window" if flag else "door"}
    climb = (lambda x, smash=False: _act("window", x=x, y=0, smash=smash)) if flag else (
        lambda x, smash=False: _act("walkTo", x=x + 0.5, y=0.5))
    log = [aline(0, 0.0, win(flag, doorway_left="inside", doorway_exit=ex), _act("walkTo", x=3.5, y=0.5)),
           aline(1, 1.0, win(flag), climb(3)),
           aline(2, 2.0, win(flag), None, sent=False),
           aline(3, 3.0, {"fight": True, "target": 1}, None, sent=False),
           aline(4, 4.0, win(flag, flee="many", trapped=1, window=[6, 0]), climb(6)),
           aline(5, 5.0, win(flag, flee="many", trapped=1, window=[6, 0], smash=True), climb(6, True)),
           aline(6, 6.0, {"fight": True, "target": 1}, None, sent=False),
           aline(7, 8.0, win(flag, doorway_exit={"end": "wound", "exit": "door"}), climb(3)),
           bline(8, 9.0, "goal", {"goal": "LootBuilding"}, _act("window", x=9, y=0))]
    acts = [row("w0", "walkTo", 0.0, x=3.5, y=0.5)]
    if flag:
        acts += [row("w1", "window", 1.0, ended=2.0, x=3, y=0, smash=False),
                 row("w2", "window", 4.0, state="rejected", reason="locked", ended=4.2, x=6, y=0, smash=False),
                 row("w3", "window", 5.0, ended=6.0, x=6, y=0, smash=True),
                 row("w4", "window", 8.0, state="failed", reason="timeout", ended=8.5, x=3, y=0, smash=False),
                 row("w5", "window", 9.0, branch="goal", x=9, y=0)]
    lines = [actl("w1", "window", "accepted", 1.0), actl("w1", "window", "done", 2.0, {"smashed": False, "cut": True}),
             actl("w3", "window", "accepted", 5.0), actl("w3", "window", "done", 6.0, {"smashed": True, "cut": False})]
    results = [{"aid": "w1", "type": "window", "state": "done", "result": {"smashed": False, "cut": True}},
               {"aid": "w3", "type": "window", "state": "done", "result": {"smashed": True, "cut": False}}]
    ts = (0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.5, 7.0, 8.0, 9.0)
    frames = [zf(t, x=5.5 if 2.5 <= t < 4 else 2.5, y=0.5) for t in ts]
    squares = [sqr(x, 0, room="shed") for x in range(4)] + [sqr(x, 0) for x in range(4, 9)]
    maps = [mline(-1, squares)] if mapped else []
    return grade(acts, results, log, frames + maps + (lines if act_lines else []))["window_exit"]


def test_the_window_exit_counts_the_window_steps_their_runs_the_climbs_their_ends_and_the_room_left():
    g = window_fixture()
    assert g["read"] is True and (g["planned_lines"], g["planned"]) == (6, 3) and g["windows"] == [(3, 0), (6, 0)]
    assert g["by_end"] == {"inside": 1}
    assert g["runs_from"] == {"inside": 1, "trapped": 1, "flee:doorway": 1}
    assert (g["sent"], g["sent_lines"], g["smash_sent"], g["done"], g["refused"]) == (4, 4, 1, 2, 2)
    assert g["ends"] == {"done": 2, "failed": 1, "rejected": 1, "running": 0}
    assert g["reasons"] == {"rejected:locked": 1, "failed:timeout": 1}
    assert (g["smashed"], g["cut"]) == (1, 1)
    # w1's frames read x 5.5 (no room) half a second after its end; w3's read the shed for WINDOW_LEFT_S
    assert (g["left"], g["stayed"], g["unread"]) == (1, 1, 0)


def test_the_window_exit_reads_smashed_and_cut_off_loop_results_without_act_lines_and_unread_without_a_map():
    g = window_fixture(act_lines=False)
    assert (g["smashed"], g["cut"], g["left"], g["stayed"]) == (1, 1, 1, 1)
    g = window_fixture(mapped=False)
    assert (g["left"], g["stayed"], g["unread"]) == (0, 0, 2)


def test_the_window_exit_reads_zero_without_the_window_step_and_unread_without_a_log():
    g = window_fixture(flag=False)
    assert (g["planned_lines"], g["planned"], g["windows"], g["by_end"], g["runs_from"]) == (0, 0, [], {}, {})
    assert (g["sent"], g["sent_lines"], g["done"], g["refused"], g["smashed"], g["cut"], g["left"]) == (0,) * 7
    assert grade(log=None)["window_exit"] == {"read": False}


# ================================================================ P26-B, the stand's second way out
def one_exit_fixture(flag=True):
    pick = "one_exit" if flag else "ok"
    many = lambda **kw: dict({"flee": "many", "doorway_pick": pick, "shelter": None}, **kw)
    log = [aline(0, 0.0, many(), None, sent=False),
           aline(1, 1.0, many(), None, sent=False),
           aline(2, 2.0, dict(many(), doorway_pick="no_door"), None, sent=False),
           aline(3, 3.0, many(shelter=4), None, sent=False),
           aline(4, 4.0, {"flee": "pair", "doorway_pick": pick}, None, sent=False),      # not a `many` line
           bline(5, 5.0, "care", {"reason": "bleeding"}, None, sent=False, others={"threat": many()})]
    return grade(log=log)["one_exit"]


def test_the_one_exit_counts_the_many_lines_refused_one_exit_their_runs_and_the_buildings_named():
    g = one_exit_fixture()
    assert g["read"] is True and (g["lines"], g["runs"], g["unnamed"]) == (4, 3, 3)
    assert g["picks"] == {"one_exit": 4, "no_door": 1} and g["buildings"] == ["4"]


def test_the_one_exit_reads_zero_where_every_pick_passes_and_unread_without_a_log():
    g = one_exit_fixture(flag=False)
    assert (g["lines"], g["runs"], g["buildings"], g["unnamed"]) == (0, 0, [], 0)
    assert g["picks"] == {"ok": 4, "no_door": 1}
    assert grade(log=None)["one_exit"] == {"read": False}


# ================================================================ P26-C, the inside corner's shove
def inside_fixture(flag=True):
    kind = "inside" if flag else "shove"
    c = lambda send, n: {"corner": {"kind": kind, "send": send, "near_n": n}, "fight": True}
    log = [aline(0, 0.0, dict(c("shove", 2), shove="crowd"), _act("shove", targetId=1)),
           aline(1, 1.0, c("stomp", 2), _act("stomp", targetId=1)),
           aline(2, 2.0, c("attack", 1), _act("attack", targetId=1)),
           aline(3, 3.0, c("attack", 2), _act("attack", targetId=1)),       # the rule's own check: never sent
           aline(4, 4.0, {"corner": {"kind": "shove", "n": 2}, "fight": True}, _act("shove", targetId=1)),   # P25-A
           aline(5, 5.0, c("shove", 2), _act("shove", targetId=1), sent=False),
           bline(6, 6.0, "care", {"reason": "bleeding"}, None, sent=False, others={"threat": c("attack", 2)})]
    return grade(log=log)["inside_send"]


def test_the_inside_send_tallies_the_inside_corner_s_sends_their_near_n_and_the_crowd_attacks():
    g = inside_fixture()
    assert g["read"] is True and g["lines"] == 5
    assert g["sends"] == {"shove": 2, "stomp": 1, "attack": 2, "other": 0} and g["near_n"] == {"2": 4, "1": 1}
    assert (g["crowd_attacks"], g["unsent"], g["crowd_shoves"]) == (1, 1, 1)


def test_the_inside_send_never_counts_p25_a_s_corner_kinds_and_reads_unread_without_a_log():
    g = inside_fixture(flag=False)
    assert (g["lines"], g["near_n"], g["crowd_attacks"], g["unsent"]) == (0, {}, 0, 0)
    assert g["sends"] == {"shove": 0, "stomp": 0, "attack": 0, "other": 0}
    assert grade(log=None)["inside_send"] == {"read": False}


# ================================================================ P26-D, the bleed under the threat branch
BLEED = [{"i": 2, "bleeding": True, "bleedingTime": 8.34}]
DRY = [{"i": 2, "bleeding": False}]


def bleed_fixture(flag=True):
    """Two `bleed` yields that ride (after a `pair` flee and a `held` one) and one standing, a P24-P yield with no
    `care_yield`; bleeding frames before the first line, under the threat, under a running bandage, under the care and
    under a goal line."""
    y = lambda near, ride: dict({"care": True, "nearest": near, "held": 1}, **(
        {"care_yield": {"why": "bleed", "near": near}} if flag else {}), **({"ride": True} if ride else {}))
    bandage = _act("bandage", itemId=5, part=2, keepMoving=True)
    log = [aline(0, 0.0, {"flee": "pair"}, _act("steer", vx=1, vy=0)),
           aline(1, 1.0, y(4.0, True), bandage, branch="care"),
           aline(2, 2.0, {"flee": "held"}, None, sent=False),
           aline(3, 3.0, y(3.5, True), bandage, branch="care"),
           aline(4, 4.0, {"fight": True}, None, sent=False),
           aline(5, 5.0, y(2.5, False), _act("bandage", itemId=5, part=2), branch="care"),
           aline(6, 6.0, {"care": True, "nearest": 5.0, "held": 1}, None, sent=False, branch="care"),
           aline(7, 7.0, {"fight": True}, None, sent=False),
           aline(8, 8.0, {"fight": True}, None, sent=False),
           bline(9, 9.5, "goal", {"goal": "Rest"}, None, sent=False)]
    parts = {9.0: DRY}
    ts = (-0.5, 0.5, 1.5, 2.6, 6.5, 7.5, 8.5, 9.0, 10.0)
    frames = [zf(t, parts=parts.get(t, BLEED if flag else DRY)) for t in ts]
    acts = [actl("b1", "bandage", "accepted", 1.0), actl("b1", "bandage", "progress", 1.8),
            actl("b1", "bandage", "done", 2.5), actl("b2", "bandage", "accepted", 20.0)]
    return grade(log=log, frames=frames + acts)["threat_bleed"]


def test_the_threat_bleed_counts_the_bleed_yields_their_rides_and_the_unbandaged_frames_by_branch():
    g = bleed_fixture()
    assert g["read"] is True and (g["yields"], g["rides"], g["standing"]) == (3, 2, 1) and g["near"] == [4.0, 3.5, 2.5]
    assert g["rides_by_leg"] == {"pair": 1, "held": 1}
    assert (g["bleeding_frames"], g["bandaging"]) == (8, 1)
    assert g["unbandaged"] == {"threat": 4, "care": 1, "other": 1, "none": 1}
    # 0.5 (threat), 1.5 under b1's span, 2.6 (threat), 6.5 (care), 7.5 and 8.5 (threat: two in a row), 9.0 dry,
    # 10.0 (goal)
    assert g["threat_run"] == 2


def test_the_threat_bleed_reads_zero_without_the_yield_or_a_bleed_and_unread_without_a_log():
    g = bleed_fixture(flag=False)
    assert (g["yields"], g["near"], g["rides"], g["standing"], g["rides_by_leg"]) == (0, [], 0, 0, {})
    assert (g["bleeding_frames"], g["bandaging"], g["threat_run"]) == (0, 0, 0)
    assert g["unbandaged"] == {"threat": 0, "care": 0, "other": 0, "none": 0}
    assert grade(log=None)["threat_bleed"] == {"read": False}


# ================================================================ P26-E, the worn wear
def wear_fixture(flag=True):
    """Jeans 21 worn, then refused `worn` (marked), one wear sent while the refusal ran and one after it (the re-send
    the rule forbids); a hat 33; the stock lines' `skipped_worn`."""
    if flag:
        acts = [row("a1", "wear", 1.0, branch="care", itemId=21),
                row("a2", "wear", 10.0, state="rejected", reason="worn", ended=11.0, branch="care", itemId=21),
                row("a3", "wear", 10.5, branch="care", itemId=21),
                row("a4", "wear", 12.0, state="rejected", reason="worn", ended=12.5, branch="care", itemId=21),
                row("a5", "wear", 13.0, branch="care", itemId=33)]
    else:
        acts = [row("a1", "wear", 1.0, branch="care", itemId=21), row("a5", "wear", 13.0, branch="care", itemId=33)]
    stock = lambda **kw: {"stock": dict({"reason": "wear", "item": 33, "loc": "base:hat", "gain": 5}, **kw)}
    log = [bline(0, 1.0, "care", stock(**({"skipped_worn": 1} if flag else {})), _act("wear", itemId=33)),
           bline(1, 2.0, "care", stock(**({"skipped_worn": 2} if flag else {})), _act("wear", itemId=33)),
           bline(2, 3.0, "care", stock(), _act("wear", itemId=33)),
           aline(3, 4.0, {"fight": True}, None, sent=False, care={"stock": {"skipped_worn": 9}})]   # the threat's line
    return grade(acts, [], log)["wear_worn"]


def test_the_wear_worn_counts_the_wears_per_item_the_worn_refusals_and_the_re_send_of_a_marked_item():
    g = wear_fixture()
    assert g["read"] is True and g["sends"] == 5 and g["per_item"] == {"21": 4, "33": 1}
    assert (g["rejected_worn"], g["marked"], g["resends"]) == (2, 1, 1)
    assert (g["skipped_lines"], g["skipped_max"]) == (2, 2)


def test_the_wear_worn_reads_zero_without_a_refusal_and_unread_without_a_log():
    g = wear_fixture(flag=False)
    assert (g["sends"], g["rejected_worn"], g["marked"], g["resends"], g["skipped_lines"]) == (2, 0, 0, 0, 0)
    assert g["skipped_max"] is None
    assert grade(log=None)["wear_worn"] == {"read": False}


# ================================================================ the edge-out check
def test_the_edge_out_check_copies_only_out_and_flags_it_when_nonzero():
    check = lambda n: G.e_edge_out_check({"edge_out": {"read": True, "only_out": n}})
    assert check(2) == {"read": True, "only_out": 2, "flagged": True}
    assert check(0) == {"read": True, "only_out": 0, "flagged": False}
    assert G.e_edge_out_check({"edge_out": {"read": False}}) == {"read": False} == G.e_edge_out_check({})
    assert grade(log=None)["edge_out_check"] == {"read": False}


def test_the_edge_out_check_flags_test_gates_e13_s_out_fixture(monkeypatch):
    seen = _captured(monkeypatch, T13.out_fixture)
    g = grade(log=seen["log"], frames=seen["frames"])
    assert g["edge_out"]["only_out"] == 2 and g["edge_out_check"] == {"read": True, "only_out": 2, "flagged": True}


# ================================================================ grade_e14 over grade_e13
def _captured(monkeypatch, fixture):
    """What test_gates_e13's `fixture` grades ({actions, results, log, frames, goals, stop}), captured off its
    `grade`."""
    seen = {}

    def grab(actions=(), results=(), log=None, frames=(), goals=(), stop="day_cap"):
        seen.update(actions=list(actions), results=list(results), log=log, frames=list(frames), goals=list(goals),
                    stop=stop)
        return {k: {} for k in T13.NEW}
    monkeypatch.setattr(T13, "grade", grab)
    fixture()
    monkeypatch.undo()
    return seen


E13_FIXTURES = [T13.drag_fixture, T13.inside_fixture, T13.exit_fixture, T13.edge_fixture, T13.out_fixture,
                T13.ttl_fixture, T13.order_fixture, T13.dirty_fixture]


@pytest.mark.parametrize("fixture", E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e14_reads_every_grade_e13_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = _captured(monkeypatch, fixture)
    a = artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e13 = E.grade_e13(a, decision_lines=seen["log"], lines=seen["frames"])
    e14 = G.grade_e14(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e14["grade"] == "grade_e14" and all(e14[k]["read"] is True for k in NEW)
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e13.items() if k not in skip} == {k: v for k, v in e14.items() if k not in skip}
    assert e14["report_lines"][:-len(NEW)] == e13["report_lines"]


def test_report_lines_e14_names_gate_e14_then_one_line_per_rule_marked_reading():
    g = G.grade_e14(artifact(), decision_lines=[aline(0, 0.0, {"fight": True}, None, sent=False)], lines=[])
    tail = g["report_lines"][-len(NEW):]
    for line, tag in zip(tail, ("P26-A", "P26-B", "P26-C", "P26-D", "P26-E", "P25-X amended")):
        assert ("(%s)" % tag) in line and "[reading]" in line and len(line) > 0
    assert "FLAGGED" not in tail[-1]
    off = G.grade_e14(artifact(), decision_lines=None, lines=[])["report_lines"][-len(NEW):]
    assert all("no decision log read" in line for line in off)
    renamed = G.report_lines_e14(dict(g, gate={"pass": True}))
    assert not any(line.startswith("gate_e13 ") for line in renamed)
    assert G.gate_e14([]) == E.gate_e13([])


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/e14.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "e14_mutant"}
    exec(compile(src[:start] + new + src[end:], "e14_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    ("e_window_exit", lambda b: b.replace('ex.get("exit") == "window"', 'ex.get("exit") == "door"'),
     lambda: window_fixture()["by_end"] == {"inside": 1}),
    ("e_window_exit", lambda b: b.replace('_loop_actions(out, "window", "threat")', '_loop_actions(out, "window")'),
     lambda: window_fixture()["sent"] == 4),
    ("e_window_exit", lambda b: b.replace('res.get("cut") is True', 'res.get("cut") is not None'),
     lambda: window_fixture()["cut"] == 1),
    ("_left_room", lambda b: b.replace("if out_ is True:", "if out_ is None:"),
     lambda: window_fixture()["left"] == 1),
    ("_run_origin", lambda b: b.replace('"trapped" if "trapped" in w else ', ''),
     lambda: window_fixture()["runs_from"]["trapped"] == 1),
    ("e_one_exit", lambda b: b.replace('many = w.get("flee") == "many"', 'many = w.get("flee") is not None'),
     lambda: one_exit_fixture()["lines"] == 4),
    ("e_one_exit", lambda b: b.replace("runs += 0 if prev else 1", "runs += 1"),
     lambda: one_exit_fixture()["runs"] == 3),
    ("e_inside_send", lambda b: b.replace('c.get("kind") != "inside"', 'c.get("kind") is None'),
     lambda: inside_fixture()["lines"] == 5),
    ("e_inside_send", lambda b: b.replace("n >= INSIDE_CROWD_N", "n > INSIDE_CROWD_N"),
     lambda: inside_fixture()["crowd_attacks"] == 1),
    ("e_inside_send", lambda b: b.replace('if ln.get("branch") != "threat":', 'if False:'),
     lambda: inside_fixture()["lines"] == 5),
    ("e_threat_bleed", lambda b: b.replace('cy.get("why") == "bleed"', 'cy.get("why") is not None'),
     lambda: bleed_fixture(flag=False)["yields"] == 0 and bleed_fixture()["yields"] == 3 and _p24p_yield_is_no_bleed()),
    ("e_threat_bleed", lambda b: b.replace("if any(s <= w <= e for s, e in spans):", "if False:"),
     lambda: bleed_fixture()["bandaging"] == 1),
    ("e_threat_bleed", lambda b: b.replace('run = run + 1 if br == "threat" else 0', "run = run + 1"),
     lambda: bleed_fixture()["threat_run"] == 2),
    ("e_threat_bleed", lambda b: b.replace('_inc(legs, str(last_flee))', '_inc(legs, "pair")'),
     lambda: bleed_fixture()["rides_by_leg"] == {"pair": 1, "held": 1}),
    ("e_wear_worn", lambda b: b.replace("t >= marked[iid]", "t >= 0"), lambda: wear_fixture()["resends"] == 1),
    ("e_wear_worn", lambda b: b.replace('a.get("reason") == "worn":', 'a.get("reason") is not None:'),
     lambda: wear_fixture()["marked"] == 1 and _a_locked_wear_marks_nothing()),
    ("_skipped_worn", lambda b: b.replace('.get("skipped_worn", c.get("skipped_worn"))', '.get("gain")'),
     lambda: wear_fixture()["skipped_max"] == 2),
    ("e_edge_out_check", lambda b: b.replace('"flagged": bool(n)', '"flagged": False'),
     lambda: G.e_edge_out_check({"edge_out": {"read": True, "only_out": 2}})["flagged"] is True),
]


def _p24p_yield_is_no_bleed():
    """A yield with a `care_yield` of another why (none exists today) is no bleed yield."""
    log = [aline(0, 0.0, {"care": True, "nearest": 4.0, "care_yield": {"why": "other", "near": 4.0}}, None, sent=False)]
    return grade(log=log)["threat_bleed"]["yields"] == 0


def _a_locked_wear_marks_nothing():
    acts = [row("a1", "wear", 1.0, state="rejected", reason="busy", branch="care", itemId=21),
            row("a2", "wear", 5.0, branch="care", itemId=21)]
    g = grade(acts, [], [aline(0, 0.0, {"fight": True}, None, sent=False)])["wear_worn"]
    return g["marked"] == 0 and g["resends"] == 0


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


# ================================================================ the real check: E16
def _e16():
    p = os.path.join(E16, "e_day_16.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E16)
    return p


def test_grade_e14_on_e16_reads_iteration_17_s_keys_zero_and_every_grade_e13_key_as_the_committed_e_grade_txt():
    p = _e16()
    g = G.grade_e14(EG13.load(p), None, EG13.load_log(p), state_dir=EG13._dir(p))
    assert g["grade"] == "grade_e14" and all(g[k]["read"] is True for k in NEW)
    w, o, s, b, ww = (g[k] for k in NEW[:5])
    # E16 ran iteration 16: no window step, no one_exit pick, no inside corner, no bleed yield, no worn refusal
    assert (w["planned_lines"], w["sent"], w["done"], w["smashed"], w["cut"], w["left"]) == (0,) * 6
    assert (o["lines"], o["runs"]) == (0, 0)
    assert (s["lines"], s["crowd_attacks"], s["crowd_shoves"]) == (0, 0, 0)
    assert (b["yields"], b["rides"]) == (0, 0)
    assert (ww["rejected_worn"], ww["marked"], ww["resends"], ww["skipped_lines"]) == (0, 0, 0, 0)
    assert g["edge_out_check"] == {"read": True, "only_out": 0, "flagged": False}
    text = open(os.path.join(E16, "e_grade.txt"), encoding="utf-8").read()
    committed = json.loads(text[text.index("\n{\n"):])
    mine = json.loads(json.dumps(EG13.finite({k: v for k, v in g.items() if k not in NEW}), sort_keys=True,
                                 allow_nan=False))
    mine["grade"] = "grade_e13"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed
