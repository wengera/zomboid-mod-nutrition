"""Plan 19 Task 3b (waves W4 and W5): the body dials (body, traits, partition, deficit, core, circadian) and the
interaction, record-engine, aerobic and training dials (interact, nutrients, aerobic, training) resolve from
NR_Data_Dials.lua, with the duplicates the inventory names unified ahead of their partners' waves (the S0115 refeeding
cut-offs acute.RISK_*, the sleep-need pair nut.NEED_*).

Each kernel field holds its registry row's value; the inline literals moved to fields (K.body's trend flags and legacy
maps, K.deficit.state's cap and clamp) and the derived values (B12_PASSIVE_FROM, the neutral pPrevKg, K.HEIGHT_M) read
exactly as the literals they replaced; and a registry-only edit, made before the kernels load with no code change,
moves a kernel output (the mutation probes, dial-inventory section 3.4).
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
import dial_lint  # noqa: E402

KERNEL_DOMAINS = ("body", "traits", "partition", "deficit", "core", "circadian", "interact", "nutrients", "aerobic",
                  "training")
RISK = ("acute.RISK_BMI_HIGH", "acute.RISK_LOSS_HIGH", "acute.RISK_DAYS_HIGH", "acute.RISK_BMI_MOD",
        "acute.RISK_LOSS_MOD", "acute.RISK_DAYS_MOD")
NUT = ("nut.NEED_MORE", "nut.NEED_LESS")


def rows():
    return {k: v for k, v in dials.values().items() if k.split(".")[0] in KERNEL_DOMAINS or k in RISK or k in NUT}


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
    return rt, rt.globals().NutritionRevamp.kernel


def field(K, dial_id):
    """K.<dial_id> by its path (core.X is K.X), a numeric segment indexing an array."""
    segs = dial_id.split(".")
    if segs[0] == "core":
        segs = segs[1:]
    v = K
    for seg in segs:
        v = v[int(seg)] if seg.isdigit() else v[seg]
    return v


def test_the_wave_holds_its_dials():
    got = rows()
    for dom in KERNEL_DOMAINS:
        assert any(k.startswith(dom + ".") for k in got), dom
    assert all(k in got for k in RISK + NUT)
    assert len(got) == 121


def test_each_kernel_field_holds_its_registry_value():
    _, K = runtime()
    for dial_id, value in rows().items():
        if dial_id.split(".")[0] != "nut":
            assert field(K, dial_id) == value, dial_id


def test_the_sleep_need_pair_reads_its_rows_at_load():
    with open(os.path.join(LUA, "server", "NR_Server_Nutrients.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in ("NEED_MORE", "NEED_LESS"):
        assert re.search(r'^NUT\.%s = K\.dials\.get\("nut\.%s"\)$' % (name, name), src, re.M), name
    assert dials.values()["nut.NEED_MORE"] == 1.3 and dials.values()["nut.NEED_LESS"] == 0.7


def test_the_moved_values_are_the_literals_they_replaced():
    rt, K = runtime()
    assert K.HEIGHT_M == 1.70
    assert K.interact.B12_PASSIVE_FROM == 4
    assert K.body.new(K.body.create(None, None, K.strength.DEFAULTS, 1), 1, 0).pPrevKg == 0.8
    T = K.traits.FAT_CUTS
    assert [[T[s][i] for i in (1, 2)] for s in (1, 2)] == [[6, 9], [9, 13]]
    assert (K.body.FAT_FMI.none, K.body.FAT_FMI.OVERWEIGHT, K.body.FAT_FMI.OBESE) == (4.5, 7.5, 10.5)
    assert (K.body.THIN.UNDERWEIGHT, K.body.THIN.VERY_UNDERWEIGHT) == (0.10, 0.065)
    assert (K.training.CLIMB_MET.JumpFence, K.training.CLIMB_MET.ClimbRope) == (4.0, 8.0)
    # the legacy protein map and the trend flags, bit for bit against the code they replaced
    old = rt.eval("""function(p)
        local m = 200
        if p <= 0.5 then m = -400 elseif p < 0.8 then m = -300 + 300 * (p - 0.5) / 0.3
        elseif p <= 1.6 then m = 150 * (p - 0.8) / 0.8 end
        return NutritionRevamp.kernel.clamp(m, -500, 1000) end""")
    for i in range(0, 241):
        p = i / 100 + 0.0013
        assert K.body.mapProteins(p) == old(p), p
        assert K.body.mapProteins(i / 100) == old(i / 100), i
    for t in (-0.1, -0.02, -0.0199, 0, 0.02, 0.0201, 0.1, 0.1001):
        assert tuple(K.body.flags(t)) == (t > 0.02, t > 0.10, t < -0.02), t
    assert (K.body.mapCarbs(450), K.body.mapLipids(10)) == (150, -60)
    # the energy state's cap and clamp
    for eb, dep in ((-8000, 0), (8000, 0), (-1000, 0.5), (0, 0.9), (-20000, 1)):
        want = rt.eval("function(eb, dep) local K = NutritionRevamp.kernel return K.clamp(1 + 0.5 * "
                       "K.clamp(-eb / K.deficit.BALANCE_SPAN_KCAL, -1, 1) + K.deficit.fatTerm(dep), 0.5, 2.0) end")(eb, dep)
        assert K.deficit.state(eb, dep) == want, (eb, dep)


def test_the_unified_duplicates_resolve_through_same_and_the_vanilla_values_are_fixed():
    text = dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))
    raw = dials.load_rows(text)
    assert raw["body.PROT_OK"]["same"] == "aerobic.P_LOW" and "value" not in raw["body.PROT_OK"]
    assert dials.values()["body.PROT_OK"] == 0.8
    for dial_id in ("training.MET_FLOOR", "training.CLIMB_MET.JumpFence", "training.CLIMB_MET.ClimbRope", "nut.NEED_MORE",
                    "nut.NEED_LESS"):
        assert raw[dial_id].get("fixed") is True, dial_id
    with pytest.raises(ValueError):
        dials.set_value(text, "nut.NEED_MORE", "1.4")
    with pytest.raises(ValueError):
        dials.set_value(text, "body.PROT_OK", "0.9")


def test_the_dial_lint_reads_the_core_domain_as_ks_top_level():
    ok = 'local K = NutritionRevamp.kernel\nK.HEIGHT_M = K.dials.get("core.HEIGHT_M")\n'
    bad = 'local K = NutritionRevamp.kernel\nK.HEIGHT_M = K.dials.get("core.WIDTH_M")\n'
    assert [f.rule for f in dial_lint.lint_text("NR_Kernel.lua", ok)] == []
    assert [f.rule for f in dial_lint.lint_text("NR_Kernel.lua", bad)] == ["E3"]


# --- the mutation probes: a registry-only edit before the kernels load moves the output ------------------------------

def test_a_registry_protein_reference_moves_the_aerobic_gate_and_the_legacy_store_through_same():
    _, base = runtime()
    _, K = runtime([("D['aerobic.P_LOW'] = { value = 0.8,", "D['aerobic.P_LOW'] = { value = 1.0,")])
    assert base.aerobic.gProt(0.9) == 1 and K.aerobic.gProt(0.9) == K.aerobic.G_PROT_LOW
    assert K.body.PROT_OK == 1.0                                         # body.PROT_OK follows through same
    assert base.body.mapProteins(1.2) == pytest.approx(75) and K.body.mapProteins(1.2) == pytest.approx(50)
    # PROT_RAMP_SPAN is its own literal (0.8 - 0.5 is not the double 0.3), so the ramp below PROT_OK does not follow


def test_a_registry_clamp_moves_the_energy_state():
    _, base = runtime()
    _, K = runtime([("D['deficit.STATE_MAX'] = { value = 2.0,", "D['deficit.STATE_MAX'] = { value = 1.5,")])
    assert base.deficit.state(-20000, 1) == 2.0 and K.deficit.state(-20000, 1) == 1.5


def test_a_registry_height_moves_the_bmi_and_a_registry_offset_moves_the_thin_reading():
    _, base = runtime()
    _, K = runtime([("D['core.HEIGHT_M'] = { value = 1.70,", "D['core.HEIGHT_M'] = { value = 1.80,"),
                    ("D['traits.THIN_F_OFFSET'] = { value = 0.08,", "D['traits.THIN_F_OFFSET'] = { value = 0.10,")])
    assert base.drain.bmi(50, 15) == pytest.approx(65 / 1.7 ** 2) and K.drain.bmi(50, 15) == pytest.approx(65 / 1.8 ** 2)
    assert base.traits.thinReading(20, 80, 2) == pytest.approx(0.12) and K.traits.thinReading(20, 80, 2) == pytest.approx(0.10)
