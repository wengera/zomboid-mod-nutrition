"""gates_f -- the LLM session grade (Plan 23 Task 15): `grade_f1(out)` is grade_e1 output plus `llm`; `grade_f2(out)`
is grade_e2 output (the death signal, P23-AO) plus the same `llm`.

Reads, besides gates_e keys: out.loop.llm.calls [{latency_s, ok}] and out.loop.goals [{type, state, source}].
llm = {calls, ok (calls with ok true), fallbacks (calls not ok: the runner fell back to the scripted goal),
latency_p50, latency_p99 (nearest rank over latency_s), goals_by_type {type: n}, goal_ends {done, failed,
superseded} (goals by final state)}. A missing key reads as empty; a non-dict artifact reads as empty.

Versioned per pass: once an artifact carries grade_f1 output it is never edited, a later pass is grade_f2."""
from agent.base import gates as GT
from agent.base import gates_e as E

GOAL_ENDS = ("done", "failed", "superseded")


def f_llm(out):
    loop = E._d(E._d(out).get("loop"))
    calls = [E._d(c) for c in E._l(E._d(loop.get("llm")).get("calls"))]
    lat = [E._n(c.get("latency_s")) for c in calls]
    goals = [E._d(x) for x in E._l(loop.get("goals"))]
    by = {}
    for x in goals:
        by[str(x.get("type"))] = by.get(str(x.get("type")), 0) + 1
    return {"calls": len(calls), "ok": sum(1 for c in calls if c.get("ok") is True),
            "fallbacks": sum(1 for c in calls if c.get("ok") is not True),
            "latency_p50": GT.pct(lat, 50), "latency_p99": GT.pct(lat, 99), "goals_by_type": by,
            "goal_ends": {k: sum(1 for x in goals if x.get("state") == k) for k in GOAL_ENDS}}


def _llm_line(g, lines):
    ll = E._d(E._d(g).get("llm"))
    lines.append("llm: %s calls (%s ok, %s fallbacks), latency p50 %s s, p99 %s s; goals %s; ends %s" % (
        ll.get("calls"), ll.get("ok"), ll.get("fallbacks"), E._f(ll.get("latency_p50")), E._f(ll.get("latency_p99")),
        ll.get("goals_by_type"), ll.get("goal_ends")))
    return lines


def report_lines_f(g):
    return _llm_line(g, E.report_lines_e(g))


def report_lines_f2(g):
    """report_lines_e2's lines (gate_e2, the death signal) and the llm line."""
    return _llm_line(g, E.report_lines_e2(g))


def grade_f1(out):
    g = E.grade_e1(out)
    g["grade"] = "grade_f1"
    g["llm"] = f_llm(out)
    g["report_lines"] = report_lines_f(g)
    return g


def grade_f2(out):
    """grade_e2(out) (the death signal, ruling P23-AO) plus the `llm` arm of grade_f1."""
    g = E.grade_e2(out)
    g["grade"] = "grade_f2"
    g["llm"] = f_llm(out)
    g["report_lines"] = report_lines_f2(g)
    return g


def report_lines_f3(g):
    """report_lines_e3's lines (gate_e3, the real wounds, the care) and the llm line."""
    return _llm_line(g, E.report_lines_e3(g))


def grade_f3(out):
    """grade_f2's readings over grade_e3 (Plan 24 Task 11: the real wounds, the care, stance, climb and water-chain
    readings, the need chain's steps in care.need_chain) plus the same `llm` arm. grade_f2 stays as it was."""
    g = E.grade_e3(out)
    g["grade"] = "grade_f3"
    g["llm"] = f_llm(out)
    g["report_lines"] = report_lines_f3(g)
    return g


def report_lines_f4(g):
    """report_lines_e4's lines (the kills headline first, gate_e4, the stance held, the ride, the glides) and the llm line."""
    return _llm_line(g, E.report_lines_e4(g))


def grade_f4(out, prev=None, decision_lines=None):
    """grade_e4's readings (kills the headline, Plan 24 Task 17) plus the same `llm` arm. grade_f3 stays as it was."""
    g = E.grade_e4(out, prev, decision_lines)
    g["grade"] = "grade_f4"
    g["llm"] = f_llm(out)
    g["report_lines"] = report_lines_f4(g)
    return g


# ================================================================ pass 5 (Plan 24 Task 35)
# grade_f5 is grade_e7 (the kills headline, the pull, the hold, the doorway, the window grab) plus the `llm` arm and the
# readings of the model's answers: `answers`, `strategy`, `refusals`, `latency` and `fallback`. The goals log is the
# LLMSource's goals.log rows (`goal_lines`, each carrying the rendered view as its `prompt` and the model's `answer`
# text); without it the readings that need no prompt come off the artifact's own `loop.llm.calls` and the rest read
# `read` false. A reading counts rows; an inference says it reads an effect off what the view showed.
import json                                        # noqa: E402 - appended below the pass 4 code so no line above shifts
import re                                          # noqa: E402
from agent.base.planner.view import WHYS           # noqa: E402

_ABSENT = object()
_BUILDING = re.compile(r"^(\d+) @(-?\d+),(-?\d+) door (\S+) (-?[\d.]+) c(\d+) (\S+)(?: h:(\S+))?(?: z:(\d+))?$")
_BAG = re.compile(r"\"want\"\s*:\s*\"bag\"")


def _view_value(prompt, key):
    """The JSON value of the view's `key: value` line, else _ABSENT (no such line, or a value that does not decode)."""
    for ln in str(prompt).splitlines():
        if ln.startswith(key + ": "):
            try:
                return json.loads(ln[len(key) + 2:])
            except ValueError:
                return _ABSENT
    return _ABSENT


def _view_buildings(prompt):
    """The view's building lines as [{id, dist, flags, z}] in the order shown, else []."""
    for ln in str(prompt).splitlines():
        if ln.startswith("buildings: "):
            out = []
            for part in ln[len("buildings: "):].split("; "):
                m = _BUILDING.match(part.strip())
                if m:
                    out.append({"id": int(m.group(1)), "dist": float(m.group(5)), "flags": m.group(7),
                                "z": int(m.group(9)) if m.group(9) is not None else None})
            return out
    return []


def _goal_of(r):
    return E._d(r.get("goal")) if r.get("ok") is True else {}


def f_answers(rows, read):
    by_type, by_want, bag = {}, {}, 0
    for r in rows:
        g = _goal_of(r)
        if g.get("type") is not None:
            by_type[str(g["type"])] = by_type.get(str(g["type"]), 0) + 1
        if g.get("want") is not None:
            by_want[str(g["want"])] = by_want.get(str(g["want"]), 0) + 1
        if read and r.get("ok") is not True and str(r.get("error")).startswith("invalid") \
                and _BAG.search(str(r.get("answer"))):
            bag += 1
    return {"read": read, "by_type": by_type, "by_want": by_want, "weapon": by_want.get("weapon", 0) if read else None,
            "bag_refused": bag if read else None}


def f_strategy(rows, read):
    sh = {"answers": 0, "tired_or_night": 0, "neither": 0, "unread": 0}
    lo = {"answers": 0, "z0": 0, "zpos_with_z0_shown": 0, "zpos_no_z0_shown": 0, "unread": 0}
    ne = {"answers": 0, "rank0": 0, "ranks": {}, "unranked": 0}
    for r in rows if read else ():
        g = _goal_of(r)
        if g.get("type") == "Shelter":
            sh["answers"] += 1
            night, tired = _view_value(r.get("prompt"), "night"), _view_value(r.get("prompt"), "tired")
            if night is True or tired is True:
                sh["tired_or_night"] += 1
            elif night is False and tired is False:
                sh["neither"] += 1
            else:
                sh["unread"] += 1
        if g.get("type") != "LootBuilding":
            continue
        shown = _view_buildings(r.get("prompt"))
        mine = next((b for b in shown if b["id"] == g.get("building")), None)
        lo["answers"] += 1
        if mine is None or mine["z"] is None:
            lo["unread"] += 1
        elif mine["z"] == 0:
            lo["z0"] += 1
        elif any(b["z"] == 0 for b in shown):
            lo["zpos_with_z0_shown"] += 1
        else:
            lo["zpos_no_z0_shown"] += 1
        ne["answers"] += 1
        open_ = [b for b in shown if "L" not in b["flags"] and "x" not in b["flags"]]
        if mine is None or mine not in open_:
            ne["unranked"] += 1
            continue
        rank = sum(1 for b in open_ if b["dist"] < mine["dist"])
        ne["ranks"][str(rank)] = ne["ranks"].get(str(rank), 0) + 1
        ne["rank0"] += 1 if rank == 0 else 0
    looted = sum(1 for r in rows if r.get("error") == "invalid: looted already")
    return {"read": read, "shelter": sh, "loot": lo, "nearest": ne, "loop": {"looted_already": looted}}


def f_refusals(rows, read):
    by = {w: 0 for w in WHYS}
    other, carried, not_carried, unchecked = 0, 0, 0, 0
    for i, r in enumerate(rows):
        err = str(r.get("error"))
        if not err.startswith("invalid: "):
            continue
        why = err[len("invalid: "):]
        if why not in by:
            other += 1
            continue
        by[why] += 1
        if not read:
            continue
        if i + 1 >= len(rows):
            unchecked += 1
            continue
        last = _view_value(rows[i + 1].get("prompt"), "last_goal")
        if isinstance(last, dict) and last.get("end") == "refused" and last.get("why") == why:
            carried += 1
        else:
            not_carried += 1
    return {"read": read, "by_why": by, "invalid_other": other, "carried": carried, "not_carried": not_carried,
            "unchecked": unchecked}


def f_latency(rows):
    errs = [str(r.get("error")) for r in rows]
    ans = [E._n(r.get("latency_s")) for r, e in zip(rows, errs)
           if e != "timeout" and not e.startswith(("spawn", "exit"))]
    ans = [v for v in ans if v is not None]
    return {"calls": len(rows), "timeouts": errs.count("timeout"), "cli_error": errs.count("cli error"),
            "malformed": errs.count("malformed"), "answered": len(ans),
            "mean": sum(ans) / len(ans) if ans else None, "max": max(ans) if ans else None}


def f_fallback(out, rows):
    goals = [E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("goals"))]
    scripted = sum(1 for x in goals if x.get("source") == "scripted")
    return {"goals": len(goals), "scripted": scripted, "llm": sum(1 for x in goals if x.get("source") == "llm"),
            "share": scripted / len(goals) if goals else None, "calls": len(rows),
            "calls_fallbacks": sum(1 for r in rows if r.get("ok") is not True)}


def f_readings(out, goal_lines=None):
    """The pass 5 readings over the goals log rows `goal_lines`, else over the artifact's calls (the prompt readings
    then read false)."""
    read = goal_lines is not None
    if read:
        rows = [r for r in E._l(goal_lines) if isinstance(r, dict)]
    else:
        rows = [E._d(c) for c in E._l(E._d(E._d(E._d(out).get("loop")).get("llm")).get("calls"))]
    return {"answers": f_answers(rows, read), "strategy": f_strategy(rows, read), "refusals": f_refusals(rows, read),
            "latency": f_latency(rows), "fallback": f_fallback(out, rows)}


def report_lines_f5(g):
    """report_lines_e7's lines, the llm line, then one line per pass 5 reading, each marked reading or inference."""
    lines = _llm_line(g, E.report_lines_e7(g))
    g = E._d(g)
    a, s, rf, lt, fb = (E._d(g.get(k)) for k in ("answers", "strategy", "refusals", "latency", "fallback"))
    sh, lo, ne = (E._d(s.get(k)) for k in ("shelter", "loot", "nearest"))
    if not a.get("read"):
        lines.append("answers, strategy, refusals (pass 5): no goals.log read")
    else:
        lines.append("answers (a): by type %s, by want %s; weapon %s, refused bag %s [reading of goals.log]" % (
            a.get("by_type"), a.get("by_want"), a.get("weapon"), a.get("bag_refused")))
        lines.append("shelter (b): %s answers, %s with tired or night true in the view, %s with both false (the line "
                     "says loot instead), %s unread [inference: the view at the call]" % (
                         sh.get("answers"), sh.get("tired_or_night"), sh.get("neither"), sh.get("unread")))
        lines.append("loot z (b): %s answers, %s of a building reading z:0, %s of z above 0 while a z:0 building was "
                     "shown, %s of z above 0 with none shown, %s unread [inference: the view at the call]" % (
                         lo.get("answers"), lo.get("z0"), lo.get("zpos_with_z0_shown"), lo.get("zpos_no_z0_shown"),
                         lo.get("unread")))
        lines.append("nearest (b): %s loot answers, %s the nearest unlooted shown, ranks %s, %s unranked (looted, "
                     "blocked or not shown) [inference: the view at the call]" % (
                         ne.get("answers"), ne.get("rank0"), ne.get("ranks"), ne.get("unranked")))
        lines.append("refusals (c): by why %s, %s invalid by the goal contract; carried into the next view %s, not "
                     "carried %s, unchecked %s [reading of goals.log]" % (
                         {k: v for k, v in E._d(rf.get("by_why")).items() if v}, rf.get("invalid_other"),
                         rf.get("carried"), rf.get("not_carried"), rf.get("unchecked")))
    lines.append("loop (b): looted already %s answers named a building looted already [reading]" % (
        E._d(s.get("loop")).get("looted_already")))
    lines.append("latency (d): %s calls, %s answered, mean %s s, max %s s; timeouts %s, cli error %s, malformed %s "
                 "[reading]" % (lt.get("calls"), lt.get("answered"), E._f(lt.get("mean")), E._f(lt.get("max")),
                                lt.get("timeouts"), lt.get("cli_error"), lt.get("malformed")))
    lines.append("fallback (f): %s of %s goals scripted (share %s); %s of %s calls fell back [reading]" % (
        fb.get("scripted"), fb.get("goals"), E._f(fb.get("share")), fb.get("calls_fallbacks"), fb.get("calls")))
    return lines


def grade_f5(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_e7's readings (the kills headline, the pull, the hold, the doorway, the window grab) plus the `llm` arm of
    grade_f4 and the pass 5 readings of the model's answers. grade_f4 stays as it was."""
    g = E.grade_e7(out, prev, decision_lines, state_dir, lines)
    g["grade"] = "grade_f5"
    g["llm"] = f_llm(out)
    g.update(f_readings(out, goal_lines))
    g["report_lines"] = report_lines_f5(g)
    return g


def gate_f5(outs):
    """gate_e7's gates and kills (grade_f5 changes none of what they read), named gate_f5."""
    return E.gate_e7(outs)
