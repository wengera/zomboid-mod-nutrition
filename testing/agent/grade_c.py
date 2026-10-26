"""Stage C's grade (spec § 4.3): a report, never a gate. `grade_c(out)` reads a c_survive or c_survive_dense artifact
and returns what the session showed, with no pass/fail: how long the character lived and why the session stopped, its
needs over time (the client frame beside the server reading), decisions per minute, the fights and their outcomes, the
death with its last ten decisions, the per-tick cost over the session, the lua_error count and a histogram of every
goal's outcome. `report_lines` are one-line findings a reviewer can quote.

A reading the artifact lacks is None (or empty), never a guess. Details with a numeric tail ("d=0.4", "moved=2") are
counted under their prefix (agent.reasons.DONE), so the histogram stays small.
"""
import math

from agent.reasons import DONE

SURVIVED = ("day_cap", "budget")     # the stops a character lived through: the session ended, the character did not
NEEDS_FIELDS = ("gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger")
PREFIXES = tuple(d for d in DONE if d.endswith("="))


def pct(values, p):
    """Nearest-rank percentile: the smallest value with at least p % of the values at or below it; None when empty."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    rank = max(1, math.ceil(p / 100.0 * len(vals)))
    return vals[min(rank, len(vals)) - 1]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _d(v):
    return v if isinstance(v, dict) else {}


def _l(v):
    return v if isinstance(v, list) else []


def detail_key(detail):
    d = "" if detail is None else str(detail)
    for p in PREFIXES:
        if d.startswith(p):
            return p
    return d


def goal_histogram(raw):
    """{goal: {state: {detail: n}}} with numeric-tail details folded under their prefix."""
    out = {}
    for goal, states in _d(raw).items():
        for state, details in _d(states).items():
            for detail, n in _d(details).items():
                k = detail_key(detail)
                d = out.setdefault(goal, {}).setdefault(state, {})
                d[k] = d.get(k, 0) + (_num(n) or 0)
    return out


def needs_summary(rows):
    """The needs series' first and last rows by field, and the largest |client hunger - server hunger| a row shows."""
    rows = [r for r in _l(rows) if isinstance(r, list) and len(r) == len(NEEDS_FIELDS)]
    diffs = [abs(r[1] - r[5]) for r in rows if _num(r[1]) is not None and _num(r[5]) is not None]
    first = dict(zip(NEEDS_FIELDS, rows[0])) if rows else None
    last = dict(zip(NEEDS_FIELDS, rows[-1])) if rows else None
    peak = {f: max((r[i] for r in rows if _num(r[i]) is not None), default=None)
            for i, f in enumerate(NEEDS_FIELDS) if f in ("hunger", "thirst", "fatigue")}
    low_health = min((r[4] for r in rows if _num(r[4]) is not None), default=None)
    return {"rows": len(rows), "first": first, "last": last, "peak": peak, "min_health": low_health,
            "hunger_client_server_max_diff": max(diffs) if diffs else None, "paired_rows": len(diffs)}


def fights_summary(fights):
    fights = [f for f in _l(fights) if isinstance(f, dict)]
    outcomes = {}
    for f in fights:
        e = f.get("end") if isinstance(f.get("end"), dict) else None
        k = "open" if e is None else "%s:%s" % (e.get("state"), detail_key(e.get("detail")))
        outcomes[k] = outcomes.get(k, 0) + 1
    return {"count": len(fights), "outcomes": outcomes}


def survived_of(reason):
    """True for a stop the character lived through (SURVIVED), False for a death, None for any other stop or none:
    a dead bus, a storm, memory or an error ended the session before the answer was known."""
    if reason in SURVIVED:
        return True
    if reason == "death":
        return False
    return None


def outcome_of(reason):
    if reason is None:
        return "no stop recorded"
    if reason in SURVIVED:
        return "survived (%s)" % reason
    if reason == "death":
        return "died"
    return "undecided: the session stopped on %s" % reason


def grade_c(out):
    out = _d(out)
    loop = _d(out.get("loop"))
    stop = _d(out.get("stop"))
    reason = stop.get("reason")
    wall_s = _num(loop.get("wallS"))
    stop_s = _num(stop.get("wallS"))
    survival_s = stop_s if stop_s is not None else wall_s
    decisions, ticks = _num(loop.get("decisions")), _num(loop.get("ticks"))
    minutes = survival_s / 60.0 if survival_s else None
    cost = _d(loop.get("cost"))
    death = _d(loop.get("death"))
    deaths = []
    if reason == "death" or death:
        deaths.append({"via": death.get("via"), "detail": death.get("detail", stop.get("detail")),
                       "wallS": death.get("wallS", stop_s), "gameMin": death.get("gameMin", stop.get("gameMin")),
                       "last_decisions": _l(death.get("last_decisions"))})
    per_min = _d(loop.get("lua_errors_per_min"))
    g = {
        "session_key": out.get("session_key"),
        "run_id": out.get("run_id"),
        "finished": out.get("finished") is True,
        "stop": {"reason": reason, "detail": stop.get("detail"), "gameMin": stop.get("gameMin")} if stop else None,
        "survived": survived_of(reason),
        "outcome": outcome_of(reason),
        "survival_s": survival_s,
        "start_kit_armed": _d(_d(out.get("readings")).get("start_kit")).get("armed"),
        "needs": _l(loop.get("needs")),
        "needs_fields": list(NEEDS_FIELDS),
        "needs_summary": needs_summary(loop.get("needs")),
        "ticks": ticks,
        "decisions": decisions,
        "decisions_per_min": decisions / minutes if decisions is not None and minutes else None,
        "ticks_per_min": ticks / minutes if ticks is not None and minutes else None,
        "fights": fights_summary(loop.get("fights")),
        "deaths": deaths,
        "last_decisions": _l(loop.get("last_decisions")),
        "cost_n": _num(cost.get("n")),
        "cost_p50": _num(cost.get("p50")),
        "cost_p99": _num(cost.get("p99")),
        "cost_max": _num(cost.get("max")),
        "lua_errors": _num(out.get("lua_errors")),
        "lua_errors_max_per_min": max((_num(v) or 0 for v in per_min.values()), default=0) if per_min else 0,
        "client_lua_errors": _num(out.get("client_lua_errors")),
        "goal_outcomes": goal_histogram(loop.get("goal_outcomes")),
        "server_polls": _num(loop.get("server_polls")),
        "server_fails": _num(loop.get("server_fails")),
    }
    g["report_lines"] = report_lines(g)
    return g


def _fmt(v, f="%.2f"):
    return "n/a" if v is None else f % v


def report_lines(g):
    lines = []
    st = g["stop"] or {}
    if g["survival_s"] is None:
        lines.append("no loop ran: stop %s (%s)" % (st.get("reason"), st.get("detail")))
    else:
        lines.append("%s after %.0f s of the loop (%.1f wall min), stop %s: %s" % (
            g["outcome"], g["survival_s"], g["survival_s"] / 60.0, st.get("reason"), st.get("detail")))
    if g["start_kit_armed"] is not None:
        lines.append("start kit %s" % ("equipped (a frame showed the bat in hand)" if g["start_kit_armed"]
                                       else "not seen in hand: the policy flees every threat unarmed"))
    lines.append("%s decisions sent over %s planner ticks (%s per min)" % (
        _fmt(g["decisions"], "%d"), _fmt(g["ticks"], "%d"), _fmt(g["decisions_per_min"], "%.1f")))
    ns = g["needs_summary"]
    if ns["rows"]:
        lines.append("needs: %d rows; peak hunger %s, thirst %s, fatigue %s; min health %s; client-server hunger "
                     "max diff %s over %d paired rows" % (
                         ns["rows"], _fmt(ns["peak"]["hunger"]), _fmt(ns["peak"]["thirst"]),
                         _fmt(ns["peak"]["fatigue"]), _fmt(ns["min_health"], "%.1f"),
                         _fmt(ns["hunger_client_server_max_diff"], "%.3f"), ns["paired_rows"]))
    fs = g["fights"]
    lines.append("fights: %d %s" % (fs["count"], ", ".join("%s x%d" % (k, n) for k, n in sorted(fs["outcomes"].items()))))
    for d in g["deaths"]:
        last = d["last_decisions"][-1] if d["last_decisions"] else {}
        lines.append("death via %s at game minute %s; the last decision: %s %s (branch %s)" % (
            d["via"], d["gameMin"], last.get("goal"), last.get("args"), last.get("branch")))
    lines.append("per-tick cost p50 %s ms, p99 %s ms, max %s ms over %s frames" % (
        _fmt(g["cost_p50"], "%.3f"), _fmt(g["cost_p99"], "%.3f"), _fmt(g["cost_max"], "%.3f"), _fmt(g["cost_n"], "%d")))
    lines.append("lua_error events %s (max %s in a minute); client console Lua errors %s" % (
        _fmt(g["lua_errors"], "%d"), g["lua_errors_max_per_min"], _fmt(g["client_lua_errors"], "%d")))
    for goal, states in sorted(g["goal_outcomes"].items()):
        parts = []
        for state, details in sorted(states.items()):
            n = sum(details.values())
            top = sorted(details.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            parts.append("%s %d (%s)" % (state, n, ", ".join("%s x%d" % (k or "-", v) for k, v in top)))
        lines.append("goal %s: %s" % (goal, "; ".join(parts)))
    return lines
