"""The gut-satiety oracles (Plan 11g Task 3; spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 4; rulings
11g-2 and 11g-3): the new study oracles of the gut stage G, encoded from the minted rows (S1799-S1894, Plan 11g Task 2)
before any model change and pinned at the P model (meal pool P fed in full at the eat, HALF_LIFE_H 0.7 h). Each
test pins today's reading and its distance to the study figure, so a change is noticed; its comment names the study
row, the target, and the tolerance Task 6 will assert. A tolerance no row evidences is labelled a design choice.
Plan 11g Task 4 re-pinned every reading under the gut stage G (fed at emptying) with its provisional constants
(G_HALF_LIFE_H 0.7, G_REQ 6, G_STEEP 0.05, G_SEED_MAX 1300: the P fits carried over); each test's comment gives the
G reading beside the P model's (Task 3's), and Task 6 turns each into the target its comment names. STUDY and the
distances' definitions are unchanged; DIST is re-pinned with PIN.
STUDY and VAS_DETECT live in gut_oracles.py since Plan 11g Task 5, beside the oracle registry the joint fit
(tools/fit_gut_satiety.py) scores, so a target lives in one place.

The replays are the existing ones, reused, not copied:
- the time courses and the protein contrast run test_satiety_meal_studies.py's satiety replay (REPLAY: one step a game
  minute, the eats landing in the stomach, the drain feeding G, G's clearance, F and the displayed hunger), under its
  protocol: from the request (displayed HUNGER 0.25, an empty stomach, G seeded at the request), the circadian factor
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
uncapped) is in its report.
"""
from . import test_replay_live_energy as E
from . import test_satiety_meal_studies as M
from .gut_oracles import STUDY, VAS_DETECT

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

FASTED = {"G0": 0.0, "h0": 8.0}     # a fasted start at 08:00, as Callahan's oracle reads (test_satiety_meal_studies.callahan)


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
    return [[rows[m]["HUNGER"] for m in E.karl_vas(d * 1440, am_dur)] for d in range(E.KARL_WARM, days)]


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
    # 260 mm a unit). Under G (Task 4, provisional constants): cut40 0.0347 (9.0 mm), cut20 0.0172 (4.5 mm, 0.0020
    # under the threshold): the pattern holds, with little margin on the 20 % side. On the P model (Task 3): cut40
    # 0.0370 (9.6 mm), cut20 0.0181 (4.7 mm, 0.0011 under)
    r = meal_sizes(host)
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
    # TIEKEN_T. Under G (Task 4, provisional constants) both arms read about -13.5 % at 4 h (liquid -27.9 points from
    # the study, solid +31.6), the liquid lower than the solid at every time point (its 553 g fill the stomach more),
    # and both back at the request at 471 / 473 min. On the P model (Task 3): both about -6 % at 4 h (liquid -20
    # points, solid +39), the liquid lower, back near 293 min
    r = tieken(host)
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
    # the scaling: the rows give no ratio). Under G (Task 4, provisional constants) both arms are about -17.5 % at 6 h
    # and back at 616 min (+256 past 360), against Tieken's 471 / 473. On the P model (Task 3): about -5 % at 6 h and
    # back at 391 / 392 min (+31 / +32), against Tieken's 292 / 295
    r = diekmann(host)
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
    # its hunger and whether hunger never falls after it. Under G (Task 4, provisional constants) the nadirs fall at
    # minutes 22 (solid), 12 (liquid), 42 (HF) and 52 (LF), G rising while the meal empties, and every recovery is
    # monotone. On the P model (Task 3) every nadir was the first minute (P fed in full at the eat)
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
    # vdk is read, never asserted. Under G (Task 4, provisional constants): belza_hp -21.8 % (+3.2 points from Belza),
    # belza_mhp -8.6 % (+6.4), Smeets -0.030 and -0.019, and vdk -21.3 % where the study reads no difference. On the P
    # model (Task 3): belza_hp -21.5 %, belza_mhp -8.4 %, Smeets -0.028 and -0.019, vdk -21.2 %
    r = protein_at_equal_energy(host)
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
    # scale, derived under ruling 11c-31). W_FAT is 1: under G (Task 4, provisional constants) Melanson's fat minus
    # carbohydrate reads 0 (-61 from the study), Marmonier's +6 (+15), Diekmann's HF minus LF +0.0023 (the study's
    # direction, -0.024 from its size). On the P model (Task 3): 0, +8 and +0.0024
    mel = M.melanson(host)
    mar = M.marmonier(host)
    d = diekmann(host)
    got = {"melanson_f_minus_c": mel[1] - mel[0], "marmonier_f_minus_c": mar["f"] - mar["c"],
           "diekmann_hf_minus_lf": d["hf"]["mean"] - d["lf"]["mean"]}
    for k, x in got.items():
        assert near(x, PIN[k]), got
        assert near(dist(x, STUDY[k]), DIST[k]), got


# --- ruling 11g-3: the three non-reproductions, re-read --------------------------------------------------------------

def test_s1224_absolute_snack_delays_re_read(host):
    # S1224 (Marmonier 2000): the protein, carbohydrate and fat snacks delayed the dinner request 60, 34 and 25 min.
    # Under G (Task 4, provisional constants) 152 / 125 / 131 (+92 / +91 / +106); on the P model (Task 3) 193 / 159 /
    # 167 (+133 / +125 / +142). Task 6: a target within 1.5x (the difference oracle's tolerance) if
    # G reproduces them, otherwise named with the new reading (ruling 11g-3)
    d = M.marmonier(host)
    got = (d["p"], d["c"], d["f"])
    assert got == PIN["marmonier"], d
    assert dist(got, STUDY["marmonier"]) == DIST["marmonier"], d


def test_s1228_fasted_drinks_re_read(host):
    # S1228 (Melanson 1999): the request 65 min after the carbohydrate drink and 126 after the fat drink. Under G (Task
    # 4, provisional constants) 329 for both (+264 / +203); on the P model (Task 3) 236 for both (+171 / +110). Task 6:
    # a target within 1.5x if G reaches it, otherwise named (ruling 11g-3)
    got = tuple(M.melanson(host))
    assert got == PIN["melanson"], got
    assert dist(got, STUDY["melanson"]) == DIST["melanson"], got


def test_s1272_half_emptying_re_read(host):
    # S1272 (Moore 1981): 277 min solid half-emptying for the 1692 g meal. Today 189 (-88), on the P model and under G
    # alike. A stomach reading: G does not enter it, so the G_HALF_LIFE_H mutation leaves it unmoved (G is fed by the
    # drain, never the reverse; ruling 11g-3)
    t = M.moore_half_emptying(host)
    assert t == PIN["moore"], t
    assert dist(t, STUDY["moore"]) == DIST["moore"], t


# --- the surplus day: Karl 2021's well-fed arm (S1325, S1871-S1875, S1892) ----------------------------------------

def test_karl_2021_well_fed_arm_at_the_eight_sampling_points(host):
    # S1325 (Karl 2021): hunger -55 % (95 % CI -73, -38) in BAL against REST. Task 6 asserts the mean over the study's
    # eight daily sampling points (before and after each meal and the morning exercise; research 03, difference 1) in
    # -64 % to -46 % (S1892, open: +/- 9 points, about one standard error, a labelled design choice). Under G (Task 4,
    # provisional constants) -45.76 % on the server path (test_replay_live_energy's twin K), +9.2 points from the
    # study and 0.24 outside the band's -46 edge; on the P model (Task 3) -45.08 %, +9.9 and 0.9 outside. Shape checks, relative to REST (ruling T3-1: model HUNGER and the study's VAS / 10 are on different
    # scales, REST reading 0.085 at the troughs against the study's 0.271): Task 6 asserts BAL / REST at each point,
    # troughs_rel and pre_breakfast_rel against the figures derived from S1872 (troughs 0.215 / 0.209 / 0.106 over
    # REST's 2.71 cm; pre-breakfast 1.000 / 0.562 / 0.519 over REST's 5.18 cm), at a tolerance that is a labelled DESIGN
    # CHOICE (S1892). Under G (Task 4, provisional constants) troughs_rel 0.877 / 0.592 / 0.634 and pre_breakfast_rel
    # 1.000 / 0.514 / 0.551 (the relative shape is the open misfit); the absolute troughs 0.085 / 0.057 / 0.061 and
    # pre-breakfast 0.240 / 0.123 / 0.132 are pinned as readings only; per day -29.7 / -55.4 / -52.2 % (study -46 /
    # -61 / -65). On the P model (Task 3): troughs_rel 0.865 / 0.601 / 0.643, pre_breakfast_rel 1.000 / 0.599 /
    # 0.641, per day -30.6 / -53.9 / -50.7 %
    r = surplus_day(host)
    assert near(r["bal"], PIN["karl_bal"]) and near(r["rest"], PIN["karl_rest"]), r
    assert near_all(r["by_day"], PIN["karl_by_day"]), r
    assert near_all(r["troughs"], PIN["karl_troughs"]) and near(r["rest_trough"], PIN["karl_rest_trough"]), r
    assert near_all(r["pre_breakfast"], PIN["karl_pre_breakfast"]), r
    assert near(r["rest_pre_breakfast"], PIN["karl_rest_pre_breakfast"]), r
    assert near_all(r["troughs_rel"], PIN["karl_troughs_rel"]) and near_all(r["pre_breakfast_rel"], PIN["karl_pre_breakfast_rel"]), r
    assert near(dist(r["bal"], STUDY["karl_bal"]), DIST["karl_bal"]), r
    for k in ("by_day", "troughs_rel", "pre_breakfast_rel"):
        assert near_all(dist(tuple(r[k]), STUDY["karl_" + k]), DIST["karl_" + k]), (k, r)


# The readings under G with the provisional constants (Plan 11g Task 4; the P model's were pinned in Task 3 at the mod
# tree 44115b1a, d62ed4ea), to 9 decimals: PIN the readings, DIST their named distances to STUDY (model less study).
# Task 6 turns each into the target its test names.
PIN = {
    'cut20_mean': 0.017234316,
    'cut40_mean': 0.034748304,
    'cut20_at': [0.022126648, 0.020332514, 0.017578484, 0.015353387, 0.013471594],
    'cut40_at': [0.044556727, 0.040969296, 0.03545166, 0.030991527, 0.026787646],
    'tieken_solid_at': [-0.264489444, -0.250484134, -0.210774103, -0.170716798, -0.133613078],
    'tieken_liquid_at': [-0.34050973, -0.300858654, -0.238475769, -0.184421231, -0.139338423],
    'tieken_solid_back': 471,
    'tieken_liquid_back': 473,
    'diekmann_hf_at': [-0.596079897, -0.568363772, -0.469931933, -0.303354712, -0.173294134],
    'diekmann_lf_at': [-0.596079897, -0.588411638, -0.485310004, -0.311544041, -0.176128512],
    'diekmann_hf_back': 616,
    'diekmann_lf_back': 616,
    'nadir_minute': {'solid': 22, 'liquid': 12, 'hf': 42, 'lf': 52},
    'nadir_hunger': {'solid': 0.183525664, 'liquid': 0.164767196, 'hf': 0.100179655, 'lf': 0.099666129},
    'monotone': {'solid': True, 'liquid': True, 'hf': True, 'lf': True},
    'protein': {'belza_mhp': -0.085958219, 'belza_hp': -0.217888627, 'smeets_30': -0.029792299, 'smeets_120': -0.018672617, 'vdk': -0.212950661},
    'melanson_f_minus_c': 0,
    'marmonier_f_minus_c': 6,
    'diekmann_hf_minus_lf': 0.002331459,
    'marmonier': (152, 125, 131),
    'melanson': (329, 329),
    'moore': 189,
    # an unasserted reading: the same meals from a fasted start at 08:00 (G 0, circadian on), as Callahan's oracle reads
    'fasted_lewis': {'cut20_mean': 0.016074644, 'cut40_mean': 0.032413661,
                     'cut20_at': [0.020337078, 0.018709377, 0.01632602, 0.014474725, 0.012944126],
                     'cut40_at': [0.040971145, 0.03770609, 0.032927991, 0.029218784, 0.025739801]},
    'fasted_tieken': {'solid': ([-0.323824685, -0.310705567, -0.267177734, -0.218266945, -0.167585881], 427),
                      'liquid': ([-0.393807644, -0.357052444, -0.292906317, -0.231188362, -0.173087953], 428)},
    'fasted_diekmann': {'hf': ([-0.629366432, -0.603128153, -0.507846054, -0.330678394, -0.170224307], 525),
                        'lf': ([-0.629366432, -0.621561346, -0.522124179, -0.338546524, -0.17306921], 525)},
    'karl_bal': -45.764187927,
    'karl_by_day': [-29.6522792, -55.390513371, -52.249771209],
    'karl_rest': 0.142558159,
    'karl_troughs': [0.084663563, 0.057156037, 0.061171432],
    'karl_rest_trough': 0.096551108,
    'karl_pre_breakfast': [0.240208468, 0.123490557, 0.132244453],
    'karl_rest_pre_breakfast': 0.240208468,
    'karl_troughs_rel': [0.876878205, 0.591977013, 0.633565299],
    'karl_pre_breakfast_rel': [1.0, 0.514097435, 0.550540346],
}
DIST = {
    'cut40': 0.015517534,
    'cut20': -0.001996454,
    'tieken_liquid_4h': -0.279338423,
    'tieken_solid_4h': 0.316386922,
    'diekmann_hf_back': 256,
    'diekmann_lf_back': 256,
    'belza_mhp': 0.064041781,
    'belza_hp': 0.032111373,
    'vdk': -0.212950661,
    'melanson_f_minus_c': -61,
    'marmonier_f_minus_c': 15,
    'diekmann_hf_minus_lf': -0.024377942,
    'marmonier': (92, 91, 106),
    'melanson': (264, 203),
    'moore': -88,
    'karl_bal': 9.235812073,
    'karl_by_day': (16.3477208, 5.609486629, 12.750228791),
    'karl_troughs_rel': (0.661878205, 0.382977013, 0.527565299),
    'karl_pre_breakfast_rel': (0.0, -0.047902565, 0.031540346),
}
