"""The composition mix_1 (Plan 31 Task 13: `planner/mix_1/`, its README the design record): the tactician whole plus
two pieces, each tested here at the rule (`rules.py`, over a hand-made tactical view) and through the fork
(`Survive(control="mix_1")` on the fake mod):

1. `clear`, the ladder's lone-idle seek as a doctrine rule: one standing zombie listed within ENGAGE_R, reachable by
   the instance's `_engageable`, armed, no group → `fight` it, at zero latency over the table's cells and over a
   running strategic play; never with two within ENGAGE_R, unarmed, or a zombie the ladder's reading leaves
   unreachable; a model answer that is no fight is vetoed `doctrine` (`lone_not_cleared`).
2. The crawler: a crawler within KEEP_R blocks the dressing and the `crawler` guard finishes it first (mode `finish`);
   the finish is held against a trigger's other answer; a retreat is never cut for it; a model answer leaving it is
   vetoed (`crawler_first`).

The tactician's own behaviour is `test_tactician.py`'s; a few of its cases are re-run here under mix_1 to show the
package is the tactician whole."""
import json

import pytest

from agent.base.planner.mix_1 import decide as MD
from agent.base.planner.mix_1 import rules as M
from agent.base.planner.survive import Survive
from agent.base.planner.tactician import decide as TD
from agent.base.planner.tactician import executors as X
from agent.base.planner.tactician import fallback as F
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician import table as TT
from agent.base.planner.tactician import tview as V

from .fakemod import MELEE_CAPS
from .test_night import house
from .test_policies import Rig, all_sends_valid
from .test_survive_g import part
from .test_tactician import BUILDING, DOOR, FakeSource, PO_square, bleeding_part, mkview, z, zrow

BLEED = {"parts": [part(1, bleeding=True, bleedingTime=5.0)], "bleeding": 1}


def crawler(zid, x, y, me=(100.0, 200.0)):
    out = z(zid, x, y, target=True, floor=True, me=me)
    out["crawler"] = True
    return out


def open_grid(x0=88, x1=112, y0=190, y1=210):
    return [PO_square(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


# ================================================================ rules: piece 1, `clear`
def test_a_lone_idle_zombie_the_decider_reads_reachable_is_cleared_by_the_doctrine():
    v = dict(mkview([zrow("Z1", 8.0, targets_me=False)], buildings=[BUILDING]), clear="Z1")
    assert M.doctrine(v) == ("clear", {"play": "fight", "target": "Z1", "bound": "dead", "why": "clear"})
    assert F.doctrine(v)[0] == "goal" or F.doctrine(v)[1]["play"] != "fight"   # the tactician alone loots
    assert M.clear_due(v) and M.bound(v)


def test_clear_does_not_fire_unreachable_with_two_unarmed_or_in_a_group():
    one = [zrow("Z1", 8.0, targets_me=False)]
    assert M.doctrine(dict(mkview(one, buildings=[BUILDING]), clear=None))[1]["play"] == "loot"   # not reachable
    two = [zrow("Z1", 7.0, targets_me=False), zrow("Z2", 8.5, targets_me=False)]
    assert M.lone(mkview(two)) is None
    assert M.doctrine(dict(mkview(two, buildings=[BUILDING]), clear="Z1"))[1]["play"] == "loot"   # two: no seek
    assert M.doctrine(dict(mkview(one, armed=None, buildings=[BUILDING]), clear="Z1"))[1]["play"] == "loot"
    group = one + [zrow("Z%d" % k, 10.0 + k * 0.3) for k in (2, 3, 4)]   # three aware at 10.6-11.2 tiles: a group
    v = dict(mkview(group, buildings=[BUILDING], doors=[DOOR]), clear="Z1")
    assert M.lone(v) == "Z1" and M.clear_target(v) is None and M.doctrine(v)[0] == "group"


def test_a_fallen_zombie_does_not_count_against_alone_and_a_stale_clear_label_is_not_followed():
    v = mkview([zrow("Z1", 3.0, posture="floor"), zrow("Z2", 8.0, targets_me=False)], buildings=[BUILDING])
    assert M.lone(v) == "Z2"
    assert M.clear_target(dict(v, clear="Z1")) is None   # the label is no longer the lone one's


def test_clear_binds_so_a_table_cell_never_answers_over_it():
    v = dict(mkview([zrow("Z1", 8.0, targets_me=False)], buildings=[BUILDING]), clear="Z1")
    t = M.Table({TT.key(v): "loot"})
    assert t.answer(v) == ("doctrine", "clear", {"play": "fight", "target": "Z1", "bound": "dead", "why": "clear"})
    assert TT.Table({TT.key(v): "loot"}).answer(v)[2]["play"] == "loot"   # the tactician's table would loot


def test_the_rubric_vetoes_any_answer_but_a_fight_while_clear_binds():
    v = dict(mkview([zrow("Z1", 8.0, targets_me=False)], buildings=[BUILDING]), clear="Z1")
    loot = {"play": "loot", "building": "B1", "want": "any", "bound": "looted", "why": "clear"}
    assert M.violations(v, loot) == ["lone_not_cleared"]
    assert M.violations(v, {"play": "fight", "target": "Z1", "bound": "dead", "why": "clear"}) == []


# ================================================================ rules: piece 2, the crawler
def test_a_crawler_within_keep_r_blocks_the_dressing_and_one_beyond_it_does_not():
    kit = {"bandages": 1}
    near = mkview([zrow("Z1", 1.1, posture="crawler")], parts=[bleeding_part(1)], kit=kit)
    far = mkview([zrow("Z1", 3.0, posture="crawler")], parts=[bleeding_part(1)], kit=kit)
    assert F.doctrine(near)[0] == "bleed"                       # the tactician dresses with a crawler at 1.1
    assert M.doctrine(near)[1] is None or M.doctrine(near)[1]["play"] != "dress"
    assert not M.dress_due(near) and not M.keep_clear(near) and M.crawler_due(near)
    assert M.doctrine(far)[0] == "bleed" and M.dress_due(far)


def test_the_rubric_wants_the_crawler_finished_but_lets_a_retreat_run():
    v = mkview([zrow("Z1", 1.1, posture="crawler"), zrow("Z2", 4.0)], parts=[bleeding_part(1)], kit={"bandages": 1},
               doors=[DOOR])
    dress = {"play": "dress", "part": "P1", "with": "bandage", "bound": "dressed", "why": "bleeding"}
    assert "crawler_first" in M.violations(v, dress)
    assert "crawler_first" in M.violations(v, {"play": "fight", "target": "Z2", "bound": "dead", "why": "lone_chaser"})
    assert M.violations(v, {"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}) == []
    assert "crawler_first" not in M.violations(v, {"play": "kite", "target": "Z2", "toward": "D1", "bound": "time",
                                                   "why": "group"})


def test_the_world_and_the_view_read_a_crawler_by_one_predicate():
    """Fix 1 (review-t13-mix1 finding 3): the frame's `crawler`, whatever `onFloor` reads, for both reads."""
    for rec in (crawler(7, 101.0, 200.0), dict(z(7, 101.0, 200.0), crawler=True)):
        assert M.is_crawler(rec) and V.posture(rec) == "crawler"
    knocked = z(7, 101.0, 200.0, floor=True)
    assert not M.is_crawler(knocked) and V.posture(knocked) == "floor"


def test_a_crawler_whose_frame_omits_on_floor_is_still_finished_first_and_never_the_standing_zombie(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    rec = dict(z(9, 101.5, 200.0), crawler=True)                  # crawler true, onFloor absent
    r.frame(zombies=[rec], wounds=BLEED)
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert lines(tmp_path)[-1]["inputs"]["mix_1"]["piece"] in ("guard.crawler", "guard.swing", "rule.reach")
    assert t.exec.play.play == "fight" and t.exec.zid == 9
    assert t._standing_keep() == [] and t._finishing(t.exec)


# ================================================================ the decider through the fork
def make(tmp_path, caps=None, grid=True):
    r = Rig(tmp_path, caps=caps)
    if grid:
        r.scan(open_grid())
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="mix_1")
    sv.control_state["mix_1"] = MD.Mix1(sv, table=M.Table())
    return r, sv


def lines(tmp_path, name="decision.log"):
    p = tmp_path / name
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def tick(r, sv, dt=0.5):
    a = sv.tick(r.world, r.acts)
    r.advance(dt)
    return a


def test_the_composition_loads_by_name_with_the_tactician_s_switches_and_its_own_state(tmp_path, monkeypatch):
    monkeypatch.delenv(TD.ENV_MODE, raising=False)
    from agent.base.planner import control as C
    from agent.base.planner import mix_1 as MIX
    assert C.load("mix_1") is MIX.assess and C.prepare_of("mix_1") is MIX.prepare
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="mix_1")
    assert (sv.DOOR_HELD, sv.GOAL_CONTINUE) == (False, False)
    r.frame()
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert isinstance(t, MD.Mix1) and isinstance(t, TD.Tactician) and "tactician" not in sv.control_state
    assert t.mode == "table" and t.source is None and isinstance(t.table, M.Table)
    assert t.table.cells == TT.Table.load().cells               # the tactician's committed cells
    line = lines(tmp_path)[-1]
    assert line["inputs"]["mix_1"]["piece"] == "rule.explore" and line["inputs"]["play"]["type"] == "travel"
    assert set(line["inputs"]["mix_1"]) == {"piece", "clear_why", "added", "started", "kind", "play", "target",
                                            "clear"}


def test_a_lone_idle_zombie_at_eight_tiles_is_fought_at_once_toward_it_in_the_stance(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["play"]["type"] == "travel"
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    mx = line["inputs"]["mix_1"]
    assert (mx["piece"], mx["added"], mx["started"], mx["play"], mx["target"], mx["clear"]) == (
        "rule.clear", True, True, "fight", 7, 7)
    assert line["branch"] == "threat" and line["inputs"]["play"]["kind"] == "fight"
    assert line["action"]["type"] == "aim" and line["action"]["args"]["targetId"] == 7
    assert line["action"]["args"]["vx"] > 0.9                   # toward it (east), the stance's `toward` leg
    ends = [x for x in lines(tmp_path, TD.PLAYS_LOG) if x["kind"] == "play_end"]
    assert ends[-1]["end"] == "doctrine"                         # the strategic play taken at once (the rule path)
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    tick(r, sv)
    mx = lines(tmp_path)[-1]["inputs"]["mix_1"]
    assert (mx["piece"], mx["started"]) == ("rule.clear", False)   # the play runs on
    all_sends_valid(r)


def test_the_tactician_alone_leaves_the_same_zombie_standing(tmp_path):
    """The control for the previous test: the tactician's own rules leave an idle zombie at 8 tiles."""
    r = Rig(tmp_path)
    r.scan(open_grid())
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="tactician")
    sv.control_state["tactician"] = TD.Tactician(sv, table=TT.Table())
    for _ in range(3):
        r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
        tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["play"]["type"] != "fight"


def test_a_lone_chaser_coming_at_seven_tiles_takes_a_running_travel_at_once(tmp_path):
    """E23 71.5-73.5 s: the tactician's `fight` rule names a chaser coming within ENGAGE_R, but its bound leaves it to
    the running travel until DANGER_R; the lone zombie's binding takes it at once, logged rule `clear`."""
    r, sv = make(tmp_path)
    r.frame()
    tick(r, sv)
    r.frame(zombies=[z(7, 107.2, 200.0)])
    tick(r, sv)
    line = lines(tmp_path)[-1]
    mx, tac = line["inputs"]["mix_1"], line["inputs"]["tactician"]
    assert (mx["piece"], mx["started"], mx["target"], tac["table"]) == ("rule.clear", True, 7, "rule")
    assert line["action"]["type"] == "aim" and (line["action"]["args"]["vx"], line["action"]["args"]["vy"]) == (
        0.0, 0.0)                                                 # a chaser: the stance stands and lets it come


def test_the_tactician_alone_lets_the_travel_run_with_the_chaser_at_seven_tiles(tmp_path):
    r = Rig(tmp_path)
    r.scan(open_grid())
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="tactician")
    sv.control_state["tactician"] = TD.Tactician(sv, table=TT.Table())
    r.frame()
    tick(r, sv)
    r.frame(zombies=[z(7, 107.2, 200.0)])
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["play"]["type"] == "travel"


def test_a_clear_play_names_why_idle_or_coming(tmp_path):
    """Fix 1 (finding 4): round two credits the seek of an idle zombie apart from the earlier take of one coming."""
    r, sv = make(tmp_path)
    r.frame()
    tick(r, sv)
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["mix_1"]["clear_why"] == "idle"
    r2, sv2 = make(tmp_path / "b")
    r2.frame()
    tick(r2, sv2)
    r2.frame(zombies=[z(7, 107.2, 200.0)])
    tick(r2, sv2)
    mx = lines(tmp_path / "b")[-1]["inputs"]["mix_1"]
    assert (mx["piece"], mx["clear_why"]) == ("rule.clear", "coming")
    r2.frame(zombies=[z(7, 104.0, 200.0)])
    tick(r2, sv2)
    assert lines(tmp_path / "b")[-1]["inputs"]["mix_1"]["clear_why"] == "coming"   # the play's own, while it runs


def seek(tmp_path):
    """A Survive whose `clear` fight runs at the idle zombie 7 at 8 tiles."""
    r, sv = make(tmp_path)
    r.frame()
    tick(r, sv)
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert t.exec.zid == 7 and t.meta["rule"] == "clear"
    return r, sv, t


def test_a_seek_ends_when_a_second_idle_zombie_lists_within_engage_r(tmp_path):
    """Fix 1 (finding 1; E23 113-117 s: the walk toward the idle 26267 while five more listed at 8 to 9 tiles)."""
    r, sv, t = seek(tmp_path)

    class Fight(dict):
        def get(self, k, default=None):
            return "fight"
    t.table.cells = Fight()   # every cell `fight` (the nearest: the seek's own walk): the lapse reads the doctrine
    r.frame(zombies=[z(7, 107.5, 200.0, target=False), z(8, 100.0, 208.0, target=False)])
    tick(r, sv)
    ends = [x for x in lines(tmp_path, TD.PLAYS_LOG) if x["kind"] == "play_end"]
    assert ends[-1]["end"] == "lapsed" and ends[-1]["play"] == "fight"
    line = lines(tmp_path)[-1]
    assert line["inputs"]["play"]["type"] != "fight" and line["inputs"]["tactician"]["table"] == "lapsed"


def test_a_seek_ends_when_its_zombie_stops_reading_reachable(tmp_path, monkeypatch):
    r, sv, t = seek(tmp_path)
    monkeypatch.setattr(sv, "_engageable", lambda zid, z: False)
    r.frame(zombies=[z(7, 107.5, 200.0, target=False)])
    tick(r, sv)
    assert t.exec.play.play != "fight"
    assert [x for x in lines(tmp_path, TD.PLAYS_LOG) if x["kind"] == "play_end"][-1]["end"] == "lapsed"


def test_a_seek_runs_on_when_its_zombie_turns_aware_or_comes_within_danger_r(tmp_path):
    """The lapse reads an idle zombie beyond DANGER_R only: a chaser, or one within DANGER_R, is the tactician's own
    `fight` rule's (two are fought one at a time, the nearest first)."""
    r, sv, t = seek(tmp_path)
    r.frame(zombies=[z(7, 107.5, 200.0, target=True), z(8, 100.0, 208.0, target=False)])
    tick(r, sv)
    assert t.exec.zid == 7
    r, sv, t = seek(tmp_path / "b")
    r.frame(zombies=[z(7, 105.5, 200.0, target=False), z(8, 100.0, 208.0, target=False)])
    tick(r, sv)
    assert t.exec.zid == 7


def test_two_idle_zombies_within_engage_r_are_not_sought(tmp_path):
    r, sv = make(tmp_path)
    for _ in range(3):
        r.frame(zombies=[z(7, 107.0, 200.0, target=False), z(8, 100.0, 208.0, target=False)])
        tick(r, sv)
    mx = lines(tmp_path)[-1]["inputs"]["mix_1"]
    assert mx["play"] != "fight" and mx["clear"] is None


def test_a_zombie_inside_a_house_the_character_is_outside_of_is_not_sought(tmp_path):
    """The ladder's `_engageable` reading, called on the instance: the zombie is on the far side of the walls."""
    r, sv = make(tmp_path, grid=False)
    r.scan(house(1, 105, y0=199) + [PO_square(x, y) for x in range(95, 102) for y in range(195, 205)])
    for _ in range(2):
        r.frame(zombies=[z(7, 106.5, 200.5, target=False)])
        tick(r, sv)
    mx = lines(tmp_path)[-1]["inputs"]["mix_1"]
    assert mx["clear"] is None and mx["play"] != "fight"


def test_a_model_answer_that_is_no_fight_while_clear_binds_is_vetoed(tmp_path):
    r, sv = make(tmp_path)
    r.scan(open_grid() + house(1, 80))
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    t = sv.control_state["mix_1"] = MD.Mix1(sv, source=FakeSource(), table=M.Table())
    t.mode = "model"
    tick(r, sv)
    assert t.exec.play.play == "fight"
    view = t.view()
    b = next(x["label"] for x in view["buildings"])
    t.source.out = {"play": "loot", "building": b, "want": "any", "bound": "looted", "why": "clear"}
    r.frame(zombies=[z(7, 108.0, 200.0, target=False)])
    tick(r, sv)
    tac = lines(tmp_path)[-1]["inputs"]["tactician"]
    assert tac["refused"] == {"why": "doctrine"} and t.exec.play.play == "fight"


def test_a_crawler_near_a_bleed_is_finished_first_and_the_dressing_waits(tmp_path):
    r, sv = make(tmp_path, caps=MELEE_CAPS)
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(zombies=[crawler(9, 101.5, 200.0)], wounds=BLEED)
    tick(r, sv)
    line = lines(tmp_path)[-1]
    mx, tac = line["inputs"]["mix_1"], line["inputs"]["tactician"]
    assert (mx["piece"], mx["added"], mx["play"], mx["target"], tac["guard"]) == ("guard.crawler", True, "fight", 9,
                                                                                 "crawler")
    assert line["action"]["type"] == "melee" and line["action"]["args"]["mode"] == "finish"
    t = sv.control_state["mix_1"]
    r.event("zombie_dead", id=9)                                  # the crawler dead and gone
    r.frame(zombies=[], wounds=BLEED)
    tick(r, sv)
    assert t.exec.play.play == "dress"


def test_the_tactician_alone_dresses_with_the_crawler_beside_it(tmp_path):
    """The control for the previous test."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="tactician")
    sv.control_state["tactician"] = TD.Tactician(sv, table=TT.Table())
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(zombies=[crawler(9, 101.5, 200.0)], wounds=BLEED)
    tick(r, sv)
    assert lines(tmp_path)[-1]["inputs"]["play"]["kind"] == "dress"


def test_a_running_dress_is_cut_by_a_crawler_coming_within_keep_r(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=11, fullType="Base.Bandage", weight=0.1, use="bandage")
    r.frame(wounds=BLEED)
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert t.exec.play.play == "dress"
    r.frame(zombies=[crawler(9, 102.0, 200.0)], wounds=BLEED)
    tick(r, sv)
    assert t.exec.play.play == "fight" and t.exec.zid == 9
    assert lines(tmp_path)[-1]["inputs"]["mix_1"]["piece"] == "guard.crawler"


def test_a_standing_zombie_within_keep_r_is_met_before_the_crawler(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[crawler(9, 101.5, 200.0), z(7, 102.0, 201.0)])
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert t.exec.play.play == "fight" and t.exec.zid == 7
    assert lines(tmp_path)[-1]["inputs"]["mix_1"]["piece"] != "guard.crawler"


def test_a_retreat_is_never_cut_for_a_crawler(tmp_path):
    r, sv = make(tmp_path, grid=False)
    r.scan(house(1, 90, y0=199) + [PO_square(x, y) for x in range(93, 108) for y in range(196, 205)])
    group = [z(7, 104.0, 200.0), z(8, 103.0, 202.0), z(9, 103.0, 198.0)]
    r.frame(zombies=group)
    t = sv.control_state["mix_1"]
    view = t.view()
    t._start(P.validate({"play": "avoid", "toward": "D1", "gait": "walk", "bound": "clear", "why": "group"}, view),
             view, V.binding(sv.world, view), "model")
    r.frame(zombies=group + [crawler(11, 101.5, 200.0)])
    assert t._guard(t.view()) is None


def test_the_crawler_s_finish_is_held_against_a_trigger_s_fight_at_a_standing_zombie_farther_off(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[crawler(9, 101.5, 200.0)])
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert t.exec.zid == 9
    r.advance(TD.TABLE_HOLD_S)
    for _ in range(3):
        r.frame(zombies=[crawler(9, 101.5, 200.0), z(7, 104.5, 200.0)])   # a chaser at 4.5: the `fight` rule's
        tick(r, sv)
    assert t.exec.zid == 9
    starts = [x for x in lines(tmp_path, TD.PLAYS_LOG) if x["kind"] == "play"]
    assert len(starts) == 1
    assert any(x["inputs"]["tactician"].get("table") == "held" for x in lines(tmp_path))


def test_a_finish_at_hand_is_held_against_a_trigger_s_travel(tmp_path):
    """Trial 10's ring (15436 knocked down at 0.9, the crawler at 2.2): the tactician's table hands the finish to a
    travel on a `down` trigger; mix_1 holds it."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 101.5, 200.0)])
    tick(r, sv)
    t = sv.control_state["mix_1"]
    assert t.exec.zid == 7
    r.advance(TD.TABLE_HOLD_S)
    for _ in range(3):
        r.frame(zombies=[z(7, 100.9, 200.0, floor=True)])        # knocked down at 0.9: the `down` trigger
        tick(r, sv)
    assert t.exec.zid == 7 and lines(tmp_path)[-1]["inputs"]["play"]["type"] == "fight"
    assert [x for x in lines(tmp_path) if x["inputs"]["tactician"].get("table") == "held"]


def test_a_crawler_nearer_than_a_running_finish_takes_it_and_one_farther_does_not(tmp_path):
    """Trial 10's ring at 62 s: the crawler biting at 0.9 while the knocked-down 15436 at 2.0 is finished."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 102.0, 200.0, floor=True)])
    t = sv.control_state["mix_1"]
    view = t.view()
    t._start(P.validate({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}, view), view,
             V.binding(sv.world, view), "doctrine", rule="fight")
    r.frame(zombies=[z(7, 101.0, 200.0, floor=True), crawler(9, 100.0, 201.2)])   # the finish nearer: kept
    assert t._guard(t.view()) is None
    r.frame(zombies=[z(7, 102.0, 200.0, floor=True), crawler(9, 100.0, 200.9)])   # the crawler nearer: it takes it
    assert t._guard(t.view())[0] == "crawler"
    r.frame(zombies=[z(7, 101.0, 200.0, floor=True), crawler(9, 100.0, 200.9)])   # within REPIN_MARGIN: kept
    assert t._guard(t.view()) is None


def test_a_lone_zombie_re_pins_a_running_fight_at_one_beyond_engage_r(tmp_path):
    """F15's ring: a table fight at the idle 16038 at 9.9 held on while the aware 16032 came at 8.7."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(8, 109.9, 200.0, target=False)])
    t = sv.control_state["mix_1"]
    view = t.view()
    t._start(P.validate({"play": "fight", "target": "Z1", "bound": "dead", "why": "clear"}, view), view,
             V.binding(sv.world, view), "table", rule="s0")
    r.frame(zombies=[z(8, 109.9, 200.0, target=False), z(7, 100.0, 208.7)])
    tick(r, sv)
    mx = lines(tmp_path)[-1]["inputs"]["mix_1"]
    assert (mx["piece"], mx["target"], mx["started"]) == ("rule.clear", 7, True)


def test_the_tactician_s_own_doctrine_runs_unchanged_under_mix_1(tmp_path):
    """A lone chaser beyond reach is met standing in the stance (the tactician's `fight` rule): the line names it so."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(7, 104.0, 200.0)], health=20.0)
    tick(r, sv)
    line = lines(tmp_path)[-1]
    assert line["branch"] == "threat" and "flee" not in line["inputs"]["branches"]["threat"]
    assert line["inputs"]["play"] == {"kind": "fight", "type": "fight", "play_id": 1, "target": 7}
    assert (line["action"]["args"]["vx"], line["action"]["args"]["vy"]) == (0.0, 0.0)
    mx = line["inputs"]["mix_1"]
    assert (mx["piece"], mx["added"]) == ("rule.fight", False)


@pytest.mark.parametrize("meta, piece", [
    ({"source": "guard", "rule": "swing"}, "guard.swing"), ({"source": "doctrine", "rule": "clear"}, "rule.clear"),
    ({"source": "table", "rule": "s0|k0"}, "table"), ({"source": "model", "rule": None}, "model"), ({}, None)])
def test_each_play_s_starter_names_its_piece(meta, piece):
    assert MD.piece_of(meta) == piece


def test_the_guards_are_the_tactician_s_three_and_the_crawler():
    assert TD.GUARDS == ("hit", "swing", "fallen") and set(MD.ADDED) == {"rule.clear", "guard.crawler"}
    assert M.RULE_NAMES == F.RULE_NAMES[:5] + ("clear",) + F.RULE_NAMES[5:]
    assert X.MELEE_API == "1.10"                                 # Task 2's three-field MeleeInputs on main


# ================================================================ the copies cannot drift (fix 1, finding 5)
def _body(fn):
    """`fn`'s source lines, dedented, its docstring and blank lines dropped, each line stripped of a trailing comment
    that follows code."""
    import ast
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(fn))
    node = ast.parse(src).body[0]
    doc = node.body[0] if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) else None
    lines = src.splitlines()
    skip = set(range(doc.lineno - 1, doc.end_lineno)) if doc is not None else set()
    out = []
    for i, ln in enumerate(lines):
        if i in skip or not ln.strip():
            continue
        code = ln.split("   # ")[0].rstrip()
        out.append(code)
    return out


def _diff(a, b):
    import difflib
    return [ln for ln in difflib.unified_diff(a, b, lineterm="", n=0)
            if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]


ASSESS_DIFF = [
    '-    prepare(sv)',
    '+    TD.prepare(sv)',
    '+    self._clear, self._clear_id = self._clear_label(view)',
    '+    self._by_clear = False',
    '+    started_at = self.play_id',
    '-            if r["_play"] is not None and R.violations(self._masked(view), r["_play"].row()):',
    '+            if r["_play"] is not None and self._veto(view, r["_play"].row()):',
    '-            play, src, rule = self._table(view)',
    '+            play, src, rule = self._doctrine(view) if why == "lapsed" else self._table(view)',
    '+            if why == "rule" and self._by_clear:',
    '+                rule = "clear"',
    '-                            end="doctrine" if why in ("rule", "veto") else "replaced")',
    '+                            end="doctrine" if why in ("rule", "veto") else ("lapsed" if why == "lapsed" else',
    '+                                                                             "replaced"))',
    '+                if rule == "clear":',
    '+                    t = self.exec.target()',
    '+                    self.meta["clear_why"] = "coming" if t is not None and chasing(t) else "idle"',
    '+            elif why == "lapsed":',
    '+                self.meta = dict(self.meta, source=src, rule=rule, clear_why=None)',
    '+    piece = piece_of(self.meta)',
    '+    target = line_play.get("target")',
    '+    if target is None and isinstance(ex, X.DressExec):',
    '+        target = ex.play.args.get("part")',
    '+    inputs[STATE_KEY] = {"piece": piece, "clear_why": self.meta.get("clear_why"), "added": piece in ADDED,',
    '+                         "started": self.play_id != started_at, "kind": ex.label, "play": ex.play.play,',
    '+                         "target": target, "clear": self._clear_id}',
]
TABLE_DUE_DIFF = [
    '+    if self._lapsed(ex):',
    '+        return "lapsed"',
    '-    if T.bound(masked):',
    '+    if M.bound(masked):',
    '-        if ans is not None and ans["play"] != ex.play.play:',
    '+        lone = M.clear_due(masked)',
    '+        if ans is not None and (ans["play"] != ex.play.play or (',
    '+                lone and isinstance(ex, X.FightExec) and ex.zid != self._clear_id)):',
    '+            self._by_clear = lone and not (M.fight_due(masked) or M.dress_due(masked))',
    '-    if self.source is None and fired and (any(t in INTERRUPTS for t in fired) or ex.age() >= TABLE_HOLD_S):',
    '+    if self.source is None and fired and (any(t in TD.INTERRUPTS for t in fired) or ex.age() >= TD.TABLE_HOLD_S):',
]


@pytest.mark.parametrize("name, named", [("assess", ASSESS_DIFF), ("_table_due", TABLE_DUE_DIFF)])
def test_each_copied_body_differs_from_the_tactician_s_only_at_its_named_lines(name, named):
    """Fix 1 (finding 5): `Mix1.assess` and `Mix1._table_due` are copies of the tactician's (829038d6); a change to the
    tactician's body, or to the copy beyond the named lines, fails here, so a later tactician fix is carried by hand
    and never lost silently."""
    got = _diff(_body(getattr(TD.Tactician, name)), _body(getattr(MD.Mix1, name)))
    assert got == named, "\n".join(got)
