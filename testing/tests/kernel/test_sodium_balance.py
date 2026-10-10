"""The multi-day sodium balance (Plan 11f Task 5b, finding F-T5-1, ruling F5-2).

Until Task 5b the kernel charged basal urine as isotonic sodium, 336.7 mmol/d for the reference man whatever the
intake, and no test ran a sodium balance longer than 10 h, so every realistic diet walked the character down the
hyponatraemia ladder to death (05-sodium-drain.md). These oracles run the mod's own K.fluids, minute by minute, for
10 game days on the kernel host and grade the balance against the science register:

- the obligatory sodium loss, 8 mmol/d (S1665, IOM 2005 Table 6-1);
- the renal adaptation time constant, the 30-59 y half-time 23.4 h of S1670 over ln 2 (the mod has no age, so the
  reference adult's band is the one used), against S1672's 458 mmol cumulative retention on a 20 -> 300 mmol/d step;
- the 24 h urinary recovery at steady state, S1674's 92.8 % (95 % CI 90.7-95.0), widened to 88-97 % by the
  obligatory loss the model charges outside the kidney;
- plasma sodium held by water, not by sodium excretion (S1678: 140 vs 138 mmol/L at 200 vs 50 mmol/d), with
  He 2005's fall of about 3 mmol/L after 5 days near zero sodium (S1680) as the named reading;
- water follows sodium: the euhydration set point carries 1000/140 g of water per retained mmol (S1683), against
  S1673's 10.5 mL per mmol of ECV on a low-to-normal step and S1678's 1.4 kg over the 50 -> 200 mmol/d band;
- the maximal free-water clearance, 11.2 mL/min = 672 g/h (S1685, Noakes 2001);
- the hypotonic thirst cap under vanilla autoDrink's 0.1 trigger (#2770), so suppression stops drinking;
- drinking to thirst drinks what people drink (Plan 11f Task 5b fix 1, ruling 5b-2): about 2.0-3.0 L/d of beverages
  for a sedentary man in a temperate climate and about 1.6-2.2 L/d for a woman (a derivation from S1707's ad libitum
  balance studies, S1708's fluid share and food water, S1709's deuterium turnover and S1710's loss per MJ; the women's
  bottom rests on three subjects).

THE LIMIT (stated, not modelled): at high sustained intakes sodium is also stored without water (S1673's
normal-to-high step retained 244 mmol with no ECV gain; S1677, Rakova 2013's swings of 200-400 mmol without body
water). The set point retains every mmol isotonically, so above about 200 mmol/d the model overstates the water
retained.

The drinking model is vanilla autoDrink (#2770): while awake (07:00-23:00), a minute whose THIRST target exceeds 0.1
drinks 2 x THIRST litres into the stomach's liquid lane, which empties first-order at K.stomach.WATER_HALF_MIN (13 min,
S1245; the meals here carry no energy into the solid lane, so the lane is never slowed). As the server does, the
thirst view counts the lane's still-unabsorbed water (ruling T1-1), in its osmotic term too (Plan 11f Task 5b fix 1:
satiation precedes absorption, S1698 and S1699; the weight 1.0 is a game choice).
The body is the 80 kg reference man (lean 65.6 kg), sedentary (MET 1.3, so no sweat), thermoFluids 1, no cold, no
alcohol. Meals at 08:00, 13:00 and 19:00 each carry a third of the day's sodium and potassium, absorbed evenly over
120 minutes, and no water (the drinking covers it). The step and retention arms absorb their intake evenly every
minute, so the renal kinetic is read without the meals' ripple.
"""
import functools
import math

import pytest

LM = 65.6
W = 80.0
DAY = 1440
AUTODRINK = 0.1                     # #2770: autoDrink drinks only when thirst exceeds a hard-coded 0.1
LITRES_PER_THIRST = 2               # #2770: min(container, 2 x thirst); NR_Server_Nutrients' LITRES_PER_THIRST
MEAL_MIN = 120
MEALS = (8 * 60, 13 * 60, 19 * 60)
WAKE, SLEEP = 7 * 60, 23 * 60
K_DIET = 70.0                       # mmol/d of potassium on the two salted diets (about 2.7 g, a mixed diet)
# the reference bodies: sex, lean kg, body kg, food water g/d (S1708: food gives 0.7 L/d to men and 0.5 L/d to women).
# The man is the file's 80 kg reference; the woman is a 65 kg body at K.body.BF_FEMALE's 0.28 band (lean 46.8 kg), the
# test's own choice.
BODIES = {"man": (1, 65.6, 80.0, 700.0), "woman": (2, 46.8, 65.0, 500.0)}


def _host():
    from .conftest import LuaHost
    return LuaHost()


@functools.lru_cache(maxsize=None)
def _shared():
    # one host for every arm of this file, so each arm runs once per session
    return _host()


@functools.lru_cache(maxsize=None)
def simulate(days, na_day, k_day=0.0, meals=True, na_day_after=None, switch_day=None, water_load=None, body="man",
             food=False):
    """Run K.fluids minute by minute; returns per-day summaries and the hourly trace."""
    h = _shared()
    F = h.K.fluids
    sex, lm, w, food_g = BODIES[body]
    if not food:
        food_g = 0.0
    f = F.new(lm, 1.0, 37.0)
    ctx = h.table(dict(sex=sex, met=1.3, thermoFluids=1.0, coldMult=1.0, ethanolAbsG=0.0, dehydPct=0.0))
    ab = h.table(dict(water=0.0, sodium=0.0, potassium=0.0))
    liquid = 0.0                     # the liquid lane, g
    lane = 1 - 0.5 ** (1 / float(h.K.stomach.WATER_HALF_MIN))
    meal = []
    out_days, hourly = [], []
    day = None
    for m in range(days * DAY):
        tod = m % DAY
        if tod == 0:
            day = dict(na_in=0.0, urine=0.0, drunk=0.0, grade=0, pmin=1e9, pmax=-1e9, psum=0.0, water_sum=0.0,
                       na_sum=0.0, cleared_g=0.0)
            out_days.append(day)
        na_now = na_day
        if switch_day is not None and m >= switch_day * DAY:
            na_now = na_day_after
        # this minute's absorbed vector
        sodium_mg = potassium_mg = water_g = 0.0
        if meals:
            if tod in MEALS:
                meal.append([na_now / 3 * 23 / MEAL_MIN, k_day / 3 * 39.1 / MEAL_MIN, food_g / 3 / MEAL_MIN, MEAL_MIN])
            for e in meal:
                sodium_mg += e[0]
                potassium_mg += e[1]
                water_g += e[2]
                e[3] -= 1
            meal = [e for e in meal if e[3] > 0]
        else:
            sodium_mg = na_now * 23 / DAY
            potassium_mg = k_day * 39.1 / DAY
        if water_load is not None and m < water_load[1]:
            water_g += water_load[0] / 60.0
        out = liquid * lane
        liquid -= out
        water_g += out
        ab.water, ab.sodium, ab.potassium = water_g, sodium_mg, potassium_mg
        F.intake(f, ab)
        day["na_in"] += sodium_mg / 23
        ctx.dehydPct = f.dehydPct
        F.losses(f, ctx, 1)
        na0 = f.na
        w0 = f.water
        F.clearance(f, 1)
        day["urine"] += na0 - f.na
        day["cleared_g"] += w0 - f.water
        f.dehydPct = F.dehydPct(f, w, 0)
        view = F.dehydPct(f, w, liquid)
        f.c = F.conc(f, lm)
        f.naPlasma = F.naPlasma(f.c)
        # Plan 11f Task 5b fix 1: the view's osmotic term counts the swallowed water too, as the server does
        f.thirstTarget = F.thirstTarget(view, F.conc(f, lm, liquid), f.naPlasma, True)
        p = f.naPlasma
        day["grade"] = max(day["grade"], int(F.hyponatGrade(p)))
        day["pmin"] = min(day["pmin"], p)
        day["pmax"] = max(day["pmax"], p)
        day["psum"] += p
        day["water_sum"] += f.water
        day["na_sum"] += f.na
        if WAKE <= tod < SLEEP and water_load is None and f.thirstTarget > AUTODRINK:
            litres = LITRES_PER_THIRST * f.thirstTarget
            liquid += litres * 1000
            day["drunk"] += litres
        if tod == DAY - 1:
            day["p_end"] = p
            day["na_end"] = f.na
            day["water_end"] = f.water
            day["pmean"] = day["psum"] / DAY
            day["water_mean"] = day["water_sum"] / DAY
            day["na_mean"] = day["na_sum"] / DAY
        if m % 60 == 59:
            hourly.append(dict(m=m + 1, na=f.na, water=f.water, p=p, cleared=day["cleared_g"]))
    return out_days, hourly


def _table(days):
    return [(i + 1, round(d["na_in"], 1), round(d["urine"], 1), round(d["p_end"], 2), d["grade"])
            for i, d in enumerate(days)]


# --- the three diets ------------------------------------------------------------------------------------------

def test_zero_sodium_never_grades_and_loses_only_the_obligatory_loss():
    days, _ = simulate(10, 0.0)
    assert all(d["grade"] == 0 for d in days), _table(days)
    # within 3 mmol/L of 140 by day 5; He 2005 (S1680) measured a fall of about 3 mmol/L after 5 days at 10-20 mmol/d
    assert abs(days[4]["p_end"] - 140) <= 3, days[4]["p_end"]
    # cumulative loss under 120 mmol: S1665's 8 mmol/d over 10 days plus the pool's adaptation
    assert -days[-1]["na_end"] < 120, days[-1]["na_end"]
    assert -days[-1]["na_end"] > 70


@pytest.mark.parametrize("na_day", [120.0, 220.0])
def test_a_salted_diet_reaches_urinary_balance_with_plasma_held(na_day):
    days, _ = simulate(10, na_day, K_DIET)
    assert all(d["grade"] == 0 for d in days), _table(days)
    for d in days[6:10]:
        share = d["urine"] / d["na_in"]
        assert 0.88 <= share <= 0.97, (na_day, share)            # S1674, widened by the obligatory loss
        assert 138 <= d["p_end"] <= 142, (na_day, d["p_end"])    # S1678: plasma defended by water


@pytest.mark.parametrize("body,band", [("man", (2.0, 3.0)), ("woman", (1.6, 2.2))])
def test_drinking_to_thirst_drinks_what_people_drink(body, band):
    # the drinking-volume oracle (a derivation, 07-thirst-volume.md section 8): days 4-10, after the salted diet's set
    # point has filled; "about" reads 5 % on the band's top. At steady state the drinks are the basal turnover (S0088 as
    # turnover, a game choice) less S1708's food water, so the man sits at the band's top and the woman at hers
    days, _ = simulate(10, 120.0, K_DIET, body=body, food=True)
    drunk = sum(d["drunk"] for d in days[3:]) / 7
    assert band[0] <= drunk <= band[1] * 1.05, (body, [round(d["drunk"], 2) for d in days])
    # the excess the uncounted swallowed water drove (ruling 5b-2) is gone: little of what is drunk is cleared unused
    cleared = sum(d["cleared_g"] for d in days[3:]) / 7 / 1000
    assert cleared < 0.1 * drunk, (body, cleared, drunk)


def test_the_hypotonic_cap_sits_under_the_autodrink_trigger(host):
    # #2770: autoDrink fires only above 0.1, so a cap at or above it never stops drinking (finding F-T5-1)
    F = host.K.fluids
    for dehyd in (0.5, 2, 4, 8):
        for canKill in (True, False):
            assert F.thirstTarget(dehyd, 1.0, 130.0, canKill) < AUTODRINK
            assert F.thirstTarget(dehyd, 1.05, 134.9, canKill) < AUTODRINK


def test_a_hypotonic_pool_reads_no_thirst_under_the_set_point():
    # under the set point a pool below its euhydration water reads c > 1, so every hypotonic pool sits above its set
    # point: no volume deficit and no osmotic drive, so no autodrink; the cap is the backstop for the view's floor
    h = _shared()
    F = h.K.fluids
    f = F.new(LM, 1.0, 37.0)
    hypo = 0
    for na in (-2000.0, -800.0, -150.0, 0.0, 150.0, 600.0):
        for k in (-100.0, 0.0, 80.0):
            for water in (-6000.0, -2000.0, -500.0, 0.0, 1000.0, 4000.0, 9000.0):
                f.na, f.k, f.water = na, k, water
                c = F.conc(f, LM)
                p = F.naPlasma(c)
                if p < F.HYPO_NA:
                    hypo += 1
                    assert F.dehydPct(f, W, 0) == 0, (na, k, water)
                    assert F.thirstTarget(F.dehydPct(f, W, 0), c, p, True) == 0, (na, k, water)
    assert hypo > 10


# --- the renal kinetic -------------------------------------------------------------------------------------------

def test_a_step_from_20_to_300_retains_what_bijlsma_measured_at_the_epstein_half_time():
    days, hourly = simulate(20, 20.0, 0.0, False, 300.0, 10)
    base = [r for r in hourly if r["m"] == 10 * DAY][0]["na"]
    end = hourly[-1]["na"]
    retained = end - base
    # S1672: 458 +/- 45 mmol cumulative balance after the switch; within 1.25x
    assert 458 / 1.25 <= retained <= 458 * 1.25, retained
    # S1670 (30-59 y): half-time 23.4 +/- 1.1 h; the time the pool takes to half its rise, within 1.25x
    half = base + retained / 2
    t_half = next(r["m"] for r in hourly if r["m"] > 10 * DAY and r["na"] >= half) - 10 * DAY
    assert 23.4 / 1.25 <= t_half / 60 <= 23.4 * 1.25, t_half / 60


def test_retained_sodium_carries_its_water_in_the_low_to_normal_band():
    lo, _ = simulate(10, 50.0, K_DIET, False)
    hi, _ = simulate(10, 200.0, K_DIET, False)
    d_na = sum(d["na_mean"] for d in hi[7:]) / 3 - sum(d["na_mean"] for d in lo[7:]) / 3
    d_w = sum(d["water_mean"] for d in hi[7:]) / 3 - sum(d["water_mean"] for d in lo[7:]) / 3
    assert d_na > 150                                           # 150 mmol/d x tau: about 211 mmol
    # S1683's 7.14 g/mmol isotonic; S1673's 10.5 mL ECV per mmol and S1678's 1.4 kg / ~211 mmol about 6.6 g/mmol
    assert 6 <= d_w / d_na <= 11, d_w / d_na
    for d in lo[6:] + hi[6:]:
        assert 138 <= d["p_end"] <= 142


def test_a_water_load_clears_at_the_maximal_free_water_rate_and_dilutes():
    # Noakes 2001 (S1685): 1.8 L/h for 3 h at rest; free-water clearance peaked at 11.2 mL/min (672 g/h)
    days, hourly = simulate(1, 0.0, 0.0, False, None, None, (1800.0, 180))
    third = hourly[2]["cleared"] - hourly[1]["cleared"]
    assert 672 / 1.25 <= third <= 672 * 1.25, third
    # drinking faster than the kidney clears dilutes plasma (S0102): Noakes's subjects fell from 144 to 136
    assert hourly[2]["p"] < 136


def test_the_balance_table_is_reported():
    # the 10-day table the task reports (in, urine, plasma at day end, worst grade), kept readable in -s output
    for na in (0.0, 120.0, 220.0):
        days, _ = simulate(10, na, 0.0 if na == 0 else K_DIET)
        print("diet", na, _table(days))
        assert len(days) == 10
