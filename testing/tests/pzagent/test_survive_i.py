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
