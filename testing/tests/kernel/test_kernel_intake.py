"""The eat's arithmetic in the kernel (NR_Kernel_Intake.lua, K.intake), Plan 10 Task R3.

NR_Kernel_Intake.lua is a kernel file, so the session `host` fixture loads it through its glob and the coverage
gate (test_zz_coverage.py) sees every line. The behaviour assertions are test_intake_shape.py's, ported to call
the kernel directly: K.intake.shareEaten, fractionOf, macrosEaten, sourceOf, chainOne, newTrace, traceStep and
assemble. The adapter (NR_Server_Intake.lua) keeps each public name as a thin wrapper; its own shape test still
drives them through the adapter, and the golden trace (test_golden_trace.py) proves the move changed nothing.

The factor pins close the golden trace's blind spot (R0 fix-2 re-review): the trace never feeds an inferred food
as a second bite, so a swap of the inferred branch's factor from frac to share left it identical. Each source's
factor is pinned here on inputs where frac != share: dish and inferred take frac; craft, table and declared take
share; the thirst-only share is the drop over scriptThirst. The property tests run 500 seeded cases each, with
no new dependency (random.Random).
"""
import math
import random

TOL = 1e-9
NAN = float("nan")

APPLE = {"calories": 95, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47, "fibre": 4.4, "water": 156}
MEAT = {"calories": 100, "carbs": 0, "lipids": 5, "proteins": 20, "iron": 2}
TEMPLATES = {
    "Fruits": {"n": 3, "density": {"fibre": 0.04, "water": 1.5, "vitC": 0.1}},
    "_default": {"n": 9, "density": {"fibre": 0.01, "water": 0.5, "iron": 0.005}},
}
KIWI = {"foodType": "Fruits", "macros": {"calories": 50, "carbs": 12, "lipids": 0, "proteins": 1}}

STUB = r"""
function(seeds)
    return function(fullType)
        local s = seeds[fullType]
        if s == nil then return nil end
        local v = {}
        for k, x in pairs(s) do v[k] = x end
        return v
    end
end
"""

# The adapter's chained lookup (IN.chainedLookup), rebuilt in the test: the kernel takes the closure as an argument.
INPUTS = r"""
function(lookup, templates, infos, trace)
    local K = NutritionRevamp.kernel
    return function(fullType)
        local i = nil
        if infos ~= nil then i = infos[fullType] end
        local vec, step, note = K.intake.chainOne(fullType, lookup, templates, i)
        K.intake.traceStep(trace, fullType, step, note)
        return vec
    end
end
"""


def KI(h):
    return h.K.intake


def as_list(t):
    return list({k: v for k, v in t.items()}.values())


def macros(t):
    return [t["calories"], t["carbs"], t["lipids"], t["proteins"]]


def close(a, b, tol=1e-6):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def lookup(h, extra=None):
    seeds = {"Base.Apple": APPLE, "Base.MincedMeat": MEAT}
    seeds.update(extra or {})
    return h.rt.eval(STUB)(h.table(seeds))


def templates(h):
    return h.table(TEMPLATES)


def before(h, extra_types=(), craft=None, **kw):
    d = {"fullType": "Base.Apple", "rawBefore": -0.16, "instBase": -0.16, "scriptHunger": -0.16,
         "cal": 95, "carb": 25.13, "lip": 0.31, "pro": 0.47,
         "cooked": False, "burnt": False, "rotten": False, "frozen": False}
    d.update(kw)
    t = h.table(d)
    t["extraTypes"] = h.rt.table(*extra_types)
    if craft is not None:
        t["craftMap"] = h.table(craft)
    return t


def assemble(h, b, raw_after, thirst_after=None, tmpl=None, infos=None, seeds=None):
    trace = KI(h).newTrace()
    lk = lookup(h, seeds)
    inputs = h.rt.eval(INPUTS)(lk, tmpl, None if infos is None else h.table(infos), trace)
    out = KI(h).assemble(b, raw_after, lk, thirst_after, tmpl, inputs, trace)
    assert h.rt.eval("function(a, b) return rawequal(a, b) end")(out[5], trace)
    return out


# --- shareEaten -----------------------------------------------------------------------------------

def test_share_eaten_whole_half_none_and_zero_base(host):
    k = KI(host)
    assert abs(k.shareEaten(-0.16, 0, -0.16) - 1.0) < TOL
    assert abs(k.shareEaten(-0.16, -0.08, -0.16) - 0.5) < TOL
    assert abs(k.shareEaten(-0.16, -0.16, -0.16) - 0.0) < TOL
    assert k.shareEaten(-0.16, 0, 0) == 0


def test_share_eaten_clamps_to_zero_one(host):
    k = KI(host)
    assert abs(k.shareEaten(-0.32, 0, -0.16) - 1.0) < TOL
    assert abs(k.shareEaten(-0.08, -0.16, -0.16) - 0.0) < TOL


# --- fractionOf -----------------------------------------------------------------------------------

def test_fraction_thirst_only(host):
    k = KI(host)
    frac, share = k.fractionOf(0, 0, 0, -0.1, 0)
    assert abs(frac - 1.0) < TOL and abs(share - 1.0) < TOL
    frac, share = k.fractionOf(0, 0, 0, -0.1, -0.05)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL
    frac, share = k.fractionOf(0, 0, None, -0.1, -0.05)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_hunger_ignores_thirst(host):
    k = KI(host)
    frac, share = k.fractionOf(-0.08, 0, -0.16, -0.1, -0.1)
    assert abs(frac - 1.0) < TOL and abs(share - 0.5) < TOL
    frac, share = k.fractionOf(-0.16, -0.08, -0.16, None, None)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_nothing_readable_is_zero(host):
    frac, share = KI(host).fractionOf(0, 0, 0, 0, 0)
    assert frac == 0 and share == 0


def test_fraction_thirst_only_against_script_thirst(host):
    k = KI(host)
    frac, share = k.fractionOf(0, 0, 0, -0.1, -0.05, -0.1)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL
    frac, share = k.fractionOf(0, 0, 0, -0.05, 0, -0.1)       # all of what was LEFT, half of the WHOLE
    assert abs(frac - 1.0) < TOL and abs(share - 0.5) < TOL
    frac, share = k.fractionOf(0, 0, 0, -0.05, 0, 0)          # the whole unknown: share falls back to frac
    assert abs(frac - 1.0) < TOL and abs(share - 1.0) < TOL


def test_fraction_property_in_zero_one(host):
    k = KI(host)
    rng = random.Random(20261007)
    for _ in range(500):
        raw_before = rng.uniform(-1.0, 0.0)
        raw_after = rng.uniform(-1.2, 0.2)
        inst = rng.choice([None, 0, rng.uniform(-1.0, -0.001), rng.uniform(0.001, 1.0)])
        tb = rng.choice([None, 0, rng.uniform(-1.0, -1e-6), rng.uniform(1e-6, 1.0)])
        ta = rng.choice([None, rng.uniform(-1.2, 0.2)])
        st = rng.choice([None, 0, rng.uniform(-1.0, -1e-6), rng.uniform(1e-6, 1.0)])
        frac, share = k.fractionOf(raw_before, raw_after, inst, tb, ta, st)
        assert 0 <= frac <= 1 and 0 <= share <= 1, (raw_before, raw_after, inst, tb, ta, st, frac, share)


# --- macrosEaten ----------------------------------------------------------------------------------

def test_macros_whole_burnt_and_half(host):
    k = KI(host)
    assert close(macros(k.macrosEaten(95, 25.13, 0.31, 0.47, 1, False)), [95, 25.13, 0.31, 0.47])
    assert close(macros(k.macrosEaten(95, 25.13, 0.31, 0.47, 1, True)), [19, 5.026, 0.062, 0.094])
    assert close(macros(k.macrosEaten(95, 25.13, 0.31, 0.47, 0.5, False)), [47.5, 12.565, 0.155, 0.235])


def test_macros_property_non_negative_and_monotone_in_share(host):
    k = KI(host)
    rng = random.Random(4207)
    for _ in range(500):
        m = [rng.uniform(0, 2000), rng.uniform(0, 300), rng.uniform(0, 200), rng.uniform(0, 200)]
        burnt = rng.random() < 0.5
        s1, s2 = sorted((rng.random(), rng.random()))
        a = macros(k.macrosEaten(*m, s1, burnt))
        b = macros(k.macrosEaten(*m, s2, burnt))
        assert all(x >= 0 for x in a + b)
        assert all(x <= y + 1e-12 for x, y in zip(a, b)), (m, s1, s2, burnt)


# --- sourceOf, chainOne, the trace ----------------------------------------------------------------

def test_source_of(host):
    k = KI(host)
    assert k.sourceOf(True, False) == "dish"
    assert k.sourceOf(True, True) == "dish"
    assert k.sourceOf(False, True) == "craft"
    assert k.sourceOf(False, False) == "baseline"
    assert k.sourceOf(False, False, "declared") == "declared"
    assert k.sourceOf(False, False, "inferred") == "inferred"
    assert k.sourceOf(False, False, "table") == "baseline"
    assert k.sourceOf(False, False, "missing") == "baseline"
    assert k.sourceOf(True, False, "declared") == "dish"
    assert k.sourceOf(False, True, "inferred") == "craft"


def test_chain_one_declared_wins_and_takes_the_items_macros(host):
    h = host
    info = h.table({"declared": "fibre:12;vitC:3;calories:999",
                    "macros": {"calories": 95, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47}})
    vec, step, note = KI(h).chainOne("Base.Apple", lookup(h), templates(h), info)
    assert step == "declared"
    assert vec["fibre"] == 12 and vec["vitC"] == 3
    assert vec["calories"] == 95 and vec["carbs"] == 25.13
    assert vec["water"] == 0
    assert as_list(note) == []


def test_chain_one_malformed_table_inferred_missing(host):
    h = host
    vec, step, note = KI(h).chainOne("Base.Apple", lookup(h), templates(h),
                                     h.table({"declared": "fibre:lots", "macros": {"calories": 95}}))
    assert step == "table" and abs(vec["fibre"] - 4.4) < TOL
    assert isinstance(note, str) and "fibre:lots" in note
    vec, step, note = KI(h).chainOne("Base.Apple", lookup(h), templates(h),
                                     h.table({"foodType": "Fruits", "macros": {"calories": 95}}))
    assert step == "table" and note is None
    vec, step, note = KI(h).chainOne("Base.Kiwi", lookup(h), templates(h), h.table(KIWI))
    assert step == "inferred"
    assert abs(vec["fibre"] - 2.0) < TOL and abs(vec["vitC"] - 5.0) < TOL
    for info in (None, h.table({"foodType": "Fruits", "macros": {"calories": 0}}), h.table({"foodType": "Fruits"})):
        vec, step, note = KI(h).chainOne("Base.Kiwi", lookup(h), templates(h), info)
        assert vec is None and step == "missing"
    vec, step, note = KI(h).chainOne("Base.Kiwi", lookup(h), None, h.table(KIWI))
    assert vec is None and step == "missing"


def test_trace_step_records_every_kind(host):
    h = host
    k = KI(h)
    trace = k.newTrace()
    k.traceStep(trace, "A.Dec", "declared", None)
    k.traceStep(trace, "A.Inf", "inferred", None)
    k.traceStep(trace, "A.Bad", "table", "not a pair: x")
    k.traceStep(trace, "A.Unk", "declared", h.rt.table("vitZ", "vitY"))
    k.traceStep(trace, "A.Tab", "table", None)
    assert as_list(trace["declared"]) == ["A.Dec", "A.Unk"]
    assert as_list(trace["inferred"]) == ["A.Inf"]
    assert as_list(trace["malformed"]) == ["A.Bad: not a pair: x"]
    assert as_list(trace["unknown"]) == ["A.Unk: vitZ", "A.Unk: vitY"]


# --- assemble (ported from test_intake_shape.py) ---------------------------------------------------

def test_assemble_baseline_half_apple(host):
    h = host
    vec, source, missing, share, frac, _ = assemble(h, before(h), -0.08)
    assert abs(share - 0.5) < TOL and abs(frac - 0.5) < TOL
    assert source == "baseline"
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL and abs(vec["water"] - 78) < TOL
    assert as_list(missing) == []


def test_assemble_baseline_instance_scale(host):
    h = host
    b = before(h, rawBefore=-0.08, instBase=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    assert source == "baseline"
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_burnt_macros_divided_by_five(host):
    h = host
    vec, *_ = assemble(h, before(h, burnt=True), 0)
    assert close(macros(vec), [19, 5.026, 0.062, 0.094])


def test_assemble_craft_map(host):
    h = host
    b = before(h, craft={"Base.MincedMeat": 2}, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2,
               scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    assert source == "craft"
    assert close(macros(vec), [200, 0, 10, 40])
    assert abs(vec["iron"] - 4) < TOL
    b = before(h, craft={"Base.MincedMeat": 0}, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2,
               scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    vec, source, *_ = assemble(h, b, 0)
    assert source == "craft" and vec["iron"] == 0


def test_assemble_dish_wins_and_records_missing(host):
    h = host
    b = before(h, extra_types=("Base.Apple", "Base.Apple", "Base.Unknown"), craft={"Base.MincedMeat": 2},
               fullType="Base.Salad", rawBefore=-0.3, instBase=-0.3, scriptHunger=-0.3, cal=190, carb=50.26,
               lip=0.62, pro=0.94)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    assert source == "dish"
    assert abs(vec["fibre"] - 8.8) < TOL
    assert as_list(missing) == ["Base.Unknown"]


def test_assemble_unknown_baseline_is_missing(host):
    h = host
    vec, source, missing, *_ = assemble(h, before(h, fullType="Base.Nothing"), 0)
    assert source == "baseline"
    assert as_list(missing) == ["Base.Nothing"]
    assert vec["fibre"] == 0 and abs(vec["calories"] - 95) < TOL


def test_assemble_second_half_of_a_part_eaten_apple(host):
    h = host
    b = before(h, rawBefore=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    assert abs(share - 0.5) < TOL and abs(frac - 1.0) < TOL
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_nothing_eaten_or_nan_lands_nothing(host):
    h = host
    vec, source, missing, share, frac, trace = assemble(h, before(h), -0.16)
    assert vec is None and source is None and share == 0 and as_list(missing) == []
    vec, *_ = assemble(h, before(h), NAN)
    assert vec is None


def test_assemble_thirst_only(host):
    h = host
    b = before(h, fullType="Base.Nothing", rawBefore=0, instBase=0, scriptHunger=0, cal=2, carb=0, lip=0, pro=0,
               thirstBefore=-0.1)
    vec, source, missing, share, frac, _ = assemble(h, b, 0, 0)
    assert abs(share - 1.0) < TOL and abs(frac - 1.0) < TOL and abs(vec["calories"] - 2) < TOL
    vec, source, missing, share, frac, _ = assemble(h, b, 0, -0.05)
    assert abs(share - 0.5) < TOL and abs(vec["calories"] - 1) < TOL


def test_assemble_thirst_only_two_eats_land_the_baseline_once(host):
    h = host
    # Plan 11 Task 6: the vector follows the calories Eat delivered, so the instance carries the table's 95 kcal
    b1 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=95, carb=0, lip=0, pro=0, thirstBefore=-0.1,
                scriptThirst=-0.1)
    v1, _, _, share1, frac1, _ = assemble(h, b1, 0, -0.05)
    b2 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=47.5, carb=0, lip=0, pro=0, thirstBefore=-0.05,
                scriptThirst=-0.1)
    v2, _, _, share2, frac2, _ = assemble(h, b2, 0, 0)
    assert abs(share1 - 0.5) < TOL and abs(frac1 - 0.5) < TOL
    assert abs(share2 - 0.5) < TOL and abs(frac2 - 1.0) < TOL
    assert abs(v1["fibre"] + v2["fibre"] - 4.4) < TOL
    assert abs(v1["water"] + v2["water"] - 156) < TOL
    assert abs(v1["calories"] - 47.5) < TOL and abs(v2["calories"] - 47.5) < TOL


def test_assemble_declared_item_wins_over_the_table(host):
    h = host
    b = before(h, declared="fibre:12;vitC:3")
    vec, source, missing, share, frac, trace = assemble(h, b, -0.08, None, templates(h))
    assert source == "declared"
    assert abs(vec["fibre"] - 6.0) < TOL and abs(vec["vitC"] - 1.5) < TOL
    assert vec["water"] == 0
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert as_list(trace["declared"]) == ["Base.Apple"]


def test_assemble_table_hit_wins_over_inference(host):
    h = host
    vec, source, missing, share, frac, trace = assemble(h, before(h, foodType="Fruits"), -0.08, None, templates(h))
    assert source == "baseline" and abs(vec["fibre"] - 2.2) < TOL
    assert as_list(trace["inferred"]) == []


def test_assemble_untabled_item_infers(host):
    h = host
    b = before(h, fullType="Base.Kiwi", foodType="Fruits", cal=50, carb=12, lip=0.4, pro=1)
    vec, source, missing, share, frac, trace = assemble(h, b, -0.08, None, templates(h))
    assert source == "inferred" and abs(frac - 0.5) < TOL
    assert abs(vec["fibre"] - 0.04 * 50 * 0.5) < TOL and abs(vec["vitC"] - 0.1 * 50 * 0.5) < TOL
    assert close(macros(vec), [25, 6, 0.2, 0.5])
    assert as_list(missing) == [] and as_list(trace["inferred"]) == ["Base.Kiwi"]


def test_assemble_untabled_without_templates_is_missing(host):
    h = host
    vec, source, missing, *_ = assemble(h, before(h, fullType="Base.Kiwi", foodType="Fruits"), 0)
    assert source == "baseline" and as_list(missing) == ["Base.Kiwi"] and vec["fibre"] == 0


def test_assemble_malformed_declared_falls_through_and_is_traced(host):
    h = host
    vec, source, missing, share, frac, trace = assemble(h, before(h, declared="fibre=12"), -0.08, None, templates(h))
    assert source == "baseline" and abs(vec["fibre"] - 2.2) < TOL
    bad = as_list(trace["malformed"])
    assert len(bad) == 1 and bad[0].startswith("Base.Apple: ")


def test_assemble_craft_inputs_through_the_chain(host):
    h = host
    patty = dict(fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0,
                 lip=10, pro=40)
    b = before(h, craft={"Base.MincedMeat": 1, "Base.Kiwi": 2}, **patty)
    vec, source, missing, share, frac, trace = assemble(h, b, 0, None, templates(h), {"Base.Kiwi": KIWI})
    assert source == "craft" and abs(vec["iron"] - 2) < TOL and abs(vec["fibre"] - 2 * 0.04 * 50) < TOL
    assert as_list(missing) == [] and as_list(trace["inferred"]) == ["Base.Kiwi"]
    assert close(macros(vec), [200, 0, 10, 40])
    b = before(h, craft={"Base.MincedMeat": 1}, **patty)
    vec, source, missing, share, frac, trace = assemble(
        h, b, 0, None, templates(h), {"Base.MincedMeat": {"declared": "iron:7", "macros": {"calories": 200}}})
    assert abs(vec["iron"] - 7) < TOL and as_list(trace["declared"]) == ["Base.MincedMeat"]
    b = before(h, craft={"Base.Nothing": 1}, **patty)
    vec, source, missing, *_ = assemble(h, b, 0, None, templates(h), {})
    assert as_list(missing) == ["Base.Nothing"]


def test_assemble_dish_ingredient_goes_through_the_chain(host):
    h = host
    b = before(h, extra_types=("Base.Apple", "Base.Kiwi"), fullType="Base.Salad", rawBefore=-0.3, instBase=-0.3,
               scriptHunger=-0.3, cal=145, carb=37.13, lip=0.31, pro=1.47)
    vec, source, missing, share, frac, trace = assemble(h, b, 0, None, templates(h), {"Base.Kiwi": KIWI})
    assert source == "dish" and abs(vec["fibre"] - 6.4) < 1e-6
    assert as_list(missing) == [] and as_list(trace["inferred"]) == ["Base.Kiwi"]


# --- the factor pins: each source's factor on inputs where frac != share ---------------------------
# rawBefore -0.08 of a -0.16 instance, eaten to 0: frac (of what was LEFT) 1.0, share (of the WHOLE) 0.5.

def _frac_share(share, frac):
    assert abs(frac - 1.0) < TOL and abs(share - 0.5) < TOL


def test_factor_table_takes_share(host):
    h = host
    b = before(h, rawBefore=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235)
    vec, source, missing, share, frac, _ = assemble(h, b, 0, None, templates(h))
    _frac_share(share, frac)
    assert source == "baseline"
    assert abs(vec["fibre"] - 4.4 * 0.5) < TOL                   # x share; x frac would land 4.4


def test_factor_declared_takes_share(host):
    h = host
    b = before(h, rawBefore=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235, declared="fibre:12")
    vec, source, missing, share, frac, _ = assemble(h, b, 0, None, templates(h))
    _frac_share(share, frac)
    assert source == "declared"
    assert abs(vec["fibre"] - 12 * 0.5) < TOL


def test_factor_inferred_takes_frac_and_no_instance_scale(host):
    # the second bite of an untabled item whose instance is scaled off its script (instBase/scriptHunger 0.5):
    # the live macros already carry both the bite and the scale, so the inferred vector takes frac (1.0)
    # and no instance scale. Swapping its factor to share lands half of this.
    h = host
    b = before(h, fullType="Base.Kiwi", foodType="Fruits", rawBefore=-0.08, instBase=-0.16, scriptHunger=-0.32,
               cal=25, carb=6, lip=0.2, pro=0.5)
    vec, source, missing, share, frac, _ = assemble(h, b, 0, None, templates(h))
    _frac_share(share, frac)
    assert source == "inferred"
    assert abs(vec["fibre"] - 0.04 * 25 * 1.0) < TOL
    assert abs(vec["vitC"] - 0.1 * 25 * 1.0) < TOL
    assert close(macros(vec), [25, 6, 0.2, 0.5])


def test_factor_craft_takes_share(host):
    h = host
    b = before(h, craft={"Base.MincedMeat": 2}, fullType="Base.MeatPatty", rawBefore=-0.1, instBase=-0.2,
               scriptHunger=-0.2, cal=100, carb=0, lip=5, pro=20)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    _frac_share(share, frac)
    assert source == "craft"
    assert abs(vec["iron"] - 2 * 2 * 0.5) < TOL                   # two minced meats x share
    assert close(macros(vec), [100, 0, 5, 20])                   # the macros x frac


def test_factor_dish_takes_frac(host):
    h = host
    b = before(h, extra_types=("Base.Apple", "Base.Apple"), fullType="Base.Salad", rawBefore=-0.15, instBase=-0.3,
               scriptHunger=-0.3, cal=190, carb=50.26, lip=0.62, pro=0.94)
    vec, source, missing, share, frac, _ = assemble(h, b, 0)
    _frac_share(share, frac)
    assert source == "dish"
    assert abs(vec["fibre"] - 8.8 * 1.0) < 1e-6                  # x frac; x share would land 4.4


def test_factor_thirst_only_share_uses_script_thirst(host):
    h = host
    b = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=47.5, carb=0, lip=0, pro=0, thirstBefore=-0.05,
               scriptThirst=-0.1)
    vec, source, missing, share, frac, _ = assemble(h, b, 0, 0)
    _frac_share(share, frac)
    assert abs(vec["fibre"] - 4.4 * 0.5) < TOL                   # the delivered 47.5 of the table's 95 kcal
    assert abs(vec["calories"] - 47.5) < TOL
    b["scriptThirst"] = 0                                        # unknown: share falls back to frac
    vec, source, missing, share, frac, _ = assemble(h, b, 0, 0)
    # Plan 11 Task 6: the vector follows the delivered calories, so the fallback share no longer over-counts
    assert abs(share - 1.0) < TOL and abs(vec["fibre"] - 4.4 * 0.5) < TOL
    b["cal"] = 0                                                 # no calories: the hunger ratio (1) with share
    vec, source, missing, share, frac, _ = assemble(h, b, 0, 0)
    assert abs(share - 1.0) < TOL and abs(vec["fibre"] - 4.4) < TOL


# --- Plan 11 Task 6: the micronutrients follow the calories Eat delivered (Appendix E) ----------------------------

FISH = {"calories": 100, "carbs": 0, "lipids": 2, "proteins": 20, "iron": 2}
TEA = {"calories": 40, "carbs": 10, "lipids": 0, "proteins": 0, "iron": 1}
BREAD = {"calories": 150, "carbs": 30, "lipids": 2, "proteins": 5, "iron": 3}
CHEESE = {"calories": 150, "carbs": 1, "lipids": 12, "proteins": 9, "iron": 3}


def test_a_caught_fish_lands_iron_with_its_delivered_calories(host):
    # #3328: the catch sets 11x the script's calories and instBase -1.0 over the script's -0.15 (x6.67)
    b = before(host, fullType="Base.Fish", rawBefore=-1.0, instBase=-1.0, scriptHunger=-0.15,
               cal=1100, carb=0, lip=22, pro=220)
    vec = assemble(host, b, 0, seeds={"Base.Fish": FISH})[0]
    assert abs(vec["calories"] - 1100) < 1e-9 and abs(vec["iron"] - 22) < 1e-9


def test_a_fish_fillet_lands_iron_with_its_delivered_calories(host):
    b = before(host, fullType="Base.Fish", rawBefore=-0.5, instBase=-0.5, scriptHunger=-0.15,
               cal=550, carb=0, lip=11, pro=110)
    vec = assemble(host, b, 0, seeds={"Base.Fish": FISH})[0]
    assert abs(vec["calories"] - 550) < 1e-9 and abs(vec["iron"] - 11) < 1e-9


def test_a_thirst_only_food_lands_iron_with_its_delivered_calories(host):
    b = before(host, fullType="Base.Tea", rawBefore=0, instBase=0, scriptHunger=0, cal=60, carb=15, lip=0, pro=0,
               thirstBefore=-0.2, scriptThirst=-0.2)
    vec = assemble(host, b, 0, thirst_after=-0.1, seeds={"Base.Tea": TEA})[0]
    assert abs(vec["calories"] - 30) < 1e-9 and abs(vec["iron"] - 0.75) < 1e-9


def test_a_hand_craft_output_lands_its_inputs_vector_at_its_own_calories(host):
    # Appendix E's MakeHotDog case: the summed inputs carry 300 kcal; the output delivers 150
    b = before(host, fullType="Base.Sandwich", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2,
               cal=150, carb=31, lip=14, pro=14, craft={"Base.Bread": 1, "Base.Cheese": 1})
    vec = assemble(host, b, 0, seeds={"Base.Bread": BREAD, "Base.Cheese": CHEESE})[0]
    assert abs(vec["calories"] - 150) < 1e-9 and abs(vec["iron"] - 3.0) < 1e-9
