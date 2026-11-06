"""base/grades/x1.py (Plan 31 Task 15b), offline: `grade_x1` and its eleven readings (the clip at the loop's stop, the
attacks landed, the trial loop's fleeing, toward, every-wound dressing and superseded melees, the meet's
presses, refusals, finishes and handbacks, and the Dress maneuver), each on a fabricated ring where it counts, its
unread case and a mutant of each reading that its fixture fails; every base key unchanged under `grade_x1` (grade_e21's
for a chain session, grade_f12's for an LLM one) on test_grades_e20's cut 2 fixture and on the committed F15
(`f_goals_16-20261105-164332`) and E23 (`e_day_23-20261105-095110`) artifacts, through the function and through the
regrade scripts `e_grade_22.py` and `f_grade_13.py`; the module's frozen copies (ruling P26-Q), the scorecard's
three readers (`reaction_segments`, `landed_hits`, `dressed`) byte for byte as at main 0e4c9ec3. The byte-for-byte
regrade tests of the artifacts grade_x1 grades are added at their artifact commits."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e21 as G21
from agent.base.grades import f12 as G12
from agent.base.grades import x1 as G
from agent.drivers import e_grade_22 as EG22
from agent.drivers import f_grade_13 as FG13
from . import test_grades_e14 as T14
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_e18 import hf

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F15 = os.path.join(TESTING, "artifacts", "f_goals_16-20261105-164332")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")
NEW = G.NEW
HELLO = {"kind": "hello", "mod": "1.10", "proto": "PZA/1", "seq": 1, "wallMs": int(T0 * 1000)}


# ================================================================ the fabricated ring
def rec(actions=(), wall_s=600.0):
    """test_grades_e14's artifact (loop.startPyMs at T0) with `actions` and the stop `wall_s` seconds on."""
    a = T14.artifact(actions)
    a["stop"]["wallS"] = wall_s
    return a


def fr(t, react="", parts=(), zombies=(), x=10.0, y=10.0, gm=None, health=100.0, seq=None):
    """A frame `t` seconds into the loop: the reaction, the body parts, the zombies, the position and the game minute
    (`me.hour` gm / 60; default 600 + t / 60, a game minute a wall minute)."""
    f = hf(t, react, health=health, parts=parts, zombies=zombies, x=x, y=y)
    f["me"]["hour"] = (600.0 + t / 60.0 if gm is None else gm) / 60.0
    if seq is not None:
        f["seq"] = seq
    return f


def part(i, wound=False, bleeding=False, bandaged=False):
    return {"i": i, "h": 90.0, "wound": wound, "bleeding": bleeding, "bandaged": bandaged}


def mel(aid, t, step, state="progress", seq=None, **res):
    """A melee act line `t` seconds on: progress with `step`, or a terminal line, its result `res`."""
    r = dict(res)
    if state == "progress":
        r.setdefault("step", step)
    ln = actl(aid, "melee", state, t, r)
    if seq is not None:
        ln["seq"] = seq
    return ln


def leaf(**kw):
    return dict({"d_press": 1.2, "d_collide_pred": 1.0, "d_min": 1.2, "look_off": 2.0, "hp0": 1.0, "hp1": 1.0,
                 "knock": False, "cut_by": ""}, **kw)


def act_row(aid, type_, sent_s, **args):
    return {"aid": aid, "type": type_, "args": dict(args), "state": "done", "reason": "", "sentS": sent_s,
            "endedS": sent_s + 1.0, "branch": "threat"}


def dl(n, t, threat=None, action=None, sent=False, branch="threat", goal=None, care=None, x=10.0, y=10.0, gm=None):
    """test_grades_e20's decision line with the inputs' position and hour (gm / 60; default 600 + t / 60)."""
    ln = T20.aline_(n, t, threat, action, sent=sent, branch=branch, goal=goal, care=care)
    ln["inputs"].update(x=x, y=y, hour=(600.0 + t / 60.0 if gm is None else gm) / 60.0)
    return ln


def ordered(*groups):
    return sorted([ln for g in groups for ln in g], key=lambda ln: ln["wallMs"])


# ================================================================ the clip at the loop's stop
def clip_case():
    lines = [fr(t) for t in (1.0, 2.0, 9.0, 11.0)] + [actl("a1", "walkTo", "accepted", 12.0)]
    rows = [dl(1, 1.0), dl(2, 9.5), dl(3, 10.5)]
    a = rec([act_row("a1", "walkTo", 5.0), act_row("a2", "walkTo", 10.5)], wall_s=10.0)
    return a, rows, lines


def test_the_clip_drops_every_source_after_the_loop_s_stop_and_counts_what_it_dropped():
    out, rows, lines, clock = G.clip(*clip_case())
    assert [round(E._n(f["wallMs"]) / 1000.0 - T0, 1) for f in lines] == [1.0, 2.0, 9.0]
    assert len(rows) == 2 and [a["aid"] for a in out["loop"]["actions"]] == ["a1"]
    assert clock == {"read": True, "start_ms": T0 * 1000.0, "stop_ms": (T0 + 10.0) * 1000.0, "stop_s": 10.0,
                     "first_frame_s": 1.0, "last_frame_s": 9.0, "frames": 1, "lines": 2, "decisions": 1,
                     "actions": 1}
    a, rows0, lines0 = clip_case()
    del a["stop"]["wallS"]
    out, rows, lines, clock = G.clip(a, rows0, lines0)
    assert clock["read"] is False and len(lines) == 5 and len(rows) == 3 and clock["lines"] == 0
    assert G.clip(a, None, lines0)[1] is None


# ================================================================ the attacks landed (the scorecard's)
def split_lines():
    """Frames every 0.1 s from 0 to 9.0: five reaction segments. A `Bite` 1.0-1.2 (m5's `hit` at 1.03 joins it) then
    `BiteDefended` 1.3-1.4 (one run, two segments by type); C `Bite` 3.0-3.6, m2's `hit` at 3.2 joining it and m1's at
    3.4 a hit of its own (a segment takes one step); D `CrawlerBiteLEFT` 5.0-5.1, then `EndDeath` 5.2-6.0 (its own
    segment, the killing attack, to the run's end through a `BiteLEFT` at 6.0) taking both of m3's `hit` steps at 5.5
    and 5.8; m4's `hit` at 8.0, in no segment (a hit
    of its own). Union: 5 segments + 6 steps - 4 joined = 7."""
    react = {10: "Bite", 11: "Bite", 12: "Bite", 13: "BiteDefended", 14: "BiteDefended"}
    react.update({k: "Bite" for k in range(30, 37)})
    react.update({50: "CrawlerBiteLEFT", 51: "CrawlerBiteLEFT"})
    react.update({k: "EndDeath" for k in range(52, 60)})
    react[60] = "BiteLEFT"                                  # a type after EndDeath in the dying run: no new segment
    frames = [fr(k / 10.0, react.get(k, ""), seq=1000 + k) for k in range(91)]
    acts = [actl("m5", "melee", "accepted", 0.8), mel("m5", 0.9, "face"), mel("m5", 1.03, "hit"),
            actl("m1", "melee", "accepted", 2.5), mel("m1", 2.6, "face"), mel("m1", 2.9, "swing"),
            mel("m1", 3.4, "hit"), mel("m1", 3.9, "face"),
            actl("m2", "melee", "accepted", 3.15), mel("m2", 3.2, "hit"), mel("m2", 3.3, "face"),
            actl("m3", "melee", "accepted", 5.4), mel("m3", 5.45, "face"), mel("m3", 5.5, "hit"),
            mel("m3", 5.7, "face"), mel("m3", 5.8, "hit"),
            actl("m4", "melee", "accepted", 7.8), mel("m4", 7.9, "face"), mel("m4", 8.0, "hit")]
    return ordered(frames, acts)


def split_read(kills=2):
    lines = split_lines()
    return G.landed_hits(E._frame_index(lines)[1], lines, kills)


def test_the_attacks_landed_split_at_a_type_change_and_the_end_death_run_is_the_one_killing_attack():
    h = split_read()
    assert (h["read"], h["runs"], h["steps"], h["joined"], h["union"], h["kills"]) == (True, 5, 6, 4, 7, 2)
    assert h["per_kill_union"] == 3.5
    lines = split_lines()
    assert G.reaction_segments(E._frame_index(lines)[1]) == [(10, 12), (13, 14), (30, 36), (50, 51), (52, 60)]
    assert [(r["source"], r["kind"], r["aid"]) for r in h["rows"]] == [
        ("both", "Bite", "m5"), ("reaction", "BiteDefended", None), ("both", "Bite", "m2"), ("step", None, "m1"),
        ("reaction", "CrawlerBiteLEFT", None), ("both", "EndDeath", "m3"), ("step", None, "m4")]
    assert G.landed_hits([], [], 1) == {"read": False}
    assert split_read(0)["per_kill_union"] is None


# ================================================================ the fleeing, toward a target
def flee_log():
    """Six lines at 2 s: L2 and L3 flee (`held`), L4 a pull leg; the character walks from x 10 to 15 away from a
    chasing zombie at x 8 (the frames)."""
    return [dl(1, 0.0, x=10.0), dl(2, 2.0, {"flee": "held"}, x=11.0), dl(3, 4.0, {"flee": "held"}, x=12.0),
            dl(4, 6.0, {"leg": "pull"}, x=13.0), dl(5, 8.0, x=14.0), dl(6, 10.0, x=15.0)]


def flee_frames():
    return [fr(t, zombies=[{"id": 7, "x": 8.0, "y": 10.0, "hasTarget": True}], x=10.0 + t / 2.0)
            for t in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0)]


def flee_read():
    return G.e_fleeing(E._Lines(rec(), flee_log(), flee_frames()))


def test_the_fleeing_reads_the_flee_lines_minutes_the_legs_and_the_frames_moving_away():
    f = flee_read()
    assert f["read"] is True and f["lines"] == 2 and f["by"] == {"flee:held": 2}
    assert f["minutes"] == pytest.approx(4.0 / 60.0) and f["seconds"] == pytest.approx(4.0)
    assert f["total_minutes"] == pytest.approx(10.0 / 60.0)
    assert f["legs"]["pull"]["lines"] == 1 and f["legs"]["back"]["lines"] == 0
    assert f["away"] == {"intervals": 5, "minutes": pytest.approx(10.0 / 60.0), "refuge_skipped": 0}
    assert G.e_fleeing(None) == {"read": False}


def toward_log():
    """A goal walk to (20, 10): L2 to L4 close on it, L5 stands, L6 names no target."""
    goal = {"type": "ExploreToward", "args": {"x": 20.0, "y": 10.0}}
    return [dl(1, 0.0, branch="goal", goal={}, x=10.0)] + [
        dict(dl(n, (n - 1) * 2.0, branch="goal", goal={}, x=x), goal=goal) for n, x in ((2, 12.0), (3, 14.0),
                                                                                       (4, 16.0), (5, 16.0))] + [
        dl(6, 10.0, x=16.0)]


def toward_read():
    return G.e_toward_target(E._Lines(rec(), toward_log(), [fr(0.0)]))


def test_the_toward_reads_the_minutes_closing_on_a_named_target():
    t = toward_read()
    assert t["read"] is True and t["lines"] == 3 and t["named_lines"] == 4 and t["by"] == {"ExploreToward": 3}
    assert t["minutes"] == pytest.approx(6.0 / 60.0) and t["named_minutes"] == pytest.approx(8.0 / 60.0)
    assert G.e_toward_target(None) == {"read": False}


# ================================================================ the wounds, every one
def wound_frames():
    """Part 3 scratched at 0 s (carried), bandaged at 30 s; part 5 scratched at 60 s and never bleeding, bandaged at
    90 s (dressed in 0.5 min); part 6 bleeding at 120 s, bandaged at 300 s (3 min: late); part 7 scratched at 120 s,
    healed at 400 s; part 8 scratched at 500 s and open at the end; part 5's bandage off at 600 s while still
    scratched (no new wound: the scorecard's rule), then bleeding unbandaged at 650 s (a new wound, open)."""
    def at(t):
        ps = []
        if t <= 600:
            ps.append(part(3, wound=True, bandaged=t >= 30))
        if t >= 60:
            ps.append(part(5, wound=True, bleeding=t >= 650, bandaged=90 <= t < 600))
        if t >= 120:
            ps.append(part(6, wound=True, bleeding=t < 300, bandaged=t >= 300))
        if 120 <= t < 400:
            ps.append(part(7, wound=True))
        elif t >= 400:
            ps.append(part(7))
        if t >= 500:
            ps.append(part(8, wound=True))
        return ps
    return [fr(t, parts=at(t), seq=t) for t in range(0, 700, 10)]


def test_every_wound_taken_is_counted_and_dressed_when_bandaged_within_a_game_minute():
    w = G.e_wounds_dressed(wound_frames())
    assert w["read"] is True and (w["wounds"], w["dressed"], w["stopped"], w["carried"]) == (6, 2, 4, 1)
    assert [(r["part"], r["seq0"], r["seq1"], r["bandaged"]) for r in w["rows"]] == [
        (3, 0, 30, True), (5, 60, 90, True), (6, 120, 300, True), (7, 120, 400, False), (8, 500, None, None),
        (5, 650, None, None)]
    assert [round(r["minutes"], 3) if r["minutes"] is not None else None for r in w["rows"]] == [
        0.5, 0.5, 3.0, 4.667, None, None]
    assert G.e_wounds_dressed([]) == {"read": False}


# ================================================================ the melees superseded
def superseded_lines():
    return [actl("m1", "melee", "accepted", 1.0), mel("m1", 1.1, "face"),
            actl("m1", "melee", "failed", 1.5, reason="superseded"),
            actl("m2", "melee", "accepted", 2.0), mel("m2", 2.1, "swing"),
            actl("m2", "melee", "failed", 2.5, reason="superseded"),
            actl("m3", "melee", "accepted", 3.0), mel("m3", 3.1, "shove"), actl("m3", "melee", "done", 3.5)]


def test_the_melees_superseded_before_their_press_are_read_off_the_terminal_lines():
    a = rec([act_row(m, "melee", 1.0) for m in ("m1", "m2", "m3", "m4")])
    m = G.e_melees_superseded(a, superseded_lines())
    assert (m["superseded_before"], m["superseded"], m["no_swing_step"], m["sent"], m["spans"]) == (1, 2, 1, 4, 3)
    assert m["aids"] == ["m1"] and G.e_melees_superseded({}, [])["sent"] == 0


# ================================================================ the meet: presses, refusals, finishes, handbacks
def meet_lines():
    """m1 (strike): a swing lowering 1.0 to 0.8, a swing knocking down (its leaf on the knock_wait line), the floor
    swing's leaf on its done kill line. m2 (shove, spent): a shove that did nothing with knock_p 41, then a refused
    swing (its leaf cut_by refused, `refusals` 1), the wait, the accepted press's line closing the run at 3, a cut
    swing (cut_by hit), a second refusal run closed by the done lost why refused. m3 (finish, headAim, sent at 9):
    the head turn and a stomp lowering, then the reflex's re-pin to 15 (step repin, `target` and `repins` on every
    later line); done handback crowd {n 3, ds} pressing 15, with a field the grade does not know. m4: handback standing
    at its record's 9. m5 (sent at 15): handback standing again."""
    return [HELLO,
            actl("m1", "melee", "accepted", 1.0), mel("m1", 1.1, "swing"),
            mel("m1", 1.5, "swing", press=leaf(hp1=0.8)),
            mel("m1", 2.0, "knock_wait", press=leaf(hp0=0.8, hp1=0.5, knock=True)),
            mel("m1", 2.2, "floor"), mel("m1", 2.6, None, state="done", end="kill", kill=True,
                                         press=leaf(hp0=0.5, hp1=0.0, d_press=0.9)),
            actl("m2", "melee", "accepted", 3.0), mel("m2", 3.1, "shove"),
            mel("m2", 3.5, "swing", press=leaf(knock_p=0.41)),
            mel("m2", 3.6, "swing", refusals=1, press=leaf(cut_by="refused")),
            mel("m2", 3.7, "refused"), mel("m2", 4.0, "swing", refusals=3),
            mel("m2", 4.5, "face", press=leaf(cut_by="hit")),
            mel("m2", 4.6, "swing", refusals=1, press=leaf(cut_by="refused")),
            mel("m2", 5.0, None, state="done", end="lost", why="refused", refusals=15),
            actl("m3", "melee", "accepted", 6.0), mel("m3", 6.1, "head"), mel("m3", 6.3, "stomp"),
            mel("m3", 6.7, "face", press=leaf(hp0=0.5, hp1=0.3, d_press=0.25)),
            mel("m3", 6.8, "repin", target=15, repins=1), mel("m3", 6.9, "face", target=15, repins=1),
            mel("m3", 7.0, None, state="done", end="handback", why="crowd", id=11, d=0.5, n=3,
                ds=[0.5, 0.6, 0.9], target=15, repins=1, zzz=1),
            actl("m4", "melee", "accepted", 8.0), mel("m4", 8.1, "head"),
            mel("m4", 8.5, None, state="done", end="handback", why="standing", id=12, d=1.4),
            actl("m5", "melee", "accepted", 9.0),
            mel("m5", 9.5, None, state="done", end="handback", why="standing", id=13, d=1.2)]


def meet_rec():
    return rec([act_row("m1", "melee", 1.0, targetId=8, mode="strike"),
                act_row("m2", "melee", 3.0, targetId=10, mode="shove"),
                act_row("m3", "melee", 6.0, targetId=9, mode="finish", headAim=True),
                act_row("m4", "melee", 8.0, targetId=9, mode="finish"),
                act_row("m5", "melee", 9.0, targetId=15, mode="strike")])


def test_the_presses_are_read_by_kind_against_their_outcome_with_the_leaf_s_numbers():
    p = G.e_meet_presses(meet_rec(), meet_lines())
    assert p["read"] is True and p["presses"] == 6 and p["refused"] == 2
    assert p["by_kind"] == {"swing": 3, "floor": 1, "shove": 1, "stomp": 1}
    assert p["by_outcome"] == {"lowered": 2, "knocked": 1, "killed": 1, "nothing": 1, "cut": 1}
    assert [(r["aid"], r["kind"], r["outcome"]) for r in p["rows"]] == [
        ("m1", "swing", "lowered"), ("m1", "swing", "knocked"), ("m1", "floor", "killed"), ("m2", "shove", "nothing"),
        ("m2", "swing", "refused"), ("m2", "swing", "cut"), ("m2", "swing", "refused"), ("m3", "stomp", "lowered")]
    assert p["shoves"] == {"n": 1, "knocked": 0, "knock_p_n": 1, "knock_p_sum": 0.41}
    t = p["table"]["swing"]["lowered"]
    assert t["n"] == 1 and t["d_press"] == {"n": 1, "min": 1.2, "median": 1.2, "max": 1.2} and t["knock_p"] == {"n": 0}
    assert p["table"]["floor"]["killed"]["d_press"]["max"] == 0.9


def test_the_refusals_are_read_by_run_with_their_counts_and_ends():
    r = G.e_meet_refusals(meet_lines())
    assert (r["read"], r["runs"], r["refused"], r["waits"], r["ended"], r["open"]) == (True, 2, 18, 1, 1, 0)
    assert [(x["aid"], x["count"], x["ended_by"]) for x in r["rows"]] == [("m2", 3, "press"), ("m2", 15, "done lost")]
    assert r["by_count"] == {"3": 1, "15": 1}


def test_the_finishes_read_the_floor_and_the_stomp_and_the_head_aim_sent():
    f = G.e_meet_finishes(meet_rec(), meet_lines())
    assert f["read"] is True and f["sent_finish"] == 2 and f["head_aim"] == {"on": 1, "off": 4, "absent": 4}
    assert f["presses"] == {"floor": 1, "stomp": 1} and f["by_outcome"] == {"killed": 1, "lowered": 1}
    assert f["kills"] == 1 and f["heads"] == 2
    assert [(x["aid"], x["kind"], x["head_aim"]) for x in f["rows"]] == [("m1", "floor", False), ("m3", "stomp", True)]


def test_the_handbacks_read_the_re_pinned_target_off_the_line_the_crowd_and_the_reflex_s_re_pins():
    h = G.e_meet_handbacks(meet_rec(), meet_lines())
    assert h["read"] is True and h["handbacks"] == 3 and h["by_why"] == {"crowd": 1, "standing": 2}
    assert h["by_target"] == {"15": 2, "9": 1} and h["repinned"] == ["15"]     # m3's line names 15, its record 9
    r0, r1 = h["rows"][0], h["rows"][1]
    assert (r0["target"], r0["n"], r0["ds"], r0["repins"], r0["extra"]) == (15, 3, [0.5, 0.6, 0.9], 1, {"zzz": 1})
    assert (r1["target"], r1["n"], r1["ds"], r1["repins"], r1["extra"]) == (9, None, None, None, {})
    assert (r0["id"], r0["d"], r1["why"]) == (11, 0.5, "standing")
    assert h["repins"] == {"melees": 1, "total": 1, "steps": 1}


def test_the_meet_readings_read_unread_without_a_span_or_on_a_log_before_pza_1_10():
    old = [dict(HELLO, mod="1.9")] + meet_lines()[1:]
    for fn in (lambda ls: G.e_meet_presses(meet_rec(), ls), G.e_meet_refusals,
               lambda ls: G.e_meet_finishes(meet_rec(), ls), lambda ls: G.e_meet_handbacks(meet_rec(), ls)):
        assert fn(old) == {"read": False} and fn([HELLO]) == {"read": False} and fn(meet_lines())["read"] is True
    assert G.meet_log(meet_lines()[1:]) is True                       # no hello: a press leaf read
    assert G.meet_log([dict(HELLO, mod="1.10.1")]) is True and G.meet_log([dict(HELLO, mod="x")]) is False


# ================================================================ the Dress
def care(phase, sends, part_=6, ride=False, kind=None, item=None, end=None):
    """The care why of a line under a running Dress (and, given, the ended ones' `dress_end`)."""
    c = {"reason": "dress", "dress": {"maneuver": "dress", "part": part_, "phase": phase, "sends": sends, "item": item,
                                      "kind": kind, "ride": ride, "lost": 0, "moved": 0}}
    if end is not None:
        c["dress_end"] = end
    return c


def dress_log():
    """Dress 1 of part 6 from 20 s: the stop sent at 20, still at 21, pick at 23; the unwear of 501, the rip of 501,
    the bandage of 900 (a rag); its end done logged at 30. Dress 2 of part 2, riding, from 40: its bandage, done at 44.
    Dress 3 of part 4 from 50, its sends falling at 52 (a new Dress of part 4: the first closed unlogged), the second
    failed `nothing` at 54."""
    def sent(n, t, type_, c, **args):
        return dl(n, t, action={"type": type_, "args": args}, sent=True, branch="care", care=c)
    return [dl(1, 10.0),
            sent(2, 20.0, "stop", care("stop", 0)), dl(3, 21.0, care=care("still", 1)),
            dl(4, 23.0, care=care("pick", 1)), sent(5, 24.0, "unwear", care("pick", 1), itemId=501),
            sent(6, 25.0, "rip", care("pick", 2, item=501), itemId=501),
            sent(7, 27.0, "bandage", care("pick", 3, kind="rag", item=900), itemId=900, part=6),
            dl(8, 30.0, branch="goal", care={"reason": "x", "dress_end": [
                {"maneuver": "dress", "part": 6, "end": "done", "sends": 4, "lost": 1}]}),
            sent(9, 40.0, "bandage", care("pick", 0, part_=2, ride=True, kind="bandage"), itemId=901, part=2,
                 keepMoving=True),
            dl(10, 44.0, care={"dress_end": [{"part": 2, "end": "done", "sends": 1, "lost": 0}]}),
            dl(11, 50.0, care=care("stop", 3, part_=4)), dl(12, 52.0, care=care("stop", 0, part_=4)),
            dl(13, 54.0, care={"dress_end": [{"part": 4, "end": "failed", "fail": "nothing", "sends": 0}]})]


def dress_frames():
    """Part 6 bleeding from 15 s (an onset at 5 s before it, ended at 8; another at 35 s, after its Dress began), part
    2 from 38 s; none for part 4."""
    def ps(t):
        out = []
        if 5 <= t < 8 or 15 <= t < 30 or 35 <= t < 37:
            out.append(part(6, wound=True, bleeding=True))
        if 38 <= t < 44:
            out.append(part(2, wound=True, bleeding=True))
        return out
    return [fr(float(t), parts=ps(t)) for t in range(0, 60)]


def dress_read():
    return G.e_dresses(E._Lines(rec(), dress_log(), dress_frames()))


def test_each_dress_reads_its_start_its_stop_its_garments_its_end_and_the_time_from_the_bleed():
    d = dress_read()
    assert d["read"] is True and d["dresses"] == 4 and d["rides"] == 1 and d["failed"] == 1
    assert d["by_end"] == {"done": 2, "unlogged": 1, "failed": 1}
    r1, r2, r3, r4 = d["rows"]
    assert (r1["part"], r1["line"], r1["end"], r1["lost"], r1["sends"], r1["ride"]) == (6, 2, "done", 1, 4, False)
    assert r1["stop"] == {"sent_s": 0.0, "still_s": 3.0, "still_waits": 1}
    assert (r1["unworn"], r1["torn"], r1["bandages"]) == ([501], [501], [{"item": 900, "kind": "rag"}])
    assert r1["s"] == 10.0 and r1["onset_s"] == -5.0 and r1["onset_to_start_s"] == 5.0 and r1["onset_to_end_s"] == 15.0
    assert (r2["part"], r2["ride"], r2["end"], r2["bandages"]) == (2, True, "done", [{"item": 901, "kind": "bandage"}])
    assert r2["stop"]["sent_s"] is None and r2["onset_to_start_s"] == 2.0
    assert (r3["part"], r3["end"], r3["end_wall"]) == (4, "unlogged", T0 + 50.0) and r3["onset_s"] is None
    assert (r4["part"], r4["end"], r4["fail"]) == (4, "failed", "nothing")
    assert G.e_dresses(None) == {"read": False}
    assert G.e_dresses(E._Lines(rec(), [dl(1, 0.0)], [])) == {"read": False}


# ================================================================ grade_x1 over its base
def to_base(g):
    """grade_x1's dict as its base's: the new keys and `base` dropped, the name restored, the new report lines dropped
    and a chain session's gate line renamed back."""
    g = dict(g)
    for k in NEW:
        g.pop(k)
    g["grade"] = g.pop("base")
    g["report_lines"] = [("gate_e21 " + ln[len("gate_x1 "):]) if ln.startswith("gate_x1 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


def cut2():
    return T14.artifact(T20.cut2_actions(), []), T20.cut2_log(), T20.cut2_lines()


def test_grade_x1_keeps_every_grade_e21_key_for_a_chain_session_and_every_grade_f12_key_for_an_llm_one():
    a, log, lines = cut2()
    e = G.grade_x1(a, log, lines=lines, kind="e")
    assert e["grade"] == "grade_x1" and e["base"] == "grade_e21"
    assert to_base(e) == G21.grade_e21(a, decision_lines=log, lines=lines)
    f = G.grade_x1(a, log, lines=lines, kind="f")
    assert f["base"] == "grade_f12" and to_base(f) == G12.grade_f12(a, decision_lines=log, lines=lines)
    assert set(NEW) <= set(e) and not set(NEW) & set(G21.grade_e21(a, decision_lines=log, lines=lines))
    assert G.session_kind(a) == "e" and G.session_kind(a, goal_lines=[]) == "f"
    assert G.session_kind({"loop": {"llm": {}}}) == "f" and G.grade_x1({"loop": {"llm": {}}})["base"] == "grade_f12"
    with pytest.raises(ValueError):
        G.grade_x1(a, kind="x")
    g = dict(e, gate={"pass": True})
    renamed = G.report_lines_x1(g)
    assert any(ln.startswith("gate_x1 ") for ln in renamed) and not any(ln.startswith("gate_e21 ") for ln in renamed)
    assert G.gate_x1([]) == G21.gate_e21([])


def test_the_report_lines_are_the_base_s_then_one_per_reading():
    a, log, lines = cut2()
    g = G.grade_x1(a, log, lines=lines, kind="e")
    tail = g["report_lines"][-G.N_LINES:]
    assert tail == G.lines_x1(g) and G.N_LINES == len(NEW) == 11
    for ln, tag in zip(tail, ("clip (", "landed hits (", "fleeing (", "toward a named target (", "wounds dressed (",
                              "melees superseded", "meet presses", "meet refusals", "meet finishes", "meet handbacks",
                              "dresses")):
        assert ln.startswith(tag), (tag, ln)
    off = G.grade_x1({}, None, lines=[], kind="e")["report_lines"][-G.N_LINES:]
    assert all("no line read" in ln for ln in off[1:5] + off[6:]) and off[0].startswith("clip (the loop's stop): no")
    r = G.readings_x1({}, None, [])
    assert all(r[k] == {"read": False} for k in NEW if k not in ("clip", "melees_superseded"))


def test_the_readings_read_the_sources_clipped_at_the_stop():
    lines = [HELLO] + meet_lines()[1:]
    early = G.readings_x1(dict(meet_rec(), stop={"reason": "death", "wallS": 2.3}), None, lines)
    whole = G.readings_x1(meet_rec(), None, lines)
    assert early["clip"]["read"] is True and early["meet_presses"]["presses"] == 2
    assert whole["meet_presses"]["presses"] == 6


# ================================================================ ruling P26-Q: the frozen copies
def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    ns = vars(G)
    assert ns["RETREAT_LABELS"] == ("avoid", "kite", "retreat", "string", "flee")
    assert ns["LABEL_KEYS"] == ("intent", "play", "act") and ns["LEGS"] == ("pull", "back")
    assert ns["REFUGE_WORDS"] == ("filter", "door", "window", "shelter", "refuge")
    assert (ns["MOVE_EPS"], ns["DRESS_MIN"], ns["SUPERSEDED"], ns["MEET_MOD"]) == (0.05, 1.0, "superseded", (1, 10))
    assert ns["PRESS_STEPS"] == ("swing", "shove", "stomp", "floor")
    assert ns["PRESS_KEYS"] == ("d_press", "d_collide_pred", "d_min", "look_off", "hp0", "hp1", "knock", "cut_by")
    assert (ns["KNOCK_P"], ns["HIT_STEP"], ns["HEAD_STEP"], ns["REFUSED"], ns["HANDBACK"]) == (
        "knock_p", "hit", "head", "refused", "handback")
    assert (ns["CARE"], ns["DRESS_KEY"], ns["DRESS_END_KEY"]) == ("care", "dress", "dress_end")
    assert ns["DRESS_SENDS"] == ("stop", "unwear", "rip", "bandage") and ns["DEATH_REACTION"] == "EndDeath"
    assert (ns["REPIN_STEP"], ns["TARGET"], ns["REPINS"], ns["CROWD_N"], ns["CROWD_DS"]) == (
        "repin", "target", "repins", "n", "ds")
    assert set(ns["DONE_KEYS"]) >= {"n", "ds", "target", "repins"}
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x1.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x1_mutant"}
    exec(compile(src[:start] + new + src[end:], "x1_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


def _presses():
    return G.e_meet_presses(meet_rec(), meet_lines())


MUTANTS = [
    ("clip", lambda b: b.replace("w <= cut", "True"), lambda: len(G.clip(*clip_case())[2]) == 3),
    ("reaction_segments", lambda b: b.replace("!= G18._reaction(frames[i - 1])", "is None"),
     lambda: split_read()["runs"] == 5),
    ("reaction_segments", lambda b: b.replace("== DEATH_REACTION:\n                break",
                                              "== None:\n                break"),
     lambda: split_read()["runs"] == 5),
    ("landed_hits", lambda b: b.replace("(i not in taken or", "(True or"), lambda: split_read()["union"] == 7),
    ("landed_hits", lambda b: b.replace("or G18._reaction(frames[s[0]]) == DEATH_REACTION)", ")"),
     lambda: split_read()["union"] == 7),
    ("flee_minutes", lambda b: b.replace("if lab is None:", "if False:"), lambda: flee_read()["lines"] == 2),
    ("away_minutes", lambda b: b.replace("d1 <= c[1] + MOVE_EPS", "False"),
     lambda: G.away_minutes(E._Lines(rec(), flee_log(), [dict(f, zombies=[{"id": 7, "x": f["me"]["x"] + 2.0,
                                                                            "y": 10.0, "hasTarget": True}])
                                                         for f in flee_frames()]))["intervals"] == 0),
    ("toward_minutes", lambda b: b.replace("- MOVE_EPS:", "+ 5.0:"), lambda: toward_read()["lines"] == 3),
    ("dressed", lambda b: b.replace('bleed or p.get("wound") is True', "bleed"),
     lambda: G.e_wounds_dressed(wound_frames())["wounds"] == 6),
    ("dressed", lambda b: b.replace('r["minutes"] <= DRESS_MIN', "True"),
     lambda: G.e_wounds_dressed(wound_frames())["dressed"] == 2),
    ("dressed", lambda b: b.replace("(bleed or i not in under)", "True"),
     lambda: G.e_wounds_dressed(wound_frames())["rows"][-1]["seq0"] == 650),
    ("e_melees_superseded", lambda b: b.replace("if not steps & set(PRESS_STEPS):", "if True:"),
     lambda: G.e_melees_superseded(rec(), superseded_lines())["superseded_before"] == 1),
    ("_press_rows", lambda b: b.replace('"kind": last if last is not None else res.get("step")',
                                        '"kind": res.get("step")'),
     lambda: _presses()["by_kind"] == {"swing": 3, "floor": 1, "shove": 1, "stomp": 1}),
    ("_outcome", lambda b: b.replace('if leaf.get("knock") is True:', "if False:"),
     lambda: _presses()["by_outcome"]["knocked"] == 1),
    ("e_meet_refusals", lambda b: b.replace('leaf.get("cut_by") == REFUSED and n == 1', "False"),
     lambda: G.e_meet_refusals(meet_lines())["runs"] == 2),
    ("e_meet_finishes", lambda b: b.replace('aim["on" if v is True else "off"] += 1', 'aim["off"] += 1'),
     lambda: G.e_meet_finishes(meet_rec(), meet_lines())["head_aim"]["on"] == 1),
    ("e_meet_handbacks", lambda b: b.replace("if k not in DONE_KEYS", "if False"),
     lambda: G.e_meet_handbacks(meet_rec(), meet_lines())["rows"][0]["extra"] == {"zzz": 1}),
    ("e_meet_handbacks", lambda b: b.replace("res.get(TARGET) if res.get(TARGET) is not None else ", ""),
     lambda: G.e_meet_handbacks(meet_rec(), meet_lines())["repinned"] == ["15"]),
    ("meet_log", lambda b: b.replace("return v >= MEET_MOD", "return True"),
     lambda: G.e_meet_presses(meet_rec(), [dict(HELLO, mod="1.9")] + meet_lines()[1:]) == {"read": False}),
    ("e_dresses", lambda b: b.replace('e.get("part") == cur["part"]', "False"),
     lambda: dress_read()["by_end"]["done"] == 2),
    ("e_dresses", lambda b: b.replace('(E._n(d.get("sends")) or 0) < cur["_sends"]', "False"),
     lambda: dress_read()["dresses"] == 4),
    ("e_dresses", lambda b: b.replace("o <= w0 * 1000.0", "True"),
     lambda: dress_read()["rows"][0]["onset_to_start_s"] == 5.0),
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


# ================================================================ the real checks: F15 and E23
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _f15():
    p = _path(F15, "f_goals_16.json")
    out, log, goals = EG22.load(p), EG22.load_log(p), FG13.load_goals(p)
    return (G.grade_x1(out, log, state_dir=F15, goal_lines=goals),
            G12.grade_f12(out, None, log, state_dir=F15, goal_lines=goals))


@functools.lru_cache(maxsize=None)
def _e23():
    p = _path(E23, "e_day_23.json")
    out, log = EG22.load(p), EG22.load_log(p)
    return G.grade_x1(out, log, state_dir=E23, kind="e"), G21.grade_e21(out, None, log, state_dir=E23)


def test_on_f15_grade_x1_keeps_every_grade_f12_key_and_reads_the_eight_attacks_and_the_meet_unread():
    g, base = _f15()
    assert g["base"] == "grade_f12" and to_base(g) == base
    h = g["landed_hits"]
    assert h["union"] == 8 and h["runs"] == 6 and h["kills"] == 0
    assert all(g[k] == {"read": False} for k in ("meet_presses", "meet_refusals", "meet_finishes", "meet_handbacks",
                                                 "dresses"))
    assert g["clip"]["read"] is True and g["clip"]["stop_s"] == pytest.approx(525.4802062511444)
    assert g["wounds_dressed"]["wounds"] == 6 and g["wounds_dressed"]["dressed"] == 0
    assert g["fleeing"]["read"] is True and g["fleeing"]["lines"] == 298
    json.dumps(g, allow_nan=False)


def test_on_e23_grade_x1_keeps_every_grade_e21_key():
    g, base = _e23()
    assert g["base"] == "grade_e21" and to_base(g) == base
    assert g["landed_hits"]["union"] == 6 and g["kills_matched"]["planner"] == 1
    w = g["wounds_dressed"]
    assert w["wounds"] == 6 and sum(1 for r in w["rows"] if r["bandaged"] is True) == 5 and w["dressed"] == 0


RUNS = os.environ.get("PZT_RUNS") or os.path.join(TESTING, "runs")
SCORED = {   # review-t15b F1: the four trial runs where the first cut disagreed, the scorecard's segments and union at
             # main 0e4c9ec3 (its rescore 17fedae5), which the copy must read
    "x_trial-mix_1-20261106-031141": (8, 10), "x_trial-tactician-20261106-030826": (5, 6),
    "x_trial-utility-20261105-225829": (2, 3), "x_trial-mix_2-20261106-031458": (13, 15)}


def _trial(run):
    """grade_x1's new readings over a trial run folder (per machine: skipped where it is absent), its sources as the
    scorecard loads them: the record, the decision log and the admin client's state log."""
    d = os.path.join(RUNS, run)
    sd = os.path.join(d, "clients", "admin", "Lua", "pzagent", "admin")
    if not os.path.isdir(sd):
        pytest.skip("%s is per machine and not here" % run)
    out = EG22.load(os.path.join(d, "x_trial.json"))
    rows = EG22.load_log(os.path.join(d, "x_trial.json"))
    return G.readings_x1(out, rows, E.session_lines(sd)[0])


@pytest.mark.parametrize("run", sorted(SCORED))
def test_the_attacks_landed_on_the_trial_runs_read_as_the_scorecard_reads_them(run):
    h = _trial(run)["landed_hits"]
    assert (h["runs"], h["union"]) == SCORED[run]


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def test_f_grade_13_prints_grade_f12_s_lines_then_the_new_ones_and_the_json():
    p = _path(F15, "f_goals_16.json")
    printed, got = _script("f_grade_13.py", p)
    g, base = _f15()
    assert printed[:-G.N_LINES] == base["report_lines"] and printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    assert got["grade"] == "grade_x1" and got["base"] == "grade_f12" and got["landed_hits"]["union"] == 8


def test_e_grade_22_prints_grade_e21_s_lines_then_the_new_ones_and_the_json():
    p = _path(E23, "e_day_23.json")
    printed, got = _script("e_grade_22.py", p)
    g, base = _e23()
    assert printed[:-G.N_LINES] == base["report_lines"] and printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    assert got["grade"] == "grade_x1" and got["base"] == "grade_e21"


def test_the_regrade_scripts_refuse_an_argument_they_do_not_define():
    """Read statically (CLAUDE.md section 5): e_grade_22's main answers usage, exit 2, on no path or more than two
    outside `--chain`; f_grade_13's on anything but one path."""
    e = open(EG22.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_22.py" in e
    assert "from agent.base.grades.x1 import gate_x1, grade_x1, report_lines_x1" in e and EG22.KIND == "e"
    f = open(FG13.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_13.py" in f and FG13.KIND == "f"
    assert EG22.grade_x1 is G.grade_x1 and FG13.grade_x1 is G.grade_x1
