"""The body-trait axes with damping (Plan 13 Task 10; spec section 8; rulings 13-15, 13-17, 13-30 and 13-31).

`K.traits.axes(body, sex)` reads the fat-mass index fm / H2 against Kelly 2009's FMI cuts (S2056 male, S2057 female,
the female table only for effective sex 2) and the BMI (lm + fm) / H2 against WHO's thinness grades (S2059), each with
its game-choice margin; a thinness rung excludes the fat rungs. `K.traits.held` is the damped step, `K.traits.WANT`
the five weight-band trait names. The constants are also read through decoy copies, so a test passes only when the
kernel reads the table it is handed.
"""
import pytest

H2 = 1.70 * 1.70
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
    """The word at a fat-mass index for a normal-BMI body (lean 52 kg keeps the BMI well above the thin cuts)."""
    b = _b(host, fmi * H2, 52.0, fatT=fatT)
    return host.call("traits.axes", b, sex), b["fatT"]


def _bmi(host, bmi, thinT=0):
    """The word at a BMI with a fat-mass index of 1 (far below every fat cut)."""
    b = _b(host, 1.0 * H2, (bmi - 1.0) * H2, thinT=thinT)
    return host.call("traits.axes", b, 1), b["thinT"]


def _held(host, rung, x, cuts, margin, up):
    return host.call("traits.held", rung, x, host.table(dict(enumerate(cuts, 1))), margin, up)


# --- the brief's tests ---

def test_overweight_needs_the_margin(host):
    b = _b(host, 6.2 * H2, 52.0)
    assert host.call("traits.axes", b, 1) == "normal"
    b = _b(host, 6.4 * H2, 52.0)
    assert host.call("traits.axes", b, 1) == "overweight"


def test_overweight_holds_inside_the_margin_on_the_way_back(host):
    b = _b(host, 5.8 * H2, 52.0, fatT=1)
    assert host.call("traits.axes", b, 1) == "overweight"
    b = _b(host, 5.6 * H2, 52.0, fatT=1)
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
        assert host.call("traits.axes", _b(host, 2.05 * H2, 40.0 * H2), 1) == "normal"
        assert host.call("traits.axes", _b(host, 2.15 * H2, 40.0 * H2), 1) == "fatA"
        assert host.call("traits.axes", _b(host, 3.15 * H2, 40.0 * H2), 1) == "fatB"
        assert host.call("traits.axes", _b(host, 4.15 * H2, 40.0 * H2), 2) == "fatA"
        assert host.call("traits.axes", _b(host, 5.15 * H2, 40.0 * H2), 2) == "fatB"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 28.75 * H2), 1) == "thinA"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 27.75 * H2), 1) == "thinB"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 26.75 * H2), 1) == "thinC"
        assert host.call("traits.axes", _b(host, 1.0 * H2, 28.95 * H2), 1) == "normal"
        for k, v in keep.items():
            T[k] = v
        host.K.HEIGHT_M = 2.0                                      # H2 = 4: FMI 6.4 at 1.70 m is 4.7 at 2 m
        assert host.call("traits.axes", _b(host, 6.4 * H2, 80.0), 1) == "normal"
        assert host.call("traits.axes", _b(host, 6.4 * 4.0, 80.0), 1) == "overweight"
    finally:
        for k, v in keep.items():
            T[k] = v
        host.K.HEIGHT_M = keepH
    assert host.call("traits.axes", _b(host, 6.4 * H2, 52.0), 1) == "overweight"


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
def test_new_lean_lays_the_band(host, muscle, weight, sexIdx):
    spec = host.call("body.create", muscle, weight, host.K.strength.DEFAULTS, sexIdx)
    b = host.call("body.newLean", spec, sexIdx, 0.0)
    assert b.band == WORD[weight]
    assert (b.fatT, b.thinT) == (spec.fatT, spec.thinT)


def test_new_lean_reads_the_spec_sex(host):
    # FMI 9.4 is Obese on the male table, Overweight on the female: the band follows spec.sexIdx, not the engine sex
    spec = host.call("body.create", None, "OBESE", host.K.strength.DEFAULTS, 1)
    spec.fm = 9.4 * H2
    assert host.call("body.newLean", spec, 2, 0.0).band == "obese"
    spec.sexIdx = 2
    assert host.call("body.newLean", spec, 1, 0.0).band == "overweight"
