"""The lethal causes' symptoms (Plan 18 Task 2; spec docs/superpowers/specs/2026-10-21-symptoms-design.md, sections 1-3).

K.effects.symptoms reads each cause's progress p = 1 - record.drain.frac[code] and folds the SYMPTOMS table of
NR_Data_Effects.lua: the endurance cap (the lowest), the stress and unhappiness floors (the highest) and the added pain
per body part (summed under a per-part cap, only while the cause is active). K.hybrid.capAt sizes any cap in its
Endurance level's band for the day length. Every expectation is computed in Python doubles beside it.
"""
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")

TOL = 1e-12
TORSO_LOWER, HEAD, LEG_L, LEG_R = 7, 8, 13, 14
MOD = {0: 0.5, 1: 0.5, 2: 0.6, 3: 0.6, 4: 0.6, 5: 0.6, 6: 0.7, 7: 0.78, 8: 0.8, 9: 0.8, 10: 0.7, 11: 0.7, 12: 0.7,
       13: 0.6, 14: 0.6, 15: 0.5, 16: 0.5}
END_K = [(0, 0.73), (1 / 3, 0.48), (2 / 3, 0.23), (1, 0.08)]
STRESS_K = [(0, 0), (0.5, 0.30), (0.9, 0.55), (1, 0.55)]
UNHAPPY_K = [(0, 0), (0.5, 25), (0.9, 50), (1, 50)]
CAUSES = ["starvation", "scurvy", "beriberi", "pellagra", "hyponatraemia", "dehydration", "iron"]
PARTS = {1: [7], 2: [13, 14], 3: [13, 14], 4: [7], 5: [8], 6: [8], 7: [7]}


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def sh(host):
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua", "NR_Data_Effects.lua"):
        _load(host, os.path.join(SHARED, name))
    return host


def _knots(k, p):
    if p <= k[0][0]:
        return k[0][1]
    for (p0, v0), (p1, v1) in zip(k, k[1:]):
        if p <= p1:
            return v0 + (v1 - v0) * (p - p0) / (p1 - p0)
    return k[-1][1]


def _drain(h, frac, mask=None, rec=None):
    """record.drain with frac {code: f}; mask and rec are code lists (mask defaults to every code in frac)."""
    if mask is None:
        mask = list(frac) if rec is None else [c for c in frac if c not in rec]
    rec = rec or []
    return h.table({"frac": {c: f for c, f in frac.items()}, "mask": float(sum(2 ** (c - 1) for c in mask)),
                    "recovering": float(sum(2 ** (c - 1) for c in rec))})


def _sym(h, D, sev=1, overlay=False, day=90, E=None):
    E = E if E is not None else h.K.effects.new()
    h.K.effects.symptoms(E, h.G.NutritionRevamp.data.effects, D, sev, overlay, day)
    return E


def _pain(E):
    return {i: E.pain[i] for i in range(17)}


def _cause_cap(p, sev=1):
    return max(0.05, min(1, 1 - (1 - _knots(END_K, p)) * sev))


# --- the shapes ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("p", [0, 0.5, 1])
def test_each_shape_at_0_half_and_1(sh, p):
    K = sh.K
    assert K.effects.shapeAt(sh.table({"shape": "flat", "v": 15}), p) == 15
    assert abs(K.effects.shapeAt(sh.table({"shape": "linear", "a": 2, "b": 10}), p) - (2 + 8 * p)) < TOL
    k = sh.table({"shape": "knots", "k": {1: 0, 2: 1, 3: 0.4, 4: 3, 5: 1, 6: 0}})
    want = {0: 1, 0.5: 3 + (0 - 3) * (0.5 - 0.4) / 0.6, 1: 0}[p]
    assert abs(K.effects.shapeAt(k, p) - want) < TOL


def test_knots_hold_beyond_the_first_and_the_last(sh):
    k = sh.table({"shape": "knots", "k": {1: 0.2, 2: 5, 3: 0.8, 4: 9}})
    assert sh.K.effects.shapeAt(k, 0) == 5                               # before the first knot: its value
    assert abs(sh.K.effects.shapeAt(k, 0.5) - 7) < TOL                   # 5 + 4 x 0.3 / 0.6
    assert sh.K.effects.shapeAt(k, 1) == 9                               # past the last knot: its value


def test_the_bit_test_reads_each_code(sh):
    for code in range(1, 8):
        assert sh.K.effects.hasBit(float(2 ** (code - 1)), code) is True
        assert sh.K.effects.hasBit(float(127 - 2 ** (code - 1)), code) is False
    assert sh.K.effects.hasBit(0.0, 1) is False


# --- the clock -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("f", [1.0, 0.75, 0.5, 0.3, 0.1, 0.0])
def test_the_clock_reads_one_minus_the_remaining_fraction(sh, f):
    p = 1 - f
    E = _sym(sh, _drain(sh, {2: f}))                                     # scurvy, active
    assert abs(E.symCap - _knots(END_K, p)) < TOL
    assert abs(E.stressFloor - _knots(STRESS_K, p)) < TOL
    assert abs(E.unhappyFloor - _knots(UNHAPPY_K, p)) < TOL
    assert abs(E.enduranceCap - E.symCap) < TOL                          # no Overfull row: the symptom cap


def test_the_levels_come_at_their_progress(sh):
    # Endurance level 2 once the cap is at or under 0.5, level 3 under 0.25, level 4 under 0.10 (#3926); Stress 1 above
    # 0.25 and 2 above 0.5; Unhappy 1 above 20 and 2 above 45 (#2369)
    def at(p):
        return _sym(sh, _drain(sh, {1: 1 - p}))
    assert 0.5 < at(0).symCap <= 0.75 and at(0).stressFloor == 0 and at(0).unhappyFloor == 0
    assert 0.25 < at(0.4).symCap <= 0.5
    assert 0.10 < at(0.8).symCap <= 0.25
    assert at(1).symCap <= 0.10
    assert 0.25 < at(0.5).stressFloor <= 0.5 and 20 < at(0.5).unhappyFloor <= 45
    assert at(0.9).stressFloor > 0.5 and at(0.9).unhappyFloor > 45
    assert at(0.4).stressFloor <= 0.25 and at(0.4).unhappyFloor <= 20 + 1e-9


def test_a_progress_outside_0_1_is_clamped(sh):
    assert abs(_sym(sh, _drain(sh, {3: 1.2})).symCap - 0.73) < TOL       # p -0.2 reads 0
    assert abs(_sym(sh, _drain(sh, {3: -0.5})).symCap - 0.08) < TOL      # p 1.5 reads 1


# --- pain --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("code", range(1, 8))
def test_each_causes_pain_sits_on_its_parts_and_sums_to_15_pain(sh, code):
    E = _sym(sh, _drain(sh, {code: 0.6}))
    P = _pain(E)
    parts = PARTS[code]
    for i in range(17):
        if i in parts:
            assert abs(P[i] - 15 / len(parts) / MOD[i]) < 1e-9, (code, i)
        else:
            assert P[i] == 0, (code, i)
    assert abs(sum(P[i] * MOD[i] for i in parts) - 15) < 1e-9            # PAIN's target: Pain level 1's band middle
    assert E.painOn is True


def test_the_lower_torso_value_is_x491s(sh):
    P = _pain(_sym(sh, _drain(sh, {1: 0.9})))
    assert abs(P[TORSO_LOWER] - 15 / 0.78) < 1e-12                       # 19.23, x491 held 20 at level 1


def test_pain_only_while_the_bit_is_in_the_mask(sh):
    E = _sym(sh, _drain(sh, {1: 0.5}, rec=[1]))                          # starvation recovering: its ceiling applies
    assert all(v == 0 for v in _pain(E).values()) and E.painOn is False
    assert abs(E.symCap - _knots(END_K, 0.5)) < TOL                      # the cap and the floors still read p
    assert abs(E.stressFloor - 0.30) < TOL
    E = _sym(sh, _drain(sh, {1: 0.5, 2: 0.5}, mask=[2], rec=[1]))        # only scurvy active
    P = _pain(E)
    assert P[TORSO_LOWER] == 0 and abs(P[LEG_L] - 12.5) < 1e-9 and abs(P[LEG_R] - 12.5) < 1e-9


def test_a_cause_without_a_fraction_adds_nothing(sh):
    E = _sym(sh, _drain(sh, {}, mask=[1]))                               # a bit with no fraction: not applied
    assert E.symCap == 1 and E.painOn is False and E.stressFloor == 0


def test_pain_clears_the_minute_its_cause_ends(sh):
    E = _sym(sh, _drain(sh, {6: 0.4}))
    assert E.pain[HEAD] > 0
    _sym(sh, _drain(sh, {}), E=E)
    assert all(v == 0 for v in _pain(E).values()) and E.painOn is False
    assert E.symCap == 1 and E.stressFloor == 0 and E.unhappyFloor == 0


def test_the_half_dip_is_added_only_past_600_minutes(sh):
    base = 15 / 0.8
    assert abs(_sym(sh, _drain(sh, {5: 0.5}), day=600).pain[HEAD] - base) < 1e-9
    assert abs(_sym(sh, _drain(sh, {5: 0.5}), day=1440).pain[HEAD] - (base + 0.005 * 1440)) < 1e-9
    assert _sym(sh, _drain(sh, {5: 0.5}), day=1440).pain[TORSO_LOWER] == 0   # only painful parts gain it


# --- overlap ----------------------------------------------------------------------------------------------------

def test_overlap_takes_the_lowest_cap_and_the_highest_floors(sh):
    E = _sym(sh, _drain(sh, {1: 0.9, 6: 0.2}))                           # starvation p 0.1, dehydration p 0.8
    assert abs(E.symCap - _knots(END_K, 0.8)) < TOL
    assert abs(E.stressFloor - _knots(STRESS_K, 0.8)) < TOL
    assert abs(E.unhappyFloor - _knots(UNHAPPY_K, 0.8)) < TOL
    P = _pain(E)
    assert abs(P[TORSO_LOWER] - 15 / 0.78) < 1e-9 and abs(P[HEAD] - 15 / 0.8) < 1e-9   # each on its own part


def test_overlap_keeps_the_deeper_cause_whichever_code_comes_first(sh):
    E = _sym(sh, _drain(sh, {1: 0.2, 6: 0.9}))                           # starvation p 0.8, dehydration p 0.1
    assert abs(E.symCap - _knots(END_K, 0.8)) < TOL
    assert abs(E.stressFloor - _knots(STRESS_K, 0.8)) < TOL
    assert abs(E.unhappyFloor - _knots(UNHAPPY_K, 0.8)) < TOL


def test_pain_sums_per_part_under_the_cap(sh):
    E = _sym(sh, _drain(sh, {1: 0.5, 4: 0.5, 7: 0.5}))                   # three causes on the lower torso: 45 PAIN
    assert abs(E.pain[TORSO_LOWER] - 20 / 0.78) < 1e-9                   # capped at Pain level 1's top
    E = _sym(sh, _drain(sh, {2: 0.5, 3: 0.5}))                           # scurvy and beriberi on both lower legs
    assert abs(E.pain[LEG_L] - 25) < 1e-9 and abs(E.pain[LEG_R] - 25) < 1e-9   # 2 x 12.5, under 20 / 0.6
    E = _sym(sh, _drain(sh, {1: 0.5, 4: 0.5}))                           # two on the lower torso: 30 PAIN, capped
    assert abs(E.pain[TORSO_LOWER] - 20 / 0.78) < 1e-9


def test_the_overfull_cap_and_the_symptom_cap_take_the_lower(sh):
    E = sh.K.effects.new()
    E.rowEndCap = 0.73
    _sym(sh, _drain(sh, {}), E=E)
    assert E.enduranceCap == 0.73                                        # Overfull alone: its cap unchanged
    _sym(sh, _drain(sh, {2: 0.5}), E=E)
    assert abs(E.enduranceCap - _knots(END_K, 0.5)) < TOL                # the deeper symptom cap
    _sym(sh, _drain(sh, {2: 1.0}), E=E)
    assert E.enduranceCap == 0.73                                        # equal at onset: 0.73 either way


def test_the_composer_keeps_the_lower_of_the_two(sh):
    from .test_kernel_effects import _compose
    E = sh.K.effects.new()
    E.symCap = 0.4
    _compose(sh, flags={"overfull": 3}, E=E)
    assert E.rowEndCap == 0.73 and E.enduranceCap == 0.4
    E.symCap = 1
    _compose(sh, flags={"overfull": 0}, E=E)
    assert E.rowEndCap == 1 and E.enduranceCap == 1


# --- Severity and Overlay ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("sev", [0, 0.5, 1, 2, 3])
def test_severity_scales_every_magnitude(sh, sev):
    p = 0.6
    E = _sym(sh, _drain(sh, {1: 1 - p}), sev=sev)
    assert abs(E.symCap - _cause_cap(p, sev)) < TOL
    assert abs(E.stressFloor - min(0.70, _knots(STRESS_K, p) * sev)) < TOL
    assert abs(E.unhappyFloor - min(59, _knots(UNHAPPY_K, p) * sev)) < TOL
    want = min(15 * sev / 0.78, 20 * sev / 0.78)
    assert abs(E.pain[TORSO_LOWER] - want) < 1e-9
    assert E.painOn is (sev > 0)


def test_severity_scales_the_per_part_cap(sh):
    E = _sym(sh, _drain(sh, {1: 0.5, 4: 0.5, 7: 0.5}), sev=2)            # 90 PAIN against a cap of 40
    assert abs(E.pain[TORSO_LOWER] - 40 / 0.78) < 1e-9


def test_overlay_drops_starvation_and_dehydration(sh):
    D = _drain(sh, {1: 0.2, 6: 0.2, 2: 0.9})
    E = _sym(sh, D, overlay=True)
    assert abs(E.symCap - _knots(END_K, 0.1)) < TOL                      # scurvy alone
    P = _pain(E)
    assert P[TORSO_LOWER] == 0 and P[HEAD] == 0 and P[LEG_L] > 0
    E = _sym(sh, _drain(sh, {1: 0.2, 6: 0.2}), overlay=True)
    assert E.symCap == 1 and E.painOn is False and E.stressFloor == 0 and E.unhappyFloor == 0
    E = _sym(sh, _drain(sh, {1: 0.2, 6: 0.2}), overlay=False)
    assert abs(E.symCap - _knots(END_K, 0.8)) < TOL


# --- recovery ---------------------------------------------------------------------------------------------------

def test_recovery_eases_the_cap_and_the_floors_with_p(sh):
    caps, stress, unhappy = [], [], []
    for f in (0.05, 0.3, 0.6, 0.9):                                      # the ceiling recovering toward 1
        E = _sym(sh, _drain(sh, {3: f}, rec=[3]))
        caps.append(E.symCap)
        stress.append(E.stressFloor)
        unhappy.append(E.unhappyFloor)
        assert E.painOn is False
    assert caps == sorted(caps) and caps[0] < caps[-1]
    assert stress == sorted(stress, reverse=True) and stress[0] > stress[-1]
    assert unhappy == sorted(unhappy, reverse=True) and unhappy[0] > unhappy[-1]


# --- no allocation ----------------------------------------------------------------------------------------------

def test_no_table_is_allocated_per_step(sh):
    E = sh.K.effects.new()
    pain = E.pain
    D = _drain(sh, {1: 0.5, 2: 0.4, 6: 0.3})
    run = sh.rt.eval("""function(K, T, E, D, n)
        K.effects.symptoms(E, T, D, 1, false, 1440)
        local hook, mask, count = debug.gethook()
        debug.sethook()
        collectgarbage("collect")
        collectgarbage("stop")
        local before = collectgarbage("count")
        for i = 1, n do
            K.effects.symptoms(E, T, D, 1, false, 1440)
        end
        local after = collectgarbage("count")
        collectgarbage("restart")
        debug.sethook(hook, mask, count)
        return after - before
    end""")
    grown = run(sh.K, sh.G.NutritionRevamp.data.effects, E, D, 2000)
    assert grown < 0.5                                                   # KB over 2000 steps: nothing allocated
    assert sh.rt.eval("function(a, b) return rawequal(a, b) end")(E.pain, pain)      # the same table, refilled


# --- the table --------------------------------------------------------------------------------------------------

def _arr(t):
    return [t[i] for i in range(1, len(t) + 1)]


def test_the_table_names_the_seven_causes_in_drain_code_order(sh):
    S = sh.G.NutritionRevamp.data.effects.SYMPTOMS
    causes = _arr(S.CAUSES)
    assert [c.name for c in causes] == CAUSES
    states = sh.K.drain.states
    assert [states[i].name for i in range(1, 8)] == CAUSES
    assert [c.name for c in causes if c.overlayOff] == ["starvation", "dehydration"]


def test_every_cause_carries_the_four_levers_and_its_parts(sh):
    S = sh.G.NutritionRevamp.data.effects.SYMPTOMS
    for code, c in enumerate(_arr(S.CAUSES), 1):
        rows = _arr(c.list)
        assert sorted(r.lever for r in rows) == ["endurance", "pain", "stress", "unhappy"], c.name
        for r in rows:
            assert r.shape in ("flat", "linear", "knots"), (c.name, r.lever)
            if r.shape == "knots":
                k = _arr(r.k)
                ps = k[0::2]
                assert len(k) % 2 == 0 and ps == sorted(ps) and ps[0] == 0 and ps[-1] == 1, (c.name, r.lever)
        pain = [r for r in rows if r.lever == "pain"][0]
        assert pain.shape == "flat" and pain.v == 15
        assert _arr(pain.parts) == PARTS[code], c.name


def test_the_magnitudes_are_task_1s(sh):
    S = sh.G.NutritionRevamp.data.effects.SYMPTOMS
    rows = {r.lever: r for r in _arr(S.CAUSES[1].list)}
    pairs = lambda r: list(zip(_arr(r.k)[0::2], _arr(r.k)[1::2]))
    assert pairs(rows["endurance"]) == END_K
    assert pairs(rows["stress"]) == STRESS_K and pairs(rows["unhappy"]) == UNHAPPY_K
    assert S.PAIN_TOP == 20 and S.CAP_LO == 0.05 and S.STRESS_HI == 0.70 and S.UNHAPPY_HI == 59
    for code in range(1, 8):                                             # one shared row per lever
        crow = {r.lever: r for r in _arr(S.CAUSES[code].list)}
        for lever in ("endurance", "stress", "unhappy"):
            assert sh.rt.eval("function(a, b) return rawequal(a, b) end")(crow[lever], rows[lever])


def test_the_pain_modifiers_are_the_jars(sh):
    m = sh.K.effects.PAIN_MOD
    assert {i: m[i] for i in range(17)} == MOD
    assert sh.K.effects.PAIN_PARTS == 17


# --- the endurance ceiling at a day length (K.hybrid.capAt, every level) -------------------------------------------

@pytest.mark.parametrize("cap,day,want", [
    (0.73, 90, 0.73), (0.48, 90, 0.48), (0.23, 90, 0.23), (0.08, 90, 0.08),        # the four levels' caps hold
    (0.75, 90, 0.75 - 0.0000930 / 3 * 1.8 * 1.6 * 2 * 90),                          # level 1's edge: room under it
    (0.5, 90, 0.5 - 0.0000930 / 3 * 1.8 * 1.6 * 2 * 90),                            # level 2's edge
    (0.73, 1440, 0.51), (0.48, 1440, 0.26), (0.23, 1440, 0.11), (0.08, 1440, 0.01),  # long days: the band's floor
    (0.9, 90, 0.9), (1, 90, 1), (0.0, 90, 0.0),                                      # level 0's band, none, the bottom
])
def test_the_ceiling_keeps_its_level_at_a_day_length(sh, cap, day, want):
    assert abs(sh.K.hybrid.capAt(cap, day) - want) < 1e-12


def test_every_symptom_cap_shows_its_level_at_the_90_minute_day(sh):
    # the level a cap shows: 1 in (0.5, 0.75], 2 in (0.25, 0.5], 3 in (0.10, 0.25], 4 at or under 0.10 (#3926)
    def level(e):
        return 0 if e > 0.75 else 1 if e > 0.5 else 2 if e > 0.25 else 3 if e > 0.10 else 4
    margin = 0.0000930 / 3 * 1.8 * 1.6 * 2 * 90
    for i in range(101):
        p = i / 100
        c = sh.K.hybrid.capAt(_cause_cap(p), 90)
        assert level(c) == level(c + margin * 0.999), p                         # one minute's worst climb keeps the level
        assert level(c) == level(_cause_cap(p)), p                      # capAt never moves it out of its band
