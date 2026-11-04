"""tools/shot_sheet.py (Plan 27 Task 7a): the visual pass's sheet, on a fabricated run folder and on E20's artifact."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shot_sheet as SS  # noqa: E402

REPO = SS.REPO
sys.path.insert(0, os.path.join(REPO, "testing"))
from agent.base import pza1  # noqa: E402

E20 = os.path.join(REPO, "testing", "artifacts", "e_day_20-20261103-121340")
# the shot numbers of the controller's E20 sheet (Plan 27 workspace, shot-sheet-e20.md): 55 of 95, every 5th
E20_SELECTED = [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65,
                66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
                92, 93, 94, 95]

N_SHOTS = 30
WOUND_SEQ = 50   # the frame whose body.scratched rose
FALL_SEQ = 40    # the frame whose body.health fell, no count rising: no wound (review-t1 minor 3)
KILL_SEQ = 155   # the act that reads targetDead


def _frame(seq, health, zombies=()):
    return pza1.encode("frame", {
        "seq": seq, "tick": seq, "wallMs": 1000 + seq, "gameMin": 560 + seq // 10, "worldAge": 1.5,
        "me": {"x": 10.5, "y": 20.5, "z": 0, "dir": "SE", "moving": True, "running": seq == 60, "sprinting": False,
               "aiming": False, "attackers": 1, "hitReaction": ""},
        "stats": {"endurance": 0.75},
        "body": {"health": health, "scratched": 1 if seq >= WOUND_SEQ else 0, "parts": [{"i": 3, "h": 0}],
                 "armPain": 2.5},
        "zombies": [{"id": 77, "x": 12, "y": 21, "dist": 2.5, "hasTarget": True, "onFloor": False, "health": 1.5},
                    {"id": 78, "x": 30, "y": 31, "dist": 9.0, "hasTarget": False, "onFloor": True, "health": 0.5}]
        if zombies else [],
    })


def _act(seq, dead):
    return pza1.encode("act", {"seq": seq, "tick": seq, "wallMs": 1000 + seq, "aid": "a%d" % seq, "type": "attack",
                               "state": "done", "reason": "", "result": {"targetDead": dead}})


def _make_run(root, state_rel=""):
    """Thirty shots at seq 10n, a frame at each (health 100, then 80 from seq 40; no scratch, then one from seq 50:
    the fall and the rise on different frames), a kill act at seq 155."""
    shots = os.path.join(root, "shots")
    os.makedirs(shots)
    idx = []
    for n in range(1, N_SHOTS + 1):
        idx.append({"n": n, "file": "shot-%04d-%d.jpg" % (n, 10 * n), "seq": 10 * n, "gameMin": 560 + n,
                    "health": 100 if n < 4 else 80, "branch": "threat", "flee": None, "fight": 0, "goal": None,
                    "trigger": "cadence", "decision_line": n})
    idx[2]["skipped"] = "not foreground"          # a skipped shot is not in the sheet
    with open(os.path.join(shots, "shots.jsonl"), "w", encoding="utf-8") as fh:
        for s in idx:
            fh.write(json.dumps(s) + "\n")
    with open(os.path.join(root, "decision.log"), "w", encoding="utf-8") as fh:
        for n in range(1, N_SHOTS + 1):
            fh.write(json.dumps({
                "action": {"type": "steer", "args": {"gait": "run", "vx": 1.0, "vy": 0.0, "seconds": 1.0}},
                "inputs": {"branches": {"threat": {"leg": "approach", "target": 77, "dist": 2.5, "stance": "stand"}}},
            }) + "\n")
    state = os.path.join(root, state_rel)
    os.makedirs(state, exist_ok=True)
    with open(os.path.join(state, "state.log"), "w", encoding="utf-8") as fh:
        for seq in range(10, 10 * N_SHOTS + 1, 10):
            fh.write(_frame(seq, 100 if seq < FALL_SEQ else 80, zombies=(seq == 60,)) + "\n")
            if seq == KILL_SEQ - 5:
                fh.write(_act(KILL_SEQ, True) + "\n")
                fh.write(_act(KILL_SEQ - 1, False) + "\n")
    return root


@pytest.fixture
def run(tmp_path):
    return _make_run(str(tmp_path / "e_day_x-1"))


def test_the_wound_is_the_frame_whose_scratch_count_rose_and_the_kill_the_act_that_reads_target_dead(run):
    """Plan 28 Task 1, 2026-11-04: a WOUND mark is a wound event, no longer a health fall (F11's bleed made 114 of
    131 shots WOUND marks)."""
    r = SS.load_run(run)
    wounds, kills = SS.find_wounds(r.frames), SS.find_kills(r.acts)
    assert wounds == [WOUND_SEQ]
    assert kills == [KILL_SEQ]


def _f(seq, health=100.0, scratched=None, bitten=None, bleeding=None, reaction=None):
    body = {"health": health, "scratched": scratched, "bitten": bitten, "bleeding": bleeding}
    return {"seq": seq, "body": body, "me": None if reaction is None else {"hitReaction": reaction}}


def test_a_wound_is_a_count_rising_or_a_hit_reactions_first_frame_never_a_health_fall_alone():
    """Plan 28 Task 1, 2026-11-04: F11's bleed made 114 of 131 shots WOUND marks, each a frame whose health fell under
    a bleed. A WOUND mark is now a wound event: body.scratched, body.bitten or body.bleeding rising above the last value
    read, or the first frame of a run reading me.hitReaction non-empty (from empty or unread)."""
    frames = [_f(1, 100.0, 0, 0, 0, ""), _f(2, 95.0, 0, 0, 0, ""),          # health fell, no count rose: no mark
              _f(3, 90.0, 1, 0, 0, ""),                                      # scratched rose
              _f(4, 85.0, 1, 0, 1, ""),                                      # bleeding rose
              _f(5, 80.0, 1, 0, 1, ""), _f(6, 75.0, 1, 0, 1, "HitReaction"),  # a hit reaction's first frame
              _f(7, 70.0, 1, 0, 1, "HitReaction"),                           # its second: no mark
              _f(8, 70.0, 1, 1, 1, "HitReaction"),                           # bitten rose under the same run
              _f(9, 65.0, 1, 1, 0, ""), _f(10, 60.0, 1, 1, 1, None),          # me unread; bleeding rose again
              _f(11, 60.0, 0, 1, 1, None), _f(12, 60.0, 1, 1, 1, "")]         # healed then scratched: a rise
    assert SS.find_wounds(frames) == [3, 4, 6, 8, 10, 12]
    assert SS.find_wounds([_f(1, reaction="HitReactionBehind")]) == [1]        # from unread
    assert SS.find_wounds([_f(1, 100.0, 2, 1, 1), _f(2, 50.0)]) == []         # the first counts and an unread body
    assert not hasattr(SS, "HEALTH_EPS")


def test_select_shots_takes_two_each_side_of_the_wound_and_the_kill_the_last_twelve_and_every_nth(run):
    r = SS.load_run(run)
    selected, marks, wounds, kills = SS.select_shots(r, every=50)
    ns = [s["n"] for s in selected]
    # the wound at seq 50 meets shot 5 first; two shots each side in the index without the skipped shot 3
    assert {n for n, m in marks.items() if "WOUND@50" in m} == {2, 4, 5, 6, 7}
    assert {n for n, m in marks.items() if "KILL@155" in m} == {14, 15, 16, 17, 18}
    assert {n for n, m in marks.items() if "DEATH" in m} == set(range(19, 31))
    assert ns == sorted(set([1, 2, 4, 5, 6, 7] + list(range(14, 31))))
    assert (wounds, kills) == ([WOUND_SEQ], [KILL_SEQ])
    assert 3 not in ns          # the skipped shot


def test_every_nth_adds_the_first_and_each_nth_after_it(run):
    r = SS.load_run(run)
    selected, marks, _, _ = SS.select_shots(r, every=5)
    assert {1, 6, 11}.issubset({s["n"] for s in selected})
    assert not {8, 9, 10, 12, 13} & {s["n"] for s in selected}


def test_frame_at_is_the_last_frame_at_or_before_the_seq(run):
    r = SS.load_run(run)
    assert SS.frame_at(r.frames, 55)["seq"] == 50
    assert SS.frame_at(r.frames, 60)["seq"] == 60
    assert SS.frame_at(r.frames, 5) is None


def test_the_sheet_heads_with_the_questions_and_writes_the_marks_and_the_frame_fields(run, tmp_path):
    out = str(tmp_path / "sheet.md")
    summary = SS.write_sheet(SS.load_run(run), out, every=5)
    text = open(out, encoding="utf-8").read()
    assert text.startswith("# Shot sheet: e_day_x-1 (")
    assert text.index("Questions, answered per shot") < text.index("## shot ")
    assert "around 1 wounds, 1 kills, the death, every 5-th" in text
    assert summary["wounds"] == [WOUND_SEQ] and summary["kills"] == [KILL_SEQ]
    sec = text.split("## shot 6  ")[1].split("## shot ")[0]      # shot 6: seq 60, near the wound, a frame with zombies
    assert os.path.join(run, "shots", "shot-0006-60.jpg") in sec
    assert "- marks: WOUND@50" in sec
    assert ("gm 566, health 80, branch threat, flee None, fight 0, goal None, trigger cadence, decision line 6, "
            "seq 60") in sec
    assert 'action steer {"gait": "run", "vx": 1.0, "vy": 0.0}' in sec
    assert "threat leg approach target 77 dist 2.5 stance stand" in sec
    assert ("frame seq 60: dir SE moving True running True sprinting False aiming False attackers 1 "
            "hitReaction ''") in sec
    assert "zombies listed 2, within 3 tiles 1, nearest 77 at 2.5 (hasTarget True, onFloor False, health 1.5)" in sec
    assert "body health 80 parts 1 armPain 2.5 endurance 0.75" in sec
    assert "KILL@155" in text.split("## shot 15  ")[1].split("## shot ")[0]
    assert "- marks: DEATH" in text.split("## shot 30  ")[1]


def test_a_shot_before_the_first_frame_has_empty_frame_fields(run, tmp_path):
    out = str(tmp_path / "sheet.md")
    r = SS.load_run(run)
    r.frames = r.frames[1:]                  # drop the frame at seq 10: shot 1 has none at or before its seq
    SS.write_sheet(r, out, every=5)
    sec = open(out, encoding="utf-8").read().split("## shot 1  ")[1].split("## shot ")[0]
    assert "frame seq None: dir None" in sec and "nearest None at None" in sec


def test_a_run_folder_state_log_is_found_under_the_clients_tree_and_prefers_admin(tmp_path):
    root = _make_run(str(tmp_path / "run"), os.path.join("clients", "admin", "Lua", "pzagent", "admin"))
    other = os.path.join(root, "clients", "bob", "Lua", "pzagent", "bob")
    os.makedirs(other)
    open(os.path.join(other, "state.log"), "w").close()
    assert SS.find_state_dir(root) == os.path.join(root, "clients", "admin", "Lua", "pzagent", "admin")
    assert SS.load_run(root).frames


def test_an_artifact_folder_state_log_beside_the_json_is_found(run):
    assert SS.find_state_dir(run) == run


def test_rotations_and_chunks_are_read_beside_the_live_log(tmp_path):
    root = _make_run(str(tmp_path / "rot"))
    live = os.path.join(root, "state.log")
    lines = open(live, encoding="utf-8").read().splitlines()
    open(os.path.join(root, "state.1.log"), "w", encoding="utf-8").write("\n".join(lines[:12]) + "\n")
    open(live, "w", encoding="utf-8").write("\n".join(lines[12:]) + "\n")
    assert [f["seq"] for f in SS.load_run(root).frames] == list(range(10, 10 * N_SHOTS + 1, 10))


def test_a_missing_index_or_decision_log_or_state_log_is_a_clear_error(tmp_path):
    root = _make_run(str(tmp_path / "r"))
    os.remove(os.path.join(root, "shots", "shots.jsonl"))
    with pytest.raises(SS.SheetError, match="shots.jsonl"):
        SS.load_run(root)
    root = _make_run(str(tmp_path / "r2"))
    os.remove(os.path.join(root, "decision.log"))
    with pytest.raises(SS.SheetError, match="decision.log"):
        SS.load_run(root)
    root = _make_run(str(tmp_path / "r3"))
    os.remove(os.path.join(root, "state.log"))
    with pytest.raises(SS.SheetError, match="state"):
        SS.load_run(root)


def test_main_exits_2_on_a_sheet_error_and_0_otherwise(run, tmp_path, capsys):
    out = str(tmp_path / "o.md")
    assert SS.main([run, out, "--every", "7"]) == 0
    assert "every 7-th" in open(out, encoding="utf-8").read()
    assert SS.main([str(tmp_path / "nothing"), out]) == 2
    assert "shot_sheet:" in capsys.readouterr().err


@pytest.mark.skipif(not os.path.isdir(E20), reason="the E20 artifact is not checked out")
def test_e20_selection_reproduces_the_controllers_sheet(tmp_path):
    """Plan 28 Task 1, 2026-11-04: under the wound-event rule E20 reads 9 wounds where the health-fall rule read 43;
    the selection is the controller's sheet's all the same (the shots around the nine fall in the same windows)."""
    r = SS.load_run(E20)
    selected, marks, wounds, kills = SS.select_shots(r, every=5)
    assert len(r.shots) == 95
    assert [s["n"] for s in selected] == E20_SELECTED
    assert (len(selected), len(wounds), len(kills)) == (55, 9, 7)
    assert wounds == [6379, 6447, 6475, 6503, 6504, 6531, 6532, 6559, 6560]
