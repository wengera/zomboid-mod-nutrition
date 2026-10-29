"""gates_e -- the chain sessions' grade (Plan 23 Task 15): `grade_e1(out, prev=None)` over one e_day artifact and
`gate_e1(outs)` over a chain's artifacts in order.

Reads (every key tolerated missing; a non-dict reads as empty, nothing raises):
  out.stop {reason, wallS}; out.loop.{first_game_min, game_min, wallS, last_frames [{seq, wallMs, gameMin, body, load,
  stats, me}], actions [{type, state, sentS, endedS, use, branch}], night.sleeps [{state, sleptH, fatigueBefore,
  fatigueAfter}], fights [{fight_ticks, flee {..}, end}], first_world_age, cost, lineage, death {last_frames, server_damage}}.
A consume action `use` is "drink"/"water" or "eat"/"food" (anything else counts under needs.unknown); a drop action
`branch` is "load" (a guard drop) or "threat" (a flee drop).

Frame time: a frame sits at loop.wallS (else stop.wallS) less the wall seconds between it and the last kept frame,
i.e. the last kept frame is taken to stand at the loop end; stat_fell compares the last frame before an action sentS
with the first frame after its endedS, and is None when the kept frames do not bracket it.

Every function here is versioned per pass: once an artifact carries its output it is never edited, a later pass is
grade_e2 / gate_e2. The death check is gates.death_check, the frozen function, reused."""
import os
import re

from agent.base import gates as GT
from agent.base.planner.goals import WOODS_R
from agent.base.planner.survive import DANGER_R, DOOR_FAILS, DOOR_NEAR_R
from agent.base.transport.files import FileTransport
from agent.base.world import World, me_floor, me_xy
from agent.driverlib import chain as CH

SURVIVED = GT.SURVIVED
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
    lie before them."""
    out = _d(out)
    loop = _d(out.get("loop"))
    if _d(out.get("stop")).get("reason") != "death":
        return None
    death = _d(loop.get("death"))
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)] or \
        [f for f in _l(death.get("last_frames")) if isinstance(f, dict)]
    k = next((i for i in range(1, len(frames)) if GT._wound(frames[i - 1], frames[i])), None)
    window = frames[k - 1:] if k is not None else frames
    check = GT.death_check(dict(death, last_frames=window))
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


# ---------------------------------------------------------------- pass 2: PZA/1.3's death signal (ruling P23-AO)
# grade_e2 / gate_e2 / report_lines_e2 (PZA/1.3, ruling P23-AO; grade_e1 and gate_e1 frozen as at a029dfab, CLAUDE.md
# section 5): grade_e1's output but for `grade` ("grade_e2"), `death` (e_death_2) and `report_lines` (report_lines_e2).
# e_death_2 is e_death with check.signal, the signal that ended the session (SIGNALS: loop.death.via "event", "frame" or
# "players" as "event", "frame_health" or "players"; None for a record without via), and, when the death frame is the
# Lua's death event's (death.frame.signal "event") with its frameSeq known, the kept frames cut at the event's own frame
# (the frames after it, read until the stop settled, are the dead character's). gate_e2 is gate_e1 over grade_e2.
# loop.death.via -> the signal that ended the session (e_death_2's check.signal)
SIGNALS = {"event": "event", "frame": "frame_health", "players": "players"}


def e_death_2(out):
    """e_death, with check.signal and, for an event death whose frameSeq is known, the kept frames (loop.last_frames
    and death.last_frames) cut at the event's frame (the pass 2 comment above)."""
    out = _d(out)
    loop = _d(out.get("loop"))
    death = _d(loop.get("death"))
    dframe = _d(death.get("frame"))
    end = _n(dframe.get("frameSeq")) if dframe.get("signal") == "event" else None
    if end is not None:
        def cut(frames):
            return [f for f in _l(frames) if isinstance(f, dict) and (_n(f.get("seq")) or 0) <= end]
        loop = dict(loop, last_frames=cut(loop.get("last_frames")),
                    death=dict(death, last_frames=cut(death.get("last_frames"))))
        out = dict(out, loop=loop)
    d = e_death(out)
    if d is not None:
        d["check"]["signal"] = SIGNALS.get(death.get("via"))
    return d


def grade_e2(out, prev=None):
    """grade_e1(out, prev) but for grade "grade_e2", death (e_death_2) and report_lines (report_lines_e2)."""
    g = grade_e1(out, prev)
    g["grade"] = "grade_e2"
    g["death"] = e_death_2(out)
    g["report_lines"] = report_lines_e2(g)
    return g


def report_lines_e2(g):
    """report_lines_e's lines, the gate line naming gate_e2 and the death line its signal."""
    g = _d(g)
    lines = report_lines_e(g)
    if isinstance(g.get("gate"), dict) and lines and lines[0].startswith("gate_e1 "):
        lines[0] = "gate_e2 " + lines[0][len("gate_e1 "):]
    de = g.get("death")
    if isinstance(de, dict):
        for i, line in enumerate(lines):
            if line.startswith("death "):
                lines[i] = "death (signal %s) %s" % (_d(de.get("check")).get("signal"), line[len("death "):])
    return lines


def gate_e2(outs):
    """gate_e1's gates over grade_e2 (its death the event-cut window): {verdict, gates, lineage_sources}."""
    outs = [_d(o) for o in _l(outs)]
    grades, prev = [], None
    for o in outs:
        grades.append(grade_e2(o, prev))
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


# ---------------------------------------------------------------- pass 3: real wounds and the care readings (Plan 24 Task 11)
# grade_e3 / gate_e3 / report_lines_e3 (PZA/1.5.2, survival iteration 6; grade_e2, gate_e2 and the passes before them
# frozen, CLAUDE.md section 5). Since PZA/1.5 a body part enters body.parts when it is bandaged or bleeding even at full
# health (Task 9 review, finding 4), so the old wound reading (gates._wound: a parts entry appearing counts) reads a
# bandage as a wound. Pass 3 counts a wound as a rise in body.bleeding/scratched/bitten or a parts entry that carries
# one: h below FULL_PART_H, bleeding, deep or infected. A bandaged part at full health is no wound. The parts entries
# that carry none are dropped from each frame (real_frame) before gates._wound reads it, so the death window's wound
# arm (gates.death_check) reads the same wounds. The care readings come from loop.actions, loop.results (the sent
# actions' results by aid, driverlib/day.py Chain.extra_record), the kept frames' me.aiming and loop.fights.
FULL_PART_H = 100.0
APPROACH_TYPES = ("attack", "walkTo", "steer")


def real_part(p):
    """Whether a body.parts entry carries a wound: h below FULL_PART_H, or bleeding, deep or infected."""
    p = _d(p)
    h = _n(p.get("h"))
    return (h is not None and h < FULL_PART_H) or p.get("bleeding") is True or p.get("deep") is True \
        or p.get("infected") is True


def real_frame(f):
    """The frame with body.parts cut to the entries real_part holds (a copy; the frame itself is untouched)."""
    f = _d(f)
    b = _d(f.get("body"))
    return dict(f, body=dict(b, parts=[p for p in _l(b.get("parts")) if real_part(p)]))


def _real_out(out):
    """The artifact with loop.last_frames and loop.death.last_frames passed through real_frame."""
    out = _d(out)
    loop = _d(out.get("loop"))
    death = loop.get("death")
    loop = dict(loop, last_frames=[real_frame(f) for f in _l(loop.get("last_frames")) if isinstance(f, dict)])
    if isinstance(death, dict):
        loop["death"] = dict(death, last_frames=[real_frame(f) for f in _l(death.get("last_frames"))
                                                 if isinstance(f, dict)])
    return dict(out, loop=loop)


def e_wounds(out):
    """{real, listed, first_seq, frames}: over the kept frames, `real` the frame pairs showing a wound by the pass 3
    reading (gates._wound over real_frame), `listed` the pairs the old reading (gates._wound over the frames as they
    are) counts, first_seq the first frame of a real wound, frames the kept frames read. listed - real is what the
    old reading took for wounds: the parts listed for a bandage or a bleed at full health."""
    frames = [f for f in _l(_d(_d(out).get("loop")).get("last_frames")) if isinstance(f, dict)]
    real = [f for i, f in enumerate(frames[1:], 1) if GT._wound(real_frame(frames[i - 1]), real_frame(f))]
    listed = sum(1 for i in range(1, len(frames)) if GT._wound(frames[i - 1], frames[i]))
    return {"real": len(real), "listed": listed, "first_seq": real[0].get("seq") if real else None,
            "frames": len(frames)}


def e_death_3(out):
    """e_death_2 over the frames cut to their real wounds (real_frame)."""
    return e_death_2(_real_out(out))


def _results(loop):
    """{aid: result} off loop.results rows {aid, type, state, result}."""
    return {r.get("aid"): _d(r.get("result")) for r in _l(loop.get("results")) if isinstance(r, dict)}


def _in_fight(a, f):
    s, e = _n(f.get("startS")), _n(_d(f.get("end")).get("endS"))
    t = _n(a.get("sentS"))
    return s is not None and t is not None and t >= s and (e is None or t <= e)


def e_standing(loop, res):
    """{n, outcomes {kill, flee, fallback, stagger, none}, rows}: a standing fight is a fight whose first action sent
    in its window is an aim. Its outcome, first that holds: kill (an attack or an aim of the window read targetDead),
    flee (the fight's flee dict is not empty), fallback (an aim of the window ended failed or rejected and an attack,
    walkTo or steer was sent after it: the stance's fallback to the approach), stagger (an attack of the window
    started, the target alive at the fight's end: the swings landed or pushed), else none."""
    acts = sorted((_d(a) for a in _l(loop.get("actions"))), key=lambda a: _n(a.get("sentS")) or 0.0)
    rows, out = [], {"kill": 0, "flee": 0, "fallback": 0, "stagger": 0, "none": 0}
    for i, f in enumerate(f for f in _l(loop.get("fights")) if isinstance(f, dict)):
        win = [a for a in acts if _in_fight(a, f)]
        if not win or win[0].get("type") != "aim":
            continue
        kill = any(res.get(a.get("aid"), {}).get("targetDead") is True for a in win if a.get("type") in ("attack", "aim"))
        bad = [a for a in win if a.get("type") == "aim" and a.get("state") in ("failed", "rejected")]
        fallback = any(b.get("type") in APPROACH_TYPES and (_n(b.get("sentS")) or 0) > (_n(a.get("sentS")) or 0)
                       for a in bad for b in win)
        stagger = any(res.get(a.get("aid"), {}).get("attackStarted") is True for a in win if a.get("type") == "attack")
        outcome = ("kill" if kill else "flee" if _d(f.get("flee")) else "fallback" if fallback
                   else "stagger" if stagger else "none")
        out[outcome] += 1
        rows.append({"fight": i, "outcome": outcome, "actions": [a.get("type") for a in win],
                     "aim_states": [a.get("state") for a in win if a.get("type") == "aim"]})
    return {"n": len(rows), "outcomes": out, "rows": rows}


def e_care(out):
    """The care, stance, water-chain and climb readings of a session: {bandage {sent, done, failed, by_part, dirty},
    rip {sent, done, rags, dirty_rags}, wash {sent, done, water}, fill {sent, done, fills [{fluid, tainted, added,
    amount}], tainted}, stance {aim_sent, aim_done, aim_failed, held_at_end, released, target_dead, moved,
    frames_aiming, frames}, standing (e_standing), climb {sent, done, fell, failed, wounds, tall}, loot
    {sent, done, containers, containers_moved}, need_chain {drink_done, drink_stat_fell, fills_done,
    containers_looted}}. A result field the record lacks is skipped by the sums, never read as a value."""
    out = _d(out)
    loop = _d(out.get("loop"))
    res = _results(loop)
    acts = [_d(a) for a in _l(loop.get("actions"))]

    def of(t):
        return [a for a in acts if a.get("type") == t]

    def done(rows):
        return [a for a in rows if a.get("state") == "done"]

    def total(rows, key):
        return sum(_n(res.get(a.get("aid"), {}).get(key)) or 0 for a in rows)

    def failed(rows):
        return sum(1 for a in rows if a.get("state") in ("failed", "rejected"))

    bd = done(of("bandage"))
    by_part = {}
    for a in bd:
        p = res.get(a.get("aid"), {}).get("part", _d(a.get("args")).get("part"))
        by_part[str(p)] = by_part.get(str(p), 0) + 1
    fl = done(of("fill"))
    fills = []
    for a in fl:
        r = res.get(a.get("aid"), {})
        fills.append({"fluid": r.get("fluid"), "tainted": r.get("tainted"), "added": r.get("added"),
                      "amount": r.get("amount")})
    aims = of("aim")
    ad = done(aims)
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)]
    cl = of("climb")
    lt = [a for a in of("interact") if _d(a.get("args")).get("kind") == "loot"]
    cont = [a for a in lt if _d(a.get("args")).get("filter") == "container"]
    needs = e_needs(out)
    return {
        "bandage": {"sent": len(of("bandage")), "done": len(bd), "failed": failed(of("bandage")),
                    "by_part": by_part, "dirty": sum(1 for a in bd if res.get(a.get("aid"), {}).get("dirty") is True)},
        "rip": {"sent": len(of("rip")), "done": len(done(of("rip"))), "rags": total(done(of("rip")), "rags"),
                "dirty_rags": total(done(of("rip")), "dirty")},
        "wash": {"sent": len(of("wash")), "done": len(done(of("wash"))), "water": total(done(of("wash")), "water")},
        "fill": {"sent": len(of("fill")), "done": len(fl), "fills": fills,
                 "tainted": sum(1 for x in fills if x["tainted"] is True)},
        "stance": {"aim_sent": len(aims), "aim_done": len(ad), "aim_failed": failed(aims),
                   "held_at_end": sum(1 for a in ad if res.get(a.get("aid"), {}).get("held") is True),
                   "released": sum(1 for a in ad if res.get(a.get("aid"), {}).get("held") is False),
                   "target_dead": sum(1 for a in ad if res.get(a.get("aid"), {}).get("targetDead") is True),
                   "moved": total(ad, "d"),
                   "frames_aiming": sum(1 for f in frames if _d(f.get("me")).get("aiming") is True),
                   "frames": len(frames)},
        "standing": e_standing(loop, res),
        "climb": {"sent": len(cl), "done": len(done(cl)), "fell": sum(1 for a in cl if a.get("reason") == "fell"),
                  "failed": sum(1 for a in cl if a.get("state") == "failed" and a.get("reason") != "fell"),
                  "wounds": total(cl, "wounds"),
                  "tall": sum(1 for a in done(cl) if res.get(a.get("aid"), {}).get("tall") is True)},
        "loot": {"sent": len(lt), "done": len(done(lt)), "containers": len(done(cont)),
                 "containers_moved": total(done(cont), "moved")},
        "need_chain": {"drink_done": needs["drink"]["done"], "drink_stat_fell": needs["drink"]["stat_fell"],
                       "fills_done": len(fl), "containers_looted": len(done(cont))}}


def report_lines_e3(g):
    """report_lines_e2's lines (the gate line naming gate_e3) then the wound, care, stance and climb lines."""
    g = _d(g)
    lines = report_lines_e2(g)
    if lines and lines[0].startswith("gate_e2 "):
        lines[0] = "gate_e3 " + lines[0][len("gate_e2 "):]
    w, c = _d(g.get("wounds")), _d(g.get("care"))
    if w:
        lines.append("wounds: %s real over %s kept frames (the old reading counted %s), first seq %s" % (
            w.get("real"), w.get("frames"), w.get("listed"), w.get("first_seq")))
    if c:
        b, r, wa, fi = _d(c.get("bandage")), _d(c.get("rip")), _d(c.get("wash")), _d(c.get("fill"))
        lines.append("care: bandage sent %s done %s (parts %s, dirty %s), rip done %s (%s rags), wash done %s (%s water)" % (
            b.get("sent"), b.get("done"), b.get("by_part"), b.get("dirty"), r.get("done"), r.get("rags"),
            wa.get("done"), wa.get("water")))
        lines.append("fill: sent %s done %s, tainted %s, fills %s" % (fi.get("sent"), fi.get("done"),
                                                                      fi.get("tainted"), fi.get("fills")))
        s, sf = _d(c.get("stance")), _d(c.get("standing"))
        lines.append("stance: aim sent %s done %s failed %s (held %s, released %s, target dead %s), %s of %s kept "
                     "frames aiming; standing fights %s %s" % (
                         s.get("aim_sent"), s.get("aim_done"), s.get("aim_failed"), s.get("held_at_end"),
                         s.get("released"), s.get("target_dead"), s.get("frames_aiming"), s.get("frames"),
                         sf.get("n"), sf.get("outcomes")))
        cl, nc = _d(c.get("climb")), _d(c.get("need_chain"))
        lines.append("climb: sent %s done %s fell %s failed %s wounds %s; need chain: drinks %s (stat fell %s), "
                     "fills %s, containers looted %s" % (
                         cl.get("sent"), cl.get("done"), cl.get("fell"), cl.get("failed"), cl.get("wounds"),
                         nc.get("drink_done"), nc.get("drink_stat_fell"), nc.get("fills_done"),
                         nc.get("containers_looted")))
    return lines


def grade_e3(out, prev=None):
    """grade_e2(out, prev) but for grade "grade_e3", death (e_death_3: the real wounds), `wounds` (e_wounds), `care`
    (e_care) and report_lines (report_lines_e3)."""
    g = grade_e2(out, prev)
    g["grade"] = "grade_e3"
    g["death"] = e_death_3(out)
    g["wounds"] = e_wounds(out)
    g["care"] = e_care(out)
    g["report_lines"] = report_lines_e3(g)
    return g


def gate_e3(outs):
    """gate_e2's gates over grade_e3 (its death the real-wound window): {verdict, gates, lineage_sources}."""
    outs = [_d(o) for o in _l(outs)]
    grades, prev = [], None
    for o in outs:
        grades.append(grade_e3(o, prev))
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


# ---------------------------------------------------------------- pass 4: kills the headline, the stance held, the ride, the glides (Plan 24 Task 17)
# grade_e4 / gate_e4 / report_lines_e4 (PZA/1.5.6, survival iteration 7; grade_e3, gate_e3 and the passes before them
# frozen, CLAUDE.md section 5). The headline is kills (ruling P24-Q): the engine's count (the death event's
# zombiesKilled, present only when the session died) beside the planner's (the distinct targetIds of the attacks and
# aims whose result read targetDead, a lower bound: World.kills, #4321's bound). Beside gate_e3's readings: the stance's
# own held count per aim leg (the Lua's heldFrames of ticks) beside the frames' `aiming` and `forceAim`, the riding
# bandages (keepMoving) against the standing ones, the care branch's yield, and the glides. The care yield and the dead
# skip live in the decision log, not in the artifact: `decision_readings(lines)` reads them off its lines (the grade
# script passes the log beside the artifact), and the artifact alone gives `yields.fights_ended_by_care`.
GLIDE_MIN_S = 0.95                  # a `moving` false run of a second less the frames' spacing (E6's ten frames: 0.992 to 1.002 s)
RUN_GAITS = ("run", "sprint")


def _kill_ids(loop, res, lo=None, hi=None):
    """The distinct targetIds of the attacks and aims of loop.actions (sent within lo..hi seconds when given) whose
    result read targetDead true."""
    ids = []
    for a in (_d(x) for x in _l(loop.get("actions"))):
        if a.get("type") not in ("attack", "aim") or res.get(a.get("aid"), {}).get("targetDead") is not True:
            continue
        t = _n(a.get("sentS"))
        if lo is not None and (t is None or t < lo or (hi is not None and t > hi)):
            continue
        zid = _d(a.get("args")).get("targetId")
        if zid is not None and zid not in ids:
            ids.append(zid)
    return ids


def e_kills(out):
    """{engine, planner, planner_ids, per_fight [kills of each fight of loop.fights], standing_fights, standing_kills,
    per_standing_fight, died, died_at}: `engine` the death event's zombiesKilled (None when the session did not die,
    or the event carries none), `planner` the distinct kill ids off the action results, `per_fight` the same count
    inside each fight's window, `standing_kills` the kills in the standing fights (e_standing) and
    `per_standing_fight` their ratio (None without a standing fight)."""
    out = _d(out)
    loop = _d(out.get("loop"))
    death = _d(loop.get("death"))
    ev = _d(death.get("event")) or _d(_d(death.get("frame")).get("event"))
    engine = _n(ev.get("zombiesKilled"))
    res = _results(loop)
    ids = _kill_ids(loop, res)
    per = []
    for f in (f for f in _l(loop.get("fights")) if isinstance(f, dict)):
        s, e = _n(f.get("startS")), _n(_d(f.get("end")).get("endS"))
        per.append(len(_kill_ids(loop, res, s, e)) if s is not None else 0)
    standing = e_standing(loop, res)
    sk = sum(per[r["fight"]] for r in standing["rows"] if r["fight"] < len(per))
    died = loop.get("death") is not None or _d(out.get("stop")).get("reason") == "death"
    at = _n(death.get("gameMin"))
    at = at if at is not None else _n(_d(out.get("stop")).get("gameMin"))
    return {"engine": engine, "planner": len(ids), "planner_ids": ids, "per_fight": per,
            "standing_fights": standing["n"], "standing_kills": sk,
            "per_standing_fight": sk / standing["n"] if standing["n"] else None,
            "died": died, "died_at": at if died else None}


def e_stance_held(out):
    """{legs, with_field, ticks, held_frames, ratio, per_leg [{aid, heldFrames, ticks}], frames_aiming,
    frames_force_aim, frames}: the stance's live hold. Per done aim leg the Lua's own count (the result's heldFrames of
    ticks, PZA/1.5.4; a leg whose result lacks them is in `legs` and not in `with_field`), `ratio` the held share of
    the ticks, beside the kept frames' me.aiming and me.forceAim (true counts; the frames are the last kept ones
    only)."""
    loop = _d(_d(out).get("loop"))
    res = _results(loop)
    legs = [a for a in (_d(x) for x in _l(loop.get("actions"))) if a.get("type") == "aim" and a.get("state") == "done"]
    per = []
    for a in legs:
        r = res.get(a.get("aid"), {})
        if _n(r.get("ticks")) is not None and _n(r.get("heldFrames")) is not None:
            per.append({"aid": a.get("aid"), "heldFrames": r["heldFrames"], "ticks": r["ticks"]})
    ticks = sum(p["ticks"] for p in per)
    held = sum(p["heldFrames"] for p in per)
    frames = [f for f in _l(loop.get("last_frames")) if isinstance(f, dict)]
    return {"legs": len(legs), "with_field": len(per), "ticks": ticks, "held_frames": held,
            "ratio": held / ticks if ticks else None, "per_leg": per,
            "frames_aiming": sum(1 for f in frames if _d(f.get("me")).get("aiming") is True),
            "frames_force_aim": sum(1 for f in frames if _d(f.get("me")).get("forceAim") is True),
            "frames": len(frames)}


def e_ride(out):
    """{riding {sent, done, walking, failed, stopped, rejected, by_part}, standing {sent, done, failed}}: the
    bandages sent with keepMoving true (riding) against the others. `walking` the done ones whose result read walking
    true, `stopped` those ended failed with the reason stopped, `failed` every failed one, `rejected` the rejected."""
    loop = _d(_d(out).get("loop"))
    res = _results(loop)
    bands = [a for a in (_d(x) for x in _l(loop.get("actions"))) if a.get("type") == "bandage"]
    ride = [a for a in bands if _d(a.get("args")).get("keepMoving") is True]
    stand = [a for a in bands if _d(a.get("args")).get("keepMoving") is not True]
    by_part = {}
    for a in ride:
        if a.get("state") == "done":
            p = res.get(a.get("aid"), {}).get("part", _d(a.get("args")).get("part"))
            by_part[str(p)] = by_part.get(str(p), 0) + 1
    return {"riding": {"sent": len(ride), "done": sum(1 for a in ride if a.get("state") == "done"),
                       "walking": sum(1 for a in ride if a.get("state") == "done"
                                      and res.get(a.get("aid"), {}).get("walking") is True),
                       "failed": sum(1 for a in ride if a.get("state") == "failed"),
                       "stopped": sum(1 for a in ride if a.get("state") == "failed" and a.get("reason") == "stopped"),
                       "rejected": sum(1 for a in ride if a.get("state") == "rejected"), "by_part": by_part},
            "standing": {"sent": len(stand), "done": sum(1 for a in stand if a.get("state") == "done"),
                         "failed": sum(1 for a in stand if a.get("state") in ("failed", "rejected"))}}


def e_yields(out):
    """{care_actions, fights_ended_by_care}: from the artifact alone, the actions sent by the care branch and the
    fights whose end line was a care line (the threat branch yielded to the care, P24-P). The firings themselves are
    decision_readings'."""
    loop = _d(_d(out).get("loop"))
    return {"care_actions": sum(1 for a in _l(loop.get("actions")) if _d(a).get("branch") == "care"),
            "fights_ended_by_care": sum(1 for f in _l(loop.get("fights"))
                                        if _d(_d(f).get("end")).get("branch") == "care")}


def decision_readings(lines):
    """{lines, care_yields, care_rides, dead_skips, dead_ids, kill_lines} off decision.log lines (dicts, `unparsed`
    ones skipped): `care_yields` the care lines whose threat why reads care true (the threat held, the branch
    yielded: inputs.branches.threat {care, nearest, held}), `care_rides` those with ride true (P24-U), `dead_skips`
    the lines whose threat why lists dead ids (the dead target skipped) and `dead_ids` the distinct ids,
    `kill_lines` the lines whose threat why carries a kill."""
    n = yields = rides = skips = kl = 0
    ids = []
    for ln in _l(lines):
        ln = _d(ln)
        if "unparsed" in ln:
            continue
        n += 1
        why = _d(_d(_d(ln.get("inputs")).get("branches")).get("threat"))
        if ln.get("branch") == "care" and why.get("care") is True:
            yields += 1
            rides += 1 if why.get("ride") is True else 0
        if _l(why.get("dead")):
            skips += 1
            ids.extend(z for z in why["dead"] if z not in ids)
        if why.get("kill") is not None:
            kl += 1
    return {"lines": n, "care_yields": yields, "care_rides": rides, "dead_skips": skips, "dead_ids": ids,
            "kill_lines": kl}


def e_glides(out):
    """{runs, tiles, rows [{seq, startS, endS, s, tiles, gait, aid}], base}: the glides, an inference and never a
    trip (the E6 guide's: its six were runs of ten frames, 0.992 to 1.002 s, `moving` false with the position
    changing, none read on a walk). A glide is a run of consecutive kept frames with me.moving false, lasting at least
    GLIDE_MIN_S (first frame to last), inside one walkTo or steer leg sent at a run or sprint gait (sentS to endedS, an
    open leg to the end). Only the kept frames are read."""
    out = _d(out)
    loop = _d(out.get("loop"))
    times, base = frame_times(out)
    legs = [(a, _n(a.get("sentS")), _n(a.get("endedS"))) for a in (_d(x) for x in _l(loop.get("actions")))
            if a.get("type") in ("walkTo", "steer") and _d(a.get("args")).get("gait") in RUN_GAITS]

    def leg_of(t):
        for a, s, e in legs:
            if s is not None and t >= s and (e is None or t <= e):
                return a
        return None

    rows, run = [], []

    def close():
        if len(run) >= 2 and run[-1][0] - run[0][0] >= GLIDE_MIN_S:
            f0, f1 = _d(run[0][1].get("me")), _d(run[-1][1].get("me"))
            dx = (_n(f1.get("x")) or 0.0) - (_n(f0.get("x")) or 0.0)
            dy = (_n(f1.get("y")) or 0.0) - (_n(f0.get("y")) or 0.0)
            a = run[0][2]
            rows.append({"seq": run[0][1].get("seq"), "startS": run[0][0], "endS": run[-1][0],
                         "s": run[-1][0] - run[0][0], "tiles": (dx * dx + dy * dy) ** 0.5,
                         "gait": _d(a.get("args")).get("gait"), "aid": a.get("aid")})
        del run[:]

    for t, f in times:
        leg = leg_of(t)
        still = leg is not None and _d(f.get("me")).get("moving") is False
        if still and run and run[0][2] is not leg:
            close()
        if still:
            run.append((t, f, leg))
        else:
            close()
    close()
    return {"runs": len(rows), "tiles": sum(r["tiles"] for r in rows), "rows": rows, "base": base}


def _headline(g):
    k = _d(g.get("kills"))
    state = "died at %s" % _f(k.get("died_at"), "%.0f") if k.get("died") is True else "survived"
    eng = k.get("engine")
    return "kills %s (engine %s, planner %s); %s; %s game minutes" % (
        eng if eng is not None else k.get("planner"), eng if eng is not None else "n/a", k.get("planner"), state,
        _f(g.get("game_minutes"), "%.1f"))


def report_lines_e4(g):
    """The kills headline first, then report_lines_e3's lines (the gate line naming gate_e4), then the pass 4 lines."""
    g = _d(g)
    lines = report_lines_e3(g)
    if lines and lines[0].startswith("gate_e3 "):
        lines[0] = "gate_e4 " + lines[0][len("gate_e3 "):]
    lines.insert(0, _headline(g))
    k, sh, rd, y, gl = (_d(g.get(x)) for x in ("kills", "stance_held", "ride", "yields", "glides"))
    if k:
        lines.append("kills: per fight %s; standing fights %s with %s kills (%s per fight); planner ids %s" % (
            k.get("per_fight"), k.get("standing_fights"), k.get("standing_kills"), _f(k.get("per_standing_fight")),
            k.get("planner_ids")))
    if sh:
        lines.append("stance held: %s of %s ticks over %s aim legs (%s with the field), ratio %s; kept frames: "
                     "%s aiming, %s forceAim of %s" % (
                         sh.get("held_frames"), sh.get("ticks"), sh.get("legs"), sh.get("with_field"),
                         _f(sh.get("ratio")), sh.get("frames_aiming"), sh.get("frames_force_aim"), sh.get("frames")))
    if rd:
        r, s = _d(rd.get("riding")), _d(rd.get("standing"))
        lines.append("bandages: riding sent %s done %s (walking %s) failed %s (stopped %s) rejected %s, parts %s; "
                     "standing sent %s done %s failed %s" % (
                         r.get("sent"), r.get("done"), r.get("walking"), r.get("failed"), r.get("stopped"),
                         r.get("rejected"), r.get("by_part"), s.get("sent"), s.get("done"), s.get("failed")))
    if y:
        log = y.get("log")
        tail = ("; decision log: %s yields (%s riding), %s dead skips of %s ids" % (
            log.get("care_yields"), log.get("care_rides"), log.get("dead_skips"), len(log.get("dead_ids")))
            if isinstance(log, dict) else "; no decision log read")
        lines.append("care yield: %s care actions, %s fights ended by the care%s" % (
            y.get("care_actions"), y.get("fights_ended_by_care"), tail))
    if gl:
        lines.append("glides (an inference, never a trip): %s over %s tiles in the kept frames: %s" % (
            gl.get("runs"), _f(gl.get("tiles")), [(r["seq"], _f(r["s"], "%.3f")) for r in gl.get("rows", [])]))
    return lines


def grade_e4(out, prev=None, decision_lines=None):
    """grade_e3(out, prev) but for grade "grade_e4": `kills` (e_kills, the headline), `stance_held`, `ride`, `yields`
    (with `log`: decision_readings, when decision_lines is given), `glides`, the standing outcome `stagger` renamed
    `stagger_inferred` (no engine signal: an attack started with the target alive) and report_lines (report_lines_e4)."""
    g = grade_e3(out, prev)
    g["grade"] = "grade_e4"
    st = _d(_d(g.get("care")).get("standing"))
    oc = _d(st.get("outcomes"))
    if "stagger" in oc:
        oc["stagger_inferred"] = oc.pop("stagger")
    for r in _l(st.get("rows")):
        if _d(r).get("outcome") == "stagger":
            r["outcome"] = "stagger_inferred"
    g["kills"] = e_kills(out)
    g["stance_held"] = e_stance_held(out)
    g["ride"] = e_ride(out)
    g["yields"] = e_yields(out)
    if decision_lines is not None:
        g["yields"]["log"] = decision_readings(decision_lines)
    g["glides"] = e_glides(out)
    g["report_lines"] = report_lines_e4(g)
    return g


def gate_e4(outs):
    """gate_e3's gates (grade_e4 changes none of what they read), and `kills` {engine, planner} summed over the chain
    (the headline, no gate; engine None when no session died): {verdict, gates, lineage_sources, kills}."""
    outs = [_d(o) for o in _l(outs)]
    res = gate_e3(outs)
    grades, prev = [], None
    for o in outs:
        grades.append(grade_e4(o, prev))
        prev = o
    eng = [g["kills"]["engine"] for g in grades if g["kills"]["engine"] is not None]
    res["kills"] = {"engine": sum(eng) if eng else None, "planner": sum(g["kills"]["planner"] for g in grades)}
    return res


# ---------------------------------------------------------------- pass 5: the whole session's frames, the engage and destination readings (Plan 24 Task 20)
# grade_e5 / gate_e5 / report_lines_e5 (PZA/1.5.6, survival iteration 8; grade_e4, gate_e4 and the passes before them
# frozen, CLAUDE.md section 5). Two gaps of the E7 write-up close here. (1) grade_e4's frame fields (`stance_held`'s
# frames, `wounds`, `glides`, the death window) read loop.last_frames, the driver's last LAST_FRAMES (3000) frames, of a
# session of 8534: grade_e5 reads them over every frame of the artifact's `state*.log` files when they sit beside the
# record (state.log, then the Lua's rotations state.1.log, state.2.log ..., decoded through FileTransport and pza1.py:
# the frame groups merged, the lines in seq order), falling back to the kept frames and saying so (`frames_source`).
# (2) The readings iteration 8 asks for, off the decision log (`e_engage`: the sought fights, the seek legs and their
# pace, the flees' turns to fight, the flees by reason, `many` by the listed count) and off a replay of the state logs
# into a World (`_replay`: each walk's destination against the buildings known at the moment it was sent, each failed
# door interact through the planner's own mark rule), and the loot by kind off the actions.
# The decision log does not name a sought fight (Survive.engaging is not logged): a sought line is a threat-branch line
# whose fight why reads `seek` or whose nearest held zombie is beyond DANGER_R (6; the hold radius reaches ENGAGE_R
# only for a sought fight), an inference named so.
STATE_RX = re.compile(r"state(?:\.(\d+))?\.log")
DEST_BUILDING_R = 3.0               # tiles: a walk ending this near a known building's box is a building walk (its door
                                    # or room square lies on or just outside the box); an inference, ruling P24-Y


def state_files(directory):
    """The state files of `directory` in read order: state.log, then state.1.log, state.2.log ... (the Lua rotates
    state.log to state.<n>.log, so the live file holds the session's start). [] when there are none or the
    directory cannot be listed."""
    try:
        names = os.listdir(directory)
    except (OSError, TypeError):
        return []
    found = [(int(m.group(1) or 0), n) for n in names for m in [STATE_RX.fullmatch(n)] if m]
    return [os.path.join(directory, n) for _, n in sorted(found)]


def session_lines(directory):
    """([line], [file name]): every decoded line of the directory's state files in seq order, the frame groups merged
    (FileTransport); ([], []) when there are no state files or they cannot be read."""
    files = state_files(directory)
    if not files:
        return [], []
    try:
        lines = FileTransport(directory).lines()
    except (OSError, ValueError):
        return [], []
    return lines, [os.path.basename(p) for p in files]


def _frame_row(f):
    """session.frame_row's row (the record's kept form), without importing the driver library's session."""
    return {"seq": f.get("seq"), "wallMs": f.get("wallMs"), "gameMin": f.get("gameMin"), "worldAge": f.get("worldAge"),
            "me": f.get("me"), "body": f.get("body"), "load": f.get("load"), "stats": f.get("stats"),
            "zombies": [{"id": z.get("id"), "dist": z.get("dist")} for z in f.get("zombies") or ()
                        if isinstance(z, dict)]}


def session_frames(lines):
    """The frame rows of `lines`, in order."""
    return [_frame_row(l) for l in _l(lines) if isinstance(l, dict) and l.get("kind") == "frame"]


def _threat_why(ln):
    return _d(_d(_d(_d(ln).get("inputs")).get("branches")).get("threat"))


def e_engage(decision_lines):
    """The engage readings of ruling P24-X off decision.log lines (dicts, `unparsed` ones skipped), the threat
    branch's lines only (`branch` threat): {read, lines, fight_lines, fights, fights_sought, sought_lines, seek_lines,
    seek_legs {walkTo {gait: n}, aim, other}, seek_walk_share, flee_turns, flees {reason: lines}, many_listed_lines,
    many_listed_max}. A fight is a run of adjacent log lines each a threat-branch fight line; sought when its first
    line is (the module comment's inference). `seek_legs` the actions the seek lines sent, by type and the walkTo's
    gait; `seek_walk_share` the walks at a walk of the seek walks; `flee_turns` the fight lines the planner read
    while its mode was flee (inputs.mode, the mode before the tick); `flees` the lines answering with a flee, by
    reason; `many_listed_*` the lines whose `many` the listed count alone made (why.listed). {read: False} when no
    decision log was given."""
    if decision_lines is None:
        return {"read": False}
    fights = sought_fights = sought_lines = seek_lines = turns = fight_lines = listed_lines = 0
    legs = {"walkTo": {}, "aim": 0, "other": 0}
    flees, listed_max, prev_fight = {}, None, False
    for ln in (_d(x) for x in _l(decision_lines)):
        if "unparsed" in ln:
            continue
        why = _threat_why(ln)
        is_fight = ln.get("branch") == "threat" and why.get("fight") is True
        if is_fight:
            fight_lines += 1
            near = _n(_d(ln.get("inputs")).get("nearest"))
            sought = why.get("seek") is True or (near is not None and near > DANGER_R)
            if sought:
                sought_lines += 1
            if not prev_fight:
                fights += 1
                sought_fights += 1 if sought else 0
            if _d(ln.get("inputs")).get("mode") == "flee":
                turns += 1
            if why.get("seek") is True:
                seek_lines += 1
                a = _d(ln.get("action"))
                if a.get("type") == "walkTo":
                    g = str(_d(a.get("args")).get("gait"))
                    legs["walkTo"][g] = legs["walkTo"].get(g, 0) + 1
                elif a.get("type") == "aim":
                    legs["aim"] += 1
                elif a:
                    legs["other"] += 1
        elif ln.get("branch") == "threat" and isinstance(why.get("flee"), str):
            flees[why["flee"]] = flees.get(why["flee"], 0) + 1
        if ln.get("branch") == "threat" and _n(why.get("listed")) is not None:
            listed_lines += 1
            listed_max = why["listed"] if listed_max is None else max(listed_max, why["listed"])
        prev_fight = is_fight
    walks = sum(legs["walkTo"].values())
    return {"read": True, "lines": len(_l(decision_lines)), "fight_lines": fight_lines, "fights": fights,
            "fights_sought": sought_fights, "sought_lines": sought_lines, "seek_lines": seek_lines,
            "seek_legs": legs, "seek_walk_share": legs["walkTo"].get("walk", 0) / walks if walks else None,
            "flee_turns": turns, "flees": flees, "many_listed_lines": listed_lines, "many_listed_max": listed_max}


def e_loot(out):
    """{sent, done, failed, by_kind {filter: {done, failed}}, failed_reasons {reason: n}}: the loot interacts of
    loop.actions by their filter (the kind of thing wanted)."""
    loop = _d(_d(out).get("loop"))
    by, reasons, sent, done, failed = {}, {}, 0, 0, 0
    for a in (_d(x) for x in _l(loop.get("actions"))):
        args = _d(a.get("args"))
        if a.get("type") != "interact" or args.get("kind") != "loot":
            continue
        sent += 1
        row = by.setdefault(str(args.get("filter")), {"done": 0, "failed": 0})
        if a.get("state") == "done":
            done += 1
            row["done"] += 1
        elif a.get("state") in ("failed", "rejected"):
            failed += 1
            row["failed"] += 1
            reasons[str(a.get("reason"))] = reasons.get(str(a.get("reason")), 0) + 1
    return {"sent": sent, "done": done, "failed": failed, "by_kind": by, "failed_reasons": reasons}


def _replay(out, lines):
    """{walks [{aid, branch, x, y, kind, tiles, building}], marks [{door, reason, atS, building}], tried_marked}, or
    None without lines or a loop start: the state lines applied to a World in order, a walkTo evaluated against the
    buildings known when it was sent (loop second sentS at t_loop0_ms + 1000 sentS on the frames clock), a failed
    door interact (the planner's `_door_failed` rule: an open or close failed for a DOOR_FAILS reason on its own
    square, a loot failed `not adjacent` on the door nearest the player within DOOR_NEAR_R) noted into the World's
    own `note_door_fail` as it ended, and a door interact sent at a square the World had marked counted."""
    loop = _d(_d(out).get("loop"))
    t0 = _n(loop.get("t_loop0_ms"))
    if not lines or t0 is None:
        return None
    events = []
    for a in (_d(x) for x in _l(loop.get("actions"))):
        s, e = _n(a.get("sentS")), _n(a.get("endedS"))
        args = _d(a.get("args"))
        if a.get("type") == "walkTo" and s is not None and _n(args.get("x")) is not None:
            events.append((t0 + s * 1000.0, 0, "walk", a))
        if a.get("type") == "interact" and args.get("kind") in ("open", "close") and s is not None:
            events.append((t0 + s * 1000.0, 1, "send", a))
        if a.get("type") == "interact" and a.get("state") == "failed" and e is not None:
            events.append((t0 + e * 1000.0, 2, "fail", a))
    events.sort(key=lambda ev: (ev[0], ev[1]))
    w = World()
    walks, marks, tried, i = [], [], 0, 0

    def handle(ev):
        nonlocal tried
        at, _, what, a = ev
        args = _d(a.get("args"))
        if what == "walk":
            nb = w.nearest_building(args["x"], args["y"])
            tiles, b = (None, None) if nb is None else nb
            kind = ("other" if tiles is None else "building" if tiles <= DEST_BUILDING_R
                    else "cluster" if tiles <= WOODS_R else "other")
            walks.append({"aid": a.get("aid"), "branch": a.get("branch"), "x": args["x"], "y": args["y"],
                          "kind": kind, "tiles": tiles, "building": b})
            return
        floor = me_floor(w)
        if what == "send":
            if (args.get("x"), args.get("y"), floor) in w.marked_doors():
                tried += 1
            return
        sq, reason = None, a.get("reason")
        if args.get("kind") in ("open", "close") and reason in DOOR_FAILS:
            sq = (args.get("x"), args.get("y"), floor)
        elif args.get("kind") == "loot" and reason == "not adjacent":
            sq = w.door_near(me_xy(w), floor, DOOR_NEAR_R)
        if sq is not None and w.note_door_fail(sq, reason):
            marks.append({"door": list(sq), "reason": reason, "atMs": at, "atS": (at - t0) / 1000.0,
                          "building": w.door_building(sq)})

    for line in lines:
        ms = _n(_d(line).get("wallMs"))
        while i < len(events) and ms is not None and events[i][0] <= ms:
            handle(events[i])
            i += 1
        w.apply(line)
    for ev in events[i:]:
        handle(ev)
    return {"walks": walks, "marks": marks, "tried_marked": tried}


def e_destinations(rep):
    """{read, walks, by_kind {building, cluster, other}, farthest, off_building [first 10 rows of kind other], ok}:
    the walks sent off the threat branch (a seek or a flee leg is no destination) by what stood at the target when
    they were sent (DEST_BUILDING_R, WOODS_R: ruling P24-Y, every walk a building), `farthest` the greatest distance
    from a known building (None when a walk had none known), `ok` no walk of kind other. {read: False} without a
    replay."""
    if rep is None:
        return {"read": False}
    walks = [r for r in rep["walks"] if r["branch"] != "threat"]
    by = {"building": 0, "cluster": 0, "other": 0}
    for r in walks:
        by[r["kind"]] += 1
    d = [r["tiles"] for r in walks if r["tiles"] is not None]
    return {"read": True, "walks": len(walks), "by_kind": by, "farthest": max(d) if d else None,
            "off_building": [r for r in walks if r["kind"] == "other"][:10], "ok": by["other"] == 0}


def e_doors(rep, decision_lines=None):
    """{read, marks [{door, reason, atS, building}], tried_marked, routes_around [building], ok}: the doors the
    planner's own rule marks stuck in the replay (P24-Z), the open or close interacts sent at a door the World had
    marked (`tried_marked`: it is to be routed around), and, with the decision log, the buildings a LootBuilding goal
    was set on after the first mark other than the marked ones. `ok` no door tried while marked. {read: False}
    without a replay."""
    if rep is None:
        return {"read": False}
    marks = rep["marks"]
    around = []
    if marks and decision_lines is not None:
        first = min(m["atMs"] for m in marks) / 1000.0
        stuck = {m["building"] for m in marks}
        for ln in (_d(x) for x in _l(decision_lines)):
            g = _d(ln.get("goal"))
            b = _d(g.get("args")).get("building")
            if g.get("type") == "LootBuilding" and (_n(ln.get("wall")) or 0) >= first and b not in stuck \
                    and b not in around:
                around.append(b)
    return {"read": True, "marks": [{k: m[k] for k in ("door", "reason", "atS", "building")} for m in marks],
            "tried_marked": rep["tried_marked"], "routes_around": around, "ok": rep["tried_marked"] == 0}


def report_lines_e5(g):
    """report_lines_e4's lines (the gate line naming gate_e5), then the pass 5 lines."""
    g = _d(g)
    lines = [("gate_e5 " + l[len("gate_e4 "):]) if l.startswith("gate_e4 ") else l for l in report_lines_e4(g)]
    lines.append("frames: %s (%s frames%s)" % (g.get("frames_source"), g.get("frames_n"),
                                              ", files %s" % g.get("frames_files") if g.get("frames_files") else ""))
    en, ds, dr, lt = (_d(g.get(x)) for x in ("engage", "destinations", "doors", "loot"))
    if en.get("read"):
        lines.append("engage: %s fights, %s sought (%s sought lines); %s seek lines (legs %s, %s walk share); %s "
                     "flee turns to fight; flees %s; many by listed count %s lines (max %s)" % (
                         en.get("fights"), en.get("fights_sought"), en.get("sought_lines"), en.get("seek_lines"),
                         en.get("seek_legs"), _f(en.get("seek_walk_share")), en.get("flee_turns"), en.get("flees"),
                         en.get("many_listed_lines"), en.get("many_listed_max")))
    else:
        lines.append("engage: no decision log read")
    if ds.get("read"):
        lines.append("destinations: %s walks, by kind %s, farthest %s tiles from a known building; %s" % (
            ds.get("walks"), ds.get("by_kind"), _f(ds.get("farthest")), "ok" if ds.get("ok") else "OFF A BUILDING"))
    else:
        lines.append("destinations: no state logs read")
    if dr.get("read"):
        lines.append("doors: %s marked stuck %s, %s tried while marked, loots routed around to buildings %s" % (
            len(dr.get("marks")), [(m["door"], m["reason"]) for m in dr.get("marks")], dr.get("tried_marked"),
            dr.get("routes_around")))
    if lt:
        lines.append("loot: %s sent, %s done, %s failed; by kind %s; failures %s" % (
            lt.get("sent"), lt.get("done"), lt.get("failed"), lt.get("by_kind"), lt.get("failed_reasons")))
    return lines


def grade_e5(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e4 but for grade "grade_e5": its frame fields (`stance_held`'s frames, `wounds`, `glides`, the death
    window, the load ratio) read over every frame of the state files in `state_dir` (or of `lines`, the decoded
    lines) when there are any, else over loop.last_frames; `frames_source` ("state_logs" | "last_frames"),
    `frames_files` and `frames_n` say which. Beside them: `engage` (e_engage, with decision_lines), `destinations`
    and `doors` (off a replay of the lines into a World), `loot` and report_lines (report_lines_e5)."""
    files = []
    if lines is None:
        lines, files = session_lines(state_dir) if state_dir is not None else ([], [])
    frames = session_frames(lines)
    out = _d(out)
    base = out
    if frames:
        base = dict(out, loop=dict(_d(out.get("loop")), last_frames=frames))
    g = grade_e4(base, prev, decision_lines)
    g["grade"] = "grade_e5"
    g["frames_source"] = "state_logs" if frames else "last_frames"
    g["frames_files"] = files if frames else []
    g["frames_n"] = len(frames) if frames else len(_l(_d(out.get("loop")).get("last_frames")))
    g["engage"] = e_engage(decision_lines)
    rep = _replay(out, lines)
    g["destinations"] = e_destinations(rep)
    g["doors"] = e_doors(rep, decision_lines)
    g["loot"] = e_loot(out)
    g["report_lines"] = report_lines_e5(g)
    return g


def gate_e5(outs):
    """gate_e4's gates and kills (grade_e5 changes none of what they read), named gate_e5:
    {verdict, gates, lineage_sources, kills}."""
    return gate_e4(outs)
