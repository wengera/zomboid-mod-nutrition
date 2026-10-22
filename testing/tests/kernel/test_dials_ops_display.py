"""Plan 19 Task 3a (waves W2 and W3): the ops dials (sched, resume, store, bus, backup) and the display dials
(hungerCurve, hybrid, view, tooltip) resolve from NR_Data_Dials.lua.

Each kernel field holds its registry row's value; each adapter field reads its row at load; the values derived from the
registry (the hybrid caps and starving minimum, the stall guard, the HUNGRY thresholds, the food-timer band edges, the
players' first budget) are bit-identical to the literals they replaced; and a registry-only edit, made before the
kernels load with no code change, moves a kernel output (the mutation probe, dial-inventory section 3.4).
"""
import os
import re
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

KERNEL_DOMAINS = ("sched", "resume", "hungerCurve", "hybrid", "view")
ADAPTERS = {
    "store": (os.path.join(LUA, "server", "NR_Server_Store.lua"), r"^S\.%s = K\.dials\.get\(\"store\.%s\"\)$"),
    "bus": (os.path.join(LUA, "server", "NR_Server_Bus.lua"), r"^    %s = K\.dials\.get\(\"bus\.%s\"\),$"),
    "backup": (os.path.join(LUA, "server", "NR_Server_Backup.lua"), r"^    %s = K\.dials\.get\(\"backup\.%s\"\),"),
    "tooltip": (os.path.join(LUA, "client", "NR_Client_Tooltip.lua"), r"^    %s = K\.dials\.get\(\"tooltip\.%s\"\),$"),
}
WAVE = KERNEL_DOMAINS + tuple(ADAPTERS)


def rows():
    return {k: v for k, v in dials.values().items() if k.split(".")[0] in WAVE}


def runtime(edits=()):
    """A fresh runtime with NR_Core, the registry (each (old, new) edit applied to its text first) and the kernels."""
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in [CORE, DIALS] + kernel_files():
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        if path == DIALS:
            for old, new in edits:
                assert src.count(old) == 1, old
                src = src.replace(old, new)
        load(src, "@" + os.path.basename(path))()
    return rt.globals().NutritionRevamp.kernel


def field(K, dial_id):
    """K.<dial_id> by its path, a numeric segment indexing an array."""
    v = K
    for seg in dial_id.split("."):
        v = v[int(seg)] if seg.isdigit() else v[seg]
    return v


def test_the_wave_holds_its_dials():
    got = rows()
    for dom in WAVE:
        assert any(k.startswith(dom + ".") for k in got), dom
    assert len(got) == 77


def test_each_kernel_field_holds_its_registry_value():
    K = runtime()
    for dial_id, value in rows().items():
        if dial_id.split(".")[0] in KERNEL_DOMAINS:
            assert field(K, dial_id) == value, dial_id


def test_each_adapter_field_reads_its_row_at_load():
    for dial_id in rows():
        dom, _, name = dial_id.partition(".")
        if dom in ADAPTERS:
            path, rx = ADAPTERS[dom]
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            assert re.search(rx % (re.escape(name), re.escape(name)), src, re.M), dial_id


def test_the_derived_values_are_the_literals_they_replaced():
    K = runtime()
    c = K.hybrid.defaults()
    assert (c.hungerCap, c.thirstCap, c.starvingMin, c.maxStepS) == (0.69, 0.83, 0.71, 3600)
    assert (c.moodRiseUnhappy, c.moodRiseSick, c.moodRiseStress, c.moodRiseBored) == (22 / 3600, 25 / 3600, 5.0e-5, 25 / 3600)
    assert K.hybrid.HUNGRY_4 == 0.70 and K.hybrid.THIRST_4 == 0.84
    T = K.hungerCurve.THRESHOLDS
    assert tuple(T[i] for i in range(1, 5)) == (0.15, 0.25, 0.45, 0.70)
    X, Y = K.hungerCurve.X, K.hungerCurve.Y
    assert tuple(X[i] for i in range(1, 8)) == (0, 0.097, 0.21125, 0.289531, 0.420782, 0.6825, 1)
    assert tuple(Y[i] for i in range(1, 8)) == (0, 0, 0.15, 0.25, 0.45, 0.70, 1)
    assert (K.view.TIMER_BAND_2, K.view.TIMER_BAND_3) == (1600, 3200)
    assert tuple(K.view.timerValues(90)) == (1000, 2800, 4400)
    assert tuple(K.view.timerValues(1200)) == (1600, 3200, 3200 + K.drain.UNITS_PER_MIN * 1200 * 2 + 1)
    assert [K.view.timerBand(t) for t in (0, 1, 1600, 1601, 3200, 3201)] == [0, 1, 1, 2, 2, 3]


def test_the_players_first_budget_is_the_sched_floor():
    with open(os.path.join(LUA, "server", "NR_Server_Players.lua"), encoding="utf-8") as fh:
        assert "budgetMs = K.sched.FLOOR_MS," in fh.read()


def test_a_same_row_resolves_to_its_target_and_the_vanilla_knots_are_fixed():
    text = dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))
    raw = dials.load_rows(text)
    assert raw["hybrid.HUNGRY_4"] == {"same": "hungerCurve.Y.6", "unit": "HUNGER", "src": "vanilla #0508",
                                      "note": raw["hybrid.HUNGRY_4"]["note"]}
    for dial_id in ("hungerCurve.Y.3", "hungerCurve.Y.4", "hungerCurve.Y.5", "hungerCurve.Y.6", "hybrid.THIRST_4",
                    "view.TIMER_BAND_2", "view.TIMER_BAND_3"):
        assert raw[dial_id].get("fixed") is True, dial_id
    assert dials.values()["hybrid.HUNGRY_4"] == 0.70
    with pytest.raises(ValueError):
        dials.set_value(text, "view.TIMER_BAND_2", "1700")


def test_values_is_a_fresh_copy():
    a = dials.values()
    a["hybrid.CAP_MARGIN"] = 9
    assert dials.values()["hybrid.CAP_MARGIN"] == 0.01


# --- the mutation probes: a registry-only edit before the kernels load moves the output ------------------------------

def test_a_registry_knot_moves_the_hunger_curve():
    old = "D['hungerCurve.X.3'] = { value = 0.21125,"
    base, moved = runtime(), runtime([(old, "D['hungerCurve.X.3'] = { value = 0.25,")])
    assert base.hungerCurve.map(0.25) > 0.15
    assert moved.hungerCurve.map(0.25) == pytest.approx(0.15, abs=1e-12)


def test_a_registry_margin_moves_the_caps():
    c = runtime([("D['hybrid.CAP_MARGIN'] = { value = 0.01,", "D['hybrid.CAP_MARGIN'] = { value = 0.02,")]).hybrid.defaults()
    assert (c.hungerCap, c.thirstCap, c.starvingMin) == (0.70 - 0.02, 0.84 - 0.02, 0.70 + 0.02)


def test_a_registry_timer_moves_the_refusal_and_a_registry_floor_moves_the_budget():
    K = runtime([("D['view.TIMER_FULL'] = { value = 4400,", "D['view.TIMER_FULL'] = { value = 5000,"),
                 ("D['sched.FLOOR_MS'] = { value = 15,", "D['sched.FLOOR_MS'] = { value = 20,")])
    assert K.view.foodTimer(4, 0, False, 90) == 5000
    assert K.sched.budgetMs(0.1, 1, 6) == 20
    base = runtime()
    assert base.view.foodTimer(4, 0, False, 90) == 4400 and base.sched.budgetMs(0.1, 1, 6) == 15


def test_each_split_knot_and_ladder_table_stays_strictly_ascending():
    # review M4: a table split into one dial per element keeps its order only if each row is tuned in order;
    # dials.py check does not see the family, so this test does
    K = runtime()
    for path in ("hungerCurve.X", "view.STIMULANT_AT", "view.SLEEP_AT", "view.OVERFULL_AT", "view.FAT_CUTS_MALE",
                 "view.FAT_CUTS_FEMALE"):
        t = field(K, path)
        vals = [t[i] for i in range(1, len(t) + 1)]
        assert all(a < b for a, b in zip(vals, vals[1:])), (path, vals)
