"""tools/facing_score.py (Plan 32 Task 2): the facing trials' scorecard, on a recorded fixture of three `probe` done act
lines (written by hand in the schema's keyed form through `pza1.encode`), a decision log of three `probe` lines and a
trial.json with a commit; the rows' shape, `--dry`, the in-place replace and `--rescore-all` keeping `seen`."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import facing_score as FS  # noqa: E402
import trial_score as TS  # noqa: E402

from agent.base import pza1  # noqa: E402

HEADER = ("# Facing trials\n\nthe header paragraph\n\n" + "| " + " | ".join(FS.COLUMNS) + " |\n|" +
          "---|" * len(FS.COLUMNS) + "\n")


def done(seq, aid, mode, pressed=False, press=None, **kw):
    res = {"ticks": 60, "mode": mode, "err_body_med": 12.34, "err_body_p90": 45.678, "err_look_med": 1.04,
           "err_look_p90": 3.96, "hold30": 0.5, "aiming_share": 0.9, "pressed": pressed, "press": press}
    res.update(kw)
    return pza1.encode("act", {"seq": seq, "tick": seq, "wallMs": 1000 + seq, "aid": aid, "type": "probe",
                               "state": "done", "reason": "", "result": res})


def other(seq, aid):
    return pza1.encode("act", {"seq": seq, "tick": seq, "wallMs": 1000 + seq, "aid": aid, "type": "aim",
                               "state": "done", "reason": "", "result": {}})


def write_run(runs, name, commit="0123456789abcdef", dirty=False, modes=("read", "snap_aimed", "turn_k"),
              hold30=(0.5, 0.2501, 1.0)):
    run = os.path.join(runs, name)
    sd = os.path.join(run, "clients", "admin", "Lua", "pzagent", "admin")
    os.makedirs(sd)
    lines = [other(1, "a1")]
    dec = [{"wall": 1.0, "branch": "probe", "action": {"type": "aim"}, "aid": "a1", "plan_index": None}]
    for i, m in enumerate(modes):
        press = {"d_press": 1.0, "look_off": 2.0, "hp0": 1.0, "hp1": 0.75, "cut_by": ""} if m == "snap_aimed" else None
        lines.append(done(2 + i, "a%d" % (i + 2), m, pressed=press is not None, press=press, hold30=hold30[i]))
        dec.append({"wall": 2.0 + i, "branch": "probe", "action": {"type": "probe"}, "aid": "a%d" % (i + 2),
                    "plan_index": i, "mode": m, "move": "back" if i == 2 else "still",
                    "k": 3.0 if m == "turn_k" else -1})
        dec.append({"wall": 2.5 + i, "branch": "probe", "action": None, "plan_index": i, "mode": m})
    with open(os.path.join(sd, "state.log"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(run, "decision.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(d) for d in dec) + "\n")
    with open(os.path.join(run, "trial.json"), "w", encoding="utf-8") as fh:
        json.dump({"variant": "facing", "commit": commit, "dirty": dirty, "fixture": "arena-east"}, fh)
    return run


@pytest.fixture
def log(tmp_path):
    p = tmp_path / "facing.md"
    p.write_text(HEADER, encoding="utf-8")
    return str(p)


def test_three_done_lines_score_to_three_rows_with_the_medians_copied(tmp_path):
    run = write_run(str(tmp_path / "runs"), "x_facing-20261108-100000")
    rows = FS.score(run)
    assert len(rows) == 3
    assert FS.COLUMNS[:3] == ("run", "commit", "mode") and FS.COLUMNS[-1] == "seen"
    c = [FS.cells(r) for r in rows]
    assert [x[0] for x in c] == ["x_facing-20261108-100000"] * 3
    assert [x[1] for x in c] == ["01234567"] * 3
    assert [x[2] for x in c] == ["read", "snap_aimed", "turn_k"]
    assert [x[3] for x in c] == ["still", "still", "back"]
    assert [x[4] for x in c] == ["-", "-", "3"]
    first = dict(zip(FS.COLUMNS, c[0]))
    assert (first["ticks"], first["body med"], first["body p90"], first["look med"], first["look p90"]) == (
        "60", "12.3", "45.7", "1.0", "4.0")
    assert (first["hold30"], first["aiming"], first["pressed"], first["hp0 -> hp1"], first["seen"]) == (
        "0.50", "0.90", "-", "-", "")
    assert dict(zip(FS.COLUMNS, c[1]))["hold30"] == "0.25"
    assert dict(zip(FS.COLUMNS, c[2]))["hold30"] == "1.00"
    snap = dict(zip(FS.COLUMNS, c[1]))
    assert (snap["pressed"], snap["hp0 -> hp1"]) == ("yes", "1.00 -> 0.75")


def test_a_dirty_commit_and_a_missing_trial_json_read_as_the_trial_scorer_reads_them(tmp_path):
    run = write_run(str(tmp_path / "runs"), "x_facing-20261108-100001", dirty=True)
    assert FS.cells(FS.score(run)[0])[1].startswith("01234567-dirty")
    os.remove(os.path.join(run, "trial.json"))
    assert FS.cells(FS.score(run)[0])[1] == "-"


def test_a_probe_that_did_not_end_done_scores_no_row(tmp_path):
    run = write_run(str(tmp_path / "runs"), "x_facing-20261108-100002", modes=("read",), hold30=(0.5,))
    sd = os.path.join(run, "clients", "admin", "Lua", "pzagent", "admin", "state.log")
    with open(sd, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(pza1.encode("act", {"seq": 9, "tick": 9, "wallMs": 2000, "aid": "a9", "type": "probe",
                                     "state": "failed", "reason": "not loaded", "result": {"missing": "getTwist"}}) + "\n")
    assert [r["mode"] for r in FS.score(run)] == ["read"]


def test_main_writes_the_rows_and_dry_writes_nothing(tmp_path, log, capsys):
    run = write_run(str(tmp_path / "runs"), "x_facing-20261108-100003")
    before = open(log, "rb").read()
    assert FS.main([run, "--log", log, "--dry"]) == 0
    assert open(log, "rb").read() == before
    assert FS.main([run, "--log", log, "--seen", "back-pedal lags"]) == 0
    head, rows, tail = TS.read_log_parts(log)
    assert len(rows) == 3 and TS.parse_row(rows[0])[-1] == "back-pedal lags"
    assert TS.parse_row(rows[1])[-1] == "back-pedal lags"
    assert FS.main([run, "--log", log]) == 0                      # the in-place replace keeps the seen text
    _, rows2, _ = TS.read_log_parts(log)
    assert len(rows2) == 3 and rows2 == rows
    assert FS.main([run, "--log", log, "--seen", "a", "--seen", "b"]) == 0
    _, rows3, _ = TS.read_log_parts(log)
    assert TS.parse_row(rows3[0])[-1] == "a / b"


def test_rescore_all_keeps_seen_adds_no_row_for_a_folder_with_none_and_keeps_a_gone_folders_rows(tmp_path, log):
    runs = str(tmp_path / "runs")
    a = write_run(runs, "x_facing-20261108-110000")
    assert FS.main([a, "--log", log, "--seen", "kept text"]) == 0
    gone = TS.format_row(["x_facing-20261101-000000", "-", "read", "still", "-"] + ["-"] * 10 + ["old seen"])
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(gone + "\n")
    write_run(runs, "x_facing-20261108-120000")                    # a folder with no row
    write_run(runs, "x_trial-20261108-130000")                     # not a facing run
    # the scorer changed its reading: rewrite a's state with another body median
    sd = os.path.join(a, "clients", "admin", "Lua", "pzagent", "admin", "state.log")
    with open(sd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(other(1, "a1") + "\n" + done(2, "a2", "read", err_body_med=99.0) + "\n" +
                 done(3, "a3", "snap_aimed") + "\n" + done(4, "a4", "turn_k") + "\n")
    before = open(log, "rb").read()
    FS.rescore_all(log, runs, dry=True)
    assert open(log, "rb").read() == before
    assert FS.main(["--rescore-all", "--log", log, "--runs", runs]) == 0
    _, rows, _ = TS.read_log_parts(log)
    cells = [TS.parse_row(r) for r in rows]
    assert [c[0] for c in cells] == ["x_facing-20261108-110000"] * 3 + ["x_facing-20261101-000000"]
    assert cells[0][FS.COLUMNS.index("body med")] == "99.0" and cells[0][-1] == "kept text"
    assert rows[3] == gone
    assert os.path.isdir(os.path.join(runs, "x_facing-20261108-120000"))


def test_the_command_line_refuses_what_it_does_not_define():
    for argv in (["r", "--bogus"], ["r", "--dr"], [], ["r", "--rescore-all"], ["--rescore-all", "--seen", "x"],
                 ["r", "--seen", "1", "--seen", "2", "--seen", "3", "--seen", "4"]):
        with pytest.raises(SystemExit) as e:
            FS.parse_args(argv)
        assert e.value.code == 2, argv


def test_the_committed_log_has_the_header_the_columns_and_no_rows():
    log = os.path.join(FS.REPO, "testing", "trials", "facing.md")
    head, rows, tail = TS.read_log_parts(log)
    text = "\n".join(head)
    assert "| " + " | ".join(FS.COLUMNS) + " |" in text
    assert "not evidence" in text and "never cited" in text
    assert rows == [] or all(TS.parse_row(r)[0].startswith("x_facing-") for r in rows)
