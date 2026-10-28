"""gates_f -- the LLM session grade (Plan 23 Task 15): `grade_f1(out)` is grade_e1 output plus `llm`.

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


def report_lines_f(g):
    lines = E.report_lines_e(g)
    ll = E._d(E._d(g).get("llm"))
    lines.append("llm: %s calls (%s ok, %s fallbacks), latency p50 %s s, p99 %s s; goals %s; ends %s" % (
        ll.get("calls"), ll.get("ok"), ll.get("fallbacks"), E._f(ll.get("latency_p50")), E._f(ll.get("latency_p99")),
        ll.get("goals_by_type"), ll.get("goal_ends")))
    return lines


def grade_f1(out):
    g = E.grade_e1(out)
    g["grade"] = "grade_f1"
    g["llm"] = f_llm(out)
    g["report_lines"] = report_lines_f(g)
    return g
