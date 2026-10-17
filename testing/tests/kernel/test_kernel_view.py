"""The view kernel (NR_Kernel_View.lua, K.view; Plan 7 Task 3, rulings 2-5).

The kernel turns the client's stored mirror (a flat scalar table, NR_Kernel_Mirror.lua) into a row
model at one of three visibility levels, the six symptom classes the moodles show, and the tooltip
lines of one food's resolved vector. It is a kernel file, so the session host loads it through its
NR_Kernel* glob and the coverage gate (test_zz_coverage.py) holds every line of it to a test here.
Every label is a translation KEY and every text a KEY (isKey true) or a formatted string: the kernel
never calls getText. The option-file and server-reader tests at the end load NR_Server_Options.lua in
a fresh runtime of their own, so the session host's options table is never replaced.
"""
import json
import os

import pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
SANDBOX = os.path.join(REPO, "mod", "NutritionRevamp", "42.21", "media", "sandbox-options.txt")
EFFECTS_LUA = os.path.join(SHARED, "NR_Data_Effects.lua")
CLASSES = ["deficiency", "excess", "stimulant", "sleep"]
# Plan 15 Task 9: the nutrients whose grade drives an effect (the Deficiency moodle's set), pinned so a change to the
# effects table, the two grade aggregates or the drain onsets is reviewed here
EFFECT_NUTRIENTS = {"iron", "vitA", "vitC", "zinc", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12",
                    "copper"}
# the flag rows' sources that read no nutrient grade (a new aggregate over grades must join K.view.aggregateOf)
NON_GRADE_FLAGS = {"overfull", "refeedEvent", "coldCredit", "starve", "allReplete", "boutVig"}


def V(h):
    return h.K.view


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def rows_of(h, t):
    return [h.py(r) for r in lst(t)]


def arr(h, items):
    return h.rt.table(*items)


def effects(h):
    """NR.data.effects loaded into the host once (NR_Data_Effects.lua, the table the client hands deficiencyKeys)."""
    nr = h.G.NutritionRevamp
    if nr.data is None or nr.data.effects is None:
        with open(EFFECTS_LUA, encoding="utf-8") as fh:
            h.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@NR_Data_Effects.lua")()
    return h.G.NutritionRevamp.data.effects


def defset(h):
    return V(h).deficiencyKeys(effects(h))


# --- the level constants and the visibility level (ruling 3: max(option, trait), clamped 1..3) ---------

@pytest.mark.parametrize("opt,trait,want", [
    (1, False, 1), (2, False, 2), (3, False, 3),       # the option alone
    (1, True, 3), (2, True, 3),                        # either Nutritionist trait grants Numbers
    (None, False, 1), ("2", False, 1),                 # an unread or non-number option reads Symptoms
    (float("nan"), True, 3),                           # NaN reads Symptoms, the trait still grants 3
    (0, False, 1), (7, False, 3), (2.6, False, 2),     # clamped 1..3, a fraction floored
])
def test_level_is_the_max_of_option_and_trait(host, opt, trait, want):
    assert V(host).level(opt, trait) == want


@pytest.mark.parametrize("lv,want", [(None, 1), ("x", 1), (float("nan"), 1), (0, 1), (2, 2), (9, 3)])
def test_clamp_level(host, lv, want):
    assert V(host).clampLevel(lv) == want


# --- changed: the per-frame test ---------------------------------------------------------------------

def test_changed_only_when_the_counter_or_the_level_moved(host):
    assert V(host).changed(3, 3, 1, 1) is False
    assert V(host).changed(4, 3, 1, 1) is True
    assert V(host).changed(3, 3, 3, 1) is True


# --- fmt: %.<d>f on a number only (the Kahlua %d rule) ------------------------------------------------

@pytest.mark.parametrize("v,d,want", [
    (72.44, 1, "72.4"), (2.0, 0, "2"), (0.0125, 3, "0.013"), (5.0, None, "5"), (1.25, 9, "1.250"),
    (1.5, -2, "2"), ("12", 1, ""), (None, 1, ""), (float("nan"), 1, ""),
    (float("inf"), 1, ""), (float("-inf"), 0, ""),
])
def test_fmt(host, v, d, want):
    assert V(host).fmt(v, d) == want


@pytest.mark.parametrize("v,unit,want", [(156.0, "g", "156 g"), (25.13, "g", "25.1 g"), (4.4, "mg", "4.40 mg"),
                                         (-150.0, "kcal", "-150 kcal"), (0.5, None, "0.50")])
def test_amount_scales_its_digits(host, v, unit, want):
    assert V(host).amount(v, unit) == want


# --- rung: the count of ascending thresholds a value reaches ------------------------------------------

def test_rung(host):
    at = arr(host, [1, 2, 4, 6])
    assert [V(host).rung(v, at) for v in (0, 0.99, 1, 3.9, 4, 6, 50)] == [0, 0, 1, 2, 3, 4, 4]
    assert V(host).rung(None, at) == 0 and V(host).rung("5", at) == 0 and V(host).rung(float("nan"), at) == 0


# --- classes (ruling 5; Plan 15 Task 9): four classes, each 0-4 ----------------------------------------------

def test_classes_of_nil_and_an_empty_mirror_are_all_zero(host):
    assert host.py(V(host).classes(None)) == {c: 0 for c in CLASSES}
    assert host.py(V(host).classes(host.table({}))) == {c: 0 for c in CLASSES}


def test_class_names_in_order(host):
    assert lst(V(host).CLASSES) == CLASSES


@pytest.mark.parametrize("kg,want", [(-0.2, 0), (-0.0201, 0), (-0.02, 1), (0.0, 1), (0.02, 1), (0.0201, 2), (0.3, 2),
                                     (None, 1), (float("nan"), 1), ("x", 1)])
def test_the_trend_word(host, kg, want):
    # Plan 15 Task 9 fix 1 (review M2): the 7-day slope onto losing (0), steady (1) or gaining (2) by K.body.flags, the
    # flags vanilla's weight arrows read (ruling 17), strict at the threshold
    assert V(host).trendIndex(kg) == want


@pytest.mark.parametrize("pct,shown", [(0, None), (0.9, None), (1, None), (1.04, "1.0 %"), (2.26, "2.3 %"),
                                       (4, "4.0 %"), (12, "12.0 %"), (float("nan"), None), ("3", None)])
def test_the_dehydration_row_shows_above_one_per_cent(host, pct, shown):
    rows = rows_of(host, V(host).rows(host.table({"fluids_dehydPct": pct}), 2, None))
    row = next((r for r in rows if r["key"] == "fluids_dehydPct"), None)
    if shown is None:
        assert row is None
    else:
        assert row == {"key": "fluids_dehydPct", "label": "UI_NR_Row_fluids_dehydPct", "text": shown, "level": 2,
                       "isKey": False}


def test_the_deficiency_set_is_the_effects_tables_grade_readers(host):
    # Plan 15 Task 9 (item 8): the set is built from the tables (K.view.deficiencyKeys), and an independent read of the
    # data file's text finds the same grade rows; a new grade row, a new aggregate over grades or a new drain onset
    # moves the pinned set and fails here until it is reviewed
    import re
    text = open(EFFECTS_LUA, encoding="utf-8").read()
    gated_on = {g for g, v in re.findall(r"^\s*(\w+) = (true|false),", text, re.M) if v == "true"}
    rows = re.findall(r'\{ src = "(\w+)", on = "(\w+)"([^\n]*)', text)
    gates = {src + rest: re.search(r'gated = "(\w+)"', rest) for src, on, rest in rows}
    grade = {src for src, on, rest in rows if on == "grade"
             and (gates[src + rest] is None or gates[src + rest].group(1) in gated_on)}   # fix 1 (L2): a gate counts only when true
    flags = {src for src, on, _ in rows if on == "flag"}
    assert flags - {"bgroupMax", "anaemia"} <= NON_GRADE_FLAGS, flags
    want = grade | set(lst(host.K.effects.BGROUP)) | set(lst(host.K.nutrients.ANAEMIA)) | set(host.py(host.K.drain.NUTRIENT).values())
    got = {k for k, v in host.py(defset(host)).items() if v is True}
    assert got == want == EFFECT_NUTRIENTS
    assert "vitD" not in got and "biotin" not in got and "iodine" not in got   # gated off, or no effect row
    assert set(host.py(V(host).deficiencyKeys(None)).keys()) == {"vitC", "thiamine", "niacin"}   # the drain onsets alone


@pytest.mark.parametrize("caf,want", [(0, 0), (49, 0), (50, 1), (150, 2), (300, 3), (499, 3), (500, 4)])
def test_stimulant(host, caf, want):
    assert V(host).classes(host.table({"acute_caf": caf}))["stimulant"] == want


@pytest.mark.parametrize("debt,want", [(0, 0), (1.9, 0), (2, 1), (6, 2), (12, 3), (24, 4), (40, 4)])
def test_sleep(host, debt, want):
    assert V(host).classes(host.table({"acute_debtH": debt}))["sleep"] == want


def test_deficiency_is_the_worst_grade_less_one_and_excess_the_highest_rung(host):
    m = host.table({"nut_vitC_g": 1, "nut_iron_g": 3, "nut_zinc_g": 2, "nut_folate_g": 0, "nut_biotin_g": 4,
                    "nut_vitC_x": 0, "nut_iron_x": 2, "nut_zinc_x": 1, "nut_vitC_p": 0.2,
                    "nutrients_epoch": 9, "nut_bad_g": "x", "nut_bad_x": "x"})
    c = host.py(V(host).classes(m, defset(host)))
    assert c["deficiency"] == 2 and c["excess"] == 2         # biotin's clinical grade drives no effect: not counted
    assert host.py(V(host).classes(m))["deficiency"] == 0     # no set: no nutrient raises the class


def test_deficiency_and_excess_are_capped_at_three(host):
    c = host.py(V(host).classes(host.table({"nut_vitC_g": 9, "nut_iron_x": 7}), defset(host)))
    assert c["deficiency"] == 3 and c["excess"] == 3


def test_all_replete_is_deficiency_zero(host):
    # an UNGRADED kind keeps g = 1 (NR_Kernel_Nutrients), so it contributes 0
    c = host.py(V(host).classes(host.table({"nut_caffeine_g": 1, "nut_sodium_g": 1})))
    assert c["deficiency"] == 0 and c["excess"] == 0


# --- rows (ruling 2) ---------------------------------------------------------------------------------

MIRROR = {"body_band": "normal", "body_weight": 78.04, "body_trend": -0.06, "body_fm": 14.26,
          "body_lm": 63.79, "fluids_dehydPct": 2.5, "acute_caf": 160.0, "acute_bac": 0.0125, "acute_debtH": 6.5,
          "nut_vitC_g": 3, "nut_vitC_p": 0.3126, "nut_vitC_x": 0, "nut_iron_g": 1, "nut_iron_p": 1.0,
          "nut_iron_x": 2, "nut_zinc_g": 0, "nut_zinc_p": 0, "nut_zinc_x": 0}


def test_rows_at_symptoms_are_the_four_class_rows_only(host):
    rows = rows_of(host, V(host).rows(host.table(MIRROR), 1, arr(host, ["vitC", "iron"]), None, None, defset(host)))
    assert [r["cls"] for r in rows] == CLASSES
    assert rows[0] == {"key": "deficiency", "label": "UI_NR_Class_deficiency", "text": "UI_NR_Class_deficiency_2",
                       "level": 1, "cls": "deficiency", "n": 2, "isKey": True}
    assert rows[1]["text"] == "UI_NR_Class_excess_2"
    assert rows[2]["text"] == "UI_NR_Class_stimulant_2"
    assert rows[3]["text"] == "UI_NR_Class_sleep_2"


def test_rows_at_bands_add_the_body_fluids_and_grade_words(host):
    rows = rows_of(host, V(host).rows(host.table(MIRROR), 2, arr(host, ["vitC", "iron", "zinc"])))
    extra = rows[4:]
    assert [r["key"] for r in extra] == ["body_band", "body_weight", "body_trend", "body_fat", "body_level",
                                        "fluids_dehydPct", "nut_vitC_g", "nut_iron_g", "nut_iron_x"]   # zinc not yet graded: no row
    by = {r["key"]: r for r in extra}
    assert by["body_band"]["text"] == "UI_NR_Band_normal" and by["body_band"]["isKey"] is True
    assert by["body_weight"]["text"] == "78.0 kg" and by["body_weight"]["isKey"] is False
    assert by["body_fat"]["text"] == "UI_NR_FatBand_healthy" and by["body_fat"]["isKey"] is True   # 14.26 / 78.04 = 18.3 %, a man
    assert by["body_fat"]["label"] == "UI_NR_Row_body_fat" and by["body_fat"]["level"] == 2 and by["body_fat"]["fatBand"] == 2
    assert by["body_trend"]["text"] == "UI_NR_Trend_losing" and by["body_trend"]["isKey"] is True
    assert by["fluids_dehydPct"]["text"] == "2.5 %"
    assert by["nut_vitC_g"] == {"key": "nut_vitC_g", "label": "UI_NR_Row_vitC", "text": "UI_NR_Grade_3",
                                "level": 2, "isKey": True}
    # an excess rung above 0 is named at Bands by its class word (vitamin C's 0 is not)
    assert by["nut_iron_x"] == {"key": "nut_iron_x", "label": "UI_NR_Row_iron_x", "text": "UI_NR_Class_excess_2",
                                "level": 2, "isKey": True, "cls": "excess", "n": 2}
    assert all(r["level"] == 2 for r in extra)
    assert all(r["label"].startswith("UI_NR_") for r in rows)


def test_rows_at_numbers_add_the_figures(host):
    rows = rows_of(host, V(host).rows(host.table(MIRROR), 3, arr(host, ["vitC", "iron"])))
    keys = [r["key"] for r in rows[4:]]
    assert keys == ["body_band", "body_weight", "body_trend", "body_fat", "body_level", "body_fm", "body_lm", "body_trendKg", "fluids_dehydPct",
                    "nut_vitC_g", "nut_vitC_p", "nut_vitC_x", "nut_iron_g", "nut_iron_p", "nut_iron_x",
                    "acute_caf", "acute_bac", "acute_debtH"]
    by = {r["key"]: r for r in rows}
    assert by["body_fm"]["text"] == "14.3 kg" and by["body_lm"]["text"] == "63.8 kg"
    assert by["body_trendKg"]["text"] == "-0.06 kg/day" and by["body_trendKg"]["level"] == 3
    assert by["nut_vitC_p"]["text"] == "31.3 %" and by["nut_vitC_p"]["label"] == "UI_NR_Row_vitC_p"
    assert by["nut_iron_x"]["text"] == "2" and by["nut_iron_x"]["label"] == "UI_NR_Row_iron_x"
    assert by["acute_caf"]["text"] == "160 mg" and by["acute_bac"]["text"] == "0.013 %"
    assert by["acute_debtH"]["text"] == "6.5 h" and by["acute_debtH"]["label"] == "UI_NR_Row_acute_debtH"
    assert by["nut_vitC_p"]["level"] == 3 and by["nut_vitC_p"]["isKey"] is False


UNGRADED_MIRROR = {"nut_selenium_g": 1, "nut_selenium_x": 1, "nut_vitE_g": 1, "nut_vitE_x": 0, "nut_sodium_g": 1,
                   "nut_caffeine_x": 9, "nut_zinc_g": 0, "nut_zinc_x": 3}


def excess_rows(h, level, graded, ungraded):
    rows = rows_of(h, V(h).rows(h.table(UNGRADED_MIRROR), level, arr(h, graded), None, arr(h, ungraded)))
    return {r["key"]: r for r in rows if r["key"].endswith("_x")}


def test_an_ungraded_nutrients_excess_is_named_at_bands_and_numbers_when_above_zero(host):
    # selenium (excessOnly) and vitamin E (ledger) have no grade row, but their excess raises the Excess class: the
    # row that names it shows while the rung is above 0, as a class word at Bands and a figure at Numbers
    graded, ungraded = ["zinc"], ["vitE", "selenium", "sodium", "caffeine"]
    assert excess_rows(host, 1, graded, ungraded) == {}
    bands = excess_rows(host, 2, graded, ungraded)
    assert sorted(bands) == ["nut_caffeine_x", "nut_selenium_x", "nut_zinc_x"]   # vitE at 0 and sodium absent: none
    assert bands["nut_selenium_x"] == {"key": "nut_selenium_x", "label": "UI_NR_Row_selenium_x",
                                       "text": "UI_NR_Class_excess_1", "level": 2, "isKey": True, "cls": "excess", "n": 1}
    assert bands["nut_caffeine_x"]["text"] == "UI_NR_Class_excess_3"           # capped at the top rung
    assert bands["nut_zinc_x"]["text"] == "UI_NR_Class_excess_3"               # a graded key not yet graded still names it
    numbers = excess_rows(host, 3, graded, ungraded)
    assert sorted(numbers) == ["nut_caffeine_x", "nut_selenium_x", "nut_zinc_x"]
    assert numbers["nut_selenium_x"] == {"key": "nut_selenium_x", "label": "UI_NR_Row_selenium_x", "text": "1",
                                         "level": 3, "isKey": False}
    keys = [r["key"] for r in rows_of(host, V(host).rows(host.table(UNGRADED_MIRROR), 3, arr(host, graded), None,
                                                          arr(host, ungraded)))]
    assert keys.index("nut_selenium_x") < keys.index("nut_caffeine_x") < keys.index("acute_caf")   # in order, before the acute figures


@pytest.mark.parametrize("x", [float("nan"), "x", None, -1])
def test_an_excess_that_is_not_a_positive_number_names_no_ungraded_row(host, x):
    m = host.table({"nut_selenium_x": x})
    for level in (2, 3):
        rows = rows_of(host, V(host).rows(m, level, None, None, arr(host, ["selenium"])))
        assert "nut_selenium_x" not in [r["key"] for r in rows]


def test_rows_of_an_absent_body_read_the_band_none(host):
    rows = rows_of(host, V(host).rows(host.table({"body_band": ""}), 2, None))
    by = {r["key"]: r for r in rows}
    assert by["body_band"]["text"] == "UI_NR_Band_none"
    assert by["body_weight"]["text"] == ""                 # no number, no unit: fmt of nil is ""
    assert by["body_fat"]["text"] == "UI_NR_Band_none" and "fatBand" not in by["body_fat"]
    rows = rows_of(host, V(host).rows(None, 2, None))
    assert {r["key"]: r for r in rows}["body_band"]["text"] == "UI_NR_Band_none"


def test_rows_with_a_nil_level_read_symptoms(host):
    assert len(lst(V(host).rows(host.table(MIRROR), None, None))) == 4


# --- the graded order and the per-key requirements a client hands the kernel ---------------------------

RECORDS = {"ORDER": {1: "vitC", 2: "thiamine", 3: "caffeine", 4: "fibre", 5: "vitK", 6: "zinc"},
           "REC": {"vitC": {"kind": "pool", "unit": "mg", "R": {1: 90, 2: 75}},
                   "thiamine": {"kind": "pool", "unit": "mg", "scale": "perMJ", "R": {1: 0.1, 2: 0.1}},
                   "caffeine": {"kind": "acute", "unit": "mg"},
                   "fibre": {"kind": "counter", "unit": "g", "R": {1: 38, 2: 25}},
                   "vitK": {"kind": "pool", "unit": "mg", "R": {1: 120, 2: 90}},
                   "zinc": {"kind": "pool", "unit": "mg", "R": {1: "x"}}}}
UNITS = {"vitC": "mg", "thiamine": "mg", "caffeine": "mg", "fibre": "g", "vitK": "ug", "zinc": "mg",
         "calories": "kcal", "carbs": "g", "lipids": "g", "proteins": "g", "water": "g"}


# --- the Body fat row: cuts, sex, hold ---------------------------------------------------------------

def fat_row(h, fm, weight, female=False, last=None, level=2):
    m = h.table({"body_band": "normal", "body_weight": weight, "body_fm": fm})
    fat = h.table({"female": female, "last": last})
    return next(r for r in rows_of(h, V(h).rows(m, level, None, fat)) if r["key"] == "body_fat")


WORDS = ["veryLean", "lean", "healthy", "high", "veryHigh"]


@pytest.mark.parametrize("female,cuts", [(False, [6, 8, 20, 25]), (True, [13, 21, 33, 39])])
def test_each_fat_cut_is_a_band_edge_for_its_sex(host, female, cuts):
    for i, cut in enumerate(cuts):
        below = fat_row(host, cut - 0.1, 100, female)         # 0.1 % under the cut: the band below
        at = fat_row(host, cut, 100, female)                  # exactly on the cut: the band above
        assert below["text"] == "UI_NR_FatBand_" + WORDS[i] and below["fatBand"] == i, (female, cut)
        assert at["text"] == "UI_NR_FatBand_" + WORDS[i + 1] and at["fatBand"] == i + 1, (female, cut)
    assert fat_row(host, 60, 100, female)["text"] == "UI_NR_FatBand_veryHigh"


def test_the_same_fraction_reads_by_sex(host):
    assert fat_row(host, 22, 100, False)["text"] == "UI_NR_FatBand_high"        # a man at 22 %
    assert fat_row(host, 22, 100, True)["text"] == "UI_NR_FatBand_healthy"       # a woman at 22 %
    assert fat_row(host, 10, 100, False)["text"] == "UI_NR_FatBand_healthy"
    assert fat_row(host, 10, 100, True)["text"] == "UI_NR_FatBand_veryLean"
    assert fat_row(host, 22, 100, None)["text"] == "UI_NR_FatBand_high"           # no sex read: a man


def test_the_fat_word_holds_until_the_fraction_leaves_the_band_by_more_than_the_band(host):
    assert V(host).FAT_BAND == 0.005
    # a man held in healthy (8 to under 20 %): 20.4 % stays, 20.6 % leaves up; 7.6 % stays, 7.4 % leaves down
    assert fat_row(host, 20.4, 100, False, 2)["fatBand"] == 2
    assert fat_row(host, 20.6, 100, False, 2)["fatBand"] == 3
    assert fat_row(host, 7.6, 100, False, 2)["fatBand"] == 2
    assert fat_row(host, 7.4, 100, False, 2)["fatBand"] == 1
    # held in high: 19.6 % stays high (under the cut by less than the band), 19.4 % leaves; 25.4 % stays, 25.6 % leaves
    assert fat_row(host, 19.6, 100, False, 3)["fatBand"] == 3
    assert fat_row(host, 19.4, 100, False, 3)["fatBand"] == 2
    assert fat_row(host, 25.4, 100, False, 3)["fatBand"] == 3
    assert fat_row(host, 25.6, 100, False, 3)["fatBand"] == 4
    # the end bands hold on their one side only; a woman's cuts
    assert fat_row(host, 12.6, 100, True, 0)["fatBand"] == 0 and fat_row(host, 13.6, 100, True, 0)["fatBand"] == 1
    assert fat_row(host, 38.6, 100, True, 4)["fatBand"] == 4 and fat_row(host, 38.4, 100, True, 4)["fatBand"] == 3
    # no prior word, or a junk one: the plain band
    for junk in (None, -1, 5, 1.5, "2"):
        assert fat_row(host, 20.4, 100, False, junk)["fatBand"] == 3, junk


def test_the_fat_row_reads_no_data_without_a_body(host):
    for fm, w in ((5, 0), (5, -1), (None, 80), (5, None)):
        row = fat_row(host, fm, w, False, 2)
        assert row["text"] == "UI_NR_Band_none" and "fatBand" not in row, (fm, w)
    assert fat_row(host, 0, 80)["text"] == "UI_NR_FatBand_veryLean"            # a body with no fat is a body


def test_the_fat_row_sits_at_bands_and_numbers_and_not_at_symptoms(host):
    for lv, want in ((1, False), (2, True), (3, True)):
        keys = [r["key"] for r in rows_of(host, V(host).rows(host.table(MIRROR), lv, None))]
        assert ("body_fat" in keys) is want, lv
    keys = [r["key"] for r in rows_of(host, V(host).rows(host.table(MIRROR), 2, None))]
    assert keys.index("body_fat") == keys.index("body_trend") + 1 == keys.index("body_weight") + 2


def test_the_band_key_and_the_held_rung_helpers(host):
    assert V(host).bandKey("P_", "x") == "P_x" and V(host).bandKey("P_", "") == "P_none"
    assert V(host).bandKey("P_", None) == "P_none" and V(host).bandKey("P_", 3) == "P_none"
    at = host.table({1: 10, 2: 20})
    assert V(host).heldRung(15, at, 0, 1) == 1 and V(host).heldRung(10.5, at, 0, 1) == 0 and V(host).heldRung(None, at, 0, 1) == 0


def test_graded_order_drops_the_ungraded_kinds(host):
    assert lst(V(host).gradedOrder(host.table(RECORDS))) == ["vitC", "thiamine", "fibre", "vitK", "zinc"]
    assert lst(V(host).gradedOrder(None)) == []


def test_ungraded_order_keeps_only_the_ungraded_kinds(host):
    assert lst(V(host).ungradedOrder(host.table(RECORDS))) == ["caffeine"]
    assert lst(V(host).ungradedOrder(None)) == []


def test_the_two_orders_split_the_shipped_records_and_every_ungraded_excess_row_is_translated(host):
    data = load_data(host)
    graded = lst(V(host).gradedOrder(data.records))
    ungraded = lst(V(host).ungradedOrder(data.records))
    assert sorted(graded + ungraded) == sorted(lst(data.records.ORDER)) and not set(graded) & set(ungraded)
    assert {"selenium", "vitE"} <= set(ungraded)
    with open(os.path.join(LUA, "shared", "Translate", "EN", "UI.json"), encoding="utf-8") as fh:
        ui = json.load(fh)
    assert all("UI_NR_Row_%s_x" % k in ui for k in ungraded)
    assert all("UI_NR_Class_excess_%d" % n in ui for n in (1, 2, 3))


def test_requirements_keep_the_unscaled_records_in_the_vectors_unit(host):
    # thiamine is per MJ (scaled), vitK's record unit is not the vector's, zinc has no number for the sex
    r = host.py(V(host).requirements(host.table(RECORDS), 2, host.table(UNITS)))
    assert r == {"vitC": 75, "fibre": 25}
    assert host.py(V(host).requirements(host.table(RECORDS), 1, host.table(UNITS))) == {"vitC": 90, "fibre": 38}
    assert host.py(V(host).requirements(None, 1, host.table(UNITS))) == {}
    assert host.py(V(host).requirements(host.table(RECORDS), 1, None)) == {}


def test_requirements_over_the_shipped_records(host):
    # NR_Data_Records.lua and NR.data.UNITS loaded on top of the host: every key kept is a record key with a
    # numeric requirement in the vector's own unit
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua"):
        with open(os.path.join(SHARED, name), encoding="utf-8") as fh:
            host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@" + name)()
    data = host.G.NutritionRevamp.data
    r = host.py(V(host).requirements(data.records, 1, data.UNITS))
    assert r["vitC"] == 90
    assert all(isinstance(v, (int, float)) and v > 0 for v in r.values())
    assert set(r) <= set(host.py(data.UNITS))                       # keyed by the vector key, never a record key
    graded = lst(V(host).gradedOrder(data.records))
    assert "caffeine" not in graded and "sodium" not in graded and "vitC" in graded


def load_data(host):
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua"):
        with open(os.path.join(SHARED, name), encoding="utf-8") as fh:
            host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@" + name)()
    return host.G.NutritionRevamp.data


def test_the_five_keys_of_3240_are_rankable_over_the_shipped_records(host):
    # Plan 8 ruling 13 (#3240): vitamin A under its vector key retinol, and the scaled thiamine, niacin, B6 and K
    data = load_data(host)
    for sex in (1, 2):
        r = host.py(V(host).requirements(data.records, sex, data.UNITS))
        for key in ("retinol", "thiamine", "niacin", "vitB6", "vitK"):
            assert isinstance(r.get(key), (int, float)) and r[key] > 0, (sex, key)
        assert "vitA" not in r
    m = host.py(V(host).requirements(data.records, 1, data.UNITS))
    f = host.py(V(host).requirements(data.records, 2, data.UNITS))
    assert (m["retinol"], f["retinol"]) == (900, 700)               # R, the RDA ug RAE/d (S0133)
    assert (m["thiamine"], f["thiamine"]) == (1.2, 1.1)             # per MJ: Rmin, the RDA (S0235)
    assert (m["niacin"], f["niacin"]) == (16, 14)                   # per MJ: Rmin, the RDA (S0267)
    assert (m["vitB6"], f["vitB6"]) == (1.3, 1.3)                   # per protein, max: the R floor (S0291)
    assert (m["vitK"], f["vitK"]) == (70, 70)                       # per kg: R at the 70 kg reference


def test_the_record_key_aliases_are_the_records_own_key_fields(host):
    data = load_data(host)
    aliases = host.py(V(host).RECORD_KEY)
    assert aliases == {"retinol": "vitA"}
    rec = host.py(data.records.REC)
    mismatched = {r["key"]: name for name, r in rec.items() if "key" in r and r["key"] != name}
    assert mismatched == aliases


def test_a_rich_retinol_item_ranks_rich_in_the_band(host):
    data = load_data(host)
    R = V(host).requirements(data.records, 1, data.UNITS)
    vec = {"calories": 150.0, "retinol": 300.0, "thiamine": 0.5, "vitK": 0.0}
    lines = rows_of(host, V(host).tooltip(host.table(vec), "table", 2, arr(host, ["retinol", "thiamine", "vitK"]),
                                         host.table({"R": host.py(R), "UNITS": host.py(data.UNITS)})))
    rich = [l["key"] for l in lines if l["text"] == "UI_NR_Tip_Rich"]
    assert rich == ["thiamine", "retinol"]                          # 0.5/1.2 = 42 %, 300/900 = 33 %
    assert [l["key"] for l in lines if l["text"] == "UI_NR_Tip_Low"] == ["vitK"]


SCALED = {"ORDER": {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f"},
          "REC": {"a": {"unit": "mg", "scale": "perMJ", "R": {1: 0.1, 2: 0.1}, "Rmin": {1: 1.2, 2: 1.1}},
                  "b": {"unit": "mg", "scale": "perMJ", "R": {1: 0.1, 2: 0.1}, "Rmin": {1: 1.2}},
                  "c": {"unit": "ug", "scale": "perKg", "R": {1: 2, 2: 1}},
                  "d": {"unit": "mg", "scale": "perProteinGMax", "R": {1: 1.3, 2: 1.4}, "Rscale": 0.016},
                  "e": {"unit": "mg", "scale": "perProteinG", "R": {1: 0.02, 2: 0.02}},
                  "vitA": {"unit": "ug", "R": {1: 900, 2: 700}}}}
SCALED_UNITS = {"a": "mg", "b": "mg", "c": "ug", "d": "mg", "e": "mg", "f": "mg", "retinol": "ug", "calories": "kcal"}


def test_requirements_by_scale_and_alias(host):
    r1 = host.py(V(host).requirements(host.table(SCALED), 1, host.table(SCALED_UNITS)))
    assert r1 == {"a": 1.2, "b": 1.2, "c": 140, "d": 1.3, "retinol": 900}
    r2 = host.py(V(host).requirements(host.table(SCALED), 2, host.table(SCALED_UNITS)))
    assert r2 == {"a": 1.1, "c": 70, "d": 1.4, "retinol": 700}     # b has no female Rmin; e's scale is unknown
    assert V(host).REF_KG == 70


# --- tooltip lines (ruling 8) -------------------------------------------------------------------------

APPLE = {"calories": 95.0, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47, "fibre": 4.4, "vitC": 8.4,
         "water": 156.0, "vitK": 0.0, "zinc": 0.1}


def tip(h, vec, source, level, keys=None, R=None, units=UNITS):
    data = h.table({"R": R or {}, "UNITS": units}) if units is not None else None
    v = h.table(vec) if vec is not None else None
    k = arr(h, keys) if keys is not None else None
    return rows_of(h, V(h).tooltip(v, source, level, k, data))


def test_tooltip_at_symptoms_is_the_source_line(host):
    for src in ("declared", "table", "inferred", "missing"):
        lines = tip(host, APPLE, src, 1)
        assert lines == [{"key": "source", "label": "UI_NR_Tip_Source_" + src, "text": "", "level": 1,
                          "isKey": False}]
    assert tip(host, APPLE, None, 1)[0]["label"] == "UI_NR_Tip_Source_missing"


def test_tooltip_of_a_missing_vector_is_the_source_line_at_every_level(host):
    assert len(tip(host, None, "missing", 3)) == 1


def test_tooltip_at_bands_the_macros_then_rich_then_low(host):
    R = {"vitC": 75, "fibre": 25, "zinc": 8, "vitK": 90, "water": 2700}
    lines = tip(host, APPLE, "table", 2, ["vitC", "fibre", "zinc", "vitK", "water"], R)
    assert [l["key"] for l in lines[1:5]] == ["calories", "carbs", "lipids", "proteins"]
    assert lines[1]["text"] == "95.0 kcal" and lines[2]["text"] == "25.1 g" and lines[3]["text"] == "0.31 g"
    assert lines[1]["label"] == "UI_NR_Row_calories" and lines[1]["isKey"] is False
    rest = lines[5:]
    # fibre 4.4/25 = 17.6 % (not rich); vitC 8.4/75 = 11.2 %; water 5.8 %; zinc 1.25 %; vitK 0 %
    assert [(l["key"], l["text"]) for l in rest] == [("vitK", "UI_NR_Tip_Low"), ("zinc", "UI_NR_Tip_Low")]
    assert all(l["isKey"] is True and l["label"] == "UI_NR_Row_" + l["key"] for l in rest)


def test_tooltip_rich_is_ranked_and_capped_at_three(host):
    vec = {"calories": 100.0, "vitC": 60.0, "fibre": 10.0, "zinc": 4.0, "water": 2000.0, "vitK": 0.0}
    R = {"vitC": 75, "fibre": 25, "zinc": 8, "water": 2700, "vitK": 90}
    lines = tip(host, vec, "declared", 2, ["vitC", "fibre", "zinc", "water", "vitK"], R)
    rich = [l["key"] for l in lines if l["text"] == "UI_NR_Tip_Rich"]
    assert rich == ["vitC", "water", "zinc"]             # 80 %, 74 %, 50 % (fibre's 40 % is the fourth)
    assert [l["key"] for l in lines if l["text"] == "UI_NR_Tip_Low"] == ["vitK"]


def test_tooltip_low_is_capped_at_three(host):
    vec = {"calories": 10.0}
    R = {"vitC": 75, "fibre": 25, "zinc": 8, "water": 2700}
    lines = tip(host, vec, "inferred", 2, ["vitC", "fibre", "zinc", "water"], R)
    assert [l["key"] for l in lines if l["text"] == "UI_NR_Tip_Low"] == ["vitC", "fibre", "zinc"]


def test_tooltip_without_requirements_or_units_lists_the_macros_only(host):
    lines = tip(host, APPLE, "table", 2, ["vitC", "fibre"], None, None)
    assert [l["key"] for l in lines] == ["source", "calories", "carbs", "lipids", "proteins"]
    assert lines[1]["text"] == "95.0"


def test_tooltip_at_numbers_every_non_zero_key_with_its_unit(host):
    lines = tip(host, APPLE, "table", 3, ["vitC", "vitK", "fibre", "water", "iodine"])
    assert [(l["key"], l["text"]) for l in lines[1:]] == [("vitC", "8.40 mg"), ("fibre", "4.40 g"),
                                                         ("water", "156 g")]
    assert all(l["level"] == 3 and l["isKey"] is False for l in lines[1:])


def test_tooltip_keys_default_to_the_vector_keys(host):
    lines = tip(host, APPLE, "table", 3, None)
    assert [l["key"] for l in lines[1:]] == ["calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC",
                                            "zinc"]


# --- the option (ruling 3): the sandbox file, its translations, the server reader -------------------

def test_the_option_file_declares_visibility_mode():
    with open(SANDBOX, encoding="utf-8") as fh:
        src = fh.read()
    assert ("option NR.VisibilityMode\n{\n    type = enum, numValues = 3, default = 2,\n"
            "    page = NutritionRevamp, translation = NR_VisibilityMode, valueTranslation = NR_VisibilityModeValues,\n}"
            ) in src


def test_the_translations_carry_the_option_and_its_three_values():
    with open(os.path.join(SHARED, "Translate", "EN", "Sandbox.json"), encoding="utf-8") as fh:
        tr = json.load(fh)
    assert tr["Sandbox_NR_VisibilityMode"] and tr["Sandbox_NR_VisibilityMode_tooltip"]
    for i in (1, 2, 3):
        assert tr["Sandbox_NR_VisibilityModeValues_option%d" % i]


READ = r"""
function(nr)
    SandboxVars = { NR = nr }
    return NutritionRevamp.server.readOptions("test")
end
"""


def fresh_options_rt():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    kernel = sorted(os.path.join(SHARED, n) for n in os.listdir(SHARED) if n.startswith("NR_Kernel"))   # Options reads K.readLeaf and K.strength
    for path in [os.path.join(SHARED, "NR_Core.lua")] + kernel + [os.path.join(LUA, "server", "NR_Server_Options.lua")]:
        with open(path, encoding="utf-8") as fh:
            rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@x")()
    return rt


@pytest.fixture(scope="module")
def opt_rt():
    return fresh_options_rt()


def _table(rt, d):
    t = rt.table()
    for k, v in d.items():
        t[k] = v
    return t


@pytest.mark.parametrize("given,want", [(None, 2), (1, 1), (2, 2), (3, 3), (0, 2), (4, 2), ("3", 2)])
def test_the_server_reads_visibility_mode(opt_rt, given, want):
    nr = {} if given is None else {"VisibilityMode": given}
    O = opt_rt.eval(READ)(_table(opt_rt, nr))
    assert O.visibilityMode == want


def test_the_default_options_carry_visibility_mode():
    # before any read: the file-scope table already names the option at its default, Bands (ruling T13-1)
    assert fresh_options_rt().globals().NutritionRevamp.server.options.visibilityMode == 2


# --- the moodle value map (Plan 7 Task 8, ruling 10): a class level onto MoodleFramework's 0..1 value ---------

@pytest.mark.parametrize("cls", ["overfull", None, "stimulant", "sleep"])
@pytest.mark.parametrize("lv,want", [(0, 0.5), (1, 0.375), (2, 0.25), (3, 0.125), (4, 0.0)])
def test_moodle_value_four_level_classes(host, cls, lv, want):
    assert V(host).moodleValue(lv, cls) == pytest.approx(want)


@pytest.mark.parametrize("cls", ["deficiency", "excess"])
@pytest.mark.parametrize("lv,want", [(0, 0.5), (1, 0.33333), (2, 0.16667), (3, 0.0), (4, 0.0)])
def test_moodle_value_three_rung_classes_reach_the_top_at_three(host, cls, lv, want):
    assert V(host).moodleValue(lv, cls) == pytest.approx(want, abs=1e-4)


@pytest.mark.parametrize("lv,want", [(None, 0.5), ("2", 0.5), (float("nan"), 0.5), (-3, 0.5), (9, 0.0), (2.7, 0.25)])
def test_moodle_value_reads_junk_as_neutral_and_clamps(host, lv, want):
    assert V(host).moodleValue(lv, "sleep") == pytest.approx(want)


def test_moodle_value_with_no_class_uses_the_four_level_map(host):
    assert V(host).moodleValue(2, None) == pytest.approx(0.25)


@pytest.mark.parametrize("cls,top", [("overfull", 4), ("sleep", 4), ("deficiency", 3), ("excess", 3)])
def test_moodle_top(host, cls, top):
    assert V(host).moodleTop(cls) == top


@pytest.mark.parametrize("cls,want", [
    ("stimulant", [0.4375, 0.3125, 0.1875, 0.0625]),
    ("deficiency", [0.41667, 0.25, 0.08333, None]),
])
def test_moodle_thresholds_are_the_bad_side_table(host, cls, want):
    got = [V(host).moodleThreshold(k, cls) for k in range(1, 5)]
    for g, w in zip(got, want):
        if w is None:
            assert g is None
        else:
            assert g == pytest.approx(w, abs=1e-5)


@pytest.mark.parametrize("cls", ["overfull", None, "deficiency", "excess", "stimulant", "sleep"])
def test_moodle_thresholds_sit_between_the_values(host, cls):
    v = V(host)
    top = v.moodleTop(cls)
    for k in range(1, 5):
        t = v.moodleThreshold(k, cls)
        if k > top:
            assert t is None
            continue
        # the bad side: strictly below the value of level k - 1 and above the value of level k
        assert v.moodleValue(k - 1, cls) > t > v.moodleValue(k, cls)


def test_the_push_signature_moves_with_any_live_class(host):
    s0 = host.call("view.pushSignature", 0.5, 0.0, 0.0, 0.0)
    assert host.call("view.pushSignature", 0.5, 0.0, 0.0, 0.0) == s0
    for args in ((1.0, 0.0, 0.0, 0.0), (0.5, 50.0, 0.0, 0.0), (0.5, 0.0, 2.0, 0.0), (0.5, 0.0, 0.0, 731.0)):
        assert host.call("view.pushSignature", *args) != s0, args
    assert host.call("view.pushSignature", 0.9, 49.0, 1.9, 730.0) == s0     # inside every step: no push


def test_the_push_signature_moves_across_each_overfull_band_edge(host):
    for lo, hi in ((730, 731), (853, 854), (976, 977), (1099, 1100)):
        assert host.call("view.pushSignature", 1.0, 0.0, 0.0, lo) != host.call("view.pushSignature", 1.0, 0.0, 0.0, hi), (lo, hi)


def test_the_push_signature_is_equal_within_an_overfull_band(host):
    assert host.call("view.pushSignature", 1.0, 0.0, 0.0, 731) == host.call("view.pushSignature", 1.0, 0.0, 0.0, 850)


def test_a_nil_mask_and_trend_read_none_and_steady(host):
    old = host.call("view.pushSignature", 1.6, 5.0, 400.0, 30.0)
    assert host.call("view.pushSignature", 1.6, 5.0, 400.0, 30.0, None, None) == old
    assert host.call("view.pushSignature", 1.6, 5.0, 400.0, 30.0, 0, 1) == old
    assert host.call("view.pushSignature", 1.6, 5.0, 400.0, 30.0, False, float("nan")) != old   # a NaN trend reads 0


def test_the_push_signature_reads_nil_as_zero(host):
    assert host.call("view.pushSignature", None, None, None, None) == host.call("view.pushSignature", 0, 0, 0, 0)


def test_the_push_offset_is_inside_the_gap_and_differs_by_name(host):
    a = host.call("view.pushOffset", "admin", 60000)
    b = host.call("view.pushOffset", "bob", 60000)
    assert 0 <= a < 60000 and 0 <= b < 60000 and a != b
    assert host.call("view.pushOffset", "admin", 60000) == a
    assert host.call("view.pushOffset", "", 60000) == 0


# --- the panel's signal lines, the hide option and the fill line (Plan 15 Task 9; spec section 4) ----------------------

def test_drain_rows_list_each_active_state_in_code_order(host):
    names = [host.K.drain.states[i].name for i in range(1, len(host.K.drain.states) + 1)]
    for lv in (1, 2, 3):
        rows = rows_of(host, V(host).rows(host.table({"drain_mask": 2 ** 0 + 2 ** 2 + 2 ** 6}), lv, None))
        drains = [r for r in rows if r["key"].startswith("drain_")]
        assert [r["key"] for r in drains] == ["drain_" + names[0], "drain_" + names[2], "drain_" + names[6]]
        assert drains[0] == {"key": "drain_starvation", "label": "UI_NR_Row_drain", "text": "UI_NR_Drain_starvation",
                             "level": 1, "isKey": True, "cls": "drain", "n": 1}
        assert [r["key"] for r in rows[:4]] == CLASSES and rows[4]["key"] == "drain_starvation"
    for junk in (0, None, float("nan"), "3", -1):
        rows = rows_of(host, V(host).rows(host.table({"drain_mask": junk}), 1, None))
        assert [r["key"] for r in rows] == CLASSES, junk


def test_the_trend_word_agrees_with_vanillas_weight_arrows(host):
    # one threshold: the word is gaining exactly when K.body.flags raises increasing, losing exactly when decreasing
    for kg in (-0.5, -0.03, -0.02, -0.019, 0.0, 0.019, 0.02, 0.021, 0.11, 0.5):
        inc, _, dec = host.K.body.flags(kg)
        assert V(host).trendIndex(kg) == (2 if inc else 0 if dec else 1), kg
    assert V(host).TREND_KG_DAY is None
    rows = rows_of(host, V(host).rows(host.table({"body_weight": 70.0, "body_trend": 0.07}), 2, None))
    assert {r["key"]: r for r in rows}["body_trend"]["text"] == "UI_NR_Trend_gaining"
    for m in ({"body_trend": 0.07}, {"body_weight": 70.0}, {"body_weight": 0, "body_trend": 0.07}):
        rows = rows_of(host, V(host).rows(host.table(m), 2, None))
        assert {r["key"]: r for r in rows}["body_trend"]["text"] == "UI_NR_Band_none", m


def test_the_hide_option_hides_level_one_of_three_moodles(host):
    v = V(host)
    for cls in ("stimulant", "sleep", "excess"):
        assert v.shownLevel(cls, 1, True) == 0 and v.shownLevel(cls, 2, True) == 2 and v.shownLevel(cls, 1, False) == 1
    for cls in ("deficiency", "overfull"):
        assert v.shownLevel(cls, 1, True) == 1
    assert v.shownLevel("sleep", 0, True) == 0 and v.shownLevel("sleep", 1, None) == 1


@pytest.mark.parametrize("hours,kcal,label,text,sep", [
    (0.03, 16.7, "UI_NR_Tip_FillsUnder", "17 kcal", ", "),
    (0.49, 100.0, "UI_NR_Tip_FillsUnder", "100 kcal", ", "),
    (0.5, 100.0, "UI_NR_Tip_Fills", "0.5 h, 100 kcal", " "),
    (1.23, 94.59, "UI_NR_Tip_Fills", "1 h, 95 kcal", " "),
    (3.65, 540.0, "UI_NR_Tip_Fills", "3.5 h, 540 kcal", " "),
    (3.76, 540.0, "UI_NR_Tip_Fills", "4 h, 540 kcal", " "),
    (24.0, 3000.0, "UI_NR_Tip_FillsOver", "24 h, 3000 kcal", " "),
])
def test_the_fill_row_rounds_to_the_half_hour_and_names_the_kcal(host, hours, kcal, label, text, sep):
    out = host.rt.table()
    V(host).fillRow(out, hours, kcal)
    assert rows_of(host, out) == [{"key": "fill", "label": label, "text": text, "level": 1, "isKey": False, "sep": sep}]


def test_the_tooltip_puts_the_fill_line_first_at_every_level(host):
    vec = host.table({"calories": 540.0, "carbs": 60.0, "lipids": 20.0, "proteins": 30.0})
    for lv in (1, 2, 3):
        rows = rows_of(host, V(host).tooltip(vec, "table", lv, arr(host, []), host.table({"fillH": 3.65})))
        assert rows[0]["key"] == "fill" and rows[0]["text"] == "3.5 h, 540 kcal" and rows[1]["key"] == "source"
    for data in (None, {}, {"fillH": float("nan")}):
        rows = rows_of(host, V(host).tooltip(vec, "table", 1, None, None if data is None else host.table(data)))
        assert [r["key"] for r in rows] == ["source"], data
    rows = rows_of(host, V(host).tooltip(None, "missing", 2, None, host.table({"fillH": 3.0})))
    assert [r["key"] for r in rows] == ["source"]


def test_the_push_signature_moves_with_the_drain_set_the_trend_and_the_dehydration_digit(host):
    sig = lambda *a: host.call("view.pushSignature", *a)
    s0 = sig(0.0, 0.0, 0.0, 0, 0, 1)
    assert sig(0.0, 0.0, 0.0, 0, 1, 1) != s0 and sig(0.0, 0.0, 0.0, 0, 32, 1) != sig(0.0, 0.0, 0.0, 0, 1, 1)
    assert sig(0.0, 0.0, 0.0, 0, 0, 0) != s0 and sig(0.0, 0.0, 0.0, 0, 0, 2) != s0
    assert sig(1.0, 0.0, 0.0, 0, 0, 1) != s0 and sig(1.9, 0.0, 0.0, 0, 0, 1) == sig(1.0, 0.0, 0.0, 0, 0, 1)
    assert sig(9.0, 0.0, 0.0, 0, 0, 1) == sig(15.0, 0.0, 0.0, 0, 0, 1)           # the digit stops at 9
    assert sig(0.0, 500.0, 24.0, 1100, 127, 2) == 127 * 100000 + 2 * 10000 + 0 * 1000 + 4 * 100 + 4 * 10 + 4
    assert sig(0.0, 0.0, 0.0, 0, 200, 7) == sig(0.0, 0.0, 0.0, 0, 127, 2)          # each digit clamped


# --- the Strength row (Plan 13 Task 18, ruling 13-19) ----------------------------------------------------------

def level_row(h, level, lv=2, **extra):
    m = {"body_band": "normal", "body_weight": 78.0, "body_fm": 14.0}
    if level is not None:
        m["body_level"] = level
    m.update(extra)
    rows = rows_of(h, V(h).rows(h.table(m), lv, None))
    return rows, next((r for r in rows if r["key"] == "body_level"), None)


@pytest.mark.parametrize("level,text", [(12.34, "12.3"), (9.96, "9.9"), (9.99999, "9.9"), (12.0, "12.0"),
                                        (0.0, "0.0"), (0.04, "0.0"), (5.0, "5.0"), (30.0, "30.0"), (-0.04, "0.0"), (-3.25, "0.0"),
                                        (6.999999999999997, "7.0"), (0.9999999999999999, "1.0")])
def test_the_strength_row_truncates_and_never_rounds_up(host, level, text):
    _, row = level_row(host, level)
    assert row == {"key": "body_level", "label": "UI_NR_Row_body_level", "text": text, "level": 2, "isKey": False}


def test_the_strength_row_sits_after_the_fat_row_at_bands_and_numbers_only(host):
    for lv, want in ((1, False), (2, True), (3, True)):
        rows, row = level_row(host, 12.34, lv)
        assert (row is not None) is want, lv
    rows, _ = level_row(host, 12.34, 2)
    keys = [r["key"] for r in rows]
    assert keys.index("body_level") == keys.index("body_fat") + 1


def test_a_body_less_mirror_shows_no_data_for_strength(host):
    _, row = level_row(host, None)
    assert row["text"] == "UI_NR_Band_none" and row["isKey"] is True
    _, row = level_row(host, float("nan"))
    assert row["text"] == "UI_NR_Band_none"
    for bad in (float("inf"), float("-inf")):
        _, row = level_row(host, bad)
        assert row["text"] == "UI_NR_Band_none"
    rows = rows_of(host, V(host).rows(None, 2, None))
    assert {r["key"]: r for r in rows}["body_level"]["text"] == "UI_NR_Band_none"


def test_a_level_built_on_a_trait_start_level_reads_it_whole(host):
    D = host.K.strength.DEFAULTS
    for key in ("STRONG", "STOUT", "none", "FEEBLE", "WEAK"):
        F = host.K.strength.fOfLevel(D.startLevel[key], D.N0[key], 1, D)
        _, row = level_row(host, host.K.strength.level(F, D.N0[key], 1, D))
        assert row["text"] == "%d.0" % D.startLevel[key], key
