"""Plan 19 Task 3f (wave W9): the strength dials resolve from NR_Data_Dials.lua, and the sandbox options are its rows.

Each K.strength.DEFAULTS key and K.strength constant holds its registry row's value, and every moved value, the
DEFAULTS `pairs` order and the protein knots read exactly as the code they replaced. The 34 strength options are the
registry's param rows: K.strength.OPTIONS is built from them at load (K.dials.paramOptions), K.dials.apply never writes
them (K.strength.params reads them into a server's P table), and tools/sandbox_options.py writes the option file from
them. The wave's duplicates are same links: the growth gate's half knot and the deficit protection's start are the RDA
(aerobic.P_LOW), the gate's full knot and the legacy store's full point are PROTEIN_FULL. A registry-only edit, made
before the kernels load with no code change, moves a kernel output (the mutation probes, dial-inventory section 3.4).
"""
import os
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import CORE, DIALS, REPO, kernel_files

sys.path.insert(0, os.path.join(REPO, "tools"))
import dials  # noqa: E402

LINKS = {
    "strength.DEFAULTS.fp_knots.2.1": "aerobic.P_LOW", "strength.DEFAULTS.pdef_lo": "aerobic.P_LOW",
    "strength.DEFAULTS.fp_knots.4.1": "strength.PROTEIN_FULL", "body.PROT_FULL": "strength.PROTEIN_FULL",
}
FIXED = {"strength.L_MAX": "vanilla #2118", "strength.MASTERY_MAX": "#1525"}
DIVISORS = ("strength.DEFAULTS.tauUpWk", "strength.DEFAULTS.tauDownWk", "strength.DEFAULTS.Wsat",
            "strength.DEFAULTS.xpPerSet", "strength.DEFAULTS.surplus_full", "strength.DEFAULTS.S_def",
            "strength.DEFAULTS.x_tau_d", "strength.DEFAULTS.detrain_hl_wk", "strength.DEFAULTS.regain_hl_wk",
            "strength.DEFAULTS.peak_hl_yr", "strength.DEFAULTS.ffmiPerLevel", "strength.DEFAULTS.b",
            "strength.DEFAULTS.nov_pspan", "strength.DEFAULTS.xs_pspan", "strength.DEFAULTS.forbes_c",
            "strength.DEFAULTS.ts", "strength.DEFAULTS.N0.WEAK", "strength.DEFAULTS.m", "strength.PROTEIN_FULL",
            "strength.FAT_PER_PTS")
# (lower, upper): the lower dial's max under the upper's min, so the difference a kernel divides by stays positive
DISJOINT = (("strength.DEFAULTS.Sg0", "strength.DEFAULTS.Sref"),              # sqrt(Sref) - sqrt(Sg0), the signal
            ("aerobic.P_LOW", "strength.DEFAULTS.pdef_hi"),                  # pdef_hi - pdef_lo, the deficit partition
            ("aerobic.P_LOW", "strength.PROTEIN_FULL"),                      # body.PROT_FULL - PROT_OK, the legacy store
            ("strength.DEFAULTS.fp_knots.1.1", "aerobic.P_LOW"),             # the knots' x gaps, K.interp
            ("aerobic.P_LOW", "strength.DEFAULTS.fp_knots.3.1"),
            ("strength.DEFAULTS.capLevel", None),                            # Fc - F0: capLevel above bio level 5
            ("strength.DEHYD_PCT1", "strength.DEHYD_PCT2"), ("strength.AM_FROM_H", "strength.AM_TO_H"))

# The replaced constructors, verbatim from 3f8ab5a8 (the values and the key order the pairs order follows).
OLD = """
local O = {}
O.DEFAULTS = {
    k = 0.009906127265972144,
    beta = 3.0,
    Sg0 = 0.5,
    Sref = 12.0,
    Smax = 30.0,
    Smax1 = 12.0,
    fp_knots = { { 0.4, 0 }, { 0.8, 0.5 }, { 1.3, 0.92 }, { 1.6, 1.0 } },
    E0 = -650.0,
    E0_drop = 0.5,
    fbal0 = 1.0,
    fbal_drop = 0.5,
    surplus_full = 0.10,
    full_drop = 0.5,
    a_nov = 6.0,
    trained_need = 0.0,
    forbes_c = 10.4,
    wT = 0.35,
    S_def = 10.0,
    wP = 0.6,
    pdef_lo = 0.8,
    pdef_hi = 1.6,
    prot_floor = 0.1,
    x_max_frac = 0.05,
    x_tau_d = 28.0,
    m = 0.3333333333333333,
    grace_d = 14,
    detrain_hl_wk = 6.0,
    detrain_status = 2.0,
    regain_hl_wk = 6.0,
    peak_hl_yr = 2.0,
    ffmi5 = 18.0,
    ffmiPerLevel = 0.5,
    capLevel = 16.5,
    ts = 1.0,
    xpPerSet = 360,
    incidental = 0.35,
    fMinShare = 0.35,
    fmMin = 0.5,
    nov_p0 = 1.6,
    nov_pspan = 0.8,
    xs_p0 = 0.8,
    xs_pspan = 0.8,
    b = 0.8,
    Fnm = 27.0,
    N0 = { STRONG = 1.14, STOUT = 1.07, none = 1.0, FEEBLE = 0.915, WEAK = 0.82 },
    startLevel = { STRONG = 9, STOUT = 7, none = 5, FEEBLE = 3, WEAK = 1 },
    traitShare = 0.5,
    ffmiNatural = 25.0,
    kouriCoef = 6.3,
    Tmax = 1.10,
    tauUpWk = 3.0,
    tauDownWk = 12.0,
    Tgrace_d = 21,
    Wsat = 5.0,
    yearsTo10 = 4.0,
    perfectS = 20.0,
    perfectP = 2.0,
    perfectE = 0.10,
}
O.DEFAULTS.M5 = 0
O.DEFAULTS.R = 0
O.DEFAULTS.ffmiNaturalRaw = 0
O.DROP_MARGIN = 0.25
O.L_MAX = 10
O.DEHYD_PCT1 = 2
O.DEHYD_STEP1 = -0.03
O.DEHYD_PCT2 = 4
O.DEHYD_STEP2 = -0.06
O.DEHYD_SWEAT_K = 1.5
O.SLEEP_KNEE_H = 18
O.SLEEP_PER_H = -0.004
O.SLEEP_CAP = -0.08
O.SLEEP_AM_FACTOR = 0.5
O.AM_FROM_H = 6
O.AM_TO_H = 12
O.CAFFEINE_BONUS = 0.02
O.VITD_PENALTY = -0.03
O.FAT_PER_10PT = -0.03
O.FAT_KNEE = 0.30
O.FAT_PER_PTS = 0.10
O.E_ACUTE_MIN = -0.20
O.E_ACUTE_MAX = 0.03
O.MASTERY_MAX = 15
O.PROTEIN_FULL = 1.6
O.RATE = 1.0
O.BODY_PROT_FULL = 1.6
return O
"""


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


def field(K, dial_id):
    """K.<dial_id> by its path, a numeric segment indexing an array."""
    v = K
    for seg in dial_id.split("."):
        v = v[int(seg)] if seg.isdigit() else v[seg]
    return v


def dump(rt, t):
    keys = rt.eval("function(t) local ks = {} for k in pairs(t) do ks[#ks + 1] = k end return ks end")(t)
    out = []
    for i in range(1, len(keys) + 1):
        k = keys[i]
        v = t[k]
        out.append((k, dump(rt, v) if lua51.lua_type(v) == "table" else float(v).hex()))
    return out


def test_the_wave_holds_its_dials():
    got = raw_rows()
    rows = [k for k in got if k.startswith("strength.")]
    assert len(rows) == 88
    assert sum(1 for k in rows if got[k].get("param")) == 34 and all("opt" in got[k] for k in rows if got[k].get("param"))
    assert sum(1 for k in rows if "fit" in got[k]) == 14


def test_each_kernel_field_holds_its_registry_value():
    _, K = runtime()
    for dial_id, value in dials.values().items():
        if dial_id.startswith("strength.") and dial_id not in ("strength.RATE",):
            assert field(K, dial_id) == value, dial_id
    assert K.strength.RATE == 1.0 and K.body.PROT_FULL == K.strength.PROTEIN_FULL == 1.6


def test_the_moved_values_and_the_pairs_order_are_the_code_they_replaced():
    rt, K = runtime()
    old = rt.execute(OLD)
    # the pairs order: the constructor's keys, then the three derived at load, as the replaced code inserted them
    assert [k for k, _ in dump(rt, K.strength.DEFAULTS)] == [k for k, _ in dump(rt, old.DEFAULTS)]
    got = dict(dump(rt, K.strength.DEFAULTS))
    for k, v in dump(rt, old.DEFAULTS):
        if k not in ("M5", "R", "ffmiNaturalRaw"):
            assert got[k] == v, k
    for name in old.keys():
        if name in ("DEFAULTS", "BODY_PROT_FULL"):
            continue
        assert float(K.strength[name]).hex() == float(old[name]).hex(), name
    assert float(K.body.PROT_FULL).hex() == float(old.BODY_PROT_FULL).hex()


def test_the_wave_duplicates_are_same_links_and_the_scale_maxima_fixed():
    raw = raw_rows()
    for dial_id, target in LINKS.items():
        assert raw[dial_id]["same"] == target, dial_id
        assert dials.values()[dial_id] == dials.values()[target], dial_id
    for dial_id, src in FIXED.items():
        assert raw[dial_id].get("fixed") is True and raw[dial_id]["src"] == src, dial_id
    for dial_id in list(FIXED) + list(LINKS):
        with pytest.raises(ValueError):
            dials.set_value(text(), dial_id, "1.2")


def test_the_wave_orderings_and_divisor_floors_hold():
    _, K = runtime()
    raw = raw_rows()
    resolved = lambda i: raw[dials._resolve(raw, i)[0]]
    for dial_id in DIVISORS:
        assert resolved(dial_id)["min"] > 0, dial_id
    for lo, hi in DISJOINT:
        if hi is None:
            assert resolved(lo)["min"] > 5, lo
        else:
            assert resolved(lo)["max"] < resolved(hi)["min"], (lo, hi)
    # Fnm under the lean of the average at the smallest height and FFMI the ranges allow (M5 = F5 - Fnm divides)
    h = raw["core.HEIGHT_M"]["min"]
    assert raw["strength.DEFAULTS.Fnm"]["max"] < raw["strength.DEFAULTS.ffmi5"]["min"] * h * h
    # the one unordered pair: fp_knots.3.1 under PROTEIN_FULL, whose range is its option's (the option scales every
    # knot's x together, so only a registry tune of PROTEIN_FULL to 1.3 or under could cross it): the shipped knots
    S = K.strength
    xs = [S.DEFAULTS.fp_knots[i][1] for i in (1, 2, 3, 4)]
    assert all(a < b for a, b in zip(xs, xs[1:])), xs
    assert S.DEHYD_STEP2 < S.DEHYD_STEP1 < 0 and S.E_ACUTE_MIN < 0 < S.E_ACUTE_MAX
    assert raw["strength.DEFAULTS.Sref"]["min"] > raw["strength.DEFAULTS.Sg0"]["max"]


def test_the_options_are_the_param_rows_and_k_dials_apply_never_writes_them():
    rt, K = runtime()
    raw = raw_rows()
    params = sorted(i for i in raw if raw[i].get("param"))
    opts = K.strength.OPTIONS
    got = [opts[i] for i in range(1, len(params) + 1)]
    assert [e.id for e in got] == params and opts[len(params) + 1] is None
    for e in got:
        row = raw[e.id]
        assert (e.opt, e.value, e.min, e.max, e.int is True) == (row["opt"], dials.values()[e.id], row["min"], row["max"],
                                                                  row.get("int") is True), e.id
        assert e.key == e.id.split(".")[-1] and e.written == dials.written(row["value"]), e.id
    ids = K.dials.OPT_IDS
    assert not any(ids[i].startswith("strength.") for i in range(1, 1000) if ids[i] is not None)
    # a sandbox table full of strength options moves no kernel field through the per-minute apply
    sv = rt.table_from({e.opt: e.max for e in got})
    seen = rt.table()
    assert K.dials.apply(sv, seen) == 0
    assert K.strength.DEFAULTS.ts == 1.0 and K.strength.PROTEIN_FULL == 1.6


def test_read_param_maps_the_written_third_back_and_clamps_like_read_leaf():
    rt, K = runtime()
    m = [K.strength.OPTIONS[i] for i in range(1, 35) if K.strength.OPTIONS[i].key == "m"][0]
    assert m.written == 0.333 and m.value == 1 / 3
    for v, want in ((0.333, 1 / 3), (0.3334, 1 / 3), (0.3336, 0.3336), (5, 1.0), (None, 1 / 3)):
        sv = rt.table_from({} if v is None else {"StrengthMaintainShare": v})
        assert K.dials.readParam(sv, m, m.value) == want, v
    g = [K.strength.OPTIONS[i] for i in range(1, 35) if K.strength.OPTIONS[i].key == "grace_d"][0]
    assert K.dials.readParam(rt.table_from({"StrengthGraceDays": 99}), g, g.value) == 14     # an integer out of range: default
    assert K.dials.written(-650.0) == -650.0 and K.dials.written(0.35) == 0.35


# --- the mutation probes: a registry-only edit before the kernels load moves the output ------------------------------

def test_a_registry_growth_rate_moves_params_and_a_registry_margin_moves_the_held_level():
    _, base = runtime()
    _, K = runtime([value_edit("strength.DEFAULTS.k", "0.0105"), value_edit("strength.DROP_MARGIN", "0.5")])
    assert base.strength.params(None)[0].k == 0.009906127265972144 and K.strength.params(None)[0].k == 0.0105
    assert base.strength.heldLevel(6.6, 7)[0] == 6 and K.strength.heldLevel(6.6, 7)[0] == 7


def test_a_registry_rda_moves_the_gate_knot_and_the_protection_start_through_same():
    _, base = runtime()
    _, K = runtime([value_edit("aerobic.P_LOW", "0.9")])
    P0, P = base.strength.params(None)[0], K.strength.params(None)[0]
    assert P0.fp_knots[2][1] == 0.8 and P.fp_knots[2][1] == 0.9 and P.pdef_lo == 0.9
    assert base.strength.fp(0.8, P0) == 0.5 and K.strength.fp(0.9, P) == 0.5


def test_a_registry_full_protein_moves_the_last_knot_the_legacy_store_and_the_option_default():
    import sandbox_options
    _, K = runtime([value_edit("strength.PROTEIN_FULL", "2.0")])
    P = K.strength.params(None)[0]
    assert K.strength.PROTEIN_FULL == 2.0 and P.fp_knots[4][1] == 2.0 and K.body.PROT_FULL == 2.0
    edited = text().replace(*value_edit("strength.PROTEIN_FULL", "2.0"))
    assert "type = double, min = 1.0, max = 3.0, default = 2.0," in sandbox_options.render(edited)


def test_a_registry_option_default_moves_its_field_params_and_the_r_of_defaults():
    # an option row's value is both its DEFAULTS field (R and averageLean read DEFAULTS, never a server's options) and the
    # entry params reads with no sandbox; Tmax is read by R at load
    _, base = runtime()
    _, K = runtime([value_edit("strength.DEFAULTS.ts", "2.0"), value_edit("strength.RATE", "2.0"),
                    value_edit("strength.DEFAULTS.Tmax", "1.12")])
    P = K.strength.params(None)[0]
    assert K.strength.DEFAULTS.ts == 2.0 and K.strength.RATE == 2.0 and K.strength.DEFAULTS.Tmax == 1.12
    assert P.ts == 2.0 and P.k == 2 * 0.009906127265972144
    assert K.strength.DEFAULTS.R > base.strength.DEFAULTS.R


def test_a_runtime_set_of_a_param_field_reaches_params():
    import replay_live
    _, K = runtime()
    replay_live.set_constants(K, {"strength.DEFAULTS.Tmax": 1.12, "strength.DEFAULTS.m": 0.5, "strength.PROTEIN_FULL": 2.0})
    P = K.strength.params(None)[0]
    assert P.Tmax == 1.12 and P.m == 0.5 and P.fp_knots[4][1] == 2.0 and P.fp_knots[2][1] == K.aerobic.P_LOW


def test_set_works_on_an_option_backed_row_and_refuses_an_out_of_range_value():
    import sandbox_options
    out, notes = dials.set_value(text(), "strength.DEFAULTS.ts", "1.5")
    assert any("sandbox_options.py --write" in n for n in notes)
    assert "default = 1.5" in sandbox_options.render(out)
    with pytest.raises(ValueError):
        dials.set_value(text(), "strength.DEFAULTS.ts", "31")


def test_the_protein_knots_must_ascend():
    with pytest.raises(ValueError, match="must ascend"):
        dials.set_value(text(), "strength.PROTEIN_FULL", "1.2")
    out, _ = dials.set_value(text(), "strength.PROTEIN_FULL", "1.5")
    assert dials.check(text=out) == [f for f in dials.check(text=out) if "must ascend" not in f]
    bad = text().replace(*value_edit("strength.PROTEIN_FULL", "1.2"))
    assert any("must ascend" in f for f in dials.check(text=bad))
