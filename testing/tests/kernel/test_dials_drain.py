"""Plan 19 Task 3g (wave W10, the last): the drain dials resolve from NR_Data_Dials.lua.

Each moved K.drain constant holds its registry row's value, every moved value reads exactly as the literal it replaced,
and the copies laid at load (STARVE_DBMI, K.drain.states' onsets, deaths and shorts) are what the code before computed;
K.drain.derive lays them again, so a runtime write (replay_live.set_constants) reaches them. The wave's duplicates are
same links: effect phase 1 is the starvation onset, the Parched thirst knot is the dehydration onset. The phases and
the thirst knots must ascend (tools/dials.py ASCENDING), each divisor's floor sits above 0, and each span a kernel
divides by is ordered by its rows' ranges. Two more rows: the engine load factor Energy's stripLoad divides out (fixed,
vanilla), and the OnsetSpeed and Severity scalers (param rows the options poll reads, one source with the option file).
A registry-only edit, made before the kernels load with no code change, moves a kernel output (the mutation probes).
"""
import os
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

# The replaced kernel lines' values, verbatim from 6d7c6d23 (NR_Kernel_Drain.lua), and Energy's inline load factor.
OLD = {
    "SHORT_STARVE_H": 336, "SHORT_DEHYD_H": 48, "STARVE_DPDT": 0.0004359462040936248, "CAL_BMI0": 22.42350650342769,
    "STARVE_ONSET_H": 30, "RECENT_MIN_KCAL": 600, "BMI_DEATH": 12, "BMI_CHRONIC": 13, "SUSPEND_M": 236.44,
    "DEHYD_ONSET": 4, "DEHYD_DEATH": 17, "BERIBERI_DEATH_H": 840, "SCURVY_DEATH_H": 2160, "PELLAGRA_DEATH_H": 4320,
    "NA_DEATH_H": 6, "FE_DEATH_H": 24,
}
OLD_PHASES = (30, 72, 336)
OLD_STATES = [  # (onset, death, short) by code, as the replaced constructor laid them
    (30, 12, 336), (4, 2160, None), (4, 840, None), (4, 4320, None), (3, 6, None), (4, 17, 48), (3, 24, None)]
LINKS = {"drain.STARVE_PHASE_H.1": "drain.STARVE_ONSET_H", "fluids.THIRST_KNOTS.5.1": "drain.DEHYD_ONSET"}
FIT = {"drain.STARVE_DPDT", "drain.CAL_BMI0"}
DIVISORS = ("drain.SHORT_STARVE_H", "drain.SHORT_DEHYD_H", "drain.BERIBERI_DEATH_H", "drain.SCURVY_DEATH_H",
            "drain.PELLAGRA_DEATH_H", "drain.NA_DEATH_H", "drain.FE_DEATH_H")
# (lower, upper): the lower dial's max under the upper's min
DISJOINT = (("drain.BMI_DEATH", "drain.BMI_CHRONIC"),        # the chronic onset comes before the death BMI
            ("drain.BMI_DEATH", "drain.CAL_BMI0"),           # CAL_BMI0 - BMI_DEATH, the opening rate's span
            ("drain.DEHYD_ONSET", "drain.DEHYD_DEATH"),      # DEHYD_DEATH - DEHYD_ONSET, Realistic dehydration's T
            ("hungerCurve.FED_M", "drain.SUSPEND_M"))        # a meal spell opens over the fed level


def text():
    return dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))


def raw_rows():
    return dials.load_rows(text())


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


def value_edit(dial_id, new):
    line = dials.source_line(dial_id)
    head = "D['%s'] = { value = %s," % (dial_id, dials.value_text(line))
    assert line.startswith(head), line
    return head, "D['%s'] = { value = %s," % (dial_id, new)


def fraction(rt, K, code, t, pace=3, dehyd=0.0, rise=0.0):
    inp = rt.table_from({"pStarve": 0.0, "pRate": 0.0, "dehydPct": dehyd, "dRise": rise})
    return K.drain.fraction(code, t, inp, rt.table_from({"pace": pace, "combine": 2, "dayMin": 90}))


def states(K):
    S = K.drain.states
    return [(S[c].onset, S[c].death, S[c].short) for c in range(1, 8)]


def test_the_wave_holds_its_dials():
    got = raw_rows()
    drain = [k for k in got if k.startswith("drain.")]
    assert len(drain) == 19
    assert {k for k in drain if "fit" in got[k]} == FIT
    assert {k for k in drain if "same" in got[k]} == {"drain.STARVE_PHASE_H.1"}
    assert got["energy.LOAD_FACTOR"].get("fixed") is True and got["energy.LOAD_FACTOR"]["src"] == "vanilla #2649"
    assert {k for k in got if k.startswith("options.")} == {"options.ONSET_SPEED", "options.SEVERITY"}


def test_each_moved_value_is_the_literal_it_replaced():
    _, K = runtime()
    for name, old in OLD.items():
        assert float(K.drain[name]).hex() == float(old).hex(), name
        assert K.drain[name] == dials.values()["drain." + name], name
    assert [K.drain.STARVE_PHASE_H[i] for i in (1, 2, 3)] == list(OLD_PHASES)
    assert K.drain.STARVE_PHASE_H[4] is None
    assert float(K.energy.LOAD_FACTOR).hex() == float(0.35).hex()


def test_the_copies_laid_at_load_are_the_code_before_and_derive_lays_the_same():
    _, K = runtime()
    dbmi = 0.0004359462040936248 * (22.42350650342769 - 12)
    assert float(K.drain.STARVE_DBMI).hex() == float(dbmi).hex()
    assert states(K) == OLD_STATES
    K.drain.derive()
    assert float(K.drain.STARVE_DBMI).hex() == float(dbmi).hex()
    assert states(K) == OLD_STATES
    assert [K.drain.states[c].name for c in range(1, 8)] == ["starvation", "scurvy", "beriberi", "pellagra",
                                                             "hyponatraemia", "dehydration", "iron"]


def test_derive_on_the_shared_host_changes_nothing(host):
    # on the session's line-hooked host, so the coverage gate (test_zz_coverage) sees derive's lines run
    K = host.K
    before = (float(K.drain.STARVE_DBMI).hex(), states(K))
    K.drain.derive()
    assert (float(K.drain.STARVE_DBMI).hex(), states(K)) == before


def test_the_wave_duplicates_are_same_links_and_the_load_factor_fixed():
    raw = raw_rows()
    _, K = runtime()
    for dial_id, target in LINKS.items():
        assert raw[dial_id]["same"] == target, dial_id
        assert dials.values()[dial_id] == dials.values()[target], dial_id
        with pytest.raises(ValueError):
            dials.set_value(text(), dial_id, "5")
    assert K.drain.STARVE_PHASE_H[1] == K.drain.STARVE_ONSET_H == 30
    assert K.fluids.THIRST_KNOTS[5][1] == K.drain.DEHYD_ONSET == 4
    with pytest.raises(ValueError, match="fixed"):
        dials.set_value(text(), "energy.LOAD_FACTOR", "0.4")


def test_the_wave_divisor_floors_and_orderings_hold():
    raw = raw_rows()
    resolved = lambda i: raw[dials._resolve(raw, i)[0]]
    for dial_id in DIVISORS:
        assert resolved(dial_id)["min"] > 0, dial_id
    for lo, hi in DISJOINT:
        assert resolved(lo)["max"] < resolved(hi)["min"], (lo, hi)


def test_the_phases_and_the_thirst_knots_must_ascend():
    with pytest.raises(ValueError, match="must ascend"):
        dials.set_value(text(), "drain.STARVE_PHASE_H.3", "72")             # equal to phase 2: the ladder's order
    with pytest.raises(ValueError, match="must ascend"):
        dials.set_value(text(), "drain.DEHYD_ONSET", "3")                   # on the level-3 knot's 3 %: K.interp divides
    for dial_id, v in (("drain.DEHYD_ONSET", "5"), ("drain.STARVE_ONSET_H", "60")):      # in order: a tune passes
        out, _ = dials.set_value(text(), dial_id, v)
        assert not [f for f in dials.check(text=out) if "must ascend" in f], dial_id



def test_a_renamed_knot_reports_an_incomplete_chain_instead_of_switching_the_rule_off():
    renamed = text().replace("D['drain.STARVE_PHASE_H.2']", "D['drain.STARVE_PHASE_H.9']")
    assert any("knot chain is incomplete: missing drain.STARVE_PHASE_H.2" in f for f in dials.check(text=renamed))
    assert not [f for f in dials.check(text=text()) if "incomplete" in f]

def test_a_runtime_set_reaches_the_copies_and_the_linked_fields():
    import replay_live
    rt, K = runtime()
    replay_live.set_constants(K, {"drain.SHORT_STARVE_H": 168.0, "drain.BMI_DEATH": 11.0, "drain.DEHYD_ONSET": 5.0,
                                  "drain.STARVE_ONSET_H": 36.0, "drain.FE_DEATH_H": 12.0})
    assert K.drain.states[1].short == 168.0 and K.drain.states[1].death == 11.0 and K.drain.states[1].onset == 36.0
    assert K.drain.STARVE_DBMI == pytest.approx(0.0004359462040936248 * (22.42350650342769 - 11.0), rel=1e-15)
    assert K.drain.states[6].onset == 5.0 and K.fluids.THIRST_KNOTS[5][1] == 5.0      # the Parched knot follows
    assert K.drain.STARVE_PHASE_H[1] == 36.0                                           # phase 1 is the onset
    f, rate = fraction(rt, K, K.drain.STARVATION, 84.0, pace=K.drain.PACE_SHORT)
    assert f == pytest.approx(0.5, abs=1e-12) and rate == pytest.approx(100 * 24 / 168.0, abs=1e-9)
    f, _ = fraction(rt, K, K.drain.IRON, 6.0)
    assert f == pytest.approx(0.5, abs=1e-12)


# --- the mutation probes: a registry-only edit before the kernels load moves the output ------------------------------

def test_a_registry_death_time_moves_the_line_and_a_registry_short_moves_the_shortened_pace():
    rt0, base = runtime()
    rt, K = runtime([value_edit("drain.SCURVY_DEATH_H", "1080"), value_edit("drain.SHORT_DEHYD_H", "96")])
    assert fraction(rt0, base, base.drain.SCURVY, 540.0)[0] == pytest.approx(0.75, abs=1e-12)
    assert fraction(rt, K, K.drain.SCURVY, 540.0)[0] == pytest.approx(0.5, abs=1e-12)
    assert fraction(rt0, base, base.drain.DEHYD, 24.0, pace=2)[0] == pytest.approx(0.5, abs=1e-12)
    assert fraction(rt, K, K.drain.DEHYD, 24.0, pace=2)[0] == pytest.approx(0.75, abs=1e-12)


def test_a_registry_dehydration_onset_moves_the_state_and_the_parched_knot():
    rt0, base = runtime()
    rt, K = runtime([value_edit("drain.DEHYD_ONSET", "5")])
    assert K.fluids.THIRST_KNOTS[5][1] == 5 and base.fluids.THIRST_KNOTS[5][1] == 4
    assert K.fluids.tVol(4.0) < base.fluids.tVol(4.0) == pytest.approx(0.84, abs=1e-12)
    f0 = fraction(rt0, base, base.drain.DEHYD, 0.0, dehyd=10.5)[0]
    f1 = fraction(rt, K, K.drain.DEHYD, 0.0, dehyd=10.5)[0]
    assert f0 == pytest.approx(1 - 6.5 / 13, abs=1e-12) and f1 == pytest.approx(1 - 5.5 / 12, abs=1e-12)


def test_a_registry_onset_moves_the_acute_onset_and_phase_1_through_same():
    _, base = runtime()
    _, K = runtime([value_edit("drain.STARVE_ONSET_H", "36")])
    assert K.drain.STARVE_ONSET_H == 36 and K.drain.STARVE_PHASE_H[1] == 36 and K.drain.states[1].onset == 36
    assert base.drain.starvePhase(33.0) == 1 and K.drain.starvePhase(33.0) == 0


def test_a_registry_phase_and_a_registry_load_factor_move_their_outputs():
    _, base = runtime()
    _, K = runtime([value_edit("drain.STARVE_PHASE_H.2", "48"), value_edit("energy.LOAD_FACTOR", "0.7")])
    assert base.drain.starvePhase(50.0) == 1 and K.drain.starvePhase(50.0) == 2
    assert base.energy.stripLoad(1.35, 10.0, 10.0) == pytest.approx(1.0, abs=1e-12)
    assert K.energy.stripLoad(1.7, 10.0, 10.0) == pytest.approx(1.0, abs=1e-12)


# --- the two scalers: the options poll reads their rows ------------------------------------------------------------

def test_the_scaler_read_is_the_clamp_it_replaced():
    rt, K = runtime()
    raw = raw_rows()
    for dial_id, opt, lo, hi in (("options.ONSET_SPEED", "OnsetSpeed", 0.5, 30), ("options.SEVERITY", "Severity", 0, 3)):
        row = K.dials.row(dial_id)
        assert (row.opt, row.min, row.max, row.value) == (opt, lo, hi, 1.0) == (raw[dial_id]["opt"], raw[dial_id]["min"],
                                                                                 raw[dial_id]["max"], raw[dial_id]["value"])
        for v in (None, 0.2, 0.5, 1.0, 2.37, 29.9, 31, 99, -1, "x", float("nan")):
            sv = rt.table_from({} if v is None else {opt: v})
            want = K.readLeaf(sv, opt, 1.0, lo, hi, True)                   # the poll's line before Plan 19 Task 3g
            got = K.dials.readParam(sv, row, row.value)
            assert (got == want) or (got != got and want != want), (dial_id, v)


def test_the_options_poll_clamps_the_scalers_at_their_rows():
    from .server_host import Host
    h = Host()
    O = h.NR.server.options
    assert (O.onsetSpeed, O.severity) == (1.0, 1.0)
    assert h.rt.eval("function(a, b) return rawequal(a, b) end")(O.ONSET_SPEED, h.NR.data.dials["options.ONSET_SPEED"])
    h.rt.execute("SandboxVars = { NR = { OnsetSpeed = 99, Severity = -1 } }")
    h.NR.server.readOptions("poll")
    assert (O.onsetSpeed, O.severity) == (30, 0)
    h.rt.execute("SandboxVars = { NR = { OnsetSpeed = 2.5, Severity = 1.5 } }")
    h.NR.server.readOptions("poll")
    assert (O.onsetSpeed, O.severity) == (2.5, 1.5)
