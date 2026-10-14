"""The day-close bench (Plan 13 Task 12, ruling 13-33; Rule 6).

Loads the mod's server tree on testing/tests/kernel/server_host.Host with the global NR_BENCH set, so
NR_Server_Metabolism.lua exposes its local closeDay as MET._closeDay (the seam), builds --players records through
MET.ensureBody (the first-sight path, on the host's player stand-in) and times --closes rounds of one close per player
inside Lua with os.clock. Before each close a body's day accumulators are refilled with a typical day (an even-ish
balance, a mixed training signal), so every close does a full day's work; the refill alone is timed in a second loop
and subtracted. Prints the microseconds per player-close: the median of --repeats fresh hosts, and each repeat.

    python tools/bench_day_close.py --players 60 --closes 200
"""
import argparse
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")

# One timed run in Lua: the closes with their refill, then the refill alone; returns both in seconds.
BENCH = r"""
function(MET, bodies, n, closes, ageH)
    local function refill(b, i)
        b.eeDay = 2500
        b.inDay = 2450 + 20 * (i % 5)
        b.ebDay = b.inDay - b.eeDay
        b.pDay = 70 + 10 * (i % 4)
        b.carbDay = 300
        b.lipDay = 80
        b.alcDay = 0
        b.exKcalDay = 150
        b.actKcalDay = 300
        b.metMinDay = 500
        b.band1Day = 30
        b.band2Day = 10
        b.sigDay = 500 * (i % 3)
    end
    local close = MET._closeDay
    local t0 = os.clock()
    for c = 1, closes do
        for i = 1, n do
            local b = bodies[i]
            refill(b, i)
            close(b, b.fm + b.lm + (b.lx or 0), false, ageH + 24 * c, 1, 0)
        end
    end
    local t1 = os.clock()
    for c = 1, closes do
        for i = 1, n do
            local b = bodies[i]
            refill(b, i)
            local w = b.fm + b.lm + (b.lx or 0)
        end
    end
    local t2 = os.clock()
    return t1 - t0, t2 - t1
end
"""


def run_once(players, closes):
    if KERNEL_TESTS not in sys.path:
        sys.path.insert(0, KERNEL_TESTS)
    import server_host
    h = server_host.Host(extra_env="\nNR_BENCH = true\n")
    MET = h.NR.server.metabolism
    if MET._closeDay is None:
        raise SystemExit("MET._closeDay is absent: this tree has no day-close bench seam")
    bodies = h.rt.table()
    for i in range(1, players + 1):
        p = h.player("bench%d" % i)
        p.nut.weight = 60 + (i % 9) * 5
        rec = h.rt.table()
        bodies[i] = MET.ensureBody("bench%d" % i, p, rec, 100.0)
    fn = h.rt.eval(BENCH)
    fn(MET, bodies, players, 5, 100.0)                 # warm-up
    t_close, t_refill = fn(MET, bodies, players, closes, 100.0 + 24 * 5)
    return (t_close - t_refill) / (players * closes) * 1e6


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--players", type=int, default=60)
    ap.add_argument("--closes", type=int, default=200)
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args(argv)
    runs = [run_once(a.players, a.closes) for _ in range(a.repeats)]
    print("day close: %.2f us per player-close (median of %d; players %d, closes %d)"
          % (statistics.median(runs), a.repeats, a.players, a.closes))
    print("repeats: " + ", ".join("%.2f" % r for r in runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
