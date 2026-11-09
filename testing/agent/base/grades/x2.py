"""grades.x2 -- the facing grade (Plan 32 Task 4; the facing trials' ruling: the snap, PZAgent_StanceMelee.lua's
K.FACING): `grade_x2` is `grades.x1.grade_x1` under "grade_x2", with "grade_x1" in `base` and the x1 grade's own base
(grade_f12 for an LLM session, grade_e21 for a chain one) in `base_x1`, plus two readings of the facing off the frames'
`me.bodyAngle` (the engine's body angle, getAnimAngleRadians, PZA/1.10 on) and the facing ring (`me.fwdAngle`,
`me.aimAngle`, PZA/1.11 on; null before), each over the sources clipped at the loop's stop (`x1.clip`):

  facing_body   the body's error against the bearing to the target, in degrees wrapped to (-180, 180] and read
                absolute: per press (the melee act lines' presses: a line whose step is a press, PRESS_STEPS, new
                where the aid's step changed into it or the line carries the previous press's leaf), at the frame at
                or before the press's wallMs, `err_body` and `err_look` (`me.lookAngle`), summarised over every press,
                by kind (swing, shove, stomp, floor) and by the press mode the press's own leaf names (`facing`, the
                leaf on the aid's next line carrying one; `unnamed` before Task 4's Lua); per stance tick (the frames
                whose act is an `aim` leg's or a `melee` span's, accepted or in progress), the error series' median,
                90th percentile (nearest rank) and `hold30` (the share under HOLD_DEG), over every tick and by the
                act's type; the breaks: the runs of consecutive stance frames over BREAK_DEG, each with its first and
                last seq, its length, its largest error, the act (aid, type, step) on its first frame and the action
                sent last before it (the decision line with `sent` true at or before the first frame's wall: its
                branch, type, the seconds before the run and the args AIM_ARGS names).
  facing_ring   over the stance frames reading `me.fwdAngle` (the forward direction the engine moves the body
                toward): the share with it within RING_DEG of `me.aimAngle` (the mouse won), of the walk vector (the
                frame's movement direction from the previous frame's position, on frames moving more than MOVE_EPS
                tiles) and of the bearing to the target (the Lua's write held), each with its denominator; null
                shares (read False) on a log without the ring (PZA/1.10 and before).

The target a frame or a press is read against: the act's own zombie (an aim's `targetId`, else its `bearing` in
degrees, 0 east and 90 south; a melee's `targetId` off the record's `loop.actions`, re-pinned to the act line's
`target` from the first line carrying it, Task 15a), found in the frame's zombie list; else the nearest standing zombie
within FACING_R tiles of the player; else none (the frame or the press unread). A finish's press (floor, stomp) under
`headAim` reads the zombie record's head estimate (`headX`, `headY`) where the frame carries one. The bearing is
atan2(dy, dx) against the angles' own convention (the probe's: Vector2.getDirection, world x and y).

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; `grades.x1` (frozen, pinned by
its regrade tests) and the shared readers of `gates_e` are its only imports."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.grades import x1 as GX1

# Frozen copies of the live names read here (P26-Q), each with its source.
MELEE = "melee"         # the reflex's type (schema actionType, PZA/1.8)
AIM = "aim"             # the stance leg's type (schema actionType, PZA/1.5)
PRESS_STEPS = ("swing", "shove", "stomp", "floor")   # planner/maneuvers/melee.py STRIKE_STEPS (the Lua's presses)
FINISH_KINDS = ("floor", "stomp")   # PZAgent_StanceMelee.lua (rule 4): the finish's presses at a fallen target
LIVE_STATES = ("accepted", "progress")   # a frame's act state while the act runs (PZAgent_Skills.lua's K.status)
FACING_KEY = "facing"   # PZAgent_StanceMelee.lua's press leaf (Plan 32 Task 4): the press mode
TARGET = "target"       # PZAgent_StanceMelee.lua's header (Task 15a): the zombie now pressed after a re-pin
AIM_ARGS = ("targetId", "bearing", "vx", "vy", "seconds", "mode", "gait")   # the args a break's sent action prints
# The grade's own numbers.
FACING_R = 1.5          # tiles: with no named target, the nearest standing zombie within this is the one faced
HOLD_DEG = 30.0         # degrees: the hold share's bound (the facing trials' hold30, PZAgent_FacingProbe.lua)
BREAK_DEG = 45.0        # degrees: a stance frame over this is in a break (the frozen `facing` block's 45 degree point)
RING_DEG = 10.0         # degrees: the forward direction within this of a vector is on it
MOVE_EPS = 0.02         # tiles a frame: a frame moving less has no walk vector (a 10 Hz frame of the slowest walk
                        # covers several times it)
UNNAMED = "unnamed"     # a press whose leaf names no mode (the Lua before Task 4)
NEW = ("facing_body", "facing_ring")
N_LINES = len(NEW)      # the report lines lines_x2 appends: one per NEW key


# ---------------------------------------------------------------- the angles
def wrap_deg(r):
    """Radians `r` in degrees wrapped to (-180, 180]."""
    d = math.degrees(r)
    while d > 180.0:
        d -= 360.0
    while d <= -180.0:
        d += 360.0
    return d


def _rank(vals, q):
    """The nearest-rank `q` quantile (ceil(q n), PZAgent_FacingProbe.lua's) of `vals`, None when empty."""
    s = sorted(vals)
    if not s:
        return None
    return s[max(1, math.ceil(q * len(s))) - 1]


def summary(errs):
    """{n, median, p90, hold30} of the absolute errors `errs` (degrees; None dropped): the nearest-rank median and
    90th percentile and the share under HOLD_DEG; {n: 0} without one."""
    xs = [abs(x) for x in errs if isinstance(x, (int, float)) and not isinstance(x, bool)]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "median": _rank(xs, 0.5), "p90": _rank(xs, 0.9),
            "hold30": sum(1 for x in xs if x < HOLD_DEG) / len(xs)}


def _me(f):
    return E._d(E._d(f).get("me"))


def _pos(rec):
    x, y = E._n(E._d(rec).get("x")), E._n(E._d(rec).get("y"))
    return (x, y) if x is not None and y is not None else None


# ---------------------------------------------------------------- the acts and their targets
def act_types(lines):
    """{aid: type} of every act line."""
    out = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("aid") is not None and ln.get("type"):
            out.setdefault(ln.get("aid"), ln.get("type"))
    return out


def act_args(out):
    """{aid: args} of the record's `loop.actions`."""
    return {a.get("aid"): E._d(a.get("args")) for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get(
        "actions")))}


def repins(lines):
    """{aid: ([wallMs], [target])} of the melee act lines carrying `target` (the reflex's re-pin), in wall order."""
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == MELEE:
            t, w = E._d(ln.get("result")).get(TARGET), E._n(ln.get("wallMs"))
            if t is not None and w is not None:
                by.setdefault(ln.get("aid"), []).append((w, t))
    return {aid: ([w for w, _ in sorted(v, key=lambda p: p[0])], [t for _, t in sorted(v, key=lambda p: p[0])])
            for aid, v in by.items()}


def _target_id(aid, wall, args, pins):
    """The zombie the act at `aid` faces at `wall`: the re-pin's target from its line on, else the args' targetId."""
    ws, ts = pins.get(aid, ([], []))
    i = bisect.bisect_right(ws, wall) - 1 if wall is not None else -1
    if i >= 0:
        return ts[i]
    tid = E._n(args.get("targetId"))
    return tid if tid is not None and tid >= 0 else None


def _nearest(frame, me):
    """The nearest standing zombie record within FACING_R of the player, else None."""
    best = None
    for z in E._l(E._d(frame).get("zombies")):
        z = E._d(z)
        p = _pos(z)
        if p is None or z.get("onFloor") is True:
            continue
        d = math.hypot(p[0] - me[0], p[1] - me[1])
        if d <= FACING_R and (best is None or d < best[0]):
            best = (d, z)
    return best[1] if best else None


def bearing(frame, typ, args, tid, head=False):
    """The bearing in radians from the frame's player to the act's target (the module docstring), else None."""
    me = _pos(_me(frame))
    if me is None:
        return None
    rec = None
    if tid is not None:
        rec = next((E._d(z) for z in E._l(E._d(frame).get("zombies")) if E._d(z).get("id") == tid), None)
    if rec is None and typ == AIM:
        b = E._n(args.get("bearing"))
        if tid is None and b is not None and b >= 0:
            return math.radians(b)
    if rec is None:
        rec = _nearest(frame, me)
    if rec is None:
        return None
    p = _pos(rec)
    if head and E._n(rec.get("headX")) is not None and E._n(rec.get("headY")) is not None:
        p = (E._n(rec.get("headX")), E._n(rec.get("headY")))
    if p is None or (p[0] == me[0] and p[1] == me[1]):
        return None
    return math.atan2(p[1] - me[1], p[0] - me[0])


def _err(frame, key, b):
    a = E._n(_me(frame).get(key))
    return wrap_deg(a - b) if a is not None and b is not None else None


# ---------------------------------------------------------------- the presses
def press_rows(out, lines, index):
    """[{aid, seq, wallMs, kind, mode, frame_seq, err_body, err_look}] of every press (the module docstring), in log
    order; `index` the frames' ([wallMs], [frame])."""
    args, pins = act_args(out), repins(lines)
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == MELEE:
            by.setdefault(ln.get("aid"), []).append(ln)
    rows = []
    for aid, lns in by.items():
        prev, mine = None, []
        for k, ln in enumerate(lns):
            res = E._d(ln.get("result"))
            step = res.get("step")
            if step in PRESS_STEPS and (step != prev or isinstance(res.get("press"), dict)):
                mine.append((k, ln, step))
            if step is not None:
                prev = step
        for k, ln, step in mine:
            leaf = next((E._d(E._d(x.get("result")).get("press")) for x in lns[k + 1:]
                         if isinstance(E._d(x.get("result")).get("press"), dict)), {})
            w = E._n(ln.get("wallMs"))
            i = bisect.bisect_right(index[0], w) - 1 if w is not None else -1
            f = index[1][i] if i >= 0 else None
            a = args.get(aid, {})
            b = bearing(f, MELEE, a, _target_id(aid, w, a, pins),
                        head=step in FINISH_KINDS and a.get("headAim") is True) if f is not None else None
            rows.append({"aid": aid, "seq": ln.get("seq"), "wallMs": w, "kind": step,
                         "mode": leaf.get(FACING_KEY) or UNNAMED, "frame_seq": E._d(f).get("seq"),
                         "err_body": _err(f, "bodyAngle", b), "err_look": _err(f, "lookAngle", b)})
    return sorted(rows, key=lambda r: (r["wallMs"] is None, r["wallMs"] or 0))


def _press_block(rows):
    def both(rs):
        return {"n": len(rs), "body": summary([r["err_body"] for r in rs]), "look": summary([r["err_look"] for r in rs])}

    out = both(rows)
    out["by_kind"] = {k: both([r for r in rows if r["kind"] == k]) for k in sorted({r["kind"] for r in rows})}
    out["by_mode"] = {m: both([r for r in rows if r["mode"] == m]) for m in sorted({r["mode"] for r in rows})}
    out["rows"] = rows
    return out


# ---------------------------------------------------------------- the stance ticks and the breaks
def stance_frames(out, lines, frames):
    """[(i, frame, type, b)] of the stance frames (an aim's or a melee's act accepted or in progress) in frame order,
    `b` the bearing to the act's target (None when unread)."""
    types, args, pins = act_types(lines), act_args(out), repins(lines)
    rows = []
    for i, f in enumerate(frames):
        act = E._d(f.get("act"))
        typ = types.get(act.get("aid"))
        if typ not in (AIM, MELEE) or act.get("state") not in LIVE_STATES:
            continue
        a = args.get(act.get("aid"), {})
        tid = _target_id(act.get("aid"), E._n(f.get("wallMs")), a, pins)
        rows.append((i, f, typ, bearing(f, typ, a, tid)))
    return rows


def _sent_before(rows, wall_ms):
    """The decision line sent last at or before `wall_ms`: {s_before, branch, type, args} (AIM_ARGS), else None."""
    best = None
    for r in E._l(rows):
        w = E._n(E._d(r).get("wall"))
        if r.get("sent") is True and w is not None and w * 1000.0 <= wall_ms and (best is None or w >= best[0]):
            best = (w, r)
    if best is None:
        return None
    a = E._d(best[1].get("action"))
    return {"s_before": (wall_ms - best[0] * 1000.0) / 1000.0, "branch": best[1].get("branch"), "type": a.get("type"),
            "args": {k: v for k, v in E._d(a.get("args")).items() if k in AIM_ARGS}}


def breaks(stance, types, decision_rows):
    """The runs of consecutive stance frames (by frame index) whose body error is over BREAK_DEG: [{seq0, seq1, n,
    max, aid, type, step, sent}] (`sent` the decision line sent last before the run's first frame)."""
    runs, cur = [], []
    for i, f, typ, b in stance:
        e = _err(f, "bodyAngle", b)
        if e is not None and abs(e) > BREAK_DEG and (not cur or cur[-1][0] == i - 1):
            cur.append((i, f, abs(e)))
            continue
        if cur:
            runs.append(cur)
            cur = []
        if e is not None and abs(e) > BREAK_DEG:
            cur.append((i, f, abs(e)))
    if cur:
        runs.append(cur)
    out = []
    for run in runs:
        f0 = run[0][1]
        act = E._d(f0.get("act"))
        w = E._n(f0.get("wallMs"))
        out.append({"seq0": f0.get("seq"), "seq1": run[-1][1].get("seq"), "n": len(run),
                    "max": max(e for _, _, e in run), "aid": act.get("aid"), "type": types.get(act.get("aid")),
                    "step": act.get("step"), "sent": _sent_before(decision_rows, w) if w is not None else None})
    return out


# ---------------------------------------------------------------- the readings
def e_facing_body(out, decision_rows, lines, frames):
    """The facing_body reading (the module docstring); {"read": False} without a frame reading `me.bodyAngle`."""
    if not any(E._n(_me(f).get("bodyAngle")) is not None for f in frames):
        return {"read": False}
    index = ([E._n(f.get("wallMs")) for f in frames], frames)
    presses = press_rows(out, lines, index)
    stance = stance_frames(out, lines, frames)
    types = act_types(lines)
    errs = [(typ, _err(f, "bodyAngle", b)) for _, f, typ, b in stance]
    by_type = {t: summary([e for tt, e in errs if tt == t]) for t in sorted({t for t, _ in errs})}
    br = breaks(stance, types, decision_rows)
    return {"read": True, "presses": _press_block(presses),
            "stance": {"frames": len(stance), "read": sum(1 for _, e in errs if e is not None),
                       "body": summary([e for _, e in errs]), "by_type": by_type},
            "breaks": {"n": len(br), "frames": sum(r["n"] for r in br), "rows": br}}


def _on(a, v):
    return a is not None and v is not None and abs(wrap_deg(a - v)) < RING_DEG


def e_facing_ring(out, lines, frames):
    """The facing_ring reading (the module docstring): {read, frames, aim, aim_n, walk, walk_n, bearing, bearing_n}
    (each share None at a zero denominator); read False with null shares without a stance frame reading fwdAngle."""
    stance = stance_frames(out, lines, frames)
    ring = [(i, f, b) for i, f, _, b in stance if E._n(_me(f).get("fwdAngle")) is not None]
    if not ring:
        return {"read": False, "frames": 0, "aim": None, "walk": None, "bearing": None}
    aim = walk = bear = 0
    aim_n = walk_n = bear_n = 0
    for i, f, b in ring:
        fwd = E._n(_me(f).get("fwdAngle"))
        a = E._n(_me(f).get("aimAngle"))
        if a is not None:
            aim_n += 1
            aim += _on(fwd, a)
        p, q = _pos(_me(f)), _pos(_me(frames[i - 1])) if i > 0 else None
        if p is not None and q is not None and math.hypot(p[0] - q[0], p[1] - q[1]) > MOVE_EPS:
            walk_n += 1
            walk += _on(fwd, math.atan2(p[1] - q[1], p[0] - q[0]))
        if b is not None:
            bear_n += 1
            bear += _on(fwd, b)
    return {"read": True, "frames": len(ring), "aim": aim / aim_n if aim_n else None, "aim_n": aim_n,
            "walk": walk / walk_n if walk_n else None, "walk_n": walk_n,
            "bearing": bear / bear_n if bear_n else None, "bearing_n": bear_n}


def readings_x2(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`), over the sources clipped at the loop's stop (`x1.clip`)."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    return {"facing_body": e_facing_body(out, rows, lines, frames), "facing_ring": e_facing_ring(out, lines, frames)}


def facing_cells(out, decision_lines, lines):
    """(median, p90) of the body error at the presses (`facing_body`'s), each None when unread: the scorecard's two
    columns (tools/trial_score.py)."""
    b = readings_x2(out, decision_lines, lines)["facing_body"]
    s = E._d(E._d(b.get("presses")).get("body")) if b.get("read") else {}
    return s.get("median"), s.get("p90")


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=1):
    return round(v, n) if isinstance(v, float) else v


def _s(s):
    s = E._d(s)
    return "n %s, median %s, p90 %s, hold30 %s" % (s.get("n"), _r(s.get("median")), _r(s.get("p90")),
                                                   _r(s.get("hold30"), 2)) if s.get("n") else "n 0"


def lines_x2(g):
    """One report line per new reading (`NEW`), each clause marked reading or inference."""
    fb, fr = E._d(g.get("facing_body")), E._d(g.get("facing_ring"))
    out = []
    if fb.get("read"):
        p, st, br = E._d(fb.get("presses")), E._d(fb.get("stance")), E._d(fb.get("breaks"))
        out.append("facing body (me.bodyAngle against the bearing to the target, degrees) [reading]: the presses %s "
                   "(the look %s), by kind %s, by mode %s; the stance ticks %s of %s frames read: %s, by type %s; "
                   "[inference] %s breaks over %s degrees (%s frames): %s" % (
                       _s(p.get("body")), _s(p.get("look")),
                       {k: _s(v.get("body")) for k, v in E._d(p.get("by_kind")).items()},
                       {k: _s(v.get("body")) for k, v in E._d(p.get("by_mode")).items()},
                       st.get("read"), st.get("frames"), _s(st.get("body")),
                       {k: _s(v) for k, v in E._d(st.get("by_type")).items()}, br.get("n"), BREAK_DEG,
                       br.get("frames"),
                       [(r["seq0"], r["n"], _r(r["max"]), r["type"], r["step"],
                         (E._d(r["sent"]).get("type"), _r(E._d(r["sent"]).get("s_before"))) if r["sent"] else None)
                        for r in E._l(br.get("rows"))]))
    else:
        out.append(GX1._unread("facing body"))
    if fr.get("read"):
        out.append("facing ring (me.fwdAngle within %s degrees) [reading]: %s stance frames; on the aim vector %s of "
                   "%s, on the walk vector %s of %s, on the bearing %s of %s" % (
                       RING_DEG, fr.get("frames"), _r(fr.get("aim"), 2), fr.get("aim_n"), _r(fr.get("walk"), 2),
                       fr.get("walk_n"), _r(fr.get("bearing"), 2), fr.get("bearing_n")))
    else:
        out.append("facing ring: no stance frame reads me.fwdAngle (a log before PZA/1.11), the shares null")
    return out


def report_lines_x2(g):
    """grade_x1's report lines over the x1 grade's own base (`base_x1`), its gate line naming gate_x2, then
    `lines_x2`."""
    g = E._d(g)
    base = GX1.report_lines_x1(dict(g, base=g.get("base_x1")))
    return [("gate_x2 " + ln[len("gate_x1 "):]) if ln.startswith("gate_x1 ") else ln for ln in base] + lines_x2(g)


def grade_x2(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x1` under "grade_x2" (`base` "grade_x1", `base_x1` its own base) with the facing readings
    (`readings_x2`), over the state lines of `state_dir` unless `lines` is given (read once and handed down); its
    report lines `report_lines_x2`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX1.grade_x1(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x1"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x2"
    g.update(readings_x2(record, decision_lines, lines))
    g["report_lines"] = report_lines_x2(g)
    return g


def gate_x2(outs):
    """gate_x1 (grade_x2 changes none of what it reads), named gate_x2."""
    return GX1.gate_x1(outs)
