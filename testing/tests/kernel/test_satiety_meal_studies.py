"""The satiety oracle (Plan 11c Task 4; spec § 5b and § 6; ruling 11c-30): published protocols replayed through the
real kernels -- the stomach's two lanes (K.stomach), the meal satiety pool (K.satiety) and the hunger function
(K.hybrid.hungerTarget) -- one step a game minute. Each step runs, in order: the minute's eats feed P with their
weighted kcal (K.satiety.feed, once per eat) and land in the stomach; the stomach drains; P decays; F is read from the
satiety mass (K.stomach.satietyMass) against K.stomach.CAPACITY_MAX_G (ruling 11c-19); and the displayed hunger is
min(0.69, hungerTarget(sated(F, post(P)), 1) x circadian(h)). Trait 1 and StatsDecrease 1 (ruling 11c-23).

The protocol (spike 2, task-4s2-report.md):
- The meal request is displayed HUNGER 0.25, vanilla's HUNGRY level 2 (ruling 11c-17, a game choice).
- A replay starts at the request with an empty stomach, P = seedP(0.25 / circadian(h0), 0, 1), or fasted (P = 0),
  where a test says so. Its endpoint is the first minute displayed HUNGER is back at 0.25 (a fasted start: after it
  first fell below), compared like with like against a study's time to a meal request.
- The circadian factor runs at each study's clock time: Callahan 2004 at 09:00 (S1247's row); a study that states no
  time (Cummings 2004, Rolls 1999, Rolls 1998, Marmonier 2000, Melanson 1999, Marciani 2012) is replayed with the
  factor held at 1, its 13:50 value.
- The intake mapping (labelled inference, ruling 11c-30): intake at a meal = 650 kcal x displayed hunger at the meal's
  start / 0.25, the spec's typical meal eaten at the request level (10,878 kJ x hunger). Rolls 1999's arms are replayed
  as intakes under it. S1233 is read under its relative form: lunch over the no-preload lunch = hunger at the lunch over the replayed
  no-preload hunger at the same minute.

The tolerance (ruling 11c-30): the hard replays land within 1.1x of the study's figure; S1233 is a check at 1.15x.

What the model does not reproduce, named and pinned so that a change is noticed:
- S1224's absolute snack delays (Marmonier 2000: 60 / 34 / 25 min; the model about 200 / 165 / 173 min). No additive
  pool meets both S1224 and S1247 (spike 1). Their differences are read, see the protein weight below.
- S1222's VAS level (the protein contrast, 0.0027 against about 0.025), see the protein weight below.
- S1228's fasted 1 MJ drinks (Melanson 1999: 65 / 126 min; the model about 236 min for both).
- S1272's 1692 g meal (Moore 1981: 277 min solid half-emptying; the model 189 min for an assumed 1500 kcal).
- Viscous fibre's own effect (ruling 11c-6): fibre counts only through mass.

The protein weight (ruling 11c-31): W_PROTEIN stays 2.5 under structure D, and it is bounded by S1224's delay
differences, no longer exempt from the mutation bar. Marmonier 2000's three snacks, read as differences (protein
over carbohydrate 26 min, protein over fat 35 min), are replayed and each model difference sits within 1.5x
(35 and 27 min); W_PROTEIN at x2 and x0.5 each fail it. The absolute delays stay a named non-reproduction. S1222
(Kohanmoo 2020: hunger -7 mm, fullness +10 mm) and S1223 (Dhillon 2016: fullness AUC +2,436 mm.240 min) give no
per-trial protein-energy contrast, preload size or timing, so S1222's VAS level is a pinned named non-reproduction:
under a request-anchored mapping (a pre-meal VAS of about 65 mm read as 0.25, a LABELLED ASSUMPTION since no row
gives a pre-meal VAS; the 1 mm = 0.01 HUNGER mapping is retired) -7 mm is about 0.025 of HUNGER, and the model's
protein contrast is 0.0027, about 10x short. The cause: the near-logarithmic read, and displayed hunger never
falling below about 0.12.

Accepted only after the mutation pass (CLAUDE.md § 6): each of HALF_LIFE_H, P_REQ, STEEP, FULL_WEIGHT,
LIQUID_WEIGHT and W_PROTEIN at x2 and x0.5 fails a hard replay (W_PROTEIN: the Marmonier difference check), and the
09:00 circadian factor dropped fails the Callahan minutes. Every test takes only `host`, so the mutation script calls each one
on a patched host; no test uses `parametrize`.
"""
import math

H_REQ = 0.25                    # the meal request: vanilla's HUNGRY level 2 (ruling 11c-17, a game choice)
TOL = 1.1                       # the hard replays' tolerance (ruling 11c-30)
CHECK_TOL = 1.15                # S1233's check (ruling 11c-30)
KJ_PER_HUNGER = 650.0 * 4.184 / H_REQ   # the intake mapping (labelled inference): 10,878.4 kJ x displayed hunger
CALLAHAN_H = 9.0                # S1247: preloads at 0900 h

# The replay runs with the coverage line hook off (every kernel line it runs is covered by the kernels' own tests).
REPLAY = r"""
function(events, minutes, P0, h0)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local st = K.stomach.new()
    local P = P0
    local hs = {}
    local ms = {}
    local bs = {}
    for m = 0, minutes - 1 do
        local list = events[m]
        if list ~= nil then
            for i = 1, #list do
                local e = list[i]
                local v = K.vector.new()
                for k, x in pairs(e.vec) do
                    v[k] = x
                end
                P = K.satiety.feed(P, v)
                if e.kind == "drink" then
                    K.stomach.ingestLiquid(st, v)
                else
                    K.stomach.ingest(st, v)
                end
            end
        end
        K.stomach.drain(st, 1 / 60)
        P = K.satiety.decay(P, 1 / 60, K.satiety.HALF_LIFE_H, 1)
        local F = K.satiety.fill(K.stomach.satietyMass(st), K.stomach.CAPACITY_MAX_G)
        local c = 1
        if h0 ~= nil then
            c = K.satiety.circadian((h0 + (m + 1) / 60) % 24)
        end
        hs[m + 1] = K.min(0.69, K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(P)), 1) * c)
        ms[m + 1] = K.stomach.mass(st)
        bs[m + 1] = K.stomach.massOf(st.buffer)
    end
    debug.sethook(hook, mask)
    return hs, ms, bs
end
"""


# --- the meals (grams; Atwater 4/4/9 for the macronutrient shares) ------------------------------------------------

def mixed(kcal, water=300.0, fibre=6.0, p=0.15, c=0.50, f=0.35):
    """A mixed meal: 15 % protein, 50 % carbohydrate, 35 % fat by energy (an illustrative meal, a game choice)."""
    return {"calories": kcal, "proteins": kcal * p / 4, "carbs": kcal * c / 4, "lipids": kcal * f / 9,
            "water": water, "fibre": fibre}


def snack(kcal, main, share, water=150.0):
    """A preload whose main macronutrient carries `share` of its energy and the other two split the rest."""
    s = {"proteins": (1 - share) / 2, "carbs": (1 - share) / 2, "lipids": (1 - share) / 2}
    s[main] = share
    return {"calories": kcal, "proteins": kcal * s["proteins"] / 4, "carbs": kcal * s["carbs"] / 4,
            "lipids": kcal * s["lipids"] / 9, "water": water}


def preload(kcal, water=400.0):
    """A liquid preload of fixed volume (S1247's preloads were equal in volume): 50/20/30 carbohydrate/protein/fat. ASSUMED (no row gives the preload's macros or mass)."""
    return {"calories": kcal, "carbs": kcal * 0.5 / 4, "proteins": kcal * 0.2 / 4, "lipids": kcal * 0.3 / 9,
            "water": water}


def dense(kcal, kcal_per_g):
    """A mixed meal at an energy density: water fills its mass (fibre 6 g per 650 kcal)."""
    v = mixed(kcal, water=0.0, fibre=6.0 * kcal / 650)
    dry = v["proteins"] + v["carbs"] + v["lipids"] + v["fibre"]
    v["water"] = max(0.0, kcal / kcal_per_g - dry)
    return v


def milk(ml):
    """S1233's drinks: 2088 kJ (499 kcal), 30.3 % fat, 54.7 % carbohydrate, 15 % protein by energy, water the rest."""
    k = 499.0
    v = {"calories": k, "proteins": k * 0.15 / 4, "carbs": k * 0.547 / 4, "lipids": k * 0.303 / 9}
    v["water"] = ml - (v["proteins"] + v["carbs"] + v["lipids"])
    return v


CASSEROLE = {"calories": 270.0, "proteins": 20.0, "carbs": 25.0, "lipids": 10.0, "water": 200.0, "fibre": 4.0}  # ASSUMED (S1231 gives only 1128 kJ and the 356 g of water)
SOUP = dict(CASSEROLE, water=CASSEROLE["water"] + 356.0)     # S1231: the same casserole with its 356 g of water in it
WATER = {"water": 356.0}                                      # S1231: the same water drunk alongside
# S1232 (Marciani 2012): 1008 kJ (241 kcal) chicken and vegetables with water; the water's amount is not in the row,
# ASSUMED 300 g drunk beside a solid part holding 200 g; the soup is the same blended
MARC_SOLID = mixed(241.0, water=200.0, fibre=4.0, p=0.30, c=0.40, f=0.30)
MARC_SOUP = dict(MARC_SOLID, water=500.0)
MARC_WATER = {"water": 300.0}


def mass_of(vec):
    return sum(vec.get(k, 0.0) for k in ("water", "proteins", "carbs", "lipids", "fibre"))


# --- the replay ---------------------------------------------------------------------------------------------------

def lua_events(host, events):
    t = host.rt.table()
    for minute, items in events.items():
        lst = host.rt.table()
        for i, (kind, vec) in enumerate(items, 1):
            lst[i] = host.table({"kind": kind, "vec": vec})
        t[minute] = lst
    return t


def start_p(host, h0=None):
    """The pool at the request with an empty stomach: displayed hunger 0.25 at the start's clock."""
    c = 1.0 if h0 is None else host.call("satiety.circadian", h0 % 24)
    return host.call("satiety.seedP", H_REQ / c, 0, 1)


def replay(host, events, minutes, P0=None, h0=None):
    """Displayed hunger, stomach mass and solid-lane mass per minute (index i is minute i + 1)."""
    if P0 is None:
        P0 = start_p(host, h0)
    hs, ms, bs = host.rt.eval(REPLAY)(lua_events(host, events), minutes, P0, h0)
    r = range(1, minutes + 1)
    return [hs[i] for i in r], [ms[i] for i in r], [bs[i] for i in r]


def hunger(host, events, minutes, P0=None, h0=None):
    return replay(host, events, minutes, P0, h0)[0]


def request(hs, after=5, fasted=False):
    """The minute (1-based) displayed hunger is back at the request after `after`; fasted: after it first fell below.
    None if never."""
    start = after
    if fasted:
        below = [i for i, x in enumerate(hs) if x < H_REQ - 1e-12]
        if not below:
            return None
        start = max(after, below[0])
    for i, x in enumerate(hs):
        if i > start and x >= H_REQ - 1e-12:
            return i + 1
    return None


def held(hs):
    """(first minute below the request, minutes held below it, lowest hunger)."""
    below = [i for i, x in enumerate(hs) if x < H_REQ]
    if not below:
        return None, 0, min(hs)
    first = below[0]
    back = next((i for i in range(first, len(hs)) if hs[i] >= H_REQ), len(hs) + 10000)
    return first + 1, back - first, min(hs)


def ratio(model, study):
    """The worse-way ratio, >= 1; infinite for a missing or non-positive reading."""
    if model is None or model <= 0:
        return math.inf
    return max(model / study, study / model)


# --- the readings, shared by the tests and the mutation script ------------------------------------------------------

def callahan(host, fasted=False, h0=CALLAHAN_H):
    """S1247: 7.5, 16 and 33 % of daily energy as equal-volume liquid preloads at 09:00 (a 2,500 kcal day, a game
    choice): 190, 400 and 825 kcal. h0 None holds the circadian factor at 1."""
    out = []
    for k in (190.0, 400.0, 825.0):
        hs = hunger(host, {0: [("drink", preload(k))]}, 900, P0=0.0 if fasted else None, h0=h0)
        out.append(request(hs, fasted=fasted))
    return out


def rolls_1999(host):
    """S1231: the 1128 kJ preloads 17 min before lunch, as lunch intakes in kJ under the intake mapping."""
    arms = {"soup": [("food", SOUP)], "cw": [("food", CASSEROLE), ("drink", WATER)], "cas": [("food", CASSEROLE)]}
    return {n: KJ_PER_HUNGER * hunger(host, {0: ev}, 17)[16] for n, ev in arms.items()}


def rolls_1998(host):
    """S1233: 499 kcal milk drinks of 300 / 450 / 600 mL, lunch 30 min on, as lunch over the no-preload lunch (the
    hunger at minute 30 over the replayed no-preload hunger at minute 30, about 0.2575)."""
    control = hunger(host, {}, 30)[29]
    return [hunger(host, {0: [("drink", milk(ml))]}, 30)[29] / control for ml in (300.0, 450.0, 600.0)]


def marmonier(host):
    """S1224: a 239 kcal (1 MJ) snack 240 min after the start of a 650 kcal lunch; the dinner request's delay."""
    base = request(hunger(host, {0: [("food", mixed(650))]}, 1500))
    out = {"base": base}
    for name, main, share in (("p", "proteins", 0.77), ("c", "carbs", 0.84), ("f", "lipids", 0.58)):
        hs = hunger(host, {0: [("food", mixed(650))], 240: [("food", snack(239.0, main, share))]}, 1500)
        t = request(hs, after=245)
        out[name] = None if t is None or base is None else t - base
    return out


def marmonier_differences(host):
    """S1224 read as differences: (protein over carbohydrate, protein over fat) delay in min; the study's 26 and 35."""
    d = marmonier(host)
    return d["p"] - d["c"], d["p"] - d["f"]


def melanson(host):
    """S1228: 1 MJ isovolumetric drinks at the first request after an overnight fast (P = 0), 70 % of energy from the
    main macronutrient (an assumed share), carbohydrate and fat."""
    out = []
    for main in ("carbs", "lipids"):
        hs = hunger(host, {0: [("drink", snack(239.0, main, 0.70, water=400.0))]}, 900, P0=0.0)
        out.append(request(hs, fasted=True))
    return out


def moore_half_emptying(host):
    """S1272: the self-selected filling meal (mean 1692 g; its energy is not in the row, ASSUMED 1500 kcal mixed with
    water to the mass): the minute the solid lane holds half its mass."""
    v = mixed(1500.0, water=0.0, fibre=12.0)
    v["water"] = 1692.0 - mass_of(v)
    _, _, bs = replay(host, {0: [("food", v)]}, 900, P0=0.0)
    return next((i + 1 for i, b in enumerate(bs) if b <= 1692.0 / 2), None)


def hard_ratios(host):
    """Every hard replay's ratio (model against study, the worse way), for the tests and the mutation script."""
    r = {}
    for i, (t, s) in enumerate(zip(callahan(host), (247.0, 286.0, 321.0))):
        r["callahan%d" % i] = ratio(t, s)
    for i, (t, s) in enumerate(zip(callahan(host, fasted=True), (247.0, 286.0, 321.0))):
        r["callahan_fasted%d" % i] = ratio(t, s)
    t = request(hunger(host, {0: [("food", mixed(650))]}, 900))
    r["meal650"] = math.inf if t is None else (240.0 / t if t < 240 else (t / 300.0 if t > 300 else 1.0))
    ro = rolls_1999(host)
    r["rolls_soup"] = ratio(ro["soup"], 1209.0)
    r["rolls_cw"] = ratio(ro["cw"], 1657.0)
    r["rolls_cas"] = ratio(ro["cas"], 1639.0)
    r["rolls_drop"] = ratio(ro["cw"] - ro["soup"], 1657.0 - 1209.0)
    pc, pf = marmonier_differences(host)
    r["marmonier_pc"] = ratio(pc, 26.0)
    r["marmonier_pf"] = ratio(pf, 35.0)
    return r


# --- time to returning hunger (S1247, S1248) -------------------------------------------------------------------------

def test_callahans_preloads_from_the_request(host):
    # S1247 (Callahan 2004): 247 +/- 24, 286 +/- 20 and 321 +/- 27 min to the meal request, preloads at 09:00
    ts = callahan(host)
    for t, s in zip(ts, (247.0, 286.0, 321.0)):
        assert ratio(t, s) <= TOL, ts


def test_callahans_preloads_from_a_fasted_start(host):
    # S1247 from an empty pool (P = 0): the preload first brings hunger below the request, then it returns
    ts = callahan(host, fasted=True)
    for t, s in zip(ts, (247.0, 286.0, 321.0)):
        assert ratio(t, s) <= TOL, ts


def test_callahans_replay_minutes_are_pinned_and_the_09_00_factor_matters(host):
    # S1247's replay minutes (the study's 247 / 286 / 321): 244, 276, 321 from the request; 243, 276, 321 fasted; the
    # 09:00 factor matters, and dropping it fails the replays
    assert callahan(host) == [244, 276, 321]
    assert callahan(host, fasted=True) == [243, 276, 321]
    # the factor held at 1 (a different seed too) moves the minutes: the 190 kcal request comes earlier without it
    assert callahan(host, h0=None) == [227, 272, 330]
    assert callahan(host)[0] > callahan(host, h0=None)[0]
    assert callahan(host, fasted=True, h0=None) != callahan(host, fasted=True)


def test_a_650_kcal_mixed_meal_holds_hunger_off_for_four_to_five_hours(host):
    # the spec's anchor 240-300 min (S1247: 247-321), within 1.1x, and inside Cummings' outer 425 (S1248: 320-425)
    t = request(hunger(host, {0: [("food", mixed(650))]}, 900))
    assert t is not None and 240 / TOL <= t <= 300 * TOL and t <= 425, t


def test_a_fasted_400_kcal_breakfast_holds_hunger_below_the_request_for_three_hours(host):
    # the brief's anchor: from an empty pool, a 400 kcal breakfast brings hunger below the request and holds it there
    # at least 180 min, with the factor at 1 and at 08:00
    for h0 in (None, 8.0):
        first, dur, _ = held(hunger(host, {0: [("food", mixed(400, water=250.0))]}, 900, P0=0.0, h0=h0))
        assert first is not None and dur >= 180, (h0, first, dur)


def test_one_meal_or_three_items_of_the_same_total_give_the_same_interval(host):
    # partition invariance: P is fed per eat and the stomach sums, so splitting a meal moves nothing
    one = request(hunger(host, {0: [("food", mixed(650))]}, 900))
    third = mixed(650 / 3, water=100.0, fibre=2.0)
    same = request(hunger(host, {0: [("food", third), ("food", third), ("food", third)]}, 900))
    spread = request(hunger(host, {0: [("food", third)], 1: [("food", third)], 2: [("food", third)]}, 900))
    assert one == same, (one, same)
    assert abs(spread - one) <= 2, (one, spread)


# --- volume: water in the food against water drunk alongside (S1231, S1233, S1232, S1235) ----------------------------

def test_rolls_1999_soup_casserole_with_water_and_casserole_alone(host):
    # S1231 (Rolls 1999): lunch 1209 +/- 125 kJ after the soup, 1657 +/- 148 after the casserole with its water drunk,
    # 1639 +/- 148 after the casserole alone; under the intake mapping (labelled inference), each within 1.1x, and the
    # soup's drop of 448 kJ within 1.1x
    ro = rolls_1999(host)
    assert ratio(ro["soup"], 1209.0) <= TOL, ro
    assert ratio(ro["cw"], 1657.0) <= TOL, ro
    assert ratio(ro["cas"], 1639.0) <= TOL, ro
    assert ratio(ro["cw"] - ro["soup"], 448.0) <= TOL, ro


def test_rolls_1998_milk_volume_check(host):
    # S1233 (Rolls 1998), a check at 1.15x: lunch including the preload 5263 / 5011 / 4703 kJ against 4323 kJ with no
    # preload; less the drink's 2088 kJ, lunch over the no-preload lunch is 0.734 / 0.676 / 0.605; the model's
    # control is the replayed no-preload hunger (about 0.2575), the ratios about 1.084 / 1.019 / 1.075
    study = [(5263.0 - 2088.0) / 4323.0, (5011.0 - 2088.0) / 4323.0, (4703.0 - 2088.0) / 4323.0]
    model = rolls_1998(host)
    for m, s in zip(model, study):
        assert ratio(m, s) <= CHECK_TOL, (model, study)
    assert model[0] > model[1] > model[2], model         # a larger drink, a smaller lunch


def test_soup_sates_more_than_the_same_meal_with_its_water_drunk_over_three_hours(host):
    # S1232 (Marciani 2012), direction: the soup reduced hunger over 3 h
    hs = hunger(host, {0: [("food", MARC_SOUP)]}, 180)
    hl = hunger(host, {0: [("food", MARC_SOLID), ("drink", MARC_WATER)]}, 180)
    assert sum(b - a for a, b in zip(hs, hl)) / 180 > 0
    assert all(a <= b + 1e-12 for a, b in zip(hs, hl))


def test_fullness_is_linear_in_the_volume_of_food(host):
    # S1235 (Goetze 2007; the brief named S1229), direction: fullness linear in gastric volume, read at minute 1 for
    # 100-600 g of food water from the request
    vols = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
    hs = [hunger(host, {0: [("food", {"water": g})]}, 1)[0] for g in vols]
    assert all(a > b for a, b in zip(hs, hs[1:])), hs
    mx, my = sum(vols) / 6, sum(hs) / 6
    sxy = sum((x - mx) * (y - my) for x, y in zip(vols, hs))
    sxx = sum((x - mx) ** 2 for x in vols)
    syy = sum((y - my) ** 2 for y in hs)
    assert sxy * sxy / (sxx * syy) > 0.999


def test_a_less_energy_dense_meal_sates_more(host):
    # S1230 (Robinson 2022: SMD -1.0 on lower energy density) and S1229 (Rolls 1999: -16 % of intake at 4.4 vs 6.7
    # kJ/g), direction: 400 kcal at 0.8 against 1.6 kcal/g holds hunger lower over 3 h, and its request is no earlier
    lo = hunger(host, {0: [("food", dense(400.0, 0.8))]}, 900)
    hi = hunger(host, {0: [("food", dense(400.0, 1.6))]}, 900)
    assert sum(lo[:180]) < sum(hi[:180])
    assert request(lo) >= request(hi)


# --- the protein weight (S1222, S1223; ruling 11c-30) ----------------------------------------------------------------

def protein_contrast(host):
    """The attempt: a 400 kcal preload at 30 % protein against one at 10 % (the carbohydrate taking the difference; an
    ASSUMED contrast, since the rows give none), from the request, as the mean hunger difference over 240 min."""
    hi = mixed(400.0, water=300.0, p=0.30, c=0.35, f=0.35)
    lo = mixed(400.0, water=300.0, p=0.10, c=0.55, f=0.35)
    hh = hunger(host, {0: [("food", hi)]}, 240)
    hl = hunger(host, {0: [("food", lo)]}, 240)
    return sum(b - a for a, b in zip(hh, hl)) / 240


def test_a_protein_preload_leaves_less_hunger_than_a_lower_protein_one(host):
    # S1222 (Kohanmoo 2020: hunger -7 mm), S1223 (Dhillon 2016: fullness AUC up over 240 min): the direction only
    assert protein_contrast(host) > 0


def test_marmonier_snack_delay_differences_bound_the_protein_weight(host):
    # S1224 (Marmonier 2000), read as differences: the protein snack's delay over the carbohydrate snack's (study 26
    # min) and over the fat snack's (study 35 min), each within 1.5x; the model reads 35 and 27. The absolute delays
    # stay a named non-reproduction (below). W_PROTEIN at x2 and x0.5 each fail this.
    pc, pf = marmonier_differences(host)
    assert ratio(pc, 26.0) <= 1.5 and ratio(pf, 35.0) <= 1.5, (pc, pf)


# --- named non-reproductions, pinned (a change is noticed) -----------------------------------------------------------

def test_marmonier_snack_delays_stay_a_named_non_reproduction(host):
    # S1224 (Marmonier 2000): 60 / 34 / 25 min (p / c / f); the model's delays sit 3-7x long and the order of p over
    # c and f is kept
    d = marmonier(host)
    assert (d["p"], d["c"], d["f"]) == (200, 165, 173), d
    assert d["p"] > d["c"] and d["p"] > d["f"]


def test_s1222_vas_level_stays_a_named_non_reproduction(host):
    # S1222 (Kohanmoo 2020: hunger -7 mm). Under a request-anchored mapping (a LABELLED ASSUMPTION: no row gives a
    # pre-meal VAS; about 65 mm read as 0.25) the target is about 0.025; the model's 0.0027 is about 10x short (the
    # near-logarithmic read, and displayed hunger never falling below about 0.12)
    d = protein_contrast(host)
    assert round(d, 4) == 0.0027, d
    assert 0.025 / d > 5


def test_melanson_fasted_drinks_stay_a_named_non_reproduction(host):
    # S1228 (Melanson 1999): 65 min (carbohydrate) and 126 min (fat); the model about 236 min for both
    assert melanson(host) == [236, 236]


def test_moores_1692_g_meal_stays_a_named_non_reproduction(host):
    # S1272 (Moore 1981): 277 min solid half-emptying for the 1692 g meal; the model's ceiling is 400 ln 2 = 277 min
    t = moore_half_emptying(host)
    assert t == 189, t
    assert 277.0 / t > TOL


def test_a_25_percent_deficit_rise_is_pinned(host):
    # Ruling C-3: the deficit drive, a named non-reproduction. S1255 (CALERIE 2) bounds the hunger rise of a 25 %
    # deficit kept for 2 y at under 10 mm. A same-day 25 % deficit of a 2,500 kcal day is a trailing-24 h balance of
    # -625 kcal: K.energy.state reads 1 + 0.5 x 625 / 1500 = 1.2083, and at the meal request (sated x = 0.75, hunger
    # 0.25 at state 1) hungerTarget reads 0.25 x 1.2083 + DEFICIT_FLOOR 0.15 x 0.2083 = 0.3333: a rise of 0.4 x
    # 0.2083 = 0.0833. Under the request-anchored mapping (a LABELLED ASSUMPTION, ruling 11c-31: about 65 mm read as
    # 0.25, so 260 mm per unit of HUNGER) that is about 22 mm, over S1255's bound; no replay holds it
    es = host.call("energy.state", -0.25 * 2500, 0, 1)
    assert abs(es - (1 + 0.5 * 625 / 1500)) < 1e-12
    rise = host.call("hybrid.hungerTarget", 1 - H_REQ, es) - host.call("hybrid.hungerTarget", 1 - H_REQ, 1)
    assert abs(rise - 1 / 12) < 1e-9, rise
    assert rise * 260 > 10                       # about 21.7 mm against S1255's < 10 mm over 2 y: not reproduced


# --- sleep debt (Plan 11d Task 3, ruling 11d-2; spec § 5d) -----------------------------------------------------------
# The factor is not yet in the writer (Plan 11d Task 6 wires it), so the replay composes the written hunger itself:
# min(0.69, H_REQ x sleepFactor(record.acute.debtH)), the request level times the factor read off a live acute record.

MM_PER_HUNGER = 260.0           # ruling 11c-31: 65 mm VAS read as HUNGER 0.25 (a LABELLED ASSUMPTION, no row)
DAY_KCAL = 2000.0               # ASSUMED day (no row): turns the studies' kcal/d into the intake ratio's band
MEAL_MINUTES = (1, 300, 660)   # ASSUMED meals of the next day at 08:01, 13:00 and 19:00 (a game choice); the ratio does not hang on them


def acute_night(host, a, ageH0, slept_h):
    """One 24 h accounting window from ageH0 at 08:00: awake 24 - slept_h hours, then asleep slept_h hours, so the
    window closes on the last asleep minute and books its debt (K.acute.sleepMinute). Returns the window's end."""
    A = host.K.acute
    n_awake = int(round((24.0 - slept_h) * 60))
    n_sleep = int(round(slept_h * 60))
    for i in range(1, n_awake + 1):
        A.sleepMinute(a, False, (8.0 + i / 60) % 24, 1.0, ageH0 + i / 60, 1 / 60, False)
    for i in range(n_awake + 1, n_awake + n_sleep + 1):
        A.sleepMinute(a, True, (8.0 + i / 60) % 24, 1.0, ageH0 + i / 60, 1 / 60, False)
    return ageH0 + (n_awake + n_sleep) / 60


def next_day_hungers(host, a, ageH0):
    """The written hunger at each of the next day's meals, each eaten at the request, the factor read off the live
    record's debt at the meal's minute (the record runs awake through the day; the debt books only at the window's
    close, so it holds all day)."""
    A = host.K.acute
    out = []
    for i in range(1, 16 * 60 + 1):
        A.sleepMinute(a, False, (8.0 + i / 60) % 24, 1.0, ageH0 + i / 60, 1 / 60, False)
        if i in MEAL_MINUTES:
            out.append(min(0.69, H_REQ * host.K.satiety.sleepFactor(a.debtH)))
    return out


def sleep_debt_reading(host):
    """(debt booked, hunger rise at the request in mm, the next-day intake ratio, the factor after a recovery night).
    One short night of 5.5 h (S1565: restriction to 5.5 h or less) books the debt; the intake ratio is the sum of
    650 kcal x hunger / 0.25 over the next day's meals against the same day rested (the intake mapping, ruling 11c-30);
    then a recovery night of 9.5 h repays REPAY of its excess (S1567: intake falls on recovery sleep)."""
    a = host.K.acute.new(0.0)
    t = acute_night(host, a, 0.0, 5.5)
    debt = a.debtH
    hs = next_day_hungers(host, a, t)
    rested = host.K.acute.new(0.0)
    tr = acute_night(host, rested, 0.0, 7.5)
    hr = next_day_hungers(host, rested, tr)
    rise_mm = (hs[0] - H_REQ) * MM_PER_HUNGER
    intake = sum(650.0 * x / H_REQ for x in hs) / sum(650.0 * x / H_REQ for x in hr)
    b = host.K.acute.new(0.0)
    tb = acute_night(host, b, 0.0, 5.5)
    acute_night(host, b, tb, 9.5)
    return debt, rise_mm, intake, host.K.satiety.sleepFactor(b.debtH)


def test_one_short_night_raises_hunger_at_the_request_by_the_pooled_size(host):
    # S1284 (Zhu 2019, 41 RCTs): hunger +13.4 mm under sleep restriction; under the request-anchored mapping (ruling
    # 11c-31, 260 mm per unit, a LABELLED ASSUMPTION) the replay's rise at the request after one 5.5 h night lies
    # within 1.5x of it (model 0.25 x 0.18 x 260 = 11.7 mm)
    debt, rise_mm, _, _ = sleep_debt_reading(host)
    assert abs(debt - host.K.satiety.SLEEP_DEBT_FULL_H) < 1e-9, debt   # the acute kernel books a full debt
    assert ratio(rise_mm, 13.4) <= 1.5, rise_mm


def test_one_short_night_raises_next_day_intake_within_the_pooled_band(host):
    # S1284 (+252.8 kcal/d) and S1565 (Fenton 2021, <= 5.5 h: +204 kcal/d) on the ASSUMED 2,000 kcal day read 1.126
    # and 1.102 (S1564's +385 kcal/d, 1.19, the band's top): the implied next-day intake ratio lies in 1.10-1.19
    # (model 1.18)
    _, _, intake, _ = sleep_debt_reading(host)
    assert 1.10 <= intake <= 1.19, intake


def test_recovery_sleep_reverses_the_factor_partially(host):
    # S1567 (Markwald 2013): intake fell on recovery sleep. A 9.5 h night after the short one repays REPAY (0.5) of
    # its 2 h excess, so the factor falls but stays above 1 (the kernel's partial repayment)
    _, _, _, f = sleep_debt_reading(host)
    S = host.K.satiety
    assert 1 < f < 1 + S.SLEEP_MAX, f
    assert abs(f - (1 + S.SLEEP_MAX * (2.0 - host.K.acute.REPAY * 2.0) / S.SLEEP_DEBT_FULL_H)) < 1e-9, f


# --- the diagnostic replays: a 36 h fast, and six meals against three (Plan 11d Task 4, ruling 11d-3; spec § 5d) ---
# Pinned readings, not fits: a reading outside its study is a finding for the controller's ruling 11d-3 (about the
# deficit floor, K.hybrid.DEFICIT_FLOOR, and the -eb24h / 1500 slope of K.energy.state), never a patch to the model.
#
# The fast replay runs the energy path the way NR_Server_Metabolism.step and NR_Server_Nutrients build it, one game
# minute a step: the eat books its vector into the day (K.energy.intake), the minute's expenditure (K.energy.minute),
# the exercise lag (K.energy.exerciseLag), the day close (K.partition.closeDay, with inDayClosed and exKcalPrev
# stamped as closeDay stamps them), the energy state (K.energy.activityState on K.energy.eb24h, the trailing-24 h
# exercise kcal, the lag, fatDep, g and the 24 h expenditure MET.ee24 computes), then the glycogen step
# (K.acute.glycogen on the trailing-24 h carbohydrate g/kg, K.body.blend24 over carbDay and carb7[7]), so the state
# reads the g of the minute before, as the server's step order does. Its simplifications, stated:
# - one 70 kg man from K.body.new (sex 1, no build flags, Strength 5, carry and responder 1), awake 07:00-23:00 at
#   MET 1.3 (the idle class, COMPENDIUM.Default) and asleep at 1.0 (Sleeping), resting, coldMult 1: no exercise, so
#   the lag and the trailing exercise kcal stay 0 (the ee24, ex24 and L build is inert: the bypass path is untested);
# - the day's partition (K.partition.day: the fat and lean change), the adaptive thermogenesis step and the training
#   and aerobic closes are not run: fm stays at its birth value, so fatDep is 0 throughout (a 36 h fast's deficit is
#   a few hundred grams of fat against the store, a fatDep of a few hundredths, left out) and at stays 0;
# - an eat books its whole vector at the eat (no stomach: the absorbed vector arrives at once, not over hours);
# - no P, F or stomach: a request-level meal reads the written hunger at the request, min(0.69,
#   hungerTarget(1 - H_REQ, es) x circadian(h)), the sated product held where state 1 reads the request.
# The intake mapping is ruling 11c-31 (a LABELLED ASSUMPTION, no row): a request-level meal eats 650 kcal x that
# hunger / 0.25, at fixed clock times (08:00, 13:00, 20:00, ASSUMED). So the next-day intake ratio is the ratio of the
# summed written hunger at the meal requests, fast arm over fed arm: what it measures is the energy state's lift of
# the request-level hunger (the -eb24h / 1500 slope and DEFICIT_FLOOR, through hungerTarget; the glycogen term is 0), fed
# back through each meal's kcal into the next meal's eb24h. It does not measure the meal pool or the stomach, and it
# does not measure when a meal is asked for (the times are fixed).
#
# Glycogen (C9): the replay logs g and the glycogen term's contribution to the energy state, read through the real
# function as activityState(..., g, ...) - activityState(..., 1, ...), at 12, 24 and 36 h of the fast and at 24 h of a
# low-carbohydrate day at maintenance energy (50 g of carbohydrate, the memo's C9 threshold; 20 % protein, fat the
# rest). Since Plan 11d Task 4b (ruling T4-1) GLYC_STATE_K is 0: g still falls, and its contribution reads 0.

FAST_KCAL_PER_HUNGER = 650.0 / H_REQ    # ruling 11c-31's intake mapping, kcal per unit of written hunger
FAST_MEAL_H = (8.0, 13.0, 20.0)         # ASSUMED clock of the three meals (a game choice): 20:00 to 08:00 two days on is 36 h
FAST_WARM_DAYS = 3                      # maintenance days before the protocol's day 0: near-steady (g within 0.004 of six days)
FAST_LOWCARB_G = 50.0                   # ASSUMED low-carbohydrate day: 50 g/d (the memo's C9 threshold), 20 % protein, fat the rest

ENERGY_REPLAY = r"""
function(plan, days, logs, H_REQ, KCAL_PER_H, LOWCARB_G)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local body = K.body.new(70, 1, {}, 5, 1, 1, 0)
    body.exKcalPrev = 0
    local a = K.acute.new(0)
    local L = 0
    local w0 = body.fm + body.lm
    local maint = K.energy.ree(body.lm) + (K.energy.COMPENDIUM.Default - K.energy.MET_REST) * w0 / 60 * 960
    local intake = {}
    for d = 1, days do
        intake[d] = 0
    end
    local out = {}
    local es = 1
    for m = 0, days * 1440 - 1 do
        local hod = (m / 60) % 24
        local w = body.fm + body.lm
        local kind = plan[m]
        if kind ~= nil then
            local kcal = maint / 3
            local p, c, f = 0.15, 0.50, 0.35
            if kind == "request" then
                kcal = KCAL_PER_H * K.min(0.69, K.hybrid.hungerTarget(1 - H_REQ, es) * K.satiety.circadian(hod))
            elseif kind == "lowcarb" then
                c = LOWCARB_G * 4 / maint
                p = 0.20
                f = 1 - p - c
            end
            local v = K.vector.new()
            v.calories = kcal
            v.proteins = kcal * p / 4
            v.carbs = kcal * c / 4
            v.lipids = kcal * f / 9
            K.energy.intake(body, v, 1)
            local d = math.floor(m / 1440) + 1
            intake[d] = intake[d] + kcal
        end
        local asleep = hod >= 23 or hod < 7
        local met = K.energy.COMPENDIUM.Default
        if asleep then
            met = K.energy.COMPENDIUM.Sleeping
        end
        local ex0 = body.exKcalDay
        K.energy.minute(body, met, true, 1, 1)
        L = K.energy.exerciseLag(L, body.exKcalDay - ex0, 1 / 60)
        local ageH = (m + 1) / 60
        if math.floor(ageH / 24) > body.dayIndex then
            body.inDayClosed = body.inDay
            body.exKcalPrev = body.exKcalDay
            K.partition.closeDay(body, ageH)
        end
        local hSince = ageH - body.lastCloseAgeH
        local ree = K.energy.ree(body.lm)
        local eeYest = ree
        if body.inDayClosed ~= nil then
            eeYest = body.inDayClosed - body.eb7[7]
        end
        local ee24 = K.max(K.body.blend24(body.eeDay, eeYest, hSince), ree)
        local ex24 = K.body.blend24(body.exKcalDay, body.exKcalPrev, hSince)
        local eb24 = K.energy.eb24h(body, hSince)
        es = K.energy.activityState(eb24, ex24, L, 0, a.g, ee24)
        if logs[m + 1] then
            out[m + 1] = {
                g = a.g,
                es = es,
                glyc = es - K.energy.activityState(eb24, ex24, L, 0, 1, ee24),
                eb24 = eb24,
            }
        end
        K.acute.glycogen(a, met, 1, K.body.blend24(body.carbDay, body.carb7[7], hSince) / w, 1 / 60)
    end
    debug.sethook(hook, mask)
    return intake, out, maint
end
"""


def energy_replay(host, plan, days, log_minutes=()):
    """Runs ENERGY_REPLAY: plan maps a minute (0 = 00:00 of the first warm-up day) to "maint" (a third of the maintenance day,
    mixed), "lowcarb" (the same at 50 g/d of carbohydrate) or "request" (a request-level meal under the intake
    mapping). Returns (kcal eaten per day, {minute end: {g, es, glyc, eb24}} at each logged minute end, maintenance)."""
    t = host.rt.table()
    for m, kind in plan.items():
        t[m] = kind
    logs = host.rt.table()
    for m in log_minutes:
        logs[m] = True
    intake, out, maint = host.rt.eval(ENERGY_REPLAY)(t, days, logs, H_REQ, FAST_KCAL_PER_HUNGER, FAST_LOWCARB_G)
    return ([intake[d] for d in range(1, days + 1)],
            {m: {k: out[m][k] for k in ("g", "es", "glyc", "eb24")} for m in log_minutes}, maint)


def meals_of(day, kind):
    """The protocol day's three meals (day 0 the protocol's first) as plan entries, after the warm-up days."""
    return {int((FAST_WARM_DAYS + day) * 1440 + h * 60): kind for h in FAST_MEAL_H}


def at_hour(day, h):
    """The minute end at clock hour h of the protocol day (the log's key)."""
    return int((FAST_WARM_DAYS + day) * 1440 + h * 60)


def warm():
    """The warm-up: FAST_WARM_DAYS maintenance days, so the trailing balance, the carbohydrate blend and g start the
    protocol near-steady (g within 0.004 of six days; a fresh K.body.new has no closed day: carb7[7], eb7[7] read 0)."""
    plan = {}
    for d in range(-FAST_WARM_DAYS, 0):
        plan.update(meals_of(d, "maint"))
    return plan


def fast_reading(host):
    """S1613's protocol on the model: day 0 maintenance; the fed arm eats maintenance on day 1, the fast arm nothing
    from 20:00 on day 0 to 08:00 on day 2 (36 h); both eat request-level meals on days 2 and 3. Returns (day-2
    intake ratio, day-3 intake ratio, the fast arm's log at 12, 24 and 36 h of the fast, the kcal per protocol day
    of the fed arm and of the fast arm)."""
    fed = warm()
    fast = warm()
    for d, kind in ((0, "maint"), (1, "maint"), (2, "request"), (3, "request")):
        fed.update(meals_of(d, kind))
        if d != 1:
            fast.update(meals_of(d, kind))
    at = [at_hour(0, 20 + 12), at_hour(0, 20 + 24), at_hour(0, 20 + 36)]
    days = FAST_WARM_DAYS + 4
    ifed, _, _ = energy_replay(host, fed, days)
    ifast, log, _ = energy_replay(host, fast, days, at)
    ifed, ifast = ifed[FAST_WARM_DAYS:], ifast[FAST_WARM_DAYS:]
    return ifast[2] / ifed[2], ifast[3] / ifed[3], [log[m] for m in at], ifed, ifast


def lowcarb_reading(host):
    """C9: day 0 maintenance and mixed; on day 1 the mixed arm eats the same and the low-carbohydrate arm eats
    maintenance at 50 g of carbohydrate. Returns (the mixed arm at 08:00 on day 1, before breakfast; the mixed arm at
    20:00 on day 1; the low-carbohydrate arm at 20:00 on day 1, 24 h after day 0's last mixed meal and the fast's own
    24 h point)."""
    mixed_day = warm()
    low = warm()
    mixed_day.update(meals_of(0, "maint"))
    low.update(meals_of(0, "maint"))
    mixed_day.update(meals_of(1, "maint"))
    low.update(meals_of(1, "lowcarb"))
    m8, m20 = at_hour(1, 8), at_hour(1, 20)
    days = FAST_WARM_DAYS + 2
    _, lm, _ = energy_replay(host, mixed_day, days, [m8, m20])
    _, ll, _ = energy_replay(host, low, days, [m20])
    return lm[m8], lm[m20], ll[m20]


def meal_frequency_ratio(host):
    """S1608 (Ohkawara 2013): 2,000 kcal a day (ASSUMED) eaten as six isoenergetic meals against three, the 24 h mean
    displayed hunger (the AUC over the same 24 h) six over three, through the satiety replay above (the stomach, P
    and the circadian factor from 08:00; the energy state held at 1, which moves the ratio about 0.03). The times are
    ASSUMED (the row gives none): three at 08:00, 13:00, 18:00; six every 150 min from 08:00 to 20:30. Each meal is
    mixed() with water and fibre scaled to its energy, so the two days carry the same mass. From an overnight fast,
    P = 0."""
    def day(n, gap):
        k = 2000.0 / n
        return {i * gap: [("food", mixed(k, water=900.0 / n, fibre=6.0 * k / 650))] for i in range(n)}
    three = hunger(host, day(3, 300), 1440, P0=0.0, h0=8.0)
    six = hunger(host, day(6, 150), 1440, P0=0.0, h0=8.0)
    return sum(six) / sum(three)


def test_a_36_h_fast_raises_next_day_intake_and_day_3_falls_back(host):
    # S1613 (Johnstone 2002): 12.2 against 10.2 MJ the day after a 36 h fast, 1.20; S1614 (Clayton 2016, 24 h at 25 % of
    # requirement, not a 36 h fast): day 3 not different, 1.0. Ruling 11d-3 asserts the direction: day 2 above 1, day 3 below
    r2, r3, _, _, _ = fast_reading(host)
    assert r2 > 1, r2
    assert r3 < r2, (r2, r3)


def test_the_36_h_fast_intake_ratios_are_pinned(host):
    # Pinned diagnostics (ruling 11d-3), re-pinned by Plan 11d Task 4b (ruling T4-1, the glycogen term retired; Task 4
    # read 1.259 and 0.944 with it): the day after the fast 1.197 (S1613 1.20: 1.003x below), day 3 0.950 (S1614 1.0:
    # 1.05x below). Under the intake mapping these are the summed written hunger at the meal requests, fast arm over
    # fed arm (see the section's head): the fed arm itself eats 2,241 kcal on day 2 against the 1,949 kcal maintenance
    # day, the trailing-24 h window reading a deficit before each meal
    r2, r3, _, _, _ = fast_reading(host)
    assert round(r2, 3) == 1.197, r2
    assert round(r3, 3) == 0.950, r3


def test_the_fasts_glycogen_term_is_logged_and_pinned(host):
    # C9 (ruling 11d-3, the memo's conflict): g and the glycogen term's contribution to the energy state at 12, 24
    # and 36 h of the fast, read through K.energy.activityState: g still falls, 0.996, 0.881, 0.718, but since Plan 11d
    # Task 4b (ruling T4-1: GLYC_STATE_K 0) its contribution is 0 (Task 4 read 0.001, 0.036, 0.085 at 0.3), so the
    # state reads 1.186, 1.5 and 1.5: from 24 h on (eb24h -1,617 and -1,858 kcal) the balance term sits at its 0.5 cap
    # and hunger plateaus there, the ruling's named cost
    _, _, log, _, _ = fast_reading(host)
    assert host.K.energy.GLYC_STATE_K == 0
    assert [round(x["g"], 3) for x in log] == [0.996, 0.881, 0.718], log
    assert [x["glyc"] for x in log] == [0, 0, 0], log
    assert [round(x["es"], 3) for x in log] == [1.186, 1.5, 1.5], log


def test_a_low_carbohydrate_day_at_maintenance_runs_glycogen_down(host):
    # C9: yes, a low-carbohydrate day runs g down. 24 h of maintenance energy at 50 g of carbohydrate (0.71 g/kg, below
    # GLYC_PIVOT 3) reads g 0.909, where the mixed arm (50 % carbohydrate, 3.5 g/kg) reads g 1.000 (0.996 at its
    # lowest, before breakfast). Since Plan 11d Task 4b (ruling T4-1: GLYC_STATE_K 0) the energy state no longer reads
    # g: at equal balance (eb24h -318 kcal in both arms, the window's phase at 20:00) the two arms read the same state,
    # where Task 4 read a glycogen term of 0.027 on the low-carbohydrate arm. So a low-carbohydrate day at equal
    # balance no longer raises hunger, consistent with S1451, S1452 and S1259 (a ketogenic deficit blunts appetite):
    # this test pins the retirement directly
    m8, m20, low = lowcarb_reading(host)
    assert round(m8["g"], 3) == 0.996 and round(m20["g"], 3) == 1.0 and m20["glyc"] == 0, (m8, m20)
    assert round(low["g"], 3) == 0.909 and low["glyc"] == 0, low
    assert low["eb24"] == m20["eb24"] and abs(low["es"] - m20["es"]) < 1e-12, (low, m20)


def test_six_meals_against_three_is_pinned_inside_the_band(host):
    # S1608 (Ohkawara 2013): hunger AUC over 24 h 41,850 on six isoenergetic meals against 36,612 on three, 1.14;
    # S1607 (Raynor 2015): the vote count mostly null. Ruling 11d-3: the model's ratio lies within [0.9, 1.3] and is
    # pinned: 0.938, the opposite direction to S1608 (grazing reads less mean hunger) and 1.22x below it, nearer
    # S1607's null. The 0.938 is schedule-sensitive: it comes mainly from the six-meal arm's last meal at 20:30 against
    # 18:00 for three meals. On a same-span schedule (six meals every 2 h from 08:00 to 18:00) the model reads 0.996,
    # and 0.970 with the energy state live (Task 4 review). The model never reaches S1608's direction under any of
    # these schedules
    r = meal_frequency_ratio(host)
    assert 0.9 <= r <= 1.3, r
    assert round(r, 3) == 0.938, r
