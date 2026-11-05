"""grades.e19 -- the chain sessions' grade, pass 19 (Plan 28 Task 7c): `grade_e19` is `grades.e18.grade_e18` under
"grade_e19" with the four readings of survival iteration 22 (Plan 28 Task 7, cut 1 of the maneuver layer: the Lua
reflex skill `melee` of PZA/1.8, Task 7a, and the planner's `Melee` maneuver behind `MELEE`, Task 7b), each read off
the state log's `melee` act lines (accepted; progress with the result {step, d, hp, swings, shoves, stomps, floors,
knockdowns, hits}; done {end, kill, the counts, hp0, hp1, dMin, steps {step: ticks}}; failed or rejected with its
reason), the frames' `act` group (PZA/1.8's `act.step`) and `cost` group, the reaction runs (`grades.e18._hit_runs`),
the artifact's actions and fights and the decision log's why fields:

  melee          the spans: the melees sent (the artifact's actions) by mode, accepted, their ends by reason, the steps
                 by name off the progress lines (each entry once), the done lines' ticks per step, the frames' act.step
                 (the cross-check), the counts each span's last result carries summed, the kills inside the spans, the
                 planner's re-sends by kind, its mapped ends, the ladder commands it replaced, the mean span and the
                 spans per fight.
  hits_in_melee  the A/B of the architecture review's section 5.1: the reaction runs whose first frame lies inside a
                 span against those outside (and of those, inside a `loop.fights` span: the ladder's fights), the kills
                 inside and outside, the runs per kill each side.
  melee_strike   per run inside a span: the frame's act.step on its first frame and on the frame before, the span's
                 last progress step before it other than `hit`, the last press step (swing, shove, stomp, floor) within
                 STRIKE_BEFORE_S before it, and the strike before it as `hits.strike_before` reads it.
  melee_cost     the frames' `cost.actMs` and `cost.maxActMs` inside the spans against outside: frames, mean and max.

A span is a melee's accepted act line's wallMs to its terminal line's (an open span, a melee with no terminal line, to
its last act line); a run, a kill or a frame lies in a span by its own wallMs (as `e18.e_hits` pairs a run with a
`loop.fights` row by its first frame). `melee` is {"read": False} without a decision log; the other three without a
frame. A key marked reading counts what the log, the frames or the artifact states; one marked inference reads an
effect off the order of lines or the frames' walls.

Every live planner name read here is copied below as a frozen constant with its source and its value at ff6d7b76
(Plan 28 Task 7b's and 7a's commits in, ruling P26-Q, `grades/__init__.py`); the why keys `maneuver` {maneuver, target,
mode, sends, step, d, ...}, `ladder`, `melee` {resend} and `melee_end` {..., end} are read off Task 7b's committed code
(`planner/dispatch.py` `_melee_dispatch` and `_observe_maneuver`, `fight.py` `choose` at 020ea2fb), the act lines'
and the frame's shapes off the schema (`schema/pza1.json` `result_melee`, `result_melee_step`, `act_now` at 689ec7bb)
and the step names off the Lua (`PZAgent_StanceMelee.lua` at ea4ba827). This module imports nothing from
`agent.base.planner` or `agent.base.world`; the chain it imports (`grades.e18.grade_e18`, which reads live names through
`e17` to `e14` and `gates_e`) is pinned by the regrade tests of the artifacts graded through it. Frozen once an artifact
carries its output; `gates_e`, `grades/e14.py` to `grades/e18.py` and every driver stay untouched."""
import bisect

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e18 as G18

# Frozen copies of the live names read here (P26-Q), each as it stood at ff6d7b76 (the line there).
SWING_TYPES = ("attack", "aim", "shove", "stomp")   # planner/policies.py:160: the sends whose `targetDead` is a kill
PRESS_STEPS = ("swing", "shove", "stomp", "floor")  # PZAgent_StanceMelee.lua:91 `COUNT`'s keys: the steps that press
HIT_STEP = "hit"                                    # PZAgent_StanceMelee.lua:328 (reflex 2): a hit reaction's step
MELEE = "melee"                                     # the skill's type (schema actionType, PZA/1.8)
COUNTS = ("swings", "shoves", "stomps", "floors", "knockdowns", "hits")   # result_melee's counts
STRIKE_BEFORE_S = G18.STRIKE_BEFORE_S               # wall seconds a press is read before a run (e18's, P28-M)
NEW = ("melee", "hits_in_melee", "melee_strike", "melee_cost")


def _per(n, k):
    return n / k if k else None


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------- the spans
def _spans(lines):
    """The melee spans of the state log in accept order: [{aid, accept, end, terminal, progress}] where `accept` is the
    accepted line's wallMs, `end` the terminal line's (else the aid's last act line's), `terminal` that line or None
    and `progress` the [(wallMs, result)] of its progress lines in log order; a melee never accepted has no span."""
    by = {}
    for ln in E._l(lines):
        if not isinstance(ln, dict) or ln.get("kind") != "act" or ln.get("type") != MELEE:
            continue
        w = E._n(ln.get("wallMs"))
        s = by.setdefault(ln.get("aid"), {"aid": ln.get("aid"), "accept": None, "end": None, "terminal": None,
                                          "progress": [], "last": None})
        st = ln.get("state")
        if st == "accepted" and s["accept"] is None:
            s["accept"] = w
        elif st == "progress":
            s["progress"].append((w, E._d(ln.get("result"))))
        elif st in G14.TERMINAL and s["terminal"] is None:
            s["terminal"], s["end"] = ln, w
        s["last"] = w if w is not None else s["last"]
    out = []
    for s in by.values():
        if s["accept"] is None:
            continue
        if s["end"] is None:
            s["end"] = s["last"] if s["last"] is not None else s["accept"]
        out.append(s)
    return sorted(out, key=lambda s: s["accept"])


def _terminals(lines):
    """{aid: terminal act line} of every melee act line's aid (a rejected melee's among them)."""
    return {aid: end for aid, (_, end) in G14._acts(lines, MELEE).items() if end is not None}


class _Index:
    """The spans' accepts sorted with the running maximum of their ends, so the span holding a wall is found by
    bisection (`at`): the latest-accepted span whose accept to end holds it."""

    def __init__(self, spans):
        self.spans = spans
        self.accepts = [s["accept"] for s in spans]
        self.reach, hi = [], None
        for s in spans:
            hi = s["end"] if hi is None or s["end"] > hi else hi
            self.reach.append(hi)

    def at(self, w):
        if w is None:
            return None
        j = bisect.bisect_right(self.accepts, w) - 1
        while j >= 0 and self.reach[j] >= w:
            if self.spans[j]["end"] >= w:
                return self.spans[j]
            j -= 1
        return None


def _kills(out, lines, idx):
    """([zombie id], [zombie id]): the kills inside the spans and outside them, each zombie once (its first kill), read
    off the act lines: a melee's result `kill` true (inside), a SWING_TYPES line's `targetDead` true (inside when its
    wallMs lies in a span, as `gates_e._act_kills` reads the kills otherwise). The target id comes from the artifact's
    loop.actions by aid; a kill whose target is unread is not counted (as `_act_kills`)."""
    targets = G18._targets(out)
    seen, inside, outside = set(), [], []
    for ln in E._l(lines):
        if not isinstance(ln, dict) or ln.get("kind") != "act":
            continue
        t, r = ln.get("type"), E._d(ln.get("result"))
        if not ((t == MELEE and r.get("kill") is True) or (t in SWING_TYPES and r.get("targetDead") is True)):
            continue
        zid = targets.get(ln.get("aid"))
        if zid is None or zid in seen:
            continue
        seen.add(zid)
        (inside if t == MELEE or idx.at(E._n(ln.get("wallMs"))) is not None else outside).append(zid)
    return inside, outside


def _fight_of(fights, t0, w):
    """The index of the `loop.fights` row whose span (loop seconds) holds wall ms `w`, else None."""
    t = w / 1000.0 - t0 if w is not None and t0 is not None else None
    return next((j for j, fi in enumerate(fights) if G18._in_span(fi, t)), None)


def _fights(out):
    return [E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("fights")) if isinstance(x, dict)]


# ---------------------------------------------------------------- melee
def _end_key(ln, row):
    """A melee's end: "done <end>", "<state> <reason>", "open" for an accepted span with no terminal line, else the
    artifact row's "<state> <reason>"."""
    if ln is not None:
        st = ln.get("state")
        if st == "done":
            return "done %s" % E._d(ln.get("result")).get("end")
        return "%s %s" % (st, ln.get("reason"))
    return "%s %s" % (E._d(row).get("state"), E._d(row).get("reason"))


def e_melee(out, L, lines, frames, spans, kills_in):
    """The melee spans (survival iteration 22): {read, sent, by_mode, accepted, ends, steps, step_ticks, frame_steps,
    swings, shoves, stomps, floors, knockdowns, hits, kills, resends, planner_ends, replaced, lines, mean_span_s,
    by_fight, outside_fights} ({"read": False} without a decision log). Reading: `sent` the artifact's loop.actions of
    type melee, `by_mode` them by `args.mode`; `accepted` the spans; `ends` every melee's end (`_end_key`: the act
    lines' terminal line, an accepted one with none "open", one with no act line its row's); `steps` the progress
    lines' steps by name, an entry counted once (a step repeated by the once-a-second heartbeat is not a new entry);
    `step_ticks` the done lines' `steps` {step: ticks} summed; `frame_steps` the frames reading `act.step` by step (the
    cross-check, frames at the frame rate); the six counts each span's last result carrying the count, summed; `kills`
    the kills inside the spans (`_kills`); and off the decision log's threat lines: `resends` the lines sending a melee
    whose why carries `melee` {resend} by kind, `planner_ends` the `melee_end` {end} lines by end, `replaced` the
    lines sending a melee by the why's `ladder` (the ladder's command it replaced), `lines` those whose why's
    `maneuver` reads melee. Inference off the walls: `mean_span_s` the mean accept-to-end of the spans with a terminal
    line, `by_fight` the spans accepted in each `loop.fights` row's span, `outside_fights` the rest."""
    if L is None:
        return {"read": False}
    rows = [E._d(a) for a in E._l(E._d(E._d(out).get("loop")).get("actions")) if E._d(a).get("type") == MELEE]
    by_mode = {}
    for a in rows:
        G14._inc(by_mode, str(E._d(a.get("args")).get("mode")))
    terms = _terminals(lines)
    accepted = {s["aid"] for s in spans}
    ends = {}
    for aid in sorted(set(terms) | accepted | {a.get("aid") for a in rows}, key=str):
        row = next((a for a in rows if a.get("aid") == aid), None)
        G14._inc(ends, "open" if aid not in terms and aid in accepted else _end_key(terms.get(aid), row))
    steps, ticks, frame_steps, counts = {}, {}, {}, {k: 0 for k in COUNTS}
    for s in spans:
        prev = None
        for _, r in s["progress"]:
            st = r.get("step")
            if isinstance(st, str) and st != prev:
                G14._inc(steps, st)
            prev = st
        term = s["terminal"]
        res = [r for _, r in s["progress"]] + ([E._d(term.get("result"))] if term is not None else [])
        for k in COUNTS:
            last = next((E._n(r.get(k)) for r in reversed(res) if E._n(r.get(k)) is not None), None)
            counts[k] += int(last or 0)
        if term is not None and term.get("state") == "done":
            for st, n in E._d(E._d(term.get("result")).get("steps")).items():
                G14._inc(ticks, st, E._n(n) or 0)
    for f in frames:
        st = E._d(E._d(f).get("act")).get("step")
        if isinstance(st, str):
            G14._inc(frame_steps, st)
    resends, pends, replaced, n = {}, {}, {}, 0
    for ln in L.rows:
        if ln.get("branch") != "threat":
            continue
        w = L.why(ln)
        n += 1 if E._d(w.get("maneuver")).get("maneuver") == MELEE else 0
        me = w.get("melee_end")
        if isinstance(me, dict):
            G14._inc(pends, str(me.get("end")))
        if not E._sent(ln, MELEE):
            continue
        G14._inc(replaced, str(w.get("ladder")))
        rs = E._d(w.get("melee")).get("resend")
        if rs is not None:
            G14._inc(resends, str(rs))
    fights, t0 = _fights(out), E._loop_start_s(out)
    by, outside = [0] * len(fights), 0
    for s in spans:
        i = _fight_of(fights, t0, s["accept"])
        if i is None:
            outside += 1
        else:
            by[i] += 1
    spans_s = [(s["end"] - s["accept"]) / 1000.0 for s in spans if s["terminal"] is not None]
    return dict({"read": True, "sent": len(rows), "by_mode": by_mode, "accepted": len(spans), "ends": ends,
                 "steps": steps, "step_ticks": ticks, "frame_steps": frame_steps}, **counts,
                kills=len(kills_in), resends=resends, planner_ends=pends, replaced=replaced, lines=n,
                mean_span_s=_mean(spans_s), by_fight=by, outside_fights=outside)


# ---------------------------------------------------------------- hits_in_melee
def e_hits_in_melee(out, frames, idx, kills):
    """The hits inside and outside the melee spans (the review's section 5.1 A/B): {read, runs, inside, outside,
    outside_fight, kills_inside, kills_outside, kills, per_kill, per_kill_inside, per_kill_outside} ({"read": False}
    without a frame). Reading: `runs` the reaction runs (`e18._hit_runs`), `kills_inside` and `kills_outside`
    (`_kills`), `kills` their sum and `per_kill` the runs over it (the session's hits per kill with a melee's `kill`
    counted, which the inherited `kills.planner`, read off `targetDead` alone, misses). Inference off the walls:
    `inside` the runs whose first frame lies in a span, `outside` the rest, `outside_fight` those of the rest inside a
    `loop.fights` row's span (the fights the ladder ran), `per_kill_inside` and `per_kill_outside` each side's runs
    over its kills (None at 0 kills)."""
    if not frames:
        return {"read": False}
    runs = G18._hit_runs(frames)
    fights, t0 = _fights(out), E._loop_start_s(out)
    inside = outside = in_fight = 0
    for f in runs:
        w = E._n(f.get("wallMs"))
        if idx.at(w) is not None:
            inside += 1
            continue
        outside += 1
        in_fight += 1 if _fight_of(fights, t0, w) is not None else 0
    ki, ko = len(kills[0]), len(kills[1])
    return {"read": True, "runs": len(runs), "inside": inside, "outside": outside, "outside_fight": in_fight,
            "kills_inside": ki, "kills_outside": ko, "kills": ki + ko, "per_kill": _per(len(runs), ki + ko),
            "per_kill_inside": _per(inside, ki), "per_kill_outside": _per(outside, ko)}


# ---------------------------------------------------------------- melee_strike
def _act_of(f):
    a = E._d(E._d(f).get("act"))
    return a.get("aid"), a.get("step")


def _step_before(span, w):
    """The span's last progress line at or before wall ms `w` whose step is not HIT_STEP: (step, seconds before)."""
    for pw, r in reversed(span["progress"]):
        if pw is None or pw > w:
            continue
        if r.get("step") != HIT_STEP:
            return r.get("step"), round((w - pw) / 1000.0, 3)
    return None, None


def _press_before(span, w):
    """The span's last progress line within STRIKE_BEFORE_S at or before wall ms `w` whose step is a PRESS_STEPS step:
    {step, before_s, d}, else None."""
    for pw, r in reversed(span["progress"]):
        if pw is None or pw > w:
            continue
        if pw < w - STRIKE_BEFORE_S * 1000.0:
            return None
        if r.get("step") in PRESS_STEPS:
            return {"step": r.get("step"), "before_s": round((w - pw) / 1000.0, 3), "d": E._n(r.get("d"))}
    return None


def e_melee_strike(out, frames, lines, idx):
    """The strike before each hit inside a melee span, by step: {read, runs, by_frame_step, by_step_before, by_press,
    rows} ({"read": False} without a frame). Reading, per run whose first frame lies in a span (`rows`): {seq, kind,
    aid (the span's), frame_aid and frame_step (the first frame's `act.aid` and `act.step`, PZA/1.8), prev_step (the
    frame before it's `act.step`)}; inference off the order of lines: `step_before` and `step_before_s` (the span's
    last progress step at or before the frame other than HIT_STEP, `_step_before`), `press` (the last press step within
    STRIKE_BEFORE_S, `_press_before`: {step, before_s, d}, else None) and `strike_before` (the run's strike as
    `hits.strike_before` reads it, `e18._strike_before`: the last accepted shove, attack or stomp within
    STRIKE_BEFORE_S). `by_frame_step`, `by_step_before` and `by_press` tally the rows' frame_step, step_before and
    press step ("None" where unread)."""
    if not frames:
        return {"read": False}
    acc, ends, targets = G18._accepts(lines), G18._ends(lines), G18._targets(out)
    pos = {id(f): i for i, f in enumerate(frames)}
    rows, by_frame, by_before, by_press = [], {}, {}, {}
    for f in G18._hit_runs(frames):
        w = E._n(f.get("wallMs"))
        span = idx.at(w)
        if span is None:
            continue
        i = pos[id(f)]
        aid, step = _act_of(f)
        prev = _act_of(frames[i - 1])[1] if i > 0 else None
        sb, sb_s = _step_before(span, w)
        press = _press_before(span, w)
        rows.append({"seq": f.get("seq"), "kind": G18._reaction(f), "aid": span["aid"], "frame_aid": aid,
                     "frame_step": step, "prev_step": prev, "step_before": sb, "step_before_s": sb_s,
                     "press": press, "strike_before": G18._strike_before(acc, ends, targets, f)})
        G14._inc(by_frame, str(step))
        G14._inc(by_before, str(sb))
        G14._inc(by_press, str(press["step"] if press is not None else None))
    return {"read": True, "runs": len(rows), "by_frame_step": by_frame, "by_step_before": by_before,
            "by_press": by_press, "rows": rows}


# ---------------------------------------------------------------- melee_cost
def _cost_side(fs):
    """{frames, actMs_mean, actMs_max, maxActMs_mean, maxActMs_max} over the frames `fs` (each statistic over the
    frames whose value reads a number; None over none)."""
    out = {"frames": len(fs)}
    for k in ("actMs", "maxActMs"):
        xs = [x for x in (E._n(E._d(E._d(f).get("cost")).get(k)) for f in fs) if x is not None]
        out[k + "_mean"], out[k + "_max"] = _mean(xs), (max(xs) if xs else None)
    return out


def e_melee_cost(frames, idx):
    """The skill tick's cost over the melee spans against the rest: {read, inside, outside}, each `_cost_side` over
    the frames whose wallMs lies in a span and over the others ({"read": False} without a frame). Reading: the frames'
    `cost.actMs` (the frame's own tick's skill tick) and `cost.maxActMs` (the worst since the last frame)."""
    if not frames:
        return {"read": False}
    ins, outs = [], []
    for f in frames:
        (ins if idx.at(E._n(f.get("wallMs"))) is not None else outs).append(f)
    return {"read": True, "inside": _cost_side(ins), "outside": _cost_side(outs)}


def readings_e19(out, decision_lines, lines):
    """{key: reading} of the four readings (`NEW`): `melee` {"read": False} without a decision log, the other three
    without a frame; the spans (`_spans`) and the kills (`_kills`) read once."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    frames = L.index[1] if L is not None else E._frame_index(lines)[1]   # sorted once per grade
    spans = _spans(lines)
    idx = _Index(spans)
    kills = _kills(out, lines, idx)
    return {"melee": e_melee(out, L, lines, frames, spans, kills[0]),
            "hits_in_melee": e_hits_in_melee(out, frames, idx, kills),
            "melee_strike": e_melee_strike(out, frames, lines, idx), "melee_cost": e_melee_cost(frames, idx)}


def lines_e19(g):
    """One report line per pass 19 reading, each clause marked reading or inference."""
    me, hm, ms, mc = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append(("melee (iteration 22) [reading]: %s sent by mode %s, %s accepted, ends %s, steps %s, ticks per step "
                "%s, frames per act.step %s, swings %s shoves %s stomps %s floors %s knockdowns %s hits %s, %s kills "
                "inside, re-sends %s, the planner's ends %s, replaced %s, %s maneuver lines; [inference] the mean span "
                "%s s, spans by fight %s, %s outside a fight" % (
                    me.get("sent"), me.get("by_mode"), me.get("accepted"), me.get("ends"), me.get("steps"),
                    me.get("step_ticks"), me.get("frame_steps"), me.get("swings"), me.get("shoves"),
                    me.get("stomps"), me.get("floors"), me.get("knockdowns"), me.get("hits"), me.get("kills"),
                    me.get("resends"), me.get("planner_ends"), me.get("replaced"), me.get("lines"),
                    me.get("mean_span_s"), me.get("by_fight"), me.get("outside_fights")))
               if me.get("read") else "melee (iteration 22): no decision log read")
    out.append(("hits in melee (iteration 22, the A/B) [reading]: %s reaction runs over %s kills (%s a kill, a "
                "melee's kill counted), %s kills inside the spans and %s outside; [inference] %s runs inside (%s a "
                "kill), %s outside (%s a kill), %s of those in a fight" % (
                    hm.get("runs"), hm.get("kills"), hm.get("per_kill"), hm.get("kills_inside"),
                    hm.get("kills_outside"), hm.get("inside"), hm.get("per_kill_inside"), hm.get("outside"),
                    hm.get("per_kill_outside"), hm.get("outside_fight")))
               if hm.get("read") else "hits in melee (iteration 22): no frames read")
    out.append(("melee strike (iteration 22) [reading]: %s runs inside a span by the first frame's act.step %s; "
                "[inference] by the step before %s, by the press within STRIKE_BEFORE_S %s" % (
                    ms.get("runs"), ms.get("by_frame_step"), ms.get("by_step_before"), ms.get("by_press")))
               if ms.get("read") else "melee strike (iteration 22): no frames read")
    ins, outs = E._d(mc.get("inside")), E._d(mc.get("outside"))
    out.append(("melee cost (iteration 22) [reading]: inside the spans %s frames actMs mean %s max %s, maxActMs mean "
                "%s max %s; outside %s frames actMs mean %s max %s, maxActMs mean %s max %s; [inference] a frame in a "
                "span by its wallMs" % (
                    ins.get("frames"), ins.get("actMs_mean"), ins.get("actMs_max"), ins.get("maxActMs_mean"),
                    ins.get("maxActMs_max"), outs.get("frames"), outs.get("actMs_mean"), outs.get("actMs_max"),
                    outs.get("maxActMs_mean"), outs.get("maxActMs_max")))
               if mc.get("read") else "melee cost (iteration 22): no frames read")
    return out


def report_lines_e19(g):
    """report_lines_e18's lines (the gate line naming gate_e19) then one line per pass 19 reading (`lines_e19`)."""
    g = E._d(g)
    out = [("gate_e19 " + ln[len("gate_e18 "):]) if ln.startswith("gate_e18 ") else ln
           for ln in G18.report_lines_e18(g)]
    return out + lines_e19(g)


def grade_e19(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e18 under "grade_e19" with the four readings of pass 19 (`NEW`, `readings_e19`; `melee` {"read": False}
    without a decision log, the other three without a frame), over the state lines of `state_dir` unless `lines` is
    given (read once and handed down)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G18.grade_e18(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e19"
    if files and "frames_files" in g:
        g["frames_files"] = files
    g.update(readings_e19(out, decision_lines, lines))
    g["report_lines"] = report_lines_e19(g)
    return g


def gate_e19(outs):
    """gate_e13 (neither grade_e14 to grade_e18 nor grade_e19 changes what it reads), named gate_e19."""
    return G18.gate_e18(outs)
