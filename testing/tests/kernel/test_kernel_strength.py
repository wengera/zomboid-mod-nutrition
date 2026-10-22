"""The carry factor and the band remap (NR_Kernel_Strength.lua), Plan 3 Task 10, and the lean-mass strength model's
constants, options and signal ring (Plan 13 Tasks 5, 11 and 12). The Plan 3 neural term, memory floor, cumulative
deficit, disuse residual, ceiling, XP-implied level and write policy are removed in Plan 13 Task 12 (spec section 9.2).

NR_Kernel_Strength.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.strength. Every expectation below is
hand-computed from the file's constants: L_MAX 10 (#2118, ruling 9); the acute carry terms (S0623, S0624, S0763,
S0762, S0765, S0626, S0633, S0651) clamped [-0.20, 0.03] (a game choice); the carry delta's trait factor by band
(WEAK 0.75, FEEBLE 0.9, STOUT 1.25, STRONG 1.5, none 1; #2144, ruling 13-7) x (1 + eAcute) (ruling 11); the band
remap WEAK 0-1, FEEBLE 2-4, none 5, STOUT 6-8, STRONG >= 9 (#2157).
"""
import math

import pytest

TOL = 1e-9

def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _ring(values):
    return {i + 1: v for i, v in enumerate(values)}


# --- constants ---

def test_constants(host):
    s = host.K.strength
    assert s.L_MAX == 10
    assert s.DEHYD_STEP1 == -0.03 and s.DEHYD_STEP2 == -0.06
    assert s.DEHYD_PCT1 == 2 and s.DEHYD_PCT2 == 4 and s.DEHYD_SWEAT_K == 1.5
    assert s.SLEEP_KNEE_H == 18 and s.SLEEP_PER_H == -0.004 and s.SLEEP_CAP == -0.08
    assert s.SLEEP_AM_FACTOR == 0.5 and s.AM_FROM_H == 6 and s.AM_TO_H == 12
    assert s.CAFFEINE_BONUS == 0.02 and s.VITD_PENALTY == -0.03
    assert s.FAT_PER_10PT == -0.03 and s.FAT_KNEE == 0.30 and s.FAT_PER_PTS == 0.10
    assert s.E_ACUTE_MIN == -0.20 and s.E_ACUTE_MAX == 0.03


def test_the_plan_3_model_is_gone(host):
    # spec section 9.2: the neural term, the memory floor, the cumulative deficit, the disuse term, fSlow, the
    # ceiling, the XP-implied level and the write policy, with their constants
    s = host.K.strength
    for name in ("neuralStep", "closeDay", "floorF", "fSlow", "ceiling", "xpLevel", "policy", "N_TARGET_K",
                 "TAU_RISE", "TAU_FALL", "TAU_IMMOB", "MEM_RETAIN", "MEM_TAU", "MEM_HOLD_DAYS", "CUMDEF_TAU",
                 "CUMDEF_FULL", "E_ENERGY_MAX", "DISUSE_K", "DISUSE_T", "F_MIN", "F_MAX", "LEVELS_PER_DOUBLING",
                 "RISE_HOLD_H", "FALL_MIN_H"):
        assert s[name] is None, name


def test_bands_table(host):
    bands = host.py(host.K.strength.BANDS)
    assert [bands[i][1] for i in range(1, 6)] == [1, 4, 5, 8, 10]
    assert [bands[i].get(2) for i in range(1, 6)] == ["WEAK", "FEEBLE", None, "STOUT", "STRONG"]


# --- the band remap ---

@pytest.mark.parametrize("level, want", [
    (0, "WEAK"), (1, "WEAK"), (2, "FEEBLE"), (4, "FEEBLE"), (5, None), (6, "STOUT"), (8, "STOUT"),
    (9, "STRONG"), (10, "STRONG"), (11, "STRONG"),
])
def test_band_of(host, level, want):
    assert host.K.strength.bandOf(level) == want


# --- the acute carry factor ---

def _ea(host, dehyd=0, sweat=False, awake=10, hour=15, caf=False, vitd=False, bf=0.18):
    return host.K.strength.eAcute(dehyd, sweat, awake, hour, caf, vitd, bf)


@pytest.mark.parametrize("kw, want", [
    (dict(), 0.0),
    (dict(dehyd=2), -0.03),
    (dict(dehyd=3.9, sweat=True), -0.045),
    (dict(dehyd=4), -0.06),
    (dict(dehyd=4, sweat=True), -0.09),
    (dict(dehyd=1.9, sweat=True), 0.0),
    (dict(awake=28), -0.04),
    (dict(awake=28, hour=8), -0.02),
    (dict(awake=28, hour=6), -0.02),
    (dict(awake=28, hour=12), -0.04),
    (dict(awake=28, hour=None), -0.04),             # no body clock (sleep off, Plan 16 Task 4): no morning halving
    (dict(awake=28, hour=None, dehyd=2), -0.07),
    (dict(awake=60), -0.08),
    (dict(awake=18), 0.0),
    (dict(caf=True), 0.02),
    (dict(vitd=True), -0.03),
    (dict(bf=0.33), -0.009),
    (dict(bf=0.30), 0.0),
    (dict(dehyd=5, sweat=True, awake=60, vitd=True, bf=0.6), -0.20),
])
def test_e_acute(host, kw, want):
    assert _close(_ea(host, **kw), want)


def test_e_acute_upper_clamp(host):
    s = host.K.strength
    old = s.CAFFEINE_BONUS
    s.CAFFEINE_BONUS = 0.10
    try:
        assert _close(_ea(host, caf=True), 0.03)
    finally:
        s.CAFFEINE_BONUS = old


# --- the carry delta ---

def test_carry_delta(host):
    assert _close(host.K.strength.carryDelta(1.5, -0.1), 1.35)
    assert _close(host.K.strength.carryDelta(0.75, 0.0), 0.75)


def test_trait_carry_table(host):
    # the constructor's own values (#2144; ruling 13-7), brought forward by ruling 13-28
    assert host.py(host.K.strength.TRAIT_CARRY) == dict(WEAK=0.75, FEEBLE=0.9, STOUT=1.25, STRONG=1.5)


@pytest.mark.parametrize("level, want", [
    (0, 0.75), (1, 0.75), (2, 0.9), (4, 0.9), (5, 1), (6, 1.25), (8, 1.25), (9, 1.5), (10, 1.5),
])
def test_trait_carry_reads_the_band_of_a_level(host, level, want):
    assert host.K.strength.traitCarry(level) == want


# --- the signal ring (ruling 13-12) ---

def test_signal_close_shifts_lands_today_and_sums(host):
    b = host.table(dict(sigDay=700.0, sig7=_ring([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])))
    total = host.K.strength.signalClose(b)
    assert host.py(b.sig7) == _ring([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 700.0])
    assert total == 2 + 3 + 4 + 5 + 6 + 7 + 700
    assert b.sigDay == 0


def test_signal_close_includes_todays_slot_in_the_sum(host):
    # the closed week is the six kept days and today's: an all-zero ring with today's 360 reads one set at xpPerSet
    b = host.table(dict(sigDay=360.0, sig7=_ring([0.0] * 7)))
    assert host.K.strength.signalClose(b) / host.K.strength.DEFAULTS.xpPerSet == 1.0
    assert host.K.strength.signalClose(b) == 360.0      # the next close keeps it in slot 6
    assert b.sig7[7] == 0 and b.sig7[6] == 360.0


# --- the immobilised day (rulings 13-13 and 13-35; Task 12 fix round 1) ---

DETRAIN_SPY = r"""
function(body, S, P, ts)
    local K = NutritionRevamp.kernel
    local orig = K.strength.detrain
    local seen = {}
    K.strength.detrain = function(b, S2, s, P2, ts2)
        seen.s = s
        seen.ts = ts2
        seen.kg = orig(b, S2, s, P2, ts2)
        return seen.kg
    end
    seen.status = K.strength.status(body)
    local ok, dFM, dLM = pcall(K.strength.disuseDay, body, S, P, ts)
    K.strength.detrain = orig
    seen.ok, seen.dFM, seen.dLM = ok, dFM, dLM
    return seen
end
"""


def _immobile(host, muscle="STRONG"):
    D = host.K.strength.DEFAULTS
    b = host.K.body["new"](host.K.body.create(muscle, None, D, 1), 1, 0.0)
    b.tDisuse = 1
    b.lm0dis = b.lm
    b.lm = b.F0 + 3.0
    b.grace = 100
    b.lx = 0.5
    b.ebDay = -300.0
    return b


def test_disuse_day_applies_the_disuse_arm_and_discards_detraining(host):
    h = host
    D = h.K.strength.DEFAULTS
    b = _immobile(h)
    lm, fm, Pk, T = b.lm, b.fm, b.Pk, b.T
    seen = h.rt.eval(DETRAIN_SPY)(b, 0.0, D, 1.0)
    assert seen.ok is True
    want_fm, want_lm = h.K.partition.disuse(_immobile(h))
    assert (seen.dFM, seen.dLM) == (want_fm, want_lm) and seen.dLM < 0
    assert b.lm == lm + seen.dLM and b.fm == fm + seen.dFM      # detraining's kg is real and discarded
    assert seen.kg > 0
    assert seen.s == seen.status                                  # detraining reads the day's opening status
    assert b.lx == 0.5 and b.Pk == Pk and b.grace == 101 and b.Tgrace == 1 and b.T == T


def test_disuse_day_keeps_the_floors(host):
    h = host
    D = h.K.strength.DEFAULTS
    b = _immobile(h)
    b.lm = D.fMinShare * b.F0 + 1e-6
    b.fm = D.fmMin + 1e-6
    b.ebDay = -5000.0
    h.K.strength.disuseDay(b, 0.0, D, 1.0)
    assert b.lm == D.fMinShare * b.F0 and b.fm == D.fmMin


def test_disuse_day_steps_the_neural_factor_on_the_clock(host):
    h = host
    D = h.K.strength.DEFAULTS
    a, b = _immobile(h), _immobile(h)
    seen = h.rt.eval(DETRAIN_SPY)(a, 10.0, D, 3.0)
    h.K.strength.disuseDay(b, 10.0, D, 1.0)
    assert seen.ts == 3.0 and a.grace == 0 and a.T > b.T > 1.0


# --- the lean-mass strength model (Plan 13 Task 5; rulings 13-1 and 13-45) ---

# The game constants of DEFAULTS (the plan's first constants block, below point T); xpPerSet 360 is measured
# (run x423-20261015-040740).
GAME = dict(ffmi5=18.0, ffmiPerLevel=0.5, capLevel=16.5, ts=1.0, xpPerSet=360, incidental=0.35, fMinShare=0.35,
            fmMin=0.5, nov_p0=1.6, nov_pspan=0.8, xs_p0=0.8, xs_pspan=0.8)


def test_defaults_game_constants_and_no_stray_key(host):
    from . import strength_model as sm
    from . import strength_level as sl
    D = host.py(host.K.strength.DEFAULTS)
    for k, v in GAME.items():
        assert D[k] == v, k
    want = set(sm.POINT_T) - {"infeasible", "regain_gated", "regain_sum"}
    want |= set(sl.LEVEL_MODEL) | set(GAME) | {"M5", "R", "kouriCoef", "ffmiNaturalRaw"}
    assert set(D) == want


def test_R_ignores_a_server_table(host):
    # R reads DEFAULTS only (ruling 13-45): a server's doubled k passed beside the years changes nothing
    from . import strength_level as sl
    P = host.py(host.K.strength.DEFAULTS)
    P["k"] = 2 * P["k"]
    del P["fp_knots"], P["N0"], P["startLevel"]
    assert _close(host.call("strength.R", 4.0, host.table(P)), sl.R_of(4.0))
    assert _close(host.K.strength.DEFAULTS.R, 1.5651015746939971, 1e-12)


def test_level_five_is_the_untrained_average(host):
    D = host.K.strength.DEFAULTS
    F5 = host.call("strength.fOfBio", 5.0, D)
    assert _close(host.call("strength.level", F5, 1.0, 1.0, D), 5.0, 1e-12)
    assert _close(host.call("strength.strengthOf", F5, 1.0, 1.0, D), 1.0, 1e-12)


def test_f_of_level_below_the_domain_reads_fnm(host):
    from . import strength_level as sl
    D = host.K.strength.DEFAULTS
    for L in (-5.0, -20.0):
        assert host.call("strength.fOfLevel", L, 1.0, 1.0, D) == sl.F_of_level(L, 1.0, 1.0) == 27.0


@pytest.mark.parametrize("L,n,frac", [(10.0, 10, 0), (9.5, 9, 0.5), (0.0, 0, 0), (0.3, 0, 0.3), (9.9999999999, 10, 0),
                                             (7 - 1e-8, 6, 1 - 1e-8)])
def test_shown_edges(host, L, n, frac):
    got_n, got_frac = host.call("strength.shown", L)
    assert got_n == n and _close(got_frac, frac, 1e-12)


def test_status_clamps(host):
    hi = host.table({"lm": 80.0, "F0": 52.0, "Fc": 68.0})
    lo = host.table({"lm": 40.0, "F0": 52.0, "Fc": 68.0})
    inverted = host.table({"lm": 60.0, "F0": 68.0, "Fc": 52.0})
    assert host.call("strength.status", hi) == 1
    assert host.call("strength.status", lo) == 0
    assert host.call("strength.status", inverted) == 0


# --- the strength sandbox options and K.strength.params (Plan 13 Task 11; spec section 10, rulings 13-1, 13-32, 13-45) ---

import os
import re

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_MOD = os.path.join(_REPO, "mod", "NutritionRevamp")
_SANDBOX_TXT = os.path.join(_MOD, "42.21", "media", "sandbox-options.txt")
_SANDBOX_JSON = os.path.join(_MOD, "common", "media", "lua", "shared", "Translate", "EN", "Sandbox.json")
_SERVER = os.path.join(_MOD, "common", "media", "lua", "server")

# The specials: StrengthRate multiplies k (K.strength.RATE, 1.0), StrengthProteinFull scales the knots
# (K.strength.PROTEIN_FULL, 1.6); every other option sets the DEFAULTS key its entry names.
_SPECIAL_DEFAULT = {"RATE": 1.0, "PROTEIN_FULL": 1.6}


def _rows(host):
    """[option name, key, min, max (, True for an integer)] of each K.strength.OPTIONS entry (Plan 19 Task 3f: built at
    load from the registry's param rows, sorted by id)."""
    t = host.py(host.K.strength.OPTIONS)
    out = []
    for _, e in sorted(t.items()):
        out.append([e["opt"], e["key"], e["min"], e["max"]] + ([True] if e.get("int") is True else []))
    return out


def _declared():
    """option name -> dict(type, min, max, default) as the option file declares it."""
    with open(_SANDBOX_TXT, encoding="utf-8") as fh:
        src = fh.read()
    out = {}
    for m in re.finditer(r"option NR\.(\w+)\n\{\n    type = (\w+)(.*?),\n    page", src, re.S):
        d = {"type": m.group(2)}
        for kv in re.findall(r"(min|max|default) = (\S+?)(?:,|$)", m.group(3) + ","):
            d[kv[0]] = float(kv[1]) if kv[1] not in ("true", "false") else kv[1]
        out[m.group(1)] = d
    return out


def _params(host, sv=None):
    P, fell = host.call("strength.params", None if sv is None else host.table(sv))
    return host.py(P), fell


def test_the_option_set_is_the_briefs_34(host):
    names = [r[0] for r in _rows(host)]
    assert len(names) == 34 and len(set(names)) == 34
    with open(_SANDBOX_TXT, encoding="utf-8") as fh:
        declared = [n for n in re.findall(r"option NR\.(\w+)", fh.read()) if n.startswith(("Strength", "LeanLoss"))]
    assert set(declared) == set(names) and len(declared) == 34
    assert declared[0] == "StrengthTimeScale" and declared[-1] == "StrengthPeakHalfLifeYears"


def test_every_option_parses_and_its_declaration_matches_the_kernel_table(host):
    # the option file's type, min, max and default are the kernel table's and DEFAULTS' (ruling 13-1)
    decl = _declared()
    D = host.py(host.K.strength.DEFAULTS)
    for name, key, lo, hi, *integer in _rows(host):
        d = decl[name]
        assert d["type"] == ("integer" if integer else "double"), name
        assert d["min"] == lo and d["max"] == hi, name
        want = _SPECIAL_DEFAULT.get(key, D.get(key))
        assert key in _SPECIAL_DEFAULT or key in D, name
        tol = 0.0005 if key == "m" else 0.0
        assert abs(d["default"] - want) <= tol, (name, d["default"], want)
        assert lo <= d["default"] <= hi, name
    assert decl["SexSpecific"]["type"] == "boolean"
    assert decl["StrengthMaintainShare"]["default"] == 0.333


def test_every_option_has_a_name_and_a_tooltip_stating_its_range(host):
    import json
    with open(_SANDBOX_JSON, "rb") as fh:
        raw = fh.read()
    assert b"\r" not in raw
    tr = json.loads(raw.decode("utf-8"))
    for name, key, lo, hi, *_ in _rows(host):
        assert tr["Sandbox_NR_" + name].strip(), name
        tip = tr["Sandbox_NR_" + name + "_tooltip"]
        assert tip.strip() and tip.endswith("."), name
        assert "Range" in tip, name
    ts = tr["Sandbox_NR_StrengthTimeScale_tooltip"]
    assert "the biology clock: 1.0 is one biological day per game day; weekly sets are still counted over 7 game days" in ts.lower()
    assert "0.1 to 1.0" in tr["Sandbox_NR_StrengthMaintainShare_tooltip"]
    assert " 0 " not in tr["Sandbox_NR_StrengthMaintainShare_tooltip"].replace("0.", "")


def test_no_options_equals_defaults_key_by_key(host):
    D = host.py(host.K.strength.DEFAULTS)
    for sv in (None, {}, {"Unrelated": 1}):
        P, fell = _params(host, sv)
        assert fell is False
        assert set(P) == set(D)
        for k in D:
            assert P[k] == D[k], k


def test_params_returns_a_new_table_with_new_knots(host):
    D = host.K.strength.DEFAULTS
    P, _ = host.call("strength.params", None)
    assert P is not D and P.fp_knots is not D.fp_knots
    P.k = 0
    assert D.k > 0


def _decoy(host):
    """Every option off its default, each to a distinct in-range value (a wrong key read fails)."""
    sv, want = {}, {}
    for i, (name, key, lo, hi, *integer) in enumerate(_rows(host)):
        frac = 0.15 + 0.7 * ((i * 7) % 11) / 11
        v = lo + (hi - lo) * frac
        if integer:
            v = round(v)
        sv[name] = v
        want[key] = v
    return sv, want


def test_decoy_all_options_off_default_each_lands_on_its_own_key(host):
    sv, want = _decoy(host)
    D = host.py(host.K.strength.DEFAULTS)
    P, fell = _params(host, sv)
    assert fell is False
    for key, v in want.items():
        if key == "RATE":
            assert abs(P["k"] - D["k"] * v) < 1e-15
        elif key == "PROTEIN_FULL":
            for i in (1, 2, 3, 4):
                assert abs(P["fp_knots"][i][1] - D["fp_knots"][i][1] * v / 1.6) < 1e-12
                assert P["fp_knots"][i][2] == D["fp_knots"][i][2]
        elif key == "yearsTo10":
            assert P[key] == v
        else:
            assert P[key] == v, key
    # nothing else moved
    moved = {k for k in D if k not in ("fp_knots", "k", "R") and P[k] != D[k]}
    assert moved == {k for k in want if k not in ("RATE", "PROTEIN_FULL")}


def test_strength_rate_doubles_k_and_leaves_R(host):
    D = host.py(host.K.strength.DEFAULTS)
    P, fell = _params(host, {"StrengthRate": 2})
    assert fell is False and P["k"] == 2 * D["k"] and P["R"] == D["R"] and P["M5"] == D["M5"]


def test_protein_full_scales_the_knots_x_only(host):
    D = host.py(host.K.strength.DEFAULTS)
    P, _ = _params(host, {"StrengthProteinFull": 2.4})
    for i in (1, 2, 3, 4):
        assert abs(P["fp_knots"][i][1] - D["fp_knots"][i][1] * 1.5) < 1e-12
        assert P["fp_knots"][i][2] == D["fp_knots"][i][2]
    P, _ = _params(host, {"StrengthProteinFull": 0.1})     # clamps to 1.0
    assert abs(P["fp_knots"][4][1] - 1.0) < 1e-12


def test_a_threshold_over_the_set_cap_falls_back(host):
    D = host.py(host.K.strength.DEFAULTS)
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": 4, "StrengthRate": 3})
    assert fell is True
    assert (P["beta"], P["Sg0"], P["Smax1"]) == (D["beta"], D["Sg0"], D["Smax1"])
    assert P["k"] == 3 * D["k"]       # the rest of the read stands


def test_a_trained_set_cap_alone_can_trip_the_guard(host):
    D = host.py(host.K.strength.DEFAULTS)
    P, fell = _params(host, {"StrengthTrainedSetCap": 8, "StrengthThresholdRise": 4, "StrengthThreshold": 1.0})
    assert fell is True and P["Smax1"] == D["Smax1"]


def test_a_cap_level_of_14_skips_the_guard(host):
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": 4, "StrengthCapLevel": 14})
    assert fell is False and P["beta"] == 4 and P["Sg0"] == 1.0
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": 4, "StrengthCapLevel": 15})
    assert fell is False        # the guard needs capLevel above 15


def test_the_guard_boundary(host):
    # threshold(s15) >= setCap(s15) falls back; a hair under passes. At Sg0 = 1.0 the equality is beta = ln(cap) / s15
    s15 = 10 / (16.5 - 5)
    cap = 30 + (12 - 30) * s15
    beta = math.log(cap) / s15
    assert 0 < beta < 4
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": beta * 0.999})
    assert fell is False and P["beta"] == beta * 0.999
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": beta * 1.001})
    assert fell is True


def test_years_to_level_10_recomputes_R(host):
    from . import strength_level as sl
    P, fell = _params(host, {"StrengthYearsToLevel10": 2})
    assert abs(P["R"] - sl.R_of(2.0)) < 1e-9 and fell is False
    P, _ = _params(host, {})
    assert P["R"] == host.K.strength.DEFAULTS.R


def test_a_rebuild_for_another_option_does_not_run_R_again(host):
    S = host.K.strength
    real = S.R
    host.rt.execute("NR_R_CALLS = 0")
    S.R = host.rt.eval("function(real) return function(y) NR_R_CALLS = NR_R_CALLS + 1; return real(y) end end")(real)
    try:
        calls = lambda: host.G.NR_R_CALLS
        _params(host, {"StrengthYearsToLevel10": 3.37})          # warms the cache for this year
        host.rt.execute("NR_R_CALLS = 0")
        _params(host, {"StrengthYearsToLevel10": 3.37, "StrengthRate": 2})
        _params(host, {"StrengthYearsToLevel10": 3.37, "StrengthTimeScale": 5})
        assert calls() == 0                                     # another leaf changed, the year did not
        _params(host, {"StrengthYearsToLevel10": 5.5})
        assert calls() == 1
        P, _ = _params(host, {})
        assert calls() == 2 and P["R"] == host.K.strength.DEFAULTS.R   # back to the default year: one more run
    finally:
        S.R = real


def test_out_of_range_doubles_clamp_and_integers_read_the_default(host):
    D = host.py(host.K.strength.DEFAULTS)
    for name, key, lo, hi, *integer in _rows(host):
        if key in ("RATE", "PROTEIN_FULL", "yearsTo10", "m"):
            continue
        for bad, expect_clamp in ((lo - 1000, lo), (hi + 1000, hi)):
            P, _ = _params(host, {name: bad, "StrengthThresholdRise": 0})
            if key in ("beta", "Sg0", "Smax1"):
                continue
            if integer:
                assert P[key] == D[key], name
            else:
                assert P[key] == expect_clamp, (name, bad)
    P, _ = _params(host, {"StrengthRate": 99})
    assert P["k"] == 4 * D["k"]
    P, _ = _params(host, {"StrengthRate": -3})
    assert P["k"] == 0.25 * D["k"]
    P, _ = _params(host, {"StrengthYearsToLevel10": 0})
    assert P["yearsTo10"] == 1
    P, _ = _params(host, {"StrengthMaintainShare": 5})
    assert P["m"] == 1.0
    P, _ = _params(host, {"StrengthMaintainShare": 0})
    assert P["m"] == 0.1


def test_a_non_number_option_reads_the_default(host):
    D = host.py(host.K.strength.DEFAULTS)
    P, fell = _params(host, {"StrengthTimeScale": "fast", "StrengthXPPerSet": True, "StrengthTraitShare": float("nan")})
    assert (P["ts"], P["xpPerSet"], P["traitShare"]) == (D["ts"], D["xpPerSet"], D["traitShare"]) and fell is False


def test_maintain_share_near_a_third_is_the_exact_third(host):
    D = host.py(host.K.strength.DEFAULTS)
    for v in (0.333, 0.3326, 0.3334, 0.33349):
        P, _ = _params(host, {"StrengthMaintainShare": v})
        assert P["m"] == D["m"], v
    for v in (0.3324, 0.3336, 0.5):
        P, _ = _params(host, {"StrengthMaintainShare": v})
        assert P["m"] == v, v


def test_pdef_hi_always_exceeds_pdef_lo(host):
    # the partition divides by (pdef_hi - pdef_lo); the option's min sits above pdef_lo
    D = host.py(host.K.strength.DEFAULTS)
    for v in (-5, 0, 0.8, 1.0, 1.19, 1.2, 1.2001):
        P, _ = _params(host, {"LeanLossProteinFull": v})
        assert P["pdef_hi"] > P["pdef_lo"] == D["pdef_lo"]
        assert P["pdef_hi"] == max(1.2, v)
    assert min(r[2] for r in _rows(host) if r[1] == "pdef_hi") > D["pdef_lo"]


def test_the_default_year_does_not_run_R():
    # the cache is seeded from DEFAULTS: on a fresh load, params for the default year never calls R
    from .conftest import LuaHost
    fresh = LuaHost()
    fresh.rt.execute("NutritionRevamp.kernel.strength.R = function() error('R ran') end")
    _params(fresh, {})
    _params(fresh, {"StrengthYearsToLevel10": 4})


def test_the_guard_falls_back_at_exact_equality(host):
    # threshold == setCap falls back (>=); stubbed, since no pair of doubles lands on equality
    S = host.K.strength
    real_t, real_c = S.threshold, S.setCap
    S.threshold = host.rt.eval("function() return 5 end")
    S.setCap = host.rt.eval("function() return 5 end")
    try:
        _, fell = _params(host, {})
        assert fell is True
    finally:
        S.threshold, S.setCap = real_t, real_c


def test_the_guard_reads_the_effective_cap(host):
    # K.body.create holds Fc at the natural limit (bio level 5 + (ffmiNaturalRaw - ffmi5) / ffmiPerLevel, about 17.74),
    # so capLevel 20 guards at 17.74: Sg0 1.0 with beta 4 trips there, and capLevel 17.7 and 20 behave the same
    bad = {"StrengthThreshold": 1.0, "StrengthThresholdRise": 4}
    assert _params(host, dict(bad, StrengthCapLevel=20))[1] is True
    assert _params(host, dict(bad, StrengthCapLevel=17.7))[1] is True
    D = host.py(host.K.strength.DEFAULTS)
    eff = 5 + (D["ffmiNaturalRaw"] - D["ffmi5"]) / D["ffmiPerLevel"]
    assert 17.7 < eff < 17.8
    s15 = 10 / (eff - 5)
    beta = math.log(30 + (12 - 30) * s15) / s15      # equality at Sg0 1.0 under the effective cap
    under = dict(StrengthThreshold=1.0, StrengthThresholdRise=beta * 0.999)
    over = dict(StrengthThreshold=1.0, StrengthThresholdRise=beta * 1.001)
    for cap in (20, 19, 17.8):        # every cap above the natural limit guards the same
        assert _params(host, dict(under, StrengthCapLevel=cap))[1] is False
        assert _params(host, dict(over, StrengthCapLevel=cap))[1] is True
    assert _params(host, dict(under, StrengthCapLevel=20))[0]["beta"] == beta * 0.999


# --- K.readLeaf (Plan 13 ruling 13-32; moved from NR_Server_Options with its clamp rule) ---

def _leaf(host, tbl, *args):
    return host.call("readLeaf", None if tbl is None else host.table(tbl), *args)


def test_read_leaf(host):
    assert _leaf(host, None, "A", 7, 0, 9) == 7                        # no table
    assert _leaf(host, {"A": 3}, "A", 7, 0, 9) == 3
    assert _leaf(host, {"A": 30}, "A", 7, 0, 9) == 7                   # out of range reads the default
    assert _leaf(host, {"A": -1}, "A", 7, 0, 9) == 7
    assert _leaf(host, {"A": 30}, "A", 7, 0, 9, True) == 9             # clamps with clampIt
    assert _leaf(host, {"A": -1}, "A", 7, 0, 9, True) == 0
    assert _leaf(host, {"A": 0}, "A", 7, 0, 9) == 0 and _leaf(host, {"A": 9}, "A", 7, 0, 9) == 9
    assert _leaf(host, {"A": float("nan")}, "A", 7, 0, 9, True) == 7   # NaN
    assert _leaf(host, {"A": "x"}, "A", 7, 0, 9, True) == 7
    assert _leaf(host, {}, "A", 7, 0, 9, True) == 7
    assert _leaf(host, {"A": True}, "A", 7, 0, 9) == 7
    assert _leaf(host, {"A": False}, "A", True) is False               # boolean default
    assert _leaf(host, {"A": 1}, "A", True) is True
    assert _leaf(host, {}, "A", False) is False
    assert _leaf(host, None, "A", True) is True


# --- the options adapter: O.strength rebuilt only when a strength leaf changed ---

def _options_host():
    import lupa.lua51 as lua51
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    shared = os.path.join(_MOD, "common", "media", "lua", "shared")
    files = [os.path.join(shared, "NR_Core.lua")]
    files += sorted(f for f in (os.path.join(shared, n) for n in os.listdir(shared))
                    if os.path.basename(f).startswith("NR_Kernel") or os.path.basename(f) == "NR_Data_Dials.lua")
    files.append(os.path.join(_SERVER, "NR_Server_Options.lua"))
    for path in files:
        with open(path, encoding="utf-8") as fh:
            load(fh.read(), "@" + os.path.basename(path))()
    return rt


def test_the_options_adapter_rebuilds_strength_only_when_a_leaf_changed():
    rt = _options_host()
    rt.execute("""
        NR_LOG = {}
        local NR = NutritionRevamp
        NR.log.say = function(level, msg) NR_LOG[#NR_LOG + 1] = level .. ":" .. msg end
        NR_CALLS = 0
        local real = NR.kernel.strength.params
        NR.kernel.strength.params = function(sv) NR_CALLS = NR_CALLS + 1; return real(sv) end
        SandboxVars = { NR = { Mode = 1, StrengthTimeScale = 1.0 } }
    """)
    G = rt.globals()
    NR = G.NutritionRevamp
    D = NR.kernel.strength.DEFAULTS
    same = rt.eval("rawequal")
    assert NR.server.options.strength.k == D.k and not same(NR.server.options.strength, D)
    NR.server.readOptions("a")
    assert G.NR_CALLS == 1 and not same(NR.server.options.strength, D) and NR.server.options.strength.ts == 1.0
    first = NR.server.options.strength
    for _ in range(5):
        NR.server.readOptions("poll")                          # nothing moved: no rebuild
    assert G.NR_CALLS == 1 and same(NR.server.options.strength, first)
    before = NR.server.options.strength
    rt.execute("SandboxVars.NR.StrengthRate = 2.0")
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 2 and not same(NR.server.options.strength, before) and NR.server.options.strength.k == 2 * D.k
    rt.execute("SandboxVars.NR.Mode = 2")                      # a non-strength leaf: no rebuild
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 2
    assert len(G.NR_LOG) == 0
    rt.execute("SandboxVars.NR.StrengthThreshold = 1.0; SandboxVars.NR.StrengthThresholdRise = 4.0")
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 3 and NR.server.options.strength.beta == D.beta
    assert len(G.NR_LOG) == 1 and G.NR_LOG[1].startswith("1:") and "StrengthThreshold 1" in G.NR_LOG[1]
    NR.server.readOptions("poll")
    assert len(G.NR_LOG) == 1                                  # once: no rebuild, no second line
    rt.execute("SandboxVars.NR.StrengthTimeScale = 0/0")       # a NaN leaf rebuilds once per change
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 4
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 4
    rt.execute("SandboxVars = nil")
    NR.server.readOptions("poll")                              # no table: the last P stands
    assert G.NR_CALLS == 4


# --- the AddXP capture (Plan 13 Task 13; spec section 4, ruling 13-11) ---

@pytest.mark.parametrize("store, f", [(0, 1.0), (60, 1.5), (299.9, 1.5), (300, 1.0), (-301, 0.7), (-300, 1.0)])
def test_protein_factor(host, store, f):
    assert host.call("strength.proteinFactor", store) == f


@pytest.mark.parametrize("store, f", [(50, 1.0), (50.001, 1.5), (-300.001, 0.7), (float("nan"), 1.0)])
def test_protein_factor_edges(host, store, f):
    # #2112: both bounds strict; a NaN store compares false everywhere and reads the neutral 1
    assert host.call("strength.proteinFactor", store) == f


def test_protein_constants(host):
    s = host.K.strength
    assert (s.PROTEIN_LO, s.PROTEIN_HI, s.PROTEIN_HI_FACTOR) == (50, 300, 1.5)
    assert (s.PROTEIN_NEG, s.PROTEIN_NEG_FACTOR) == (-300, 0.7)


def test_capture_divides_the_chain_and_weights_the_source(host):
    D = host.K.strength.DEFAULTS
    assert abs(host.call("strength.capture", 9.0, 60, 2.0, 1.0, True, D) - 3.0) < 1e-12
    assert abs(host.call("strength.capture", 6.0, 0, 1.0, 1.0, False, D) - 6.0 * D["incidental"]) < 1e-12
    assert host.call("strength.capture", -1.0, 0, 1.0, 1.0, True, D) == 0
    assert abs(host.call("strength.capture", 6.0, 0, 0.0, 1.0, True, D) - 6.0) < 1e-12


def test_capture_divides_a_book_above_1_only(host):
    D = host.K.strength.DEFAULTS
    assert abs(host.call("strength.capture", 6.0, 0, 1.0, 3.0, True, D) - 2.0) < 1e-12
    assert abs(host.call("strength.capture", 6.0, 0, 1.0, 0.5, True, D) - 6.0) < 1e-12      # <= 1: not applied
    assert abs(host.call("strength.capture", 6.0, 0, 1.0, 1.0, True, D) - 6.0) < 1e-12


def test_capture_the_low_protein_factor_is_divided_out(host):
    D = host.K.strength.DEFAULTS
    assert abs(host.call("strength.capture", 7.0, -400, 1.0, 1.0, True, D) - 10.0) < 1e-12


@pytest.mark.parametrize("sm", [float("nan"), float("inf"), -2.0, 0.0, "x", None])
def test_capture_a_bad_sandbox_multiplier_reads_1(host, sm):
    D = host.K.strength.DEFAULTS
    assert abs(host.call("strength.capture", 6.0, 0, sm, 1.0, True, D) - 6.0) < 1e-12


@pytest.mark.parametrize("bm", [float("nan"), float("inf"), "x", None])
def test_capture_a_bad_book_multiplier_reads_1(host, bm):
    D = host.K.strength.DEFAULTS
    assert abs(host.call("strength.capture", 6.0, 0, 1.0, bm, True, D) - 6.0) < 1e-12


@pytest.mark.parametrize("amount", [0, -0.0, float("nan"), float("inf"), float("-inf"), "6", None])
def test_capture_a_bad_or_non_positive_amount_is_0(host, amount):
    D = host.K.strength.DEFAULTS
    assert host.call("strength.capture", amount, 0, 1.0, 1.0, True, D) == 0


def test_capture_reads_the_incidental_weight_off_P(host):
    P = host.table({"incidental": 0.5})
    assert abs(host.call("strength.capture", 6.0, 60, 1.0, 1.0, False, P) - 2.0) < 1e-12
    assert abs(host.call("strength.capture", 6.0, 60, 1.0, 1.0, True, P) - 4.0) < 1e-12


# --- the level write (Plan 13 Task 14; spec section 7, rulings 13-9, 13-42) ---

LADDER_T = {0: 0, 1: 1500, 2: 4500, 3: 10500, 4: 19500, 5: 37500, 6: 67500, 7: 127500, 8: 217500, 9: 337500,
            10: 487500}


def test_pin_xp_is_the_level_total_plus_the_fraction(host):
    t = host.table(LADDER_T)
    assert host.call("strength.pinXp", 7, 0.25, t) == 127500 + 0.25 * 90000
    assert host.call("strength.pinXp", 0, 0.5, t) == 750
    assert host.call("strength.pinXp", 9, 0.5, t) == 337500 + 0.5 * 150000
    assert host.call("strength.pinXp", 5, 0, t) == 37500


def test_pin_xp_at_10_parks_at_the_level_9_total(host):
    t = host.table(LADDER_T)
    assert host.call("strength.pinXp", 10, 0, t) == 337500
    assert host.call("strength.pinXp", 10, 0.7, t) == 337500


def test_pin_xp_stays_one_xp_below_the_next_total(host):
    t = host.table(LADDER_T)
    assert host.call("strength.pinXp", 7, 1 - 1e-10, t) <= 217500 - 1
    assert host.call("strength.pinXp", 7, 0.5, t) == 127500 + 0.5 * 90000


def test_raw_xp_divides_the_chain_capture_reads(host):
    s = host.K.strength
    assert abs(s.rawXp(9.0, 60, 2.0, 1.0) - 3.0) < 1e-12
    assert abs(s.rawXp(7.0, -400, 1.0, 1.0) - 10.0) < 1e-12
    assert abs(s.rawXp(6.0, 0, 1.0, 3.0) - 2.0) < 1e-12
    assert abs(s.rawXp(6.0, 0, 1.0, 0.5) - 6.0) < 1e-12                 # a book at or below 1: not applied
    assert abs(s.rawXp(6.0, 0, float("nan"), float("nan")) - 6.0) < 1e-12
    assert abs(s.rawXp(6.0, 0, 0.0, None) - 6.0) < 1e-12


# BeyondTen's cumulative mastery cost from level 10 (Shared.lua:222 shape): 0 at 10, per-level 1000, 1100, ...
MASTERY = r"""
function(perk, target)
    local c = { [10] = 0, [11] = 1000, [12] = 2100, [13] = 3300, [14] = 4600, [15] = 6000 }
    if target <= 10 then return 0 end
    if target > 15 then target = 15 end
    return c[target]
end
"""


def _cost(host):
    f = host.rt.eval(MASTERY)
    return host.rt.eval("function(f) return function(L) return f('Strength', L) end end")(f)


@pytest.mark.parametrize("L, want", [(12.0, 2100), (10.4, 400), (16.2, 6000), (15.0, 6000), (12.5, 2700),
                                     (10.0, 0), (11.9999999999, 2100), (9.5, 0), (14.5, 5300)])
def test_mastery_xp_reads_the_cost_at_the_floor_plus_the_fraction(host, L, want):
    # ruling 13-42: cost(min(floor(L), 15)) + frac (cost(next) - cost(floor(L))); 0 + frac cost(11) on [10, 11)
    assert abs(host.call("strength.masteryXp", L, _cost(host)) - want) < 1e-6


# --- Plan 13 Task 10c: the level-drop hysteresis (Angus, 2026-10-15: "Drop only 0.25 below") ---

@pytest.mark.parametrize("L, Lw, n, frac", [
    (5.0, None, 5, 0), (4.99, None, 4, 0.99),                      # nothing written: shown's floor
    (4.9, 5, 5, 0), (4.76, 5, 5, 0), (4.75, 5, 5, 0),               # within 0.25 below: held, an empty bar
    (4.74, 5, 4, 0.74),                                              # past it: down to floor(L + 0.25)
    (3.8, 5, 4, 0), (3.7, 5, 3, 0.7),                               # several levels at once, to floor(L + 0.25)
    (5.99, 5, 5, 0.99), (6.0, 5, 6, 0), (6.3, 5, 6, 0.3),           # a rise lands at the whole number, not later
    (8.2, 5, 8, 0.2),
    (9.8, 10, 10, 0), (9.76, 10, 10, 0), (9.74, 10, 9, 0.74), (12.3, 10, 10, 0),
    (-0.4, 0, 0, 0), (0.5, 3, 0, 0.5), (2.9, 3, 3, 0),
])
def test_held_level(host, L, Lw, n, frac):
    got_n, got_frac = host.call("strength.heldLevel", L, Lw)
    assert got_n == n and _close(got_frac, frac, 1e-9), (L, Lw, got_n, got_frac)


@pytest.mark.parametrize("Lw", [None, float("nan"), float("inf"), "5", True])
def test_held_level_without_a_finite_written_level_is_shown(host, Lw):
    for L in (4.9, 5.0, 7.3, 10.0, 12.0):
        assert tuple(host.call("strength.heldLevel", L, Lw)) == tuple(host.call("strength.shown", L))


def test_the_drop_margin(host):
    assert host.K.strength.DROP_MARGIN == 0.25


def test_held_level_reads_the_drop_margin(host):
    keep = host.K.strength.DROP_MARGIN
    try:
        host.K.strength.DROP_MARGIN = 0.5
        assert host.call("strength.heldLevel", 4.6, 5)[0] == 5
        assert host.call("strength.heldLevel", 4.49, 5)[0] == 4
        assert host.call("strength.heldLevel", 3.6, 5)[0] == 4         # floor(3.6 + 0.5)
        host.K.strength.DROP_MARGIN = 0
        assert host.call("strength.heldLevel", 4.99, 5)[0] == 4
    finally:
        host.K.strength.DROP_MARGIN = keep


def test_a_small_loss_never_drops_and_a_regain_never_needs_a_margin(host):
    # a day's dip and the next day's regain: the written level never leaves 5, and once past 6 it shows 6 at once
    Lw = 5
    for L in (5.0, 4.9, 4.8, 4.95, 5.2, 5.9):
        Lw = host.call("strength.heldLevel", L, Lw)[0]
        assert Lw == 5, L
    assert host.call("strength.heldLevel", 6.0, Lw)[0] == 6
