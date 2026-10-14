"""The strength-level reference (Plan 13 Task 2b; ruling 13-45, with rulings 13-46 and 13-47).

The tracked Python counterpart of the kernel's shown-level model, the reference Tasks 5, 8, 9 and 17 test the kernel
against. It reads Task 2's oracle `strength_model` and nothing else, and needs no package.
- Spec section 2.1: S = ((F - Fnm) / M5)^b * N0 * T and the shown level L = 5 + 5 (S - 1) / (R - 1).
- Spec section 2.4: R, the S of the untrained average after Y years of perfect training at Tmax, read off the growth
  law's full-gate step (the oracle's `fast_grow`) from the average's creation body.
- Spec section 3.2: the trait starts (F, F0, Fc, Pk), Fc clamped at the natural FFMI limit (ruling 13-47).
- Spec sections 4 and 6: the neural factor T, its rise, its grace counter and its decay.
"""
import math

from . import strength_model

# The strength-model block of K.strength.DEFAULTS (the plan's second constants block, ruling 13-45).
LEVEL_MODEL = dict(
    b=0.8,
    Fnm=27.0,
    N0=dict(STRONG=1.14, STOUT=1.07, none=1.0, FEEBLE=0.915, WEAK=0.82),
    startLevel=dict(STRONG=9, STOUT=7, none=5, FEEBLE=3, WEAK=1),
    traitShare=0.5,
    ffmiNatural=25.0,   # kg/m2 normalised to 1.80 m (Kouri 1995, S1915; ruling 13-47)
    Tmax=1.10,
    tauUpWk=3.0,
    tauDownWk=12.0,
    Tgrace_d=21,
    Wsat=5.0,
    yearsTo10=4.0,
    perfectS=20.0,      # hard sets a week
    perfectP=2.0,       # g/kg/day of protein
    perfectE=0.10,      # surplus as a share of TDEE
)

# Kouri 1995's height normalisation, FFMI_norm = FFMI + 6.1 (1.8 - h): a game choice, not yet a settled science row
# (ruling 13-47).
KOURI_COEF = 6.1
KOURI_HEIGHT_M = 1.8
FFMI_NATURAL_RAW = LEVEL_MODEL["ffmiNatural"] - KOURI_COEF * (KOURI_HEIGHT_M - strength_model.H)
FC_LIMIT = FFMI_NATURAL_RAW * strength_model.H2

FAT_KG = 13.005   # the no-pick creation fat, FMI 4.5 at 1.70 m (spec section 3.2)
TDEE = 2600.0

F5 = strength_model.F_of(5.0)
FC5 = strength_model.F_of(16.5)
M5 = F5 - LEVEL_MODEL["Fnm"]

_R_CACHE = {}


def S_of(F, N0, T):
    """General strength (spec section 2.1); 0 at or below Fnm."""
    lm = LEVEL_MODEL
    if F <= lm["Fnm"]:
        return 0.0
    return ((F - lm["Fnm"]) / M5) ** lm["b"] * N0 * T


def R_of(years):
    """The S of the untrained average after `years` of perfect training, at Tmax (spec section 2.4)."""
    body = strength_model.creation(dict(strength_model.POINT_T))
    for _ in range(round(years * 365)):
        body.fast_grow(LEVEL_MODEL["perfectS"])
    return S_of(body.F, 1.0, LEVEL_MODEL["Tmax"])


def _R(R):
    if R is not None:
        return R
    years = LEVEL_MODEL["yearsTo10"]
    if years not in _R_CACHE:
        _R_CACHE[years] = R_of(years)
    return _R_CACHE[years]


def level(F, N0, T, R=None):
    """The shown level, linear in S (spec section 2.1)."""
    R = _R(R)
    return 5.0 + 5.0 * (S_of(F, N0, T) - 1.0) / (R - 1.0)


def F_of_level(L, N0, T, R=None):
    """The lean F at which `level(F, N0, T, R)` is L; Fnm when that level needs S <= 0."""
    R = _R(R)
    lm = LEVEL_MODEL
    S = 1.0 + (L - 5.0) * (R - 1.0) / 5.0
    if S <= 0.0:
        return lm["Fnm"]
    return lm["Fnm"] + M5 * (S / (N0 * T)) ** (1.0 / lm["b"])


def trait_start(trait, R=None):
    """`F, F0, Fc, Pk` of a muscle pick (spec section 3.2; rulings 13-46 and 13-47)."""
    lm = LEVEL_MODEL
    F = F_of_level(lm["startLevel"][trait], lm["N0"][trait], 1.0, R)
    d = lm["traitShare"] * (F - F5)
    F0 = F5 + d
    Fc = min(FC5 + d, FC_LIMIT)
    return F, F0, Fc, max(F, F0)


def neural_day(T, tgrace, S, ts=1.0):
    """One closed day of the neural factor (spec sections 4 and 6) -> `T, tgrace`."""
    lm = LEVEL_MODEL
    if S < strength_model.POINT_T["m"] * lm["Wsat"]:
        tgrace = tgrace + 1
    else:
        tgrace = 0
    if tgrace > lm["Tgrace_d"] / ts:
        T = 1.0 + (T - 1.0) * math.exp(-ts / (7.0 * lm["tauDownWk"]))
    else:
        T = lm["Tmax"] - (lm["Tmax"] - T) * math.exp(-min(1.0, S / lm["Wsat"]) * ts / (7.0 * lm["tauUpWk"]))
    return T, tgrace


def perfect_run(trait, days):
    """The shown level after each of `days` days of perfect training from creation (spec section 2.4's table)."""
    lm = LEVEL_MODEL
    F, F0, Fc, Pk = trait_start(trait)
    body = strength_model.Body(dict(strength_model.POINT_T, exact=True, ts=1.0), 5.0, 16.5, FAT_KG)
    body.F, body.F0, body.Fc, body.Pk = F, F0, Fc, Pk
    N0 = lm["N0"][trait]
    T, tgrace = 1.0, 0
    out = []
    for _ in range(days):
        body.day(lm["perfectS"], lm["perfectP"], lm["perfectE"] * TDEE, TDEE)
        T, tgrace = neural_day(T, tgrace, lm["perfectS"])
        out.append(level(body.F, N0, T))
    return out
