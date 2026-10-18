"""The stall slot bench (Plan 16 Task 2 fix 1, ruling F2; Rule 6): one queue slot's cost against the sub-steps it runs.

Loads the golden trace's host (testing/tests/kernel/golden_trace.py) with the slot cap lifted, plays g1 five minutes,
then stalls the clock k game hours and times the one queue slot that integrates the stall in k hour-long pipelines:
the host's wall time of the slot (median of 7 fresh hosts) and the Java calls it makes (test_minute_pipeline's
counting stub on the player). K.resume.SLOT_SUBSTEPS (NR_Kernel_Resume.lua) was sized from its output: about 0.56 ms
of host time and 68 Java calls an hour-long sub-step.

    python tools/bench_slot.py
"""
import os
import statistics
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "testing", "tests", "kernel"))
sys.path.insert(0, os.path.join(REPO, "testing", "tests"))
import golden_trace  # noqa: E402
from kernel.test_minute_pipeline import ENGINE_COUNT, _minute  # noqa: E402


def main():
    rows = []
    for k in (1, 2, 3, 4, 6, 8):
        walls, calls = [], []
        for _ in range(7):
            h = golden_trace.new_host()
            h.K.resume.SLOT_SUBSTEPS = 100
            C = h.rt.eval("{ n = 0, by = {} }")
            g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
            h.rt.eval(ENGINE_COUNT)(g1, C)
            h.online(g1)
            start = golden_trace.START_AGE
            for m in range(1, 6):
                _minute(h, start + m / 60.0)
            h.T.age = start + 5 / 60.0 + (k if k > 1 else 1 / 60.0)
            h.minute()
            n0 = C.n
            t0 = time.perf_counter()
            h.tick(golden_trace.TICKS)
            walls.append((time.perf_counter() - t0) * 1000)
            calls.append(C.n - n0)
        rows.append((k, statistics.median(walls), calls[0]))
    base = rows[0][1]
    for k, ms, c in rows:
        print("stall %dh: %d pipeline(s), host %.3f ms a slot (%.2f x one minute), %d Java calls (%.1f a pipeline)"
              % (k, k, ms, ms / base, c, c / k))


if __name__ == "__main__":
    main()
