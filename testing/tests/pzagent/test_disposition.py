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
        2.0, 5, 3.0, 2.0, 1.0)   # fix 2: the run from 1.0 tiles a second
    assert (P.STRING_ENTRY_R, P.STRING_MIN_GAP, P.STRING_RELEASE_R, P.SPRINTER_V) == (10.0, 1.5, 8.0, 1.6)
    assert (P.STRING_TURN_DEG, P.STRING_STEP_DEG, P.STRING_LOOK_R, P.RELEASE_WAIT_S, P.SPRINT_READS) == (
        120.0, 15.0, 10.0, 2.5, 3)
    assert S.T22_SWITCHES == ("DISPOSITION", "ENGAGED_RIDE") and "T22_SWITCHES" in S.__all__   # fix 3's ride
    assert T.Threat.DISPOSITION is True and T.Threat.ENGAGED_RIDE is False   # fix 6: the gate's, by default
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
    """Five standing within GROUP_ENTRY_R (STRING_N), the nearest beyond STRING_MIN_GAP: `string` on the first line
    that reads them (fix 2: the count's jump takes no dwell), logged once; the melee re-sent with `disposition`
    string and the string heading (logged `string_heading` {deg, open, room}), away from the group (west) on open
    ground."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    out = lines(tmp_path, r, sv, [group(5, 4.0)] * 5)
    whys = [w.get("disposition") for w, _ in out]
    changed = [d for d in whys if d is not None]
    assert changed == [{"from": "hunt", "to": "string", "why": "count", "dwell": 0.5}]
    k = whys.index(changed[0])
    assert k == 0
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


# ================================================================ fix 2: the string at range, never inside the clump
def test_eight_coming_enter_the_string_at_once_from_hunt_with_its_heading(tmp_path):
    """Fix 2 (the string probe `x_trial-ladder-20261112-055128`: the string entered after the dwell with four already
    within 1.6 tiles): one zombie met at 2.4 tiles (`hunt`, the melee); then eight standing listed at 9 to 10.5 tiles
    east and the first stepped back to 7; the next line all eight closing to 8 to 10 tiles (within STRING_ENTRY_R, none within
    GROUP_ENTRY_R): `string` at once, 1.0 s into `hunt` (no dwell on the count's jump, why "coming"), the melee sent
    at the pin 7 tiles off (within STRING_RELEASE_R) with `disposition` string and the string heading (west)."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.4))
    assert sv.disposition == "hunt"
    fan = (0.0, 20.0, -20.0, 35.0, -35.0, 10.0, -10.0, 45.0)
    line(tmp_path, r, sv, [zp(1, 0.0, 7.0)] + [zp(10 + i, b, 10.5 - 0.2 * i) for i, b in enumerate(fan)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 7.0)] + [zp(10 + i, b, 10.0 - 0.25 * i) for i, b in enumerate(fan)])
    assert why["disposition"] == {"from": "hunt", "to": "string", "why": "coming", "dwell": 1.0}
    assert sv.group_n == 0 and why["string_heading"]["deg"] == pytest.approx(180.0, abs=20.0)
    assert b.type == "melee" and b.args["disposition"] == "string" and b.args["withdrawX"] < -0.9


def test_five_within_six_with_the_nearest_at_1_2_hold_and_never_string(tmp_path):
    """Fix 2: five standing within GROUP_ENTRY_R with the nearest at 1.2 tiles (inside STRING_MIN_GAP, the clump): no
    `string` entered at range on any line; `hold` after the dwell (why entry). (Fix 3's clump entry comes once `hold`
    has held its dwell: `test_a_hold_inside_a_crowd_strings_after_string_pin_s`.)"""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 1.2))
    out = lines(tmp_path, r, sv, [[zp(1, 0.0, 1.2)] + group(4, 4.0)] * 6)
    tos = [w.get("disposition", {}).get("to") for w, _ in out]
    assert "string" not in tos and sv.disposition == "hold"
    assert next(w["disposition"] for w, _ in out if "disposition" in w)["why"] == "entry"


def test_a_string_whose_nearest_stays_inside_the_gap_goes_to_hold(tmp_path):
    """Fix 2: in `string`, the nearest standing at 1.0 tiles (inside STRING_MIN_GAP) for STRING_PIN_S: `hold`, why
    "clump"; the lines under it keep the string."""
    r, sv = string_rig(tmp_path)
    out = lines(tmp_path, r, sv, [[zp(1, 0.0, 1.0)] + group(5, 4.0)[1:]] * 8)
    tos = [w.get("disposition", {}).get("to") for w, _ in out]
    k = tos.index("hold")
    assert out[k][0]["disposition"]["why"] == "clump" and k == 6 and all(t is None for t in tos[:k])


# ================================================================ fix 3: the clump entry, the contract, the ride
from agent.base.pza1 import Rip  # noqa: E402

from .test_survive_g import part  # noqa: E402

CLUMP = [zp(1, 0.0, 1.0), zp(2, 60.0, 1.1), zp(3, -60.0, 1.2), zp(4, 120.0, 1.3), zp(5, -120.0, 1.4)]


def test_a_hold_inside_a_crowd_strings_after_string_pin_s(tmp_path):
    """Fix 3 (the horde8 trial `x_trial-ladder-20261112-061307`: six game minutes of `hold` inside four to seven at
    0.5 to 0.9 tiles, the string barred by STRING_MIN_GAP): five standing within GROUP_ENTRY_R, the nearest at 1.0
    (inside the gap): `hold` first (no string at range), then, once STRING_N have stood STRING_PIN_S and the hold its
    dwell, `string` (why crowd) whatever the gap, its melee carrying `disposition` string."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 1.0))
    out = lines(tmp_path, r, sv, [CLUMP] * 12)
    ds = [w["disposition"] for w, _ in out if "disposition" in w]
    assert [d["to"] for d in ds] == ["hold", "string"] and ds[1]["why"] == "crowd"
    k = next(i for i, (w, _) in enumerate(out) if w.get("disposition", {}).get("to") == "string")
    assert out[k][1].type == "melee" and out[k][1].args["disposition"] == "string"
    assert all(w.get("disposition", {}).get("to") != "hold" for w, _ in out[k + 1:])   # no clump exit for it


def test_a_pinned_hold_strings_whatever_the_gap(tmp_path):
    """Fix 3: three standing (under STRING_N), the nearest at 1.0, the leaf `pinned` for STRING_PIN_S: `string`, why
    pinned (fix 2's gap no longer bars the entries from inside the clump)."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 1.0))
    zs = CLUMP[:3]
    for k in range(14):
        m = melee_of(r)
        r.fake.act(m.aid, "progress", "melee", result={"step": "work", "work": {"pinned": True, "n": 3}})
        r.pump()
        why, _ = line(tmp_path, r, sv, zs)
        if sv.disposition == "string":
            break
    assert sv.disposition == "string" and why["disposition"]["why"] == "pinned"


def test_a_flee_row_in_contact_under_a_fight_disposition_is_the_melee_at_the_nearest(tmp_path):
    """Fix 3 (the same trial, lines 153 and 157: the melee ended in contact and the drag guard, reading no engaged
    melee, steered `many`): in `hold`, the melee ended (lost), the frame reading two attackers (the guard's count)
    with three standing within KEEP_R: no steer; the melee at the nearest standing, logged `engage_dispatch` {from
    "many", target 1}."""
    r, sv = hold_rig(tmp_path)
    m = melee_of(r)
    r.fake.act(m.aid, "done", "melee", result={"end": "lost", "why": "out of range"})
    r.pump()
    zs = [zp(1, 0.0, 0.7), zp(2, 120.0, 0.9), zp(3, -120.0, 1.1)]
    why, b = line(tmp_path, r, sv, zs, attackers=2)
    assert b.type == "melee" and b.args["targetId"] == 1
    assert why["engage_dispatch"] == {"from": "many", "target": 1} and "flee" not in why


def test_a_lost_melee_in_contact_re_pins_the_nearest_standing(tmp_path):
    """Fix 3 (`dispatch.FightDispatch._pin_nearest`): the melee at 1 ends `lost` in contact while 2 stands nearer
    (0.6 tiles): the next melee goes at 2, never at a zombie beyond KEEP_R."""
    r, sv = hold_rig(tmp_path)
    m = melee_of(r)
    r.fake.act(m.aid, "done", "melee", result={"end": "lost", "why": "no progress"})
    r.pump()
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 2.2), zp(2, 90.0, 0.6), zp(3, -70.0, 4.0)])
    assert b.type == "melee" and b.args["targetId"] == 2


BLEED = {"parts": [part(4, bleeding=True, bleedingTime=5.0)], "bleeding": 1}   # an upper-body part bleeding
SHIRT = 20


def ride_rig(tmp_path, worn=False):
    """`hold_rig`'s engaged melee with a cotton T-shirt held (`worn`: worn) and part 4 bleeding on the next line;
    ENGAGED_RIDE on (fix 6 turned it off by default: these cases read the ride's on arm)."""
    r, sv = hold_rig(tmp_path)
    sv.ENGAGED_RIDE = True
    r.event("item_added", itemId=SHIRT, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton",
            worn=worn)
    accept(r, melee_of(r), "work")
    return r, sv


def ride_line(tmp_path, r, sv, zs):
    """One line over `zs` with part 4 bleeding, 2.5 s on (past CLOCK_SPEED_S: the zombies' tracks restart, so the
    clock reads their state's floors, WALK_TPS for a chaser)."""
    r.advance(2.0)
    return line(tmp_path, r, sv, zs, wounds=BLEED)


def three_at(d):
    """Three standing chasers east of ME, the nearest at `d` tiles."""
    return [zp(1, 0.0, d), zp(2, 30.0, d + 0.3), zp(3, -30.0, d + 0.5)]


@pytest.mark.parametrize("d", [0.9, 6.0])
def test_a_riding_rip_under_hold_waits_for_the_clock(tmp_path, d):
    """Fix 4 (Task 2 Lua fix 2: while a rip rides the melee the reflex presses nothing): under `hold` with the melee
    engaged, part 4 bleeding and an unworn cotton T-shirt held, the nearest at 0.9 tiles (ttc about 0.1 s) or at 6
    tiles walking (ttc (6 - 0.7) / 1.45 = 3.66 s against the rip's 4.134 + 1.5): no rip; logged `care_ride` {why
    "clock"} and `clock` {action rip, ride "melee", refused true}."""
    r, sv = ride_rig(tmp_path)
    why, a = ride_line(tmp_path, r, sv, three_at(d))
    assert a.type != "rip" and not any(x.type == "rip" for x in r.acts.history)
    assert why["care_ride"] == {"under": "hold", "cmd": None, "why": "clock"}
    assert why["clock"]["action"] == "rip" and why["clock"]["ride"] == "melee" and why["clock"]["refused"] is True


def test_a_riding_rip_under_hold_goes_when_the_clock_allows(tmp_path):
    """Fix 4: the nearest at 9.5 tiles walking (ttc (9.5 - 0.7) / 1.45 = 6.07 s, above 5.634; 12 tiles lies beyond
    the hold radius, DISENGAGE_R, where the threat and its disposition end): the rip goes with keepMoving riding the
    melee, logged `care_ride` {under hold, cmd rip} and `clock` {action rip, ride "melee"}; the melee still runs (the
    Python's ride model) and the next line sends nothing over it."""
    r, sv = ride_rig(tmp_path)
    m = melee_of(r)
    why, rip = ride_line(tmp_path, r, sv, three_at(9.5))
    assert rip.type == "rip" and rip.args["itemId"] == SHIRT and rip.args["keepMoving"] is True
    assert why["care_ride"] == {"under": "hold", "cmd": "rip"}
    assert why["clock"]["ride"] == "melee" and "refused" not in why["clock"]
    assert sv.fight._engaged() and melee_of(r) is m
    accept(r, rip)
    why, c = line(tmp_path, r, sv, three_at(9.5), wounds=BLEED)
    assert c is rip and sv.fight._engaged()


def test_a_bleed_with_only_a_worn_garment_waits_logged_worn(tmp_path):
    """Fix 3: the trial's own inventory (the cotton garments all worn: an unwear stops on a walk): no command over
    the engaged melee, logged `care_ride` {under hold, cmd null, why worn}."""
    r, sv = ride_rig(tmp_path, worn=True)
    m = melee_of(r)
    why, a = line(tmp_path, r, sv, closing_three(4), wounds=BLEED)
    assert a.type == "melee" and why["care_ride"] == {"under": "hold", "cmd": None, "why": "worn"}


# ================================================================ fix 5: the string's exit by the standing count at range
def strung(n_near, n_far):
    """`n_near` standing at 4 to 5 tiles east and `n_far` at 7 to 9.5 (within STRING_ENTRY_R, beyond GROUP_ENTRY_R),
    none closing (the same squares every line); the first line's 1 moved out to 9.8."""
    near = [zp(20 + i, b, 4.0 + 0.3 * i) for i, b in enumerate((0.0, 25.0, -25.0)[:n_near])]
    far = [zp(30 + i, b, 7.0 + 0.5 * i) for i, b in enumerate((10.0, -10.0, 35.0, -35.0, 50.0, -50.0)[:n_far])]
    gone = [zp(10 + i, 180.0, 14.0) for i in range(8)]   # string_rig's group moved away (still listed: ZOMBIE_TTL_S)
    return [zp(1, 0.0, 9.8)] + near + far + gone


def test_a_strung_out_group_keeps_the_string_past_the_dwell(tmp_path):
    """Fix 5 (the horde8 trial `x_trial-ladder-20261112-065221`, decision line 14: `string -> hold why count` with two
    within GROUP_ENTRY_R and five more within 10 tiles): in `string`, two standing within 6 tiles and six more within
    10 (none closing): the string holds through 4 s of lines (more than GROUP_LEAVE_N stand within STRING_ENTRY_R)."""
    r, sv = string_rig(tmp_path)
    out = lines(tmp_path, r, sv, [strung(2, 6)] * 8)
    assert all("disposition" not in w for w, _ in out) and sv.disposition == "string"


def test_three_within_string_entry_r_leave_the_string_to_hold(tmp_path):
    """Fix 5: in `string`, three standing within STRING_ENTRY_R (one within 6, two beyond) and the rest gone beyond
    12 tiles: `hold` (why count) once they have read so for DISPOSITION_DWELL_S."""
    r, sv = string_rig(tmp_path)
    out = lines(tmp_path, r, sv, [strung(1, 1)] * 6)   # 1 at 9.8, one at 4, one at 7: three within STRING_ENTRY_R
    tos = [w.get("disposition", {}).get("to") for w, _ in out]
    k = tos.index("hold")
    assert out[k][0]["disposition"]["why"] == "count" and k == 4 and all(t is None for t in tos[:k])


def test_a_string_melee_lost_out_of_range_is_re_sent_never_walked(tmp_path):
    """Fix 5 (the same trial, decision line 11: the string's melee ended `lost` out of range at 6.6 tiles and the
    Fight's approach `walkTo` went): in `string`, the melee ends `lost` out of range with the nearest standing at 4.5
    tiles (within STRING_RELEASE_R): the next send is the melee at it, `disposition` string, no walk, aim or seek."""
    r, sv = string_rig(tmp_path)
    m = melee_of(r)
    r.fake.act(m.aid, "accepted", "melee")
    r.fake.act(m.aid, "done", "melee", result={"end": "lost", "why": "out of range"})
    r.pump()
    zs = ([zp(1, 0.0, 6.6), zp(2, 20.0, 4.5)] + [zp(10 + i, b, 5.5) for i, b in enumerate((40.0, -40.0, 60.0))]
          + [zp(13, 0.0, 12.0), zp(14, 0.0, 12.0)])   # string_rig's 13 and 14 moved away (still listed)
    why, b = line(tmp_path, r, sv, zs)
    assert b.type == "melee" and b.args["disposition"] == "string" and b.args["targetId"] == 2
    assert not any(a.type in ("walkTo", "aim") for a in r.acts.history)


# ================================================================ fix 6: the care starts through the release
def far_string(tmp_path, d):
    """`string_rig`'s string with a cotton T-shirt held and its melee accepted; then every zombie moved to `d` tiles
    east (2.5 s on: the tracks restart, the clock reads WALK_TPS for a chaser) with part 4 bleeding: the line."""
    r, sv = string_rig(tmp_path)
    r.event("item_added", itemId=SHIRT, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton")
    accept(r, melee_of(r), "work")
    zs = [zp(i, b, d + 0.1 * k) for k, (i, b) in enumerate(((1, 0.0), (10, 10.0), (11, -10.0), (12, 20.0),
                                                              (13, -20.0), (14, 30.0)))]
    r.advance(2.0)
    return r, sv, zs, line(tmp_path, r, sv, zs, wounds=BLEED)


def test_under_string_a_bleed_releases_the_melee_then_the_rip_starts(tmp_path):
    """Fix 6 (the horde8 trial `x_trial-ladder-20261112-070655`, decision lines 41 to 63: the bleed yield took the
    care over the string): under `string` with the nearest at 9.5 tiles walking (ttc 6.07 s, above the rip's 5.634)
    and part 4 bleeding: the melee is re-sent with `release` true (`care_hold` {why "release"}), no care command; on
    the reflex's `released safe` hand-back the next line yields to the care, logged `care_start` {under string,
    action rip, released "released"}, and the rip goes standing (no keepMoving), with no stop and no steer."""
    r, sv, zs, (why, b) = far_string(tmp_path, 9.5)
    assert b.type == "melee" and b.args["release"] is True and b.args["disposition"] == "string"
    assert why["care_hold"] == {"why": "release", "action": "rip"}
    accept(r, b, "work")
    r.fake.act(b.aid, "done", "melee", result={"end": "handback", "why": "released", "safe": True})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=zs, wounds=BLEED)
    tick(r, sv)
    from .test_survive import last
    d = last(tmp_path)
    th = d["inputs"]["branches"]["threat"]
    assert th["care_start"] == {"under": "string", "action": "rip", "released": "released"}
    assert d["branch"] == "care" and d["action"]["type"] == "rip" and "keepMoving" not in d["action"]["args"]
    assert not any(a.type in ("stop", "steer") for a in r.acts.history)


def test_under_string_a_bleed_the_clock_refuses_holds_the_care(tmp_path):
    """Fix 6: the same with the nearest at 6 tiles (ttc 3.66 s): no release, no care command, no clock leg; logged
    `care_hold` {why "clock", action rip}."""
    r, sv, zs, (why, b) = far_string(tmp_path, 6.0)
    assert why["care_hold"] == {"why": "clock", "action": "rip"}
    assert not any(a.type in ("stop", "steer", "rip", "unwear", "bandage") for a in r.acts.history)
    assert not any(a.type == "melee" and a.args.get("release") for a in r.acts.history)
