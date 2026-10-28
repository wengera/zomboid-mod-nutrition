"""base/gates_e.py (Plan 23 Task 15), offline: grade_e1 and gate_e1 over artifacts built from fakemod.DEFAULT_FRAME."""
import copy
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates as GT
from agent.base import gates_e as E
from agent.drivers import e_grade as EG
from .fakemod import DEFAULT_FRAME

HERE = os.path.dirname(os.path.abspath(__file__))


def frame(seq, wall_s=None, **over):
    """A kept frame row: DEFAULT_FRAME with seq and wallMs (seq tenths of a second unless wall_s) and `over` laid on;
    dotted keys reach into a group (stats.thirst)."""
    f = copy.deepcopy(DEFAULT_FRAME)
    f["seq"] = seq
    f["wallMs"] = int(1_000_000 + (seq * 100 if wall_s is None else wall_s * 1000))
    for k, v in over.items():
        if "." in k:
            g, kk = k.split(".")
            f[g][kk] = v
        else:
            f[k] = v
    return f


def series(n=100, **per):
    """n frames, one a second (seq 1..n); per maps a key to a function of the index."""
    out = []
    for i in range(n):
        out.append(frame(i + 1, i, **{k: fn(i) for k, fn in per.items()}))
    return out


def act(type_, sent, end, state="done", **extra):
    return dict({"aid": 1, "type": type_, "args": {}, "state": state, "reason": None, "sentS": sent, "endedS": end},
                **extra)


def art(frames=None, actions=(), stop="day_cap", game_min=1000.0, first=0.0, **loop):
    frames = series() if frames is None else frames
    lp = {"wallS": float(len(frames) - 1), "first_game_min": first, "game_min": game_min, "last_frames": frames,
          "actions": list(actions), "fights": [], "cost": {"p50": 0.2, "p99": 1.0, "max": 2.0, "over5": 0}}
    lp.update(loop)
    return {"stop": {"reason": stop, "detail": "x", "wallS": lp["wallS"]}, "loop": lp, "frames": {}}


SLEEP = {"aid": 3, "state": "done", "reason": None, "result": None, "startS": 1, "endS": 2, "fatigueBefore": 0.8,
         "fatigueAfter": 0.2, "sleptH": 7.5, "bedType": "bed"}


def good(game_min=1440.0, **kw):
    """A session that drank, ate and slept, thirst and hunger falling after each."""
    fr = series(thirst_fn=None) if False else series(**{"stats": lambda i: {"hunger": 0.5 if i < 40 else 0.2,
                                                                        "thirst": 0.5 if i < 20 else 0.1,
                                                                        "fatigue": 0.1}})
    return art(fr, [act("consume", 18, 19, use="drink"), act("consume", 38, 39, use="eat")],
               game_min=game_min, night={"wants": 5, "steps": [], "sleeps": [dict(SLEEP)]}, **kw)


# ---------------------------------------------------------------- grade_e1
def test_survived_follows_the_stop_and_game_minutes_the_loop_difference():
    g = E.grade_e1(art(game_min=900.0, first=100.0))
    assert g["survived"] is True and g["game_minutes"] == 800.0 and g["grade"] == "grade_e1"
    assert E.grade_e1(art(stop="budget"))["survived"] is True
    assert E.grade_e1(art(stop="bus_dead"))["survived"] is False
    assert E.grade_e1(art(first=None))["game_minutes"] is None


def test_missing_keys_and_malformed_artifacts_never_raise():
    for bad in ({}, None, [], "x", {"loop": None}, {"loop": {"actions": None, "last_frames": 3, "fights": "x"}},
                {"stop": {"reason": "death"}, "loop": {"death": []}}):
        g = E.grade_e1(bad)
        assert isinstance(g["report_lines"], list)
    assert E.gate_e1(None)["verdict"] == "NO-GO" and E.gate_e1([None, 3])["verdict"] == "NO-GO"


def test_needs_count_consumes_by_use_and_stat_fell_reads_the_bracketing_frames():
    g = E.grade_e1(good())
    n = g["needs"]
    assert n["drink"] == {"sent": 1, "done": 1, "stat_fell": True}
    assert n["eat"] == {"sent": 1, "done": 1, "stat_fell": True}
    assert n["sleep"] == {"sent": 1, "done": 1, "sleptH": 7.5, "fatigue_fell": True}


def test_a_stat_that_did_not_fall_and_a_failed_action():
    fr = series(**{"stats": lambda i: {"hunger": 0.5, "thirst": 0.5, "fatigue": 0.1}})
    a = art(fr, [act("consume", 10, 12, use="drink"), act("consume", 30, 32, state="failed", use="eat"),
                 act("consume", 40, 42)])
    n = E.grade_e1(a)["needs"]
    assert n["drink"] == {"sent": 1, "done": 1, "stat_fell": False}
    assert n["eat"] == {"sent": 1, "done": 0, "stat_fell": None} and n["unknown"] == 1


def test_stat_fell_is_none_when_the_frames_do_not_bracket_the_action():
    a = art(series(20), [act("consume", 30, 32, use="drink"), act("consume", 0.0, 5, use="eat"),
                         act("consume", 10, None, use="drink")])
    n = E.grade_e1(a)["needs"]
    assert n["drink"]["done"] == 2 and n["drink"]["stat_fell"] is None
    assert n["eat"]["stat_fell"] is None                   # no frame before sentS 0.0
    a = art(series(20), [act("consume", 10, 12, use="drink")])
    a["loop"].pop("wallS")
    a["stop"].pop("wallS")
    assert E.grade_e1(a)["needs"]["drink"]["stat_fell"] is None       # no anchor for the frames


def test_sleep_fatigue_that_rose_and_no_sleep():
    s = dict(SLEEP, fatigueAfter=0.9)
    n = E.grade_e1(art(night={"sleeps": [s, dict(SLEEP, state="failed")]}))["needs"]["sleep"]
    assert n == {"sent": 2, "done": 1, "sleptH": 7.5, "fatigue_fell": False}
    assert E.grade_e1(art())["needs"]["sleep"] == {"sent": 0, "done": 0, "sleptH": 0, "fatigue_fell": None}


def test_the_stand_off_rule():
    fights = [{"fight_ticks": 21, "flee": {"stalled": 3}, "end": {"health": 90}},
              {"fight_ticks": 21, "flee": {"unreachable": 1}, "end": None},
              {"fight_ticks": 20, "flee": {"stalled": 3}, "end": {}},
              {"fight_ticks": 40, "flee": {}, "end": {}},
              {"fight_ticks": 40, "flee": {"hurt": 2}, "end": {}}]
    assert E.grade_e1(art(fights=fights))["fights"] == {"n": 5, "ended": 4, "fled": 4, "stand_offs": 2}


def test_load_ratio_and_the_drop_branches():
    fr = series(**{"load": lambda i: {"weight": 4.0 + (i == 50) * 4.5, "max": 10.0, "level": 0, "n": 3}})
    a = art(fr, [act("drop", 1, 2, branch="load"), act("drop", 3, 4, branch="threat"),
                 act("drop", 5, 6, branch="threat"), act("drop", 7, 8, state="failed", branch="load")])
    assert E.grade_e1(a)["load"] == {"max_ratio": pytest.approx(0.85), "guard_drops": 1, "flee_drops": 2}
    assert E.grade_e1(art([]))["load"]["max_ratio"] is None


def test_lineage_from_prev_or_the_loop_and_cost():
    prev = art()
    nxt = art()
    g = E.grade_e1(nxt, prev)
    assert g["lineage"]["ok"] is True
    moved = art(series(5, **{"me": lambda i: dict(DEFAULT_FRAME["me"], x=150.0)}))
    assert E.grade_e1(moved, prev)["lineage"]["ok"] is False
    assert E.grade_e1(art(lineage={"ok": True}))["lineage"] == {"ok": True}
    assert E.grade_e1(art())["lineage"] is None
    assert g["cost"] == {"p50": 0.2, "p99": 1.0, "max": 2.0, "over5": 0}


def _death_art(n, wound_at, health_from):
    fr = []
    for i in range(n):
        h = 100.0 if i < health_from else max(0.0, 100.0 - 5.0 * (i - health_from + 1))
        fr.append(frame(i + 1, i, **{"body": {"health": h, "bleeding": 1 if i >= wound_at else 0, "scratched": 0,
                                              "bitten": 0, "parts": []},
                                     "zombies": [{"id": 1, "dist": 2.0}]}))
    a = art(fr, stop="death")
    a["loop"]["death"] = {"last_frames": fr, "server_damage": []}
    return a


def test_the_death_window_opens_at_the_first_wound_rise():
    a = _death_art(500, wound_at=100, health_from=105)       # a wound 400 frames before the end
    d = E.grade_e1(a)["death"]
    assert d["first_wound_seq"] == 101 and d["window_frames_n"] == 401
    assert d["explained"] is True and d["check"]["explained_by"] == "wound"
    assert E.grade_e1(a)["survived"] is False


def test_a_death_with_no_wound_or_no_zombie_is_not_explained():
    a = _death_art(300, wound_at=999, health_from=100)        # health falls, no wound ever
    d = E.grade_e1(a)["death"]
    assert d["first_wound_seq"] is None and d["explained"] is False
    a = _death_art(300, wound_at=100, health_from=105)
    for f in a["loop"]["last_frames"]:
        f["zombies"] = []
    assert E.grade_e1(a)["death"]["explained"] is False
    assert E.grade_e1(art())["death"] is None


def test_a_server_record_in_the_window_explains_by_the_tagged_arm():
    a = _death_art(300, wound_at=100, health_from=105)
    fr = a["loop"]["last_frames"]
    lo = fr[99]["wallMs"]
    a["loop"]["death"]["server_damage"] = [{"i": 1, "tag": "BLEEDING", "amount": 95.0, "wall": lo + 500},
                                           {"i": 2, "tag": "OLD", "amount": 500.0, "wall": lo - 5000}]
    c = E.grade_e1(a)["death"]["check"]
    assert c["explained_by"] == "tagged" and c["server_n"] == 1


# ---------------------------------------------------------------- gate_e1
def test_gate_passes_a_day_that_did_everything():
    r = E.gate_e1([good(700.0), good(740.0)])
    assert r["verdict"] == "GO"
    assert r["gates"]["alive_through"] == {"ok": True, "value": 1440.0, "threshold": 1440.0, "n": 2}
    for k in ("drink_done", "eat_done", "sleep_done"):
        assert r["gates"][k]["ok"] is True and r["gates"][k]["value"] == 2 and r["gates"][k]["threshold"] == 1
    assert "death_explained" not in r["gates"]


def test_gate_fails_each_gate_alone():
    base = lambda: [good(1440.0)]                       # noqa: E731
    assert E.gate_e1(base())["verdict"] == "GO"
    r = E.gate_e1([good(1439.0)])
    assert r["verdict"] == "NO-GO" and r["gates"]["alive_through"]["ok"] is False
    a = good()
    a["loop"]["actions"] = [x for x in a["loop"]["actions"] if x.get("use") != "drink"]
    r = E.gate_e1([a])
    assert [k for k, v in r["gates"].items() if not v["ok"]] == ["drink_done"]
    a = good()
    a["loop"]["actions"] = [x for x in a["loop"]["actions"] if x.get("use") != "eat"]
    assert [k for k, v in E.gate_e1([a])["gates"].items() if not v["ok"]] == ["eat_done"]
    a = good()
    a["loop"]["night"]["sleeps"][0]["state"] = "failed"
    assert [k for k, v in E.gate_e1([a])["gates"].items() if not v["ok"]] == ["sleep_done"]


def test_gate_with_a_death_needs_it_explained_and_is_never_alive_through():
    d = _death_art(300, wound_at=100, health_from=105)
    d["loop"]["game_min"] = 2000.0
    r = E.gate_e1([good(), d])
    assert r["gates"]["alive_through"]["ok"] is False and r["gates"]["death_explained"]["ok"] is True
    for f in d["loop"]["last_frames"]:
        f["zombies"] = []
    d["loop"]["death"]["last_frames"] = d["loop"]["last_frames"]
    r = E.gate_e1([good(), d])
    assert r["gates"]["death_explained"]["ok"] is False and r["verdict"] == "NO-GO"


def test_gate_reads_each_session_against_the_one_before_it():
    a, b = good(700.0), good(740.0)
    b["loop"]["last_frames"][0]["me"]["x"] = 999.0
    assert E.grade_e1(b, a)["lineage"]["ok"] is False
    assert E.gate_e1([a, b])["verdict"] == "GO"            # lineage is reported, not gated
    assert E.gate_e1([])["verdict"] == "NO-GO"


# ---------------------------------------------------------------- report lines and the script
def test_report_lines_put_the_gate_verdict_first():
    g = E.grade_e1(good())
    assert not g["report_lines"][0].startswith("gate_e1")
    g["gate"] = E.gate_e1([good(100.0)])
    lines = E.report_lines_e(g)
    assert lines[0].startswith("gate_e1 NO-GO: alive_through FAIL") and any(l.startswith("sleep:") for l in lines)


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


def _run(args):
    return subprocess.run([sys.executable, os.path.join(os.path.dirname(E.__file__), "..", "drivers", "e_grade.py")]
                          + args, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(HERE)))


def test_the_script_prints_lines_then_strict_json(tmp_path):
    a = _write(tmp_path, "a.json", good())
    b = _write(tmp_path, "b.json", good())
    r = _run([a])
    assert r.returncode == 0
    body = r.stdout[r.stdout.index("\n{\n"):]
    assert json.loads(body)["grade"] == "grade_e1" and r.stdout.startswith("survived")
    r = _run([_write(tmp_path, "c.json", art()), _write(tmp_path, "d.json", art())])
    assert r.returncode == 0 and json.loads(r.stdout[r.stdout.index("\n{\n"):])["lineage"]["ok"] is True
    r = _run(["--chain", a, b])
    assert r.returncode == 0 and r.stdout.startswith("gate_e1")
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["verdict"] in ("GO", "NO-GO")


def test_the_script_exits_two_on_a_bad_call(tmp_path):
    assert _run([]).returncode == 2
    assert _run([str(tmp_path / "nope.json")]).returncode == 2
    assert _run(["--chain"]).returncode == 2
    assert _run(["a", "b", "c"]).returncode == 2
    assert EG.finite(float("inf")) is None and EG.finite({"a": [float("nan"), 1]}) == {"a": [None, 1]}
