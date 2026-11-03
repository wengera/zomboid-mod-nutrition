"""Survival 20 (survival iteration 18; Plan 26 Task 7; E17, `e_day_17-20261102-180459`, rows pending its write-up's
mint). E17's own record, read as the planner read it (`replay_decisions.read_record` and `align`: the World through a
decision line's frame and the trailing lines its tick read), and replayed (`replay_decisions.replay`: HEAD's planner
is the one E17 ran on, `6df43e92`, so with iteration 18's switches off the replay is the record's own rules). The
stand held building 2's kitchen door (10721, 10638) from line 362; its `inside` end at line 380 (frame seq 3447)
walked out by the kitchen window (10720, 10634), a `solidTrans` square holding a `counter`, where the window act a81
waited 14.3 s and failed `dead`.

- P26-I, a window way out needs a walkable inside square (`WINDOW_INNER`): `night.window_exits` leaves out a window
  whose inside square reads `solid` or `solidTrans`; its outside square is never solid (`World.window_way`).
- P26-J, the window step is stall-read like the walk (`WINDOW_STALL`): the window act holding the player within
  STUCK_MOVE for WINDOW_STALL_S is dropped and its exit refused `stalled`; a first `interrupted` end is sent once more,
  the second refused (the E17 write-up's amendment).
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
