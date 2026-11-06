"""grades.x1 -- the Harden composition's grade (Plan 31 Task 15b; ruling P31-H: the ladder with the Dress maneuver on
by default over the meet reflex, PZA/1.10): `grade_x1` is the session's base grade, `grades.f12.grade_f12` for an LLM
session or `grades.e21.grade_e21` for a chain session, under "grade_x1" with the base's name kept in `base`, plus the
trial loop's readings copied from the scorecard (`tools/trial_score.py` at main 0e4c9ec3, ruling P31-T: Plan 31 Task
15's pre-step and its residual) and the readings of the meet and the Dress:

  clip               the loop's stop: every new reading below reads the sources cut at `loop.startPyMs` plus
                     `stop.wallS` (the scorecard's `clip`, copied): the state lines after it, the decision lines and
                     the actions after it dropped; the counts dropped and the clock's base. The base's keys read the
                     sources whole, as their grade reads them.
  landed_hits        the attacks landed (the scorecard's `landed_hits` over its `reaction_segments`, copied): the
                     reaction runs split where the type changes, one reflex `hit` step joining each segment and every
                     further step a hit of its own; the EndDeath run (DEATH_REACTION, to the end of the continuous
                     reaction) is the one killing attack, every step and type change inside it joining it.
  fleeing            the minutes fleeing or retreating (`flee_minutes`), the frame-based minutes moving away from a
                     chaser with no refuge named (`away_minutes`) and the ladder's fight legs (`leg_minutes`).
  toward_target      the minutes moving toward a named target (`toward_minutes`).
  wounds_dressed     every wound taken and those dressed within DRESS_MIN game minutes (the scorecard's `dressed`,
                     copied: a part newly reading `wound` or `bleeding` true, a scratch that never bleeds included,
                     closed bandaged or healed; a dressed part takes a new wound only when it bleeds again
                     unbandaged, so a bandage coming off a part still wounded but not bleeding opens none).
  melees_superseded  the melees superseded before their press.
  meet_presses       each press's leaf (`d_press`, `d_collide_pred`, `look_off`, `d_min`, `knock_p`) against its
                     outcome (killed, knocked down, lowered, cut, nothing), by the press's kind.
  meet_refusals      the presses the engine refused, by run (the Lua's `refusals` count), the waits and the ends.
  meet_finishes      the finishes (the floor swing and the stomp at a fallen target) and whether `headAim` was sent.
  meet_handbacks     the melees ended `handback`, by why, by target (the line's `target` after the reflex re-pinned,
                     Task 15a, else the record's), with the crowd's `n` and `ds` and the reflex's re-pins.
  dresses            each Dress maneuver: its start, its stop, the garments unworn and torn, the part, its end, the time
                     from the part's first bleeding frame; the rides.

A reading is {"read": False} without its source (a frame for `landed_hits` and `wounds_dressed`, a decision log for
`fleeing`, `toward_target` and `dresses`, a melee span on a log of PZA/1.10 or later for the four meet readings,
`meet_log`: F15's and E23's PZA/1.9 logs read them unread; `melees_superseded` reads with no
span, its denominator the record's), and the Dress's reads False on a log no line of which carries the care why's
`dress`. A key marked reading counts what the log, the frames or the record states; one marked inference reads an
effect off the order of lines or the walls. The clocks are `grades.e21`'s (a decision line's `wall` epoch seconds, a
state line's `wallMs` epoch milliseconds, one host clock) and the scorecard's (a decision line's game minute its
`inputs.hour` x 60, a frame's its `me.hour` x 60, each unwrapped past midnight).

The scorecard's readers are copied here verbatim from main 0e4c9ec3, not imported: the scorecard is a live tool that
is never frozen (P31-T), while this module is frozen once an artifact carries its output (`grades/__init__.py`), so the
sessions' hits per kill and dressing are the trials' by construction (fix 1, review-t15b F1, F2). Every live name read
is copied below as a frozen constant with its source (ruling P26-Q): the scorecard's constants at 0e4c9ec3, the melee
maneuver's press leaf keys and the care branch's dress keys at bcaeb94d, and the Lua's step names and line fields, Task
15a's among them (its `PZAgent_StanceMelee.lua` header, read in its worktree before its commit). This module imports
nothing from `agent.base.planner`, `agent.base.world` or `tools`; the chains it imports (`grades.f12.grade_f12` and
`grades.e21.grade_e21`) are pinned by the regrade tests of the artifacts graded through them, and every artifact
graded through `grade_x1` takes its byte-for-byte regrade test in its artifact commit."""
import bisect
import math
import statistics

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e18 as G18
from agent.base.grades import e19 as G19
from agent.base.grades import e21 as G21
from agent.base.grades import f12 as G12

# Frozen copies of the live names read here (P26-Q), each with its source: tools/trial_score.py at 0e4c9ec3, the
# planner at bcaeb94d, the Lua at Task 15a.
RETREAT_LABELS = ("avoid", "kite", "retreat", "string", "flee")   # tools/trial_score.py:95
LABEL_KEYS = ("intent", "play", "act")                            # tools/trial_score.py:99
REFUGE_WORDS = ("filter", "door", "window", "shelter", "refuge")  # tools/trial_score.py:100
LEGS = ("pull", "back")                                           # tools/trial_score.py:101: the ladder's fight legs
MOVE_EPS = 0.05        # tools/trial_score.py:102: tiles, a fall in the distance this small is drift, not movement
DRESS_MIN = 1.0        # tools/trial_score.py:104: game minutes, a wound dressed this soon after its onset is in time
DEATH_REACTION = "EndDeath"   # tools/trial_score.py:106: a dying character's reaction, one landed attack
SUPERSEDED = "superseded"   # tools/trial_score.py:107: the melee's terminal reason when the planner sent another act
MELEE = "melee"             # the skill's type (schema actionType, PZA/1.8)
HIT_STEP = "hit"            # PZAgent_StanceMelee.lua (rule 1): the reflex's step on a tick its hit reaction reads set
PRESS_STEPS = ("swing", "shove", "stomp", "floor")   # planner/maneuvers/melee.py:42 STRIKE_STEPS (the Lua's presses)
PRESS_KEYS = ("d_press", "d_collide_pred", "d_min", "look_off", "hp0", "hp1", "knock", "cut_by")   # melee.py:44
                       # (planner/maneuvers/melee.py PRESS_KEYS: the press leaf's keys)
KNOCK_P = "knock_p"    # Task 15a's Lua header (line 111): a shove's leaf adds the chance in 0 to 1 of its critical
                       # knock-down (#4373's roll); absent before it, read None
REPIN_STEP = "repin"   # Task 15a's Lua header (lines 61-62): the reflex re-pinned its target to a nearer standing one
TARGET = "target"      # Task 15a's Lua header (lines 117-119): every line after a re-pin, the zombie now pressed
REPINS = "repins"      # ... and the re-pins so far
CROWD_N = "n"          # Task 15a's Lua header (line 58): a crowd handback's count of the standing zombies
CROWD_DS = "ds"        # ... and their distances, nearest first
FINISH_KINDS = ("floor", "stomp")   # PZAgent_StanceMelee.lua (rule 4): the finish's presses at a fallen target
HEAD_STEP = "head"     # PZAgent_StanceMelee.lua (rule 4): the finish turning to the aim point before its press
REFUSED = "refused"    # PZAgent_StanceMelee.lua (rule 2): a refused press's `cut_by`, the wait's step, the end's why
HANDBACK = "handback"  # PZAgent_StanceMelee.lua's done `end` (why crowd or standing, with the other zombie's id and d)
DONE_KEYS = ("end", "kill", "why", "id", "d", "swings", "shoves", "stomps", "floors", "knockdowns", "hits", "spent",
             "hp0", "hp1", "dMin", "steps", "press", "refusals", "n", "ds", "target", "repins")   # the Lua's done
                       # fields (its header, Task 15a's lines 117-120); any other field a handback's done line carries
                       # is kept under `extra`
CARE = "care"          # planner/care.py:829: the care branch's why, `inputs.branches.care`
DRESS_KEY = "dress"    # planner/care.py:829: the running Dress's log on the care why
DRESS_END_KEY = "dress_end"   # planner/care.py:789: the ended Dresses' logs, a list, on the next why once
DRESS_SENDS = ("stop", "unwear", "rip", "bandage")   # planner/maneuvers/dress.py's commands (its sequence)
STILL_PHASE = "still"  # planner/maneuvers/dress.py: the wait after a stop for a frame reading `me.moving` false
PICK_PHASE = "pick"    # planner/maneuvers/dress.py: the pick, once the character is still
# The grade's own numbers.
NEW = ("clip", "landed_hits", "fleeing", "toward_target", "wounds_dressed", "melees_superseded", "meet_presses",
       "meet_refusals", "meet_finishes", "meet_handbacks", "dresses")
N_LINES = len(NEW)     # the report lines lines_x1 appends: one per NEW key
MEET_MOD = (1, 10)     # the hello's `mod` from which the melee is the meet (PZA/1.10, Plan 31 Task 2)
KINDS = ("e", "f")     # the session's kind: a chain session (grade_e21) or an LLM one (grade_f12)


def _per(n, k):
    return n / k if k else None


def _gap(a, b):
    return b - a if a is not None and b is not None and b >= a else 0.0


def _spread(xs):
    """{n, min, median, max} of the numbers in `xs` (None dropped); {n: 0} without one."""
    xs = [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool)]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "min": min(xs), "median": statistics.median(xs), "max": max(xs)}


# ---------------------------------------------------------------- the clip at the loop's stop
def stop_ms(out):
    """The loop's stop on the frames' clock (epoch ms): `loop.startPyMs` (else `t_loop0_ms`) plus `stop.wallS` x
    1000; None without either (an old or crashed record, read whole). The scorecard's `stop_ms`."""
    out = E._d(out)
    t0 = E._n(E._d(out.get("loop")).get("startPyMs"))
    t0 = t0 if t0 is not None else E._n(E._d(out.get("loop")).get("t_loop0_ms"))
    w = E._n(E._d(out.get("stop")).get("wallS"))
    return t0 + w * 1000.0 if t0 is not None and w is not None else None


def clip(out, decision_lines, lines):
    """(out, decision lines, lines, clock): the sources cut at the loop's stop (`stop_ms`), the scorecard's `clip`
    over a record, its decision lines (None kept None) and its state lines. A state line is kept when its `wallMs` is
    at or before the stop (one with none kept), a decision line when its `wall` is, a `loop.actions` row when its
    `sentS` is at or before `stop.wallS` and a `loop.fights` row when its `startS` is; `loop.game_min` is held to
    `stop.gameMin`. `clock` {read, start_ms, stop_ms, stop_s, first_frame_s, last_frame_s, frames, lines, decisions,
    actions}: the last four the counts dropped (`lines` the state lines of every kind, `frames` among them), `read`
    False when the record has no stop to cut at (nothing dropped)."""
    out = E._d(out)
    lines = E._l(lines)
    rows = decision_lines
    t0 = E._n(E._d(out.get("loop")).get("startPyMs"))
    t0 = t0 if t0 is not None else E._n(E._d(out.get("loop")).get("t_loop0_ms"))
    cut = stop_ms(out)
    stop_s = E._n(E._d(out.get("stop")).get("wallS"))

    def at(w):
        return cut is None or w is None or w <= cut

    kept = [ln for ln in lines if at(E._n(E._d(ln).get("wallMs")))]
    drows = None if rows is None else [d for d in rows if cut is None or E._n(E._d(d).get("wall")) is None
                                       or E._n(E._d(d).get("wall")) * 1000.0 <= cut]
    loop = dict(E._d(out.get("loop")))
    acts = E._l(loop.get("actions"))
    if cut is not None:
        loop["actions"] = [a for a in acts if E._n(E._d(a).get("sentS")) is None
                           or E._n(E._d(a).get("sentS")) <= stop_s]
        if "fights" in loop:
            loop["fights"] = [f for f in E._l(loop.get("fights")) if E._n(E._d(f).get("startS")) is None
                              or E._n(E._d(f).get("startS")) <= stop_s]
        g1, gs = E._n(loop.get("game_min")), E._n(E._d(out.get("stop")).get("gameMin"))
        if g1 is not None and gs is not None and gs < g1:
            loop["game_min"] = gs
    out = dict(out, loop=loop) if "loop" in out or cut is not None else out
    frames = [ln for ln in kept if E._d(ln).get("kind") == "frame" and E._n(ln.get("wallMs")) is not None]
    secs = [(E._n(f.get("wallMs")) - t0) / 1000.0 for f in frames] if t0 is not None else []
    clock = {"read": cut is not None, "start_ms": t0, "stop_ms": cut, "stop_s": stop_s if cut is not None else None,
             "first_frame_s": min(secs) if secs else None, "last_frame_s": max(secs) if secs else None,
             "frames": sum(1 for ln in lines if E._d(ln).get("kind") == "frame") - len(frames),
             "lines": len(lines) - len(kept), "decisions": len(rows or []) - len(drows or []),
             "actions": len(acts) - len(E._l(loop.get("actions")))}
    return out, drows, kept, clock


# ---------------------------------------------------------------- the hits landed (the scorecard's, copied)
def reaction_segments(frames):
    """[(first, last)] frame indices of the reaction runs of `frames` (`e21._reaction_runs`: a run lasts while the
    frames read `me.hitReaction` non-empty) split where the reaction type changes between two frames of one run (a
    Bite, then a CrawlerBite, then an EndDeath are three segments). The death reaction (DEATH_REACTION) ends the split:
    its segment runs to the end of the continuous run, whatever types follow it."""
    out = []
    for a, b in G21._reaction_runs(frames):
        start = a
        for i in range(a + 1, b + 1):
            if G18._reaction(frames[start]) == DEATH_REACTION:
                break
            if G18._reaction(frames[i]) != G18._reaction(frames[i - 1]):
                out.append((start, i - 1))
                start = i
        out.append((start, b))
    return out


def landed_hits(frames, lines, kills):
    """The attacks landed (the hits' union, Plan 31 Task 15's pre-step): {read, runs, steps, joined, union, kills,
    per_kill_union, rows}, the shape of `e21.e_hits_union`'s ({"read": False} without a frame). `runs` the reaction
    segments (`reaction_segments`), `steps` the reflex's `hit` step runs (`e21._step_runs`); each step joins the first
    segment, in wall order, that has no step yet and lies within one frame interval of it (`e21._joins`, so a step
    lagging the reaction's first frame still joins it), and a step that joins none (a second step in a segment's span, or
    one in no reaction) is a hit of its own: `union` is the segments plus the steps that joined none, `per_kill_union`
    over `kills` (None at 0). A dying character's reaction stays set to the end of its life: its continuous run, which
    `e_hits_union` counted once, reads here the segments of its types and the steps the reflex wrote in it, up to the
    EndDeath reaction (DEATH_REACTION): the EndDeath run, to the end of the continuous reaction, is one landed attack,
    the killing one, and every reflex `hit` step and type change inside it joins it (attacks on a dying character are not
    a reading of the fight: Angus's metric is the successful attacks per kill, ruling on the pre-step). `rows` the
    union in wall order {source ("reaction", "step", "both"), seq, wallMs, aid, kind (the segment's reaction)}."""
    if not frames:
        return {"read": False}
    walls = [E._n(f.get("wallMs")) for f in frames]
    segs, steps = reaction_segments(frames), G21._step_runs(lines)
    rows = [{"source": "reaction", "seq": frames[a].get("seq"), "wallMs": walls[a], "aid": None,
             "kind": G18._reaction(frames[a])} for a, _ in segs]
    taken, joined = set(), 0
    for w, seq, aid in steps:
        k = next((i for i, s in enumerate(segs) if (i not in taken or G18._reaction(frames[s[0]]) == DEATH_REACTION)
                  and G21._joins(walls, s, w)), None)
        if k is None:
            rows.append({"source": "step", "seq": seq, "wallMs": w, "aid": aid, "kind": None})
            continue
        taken.add(k)
        joined += 1
        row = rows[k]
        row.update(source="both", aid=aid)
        if w < row["wallMs"]:
            row.update(seq=seq, wallMs=w)
    k = E._n(kills) or 0
    union = len(segs) + len(steps) - joined
    return {"read": True, "runs": len(segs), "steps": len(steps), "joined": joined, "union": union, "kills": k,
            "per_kill_union": G21._per(union, k), "rows": sorted(rows, key=lambda r: r["wallMs"])}


def _event_kills(lines):
    """The distinct `zombie_dead` event ids of the state lines (the scorecard's kills), in log order."""
    out = []
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "event" and ln.get("event") == "zombie_dead" \
                and ln.get("id") not in out:
            out.append(ln.get("id"))
    return out


# ---------------------------------------------------------------- the clocks (the scorecard's)
def _unwrap(mins):
    """Minutes of the day (a None kept) unwrapped past midnight: a fall of more than half a day adds a day."""
    out, off, prev = [], 0.0, None
    for m in mins:
        if m is None:
            out.append(None)
            continue
        if prev is not None and m + off < prev - 720.0:
            off += 1440.0
        out.append(m + off)
        prev = m + off
    return out


def line_minutes(rows):
    """Each decision line's game minute, its `inputs.hour` x 60 unwrapped (None without an hour)."""
    return _unwrap([(lambda h: h * 60.0 if h is not None else None)(E._n(E._d(r.get("inputs")).get("hour")))
                    for r in rows])


def frame_minutes(frames):
    """Each frame's game minute, its `me.hour` x 60 unwrapped, else its `gameMin` (None without either)."""
    def one(f):
        h = E._n(E._d(f.get("me")).get("hour"))
        return h * 60.0 if h is not None else E._n(f.get("gameMin"))
    return _unwrap([one(f) for f in frames])


def log_minutes(rows):
    """The decision log's game minutes, from its first line to its last (0.0 under two lines)."""
    gm = [m for m in line_minutes(rows) if m is not None]
    return gm[-1] - gm[0] if len(gm) > 1 else 0.0


# ---------------------------------------------------------------- the fleeing (the scorecard's, copied)
def _label(v):
    """A variant's choice as a lower-case string: the value itself, or a dict's `kind`, `name` or `type`."""
    if isinstance(v, dict):
        v = next((v[k] for k in ("kind", "name", "type") if isinstance(v.get(k), str)), None)
    return v.lower() if isinstance(v, str) else None


def _labels(r):
    """The labels of the line's (then its inputs') LABEL_KEYS, in that order."""
    return [lab for src in (r, E._d(r.get("inputs"))) for k in LABEL_KEYS for lab in [_label(src.get(k))]
            if lab is not None]


def _retreat_label(r):
    return next((lab for lab in _labels(r) if lab.startswith(RETREAT_LABELS)), None)


def leg_minutes(rows):
    """{leg: {lines, minutes}} of the ladder's fight legs walking off a zombie (LEGS), off the threat why's `leg`,
    each line standing to the next."""
    gm = line_minutes(rows)
    out = {leg: {"lines": 0, "minutes": 0.0} for leg in LEGS}
    for i, r in enumerate(rows):
        leg = E._bw(r, "threat").get("leg")
        if leg not in out:
            continue
        out[leg]["lines"] += 1
        if i + 1 < len(rows):
            out[leg]["minutes"] += _gap(gm[i], gm[i + 1])
    return out


def flee_minutes(rows):
    """The minutes fleeing or retreating: {lines, minutes, seconds, total_minutes, by}. A line is a flee or retreat
    leg when the threat why's `flee` is set or a label of the line's or its inputs' LABEL_KEYS starts with a
    RETREAT_LABELS word; each such line stands from its own game minute to the next line's and from its wall to the
    next line's. `by` the lines by flee reason or label; `total_minutes` the log's, the denominator."""
    gm = line_minutes(rows)
    n, mins, secs, by = 0, 0.0, 0.0, {}
    for i, r in enumerate(rows):
        why = E._bw(r, "threat").get("flee")
        lab = "flee:%s" % why if why is not None else _retreat_label(r)
        if lab is None:
            continue
        n += 1
        by[lab] = by.get(lab, 0) + 1
        if i + 1 < len(rows):
            mins += _gap(gm[i], gm[i + 1])
            secs += _gap(E._n(r.get("wall")), E._n(rows[i + 1].get("wall")))
    return {"lines": n, "minutes": mins, "seconds": secs, "total_minutes": log_minutes(rows), "by": by}


def _xy(v):
    """(x, y) of a [x, y] or {x, y}, else None."""
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        x, y = E._n(v[0]), E._n(v[1])
    elif isinstance(v, dict):
        x, y = E._n(v.get("x")), E._n(v.get("y"))
    else:
        return None
    return (x, y) if x is not None and y is not None else None


def _play_targets(r):
    """The `target` values of the line's (then its inputs') `play` and `intent` dicts, in that order."""
    return [p["target"] for src in (r, E._d(r.get("inputs"))) for k in ("play", "intent") for p in [src.get(k)]
            if isinstance(p, dict) and p.get("target") is not None]


def _refuge_word(v):
    return isinstance(v, str) and any(w in v.lower() for w in REFUGE_WORDS)


def names_refuge(r):
    """Whether the line names a filter, door, window or shelter target: a label or a string play target containing a
    REFUGE_WORDS word; or the ladder's own, its threat why's `shelter` set, its `doorway_pick` set to anything but
    `no_door`, or its goal's `type` a Shelter."""
    if any(_refuge_word(x) for x in _labels(r) + _play_targets(r)):
        return True
    t = E._bw(r, "threat")
    if t.get("shelter") is not None or t.get("doorway_pick") not in (None, "no_door"):
        return True
    return _refuge_word(E._d(r.get("goal")).get("type"))


def _chaser(f):
    """(id, distance) of the frame's nearest zombie whose `hasTarget` is true, by `e18._zd`, else None."""
    best = None
    for q in (E._d(x) for x in E._l(E._d(f).get("zombies"))):
        if q.get("hasTarget") is not True:
            continue
        d = G18._zd(f, q)
        if d is not None and (best is None or d < best[1]):
            best = (q.get("id"), d)
    return best


def away_minutes(L):
    """The frame-based minutes moving away from a chaser with no refuge named: {intervals, minutes, refuge_skipped}.
    Over each pair of consecutive frames: the character moved more than MOVE_EPS, the nearest zombie targeting it on
    the first frame is listed on the second more than MOVE_EPS farther, and no decision line in force over the
    interval names a refuge (`names_refuge`): the interval's game minutes (`frame_minutes`) count, one whose clock
    steps back counting 0. `refuge_skipped` the intervals moving away but under a refuge."""
    walls, frames = L.index
    gm = frame_minutes(frames)
    lwalls = [(E._n(r.get("wall")) or 0.0) * 1000.0 for r in L.rows]
    n, mins, skipped = 0, 0.0, 0
    for k in range(1, len(frames)):
        a, b = frames[k - 1], frames[k]
        pa, pb = G21._me(a), G21._me(b)
        if pa is None or pb is None or G21._hyp(pa, pb) <= MOVE_EPS:
            continue
        c = _chaser(a)
        if c is None:
            continue
        q = next((E._d(x) for x in E._l(b.get("zombies")) if E._d(x).get("id") == c[0]), None)
        d1 = G18._zd(b, q) if q is not None else None
        if d1 is None or d1 <= c[1] + MOVE_EPS:
            continue
        j = bisect.bisect_right(lwalls, walls[k - 1]) - 1
        hi = bisect.bisect_right(lwalls, walls[k])
        if any(names_refuge(L.rows[i]) for i in range(max(j, 0), hi)):
            skipped += 1
            continue
        n += 1
        mins += _gap(gm[k - 1], gm[k])
    return {"intervals": n, "minutes": mins, "refuge_skipped": skipped}


def e_fleeing(L):
    """{read, ...flee_minutes, away, legs} ({"read": False} without a decision log)."""
    if L is None:
        return {"read": False}
    return dict(flee_minutes(L.rows), read=True, away=away_minutes(L), legs=leg_minutes(L.rows))


# ---------------------------------------------------------------- toward a named target (the scorecard's, copied)
def _zombie_xy(frame, label):
    z = next((E._d(q) for q in E._l(E._d(frame).get("zombies")) if E._d(q).get("id") == label), None)
    return _xy(z) if z is not None else None


def _resolve(t, frame):
    """(label, (x, y)) of a play's target: a square ("play:<x>,<y>") or a zombie id the frame lists ("zombie:<id>"),
    else None."""
    sq = _xy(t)
    if sq is not None:
        return "play:%s,%s" % sq, sq
    sq = _zombie_xy(frame, t)
    return ("zombie:%s" % t, sq) if sq is not None else None


def named_target(r, frame=None):
    """(label, (x, y)) of the target the line's decider names, else None: a variant's play or intent target; else, on
    a `goal` line, the goal's `args` square (label its `type`) or the goal why's `goal_continue.target` (label
    "continue:<source>")."""
    for t in _play_targets(r):
        got = _resolve(t, frame)
        if got is not None:
            return got
    if r.get("branch") != "goal":
        return None
    g = E._d(r.get("goal"))
    sq = _xy(E._d(g.get("args")))
    if sq is not None:
        return str(g.get("type")), sq
    c = E._d(E._bw(r, "goal").get("goal_continue"))
    sq = _xy(c.get("target"))
    return ("continue:%s" % c.get("source"), sq) if sq is not None else None


def toward_minutes(L):
    """The minutes moving toward a named target: {lines, minutes, named_lines, named_minutes, unresolved,
    total_minutes, by}. A line (after the first) moved toward its target when it names one (`named_target`, the frame
    at the line) and its position lies more than MOVE_EPS tiles nearer it than the line before's did; it counts the
    game minutes from the line before to it. `named_*` every line naming a target; `unresolved` the lines whose play
    or intent target resolved to nothing; `by` the moving lines by target label."""
    rows = L.rows
    gm = line_minutes(rows)
    n, mins, nn, nmins, by = 0, 0.0, 0, 0.0, {}
    unresolved = sum(1 for r in rows for ts in [_play_targets(r)]
                     if ts and all(_resolve(t, L.frame(r)) is None for t in ts))
    for i in range(1, len(rows)):
        t = named_target(rows[i], L.frame(rows[i]))
        if t is None:
            continue
        nn += 1
        span = _gap(gm[i - 1], gm[i])
        nmins += span
        p, q = G21._pos(rows[i]), G21._pos(rows[i - 1])
        if p is None or q is None:
            continue
        if math.hypot(p[0] - t[1][0], p[1] - t[1][1]) < math.hypot(q[0] - t[1][0], q[1] - t[1][1]) - MOVE_EPS:
            n += 1
            mins += span
            lab = t[0].split(":")[0]
            by[lab] = by.get(lab, 0) + 1
    return {"lines": n, "minutes": mins, "named_lines": nn, "named_minutes": nmins, "unresolved": unresolved,
            "total_minutes": log_minutes(rows), "by": by}


def e_toward_target(L):
    """{read, ...toward_minutes} ({"read": False} without a decision log)."""
    if L is None:
        return {"read": False}
    return dict(toward_minutes(L), read=True)


# ---------------------------------------------------------------- the wounds, every one
def dressed(frames):
    """The wounds dressed within one game minute: {wounds, dressed, stopped, rows}. A wound is taken on a body part
    (a `body.parts[i]` entry, as the care readers read them) at the first frame (wall order) it reads `wound` or
    `bleeding` true while it has no open wound and is not under a bandage (so the first frame's wounded parts are
    taken): the `wound` flag is the Lua's rank-1 test of a bandageable part (scratched, cut, bitten or deep-wounded,
    `planner/care.py` `_wounds`), so a scratch that never bleeds is a wound, as a bleed is (a frame without the key
    reads `bleeding` alone). It closes at the part's first later frame reading `bandaged` true (dressed, `bandaged`
    True), or reading neither `wound` nor `bleeding`, or not listed (healed, `bandaged` False); `dressed` the wounds
    closed bandaged within DRESS_MIN game minutes of their onset (`frame_minutes`, inclusive), `stopped` those closed
    either way; each row {part, seq0, seq1, minutes, bandaged}, the last three None past the log's end. A dressed part
    takes a new wound only when it reads `bleeding` true again unbandaged (its removed bandage leaves the old wound's
    flag, no new wound); it is clean again when it reads neither. `wounds` the denominator."""
    gm = frame_minutes(frames)
    opened, under, rows = {}, set(), []
    for f, m in zip(frames, gm):
        cur = {p.get("i"): p for p in (E._d(x) for x in E._l(E._d(f.get("body")).get("parts"))) if "i" in p}
        for i, p in cur.items():
            bleed = p.get("bleeding") is True
            hurt, band = bleed or p.get("wound") is True, p.get("bandaged") is True
            if i in opened:
                if band or not hurt:
                    r = rows[opened.pop(i)]
                    r.update(seq1=f.get("seq"), minutes=_gap(r["m0"], m), bandaged=band)
                    if band:
                        under.add(i)
            elif band:
                under.add(i)
            elif hurt and (bleed or i not in under):
                under.discard(i)
                opened[i] = len(rows)
                rows.append({"part": i, "seq0": f.get("seq"), "m0": m, "seq1": None, "minutes": None,
                             "bandaged": None})
            elif not hurt:
                under.discard(i)
        for i in [i for i in opened if i not in cur]:   # a part no longer listed reads healed
            r = rows[opened.pop(i)]
            r.update(seq1=f.get("seq"), minutes=_gap(r["m0"], m), bandaged=False)
        under -= {i for i in under if i not in cur}
    for r in rows:
        r.pop("m0")
    return {"wounds": len(rows), "dressed": sum(1 for r in rows if r["bandaged"] is True
                                                and r["minutes"] <= DRESS_MIN),
            "stopped": sum(1 for r in rows if r["seq1"] is not None), "rows": rows}


def e_wounds_dressed(frames):
    """Every wound taken and those dressed within DRESS_MIN game minutes: the scorecard's `dressed` (copied above,
    its rule and its rows) with `read` True and `carried` the wounds taken on the first frame (the session's own
    first sight: a chain session's carried wounds), {"read": False} without a frame."""
    if not frames:
        return {"read": False}
    d = dressed(frames)
    first = frames[0].get("seq")
    return dict(d, read=True, carried=sum(1 for r in d["rows"] if r["seq0"] == first))


# ---------------------------------------------------------------- the melees superseded (the scorecard's, copied)
def e_melees_superseded(out, lines):
    """The melees superseded before their press: {read, superseded_before, superseded, no_swing_step, sent, spans,
    aids}. A melee span whose terminal act line reads state `failed` and reason `superseded` is `superseded`;
    `superseded_before` those whose progress steps hold none of PRESS_STEPS, `aids` theirs; `no_swing_step` the
    superseded with no `swing` step; `sent` the denominator, the record's `loop.actions` of type melee (the spans'
    count without a record)."""
    spans = G19._spans(lines)
    sup, before, noswing, aids = 0, 0, 0, []
    for s in spans:
        t = E._d(s["terminal"])
        if t.get("state") != "failed" or t.get("reason") != SUPERSEDED:
            continue
        sup += 1
        steps = {E._d(r).get("step") for _, r in s["progress"]}
        if not steps & set(PRESS_STEPS):
            before += 1
            aids.append(s["aid"])
        if "swing" not in steps:
            noswing += 1
    acts = [a for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions"))) if a.get("type") == MELEE]
    return {"read": True, "superseded_before": before, "superseded": sup, "no_swing_step": noswing,
            "sent": len(acts) if acts else len(spans), "spans": len(spans), "aids": aids}


# ---------------------------------------------------------------- the meet: the presses, the refusals, the finishes
def _version(v):
    """The hello's `mod` string as a tuple of ints ("1.10" -> (1, 10)), else None."""
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return None


def meet_log(lines):
    """Whether the state log is the meet's (PZA/1.10 on): the hello's `mod` at MEET_MOD or later, or, with no hello
    read, a melee act line carrying a press leaf."""
    hello = next((ln for ln in E._l(lines) if isinstance(ln, dict) and ln.get("kind") == "hello"), None)
    v = _version(hello.get("mod")) if hello is not None else None
    if v is not None:
        return v >= MEET_MOD
    return any(isinstance(E._d(ln.get("result")).get("press"), dict) for lns in _melee_lines(lines).values()
               for ln in lns)


def _melee_lines(lines):
    """{aid: [act line]} of the melee act lines in log order."""
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == MELEE:
            by.setdefault(ln.get("aid"), []).append(ln)
    return by


def _outcome(leaf, ln):
    """The press's outcome off its leaf (and its line): refused (the engine refused it: no press), killed (`hp1` 0 or
    under, or a done line reading `kill`), knocked (`knock` true), lowered (`hp1` under `hp0`), cut (`cut_by` another
    reason: a hit reaction, a supersede), else nothing."""
    cut = leaf.get("cut_by")
    if cut == REFUSED:
        return "refused"
    h0, h1 = E._n(leaf.get("hp0")), E._n(leaf.get("hp1"))
    res = E._d(ln.get("result"))
    if (h1 is not None and h1 <= 0) or (ln.get("state") == "done" and res.get("kill") is True):
        return "killed"
    if leaf.get("knock") is True:
        return "knocked"
    if h0 is not None and h1 is not None and h1 < h0:
        return "lowered"
    if isinstance(cut, str) and cut:
        return "cut"
    return "nothing"


def _press_rows(out, lines):
    """[{aid, seq, wallMs, kind, outcome, d_press, d_collide_pred, d_min, look_off, knock_p, hp0, hp1, knock, cut_by,
    head_aim, mode}] of every press leaf on a melee act line, in log order. Reading: the leaf's fields (PRESS_KEYS and
    KNOCK_P, absent read None); the press's `kind` the aid's last PRESS_STEPS step on a line before the leaf's (the
    leaf comes on the line after its press's result, whose own step may be the next press), else the leaf line's own
    step; `head_aim` the record's `headAim` argument of the aid true (an absent one reads False, as the Lua reads it:
    `args.headAim == true`; None for an aid the record lacks) and `mode` its mode."""
    args = {a.get("aid"): E._d(a.get("args")) for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get(
        "actions")))}
    rows = []
    for aid, lns in _melee_lines(lines).items():
        last = None
        for ln in lns:
            res = E._d(ln.get("result"))
            leaf = res.get("press")
            if isinstance(leaf, dict):
                a = args.get(aid, {})
                row = {"aid": aid, "seq": ln.get("seq"), "wallMs": E._n(ln.get("wallMs")),
                       "kind": last if last is not None else res.get("step"), "outcome": _outcome(leaf, ln)}
                row.update({k: leaf.get(k) for k in PRESS_KEYS + (KNOCK_P,)})
                row.update(head_aim=(a.get("headAim") is True) if aid in args else None, mode=a.get("mode"))
                rows.append(row)
            if res.get("step") in PRESS_STEPS:
                last = res.get("step")
    return sorted(rows, key=lambda r: (r["wallMs"] is None, r["wallMs"] or 0))


OUTCOMES = ("killed", "knocked", "lowered", "cut", "nothing", "refused")
FIELDS = ("d_press", "d_collide_pred", "d_min", "look_off", KNOCK_P)


def e_meet_presses(out, lines):
    """The presses against their outcome: {read, presses, refused, by_kind, by_outcome, table, shoves, rows}
    ({"read": False} without a melee span). Reading: every press leaf (`_press_rows`), `presses` those not refused (a
    refused press is the engine's, counted under `refused` and read by `meet_refusals`); `by_kind` and `by_outcome`
    their counts; `table` {kind: {outcome: {n, d_press, d_collide_pred, d_min, look_off, knock_p}}}, each field's
    `_spread`: the presses by their distances, look and expected roll against what they did; `shoves` {n, knocked,
    knock_p_n, knock_p_sum} the shoves' knock-downs beside the sum of the expected rolls they logged (`knock_p`, the
    Lua's units, read as logged)."""
    if not G19._spans(lines) or not meet_log(lines):
        return {"read": False}
    rows = _press_rows(out, lines)
    real = [r for r in rows if r["outcome"] != "refused"]
    by_kind, by_out, table = {}, {}, {}
    for r in real:
        G14._inc(by_kind, str(r["kind"]))
        G14._inc(by_out, r["outcome"])
    for kind in sorted(by_kind):
        t = table.setdefault(kind, {})
        for o in OUTCOMES:
            got = [r for r in real if str(r["kind"]) == kind and r["outcome"] == o]
            if got:
                t[o] = dict({"n": len(got)}, **{f: _spread([r[f] for r in got]) for f in FIELDS})
    sh = [r for r in real if r["kind"] == "shove"]
    kp = [E._n(r[KNOCK_P]) for r in sh if E._n(r[KNOCK_P]) is not None]
    return {"read": True, "presses": len(real), "refused": len(rows) - len(real), "by_kind": by_kind,
            "by_outcome": by_out, "table": table,
            "shoves": {"n": len(sh), "knocked": sum(1 for r in sh if r["knock"] is True), "knock_p_n": len(kp),
                       "knock_p_sum": sum(kp) if kp else None}, "rows": rows}


def e_meet_refusals(lines):
    """The presses the engine refused, by run: {read, runs, refused, waits, ended, open, by_count, rows} ({"read":
    False} without a melee span). Reading, per melee's act lines in log order (the Lua's residual: a run of refusals
    writes its leaf on its first, `refusals` 1 with `cut_by` refused, and its count again at its end, on the next
    accepted press's line or the melee's end line): a run opens on a line whose leaf reads `cut_by` refused with
    `refusals` 1 and closes on the next line carrying `refusals`, its count; `ended_by` that line's step ("press" on a
    progress line) or its state and end; a run with no closing line is `open`. `waits` the entries into the wait's
    step (REFUSED), `ended` the melees ended lost with why refused, `refused` the runs' counts summed."""
    if not G19._spans(lines) or not meet_log(lines):
        return {"read": False}
    rows, waits, ended = [], 0, 0
    for aid, lns in _melee_lines(lines).items():
        run, prev = None, None
        for ln in lns:
            res = E._d(ln.get("result"))
            st = res.get("step")
            if ln.get("state") == "progress" and st == REFUSED and prev != REFUSED:
                waits += 1
            if ln.get("state") == "progress":
                prev = st
            if ln.get("state") == "done" and res.get("end") == "lost" and res.get("why") == REFUSED:
                ended += 1
            n = E._n(res.get("refusals"))
            if n is None:
                continue
            leaf = E._d(res.get("press"))
            if leaf.get("cut_by") == REFUSED and n == 1:
                if run is not None:
                    rows.append(run)
                run = {"aid": aid, "seq0": ln.get("seq"), "seq1": None, "count": None, "ended_by": None}
                continue
            if run is None:
                run = {"aid": aid, "seq0": None, "seq1": None, "count": None, "ended_by": None}
            how = "press" if ln.get("state") == "progress" else "%s %s" % (ln.get("state"), res.get("end"))
            run.update(seq1=ln.get("seq"), count=int(n), ended_by=how)
            rows.append(run)
            run = None
        if run is not None:
            rows.append(run)
    by = {}
    for r in rows:
        G14._inc(by, str(r["count"]))
    return {"read": True, "runs": len(rows), "refused": sum(r["count"] or 0 for r in rows), "waits": waits,
            "ended": ended, "open": sum(1 for r in rows if r["count"] is None), "by_count": by, "rows": rows}


def e_meet_finishes(out, lines):
    """The finishes and the head aim: {read, sent_finish, head_aim, presses, by_outcome, kills, heads, rows}
    ({"read": False} without a melee span). Reading: `sent_finish` the record's melees sent in mode finish;
    `head_aim` {on, off, absent} the record's melees by their `headAim` argument (the finish aimed at the head
    estimate when on; an absent argument is off, as the Lua reads it, and counted under `absent` too: the send omits
    a false one); `presses` {floor, stomp} the finish presses' leaves (`_press_rows` of FINISH_KINDS, refused
    ones left out), `by_outcome` theirs, `kills` those killing, `heads` the entries into the finish's turn to its aim
    point (HEAD_STEP); `rows` each finish press {aid, kind, outcome, d_press, look_off, head_aim}."""
    if not G19._spans(lines) or not meet_log(lines):
        return {"read": False}
    acts = [a for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions"))) if a.get("type") == MELEE]
    aim = {"on": 0, "off": 0, "absent": 0}
    for a in acts:
        v = E._d(a.get("args")).get("headAim")
        aim["on" if v is True else "off"] += 1
        aim["absent"] += 0 if "headAim" in E._d(a.get("args")) else 1
    rows = [r for r in _press_rows(out, lines) if r["kind"] in FINISH_KINDS and r["outcome"] != "refused"]
    by, pr = {}, {k: 0 for k in FINISH_KINDS}
    for r in rows:
        G14._inc(by, r["outcome"])
        pr[r["kind"]] += 1
    heads = 0
    for lns in _melee_lines(lines).values():
        prev = None
        for ln in lns:
            if ln.get("state") != "progress":
                continue
            st = E._d(ln.get("result")).get("step")
            heads += 1 if st == HEAD_STEP and prev != HEAD_STEP else 0
            prev = st
    return {"read": True, "sent_finish": sum(1 for a in acts if E._d(a.get("args")).get("mode") == "finish"),
            "head_aim": aim, "presses": pr, "by_outcome": by, "kills": by.get("killed", 0), "heads": heads,
            "rows": [{k: r[k] for k in ("aid", "kind", "outcome", "d_press", "look_off", "head_aim")} for r in rows]}


def e_meet_handbacks(out, lines):
    """The melees ended `handback` and the reflex's re-pins (Task 15a): {read, handbacks, by_why, by_target,
    repinned, repins, rows} ({"read": False} without a melee span on the meet's log). Reading: each melee's done line
    reading `end` HANDBACK, its row {aid, seq, target, why, id, d, n, ds, repins, extra}: `target` the line's own
    TARGET (the zombie the reflex pressed after a re-pin) else the record's `targetId`, `n` and `ds` the crowd's count
    and distances (CROWD_N, CROWD_DS; None on a standing handback), `repins` the line's REPINS, `extra` every field
    beyond DONE_KEYS; `by_why` the rows by why, `by_target` by target, `repinned` the targets handed back more than
    once (the re-pin loop across melees). `repins` {melees, total, steps}: the melees whose lines read REPINS above 0,
    the sum of each one's last REPINS, and the entries into the REPIN_STEP step."""
    if not G19._spans(lines) or not meet_log(lines):
        return {"read": False}
    target = {a.get("aid"): E._d(a.get("args")).get("targetId")
              for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions")))}
    rows, rp = [], {"melees": 0, "total": 0, "steps": 0}
    for aid, lns in _melee_lines(lines).items():
        last, prev = 0, None
        for ln in lns:
            res = E._d(ln.get("result"))
            n = E._n(res.get(REPINS))
            last = int(n) if n is not None else last
            if ln.get("state") == "progress":
                st = res.get("step")
                rp["steps"] += 1 if st == REPIN_STEP and prev != REPIN_STEP else 0
                prev = st
            if ln.get("state") == "done" and res.get("end") == HANDBACK:
                rows.append({"aid": aid, "seq": ln.get("seq"),
                             "target": res.get(TARGET) if res.get(TARGET) is not None else target.get(aid),
                             "why": res.get("why"), "id": res.get("id"), "d": res.get("d"), "n": res.get(CROWD_N),
                             "ds": res.get(CROWD_DS), "repins": res.get(REPINS),
                             "extra": {k: v for k, v in res.items() if k not in DONE_KEYS}})
        rp["melees"] += 1 if last > 0 else 0
        rp["total"] += last
    by_why, by_t = {}, {}
    for r in rows:
        G14._inc(by_why, str(r["why"]))
        G14._inc(by_t, str(r["target"]))
    return {"read": True, "handbacks": len(rows), "by_why": by_why, "by_target": by_t,
            "repinned": sorted(t for t, n in by_t.items() if n > 1), "repins": rp,
            "rows": sorted(rows, key=lambda r: r["seq"] or 0)}


# ---------------------------------------------------------------- the Dress
def _bleed_onsets(frames, walls):
    """{part: [wallMs]} of each part's bleeding onsets: a frame reading the part `bleeding` true after one not (the
    first frame's bleeding parts included)."""
    out, prev = {}, set()
    for f, w in zip(frames, walls):
        now = {p.get("i") for p in (E._d(x) for x in E._l(E._d(f.get("body")).get("parts")))
               if p.get("bleeding") is True}
        for i in now - prev:
            out.setdefault(i, []).append(w)
        prev = now
    return out


def _close(row, how, wall):
    row.update(end=how, end_wall=wall)


def e_dresses(L):
    """Each Dress maneuver (Plan 31 Task 8, the default under P31-H): {read, dresses, by_end, rides, failed, rows}
    ({"read": False} without a decision log or a line carrying the care why's `dress`). Reading, off the decision
    lines' care why (`inputs.branches.care`): a Dress starts on a line carrying `dress` while none is open, or one
    whose part differs from the open one's or whose `sends` fell (the open one then closed `unlogged`); it ends on
    the first line whose `dress_end` list holds an entry of its part (`end` that entry's end, `fail` its fail, `lost`
    and `sends` its counts; an entry matching no open Dress ends the latest `unlogged` one of its part, its wall the
    entry's line's). Per row {part, line (1-based), wall, ride, stop, unworn, torn, bandages, end, fail,
    lost, sends, end_wall, s, onset_s, onset_to_start_s, onset_to_end_s}: the commands the care branch sent while it
    was open (a line `sent` with an action of DRESS_SENDS), `stop` {sent_s (from the start), still_s (from the stop's
    send to the first later line whose phase is PICK_PHASE: the still wait over), still_waits (the lines in
    STILL_PHASE)}, the unwears' and the rips' item ids (the garments unworn and torn), the bandages {item, kind};
    `s` the Dress's wall seconds; inference off the walls: `onset_s` the part's last bleeding onset at or before the
    start (`_bleed_onsets`, the frames' wall less the start's, negative before it) and `onset_to_*` the seconds from
    it to the start and to the end (None without an onset). `rides` the rows whose `ride` is true; `by_end` the rows
    by end ("open" for one with no end logged)."""
    if L is None:
        return {"read": False}
    walls, frames = L.index
    onsets = _bleed_onsets(frames, walls)
    rows, cur, any_line = [], None, False
    for n, ln in enumerate(L.rows):
        care = E._bw(ln, CARE)
        w = E._n(ln.get("wall"))
        for e in (E._d(x) for x in E._l(care.get(DRESS_END_KEY))):
            hit = cur if cur is not None and e.get("part") == cur["part"] else next(
                (r for r in reversed(rows) if r["part"] == e.get("part") and r["end"] == "unlogged"), None)
            if hit is None:
                continue
            _close(hit, e.get("end"), w)
            hit.update(fail=e.get("fail"), lost=e.get("lost"), sends=e.get("sends"))
            if hit is cur:
                cur = None
        d = care.get(DRESS_KEY)
        if isinstance(d, dict):
            any_line = True
            if cur is not None and (d.get("part") != cur["part"] or (E._n(d.get("sends")) or 0) < cur["_sends"]):
                _close(cur, "unlogged", cur["_last"])
                cur = None
            if cur is None:
                cur = {"part": d.get("part"), "line": n + 1, "wall": w, "ride": d.get("ride") is True,
                       "stop": {"sent_s": None, "still_s": None, "still_waits": 0}, "unworn": [], "torn": [],
                       "bandages": [], "end": None, "fail": None, "lost": d.get("lost"), "sends": d.get("sends"),
                       "end_wall": None, "_sends": 0, "_last": w, "_stop_w": None}
                rows.append(cur)
            cur["_sends"], cur["_last"] = E._n(d.get("sends")) or 0, w
            cur["lost"], cur["sends"] = d.get("lost"), d.get("sends")
            if d.get("phase") == STILL_PHASE:
                cur["stop"]["still_waits"] += 1
            if d.get("phase") == PICK_PHASE and cur["_stop_w"] is not None and cur["stop"]["still_s"] is None \
                    and w is not None:
                cur["stop"]["still_s"] = w - cur["_stop_w"]
            a = E._d(ln.get("action"))
            if ln.get("sent") is True and ln.get("branch") == CARE and a.get("type") in DRESS_SENDS:
                t, iid = a.get("type"), E._d(a.get("args")).get("itemId")
                if t == "stop" and cur["stop"]["sent_s"] is None and w is not None and cur["wall"] is not None:
                    cur["stop"]["sent_s"], cur["_stop_w"] = w - cur["wall"], w
                elif t == "unwear":
                    cur["unworn"].append(iid)
                elif t == "rip":
                    cur["torn"].append(iid)
                elif t == "bandage":
                    cur["bandages"].append({"item": iid, "kind": d.get("kind")})
    if not any_line:
        return {"read": False}
    by = {}
    for r in rows:
        for k in ("_sends", "_last", "_stop_w"):
            r.pop(k)
        G14._inc(by, str(r["end"]) if r["end"] is not None else "open")
        w0, w1 = r["wall"], r["end_wall"]
        r["s"] = w1 - w0 if w0 is not None and w1 is not None else None
        on = [o for o in onsets.get(r["part"], []) if w0 is not None and o is not None and o <= w0 * 1000.0]
        o = on[-1] / 1000.0 if on else None
        r["onset_s"] = o - w0 if o is not None else None
        r["onset_to_start_s"] = w0 - o if o is not None else None
        r["onset_to_end_s"] = w1 - o if o is not None and w1 is not None else None
    return {"read": True, "dresses": len(rows), "by_end": by, "rides": sum(1 for r in rows if r["ride"]),
            "failed": sum(1 for r in rows if r["end"] == "failed"), "rows": rows}


# ---------------------------------------------------------------- the readings, the grade
def readings_x1(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`), each over the sources clipped at the loop's stop (`clip`)."""
    out, rows, lines, clock = clip(out, decision_lines, lines)
    L = E._Lines(out, rows, lines) if rows is not None else None
    frames = L.index[1] if L is not None else E._frame_index(lines)[1]
    kills = _event_kills(lines)
    return {"clip": clock, "landed_hits": landed_hits(frames, lines, len(kills)), "fleeing": e_fleeing(L),
            "toward_target": e_toward_target(L), "wounds_dressed": e_wounds_dressed(frames),
            "melees_superseded": e_melees_superseded(out, lines), "meet_presses": e_meet_presses(out, lines),
            "meet_refusals": e_meet_refusals(lines), "meet_finishes": e_meet_finishes(out, lines),
            "meet_handbacks": e_meet_handbacks(out, lines), "dresses": e_dresses(L)}


def apply_x1(g, out, decision_lines, lines):
    """grade dict `g` (grade_e21's or grade_f12's) with the new readings (`readings_x1`), in place."""
    g.update(readings_x1(out, decision_lines, lines))
    return g


def session_kind(out, goal_lines=None):
    """"f" for an LLM session (a goals log given, or the record's `loop.llm`, the F driver's), else "e"."""
    return "f" if goal_lines is not None or "llm" in E._d(E._d(out).get("loop")) else "e"


def _f(v):
    return "%.3f" % v if isinstance(v, float) else str(v)


def _unread(name):
    return "%s: no line read (no source, or no line carrying its field)" % name


def _round(v, n=2):
    return round(v, n) if isinstance(v, float) else v


def lines_x1(g):
    """One report line per new reading (`NEW`), each clause marked reading or inference."""
    c, h, fl, tw, wd, ms = (E._d(g.get(x)) for x in NEW[:6])
    mp, mr, mf, mh, dr = (E._d(g.get(x)) for x in NEW[6:])
    out = []
    out.append("clip (the loop's stop) [reading]: the new readings cut at %s s after loop.startPyMs %s; dropped %s "
               "state lines (%s frames), %s decision lines, %s actions" % (
                   _f(c.get("stop_s")), _f(c.get("start_ms")), c.get("lines"), c.get("frames"), c.get("decisions"),
                   c.get("actions")) if c.get("read") else
               "clip (the loop's stop): no loop start or stop on the record, the new readings read whole")
    out.append("landed hits (the scorecard's: the reaction segments, the reflex's hit steps) [reading]: %s segments, "
               "%s hit steps; [inference] %s joined, %s attacks landed, %s a kill over %s kills (zombie_dead events)"
               % (h.get("runs"), h.get("steps"), h.get("joined"), h.get("union"), _f(h.get("per_kill_union")),
                  h.get("kills")) if h.get("read") else _unread("landed hits"))
    out.append("fleeing (the trial loop's) [reading]: %s lines, %s game minutes (%s s) over %s, by %s; the legs %s; "
               "[inference] away from a chaser with no refuge named %s intervals, %s game minutes (%s under a "
               "refuge skipped)" % (
                   fl.get("lines"), _f(fl.get("minutes")), _f(fl.get("seconds")), _f(fl.get("total_minutes")),
                   fl.get("by"), {k: (v["lines"], _round(v["minutes"])) for k, v in E._d(fl.get("legs")).items()},
                   E._d(fl.get("away")).get("intervals"), _f(E._d(fl.get("away")).get("minutes")),
                   E._d(fl.get("away")).get("refuge_skipped")) if fl.get("read") else _unread("fleeing"))
    out.append("toward a named target (the trial loop's) [inference]: %s lines, %s game minutes over %s (named on %s "
               "lines, %s min; %s unresolved), by %s" % (
                   tw.get("lines"), _f(tw.get("minutes")), _f(tw.get("total_minutes")), tw.get("named_lines"),
                   _f(tw.get("named_minutes")), tw.get("unresolved"), tw.get("by")) if tw.get("read") else
               _unread("toward a named target"))
    out.append("wounds dressed (the scorecard's, every wound, within DRESS_MIN %s game minute) [reading]: %s of %s "
               "wounds (%s carried from the first frame), %s closed: %s" % (
                   DRESS_MIN, wd.get("dressed"), wd.get("wounds"), wd.get("carried"), wd.get("stopped"),
                   [(r["part"], r["seq0"], r["seq1"], _round(r["minutes"]), r["bandaged"])
                    for r in E._l(wd.get("rows"))]) if wd.get("read") else _unread("wounds dressed"))
    out.append("melees superseded before their press [reading]: %s of %s sent (%s superseded in all, %s with no swing "
               "step) %s" % (ms.get("superseded_before"), ms.get("sent"), ms.get("superseded"),
                             ms.get("no_swing_step"), ms.get("aids")))
    out.append("meet presses (PZA/1.10's leaf against its outcome) [reading]: %s presses by kind %s, by outcome %s (%s "
               "refused); the shoves %s knocked %s, expected rolls %s summed %s" % (
                   mp.get("presses"), mp.get("by_kind"), mp.get("by_outcome"), mp.get("refused"),
                   E._d(mp.get("shoves")).get("n"), E._d(mp.get("shoves")).get("knocked"),
                   E._d(mp.get("shoves")).get("knock_p_n"), _f(E._d(mp.get("shoves")).get("knock_p_sum")))
               if mp.get("read") else _unread("meet presses"))
    out.append("meet refusals [reading]: %s runs, %s refused presses, by count %s, %s waits, %s melees ended refused, "
               "%s open" % (mr.get("runs"), mr.get("refused"), mr.get("by_count"), mr.get("waits"), mr.get("ended"),
                            mr.get("open")) if mr.get("read") else _unread("meet refusals"))
    out.append("meet finishes [reading]: %s sent in mode finish, headAim %s; the finish presses %s by outcome %s (%s "
               "kills), %s turns to the head" % (
                   mf.get("sent_finish"), mf.get("head_aim"), mf.get("presses"), mf.get("by_outcome"),
                   mf.get("kills"), mf.get("heads")) if mf.get("read") else _unread("meet finishes"))
    out.append("meet handbacks [reading]: %s handbacks by why %s, by target %s, handed back again %s; the crowds %s; "
               "the reflex's re-pins %s" % (
                   mh.get("handbacks"), mh.get("by_why"), mh.get("by_target"), mh.get("repinned"),
                   [(r["n"], r["ds"]) for r in E._l(mh.get("rows")) if r["why"] == "crowd"], mh.get("repins"))
               if mh.get("read") else _unread("meet handbacks"))
    out.append("dresses (the Dress maneuver) [reading]: %s Dresses by end %s (%s rides, %s failed): %s; [inference] "
               "the seconds from the part's bleeding onset to the start and the end %s" % (
                   dr.get("dresses"), dr.get("by_end"), dr.get("rides"), dr.get("failed"),
                   [(r["part"], r["end"], r["torn"], r["unworn"], _round(r["s"], 1)) for r in E._l(dr.get("rows"))],
                   [(r["part"], _round(r["onset_to_start_s"], 1), _round(r["onset_to_end_s"], 1))
                    for r in E._l(dr.get("rows"))]) if dr.get("read") else _unread("dresses"))
    return out


def report_lines_x1(g):
    """The base's report lines (grade_f12's, or grade_e21's with its gate line naming gate_x1), then `lines_x1`."""
    g = E._d(g)
    if g.get("base") == "grade_f12":
        base = G12.report_lines_f12(g)
    else:
        base = [("gate_x1 " + ln[len("gate_e21 "):]) if ln.startswith("gate_e21 ") else ln
                for ln in G21.report_lines_e21(g)]
    return base + lines_x1(g)


def grade_x1(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """The base grade (`kind` "f": grade_f12, "e": grade_e21; None: `session_kind`) under "grade_x1" with `base` its
    name and the new readings (`apply_x1`), over the state lines of `state_dir` unless `lines` is given (read once and
    handed down, `frames_files` restored as grade_f12 restores it)."""
    record = E._d(record)
    kind = session_kind(record, goal_lines) if kind is None else kind
    if kind not in KINDS:
        raise ValueError("kind %r is none of %s" % (kind, KINDS))
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    if kind == "f":
        g = G12.grade_f12(record, prev, decision_lines, state_dir, lines, goal_lines)
    else:
        g = G21.grade_e21(record, prev, decision_lines, state_dir, lines=lines)
    g["base"], g["grade"] = g["grade"], "grade_x1"
    if files and "frames_files" in g:
        g["frames_files"] = files
    apply_x1(g, record, decision_lines, lines)
    g["report_lines"] = report_lines_x1(g)
    return g


def gate_x1(outs):
    """gate_e21 (grade_x1 changes none of what it reads), named gate_x1."""
    return G21.gate_e21(outs)
