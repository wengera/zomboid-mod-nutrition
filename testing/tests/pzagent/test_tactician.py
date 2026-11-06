"""The tactician variant (Plan 31 Task 11, T: `planner/tactician/`, its README the design record): the plays'
validation, the triggers over a synthetic frame stream, the coalesced and late-validated source (a fake runner, never a
real `claude` call), the fallback doctrine's rules, the cached table, the rubric, and the decider end to end through
`Survive(control="tactician")` on the fake mod."""
import json
import threading

import pytest

from agent.base.planner import policies as PO
from agent.base.planner.survive import Survive
from agent.base.planner.tactician import decide as D
from agent.base.planner.tactician import executors as X
from agent.base.planner.tactician import fallback as F
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician import rubric as R
from agent.base.planner.tactician import source as S
from agent.base.planner.tactician import table as T
from agent.base.planner.tactician import tview as V
from agent.base.planner.tactician.trigger import CLEAR_S, NOTICE_GAP_S, Triggers

from .fakemod import MELEE_CAPS
from .test_night import CLOSED, house
from .test_policies import CRATE, Rig, all_sends_valid, zombie
from .test_survive_g import part


# ================================================================ fixtures
def z(zid, x, y, target=True, floor=False, me=(100.0, 200.0)):
    out = zombie(zid, x, y, me)
    out["hasTarget"] = target
    if floor:
        out["onFloor"] = True
    return out


def zrow(label, dist, posture="standing", targets_me=True, bearing="E", line="clear", zid=None):
    return {"label": label, "id": zid if zid is not None else int(label[1:]) + 100, "bearing": bearing,
            "dist": dist, "closing": 0.5, "posture": posture, "targets_me": targets_me, "known": True,
            "state": "walktoward", "behind": False, "line": line, "health": 1.0}


def mkview(zombies=(), parts=(), armed="Base.BaseballBat", kit=None, doors=(), buildings=(), health=100.0,
           inside=False, goal=None, needs=None):
    k = {"weapon": armed, "cond": 1.0, "bandages": 0, "rags": 0, "dirty_rags": 0, "rip": 0, "unwear": 0, "water": 0,
         "food": 0, "load": 0}
    k.update(kit or {})
    return {"trigger": "notice", "me": {"x": 100.0, "y": 200.0, "health": health, "inside": inside, "building": None,
                                        "armed": armed, "cond": 1.0, "endurance": 1.0, "armPain": 0.0, "hit": None,
                                        "attackers": 0},
            "zombies": list(zombies), "counts": {}, "map": [], "body": {"health": health, "parts": list(parts),
                                                                        "armPain": 0.0},
            "kit": k, "doors": list(doors), "buildings": list(buildings),
            "needs": needs or {"thirst": 0.0, "hunger": 0.0, "fatigue": 0.0, "night": False}, "play": None,
            "last_plays": [], "goal": goal, "refusal": None}


def bleeding_part(i=1, h=50.0):
    return {"label": "P%d" % i, "name": V.PART_NAMES[i], "bleeding": True, "bandaged": False, "dirty": False,
            "deep": False, "wound": True, "h": h}


DOOR = {"label": "D1", "building": "B1", "dist": 5.0, "bearing": "W", "open": False, "locked": False,
        "zombies_near": 0}
BUILDING = {"label": "B1", "dist": 4.0, "bearing": "W", "looted": False, "shelter": True, "zombies_near": 0,
            "here": False}


# ================================================================ the plays and their validation
def test_a_valid_fight_passes_and_carries_its_target():
    v = mkview([zrow("Z1", 3.0)])
    p = P.validate({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}, v)
    assert (p.play, p.target(), p.bound, p.why) == ("fight", "Z1", "dead", "lone_chaser")
    assert p.row() == {"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}


@pytest.mark.parametrize("obj, why", [
    ("fight Z1", "not_object"),
    ({"play": "charge", "target": "Z1", "bound": "dead", "why": "lone_chaser"}, "unknown_play"),
    ({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser", "note": "it is alone"}, "extra_key"),
    ({"play": "fight", "target": "Z1", "bound": "dead"}, "missing_arg"),
    ({"play": "fight", "target": "Z9", "bound": "dead", "why": "lone_chaser"}, "unknown_label"),
    ({"play": "fight", "target": "B1", "bound": "dead", "why": "lone_chaser"}, "bad_arg"),
    ({"play": "fight", "target": [101, 200], "bound": "dead", "why": "lone_chaser"}, "bad_arg"),
    ({"play": "fight", "target": "Z1", "bound": "time", "why": "lone_chaser"}, "bad_bound"),
    ({"play": "fight", "target": "Z1", "bound": "dead", "why": "it is alone"}, "bad_why"),
    ({"play": "avoid", "toward": "D1", "gait": "sprint", "bound": "clear", "why": "group"}, "bad_arg"),
    ({"play": "travel", "to": "B7", "gait": "walk", "bound": "arrived", "why": "clear"}, "unknown_label"),
])
def test_a_bad_answer_is_refused_with_its_closed_why(obj, why):
    v = mkview([zrow("Z1", 3.0)], doors=[DOOR], buildings=[BUILDING])
    with pytest.raises(P.Refused) as e:
        P.validate(obj, v)
    assert e.value.why == why and why in P.REFUSALS


def test_a_free_text_field_is_refused_wherever_it_stands():
    v = mkview([zrow("Z1", 3.0)])
    for k in ("reason", "why_text", "comment"):
        with pytest.raises(P.Refused, match="extra_key"):
            P.validate({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser", k: "x"}, v)


def test_the_meaning_checks_refuse_a_dress_of_a_dry_part_an_unheld_item_a_looted_loot_and_a_shelterless_shelter():
    v = mkview(parts=[bleeding_part(1), dict(bleeding_part(2), bleeding=False)], kit={"bandages": 1},
               buildings=[dict(BUILDING, looted=True, shelter=False)])
    assert P.validate({"play": "dress", "part": "P1", "with": "bandage", "bound": "dressed", "why": "bleeding"}, v)
    for obj, why in (({"play": "dress", "part": "P2", "with": "bandage", "bound": "dressed", "why": "bleeding"},
                      "not_bleeding"),
                     ({"play": "dress", "part": "P1", "with": "rag", "bound": "dressed", "why": "bleeding"}, "no_item"),
                     ({"play": "loot", "building": "B1", "want": "any", "bound": "looted", "why": "clear"}, "looted"),
                     ({"play": "shelter", "building": "B1", "bound": "inside", "why": "night"}, "no_shelter")):
        with pytest.raises(P.Refused) as e:
            P.validate(obj, v)
        assert e.value.why == why


def test_a_kite_may_hold_the_stance_with_no_refuge_and_a_travel_may_explore():
    v = mkview([zrow("Z1", 3.0)])
    assert P.validate({"play": "kite", "target": "Z1", "toward": "stance", "bound": "time", "why": "group"},
                      v).target() == "Z1"
    assert P.validate({"play": "travel", "to": "explore", "gait": "walk", "bound": "arrived", "why": "clear"},
                      v).args["to"] == "explore"


def test_the_system_prompt_names_every_play_bound_and_why_and_no_free_text_field():
    for p, s in P.SCHEMA["plays"].items():
        assert p in P.SYSTEM and "|".join(s["bounds"]) in P.SYSTEM
    assert "|".join(P.WHYS) in P.SYSTEM
    for spec in P.ARGS.values():
        for a in spec.values():
            assert "enum" in a or "label" in a   # every arg typed: no free string anywhere


# ================================================================ the triggers
def step(trig, r, t):
    return trig.step(r.world, t)


def test_each_trigger_fires_once_per_change_over_a_synthetic_frame_stream(tmp_path):
    r = Rig(tmp_path)
    tr = Triggers()
    r.frame()
    assert step(tr, r, 0.0) == []
    r.frame(zombies=[z(1, 108.0, 200.0)])
    assert step(tr, r, 1.0) == ["notice"]
    r.frame(zombies=[z(1, 107.5, 200.0)])
    assert step(tr, r, 1.5) == []                                     # still listed: no second notice
    r.frame(zombies=[z(1, 104.0, 200.0)])
    assert step(tr, r, 2.0) == ["count"]                              # into DANGER_R: the count 0 -> 1
    r.frame(zombies=[z(1, 104.0, 200.0)], hit_reaction="HitReaction")
    assert step(tr, r, 2.5) == ["hit"]
    r.frame(zombies=[z(1, 104.0, 200.0)], hit_reaction="HitReaction")
    assert step(tr, r, 3.0) == []                                     # the same reaction: no second hit
    r.frame(zombies=[z(1, 104.0, 200.0)], wounds={"parts": [part(1, bleeding=True)], "bleeding": 1})
    assert step(tr, r, 3.5) == ["wound"]
    r.frame(zombies=[z(1, 104.0, 200.0, floor=True)], wounds={"parts": [part(1, bleeding=True)], "bleeding": 1})
    assert step(tr, r, 4.0) == ["count", "down"]                      # it fell: standing 1 -> 0, and down
    tr.note_ended()
    r.frame(zombies=[z(1, 104.0, 200.0, floor=True)], wounds={"parts": [part(1, bleeding=True)], "bleeding": 1})
    assert step(tr, r, 4.5) == ["ended"]
    assert tr.fired["notice"] == 1 and tr.fired["hit"] == 1


def test_a_zombie_dead_event_fires_down_and_the_session_s_past_events_do_not(tmp_path):
    r = Rig(tmp_path)
    r.event("zombie_dead", id=7)
    tr = Triggers()
    r.frame()
    assert step(tr, r, 0.0) == []
    r.event("zombie_dead", id=8)
    r.frame()
    assert step(tr, r, 0.5) == ["down"]


def test_clear_fires_once_after_its_hold_and_notice_again_after_the_gap(tmp_path):
    r = Rig(tmp_path)
    tr = Triggers()
    near, far = [z(1, 108.0, 200.0)], [z(1, 125.0, 200.0)]   # 8 tiles off, and 25 (beyond NOTICE_R, still listed)
    r.frame(zombies=near)
    assert step(tr, r, 0.0) == ["notice"]
    r.frame(zombies=far)
    assert step(tr, r, 1.0) == []
    r.frame(zombies=far)
    assert step(tr, r, 1.0 + CLEAR_S - 0.1) == []
    r.frame(zombies=far)
    assert step(tr, r, 1.0 + CLEAR_S) == ["clear"]
    r.frame(zombies=far)
    assert step(tr, r, 2.0 + CLEAR_S) == []
    r.frame(zombies=near)
    assert step(tr, r, NOTICE_GAP_S - 1.0) == []                      # back within 12 before the gap: no notice
    r.frame(zombies=far)
    step(tr, r, NOTICE_GAP_S)
    r.frame(zombies=near)
    assert step(tr, r, 2 * NOTICE_GAP_S + 1.0) == ["notice"]


def test_arrived_fires_on_entering_a_room_and_need_on_a_mark_crossed(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 100) + [])
    tr = Triggers()
    r.frame(x=98.5, y=201.5, thirst=0.05)
    assert step(tr, r, 0.0) == []
    r.frame(x=100.5, y=201.5, thirst=0.05)
    assert step(tr, r, 0.5) == ["arrived"]
    r.frame(x=100.5, y=201.5, thirst=0.2)
    assert step(tr, r, 1.0) == ["need"]
    r.frame(x=100.5, y=201.5, thirst=0.21)
    assert step(tr, r, 1.5) == []


def test_the_closing_speed_reads_the_window_s_oldest_sample(tmp_path):
    r = Rig(tmp_path)
    tr = Triggers()
    for k, x in enumerate((110.0, 109.0, 108.0)):
        r.frame(zombies=[z(1, x, 200.0)])
        step(tr, r, 0.5 * k)
    assert tr.closing(1) == pytest.approx(2.0)


# ================================================================ the source: coalesced, validated late
class Proc:
    def __init__(self, out, rc=0, err=""):
        self.stdout, self.returncode, self.stderr = out, rc, err


def envelope(obj, is_error=False):
    return json.dumps({"type": "result", "is_error": is_error, "result": json.dumps(obj) if not isinstance(
        obj, str) else obj, "usage": {"input_tokens": 429}})


class GatedRunner:
    """A fake CLI: each call waits on `go`, then answers `obj`."""

    def __init__(self, obj):
        self.obj, self.go, self.calls = obj, threading.Event(), []

    def __call__(self, argv, prompt, timeout, env):
        self.calls.append((argv, prompt, env))
        self.go.wait(5.0)
        return Proc(envelope(self.obj))


def test_one_call_in_flight_the_rest_coalesced_and_the_answer_validated_against_the_view_it_lands_on():
    run = GatedRunner({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"})
    clock = {"t": 0.0}
    src = S.TacticianSource(S.cli("haiku"), clock=lambda: clock["t"], runner=run)
    v = mkview([zrow("Z1", 3.0)])
    assert src.ask(v, "notice") is True
    assert src.ask(v, "count") is False and src.ask(v, "hit") is False
    assert src.coalesced == 2 and src.dirty is True
    assert src.poll(v) is None                                       # still out
    run.go.set()
    src.join(5.0)
    r = src.poll(v)
    assert r["play"] == {"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}
    assert r["refused_why"] is None and r["coalesced"] == 0 and r["model"] == "haiku" and r["trigger"] == "notice"
    assert len(run.calls) == 1 and "CLAUDECODE" not in run.calls[0][2]
    assert src.poll(v) is None                                       # collected once
    assert src.ask(v, "coalesced") is True and src.coalesced == 0    # the dirty flight asks again at once
    src.join(5.0)


def test_a_late_answer_naming_a_zombie_gone_from_the_moment_s_view_is_refused():
    run = GatedRunner({"play": "fight", "target": "Z2", "bound": "dead", "why": "lone_chaser"})
    run.go.set()
    src = S.TacticianSource(S.cli(), runner=run)
    src.ask(mkview([zrow("Z1", 3.0), zrow("Z2", 5.0)]), "count")
    src.join(5.0)
    r = src.poll(mkview([zrow("Z1", 3.0)]))
    assert r["play"] is None and r["refused_why"] == "unknown_label"


def test_a_call_past_its_timeout_is_abandoned_and_its_late_answer_ignored():
    run = GatedRunner({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"})
    clock = {"t": 0.0}
    src = S.TacticianSource(S.cli(), timeout_s=5.0, clock=lambda: clock["t"], runner=run)
    v = mkview([zrow("Z1", 3.0)])
    src.ask(v, "notice")
    clock["t"] = 5.5
    r = src.poll(v)
    assert r["error"] == "timeout" and r["refused_why"] == "timeout" and r["play"] is None
    assert src.busy() and src.ask(v, "count") is False               # the abandoned thread still runs: no new call
    run.go.set()
    src.join(5.0)
    assert src.poll(v) is None and not src.busy()


def test_the_call_reads_the_limit_only_off_an_exit_or_an_error_envelope():
    ok = S.call(S.cli(), "v", lambda *a: Proc(envelope({"play": "fight"})))
    assert ok["limited"] is False and ok["error"] is None   # a successful envelope's 429 token count is no limit
    assert S.call(S.cli(), "v", lambda *a: Proc("", rc=1))["limited"] is True
    lim = S.call(S.cli(), "v", lambda *a: Proc(envelope("API Error: 429 rate limit", is_error=True)))
    assert lim["limited"] is True and lim["error"] == "cli error"
    assert S.call(S.cli(), "v", lambda *a: Proc("not json"))["error"] == "malformed"


def test_the_cli_is_llm_s_argv_with_the_tactician_s_system_prompt_and_model():
    argv = S.cli("haiku")
    assert argv[argv.index("--model") + 1] == "haiku"
    assert argv[argv.index("--system-prompt") + 1] == P.SYSTEM
    assert argv[argv.index("--tools") + 1] == "" and "--no-session-persistence" in argv


# ================================================================ the fallback doctrine
def answer(view):
    return F.doctrine(view)


def test_one_standing_zombie_armed_is_fought_whatever_the_health():
    for health in (100.0, 30.0, 5.0):
        rule, ans = answer(mkview([zrow("Z1", 4.0)], health=health))
        assert (rule, ans["play"], ans["target"]) == ("fight", "fight", "Z1")


def test_a_zombie_in_reach_is_struck_even_while_a_part_bleeds():
    rule, ans = answer(mkview([zrow("Z1", 1.5)], parts=[bleeding_part()], kit={"bandages": 1}))
    assert (rule, ans["play"]) == ("reach", "fight")


def test_a_bleed_is_dressed_before_a_fight_with_a_zombie_still_beyond_keep_r_ripping_with_nothing_held():
    rule, ans = answer(mkview([zrow("Z1", 4.0)], parts=[bleeding_part(3, 60.0), bleeding_part(1, 40.0)],
                              kit={"unwear": 1}))
    assert (rule, ans["play"], ans["part"], ans["with"]) == ("bleed", "dress", "P1", "rip")


def test_a_bleed_with_nothing_to_dress_or_tear_falls_to_the_fight():
    rule, ans = answer(mkview([zrow("Z1", 4.0)], parts=[bleeding_part()]))
    assert (rule, ans["play"]) == ("fight", "fight")


def test_a_group_is_kited_toward_a_refuge_away_from_it_and_avoided_before_it_arrives():
    zs = [zrow("Z1", 3.0, bearing="E"), zrow("Z2", 4.0, bearing="E"), zrow("Z3", 5.0, bearing="NE")]
    rule, ans = answer(mkview(zs, doors=[DOOR]))
    assert (rule, ans["play"], ans["toward"]) == ("group", "kite", "D1")
    far = [zrow("Z%d" % k, 9.0 + k, bearing="E") for k in (1, 2, 3)]
    rule, ans = answer(mkview(far, doors=[DOOR]))
    assert (rule, ans["play"], ans["toward"]) == ("group", "avoid", "D1")


def test_a_door_toward_the_group_is_no_refuge_and_with_none_the_kite_holds_the_stance():
    zs = [zrow("Z1", 3.0, bearing="W"), zrow("Z2", 4.0, bearing="W"), zrow("Z3", 5.0, bearing="W")]
    rule, ans = answer(mkview(zs, doors=[DOOR]))
    assert (ans["play"], ans["toward"]) == ("kite", "stance")


def test_one_standing_with_two_more_aware_farther_is_still_fought_never_fled():
    zs = [zrow("Z1", 4.0), zrow("Z2", 9.0), zrow("Z3", 10.0)]
    rule, ans = answer(mkview(zs, doors=[DOOR]))
    assert ans["play"] == "fight"


def test_unarmed_one_is_kited_and_two_are_a_group():
    rule, ans = answer(mkview([zrow("Z1", 4.0)], armed=None, doors=[DOOR]))
    assert (rule, ans["play"]) == ("unarmed", "kite")
    rule, ans = answer(mkview([zrow("Z1", 4.0), zrow("Z2", 5.0)], armed=None, doors=[DOOR]))
    assert (rule, ans["play"]) == ("group", "kite")


def test_one_or_two_coming_within_engage_r_are_fought_before_a_loot():
    rule, ans = answer(mkview([zrow("Z1", 8.0)], buildings=[BUILDING]))
    assert (rule, ans["play"]) == ("fight", "fight")
    rule, ans = answer(mkview([zrow("Z1", 8.0, targets_me=False)], buildings=[BUILDING]))
    assert (rule, ans["play"]) == ("loot", "loot")


def test_the_strategic_rules_shelter_at_night_loot_the_goal_s_building_travel_and_explore():
    b2 = dict(BUILDING, label="B2", dist=9.0)
    assert answer(mkview(buildings=[BUILDING], needs={"night": True, "fatigue": 0.1}))[1]["play"] == "shelter"
    rule, ans = answer(mkview(buildings=[BUILDING, b2], goal={"type": "LootBuilding", "building": "B2"}))
    assert (rule, ans["building"]) == ("goal", "B2")
    rule, ans = answer(mkview(buildings=[dict(BUILDING, looted=True)]))
    assert (rule, ans["play"], ans["to"]) == ("travel", "travel", "B1")
    rule, ans = answer(mkview())
    assert (rule, ans["to"]) == ("explore", "explore")


def test_every_doctrine_answer_validates_on_its_view():
    views = [mkview([zrow("Z1", 4.0)]), mkview(parts=[bleeding_part()], kit={"rags": 1}),
             mkview([zrow("Z%d" % k, 3.0 + k) for k in (1, 2, 3)], doors=[DOOR]), mkview(buildings=[BUILDING]),
             mkview()]
    for v in views:
        rule, ans = answer(v)
        assert P.validate(ans, v).play == ans["play"] and rule in F.RULES


# ================================================================ the rubric and the table
def test_the_rubric_reads_its_three_rules_and_never_binds_both_combat_rules_at_once():
    lone = mkview([zrow("Z1", 4.0)])
    assert R.violations(lone, {"play": "kite"}) == ["lone_not_fight"]
    assert R.violations(lone, {"play": "fight"}) == []
    bleed = mkview([zrow("Z1", 4.0)], parts=[bleeding_part()], kit={"bandages": 1})
    assert R.violations(bleed, {"play": "fight"}) == ["bleed_not_dress"]
    assert R.violations(bleed, {"play": "dress"}) == []
    assert R.violations(mkview(buildings=[BUILDING]), {"play": "travel", "to": "explore"}) == ["travel_nowhere"]
    assert R.violations(mkview(), {"play": "travel", "to": "explore"}) == []
    assert R.violations(lone, None) == ["lone_not_fight"]


def test_the_doctrine_breaks_no_rubric_rule_on_the_fixed_views():
    views = [mkview([zrow("Z1", d)], parts=p, kit=k) for d in (1.0, 4.0) for p in ([], [bleeding_part()])
             for k in ({}, {"bandages": 1})] + [mkview(buildings=[BUILDING]), mkview()]
    for v in views:
        assert R.violations(v, answer(v)[1]) == []


def test_the_table_s_cell_answers_with_the_fallback_s_target_else_the_doctrine():
    v = mkview([zrow("Z1", 4.0), zrow("Z2", 5.0)])
    k = T.key(v)
    assert k == "s2|k0|g0|a1|hhi|b0|d0|i0"
    assert T.Table().answer(v)[:2] == ("doctrine", "fight")
    src, cell, ans = T.Table({k: "kite"}).answer(v)
    assert (src, cell, ans["play"], ans["target"]) == ("table", k, "kite", "Z1")
    assert T.Table({k: "dress"}).answer(v)[0] == "doctrine"          # no bleed: the cell's play has no target


def test_where_a_rule_binds_the_doctrine_answers_whatever_the_cell_holds():
    lone = mkview([zrow("Z1", 4.0)])
    bleed = mkview(parts=[bleeding_part()], kit={"rags": 1})
    for v, play in ((lone, "fight"), (bleed, "dress")):
        assert T.bound(v)
        src, rule, ans = T.Table({T.key(v): "kite"}).answer(v)
        assert (src, ans["play"]) == ("doctrine", play)
    assert T.Table.fit([(lone, {"play": "kite"})]).cells == {}       # a bound view labels no cell


def test_the_table_fits_each_cell_s_majority_ties_to_the_doctrine():
    v = mkview([zrow("Z1", 4.0), zrow("Z2", 5.0)])
    t = T.Table.fit([(v, {"play": "kite"}), (v, {"play": "kite"}), (v, {"play": "fight"}), (v, None)])
    assert t.cells == {T.key(v): "kite"}
    t = T.Table.fit([(v, {"play": "kite"}), (v, {"play": "fight"})])
    assert t.cells == {T.key(v): "fight"}


def test_the_committed_table_loads_and_names_only_plays():
    t = T.Table.load()
    assert all(p in P.PLAYS for p in t.cells.values())


# ================================================================ the decider through the fork
def make(tmp_path, caps=None, table=True):
    """A Survive under the tactician on a fresh Rig. `table` True pins the doctrine (an empty table: the decider's rules
    under test, whatever cells the bench committed); False keeps the committed `table.json`."""
    r = Rig(tmp_path, caps=caps)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="tactician")
    if table:
        sv.control_state["tactician"] = D.Tactician(sv, table=T.Table())
    return r, sv


def lines(tmp_path, name="decision.log"):
    p = tmp_path / name
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def tick(r, sv, dt=0.5):
    a = sv.tick(r.world, r.acts)
    r.advance(dt)
    return a


def test_the_variant_loads_by_name_runs_the_table_and_makes_no_call_without_the_model(tmp_path, monkeypatch):
    monkeypatch.delenv(D.ENV_MODE, raising=False)
    r, sv = make(tmp_path, table=False)
    r.frame()
    tick(r, sv)
    t = sv.control_state["tactician"]
    assert t.mode == "table" and t.source is None and t.table.cells == T.Table.load().cells
    assert isinstance(sv.goals.source, X.PlaySource) and sv.GOAL_CONTINUE is False and sv.DOOR_HELD is False
    assert Survive.GOAL_CONTINUE is True and Survive.DOOR_HELD is True   # instance fields only, never the class


def test_the_model_mode_is_refused_without_an_llm_goal_source(tmp_path, monkeypatch):
    monkeypatch.setenv(D.ENV_MODE, "model")
    r, sv = make(tmp_path, table=False)
    r.frame()
    tick(r, sv)
    assert sv.control_state["tactician"].mode == "table"


def test_one_chasing_zombie_beyond_reach_is_met_in_the_stance_never_fled(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 104.0, 200.0)], health=20.0)
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["branch"] == "threat" and "flee" not in line["inputs"]["branches"]["threat"]
    assert line["inputs"]["play"] == {"kind": "fight", "type": "fight", "play_id": 1, "target": 7}
    assert line["action"]["type"] == "aim" and line["action"]["args"]["targetId"] == 7
    assert (line["action"]["args"]["vx"], line["action"]["args"]["vy"]) == (0.0, 0.0)   # standing: let it come
    tac = line["inputs"]["tactician"]
    assert (tac["play"], tac["target"], tac["source"], tac["rule"]) == ("fight", "Z1", "doctrine", "fight")
    assert (line["inputs"]["x"], line["inputs"]["y"]) == (100.0, 200.0)
    all_sends_valid(r)


def test_within_the_melee_s_release_the_fight_presses_through_the_melee_maneuver(tmp_path):
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    r.frame(zombies=[z(7, 101.8, 200.0)])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["action"]["type"] == "melee" and line["action"]["args"]["targetId"] == 7
    args = line["action"]["args"]
    assert args["mode"] == "strike"
    if X.MELEE_API == "1.9":
        assert (args["backVx"], args["backVy"]) == (0.0, 0.0)          # no back step after a press
    else:
        assert "backVx" not in args and "closeR" not in args            # PZA/1.10: the meet has none
    r.frame(zombies=[z(7, 101.6, 200.0)])
    tick(r, sv)
    assert lines(tmp_path)[-1]["action"] is None                       # the melee runs: held, not re-sent


def test_a_bleeding_part_with_nothing_near_is_dressed_by_the_dress_maneuver_first(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(zombies=[z(7, 104.5, 200.0)], wounds={"parts": [part(1, bleeding=True, bleedingTime=5.0)], "bleeding": 1})
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["branch"] == "care" and line["inputs"]["play"]["kind"] == "dress"
    assert line["action"]["type"] == "stop"                            # the Dress stops first
    assert "target" not in line["inputs"]["play"]


def test_a_dress_that_found_nothing_is_not_restarted_until_an_item_is_added_or_its_hold_passes(tmp_path):
    r, sv = make(tmp_path)
    bleeding = {"parts": [part(1, bleeding=True, bleedingTime=5.0)], "bleeding": 1}
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(wounds=bleeding)
    tick(r, sv)
    t = sv.control_state["tactician"]
    assert t.exec.play.play == "dress"
    t._end("nothing")                                                  # as the Dress ending failed "nothing"
    r.frame(wounds=bleeding)
    tick(r, sv)
    assert t.exec.play.play != "dress" and 1 in t.dress_held
    r.event("item_added", itemId=12, fullType="Base.RippedSheets", weight=0.1, use="bandage")
    r.frame(wounds=bleeding)
    tick(r, sv)                                                         # a new item: no trigger, so the play runs on
    t._end("replaced", broken=False)
    r.frame(wounds=bleeding)
    tick(r, sv)
    assert t.exec.play.play == "dress" and not t.dress_held


def test_a_standing_zombie_inside_the_swing_radius_takes_any_play_by_the_guard(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(wounds={"parts": [part(1, bleeding=True, bleedingTime=5.0)], "bleeding": 1})
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["play"]["kind"] == "dress"
    r.frame(zombies=[z(7, 100.8, 200.0)], wounds={"parts": [part(1, bleeding=True, bleedingTime=5.0)], "bleeding": 1})
    tick(r, sv)
    tac = lines(tmp_path)[-1]["inputs"]["tactician"]
    assert tac["play"] == "fight" and tac["source"] == "guard" and tac["guard"] == "swing"


def test_a_hit_reaction_hands_the_tick_to_the_melee(tmp_path):
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    r.frame(zombies=[z(7, 102.0, 200.0), z(8, 102.2, 200.5), z(9, 102.4, 199.5)], hit_reaction="HitReaction")
    tick(r, sv)
    tac = lines(tmp_path)[-1]["inputs"]["tactician"]
    assert (tac["play"], tac["guard"]) == ("fight", "hit")


def test_a_group_with_no_refuge_is_kited_in_the_stance_and_the_line_names_the_retreat(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 103.0, 200.0), z(8, 103.5, 201.0), z(9, 104.0, 199.0)])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["branch"] == "threat" and line["inputs"]["branches"]["threat"]["flee"] == "group"
    assert line["inputs"]["play"]["kind"] == "kite_stance" and line["inputs"]["play"]["target"] == 7
    a = line["action"]
    assert a["type"] == "aim" and a["args"]["targetId"] == 7 and a["args"]["vx"] < 0.0   # backpedal, facing it


def test_a_group_with_a_door_away_is_kited_toward_that_door(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 90, y0=199) + [PO_square(x, y) for x in range(93, 108) for y in range(196, 205)])
    r.frame(zombies=[z(7, 103.0, 200.0), z(8, 103.5, 201.0), z(9, 104.0, 199.0)])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["inputs"]["play"]["kind"] == "kite_door"
    assert line["inputs"]["tactician"]["target"] == "Z1"


def PO_square(x, y):
    from .test_policies import square
    return square(x, y)


def test_a_zombie_behind_a_closed_door_is_never_waited_on(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 100, y0=198) + [PO_square(x, y) for x in range(95, 100) for y in range(196, 204)])
    r.frame(x=98.5, y=199.5, zombies=[z(7, 101.5, 199.5, me=(98.5, 199.5))])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    w = sv.world
    assert V.line_of(w, w.zombies[7]) == "door"
    assert line["inputs"]["play"]["kind"] == "fight"
    assert line["action"] is not None and line["action"]["type"] == "walkTo"   # through the door, never a wait


def test_with_nothing_near_the_strategic_goal_layer_runs_and_the_line_keeps_the_ladder_s_contract(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["inputs"]["play"]["type"] == "travel" and line["inputs"]["tactician"]["rule"] == "explore"
    assert {"need", "consume_refused", "cooled", "branches", "x", "y"} <= set(line["inputs"])
    assert "goal" in line and line["branch"] in (None, "goal")


def test_plays_log_records_each_play_its_end_and_its_source(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 104.0, 200.0)])
    tick(r, sv)
    r.event("zombie_dead", id=7)
    r.frame()
    tick(r, sv)
    rows = lines(tmp_path, D.PLAYS_LOG)
    kinds = [x["kind"] for x in rows]
    assert kinds[:3] == ["play", "play_end", "play"]
    assert rows[0]["play"]["play"] == "fight" and rows[0]["source"] == "doctrine"
    assert rows[1]["end"] == "dead" and rows[1]["bound_broken"] is True and rows[1]["aids"]


class FakeSource:
    """A model source whose answers the test hands in."""

    def __init__(self):
        self.asked, self.dirty, self.out = [], False, None

    def ask(self, view, trigger):
        self.asked.append(trigger)
        return True

    def busy(self):
        return False

    def poll(self, view_now):
        out, self.out = self.out, None
        if out is None:
            return None
        play, why = S.judge(out, view_now)
        return {"trigger": "notice", "view": None, "answer": out, "play": play.row() if play else None,
                "refused_why": why, "latency_s": 2.0, "model": "fake", "coalesced": 0, "error": None, "_play": play}


def test_a_model_answer_overrides_the_table_and_a_refused_one_reaches_the_next_view_once(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 104.0, 200.0), z(8, 105.0, 201.5)])
    t = sv.control_state["tactician"] = D.Tactician(sv, source=FakeSource(), table=T.Table())
    t.mode = "model"
    tick(r, sv)
    assert t.source.asked == ["notice"] and t.exec.play.play == "fight"
    t.source.out = {"play": "kite", "target": "Z1", "toward": "stance", "bound": "time", "why": "lone_chaser"}
    r.frame(zombies=[z(7, 104.0, 200.0), z(8, 105.0, 201.5)])
    tick(r, sv)
    assert t.exec.play.play == "kite" and lines(tmp_path)[-1]["inputs"]["tactician"]["source"] == "model"
    t.source.out = {"play": "fight", "target": "Z5", "bound": "dead", "why": "lone_chaser"}
    r.frame(zombies=[z(7, 104.0, 200.0), z(8, 105.0, 201.5)])
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["tactician"]["refused"] == {"why": "unknown_label"}
    assert t.refusal == "unknown_label" and t.view()["refusal"] == "unknown_label"
    calls = [x for x in lines(tmp_path, D.PLAYS_LOG) if x["kind"] == "call"]
    assert [c["refused_why"] for c in calls] == [None, "unknown_label"] and calls[0]["applied_at"] is not None


def test_a_model_answer_breaking_a_rule_the_doctrine_keeps_is_vetoed(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 104.0, 200.0)])
    t = sv.control_state["tactician"] = D.Tactician(sv, source=FakeSource(), table=T.Table())
    t.mode = "model"
    tick(r, sv)
    t.source.out = {"play": "avoid", "toward": "stance", "gait": "walk", "bound": "clear", "why": "group"}
    r.frame(zombies=[z(7, 104.0, 200.0)])
    tick(r, sv)   # an invalid toward: refused by the schema, not the veto
    assert lines(tmp_path)[-1]["inputs"]["tactician"]["refused"] == {"why": "bad_arg"}
    t.source.out = {"play": "kite", "target": "Z1", "toward": "stance", "bound": "time", "why": "group"}
    t._end("replaced", broken=False)
    r.frame(zombies=[z(7, 104.0, 200.0), z(8, 105.0, 201.0)])
    tick(r, sv)   # two standing: no rule binds, the model's kite stands
    assert t.exec.play.play == "kite"
    t.source.out = {"play": "kite", "target": "Z1", "toward": "stance", "bound": "time", "why": "group"}
    t._end("replaced", broken=False)
    r.frame(zombies=[z(7, 104.0, 200.0), z(8, 115.0, 201.0)])
    tick(r, sv)   # one standing within DANGER_R, armed: the kite is vetoed, the doctrine's fight runs
    assert lines(tmp_path)[-1]["inputs"]["tactician"]["refused"] == {"why": "doctrine"}
    assert t.exec.play.play == "fight"


def test_a_model_s_loot_pins_its_building_once_through_the_play_source(tmp_path):
    r, sv = make(tmp_path)
    sqs = house(1, 104) + [PO_square(x, y) for x in range(95, 104) for y in range(196, 205)]
    sqs = [dict(q, containers=[CRATE]) if (q["x"], q["y"]) == (105, 201) else q for q in sqs]
    r.scan(sqs)
    r.frame()
    t = sv.control_state["tactician"] = D.Tactician(sv, source=FakeSource(), table=T.Table())
    t.mode = "model"
    t.source.out = {"play": "loot", "building": "B1", "want": "any", "bound": "looted", "why": "clear"}
    tick(r, sv)
    tick(r, sv)
    g = sv.goals.current
    assert g is not None and g.TYPE == "LootBuilding" and g.building == 1
    assert sv.goals.source.pin is None and sv.goals.source.pinned is g


def test_the_melee_call_site_is_one_function():
    """Task 2's API switch is one place: `executors.melee_step` is the only maker of the Melee's inputs."""
    import inspect
    src, fn = inspect.getsource(X), inspect.getsource(X.melee_step)
    assert src.count("= MeleeInputs(") == fn.count("= MeleeInputs(") == 2 and X.MELEE_API in ("1.9", "1.10")


def test_melee_step_builds_task_2_s_inputs_on_the_pza_1_10_api(monkeypatch):
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class Inputs110:   # Task 2's MeleeInputs (4d646a0a): mode, reach, floor_swing
        mode: str
        reach: float
        floor_swing: bool

    class M:
        inputs = None

        def step(self):
            return "cmd"
    monkeypatch.setattr(X, "MeleeInputs", Inputs110)
    monkeypatch.setattr(X, "MELEE_API", "1.10")
    m = M()

    class W:
        weapon = {"reach": 1.2}
    assert X.melee_step(m, "strike", W()) == "cmd"
    assert m.inputs == Inputs110("strike", pytest.approx(1.2 + PO.ATTACK_MARGIN), True)


def test_today_s_melee_takes_no_back_leg_and_the_guard_s_swing_close(monkeypatch):
    class M:
        inputs = None

        def step(self):
            return None

    class W:
        weapon = None
    m = M()
    if X.MELEE_API != "1.9":
        pytest.skip("the PZA/1.10 meet is on this tree")
    X.melee_step(m, "shove", W())
    assert (m.inputs.back, m.inputs.close_r, m.inputs.reach) == ((0.0, 0.0), X.SWING_GUARD_R, 0.0)


@pytest.mark.parametrize("end, bound", [("dead", "dead"), ("kill", "dead"), ("handback", "second_standing")])
def test_the_meet_s_ends_map_onto_the_fight_s_bounds(tmp_path, end, bound):
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    r.frame(zombies=[z(7, 101.8, 200.0)])
    tick(r, sv)
    ex = sv.control_state["tactician"].exec

    class Done:
        handback, end_why, target = {"id": 8, "d": 1.0}, None, 7

        def observe(self):
            pass

        def take_kills(self):
            return []

        def take_span(self):
            return None

        def over(self):
            return end
    ex.m = Done()
    assert ex.bound() == bound
