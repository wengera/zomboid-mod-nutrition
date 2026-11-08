"""Survival 15 (survival iteration 14; Plan 25 Task 7; F4, `f_goals_5-20261030-180527`, and E12,
`e_day_12-20261030-175041`). The fake mod over PZA/1.7.

- P25-G, the shelter shun loop (F4: 67 Shelter answers for its one building flagged `s`, 57 failed `shun` within 1.5 s,
  never cooled since each had sent a walk): a Shelter started on a building the kit shuns ends `failed "shunned"`
  before any plan or walk, its stamp untouched; the runner cools a goal failed `shun`, `shunned`, `no plan` or `no
  door` whatever it sent, its refusal carried to the next view as `{end: "cooled", why: "shunned"}`; the prompt says
  what the `s` flag means for the choice. (`llm.place_error`'s refusal is in `test_llm.py`, `why_of` in
  `test_view.py`.)
- P25-H, the unwear under a goal (F4: part 8 bled on 904 lines, every cotton garment worn, no idle tick for the stock):
  the bleeding step's last step is the unwear of the least-covering worn cotton garment on a quiet care tick, ahead of
  a running goal; never under the ride or a zombie within DISENGAGE_R; the rip of an unworn garment first.
- P25-I, the corner's third branch logged (E12: 22 repeated shoves, `corner` on 0 lines): the shove again after a
  missed shove while the swing is divided logs `corner` {kind "shove", shoved, n, sore}.
"""
import pytest

from agent.base.planner import care as C
from agent.base.planner import goals as G
from agent.base.planner import llm as L
from agent.base.planner import survive as S
from agent.base.planner.goals import GoalRunner, LootBuilding, Shelter
from agent.base.planner.night import SHUN_MIN
from agent.base.planner.survive import Survive

from .fakemod import DEFAULT_HELLO
from .test_goals import Src, inside
from .test_night import house
from .test_policies import FRIDGE, Rig, all_sends_valid
from .test_survive import last, threat_why, tick
from .test_survive_g import care_frame, care_why, part
from .test_survive_n import SHIRT, TSHIRT, bleed, unwear_rig, worn
from .test_survive_t import shoved
from .test_survive_q import z


# ================================================================ P25-G: the shelter shun loop
def test_a_shelter_started_on_a_shunned_building_ends_failed_shunned_before_any_walk_its_stamp_unchanged(tmp_path):
    """F4's goals 2-76: building 8 shunned, a Shelter of it walked and failed `shun`. Now the goal ends at its start,
    `failed "shunned"`, no command sent, the shun's stamp (450, SHUN_MIN not yet spent at 500) left as it was, and the
    goal is cooled (it sent nothing)."""
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, game_min=500.0)
    store = {1: 450.0}
    g = Shelter(1)
    runner = GoalRunner(Src(g), r.clock, shunned=store)
    assert runner.tick(r.world, r.acts) is None
    assert (g.state, g.reason) == ("failed", "shunned") and g.plan is None
    assert store == {1: 450.0} and r.acts.history == []
    assert runner.cooling() == [{"type": "Shelter", "args": {"building": 1}}]
    r.frame(x=100.0, y=201.5, game_min=450.0 + SHUN_MIN)          # past SHUN_MIN: the plan walks again
    g2 = Shelter(1)
    r.advance(G.GOAL_COOL_S)
    runner2 = GoalRunner(Src(g2), r.clock, shunned=store)
    cmd = runner2.tick(r.world, r.acts)
    assert cmd is not None and cmd.TYPE == "walkTo" and g2.running


def shelter_shunned(r):
    """A Shelter of building 2 (its one door locked) from 9.5 tiles off: the walk, then the open refused `locked`, so
    the machine shuns it (`failed "shun"`) having sent two commands."""
    r.scan(house(2, 110, door={"open": False, "locked": True, "barricaded": False}))
    r.frame(x=100.0, y=201.5, game_min=500.0)
    src = Src(Shelter(2), Shelter(2), Shelter(2))
    runner = GoalRunner(src, r.clock)
    sent = []
    for pos in ((100.0, 201.5), (109.5, 201.5)):
        r.frame(x=pos[0], y=pos[1], game_min=500.0)
        cmd = runner.tick(r.world, r.acts)
        runner.send(cmd)
        sent.append(cmd.TYPE)
        r.answer() if cmd.TYPE == "walkTo" else r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=109.5, y=201.5, game_min=501.0)
    runner.tick(r.world, r.acts)
    assert sent == ["walkTo", "interact"]
    return runner, src


def test_the_runner_cools_a_shelter_failed_shun_after_a_sent_walk_and_carries_the_refusal_as_shunned(tmp_path):
    """Ruling P25-G (4): F4's Shelters each sent a walk first, so `sent_n == 0` never cooled them. A goal failed `shun`
    is cooled whatever it sent: the next proposal of it within GOAL_COOL_S is refused, and the view after carries it as
    `last_goal` `{end: "cooled", why: "shunned"}` (Task 4's refusal path, `why_of`'s new meaning)."""
    r = Rig(tmp_path)
    runner, src = shelter_shunned(r)
    assert [(h["state"], h["reason"]) for h in runner.history] == [("failed", "shun")]
    assert runner.why["refused"] == {"type": "Shelter", "args": {"building": 2}}   # proposed again on the same tick
    assert runner.refusal == {"type": "Shelter", "args": {"building": 2}, "end": "cooled", "why": "shunned"}
    r.advance(1.0)
    runner.tick(r.world, r.acts)
    assert src.views[-1]["last_goal"] == {"type": "Shelter", "args": {"building": 2}, "end": "cooled",
                                          "why": "shunned"}
    all_sends_valid(r)


@pytest.mark.parametrize("reason", ("shun", "shunned", "no plan", "no door"))
def test_every_shun_reason_cools_whatever_was_sent(tmp_path, reason):
    """`goals.COOL_REASONS`: `shun`, `shunned`, `no plan`, `no door`, each cooled with commands sent; `goal budget` with
    commands sent is not (the rule before P25-G)."""
    assert G.COOL_REASONS == ("shun", "shunned", "no plan", "no door")
    r = Rig(tmp_path)
    r.frame()
    for why, cooled in ((reason, True), ("goal budget", False)):
        runner = GoalRunner(Src(), r.clock)
        g = Shelter(3)
        g.started_wall, g.sent_n = r.clock(), 2
        g.end("failed", why)
        runner._close(g)
        assert bool(runner.cooling()) is cooled, why


def test_the_prompt_says_what_the_s_flag_means_for_the_choice():
    """Ruling P25-G (5): the building line's `s` sentence, the refusal rule's Shelter clause, the strategy's third line's
    clause and the `shunned` why's meaning, each once (exact substrings; SHUN_MIN rendered as its number: the prompt
    names no constant, `test_system_names_no_path_credential_or_planner_internal`)."""
    s = ("s shunned (its shelter failed within the last %g game minutes: not a shelter now; with no other building "
         "listed, ExploreToward a square along a road toward unknown ground to find one, or Rest when hold reads)"
         % SHUN_MIN)
    for text in (s, "choose Shelter in a listed building over a LootBuilding, never a building flagged s;",
                 "a Shelter only a building listed without the s flag",
                 "shunned: its shelter failed, every door of it tried; passed over for %g game minutes." % SHUN_MIN):
        assert L.SYSTEM.count(text) == 1, text


# ================================================================ P25-H: the unwear under a goal
def test_a_bleeding_part_with_every_cotton_garment_worn_unwears_the_least_covering_on_a_quiet_tick(tmp_path):
    """F4's line from game minute 1351: part 8 bleeding, nothing held, belt, skinny trousers, shoes, socks and a T-shirt
    worn. `Care.choose()` on a quiet tick answers the unwear of the T-shirt (covering 3, under the shirt's 7; never the
    trousers or the shoes), logged with the part; not quiet, or riding, None (the goal keeps the tick)."""
    r, sv = unwear_rig(tmp_path)
    c = sv.care
    c.quiet = True
    cmd = c.choose()
    assert (cmd.TYPE, cmd.itemId) == ("unwear", 20)
    assert c.why == {"reason": "unwear", "part": 9, "item": 20, "loc": TSHIRT, "cover": 3.0}
    c.quiet = False
    assert c.choose() is None
    c.quiet, c.ride_now = True, True
    assert c.choose() is None
    c.ride_now, c.unwear_wound = False, False   # the switch off: the bleeding step does not unwear (the stock may)
    assert c.choose() is None


def test_an_unworn_cotton_garment_held_is_ripped_never_the_unwear(tmp_path):
    r, sv = unwear_rig(tmp_path)
    r.event("item_added", itemId=30, fullType="Base.Tshirt_Blue", weight=0.2, use="clothing", rip="cotton",
            clothing={"loc": TSHIRT, "bite": 1.0, "scratch": 1.0})
    c = sv.care
    c.quiet = True
    cmd = c.choose()
    assert (cmd.TYPE, cmd.itemId) == ("rip", 30) and c.why["reason"] == "no_rag"
    assert c._unwear_step()[0] is not None   # an unwear was possible, and the rip took precedence


def test_after_the_unwear_s_done_the_still_worn_garment_waits_then_is_ripped_once_read_unworn(tmp_path, monkeypatch):
    """The settle (WEAR_SETTLE_MAX frames after the done while the garment still reads worn): nothing is unworn or
    ripped; once the Lua's item_changed reads it unworn, the next care tick rips it (P24-AJ's `unworn_item`).
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = unwear_rig(tmp_path)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and care_why(tmp_path)["reason"] == "unwear"   # the bleeding step's
    r.fake.answer({"unwear": ["accepted", {"state": "done", "result": {"itemId": 20, "loc": TSHIRT}}]})
    r.pump()
    for _ in range(3):
        bleed(r)
        tick(r, sv)
        assert care_why(tmp_path).get("reason") is None
    assert sum(1 for a in r.acts.history if a.type in ("unwear", "rip")) == 1
    assert r.world.frame_n < r.world.act_n[str(sv.care.sends[20].aid)] + C.WEAR_SETTLE_MAX
    r.event("item_changed", itemId=20, use="clothing", rip="cotton", clothing={"loc": TSHIRT, "bite": 1.0,
                                                                               "scratch": 2.0})
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 20}) and care_why(tmp_path)["reason"] == "no_rag"
    all_sends_valid(r)


def goal_rig(tmp_path):
    """A PZA/1.7 build, the T-shirt and the shirt worn, building 1 with a fridge, a LootBuilding(1) goal sent and
    running (no wound yet), no zombie."""
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(LootBuilding(1)))
    r.fake.hello(mod="1.7.0")
    r.pump()
    r.scan([inside(101, 200, containers=[FRIDGE])])
    worn(r, 20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0)
    worn(r, 21, "Base.Shirt_FormalWhite", SHIRT, 2.0, 5.0)
    care_frame(r, [part(9)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "goal" and r.acts.current is not None
    return r, sv


def test_through_survive_the_care_s_unwear_pre_empts_a_running_goal_on_a_quiet_tick(tmp_path, monkeypatch):
    """F4's 903 goal lines: the care branch, before the goal's, sends the unwear while the goal's loot runs; its line
    is the care branch's with the why. With UNWEAR_WOUND off the goal keeps the tick (the stock waits for an idle one).
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = goal_rig(tmp_path)
    goal_cmd = r.cmd()
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path) == {"reason": "unwear", "part": 9, "item": 20, "loc": TSHIRT, "cover": 3.0}
    (tmp_path / "off").mkdir()
    r2, sv2 = goal_rig(tmp_path / "off")
    sv2.UNWEAR_WOUND = False
    bleed(r2)
    tick(r2, sv2)
    assert r2.cmd() == goal_cmd and last(tmp_path / "off")["branch"] == "goal"
    assert not any(a.type == "unwear" for a in r2.acts.history)


def test_with_the_switch_off_the_idle_stock_unwears_as_before(tmp_path, monkeypatch):
    """`Survive.UNWEAR_WOUND` off (`T4_SWITCHES`, the replay tests' `pre_t4`): P24-AJ's idle stock's unwear, its why under
    the care's `stock`.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    assert S.T4_SWITCHES[0] == "UNWEAR_WOUND" and S.Survive.UNWEAR_WOUND is True   # named change, Plan 25 Task 8:
    # iteration 14's second half adds its switches after it (`test_survive_v`)
    r, sv = unwear_rig(tmp_path)
    sv.UNWEAR_WOUND = False
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})
    assert care_why(tmp_path)["stock"] == {"reason": "unwear", "item": 20, "loc": TSHIRT, "cover": 3.0}


def test_a_build_without_unwear_has_the_bleeding_step_want_the_bandage(tmp_path):
    """Plan 28 Task 7b fix 1, a named fixture correction: the build's caps off the fake's PZA/1.7 caps (no PZA/1.8
    `melee`, which a build without `unwear` cannot announce)."""
    caps = tuple(t for t in DEFAULT_HELLO["caps"] if t != "unwear")
    r, sv = unwear_rig(tmp_path, caps=caps)
    tick(r, sv)
    assert not any(a.type == "unwear" for a in r.acts.history) and care_why(tmp_path).get("want") == "bandage"


# ================================================================ P25-I: the corner's third branch logged
def test_a_missed_shove_at_a_lone_target_while_sore_is_shoved_again_with_the_corner_logged(tmp_path):
    """E12's 22 repeated shoves under the `wounded` hold (armPain 44, one zombie in reach): the corner's third branch
    sends the shove again and logs `corner` {kind shove, shoved, n 1, sore true} beside the shove's own keys."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1})
    assert w["corner"] == {"kind": "shove", "shoved": 1, "n": 1, "sore": True} and w["shove"] == "strain"
