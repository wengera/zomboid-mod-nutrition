"""grades.x4 -- the column grade (Plan 34 Task 5): `grade_x4` is `grades.x3.grade_x3` under "grade_x4", with "grade_x3"
in `base`, x3's own base ("grade_x2") in `base_x3`, and x3's nesting below it kept (`base_x2` "grade_x1", `base_x1`
grade_f12 for an LLM session, grade_e21 for a chain one), plus nine readings of Plan 34's rules and of the frozen x3
readers' vocabulary, each over the sources clipped at the loop's stop (`x1.clip`) and each `{"read": False}` when its
source is absent (the decision log for every reading but two: `shoves` reads the state log's act lines, False without
any act line; `idle_snap_by_act` the frames, False without a frame reading `me.bodyAngle`):

  care_withheld     LEAVE_CARE (Task 1): the decision lines whose threat why carries CARE_WITHHELD; {read, lines,
                    by_n (the why's `n`, as a string, to the count), keys (the distinct `key` values, None left out, in
                    first-seen order)}.
  care_at_group     criterion 1: the decision lines of the care branch that sent a `stop`, `rip` or `unwear`, or a
                    `bandage` whose `args.keepMoving` is not true (a standing one: the ride keeps the leg), whose frame
                    (the frame at or before the line's wall, x3's alignment) reads GROUP_LEAVE_N or more standing
                    zombies (x3's `standing`: not `onFloor`) within GROUP_ENTRY_R of the player; {read, lines, rows
                    [{i, type, standing}]}. A line with no frame before it is not counted.
  door_leave        the door under a column (Tasks 2's DOOR_INSIDE and LEAVE_DOOR_RACE) over the threat whys: `lines`
                    the lines whose `group_leave` reads `leg` "door", `picks` their runs of consecutive lines counted as
                    x3 counts a leg (a run one of whose lines sent an action); `refused` {race, one_exit, ...} the
                    `group_leave` `door_refused` values; `aborts` the lines whose `group_leave` carries `door_dropped`;
                    `enters_outside` the lines whose shelter why (the dict holding SHELTER: the Flee's why, merged into
                    the threat why) reads `ended` "outside"; `closes` {sent (the `interact` `close` actions sent), inside
                    (those whose frame puts the player on a square the state log's map last recorded, at or before the
                    line, with a `room`, of the plan's building when the shelter why names one), refused (the shelter
                    whys whose `refused` is a string: "outside" or "guarded"; the doorway pick's list is not one),
                    refused_by {value: count}, unread (closes with no frame or no square record)}.
  retreat           the fighting retreat (Task 3's RETREAT_GAP, RETREAT_MELEE, STRUNG_HOLD): the lines whose
                    `group_retreat` reads `leg` "retreat"; {read, lines, by_kind (on those lines, the `retreat_leg`
                    `kind` values, stand and back first, and `melee` the lines that sent a melee), breaks (the lines
                    carrying `retreat_break`), strung_holds (the lines whose `group_leave` carries `strung_n`), gap (the
                    scorecard's `retreat_gap` over the decision lines, copied below as a frozen copy)}.
  shoves            criterion 4 (Task 4's SHOVE_CLEAR): over the act lines of `shove` and `stomp`, by act id: {read,
                    sent (the acts), done (their `done` lines), started (done lines whose `result.attackStarted` is
                    true), busy (lines `rejected` or `failed` with reason `busy`), waited (the median of the ended
                    lines' `result.waited`, None before PZA/1.12), by_type {shove, stomp} each the same five}.
  idle_snap_by_act  x3's `idle_snap` frames (no melee running, a standing zombie within IDLE_SNAP_R) split by the
                    frame's act (its type when the act is accepted or in progress, else "none"; a running act of an
                    unlisted aid "unknown"), each with x2's summary of the body's error; {read, frames, by_act}.
  frame_age         the decision lines carrying the line's own `frame_age` (Task 5's stale frame, survive.py); {read,
                    lines, median, max}.
  group_leave_legs  the frozen x3 reader's vocabulary folded in (CLAUDE.md section 4, "A frozen reader's vocabulary":
                    x3's `group_leave` counts `walkTo` and `steer` legs by the action sent): the lines whose threat why
                    carries `group_leave`, their `leg` values counted {shove, door, retreat, run, ...} and their `end`
                    values {strung, ...}; {read, lines, legs, ends}.
  drag_fight        likewise for x3's `drag_guard` (Plan 33 fix 2 wrote `drag_fight`): the lines whose threat why
                    carries `drag_fight`, by its `why` {hit, stuck, ...}, and `spent` the lines carrying `spent`.

The why keys are the spec's (`docs/superpowers/specs/2026-11-09-plan-34-the-column-design.md` section 3) and are read by
key with x3's `carries` and `value_of`, so a key nested in a policy's why is read where it sits.

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; the scorecard's `retreat_gap`
is copied here as a frozen copy (tools/trial_score.py at 35fc4bb9) over x1's frozen `line_minutes` and `_gap`;
`grades.x3`, `grades.x2` and `grades.x1` (frozen, pinned by their regrade tests) and the shared readers of `gates_e` are
its only imports."""
import math
import statistics

from agent.base import gates_e as E
from agent.base.grades import x1 as GX1
from agent.base.grades import x2 as GX2
from agent.base.grades import x3 as GX3
from agent.base.grades.x3 import carries, sent_action, standing, threat_why, value_of

# Frozen copies of the live names read here (P26-Q), each with its source.
CARE = "care"              # planner/survive.py BRANCHES: the care branch's name, a decision line's `branch`
CARE_SENDS = ("stop", "rip", "unwear")   # planner/maneuvers/dress.py's commands but the bandage (x1's DRESS_SENDS)
BANDAGE = "bandage"        # schema actionType
KEEP_MOVING = "keepMoving"   # the bandage's arg (P24-U's ride: the dressing on the move)
MELEE = "melee"            # schema actionType (PZA/1.8)
AIM = "aim"                # schema actionType: the stance leg
SHOVE = "shove"            # schema actionType
STOMP = "stomp"            # schema actionType
INTERACT = "interact"      # schema actionType
CLOSE = "close"            # the interact's `kind` that shuts a door
DOOR = "door"              # planner/group.py `_leave_leg`: the leave's door leg
RETREAT = "retreat"        # planner/group.py `_leave_leg`: the fighting retreat's leg
OUTSIDE = "outside"        # Plan 34 spec section 3.2: the shelter's enter read off a room square
CARE_WITHHELD = "care_withheld"   # spec section 3.1: LEAVE_CARE's why key
GROUP_LEAVE = "group_leave"       # planner/group.py: GROUP_LEAVE's why key
GROUP_RETREAT = "group_retreat"   # planner/group.py: the retreat's why key
DOOR_REFUSED = "door_refused"     # spec section 3.2: LEAVE_DOOR_RACE's withheld pick ("race" | "one_exit")
DOOR_DROPPED = "door_dropped"     # spec section 3.2: LEAVE_DOOR_RACE's abort
STRUNG_N = "strung_n"             # spec section 3.3: STRUNG_HOLD's count
RETREAT_LEG = "retreat_leg"       # planner/fight.py `_retreat_leg` (kind from spec section 3.3)
RETREAT_BREAK = "retreat_break"   # spec section 3.3: RETREAT_MELEE's give-way
DRAG_FIGHT = "drag_fight"         # planner/group.py (Plan 33 Task 3 fix 2): the drag guard's why key
SPENT = "spent"                   # ... its spent shoves
SHELTER = "shelter"               # planner/flee.py `_shelter`: the Flee's shelter why (the building)
ENDED = "ended"                   # ... the step's end (spec section 3.2: "outside")
REFUSED = "refused"               # ... the close refused (spec section 3.2: "outside" | "guarded")
FRAME_AGE = "frame_age"           # planner/survive.py `_apply` (Plan 34 Task 5): the stale frame's age
WAITED = "waited"                 # PZAgent_Stance.lua (Plan 34 Task 4, PZA/1.12): the ticks a shove or stomp waited
ATTACK_STARTED = "attackStarted"  # the shove's and stomp's result (PZAgent_SkillsWorld.lua)
BUSY = "busy"                     # K.attackBusy's refusal reason
BUSY_STATES = ("rejected", "failed")   # the act states a busy refusal ends in (before and after Task 4)
END_STATES = ("done", "failed")        # the act states that end a sent act
LIVE_STATES = ("accepted", "progress")   # a frame's act state while the act runs (PZAgent_Skills.lua's K.status)
LEAVE_LEGS = ("shove", "door", "retreat", "run")   # planner/group.py `_leave_leg`
LEAVE_ENDS = ("strung",)                           # planner/group.py `_group_leave`
DRAG_WHYS = ("hit", "stuck")                       # planner/group.py: the drag guard's whys
RETREAT_KINDS = ("stand", "back")                  # spec section 3.3: the retreat leg's kinds
REFUSALS = ("race", "one_exit")                    # spec section 3.2
GROUP_LEAVE_N = 3          # planner/policies.py GROUP_LEAVE_N (Plan 33 Task 3 fix 3), a frozen copy
GROUP_ENTRY_R = 6.0        # tiles: planner/policies.py GROUP_ENTRY_R (Plan 33 Task 3 fix 1), a frozen copy
GAP_CLOSE = 0.6            # tiles: tools/trial_score.py GAP_CLOSE (35fc4bb9), a frozen copy
IDLE_SNAP_R = 2.5          # tiles: grades.x3 IDLE_SNAP_R (PZAgent_StanceMelee.lua K.IDLE_SNAP_R)
NONE_ACT = "none"          # a frame with no act running
UNKNOWN_ACT = "unknown"    # a running act whose aid no act line types
NEW = ("care_withheld", "care_at_group", "door_leave", "retreat", "shoves", "idle_snap_by_act", "frame_age",
       "group_leave_legs", "drag_fight")
N_LINES = len(NEW)         # the report lines lines_x4 appends: one per NEW key


# ---------------------------------------------------------------- shared readers
def owner(why, key):
    """The first dict in `why` (its own keys first, then its values in order, lists included) holding `key`, else
    None."""
    if isinstance(why, dict):
        if key in why:
            return why
        for v in why.values():
            o = owner(v, key)
            if o is not None:
                return o
    if isinstance(why, list):
        for v in why:
            o = owner(v, key)
            if o is not None:
                return o
    return None


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _count(keys, vals):
    """{key: count} with every name of `keys` first (0 when unseen), then any other value seen, in first-seen order."""
    out = {k: 0 for k in keys}
    for v in vals:
        out[v] = out.get(v, 0) + 1
    return out


def square_at(frame):
    """The frame's player square (x, y, z) floored, else None."""
    me = GX2._pos(GX2._me(frame))
    if me is None:
        return None
    z = _num(GX2._me(frame).get("z"))
    return int(math.floor(me[0])), int(math.floor(me[1])), int(math.floor(z)) if z is not None else 0


def map_lines(lines):
    """The state log's map lines with a `wallMs`, in wall order."""
    return sorted((ln for ln in E._l(lines) if isinstance(ln, dict) and ln.get("kind") == "map"
                   and _num(ln.get("wallMs")) is not None), key=lambda ln: ln["wallMs"])


def record_at(maps, sq, wall_ms):
    """The square record of `sq` the map lines last wrote at or before `wall_ms`, else None."""
    rec = None
    for ln in maps:
        if ln["wallMs"] > wall_ms:
            break
        for s in E._l(ln.get("squares")):
            s = E._d(s)
            if (s.get("x"), s.get("y"), s.get("z") or 0) == sq:
                rec = s
    return rec


def on_room(s, building):
    """The square record `s` is a room square (of `building` when one is named)."""
    return s.get("room") is not None and (building is None or s.get("building") == building)


# ---------------------------------------------------------------- the frozen copy of the scorecard's retreat gap
def retreat_gap(rows):
    """tools/trial_score.py `retreat_gap` at 35fc4bb9, a frozen copy: {lines, minutes, min, median, closed, read} over
    the decision lines whose threat why carries `group_retreat` with `leg` "retreat": `nearest` their `inputs.nearest`
    readings (None skipped), `min` and `median` of them, `closed` the lines reading under GAP_CLOSE, `minutes` their game
    minutes to the next line; `read` False with no such line."""
    gm = GX1.line_minutes(rows)
    out = {"lines": 0, "minutes": 0.0, "min": None, "median": None, "closed": 0, "read": False}
    ds = []
    for i, r in enumerate(rows):
        gr = E._d(E._bw(r, "threat").get("group_retreat"))
        if gr.get("leg") != "retreat":
            continue
        out["lines"] += 1
        if i + 1 < len(rows):
            out["minutes"] += GX1._gap(gm[i], gm[i + 1])
        d = E._n(E._d(r.get("inputs")).get("nearest"))
        if d is not None:
            ds.append(d)
            if d < GAP_CLOSE:
                out["closed"] += 1
    if ds:
        ds.sort()
        out.update(min=ds[0], median=ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2.0)
    out["read"] = out["lines"] > 0
    return out


# ---------------------------------------------------------------- the readings
def e_care_withheld(rows):
    """The care_withheld reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    n, by_n, keys = 0, {}, []
    for r in E._l(rows):
        if not carries(threat_why(r), CARE_WITHHELD):
            continue
        n += 1
        w = E._d(value_of(threat_why(r), CARE_WITHHELD))
        by_n[str(w.get("n"))] = by_n.get(str(w.get("n")), 0) + 1
        k = w.get("key")
        if k is not None and k not in keys:
            keys.append(k)
    return {"read": True, "lines": n, "by_n": dict(sorted(by_n.items())), "keys": keys}


def e_care_at_group(rows, lines):
    """The care_at_group reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    index = E._frame_index(lines)
    out = []
    for i, r in enumerate(E._l(rows)):
        r = E._d(r)
        if r.get("branch") != CARE:
            continue
        typ, args = sent_action(r)
        if not (typ in CARE_SENDS or (typ == BANDAGE and args.get(KEEP_MOVING) is not True)):
            continue
        f = E._frame_at(index, E._n(r.get("wall")))
        n = len(standing(f, GROUP_ENTRY_R)) if f is not None else None
        if n is not None and n >= GROUP_LEAVE_N:
            out.append({"i": i, "type": typ, "standing": n})
    return {"read": True, "lines": len(out), "rows": out}


def e_door_leave(rows, lines):
    """The door_leave reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    rows = E._l(rows)
    index, maps = E._frame_index(lines), map_lines(lines)
    runs, cur, refused, aborts, enters = [], [], [], 0, 0
    closes = {"sent": 0, "inside": 0, "refused": 0, "refused_by": {}, "unread": 0}
    for i, r in enumerate(rows):
        why = threat_why(r)
        gl = E._d(value_of(why, GROUP_LEAVE))
        if gl.get("leg") == DOOR:
            if cur and cur[-1] != i - 1:
                runs.append(cur)
                cur = []
            cur.append(i)
        if gl.get(DOOR_REFUSED) is not None:
            refused.append(gl.get(DOOR_REFUSED))
        if carries(gl, DOOR_DROPPED):
            aborts += 1
        sh = owner(why, SHELTER) or {}
        if sh.get(ENDED) == OUTSIDE:
            enters += 1
        if isinstance(sh.get(REFUSED), str):
            closes["refused"] += 1
            closes["refused_by"][sh[REFUSED]] = closes["refused_by"].get(sh[REFUSED], 0) + 1
        typ, args = sent_action(r)
        if typ != INTERACT or args.get("kind") != CLOSE:
            continue
        closes["sent"] += 1
        wall = E._n(E._d(r).get("wall"))
        f = E._frame_at(index, wall)
        sq = square_at(f) if f is not None else None
        s = record_at(maps, sq, wall * 1000.0) if sq is not None else None
        if s is None:
            closes["unread"] += 1
            continue
        b = value_of(why, SHELTER)
        closes["inside"] += 1 if on_room(s, b if _num(b) is not None else None) else 0
    if cur:
        runs.append(cur)
    picks = 0
    for run in runs:
        if not any(sent_action(rows[i])[0] for i in run):
            continue
        picks += 1
    return {"read": True, "lines": sum(len(run) for run in runs), "picks": picks, "refused": _count(REFUSALS, refused),
            "aborts": aborts, "enters_outside": enters, "closes": closes}


def e_retreat(rows):
    """The retreat reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    rows = E._l(rows)
    n, kinds, melees, breaks, holds = 0, [], 0, 0, 0
    for r in rows:
        why = threat_why(r)
        if carries(why, RETREAT_BREAK):
            breaks += 1
        gl = E._d(value_of(why, GROUP_LEAVE))
        if carries(gl, STRUNG_N):
            holds += 1
        gr = E._d(value_of(why, GROUP_RETREAT))
        if gr.get("leg") != RETREAT:
            continue
        n += 1
        k = E._d(value_of(why, RETREAT_LEG)).get("kind")
        if k is not None:
            kinds.append(k)
        typ, _ = sent_action(r)
        if typ == MELEE:
            melees += 1
    by_kind = _count(RETREAT_KINDS, kinds)
    by_kind[MELEE] = by_kind.get(MELEE, 0) + melees
    return {"read": True, "lines": n, "by_kind": by_kind, "breaks": breaks, "strung_holds": holds,
            "gap": retreat_gap(rows)}


def _shove_block(acts):
    """{sent, done, started, busy, waited} over `acts` ({aid: [act line]}: the shoves' and stomps')."""
    done = started = busy = 0
    waited = []
    for lns in acts.values():
        for ln in lns:
            res, st = E._d(ln.get("result")), ln.get("state")
            if st == "done":
                done += 1
                started += 1 if res.get(ATTACK_STARTED) is True else 0
            if st in BUSY_STATES and ln.get("reason") == BUSY:
                busy += 1
            if st in END_STATES and _num(res.get(WAITED)) is not None:
                waited.append(res.get(WAITED))
    return {"sent": len(acts), "done": done, "started": started, "busy": busy,
            "waited": statistics.median(waited) if waited else None}


def e_shoves(lines):
    """The shoves reading (the module docstring)."""
    acts = [ln for ln in E._l(lines) if isinstance(ln, dict) and ln.get("kind") == "act"]
    if not acts:
        return {"read": False}
    by = {}
    for ln in acts:
        if ln.get("type") in (SHOVE, STOMP):
            by.setdefault(ln.get("type"), {}).setdefault(ln.get("aid"), []).append(ln)
    out = _shove_block({(t, aid): lns for t, d in by.items() for aid, lns in d.items()})
    out = dict({"read": True}, **out)
    out["by_type"] = {t: _shove_block(by.get(t, {})) for t in (SHOVE, STOMP)}
    return out


def e_idle_snap_by_act(lines, frames):
    """The idle_snap_by_act reading (the module docstring): x3's `e_idle_snap` frames, split."""
    if not any(E._n(GX2._me(f).get("bodyAngle")) is not None for f in frames):
        return {"read": False}
    types = GX2.act_types(lines)
    errs, n = {}, 0
    for f in frames:
        act = E._d(f.get("act"))
        if types.get(act.get("aid")) == MELEE and act.get("state") in LIVE_STATES:
            continue
        near = standing(f, IDLE_SNAP_R)
        if not near:
            continue
        n += 1
        key = (types.get(act.get("aid")) or UNKNOWN_ACT) if act.get("state") in LIVE_STATES else NONE_ACT
        me, p = GX2._pos(GX2._me(f)), GX2._pos(near[0][1])
        b = math.atan2(p[1] - me[1], p[0] - me[0]) if p != me else None
        errs.setdefault(key, []).append(GX2._err(f, "bodyAngle", b))
    return {"read": True, "frames": n, "by_act": {k: GX2.summary(v) for k, v in errs.items()}}


def e_frame_age(rows):
    """The frame_age reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    ages = [a for a in (_num(E._d(r).get(FRAME_AGE)) for r in E._l(rows)) if a is not None]
    return {"read": True, "lines": len(ages), "median": statistics.median(ages) if ages else None,
            "max": max(ages) if ages else None}


def e_group_leave_legs(rows):
    """The group_leave_legs reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    n, legs, ends = 0, {k: 0 for k in LEAVE_LEGS}, {k: 0 for k in LEAVE_ENDS}
    for r in E._l(rows):
        why = threat_why(r)
        if not carries(why, GROUP_LEAVE):
            continue
        n += 1
        gl = E._d(value_of(why, GROUP_LEAVE))
        leg, end = gl.get("leg"), gl.get("end")
        if leg is not None:
            legs[leg] = legs.get(leg, 0) + 1
        if end is not None:
            ends[end] = ends.get(end, 0) + 1
    return {"read": True, "lines": n, "legs": legs, "ends": ends}


def e_drag_fight(rows):
    """The drag_fight reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    n, whys, spent = 0, [], 0
    for r in E._l(rows):
        why = threat_why(r)
        if not carries(why, DRAG_FIGHT):
            continue
        n += 1
        df = E._d(value_of(why, DRAG_FIGHT))
        if df.get("why") is not None:
            whys.append(df.get("why"))
        if carries(df, SPENT):
            spent += 1
    return {"read": True, "lines": n, "by_why": _count(DRAG_WHYS, whys), "spent": spent}


def readings_x4(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`), over the sources clipped at the loop's stop (`x1.clip`)."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    return {"care_withheld": e_care_withheld(rows), "care_at_group": e_care_at_group(rows, lines),
            "door_leave": e_door_leave(rows, lines), "retreat": e_retreat(rows), "shoves": e_shoves(lines),
            "idle_snap_by_act": e_idle_snap_by_act(lines, frames), "frame_age": e_frame_age(rows),
            "group_leave_legs": e_group_leave_legs(rows), "drag_fight": e_drag_fight(rows)}


def care_cell(out, decision_lines, lines):
    """The scorecard's `care@3+` (tools/trial_score.py): care_at_group's lines over the clipped sources, None when
    unread."""
    _, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    c = e_care_at_group(rows, lines)
    return c.get("lines") if c.get("read") else None


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=3):
    return round(v, n) if isinstance(v, float) else v


def lines_x4(g):
    """One report line per new reading (`NEW`), each clause marked reading or inference."""
    cw, cg, dl, rt, sh, idle, fa, gl, df = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append("care withheld (threat why %s) [reading]: %s lines, by n %s, keys %s" % (
        CARE_WITHHELD, cw.get("lines"), cw.get("by_n"), cw.get("keys")) if cw.get("read")
        else GX1._unread("care withheld"))
    out.append("care at group (care sends %s, or a bandage without %s, with %s or more standing within %s tiles) "
               "[reading]: %s lines %s" % (
                   "/".join(CARE_SENDS), KEEP_MOVING, GROUP_LEAVE_N, GROUP_ENTRY_R, cg.get("lines"),
                   [(r["i"], r["type"], r["standing"]) for r in E._l(cg.get("rows"))])
               if cg.get("read") else GX1._unread("care at group"))
    if dl.get("read"):
        c = E._d(dl.get("closes"))
        out.append("door leave (group_leave leg door, %s, %s; the shelter why) [reading]: %s door lines, %s picks, "
                   "refused %s, %s aborts, %s enters ended outside; closes %s sent, %s refused %s; [inference] %s "
                   "closes sent on a room square of the plan's building, %s unread" % (
                       DOOR_REFUSED, DOOR_DROPPED, dl.get("lines"), dl.get("picks"), dl.get("refused"),
                       dl.get("aborts"), dl.get("enters_outside"), c.get("sent"), c.get("refused"),
                       c.get("refused_by"), c.get("inside"), c.get("unread")))
    else:
        out.append(GX1._unread("door leave"))
    if rt.get("read"):
        gp = E._d(rt.get("gap"))
        out.append("retreat (group_retreat leg retreat) [reading]: %s lines, by kind %s, %s breaks (%s), %s strung "
                   "holds (%s); the gap: nearest min %s median %s, %s lines under %s" % (
                       rt.get("lines"), rt.get("by_kind"), rt.get("breaks"), RETREAT_BREAK, rt.get("strung_holds"),
                       STRUNG_N, _r(gp.get("min")), _r(gp.get("median")), gp.get("closed"), GAP_CLOSE))
    else:
        out.append(GX1._unread("retreat"))
    out.append("shoves (shove and stomp acts) [reading]: %s sent, %s done, %s started, %s busy, waited median %s; by "
               "type (sent, busy, done, started) %s" % (sh.get("sent"), sh.get("done"), sh.get("started"), sh.get("busy"), sh.get("waited"),
                            {t: (v.get("sent"), v.get("busy"), v.get("done"), v.get("started"))
                             for t, v in E._d(sh.get("by_type")).items()})
               if sh.get("read") else GX1._unread("shoves"))
    out.append("idle snap by act (x3's idle frames by the frame's act) [reading]: %s frames, %s" % (
        idle.get("frames"), {k: GX2._s(v) for k, v in E._d(idle.get("by_act")).items()})
               if idle.get("read") else "idle snap by act: no frame reads me.bodyAngle")
    out.append("frame age (the line's %s, seconds) [reading]: %s lines, median %s, max %s" % (
        FRAME_AGE, fa.get("lines"), fa.get("median"), fa.get("max")) if fa.get("read")
        else GX1._unread("frame age"))
    out.append("group leave legs (threat why %s by leg and end) [reading]: %s lines, legs %s, ends %s" % (
        GROUP_LEAVE, gl.get("lines"), gl.get("legs"), gl.get("ends")) if gl.get("read")
        else GX1._unread("group leave legs"))
    out.append("drag fight (threat why %s) [reading]: %s lines, by why %s, %s spent" % (
        DRAG_FIGHT, df.get("lines"), df.get("by_why"), df.get("spent")) if df.get("read")
        else GX1._unread("drag fight"))
    return out


def report_lines_x4(g):
    """grade_x3's report lines (`report_lines_x3`), its gate line naming gate_x4, then `lines_x4`."""
    g = E._d(g)
    base = GX3.report_lines_x3(g)
    return [("gate_x4 " + ln[len("gate_x3 "):]) if ln.startswith("gate_x3 ") else ln for ln in base] + lines_x4(g)


def grade_x4(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x3` under "grade_x4" (`base` "grade_x3", `base_x3` x3's own base, x3's nesting kept) with the column
    readings (`readings_x4`), over the state lines of `state_dir` unless `lines` is given (read once and handed down);
    its report lines `report_lines_x4`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX3.grade_x3(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x3"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x4"
    g.update(readings_x4(record, decision_lines, lines))
    g["report_lines"] = report_lines_x4(g)
    return g


def gate_x4(outs):
    """gate_x3 (grade_x4 changes none of what it reads), named gate_x4."""
    return GX3.gate_x3(outs)
