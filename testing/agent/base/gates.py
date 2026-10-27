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
      loop_ms                  {p50, p90, n} over the encounters' loop_ms (the first action's accept minus the first
                               sight, the client's clock).
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
    loops = [v for v in (_num(r.get("loop_ms")) for r in rows if not r.get("void")) if v is not None]
    return {
        "measure": "measure_x5",
        "attack_started_share": {"share": _share(started, len(done)), "started": started, "n": len(done)},
        "melee_delay": {"min": delays[0] if delays else None, "p50": pct(delays, 50),
                        "max": delays[-1] if delays else None, "n": len(delays)},
        "client_server_agreement": {"share": _share(agree, len(kept)), "agree": agree, "n": len(kept),
                                    "voided": len(swings) - len(kept), "tol": AGREE_TOL},
        "loop_ms": {"p50": pct(loops, 50), "p90": pct(loops, 90), "n": len(loops)},
        "kills": {"n": sum(1 for r in rows if r.get("killed") is True),
                  "per_encounter": [None if r.get("void") else r.get("killed") for r in rows]},
        "health_lost": [r.get("health_lost") for r in rows],
        "server_tags": [r.get("server_tags") for r in rows],
        "encounters": {"n": len(rows), "voided": sum(1 for r in rows if r.get("void"))},
        "stop": out.get("stop"),
    }
