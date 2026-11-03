"""grades.e15 -- the chain sessions' grade, pass 15 (Plan 26 Task 7b): `grade_e15` is `grades.e14.grade_e14` under
"grade_e15" with the three readings of survival iteration 18 (Plan 26 Task 7 and its fix 1), each read off the decision
log's why fields, the artifact's actions and the state log's act lines, frames and map:

  window_inner  P26-I, a window way out needs an inside square that can be stood on (`Threat.WINDOW_INNER`): the planner
                logs no why for a window it left out, so this counts the trapped lines while the kept map held a window
                of the player's building whose inside square reads `solid` or `solidTrans`, and the window steps that
                named such a window (an inference; the second must read 0 on a build with the rule).
  window_stall  P26-J (`Threat.WINDOW_STALL`) and P26-M: the window climbs dropped for their stall (an inference off the
                refused set that grew while the act still ran) and the `interrupted` ends, how many were sent again
                (the Lua's P26-M end, the Flee's one more try) and how many were not (the exit refused).
  stand_crowd   P26-K (`Threat.STAND_CROWD`) and P26-K2: the stand's `crowd` ends with the count they logged, the exit
                each took (`close` | `window` | `door` | `opening` | `trapped`), the closes sent on the end's tick and
                whether a zombie read inside within CLOSE_INSIDE_S after one (an inference off the frames and the map).

Each reading is {"read": False} without a decision log. A key marked reading counts what the log or the artifact
states; one marked inference reads an effect off the map, the frames or the order of lines. Frozen once an artifact
carries its output (`grades/__init__.py`); `gates_e`, `grades/e14.py` and every driver stay untouched."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.world import World

RESEND_S = 5.0               # loop seconds: an `interrupted` window act sent again at its square this soon after
                             # its end is the same exit's second try (the Flee sends it on the next choose)
CLOSE_INSIDE_S = 30.0        # wall seconds: a zombie on a square of the stand's building is read this long after
                             # a close
STALL_SLACK_S = 1.0          # wall seconds: a window act sent this far before its run's first line still belongs to it
STALL_LOOKAHEAD_LINES = 5    # log lines: the refused set is read at the first line within this many after a run that
                             # carries one (the trapped hold's, the next flee's)
HELD_FLEES = ("many", "doorway")


def _sq(v):
    """(x, y, z) of a list of three or more numbers, else None."""
    if isinstance(v, list) and len(v) >= 3 and all(E._n(c) is not None for c in v[:3]):
        return tuple(int(c) for c in v[:3])
    return None


def _refused(w):
    """The set of squares the Flee's `refused` why lists, None when the why carries no `refused`."""
    r = w.get("refused")
    return None if not isinstance(r, list) else {s for s in (_sq(x) for x in r) if s is not None}


def _held(w):
    """True when the Flee's threat why reads the trapped hold: a `many` or `doorway` flee carrying `trapped`
    (`flee.py:656`) or a stand exit (`doorway_exit`) reading `exit` "trapped"."""
    ex = w.get("doorway_exit")
    return w.get("flee") in HELD_FLEES and ("trapped" in w or (isinstance(ex, dict) and ex.get("exit") == "trapped"))


class _Map:
    """The kept map as `World.window_way` reads one: its `map` and `_window_edge`, borrowed from `World`."""
    _window_edge = World._window_edge
    window_way = World.window_way

    def __init__(self, squares):
        self.map = squares


def _unstood(squares, building, z):
    """The window squares (x, y) of `building` on floor `z` whose inside square (`World.window_way`) reads `solid` or
    `solidTrans`, a window not barricaded (`goals.usable_windows`' own filter; a window failed by a dead end is not
    known to the map and is read as usable)."""
    m, out = _Map(squares), set()
    for sq, rec in squares.items():
        w = rec.get("window")
        if w is None or sq[2] != z or (isinstance(w, dict) and w.get("barricaded") is True):
            continue
        way = m.window_way(sq, building)
        inner = squares.get(way[0]) if way is not None else None
        if inner is not None and (inner.get("solid") or inner.get("solidTrans")):
            out.add((sq[0], sq[1]))
    return out


def e_window_inner(L, lines):
    """The window inner square (P26-I, `Threat.WINDOW_INNER`; E17, `e_day_17-20261102-180459`: the stand's `inside`
    end walked out by the kitchen window whose inside square read `solidTrans` with a counter on it): {read, lines,
    offered, windows, unread}. Inference, named so: the planner logs no why for a window `night.window_exits` left out,
    so both counts read the kept map as of the line (`_MapView`) for the windows of the building of the square the
    player stood on (the frame, else `inputs.x`/`y`) that were not barricaded and whose inside square
    (`World.window_way`) reads `solid` or `solidTrans`. `lines` counts the threat lines that read the trapped hold
    (`_held`: a `many` or `doorway` flee carrying `trapped`, or a `doorway_exit` reading `trapped`) while such a window
    existed (a standable window beside it would have been offered, so these are the lines on which a left-out window
    existed, not the lines it alone caused); `offered` the lines whose window step (`step` "window") names such a
    window, which must read 0 on a build with the rule (E17's reading: the lines that walked to the counter's window);
    `windows` lists those squares of both (distinct, sorted) and `unread` the trapped lines whose player square, or its
    building, the map does not know."""
    if L is None:
        return {"read": False}
    mv = E._MapView(lines)
    n = offered = unread = 0
    windows = set()
    for ln in L.rows:
        w = L.why(ln)
        held, win = _held(w), w.get("window")
        step = w.get("step") == "window" and isinstance(win, list) and len(win) >= 2
        if not held and not step:
            continue
        me = E._frame_me(L, ln)
        squares = mv.at(E._n(ln.get("wall")))
        here = None if me is None else squares.get((int(math.floor(me[0])), int(math.floor(me[1])), me[2]))
        building = None if here is None else here.get("building")
        if building is None:
            unread += 1 if held else 0
            continue
        found = _unstood(squares, building, me[2])
        n += 1 if held and found else 0
        if step and (win[0], win[1]) in found:
            offered += 1
            windows.add((win[0], win[1]))
        windows |= found if held else set()
    return {"read": True, "lines": n, "offered": offered, "windows": sorted(windows), "unread": unread}


def _window_runs(L):
    """[(first index, last index, outer square, window (x, y))] of the adjacent lines whose threat why reads `step`
    "window" with one `outer` (a window way out's step, `flee.Flee._window_step`)."""
    runs = []
    for i, ln in enumerate(L.rows):
        w = L.why(ln)
        outer, win = _sq(w.get("outer")), w.get("window")
        if w.get("step") != "window" or outer is None or not isinstance(win, list) or len(win) < 2:
            continue
        if runs and runs[-1][1] == i - 1 and runs[-1][2] == outer:
            runs[-1][1] = i
        else:
            runs.append([i, i, outer, (win[0], win[1])])
    return runs


def _stalled(out, L, lines):
    """The (x, y) of the window runs whose climb the stall read dropped: the Flee notes the window `stalled`, refuses
    its outer square (`flee.py:437`) and leaves the act running, so an inference reads the refused set growing with the
    run's outer square at the first line within STALL_LOOKAHEAD_LINES after the run that carries one, while the run's
    window act (the last threat `window` act of that square sent within the run, STALL_SLACK_S before its first line)
    was not yet ended at that line's wall; a climb that ended first (`done`, `locked`, `dead`) is a refusal of its
    own."""
    acts = G14._acts(lines, "window")
    rows = G14._loop_actions(out, "window", "threat")
    found = []
    if L.t0 is None:
        return found
    for first, last, outer, win in _window_runs(L):
        w0 = E._n(L.rows[first].get("wall"))
        seen = _refused(L.why(L.rows[first]))
        if w0 is None or (seen is not None and outer in seen):
            continue
        for j in range(last + 1, min(len(L.rows), last + 1 + STALL_LOOKAHEAD_LINES)):
            now = _refused(L.why(L.rows[j]))
            if now is None:
                continue
            wall_ms = (E._n(L.rows[j].get("wall")) or 0.0) * 1000.0
            if outer in now:
                mine = [a for a in rows if (E._d(a.get("args")).get("x"), E._d(a.get("args")).get("y")) == win
                        and w0 - STALL_SLACK_S <= L.t0 + (E._n(a.get("sentS")) or 0.0) <= wall_ms / 1000.0]
                if mine:
                    row = mine[-1]
                    ended_ms = G14._end_ms(L, row, acts)
                    if row.get("state") not in G14.TERMINAL or (ended_ms is not None and ended_ms > wall_ms):
                        found.append(win)
            break
    return found


def e_window_stall(out, L, lines):
    """The window stall and the interrupted end (P26-J, `Threat.WINDOW_STALL`, and P26-M): {read, stalled, windows,
    interrupted, resent, refused_after_interrupt}. Inference (`_stalled`): `stalled` the window climbs the Flee dropped
    for their stall, `windows` their squares: the planner logs the drop only as the window's outer square joining the
    `refused` why, with no `window_fail` key, so the growth with the act still running stands for it. Reading, off the
    threat branch's `window` acts of loop.actions (the terminal act line's state and reason where one exists):
    `interrupted` those that ended `failed` `interrupted` (the Lua's end when a hit clears its queue, P26-M), `resent`
    those followed by another threat `window` act at the same square sent within RESEND_S of their end (the Flee's one
    more try, `flee.py:443`) and `refused_after_interrupt` the others (the second `interrupted` end within
    DOOR_RETRY_MIN reads `failed` and refuses the exit, or the session ended there)."""
    if L is None:
        return {"read": False}
    stalled = _stalled(out, L, lines)
    acts = G14._acts(lines, "window")
    rows = G14._loop_actions(out, "window", "threat")
    interrupted = resent = 0
    for a in rows:
        end = acts.get(a.get("aid"), (None, None))[1]
        state, reason = (end.get("state"), end.get("reason")) if end is not None else (a.get("state"), a.get("reason"))
        if state != "failed" or reason != "interrupted":
            continue
        interrupted += 1
        end_ms = G14._end_ms(L, a, acts)
        if end_ms is None or L.t0 is None:
            continue
        end_s, at = end_ms / 1000.0 - L.t0, E._d(a.get("args"))
        resent += 1 if any(b is not a and (E._d(b.get("args")).get("x"), E._d(b.get("args")).get("y"))
                           == (at.get("x"), at.get("y")) and 0.0 <= (E._n(b.get("sentS")) or 0.0) - end_s <= RESEND_S
                           for b in rows) else 0
    return {"read": True, "stalled": len(stalled), "windows": sorted(set(stalled)), "interrupted": interrupted,
            "resent": resent, "refused_after_interrupt": interrupted - resent}


def _inside_after(L, mv, ln):
    """True when a frame within CLOSE_INSIDE_S after the line's wall holds a zombie on a mapped square with a room of
    the building the player stood in at the line, False when every mapped frame there holds none, None when the
    player's building or every frame is unread."""
    wall = E._n(ln.get("wall"))
    me = E._frame_me(L, ln)
    if wall is None or me is None:
        return None
    here = mv.at(wall).get((int(math.floor(me[0])), int(math.floor(me[1])), me[2]))
    building = None if here is None else here.get("building")
    if building is None:
        return None
    walls, frames = L.index
    lo = bisect.bisect_right(walls, wall * 1000.0)
    hi = bisect.bisect_right(walls, (wall + CLOSE_INSIDE_S) * 1000.0)
    seen = None
    for w, f in zip(walls[lo:hi], frames[lo:hi]):
        squares = mv.at(w / 1000.0)
        for z in E._l(f.get("zombies")):
            x, y = E._n(E._d(z).get("x")), E._n(E._d(z).get("y"))
            if x is None or y is None:
                continue
            s = squares.get((int(math.floor(x)), int(math.floor(y)), me[2]))
            if s is None:
                continue
            seen = False
            if s.get("room") is not None and s.get("building") == building:
                return True
    return seen


def e_stand_crowd(L, lines):
    """The stand's crowd end (P26-K, `Threat.STAND_CROWD`, and P26-K2): {read, lines, n_hist, by_exit, closes,
    inside_after_close, unread}. Reading: `lines` the threat lines whose `doorway_left` reads "crowd", `n_hist` the
    count each logged in `doorway_crowd` {n} as a histogram, `by_exit` their `doorway_exit` {end crowd, exit} by `exit`
    (`close` for a crowd with nobody inside, K2; `window`, `door`, `opening` or `trapped` for a walk out; "none" for a
    line without one), `closes` the lines among them that sent an `interact` `close` on the end's tick. Inference off
    the frames and the map (`_MapView`): `inside_after_close` the closes after which a frame within CLOSE_INSIDE_S held
    a zombie on a room square of the building the player stood in (the close shut a room that was not empty, or one
    that was entered by another way) and `unread` the closes whose building or frames the map does not know. The
    reading is apart from the frozen `gates_e.e_stand_exit`: its `closes` (must read 0) counts the close after a stand's
    wound, drag and inside ends, a `crowd` end's close (P26-K2, `doorway_exit` {end crowd, exit close}) is
    counted here only, and this reader never reads or changes `stand_exit`."""
    if L is None:
        return {"read": False}
    mv = E._MapView(lines)
    n_hist, by_exit = {}, {}
    n = closes = inside = unread = 0
    for ln in L.rows:
        w = L.why(ln)
        if w.get("doorway_left") != "crowd":
            continue
        n += 1
        G14._inc(n_hist, str(E._d(w.get("doorway_crowd")).get("n")))
        ex = w.get("doorway_exit")
        G14._inc(by_exit, str(ex.get("exit")) if isinstance(ex, dict) and ex.get("end") == "crowd" else "none")
        if not (E._sent(ln, "interact") and E._d(E._d(ln.get("action")).get("args")).get("kind") == "close"):
            continue
        closes += 1
        after = _inside_after(L, mv, ln)
        inside += 1 if after is True else 0
        unread += 1 if after is None else 0
    return {"read": True, "lines": n, "n_hist": n_hist, "by_exit": by_exit, "closes": closes,
            "inside_after_close": inside, "unread": unread}


def _lines_e15(g):
    wi, ws, sc = (E._d(g.get(k)) for k in ("window_inner", "window_stall", "stand_crowd"))
    out = []
    out.append(("window inner square (P26-I) [inference]: %s trapped lines while the kept map held a window of the "
                "player's building whose inside square reads solid or solidTrans, %s window-step lines naming one "
                "(must read 0), at %s; %s trapped lines with the player's square or building unread" % (
                    wi.get("lines"), wi.get("offered"), wi.get("windows"), wi.get("unread")))
               if wi.get("read") else "window inner square (P26-I): no decision log read")
    out.append(("window stall and interrupt (P26-J, P26-M) [reading]: %s interrupted window acts, %s sent again, %s "
                "not (the exit refused); [inference] %s window climbs dropped for their stall, at %s" % (
                    ws.get("interrupted"), ws.get("resent"), ws.get("refused_after_interrupt"), ws.get("stalled"),
                    ws.get("windows"))) if ws.get("read") else "window stall and interrupt (P26-J, P26-M): no decision "
                                                                "log read")
    out.append(("stand crowd end (P26-K, P26-K2) [reading]: %s `crowd` ends, sizes %s, exits %s, %s closes sent on "
                "the tick (the frozen stand_exit `closes` reading excludes `crowd` ends from P26-N on); [inference] "
                "%s closes followed within CLOSE_INSIDE_S by a zombie inside, %s unread" % (
                    sc.get("lines"), sc.get("n_hist"), sc.get("by_exit"), sc.get("closes"),
                    sc.get("inside_after_close"), sc.get("unread"))) if sc.get("read")
               else "stand crowd end (P26-K, P26-K2): no decision log read")
    return out


def report_lines_e15(g):
    """report_lines_e14's lines (the gate line naming gate_e15) then one line per pass 15 reading, each clause marked
    reading or inference."""
    g = E._d(g)
    out = [("gate_e15 " + ln[len("gate_e14 "):]) if ln.startswith("gate_e14 ") else ln
           for ln in G14.report_lines_e14(g)]
    return out + _lines_e15(g)


def grade_e15(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e14 under "grade_e15" with the three readings of survival iteration 18: `window_inner`, `window_stall` and
    `stand_crowd` (each {"read": False} without a decision log; they read the state lines' map, frames and act
    lines)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G14.grade_e14(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e15"
    if files and "frames_files" in g:
        g["frames_files"] = files
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    g["window_inner"] = e_window_inner(L, lines)
    g["window_stall"] = e_window_stall(out, L, lines)
    g["stand_crowd"] = e_stand_crowd(L, lines)
    g["report_lines"] = report_lines_e15(g)
    return g


def gate_e15(outs):
    """gate_e13 (neither grade_e14 nor grade_e15 changes what it reads), named gate_e15."""
    return E.gate_e13(outs)
