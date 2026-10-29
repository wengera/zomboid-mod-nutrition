"""The Survive decision golden (Plan 24 Task 1): `agent.base.replay_decisions` over E5 and F1.

Each golden is reproduced byte for byte from its artifact; a re-record is only under a named behaviour change
(`replay_decisions`' docstring, CLAUDE.md § 6 golden trace)."""
import functools
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


def golden(key):
    with open(R.golden_path(key), "rb") as f:
        return f.read()


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


def test_a_smaller_cornered_r_moves_the_f1_golden_first_at_line_537(monkeypatch):
    """The mutation pass: CORNERED_R 1.5 -> 1.0 (survive's and policies' copies). At F1's line 537 the golden's corner
    attack on 15921 goes; the replay with the mutant sends nothing there."""
    base = {d["line"]: d for d in json.loads(golden("f1").decode("utf-8"))["decisions"]}
    assert base[537]["action"] == {"type": "attack", "args": {"targetId": 15921}}
    monkeypatch.setattr(S, "CORNERED_R", 1.0)
    monkeypatch.setattr(P, "CORNERED_R", 1.0)
    moved = {d["line"]: d for d in R.run(run_dir("f1"))}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff and diff[0] == 537
    assert moved[537]["action"] is None


def test_without_the_trailing_read_rule_f1_moves_at_line_498(monkeypatch):
    """The act model's own falsifier: a60's `done` (written 2 ms before line 498's wall) taken at 498 sends the next
    steer a tick early, where the record still ran a60."""
    base = {d["line"]: d for d in json.loads(golden("f1").decode("utf-8"))["decisions"]}
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


@pytest.mark.parametrize("key,compared", [("e5", 116), ("f1", 331)])
def test_the_replay_agrees_with_the_record_at_every_threat_line(key, compared):
    """The reading at the goldens' recording (an offline oracle's; a later divergence is a finding to name)."""
    rows = replay_rows(key)
    got = R.agreement(run_dir(key), rows)
    assert got == {"compared": compared, "agree": compared, "skipped_world": 0, "first_divergence": None}
    _, rec = R.read_record(run_dir(key))
    assert [r["inputs"]["branches"].get("threat") for r in rows] == [r["inputs"]["branches"].get("threat") for r in rec]


def test_agreement_names_the_first_divergence():
    rows = replay_rows("e5")
    k = next(i for i, r in enumerate(rows) if r["branch"] == "threat" and r["sent"])
    rows[k] = dict(rows[k], action=None, sent=False)
    got = R.agreement(run_dir("e5"), rows)
    assert got["agree"] == got["compared"] - 1 and got["first_divergence"]["line"] == k + 1
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
@pytest.mark.parametrize("key,compared,agree,first", [("e2", 119, 97, 94), ("e3", 131, 113, 137),
                                                      ("e4", 1341, 1134, 302)])
def test_the_older_records_diverge_where_the_rules_changed_since(key, compared, agree, first):
    """The reading at fix 1's recording: HEAD's decisions over inputs recorded under older rules (E2 at 42e7f49b, E3
    at 145868e2, E4 at 259a58bc); each first divergence is named in the module docstring with its rule."""
    got = R.agreement(run_dir(key), replay_rows(key))
    assert (got["compared"], got["agree"], got["skipped_world"]) == (compared, agree, 0)
    assert got["first_divergence"]["line"] == first


def test_e2_line_94_is_the_reposition_floor(monkeypatch):
    """E2 (42e7f49b) repositioned to (10733, 10642), 0.99 tiles off, under REPOSITION_MIN 1.2 (P23-AJ 5, aa130e9d):
    HEAD walks to (10731, 10642). With the floor at 0 the replay agrees at 94 and first diverges at 98."""
    d = R.agreement(run_dir("e2"), replay_rows("e2"))["first_divergence"]
    assert d["record"]["action"]["args"] == {"gait": "run", "x": 10733.5, "y": 10642.5}
    assert d["replay"]["action"]["args"] == {"gait": "run", "x": 10731.5, "y": 10642.5}
    monkeypatch.setattr(P, "REPOSITION_MIN", 0.0)
    assert R.agreement(run_dir("e2"), R.replay(run_dir("e2")))["first_divergence"]["line"] == 98


def test_e3_line_137_walks_to_the_kitchen_door_not_the_bedroom_door():
    """E3 (145868e2) took the bedroom door (10725, 10629) for exterior; HEAD's exterior door by its own edge
    (amendment 5, c41f9880) and the room-less kitchen door (R2, 259a58bc) send the approach to (10721, 10638)."""
    d = R.agreement(run_dir("e3"), replay_rows("e3"))["first_divergence"]
    assert d["record"]["action"]["args"] == {"gait": "run", "x": 10726.5, "y": 10628.5}
    assert d["replay"]["action"]["args"] == {"gait": "run", "x": 10721.5, "y": 10638.5}
    assert d["record"]["why"]["shelter"] == d["replay"]["why"]["shelter"] == 2


def test_e4_line_302_is_the_cut_leg(monkeypatch):
    """E4 (259a58bc) held its steer a29 when a second zombie was held at 302; HEAD cuts the leg on the new threat
    ahead (P23-AP 3, e07a52cb) and the re-choose walks to building 2's approach. With the cut off the replay agrees
    at 302 and first diverges at 450."""
    d = R.agreement(run_dir("e4"), replay_rows("e4"))["first_divergence"]
    assert d["record"]["why"]["holding"] == "a29" and d["replay"]["why"]["step"] == "approach"
    monkeypatch.setattr(P.Flee, "_cut_leg", lambda self: None)
    assert R.agreement(run_dir("e4"), R.replay(run_dir("e4")))["first_divergence"]["line"] == 450


def test_the_older_goldens_reach_the_hold_breach_door_exit_shelter_stall_and_stuck_paths():
    why = [d["why"] for k in ("e2", "e3", "e4") for d in json.loads(golden(k).decode("utf-8"))["decisions"]]
    flee = {w.get("flee") for w in why}
    assert {"held_inside", "many", "held", "pair", "health", "unreachable", "steps", "unarmed"} <= flee
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
