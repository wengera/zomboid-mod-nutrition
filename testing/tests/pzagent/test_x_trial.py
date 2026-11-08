"""drivers/x_trial.py and driverlib/trial.py (Plan 31 Task 6, the generic trial driver, ruling P31-T), offline: the
driver is never invoked, the game never boots, the `claude` CLI is never called.

The static tests read the driver's refusal (its order before `main` and `parse_argv` over bad and good argvs), its
constants and its imports. The pre-boot checks run against the real profile and throwaway fixture records (conftest's
`agent_fixture`), every machine reading injected. The boot (`trial.boot_and_run`) runs whole on a real run layout
(`pzt.paths.RUNS` pointed into tmp, the run dir made by `new_run_dir`) with `_dlib.boot`, the teardown and the kill
injected: the fake boot starts DayMod (test_e_day_24.py's, trimmed, its position moved by the teleport) under a
FakeServer whose `rcon` is the fake RCON (every command recorded in order) and FakeBus's replies; the session is the
library's `run_session` on the fake clock with InlinePolls (test_e_day_24.py's), so the loop stays single-threaded
but for the wave thread under test. `Survive` is wrapped so the `control=` keyword is recorded and passed on only
when Plan 31 Task 1's fork is on the tree."""
import inspect
import json
import os
import re
import types

import pytest

from agent.base.planner import survive as SV
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.llm import LLMSource
from agent.base.planner.survive import Survive
from agent.driverlib import chain as CH
from agent.driverlib import day as DY
from agent.driverlib import polls as P
from agent.driverlib import session as S
from agent.driverlib import trial as TR
from agent.drivers import x_trial as XT
from .fakemod import DEFAULT_FRAME, FakeMod

REPO = S.REPO
X = S.X
KIT = S.DEFAULTS["KIT"]
KIT_ID = 5001
BAT = {"itemId": KIT_ID, "fullType": KIT, "weight": 1.5, "use": "weapon"}
FORK = "control" in inspect.signature(Survive.__init__).parameters     # Plan 31 Task 1's fork on this tree
ME = XT.__file__


# ================================================================ static: the refusal, the constants, the imports
def test_the_driver_refuses_arguments_before_main():
    src = open(ME, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]), sys.argv[1:])")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert XT.parse_argv is TR.parse_argv and XT.flags is TR.flags
    base = ["--variant", "ladder", "--fixture", "agent"]
    for bad in ([], ["x"], ["--help"], ["--variant", "ladder"], ["--fixture", "agent"], ["--variant"],
                base + ["--variant", "doctrine"], base + ["--no-llm", "--no-llm"], base + ["--no-llm", "x"],
                base + ["--session", "1"], base + ["--prev", "a.json"], base + ["--minutes"],
                base + ["--minutes", "0"], base + ["--minutes", "-1"], base + ["--minutes", "five"],
                base + ["--minutes", "nan"], base + ["--minutes", "inf"], base + ["--waves", "horde"],
                base + ["--teleport", "10750"], base + ["--teleport", "10750,10620,0"], base + ["--teleport", "a,b"],
                base + ["--make-fixture", "agent"], base + ["--make-fixture", "arena-east", "--waves", "lone"],
                base + ["--make-fixture", "arena-east", "--waves", "pair"], base + ["--make-fixture", "../x"],
                ["--variant", "Ladder", "--fixture", "agent"], ["--variant", "a-b", "--fixture", "agent"],
                ["--variant", "ladder", "--fixture", "../agent"], base + ["--waves", "lone", "x"],
                base + ["--minutes", "6"], base + ["--minutes", "6", "--no-llm"], base + ["--detached", "--detached"],
                base + ["--detached", "x"], base + ["--minutes", "61", "--detached"],
                base + ["--make-fixture", "arena-east"],           # 688 s: five minutes, the model and the snapshot
                base + ["--goals"], base + ["--goals", "wander"], base + ["--goals", "hold"],      # hold: no model
                base + ["--goals", "hold", "--goals", "hold", "--no-llm"],
                base + ["--no-llm", "--goals", "Hold"], base + ["--no-llm", "--goals", "scripted", "--goals", "hold"]):
        r = XT.parse_argv(bad, ME)
        assert r and "x_trial.py" in r and "\n" not in r, bad
    for good in (base, base + ["--minutes", "5"], base + ["--minutes", "0.5"], base + ["--no-llm"],
                 ["--no-llm"] + base, base + ["--waves", "lone"], base + ["--waves", "pair"],
                 base + ["--waves", "street"], base + ["--teleport", "10750,10620"],
                 base + ["--teleport", "10750.5,-3"],
                 base + ["--make-fixture", "arena-east", "--no-llm", "--minutes", "1"],
                 base + ["--teleport", "10750,10620", "--make-fixture", "arena-east", "--waves", "street",
                         "--minutes", "1", "--no-llm"], base + ["--detached"],
                 base + ["--minutes", "6", "--detached"], base + ["--minutes", "60", "--detached", "--no-llm"],
                 base + ["--goals", "scripted"], base + ["--no-llm", "--goals", "scripted"],
                 base + ["--no-llm", "--goals", "hold"], ["--goals", "hold", "--no-llm"] + base,
                 base + ["--no-llm", "--goals", "hold", "--waves", "lone", "--teleport", "10750,10620"]):
        assert XT.parse_argv(good, ME) is None, good
    assert XT.flags(base) == {"variant": "ladder", "fixture": "agent", "minutes": 5, "no_llm": False,
                              "goals": "scripted", "waves": "street", "teleport": None, "make_fixture": None,
                              "detached": False}
    assert XT.flags(base + ["--no-llm", "--goals", "hold"])["goals"] == "hold"
    assert XT.flags(base + ["--no-llm", "--goals", "hold"])["no_llm"] is True
    assert XT.flags(base + ["--minutes", "0.5", "--no-llm", "--waves", "pair", "--teleport", "10750,10620.5",
                            "--make-fixture", "arena-east", "--detached"]) == {
        "variant": "ladder", "fixture": "agent", "minutes": 0.5, "no_llm": True, "goals": "scripted",
        "waves": "pair", "teleport": [10750, 10620.5], "make_fixture": "arena-east", "detached": True}


def test_the_refusal_names_why():
    r = XT.parse_argv(["--variant", "ladder", "--fixture", "agent", "--make-fixture", "a", "--waves", "lone"], ME)
    assert r.startswith("x_trial.py takes only --variant <name> --fixture <name> [--minutes N] [--no-llm] "
                        "[--goals scripted|hold] [--waves lone|pair|street] [--teleport X,Y] "
                        "[--make-fixture <name>] [--detached]; refused: ")
    assert "spawned zombies into the fixture" in r
    assert "(missing --fixture)" in XT.parse_argv(["--variant", "ladder"], ME)
    base = ["--variant", "ladder", "--fixture", "agent"]
    r = XT.parse_argv(base + ["--goals", "hold"], ME)
    assert r.startswith("x_trial.py takes only ") and r.endswith(
        "(--goals hold holds the square with no model: pass --no-llm)")
    assert XT.parse_argv(base + ["--goals", "wander"], ME).endswith("(--goals takes one of scripted, hold)")
    r = XT.parse_argv(["--variant", "ladder", "--fixture", "agent", "--minutes", "6"], ME)
    assert r.endswith("(the wall bound 628 s passes the foreground cap 570 s: pass --detached (the controller "
                      "launches it detached after Angus approves))")


# ================================================================ the wall-time bound
def test_the_wall_bound_sums_every_wait_and_the_default_fits_the_foreground_cap():
    base = ["--variant", "ladder", "--fixture", "agent"]
    w = TR.wall_bound(XT.flags(base))
    assert w["parts"] == {"preboot": 15.0, "budget": 410.0, "stop_settle": 2.0, "polls_join": 35.0,
                          "wave_join": 6.0, "teardown": 75.0, "llm_join": 25.0, "snapshot": 0.0}
    assert w["total_s"] == 568.0 and w["total_s"] <= TR.FOREGROUND_CAP_S == 570.0 and w["launch"] == "foreground"
    # each part off its owner: the budget's extra, the library's settle and joins, bounded_teardown's two waits
    assert TR.BUDGET_EXTRA_S == 110.0 and TR.TEARDOWN_S == TR.B.TEARDOWN_QUIT_S + TR.B.TEARDOWN_STOP_S == 75
    assert TR.POLLS_JOIN_S == max(S.STEP_TIMEOUT_S, S.DEFAULTS["SERVER_TIMEOUT_S"]) + 5 and S.STOP_SETTLE_S == 2.0
    assert TR.LLM_JOIN_S == TR.L.LLM_TIMEOUT_S + 5 and TR.WAVE_JOIN_S == 6.0
    assert TR.wall_bound(XT.flags(base + ["--no-llm"]))["total_s"] == 543.0
    six = TR.wall_bound(XT.flags(base + ["--minutes", "6"]))
    assert six["total_s"] == 628.0 and six["launch"] == "detached"
    snap = TR.wall_bound(XT.flags(base + ["--minutes", "1", "--no-llm", "--teleport", "1,2", "--make-fixture", "a1"]))
    assert snap["parts"]["snapshot"] == 120.0 and snap["total_s"] == 15 + 170 + 2 + 35 + 6 + 75 + 120
    line = TR.bound_line(XT.flags(base))
    assert line == ("x_trial wall bound 568 s (preboot 15 + budget 410 + stop_settle 2 + polls_join 35 + wave_join 6 "
                    "+ teardown 75 + llm_join 25): foreground: under the 570 s cap")
    assert TR.bound_line(XT.flags(base + ["--minutes", "6", "--detached"])).endswith(
        "detached: past the ten-minute cap, the controller launches it after Angus approves")


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(ME) == XT.DRIVER == XT.KEY + ".py" == "x_trial.py"
    assert (XT.KEY, XT.PROFILE, XT.ARTIFACT) == ("x_trial", "testing/profiles/agent.toml", "x_trial.json")
    assert os.path.isfile(os.path.join(REPO, XT.PROFILE))
    assert TR.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"] == 10.0
    assert TR.DEFAULT_MINUTES == 5 and TR.DEFAULT_WAVES == "street" and TR.USER == "admin"
    src = open(ME, encoding="utf-8").read()
    assert ("TR.boot_and_run(args, lambda: TR.preboot(args, PROFILE), key=KEY, driver=DRIVER, artifact=ARTIFACT,"
            in src)
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    assert "import xlib as X" in imports and "from agent.driverlib import trial as TR" in imports
    assert not [l for l in imports if "drivers" in l or re.search(r"\b(e_day|f_goals)_\d+", l)], imports


def test_the_trial_library_never_copies_into_the_artifacts_nor_prints_next_steps():
    """No auto-copy (the code, past the docstring, calls none of copy_run, copy_artifacts, copy_state_logs,
    copy_shots_index or next_steps) and no grade."""
    import ast
    tree = ast.parse(open(TR.__file__, encoding="utf-8").read())
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and id(n) not in docs]
    for name in ("copy_run", "copy_artifacts", "copy_state_logs", "copy_shots_index", "next_steps", "grade",
                 "grade_fn", "driver_checks"):
        assert name not in names, name
    assert not [s for s in strings if "artifacts" in s], strings


def test_the_rcon_forms_live_in_one_constant_each():
    assert TR.TELEPORT_CMD.format(user="admin", x=10750, y=10620, z=0) == 'teleportto "admin" 10750,10620,0'
    assert TR.TELEPORT_TAG == "setup_tp"
    assert TR.CREATEHORDE2_CMD.format(x=108, y=200, z=0, count=1, radius=1) == (
        "createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1")
    src = open(TR.__file__, encoding="utf-8").read()
    assert src.count("teleportto ") == 1 and src.count("createhorde2 -x") == 1


# ================================================================ the waves
def test_the_wave_square_is_the_position_plus_the_distance_at_the_bearing():
    assert TR.wave_square((100.0, 200.0), 8.0, 0.0) == (108, 200)
    assert TR.wave_square((100.0, 200.0), 8.0, 90.0) == (100, 208)
    assert TR.wave_square((100.0, 200.0), 8.0, 180.0) == (92, 200)
    assert TR.wave_square((100.0, 200.0), 8.0, -90.0) == (100, 192)
    # 35 degrees: 8 cos 35 = 6.553, 8 sin 35 = 4.589; the square is the floor of the point
    assert TR.wave_square((100.5, 200.5), 8.0, 35.0) == (107, 205)
    assert TR.wave_square((100.5, 200.5), 8.0, -35.0) == (107, 195)
    assert TR.wave_square((10764.2, 10617.9), 15.0, 45.0) == (10774, 10628)


def test_the_plans_spawn_as_named():
    assert TR.WAVE_PLANS["lone"] == {"period_s": 60.0, "spawns": ((1, 8.0, 0.0),)}
    pair = TR.WAVE_PLANS["pair"]
    assert pair["period_s"] == 90.0 and [s[:2] for s in pair["spawns"]] == [(1, 8.0), (1, 8.0)]
    assert abs(pair["spawns"][1][2] - pair["spawns"][0][2]) == 70.0
    assert TR.WAVE_PLANS["street"] == {"period_s": None, "spawns": ()}


def _waves(plan, pos=(100.0, 200.0)):
    sent = []
    w = TR.Waves(plan, lambda cmd, tag: sent.append((cmd, tag)) or {"ok": True, "reply": "ok"}, lambda: pos)
    return w, sent


def test_lone_fires_one_zombie_at_8_tiles_at_the_start_then_every_60_s():
    w, sent = _waves("lone")
    w.begin(1000.0)
    assert len(w.step(1000.0)) == 1
    assert sent == [("createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1", "wave_0_0")]
    assert w.step(1000.0) == [] and w.step(1059.9) == []
    assert len(w.step(1060.0)) == 1 and w.step(1061.0) == [] and len(w.step(1120.5)) == 1
    assert [t for _, t in sent] == ["wave_0_0", "wave_1_0", "wave_2_0"]
    r = w.rows
    assert [x["t"] for x in r] == [0.0, 60.0, 120.5] and r[2]["lateS"] == 0.5 and r[2]["missed"] == 0
    assert r[0]["from"] == [100.0, 200.0] and r[0]["at"] == [108, 200, 0]
    assert r[0]["ack"] == {"ok": True, "reply": "ok"}
    # a late pass fires the latest boundary's wave, never the missed ones in a burst, and the next is the next boundary
    assert len(w.step(1310.0)) == 1 and w.rows[-1]["wave"] == 5 and w.rows[-1]["lateS"] == 10.0
    assert w.rows[-1]["missed"] == 2                                       # waves 3 and 4 skipped
    assert w.step(1359.0) == [] and len(w.step(1360.0)) == 1 and w.rows[-1]["wave"] == 6


def test_pair_fires_two_at_8_tiles_70_degrees_apart_every_90_s():
    w, sent = _waves("pair")
    w.begin(0.0)
    assert len(w.step(0.0)) == 2
    assert sent == [("createhorde2 -x 106 -y 195 -z 0 -count 1 -radius 1", "wave_0_0"),
                    ("createhorde2 -x 106 -y 204 -z 0 -count 1 -radius 1", "wave_0_1")]
    assert w.step(89.0) == [] and len(w.step(90.0)) == 2 and w.step(170.0) == [] and len(w.step(180.0)) == 2
    assert [r["bearing"] for r in w.rows[:2]] == [-35.0, 35.0]


def test_street_spawns_nothing_and_starts_no_thread():
    w, sent = _waves("street")
    w.start()
    assert w.started is True and w._thread is None and w.step(1e9) == [] and sent == []
    w.stop()
    assert w.record() == {"plan": "street", "period_s": None, "spawns": [], "started": True, "rows": [],
                          "error": None, "joined": None, "confirm": [], "by_wave": [], "server_spawns": None}


def _confirming(plan, seen, pos=(100.0, 200.0)):
    """Waves over a fake RCON and a `seen` dict {zombie id: (x, y) of its first listing}: the lone wave's square is
    (108, 200), centre (108.5, 200.5); the pair's are (106, 195) at -35 degrees and (106, 204) at 35."""
    sent = []
    w = TR.Waves(plan, lambda cmd, tag: sent.append(tag) or {"ok": True}, lambda: pos, listed=lambda: seen)
    return w, sent


NEAR = (108.4, 200.6)         # a zombie first listed at the lone wave's square
FAR = (60.0, 140.0)           # a natural walker first listed 60 tiles off


def test_a_wave_its_frames_never_list_is_re_sent_once_after_the_confirm_window():
    """Task 12's loop fix (trial 1: the server spawned six, the frames listed three): no zombie first listed at the
    spawn's square WAVE_CONFIRM_S after the send re-sends the spawn once, its own confirmation recorded and never
    re-sent; a natural walker already listed (7) confirms nothing."""
    seen = {7: FAR}
    w, sent = _confirming("lone", seen)
    w.begin(0.0)
    assert len(w.step(0.0)) == 1 and sent == ["wave_0_0"] and TR.WAVE_CONFIRM_S == 8.0 and TR.WAVE_CONFIRM_R == 2.0
    assert w.step(7.9) == [] and sent == ["wave_0_0"]
    rows = w.step(8.0)
    assert sent == ["wave_0_0", "wave_0_0_resend"] and len(rows) == 1 and rows[0]["resend_of"] == 0
    assert rows[0]["wave"] == 0 and rows[0]["cmd"] == "createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1"
    assert w.confirms == [{"wave": 0, "spawn": 0, "resend": False, "need": 1, "listed_ids": [], "t": 8.0, "resent": 1}]
    assert w.step(16.0) == [] and sent == ["wave_0_0", "wave_0_0_resend"]           # the re-send is never re-sent
    assert w.confirms[-1] == {"wave": 0, "spawn": 0, "resend": True, "need": 1, "listed_ids": [], "t": 16.0}
    assert w.by_wave[0] == {"wave": 0, "sent": 1, "resent": 1, "listed_ids": [], "confirmed": False}
    assert len(w.step(60.0)) == 1 and sent[-1] == "wave_1_0"
    seen[9] = NEAR                                                                   # wave 1's zombie read after its send
    assert w.step(68.0) == []
    assert w.confirms[-1] == {"wave": 1, "spawn": 0, "resend": False, "need": 1, "listed_ids": [9], "t": 68.0}
    assert w.by_wave[1] == {"wave": 1, "sent": 1, "resent": 0, "listed_ids": [9], "confirmed": True}


def test_a_wave_read_by_the_frames_is_confirmed_and_never_re_sent():
    seen = {7: FAR}
    w, sent = _confirming("lone", seen)
    w.begin(0.0)
    w.step(0.0)
    seen[11] = NEAR                                                                  # the frames list the spawn
    assert w.step(8.0) == [] and sent == ["wave_0_0"]
    assert w.confirms == [{"wave": 0, "spawn": 0, "resend": False, "need": 1, "listed_ids": [11], "t": 8.0}]
    rec = w.record()
    assert rec["confirm"] == w.confirms and "resend_of" not in w.rows[0]
    assert rec["by_wave"] == [{"wave": 0, "sent": 1, "resent": 0, "listed_ids": [11], "confirmed": True}]


def test_a_natural_walkers_id_confirms_nothing():
    """Round one's re-send counted any new id (trial 5: 11 spawns logged against 8 planned, three ids never listed):
    a walker first listed after the send but far from the square, one already listed before the send beside it, and
    one first listed within the radius but just past it (2.6 tiles) confirm nothing, so the spawn is re-sent; a
    zombie first listed 1.4 tiles from the square's centre after the send confirms it."""
    seen = {7: NEAR}                                                  # listed before the send, standing at its square
    w, sent = _confirming("lone", seen)
    w.begin(0.0)
    w.step(0.0)
    seen[8] = FAR                                                     # a new id, far
    seen[10] = (108.5 + 2.6, 200.5)                                   # a new id, just past WAVE_CONFIRM_R
    seen[12] = None                                                   # a new id with no position
    rows = w.step(8.0)
    assert [r["resend_of"] for r in rows] == [0] and w.confirms[0]["listed_ids"] == []
    assert w.confirms[0]["resent"] == 1
    seen[13] = (108.5 + 1.0, 200.5 + 1.0)                             # 1.41 tiles from the centre
    assert w.step(16.0) == [] and w.confirms[1]["listed_ids"] == [13]
    assert w.by_wave[0] == {"wave": 0, "sent": 1, "resent": 1, "listed_ids": [13], "confirmed": True}


def test_a_pair_short_of_one_re_sends_the_missing_spawn_at_its_own_bearing():
    """The pair's two squares are (106, 195) and (106, 204): with the second's zombie listed the first spawn alone is
    re-sent at its bearing (-35), and with the first's listed the second alone at 35 (round one's re-send repeated the
    plan's first N spawns, so a missing second spawn was sent at the first's bearing)."""
    seen = {}
    w, sent = _confirming("pair", seen)
    w.begin(0.0)
    assert len(w.step(0.0)) == 2
    seen[5] = (106.4, 204.5)                                         # spawn 1's zombie read
    rows = w.step(8.0)
    assert [r["spawn"] for r in rows] == [0] and sent == ["wave_0_0", "wave_0_1", "wave_0_0_resend"]
    assert rows[0]["cmd"] == "createhorde2 -x 106 -y 195 -z 0 -count 1 -radius 1" and rows[0]["bearing"] == -35.0
    assert [(c["spawn"], c["listed_ids"], c.get("resent")) for c in w.confirms] == [(0, [], 1), (1, [5], None)]
    assert w.by_wave[0] == {"wave": 0, "sent": 2, "resent": 1, "listed_ids": [5], "confirmed": False}
    seen = {}
    w, sent = _confirming("pair", seen)
    w.begin(0.0)
    w.step(0.0)
    seen[6] = (106.6, 195.5)                                         # spawn 0's zombie read
    rows = w.step(8.0)
    assert [r["spawn"] for r in rows] == [1] and sent == ["wave_0_0", "wave_0_1", "wave_0_1_resend"]
    assert rows[0]["cmd"] == "createhorde2 -x 106 -y 204 -z 0 -count 1 -radius 1" and rows[0]["bearing"] == 35.0


def test_a_spawn_of_three_short_of_two_re_sends_the_missing_two(monkeypatch):
    monkeypatch.setitem(TR.WAVE_PLANS, "trio", {"period_s": 60.0, "spawns": ((3, 8.0, 0.0),)})
    seen = {}
    w, sent = _confirming("trio", seen)
    w.begin(0.0)
    w.step(0.0)
    seen[3] = NEAR
    rows = w.step(8.0)
    assert rows[0]["cmd"] == "createhorde2 -x 108 -y 200 -z 0 -count 2 -radius 1" and rows[0]["count"] == 2
    assert w.by_wave[0] == {"wave": 0, "sent": 3, "resent": 2, "listed_ids": [3], "confirmed": False}


def test_waves_without_a_listing_never_confirm():
    w, sent = _waves("lone")
    w.begin(0.0)
    w.step(0.0)
    assert w.pending == [] and w.step(30.0) == [] and w.confirms == [] and sent == [("createhorde2 -x 108 -y 200 -z 0 "
                                                                                         "-count 1 -radius 1", "wave_0_0")]


def test_the_trial_chain_collects_every_listed_id_with_its_first_position_for_the_waves(tmp_path):
    c, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--waves", "lone"])
    assert c.first_seen == {} and c.waves.listed() == {}
    c.on_frame({"me": {"x": 1.0, "y": 2.0, "z": 0}, "zombies": [{"id": 4, "x": 5.5, "y": 6.5}, {"id": 6}]})
    c.on_frame({"me": {"x": 1.0, "y": 2.0, "z": 0}, "zombies": [
        {"id": 6, "x": 9.0, "y": 9.0}, {"id": 8, "x": 7.0, "y": 8.0}, "junk", {"id": None}, {"id": 4, "x": 0.0, "y": 0.0}]})
    # the first listing's position stays: 4's (5.5, 6.5), 6's none (the first frame carried no square), 8's (7.0, 8.0)
    assert c.waves.listed() == {4: (5.5, 6.5), 6: None, 8: (7.0, 8.0)}


def test_the_servers_spawn_lines_are_counted_from_its_log_into_the_waves_record(tmp_path):
    """The count of CreateHorde2Command's "Spawning" lines (one per zombie), the sample's own line shape; none without
    the log, and nothing noted without a wave record."""
    line = ("WARN : General      f:421 st:4,276,448,296 at CreateHorde2Command.Command         > Spawning new Male Zed, "
            "Dressed in No Outfit, isFallOnFront:false\n")
    other = "LOG  : General      f:533 st:4,276,459,389> ItemPickInfo -> Spawning new thing elsewhere\n"
    (tmp_path / TR.SERVER_LOG).write_text(line + other + line + line, encoding="utf-8")
    assert TR.server_spawns(str(tmp_path)) == 3
    out = {"loop": {"trial": {"waves": {"plan": "lone", "server_spawns": None}}}}
    assert TR.note_server_spawns(out, str(tmp_path)) == 3 and out["loop"]["trial"]["waves"]["server_spawns"] == 3
    empty = tmp_path / "empty"
    empty.mkdir()
    assert TR.server_spawns(str(empty)) is None
    assert TR.note_server_spawns(out, str(empty)) is None and out["loop"]["trial"]["waves"]["server_spawns"] is None
    assert TR.note_server_spawns({}, str(tmp_path)) is None and TR.note_server_spawns({"loop": {}}, str(tmp_path)) is None


def test_a_wave_spawns_on_the_characters_floor():
    w, sent = _waves("lone", pos=(100.0, 200.0, 1))
    w.begin(0.0)
    w.step(0.0)
    assert sent == [("createhorde2 -x 108 -y 200 -z 1 -count 1 -radius 1", "wave_0_0")]
    w, sent = _waves("lone", pos=(100.0, 200.0, None))
    w.begin(0.0)
    w.step(0.0)
    assert sent[0][0].endswith("-z 0 -count 1 -radius 1")


def test_a_wave_without_a_frame_position_is_recorded_skipped():
    w, sent = _waves("lone", pos=None)
    w.begin(0.0)
    rows = w.step(0.0)
    assert sent == [] and rows[0]["skipped"] == "no frame position" and rows[0]["cmd"] is None


def test_the_wave_thread_fires_the_first_wave_at_once_and_stops_on_its_join():
    sent = []
    w = TR.Waves("lone", lambda cmd, tag: sent.append(tag) or {"ok": True}, lambda: (1.0, 2.0), poll_s=0.01)
    w.start()
    for _ in range(500):
        if sent:
            break
        import time
        time.sleep(0.01)
    w.stop()
    assert sent == ["wave_0_0"] and w.joined is True and w.error is None and not w._thread.is_alive()


def test_a_wave_fault_ends_the_waves_never_the_loop():
    def boom(cmd, tag):
        raise RuntimeError("socket")
    w = TR.Waves("lone", boom, lambda: (1.0, 2.0), poll_s=0.01)
    w.start()
    w._thread.join(5)
    w.stop()
    assert w.error == "RuntimeError: socket" and w.joined is True


# ================================================================ provenance, trial.json, the switches
def test_provenance_reads_the_snapshot_stamp_when_present(tmp_path):
    stamp = {"commit": "a" * 40, "dirty": True, "diff_sha256": "b" * 64, "made_at": "2026-11-05T18:00:00"}
    (tmp_path / TR.STAMP).write_text(json.dumps(stamp), encoding="utf-8")

    def no_git(*a):
        raise AssertionError("git is never asked beside a stamp")
    p = TR.provenance(str(tmp_path), git=no_git)
    assert p == {"commit": "a" * 40, "stamp": stamp, "dirty": True, "diff_sha256": "b" * 64, "untracked": None,
                 "provenance": "stamp", "diff": None}
    (tmp_path / TR.STAMP).write_text("{nope", encoding="utf-8")
    p = TR.provenance(str(tmp_path), git=no_git)
    assert p["provenance"] == "stamp" and p["commit"] is None and "error" in p["stamp"]


def test_provenance_reads_git_over_the_sessions_paths_without_a_stamp(tmp_path):
    asked = []

    def git(repo, *args):
        asked.append(args)
        if args[0] == "rev-parse":
            return 0, b"c" * 40 + b"\n"
        if args[0] == "status":
            return 0, b" M testing/agent/base/planner/survive.py\n"
        if args[0] == "ls-files":
            return 0, b""
        return 0, b"diff --git a/x b/x\n+1\n"
    p = TR.provenance(str(tmp_path), git=git)
    import hashlib
    assert p["commit"] == "c" * 40 and p["dirty"] is True and p["provenance"] == "git" and p["stamp"] is None
    assert p["diff"] == "diff --git a/x b/x\n+1\n" and p["untracked"] == []
    assert p["diff_sha256"] == hashlib.sha256(b"diff --git a/x b/x\n+1\n").hexdigest()
    assert asked[1] == ("status", "--porcelain", "--") + TR.SESSION_PATHS
    assert asked[2] == ("diff", "HEAD", "--") + TR.SESSION_PATHS
    assert asked[3] == ("ls-files", "-o", "--exclude-standard", "-z", "--") + TR.SESSION_PATHS
    clean = TR.provenance(str(tmp_path), git=lambda repo, *a: (0, b"d" * 40) if a[0] == "rev-parse" else (0, b""))
    assert clean["dirty"] is False and clean["diff"] is None and clean["diff_sha256"] is None
    assert clean["untracked"] is None
    broken = TR.provenance(str(tmp_path), git=lambda repo, *a: (128, b""))
    assert broken["commit"] is None and broken["dirty"] is None


def test_an_uncommitted_variant_package_lands_in_the_diff_and_its_hash(tmp_path):
    """The untracked files under SESSION_PATHS (a new planner package nobody committed yet) are appended to the diff
    in their named blocks and hashed with it; a file not under the paths is never read."""
    import hashlib
    pkg = tmp_path / "testing" / "agent" / "base" / "planner" / "doctrine"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_bytes(b"CONTROL = 1\n")
    (pkg / "assess.py").write_bytes(b"def assess(s, f):\n    return None")          # no final newline
    tracked = b"diff --git a/testing/agent/x.py b/testing/agent/x.py\n+1\n"

    def git(repo, *args):
        assert repo == str(tmp_path)
        if args[0] == "rev-parse":
            return 0, b"c" * 40
        if args[0] == "status":
            return 0, b"?? testing/agent/base/planner/doctrine/\n"
        if args[0] == "ls-files":
            assert args[-len(TR.SESSION_PATHS):] == TR.SESSION_PATHS
            return 0, (b"testing/agent/base/planner/doctrine/assess.py\0"
                       b"testing/agent/base/planner/doctrine/__init__.py\0")
        return 0, tracked
    p = TR.provenance(str(tmp_path), git=git)
    a, i = b"def assess(s, f):\n    return None", b"CONTROL = 1\n"
    want = (tracked
            + (TR.UNTRACKED_HEAD % ("testing/agent/base/planner/doctrine/__init__.py",
                                    hashlib.sha256(i).hexdigest(), len(i))).encode() + i
            + (TR.UNTRACKED_HEAD % ("testing/agent/base/planner/doctrine/assess.py",
                                    hashlib.sha256(a).hexdigest(), len(a))).encode() + a + b"\n")
    assert p["dirty"] is True and p["untracked"] == ["testing/agent/base/planner/doctrine/__init__.py",
                                                     "testing/agent/base/planner/doctrine/assess.py"]
    assert p["diff"] == want.decode() and p["diff_sha256"] == hashlib.sha256(want).hexdigest()
    # an edit of the untracked file moves the hash: the run is tied to the bytes that ran
    (pkg / "assess.py").write_bytes(b"def assess(s, f):\n    return 1")
    assert TR.provenance(str(tmp_path), git=git)["diff_sha256"] != p["diff_sha256"]


def _git_answers(repo):
    import subprocess
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True).returncode == 0
    except OSError:
        return False


@pytest.mark.skipif(not _git_answers(REPO) and not os.path.isfile(os.path.join(REPO, TR.STAMP)),
                    reason="a tree with neither git nor a TRIAL_STAMP.json (a bare archive): provenance records None")
def test_provenance_on_this_tree_names_its_head():
    p = TR.provenance(REPO)
    if p["provenance"] == "git":
        assert p["commit"] and re.match(r"^[0-9a-f]{40}$", p["commit"]) and p["dirty"] in (True, False)
    else:
        assert p["stamp"] is not None


def test_the_switches_are_every_t_tuple_read_off_the_planner():
    sv = types.SimpleNamespace(CORNER_BREAK=False, SWING_CLOSE=True)
    sw = TR.switches(sv)
    names = [n for k in sorted((int(m.group(1)), k) for k in dir(SV) for m in [TR.SWITCH_RX.match(k)] if m)
             for n in getattr(SV, k[1])] + list(TR.EXTRA_SWITCHES)
    assert list(sw) == names and names[0] == "CORNER_BREAK" and "SWING_CLOSE" in names
    assert sw["CORNER_BREAK"] is False and sw["SWING_CLOSE"] is True and sw["DOOR_HELD"] is None
    assert names[-1] == "DRESS_MANEUVER" and sw["DRESS_MANEUVER"] is None


# ================================================================ pre-boot
class Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


CONTROL = types.SimpleNamespace(CONTROLS=("ladder",), load=lambda name: (_ for _ in ()).throw(
    ValueError("unknown control %r" % name)))      # planner/control.py's shape (Plan 31 Task 1): CONTROLS, load


class Forked:
    """A Survive stand-in whose constructor takes the fork's keyword (variant_check reads only the signature)."""

    def __init__(self, world, actions, log_path, clock=None, source=None, control="ladder"):
        pass


def _preboot(monkeypatch, args, **kw):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok  PZ java processes: none"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    kw.setdefault("free", lambda: 15.0)
    kw.setdefault("java_pids", lambda: [])
    kw.setdefault("survive", Forked)
    kw.setdefault("control", CONTROL)
    return TR.preboot(args, XT.PROFILE, **kw)


def _no_cli(*a, **k):
    raise AssertionError("the claude CLI is never called under --no-llm")


def test_preboot_on_the_real_profile_without_the_model_never_probes(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    pre, ok = _preboot(monkeypatch, args, which=_no_cli, run=_no_cli)
    assert ok, pre
    assert pre["checks"] == {"profile_exists": True, "doctor_clean": True, "lint_clean": True, "memory": True,
                             "no_game_java": True, "fixture_ok": True, "variant_ok": True}
    assert pre["profile"] == "agent" and pre["free_gb"] == 15.0 and pre["java_pids"] == []
    assert pre["claude_available"]["error"] == "not probed: --no-llm" and pre["claude_version"] is None
    assert pre["claude_answers"]["ok"] is None and pre["claude_answers"]["error"] == "not probed: --no-llm"
    assert pre["variant"] == {"variant": "ladder", "fork": True, "ok": True, "error": None}


def test_preboot_with_the_model_probes_once_and_refuses_on_a_failed_probe(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent"])
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        if argv[-1] == "--version":
            return Proc("2.1.310 (Claude Code)\n")
        return Proc(json.dumps({"type": "result", "is_error": False, "result": "ok"}))
    pre, ok = _preboot(monkeypatch, args, which=lambda n: "C:/bin/claude.exe", run=run)
    assert ok, pre
    assert len(calls) == 2 and calls[0] == ["C:/bin/claude.exe", "--version"] and "-p" in calls[1]
    assert pre["checks"]["claude_ok"] is True and pre["claude_answers"]["ok"] is True
    assert pre["claude_version"] == "2.1.310 (Claude Code)"

    def limited(argv, **kw):
        if argv[-1] == "--version":
            return Proc("2.1.310 (Claude Code)\n")
        return Proc("", 1, "rate limited")
    pre, ok = _preboot(monkeypatch, args, which=lambda n: "C:/bin/claude.exe", run=limited)
    assert ok is False and pre["checks"]["claude_ok"] is False and "rate limited" in pre["claude_answers"]["error"]
    pre, ok = _preboot(monkeypatch, args, which=lambda n: None, run=_no_cli)
    assert ok is False and pre["claude_answers"]["error"] == "not probed: no CLI"


def test_preboot_refuses_each_failed_check(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    kw = {"which": _no_cli, "run": _no_cli}
    assert _preboot(monkeypatch, args, free=lambda: 9.9, **kw)[1] is False
    assert _preboot(monkeypatch, args, free=lambda: None, **kw)[1] is False
    assert _preboot(monkeypatch, args, java_pids=lambda: ["4242"], **kw)[1] is False

    def unread():
        raise OSError("no powershell")
    pre, ok = _preboot(monkeypatch, args, java_pids=unread, **kw)
    assert ok is False and pre["java_pids"] is None and "no powershell" in pre["java_error"]
    pre, ok = _preboot(monkeypatch, XT.flags(["--variant", "ladder", "--fixture", "nope", "--no-llm"]), **kw)
    assert ok is False and pre["checks"]["fixture_ok"] is False and "nope" in pre["fixture_error"]
    pre, ok = _preboot(monkeypatch, args, survive=Survive if not FORK else type("Old", (), {
        "__init__": lambda self, world, actions, log_path, clock=None, source=None: None}), **kw)
    assert ok is False and pre["variant"]["fork"] is False and "Task 1" in pre["variant"]["error"]
    taken = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm", "--make-fixture", "agent0"])
    pre, ok = _preboot(monkeypatch, taken, **kw)
    assert ok is False and pre["checks"]["make_fixture_free"] is False
    free = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm", "--make-fixture", "arena-east"])
    pre, ok = _preboot(monkeypatch, free, **kw)
    assert ok and pre["checks"]["make_fixture_free"] is True
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (False, "FAIL ports in use"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    assert TR.preboot(args, XT.PROFILE, free=lambda: 15.0, java_pids=lambda: [], survive=Forked, control=CONTROL,
                      **kw)[1] is False


def test_an_unknown_variant_refuses_the_boot_once_the_fork_is_on_the_tree():
    r = TR.variant_check("no_such_variant_xyz", survive=Forked, control=CONTROL)
    assert r == {"variant": "no_such_variant_xyz", "fork": True, "ok": False,
                 "error": "ValueError: unknown control 'no_such_variant_xyz'"}
    assert TR.variant_check("ladder", survive=Forked, control=CONTROL)["ok"] is True
    loaded = []
    stub = types.SimpleNamespace(CONTROLS=("ladder",), load=loaded.append)
    assert TR.variant_check("doctrine", survive=Forked, control=stub)["ok"] is True and loaded == ["doctrine"]


# ================================================================ the fake session: DayMod, FakeServer, FakeBus
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


class DayMod(FakeMod):
    """test_e_day_24.py's DayMod trimmed: one frame a tick at 10 Hz on the shared clock, the character at `pos` (moved
    by `teleport`), equip wields the bat, attack rejected, every other type accepted and done."""

    def __init__(self, d, clock, items=(), pos=(100.0, 200.0)):
        super().__init__(d, clock=clock.now)
        self.clk, self.t0 = clock, clock.t
        self.hz = 10
        self.pos = list(pos)
        self.weapon = None
        self.pending, self.cmd_seen, self.cmds = [dict(i) for i in items], 0, []
        self.hello(mode="append")
        self.next_t = clock.t
        self._tick()
        self.next_t += 1.0 / self.hz

    def s(self):
        return self.clk.t - self.t0

    def sleep(self, dt):
        end = self.clk.t + dt
        while self.next_t <= end + 1e-9:
            self.clk.t = self.next_t
            self._tick()
            self.next_t += 1.0 / self.hz
        self.clk.t = max(self.clk.t, end)

    def _poll(self):
        p = os.path.join(self.dir, "cmd.txt")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8") as f:
            cmd = json.loads(f.read())
        if cmd["seq"] <= self.cmd_seen:
            return
        self.cmd_seen = cmd["seq"]
        self.cmds.append(cmd)
        t, aid = cmd["type"], cmd["aid"]
        if t == "attack":
            self.act(aid, "rejected", t, reason="no target")
            return
        self.act(aid, "accepted", t)
        if t == "equip":
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
        self.act(aid, "done", t, result={})

    def _tick(self):
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        gmin = 480.0 + self.s() * 16.0 / 60.0
        self.frame(gameMin=gmin, worldAge=8.0 + (gmin - 480.0) / 60.0, weapon=self.weapon, zombies=[],
                   me=dict(DEFAULT_FRAME["me"], x=self.pos[0], y=self.pos[1]))


class FakeServer:
    """The fake RCON: every command recorded in `calls` in order; teleportto moves the fake mod's character."""

    def __init__(self, mod, calls):
        self.mod, self.calls, self.errors = mod, calls, []

    def rcon(self, cmd):
        self.calls.append(("rcon", cmd))
        m = re.match(r'^teleportto "admin" (-?[\d.]+),(-?[\d.]+),(-?[\d.]+)$', cmd)
        if m:
            self.mod.pos = [float(m.group(1)), float(m.group(2))]
            return True, "admin teleported to %s" % cmd.split(" ", 2)[2]
        if cmd.startswith("createhorde2 "):
            return True, "Horde spawned."
        return False, "unknown command"


class FakeBus:
    """test_e_day_24.py's FakeBus, its happy path (stats.all, players, damage.watch, item.get, ping)."""

    def __init__(self, mod):
        self.mod = mod

    def ask(self, node, cmd, args, timeout=30):
        self.mod.sleep(0.05)
        if cmd == "ping":
            return "pong"
        if cmd == "item.get":
            return {"fullType": KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
        if cmd == "stats.all":
            return {"side": "server", "user": args, "worldAge": 8.0, "mult": 1.0, "wall": 1,
                    "stats": {"Hunger": 0.11, "Thirst": 0.1, "Fatigue": 0.05}, "missing": {}}
        if cmd == "players":
            return ["admin"]
        if cmd == "damage.watch":
            return {"ok": True, "side": "server", "hooked": True, "user": args.split()[0], "counts": {}, "n": 0,
                    "last": {}, "dropped": 0}
        return {"error": "unknown command " + cmd}


class InlinePolls(P.PollThread):
    """test_e_day_24.py's InlinePolls: `latest(name)` first runs that read when it is due, on the caller's thread."""

    def start(self):
        self.started = True

    def latest(self, name):
        self.run_due(only=name)
        return super().latest(name)


def _survive_recording(monkeypatch):
    """TR.Survive wrapped: each construction's `control` recorded, passed on only when the fork is on the tree."""
    seen = []

    def make(*a, **kw):
        seen.append(kw.get("control", "<absent>"))
        if not FORK:
            kw.pop("control", None)
        return Survive(*a, **kw)
    monkeypatch.setattr(TR, "Survive", make)
    return seen


def boot_trial(tmp_path, monkeypatch, argv, prov=None, rc=0, mem_ok=True, preboot_print=None, server_log=None):
    """trial.boot_and_run on the real profile and a real run layout with the boot, the teardown and the kill injected
    (the module docstring); the fake RCON's calls and the snapshot's argv land in one ordered list. The fake teardown
    marks `server_stopped` with `rc` as bounded_teardown does; `mem_ok` False refuses at the memory gate;
    `server_log` (text) is written as the run folder's server-stdout.log at the boot."""
    clock = Clock()
    calls = []
    runs = tmp_path / "runs"
    from pzt import paths as PZ
    monkeypatch.setattr(PZ, "RUNS", str(runs))
    waits = []

    def wait_memory(g, **kw):
        waits.append(kw)
        return mem_ok, [{"wall": 0, "free_gb": 15.0 if mem_ok else 3.0}]
    monkeypatch.setattr(S.DL, "wait_memory", wait_memory)
    monkeypatch.setattr(X, "free_gb", lambda: 15.0)
    monkeypatch.setattr(X, "java_gb", lambda: {"pids": [], "gb": 0.0, "each": []})
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    monkeypatch.setattr(DY, "copy_run", lambda *a, **k: pytest.fail("copy_run is never called by a trial"))
    monkeypatch.setattr(X.Xs, "copy_artifacts", lambda *a, **k: pytest.fail("no artifact copy in a trial"))
    seen = _survive_recording(monkeypatch)
    got = {"run_dir": None, "mod": None}

    def boot(xs, prof, rec_fx, run_dir, users, started, clients, holder, make_client=None):
        cache = tmp_path / "client-cache"
        client = types.SimpleNamespace(cache=str(cache), username="admin", seen={}, alive=True, proc=None,
                                       console=str(tmp_path / "console.txt"))
        mod = DayMod(os.path.join(str(cache), "Lua", "pzagent", "admin"), clock, items=[BAT])
        srv = FakeServer(mod, calls)
        holder["server"], xs.server = srv, srv
        xs.ask, xs.node, xs.sleep = FakeBus(mod).ask, (lambda side: side), mod.sleep
        clients["admin"] = client
        started.append(client)
        got.update(mod=mod, xs=xs, run_dir=run_dir)
        if server_log is not None:
            with open(os.path.join(run_dir, TR.SERVER_LOG), "w", encoding="utf-8") as fh:
                fh.write(server_log)
        return {"verify": [{"ok": True}], "build": "42.21.0"}

    def run_session_fn(xs, transport, pre, note):
        sess = TR.run_session(args, xs, transport, pre, note, clock=clock.now, sleep=got["mod"].sleep,
                              free=lambda: 30.0, polls=InlinePolls(clock=clock.now))
        got["sess"] = sess
        return sess

    def teardown(tl, srv, cl):
        calls.append(("teardown",))
        tl.mark("server_stopped", rc=rc, errors=0)

    def snap(cmd, **kw):
        calls.append(("run", cmd))
        return Proc("FIXTURE snapshotted", 0)

    def preboot():
        if preboot_print:
            print(preboot_print)
        return {"checks": {"ok": True}}, True

    args = XT.flags(argv)
    out = TR.boot_and_run(args, preboot, key=XT.KEY, driver=XT.DRIVER, artifact=XT.ARTIFACT, profile=XT.PROFILE,
                          argv=argv, run_session_fn=run_session_fn, boot=boot, teardown=teardown,
                          kill=lambda srv, every: None, run=snap,
                          provenance_fn=prov or (lambda repo: {"commit": "e" * 40, "stamp": None, "dirty": False,
                                                               "diff_sha256": None, "untracked": None,
                                                               "provenance": "git", "diff": None}))
    return types.SimpleNamespace(out=out, calls=calls, seen=seen, clock=clock, run_dir=got["run_dir"],
                                 sess=got.get("sess"), mod=got["mod"], runs=runs, args=args, waits=waits)


# ================================================================ the boot on a real run layout
def test_a_trial_writes_trial_json_at_the_run_root_and_copies_nothing(tmp_path, monkeypatch, agent_fixture):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.5", "--no-llm"]
    r = boot_trial(tmp_path, monkeypatch, argv)
    out = r.out
    assert out["phase_errors"] == {} and out.get("error") is None and out["stop"]["reason"] == "day_cap"
    assert out["stop"]["wallS"] == pytest.approx(30, abs=0.3) and out["finished"] is True
    run_id = os.path.basename(r.run_dir)
    assert re.match(r"^x_trial-ladder-\d{8}-\d{6}$", run_id) and os.path.dirname(r.run_dir) == str(r.runs)
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert tuple(trial) == TR.TRIAL_KEYS
    assert trial["variant"] == "ladder" and trial["fixture"] == "agent" and trial["minutes"] == 0.5
    assert trial["commit"] == "e" * 40 and trial["dirty"] is False and trial["stamp"] is None
    assert trial["provenance"] == "git" and trial["diff_sha256"] is None and trial["untracked"] is None
    assert trial["waves"] == "street" and trial["wave_plan"] == {"period_s": None, "spawns": []}
    assert trial["no_llm"] is True and trial["teleport"] is None and trial["make_fixture"] is None
    assert trial["goals"] == "scripted" and list(trial).index("goals") == list(trial).index("no_llm") + 1
    assert trial["detached"] is False and trial["wall_bound_s"] == 15 + 140 + 2 + 35 + 6 + 75
    assert trial["argv"] == argv and re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", trial["started_at"])
    assert trial["end_pos"] == [100.0, 200.0, 0] and trial["end_health"] == 100.0       # the last kept frame's
    assert trial["switches"] == TR.switches(r.sess.planner) and trial["switches"]["SWING_CLOSE"] is True
    assert json.loads(json.dumps(out["trial"])) == trial
    assert r.seen == ["ladder"]                                       # Survive(control="ladder")
    assert isinstance(r.sess, TR.TrialChain) and isinstance(r.sess.planner.goals.source, ScriptedSource)
    assert r.sess.idle is False and r.sess.ticks > 0                 # the variant decides on a trial
    assert r.sess.lim["DAY_CAP_S"] == 30.0 and out["constants"]["BUDGET_S"] == 140.0
    assert out["wall_bound"] == TR.wall_bound(r.args)
    assert r.waits == [{"max_wait_s": 0.0}]                           # the memory gate reads once, never waits
    assert out["driver_commit"] == "e" * 40 and out["session_key"] == "x_trial" and out["driver"] == "x_trial.py"
    # no auto-copy (copy_run and copy_artifacts fail the test if called): nothing under this tree's artifacts
    assert not os.path.exists(os.path.join(REPO, "testing", "artifacts", run_id))
    assert "make_fixture" not in out and "llm" not in out["loop"]
    assert out["loop"]["trial"] == {"teleport": None, "idle": False,
                                    "waves": {"plan": "street", "period_s": None, "spawns": [], "started": True,
                                              "rows": [], "error": None, "joined": None, "confirm": [],
                                              "by_wave": [], "server_spawns": None}}
    assert r.calls == [("teardown",)]                                  # no RCON on the street, no snapshot
    persisted = json.loads(open(os.path.join(r.run_dir, "x_trial.json"), encoding="utf-8").read())
    assert persisted["finished"] is True and persisted["trial"]["variant"] == "ladder"
    json.dumps(out, allow_nan=False, default=str)


def test_the_bound_is_printed_before_the_preboot(tmp_path, monkeypatch, agent_fixture, capsys):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.1", "--no-llm"]
    boot_trial(tmp_path, monkeypatch, argv, preboot_print="PREBOOT-RAN")
    text = capsys.readouterr().out
    line = TR.bound_line(XT.flags(argv))
    assert line.startswith("x_trial wall bound 249 s (") and line.endswith("foreground: under the 570 s cap")
    assert text.index(line) < text.index("PREBOOT-RAN")


def test_a_memory_gate_refusal_leaves_no_run_folder(tmp_path, monkeypatch, agent_fixture):
    with pytest.raises(SystemExit):
        boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.1",
                                           "--no-llm"], mem_ok=False)
    assert not (tmp_path / "runs").exists() or os.listdir(str(tmp_path / "runs")) == []


def test_a_dirty_tree_saves_its_diff_beside_trial_json(tmp_path, monkeypatch, agent_fixture):
    prov = {"commit": "f" * 40, "stamp": None, "dirty": True, "diff_sha256": "0" * 64,
            "untracked": ["testing/agent/base/planner/doctrine/__init__.py"], "provenance": "git",
            "diff": "diff --git a/x b/x\r\n+1\n### untracked file testing/agent/base/planner/doctrine/__init__.py\n"}
    r = boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.1",
                                           "--no-llm"], prov=lambda repo: prov)
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert trial["dirty"] is True and trial["diff_sha256"] == "0" * 64 and "diff" not in trial
    assert trial["untracked"] == prov["untracked"]
    with open(os.path.join(r.run_dir, "trial.diff"), encoding="utf-8", newline="") as fh:
        assert fh.read() == prov["diff"]


def test_the_lone_wave_spawns_at_the_square_off_the_last_frame(tmp_path, monkeypatch, agent_fixture):
    r = boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.2",
                                           "--no-llm", "--waves", "lone"])
    rcon = [c for c in r.calls if c[0] == "rcon"]
    # wave 0 at once; 12 s < 60; the fake lists no spawned zombie, so the wave is re-sent once at WAVE_CONFIRM_S
    assert rcon == [("rcon", "createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1")] * 2
    w = r.out["loop"]["trial"]["waves"]
    assert w["plan"] == "lone" and w["started"] is True and w["joined"] is True and w["error"] is None
    assert len(w["rows"]) == 2 and w["rows"][0]["at"] == [108, 200, 0] and w["rows"][0]["ack"]["ok"] is True
    assert w["rows"][1]["resend_of"] == 0 and w["confirm"][0]["resent"] == 1 and w["confirm"][0]["listed_ids"] == []
    assert w["by_wave"] == [{"wave": 0, "sent": 1, "resent": 1, "listed_ids": [], "confirmed": False}]
    assert w["server_spawns"] is None                                  # the fake server writes no log
    steps = [s for s in r.out["steps"] if s.get("cmd") == "rcon"]
    assert [s["step"] for s in steps] == ["wave_0_0", "wave_0_0_resend"]
    # the waves read the session's clock and began at the loop's first frame read (one pass after the loop's start),
    # never at the hello frame, tens of seconds before it on the fake clock (the kit phase between)
    assert r.sess.waves.clock == r.sess.clock
    assert r.sess.t_loop0 - r.mod.t0 > 5.0
    assert r.sess.t_loop0 <= r.sess.waves.t0 <= r.sess.t_loop0 + 1.0
    assert w["rows"][0]["t"] < 1.0


def test_the_servers_spawn_count_reaches_the_record_and_the_persisted_artifact(tmp_path, monkeypatch, agent_fixture):
    """The run folder's server log read after the teardown: two "Spawning" lines (the plan's lone wave sent twice, the
    second a re-send) against the frames' none listed."""
    log = ("LOG  : Lua          f:400 st:1> PZTK: cmd #1 ping -> pong\n" +
           "WARN : General      f:421 st:2 at CreateHorde2Command.Command         > Spawning new Male Zed, Dressed in "
           "No Outfit\n" * 2)
    r = boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.2",
                                           "--no-llm", "--waves", "lone"], server_log=log)
    w = r.out["loop"]["trial"]["waves"]
    assert w["server_spawns"] == 2 and w["by_wave"][0]["sent"] + w["by_wave"][0]["resent"] == 2
    assert w["by_wave"][0]["listed_ids"] == []
    persisted = json.loads(open(os.path.join(r.run_dir, "x_trial.json"), encoding="utf-8").read())
    assert persisted["loop"]["trial"]["waves"]["server_spawns"] == 2


def test_the_fixture_making_path_teleports_then_snapshots_in_order(tmp_path, monkeypatch, agent_fixture):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.2", "--no-llm", "--teleport", "10750,10620",
            "--make-fixture", "arena-east"]
    r = boot_trial(tmp_path, monkeypatch, argv)
    snap = CH.snapshot_cmd(r.run_dir, "arena-east", "agent", 1)
    assert r.calls == [("rcon", 'teleportto "admin" 10750,10620,0'), ("teardown",), ("run", snap)]
    assert snap[-8:] == ["--from-run", r.run_dir, "--name", "arena-east", "--parent", "agent", "--session", "1"]
    tp = r.out["loop"]["trial"]["teleport"]
    assert tp["cmd"] == 'teleportto "admin" 10750,10620,0' and tp["ack"]["ok"] is True and tp["arrived"] is True
    assert tp["pos"] == [10750.0, 10620.0, 0]
    steps = [s for s in r.out["steps"] if s.get("cmd") == "rcon"]
    assert [s["step"] for s in steps] == ["setup_tp"] and steps[0]["phase"] == "loop"
    assert r.sess.first_frame["me"]["x"] == 100.0                     # the hello-phase frame, before the teleport
    # the planner idle under --make-fixture: no tick decided, only the kit's equip and the loop's closing stop sent
    assert r.sess.idle is True and r.sess.ticks == 0 and r.out["loop"]["trial"]["idle"] is True
    assert {c["type"] for c in r.mod.cmds} <= {"equip", "stop"}
    end = {"pos": [10750.0, 10620.0, 0], "health": 100.0, "start_health": 100.0}
    mf = r.out["make_fixture"]
    assert mf == {"name": "arena-east", "cmd": snap, "ran": True, "exit": 0, "output": "FIXTURE snapshotted",
                  "skipped": None, "error": None, "server_stop": {"marked": True, "rc": 0, "clean": True}, "end": end}
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert trial["teleport"] == [10750, 10620] and trial["make_fixture"] == "arena-east"
    assert trial["end_pos"] == [10750.0, 10620.0, 0] and trial["end_health"] == 100.0


def test_a_killed_server_never_becomes_a_fixture(tmp_path, monkeypatch, agent_fixture):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.1", "--no-llm", "--teleport", "10750,10620",
            "--make-fixture", "arena-east"]
    r = boot_trial(tmp_path, monkeypatch, argv, rc=None)                 # the 45 s stop timed out: killed
    assert [c[0] for c in r.calls] == ["rcon", "teardown"]
    assert r.out["make_fixture"]["skipped"] == "the server did not stop cleanly (rc None, marked True)"


def test_make_fixture_skips_each_failed_gate():
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--teleport", "1,2", "--make-fixture", "a1"])

    def never(*a, **k):
        raise AssertionError("no snapshot")
    clean = [{"phase": "server_stopped", "rc": 0, "errors": 0}]
    ok = {"stop": {"reason": "day_cap"}, "timeline": clean, "loop": {"trial": {"teleport": {"arrived": True}}}}
    at = {"pos": [1.5, 2.5, 0], "health": 100.0, "start_health": 100.0}

    def skip(out, end=at):
        return TR.make_fixture(out, args, "r", end, never)["skipped"]
    assert "stopped death" in skip(dict(ok, stop={"reason": "death"}))
    assert "failed" in skip(dict(ok, error="X: y"))
    assert "did not stop cleanly (rc None, marked False)" in skip(dict(ok, timeline=[]))
    assert "did not stop cleanly (rc None" in skip(dict(ok, timeline=[{"phase": "server_stopped", "rc": None}]))
    assert "did not stop cleanly (rc 1" in skip(dict(ok, timeline=[{"phase": "server_stopped", "rc": 1}]))
    assert "did not stop cleanly" in skip(dict(ok, hard_kill_error="OSError: x"))
    assert "did not stop cleanly" in skip(dict(ok, teardown_error="TimeoutExpired: x"))
    assert "teleport's square" in skip(dict(ok, loop={"trial": {"teleport": {"arrived": False}}}))
    assert "ended at [9.0, 2.0, 0], not within 2.0 tiles" in skip(ok, dict(at, pos=[9.0, 2.0, 0]))
    assert "ended at None" in skip(ok, dict(at, pos=None))
    assert "ended wounded or unread (health 80.0, 100.0 at the start)" in skip(ok, dict(at, health=80.0))
    assert "ended wounded or unread (health None" in skip(ok, dict(at, health=None))
    r = TR.make_fixture(ok, args, "r", at, lambda cmd, **k: Proc("", 1, "refused: fixture 'a1' already exists"))
    assert r["ran"] is True and r["exit"] == 1 and "already exists" in r["output"] and r["skipped"] is None
    # without a teleport the square is not asked, the stop and the health still are
    plain = XT.flags(["--variant", "ladder", "--fixture", "agent", "--make-fixture", "a1"])
    r = TR.make_fixture(dict(ok, loop={}), plain, "r", dict(at, pos=[50.0, 60.0, 0]), lambda cmd, **k: Proc("", 0))
    assert r["ran"] is True and r["skipped"] is None
    nothing = TR.make_fixture(dict(ok, loop={}), plain, "r", None, never)             # no session: nothing read
    assert nothing["skipped"] == "the character ended wounded or unread (health None, None at the start)"


def _chain(tmp_path, argv, **kw):
    args = XT.flags(argv)
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=str(tmp_path / "a.json"),
                               rcon=lambda cmd, tag: {"ok": True})
    seen = []

    def make(*a, **k):
        seen.append(k.get("control", "<absent>"))
        if not FORK:
            k.pop("control", None)
        return Survive(*a, **k)
    orig = TR.Survive
    TR.Survive = make
    try:
        return TR.make_session(xs, None, args, clock=lambda: 5.0, **kw), seen
    finally:
        TR.Survive = orig


def test_the_model_trial_builds_the_llm_source_and_its_record(tmp_path):
    c, seen = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent"], cli_version="2.1")
    assert seen == ["ladder"] and isinstance(c, TR.TrialChain) and isinstance(c.planner.goals.source, LLMSource)
    assert c.planner.goals.source.log_path == str(tmp_path / "goals.log")
    assert c.lim["DAY_CAP_S"] == 300.0 and c.lim["PLANNER_HZ"] == 2
    rec = c.extra_record()
    assert rec["llm"]["model"] == TR.MODEL and rec["llm"]["cli_version"] == "2.1" and rec["llm"]["calls"] == []
    assert rec["trial"]["waves"]["plan"] == "street" and c.waves.clock is c.clock


def test_the_waves_stop_at_the_loops_stop_before_its_settle(tmp_path, monkeypatch):
    c, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--waves", "lone"])
    order = []
    c.waves.stop = lambda: order.append("waves.stop")
    monkeypatch.setattr(S.Session, "stop_character", lambda self: order.append("stop_character"))
    c.stop_character()
    assert order == ["waves.stop", "stop_character"]


def test_a_teleport_that_raises_still_stops_the_waves_and_saves(tmp_path, monkeypatch):
    c, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--teleport", "1,2"])
    order = []

    def boom(sess, x, y):
        raise X.Budget("wall past the budget")
    monkeypatch.setattr(TR, "teleport", boom)
    c.ready = True
    c.waves.stop = lambda: order.append("waves.stop")
    c.save = lambda: order.append("save")
    with pytest.raises(X.Budget):
        c.phase_loop()
    assert order == ["waves.stop", "save"]


def test_the_planner_factory_passes_the_variant_as_control():
    """The fork's keyword: `Survive(..., control=<variant>)` in the factory's source, whatever the tree's Survive."""
    src = inspect.getsource(TR.planner_factory)
    assert "return Survive(world, actions, log_path, clock, source=source, control=variant)" in src


def test_the_ladder_arm_runs_the_dress_maneuver_by_default_and_records_it(tmp_path):
    """Plan 31 Task 15a: the Dress maneuver is Survive's default, so Task 12's pre-run edit (62776c14, the ladder
    arm's instance override LADDER_ON) is gone: the ladder arm's planner reads DRESS_MANEUVER True off the class, set on
    no instance, and trial.json's switches still carry it (EXTRA_SWITCHES)."""
    assert SV.Survive.DRESS_MANEUVER is True and not hasattr(TR, "LADDER_ON")
    c, seen = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--goals", "hold"])
    assert seen == ["ladder"] and "DRESS_MANEUVER" not in vars(c.planner) and c.planner.DRESS_MANEUVER is True
    assert TR.switches(c.planner)["DRESS_MANEUVER"] is True
    c2, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    assert c2.planner.DRESS_MANEUVER is True and c2.planner is not c.planner


# ================================================================ --goals hold (Plan 31 Task 12's pre-step)
HOLD_ARGV = ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--goals", "hold"]


def test_the_hold_source_scans_in_place_then_rests_and_notes_the_start_square():
    """Task 12's loop fix: the first request on a scan place is ExploreToward to the character's own square (the
    place's scan, ended arrived), every later one there a Rest; a new place takes its own scan, never a walk off."""
    src = TR.HoldSource()
    assert src.NAME == "hold" and src.square is None and src.scanned == []
    g = src.propose({"pos": {"x": 10750.5, "y": 10620.5, "z": 0}})
    assert g.TYPE == "ExploreToward" and (g.x, g.y) == (10750, 10620) and src.square == [10750.5, 10620.5]
    assert src.scanned == [(10750, 10620)]
    g = src.propose({"pos": {"x": 10751.2, "y": 10619.0, "z": 0}})    # the same place: a rest
    assert g.TYPE == "Rest" and g.seconds == TR.HOLD_REST_S == 30.0
    g = src.propose({"pos": {"x": 10790.0, "y": 10600.0, "z": 0}})    # a new place: its own scan in place
    assert g.TYPE == "ExploreToward" and (g.x, g.y) == (10790, 10600)
    assert src.square == [10750.5, 10620.5]                            # the square is the first pos, never moved
    assert src.propose({"pos": {"x": 10790.4, "y": 10600.3}}).TYPE == "Rest"
    late = TR.HoldSource()
    assert late.propose({}).TYPE == "Rest" and late.square is None    # no pos yet: a rest, no scan
    assert late.propose({"pos": {"x": None, "y": 3}}).TYPE == "Rest" and late.square is None
    assert late.propose({"pos": {"x": 5, "y": 6}}).TYPE == "ExploreToward" and late.square == [5, 6]
    assert late.propose({"pos": {"x": 5, "y": 6}}).TYPE == "Rest"


def test_the_hold_place_is_the_explore_grid(monkeypatch):
    """HoldSource.place rounds as policies.place_of does (half up on the SCAN_R grid)."""
    from agent.base.planner import policies as PO
    for x, y in ((10789.5, 10614.5), (10785.0, 10615.0), (10784.99, 10604.99), (-5.0, 5.0), (0.0, 0.0)):
        monkeypatch.setattr(PO, "me_xy", lambda w, x=x, y=y: (x, y))
        assert TR.HoldSource.place(x, y) == PO.place_of(types.SimpleNamespace())


def test_the_hold_source_reissues_a_fresh_rest_when_one_ends_and_never_walks():
    src = TR.HoldSource()
    seen = []
    view = {"pos": {"x": 1.0, "y": 2.0, "z": 0}, "edge": [90, 90], "toward": {"for": "unlooted", "door": [50, 50]},
            "buildings": [{"id": 7, "dist": 5.0, "looted": False, "containers": 3, "shelter": True, "door": [9, 9]}],
            "needs_wanted": ["water", "food", "bandage"], "stock_uses": ["water", "food"], "want_shelter": True,
            "stuck": {"edge": [4, 5, "N"]}, "cooled": []}
    for _ in range(6):
        g = src.propose(view)
        seen.append(g)
        g.end("done", "rested")                                       # the goal ends: the next request is a new one
    assert seen[0].TYPE == "ExploreToward" and seen[0].args() == {"x": 1, "y": 2}     # the scan in place, no walk
    assert {g.TYPE for g in seen[1:]} == {"Rest"} and len({id(g) for g in seen}) == 6
    assert all(g.args() == {"seconds": 30.0} for g in seen[1:])
    assert not any(g.TYPE in ("LootBuilding", "Shelter", "Stock") for g in seen)


def test_the_hold_planner_rests_through_the_quiet_where_the_scripted_one_walks(tmp_path):
    c, seen = _chain(tmp_path, HOLD_ARGV)
    assert seen == ["ladder"] and isinstance(c.planner.goals.source, TR.HoldSource)
    assert not isinstance(c.planner.goals.source, ScriptedSource) and c.lim["DAY_CAP_S"] == 300.0
    c, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    assert isinstance(c.planner.goals.source, ScriptedSource)
    c, _ = _chain(tmp_path, ["--variant", "ladder", "--fixture", "agent", "--no-llm", "--goals", "scripted"])
    assert isinstance(c.planner.goals.source, ScriptedSource)
    assert "llm" not in c.extra_record() and "goals" in inspect.signature(TR.planner_factory).parameters


def test_the_hold_trial_writes_goals_hold_in_trial_json_and_keeps_the_no_llm_bound(tmp_path, monkeypatch,
                                                                                     agent_fixture):
    argv = HOLD_ARGV + ["--minutes", "0.5"]
    r = boot_trial(tmp_path, monkeypatch, argv)
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert tuple(trial) == TR.TRIAL_KEYS and trial["goals"] == "hold" and trial["no_llm"] is True
    assert trial["variant"] == "ladder" and trial["argv"] == argv
    assert isinstance(r.sess.planner.goals.source, TR.HoldSource) and "llm" not in r.out["loop"]
    assert r.out["stop"]["reason"] == "day_cap" and r.out["finished"] is True and r.out.get("error") is None
    assert trial["wall_bound_s"] == 15 + 140 + 2 + 35 + 6 + 75        # the no-model bound, as --no-llm's
    assert TR.wall_bound(r.args) == TR.wall_bound(XT.flags(argv[:-4] + ["--minutes", "0.5"]))
