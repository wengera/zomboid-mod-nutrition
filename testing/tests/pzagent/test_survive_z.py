"""Survival 20 (survival iteration 18; Plan 26 Task 7; E17, `e_day_17-20261102-180459`, rows #4516-#4524;
F5, `f_goals_6-20261030-192251`, its a20 the one live window climbed `done`, for WINDOW_STALL_S; E16,
`e_day_16-20261102-125450`, through `test_survive_y`'s shed). E17's own record, read as the planner read it
(`replay_decisions.read_record` and `align`: the World through a decision line's frame and the trailing lines its tick
read), and replayed (`replay_decisions.replay`: HEAD's planner is the one E17 ran on, `6df43e92`, so with iteration
18's switches off the replay is the record's own rules). The
stand held building 2's kitchen door (10721, 10638) from line 362; its `inside` end at line 380 (frame seq 3447)
walked out by the kitchen window (10720, 10634), a `solidTrans` square holding a `counter`, where the window act a81
waited 14.3 s and failed `dead`.

- P26-I, a window way out needs a walkable inside square (`WINDOW_INNER`): `night.window_exits` leaves out a window
  whose inside square reads `solid` or `solidTrans`; its outside square is never solid (`World.window_way`).
- P26-J, the window step is stall-read like the walk (`WINDOW_STALL`): the window act holding the player within
  STUCK_MOVE for WINDOW_STALL_S is dropped and its exit refused `stalled`; a first `interrupted` end is sent once more,
  the second refused (the E17 write-up's amendment).
- P26-K, the stand leaves before the room fills (`STAND_CROWD`): the doorway stand's end `crowd` at STAND_CROWD_N
  standing held zombies within DANGER_R, read after `wound` and before `inside` (line 370: six held, none inside; the
  first bite 2 game minutes after the record's end).
- P26-K2 (Task 7 fix 1), the controller's amendment: the crowd counts standing zombies only (a fallen one is the finish
  rule's stomp); a `crowd` end with no zombie on a square of the stand's room nor on its door square takes the close
  (`doorway_exit` {crowd, close}: E17's line 364, every zombie outside), else walks out by the way out as P25-W's ends
  do (E16's line 469: 24134 on the door's inside square), else holds trapped.
"""
import functools
import os

from agent.base import replay_decisions as R
from agent.base.planner import flee as FL
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.world import World, me_xy

from . import test_survive_y as Y

E17 = os.path.join(R.ARTIFACTS, "e_day_17-20261102-180459")
COUNTER = (10720, 10634, 0)       # the kitchen window's square: its record on its own west edge, a `counter` on it
COUNTER_OUT = (10719, 10634, 0)   # the outdoor square west of it, the climb's landing
KITCHEN_DOOR = (10721, 10638, 0)  # the stand's door, kept on the outdoor square's north edge
WIN_IN = (10710.5, 10596.5)       # the centre of E16's shed window's inside square (`test_survive_y`'s rig)
STALL_LINE = 393                  # E17's line whose tick drops a81 at its stall (P26-J)


@functools.lru_cache(maxsize=1)
def e17():
    lines, rows = R.read_record(E17)
    return lines, rows, R.align(lines, rows)


def e17_world(line, **counter):
    """A World holding E17's record through decision line `line`'s frame and the trailing lines its tick read;
    `counter` fields laid over the counter window's square (a map delta, as the Lua sends one)."""
    lines, _, ends = e17()
    w = World()
    for ln in lines[:ends[line - 1][1]]:
        w.apply(ln)
    if counter:
        w.apply({"kind": "map", "mode": "delta", "squares": [dict(w.map[COUNTER], **counter)], "missing": []})
    return w


def held(w):
    """The zombies within DISENGAGE_R of the player (the threat branch's hold while a threat policy runs)."""
    return [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= P.DISENGAGE_R]


def e17_replay(upto, **on):
    """E17's record replayed through decision line `upto` with iteration 18's switches as given (each of
    `survive.T8_SWITCHES` off unless named True): the replayed decision lines."""
    def mutate(sv):
        for name in S.T8_SWITCHES:
            setattr(sv, name, bool(on.get(name)))
    return R.replay(E17, mutate=mutate, upto=upto)


def threat(row):
    return row["inputs"]["branches"]["threat"]


def test_the_iteration_18_switches():
    assert S.T8_SWITCHES[0] == "WINDOW_INNER" and "T8_SWITCHES" in S.__all__
    assert all(getattr(S.Survive, name) is True for name in S.T8_SWITCHES)


# ================================================ P26-I: a window way out needs a walkable inside square
def test_e17_s_counter_window_reads_solid_trans_with_its_counter_and_its_locked_record():
    """The reading the rule rests on: line 380's map holds the window square (10720, 10634) as a kitchen room square of
    building 2, `solidTrans` true with a `counter` container, `solid` false, its window locked on its west edge, and
    the outdoor square west of it walkable; the replay agrees with the record's line 380 (the `inside` end, the
    window way out) with iteration 18 off."""
    w = e17_world(380)
    s = w.map[COUNTER]
    assert (s["room"], s["building"], s["solid"], s["solidTrans"]) == ("kitchen", 2, False, True)
    assert [c["type"] for c in s["containers"]] == ["counter"] and (s["edgeW"], s["blockW"]) == (True, True)
    assert s["window"] == {"open": False, "locked": True, "barricaded": False}
    o = w.map[COUNTER_OUT]
    assert (o["solid"], o["solidTrans"], o["room"]) == (False, False, None)
    row = e17_replay(380)[379]
    w = threat(row)
    assert w["doorway_exit"] == {"end": "inside", "exit": "window"} and w["window"] == [10720, 10634]


def test_e17_s_kitchen_has_no_way_out_with_its_counter_window_left_out_and_the_window_without_the_counter():
    """Line 380 (frame seq 3447): of building 2's ways out every door and opening and every other window is refused by
    the held zombies, so the counter window was the one `exit_plan` answered. With P26-I it is left out (its inside
    square `solidTrans`): no way out. The same square read walkable (`solidTrans` false) answers the window; with the
    switch off (`walkable` False) the counter window too."""
    w = e17_world(380)
    assert P.exit_plan(w, held(w), windows=True) is None
    e = P.exit_plan(w, held(w), windows=True, walkable=False)
    assert (e["window"], e["inner"], e["outer"], e["smash"]) == (COUNTER, COUNTER, COUNTER_OUT, True)
    w = e17_world(380, solidTrans=False)
    e = P.exit_plan(w, held(w), windows=True)
    assert (e["window"], e["inner"], e["outer"], e["step"]) == (COUNTER, COUNTER, COUNTER_OUT, "window")


def test_a_solid_inside_square_is_left_out_too_and_the_window_record_filter_is_the_goal_layer_s():
    """A `solid` inside square (a wall object) is no way out either; `goals.usable_windows` (the window record's
    filter both callers share) still lists the counter window: the walkability read is the exits' alone."""
    from agent.base.planner import goals as G
    from agent.base.planner import night as N
    w = e17_world(380, solidTrans=False, solid=True)
    assert COUNTER not in [e["window"] for e in N.window_exits(w, 2, 0)]
    w = e17_world(380)
    assert (COUNTER, True) in G.usable_windows(w, 2, 0)
    assert COUNTER not in [e["window"] for e in N.window_exits(w, 2, 0)]
    assert COUNTER in [e["window"] for e in N.window_exits(w, 2, 0, walkable=False)]


def test_world_stood_on_is_the_one_walkability_read_of_the_window_exits():
    """Review-t7 minor 3: `World.stood_on` (`_solid` with `trans`) is the read `night.window_exits` takes: an unmapped
    square, a `solid` one and a `solidTrans` one (the counter) cannot be stood on; the outdoor square west of it can."""
    w = e17_world(380)
    assert not w.stood_on(COUNTER) and w.stood_on(COUNTER_OUT) and not w.stood_on((0, 0, 0))
    assert not e17_world(380, solidTrans=False, solid=True).stood_on(COUNTER)
    assert e17_world(380, solidTrans=False).stood_on(COUNTER)


def test_e17_s_inside_end_reads_trapped_with_the_counter_window_left_out():
    """E17 replayed to line 380 with P26-I alone on: the stand's `inside` end finds no way out and reads `trapped`
    (`doorway_exit` {end inside, exit trapped}), no walk to the counter."""
    row = e17_replay(380, WINDOW_INNER=True)[379]
    w = threat(row)
    assert w["doorway_left"] == "inside" and w["doorway_exit"] == {"end": "inside", "exit": "trapped"}
    assert w["trapped"] == 2 and "window" not in w and row["action"] is None


# ================================================ P26-J: the window step is stall-read like the walk
F5 = os.path.join(R.ARTIFACTS, "f_goals_6-20261030-192251")


def act_holds(artifact, aid):
    """The window act `aid`'s frames walked through a Flee's own stall read (`Flee._still_for`, the anchor taken at
    its accept): (the longest wall seconds the player stood within STUCK_MOVE, the seq of the first frame whose read
    reached WINDOW_STALL_S or None, the act's last state)."""
    lines, _ = R.read_record(artifact)
    acts = [ln for ln in lines if ln["kind"] == "act" and ln.get("aid") == aid]
    t0, t1 = acts[0]["wallMs"], acts[-1]["wallMs"]
    now = {"t": t0 / 1000.0}
    w = World()
    f = FL.Flee(w, None, clock=lambda: now["t"])
    anchor, longest, first = None, 0.0, None
    for ln in lines:
        w.apply(ln)
        if ln["kind"] != "frame" or not t0 <= ln["wallMs"] <= t1:
            continue
        now["t"] = ln["wallMs"] / 1000.0
        anchor = anchor or (now["t"], me_xy(w))
        anchor, still = f._still_for(anchor)
        longest = max(longest, still)
        if first is None and still >= P.WINDOW_STALL_S:
            first = ln["seq"]
    return round(longest, 3), first, acts[-1]["state"]


def test_the_window_stall_constant_lies_between_f5_s_climb_done_and_e17_s_act_that_waited_dead():
    """WINDOW_STALL_S's provenance, read through the Flee's own stall read: F5's a20, the one live window climbed `done`
    (the open, then the climb), held the player 2.497 s at most (under it: kept); E17's a81 held it 12.9 s and its read
    reached WINDOW_STALL_S at frame seq 3515 (the health 98.88993072509766 there), 9.3 s before its `dead` end. With
    WALK_STALL_S, F5's climb would have been dropped."""
    assert P.WINDOW_STALL_S == 3.0 and P.WALK_STALL_S == 1.0
    assert act_holds(F5, "a20") == (2.497, None, "done")
    assert act_holds(E17, "a81") == (12.9, 3515, "failed")
    assert 2.497 >= P.WALK_STALL_S


def climb_running(tmp_path, stall=True):
    """E16's shed (`test_survive_y`'s rig) with the player on the window's inside square: the Flee's way out sends
    `Window(10710, 10596)`, accepted and running; (r, f)."""
    r = Y.e16_rig(tmp_path, me=WIN_IN)
    f = Y.flee_on(r)
    f.window_stall_on = stall
    f.step()
    assert r.cmd() == ("window", {"x": 10710, "y": 10596})
    r.fake.answer({"window": ["accepted"]})
    r.pump()
    return r, f


def hold_for(r, f, seconds, step=0.0):
    """Frames every half second for `seconds`, the player moved `step` tiles east of the inside square's centre per
    frame (0: held), each read by the Flee's step."""
    t, x = 0.0, WIN_IN[0]
    while t < seconds:
        dt = min(0.5, seconds - t)
        r.advance(dt)
        t, x = t + dt, x + step
        r.frame(x=x, y=WIN_IN[1], zombies=Y.zs(Y.E16_469, (x, WIN_IN[1])))
        f.step()


def test_a_climb_that_holds_the_player_for_window_stall_s_is_dropped_and_its_window_refused_stalled(tmp_path):
    """The window act running, every frame on the same spot for WINDOW_STALL_S: the Flee drops it (`_dropped`), notes
    the window `stalled` (`World.note_window_fail`) and refuses its outside square; the next choose has no way out
    (the door's opening refused for the zombies on its square, the adoption spent) and stops the act still running
    (`Stop`), the trapped hold."""
    r, f = climb_running(tmp_path)
    hold_for(r, f, P.WINDOW_STALL_S - 0.5)
    assert f.exit is not None and r.world.window_fail(Y.WIN) is None
    hold_for(r, f, 0.5)
    assert r.world.window_fail(Y.WIN) == "stalled" and Y.WIN_OUT in f.refused and f.exit is None
    assert r.cmd() == ("stop", {}) and f.why["trapped"] == 1


def test_a_stalled_window_is_a_dead_end_and_the_next_exit_plan_offers_no_window(tmp_path):
    """Ruling P26-J2 (review-t7 nit 3): `stalled` is in `goals.WINDOW_DEAD`, so a window whose climb stalled is left out
    by `usable_windows` and the exits for DOOR_RETRY_MIN game minutes (`World.window_fail`), never offered again at
    once: before the stall `exit_plan` offers the shed window; after it, none; past DOOR_RETRY_MIN it is offered
    again."""
    from agent.base.planner import goals as G
    from agent.base.world import DOOR_RETRY_MIN
    assert "stalled" in G.WINDOW_DEAD
    r, f = climb_running(tmp_path)
    zs = list(r.world.zombies.values())
    assert P.exit_plan(r.world, zs, windows=True)["window"] == Y.WIN   # no refusal passed: only the mark can drop it
    hold_for(r, f, P.WINDOW_STALL_S)
    assert r.world.window_fail(Y.WIN) == "stalled"
    assert Y.WIN not in [sq for sq, _ in G.usable_windows(r.world, 1, 0)]
    assert P.exit_plan(r.world, zs, windows=True) is None
    r.world.window_marks[Y.WIN] = (r.world.world_minutes() - DOOR_RETRY_MIN, "stalled")
    assert P.exit_plan(r.world, zs, windows=True)["window"] == Y.WIN


def test_a_climb_whose_frames_move_or_hold_under_the_limit_is_kept(tmp_path):
    """The window act running while the frames move 0.3 tiles a half second (past STUCK_MOVE each second) for twice
    WINDOW_STALL_S, or hold F5's 2.497 s: kept, no failure noted, the climb's own end awaited."""
    r, f = climb_running(tmp_path)
    hold_for(r, f, 2 * P.WINDOW_STALL_S, step=0.3)
    assert f.exit is not None and r.world.window_fail(Y.WIN) is None and r.cmd()[0] == "window"
    r, f = climb_running(tmp_path / "f5")
    hold_for(r, f, 2.497)
    assert f.exit is not None and r.world.window_fail(Y.WIN) is None and r.cmd()[0] == "window"


def test_with_the_switch_off_the_climb_runs_to_its_own_end(tmp_path):
    r, f = climb_running(tmp_path, stall=False)
    hold_for(r, f, 4 * P.WINDOW_STALL_S)
    assert f.exit is not None and r.world.window_fail(Y.WIN) is None and r.cmd()[0] == "window"


def test_a_climb_interrupted_once_is_sent_again_and_refused_on_the_second(tmp_path):
    """The amendment's clause (a Lua that ends the act `interrupted` when its queue empties before the climb): the first
    `interrupted` end keeps the exit and sends `Window` once more; the second (within DOOR_RETRY_MIN, `goals.
    note_window_end` reads it `failed`) refuses it, the trapped hold. With the switch off the first refuses it."""
    r, f = climb_running(tmp_path)
    r.fake.answer({"window": [{"state": "failed", "reason": "interrupted"}]})
    r.pump()
    r.frame(x=WIN_IN[0], y=WIN_IN[1], zombies=Y.zs(Y.E16_469, WIN_IN))
    f.step()
    assert r.world.window_fail(Y.WIN) == "interrupted" and Y.WIN_OUT not in f.refused and f.exit is not None
    assert [a.type for a in r.acts.history] == ["window", "window"] and r.cmd() == ("window", {"x": 10710, "y": 10596})
    r.fake.answer({"window": ["accepted", {"state": "failed", "reason": "interrupted"}]})
    r.pump()
    r.frame(x=WIN_IN[0], y=WIN_IN[1], zombies=Y.zs(Y.E16_469, WIN_IN))
    f.step()
    assert r.world.window_fail(Y.WIN) == "failed" and Y.WIN_OUT in f.refused and f.exit is None
    assert [a.type for a in r.acts.history] == ["window", "window"] and f.why["trapped"] == 1
    r, f = climb_running(tmp_path / "off", stall=False)
    r.fake.answer({"window": [{"state": "failed", "reason": "interrupted"}]})
    r.pump()
    r.frame(x=WIN_IN[0], y=WIN_IN[1], zombies=Y.zs(Y.E16_469, WIN_IN))
    f.step()
    assert Y.WIN_OUT in f.refused and f.exit is None and [a.type for a in r.acts.history] == ["window"]


def test_e17_s_window_act_is_dropped_at_its_stall_and_the_window_noted_stalled():
    """E17 replayed with P26-J alone on: the `inside` end's walk and a81 go as the record sent them, and the record's
    lines hold a81 to line 392 (each `holding` it); line 393 is the first tick whose read of the act's hold reaches
    WINDOW_STALL_S (the player on (10721.51, 10634.64) since frame seq 3482): a81 is dropped, the counter window noted
    `stalled` in the World, the way out refused, and the threat branch answers the `inside` corner at 2403 (no swing
    under its `Bite`) where the record held a81 on; the next send (line 394's, the trapped hold's bandage under P25-Q)
    supersedes the act, which ran on live 9.3 s more to its `dead` end."""
    kept = {}

    def mutate(sv):
        kept["sv"] = sv
        for name in S.T8_SWITCHES:
            setattr(sv, name, name == "WINDOW_STALL")
    rows = R.replay(E17, mutate=mutate, upto=394)
    _, rec, _ = e17()
    sent = [(k, row["action"]["type"]) for k, row in enumerate(rows, 1) if k >= 380 and row["sent"]]
    assert sent == [(380, "walkTo"), (383, "window"), (394, "bandage")]
    assert all(threat(rows[k - 1]).get("holding") == "a81" for k in range(384, STALL_LINE))
    assert "holding" not in threat(rows[STALL_LINE - 1]) and threat(rec[STALL_LINE - 1])["holding"] == "a81"
    assert threat(rows[STALL_LINE - 1])["cornered"] == 2403
    assert kept["sv"].world.window_marks[COUNTER][1] == "stalled"


# ================================================ P26-K: the stand leaves before the room fills
ZOMBIE_FIELDS = ("x", "y", "dist", "hasTarget", "crawler", "health", "onFloor")
LINE_370_NEAREST = (2408, 2444, 2417, 2403, 2400, 2401)   # line 370's six within DANGER_R, nearest first; 2416 beyond


def e17_stand(tmp_path, line, keep=None, crowd=True, place=None, fallen=(), bleed=None):
    """A Survive on a Rig holding E17's map as decision line `line` read it, its doorway stand on building 2's kitchen
    door running as the record's ran from line 362 (the plan `night.shelter_plan` kept to the door, marked a stand as
    `Flee.choose` marks one, `stood` at `stand` as `Flee._stand_at_post` leaves it), then line `line`'s frame (the
    player, `me.attackers`, the zombies the World held then, only those of ids `keep` when given, those of `place`
    ({id: (x, y)}) moved there, those of `fallen` lying `onFloor`) ticked with `STAND_CROWD` as given; with `bleed` (a
    part index) that part bleeding on the frame though the stand's start snapshot (`bleed0`) held none: (r, sv, the
    threat why)."""
    from agent.base.planner import night as N
    from .test_survive import make, threat_why, tick
    from .test_survive_g import part
    w = e17_world(line)
    r, sv = make(tmp_path)
    sv.STAND_CROWD = crowd
    r.scan([dict(s) for s in w.map.values()])
    rows = [dict({k: z.get(k) for k in ZOMBIE_FIELDS}, id=zid) for zid, z in w.zombies.items()
            if keep is None or zid in keep]
    for row in rows:
        if row["id"] in (place or {}):
            row["x"], row["y"] = place[row["id"]]
        if row["id"] in fallen:
            row["onFloor"] = True
    me = w.me
    wounds = None if bleed is None else {"parts": [part(bleed, bleeding=True, bleedingTime=3.0)], "bleeding": 1}
    r.frame(x=me["x"], y=me["y"], zombies=rows, attackers=me["attackers"], wounds=wounds)
    f = FL.Flee(r.world, r.acts, r.clock, shunned=sv.night.shunned)
    plan = N.shelter_plan(r.world, 2, door=KITCHEN_DOOR)
    way = r.world.door_way(KITCHEN_DOOR)
    plan.update(stand=True, way=way, post=P.stand_post(r.world, way, 2, True), step="stand", stood=True,
                quiet=r.clock())
    if bleed is not None:
        plan["bleed0"] = frozenset()
    f.plan, f.picked = plan, True
    sv.flee = f
    tick(r, sv)
    return r, sv, threat_why(tmp_path)


def test_the_stand_crowd_constant_and_its_end_among_the_ends_that_walk_out():
    from agent.base.planner import doorway as D
    assert S.T8_SWITCHES == ("WINDOW_INNER", "WINDOW_STALL", "STAND_CROWD") and P.STAND_CROWD_N == 4
    assert "crowd" in D.STAND_EXIT_ENDS


def test_line_370_s_six_within_danger_r_none_inside_and_the_record_s_stand_held():
    """The reading the rule rests on: at line 370 six zombies stood within DANGER_R of the stand (2416 beyond it), none
    on the kitchen's squares, and the record's stand held (no end) until line 380's `inside`."""
    w = e17_world(370)
    near = sorted((P.zdist(w, z), zid) for zid, z in w.zombies.items() if P.zdist(w, z) <= P.DANGER_R)
    assert tuple(zid for _, zid in near) == LINE_370_NEAREST
    assert all(w.map.get((int(z["x"]), int(z["y"]), 0), {}).get("room") is None for z in w.zombies.values())
    _, rec, _ = e17()
    assert all("doorway_left" not in threat(rec[k - 1]) for k in range(362, 380))


def test_e17_s_stand_with_four_held_all_outside_ends_crowd_and_takes_the_close(tmp_path):
    """Ruling P26-K2. Line 370's geometry with its four nearest (2408, 2444, 2417, 2403, all within DANGER_R) and 2416
    beyond it, every one outside the kitchen and off its door square: the stand ends `crowd` (`doorway_left` crowd,
    `doorway_crowd` {n 4}) and takes the close, the stand's own re-close of the door with the plan kept on its close
    step (`doorway_exit` {end crowd, exit close}), never the way out."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:4] + (2416,))
    assert w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 4}
    assert w["doorway_exit"] == {"end": "crowd", "exit": "close"} and w["flee"] == "doorway"
    assert sv.flee.plan is not None and sv.flee.plan["step"] == "close" and sv.flee.plan["left"] == "crowd"
    assert sv.flee.walking_out is None and sv.stand_left is None
    assert r.cmd() == ("interact", {"kind": "close", "x": 10721, "y": 10638, "filter": "all", "maxWeight": 0.0})


def test_a_crowd_end_with_a_zombie_on_a_room_square_takes_the_way_out(tmp_path):
    """Ruling P26-K2, the mutant's case (E16's line 469 geometry is the other: `test_e16_s_stand_on_line_469...`): the
    same four with 2408 on the kitchen square (10721, 10636), beside the post: the end is `crowd` and the walk-out
    (`Flee.walk_out`: the plan dropped, the adoption spent), the exit the choose took or `trapped`, never `close`."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:4] + (2416,), place={2408: (10721.5, 10636.5)})
    assert w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 4} and "doorway_inside" not in w
    assert w["doorway_exit"]["end"] == "crowd" and w["doorway_exit"]["exit"] in ("door", "opening", "window", "trapped")
    assert sv.flee.plan is None and sv.flee.adopted and sv.stand_left == "crowd" and sv.stand_exit == "crowd"


def test_a_crowd_end_with_a_zombie_on_the_door_square_takes_the_way_out(tmp_path):
    """Ruling P26-K2: 2408 on the stand's door square (10721, 10638) itself: not a close, the walk-out."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:4] + (2416,), place={2408: (10721.5, 10638.5)})
    assert w["doorway_left"] == "crowd" and w["doorway_exit"]["exit"] != "close"
    assert sv.flee.plan is None and sv.stand_left == "crowd"


def test_a_wounded_stand_with_four_held_outside_ends_wound_not_crowd_and_walks_out(tmp_path):
    """Review-t7 minor 2: `crowd` is read after `wound`. Line 370's four nearest, all outside (the case that takes the
    close under P26-K2), with part 4 newly bleeding (absent from the stand's start snapshot): the end is `wound`
    (P25-W: a bleeding stand never shuts the door on the character), the walk-out, never `crowd`'s close; no
    `doorway_crowd` is logged. The mutant swapping the two entries of `_stand_end` reads `crowd` and fails it."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:4] + (2416,), bleed=4)
    assert w["doorway_left"] == "wound" and "doorway_crowd" not in w
    assert w["doorway_exit"]["end"] == "wound" and w["doorway_exit"]["exit"] != "close"
    assert sv.flee.plan is None and sv.stand_left == "wound" and sv.stand_exit == "wound"
    assert not [a for a in r.acts.history if a.type == "interact" and a.args["kind"] == "close"]


def test_a_crowd_counts_standing_zombies_only(tmp_path):
    """Ruling P26-K2: two standing and two fallen (`onFloor`) held within DANGER_R do not end the stand (the finish
    rule stomps the fallen); four standing do."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:4] + (2416,), fallen=(2417, 2403))
    assert "doorway_left" not in w and "doorway_crowd" not in w and w["doorway"] == 2
    assert sv.flee.plan["step"] == "stand"
    d = tmp_path / "four"
    d.mkdir()
    r, sv, w = e17_stand(d, 370, keep=LINE_370_NEAREST[:4] + (2416,), fallen=(2416,))
    assert w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 4}


def test_e17_s_stand_with_three_held_holds(tmp_path):
    """The same line with its three nearest within DANGER_R: no end, the stand's Doorway answers."""
    r, sv, w = e17_stand(tmp_path, 370, keep=LINE_370_NEAREST[:3] + (2416,))
    assert "doorway_left" not in w and "doorway_crowd" not in w and w["doorway"] == 2
    assert sv.flee.plan["step"] == "stand"


def test_with_the_switch_off_six_held_leave_the_stand_standing(tmp_path):
    r, sv, w = e17_stand(tmp_path, 370, crowd=False)
    assert "doorway_left" not in w and w["doorway"] == 2
    d = tmp_path / "on"
    d.mkdir()
    r, sv, w = e17_stand(d, 370)
    assert w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 6}


def test_e17_replayed_on_iteration_18_ends_its_stand_crowd_at_line_364():
    """E17 replayed with iteration 18 on: the stand began at line 362 as the record's (two held within DANGER_R), and
    ends `crowd` at line 364, the first of its lines to read four within DANGER_R, 16 lines before the record's
    `inside` end at 380; no zombie is on the kitchen or its door square there (seven held, all outside), so under ruling
    P26-K2 the end takes the close: the interact `close` at the door (10721, 10638) is sent and `doorway_exit` reads
    {crowd, close} (iteration 18's first reading ended it `trapped`; the replay is open loop from here: its next lines
    are counterfactual)."""
    rows = e17_replay(364, WINDOW_INNER=True, WINDOW_STALL=True, STAND_CROWD=True)
    _, rec, _ = e17()
    assert threat(rows[361])["leg"] == "stand" and rows[361]["inputs"]["threats"] == 2
    assert "doorway_left" not in threat(rows[362]) and rows[362]["inputs"]["threats"] == 3
    w = threat(rows[363])
    assert rows[363]["inputs"]["threats"] == 4 and w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 4}
    assert w["doorway_exit"] == {"end": "crowd", "exit": "close"} and "trapped" not in w and w["step"] == "close"
    assert rows[363]["sent"] and rows[363]["action"]["type"] == "interact"
    assert rows[363]["action"]["args"] == {"filter": "all", "kind": "close", "maxWeight": 0.0, "x": 10721, "y": 10638}
    assert threat(rec[363])["leg"] == "stand"


def test_e16_s_stand_on_line_469_ends_crowd_ahead_of_inside_and_walks_out_by_the_window(tmp_path):
    """E16's stand on the shed (`test_survive_y.stand_on_shed`) at line 469, five within DANGER_R (24164 and 24134 on
    the door's inside square): with P26-K the end is `crowd` {n 5}, read before `inside`, and it walks out by the
    window as the `inside` end did (P26-A)."""
    r, sv, w = Y.stand_on_shed(tmp_path, crowd=True)
    assert w["doorway_left"] == "crowd" and w["doorway_crowd"] == {"n": 5} and "doorway_inside" not in w
    assert w["doorway_exit"] == {"end": "crowd", "exit": "window"} and sv.flee.walking_out == "crowd"
    assert r.cmd() == ("walkTo", {"x": 10710.5, "y": 10596.5, "gait": "run"})
