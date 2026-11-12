"""Plan 36 Task 4 (the action clock, `planner/clock.py`; the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.4;
Angus's direction, memory `finish-actions-gain-distance`): no timed action starts unless the smallest time to contact
exceeds its duration plus ACTION_MARGIN_S; a refused one gains distance along the room's open heading first, then runs
to its end; a running one is cut only by the clock, into the melee, never by a steer.

F21's shape (`f_goals_21-20261111-150552`, decision lines 427 to 494: four standing west of the character, three parts
bleeding, a rip wanted; every one of its seven rips started with the nearest standing 3.4 to 5.7 tiles off and was
superseded by the next steer) and the trials' door case (two thumping at 0.3 tiles, an `interact` wanted; P31-T, not
evidence) on the fake mod announcing PZA/1.13 with the `melee` cap. Every fixture is synthetic, never a replay. The
rip rides no walk here: the Lua's side slot rides a keepMoving bandage alone (`clock.py`'s docstring), so the rip goes
at the stop the clock allows."""
import pytest

from agent.base import pza1
from agent.base.planner import clock as CK
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .fakemod import DEFAULT_FRAME
from .test_survive import last, threat_why, tick
from .test_survive_an import accept
from .test_survive_ar import rig
from .test_survive_g import part

ME = (100.0, 200.0)   # the fake frame's default position
SHIRT = 20            # the held unworn cotton T-shirt (the rip's garment)
RAG = 41              # a clean rag (the bandage's dressing)
PARTS = (2, 5, 8)     # F21's three bleeding parts (its line 431's `dress` part 8 among them)


def zr(zid, dx, dy=0.0, state="walktoward", target=True):
    """A standing zombie `dx`, `dy` tiles off ME, its PZA/1.9 state and target."""
    return {"id": zid, "x": ME[0] + dx, "y": ME[1] + dy, "dist": (dx * dx + dy * dy) ** 0.5, "hasTarget": target,
            "crawler": False, "health": 1.0, "onFloor": None, "known": None, "state": state, "behind": None}


def four_west(near, state="walktoward"):
    """F21's four standing, west of the character: the nearest at `near` tiles (its `state`), three more behind it."""
    return [zr(1, -near, state=state), zr(2, -near - 1.0, 0.8), zr(3, -near - 1.4, -0.9), zr(4, -near - 2.0, 0.3)]


def frame(r, zs, moving=False, parts=PARTS):
    me = dict(DEFAULT_FRAME["me"], moving=moving)
    ps = [part(i, bleeding=True, bleedingTime=8.0) for i in parts]
    body = dict(DEFAULT_FRAME["body"], parts=ps, bleeding=len(ps))
    r.fake.frame(me=me, body=body, zombies=list(zs))
    r.pump()


def survive(tmp_path, shirt=True, rag=False, clock=True):
    """A Survive (the ladder, ACTION_CLOCK `clock`) on a `rig` announcing PZA/1.13 with `melee`, holding the unworn
    cotton T-shirt (`shirt`) and a clean rag (`rag`)."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.ACTION_CLOCK = clock
    if shirt:
        r.event("item_added", itemId=SHIRT, fullType="Base.Tshirt_White", weight=0.2, use="clothing", rip="cotton")
    if rag:
        r.event("item_added", itemId=RAG, fullType="Base.RippedSheets", weight=0.1, use="bandage")
    return r, sv


def step(tmp_path, r, sv, zs, moving=False, dt=0.5):
    """One decision line `dt` seconds on over `zs`: the line. A `dt` past CLOCK_SPEED_S (JUMP) starts every zombie's
    track afresh (the clock's own speed reads only the frames of the last CLOCK_SPEED_S), so a fixture that moves the
    zombies by more than a walk reads their state's floors alone."""
    r.advance(dt)
    frame(r, zs, moving=moving)
    tick(r, sv)
    return last(tmp_path)


JUMP = P.CLOCK_SPEED_S + 0.5   # seconds: a step whose zombies' tracks restart (`step`)


def care_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["care"]


def types(r):
    return [a.type for a in r.acts.history]


# ================================================================ the switch
def test_the_switch_is_on_by_default_in_t21():
    assert S.T21_SWITCHES == ("ACTION_CLOCK", "BACKSWING") and "T21_SWITCHES" in S.__all__
    assert S.Survive.ACTION_CLOCK is True


# ================================================================ F21's shape
def test_no_rip_starts_with_the_nearest_at_one_tile_lunging(tmp_path):
    """F21's shape with the nearest at 1.0 tile lunging (0.19 s to contact): no care step goes (no stop, unwear or
    rip); the threat branch answers with the melee (a standing zombie within KEEP_R: the Fight's, rule (a)). Pinned with
    ENGAGED_RIDE off (a named change, Plan 37 Task 3 fix 3: under `hold` the rip rides the engaged melee with
    keepMoving, `test_disposition.py`)."""
    r, sv = survive(tmp_path)
    sv.ENGAGED_RIDE = False
    for _ in range(3):
        line = step(tmp_path, r, sv, four_west(1.0, state="lunge"))
        assert line["branch"] == "threat"
    assert not {"stop", "unwear", "rip", "bandage"} & set(types(r))
    assert "melee" in types(r)


def test_the_gain_distance_leg_goes_when_the_clock_refuses_the_rip(tmp_path):
    """The nearest at 4.0 tiles walking: (4.0 - 0.7) / 1.45 = 2.28 s against the rip's 4.134 + 1.5: refused. The
    care branch's line sends the gain-distance leg, a steer at a run straight away (east: no ring on the frame, the
    first clear turn), logged `clock` {action rip, refused, leg "sent"}. Fix 2 (PZA/1.15's side slot admits the rip
    with keepMoving): on the next line, with the leg running, the rip rides it (`test_the_refused_rip_rides_the_leg`)."""
    r, sv = survive(tmp_path)
    line = step(tmp_path, r, sv, four_west(4.0))
    assert line["branch"] == "care" and line["action"]["type"] == "steer"
    args = line["action"]["args"]
    assert (args["vx"], args["vy"], args["gait"]) == (1.0, 0.0, "run")
    assert args["seconds"] == pytest.approx(P.ACTION_S["rip"] + P.ACTION_MARGIN_S)   # fix 2b: the rip will ride it
    ck = care_why(tmp_path)["clock"]
    assert ck["action"] == "rip" and ck["refused"] is True and ck["leg"] == "sent"
    assert ck["ttc"] == pytest.approx(3.3 / 1.45, abs=1e-3) and ck["need"] == pytest.approx(4.134 + 1.5)


# ================================================================ fix 2: the rip rides the leg
def _riding_rip(tmp_path):
    """F21's shape at 4.0 tiles walking: the leg, accepted; the next line's riding rip, accepted. (r, sv, rip)."""
    r, sv = survive(tmp_path)
    step(tmp_path, r, sv, four_west(4.0))
    accept(r, r.acts.history[-1])
    step(tmp_path, r, sv, four_west(4.6), moving=True)
    rip = r.acts.history[-1]
    accept(r, rip)
    return r, sv, rip


def test_the_refused_rip_rides_the_leg(tmp_path):
    """Plan 36 Task 4 fix 2 (the Tend side slot's contract, task-2-report.md Phase B 7c): with the leg running and the
    clock still refusing the rip (4.6 tiles walking: 2.69 s against 5.634), the care's line sends the rip of the held
    T-shirt with keepMoving (no stop), logged `clock` {action rip, ride true, refused, dress: the Dress's log with
    `rip_ride`}; the
    leg is not superseded on the wire (no stop, no second steer)."""
    r, sv, rip = _riding_rip(tmp_path)
    line = last(tmp_path)
    assert line["branch"] == "care" and line["action"] == {"type": "rip", "args": {"itemId": SHIRT, "keepMoving": True}}
    ck = care_why(tmp_path)["clock"]
    assert ck["action"] == "rip" and ck["ride"] is True and ck["refused"] is True
    assert ck["dress"]["rip_ride"] is True and sv.care.dress.phase == "sent"
    assert types(r) == ["steer", "rip"]
    line = step(tmp_path, r, sv, four_west(5.0), moving=True)
    assert line["action"] is None and r.acts.history[-1] is rip   # the riding rip runs to its end


def test_the_leg_runs_for_the_riding_rip_s_duration_and_a_leg_with_no_ride_keeps_clock_leg_s(tmp_path):
    """Fix 2b: the leg a rip will ride runs the rip's 4.134 s plus ACTION_MARGIN_S (5.634 s, logged `seconds` on the
    `clock` why), longer than the rip, so the riding rip never finishes standing; a refused bandage's leg (no ride)
    keeps CLOCK_LEG_S."""
    r, sv, rip = _riding_rip(tmp_path)
    leg = r.acts.history[0]
    assert leg.type == "steer" and leg.args["seconds"] == pytest.approx(5.634)
    assert leg.args["seconds"] > P.ACTION_S["rip"] and rip.args["keepMoving"] is True
    (tmp_path / "b").mkdir()
    r2, sv2 = survive(tmp_path / "b", shirt=False, rag=True)
    line = step(tmp_path / "b", r2, sv2, four_west(9.0))
    assert line["action"]["type"] == "steer" and line["action"]["args"]["seconds"] == P.CLOCK_LEG_S
    assert care_why(tmp_path / "b")["clock"]["seconds"] == P.CLOCK_LEG_S


def test_the_rip_done_while_walking_is_followed_by_the_bandage_once_the_clock_allows(tmp_path):
    """The riding rip ends done walking (`walking` true, one clean rag): the bandage waits while the clock refuses it
    (9.0 tiles: 5.72 s against 6.944, the leg held) and goes standing (no keepMoving) once it allows (11.5 tiles)."""
    r, sv, rip = _riding_rip(tmp_path)
    r.fake.act(rip.aid, "done", "rip", result={"rags": 1, "dirty": 0, "walking": True})
    r.event("item_removed", itemId=SHIRT, fullType="Base.Tshirt_White")
    r.event("item_added", itemId=RAG, fullType="Base.RippedSheets", weight=0.1, use="bandage")
    line = step(tmp_path, r, sv, four_west(9.0), moving=True, dt=JUMP)
    assert line["action"] is None or line["action"]["type"] == "steer"
    assert "bandage" not in types(r)
    line = step(tmp_path, r, sv, four_west(11.5), moving=True, dt=JUMP)
    assert line["action"]["type"] == "bandage" and "keepMoving" not in line["action"]["args"]
    assert line["action"]["args"]["itemId"] == RAG


def test_a_riding_rip_under_the_margin_is_cut_into_the_melee_and_no_bandage_rides(tmp_path):
    """The riding rip running, the nearest closing to 1.2 tiles (0.34 s): the clock's cut, the melee at it (`clock`
    {action rip, cut}), never a steer re-aim nor a riding bandage."""
    r, sv, rip = _riding_rip(tmp_path)
    line = step(tmp_path, r, sv, four_west(1.2), dt=JUMP)
    assert line["branch"] == "threat" and line["action"]["type"] == "melee"
    assert threat_why(tmp_path)["clock"]["cut"] is True and threat_why(tmp_path)["clock"]["action"] == "rip"
    assert types(r) == ["steer", "rip", "melee"]
    assert not any(a.type == "bandage" for a in r.acts.history)


def test_the_leg_takes_the_room_ring_s_most_open_heading_within_room_open_deg(tmp_path):
    """The ring (PZA/1.14's `me.room`, `World.room`) reading 0.5 tiles clear due east, 3.0 at 45 degrees (the world's
    +y side) and 1.0 at -45: the gain-distance leg takes 45 degrees, logged `room_open` 45 on the care's `clock` why;
    a ring reading no clear tile within ROOM_OPEN_DEG keeps the straight-away heading (`policies.room_open_heading`)."""
    r, sv = survive(tmp_path)
    ring = {"h": [0.5, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], "stop": ["wall"] * 8, "tick": 1}
    r.advance(0.5)
    me = dict(DEFAULT_FRAME["me"], moving=False, room=ring)
    ps = [part(i, bleeding=True, bleedingTime=8.0) for i in PARTS]
    r.fake.frame(me=me, body=dict(DEFAULT_FRAME["body"], parts=ps, bleeding=len(ps)), zombies=four_west(4.0))
    r.pump()
    tick(r, sv)
    line = last(tmp_path)
    ck = care_why(tmp_path)["clock"]
    assert line["action"]["type"] == "steer" and ck["room_open"] == 45.0
    assert (line["action"]["args"]["vx"], line["action"]["args"]["vy"]) == pytest.approx((0.5 ** 0.5, 0.5 ** 0.5))
    shut = {"h": [0.0] * 8, "stop": ["wall"] * 8, "tick": 2}
    assert P.room_open_heading(r.world, (1.0, 0.0)) == ((pytest.approx(0.5 ** 0.5), pytest.approx(0.5 ** 0.5)), 45.0)
    r.world.room_ring = shut
    assert P.room_open_heading(r.world, (1.0, 0.0)) == ((1.0, 0.0), None)


def test_with_the_switch_off_the_column_withholds_the_care_and_the_flee_steers(tmp_path):
    """ACTION_CLOCK off, the rules before it (Plan 34's LEAVE_CARE over Plan 32 Task 5 (c)): with three or more standing
    within GROUP_ENTRY_R the care is withheld (`care_withheld` {why "group"}) and the `many` flee steers (F21's line
    437); and with LEAVE_CARE off as well the commitment yields at 4.0 tiles (beyond CARE_HOLD_R) and the Dress's stop
    goes at once (F21's line 431), the stop the clock now refuses. Pinned with DISPOSITION off (a named change, Plan 37
    Task 3: the selector's `hunt` fights the four where the `many` flee steered)."""
    r, sv = survive(tmp_path, clock=False)
    sv.DISPOSITION = False
    line = step(tmp_path, r, sv, four_west(4.0))
    assert line["branch"] == "threat" and line["action"]["type"] == "steer"
    assert threat_why(tmp_path)["care_withheld"]["why"] == "group" and threat_why(tmp_path)["flee"] == "many"
    (tmp_path / "b").mkdir()
    r, sv = survive(tmp_path / "b", clock=False)
    sv.LEAVE_CARE = False
    line = step(tmp_path / "b", r, sv, four_west(4.0))
    assert line["branch"] == "care" and line["action"]["type"] == "stop"


def test_the_rip_goes_at_the_stop_once_the_leg_gained_the_distance(tmp_path):
    """After the leg, the four at 9.5 tiles (6.07 s at the walk's floor): the Dress's stop goes (asked with the rip after it), logged
    `clock` {action rip, waited > 0}; once still, the rip goes with its own `clock` read; no steer after it."""
    r, sv = survive(tmp_path)
    step(tmp_path, r, sv, four_west(4.0))
    accept(r, r.acts.history[-1])
    line = step(tmp_path, r, sv, four_west(9.5), moving=True, dt=JUMP)
    assert line["branch"] == "care" and line["action"]["type"] == "stop"
    ck = care_why(tmp_path)["clock"]
    assert ck["action"] == "rip" and "refused" not in ck and ck["waited"] == pytest.approx(JUMP)
    r.answer()
    line = step(tmp_path, r, sv, four_west(9.6))
    assert line["action"] == {"type": "rip", "args": {"itemId": SHIRT}}
    assert care_why(tmp_path)["clock"]["action"] == "rip"
    assert types(r) == ["steer", "stop", "rip"]


def test_a_bandage_at_the_stop_the_clock_allows(tmp_path):
    """A clean rag held: the bandage needs 5.444 + 1.5 s, so the nearest at 9.0 tiles (5.72 s) refuses it (the leg)
    and at 11.5 (7.45 s) allows it: the stop, then the standing bandage (no keepMoving)."""
    r, sv = survive(tmp_path, shirt=False, rag=True)
    line = step(tmp_path, r, sv, four_west(9.0))
    assert line["action"]["type"] == "steer" and care_why(tmp_path)["clock"]["action"] == "bandage"
    accept(r, r.acts.history[-1])
    line = step(tmp_path, r, sv, four_west(11.5), moving=True, dt=JUMP)
    assert line["action"]["type"] == "stop" and care_why(tmp_path)["clock"]["action"] == "bandage"
    r.answer()
    line = step(tmp_path, r, sv, four_west(11.6))
    assert line["action"]["type"] == "bandage" and "keepMoving" not in line["action"]["args"]
    assert line["action"]["args"]["itemId"] == RAG


def _running_bandage(tmp_path):
    r, sv = survive(tmp_path, shirt=False, rag=True)
    step(tmp_path, r, sv, [zr(1, -11.5)])
    r.answer()
    step(tmp_path, r, sv, [zr(1, -11.5)])
    a = r.acts.history[-1]
    assert a.type == "bandage"
    accept(r, a)
    return r, sv, a


def test_a_running_bandage_is_held_while_the_clock_holds_whatever_the_threat_would_do(tmp_path):
    """The bandage running, the four closing to 3.9 tiles (2.21 s, over the margin): the threat branch holds it (no
    steer, no flee leg, no melee), logged `clock` {action bandage, running}."""
    r, sv, a = _running_bandage(tmp_path)
    for near, dt in ((5.0, JUMP), (4.4, 0.5), (3.9, 0.5)):
        line = step(tmp_path, r, sv, four_west(near), dt=dt)
        assert line["branch"] == "threat" and line["action"] is None
        ck = threat_why(tmp_path)["clock"]
        assert ck["action"] == "bandage" and ck["running"] == a.aid and "cut" not in ck
    assert r.acts.history[-1] is a


def test_a_running_bandage_with_a_zombie_closing_under_the_margin_is_cut_into_the_melee(tmp_path):
    """The bandage running, the nearest closing to 1.2 tiles (0.34 s, under the margin): the cut, the melee at it
    (logged `clock` {cut, target 1} and `point_blank_fight` {over "clock"}), never a steer."""
    r, sv, a = _running_bandage(tmp_path)
    step(tmp_path, r, sv, four_west(3.9), dt=JUMP)
    line = step(tmp_path, r, sv, four_west(1.2), dt=JUMP)
    assert line["branch"] == "threat" and line["action"]["type"] == "melee"
    assert line["action"]["args"]["targetId"] == 1
    why = threat_why(tmp_path)
    assert why["clock"]["cut"] is True and why["clock"]["target"] == 1 and why["clock"]["action"] == "bandage"
    assert why["point_blank_fight"]["over"] == "clock"
    assert "steer" not in types(r)


# ================================================================ the trials' door case
def test_the_door_interact_with_two_thumping_at_point_three_is_refused_and_the_melee_sent(tmp_path):
    """The threat branch's own door `interact` (the flee's or the leave's open, F21's line 458 shape) with two
    zombies attacking at 0.3 tiles: refused (0 s to contact against the door's 0.112 + 1.5), a standing zombie in
    contact, so the decision is taken again as the Fight at the clock's zombie and its melee goes, logged `clock`
    {action door, refused, fight}. The gate's method (`ClockGate._clock_threat`) read directly: no planner-level case
    sends the door interact with two in contact (the point-blank rows fight first), P26-7f."""
    r, sv = survive(tmp_path, shirt=False)
    frame(r, [zr(1, 0.3, state="attack"), zr(2, 0.0, 0.3, state="attack")], parts=())
    sv._read(r.world, r.acts)
    owner, cmd = sv._clock_threat(sv._held, None, (sv.flee, pza1.Interact(101, 200, "open")))
    assert cmd is not None and cmd.TYPE == "melee" and owner is sv.fight
    assert sv.clock_now["action"] == "door" and sv.clock_now["refused"] is True and sv.clock_now["fight"] in (1, 2)


def test_the_door_interact_with_the_nearest_far_goes_and_one_closing_beyond_keep_r_gains_distance(tmp_path):
    """Allowed (the nearest at 9 tiles: 5.72 s): the interact unchanged, `clock` {action door, waited 0}; refused with
    nobody within KEEP_R (the nearest at 3.0 lunging: 1.44 s), the gain-distance leg."""
    r, sv = survive(tmp_path, shirt=False)
    frame(r, [zr(1, -9.0)], parts=())
    sv._read(r.world, r.acts)
    ans = (sv.flee, pza1.Interact(101, 200, "open"))
    assert sv._clock_threat(sv._held, None, ans) is ans and sv.clock_now["waited"] == 0.0
    frame(r, [zr(1, -3.0, state="lunge")], parts=())
    sv._read(r.world, r.acts)
    owner, cmd = sv._clock_threat(sv._held, None, ans)
    assert isinstance(owner, CK.ClockLeg) and cmd.TYPE == "steer" and (cmd.vx, cmd.vy) == (1.0, 0.0)


# ================================================================ the goal's loot and scan
@pytest.mark.parametrize("cmd, kind", [(pza1.Interact(98, 200, "loot", "food"), "loot"), (pza1.Scan(10), "scan")])
def test_the_goal_s_loot_and_scan_ask_the_clock(tmp_path, cmd, kind):
    """The goal branch's loot and scan (`Survive._assess_ladder`'s gate, read at `_clock_gate`): the nearest at 2.0
    tiles walking (0.90 s) refuses both (the leg); at 12 tiles both go unchanged."""
    r, sv = survive(tmp_path, shirt=False)
    frame(r, [zr(1, -2.0)], parts=())
    sv._read(r.world, r.acts)
    owner, out, why = sv._clock_gate("goal", sv.goals, cmd)
    assert isinstance(owner, CK.ClockLeg) and out.TYPE == "steer" and why["action"] == kind and why["refused"]
    frame(r, [zr(1, -12.0)], parts=())
    sv._read(r.world, r.acts)
    owner, out, why = sv._clock_gate("goal", sv.goals, cmd)
    assert owner is sv.goals and out is cmd and why["action"] == kind and "refused" not in why


def test_a_refused_episode_re_aims_its_leg_then_spent_hands_the_tick_to_the_threat(tmp_path):
    """The leg that ended while the clock still refuses is re-aimed (the episode's second leg, `waited` counting from
    its first refusal); past CLOCK_EPISODE_S the episode is spent: the commitment withholds the yield (`care_commit`
    {phase "spent"} on the threat's why) and the threat branch decides (here the `many` flee), no care step sent. Pinned
    with DISPOSITION off (a named change, Plan 37 Task 3: the selector's `hunt` fights the four where the flee
    steered)."""
    r, sv = survive(tmp_path)
    sv.DISPOSITION = False
    step(tmp_path, r, sv, four_west(4.0))
    accept(r, r.acts.history[-1])
    r.fake.act(r.acts.history[-1].aid, "done", "steer", result={})
    r.pump()
    line = step(tmp_path, r, sv, four_west(4.0), dt=1.0)
    assert line["branch"] == "care" and line["action"]["type"] == "steer"
    assert care_why(tmp_path)["clock"]["waited"] == pytest.approx(1.0)
    line = step(tmp_path, r, sv, four_west(4.0), dt=P.CLOCK_EPISODE_S)
    assert line["branch"] == "threat" and threat_why(tmp_path)["care_commit"]["phase"] == "spent"
    assert threat_why(tmp_path)["flee"] == "many"
    assert not {"stop", "unwear", "rip", "bandage"} & set(types(r))
