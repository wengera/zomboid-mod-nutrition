"""base/grades/e19.py (Plan 28 Task 7c), offline: `grade_e19` and its four readings of survival iteration 22 (the
melee reflex skill of PZA/1.8 and the planner's `Melee` maneuver: the melee spans, the hits inside and outside them,
the strike before each hit inside a span by step, the skill tick's cost over the spans), each on a fabricated log
where it counts and a clean one where it reads zero, the unread case (`melee` needs the decision log, the other three
a frame), a mutant per reading, every `grade_e18` key unchanged under `grade_e19` on test_gates_e13's fixtures, the
module's frozen copies (ruling P26-Q), and the real checks on E21 (`e_day_21-20261104-201749`, no melee sent: the new
keys read zero there): every inherited key equal to the committed `e_grade.txt`'s, through the function and through
`e_grade_19.py` (its printed lines the committed ones then the four new ones)."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e18 as G18
from agent.base.grades import e19 as G
from agent.drivers import e_grade_19 as EG19
from . import test_grades_e14 as T14
from .test_gates_e13 import _act
from .test_gates_e7 import aline
from .test_grades_e14 import actl, row
from .test_grades_e17 import CLEAN
from .test_grades_e18 import hf

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E21 = os.path.join(TESTING, "artifacts", "e_day_21-20261104-201749")
NEW = G.NEW
NEW18 = G18.NEW


def grade(actions=(), results=(), log=None, frames=(), fights=None):
    a = T14.artifact(actions, results)
    if fights is not None:
        a["loop"]["fights"] = list(fights)
    return G.grade_e19(a, decision_lines=log, lines=list(frames))


def mf(t, aid=None, step=None, react="", act_ms=0.0, max_ms=0.0):
    """`hf` with the frame's `act` group (PZA/1.8: aid, state, step; None without an aid) and its skill tick's cost."""
    f = hf(t, react)
    f["act"] = {"aid": aid, "state": "accepted", "step": step} if aid is not None else None
    f["cost"] = dict(f["cost"], actMs=act_ms, maxActMs=max_ms)
    return f


def prog(aid, t, step, d, **counts):
    """A melee progress act line: the step, d, hp and the six counts (0 unless given)."""
    r = dict({k: 0 for k in G.COUNTS}, step=step, d=d, hp=2.0, **counts)
    return actl(aid, "melee", "progress", t, r)


def mdone(aid, t, end, steps, **counts):
    r = dict({k: 0 for k in G.COUNTS}, end=end, kill=end == "dead", hp0=2.0, hp1=1.5, dMin=0.5, steps=steps, **counts)
    return actl(aid, "melee", "done", t, r)


def mv(zid, **why):
    """A threat why sending or holding a melee at `zid` (`dispatch._melee_dispatch`'s keys)."""
    m = {"maneuver": "melee", "target": zid, "mode": "strike", "sends": 1, "step": None, "d": None}
    return dict({"fight": True, "target": zid, "maneuver": m}, **why)


def melee_lines():
    """The state log, in wall order. m1 (a strike at 9, 1.0 to 3.0, failed superseded): face, swing, a hit, stand;
    m2 (its re-send, 3.0 to 5.0, done time): back twice (the heartbeat), shove, knock_wait, a hit; the ladder's stomp
    k0 at 6 killing inside m2's span; m3 (a finish at 9, 5.0 to 5.5, done dead, the kill); m4 rejected too far; the
    attacks a1 (killing 5) and a3 (killing 9 again, not counted twice); m5 (a shove at 3 from 12.0, open: no terminal
    line, its span to its last line at 12.25). The frames: m1's face, its hit run (two frames), its stand; m2's shove
    and its hit run; m3's stomp; two runs outside the spans (9.0 inside fight 0, 9.75 in none); m5's close."""
    return [
        mf(0.5, act_ms=0, max_ms=1),
        actl("m1", "melee", "accepted", 1.0),
        prog("m1", 1.25, "face", 1.0), mf(1.25, "m1", "face", act_ms=2, max_ms=4),
        prog("m1", 1.5, "swing", 0.9, swings=1),
        prog("m1", 2.0, "hit", 0.7, swings=1, hits=1), mf(2.0, "m1", "hit", "Bite", 4, 8),
        mf(2.25, "m1", "hit", "Bite", 2, 4),
        prog("m1", 2.5, "stand", 0.8, swings=1, hits=1), mf(2.5, "m1", "stand", act_ms=2, max_ms=4),
        actl("m1", "melee", "failed", 3.0, reason="superseded"),
        actl("m2", "melee", "accepted", 3.0),
        prog("m2", 3.25, "back", 0.6), prog("m2", 3.5, "back", 0.9),
        prog("m2", 4.0, "shove", 1.0, shoves=1),
        actl("k0", "stomp", "accepted", 4.25), mf(4.25, "m2", "shove", act_ms=6, max_ms=12),
        prog("m2", 4.5, "knock_wait", 1.05, shoves=1, knockdowns=1),
        actl("k0", "stomp", "done", 4.5, {"hit": True, "targetDead": True}),
        prog("m2", 4.75, "hit", 0.9, shoves=1, knockdowns=1, hits=1), mf(4.75, "m2", "hit", "BiteLEFT", 2, 4),
        mdone("m2", 5.0, "time", {"back": 30, "shove": 20, "knock_wait": 5, "hit": 5}, shoves=1, knockdowns=1,
              hits=1),
        actl("m3", "melee", "accepted", 5.0),
        prog("m3", 5.25, "stomp", 0.4, stomps=1), mf(5.25, "m3", "stomp", act_ms=3, max_ms=6),
        mdone("m3", 5.5, "dead", {"stomp": 18}, stomps=1),
        actl("m4", "melee", "rejected", 8.0, reason="too far"),
        mf(9.0, react="Bite", act_ms=1, max_ms=2), mf(9.5, act_ms=2, max_ms=4),
        mf(9.75, react="Bite", act_ms=1, max_ms=3), mf(9.875, act_ms=1, max_ms=1),
        actl("a1", "attack", "accepted", 10.0), mf(10.5, "a1", act_ms=1, max_ms=1),
        actl("a1", "attack", "done", 10.5, {"targetDead": True}),
        actl("a3", "attack", "accepted", 11.5), actl("a3", "attack", "done", 11.75, {"targetDead": True}),
        actl("m5", "melee", "accepted", 12.0), mf(12.125, "m5", "close", act_ms=3, max_ms=6),
        prog("m5", 12.25, "close", 2.0)]


def melee_actions():
    return [row("m1", "melee", 1.0, state="failed", reason="superseded", targetId=9, mode="strike"),
            row("m2", "melee", 3.0, targetId=9, mode="strike"), row("k0", "stomp", 4.25, targetId=6),
            row("m3", "melee", 5.0, targetId=9, mode="finish"),
            row("m4", "melee", 8.0, state="rejected", reason="too far", targetId=7, mode="strike"),
            row("a1", "attack", 10.0, targetId=5), row("a3", "attack", 11.5, targetId=9),
            row("m5", "melee", 12.0, state="accepted", targetId=3, mode="shove"),
            row("m6", "melee", 13.0, state="failed", reason="interrupted", targetId=2, mode="strike")]


def melee_log():
    """Seven threat lines carrying the maneuver: the sends (ladder attack, aim with an early re-send, stomp with a time
    re-send, attack at 7, shove at 3), a holding line, a re-send logged and not sent; two `melee_end` lines; an
    attack; a care line sending a melee with a re-send (not read)."""
    return [aline(0, 1.0, mv(9, ladder="attack"), _act("melee", targetId=9, mode="strike")),
            aline(1, 2.0, mv(9), None, sent=False),
            aline(2, 3.0, mv(9, ladder="aim", leg="back", melee={"resend": "early"}),
                  _act("melee", targetId=9, mode="strike")),
            aline(3, 5.0, mv(9, ladder="stomp", melee={"resend": "time"}), _act("melee", targetId=9, mode="finish")),
            aline(4, 5.75, {"fight": True, "target": 7, "melee_end": {"maneuver": "melee", "target": 9,
                                                                      "end": "dead"}}, None, sent=False),
            aline(5, 8.0, mv(7, ladder="attack"), _act("melee", targetId=7, mode="strike")),
            aline(6, 8.5, {"fight": True, "target": 5, "melee_end": {"maneuver": "melee", "target": 7,
                                                                     "end": "too far"}}, None, sent=False),
            aline(7, 9.0, mv(5, ladder="attack", melee={"resend": "early"}), _act("melee", targetId=5), sent=False),
            aline(8, 10.0, {"fight": True, "target": 5}, _act("attack", targetId=5)),
            aline(9, 11.0, mv(4, ladder="attack", melee={"resend": "time"}), _act("melee", targetId=4),
                  branch="care"),
            aline(10, 12.0, mv(3, ladder="shove"), _act("melee", targetId=3, mode="shove"))]


FIGHTS = [{"startS": 0.5, "end": {"endS": 9.5}}, {"startS": 10.0, "end": None}]


def melee_fixture(log=True):
    return grade(melee_actions(), [], melee_log() if log else None, melee_lines(), fights=FIGHTS)


# ================================================================ melee, the spans
MELEE = {"read": True, "sent": 6, "by_mode": {"strike": 4, "finish": 1, "shove": 1}, "accepted": 4,
         "ends": {"failed superseded": 1, "done time": 1, "done dead": 1, "rejected too far": 1, "open": 1,
                  "failed interrupted": 1},
         "steps": {"face": 1, "swing": 1, "hit": 2, "stand": 1, "back": 1, "shove": 1, "knock_wait": 1, "stomp": 1,
                   "close": 1},
         "step_ticks": {"back": 30, "shove": 20, "knock_wait": 5, "hit": 5, "stomp": 18},
         "frame_steps": {"face": 1, "hit": 3, "stand": 1, "shove": 1, "stomp": 1, "close": 1},
         "swings": 1, "shoves": 1, "stomps": 1, "floors": 0, "knockdowns": 1, "hits": 2, "kills": 2,
         "resends": {"early": 1, "time": 1}, "planner_ends": {"dead": 1, "too far": 1},
         "replaced": {"attack": 2, "aim": 1, "stomp": 1, "shove": 1}, "lines": 7, "mean_span_s": 1.5,
         "by_fight": [3, 1], "outside_fights": 0}


def test_the_melee_counts_the_spans_their_ends_steps_counts_kills_re_sends_and_the_ladder_they_replaced():
    assert melee_fixture()["melee"] == MELEE


def _zero_melee(fights=0):
    return {"read": True, "sent": 0, "by_mode": {}, "accepted": 0, "ends": {}, "steps": {}, "step_ticks": {},
            "frame_steps": {}, "swings": 0, "shoves": 0, "stomps": 0, "floors": 0, "knockdowns": 0, "hits": 0,
            "kills": 0, "resends": {}, "planner_ends": {}, "replaced": {}, "lines": 0, "mean_span_s": None,
            "by_fight": [0] * fights, "outside_fights": 0}


def test_the_melee_reads_zero_without_a_melee_and_unread_without_a_log():
    assert grade(log=CLEAN, frames=[hf(0.0), hf(1.0)])["melee"] == _zero_melee()
    assert melee_fixture(log=False)["melee"] == {"read": False}


def test_the_index_finds_the_latest_accepted_span_holding_a_wall_past_a_shorter_one():
    long_, short = {"aid": "a", "accept": 0.0, "end": 10.0}, {"aid": "b", "accept": 2.0, "end": 3.0}
    idx = G._Index([long_, short])
    assert idx.at(5.0) is long_ and idx.at(2.5) is short and idx.at(11.0) is None and idx.at(None) is None
    assert G._Index([]).at(1.0) is None


def _index_case():
    idx = G._Index([{"aid": "a", "accept": 0.0, "end": 10.0}, {"aid": "b", "accept": 2.0, "end": 3.0}])
    got = idx.at(5.0)
    return got is not None and got["aid"] == "a" and idx.at(-1.0) is None


# ================================================================ hits_in_melee, the A/B
HITS_IN = {"read": True, "runs": 4, "inside": 2, "outside": 2, "outside_fight": 1, "kills_inside": 2,
           "kills_outside": 1, "kills": 3, "per_kill": 4 / 3, "per_kill_inside": 1.0, "per_kill_outside": 2.0}


def test_the_hits_in_melee_split_the_runs_and_the_kills_by_the_spans():
    g = melee_fixture()
    assert g["hits_in_melee"] == HITS_IN
    assert g["hits"]["runs"] == 4 and g["kills"]["planner"] == 3    # the inherited hits: m3's kill read by none


def test_the_hits_in_melee_read_zero_on_quiet_frames_and_unread_without_frames():
    assert grade(log=None, frames=[hf(0.0), hf(1.0)])["hits_in_melee"] == {
        "read": True, "runs": 0, "inside": 0, "outside": 0, "outside_fight": 0, "kills_inside": 0, "kills_outside": 0,
        "kills": 0, "per_kill": None, "per_kill_inside": None, "per_kill_outside": None}
    assert grade(log=CLEAN)["hits_in_melee"] == {"read": False}


# ================================================================ melee_strike, the strike before each hit by step
def _sb(seq, kind, **kw):
    out = {"seq": seq, "kind": kind, "type": None, "aid": None, "before_s": None, "target": None, "nearest": None,
           "knockdown": None, "attackStarted": None}
    out.update(kw)
    return out


STRIKE = {"read": True, "runs": 2, "by_frame_step": {"hit": 2}, "by_step_before": {"swing": 1, "knock_wait": 1},
          "by_press": {"swing": 1, "shove": 1},
          "rows": [{"seq": 20, "kind": "Bite", "aid": "m1", "frame_aid": "m1", "frame_step": "hit", "prev_step": "face",
                    "step_before": "swing", "step_before_s": 0.5, "press": {"step": "swing", "before_s": 0.5, "d": 0.9},
                    "strike_before": _sb(20, "Bite")},
                   {"seq": 47, "kind": "BiteLEFT", "aid": "m2", "frame_aid": "m2", "frame_step": "hit",
                    "prev_step": "shove", "step_before": "knock_wait", "step_before_s": 0.25,
                    "press": {"step": "shove", "before_s": 0.75, "d": 1.0},
                    "strike_before": _sb(47, "BiteLEFT", type="stomp", aid="k0", before_s=0.5, target=6,
                                         nearest=False)}]}


def test_the_melee_strike_reads_each_hit_inside_a_span_by_its_step_the_step_before_and_the_press():
    assert melee_fixture()["melee_strike"] == STRIKE


def test_the_melee_strike_reads_no_press_beyond_the_window_and_zero_without_a_span():
    span = {"progress": [(1000.0, {"step": "swing", "d": 0.9}), (3200.0, {"step": "stand", "d": 1.0})]}
    assert G._press_before(span, 3500.0) is None
    assert G._press_before(span, 2900.0) == {"step": "swing", "before_s": 1.9, "d": 0.9}
    assert G._step_before({"progress": [(1.0, {"step": "hit"})]}, 2.0) == (None, None)
    assert grade(log=None, frames=[hf(0.0, "Bite"), hf(1.0)])["melee_strike"] == {
        "read": True, "runs": 0, "by_frame_step": {}, "by_step_before": {}, "by_press": {}, "rows": []}
    assert grade(log=CLEAN)["melee_strike"] == {"read": False}


# ================================================================ melee_cost
COST = {"read": True,
        "inside": {"frames": 8, "actMs_mean": 3.0, "actMs_max": 6, "maxActMs_mean": 6.0, "maxActMs_max": 12},
        "outside": {"frames": 6, "actMs_mean": 1.0, "actMs_max": 2, "maxActMs_mean": 2.0, "maxActMs_max": 4}}


def test_the_melee_cost_reads_the_skill_tick_inside_the_spans_against_outside():
    assert melee_fixture()["melee_cost"] == COST


def test_the_melee_cost_reads_no_frame_inside_without_a_span_and_unread_without_frames():
    f = mf(1.0, act_ms=0.5, max_ms=1.5)
    f["cost"].pop("maxActMs")
    assert grade(log=None, frames=[f])["melee_cost"] == {
        "read": True, "inside": {"frames": 0, "actMs_mean": None, "actMs_max": None, "maxActMs_mean": None,
                                 "maxActMs_max": None},
        "outside": {"frames": 1, "actMs_mean": 0.5, "actMs_max": 0.5, "maxActMs_mean": None, "maxActMs_max": None}}
    assert grade(log=CLEAN)["melee_cost"] == {"read": False}


# ================================================================ grade_e19 over grade_e18
@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e19_reads_every_grade_e18_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e18 = G18.grade_e18(a, decision_lines=seen["log"], lines=seen["frames"])
    e19 = G.grade_e19(a, decision_lines=seen["log"], lines=seen["frames"])
    framed = bool(E._frame_index(seen["frames"])[1])
    assert e19["grade"] == "grade_e19" and e19["melee"]["read"] is True
    assert all(e19[k]["read"] is framed for k in NEW[1:])
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e18.items() if k not in skip} == {k: v for k, v in e19.items() if k not in skip}
    assert e19["report_lines"][:-len(NEW)] == [("gate_e19 " + ln[len("gate_e18 "):]) if ln.startswith("gate_e18 ")
                                               else ln for ln in e18["report_lines"]]


def test_grade_e19_without_a_decision_log_reads_the_melee_unread_but_the_frames_readings():
    g = grade(log=None, frames=[hf(0.0, "Bite"), hf(1.0)])
    assert g["grade"] == "grade_e19" and g["melee"] == {"read": False}
    assert all(g[k]["read"] is True for k in NEW[1:])
    assert G.readings_e19({}, None, []) == {k: {"read": False} for k in NEW}
    assert NEW == ("melee", "hits_in_melee", "melee_strike", "melee_cost")


def test_report_lines_e19_names_gate_e19_then_one_line_per_reading_marked_reading_or_inference():
    g = melee_fixture()
    tail = g["report_lines"][-len(NEW):]
    assert tail == G.lines_e19(g)
    for line in tail:
        assert "(iteration 22" in line and "[reading]" in line and "[inference]" in line, line
    off = grade(log=None)["report_lines"][-len(NEW):]
    assert "no decision log read" in off[0] and all("no frames read" in line for line in off[1:])
    renamed = G.report_lines_e19(dict(g, gate={"pass": True}))
    assert any(line.startswith("gate_e19 ") for line in renamed)
    assert not any(line.startswith(("gate_e13 ", "gate_e14 ", "gate_e15 ", "gate_e16 ", "gate_e17 ", "gate_e18 "))
                   for line in renamed)
    assert G.gate_e19([]) == E.gate_e13([])
    assert all(len(line) < 2000 for line in tail)


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
    assert ns["SWING_TYPES"] == ("attack", "aim", "shove", "stomp")
    assert ns["PRESS_STEPS"] == ("swing", "shove", "stomp", "floor") and ns["HIT_STEP"] == "hit"
    assert ns["MELEE"] == "melee" and ns["STRIKE_BEFORE_S"] == 2.0
    assert ns["COUNTS"] == ("swings", "shoves", "stomps", "floors", "knockdowns", "hits")
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/e19.py's source with `edit` applied inside the top-level def or class `name` only, executed as a module
    copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\nclass %s" % name if ("\nclass %s" % name) in src else "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "e19_mutant"}
    exec(compile(src[:start] + new + src[end:], "e19_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


M = lambda: melee_fixture()["melee"]              # noqa: E731
H = lambda: melee_fixture()["hits_in_melee"]      # noqa: E731
S = lambda: melee_fixture()["melee_strike"]       # noqa: E731
C = lambda: melee_fixture()["melee_cost"]         # noqa: E731

MUTANTS = [
    # the spans and the kills
    ("_spans", lambda b: b.replace('elif st in G14.TERMINAL and s["terminal"] is None:', 'elif st == "done":'),
     lambda: M()["mean_span_s"] == 1.5),
    ("_spans", lambda b: b.replace('s["end"] = s["last"] if s["last"] is not None else s["accept"]',
                                   's["end"] = s["accept"]'), lambda: C()["inside"]["frames"] == 8),
    ("_spans", lambda b: b.replace('elif st == "progress":', 'elif st == "nothing":'),
     lambda: M()["steps"] == MELEE["steps"]),
    ("_Index", lambda b: b.replace("j -= 1", "break"), _index_case),
    ("_Index", lambda b: b.replace('if self.spans[j]["end"] >= w:', "if True:"), _index_case),
    ("_kills", lambda b: b.replace("zid in seen", "False"), lambda: H()["kills_outside"] == 1),
    ("_kills", lambda b: b.replace(" or idx.at(E._n(ln.get(\"wallMs\"))) is not None", ""),
     lambda: H()["kills_inside"] == 2),
    ("_kills", lambda b: b.replace('(t == MELEE and r.get("kill") is True)', "t == MELEE"),
     lambda: M()["kills"] == 2),
    # melee
    ("e_melee", lambda b: b.replace("st != prev", "True"), lambda: M()["steps"]["back"] == 1),
    ("e_melee", lambda b: b.replace("reversed(res)", "res"), lambda: M()["swings"] == 1),
    ("e_melee", lambda b: b.replace("G14._inc(ticks, st, E._n(n) or 0)", "G14._inc(ticks, st)"),
     lambda: M()["step_ticks"] == MELEE["step_ticks"]),
    ("e_melee", lambda b: b.replace("if not E._sent(ln, MELEE):", "if False:"), lambda: M()["resends"]["early"] == 1),
    ("e_melee", lambda b: b.replace('if ln.get("branch") != "threat":', "if False:"), lambda: M()["lines"] == 7),
    ("e_melee", lambda b: b.replace('"open" if aid not in terms and aid in accepted else ', ""),
     lambda: M()["ends"]["open"] == 1),
    ("e_melee", lambda b: b.replace(' if s["terminal"] is not None]', "]"), lambda: M()["mean_span_s"] == 1.5),
    ("e_melee", lambda b: b.replace('G14._inc(by_mode, str(E._d(a.get("args")).get("mode")))',
                                    'G14._inc(by_mode, "x")'), lambda: M()["by_mode"] == MELEE["by_mode"]),
    ("e_melee", lambda b: b.replace("i = _fight_of(fights, t0, s[\"accept\"])", "i = None"),
     lambda: M()["by_fight"] == [3, 1]),
    ("_end_key", lambda b: b.replace('"done %s" % E._d(ln.get("result")).get("end")', '"done"'),
     lambda: M()["ends"]["done time"] == 1),
    # hits_in_melee
    ("e_hits_in_melee", lambda b: b.replace("in_fight += 1 if _fight_of(fights, t0, w) is not None else 0",
                                            "in_fight += 1"), lambda: H()["outside_fight"] == 1),
    ("e_hits_in_melee", lambda b: b.replace("_per(outside, ko)", "_per(outside, ki)"),
     lambda: H()["per_kill_outside"] == 2.0),
    ("e_hits_in_melee", lambda b: b.replace("if idx.at(w) is not None:", "if False:"), lambda: H()["inside"] == 2),
    ("e_hits_in_melee", lambda b: b.replace('"per_kill": _per(len(runs), ki + ko)', '"per_kill": _per(len(runs), ko)'),
     lambda: H()["per_kill"] == 4 / 3),
    # melee_strike
    ("_step_before", lambda b: b.replace('if r.get("step") != HIT_STEP:', "if True:"),
     lambda: S()["rows"][0]["step_before"] == "swing"),
    ("_press_before", lambda b: b.replace('if r.get("step") in PRESS_STEPS:', 'if r.get("step") is not None:'),
     lambda: S()["rows"][1]["press"]["step"] == "shove"),
    ("_press_before", lambda b: b.replace("w - STRIKE_BEFORE_S * 1000.0", "w - 1e9"),
     lambda: G._press_before({"progress": [(1000.0, {"step": "swing", "d": 0.9})]}, 3500.0) is None),
    ("e_melee_strike", lambda b: b.replace("frames[i - 1]", "frames[i]"),
     lambda: S()["rows"][1]["prev_step"] == "shove"),
    ("e_melee_strike", lambda b: b.replace("if span is None:", "if False:"), lambda: S()["runs"] == 2),
    # melee_cost
    ("e_melee_cost", lambda b: b.replace("(ins if idx.at(", "(outs if idx.at("), lambda: C() == COST),
    ("_cost_side", lambda b: b.replace("max(xs)", "min(xs)"), lambda: C()["inside"]["actMs_max"] == 6),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = holds()
    except Exception:       # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real checks: E21
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _to_e18(g):
    """grade_e19's JSON as grade_e18's: the four new keys dropped, the name and the gate line renamed, the four new
    report lines dropped."""
    g = dict(g)
    for k in NEW:
        g.pop(k)
    g["grade"] = "grade_e18"
    g["report_lines"] = [("gate_e18 " + ln[len("gate_e19 "):]) if ln.startswith("gate_e19 ") else ln
                         for ln in g["report_lines"][:-len(NEW)]]
    return g


def test_grade_e19_on_e21_keeps_every_grade_e18_key_as_the_committed_e_grade_txt_and_reads_no_melee():
    """E21 ran survival iteration 21 on PZA/1.7.2 (no melee sent, no frame `act.step`): the melee reads zero over its
    twelve fights, its four kills all outside a span (the inherited `kills.planner`), its frames all outside a span."""
    p = os.path.join(E21, "e_day_21.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E21)
    out = EG19.load(p)
    g = G.grade_e19(out, None, EG19.load_log(p), state_dir=EG19._dir(p))
    mine = json.loads(json.dumps(EG19.finite(g), sort_keys=True, allow_nan=False))
    assert g["grade"] == "grade_e19" and len(out["loop"]["fights"]) == 12
    assert g["melee"] == _zero_melee(12)
    hm = g["hits_in_melee"]
    k = g["kills"]["planner"]
    assert (hm["inside"], hm["kills_inside"], hm["kills_outside"], hm["kills"]) == (0, 0, 4, 4) == (0, 0, k, k)
    assert hm["per_kill"] == hm["per_kill_outside"] == g["hits"]["per_kill"] == 0.0
    assert hm["runs"] == hm["outside"] == g["hits"]["runs"]
    assert g["melee_strike"]["runs"] == 0 and g["melee_cost"]["inside"]["frames"] == 0
    assert g["melee_cost"]["outside"]["frames"] == len(E._frame_index(E.session_lines(E21)[0])[1])
    _, committed = _committed(E21, "e_grade.txt")
    assert _to_e18(mine) == committed


def test_e_grade_19_prints_the_committed_e_grade_txt_s_lines_then_the_four_new_ones():
    """`e_grade_19.py` on the committed E21 artifact: the committed `e_grade.txt`'s report lines (CRLF folded, a gate
    line renamed), then the four new lines, then the JSON whose inherited keys equal the committed."""
    p = os.path.join(E21, "e_day_21.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E21)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_19.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(E21, "e_grade.txt")
    assert [("gate_e18 " + ln[len("gate_e19 "):]) if ln.startswith("gate_e19 ") else ln
            for ln in printed[:-len(NEW)]] == want_lines and len(printed) == len(want_lines) + len(NEW)
    assert got["grade"] == "grade_e19" and printed[-len(NEW):] == got["report_lines"][-len(NEW):]
    assert _to_e18(got) == want


def test_e_grade_19_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5: a driver's refusal is tested without invoking it on a bad argument): its
    main answers usage, exit 2, on no path or more than two outside `--chain`."""
    src = open(EG19.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e19 import gate_e19, grade_e19, report_lines_e19" in src
    body = src[src.index('"""', 3):]
    assert "usage: e_grade_19.py" in src and "e18" not in body and "_e18" not in body
