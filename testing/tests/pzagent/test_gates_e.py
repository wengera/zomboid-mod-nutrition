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


def _run(args, script="e_grade_2.py"):
    """The pass-2 script by default (e_grade.py is frozen with grade_e1: review I1)."""
    return subprocess.run([sys.executable, os.path.join(os.path.dirname(E.__file__), "..", "drivers", script)]
                          + args, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(HERE)))


def test_the_script_prints_lines_then_strict_json(tmp_path):
    a = _write(tmp_path, "a.json", good())
    b = _write(tmp_path, "b.json", good())
    r = _run([a])
    assert r.returncode == 0
    body = r.stdout[r.stdout.index("\n{\n"):]
    assert json.loads(body)["grade"] == "grade_e2" and r.stdout.startswith("survived")
    r = _run([_write(tmp_path, "c.json", art()), _write(tmp_path, "d.json", art())])
    assert r.returncode == 0 and json.loads(r.stdout[r.stdout.index("\n{\n"):])["lineage"]["ok"] is True
    r = _run(["--chain", a, b])
    assert r.returncode == 0 and r.stdout.startswith("gate_e2")
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


# ---------------------------------------------------------------- PZA/1.3: grade_e2, the death signal (ruling P23-AO)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FROZEN_AT = "a029dfab"                    # grade_e1's last commit before PZA/1.3 (CLAUDE.md § 5 freezing)


def _event_death_art():
    """The fourth chain's shape: the health fell and froze at seq 290; the event's frame (frameSeq) is 290."""
    a = _death_art(300, wound_at=100, health_from=280)        # 100 down to 5 over seq 281..300
    fr = a["loop"]["last_frames"]
    for f in fr[290:]:
        f["body"]["health"] = fr[289]["body"]["health"]      # frozen from seq 290 on
    a["loop"]["death"].update(via="event", frame={"signal": "event", "seq": 289, "health": 50.0, "frameSeq": 290})
    return a


def test_the_death_check_names_the_signal_that_ended_the_session():
    for via, signal in (("frame", "frame_health"), ("players", "players"), ("event", "event"), (None, None)):
        a = _death_art(300, wound_at=100, health_from=105)
        if via is not None:
            a["loop"]["death"]["via"] = via
        g = E.grade_e2(a)
        assert g["grade"] == "grade_e2" and g["death"]["check"]["signal"] == signal, via
        assert any(l.startswith("death (signal %s) explained" % signal) for l in g["report_lines"]), via
    assert E.grade_e2(art())["death"] is None


def test_an_event_death_ends_the_window_at_the_events_frame():
    """grade_e2: the frozen frames after the event's frame, read until the stop settled, are no part of the window."""
    a = _event_death_art()
    fr = a["loop"]["last_frames"]
    d = E.grade_e2(a)["death"]
    assert d["check"]["signal"] == "event" and d["first_wound_seq"] == 101
    assert d["window_frames_n"] == 191 and d["check"]["frames_window_ms"]["to"] == fr[289]["wallMs"]
    assert E.grade_e1(a)["death"]["window_frames_n"] == 201 and "signal" not in E.grade_e1(a)["death"]["check"]
    a["loop"]["death"]["frame"]["frameSeq"] = None            # the event's frame never read: every kept frame
    assert E.grade_e2(a)["death"]["window_frames_n"] == 201


def test_grade_e2_is_grade_e1_but_for_its_name_the_death_and_the_report():
    for a in (good(), _death_art(300, wound_at=100, health_from=105), _event_death_art()):
        e1, e2 = E.grade_e1(a), E.grade_e2(a)
        assert {k: v for k, v in e1.items() if k not in ("grade", "death", "report_lines")} == \
            {k: v for k, v in e2.items() if k not in ("grade", "death", "report_lines")}


def test_gate_e2_is_gate_e1_over_grade_e2():
    d = _event_death_art()
    assert E.gate_e2([good(), d])["gates"]["death_explained"]["value"] == E.grade_e2(d)["death"]["explained"]
    for outs in ([good(700.0), good(740.0)], [good(1439.0)], [good(), _death_art(300, wound_at=100, health_from=105)],
                 [], None):
        assert E.gate_e2(outs) == E.gate_e1(outs)
    lines = E.report_lines_e2(dict(E.grade_e2(good()), gate=E.gate_e2([good(100.0)])))
    assert lines[0].startswith("gate_e2 NO-GO: alive_through 100.0 >= 1440.0 FAIL")


def _frozen_gates_e(tmp_path):
    """gates_e.py as committed at FROZEN_AT, imported from a scratch file; the git read runs in the scrubbed
    environment (tools/tests/gitenv.scrubbed_env), and the test skips when the object is unavailable (review M3)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gitenv", os.path.join(REPO, "tools", "tests", "gitenv.py"))
    gitenv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gitenv)
    try:
        r = subprocess.run(["git", "show", "%s:testing/agent/base/gates_e.py" % FROZEN_AT], cwd=REPO,
                           capture_output=True, env=gitenv.scrubbed_env())
    except OSError as e:
        pytest.skip("git is not runnable here: %s" % e)
    if r.returncode != 0 or not r.stdout:
        pytest.skip("%s:testing/agent/base/gates_e.py is unavailable in this checkout" % FROZEN_AT)
    src = r.stdout
    path = tmp_path / "gates_e_frozen.py"
    path.write_bytes(src)
    spec = importlib.util.spec_from_file_location("gates_e_frozen", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_grade_e1_and_gate_e1_answer_byte_for_byte_as_at_their_freeze(tmp_path):
    F = _frozen_gates_e(tmp_path)
    arts = [good(), art(), art(stop="budget"), _death_art(300, wound_at=100, health_from=105), _event_death_art(),
            _death_art(300, wound_at=999, health_from=100)]
    for a in arts:
        assert json.dumps(E.grade_e1(a), sort_keys=True) == json.dumps(F.grade_e1(a), sort_keys=True)
    assert json.dumps(E.gate_e1(arts)) == json.dumps(F.gate_e1(arts))


E_ARTIFACTS = (("e_day-20261028-110422", "e_day"), ("e_day_2-20261028-124249", "e_day_2"),
               ("e_day_3-20261028-153631", "e_day_3"), ("e_day_4-20261028-173649", "e_day_4"))


@pytest.mark.parametrize("run_id,key", E_ARTIFACTS)
def test_the_frozen_e_grade_reproduces_each_e_artifacts_committed_report_byte_for_byte(run_id, key):
    """e_grade.py run bare, as each guide's command line documents it (review I1)."""
    d = os.path.join(REPO, "testing", "artifacts", run_id)
    if not os.path.isfile(os.path.join(d, "e_grade.txt")):
        pytest.skip("%s is not checked out" % run_id)
    r = subprocess.run([sys.executable, os.path.join(REPO, "testing", "agent", "drivers", "e_grade.py"),
                        os.path.join(d, key + ".json")], capture_output=True, cwd=REPO)
    assert r.returncode == 0
    with open(os.path.join(d, "e_grade.txt"), "rb") as fh:
        want = fh.read()
    assert r.stdout == want                                   # CRLF both: the artifacts were printed on this host


# ================================================================ pass 3: real wounds and the care readings (Plan 24 Task 11)
BANDAGED = {"i": 3, "h": 100.0, "bleeding": False, "bleedingTime": 0.0, "bandaged": True, "bandageLife": 40.0,
            "bandageDirty": False, "deep": False, "infected": False}


def _bandage_art(part, n=300, at=100, stop="day_cap"):
    """n frames; from frame `at` on the body lists `part` and nothing else changes (no rise in bleeding, scratched or
    bitten, health full): the shape of a bandage laid on a part at full health."""
    fr = [frame(i + 1, i, **{"body": {"health": 100.0, "bleeding": 0, "scratched": 0, "bitten": 0,
                                       "parts": [part] if i >= at else []}}) for i in range(n)]
    return art(fr, stop=stop)


def test_a_bandage_on_a_full_health_part_is_a_wound_to_the_old_reading_and_none_to_pass_3():
    a = _bandage_art(BANDAGED)
    w = E.e_wounds(a)
    assert w == {"real": 0, "listed": 1, "first_seq": None, "frames": 300}
    assert GT._wound(a["loop"]["last_frames"][99], a["loop"]["last_frames"][100]) == "part 3 appears at 100.0"
    # the death window: a death after such a bandage opens at the bandage under pass 2, at no wound under pass 3
    d = _bandage_art(BANDAGED, stop="death")
    d["loop"]["death"] = {"last_frames": d["loop"]["last_frames"], "server_damage": []}
    assert E.grade_e2(d)["death"]["first_wound_seq"] == 101 and E.grade_e2(d)["death"]["window_frames_n"] == 201
    g3 = E.grade_e3(d)["death"]
    assert g3["first_wound_seq"] is None and g3["window_frames_n"] == 300


def test_pass_3_counts_a_part_that_carries_a_wound_and_a_rise_in_the_body_counts():
    for part in (dict(BANDAGED, h=90.0), dict(BANDAGED, bleeding=True), dict(BANDAGED, deep=True),
                 dict(BANDAGED, infected=True)):
        w = E.e_wounds(_bandage_art(part))
        assert w["real"] == 1 and w["listed"] == 1 and w["first_seq"] == 101, part
    rise = art(series(100, body=lambda i: {"health": 100.0, "bleeding": 0, "scratched": 1 if i >= 30 else 0,
                                           "bitten": 0, "parts": []}))
    assert E.e_wounds(rise)["real"] == 1 and E.e_wounds(rise)["first_seq"] == 31
    fall = [dict(BANDAGED, h=90.0)]
    lower = art(series(100, body=lambda i: {"health": 100.0, "bleeding": 0, "scratched": 0, "bitten": 0,
                                            "parts": [dict(fall[0], h=90.0 if i < 50 else 80.0)]}))
    assert E.e_wounds(lower)["real"] == 1 and E.e_wounds(lower)["first_seq"] == 51      # h 90 -> 80 on a listed part
    assert E.real_frame(frame(1))["body"]["parts"] == [] and frame(1)["body"]["parts"] == []
    f = frame(1, body={"health": 100.0, "bleeding": 0, "scratched": 0, "bitten": 0, "parts": [BANDAGED]})
    assert E.real_frame(f)["body"]["parts"] == [] and f["body"]["parts"] == [BANDAGED]       # a copy


def test_pass_3_reads_missing_and_malformed_artifacts_as_empty():
    for bad in ({}, None, "x", {"loop": {"last_frames": [None, 5], "actions": "x", "results": 3, "fights": [None]}}):
        g = E.grade_e3(bad)
        assert g["grade"] == "grade_e3" and g["wounds"]["real"] == 0
        assert g["care"]["bandage"]["done"] == 0 and g["care"]["standing"]["n"] == 0


def res(aid, type_, result, state="done"):
    return {"aid": aid, "type": type_, "state": state, "result": result}


def aact(aid, type_, sent, end, state="done", reason="", args=None, **extra):
    return dict({"aid": aid, "type": type_, "args": args or {}, "state": state, "reason": reason, "sentS": sent,
                 "endedS": end, "branch": "care"}, **extra)


def care_art():
    acts = [aact("b1", "bandage", 1, 2, args={"itemId": 9, "part": -1}),
            aact("b2", "bandage", 3, 4, args={"itemId": 9, "part": 5}),
            aact("b3", "bandage", 5, 6, state="failed", reason="no wound", args={"itemId": 9}),
            aact("r1", "rip", 7, 8), aact("w1", "wash", 9, 10, args={"itemId": 8, "x": 1, "y": 2}),
            aact("f1", "fill", 11, 12), aact("f2", "fill", 13, 14), aact("f3", "fill", 15, 16, state="failed"),
            aact("c1", "climb", 17, 18), aact("c2", "climb", 19, 20, state="failed", reason="fell"),
            aact("i1", "interact", 21, 22, args={"x": 1, "y": 1, "kind": "loot", "filter": "container"}),
            aact("i2", "interact", 23, 24, args={"x": 1, "y": 1, "kind": "loot", "filter": "food"}),
            aact("i3", "interact", 25, 26, args={"x": 1, "y": 1, "kind": "open"}),
            aact("a1", "aim", 30, 32), aact("a2", "aim", 33, 35), aact("a3", "aim", 36, 37, state="failed")]
    results = [res("b1", "bandage", {"part": 2, "dirty": True, "life": 0.0}),
               res("b2", "bandage", {"part": 5, "dirty": False, "life": 40.0}),
               res("r1", "rip", {"rags": 3, "dirty": 1}), res("w1", "wash", {"water": 7}),
               res("f1", "fill", {"amount": 1.0, "added": 1.0, "fluid": "Water", "tainted": False}),
               res("f2", "fill", {"amount": 2.0, "added": 1.0, "fluid": "TaintedWater", "tainted": True}),
               res("c1", "climb", {"tall": True, "wounds": 1}), res("i1", "interact", {"moved": 4}),
               res("i2", "interact", {"moved": 9}),
               res("a1", "aim", {"d": 1.5, "held": True, "targetDead": False}),
               res("a2", "aim", {"d": 2.0, "held": False, "targetDead": True})]
    frames = series(100, me=lambda i: dict(DEFAULT_FRAME["me"], aiming=i % 4 == 0))
    return art(frames, acts, results=results)


def test_the_care_readings_count_the_actions_by_state_and_their_results():
    c = E.grade_e3(care_art())["care"]
    assert c["bandage"] == {"sent": 3, "done": 2, "failed": 1, "by_part": {"2": 1, "5": 1}, "dirty": 1}
    assert c["rip"] == {"sent": 1, "done": 1, "rags": 3, "dirty_rags": 1}
    assert c["wash"] == {"sent": 1, "done": 1, "water": 7}
    assert c["fill"]["sent"] == 3 and c["fill"]["done"] == 2 and c["fill"]["tainted"] == 1
    assert c["fill"]["fills"] == [{"fluid": "Water", "tainted": False, "added": 1.0, "amount": 1.0},
                                  {"fluid": "TaintedWater", "tainted": True, "added": 1.0, "amount": 2.0}]
    assert c["stance"] == {"aim_sent": 3, "aim_done": 2, "aim_failed": 1, "held_at_end": 1, "released": 1,
                           "target_dead": 1, "moved": 3.5, "frames_aiming": 25, "frames": 100}
    assert c["climb"] == {"sent": 2, "done": 1, "fell": 1, "failed": 0, "wounds": 1, "tall": 1}
    assert c["loot"] == {"sent": 2, "done": 2, "containers": 1, "containers_moved": 4}
    assert c["need_chain"] == {"drink_done": 0, "drink_stat_fell": None, "fills_done": 2, "containers_looted": 1}


def test_the_care_without_the_results_key_counts_the_actions_and_skips_the_result_fields():
    a = care_art()
    del a["loop"]["results"]
    c = E.grade_e3(a)["care"]
    assert c["bandage"]["done"] == 2 and c["bandage"]["by_part"] == {"-1": 1, "5": 1}      # the args' part, else
    assert c["rip"]["rags"] == 0 and c["fill"]["tainted"] == 0 and c["stance"]["held_at_end"] == 0


def _stand(first, end=True, flee=None, start=100.0, stop=130.0):
    return {"startS": start, "ticks": 5, "fight_ticks": 5, "flee": flee or {}, "threats_max": 1,
            "end": {"endS": stop, "branch": "need"} if end else None}


def test_a_standing_fight_is_one_whose_first_action_is_an_aim_and_has_one_outcome():
    acts = [aact("a1", "aim", 101, 110), aact("t1", "attack", 111, 112),                         # 0: kill
            aact("a2", "aim", 201, 220, state="failed", reason="interrupted"), aact("w1", "walkTo", 221, 225),  # 1: fallback
            aact("a3", "aim", 301, 310), aact("t2", "attack", 311, 312),                         # 2: stagger
            aact("a4", "aim", 401, 410),                                                         # 3: flee
            aact("t3", "attack", 501, 502), aact("a5", "aim", 503, 510),                         # 4: not standing
            aact("a6", "aim", 601, 610)]                                                         # 5: none
    results = [res("t1", "attack", {"swings": 1, "attackStarted": True, "targetDead": True}),
               res("t2", "attack", {"swings": 1, "attackStarted": True, "targetDead": False})]
    fights = [_stand(0, start=100, stop=120), _stand(0, start=200, stop=230), _stand(0, start=300, stop=320),
              _stand(0, start=400, stop=420, flee={"health": 2}), _stand(0, start=500, stop=520),
              _stand(0, start=600, stop=620)]
    a = art(actions=acts, fights=fights, results=results)
    s = E.grade_e3(a)["care"]["standing"]
    assert s["n"] == 5 and s["outcomes"] == {"kill": 1, "flee": 1, "fallback": 1, "stagger": 1, "none": 1}
    assert [r["outcome"] for r in s["rows"]] == ["kill", "fallback", "stagger", "flee", "none"]
    assert [r["fight"] for r in s["rows"]] == [0, 1, 2, 3, 5]
    # an open fight (no end) takes the actions after its start
    o = art(actions=[aact("a1", "aim", 101, 110)], fights=[_stand(0, end=False, start=100)])
    assert E.grade_e3(o)["care"]["standing"]["n"] == 1


def test_grade_e3_is_grade_e2_but_for_its_name_the_death_the_wounds_the_care_and_the_report():
    for a in (good(), _death_art(300, wound_at=100, health_from=105), _event_death_art(), care_art()):
        e2, e3 = E.grade_e2(a), E.grade_e3(a)
        keep = lambda g: {k: v for k, v in g.items() if k not in ("grade", "death", "report_lines", "wounds", "care")}
        assert keep(e2) == keep(e3) and e3["grade"] == "grade_e3" and "care" not in e2
    d = _death_art(300, wound_at=100, health_from=105)           # a real rise: pass 3 reads the same window as pass 2
    assert E.grade_e3(d)["death"] == E.grade_e2(d)["death"]


def test_gate_e3_is_gate_e2_over_grade_e3_and_its_lines_name_it():
    d = _event_death_art()
    assert E.gate_e3([good(), d])["gates"]["death_explained"]["value"] == E.grade_e3(d)["death"]["explained"]
    for outs in ([good(700.0), good(740.0)], [good(1439.0)], [good(), _death_art(300, wound_at=100, health_from=105)],
                 [], None):
        assert E.gate_e3(outs) == E.gate_e2(outs)
    lines = E.report_lines_e3(dict(E.grade_e3(care_art()), gate=E.gate_e3([good(100.0)])))
    assert lines[0].startswith("gate_e3 NO-GO: alive_through 100.0 >= 1440.0 FAIL")
    assert any(l.startswith("wounds: 0 real over 100 kept frames (the old reading counted 0)") for l in lines)
    assert any(l.startswith("care: bandage sent 3 done 2") for l in lines)
    assert any(l.startswith("stance: aim sent 3 done 2 failed 1 (held 1, released 1, target dead 1), 25 of 100") for l in lines)
    assert any(l.startswith("climb: sent 2 done 1 fell 1 failed 0 wounds 1; need chain") for l in lines)


def test_the_pass_3_script_prints_lines_then_strict_json_and_exits_two_on_a_bad_call(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(care_art()), encoding="utf-8")
    script = os.path.join(HERE, "..", "..", "agent", "drivers", "e_grade_3.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and "\ncare: bandage sent 3 done 2" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e3"
    c = subprocess.run([sys.executable, script, "--chain", str(p), str(p)], capture_output=True, text=True, cwd=cwd)
    assert c.returncode == 0 and c.stdout.startswith("gate_e3 ")
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2


# ================================================================ pass 4: kills the headline (Plan 24 Task 17)
def _kill_art(engine=2, planner_ids=(11,), twice=True, dead=True):
    """A session of two standing fights: fight 0 kills 11 (an attack and then an aim of the same id read dead when
    `twice`), fight 1 ends with the care; a death event carrying zombiesKilled `engine` when `dead`."""
    acts = [aact("a1", "aim", 101, 110, args={"targetId": planner_ids[0]}),
            aact("t1", "attack", 111, 112, args={"targetId": planner_ids[0]}),
            aact("a2", "aim", 201, 210, args={"targetId": 12})]
    results = [res("t1", "attack", {"attackStarted": True, "targetDead": True})]
    if twice:
        results.append(res("a1", "aim", {"held": False, "targetDead": True, "heldFrames": 3, "ticks": 4}))
    fights = [dict(_stand(0, start=100, stop=120)),
              dict(_stand(0, start=200, stop=220), end={"endS": 220.0, "branch": "care"})]
    a = art(actions=acts, fights=fights, results=results, stop="death" if dead else "day_cap")
    if dead:
        a["loop"]["death"] = {"via": "event", "gameMin": 605.0, "frame": {"signal": "event"},
                              "event": {"seq": 9, "zombiesKilled": engine}, "last_frames": a["loop"]["last_frames"],
                              "server_damage": []}
        a["stop"]["gameMin"] = 605.0
    return a


def test_the_kills_read_the_engines_count_beside_the_planners_distinct_ids():
    k = E.grade_e4(_kill_art(engine=2))["kills"]
    assert k["engine"] == 2 and k["planner"] == 1 and k["planner_ids"] == [11]          # two results of one id count once
    assert k["per_fight"] == [1, 0] and k["standing_fights"] == 2 and k["standing_kills"] == 1
    assert k["per_standing_fight"] == 0.5 and k["died"] is True and k["died_at"] == 605.0
    s = E.grade_e4(_kill_art(dead=False))["kills"]
    assert s["engine"] is None and s["died"] is False and s["died_at"] is None and s["planner"] == 1
    assert E.grade_e4({})["kills"]["planner"] == 0 and E.grade_e4(None)["kills"]["per_standing_fight"] is None


def test_the_report_opens_with_the_kills_line_naming_both_counts():
    g = E.grade_e4(_kill_art(engine=2))
    assert g["report_lines"][0] == "kills 2 (engine 2, planner 1); died at 605; %s game minutes" % E._f(
        g["game_minutes"], "%.1f")
    s = E.grade_e4(_kill_art(dead=False))
    assert s["report_lines"][0].startswith("kills 1 (engine n/a, planner 1); survived; ")
    lines = E.report_lines_e4(dict(g, gate=E.gate_e4([_kill_art()])))
    assert lines[0].startswith("kills 2 (") and lines[1].startswith("gate_e4 ")


def test_gate_e4_is_gate_e3_and_sums_the_kills():
    for outs in ([good(700.0), good(740.0)], [good(1439.0)], [], None):
        g4 = E.gate_e4(outs)
        assert {k: v for k, v in g4.items() if k != "kills"} == E.gate_e3(outs)
    assert E.gate_e4([_kill_art(engine=3), _kill_art(dead=False)])["kills"] == {"engine": 3, "planner": 2}
    assert E.gate_e4([_kill_art(dead=False)])["kills"] == {"engine": None, "planner": 1}


def test_the_stance_held_reads_the_lua_count_per_aim_leg_beside_the_frames():
    acts = [aact("a1", "aim", 1, 2), aact("a2", "aim", 3, 4), aact("a3", "aim", 5, 6)]
    results = [res("a1", "aim", {"held": True, "heldFrames": 8, "ticks": 10}),
               res("a2", "aim", {"held": True, "heldFrames": 0, "ticks": 5}), res("a3", "aim", {"held": True})]
    frames = series(20, me=lambda i: dict(DEFAULT_FRAME["me"], aiming=i < 3, forceAim=i < 10))
    s = E.grade_e4(art(frames, acts, results=results))["stance_held"]
    assert s["legs"] == 3 and s["with_field"] == 2 and s["ticks"] == 15 and s["held_frames"] == 8
    assert s["ratio"] == 8 / 15 and s["per_leg"][1] == {"aid": "a2", "heldFrames": 0, "ticks": 5}
    assert (s["frames_aiming"], s["frames_force_aim"], s["frames"]) == (3, 10, 20)
    assert E.grade_e4(art())["stance_held"]["ratio"] is None


def test_a_riding_bandage_ended_stopped_counts_under_stopped_and_apart_from_the_standing_ones():
    acts = [aact("b1", "bandage", 1, 2, args={"itemId": 9, "part": 3, "keepMoving": True}),
            aact("b2", "bandage", 3, 4, state="failed", reason="stopped",
                 args={"itemId": 9, "part": 4, "keepMoving": True}),
            aact("b3", "bandage", 5, 6, state="rejected", reason="leg part",
                 args={"itemId": 9, "part": 12, "keepMoving": True}),
            aact("b4", "bandage", 7, 8, args={"itemId": 9, "part": 2}),
            aact("b5", "bandage", 9, 10, state="failed", reason="no wound", args={"itemId": 9, "keepMoving": False})]
    results = [res("b1", "bandage", {"part": 3, "walking": True}), res("b4", "bandage", {"part": 2})]
    g = E.grade_e4(art(actions=acts, results=results))
    assert g["ride"]["riding"] == {"sent": 3, "done": 1, "walking": 1, "failed": 1, "stopped": 1, "rejected": 1,
                                   "by_part": {"3": 1}}
    assert g["ride"]["standing"] == {"sent": 2, "done": 1, "failed": 1}
    assert "bandages: riding sent 3 done 1 (walking 1) failed 1 (stopped 1) rejected 1" in "\n".join(
        g["report_lines"])


T0 = 1_000_000.0                      # the loop start on the frames clock: frame(i + 1, wall_s) sits at 1_000_000 + wall_s * 1000


def _glide_frames(n, moving, x0=0.0):
    """n frames a tenth of a second apart; me.moving per index from `moving`, x advancing 0.3 a frame."""
    return [frame(i + 1, i / 10.0, me=dict(DEFAULT_FRAME["me"], moving=moving(i), x=x0 + 0.3 * i, y=0.0))
            for i in range(n)]


def test_a_glide_is_a_second_of_moving_false_inside_a_run_leg_and_never_a_trip():
    fr = _glide_frames(40, lambda i: not 10 <= i < 21)                  # frames 10..20: 1.0 s still-reading

    def leg(gait, s=0.0, e=4.0):
        return aact("w1", "steer", s, e, args={"vx": 1, "vy": 0, "seconds": 4, "gait": gait})
    a = art(fr, [leg("sprint")], t_loop0_ms=T0)
    gl = E.grade_e4(a)["glides"]
    assert gl["runs"] == 1 and gl["rows"][0]["seq"] == 11 and abs(gl["rows"][0]["s"] - 1.0) < 1e-9
    assert abs(gl["rows"][0]["tiles"] - 3.0) < 1e-9 and gl["rows"][0]["gait"] == "sprint"
    assert E.grade_e4(art(fr, [leg("run")], t_loop0_ms=T0))["glides"]["runs"] == 1
    assert E.grade_e4(art(fr, [leg("walk")], t_loop0_ms=T0))["glides"]["runs"] == 0                # not a run leg
    assert E.grade_e4(art(fr, [leg("sprint", 0.0, 1.5)], t_loop0_ms=T0))["glides"]["runs"] == 0    # the leg ended before it
    assert E.grade_e4(art(_glide_frames(40, lambda i: not 10 <= i < 15), [leg("sprint")], t_loop0_ms=T0))["glides"]["runs"] == 0
    assert E.grade_e4(art(fr, [], t_loop0_ms=T0))["glides"]["runs"] == 0                           # no leg at all
    assert any(l.startswith("glides (an inference, never a trip): 1 over 3.00 tiles") for l in
               E.grade_e4(a)["report_lines"])


def test_a_glide_run_does_not_span_two_legs():
    fr = _glide_frames(40, lambda i: not 10 <= i < 21)
    legs = [aact("w1", "steer", 0.0, 1.5, args={"gait": "sprint"}),
            aact("w2", "steer", 1.5, 4.0, args={"gait": "sprint"})]
    assert E.grade_e4(art(fr, legs, t_loop0_ms=T0))["glides"]["runs"] == 0


def test_the_care_yield_reads_the_artifact_and_the_decision_log():
    fights = [_stand(0, start=10, stop=20), dict(_stand(0, start=30, stop=40), end={"endS": 40.0, "branch": "care"})]
    a = art(actions=[aact("b1", "bandage", 41, 42)], fights=fights)
    assert E.grade_e4(a)["yields"] == {"care_actions": 1, "fights_ended_by_care": 1}
    log = [{"branch": "care", "inputs": {"branches": {"threat": {"care": True, "nearest": 8.0, "held": 1}}}},
           {"branch": "care", "inputs": {"branches": {"threat": {"care": True, "ride": True}}}},
           {"branch": "care", "inputs": {"branches": {"threat": {}}}},
           {"branch": "threat", "inputs": {"branches": {"threat": {"fight": True, "dead": [5, 6], "kill": 5}}}},
           {"branch": "threat", "inputs": {"branches": {"threat": {"dead": [5]}}}}, {"unparsed": "x"}]
    r = E.decision_readings(log)
    assert r == {"lines": 5, "care_yields": 2, "care_rides": 1, "dead_skips": 2, "dead_ids": [5, 6], "kill_lines": 1}
    g = E.grade_e4(a, None, log)
    assert g["yields"]["log"] == r and any("decision log: 2 yields (1 riding), 2 dead skips of 2 ids" in l
                                           for l in g["report_lines"])
    assert any("no decision log read" in l for l in E.grade_e4(a)["report_lines"])
    assert E.decision_readings(None)["lines"] == 0


def test_the_standing_stagger_is_named_as_the_inference_it_is():
    acts = [aact("a3", "aim", 301, 310, args={"targetId": 4}), aact("t2", "attack", 311, 312, args={"targetId": 4})]
    a = art(actions=acts, fights=[_stand(0, start=300, stop=320)],
            results=[res("t2", "attack", {"attackStarted": True, "targetDead": False})])
    s = E.grade_e4(a)["care"]["standing"]
    assert s["outcomes"] == {"kill": 0, "flee": 0, "fallback": 0, "stagger_inferred": 1, "none": 0}
    assert s["rows"][0]["outcome"] == "stagger_inferred"
    assert E.grade_e3(a)["care"]["standing"]["outcomes"]["stagger"] == 1                # grade_e3 as it was


def test_grade_e4_is_grade_e3_but_for_its_name_the_kills_and_the_pass_4_readings():
    for a in (good(), _death_art(300, wound_at=100, health_from=105), _event_death_art(), care_art()):
        e3, e4 = E.grade_e3(a), E.grade_e4(a)
        drop = ("grade", "report_lines", "kills", "stance_held", "ride", "yields", "glides", "care")
        keep = lambda g: {k: v for k, v in g.items() if k not in drop}
        assert keep(e3) == keep(e4) and e4["grade"] == "grade_e4" and "kills" not in e3
        c3, c4 = dict(e3["care"]), dict(e4["care"])
        c3.pop("standing"), c4.pop("standing")
        assert c3 == c4


def test_the_pass_4_script_prints_the_kills_line_first_then_strict_json_and_reads_the_log(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(_kill_art(engine=2)), encoding="utf-8")
    script = os.path.join(HERE, "..", "..", "agent", "drivers", "e_grade_4.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and r.stdout.startswith("kills 2 (engine 2, planner 1); died at 605; ")
    assert "no decision log read" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e4"
    (tmp_path / "decision.log").write_text(
        json.dumps({"branch": "care", "inputs": {"branches": {"threat": {"care": True}}}}) + "\n", encoding="utf-8")
    r2 = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert "decision log: 1 yields (0 riding)" in r2.stdout
    c = subprocess.run([sys.executable, script, "--chain", str(p), str(p)], capture_output=True, text=True, cwd=cwd)
    assert c.returncode == 0 and c.stdout.startswith("kills ") and "\ngate_e4 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2


# ================================================================ pass 5: the whole session's frames, the engage and destination readings (Plan 24 Task 20)
from agent.base import pza1                                                    # noqa: E402
from .fakemod import square                                                    # noqa: E402

W0 = 1_700_000_000_000                                                         # the loop start on the frames clock (epoch ms)


def _line(kind, seq, wall, **body):
    return pza1.encode(kind, dict(body, seq=seq, tick=seq, wallMs=wall)) + "\n"


def _fline(seq, wall, aiming=False, world_age=8.0, **me):
    f = copy.deepcopy(DEFAULT_FRAME)
    f["me"].update(aiming=aiming, **me)
    f["worldAge"] = world_age
    return _line("frame", seq, wall, **f)


def _mline(seq, wall, squares):
    return _line("map", seq, wall, mode="full", scanId=1, part=1, parts=1, squares=squares, missing=[])


def _state(root, *files):
    """A fresh directory under `root` holding state.log, state.1.log ... from lists of lines (strings)."""
    root.mkdir(parents=True, exist_ok=True)
    for i, lines in enumerate(files):
        (root / ("state.log" if i == 0 else "state.%d.log" % i)).write_text("".join(lines), encoding="utf-8",
                                                                              newline="")
    return str(root)


def _room(x, y, building=1):
    return square(x=x, y=y, room="kitchen", building=building)


def test_the_frames_are_read_from_every_state_log_when_they_sit_beside_the_record(tmp_path):
    d = _state(tmp_path / "two", [_fline(1, W0, aiming=True), _fline(2, W0 + 100, aiming=True)],
               [_fline(3, W0 + 200, aiming=True), _fline(4, W0 + 300, aiming=True)])
    kept = [frame(4, 0.3, **{"me": dict(DEFAULT_FRAME["me"], aiming=False)})]
    a = art(kept, t_loop0_ms=W0)
    g = E.grade_e5(a, state_dir=d)
    assert g["grade"] == "grade_e5" and g["frames_source"] == "state_logs" and g["frames_n"] == 4
    assert g["frames_files"] == ["state.log", "state.1.log"] and g["stance_held"]["frames"] == 4
    assert g["stance_held"]["frames_aiming"] == 4                       # grade_e4 over the kept frame reads 0 of 1
    assert E.grade_e4(a)["stance_held"]["frames"] == 1 and E.grade_e4(a)["stance_held"]["frames_aiming"] == 0
    assert any(l.startswith("frames: state_logs (4 frames, files ['state.log', 'state.1.log'])")
               for l in g["report_lines"])
    only = E.grade_e5(a, state_dir=_state(tmp_path / "one", [_fline(1, W0, aiming=True)]))
    assert only["frames_n"] == 1 and only["frames_files"] == ["state.log"]


def test_a_record_with_no_state_logs_reads_the_kept_frames_and_says_so(tmp_path):
    kept = [frame(i + 1, i / 10.0, **{"me": dict(DEFAULT_FRAME["me"], aiming=True)}) for i in range(5)]
    a = art(kept, t_loop0_ms=W0)
    for g in (E.grade_e5(a), E.grade_e5(a, state_dir=str(tmp_path)), E.grade_e5(a, state_dir=str(tmp_path / "no"))):
        assert g["frames_source"] == "last_frames" and g["frames_files"] == [] and g["frames_n"] == 5
        assert g["stance_held"]["frames_aiming"] == 5
        assert any(l.startswith("frames: last_frames (5 frames)") for l in g["report_lines"])
        assert g["destinations"] == {"read": False} and g["doors"] == {"read": False}


def test_grade_e5_is_grade_e4_but_for_its_name_the_frames_and_the_pass_5_readings():
    for a in (good(), _death_art(300, wound_at=100, health_from=105), care_art()):
        e4, e5 = E.grade_e4(a), E.grade_e5(a)
        drop = ("grade", "report_lines", "frames_source", "frames_files", "frames_n", "engage", "destinations", "doors",
                "loot")
        assert {k: v for k, v in e4.items() if k not in ("grade", "report_lines")} == \
            {k: v for k, v in e5.items() if k not in drop}
        assert e5["grade"] == "grade_e5" and E.gate_e5([a, a]) == E.gate_e4([a, a])


def _walk(aid, sent, x, y, branch="goal"):
    return aact(aid, "walkTo", sent, sent + 1, args={"x": x, "y": y, "gait": "walk"}, branch=branch)


def test_a_walk_off_every_building_fails_the_destinations_field(tmp_path):
    sq = [_room(100 + i, 200 + j) for i in range(4) for j in range(4)]
    d = _state(tmp_path / "m", [_mline(1, W0, sq), _fline(2, W0 + 5000)])
    acts = [_walk("w1", 1.0, 101, 201), _walk("w2", 2.0, 130, 201), _walk("w3", 3.0, 300, 200),
            _walk("w4", 4.0, 120, 200, branch="threat")]                     # a seek or a flee leg is no destination
    g = E.grade_e5(art(actions=acts, t_loop0_ms=W0), state_dir=d)
    ds = g["destinations"]
    assert ds["read"] is True and ds["walks"] == 3 and ds["by_kind"] == {"building": 1, "cluster": 1, "other": 1}
    assert ds["ok"] is False and ds["off_building"][0]["aid"] == "w3" and abs(ds["farthest"] - 196.0) < 1e-9
    assert any("OFF A BUILDING" in l for l in g["report_lines"])
    good_acts = [_walk("w1", 1.0, 101, 201), _walk("w2", 2.0, 130, 201)]
    ok = E.grade_e5(art(actions=good_acts, t_loop0_ms=W0), state_dir=d)["destinations"]
    assert ok["ok"] is True and ok["by_kind"] == {"building": 1, "cluster": 1, "other": 0}
    # a walk is read against the buildings known when it was sent: before the map line there is none known
    early = _state(tmp_path / "e", [_fline(1, W0), _mline(2, W0 + 5000, sq)])
    first = E.grade_e5(art(actions=[_walk("w1", 1.0, 101, 201)], t_loop0_ms=W0), state_dir=early)["destinations"]
    assert first["by_kind"]["other"] == 1 and first["farthest"] is None


def _open(aid, sent, x, y, state="failed", reason="locked"):
    return aact(aid, "interact", sent, sent + 0.5, state=state, reason=reason, args={"kind": "open", "x": x, "y": y},
                branch="goal")


def test_the_second_failure_at_a_door_marks_it_and_a_try_while_marked_fails_the_field(tmp_path):
    sq = [_room(100 + i, 200 + j) for i in range(4) for j in range(4)]
    d = _state(tmp_path / "d", [_mline(1, W0, sq), _fline(2, W0 + 100), _fline(3, W0 + 9000)])
    one = E.grade_e5(art(actions=[_open("o1", 1.0, 101, 200)], t_loop0_ms=W0), state_dir=d)["doors"]
    assert one["read"] is True and one["marks"] == [] and one["ok"] is True
    acts = [_open("o1", 1.0, 101, 200), _open("o2", 2.0, 101, 200)]
    two = E.grade_e5(art(actions=acts, t_loop0_ms=W0), state_dir=d)["doors"]
    assert len(two["marks"]) == 1 and two["marks"][0]["door"] == [101, 200, 0] and two["marks"][0]["reason"] == "locked"
    assert two["tried_marked"] == 0 and two["ok"] is True
    retry = E.grade_e5(art(actions=acts + [_open("o3", 4.0, 101, 200)], t_loop0_ms=W0), state_dir=d)
    assert retry["doors"]["tried_marked"] == 1 and retry["doors"]["ok"] is False
    elsewhere = acts + [_open("o3", 4.0, 102, 200, state="done", reason="")]
    assert E.grade_e5(art(actions=elsewhere, t_loop0_ms=W0), state_dir=d)["doors"]["tried_marked"] == 0
    log = [{"wall": W0 / 1000.0 + 5, "goal": {"type": "LootBuilding", "args": {"building": 2}}},
           {"wall": W0 / 1000.0 + 6, "goal": {"type": "LootBuilding", "args": {"building": 1}}},
           {"wall": W0 / 1000.0 - 5, "goal": {"type": "LootBuilding", "args": {"building": 3}}}]
    around = E.grade_e5(art(actions=acts, t_loop0_ms=W0), decision_lines=log, state_dir=d)
    assert around["doors"]["routes_around"] == [2]           # after the mark, not the stuck building 1, not before it
    assert any(l.startswith("doors: 1 marked stuck") for l in around["report_lines"])


def test_a_door_marked_from_outside_is_no_retry_from_inside_but_is_from_outside_again(tmp_path):
    """Task 20 fix 1, the review's major: the planner's mark is one-sided (Task 18 fix 1); the replay notes the side
    the character stood on (Night.inside) and counts a try only from the marking side."""
    sq = [_room(100 + i, 200 + j) for i in range(4) for j in range(4)]
    d = _state(tmp_path / "s", [_mline(1, W0, sq), _fline(2, W0 + 100, x=50.5, y=50.5),
                               _fline(3, W0 + 3000, x=101.5, y=201.5), _fline(4, W0 + 5000, x=50.5, y=50.5)])
    marked = [_open("o1", 1.0, 101, 200), _open("o2", 2.0, 101, 200)]
    inside = marked + [_open("o3", 4.0, 101, 200, state="done", reason="")]
    g = E.grade_e5(art(actions=inside, t_loop0_ms=W0), state_dir=d)["doors"]
    assert len(g["marks"]) == 1 and g["tried_marked"] == 0 and g["ok"] is True
    again = inside + [_open("o4", 6.0, 101, 200)]
    g = E.grade_e5(art(actions=again, t_loop0_ms=W0), state_dir=d)["doors"]
    assert g["tried_marked"] == 1 and g["ok"] is False


def _tline(branch="threat", fight=None, flee=None, near=None, mode=None, action=None, **why):
    w = dict(why)
    if fight is not None:
        w["fight"] = fight
    if flee is not None:
        w["flee"] = flee
    return {"branch": branch, "action": action, "inputs": {"nearest": near, "mode": mode,
                                                           "branches": {"threat": w}}}


def test_a_sought_fight_is_counted_with_its_seek_legs_and_a_flee_turn():
    walk = {"type": "walkTo", "args": {"gait": "walk", "x": 1, "y": 2}}
    log = [_tline(fight=True, seek=True, near=9.0, action=walk),              # a sought fight: held at 9 tiles
           _tline(fight=True, seek=True, near=8.0, action={"type": "aim", "args": {}}),
           _tline(fight=True, near=2.0),
           _tline(branch="goal"),
           _tline(fight=True, near=3.0, mode="flee"),                          # a fight the flee turned to: not sought
           _tline(flee="many", near=3.0), _tline(flee="many", near=4.0, listed=5), _tline(flee="health"),
           {"unparsed": "x"}]
    en = E.e_engage(log)
    assert en["read"] is True and en["fights"] == 2 and en["fights_sought"] == 1 and en["sought_lines"] == 2
    assert en["seek_lines"] == 2 and en["seek_legs"] == {"walkTo": {"walk": 1}, "aim": 1, "other": 0}
    assert en["seek_walk_share"] == 1.0 and en["flee_turns"] == 1 and en["fight_lines"] == 4
    assert en["flees"] == {"many": 2, "health": 1} and en["many_listed_lines"] == 1 and en["many_listed_max"] == 5
    none = E.e_engage([_tline(flee="many", near=5.0), _tline(fight=True, near=3.0)])
    assert none["fights"] == 1 and none["fights_sought"] == 0 and none["seek_lines"] == 0       # E7: nothing sought
    assert E.e_engage(None) == {"read": False} and E.e_engage([])["fights"] == 0
    g = E.grade_e5(art(), decision_lines=log)
    assert g["engage"] == en and any(l.startswith("engage: 2 fights, 1 sought (2 sought lines); 2 seek lines")
                                     for l in g["report_lines"])
    assert any("engage: no decision log read" in l for l in E.grade_e5(art())["report_lines"])


def test_the_loot_is_counted_by_kind_with_the_failure_reasons():
    def loot(aid, filt, state, reason=""):
        return aact(aid, "interact", 1, 2, state=state, reason=reason, args={"kind": "loot", "filter": filt})
    acts = [loot("l1", "food", "done"), loot("l2", "food", "failed", "not adjacent"),
            loot("l3", "water", "failed", "no match"), aact("o1", "interact", 1, 2, args={"kind": "open"})]
    lt = E.grade_e5(art(actions=acts))["loot"]
    assert lt == {"sent": 3, "done": 1, "failed": 2, "by_kind": {"food": {"done": 1, "failed": 1},
                                                                "water": {"done": 0, "failed": 1}},
                  "failed_reasons": {"not adjacent": 1, "no match": 1}}


def test_the_pass_5_script_reads_the_state_logs_and_the_decision_log_beside_the_artifact(tmp_path):
    kept = [frame(1, 0.0, **{"me": dict(DEFAULT_FRAME["me"], aiming=False)})]
    (tmp_path / "a.json").write_text(json.dumps(art(kept, t_loop0_ms=W0)), encoding="utf-8")
    _state(tmp_path, [_fline(1, W0, aiming=True)], [_fline(2, W0 + 100, aiming=True)])
    (tmp_path / "decision.log").write_text(json.dumps(_tline(fight=True, seek=True, near=9.0)) + "\n", encoding="utf-8")
    script = os.path.join(HERE, "..", "..", "agent", "drivers", "e_grade_5.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "frames: state_logs (2 frames" in r.stdout
    assert "engage: 1 fights, 1 sought" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e5"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=cwd)
    assert c.returncode == 0 and "\ngate_e5 " in c.stdout and "\ngate_e4 " not in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2


# ================================================================ pass 6: the opened fight window, the minutes alive, the iteration 9 and PZA/1.6 readings (Plan 24 Task 23)
E8_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "artifacts", "e_day_8-20261029-174023")


def _fight6(start, end=None, **kw):
    return dict({"startS": start, "end": {"endS": end} if end is not None else None, "fight_ticks": 3}, **kw)


def _stand_art(acts, results=(), fights=None):
    return art(actions=acts, results=list(results), fights=fights or [_fight6(10.0, 20.0)])


def test_the_window_opens_before_the_first_send_so_a_standing_fight_is_standing():
    """E8: the first send precedes the fight's startS by 1.12e-05 to 2.67e-05 s; grade_e5 misses it, so a walk sent
    first leaves the aim as the first action it sees (standing, wrongly) and an aim sent first is missed."""
    aim_first = [aact("a1", "aim", 10.0 - 2.0e-5, 11.0), aact("k1", "attack", 12.0, 13.0)]
    walk_first = [aact("w0", "walkTo", 10.0 - 1.2e-5, 10.5), aact("a2", "aim", 11.0, 12.0)]
    kill = [res("k1", "attack", {"targetDead": True, "attackStarted": True})]
    for acts, n5, n6 in ((aim_first, 0, 1), (walk_first, 1, 0)):
        a = _stand_art(acts, kill)
        assert E.grade_e5(a)["kills"]["standing_fights"] == n5
        g = E.grade_e6(a)
        assert g["kills"]["standing_fights"] == n6 and g["care"]["standing"]["n"] == n6
    a = _stand_art([aact("a1", "aim", 10.0 - 2.0e-5, 11.0, args={"targetId": 7})], [res("a1", "aim", {"targetDead": True})])
    g = E.grade_e6(a)
    assert g["kills"]["per_fight"] == [1] and g["kills"]["standing_kills"] == 1
    assert g["kills"]["per_standing_fight"] == 1.0
    assert E.grade_e5(a)["kills"]["per_fight"] == [0]                    # the older window missed the first send's kill
    assert g["care"]["standing"]["outcomes"] == {"kill": 1, "flee": 0, "fallback": 0, "stagger_inferred": 0, "none": 0}
    far = _stand_art([aact("a1", "aim", 10.0 - 0.002, 11.0)])            # 2 ms early is outside the 1 ms slack
    assert E.grade_e6(far)["kills"]["standing_fights"] == 0
    assert E.FIGHT_WINDOW_SLACK_S == 0.001


@pytest.mark.skipif(not os.path.isdir(E8_DIR), reason="the E8 artifact is not in this tree")
def test_the_e8_artifact_reads_other_standing_fights_under_grade_e6():
    """E8 (e_day_8-20261029-174023): grade_e5 reads fights 0, 1 and 2 as standing (fight 0 began with a walkTo sent
    1.4e-05 s before its startS, so its first aim read as the first action; fight 3's first aim was missed),
    grade_e6 reads fights 1, 2 and 3; the minutes stop at the death event."""
    with open(os.path.join(E8_DIR, "e_day_8.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    r5 = [r["fight"] for r in E.e_standing(o["loop"], E._results(o["loop"]))["rows"]]
    r6 = [r["fight"] for r in E.e_standing_2(o["loop"], E._results(o["loop"]))["rows"]]
    assert r5 == [0, 1, 2] and r6 == [1, 2, 3]
    g = E.grade_e6(o, state_dir=E8_DIR)
    assert g["kills"]["standing_fights"] == 3 and g["kills"]["engine"] == 4
    assert abs(g["game_minutes_log_end"] - 133.0609) < 1e-3 and abs(g["game_minutes_alive"] - 131.5253) < 1e-3


def _alive_art(stop, event_age, last_age, first=1.0):
    fr = [frame(1, 0, worldAge=first), frame(2, 1, worldAge=last_age)]
    a = art(fr, stop=stop, first_world_age=first)
    if stop == "death":
        ev = {"zombiesKilled": 2}
        if event_age is not None:
            ev["worldAge"] = event_age
        a["loop"]["death"] = {"event": ev, "last_frames": fr, "server_damage": []}
    return a


def test_the_minutes_stop_at_the_death_event_and_a_survivor_reads_the_log_end():
    dead = _alive_art("death", 1.5, 2.0)
    g = E.grade_e6(dead)
    assert abs(g["game_minutes_alive"] - 30.0) < 1e-9 and abs(g["game_minutes_log_end"] - 60.0) < 1e-9
    assert g["game_minutes"] == g["game_minutes_alive"] and g["minutes_alive_source"] == "death event"
    assert E.grade_e5(dead)["game_minutes"] == g["game_minutes_log_end"]         # grade_e5 ran past the death
    assert g["report_lines"][0].startswith("kills 2 (engine 2, planner 0); died at")
    assert "30.0 game minutes" in g["report_lines"][0]
    live = E.grade_e6(_alive_art("day_cap", None, 2.0))
    assert live["game_minutes_alive"] == live["game_minutes_log_end"] == live["game_minutes"]
    assert live["minutes_alive_source"] == "loop.first_world_age"
    no_age = E.grade_e6(_alive_art("death", None, 2.0))                          # an event with no worldAge: the log end
    assert no_age["game_minutes_alive"] == no_age["game_minutes_log_end"]


def _cline(stock=None, want=None, sent=True, gm=100):
    care = {}
    if stock is not None:
        care["stock"] = {"reason": "stock", "item": 5, "dressings": stock, "stock": 2}
    if want:
        care["want"] = want
    return {"branch": "care", "gameMin": gm, "sent": sent, "action": None, "inputs": {"branches": {"care": care}}}


def test_the_rag_stock_counts_its_rips_lines_dressings_and_wants():
    acts = [aact("r1", "rip", 1, 2, branch="care"), aact("r2", "rip", 3, 4, state="failed", reason="worn", branch="care"),
            aact("r3", "rip", 5, 6, branch="threat")]
    log = [_cline(stock=0), _cline(stock=1, gm=110), _cline(stock=1, sent=False), _cline(want="bandage"), _cline()]
    g = E.grade_e6(art(actions=acts), decision_lines=log)["rags"]
    assert g["rips"] == {"sent": 3, "done": 2, "failed": 1, "by_branch": {"care": 2, "threat": 1}}
    assert (g["read"], g["stock_lines"], g["stock_sent"], g["want_lines"]) == (True, 3, 2, 1)
    assert g["dressings"] == [{"gameMin": 100, "dressings": 0}, {"gameMin": 110, "dressings": 1}]
    assert (g["dressings_min"], g["dressings_max"]) == (0, 1)
    none = E.grade_e6(art(), decision_lines=[_cline()])["rags"]
    assert none["stock_lines"] == 0 and none["dressings_min"] is None and none["rips"]["sent"] == 0
    assert E.grade_e6(art(actions=acts))["rags"]["read"] is False


def _gline(leg=None, leg_len=None, reason=None, args=None, sent=True):
    gw = {} if leg is None else {"leg": leg, "legLen": leg_len}
    if reason:
        gw["reason"] = reason
    return {"branch": "goal", "sent": sent, "goal": {"type": "ExploreToward", "args": args or {"x": 9, "y": 9}},
            "inputs": {"branches": {"goal": gw}}}


def test_the_legged_walks_count_legs_halvings_failures_and_the_target_kept():
    acts = [aact("w1", "walkTo", 1, 2, state="failed", reason="no square", branch="goal"),
            aact("w2", "walkTo", 3, 4, branch="goal"),
            aact("w3", "walkTo", 5, 6, state="failed", reason="no square", branch="threat")]
    log = [_gline([1, 1], 30.0), _gline([2, 2], 15.0), _gline([3, 3], 10.0), _gline([4, 4], 30.0),
           _gline(reason="no square"), _gline(), _gline([5, 5], 30.0, args={"x": 1, "y": 1}, sent=False)]
    g = E.grade_e6(art(actions=acts), decision_lines=log)["legs"]
    assert g["no_square"] == {"sent": 2, "failed": 1} and g["leg_lines"] == 5 and g["leg_sent"] == 4
    assert g["lens"] == [30.0, 15.0, 10.0, 30.0, 30.0] and g["halvings"] == 2 and g["min_len"] == 10.0
    assert g["goal_no_square_fails"] == 1 and len(g["targets"]) == 2 and abs(g["legs_per_target"] - 2.5) < 1e-9
    none = E.grade_e6(art(), decision_lines=[_gline()])["legs"]
    assert none["leg_lines"] == 0 and none["lens"] == [] and none["legs_per_target"] is None
    assert E.grade_e6(art(actions=acts))["legs"]["read"] is False


def _zl(seq, wall, zombies):
    f = copy.deepcopy(DEFAULT_FRAME)
    f["zombies"] = zombies
    return _line("frame", seq, wall, **f)


def _z(zid, dist, target):
    return {"id": zid, "x": 1.0, "y": 1.0, "dist": dist, "hasTarget": target, "crawler": False, "health": 1.0}


def _many_line(wall_ms, listed=None):
    ln = _tline(flee="many" if listed is None else None, near=4.0, listed=listed)
    ln["wall"] = wall_ms / 1000.0
    return ln


def test_the_idle_many_reads_the_idle_zombies_beyond_danger_r_in_the_nearest_frame(tmp_path):
    d = _state(tmp_path / "z", [_zl(1, W0, [_z(1, 3.0, True), _z(2, 9.5, False), _z(3, 9.9, False), _z(4, 12.5, False)]),
                                _zl(2, W0 + 1000, [_z(1, 3.0, True), _z(5, 5.0, False), _z(6, 8.0, True)])])
    log = [_many_line(W0 + 500), _many_line(W0 + 1500), _many_line(W0 + 600, listed=5), _tline(fight=True, near=3.0)]
    g = E.grade_e6(art(), decision_lines=log, state_dir=d)["idle_many"]
    # the first and third lines read the first frame (9.5 and 9.9 are idle beyond 6 within 12; 12.5 is out), the
    # second the second frame (its idle zombie stands at 5.0, inside DANGER_R: the planner counts it, no reading)
    assert g["read"] is True and g["many_lines"] == 3 and g["with_idle"] == 2 and g["max_idle"] == 2
    assert [r["idle"] for r in g["rows"]] == [2, 2]
    inside = _state(tmp_path / "i", [_zl(1, W0, [_z(1, 3.0, True), _z(2, 5.0, False)])])
    assert E.grade_e6(art(), decision_lines=[_many_line(W0 + 100)], state_dir=inside)["idle_many"]["with_idle"] == 0
    assert E.grade_e6(art(), state_dir=d)["idle_many"] == {"read": False}               # no decision log
    assert E.grade_e6(art(), decision_lines=log)["idle_many"] == {"read": False}        # no frames
    before = _state(tmp_path / "b", [_zl(1, W0 + 9000, [_z(2, 9.5, False)])])          # the frame after the line
    assert E.grade_e6(art(), decision_lines=[_many_line(W0)], state_dir=before)["idle_many"]["with_idle"] == 0


def test_the_pza16_fields_count_clothing_wear_window_worn_and_locked_doors(tmp_path):
    def loot(aid, filt):
        return aact(aid, "interact", 1, 2, args={"kind": "loot", "filter": filt})
    acts = [loot("c1", "clothing"),
            aact("c2", "interact", 1, 2, state="failed", reason="no match", args={"kind": "loot", "filter": "clothing"}),
            loot("f1", "food"), aact("w1", "wear", 3, 4, args={"itemId": 9}),
            aact("w2", "wear", 5, 6, state="failed", reason="busy"), aact("x1", "window", 7, 8),
            aact("x2", "window", 9, 10, state="failed", reason="not a window")]
    results = [res("w1", "wear", {"itemId": 9, "loc": "base:tshirt", "replaced": 4}),
               res("x1", "window", {"smashed": True, "opened": False, "cut": True, "wounds": 1})]
    door = {"open": False, "locked": True, "barricaded": False}
    other = {"open": False, "locked": False, "barricaded": False}
    sq = [square(x=100, y=200, door=door), square(x=101, y=200, door=other), square(x=102, y=200, window=door)]
    d = _state(tmp_path / "p", [_mline(1, W0, sq), _fline(2, W0 + 100), _fline(3, W0 + 200, worn=[])])
    p = E.grade_e6(art(actions=acts, results=results, t_loop0_ms=W0), state_dir=d)["pza16"]
    assert p["clothing_looted"] == {"sent": 2, "done": 1, "failed": 1}
    assert p["wear"] == {"sent": 2, "done": 1, "failed": 1, "reasons": {"busy": 1}, "replaced": 1}
    assert p["window"] == {"sent": 2, "done": 1, "failed": 1, "reasons": {"not a window": 1}, "smashed": 1,
                           "opened": 0, "cut": 1}
    assert p["doors"] == {"read": True, "seen": 3, "locked": 2}
    empty = E.grade_e6(art())["pza16"]
    assert empty["clothing_looted"]["sent"] == 0 and empty["wear"]["sent"] == 0 and empty["window"]["sent"] == 0
    assert empty["worn"] == {"read": False, "max_locs": None, "last": None} and empty["doors"] == {"read": False}


def test_the_worn_list_is_read_off_the_frames_me_worn(tmp_path):
    fr = {"seq": 1, "tick": 1, "wallMs": W0}
    f = copy.deepcopy(DEFAULT_FRAME)
    f["me"]["worn"] = [{"loc": "base:tshirt", "bite": 0.0, "scratch": 5.0, "holes": 0, "cond": 100.0},
                       {"loc": "base:trousers", "bite": 0.0, "scratch": 5.0, "holes": 0, "cond": 100.0}]
    d = _state(tmp_path / "w", [_line("frame", 1, W0, **f), _fline(2, W0 + 100)])
    p = E.grade_e6(art(), state_dir=d)["pza16"]["worn"]
    assert p["read"] is True and p["max_locs"] == 2 and len(p["last"]) == 2


def test_grade_e6_is_grade_e5_but_for_its_name_and_the_pass_6_fields():
    for a in (good(), _death_art(300, wound_at=100, health_from=105), care_art()):
        e5, e6 = E.grade_e5(a), E.grade_e6(a)
        drop = ("grade", "report_lines", "rags", "legs", "idle_many", "pza16", "game_minutes_alive",
                "game_minutes_log_end", "minutes_alive_source")
        assert {k: v for k, v in e5.items() if k not in ("grade", "report_lines")} == \
            {k: v for k, v in e6.items() if k not in drop}
        assert e6["grade"] == "grade_e6" and E.gate_e6([a, a]) == E.gate_e5([a, a])
    assert E.grade_e6({})["grade"] == "grade_e6" and E.grade_e6(None)["rags"]["read"] is False


def test_the_pass_6_script_reads_the_artifact_and_names_the_gate(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(t_loop0_ms=W0)), encoding="utf-8")
    _state(tmp_path, [_fline(1, W0)])
    (tmp_path / "decision.log").write_text(json.dumps(_cline(stock=0)) + "\n", encoding="utf-8")
    script = os.path.join(HERE, "..", "..", "agent", "drivers", "e_grade_6.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "rags: rips" in r.stdout
    assert "stock lines 1" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e6"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=cwd)
    assert c.returncode == 0 and "\ngate_e6 " in c.stdout and "\ngate_e5 " not in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2
