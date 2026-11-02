"""grades.e14 -- the chain sessions' grade, pass 14 (Plan 26 Task 4): `grade_e14` is `gates_e.grade_e13` under
"grade_e14" with the six readings of survival iteration 17 (Plan 26 Task 2 and its fix 1), each read off the decision
log's why fields, the artifact's actions and the state log's act lines, frames and map:

  window_exit     P26-A, the window way out: the exits planned through a window, the climbs the threat branch sent,
                  their ends, `smashed` and `cut` off the act lines, the stand's ends they ran from and the room left.
  one_exit        P26-B, the stand's second way out: the `many` lines whose `doorway_pick` reads "one_exit".
  inside_send     P26-C, the inside corner's shove: the `inside` corner's sends by kind with their `near_n`.
  threat_bleed    P26-D, the bleed under the threat branch: the `bleed` yields, their rides, and the frames that bled
                  with no bandage running, by the branch that answered.
  wear_worn       P26-E, the worn wear: the wears per item, the `rejected worn` ends, the re-sends of a marked item.
  edge_out_check  grade_e13's `edge_out.only_out`, flagged when nonzero (the spec's section 3 nit).

Each reading is {"read": False} without a decision log. A key marked reading counts what the log or the artifact
states; one marked inference reads an effect off the frames, the map or the order of lines. Frozen once an artifact
carries its output (`grades/__init__.py`); `gates_e` and every driver stay untouched."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.planner.policies import INSIDE_CROWD_N

WINDOW_LEFT_S = 5.0          # wall seconds: a done climb's frames are read this long after its end for the room left
TERMINAL = ("done", "failed", "rejected")
SENDS = ("shove", "stomp", "attack")
BRANCHES = ("threat", "care")


def _inc(d, k, n=1):
    d[k] = d.get(k, 0) + n


def _acts(lines, kind):
    """{aid: (first wallMs, terminal act line or None)} of the state log's `kind` act lines, in log order."""
    out = {}
    for ln in E._l(lines):
        if not isinstance(ln, dict) or ln.get("kind") != "act" or ln.get("type") != kind:
            continue
        w = E._n(ln.get("wallMs"))
        first, end = out.get(ln.get("aid"), (w, None))
        out[ln.get("aid")] = (first if first is not None else w,
                              ln if end is None and ln.get("state") in TERMINAL else end)
    return out


def _loop_actions(out, kind, branch=None):
    """The artifact's loop.actions rows of type `kind` (of `branch` when given), in send order."""
    rows = [E._d(a) for a in E._l(E._d(E._d(out).get("loop")).get("actions"))]
    rows = [a for a in rows if a.get("type") == kind and (branch is None or a.get("branch") == branch)]
    return sorted(rows, key=lambda a: E._n(a.get("sentS")) or 0.0)


def _end_ms(L, row, acts):
    """The wall ms a loop.actions row ended at: its terminal act line's, else its endedS on the loop clock."""
    end = acts.get(row.get("aid"), (None, None))[1]
    if end is not None and E._n(end.get("wallMs")) is not None:
        return E._n(end.get("wallMs"))
    t = E._n(row.get("endedS"))
    return None if t is None or L.t0 is None else (L.t0 + t) * 1000.0


def _left_room(L, mv, wall_ms):
    """True when a frame within WINDOW_LEFT_S after `wall_ms` reads a square with no room, False when every mapped
    frame there reads a room, None when none is mapped (an inference off the frames and the map, `_MapView`)."""
    walls, frames = L.index
    lo = bisect.bisect_left(walls, wall_ms)
    hi = bisect.bisect_right(walls, wall_ms + WINDOW_LEFT_S * 1000.0)
    seen = None
    for w, f in zip(walls[lo:hi], frames[lo:hi]):
        me = E._d(f.get("me"))
        x, y = E._n(me.get("x")), E._n(me.get("y"))
        if x is None or y is None:
            continue
        out_ = E._outside(mv.at(w / 1000.0), (x, y, int(E._n(me.get("z")) or 0)))
        if out_ is True:
            return True
        seen = False if out_ is False else seen
    return seen


def _run_origin(L, i):
    """What a run of window-step lines starting at `L.rows[i]` ran from: the stand's end (`doorway_exit.end`, on the
    run's first line or the line before it, whose `exit` reads "window"), else "trapped" (the trapped flee's why),
    else "flee:<reason>"."""
    for j in (i, i - 1):
        ex = L.why(L.rows[j]).get("doorway_exit") if j >= 0 else None
        if isinstance(ex, dict) and ex.get("exit") == "window":
            return str(ex.get("end"))
    w = L.why(L.rows[i])
    return "trapped" if "trapped" in w else "flee:%s" % w.get("flee")


def e_window_exit(out, L, lines):
    """The window way out (P26-A, `Threat.WINDOW_EXIT`): {read, planned_lines, planned, windows, runs_from, by_end,
    sent, sent_lines, smash_sent, done, refused, ends, reasons, smashed, cut, left, stayed, unread}. Reading:
    `planned_lines` the lines whose threat why reads `step` "window" (the Flee's window step, `flee.Flee._window_step`),
    `planned` the runs of them (one way out each; a window refused `locked` unsmashed and offered again as a smash,
    ruling P26-7c, shows two climbs in one run), `windows` the distinct window squares they name; `by_end` the stand's
    end ticks whose `doorway_exit` reads `exit` "window", by `end`; `sent` the `window` actions of loop.actions the
    threat branch sent (`sent_lines` the threat lines that sent one, `smash_sent` those sent with `smash` true), `done`
    those that ended done and `refused` those that failed or were rejected (the exit then refused, or a `locked` try
    re-offered as a smash), `ends` by state (done | failed | rejected | running) and `reasons` the others by
    "state:reason" (a timeout included); `smashed` and `cut` the done climbs whose result reads them true, off the state
    log's act line (else loop.results): the Flee logs neither. Inference: `runs_from` the runs by what they ran from
    (`_run_origin`: the stand's end, "trapped" or the flee's reason), and per done climb whether a frame within
    WINDOW_LEFT_S after its end read a square with no room (`left`), every mapped one a room (`stayed`), or none was
    mapped (`unread`)."""
    if L is None:
        return {"read": False}
    planned, windows, runs_from, by_end = 0, set(), {}, {}
    prev = False
    for i, ln in enumerate(L.rows):
        w = L.why(ln)
        ex = w.get("doorway_exit")
        if isinstance(ex, dict) and ex.get("exit") == "window":
            _inc(by_end, str(ex.get("end")))
        step = w.get("step") == "window"
        if step:
            sq = w.get("window")
            if isinstance(sq, list) and len(sq) >= 2:
                windows.add((sq[0], sq[1]))
            if not prev:
                planned += 1
                _inc(runs_from, _run_origin(L, i))
        prev = step
    acts, mv = _acts(lines, "window"), E._MapView(lines)
    rows = _loop_actions(out, "window", "threat")
    ends, reasons = {"done": 0, "failed": 0, "rejected": 0, "running": 0}, {}
    smashed = cut = left = stayed = unread = 0
    for a in rows:
        st = a.get("state") if a.get("state") in TERMINAL else "running"
        ends[st] += 1
        if st in ("failed", "rejected"):
            _inc(reasons, "%s:%s" % (st, a.get("reason")))
        if st != "done":
            continue
        end = acts.get(a.get("aid"), (None, None))[1]
        res = E._d(end.get("result")) if end is not None else L.res.get(a.get("aid"), {})
        smashed += 1 if res.get("smashed") is True else 0
        cut += 1 if res.get("cut") is True else 0
        ms = _end_ms(L, a, acts)
        gone = None if ms is None else _left_room(L, mv, ms)
        left += 1 if gone is True else 0
        stayed += 1 if gone is False else 0
        unread += 1 if gone is None else 0
    return {"read": True, "planned_lines": sum(1 for ln in L.rows if L.why(ln).get("step") == "window"),
            "planned": planned, "windows": sorted(windows), "runs_from": runs_from, "by_end": by_end,
            "sent": len(rows), "sent_lines": sum(1 for ln in L.rows if ln.get("branch") == "threat"
                                                 and E._sent(ln, "window")),
            "smash_sent": sum(1 for a in rows if E._d(a.get("args")).get("smash") is True),
            "done": ends["done"], "refused": ends["failed"] + ends["rejected"], "ends": ends, "reasons": reasons,
            "smashed": smashed, "cut": cut, "left": left, "stayed": stayed, "unread": unread}


def e_one_exit(L):
    """The stand's second way out (P26-B, `Threat.STAND_SECOND_EXIT`): {read, lines, runs, picks, buildings, unnamed}.
    Reading: `lines` the lines whose threat why flees `many` with `doorway_pick` "one_exit" (`Flee.door_verdicts`'
    verdict the first failing condition, `DoorwayStand._doorway_pick`), `runs` the runs of adjacent ones, `picks` every
    `many` line's `doorway_pick` by value (the context the count sits in), `buildings` the distinct buildings those
    lines name (their `shelter` or `exit`) and `unnamed` the lines naming none: the planner logs no building beside the
    verdict (the refused door's building is the one the Flee did not pick), so `unnamed` is the line count on a correct
    log."""
    if L is None:
        return {"read": False}
    lines = runs = unnamed = 0
    picks, buildings, prev = {}, set(), False
    for ln in L.rows:
        w = L.why(ln)
        many = w.get("flee") == "many"
        if many and w.get("doorway_pick") is not None:
            _inc(picks, str(w.get("doorway_pick")))
        one = many and w.get("doorway_pick") == "one_exit"
        if one:
            lines += 1
            runs += 0 if prev else 1
            b = w.get("shelter") if w.get("shelter") is not None else w.get("exit")
            if b is None:
                unnamed += 1
            else:
                buildings.add(repr(b))
        prev = one
    return {"read": True, "lines": lines, "runs": runs, "picks": picks, "buildings": sorted(buildings),
            "unnamed": unnamed}


def e_inside_send(L):
    """The inside corner's shove (P26-C, `Threat.INSIDE_SHOVE`): {read, lines, sends, near_n, crowd_attacks, unsent,
    crowd_shoves}. Reading: `lines` the threat lines whose why carries `corner` with `kind` "inside" (the Fight logs it
    on every send of such a corner, `fight.Fight.choose`; P25-A's corner kinds share the key and are never counted
    here), `sends` them by `send` (shove | stomp | attack | other), `near_n` a histogram of the zombies at point blank
    each logged, `crowd_attacks` the attacks logged with `near_n` at INSIDE_CROWD_N or more (must read 0: the rule's own
    check), `unsent` the corner lines that sent nothing and `crowd_shoves` the threat lines whose why reads `shove`
    "crowd" (`shove.FightShove._crowd_shove`)."""
    if L is None:
        return {"read": False}
    sends, hist = {k: 0 for k in SENDS + ("other",)}, {}
    lines = crowd = unsent = shoves = 0
    for ln in L.rows:
        if ln.get("branch") != "threat":
            continue
        w = L.why(ln)
        shoves += 1 if w.get("shove") == "crowd" else 0
        c = w.get("corner")
        if not isinstance(c, dict) or c.get("kind") != "inside":
            continue
        lines += 1
        s = c.get("send") if c.get("send") in SENDS else "other"
        sends[s] += 1
        n = E._n(c.get("near_n"))
        _inc(hist, str(c.get("near_n")))
        crowd += 1 if s == "attack" and n is not None and n >= INSIDE_CROWD_N else 0
        unsent += 0 if ln.get("sent") is True else 1
    return {"read": True, "lines": lines, "sends": sends, "near_n": hist, "crowd_attacks": crowd, "unsent": unsent,
            "crowd_shoves": shoves}


def _bandage_spans(lines):
    """[(first wallMs, end wallMs or inf)] of the state log's bandage act lines: the spans a bandage ran."""
    return [(s, E._n(end.get("wallMs")) if end is not None else math.inf)
            for s, end in _acts(lines, "bandage").values() if s is not None]


def _bleeds(f):
    return any(isinstance(p, dict) and p.get("bleeding") is True for p in E._l(E._d(f.get("body")).get("parts")))


def e_threat_bleed(L, lines):
    """The bleed under the threat branch (P26-D, `Threat.THREAT_BLEED`): {read, yields, near, rides, standing,
    rides_by_leg, bleeding_frames, bandaging, unbandaged, threat_run}. Reading: `yields` the lines whose threat why
    carries `care_yield` {why "bleed", near} (a yield only the bleed rule made, `threat.py`), `near` their nearest
    distances in log order, `rides` those whose threat why reads `ride` true (the bandage riding a `pair` or `held`
    flee's leg with `keepMoving`, the care's `ride_now`) and `standing` the rest (a running Fight's tick with nothing in
    reach). Inference: `rides_by_leg` the rides by the flee reason of the last line before each that names one (the leg
    the ride held; `flee_reason` itself is not logged); off the state log's frames, `bleeding_frames` the frames with a
    part whose `bleeding` reads true, `bandaging` those inside a bandage act's span (its first act line to its end),
    `unbandaged` the others by the branch of the decision line in force at the frame (threat | care | other | none:
    before the first line), and `threat_run` the most such threat-branch frames in a row (F7's 157)."""
    if L is None:
        return {"read": False}
    yields, near, rides, legs, last_flee = 0, [], 0, {}, None
    for ln in L.rows:
        w = L.why(ln)
        cy = w.get("care_yield")
        if isinstance(cy, dict) and cy.get("why") == "bleed":
            yields += 1
            near.append(E._n(cy.get("near")))
            if w.get("ride") is True:
                rides += 1
                _inc(legs, str(last_flee))
        if w.get("flee") is not None:
            last_flee = w.get("flee")
    spans = _bandage_spans(lines)
    walls = [(E._n(ln.get("wall")) or 0.0) * 1000.0 for ln in L.rows]
    bleeding = bandaging = run = top = 0
    unb = {k: 0 for k in BRANCHES + ("other", "none")}
    for w, f in zip(*L.index):
        if not _bleeds(f):
            run = 0
            continue
        bleeding += 1
        if any(s <= w <= e for s, e in spans):
            bandaging += 1
            run = 0
            continue
        i = bisect.bisect_right(walls, w) - 1
        br = "none" if i < 0 else L.rows[i].get("branch")
        br = br if br in unb else "other"
        unb[br] += 1
        run = run + 1 if br == "threat" else 0
        top = max(top, run)
    return {"read": True, "yields": yields, "near": near, "rides": rides, "standing": yields - rides,
            "rides_by_leg": legs, "bleeding_frames": bleeding, "bandaging": bandaging, "unbandaged": unb,
            "threat_run": top}


def _skipped_worn(ln):
    """The `skipped_worn` count a care-branch line's why carries (the stock's wear line: under `stock` or its own)."""
    c = E._bw(ln, "care")
    v = E._d(c.get("stock")).get("skipped_worn", c.get("skipped_worn"))
    return E._n(v)


def e_wear_worn(out, L):
    """The worn wear (P26-E, `Survive.WEAR_WORN`): {read, sends, per_item, rejected_worn, marked, resends,
    skipped_lines, skipped_max}. Reading: `sends` the `wear` actions of loop.actions, `per_item` them by item id,
    `rejected_worn` those rejected `worn` (each marks its garment worn, `World.mark_worn`), `marked` the distinct items
    so marked, `resends` the wears of a marked item sent after its `worn` refusal ended (must read 0 with the switch on:
    F5 re-sent its jeans every WEAR_RETRY_MIN), `skipped_lines` the care lines whose stock wear why carries
    `skipped_worn` and `skipped_max` the most it counted."""
    if L is None:
        return {"read": False}
    rows = _loop_actions(out, "wear")
    per, marked, resends = {}, {}, 0
    for a in rows:
        iid = E._d(a.get("args")).get("itemId")
        _inc(per, str(iid))
        t = E._n(a.get("sentS"))
        if iid in marked and t is not None and t >= marked[iid]:
            resends += 1
        if a.get("state") == "rejected" and a.get("reason") == "worn":
            e = E._n(a.get("endedS"))
            marked.setdefault(iid, e if e is not None else t if t is not None else 0.0)
    counts = [c for c in (_skipped_worn(ln) for ln in L.rows if ln.get("branch") == "care") if c is not None]
    return {"read": True, "sends": len(rows), "per_item": per,
            "rejected_worn": sum(1 for a in rows if a.get("state") == "rejected" and a.get("reason") == "worn"),
            "marked": len(marked), "resends": resends, "skipped_lines": len(counts),
            "skipped_max": max(counts) if counts else None}


def e_edge_out_check(g):
    """grade_e13's `edge_out.only_out` (P25-X amended, EDGE_OUT_OF_HOLD) copied with `flagged` true when it is nonzero
    (the spec's section 3 nit: it read 0 on E16 and must keep reading 0): {read, only_out, flagged}."""
    eo = E._d(E._d(g).get("edge_out"))
    if not eo.get("read"):
        return {"read": False}
    n = eo.get("only_out")
    return {"read": True, "only_out": n, "flagged": bool(n)}


def _lines_e14(g):
    w, o, s, b, ww, ec = (E._d(g.get(k)) for k in ("window_exit", "one_exit", "inside_send", "threat_bleed",
                                                   "wear_worn", "edge_out_check"))
    out = []
    out.append(("window way out (P26-A) [reading]: %s window-step lines in %s runs at windows %s, stand ends to a "
                "window %s; %s climbs sent by the threat branch (%s lines, %s with smash), %s done, %s refused, "
                "ends %s, reasons %s, %s smashed and %s cut on the act lines; [inference] runs from %s, done climbs "
                "that left the room squares %s, stayed on them %s, unread %s" % (
                    w.get("planned_lines"), w.get("planned"), w.get("windows"), w.get("by_end"), w.get("sent"),
                    w.get("sent_lines"), w.get("smash_sent"), w.get("done"), w.get("refused"), w.get("ends"),
                    w.get("reasons"), w.get("smashed"), w.get("cut"), w.get("runs_from"), w.get("left"),
                    w.get("stayed"), w.get("unread"))) if w.get("read")
               else "window way out (P26-A): no decision log read")
    out.append(("stand second way out (P26-B) [reading]: %s `many` lines with `doorway_pick` one_exit in %s runs, "
                "every `many` pick %s; buildings named %s, %s lines naming none" % (
                    o.get("lines"), o.get("runs"), o.get("picks"), o.get("buildings"), o.get("unnamed")))
               if o.get("read") else "stand second way out (P26-B): no decision log read")
    out.append(("inside corner shove (P26-C) [reading]: %s `inside` corner sends %s, near_n %s, %s attacks at "
                "INSIDE_CROWD_N or more (must read 0), %s unsent, %s `crowd` shoves" % (
                    s.get("lines"), s.get("sends"), s.get("near_n"), s.get("crowd_attacks"), s.get("unsent"),
                    s.get("crowd_shoves"))) if s.get("read") else "inside corner shove (P26-C): no decision log read")
    out.append(("bleed under the threat (P26-D) [reading]: %s `bleed` yields at %s (%s rides, %s standing); "
                "[inference] rides by leg %s, %s frames bleeding, %s with a bandage running, unbandaged by branch %s, "
                "the most threat frames in a row %s" % (
                    b.get("yields"), b.get("near"), b.get("rides"), b.get("standing"), b.get("rides_by_leg"),
                    b.get("bleeding_frames"), b.get("bandaging"), b.get("unbandaged"), b.get("threat_run")))
               if b.get("read") else "bleed under the threat (P26-D): no decision log read")
    out.append(("worn wear (P26-E) [reading]: %s wears per item %s, %s rejected worn (%s items marked), %s re-sends of "
                "a marked item (must read 0), %s stock lines with skipped_worn (max %s)" % (
                    ww.get("sends"), ww.get("per_item"), ww.get("rejected_worn"), ww.get("marked"), ww.get("resends"),
                    ww.get("skipped_lines"), ww.get("skipped_max"))) if ww.get("read")
               else "worn wear (P26-E): no decision log read")
    out.append(("edge out check (P25-X amended) [reading]: only_out %s%s" % (
        ec.get("only_out"), " FLAGGED (must read 0)" if ec.get("flagged") else "")) if ec.get("read")
               else "edge out check (P25-X amended): no decision log read")
    return out


def report_lines_e14(g):
    """report_lines_e13's lines (the gate line naming gate_e14) then one line per pass 14 reading, each clause marked
    reading or inference."""
    g = E._d(g)
    out = [("gate_e14 " + ln[len("gate_e13 "):]) if ln.startswith("gate_e13 ") else ln for ln in E.report_lines_e13(g)]
    return out + _lines_e14(g)


def grade_e14(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e13 under "grade_e14" with the six readings of survival iteration 17: `window_exit`, `one_exit`,
    `inside_send`, `threat_bleed`, `wear_worn` and `edge_out_check` (each {"read": False} without a decision log; the
    window way out and the bleed read the state lines' act lines, frames and map)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = E.grade_e13(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e14"
    if files and "frames_files" in g:
        g["frames_files"] = files
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    g["window_exit"] = e_window_exit(out, L, lines)
    g["one_exit"] = e_one_exit(L)
    g["inside_send"] = e_inside_send(L)
    g["threat_bleed"] = e_threat_bleed(L, lines)
    g["wear_worn"] = e_wear_worn(out, L)
    g["edge_out_check"] = e_edge_out_check(g)
    g["report_lines"] = report_lines_e14(g)
    return g


def gate_e14(outs):
    """gate_e13 (grade_e14 changes none of what it reads), named gate_e14."""
    return E.gate_e13(outs)
