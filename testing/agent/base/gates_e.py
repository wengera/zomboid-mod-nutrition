"""gates_e -- the chain sessions' grade (Plan 23 Task 15): `grade_e1(out, prev=None)` over one e_day artifact and
`gate_e1(outs)` over a chain's artifacts in order.

Reads (every key tolerated missing; a non-dict reads as empty, nothing raises):
  out.stop {reason, wallS}; out.loop.{first_game_min, game_min, wallS, last_frames [{seq, wallMs, gameMin, body, load,
  stats, me}], actions [{type, state, sentS, endedS, use, branch}], night.sleeps [{state, sleptH, fatigueBefore,
  fatigueAfter}], fights [{fight_ticks, flee {..}, end}], first_world_age, cost, lineage, death {via, frame {signal,
  seq, frameSeq}, last_frames, server_damage}}.
A consume action `use` is "drink"/"water" or "eat"/"food" (anything else counts under needs.unknown); a drop action
`branch` is "load" (a guard drop) or "threat" (a flee drop).

Frame time: a frame sits at loop.wallS (else stop.wallS) less the wall seconds between it and the last kept frame,
i.e. the last kept frame is taken to stand at the loop end; stat_fell compares the last frame before an action sentS
with the first frame after its endedS, and is None when the kept frames do not bracket it.

Every function here is versioned per pass: once an artifact carries its output it is never edited, a later pass is
grade_e2 / gate_e2. The death check is gates.death_check, the frozen function, reused."""
from agent.base import gates as GT
from agent.driverlib import chain as CH

SURVIVED = GT.SURVIVED
# loop.death.via -> the signal that ended the session (e_death's check.signal; PZA/1.3 added "event", ruling P23-AO)
SIGNALS = {"event": "event", "frame": "frame_health", "players": "players"}
ALIVE_MINUTES = 1440.0               # the chain day: 24 game hours summed over its sessions
STAND_OFF_TICKS = 20
_USE = {"drink": "drink", "water": "drink", "eat": "eat", "food": "eat"}
_STAT = {"drink": "thirst", "eat": "hunger"}


def _d(v):
    return v if isinstance(v, dict) else {}


def _l(v):
    return v if isinstance(v, list) else []


def _n(v):
    return GT._num(v)


def _f(v, f="%.2f"):
    return GT._fmt(v, f)


def frame_times(out):
    """([(loop second, frame)], time_base) over loop.last_frames. With loop.t_loop0_ms (the loop start in epoch ms on
    the frames clock) a frame sits at (wallMs - t_loop0_ms) / 1000, time_base "t_loop0_ms"; without it the last kept
    frame is anchored at loop.wallS (else stop.wallS), time_base "anchor"; ([], None) without either."""
    out = _d(out)
    loop = _d(out.get("loop"))
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict) and _n(f.get("wallMs")) is not None]
    t0 = _n(loop.get("t_loop0_ms"))
    if t0 is not None:
        return [((f["wallMs"] - t0) / 1000.0, f) for f in frames], "t_loop0_ms"
    end = _n(loop.get("wallS"))
    end = end if end is not None else _n(_d(out.get("stop")).get("wallS"))
    if end is None or not frames:
        return [], None
    last = frames[-1]["wallMs"]
    return [(end - (last - f["wallMs"]) / 1000.0, f) for f in frames], "anchor"


def _stat_fell(times, a, stat):
    s, e = _n(a.get("sentS")), _n(a.get("endedS"))
    if s is None or e is None:
        return None
    before = [f for t, f in times if t < s]
    after = [f for t, f in times if t > e]
    if not before or not after:
        return None
    v0, v1 = _n(_d(before[-1].get("stats")).get(stat)), _n(_d(after[0].get("stats")).get(stat))
    return None if v0 is None or v1 is None else v1 < v0


def e_needs(out):
    """{drink, eat: {sent, done, stat_fell}, unknown, sleep: {sent, done, sleptH, fatigue_fell}}; stat_fell is true when
    any done action's stat fell, false when every bracketed one did not, None when none was bracketed."""
    loop = _d(_d(out).get("loop"))
    times, base = frame_times(out)
    res = {"time_base": base, "drink": {"sent": 0, "done": 0, "stat_fell": None}, "eat": {"sent": 0, "done": 0, "stat_fell": None},
           "unknown": 0}
    falls = {"drink": [], "eat": []}
    for a in _l(loop.get("actions")):
        a = _d(a)
        if a.get("type") != "consume":
            continue
        k = _USE.get(a.get("use"))
        if k is None:
            res["unknown"] += 1
            continue
        res[k]["sent"] += 1
        if a.get("state") == "done":
            res[k]["done"] += 1
            r = _stat_fell(times, a, _STAT[k])
            if r is not None:
                falls[k].append(r)
    for k, v in falls.items():
        res[k]["stat_fell"] = any(v) if v else None
    sl = [_d(s) for s in _l(_d(loop.get("night")).get("sleeps"))]
    done = [s for s in sl if s.get("state") == "done"]
    fell = [s["fatigueAfter"] < s["fatigueBefore"] for s in done
            if _n(s.get("fatigueBefore")) is not None and _n(s.get("fatigueAfter")) is not None]
    res["sleep"] = {"sent": len(sl), "done": len(done), "sleptH": sum(_n(s.get("sleptH")) or 0 for s in done),
                    "fatigue_fell": any(fell) if fell else None}
    return res


def e_fights(rows):
    """{n, ended, fled, stand_offs}: ended = a fight with an end record, fled = a flee tick seen, a stand-off a fight
    of more than STAND_OFF_TICKS fight ticks whose flee dict has `unreachable` or `stalled`."""
    rows = [f for f in _l(rows) if isinstance(f, dict)]
    d = GT.d_fights(rows)
    return {"n": d["count"], "ended": d["count"] - d["open"], "fled": d["fled"],
            "stand_offs": sum(1 for f in rows if (_n(f.get("fight_ticks")) or 0) > STAND_OFF_TICKS
                              and ("unreachable" in _d(f.get("flee")) or "stalled" in _d(f.get("flee"))))}


def e_load(loop):
    """{max_ratio (weight / max over the kept frames), guard_drops (done drops on the load branch), flee_drops (on
    the threat branch)}."""
    ratios = []
    for f in _l(loop.get("last_frames")):
        ld = _d(_d(f).get("load"))
        w, m = _n(ld.get("weight")), _n(ld.get("max"))
        if w is not None and m:
            ratios.append(w / m)
    drops = [_d(a) for a in _l(loop.get("actions")) if _d(a).get("type") == "drop" and _d(a).get("state") == "done"]
    return {"max_ratio": max(ratios) if ratios else None,
            "guard_drops": sum(1 for a in drops if a.get("branch") == "load"),
            "flee_drops": sum(1 for a in drops if a.get("branch") == "threat")}


def e_minutes(out):
    """(game minutes, source): (last worldAge - first worldAge) * 60, the first from loop.first_world_age (source
    "loop.first_world_age") else readings.hello.first_frame.worldAge ("readings.hello.first_frame"), the last from the
    last kept frame else stop.worldAge; without a first worldAge the loop.game_min less loop.first_game_min clock
    difference, one midnight wrap added when negative ("gameMin"); (None, None) when nothing reads."""
    out = _d(out)
    loop = _d(out.get("loop"))
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)]
    last = _n(frames[-1].get("worldAge")) if frames else None
    last = last if last is not None else _n(_d(out.get("stop")).get("worldAge"))
    for first, src in ((_n(loop.get("first_world_age")), "loop.first_world_age"),
                       (_n(_d(_d(_d(out.get("readings")).get("hello")).get("first_frame")).get("worldAge")),
                        "readings.hello.first_frame")):
        if first is not None and last is not None:
            return (last - first) * 60.0, src
    g0, g1 = _n(loop.get("first_game_min")), _n(loop.get("game_min"))
    if g0 is None or g1 is None:
        return None, None
    return (g1 - g0 if g1 >= g0 else g1 - g0 + 1440.0), "gameMin"


def unresolved_fights(out):
    """Fights of one session neither ended nor cut by the day cap: every fight without an `end` except the last one of
    a session that stopped at the day cap, and every stand-off (more than STAND_OFF_TICKS fight ticks, a flee dict
    naming unreachable or stalled, no end)."""
    out = _d(out)
    rows = [f for f in _l(_d(out.get("loop")).get("fights")) if isinstance(f, dict)]
    cap = _d(out.get("stop")).get("reason") == "day_cap"
    n = 0
    for i, f in enumerate(rows):
        if f.get("end") is not None:
            continue
        flee = _d(f.get("flee"))
        stand = (_n(f.get("fight_ticks")) or 0) > STAND_OFF_TICKS and ("unreachable" in flee or "stalled" in flee)
        if stand or not (cap and i == len(rows) - 1):
            n += 1
    return n


def e_death(out):
    """None unless the stop is a death; else {first_wound_seq, window_frames, window_frames_n (the same count),
    window_truncated, explained, check}: the window opens one row before the first kept frame whose bleeding +
    scratched + bitten rose over the row before it (so the wound arm sees the rise), runs to the end of every kept
    frame, and gates.death_check grades the death record restricted to it. window_truncated: the first wound is the
    first row the frames can show (a rise at the second frame, or a wound already on at the first), so its onset may
    lie before them. When the death frame is the Lua's death event's (PZA/1.3, ruling P23-AO: death.frame.signal
    "event") and its frameSeq is known, the frames end at the event's own frame (the frames after it, read until the
    stop settled, are the dead character's). check.signal names what ended the session (SIGNALS: death.via "event",
    "frame" or "players" as "event", "frame_health" or "players"; None for a record without via)."""
    out = _d(out)
    loop = _d(out.get("loop"))
    if _d(out.get("stop")).get("reason") != "death":
        return None
    death = _d(loop.get("death"))
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)] or \
        [f for f in _l(death.get("last_frames")) if isinstance(f, dict)]
    dframe = _d(death.get("frame"))
    end = _n(dframe.get("frameSeq")) if dframe.get("signal") == "event" else None
    if end is not None:
        frames = [f for f in frames if (_n(f.get("seq")) or 0) <= end]
    k = next((i for i in range(1, len(frames)) if GT._wound(frames[i - 1], frames[i])), None)
    window = frames[k - 1:] if k is not None else frames
    check = GT.death_check(dict(death, last_frames=window))
    check["signal"] = SIGNALS.get(death.get("via"))
    on = bool(frames) and any((_n(_d(frames[0].get("body")).get(w)) or 0) > 0 for w in GT.WOUND_KEYS)
    return {"first_wound_seq": frames[k].get("seq") if k is not None else None, "window_frames": len(window),
            "window_frames_n": len(window), "window_truncated": k == 1 or on,
            "explained": check["explained"], "check": check}


def grade_e1(out, prev=None):
    """The chain session report (Plan 23 Task 15): survived (stop in SURVIVED), game_minutes and minutes_source
    (e_minutes: worldAge), needs, fights, fights_unresolved, load, lineage (loop.lineage when a dict, else chain.lineage_diff(prev, first kept frame) given prev;
    lineage_source loop | rebuilt | None), cost {p50, p99, max, over5}, death (e_death), report_lines."""
    out = _d(out)
    loop = _d(out.get("loop"))
    stop = _d(out.get("stop"))
    minutes, msrc = e_minutes(out)
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)]
    if isinstance(loop.get("lineage"), dict):          # the driver record is the truth (P23-X)
        lineage, source = loop["lineage"], "loop"
    elif prev is not None:                              # the kept frames may no longer hold the first frame
        lineage, source = CH.lineage_diff(prev, frames[0] if frames else {}), "rebuilt"
    else:
        lineage, source = None, None
    cost = _d(loop.get("cost"))
    g = {"grade": "grade_e1", "session_key": out.get("session_key"), "run_id": out.get("run_id"),
         "stop": {"reason": stop.get("reason"), "detail": stop.get("detail")} if stop else None,
         "survived": stop.get("reason") in SURVIVED,
         "game_minutes": minutes, "minutes_source": msrc,
         "needs": e_needs(out), "fights": e_fights(loop.get("fights")), "fights_unresolved": unresolved_fights(out), "load": e_load(loop), "lineage": lineage, "lineage_source": source,
         "cost": {k: cost.get(k) for k in ("p50", "p99", "max", "over5")}, "death": e_death(out)}
    g["report_lines"] = report_lines_e(g)
    return g


def report_lines_e(g):
    """grade_e1 findings, one line each, the gate verdict first when g carries a `gate`."""
    g = _d(g)
    lines = []
    gate = g.get("gate")
    if isinstance(gate, dict):
        lines.append("gate_e1 %s: %s" % (gate.get("verdict"), ", ".join(
            "%s %s >= %s %s" % (k, _d(v).get("value"), _d(v).get("threshold"), "ok" if _d(v).get("ok") else "FAIL")
            if k not in ("death_explained", "fights_resolved") else
            "%s %s%s" % (k, "%s unresolved " % v.get("value") if k == "fights_resolved" else "",
                         "ok" if _d(v).get("ok") else "FAIL")
            for k, v in _d(gate.get("gates")).items())))
    st = _d(g.get("stop"))
    lines.append("%s (stop %s), %s game min (%s)" % ("survived" if g.get("survived") else "not survived",
                                                    st.get("reason"), _f(g.get("game_minutes"), "%.0f"),
                                                    g.get("minutes_source")))
    nd = _d(g.get("needs"))
    for k in ("drink", "eat"):
        v = _d(nd.get(k))
        lines.append("%s: sent %s, done %s, stat fell %s" % (k, v.get("sent"), v.get("done"), v.get("stat_fell")))
    lines.append("unknown consumes (no valid use): %s; frame time base %s" % (nd.get("unknown"), nd.get("time_base")))
    sl = _d(nd.get("sleep"))
    lines.append("sleep: sent %s, done %s, slept %s h, fatigue fell %s" % (
        sl.get("sent"), sl.get("done"), _f(sl.get("sleptH"), "%.1f"), sl.get("fatigue_fell")))
    fs = _d(g.get("fights"))
    lines.append("fights: %s (ended %s, fled %s, stand-offs %s)" % (fs.get("n"), fs.get("ended"), fs.get("fled"),
                                                                   fs.get("stand_offs")))
    lines.append("fights_resolved: unresolved %s" % g.get("fights_unresolved"))
    ld = _d(g.get("load"))
    lines.append("load: max ratio %s, guard drops %s, flee drops %s" % (
        _f(ld.get("max_ratio"), "%.3f"), ld.get("guard_drops"), ld.get("flee_drops")))
    if isinstance(g.get("lineage"), dict):
        lines.append("lineage %s (position d %s)" % ("ok" if g["lineage"].get("ok") else "BROKEN",
                                                    _f(_d(g["lineage"].get("position")).get("d"))))
    co = _d(g.get("cost"))
    lines.append("cost p50 %s ms, p99 %s ms, max %s ms, over5 %s" % (
        _f(co.get("p50"), "%.3f"), _f(co.get("p99"), "%.3f"), _f(co.get("max"), "%.3f"), co.get("over5")))
    de = g.get("death")
    if isinstance(de, dict):
        lines.append("death %s by the frames: first wound seq %s, window %s frames: %s" % (
            "explained" if de.get("explained") else "NOT explained", de.get("first_wound_seq"),
            de.get("window_frames_n"), _d(de.get("check")).get("why")))
    return lines


def gate_e1(outs):
    """{verdict, gates, lineage_sources} over a chain artifacts in order: alive_through (the summed game_minutes >= 1440
    and no death), fights_resolved (no unresolved fight summed over the chain, value the count), drink_done, eat_done, sleep_done (each >= 1 summed done), and death_explained when an artifact died (the
    first death in the chain). Each gate {ok, value, threshold, n} (n the artifacts read); verdict GO when every gate
    is ok, else NO-GO."""
    outs = [_d(o) for o in _l(outs)]
    grades, prev = [], None
    for o in outs:
        grades.append(grade_e1(o, prev))
        prev = o
    n = len(outs)
    minutes = sum(g["game_minutes"] or 0 for g in grades)
    dead = any(g["death"] is not None for g in grades)
    done = {k: sum(_d(g["needs"].get(k)).get("done", 0) for g in grades) for k in ("drink", "eat", "sleep")}
    gates = {"alive_through": {"ok": minutes >= ALIVE_MINUTES and not dead, "value": minutes,
                               "threshold": ALIVE_MINUTES, "n": n}}
    unresolved = sum(g["fights_unresolved"] for g in grades)
    gates["fights_resolved"] = {"ok": unresolved == 0, "value": unresolved, "threshold": 0, "n": n}
    for k in ("drink", "eat", "sleep"):
        gates["%s_done" % k] = {"ok": done[k] >= 1, "value": done[k], "threshold": 1, "n": n}
    first = next((g["death"] for g in grades if g["death"] is not None), None)
    if first is not None:
        gates["death_explained"] = {"ok": first["explained"] is True, "value": first["explained"],
                                    "threshold": True, "n": n}
    ok = bool(grades) and all(v["ok"] for v in gates.values())
    return {"verdict": "GO" if ok else "NO-GO", "gates": gates, "lineage_sources": [g["lineage_source"] for g in grades]}
