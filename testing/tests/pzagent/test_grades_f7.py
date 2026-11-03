"""base/grades/f7.py (Plan 26 Task 4), offline: `grade_f7` and its three readings of the LLM source's fourth round (the
all-looted line P26-G, every object parsed P26-F, the re-ask once P26-H), each on a fabricated goals log where it counts
and a clean one where it reads zero, a mutant per reading, every `grade_f6` key unchanged under `grade_f7` on
test_gates_f6's artifact (F3, `f_goals_4-20261030-114742`), and the real check on F7 (`f_goals_8-20261102-093241`): call
8's two objects, no `open:` line (P26-G landed after F7) beside its 33 all-looted views, no re-ask, and every grade_f6
key equal to the committed `f_grade.txt`'s."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_f as F
from agent.base.grades import f7 as G
from agent.drivers import f_grade_6 as FG6
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F7 = os.path.join(TESTING, "artifacts", "f_goals_8-20261102-093241")
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
NEW = ("open_views", "objects", "reasks")

LOOTED = "buildings: 2 @10720,10637 door 10721,10638 11.9 c25 Lv h:- z:0; 3 @10738,10634 door - 30.2 c10 L h:- z:0"
MIXED = "buildings: 2 @10720,10637 door 10721,10638 11.9 c25 Lv h:- z:0; 3 @10738,10634 door - 30.2 c10 v h:- z:0"
OPEN = 'open: ["ExploreToward","Stock"]'


def prompt(*lines):
    return "\n".join(('pos: {"x":10708.5,"y":10638.5,"z":0}', "hour: 9.8") + lines)


def goal_row(goal=None, error=None, answer='{"type":"Rest"}', p=prompt(), cycle=None, reask=None, skipped=None):
    r = {"answer": answer, "error": error, "goal": goal, "ok": goal is not None, "prompt": p, "latency_s": 4.0,
         "model": "sonnet", "prompt_bytes": len(p), "answer_bytes": len(answer or "")}
    if cycle is not None:
        r.update(cycle=cycle, reask=bool(reask), skipped=list(skipped or []))
    return r


def grade(rows, **llm):
    a = art()
    if llm:
        a["loop"]["llm"] = dict(llm, calls=[])
    return G.grade_f7(a, goal_lines=rows)


# ================================================================ P26-G, the all-looted line
def open_fixture(flag=True):
    """Four views carrying the `open:` line (one taken, a refusal re-asked and refused again, a timeout), one all-looted
    view without it, one with an unlooted building."""
    o = (OPEN,) if flag else ()
    rows = [goal_row({"type": "ExploreToward", "x": 1, "y": 2}, p=prompt(LOOTED, *o), cycle=1),
            goal_row(error="invalid: looted already", p=prompt(LOOTED, *o), cycle=2),
            goal_row(error="invalid: out of range", p=prompt(LOOTED, *o), cycle=2, reask=True),
            goal_row(error="timeout", answer=None, p=prompt(LOOTED, *o), cycle=3),
            goal_row({"type": "Stock"}, p=prompt(LOOTED), cycle=4),
            goal_row({"type": "LootBuilding", "building": 3}, p=prompt(MIXED), cycle=5)]
    return grade(rows)["open_views"]


def test_the_open_views_count_the_open_line_the_answers_on_it_and_the_all_looted_views_without_it():
    g = open_fixture()
    assert g["read"] is True and g["n"] == 4 and g["taken"] == {"ExploreToward": 1}
    assert g["refused"] == {"looted already": 1, "out of range": 1} and g["other"] == {"timeout": 1}
    assert g["stand_in"] == 2                 # the re-ask's refusal and the timeout; the first refusal was re-asked
    assert (g["all_looted"], g["all_looted_no_open"]) == (5, 1)


def test_the_open_views_read_zero_without_the_line_and_unread_without_a_goals_log():
    g = open_fixture(flag=False)
    assert (g["n"], g["taken"], g["refused"], g["other"], g["stand_in"]) == (0, {}, {}, {}, 0)
    assert (g["all_looted"], g["all_looted_no_open"]) == (5, 5)
    assert G.grade_f7(art())["open_views"] == {"read": False}


def test_an_open_line_is_its_own_view_line_never_a_mention_of_the_key():
    assert G._has_open(prompt(OPEN)) and not G._has_open(prompt("note: open: []")) and not G._has_open("reopen: 1")
    assert G._all_looted(prompt(LOOTED)) and not G._all_looted(prompt(MIXED)) and not G._all_looted(prompt())


# ================================================================ P26-F, every object parsed
F7_CALL_8 = ('{"type":"LootBuilding","building":2}\n\nWait—building 2 is listed as "Lv" (looted flag L), so it can\'t '
             'be named.\n\n{"type":"ExploreToward","x":10704,"y":10640}')


THREE = '{"type":"Bogus"} {"type":"Stock"} {"type":"LootBuilding","building":3}'
THREE_SKIPPED = [{"goal": {"type": "Stock"}, "why": "refused"},
                 {"goal": {"type": "LootBuilding", "building": 3}, "why": "looted already"},
                 {"goal": None, "why": "unknown type"}]


def objects_fixture(flag=True):
    loot = {"type": "LootBuilding", "building": 2}
    rows = [goal_row({"type": "ExploreToward", "x": 10704, "y": 10640}, answer=F7_CALL_8 if flag else '{"type":"Rest"}',
                     cycle=1, skipped=[{"goal": loot, "why": "looted already"}] if flag else []),
            goal_row({"type": "Rest"}, cycle=2),
            goal_row(error="malformed", answer="no json here", cycle=3),
            goal_row(error="invalid: refused", cycle=4, answer=THREE if flag else '{"type":"Stock"}',
                     skipped=THREE_SKIPPED if flag else THREE_SKIPPED[:1]),
            goal_row(error="timeout", answer=None, cycle=5)]
    return grade(rows)["objects"]


def test_the_objects_count_every_object_per_answer_the_skipped_by_why_and_the_take_after_a_skip():
    g = objects_fixture()
    assert g["read"] is True and g["answers"] == 5 and g["per_answer"] == {"2": 1, "1": 1, "0": 2, "3": 1}
    assert (g["multi"], g["multi_calls"]) == (2, [1, 4])
    assert g["skipped_by_why"] == {"looted already": 2, "refused": 1, "unknown type": 1}
    assert (g["skipped_invalid"], g["taken_after_skip"]) == (1, 1)


def _taken_with_only_an_invalid_object_skipped():
    """`{"type":"Rest"} {"type":"Bogus"}`: the Rest taken, the Bogus invalid (`goal` None, wherever it stood)."""
    rows = [goal_row({"type": "Rest"}, answer='{"type":"Rest"} {"type":"Bogus"}', cycle=1,
                     skipped=[{"goal": None, "why": "unknown type"}])]
    return grade(rows)["objects"]


def test_an_invalid_object_after_the_taken_one_is_no_earlier_skip():
    g = _taken_with_only_an_invalid_object_skipped()
    assert g["per_answer"] == {"2": 1} and (g["skipped_invalid"], g["taken_after_skip"]) == (1, 0)


def test_the_objects_read_one_object_per_answer_without_a_second_and_unread_without_a_goals_log():
    g = objects_fixture(flag=False)
    assert g["per_answer"] == {"1": 3, "0": 2} and (g["multi"], g["multi_calls"]) == (0, [])
    assert (g["skipped_by_why"], g["skipped_invalid"], g["taken_after_skip"]) == ({"refused": 1}, 0, 0)
    assert G.grade_f7(art())["objects"] == {"read": False}


# ================================================================ P26-H, the re-ask once
def reask_fixture(flag=True, **llm):
    if not flag:
        rows = [goal_row(error="invalid: looted already"), goal_row({"type": "Rest"})]
        return grade(rows, **llm)["reasks"]
    rows = [goal_row(error="invalid: looted already", cycle=1),
            goal_row({"type": "ExploreToward", "x": 1, "y": 2}, cycle=1, reask=True),
            goal_row(error="invalid: looted already", cycle=2),
            goal_row(error="invalid: out of range", cycle=2, reask=True),
            goal_row(error="invalid: refused", cycle=4, reask=True),          # no first call before it
            goal_row({"type": "Rest"}, cycle=3)]
    return grade(rows, **llm)["reasks"]


def test_the_reasks_count_the_cycles_re_asked_the_takes_the_stand_ins_and_the_artifact_s_total():
    g = reask_fixture(reasks_total=3)
    assert g["read"] is True and (g["n"], g["taken"], g["stand_in"], g["unpaired"], g["cycles"]) == (3, 1, 2, 1, 4)
    assert (g["reasks_total"], g["agree"]) == (3, True)
    assert reask_fixture(reasks_total=2)["agree"] is False
    assert (reask_fixture()["reasks_total"], reask_fixture()["agree"]) == (None, None)


def test_the_reasks_read_zero_on_a_third_round_log_and_unread_without_a_goals_log():
    g = reask_fixture(flag=False)
    assert (g["n"], g["taken"], g["stand_in"], g["unpaired"], g["cycles"], g["agree"]) == (0, 0, 0, 0, None, None)
    assert G.grade_f7(art())["reasks"] == {"read": False}


# ================================================================ the report and the gate
def test_report_lines_f7_are_report_lines_f6_then_one_line_per_rule():
    g = grade([goal_row({"type": "Rest"})])
    tail = g["report_lines"][-len(NEW):]
    assert g["report_lines"][:-len(NEW)] == F.report_lines_f6(g)
    for line, tag in zip(tail, ("P26-G", "P26-F", "P26-H")):
        assert ("(%s)" % tag) in line and "[reading]" in line
    off = G.grade_f7(art())["report_lines"][-len(NEW):]
    assert all("no goals.log read" in line for line in off)
    assert G.gate_f7([]) == F.gate_f6([])


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/f7.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "f7_mutant"}
    exec(compile(src[:start] + new + src[end:], "f7_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    ("f_open_views", lambda b: b.replace("_stand_in(r, e) else", 'r.get("ok") is not True else'),
     lambda: open_fixture()["stand_in"] == 2),
    ("f_open_views", lambda b: b.replace("if not _has_open(p):\n", "if False:\n"), lambda: open_fixture()["n"] == 4),
    ("_has_open", lambda b: b.replace("ln.startswith(OPEN_LINE)", "OPEN_LINE in ln"),
     lambda: not G._has_open(prompt("note: open: []"))),
    ("_all_looted", lambda b: b.replace("bool(shown) and ", ""), lambda: not G._all_looted(prompt())),
    ("_ends_cycle", lambda b: b.replace("last[k] == i", "True"), lambda: open_fixture()["stand_in"] == 2),
    ("f_objects", lambda b: b.replace("if k >= 2 else", "if k > 2 else"), lambda: objects_fixture()["multi"] == 2),
    ("f_objects", lambda b: b.replace('invalid += 1 if s.get("goal") is None else 0', "invalid += 1"),
     lambda: objects_fixture()["skipped_invalid"] == 1),
    ("f_objects", lambda b: b.replace('any(s.get("goal") is not None for s in sk)', "sk"),
     lambda: objects_fixture()["taken_after_skip"] == 1 and
     _taken_with_only_an_invalid_object_skipped()["taken_after_skip"] == 0),
    ("f_objects", lambda b: b.replace('r.get("ok") is True and any', "any"),
     lambda: objects_fixture()["taken_after_skip"] == 1),
    ("f_reasks", lambda b: b.replace("firsts[_cycle_key(i, r)] < i", "True"),
     lambda: _a_reask_before_its_first_is_unpaired()),
    ("f_reasks", lambda b: b.replace("(tot == len(re_))", "(tot == 0)"),
     lambda: reask_fixture(reasks_total=3)["agree"] is True),
    ("f_reasks", lambda b: b.replace('if r.get("ok") is not True), "unpaired"', 'if r.get("ok") is False), "unpaired"'),
     lambda: _a_reask_with_ok_missing_is_a_stand_in()),
    ("_cycle_key", lambda b: b.replace('("c", c) if', '("i", i) if'), lambda: open_fixture()["stand_in"] == 2),
]


def _a_reask_before_its_first_is_unpaired():
    rows = [goal_row(error="invalid: refused", cycle=1, reask=True), goal_row(error="invalid: refused", cycle=1)]
    return grade(rows)["reasks"]["unpaired"] == 1


def _a_reask_with_ok_missing_is_a_stand_in():
    r = goal_row(error="timeout", cycle=1, reask=True)
    del r["ok"]
    return grade([goal_row(error="invalid: refused", cycle=1), r])["reasks"]["stand_in"] == 1


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


# ================================================================ the committed artifacts
def _grade(d, name, fn):
    p = os.path.join(d, name + ".json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    with open(p, encoding="utf-8") as fh:
        out = json.load(fh)
    return fn(out, None, FG6.load_log(p), state_dir=d, goal_lines=FG6.load_goals(p))


def test_grade_f7_on_f3_reads_every_grade_f6_key_unchanged():
    g6, g7 = _grade(F3, "f_goals_4", F.grade_f6), _grade(F3, "f_goals_4", G.grade_f7)
    skip = ("grade", "report_lines") + NEW
    assert g7["grade"] == "grade_f7" and all(g7[k]["read"] is True for k in NEW)
    assert {k: v for k, v in g6.items() if k not in skip} == {k: v for k, v in g7.items() if k not in skip}
    assert g7["report_lines"][:-len(NEW)] == g6["report_lines"]


def test_grade_f7_on_f7_reads_call_8_s_two_objects_no_open_line_no_reask_and_grade_f6_as_committed():
    g = _grade(F7, "f_goals_8", G.grade_f7)
    o, b, r = (g[k] for k in NEW)
    assert b["answers"] == 40 and b["per_answer"] == {"1": 39, "2": 1} and b["multi_calls"] == [8]
    assert b["skipped_by_why"] == {} and b["taken_after_skip"] == 0      # F7's rows carry no `skipped` (P26-F after F7)
    # P26-G landed after F7: no view carries the line, and the review of Task 3's 33 all-looted views read here
    assert (o["n"], o["all_looted"], o["all_looted_no_open"]) == (0, 33, 33)
    assert (r["n"], r["taken"], r["stand_in"], r["cycles"], r["reasks_total"]) == (0, 0, 0, None, None)
    text = open(os.path.join(F7, "f_grade.txt"), encoding="utf-8").read()
    committed = json.loads(text[text.index("\n{\n"):])
    mine = json.loads(json.dumps(FG6.finite({k: v for k, v in g.items() if k not in NEW}), sort_keys=True,
                                 allow_nan=False))
    mine["grade"] = "grade_f6"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed


F8 = os.path.join(TESTING, "artifacts", "f_goals_9-20261102-181937")
F9 = os.path.join(TESTING, "artifacts", "f_goals_10-20261102-231705")


def test_f_grade_7_on_f8_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_7.py` on the committed F8 artifact reproduces its committed `f_grade.txt`
    byte for byte (CRLF folded), so a drift in a live planner name the frozen grade reads
    (`llm.objects`, `view.OPEN_KEY`) fails here."""
    p = os.path.join(F8, "f_goals_9.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F8)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_7.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F8, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want


def test_f_grade_7_on_f9_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_7.py` on the committed F9 artifact reproduces its committed `f_grade.txt`
    byte for byte (CRLF folded), so a drift in a live planner name the frozen grade reads
    (`llm.objects`, `view.OPEN_KEY`) fails here."""
    p = os.path.join(F9, "f_goals_10.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F9)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_7.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F9, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
