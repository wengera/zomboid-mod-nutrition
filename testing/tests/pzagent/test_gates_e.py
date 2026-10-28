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
    assert lines[0].startswith("gate_e1 NO-GO: alive_through 100.0 >= 1440.0 FAIL") and any(l.startswith("sleep:") for l in lines)


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


# ---------------------------------------------------------------- fix round 1
def test_t_loop0_ms_pairs_an_eat_the_anchor_mispairs():
    a = good()
    a["loop"]["wallS"] = 104.0                                   # the stop came 5 s after the last frame (99 s)
    a["stop"]["wallS"] = 104.0
    n = E.grade_e1(a)["needs"]
    assert n["time_base"] == "anchor" and n["eat"]["stat_fell"] is False          # frames placed 5 s late
    a["loop"]["t_loop0_ms"] = 1_000_000
    n = E.grade_e1(a)["needs"]
    assert n["time_base"] == "t_loop0_ms" and n["eat"]["stat_fell"] is True
    assert E.grade_e1(art([]))["needs"]["time_base"] is None


def test_report_prints_unknown_consumes_and_each_gate_value():
    a = good(1510.0)
    a["loop"]["actions"].append(act("consume", 50, 52))
    g = E.grade_e1(a)
    assert g["needs"]["unknown"] == 1
    g["gate"] = E.gate_e1([a])
    lines = E.report_lines_e(g)
    assert "alive_through 1510.0 >= 1440.0 ok" in lines[0] and "drink_done 1 >= 1 ok" in lines[0]
    assert any(l.startswith("unknown consumes (no valid use): 1") for l in lines)


def test_the_death_window_opens_on_the_wound_arms_own_rise():
    a = _death_art(300, wound_at=100, health_from=105)
    for f in a["loop"]["last_frames"][100:]:
        f["body"]["bleeding"] = 2                                # 1 -> 2: no rise the wound arm reads
    a["loop"]["last_frames"][50]["body"]["parts"] = [{"i": 1, "h": 90.0}]       # a parts-only wound, earlier
    d = E.grade_e1(a)["death"]
    assert d["first_wound_seq"] == 51 and d["window_frames_n"] == 251


def test_the_first_death_in_the_chain_is_graded():
    d = _death_art(300, wound_at=100, health_from=105)
    r = E.gate_e1([d, good()])
    assert r["gates"]["death_explained"]["ok"] is True
    for f in d["loop"]["last_frames"]:
        f["zombies"] = []
    d["loop"]["death"]["last_frames"] = d["loop"]["last_frames"]
    assert E.gate_e1([d, good()])["gates"]["death_explained"]["ok"] is False


# ---------------------------------------------------------------- fix round 2 (P23-X)
def test_the_drivers_loop_lineage_wins_over_a_rebuild():
    prev = art()
    a = art(lineage={"ok": True, "position": {"d": 0.0}})
    a["loop"]["last_frames"][0]["me"]["x"] = 999.0              # the kept first frame would disagree
    g = E.grade_e1(a, prev)
    assert g["lineage_source"] == "loop" and g["lineage"]["ok"] is True
    assert E.gate_e1([prev, a])["verdict"] == "NO-GO"           # reads without raising
    b = art()
    b["loop"]["last_frames"][0]["me"]["x"] = 999.0
    g = E.grade_e1(b, prev)
    assert g["lineage_source"] == "rebuilt" and g["lineage"]["ok"] is False
    g = E.grade_e1(art())
    assert g["lineage_source"] is None and g["lineage"] is None
    assert E.grade_e1(art(lineage=None), prev)["lineage_source"] == "rebuilt"


# ---------------------------------------------------------------- fix wave G (C-2, I-2, I-5)
def _aged(first_age, last_age, **kw):
    """A session whose last kept frame stands at worldAge last_age (hours); the gameMin clock is the time of day."""
    a = art(**kw)
    a["loop"]["last_frames"][-1]["worldAge"] = last_age
    return a


def test_minutes_read_off_worldage_across_midnight():
    a = _aged(0, 31.0, game_min=60.0, first=1380.0, first_world_age=7.0)    # 23:00 to 01:00 on the clock, 24 h in age
    g = E.grade_e1(a)
    assert g["game_minutes"] == pytest.approx(1440.0) and g["minutes_source"] == "loop.first_world_age"
    a = _aged(0, 31.0, game_min=60.0, first=1380.0)
    a["readings"] = {"hello": {"first_frame": {"worldAge": 7.0}}}
    g = E.grade_e1(a)
    assert g["game_minutes"] == pytest.approx(1440.0) and g["minutes_source"] == "readings.hello.first_frame"


def test_minutes_fall_back_to_a_wrap_safe_gamemin_difference():
    g = E.grade_e1(art(game_min=60.0, first=1380.0))              # no worldAge source: 23:00 to 01:00
    assert g["game_minutes"] == 120.0 and g["minutes_source"] == "gameMin"
    assert E.grade_e1(art(game_min=900.0, first=100.0))["game_minutes"] == 800.0
    assert E.grade_e1(art(first=None))["minutes_source"] is None
    r = E.gate_e1([art(game_min=60.0, first=1380.0)])
    assert r["gates"]["alive_through"]["value"] == 120.0           # positive, not -1320


def test_report_line_names_the_minutes_source():
    lines = E.grade_e1(art(game_min=900.0, first=100.0))["report_lines"]
    assert any("800 game min (gameMin)" in l for l in lines)


def _fight(ticks=5, end=True, flee=None):
    return {"fight_ticks": ticks, "flee": flee or {}, "end": {"health": 90} if end else None}


def test_fights_resolved_gate_fails_a_stand_off_and_an_unended_fight():
    ok = good(1440.0, fights=[_fight(), _fight(30, end=True, flee={"stalled": 2})])
    r = E.gate_e1([ok])
    assert r["gates"]["fights_resolved"] == {"ok": True, "value": 0, "threshold": 0, "n": 1}
    so = good(1440.0, fights=[_fight(), _fight(30, end=False, flee={"unreachable": 1})])
    r = E.gate_e1([so])
    assert r["gates"]["fights_resolved"]["ok"] is False and r["verdict"] == "NO-GO"
    # an open fight that is not the last, or in a session not stopped at the cap, is unresolved
    assert E.gate_e1([good(1440.0, fights=[_fight(end=False), _fight()])])["gates"]["fights_resolved"]["value"] == 1
    d = good(1440.0, fights=[_fight(end=False)])
    d["stop"]["reason"] = "budget"
    assert E.gate_e1([d])["gates"]["fights_resolved"]["ok"] is False


def test_the_last_open_fight_of_a_day_cap_session_is_cut_by_the_cap():
    cut = good(1440.0, fights=[_fight(), _fight(8, end=False)])
    assert E.gate_e1([cut])["gates"]["fights_resolved"]["ok"] is True
    assert E.grade_e1(cut)["fights_unresolved"] == 0
    # and across the chain the unresolved count sums
    bad = good(1440.0, fights=[_fight(end=False), _fight()])
    assert E.gate_e1([bad, bad])["gates"]["fights_resolved"]["value"] == 2
    lines = E.report_lines_e(dict(E.grade_e1(bad), gate=E.gate_e1([bad])))
    assert "fights_resolved 1 unresolved FAIL" in lines[0] and any("unresolved 1" in l for l in lines[1:])


def test_death_window_reports_frames_and_truncation():
    a = _death_art(3000, wound_at=100, health_from=2990)     # a wound far before the old 300-frame tail
    d = E.grade_e1(a)["death"]
    assert d["first_wound_seq"] == 101 and d["window_frames"] == 2901 and d["window_truncated"] is False
    a = _death_art(300, wound_at=1, health_from=100)         # the first wound is the first row the window can see
    assert E.grade_e1(a)["death"]["window_truncated"] is True
    a = _death_art(300, wound_at=0, health_from=100)         # bleeding already on in the first kept frame
    assert E.grade_e1(a)["death"]["window_truncated"] is True


def test_gate_names_each_artifacts_lineage_source():
    r = E.gate_e1([art(), art(lineage={"ok": True}), art()])
    assert r["lineage_sources"] == [None, "loop", "rebuilt"]
