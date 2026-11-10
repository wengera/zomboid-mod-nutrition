"""grades.x5 -- the footwork grade (Plan 35 Task 5): `grade_x5` is `grades.x4.grade_x4` under "grade_x5", with
"grade_x4" in `base`, x4's own base ("grade_x3") in `base_x4`, and x4's nesting below it kept (`base_x3` "grade_x2",
`base_x2` "grade_x1", `base_x1` grade_f12 for an LLM session, grade_e21 for a chain one; x4's nine readings kept at the
top level), plus five readings of the footwork (the spec `docs/superpowers/specs/2026-11-10-plan-35-the-footwork-design.md`
section 3.4), each over the sources clipped at the loop's stop (`x1.clip`). The state log's melee act lines are read by
`aid`; a melee is "under work" (an engagement) when any of its act lines' result carries the `work` leaf (Plan 35 Task
1: every result line of a melee sent with work carries `contact` and `work`; the scorecard's `engagements` reads the
first progress line's):

  work         the footwork's steps over the melee act lines ({read: False} without any act line): `steps` {work,
               cornered, pile} the step entries (per aid, the runs of consecutive progress lines reading that step: a
               progress line goes on every step change and once a second while a step holds, so a run is one entry);
               `turns` the headings' turns histogram (per aid, a line whose `work` leaf's (heading, turn) differs from
               the aid's last leaf read counts its `turn`, keyed by the turn in whole degrees as a string, WORK_TURNS'
               order first, only values seen); `cornered_ticks` the done lines' `steps.cornered` summed (a failed line
               carries no `steps`: a superseded melee's ticks are not read); `pile` {episodes (the melees with one or
               more pile entries), shoves (the pile entries: each follows the reflex's pile shove at its result,
               PZAgent_StanceWork.lua `pileTick`, so one entry is one shove), knockdowns (those whose shove leaf, the
               `press` on the entry's first line, else on the aid's line before it, reads `knock` true)}.
  contact      the frames' contact seconds inside the engagements ({read: False} without a frame): a frame reads
               contact when its nearest standing zombie (not `crawler`, not `onFloor`, health above 0 or unread) is
               inside CONTACT_R, its `act.step` is not in STRIKE_STEPS (a press in flight) and `me.hitReaction` is empty;
               it stands from its wall to the next frame's, at most FRAME_CAP_S (the last frame the interval before it);
               the definition is the scorecard's `contact_seconds` (tools/trial_score.py, Plan 35 Task 3), copied. {read,
               seconds (the contact frames inside any engagement's span, `e19._spans`' accepted to terminal, counted
               once), frames, engagements (the count), per_engagement [{aid, seconds, hits, hits_inside}], hits_inside};
               `hits` the reaction onsets (`e21._reaction_runs`' first frames) whose wall falls in the span,
               `hits_inside` those whose frame before the onset read contact (the onset's own frame reads a reaction,
               never contact), the top-level one counted once over the engagements.
  handbacks    the engagements' `done` lines ending `handback`, by `why` (floor, clear, crowd, standing, head_stall, in
               first-seen order); {read (False without any act line), lines, by_why}.
  engage_hold  ENGAGE_HOLD (Task 2): the decision lines whose threat why carries `engage_hold` anywhere in it (the
               Fight's busy, a group or care hold, the threat's `many` or `health` read), by its `rule` (each line
               counted once per distinct rule it carries; a non-dict value is read as the rule itself); {read, lines,
               by_rule}.
  withdraw     WITHDRAW (Task 2): the decision lines whose threat why carries `withdraw` as a [vx, vy] pair of numbers
               (the melee maneuver's why); {read, lines, sends (those that sent a melee), resends (those sends whose
               previous melee send, on any line, was at the same `targetId`: the planner re-sends past
               WITHDRAW_RESEND_DEG only)}.

Task 2's keys (`engage_hold` {rule}, the melee why's `withdraw` [vx, vy]) are read as the spec's sections 3.2 and 3.3
name them: Task 2 ran beside this module and its report was not yet written.

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; the contact definition is
copied from the scorecard (never imported: the scorecard is live). `grades.x4`, `grades.x1` and the frozen e-grades'
readers (`e18._reaction`, `e19._spans`, `e21._reaction_runs`, as `grades.x1` imports them) and the shared readers of
`gates_e` are its only imports."""
from agent.base import gates_e as E
from agent.base.grades import e18 as G18
from agent.base.grades import e19 as G19
from agent.base.grades import e21 as G21
from agent.base.grades import x1 as GX1
from agent.base.grades import x4 as GX4
from agent.base.grades.x3 import carries, sent_action, threat_why

# Frozen copies of the live names read here (P26-Q), each with its source.
MELEE = "melee"            # schema actionType (PZA/1.8)
PROGRESS = "progress"      # the act line's state on a step change (PZAgent_Skills.lua)
DONE = "done"              # the act line's state at a done end
HANDBACK = "handback"      # PZAgent_StanceMelee.lua's done `end`
WORK = "work"              # PZAgent_StanceWork.lua (PZA/1.13): the result's leaf and the stepping step
CORNERED = "cornered"      # ... the step with no clear heading
PILE = "pile"              # ... the step after the pile shove
WORK_STEPS = (WORK, CORNERED, PILE)
WORK_TURNS = (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180)   # PZAgent_StanceWork.lua K.WORK_TURNS
HANDBACK_WHYS = ("floor", "clear", "crowd", "standing", "head_stall")     # the done line's whys a hand-back reads
STRIKE_STEPS = ("swing", "shove", "stomp", "floor")   # planner/maneuvers/melee.py STRIKE_STEPS (2b340174): in flight
CONTACT_R = 1.0            # tiles: tools/trial_score.py CONTACT_R (Plan 35 Task 3, at 2b340174), a frozen copy
FRAME_CAP_S = 1.0          # seconds: tools/trial_score.py FRAME_CAP_S (at 2b340174), a frozen copy
ENGAGE_HOLD = "engage_hold"   # spec section 3.2 (Task 2): the hold's why key, {rule}
RULE = "rule"              # ... its rule
WITHDRAW = "withdraw"      # spec section 3.3 (Task 2): the melee why's withdraw vector [vx, vy]
TARGET_ID = "targetId"     # the melee's arg (schema args_melee)
NEW = ("work", "contact", "handbacks", "engage_hold", "withdraw")
N_LINES = len(NEW)         # the report lines lines_x5 appends: one per NEW key


# ---------------------------------------------------------------- shared readers
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def values_of(why, key):
    """Every value held under `key` in `why` (its own keys first, then its values in order, lists included)."""
    out = []
    if isinstance(why, dict):
        if key in why:
            out.append(why[key])
        for k, v in why.items():
            out.extend(values_of(v, key))
    elif isinstance(why, list):
        for v in why:
            out.extend(values_of(v, key))
    return out


def melee_lines(lines):
    """{aid: [act line]} of the melee act lines, in log order, the aids in first-seen order."""
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == MELEE:
            by.setdefault(ln.get("aid"), []).append(ln)
    return by


def under_work(lns):
    """The melee's act lines carry the `work` leaf (an engagement)."""
    return any(isinstance(E._d(ln.get("result")).get(WORK), dict) for ln in lns)


def step_runs(lns):
    """[(step, [i])] the runs of consecutive progress lines of one melee's lines `lns` by `result.step` (`i` the line's
    index in `lns`; a melee's other lines, its accepted and its end, bound its progress lines)."""
    runs = []
    for i, ln in enumerate(lns):
        if ln.get("state") != PROGRESS:
            continue
        s = E._d(ln.get("result")).get("step")
        if runs and runs[-1][0] == s:
            runs[-1][1].append(i)
        else:
            runs.append((s, [i]))
    return runs


def _turn_key(t):
    return str(int(round(t)))


def _hist(vals, order):
    """{key: count} of `vals`, the keys of `order` seen first in its order, then the others in first-seen order."""
    seen = {}
    for v in vals:
        seen[v] = seen.get(v, 0) + 1
    out = {k: seen[k] for k in order if k in seen}
    out.update((k, n) for k, n in seen.items() if k not in out)
    return out


def standing_z(z):
    """tools/trial_score.py `_standing`, copied: a zombie record not a crawler, not on the floor, health above 0 (a record
    with no health leaf reads alive)."""
    z = E._d(z)
    h = E._n(z.get("health"))
    return not z.get("crawler") and not z.get("onFloor") and (h is None or h > 0)


def in_contact(f):
    """tools/trial_score.py `_in_contact`, copied: the nearest standing zombie inside CONTACT_R, no press in flight
    (`act.step` in STRIKE_STEPS) and no hit reaction."""
    if E._d(f.get("act")).get("step") in STRIKE_STEPS or G18._reaction(f):
        return False
    ds = [E._n(E._d(z).get("dist")) for z in E._l(f.get("zombies")) if standing_z(z)]
    ds = [d for d in ds if d is not None]
    return bool(ds) and min(ds) < CONTACT_R


def frame_seconds(frames):
    """[seconds] each frame stands (tools/trial_score.py `contact_seconds`' durations, copied): its wall to the next
    frame's, at most FRAME_CAP_S, the last frame the interval before it."""
    walls = [E._n(f.get("wallMs")) for f in frames]
    dur = []
    for i, w in enumerate(walls):
        nxt = walls[i + 1] if i + 1 < len(walls) else None
        d = (nxt - w) if nxt is not None and w is not None else (w - walls[i - 1] if i and w is not None and
                                                                  walls[i - 1] is not None else 0.0)
        dur.append(min(max(d, 0.0), FRAME_CAP_S * 1000.0) / 1000.0)
    return walls, dur


# ---------------------------------------------------------------- the readings
def e_work(lines):
    """The work reading (the module docstring)."""
    by = melee_lines(lines)
    if not any(isinstance(ln, dict) and ln.get("kind") == "act" for ln in E._l(lines)):
        return {"read": False}
    steps = {k: 0 for k in WORK_STEPS}
    turns, cornered, episodes, shoves, knocks = [], 0, 0, 0, 0
    for lns in by.values():
        piles = 0
        for s, idx in step_runs(lns):
            if s not in steps:
                continue
            steps[s] += 1
            if s != PILE:
                continue
            piles += 1
            first = idx[0]
            press = E._d(E._d(lns[first].get("result")).get("press"))
            if not press and first > 0:
                press = E._d(E._d(lns[first - 1].get("result")).get("press"))
            knocks += 1 if press.get("knock") is True else 0
        shoves += piles
        episodes += 1 if piles else 0
        last = None
        for ln in lns:
            w = E._d(ln.get("result")).get(WORK)
            if not isinstance(w, dict):
                continue
            key = (w.get("heading"), w.get("turn"))
            if key != last and _num(w.get("turn")) is not None:
                turns.append(_turn_key(w.get("turn")))
            last = key
        for ln in lns:
            if ln.get("state") == DONE:
                cornered += _num(E._d(E._d(ln.get("result")).get("steps")).get(CORNERED)) or 0
    return {"read": True, "steps": steps, "turns": _hist(turns, [_turn_key(t) for t in WORK_TURNS]),
            "cornered_ticks": cornered, "pile": {"episodes": episodes, "shoves": shoves, "knockdowns": knocks}}


def e_contact(lines, frames):
    """The contact reading (the module docstring)."""
    if not frames:
        return {"read": False}
    by = melee_lines(lines)
    work_aids = {aid for aid, lns in by.items() if under_work(lns)}
    spans = [s for s in G19._spans(lines) if s["aid"] in work_aids]
    walls, dur = frame_seconds(frames)
    hot = {i for i, f in enumerate(frames) if walls[i] is not None and in_contact(f)}
    onsets = [a for a, _ in G21._reaction_runs(frames) if walls[a] is not None]

    def inside(i, s):
        return s["accept"] <= walls[i] <= s["end"]

    per, all_hot, all_in = [], set(), set()
    for s in spans:
        h = [i for i in hot if inside(i, s)]
        o = [a for a in onsets if inside(a, s)]
        oi = [a for a in o if a - 1 in hot]
        all_hot.update(h)
        all_in.update(oi)
        per.append({"aid": s["aid"], "seconds": sum(dur[i] for i in sorted(h)), "hits": len(o),
                    "hits_inside": len(oi)})
    return {"read": True, "seconds": sum(dur[i] for i in sorted(all_hot)), "frames": len(all_hot),
            "engagements": len(spans), "per_engagement": per, "hits_inside": len(all_in)}


def e_handbacks(lines):
    """The handbacks reading (the module docstring)."""
    if not any(isinstance(ln, dict) and ln.get("kind") == "act" for ln in E._l(lines)):
        return {"read": False}
    whys = []
    for lns in melee_lines(lines).values():
        if not under_work(lns):
            continue
        for ln in lns:
            res = E._d(ln.get("result"))
            if ln.get("state") == DONE and res.get("end") == HANDBACK:
                whys.append(res.get("why"))
    return {"read": True, "lines": len(whys), "by_why": _hist(whys, HANDBACK_WHYS)}


def e_engage_hold(rows):
    """The engage_hold reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    n, rules = 0, []
    for r in E._l(rows):
        why = threat_why(r)
        if not carries(why, ENGAGE_HOLD):
            continue
        n += 1
        seen = []
        for v in values_of(why, ENGAGE_HOLD):
            rule = E._d(v).get(RULE) if isinstance(v, dict) else v
            if rule not in seen:
                seen.append(rule)
        rules.extend(seen)
    return {"read": True, "lines": n, "by_rule": _hist(rules, ())}


def _pair(v):
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(_num(x) is not None for x in v)


def e_withdraw(rows):
    """The withdraw reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    n, sends, resends, prev = 0, 0, 0, None
    for r in E._l(rows):
        typ, args = sent_action(r)
        carried = any(_pair(v) for v in values_of(threat_why(r), WITHDRAW))
        if carried:
            n += 1
        if typ != MELEE:
            continue
        if carried:
            sends += 1
            resends += 1 if prev is not None and args.get(TARGET_ID) == prev else 0
        prev = args.get(TARGET_ID)
    return {"read": True, "lines": n, "sends": sends, "resends": resends}


def readings_x5(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`), over the sources clipped at the loop's stop (`x1.clip`)."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    return {"work": e_work(lines), "contact": e_contact(lines, frames), "handbacks": e_handbacks(lines),
            "engage_hold": e_engage_hold(rows), "withdraw": e_withdraw(rows)}


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=2):
    return round(v, n) if isinstance(v, float) else v


def lines_x5(g):
    """One report line per new reading (`NEW`), each clause marked reading or inference."""
    wk, ct, hb, eh, wd = (E._d(g.get(k)) for k in NEW)
    out = []
    if wk.get("read"):
        p = E._d(wk.get("pile"))
        out.append("work (the melee's footwork steps) [reading]: step entries %s, turns %s, %s cornered ticks (done "
                   "lines); pile: %s episodes, %s shoves, %s knock-downs" % (
                       wk.get("steps"), wk.get("turns"), wk.get("cornered_ticks"), p.get("episodes"), p.get("shoves"),
                       p.get("knockdowns")))
    else:
        out.append(GX1._unread("work"))
    out.append("contact (nearest standing inside %s tiles, no press in flight, no hit reaction, inside the %s "
               "engagements) [reading]: %s s over %s frames, %s hits inside contact; per engagement %s" % (
                   CONTACT_R, ct.get("engagements"), _r(ct.get("seconds")), ct.get("frames"), ct.get("hits_inside"),
                   [(e["aid"], _r(e["seconds"]), e["hits"], e["hits_inside"]) for e in E._l(ct.get("per_engagement"))])
               if ct.get("read") else "contact: no frame read")
    out.append("handbacks (the engagements' done handback lines) [reading]: %s lines, by why %s" % (
        hb.get("lines"), hb.get("by_why")) if hb.get("read") else GX1._unread("handbacks"))
    out.append("engage hold (threat why %s) [reading]: %s lines, by rule %s" % (
        ENGAGE_HOLD, eh.get("lines"), eh.get("by_rule")) if eh.get("read") else GX1._unread("engage hold"))
    out.append("withdraw (threat why %s) [reading]: %s lines, %s melee sends, %s re-sends at the same target" % (
        WITHDRAW, wd.get("lines"), wd.get("sends"), wd.get("resends")) if wd.get("read")
        else GX1._unread("withdraw"))
    return out


def report_lines_x5(g):
    """grade_x4's report lines (`report_lines_x4`), its gate line naming gate_x5, then `lines_x5`."""
    g = E._d(g)
    base = GX4.report_lines_x4(g)
    return [("gate_x5 " + ln[len("gate_x4 "):]) if ln.startswith("gate_x4 ") else ln for ln in base] + lines_x5(g)


def grade_x5(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x4` under "grade_x5" (`base` "grade_x4", `base_x4` x4's own base, x4's nesting kept) with the footwork
    readings (`readings_x5`), over the state lines of `state_dir` unless `lines` is given (read once and handed down);
    its report lines `report_lines_x5`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX4.grade_x4(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x4"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x5"
    g.update(readings_x5(record, decision_lines, lines))
    g["report_lines"] = report_lines_x5(g)
    return g


def gate_x5(outs):
    """gate_x4 (grade_x5 changes none of what it reads), named gate_x5."""
    return GX4.gate_x4(outs)
