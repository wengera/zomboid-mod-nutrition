"""grades.x7 -- the disposition grade (Plan 37 Task 4): `grade_x7` is `grades.x6.grade_x6` under "grade_x7", with
"grade_x6" in `base`, x6's own base ("grade_x5") in `base_x6`, and x6's nesting below it kept (`base_x5` "grade_x4",
`base_x4` "grade_x3", `base_x3` "grade_x2", `base_x2` "grade_x1", `base_x1` grade_f12 for an LLM session, grade_e21 for
a chain one; x6's eight readings, x5's five and x4's nine kept at the top level), plus five readings of the disposition
(the spec `docs/superpowers/specs/2026-11-12-plan-37-the-disposition-design.md` sections 3.1, 3.2 and 3.6), each over
the sources clipped at the loop's stop (`x1.clip`). The first four are the scorecard's crowd readers (tools/
trial_score.py `restart_readings`, `disp_readings`, `string_readings`, `release_readings`, Plan 37 Task 1b, at
46021a9f), copied with their counting rules, each with its rows; the minutes in contact are x5's `contact.seconds`
(`grades.x5.e_contact` over the same clipped sources):

  restarts    the work melees (a melee span, `e19._spans`, whose first progress line carries a `work` leaf, the
              scorecard's `engagements` rule, or one of whose act lines carries `args.workR`) whose terminal line reads
              `failed superseded`, whose last progress leaf's `work.gap` is a number under KEEP_R, and whose next act
              (the earliest `accepted` line of another aid at or after the terminal line, within RESTART_S) is not a
              melee: `n`, `per_contact_min` (n per minute of contact, None over none), `rows` [{aid, by (the next act's
              type), gap}]. A melee superseded by a melee is no restart (the re-send keeps the footwork's state), nor a
              supersede with no act after it inside RESTART_S. {read: False} with no work melee.
  disposition the decision lines whose threat why (`inputs.branches.threat`) carries `disposition` {from, to, why,
              dwell} (a transition's line only, each a change): `changes`, `per_contact_min`, `dwell_median` (over the
              numeric dwells), `by_to` {name: n} DISP_ORDER first (zero-filled) then any other in sorted order, `by_why`
              {why: n} in first-seen order, `rows` [{line (the decision line's index), from, to, why, dwell}].
              {read: False} with no such line.
  string      the melees' work leaves (`result.work`, a non-empty dict) reading `disposition`: `episodes` the runs of
              one melee's leaves reading "string" (a leaf reading another disposition ends one, a line with no work
              leaf does not); `turns` the leaves carrying `turn_for` {leader, gap2}, counted once while the heartbeat
              re-reads the same value; `turns_gap_ok` the turns whose `gap2` is STRING_GAP or more, `gap2` their
              values in order and `gap2_median`; `kills` the done lines reading `kill` true of the melees whose last
              leaf carrying `disposition` read "string"; `walk_lines` the leaves whose `step_for` reads "string" (each
              line). {read: False} with no leaf carrying `disposition`.
  safe_release (the key is not `release`, grade_e10's P25-M reading on a chain session) the melee sends (decision
              lines `sent` true whose action is a melee) whose args read `release` true (`asked`); the melee done
              lines reading `end` "handback" and `why` "released" with `safe` true (`safe`) or false (`bound`);
              `early` the asked lines after which a non-melee command was sent within EARLY_S before the hand-back
              (a `released` or `floor` done line) of the melee that line started (the first melee accepted at or after
              the asked line's wall; a melee never handed back by then, or none found, is early); `rows` [{line, aid,
              back (the hand-back's why, None without one), early}]. {read: False} without a decision log, or with no
              melee send whose args carry a boolean `release` and no `released` hand-back (the scorecard's rule: a
              run under PZA/1.16 sending `release` false reads asked 0).
  speeds      the tiles a second between consecutive frames whose walls lie more than MIN_DT_S and less than MAX_DT_S
              apart (a speed of MAX_TPS or more dropped as a teleport), the method of the controller's scratch reads
              (Plan 36 Task 4's zombie speeds; Plan 37's `me_speeds.py`): `me` the character's, grouped by the later
              frame's flags (`me_gait`: "walk", "run" or "sprint" while `moving`, "still" or "still_run" not, with
              "sneak_" before it while `sneaking` and "aimed_" before that while `aiming`; the sneak a group of its own
              as the scratch read it, since the sneaking walk is slower: on F22 the walk's median 2.08, the sneaking
              walk's 1.51); `zombies` each listed zombie's between the two frames that list its id, grouped "crawler"
              when the later frame reads it a crawler, else by its `state`; each group {n, median, p90} (p90 the sorted
              values' index int(0.9 n)), by n descending then name. {read: False} when every group holds under
              MIN_PAIRS.

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; the scorecard's readers are
copied (never imported: the scorecard is live). `grades.x6`, `grades.x5`, `grades.x1`, `e19._spans` and the shared
readers of `gates_e` are its only imports."""
import math
import statistics

from agent.base import gates_e as E
from agent.base.grades import e19 as G19
from agent.base.grades import x1 as GX1
from agent.base.grades import x5 as GX5
from agent.base.grades import x6 as GX6

# Frozen copies of the live names read here (P26-Q), each with its source.
MELEE = GX6.MELEE          # schema actionType (PZA/1.8), x5's copy
ACCEPTED = "accepted"      # the act line's state at the Lua's acceptance
DONE = "done"              # ... at a done end
FAILED = "failed"          # ... at a failed end
SUPERSEDED = "superseded"  # the failed line's reason when the planner sent another act (schema reason enum)
WORK = "work"              # the result's work leaf (PZA/1.13)
WORK_R = "workR"           # tools/trial_score.py:1089 restart_readings' args key (at 46021a9f): a melee sent under work
KEEP_R = 2.5               # tiles: tools/trial_score.py:1055 KEEP_R (at 46021a9f; planner/policies.py:134 KEEP_R)
STRING_GAP = 2.5           # tiles: tools/trial_score.py:1056 STRING_GAP (at 46021a9f; the spec's 3.2 STRING_GAP)
RESTART_S = 1.0            # seconds: tools/trial_score.py:1057 RESTART_S (at 46021a9f)
EARLY_S = 1.0              # seconds: tools/trial_score.py:1058 EARLY_S (at 46021a9f)
DISP_ORDER = ("hunt", "hold", "string", "break")   # tools/trial_score.py:1059 DISP_ORDER (at 46021a9f)
DISPOSITION = "disposition"   # the threat why's transition key and the work leaf's running disposition (spec 3.1, 3.2)
STRING = "string"          # the disposition, and work.step_for's walk under it (spec 3.3)
TURN_FOR = "turn_for"      # the work leaf's turn {leader, gap2} (spec 3.3)
RELEASE = "release"        # the melee's work argument (spec 3.1)
HANDBACK = "handback"      # the done result's `end` at a hand-back
RELEASED = "released"      # ... its `why` at the safe release (spec 3.1)
FLOOR = "floor"            # ... its `why` at the health floor
MIN_DT_S = 0.05            # seconds: the controller's scratch me_speeds.py (Plan 37's open): a frame pair this close
MAX_DT_S = 0.3             # ... or this far apart is not read (Plan 36 Task 4: "consecutive frames within 0.3 s")
MAX_TPS = 10.0             # tiles a second: ... a speed this fast or faster is a teleport, dropped
MIN_PAIRS = 30             # pairs: ... a group under this many the scratch does not print; every group under it: unread
CRAWLER = "crawler"        # the zombies' group of a crawler (the frame's zombie `crawler` flag)
NEW = ("restarts", "disposition", "string", "safe_release", "speeds")
N_LINES = len(NEW)         # the report lines lines_x7 appends: one per NEW key


# ---------------------------------------------------------------- shared readers
def _median(vals):
    return statistics.median(vals) if vals else None


def _per_min(n, contact_s):
    """`n` per minute of contact (tools/trial_score.py `_per_min`'s rate, as a number), None over none."""
    return n / (contact_s / 60.0) if contact_s else None


def _work_leaf(ln):
    """tools/trial_score.py `_work_leaf` (at 46021a9f), copied: the act line's work leaf when non-empty, else {}."""
    w = E._d(E._d(ln.get("result")).get(WORK))
    return w if w else {}


def _threat(r):
    """The decision line's threat why (`inputs.branches.threat`), else {}."""
    return E._d(E._d(E._d(E._d(r).get("inputs")).get("branches")).get("threat"))


# ---------------------------------------------------------------- the readings
def e_restarts(lines, contact_s):
    """The restarts reading (the module docstring): tools/trial_score.py `restart_readings` (at 46021a9f), copied, with
    the rows and the rate."""
    lines = [ln for ln in E._l(lines) if isinstance(ln, dict)]
    acts = [(E._n(ln.get("wallMs")), i, ln) for i, ln in enumerate(lines) if ln.get("kind") == "act"
            and ln.get("state") == ACCEPTED and E._n(ln.get("wallMs")) is not None]
    work_r = {ln.get("aid") for ln in lines if ln.get("kind") == "act" and ln.get("type") == MELEE
              and WORK_R in E._d(ln.get("args"))}
    rows, work = [], 0
    for s in G19._spans(lines):
        if not (s["aid"] in work_r or (s["progress"] and WORK in s["progress"][0][1])):
            continue
        work += 1
        t = E._d(s["terminal"])
        if t.get("state") != FAILED or t.get("reason") != SUPERSEDED or s["end"] is None:
            continue
        gap = E._n(E._d(E._d(s["progress"][-1][1]).get(WORK)).get("gap")) if s["progress"] else None
        if gap is None or gap >= KEEP_R:
            continue
        nxt = [(w, i, ln) for w, i, ln in acts
               if ln.get("aid") != s["aid"] and s["end"] <= w <= s["end"] + RESTART_S * 1000.0]
        if not nxt:
            continue
        by = min(nxt, key=lambda x: (x[0], x[1]))[2].get("type")
        if by != MELEE:
            rows.append({"aid": s["aid"], "by": by, "gap": gap})
    if not work:
        return {"read": False}
    return {"read": True, "n": len(rows), "per_contact_min": _per_min(len(rows), contact_s), "rows": rows}


def e_disposition(rows, contact_s):
    """The disposition reading (the module docstring): tools/trial_score.py `disp_readings` (at 46021a9f), copied, with
    the whys and the rows."""
    out, dwells, by_to, by_why = [], [], {}, {}
    for i, r in enumerate(E._l(rows)):
        d = _threat(r).get(DISPOSITION)
        if not isinstance(d, dict):
            continue
        v = E._n(d.get("dwell"))
        if v is not None:
            dwells.append(v)
        by_to[str(d.get("to"))] = by_to.get(str(d.get("to")), 0) + 1
        by_why[str(d.get("why"))] = by_why.get(str(d.get("why")), 0) + 1
        out.append({"line": i, "from": d.get("from"), "to": d.get("to"), "why": d.get("why"), "dwell": d.get("dwell")})
    if not out:
        return {"read": False}
    names = list(DISP_ORDER) + sorted(k for k in by_to if k not in DISP_ORDER)
    return {"read": True, "changes": len(out), "per_contact_min": _per_min(len(out), contact_s),
            "dwell_median": _median(dwells), "by_to": {k: by_to.get(k, 0) for k in names}, "by_why": by_why,
            "rows": out}


def e_string(lines):
    """The string reading (the module docstring): tools/trial_score.py `string_readings` (at 46021a9f), copied, with
    the walk lines."""
    episodes = turns = wide = kills = walks = 0
    gap2, seen = [], False
    for lns in GX1._melee_lines(lines).values():
        run, prev, last = False, None, None
        for ln in lns:
            w = _work_leaf(ln)
            if not w:
                continue
            d = w.get(DISPOSITION)
            if d is not None:
                seen = True
                if d == STRING and not run:
                    episodes += 1
                run = d == STRING
            last = d if d is not None else last
            walks += 1 if w.get("step_for") == STRING else 0
            t = w.get(TURN_FOR)
            if isinstance(t, dict) and t != prev:
                turns += 1
                g = E._n(t.get("gap2"))
                if g is not None:
                    gap2.append(g)
                    wide += 1 if g >= STRING_GAP else 0
            prev = t if isinstance(t, dict) else None
        done = [ln for ln in lns if ln.get("state") == DONE and E._d(ln.get("result")).get("kill") is True]
        kills += len(done) if last == STRING else 0
    if not seen:
        return {"read": False}
    return {"read": True, "episodes": episodes, "turns": turns, "turns_gap_ok": wide, "gap2": gap2,
            "gap2_median": _median(gap2), "kills": kills, "walk_lines": walks}


def e_release(rows, lines):
    """The release reading (the module docstring): tools/trial_score.py `release_readings` (at 46021a9f), copied, with
    the rows."""
    if rows is None:
        return {"read": False}
    rows = E._l(rows)
    lines = [ln for ln in E._l(lines) if isinstance(ln, dict)]
    asked, keyed = [], False
    for i, r in enumerate(rows):
        act = E._d(r.get("action"))
        if act.get("type") != MELEE or r.get("sent") is not True:
            continue
        rel = E._d(act.get("args")).get(RELEASE)
        keyed = keyed or isinstance(rel, bool)
        if rel is True and E._n(r.get("wall")) is not None:
            asked.append((E._n(r.get("wall")), i))
    safe = bound = 0
    back, why, first = {}, {}, {}
    for ln in lines:
        if ln.get("kind") != "act" or ln.get("type") != MELEE:
            continue
        w = E._n(ln.get("wallMs"))
        if ln.get("state") == ACCEPTED and w is not None:
            first.setdefault(ln.get("aid"), w / 1000.0)
        res = E._d(ln.get("result"))
        if ln.get("state") == DONE and res.get("end") == HANDBACK and res.get("why") in (RELEASED, FLOOR):
            if w is not None:
                back.setdefault(ln.get("aid"), w / 1000.0)
                why.setdefault(ln.get("aid"), res.get("why"))
            if res.get("why") == RELEASED:
                keyed = True
                safe += 1 if res.get("safe") is True else 0
                bound += 1 if res.get("safe") is False else 0
    if not keyed:
        return {"read": False}
    out = []
    for t, li in asked:
        aid = min(((w, a) for a, w in first.items() if w >= t), default=(None, None))[1]
        early = False
        for r in rows:
            w = E._n(r.get("wall"))
            act = E._d(r.get("action"))
            if (w is not None and r.get("sent") is True and act.get("type") not in (None, MELEE)
                    and t < w <= t + EARLY_S and (aid not in back or back[aid] > w)):
                early = True
                break
        out.append({"line": li, "aid": aid, "back": why.get(aid), "early": early})
    return {"read": True, "asked": len(asked), "safe": safe, "bound": bound,
            "early": sum(1 for r in out if r["early"]), "rows": out}


def me_gait(me):
    """The character's group name off a frame's `me` flags (the module docstring's speeds)."""
    if me.get("moving"):
        g = "sprint" if me.get("sprinting") else ("run" if me.get("running") else "walk")
    else:
        g = "still_run" if me.get("running") or me.get("sprinting") else "still"
    g = ("sneak_" + g) if me.get("sneaking") else g
    return ("aimed_" + g) if me.get("aiming") else g


def _groups_of(by):
    """{name: {n, median, p90}} of {name: [value]}, by n descending then name."""
    return {k: _group(by[k]) for k in sorted(by, key=lambda k: (-len(by[k]), k))}


def _group(vals):
    vs = sorted(vals)
    return {"n": len(vs), "median": statistics.median(vs), "p90": vs[int(0.9 * len(vs))]}


def e_speeds(frames):
    """The speeds reading (the module docstring)."""
    me, zs = {}, {}
    for a, b in zip(frames, frames[1:]):
        wa, wb = E._n(a.get("wallMs")), E._n(b.get("wallMs"))
        if wa is None or wb is None:
            continue
        dt = (wb - wa) / 1000.0
        if not MIN_DT_S < dt < MAX_DT_S:
            continue
        ma, mb = E._d(a.get("me")), E._d(b.get("me"))
        xa, ya, xb, yb = E._n(ma.get("x")), E._n(ma.get("y")), E._n(mb.get("x")), E._n(mb.get("y"))
        if None not in (xa, ya, xb, yb):
            v = math.hypot(xb - xa, yb - ya) / dt
            if v < MAX_TPS:
                me.setdefault(me_gait(mb), []).append(v)
        pos = {}
        for z in (E._d(q) for q in E._l(a.get("zombies"))):
            if z.get("id") is not None and E._n(z.get("x")) is not None and E._n(z.get("y")) is not None:
                pos[z.get("id")] = (E._n(z.get("x")), E._n(z.get("y")))
        for z in (E._d(q) for q in E._l(b.get("zombies"))):
            p = pos.get(z.get("id"))
            x, y = E._n(z.get("x")), E._n(z.get("y"))
            if p is None or x is None or y is None:
                continue
            v = math.hypot(x - p[0], y - p[1]) / dt
            if v < MAX_TPS:
                zs.setdefault(CRAWLER if z.get("crawler") else str(z.get("state")), []).append(v)
    if not any(len(v) >= MIN_PAIRS for v in list(me.values()) + list(zs.values())):
        return {"read": False}
    return {"read": True, "me": _groups_of(me), "zombies": _groups_of(zs)}


def readings_x7(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`: none an earlier grade's key, the release `safe_release` since
    grade_e10's `release` is P25-M's), over the sources clipped at the loop's stop
    (`x1.clip`), the minutes in contact x5's `contact.seconds` over the same sources."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    contact = GX5.e_contact(lines, frames)
    cs = E._n(contact.get("seconds")) if contact.get("read") else None
    return {"restarts": e_restarts(lines, cs), "disposition": e_disposition(rows, cs), "string": e_string(lines),
            "safe_release": e_release(rows, lines), "speeds": e_speeds(frames)}


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=2):
    return round(v, n) if isinstance(v, float) else v


def _groups(gs):
    return {k: (v["n"], _r(v["median"]), _r(v["p90"])) for k, v in E._d(gs).items()}


def lines_x7(g):
    """One report line per new reading (`NEW`), each clause marked reading."""
    rs, dp, st, rl, sp = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append("restarts (work melees superseded inside %s tiles by a non-melee act within %s s) [reading]: %s (%s per "
               "minute of contact); %s" % (KEEP_R, RESTART_S, rs.get("n"), _r(rs.get("per_contact_min")),
                                          [(r["aid"], r["by"], _r(r["gap"])) for r in E._l(rs.get("rows"))])
               if rs.get("read") else GX1._unread("restarts"))
    out.append("disposition (the threat why's transitions) [reading]: %s changes (%s per minute of contact), dwell "
               "median %s s, by to %s, by why %s" % (dp.get("changes"), _r(dp.get("per_contact_min")),
                                                     _r(dp.get("dwell_median")), dp.get("by_to"), dp.get("by_why"))
               if dp.get("read") else GX1._unread("disposition"))
    out.append("string (the work leaf's string) [reading]: %s episodes, %s turns (%s with gap2 of %s or more), gap2 "
               "median %s, %s kills of melees last reading string, %s walk lines" % (
                   st.get("episodes"), st.get("turns"), st.get("turns_gap_ok"), STRING_GAP, _r(st.get("gap2_median")),
                   st.get("kills"), st.get("walk_lines")) if st.get("read") else GX1._unread("string"))
    out.append("safe release (the melee's release) [reading]: %s asked, %s released safe, %s released bound, %s early "
               "(a non-melee command within %s s of an asked line before its hand-back)" % (
                   rl.get("asked"), rl.get("safe"), rl.get("bound"), rl.get("early"), EARLY_S)
               if rl.get("read") else GX1._unread("safe release"))
    out.append("speeds (tiles a second over frame pairs %s to %s s apart; n, median, p90) [reading]: me %s; zombies %s"
               % (MIN_DT_S, MAX_DT_S, _groups(sp.get("me")), _groups(sp.get("zombies")))
               if sp.get("read") else GX1._unread("speeds"))
    return out


def report_lines_x7(g):
    """grade_x6's report lines (`report_lines_x6`), its gate line naming gate_x7, then `lines_x7`."""
    g = E._d(g)
    base = GX6.report_lines_x6(g)
    return [("gate_x7 " + ln[len("gate_x6 "):]) if ln.startswith("gate_x6 ") else ln for ln in base] + lines_x7(g)


def grade_x7(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x6` under "grade_x7" (`base` "grade_x6", `base_x6` x6's own base, x6's nesting kept) with the disposition
    readings (`readings_x7`), over the state lines of `state_dir` unless `lines` is given (read once and handed down);
    its report lines `report_lines_x7`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX6.grade_x6(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x6"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x7"
    g.update(readings_x7(record, decision_lines, lines))
    g["report_lines"] = report_lines_x7(g)
    return g


def gate_x7(outs):
    """gate_x6 (grade_x7 changes none of what it reads), named gate_x7."""
    return GX6.gate_x6(outs)
