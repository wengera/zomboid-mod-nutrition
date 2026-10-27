"""The agent base's live gates (Plan 22, spec § 10), each versioned and graded off a driver's artifact dict.

THE SIDECAR TRIGGER (spec § 8 (6)), stated here before X4 runs:
  X4 fires it when the link's emit reads above 1 ms mean (SIDECAR_MEAN_MS = 1.0) or 3 ms worst (SIDECAR_WORST_MS = 3.0)
  per flushing tick: the mean and max of cost.linkMs over the frames whose linkMs > 0; fired builds the sidecar.

`gate_x4(out)` grades `testing/agent/drivers/x4_link.py`'s artifact (X4, "the link"). Each graded gate is `{ok, value,
threshold, n}`; a reading the artifact lacks fails its gate with `value None`; `verdict` is GO when every graded gate
is ok. The gates and the paths they read:

  tick_mean_at60  readings.rate60.tickMs (each 60 Hz frame's cost.tickMs): the mean < TICK_MEAN_MS (1 ms) over at least
                  RATE60_MIN_FRAMES (1620, 90 % of 30 s at 60 Hz) frames.
  worst_tick      frames.cost (every frame's {seq, tick, wallMs, cost}): the max cost.tickMaxMs <= WORST_TICK_MS (3 ms,
                  ruling P22-4, the 1 ms clock) and the sum of cost.over5 == 0, over frames whose wallMs span at least
                  WORST_SPAN_S (600 s).
  gaps            frames.gaps (the transport's seq gaps) == 0.
  lua_errors      frames.lua_errors (the lua_error events on the link) == 0.
  parks           frames.parks (the client parked in the debugger) == 0.
  cmd_move_p90    readings.walk.legs: per leg first_move.wallMs - accepted_wallMs (both the client's clock; a leg
                  without first_move or accepted_wallMs is +inf), the nearest-rank p90 < MOVE_P90_MS (500 ms) over at
                  least MIN_LEGS (20) legs.
  map_kept        readings.final_scan.kept: walls, doors, windows and containers each `ratio` >= MAP_KEPT_MIN
                  (0.99); the ratio is fidelity, kept / (total - absent) over the squares both the kept map and the
                  final scan saw; `absent` (a final square no full scan ever sent: coverage) is reported for the
                  guide, never graded.

Ungraded beside the verdict: `sidecar_trigger` ("fired", "not fired", or "unmeasured" with no flushing frame),
`emit_mean_ms` and `emit_worst_ms`.

FROZEN once X4's artifact carries its output (CLAUDE.md § 5 "Freezing"): `gate_x4` is never edited after Task 12's
run; a later pass is `gate_x4_2`, a new function beside it.
"""
import math

TICK_MEAN_MS = 1.0
RATE60_MIN_FRAMES = 1620
WORST_TICK_MS = 3.0
WORST_SPAN_S = 600.0
MOVE_P90_MS = 500.0
MIN_LEGS = 20
MAP_KEPT_MIN = 0.99
MAP_KINDS = ("walls", "doors", "windows", "containers")
SIDECAR_MEAN_MS = 1.0
SIDECAR_WORST_MS = 3.0
GRADED = ("tick_mean_at60", "worst_tick", "gaps", "lua_errors", "parks", "cmd_move_p90", "map_kept")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def pct(values, p):
    """Nearest-rank percentile: the smallest value with at least p % of the values at or below it; None when empty."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    rank = max(1, math.ceil(p / 100.0 * len(vals)))
    return vals[min(rank, len(vals)) - 1]


def _gate(ok, value, threshold, n):
    return {"ok": bool(ok), "value": value, "threshold": threshold, "n": n}


def _readings(out, phase):
    r = (out.get("readings") or {}).get(phase)
    return r if isinstance(r, dict) else None


def _cost_rows(out):
    rows = (out.get("frames") or {}).get("cost")
    return rows if isinstance(rows, list) else None


def _cost(row, key):
    c = row.get("cost") if isinstance(row, dict) else None
    return _num(c.get(key)) if isinstance(c, dict) else None


def tick_mean_at60(out):
    th = "mean < %s ms over >= %d frames" % (TICK_MEAN_MS, RATE60_MIN_FRAMES)
    r = _readings(out, "rate60")
    vals = r.get("tickMs") if r else None
    if not isinstance(vals, list):
        return _gate(False, None, th, 0)
    vals = [_num(v) for v in vals]
    vals = [v for v in vals if v is not None]
    if not vals:
        return _gate(False, None, th, 0)
    mean = sum(vals) / len(vals)
    return _gate(mean < TICK_MEAN_MS and len(vals) >= RATE60_MIN_FRAMES, mean, th, len(vals))


def worst_tick(out):
    th = "max tickMaxMs <= %s ms and 0 over5, over >= %s s" % (WORST_TICK_MS, WORST_SPAN_S)
    rows = _cost_rows(out)
    if not rows:
        return _gate(False, None, th, 0)
    tops = [_cost(r, "tickMaxMs") for r in rows]
    tops = [v for v in tops if v is not None]
    overs = [_cost(r, "over5") for r in rows]
    overs = [v for v in overs if v is not None]
    walls = [_num(r.get("wallMs")) for r in rows if isinstance(r, dict) and r.get("cost") is not None]
    walls = [w for w in walls if w is not None]
    if not tops or not overs or len(walls) < 2:
        return _gate(False, None, th, len(tops))
    value = {"tickMaxMs": max(tops), "over5": sum(overs), "span_s": (max(walls) - min(walls)) / 1000.0}
    ok = value["tickMaxMs"] <= WORST_TICK_MS and value["over5"] == 0 and value["span_s"] >= WORST_SPAN_S
    return _gate(ok, value, th, len(tops))


def _count_gate(out, key):
    v = _num((out.get("frames") or {}).get(key))
    return _gate(v == 0, v, "== 0", 1 if v is not None else 0)


def leg_move_ms(legs):
    """Per leg: first_move.wallMs - accepted_wallMs (the client's clock); +inf for a leg missing either."""
    vals = []
    for leg in legs or ():
        leg = leg if isinstance(leg, dict) else {}
        a = _num(leg.get("accepted_wallMs"))
        m = _num((leg.get("first_move") or {}).get("wallMs"))
        vals.append(m - a if a is not None and m is not None else math.inf)
    return vals


def cmd_move_p90(out):
    th = "p90 < %s ms over >= %d legs" % (MOVE_P90_MS, MIN_LEGS)
    r = _readings(out, "walk")
    legs = r.get("legs") if r else None
    if not isinstance(legs, list) or not legs:
        return _gate(False, None, th, 0)
    p90 = pct(leg_move_ms(legs), 90)
    return _gate(p90 < MOVE_P90_MS and len(legs) >= MIN_LEGS, p90, th, len(legs))


def map_kept(out):
    th = "each of %s ratio >= %s" % ("/".join(MAP_KINDS), MAP_KEPT_MIN)
    r = _readings(out, "final_scan")
    kept = r.get("kept") if r else None
    if not isinstance(kept, dict):
        return _gate(False, None, th, 0)
    value = {k: _num((kept.get(k) or {}).get("ratio")) for k in MAP_KINDS}
    n = sum(_num((kept.get(k) or {}).get("total")) or 0 for k in MAP_KINDS)
    ok = all(v is not None and v >= MAP_KEPT_MIN for v in value.values())
    return _gate(ok, value, th, n)


def sidecar(out):
    """The sidecar trigger (the module docstring): (trigger, emit_mean_ms, emit_worst_ms, n flushing frames)."""
    links = [_cost(r, "linkMs") for r in _cost_rows(out) or ()]
    links = [v for v in links if v is not None and v > 0]
    if not links:
        return "unmeasured", None, None, 0
    mean, worst = sum(links) / len(links), max(links)
    fired = mean > SIDECAR_MEAN_MS or worst > SIDECAR_WORST_MS
    return ("fired" if fired else "not fired"), mean, worst, len(links)


def gate_x4(out):
    """X4's go/no-go (the module docstring); frozen once X4's artifact carries it."""
    gates = {"tick_mean_at60": tick_mean_at60(out), "worst_tick": worst_tick(out),
             "gaps": _count_gate(out, "gaps"), "lua_errors": _count_gate(out, "lua_errors"),
             "parks": _count_gate(out, "parks"), "cmd_move_p90": cmd_move_p90(out), "map_kept": map_kept(out)}
    trigger, mean, worst, n = sidecar(out)
    return {"gate": "gate_x4", "gates": gates, "pass": {k: g["ok"] for k, g in gates.items()},
            "verdict": "GO" if all(g["ok"] for g in gates.values()) else "NO-GO",
            "sidecar_trigger": trigger, "emit_mean_ms": mean, "emit_worst_ms": worst, "emit_frames": n,
            "sidecar_thresholds": {"mean_ms": SIDECAR_MEAN_MS, "worst_ms": SIDECAR_WORST_MS}}


# ================================================================ X5: a measurement, no gate
AGREE_TOL = 0.5      # a zombie's health: the client's copy agrees with the server's within this


def _share(k, n):
    return k / n if n else None


def measure_x5(out):
    """X5's report (spec § 10: a measurement with pass lines, no gate; no verdict), off
    `testing/agent/drivers/x5_combat.py`'s artifact, readings.encounters.rows (a voided encounter's row has no swings):

      attack_started_share     over the swings (attack actions) ended `done`: {share, started, n}, `started` those whose
                               result.attackStarted is true.
      melee_delay              {min, p50, max, n} over the done swings' numeric result.meleeDelay (p50 nearest-rank).
      client_server_agreement  over the swings whose pair_void is false: {share, agree, n, voided, tol}, `agree` those
                               with |pair_after.client_health - pair_after.server_health| <= AGREE_TOL (the client's
                               copy of the zombie's health in the frame nearest the server's read, within the
                               driver's PAIR_SLACK_S); `voided` the swings whose pair_void is not false.
      loop_ms                  {p50, p90, n} over the encounters' loop_ms, raw: the first action's accept minus the
                               first sight (the client's clock). When the first action is an attack it holds the
                               driver's synchronous zombie.get before the send (that swing's pre_read_ms).
      loop_ms_net              {p50, p90, n}: loop_ms minus the first swing's pre_read_ms when the first action was
                               that swing (its loop_ms is set), else loop_ms: the agent's own loop, sight to accept.
      kills                    {n, per_encounter [killed, None for a voided encounter]}.
      health_lost              per encounter: body.health at the first sight minus at the end.
      server_tags              per encounter: the server's damage.watch per-tag rise.
      encounters               {n, voided}; stop: the driver's out["stop"].
    """
    rows = ((out.get("readings") or {}).get("encounters") or {}).get("rows")
    rows = [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    swings = [s for r in rows if not r.get("void") for s in r.get("swings") or () if isinstance(s, dict)]
    done = [s for s in swings if s.get("state") == "done"]
    started = sum(1 for s in done if isinstance(s.get("result"), dict) and s["result"].get("attackStarted") is True)
    delays = [_num(s["result"].get("meleeDelay")) for s in done if isinstance(s.get("result"), dict)]
    delays = sorted(d for d in delays if d is not None)
    kept = [s.get("pair_after") or {} for s in swings if s.get("pair_void") is False]
    diffs = [(_num(p.get("client_health")), _num(p.get("server_health"))) for p in kept]
    agree = sum(1 for c, s in diffs if c is not None and s is not None and abs(c - s) <= AGREE_TOL)
    loops, nets = [], []
    for r in rows:
        v = _num(r.get("loop_ms"))
        if r.get("void") or v is None:
            continue
        first = next((s for s in r.get("swings") or () if isinstance(s, dict)), None)
        pre = _num(first.get("pre_read_ms")) if first and _num(first.get("loop_ms")) is not None else 0
        loops.append(v)
        nets.append(v - (pre or 0))
    return {
        "measure": "measure_x5",
        "attack_started_share": {"share": _share(started, len(done)), "started": started, "n": len(done)},
        "melee_delay": {"min": delays[0] if delays else None, "p50": pct(delays, 50),
                        "max": delays[-1] if delays else None, "n": len(delays)},
        "client_server_agreement": {"share": _share(agree, len(kept)), "agree": agree, "n": len(kept),
                                    "voided": len(swings) - len(kept), "tol": AGREE_TOL},
        "loop_ms": {"p50": pct(loops, 50), "p90": pct(loops, 90), "n": len(loops)},
        "loop_ms_net": {"p50": pct(nets, 50), "p90": pct(nets, 90), "n": len(nets)},
        "kills": {"n": sum(1 for r in rows if r.get("killed") is True),
                  "per_encounter": [None if r.get("void") else r.get("killed") for r in rows]},
        "health_lost": [r.get("health_lost") for r in rows],
        "server_tags": [r.get("server_tags") for r in rows],
        "encounters": {"n": len(rows), "voided": sum(1 for r in rows if r.get("void"))},
        "stop": out.get("stop"),
    }


# ================================================================ D: the survival acceptance, a report and no gate
SURVIVED = ("day_cap", "budget")     # grade_c.py L13: the stops a character lived through
DEATH_TOL = 0.10                     # the brief: the frames' health fall within 10 % of the server's damage amounts
D_NEEDS_FIELDS = ("gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger")


def _dd(v):
    return v if isinstance(v, dict) else {}


def _ll(v):
    return v if isinstance(v, list) else []


def survived_of(reason):
    """grade_c.py's survived_of (L87-L95), copied: True for a stop the character lived through (SURVIVED), False for a
    death, None for any other stop or none (the session ended before the answer was known)."""
    if reason in SURVIVED:
        return True
    if reason == "death":
        return False
    return None


def outcome_of(reason):
    """grade_c.py's outcome_of (L98-L105), copied."""
    if reason is None:
        return "no stop recorded"
    if reason in SURVIVED:
        return "survived (%s)" % reason
    if reason == "death":
        return "died"
    return "undecided: the session stopped on %s" % reason


def d_needs_summary(rows, pairs):
    """grade_c.py's needs_summary (L67-L78) over d_survive's needs, the client-server hunger difference read only over
    the rows whose needs_pairs entry is paired (the frame and the server read in the same wall second)."""
    rows, pairs = _ll(rows), _ll(pairs)
    ok = [r for r in rows if isinstance(r, list) and len(r) == len(D_NEEDS_FIELDS)]
    paired = [r for r, p in zip(rows, pairs) if isinstance(r, list) and len(r) == len(D_NEEDS_FIELDS)
              and _dd(p).get("paired") is True and _num(r[1]) is not None and _num(r[5]) is not None]
    diffs = [abs(r[1] - r[5]) for r in paired]
    peak = {f: max((r[i] for r in ok if _num(r[i]) is not None), default=None)
            for i, f in enumerate(D_NEEDS_FIELDS) if f in ("hunger", "thirst", "fatigue")}
    return {"rows": len(ok), "first": dict(zip(D_NEEDS_FIELDS, ok[0])) if ok else None,
            "last": dict(zip(D_NEEDS_FIELDS, ok[-1])) if ok else None, "peak": peak,
            "min_health": min((r[4] for r in ok if _num(r[4]) is not None), default=None),
            "hunger_client_server_max_diff": max(diffs) if diffs else None, "paired_rows": len(diffs),
            "unpaired_rows": sum(1 for p in pairs if _dd(p).get("paired") is not True)}


def d_actions(rows):
    """{type: {state: n}} over the planner's sends, and {type: {reason: n}} over those ended failed, rejected or
    timeout."""
    rows = [a for a in _ll(rows) if isinstance(a, dict)]
    by, why = {}, {}
    for a in rows:
        t, s = str(a.get("type")), str(a.get("state"))
        d = by.setdefault(t, {})
        d[s] = d.get(s, 0) + 1
        if s in ("failed", "rejected", "timeout"):
            r, w = str(a.get("reason") or ""), why.setdefault(t, {})
            w[r] = w.get(r, 0) + 1
    return {"n": len(rows), "by_type": by, "failed_reasons": why}


def d_fights(rows):
    """The fights off the decision log's threat branch: their count, how many fought (a fight tick seen) or fled (a
    flee tick seen), how many are still open, the health each lost while it ran (None for an open one), and the flee
    reasons summed."""
    rows = [f for f in _ll(rows) if isinstance(f, dict)]
    lost, flee = [], {}
    for f in rows:
        h0, h1 = _num(f.get("health")), _num(_dd(f.get("end")).get("health"))
        lost.append(h0 - h1 if h0 is not None and h1 is not None else None)
        for k, n in _dd(f.get("flee")).items():
            flee[k] = flee.get(k, 0) + (_num(n) or 0)
    return {"count": len(rows), "fought": sum(1 for f in rows if (_num(f.get("fight_ticks")) or 0) > 0),
            "fled": sum(1 for f in rows if _dd(f.get("flee"))), "open": sum(1 for f in rows if f.get("end") is None),
            "health_lost": lost, "flee_reasons": flee}


def death_check(death):
    """Whether the frames explain a death (spec § 10): the health fall over the death record's last_frames (the sum of
    every drop in body.health between consecutive frames) against the sum of the server's damage `amount`s whose
    server `wall` lies in the same window, (the first frame's wallMs, the last frame's wallMs] (a record at the first
    frame's time already shows in it). Explained when the window holds server records and |fall - amount| <=
    DEATH_TOL * amount; not explained otherwise, `why` naming the reason."""
    death = _dd(death)
    hs = [(_num(f.get("wallMs")), _num(_dd(f.get("body")).get("health")))
          for f in _ll(death.get("last_frames")) if isinstance(f, dict)]
    hs = [(w, h) for w, h in hs if w is not None and h is not None]
    r = {"explained": False, "why": None, "tol": DEATH_TOL, "frames_n": len(hs), "frames_window_ms": None,
         "health_fall": None, "server_window_ms": None, "server_n": 0, "server_amount": None, "server_tags": {},
         "diff": None}
    if len(hs) < 2:
        r["why"] = "fewer than two frames with a wallMs and a body.health"
        return r
    lo, hi = hs[0][0], hs[-1][0]
    r["frames_window_ms"] = {"from": lo, "to": hi}
    r["server_window_ms"] = {"from": lo, "to": hi, "rule": "from < wall <= to"}
    r["health_fall"] = sum(max(0.0, a[1] - b[1]) for a, b in zip(hs, hs[1:]))
    recs = [d for d in _ll(death.get("server_damage")) if isinstance(d, dict) and _num(d.get("wall")) is not None
            and lo < d["wall"] <= hi and _num(d.get("amount")) is not None]
    r["server_n"] = len(recs)
    for d in recs:
        t = str(d.get("tag"))
        r["server_tags"][t] = r["server_tags"].get(t, 0.0) + d["amount"]
    if not recs:
        r["why"] = "no server damage record in the frames' window"
        return r
    amount = sum(d["amount"] for d in recs)
    r["server_amount"], r["diff"] = amount, r["health_fall"] - amount
    if amount <= 0:
        r["why"] = "the server's records in the window sum to %s" % amount
        return r
    r["explained"] = abs(r["diff"]) <= DEATH_TOL * amount
    if not r["explained"]:
        r["why"] = "the fall %s and the server's %s differ by more than %s of it" % (r["health_fall"], amount,
                                                                                     DEATH_TOL)
    return r


def grade_d(out):
    """The survival acceptance's report (spec § 10; no gate, no verdict), off `testing/agent/drivers/d_survive.py`'s
    artifact, in grade_c's shape (testing/agent/grade_c.py L113-L160):

      survived, outcome, stop, survival_s  the stop (out["stop"]) and the loop's wall seconds at it.
      game_minutes                         the stop's gameMin minus the session's first frame's (loop.first_game_min).
      start_kit_armed                      readings.kit.armed (a frame showed the bat in hand).
      actions                              {n, by_type {type: {state: n}}, failed_reasons} over loop.actions (the
                                           planner's sends with their ends).
      needs, needs_summary                 the needs series [gameMin, hunger, thirst, fatigue, health, serverHunger]
                                           and its summary, the client-server hunger difference over paired rows.
      fights                               the decision log's threat-branch runs (loop.fights).
      health_lost_by_source                the server's damage.watch records merged over the loop, by tag
                                           (loop.damage.totals {tag: {n, amount}}), the server's own counts beside.
      deaths                               the death record's via, detail, gameMin and last decisions.
      death_explained, death_check         None without a death record; else death_check's verdict and numbers: the
                                           frames' window and health fall, the server's window, record count and
                                           amount, the difference and the tolerance.
      cost, lua_errors, parks, gaps        the frames' tick cost and the link's counters.
    `report_lines` are one-line findings a reviewer can quote."""
    out = _dd(out)
    loop = _dd(out.get("loop"))
    stop = _dd(out.get("stop"))
    reason = stop.get("reason")
    survival_s = _num(stop.get("wallS"))
    survival_s = survival_s if survival_s is not None else _num(loop.get("wallS"))
    g0, g1 = _num(loop.get("first_game_min")), _num(stop.get("gameMin"))
    death = _dd(loop.get("death"))
    deaths = []
    if reason == "death" or death:
        deaths.append({"via": death.get("via"), "detail": death.get("detail", stop.get("detail")),
                       "wallS": death.get("wallS", survival_s), "gameMin": death.get("gameMin", stop.get("gameMin")),
                       "last_decisions": _ll(death.get("last_decisions"))})
    check = death_check(death) if death else None
    dmg = _dd(loop.get("damage"))
    frames = _dd(out.get("frames"))
    cost = _dd(loop.get("cost"))
    per_min = _dd(loop.get("lua_errors_per_min"))
    g = {
        "grade": "grade_d",
        "session_key": out.get("session_key"),
        "run_id": out.get("run_id"),
        "finished": out.get("finished") is True,
        "stop": {"reason": reason, "detail": stop.get("detail"), "gameMin": stop.get("gameMin")} if stop else None,
        "survived": survived_of(reason),
        "outcome": outcome_of(reason),
        "survival_s": survival_s,
        "game_minutes": g1 - g0 if g0 is not None and g1 is not None else None,
        "start_kit_armed": _dd(_dd(out.get("readings")).get("kit")).get("armed"),
        "ticks": _num(loop.get("ticks")),
        "decisions": _num(loop.get("decisions")),
        "actions": d_actions(loop.get("actions")),
        "needs": _ll(loop.get("needs")),
        "needs_fields": list(D_NEEDS_FIELDS),
        "needs_summary": d_needs_summary(loop.get("needs"), loop.get("needs_pairs")),
        "fights": d_fights(loop.get("fights")),
        "health_lost_by_source": {str(k): dict(_dd(v)) for k, v in sorted(_dd(dmg.get("totals")).items())},
        "damage_counts_server": dmg.get("counts"),
        "damage_polls": {k: dmg.get(k) for k in ("polls", "fails", "merged", "lost", "dropped")},
        "deaths": deaths,
        "death_explained": check["explained"] if check is not None else None,
        "death_check": check,
        "cost": {k: cost.get(k) for k in ("n", "p50", "p99", "max", "tickMaxMs", "over5")},
        "lua_errors": _num(frames.get("lua_errors")),
        "lua_errors_max_per_min": max((_num(v) or 0 for v in per_min.values()), default=0),
        "parks": _num(frames.get("parks")),
        "gaps": _num(frames.get("gaps")),
        "server_polls": _num(loop.get("server_polls")),
        "server_fails": _num(loop.get("server_fails")),
    }
    g["report_lines"] = report_lines_d(g)
    return g


def _fmt(v, f="%.2f"):
    return "n/a" if _num(v) is None else f % v


def report_lines_d(g):
    """grade_d's one-line findings (grade_c.py's report_lines, L167-L196, on the new fields)."""
    lines = []
    st = g.get("stop") or {}
    if g.get("survival_s") is None:
        lines.append("no loop ran: stop %s (%s)" % (st.get("reason"), st.get("detail")))
    else:
        lines.append("%s after %.0f s of the loop (%.1f wall min, %s game min), stop %s: %s" % (
            g["outcome"], g["survival_s"], g["survival_s"] / 60.0, _fmt(g.get("game_minutes"), "%.0f"),
            st.get("reason"), st.get("detail")))
    if g.get("start_kit_armed") is not None:
        lines.append("start kit %s" % ("equipped (a frame showed the bat in hand)" if g["start_kit_armed"]
                                       else "not seen in hand: the planner flees every threat unarmed"))
    acts = g["actions"]
    per = "; ".join("%s %s" % (t, ", ".join("%s %d" % (s, n) for s, n in sorted(d.items())))
                    for t, d in sorted(acts["by_type"].items()))
    lines.append("%d actions sent over %s planner ticks: %s" % (acts["n"], _fmt(g.get("ticks"), "%d"), per or "none"))
    ns = g["needs_summary"]
    if ns["rows"]:
        lines.append("needs: %d rows; peak hunger %s, thirst %s, fatigue %s; min health %s; client-server hunger "
                     "max diff %s over %d paired rows (%d unpaired)" % (
                         ns["rows"], _fmt(ns["peak"]["hunger"]), _fmt(ns["peak"]["thirst"]),
                         _fmt(ns["peak"]["fatigue"]), _fmt(ns["min_health"], "%.1f"),
                         _fmt(ns["hunger_client_server_max_diff"], "%.3f"), ns["paired_rows"], ns["unpaired_rows"]))
    fs = g["fights"]
    lines.append("fights: %d (fought %d, fled %d, open %d); flee reasons %s" % (
        fs["count"], fs["fought"], fs["fled"], fs["open"], fs["flee_reasons"] or "none"))
    hl = g["health_lost_by_source"]
    lines.append("health lost by source (the server's damage.watch): %s" % (", ".join(
        "%s %s over %d records" % (k, _fmt(_dd(v).get("amount"), "%.3f"), _num(_dd(v).get("n")) or 0)
        for k, v in hl.items()) or "none recorded"))
    for d in g["deaths"]:
        last = d["last_decisions"][-1] if d["last_decisions"] else {}
        lines.append("death via %s at game minute %s; the last decision: branch %s, action %s" % (
            d["via"], d["gameMin"], last.get("branch"), last.get("action")))
    c = g.get("death_check")
    if c is not None:
        lines.append("death %s by the frames: health fall %s over %d frames against the server's %s over %d records "
                     "in the same window (tol %s)%s" % (
                         "explained" if c["explained"] else "NOT explained", _fmt(c["health_fall"], "%.3f"),
                         c["frames_n"], _fmt(c["server_amount"], "%.3f"), c["server_n"], c["tol"],
                         "" if c["why"] is None else ": " + c["why"]))
    co = g["cost"]
    lines.append("per-tick cost p50 %s ms, p99 %s ms, max %s ms over %s frames; worst tickMaxMs %s, over5 %s" % (
        _fmt(co.get("p50"), "%.3f"), _fmt(co.get("p99"), "%.3f"), _fmt(co.get("max"), "%.3f"),
        _fmt(co.get("n"), "%d"), _fmt(co.get("tickMaxMs"), "%.3f"), _fmt(co.get("over5"), "%d")))
    lines.append("lua_error events %s (max %s in a minute); parks %s; gaps %s" % (
        _fmt(g["lua_errors"], "%d"), g["lua_errors_max_per_min"], _fmt(g["parks"], "%d"), _fmt(g["gaps"], "%d")))
    return lines
