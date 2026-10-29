"""The Survive decision golden (Plan 24 Task 1): `agent.base.replay_decisions` over E5 and F1 (then E2, E3 and E4,
Task 1 fix 1; and F1 with the PZA/1.5 caps, `f1-caps15`, Task 10 fix 1).

Each golden is reproduced byte for byte from its artifact; a re-record is only under a named behaviour change
(`replay_decisions`' docstring, CLAUDE.md § 6 golden trace)."""
import functools
import hashlib
import math
import json
import os

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import policies as P
from agent.base.planner import survive as S


def run_dir(key):
    return os.path.join(R.ARTIFACTS, R.RUNS[key])


@functools.lru_cache(maxsize=5)
def replayed(key):
    return json.dumps(R.replay(run_dir(key)), sort_keys=True)


def replay_rows(key):
    return json.loads(replayed(key))


# ---------------------------------------------------------------- the rules before P24-X (Plan 24 Task 18)
def pre_x(sv):
    """The replay's mutate seam onto the rules before ruling P24-X (`Survive.ENGAGE` off: no engage within
    ENGAGE_R, the flee's `held` rule and the refight margin as before, no seek): with it the six goldens of
    `24987f2a` are reproduced line for line (`test_with_engage_off_the_goldens_are_iteration_7_s`). The tests below
    that pin a line of an earlier ruling (P23-AJ to P24-N) read it there, since P24-X re-records every golden from
    its line 1 (the engage of a zombie at 7 tiles where the record looted) and every later line of those episodes is
    open loop. Not behind the switch: Task 18's WIDE_TURNS and STEP_PROBE (and fix 1's group-aware wide tier), which
    the PRE_X pins prove move no golden (Task 18 fix 1, the review's minor 13)."""
    sv.ENGAGE = False


@functools.lru_cache(maxsize=6)
def _pre_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_x), sort_keys=True)


def pre_rows(key):
    """The replayed log with P24-X off (`pre_x`)."""
    return json.loads(_pre_replayed(key))


def pre_replay(key):
    """`R.replay` with P24-X off, uncached (a test's own monkeypatched mutants read)."""
    return R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_x)


def pre_run(key):
    """`R.run` with P24-X off, uncached."""
    return R.decisions(pre_replay(key))


def pre_gold(key):
    """{line: decision} of the replay with P24-X off: the golden as recorded at `24987f2a`."""
    return {d["line"]: d for d in R.decisions(pre_rows(key))}


def golden(key):
    with open(R.golden_path(key), "rb") as f:
        return f.read()


def divergences(key, rep):
    """Every line `R.agreement` would name a divergence at, in order (its comparison, each line)."""
    _, rows = R.read_record(run_dir(key))
    return [k for k, (rec, got) in enumerate(zip(rows, rep), 1) if (rec["branch"] == "threat" or got["branch"] ==
            "threat") and (got["branch"], got["action"]) != (rec["branch"], R.as_run(rec["action"]))]


DEAD_LINES = [254, 255, 333]   # F1's lines the dead target moved (Task 12 fix 1): the swings at 15911 and 15937 read
                               # dead (254, 333) and the `unreachable` flee's walk held at 255


KEYS = ["e5", "f1", "e2", "e3", "e4"]


@pytest.mark.parametrize("key", KEYS)
def test_the_golden_is_reproduced_byte_for_byte_from_its_artifact(key):
    raw = golden(key)
    head = json.loads(raw.decode("utf-8"))
    assert head["artifact"] == R.RUNS[key] and head.get("span") == R.SPANS.get(key)
    text = R.golden_text(R.run(run_dir(key)), head["base"], head["artifact"], head["recorded"], head.get("span"))
    assert text.encode("utf-8") == raw
    assert b"\r" not in raw and raw.endswith(b"}\n")


@pytest.mark.parametrize("key", KEYS)
def test_two_runs_give_identical_output(key):
    a, b = R.run(run_dir(key)), R.run(run_dir(key))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert R.golden_text(a, "x", "y", "z") == R.golden_text(b, "x", "y", "z")


def test_a_smaller_cornered_r_moves_the_f1_golden_first_at_line_484(monkeypatch):
    """The mutation pass: CORNERED_R 1.5 -> 1.0 (survive's and policies' copies). Named change, Plan 24 survival 5
    (P24-A (c)): F1's golden moves first at line 484, where 15921 at 1.03-1.5 tiles read a `walk` corner the running
    `many` episode refused (`yield` "many"); with the mutant no corner is read there. (At Task 1's recording it moved
    first at 537, the corner attack on 15921, a `stuck` corner now, still moved.)"""
    base = {d["line"]: d for d in json.loads(golden("f1").decode("utf-8"))["decisions"]}
    assert base[484]["why"]["yield"] == "many"
    assert base[537]["action"] == {"type": "attack", "args": {"targetId": 15921}}
    assert base[537]["why"]["corner_kind"] == "stuck"
    monkeypatch.setattr(S, "CORNERED_R", 1.0)
    monkeypatch.setattr(P, "CORNERED_R", 1.0)
    moved = {d["line"]: d for d in R.run(run_dir("f1"))}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff and diff[0] == 484 and "yield" not in moved[484]["why"] and 537 in diff


def test_without_the_trailing_read_rule_f1_moves_at_line_498(monkeypatch):
    """The act model's own falsifier: a60's `done` (written 2 ms before line 498's wall) taken at 498 sends the next
    steer a tick early, where the record still ran a60. Named change, Task 12 fix 1 (the review's minor 5): the
    binder reads a recorded sprint as the run the replay sends (`as_run`), so the flee legs bind to the record's aids
    again and the falsifier is read on the golden's own replay, as before Task 12 (which read it with FLEE_GAIT set
    back to the sprint)."""
    base = {d["line"]: d for d in R.run(run_dir("f1"))}
    monkeypatch.setattr(R._Acts, "ends_current", lambda self, got: False)
    moved = {d["line"]: d for d in R.run(run_dir("f1"))}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff[0] == 498 and base[498]["action"] is None and moved[498]["action"]["type"] == "steer"


@pytest.mark.parametrize("key", KEYS)
def test_the_goal_branch_s_decisions_are_excluded(key):
    rows = replay_rows(key)
    out = R.run(run_dir(key))
    assert all(d["branch"] != "goal" for d in out)
    assert [d["line"] for d in out] == [k for k, r in enumerate(rows, 1) if r["branch"] != "goal"]
    goal_sends = [k for k, r in enumerate(rows, 1) if r["branch"] == "goal" and r["sent"]]
    assert goal_sends, "the record's goal sends are replayed (they supersede the threat's actions), not output"
    assert not set(goal_sends) & {d["line"] for d in out}


def test_the_recorded_goals_answer_from_the_record():
    g = R.RecordedGoals(kit=None)
    row = {"branch": "goal", "sent": True, "action": {"type": "walkTo", "args": {"x": 1, "y": 2, "gait": "walk"}},
           "goal": {"type": "ExploreToward", "state": "running"}, "inputs": {"branches": {"goal": {"goal": "E"}}}}
    g.feed(row)
    assert g.current is not None and not g.pending
    cmd = g.tick(None, None)
    assert (cmd.TYPE, cmd.args()) == ("walkTo", {"x": 1, "y": 2, "gait": "walk"}) and g.why == {"goal": "E"}
    row = dict(row, branch="threat", sent=False, action=None, goal={"type": "ExploreToward", "state": "done"},
               inputs={"branches": {"goal": {"pending": True}}})
    g.feed(row)
    assert g.current is None and g.pending and g.tick(None, None) is None and g.line() == row["goal"]


def test_a_source_other_than_scripted_is_refused():
    with pytest.raises(ValueError):
        R.replay(run_dir("e5"), source="llm")


def test_with_survival_5_s_a_b_c_off_the_records_diverge_first_at_the_point_blank_and_the_stuck_reads(monkeypatch):
    """Task 1 read every threat line of E5 and F1 agreeing. With P24-A's listing and met window (a), look behind (b)
    and corner yield (c) held off, the first divergences are the other rules': E5 at 236, the `stuck` corner's leg
    under the group of seven at STUCK_RETRY_GROUP_S (fix 1 (1); before fix 1, 241: the attack on 19249 at 0.50
    tiles where the record walked its approach, (e)); F1 at 573, the pin on 15917 (1.09 tiles) held against 15921
    only 0.18 nearer (fix 1 (2), REPIN_MARGIN; the record re-pinned), after 540, where fix 1 (1)'s retry leg now
    agrees with the record's group steer. Before fix 1 F1 diverged first at 540: the corner taken at 537 read
    `stuck` (the steer leg a65 had stood over WALK_STALL_S with 15921 at 1.25 tiles on this tick's record, 1.86 on
    the last tick's, which the stuck read used before (g)), and the group of four did not end it there.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    from agent.base.world import World
    monkeypatch.setattr(S, "MANY_LISTED_N", 10 ** 9)
    monkeypatch.setattr(World, "met_window", lambda self, r=None: None)
    monkeypatch.setattr(S.Survive, "_behind_walk", lambda self: [])
    monkeypatch.setattr(S.Survive, "_walk_yields", lambda self: None)
    e5 = R.agreement(run_dir("e5"), pre_replay("e5"))
    assert (e5["compared"], e5["agree"], e5["first_divergence"]["line"]) == (116, 111, 236)
    assert e5["first_divergence"]["replay"]["why"]["group"] == "retry"
    rep = pre_replay("f1")
    f1 = R.agreement(run_dir("f1"), rep)
    assert (f1["compared"], f1["agree"], f1["first_divergence"]["line"]) == (331, 312, 254)   # named change, below
    assert f1["first_divergence"]["record"]["action"] == {"type": "attack", "args": {"targetId": 15911}}
    assert f1["first_divergence"]["replay"]["why"]["flee"] == "unreachable"
    assert divergences("f1", rep)[:4] == DEAD_LINES + [573]
    _, rec = R.read_record(run_dir("f1"))
    assert rec[572]["action"] == {"type": "attack", "args": {"targetId": 15921}}
    assert rep[572]["action"] == {"type": "attack", "args": {"targetId": 15917}}
    # Named change, Task 12 (ruling P24-O): F1 diverged first at 491, its unbound run legs ending a tick before the
    # record's sprint legs; Task 12 fix 1 binds them through `as_run` (minor 5), so 491 agrees again, and the dead
    # target (the controller's ruling on concern 6) moves 254, 255 and 333 ahead of it: the first divergence past
    # them is 573 again, as before Task 12.


@pytest.mark.parametrize("key,compared,agree,first", [("e5", 116, 109, 219), ("f1", 331, 295, 254)])
def test_the_replay_diverges_from_the_record_first_where_survival_5_moved_it(key, compared, agree, first):
    """The reading at Plan 24 Task 2's recording (an offline oracle's): E5 first at line 219, the fight's walk at
    19275 refused with 19249 and 19278 listed behind it (P24-A (b)); F1 first at 163, the `many` flee on four listed
    within 12 tiles (P24-A (a)), its shelter walk at a sprint where the record's `held` flee ran. Fix 1 re-read:
    E5 109 (112 before; the `stuck` corner's retries, fix 1 (1)), F1 301 (299; its retry at 540 agrees with the
    record's group steer there). Fix 2: F1 297 (G3's health retries at 603-614 where the record swung). Task 12
    (ruling P24-O): a recorded sprint reads as the run the replay sends (`R.as_run`); F1 294, its unbound run legs
    ending at their seconds a tick before the record's at 491 (open loop), and its first divergence moves to 483: at
    163 the replay's `many` shelter walk (once a sprint) is now the record's own `held` walk at a run, the same
    action (the why differs, `listed` 4), and 483 is the `many` flee's steer (four listed) where the record held.
    Task 12 fix 1: F1 295 (the binder reads `as_run`: minor 5), and the dead target (the ruling on concern 6) moves
    F1's first divergence to 254, its swing at 15911 read dead the tick before (the `unreachable` flee from 15885
    instead), with 255 and 333 (the swing at 15937's corpse, the branch passing) after it; 483 is the first past
    them. The review's minor 6: at 163 the action agrees under `as_run` while the reason differs, pinned here.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    rep = pre_rows(key)
    got = R.agreement(run_dir(key), rep)
    assert (got["compared"], got["agree"], got["skipped_world"]) == (compared, agree, 0)
    d = got["first_divergence"]
    assert d["line"] == first
    if key == "e5":
        assert d["record"]["why"]["target"] == 19275 and d["replay"]["why"]["behind"] == [19249, 19278]
        return
    assert d["record"]["action"] == {"type": "attack", "args": {"targetId": 15911}} and d["replay"]["why"]["kill"] == 15911
    assert d["replay"]["why"]["flee"] == "unreachable" and d["replay"]["action"]["type"] == "walkTo"
    divs = divergences(key, rep)
    assert divs[:4] == DEAD_LINES + [483]
    rec = R.read_record(run_dir(key))[1]
    assert rec[482]["action"] is None and rep[482]["inputs"]["branches"]["threat"]["listed"] == 4
    assert rep[482]["action"]["type"] == "steer" and rep[482]["inputs"]["branches"]["threat"]["flee"] == "many"
    r163, p163 = rec[162]["inputs"]["branches"]["threat"], rep[162]["inputs"]["branches"]["threat"]
    assert r163["flee"] == "held" and p163["flee"] == "many" and p163["listed"] == 4 and 163 not in divs
    assert rep[162]["action"] == R.as_run(rec[162]["action"]) and rep[162]["branch"] == rec[162]["branch"] == "threat"


def test_agreement_names_the_first_divergence():
    """Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`)."""
    rows = pre_rows("e5")
    base = R.agreement(run_dir("e5"), rows)["agree"]
    k = next(i for i, r in enumerate(rows) if r["branch"] == "threat" and r["sent"])
    rows[k] = dict(rows[k], action=None, sent=False)
    got = R.agreement(run_dir("e5"), rows)
    assert got["agree"] == base - 1 and got["first_divergence"]["line"] == k + 1
    rows[k] = dict(rows[k], inputs=dict(rows[k]["inputs"], x=0.0))
    assert R.agreement(run_dir("e5"), rows)["skipped_world"] == 1


@pytest.mark.parametrize("key", KEYS)
def test_every_decision_line_aligns_to_one_frame_at_or_before_its_wall(key):
    lines, rows = R.read_record(run_dir(key))
    ends = R.align(lines, rows)
    assert len(ends) == len(rows)
    for (frame_end, wall_end), row in zip(ends, rows):
        f = lines[frame_end - 1]
        assert f["kind"] == "frame" and f["me"]["hour"] == row["inputs"]["hour"] and f["wallMs"] / 1000.0 <= row["wall"]
        assert all(ln["kind"] != "frame" for ln in lines[frame_end:wall_end])


def test_the_recorded_aids_follow_the_session_s_pre_loop_equip():
    lines, rows = R.read_record(run_dir("e5"))
    aids, offset = R.recorded_aids(lines, rows)
    assert offset == 1 and aids[1] == "a2"


# ================================================================ Task 1 fix 1: E2, E3 and E4 (older rules)
@pytest.mark.parametrize("key,compared,agree,first", [("e2", 119, 96, 94), ("e3", 131, 108, 137),
                                                      ("e4", 1341, 1113, 302)])
def test_the_older_records_diverge_where_the_rules_changed_since(key, compared, agree, first):
    """The reading at fix 1's recording: HEAD's decisions over inputs recorded under older rules (E2 at 42e7f49b, E3
    at 145868e2, E4 at 259a58bc); each first divergence is named in the module docstring with its rule. Plan 24
    Task 2 (P24-A) re-read: E2 96 of 119 (97 before), E4 1119 of 1341 (1134), E3 unmoved; the first divergences
    unmoved (the survival 5 rules move these runs only after them). Fix 1 (1)'s retries: E3 108 (113), E4 1113.
    Task 12 (ruling P24-O, a recorded sprint read as a run): E4 1089, its unbound run legs ending at their seconds
    from 524 on (open loop), the first divergence unmoved. Task 12 fix 1 (minor 5: the binder reads `as_run`): E4
    1113 again, its run legs bound to the record's sprinted aids.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    got = R.agreement(run_dir(key), pre_rows(key))
    assert (got["compared"], got["agree"], got["skipped_world"]) == (compared, agree, 0)
    assert got["first_divergence"]["line"] == first


def test_e2_line_94_is_the_reposition_floor(monkeypatch):
    """E2 (42e7f49b) repositioned to (10733, 10642), 0.99 tiles off, under REPOSITION_MIN 1.2 (P23-AJ 5, aa130e9d):
    HEAD walks to (10731, 10642). With the floor at 0 the replay agrees at 94 and first diverges at 98.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    d = R.agreement(run_dir("e2"), pre_rows("e2"))["first_divergence"]
    assert d["record"]["action"]["args"] == {"gait": "run", "x": 10733.5, "y": 10642.5}
    assert d["replay"]["action"]["args"] == {"gait": "run", "x": 10731.5, "y": 10642.5}
    monkeypatch.setattr(P, "REPOSITION_MIN", 0.0)
    assert R.agreement(run_dir("e2"), pre_replay("e2"))["first_divergence"]["line"] == 98


def test_e3_line_137_walks_to_the_kitchen_door_not_the_bedroom_door():
    """E3 (145868e2) took the bedroom door (10725, 10629) for exterior; HEAD's exterior door by its own edge
    (amendment 5, c41f9880) and the room-less kitchen door (R2, 259a58bc) send the approach to (10721, 10638).
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    d = R.agreement(run_dir("e3"), pre_rows("e3"))["first_divergence"]
    assert d["record"]["action"]["args"] == {"gait": "run", "x": 10726.5, "y": 10628.5}
    assert d["replay"]["action"]["args"] == {"gait": "run", "x": 10721.5, "y": 10638.5}
    assert d["record"]["why"]["shelter"] == d["replay"]["why"]["shelter"] == 2


def test_e4_line_302_is_the_cut_leg(monkeypatch):
    """E4 (259a58bc) held its steer a29 when a second zombie was held at 302; HEAD cuts the leg on the new threat
    ahead (P23-AP 3, e07a52cb) and the re-choose walks to building 2's approach. With the cut off the replay agrees
    at 302 and first diverges at 450. Named change, Plan 24 Task 2: with the cut off it now first diverges at 388,
    the met window's turn of a first leg (P24-A (a)); with that off too, at 411, the fight's walk at 19030 refused
    for 19029 and 19031 behind it (P24-A (b)) and the `many` flee on four listed (P24-A (a)); with both off, at 447,
    the `walk` corner on 19032 refused in the running `many` episode (P24-A (c)); with that off, at 452: the R4
    re-pin to 19035 that went at 450, held two lines by P24-A (d) while the pin 19032 stood within POINT_BLANK_R.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    from agent.base.world import World

    def first():
        return R.agreement(run_dir("e4"), pre_replay("e4"))["first_divergence"]
    d = R.agreement(run_dir("e4"), pre_rows("e4"))["first_divergence"]
    assert d["record"]["why"]["holding"] == "a29" and d["replay"]["why"]["step"] == "approach"
    monkeypatch.setattr(P.Flee, "_cut_leg", lambda self: None)
    assert first()["line"] == 388
    monkeypatch.setattr(World, "met_window", lambda self, r=None: None)
    d = first()
    assert d["line"] == 411 and d["replay"]["why"]["flee"] == "many" and d["record"]["why"]["target"] == 19030
    monkeypatch.setattr(S, "MANY_LISTED_N", 10 ** 9)
    d = first()
    assert d["line"] == 411 and d["replay"]["why"]["behind"] == [19029, 19031]
    monkeypatch.setattr(S.Survive, "_behind_walk", lambda self: [])
    d = first()
    assert d["line"] == 447 and d["replay"]["why"]["yield"] == "many"
    monkeypatch.setattr(S.Survive, "_walk_yields", lambda self: None)
    d = first()
    assert d["line"] == 452 and d["replay"]["action"] == {"type": "attack", "args": {"targetId": 19035}}


def test_the_older_goldens_reach_the_hold_breach_door_exit_shelter_stall_and_stuck_paths():
    """Named change, Plan 24 Task 2 (P24-A (a)): E2's five `pair` and `health` lines (186, 192, 208, 209, 211) read
    `many` now (four or five listed within 12 tiles); `pair` stays reached on E5 and F1, `health` on no golden (its
    flee is `test_survive`'s), the corner's `yield` and the `listed`, `behind` and `met` keys on these.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    why = [d["why"] for k in ("e2", "e3", "e4") for d in pre_gold(k).values()]
    flee = {w.get("flee") for w in why}
    assert {"held_inside", "many", "held", "unreachable", "steps", "unarmed"} <= flee
    assert not {"pair", "health"} & flee
    why5 = [d["why"] for k in ("e5", "f1") for d in pre_gold(k).values()]
    assert "pair" in {w.get("flee") for w in why5}
    assert {"yield", "listed", "behind", "met", "corner_kind"} <= set().union(*why, *why5)
    keys = set().union(*why)
    assert {"breach", "door", "exit", "shelter", "step", "stuck", "cut", "group", "cornered"} <= keys
    assert "stalled" in {w.get("ended") for w in why}


def test_closing_ticks_now_moves_the_e2_golden_at_line_164(monkeypatch):
    """The review's M1: a mutant E5 and F1 never saw moves E2 (the `closing` breach)."""
    base = {d["line"]: d for d in json.loads(golden("e2").decode("utf-8"))["decisions"]}
    monkeypatch.setattr(S, "CLOSING_TICKS", 4)
    moved = {d["line"]: d for d in R.run(run_dir("e2"))}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff and diff[0] == 164


# ================================================================ Plan 24 Task 2: survival 5 on the goldens (P24-A)
def gold(key):
    return {d["line"]: d for d in json.loads(golden(key).decode("utf-8"))["decisions"]}


def test_e5_lines_219_to_231_many_fires_on_the_listing_at_220_not_on_the_six_tile_count():
    """P24-A (a) on E5: at 219 three zombies are listed within LISTED_R (19277 at 12.16 tiles just past it), one within
    DANGER_R: no `many` (219's flee is (b)'s); at 220 five are listed, still one within DANGER_R: `many` on the listing
    (`listed` 5), where the record still fought (its `many` came at 222 on the hold radius's count); `many` holds to
    231. The met window (a) turns the first leg at 222 (`met`, seven met).
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    g, rows = pre_gold("e5"), pre_rows("e5")
    assert "listed" not in g[219]["why"] and rows[218]["inputs"]["threats"] == 1
    assert g[220]["why"]["flee"] == "many" and g[220]["why"]["listed"] == 5 and rows[219]["inputs"]["threats"] == 1
    assert all(g[line]["why"]["flee"] == "many" for line in range(220, 232))
    assert g[222]["action"]["type"] == "steer" and g[222]["why"]["met"][2] == 7


def test_e5_line_219_the_fight_s_walk_at_19275_is_refused_for_the_two_listed_behind_it():
    """P24-A (b) on E5's line 219: the record walked at 19275 (5.99 tiles); 19278 (11.04 tiles, 3 degrees off its
    bearing) and 19249 (11.78, 13 degrees) are listed behind it: the flee `held`, the shelter approach walk.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    w = pre_gold("e5")[219]
    assert w["why"]["flee"] == "held" and w["why"]["behind"] == [19249, 19278] and "fight" not in w["why"]
    assert w["action"] == {"type": "walkTo", "args": {"gait": "run", "x": 10721.5, "y": 10638.5}}


def no_group_retry(monkeypatch):
    """P24-A fix 1 (1) switched off: a `stuck` corner under a group retries at STUCK_RETRY_S only, beyond point
    blank, as survival 5 had it (E5's corner then stays to 241, where (d) and (e) are read)."""
    monkeypatch.setattr(S.Survive, "_melee_group", lambda self, held: False)


def test_e5_line_241_the_point_blank_attack_goes_where_the_record_walked(monkeypatch):
    """P24-A (e) on E5's line 241: the cornered Fight's approach was due (two swings not started) with 19249 at 0.50
    tiles: the record walked to its square's centre; the attack goes, its swing running to the record's end (243).
    Fix 1 (1) leaves that corner at 236 for its leg on the golden, so the line is read with it off."""
    no_group_retry(monkeypatch)
    g = {d["line"]: d for d in R.run(run_dir("e5"))}
    assert g[241]["action"] == {"type": "attack", "args": {"targetId": 19249}} and g[241]["why"]["approach"] is False
    assert g[242]["why"]["holding"] == g[243]["why"]["holding"]


def point_blank_walk(monkeypatch):
    """P24-A (e) switched off: the approach flag kept at point blank, the walk sent as before."""
    real_choose = P.Fight._choose

    def choose(self):
        approach = self.approach
        cmd = real_choose(self)
        if approach and cmd is not None and cmd.TYPE == "attack":
            t = self.world.zombies[cmd.targetId]
            self.approach = False
            self.why["approach"] = True
            return P.WalkTo(*P.centre((t["x"], t["y"])), "run")
        return cmd
    monkeypatch.setattr(P.Fight, "_choose", choose)


def repin_any(monkeypatch):
    """P24-A (d) switched off: the pin's own distance unread, a pin within POINT_BLANK_R re-pinned as before."""
    real = P.Fight._repin_point_blank

    def repin(self):
        pin = self.target
        self.target = None
        real(self)
        if self.target is None:
            self.target = pin
        elif self.target != pin:
            self.repositioned = False
    monkeypatch.setattr(P.Fight, "_repin_point_blank", repin)


def test_e5_line_242_with_the_approach_walk_the_pin_within_point_blank_holds(monkeypatch):
    """P24-A (d) on E5, where the golden cannot show it ((e)'s attack at 241 still swings at 242 and the record ends
    at 243): with (e) off the approach walk goes at 241 as recorded, and at 242 19248 stands at 0.51 tiles, nearer
    than the pin 19249 at 0.54, itself within POINT_BLANK_R: the pin holds; with (d) off too, the re-pin to 19248.
    Fix 1 (2): 0.03 nearer, under REPIN_MARGIN, it holds as well. Read with fix 1 (1) off (`no_group_retry`)."""
    no_group_retry(monkeypatch)
    point_blank_walk(monkeypatch)
    held = {d["line"]: d for d in R.run(run_dir("e5"))}
    assert held[241]["action"]["type"] == "walkTo" and held[242]["why"]["target"] == 19249
    repin_any(monkeypatch)
    moved = {d["line"]: d for d in R.run(run_dir("e5"))}
    diff = [k for k in sorted(set(held) | set(moved)) if held.get(k) != moved.get(k)]
    assert diff[0] == 242 and moved[242]["why"]["target"] == 19248


@pytest.mark.parametrize("key,mutant,first", [
    ("e5", "listing", 220), ("e5", "met", 189), ("e5", "behind", 219), ("f1", "yield", 484),
    ("e5", "point_blank", 241), ("e5", "corner_kind", 233), ("f1", "group_retry", 540)])
def test_each_survival_5_rule_switched_off_moves_its_golden_first_at_its_line(monkeypatch, key, mutant, first):
    """The mutation pass on the goldens: each P24-A rule E5 and F1 reach, switched off, moves its golden first at
    the line its own test names ((a) listing 220, met 189; (b) 219; (c) F1 484; (e) 241; (g)'s `corner_kind` 233;
    (d)'s is the test above, behind (e)). (f), (h) and (i) are reached on no golden (no room-square group; PZA/1.3
    frames carry no `attackers` or `hitReaction`): their mutants fail `test_survive`'s and `test_policies`' cases.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    from agent.base.world import World
    if mutant == "point_blank":   # (e) is read behind fix 1 (1), which leaves E5's corner at 236
        no_group_retry(monkeypatch)
        base = {d["line"]: d for d in pre_run(key)}
    else:
        base = pre_gold(key)
    if mutant == "listing":
        monkeypatch.setattr(S, "MANY_LISTED_N", 10 ** 9)
    elif mutant == "met":
        monkeypatch.setattr(World, "met_window", lambda self, r=None: None)
    elif mutant == "behind":
        monkeypatch.setattr(S.Survive, "_behind_walk", lambda self: [])
    elif mutant == "yield":
        monkeypatch.setattr(S.Survive, "_walk_yields", lambda self: None)
    elif mutant == "point_blank":
        point_blank_walk(monkeypatch)
    elif mutant == "group_retry":
        no_group_retry(monkeypatch)
    elif mutant == "corner_kind":
        real_decide = S.Survive._decide

        def decide(self, held, breach, replanned=False):
            out = real_decide(self, held, breach, replanned)
            self.why.pop("corner_kind", None)
            return out
        monkeypatch.setattr(S.Survive, "_decide", decide)
    moved = {d["line"]: d for d in pre_run(key)}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff and diff[0] == first


@pytest.mark.parametrize("key", ["e5", "f1"])
def test_the_pza1_3_records_carry_no_attackers_or_hit_reaction(key):
    """P24-A (h) and (i) read PZA/1.4's `me.attackers` and `me.hitReaction`; E5's and F1's frames (PZA/1.3) decode
    them None, so neither rule moves these goldens."""
    lines, _ = R.read_record(run_dir(key))
    frames = [ln for ln in lines if ln["kind"] == "frame"]
    assert frames and all(f["me"].get("attackers") is None and f["me"].get("hitReaction") is None for f in frames)


# ================================================================ Plan 24 Task 2 fix 2 on the goldens (the review's G1-G3)
def test_f1_line_540_the_stuck_corner_under_four_sends_the_retry_steer():
    """G1 (fix 1 (1) with the nearest within POINT_BLANK_R): at F1 line 540, four held, the nearest at 0.44 tiles and
    the stuck read of 537 1.52 s old, the `stuck` corner sends its retry leg, as the record steered there."""
    g = gold("f1")
    assert g[537]["why"]["corner_kind"] == "stuck"
    assert g[540]["action"]["type"] == "steer" and g[540]["why"]["group"] == "retry"


def test_e4_line_455_the_retry_leg_turns_off_the_stuck_heading_of_449():
    """G2: the retry's Flee is new, so before fix 2 its first leg forgot the stuck leg (aimed 1.2 degrees from it on
    f6fa1d3b's golden); now the stuck heading is carried (`skip`) and the leg turns at least STUCK_SKIP_DEG off it.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    g = pre_gold("e4")
    stuck = g[449]["action"]["args"]
    leg = g[455]
    assert leg["why"]["group"] == "retry" and leg["why"]["skip"] == [stuck["vx"], stuck["vy"]]
    cos = leg["action"]["args"]["vx"] * stuck["vx"] + leg["action"]["args"]["vy"] * stuck["vy"]
    assert cos < math.cos(math.radians(P.STUCK_SKIP_DEG))


def test_f1_s_second_stuck_corner_no_longer_holds_to_the_end_under_flee_health():
    """G3 (ruling P24-E) on F1's 572-615: the `stuck` corner of 572 held through health 33.8 (607) to 0.9 (615);
    under FLEE_HEALTH_PAIR with two held it now tries a leg each STUCK_RETRY_GROUP_S (603, 608, 614, `yield`
    "health"). Open loop: the record's frames do not move with those legs."""
    g = gold("f1")
    retries = [k for k in range(572, 616) if g[k]["why"].get("group") == "retry"]
    assert retries == [603, 608, 614] and all(g[k]["why"]["yield"] == "health" for k in retries)
    assert all(g[k]["action"]["type"] == "steer" for k in retries)


# ================================================================ Task 10 fix 1: the sixth golden (the review's major 3)
SIXTH = "f1-caps15"


def run_sixth():
    return R.run(run_dir(SIXTH), caps=R.HELLO_CAPS[SIXTH])


def moved_from_sixth(rows):
    base, got = gold(SIXTH), {d["line"]: d for d in rows}
    return [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]


def pre_moved_from_sixth(rows):
    """`moved_from_sixth` against the sixth golden as recorded before P24-X (`pre_gold`)."""
    base, got = pre_gold(SIXTH), {d["line"]: d for d in rows}
    return [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]


def test_the_sixth_golden_is_f1_s_inputs_with_the_pza1_5_caps_reproduced_byte_for_byte():
    """A regression pin of HEAD's decisions over real frames with the stance, care, fill and climb on (the record's
    own hello announced none: `World.can`), never an agreement oracle: F1's frames, its hello's caps plus CAPS_15."""
    raw = golden(SIXTH)
    head = json.loads(raw.decode("utf-8"))
    assert R.RUNS[SIXTH] == R.RUNS["f1"] == head["artifact"] and head["caps"] == list(R.CAPS_15)
    assert R.CAPS_15 == ("aim", "climb", "bandage", "rip", "wash", "fill") and "span" not in head
    text = R.golden_text(run_sixth(), head["base"], head["artifact"], head["recorded"], None, head["caps"])
    assert text.encode("utf-8") == raw and b"\r" not in raw and raw.endswith(b"}\n")
    a, b = run_sixth(), run_sixth()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert all(d["branch"] != "goal" for d in a)


def test_with_caps_adds_the_skills_to_a_hello_only():
    hello = {"kind": "hello", "caps": ["attack", "aim"]}
    assert R.with_caps(hello, R.CAPS_15)["caps"] == ["attack", "aim", "climb", "bandage", "rip", "wash", "fill"]
    assert R.with_caps(hello, None) is hello and hello["caps"] == ["attack", "aim"]
    frame = {"kind": "frame", "caps": None}
    assert R.with_caps(frame, R.CAPS_15) is frame


def test_the_sixth_golden_moves_first_at_line_106_the_first_stance_leg_where_f1_walked():
    """Its first moved line against F1's golden is the faithful one: at 106 the fight engaged 15885 at 5.90 tiles,
    the record's walk at a run; with `aim` announced the Fight meets it in the stance. Every later line of the episode
    is open loop (the record's frames follow the walk).
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    six, f1 = pre_gold(SIXTH), pre_gold("f1")
    first = next(k for k in sorted(f1) if f1[k] != six.get(k))
    assert first == 106 and f1[106]["action"]["type"] == "walkTo"
    assert six[106]["action"]["type"] == "aim" and six[106]["action"]["args"]["targetId"] == 15885
    assert six[106]["why"]["stance"] is True and six[106]["why"]["stand_s"] == 0.0
    assert {d["action"]["type"] for d in six.values() if d["action"]} == {"aim", "walkTo", "steer", "attack"}


def test_with_the_stand_decision_off_the_sixth_golden_is_f1_s_own(monkeypatch):
    """The mutation pass: `_stance_ok` False gives F1's golden decisions line for line (the stance is the only rule
    the PZA/1.5 caps reach on F1's frames: no part bleeds, no square holds water, no goal is replayed).
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    monkeypatch.setattr(S.Survive, "_stance_ok", lambda self, held, inside: False)
    got = {d["line"]: d for d in pre_run(SIXTH)}
    assert got == pre_gold("f1") and pre_moved_from_sixth(list(got.values()))[0] == 106


def test_the_replay_ends_an_unbound_aim_at_its_seconds(monkeypatch):
    """THE ACTS (Task 10 fix 1): an unbound `aim` ends `done` at its `seconds`, as a steer does. Named change (Task
    12, ruling P24-N): on the sixth golden the leg held open no longer moves anything, since a standing leg gives way
    the tick its target comes inside KEEP_R (111, 2.46 tiles, 2.53 s after 106's leg) and the backpedal it sends
    there is the leg the ended one re-aimed; `end_legs` itself is pinned here on its own.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    from agent.base.actions import Action
    acts = R._Acts(None, {})
    leg = Action(aid="a1", type="aim", args={"vx": 0.0, "vy": 0.0, "seconds": 2.0, "targetId": 1, "bearing": -1.0},
                 deadline_s=30.0, sent_wall=100.0)
    walk = Action(aid="a2", type="walkTo", args={"x": 1, "y": 2, "gait": "run"}, deadline_s=30.0, sent_wall=100.0)
    acts.unbound = [leg, walk]
    acts.end_legs(101.9)
    assert leg.state == "sent"
    acts.end_legs(102.0)
    assert (leg.state, leg.ended_wall, walk.state) == ("done", 102.0, "sent") and R.LEG_TYPES == ("steer", "aim")
    six = pre_gold(SIXTH)
    assert six[111]["action"]["type"] == "aim" and six[110]["why"]["holding"] == "a12"
    assert six[111]["why"]["leg"] == "back" and six[111]["why"]["dist"] <= P.KEEP_R
    monkeypatch.setattr(R, "LEG_TYPES", ("steer",))
    assert pre_moved_from_sixth(pre_run(SIXTH)) == []


def test_keep_r_and_the_advance_on_the_sixth_golden(monkeypatch):
    """Ruling P24-N (Task 12, re-recorded under it): of the stance legs on F1's frames the ones whose target is
    inside KEEP_R backpedal, 111 (2.46 tiles), 114 and 362 (2.05: the standing leg sent at 360, 5.78 tiles off, gives
    way the tick its target comes inside KEEP_R, the one decision P24-N moved; P24-M's band held that leg); the others
    (2.78 to 6.00 tiles) stand facing the target. Named change (Task 12 fix 1, the review's major 1): the backpedal of
    111 gives way at 112, its target 2.78 tiles off (past KEEP_R + KEEP_MARGIN), to a standing leg, which gives way
    at 114 (2.18 tiles) to the next backpedal. Line 373's target, 16.96 tiles off, is beyond the Lua's aim range
    (AIM_R 12), so the Fight walks at a run as the approach does. The mutation pass: KEEP_R at FIGHT_REACH (no
    backpedal) or at 2.4 moves the golden first at 111; a standing leg that never gives way inside KEEP_R moves it
    first at 114; a backpedal that never gives way on distance (Task 12's rule) first at 112; STAND_MAX_S switched
    off (infinite) or at 5 s moves nothing, since no stand on F1's frames reaches it (the longest stand clock is 2.53
    s, line 114), and at 2 s (the advance at 111) it moves the golden first at 111: the advance runs on a real
    sequence, but this golden cannot pin its 20 s (the fake-mod cases do).
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    six = pre_gold(SIXTH)
    legs = {k: d for k, d in six.items() if d["action"] and d["action"]["type"] == "aim"}
    assert sorted(legs) == [106, 111, 112, 114, 192, 216, 288, 360, 362, 435, 517, 557]
    back = [k for k, d in legs.items() if (d["action"]["args"]["vx"], d["action"]["args"]["vy"]) != (0.0, 0.0)]
    assert back == [111, 114, 362] and all(legs[k]["why"]["leg"] == "back" for k in back)
    assert legs[112]["why"]["leg"] == "stand" and legs[112]["why"]["dist"] > P.KEEP_R + P.KEEP_MARGIN
    assert max(legs[k]["why"]["dist"] for k in back) <= P.KEEP_R < min(
        d["why"]["dist"] for k, d in legs.items() if k not in back)
    assert all(d["why"]["leg"] == "stand" for k, d in legs.items() if k not in back)
    assert max(d["why"].get("stand_s") or 0.0 for d in six.values()) < P.STAND_MAX_S
    assert not any(d["why"].get("advance") for d in six.values())
    assert six[373]["action"] == {"type": "walkTo", "args": {"gait": "run", "x": 10734.5, "y": 10625.5}}
    assert six[373]["why"]["dist"] > P.AIM_R
    for name, val, first in (("KEEP_R", P.FIGHT_REACH, 111), ("KEEP_R", 2.4, 111), ("STAND_MAX_S", math.inf, None),
                             ("STAND_MAX_S", 5.0, None), ("STAND_MAX_S", 2.0, 111)):
        old = getattr(P, name)
        monkeypatch.setattr(P, name, val)
        moved = pre_moved_from_sixth(pre_run(SIXTH))
        assert (moved[0] if moved else None) == first, (name, val)
        monkeypatch.setattr(P, name, old)
    busy = P.Fight.busy

    def stand_holds(self):   # P24-N's give-way of a standing leg inside KEEP_R removed
        if P.Policy.busy(self) and self.last.type == "aim" and self._leg == "stand":
            t = self._target(pin=False)
            return t is not None and t[0] == self.last.args.get("targetId") and t[2] > P.FIGHT_REACH
        return busy(self)
    monkeypatch.setattr(P.Fight, "busy", stand_holds)
    assert pre_moved_from_sixth(pre_run(SIXTH))[0] == 114

    def back_holds(self):   # Task 12 fix 1's give-way of a backpedal past KEEP_R + KEEP_MARGIN removed
        if P.Policy.busy(self) and self.last.type == "aim" and self._leg == "back":
            t = self._target(pin=False)
            return t is not None and t[0] == self.last.args.get("targetId") and t[2] > P.FIGHT_REACH
        return busy(self)
    monkeypatch.setattr(P.Fight, "busy", back_holds)
    assert pre_moved_from_sixth(pre_run(SIXTH))[0] == 112


def test_agreement_reads_a_recorded_sprint_as_the_run_p24_o_sends():
    """Task 12 (ruling P24-O): `as_run` maps a sprint gait to run and leaves any other action as it is.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    sprint = {"type": "steer", "args": {"vx": 1.0, "vy": 0.0, "seconds": 3.0, "gait": "sprint"}}
    assert R.as_run(sprint) == {"type": "steer", "args": {"vx": 1.0, "vy": 0.0, "seconds": 3.0, "gait": "run"}}
    assert sprint["args"]["gait"] == "sprint" and R.as_run(None) is None
    walk = {"type": "walkTo", "args": {"x": 1, "y": 2, "gait": "walk"}}
    assert R.as_run(walk) is walk and R.as_run({"type": "attack", "args": {"targetId": 1}})["args"] == {"targetId": 1}
    got = R.agreement(run_dir("f1"), pre_rows("f1"))
    assert got["gait_only"] == 4   # Task 12 fix 1: the legs bound through `as_run` agree at 491 and 498 too


def test_the_binder_reads_a_recorded_sprint_as_the_run_the_planner_sends():
    """The review's minor 5: a replayed leg equal to the record's under `as_run` binds to the record's aid, so its
    record's act lines end it (E4's tail from 524 and F1's 491-502 were unbound and open loop at Task 12); a walk at
    another gait or a run against a recorded walk does not."""
    acts = R._Acts(None, {3: "a9"})
    from agent.base.actions import Action
    leg = Action(aid="a5", type="steer", args={"vx": 1.0, "vy": 0.0, "seconds": 3.0, "gait": "run"}, deadline_s=30.0,
                 sent_wall=1.0)
    row = {"sent": True, "action": {"type": "steer", "args": dict(leg.args, gait="sprint")}}
    acts.sent(3, row, leg, [], 1.0)
    assert acts.bound == {"a9": leg} and acts.unbound == []
    walk = Action(aid="a6", type="walkTo", args={"x": 1.5, "y": 2.5, "gait": "run"}, deadline_s=30.0, sent_wall=2.0)
    acts.sent(3, {"sent": True, "action": {"type": "walkTo", "args": dict(walk.args, gait="walk")}}, walk, [], 2.0)
    assert acts.unbound == [walk]


def test_f1_reads_three_kills_off_its_recorded_attack_results():
    """Ruling P24-Q (Task 12): F1's bound attacks carry the record's results; three read `targetDead` (15911 at 254,
    15937 at 333, 15885 at 454), each logged once as the threat why's `kill`; the other goldens read none (no bound
    result of theirs reads `targetDead` true), and the sixth's replayed attacks are unbound (open loop) so read none.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1.
    """
    kills = {k: d["why"]["kill"] for k, d in pre_gold("f1").items() if "kill" in d["why"]}
    assert kills == {254: 15911, 333: 15937, 454: 15885}
    for key in ("e2", "e3", "e4", "e5", SIXTH):
        assert not any("kill" in d["why"] for d in pre_gold(key).values()), key


# ================================================================ Plan 24 Task 18: P24-X on the goldens
# the six goldens as recorded at 24987f2a (iteration 7): sha256 of the file, its base and its recorded date
PRE_X = {"e2": ("36a05b652b897183af2fc13254eab35b4c9cb9251720be1c3d4642181778e9d7", "fd74ad62"),
         "e3": ("172c02ba249aee8874ee1d196a5856e0d2d2a8ee6483aa88de8f03ef8cf83f26", "8d73d87f"),
         "e4": ("77b8a64ad3e0ac8fdc5e426e4eca5b3a25bbd25ae97cb8ec2db4dc55ece01fa8", "9e973194"),
         "e5": ("a660b1d337b6daf36fff7ed5c70f9c19f223a38ad2dbddfea1e17806879885d6", "8d73d87f"),
         "f1": ("fd7e223a8524b853f1ba64e68af43e0fcf536c1e09533f773a19a895dca64766", "e5fd5eb8"),
         SIXTH: ("1f3bd400786b3cc7be9cad360a575088164ebc091d666b219ed005f2f7a2a4e7", "9e973194")}


@pytest.mark.parametrize("key", sorted(PRE_X))
def test_with_engage_off_the_goldens_are_iteration_7_s(key):
    """P24-X is one switch (`Survive.ENGAGE`): with it off every golden is the file recorded at 24987f2a byte for byte
    (its sha256 pinned), so every line P24-X moved is P24-X's (the engage within ENGAGE_R, the flee's turn at the
    fight's line, the seek)."""
    sha, base = PRE_X[key]
    text = R.golden_text(R.decisions(pre_rows(key)), base, R.RUNS[key], "2026-10-29", R.SPANS.get(key),
                         R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


# the first line P24-X (as Task 18 fix 1 narrowed it) moves on each golden, and the zombie it engages there
FIRST_ENGAGE = {"e2": (68, 12787), "e3": (69, 14910), "e4": (247, 19001), "e5": (69, 19223), "f1": (102, 15885),
                SIXTH: (102, 15885)}   # fix 1's minor 8 (ENGAGE_R 9): e2 67, e3 68, e5 68, f1 100 at ENGAGE_R 10


@pytest.mark.parametrize("key", sorted(PRE_X))
def test_p24_x_moves_every_golden_first_at_its_first_engage_where_the_record_s_goal_ran(key):
    """Named change, Task 18 fix 1 (the review's major 2 and ruling 2): Task 18 moved every golden first at line 1,
    the engage of the zombie listed 7.0 tiles from the fixture's spawn; that zombie stands idle on ground the first
    frame's map does not hold, and the spawn is a room square, so it is no longer engaged
    (`test_survive_h.test_the_spawn_engage_in_every_golden_is_neither_engaged_nor_sought`). Each golden now moves
    first where the record's goal ran with a zombie within ENGAGE_R the engage reaches (the faithful line; the episode
    after it is open loop): a fight on it, the approach at a run on the five PZA/1.4 builds, the seek's walk round a
    wall at a walk on the sixth."""
    g, pre = gold(key), pre_gold(key)
    first = min(k for k in set(g) | set(pre) if g.get(k) != pre.get(k))
    line, zid = FIRST_ENGAGE[key]
    assert first == line and line not in pre and 1 not in g
    w = g[line]["why"]
    assert g[line]["branch"] == "threat" and w["fight"] is True and w["target"] == zid
    assert w["dist"] > P.DANGER_R and w["dist"] <= P.ENGAGE_R
    if key == SIXTH:
        assert g[line]["action"]["args"]["gait"] == "walk" and w["seek"] is True and w["leg"] == "walk"
    else:
        assert g[line]["action"]["type"] == "walkTo" and g[line]["action"]["args"]["gait"] == "run" and "seek" not in w


@pytest.mark.parametrize("key", sorted(PRE_X))
def test_on_every_golden_no_goal_runs_while_a_fight_is_sought(key):
    """P24-X: the goal branch never runs while one or two zombies within ENGAGE_R are to be sought: on every replayed
    tick that reaches the goal branch `_sought()` answers None."""
    seen = []

    def watch(sv):
        real = sv._goal

        def goal():
            seen.append(sv._sought())
            return real()
        sv._goal = goal
    R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=watch)
    assert seen and all(x is None for x in seen)
    pre = []

    def watch_pre(sv):
        pre_x(sv)
        real = sv._goal

        def goal():
            sv.ENGAGE = True
            pre.append(sv._sought())
            sv.ENGAGE = False
            return real()
        sv._goal = goal
    R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=watch_pre)
    assert any(x is not None for x in pre)   # before P24-X the goal ran with a fight to seek


def test_the_sixth_golden_s_seek_walk_round_the_wall_gives_way_at_the_first_tick_inside_keep_r(monkeypatch):
    """Task 18 fix 1, the review's blocker on the sixth golden: the seek's walk round the wall on 15885 (line 102,
    8.25 tiles; line 100 at 9.48 before minor 8's ENGAGE_R 9) holds while its target stays beyond KEEP_R and gives way
    at line 111, the first tick inside it (2.46 tiles): the backpedal, iteration 7's stance. The mutant (the walk never
    gives way) moves the golden first there."""
    g = gold(SIXTH)
    assert g[102]["action"]["type"] == "walkTo" and g[102]["why"]["seek"] is True
    held = [k for k in range(103, 111) if g[k]["why"].get("holding") == "a12"]
    assert held == list(range(103, 111))
    assert g[111]["why"]["leg"] == "back" and g[111]["why"]["dist"] <= P.KEEP_R
    monkeypatch.setattr(P.Fight, "_walk_gives_way", lambda self: False)
    moved = {d["line"]: d for d in R.run(run_dir(SIXTH), caps=R.HELLO_CAPS[SIXTH])}
    diff = [k for k in sorted(set(g) | set(moved)) if g.get(k) != moved.get(k)]
    assert diff[0] == 111 and moved[111]["why"]["holding"] == "a12"
