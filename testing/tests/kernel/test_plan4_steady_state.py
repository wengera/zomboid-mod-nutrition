"""The 60-day kernel replay of a mixed diet at the RDA (Plan 4 close, ruling T19-5).

No measured acceptance arm touched fat-soluble absorption, so this replay stands in for a fourth boot: a
male 80 kg character eats three meals a day (08:00, 13:00, 19:00), each 300 ug retinol, 40 ug vitK and
10 g fat (900 ug retinol, 120 ug vitK and 30 g fat a day), through the real kernel chain the slow clock
runs -- K.stomach.ingest, then per minute K.stomach.context, drain, absorb (the fat factor on the meal's
lipids, ruling T19-1), the vitamin A fold (carotene 0, so absorbed vitA = absorbed retinol, as
NR_Server_Nutrients' factors writes it) and K.nutrients.minute over NR.data.records with K.interact.two.
Every number is recomputed below in Python doubles from the same constants and asserted to 1e-6.

The e-fold is 3 g (ruling T19-6). The buffer's lipids empty with the vitamins on Plan 11c's zero-order solid
lane (Task 6), so three 10 g-fat meals a day absorb 71 % of their fat-soluble load (0.7139 of the 60-day retinol);
vitA's liver p is 0.883 at day 60 (lowest 0.882 over days 30-60) and vitK's 0.989 (lowest 0.907 over days 30-60,
grade 1). The brief's
expectations (vitA p >= 0.85, vitK grade 1) are met; the numbers are pinned as measured, not tuned.
"""
import math
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DATA = os.path.join(SHARED, "NR_Data_Records.lua")

DAYS = 60
MEALS = (480, 780, 1140)            # minute of the day
MEAL = dict(retinol=300.0, vitK=40.0, lipids=10.0)
MEAL_KCAL = 490.0                  # the Lua meal's calories (REPLAY), which set the zero-order lane
LN2 = 0.6931471805599453


def _frac(E, dtM):
    fw = 1 - math.exp(-LN2 * dtM / 13)
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def rh(host):
    _load(host, DATA)
    return host


# The replay runs with the coverage line hook off (86 400 minutes x 27 records under a per-line hook
# is minutes of wall time); every line it runs is covered by the kernel's own tests.
REPLAY = r"""
function(records, days, meals, retinol, vitK, lipids)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local st = K.stomach.new()
    local state = K.nutrients.newState(records)
    local ctx = { sex = 1, w = 80, eeMJ = 10, pDay = 80, dial = 1, excessOn = true, two = K.interact.two,
                  riboGrade = 1, e24Zn = 0 }
    local sctx = {}
    local empty = {}
    local meal = K.vector.new()
    meal.retinol = retinol
    meal.vitK = vitK
    meal.lipids = lipids
    meal.proteins = 25
    meal.carbs = 75
    meal.calories = 490
    local totIn = 0
    local totAbs = 0
    local minK = 1
    local minA = 1
    for m = 0, days * 1440 - 1 do
        local mod = m - math.floor(m / 1440) * 1440
        if mod == meals[1] or mod == meals[2] or mod == meals[3] then
            K.stomach.ingest(st, meal)
            totIn = totIn + retinol
        end
        K.stomach.context(st, sctx)
        local absorbed = K.stomach.absorb(K.stomach.drain(st, 1 / 60), sctx)
        absorbed.vitA = absorbed.retinol
        totAbs = totAbs + absorbed.retinol
        K.nutrients.minute(state, records, absorbed, empty, ctx, 1)
        if m >= 30 * 1440 then
            minK = math.min(minK, state.vitK.p)
            minA = math.min(minA, state.vitA.p)
        end
    end
    debug.sethook(hook, mask)
    return state.vitA.p, state.vitA.p2, state.vitA.g, state.vitK.p, state.vitK.g, totAbs / totIn, minA, minK
end
"""


def _grade_hyst(p, ladder, g_prev, hyst=0.02):
    g = 1 if p > ladder[0] else 2 if p > ladder[1] else 3 if p > ladder[2] else 4
    if g >= g_prev:
        return g
    h = g_prev
    while h > g and p > ladder[h - 2] + hyst:
        h -= 1
    return h


def _replay_py():
    """The same chain for retinol and vitK in doubles: the buffer, the meal-lipid factor, the ZOH step."""
    b = dict(lipids=0.0, retinol=0.0, vitK=0.0, calories=0.0)
    kA = 0.008748517704155646                  # vitA k (the record)
    kK = 0.25946357728426606                   # vitK k (the record)
    RA = 900.0                                 # male RDA, no absorb field
    RK = 1.0 * 80                              # 1 ug/kg x 80 kg
    pA = pK = 1.0
    gK = 1
    tot_in = tot_abs = 0.0
    minA = minK = 1.0
    dtD = 1 / 1440
    for m in range(DAYS * 1440):
        if m % 1440 in MEALS:
            for k, v in MEAL.items():
                b[k] = b[k] + v * 1
            b["calories"] = b["calories"] + MEAL_KCAL
            tot_in += MEAL["retinol"]
        lip = b["lipids"]
        f = _frac(b["calories"], 1.0)
        em = {k: 0 + v * f for k, v in b.items()}
        for k in b:
            b[k] = b[k] * (1 - f)
        fat = min(max(1 - math.exp(-lip / 3), 0.05), 1.0)
        aA = em["retinol"] * 1.0 * fat
        aK = em["vitK"] * 1.0 * fat
        tot_abs += aA
        e = math.exp(-kA * dtD)
        pA = pA * e + (1 - e) * (aA / dtD / RA)
        e = math.exp(-kK * dtD)
        pK = min(pK * e + (1 - e) * (aK / dtD / RK), 1.0)
        gK = _grade_hyst(pK, (0.70, 0.45, 0.25), gK)
        if m >= 30 * 1440:
            minA = min(minA, pA)
            minK = min(minK, pK)
    return pA, pK, gK, tot_abs / tot_in, minA, minK


def test_sixty_days_at_the_rda_through_the_kernel_chain(rh):
    records = rh.G.NutritionRevamp.data.records
    meals = rh.rt.table(*MEALS)
    pA, p2A, gA, pK, gK, frac, minA, minK = rh.rt.eval(REPLAY)(records, DAYS, meals, MEAL["retinol"],
                                                              MEAL["vitK"], MEAL["lipids"])
    epA, epK, egK, efrac, eminA, eminK = _replay_py()
    # the Python doubles, as literals (the replay above, run once)
    assert abs(efrac - 0.7138916612921502) < 1e-9
    assert abs(epA - 0.8834645470568487) < 1e-9
    assert abs(epK - 0.9894153856691867) < 1e-9
    assert abs(eminK - 0.9074649197628905) < 1e-9
    # the kernel chain agrees with the doubles
    assert abs(frac - efrac) < 1e-6
    assert abs(pA - epA) < 1e-6
    assert abs(pK - epK) < 1e-6
    assert abs(minA - eminA) < 1e-6
    assert abs(minK - eminK) < 1e-6
    assert gK == egK
    # vitamin A: p 0.883 at day 60 (lowest 0.882 over days 30-60); graded 1 (plasma p2 at 1)
    assert gA == 1 and p2A == 1
    assert pA >= 0.85 and minA >= 0.85               # the brief's expectation, met
    # vitamin K: near its 80 ug/d requirement at a 0.71 absorbed fraction (86 ug/d), grade 1
    assert gK == 1                                   # the brief's grade 1, met
