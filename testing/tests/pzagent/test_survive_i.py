"""Survival 9 (Plan 24 Task 21, spec § 6 item 19; the eighth chain's E8, `e_day_8-20261029-174023`: four kills, then
two bites, one bandaged, the other bleeding 73 game minutes to the death with no dressing held; from game minute 618
every goal walk failed `no square`, 62 to 234 tiles off; fight 1's `many` fired on three held, two of them idle):
refactor A (a pure ordered `assess`, the water chain lifted out), P24-AB (the rag stock), P24-AC (legged far walks),
P24-AD (idle zombies and `many`). The fake mod over the PZA/1.5 skills."""
import json

from agent.base.planner import survive as S
from agent.base.planner import water as W

from .test_survive import make, tick


# ================================================================ refactor A
def test_assess_decides_without_sending_or_writing_and_apply_sends_and_logs(tmp_path):
    """Refactor A: `assess` returns the Decision (branch, owner, command, inputs) with nothing sent and no line
    written; `_apply` sends it through its owner and appends the line; `tick` is the two."""
    r, sv = make(tmp_path)
    r.frame(zombies=[dict(id=1, x=104.0, y=200.0, dist=4.0, hasTarget=True, crawler=False, health=1.0)])
    sent_before = len(r.acts.history)
    d = sv.assess(sv._read(r.world, r.acts))
    assert isinstance(d, S.Decision) and d.branch == "threat" and d.cmd is not None and d.owner is sv.fight
    assert len(r.acts.history) == sent_before and not (tmp_path / "decision.log").exists()
    assert set(d.inputs["branches"]) == {"threat"} and d.inputs["cooled"] is None
    a = sv._apply(d)
    assert a is r.acts.history[-1] and a.type == d.cmd.TYPE and sv.last_branch == "threat"
    line = json.loads((tmp_path / "decision.log").read_text(encoding="utf-8").splitlines()[-1])
    assert line["branch"] == "threat" and line["sent"] is True and line["action"]["type"] == d.cmd.TYPE


def test_the_water_chain_is_its_own_module_and_survive_re_exports_its_constants():
    """Refactor A (the Task 10 review's ruling 7): `planner/water.py` holds the fill, its constants and its wants."""
    assert (S.FILL_SETTLE_S, S.FILL_RETRY_MIN, S.FILL_WANTS, S.SOURCE_FAILS) == (
        W.FILL_SETTLE_S, W.FILL_RETRY_MIN, W.FILL_WANTS, W.SOURCE_FAILS)
    assert not hasattr(S.Survive, "_fill_plan") and not hasattr(S.Survive, "_check_fills")


def test_survive_s_fills_are_the_water_chain_s(tmp_path):
    r, sv = make(tmp_path)
    assert sv.fills is sv.water.fills
    marks = {"container": 1.0, "water_source": 2.0, "water": 3.0}
    sv.water.why = {"want": "water_source"}
    sv.water.wants(marks, 9.0)
    assert marks == {"water_source": 9.0, "water": 3.0}
    W.Water.clear(marks)
    assert marks == {"water": 3.0}


# ================================================================ P24-AB: the rag stock
from agent.base.planner import care as C   # noqa: E402
from agent.base.planner import goals as G   # noqa: E402
from agent.base.planner import view as V   # noqa: E402

from .test_survive import last   # noqa: E402
from .test_survive_g import care_frame, care_why, garment, hello152, hold, part   # noqa: E402
from .test_survive_h import goal_walking   # noqa: E402
from .test_policies import all_sends_valid, zombie   # noqa: E402


def stock_rig(tmp_path, *dressings):
    """A PZA/1.5.2 build (the item record's `worn` and `rip`), a looted unworn cotton shirt (22) and a worn T-shirt
    (20) held, and `dressings` [(id, fullType)] held; no part bleeding, no zombie."""
    r, sv = make(tmp_path)
    hello152(r)
    garment(r, 20, ft="Base.Tshirt_WhiteLongSleeveTINT", rip="cotton", worn=True)
    r.frame()
    garment(r, 22, rip="cotton")
    for iid, ft in dressings:
        hold(r, iid, ft)
    care_frame(r, [part(5)])
    return r, sv


def test_the_rag_stock_constant():
    """Ruling P24-AB: two clean dressings (Angus: "a couple clean rags")."""
    assert C.RAG_STOCK == 2 and "RAG_STOCK" in C.__all__


def test_an_idle_tick_with_no_dressing_rips_the_unworn_cotton_garment_for_the_stock(tmp_path):
    """P24-AB: no threat, nothing running, no wound, no dressing held, an unworn cotton shirt held: the care branch
    rips it (its why `stock`), never the worn T-shirt; the goal does not run that tick."""
    r, sv = stock_rig(tmp_path)
    tick(r, sv)
    d = last(tmp_path)
    assert d["branch"] == "care" and r.cmd() == ("rip", {"itemId": 22})
    assert care_why(tmp_path)["stock"] == {"reason": "stock", "item": 22, "dressings": 0, "stock": 2}
    assert "goal" not in d["inputs"]["branches"] and sv.care.last is r.acts.history[-1]
    all_sends_valid(r)


def test_one_bandage_held_still_rips_and_two_dressings_rip_nothing(tmp_path):
    """P24-AB: fewer than RAG_STOCK clean dressings rips; a bandage and a clean rag (two) rips nothing, the goal runs;
    a dirty rag is no clean dressing."""
    r, sv = stock_rig(tmp_path, (10, "Base.Bandage"), (11, "Base.RippedSheetsDirty"))
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22}) and care_why(tmp_path)["stock"]["dressings"] == 1
    (tmp_path / "b").mkdir()
    r2, sv2 = stock_rig(tmp_path / "b", (10, "Base.Bandage"), (12, "Base.RippedSheets"))
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] == "goal" and not any(a.type == "rip" for a in r2.acts.history)


def test_the_stock_never_rips_with_a_threat_held(tmp_path):
    """P24-AB: a zombie at 4 tiles: the threat branch answers; and one idle at 9.5 tiles (beyond ENGAGE_R, within
    DISENGAGE_R: no engage, the goal runs) is no quiet tick either."""
    r, sv = stock_rig(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and not any(a.type == "rip" for a in r.acts.history)
    (tmp_path / "b").mkdir()
    r2, sv2 = stock_rig(tmp_path / "b")
    r2.frame(zombies=[dict(zombie(1, 109.5, 200.0), hasTarget=False)])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care" and not any(a.type == "rip" for a in r2.acts.history)


def test_the_stock_never_supersedes_a_running_drink(tmp_path):
    """P24-AB (Task 10's objection): thirsty with water held, the drink goes first; while it runs (accepted, the
    thirst read back under THIRST_T) the need holds it and nothing is ripped; once it ended the idle tick rips."""
    r, sv = stock_rig(tmp_path)
    hold(r, 30, "Base.WaterBottle", use="water")
    care_frame(r, [part(5)], thirst=0.5)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 30}) and last(tmp_path)["branch"] == "need"
    r.fake.answer({"consume": ["accepted"]})
    r.pump()
    care_frame(r, [part(5)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "need" and not any(a.type == "rip" for a in r.acts.history)
    r.fake.answer({"consume": ["done"]})
    r.pump()
    care_frame(r, [part(5)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22})


def test_the_stock_never_supersedes_a_running_goal_walk(tmp_path):
    """P24-AB: the goal's walk running (accepted, not ended), the shirt looted meanwhile: the goal branch holds,
    nothing ripped; once the walk ended the idle tick rips (before the goal's next step)."""
    r, sv = make(tmp_path)
    hello152(r)
    r.frame()
    walk = goal_walking(r, sv)
    garment(r, 22, rip="cotton")
    r.frame()
    tick(r, sv)
    assert last(tmp_path)["branch"] == "goal" and r.acts.current is walk
    assert not any(a.type == "rip" for a in r.acts.history)
    r.fake.answer({"walkTo": ["done"]})
    r.pump()
    r.frame()
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22}) and last(tmp_path)["branch"] == "care"


def test_a_bleeding_part_with_no_dressing_and_no_unworn_cotton_wants_bandage(tmp_path):
    """P24-AB: part 9 bleeding, nothing held but the worn T-shirt (E8 from game minute 617: no bandage, rag or unworn
    cotton): the care branch marks the want `bandage` (logged `want`), the view lists it, the goals' kit takes it
    first, and the scripted source loots the nearest building known to hold a bandage; a dressing found drops the
    want. The worn garment's unwear and rip waits for the Lua's unwear."""
    r, sv = make(tmp_path)
    hello152(r)
    garment(r, 20, ft="Base.Tshirt_WhiteLongSleeveTINT", rip="cotton", worn=True)
    r.frame()
    care_frame(r, [part(9, bleeding=True, bleedingTime=14.7)])
    tick(r, sv)
    assert care_why(tmp_path)["want"] == "bandage" and "bandage" in sv.need_marks
    assert sv.goals.kit.wants == ("bandage",)
    v = V.view(r.world, sv)
    assert "bandage" in v["needs_wanted"]
    assert G.wanted_uses(r.world, sv.goals.kit.wants)[0] == "bandage"
    assert not any(a.type == "rip" for a in r.acts.history)
    src = G.ScriptedSource()
    got = list(src.candidates({"needs_wanted": ["bandage"], "buildings": [
        {"id": 4, "dist": 20.0, "holds": {"food": 2}, "looted": False, "containers": 1},
        {"id": 7, "dist": 30.0, "holds": {"bandage": 1}, "looted": False, "containers": 1}]}))
    assert got[0] == G.LootBuilding(7)
    hold(r, 12, "Base.RippedSheets")
    care_frame(r, [part(9, bleeding=True, bleedingTime=14.7)])
    tick(r, sv)
    assert r.cmd()[0] == "bandage" and "bandage" not in sv.need_marks


def test_with_no_want_the_loot_order_is_unchanged():
    assert G.STOCK_WANTS == ("water", "container", "clothing", "food", "bandage", "weapon")
    assert list(G.ScriptedSource().candidates({"needs_wanted": [], "buildings": [
        {"id": 7, "dist": 30.0, "holds": {"bandage": 1}, "looted": False, "containers": 1}]}))[:1] == [G.LootBuilding(7)]


# ================================================================ P24-AC: legged far walks
import math   # noqa: E402

from .test_goals import FRIDGE, Src, inside   # noqa: E402
from .test_policies import Rig   # noqa: E402


def far_runner(r, goal):
    """A runner on `goal` with the player's place scanned already (its first command the walk)."""
    runner = G.GoalRunner(Src(goal), r.clock)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    return runner


def step(r, runner):
    """A tick of the runner (its observe first, as Survive's), the scans answered done; the walk it sent, or None."""
    while True:
        runner.observe(r.world, r.acts)
        cmd = runner.tick(r.world, r.acts)
        if cmd is None:
            return None
        runner.send(cmd)
        if cmd.TYPE != "scan":
            return cmd
        r.answer()
        r.frame(x=r.world.me["x"], y=r.world.me["y"])


def test_the_leg_constants():
    """Ruling P24-AC: legs of at most 30 tiles (inside E8's bracket: 9.4 tiles got a square, 62.7 did not), halved
    down to 10."""
    assert (G.LEG_MAX, G.LEG_MIN) == (30.0, 10.0)


def test_a_100_tile_destination_is_walked_in_30_tile_legs_then_directly(tmp_path):
    """P24-AC: ExploreToward(200, 200) from (100.5, 200.5): each walk a leg along the line to a square centre within
    30 tiles (`why` `leg`, `legLen`), each leg done moving the player there; within 30 tiles the walk is the target's
    own, and its arrival ends the goal done."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5)
    g = G.ExploreToward(200, 200)
    runner = far_runner(r, g)
    legs = []
    while True:
        cmd = step(r, runner)
        me = (r.world.me["x"], r.world.me["y"])
        d = math.hypot(cmd.x - me[0], cmd.y - me[1])
        if (cmd.x, cmd.y) == (200, 200):
            assert math.hypot(200 - me[0], 200 - me[1]) <= G.LEG_MAX and "leg" not in g.why
            break
        assert d <= G.LEG_MAX and d >= G.LEG_MAX - 1.5 and abs(cmd.y - 200.5) <= 0.5 and g.why["legLen"] == 30.0
        assert g.why["leg"] == [cmd.x, cmd.y] and g.state == "running"
        legs.append((cmd.x, cmd.y))
        r.answer()
        r.frame(x=cmd.x, y=cmd.y)
    assert legs == [(129.5, 200.5), (158.5, 200.5), (187.5, 200.5)]   # 29.25 tiles on, each a square's centre
    r.answer()
    r.frame(x=200.2, y=200.3)
    step(r, runner)
    assert (g.state, g.reason) == ("done", "arrived")
    all_sends_valid(r)


def test_a_no_square_leg_halves_to_15_then_10_and_nothing_is_marked(tmp_path):
    """P24-AC: a leg failed `no square` is re-sent at half its length, 15 then 10 tiles (LEG_MIN); at 10 the goal
    fails `no square`; neither the far target nor any leg square is marked stuck (E8's 278 walks each marked their
    target, the edge stepping a square at a time)."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    g = G.ExploreToward(200, 200)
    runner = far_runner(r, g)
    lens = []
    for _ in range(3):
        cmd = step(r, runner)
        lens.append((g.why["legLen"], math.hypot(cmd.x - 100.5, cmd.y - 200.5)))
        assert g.state == "running"
        r.answer({"state": "failed", "reason": "no square"})
        r.frame(x=100.5, y=200.5, game_min=481.0)
    step(r, runner)
    assert lens == [(30.0, 29.0), (15.0, 14.0), (10.0, 9.0)]   # each leg's square centre within its length
    assert (g.state, g.reason) == ("failed", "no square") and r.world.stuck == {}
    assert runner.history[-1]["args"] == {"x": 200, "y": 200}


def test_a_direct_walk_failed_no_square_still_marks_its_target(tmp_path):
    """P24-AC changes legs only: a target within LEG_MAX whose walk fails `no square` is marked, as before."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5, game_min=480.0)
    g = G.ExploreToward(120, 200)
    runner = far_runner(r, g)
    cmd = step(r, runner)
    assert (cmd.x, cmd.y) == (120, 200)
    r.answer({"state": "failed", "reason": "no square"})
    r.frame(x=100.5, y=200.5, game_min=481.0)
    step(r, runner)
    assert (g.state, g.reason) == ("failed", "no square") and (120, 200) in r.world.stuck


def test_a_done_leg_restores_the_full_length(tmp_path):
    """P24-AC: after a halved leg ends done the next leg is LEG_MAX again."""
    r = Rig(tmp_path)
    r.frame(x=100.5, y=200.5)
    g = G.ExploreToward(200, 200)
    runner = far_runner(r, g)
    step(r, runner)
    r.answer({"state": "failed", "reason": "no square"})
    r.frame(x=100.5, y=200.5)
    cmd = step(r, runner)
    assert g.why["legLen"] == 15.0
    r.answer()
    r.frame(x=cmd.x, y=cmd.y)
    step(r, runner)
    assert g.why["legLen"] == 30.0


def test_a_loot_building_container_beyond_leg_max_is_walked_to_in_a_leg_first(tmp_path):
    """P24-AC: LootBuilding's container 45 tiles off: a leg of at most 30 tiles toward it first, then the loot."""
    r = Rig(tmp_path)
    r.scan([inside(145, 200, containers=[FRIDGE])])
    r.frame(x=100.5, y=200.5)
    g = G.LootBuilding(1)
    runner = G.GoalRunner(Src(g), r.clock)
    cmd = step(r, runner)
    assert cmd.TYPE == "walkTo" and math.hypot(cmd.x - 100.5, cmd.y - 200.5) <= G.LEG_MAX and g.why["leg"]
    r.answer()
    r.frame(x=cmd.x, y=cmd.y)
    cmd = step(r, runner)
    assert cmd.TYPE == "interact" and cmd.args()["kind"] == "loot" and cmd.args()["x"] == 145


# ================================================================ P24-AD: idle zombies and `many`
from agent.base import replay_decisions as R   # noqa: E402
from agent.base.planner import policies as P   # noqa: E402

from .test_survive import threat_why   # noqa: E402

E8 = R.os.path.join(R.ARTIFACTS, "e_day_8-20261029-174023")


def zi(zid, x, y, chasing=True):
    return dict(zombie(zid, x, y), hasTarget=chasing)


def fight_on(tmp_path):
    """A fight engaged on one chasing zombie at 5 tiles (the stance's first leg)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zi(1, 105.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight" and threat_why(tmp_path)["fight"] is True
    return r, sv


def test_three_held_with_two_idle_beyond_danger_r_is_no_many_the_fight_stands(tmp_path):
    """P24-AD (E8's fight 1): one chasing at 5 tiles, two idle at 8 and 9.5 (all within the hold radius): no `many`,
    the fight stands; the two waking (chasing) is `many` on that tick."""
    r, sv = fight_on(tmp_path)
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 100.0, 208.0, chasing=False), zi(3, 90.5, 200.0, chasing=False)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("fight") is True and "flee" not in w and sv.mode == "fight"
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 100.0, 208.0), zi(3, 90.5, 200.0)])
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many" and r.cmd()[0] == "steer"


def test_three_chasing_held_is_many(tmp_path):
    r, sv = fight_on(tmp_path)
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 100.0, 208.0), zi(3, 90.5, 200.0)])
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many"


def test_an_idle_zombie_inside_danger_r_still_counts(tmp_path):
    """P24-AD: an idle zombie within DANGER_R counts as before: one chasing at 5 and two idle at 4 and 5.5 is `many`."""
    r, sv = fight_on(tmp_path)
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 100.0, 204.0, chasing=False), zi(3, 94.5, 200.0, chasing=False)])
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many"


def test_the_listing_counts_an_idle_zombie_only_inside_danger_r(tmp_path):
    """P24-AD on the listing (MANY_LISTED_N within LISTED_R): one chasing at 5, one chasing at 9, two idle at 10 and 11
    are no `many` (two counted); with the two chasing, four listed and four pressing: `many` `listed`."""
    r, sv = fight_on(tmp_path)
    far = [zi(3, 110.0, 200.0, chasing=False), zi(4, 100.0, 211.0, chasing=False)]
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 91.0, 200.0)] + far)
    sv.mode = None   # the listing's own read: no running fight's held count
    many, listed = sv._many_read([z for z in r.world.zombies.values() if P.zdist(r.world, z) <= 6.0], 1)
    assert (many, listed) == (False, None)
    r.frame(zombies=[zi(1, 105.0, 200.0), zi(2, 91.0, 200.0), zi(3, 110.0, 200.0), zi(4, 100.0, 211.0)])
    many, listed = sv._many_read([z for z in r.world.zombies.values() if P.zdist(r.world, z) <= 6.0], 1)
    assert (many, listed) == (True, 4)


def test_a_frame_with_no_has_target_counts_every_zombie_as_before(tmp_path):
    """P24-AD reads `hasTarget` false only: a frame that does not carry it (PZA/1.3's records) counts as before."""
    r, sv = fight_on(tmp_path)
    zs = [zi(1, 105.0, 200.0), zi(2, 100.0, 208.0), zi(3, 90.5, 200.0)]
    for z in zs[1:]:
        del z["hasTarget"]
    r.frame(zombies=zs)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many"


def test_e8_line_170_s_many_flee_is_now_the_fight(monkeypatch):
    """P24-AD on E8's record (replayed to line 170, the fight 1 `many` flee: 16318 chasing at 7.497342719768519,
    16316 and 16317 idle at 9.45 and 9.95): the replay fights on; with every zombie counted (the rule before) it flees
    `many` as the record did."""
    rep = R.replay(E8, upto=170)
    w = rep[169]["inputs"]["branches"]["threat"]
    assert rep[169]["branch"] == "threat" and w.get("fight") is True and "flee" not in w

    def old_rule(sv):
        sv._counts_many = lambda z: True
    rep = R.replay(E8, upto=170, mutate=old_rule)
    assert rep[169]["inputs"]["branches"]["threat"]["flee"] == "many" and rep[169]["action"]["type"] == "steer"
