"""grades.x3 -- the group grade (Plan 33 Task 4): `grade_x3` is `grades.x2.grade_x2` under "grade_x3", with "grade_x2"
in `base`, x2's own base ("grade_x1") in `base_x2` and the x1 grade's base (grade_f12 for an LLM session, grade_e21 for
a chain one) kept in `base_x1`, plus five readings of Plan 33's rules, each over the sources clipped at the loop's stop
(`x1.clip`) and each `{"read": False}` when its source is absent:

  head_ticks     the finish's head step (Task 1, PZAgent_StanceMelee.lua's K.HEAD_MAX_TICKS): over the melee act lines,
                 every `head_ticks` read on a press leaf (`result.press.head_ticks`: the head ticks the press waited)
                 and on a done line (`result.head_ticks`: the handback's); {read, leaves (the values read), max (None
                 with none: a log before Task 1's Lua), over_cap (the melees whose done line reads `end` HANDBACK and
                 `why` HEAD_STALL), by_melee [[aid, the melee's largest head_ticks]] in the melees' first-line order}.
                 Read False without a melee act line.
  crawler_first  the crawler stomped first (Task 2's CRAWLER_FIRST): the decision lines whose threat why
                 (`inputs.branches.threat`) carries the key CRAWLER_FIRST at any depth; {read, lines, finishes (those
                 lines that sent a finish: a `melee` in mode `finish`, or a `stomp`), targets (the finishes' targetIds,
                 distinct, in order), kills (those targets among the `zombie_dead` events), rows [{i, sent, type, mode,
                 target, crawler (the why's value)}]}. Read False without a decision log.
  group_leave    the group left before it closes (Task 3's GROUP_LEAVE): the decision lines whose threat why carries
                 GROUP_LEAVE, gathered into legs (runs of consecutive such lines); a leg is counted when one of its lines
                 sent an action; {read, lines, legs, to_door (the legs that sent a `walkTo`: the leave toward a door or
                 doorway), runs (the legs that sent a `steer`), standing_at (per leg, the standing zombies within
                 GROUP_NEAR_R of the player at the frame at or before the leg's first line; None with no frame), rows
                 [{i0, i1, types, standing}]}. Read False without a decision log.
  drag_guard     the drag-down guard fought (Task 3's DRAG_GUARD_FIGHT and SIDE_CLEAR): {read, guard_lines (the lines
                 whose threat why carries DRAG_GUARD), shoves (those that sent a shove: a `shove`, or a `melee` in mode
                 `shove`), runs_refused (those that sent no `steer`: the run held back, a shove or nothing sent),
                 runs (those that sent a `steer`), clear_lines (the lines carrying SIDE_CLEAR), clear_steers (those that
                 sent a `steer`), rotations (the SIDE_CLEAR value's rotation on each clear steer: the value itself when a
                 number, else its ROTATION_KEYS' first number), side_shoves (the SIDE_CLEAR lines that sent a shove: no
                 clear bearing), into_side {steers, blocked} (every sent `steer` in the log, and those whose heading
                 (vx, vy) passes within SIDE_R of a standing zombie over the first SIDE_LOOK tiles of the leg, at the
                 frame at or before its line: the spec's success clause 4)}. Read False without a decision log.
  idle_snap      the body between presses (Task 1's idle snap): the frames with no melee act running (the frame's act
                 not a melee accepted or in progress) and a standing zombie within IDLE_SNAP_R; the body's error
                 (`me.bodyAngle`) against the bearing to the nearest such zombie, x2's form (degrees wrapped, absolute);
                 {read, frames, body (x2's summary: n, median, p90, hold30), body_err_median}. Read False without a
                 frame reading `me.bodyAngle`.

"Carries the key" (the contract with Tasks 2 and 3): the threat why is a dict, and the key is one of its keys or a key
of a dict nested in it (a list's dicts included), whatever its value; the why's own value is printed as it stands.

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; `grades.x2` and `grades.x1`
(frozen, pinned by their regrade tests) and the shared readers of `gates_e` are its only imports."""
import math

from agent.base import gates_e as E
from agent.base.grades import x1 as GX1
from agent.base.grades import x2 as GX2

# Frozen copies of the live names read here (P26-Q), each with its source.
MELEE = "melee"            # the reflex's type (schema actionType, PZA/1.8)
STEER = "steer"            # schema actionType: the run
WALK = "walkTo"            # schema actionType: a leave leg toward a door or doorway (Task 3's amendments: no `leave` type)
SHOVE = "shove"            # schema actionType, and the melee's mode `shove`
STOMP = "stomp"            # schema actionType
FINISH = "finish"          # the melee's mode at a fallen zombie (planner/maneuvers/melee.py, PZAgent_StanceMelee.lua)
LIVE_STATES = ("accepted", "progress")   # a frame's act state while the act runs (PZAgent_Skills.lua's K.status)
HEAD_TICKS = "head_ticks"  # PZAgent_StanceMelee.lua (Plan 33 Task 1): the press leaf's and the head_stall handback's
HANDBACK = "handback"      # PZAgent_StanceMelee.lua's done `end`
HEAD_STALL = "head_stall"  # PZAgent_StanceMelee.lua (Plan 33 Task 1): the handback's why at K.HEAD_MAX_TICKS
THREAT = "threat"          # planner/survive.py: the threat branch's why, `inputs.branches.threat`
CRAWLER_FIRST = "crawler_first"   # Plan 33 Task 2's amendments: the why key of the CRAWLER_FIRST rule
GROUP_LEAVE = "group_leave"       # Plan 33 Task 3's amendments: the why key of the GROUP_LEAVE rule
DRAG_GUARD = "drag_guard"         # Plan 33 Task 3's amendments: the why key of the DRAG_GUARD_FIGHT rule
SIDE_CLEAR = "side_clear"         # Plan 33 Task 3's amendments: the why key of the SIDE_CLEAR rule
ROTATION_KEYS = ("rotation", "rot", "turn", "deg")   # a SIDE_CLEAR dict value's rotation, the first number read
GROUP_NEAR_R = 3.0         # tiles: planner/policies.py GROUP_NEAR_R (P23-AP 2)
SIDE_R = 1.0               # tiles: Plan 33 Task 3's amendments, SIDE_CLEAR's clearance
SIDE_LOOK = 3.0            # tiles: ... over the leg's first SIDE_LOOK tiles
IDLE_SNAP_R = 2.5          # tiles: PZAgent_StanceMelee.lua K.IDLE_SNAP_R (Plan 33 Task 1; KEEP_R's value)
NEW = ("head_ticks", "crawler_first", "group_leave", "drag_guard", "idle_snap")
N_LINES = len(NEW)         # the report lines lines_x3 appends: one per NEW key


# ---------------------------------------------------------------- shared readers
def carries(why, key):
    """True when the dict `why` holds `key` as its own key or as the key of a dict nested in it (lists included)."""
    if isinstance(why, dict):
        return key in why or any(carries(v, key) for v in why.values())
    if isinstance(why, list):
        return any(carries(v, key) for v in why)
    return False


def value_of(why, key):
    """The value of the first `key` found in `why` (`carries`' order: its own keys first), else None."""
    if isinstance(why, dict):
        if key in why:
            return why[key]
        for v in why.values():
            if carries(v, key):
                return value_of(v, key)
    if isinstance(why, list):
        for v in why:
            if carries(v, key):
                return value_of(v, key)
    return None


def threat_why(row):
    """The decision line's threat why (`inputs.branches.threat`), else {}."""
    return E._d(E._d(E._d(E._d(row).get("inputs")).get("branches")).get(THREAT))


def sent_action(row):
    """(type, args) of the line's sent action, else (None, {})."""
    row = E._d(row)
    a = E._d(row.get("action"))
    if row.get("sent") is not True or not a.get("type"):
        return None, {}
    return a.get("type"), E._d(a.get("args"))


def is_shove(typ, args):
    return typ == SHOVE or (typ == MELEE and args.get("mode") == SHOVE)


def is_finish(typ, args):
    return typ == STOMP or (typ == MELEE and args.get("mode") == FINISH)


def standing(frame, r):
    """[(d, zombie)] of the frame's standing zombies (not reading `onFloor` true) within `r` of the player, nearest
    first; [] without a player position."""
    me = GX2._pos(GX2._me(frame))
    if me is None:
        return []
    out = []
    for z in E._l(E._d(frame).get("zombies")):
        z = E._d(z)
        p = GX2._pos(z)
        if p is None or z.get("onFloor") is True:
            continue
        d = math.hypot(p[0] - me[0], p[1] - me[1])
        if d <= r:
            out.append((d, z))
    return sorted(out, key=lambda t: t[0])


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ---------------------------------------------------------------- the readings
def e_head_ticks(out, lines):
    """The head_ticks reading (the module docstring)."""
    by = GX1._melee_lines(lines)
    if not by:
        return {"read": False}
    leaves, over, rows = 0, 0, []
    for aid, lns in by.items():
        vals = []
        for ln in lns:
            res = E._d(ln.get("result"))
            for v in (E._d(res.get("press")).get(HEAD_TICKS), res.get(HEAD_TICKS)):
                if _num(v) is not None:
                    vals.append(v)
            if ln.get("state") == "done" and res.get("end") == HANDBACK and res.get("why") == HEAD_STALL:
                over += 1
        leaves += len(vals)
        if vals:
            rows.append([aid, max(vals)])
    return {"read": True, "leaves": leaves, "max": max((v for _, v in rows), default=None), "over_cap": over,
            "by_melee": rows}


def e_crawler_first(out, rows, lines):
    """The crawler_first reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    picked, targets, finishes = [], [], 0
    for i, r in enumerate(E._l(rows)):
        why = threat_why(r)
        if not carries(why, CRAWLER_FIRST):
            continue
        typ, args = sent_action(r)
        fin = is_finish(typ, args)
        t = args.get("targetId")
        if fin:
            finishes += 1
            if t is not None and t not in targets:
                targets.append(t)
        picked.append({"i": i, "sent": typ is not None, "type": typ, "mode": args.get("mode"), "target": t,
                       "crawler": value_of(why, CRAWLER_FIRST)})
    dead = set(GX1._event_kills(lines))
    return {"read": True, "lines": len(picked), "finishes": finishes, "targets": targets,
            "kills": sum(1 for t in targets if t in dead), "rows": picked}


def e_group_leave(out, rows, lines):
    """The group_leave reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    rows = E._l(rows)
    index = E._frame_index(lines)
    runs, cur = [], []
    for i, r in enumerate(rows):
        if carries(threat_why(r), GROUP_LEAVE):
            if cur and cur[-1] != i - 1:
                runs.append(cur)
                cur = []
            cur.append(i)
    if cur:
        runs.append(cur)
    legs = []
    for run in runs:
        types = [t for t in (sent_action(rows[i])[0] for i in run) if t is not None]
        if not types:
            continue
        f = E._frame_at(index, E._n(E._d(rows[run[0]]).get("wall")))
        legs.append({"i0": run[0], "i1": run[-1], "types": types,
                     "standing": len(standing(f, GROUP_NEAR_R)) if f is not None else None})
    return {"read": True, "lines": sum(len(r) for r in runs), "legs": len(legs),
            "to_door": sum(1 for g in legs if WALK in g["types"]), "runs": sum(1 for g in legs if STEER in g["types"]),
            "standing_at": [g["standing"] for g in legs], "rows": legs}


def rotation(v):
    """The SIDE_CLEAR value's rotation: the value when a number, else its ROTATION_KEYS' first number, else None."""
    if _num(v) is not None:
        return v
    v = E._d(v)
    return next((v[k] for k in ROTATION_KEYS if _num(v.get(k)) is not None), None)


def blocks(frame, vx, vy):
    """True when the heading (vx, vy) from the frame's player passes within SIDE_R of a standing zombie over the
    first SIDE_LOOK tiles (the segment's nearest point to the zombie); False with no heading or no position."""
    me = GX2._pos(GX2._me(frame))
    n = math.hypot(vx, vy) if vx is not None and vy is not None else 0.0
    if me is None or n == 0.0:
        return False
    ux, uy = vx / n, vy / n
    for _, z in standing(frame, SIDE_LOOK + SIDE_R):
        p = GX2._pos(z)
        t = min(max((p[0] - me[0]) * ux + (p[1] - me[1]) * uy, 0.0), SIDE_LOOK)
        if math.hypot(me[0] + t * ux - p[0], me[1] + t * uy - p[1]) < SIDE_R:
            return True
    return False


def e_drag_guard(out, rows, lines):
    """The drag_guard reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    index = E._frame_index(lines)
    g = {"read": True, "guard_lines": 0, "shoves": 0, "runs_refused": 0, "runs": 0, "clear_lines": 0,
         "clear_steers": 0, "rotations": [], "side_shoves": 0, "into_side": {"steers": 0, "blocked": 0}}
    for r in E._l(rows):
        why = threat_why(r)
        typ, args = sent_action(r)
        if carries(why, DRAG_GUARD):
            g["guard_lines"] += 1
            g["shoves"] += 1 if is_shove(typ, args) else 0
            g["runs" if typ == STEER else "runs_refused"] += 1
        if carries(why, SIDE_CLEAR):
            g["clear_lines"] += 1
            if typ == STEER:
                g["clear_steers"] += 1
                g["rotations"].append(rotation(value_of(why, SIDE_CLEAR)))
            g["side_shoves"] += 1 if is_shove(typ, args) else 0
        if typ == STEER:
            g["into_side"]["steers"] += 1
            f = E._frame_at(index, E._n(E._d(r).get("wall")))
            if f is not None and blocks(f, E._n(args.get("vx")), E._n(args.get("vy"))):
                g["into_side"]["blocked"] += 1
    return g


def e_idle_snap(out, lines, frames):
    """The idle_snap reading (the module docstring)."""
    if not any(E._n(GX2._me(f).get("bodyAngle")) is not None for f in frames):
        return {"read": False}
    types = GX2.act_types(lines)
    errs, n = [], 0
    for f in frames:
        act = E._d(f.get("act"))
        if types.get(act.get("aid")) == MELEE and act.get("state") in LIVE_STATES:
            continue
        near = standing(f, IDLE_SNAP_R)
        if not near:
            continue
        n += 1
        me, p = GX2._pos(GX2._me(f)), GX2._pos(near[0][1])
        b = math.atan2(p[1] - me[1], p[0] - me[0]) if p != me else None
        errs.append(GX2._err(f, "bodyAngle", b))
    s = GX2.summary(errs)
    return {"read": True, "frames": n, "body": s, "body_err_median": s.get("median")}


def readings_x3(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`), over the sources clipped at the loop's stop (`x1.clip`)."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    return {"head_ticks": e_head_ticks(out, lines), "crawler_first": e_crawler_first(out, rows, lines),
            "group_leave": e_group_leave(out, rows, lines), "drag_guard": e_drag_guard(out, rows, lines),
            "idle_snap": e_idle_snap(out, lines, frames)}


def head_ticks_cell(out, decision_lines, lines):
    """The scorecard's `head_ticks max` (tools/trial_score.py): head_ticks' max, None when unread or none read."""
    h = e_head_ticks(out, lines)
    return h.get("max") if h.get("read") else None


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=1):
    return round(v, n) if isinstance(v, float) else v


def lines_x3(g):
    """One report line per new reading (`NEW`), each clause marked reading or inference."""
    h, c, gl, dg, idle = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append("head ticks (the finish's head step, the press leaves' and handbacks' head_ticks) [reading]: %s values "
               "read, max %s, %s melees handed back head_stall, by melee %s" % (
                   h.get("leaves"), h.get("max"), h.get("over_cap"), h.get("by_melee"))
               if h.get("read") else GX1._unread("head ticks"))
    out.append("crawler first (threat why %s) [reading]: %s lines, %s finishes sent at %s, %s of them killed; "
               "%s" % (CRAWLER_FIRST, c.get("lines"), c.get("finishes"), c.get("targets"), c.get("kills"),
                       [(r["i"], r["type"], r["mode"], r["target"]) for r in E._l(c.get("rows"))])
               if c.get("read") else GX1._unread("crawler first"))
    out.append("group leave (threat why %s) [reading]: %s lines, %s legs, %s toward a door, %s runs; standing within "
               "%s tiles at each leg's first line %s" % (
                   GROUP_LEAVE, gl.get("lines"), gl.get("legs"), gl.get("to_door"), gl.get("runs"), GROUP_NEAR_R,
                   gl.get("standing_at"))
               if gl.get("read") else GX1._unread("group leave"))
    if dg.get("read"):
        ins = E._d(dg.get("into_side"))
        out.append("drag guard (threat why %s, %s) [reading]: %s guard lines, %s shoves, %s runs refused, %s runs; "
                   "%s clear lines, %s clear steers rotated %s, %s side shoves; [inference] %s of %s steers sent "
                   "heading within %s tiles of a standing zombie over %s tiles" % (
                       DRAG_GUARD, SIDE_CLEAR, dg.get("guard_lines"), dg.get("shoves"), dg.get("runs_refused"),
                       dg.get("runs"), dg.get("clear_lines"), dg.get("clear_steers"), dg.get("rotations"),
                       dg.get("side_shoves"), ins.get("blocked"), ins.get("steers"), SIDE_R, SIDE_LOOK))
    else:
        out.append(GX1._unread("drag guard"))
    out.append("idle snap (me.bodyAngle against the nearest standing zombie within %s tiles, no melee running) "
               "[reading]: %s frames, %s" % (IDLE_SNAP_R, idle.get("frames"), GX2._s(idle.get("body")))
               if idle.get("read") else "idle snap: no frame reads me.bodyAngle")
    return out


def report_lines_x3(g):
    """grade_x2's report lines (`report_lines_x2`), its gate line naming gate_x3, then `lines_x3`."""
    g = E._d(g)
    base = GX2.report_lines_x2(g)
    return [("gate_x3 " + ln[len("gate_x2 "):]) if ln.startswith("gate_x2 ") else ln for ln in base] + lines_x3(g)


def grade_x3(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x2` under "grade_x3" (`base` "grade_x2", `base_x2` x2's own base, `base_x1` kept) with the group
    readings (`readings_x3`), over the state lines of `state_dir` unless `lines` is given (read once and handed down);
    its report lines `report_lines_x3`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX2.grade_x2(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x2"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x3"
    g.update(readings_x3(record, decision_lines, lines))
    g["report_lines"] = report_lines_x3(g)
    return g


def gate_x3(outs):
    """gate_x2 (grade_x3 changes none of what it reads), named gate_x3."""
    return GX2.gate_x2(outs)
