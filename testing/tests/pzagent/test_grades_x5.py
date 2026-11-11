"""base/grades/x5.py (Plan 35 Task 5), offline: `grade_x5` and its footwork readings (`work`: the melee's work,
cornered and pile step entries, the headings' turns, the cornered ticks and the pile's episodes, shoves and
knock-downs; `contact`: the frames' contact seconds inside the engagements, per engagement, with the hits inside them;
`handbacks`: the engagements' hand-backs by why; `engage_hold`: the planner's holds by rule; `withdraw`: the withdraw
vector's lines, melee sends and re-sends), each on a fabricated ring where it counts, its unread case and a mutant of
each reading that its fixture fails (each mutant named in the MUTANTS list's comment); every grade_x4 key kept under
`grade_x5` on the committed F20 (`f_goals_20-20261109-155512`, Plan 34's evidence session, the first graded through
grade_x4) with every footwork reading empty (F20 ran before PZA/1.13: no melee carries `work`, no line `engage_hold`
or `withdraw`), through the function and through the regrade script `f_grade_17.py`, whose grade_x4 part reproduces
F20's committed `f_grade.txt` byte for byte."""
import functools
import hashlib
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x4 as GX4
from agent.base.grades import x5 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import f_grade_15 as FG15
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_x2 import fr, ordered, rec, zr
from .test_grades_x4 import dline

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F20 = os.path.join(TESTING, "artifacts", "f_goals_20-20261109-155512")


def mel(aid, t, state="progress", step=None, work=None, press=None, **res):
    """A melee act line `t` seconds in: its step, its `work` leaf ({heading, turn}) and press leaf when given."""
    r = dict(res)
    if step is not None:
        r["step"] = step
    if work is not None:
        r["work"] = dict(work, clear=True, gap=0.5, n=1)
        r["contact"] = 0
    if press is not None:
        r["press"] = press
    return actl(aid, "melee", state, t, r)


def wl(heading, turn):
    return {"heading": heading, "turn": turn}


def knock(k):
    return {"d_press": 0.5, "knock": k, "knock_p": 0.3, "cut_by": ""}


# ================================================================ work
def work_case():
    """Three melees. m1 (under work): face (heading 10, turn 0), a work run of two lines (the second turned 30), a
    swing, a second work run (the same leaf), cornered (turn 180), a shove, a pile run of two lines whose first carries
    the shove's leaf knocked down, a swing, a shove carrying a knocked-down leaf, a pile line with no leaf (the leaf read
    off the line before), done handback floor with steps {work 40, cornered 7, pile 12} (the leaf unchanged). m2 (under
    work): work (heading 5, turn -30), a pile line whose leaf did not knock down, done handback clear with steps
    {cornered 3}. m3 (no work leaf): face, done kill with steps {face 5}."""
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="face", work=wl(10.0, 0)),
            mel("m1", 1.2, step="work", work=wl(10.0, 0)), mel("m1", 1.3, step="work", work=wl(40.0, 30)),
            mel("m1", 1.4, step="swing"), mel("m1", 1.5, step="work", work=wl(40.0, 30)),
            mel("m1", 1.6, step="cornered", work=wl(200.0, 180)), mel("m1", 1.7, step="shove"),
            mel("m1", 1.8, step="pile", press=knock(True)), mel("m1", 1.9, step="pile"),
            mel("m1", 2.0, step="swing"), mel("m1", 2.1, step="shove", press=knock(True)), mel("m1", 2.2, step="pile"),
            mel("m1", 2.3, "done", work=wl(200.0, 180), end="handback", why="floor",
                steps={"work": 40, "cornered": 7, "pile": 12}),
            mel("m2", 3.0, "accepted"), mel("m2", 3.1, step="work", work=wl(5.0, -30)),
            mel("m2", 3.2, step="pile", press=knock(False)), mel("m2", 3.3, "done", end="handback", why="clear",
                                                                 steps={"cornered": 3}),
            mel("m3", 4.0, "accepted"), mel("m3", 4.1, step="face"), mel("m3", 4.2, "done", end="kill",
                                                                         steps={"face": 5})]
    return rec(), None, ordered(acts)


def _work():
    return G.readings_x5(*work_case())["work"]


def test_work_reads_the_step_entries_turns_cornered_ticks_and_the_pile():
    w = _work()
    assert w == {"read": True, "steps": {"work": 3, "cornered": 1, "pile": 3},
                 "turns": {"0": 1, "30": 1, "-30": 1, "180": 1}, "cornered_ticks": 10,
                 "pile": {"episodes": 2, "shoves": 3, "knockdowns": 2}}


def test_work_is_unread_without_an_act_line_and_empty_without_a_work_step():
    assert G.readings_x5(rec(), None, [fr(1.0, 0.0)])["work"] == {"read": False}
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="face"), mel("m1", 1.2, step="swing"),
            mel("m1", 1.3, "done", end="kill", steps={"face": 3, "swing": 4})]
    assert G.readings_x5(rec(), None, acts)["work"] == {
        "read": True, "steps": {"work": 0, "cornered": 0, "pile": 0}, "turns": {}, "cornered_ticks": 0,
        "pile": {"episodes": 0, "shoves": 0, "knockdowns": 0}}


# ================================================================ contact
def zs(d, **kw):
    z = zr(7, 10.0 + d, 10.0)
    z.update(kw)
    return z


def cf(t, d=None, step=None, reaction="", extra=()):
    """A frame `t` seconds in with one zombie `d` tiles east (none when None), the act's step, the reaction."""
    f = fr(t, 0.0, zs=([zs(d)] if d is not None else []) + list(extra),
           act={"aid": "m1", "state": "progress", "step": step} if step else None)
    f["me"]["hitReaction"] = reaction
    return f


def contact_case():
    """m1 (under work) from 1.0 to 3.0 s, m3 (no work) from 4.5 to 5.0 s; frames every 0.1 s from 0.8 to 3.0, then from
    4.5 to 5.0 (the frame at 3.0 standing FRAME_CAP_S, 1.0 s, of its 1.5 s gap). Contact inside m1: 1.0 to 1.4 (five
    frames at 0.5 tiles), 1.9 (0.9 tiles) and 3.0 (0.5): 1.6 s over seven frames. Not contact: 0.8 and 0.9 (before the
    span), 1.5 (a swing in flight), 1.6 (a crawler at 0.5, the standing one at 1.5), 1.7 (one on the floor at 0.5), 1.8
    (1.0 tiles exactly), 2.0 and 2.1 (a Bite: its onset after the contact frame 1.9, a hit inside), 2.2 (3 tiles), 2.3 (a
    second onset after 2.2: a hit, not inside), 2.4 to 2.9 (none near). m3's 4.5 to 4.7 contact and its onset at 4.8
    after it are no engagement's."""
    fs = [cf(0.8, 0.5), cf(0.9, 0.5)] + [cf(1.0 + k / 10.0, 0.5) for k in range(5)]
    fs += [cf(1.5, 0.5, step="swing"), cf(1.6, 1.5, extra=[dict(zs(0.5), id=8, crawler=True)]),
           cf(1.7, 1.5, extra=[dict(zs(0.5), id=9, onFloor=True)]), cf(1.8, 1.0), cf(1.9, 0.9),
           cf(2.0, 0.5, reaction="Bite"), cf(2.1, 0.5, reaction="Bite"), cf(2.2, 3.0), cf(2.3, 3.0, reaction="Bite")]
    fs += [cf(2.4 + k / 10.0, None) for k in range(6)] + [cf(3.0, 0.5)]
    fs += [cf(4.5, 0.5), cf(4.6, 0.5), cf(4.7, 0.5), cf(4.8, 0.5, reaction="Bite"), cf(4.9, None), cf(5.0, None)]
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="face", work=wl(0.0, 0)),
            mel("m1", 3.0, "done", work=wl(0.0, 0), end="kill", steps={"face": 9}),
            mel("m3", 4.5, "accepted"), mel("m3", 4.6, step="face"), mel("m3", 5.0, "done", end="kill")]
    return rec(), None, ordered(fs, acts)


def _contact():
    return G.readings_x5(*contact_case())["contact"]


def test_contact_reads_the_seconds_inside_the_engagements_and_the_hits_inside_contact():
    c = _contact()
    assert (c["read"], c["frames"], c["engagements"], c["hits_inside"]) == (True, 7, 1, 1)
    assert c["seconds"] == pytest.approx(1.6, abs=0.01)
    assert [(e["aid"], e["hits"], e["hits_inside"]) for e in c["per_engagement"]] == [("m1", 2, 1)]
    assert c["per_engagement"][0]["seconds"] == pytest.approx(1.6, abs=0.01)


def test_contact_is_the_scorecards_definition_copied():
    """The frozen copy reads, frame by frame, what tools/trial_score.py's live `_in_contact` reads (the copy's source),
    and the scorecard's `contact_seconds` engagement for m1 is this reading's per-engagement seconds."""
    sys.path.insert(0, os.path.join(os.path.dirname(TESTING), "tools"))
    import trial_score as TS
    from agent.base import gates_e as E
    out, rows, lines = contact_case()
    frames = E._frame_index(lines)[1]
    assert [G.in_contact(f) for f in frames] == [TS._in_contact(f) for f in frames]
    live = {e["aid"]: e["seconds"] for e in TS.contact_seconds(frames, lines)["engagements"]}
    assert live["m1"] == pytest.approx(_contact()["per_engagement"][0]["seconds"])
    assert (G.CONTACT_R, G.FRAME_CAP_S, G.STRIKE_STEPS) == (TS.CONTACT_R, TS.FRAME_CAP_S, TS.STRIKE_STEPS)


def test_contact_is_unread_without_a_frame():
    assert G.readings_x5(rec(), None, [mel("m1", 1.0, "accepted")])["contact"] == {"read": False}


# ================================================================ handbacks
def handback_case():
    """m1 and m2 (under work) done handback floor and clear; m4 (under work) done handback floor; m5 (under work) done
    lost (no hand-back); m6 (under work) failed superseded; m3 (no work) done handback standing (no engagement's)."""
    acts = [mel("m1", 1.0, step="work", work=wl(0.0, 0)), mel("m1", 1.5, "done", end="handback", why="floor"),
            mel("m2", 2.0, step="work", work=wl(0.0, 0)), mel("m2", 2.5, "done", end="handback", why="clear"),
            mel("m4", 3.0, step="face", work=wl(0.0, 0)), mel("m4", 3.5, "done", end="handback", why="floor"),
            mel("m5", 4.0, step="face", work=wl(0.0, 0)), mel("m5", 4.5, "done", end="lost", why="out of range"),
            mel("m6", 5.0, step="face", work=wl(0.0, 0)), mel("m6", 5.5, "failed", end="handback", why="crowd"),
            mel("m3", 6.0, step="face"), mel("m3", 6.5, "done", end="handback", why="standing")]
    return rec(), None, ordered(acts)


def _handbacks():
    return G.readings_x5(*handback_case())["handbacks"]


def test_handbacks_read_the_engagements_handbacks_by_why():
    assert _handbacks() == {"read": True, "lines": 3, "by_why": {"floor": 2, "clear": 1}}


# ================================================================ engage_hold
def hold_case():
    """Five lines: the Fight's hold nested (retreat_gap); the threat's many beside a nested crawler_clear; many twice on
    one line (counted once); none; a care hold carried as a bare string (read as its rule)."""
    rows = [dline(1.0, {"fight": {"engage_hold": {"rule": "retreat_gap"}}}),
            dline(1.5, {"engage_hold": {"rule": "many"}, "fight": {"engage_hold": {"rule": "crawler_clear"}}}),
            dline(2.0, {"engage_hold": {"rule": "many"}, "leave": {"engage_hold": {"rule": "many"}}}),
            dline(2.5, {"flee": "many"}),
            dline(3.0, {"care_commit": {"engage_hold": "care"}})]
    return rec(), rows, []


def _hold():
    return G.readings_x5(*hold_case())["engage_hold"]


def test_engage_hold_reads_its_lines_by_rule():
    assert _hold() == {"read": True, "lines": 4, "by_rule": {"retreat_gap": 1, "many": 2, "crawler_clear": 1,
                                                            "care": 1}}


# ================================================================ withdraw
def withdraw_case():
    """Seven lines: a melee at 1 sent with the withdraw vector (a send, not a re-send); a line carrying it with no send;
    a melee at 1 re-sent with it (a re-send); a melee at 2 with it (a send at a new target); a melee at 3 with no vector
    (a send that sets the target the next send is compared with); a melee at 3 with it (a re-send); a line whose
    withdraw is None (not carried)."""
    m = {"maneuver": "melee"}
    rows = [dline(1.0, {"fight": dict(m, withdraw=[1.0, 0.0])}, "melee", targetId=1, mode="strike"),
            dline(1.5, {"fight": dict(m, withdraw=[1.0, 0.0])}),
            dline(2.0, {"fight": dict(m, withdraw=[0.0, 1.0])}, "melee", targetId=1, mode="strike"),
            dline(2.5, {"fight": dict(m, withdraw=[0.0, 1.0])}, "melee", targetId=2, mode="strike"),
            dline(3.0, {"fight": dict(m)}, "melee", targetId=3, mode="strike"),
            dline(3.5, {"fight": dict(m, withdraw=[-1.0, 0.0])}, "melee", targetId=3, mode="strike"),
            dline(4.0, {"fight": dict(m, withdraw=None)})]
    return rec(), rows, []


def _withdraw():
    return G.readings_x5(*withdraw_case())["withdraw"]


def test_withdraw_reads_its_lines_sends_and_resends():
    assert _withdraw() == {"read": True, "lines": 5, "sends": 4, "resends": 2}


# ================================================================ the module's cases
def test_the_decision_readings_are_unread_without_a_decision_log():
    g = G.readings_x5(rec(), None, [fr(1.0, 0.0)])
    for k in ("engage_hold", "withdraw", "work", "handbacks"):
        assert g[k] == {"read": False}, k


def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = hold_case()
    out["stop"]["wallS"] = 1.6 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    assert G.readings_x5(out, rows, lines)["engage_hold"]["lines"] == 2


def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    ns = vars(G)
    assert (ns["CONTACT_R"], ns["FRAME_CAP_S"], ns["STRIKE_STEPS"]) == (1.0, 1.0, ("swing", "shove", "stomp", "floor"))
    assert ns["WORK_STEPS"] == ("work", "cornered", "pile")
    assert ns["WORK_TURNS"] == (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180)
    assert (ns["ENGAGE_HOLD"], ns["RULE"], ns["WITHDRAW"]) == ("engage_hold", "rule", "withdraw")
    assert ns["NEW"] == ("work", "contact", "handbacks", "engage_hold", "withdraw")


def test_the_frozen_copies_match_their_live_sources_at_this_commit():
    """The copies' sources read at the commit the module was written on: the planner's STRIKE_STEPS and the Lua's
    K.WORK_TURNS (a later change of either is the next grade's to fold in, never this module's)."""
    from agent.base.planner.maneuvers import melee as PM
    assert G.STRIKE_STEPS == PM.STRIKE_STEPS
    lua = open(os.path.join(TESTING, "PZAgent", "PZAgent", "42", "media", "lua", "client", "PZAgent_StanceWork.lua"),
               encoding="utf-8").read()
    assert "K.WORK_TURNS = { 0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180 }" in lua
    assert "K.WORK_CONTACT_R = 1.0" in lua


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x5.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x5_mutant"}
    exec(compile(src[:start] + new + src[end:], "x5_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


WORK_WANT = test_work_reads_the_step_entries_turns_cornered_ticks_and_the_pile
CONTACT_WANT = test_contact_reads_the_seconds_inside_the_engagements_and_the_hits_inside_contact

MUTANTS = [
    # work: every progress line counted as an entry (no runs)
    ("e_work", lambda b: b.replace("steps[s] += 1", "steps[s] += len(idx)"), WORK_WANT),
    # work: consecutive progress lines merged whatever their step (no run per step)
    ("step_runs", lambda b: b.replace("if runs and runs[-1][0] == s:", "if runs:"), WORK_WANT),
    # work: an off-by-one step filter (the pile step left out)
    ("e_work", lambda b: b.replace("if s not in steps:", "if s not in (WORK, CORNERED):"), WORK_WANT),
    # work: the turns read off every line carrying the leaf (no heading change)
    ("e_work", lambda b: b.replace("if key != last and ", "if "), lambda: _work()["turns"] == {
        "0": 1, "30": 1, "-30": 1, "180": 1}),
    # work: the shove's leaf read only on the pile entry's own line
    ("e_work", lambda b: b.replace("if not press and first > 0:", "if False:"),
     lambda: _work()["pile"]["knockdowns"] == 2),
    # work: the knock read as any leaf present
    ("e_work", lambda b: b.replace('press.get("knock") is True', 'bool(press)'),
     lambda: _work()["pile"]["knockdowns"] == 2),
    # work: the cornered ticks off the wrong key
    ("e_work", lambda b: b.replace(".get(CORNERED)) or 0", ".get(WORK)) or 0"), lambda: _work()["cornered_ticks"] == 10),
    # work: an episode per pile entry
    ("e_work", lambda b: b.replace("episodes += 1 if piles else 0", "episodes += piles"),
     lambda: _work()["pile"]["episodes"] == 2),
    # contact: a crawler read as standing
    ("standing_z", lambda b: b.replace('not z.get("crawler") and ', ""), CONTACT_WANT),
    # contact: a press in flight read as contact
    ("in_contact", lambda b: b.replace('E._d(f.get("act")).get("step") in STRIKE_STEPS or ', ""), CONTACT_WANT),
    # contact: the radius inclusive
    ("in_contact", lambda b: b.replace("min(ds) < CONTACT_R", "min(ds) <= CONTACT_R"), CONTACT_WANT),
    # contact: no cap on a frame's seconds
    ("frame_seconds", lambda b: b.replace("min(max(d, 0.0), FRAME_CAP_S * 1000.0)", "max(d, 0.0)"), CONTACT_WANT),
    # contact: every melee an engagement
    ("e_contact", lambda b: b.replace("if s[\"aid\"] in work_aids", "if True"), CONTACT_WANT),
    # contact: a hit counted outside the contact (every onset in the span)
    ("e_contact", lambda b: b.replace("oi = [a for a in o if a - 1 in hot]", "oi = list(o)"), CONTACT_WANT),
    # contact: the onset's own frame read for contact
    ("e_contact", lambda b: b.replace("a - 1 in hot", "a in hot"), CONTACT_WANT),
    # contact: the span's end exclusive
    ("e_contact", lambda b: b.replace('<= walls[i] <= s["end"]', '<= walls[i] < s["end"]'), CONTACT_WANT),
    # handbacks: every melee's
    ("e_handbacks", lambda b: b.replace("if not under_work(lns):", "if False:"),
     test_handbacks_read_the_engagements_handbacks_by_why),
    # handbacks: any end's why
    ("e_handbacks", lambda b: b.replace(' and res.get("end") == HANDBACK', ""),
     test_handbacks_read_the_engagements_handbacks_by_why),
    # handbacks: a failed line's
    ("e_handbacks", lambda b: b.replace('ln.get("state") == DONE and ', ""),
     test_handbacks_read_the_engagements_handbacks_by_why),
    # handbacks: the engagement read off a wrong leaf key
    ("under_work", lambda b: b.replace(".get(WORK)", ".get(\"contact\")"),
     test_handbacks_read_the_engagements_handbacks_by_why),
    # engage_hold: only the threat why's own key
    ("e_engage_hold", lambda b: b.replace("carries(why, ENGAGE_HOLD)", "ENGAGE_HOLD in why"),
     test_engage_hold_reads_its_lines_by_rule),
    # engage_hold: a rule counted per occurrence, not per line
    ("e_engage_hold", lambda b: b.replace("if rule not in seen:", "if True:"), test_engage_hold_reads_its_lines_by_rule),
    # engage_hold: the first value only
    ("values_of", lambda b: b.replace("out.extend(values_of(v, key))", "pass", 1),
     test_engage_hold_reads_its_lines_by_rule),
    # withdraw: a None vector carried
    ("_pair", lambda b: b.replace("len(v) == 2 and ", "").replace("isinstance(v, (list, tuple)) and ", "True or "),
     test_withdraw_reads_its_lines_sends_and_resends),
    # withdraw: a re-send read off the target of the last vector-carrying send only
    ("e_withdraw", lambda b: b.replace("        prev = args.get(TARGET_ID)\n", "").replace(
        "resends += 1 if prev is not None and args.get(TARGET_ID) == prev else 0",
        "resends += 1 if prev is not None and args.get(TARGET_ID) == prev else 0\n            prev = args.get(TARGET_ID)"),
     test_withdraw_reads_its_lines_sends_and_resends),
    # withdraw: every melee send counted
    ("e_withdraw", lambda b: b.replace("        if carried:\n            sends += 1", "        if True:\n            sends += 1"),
     test_withdraw_reads_its_lines_sends_and_resends),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, holds = MUTANTS[n]
    assert holds() is not False, "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = holds() is not False
    except AssertionError:   # a fixture written as a test fails by assertion
        survives = False
    except Exception:        # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real check: F20
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _f20():
    p = _path(F20, "f_goals_20.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG15.load_goals(p)
    return G.grade_x5(out, log, state_dir=F20, goal_lines=goals, kind="f"), GX4.grade_x4(
        out, log, state_dir=F20, goal_lines=goals, kind="f")


def to_x4(g):
    """grade_x5's dict as grade_x4's: the new keys and `base_x4` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x4")
    g["report_lines"] = [("gate_x4 " + ln[len("gate_x5 "):]) if ln.startswith("gate_x5 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


F20_EMPTY = {
    "work": {"read": True, "steps": {"work": 0, "cornered": 0, "pile": 0}, "turns": {}, "cornered_ticks": 0,
             "pile": {"episodes": 0, "shoves": 0, "knockdowns": 0}},
    "contact": {"read": True, "seconds": 0, "frames": 0, "engagements": 0, "per_engagement": [], "hits_inside": 0},
    "handbacks": {"read": True, "lines": 0, "by_why": {}},
    "engage_hold": {"read": True, "lines": 0, "by_rule": {}},
    "withdraw": {"read": True, "lines": 0, "sends": 0, "resends": 0},
}


def test_on_f20_grade_x5_keeps_every_grade_x4_key_and_reads_every_footwork_reading_empty():
    g, base = _f20()
    assert (g["grade"], g["base"], g["base_x4"], g["base_x3"], g["base_x2"], g["base_x1"]) == (
        "grade_x5", "grade_x4", "grade_x3", "grade_x2", "grade_x1", "grade_f12")
    assert to_x4(g) == base
    assert {k: g[k] for k in G.NEW} == F20_EMPTY
    json.dumps(g, allow_nan=False)


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


F20_SHA256 = "6c7890abbe0fe951eabc6ac9840fe6e6c80581367c79d6b58279db1073b65fb2"# f_grade_17.py's whole stdout on F20 (CRLF folded), pinned at its first run


def test_f_grade_17_on_f20_reproduces_the_committed_f_grade_txt_under_its_new_lines():
    """f_grade_17.py on F20: its grade_x4 lines are the committed f_grade.txt's (f_grade_16's) lines byte for byte, the
    five footwork lines after them, its JSON the committed one's with the footwork keys (each empty) and the names
    added, and the whole output's sha256 pinned (a drift in any reading or any live name read through the grade chain
    fails here)."""
    p = _path(F20, "f_goals_20.json")
    text = _script("f_grade_17.py", p).decode("utf-8")
    want = open(os.path.join(F20, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert [("gate_x4 " + ln[len("gate_x5 "):]) if ln.startswith("gate_x5 ") else ln
            for ln in lines[:-G.N_LINES]] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("work (the melee's footwork steps)")
    got = json.loads(text[i:])
    assert {k: got[k] for k in G.NEW} == F20_EMPTY
    assert to_x4(got) == json.loads(want[j:])
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == F20_SHA256


# ================================================================ the first artifact graded through grade_x5: F21
F21 = os.path.join(TESTING, "artifacts", "f_goals_21-20261111-150552")


def test_f_grade_17_on_f21_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_17.py` on the committed F21 artifact (Plan 35's evidence session, the first graded through
    `grade_x5`: the work, contact, hand-back, engage-hold and withdraw readings over grade_x4's) reproduces its committed
    `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the grade chain fails here."""
    p = _path(F21, "f_goals_21.json")
    want = open(os.path.join(F21, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert _script("f_grade_17.py", p) == want
