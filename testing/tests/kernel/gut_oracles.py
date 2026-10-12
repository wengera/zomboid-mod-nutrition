"""The gut-satiety oracle registry (Plan 11g Task 5; spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 4;
rulings 11g-2, 11g-3, T2-3, T3-1, T3-3): one table of every oracle the joint fit (tools/fit_gut_satiety.py) scores and
Task 6's assertions read, so a target lives in one place. STUDY, the study figures test_satiety_gut_oracle.py's named
distances are read against, lives here too, and that module imports it.

An oracle is a name, the reading group it is picked from, its study figure (`target`), its tolerance as a band
(`lo`, `hi`; one bound None for a one-sided check), the `scale` its miss is relative to, its kind ("two-sided",
"one-sided" or "reading") and its row id. The readings are the oracle modules' own functions, run on whatever host is
passed (the kernel tests' `host`, or the fit's patched one), so the tests and the fit compute identical numbers; the
surplus day runs on the server path (tools/replay_live.py), whatever host is passed.

The miss (the fit's loss term): how far the reading sits outside its band, over the oracle's scale (the study figure's
size unless the entry says otherwise), 0 inside the band; a reading of None (the request never returned inside the
replay) misses NONE_MISS. A ratio tolerance t on a figure s is the band [s / t, s x t] (sorted for a negative s), so the
miss above it is r - t and below it 1 / t - r, r = model / s: continuous through a sign change, where the worse-way
ratio is not. A reading-kind entry is reported, never in the loss. Every hard and one-sided oracle counts at weight 1.

The bands that are not a row's own figure are labelled DESIGN CHOICE beside their entry.
"""
import math

from . import test_satiety_meal_studies as M

NONE_MISS = 10.0                # a reading of None: the request never came back inside the replay (a DESIGN CHOICE: worse
                                # than any finite miss the fit meets on the provisional constants)
VAS_DETECT = 5.0 / M.MM_PER_HUNGER   # a DESIGN CHOICE (no row): 5 mm of VAS, read under ruling 11c-31's 260 mm a unit, as
                                     # the smallest mean hunger difference a single crossover of S1809's size detects

# --- the study figures each distance is read against ---------------------------------------------------------------

STUDY = {
    "tieken_liquid_4h": 0.14,          # S1833: +14 +/- 10 % above fasting at 4 h after the liquid
    "tieken_solid_4h": -0.45,          # S1833: -45 +/- 19 % below fasting at 4 h after the solid
    "diekmann_6h_min": 360,            # S1828: still below baseline at 6.0 h (a recovery minute after 360)
    "belza_mhp": -0.15,                # S1820: hunger -15 % at 25 % protein against 14 %
    "belza_hp": -0.25,                 # S1820: hunger -25 % at 50 % protein against 14 %
    "vdk": 0.0,                        # S1818: no difference (AUC P = 0.634)
    "melanson_f_minus_c": 126 - 65,    # S1228: the fat drink's request 61 min later than the carbohydrate drink's
    "marmonier_f_minus_c": 25 - 34,    # S1224: the fat snack's delay 9 min shorter than the carbohydrate snack's
    "diekmann_hf_minus_lf": 250.0 / 360 * 10 / M.MM_PER_HUNGER,   # S1828: HF minus LF hunger iAUC +250 min x score
                                                # (0-10 scale) over 6 h: 6.94 mm mean, derived (x10 mm a score), read
                                                # under ruling 11c-31's 260 mm a unit
    "marmonier": (60, 34, 25),         # S1224: the protein, carbohydrate and fat snacks' delays (min)
    "melanson": (65, 126),             # S1228: the carbohydrate and fat drinks' requests (min)
    "moore": 277,                      # S1272: the 1692 g meal's solid half-emptying (min)
    "karl_bal": -55.0,                 # S1325: BAL against REST (%)
    "karl_by_day": (-46.0, -61.0, -65.0),       # S1892 (derived from S1872's read): per day (%)
    "karl_troughs_rel": (0.215, 0.209, 0.106),     # derived from S1872: BAL's post-meal means (0.058, 0.057, 0.029,
                                                   # cm / 10) over REST's (2.25 + 2.35 + 3.53) / 3 = 2.71 cm
    "karl_pre_breakfast_rel": (1.000, 0.562, 0.519),   # derived from S1872: BAL's pre-breakfast (0.518, 0.291, 0.269)
                                                       # over REST's 5.18 cm
}

# the meal studies' figures live in test_satiety_meal_studies.py (the hard replays and their tests read the same tuples)
CALLAHAN = M.CALLAHAN_MIN
MEAL650 = M.MEAL650_MIN
ROLLS_1999 = M.ROLLS_1999
ROLLS_1998 = M.ROLLS_1998
MARMONIER_DIFF = M.MARMONIER_DIFF
S1222 = M.S1222_BAND


# --- the readings: each group run once per host ----------------------------------------------------------------------

def _gut():
    from . import test_satiety_gut_oracle as GO    # imported late: that module imports STUDY from here
    return GO


GROUPS = {
    "callahan": lambda h: M.callahan(h),
    "callahan_fasted": lambda h: M.callahan(h, fasted=True),
    "breakfast400": M.breakfast400,
    "meal650": lambda h: M.request(M.hunger(h, {0: [("food", M.mixed(650))]}, 900)),
    "rolls_1999": M.rolls_1999,
    "rolls_1998": M.rolls_1998,
    "marmonier": M.marmonier,
    "melanson": M.melanson,
    "moore": M.moore_half_emptying,
    "protein_contrast": M.protein_contrast,
    "meal_sizes": lambda h: _gut().meal_sizes(h),
    "tieken": lambda h: _gut().tieken(h),
    "diekmann": lambda h: _gut().diekmann(h),
    "protein": lambda h: _gut().protein_at_equal_energy(h),
    "karl": lambda h: _gut().surplus_day(h),        # the server path (tools/replay_live.py); the host is not read
}


def read_all(host):
    """Every reading group on `host`, by name."""
    return {name: fn(host) for name, fn in GROUPS.items()}


# --- the oracles -----------------------------------------------------------------------------------------------------

class Oracle:
    def __init__(self, name, group, pick, target, lo=None, hi=None, scale=None, kind="two-sided", row="", tol="",
                 none_is="miss"):
        self.name, self.group, self.pick, self.target = name, group, pick, target
        self.lo, self.hi, self.kind, self.row, self.tol = lo, hi, kind, row, tol
        self.none_is = none_is          # "miss": a None reading misses NONE_MISS; "inf": it is +inf (never returns)
        self.scale = scale
        if scale is None and kind != "reading":
            self.scale = abs(target)
        assert self.kind == "reading" or self.scale > 0, "oracle %s: scale %r is not positive" % (name, self.scale)

    def miss(self, value):
        """The relative miss beyond the tolerance: 0 inside the band; None for a reading-kind entry."""
        if self.kind == "reading":
            return None
        if value is None:
            if self.none_is != "inf":
                return NONE_MISS
            value = math.inf
        elif math.isnan(value) or math.isinf(value) and not (value > 0 and self.none_is == "inf"):
            return NONE_MISS            # a NaN or an infinite reading (+inf passes only where it means "never returns")
        out = 0.0
        if self.lo is not None and value < self.lo:
            out = self.lo - value
        if self.hi is not None and value > self.hi:
            out = value - self.hi
        return out / self.scale


def ratio_oracle(name, group, pick, target, tol, row):
    """Within `tol` x of `target`, the worse way: the band [target / tol, target x tol]."""
    a, b = sorted((target / tol, target * tol))
    return Oracle(name, group, pick, target, lo=a, hi=b, kind="two-sided", row=row, tol="%gx" % tol)


def _sub(group, *keys):
    def pick(r):
        x = r[group]
        for k in keys:
            if x is None:
                return None
            x = x[k]
        return x
    return pick


def _diff(a, b):
    return None if a is None or b is None else a - b


def _later_minus_earlier(later, earlier):
    """later - earlier for two return minutes, None being "never returns" (+inf; a none_is="inf" oracle's pick): a None
    later arm passes (+inf), a None earlier arm only gives -inf (a miss), both None is -inf (NONE_MISS)."""
    later = math.inf if later is None else later
    earlier = math.inf if earlier is None else earlier
    if math.isinf(later) and math.isinf(earlier):
        return -math.inf
    return later - earlier


def _min_back(r):
    """The earlier of the two Diekmann arms' recoveries; None is +inf (the arm never returns)."""
    return min(math.inf if x is None else x for x in (r["diekmann"]["hf"]["back"], r["diekmann"]["lf"]["back"]))


ORACLES = []
for _i, _k in enumerate((190, 400, 825)):
    ORACLES.append(ratio_oracle("callahan_%d" % _k, "callahan", _sub("callahan", _i), CALLAHAN[_i], M.TOL, "S1247"))
for _i, _k in enumerate((190, 400, 825)):
    ORACLES.append(ratio_oracle("callahan_fasted_%d" % _k, "callahan_fasted", _sub("callahan_fasted", _i), CALLAHAN[_i],
                                M.TOL, "S1247"))
ORACLES += [
    # the 400 kcal breakfast's hold (test_a_fasted_400_kcal_breakfast_holds_hunger_below_the_request_for_three_hours; ruling
    # T5-2): an asserted test with no row of its own, so it joins the loss as a one-sided entry on the shorter hold
    Oracle("breakfast400_held", "breakfast400", lambda r: min(d for _, d in r["breakfast400"]), M.BREAKFAST_HOLD_MIN,
           lo=M.BREAKFAST_HOLD_MIN, scale=M.BREAKFAST_HOLD_MIN, kind="one-sided", row="",
           tol=">= 180 min at h0 None and 8.0 (the existing test's assertion, no row)"),
    Oracle("meal650", "meal650", _sub("meal650"), sum(MEAL650) / 2, lo=MEAL650[0] / M.TOL, hi=MEAL650[1] * M.TOL,
           row="S1247, S1248", tol="1.1x of 240-300"),
    ratio_oracle("rolls_soup", "rolls_1999", _sub("rolls_1999", "soup"), ROLLS_1999["soup"], M.TOL, "S1231"),
    ratio_oracle("rolls_cw", "rolls_1999", _sub("rolls_1999", "cw"), ROLLS_1999["cw"], M.TOL, "S1231"),
    ratio_oracle("rolls_cas", "rolls_1999", _sub("rolls_1999", "cas"), ROLLS_1999["cas"], M.TOL, "S1231"),
    ratio_oracle("rolls_drop", "rolls_1999", lambda r: r["rolls_1999"]["cw"] - r["rolls_1999"]["soup"],
                 ROLLS_1999["cw"] - ROLLS_1999["soup"], M.TOL, "S1231"),
]
for _i, _ml in enumerate((300, 450, 600)):
    ORACLES.append(ratio_oracle("rolls98_%d" % _ml, "rolls_1998", _sub("rolls_1998", _i), ROLLS_1998[_i], M.CHECK_TOL,
                                "S1233"))
ORACLES += [
    # S1233's ordering, 300 > 450 > 600 mL (ruling T5-2; test_rolls_1998_milk_volume_check asserts it): the smaller of
    # the two steps at or above 0, its scale the study's smaller step (a DESIGN CHOICE)
    Oracle("rolls98_ordering", "rolls_1998", lambda r: min(r["rolls_1998"][0] - r["rolls_1998"][1],
                                                           r["rolls_1998"][1] - r["rolls_1998"][2]),
           0.0, lo=0.0, scale=min(ROLLS_1998[0] - ROLLS_1998[1], ROLLS_1998[1] - ROLLS_1998[2]), kind="one-sided",
           row="S1233", tol="300 > 450 > 600 mL"),
    Oracle("s1222_contrast", "protein_contrast", _sub("protein_contrast"), 0.025, lo=S1222[0], hi=S1222[1],
           row="S1222", tol="0.0125-0.04"),
    ratio_oracle("marmonier_pc", "marmonier", lambda r: _diff(r["marmonier"]["p"], r["marmonier"]["c"]),
                 MARMONIER_DIFF[0], 1.5, "S1224"),
    ratio_oracle("marmonier_pf", "marmonier", lambda r: _diff(r["marmonier"]["p"], r["marmonier"]["f"]),
                 MARMONIER_DIFF[1], 1.5, "S1224"),
    # S1809 (Lewis 2015): the 40 % cut detectable at every time point and on its 30-240 min mean, the 20 % cut not
    Oracle("lewis_cut40_at", "meal_sizes", lambda r: min(r["meal_sizes"]["cut40"]["at"]), 0.0, lo=0.0,
           scale=VAS_DETECT, kind="one-sided", row="S1809", tol=">= 0 at each of 30-240 min"),
    Oracle("lewis_cut40_mean", "meal_sizes", _sub("meal_sizes", "cut40", "mean"), VAS_DETECT, lo=VAS_DETECT,
           kind="one-sided", row="S1809", tol=">= VAS_DETECT"),
    Oracle("lewis_cut20_mean", "meal_sizes", _sub("meal_sizes", "cut20", "mean"), VAS_DETECT, hi=VAS_DETECT,
           kind="one-sided", row="S1809", tol="<= VAS_DETECT"),
    # S1833 (Tieken 2007): each arm's 4 h reading within the row's spread (a DESIGN CHOICE: the spread as the
    # tolerance), the solid below the liquid at each rating time (the scale the study's 4 h gap, a DESIGN CHOICE)
    Oracle("tieken_liquid_4h", "tieken", lambda r: r["tieken"]["liquid"]["at"][-1], STUDY["tieken_liquid_4h"],
           lo=0.04, hi=0.24, row="S1833", tol="+/- 0.10"),
    Oracle("tieken_solid_4h", "tieken", lambda r: r["tieken"]["solid"]["at"][-1], STUDY["tieken_solid_4h"],
           lo=-0.64, hi=-0.26, row="S1833", tol="+/- 0.19"),
    Oracle("tieken_solid_below_liquid", "tieken",
           lambda r: min(b - a for a, b in zip(r["tieken"]["solid"]["at"], r["tieken"]["liquid"]["at"])),
           STUDY["tieken_liquid_4h"] - STUDY["tieken_solid_4h"], lo=0.0, kind="one-sided", row="S1833",
           tol="liquid - solid >= 0 at each rating time"),
    # S1828 (Diekmann 2026): both arms still below the request at 6 h; the 1,000 kcal recovery later than the 540 kcal
    # liquid's (S1840's scaling with emptying; the ordering a DESIGN CHOICE, the rows give no ratio; its scale the 2 h
    # between harvest 11 § 6's about 4 h and over 6 h)
    Oracle("diekmann_hf_6h", "diekmann", _sub("diekmann", "hf", "back"), STUDY["diekmann_6h_min"],
           lo=STUDY["diekmann_6h_min"] + 1, kind="one-sided", row="S1828", tol="recovery after 360 min",
           none_is="inf"),
    Oracle("diekmann_lf_6h", "diekmann", _sub("diekmann", "lf", "back"), STUDY["diekmann_6h_min"],
           lo=STUDY["diekmann_6h_min"] + 1, kind="one-sided", row="S1828", tol="recovery after 360 min",
           none_is="inf"),
    Oracle("diekmann_after_tieken", "diekmann",
           lambda r: _later_minus_earlier(_min_back(r), r["tieken"]["liquid"]["back"]),
           120.0, lo=0.0, scale=120.0, kind="one-sided", row="S1828, S1833, S1840", tol=">= 0 min", none_is="inf"),
    # S1820 (Belza 2013) and the nulls (S1818, S1821, S1814, S1225): belza_hp in [-0.25, 0] and belza_mhp in
    # [belza_hp, 0] (a DESIGN CHOICE between the two sides); S1822 (Smeets 2008) the HP arm at or below AP at 30 and
    # 120 min (the row rates satiety, so its scale is VAS_DETECT, a DESIGN CHOICE)
    Oracle("belza_hp", "protein", _sub("protein", "belza_hp"), STUDY["belza_hp"], lo=-0.25, hi=0.0, row="S1820",
           tol="[-0.25, 0]"),
    Oracle("belza_mhp", "protein", _sub("protein", "belza_mhp"), STUDY["belza_mhp"], hi=0.0, kind="one-sided",
           row="S1820", tol="<= 0"),
    Oracle("belza_mhp_above_hp", "protein", lambda r: r["protein"]["belza_mhp"] - r["protein"]["belza_hp"],
           STUDY["belza_mhp"] - STUDY["belza_hp"], lo=0.0, kind="one-sided", row="S1820", tol=">= belza_hp"),
    Oracle("smeets_30", "protein", _sub("protein", "smeets_30"), 0.0, hi=0.0, scale=VAS_DETECT, kind="one-sided",
           row="S1822", tol="<= 0"),
    Oracle("smeets_120", "protein", _sub("protein", "smeets_120"), 0.0, hi=0.0, scale=VAS_DETECT, kind="one-sided",
           row="S1822", tol="<= 0"),
    # S1325 (Karl 2021): BAL against REST at the eight sampling points within -64 % to -46 % (S1892, open: +/- 9
    # points, about one standard error, a labelled DESIGN CHOICE)
    Oracle("karl_bal", "karl", _sub("karl", "bal"), STUDY["karl_bal"], lo=-64.0, hi=-46.0, row="S1325, S1892",
           tol="-64 to -46 %"),
    # the fat trio (ruling T3-3; ruling T2-3's W_FAT fit): Melanson f - c >= 0, Diekmann HF - LF >= 0, Marmonier f - c
    # within the difference oracle's 1.5x
    Oracle("melanson_f_minus_c", "melanson", lambda r: _later_minus_earlier(r["melanson"][1], r["melanson"][0]),
           STUDY["melanson_f_minus_c"], lo=0.0, kind="one-sided", row="S1228", tol=">= 0", none_is="inf"),
    Oracle("diekmann_hf_minus_lf", "diekmann", lambda r: r["diekmann"]["hf"]["mean"] - r["diekmann"]["lf"]["mean"],
           STUDY["diekmann_hf_minus_lf"], lo=0.0, kind="one-sided", row="S1828", tol=">= 0"),
    ratio_oracle("marmonier_f_minus_c", "marmonier", lambda r: _diff(r["marmonier"]["f"], r["marmonier"]["c"]),
                 float(STUDY["marmonier_f_minus_c"]), 1.5, "S1224"),
    # reported, never in the loss: harvest 11 § 7's nadir (inference), van der Klaauw's null, Karl's per-day shape
    # (ruling T3-1), and ruling 11g-3's three non-reproductions
    Oracle("nadir_minutes", "tieken", lambda r: [r["tieken"]["solid"]["nadir"][0], r["tieken"]["liquid"]["nadir"][0],
                                                 r["diekmann"]["hf"]["nadir"][0], r["diekmann"]["lf"]["nadir"][0]],
           15, kind="reading", row="S1833"),
    Oracle("vdk", "protein", _sub("protein", "vdk"), STUDY["vdk"], kind="reading", row="S1818"),
    Oracle("karl_by_day", "karl", _sub("karl", "by_day"), STUDY["karl_by_day"], kind="reading", row="S1892"),
    Oracle("karl_troughs_rel", "karl", _sub("karl", "troughs_rel"), STUDY["karl_troughs_rel"], kind="reading",
           row="S1872"),
    Oracle("karl_pre_breakfast_rel", "karl", _sub("karl", "pre_breakfast_rel"), STUDY["karl_pre_breakfast_rel"],
           kind="reading", row="S1872"),
    Oracle("marmonier_delays", "marmonier", lambda r: [r["marmonier"][k] for k in ("p", "c", "f")],
           STUDY["marmonier"], kind="reading", row="S1224"),
    Oracle("melanson_requests", "melanson", lambda r: list(r["melanson"]), STUDY["melanson"], kind="reading",
           row="S1228"),
    Oracle("moore_half_emptying", "moore", _sub("moore"), STUDY["moore"], kind="reading", row="S1272"),
]
del _i, _k, _ml

assert len({o.name for o in ORACLES}) == len(ORACLES)
