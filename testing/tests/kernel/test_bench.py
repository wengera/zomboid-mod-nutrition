"""NR_Server_Bench.lua must load with no engine and expose NutritionRevamp.bench_writer() (Plan 11 Task 14).

The file is a server/ file the kernel host does not load, so this test loads it on top of the session host. It
names no Java global, so it loads with no engine. bench_writer() runs kernel.hybrid.write once over module-level
tables it fills once, so bench.global measures the write and not a constructor (spec § 6).
"""
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BENCH = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Bench.lua"
)


@pytest.fixture(scope="session")
def bench_host(host):
    with open(BENCH, encoding="utf-8") as fh:
        src = fh.read()
    chunk = host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Server_Bench.lua")
    chunk()
    return host


def test_bench_writer_is_a_function(bench_host):
    assert lua51.lua_type(bench_host.G.NutritionRevamp.bench_writer) == "function"
    assert lua51.lua_type(bench_host.G.NutritionRevamp.bench_writer_input) == "function"


def test_bench_writer_writes_a_steady_minute(bench_host):
    out = bench_host.G.NutritionRevamp.bench_writer()
    assert out["hunger"] == pytest.approx(0.3)
    assert out["fatigue"] == pytest.approx(0.37)
    assert out["panic"] == 10
    assert out["stress"] == pytest.approx(min(0.1, 0.05 + 5.0e-5 * 60))


def test_bench_writer_reuses_the_same_tables(bench_host):
    same_out = bench_host.rt.eval(
        "function() local NR = NutritionRevamp return NR.bench_writer() == NR.bench_writer() end")()
    same_in = bench_host.rt.eval(
        "function() local NR = NutritionRevamp return NR.bench_writer_input() == NR.bench_writer_input() end")()
    assert same_out is True and same_in is True
