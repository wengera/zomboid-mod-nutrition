"""grades.e20 -- the chain sessions' grade, pass 20 (Plan 29 Task 3): `grade_e20` is `grades.e19.grade_e19` under
"grade_e20" with cut 2 of the maneuver layer's reads (ruling P29-J) and one reading per rule of survival iteration 23
(Plan 29 Tasks 1 and 2, `T13_SWITCHES`), each read off the state log's act lines and events, the frames, the artifact's
actions and the decision log's why fields:

  kills         whole again (`e_kills_whole`): the union of the ladder's act lines reading `targetDead` (the SWING_TYPES
                sends, as `gates_e._act_kills` reads them) and the melee's done lines reading `kill`, one zombie once,
                beside the `zombie_dead` events (`agree`); the frozen `gates_e.e_kills_9` read kept whole under
                `kills.legacy_planner`, and `hits.per_kill` over the whole count (the frozen hits' leaves under
                `hits.legacy`).
  facing_all    the facing over every press (`e_facing_all`): on the frame after each `swing` event the compass points
                between `me.dir` and the bearing of the press's target, the ladder's attacks, shoves and stomps and the
                melee's swing, shove, stomp and floor steps, by source.
  pain_swings   the melee's swings by the arms' pain on the line that sent each (`e_pain_swings`): under STRAIN_HARD
                against at or above, each swing's landing (the target lowered, knocked down, killed).
  route_cross   P29-A, the route through a door read by whether it crossed: the route legs, their ends.
  goal_stall    P29-B, a budget end that never moved: the budget ends and the stalls marked.
  close_idle    P29-C, P27-J's walk to close at an idle zombie only: the walks, the chasers held.
  dress_finish  P29-D, a running dressing waited on by the flee: the waits.
  health_near   P29-E, the `health` flee only from a zombie within DANGER_R: the lines withheld, by what answered.
  finish_lone   P29-F, the lone fallen pin's finish kept over a flee: the lines kept.
  many_near     P29-G, the `many` count over the standing zombies within DANGER_R: the lines withheld by the count.
  flee_held     P29-H', a flee walk read heading at a held zombie dropped for the stance: the walks given up.

The press (`facing_all`) is the `swing` event (attackStarted true): one per press, as `grades.e18.e_facing` pairs the
ladder's; the melee's step entries on the frames undercount a repeated floor swing in one `floor` step (E22: 42 entries
against 44 presses). A melee swing's landing is read off the melee's own next line after its `swing` step (a
progress line of another step or its done line: `hp` or `hp1`, `knockdowns`, `kill`, the Lua's read a tick after the
attack ended): the frame after the event reads the target's health before the hit lands (F13's eleven swings: the fall
shows two or three frames on). `kills`, `facing_all` and `pain_swings` read a decision log, frames or the act lines as
each says; a rule's reading is {"read": False} without a decision log and on a log no line of which carries the rule's
why field (a log written before iteration 23, E22's and F13's). A key marked reading counts what the log, the frames
or the artifact states; one marked inference reads an effect off the order of lines.

Every live planner name read here is copied below as a frozen constant with its source and its value at d54bfc1a
(Plan 29 Task 2's last commit; ruling P26-Q, `grades/__init__.py`); the why keys are read off Tasks 1 and 2's committed
code at that commit (`edges.py` `route_why` and `read_route_end`, the goal's, the Fight's and the fill's route walks;
`goal_runner.py` `_noted`, `survive.py` `_decide`'s `stall`; `shove.py` `_shove_close`; `threat.py` `_decide`,
`_dress_waits` and the why loop; `flee.py` `held_cut`), the melee's `pain` off `dispatch.py` `_melee_dispatch` and the
act lines' shapes off the schema (`schema/pza1.json` `result_melee`, `result_melee_step`). This module imports nothing
from `agent.base.planner` or `agent.base.world`; the chain it imports (`grades.e19.grade_e19`, which reads live names
through `e18` to `e14` and `gates_e`) is pinned by the regrade tests of the artifacts graded through it. Frozen once an
artifact carries its output; `gates_e`, `grades/e14.py` to `grades/e19.py` and every driver stay untouched."""
from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e18 as G18
from agent.base.grades import e19 as G19

# Frozen copies of the live names read here (P26-Q), each as it stood at d54bfc1a (the line there).
SWING_TYPES = ("attack", "aim", "shove", "stomp")   # planner/policies.py:160: the sends whose `targetDead` is a kill
STRAIN_HARD = 20.0     # planner/policies.py:164: the arms' summed pain at which the damage is halved (P24-AP)
PRESS_STEPS = ("swing", "shove", "stomp", "floor")  # PZAgent_StanceMelee.lua:97 `COUNT`'s keys: the steps that press
SWING_STEP = "swing"   # the strike mode's swing at a standing target (`result_melee_step` step, PZA/1.8)
MELEE = "melee"        # the skill's type (schema actionType, PZA/1.8)
LADDER_STRIKES = {"attack": "swings", "shove": "shoves", "stomp": "stomps"}    # e18's STRIKES by facing tally
MELEE_STRIKES = {"swing": "swings", "shove": "shoves", "stomp": "stomps", "floor": "floors"}   # COUNT's map
TALLIES = ("swings", "shoves", "stomps", "floors")
SITES = ("goal", "threat", "need")   # the branches whose why logs a P29-A route (the goal, the Fight, the fill)
BUDGET = "goal budget"               # goal_runner.py:279's end reason (GOAL_MAX_S)
RULES = ("route_cross", "goal_stall", "close_idle", "dress_finish", "health_near", "finish_lone", "many_near",
         "flee_held")
NEW = ("facing_all", "pain_swings") + RULES
N_LINES = 1 + len(NEW)   # the report lines lines_e20 appends: the kills line, then one per NEW key


def _per(n, k):
    return n / k if k else None


# ---------------------------------------------------------------- the kills, whole
def _kill_rows(out, lines):
    """([(zombie id, loop second)], melee ids, ladder ids, source): the kills off the act lines (`source` "act
    lines"), else off loop.results ("loop.results"). Reading: `ladder` the zombies whose SWING_TYPES send's line read
    `targetDead` true (`gates_e._act_kills`'s read, copied), `melee` those whose melee line read `kill` true (its done
    line: `result_melee`), each target off the artifact's loop.actions by aid, each side's zombie once; the union in act
    order, one zombie once, each with its loop second: a ladder kill's send (`sentS`, as `_act_kills` places it), a
    melee kill's done line (its wallMs on the loop clock, `gates_e._loop_start_s`; off loop.results its row's
    `endedS`), so a melee re-sent at its zombie is placed where it killed."""
    loop = E._d(E._d(out).get("loop"))
    acts = {a.get("aid"): a for a in (E._d(x) for x in E._l(loop.get("actions")))}
    if lines:
        rows, source = [E._d(ln) for ln in E._l(lines) if isinstance(ln, dict) and ln.get("kind") == "act"], \
            "act lines"
    else:
        rows, source = [E._d(r) for r in E._l(loop.get("results")) if isinstance(r, dict)], "loop.results"
    t0 = E._loop_start_s(out)
    seen, got, melee, ladder = set(), [], [], []
    for r in rows:
        t, res = r.get("type"), E._d(r.get("result"))
        if t == MELEE and res.get("kill") is True:
            side = melee
        elif t in SWING_TYPES and res.get("targetDead") is True:
            side = ladder
        else:
            continue
        a = E._d(acts.get(r.get("aid")))
        zid = E._d(a.get("args")).get("targetId")
        if zid is None:
            continue
        if zid not in side:
            side.append(zid)
        if zid in seen:
            continue
        seen.add(zid)
        got.append((zid, _kill_s(side is melee, r, a, t0)))
    return got, melee, ladder, source


def _kill_s(is_melee, r, a, t0):
    """The loop second a kill is placed at (`_kill_rows`): a ladder kill's `sentS`; a melee kill's done line's wallMs
    on the loop clock, else its row's `endedS`, else its `sentS`."""
    if not is_melee:
        return E._n(a.get("sentS"))
    w = E._n(r.get("wallMs"))
    if w is not None and t0 is not None:
        return w / 1000.0 - t0
    ended = E._n(a.get("endedS"))
    return ended if ended is not None else E._n(a.get("sentS"))


def e_kills_whole(out, lines):
    """The kills read whole (P29-J): {planner, planner_ids, melee, ladder, events, event_ids, agree, source}
    (`_kill_rows`): `planner_ids` the union in act order, one zombie once, `planner` its count; `event_ids` the
    `zombie_dead` events (None without lines) and `agree` whether the two sets are equal (None without lines)."""
    got, melee, ladder, source = _kill_rows(out, lines)
    ids = [z for z, _ in got]
    events = E._dead_events(lines) if lines else None
    return {"planner": len(ids), "planner_ids": ids, "melee": melee, "ladder": ladder,
            "events": len(events) if events is not None else None, "event_ids": events,
            "agree": (set(ids) == set(events)) if events is not None else None, "source": source}


def _per_fight(out, kills):
    """{per_fight, standing_kills, per_standing_fight} over the whole kills [(id, loop second)], as `gates_e.e_kills_9`
    derives them over the act-line kills: each `loop.fights` row's kills within its startS (less
    FIGHT_WINDOW_SLACK_S) to its `end.endS` (`gates_e._kills_in`), the standing fights' sum (`gates_e.e_standing_2`)
    and that sum over their count."""
    loop = E._d(E._d(out).get("loop"))
    per = []
    for f in (f for f in E._l(loop.get("fights")) if isinstance(f, dict)):
        s, e = E._n(f.get("startS")), E._n(E._d(f.get("end")).get("endS"))
        per.append(E._kills_in(kills, s - E.FIGHT_WINDOW_SLACK_S, e) if s is not None else 0)
    standing = E.e_standing_2(loop, E._results(loop))
    sk = sum(per[r["fight"]] for r in standing["rows"] if r["fight"] < len(per))
    return {"per_fight": per, "standing_kills": sk,
            "per_standing_fight": sk / standing["n"] if standing["n"] else None}


def _whole(g, out, lines):
    """(kills, hits) of grade dict `g` read whole: `kills` the frozen read with `e_kills_whole`'s leaves and the
    per-fight leaves over the whole kills (`_per_fight`: `per_fight`, `standing_kills`, `per_standing_fight`) over it,
    the frozen read whole only under `legacy_planner`; `hits` (when read) with `kills`, `per_kill` and
    `wounds_per_kill` over the whole count, the frozen three under `legacy`."""
    old = E._d(g.get("kills"))
    kills = dict(old, **e_kills_whole(out, lines))
    kills.update(_per_fight(out, _kill_rows(out, lines)[0]))
    kills["legacy_planner"] = old
    hits = E._d(g.get("hits"))
    if hits.get("read") is not True:
        return kills, hits
    n, runs, wounds = kills["planner"], E._n(hits.get("runs")) or 0, E._n(hits.get("wounds")) or 0
    legacy = {k: hits.get(k) for k in ("kills", "per_kill", "wounds_per_kill")}
    hits = dict(hits, kills=n, per_kill=_per(runs, n), wounds_per_kill=_per(wounds, n), legacy=legacy)
    return kills, hits


def _legacy(g):
    """grade dict `g` as the frozen chain read it: `kills` its `legacy_planner`, `hits` its `legacy` leaves (the
    inherited report lines read these)."""
    g = dict(E._d(g))
    k = E._d(g.get("kills"))
    if "legacy_planner" in k:
        g["kills"] = k["legacy_planner"]
    h = E._d(g.get("hits"))
    if "legacy" in h:
        h = dict(h)
        h.update(h.pop("legacy"))
        g["hits"] = h
    return g


# ---------------------------------------------------------------- the facing over every press
def _tally():
    return {"n": 0, "off_by_points": {str(i): 0 for i in range(5)}, "unread": 0}


def _last_press(prog, aid, step):
    """The melee press's step: the frame's own `act.step` when it is a press step, else the aid's last progress
    step before the event (`prog`)."""
    return step if step in PRESS_STEPS else prog.get(aid)


def e_facing_all(out, lines, frames):
    """The facing over every press (P29-J): {read, presses, swings, shoves, stomps, floors, by_source {ladder, melee},
    paired, other} ({"read": False} without a frame). Each started `swing` event (`attackStarted` true) is read on the
    first frame after it, its act the frame's own `act.aid` (a reading), else the last accepted act line before the
    event (an inference off the order of lines; `paired` counts them by "frame" and by "line"), as `e18.e_facing`
    reads the ladder's. A ladder strike (attack, shove, stomp) tallies as its type; a melee press as its step, the
    frame's own `act.step` when a press step, else the melee's last progress step before the event (`_last_press`);
    a melee event at no press step is `other`, any other act's event not counted. Each tally {n, off_by_points (the
    compass points 0 to 4 between `me.dir` and the bearing of the act's target on that frame, `e18._facing_off`),
    unread (no target listed or no point read)}; the four top-level tallies sum the two sources."""
    if not frames:
        return {"read": False}
    targets, types = G18._targets(out), G18._act_types(out, lines)
    by = {s: {k: _tally() for k in TALLIES} for s in ("ladder", "melee")}
    paired, other, n = {"frame": 0, "line": 0}, 0, 0
    pend, last, prog = [], None, {}
    for ln in E._l(lines):
        if not isinstance(ln, dict):
            continue
        k = ln.get("kind")
        if k == "act" and ln.get("state") == "accepted":
            last = ln
        if k == "act" and ln.get("type") == MELEE and ln.get("state") == "progress":
            prog[ln.get("aid")] = E._d(ln.get("result")).get("step")
        if k == "event" and ln.get("event") == "swing" and ln.get("attackStarted") is True:
            pend.append((E._d(last).get("aid"), dict(prog)))
        elif k == "frame" and pend:
            act = E._d(ln.get("act"))
            own = act.get("aid")
            for inferred, before in pend:
                aid = own if own is not None else inferred
                t = types.get(aid)
                if t == MELEE:
                    step = act.get("step") if own == aid else None
                    key, src = MELEE_STRIKES.get(_last_press(before, aid, step)), "melee"
                    if key is None:
                        other += 1
                        continue
                elif t in LADDER_STRIKES:
                    key, src = LADDER_STRIKES[t], "ladder"
                else:
                    continue
                n += 1
                paired["frame" if own is not None else "line"] += 1
                tally = by[src][key]
                tally["n"] += 1
                off = G18._facing_off(ln, targets.get(aid))
                if off is None:
                    tally["unread"] += 1
                else:
                    tally["off_by_points"][str(off)] += 1
            pend = []
    total = {}
    for key in TALLIES:
        t = _tally()
        for src in by.values():
            t["n"] += src[key]["n"]
            t["unread"] += src[key]["unread"]
            for p, c in src[key]["off_by_points"].items():
                t["off_by_points"][p] += c
        total[key] = t
    return dict({"read": True, "presses": n}, **total, by_source=by, paired=paired, other=other)


# ---------------------------------------------------------------- the swings by the arms' pain
def _band(pain):
    """The pain band of a send's `melee.pain`: "under" STRAIN_HARD, "at_or_above", "unread" (None)."""
    if pain is None:
        return "unread"
    return "at_or_above" if pain >= STRAIN_HARD else "under"


def _pains(L):
    """{aid: the arms' pain} of the melees the decision log sent: the sending line's why `melee` {pain}
    (`dispatch._melee_dispatch`, P28-H), its action matched to the artifact's row (`gates_e._Lines.action`)."""
    out = {}
    for ln in L.rows:
        if not E._sent(ln, MELEE):
            continue
        a = L.action(ln)
        if a is not None:
            out[a.get("aid")] = E._n(E._d(L.why(ln).get("melee")).get("pain"))
    return out


def _landing(r0, ln1):
    """(hp1, lowered, knockdown, killed) of a swing whose step's first progress result is `r0` and whose next act
    line is `ln1` (a progress line of another step or the terminal line; None when the span ended with none): the
    target's health on that line (`hp`, a done line's `hp1`) under `hp`, its `knockdowns` over r0's, a done `kill`."""
    if ln1 is None:
        return None, False, False, False
    r1 = E._d(ln1.get("result"))
    h0 = E._n(r0.get("hp"))
    h1 = E._n(r1.get("hp1")) if ln1.get("state") != "progress" else E._n(r1.get("hp"))
    lowered = h0 is not None and h1 is not None and h1 < h0
    kd = E._n(r1.get("knockdowns")) is not None and E._n(r0.get("knockdowns")) is not None and \
        E._n(r1.get("knockdowns")) > E._n(r0.get("knockdowns"))
    return h1, lowered, kd, ln1.get("state") == "done" and r1.get("kill") is True


def e_pain_swings(out, L, lines):
    """The melee's swings by the arms' pain (P29-J, the review's risk): {read, under, at_or_above, unread, rows}
    ({"read": False} without a decision log). Reading: each melee span's (`e19._spans`) entries into the SWING_STEP
    step off its progress lines (an entry once: the heartbeat's repeat is no new swing), banded by the pain the
    decision line that sent the melee logged (`_pains`; `unread` where no line sent it or the pain reads None), the
    target off the artifact's actions. Inference off the order of lines, on the melee's next line after the step
    (`_landing`): `lowered` (the target's health under the swing's), `knockdowns` (the count risen), `killed` (a done
    line's `kill`). Each band {swings, lowered, knockdowns, killed}; `rows` one per swing {aid, target, pain, hp0,
    hp1, lowered, knockdown, killed} in accept order."""
    if L is None:
        return {"read": False}
    pains, targets = _pains(L), G18._targets(out)
    bands = {b: {"swings": 0, "lowered": 0, "knockdowns": 0, "killed": 0} for b in ("under", "at_or_above", "unread")}
    rows = []
    for s in G19._spans(lines):
        seq = [("progress", r) for _, r in s["progress"]]
        term = s["terminal"]
        prev = None
        for i, (_, r) in enumerate(seq):
            st = r.get("step")
            if st == SWING_STEP and st != prev:
                nxt = next((q for _, q in seq[i + 1:] if q.get("step") != SWING_STEP), None)
                ln1 = {"state": "progress", "result": nxt} if nxt is not None else term
                hp1, lowered, kd, killed = _landing(r, ln1)
                pain = pains.get(s["aid"])
                b = bands[_band(pain)]
                b["swings"] += 1
                b["lowered"] += 1 if lowered else 0
                b["knockdowns"] += 1 if kd else 0
                b["killed"] += 1 if killed else 0
                rows.append({"aid": s["aid"], "target": targets.get(s["aid"]), "pain": pain, "hp0": E._n(r.get("hp")),
                             "hp1": hp1, "lowered": lowered, "knockdown": kd, "killed": killed})
            prev = st
    return dict({"read": True}, **bands, rows=rows)


# ---------------------------------------------------------------- iteration 23's readings, one per rule
def _whys(ln):
    """{site: why} of a decision-log line: the goal's, the threat's and the need's fill's (`fill` under `need`)."""
    return {"goal": E._bw(ln, "goal"), "threat": E._threat_why(ln), "need": E._d(E._bw(ln, "need").get("fill"))}


def _xy(v):
    """(x, y) of a two-number list, else None."""
    v = E._l(v)
    return (E._n(v[0]), E._n(v[1])) if len(v) == 2 else None


def _target_of(ln):
    """(x, y) of the line's sent walkTo, else None."""
    a = E._d(ln.get("action"))
    if ln.get("sent") is not True or a.get("type") != "walkTo":
        return None
    args = E._d(a.get("args"))
    return E._n(args.get("x")), E._n(args.get("y"))


def _route(why):
    """The why's P29-A `route` {door, target, beyond, start_side} (`edges.route_why`), else None (a LootBuilding's
    `route` names its step, a string)."""
    r = why.get("route")
    return r if isinstance(r, dict) and "beyond" in r and "door" in r else None


def e_route_cross(L):
    """P29-A, the route through a door read by whether it crossed (`ROUTE_CROSS`): {read, legs, by_site, ends,
    crossed, uncrossed, noted, next_way, dropped} ({"read": False} without a decision log or a line carrying a
    `route` or `route_end`). Reading: `legs` the lines whose answering branch (the goal, the Fight's threat, the
    need's fill) sent the walkTo to its why's `route` target, `by_site` them by branch; over every `route_end` {door,
    crossed, noted, next, dropped} on the three whys (each end logged once): `ends`, `crossed`, `uncrossed`, `noted`,
    `next_way` (an uncrossed end whose `next` names a door other than its own: the run's next way), `dropped`."""
    if L is None:
        return {"read": False}
    legs, by = 0, {s: 0 for s in SITES}
    c = {"ends": 0, "crossed": 0, "uncrossed": 0, "noted": 0, "next_way": 0, "dropped": 0}
    seen = False
    for ln in L.rows:
        whys = _whys(ln)
        for site in SITES:
            w = whys[site]
            r = _route(w)
            seen = seen or r is not None
            if r is not None and ln.get("branch") == site and _target_of(ln) == _xy(r.get("target")):
                legs += 1
                by[site] += 1
            e = w.get("route_end")
            if not isinstance(e, dict):
                continue
            seen = True
            c["ends"] += 1
            crossed = e.get("crossed") is True
            c["crossed" if crossed else "uncrossed"] += 1
            c["noted"] += 1 if e.get("noted") is True else 0
            nxt = e.get("next")
            c["next_way"] += 1 if not crossed and nxt is not None and nxt != e.get("door") else 0
            c["dropped"] += 1 if e.get("dropped") is True else 0
    if not seen:
        return {"read": False}
    return dict({"read": True, "legs": legs, "by_site": by}, **c)


def e_goal_stall(L):
    """P29-B, a budget end that never moved (`GOAL_STALL`): {read, ends, marked, targets} ({"read": False} without a
    decision log; {"read": False, ends} on a log no line of which carries `stall`). Reading: `ends` the goal whys
    whose `ended` reads the BUDGET reason, `marked` the lines whose goal why carries `stall` {moved, target}
    (`goal_runner._noted`, Survive's `_decide`: the tick the end read as stuck), `targets` their targets in order."""
    if L is None:
        return {"read": False}
    ends, targets = 0, []
    for ln in L.rows:
        g = E._bw(ln, "goal")
        ends += 1 if E._d(g.get("ended")).get("reason") == BUDGET else 0
        s = g.get("stall")
        if isinstance(s, dict):
            targets.append(s.get("target"))
    if not targets:
        return {"read": False, "ends": ends}   # the budget ends kept for the write-up (review-t3 m3)
    return {"read": True, "ends": ends, "marked": len(targets), "targets": targets}


def e_close_idle(L):
    """P29-C, P27-J's walk to close at an idle zombie only (`CLOSE_IDLE`): {read, walks, chasing, held} ({"read":
    False} without a decision log or a line carrying `close_held` or `shove_close` {idle}). Reading, on the threat why:
    `walks` the lines sending the walkTo whose `shove_close` reads `idle` true, `chasing` those sending it without
    (must read 0 with the rule on), `held` the lines carrying `close_held` {target, d} (`shove._shove_close`: a
    chaser's due count, no walk)."""
    if L is None:
        return {"read": False}
    walks = chasing = held = 0
    for ln in L.rows:
        w = L.why(ln)
        held += 1 if isinstance(w.get("close_held"), dict) else 0
        sc = w.get("shove_close")
        if not isinstance(sc, dict) or not E._sent(ln, "walkTo") or sc.get("left") is True:
            continue   # a `left` line's walk is the Fight's next choice, never the close (shove.py:224-227)
        if sc.get("idle") is True:
            walks += 1
        else:
            chasing += 1
    if not walks and not held:
        return {"read": False}
    return {"read": True, "walks": walks, "chasing": chasing, "held": held}


def _lines_with(L, key):
    """The decision lines whose threat why carries `key` as a dict, in order."""
    return [ln for ln in L.rows if isinstance(L.why(ln).get(key), dict)]


def e_dress_finish(L):
    """P29-D, a running dressing waited on by the flee (`DRESS_FINISH`): {read, waits} ({"read": False} without a
    decision log or a line carrying it). Reading: `waits` the lines whose threat why carries `dress_finish` {action,
    near} (`threat._dress_waits`)."""
    rows = _lines_with(L, "dress_finish") if L is not None else []
    return {"read": True, "waits": len(rows)} if rows else {"read": False}


def e_health_near(L):
    """P29-E, the `health` flee only from a zombie within DANGER_R (`HEALTH_NEAR`): {read, lines, stances, cares, flees,
    other} ({"read": False} without a decision log or a line carrying it). Reading, over the lines whose threat why
    carries `health_near` {near} (`threat._hysteresis`'s withheld flee): `stances` those the threat branch answered
    with a fight (the low fight's stance), `flees` those it answered with a flee of another reason, `cares` those the
    care branch answered (the threat's pass), `other` the rest (another branch after the pass, or the threat
    holding)."""
    rows = _lines_with(L, "health_near") if L is not None else []
    if not rows:
        return {"read": False}
    st = fl = ca = 0
    for ln in rows:
        w = L.why(ln)
        if ln.get("branch") == "threat" and w.get("fight") is True:
            st += 1
        elif ln.get("branch") == "threat" and isinstance(w.get("flee"), str):
            fl += 1
        elif ln.get("branch") == "care":
            ca += 1
    return {"read": True, "lines": len(rows), "stances": st, "cares": ca, "flees": fl,
            "other": len(rows) - st - fl - ca}


def _targets_of(L, rows, key):
    out = []
    for ln in rows:
        t = L.why(ln)[key].get("target")
        if t not in out:
            out.append(t)
    return out


def e_finish_lone(L):
    """P29-F, the lone fallen pin's finish kept over a flee (`FINISH_LONE`): {read, kept, targets} ({"read": False}
    without a decision log or a line carrying it). Reading: `kept` the lines whose threat why carries `finish_lone`
    {target} (`threat._finish_lone`), `targets` the pins, each once."""
    rows = _lines_with(L, "finish_lone") if L is not None else []
    return {"read": True, "kept": len(rows), "targets": _targets_of(L, rows, "finish_lone")} if rows else \
        {"read": False}


def e_many_near(L):
    """P29-G, the `many` count over the standing zombies within DANGER_R (`MANY_NEAR`): {read, lines, n} ({"read":
    False} without a decision log or a line carrying it). Reading: `lines` the lines whose threat why carries
    `many_near` {n} (`threat._many`: the old read said `many`, the standing count did not), `n` them by the count."""
    rows = _lines_with(L, "many_near") if L is not None else []
    if not rows:
        return {"read": False}
    by = {}
    for ln in rows:
        m = L.why(ln)["many_near"]
        G14._inc(by, str(E._n(m.get("n"))))
    return {"read": True, "lines": len(rows), "n": by}


def e_flee_held(L):
    """P29-H', a flee walk read heading at a held zombie dropped for the stance (`FLEE_HELD_STANCE`): {read, given_up,
    targets} ({"read": False} without a decision log or a line carrying it). Reading: `given_up` the lines whose
    threat why carries `flee_held_stance` {target, heading, bearing, d} (`flee.Flee._held_ahead`'s cut), `targets` the
    held zombies, each once."""
    rows = _lines_with(L, "flee_held_stance") if L is not None else []
    return {"read": True, "given_up": len(rows), "targets": _targets_of(L, rows, "flee_held_stance")} if rows else \
        {"read": False}


def readings_e20(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`): `facing_all` {"read": False} without a frame, the others without a
    decision log (a rule's also on a log carrying none of its lines)."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    frames = L.index[1] if L is not None else E._frame_index(lines)[1]
    return {"facing_all": e_facing_all(out, lines, frames), "pain_swings": e_pain_swings(out, L, lines),
            "route_cross": e_route_cross(L), "goal_stall": e_goal_stall(L), "close_idle": e_close_idle(L),
            "dress_finish": e_dress_finish(L), "health_near": e_health_near(L), "finish_lone": e_finish_lone(L),
            "many_near": e_many_near(L), "flee_held": e_flee_held(L)}


def apply_e20(g, out, decision_lines, lines):
    """grade dict `g` (grade_e19's or grade_f10's) with the kills and the hits read whole (`_whole`) and the new
    readings (`readings_e20`), in place."""
    g["kills"], g["hits"] = _whole(g, E._d(out), lines)
    g.update(readings_e20(out, decision_lines, lines))
    return g


# ---------------------------------------------------------------- the report
def _tl(t):
    t = E._d(t)
    return "%s (by points %s, %s unread)" % (t.get("n"), t.get("off_by_points"), t.get("unread"))


def _rule_line(name, g, fmt, keys):
    r = E._d(g.get(name))
    if not r.get("read"):
        ends = " (%s budget ends)" % r["ends"] if "ends" in r else ""
        return "%s: no line read (no decision log, or no line carrying its why)%s" % (fmt.split(" [")[0], ends)
    return fmt % tuple(r.get(k) for k in keys)


def lines_e20(g):
    """The kills line, then one report line per pass 20 reading (`NEW`), each clause marked reading or inference."""
    k, h, fa, ps = E._d(g.get("kills")), E._d(g.get("hits")), E._d(g.get("facing_all")), E._d(g.get("pain_swings"))
    out = [("kills whole (P29-J) [reading]: %s kills %s (melee %s, ladder %s) against %s zombie_dead events %s, agree "
            "%s (the frozen read %s); whole too: per fight %s, %s on the standing fights (%s a standing fight); %s "
            "reaction runs, %s a kill" % (
                k.get("planner"), k.get("planner_ids"), k.get("melee"), k.get("ladder"), k.get("events"),
                k.get("event_ids"), k.get("agree"), E._d(k.get("legacy_planner")).get("planner"), k.get("per_fight"),
                k.get("standing_kills"), k.get("per_standing_fight"), h.get("runs"), h.get("per_kill")))]
    if fa.get("read"):
        bs = E._d(fa.get("by_source"))
        lad, mel = E._d(bs.get("ladder")), E._d(bs.get("melee"))
        out.append("facing over every press (P29-J) [reading]: %s presses; the melee's swings %s, shoves %s, "
                   "stomps %s, floor swings %s; the ladder's attacks %s, shoves %s, stomps %s; %s melee events at no "
                   "press step; each event's act the frame's own %s; [inference] by the last accepted act line %s" % (
                       fa.get("presses"), _tl(mel.get("swings")), _tl(mel.get("shoves")), _tl(mel.get("stomps")),
                       _tl(mel.get("floors")), _tl(lad.get("swings")), _tl(lad.get("shoves")),
                       _tl(lad.get("stomps")), fa.get("other"), E._d(fa.get("paired")).get("frame"),
                       E._d(fa.get("paired")).get("line")))
    else:
        out.append("facing over every press (P29-J): no frames read")
    if ps.get("read"):
        u, a, n = E._d(ps.get("under")), E._d(ps.get("at_or_above")), E._d(ps.get("unread"))
        out.append("pain swings (P29-J) [reading]: the melee's swings sent under STRAIN_HARD %s, at or above %s, the "
                   "pain unread %s; [inference] off the melee's next line (its own `hp`/`hp1`, `knockdowns`, `kill`): "
                   "lowered %s / %s / %s, knock-downs %s / %s / %s, killed %s / %s / %s" % (
                       u.get("swings"), a.get("swings"), n.get("swings"), u.get("lowered"), a.get("lowered"),
                       n.get("lowered"), u.get("knockdowns"), a.get("knockdowns"), n.get("knockdowns"),
                       u.get("killed"), a.get("killed"), n.get("killed")))
    else:
        out.append("pain swings (P29-J): no decision log read")
    out.append(_rule_line("route_cross", g, "route cross (iteration 23, P29-A) [reading]: %s route legs by site %s; "
                          "%s ends, %s crossed, %s uncrossed (%s noted), %s to the run's next way, %s dropped",
                          ("legs", "by_site", "ends", "crossed", "uncrossed", "noted", "next_way", "dropped")))
    out.append(_rule_line("goal_stall", g, "goal stall (iteration 23, P29-B) [reading]: %s budget ends, %s marked "
                          "stalls at %s", ("ends", "marked", "targets")))
    out.append(_rule_line("close_idle", g, "close idle (iteration 23, P29-C) [reading]: %s walks to close at an idle "
                          "zombie, %s at a chaser (must read 0), %s chasers held", ("walks", "chasing", "held")))
    out.append(_rule_line("dress_finish", g, "dress finish (iteration 23, P29-D) [reading]: %s flee lines waiting on "
                          "a running dressing", ("waits",)))
    out.append(_rule_line("health_near", g, "health near (iteration 23, P29-E) [reading]: %s lines withholding the "
                          "`health` flee: %s stances, %s cares, %s flees of another reason, %s other",
                          ("lines", "stances", "cares", "flees", "other")))
    out.append(_rule_line("finish_lone", g, "finish lone (iteration 23, P29-F) [reading]: %s lines keeping the lone "
                          "fallen pin's finish, pins %s", ("kept", "targets")))
    out.append(_rule_line("many_near", g, "many near (iteration 23, P29-G) [reading]: %s lines withholding `many` by "
                          "the standing count, by count %s", ("lines", "n")))
    out.append(_rule_line("flee_held", g, "flee held (iteration 23, P29-H') [reading]: %s flee walks given up for "
                          "the stance, held zombies %s", ("given_up", "targets")))
    return out


def report_lines_e20(g):
    """report_lines_e19's lines over the legacy kills and hits (`_legacy`; the gate line naming gate_e20) then the
    pass 20 lines (`lines_e20`)."""
    g = E._d(g)
    out = [("gate_e20 " + ln[len("gate_e19 "):]) if ln.startswith("gate_e19 ") else ln
           for ln in G19.report_lines_e19(_legacy(g))]
    return out + lines_e20(g)


def grade_e20(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e19 under "grade_e20" with the kills and the hits read whole and the new readings (`apply_e20`), over the
    state lines of `state_dir` unless `lines` is given (read once and handed down)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G19.grade_e19(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e20"
    if files and "frames_files" in g:
        g["frames_files"] = files
    apply_e20(g, out, decision_lines, lines)
    g["report_lines"] = report_lines_e20(g)
    return g


def gate_e20(outs):
    """gate_e13 (neither grade_e14 to grade_e19 nor grade_e20 changes what it reads), named gate_e20."""
    return G19.gate_e19(outs)
