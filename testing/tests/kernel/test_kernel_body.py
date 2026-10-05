"""The body split, the weight band, the direction flags and the macro-mirror maps (NR_Kernel_Body.lua),
Plan 3 Task 6.

NR_Kernel_Body.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.body. Every expectation below is hand-computed
from the file's constants: the band-anchored fat-fraction table (anchors 50/60/70/80/95/105 kg; male
0.06..0.33, female 0.15..0.40; S1051 open, a design-phase-v1 game choice), the build offsets, the
BF_MIN/BF_MAX clamp, the band edges (#0531, #0155), the flag thresholds (ruling 17) and the mirror maps
(#0022, #0023, ruling 13).
"""
import pytest

TOL = 1e-9


def _close(a, b):
    return abs(a - b) < TOL


def _build(host, **flags):
    return host.table(flags)


# --- constants ---

def test_constants(host):
    b = host.K.body
    assert list(host.py(b.ANCHORS_W).values()) == [50, 60, 70, 80, 95, 105]
    assert list(host.py(b.BF_MALE).values()) == [0.06, 0.09, 0.13, 0.18, 0.27, 0.33]
    assert list(host.py(b.BF_FEMALE).values()) == [0.15, 0.19, 0.23, 0.28, 0.35, 0.40]
    assert host.py(b.BF_MIN) == {1: 0.04, 2: 0.12}
    assert b.BF_MAX == 0.55
    assert host.py(b.BUILD_OFFSET) == {"athletic": -0.04, "fit": -0.02, "outOfShape": 0.02,
                                       "unfit": 0.04, "strong": -0.02, "stout": -0.01}


# --- interp ---

@pytest.mark.parametrize("w,sex,bf", [
    (80, 1, 0.18),
    (87.5, 1, 0.225),
    (40, 1, 0.06),        # flat below the first anchor
    (50, 1, 0.06),
    (105, 1, 0.33),
    (120, 2, 0.40),       # flat above the last anchor
    (55, 2, 0.17),
    (80, 2, 0.28),
])
def test_interp(host, w, sex, bf):
    assert _close(host.call("body.interp", w, sex), bf)


# --- split ---

def test_split_plain(host):
    fm, lm, bf = host.call("body.split", 80, 1, _build(host))
    assert _close(fm, 14.4)
    assert _close(lm, 65.6)
    assert _close(bf, 0.18)


def test_split_athletic_offset(host):
    fm, lm, bf = host.call("body.split", 80, 1, _build(host, athletic=True))
    assert _close(bf, 0.14)
    assert _close(fm, 80 * 0.14)
    assert _close(fm + lm, 80)


def test_split_false_flag_adds_nothing(host):
    _, _, bf = host.call("body.split", 80, 1, _build(host, athletic=False, stout=True))
    assert _close(bf, 0.17)


def test_split_clamps_at_bf_min(host):
    fm, lm, bf = host.call("body.split", 50, 1, _build(host, athletic=True, strong=True))
    assert _close(bf, 0.04)
    assert _close(fm, 2.0)
    assert _close(lm, 48.0)


def test_split_clamps_at_bf_min_female(host):
    _, _, bf = host.call("body.split", 40, 2, _build(host, athletic=True, fit=True))
    assert _close(bf, 0.12)


def test_split_clamps_at_bf_max(host):
    _, _, bf = host.call("body.split", 150, 2, _build(host, unfit=True, outOfShape=True, stout=True))
    assert _close(bf, 0.45)
    b = host.K.body
    b.BF_MAX = 0.42
    try:
        _, _, bf = host.call("body.split", 150, 2, _build(host, unfit=True))
        assert _close(bf, 0.42)
    finally:
        b.BF_MAX = 0.55


def test_split_clamps_weight_high(host):
    fm, lm, bf = host.call("body.split", 300, 2, _build(host))
    assert _close(bf, 0.40)
    assert _close(fm, 80.0)
    assert _close(lm, 120.0)


def test_split_clamps_weight_low(host):
    fm, lm, bf = host.call("body.split", 10, 1, _build(host))
    assert _close(bf, 0.06)
    assert _close(fm + lm, 35.0)


# --- band ---

@pytest.mark.parametrize("w,band", [
    (100, "obese"),
    (130, "obese"),
    (99.99, "overweight"),
    (85, "overweight"),
    (84.99, "normal"),
    (80, "normal"),
    (75.01, "normal"),
    (75, "underweight"),
    (65.01, "underweight"),
    (65, "veryUnderweight"),
    (50.01, "veryUnderweight"),
    (50, "emaciated"),
    (30, "emaciated"),
])
def test_band(host, w, band):
    assert host.call("body.band", w) == band


# --- flags / trend ---

@pytest.mark.parametrize("t,expect", [
    (0.05, (True, False, False)),
    (0.15, (True, True, False)),
    (-0.05, (False, False, True)),
    (0, (False, False, False)),
    (0.02, (False, False, False)),
    (0.10, (True, False, False)),
    (-0.02, (False, False, False)),
])
def test_flags(host, t, expect):
    assert tuple(host.call("body.flags", t)) == expect


def test_trend_reads_the_oldest_slot(host):
    ring = host.table({i: 80 for i in range(1, 8)})
    assert _close(host.call("body.trend", ring, 80.7), 0.1)
    ring[1] = 81.4
    assert _close(host.call("body.trend", ring, 80.7), -0.1)


def test_trend_of_a_fresh_ring_is_zero(host):
    ring = host.table({i: 72.5 for i in range(1, 8)})
    assert host.call("body.trend", ring, 72.5) == 0


# --- the macro-mirror maps ---

@pytest.mark.parametrize("eb,out", [(5000, 3700), (-3000, -2200), (120.5, 120.5), (3700, 3700), (-2200, -2200)])
def test_map_calories(host, eb, out):
    assert _close(host.call("body.mapCalories", eb), out)


@pytest.mark.parametrize("p,out", [
    (0.3, -400),
    (0.5, -400),
    (0.65, -150),
    (0.8, 0),
    (1.2, 75),
    (1.6, 150),
    (2.0, 200),
])
def test_map_proteins(host, p, out):
    assert _close(host.call("body.mapProteins", p), out)


def test_map_proteins_opens_the_xp_arm_near_107(host):
    # #2112: vanilla's x1.5 XP arm needs 50 < proteins < 300; 1.07 g/kg/d maps to 50.625.
    v = host.call("body.mapProteins", 1.07)
    assert v >= 50
    assert _close(v, 50.625)


@pytest.mark.parametrize("g,out", [(400, 100), (300, 0), (0, -300), (2000, 1000), (-1000, -500)])
def test_map_carbs(host, g, out):
    assert _close(host.call("body.mapCarbs", g), out)


@pytest.mark.parametrize("g,out", [(0, -70), (70, 0), (120, 50), (5000, 1000)])
def test_map_lipids(host, g, out):
    assert _close(host.call("body.mapLipids", g), out)


# --- new ---

def test_new_record_body(host):
    body = host.py(host.K.body["new"](80, 1, _build(host), 5, 1.0, 1.0, 100))
    scalars = {
        "bv": 1, "fm0": body["fm"], "lm0": body["lm"], "lm0dis": body["lm"], "fmRef": body["fm"], "l0": 5, "sex": 1, "r": 1.0,
        "traitCarry": 1.0, "bornAge": 100, "lastAgeH": 100, "at": 0, "dayIndex": 4, "inDay": 0, "eeDay": 0, "ebDay": 0,
        "actKcalDay": 0, "pDay": 0, "carbDay": 0, "lipDay": 0, "alcDay": 0, "eb24h": 0, "vStr": 0,
        "vHyp": 0, "vStrHigh": 0, "metMinDay": 0, "band1Day": 0, "band2Day": 0, "n": 0, "nPeak": 0,
        "tPeakD": 4, "cumDef": 0, "tDisuse": 0, "shownL": 5, "riseHeldH": 0, "lastFallAge": 100,
        "delta": 1.0, "band": "normal", "tac": 1.0, "dmod": 1, "rmod": 1, "energyState": 1,
    }
    for k, v in scalars.items():
        assert body[k] == v, k
    assert _close(body["fm"], 14.4)
    assert _close(body["lm"], 65.6)
    assert list(body["eb7"].values()) == [0] * 7
    assert list(body["mass7"].values()) == [80] * 7
    assert len(body["mass7"]) == 7
    assert list(body["bandWeek"].values()) == [{1: 0, 2: 0}] * 7
    assert len(body["bandWeek"]) == 7
    assert list(body["nHist"].values()) == [0] * 14
    assert len(body["nHist"]) == 14
    assert body["mirrorLast"] == {1: 0, 2: 0, 3: 0, 4: 0}
    ring_keys = {"eb7", "mass7", "bandWeek", "nHist", "mirrorLast"}
    assert set(body) == set(scalars) | {"fm", "lm"} | ring_keys


def test_new_rings_are_distinct_tables(host):
    body = host.K.body["new"](62, 2, _build(host, fit=True), 3, 0.9, 1.3, 47.5)
    week = body.bandWeek
    assert not host.rt.eval("rawequal")(week[1], week[2])
    py = host.py(body)
    assert py["band"] == "veryUnderweight"
    assert py["dayIndex"] == 1
    assert py["tPeakD"] == 1
    assert py["delta"] == 0.9
    assert _close(py["fm"] / 62, 0.19 * 0.8 + 0.23 * 0.2 - 0.02)
