"""The stage gates of the agent spike (spec § 4), each a pure function of a driver's artifact dict.

A gate whose reading is missing or empty fails; it never passes on nothing.
"""
import math

TICK_P99_MS = 2.0          # spec § 4.1: per-tick cost at 5 Hz, p99 under this
SCAN15_MS = 5.0            # spec § 4.1: a 15-tile scan under this (every one of the five)
CMD_MOTION_P90_MS = 500.0  # spec § 4.1: cmd -> motion, p90 under this
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
    """Per motion command: the first-motion frame's `wallMs` minus the ack's `wallMs`. Both are stamped by the client's
    own PZA.now() (getTimestampMs), so no Python clock enters the difference; a row lacking either is skipped."""
    out = []
    for r in motion_rows or ():
        a = _num((r.get("ack") or {}).get("wallMs"))
        m = _num((r.get("first_motion") or {}).get("wallMs"))
        if a is not None and m is not None:
            out.append(m - a)
    return out


def _count(v):
    if isinstance(v, (list, tuple)):
        return len(v)
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def gate_a(out):
    """Stage A's go/no-go (spec § 4.1) from a_pipe's artifact dict.

    tick_p99_ms_at5   p99 of the per-frame tickMs (pollMs + actMs + senseMs + linkMs) at rate 5; < TICK_P99_MS.
    scan15_ms_max     the largest scanMs of the 15-tile scans; < SCAN15_MS.
    cmd_motion_p90_ms p90 over the motion commands of (first-motion frame wallMs - ack wallMs), both the client's clock;
                      < CMD_MOTION_P90_MS.
    gaps              the link's seq gaps; 0.
    lua_errors        lua_error events on the link plus client console error hits; 0.
    hello             the hello line arrived with a mode of append or chunk.
    A missing reading (no frames, no scans, no motion pairs, no gaps list, no error counts) fails its gate.
    """
    rd = out.get("readings") or {}
    at5 = ((rd.get("rates") or {}).get("5") or {}).get("tickMs") or []
    tick = pct(at5, 99)
    scans = ((rd.get("scans") or {}).get("15") or [])
    scan_ms = [_num(s.get("scanMs")) for s in scans]
    scan_max = max(scan_ms) if scan_ms and None not in scan_ms else None
    cm = cmd_motion_ms(rd.get("motion"))
    cm90 = pct(cm, 90)
    gaps = _count(out.get("gaps"))
    ev, con = _count(out.get("lua_errors")), _count(out.get("client_lua_errors"))
    errs = ev + con if ev is not None and con is not None else None
    mode = out.get("mode")
    passed = {
        "tick_p99_at5": tick is not None and tick < TICK_P99_MS,
        "scan15": scan_max is not None and scan_max < SCAN15_MS,
        "cmd_motion_p90": cm90 is not None and cm90 < CMD_MOTION_P90_MS,
        "gaps": gaps == 0,
        "lua_errors": errs == 0,
        "hello": mode in MODES,
    }
    return {"mode": mode, "tick_p99_ms_at5": tick, "scan15_ms_max": scan_max, "cmd_motion_p90_ms": cm90,
            "cmd_motion_n": len(cm), "gaps": gaps, "lua_errors": errs, "pass": passed,
            "verdict": "GO" if all(passed.values()) else "NO-GO"}
