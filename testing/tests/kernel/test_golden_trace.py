"""The golden trace (Plan 10 Task R0, ruling 3): every refactor commit reproduces the trace of 1.0.0 byte for
byte. The scenario and the serialiser are golden_trace.py; the host is server_host.py. A refactor that cannot keep
the trace stops and reports; it never re-records golden/trace-1.0.0.json. A plan that names a behaviour change
re-records it in that change's own commit (CLAUDE.md § 6); Plan 11e Task 1 re-recorded it when the stand-in player
gained getStats (ruling 11e-3: the golden records the written stats).

The golden file is read in text mode, so a CRLF checkout (core.autocrlf) compares equal.
"""
from . import golden_trace


def _golden():
    with open(golden_trace.GOLDEN, encoding="utf-8") as fh:
        return fh.read()


def test_the_golden_trace_of_1_0_0_is_reproduced():
    assert golden_trace.serialize(golden_trace.run(golden_trace.new_host())) == _golden()


def test_the_trace_is_deterministic_within_one_process():
    a = golden_trace.serialize(golden_trace.run(golden_trace.new_host()))
    b = golden_trace.serialize(golden_trace.run(golden_trace.new_host()))
    assert a == b


def test_the_trace_records_the_written_stats_at_every_snapshot():
    # Plan 11e Task 1 (ruling 11e-3): the stand-in player answers getStats, so W.step runs its full composition and
    # every snapshot carries the HUNGER, THIRST and FATIGUE the writer wrote; the hunger moves over the scenario.
    trace = golden_trace.run(golden_trace.new_host())
    hungers = set()
    for snap in trace["snapshots"]:
        for name in golden_trace.NAMES:
            written = snap["players"][name]["written"]
            for stat in ("HUNGER", "THIRST", "FATIGUE"):
                assert isinstance(written[stat], golden_trace._Num), (snap["minute"], name, stat)
            hungers.add(written["HUNGER"].text)
    assert len(hungers) > len(golden_trace.NAMES)
