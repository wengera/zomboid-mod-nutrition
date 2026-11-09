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
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T


def run_dir(key):
    return os.path.join(R.ARTIFACTS, R.RUNS[key])


@functools.lru_cache(maxsize=5)
def replayed(key):
    return json.dumps(R.replay(run_dir(key)), sort_keys=True)


def replay_rows(key):
    return json.loads(replayed(key))


# ---------------------------------------------------------------- P28-F's planner side (Plan 28 Task 3 fix 1, R2)
# The stance is not read held after an attack (review-t1b R2: the Lua releases it on the attack's first tick and keeps
# none after the swing; `fight.Fight.in_stance`), a named change with no switch: the sixth golden's files before it
# that an older seam reproduced (PRE_AD, PRE_AG, PRE_AN) are no longer HEAD's replay, so those three cases re-run on a
# `git archive` of the last build reading the hold (CLAUDE.md § 5: a replay broken at HEAD by a later change re-runs on
# the last build whose pins it held), the archive holding the planner, the tests, the data and F1's artifact
R2_FROZEN = "361324b7"
R2_FROZEN_NODES = ("test_the_sixth_golden_is_f1_s_inputs_with_the_pza1_5_caps_reproduced_byte_for_byte",
                   "test_with_idle_off_the_goldens_are_iteration_8_s[f1-caps15]",
                   "test_with_strain_off_the_goldens_are_iteration_9_s[f1-caps15]",
                   "test_with_iteration_11_off_the_goldens_are_task_27_s[f1-caps15]")


@functools.lru_cache(maxsize=1)
def _r2_frozen_run():
    """(returncode, output, the sixth golden's text there) of the sixth-golden cases (R2_FROZEN_NODES: its byte for
    byte replay, then the three older seams) run once in a child pytest on a `git archive` of R2_FROZEN; skipped where
    git or the commit is not reachable (a source export with no history)."""
    import io
    import subprocess
    import sys
    import tarfile
    import tempfile
    paths = ["pytest.ini", "data", "testing/agent", "testing/PZAgent", "testing/tests/conftest.py",
             "testing/tests/slow_tests.txt", "testing/tests/pzagent", "testing/artifacts/" + R.RUNS["f1"]]
    try:
        blob = subprocess.run(["git", "-C", R.REPO, "archive", "--format=tar", R2_FROZEN] + paths,
                              capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip("no git archive of %s: %s" % (R2_FROZEN, e))
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
            tf.extractall(tmp, filter="data")
        nodes = ["testing/tests/pzagent/test_replay_decisions.py::" + n for n in R2_FROZEN_NODES]
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider"] + nodes,
                             cwd=tmp, capture_output=True, text=True,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        with open(os.path.join(tmp, "testing", "tests", "pzagent", "golden", "survive-decisions-%s.json" % SIXTH),
                  encoding="utf-8", newline="") as f:
            text = f.read()
    return run.returncode, run.stdout[-4000:] + run.stderr[-2000:], text


def r2_frozen(node):
    """Asserts the case `node` (one of R2_FROZEN_NODES) passed on R2_FROZEN's archive."""
    rc, out, _ = _r2_frozen_run()
    assert rc == 0 and "PASSED testing/tests/pzagent/test_replay_decisions.py::" + node in out, out


# ---------------------------------------------------------------- the rules before Task 32 (survival iteration 11)
def pre_an(sv):
    """The replay's mutate seam onto the rules before Plan 24 Task 32 (survival iteration 11): `Survive.PULL` (P24-AN,
    the pull), `Survive.DOORWAY` (P24-AO, the doorway stand) and `Survive.TRANS` (P24-AS, the transparent solid in a
    heading read) off. P24-AN's listing count, P24-AP, P24-AQ and P24-AR stay on: they read what no record carries or
    what every record carries alike (`hasTarget` on every listed zombie, no `armPain`, `onFloor` or part `bleeding`:
    `test_no_record_carries_what_iteration_11_reads`), so with these three off every golden is the file as it stood
    before Task 32 byte for byte (`test_with_iteration_11_off_the_goldens_are_task_27_s`). Task 32 fix 1: its two
    switches (`fix1_off`: `HOLD_WIDE`, ruling R2, and `STANCE_LISTED`, the review's major 6) off with them."""
    sv.PULL = False
    sv.DOORWAY = False
    sv.TRANS = False
    fix1_off(sv)


def fix1_off(sv):
    """The replay's mutate seam onto the rules as Task 32 landed them (`45e099ea`): Task 32 fix 1's switches off,
    `Survive.HOLD_WIDE` (ruling R2: every hold kind fights within KEEP_R, no swing under any) and
    `Survive.STANCE_LISTED` (the stance's count of the standing held within DANGER_R or chasing). The fix's other
    rules read what no record carries (`onFloor`, `armPain`, a part's `bleeding`, a `many` shelter at a door: the
    doorway's post, its ends and its walk back, FINISH_R, the care tick's drag exclusion) or move nothing (the
    `solidTrans` reads of the ride and the reposition: `test_fix_1_moves_f1_and_the_sixth_at_r2_and_no_other_golden`).
    Task 36: iteration 12's switches (`pre_t36`) off with them."""
    sv.HOLD_WIDE = False
    sv.STANCE_LISTED = False
    pre_t36(sv)


# Plan 24 Task 36 (survival iteration 12): the switches of the rules that move a golden
T36_SWITCHES = ("EDGE", "PICK_WHY")


def pre_t36(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 24 Task 36 (survival iteration 12): its golden movers off
    (`T36_SWITCHES`: `Survive.EDGE`, P24-AU's edge hold; `Survive.PICK_WHY`, P24-AX's `doorway_pick` on every `many`
    line), but those named in `keep`. P24-AT reads what no record
    carries (`body.strain`, `body.armPain`: `test_no_record_carries_a_pza1_7_read`), so it has no switch. Plan 25 Task
    3: iteration 13's switches (`pre_t3`) off with them, in every seam onto an earlier rule."""
    for name in T36_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t3(sv)


def pre_t3(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 25 Task 3 (survival iteration 13): its switches off
    (`survive.T3_SWITCHES`: CORNER_BREAK, P25-A; FINISH_FIRST, P25-B; HOLD_RUN, P25-C; RIDE_WAIT, P25-D; DOOR_WALK,
    P25-E; FENCE_WAIT, P25-F), but those named in `keep`. Plan 25 Task 7: iteration 14's switch (`pre_t4`) off with
    them, so every seam onto an earlier rule reads it off."""
    for name in S.T3_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t4(sv)


def pre_t4(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 25 Task 7 (survival iteration 14): its switches off
    (`survive.T4_SWITCHES`: UNWEAR_WOUND, P25-H; Task 8's FINISH_FAR, P25-J, STAND_WOUND, P25-K, SHOVE_BREAK,
    P25-L, and SHELTER_LEGS, P25-N), but those named in `keep`. P25-G (the shun loop: the goal source, the runner's
    cooling, the view's `shunned` why), P25-I (the corner's third branch's why), P25-M (the hold's `release` why)
    and P25-O (the hello's two-number mod version, a defect fix: no golden's hello reads "1.7") move no golden, so
    they have no switch (`test_iteration_14_moves_no_golden`). Plan 25 Task 10: iteration 15's switches (`pre_t5`) off
    with them, so every seam onto an earlier rule reads them off."""
    for name in S.T4_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t5(sv)


def pre_t5(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 25 Task 10 (survival iteration 15): its switches off
    (`survive.T5_SWITCHES`), but those named in `keep` (`test_iteration_15_moves_no_golden`). Plan 25 Task 14:
    iteration 16's switches (`pre_t6`) off with them, so every seam onto an earlier rule reads them off."""
    for name in S.T5_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t6(sv)


def pre_t6(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 25 Task 14 (survival iteration 16): its switches off
    (`survive.T6_SWITCHES`), but those named in `keep` (`test_iteration_16_moves_no_golden`). Plan 26 Task 2:
    iteration 17's switches (`pre_t7`) off with them, so every seam onto an earlier rule reads them off."""
    for name in S.T6_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t7(sv)


def pre_t7(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 26 Task 2 (survival iteration 17): its switches off
    (`survive.T7_SWITCHES`), but those named in `keep` (the one-switch form `pre_t3`'s tests use; no test passes it
    here). Plan 26 Task 7: iteration 18's switches (`pre_t8`) off with them, so every seam onto an earlier rule reads
    them off."""
    for name in S.T7_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t8(sv)


def pre_t8(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 26 Task 7 (survival iteration 18): its switches off
    (`survive.T8_SWITCHES`), but those named in `keep` (the one-switch form `pre_t3`'s tests use; no test passes it
    here). Plan 27 Task 1: iteration 19's switches (`pre_t9`) off with them, so every seam onto an earlier rule reads
    them off."""
    for name in S.T8_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t9(sv)


def pre_t9(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 27 Task 1 (survival iteration 19): its switches off
    (`survive.T9_SWITCHES`), but those named in `keep` (the one-switch form `pre_t3`'s tests use; no test passes it
    here). Plan 27 Task 5: iteration 20's switches (`pre_t10`) off with them, so every seam onto an earlier rule reads
    them off."""
    for name in S.T9_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t10(sv)


def pre_t10(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 27 Task 5 (survival iteration 20): its switches off
    (`survive.T10_SWITCHES`), but those named in `keep` (the one-switch form `pre_t3`'s tests use). Plan 28 Task 3:
    iteration 21's switches (`pre_t11`) off with them, so every seam onto an earlier rule reads them off."""
    for name in S.T10_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t11(sv)


def pre_t11(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 28 Task 3 (survival iteration 21): its switches off
    (`survive.T11_SWITCHES`), but those named in `keep` (the one-switch form `pre_t3`'s tests use). Plan 28 Task 7b:
    iteration 22's switch (`pre_t12`) off with them, so every seam onto an earlier rule reads it off."""
    for name in S.T11_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t12(sv)


def pre_t12(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 28 Task 7b (survival iteration 22): its switch off
    (`survive.T12_SWITCHES`: MELEE, cut 1 of the maneuver layer), but those named in `keep`; every seam onto an
    earlier rule reads it off (`pre_t11`). Plan 29 Task 1: iteration 23's switches (`pre_t13`) off with it, so every
    seam onto an earlier rule reads them off."""
    for name in S.T12_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t13(sv)


def pre_t13(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 29 Task 1 (survival iteration 23): its switches off
    (`survive.T13_SWITCHES`: ROUTE_CROSS, ruling P29-A; GOAL_STALL, P29-B; Task 2's hit rules, HEALTH_NEAR, P29-E, and
    DRESS_FINISH, P29-D; MANY_NEAR, P29-G; FINISH_LONE, P29-F; CLOSE_IDLE, P29-C; FLEE_HELD_STANCE, P29-H'), but those
    named in `keep`; every seam onto an earlier rule reads them off (`pre_t12`). Plan 30 Task 3: iteration 24's switches
    (`pre_t14`) off with them, so every seam onto an earlier rule reads them off."""
    for name in S.T13_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t14(sv)


def pre_t14(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 30 Task 3 (survival iteration 24): its switches off
    (`survive.T14_SWITCHES`: SWING_CLOSE, ruling P30-A; GOAL_CONTINUE, P30-B; DOOR_HELD, P30-C; SNEAK, P30-D; STILL,
    P30-E; DRESS_RIDE, P30-F), but those named in `keep`; every seam onto an earlier rule reads them off
    (`pre_t13`). Plan 32 Task 5: the coward rules' switches (`pre_t16`) off with them, so every seam onto an earlier
    rule reads them off. (Plan 31 Task 15a's `T15_SWITCHES` and the Dress default move no golden,
    `test_survive_ah.test_this_task_moves_no_golden`, so they have no seam here.)"""
    for name in S.T14_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t16(sv)


def pre_t16(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 32 Task 5 (the coward rules): its switches off
    (`survive.T16_SWITCHES`: POINT_BLANK_FIGHT, (a); PAIR_NEAREST, (b); CARE_COMMIT, (c); STRAIN_BOUND, (d)), but those
    named in `keep`; every seam onto an earlier rule reads them off (`pre_t14`). Plan 33 Task 3: the group rules'
    switches (`pre_t17`) off with them, so every seam onto an earlier rule reads them off."""
    for name in S.T16_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)
    pre_t17(sv)


def pre_t17(sv, keep=()):
    """The replay's mutate seam onto the rules before Plan 33 Task 3 (the group's entry and the drag guard): its
    switches off (`survive.T18_SWITCHES`: GROUP_LEAVE, DRAG_GUARD_FIGHT, SIDE_CLEAR), but those named in `keep`; every
    seam onto an earlier rule reads them off (`pre_t16`)."""
    for name in S.T18_SWITCHES:
        if name not in keep:
            setattr(sv, name, False)


# ---------------------------------------------------------------- the rules before P24-X (Plan 24 Task 18)
def pre_x(sv):
    """The replay's mutate seam onto the rules before ruling P24-X (`Survive.ENGAGE` off: no engage within
    ENGAGE_R, the flee's `held` rule and the refight margin as before, no seek): with it the six goldens of
    `24987f2a` are reproduced line for line (`test_with_engage_off_the_goldens_are_iteration_7_s`). The tests below
    that pin a line of an earlier ruling (P23-AJ to P24-N) read it there, since P24-X re-records every golden from
    its line 1 (the engage of a zombie at 7 tiles where the record looted) and every later line of those episodes is
    open loop. Not behind the switch: Task 18's WIDE_TURNS and STEP_PROBE (and fix 1's group-aware wide tier), which
    the PRE_X pins prove move no golden (Task 18 fix 1, the review's minor 13). Plan 24 Task 21: ruling P24-AD's
    switch (`Survive.IDLE`) is off with it, the idle zombie counted toward `many` as before; Task 27: rulings P24-AG
    and P24-AK's (`Survive.STRAIN`) too, no spent read; Task 32: iteration 11's switches (`pre_an`) too."""
    sv.ENGAGE = False
    sv.IDLE = False
    sv.STRAIN = False
    pre_an(sv)


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


def pre_ad(sv):
    """The replay's mutate seam onto the rules before ruling P24-AD (Plan 24 Task 21: `Survive.IDLE` off, every
    zombie counted toward `many`), P24-X kept: it reproduces the six goldens as they stood before Task 21's re-record
    byte for byte (Task 21's report). A test that pins a line of an earlier ruling which P24-AD moved downstream (open
    loop) reads it there. Task 27: `Survive.STRAIN` off with it (P24-AG and P24-AK moved E4 and F1 downstream);
    Task 32: iteration 11's switches (`pre_an`) too."""
    sv.IDLE = False
    sv.STRAIN = False
    pre_an(sv)


@functools.lru_cache(maxsize=6)
def _pre_ad_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_ad), sort_keys=True)


def pre_ad_gold(key):
    """{line: decision} of the replay with P24-AD off: the golden before Task 21's re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_ad_replayed(key)))}


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
    first at 537, the corner attack on 15921, a `stuck` corner now, still moved.) Read with P24-AD off (`pre_ad`):
    Task 21's re-record moved F1 from line 163, these lines downstream of it."""
    base = pre_ad_gold("f1")
    assert base[484]["why"]["yield"] == "many"
    assert base[537]["action"] == {"type": "attack", "args": {"targetId": 15921}}
    assert base[537]["why"]["corner_kind"] == "stuck"
    monkeypatch.setattr(T, "CORNERED_R", 1.0)   # Task 36: the threat branch's and the Fight's copies
    monkeypatch.setattr(F, "CORNERED_R", 1.0)
    moved = {d["line"]: d for d in R.run(run_dir("f1"), mutate=pre_ad)}
    diff = [k for k in sorted(set(base) | set(moved)) if base.get(k) != moved.get(k)]
    assert diff and diff[0] == 484 and "yield" not in moved[484]["why"] and 537 in diff


def test_without_the_trailing_read_rule_f1_moves_at_line_498(monkeypatch):
    """The act model's own falsifier: a60's `done` (written 2 ms before line 498's wall) taken at 498 sends the next
    steer a tick early, where the record still ran a60. Named change, Task 12 fix 1 (the review's minor 5): the
    binder reads a recorded sprint as the run the replay sends (`as_run`), so the flee legs bind to the record's aids
    again and the falsifier is read on the golden's own replay, as before Task 12 (which read it with FLEE_GAIT set
    back to the sprint). Named change, ruling P29-G (Plan 29 Task 2): its `many` count over the standing within
    DANGER_R moves F1 from line 484, so the falsifier is read with `MANY_NEAR` off (the rule before it). Named change,
    ruling P30-C (Plan 30 Task 3): its `leave` at the gate moves F1's decisions from line 468, so `DOOR_HELD` is off
    too. Named change, Plan 32 Task 5: the coward rules (`survive.T16_SWITCHES`) move F1 from line 519, so they are off
    too (`pre_t16`)."""
    def off(sv):
        sv.MANY_NEAR = False
        sv.DOOR_HELD = False
        pre_t16(sv)
    base = {d["line"]: d for d in R.run(run_dir("f1"), mutate=off)}
    monkeypatch.setattr(R._Acts, "ends_current", lambda self, got: False)
    moved = {d["line"]: d for d in R.run(run_dir("f1"), mutate=off)}
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
    monkeypatch.setattr(T, "MANY_LISTED_N", 10 ** 9)
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
    monkeypatch.setattr(F, "REPOSITION_MIN", 0.0)
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
    monkeypatch.setattr(T, "MANY_LISTED_N", 10 ** 9)
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
    monkeypatch.setattr(T, "CLOSING_TICKS", 4)
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
    Fix 1 (1) leaves that corner at 236 for its leg on the golden, so the line is read with it off. Named change,
    Plan 32 Task 5: read with the coward rules off (`pre_t16`; (a) moves E5 from line 222)."""
    no_group_retry(monkeypatch)
    g = {d["line"]: d for d in R.run(run_dir("e5"), mutate=pre_t16)}
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
    Fix 1 (2): 0.03 nearer, under REPIN_MARGIN, it holds as well. Read with fix 1 (1) off (`no_group_retry`). Named
    change, Plan 32 Task 5: read with the coward rules off (`pre_t16`; (a) moves E5 from line 222, (b) from 233)."""
    no_group_retry(monkeypatch)
    point_blank_walk(monkeypatch)
    held = {d["line"]: d for d in R.run(run_dir("e5"), mutate=pre_t16)}
    assert held[241]["action"]["type"] == "walkTo" and held[242]["why"]["target"] == 19249
    repin_any(monkeypatch)
    moved = {d["line"]: d for d in R.run(run_dir("e5"), mutate=pre_t16)}
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
        monkeypatch.setattr(T, "MANY_LISTED_N", 10 ** 9)
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
    the stuck read of 537 1.52 s old, the `stuck` corner sends its retry leg, as the record steered there. Named change,
    ruling P30-C (Plan 30 Task 3): its `leave` at the gate moves F1 from line 468, so the line is read with iteration
    24 off (`pre_t14_gold`)."""
    g = pre_t14_gold("f1")
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
    "health"). Open loop: the record's frames do not move with those legs. Read with P24-AD off (`pre_ad`, Task 21)."""
    g = pre_ad_gold("f1")
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
    Named change, Plan 31 Task 15a: the chaser met in the stance; pinned with `CHASER_STANCE` off."""
    monkeypatch.setattr("agent.base.planner.threat.Threat.CHASER_STANCE", False)
    monkeypatch.setattr(S.Survive, "_stance_ok", lambda self, held, inside: False)
    got = {d["line"]: d for d in pre_run(SIXTH)}
    assert got == pre_gold("f1") and pre_moved_from_sixth(list(got.values()))[0] == 106


def test_the_replay_ends_an_unbound_aim_at_its_seconds(monkeypatch):
    """THE ACTS (Task 10 fix 1): an unbound `aim` ends `done` at its `seconds`, as a steer does. Named change (Task
    12, ruling P24-N): on the sixth golden the leg held open no longer moves anything, since a standing leg gives way
    the tick its target comes inside KEEP_R (111, 2.46 tiles, 2.53 s after 106's leg) and the backpedal it sends
    there is the leg the ended one re-aimed; `end_legs` itself is pinned here on its own.
    Named change, ruling P24-X (Plan 24 Task 18): read on the replay with P24-X off (`pre_x`), the rules it pins
    being earlier; P24-X re-recorded the golden from its line 1. Named change, Plan 28 Task 7b: `melee` joins
    LEG_TYPES after the two (`test_an_unbound_melee_ends_done_at_its_seconds`).
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
    assert (leg.state, leg.ended_wall, walk.state) == ("done", 102.0, "sent") and R.LEG_TYPES[:2] == ("steer", "aim")
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
        for mod in (P, F):   # Task 36: the Fight's copy (`planner/fight.py`) beside the policies' own
            monkeypatch.setattr(mod, name, val)
        moved = pre_moved_from_sixth(pre_run(SIXTH))
        assert (moved[0] if moved else None) == first, (name, val)
        for mod in (P, F):
            monkeypatch.setattr(mod, name, old)
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


# Plan 24 Task 21: the six goldens as they stood before P24-AD's re-record (base 14f9c6a8), their sha256
PRE_AD = {"e2": "f52a02afdff62493dc9e0a537504005660bfd30c99cab0d694e42daf89aebbc6",
          "e3": "c84f227a6d1d4535324da3ad99fd1dfaaa78e5bd86cfaacd3d3deb90e3214ee4",
          "e4": "74e0c3137d408b95591145e4784e399064b487fb21bede4c36e80f6326b8d0c9",
          "e5": "ad7eb5a78de21c86b2c99e2205a528edecb67114eb1ca775b9d2f0292ecd7f29",
          "f1": "ab1a30cb814d55bdeb113245f3b237434bc25ed1fabc4164845af395f5e943b0",
          SIXTH: "c7264689202e5ce4b9b7d683622e296762f6dfc138e411654ba263c62d474e76"}


@pytest.mark.parametrize("key", sorted(PRE_AD))
def test_with_idle_off_the_goldens_are_iteration_8_s(key):
    """P24-AD is one switch (`Survive.IDLE`): with it off every golden is the file Task 21 re-recorded byte for byte
    (its sha256 pinned), so every line P24-AD moved is P24-AD's (refactor A, P24-AB and P24-AC moved none). Named
    change, P28-F's planner side (Plan 28 Task 3 fix 1, R2, no switch): the sixth's case runs on R2_FROZEN's archive."""
    if key == SIXTH:
        return r2_frozen("test_with_idle_off_the_goldens_are_iteration_8_s[f1-caps15]")
    text = R.golden_text(R.decisions(json.loads(_pre_ad_replayed(key))), "14f9c6a8", R.RUNS[key], "2026-10-29",
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PRE_AD[key]


# the first line P24-AD moves on each golden: the tick its `many` read first differs, the old read's count
FIRST_IDLE = {"e2": 146, "e3": 214, "e4": 381, "e5": 215, "f1": 163, SIXTH: 163}


@pytest.mark.parametrize("key", sorted(FIRST_IDLE))
def test_p24_ad_moves_each_golden_first_at_its_line(key):
    """Task 21's attribution: each golden moves first at FIRST_IDLE's line against the rules before P24-AD. Named
    change, Task 36: read against the goldens before Task 36 (`pre_t36_gold`), P24-AX's `doorway_pick` moving E3 at
    204, before its line 214 here."""
    base, got = pre_ad_gold(key), pre_t36_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    assert diff and diff[0] == FIRST_IDLE[key]


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
    g, pre = pre_t6_gold(key), pre_gold(key)   # named change, Task 14 (P25-X): the goldens before its re-record
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
    g = pre_t6_gold(SIXTH)   # named change, Task 14 (P25-X): the goldens before its re-record
    assert g[102]["action"]["type"] == "walkTo" and g[102]["why"]["seek"] is True
    held = [k for k in range(103, 111) if g[k]["why"].get("holding") == "a12"]
    assert held == list(range(103, 111))
    assert g[111]["why"]["leg"] == "back" and g[111]["why"]["dist"] <= P.KEEP_R
    monkeypatch.setattr(P.Fight, "_walk_gives_way", lambda self: False)
    moved = {d["line"]: d for d in R.run(run_dir(SIXTH), caps=R.HELLO_CAPS[SIXTH], mutate=pre_t6)}
    diff = [k for k in sorted(set(g) | set(moved)) if g.get(k) != moved.get(k)]
    assert diff[0] == 111 and moved[111]["why"]["holding"] == "a12"


# ================================================================ Plan 24 Task 27: P24-AG to P24-AL on the goldens
def pre_ag(sv):
    """The replay's mutate seam onto the rules before rulings P24-AG and P24-AK (Plan 24 Task 27: `Survive.STRAIN` off,
    no spent read), every other rule kept: it reproduces the six goldens as they stood before Task 27's re-record byte
    for byte (`test_with_strain_off_the_goldens_are_iteration_9_s`), so P24-AH, P24-AI, P24-AJ and P24-AL, always on,
    move no golden: the records announce no `shove`, `stomp` or `unwear` and carry no `armPain`, `strain`,
    `loadedWidth` or `onFloor` (`test_no_record_carries_a_pza1_7_read`), and the goals answer from the record.
    Task 32: iteration 11's switches (`pre_an`) off with it."""
    sv.STRAIN = False
    pre_an(sv)


@functools.lru_cache(maxsize=6)
def _pre_ag_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_ag), sort_keys=True)


def pre_ag_gold(key):
    """{line: decision} of the replay with P24-AG off: the golden before Task 27's re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_ag_replayed(key)))}


# the six goldens as they stood before Task 27's re-record (base 9abc5037, recorded 2026-10-29), their sha256
PRE_AG = {"e2": "ce339594d3cc5a0715468423bd5a2c60ab2421a7a52dd99342c390127e0c7d06",
          "e3": "51822032e67a4c7c76cc5ddbd0e426357c13596d70db4b904f57980988de9eaf",
          "e4": "2279b91ab3bd32c884287eec20166209a46f60a9dc92638211c19faa53be9045",
          "e5": "ce0bc741b43c2b87a2f92edd80e2710cea0cb5d3ac42bbd5322ba5a1d9f28f53",
          "f1": "556dd17687bc90f87e2673ec45b36d5d7066eb93434b1226285bcd0aecd1e817",
          SIXTH: "acd162ed7043871a31d2dd20f6ac6791c3f5e731efecbbfdc3a9451d5a9d4dc9"}


@pytest.mark.parametrize("key", sorted(PRE_AG))
def test_with_strain_off_the_goldens_are_iteration_9_s(key):
    """P24-AG and P24-AK are one switch (`Survive.STRAIN`): with it off every golden is the file as it stood before
    Task 27 byte for byte (its sha256 pinned), so every line Task 27 moved is theirs, and the shove, the stomp, the
    finish of the fallen, the loaded-window legs and the unwear (always on) moved none. Named change, P28-F's
    planner side (Plan 28 Task 3 fix 1, R2, no switch): the sixth's case runs on R2_FROZEN's archive."""
    if key == SIXTH:
        return r2_frozen("test_with_strain_off_the_goldens_are_iteration_9_s[f1-caps15]")
    text = R.golden_text(R.decisions(json.loads(_pre_ag_replayed(key))), "9abc5037", R.RUNS[key], "2026-10-29",
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PRE_AG[key]


# the first line P24-AG moves on each golden it moves (the ENDURANCE moodle's first level read off the record's
# frames: no record carries armPain, and none reads fatigue near TIRED_FIGHT_T); E2, E3 and E5 never read
# endurance at or under ENDURANCE_T (their least 0.919, 0.965, 0.949) nor fatigue 0.6, so they do not move
# Task 27 fix 1 (the endurance hold released above ENDURANCE_RELEASE) moves F1 and the sixth from 604 to 555: the
# replay's fight walk at 555-556 (the old fight, endurance 0.754 after the 0.747 of gm 635) leaves the decision list
# (the spent character seeks no fight; the goal answers), and the first decision that differs is 557, the held flee
# `strain` at endurance 0.753, over ENDURANCE_T and under ENDURANCE_RELEASE
FIRST_STRAIN = {"e4": 427, "f1": 555, SIXTH: 555}
FIRST_HELD = {"f1": 557, SIXTH: 557}


@pytest.mark.parametrize("key", sorted(PRE_AG))
def test_p24_ag_moves_e4_and_f1_first_at_the_endurance_moodle_and_no_other_golden(key):
    """Task 27's attribution: E4 moves first at line 427 (game minute 619: the held flee's reason reads `strain`, the
    endurance 0.708), F1 and the sixth (fix 1's release line) at line 555 (game minute 636: the fight walk leaves the
    list, and 557 is the held flee `strain` at endurance 0.753, which the edge alone had let turn back to fight;
    before fix 1 they moved first at 604, game minute 642, the `walk` corner on 15917 yielding `strain` at 0.737);
    every later moved line is that episode's, open loop
    (E4's character died at 627 in the record, so its replay's tail flees `unarmed` once its inventory is gone).
    Named change, Plan 24 Task 32: read against the golden as it stood before Task 32 (`pre_an_gold`), iteration 11
    having moved E4 from line 431 and the sixth from line 164 (`test_iteration_11_moves_...`)."""
    base, got = pre_ag_gold(key), pre_an_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_STRAIN:
        assert diff == []
        assert PRE_T36[key][0] == PRE_AG[key]   # named change, Task 36: the file before Task 36's re-record
        return
    line = FIRST_STRAIN[key]
    assert diff[0] == line
    first = FIRST_HELD.get(key, line)
    assert line in got or key in FIRST_HELD
    assert min(k for k in diff if k in got) == first
    w = got[first]["why"]
    assert w["strain"]["kind"] == "endurance" and w["strain"]["endurance"] <= P.ENDURANCE_RELEASE
    assert (w["strain"]["endurance"] > P.ENDURANCE_T) is (key in FIRST_HELD)
    assert w["strain"]["armPain"] is None and w["strain"]["fatigue"] < P.TIRED_FIGHT_T
    assert w.get("flee") == "strain" or w.get("yield") == "strain"


@pytest.mark.parametrize("key", sorted(R.RUNS))
def test_no_record_carries_a_pza1_7_read(key):
    """The goldens' records predate PZA/1.7: no hello announces `shove`, `stomp` or `unwear`, and no frame carries
    `body.armPain`, `body.strain`, `me.loadedWidth` or a zombie's `onFloor` (decoded None), so P24-AG's Fight half,
    P24-AH, P24-AI, P24-AJ and P24-AL read nothing there."""
    lines, _ = R.read_record(run_dir(key))
    hellos = [ln for ln in lines if ln.get("kind") == "hello"]
    frames = [ln for ln in lines if ln.get("kind") == "frame"]
    assert hellos and frames
    assert not any(c in (h.get("caps") or ()) for h in hellos for c in ("shove", "stomp", "unwear"))
    assert not any(c in (R.HELLO_CAPS.get(key) or ()) for c in ("shove", "stomp", "unwear"))
    for fr in frames:
        assert (fr.get("body") or {}).get("armPain") is None and (fr.get("body") or {}).get("strain") is None
        assert (fr.get("me") or {}).get("loadedWidth") is None
        assert not any(zz.get("onFloor") is not None for zz in fr.get("zombies") or ())


# ================================================================ Plan 24 Task 32: iteration 11 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_an_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_an), sort_keys=True)


def pre_an_gold(key):
    """{line: decision} of the replay with iteration 11's switches off: the golden before Task 32's re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_an_replayed(key)))}


def _one_off(name, fix1=True):
    def m(sv):
        if fix1:
            fix1_off(sv)
        pre_t36(sv)   # Task 36: iteration 12's switches off in every seam onto an earlier rule
        setattr(sv, name, False)
    return m


@functools.lru_cache(maxsize=8)
def _one_off_gold(key, name, fix1=True):
    """{line: decision} of the replay with the one switch `name` off, the other rules of HEAD on (with `fix1`, Task
    32 fix 1's switches off too: the rules as Task 32 landed them)."""
    return {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                         mutate=_one_off(name, fix1)))}


@functools.lru_cache(maxsize=6)
def _t32_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=fix1_off), sort_keys=True)


def t32_gold(key):
    """{line: decision} of the replay with Task 32 fix 1's switches off: the golden as Task 32 recorded it."""
    return {d["line"]: d for d in R.decisions(json.loads(_t32_replayed(key)))}


# the six goldens as they stood before Task 32's re-record: sha256, base, recorded
PRE_AN = {"e2": ("ce339594d3cc5a0715468423bd5a2c60ab2421a7a52dd99342c390127e0c7d06", "9abc5037", "2026-10-29"),
          "e3": ("51822032e67a4c7c76cc5ddbd0e426357c13596d70db4b904f57980988de9eaf", "9abc5037", "2026-10-29"),
          "e4": ("002ac8ca98385c05d792f0ce0cee9eb383d78d2d8e73f758c27399a1171875b8", "eff3bdce", "2026-10-30"),
          "e5": ("ce0bc741b43c2b87a2f92edd80e2710cea0cb5d3ac42bbd5322ba5a1d9f28f53", "9abc5037", "2026-10-29"),
          "f1": ("58540fb15d575cbbccb3fd41c9cd4389dd411180d532f4fb4c83d96f7ad74e01", "eff3bdce", "2026-10-30"),
          SIXTH: ("9cec6a97101e7e44ff26ea03b42d472e9c78ac1dcff097df7a735604fbe96cb1", "eff3bdce", "2026-10-30")}


@pytest.mark.parametrize("key", sorted(PRE_AN))
def test_with_iteration_11_off_the_goldens_are_task_27_s(key):
    """Iteration 11's golden movers are three switches (`Survive.PULL`, `DOORWAY`, `TRANS`): with them off every golden
    is the file as it stood before Task 32 byte for byte (its sha256 pinned), so P24-AN's listing count, P24-AP,
    P24-AQ and P24-AR (always on) move none. Named change, P28-F's planner side (Plan 28 Task 3 fix 1, R2, no
    switch): the sixth's case runs on R2_FROZEN's archive."""
    if key == SIXTH:
        return r2_frozen("test_with_iteration_11_off_the_goldens_are_task_27_s[f1-caps15]")
    sha, base, recorded = PRE_AN[key]
    text = R.golden_text(R.decisions(json.loads(_pre_an_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


# the first line iteration 11 moves on each golden it moves, and the one switch that moves it
FIRST_AN = {"e4": (431, "TRANS"), SIXTH: (164, "PULL")}


@pytest.mark.parametrize("key", sorted(PRE_AN))
def test_iteration_11_moves_e4_at_the_transparent_solid_and_the_sixth_at_the_pull_and_no_other_golden(key):
    """Task 32's attribution. E4 moves first at line 431 (game minute 620, the `strain` flee's re-aim: the heading
    turned 60 degrees, (-0.99967, 0.02567), crosses a `solidTrans` square within its STEER_PROBE line, so P24-AS turns
    it 150, (-0.02567, -0.99967), its AHEAD_R probe clear); every later line is that episode's, open loop to the
    log's end. The sixth (F1 with the PZA/1.5 caps) moves first at line 164 (game minute 584: 15911 chases alone at
    8.93 tiles, the rest of the listing beyond DANGER_R: the pull's leg away from their centroid where the seek's leg
    went toward it), and at 165 the pulled chaser past ENGAGE_R (9.34) is stood for, never sought back. P24-AO moves
    no golden: the five PZA/1.4 builds announce no stance, and the sixth's four shelter plans are picked under
    `unreachable`, `pair` and `strain` flees, never a `many` one. Each golden's own switch alone off reproduces the
    file before Task 32: the other two move nothing on it. Named change, Task 32 fix 1: read against the goldens as
    Task 32 recorded them (`t32_gold`, fix 1's switches off; `test_fix_1_moves_...` attributes fix 1's moves)."""
    base, got = pre_an_gold(key), t32_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_AN:
        assert diff == []
        assert PRE_FIX1[key][0] == PRE_AN[key][0]
        return
    line, switch = FIRST_AN[key]
    assert diff[0] == line
    assert _one_off_gold(key, switch) == base
    if key == "e4":
        b, g = base[line], got[line]
        assert b["why"]["turn"] == 60 and b["why"]["probe"] == 3.0 and g["why"]["turn"] == 150
        assert g["why"]["probe"] == 9.0 and g["action"]["type"] == b["action"]["type"] == "steer"
    else:
        b, g = base[line]["why"], got[line]["why"]
        assert b["leg"] == "seek" and g["leg"] == "pull" and b["target"] == g["target"] == 15911
        assert g["dist"] == b["dist"] and 8.9 < g["dist"] <= P.ENGAGE_R and len(g["pull"]) == 2
        assert got[line + 1]["why"]["leg"] == "stand" and got[line + 1]["why"]["dist"] > P.ENGAGE_R


@pytest.mark.parametrize("key", sorted(R.RUNS))
def test_no_record_carries_what_iteration_11_reads(key):
    """The goldens' records: every listed zombie reads its `hasTarget` (so P24-AN's listing count reads as P24-AD's
    did: none counts as unread), and no part record carries `bleeding` (PZA/1.5), so P24-AR's ride never reads a
    wound there; with `test_no_record_carries_a_pza1_7_read` (no `armPain`, no `onFloor`, no `stomp` announced),
    P24-AP and P24-AQ read nothing either."""
    lines, _ = R.read_record(run_dir(key))
    frames = [ln for ln in lines if ln.get("kind") == "frame"]
    assert frames
    for fr in frames:
        assert all(zz.get("hasTarget") is not None for zz in fr.get("zombies") or ())
        assert all(p.get("bleeding") is None for p in ((fr.get("body") or {}).get("parts") or ()) if isinstance(p, dict))


# ================================================================ Plan 24 Task 32 fix 1 on the goldens
# the six goldens as Task 32 recorded them (`45e099ea`): sha256, base, recorded
PRE_FIX1 = {"e2": ("ce339594d3cc5a0715468423bd5a2c60ab2421a7a52dd99342c390127e0c7d06", "9abc5037", "2026-10-29"),
            "e3": ("51822032e67a4c7c76cc5ddbd0e426357c13596d70db4b904f57980988de9eaf", "9abc5037", "2026-10-29"),
            "e4": ("dd93ec28b348a9238be69f2ed3e711d22aabfbdac486d2938d7218b528a572c9", "434543ac", "2026-10-30"),
            "e5": ("ce0bc741b43c2b87a2f92edd80e2710cea0cb5d3ac42bbd5322ba5a1d9f28f53", "9abc5037", "2026-10-29"),
            "f1": ("58540fb15d575cbbccb3fd41c9cd4389dd411180d532f4fb4c83d96f7ad74e01", "eff3bdce", "2026-10-30"),
            SIXTH: ("cebf068324c1ddaa30acfbbe0f996f7d9c906b92665f1ff03ec133d28044a30d", "434543ac", "2026-10-30")}


@pytest.mark.parametrize("key", sorted(PRE_FIX1))
def test_with_fix_1_off_the_goldens_are_task_32_s(key):
    """Task 32 fix 1's golden movers are two switches (`Survive.HOLD_WIDE`, `STANCE_LISTED`): with them off every
    golden is the file as Task 32 recorded it byte for byte (its sha256 pinned), so the fix's other rules (always on)
    move none."""
    sha, base, recorded = PRE_FIX1[key]
    text = R.golden_text(R.decisions(json.loads(_t32_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


# the first line fix 1 moves on each golden it moves, and the one switch that moves it
FIRST_FIX1 = {"f1": (559, "HOLD_WIDE"), SIXTH: (559, "HOLD_WIDE")}


@pytest.mark.parametrize("key", sorted(PRE_FIX1))
def test_fix_1_moves_f1_and_the_sixth_at_r2_and_no_other_golden(key):
    """Task 32 fix 1's attribution. F1 and the sixth move first at line 559 (game minute 636): the `walk` corner on
    15921 at 1.09 tiles under the endurance hold (0.752, under ENDURANCE_RELEASE) yielded `strain` (the flee's walk
    held, then `pair`); under ruling R2 a hold fights a zombie within KEEP_R, so the corner swings (the records announce
    no `shove`, so the swing stays: `Survive._fight_spent`); every later moved line is that episode's, open loop.
    STANCE_LISTED (the review's major 6) moves no golden: on the sixth, the one golden whose build stands, no fight's
    held list carried an idle zombie beyond DANGER_R into the stance's count past MAX_FIGHT; the E9 replay is its
    reading (`test_survive_o`). E2, E3, E4 and E5 are unmoved: E4's endurance hold met its zombies within KEEP_R only
    in corners, which swung before. HOLD_WIDE alone off reproduces Task 32's file; STANCE_LISTED alone off moves
    nothing."""
    base, got = t32_gold(key), pre_t36_gold(key)   # named change, Task 36: the goldens as fix 1 recorded them
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    assert _one_off_gold(key, "STANCE_LISTED", False) == got
    if key not in FIRST_FIX1:
        assert diff == []
        assert PRE_T36[key][0] == PRE_FIX1[key][0]
        return
    line, switch = FIRST_FIX1[key]
    assert diff[0] == line
    assert _one_off_gold(key, switch, False) == base
    b, g = base[line], got[line]
    assert b["why"]["yield"] == "strain" and b["why"]["strain"]["kind"] == "endurance"
    assert P.ENDURANCE_T < b["why"]["strain"]["endurance"] <= P.ENDURANCE_RELEASE
    assert g["why"]["corner_kind"] == "walk" and g["why"]["cornered"] == 15921 and g["why"]["dist"] <= P.KEEP_R
    assert g["action"] == {"type": "attack", "args": {"targetId": 15921}}


# ================================================================ Plan 24 Task 36: iteration 12 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t36_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t36), sort_keys=True)


def pre_t36_gold(key):
    """{line: decision} of the replay with iteration 12's switches off: the golden before Task 36's re-records."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t36_replayed(key)))}


@functools.lru_cache(maxsize=12)
def _only_t36(key, switch):
    """{line: decision} of the replay with iteration 12's switches off but `switch`."""
    return {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                         mutate=lambda sv: pre_t36(sv, keep=(switch,))))}


# the six goldens as they stood before Task 36 (Task 32 fix 2's HEAD, `6f13037c`): sha256, base, recorded
PRE_T36 = {"e2": ("ce339594d3cc5a0715468423bd5a2c60ab2421a7a52dd99342c390127e0c7d06", "9abc5037", "2026-10-29"),
           "e3": ("51822032e67a4c7c76cc5ddbd0e426357c13596d70db4b904f57980988de9eaf", "9abc5037", "2026-10-29"),
           "e4": ("dd93ec28b348a9238be69f2ed3e711d22aabfbdac486d2938d7218b528a572c9", "434543ac", "2026-10-30"),
           "e5": ("ce0bc741b43c2b87a2f92edd80e2710cea0cb5d3ac42bbd5322ba5a1d9f28f53", "9abc5037", "2026-10-29"),
           "f1": ("be1666e039724549a5fddf9c920dae65910388c0e836457479c8dd1916dacb06", "7eac71ab", "2026-10-30"),
           SIXTH: ("d93a2b607209fd416aa859c43d4fd665f3e16463535a60682e8f8c171565ec5a", "7eac71ab", "2026-10-30")}


@pytest.mark.parametrize("key", sorted(PRE_T36))
def test_with_iteration_12_off_the_goldens_are_task_32_fix_2_s(key):
    """Iteration 12's golden movers are `T36_SWITCHES`: with them off every golden is the file as it stood before Task
    36 byte for byte (its sha256 pinned), so the pure move (`5bfbfff7`) and the rules without a switch move none."""
    sha, base, recorded = PRE_T36[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t36_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


# the first line each iteration-12 switch moves, alone on, on each golden it moves
FIRST_T36 = {"e2": {"PICK_WHY": 147}, "e3": {"PICK_WHY": 204}, "e4": {"PICK_WHY": 388}, "e5": {"PICK_WHY": 224},
             "f1": {"PICK_WHY": 484}, SIXTH: {"EDGE": 361, "PICK_WHY": 484}}


@pytest.mark.parametrize("key", sorted(PRE_T36))
def test_iteration_12_moves_each_golden_first_at_its_switch_s_line(key):
    """Task 36's attribution, each switch alone on against the goldens before Task 36 (`pre_t36_gold`):
    - EDGE (P24-AU) moves the sixth alone, at line 361 (game minute 610) and no other: the pull on 15885 (sent at
      358, 7.93 tiles, the group's centroid (10734.5, 10624.66)) reads the chaser at 4.30 tiles, within PULL_R; the
      group had left the listing, so before the edge hold the pull's end read no group and the seek leg went toward
      the chaser (`seek`), where now the group is held at its last listed squares and the pull's end stands
      (`stand`); from 362 the lines are the old ones (the backpedal at 2.05 tiles).
    - PICK_WHY (P24-AX) moves every golden at its first `many` line (E2 147, E3 204, E4 388, E5 224, F1 and the sixth
      484), and moves no decision: every line it moves differs by the why's `doorway_pick` alone, `no_stance` on the
      five PZA/1.4 builds (no `aim` announced), on the sixth `taken`, `picked`, `no_door`, `pending` or `standing`.
    A golden no switch moves is the file before Task 36 byte for byte."""
    base, got = pre_t36_gold(key), pre_t6_gold(key)   # named change, Task 14 (P25-X): the goldens before its re-record
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T36:
        assert diff == []
        assert pre_t6_sha(key) == PRE_T36[key][0]
        return
    assert diff[0] == min(FIRST_T36[key].values())
    for switch in T36_SWITCHES:
        alone = _only_t36(key, switch)
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T36[key].get(switch), switch
    alone = _only_t36(key, "PICK_WHY")
    for k in [k for k in sorted(alone) if alone[k] != base.get(k)]:
        a, w = dict(alone[k], why=dict(alone[k]["why"])), alone[k]["why"]["doorway_pick"]
        del a["why"]["doorway_pick"]
        assert a == base[k] and alone[k]["why"]["flee"] == "many", k
        assert w == "no_stance" if key != SIXTH else w in ("taken", "picked", "no_door", "pending", "standing"), k
    if key == SIXTH:
        b, g = base[361]["why"], got[361]["why"]
        assert b["leg"] == "seek" and g["leg"] == "stand" and b["target"] == g["target"] == 15885
        assert P.KEEP_R < g["dist"] <= P.PULL_R and got[361]["action"]["args"]["vx"] == 0.0
        assert base[358]["why"]["leg"] == "pull" and got[362] == base[362] and got[362]["why"]["leg"] == "back"


# ================================================================ Plan 25 Task 2: the observes read in `_read`
def pre_t2(sv):
    """The replay's mutate seam onto the rules before Plan 25 Task 2: `Survive.OBSERVES_IN_READ` off (every observe
    inside `assess`, as Plan 24 left them)."""
    sv.OBSERVES_IN_READ = False


@pytest.mark.parametrize("key", sorted(PRE_T36))
def test_observes_in_read_moves_no_golden(key):
    """Task 2 moved every held policy's observe into `_read` (`OBSERVES_IN_READ`): the six goldens stay byte-identical
    with it on (`test_the_golden_is_reproduced_byte_for_byte_from_its_artifact`) and with it off, so no golden line
    reads the observes' order (no record carries a care action's end or a night step on a threat tick the order moves)."""
    with open(R.golden_path(key), encoding="utf-8") as f:
        head = json.load(f)
    text = R.golden_text(R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t2)), head["base"],
                         R.RUNS[key], head["recorded"], R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert text.encode("utf-8") == golden(key)


# ================================================================ Plan 25 Task 3: iteration 13 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t3_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t3), sort_keys=True)


def pre_t3_gold(key):
    """{line: decision} of the replay with iteration 13's switches off: the golden before Task 3's re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t3_replayed(key)))}


@functools.lru_cache(maxsize=12)
def _only_t3(key, switch):
    """{line: decision} of the replay with iteration 13's switches off but `switch`."""
    return {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                         mutate=lambda sv: pre_t3(sv, keep=(switch,))))}


# the six goldens as they stood before Task 3 (Task 2's HEAD, `843c4ec3`): sha256, base, recorded
PRE_T3 = {"e2": ("f2edee8655bb6c6706ce8b2af99daff97445d4a1673ed2799e912fdf0e266cb9", "eaa1c9a3", "2026-10-30"),
          "e3": ("2585ba89039b0306ee93e814909507afdaccb038936d9dece1171511ec6d5bac", "eaa1c9a3", "2026-10-30"),
          "e4": ("26155f3807a88aa064fd01df557cfa1e9c59ff73d124f8037bd3c82eed258cf8", "eaa1c9a3", "2026-10-30"),
          "e5": ("cba5e2bff3226198dffae52078a1b38269101a6e786cc0199d204adefa0900cf", "eaa1c9a3", "2026-10-30"),
          "f1": ("599990a3e11d14315e0b9d076bbfa10a49341c503aff4831709fac4d9f7d43d5", "eaa1c9a3", "2026-10-30"),
          SIXTH: ("200e3621f8de68832d3eb9ba143bb165339b58d22cbacdf54e283b5f47633562", "eaa1c9a3", "2026-10-30")}


@pytest.mark.parametrize("key", sorted(PRE_T3))
def test_with_iteration_13_off_the_goldens_are_task_2_s(key):
    """Iteration 13's golden movers are `survive.T3_SWITCHES`: with them off every golden is the file as it stood
    before Task 3 byte for byte (its sha256 pinned), so the rules without a switch (the goal view's `spent`, the
    imports, `World.fence_crossing` under `fence_on_line`, the Fight's `_standing`) move none."""
    sha, base, recorded = PRE_T3[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t3_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


# the first line each iteration-13 switch moves, alone on, on each golden it moves
FIRST_T3 = {"e4": {"HOLD_RUN": 431}}


@pytest.mark.parametrize("key", sorted(PRE_T3))
def test_iteration_13_moves_e4_alone_at_the_endurance_hold_s_first_walk(key):
    """Task 3's attribution, each switch alone on against the goldens before Task 3 (`pre_t3_gold`):
    - HOLD_RUN (P25-C) moves E4 alone, at line 431 (game minute 620): its endurance hold (from line 427,
      `FIRST_STRAIN`) flees `strain` with no zombie within DANGER_R (the steer's own why reads the nearest 8.16 tiles
      off at its aim), and the leg the record ran (a49, `run`) goes at a walk, logged `hold_walk`; every later moved
      line is downstream of it (open loop: the unbound walk). F1 and the sixth carry the endurance hold too (from line
      555) and move nowhere: each reads two `strain` flee ticks, both with a zombie within DANGER_R (the run), over
      1.46 game minutes of the hold, far short of HOLD_SPAN_MIN.
    - CORNER_BREAK, FINISH_FIRST, RIDE_WAIT, DOOR_WALK and FENCE_WAIT move no golden: no record carries a shove's
      result or `onFloor` (PZA/1.7), no ride runs under a held Fight (F1's parts decode no bleeding), the sixth picks no
      doorway stand, and the fence wait needs the stance's `aim`, which only the sixth announces, where no chaser is
      read across a fence within AIM_R.
    A golden no switch moves is the file before Task 3 byte for byte."""
    base, got = pre_t3_gold(key), pre_t6_gold(key)   # named change, Task 14 (P25-X): the goldens before its re-record
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T3:
        assert diff == []
        assert pre_t6_sha(key) == PRE_T3[key][0]
        return
    assert diff[0] == min(FIRST_T3[key].values())
    for switch in S.T3_SWITCHES:
        alone = _only_t3(key, switch)
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T3[key].get(switch), switch
    b, g = base[431], got[431]
    assert b["action"]["type"] == g["action"]["type"] == "steer" and b["action"]["args"]["gait"] == "run"
    assert g["action"]["args"]["gait"] == "walk" and g["why"]["hold_walk"] is True and "hold_walk" not in b["why"]
    assert g["why"]["flee"] == "strain" and g["why"]["strain"]["kind"] == "endurance"
    assert dict(g["action"]["args"], gait="run") == b["action"]["args"]


# ================================================================ Plan 25 Task 7: iteration 14 on the goldens
@pytest.mark.parametrize("key", sorted(PRE_T3))
def test_iteration_14_moves_no_golden(key):
    """Task 7's rules move no golden: the six are byte-identical with them on (`test_the_golden_is_reproduced_byte_
    for_byte_from_its_artifact`) and with iteration 14's switch off (`pre_t4`): no ring reaches P25-H's unwear (the
    five PZA/1.4 builds decode no part `bleeding`; the sixth announces PZA/1.5's caps, no `unwear`), no golden's
    scripted Shelter or LootBuilding fails for a shun (P25-G's cooling), and no record carries a shove's result (P25-I's
    why: PZA/1.7). Plan 25 Task 8: the second half's rules move none either, on and off: P25-J's far finish and P25-L's
    break need the PZA/1.7 `stomp` and `shove`, which no golden's build announces; P25-K's wound end needs a doorway
    stand reading a part's `bleeding`; no golden's ring releases a hold (P25-M's `release`); P25-N's legs
    (SHELTER_LEGS) send no leg in any golden, on or off, so no golden's Shelter goal or night shelter approach meets a
    door beyond `leg_len` (`goal_policies.leg_max`); and no golden's hello reads "1.7", the two-number version P25-O
    reads (their hellos read 1.2 to 1.5.x). Task 8 fix 1's amended P25-J (3) (one finish rule, the knock window, the
    `pair` flee's own finish) moves none either: it needs the PZA/1.7 `stomp` and `onFloor`, as P25-J does."""
    _, base, recorded = PRE_T6[key]   # named change, Task 14 (P25-X): the goldens before its re-record
    text = R.golden_text(R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t4)), base,
                         R.RUNS[key], recorded, R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PRE_T6[key][0]


# ================================================================ Plan 25 Task 10: iteration 15 on the goldens
@pytest.mark.parametrize("key", sorted(PRE_T3))
def test_iteration_15_moves_no_golden(key):
    """Task 10's rules move no golden: the six are byte-identical with them on (`test_the_golden_is_reproduced_byte_
    for_byte_from_its_artifact`) and with iteration 15's switches off (`pre_t5`). P25-P's unarmed fight needs a build
    announcing the PZA/1.7 `shove`, which no golden's build does (their hellos read 1.2 to 1.5.x), so every unarmed
    golden tick flees `unarmed` as before; P25-S's low fight needs it too, so every golden tick under FLEE_HEALTH with
    one zombie flees `health` as before. P25-Q (`TRAPPED_CARE`) passes no golden's trapped hold to a care that sends:
    no golden ring decodes a part's `bleeding` (PZA/1.4), nor announces `unwear`."""
    _, base, recorded = PRE_T6[key]   # named change, Task 14 (P25-X): the goldens before its re-record
    text = R.golden_text(R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t5)), base,
                         R.RUNS[key], recorded, R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PRE_T6[key][0]


# ================================================================ Plan 25 Task 14: iteration 16 on the goldens
# the six goldens as they stood before Task 14's amendment re-recorded them (Task 13's HEAD, `bc2950f8`): sha256, base,
# recorded
PRE_T6 = {"e2": ("f2edee8655bb6c6706ce8b2af99daff97445d4a1673ed2799e912fdf0e266cb9", "eaa1c9a3", "2026-10-30"),
          "e3": ("2585ba89039b0306ee93e814909507afdaccb038936d9dece1171511ec6d5bac", "eaa1c9a3", "2026-10-30"),
          "e4": ("559e725e3ee48cb88b63cb97d2235d75da6f347479b7c053f4d9d88c7821b5d5", "b12039ba", "2026-10-30"),
          "e5": ("cba5e2bff3226198dffae52078a1b38269101a6e786cc0199d204adefa0900cf", "eaa1c9a3", "2026-10-30"),
          "f1": ("599990a3e11d14315e0b9d076bbfa10a49341c503aff4831709fac4d9f7d43d5", "eaa1c9a3", "2026-10-30"),
          SIXTH: ("200e3621f8de68832d3eb9ba143bb165339b58d22cbacdf54e283b5f47633562", "eaa1c9a3", "2026-10-30")}


@functools.lru_cache(maxsize=6)
def _pre_t6_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t6), sort_keys=True)


def pre_t6_gold(key):
    """{line: decision} of the replay with iteration 16's switches off: the golden before Task 14's re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t6_replayed(key)))}


def pre_t6_sha(key):
    """The sha256 of the golden file the replay with iteration 16's switches off writes, under the base and the date
    it stood at before Task 14's re-record (`PRE_T6`)."""
    _, base, recorded = PRE_T6[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t6_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("key", sorted(PRE_T6))
def test_with_iteration_16_off_the_goldens_are_task_13_s(key):
    """Iteration 16's golden mover is `BLOCKED_EDGE` (P25-X): with `survive.T6_SWITCHES` off (`pre_t6`) every golden
    is the file as it stood before Task 14's re-record byte for byte (its sha256 pinned). P25-U, P25-V and P25-W
    read a doorway stand that stood, and no golden's stand stands: their `doorway_pick` reads `no_stance`, `taken`,
    `picked`, `pending`, `no_door` and `standing`, never `ok` (five goldens read `no_stance` on every `many` line,
    their builds announcing no `aim`; `f1-caps15`, on PZA/1.5's caps, never picks a door free)."""
    assert pre_t6_sha(key) == PRE_T6[key][0]


# the first line P25-X moves on each golden (every one at its first engage, `FIRST_ENGAGE`): (line, target, edge)
FIRST_T6 = {"e2": (68, 12787, [10731, 10642, "N"]), "e3": (69, 14910, [10733, 10642, "N"]),
            "e4": (247, 19001, [10732, 10642, "N"]), "e5": (69, 19223, [10733, 10642, "N"]),
            "f1": (102, 15885, [10733, 10642, "N"]), SIXTH: (102, 15885, [10733, 10642, "N"])}


@pytest.mark.parametrize("key", sorted(PRE_T6))
def test_p25_x_moves_every_golden_first_at_its_first_engage_the_gate_zombie_refused(key):
    """Task 14's attribution: P25-X re-records all six, each first moved at its first engage (`FIRST_ENGAGE`), the
    fixture's fence row on y 10642 (E15's locked chain-link gate at (10756, 10642), the old locked gate at (10732,
    10642), #4273, #4282; its unlocked door record at (10747, 10642) beyond DISENGAGE_R of every crossing): before
    it the Fight walked at the chaser across the fence (E4's 19001 is the zombie the review of Plan 24 Task 18 named,
    sought every UNREACHABLE_S behind a locked gate); now its line crosses a known blocked edge with no unlocked door
    on its run within DISENGAGE_R, so the target is refused and marked (`blocked_edge` {action refuse, door None},
    `marked`), and every later moved line is downstream of it (open loop). Each other iteration-16 switch alone off
    moves nothing (`BLOCKED_EDGE` alone off is the file before)."""
    base, got = pre_t6_gold(key), gold(key)
    first = min(k for k in set(base) | set(got) if base.get(k) != got.get(k))
    line, zid, edge = FIRST_T6[key]
    assert first == line == FIRST_ENGAGE[key][0] and base[line]["why"]["target"] == zid
    assert base[line]["action"]["type"] == "walkTo" and got[line]["action"] is None
    w = got[line]["why"]
    assert w["blocked_edge"] == {"action": "refuse", "door": None, "edge": edge} and w["marked"] == zid
    only = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                         mutate=lambda sv: pre_t6(sv, keep=("STAND_DRAG_EARLY",
                                                                                            "STAND_INSIDE",
                                                                                            "STAND_EXIT"))))}
    assert only == base


# ---------------------------------------------------------------- Task 14 fix 1: P25-X's amendment and P25-Y
# the six goldens as they stood at `427c0b2d`'s re-record (base `bc2950f8`), before `EDGE_OUT_OF_HOLD` re-recorded them
PRE_EDGE_OUT = {"e2": ("f7f52aa9855f484aa40caf841a4656c14304b582c19df4e9ea4ba64d16db41ca", "bc2950f8", "2026-11-02"),
                "e3": ("798305a247dc992bc8edde0222b03bc6663213042bbb593f45db6610cbe6d611", "bc2950f8", "2026-11-02"),
                "e4": ("f63bc9225d9ff8d0e00fee9f25eb7bcad8a0a24daf6c089be04a4142d136a1e7", "bc2950f8", "2026-11-02"),
                "e5": ("e96579ba458b4c8265c37e8bf26cf1f8e182483b67ea2c64a5404c1b45e359f9", "bc2950f8", "2026-11-02"),
                "f1": ("addf870b774fd64b8f7b94dfde089eceeae58ace05b9a8e43a39b5d3d234cd46", "bc2950f8", "2026-11-02"),
                SIXTH: ("da59a6747702ee3ee1ef59e709c2e9055bea15983cc8fdd085f2379c9833860b", "bc2950f8", "2026-11-02")}
# the first line `EDGE_OUT_OF_HOLD` moves on each golden: the tick after the refusal at the first engage
# (`FIRST_ENGAGE`), where the file before fled `unreachable` from the refused zombie across the fence row
FIRST_EDGE_OUT = {"e2": 70, "e3": 85, "e4": 250, "e5": 75, "f1": 106, SIXTH: 106}


def pre_edge_out(sv):
    """`EDGE_OUT_OF_HOLD` off. Named change, Plan 27 Task 1 (ruling P27-B re-recorded E4): iteration 19's switches
    (`pre_t9`) off with it, so the seam reads the files of `427c0b2d`."""
    sv.EDGE_OUT_OF_HOLD = False
    pre_t9(sv)


@functools.lru_cache(maxsize=6)
def _pre_edge_out_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_edge_out), sort_keys=True)


def pre_edge_out_decisions(key):
    return R.decisions(json.loads(_pre_edge_out_replayed(key)))


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_edge_out_of_hold_off_the_goldens_are_the_p25_x_files(key):
    """`EDGE_OUT_OF_HOLD` (P25-X amended, Task 14 fix 1) is the only mover of the re-record: with it off every golden
    is the file of `427c0b2d` byte for byte (its sha256 pinned)."""
    _, base, recorded = PRE_EDGE_OUT[key]
    text = R.golden_text(pre_edge_out_decisions(key), base, R.RUNS[key], recorded, R.SPANS.get(key),
                         R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PRE_EDGE_OUT[key][0]


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_edge_out_of_hold_moves_every_golden_first_the_tick_after_its_first_refusal(key):
    """Task 14 fix 1's attribution: all six move, each first at `FIRST_EDGE_OUT`, the line after the first engage's
    refusal (`FIRST_ENGAGE`, P25-X): the file before fled `unreachable` from the refused zombie held across the fence
    row (the shelter approach walk of its building); now the zombie is out of the hold, the threat branch passes and
    the goal runs, so the line leaves the golden (which holds no goal line). Every later moved line is downstream of it
    (open loop)."""
    base, got = {d["line"]: d for d in pre_edge_out_decisions(key)}, gold(key)
    moved = sorted(k for k in set(base) | set(got) if base.get(k) != got.get(k))
    assert moved[0] == FIRST_EDGE_OUT[key] > FIRST_ENGAGE[key][0]
    line = FIRST_EDGE_OUT[key]
    assert base[line]["why"]["flee"] == "unreachable" and line not in got
    assert base[FIRST_ENGAGE[key][0]] == got[FIRST_ENGAGE[key][0]]


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_dirty_rag_rip_moves_no_golden(key):
    """P25-Y reads a bleeding part under a dirty rag with a garment held: no golden ring carries one, so the files
    are the same with `DIRTY_RAG_RIP` off."""
    only = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                       mutate=lambda sv: setattr(sv, "DIRTY_RAG_RIP", False)))}
    assert only == gold(key)


# ================================================================ Plan 26 Task 2: iteration 17 on the goldens
@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_17_moves_no_golden(key):
    """Survival iteration 17 (P26-A to P26-E) moves no golden: the six are byte-identical with its switches on
    (`test_the_golden_is_reproduced_byte_for_byte_from_its_artifact`) and off (`pre_t7`). P26-A's window way out needs
    a build announcing `window`, and P26-C's crowd one announcing `shove` (PZA/1.7), which no golden's hello does;
    P26-B's `one_exit` reads a doorway stand's pick, for which only `f1-caps15` announces the stance, and the one door
    it reads free there, building 2's kitchen door (10721, 10638), has another way out on each of its 13 reads; P26-D
    and P26-E read a part's `bleeding` and a `wear`, which no golden ring carries."""
    only = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t7))}
    assert only == pre_t9_gold(key)   # named change, Plan 27 Task 1: `pre_t7` turns iteration 19 off (P27-B, E4)


# ================================================================ Plan 26 Task 7: iteration 18 on the goldens
@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_18_moves_no_golden(key):
    """Survival iteration 18 moves no golden: the six are byte-identical with its switches on
    (`test_the_golden_is_reproduced_byte_for_byte_from_its_artifact`) and off (`pre_t8`). P26-I and P26-J read a
    window way out and its act, which need a build announcing `window`, and no golden's hello does; P26-K reads a
    running doorway stand, which only `f1-caps15` reaches (its hello announcing the stance), on two lines (357 and
    518) with at most one zombie within DANGER_R, under STAND_CROWD_N. P26-L1 reads `body.armPain` (PZA/1.7), which no
    golden's frames carry; P26-L2 reads P26-D's bleed yield, and no golden's parts decode `bleeding`."""
    only = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t8))}
    assert only == pre_t9_gold(key)   # named change, Plan 27 Task 1: `pre_t8` turns iteration 19 off (P27-B, E4)


# ================================================================ Plan 27 Task 1: iteration 19 on the goldens
# the goldens as they stood before iteration 19 re-recorded them (Plan 26's close, `88fd464e`): sha256, base, recorded
PRE_T9 = {"e4": ("08be3096ea6b460e561c14050dc08887665e4504548d76783ee99c8457dcef84", "88fd464e", "2026-11-02")}
# the first line each iteration-19 switch moves, alone on, on each golden it moves
FIRST_T9 = {"e4": {"MANY_TAIL": 434}}


@functools.lru_cache(maxsize=6)
def _pre_t9_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t9), sort_keys=True)


def pre_t9_gold(key):
    """{line: decision} of the replay with iteration 19's switches off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t9_replayed(key)))}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_iteration_19_off_the_goldens_are_plan_26_s(key):
    """Iteration 19's golden movers are `survive.T9_SWITCHES`: with them off (`pre_t9`) a golden it re-recorded is the
    file as it stood before byte for byte (its sha256 pinned, `PRE_T9`), and every other golden is its file as
    iteration 20 left it off (named change, Plan 27 Task 5: P27-I re-recorded five, `pre_t10_gold`)."""
    if key not in PRE_T9:
        assert pre_t9_gold(key) == pre_t10_gold(key)
        return
    sha, base, recorded = PRE_T9[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t9_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_19_moves_e4_alone_at_the_many_tail(key):
    """Survival iteration 19's attribution, each switch alone on against the goldens before it (`pre_t9_gold`):
    - MANY_TAIL (P27-B) moves E4 alone, first at line 434 (game minute 620): the `many` episode begun before E4's
      endurance hold still ran under the `strain` flee (`flee_many`), and its fourth tick with no zombie standing
      within DANGER_R and one pressing ends it, logged `many_tail` {ticks 4, standing 0, pressing 1}, the decision
      unmoved; at line 441 the listing's four make `many` again (`listed` 4, a new episode as P24-A (a) reads it),
      the decision unmoved. No other line moves.
    - FLEE_FINISH (P27-A) moves no golden: its finish reads a zombie the frame reads `onFloor`, which no golden's frames
      carry. HOLD_LONE (P27-C) moves none: the hold fight needs a build announcing the PZA/1.7 `shove`, which no
      golden's hello does. HOLD_REST (P27-C2) moves none: E4's hold walk (lines 431 to 440, the one golden carrying
      `hold_walk`) reads a chaser listed on every line, its record reading no `hasTarget` false at all. SPENT_KEEP
      (P27-D) moves none: no golden ring decodes a bandaged part (PZA/1.4's parts carry no dressing). LOW_SWING (P27-E)
      moves none: the low fight needs the PZA/1.7 `shove`, as HOLD_LONE does.
    A golden no switch moves is its file before iteration 19 byte for byte. Named change, Plan 27 Task 5: read against
    the goldens with iteration 20 off (`pre_t10_gold`), whose P27-I re-recorded five."""
    base, got = pre_t9_gold(key), pre_t10_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T9:
        assert diff == []
        return
    assert diff[0] == min(FIRST_T9[key].values())
    for switch in S.T9_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t9(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T9[key].get(switch), switch
    assert diff == [434, 441]
    for k in diff:
        assert base[k]["action"] == got[k]["action"] and base[k]["branch"] == got[k]["branch"]
    assert got[434]["why"]["many_tail"] == {"ticks": 4, "standing": 0, "pressing": 1}
    assert got[434]["why"]["flee"] == "strain" and "many_tail" not in base[434]["why"]
    assert got[441]["why"]["listed"] == 4 and "listed" not in base[441]["why"]


# ================================================================ Plan 27 Task 5: iteration 20 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t10_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t10), sort_keys=True)


def pre_t10_gold(key):
    """{line: decision} of the replay with iteration 20's switches off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t10_replayed(key)))}


# the goldens as they stood before iteration 20 re-recorded them (Plan 27 Task 1's close): sha256, base, recorded
PRE_T10 = {"e2": ("1dd65da34adb1e64aaa7ddc6dea56e1b2fba0fb608487501279789e34fcc9f2e", "88fd464e", "2026-11-02"),
           "e3": ("c28c6a4b263f7399e48e2b1d429b755509500b5b930839ee96dd94f98c751ad8", "88fd464e", "2026-11-02"),
           "e4": ("63b2443b33ff7f6647c4581d6681c8c8c24943756d182378bf1025d515f3821a", "c1e04d78", "2026-11-03"),
           "e5": ("21d0e31baf772699707c95db81371550096493242ddefc53b11f32f8ba38fd7e", "88fd464e", "2026-11-02"),
           "f1": ("c093db79eaf3606348b3e4f18fd591093c7fac5e065ce22624229e27b3cf1870", "88fd464e", "2026-11-02"),
           SIXTH: ("9d0883924706f94c64a38d9090cba145f52a229a767db36925a859b5c4065a12", "88fd464e", "2026-11-02")}
# the first line each iteration-20 switch moves, alone on, on each golden it moves (P27-I's across clause: the zombie
# across the fence row listed beyond the hold radius; P27-K2's corner yield: E2's inside corner under FLEE_HEALTH_FLOOR;
# fix 2's P27-M: the sixth's first stance attack, its `attack` why)
FIRST_T10 = {"e2": {"LOW_EXIT": 222}, "e3": {"LISTING_FALLEN": 165}, "e4": {"LISTING_FALLEN": 381},
             "e5": {"LISTING_FALLEN": 217}, "f1": {"LISTING_FALLEN": 247},
             SIXTH: {"LISTING_FALLEN": 247, "ATTACK_REACH": 246}}
# the first line on each golden whose decision (branch or action) iteration 20 moves, else None (whys alone)
ACTED_T10 = {"e2": 222, "e4": 441, SIXTH: 320}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_iteration_20_off_the_goldens_are_iteration_19_s(key):
    """Iteration 20's golden movers are `survive.T10_SWITCHES`: with them off (`pre_t10`) a golden it re-recorded is
    the file as it stood before byte for byte (its sha256 pinned, `PRE_T10`), and every other golden is its file
    now."""
    if key not in PRE_T10:
        assert pre_t10_gold(key) == gold(key)
        return
    sha, base, recorded = PRE_T10[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t10_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_20_moves_the_six_goldens_at_the_listing_s_across_clause_and_e2_s_corner_yield(key):
    """Survival iteration 20's attribution, each switch alone on against the goldens before it (`pre_t10_gold`):
    - LOW_EXIT (P27-K2) moves E2 alone, first at line 222 (health under FLEE_HEALTH_FLOOR): the inside corner on 12839
      at 1.22 tiles, the record's, yields to the `health` flee's way out (logged `corner` {yield health}), the flee's
      walk to its exit 3 sent where the corner held its swing; the later moved lines are downstream (open loop).
    - LISTING_FALLEN (P27-I) moves E3, E4, E5, F1 and the sixth, each first where a zombie across the fence row (a
      known blocked edge, P25-X's) is listed beyond the hold radius on a threat line: its `listing` {fallen 0, across
      1 or 2} why (E3 165, E4 381, E5 217, F1 and the sixth 247), the decision unmoved; E3's, E5's, F1's and the
      sixth's moved lines are whys alone, and E4's decisions move from line 441, where the listing's four made `many`
      again before (`listed` 4, Task 1's P27-B re-entry) and now one of them, across the fence, is left out (`listing`
      {fallen 0, across 1}): the endurance hold's `strain` flee holds its running leg where the `many` steer went, and
      every later moved line is downstream of it (open loop). The clauses reach every read of the listing, so on E4
      under `LISTING_FALLEN` alone the `many_tail` why also moves, from line 434 to line 430, before line 441's
      decision change. No golden frame reads `onFloor`, so the fallen clause moves none. E2 lists no zombie across the
      row beyond its hold.
    - STUCK_LEAVE (P27-F) moves none: its mark reads a goal walk the goal runner sent, and the replay's goals are the
      record's (`RecordedGoals`). FLOOR_FINISH (P27-G) and FALLEN_SEEK (P27-H) move none: both read a zombie the
      frame reads `onFloor`. SHOVE_CLOSE (P27-J) moves none: a shove-only Fight and the hold's lone fight need a build
      announcing the PZA/1.7 `shove`, which no golden's hello does. STOCK_EARLY (P27-K1) moves none: no replayed
      golden tick sends the stock's rip (the replays above, each switch alone). REPLACE_QUIET (P27-K3) moves none: no
      golden ring decodes a bandaged part. P27-L (WOUNDED_SWING's default off) moves none: no golden frame carries
      `body.armPain`.
    - ATTACK_REACH (fix 2's P27-M) moves the sixth alone (the one golden whose hello announces the stance), first at
      line 246, the `attack` {dist, reach} why on the stance's attack at 15911 from 0.8922789090925147 tiles (the
      record's bat reads `weapon.reach` 1.125), the decision unmoved; its decisions move from line 320, where the
      attack at 15937 from 1.9071235531258082 tiles is held (`attack_held`) for the stance's standing leg, the attack
      going on line 321 from 0.37365609000281447; the later moved lines are downstream (open loop). The other goldens'
      hellos announce no `aim`, so their Fights are the approach and swing, which the rule leaves.
    - POINT_BLANK_PIN (fix 2's P27-N) moves none: the one marked zombie a golden lists within POINT_BLANK_R, the
      sixth's gate zombie 15885 (0.9282266374931059 tiles off at line 228), is refused across the fence row's blocked
      edge (`edge_marks`), which the pin leaves out; no golden frame reads a hit reaction. HEALTH_RIDE (fix 2's P27-O)
      moves none: no golden ring decodes a bleeding part.
    A golden no switch moves is its file before iteration 20 byte for byte. Named change, Plan 27 Task 5 fix 2: each
    switch's own first line is read at that line (`FIRST_T10`), the sixth's first moved line now P27-M's. Named
    change, Plan 28 Task 3: read against the goldens with iteration 21 off (`pre_t11_gold`), whose P28-C re-recorded
    four."""
    base, got = pre_t10_gold(key), pre_t11_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T10:
        assert diff == []
        return
    assert diff[0] == min(FIRST_T10[key].values())
    for switch in S.T10_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t10(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T10[key].get(switch), switch
    if "LISTING_FALLEN" in FIRST_T10[key]:
        first = FIRST_T10[key]["LISTING_FALLEN"]
        assert got[first]["why"]["listing"]["fallen"] == 0 and got[first]["why"]["listing"]["across"] >= 1
        assert "listing" not in base[first]["why"]
    if "LOW_EXIT" in FIRST_T10[key]:
        first = FIRST_T10[key]["LOW_EXIT"]
        assert base[first]["why"]["corner_kind"] == "inside" and got[first]["why"]["corner"] == {"yield": "health"}
        assert got[first]["why"]["flee"] == "health" and got[first]["action"]["type"] == "walkTo"
    if "ATTACK_REACH" in FIRST_T10[key]:
        first = FIRST_T10[key]["ATTACK_REACH"]
        assert got[first]["why"]["attack"] == {"dist": 0.8922789090925147, "reach": 1.125}
        assert "attack" not in base[first]["why"] and got[first]["action"] == base[first]["action"]
        held = got[ACTED_T10[key]]
        assert held["why"]["attack_held"] == {"target": 15937, "dist": 1.9071235531258082, "reach": 1.125}
        assert held["action"]["type"] == "aim" and base[ACTED_T10[key]]["action"]["type"] == "attack"
    acted = [k for k in diff if (base.get(k) or {}).get("action") != (got.get(k) or {}).get("action")
             or (base.get(k) or {}).get("branch") != (got.get(k) or {}).get("branch")]
    assert (acted[0] if acted else None) == ACTED_T10.get(key)


# ================================================================ Plan 28 Task 3: iteration 21 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t11_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t11), sort_keys=True)


def pre_t11_gold(key):
    """{line: decision} of the replay with iteration 21's switches off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t11_replayed(key)))}


# the goldens as they stood before iteration 21 re-recorded them (Plan 27's close): sha256, base, recorded
PRE_T11 = {"e2": ("90cea8a29fc7e8cedc6376a775587deb72d59f5942224bf75c30aad6fba46465", "d96f9318", "2026-11-03"),
           "e3": ("57fc396be0b7e9ebb3ebd85e58c13c3cb9bbb60ce3b27099b1a14bfdfe95e448", "2625cb96", "2026-11-03"),
           "e4": ("c76405232c9967825e7a97d8db63af000fe0722893be990e17855ab3fcabf6b0", "2625cb96", "2026-11-03"),
           "f1": ("9707340b286feee69c6035249724e57a965a4486000cb1b70feb3c963a13f035", "2625cb96", "2026-11-03"),
           SIXTH: ("adbf3f4a105a6dbf94b06c975ada722cfaf21a0e095f7a38247147321a7865da", "e4cf5b40", "2026-11-03")}
# the goldens a named change with no switch re-recorded in iteration 21, and the first line it moved: fix 1's R2,
# P28-F's planner side (the stance not read held after an attack), the sixth's follow-up attack at 15885 from
# 0.7801175874939513 tiles now its `enter` leg, the attack on line 441 from 1.0072464647115065 tiles
R2_MOVED = {SIXTH: 440}
# the first line each iteration-21 switch moves, alone on, on each golden it moves (APPROACH_WALK, the spec's 1 (b):
# the approach-and-swing Fight's first walk to a zombie beyond FIGHT_REACH, at a walk where the run went)
FIRST_T11 = {"e2": {"APPROACH_WALK": 146}, "e3": {"APPROACH_WALK": 170}, "e4": {"APPROACH_WALK": 302},
             "f1": {"APPROACH_WALK": 164}}
# every line on each golden whose decision (branch or action) iteration 21 moves: the approach walks' gait alone
ACTED_T11 = {"e2": [146, 156, 210], "e3": [170, 203], "e4": [302, 334, 371], "f1": [164, 223, 318, 353, 432, 516]}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_iteration_21_off_the_goldens_are_iteration_20_s(key):
    """Iteration 21's golden movers are `survive.T11_SWITCHES`: with them off (`pre_t11`) a golden it re-recorded is
    the file as it stood before byte for byte (its sha256 pinned, `PRE_T11`), and every other golden is its file
    now. Named change, fix 1's R2 (P28-F's planner side, no switch): the sixth (`R2_MOVED`) is its file now with the
    switches off too, and its file before (its sha256 in `PRE_T11`) is the file R2_FROZEN's archive holds, which that
    build replays byte for byte (`r2_frozen`). Named change, Plan 29 Task 2: "its file now" is the golden with
    iteration 23 off (`pre_t13_gold`), whose P29-G and P29-H' re-recorded the six."""
    if key in R2_MOVED:
        assert pre_t11_gold(key) == pre_t13_gold(key)
        r2_frozen("test_the_sixth_golden_is_f1_s_inputs_with_the_pza1_5_caps_reproduced_byte_for_byte")
        assert hashlib.sha256(_r2_frozen_run()[2].encode("utf-8")).hexdigest() == PRE_T11[key][0]
        return
    if key not in PRE_T11:
        assert pre_t11_gold(key) == pre_t13_gold(key)
        return
    sha, base, recorded = PRE_T11[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t11_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_21_moves_four_goldens_at_the_approach_walk(key):
    """Survival iteration 21's attribution, each switch alone on against the goldens before it (`pre_t11_gold`):
    - APPROACH_WALK (the spec's 1 (b), ruling P27-9, landed in P28-C's commit and its own switch since fix 1: the walk
      to a zombie beyond FIGHT_REACH of a Fight not in the stance at a walk, never a run, and so the approach after
      unstarted swings) moves E2, E3, E4 and F1, each first at its first approach walk
      (E2 line 146 at 12788 from 4.231606567324637 tiles, E3 170, E4 302, F1 164): `gait` "walk" where the record ran,
      logged `leg` "walk"; every moved decision is such a walk's gait (`ACTED_T11`), the other moved lines the
      `holding` lines under it carrying the same `leg` why. E5's replayed Fights send no walk beyond FIGHT_REACH, and
      the sixth's hello announces the stance, whose walks already go at a walk.
    - FLOOR_PAIN (P28-C) moves none: the floor swing under the pain reads `onFloor` and `body.armPain`, which no
      golden's frames carry.
    - WOUND_DRESS (P28-A) moves none: its step reads a part's `wound` (PZA/1.7.2), which no golden ring decodes.
    - SHOVE_BACK (P28-B2) moves none: its back leg follows a shove, which needs a build announcing the PZA/1.7 `shove`,
      and no golden's hello does. DRIFT_STAND (P28-B3) moves none: no replayed golden tick reads a cornered Fight's
      drifted pin (`out_of_reach`, on no golden line). SHOVE_R's 1.1 (no switch) reaches only the shoves.
    - CIRCLE (P28-E) moves none: no golden line logs a `back` leg (the sixth's stance legs are its `pull`, `seek`,
      `enter` and `stand` legs; the other hellos announce no `aim`).
    - BUSY_RETRY (P28-D) moves none: a shove or a stomp rejected `busy` needs a build announcing the PZA/1.7 `shove`
      and `stomp`, and no golden's hello does.
    A golden no switch moves is its file before iteration 21 byte for byte, but the sixth: fix 1's R2 (P28-F's planner
    side, no switch) re-recorded it, so `pre_t11` reproduces its file now and its file before is pinned by `PRE_T11`'s
    sha256 on R2_FROZEN's archive (`test_p28_f_s_planner_side_moves_the_sixth_at_its_follow_up_swing`). Named change,
    Plan 29 Task 2: read against the goldens with iteration 23 off (`pre_t13_gold`), whose P29-G and P29-H'
    re-recorded the six."""
    base, got = pre_t11_gold(key), pre_t13_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T11:
        assert diff == []
        return
    assert diff[0] == min(FIRST_T11[key].values())
    for switch in S.T11_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t11(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T11[key].get(switch), switch
    acted = [k for k in diff if base[k]["action"] != got[k]["action"] or base[k]["branch"] != got[k]["branch"]]
    assert acted == ACTED_T11[key]
    for k in acted:
        was, now = base[k]["action"], got[k]["action"]
        assert (was["type"], was["args"]["gait"]) == ("walkTo", "run") and now["type"] == "walkTo"
        assert dict(was["args"], gait="walk") == now["args"] and got[k]["why"]["leg"] == "walk"
        assert "leg" not in base[k]["why"] and got[k]["why"]["fight"] is True


def test_p28_f_s_planner_side_moves_the_sixth_at_its_follow_up_swing():
    """Fix 1's R2 (review-t1b R2; Task 1b `e75bf474`, `e9241a94`: the Lua releases the stance on the attack's first
    tick and keeps none after the swing), a named change with no switch: the stance is not read held after an attack
    (`fight.Fight.in_stance`, AIM_HOLD_S deleted). Against the sixth's file before it (R2_FROZEN's), the first moved
    line is 440: the follow-up attack at 15885 from 0.7801175874939513 tiles, read from the stance before, is the
    `enter` leg (0, 0) now, and the attack goes on line 441 from 1.0072464647115065 tiles; every later moved line is
    downstream (open loop). The other five goldens' hellos announce no `aim`, so their Fights never read the stance.
    Named change, ruling P30-C (Plan 30 Task 3): read against the sixth with iteration 24 off (`pre_t14_gold`), whose
    `door_held` reads moved it from line 113."""
    old = {d["line"]: d for d in json.loads(_r2_frozen_run()[2])["decisions"]}
    new = pre_t14_gold(SIXTH)
    diff = [k for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]
    assert diff[0] == R2_MOVED[SIXTH]
    was, now, then = old[440], new[440], new[441]
    assert was["action"] == {"type": "attack", "args": {"targetId": 15885}} and was["why"]["stance"] is True
    assert was["why"]["dist"] == 0.7801175874939513
    assert now["action"]["type"] == "aim" and now["why"]["leg"] == "enter"
    assert now["action"]["args"]["targetId"] == 15885
    assert then["action"] == {"type": "attack", "args": {"targetId": 15885}}
    assert then["why"]["dist"] == 1.0072464647115065


# ================================================================ Plan 28 Task 7b: iteration 22 on the goldens
@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_22_moves_no_golden(key):
    """Survival iteration 22 (cut 1 of the maneuver layer: the melee maneuver, `dispatch.FightDispatch`, gated on a
    hello announcing PZA/1.8's `melee`) moves no golden: no golden's record has a hello announcing `melee`, nor does
    the sixth's added caps (`HELLO_CAPS`: the PZA/1.5 skills), so every Fight sends its ladder's command; the six are
    byte-identical with MELEE on (`test_the_golden_is_reproduced_byte_for_byte_from_its_artifact`) and off
    (`pre_t12`). The refactors beside it (the ladder's body as `Fight._ladder`, the kill read's `_read_dead`, the
    replay's LEG_TYPES gaining `melee`) move none either. Named change, Plan 29 Task 2: read against the goldens with
    iteration 23 off (`pre_t13_gold`), whose P29-G and P29-H' re-recorded the six."""
    lines, _ = R.read_record(run_dir(key))
    hellos = [ln for ln in lines if ln.get("kind") == "hello"]
    assert hellos and not any("melee" in (h.get("caps") or ()) for h in hellos)
    assert "melee" not in (R.HELLO_CAPS.get(key) or ())
    off = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t12))}
    assert off == pre_t13_gold(key)


# ================================================================ Plan 29: iteration 23 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t13_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t13), sort_keys=True)


def pre_t13_gold(key):
    """{line: decision} of the replay with iteration 23's switches off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t13_replayed(key)))}


# the goldens as they stood before iteration 23 re-recorded them (Plan 28's close): sha256, base, recorded
PRE_T13 = {"e2": ("22079b3cfd05424afc223ba8cbe04ca0a2a1042dee718665715ee052c45a9812", "f229e492", "2026-11-04"),
           "e3": ("071091035506608c8be230e41182e0bd845f75ade43ab57a83e1c911fac18aa7", "f229e492", "2026-11-04"),
           "e4": ("415b17d4b89581f787d7aad5f2869dcaef622112de5b9f990c85500001c70483", "f229e492", "2026-11-04"),
           "e5": ("dec025ecd9f457472e9cc4be440455c59a81be15f1b2086f6e4fbce78f40c166", "2625cb96", "2026-11-03"),
           "f1": ("99037dd794ed197afd6212393dc194d64b587ff5e0b4b3a4b37730a68331b03d", "f229e492", "2026-11-04"),
           SIXTH: ("f5e2782cc4fbc9a2c6343e68e4e23a2d6007fc5871944deb14c11e2cb258c5b3", "388a3c1a", "2026-11-04")}
# the first line each iteration-23 switch moves, alone on, on each golden it moves (P29-G's count over the standing
# within DANGER_R: the first `many` the hold radius's, the DANGER_R count's or an episode's read made with at most one
# standing within it; P29-H': the first shelter step's or exit's walk read heading at a held zombie)
FIRST_T13 = {"e2": {"FLEE_HELD_STANCE": 148}, "e3": {"MANY_NEAR": 204, "FLEE_HELD_STANCE": 231},
             "e4": {"MANY_NEAR": 390}, "e5": {"FLEE_HELD_STANCE": 221},
             "f1": {"MANY_NEAR": 484, "FLEE_HELD_STANCE": 518}, SIXTH: {"MANY_NEAR": 484, "FLEE_HELD_STANCE": 527}}
# every line on each golden whose decision (branch or action) iteration 23 moves
ACTED_T13 = {"e2": [148, 156, 186, 192], "e3": [204, 210, 231, 237, 243, 249, 255, 256, 265, 268, 271, 272],
             "e4": [447, 449, 450, 454, 455], "e5": [221, 222, 224, 229, 231],
             "f1": [484, 485, 491, 492, 498, 499, 518, 521, 528, 532, 537, 557, 607, 610, 612, 614],
             SIXTH: [484, 485, 491, 492, 498, 499, 527, 532, 537, 540, 557, 607, 610, 612, 614]}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_23_moves_no_golden(key):
    """Survival iteration 23's Task 1 (ruling P29-A, `ROUTE_CROSS`: the route through a door walks one step beyond its
    far square and reads its end by whether it crossed) moves no golden: no golden's replay sends a route walk (every
    `blocked_edge` the six log is a refusal, which P29-A leaves as it was, and no route leg ends, so no door is noted or
    read marked), and their goal branch is the record's (`RecordedGoals`), never the goals' kit nor the runner's
    budget end (ruling P29-B, `GOAL_STALL`: no stall is read): the six are byte-identical with Task 1's switches on
    (`test_the_golden_is_reproduced_byte_for_byte_from_its_artifact`) and off. Named change, Plan 29 Task 2: Task 2's
    hit rules (`T13_SWITCHES[2:]`) stay on here, since P29-G and P29-H' re-recorded the six (the attribution,
    `test_iteration_23_s_hit_rules_move_the_goldens_at_the_many_count_and_the_flee_walk_s_heading`); the name is
    Task 1's. Named change, Plan 30 Task 3: read against the goldens with iteration 24 off (`pre_t14_gold`), whose
    P30-C re-recorded the six."""
    rows = pre_t14_gold(key)
    assert all((d["why"] or {}).get("blocked_edge", {}).get("action") in (None, "refuse") for d in rows.values())
    off = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                       mutate=lambda sv: pre_t13(sv, keep=S.T13_SWITCHES[2:])))}
    assert off == rows


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_iteration_23_off_the_goldens_are_iteration_22_s(key):
    """Iteration 23's golden movers are `survive.T13_SWITCHES`: with them off (`pre_t13`) a golden it re-recorded is
    the file as it stood before byte for byte (its sha256 pinned, `PRE_T13`), and every other golden is its file
    now."""
    if key not in PRE_T13:
        assert pre_t13_gold(key) == gold(key)
        return
    sha, base, recorded = PRE_T13[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t13_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_23_s_hit_rules_move_the_goldens_at_the_many_count_and_the_flee_walk_s_heading(key):
    """Survival iteration 23's attribution, each switch alone on against the goldens before it (`pre_t13_gold`):
    - MANY_NEAR (ruling P29-G: the `many` flee's count the standing zombies within DANGER_R, over MAX_FIGHT to begin
      an episode, MAX_FIGHT to hold one) moves E3, E4, F1 and the sixth, each first at its first `many` read with at
      most one standing within DANGER_R where the reads before it made one: E3 line 204 (one standing, `many_near`
      {n 1}: the Fight's walk held where the `many` steer went), E4 line 390 (an episode's tick held by the nearest
      within DANGER_R, one standing: the `held` reason on the running leg, the decision unmoved; its decisions move
      from line 447), F1 and the sixth line 484 (one standing: the Fight held where the `many` steer went); every
      moved line logs `many_near` or is downstream of one (open loop), each acted line listed (`ACTED_T13`). E2 and
      E5 read no `many` the count leaves.
    - FLEE_HELD_STANCE (ruling P29-H': a flee walk whose observed heading runs at a held zombie dropped with its plan,
      the door marked `walled`) moves E2, E3, E5, F1 and the sixth, each first at its first shelter step's or exit's
      walk read heading at a held zombie within AHEAD_CONE or the CORRIDOR_R tube, logged `flee_held_stance` {target,
      heading, bearing, d}: E2 line 148 (exit 3's walk, 12839 2.807 tiles off: the Fight's walk where the walk ran
      on; fix 1, review-t2 M2: its outside square marked `walled`, so no later episode walks exit 3 again, lines 186
      and 192's `pair` flees among them), E3 231 (building 2's approach, 14926), E5 221 (building 2's approach,
      19275), F1 518 (building 2's approach, 15921) and the sixth 527 (the same approach under its `many` flee): the
      walk dropped, the steer or the fight in its place, every later moved line downstream (open loop). E4's flee
      walks read no held zombie ahead.
    - ROUTE_CROSS (P29-A) and GOAL_STALL (P29-B) move none (`test_iteration_23_moves_no_golden`). HEALTH_NEAR (P29-E)
      moves none: every golden `health` line holds a zombie within DANGER_R. DRESS_FINISH (P29-D) moves none: no golden
      flee commands over a running dressing with nobody within DANGER_R (the sixth's hello alone announces `bandage`,
      and F1's parts decode `bleeding` None). FINISH_LONE (P29-F) moves none: its pin's finish needs a zombie read
      `onFloor` (no golden frame carries it), a shove's knock window or a melee (no golden hello announces either).
      CLOSE_IDLE (P29-C) moves none: P27-J's close needs a shove-only Fight, so a build announcing the PZA/1.7 `shove`.
    A golden no switch moves is its file before iteration 23 byte for byte. Named change, Plan 30 Task 3: read against
    the goldens with iteration 24 off (`pre_t14_gold`), whose P30-C re-recorded the six."""
    base, got = pre_t13_gold(key), pre_t14_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    if key not in FIRST_T13:
        assert diff == []
        return
    assert diff[0] == min(FIRST_T13[key].values())
    for switch in S.T13_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t13(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T13[key].get(switch), switch
    if "MANY_NEAR" in FIRST_T13[key]:
        first = FIRST_T13[key]["MANY_NEAR"]
        assert base[first]["why"]["flee"] == "many" and got[first]["why"]["many_near"]["n"] <= 1
    if "FLEE_HELD_STANCE" in FIRST_T13[key]:
        first = FIRST_T13[key]["FLEE_HELD_STANCE"]
        cut = got[first]["why"]["flee_held_stance"]
        assert base[first]["why"]["step"] in ("approach", "walk") and base[first]["why"].get("holding")
        assert set(cut) == {"target", "heading", "bearing", "d"} and cut["d"] <= P.AHEAD_R
    acted = [k for k in diff if base[k]["action"] != got[k]["action"] or base[k]["branch"] != got[k]["branch"]]
    assert acted == ACTED_T13[key]
    assert all("many_near" not in base[k]["why"] and "flee_held_stance" not in base[k]["why"] for k in diff)


def test_an_unbound_melee_ends_done_at_its_seconds():
    """`melee` is one of the replay's LEG_TYPES (Plan 28 Task 7b): an unbound PZA/1.8 one ends `done`, its result
    empty, once its `seconds` have passed on the clock, as an unbound stance leg does, so a replayed span was 2.5 s
    long (Plan 28's MELEE_S); a PZA/1.10 one (Plan 31 Task 2) has no `seconds` and never ends on time."""
    from agent.base.actions import Action
    assert R.LEG_TYPES == ("steer", "aim", "melee")
    acts = R._Acts(None, [])
    a = Action(aid="a1", type="melee", args={"targetId": 9, "seconds": 2.5}, deadline_s=30.0, sent_wall=100.0)
    b = Action(aid="a2", type="melee", args={"targetId": 9, "faceR": 3.0}, deadline_s=30.0, sent_wall=100.0)
    acts.unbound.extend([a, b])
    acts.end_legs(100.0 + 2.5 - 0.1)
    assert a.state == "sent"
    acts.end_legs(100.0 + 2.5)
    assert (a.state, a.result, a.ended_wall) == ("done", {}, 100.0 + 2.5)
    acts.end_legs(100.0 + 3600.0)
    assert b.state == "sent"


# ================================================================ Plan 30 Task 3: iteration 24 on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t14_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t14), sort_keys=True)


def pre_t14_gold(key):
    """{line: decision} of the replay with iteration 24's switches off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t14_replayed(key)))}


# the goldens as they stood before iteration 24 re-recorded them (Plan 30 Task 3, head 2d3622ef): sha256, base, recorded
PRE_T14 = {"e2": ("70565f1b2abc016d11d9ec18aea095d21c0ba4eb9e9eeb549722e3a3d38ac398", "2308cf4e", "2026-11-05"),
           "e3": ("0673248672bd894193b351c26ebb5038c1570b0b1a55690f9945e15e4ddac08c", "9d09d625", "2026-11-05"),
           "e4": ("dc169846d69eb0b696f9aef5ca945bd9d687901350590d30ab5c38f4815b33e2", "e6b6e8e3", "2026-11-05"),
           "e5": ("566c61bcb5f0ee9af355c4d112f79bfd5440fcae95117fa4332d0ef55de5386e", "9d09d625", "2026-11-05"),
           "f1": ("5a1bf679dda5d46d1a2817e9a1efbb8a38ac1481801121df3799563ddc5312bb", "9d09d625", "2026-11-05"),
           SIXTH: ("8628bd14d538009267067356100e1917aa50b74f1e1a18a62f86d4970243ee01", "9d09d625", "2026-11-05")}
# the first line each iteration-24 switch moves, alone on, on each golden it moves (P30-C: the first `door_held` read,
# a `leave` at the locked gate (10732, 10642) on every golden, the gate zombie within DOOR_HELD_R behind it)
FIRST_T14 = {"e2": {"DOOR_HELD": 75}, "e3": {"DOOR_HELD": 103}, "e4": {"DOOR_HELD": 261}, "e5": {"DOOR_HELD": 89},
             "f1": {"DOOR_HELD": 113}, SIXTH: {"DOOR_HELD": 113}}
# every line on each golden whose decision (branch or action) iteration 24 moves
ACTED_T14 = {"e2": [], "e3": [], "e5": [],
             "e4": [590, 591, 597, 603, 610, 616, 659, 665, 666, 671, 673, 678, 680, 685, 687, 692, 694, 697, 698, 701,
                    705, 707, 712, 714, 719, 721, 726, 728, 733, 734, 740, 741, 746, 748, 753, 755, 760, 762, 767, 768,
                    774, 775, 780, 781, 787, 788, 793, 795, 800, 801, 806, 808, 813, 815, 819, 821, 826, 828, 833, 835,
                    840, 841, 847, 848, 854, 861, 868, 869, 875],
             "f1": [468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 485, 528, 532, 535, 537, 540,
                    541, 542],
             SIXTH: [468, 469, 470, 471, 472, 473, 474, 479, 481, 483, 485, 487, 491, 493, 498, 499, 532, 533, 534, 536,
                     537, 540, 541, 542, 543]}
GATE_LEAVE = {"door": [10732, 10642], "kind": "locked gate", "n_behind": 1, "decision": "leave"}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_iteration_24_off_the_goldens_are_iteration_23_s(key):
    """Iteration 24's golden movers are `survive.T14_SWITCHES`: with them off (`pre_t14`) each golden it re-recorded is
    the file as it stood before byte for byte (its sha256 pinned, `PRE_T14`)."""
    sha, base, recorded = PRE_T14[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t14_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_iteration_24_moves_the_goldens_at_the_door_held_read(key):
    """Survival iteration 24's attribution (Plan 30 Task 3), each switch alone on against the goldens before it
    (`pre_t14_gold`):
    - DOOR_HELD (ruling P30-C: a zombie behind a closed door, a locked gate or a window within DOOR_HELD_R decided on
      one tick) moves all six, each first at its first `door_held` read, a `leave` at the locked gate (10732, 10642)
      with the gate zombie behind it (`GATE_LEAVE`): E2 line 75, E3 103, E4 261, E5 89, F1 and the sixth 113. On E2, E3
      and E5 only the why moves (each read logged, the gate zombie already edge-marked out of the hold by P25-X's
      refusal). On E4 the decisions move from line 590, two lines after a `leave` at the window (10768, 10637) took a
      zombie behind it out of the `unarmed` flee's group (its centroid, so its heading), every later moved line
      downstream (open loop); on F1 and the sixth from line 468, where the gate zombie's `leave` left the running
      Fight's walk at 15885 (7.9 tiles off) with no held zombie within DANGER_R, so the fight was released (P24-X's
      release, `Engage._released`) and the goal ran. Every moved line logs `door_held` or is downstream of one; each
      acted line is listed (`ACTED_T14`).
    - SWING_CLOSE (P30-A) moves none: no golden's hello announces `melee`. GOAL_CONTINUE (P30-B) moves none: the goal
      branch is the record's (`RecordedGoals`). SNEAK (P30-D) moves none: no golden's hello announces `sneak`.
      DRESS_RIDE (P30-F) moves none: no golden sends a dressing (no decision line's action is a `bandage`), so no
      flee waits on one. STILL
      (P30-E) moves none: its read is only of a held zombie beyond the swing's reach (F1's and the sixth's line 481
      read 15910 steady at 1.060106611108762 tiles, inside it, while the Fight walked at 15885).
    A golden no switch moves is its file before iteration 24 byte for byte. Named change, Plan 32 Task 5: read against
    the goldens with the coward rules off (`pre_t16_gold`), which re-recorded the six."""
    base, got = pre_t14_gold(key), pre_t16_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    assert diff[0] == min(FIRST_T14[key].values())
    for switch in S.T14_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t14(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        assert (moved[0] if moved else None) == FIRST_T14[key].get(switch), switch
    first = FIRST_T14[key]["DOOR_HELD"]
    assert got[first]["why"]["door_held"] == GATE_LEAVE and "door_held" not in base[first]["why"]
    acted = [k for k in diff if base[k]["action"] != got[k]["action"] or base[k]["branch"] != got[k]["branch"]]
    assert acted == ACTED_T14[key]
    assert all("door_held" not in base[k]["why"] for k in diff)


# ================================================================ Plan 32 Task 5: the coward rules on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t16_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t16), sort_keys=True)


def pre_t16_gold(key):
    """{line: decision} of the replay with the coward rules off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t16_replayed(key)))}


# the goldens as they stood before the coward rules re-recorded them (Plan 32 Task 5, head 8b632ee5, the files of
# `9587540f`): sha256, base, recorded
PRE_T16 = {"e2": ("f4e37bc0632dd4504aad26daf2e3675fddc29137ab1dc5a7c70ffc882c355173", "f299f985", "2026-11-05"),
           "e3": ("2949482e8ac5f1c1b8ea971f81e6596b08de0919f2ac44e2dfb4182085b5bfaf", "f299f985", "2026-11-05"),
           "e4": ("3d22242618dfd3da864ada19cb74a1cf3793c0e273fe3ac0b7c552d144ad5843", "f299f985", "2026-11-05"),
           "e5": ("85a1cce564454073c504c2c373f5b1decef0937598f94fb195ad411fd071967b", "f299f985", "2026-11-05"),
           "f1": ("a2d2fc5a6a2fbb2171f3de6b4aa0e821464f6e0861dde4a8c7a5523726437856", "f299f985", "2026-11-05"),
           SIXTH: ("dcaf7a2389409efcf4ddbcf312da40a37ee283080cea0a209159a3942b5249ec", "f299f985", "2026-11-05")}
# the first line each coward rule moves, alone on, on each golden it moves (CARE_COMMIT moves none: no golden's frames
# carry a part the care dresses under a held threat)
FIRST_T16 = {"e2": {"POINT_BLANK_FIGHT": 181, "PAIR_NEAREST": 193},
             "e3": {"POINT_BLANK_FIGHT": 257, "PAIR_NEAREST": 260},
             "e4": {"POINT_BLANK_FIGHT": 446, "PAIR_NEAREST": 450, "STRAIN_BOUND": 423},
             "e5": {"POINT_BLANK_FIGHT": 222, "PAIR_NEAREST": 233},
             "f1": {"POINT_BLANK_FIGHT": 519, "PAIR_NEAREST": 568, "STRAIN_BOUND": 557},
             SIXTH: {"POINT_BLANK_FIGHT": 520, "PAIR_NEAREST": 568, "STRAIN_BOUND": 557}}
# the why each rule logs on the first line it moves alone
WHY_T16 = {"POINT_BLANK_FIGHT": "point_blank_fight", "PAIR_NEAREST": "pair_nearest", "STRAIN_BOUND": "strain_bound"}
# every line on each golden whose decision (branch or action) the four rules move together
ACTED_T16 = {"e2": [206, 210, 211],
             "e3": [257, 260, 263, 265, 268, 271, 272, 273, 276, 278, 281, 284],
             "e4": [424, 431, 438, 442, 447, 450, 452, 454, 457, 460, 462, 465, 468, 471, 474, 477, 480, 483, 485, 486,
                    489, 491, 492, 494, 498, 499, 504, 506, 511, 513, 518, 519, 525, 526, 531, 533, 538, 539, 545, 546,
                    552, 558, 565, 571],
             "e5": [222, 224, 225, 226, 229, 231, 236, 239, 242],
             "f1": [519, 520, 521, 525, 528, 532, 535, 536, 537, 541, 542, 543, 557, 559, 607, 610, 612, 614],
             SIXTH: [520, 525, 526, 527, 557, 558, 568, 569, 572, 573, 575, 576, 589, 590, 591, 592, 593, 594, 596, 597,
                     599, 600, 603, 604, 607, 609, 610, 612, 614]}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_the_coward_rules_off_the_goldens_are_plan_31_s(key):
    """The coward rules' golden movers are `survive.T16_SWITCHES`: with them off (`pre_t16`) each golden is the file as
    it stood before their re-record byte for byte (its sha256 pinned, `PRE_T16`)."""
    sha, base, recorded = PRE_T16[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t16_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_the_coward_rules_move_the_goldens_at_their_lines(key):
    """Named change `Plan 32 Task 5: the coward rules on by default`, each switch alone on against the goldens before it
    (`pre_t16_gold`):
    - POINT_BLANK_FIGHT ((a): a standing zombie within KEEP_R fought whatever the flee reason) moves all six, each first
      at its first flee read with one standing within KEEP_R: E2 line 181, E3 257, E4 446, E5 222, F1 519, the sixth
      520, each logging `point_blank_fight`.
    - PAIR_NEAREST ((b): two within KEEP_R, the nearer standing one the pin) moves all six: E2 193, E3 260, E4 450, E5
      233, F1 and the sixth 568, each logging `pair_nearest`.
    - STRAIN_BOUND ((d): the `strain` flee only at the moodle's second level) moves E4 from 423 and F1 and the sixth from
      557 (their endurance holds at the moodle's first level), each logging `strain_bound`; E2, E3 and E5 read no hold.
    - CARE_COMMIT ((c)) moves none: no golden's frames carry a part the care dresses under a held threat (E2 to E5's
      hellos announce no `bandage`, F1's parts decode no `bleeding` or `wound`).
    The four together move each golden first at the least of those lines, every later moved line downstream (open
    loop); the acted lines (branch or action moved) are `ACTED_T16`. Named change, Plan 33 Task 3: read against the
    goldens with the group rules off (`pre_t17_gold`), which re-recorded five of the six."""
    base, got = pre_t16_gold(key), pre_t17_gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    assert diff[0] == min(FIRST_T16[key].values())
    for switch in S.T16_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t16(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        first = moved[0] if moved else None
        assert first == FIRST_T16[key].get(switch), switch
        if first is not None:
            assert WHY_T16[switch] in alone[first]["why"] and WHY_T16[switch] not in base[first]["why"], switch
    acted = [k for k in diff if base[k]["action"] != got[k]["action"] or base[k]["branch"] != got[k]["branch"]]
    assert acted == ACTED_T16[key]


# ================================================================ Plan 33 Task 3: the group rules on the goldens
@functools.lru_cache(maxsize=6)
def _pre_t17_replayed(key):
    return json.dumps(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key), mutate=pre_t17), sort_keys=True)


def pre_t17_gold(key):
    """{line: decision} of the replay with the group rules off: the golden before its re-record."""
    return {d["line"]: d for d in R.decisions(json.loads(_pre_t17_replayed(key)))}


# the goldens as they stood before the group rules re-recorded them (Plan 33 Task 3, head cf37c14e, the files of
# Plan 32 Task 5's `e0a1f0b9`): sha256, base, recorded
PRE_T17 = {"e2": ("b521d04739ecfafb186f857a8646f3898d31e12cde7665daca2af70c56cf813e", "8b632ee5", "2026-11-08"),
           "e3": ("14e8dcb46ded6e2ccb956f5ae5fee58477ac50ef9bfc659ac436838b6e47dcbe", "8b632ee5", "2026-11-08"),
           "e4": ("a1fe9ace284863b30a12952d260d7ffa77a55aa5c3d7a70709ddf5c73a6bdfc3", "8b632ee5", "2026-11-08"),
           "e5": ("2acf059c7f681ba1aac0252ebf3b18a70cc181dca7cd42918215884e97791ae5", "8b632ee5", "2026-11-08"),
           "f1": ("efeb9f29274de7c6b5fab3a7e67b2a9b4d8f9db5e2da13ec658be68fa211c671", "8b632ee5", "2026-11-08"),
           SIXTH: ("c367497f922e1eebc8b875a72690c68278a77e50e7315e1e9d759073987224c8", "8b632ee5", "2026-11-08")}
# the first line each group rule moves, alone on, on each golden it moves (DRAG_GUARD_FIGHT moves none: no golden's
# frames read the drag-down guard under a hit reaction or unmoving)
FIRST_T17 = {"e2": {},
             "e3": {"GROUP_LEAVE": 260},
             "e4": {"GROUP_LEAVE": 388, "SIDE_CLEAR": 489},
             "e5": {"GROUP_LEAVE": 224},
             "f1": {"SIDE_CLEAR": 610},
             SIXTH: {"SIDE_CLEAR": 610}}
# the why each rule logs on the first line it moves alone
WHY_T17 = {"GROUP_LEAVE": "group_leave", "DRAG_GUARD_FIGHT": "drag_fight", "SIDE_CLEAR": "side_clear"}
# every line on each golden whose decision (branch or action) the three rules move together; E4's re-read at Task 3
# fix 2 (SIDE_CLEAR's least-bad run in its shove's place: line 489 now the wanted heading's run, as the record's);
# E4's and E5's re-read at Task 3 fix 4 (the leave's `run` leg above RETREAT_MAX_N): E4 gains 478 and 479 (the `many`
# flee's run steers at five standing) and 489 and 491 (downstream of the run) and loses 482 (the run's held steer, now
# the pre-group golden's line where the fix-3 retreat attacked); E5 gains 229, 233 and 236 (the run's lines at six and
# seven standing where the fix-3 retreat attacked) and loses 226 (the retreat pin's attack at 19278, now the pre-group
# golden's line where the fix-3 retreat held)
ACTED_T17 = {"e2": [],
             "e3": [],
             "e4": [388, 395, 469, 470, 471, 474, 477, 478, 479, 485, 489, 491, 492, 494, 495, 499, 501, 502, 503, 506, 509, 513, 516, 519,
                    522, 526, 529, 533, 536, 539, 543, 546, 550, 552, 556, 558, 563, 565, 566, 567, 568,
                    569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 582, 583, 584, 585, 586, 587, 780,
                    781, 787, 788, 793, 795, 800, 801, 806, 808, 813, 815, 819, 821, 826, 828, 833, 835,
                    840, 841, 847, 848, 854, 861, 868, 869, 875, 950, 963, 964, 966, 967, 968, 969, 973,
                    975, 976, 979, 983, 986, 989, 993, 996, 1000, 1061, 1068, 1075, 1082, 1089, 1096,
                    1102, 1109, 1116, 1121, 1123, 1124, 1126, 1132, 1139, 1274, 1280, 1281, 1286, 1288,
                    1293, 1295, 1300, 1302, 1307, 1308, 1314, 1315, 1320, 1322, 1327, 1329, 1334, 1336,
                    1341, 1343, 1348, 1350, 1354, 1356, 1361, 1363, 1367, 1369, 1374, 1376, 1381, 1383,
                    1388, 1389, 1394, 1396, 1401, 1403, 1408, 1410, 1415, 1417, 1421, 1423, 1428, 1430,
                    1435, 1437, 1442, 1444, 1448, 1451, 1455, 1458, 1462, 1465, 1468, 1471, 1474, 1478,
                    1481, 1484, 1487, 1491, 1494, 1497, 1501, 1504, 1506, 1508, 1509, 1513, 1516, 1519,
                    1522, 1526, 1528, 1533, 1535, 1540, 1542, 1547, 1549, 1554, 1555, 1560, 1562, 1567,
                    1569, 1574, 1576, 1581, 1583, 1588, 1590, 1594, 1596, 1601, 1603, 1608, 1610, 1614,
                    1616, 1621, 1622],
             "e5": [225, 228, 229, 233, 236],
             "f1": [610, 614],
             SIXTH: [610, 614]}


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_with_the_group_rules_off_the_goldens_are_plan_32_s(key):
    """The group rules' golden movers are `survive.T18_SWITCHES`: with them off (`pre_t17`) each golden is the file as
    it stood before their re-record byte for byte (its sha256 pinned, `PRE_T17`)."""
    sha, base, recorded = PRE_T17[key]
    text = R.golden_text(R.decisions(json.loads(_pre_t17_replayed(key))), base, R.RUNS[key], recorded,
                         R.SPANS.get(key), R.HELLO_CAPS.get(key))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha


@pytest.mark.parametrize("key", sorted(PRE_EDGE_OUT))
def test_the_group_rules_move_the_goldens_at_their_lines(key):
    """Named change `Plan 33 Task 3: GROUP_LEAVE, DRAG_GUARD_FIGHT and SIDE_CLEAR on by default`, each switch alone on
    against the goldens before it (`pre_t17_gold`):
    - GROUP_LEAVE (fix 3, re-recorded under `Plan 33 Task 3 fix 3: GROUP_LEAVE at three closing`: GROUP_LEAVE_N 3 closing
      within GROUP_ENTRY_R, no FIGHT_REACH exception, the fighting retreat) moves E3 from line 260, E4 from 388 and E5
      from 224 (`group_leave`), and F1 and the sixth no longer (their fix-1 leaves at 444 were pairs): the why only on
      E3, the retreat's backpedal or shove sent where the record fought on E4 and E5 (`ACTED_T17`), every later moved
      line downstream (open loop).
    - SIDE_CLEAR moves E4 from line 489 (its long tail, a dead character's frames replayed to the day cap, every later
      moved line downstream) and F1 and the sixth from 610: a run steer passing a standing zombie turned to a clear
      heading, else (Task 3 fix 2, re-recorded under `Plan 33 Task 3 fix 2: ...`) to the least-bad heading where it
      sent the shove before (E4 489, F1 and the sixth 614; `side_clear` {least_bad}).
    - DRAG_GUARD_FIGHT moves none (no golden's guard line reads a hit reaction or the unmoving count). E2 moves under
      none, its file unchanged.
    The three together move each golden first at the least of those lines; the acted lines are `ACTED_T17`."""
    base, got = pre_t17_gold(key), gold(key)
    diff = [k for k in sorted(set(base) | set(got)) if base.get(k) != got.get(k)]
    assert (diff[0] if diff else None) == min(FIRST_T17[key].values(), default=None)
    for switch in S.T18_SWITCHES:
        alone = {d["line"]: d for d in R.decisions(R.replay(run_dir(key), caps=R.HELLO_CAPS.get(key),
                                                             mutate=lambda sv: pre_t17(sv, keep=(switch,))))}
        moved = [k for k in sorted(set(base) | set(alone)) if base.get(k) != alone.get(k)]
        first = moved[0] if moved else None
        assert first == FIRST_T17[key].get(switch), switch
        if first is not None:
            assert WHY_T17[switch] in alone[first]["why"] and WHY_T17[switch] not in base[first]["why"], switch
    acted = [k for k in diff if base[k]["action"] != got[k]["action"] or base[k]["branch"] != got[k]["branch"]]
    assert acted == ACTED_T17[key]
