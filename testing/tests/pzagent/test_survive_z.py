"""Survival 20 (survival iteration 18; Plan 26 Task 7; E17, `e_day_17-20261102-180459`, rows pending its write-up's
mint). E17's own record, read as the planner read it (`replay_decisions.read_record` and `align`: the World through a
decision line's frame and the trailing lines its tick read), and replayed (`replay_decisions.replay`: HEAD's planner
is the one E17 ran on, `6df43e92`, so with iteration 18's switches off the replay is the record's own rules). The
stand held building 2's kitchen door (10721, 10638) from line 362; its `inside` end at line 380 (frame seq 3447)
walked out by the kitchen window (10720, 10634), a `solidTrans` square holding a `counter`, where the window act a81
waited 14.3 s and failed `dead`.

- P26-I, a window way out needs a walkable inside square (`WINDOW_INNER`): `night.window_exits` leaves out a window
  whose inside square reads `solid` or `solidTrans`; its outside square is never solid (`World.window_way`).
"""
import functools
import os

from agent.base import replay_decisions as R
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.world import World

E17 = os.path.join(R.ARTIFACTS, "e_day_17-20261102-180459")
COUNTER = (10720, 10634, 0)       # the kitchen window's square: its record on its own west edge, a `counter` on it
COUNTER_OUT = (10719, 10634, 0)   # the outdoor square west of it, the climb's landing
KITCHEN_DOOR = (10721, 10638, 0)  # the stand's door, kept on the outdoor square's north edge


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
