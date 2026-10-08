"""Decision 2 (c) against Appendix D: the mod's minute-stepped satiety scalar beside an independent vanilla model.

Vanilla here is testing/spikes/satiety_sim.py's own model (its Timer and rates, #0470-#0473, #0503, #0054, #0529):
the moodle-up seconds of each minute freeze the decay, and an eat that takes HUNGER to 0 fills the food timer. The
mod's side is the kernel (K.satiety.add, bulkFactor, rate and step), one step a game minute, with the FOOD_EATEN
moodle read once a minute (fed = its own timer above 0 at the minute's start) and its timer filled by vanilla's
JustAteFood on the HUNGER the writer last wrote (Appendix D Question 4), capped at 0.69 like the writer.

The bulks are Appendix D's (satiety-summary.md: the menu's K.stomach.bulkOf on the 1.0.0 data, unrounded here) and
r0 is the kernel's R0, so the oracle does not move when the item pass or the intake moves a vector.
"""
import math
import os
import re

import pytest

RATE_IDLE, RATE_FED = 9.6e-6, 0.0
TIMER_PER_HUNGER, TIMER_CAP = 13000.0, 11000.0
HUNGRY_AT = (0.15, 0.25, 0.45, 0.70)
CAP = 0.69
BULK = {"CerealBowl": 8.1816, "Banana": 3.4710871, "OpenBeans": 6.71143, "BreadSlices": 2.9175714,
        "Steak": 3.1950376}
MENU = {7 * 60: [("CerealBowl", -20.0, False), ("Banana", -16.0, False)],
        12 * 60: [("OpenBeans", -24.0, False), ("BreadSlices", -10.0, False)],
        19 * 60: [("Steak", -40.0, True)]}
LIGHT = {7 * 60: [("Banana", -16.0, False)], 12 * 60: [("BreadSlices", -10.0, False)],
         19 * 60: [("OpenBeans", -24.0, False)]}
DAYS = {"DayLength1-15min": 15, "DayLength3-60min": 60, "DayLength4-90min": 90}


def level(h):
    return sum(1 for t in HUNGRY_AT if h > t)


def relief(script_hunger, cooked):
    r = abs(script_hunger) / 100.0
    return r * 1.3 if cooked else r


def fill(t, stat_after, r, cooked):
    """JustAteFood: the timer fills only when the eat leaves HUNGER at 0 (#0054, #0503), twice for a cooked item."""
    if stat_after > 0.0:
        return t
    t = float(int(t + r * TIMER_PER_HUNGER))
    if cooked:
        t = float(int(t + r * TIMER_PER_HUNGER))
    return min(t, TIMER_CAP)


def simulate(host, daylen, meals, beta, days=3):
    """The reported day's (vanilla HUNGER, the writer's HUNGER) per game minute."""
    decay = daylen / 30.0                                  # timer units a game-second (#0529)
    rates = host.call("satiety.defaults")
    full = host.K.stomach.FULL_BULK
    s_v, s_m, t_v, t_m, h_m = 1.0, 1.0, 0.0, 0.0, 0.0
    out = []
    for day in range(days):
        for minute in range(1440):
            for food, script_hunger, cooked in meals.get(minute, []):
                r = relief(script_hunger, cooked)
                s_v = min(1.0, s_v + r)
                t_v = fill(t_v, 1.0 - s_v, r, cooked)
                stat = min(max(h_m - r, 0.0), 1.0)         # vanilla's Eat on the HUNGER the writer last wrote
                t_m = fill(t_m, stat, r, cooked)
                h_m = stat
                s_m = host.call("satiety.add", s_m, r, host.call("satiety.bulkFactor", BULK[food], full, r, beta))
            fed_s = min(60.0, t_v / decay)
            s_v *= math.exp(-(RATE_FED * fed_s + RATE_IDLE * (60.0 - fed_s)))
            t_v = max(0.0, t_v - decay * 60.0)
            rate = host.call("satiety.rate", rates, False, False, t_m > 0)
            s_m = host.call("satiety.step", s_m, 60, rate, 1, 1)
            t_m = max(0.0, t_m - decay * 60.0)
            h_m = min(max(1.0 - s_m, 0.0), CAP)
            if day == days - 1:
                out.append((1.0 - s_v, h_m))
    return out


def compare(rows):
    agree = sum(1 for v, m in rows if level(v) == level(m))
    hungrier = sum(1 for v, m in rows if level(m) > level(v))
    lighter = sum(1 for v, m in rows if level(m) < level(v))
    mad = sum(abs(v - m) for v, m in rows) / len(rows)
    return agree, hungrier, lighter, mad


@pytest.mark.parametrize("day", sorted(DAYS))
@pytest.mark.parametrize("menu", ["menu", "light"])
def test_beta_zero_is_vanilla_within_a_minutes_lag(host, day, menu):
    agree, hungrier, lighter, mad = compare(simulate(host, DAYS[day], MENU if menu == "menu" else LIGHT, 0.0))
    assert mad <= 2e-3, (day, menu, mad)
    assert hungrier + lighter <= 10, (day, menu, hungrier, lighter)


@pytest.mark.parametrize("day", sorted(DAYS))
@pytest.mark.parametrize("beta", [0.25, 0.5])
def test_on_the_main_menu_every_beta_is_option_a(host, day, beta):
    """Appendix D: every main-menu meal saturates S, so the bulk factor never shows ("= (a)")."""
    assert simulate(host, DAYS[day], MENU, beta) == simulate(host, DAYS[day], MENU, 0.0)


@pytest.mark.parametrize("day", sorted(DAYS))
@pytest.mark.parametrize("beta, agree, lighter, mad", [(0.25, 1329, 111, 0.0348), (0.5, 963, 477, 0.0708)])
def test_the_light_menu_reproduces_appendix_d(host, day, beta, agree, lighter, mad):
    """Appendix D's (c) rows: the light menu at beta 0.25 is less hungry than vanilla for 111 minutes (MAD 0.0348),
    at beta 0.5 for 477 (0.0708), on every day length (no light meal saturates, so no freeze fires)."""
    a, hungrier, l, m = compare(simulate(host, DAYS[day], LIGHT, beta))
    assert (a, hungrier, l) == (agree, 0, lighter)
    assert round(m, 4) == mad


def test_the_default_beta_is_the_decisions_floor():
    from .server_host import REPO
    txt = open(os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt"),
               encoding="utf-8").read()
    block = re.search(r"option NR\.SatietyBulk\s*\{(.*?)\}", txt, re.S).group(1)
    assert float(re.search(r"default\s*=\s*([0-9.]+)", block).group(1)) == 0.25
    assert float(re.search(r"min\s*=\s*([0-9.]+)", block).group(1)) == 0.25
    assert float(re.search(r"max\s*=\s*([0-9.]+)", block).group(1)) == 0.5
