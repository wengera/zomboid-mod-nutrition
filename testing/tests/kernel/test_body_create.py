"""The creation body table (Plan 13 Task 9; spec section 3.2; rulings 13-14, 13-30, 13-31, 13-46 and 13-47).

`K.body.create(muscle, weight, P, sexIdx)` against the strength-level reference (`strength_level.trait_start`,
`perfect_run`) and spec section 3.2's kg columns at 1.70 m (2.89 m2), unrounded: the muscle starts through N0 and lean,
the set point and the natural cap moved by the trait share, the cap clamped at the natural FFMI limit, the peak, the
fat and thin weight picks by sex (the fat picks scaled by the start lean over the average's, Task 10b), the rungs,
the anti-stacking exclusions over every legal pick set of the 8 body traits
for both sexes, and `K.body.new` (renamed from `newLean` in Task 12) under ten years of perfect training.
"""
import pytest

from . import strength_level as sl

H2 = 1.70 * 1.70
FAVG = 18.0 * H2   # the untrained average lean, K.strength.fOfBio(5, DEFAULTS)
MUSCLE = (None, "WEAK", "FEEBLE", "STOUT", "STRONG")
WEIGHT = (None, "OVERWEIGHT", "OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT")
THIN = ("UNDERWEIGHT", "VERY_UNDERWEIGHT")
EXCLUDED = {("WEAK", "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"), ("FEEBLE", "UNDERWEIGHT"),
            ("FEEBLE", "VERY_UNDERWEIGHT")}


def _legal(m, w):
    return not (w in THIN and m in ("WEAK", "FEEBLE"))


def _d(host):
    return host.K.strength.DEFAULTS


def _copy(host, **over):
    """A Lua copy of DEFAULTS with the overrides set (the session host is shared, so DEFAULTS is never written)."""
    P = host.rt.table()
    for k, v in _d(host).items():
        P[k] = v
    for k, v in over.items():
        P[k] = v
    return P


SPEC_KEYS = ("lm", "F0", "Fc", "Pk", "N0", "fm", "fatT", "thinT", "sexIdx")


def _spec(host, m, w, P=None, sexIdx=None):
    P = _d(host) if P is None else P
    s = host.call("body.create", m, w, P, sexIdx)
    return {k: s[k] for k in SPEC_KEYS}


# --- the derived limit (amendment 1) ---

def test_the_natural_limit_is_derived_once_from_kouri(host):
    D = _d(host)
    assert D.kouriCoef == sl.KOURI_COEF == 6.3
    assert D.ffmiNaturalRaw == D.ffmiNatural - D.kouriCoef * (1.8 - host.K.HEIGHT_M)
    assert abs(D.ffmiNaturalRaw - sl.FFMI_NATURAL_RAW) < 1e-12
    assert abs(D.ffmiNaturalRaw * H2 - sl.FC_LIMIT) < 1e-12


# --- the brief's tests ---

@pytest.mark.parametrize("muscle", MUSCLE)
def test_muscle_starts_match_the_reference(host, muscle):
    D = _d(host)
    key = muscle or "none"
    s = host.call("body.create", muscle, None, D)
    F, F0, Fc, Pk = sl.trait_start(key)
    for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(s[k] - v) < 1e-12, k
    assert s["N0"] == D["N0"][key] == sl.LEVEL_MODEL["N0"][key]
    L = host.call("strength.level", s["lm"], s["N0"], 1.0, D)
    assert host.call("strength.shown", L)[0] == D["startLevel"][key]
    assert abs(s["fm"] - 4.5 * H2 * F / FAVG) < 1e-9          # Task 10b: 20 % body fat at every start lean
    assert s["fatT"] == 0 and s["thinT"] == 0


@pytest.mark.parametrize("weight, fat_kg, lean", [
    ("OVERWEIGHT", 21.675, None), ("OBESE", 30.345, None),
    ("UNDERWEIGHT", 4.335, 47.685), ("VERY_UNDERWEIGHT", 2.89, 44.795),
])
def test_weight_picks(host, weight, fat_kg, lean):
    D = _d(host)
    s = host.call("body.create", None, weight, D)
    assert abs(s["fm"] - fat_kg) < 1e-9
    assert abs(s["lm"] - (lean if lean is not None else sl.F5)) < 1e-9
    # a weight pick leaves the set point, the cap and the peak where the muscle pick put them
    F, F0, Fc, Pk = sl.trait_start("none")
    for k, v in (("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(s[k] - v) < 1e-12, k


@pytest.mark.parametrize("muscle", MUSCLE)
def test_set_point_and_cap_move_by_the_share(host, muscle):
    D = _d(host)
    s = host.call("body.create", muscle, None, D)
    d = D["traitShare"] * (s["lm"] - sl.F5)
    assert abs(s["F0"] - (sl.F5 + d)) < 1e-9
    lim = (D["ffmiNatural"] - 6.3 * (1.8 - 1.70)) * 1.70 ** 2
    assert abs(s["Fc"] - min(host.call("strength.fOfBio", D["capLevel"], D) + d, lim)) < 1e-9
    assert s["Fc"] <= lim + 1e-9                      # every trait is at most the natural limit
    assert (s["Fc"] == lim) == (muscle in ("STRONG", "STOUT"))   # only Strong's and Stout's are clamped


@pytest.mark.parametrize("muscle", MUSCLE)
def test_the_peak_starts_at_the_larger_of_start_and_set_point(host, muscle):
    s = _spec(host, muscle, None)
    assert s["Pk"] == max(s["lm"], s["F0"])
    # Feeble's and Weak's deconditioned half sits below the peak, on the regain path; the others start at the peak
    assert (s["Pk"] > s["lm"]) == (muscle in ("WEAK", "FEEBLE"))


def test_thin_is_depletion_below_the_peak(host):
    D = _d(host)
    s = host.call("body.create", "STRONG", "VERY_UNDERWEIGHT", D)
    assert s["lm"] < s["F0"] < s["Pk"]
    assert abs(s["Pk"] - sl.trait_start("STRONG")[0]) < 1e-9


@pytest.mark.parametrize("muscle", MUSCLE)
@pytest.mark.parametrize("weight", THIN)
def test_thin_never_raises_lean(host, muscle, weight):
    # ruling 13-14: F = min(F_start, BMI_target * H2 - fat_target), built for excluded pairs too
    s = _spec(host, muscle, weight)
    F = sl.trait_start(muscle or "none")[0]
    t = {"UNDERWEIGHT": (18.0, 1.5), "VERY_UNDERWEIGHT": (16.5, 1.0)}[weight]
    assert abs(s["lm"] - min(F, t[0] * H2 - t[1] * H2)) < 1e-12
    assert s["lm"] <= F


@pytest.mark.parametrize("muscle", MUSCLE)
def test_perfect_training_from_each_start_matches_the_reference(host, muscle):
    D = _d(host)
    key = muscle or "none"
    lm = sl.LEVEL_MODEL
    b = host.call("body.new", host.call("body.create", muscle, None, D), 1, 0)
    ref = sl.perfect_run(key, 3650)
    marks = (1, 28, 70, 182, 365, 730, 1460, 2190, 3650)
    for day in range(1, 3651):
        host.call("strength.day", b, lm["perfectS"], lm["perfectP"], lm["perfectE"] * sl.TDEE, sl.TDEE, 0.0, D, 1.0)
        got = host.call("strength.level", b["lm"], b["N0"], b["T"], D)
        if day in marks:
            assert abs(got - ref[day - 1]) < 1e-9, (key, day)
        if muscle in ("FEEBLE", "WEAK"):
            assert got < 10.0, (key, day)


@pytest.mark.parametrize("weight, fmi", [(None, 7.0), ("OVERWEIGHT", 11.0), ("OBESE", 15.0)])
def test_female_fat_picks_sit_in_the_female_bands(host, weight, fmi):
    D = _d(host)
    s = host.call("body.create", None, weight, D, 2)
    assert abs(s["fm"] - fmi * 1.70 * 1.70) < 1e-9
    assert s["sexIdx"] == 2


@pytest.mark.parametrize("weight, fmi", [(None, 4.5), ("OVERWEIGHT", 7.5), ("OBESE", 10.5)])
@pytest.mark.parametrize("sexIdx", [None, 1])
def test_male_fat_picks_are_the_default(host, weight, fmi, sexIdx):
    s = _spec(host, None, weight, sexIdx=sexIdx)
    assert abs(s["fm"] - fmi * H2) < 1e-9
    assert s["sexIdx"] == 1


@pytest.mark.parametrize("weight", THIN)
def test_thin_fat_is_the_same_for_both_sexes(host, weight):
    assert _spec(host, None, weight, sexIdx=1)["fm"] == _spec(host, None, weight, sexIdx=2)["fm"]
    assert _spec(host, None, weight, sexIdx=1)["lm"] == _spec(host, None, weight, sexIdx=2)["lm"]


@pytest.mark.parametrize("weight, fatT, thinT", [(None, 0, 0), ("OVERWEIGHT", 1, 0), ("OBESE", 2, 0),
                                                  ("UNDERWEIGHT", 0, 1), ("VERY_UNDERWEIGHT", 0, 2)])
@pytest.mark.parametrize("sexIdx", [1, 2])
def test_the_rungs_of_the_weight_pick(host, weight, fatT, thinT, sexIdx):
    s = _spec(host, "STOUT", weight, sexIdx=sexIdx)
    assert (s["fatT"], s["thinT"]) == (fatT, thinT)


def test_emaciated_is_read_as_very_underweight(host):
    # ruling 13-30: Emaciated is read as rung 2; its body is Very Underweight's, the deepest thin row
    for m in MUSCLE:
        assert _spec(host, m, "EMACIATED") == _spec(host, m, "VERY_UNDERWEIGHT")


@pytest.mark.parametrize("prof", [0, 1, 2])
@pytest.mark.parametrize("sexIdx", [1, 2])
def test_creation_pick_sets_every_point_giver_costs_the_body(host, sexIdx, prof):
    # Task 17b: the profession's Strength boost is not a pick, but every point-giving body trait still costs the body
    # at each boost; the exact smallest drop and the free set are prof 0's, and at any boost the free set stays
    # among the excluded pairs
    D = _d(host)

    def body(m, w):
        s = host.call("body.create", m, w, D, sexIdx, prof)
        return host.call("strength.level", s["lm"], s["N0"], 1.0, D), s["fm"], s["fatT"]

    drops = []
    for m in MUSCLE:
        for w in WEIGHT:
            if not _legal(m, w):
                continue
            L, fm, fatT = body(m, w)
            if m in ("WEAK", "FEEBLE"):
                assert L <= body(None, w)[0] - 0.5, (m, w)
                drops.append(body(None, w)[0] - L)
            if w in THIN:
                assert L <= body(m, None)[0] - 0.5, (m, w)
                drops.append(body(m, None)[0] - L)
            if w in ("OVERWEIGHT", "OBESE"):
                _, fm0, fatT0 = body(m, None)
                assert fatT > fatT0 and fm > fm0, (m, w)
    # amendment 4: the smallest level cost of a point-giving pick over the legal sets
    if prof == 0:
        assert abs(min(drops) - 1.249) < 0.0005, min(drops)
    else:
        assert min(drops) >= 0.5, (prof, min(drops))
    # the pairs the rule excludes because they cost nothing
    for m, w in (("WEAK", "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"), ("FEEBLE", "UNDERWEIGHT")):
        if prof == 0:
            assert body(m, w)[0] > body(m, None)[0] - 0.5, (m, w)
    for w in THIN:
        for m in ("WEAK", "FEEBLE"):
            assert host.K.body.EXCLUDES[w][m] is True
    # the zero-cost pairs over every set, legal or not, all sit among the excluded ones
    free = set()
    for m in MUSCLE:
        for w in WEIGHT:
            L = body(m, w)[0]
            if m in ("WEAK", "FEEBLE") and L > body(None, w)[0] - 0.5:
                free.add((m, w))
            if w in THIN and L > body(m, None)[0] - 0.5:
                free.add((m, w))
    if prof == 0:
        assert free == {("WEAK", "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"), ("FEEBLE", "UNDERWEIGHT")}
        # Feeble with Very Underweight would cost 0.68 levels; it is excluded by the same rule (spec section 3.2)
        assert abs((body("FEEBLE", None)[0] - body("FEEBLE", "VERY_UNDERWEIGHT")[0]) - 0.68) < 0.005
    assert free <= EXCLUDED


def test_the_exclusions_are_exactly_the_four_pairs(host):
    got = {(m, w) for w, row in host.py(host.K.body.EXCLUDES).items() for m, on in row.items() if on is True}
    assert got == EXCLUDED
    assert {(m, w) for m in MUSCLE for w in WEIGHT if not _legal(m, w)} == EXCLUDED


# --- the keys create reads, against decoys (amendment 5) ---

def test_create_ignores_decoy_keys(host):
    # keys whose default equals a key create reads (traitShare 0.5 = ffmiPerLevel's, E0_drop's, fbal_drop's,
    # full_drop's, fmMin's, Sg0's), the inputs ffmiNaturalRaw is derived from, and R's own inputs, moved apart
    decoy = _copy(host, E0_drop=0.9, fbal_drop=0.8, full_drop=0.2, fmMin=3.0, Sg0=1.5, ffmiNatural=30.0,
                  kouriCoef=1.0, Tmax=1.5, yearsTo10=2.0, perfectS=9.0, ts=3.0, m=0.9)
    for m in MUSCLE:
        for w in WEIGHT:
            for sx in (1, 2):
                assert _spec(host, m, w, decoy, sx) == _spec(host, m, w, sexIdx=sx), (m, w, sx)


def _expect(host, P, m, w, sexIdx=1):
    """The create formula in Python over the strength kernel's own functions, under the table P."""
    key = m or "none"
    N0 = P.N0[key]
    F = host.call("strength.fOfLevel", P.startLevel[key], N0, 1.0, P)
    F5 = host.call("strength.fOfBio", 5.0, P)
    d = P.traitShare * (F - F5)
    F0 = F5 + d
    Fc = min(host.call("strength.fOfBio", P.capLevel, P) + d, P.ffmiNaturalRaw * H2)
    return F, F0, Fc, max(F, F0), N0


@pytest.mark.parametrize("over", [
    dict(traitShare=0.3), dict(capLevel=14.0), dict(ffmiNaturalRaw=26.0), dict(ffmiNaturalRaw=20.0),
    dict(R=1.9), dict(M5=22.0), dict(Fnm=25.0), dict(b=0.7), dict(ffmi5=17.0), dict(ffmiPerLevel=0.6),
    "N0", "startLevel",
])
def test_create_reads_its_own_keys(host, over):
    if over == "N0":
        t = host.table({"STRONG": 1.2, "STOUT": 1.1, "none": 0.95, "FEEBLE": 0.9, "WEAK": 0.8})
        P = _copy(host, N0=t)
    elif over == "startLevel":
        t = host.table({"STRONG": 8, "STOUT": 6, "none": 4, "FEEBLE": 2, "WEAK": 1.5})
        P = _copy(host, startLevel=t)
    else:
        P = _copy(host, **over)
    moved = False
    for m in MUSCLE:
        s = _spec(host, m, None, P)
        F, F0, Fc, Pk, N0 = _expect(host, P, m, None)
        for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk), ("N0", N0)):
            assert abs(s[k] - v) < 1e-12, (over, m, k)
        moved = moved or any(abs(s[k] - d) > 1e-9 for k, d in _spec(host, m, None).items())
    assert moved, over


# --- the constructor ---

def test_new_lays_the_spec_and_the_surviving_fields(host):
    spec = host.call("body.create", "STRONG", "OBESE", _d(host), 2)
    b = host.call("body.new", spec, 2, 50.0)
    for k in ("lm", "F0", "Fc", "Pk", "N0", "fm", "fatT", "thinT"):
        assert b[k] == spec[k], k
    assert b.fatT == 2 and b.thinT == 0
    assert (b.lx, b.grace, b.sigDay, b.T, b.Tgrace, b.S) == (0, 0, 0, 1, 0, 0)
    assert [b.sig7[i] for i in range(1, 8)] == [0] * 7
    assert b.fmRef == b.fm and b.lm0dis == b.lm
    assert b.sex == 2 and b.bornAge == 50.0 and b.lastAgeH == 50.0 and b.wday == 2 and b.dayIndex == 2
    for i in range(1, 8):
        assert b.mass7[i] == b.lm + b.lx + b.fm
        assert b.eb7[i] == 0 and b.p7[i] == 0
        assert b.bandWeek[i][1] == 0 and b.bandWeek[i][2] == 0
    assert b.trail.at == 50.0 and b.trail.ch == -1
    for k in ("at", "inDay", "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay",
              "metMinDay", "band1Day", "band2Day"):
        assert b[k] == 0, k
    assert (b.tac, b.rmod, b.pPrevKg, b.energyState) == (1.0, 1, 0.8, 1)
    # Task 12's removals are not laid
    for k in ("fm0", "lm0", "l0", "r", "traitCarry", "strAgeH", "vStr", "vHyp", "vStrHigh", "n", "nPeak", "tPeakD",
              "nHist", "cumDef", "shownL", "riseHeldH", "lastFallAge", "delta"):
        assert b[k] is None, k
    # the body owns its fields: no table is shared with the spec
    b.lm = 1.0
    assert spec.lm != 1.0


@pytest.mark.parametrize("m, w, sx", [("STRONG", "OBESE", 2), ("WEAK", None, 1), ("STRONG", "VERY_UNDERWEIGHT", 1)])
def test_new_anchors_and_the_disuse_count(host, m, w, sx):
    # the disuse arm survives Task 12 (its count tDisuse and its anchor lm0dis, spec section 9.2)
    spec = host.call("body.create", m, w, _d(host), sx)
    b = host.call("body.new", spec, sx, 0.0)
    assert b.tDisuse == 0
    assert b.lm0dis == spec.lm and b.fmRef == spec.fm and b.Pk == spec.Pk


def test_the_pick_tables_are_the_enumerated_ones(host):
    # a trait added to a table without the pick-set test enumerating it fails here
    D = host.py(_d(host))
    assert set(D["N0"]) == set(D["startLevel"]) == {m or "none" for m in MUSCLE}
    fat = set(host.py(host.K.body.FAT_FMI)) | set(host.py(host.K.body.THIN))
    assert fat == {w or "none" for w in WEIGHT}
    assert set(host.py(host.K.body.FAT_FMI_F)) == set(host.py(host.K.body.FAT_FMI))


@pytest.mark.parametrize("years", [1.0, 10.0])
@pytest.mark.parametrize("sexIdx", [1, 2])
def test_no_legal_pick_is_free_at_the_option_bounds(host, years, sexIdx):
    # NR.StrengthYearsToLevel10 is the one option that moves the start lean and the level scale (R)
    P = _copy(host, yearsTo10=years, R=host.call("strength.R", years))

    def body(m, w):
        s = host.call("body.create", m, w, P, sexIdx)
        return host.call("strength.level", s["lm"], s["N0"], 1.0, P), s["fm"], s["fatT"]

    for m in MUSCLE:
        for w in WEIGHT:
            if not _legal(m, w):
                continue
            L, fm, fatT = body(m, w)
            if m in ("WEAK", "FEEBLE"):
                assert L <= body(None, w)[0] - 0.5, (m, w)
            if w in THIN:
                assert L <= body(m, None)[0] - 0.5, (m, w)
            if w in ("OVERWEIGHT", "OBESE"):
                _, fm0, fatT0 = body(m, None)
                assert fatT > fatT0 and fm > fm0, (m, w)


# --- Task 17b: a profession's Strength boost starts the body like a small trait ---

PROF = (0, 1, 2)


@pytest.mark.parametrize("prof", PROF)
@pytest.mark.parametrize("muscle", MUSCLE)
def test_profession_boost_matches_the_reference(host, muscle, prof):
    D = _d(host)
    key = muscle or "none"
    s = host.call("body.create", muscle, None, D, None, prof)
    F, F0, Fc, Pk = sl.trait_start(key, prof=prof)
    for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(s[k] - v) < 1e-12, (key, prof, k)
    assert s["N0"] == D["N0"][key]                    # the boost adds no innate factor
    L = host.call("strength.level", s["lm"], s["N0"], 1.0, D)
    assert host.call("strength.shown", L)[0] == min(10, D["startLevel"][key] + prof)


@pytest.mark.parametrize("prof", PROF)
@pytest.mark.parametrize("muscle", MUSCLE)
@pytest.mark.parametrize("weight", THIN)
def test_a_thin_pick_caps_the_boosted_start(host, muscle, weight, prof):
    # the boost raises F before the thin cap: lm = min(F_boosted, BMI * H2 - fat)
    s = host.call("body.create", muscle, weight, _d(host), None, prof)
    F, F0, Fc, Pk = sl.trait_start(muscle or "none", prof=prof)
    t = {"UNDERWEIGHT": (18.0, 1.5), "VERY_UNDERWEIGHT": (16.5, 1.0)}[weight]
    assert abs(s["lm"] - min(F, t[0] * H2 - t[1] * H2)) < 1e-12
    for k, v in (("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(s[k] - v) < 1e-12, k


def test_a_thin_pick_with_a_boost_cuts_more_lean():
    # Feeble +2 starts at level 5 (above Underweight's 47.69 kg), so Underweight now lowers it
    F = sl.trait_start("FEEBLE", prof=2)[0]
    assert F > 18.0 * H2 - 1.5 * H2 > sl.trait_start("FEEBLE")[0]


@pytest.mark.parametrize("prof", [1, 2, 3])
def test_strong_with_a_boost_starts_at_ten(host, prof):
    D = _d(host)
    s = host.call("body.create", "STRONG", None, D, None, prof)
    L = host.call("strength.level", s["lm"], s["N0"], 1.0, D)
    assert abs(L - 10.0) < 1e-9                       # the start level clamped to 10: the native perk is reachable
    assert host.call("strength.shown", L)[0] == 10


def test_none_with_one_starts_at_six(host):
    D = _d(host)
    s = host.call("body.create", None, None, D, None, 1)
    L = host.call("strength.level", s["lm"], s["N0"], 1.0, D)
    assert abs(L - 6.0) < 1e-9 and s["N0"] == 1.0


def test_a_negative_boost_clamps_at_zero(host):
    D = _d(host)
    s = host.call("body.create", "WEAK", None, D, None, -3)
    assert abs(s["lm"] - host.call("strength.fOfLevel", 0, D["N0"]["WEAK"], 1.0, D)) < 1e-12
    assert abs(s["lm"] - sl.trait_start("WEAK", prof=-3)[0]) < 1e-12


@pytest.mark.parametrize("bad", [None, "2", True, float("nan"), float("inf")])
def test_an_unreadable_boost_reads_zero(host, bad):
    D = _d(host)
    for m in MUSCLE:
        for w in (None, "UNDERWEIGHT", "OBESE"):
            got = host.py(host.call("body.create", m, w, D, 1, bad))
            assert got == host.py(host.call("body.create", m, w, D, 1)), (m, w, bad)


# --- Task 10b: the fat starts scale with the start lean (Angus, 2026-10-15) ---

FAT_MID = {1: {None: 4.5, "OVERWEIGHT": 7.5, "OBESE": 10.5}, 2: {None: 7.0, "OVERWEIGHT": 11.0, "OBESE": 15.0}}
BANDS = {1: {None: (3.0, 6.0), "OVERWEIGHT": (6.0, 9.0), "OBESE": (9.0, 12.0)},   # Kelly 2009 male, obese class I
         2: {None: (5.0, 9.0), "OVERWEIGHT": (9.0, 13.0), "OBESE": (13.0, 17.0)}}  # female, obese class I


def test_the_fat_tables(host):
    assert host.py(host.K.body.FAT_FMI) == {"none": 4.5, "OVERWEIGHT": 7.5, "OBESE": 10.5}
    assert host.py(host.K.body.FAT_FMI_F) == {"none": 7.0, "OVERWEIGHT": 11.0, "OBESE": 15.0}


@pytest.mark.parametrize("prof", [0, 1])
@pytest.mark.parametrize("sexIdx", [1, 2])
@pytest.mark.parametrize("weight", [None, "OVERWEIGHT", "OBESE"])
@pytest.mark.parametrize("muscle", MUSCLE)
def test_every_fat_start_sits_mid_band_in_body_fat(host, muscle, weight, sexIdx, prof):
    s = host.call("body.create", muscle, weight, _d(host), sexIdx, prof)
    fmi = FAT_MID[sexIdx][weight]
    lo, hi = BANDS[sexIdx][weight]
    assert lo < fmi < hi and abs(fmi - (lo + hi) / 2) < 1e-12
    assert abs(s["fm"] - fmi * H2 * s["lm"] / FAVG) < 1e-9
    # the body-fat share is the band middle's at the average lean, whatever the start lean
    bf = s["fm"] / (s["fm"] + s["lm"])
    assert abs(bf - fmi / (18.0 + fmi)) < 1e-12
    assert lo / (18.0 + lo) < bf < hi / (18.0 + hi)


@pytest.mark.parametrize("muscle, fat, weight", [
    (None, 30.345, 82.365), ("STRONG", 35.4997538, 96.3564746), ("WEAK", 24.5672261, 66.6824708),
])
def test_the_verified_obese_bodies(host, muscle, fat, weight):
    s = _spec(host, muscle, "OBESE")
    assert abs(s["fm"] - fat) < 1e-6
    assert abs(s["lm"] + s["fm"] - weight) < 1e-6
    assert abs(s["fm"] / (s["lm"] + s["fm"]) - 10.5 / 28.5) < 1e-12   # 36.84 %


def test_a_strong_none_pick_starts_at_20_percent_not_a_fixed_13_kg(host):
    s = _spec(host, "STRONG", None)
    assert abs(s["fm"] - 4.5 * H2 * sl.trait_start("STRONG")[0] / FAVG) < 1e-9
    assert s["fm"] > 15.2
    assert abs(s["fm"] / (s["fm"] + s["lm"]) - 0.2) < 1e-12


@pytest.mark.parametrize("weight", THIN)
@pytest.mark.parametrize("muscle", (None, "STOUT", "STRONG"))
def test_thin_fat_is_not_scaled(host, muscle, weight):
    s = _spec(host, muscle, weight)
    assert s["fm"] == host.K.body.THIN[weight].fmi * H2
