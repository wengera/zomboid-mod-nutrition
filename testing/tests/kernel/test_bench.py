"""NR_Server_Bench.lua must load with no engine and expose NutritionRevamp.bench_fast().

The file is a server/ file the kernel host does not load (the host loads NR_Core.lua and the
NR_Kernel*.lua files only), so this test loads it on top of the session host itself. The file names
no Java global at file scope or in its functions -- it only reads NutritionRevamp.kernel, which the
host has -- so it loads with no engine. bench_fast() runs kernel.fast.step once over module-level
tables it fills once, so bench.global measures the step and not a constructor (spec § 6).
"""
import os
import pytest
import lupa.lua51 as lua51

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


def test_file_reads_only_the_kernel_global(bench_host):
    assert bench_host.G.NutritionRevamp is not None


def test_bench_fast_is_a_function(bench_host):
    assert lua51.lua_type(bench_host.G.NutritionRevamp.bench_fast) == "function"
    assert lua51.lua_type(bench_host.G.NutritionRevamp.bench_fast_input) == "function"


def test_bench_fast_returns_a_clamped_hunger(bench_host):
    out = bench_host.G.NutritionRevamp.bench_fast()
    assert lua51.lua_type(out) == "table"
    h = out["hunger"]
    assert isinstance(h, (int, float))
    assert 0.0 <= h <= 1.0


def test_bench_fast_input_is_a_steady_state_awake_tick(bench_host):
    inp = bench_host.G.NutritionRevamp.bench_fast_input()
    assert lua51.lua_type(inp) == "table"
    assert inp["asleep"] is False
    assert inp["M"] > 0
    assert inp["D"] > 0


def test_bench_fast_reuses_the_same_tables(bench_host):
    # lupa wraps each return in a fresh proxy, so identity is checked on the Lua side: the module
    # owns one output and one input table and never re-allocates, so bench measures the step only.
    same_out = bench_host.rt.eval(
        "function() local NR = NutritionRevamp return NR.bench_fast() == NR.bench_fast() end"
    )()
    assert same_out is True
    same_in = bench_host.rt.eval(
        "function() local NR = NutritionRevamp return NR.bench_fast_input() == NR.bench_fast_input() end"
    )()
    assert same_in is True
