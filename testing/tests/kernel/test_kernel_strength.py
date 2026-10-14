"""The functional factor, the ceiling, the write policy, the carry factor and the band remap
(NR_Kernel_Strength.lua), Plan 3 Task 10.

NR_Kernel_Strength.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.strength. Every expectation below is
hand-computed from the file's constants: the neural target 0.18 x dStr (S0585); the rising, falling and
immobilised time constants 14, 60 and 10 days (S0086; S0655 open, design-phase-v1; S0070/S0612); the
memory floor 0.80 x exp(-dt/300) after 14 days held (S0655 open, design-phase-v1); the cumulative deficit's
10-day decay, 50000 kcal full scale and -0.10 (S0601, S0602); the disuse residual -0.325 ln(1 + t/22)
(fitted to S0070); the factor clamp [0.55, 1.25] and 10 levels per doubling (game choices); L_MAX 10
(#2118, ruling 9); the write policy's 6 h rise hold and 1 h fall spacing (ruling 10); the acute carry
terms (S0623, S0624, S0763, S0762, S0765, S0626, S0633, S0651) clamped [-0.20, 0.03] (a game choice); the
carry delta traitCarry x (1 + eAcute) (ruling 11); the band remap WEAK 0-1, FEEBLE 2-4, none 5, STOUT
6-8, STRONG >= 9 (#2157).
"""
import math

import pytest

TOL = 1e-9

# The Strength XP ladder: getTotalXpForLevel(L) for L = 1..10 (#2102). 37500 is level 5's total, 67500
# level 6's; getTotalXpForLevel(11) == getTotalXpForLevel(10) (#2859), so the Java cap is 10 (#2118).
LADDER = [1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500]


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _ring(values):
    return {i + 1: v for i, v in enumerate(values)}


def _body(host, **kw):
    d = dict(n=0.0, nPeak=0.0, tPeakD=0, nHist=_ring([0.0] * 14), cumDef=0.0, tDisuse=0, ebDay=0.0,
             shownL=5, riseHeldH=0.0, lastFallAge=0.0)
    d.update(kw)
    return host.table(d)


# --- constants ---

def test_constants(host):
    s = host.K.strength
    assert s.N_TARGET_K == 0.18 and s.TAU_RISE == 14 and s.TAU_FALL == 60 and s.TAU_IMMOB == 10
    assert s.MEM_RETAIN == 0.80 and s.MEM_TAU == 300 and s.MEM_HOLD_DAYS == 14
    assert s.CUMDEF_TAU == 10 and s.CUMDEF_FULL == 50000 and s.E_ENERGY_MAX == -0.10
    assert s.DISUSE_K == -0.325 and s.DISUSE_T == 22
    assert s.F_MIN == 0.55 and s.F_MAX == 1.25 and s.LEVELS_PER_DOUBLING == 10 and s.L_MAX == 10
    assert s.RISE_HOLD_H == 6 and s.FALL_MIN_H == 1
    assert s.DEHYD_STEP1 == -0.03 and s.DEHYD_STEP2 == -0.06
    assert s.DEHYD_PCT1 == 2 and s.DEHYD_PCT2 == 4 and s.DEHYD_SWEAT_K == 1.5
    assert s.SLEEP_KNEE_H == 18 and s.SLEEP_PER_H == -0.004 and s.SLEEP_CAP == -0.08
    assert s.SLEEP_AM_FACTOR == 0.5 and s.AM_FROM_H == 6 and s.AM_TO_H == 12
    assert s.CAFFEINE_BONUS == 0.02 and s.VITD_PENALTY == -0.03
    assert s.FAT_PER_10PT == -0.03 and s.FAT_KNEE == 0.30 and s.FAT_PER_PTS == 0.10
    assert s.E_ACUTE_MIN == -0.20 and s.E_ACUTE_MAX == 0.03


def test_bands_table(host):
    bands = host.py(host.K.strength.BANDS)
    assert [bands[i][1] for i in range(1, 6)] == [1, 4, 5, 8, 10]
    assert [bands[i].get(2) for i in range(1, 6)] == ["WEAK", "FEEBLE", None, "STOUT", "STRONG"]


# --- the neural term ---

def test_neural_rises_toward_target_over_one_tau(host):
    b = _body(host)
    host.K.strength.neuralStep(b, 0.5, False, False, 14)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)))


def test_neural_rise_composes_per_minute(host):
    b = _body(host)
    for _ in range(14 * 24):
        host.K.strength.neuralStep(b, 0.5, False, False, 1 / 24)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)), 1e-12)


def test_neural_falling_maintained_holds(host):
    b = _body(host, n=0.09)
    host.K.strength.neuralStep(b, 0.0, True, False, 30)
    assert b.n == 0.09


def test_neural_maintained_does_not_hold_a_rise(host):
    b = _body(host)
    host.K.strength.neuralStep(b, 0.5, True, False, 14)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)))


def test_neural_falling_immobilised_uses_tau_10(host):
    b = _body(host, n=0.1)
    host.K.strength.neuralStep(b, 0.0, False, True, 10)
    assert _close(b.n, 0.1 * math.exp(-1))


def test_neural_falling_uses_tau_60(host):
    b = _body(host, n=0.1)
    host.K.strength.neuralStep(b, 0.0, False, False, 60)
    assert _close(b.n, 0.1 * math.exp(-1))


def test_neural_at_target_unchanged(host):
    b = _body(host, n=0.09)
    host.K.strength.neuralStep(b, 0.5, False, False, 5)
    assert _close(b.n, 0.09)


# --- the day close: the ring, the held peak, the cumulative deficit ---

def test_close_day_peak_after_fourteen_days_held(host):
    b = _body(host, n=0.09)
    for d in range(1, 14):
        host.K.strength.closeDay(b, d)
        assert b.nPeak == 0
    host.K.strength.closeDay(b, 14)
    assert _close(b.nPeak, 0.09) and b.tPeakD == 14
    hist = host.py(b.nHist)
    assert [hist[i] for i in range(1, 15)] == [0.09] * 14


def test_close_day_one_high_day_then_zeros_no_peak(host):
    b = _body(host, n=0.09)
    host.K.strength.closeDay(b, 1)
    b.n = 0.0
    for d in range(2, 30):
        host.K.strength.closeDay(b, d)
    assert b.nPeak == 0 and b.tPeakD == 0


def test_close_day_ring_shifts_oldest_out(host):
    b = _body(host, nHist=_ring([float(i) for i in range(1, 15)]), n=99.0)
    host.K.strength.closeDay(b, 3)
    hist = host.py(b.nHist)
    assert [hist[i] for i in range(1, 15)] == [float(i) for i in range(2, 15)] + [99.0]
    assert b.nPeak == 2.0 and b.tPeakD == 3


def test_close_day_peak_not_lowered(host):
    b = _body(host, nPeak=0.2, tPeakD=5, n=0.09, nHist=_ring([0.09] * 14))
    host.K.strength.closeDay(b, 40)
    assert b.nPeak == 0.2 and b.tPeakD == 5


def test_cum_def_decays_and_adds_deficit(host):
    b = _body(host, cumDef=10000.0, ebDay=-800.0)
    host.K.strength.closeDay(b, 1)
    assert _close(b.cumDef, 10000 * math.exp(-0.1) + 800)


def test_cum_def_surplus_only_decays(host):
    b = _body(host, cumDef=10000.0, ebDay=600.0)
    host.K.strength.closeDay(b, 1)
    assert _close(b.cumDef, 10000 * math.exp(-0.1))


# --- the memory floor and the slow factor ---

def test_floor_at_peak_day(host):
    b = _body(host, nPeak=0.1, tPeakD=50)
    assert _close(host.K.strength.floorF(b, 50), 1.08)


def test_floor_three_hundred_days_later(host):
    b = _body(host, nPeak=0.1, tPeakD=50)
    assert _close(host.K.strength.floorF(b, 350), 1 + 0.08 * math.exp(-1))


def test_fslow_replete(host):
    assert _close(host.K.strength.fSlow(_body(host), 10), 1.0)


def test_fslow_neural(host):
    assert _close(host.K.strength.fSlow(_body(host, n=0.09), 10), 1.09)


def test_fslow_floor_wins_over_lower_n(host):
    b = _body(host, n=0.0, nPeak=0.1, tPeakD=10)
    assert _close(host.K.strength.fSlow(b, 10), 1.08)


def test_fslow_cum_def_half(host):
    assert _close(host.K.strength.fSlow(_body(host, cumDef=25000.0), 10), 0.95)


def test_fslow_cum_def_saturates(host):
    assert _close(host.K.strength.fSlow(_body(host, cumDef=90000.0), 10), 0.90)


def test_fslow_disuse_day_5(host):
    got = host.K.strength.fSlow(_body(host, tDisuse=5), 10)
    assert _close(got, 1 + (-0.325 * math.log(1 + 5 / 22)))
    assert abs(got - 0.933443) < 2e-6  # the plan rounds ln(1.227273); exact 0.9334418


@pytest.mark.parametrize("kw, want", [
    (dict(n=0.5), 1.25),
    (dict(tDisuse=400, cumDef=60000.0), 0.55),
])
def test_fslow_clamps(host, kw, want):
    assert _close(host.K.strength.fSlow(_body(host, **kw), 10), want)


# --- the ceiling ---

@pytest.mark.parametrize("l0, lm, lm0, f, want", [
    (5, 65.6, 65.6, 1, 5),
    (5, 78.72, 65.6, 1, 8),
    (5, 59.04, 65.6, 0.95, 3),
    (9, 131.2, 65.6, 1, 10),
    (1, 20, 65.6, 0.55, 0),
])
def test_ceiling(host, l0, lm, lm0, f, want):
    assert host.K.strength.ceiling(l0, lm, lm0, f) == want


# --- the XP-implied level ---

@pytest.mark.parametrize("xp, want", [
    (0, 0), (1499, 0), (1500, 1), (19499, 3), (20000, 4), (37500, 5), (67499, 5), (67500, 6),
    (487499, 9), (487500, 10), (500000, 10),
])
def test_xp_level(host, xp, want):
    assert host.K.strength.xpLevel(xp, host.table(_ring(LADDER))) == want


# --- the write policy ---

def test_policy_falls_one_level_per_hour(host):
    s = host.K.strength
    b = _body(host, shownL=5, lastFallAge=0.0)
    assert s.policy(b, 5, 3, 100, 1 / 60) == 4
    assert b.shownL == 4 and b.lastFallAge == 100
    assert s.policy(b, 5, 3, 100 + 10 / 60, 10 / 60) == 4
    assert s.policy(b, 5, 3, 101, 50 / 60) == 3
    assert b.lastFallAge == 101
    assert s.policy(b, 5, 3, 102, 1) == 3


def test_policy_rises_one_level_after_six_hours_held(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    got = [s.policy(b, 7, 8, 100 + h, 1) for h in range(1, 7)]
    assert got == [5, 5, 5, 5, 5, 6]
    assert b.riseHeldH == 0 and b.shownL == 6


def test_policy_rise_hold_resets_when_ceiling_drops(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    for h in range(1, 6):
        s.policy(b, 7, 8, 100 + h, 1)
    assert b.riseHeldH == 5
    s.policy(b, 7, 5, 106, 1)
    assert b.riseHeldH == 0 and b.shownL == 5


def test_policy_never_above_vanilla(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    for h in range(1, 49):
        assert s.policy(b, 5, 8, 100 + h, 1) == 5


def test_policy_follows_vanilla_down_at_once(host):
    s = host.K.strength
    b = _body(host, shownL=7, lastFallAge=100.0)
    assert s.policy(b, 4, 10, 100.5, 1 / 60) == 4
    assert b.shownL == 4


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


# --- the lean-mass strength model (Plan 13 Task 5; rulings 13-1 and 13-45) ---

# The game constants of DEFAULTS (the plan's first constants block, below point T); xpPerSet 346 is provisional
# until Task 1's calibration run.
GAME = dict(ffmi5=18.0, ffmiPerLevel=0.5, capLevel=16.5, ts=1.0, xpPerSet=346, incidental=0.35, fMinShare=0.35,
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

# The specials: StrengthRate multiplies k (default 1.0), StrengthProteinFull scales the knots (default 1.6).
_SPECIAL_DEFAULT = {"kMul": 1.0, "pFull": 1.6}


def _rows(host):
    t = host.py(host.K.strength.OPTIONS)
    return [[row[j] for j in sorted(row)] for _, row in sorted(t.items())]


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
    assert names[0] == "StrengthTimeScale" and names[-1] == "StrengthPeakHalfLifeYears"


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
        assert tip.strip() and tip.endswith(".") or "Range" in tip, name
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
        if key == "kMul":
            assert abs(P["k"] - D["k"] * v) < 1e-15
        elif key == "pFull":
            for i in (1, 2, 3, 4):
                assert abs(P["fp_knots"][i][1] - D["fp_knots"][i][1] * v / 1.6) < 1e-12
                assert P["fp_knots"][i][2] == D["fp_knots"][i][2]
        elif key == "yearsTo10":
            assert P[key] == v
        else:
            assert P[key] == v, key
    # nothing else moved
    moved = {k for k in D if k not in ("fp_knots", "k", "R") and P[k] != D[k]}
    assert moved == {k for k in want if k not in ("kMul", "pFull")}


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
        if key in ("kMul", "pFull", "yearsTo10", "m"):
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


def test_the_guard_reads_the_servers_cap_level(host):
    # capLevel 20 puts bio level 15 at s = 2/3, where Sg0 1.0 with beta 4 still passes (it fails at the default cap's 0.87)
    P, fell = _params(host, {"StrengthThreshold": 1.0, "StrengthThresholdRise": 4, "StrengthCapLevel": 20})
    assert fell is False and P["beta"] == 4


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
                    if os.path.basename(f).startswith("NR_Kernel"))
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
    assert same(NR.server.options.strength, D)
    NR.server.readOptions("a")
    assert G.NR_CALLS == 1 and not same(NR.server.options.strength, D) and NR.server.options.strength.ts == 1.0
    first = NR.server.options.strength
    for _ in range(5):
        NR.server.readOptions("poll")                          # nothing moved: no rebuild
    assert G.NR_CALLS == 1 and same(NR.server.options.strength, first)
    rt.execute("SandboxVars.NR.StrengthRate = 2.0")
    NR.server.readOptions("poll")
    assert G.NR_CALLS == 2 and NR.server.options.strength.k == 2 * D.k
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
