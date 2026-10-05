"""The 27 declarative nutrient records (NR_Data_Records.lua, NR.data.records; Plan 4 Task 7).

The engine (NR_Kernel_Nutrients.lua) is one generic loop over { ORDER, REC }; the tier of each record
lives in its `kind`, and the engine routes an unknown kind string to ctx.two and grades it, so these
tests pin every kind exactly. The file is data, not a kernel: it loads before the kernels in the game
(NR_Data_ sorts before NR_Kernel_), so every derived rate is a literal computed in Python doubles with
its expression in the trailing comment, and the table below recomputes each through the kernel's own
function to 1e-9. NR_Data_Records.lua is loaded on top of the session host the way test_data_units.py
loads NR_Data_Nutrients.lua (which provides NR.data.UNITS).
"""
import csv
import math
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DATA = os.path.join(SHARED, "NR_Data_Records.lua")
NUTRIENTS = os.path.join(SHARED, "NR_Data_Nutrients.lua")
REGISTER = os.path.join(REPO, "docs", "reference", "science.tsv")


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def rh(host):
    _load(host, NUTRIENTS)
    _load(host, DATA)
    return host


def _records(h):
    return h.G.NutritionRevamp.data.records


def _rec(h, key):
    return h.py(_records(h).REC[key])


def _order(h):
    order = _records(h).ORDER
    return [order[i] for i in range(1, len(order) + 1)]


# The plan's record order (Task 7's table, row order) and the kind of each (ruling 3).
ORDER = ["vitC", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "vitA", "vitD",
         "vitE", "vitK", "pantothenate", "biotin", "iron", "zinc", "copper", "magnesium", "calcium", "iodine",
         "selenium", "fibre", "efa", "sodium", "potassium", "caffeine", "ethanol"]
KIND = {"vitC": "pool", "thiamine": "pool", "riboflavin": "pool", "niacin": "pool", "vitB6": "pool",
        "folate": "pool", "vitB12": "pool2", "choline": "pool", "vitA": "pool2", "vitD": "pool",
        "vitE": "ledger", "vitK": "pool", "pantothenate": "ledger", "biotin": "counter", "iron": "pool2",
        "zinc": "pool", "copper": "derived", "magnesium": "pool", "calcium": "counter", "iodine": "pool",
        "selenium": "excessOnly", "fibre": "counter", "efa": "pool", "sodium": "fast", "potassium": "fast",
        "caffeine": "acute", "ethanol": "acute"}
ENGINE_KINDS = {"pool", "pool2", "counter", "derived", "excessOnly", "ledger", "fast", "acute"}

# The requirement per record, {male, female}, as transcribed from the rows (scale noted where scaled).
R = {"vitC": (90, 75), "thiamine": (0.1, 0.1), "riboflavin": (1.3, 1.1), "niacin": (1.6, 1.6),
     "vitB6": (1.3, 1.3), "folate": (400, 400), "vitB12": (2.4, 2.4), "choline": (550, 425),
     "vitA": (900, 700), "vitD": (15, 15), "vitE": (15, 15), "vitK": (1, 1), "pantothenate": (5, 5),
     "biotin": (30, 30), "iron": (8, 18), "zinc": (11, 8), "copper": (900, 900), "magnesium": (400, 310),
     "calcium": (1000, 1000), "iodine": (150, 150), "selenium": (55, 55), "fibre": (38, 25),
     "efa": (18.6, 13.1), "sodium": (1500, 1500), "potassium": (3400, 2600)}
SCALE = {"thiamine": "perMJ", "niacin": "perMJ", "vitB6": "perProteinGMax", "vitK": "perKg"}

# The records with no vector key: copper is derived, pantothenate and biotin have no key in NR.data.UNITS.
NO_KEY = {"copper", "pantothenate", "biotin"}


def test_order_is_the_plans_and_matches_rec(rh):
    order = _order(rh)
    assert order == ORDER
    assert len(order) == 27
    rec_keys = set(rh.py(_records(rh).REC).keys())
    assert rec_keys == set(ORDER)


def test_every_kind_is_the_plans_and_in_the_engines_set(rh):
    for key in ORDER:
        kind = _rec(rh, key)["kind"]
        assert kind in ENGINE_KINDS, (key, kind)
        assert kind == KIND[key], key


def test_every_requirement_is_two_positive_numbers(rh):
    for key in ORDER:
        rec = _rec(rh, key)
        if rec["kind"] == "acute":
            assert "R" not in rec, key                       # caffeine and ethanol carry no requirement
            continue
        r = rec["R"]
        assert sorted(r.keys()) == [1, 2], key
        assert all(isinstance(v, (int, float)) and v > 0 for v in r.values()), key
        assert (r[1], r[2]) == pytest.approx(R[key]), key
        assert rec.get("scale") == SCALE.get(key), key
    assert _rec(rh, "vitB6")["Rscale"] == 0.016
    assert _rec(rh, "thiamine")["Rmin"] == {1: 1.2, 2: 1.1}
    assert _rec(rh, "niacin")["Rmin"] == {1: 16, 2: 14}


def test_every_unit_matches_the_units_contract(rh):
    units = dict(rh.G.NutritionRevamp.data.UNITS.items())
    for key in ORDER:
        rec = _rec(rh, key)
        assert isinstance(rec.get("unit"), str), key
        if key in NO_KEY:
            assert rec.get("key") is None, key
            continue
        assert rec["key"] in units, key
        assert rec["unit"] == units[rec["key"]], key
        if rec.get("key2") is not None:
            assert rec["unit"] == units[rec["key2"]], key
    assert _rec(rh, "vitA")["key"] == "retinol"
    assert _rec(rh, "vitA")["key2"] == "carotene"
    assert _rec(rh, "copper")["unit"] == "ug"


def test_every_pool_has_a_rate_and_a_descending_ladder(rh):
    for key in ORDER:
        rec = _rec(rh, key)
        if rec["kind"] not in ("pool", "pool2"):
            continue
        if key == "iron":
            assert "k" not in rec                              # iron is zero-order: L, not k
            assert rec["L"] == {1: 1.0, 2: 1.5}
        else:
            assert isinstance(rec["k"], float) and rec["k"] > 0, key
        lad = rec.get("ladder")
        if lad is None:
            continue                                           # the engine's generic ladder applies
        assert sorted(lad.keys()) == [1, 2, 3], key
        assert 1 > lad[1] > lad[2] > lad[3] > 0, key


def test_the_ladders_are_the_rows(rh):
    recs = _records(rh).REC
    lad = lambda k: tuple(rh.K.nutrients.ladderOf(recs[k])[i] for i in (1, 2, 3))   # nil -> the generic ladder
    assert lad("vitC") == (0.70, 0.45, 0.15)
    assert lad("thiamine") == pytest.approx((0.70, 0.45, 0.5 / 1.2), abs=1e-12)
    assert lad("vitB6") == (0.70, 0.45, 0.25)
    assert lad("folate") == pytest.approx((0.70, 0.10, math.exp(-math.log(10) / 90 * 120)), abs=1e-12)
    assert lad("vitB12") == (0.70, 0.45, 0.10)
    assert lad("choline") == (0.70, 0.45, 0.30)
    assert lad("vitA") == pytest.approx((0.25, 0.175, 0.175 * 0.35), abs=1e-12)
    assert lad("vitD") == (0.67, 0.40, 0.17)
    assert lad("iron") == (0.50, 0.15, 0.01)
    assert lad("fibre") == (0.5, 0.25, 0.0)
    for key in ("riboflavin", "niacin", "vitK", "zinc", "copper", "magnesium", "iodine", "efa"):
        assert lad(key) == (0.70, 0.45, 0.25), key


# (record, kernel function, its arguments): every derived rate recomputed through the kernel to 1e-9.
DERIVED = [
    ("vitC", "calib", (0.15, 40)),
    ("thiamine", "kFromHalfLife", (13.5,)),
    ("riboflavin", "kFromHalfLife", (13.5,)),
    ("niacin", "calib", (0.25, 55)),
    ("vitB6", "kFromHalfLife", (29,)),
    ("folate", "calib", (0.10, 90)),
    ("choline", "calib", (0.30, 21)),
    ("vitA", "calib", (0.35, 120)),
    ("vitD", "kFromHalfLife", (60,)),
    ("vitK", "calibAt", (0.155, 13, 10 / 120)),
    ("zinc", "calibAt", (0.5, 49, 4 / 11)),
    ("efa", "calib", (0.25, 28)),
]


@pytest.mark.parametrize("key,fn,args", DERIVED)
def test_each_derived_rate_is_the_kernels_function(rh, key, fn, args):
    expect = rh.K.nutrients[fn](*args)
    assert abs(_rec(rh, key)["k"] - expect) < 1e-9, (key, expect)


def test_the_hand_rates(rh):
    k = lambda key: _rec(rh, key)["k"]
    assert k("vitC") == pytest.approx(0.0474280, abs=1e-7)
    assert k("thiamine") == pytest.approx(0.0513442356, abs=1e-10)
    assert k("riboflavin") == k("thiamine")                     # game choice: thiamine's (open S1067)
    assert k("niacin") == pytest.approx(0.0252054, abs=1e-7)
    assert k("folate") == pytest.approx(0.0255843, abs=1e-7)
    assert k("choline") == pytest.approx(0.0573320, abs=1e-7)
    assert k("efa") == pytest.approx(0.0495105, abs=1e-7)
    assert k("vitA") == pytest.approx(0.0087485, abs=1e-7)
    assert k("vitB6") == pytest.approx(0.0239016, abs=1e-7)
    assert k("vitD") == pytest.approx(0.0115525, abs=1e-7)
    # the exact calibAt at 4/11 and 10/120 (J's 0.0310169 and 0.1960223 used 0.36 and 0.0833)
    assert k("zinc") == pytest.approx(0.0314377, abs=1e-7)
    assert k("vitK") == pytest.approx(0.1960552, abs=1e-7)
    assert k("vitB12") == 0.001
    assert k("iodine") == 0.01
    assert k("magnesium") == 0.013
    assert abs(_rec(rh, "fibre")["counter"]["kEma"] - rh.K.nutrients.kFromHalfLife(3.5)) < 1e-9
    assert abs(_rec(rh, "thiamine")["ladder"][3] - rh.K.nutrients.fFromThreshold(0.5, 1.2)) < 1e-9


def test_the_store_derived_rates_close(rh):
    # magnesium k = R_abs / soft-tissue store = 400 x 0.325 / 10 000; iodine k = 150 / 15 000; B12 2.5 / 2500
    mg = _rec(rh, "magnesium")
    assert abs(mg["k"] - mg["R"][1] * mg["absorb"] / mg["store"]) < 1e-12
    io = _rec(rh, "iodine")
    assert abs(io["k"] - io["R"][1] / io["store"]) < 1e-12
    assert _rec(rh, "vitB12")["store"] == 2500


# Ruling 5: the records whose replete-to-clinical time at zero intake exceeds 90 days take the dial.
DIALLED = {"folate", "vitB12", "vitA", "vitD", "magnesium", "iodine"}


def test_the_dial_exponents_are_ruling_5s(rh):
    recs = _records(rh).REC
    for key in ORDER:
        kind = _rec(rh, key)["kind"]
        if kind not in ("pool", "pool2"):
            continue
        assert rh.K.nutrients.dialExp(recs[key]) == (1 if key in DIALLED else 0), key


def test_the_two_compartment_fields(rh):
    iron = _rec(rh, "iron")
    assert iron["clinicalOnP2"] is True and iron["p2Clinical"] == 0.88
    assert iron["two"]["totalPerKg"] == {1: 50, 2: 40}
    assert iron["two"]["storeShare"] == 0.25
    assert abs(iron["two"]["hbShare"] - 2 / 3) < 1e-12
    assert (iron["two"]["xMax"], iron["two"]["etaK"], iron["two"]["anaemiaP2"]) == (30, 0.5, 0.88)
    assert iron["absorb"] == 0.18
    assert "pCap" not in iron                                  # eta(p) is iron's repletion limit
    assert iron["ul"] == 45 and iron["acute"]["perKg"] == {1: 20, 2: 60}
    vita = _rec(rh, "vitA")
    assert vita["clinicalOnP2"] is True and vita["p2Clinical"] == 0.35
    assert vita["two"] == {"plasmaKnee": 0.175, "caroteneOff": 1.0}
    assert "pCap" not in vita                                  # hoardable to toxicity
    assert vita["ul"] == 3000 and vita["chronic"] == {"perDay": 7500, "store": 7.2}
    assert vita["acute"]["abs"] == 90000
    b12 = _rec(rh, "vitB12")
    assert b12["clinicalOnP2"] is True and b12["p2Clinical"] == 1.0
    assert b12["two"] == {"fThreshold": 0.10}
    clin = {key for key in ORDER if _rec(rh, key).get("clinicalOnP2")}
    assert clin == {"iron", "vitA", "vitB12"}


def test_the_counter_derived_and_excess_fields(rh):
    cu = _rec(rh, "copper")
    assert cu["derived"] == {"from": "zinc", "kcu": 0.02, "ulZn": 40}
    assert cu["ul"] == 10000
    ca = _rec(rh, "calcium")
    assert ca["counter"]["absorb"] == 0.25 and ca["counter"]["lossPerDay"] == 200
    assert ca["counter"]["skeleton"] == {1: 1400, 2: 1200}       # S0411: 1400 g men, 1200 g women
    assert ca["ul"] == 2500
    assert _rec(rh, "biotin")["counter"] == {"cosmeticDays": 90}
    fib = _rec(rh, "fibre")["counter"]
    assert (fib["marginal"], fib["depleted"]) == (0.5, 0.25)
    se = _rec(rh, "selenium")
    assert se["ul"] == 400 and se["chronic"] == {"perDay": 5000}
    vd = _rec(rh, "vitD")
    assert vd["sun"]["kSun"] == 0.0 and vd["pCap"] == 3.3
    assert vd["ul"] == 100 and vd["chronic"] == {"perDay": 250, "store": 5}
    assert _rec(rh, "vitC")["ul"] == 2000 and _rec(rh, "vitC")["pCap"] == 1.0
    assert _rec(rh, "vitE")["ul"] == 300
    assert _rec(rh, "choline")["kFemale"] == 0.57
    for key in ("thiamine", "riboflavin", "vitB12", "vitK", "pantothenate", "biotin", "efa"):
        assert "ul" not in _rec(rh, key), key


# --- the labelling rule as a tool check for this file -------------------------------------------------

NUM = re.compile(r"(?<![A-Za-z_0-9.])\d")
SID = re.compile(r"\bS\d{4}\b")
LABEL = re.compile(r"\bS\d{4}\b|design-phase-v1|game choice")


def _code_and_comment(line):
    code = re.sub(r'"[^"]*"', '""', line)
    i = code.find("--")
    if i < 0:
        return code, ""
    return code[:i], line[line.find("--"):]


def _register():
    with open(REGISTER, encoding="utf-8") as fh:
        return {r["id"]: r for r in csv.DictReader(fh, delimiter="\t")}


def test_every_number_line_carries_a_label():
    with open(DATA, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    bad = []
    for n, line in enumerate(lines, 1):
        code, comment = _code_and_comment(line)
        if NUM.search(code) and not LABEL.search(comment):
            bad.append((n, line))
    assert bad == []


def test_every_number_sits_on_its_own_line():
    with open(DATA, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for n, line in enumerate(lines, 1):
        code, _ = _code_and_comment(line)
        assert len(re.findall(r"(?<![A-Za-z_0-9.])\d[\d.]*", code)) <= 1, (n, line)


def test_every_cited_row_exists_and_an_open_one_is_labelled_open():
    reg = _register()
    with open(DATA, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for n, line in enumerate(lines, 1):
        for sid in SID.findall(line):
            assert sid in reg, (n, sid)
            st = reg[sid]["status"]
            assert st != "superseded", (n, sid)
            if st == "open":
                assert re.search(r"\bopen\b|design-phase-v1|game choice", line), (n, sid, line)


def test_science_check_scan_is_clean():
    out = subprocess.run([sys.executable, os.path.join(REPO, "tools", "science_check.py"), "--scan", DATA],
                         cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_the_banner_says_not_a_kernel_file():
    with open(DATA, encoding="utf-8") as fh:
        first = fh.readline()
    assert first.startswith("-- NR_Data_Records.lua -- not a kernel file")


# --- the records through the engine ---------------------------------------------------------------------

SIM = r"""
function(records, days, dial)
    local K = NutritionRevamp.kernel
    local state = K.nutrients.newState(records)
    local two = function(key, s, rec, aAbs, ctx, dtD, dtH)
        if key == "vitB12" then
            local R = K.nutrients.requirement(rec, ctx)
            K.nutrients.stepPool(s, rec, aAbs, R, K.nutrients.kEff(rec, rec.k, ctx.dial or 1), dtD)
            s.p2 = math.min(1, s.p / rec.two.fThreshold)
        end
    end
    local ctx = { sex = 1, w = 80, eeMJ = 10, pDay = 80, dial = dial, two = two }
    local empty = {}
    local first = {}
    for step = 1, days * 24 do
        K.nutrients.minute(state, records, empty, empty, ctx, 60)
        for i = 1, #records.ORDER do
            local key = records.ORDER[i]
            if state[key].g == 4 and first[key] == nil then
                first[key] = step / 24
            end
        end
    end
    return state, first
end
"""


def _simulate(h, days, dial=None):
    state, first = h.rt.eval(SIM)(_records(h), days, dial)
    return h.py(state), h.py(first)


def test_zero_intake_for_forty_days(rh):
    state, first = _simulate(rh, 41)
    assert 39 <= first["vitC"] <= 41                           # ln(1/0.15)/k = 40 d
    assert 16 <= first["thiamine"] <= 18                       # ln(1/0.4167)/0.0513 = 17.05 d
    assert first["choline"] == pytest.approx(21, abs=1 / 24 + 1e-9)
    assert first["efa"] == pytest.approx(28, abs=1 / 24 + 1e-9)
    assert first["riboflavin"] == pytest.approx(27, abs=1 / 24 + 1e-9)
    assert first["vitK"] == pytest.approx(7.07, abs=0.05)
    assert state["vitB12"]["g"] == 1                           # real scale: exp(-0.001 x 41) = 0.96
    assert state["vitB12"]["p"] == pytest.approx(math.exp(-0.001 * 41), abs=1e-9)
    assert state["iron"]["g"] == 1 and state["vitA"]["g"] == 1
    assert state["vitE"]["g"] == 1 and state["sodium"]["g"] == 1 and state["caffeine"]["g"] == 1
    assert state["allReplete"] is False


def test_the_dial_compresses_b12(rh):
    state, _ = _simulate(rh, 40, 10)
    assert state["vitB12"]["p"] == pytest.approx(math.exp(-0.01 * 40), abs=1e-9)   # 0.6703
    assert state["vitB12"]["g"] == 2
    assert state["vitC"]["p"] == pytest.approx(0.15, abs=1e-9)  # vitC takes no dial (exponent 0)
