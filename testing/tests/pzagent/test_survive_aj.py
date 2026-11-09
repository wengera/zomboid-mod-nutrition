"""Plan 33 Task 2 (the crawler first; the spec `docs/superpowers/specs/2026-11-09-plan-33-the-group-design.md` § 3.2):
`survive.T17_SWITCHES`' CRAWLER_FIRST, the Fight's `crawler_first` rule (`fight.Fight._crawler_first`), on by default.
A zombie reading `crawler` true or `onFloor` true within CRAWLER_R (1.0 tile) while a standing zombie stands within
DANGER_R is the pin of a finish (a `stomp`, the melee in mode `finish` where the build announces it) before the
standing one is met, unless the standing one is within STAND_MIN_R; the pin returns to the nearest standing zombie when
the crawler reads dead, beyond CRAWLER_R, or after CRAWLER_TRIES finishes at it ended without a kill.

The live session F18 (`f_goals_18-20261108-235005`, its GUIDE § 3): the crawler 13649 lay within 0.4 tiles of the
character from game minute 608 to the death at 617 and was the target of no decision line after 356, the pair rule
(`pair_nearest`) pinning the nearest standing zombie and the finish silent with one standing within KEEP_R; its bites
(`CrawlerBiteLEFT` 2, `CrawlerBiteRIGHT` 1 of the four reaction runs) came from under the character's feet. Its replay
is `replay_decisions.replay`, open loop, through this file's own frame pairing (`align_f18`): `replay_decisions.align`
refuses F18 at line 131, whose hour two frames read (seq 1558 and 1559, the clock standing), and the GUIDE's pairing
(How to read it) takes the later, the latest frame reading the line's hour at or before its wall; every other line is
`align`'s.
"""
import functools
import json
import math
import os

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.world import World

from .test_policies import Rig, zombie

F18 = os.path.join(R.ARTIFACTS, "f_goals_18-20261108-235005")
CRAWLER = 13649


# ================================================================ the constants and the switch
def test_the_crawler_constants_and_the_switch():
    """CRAWLER_R 1.0 tile, CRAWLER_TRIES 2, the rule among the Fight's rules, CRAWLER_FIRST on by default in
    `survive.T17_SWITCHES`."""
    assert P.CRAWLER_R == 1.0 and F.CRAWLER_TRIES == 2
    assert "crawler_first" in F.FIGHT_RULES
    assert S.T17_SWITCHES == ("CRAWLER_FIRST",) and S.Survive.CRAWLER_FIRST is True


def test_the_switch_reaches_the_fight_rules(tmp_path):
    """Survive's `_fight_rules` carries `crawler_first` while CRAWLER_FIRST is on, and not with it off."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    assert "crawler_first" in sv._fight_rules()
    sv.CRAWLER_FIRST = False
    assert "crawler_first" not in sv._fight_rules()


# ================================================================ the rule on the fake mod
def at(zid, x, floor=False, crawler=False, chasing=True):
    return dict(zombie(zid, x, 200.0), onFloor=floor, crawler=crawler, hasTarget=chasing)


def crawl(zid, x):
    return at(zid, x, floor=True, crawler=True)


def fight_rig(tmp_path, zs, rule=True):
    """A Fight on a fresh Rig over one frame of `zs`, its rules the defaults with `crawler_first` on or off."""
    r = Rig(tmp_path)
    r.frame(zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.rules = (f.rules | {"crawler_first"}) if rule else (f.rules - {"crawler_first"})
    return r, f


def test_a_crawler_within_crawler_r_is_stomped_before_the_standing_one(tmp_path):
    """F18's line 357 on the fake mod: the crawler at 0.4 tiles, a standing zombie at 1.2 (within DANGER_R, beyond
    STAND_MIN_R): the stomp goes at the crawler, the pin on it, the why `crawler_first` {target, dist, standing,
    standing_dist, tries}; off, the pair rule's standing pin as before."""
    zs = [crawl(1, 100.4), at(2, 101.2)]
    r, f = fight_rig(tmp_path, zs)
    f.target = 2   # the threat branch's point-blank pin on the standing one
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("stomp", 1) and f.target == 1
    cf = f.why["crawler_first"]
    assert cf["target"] == 1 and cf["dist"] == pytest.approx(0.4) and cf["standing"] == 2
    assert cf["standing_dist"] == pytest.approx(1.2) and cf["tries"] == 0
    assert "pair_nearest" not in f.why
    (tmp_path / "off").mkdir()
    r2, f2 = fight_rig(tmp_path / "off", zs, rule=False)
    f2.target = 2
    cmd2 = f2.choose()
    assert getattr(cmd2, "targetId", 2) == 2 and "crawler_first" not in f2.why and f2.target == 2


def test_a_knocked_down_zombie_reading_on_floor_is_taken_too(tmp_path):
    """`onFloor` true without `crawler` (a knock-down) within CRAWLER_R reads as the crawler does."""
    r, f = fight_rig(tmp_path, [at(1, 100.5, floor=True), at(2, 104.0)])
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("stomp", 1) and f.why["crawler_first"]["target"] == 1


def test_a_crawler_reading_crawler_while_on_floor_reads_false_is_taken(tmp_path):
    """`crawler` true alone (the frame's `onFloor` false) reads as a crawler, never as the standing one."""
    r, f = fight_rig(tmp_path, [at(1, 100.5, crawler=True), at(2, 102.0)])
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("stomp", 1) and f.why["crawler_first"]["standing"] == 2


def test_the_standing_one_within_stand_min_r_keeps_the_meet(tmp_path):
    """The exception: a standing zombie within STAND_MIN_R (the engine's call would take it, #4372): the rule is
    silent, the standing one the Fight's as before."""
    r, f = fight_rig(tmp_path, [crawl(1, 100.4), at(2, 100.5)])
    cmd = f.choose()
    assert "crawler_first" not in f.why and getattr(cmd, "targetId", None) != 1


def test_with_no_standing_zombie_within_danger_r_the_finish_stands_as_before(tmp_path):
    """No standing zombie within DANGER_R: the rule is silent and the finish (P24-AL; P27-G's floor swing with the bat
    held) takes the crawler as today, the same command as with the rule off."""
    zs = [crawl(1, 100.4), at(2, 107.0)]
    r, f = fight_rig(tmp_path, zs)
    cmd = f.choose()
    assert "crawler_first" not in f.why and cmd.targetId == 1 and f.why["downed"] == 1
    (tmp_path / "off").mkdir()
    r2, f2 = fight_rig(tmp_path / "off", zs, rule=False)
    cmd2 = f2.choose()
    assert (cmd2.TYPE, cmd2.targetId) == (cmd.TYPE, cmd.targetId) and f2.why == f.why


def test_a_crawler_beyond_crawler_r_is_not_taken(tmp_path):
    """The crawler at 1.3 tiles (beyond CRAWLER_R): the rule is silent."""
    r, f = fight_rig(tmp_path, [crawl(1, 101.3), at(2, 102.0)])
    f.choose()
    assert "crawler_first" not in f.why


def test_the_nearest_crawler_is_taken_and_kept_while_it_holds(tmp_path):
    """Two within CRAWLER_R: the nearer first; once pinned it is kept while it holds, a nearer one notwithstanding."""
    r, f = fight_rig(tmp_path, [crawl(1, 100.8), crawl(3, 100.5), at(2, 102.0)])
    assert f.choose().targetId == 3
    r.frame(zombies=[crawl(1, 100.3), crawl(3, 100.5), at(2, 102.0)])
    f.observe()
    assert f.choose().targetId == 3 and f.target == 3


def test_the_pin_returns_to_the_standing_one_when_the_crawler_reads_dead(tmp_path):
    """The stomp's pin on the crawler, then the crawler read dead (`dead`, as the Fight's kill read records it): the
    pin returns to the standing zombie, logged `crawler_first` {returned, crawler, why "dead"}."""
    r, f = fight_rig(tmp_path, [crawl(1, 100.4), at(2, 101.5)])
    f.choose()
    assert f.target == 1
    f.dead[1] = r.clock() + P.UNREACHABLE_S
    f.observe()
    cmd = f.choose()
    assert f.target == 2 and getattr(cmd, "targetId", 2) == 2
    assert f.why["crawler_first"] == {"returned": 2, "crawler": 1, "why": "dead"}


def test_the_pin_returns_to_the_standing_one_when_the_crawler_is_beyond_crawler_r(tmp_path):
    r, f = fight_rig(tmp_path, [crawl(1, 100.4), at(2, 101.5)])
    f.choose()
    r.frame(zombies=[crawl(1, 98.7), at(2, 101.5)])
    f.observe()
    f.choose()
    assert f.target == 2 and f.why["crawler_first"] == {"returned": 2, "crawler": 1, "why": "beyond"}


def test_after_crawler_tries_finishes_without_a_kill_the_crawler_is_left(tmp_path):
    """CRAWLER_TRIES (2) stomps at the crawler ended `done` without a kill: the third choose leaves it, the pin back on
    the standing one (`why` "tries"); one ended stomp leaves the rule on (tries 1)."""
    zs = [crawl(1, 100.4), at(2, 101.5)]
    r, f = fight_rig(tmp_path, zs)
    done = {"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}}
    a = f.step()
    assert a.type == "stomp" and a.args["targetId"] == 1
    r.answer(done)
    r.frame(zombies=zs)
    a = f.step()
    assert a.type == "stomp" and a.args["targetId"] == 1 and f.why["crawler_first"]["tries"] == 1
    r.answer(done)
    r.frame(zombies=zs)
    a = f.step()
    assert f.crawler_tries == {1: 2} and f.target == 2
    assert f.why["crawler_first"] == {"returned": 2, "crawler": 1, "why": "tries"}
    assert a is None or a.args.get("targetId") == 2


def test_a_killing_stomp_counts_no_try(tmp_path):
    """A stomp that kills (`targetDead`) is no try: the crawler is dead, the pin returns (`why` "dead")."""
    zs = [crawl(1, 100.4), at(2, 101.5)]
    r, f = fight_rig(tmp_path, zs)
    f.step()
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": True}})
    r.frame(zombies=zs)
    f.step()
    assert f.crawler_tries == {} and f.target == 2 and f.why["crawler_first"]["why"] == "dead"


def test_a_running_stomp_at_the_crawler_holds_and_another_send_gives_way(tmp_path):
    """`busy`: the stomp at the crawler holds while it runs; an attack at the standing one gives way to the crawler."""
    zs = [crawl(1, 100.4), at(2, 101.5)]
    r, f = fight_rig(tmp_path, zs)
    f.step()
    r.fake.answer({"stomp": ["accepted"]})
    r.pump()
    assert f.busy()
    (tmp_path / "b").mkdir()
    r2, f2 = fight_rig(tmp_path / "b", zs, rule=False)
    f2.target = 2
    f2.send(F.Attack(2))
    r2.fake.answer({"attack": ["accepted"]})
    r2.pump()
    assert f2.busy()
    f2.rules = f2.rules | {"crawler_first"}
    assert not f2.busy()


def test_the_tries_are_shared_across_the_fights_of_one_survive(tmp_path):
    """Survive's `crawler_tries` is set on every Fight it observes, so a new Fight keeps the count."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    r.frame(zombies=[crawl(1, 100.4), at(2, 101.5)])
    f = F.Fight(r.world, r.acts, r.clock)
    sv.crawler_tries[1] = 2
    sv._observe(f)
    assert f.crawler_tries is sv.crawler_tries


def test_a_door_fight_or_a_doorway_stand_takes_no_crawler_first(tmp_path):
    r, f = fight_rig(tmp_path, [crawl(1, 100.4), at(2, 101.5)])
    f.only = {2}
    f.choose()
    assert "crawler_first" not in f.why


# ================================================================ F18 replayed
def align_f18(lines, rows):
    """`replay_decisions.align` with the GUIDE's pairing where two frames read a line's hour (F18's line 131): the
    latest such frame at or before the line's wall."""
    by_hour = {}
    for i, ln in enumerate(lines):
        if ln["kind"] == "frame":
            by_hour.setdefault(ln["me"].get("hour"), []).append(i)
    ends, last = [], 0
    for k, row in enumerate(rows, 1):
        hits = [i for i in by_hour.get(row["inputs"]["hour"], []) if i >= last]
        if len(hits) > 1:
            hits = [max(i for i in hits if lines[i]["wallMs"] / 1000.0 <= row["wall"])]
        if len(hits) != 1:
            raise ValueError("decision line %d: %d frames read hour %r" % (k, len(hits), row["inputs"]["hour"]))
        end = hits[0] + 1
        while end < len(lines) and lines[end]["kind"] != "frame" and lines[end]["wallMs"] / 1000.0 <= row["wall"]:
            end += 1
        ends.append((hits[0] + 1, end))
        last = hits[0]
    return ends


def _need_f18():
    if not os.path.isfile(os.path.join(F18, "decision.log")):
        pytest.skip("%s is not checked out" % F18)


@functools.lru_cache(maxsize=4)
def _f18(on):
    """F18 replayed (every line) with CRAWLER_FIRST `on`, as JSON. Pinned with Plan 33 Task 3's group rules off
    (`survive.T18_SWITCHES`: GROUP_LEAVE, DRAG_GUARD_FIGHT, SIDE_CLEAR), a named change that moves F18's lines from 342
    (the controller's pin at the merge of Tasks 2 and 3; CLAUDE.md section 6)."""
    _need_f18()
    orig = R.align
    R.align = align_f18
    try:
        def mutate(sv):
            sv.CRAWLER_FIRST = on
            for k in S.T18_SWITCHES:
                setattr(sv, k, False)
        return json.dumps(R.replay(F18, mutate=mutate))
    finally:
        R.align = orig


def f18(on):
    return json.loads(_f18(on))


@functools.lru_cache(maxsize=1)
def record():
    _need_f18()
    with open(os.path.join(F18, "decision.log"), encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


@functools.lru_cache(maxsize=1)
def _near():
    """{line: (crawler's tiles or None, nearest standing zombie's (tiles, id) or None)} off each line's frame, from line
    356 on (the frame pairing `align_f18`'s)."""
    _need_f18()
    lines, rows = R.read_record(F18)
    w, i, out = World(), 0, {}
    for k, (row, (fe, _)) in enumerate(zip(rows, align_f18(lines, rows)), 1):
        for ln in lines[i:fe]:
            w.apply(ln)
        i = fe
        if k < 356:
            continue
        mx, my = w.me["x"], w.me["y"]
        cd, stand = None, None
        for zid, z in w.zombies.items():
            if z.get("x") is None:
                continue
            d = math.hypot(z["x"] - mx, z["y"] - my)
            if zid == CRAWLER:
                cd = d
            elif z.get("onFloor") is not True and z.get("crawler") is not True and (stand is None or d < stand[0]):
                stand = (d, zid)
        out[k] = (cd, stand)
    return out


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def at_crawler(row):
    a = row.get("action") or {}
    return (a.get("args") or {}).get("targetId") == CRAWLER and a.get("type") in ("stomp", "melee")


def test_f18_with_crawler_first_off_replays_as_recorded_from_line_356():
    """The replay's own baseline: with CRAWLER_FIRST off, every line from 356 to the death (415) sends what the record
    sent, and none after 356 sends at the crawler."""
    off, rec = f18(False), record()
    assert len(off) == len(rec) == 415
    assert [off[k - 1]["action"] for k in range(356, 416)] == [rec[k - 1]["action"] for k in range(356, 416)]
    assert not any(at_crawler(rec[k - 1]) for k in range(357, 416))


def holds_crawler(row):
    """The line holds a running finish at the crawler (the Fight's `busy`, its maneuver's target 13649)."""
    th = threat(row)
    return bool(th.get("holding")) and (th.get("maneuver") or {}).get("target") == CRAWLER


def test_f18_s_crawler_is_the_target_of_a_finish_from_its_first_line_in_reach():
    """With CRAWLER_FIRST on: the first line from 356 whose frame lists 13649 within CRAWLER_R and a standing zombie
    within DANGER_R beyond STAND_MIN_R is 356 itself (13649 at 0.23 tiles, 13648 standing at 4.04, the record holding
    the finish a75 at 13649); it logs `crawler_first` at 13649 and holds that finish, and so does line 357, where the
    record superseded it with a melee at 13651 (standing at 1.13, `pair_nearest`, the last line naming 13649 in the
    record); line 358 sends the finish at 13649 again (the open-loop replay reads a75 ended by the record's a76)."""
    on, near, rec = f18(True), _near(), record()
    first = next(k for k in sorted(near) if near[k][0] is not None and near[k][0] <= P.CRAWLER_R
                 and near[k][1] is not None and P.STAND_MIN_R < near[k][1][0] <= P.DANGER_R)
    assert first == 356
    for k in (356, 357):
        why = threat(on[k - 1]).get("crawler_first")
        assert why["target"] == CRAWLER and why["dist"] <= P.CRAWLER_R and holds_crawler(on[k - 1]), k
    assert why["standing"] == 13651 and why["standing_dist"] == pytest.approx(1.1291330499090764)
    assert rec[356]["action"]["type"] == "melee" and rec[356]["action"]["args"]["targetId"] == 13651
    assert on[356]["action"] is None and at_crawler(on[357])


def test_f18_s_finishes_at_the_crawler_and_the_returns_from_line_357():
    """From line 357 to the death the record sent nothing at 13649; with CRAWLER_FIRST on, four finishes go at it
    (lines 358, 384, 386 and 395), and the pin returns to the standing one on the lines a standing zombie read within
    STAND_MIN_R (366, 370, 374, 398: `why` "standing") or the crawler beyond CRAWLER_R (385: `why` "beyond"). The
    drag-down guard's lines (402 to 415) keep their own row (the flee runs ahead of the Fight)."""
    on, rec = f18(True), record()
    assert [k for k in range(357, 416) if at_crawler(rec[k - 1])] == []
    assert [k for k in range(357, 416) if at_crawler(on[k - 1])] == [358, 384, 386, 395]
    returns = {k: threat(on[k - 1])["crawler_first"]["why"] for k in range(357, 416)
               if "returned" in (threat(on[k - 1]).get("crawler_first") or {})}
    assert returns == {366: "standing", 370: "standing", 374: "standing", 385: "beyond", 398: "standing"}
    assert all(threat(on[k - 1]).get("flee") == "many" for k in range(402, 416))


# ================================================================ the six goldens
GOLDENS = ("e2", "e3", "e4", "e5", "f1", "f1-caps15")


@pytest.mark.slow
@pytest.mark.parametrize("key", GOLDENS)
def test_crawler_first_moves_no_golden(key):
    """The six decision goldens with CRAWLER_FIRST off are the files byte for byte, and so (the default, on) are
    they: no golden's ring reaches the rule, so none was re-recorded (Plan 33 Task 2)."""
    with open(R.golden_path(key), encoding="utf-8", newline="") as f:
        text = f.read()
    head = json.loads(text)
    caps = R.HELLO_CAPS.get(key)

    def mutate(sv):
        sv.CRAWLER_FIRST = False
    off = R.golden_text(R.decisions(R.replay(os.path.join(R.ARTIFACTS, R.RUNS[key]), caps=caps, mutate=mutate)),
                        head["base"], R.RUNS[key], head["recorded"], R.SPANS.get(key), caps)
    on = R.golden_text(R.decisions(R.replay(os.path.join(R.ARTIFACTS, R.RUNS[key]), caps=caps)),
                       head["base"], R.RUNS[key], head["recorded"], R.SPANS.get(key), caps)
    assert off == on == text
