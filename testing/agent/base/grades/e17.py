"""grades.e17 -- the chain sessions' grade, pass 17 (Plan 27 Task 6): `grade_e17` is `grades.e16.grade_e16` under
"grade_e17" with the nine readings of survival iteration 20 (Plan 27 Task 5, `T10_SWITCHES` and P27-L), each read off
the decision log's why fields, the artifact's actions and the state log's act lines, events and frames:

  stuck_leave        P27-F, the stuck walk's mark and the leave (`STUCK_LEAVE`): the `stuck_mark` lines by goal, the
                     `leave` picks by way, the rests proposed on a marked square, the game minutes spent on one.
  floor_finish       P27-G, the swing at a fallen zombie in reach (`FLOOR_FINISH`): the swings sent, landed, their
                     kills, the `strike_runs` holds and the stomps after a swing at the same zombie.
  fallen_seek        P27-H, the fallen target out of reach (`FALLEN_SEEK`): the walks to it, the ones left, the ticks.
  listing            P27-I, the listing's left-out zombies (`LISTING_FALLEN`): the fallen and across counts, the
                     `many` episodes the clause kept from starting.
  shove_close        P27-J, the shove-only fight's close and the hold's idle zombie (`SHOVE_CLOSE`): the walks to
                     point blank, the shoves after, the ones left, the rests at an idle zombie.
  stock_early        P27-K1, the rag stock ahead of the bleed (`STOCK_EARLY`): the early rips by branch, the care
                     yield's, the dressings after.
  low_exit           P27-K2, the low fight's exit and the inside corner's yield (`LOW_EXIT`): the exits, the yields,
                     the health flee after them and the bites after them.
  spent_held         P27-K3, the replace held under a chaser (`REPLACE_QUIET`): the holds, the replaces after them,
                     the holds on a bleeding part.
  wounded_swing_off  P27-L, P26-L1's divided swing withdrawn (`WOUNDED_SWING` off by default): the divided swings that
                     went (must read 0 with the default) and P25-L's breaks.

Each reading is {"read": False} without a decision log. A key marked reading counts what the log or the artifact
states; one marked inference reads an effect off the frames, the events or the order of lines. Every live planner name
the readings read is copied below as a frozen constant with its source and its value at b6ebd954 (ruling P26-Q,
`grades/__init__.py`): this module imports nothing from `agent.base.planner` or `agent.base.world`; the chain it
imports (`grades.e16.grade_e16`, which reads live names through `e15`, `e14` and `gates_e`) is pinned by the regrade
tests of the artifacts graded through it. Frozen once an artifact carries its output; `gates_e`, `grades/e14.py`,
`grades/e15.py`, `grades/e16.py` and every driver stay untouched."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e16 as G16

# Frozen copies of the live planner names read here (P26-Q), each as it stood at b6ebd954 (Plan 27 Task 5's head).
DANGER_R = 6.0                 # planner/policies.py:74: tiles, a zombie this close is a threat
LISTED_R = 12.0                # planner/policies.py:123: tiles, the listing's edge
FLEE_HEALTH_FLOOR = 20.0       # planner/policies.py:199: the health under which the inside corner yields (P27-K2)
MANY_LISTED_N = 4              # planner/policies.py:212: zombies listed within LISTED_R that make `many`
SHOVE_FAIL_N = 3               # planner/policies.py:268: missed shoves at a lone target before the low fight's exit
STUCK_MARK_MIN = 30.0          # planner/policies.py:293: game minutes a stuck walk's square stays marked
STUCK_LEAVE_R = 10.0           # planner/policies.py:297: tiles from a marked square the walk away from its edge goes
FALLEN_SEEK_TICKS = 4          # planner/policies.py:300: ticks a fallen target out of reach reads before its walk
SHOVE_CLOSE_TICKS = 6          # planner/policies.py:304: ticks a shove-only fight's chaser holds before its walk
RAG_STOCK = 2                  # planner/care.py:157: clean dressings the care keeps (the early rip's ceiling)
REST_GOAL = "Rest"             # planner/goal_policies.py: Rest.TYPE, the goal the scripted source answers idle
LOOT_GOAL = "LootBuilding"     # planner/goal_policies.py: LootBuilding.TYPE, a `leave` way
EXPLORE_GOAL = "ExploreToward"  # planner/goal_policies.py: ExploreToward.TYPE, the walk back or the walk away

FOLLOW_LINES = 20              # log lines: a send's follow-up (a stomp, a shove, a kill, a flee) is read this far on
                               # (ten seconds at the drivers' PLANNER_HZ 2, e16's TAIL_AFTER_LINES)
SWING_WINDOW_S = 2.0           # wall seconds: a swing event is read from a send to its end, else this long after it
BITE_AFTER_S = 10.0            # wall seconds: a bite is read after an exit or a yield this long
WAYS = ("walk", "loot", "explore")
NEW = ("stuck_leave", "floor_finish", "fallen_seek", "listing", "shove_close", "stock_early", "low_exit",
       "spent_held", "wounded_swing_off")


def _gw(ln):
    """The goal branch's why of a decision-log line (`inputs.branches.goal`: the runner's why)."""
    return E._bw(ln, "goal")


def _line_square(ln):
    """(x, y) of the line's `inputs.x`, `inputs.y` floored (the planner's own position read), else None."""
    inp = E._d(ln.get("inputs"))
    x, y = E._n(inp.get("x")), E._n(inp.get("y"))
    return None if x is None or y is None else (int(math.floor(x)), int(math.floor(y)))


def _frame_min(f):
    """The frame's game minute on `World.world_minutes`' clock (e16's `_world_min` base): `worldAge * 60` rounded
    1e-6, else its gameMin; None without either."""
    a = E._n(E._d(f).get("worldAge"))
    if a is not None:
        return round(a * 60.0, 6)
    return E._n(E._d(f).get("gameMin"))


def _line_min(L, ln):
    """The game minute at the line: the frame's beside it (`_frame_min`), else the line's own gameMin."""
    f = L.frame(ln)
    m = _frame_min(f) if f is not None else None
    return m if m is not None else E._n(ln.get("gameMin"))


def _target(ln):
    return E._d(E._d(ln.get("action")).get("args")).get("targetId")


def _after(rows, i, test):
    """Whether a line from `i` + 1 to `i` + FOLLOW_LINES passes `test`."""
    return any(test(rows[j]) for j in range(i + 1, min(len(rows), i + 1 + FOLLOW_LINES)))


# ---------------------------------------------------------------- P27-F
def _marks(L):
    """[(line index, (x, y), edge or None, goal type, game minute)] of the lines whose goal why carries `stuck_mark`
    {edge, square, goal} (`GoalRunner._read_walks`, logged on the tick the walk's end marked its square)."""
    out = []
    for i, ln in enumerate(L.rows):
        m = _gw(ln).get("stuck_mark")
        if not isinstance(m, dict):
            continue
        sq = E._l(m.get("square"))
        if len(sq) < 2 or E._n(sq[0]) is None or E._n(sq[1]) is None:
            continue
        out.append((i, (int(sq[0]), int(sq[1])), m.get("edge"), E._d(m.get("goal")).get("type"), _line_min(L, ln)))
    return out


def _away(mark):
    """The two targets of P27-F's walk away from mark's edge (`ScriptedSource._ways_out`'s last way: STUCK_LEAVE_R
    tiles from the square along the edge's axis); () without an edge."""
    _, (x, y), edge, _, _ = mark
    e = E._l(edge)
    if len(e) < 3:
        return ()
    r = int(STUCK_LEAVE_R)
    return ((x, y - r), (x, y + r)) if e[2] == "N" else ((x - r, y), (x + r, y))


def _way(leave, mark):
    """A `leave` pick's way: "loot" for a LootBuilding, "explore" for an ExploreToward at one of the last mark's
    `_away` targets (an inference off the targets), "walk" for any other ExploreToward (the walk back to a building on
    the square's side of the edge, the brief's cluster walk)."""
    t = E._d(E._d(leave).get("target"))
    if t.get("type") == LOOT_GOAL:
        return "loot"
    a = E._d(t.get("args"))
    to = (E._n(a.get("x")), E._n(a.get("y")))
    if t.get("type") == EXPLORE_GOAL and mark is not None and to in _away(mark):
        return "explore"
    return "walk"


def _live(marks, sq, m, upto=None):
    """Whether square `sq` carries a mark logged at or before line `upto` (any line when None) whose game minute is
    within STUCK_MARK_MIN of `m` and not after it (`GoalRunner.stuck_at`'s window)."""
    return any(s == sq and t is not None and m is not None and t <= m < t + STUCK_MARK_MIN
               and (upto is None or i <= upto) for i, s, _, _, t in marks)


def _marked_minutes(L, marks):
    """Game minutes the frames put the player on a live marked square (an inference): each adjacent pair of frames
    whose first reads a marked square within STUCK_MARK_MIN of its mark adds its game minutes (`G16._world_min`)."""
    if not marks:
        return 0.0
    squares = {s for _, s, _, _, _ in marks}
    _, frames = L.index
    total = 0.0
    for f0, f1 in zip(frames, frames[1:]):
        sq = G16._square(f0)
        if sq is None or sq[:2] not in squares or not _live(marks, sq[:2], _frame_min(f0)):
            continue
        dm = G16._world_min(f0, f1)
        total += dm if dm is not None and dm > 0 else 0.0
    return total


def e_stuck_leave(L):
    """The stuck walk's mark and the leave (P27-F, `Survive.STUCK_LEAVE`): {read, marks, edged, leaves,
    rests_on_marked, minutes_on_marked_square}. Reading: `marks` the lines whose goal why carries `stuck_mark` by the
    marked walk's goal type, `edged` those naming a first edge, `leaves` the goal lines whose why carries `leave`
    {why "stuck", target} (`ScriptedSource.last_leave`, logged on the pick) by way (`_way`: "loot", "walk" the walk back
    to a building, "explore" the walk away from the edge, told apart by its target: an inference). Inference off the
    line's position and the frames: `rests_on_marked` the goal lines proposing a Rest with the line's square
    (`inputs.x`, `inputs.y`) marked within STUCK_MARK_MIN game minutes before (must read 0: the source leaves there),
    `minutes_on_marked_square` the game minutes the frames stood on a live mark (`_marked_minutes`)."""
    if L is None:
        return {"read": False}
    marks = _marks(L)
    by, ways, rests = {}, {w: 0 for w in WAYS}, 0
    for _, _, _, goal, _ in marks:
        G14._inc(by, str(goal))
    for i, ln in enumerate(L.rows):
        gw = _gw(ln)
        if isinstance(gw.get("leave"), dict):
            last = next((m for m in reversed(marks) if m[0] <= i), None)
            ways[_way(gw["leave"], last)] += 1
        if gw.get("proposed") == REST_GOAL and _live(marks, _line_square(ln), _line_min(L, ln), upto=i):
            rests += 1
    return {"read": True, "marks": by, "edged": sum(1 for m in marks if m[2]), "leaves": ways,
            "rests_on_marked": rests, "minutes_on_marked_square": _marked_minutes(L, marks)}


# ---------------------------------------------------------------- P27-G
def _swung(L, ln, row, acts, swings):
    """Whether a `swing` event (`attackStarted` true) sits in the state log from the line's send to the action's end
    (`G14._end_ms`, else SWING_WINDOW_S after the send): the swing went (an inference off the events)."""
    w = (E._n(ln.get("wall")) or 0.0) * 1000.0
    end = G14._end_ms(L, row, acts) if row is not None else None
    hi = end if end is not None else w + SWING_WINDOW_S * 1000.0
    i = bisect.bisect_left(swings, w)
    return i < len(swings) and swings[i] <= hi


def _swing_walls(lines):
    return sorted(E._n(ln.get("wallMs")) for ln in E._l(lines)
                  if isinstance(ln, dict) and ln.get("kind") == "event" and ln.get("event") == "swing"
                  and ln.get("attackStarted") is True and E._n(ln.get("wallMs")) is not None)


def e_floor_finish(L, lines):
    """The swing at a fallen zombie in reach (P27-G, `Threat.FLOOR_FINISH`): {read, lines, sent, landed, kills,
    strike_holds, stomps_after}. Reading: `lines` the threat lines whose why carries `floor_finish` {target, health}
    (`finish.FightFinish._floor_finish` and the flee's `ThreatFinish._flee_finish`, kind `floor_finish`), `sent` those
    that sent the `attack`, `kills` the zombies their results read dead, `strike_holds` the threat lines whose why
    carries `strike_runs` {target, aid} (the finish held while a strike at its zombie runs). Inference off the events
    and the order of lines: `landed` the sends with a `swing` event in their act (`_swung`), `stomps_after` the sends
    followed within FOLLOW_LINES by a stomp sent at the same zombie."""
    if L is None:
        return {"read": False}
    acts, swings, rows = G14._acts(lines, "attack"), _swing_walls(lines), L.rows
    n = holds = landed = after = 0
    sent = []
    for i, ln in enumerate(rows):
        if ln.get("branch") != "threat":
            continue
        w = L.why(ln)
        holds += 1 if isinstance(w.get("strike_runs"), dict) else 0
        if not isinstance(w.get("floor_finish"), dict):
            continue
        n += 1
        if not E._sent(ln, "attack"):
            continue
        sent.append(ln)
        landed += 1 if _swung(L, ln, L.action(ln), acts, swings) else 0
        zid = _target(ln)
        after += 1 if _after(rows, i, lambda r: E._sent(r, "stomp") and _target(r) == zid) else 0
    return {"read": True, "lines": n, "sent": len(sent), "landed": landed, "kills": len(L.kill_ids(sent)),
            "strike_holds": holds, "stomps_after": after}


# ---------------------------------------------------------------- P27-H
def e_fallen_seek(L):
    """The fallen target out of reach (P27-H, `Threat.FALLEN_SEEK`): {read, lines, walks, left, ticks, short,
    kills_after}. Reading: `lines` the threat lines whose why carries `fallen_seek` {target, dist, ticks}
    (`finish.FightFinish._fallen_seek`), `walks` those not `left` that sent the `walkTo`, `left` those reading `left`
    true (the stance ended on it), `ticks` the lines by their `ticks` and `short` those under FALLEN_SEEK_TICKS (must
    read 0). Inference off the order of lines: `kills_after` the walks' targets killed by a send within FOLLOW_LINES
    after the walk."""
    if L is None:
        return {"read": False}
    rows = L.rows
    n = walks = left = short = 0
    ticks, killed = {}, []
    for i, ln in enumerate(rows):
        fs = L.why(ln).get("fallen_seek") if ln.get("branch") == "threat" else None
        if not isinstance(fs, dict):
            continue
        n += 1
        t = E._n(fs.get("ticks"))
        G14._inc(ticks, str(int(t)) if t is not None else "None")
        short += 1 if t is not None and t < FALLEN_SEEK_TICKS else 0
        if fs.get("left") is True:
            left += 1
            continue
        if not E._sent(ln, "walkTo"):
            continue
        walks += 1
        zid = fs.get("target")
        if zid not in killed and _after(rows, i, lambda r: L.killed(r) == zid):
            killed.append(zid)
    return {"read": True, "lines": n, "walks": walks, "left": left, "ticks": ticks, "short": short,
            "kills_after": len(killed)}


# ---------------------------------------------------------------- P27-I
def _listed_p24(f):
    """The frame's zombies within LISTED_R that P24-AN's listing counts (`Threat._counts_listed_p24`: within DANGER_R
    or chasing), the distance off the player's position, else the frame's `dist`."""
    me = E._d(E._d(f).get("me"))
    mx, my = E._n(me.get("x")), E._n(me.get("y"))
    n = 0
    for z in E._l(E._d(f).get("zombies")):
        z = E._d(z)
        zx, zy = E._n(z.get("x")), E._n(z.get("y"))
        d = math.hypot(zx - mx, zy - my) if None not in (zx, zy, mx, my) else E._n(z.get("dist"))
        if d is not None and d <= LISTED_R and (d <= DANGER_R or z.get("hasTarget") is True):
            n += 1
    return n


def e_listing(L):
    """The listing's left-out zombies (P27-I, `Threat.LISTING_FALLEN`): {read, lines, fallen, across, many_avoided}.
    Reading: `lines` the threat whys carrying `listing` {fallen, across} (`Threat._listing_out`, whatever branch
    answered), `fallen` and `across` their counts summed. Inference off the frames: `many_avoided` the lines not fleeing
    `many` whose frame lists MANY_LISTED_N or more by P24-AN's count (`_listed_p24`) and fewer once the line's left-out
    zombies are taken away (the planner's own counts; an over-read where one it left out was counted by P24-AD's held
    reading alone)."""
    if L is None:
        return {"read": False}
    n = fallen = across = avoided = 0
    for ln in L.rows:
        w = L.why(ln)
        lo = w.get("listing")
        if not isinstance(lo, dict):
            continue
        n += 1
        fa, ac = E._n(lo.get("fallen")) or 0, E._n(lo.get("across")) or 0
        k, fallen, across = fa + ac, fallen + fa, across + ac
        f = L.frame(ln)
        before = _listed_p24(f) if f is not None else 0
        avoided += 1 if w.get("flee") != "many" and before >= MANY_LISTED_N > before - k else 0
    return {"read": True, "lines": n, "fallen": fallen, "across": across, "many_avoided": avoided}


# ---------------------------------------------------------------- P27-J
def e_shove_close(L):
    """The shove-only fight's close and the hold's idle zombie (P27-J, `Threat.SHOVE_CLOSE`): {read, lines, walks,
    left, short, idle_rests, shoves_after}. Reading: `lines` the threat lines whose why carries `shove_close` {target,
    dist, ticks} (`shove.FightShove._shove_close`), `walks` those not `left` that sent the `walkTo`, `left` those
    reading `left` true (the chaser's line read blocked), `short` those whose `ticks` read under SHOVE_CLOSE_TICKS
    (must read 0), `idle_rests` the lines whose threat why `rest` carries `idle` (`Threat._rest` at an idle zombie
    within DANGER_R, P27-J (a)). Inference off the order of lines: `shoves_after` the walks followed within
    FOLLOW_LINES by a shove sent at the same zombie."""
    if L is None:
        return {"read": False}
    rows = L.rows
    n = walks = left = short = idle = after = 0
    for i, ln in enumerate(rows):
        w = L.why(ln)
        idle += 1 if isinstance(w.get("rest"), dict) and "idle" in w["rest"] else 0
        sc = w.get("shove_close") if ln.get("branch") == "threat" else None
        if not isinstance(sc, dict):
            continue
        n += 1
        t = E._n(sc.get("ticks"))
        short += 1 if t is not None and t < SHOVE_CLOSE_TICKS else 0
        if sc.get("left") is True:
            left += 1
            continue
        if not E._sent(ln, "walkTo"):
            continue
        walks += 1
        zid = sc.get("target")
        after += 1 if _after(rows, i, lambda r: E._sent(r, "shove") and _target(r) == zid) else 0
    return {"read": True, "lines": n, "walks": walks, "left": left, "short": short, "idle_rests": idle,
            "shoves_after": after}


# ---------------------------------------------------------------- P27-K1
def _stock_early(ln):
    """The line's `stock_early` {rags, bandages, branch}: under the care why's `stock` (the stock step's, branch
    "stock" or "goal"), else on the care why itself (the care yield's, branch "yield"); else None."""
    c = E._bw(ln, "care")
    s = E._d(c.get("stock")).get("stock_early")
    s = s if isinstance(s, dict) else c.get("stock_early")
    return s if isinstance(s, dict) else None


def _held_clean(ln):
    """The clean dressings (`rag` + `bandage`) the line's care why `held` reads, else None."""
    h = E._bw(ln, "care").get("held")
    if not isinstance(h, dict):
        return None
    return (E._n(h.get("rag")) or 0) + (E._n(h.get("bandage")) or 0)


def e_stock_early(L, lines):
    """The rag stock ahead of the bleed (P27-K1, `Survive.STOCK_EARLY`): {read, lines, rips, yields, full,
    rags_after}. Reading: `lines` the lines carrying `stock_early` (`_stock_early`), `rips` those that sent the `rip`
    by the why's `branch`, `yields` the care yield's ("yield", the wound's rip the bleed's room takes), `full` the rips
    whose `rags` + `bandages` read RAG_STOCK or more (must read 0: the stock's ceiling). Inference off the order of
    lines: `rags_after` the rips after whose end (the rip's terminal act line, else its row's endedS) the first care
    `held` read counts more clean dressings than the rip's why (the rip landed a rag)."""
    if L is None:
        return {"read": False}
    acts, rows = G14._acts(lines, "rip"), L.rows
    n = full = after = 0
    by = {}
    for i, ln in enumerate(rows):
        s = _stock_early(ln)
        if s is None:
            continue
        n += 1
        if not E._sent(ln, "rip"):
            continue
        G14._inc(by, str(s.get("branch")))
        had = (E._n(s.get("rags")) or 0) + (E._n(s.get("bandages")) or 0)
        full += 1 if had >= RAG_STOCK else 0
        row = L.action(ln)
        end = G14._end_ms(L, row, acts) if row is not None else None
        if end is None:
            continue
        nxt = next((h for h in (_held_clean(r) for r in rows[i + 1:] if (E._n(r.get("wall")) or 0.0) * 1000.0 >= end)
                    if h is not None), None)
        after += 1 if nxt is not None and nxt > had else 0
    return {"read": True, "lines": n, "rips": by, "yields": by.get("yield", 0), "full": full, "rags_after": after}


# ---------------------------------------------------------------- P27-K2
def _bites(f):
    return E._n(E._d(E._d(f).get("body")).get("bitten")) or 0


def _bitten_after(L, ln):
    """Whether a frame within BITE_AFTER_S after the line reads more parts bitten than the frame at it (an
    inference)."""
    f0 = L.frame(ln)
    if f0 is None:
        return False
    w = (E._n(ln.get("wall")) or 0.0) * 1000.0
    walls, frames = L.index
    lo, hi = bisect.bisect_right(walls, w), bisect.bisect_right(walls, w + BITE_AFTER_S * 1000.0)
    b0 = _bites(f0)
    return any(_bites(f) > b0 for f in frames[lo:hi])


def e_low_exit(L):
    """The low fight's exit and the inside corner's yield (P27-K2, `Threat.LOW_EXIT`): {read, exits, short,
    corner_yields, above_floor, flee_after, bites_after}. Reading: `exits` the threat lines whose why carries
    `low_exit` {target, missed} (`shove.FightShove._low_exit`, the Fight sending nothing), `short` those whose `missed`
    reads under SHOVE_FAIL_N (must read 0), `corner_yields` the lines whose threat why `corner` reads {yield "health"}
    (`Threat._corner_exit`), `above_floor` those whose health (`gates_e._line_health`) reads FLEE_HEALTH_FLOOR or more
    (must read 0). Inference off the order of lines and the frames, over the exits and the yields: `flee_after` those
    on whose line or within FOLLOW_LINES after it the threat why flees `health`, `bites_after` those after which a frame
    within BITE_AFTER_S reads a new bite (`_bitten_after`)."""
    if L is None:
        return {"read": False}
    rows = L.rows
    exits = short = yields = above = flee = bites = 0
    health = lambda r: L.why(r).get("flee") == "health"     # noqa: E731
    for i, ln in enumerate(rows):
        w = L.why(ln)
        le = w.get("low_exit") if ln.get("branch") == "threat" else None
        c = w.get("corner")
        cy = isinstance(c, dict) and c.get("yield") == "health"
        if isinstance(le, dict):
            exits += 1
            m = E._n(le.get("missed"))
            short += 1 if m is not None and m < SHOVE_FAIL_N else 0
        elif not cy:
            continue
        if cy:
            yields += 1
            h = E._line_health(L, ln)
            above += 1 if h is not None and h >= FLEE_HEALTH_FLOOR else 0
        flee += 1 if health(ln) or _after(rows, i, health) else 0
        bites += 1 if _bitten_after(L, ln) else 0
    return {"read": True, "exits": exits, "short": short, "corner_yields": yields, "above_floor": above,
            "flee_after": flee, "bites_after": bites}


# ---------------------------------------------------------------- P27-K3
def _bleeding(f, part):
    return any(isinstance(p, dict) and p.get("i") == part and p.get("bleeding") is True
               for p in E._l(E._d(E._d(f).get("body")).get("parts")))


def e_spent_held(L):
    """The replace held under a chaser (P27-K3, `Survive.REPLACE_QUIET`): {read, holds, parts, unchased,
    replaces_after, bleeding_while_held}. Reading: `holds` the lines whose care why carries `spent_held` {part,
    chasing} (`care.Care.choose`'s spent step), `parts` them by part, `unchased` those whose `chasing` reads 0 or less
    (must read 0: the rule holds only under a chaser), `replaces_after` the spent replaces (a care line sending the
    `bandage` for the `spent` reason) of a part held since that part's last replace. Inference off the frames:
    `bleeding_while_held` the holds whose frame reads the held part bleeding."""
    if L is None:
        return {"read": False}
    holds = unchased = after = bled = 0
    parts, pending = {}, set()
    for ln in L.rows:
        c = E._bw(ln, "care")
        if ln.get("branch") == "care" and c.get("reason") == "spent" and E._sent(ln, "bandage"):
            p = c.get("part")
            after += 1 if p in pending else 0
            pending.discard(p)
        h = c.get("spent_held")
        if not isinstance(h, dict):
            continue
        holds += 1
        p = h.get("part")
        G14._inc(parts, str(p))
        pending.add(p)
        ch = E._n(h.get("chasing"))
        unchased += 1 if ch is not None and ch <= 0 else 0
        f = L.frame(ln)
        bled += 1 if f is not None and _bleeding(f, p) else 0
    return {"read": True, "holds": holds, "parts": parts, "unchased": unchased, "replaces_after": after,
            "bleeding_while_held": bled}


# ---------------------------------------------------------------- P27-L
def e_wounded_swing_off(L):
    """P26-L1's divided swing withdrawn (P27-L, `Threat.WOUNDED_SWING` off by default): {read, lines, swings, breaks}.
    Reading: `lines` the threat lines whose why carries `wounded_swing` (the misses, `shove.FightShove._wounded_swing`),
    `swings` those that sent the `attack` (must read 0 with the default: the rule is off), `breaks` the threat lines
    whose why `corner` reads kind "break" carrying `misses` (P25-L's break after the missed shoves, which takes the
    swing's place: `gates_e.e_corner_kinds`' `miss_breaks`)."""
    if L is None:
        return {"read": False}
    lines = swings = breaks = 0
    for ln in L.rows:
        if ln.get("branch") != "threat":
            continue
        w = L.why(ln)
        if w.get("wounded_swing") is not None:
            lines += 1
            swings += 1 if E._sent(ln, "attack") else 0
        c = w.get("corner")
        breaks += 1 if isinstance(c, dict) and c.get("kind") == "break" and c.get("misses") is not None else 0
    return {"read": True, "lines": lines, "swings": swings, "breaks": breaks}


def readings_e17(out, decision_lines, lines):
    """{key: reading} of the nine readings of survival iteration 20 (`NEW`), each {"read": False} without a decision
    log."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    return {"stuck_leave": e_stuck_leave(L), "floor_finish": e_floor_finish(L, lines), "fallen_seek": e_fallen_seek(L),
            "listing": e_listing(L), "shove_close": e_shove_close(L), "stock_early": e_stock_early(L, lines),
            "low_exit": e_low_exit(L), "spent_held": e_spent_held(L), "wounded_swing_off": e_wounded_swing_off(L)}


def lines_e17(g):
    """One report line per pass 17 reading, each clause marked reading or inference."""
    sl, ff, fs, li, sc, se, lx, sh, wo = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append(("stuck leave (P27-F) [reading]: %s `stuck_mark` lines by goal %s (%s naming an edge), `leave` picks by "
                "way %s ([inference] the walk away told from the walk back by its target); [inference] %s rests "
                "proposed on a marked square (must read 0), %s game minutes on a marked square" % (
                    sum(E._d(sl.get("marks")).values()), sl.get("marks"), sl.get("edged"), sl.get("leaves"),
                    sl.get("rests_on_marked"), sl.get("minutes_on_marked_square"))) if sl.get("read")
               else "stuck leave (P27-F): no decision log read")
    out.append(("floor finish (P27-G) [reading]: %s `floor_finish` lines, %s swings sent, %s kills, %s `strike_runs` "
                "holds; [inference] %s with a swing event, %s followed by a stomp at the same zombie" % (
                    ff.get("lines"), ff.get("sent"), ff.get("kills"), ff.get("strike_holds"), ff.get("landed"),
                    ff.get("stomps_after"))) if ff.get("read") else "floor finish (P27-G): no decision log read")
    out.append(("fallen seek (P27-H) [reading]: %s `fallen_seek` lines, %s walks, %s left, ticks %s, %s under "
                "FALLEN_SEEK_TICKS (must read 0); [inference] %s walked targets killed after" % (
                    fs.get("lines"), fs.get("walks"), fs.get("left"), fs.get("ticks"), fs.get("short"),
                    fs.get("kills_after"))) if fs.get("read") else "fallen seek (P27-H): no decision log read")
    out.append(("listing (P27-I) [reading]: %s `listing` lines leaving out %s fallen and %s across; [inference] %s "
                "lines whose listing fell under MANY_LISTED_N by the clause" % (
                    li.get("lines"), li.get("fallen"), li.get("across"), li.get("many_avoided"))) if li.get("read")
               else "listing (P27-I): no decision log read")
    out.append(("shove close (P27-J) [reading]: %s `shove_close` lines, %s walks, %s left, %s under SHOVE_CLOSE_TICKS "
                "(must read 0), %s rests at an idle zombie; [inference] %s walks followed by a shove at the same "
                "zombie" % (sc.get("lines"), sc.get("walks"), sc.get("left"), sc.get("short"), sc.get("idle_rests"),
                            sc.get("shoves_after"))) if sc.get("read") else "shove close (P27-J): no decision log read")
    out.append(("stock early (P27-K1) [reading]: %s `stock_early` lines, rips by branch %s (%s the care yield's), %s "
                "at RAG_STOCK or more (must read 0); [inference] %s followed by more clean dressings held" % (
                    se.get("lines"), se.get("rips"), se.get("yields"), se.get("full"), se.get("rags_after")))
               if se.get("read") else "stock early (P27-K1): no decision log read")
    out.append(("low exit (P27-K2) [reading]: %s `low_exit` lines, %s under SHOVE_FAIL_N misses (must read 0), %s "
                "inside corner yields, %s at FLEE_HEALTH_FLOOR or more (must read 0); [inference] %s followed by the "
                "`health` flee, %s by a new bite within BITE_AFTER_S" % (
                    lx.get("exits"), lx.get("short"), lx.get("corner_yields"), lx.get("above_floor"),
                    lx.get("flee_after"), lx.get("bites_after"))) if lx.get("read")
               else "low exit (P27-K2): no decision log read")
    out.append(("spent held (P27-K3) [reading]: %s `spent_held` lines by part %s, %s with no chaser (must read 0), %s "
                "spent replaces after a hold; [inference] %s holds on a bleeding part" % (
                    sh.get("holds"), sh.get("parts"), sh.get("unchased"), sh.get("replaces_after"),
                    sh.get("bleeding_while_held"))) if sh.get("read") else "spent held (P27-K3): no decision log read")
    out.append(("wounded swing off (P27-L) [reading]: %s `wounded_swing` lines, %s divided swings sent (must read 0 "
                "with the default), %s P25-L breaks" % (wo.get("lines"), wo.get("swings"), wo.get("breaks")))
               if wo.get("read") else "wounded swing off (P27-L): no decision log read")
    return out


def report_lines_e17(g):
    """report_lines_e16's lines (the gate line naming gate_e17) then one line per pass 17 reading (`lines_e17`)."""
    g = E._d(g)
    out = [("gate_e17 " + ln[len("gate_e16 "):]) if ln.startswith("gate_e16 ") else ln
           for ln in G16.report_lines_e16(g)]
    return out + lines_e17(g)


def grade_e17(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e16 under "grade_e17" with the nine readings of survival iteration 20 (`NEW`, `readings_e17`; each
    {"read": False} without a decision log; they read the state lines' act lines, events and frames)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G16.grade_e16(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e17"
    if files and "frames_files" in g:
        g["frames_files"] = files
    g.update(readings_e17(out, decision_lines, lines))
    g["report_lines"] = report_lines_e17(g)
    return g


def gate_e17(outs):
    """gate_e13 (neither grade_e14, grade_e15, grade_e16 nor grade_e17 changes what it reads), named gate_e17."""
    return E.gate_e13(outs)
