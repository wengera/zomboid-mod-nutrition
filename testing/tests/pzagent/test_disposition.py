"""Plan 37 Task 3 (the disposition; the spec `docs/superpowers/specs/2026-11-12-plan-37-the-disposition-design.md`
§§ 3.1, 3.2, 3.4 and 3.5): the selector (`planner/disposition.py`'s `Disposer`) picks `hunt`, `hold`, `string` or
`break` on events with a dwell and a hysteresis, hands it to the engaged melee by a re-send (`disposition`, the
withdraw, `release`), and hands the contact over to the Flee only through the reflex's hand-back.

Every fixture is synthetic (test_survive_as.py's style: the fake mod announcing PZA/1.13 with the `melee` cap, a line
every half second), never a replay; F22's replay is `test_survive_av.py`'s."""
import math

import pytest

from agent.base.planner import disposition as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers.melee import WorkInputs
from agent.base.pza1 import MELEE_DISPOSITIONS

from .test_base_world import _grid
from .test_survive import threat_why, tick
from .test_survive_an import accept
from .test_survive_ar import rig
from .test_survive_as import ME, line, zp
from .test_survive_q import z


def survive(tmp_path, first):
    """test_survive_as's `survive` (its first line the melee at `first`, accepted, `face`) with DISPOSITION on (that
    file pins Plan 36's picker with it off): the line is read again under the selector."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    r.frame(zombies=[first])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee" and sv.mode == "fight" and sv.DISPOSITION is True
    accept(r, a, "face")
    return r, sv, a


def melee_of(r):
    """The last melee the planner sent (the engaged one)."""
    return next(a for a in reversed(r.acts.history) if a.type == "melee")


def lines(tmp_path, r, sv, frames, **frame):
    """Each of `frames` (zombie lists) one decision line half a second on: [(why, last action)]."""
    return [line(tmp_path, r, sv, zs, **frame) for zs in frames]


def ring_of(deg, d, n, bearings):
    """`n` standing zombies `d` tiles off ME at `bearings` (degrees), ids from `deg`."""
    return [zp(deg + i, b, d) for i, b in enumerate(bearings[:n])]


FAN = (0.0, 30.0, -30.0, 60.0, -60.0, 15.0, -15.0, 45.0)   # bearings east of ME: a group to the east


def group(n, d):
    """`n` of the fan at `d` tiles, the rest of the eight at 12 tiles (still listed: the World keeps a zombie its
    frames drop ZOMBIE_TTL_S)."""
    return [zp(10 + i, b, d if i < n else 12.0) for i, b in enumerate(FAN)]


# ================================================================ the constants and the switch
def test_the_constants_and_the_switch():
    """The spec's §§ 3.2 and 3.5 values, the switch on by default in T22_SWITCHES, the deleted names gone (GROUP_LEAVE
    kept as `Threat`'s seam onto the rules before Plan 33, out of T18_SWITCHES)."""
    assert (P.DISPOSITION_DWELL_S, P.STRING_N, P.STRING_PIN_S, P.BREAK_CORNERED_S, P.STRING_RUN_V) == (
        2.0, 5, 3.0, 2.0, 1.6)
    assert (P.STRING_TURN_DEG, P.STRING_STEP_DEG, P.STRING_LOOK_R, P.RELEASE_WAIT_S, P.SPRINT_READS) == (
        120.0, 15.0, 10.0, 2.5, 3)
    assert S.T22_SWITCHES == ("DISPOSITION",) and "T22_SWITCHES" in S.__all__ and T.Threat.DISPOSITION is True
    assert not hasattr(P, "RETREAT_MAX_N") and not hasattr(T.Threat, "_group_lapse")
    assert not any(hasattr(T.Threat, n) for n in ("SPENT_LEAVE", "RUN_HOLD"))
    assert S.T18_SWITCHES == () and T.Threat.GROUP_LEAVE is True   # the leave's seam, out of the tuples
    assert D.WIRE == tuple(MELEE_DISPOSITIONS)


@pytest.mark.parametrize("disposition", [None, "hunt", "hold", "string"])
def test_the_work_inputs_carry_the_crawler_buffer_and_the_pile_under_every_disposition(disposition):
    """`WorkInputs` under every disposition sends crawlerR and pile (the two primitives no table turns off) beside the
    disposition and the release; the disposition and the release are part of the behaviour a re-send follows."""
    w = WorkInputs(3.5, 1.2, 0.4, None, 40.0, True, disposition=disposition)
    a = w.args()
    assert a["crawlerR"] == 1.2 and a["pile"] is True and a["disposition"] == disposition and a["release"] is False
    assert w.behaviour() != WorkInputs(3.5, 1.2, 0.4, None, 40.0, True, disposition=disposition,
                                       release=True).behaviour()
    if disposition is not None:
        assert w.behaviour() != WorkInputs(3.5, 1.2, 0.4, None, 40.0, True).behaviour()


# ================================================================ hunt
def test_two_standing_are_hunted_with_no_withdraw(tmp_path):
    """One standing at 1.8 tiles, then a second at 3 tiles (not closing: no spread pull, fix 1): the first line enters
    `hunt` (logged `disposition` {from null, to hunt, why count, dwell null}) and the melee carries `disposition` hunt
    and no withdraw; the second line no change, no re-send."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 1.8))
    assert a.args["disposition"] == "hunt" and "withdrawX" not in a.args
    assert sv.disposition == "hunt"
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 1.8), zp(2, 90.0, 3.0)])
    assert b is a and sv.disposition == "hunt" and "disposition" not in why and why.get("fight") is True


def test_the_first_line_logs_the_entry(tmp_path):
    r, sv, a = survive(tmp_path, zp(1, 0.0, 1.8))
    from .test_survive import decisions
    first = decisions(tmp_path)[0]["inputs"]["branches"]["threat"]
    assert first["disposition"] == {"from": None, "to": "hunt", "why": "count", "dwell": None}


# ================================================================ hold
def closing_three(k):
    """Line k's three standing closing: 1 east, 2 and 3 at bearings -70 and +70, each a quarter tile nearer a line."""
    return [zp(1, 0.0, 2.4 - 0.1 * k), zp(2, -70.0, 5.5 - 0.25 * k), zp(3, 70.0, 5.5 - 0.25 * k)]


def test_hold_is_entered_at_three_closing_after_the_dwell(tmp_path):
    """Three standing closing within GROUP_ENTRY_R: hunt holds under DISPOSITION_DWELL_S (the lines at 0.5 to 1.5 s),
    then `hold` (logged once, why entry, dwell 2.0) and the melee re-sent with `disposition` hold and a withdraw."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    out = lines(tmp_path, r, sv, [closing_three(k) for k in range(1, 5)])
    assert [sv_d for sv_d in (w.get("disposition") for w, _ in out[:3])] == [None, None, None]
    why, b = out[3]
    assert why["disposition"] == {"from": "hunt", "to": "hold", "why": "entry", "dwell": 2.0}
    assert b.type == "melee" and b.args["disposition"] == "hold" and "withdrawX" in b.args
    assert sv.disposition == "hold"


def hold_rig(tmp_path):
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    lines(tmp_path, r, sv, [closing_three(k) for k in range(1, 5)])
    assert sv.disposition == "hold"
    return r, sv


def test_hold_is_kept_under_the_dwell_when_the_count_flickers_to_two(tmp_path):
    """In `hold`, the count flickers to two for one line and back: no change (the dwell and the exit's own clock);
    two standing for DISPOSITION_DWELL_S within GROUP_ENTRY_R + RETREAT_HOLD_R leaves to `hunt`."""
    r, sv = hold_rig(tmp_path)
    two = [zp(1, 0.0, 1.9), zp(2, -70.0, 4.0), zp(3, 70.0, 9.0)]   # 3 still listed (the World's ZOMBIE_TTL_S), far
    line(tmp_path, r, sv, two)
    line(tmp_path, r, sv, closing_three(5))
    assert sv.disposition == "hold"
    out = lines(tmp_path, r, sv, [two] * 5)
    tos = [w.get("disposition", {}).get("to") for w, _ in out]
    assert tos[:4] == [None] * 4 and tos[4] == "hunt" and sv.disposition == "hunt"


def test_a_pair_closing_at_a_wide_spread_is_pulled_to_a_line_under_hunt(tmp_path):
    """Fix 1 (the controller's ruling, Plan 36's pair behaviour): under `hunt` two standing closing within
    GROUP_ENTRY_R at bearings 0 and 90 (the spread 90, over PULL_SPREAD_DEG), the nearest beyond the reach: the melee
    is re-sent with the withdraw along the bisector turned about (225 degrees), `disposition` hunt, logged
    `engage_pull` {why "spread", n 2}."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3))
    line(tmp_path, r, sv, [zp(1, 0.0, 2.1), zp(2, 90.0, 5.5)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 1.9), zp(2, 90.0, 5.0)])
    assert sv.disposition == "hunt" and b.type == "melee" and b.args["disposition"] == "hunt"
    assert (why["engage_pull"]["why"], why["engage_pull"]["n"]) == ("spread", 2)
    assert why["engage_pull"]["heading"] == pytest.approx(225.0)
    assert (b.args["withdrawX"], b.args["withdrawY"]) == pytest.approx(
        (math.cos(math.radians(225.0)), math.sin(math.radians(225.0))), abs=1e-9)


def column_three(k):
    """Line k's column east of ME: 1 at bearing 0, 2 and 3 at bearings +5 and -5, each nearer a line."""
    return [zp(1, 0.0, 2.4 - 0.1 * k), zp(2, 5.0, 5.5 - 0.25 * k), zp(3, -5.0, 5.5 - 0.25 * k)]


def test_a_column_of_three_gets_no_retreat_under_hunt_and_the_retreat_under_hold(tmp_path):
    """Fix 1: three standing closing in a column (the spread 10, no spread or cone pull): inside the dwell `hunt`
    sends no withdraw (the retreat is `hold`'s alone); at `hold` the melee carries the retreat's heading away from
    their centroid (due west), logged `engage_pull` {why "retreat", n 3}, as before."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    out = lines(tmp_path, r, sv, [column_three(k) for k in range(1, 5)])
    assert all("engage_pull" not in w for w, _ in out[:3]) and sv.disposition == "hold"
    why, b = out[3]
    assert why["disposition"]["to"] == "hold" and b.args["disposition"] == "hold"
    assert (why["engage_pull"]["why"], why["engage_pull"]["n"]) == ("retreat", 3)
    assert (b.args["withdrawX"], b.args["withdrawY"]) == pytest.approx((-1.0, 0.0), abs=1e-6)


# ================================================================ string
def test_string_is_entered_at_five_and_logged_once(tmp_path):
    """Five standing within GROUP_ENTRY_R (STRING_N): after the dwell `string`, logged once; the melee re-sent with
    `disposition` string and the string heading (logged `string_heading` {deg, open, room}), away from the group
    (west) on open ground."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    out = lines(tmp_path, r, sv, [group(5, 4.0)] * 5)
    whys = [w.get("disposition") for w, _ in out]
    changed = [d for d in whys if d is not None]
    assert changed == [{"from": "hunt", "to": "string", "why": "count", "dwell": 2.0}]
    k = whys.index(changed[0])
    why, b = out[k]
    assert b.type == "melee" and b.args["disposition"] == "string"
    assert why["string_heading"]["room"] is None and why["string_heading"]["open"] == P.STRING_LOOK_R
    assert (b.args["withdrawX"], b.args["withdrawY"]) == pytest.approx((-1.0, 0.0), abs=1e-6)
    assert all(a2.type == "melee" for a2 in r.acts.history)


def string_rig(tmp_path):
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    lines(tmp_path, r, sv, [group(5, 4.0)] * 5)
    assert sv.disposition == "string"
    return r, sv


def test_string_holds_at_four_and_leaves_to_hold_after_the_dwell_at_three(tmp_path):
    """In `string`: four standing (inside the hysteresis band) hold it whatever the time; three for under
    DISPOSITION_DWELL_S hold it; three for the dwell leave to `hold` (why count)."""
    r, sv = string_rig(tmp_path)
    lines(tmp_path, r, sv, [group(3, 4.0)] * 6)   # with the first line's 1, still listed at 2.4 tiles: four
    assert sv.disposition == "string" and sv.group_n == 4
    out = lines(tmp_path, r, sv, [group(2, 4.0)] * 5)
    tos = [w.get("disposition", {}).get("to") for w, _ in out]
    assert tos[:4] == [None] * 4 and tos[4] == "hold" and sv.disposition == "hold"


def test_hold_pinned_for_three_seconds_strings(tmp_path):
    """In `hold` (three standing, under STRING_N), the engaged melee's work leaf reading `pinned` for STRING_PIN_S
    with the count not falling: `string` (why pinned); unpinned, the hold stays."""
    r, sv = hold_rig(tmp_path)
    zs = closing_three(4)
    for k in range(8):
        m = melee_of(r)
        r.fake.act(m.aid, "progress", "melee", result={"step": "work", "work": {"pinned": True, "n": 3}})
        r.pump()
        why, _ = line(tmp_path, r, sv, zs)
        if sv.disposition == "string":
            break
    assert sv.disposition == "string" and why["disposition"]["why"] == "pinned" and k == 6


def test_hold_unpinned_stays(tmp_path):
    r, sv = hold_rig(tmp_path)
    lines(tmp_path, r, sv, [closing_three(4)] * 8)
    assert sv.disposition == "hold"


# ================================================================ break
def test_break_at_the_health_floor_takes_the_flee_only_after_the_floor_hand_back(tmp_path):
    """In `hold`, the health falls to 35 (under FLEE_HEALTH): `break` at once (why health, no dwell), the release asked
    on the engaged melee (`release` true on its re-send), the Fight kept; the reflex's `floor` hand-back ends it and
    the next line is the rows' flee (three standing: `many`), logged `release` {asked, waited, end floor}."""
    r, sv = hold_rig(tmp_path)
    zs = closing_three(4)
    why, b = line(tmp_path, r, sv, zs, health=35.0)
    assert why["disposition"]["to"] == "break" and why["disposition"]["why"] == "health"
    assert b.type == "melee" and b.args["release"] is True and b.args["disposition"] == "hold"
    accept(r, b, "work")
    why, c = line(tmp_path, r, sv, zs, health=35.0)
    assert c is b and sv.mode == "fight"
    r.fake.act(b.aid, "done", "melee", result={"end": "handback", "why": "floor"})
    r.pump()
    why, d = line(tmp_path, r, sv, zs, health=35.0)
    assert d.type == "steer" and why.get("flee") in ("health", "many")   # the rows below: three standing read `many`
    assert why["release"]["end"] == "floor" and why["release"]["waited"] == pytest.approx(1.0)


def test_a_release_not_handed_back_takes_the_flee_at_the_bound(tmp_path):
    """The release asked and no hand-back: the Fight is kept until RELEASE_WAIT_S, then the flee, `release` {end
    bound}."""
    r, sv = hold_rig(tmp_path)
    zs = closing_three(4)
    why, b = line(tmp_path, r, sv, zs, health=35.0)
    accept(r, b, "work")
    out = lines(tmp_path, r, sv, [zs] * 6, health=35.0)
    kinds = [a.type for _, a in out]
    k = next(i for i, (w, _) in enumerate(out) if "release" in w)
    assert all(t == "melee" for t in kinds[:k]) and out[k][0]["release"]["end"] == "bound"
    assert out[k][0]["release"]["waited"] >= P.RELEASE_WAIT_S and out[k][1].type != "melee"


# ================================================================ the string heading on the map
def lane_rig(tmp_path, room=None):
    """ME at (100.5, 200.5) in a north-south lane one square wide (x 100), its walls the west edges of x 100 and x 101
    from y 190 to 210, everything else open ground; a group of five east at 3 tiles."""
    r = rig(tmp_path)
    over = {}
    for y in range(190, 211):
        over[(100, y)] = {"blockW": True}
        over[(101, y)] = {"blockW": True}
    r.scan(_grid(96, 190, 105, 210, over=over))
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    r.frame(x=100.5, y=200.5, zombies=[z(1, 103.5, 200.5)])
    if room is not None:
        r.world.room_ring = {"h": list(room), "stop": ["open"] * 8, "tick": 1}
    return r, sv


def test_the_string_heading_takes_the_lane_s_open_end_over_the_way_straight_away(tmp_path):
    """The group east, the way straight away (west) walled at the lane's west edge: of the headings within
    STRING_TURN_DEG either side, the lane's ends (90 and 270 degrees, STRING_LOOK_R open) win, the tie to the nearer
    to straight away, then the lower turn: 90 degrees (the world's +y)."""
    r, sv = lane_rig(tmp_path)
    assert r.world.open_line(180.0, P.STRING_LOOK_R) < 1.0
    vec, why = sv._string_heading()
    assert why["deg"] == pytest.approx(90.0) and why["open"] == P.STRING_LOOK_R and why["room"] is None
    assert vec == pytest.approx((0.0, 1.0), abs=1e-9)


def test_the_string_heading_is_clamped_to_the_ring(tmp_path):
    """The ring reads 90 degrees closed and 45 open: the lane's heading clamped to 45 (`room` 45), as the pull is."""
    r, sv = lane_rig(tmp_path, room=(3.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    vec, why = sv._string_heading()
    assert why["deg"] == pytest.approx(90.0) and why["room"] == 45.0
    assert vec == pytest.approx((math.cos(math.radians(45.0)), math.sin(math.radians(45.0))), abs=1e-9)


def test_the_string_heading_with_the_ring_closed_sends_none(tmp_path):
    r, sv = lane_rig(tmp_path, room=(0.0,) * 8)
    vec, why = sv._string_heading()
    assert vec is None and why["room"] == "closed"


# ================================================================ the switch off
def test_with_the_switch_off_the_melee_carries_no_disposition(tmp_path):
    """DISPOSITION off: Plan 36's melee, no `disposition` and no `release` on the wire, no `disposition` why."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.DISPOSITION = False
    r.frame(zombies=[zp(1, 0.0, 1.8)])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee" and "disposition" not in a.args and "release" not in a.args
    assert "disposition" not in threat_why(tmp_path) and sv.disposition is None
