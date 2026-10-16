"""The gut-satiety oracles (Plan 11g Task 3; spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 4; rulings
11g-2 and 11g-3): the new study oracles of the gut-satiety plan, encoded from the minted rows (S1799-S1894, Plan 11g Task 2)
before any model change and pinned at the P model (meal pool P fed in full at the eat, HALF_LIFE_H 0.7 h). Each
test pins today's reading and its distance to the study figure, so a change is noticed; its comment names the study
row, the target, and the tolerance Task 6 will assert. A tolerance no row evidences is labelled a design choice.
Plan 11g Task 4 re-pinned every reading under the gut stage G (fed at emptying) with its provisional constants (the
P fits carried over). Plan 11g Task 6 fitted G's constants (fit-11g-20261012, degenerate) and turned each target into
an assertion of its registry entry (gut_oracles.check: the band and kind read from gut_oracles.ORACLES, never
re-typed); a target the fit leaves outside its band is a named non-reproduction (gut_oracles.NAMED), pinned at its
reading and asserted still outside. Plan 11g Task 6c (spec § 7) replaced G with the meal pool M, fed in full at the
eat, counted F to the hard capacity and refit (tools/fit_gut_satiety.py, fit-11g-20261012b); its fix 1 made Tieken
read-only (ruling T6c-2), scored S1233's volume slope (ruling T6c-3) and refit (fit-11g-20261012c); its fix 2 scored
S1231's null for water drunk alongside, lifted LIQUID_WEIGHT's bound to (0, 1] (ruling T6c-5) and refit
(fit-11g-20261012d). Every other reading stays pinned (PIN, and DIST its distance to STUDY), so a change is noticed; each
comment gives the refit's reading beside the earlier fits', the gut stage's and the P model's.
STUDY and VAS_DETECT live in gut_oracles.py since Plan 11g Task 5, beside the oracle registry the joint fit scores, so
a target lives in one place.

The replays are the existing ones, reused, not copied:
- the time courses and the protein contrast run test_satiety_meal_studies.py's satiety replay (REPLAY: one step a game
  minute, the eats landing in the stomach and feeding M, the drain clearing M, F and the displayed hunger), under its
  protocol: from the request (displayed HUNGER 0.25, an empty stomach, M seeded at the request), the circadian factor
  held at 1 where the study states no clock;
- the surplus day runs test_replay_live_energy.py's Karl twin K on the shipped server path (tools/replay_live.py), so
  the deficit drive's energy-state term is in the hunger it reads;
- the three non-reproductions of ruling 11g-3 are test_satiety_meal_studies.py's own readings (marmonier, melanson,
  moore_half_emptying), re-read here as distances.

A time course's baseline is the request, H_REQ: a reading "relative to fasting" is hunger / H_REQ - 1, and the
recovery minute is the first minute displayed hunger is back at H_REQ (test_satiety_meal_studies.request).

Every reading function takes only `host` (the mutation-script convention of test_satiety_meal_studies.py); no
`parametrize`. Accepted after the mutation pass (CLAUDE.md § 6, Plan 11g Task 3 amendments): on a scratch copy,
K.satiety.HALF_LIFE_H at x2 (1.4) and at x0.5 (0.35) fails every test but S1272's, and moves 65 and 66 of the 75
pinned leaves beyond PIN_TOL. The leaves it leaves are structural under P, not continuous readings: the four nadir
minutes (always the first minute, P fed in full at the eat) and the four monotone flags, Melanson's fat minus
carbohydrate at x2 (both arms move together, 0 against 0), and S1272's half-emptying, a stomach reading P does not
enter (named in its test). Plan 11g Task 4's mutation pass (G_HALF_LIFE_H at x2 and x0.5, the feed removed, seedG
uncapped) is in its report. Plan 11g Task 6's (each fitted constant at x2 and x0.5 on a scratch copy fails 22 to 27 of
the 50 tests of this file, test_satiety_meal_studies.py and test_replay_live_oracle.py; LIQUID_WEIGHT 9) is in its report,
and Plan 11g Task 6c's and its fix 1's and fix 2's in theirs.
"""
from . import test_replay_live_energy as E
from . import test_satiety_meal_studies as M
from .gut_oracles import STUDY, VAS_DETECT, check, check_karl_shape

PIN_TOL = 1e-6                  # a pin's tolerance: today's reading to 1e-6


def near(x, pin):
    return abs(x - pin) < PIN_TOL


# --- the meals -----------------------------------------------------------------------------------------------------

def vec(kcal, comp):
    """A meal of `kcal` at `comp`: energy shares p, c, f (normalised to their sum, Atwater 4/4/9), and either a total
    mass in grams (`mass`, water filling it) or water (`water`, grams) beside fibre (`fibre`, grams)."""
    s = comp["p"] + comp["c"] + comp["f"]
    v = {"calories": kcal, "proteins": kcal * comp["p"] / s / 4, "carbs": kcal * comp["c"] / s / 4,
         "lipids": kcal * comp["f"] / s / 9, "fibre": comp.get("fibre", 0.0)}
    if "mass" in comp:
        v["water"] = max(0.0, comp["mass"] - M.mass_of(v))
    else:
        v["water"] = comp.get("water", 0.0)
    return v


# S1833 (Tieken 2007), Table 2: 540 kcal each; solid 64/15/25 % and liquid 73/18/10 % of energy from carbohydrate,
# protein and fat (as printed, normalised here), fibre 2 against 12 g, weight 138 against 553 g
TIEKEN_KCAL = 540.0
TIEKEN_SOLID = {"kind": "food", "c": 0.64, "p": 0.15, "f": 0.25, "fibre": 2.0, "mass": 138.0}
TIEKEN_LIQUID = {"kind": "drink", "c": 0.73, "p": 0.18, "f": 0.10, "fibre": 12.0, "mass": 553.0}

# S1827 / S1828 (Diekmann 2026), Table 2: about 4200 kJ (1003.8 kcal, derived: 4200 / 4.184); high fat 54 % fat, 35 %
# carbohydrate, 6.6 g fibre; low fat 59 % carbohydrate, 11.2 g fibre; both 26.6 g protein (10.6 % of energy, derived:
# 26.6 x 4 / 1003.8), the low-fat meal's fat the rest (30.4 %, derived). The water is not in the row: ASSUMED 300 g per
# 650 kcal (test_satiety_meal_studies.mixed's)
DIEKMANN_KCAL = 4200.0 / 4.184
DIEKMANN_P = 26.6 * 4 / DIEKMANN_KCAL
DIEKMANN_HF = {"kind": "food", "p": DIEKMANN_P, "c": 0.35, "f": 1 - DIEKMANN_P - 0.35, "fibre": 6.6,
               "water": 300.0 * DIEKMANN_KCAL / 650}
DIEKMANN_LF = {"kind": "food", "p": DIEKMANN_P, "c": 0.59, "f": 1 - DIEKMANN_P - 0.59, "fibre": 11.2,
               "water": 300.0 * DIEKMANN_KCAL / 650}

# S1808 / S1809 (Lewis 2015): breakfasts 3310 / 2650 / 1990 kJ (men) and 2540 / 2030 / 1520 kJ (women); the full
# portion is their mean, 699.1 kcal (derived: (3310 + 2540) / 2 / 4.184), cut by 20 % and 40 %. Its composition is not
# in the rows: ASSUMED test_satiety_meal_studies.mixed's 15/50/35 % with 300 g of water and 6 g of fibre per 650 kcal,
# all scaled with the portion
LEWIS_KCAL = (3310.0 + 2540.0) / 2 / 4.184
LEWIS_T = (30, 60, 120, 180, 240)      # minutes after the breakfast's start the oracle reads (S1809: 30-240 min)


def lewis_comp(kcal):
    return {"kind": "food", "p": 0.15, "c": 0.50, "f": 0.35, "water": 300.0 * kcal / 650, "fibre": 6.0 * kcal / 650}


TIEKEN_T = (15, 60, 120, 180, 240)     # S1833's rating times (min)
DIEKMANN_T = (30, 60, 120, 240, 360)   # S1828's rating times after the meal (min; 0.5, 1, 2, 4, 6 h)


# --- the readings, shared by the tests and the mutation script ------------------------------------------------------

FASTED = {"M0": 0.0, "h0": 8.0}     # a fasted start at 08:00, as Callahan's oracle reads (test_satiety_meal_studies.callahan)


def time_course(host, kcal, composition, minutes, start=None):
    """Displayed HUNGER a minute (index i is minute i + 1) after one meal of `kcal` at `composition` (vec's keys plus
    `kind`, "food" or "drink") eaten at minute 0. ASSUMED start (no row gives the studies' start state): from the
    request (HUNGER 0.25, not fasted), the circadian factor held at 1 (not about 08:00). `start` = FASTED reads a fasted
    start at 08:00 instead."""
    return M.hunger(host, {0: [(composition["kind"], vec(kcal, composition))]}, minutes, **(start or {}))


def at(hs, t):
    """Displayed hunger at minute t after the eat (the step that ends t minutes on)."""
    return hs[t - 1]


def nadir(hs):
    """(the minute of the lowest displayed hunger, that hunger)."""
    i = min(range(len(hs)), key=lambda k: hs[k])
    return i + 1, hs[i]


def rises_after_nadir(hs):
    """True when displayed hunger never falls after its nadir: one early nadir, then a monotone recovery."""
    n, _ = nadir(hs)
    return all(b >= a - 1e-12 for a, b in zip(hs[n - 1:], hs[n:]))


def meal_sizes(host, start=None):
    """S1808 / S1809 (Lewis 2015): the full breakfast and its 20 % and 40 % cuts, from the request. Returns {cut: the
    hunger difference cut minus full at each of LEWIS_T, and its mean over minutes 30-240}."""
    full = time_course(host, LEWIS_KCAL, lewis_comp(LEWIS_KCAL), 240, start)
    out = {}
    for name, share in (("cut20", 0.8), ("cut40", 0.6)):
        k = LEWIS_KCAL * share
        hs = time_course(host, k, lewis_comp(k), 240, start)
        d = [a - b for a, b in zip(hs, full)]
        out[name] = {"at": [at(d, t) for t in LEWIS_T], "mean": sum(d[29:240]) / len(d[29:240])}
    return out


def tieken(host, start=None):
    """S1833 (Tieken 2007): the 540 kcal solid and liquid meal replacements. Returns {arm: {at: hunger / H_REQ - 1 at
    each of TIEKEN_T, back: the recovery minute, nadir: (minute, hunger), monotone}}."""
    out = {}
    for name, comp in (("solid", TIEKEN_SOLID), ("liquid", TIEKEN_LIQUID)):
        hs = time_course(host, TIEKEN_KCAL, comp, 900, start)
        out[name] = {"at": [at(hs, t) / M.H_REQ - 1 for t in TIEKEN_T], "back": M.request(hs),
                     "nadir": nadir(hs), "monotone": rises_after_nadir(hs)}
    return out


def diekmann(host, start=None):
    """S1828 (Diekmann 2026): the ~1,000 kcal high-fat and low-fat meals. Returns {arm: {at: hunger / H_REQ - 1 at each
    of DIEKMANN_T, back, nadir, monotone, mean: mean hunger over 0-6 h}}."""
    out = {}
    for name, comp in (("hf", DIEKMANN_HF), ("lf", DIEKMANN_LF)):
        hs = time_course(host, DIEKMANN_KCAL, comp, 900, start)
        out[name] = {"at": [at(hs, t) / M.H_REQ - 1 for t in DIEKMANN_T], "back": M.request(hs),
                     "nadir": nadir(hs), "monotone": rises_after_nadir(hs), "mean": sum(hs[:360]) / 360}
    return out


# The protein contrast at equal energy: the meal energy is in none of the rows, so each arm is ASSUMED 650 kcal (the
# spec's typical meal) with 300 g of water and 6 g of fibre, eaten from the request
PROTEIN_KCAL = 650.0


def protein_arm(host, p, c, f, minutes=240):
    return time_course(host, PROTEIN_KCAL, {"kind": "food", "p": p, "c": c, "f": f, "water": 300.0, "fibre": 6.0},
                       minutes)


def protein_at_equal_energy(host):
    """The protein-against-carbohydrate oracle at equal energy (harvest 11 § 3). The rows' meal energies are not given
    (ASSUMED 650 kcal each). Under P the contrast is carried by PROTEIN_FILL and FULL_WEIGHT: W_PROTEIN at x0.5 or x2
    leaves belza_hp in band, so Task 6's mutation pass must re-check W_PROTEIN against this oracle under G. Returns:
    - belza_mhp, belza_hp: S1820 (Belza 2013), 25 % and 50 % protein against 14 % (fat held at 30 %, ASSUMED, the
      carbohydrate taking the rest): the 4-h mean hunger's change against NP (study -15 % and -25 %);
    - smeets_30, smeets_120: S1822 (Smeets 2008), 25/45/30 against 10/60/30 % protein/carbohydrate/fat: the hunger
      difference HP minus AP at 30 and 120 min (study: satiety higher at both; the row rates satiety, not hunger);
    - vdk: S1818 (van der Klaauw 2013), 60 % protein against 60 % carbohydrate (the other two at 20 % each, ASSUMED):
      the 4-h mean hunger's change (study: no difference, AUC P = 0.634)."""
    np_ = protein_arm(host, 0.14, 0.56, 0.30)
    mhp = protein_arm(host, 0.25, 0.45, 0.30)
    hp = protein_arm(host, 0.50, 0.20, 0.30)
    s_ap = protein_arm(host, 0.10, 0.60, 0.30)
    v_p = protein_arm(host, 0.60, 0.20, 0.20)
    v_c = protein_arm(host, 0.20, 0.60, 0.20)

    def mean(hs):
        return sum(hs) / len(hs)
    return {"belza_mhp": mean(mhp) / mean(np_) - 1, "belza_hp": mean(hp) / mean(np_) - 1,
            "smeets_30": at(mhp, 30) - at(s_ap, 30), "smeets_120": at(mhp, 120) - at(s_ap, 120),
            "vdk": mean(v_p) / mean(v_c) - 1}


KARL_POST = (1, 5, 7)           # the post-meal rows among karl_vas's sorted eight (07:00, 12:00, 18:00)
KARL_PRE_BREAKFAST = 0          # 06:59


def karl_vas_rows(arm):
    """Twin K's eight VAS readings a study day for `arm` (test_replay_live_energy.karl_rows on the server path),
    one list per study day, in karl_vas's order: pre- and post-breakfast, pre- and post-exercise, pre- and post-lunch,
    pre- and post-dinner."""
    rows, days, am_dur = E.karl_rows(arm)
    return [[rows[m][E.RL.H_MODEL] for m in E.karl_vas(d * 1440, am_dur)] for d in range(E.KARL_WARM, days)]


def surplus_day(host):
    """S1325 / S1872 / S1892 (Karl 2021): the well-fed arm (BAL, 22.7 MJ/d over three SUSOPS days) against the
    sedentary REST day, at the study's eight daily sampling points, on the server path. Returns {bal: the mean daily
    hunger's change against REST in %, by_day: each SUSOPS day's, rest: REST's mean, troughs: the mean post-meal hunger
    of each BAL day, rest_trough, pre_breakfast: BAL's pre-breakfast hunger by day, rest_pre_breakfast, troughs_rel:
    each BAL day's trough over REST's, pre_breakfast_rel: each day's pre-breakfast over REST's (ruling T3-1: model
    HUNGER and the study's VAS / 10 are on different scales, so the shape is read relative to REST)}."""
    rest = karl_vas_rows("REST")[0]
    bal = karl_vas_rows("BAL")
    r = sum(rest) / len(rest)
    allbal = [x for day in bal for x in day]
    rest_trough = sum(rest[i] for i in KARL_POST) / 3
    troughs = [sum(day[i] for i in KARL_POST) / 3 for day in bal]
    return {"bal": 100 * (sum(allbal) / len(allbal) / r - 1),
            "by_day": [100 * (sum(day) / len(day) / r - 1) for day in bal], "rest": r,
            "troughs": troughs, "rest_trough": rest_trough,
            "pre_breakfast": [day[KARL_PRE_BREAKFAST] for day in bal], "rest_pre_breakfast": rest[KARL_PRE_BREAKFAST],
            "troughs_rel": [t / rest_trough for t in troughs],
            "pre_breakfast_rel": [day[KARL_PRE_BREAKFAST] / rest[KARL_PRE_BREAKFAST] for day in bal]}


def dist(model, study):
    """A named distance: the model's reading less the study's figure, elementwise over a tuple."""
    if isinstance(study, tuple):
        return tuple(m - s for m, s in zip(model, study))
    return model - study


def near_all(xs, pins):
    return len(xs) == len(pins) and all(near(x, p) for x, p in zip(xs, pins))


# --- meal size (S1808, S1809, S1838) ----------------------------------------------------------------------------------

def test_meal_size_grades_hunger_at_a_40_percent_cut(host):
    # S1809 (Lewis 2015): hunger greater after the 40 % cut at every time point 30-240 min (p < 0.006); no condition x
    # time interaction after the 20 % cut (p > 0.291). S1838 (open): no source tabulates the values, so the target is
    # the pattern. Task 6 asserts: the 40 % cut's difference positive at each of LEWIS_T and its 30-240 min mean at
    # least VAS_DETECT, the 20 % cut's mean below VAS_DETECT (VAS_DETECT a DESIGN CHOICE: 5 mm under ruling 11c-31's
    # 260 mm a unit). The refit (Task 6c fix 2): cut40 0.0349 (9.1 mm), cut20 0.0172 (4.5 mm): each target holds (fix
    # 1's fit: 0.0350, 0.0173; Task 6c's fit: cut40 0.0342, cut20 0.0167). The gut
    # stage's fit (Task 6): cut40 0.0423, cut20 0.0211 (5.5 mm, named). Under G's provisional constants (Task 4): cut40
    # 0.0347, cut20 0.0172 (4.5 mm). On the P model (Task 3): cut40 0.0370 (9.6 mm), cut20 0.0181 (4.7 mm)
    r = meal_sizes(host)
    check({"meal_sizes": r}, "lewis_cut40_at", "lewis_cut40_mean", "lewis_cut20_mean")
    assert near(r["cut40"]["mean"], PIN["cut40_mean"]) and near(r["cut20"]["mean"], PIN["cut20_mean"]), r
    assert near_all(r["cut40"]["at"], PIN["cut40_at"]) and near_all(r["cut20"]["at"], PIN["cut20_at"]), r
    assert near(dist(r["cut40"]["mean"], VAS_DETECT), DIST["cut40"]), r
    assert near(dist(r["cut20"]["mean"], VAS_DETECT), DIST["cut20"]), r
    # ASSUMED start: from the request, the clock held at 1 (no row gives the study's start state); the fasted start at
    # 08:00 is an unasserted reading
    f = meal_sizes(host, FASTED)
    for k in ("cut20", "cut40"):
        assert near(f[k]["mean"], PIN["fasted_lewis"][k + "_mean"]) and near_all(f[k]["at"], PIN["fasted_lewis"][k + "_at"]), f


# --- the time courses: recovery scaling with emptying (S1833, S1828, S1840) ----------------------------------------

def test_the_540_kcal_meal_replacements_at_four_hours(host):
    # S1833 (Tieken 2007): at 4 h hunger +14 +/- 10 % above fasting after the liquid, -45 +/- 19 % below it after the
    # solid, the solid lower at every time point (15-240 min); the arms differ in composition, fibre and mass (the
    # row's caveat). Task 6 asserts each arm's 4 h reading within the study's +/- (liquid +4 to +24 %, solid -64 to
    # -26 %; the row's spread taken as the tolerance, a DESIGN CHOICE) and the solid below the liquid at each of
    # TIEKEN_T. Since Task 6c fix 1 the three are reading-kind (ruling T6c-2: pinned, named and reported, never
    # scored). The refit (Task 6c fix 2) reads both arms about -4 % at 4 h (liquid -4.3 %, -18.3 points from the study;
    # solid -3.7 %, +41.3), the liquid lower at every time point, back at 279 / 276 min: all three named
    # non-reproductions (gut_oracles.NAMED: the stomach empties both arms' kcal alike and M is fed alike at the eat);
    # fix 1's fit read the same to 0.1 point. Task 6c's fit: -4.6 % and -4.1 %, back at 274 / 272.
    # The gut stage's fit (Task 6): -4.5 % and -3.7 %, named; under G's provisional constants (Task 4) both about
    # -13.5 %, back at 471 / 473 min; on the P model (Task 3) both about -6 %, back near 293 min
    r = tieken(host)
    check({"tieken": r}, "tieken_liquid_4h", "tieken_solid_4h", "tieken_solid_below_liquid")
    for arm in ("solid", "liquid"):
        assert near_all(r[arm]["at"], PIN["tieken_%s_at" % arm]), r
        assert r[arm]["back"] == PIN["tieken_%s_back" % arm], r
    assert near(dist(r["liquid"]["at"][-1], STUDY["tieken_liquid_4h"]), DIST["tieken_liquid_4h"]), r
    assert near(dist(r["solid"]["at"][-1], STUDY["tieken_solid_4h"]), DIST["tieken_solid_4h"]), r
    # ASSUMED start: from the request, the clock held at 1 (the row gives neither); a fasted start at 08:00 is an
    # unasserted reading
    f = tieken(host, FASTED)
    for arm in ("solid", "liquid"):
        assert near_all(f[arm]["at"], PIN["fasted_tieken"][arm][0]) and f[arm]["back"] == PIN["fasted_tieken"][arm][1], f


def test_the_1000_kcal_meal_still_sates_at_six_hours(host):
    # S1828 (Diekmann 2026): hunger still below baseline 6.0 h after the ~4200 kJ meals, both arms. Harvest 11 § 6:
    # recovery about 4 h after 540 kcal and over 6 h after about 1,000 kcal, scaling with emptying time (S1840:
    # r = 0.75 against the time for 90 % to empty). Task 6 asserts each arm below H_REQ at 360 min, its recovery
    # minute after 360, and the 1,000 kcal recovery later than the 540 kcal liquid's (the ordering a DESIGN CHOICE for
    # the scaling: the rows give no ratio). The refit (Task 6c fix 2): back at 381 / 383 min (+21 / +23 past 360), 102
    # min after Tieken's liquid: each target holds (fix 1's fit: 382 / 384, 103 min after; Task 6c's fit: 365 / 368, 91
    # min after). The gut stage's fit (Task 6): 448 / 457; under G's provisional
    # constants (Task 4) both back at 616 min; on the P model (Task 3) at 391 / 392 min
    r = diekmann(host)
    check({"diekmann": r, "tieken": tieken(host)}, "diekmann_hf_6h", "diekmann_lf_6h", "diekmann_after_tieken")
    for arm in ("hf", "lf"):
        assert near_all(r[arm]["at"], PIN["diekmann_%s_at" % arm]), r
        assert r[arm]["back"] == PIN["diekmann_%s_back" % arm], r
        assert dist(r[arm]["back"], STUDY["diekmann_6h_min"]) == DIST["diekmann_%s_back" % arm], r
    # ASSUMED start: from the request, the clock held at 1 (the row gives neither); a fasted start at 08:00 is an
    # unasserted reading
    f = diekmann(host, FASTED)
    for arm in ("hf", "lf"):
        assert near_all(f[arm]["at"], PIN["fasted_diekmann"][arm][0]) and f[arm]["back"] == PIN["fasted_diekmann"][arm][1], f


def test_the_single_early_nadir_is_a_reading(host):
    # Harvest 11 § 7 (inference, never asserted as a target): the hunger courses read as one early nadir (S1833:
    # 15 min, the only one stated in text) and a monotone recovery. Pinned as a reading: each course's nadir minute,
    # its hunger and whether hunger never falls after it. The refit (Task 6c, its fix 1 and fix 2): every nadir is the first minute (M fed in
    # full at the eat, as P was; the study's 15 min is an accepted downside, spec § 7). The gut stage's fit (Task 6):
    # minutes 1, 1, 69 and 78; under G's provisional constants (Task 4) minutes 22, 12, 42 and 52; on the P model
    # (Task 3) every nadir was the first minute
    t, d = tieken(host), diekmann(host)
    got = {"solid": t["solid"], "liquid": t["liquid"], "hf": d["hf"], "lf": d["lf"]}
    for arm, x in got.items():
        assert x["nadir"][0] == PIN["nadir_minute"][arm], (arm, x["nadir"])
        assert near(x["nadir"][1], PIN["nadir_hunger"][arm]), (arm, x["nadir"])
        assert x["monotone"] == PIN["monotone"][arm], (arm, x)


# --- protein against carbohydrate at equal energy (S1820, S1822, S1818, S1821, S1814, S1225, S1222) ----------------

def test_protein_against_carbohydrate_at_equal_energy(host):
    # Harvest 11 § 3: modest and mixed. Positive: S1820 (Belza 2013: hunger -15 % at 25 % and -25 % at 50 % protein
    # against 14 %), S1822 (Smeets 2008: satiety higher at 30 and 120 min, AUC 263 against 236 mm h), the pooled S1222
    # (-7 mm). Null: S1818 (van der Klaauw 2013, n = 8, AUC P = 0.634), S1821 (Blom 2006), S1814 (Foster-Schubert
    # 2008), S1225 (Raben 2003). Task 6 asserts belza_hp in [-0.25, 0] and belza_mhp in [belza_hp, 0] (Belza's size
    # the floor, the nulls the ceiling: a DESIGN CHOICE between the two sides) and smeets_30, smeets_120 at or below 0;
    # vdk is read, never asserted. The refit (Task 6c fix 2, W_PROTEIN 2.50): belza_hp -24.7 % (+0.3 points from
    # Belza), belza_mhp -7.6 % (+7.4), Smeets -0.027 and -0.018, each target holding; vdk -28.0 % where the study reads
    # no difference. Fix 1's fit (W_PROTEIN 2.49): -24.9 %, -7.7 %, -0.027, -0.018, vdk -28.3 %. Task 6c's fit (W_PROTEIN 2.5): -24.1 %, -7.5 %, -0.025, -0.017, vdk -27.2 %. The gut stage's fit (Task 6): -23.4 %, -10.5 %, -0.033, -0.029, vdk -21.2 %; under G's provisional
    # constants (Task 4): -21.8 %, -8.6 %, -0.030, -0.019, vdk -21.3 %; on the P model (Task 3): -21.5 %, -8.4 %, -0.028,
    # -0.019, vdk -21.2 %
    r = protein_at_equal_energy(host)
    check({"protein": r}, "belza_hp", "belza_mhp", "belza_mhp_above_hp", "smeets_30", "smeets_120")
    for k in ("belza_mhp", "belza_hp", "smeets_30", "smeets_120", "vdk"):
        assert near(r[k], PIN["protein"][k]), r
    for k in ("belza_mhp", "belza_hp", "vdk"):
        assert near(dist(r[k], STUDY[k]), DIST[k]), r


# --- the fat weight (ruling T2-3): S1228 and S1224 against the hunger nulls -----------------------------------------

def test_the_fat_weight_readings_are_pinned(host):
    # Ruling T3-3, Task 6's form: Melanson f - c >= 0; Diekmann HF - LF >= 0; Marmonier f - c within the difference
    # oracle's 1.5x; the fit residual is reported beside them. Ruling T2-3: Task 6 fits W_FAT between S1228 (Melanson 1999: fat's request 61 min after carbohydrate's) and S1224
    # (Marmonier 2000: fat's delay 9 min shorter than carbohydrate's), with the hunger nulls on the other side (S1810,
    # S1816, S1818, S1830) and S1828 reversed (more hunger after high fat, +6.94 mm on the 6 h mean, 0.0267 of the
    # scale, derived under ruling 11c-31). The refit (Task 6c fix 2) sets W_FAT 0.878683 (fix 1's 0.881368) with the two minute
    # differences on Melanson's 61 min scale (spec § 7): Melanson's fat minus carbohydrate reads -2 (-63 from the study)
    # and Marmonier's +4 (+13, past 1.5x), both named non-reproductions; Diekmann's HF minus LF +0.0031 (the study's
    # direction) holds. Task 6c's fit (W_FAT 0.894427): -2, +5 and +0.0030. The gut stage's fit (Task 6, W_FAT 0.405618 on Marmonier's own 9 min scale): -15, -6 and
    # +0.0025. At W_FAT 1, under G's provisional constants (Task 4): 0, +6 and +0.0023; on the P model (Task 3): 0, +8
    # and +0.0024
    mel = M.melanson(host)
    mar = M.marmonier(host)
    d = diekmann(host)
    check({"melanson": mel, "marmonier": mar, "diekmann": d}, "melanson_f_minus_c", "diekmann_hf_minus_lf",
          "marmonier_f_minus_c")
    got = {"melanson_f_minus_c": mel[1] - mel[0], "marmonier_f_minus_c": mar["f"] - mar["c"],
           "diekmann_hf_minus_lf": d["hf"]["mean"] - d["lf"]["mean"]}
    for k, x in got.items():
        assert near(x, PIN[k]), got
        assert near(dist(x, STUDY[k]), DIST[k]), got


# --- ruling 11g-3: the three non-reproductions, re-read --------------------------------------------------------------

def test_s1224_absolute_snack_delays_re_read(host):
    # S1224 (Marmonier 2000): the protein, carbohydrate and fat snacks delayed the dinner request 60, 34 and 25 min.
    # Re-read under the refit (ruling 11g-3, Task 6c fix 1 and fix 2 alike): 183 / 156 / 160 (+123 / +122 / +135), 3-7x long, so it
    # stays named (Task 6c's fit: 189 / 160 / 165). The gut stage's fit (Task 6): 149 / 132 / 126; under G's provisional constants (Task 4) 152 / 125 / 131; on
    # the P model (Task 3) 193 / 159 / 167
    d = M.marmonier(host)
    got = (d["p"], d["c"], d["f"])
    assert got == PIN["marmonier"], d
    assert dist(got, STUDY["marmonier"]) == DIST["marmonier"], d


def test_s1228_fasted_drinks_re_read(host):
    # S1228 (Melanson 1999): the request 65 min after the carbohydrate drink and 126 after the fat drink. Re-read under
    # the refit (ruling 11g-3, Task 6c fix 1): 219 / 217 (+154 / +91): the fat drink 1.7x long, the carbohydrate drink
    # 3.4x, so it stays named (Task 6c's fit: 217 / 215). The gut stage's fit (Task 6): 156 / 141; under G's provisional constants (Task 4) 329
    # for both; on the P model (Task 3) 236 for both
    got = tuple(M.melanson(host))
    assert got == PIN["melanson"], got
    assert dist(got, STUDY["melanson"]) == DIST["melanson"], got


def test_s1272_half_emptying_re_read(host):
    # S1272 (Moore 1981): 277 min solid half-emptying for the 1692 g meal. Re-read under the refit (ruling 11g-3,
    # Task 6c fix 1): 189 (-88), as on the P model and under G, so it stays named. A stomach reading: no satiety constant but
    # those of the stomach's fill enters it (M is fed at the eat and never feeds the drain)
    t = M.moore_half_emptying(host)
    assert t == PIN["moore"], t
    assert dist(t, STUDY["moore"]) == DIST["moore"], t


# --- the surplus day: Karl 2021's well-fed arm (S1325, S1871-S1875, S1892) ----------------------------------------

def test_karl_2021_well_fed_arm_at_the_eight_sampling_points(host):
    # S1325 (Karl 2021): hunger -55 % (95 % CI -73, -38) in BAL against REST. Task 6 asserts the mean over the study's
    # eight daily sampling points (before and after each meal and the morning exercise; research 03, difference 1) in
    # -64 % to -46 % (S1892, open: +/- 9 points, about one standard error, a labelled design choice). The refit
    # (Task 6c fix 2) read -54.49 % (fix 1's fit -54.47 %, Task 6c's -52.73 %) on the server path (test_replay_live_energy's twin K), and
    # -49.21 % under the deficit drive's refit on the deficit studies alone (Task 7, which holds the arm in this band as a constraint), inside: F counted past 730 g gives
    # BAL's fuller stomach its own fullness (spec § 7). The gut stage's fit (Task 6) -44.67 %, named; under G's
    # provisional constants (Task 4) -45.76 %; on the P model (Task 3) -45.08 %.
    # Shape checks, relative to REST (ruling T3-1: model HUNGER and the study's VAS / 10 are on different scales):
    # troughs_rel and pre_breakfast_rel against the figures derived from S1872 (troughs 0.215 / 0.209 / 0.106 over
    # REST's 2.71 cm; pre-breakfast 1.000 / 0.562 / 0.519 over REST's 5.18 cm) within gut_oracles.KARL_SHAPE_TOL, a
    # labelled DESIGN CHOICE (S1892). Under the deficit refit (Task 7): troughs_rel 0.536 / 0.432 / 0.457, all three named,
    # pre_breakfast_rel 1.000 / 0.721 / 0.763, days 2 and 3 named; per day -41.5 / -54.4 / -51.7 %.
    # The satiety refit (Task 6c fix 2): troughs_rel 0.522 / 0.362 / 0.388, days 1 and 3 named
    # (day 2 inside), pre_breakfast_rel 1.000 / 0.603 / 0.646, day 3 named; per day -42.6 / -61.8 / -59.1 % (study -46 /
    # -61 / -65). Fix 1's fit: troughs_rel 0.525 / 0.365 / 0.390, the rest alike to 0.1. Task 6c's fit: 0.548 / 0.381 / 0.408, 1.000 / 0.598 / 0.640, -40.1 / -60.4 / -57.6 %.
    # The gut stage's fit (Task 6): troughs_rel 0.887 / 0.609 / 0.652, all three named, pre_breakfast_rel 1.000 / 0.590 /
    # 0.632. Under G's provisional constants (Task 4) troughs_rel 0.877 / 0.592 / 0.634 and
    # pre_breakfast_rel 1.000 / 0.514 / 0.551; on the P model (Task 3) 0.865 / 0.601 / 0.643 and 1.000 / 0.599 / 0.641
    r = surplus_day(host)
    check({"karl": r}, "karl_bal")
    check_karl_shape(r)
    assert near(r["bal"], PIN["karl_bal"]) and near(r["rest"], PIN["karl_rest"]), r
    assert near_all(r["by_day"], PIN["karl_by_day"]), r
    assert near_all(r["troughs"], PIN["karl_troughs"]) and near(r["rest_trough"], PIN["karl_rest_trough"]), r
    assert near_all(r["pre_breakfast"], PIN["karl_pre_breakfast"]), r
    assert near(r["rest_pre_breakfast"], PIN["karl_rest_pre_breakfast"]), r
    assert near_all(r["troughs_rel"], PIN["karl_troughs_rel"]) and near_all(r["pre_breakfast_rel"], PIN["karl_pre_breakfast_rel"]), r
    assert near(dist(r["bal"], STUDY["karl_bal"]), DIST["karl_bal"]), r
    for k in ("by_day", "troughs_rel", "pre_breakfast_rel"):
        assert near_all(dist(tuple(r[k]), STUDY["karl_" + k]), DIST["karl_" + k]), (k, r)


# The readings under the refit meal pool M (Plan 11g Task 6c fix 2, fit-11g-20261012d; Karl's surplus day's under the
# deficit drive's refit, Task 7, fit-11g-deficit-20261012, re-pinned under Plan 13 Task 12's lean partition at the day
# close, its first moves at the 4th to 6th decimal; fix 1's fit-11g-20261012c and Task 6c's fit-11g-20261012b before it; the gut stage G's in Task 6, the provisional G's in Task 4, the P
# model's in Task 3 at the mod tree 44115b1a, d62ed4ea), to 9 decimals: PIN the readings, DIST their named distances to
# STUDY (model less study). The targets are asserted from the registry (gut_oracles.check).
PIN = {
    'cut20_mean': 0.017198996,
    'cut40_mean': 0.034933153,
    'cut20_at': [0.020461346, 0.019428265, 0.017534168, 0.015849054, 0.014350634],
    'cut40_at': [0.041467636, 0.03940724, 0.035630595, 0.032271906, 0.028236862],
    'tieken_solid_at': [-0.292458156, -0.238007373, -0.168276757, -0.101429669, -0.037077581],
    'tieken_liquid_at': [-0.377735055, -0.296824468, -0.200741067, -0.117139639, -0.043416512],
    'tieken_solid_back': 276,
    'tieken_liquid_back': 279,
    'diekmann_hf_at': [-0.600590382, -0.540000942, -0.424972183, -0.21622066, -0.030495647],
    'diekmann_lf_at': [-0.621820172, -0.559225491, -0.440476849, -0.225303806, -0.034278718],
    'diekmann_hf_back': 381,
    'diekmann_lf_back': 383,
    'nadir_minute': {'solid': 1, 'liquid': 1, 'hf': 1, 'lf': 1},
    'nadir_hunger': {'solid': 0.172547373, 'liquid': 0.148889013, 'hf': 0.084681493, 'lf': 0.078864622},
    'monotone': {'solid': True, 'liquid': True, 'hf': True, 'lf': True},
    'protein': {'belza_mhp': -0.076345732, 'belza_hp': -0.24681606, 'smeets_30': -0.026867065, 'smeets_120': -0.017954711, 'vdk': -0.280346256},
    'melanson_f_minus_c': -2,
    'marmonier_f_minus_c': 4,
    'diekmann_hf_minus_lf': 0.003145698,
    'marmonier': (183, 156, 160),
    'melanson': (219, 217),
    'moore': 189,
    # an unasserted reading: the same meals from a fasted start at 08:00 (M 0, circadian on), as Callahan's oracle reads
    'fasted_lewis': {'cut20_mean': 0.016045926, 'cut40_mean': 0.032596107,
                     'cut20_at': [0.018755232, 0.017860228, 0.016284631, 0.01494692, 0.013795954],
                     'cut40_at': [0.038014301, 0.0362312, 0.033096238, 0.030440071, 0.027151279]},
    'fasted_tieken': {'solid': ([-0.352134786, -0.299664094, -0.227775909, -0.152893625, -0.074723198], 300),
                      'liquid': ([-0.430224171, -0.35372768, -0.257924274, -0.167711007, -0.080822144], 302)},
    'fasted_diekmann': {'hf': ([-0.633988974, -0.577250398, -0.466143798, -0.246912023, -0.026811308], 375),
                        'lf': ([-0.653444393, -0.594919199, -0.480539613, -0.255641276, -0.030611033], 377)},
    'karl_bal': -49.210035778,
    'karl_by_day': [-41.469871886, -54.425662814, -51.734572633],
    'karl_rest': 0.150386219,
    'karl_troughs': [0.03978156, 0.032040739, 0.033929617],
    'karl_rest_trough': 0.074172944,
    'karl_pre_breakfast': [0.281351652, 0.20277995, 0.214805136],
    'karl_rest_pre_breakfast': 0.281351652,
    'karl_troughs_rel': [0.536335194, 0.431973402, 0.457439268],
    'karl_pre_breakfast_rel': [1.0, 0.720734883, 0.763475654],
}
DIST = {
    'cut40': 0.015702383,
    'cut20': -0.002031773,
    'tieken_liquid_4h': -0.183416512,
    'tieken_solid_4h': 0.412922419,
    'diekmann_hf_back': 21,
    'diekmann_lf_back': 23,
    'belza_mhp': 0.073654268,
    'belza_hp': 0.00318394,
    'vdk': -0.280346256,
    'melanson_f_minus_c': -63,
    'marmonier_f_minus_c': 13,
    'diekmann_hf_minus_lf': -0.023563704,
    'marmonier': (123, 122, 135),
    'melanson': (154, 91),
    'moore': -88,
    'karl_bal': 5.789964222,
    'karl_by_day': (4.530128114, 6.574337186, 13.265427367),
    'karl_troughs_rel': (0.321335194, 0.222973402, 0.351439268),
    'karl_pre_breakfast_rel': (0.0, 0.158734883, 0.244475654),
}


# --- the stability checks (Plan 11g spec § 7, Task 6c) --------------------------------------------------------------
# DESIGN CHOICES in the registry (gut_oracles.stability), so no later fit can go flat unseen: the Task 6 fit of the gut
# stage G read the 650 kcal meal at 19:00 back at 954 / 303 / 282 min under hunger x0.98 / x1.00 / x1.02 and hunger
# 0.265 at +24 h (the P model 311 / 296 / 281 and 0.422).

def test_the_stability_checks_hold(host):
    # the refit (fit-11g-20261012d, Plan 11g Task 6c fix 2): back at 298 / 282 / 266 min (latest 298 <= 425, S1248;
    # spread 32 <= 60) and hunger 0.3959 at +24 h after one 650 kcal meal at 08:00 (>= 0.378); fix 1's fit read 299 /
    # 282 / 267 and 0.3944, Task 6c's 291 / 277 / 265 and 0.4948
    from . import gut_oracles as GOR
    r = {"stability": GOR.stability(host)}
    got = check(r, "stability_latest", "stability_spread", "stability_rise")
    assert r["stability"]["back"] == [298, 282, 266], r
    assert got["stability_spread"] == 32 and round(got["stability_rise"], 4) == 0.3959, got


def test_a_flat_read_fails_the_stability_checks(host):
    # the Task 6 fit's flat exponent (MEAL_STEEP 0.019723) on the refit's other constants: the fasting rise falls to
    # 0.316 (0.313 under Task 6c's), under the check's 0.378, so the registry rejects it
    from . import gut_oracles as GOR
    S = host.K.satiety
    keep = S.MEAL_STEEP
    S.MEAL_STEEP = 0.019723
    try:
        r = {"stability": GOR.stability(host)}
    finally:
        S.MEAL_STEEP = keep
    assert GOR.BY_NAME["stability_rise"].miss(r["stability"]["rise"]) > 0, r
    assert round(r["stability"]["rise"], 3) == 0.316, r
