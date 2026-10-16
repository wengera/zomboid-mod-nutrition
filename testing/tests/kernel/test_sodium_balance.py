"""The multi-day sodium balance (Plan 11f Task 5b, finding F-T5-1, ruling F5-2).

Until Task 5b the kernel charged basal urine as isotonic sodium, 336.7 mmol/d for the reference man whatever the
intake, and no test ran a sodium balance longer than 10 h, so every realistic diet walked the character down the
hyponatraemia ladder to death (05-sodium-drain.md). These oracles run the mod's own K.fluids, minute by minute, for
10 game days on the kernel host and grade the balance against the science register:

- the obligatory sodium loss, 8 mmol/d (S1665, IOM 2005 Table 6-1);
- the renal adaptation time constant, the 30-59 y half-time 23.4 h of S1670 over ln 2 (the mod has no age, so the
  reference adult's band is the one used), against S1672's 458 mmol cumulative retention on a 20 -> 300 mmol/d step;
- the 24 h urinary recovery at steady state, S1674's 92.8 % (95 % CI 90.7-95.0), its bottom widened to 88 % by the
  obligatory loss the model charges outside the kidney and its top kept at 95.0; the 220 mmol/d arm reads above the
  CI (95.3-96.2 %), a named reading: the fixed 8 mmol/d is a smaller share of a larger intake (ceiling 212/220);
- plasma sodium held by water, not by sodium excretion (S1678: 140 vs 138 mmol/L at 200 vs 50 mmol/d), with
  He 2005's fall of about 3 mmol/L after 5 days near zero sodium (S1680) as the named reading;
- water follows sodium: the euhydration set point carries 1000/140 g of water per retained mmol (S1683), against
  S1673's 10.5 mL per mmol of ECV on a low-to-normal step and S1678's 1.4 kg over the 50 -> 200 mmol/d band;
- the maximal free-water clearance, 11.2 mL/min = 672 g/h (S1685, Noakes 2001);
- the hypotonic thirst cap under vanilla autoDrink's 0.1 trigger (#2770), so suppression stops drinking;
- drinking to thirst drinks what people drink (Plan 11f Task 5b fix 1, ruling 5b-2): about 2.0-3.0 L/d of beverages
  for a sedentary man in a temperate climate and about 1.6-2.2 L/d for a woman (a derivation from S1707's ad libitum
  balance studies, S1708's fluid share and food water, S1709's deuterium turnover and S1710's loss per MJ; the women's
  bottom rests on three subjects); since Plan 15 Task 3's basal net loss by lean mass both read under their bands,
  a named non-reproduction (DRINK_NAMED);
- the volume defence (Plan 11f Task 5b fix 1, review finding 1): a sodium deficit contracts the set point isotonically
  up to 8 % of ECF (0.20 L/kg, S1714; the 8-10 % volume threshold of S1717 and S1722 applied to ECF, a game choice),
  then ever less, bounded by 20 % (S1729, McCance's plateau read by eye). Past the onset a volume-thirst term relaxes
  the hypotonic cap by the same ramp (Plan 11f Task 5b fix 2, candidate C-9; S1729, S1731, S1724, a game choice), so
  heat work on plain water keeps drinking: the water stays near the bounded set point, the deficit stays small and the
  pool dilutes through the hyponatraemia grades, the first after a loss of the order of McCance's 765 mEq (S1730);
- the onset itself (Plan 11f Task 5b fix 2, candidate C-12): a slow, low-sweat depletion on water in excess loses
  water pari passu with sodium (S1729's first phase) until the contraction nears 8 % of ECF, and the contraction at
  which water stops fully following sodium (a marginal under 90 % of 1000/140 g/mmol, the test's criterion) lies
  between S1717's 7 % of the volume (rat; applied to ECF) and S1721's 1.6 kg sodium-depletion weight loss, by which
  plasma vasopressin had risen;
- sweat sodium adapts to a sodium deficit (Plan 11f Task 5b fix 3, candidate C-14): the effective concentration falls
  linearly with the deficit max(-na, 0) from the drawn baseline to 0.325 of it at 331 mmol, floored at 10 mmol/L
  (08-sweat-sodium.md section 7; derivations resting on S1751, S1769, S1749, S1752, S1750 and S1753, the line a game
  choice, S1770 open). The deficit is the driver (S1747: "the presence of a salt deficit is required"; S1749, S1750),
  so heat work on plain water conserves toward about 96 mmol/d of sweat sodium while a replete worker keeps the draw.
  The detectable onset (a fall past S1762's ~15 % day-to-day variation, the test's criterion) at 296 mmol/d is graded
  within 2x of Cage and Dobson's 12 h and Robinson's 14 h (S1773, S1752).

THE WEAK SPOT (stated, not modelled): a replete, acclimatising worker keeps the drawn sweat sodium, while Allsopp
1998's replete group (S1755) and the free-diet acclimation series (S1739, S1743, S1744) fall without a known deficit;
heat acclimatisation needs an exposure field, a later candidate. No gland lag is stored (S1748's 1-4 days, S1773's
5 h of aldosterone), so a heavy shift's deficit lowers the concentration within its first hours.

THE LIMIT (stated, not modelled): at high sustained intakes sodium is also stored without water (S1673's
normal-to-high step retained 244 mmol with no ECV gain; S1677, Rakova 2013's swings of 200-400 mmol without body
water). The set point retains every mmol isotonically, so above about 200 mmol/d the model overstates the water
retained.

The drinking model is vanilla autoDrink (#2770): while awake (07:00-23:00), a minute whose THIRST target exceeds 0.1
drinks 2 x THIRST litres into the stomach's liquid lane, which empties first-order at K.stomach.WATER_HALF_MIN (13 min,
S1245; the meals here carry no energy into the solid lane, so the lane is never slowed). As the server does, the
thirst view counts the lane's still-unabsorbed water (ruling T1-1), in its osmotic term too (Plan 11f Task 5b fix 1:
satiation precedes absorption, S1698 and S1699; the weight 1.0 is a game choice), and the hypotonic cap is relaxed by
the record's volume-defence weight (Plan 11f Task 5b fix 2). The simulation passes the liquid lane's water only: its
food water is absorbed with the meal, never held in a solid buffer, so the server's buffer-water term is not exercised.
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
WORK, WORK_MET = 9 * 60, 8         # the heat-work arm's shift starts at 09:00 at MET 8 (1 L/h of sweat at sweatK 1)
K_DIET = 70.0                       # mmol/d of potassium on the two salted diets (about 2.7 g, a mixed diet)
# the reference bodies: sex (read by no basal term since Plan 15 Task 3), lean kg, body kg, food water g/d (S1708: food gives 0.7 L/d to men and 0.5 L/d to women).
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
             food=False, work_h=0, na0=0.0):
    """Run K.fluids minute by minute; returns per-day summaries and the hourly trace."""
    h = _shared()
    F = h.K.fluids
    sex, lm, w, food_g = BODIES[body]
    if not food:
        food_g = 0.0
    f = F.new(lm, 1.0, 37.0)
    f.na = na0                       # a balance carried in (Plan 11f Task 5b fix 3: the driver arm)
    ctx = h.table(dict(lm=lm, met=1.3, thermoFluids=1.0, coldMult=1.0, ethanolAbsG=0.0, dehydPct=0.0))
    ab = h.table(dict(water=0.0, sodium=0.0, potassium=0.0))
    liquid = 0.0                     # the liquid lane, g
    lane = 1 - 0.5 ** (1 / float(h.K.stomach.WATER_HALF_MIN))
    meal = []
    out_days, hourly = [], []
    day = None
    first_grade = None
    first_g3 = None
    at_mccance = None
    for m in range(days * DAY):
        tod = m % DAY
        if tod == 0:
            day = dict(na_in=0.0, urine=0.0, drunk=0.0, grade=0, pmin=1e9, pmax=-1e9, psum=0.0, water_sum=0.0,
                       na_sum=0.0, k_sum=0.0, cleared_g=0.0, dmax=0.0, weu_min=0.0, g3=0, sweat_na=0.0,
                       eff_min=1e9)
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
        ctx.met = 1.3
        if WORK <= tod < WORK + work_h * 60:
            ctx.met = WORK_MET
        nb = f.na
        F.losses(f, ctx, 1)
        day["sweat_na"] += nb - f.na - F.BASAL_NA / DAY       # the sweat's sodium alone
        day["eff_min"] = min(day["eff_min"], F.naSweatEff(f))
        nc = f.na
        w0 = f.water
        F.clearance(f, 1, w)
        day["urine"] += nc - f.na
        day["cleared_g"] += w0 - f.water
        f.dehydPct = F.dehydPct(f, w, 0)
        view = F.dehydPct(f, w, liquid)
        f.c = F.conc(f, lm)
        f.naPlasma = F.naPlasma(f.c)
        # Plan 11f Task 5b fix 1: the view's osmotic term counts the swallowed water too, as the server does; fix 2:
        # the hypotonic cap is relaxed by the volume-defence weight, as the server does
        f.thirstTarget = F.thirstTarget(view, F.conc(f, lm, liquid), f.naPlasma, F.defence(f, w))
        p = f.naPlasma
        g = int(F.hyponatGrade(p))
        day["grade"] = max(day["grade"], g)
        if g == 3:
            day["g3"] += 1
            if first_g3 is None:
                first_g3 = dict(m=m, loss=day_loss(out_days) - f.na)
        if at_mccance is None and day_loss(out_days) - f.na >= 765:
            at_mccance = dict(m=m, p=p, water=f.water, weu=F.weu(f, w))
        day["pmin"] = min(day["pmin"], p)
        day["pmax"] = max(day["pmax"], p)
        day["psum"] += p
        day["water_sum"] += f.water
        day["na_sum"] += f.na
        day["k_sum"] += f.k
        day["dmax"] = max(day["dmax"], f.dehydPct)
        day["weu_min"] = min(day["weu_min"], F.weu(f, w))
        if first_grade is None and p < F.HYPONAT[1]:
            first_grade = dict(m=m, loss=day_loss(out_days) - f.na, weu=F.weu(f, w), water=f.water)
        day["first_grade"] = first_grade
        day["first_g3"] = first_g3
        day["at_mccance"] = at_mccance
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
            day["k_mean"] = day["k_sum"] / DAY
            day["weu_end"] = F.weu(f, w)
        if m % 60 == 59:
            hourly.append(dict(m=m + 1, na=f.na, k=f.k, water=f.water, p=p, cleared=day["cleared_g"]))
    return out_days, hourly


def day_loss(days):
    # the sodium taken in so far; the cumulative loss is this less the pool's balance
    return sum(d["na_in"] for d in days)


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
        if na_day == 120.0:
            assert 0.88 <= share <= 0.950, (na_day, share)       # S1674's CI top; the bottom widened by the obligatory loss
        else:
            # a pin, not an oracle: a named reading above S1674's CI (Plan 11f Task 5b fix 1, review finding 3); the
            # 8 mmol/d obligatory loss is 3.6 % of 220, so the share climbs toward 212/220 = 96.4 %; it read 95.3-96.2 %
            # on days 7-10, and the assertion pins the model between the CI top and that ceiling
            assert 0.950 < share < (na_day - 8) / na_day, (na_day, share)
        assert 138 <= d["p_end"] <= 142, (na_day, d["p_end"])    # S1678: plasma defended by water


# Plan 15 Task 3's named non-reproduction: the drinking-volume oracle's readings under the basal net loss by lean mass
# (2000 + 32 x (lm - 52.02) g/d, S1688, S2218, S2220), each below its band. The band is what people drink, AI-level
# turnover with ordinary sweating and generous drinking (S1707, S1709); the new basal is the minimum net loss of a
# sedentary body that does not sweat (water-report.md section 1), so drinking to thirst now drinks basal less food
# water: the man 2434.56 - 700 = 1.73 L/d, the woman 1832.96 - 500 = 1.33 L/d (by construction). Under the AI 3700/2700
# they sat at their bands' tops (about 3.0 and 2.2). Pinned at the reading so a change is noticed, and asserted still
# under its band so a reading that comes back inside is promoted to a target; not re-fitted (Task 3 amendment 4).
DRINK_NAMED = {"man": 1.7593624653224822, "woman": 1.3436481768045616}   # miss under the band: 0.241 and 0.256 L/d


@pytest.mark.parametrize("body,band", [("man", (2.0, 3.0)), ("woman", (1.6, 2.2))])
def test_drinking_to_thirst_drinks_what_people_drink(body, band):
    # the drinking-volume oracle (a derivation, 07-thirst-volume.md section 8): days 4-10, after the salted diet's set
    # point has filled; "about" reads 5 % on the band's top. At steady state the drinks are the basal net loss (Plan 15
    # Task 3) less S1708's food water, so the level holds by construction, and both bodies now read under their bands
    # (DRINK_NAMED). What the oracle still tests is the absence of over-drinking (Plan 11f Task 5b fix 1, ruling
    # 5b-2): drinks above the turnover, cleared unused. The simulation passes the liquid lane's water only (its food
    # water is absorbed with the meal), so the server's solid-buffer term is not exercised here
    days, _ = simulate(10, 120.0, K_DIET, body=body, food=True)
    drunk = sum(d["drunk"] for d in days[3:]) / 7
    assert abs(drunk - DRINK_NAMED[body]) < 1e-6, (body, drunk, [round(d["drunk"], 2) for d in days])
    assert drunk < band[0], (body, drunk, "inside its band now: promote it to a target")
    # the excess the uncounted swallowed water drove (ruling 5b-2) is gone: little of what is drunk is cleared unused
    cleared = sum(d["cleared_g"] for d in days[3:]) / 7 / 1000
    assert cleared < 0.1 * drunk, (body, cleared, drunk)


def test_the_hypotonic_cap_sits_under_the_autodrink_trigger(host):
    # #2770: autoDrink fires only above 0.1, so a cap at or above it never stops drinking (finding F-T5-1)
    F = host.K.fluids
    for dehyd in (0.5, 2, 4, 8):
        assert F.thirstTarget(dehyd, 1.0, 130.0) < AUTODRINK
        assert F.thirstTarget(dehyd, 1.05, 134.9) < AUTODRINK


def test_a_hypotonic_pool_reads_no_thirst_under_the_set_point():
    # inside the volume defence's onset (Plan 11f Task 5b fix 1: na + k above -179.2 mmol at 80 kg) a pool below its
    # euhydration water reads c > 1, so every hypotonic pool sits above its set point: no deficit, no osmotic drive,
    # no autodrink, and no defence weight, so the cap stands as before. Past the onset the set point is bounded, so a
    # hypotonic pool can read a deficit, and its thirst is the cap relaxed by the defence weight toward the volume
    # thirst (Plan 11f Task 5b fix 2): between the capped and the uncapped target, the volume defended by drinking
    h = _shared()
    F = h.K.fluids
    f = F.new(LM, 1.0, 37.0)
    hypo = past = relaxed = 0
    for na in (-2000.0, -800.0, -150.0, 0.0, 150.0, 600.0):
        for k in (-100.0, 0.0, 80.0):
            for water in (-6000.0, -2000.0, -500.0, 0.0, 1000.0, 4000.0, 9000.0):
                f.na, f.k, f.water = na, k, water
                c = F.conc(f, LM)
                p = F.naPlasma(c)
                if p < F.HYPO_NA:
                    hypo += 1
                    d = F.dehydPct(f, W, 0)
                    r = F.defence(f, W)
                    t = F.thirstTarget(d, c, p, r)
                    if na + k > -179.2:
                        assert d == 0, (na, k, water)
                        assert r == 0, (na, k, water)
                        assert t == 0, (na, k, water)
                    else:
                        past += d > 0
                        assert r > 0, (na, k, water)
                        free = F.tVol(d)
                        capped = min(free, F.HYPO_CAP)
                        assert abs(t - (capped + r * (free - capped))) < 1e-12, (na, k, water)
                        if d >= 2 and r > 0.5:
                            relaxed += 1
                            assert t > AUTODRINK, (na, k, water)
    assert hypo > 10 and past > 0 and relaxed > 0


# --- the volume defence (Plan 11f Task 5b fix 1, review finding 1) -----------------------------------------------

def _heat(days=11):
    # heat work at MET 8 for 8 h/d (1 L/h of sweat at a drawn 37 mmol/L, 296 mmol/d before adaptation), no dietary
    # sodium, plain water to thirst; 11 days, McCance 1936's span (S1730)
    return simulate(days, 0.0, K_DIET, food=True, work_h=8)


SWEAT_BASE = 8 * 37.0                # the heat arm's daily sweat sodium at the draw, mmol
SWEAT_FLOOR = 0.325 * SWEAT_BASE     # past DEF_FULL: 96.2 mmol/d (08-sweat-sodium.md section 7, derived)


def heat_table(days):
    return [(i + 1, round(-d["na_end"], 0), round(-d["weu_end"], 0), round(d["water_end"], 0), round(d["dmax"], 2),
             round(d["drunk"], 2), round(d["sweat_na"], 1), round(d["pmin"], 1), round(d["p_end"], 1), d["grade"],
             d["g3"]) for i, d in enumerate(days)]


def test_heat_work_on_plain_water_holds_the_volume_and_dilutes_the_pool():
    # McCance's mode (S1729: "the volume of the body fluids was relatively well maintained but only at the expense of
    # the osmotic pressure"; S1731: the subjects drank freely): past the onset the relaxed cap lets drinking replace
    # the volume (Plan 11f Task 5b fix 2, review finding 1), so the water stays near the bounded set point and plasma
    # falls. Before the fix the cap stopped autodrink below 135 and the water ran to -20 kg, dehydPct 21, by day 10.
    # Plan 11f Task 5b fix 3: the sweat conserves sodium under the deficit, so past the bound the pool dilutes about
    # 2.3 mmol/L a day, not 7, and McCance's 11 days end at grade 1 (his subjects reached -11 %, S1729)
    days, _ = _heat()
    ecf = 0.20 * W * 1000                                       # S1714: 16000 g of ECF at 80 kg
    full = 0.20 * ecf                                           # S1729: McCance's plateau, by eye
    # the contraction stops near the bound: never past full defence, and within a tenth of it by day 10
    assert all(-d["weu_min"] < full for d in days), heat_table(days)
    assert -days[-1]["weu_end"] > 0.9 * full, heat_table(days)
    # the water deficit is bounded near the contraction: at each day's end the water sits within 2 % of body mass
    # (S0092's threshold) of the set point, so the body's loss is the contraction (McCance's 2-3 kg, S1729) and a
    # thirst-lag, not a running dehydration
    for d in days:
        assert d["weu_end"] - d["water_end"] < 0.02 * W * 1000, heat_table(days)
        assert -d["water_end"] < full + 0.02 * W * 1000, heat_table(days)
    # the deficit stays small: no minute of the ten days reaches S0709's 4 % strain point (the moodle's level 3), the
    # last days' worst minute is within half a point of day 4's (not running), and the severe-dehydration drain (10 %)
    # is never approached; the work hours' worst minute sits above 2 % because the sweat's sodium no longer lowers the
    # bounded set point, so all of the sweat's water reads as deficit until it is drunk back
    assert max(d["dmax"] for d in days) < 4, heat_table(days)
    assert max(d["dmax"] for d in days[7:]) - days[3]["dmax"] < 0.5, heat_table(days)
    # plasma falls through the grades: the day-end plasma falls every day past the onset, and the grades climb
    for a, b in zip(days[2:], days[3:]):
        assert b["p_end"] < a["p_end"], heat_table(days)
    for a, b in zip(days, days[1:]):
        assert b["grade"] >= a["grade"], heat_table(days)
    assert days[-1]["grade"] >= 1, heat_table(days)
    # the sweat conserves (Plan 11f Task 5b fix 3): the first day's sweat sodium already falls below the draw's 296
    # mmol/d, the second day's below the first's, and from day 3 it sits at the floor, 0.325 x 296 = 96.2 mmol/d
    # (derived), against McCance 1938's 162 -> 73 mmol per exposure (S1749) and Consolazio's 487 -> 71 mmol/d (S1761,
    # whose balance is not given)
    assert SWEAT_FLOOR < days[0]["sweat_na"] < 0.9 * SWEAT_BASE, heat_table(days)
    assert days[1]["sweat_na"] < days[0]["sweat_na"], heat_table(days)
    for d in days[2:]:
        assert abs(d["sweat_na"] - SWEAT_FLOOR) < 0.01 * SWEAT_FLOOR, heat_table(days)
    first = days[-1]["first_grade"]
    assert first is not None
    # the cumulative sodium loss at the first grade is of the order of McCance's 11-day total, 765 mEq (S1730, Table X)
    assert 765 / 2 <= first["loss"] <= 765 * 2, first
    # the depth against McCance's -11 % serum sodium (S1729; S1730's 340 -> 302 mg/100 cc) is a reading, reported
    assert days[-1]["at_mccance"] is not None


def test_onset_a_slow_depletion_loses_water_with_sodium_until_the_volume_defence():
    # Plan 11f Task 5b fix 2 (review finding 2, candidate C-12): the obligatory loss alone (S1665's 8 mmol/d, no sweat,
    # no dietary sodium or potassium) over 30 days, water evenly at 4 L/d (above the 2.43 L/d basal, Plan 15 Task 3; the kidney
    # clears the rest), so the onset is crossed gradually, about 57 g of isotonic contraction a day. Read a day apart
    days, hourly = simulate(30, 0.0, 0.0, False, water_load=(4000.0 / 24, 30 * DAY))
    iso = 1000 / 140                                            # S1683: g of water per mmol, isotonic
    cross = None
    for i in range(24, len(hourly)):
        a, b = hourly[i - 24], hourly[i]
        ds = (b["na"] + b["k"]) - (a["na"] + a["k"])
        dw = b["water"] - a["water"]
        assert ds < -7, (i, ds)                                 # the depletion runs every day
        if cross is None:
            if dw / ds < 0.9 * iso:
                cross = dict(h=i, contraction=-(a["water"] + b["water"]) / 2, ratio=dw / ds / iso)
            else:
                # S1729's first phase: water lost pari passu with sodium, no change in the osmotic pressure
                assert abs(b["p"] - 140) < 1, (i, b["p"])
    assert cross is not None, [round(r["water"]) for r in hourly[::24]]
    # S1717: rat vasopressin rose at a blood-volume fall of about 7 % (8 % or more significant), applied to ECF, a
    # game choice (16000 g at 80 kg); S1721: a sodium depletion of 1.6 kg body weight had raised plasma vasopressin
    assert 0.07 * 0.20 * W * 1000 <= cross["contraction"] <= 1600, cross


def test_a_potassium_surplus_carries_its_water_too():
    # the set point counts potassium (Plan 11f Task 5b): a game choice with no row (review finding 5). Its effect,
    # pinned: a 140 mmol/d potassium surplus holds 1000/140 g of water per retained mmol, as sodium does, and plasma
    # stays defended; without it the surplus would read hypertonic and drive drinking
    lo, _ = simulate(10, 120.0, 0.0, False)
    hi, _ = simulate(10, 120.0, 140.0, False)
    d_k = sum(d["k_mean"] for d in hi[7:]) / 3 - sum(d["k_mean"] for d in lo[7:]) / 3
    d_w = sum(d["water_mean"] for d in hi[7:]) / 3 - sum(d["water_mean"] for d in lo[7:]) / 3
    assert d_k > 100                                            # 140 mmol/d x K_TAU_H 24 h: about 140 mmol
    assert abs(d_w / d_k - 1000 / 140) < 0.5, d_w / d_k
    for d in hi[6:]:
        assert 138 <= d["p_end"] <= 142, d["p_end"]


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
    # drinking faster than the kidney clears dilutes plasma (S0102): Noakes's subjects fell 8 mmol/L, 144 to 136; the
    # fall is graded two-sided within 1.25x (Plan 11f Task 5b fix 1, review finding 7). The model starts at 140, so its
    # 3 h reading of 131.9 against Noakes's 136 is a named reading of the absolute level, not a pass band
    fall = 140 - hourly[2]["p"]
    assert 8 / 1.25 <= fall <= 8 * 1.25, hourly[2]["p"]


def test_the_heat_work_table_is_reported():
    # na deficit, contraction, water, worst dehydPct, drunk, sweat sodium, plasma min and end, grade, minutes at grade
    # 3; read against McCance's -11 % at 11 days (S1729) and his 765 mEq (S1730). The 17-day run is the lethal route's
    # reading: whether, and at what cumulative loss, the arm reaches grade 3
    days, _ = _heat()
    print("heat", heat_table(days), days[-1]["first_grade"], days[-1]["first_g3"], days[-1]["at_mccance"])
    assert len(days) == 11
    long, _ = _heat(17)
    print("heat17", heat_table(long)[11:], long[-1]["first_g3"])
    assert len(long) == 17


# --- sweat sodium adaptation (Plan 11f Task 5b fix 3, candidate C-14) ---------------------------------------------

def test_onset_the_sweat_sodium_fall_is_detectable_within_hours_of_a_deficit():
    # 296 mmol/d of sweat sodium spread evenly (1/3 L/h at MET 3 + 5/3, 8 L/d at the drawn 37), no intake: the fall is
    # read as detectable once the effective concentration is 15 % under the draw (S1762's ~15 % day-to-day variation
    # within a person; the criterion is the test's own). Graded within 2x of the 12-14 h onset: Cage and Dobson's
    # "about 12 hours after the beginning of an acclimatizing stress" (S1773) and Robinson 1956's decline from 14 h
    # (S1752). The model stores no lag, so the deficit's build-up is the only delay
    h = _shared()
    F = h.K.fluids
    f = F.new(LM, 1.0, 37.0)
    ctx = h.table(dict(lm=LM, met=3 + 5 / 3, thermoFluids=1.0, coldMult=1.0, ethanolAbsG=0.0, dehydPct=0.0))
    assert abs(F.sweatLh(ctx.met, 1.0, 1.0) * 24 * 37 - 296) < 1e-9
    onset = None
    for m in range(2 * DAY):
        F.losses(f, ctx, 1)
        if onset is None and F.naSweatEff(f) < 0.85 * 37:
            onset = dict(h=(m + 1) / 60, deficit=-f.na)
    assert onset is not None
    print("onset", onset)
    assert 12 / 2 <= onset["h"] <= 14 * 2, onset


@pytest.mark.parametrize("na_day", [304.0, 399.0])
def test_a_replete_worker_keeps_the_drawn_sweat_sodium(na_day):
    # Baker's "the presence of a salt deficit is required" (S1747; McCance 1938's generous arm 62 -> 70, S1749): the heat
    # arm with dietary sodium matching the sweat and obligatory losses (304 mmol/d) or Armstrong's 399 (S1750). The
    # balance dips within each shift, so the matched diet reads a few per cent under the draw; every day stays within
    # S1762's ~15 % day-to-day variation, and the generous diet sits at the draw. Armstrong's rise to 56 mM on 399 is
    # not modelled: the draw is the ceiling
    days, _ = simulate(10, na_day, K_DIET, food=True, work_h=8)
    print("replete", na_day, [(round(d["na_end"]), round(d["sweat_na"], 1), round(d["eff_min"], 2)) for d in days])
    for d in days:
        assert d["sweat_na"] >= 0.85 * SWEAT_BASE, (na_day, d["sweat_na"])
        assert d["grade"] == 0 and 138 <= d["p_end"] <= 142, (na_day, d["p_end"])
    if na_day == 399.0:
        for d in days[1:]:
            assert d["sweat_na"] > 0.995 * SWEAT_BASE, d["sweat_na"]


def test_the_sweat_reads_the_balance_not_the_diet():
    # the driver is the deficit (S1747, S1749, S1750), not the intake: a surplus carried into a salt-free shift keeps
    # the draw, and a deficit carried into a generous diet (Armstrong's 399 mmol/d) conserves until it is repaid
    surplus, _ = simulate(1, 0.0, K_DIET, food=True, work_h=8, na0=600.0)
    assert surplus[0]["eff_min"] == 37, surplus[0]["eff_min"]
    assert abs(surplus[0]["sweat_na"] - SWEAT_BASE) < 1e-6, surplus[0]["sweat_na"]
    deficit, _ = simulate(1, 399.0, K_DIET, food=True, work_h=8, na0=-600.0)
    assert deficit[0]["sweat_na"] < 0.6 * SWEAT_BASE, deficit[0]["sweat_na"]


def test_the_balance_table_is_reported():
    # the 10-day table the task reports (in, urine, plasma at day end, worst grade), kept readable in -s output
    for na in (0.0, 120.0, 220.0):
        days, _ = simulate(10, na, 0.0 if na == 0 else K_DIET)
        print("diet", na, _table(days))
        assert len(days) == 10
