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
