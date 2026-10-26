"""The stage gates of the agent spike (spec § 4), each a pure function of a driver's artifact dict.

A gate whose reading is missing or empty fails; it never passes on nothing.
"""
import math

TICK_P99_MS = 2.0          # spec § 4.1: per-tick cost at 5 Hz, p99 under this
SCAN15_MS = 5.0            # spec § 4.1: a 15-tile scan's per-tick cost under this (every step of all five)
CMD_MOTION_P90_MS = 500.0  # spec § 4.1: cmd -> motion, p90 under this
MOTION_COMMANDS = 20      # a_pipe's ten round trips: every unvoided one is graded, and this many must be unvoided
MIN_FRAME_SHARE = 0.9      # the tick gate needs at least this share of the nominal 60*r frames at 5 Hz
MODES = ("append", "chunk")


def pct(values, p):
    """Nearest-rank percentile: the smallest value with at least p % of the values at or below it; None when empty."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    rank = max(1, math.ceil(p / 100.0 * len(vals)))
    return vals[min(rank, len(vals)) - 1]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def cmd_motion_ms(motion_rows):
    """Per motion command row: the first-motion frame's `wallMs` minus the ack's `wallMs`. Both are stamped by the
    client's own PZA.now() (getTimestampMs), so no Python clock enters the difference. A command with no ack or no first
    motion (or never sent) is +inf: it counts, and counts as the slowest."""
    out = []
    for r in motion_rows or ():
        a = _num((r.get("ack") or {}).get("wallMs"))
        m = _num((r.get("first_motion") or {}).get("wallMs"))
        out.append(m - a if a is not None and m is not None else math.inf)
    return out


def scan_step_ms(row):
    """A chunked scan row's per-tick cost: max(scanStepMaxMs, last step + scanEmitMs), the completing tick paying for
    its own chunk plus the scan line's emit and flush; None when any of the three is missing."""
    row = row if isinstance(row, dict) else {}
    top, emit = _num(row.get("scanStepMaxMs")), _num(row.get("scanEmitMs"))
    steps = row.get("scanMsPerTick")
    last = _num(steps[-1]) if isinstance(steps, list) and steps else None
    if top is None or emit is None or last is None:
        return None
    return max(top, last + emit)


def _count(v):
    if isinstance(v, (list, tuple)):
        return len(v)
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def gate_a(out):
    """Stage A's go/no-go (spec § 4.1) from a_pipe's artifact dict.

    tick_p99_ms_at5   p99 of the per-frame tickMs (pollMs + actMs + senseMs + linkMs; a_pipe_2 adds scanStepMs) at
                      rate 5; < TICK_P99_MS, on at least MIN_FRAME_SHARE of the window's nominal frames.
    scan15_ms_max     the largest per-tick scan cost over the 15-tile scans: per row, max(scanStepMaxMs, the last
                      step of scanMsPerTick + scanEmitMs), the completing tick carrying the line's emit and flush;
                      < SCAN15_MS. A row missing any of the three fails the gate (a pass-1 row, which has only the
                      one-tick scanMs, fails it). scan15_latency_ms_max is the largest summed scanMs, ungraded.
    cmd_motion_p90_ms p90 over every unvoided motion command of (first-motion frame wallMs - ack wallMs), both the
                      client's clock, an unpaired command +inf; < CMD_MOTION_P90_MS over at least MOTION_COMMANDS
                      unvoided commands. A row whose `voided` is set (a_pipe_2: the character's health fell or a
                      zombie was in radius during the leg, or it was dead at the send) leaves both the pairs and the
                      count, and is reported in cmd_motion_voided with its reasons; a pass-1 row has no `voided`.
    gaps              the link's seq gaps; 0.
    lua_errors        lua_error events on the link plus client console error hits; 0.
    hello             the hello line arrived with a mode of append or chunk.
    A missing reading (no frames, no scans, no motion pairs, no gaps list, no error counts) fails its gate.
    """
    rd = out.get("readings") or {}
    r5 = (rd.get("rates") or {}).get("5") or {}
    at5 = r5.get("tickMs") or []
    tick = pct(at5, 99)
    frames, expected = _num(r5.get("frames")), _num(r5.get("expected"))
    enough = frames is not None and bool(expected) and frames >= MIN_FRAME_SHARE * expected
    scans = ((rd.get("scans") or {}).get("15") or [])
    scan_step = [scan_step_ms(s) for s in scans]
    scan_max = max(scan_step) if scan_step and None not in scan_step else None
    scan_ms = [_num(s.get("scanMs")) for s in scans]
    scan_latency = max(scan_ms) if scan_ms and None not in scan_ms else None
    rows = [r for r in (rd.get("motion") or ()) if isinstance(r, dict)]
    voided = [str(r["voided"]) for r in rows if r.get("voided")]
    cm = cmd_motion_ms([r for r in rows if not r.get("voided")])
    cm90 = pct(cm, 90)
    gaps = _count(out.get("gaps"))
    ev, con = _count(out.get("lua_errors")), _count(out.get("client_lua_errors"))
    errs = ev + con if ev is not None and con is not None else None
    mode = out.get("mode")
    passed = {
        "tick_p99_at5": tick is not None and tick < TICK_P99_MS and enough,
        "scan15": scan_max is not None and scan_max < SCAN15_MS,
        "cmd_motion_p90": cm90 is not None and cm90 < CMD_MOTION_P90_MS and len(cm) >= MOTION_COMMANDS,
        "gaps": gaps == 0,
        "lua_errors": errs == 0,
        "hello": mode in MODES,
    }
    return {"mode": mode, "tick_p99_ms_at5": tick, "scan15_ms_max": scan_max, "scan15_latency_ms_max": scan_latency,
            "cmd_motion_p90_ms": cm90,
            "tick_frames_at5": frames, "cmd_motion_n": len(cm), "cmd_motion_voided": len(voided),
            "cmd_motion_voided_reasons": voided,
            "cmd_motion_paired": sum(1 for v in cm if v != math.inf), "gaps": gaps, "lua_errors": errs, "pass": passed,
            "verdict": "GO" if all(passed.values()) else "NO-GO"}


# ================================================================ Stage B (spec § 4.2)
from agent.reasons import REASONS                    # noqa: E402

SEQUENCES = 5              # b_actions' repetitions
COMPLETE_MIN = 4           # spec § 4.2: sequences completed, at least this many of SEQUENCES


def _eat_seen(se):
    """A row's server_eat saw the eat: some after-reading's hunger below the before's, or its calories above."""
    if not isinstance(se, dict) or not isinstance(se.get("before"), dict):
        return None
    b = se["before"]
    hb, cb = _num(b.get("hunger")), _num(b.get("calories"))
    for a in se.get("after") or ():
        a = a if isinstance(a, dict) else {}
        ha, ca = _num(a.get("hunger")), _num(a.get("calories"))
        if (hb is not None and ha is not None and ha < hb) or (cb is not None and ca is not None and ca > cb):
            return True
    return False


def gate_b(out):
    """Stage B's go/no-go (spec § 4.2) from b_actions' artifact dict (its rows under readings.reps).

    completed            repetitions whose `completed` is True (every step done); >= COMPLETE_MIN.
    reasons_in_set       every step whose state is "failed" (a Lua-reported goal failure) carries a detail in
                         agent.reasons.REASONS; a refused, timed-out or skipped step has no Lua detail and counts against
                         `completed` only.
    eats_seen_by_server  repetitions whose server_eat shows the eat: an after-reading with the server's hunger below the
                         pre-eat reading or its calories above it (re-derived here, never the driver's `moved`);
                         == SEQUENCES.
    A missing reading fails its gate: no readings.reps or an empty one fails all three; a row that is not a dict fails
    all three; a row without `completed` fails `completed`; a row without a readable server_eat fails the eats gate.
    `sequences` reports SEQUENCES (the target); `rows` the rows the artifact holds.
    """
    reps = (out.get("readings") or {}).get("reps")
    reps = reps if isinstance(reps, list) else None
    rows_ok = bool(reps) and all(isinstance(r, dict) for r in reps)
    if rows_ok:
        has_completed = all("completed" in r for r in reps)
        completed = sum(1 for r in reps if r.get("completed") is True) if has_completed else None
        failed = [s for r in reps for s in (r.get("steps") or ()) if isinstance(s, dict) and s.get("state") == "failed"]
        bad = sorted({str(s.get("detail")) for s in failed if s.get("detail") not in REASONS})
        in_set = not bad
        seen = [_eat_seen(r.get("server_eat")) for r in reps]
        eats = None if None in seen else sum(1 for v in seen if v)
        fail_names = sorted({"%s:%s" % (s.get("goal"), s.get("detail")) for r in reps for s in (r.get("steps") or ())
                             if isinstance(s, dict) and s.get("state") != "done"})
    else:
        completed, in_set, eats, bad, fail_names = None, False, None, [], []
    passed = {
        "completed": completed is not None and completed >= COMPLETE_MIN,
        "reasons_in_set": in_set,
        "eats_seen_by_server": eats == SEQUENCES,
    }
    return {"sequences": SEQUENCES, "rows": len(reps) if reps is not None else None, "completed": completed,
            "reasons_in_set": in_set, "reasons_outside_set": bad, "eats_seen_by_server": eats,
            "failing_steps": fail_names, "pass": passed, "verdict": "GO" if all(passed.values()) else "NO-GO"}
