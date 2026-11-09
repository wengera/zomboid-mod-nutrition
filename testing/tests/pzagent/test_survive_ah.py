"""Plan 31 Task 15a (Harden): the ladder's two street defects, `survive.T15_SWITCHES`, each with its killing test, on
the fake mod and on round two's ladder trials where this machine still has them (`testing/runs/` is per-machine and
gitignored, so each replay is skipped where absent: trial 8, `x_trial-ladder-20261106-030051`, the pair; trial 12,
`x_trial-ladder-20261106-031801`, the street). The replays are `replay_decisions.replay` over the run's admin state log
and decision log, open loop: they check the decisions at the situations the runs recorded, never an outcome.

- (a) CHASER_STANCE (the Fight's `chaser_stance` rule, `fight.Fight._chaser_stands`): a Fight not in the stance meets a
  chasing pin within DANGER_R in the stance's standing leg, never the approach walk toward it. Trial 8's line 200: the
  stance count read 3 (over MAX_FIGHT), the approach walk sent an unaimed walkTo at 10095 chasing 5.39 tiles off, which
  closed to 0.26 in 2 s and bit at 101.7 s; trial 12 sent four more (lines 433, 446, 452, 492).
- (b) SCRATCH_DRESS (with DRESS_MANEUVER, on by default since this task: `care.Care.scratch_wanted`, the Dress's
  `wound`, `care_yield.CareYield._wound_yields`): a wound not bleeding (a scratch, #2364's drain) is one Dress, which
  tears a garment when nothing is held, once no zombie stands within KEEP_R, the threat branch yielding to it. Trial 12's
  parts 9 and 6 scratched from line 305 and never dressed (health 92.7 to 16.2), every care line P28-A's `wound_held`
  {clean 0}: no clean dressing past WOUND_RESERVE, and P28-A's step tears nothing.
"""
import glob
import json
import os
import shutil
import tempfile

import pytest

from agent.base.planner import care as C
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers import Dress
from agent.base import replay_decisions as R

from .fakemod import DEFAULT_FRAME
from .test_dress import TSHIRT, hello17, hold, unworn_shirt, worn_shirt
from .test_policies import Rig, all_sends_valid
from .test_survive import decisions, last, make, threat_why, tick
from .test_survive_g import part

T8 = "x_trial-ladder-20261106-030051"
T12 = "x_trial-ladder-20261106-031801"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_the_t15_switches():
    """`survive.T15_SWITCHES`, each on by default, and DRESS_MANEUVER on by default (ruling P31-H)."""
    assert S.T15_SWITCHES == ("CHASER_STANCE", "SCRATCH_DRESS")
    assert T.Threat.CHASER_STANCE is True and S.Survive.SCRATCH_DRESS is True and S.Survive.DRESS_MANEUVER is True
    assert "chaser_stance" in F.FIGHT_RULES


def _off(sv):
    """This task's three switches off on the replay's fresh Survive: the Dress default and T15_SWITCHES."""
    sv.DRESS_MANEUVER = False
    for name in S.T15_SWITCHES:
        setattr(sv, name, False)


@pytest.mark.parametrize("key", ["e5", "f1", "e2", "e3", "e4", "f1-caps15"])
def test_this_task_moves_no_golden(key):
    """The Dress on by default and T15_SWITCHES move no golden: each of the six replayed with the three off is its
    golden file byte for byte, as it is with them on (`test_replay_decisions`' byte-for-byte tests): no golden's
    frames reach the care branch with a wound (F1's parts decode no `bleeding`, the E records' hellos announce none of
    the PZA/1.5 skills), nor a non-stance Fight at a chaser with `aim` announced."""
    with open(R.golden_path(key), "rb") as f:
        raw = f.read()
    head = json.loads(raw.decode("utf-8"))
    caps = R.HELLO_CAPS.get(key)
    rows = R.run(os.path.join(R.ARTIFACTS, R.RUNS[key]), caps=caps, mutate=_off)
    text = R.golden_text(rows, head["base"], head["artifact"], head["recorded"], head.get("span"), head.get("caps"))
    assert text.encode("utf-8") == raw


# ================================================================ (a) the chaser met in the stance
def zd(zid, x, y=200.0, chasing=True, floor=False):
    return {"id": zid, "x": x, "y": y, "dist": abs(x - 100.0), "hasTarget": chasing, "crawler": False, "health": 1.0,
            "onFloor": floor}


def walk_fight(r, rules=None, stance=False):
    """A Fight not in the stance (Survive's `stance` False: a stance count over MAX_FIGHT), its rules the defaults."""
    f = F.Fight(r.world, r.acts, r.clock)
    f.stance = stance
    if rules is not None:
        f.rules = rules
    return f


@pytest.mark.parametrize("x, chasing, rule, want", [(105.0, True, True, "aim"), (105.0, True, False, "walkTo"),
                                                    (105.0, False, True, "walkTo"), (107.0, True, True, "walkTo")])
def test_a_chaser_within_danger_r_is_met_standing_not_walked_to(tmp_path, x, chasing, rule, want):
    """(a): a chasing pin 5 tiles off (inside DANGER_R 6, beyond FIGHT_REACH) takes the stance's standing leg, an aim
    at it walking nowhere (logged `chaser_stance`); the falsifiers: the rule off, an idle pin, a chaser at 7 tiles
    (beyond DANGER_R) each take the approach walk as before."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(9, x, chasing=chasing)])
    f = walk_fight(r)
    if not rule:
        f.rules = f.rules - {"chaser_stance"}
    cmd = f.step()
    assert cmd.type == want
    if want == "aim":
        assert (cmd.args["vx"], cmd.args["vy"], cmd.args["targetId"]) == (0.0, 0.0, 9)
        assert f.why["chaser_stance"] is True and f.why["leg"] == "stand"
    else:
        assert "chaser_stance" not in f.why


def test_the_chaser_s_stand_holds_while_it_comes_and_gives_way_inside_keep_r(tmp_path):
    """The chaser's standing leg holds (`busy`) while the chaser stays beyond KEEP_R, and gives way inside it, where the
    next choose's leg is the stand again (the melee's dispatch point with `melee` announced)."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(9, 105.0)])
    f = walk_fight(r)
    a = f.step()
    r.answer("accepted")
    r.advance(0.5)
    r.frame(zombies=[zd(9, 103.0)])
    f.observe()
    assert f.busy() is True
    r.advance(0.5)
    r.frame(zombies=[zd(9, 102.3)])
    f.observe()
    assert f.busy() is False and a.type == "aim"


def test_a_failed_stance_or_a_riding_bandage_keeps_the_walk(tmp_path):
    """The rule's own bars: a stand-off fallback (the Lua's aim failed) or a riding bandage (P24-U: an aim ends it)."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(9, 105.0)])
    f = walk_fight(r)
    f.standoff = True
    assert f.step().type == "walkTo"
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    r2.frame(zombies=[zd(9, 105.0)])
    f2 = walk_fight(r2)
    f2.ride = object()
    assert f2.step().type == "walkTo"


# ---------------------------------------------------------------- the trials' replays
def run_dir(run):
    """The trial run's folder on this machine (`$PZT_RUNS`, else `testing/runs/` under this tree or any tree it sits
    in: a worktree lives inside the main checkout), else None."""
    p, roots = REPO, [os.environ.get("PZT_RUNS")]
    while True:
        roots.append(os.path.join(p, "testing", "runs"))
        if os.path.dirname(p) == p:
            break
        p = os.path.dirname(p)
    for root in roots:
        if root and os.path.isdir(os.path.join(root, run)):
            return os.path.join(root, run)
    return None


_REPLAYS = {}


def replay(run, **switches):
    """(the record's rows, the replayed rows) of trial `run` with `switches` set on the fresh Survive (the replay's
    mutate seam), cached; skipped where the run is absent."""
    key = (run, tuple(sorted(switches.items())))
    if key in _REPLAYS:
        return _REPLAYS[key]
    root = run_dir(run)
    logs = glob.glob(os.path.join(root, "clients", "admin", "Lua", "pzagent", "*", "state.log")) if root else []
    if not logs:
        pytest.skip("%s is not on this machine (testing/runs/ is per-machine)" % run)

    def mutate(sv):
        for name, v in switches.items():
            setattr(sv, name, v)
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(logs[0], os.path.join(d, "state.log"))
        shutil.copy(os.path.join(root, "decision.log"), os.path.join(d, "decision.log"))
        rep = R.replay(d, mutate=mutate)
    with open(os.path.join(root, "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(ln) for ln in f if ln.strip()]
    _REPLAYS[key] = (rows, rep)
    return rows, rep


def action(row):
    return (row.get("action") or {}).get("type")


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def test_trial_8_s_line_200_meets_10095_standing_and_never_walks_at_it():
    """Trial 8's line 200 (the record's unaimed walkTo at 10095 chasing 5.39 tiles off): the stance's standing leg at
    10095 (an aim walking nowhere, `chaser_stance`), held over lines 201 and 202, then the melee once it is within
    KEEP_R (line 203); no walkTo on lines 200 to 204. With CHASER_STANCE off the replay sends the record's walkTo."""
    rows, rep = replay(T8)
    assert action(rows[199]) == "walkTo"
    a = rep[199]["action"]
    assert (a["type"], a["args"]["targetId"], a["args"]["vx"], a["args"]["vy"]) == ("aim", 10095, 0.0, 0.0)
    assert threat(rep[199]).get("chaser_stance") is True
    assert [action(x) for x in rep[200:203]] == [None, None, "melee"]
    assert all(action(x) != "walkTo" for x in rep[199:204])
    _, off = replay(T8, CHASER_STANCE=False)
    assert action(off[199]) == "walkTo" and off[199]["action"]["args"] == rows[199]["action"]["args"]


def test_trial_12_s_four_walks_at_chasers_are_gone():
    """Trial 12's lines 433, 446, 452 and 492 (the record's walkTos at chasers 4.84 to 5.81 tiles off, each the
    approach walk, `leg` walk): with both of this task's street rules off the replay sends all four as recorded; with
    CHASER_STANCE on (SCRATCH_DRESS off, so the scratch's open-loop Dress, which never ends in a replay, holds no tick)
    none of the four lines walks."""
    lines = (433, 446, 452, 492)
    rows, off = replay(T12, CHASER_STANCE=False, SCRATCH_DRESS=False)
    for k in lines:
        assert action(rows[k - 1]) == "walkTo" and action(off[k - 1]) == "walkTo" and threat(off[k - 1])["leg"] == "walk"
    _, on = replay(T12, SCRATCH_DRESS=False)
    assert all(action(on[k - 1]) != "walkTo" for k in lines)


# ================================================================ (b) the scratch dressed
def frame(r, parts, moving=False, zombies=()):
    me = dict(DEFAULT_FRAME["me"], moving=moving)
    body = dict(DEFAULT_FRAME["body"], parts=list(parts), bleeding=sum(1 for p in parts if p.get("bleeding")))
    r.fake.frame(me=me, body=body, zombies=list(zombies))
    r.pump()


def scratch(i=9, **k):
    """A scratched part (`wound` true), not bleeding, unbandaged."""
    return part(i, wound=True, **k)


def zombie(zid, dx, chasing=True):
    return {"id": zid, "x": 100.0 + dx, "y": 200.0, "dist": abs(dx), "hasTarget": chasing, "crawler": False,
            "health": 1.0, "onFloor": False}


def scratch_rig(tmp_path, scratch_dress=True):
    """A Survive (DRESS_MANEUVER its default, on) on a PZA/1.7 hello, nothing held but the worn cotton T-shirt, part 9
    scratched."""
    r, sv = make(tmp_path)
    hello17(r)
    worn_shirt(r)
    r.frame()
    sv.SCRATCH_DRESS = scratch_dress
    frame(r, [scratch()])
    return r, sv


def care(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["care"]


def test_a_scratch_with_nothing_held_is_dressed_by_a_dress_that_tears_the_worn_shirt(tmp_path):
    """(b), trial 12's state (no dressing held, a worn cotton T-shirt, a scratch not bleeding): the care branch's Dress
    of part 9 (`wound`): the stop, the unwear once still, the rip, the bandage with the clean rag, and its end done once
    the part reads bandaged; the whole within a game minute of the fake's clock (every tick here is one frame)."""
    r, sv = scratch_rig(tmp_path)
    start = r.world.world_minutes()
    tick(r, sv)
    assert r.cmd() == ("stop", {}) and last(tmp_path)["branch"] == "care"
    assert care(tmp_path)["reason"] == "dress" and care(tmp_path)["dress"]["wound"] is True
    r.answer()
    frame(r, [scratch()])
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})
    r.answer({"state": "done", "result": {"itemId": 20, "loc": TSHIRT}})
    unworn_shirt(r)
    frame(r, [scratch()])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 20})
    r.answer({"state": "done", "result": {"rags": 1, "dirty": 0}})
    r.event("item_removed", itemId=20, fullType="Base.Tshirt_White")
    hold(r, 41, "Base.RippedSheets")
    frame(r, [scratch()])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 41, "part": 9})
    r.answer({"state": "done", "result": {"part": 9, "dirty": False, "life": 2.0}})
    frame(r, [scratch(bandaged=True, bandageLife=2.0, bandageDirty=False)])
    tick(r, sv)
    assert [e["end"] for e in care(tmp_path)["dress_end"]] == ["done"] and sv.care.dress is None
    assert r.world.world_minutes() - start <= 1.0
    all_sends_valid(r)


def test_with_scratch_dress_off_p28_a_holds_the_scratch_for_the_reserve(tmp_path):
    """The falsifier, trial 12's care line: with SCRATCH_DRESS off, P28-A's step holds the scratch (no clean dressing
    past WOUND_RESERVE), `wound_held` {part 9, clean 0}, and nothing is sent."""
    r, sv = scratch_rig(tmp_path, scratch_dress=False)
    tick(r, sv)
    assert care(tmp_path)["wound_held"] == {"part": 9, "clean": 0}
    assert not any(a.type in ("stop", "unwear", "rip", "bandage") for a in r.acts.history)


def test_a_standing_zombie_within_keep_r_holds_the_scratch_s_dress(tmp_path):
    """No Dress starts with a standing zombie within KEEP_R (the Dress's own end): the care line logs `wound_held`
    {part, standing}; once it is gone the Dress starts."""
    c_r = Rig(tmp_path)
    hello17(c_r)
    worn_shirt(c_r)
    frame(c_r, [scratch()], zombies=[zombie(7, 2.0)])
    c = C.Care(c_r.world, c_r.acts, c_r.clock)
    c.dress_cls, c.scratch_dress = Dress, True
    assert c.scratch_wanted() is False and c.choose() is None
    assert c.why["wound_held"] == {"part": 9, "standing": 1}
    frame(c_r, [scratch()], zombies=[zombie(7, 2.6)])
    cmd = c.choose()
    assert cmd.TYPE == "stop" and c.dress.wound is True and c.dress.part == 9


def test_a_bleed_takes_the_place_of_a_running_scratch_dress(tmp_path):
    """A part that starts bleeding while a scratch's Dress runs: the scratch's Dress is dropped (`dress_end` {end
    "bleed"}) and a bleed's Dress of the bleeding part starts."""
    r = Rig(tmp_path)
    hello17(r)
    hold(r, 10, "Base.Bandage")
    frame(r, [scratch()])
    c = C.Care(r.world, r.acts, r.clock)
    c.dress_cls, c.scratch_dress = Dress, True
    assert c.choose().TYPE == "stop" and c.dress.wound is True
    frame(r, [scratch(), part(3, bleeding=True, bleedingTime=5.0)])
    c.observe()
    c.choose()
    assert c.dress.part == 3 and c.dress.wound is False
    assert [e["end"] for e in c.why["dress_end"]] == ["bleed"]


def test_the_scratch_takes_a_clean_dressing_before_tearing_and_a_dirty_rag_last(tmp_path):
    """The scratch Dress's pick: a clean rag held goes on at once (no tear); with only a dirty rag and nothing to tear
    the dirty rag (the last resort, #4299 against #2364); a bleed's pick is unchanged."""
    r = Rig(tmp_path)
    hello17(r)
    hold(r, 11, "Base.RippedSheets")
    worn_shirt(r)
    frame(r, [scratch()])
    d = Dress(r.world, r.acts, r.clock, part=9, wound=True)
    assert d._choice() == ("bandage", 11, "rag")
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    hello17(r2)
    hold(r2, 13, "Base.RippedSheetsDirty")
    worn_shirt(r2)
    frame(r2, [scratch()])
    assert Dress(r2.world, r2.acts, r2.clock, part=9, wound=True)._choice()[0] == "unwear"
    (tmp_path / "c").mkdir()
    r3 = Rig(tmp_path / "c")
    hello17(r3)
    hold(r3, 13, "Base.RippedSheetsDirty")
    frame(r3, [scratch()])
    assert Dress(r3.world, r3.acts, r3.clock, part=9, wound=True)._choice() == ("bandage", 13, "dirty")


def test_the_scratch_s_dress_is_done_on_bandaged_not_on_bleeding_false(tmp_path):
    """A wound Dress ends done once the part reads bandaged (a scratch reads bleeding false from the start); a bleed's
    Dress on the same frame would end done at once."""
    r = Rig(tmp_path)
    hello17(r)
    worn_shirt(r)
    frame(r, [scratch()])
    d = Dress(r.world, r.acts, r.clock, part=9, wound=True)
    d.observe()
    assert d.over() is None
    frame(r, [scratch(bandaged=True, bandageLife=2.0, bandageDirty=False)])
    d.observe()
    assert d.over() == "done"
    b = Dress(r.world, r.acts, r.clock, part=9)
    frame(r, [scratch()])
    b.observe()
    assert b.over() == "done"


@pytest.mark.parametrize("dx, chasing, closing, yields", [(8.0, True, True, True), (3.0, True, True, False),
                                                          (3.0, False, False, True), (2.0, True, False, False)])
def test_the_threat_branch_yields_to_the_scratch_s_dress(monkeypatch, tmp_path, dx, chasing, closing, yields):
    """The yield (`_wound_yields`): a chaser 8 tiles off (trial 12's lines 316 to 328), closing: the care's Dress
    takes the tick (`care_yield` {why "scratch"}); one at 3 tiles closing: no yield (beyond KEEP_R, inside CARE_R);
    an idle one at 3 tiles, still: the yield; one at 2 tiles (inside KEEP_R): none.
    Named change, Plan 32 Task 5 (the coward rules on by default): pinned with `CARE_COMMIT` off, the rule before it
    ((c), a care action wanted taking one walk away, then finished with the threat branch yielding)."""
    monkeypatch.setattr("agent.base.planner.threat.Threat.CARE_COMMIT", False)
    r, sv = scratch_rig(tmp_path)
    off = dx + (0.6 if closing else 0.0)
    for k in range(4):
        if closing:
            off -= 0.2
        r.advance(0.5)
        r.frame(zombies=[zombie(7, off, chasing=chasing)], wounds={"parts": [scratch()], "bleeding": 0})
        tick(r, sv)
    th = threat_why(tmp_path)
    assert th.get("held") == 1 or not yields
    if yields:
        assert last(tmp_path)["branch"] == "care" and th.get("care_yield") == {"why": "scratch", "near": th["nearest"]}
        assert any(a.type == "stop" for a in r.acts.history)
    else:
        assert th.get("care_yield") is None and not any(a.type == "stop" for a in r.acts.history)


def test_trial_12_s_scratch_takes_the_care_s_dress_within_a_game_minute_of_the_first_quiet_line():
    """Trial 12 replayed: the record has no care line from the scratch (line 305) to the cap; the replay's first care
    line after it is the scratch Dress's stop of part 9 (`wound`), on line 314, 0.43 game minutes after line 311, the
    first line after the scratch whose nearest zombie read beyond KEEP_R (the lines between read a `many` group). With
    SCRATCH_DRESS off no care line sends anything after the scratch (P28-A's `wound_held` {clean 0}).
    Named change, Plan 32 Task 5 (the coward rules on by default): pinned with `CARE_COMMIT` off, the rule before it
    ((c), a care action wanted taking one walk away, then finished with the threat branch yielding), passed to the
    replay's own switches (its cache is keyed by them)."""
    rows, rep = replay(T12, CARE_COMMIT=False)
    assert not any(r["branch"] == "care" for r in rows[304:])
    quiet = next(k for k in range(305, len(rows) + 1)
                 if rows[k - 1]["inputs"].get("nearest") is None or rows[k - 1]["inputs"]["nearest"] > P.KEEP_R)
    first = next(k for k in range(305, len(rep) + 1) if rep[k - 1]["branch"] == "care" and rep[k - 1]["action"])
    c = rep[first - 1]["inputs"]["branches"]["care"]
    assert (quiet, first, rep[first - 1]["action"]["type"]) == (311, 314, "stop")
    assert c["dress"]["wound"] is True and c["dress"]["part"] == 9
    assert (rep[first - 1]["inputs"]["hour"] - rows[quiet - 1]["inputs"]["hour"]) * 60 <= 1.0
    _, off = replay(T12, SCRATCH_DRESS=False, CARE_COMMIT=False)
    assert not any(r["branch"] == "care" and r["action"] for r in off[304:])


def test_a_running_scratch_dress_gives_way_to_a_chaser_closing_within_care_hold_r(monkeypatch, tmp_path):
    """Fix 1, review-t15a M2: a scratch's Dress started under a chaser 8 tiles off (its stop sent and done) holds the
    threat branch's yield while the chaser closes beyond CARE_HOLD_R (3.0), as a running bleed bandage does, and gives
    way once it closes within it (2.8): the threat branch takes that tick, no `care_yield`; the old hold reached KEEP_R
    (2.5), the Dress's own end.
    Named change, Plan 32 Task 5 (the coward rules on by default): pinned with `CARE_COMMIT` off, the rule before it
    ((c), a care action wanted taking one walk away, then finished with the threat branch yielding)."""
    monkeypatch.setattr("agent.base.planner.threat.Threat.CARE_COMMIT", False)
    r, sv = scratch_rig(tmp_path)
    off = 8.6
    for k in range(4):
        off -= 0.2
        r.advance(0.5)
        r.frame(zombies=[zombie(7, off)], wounds={"parts": [scratch()], "bleeding": 0})
        tick(r, sv)
    assert r.cmd() == ("stop", {}) and sv.care.dress is not None and sv.care.dress.wound
    r.answer()
    seen = []
    for off in (6.0, 4.5, 3.4, 3.1, 2.8):
        r.advance(0.5)
        r.frame(zombies=[zombie(7, off)], wounds={"parts": [scratch()], "bleeding": 0})
        tick(r, sv)
        th = threat_why(tmp_path)
        seen.append((off, last(tmp_path)["branch"], (th.get("care_yield") or {}).get("why")))
    assert seen[:4] == [(6.0, "care", "scratch"), (4.5, "care", "scratch"), (3.4, "care", "scratch"),
                        (3.1, "care", "scratch")], seen
    assert seen[4] == (2.8, "threat", None), seen


def test_a_zombie_read_dead_but_listed_standing_holds_neither_the_scratch_s_start_nor_its_yield(tmp_path):
    """Fix 1, review-t15a M5: one standing read (`Care.scratch_room`, the ids read dead left out through the Care's
    `skip`, which Survive sets each tick, and the Dress's own KEEP_R end through its `skip`) for the scratch's start,
    the threat branch's yield and the Dress's end: a zombie listed standing at 2.0 tiles but read dead (Survive's
    `dead`) holds none of them; the Dress's stop goes."""
    r, sv = scratch_rig(tmp_path)
    sv.dead[7] = r.clock() + 60.0
    for _ in range(4):
        r.advance(0.5)
        r.frame(zombies=[zombie(7, 2.0, chasing=False)], wounds={"parts": [scratch()], "bleeding": 0})
        tick(r, sv)
    assert sv.care.skip == {7} and sv.care.scratch_room() is True
    assert any(a.type == "stop" for a in r.acts.history) and sv.care.dress is not None and sv.care.dress.wound


def test_the_yield_to_the_scratch_leaves_a_zombie_read_dead_out(monkeypatch, tmp_path):
    """Fix 1, review-t15a M5, the yield's half: a live chaser 8 tiles off and closing (the threat branch's tick, the
    yield's case) and a zombie listed standing at 2.0 tiles but read dead: the yield to the scratch's Dress goes
    (`care_yield` {why "scratch"}), the dead one held out of the yield's standing read as out of the start's.
    Named change, Plan 32 Task 5 (the coward rules on by default): pinned with `CARE_COMMIT` off, the rule before it
    ((c), a care action wanted taking one walk away, then finished with the threat branch yielding)."""
    monkeypatch.setattr("agent.base.planner.threat.Threat.CARE_COMMIT", False)
    r, sv = scratch_rig(tmp_path)
    sv.dead[7] = r.clock() + 60.0
    off = 8.6
    for _ in range(4):
        off -= 0.2
        r.advance(0.5)
        r.frame(zombies=[zombie(7, 2.0, chasing=False), zombie(8, off)], wounds={"parts": [scratch()], "bleeding": 0})
        tick(r, sv)
    th = threat_why(tmp_path)
    assert last(tmp_path)["branch"] == "care" and th.get("care_yield") == {"why": "scratch", "near": th["nearest"]}
    assert any(a.type == "stop" for a in r.acts.history)
