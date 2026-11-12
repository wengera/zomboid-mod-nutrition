"""base/grades/x7.py (Plan 37 Task 4), offline: `grade_x7` and its disposition readings (`restarts`: the work melees
superseded inside KEEP_R by a non-melee act; `disposition`: the threat why's transitions with their dwell; `string`: the
work leaf's string episodes, turns, kills and walk lines; `safe_release`: the melee's release asked, handed back safe or
at the bound, and broken early; `speeds`: the character's and the zombies' tiles a second by gait), each on a fabricated
ring where it counts, its unread case, its agreement with the scorecard's live reader (the copy's source) and a mutant
of each reading its fixture fails (each mutant named in the MUTANTS list's comment); every grade_x6 key kept under
`grade_x7` on the committed F22 (`f_goals_22-20261111-215108`, Plan 36's evidence session, graded through grade_x6),
through the function and through the regrade script `f_grade_19.py`, whose grade_x6 part reproduces F22's committed
`f_grade.txt` line for line and key for key.

F22 ran before the Plan 37 keys (PZA/1.16's `disposition`, `turn_for`, `release` and the `released` hand-back): its
disposition, string and safe_release read unread. Its restarts read: the reader's work melee is the scorecard's (a melee
whose first progress line carries the `work` leaf, every Plan 36 melee, or one whose act lines carry `args.workR`), and
F22's three steers that cut a work melee inside KEEP_R (a161, a180, a183) are the restarts Plan 37 removes."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x6 as GX6
from agent.base.grades import x7 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import f_grade_15 as FG15
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_x2 import ordered, rec
from .test_grades_x4 import dline

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F22 = os.path.join(TESTING, "artifacts", "f_goals_22-20261111-215108")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")


def _ts():
    sys.path.insert(0, os.path.join(os.path.dirname(TESTING), "tools"))
    import trial_score as TS
    return TS


def mel(aid, t, state="progress", work=None, reason="", args=None, **res):
    """A melee act line `t` seconds in: its `work` leaf when given, its `args` when given."""
    r = dict(res)
    if work is not None:
        r["work"] = dict(work)
    ln = actl(aid, "melee", state, t, r, reason)
    if args is not None:
        ln["args"] = dict(args)
    return ln


def act(aid, type_, t, state="accepted", reason="", **res):
    return actl(aid, type_, state, t, res, reason)


def tline(t, why, type_=None, sent=True, branch="threat", **args):
    """A decision line whose why sits on `branch`."""
    r = dline(t, {}, type_, sent=sent, **args)
    r["inputs"]["branches"] = {branch: dict(why)}
    return r


# ================================================================ restarts
def restarts_case():
    """m1 (work by its first leaf): superseded at gap 1.0, a steer accepted 0.1 s on (a restart). m2: superseded at gap
    1.0 with a melee m3 accepted next (no restart). m3: superseded at gap 2.5 exactly (KEEP_R: no restart), a steer
    next. m4: superseded at gap 2.0, the next act 1.3 s on (outside RESTART_S). m5 (work by `args.workR`, its first
    progress line with no work leaf): superseded at gap 0.5, an aim next (a restart). m6 (no work at all): superseded,
    a steer next. m7 (work): failed stopped at gap 1.0, a steer next (no supersede)."""
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, work={"gap": 1.0}),
            mel("m1", 1.5, "failed", reason="superseded"), act("s1", "steer", 1.6),
            mel("m2", 2.0, "accepted"), mel("m2", 2.1, work={"gap": 1.0}),
            mel("m2", 2.5, "failed", reason="superseded"),
            mel("m3", 2.6, "accepted"), mel("m3", 2.7, work={"gap": 2.5}),
            mel("m3", 3.0, "failed", reason="superseded"), act("s3", "steer", 3.1),
            mel("m4", 4.0, "accepted"), mel("m4", 4.1, work={"gap": 2.0}),
            mel("m4", 4.5, "failed", reason="superseded"), act("s4", "steer", 5.8),
            mel("m5", 6.0, "accepted", args={"workR": 1.2}), mel("m5", 6.1, step="face"),
            mel("m5", 6.2, work={"gap": 0.5}), mel("m5", 6.5, "failed", reason="superseded"), act("a5", "aim", 6.6),
            mel("m6", 7.0, "accepted"), mel("m6", 7.1, step="face"), mel("m6", 7.5, "failed", reason="superseded"),
            act("s6", "steer", 7.6),
            mel("m7", 8.0, "accepted"), mel("m7", 8.1, work={"gap": 1.0}), mel("m7", 8.5, "failed", reason="stopped"),
            act("s7", "steer", 8.6)]
    return rec(), None, ordered(acts)


RESTARTS_WANT = {"read": True, "n": 2, "per_contact_min": None,
                 "rows": [{"aid": "m1", "by": "steer", "gap": 1.0}, {"aid": "m5", "by": "aim", "gap": 0.5}]}


def _restarts():
    return G.readings_x7(*restarts_case())["restarts"]


def test_restarts_read_the_work_melees_cut_close_in_by_a_non_melee_act():
    assert _restarts() == RESTARTS_WANT


def test_restarts_rate_is_over_x5_s_minutes_in_contact():
    assert G.e_restarts(restarts_case()[2], 60.0)["per_contact_min"] == 2.0
    assert G.e_restarts(restarts_case()[2], 0.0)["per_contact_min"] is None


def test_restarts_are_unread_without_a_work_melee_and_agree_with_the_scorecard():
    acts = [mel("m6", 7.0, "accepted"), mel("m6", 7.1, step="face"), mel("m6", 7.5, "failed", reason="superseded"),
            act("s6", "steer", 7.6)]
    assert G.readings_x7(rec(), None, acts)["restarts"] == {"read": False}
    live = _ts().restart_readings(restarts_case()[2])
    assert (live["read"], live["n"], live["aids"]) == (True, 2, [r["aid"] for r in _restarts()["rows"]])


# ================================================================ disposition
def disposition_case():
    """A line with no why; hunt to hold (three, 2.5 s); hold to string (many, 3.0 s); a non-dict disposition (not a
    change); string to tend (clear, no dwell: a name outside DISP_ORDER); tend to hold (three, 4.0 s); a transition on
    the care branch (not the threat's: not read)."""
    rows = [dline(1.0, {}),
            dline(2.0, {"disposition": {"from": "hunt", "to": "hold", "why": "three", "dwell": 2.5}}),
            dline(3.0, {"disposition": {"from": "hold", "to": "string", "why": "many", "dwell": 3.0}}),
            dline(4.0, {"disposition": "string"}),
            dline(5.0, {"disposition": {"from": "string", "to": "tend", "why": "clear", "dwell": None}}),
            dline(6.0, {"disposition": {"from": "tend", "to": "hold", "why": "three", "dwell": 4.0}}),
            tline(7.0, {"disposition": {"from": "hold", "to": "break", "why": "floor", "dwell": 1.0}}, branch="care")]
    return rec(), rows, []


DISPOSITION_WANT = {
    "read": True, "changes": 4, "per_contact_min": None, "dwell_median": 3.0,
    "by_to": {"hunt": 0, "hold": 2, "string": 1, "break": 0, "tend": 1}, "by_why": {"three": 2, "many": 1, "clear": 1},
    "rows": [{"line": 1, "from": "hunt", "to": "hold", "why": "three", "dwell": 2.5},
             {"line": 2, "from": "hold", "to": "string", "why": "many", "dwell": 3.0},
             {"line": 4, "from": "string", "to": "tend", "why": "clear", "dwell": None},
             {"line": 5, "from": "tend", "to": "hold", "why": "three", "dwell": 4.0}]}


def _disposition():
    return G.readings_x7(*disposition_case())["disposition"]


def test_disposition_reads_the_threat_why_s_transitions():
    assert _disposition() == DISPOSITION_WANT


def test_disposition_rate_is_over_the_minutes_in_contact():
    assert G.e_disposition(disposition_case()[1], 120.0)["per_contact_min"] == 2.0


def test_disposition_is_unread_without_a_transition_and_agrees_with_the_scorecard():
    assert G.readings_x7(rec(), [dline(1.0, {})], [])["disposition"] == {"read": False}
    assert G.readings_x7(rec(), None, [])["disposition"] == {"read": False}
    live = _ts().disp_readings(disposition_case()[1])
    d = _disposition()
    assert (live["changes"], live["dwells"]) == (d["changes"], [2.5, 3.0, 4.0])
    assert {k: v for k, v in d["by_to"].items() if v} == live["by"]


# ================================================================ string
def string_case():
    """m1: a hunt leaf; a string walk leaf (episode 1); the turn (leader 7, gap2 3.0) on a walk leaf and re-read on the
    heartbeat (one turn); a line with no work leaf and one with a leaf carrying no disposition (neither ends the run);
    the turn (leader 8, gap2 2.5: STRING_GAP exactly, wide); a hold leaf (ends the run); a string leaf (episode 2);
    done kill with a leaf carrying no disposition (the last disposition string: a kill). m2: a string leaf with the turn
    (leader 9, gap2 1.5) (episode 3); a hunt leaf; done kill (last hunt: no kill). m3: a leaf with no disposition, done
    kill (no kill)."""
    t7, t8 = {"leader": 7, "gap2": 3.0}, {"leader": 8, "gap2": 2.5}
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, work={"disposition": "hunt"}),
            mel("m1", 1.2, work={"disposition": "string", "step_for": "string"}),
            mel("m1", 1.3, work={"disposition": "string", "step_for": "string", "turn_for": t7}),
            mel("m1", 1.4, work={"disposition": "string", "turn_for": t7}),
            mel("m1", 1.5, step="face"), mel("m1", 1.6, work={"gap": 1.0}),
            mel("m1", 1.7, work={"disposition": "string", "turn_for": t8}),
            mel("m1", 1.8, work={"disposition": "hold"}), mel("m1", 1.9, work={"disposition": "string"}),
            mel("m1", 2.0, "done", work={"gap": 2.0}, end="kill", kill=True),
            mel("m2", 3.0, "accepted"), mel("m2", 3.1, work={"disposition": "string", "turn_for": {"leader": 9,
                                                                                                "gap2": 1.5}}),
            mel("m2", 3.2, work={"disposition": "hunt"}), mel("m2", 3.3, "done", end="kill", kill=True),
            mel("m3", 4.0, "accepted"), mel("m3", 4.1, work={"step_for": "gap"}),
            mel("m3", 4.2, "done", end="kill", kill=True)]
    return rec(), None, ordered(acts)


STRING_WANT = {"read": True, "episodes": 3, "turns": 3, "turns_gap_ok": 2, "gap2": [3.0, 2.5, 1.5],
               "gap2_median": 2.5, "kills": 1, "walk_lines": 2}


def _string():
    return G.readings_x7(*string_case())["string"]


def test_string_reads_the_episodes_turns_kills_and_walk_lines():
    assert _string() == STRING_WANT


def test_string_is_unread_without_a_disposition_leaf_and_agrees_with_the_scorecard():
    acts = [mel("m3", 4.0, "accepted"), mel("m3", 4.1, work={"step_for": "gap"}), mel("m3", 4.2, "done", kill=True)]
    assert G.readings_x7(rec(), None, acts)["string"] == {"read": False}
    live = _ts().string_readings(string_case()[2])
    s = _string()
    assert (live["episodes"], live["turns"], live["wide"], live["gap2"], live["kills"]) == (
        s["episodes"], s["turns"], s["turns_gap_ok"], s["gap2"], s["kills"])


# ================================================================ release
def release_case():
    """A melee sent with release false (keyed, not asked); asked at 2.0 (m2 accepted 2.05), a steer sent at 2.5 before
    m2's released safe hand-back at 3.0 (early); asked at 4.0 (m4), released bound at 4.4, a steer at 4.6 after it (not
    early); asked at 6.0 (m6), a walkTo at 7.5 (outside EARLY_S), m6's floor hand-back at 8.0; a melee release line not
    sent (not asked)."""
    rows = [dline(1.0, {}, "melee", release=False), dline(2.0, {}, "melee", release=True), dline(2.5, {}, "steer"),
            dline(4.0, {}, "melee", release=True), dline(4.6, {}, "steer"), dline(6.0, {}, "melee", release=True),
            dline(7.5, {}, "walkTo"), dline(9.0, {}, "melee", sent=False, release=True)]
    acts = [mel("m0", 1.05, "accepted"), mel("m0", 1.5, "failed", reason="superseded"),
            mel("m2", 2.05, "accepted"), mel("m2", 3.0, "done", end="handback", why="released", safe=True),
            mel("m4", 4.05, "accepted"), mel("m4", 4.4, "done", end="handback", why="released", safe=False),
            mel("m6", 6.05, "accepted"), mel("m6", 8.0, "done", end="handback", why="floor")]
    return rec(), rows, ordered(acts)


RELEASE_WANT = {"read": True, "asked": 3, "safe": 1, "bound": 1, "early": 1,
                "rows": [{"line": 1, "aid": "m2", "back": "released", "early": True},
                         {"line": 3, "aid": "m4", "back": "released", "early": False},
                         {"line": 5, "aid": "m6", "back": "floor", "early": False}]}


def _release():
    return G.readings_x7(*release_case())["safe_release"]


def test_release_reads_the_asked_the_hand_backs_and_the_early_breaks():
    assert _release() == RELEASE_WANT


def test_release_is_unread_without_a_release_key_or_a_log_and_agrees_with_the_scorecard():
    assert G.readings_x7(rec(), [dline(1.0, {}, "melee")], [])["safe_release"] == {"read": False}
    assert G.readings_x7(rec(), None, release_case()[2])["safe_release"] == {"read": False}
    live = _ts().release_readings(release_case()[1], release_case()[2])
    r = _release()
    assert live == {k: r[k] for k in ("read", "asked", "safe", "bound", "early")}


# ================================================================ speeds
def sfr(t, x, zs=(), **me):
    """A frame `t` seconds in at (x, 10): its `me` flags and its zombies [(id, x, state, crawler)]."""
    m = dict({"x": x, "y": 10.0, "moving": True, "running": False, "aiming": False, "sneaking": False}, **me)
    return {"kind": "frame", "seq": int(round(t * 10)), "wallMs": int(round((T0 + t) * 1000)), "me": m,
            "zombies": [{"id": i, "x": zx, "y": 12.0, "state": s, "crawler": c} for i, zx, s, c in zs]}


def speeds_case():
    """40 frames 0.1 s apart walking at 2 tiles a second (39 pairs), zombie 1 lunging at 1.5 and the crawler 2 (state
    walktoward) at 0.5; a 0.5 s gap (not read) walking 2 tiles more; 6 frames running at 3.5 (5 pairs); a teleport 5
    tiles in 0.1 s (dropped) after 4 frames sneaking at 1.5 (4 pairs, the first off the last running frame: the later
    frame's flags name the pair)."""
    fs, x = [], 0.0
    for i in range(40):
        fs.append(sfr(0.1 * i, x, [(1, 1.5 * 0.1 * i, "lunge", False), (2, 0.05 * i, "walktoward", True)]))
        x += 0.2
    t = 3.9 + 0.5
    x += 1.8
    for i in range(6):
        fs.append(sfr(t, x, running=True))
        t, x = t + 0.1, x + 0.35
    t, x = t - 0.1, x - 0.35
    for i in range(4):
        t, x = t + 0.1, x + 0.15
        fs.append(sfr(t, x, sneaking=True))
    fs.append(sfr(t + 0.1, x + 5.0, sneaking=True))
    return rec(), None, fs


def _speeds():
    return G.readings_x7(*speeds_case())["speeds"]


def _close(a, b):
    return a is not None and abs(a - b) < 1e-6


def test_speeds_read_the_character_by_gait_and_the_zombies_by_state():
    s = _speeds()
    assert s["read"] is True and list(s["me"]) == ["walk", "run", "sneak_walk"] and list(s["zombies"]) == [
        "crawler", "lunge"]
    assert [s["me"][k]["n"] for k in s["me"]] == [39, 5, 4]
    assert _close(s["me"]["walk"]["median"], 2.0) and _close(s["me"]["walk"]["p90"], 2.0)
    assert _close(s["me"]["run"]["median"], 3.5) and _close(s["me"]["sneak_walk"]["median"], 1.5)
    assert (s["zombies"]["lunge"]["n"], s["zombies"]["crawler"]["n"]) == (39, 39)
    assert _close(s["zombies"]["lunge"]["median"], 1.5) and _close(s["zombies"]["crawler"]["median"], 0.5)


def test_speeds_are_unread_under_thirty_pairs_in_every_group():
    assert G.readings_x7(rec(), None, speeds_case()[2][:30])["speeds"] == {"read": False}
    assert G.readings_x7(rec(), None, speeds_case()[2][:31])["speeds"]["read"] is True
    assert G.readings_x7(rec(), None, [])["speeds"] == {"read": False}


def test_me_gait_names_every_flag_combination():
    assert [G.me_gait(m) for m in ({"moving": True}, {"moving": True, "running": True},
                                   {"moving": True, "sprinting": True}, {}, {"running": True},
                                   {"moving": True, "aiming": True, "sneaking": True}, {"aiming": True})] == [
        "walk", "run", "sprint", "still", "still_run", "aimed_sneak_walk", "aimed_still"]


# ================================================================ the module's cases
def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = disposition_case()
    out["stop"]["wallS"] = 3.5 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    assert G.readings_x7(out, rows, lines)["disposition"]["changes"] == 2


def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    assert G.NEW == ("restarts", "disposition", "string", "safe_release", "speeds")
    assert (G.KEEP_R, G.STRING_GAP, G.RESTART_S, G.EARLY_S) == (2.5, 2.5, 1.0, 1.0)
    assert G.DISP_ORDER == ("hunt", "hold", "string", "break")
    assert (G.MIN_DT_S, G.MAX_DT_S, G.MAX_TPS, G.MIN_PAIRS) == (0.05, 0.3, 10.0, 30)


def test_the_frozen_copies_match_their_live_sources_at_this_commit():
    """The copies' sources read at the commit the module was written on (46021a9f): the scorecard's constants and the
    planner's KEEP_R (a later change of any is the next grade's to fold in)."""
    TS = _ts()
    assert (G.KEEP_R, G.STRING_GAP, G.RESTART_S, G.EARLY_S, G.DISP_ORDER) == (
        TS.KEEP_R, TS.STRING_GAP, TS.RESTART_S, TS.EARLY_S, TS.DISP_ORDER)
    from agent.base.planner import policies as P
    assert P.KEEP_R == G.KEEP_R
    src = open(TS.__file__, encoding="utf-8").read()
    assert '"%s" in E._d(ln.get("args"))' % G.WORK_R in src


def test_no_new_key_shadows_an_earlier_grade_s_key():
    """grade_x7 updates grade_x6's dict with NEW: a key an earlier grade holds (grade_e10's `release`, P25-M, on a chain
    session) would be overwritten and the base's report lines with it; the committed F22 grade (grade_x6's, an LLM
    session) and grade_x6 over the chain session E23 hold none of NEW."""
    p = _path(F22, "f_grade.txt")
    t = open(p, "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    keys = set(json.loads(t[t.index("\n{\n"):]))
    assert not keys & set(G.NEW) and "contact" in keys and "rip_ride" in keys
    q = _path(E23, "e_day_23.json")
    e = GX6.grade_x6(EG23.load(q), EG23.load_log(q), state_dir=E23, kind="e")
    assert not set(e) & set(G.NEW) and "release" in e


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x7.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x7_mutant"}
    exec(compile(src[:start] + new + src[end:], "x7_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


def holds(fn, want):
    return lambda: fn() == want


MUTANTS = [
    # restarts: a melee superseded by a melee counted
    ("e_restarts", lambda b: b.replace("if by != MELEE:", "if True:"), holds(_restarts, RESTARTS_WANT)),
    # restarts: the gap at KEEP_R exactly read inside
    ("e_restarts", lambda b: b.replace("gap >= KEEP_R", "gap > KEEP_R"), holds(_restarts, RESTARTS_WANT)),
    # restarts: no RESTART_S window
    ("e_restarts", lambda b: b.replace("s[\"end\"] <= w <= s[\"end\"] + RESTART_S * 1000.0", "s[\"end\"] <= w"),
     holds(_restarts, RESTARTS_WANT)),
    # restarts: the workR rule dropped (a melee sent under work whose first line carries no leaf)
    ("e_restarts", lambda b: b.replace("s[\"aid\"] in work_r or ", ""), holds(_restarts, RESTARTS_WANT)),
    # restarts: any failure read as a supersede
    ("e_restarts", lambda b: b.replace(" or t.get(\"reason\") != SUPERSEDED", ""), holds(_restarts, RESTARTS_WANT)),
    # disposition: a non-dict disposition counted
    ("e_disposition", lambda b: b.replace("if not isinstance(d, dict):", "if d is None:"),
     holds(_disposition, DISPOSITION_WANT)),
    # disposition: the listed names not zero-filled
    ("e_disposition", lambda b: b.replace("{k: by_to.get(k, 0) for k in names}", "dict(by_to)"),
     holds(_disposition, DISPOSITION_WANT)),
    # disposition: the why off a wrong branch (the care's)
    ("_threat", lambda b: b.replace(".get(\"threat\")", ".get(\"care\")"),
     holds(_disposition, DISPOSITION_WANT)),
    # disposition: a missing dwell read as 0
    ("e_disposition", lambda b: b.replace("v = E._n(d.get(\"dwell\"))", "v = E._n(d.get(\"dwell\")) or 0.0"),
     holds(_disposition, DISPOSITION_WANT)),
    # string: a heartbeat's re-read turn counted again
    ("e_string", lambda b: b.replace("if isinstance(t, dict) and t != prev:", "if isinstance(t, dict):"),
     holds(_string, STRING_WANT)),
    # string: a turn at STRING_GAP exactly not wide
    ("e_string", lambda b: b.replace("g >= STRING_GAP", "g > STRING_GAP"), holds(_string, STRING_WANT)),
    # string: a leaf with no disposition clearing the last one (the kill lost)
    ("e_string", lambda b: b.replace("last = d if d is not None else last", "last = d"), holds(_string, STRING_WANT)),
    # string: every melee's kill counted
    ("e_string", lambda b: b.replace("if last == STRING else 0", "if True else 0"), holds(_string, STRING_WANT)),
    # string: a leaf with no disposition ending the run (an extra episode)
    ("e_string", lambda b: b.replace("            last = d if d is not None else last\n",
                                     "            run = run and d is not None\n"
                                     "            last = d if d is not None else last\n"),
     holds(_string, STRING_WANT)),
    # string: the walk lines off a wrong key
    ("e_string", lambda b: b.replace("w.get(\"step_for\") == STRING", "w.get(DISPOSITION) == STRING"),
     holds(_string, STRING_WANT)),
    # release: an unsent melee read as asked
    ("e_release", lambda b: b.replace("if act.get(\"type\") != MELEE or r.get(\"sent\") is not True:",
                                      "if act.get(\"type\") != MELEE:"), holds(_release, RELEASE_WANT)),
    # release: a command after the hand-back read as early
    ("e_release", lambda b: b.replace("(aid not in back or back[aid] > w)", "True"), holds(_release, RELEASE_WANT)),
    # release: no EARLY_S window
    ("e_release", lambda b: b.replace("t < w <= t + EARLY_S", "t < w"), holds(_release, RELEASE_WANT)),
    # release: the melee matched to the last accepted before the ask, not the first after
    ("e_release", lambda b: b.replace("min(((w, a) for a, w in first.items() if w >= t)",
                                      "max(((w, a) for a, w in first.items() if w < t)"),
     holds(_release, RELEASE_WANT)),
    # release: a bound read as any not-safe hand-back (the floor's among them)
    ("e_release", lambda b: b.replace("bound += 1 if res.get(\"safe\") is False else 0",
                                      "bound += 1 if res.get(\"safe\") is not True else 0").replace(
        "            if res.get(\"why\") == RELEASED:\n", "            if True:\n"), holds(_release, RELEASE_WANT)),
    # speeds: a pair across the 0.5 s gap read
    ("e_speeds", lambda b: b.replace("MIN_DT_S < dt < MAX_DT_S", "MIN_DT_S < dt < 1.0"),
     test_speeds_read_the_character_by_gait_and_the_zombies_by_state),
    # speeds: the teleport kept
    ("e_speeds", lambda b: b.replace("            if v < MAX_TPS:\n                me.", "            if True:\n"
                                                                                   "                me."),
     test_speeds_read_the_character_by_gait_and_the_zombies_by_state),
    # speeds: the crawler grouped by its state
    ("e_speeds", lambda b: b.replace("CRAWLER if z.get(\"crawler\") else ", ""),
     test_speeds_read_the_character_by_gait_and_the_zombies_by_state),
    # speeds: the sneak merged into the walk
    ("me_gait", lambda b: b.replace("g = (\"sneak_\" + g) if me.get(\"sneaking\") else g", "pass"),
     test_speeds_read_the_character_by_gait_and_the_zombies_by_state),
    # speeds: the group off the earlier frame's flags
    ("e_speeds", lambda b: b.replace("me.setdefault(me_gait(mb)", "me.setdefault(me_gait(ma)"),
     test_speeds_read_the_character_by_gait_and_the_zombies_by_state),
    # speeds: the unread floor inclusive of a group under MIN_PAIRS
    ("e_speeds", lambda b: b.replace("len(v) >= MIN_PAIRS", "len(v) >= MIN_PAIRS - 1"),
     test_speeds_are_unread_under_thirty_pairs_in_every_group),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, check = MUTANTS[n]
    assert check() is not False, "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = check() is not False
    except Exception:   # a fixture written as a test fails by assertion; a mutant may crash on its fixture
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real check: F22
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


def to_x6(g):
    """grade_x7's dict as grade_x6's: the new keys and `base_x6` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x6")
    g["report_lines"] = [("gate_x6 " + ln[len("gate_x7 "):]) if ln.startswith("gate_x7 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


UNREAD = {"read": False}
F22_RESTARTS = [("a161", "steer"), ("a180", "steer"), ("a183", "steer")]


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


def _check_f22(got):
    assert {k: got[k] for k in ("disposition", "string", "safe_release")} == {
        "disposition": UNREAD, "string": UNREAD, "safe_release": UNREAD}
    rs = got["restarts"]
    assert (rs["read"], rs["n"]) == (True, 3) and [(r["aid"], r["by"]) for r in rs["rows"]] == F22_RESTARTS
    assert all(r["gap"] < G.KEEP_R for r in rs["rows"]) and rs["per_contact_min"] > 0
    sp = got["speeds"]
    assert sp["read"] is True and 2.0 <= sp["me"]["walk"]["median"] <= 2.2
    assert 3.4 <= sp["me"]["run"]["median"] <= 3.7 and 0.9 <= sp["me"]["aimed_walk"]["median"] <= 1.1
    assert "lunge" in sp["zombies"] and "walktoward" in sp["zombies"]


@functools.lru_cache(maxsize=None)
def _f22():
    p = _path(F22, "f_goals_22.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG15.load_goals(p)
    return G.grade_x7(out, log, state_dir=F22, goal_lines=goals, kind="f"), GX6.grade_x6(
        out, log, state_dir=F22, goal_lines=goals, kind="f")


def test_on_f22_grade_x7_keeps_every_grade_x6_key_and_reads_the_restarts_and_the_speeds():
    g, base = _f22()
    assert to_x6(g) == base
    assert (g["grade"], g["base"], g["base_x6"], g["base_x5"], g["base_x1"]) == (
        "grade_x7", "grade_x6", "grade_x5", "grade_x4", "grade_f12")
    _check_f22(g)
    json.dumps(g, allow_nan=False)


def test_f_grade_19_on_f22_reproduces_the_committed_f_grade_txt_under_its_new_lines():
    """f_grade_19.py on F22: its grade_x6 lines are the committed f_grade.txt's (f_grade_18's) lines byte for byte, the
    five disposition lines after them, its JSON the committed one's with the disposition keys and the names added."""
    p = _path(F22, "f_goals_22.json")
    text = _script("f_grade_19.py", p).decode("utf-8")
    want = open(os.path.join(F22, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert [("gate_x6 " + ln[len("gate_x7 "):]) if ln.startswith("gate_x7 ") else ln
            for ln in lines[:-G.N_LINES]] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("restarts") and lines[-1].startswith("speeds")
    got = json.loads(text[i:])
    _check_f22(got)
    assert to_x6(got) == json.loads(want[j:])


# ================================================================ the first artifact graded through grade_x7: F23
F23 = os.path.join(TESTING, "artifacts", "f_goals_23-20261112-093508")


def test_f_grade_19_on_f23_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_19.py` on the committed F23 artifact (Plan 37's evidence session, the first graded through
    `grade_x7`: the restarts, disposition, string, safe_release and speeds readings over grade_x6's) reproduces its committed
    `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the grade chain fails here."""
    p = _path(F23, "f_goals_23.json")
    want = open(os.path.join(F23, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert _script("f_grade_19.py", p) == want
