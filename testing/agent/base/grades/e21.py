"""grades.e21 -- the chain sessions' grade, pass 21 (Plan 30 Task 4): `grade_e21` is `grades.e20.grade_e20` under
"grade_e21" with the hits and the kills read as the plan's measure counts them (ruling P29-K's grade change, the hits'
frame gap; the spec `2026-11-05-plan-30-the-intent-design.md` section 1 reading 5, #4638, #4639) and one reading per
rule of survival iteration 24 (Plan 30 Task 3, `T14_SWITCHES`) with the standing minutes, each read off the frames,
the state log's act lines and events, the artifact's actions and the decision log's why fields:

  hits_union     the hits as the union of the frames' reaction runs (`e18._hit_runs`'s start rule) with the reflex's
                 `hit` steps (a melee's progress lines, one per run of consecutive `hit` steps), a step within one
                 frame interval of a run joining it: the 10 Hz frames miss a reaction shorter than their step (P29-K;
                 F14's a104, a128 and a212: #4638), and `per_kill_union` over `kills_matched.planner`.
  kills_matched  the kills read whole (`e20.e_kills_whole`) and a `zombie_dead` event no act or done line names matched
                 to the last killing press whose swing event came within MATCH_FRAMES frames before it at the dead
                 zombie within the press's reach (F14's 32434 beside the ladder's floor attack a59 at 32433, #4639).
  sneak          P30-D, the sneak gait (`SNEAK`): the frames' `me.sneaking` (PZA/1.9) by game minute, the sneak walk's
                 speed, the zombies passed within SNEAK_R with no target change, the first change under it.
  goal_wait      P30-B, no standing on a model wait (`GOAL_CONTINUE`): the standing on the wait (`unmoved_near_s`, the
                 plan's reading), the desk read's pending runs near a zombie (`near_runs`, movement not read), the
                 explore hops' lengths, the continued walk's and the extended hop's lines.
  door_held      P30-C, the door held (`DOOR_HELD`): the decisions by kind and decision, the stance's door steps, the
                 kills within DOOR_KILL_S after a `stance_open`.
  swing_close    P30-A, the swing close (`SWING_CLOSE`): the Lua's `held` and `again`, the back steps after a press by
                 its landing, the hits (the union's) inside a back step.
  still          P30-E, the still read (`STILL`): the resolutions by kind.
  dress_ride     P30-F, the dressing under a fast bleed (`DRESS_RIDE`): the rides, the health across each.
  standing       the stretches of STAND_LINES or more decision lines with the character within STILL_MOVE_R of the
                 stretch's first position and a zombie within NEAR_R on every line, by the stretch's branch (the form
                 of Plan 29's desk read `pause-and-door-read.md` section A.1).

A rule's reading is {"read": False} without its source (a decision log; for `sneak` frames carrying `me.sneaking`, for
`swing_close` a melee span) and reads False on a source no line of which carries the rule's own field (a log written
before iteration 24, F14's and E23's). The rule's own field is the planner's log of the rule firing, never the
instrument: `sneak` reads True only on a log carrying `inputs.sneak` (logged with the `sneak` cap and the switch on)
and `swing_close` only on a melee sent with `closeR` above 0 (the switch on); the instrument, PZA/1.9's `me.sneaking`
and the Lua's `held`/`again` (present with the rule off too), is named apart as `capable`. Under `read` False the
rule's own firing leaves read None (`goal_wait`'s `continued` and `extended`, `swing_close`'s `held`, `again` and
`lines`, `sneak`'s `postures`), and the measures stay (the baselines the plan's measure compares: the standing on a
model wait, the bites in a back step, the sneak's minutes), as `e20.e_goal_stall` keeps its ends. A key marked reading
counts what the log, the frames or the artifact states; one marked inference reads an effect off the order of lines or
the walls. The clocks: a decision line's `wall` is the planner's epoch seconds, a state-log line's `wallMs` the Lua's
epoch milliseconds, one host clock (a frame is joined to a line as the frame at or before `wall` x 1000, `gates_e`
`_frame_at`); a frame interval is the frames' own `wallMs` gaps; a game minute is the frame's or the line's `gameMin`.

Every live planner name read here is copied below as a frozen constant with its source and its value at 8901afdb
(Plan 30 Task 3's last commit; ruling P26-Q, `grades/__init__.py`); the why keys are read off Task 3's committed code
at that commit (`goal_runner.py` `tick`'s `goal_continue` and `hop_extended`, `survive.py` `_apply`'s `sneak` and
`_decide`'s `door_held`, `door_held.py` `_door_open_cmd`'s `door_step`, `threat.py` `_decide`'s `still` and
`_dress_waits`' `dress_ride`, `maneuvers/melee.py` `_log`'s `swing_close`), the frame's and the act lines' shapes off
the schema (`schema/pza1.json` `me.sneaking`, the zombie's `hasTarget` and `state`, `args_melee.closeR`,
`result_melee_step` `held` and `again`, PZA/1.9), the step names off the Lua (`PZAgent_StanceMelee.lua`) and the
presses' reaches off the engine's rows (#4592). This module imports nothing from `agent.base.planner` or
`agent.base.world`; the chain it imports (`grades.e20.grade_e20`, which reads live names through `e19` to `e14` and
`gates_e`) is pinned by the regrade tests of the artifacts graded through it. Frozen once an artifact carries its
output; `gates_e`, `grades/e14.py` to `grades/e20.py` and every driver stay untouched."""
import bisect
import math
import statistics

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e18 as G18
from agent.base.grades import e19 as G19
from agent.base.grades import e20 as G20

# Frozen copies of the live names read here (P26-Q), each as it stood at 8901afdb (the line there).
SNEAK_R = 8.0          # planner/policies.py:405 (P30-D): tiles, a zombie listed this near and no chaser: the sneak
STILL_DRIFT_R = 0.3    # planner/policies.py:390 (P30-E): tiles of drift read as unmoved (the goal wait's stand)
STILL_MOVE_R = 1.0     # planner/policies.py:392 (P30-E): "unmoved under a tile" (the standing stretch's bound)
SHOVE_REACH = 1.1      # #4592: the shove's hit list, a standing target's nearest point under the bare hands' MaxRange
SHOVE_LUNGE = 0.20000000298023224   # #4592: added against a zombie lunging at the shover from under 2 tiles
SHOVE_R = SHOVE_REACH + SHOVE_LUNGE   # tiles: the shove's widest hit list (#4592's 1.3000000029802322, arithmetic)
STOMP_R = 0.6000000238418579   # #4592 (#4372's): tiles, the floor target the stomp plays at; the engine reads the
                               # nearest of head, pelvis and position, this grade the position (`e18._zd`)
CLOSE_KEY = "closeR"   # schema `args_melee.closeR` (PZA/1.9): a melee sent with it above 0 is the swing close's (P30-A)
LINE_S = 0.5           # driverlib/day.py:85 `PLANNER_HZ` 2: wall seconds one decision line stands for
HIT_STEP = "hit"       # PZAgent_StanceMelee.lua:359: the reflex's step on a tick its own hit reaction read is set
BACK_STEP = "back"     # PZAgent_StanceMelee.lua:311: the back leg's step
PRESS_STEPS = ("swing", "shove", "stomp", "floor")   # e20's (PZAgent_StanceMelee.lua `COUNT`'s keys)
MELEE = "melee"        # the skill's type (schema actionType, PZA/1.8)
WALK = "walkTo"        # the walk's type
SNEAK_GAIT = "walk"    # the Lua's `walk` under the sneak flag is the sneak walk (#4656; `sneak.py` re-gaits to it)
EXPLORE = "ExploreToward"   # the explore goal; its hop is `goal_policies.py:341` `_dist`, the target square off (x, y)
STANCE_OPEN = "stance_open"  # door_held.py:139: the decision that opens the door from the stance
# The grade's own numbers.
MATCH_LADDER = ("attack", "stomp", "shove")   # the ladder's presses an event is matched to (the spec's 4)
MATCH_STEPS = ("swing", "floor", "stomp")     # the melee's press steps an event is matched to (a shove kills nothing)
MATCH_FRAMES = 12      # frames: a death this many frames or fewer after a press's swing event is that press's. On
                       # F14 and E23 the deaths the whole read names trail their own press's swing event by 2 to 11
                       # frames (F14's 32338 at 11, a35's floor swing seq 2687 to its death seq 2703; E23's 26241 at
                       # 2), and no unnamed death has a false candidate within 13; a death past it reads unmatched,
                       # so `agree` False (the brief's 8 widened to cover 11, review-t4 m2)
NEAR_R = 10.0          # tiles: a zombie this near makes a stand a stand near a zombie (the desk read's 10 tiles)
STAND_LINES = 20       # decision lines: a stretch this long is a standing stretch (the desk read's 20)
DOOR_KILL_S = 60.0     # wall seconds after a `stance_open` a kill is counted to the door (the task's amendments)
RULES = ("sneak", "goal_wait", "door_held", "swing_close", "still", "dress_ride")
NEW = ("hits_union", "kills_matched") + RULES + ("standing",)
N_LINES = len(NEW)     # the report lines lines_e21 appends: one per NEW key


def _per(n, k):
    return n / k if k else None


def _hyp(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _near(f):
    """The least distance of the frame's listed zombies (`e18._zd`), else None."""
    ds = [d for d in (G18._zd(f, q) for q in E._l(E._d(f).get("zombies"))) if d is not None]
    return min(ds) if ds else None


def _pos(ln):
    """(x, y) of the decision line's inputs, else None."""
    i = E._d(ln.get("inputs"))
    x, y = E._n(i.get("x")), E._n(i.get("y"))
    return (x, y) if x is not None and y is not None else None


def _wall(ln):
    return E._n(ln.get("wall"))


def _span_s(rows):
    """Wall seconds a run of decision lines stands for: its last line's wall less its first's, and one LINE_S."""
    return (_wall(rows[-1]) or 0.0) - (_wall(rows[0]) or 0.0) + LINE_S


def _runs(flags):
    """The [first, last] index pairs of the runs of True in `flags`."""
    out, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


# ---------------------------------------------------------------- the hits, the union
def _reaction_runs(frames):
    """[(first, last)] frame indices of the reaction runs of `frames` (wall order): `e18._hit_runs`'s start rule, a
    run lasting while the frames read `me.hitReaction` non-empty."""
    out, prev = [], None
    for i, f in enumerate(frames):
        h = G18._reaction(f)
        if h is not None and prev is None:
            out.append([i, i])
        elif h is not None and out:
            out[-1][1] = i
        prev = h
    return [tuple(r) for r in out]


def _step_runs(lines):
    """[(wallMs, seq, aid)] of the reflex's `hit` steps: per melee span (`e19._spans`), one per run of consecutive
    progress lines whose step is HIT_STEP (the heartbeat's repeat is no new hit), at the run's first line, in wall
    order."""
    seqs = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == MELEE \
                and ln.get("state") == "progress":
            seqs.setdefault(ln.get("aid"), []).append(ln.get("seq"))
    out = []
    for s in G19._spans(lines):
        prev = None
        for j, (w, r) in enumerate(s["progress"]):
            st = r.get("step")
            if st == HIT_STEP and prev != HIT_STEP and w is not None:
                q = seqs.get(s["aid"], [])
                out.append((w, q[j] if j < len(q) else None, s["aid"]))
            prev = st
    return sorted(out, key=lambda p: p[0])


def _joins(walls, run, w):
    """Whether a step at wall ms `w` lies within one frame interval of the reaction run (first, last): from the frame
    before the run's first to the frame after its last (the run's own frames at the log's ends)."""
    a, b = run
    lo = walls[a - 1] if a > 0 else walls[a]
    hi = walls[b + 1] if b + 1 < len(walls) else walls[b]
    return lo <= w <= hi


def e_hits_union(frames, lines, kills):
    """The hits as the union (the spec's 5, #4638): {read, runs, steps, joined, union, kills, per_kill_union, rows}
    ({"read": False} without a frame). Reading: `runs` the reaction runs (`_reaction_runs`), `steps` the reflex's
    `hit` step runs (`_step_runs`); inference off the walls: `joined` the steps within one frame interval of a run
    (`_joins`, each joining the first such run; several may join one, a melee re-sent in one reaction), `union` the
    runs and the steps that joined none, `per_kill_union` over `kills` (None at 0); `rows` the union in wall order
    {source ("reaction", "step", "both"), seq and wallMs (the earlier of the run's first frame and its joined step's
    line), aid (the first joined step's), kind (the run's reaction)}."""
    if not frames:
        return {"read": False}
    walls = [E._n(f.get("wallMs")) for f in frames]
    runs, steps = _reaction_runs(frames), _step_runs(lines)
    rows = [{"source": "reaction", "seq": frames[a].get("seq"), "wallMs": walls[a], "aid": None,
             "kind": G18._reaction(frames[a])} for a, _ in runs]
    joined = 0
    for w, seq, aid in steps:
        k = next((i for i, r in enumerate(runs) if _joins(walls, r, w)), None)
        if k is None:
            rows.append({"source": "step", "seq": seq, "wallMs": w, "aid": aid, "kind": None})
            continue
        joined += 1
        row = rows[k]
        row.update(source="both", aid=row["aid"] if row["aid"] is not None else aid)
        if w < row["wallMs"]:
            row.update(seq=seq, wallMs=w)
    k = E._n(kills) or 0
    union = len(runs) + len(steps) - joined
    return {"read": True, "runs": len(runs), "steps": len(steps), "joined": joined, "union": union, "kills": k,
            "per_kill_union": _per(union, k), "rows": sorted(rows, key=lambda r: r["wallMs"])}


# ---------------------------------------------------------------- the kills, matched to the press
def _press_kind(t, step):
    """("ladder", t) of a ladder press an event may be matched to, ("melee", step) of a melee press step, else None."""
    if t in MATCH_LADDER:
        return "ladder", t
    if t == MELEE and step in MATCH_STEPS:
        return "melee", step
    return None


def _reach(t, step, arg, f):
    """The press's reach in tiles: a stomp's STOMP_R and a shove's SHOVE_R (the ladder's or the melee's: the engine's
    hit list, #4592, not the Lua's send gates K.STOMP_R 0.5 and K.SHOVE_R 1.5), an attack's
    the frame's `weapon.reach` (the engine's, max range times range mod), a melee swing's or floor swing's its `reach`
    argument when above 0, else the frame's weapon reach; None for any other press."""
    kind = step if t == MELEE else t
    if kind == "stomp":
        return STOMP_R
    if kind == "shove":
        return SHOVE_R
    w = E._n(E._d(E._d(f).get("weapon")).get("reach"))
    if kind == "attack":
        return w
    if t == MELEE and kind in ("swing", "floor"):
        a = E._n(arg)
        return a if a is not None and a > 0 else w
    return None


def _presses(out, lines):
    """The swing events' presses in log order, each paired on the first frame after its event as `e20.e_facing_all`
    pairs them: {n (the frame's count in the log), seq (the event's), aid, type, step, frame}."""
    types = G18._act_types(out, lines)
    pend, last, prog, n, got = [], None, {}, 0, []
    for ln in E._l(lines):
        if not isinstance(ln, dict):
            continue
        k = ln.get("kind")
        if k == "act" and ln.get("state") == "accepted":
            last = ln
        if k == "act" and ln.get("type") == MELEE and ln.get("state") == "progress":
            prog[ln.get("aid")] = E._d(ln.get("result")).get("step")
        if k == "event" and ln.get("event") == "swing" and ln.get("attackStarted") is True:
            pend.append((ln.get("seq"), E._d(last).get("aid"), dict(prog)))
        elif k == "frame":
            n += 1
            act = E._d(ln.get("act"))
            own = act.get("aid")
            for seq, inferred, before in pend:
                aid = own if own is not None else inferred
                t = types.get(aid)
                step = G20._last_press(before, aid, act.get("step") if own == aid else None) if t == MELEE else None
                got.append({"n": n, "seq": seq, "aid": aid, "type": t, "step": step, "frame": ln})
            pend = []
        yield ln, n, got


def e_kills_matched(out, lines):
    """The kills read whole with the deaths matched to their press (the spec's 4, #4639): `e20.e_kills_whole`'s keys
    with `whole` and `whole_ids` (its count and ids), `planner` and `planner_ids` the whole ids then the matched,
    `matched`, `by_source`, `unmatched` (None without lines) and `agree` (the union against the events; None without
    lines). Inference off the order of lines: a `zombie_dead` event whose id the whole read lacks is matched to the
    latest press (`_presses`) whose swing event came at most MATCH_FRAMES frames before it (`frames_before`: the frames
    from the one after the swing event to the death), a killing press (`_press_kind`: the ladder's attack, stomp or
    shove, the melee's swing, floor or stomp step) whose frame after the event lists the dead zombie within the press's
    reach (`_reach`) of the character; each row {id, aid, type, step, source, seq (the swing event's), frames_before, d,
    reach}."""
    out = E._d(out)
    w = G20.e_kills_whole(out, lines)
    got = dict(w, whole=w["planner"], whole_ids=list(w["planner_ids"]))
    ids, matched, unmatched = list(w["planner_ids"]), [], []
    if not lines:
        return dict(got, matched=[], by_source={}, unmatched=None)
    args = {a.get("aid"): E._d(a.get("args")) for a in (E._d(x) for x in E._l(E._d(out.get("loop")).get("actions")))}
    seen = set(ids)
    for ln, n, presses in _presses(out, lines):
        if ln.get("kind") != "event" or ln.get("event") != "zombie_dead" or ln.get("id") in seen:
            continue
        zid = ln.get("id")
        seen.add(zid)
        row = None
        for p in reversed(presses):
            fb = n - p["n"] + 1
            if fb > MATCH_FRAMES:
                break
            kind = _press_kind(p["type"], p["step"])
            if kind is None:
                continue
            reach = _reach(p["type"], p["step"], args.get(p["aid"], {}).get("reach"), p["frame"])
            q = next((E._d(x) for x in E._l(p["frame"].get("zombies")) if E._d(x).get("id") == zid), None)
            d = G18._zd(p["frame"], q) if q is not None else None
            if d is not None and reach is not None and d <= reach:
                row = {"id": zid, "aid": p["aid"], "type": p["type"], "step": p["step"], "source": kind[0],
                       "seq": p["seq"], "frames_before": fb, "d": d, "reach": reach}
                break
        if row is None:
            unmatched.append(zid)
        else:
            matched.append(row)
            ids.append(zid)
    by = {}
    for r in matched:
        G14._inc(by, r["source"])
    events = w["event_ids"]
    return dict(got, planner=len(ids), planner_ids=ids, matched=matched, by_source=by, unmatched=unmatched,
                agree=(set(ids) == set(events)) if events is not None else None)


# ---------------------------------------------------------------- P30-D, the sneak
def _sneaking(f):
    """Whether the frame reads `me.sneaking` true (PZA/1.9's observed flag)."""
    return E._d(E._d(f).get("me")).get("sneaking") is True


def _me(f):
    me = E._d(E._d(f).get("me"))
    x, y = E._n(me.get("x")), E._n(me.get("y"))
    return (x, y) if x is not None and y is not None else None


def _legs(out, lines, frames, walls):
    """The walkTo legs sent while sneaking: [{aid, gait, tiles, s, speed}] in accept order. Reading: a leg is a walkTo's
    accepted act line to its terminal line (`e14._acts`), sent while sneaking when the first frame at or after its
    accept reads `me.sneaking` true, its gait the artifact's `args.gait`; inference off the frames: `tiles` the path
    over the frames from its accept to its end, `s` their wall span, `speed` tiles over s (None at 0 s)."""
    gaits = {a.get("aid"): E._d(a.get("args")).get("gait")
             for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions")))}
    rows = []
    for aid, (w0, end) in sorted(G14._acts(lines, WALK).items(), key=lambda p: p[1][0] or 0):
        w1 = E._n(E._d(end).get("wallMs"))
        if w0 is None or w1 is None:
            continue
        span = frames[bisect.bisect_left(walls, w0):bisect.bisect_right(walls, w1)]
        if not span or not _sneaking(span[0]):
            continue
        pts = [p for p in (_me(f) for f in span) if p is not None]
        tiles = sum(_hyp(a, b) for a, b in zip(pts, pts[1:]))
        s = (E._n(span[-1].get("wallMs")) - E._n(span[0].get("wallMs"))) / 1000.0
        rows.append({"aid": aid, "gait": gaits.get(aid), "tiles": tiles, "s": s, "speed": tiles / s if s > 0 else None})
    return rows


def e_sneak(out, L, lines, frames):
    """P30-D, the sneak gait (`SNEAK`): {read, capable, frames, minutes, seconds, walk_speed, legs, near, passed,
    noticed, chasing, first_change, postures} ({"read": False} without a frame reading `me.sneaking` a boolean: a log
    before PZA/1.9). `capable` True (the frames carry the instrument); `read` True only on a decision log a line of
    which carries `inputs.sneak` (the rule's own log, written with the `sneak` cap and the switch on: survive.py:1237),
    else False with the frames' measures kept and `postures` None. Reading, off the frames: `frames` those sneaking,
    `minutes` their distinct game minutes, `seconds` the wall gaps from each to the next frame; the zombies listed within SNEAK_R (`e18._zd`) on a sneaking frame (`near`
    their count): `passed` those never reading `hasTarget` true on one, `noticed` those reading it true after not,
    `chasing` those reading it true on their first, `first_change` {seq, id, d, state} the first `noticed` frame;
    `legs` (`_legs`) and `walk_speed` the median speed of the sneak walks (gait SNEAK_GAIT, speed above 0: a leg stood
    still is no walk); `postures` the decision lines' `inputs.sneak` sends by `on` (None unread)."""
    if not any(isinstance(E._d(E._d(f).get("me")).get("sneaking"), bool) for f in frames):
        return {"read": False}
    walls = [E._n(f.get("wallMs")) for f in frames]
    n, mins, secs = 0, set(), 0.0
    last, order, first = {}, [], None
    for i, f in enumerate(frames):
        if not _sneaking(f):
            continue
        n += 1
        gm = E._n(f.get("gameMin"))
        if gm is not None:
            mins.add(int(gm))
        if i + 1 < len(frames) and walls[i] is not None and walls[i + 1] is not None:
            secs += (walls[i + 1] - walls[i]) / 1000.0
        for q in (E._d(x) for x in E._l(f.get("zombies"))):
            d = G18._zd(f, q)
            within = d is not None and d <= SNEAK_R
            zid, on = q.get("id"), q.get("hasTarget") is True
            if within and zid not in last:
                order.append(zid)
                last[zid] = "chasing" if on else "idle"
            elif within and on and last[zid] == "idle":
                last[zid] = "noticed"
                if first is None:
                    first = {"seq": f.get("seq"), "id": zid, "d": d, "state": q.get("state")}
    legs = _legs(out, lines, frames, walls)
    speeds = [r["speed"] for r in legs if r["gait"] == SNEAK_GAIT and r["speed"] is not None and r["speed"] > 0]
    logs = [E._d(ln.get("inputs")).get("sneak") for ln in (L.rows if L is not None else [])]
    logs = [x for x in logs if isinstance(x, dict)]
    postures = None
    if logs:
        postures = {"on": 0, "off": 0}
        for x in logs:
            if x.get("sent") is True:
                postures["on" if x.get("on") is True else "off"] += 1
    return {"read": bool(logs), "capable": True, "frames": n, "minutes": len(mins), "seconds": secs,
            "walk_speed": statistics.median(speeds) if speeds else None, "legs": legs, "near": len(order),
            "passed": [z for z in order if last[z] == "idle"], "noticed": [z for z in order if last[z] == "noticed"],
            "chasing": [z for z in order if last[z] == "chasing"], "first_change": first, "postures": postures}


# ---------------------------------------------------------------- P30-B, the goal wait
def e_goal_wait(L):
    """P30-B, no standing on a model wait (`GOAL_CONTINUE`): {read, lines, runs, seconds, unmoved, unmoved_near,
    unmoved_near_s, near_runs, hops, continued, extended} ({"read": False} without a decision log; `read` False with
    the measures on a log no line of which carries `goal_continue` or `hop_extended`, `continued` and `extended` then
    None). Reading, on the goal why (`inputs.branches.goal`): `lines` those reading `pending` true, `runs` their runs,
    `seconds` the runs' spans (the last line's wall less the first's, and one LINE_S); `unmoved` the pending lines whose
    position (the inputs' x, y) lies within STILL_DRIFT_R of the line before's (line to line at the planner's 2 Hz, so
    any walk slower than STILL_DRIFT_R / LINE_S, 0.6 tiles a second, reads unmoved: read `sneak.walk_speed` before
    citing this against a sneaking wait), `unmoved_near` those whose frame (the frame at or before the line) lists a
    zombie within NEAR_R, `unmoved_near_s` them at LINE_S each: THE STANDING ON THE WAIT, the plan's reading (F14's
    baseline 118 lines, 59.0 s); `near_runs` {runs, lines, s} Plan 29's desk read section A.2 reproduced, the pending
    runs with a zombie within NEAR_R on the frame at their first or last line, movement not read: under P30-B the goal
    stays pending while the continued walk runs, so the rule working does not lower it (F14's 19 runs, 181 lines,
    90.1 s: the spec's "F14's 90 s"), never the plan's reading; `hops`
    the distance from the line's position to each ExploreToward taken (`proposed`; its `args` target, extended or not:
    `goal_policies.py:341` `_dist`); `continued` {lines, sent, by_source} the lines carrying `goal_continue` {target,
    source}, those sending its walkTo, by source; `extended` {lines, lengths} the lines carrying `hop_extended` {from,
    to} and each hop's added length."""
    if L is None:
        return {"read": False}
    rows = L.rows
    pend = [E._bw(ln, "goal").get("pending") is True for ln in rows]

    def near(ln):
        d = _near(L.frame(ln))
        return d is not None and d <= NEAR_R

    def ends_near(first, last):
        return near(first) or near(last)

    unmoved = near_n = 0
    for i, ln in enumerate(rows):
        if not pend[i] or i == 0:
            continue
        a, b = _pos(ln), _pos(rows[i - 1])
        if a is not None and b is not None and _hyp(a, b) < STILL_DRIFT_R:
            unmoved += 1
            near_n += 1 if near(ln) else 0
    runs = _runs(pend)
    nr = [(a, b) for a, b in runs if ends_near(rows[a], rows[b])]
    hops, cont, ext = [], {"lines": 0, "sent": 0, "by_source": {}}, {"lines": 0, "lengths": []}
    for ln in rows:
        g = E._bw(ln, "goal")
        p, t = _pos(ln), G20._xy([E._d(g.get("args")).get("x"), E._d(g.get("args")).get("y")])
        if g.get("proposed") == EXPLORE and p is not None and t is not None and None not in t:
            hops.append(_hyp(t, p))
        c = g.get("goal_continue")
        if isinstance(c, dict):
            cont["lines"] += 1
            cont["sent"] += 1 if E._sent(ln, WALK) else 0
            G14._inc(cont["by_source"], str(c.get("source")))
        h = g.get("hop_extended")
        if isinstance(h, dict):
            ext["lines"] += 1
            f, t = G20._xy(h.get("from")), G20._xy(h.get("to"))
            ext["lengths"].append(_hyp(t, f) if f is not None and t is not None else None)
    read = bool(cont["lines"] or ext["lines"])
    return {"read": read, "lines": sum(pend), "runs": len(runs),
            "seconds": sum(_span_s(rows[a:b + 1]) for a, b in runs), "unmoved": unmoved, "unmoved_near": near_n,
            "unmoved_near_s": near_n * LINE_S,
            "near_runs": {"runs": len(nr), "lines": sum(b - a + 1 for a, b in nr),
                          "s": sum(_span_s(rows[a:b + 1]) for a, b in nr)},
            "hops": hops, "continued": cont if read else None, "extended": ext if read else None}


# ---------------------------------------------------------------- P30-C, the door held
def e_door_held(L, lines):
    """P30-C, the door held (`DOOR_HELD`): {read, lines, by_kind, by_decision, by, doors, steps, kills_after_open,
    kill_ids} ({"read": False} without a decision log or a line carrying it). Reading, on the threat why: `lines` those
    carrying `door_held` {door, kind, n_behind, decision} (logged on the tick a decision is first read and again when
    the door, the decision or the zombies behind change), them by kind, by decision and by both, `doors` the doors each
    once; `steps` the lines by the stance's door step (`door_step` post, open, meet); inference off the walls:
    `kills_after_open` the `zombie_dead` events within DOOR_KILL_S after a `stance_open` line, `kill_ids` theirs."""
    if L is None:
        return {"read": False}
    kinds, decs, by, doors, steps, opens = {}, {}, {}, [], {}, []
    n = 0
    for ln in L.rows:
        w = L.why(ln)
        st = w.get("door_step")
        if isinstance(st, str):
            G14._inc(steps, st)
        dh = w.get("door_held")
        if not isinstance(dh, dict):
            continue
        n += 1
        G14._inc(kinds, str(dh.get("kind")))
        G14._inc(decs, str(dh.get("decision")))
        G14._inc(by, "%s %s" % (dh.get("kind"), dh.get("decision")))
        if dh.get("door") not in doors:
            doors.append(dh.get("door"))
        if dh.get("decision") == STANCE_OPEN and _wall(ln) is not None:
            opens.append(_wall(ln))
    if not n:
        return {"read": False}
    kill_ids = []
    for ev in E._l(lines):
        if not (isinstance(ev, dict) and ev.get("kind") == "event" and ev.get("event") == "zombie_dead"):
            continue
        ms = E._n(ev.get("wallMs"))
        w = ms / 1000.0 if ms is not None else None
        if w is not None and ev.get("id") not in kill_ids and any(0 < w - t and w - t <= DOOR_KILL_S for t in opens):
            kill_ids.append(ev.get("id"))
    return {"read": True, "lines": n, "by_kind": kinds, "by_decision": decs, "by": by, "doors": doors,
            "steps": steps, "kills_after_open": len(kill_ids), "kill_ids": kill_ids}


# ---------------------------------------------------------------- P30-A, the swing close
def _last_count(s, key):
    """The span's last progress or terminal result carrying `key` as a number, else None."""
    res = [r for _, r in s["progress"]] + ([E._d(s["terminal"].get("result"))] if s["terminal"] is not None else [])
    return next((E._n(r.get(key)) for r in reversed(res) if E._n(r.get(key)) is not None), None)


def e_swing_close(out, L, lines, rows):
    """P30-A, the swing close (`SWING_CLOSE`): {read, capable, held, again, lines, back, bites_in_back} ({"read":
    False} without a melee span). `read` True only when the artifact's actions carry a melee sent with `closeR` above 0
    (CLOSE_KEY: the rule's own send, the switch on; dispatch.py's `_melee_inputs` sends 0 with it off), else False with
    `held`, `again` and `lines` None and the measures kept; `capable` whether a melee act line carries `held` or
    `again` (the instrument, PZA/1.9's Lua, present with the rule off too). Reading, off the melee's act lines
    (`e19._spans`): `held` and `again` each span's last count summed (PZA/1.9's
    `result_melee_step`: the stance held at a chaser beyond closeR, the swings pressed again after one that did
    nothing); `lines` the decision lines whose threat why's `maneuver` carries `swing_close` {held, pressed_again}
    (None without a log). Inference off the order of lines: `back` {after_landed, after_nothing, no_press} each entry
    into BACK_STEP by the span's last press entry before it (a PRESS_STEPS step) and its landing, read on the back
    line as `e20._landing` reads the next line (the target lowered or knocked down); `bites_in_back` the hits of the
    union (`rows`, `e_hits_union`) whose wall lies from a back entry's line to the span's next line of another step
    (or its terminal line)."""
    spans = G19._spans(lines)
    if not spans:
        return {"read": False}
    capable = any(_last_count(s, k) is not None for s in spans for k in ("held", "again"))
    read = any(E._d(a).get("type") == MELEE and (E._n(E._d(E._d(a).get("args")).get(CLOSE_KEY)) or 0) > 0
               for a in E._l(E._d(E._d(out).get("loop")).get("actions")))
    held = sum(int(_last_count(s, "held") or 0) for s in spans)
    again = sum(int(_last_count(s, "again") or 0) for s in spans)
    back = {"after_landed": 0, "after_nothing": 0, "no_press": 0}
    periods = []
    for s in spans:
        seq, press, prev = s["progress"], None, None
        for i, (w, r) in enumerate(seq):
            st = r.get("step")
            if st != prev and st in PRESS_STEPS:
                press = r
            elif st != prev and st == BACK_STEP:
                if press is None:
                    back["no_press"] += 1
                else:
                    _, lowered, kd, killed = G20._landing(press, {"state": "progress", "result": r})
                    back["after_landed" if lowered or kd else "after_nothing"] += 1
                nxt = next((q for q in seq[i + 1:] if q[1].get("step") != BACK_STEP), None)
                end = nxt[0] if nxt is not None else E._n(E._d(s["terminal"]).get("wallMs")) if s["terminal"] else w
                periods.append((w, end if end is not None else w))
            prev = st
    bites = 0
    for row in E._l(rows):
        w = row.get("wallMs")
        bites += 1 if w is not None and any(lo <= w <= hi for lo, hi in periods) else 0
    n = None
    if L is not None:
        n = sum(1 for ln in L.rows if isinstance(E._d(L.why(ln).get("maneuver")).get("swing_close"), dict))
    if not read:
        held = again = n = None
    return {"read": read, "capable": capable, "held": held, "again": again, "lines": n, "back": back,
            "bites_in_back": bites}


# ---------------------------------------------------------------- P30-E, the still; P30-F, the dress ride
def e_still(L):
    """P30-E, the still read (`STILL`): {read, resolutions, by, targets, d} ({"read": False} without a decision log
    or a line carrying it). Reading: the lines whose threat why carries `still` {target, d, resolved} (logged once a
    resolution, the read then starting again), them by `resolved` (approach, goal), the targets each once, each
    resolution's distance."""
    rows = G20._lines_with(L, "still") if L is not None else []
    if not rows:
        return {"read": False}
    by, targets, ds = {}, [], []
    for ln in rows:
        s = L.why(ln)["still"]
        G14._inc(by, str(s.get("resolved")))
        if s.get("target") not in targets:
            targets.append(s.get("target"))
        ds.append(E._n(s.get("d")))
    return {"read": True, "resolutions": len(rows), "by": by, "targets": targets, "d": ds}


def _health(f):
    return E._n(E._d(E._d(f).get("body")).get("health"))


def e_dress_ride(L):
    """P30-F, the dressing under a fast bleed (`DRESS_RIDE`): {read, rides, lines, health_lost, rows} ({"read": False}
    without a decision log or a line carrying it). Reading: a ride is a run of consecutive decision lines whose threat
    why carries `dress_ride` {part, rate} on one part; each row {part, lines, rate_max, h0, h1, h_min}: the health on
    the frame at its first line and at its last, the least over the frames between; `health_lost` the h0 less h1
    summed."""
    if L is None:
        return {"read": False}
    rides, prev_part, prev_i = [], None, None
    for i, ln in enumerate(L.rows):
        r = L.why(ln).get("dress_ride")
        if not isinstance(r, dict):
            continue
        part = r.get("part")
        if rides and prev_part == part and prev_i == i - 1:
            rides[-1].append(ln)
        else:
            rides.append([ln])
        prev_part, prev_i = part, i
    if not rides:
        return {"read": False}
    walls, frames = L.index
    out = []
    for ride in rides:
        f0, f1 = L.frame(ride[0]), L.frame(ride[-1])
        lo, hi = E._n(E._d(f0).get("wallMs")), E._n(E._d(f1).get("wallMs"))
        hs = [h for f, w in zip(frames, walls) if lo is not None and hi is not None and lo <= w <= hi
              for h in [_health(f)] if h is not None]
        rates = [E._n(L.why(ln)["dress_ride"].get("rate")) for ln in ride]
        rates = [x for x in rates if x is not None]
        out.append({"part": L.why(ride[0])["dress_ride"].get("part"), "lines": len(ride),
                    "rate_max": max(rates) if rates else None, "h0": _health(f0), "h1": _health(f1),
                    "h_min": min(hs) if hs else None})
    lost = sum(r["h0"] - r["h1"] for r in out if r["h0"] is not None and r["h1"] is not None)
    return {"read": True, "rides": len(out), "lines": sum(r["lines"] for r in out), "health_lost": lost, "rows": out}


# ---------------------------------------------------------------- the standing minutes
def _stretches(L):
    """[(first, last)] line indices of the standing stretches: from a line whose frame lists a zombie within NEAR_R,
    the lines while each one's position lies within STILL_MOVE_R of the first's and its frame lists one, at least
    STAND_LINES of them; the next stretch read from the line that ended the last."""
    rows, out, i = L.rows, [], 0
    near = [(lambda d: d is not None and d <= NEAR_R)(_near(L.frame(ln))) for ln in rows]
    while i < len(rows):
        p0 = _pos(rows[i])
        if not near[i] or p0 is None:
            i += 1
            continue
        j = i
        while j + 1 < len(rows):
            p = _pos(rows[j + 1])
            if not near[j + 1] or p is None or _hyp(p, p0) >= STILL_MOVE_R:
                break
            j += 1
        if j - i + 1 >= STAND_LINES:
            out.append((i, j))
        i = j + 1
    return out


def e_standing(L):
    """The standing minutes (the spec's 6 measure, the desk read's section A.1 form): {read, stretches, lines,
    seconds, game_minutes, by_branch, rows} ({"read": False} without a decision log). Reading: the stretches
    (`_stretches`), each row {first, last (1-based lines), lines, s (its last line's wall less its first's and one
    LINE_S), gm (its game minutes, last less first), branch (its lines' commonest answering branch, "None" for none),
    branches (its lines by branch)}; `by_branch` {branch: {stretches, lines, seconds}}."""
    if L is None:
        return {"read": False}
    rows, out, by = L.rows, [], {}
    for a, b in _stretches(L):
        br = {}
        for ln in rows[a:b + 1]:
            G14._inc(br, str(ln.get("branch")))
        top = max(br.items(), key=lambda kv: kv[1])[0]
        g0, g1 = E._n(rows[a].get("gameMin")), E._n(rows[b].get("gameMin"))
        r = {"first": a + 1, "last": b + 1, "lines": b - a + 1, "s": _span_s(rows[a:b + 1]),
             "gm": g1 - g0 if g0 is not None and g1 is not None else None, "branch": top, "branches": br}
        out.append(r)
        t = by.setdefault(top, {"stretches": 0, "lines": 0, "seconds": 0.0})
        t["stretches"] += 1
        t["lines"] += r["lines"]
        t["seconds"] += r["s"]
    return {"read": True, "stretches": len(out), "lines": sum(r["lines"] for r in out),
            "seconds": sum(r["s"] for r in out), "game_minutes": sum(r["gm"] or 0 for r in out), "by_branch": by,
            "rows": out}


def readings_e21(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`): `kills_matched` read with or without lines (the whole read's own
    sources), `hits_union` and `sneak` {"read": False} without a frame, `swing_close` without a melee span, the others
    without a decision log."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    frames = L.index[1] if L is not None else E._frame_index(lines)[1]
    km = e_kills_matched(out, lines)
    hu = e_hits_union(frames, lines, km["planner"])
    return {"hits_union": hu, "kills_matched": km, "sneak": e_sneak(out, L, lines, frames), "goal_wait": e_goal_wait(L),
            "door_held": e_door_held(L, lines), "swing_close": e_swing_close(out, L, lines, hu.get("rows")),
            "still": e_still(L), "dress_ride": e_dress_ride(L), "standing": e_standing(L)}


def apply_e21(g, out, decision_lines, lines):
    """grade dict `g` (grade_e20's or grade_f11's) with the new readings (`readings_e21`), in place."""
    g.update(readings_e21(out, decision_lines, lines))
    return g


# ---------------------------------------------------------------- the report
def _f(v):
    return "%.3f" % v if isinstance(v, float) else str(v)


def _unread(name):
    return "%s: no line read (no source, or no line carrying its field)" % name


def lines_e21(g):
    """One report line per pass 21 reading (`NEW`), each clause marked reading or inference."""
    u, k, s, w = (E._d(g.get(x)) for x in ("hits_union", "kills_matched", "sneak", "goal_wait"))
    d, c, st, r, sd = (E._d(g.get(x)) for x in ("door_held", "swing_close", "still", "dress_ride", "standing"))
    out = []
    out.append("hits union (P30, the union of the reaction runs and the hit steps) [reading]: %s reaction runs, %s hit "
               "step runs; [inference] %s joined to a run, %s attacks landed, %s a kill over %s kills matched "
               "(`kills_matched.planner`)" % (
                   u.get("runs"), u.get("steps"), u.get("joined"), u.get("union"), _f(u.get("per_kill_union")),
                   u.get("kills")) if u.get("read") else
               "hits union (P30, the union of the reaction runs and the hit steps): no frames read")
    out.append("kills matched (P30, the kills matched to the press) [reading]: the whole read %s %s, the events %s; "
               "[inference] matched %s (%s), unmatched %s: %s kills %s, agree %s" % (
                   k.get("whole"), k.get("whole_ids"), k.get("event_ids"),
                   [(m.get("id"), m.get("aid"), m.get("type"), m.get("step"), m.get("frames_before")) for m in
                    E._l(k.get("matched"))], k.get("by_source"), k.get("unmatched"), k.get("planner"),
                   k.get("planner_ids"), k.get("agree")))
    if s.get("capable"):
        head = ("sneak (iteration 24, P30-D) [reading]: postures sent %s; " % (s.get("postures"),) if s.get("read")
                else _unread("sneak (iteration 24, P30-D)") + " (the frames carry me.sneaking); ")
        out.append(head + "[reading] %s frames sneaking over %s game minutes (%s s); the sneak walk %s tiles a second "
                   "over %s legs; zombies within SNEAK_R %s: passed %s, noticed %s (first %s), chasing %s" % (
                       s.get("frames"), s.get("minutes"), _f(s.get("seconds")), _f(s.get("walk_speed")),
                       len(E._l(s.get("legs"))), s.get("near"), s.get("passed"), s.get("noticed"),
                       s.get("first_change"), s.get("chasing")))
    else:
        out.append(_unread("sneak (iteration 24, P30-D)"))
    if "lines" in w:
        cont, ext = E._d(w.get("continued")), E._d(w.get("extended"))
        head = ("goal wait (iteration 24, P30-B) [reading]: %s continued-walk lines (%s sent, by source %s), %s hops "
                "extended by %s; " % (cont.get("lines"), cont.get("sent"), cont.get("by_source"), ext.get("lines"),
                                      ext.get("lengths"))
                if w.get("read") else _unread("goal wait (iteration 24, P30-B)") + "; ")
        nr = E._d(w.get("near_runs"))
        out.append(head + "[reading] the standing on the wait (the plan's reading): %s pending lines unmoved near a "
                   "zombie (%s s), unmoved under STILL_DRIFT_R %s tiles from the line before (a walk under %s tiles a "
                   "second reads unmoved: read the sneak walk's speed first); %s lines pending in %s runs (%s s), %s "
                   "unmoved; [the desk read's A.2, movement not read, never the plan's reading] %s runs pending with a "
                   "zombie within NEAR_R at an end, %s lines (%s s); the explore hops %s" % (
                       w.get("unmoved_near"), _f(w.get("unmoved_near_s")), STILL_DRIFT_R, STILL_DRIFT_R / LINE_S,
                       w.get("lines"), w.get("runs"), _f(w.get("seconds")), w.get("unmoved"), nr.get("runs"),
                       nr.get("lines"), _f(nr.get("s")), [round(h, 2) for h in E._l(w.get("hops"))]))
    else:
        out.append(_unread("goal wait (iteration 24, P30-B)"))
    out.append("door held (iteration 24, P30-C) [reading]: %s decisions by kind %s, by decision %s, by both %s at %s; "
               "the door steps %s; [inference] %s kills within DOOR_KILL_S after a stance_open %s" % (
                   d.get("lines"), d.get("by_kind"), d.get("by_decision"), d.get("by"), d.get("doors"), d.get("steps"),
                   d.get("kills_after_open"), d.get("kill_ids")) if d.get("read") else
               _unread("door held (iteration 24, P30-C)"))
    if "back" in c:
        b = E._d(c.get("back"))
        head = ("swing close (iteration 24, P30-A) [reading]: %s stances held at a chaser, %s swings pressed again "
                "(%s why lines); " % (c.get("held"), c.get("again"), c.get("lines")) if c.get("read") else
                _unread("swing close (iteration 24, P30-A)") + " (capable %s); " % (c.get("capable"),))
        out.append(head + "[inference] the back steps after a landed press %s, after a press that did nothing %s, "
                   "with no press %s; %s hits in a back step" % (
                       b.get("after_landed"), b.get("after_nothing"), b.get("no_press"), c.get("bites_in_back")))
    else:
        out.append(_unread("swing close (iteration 24, P30-A)"))
    out.append("still (iteration 24, P30-E) [reading]: %s resolutions %s at %s" % (
        st.get("resolutions"), st.get("by"), st.get("targets")) if st.get("read") else
        _unread("still (iteration 24, P30-E)"))
    out.append("dress ride (iteration 24, P30-F) [reading]: %s rides over %s lines, the health lost across them %s: %s"
               % (r.get("rides"), r.get("lines"), _f(r.get("health_lost")),
                  [(x.get("part"), x.get("lines"), x.get("h0"), x.get("h1")) for x in E._l(r.get("rows"))])
               if r.get("read") else _unread("dress ride (iteration 24, P30-F)"))
    out.append("standing (P30, the standing minutes) [reading]: %s stretches of STAND_LINES or more lines unmoved near "
               "a zombie, %s lines, %s s, %s game minutes, by branch %s" % (
                   sd.get("stretches"), sd.get("lines"), _f(sd.get("seconds")), sd.get("game_minutes"),
                   {b: (x.get("stretches"), x.get("lines")) for b, x in E._d(sd.get("by_branch")).items()})
               if sd.get("read") else _unread("standing (P30, the standing minutes)"))
    return out


def report_lines_e21(g):
    """report_lines_e20's lines (the gate line naming gate_e21) then the pass 21 lines (`lines_e21`)."""
    g = E._d(g)
    out = [("gate_e21 " + ln[len("gate_e20 "):]) if ln.startswith("gate_e20 ") else ln
           for ln in G20.report_lines_e20(g)]
    return out + lines_e21(g)


def grade_e21(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e20 under "grade_e21" with the new readings (`apply_e21`), over the state lines of `state_dir` unless
    `lines` is given (read once and handed down)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G20.grade_e20(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e21"
    if files and "frames_files" in g:
        g["frames_files"] = files
    apply_e21(g, out, decision_lines, lines)
    g["report_lines"] = report_lines_e21(g)
    return g


def gate_e21(outs):
    """gate_e13 (neither grade_e14 to grade_e20 nor grade_e21 changes what it reads), named gate_e21."""
    return G20.gate_e20(outs)
