"""drivers/p_grade_2.py (Plan 24 Task 19): the stance probe's regrade, offline on synthetic records and on the committed
artifact (p_stance-20261029-135919), which it reads and never writes. Each reading has a case that fails it: a leg
that never moves reads no movement run, a leg that moves to its end reads no stand, and the grade window's tiles are
the committed grade_p1's own on the real record."""
import json
import os

from agent.drivers import p_grade_2 as G

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ARTIFACT = os.path.join(REPO, "testing", "artifacts", "p_stance-20261029-135919", "p_stance.json")


def frames(xs, t0=1000.0, step_ms=100.0, seq0=10, moving=True):
    """Frames at x in `xs`, y 5.5, one every `step_ms` from `t0`."""
    return [{"seq": seq0 + i, "wallMs": t0 + i * step_ms, "x": x, "y": 5.5, "dir": "E", "pace": 0.9 if moving else 0,
             "moving": moving, "aiming": True, "forceAim": True} for i, x in enumerate(xs)]


def record(xs, acked=1050.0, end=None, **kw):
    fr = frames(xs, **kw)
    end = fr[-1]["wallMs"] if end is None else end
    step = {"step": "aim_strafe", "args": {"vx": -1.0, "vy": 0.0}, "ackedMs": acked, "endMs": end}
    stand = {"step": "aim_stand", "args": {"vx": 0.0, "vy": 0.0}, "ackedMs": acked, "endMs": end}
    return {"run_id": "synthetic", "probe": {"frames": fr, "steps": [stand, step]}, "grade_p1": {"strafe_tiles": None}}


def test_a_leg_that_moves_then_stands_reads_the_run_and_the_stand():
    xs = [10.5, 10.4, 10.3, 10.2] + [10.2] * 20
    r = G.regrade(record(xs))
    bp = r["backpedal"]
    assert bp["start"]["seq"] == 10                       # the frame before the ack is the start position
    assert abs(bp["leg_tiles"] - 0.3) < 1e-9
    assert bp["run"]["first_seq"] == 11 and bp["run"]["last_seq"] == 13
    assert abs(bp["run"]["tiles"] - 0.3) < 1e-9
    assert abs(bp["run"]["span_s"] - 0.3) < 1e-9
    assert abs(bp["run"]["tiles_per_s"] - 1.0) < 1e-9
    assert bp["stand"]["frames"] == 20 and bp["stand"]["positions"] == [(10.2, 5.5)]
    assert bp["grade_window"]["opens_after_run"] is True
    assert bp["grade_window"]["tiles"] == 0                # the settle window misses the whole run


def test_a_leg_that_never_moves_reads_no_run():
    r = G.regrade(record([10.5] * 30))
    assert r["backpedal"]["run"] is None and r["backpedal"]["stand"] is None
    assert r["backpedal"]["leg_tiles"] == 0


def test_a_leg_that_moves_to_its_end_reads_an_empty_stand():
    xs = [10.5 - 0.1 * i for i in range(30)]
    r = G.regrade(record(xs))
    assert r["backpedal"]["stand"]["frames"] == 0
    assert r["backpedal"]["grade_window"]["tiles"] > 1.0


def test_a_leg_with_no_frames_is_an_error_not_a_raise():
    rec = record([10.5] * 5, acked=99999.0, end=99999.5)
    assert "error" in G.regrade(rec)["backpedal"]


def test_the_counts_read_aiming_and_force_aim_apart():
    rec = record([10.5] * 12)
    for f in rec["probe"]["frames"][5:]:
        f["aiming"] = False
    leg = G.regrade(rec)["legs"]["aim_stand"]
    assert leg["n"] == 11 and leg["forceAim"] == 11 and leg["aiming"] == 4


def test_on_the_committed_record_the_grade_window_reproduces_grade_p1():
    with open(ARTIFACT, encoding="utf-8") as fh:
        rec = json.load(fh)
    r = G.regrade(rec)
    bp = r["backpedal"]
    assert bp["grade_window"]["tiles"] == rec["grade_p1"]["strafe_tiles"] == 0.09375
    assert bp["grade_window"]["n"] == rec["grade_p1"]["legs"]["aim_strafe"]["n"] == 40
    assert bp["leg_tiles"] == 1.01171875
    assert bp["run"]["last_seq"] == 415 and bp["stand"]["positions"] == [(10720.48828125, 10630.5)]
    assert r["legs"]["aim_stand"]["aiming"] == r["legs"]["aim_stand"]["n"] == 50
    assert r["legs"]["aim_strafe"]["forceAim"] == r["legs"]["aim_strafe"]["n"] == 50

def test_the_stand_counts_read_moving_and_pace_zero_apart():
    xs = [10.5, 10.4, 10.3, 10.2] + [10.2] * 20
    rec = record(xs)
    for f in rec["probe"]["frames"][4:]:
        f["pace"] = 0
    st = G.regrade(rec)["backpedal"]["stand"]
    assert st["frames"] == 20 and st["moving_true"] == 20 and st["pace_zero"] == 20
    for f in rec["probe"]["frames"][4:10]:
        f["moving"] = False
        f["pace"] = 0.5
    st = G.regrade(rec)["backpedal"]["stand"]
    assert st["frames"] == 20 and st["moving_true"] == 14 and st["pace_zero"] == 14


def test_the_modal_step_is_the_most_common_not_the_last_or_the_largest():
    xs = [10.5, 10.4, 10.3, 10.2, 10.1, 9.9] + [9.9] * 10
    run = G.regrade(record(xs))["backpedal"]["run"]
    assert run["frames"] == 5 and abs(run["modal_step"] - 0.1) < 1e-9
    assert abs(run["steps"][-1] - 0.2) < 1e-9


def test_on_the_committed_record_the_run_and_the_stand_read_the_guide_s_values():
    with open(ARTIFACT, encoding="utf-8") as fh:
        rec = json.load(fh)
    bp = G.regrade(rec)["backpedal"]
    assert bp["run"]["span_s"] == 1.195
    assert bp["run"]["tiles_per_s"] == 0.8466265690376569
    assert bp["run"]["modal_step"] == 0.09375
    st = bp["stand"]
    assert st["frames"] == st["moving_true"] == st["pace_zero"] == 38
    assert st["span_s"] == 3.801


def test_it_refuses_any_argument_but_one_path(capsys):
    assert G.main([]) == 2
    assert G.main(["--session", "1"]) == 2
    assert G.main(["a.json", "b.json"]) == 2
    assert G.main([os.path.join(REPO, "no-such-record.json")]) == 2
