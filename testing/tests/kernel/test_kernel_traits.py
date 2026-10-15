"""The body-trait axes with damping (Plan 13 Task 10; spec section 8; rulings 13-15, 13-17, 13-30 and 13-31).

`K.traits.axes(body, sex)` reads the lean-scaled fat index fm / (H2 * lm / Favg) against Kelly 2009's FMI cuts (S2056
male, S2057 female, the female table only for effective sex 2; Task 10b, Angus 2026-10-15: a cut and its margin scale
with the body's lean lm over the untrained average's Favg, so the male cuts sit at 25 % and 33.3 % body fat for every
lean) and the BMI (lm + fm) / H2 against WHO's thinness grades (S2059), each with
its game-choice margin; a thinness rung excludes the fat rungs. `K.traits.held` is the damped step, `K.traits.WANT`
the five weight-band trait names. The constants are also read through decoy copies, so a test passes only when the
kernel reads the table it is handed.
"""
import pytest

H2 = 1.70 * 1.70
FAVG = 18.0 * H2   # the untrained average lean, K.strength.fOfBio(5, DEFAULTS): 52.02 kg at 1.70 m
NAMES = ("OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED")
MUSCLE = (None, "WEAK", "FEEBLE", "STOUT", "STRONG")
WEIGHT = (None, "OVERWEIGHT", "OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED")
WORD = {None: "normal", "OVERWEIGHT": "overweight", "OBESE": "obese", "UNDERWEIGHT": "underweight",
        "VERY_UNDERWEIGHT": "veryUnderweight", "EMACIATED": "veryUnderweight"}
EXCLUDED = {("WEAK", "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"), ("WEAK", "EMACIATED"),
            ("FEEBLE", "UNDERWEIGHT"), ("FEEBLE", "VERY_UNDERWEIGHT"), ("FEEBLE", "EMACIATED")}


def _b(host, fm, lm, fatT=0, thinT=0, lx=0):
    return host.table({"fm": fm, "lm": lm, "fatT": fatT, "thinT": thinT, "lx": lx})


def _fmi(host, fmi, fatT=0, sex=1):
    """The word at a fat-mass index for a body at the average lean (its BMI well above the thin cuts)."""
    b = _b(host, fmi * H2, FAVG, fatT=fatT)
    return host.call("traits.axes", b, sex), b["fatT"]


def _bmi(host, bmi, thinT=0):
    """The word at a BMI with a fat-mass index of 1 (far below every fat cut)."""
    b = _b(host, 1.0 * H2, (bmi - 1.0) * H2, thinT=thinT)
    return host.call("traits.axes", b, 1), b["thinT"]


def _held(host, rung, x, cuts, margin, up):
    return host.call("traits.held", rung, x, host.table(dict(enumerate(cuts, 1))), margin, up)


# --- the brief's tests ---

def test_overweight_needs_the_margin(host):
    b = _b(host, 6.2 * H2, FAVG)
    assert host.call("traits.axes", b, 1) == "normal"
    b = _b(host, 6.4 * H2, FAVG)
    assert host.call("traits.axes", b, 1) == "overweight"


def test_overweight_holds_inside_the_margin_on_the_way_back(host):
    b = _b(host, 5.8 * H2, FAVG, fatT=1)
    assert host.call("traits.axes", b, 1) == "overweight"
    b = _b(host, 5.6 * H2, FAVG, fatT=1)
    assert host.call("traits.axes", b, 1) == "normal"


def test_thinness_excludes_the_fat_traits(host):
    b = _b(host, 7.0 * H2, 44.0 - 7.0 * H2, fatT=1)   # BMI 15.2 with FMI 7: thin wins
    assert host.call("traits.axes", b, 1) == "emaciated"
    assert b["fatT"] == 0


def test_creation_picks_sit_inside_their_held_ranges(host):
    D = host.K.strength.DEFAULTS
    for muscle, weight, word in ((None, "UNDERWEIGHT", "underweight"), (None, "VERY_UNDERWEIGHT", "veryUnderweight"),
                                 (None, "OVERWEIGHT", "overweight"), (None, "OBESE", "obese"), ("STOUT", "UNDERWEIGHT", "underweight")):
        for sexIdx in (1, 2):
            s = host.call("body.create", muscle, weight, D, sexIdx)
            assert host.call("traits.axes", s, sexIdx) == word


# --- the constants ---

def test_the_constants(host):
    T = host.py(host.K.traits)
    assert T["FAT_CUTS"] == {1: {1: 6, 2: 9}, 2: {1: 9, 2: 13}}
    assert T["FAT_WORDS"] == {1: "overweight", 2: "obese"}
    assert T["FAT_MARGIN"] == 0.3
    assert T["THIN_CUTS"] == {1: 18.5, 2: 17, 3: 16}
    assert T["THIN_WORDS"] == {1: "underweight", 2: "veryUnderweight", 3: "emaciated"}
    assert T["THIN_MARGIN"] == 0.5


# --- held: the damped step ---

@pytest.mark.parametrize("rung, x, want", [
    (0, 6.29, 0), (0, 6.31, 1), (0, 9.29, 1), (0, 9.31, 2),          # deeper only past cut + margin, several rungs at once
    (1, 5.71, 1), (1, 5.69, 0), (1, 9.29, 1), (1, 9.31, 2),
    (2, 8.71, 2), (2, 8.69, 1), (2, 5.69, 0), (2, 20.0, 2),          # back only past cut - margin, several rungs at once
])
def test_held_up(host, rung, x, want):
    assert _held(host, rung, x, (6, 9), 0.3, True) == want


@pytest.mark.parametrize("rung, x, want", [
    (0, 18.01, 0), (0, 17.99, 1), (0, 16.49, 2), (0, 15.49, 3),
    (1, 18.99, 1), (1, 19.01, 0), (1, 16.51, 1), (1, 16.49, 2),
    (2, 17.49, 2), (2, 17.51, 1), (2, 19.01, 0), (2, 15.51, 2), (2, 15.49, 3),
    (3, 16.49, 3), (3, 16.51, 2), (3, 19.01, 0), (3, 5.0, 3),
])
def test_held_down(host, rung, x, want):
    assert _held(host, rung, x, (18.5, 17, 16), 0.5, False) == want


def test_held_is_strict_at_the_margin(host):
    # "by more than margin": exactly representable readings that sit on cut +/- margin move nothing
    assert _held(host, 0, 6.5, (6, 9), 0.5, True) == 0
    assert _held(host, 1, 5.5, (6, 9), 0.5, True) == 1
    assert _held(host, 0, 17.5, (18, 17), 0.5, False) == 0
    assert _held(host, 1, 18.5, (18, 17), 0.5, False) == 1


def test_held_reads_its_arguments(host):
    # a decoy table and margin whose values coincide with none of the module's
    assert _held(host, 0, 1.11, (1, 2), 0.1, True) == 1
    assert _held(host, 0, 1.09, (1, 2), 0.1, True) == 0
    assert _held(host, 0, 2.2, (1, 2), 0.1, True) == 2
    assert _held(host, 2, 0.95, (1, 2), 0.1, True) == 1
    assert _held(host, 0, 0.0, (1, 0.5, 0.25), 0.2, False) == 3
    assert _held(host, 3, 1.3, (1, 0.5, 0.25), 0.2, False) == 0
    assert _held(host, 0, 0.75, (1, 0.5, 0.25), 0.2, False) == 1


# --- axes: each cut and margin, through the effective sex ---

@pytest.mark.parametrize("fmi, fatT, want", [
    (6.29, 0, "normal"), (6.31, 0, "overweight"), (9.29, 0, "overweight"), (9.31, 0, "obese"),
    (5.71, 1, "overweight"), (5.69, 1, "normal"), (8.71, 2, "obese"), (8.69, 2, "overweight"), (5.69, 2, "normal"),
])
def test_male_fat_cuts(host, fmi, fatT, want):
    assert _fmi(host, fmi, fatT, 1) == (want, ["normal", "overweight", "obese"].index(want))


@pytest.mark.parametrize("fmi, fatT, want", [
    (9.29, 0, "normal"), (9.31, 0, "overweight"), (13.29, 0, "overweight"), (13.31, 0, "obese"),
    (8.71, 1, "overweight"), (8.69, 1, "normal"), (12.71, 2, "obese"), (12.69, 2, "overweight"),
])
def test_female_fat_cuts(host, fmi, fatT, want):
    assert _fmi(host, fmi, fatT, 2) == (want, ["normal", "overweight", "obese"].index(want))


def test_the_female_table_is_read_only_for_effective_sex_2(host):
    # the caller passes K.body.effSex: with NR.SexSpecific off every character arrives as 1
    assert _fmi(host, 9.4, 0, 1) == ("obese", 2)
    assert _fmi(host, 9.4, 0, 2) == ("overweight", 1)
    assert _fmi(host, 7.0, 0, 1) == ("overweight", 1)
    assert _fmi(host, 7.0, 0, 2) == ("normal", 0)
    assert _fmi(host, 9.4, 0, None) == ("obese", 2)


@pytest.mark.parametrize("bmi, thinT, want", [
    (18.01, 0, "normal"), (17.99, 0, "underweight"), (16.51, 0, "underweight"), (16.49, 0, "veryUnderweight"),
    (15.51, 0, "veryUnderweight"), (15.49, 0, "emaciated"),
    (18.99, 1, "underweight"), (19.01, 1, "normal"), (17.49, 2, "veryUnderweight"), (17.51, 2, "underweight"),
    (16.49, 3, "emaciated"), (16.51, 3, "veryUnderweight"),
])
def test_thin_cuts(host, bmi, thinT, want):
    words = ["normal", "underweight", "veryUnderweight", "emaciated"]
    assert _bmi(host, bmi, thinT) == (want, words.index(want))


def test_the_bmi_is_lean_plus_fat_without_the_labile_lean(host):
    # ruling 13-15: lx rides in the weight slot but never counts toward thinness, nor toward the fat index
    b = _b(host, 1.0 * H2, 15.4 * H2, lx=5.0)                   # BMI 16.4 from lm + fm; 18.13 with lx
    assert host.call("traits.axes", b, 1) == "veryUnderweight"
    b = _b(host, 7.0 * H2, 44.0 - 7.0 * H2, lx=5.0)             # BMI 15.2 from lm + fm; FMI 7 with or without lx
    assert host.call("traits.axes", b, 1) == "emaciated"
    b = _b(host, 6.2 * H2, 52.0, lx=5.0)                        # FMI 6.2: lx is lean, not fat
    assert host.call("traits.axes", b, 1) == "normal"
    # the fat counts: lean 50 alone is BMI 17.3, with 13 kg of fat 21.8
    b = _b(host, 13.0, 50.0)
    assert host.call("traits.axes", b, 1) == "normal"


def test_precedence_clears_a_held_fat_rung(host):
    b = _b(host, 12.0 * H2, (16.0 - 12.0) * H2, fatT=2, thinT=1)   # FMI 12, BMI 16: thin holds, fat cleared
    assert host.call("traits.axes", b, 1) == "veryUnderweight"
    assert (b["fatT"], b["thinT"]) == (0, 2)
    # back out of thinness, the fat axis is read afresh from 0
    b = _b(host, 12.0 * H2, 52.0, fatT=0, thinT=1)
    assert host.call("traits.axes", b, 1) == "obese"
    assert (b["fatT"], b["thinT"]) == (2, 0)
    b = _b(host, 6.5 * H2, (17.9 - 6.5) * H2, fatT=1)   # BMI 17.9, FMI 6.5: Underweight clears Overweight
    assert host.call("traits.axes", b, 1) == "underweight"
    assert (b["fatT"], b["thinT"]) == (0, 1)


def test_axes_reads_its_tables(host):
    T = host.K.traits
    keep = {k: T[k] for k in ("FAT_CUTS", "FAT_WORDS", "FAT_MARGIN", "THIN_CUTS", "THIN_WORDS", "THIN_MARGIN")}
    keepH = host.K.HEIGHT_M
    try:
        T.FAT_CUTS = host.table({1: {1: 2, 2: 3}, 2: {1: 4, 2: 5}})
        T.FAT_WORDS = host.table({1: "fatA", 2: "fatB"})
        T.FAT_MARGIN = 0.1
        T.THIN_CUTS = host.table({1: 30, 2: 29, 3: 28})
        T.THIN_WORDS = host.table({1: "thinA", 2: "thinB", 3: "thinC"})
        T.THIN_MARGIN = 0.2
        s = 40.0 * H2 / FAVG                                      # the fat index scales with lean (Task 10b)
        assert host.call("traits.axes", _b(host, 2.05 * H2 * s, 40.0 * H2), 1) == "normal"
        assert host.call("traits.axes", _b(host, 2.15 * H2 * s, 40.0 * H2), 1) == "fatA"
        assert host.call("traits.axes", _b(host, 3.15 * H2 * s, 40.0 * H2), 1) == "fatB"
        assert host.call("traits.axes", _b(host, 4.15 * H2 * s, 40.0 * H2), 2) == "fatA"
        assert host.call("traits.axes", _b(host, 5.15 * H2 * s, 40.0 * H2), 2) == "fatB"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 28.75 * H2), 1) == "thinA"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 27.75 * H2), 1) == "thinB"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 26.75 * H2), 1) == "thinC"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 28.95 * H2), 1) == "normal"
        for k, v in keep.items():
            T[k] = v
        host.K.HEIGHT_M = 2.0                                      # H2 = 4: the average lean is 18 * 4 = 72 kg
        assert host.call("traits.axes", _b(host, 6.4 * H2, 72.0), 1) == "normal"
        assert host.call("traits.axes", _b(host, 6.4 * 4.0, 72.0), 1) == "overweight"
        assert host.call("traits.axes", _b(host, 1.0 * 4.0, 17.9 * 4.0 - 4.0), 1) == "underweight"  # BMI 17.9 at 2 m
    finally:
        for k, v in keep.items():
            T[k] = v
        host.K.HEIGHT_M = keepH
    assert host.call("traits.axes", _b(host, 6.4 * H2, FAVG), 1) == "overweight"


# --- WANT ---

@pytest.mark.parametrize("fatT, thinT, on", [
    (0, 0, ()), (1, 0, ("OVERWEIGHT",)), (2, 0, ("OBESE",)),
    (0, 1, ("UNDERWEIGHT",)), (0, 2, ("VERY_UNDERWEIGHT",)), (0, 3, ("EMACIATED",)),
])
def test_want(host, fatT, thinT, on):
    w = host.py(host.call("traits.WANT", fatT, thinT))
    assert set(w) == set(NAMES)
    for n in NAMES:
        assert w[n] is (n in on), n


# --- the creation picks and the constructor ---

@pytest.mark.parametrize("sexIdx", [1, 2])
@pytest.mark.parametrize("muscle, weight", [(m, w) for m in MUSCLE for w in WEIGHT if (m, w) not in EXCLUDED])
def test_every_legal_creation_pick_keeps_its_rung(host, muscle, weight, sexIdx):
    # the excluded pairs (ruling 13-46) are left out: Weak with Underweight sits at BMI 16.07 and reads Very Underweight
    s = host.call("body.create", muscle, weight, host.K.strength.DEFAULTS, sexIdx)
    fatT, thinT = s["fatT"], s["thinT"]
    assert host.call("traits.axes", s, sexIdx) == WORD[weight]
    assert (s["fatT"], s["thinT"]) == (fatT, thinT)


@pytest.mark.parametrize("muscle, weight, sexIdx", [
    (None, None, 1), ("STRONG", "OBESE", 2), (None, "OVERWEIGHT", 1), ("STOUT", "UNDERWEIGHT", 2),
    (None, "EMACIATED", 1),
])
def test_new_lays_the_band(host, muscle, weight, sexIdx):
    spec = host.call("body.create", muscle, weight, host.K.strength.DEFAULTS, sexIdx)
    b = host.call("body.new", spec, sexIdx, 0.0)
    assert b.band == WORD[weight]
    assert (b.fatT, b.thinT) == (spec.fatT, spec.thinT)


def test_new_reads_the_spec_sex(host):
    # FMI 9.4 is Obese on the male table, Overweight on the female: the band follows spec.sexIdx, not the engine sex
    spec = host.call("body.create", None, "OBESE", host.K.strength.DEFAULTS, 1)
    spec.fm = 9.4 * H2
    assert host.call("body.new", spec, 2, 0.0).band == "obese"
    spec.sexIdx = 2
    assert host.call("body.new", spec, 1, 0.0).band == "overweight"


# --- Task 10b: the fat cuts and their margin scale with lean (Angus, 2026-10-15) ---

STRONG_F = 60.85672078038634   # Strong's start lean (strength_level.trait_start("STRONG")[0]; spec section 3.2)
WEAK_F = 42.115244731130076     # Weak's start lean (strength_level.trait_start("WEAK")[0])


def test_the_start_leans_are_the_references():
    from . import strength_level as sl
    assert abs(sl.trait_start("STRONG")[0] - STRONG_F) < 1e-9
    assert abs(sl.trait_start("WEAK")[0] - WEAK_F) < 1e-9


def test_the_average_lean_is_the_strength_kernels(host):
    assert abs(host.call("strength.fOfBio", 5.0, host.K.strength.DEFAULTS) - FAVG) < 1e-12
    assert abs(host.call("traits.leanAvg") - FAVG) < 1e-12


@pytest.mark.parametrize("lm", [WEAK_F, FAVG, STRONG_F])
def test_the_male_cuts_are_25_and_33_percent_body_fat_at_every_lean(host, lm):
    # cutFat(k) = FAT_CUTS[k] * H2 * lm / Favg; past it by more than the scaled margin the rung moves
    for k, cut, word in ((1, 6.0, "overweight"), (2, 9.0, "obese")):
        kg = cut * H2 * lm / FAVG
        assert abs(kg / (kg + lm) - cut / (18.0 + cut)) < 1e-12
        on = (cut + 0.3) * H2 * lm / FAVG
        assert host.call("traits.axes", _b(host, on * 0.999, lm), 1) == ("normal", "overweight")[k - 1]
        assert host.call("traits.axes", _b(host, on * 1.001, lm), 1) == word


def test_a_strong_body_at_the_average_fat_holds_overweight_later(host):
    # Overweight's cut: 17.34 kg of fat at the average lean, 20.2856 kg at Strong's (both 25 % body fat); the switch
    # needs the scaled margin past it: 18.207 kg at the average, 21.2999 kg at Strong's
    avg_on = 6.3 * H2
    strong_cut = 6.0 * H2 * STRONG_F / FAVG
    strong_on = 6.3 * H2 * STRONG_F / FAVG
    assert abs(6.0 * H2 - 17.34) < 1e-9
    assert abs(avg_on - 18.207) < 1e-9
    assert abs(strong_cut - 20.285573593462107) < 1e-9
    assert abs(strong_on - 21.29985227313522) < 1e-9
    fm = 19.0                                                  # past the average's switch, short of Strong's cut
    assert host.call("traits.axes", _b(host, fm, FAVG), 1) == "overweight"
    assert host.call("traits.axes", _b(host, fm, STRONG_F), 1) == "normal"
    assert host.call("traits.axes", _b(host, strong_on - 0.01, STRONG_F), 1) == "normal"
    assert host.call("traits.axes", _b(host, strong_on + 0.01, STRONG_F), 1) == "overweight"


def test_the_base_character_at_20_percent_is_normal(host):
    s = host.call("body.create", None, None, host.K.strength.DEFAULTS, 1)
    assert abs(s.fm / (s.fm + s.lm) - 0.20) < 1e-12
    assert host.call("traits.axes", s, 1) == "normal"


def test_weak_with_its_normal_fat_is_normal(host):
    s = host.call("body.create", "WEAK", None, host.K.strength.DEFAULTS, 1)
    assert abs(s.fm / (s.fm + s.lm) - 0.20) < 1e-12
    assert host.call("traits.axes", s, 1) == "normal"
    # Weak's Overweight cut is 14.04 kg and its switch 14.74 kg: the average's 13.0 kg is still normal on Weak
    assert host.call("traits.axes", _b(host, 13.005, s.lm), 1) == "normal"
    assert host.call("traits.axes", _b(host, 14.8, s.lm), 1) == "overweight"


@pytest.mark.parametrize("lm", [WEAK_F, STRONG_F])
def test_the_margin_scales_with_lean(host, lm):
    # the hysteresis band is 0.3 FMI scaled by lm / Favg on both sides of each cut
    r = H2 * lm / FAVG
    for rung, x, want in ((0, 6.28, 0), (0, 6.32, 1), (1, 5.72, 1), (1, 5.68, 0), (1, 9.28, 1), (1, 9.32, 2),
                          (2, 8.72, 2), (2, 8.68, 1)):
        b = _b(host, x * r, lm, fatT=rung)
        host.call("traits.axes", b, 1)
        assert b["fatT"] == want, (lm, rung, x)


def test_hysteresis_holds_a_rung_through_a_small_oscillation(host):
    r = H2 * STRONG_F / FAVG
    b = _b(host, 6.31 * r, STRONG_F)
    assert host.call("traits.axes", b, 1) == "overweight"
    for x in (5.75, 6.25, 5.71, 6.29, 5.9):
        b.fm = x * r
        assert host.call("traits.axes", b, 1) == "overweight", x
    b.fm = 5.69 * r
    assert host.call("traits.axes", b, 1) == "normal"
    for x in (6.0, 6.25, 6.29, 5.8):
        b.fm = x * r
        assert host.call("traits.axes", b, 1) == "normal", x


@pytest.mark.parametrize("lm", [WEAK_F, FAVG, STRONG_F])
def test_the_female_cuts_scale_the_same_way(host, lm):
    r = H2 * lm / FAVG
    for rung, x, want in ((0, 9.28, "normal"), (0, 9.32, "overweight"), (0, 13.32, "obese"),
                          (2, 12.72, "obese"), (2, 12.68, "overweight")):
        assert host.call("traits.axes", _b(host, x * r, lm, fatT=rung), 2) == want, (lm, x)
    # the same body on the male table reads one rung worse
    assert host.call("traits.axes", _b(host, 9.32 * r, lm), 1) == "obese"
