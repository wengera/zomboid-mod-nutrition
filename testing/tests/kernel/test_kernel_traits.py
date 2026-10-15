"""The body-trait axes with damping (Plan 13 Task 10; spec section 8; rulings 13-15, 13-17, 13-30 and 13-31; Task 10c).

`K.traits.axes(body, sex)` reads the lean-scaled fat index fm / (H2 * lm / Favg) against Kelly 2009's FMI cuts (S2056
male, S2057 female, the female table only for effective sex 2; Task 10b, Angus 2026-10-15: a cut and its margin scale
with the body's lean lm over the untrained average's Favg, so the male cuts sit at 25 % and 33.3 % body fat for every
lean) and the body-fat share fm / (lm + fm) against the thin edges 12, 8 and 5 % (Task 10c, Angus 2026-10-15: "thin
should start at below 12% bodyfat"; the female values 8 points higher, THIN_F_OFFSET), each with
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
THIN_WORDS = ["normal", "underweight", "veryUnderweight", "emaciated"]


def _b(host, fm, lm, fatT=0, thinT=0, lx=0):
    return host.table({"fm": fm, "lm": lm, "fatT": fatT, "thinT": thinT, "lx": lx})


def _fmi(host, fmi, fatT=0, sex=1):
    """The word at a fat-mass index for a body at the average lean (its body fat well above the thin edges)."""
    b = _b(host, fmi * H2, FAVG, fatT=fatT)
    return host.call("traits.axes", b, sex), b["fatT"]


def _bf(host, bf, thinT=0, sex=1, lm=50.0):
    """The word at a body-fat share bf on lean lm (its fat index far below every fat cut)."""
    b = _b(host, bf * lm / (1 - bf), lm, thinT=thinT)
    return host.call("traits.axes", b, sex), b["thinT"]


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
    b = _b(host, 2.0, 48.0, fatT=1)                     # 4 % body fat: Emaciated, the held fat rung cleared
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
    assert T["THIN_CUTS"] == {1: 0.12, 2: 0.08, 3: 0.05}
    assert T["THIN_WORDS"] == {1: "underweight", 2: "veryUnderweight", 3: "emaciated"}
    assert T["THIN_MARGIN"] == 0.005
    assert T["THIN_F_OFFSET"] == 0.08


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


# the thin edges 0.12, 0.08, 0.05 with the 0.005 margin (Task 10c): a rung is entered past edge - margin and left past
# edge + margin
THIN_CASES = [
    (0.1151, 0, "normal"), (0.1149, 0, "underweight"), (0.0751, 0, "underweight"), (0.0749, 0, "veryUnderweight"),
    (0.0451, 0, "veryUnderweight"), (0.0449, 0, "emaciated"),
    (0.1249, 1, "underweight"), (0.1251, 1, "normal"), (0.0849, 2, "veryUnderweight"), (0.0851, 2, "underweight"),
    (0.1251, 2, "normal"), (0.0549, 3, "emaciated"), (0.0551, 3, "veryUnderweight"), (0.0749, 3, "veryUnderweight"),
    (0.20, 3, "normal"), (0.01, 0, "emaciated"),
]


@pytest.mark.parametrize("bf, thinT, want", THIN_CASES)
def test_thin_edges(host, bf, thinT, want):
    assert _bf(host, bf, thinT) == (want, THIN_WORDS.index(want))


@pytest.mark.parametrize("bf, thinT, want", THIN_CASES)
def test_the_female_thin_edges_sit_8_points_higher(host, bf, thinT, want):
    # NR.SexSpecific on, a female character: 20 / 16 / 13 %, the same margin
    assert _bf(host, bf + 0.08, thinT, sex=2) == (want, THIN_WORDS.index(want))
    # the male edges for effective sex 1 and for an unread sex
    assert _bf(host, bf, thinT, sex=None) == (want, THIN_WORDS.index(want))


def test_the_female_offset_is_read_only_for_effective_sex_2(host):
    assert _bf(host, 0.15, 0, sex=1) == ("normal", 0)
    assert _bf(host, 0.15, 0, sex=2) == ("veryUnderweight", 2)
    assert _bf(host, 0.19, 0, sex=2) == ("underweight", 1)


def test_thinness_reads_body_fat_not_bmi(host):
    # Task 10c (Angus, 2026-10-15): thin is leanness, not weight. A light body at a normal share is normal (BMI 17.3
    # at 20 %), a heavy lean one is thin (BMI 28.8 at 10 %), whatever the height
    assert host.call("traits.axes", _b(host, 10.0, 40.0), 1) == "normal"
    assert host.call("traits.axes", _b(host, 75.0 / 9.0, 75.0), 1) == "underweight"
    keepH = host.K.HEIGHT_M
    try:
        for h in (1.5, 2.0):
            host.K.HEIGHT_M = h
            assert host.call("traits.axes", _b(host, 10.0, 40.0), 1) == "normal", h
            assert host.call("traits.axes", _b(host, 75.0 / 9.0, 75.0), 1) == "underweight", h
    finally:
        host.K.HEIGHT_M = keepH


def test_the_body_fat_share_leaves_out_the_labile_lean(host):
    # ruling 13-15: lx rides in the weight slot but never counts toward thinness, nor toward the fat index
    b = _b(host, 50.0 * 0.07 / 0.93, 50.0, lx=5.0)             # 7 % of lm + fm; 6.4 % with lx
    assert host.call("traits.axes", b, 1) == "veryUnderweight"
    b = _b(host, 50.0 * 0.11 / 0.89, 50.0, lx=-3.0)            # 11 % of lm + fm; 11.7 % with lx
    assert host.call("traits.axes", b, 1) == "underweight"
    b = _b(host, 6.2 * H2, 52.0, lx=5.0)                        # FMI 6.2: lx is lean, not fat
    assert host.call("traits.axes", b, 1) == "normal"


def test_a_massless_body_reads_the_deepest_rung(host):
    assert host.call("traits.thinReading", 0.0, 0.0, 1) == 0
    assert host.call("traits.thinReading", 0.0, 0.0, 2) == pytest.approx(-0.08)
    assert host.call("traits.thinReading", 5.0, 45.0, 1) == pytest.approx(0.1)
    assert host.call("traits.thinReading", 5.0, 45.0, 2) == pytest.approx(0.02)


def test_precedence_clears_a_held_fat_rung(host):
    b = _b(host, 3.0, 40.0, fatT=2, thinT=1)            # 7 % body fat: thin holds and deepens, fat cleared
    assert host.call("traits.axes", b, 1) == "veryUnderweight"
    assert (b["fatT"], b["thinT"]) == (0, 2)
    # back out of thinness, the fat axis is read afresh from 0
    b = _b(host, 12.0 * H2, 52.0, fatT=0, thinT=1)
    assert host.call("traits.axes", b, 1) == "obese"
    assert (b["fatT"], b["thinT"]) == (2, 0)
    b = _b(host, 5.0, 45.0, fatT=1)                     # 10 % body fat: Underweight clears a held Overweight
    assert host.call("traits.axes", b, 1) == "underweight"
    assert (b["fatT"], b["thinT"]) == (0, 1)


def test_axes_reads_its_tables(host):
    T = host.K.traits
    keep = {k: T[k] for k in ("FAT_CUTS", "FAT_WORDS", "FAT_MARGIN", "THIN_CUTS", "THIN_WORDS", "THIN_MARGIN",
                              "THIN_F_OFFSET")}
    keepH = host.K.HEIGHT_M
    try:
        T.FAT_CUTS = host.table({1: {1: 2, 2: 3}, 2: {1: 4, 2: 5}})
        T.FAT_WORDS = host.table({1: "fatA", 2: "fatB"})
        T.FAT_MARGIN = 0.1
        T.THIN_CUTS = host.table({1: -1, 2: -2, 3: -3})          # no thin rung while the fat decoys are read
        s = 40.0 * H2 / FAVG                                      # the fat index scales with lean (Task 10b)
        assert host.call("traits.axes", _b(host, 2.05 * H2 * s, 40.0 * H2), 1) == "normal"
        assert host.call("traits.axes", _b(host, 2.15 * H2 * s, 40.0 * H2), 1) == "fatA"
        assert host.call("traits.axes", _b(host, 3.15 * H2 * s, 40.0 * H2), 1) == "fatB"
        assert host.call("traits.axes", _b(host, 4.15 * H2 * s, 40.0 * H2), 2) == "fatA"
        assert host.call("traits.axes", _b(host, 5.15 * H2 * s, 40.0 * H2), 2) == "fatB"
        T.FAT_CUTS = host.table({1: {1: 100, 2: 200}, 2: {1: 100, 2: 200}})   # no fat rung under the thin decoys
        T.THIN_CUTS = host.table({1: 0.30, 2: 0.25, 3: 0.22})
        T.THIN_WORDS = host.table({1: "thinA", 2: "thinB", 3: "thinC"})
        T.THIN_MARGIN = 0.01
        T.THIN_F_OFFSET = 0.03
        assert _bf(host, 0.295)[0] == "normal"
        assert _bf(host, 0.285)[0] == "thinA"
        assert _bf(host, 0.235)[0] == "thinB"
        assert _bf(host, 0.205)[0] == "thinC"
        assert _bf(host, 0.305, sex=2)[0] == "thinA"                # 0.305 - 0.03 = 0.275
        assert _bf(host, 0.325, sex=2)[0] == "normal"
        for k, v in keep.items():
            T[k] = v
        host.K.HEIGHT_M = 2.0                                      # H2 = 4: the average lean is 18 * 4 = 72 kg
        assert host.call("traits.axes", _b(host, 6.4 * H2, 72.0), 1) == "normal"
        assert host.call("traits.axes", _b(host, 6.4 * 4.0, 72.0), 1) == "overweight"
        assert _bf(host, 0.11)[0] == "underweight"                  # the thin axis is height-free
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

@pytest.mark.parametrize("prof", [0, 1, 2])
@pytest.mark.parametrize("sexIdx", [1, 2])
@pytest.mark.parametrize("muscle, weight", [(m, w) for m in MUSCLE for w in WEIGHT])
def test_every_creation_pick_keeps_its_rung(host, muscle, weight, sexIdx, prof):
    # every pair is legal since Task 10c (the exclusions lifted): each created body reads its pick's word and rungs
    s = host.call("body.create", muscle, weight, host.K.strength.DEFAULTS, sexIdx, prof)
    fatT, thinT = s["fatT"], s["thinT"]
    assert host.call("traits.axes", s, sexIdx) == WORD[weight]
    assert (s["fatT"], s["thinT"]) == (fatT, thinT)


@pytest.mark.parametrize("prof", [0, 1, 2])
@pytest.mark.parametrize("sexIdx", [1, 2])
@pytest.mark.parametrize("muscle, weight", [(m, w) for m in MUSCLE for w in ("UNDERWEIGHT", "VERY_UNDERWEIGHT")])
def test_a_created_thin_pick_is_held_by_the_axis_alone(host, muscle, weight, sexIdx, prof):
    # Task 10c: the thin starts sit mid-band (10 % and 6.5 %, female 18 % and 14.5 %), so a reading from no rung at
    # all enters the pick's rung and goes no deeper (Task 10's concern 2: a start on its entry edge, gone)
    s = host.call("body.create", muscle, weight, host.K.strength.DEFAULTS, sexIdx, prof)
    want = s["thinT"]
    s.thinT = 0
    assert host.call("traits.axes", s, sexIdx) == WORD[weight]
    assert s["thinT"] == want
    bf = host.call("traits.thinReading", s["fm"], s["lm"], sexIdx)
    cuts = (0.12, 0.08, 0.05)
    margin = 0.005
    assert bf <= cuts[want - 1] - margin - 0.01 + 1e-12            # inside the rung by a point or more past entry
    assert bf >= cuts[want] - margin + 0.01 - 1e-12                 # and a point or more short of the next rung's


@pytest.mark.parametrize("muscle, weight, sexIdx", [
    (None, None, 1), ("STRONG", "OBESE", 2), (None, "OVERWEIGHT", 1), ("STOUT", "UNDERWEIGHT", 2),
    (None, "EMACIATED", 1), ("WEAK", "VERY_UNDERWEIGHT", 1), ("FEEBLE", "UNDERWEIGHT", 2),
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
    assert abs(host.call("strength.averageLean") - FAVG) < 1e-12


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


def test_the_fat_axis_scales_by_lm_not_lx(host):
    # the labile lean lx is left out of the lean the fat cuts scale by (Task 10b: body.lm, not lx)
    for fatT in (0, 1):
        b = _b(host, 6.4 * H2, FAVG, fatT=fatT, lx=5.0)
        assert host.call("traits.axes", b, 1) == "overweight", fatT
