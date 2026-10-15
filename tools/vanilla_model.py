#!/usr/bin/env python3
"""A small model of vanilla Project Zomboid's hunger, thirst, weight and Strength experience (Plan 14 Task 2).

The model feeds the player guide's vanilla-versus-mod charts with the vanilla side's `vanilla-model` series.
Each formula is a small named function carrying the register rows it rests on in `FORMULAS`, keyed by the
source map's names (VM1 to VM16 and JT1, `docs/superpowers/research/2026-10-15-mod-guide/source-map.md` § 4).
It is pure Python, deterministic, and runs no game: every rate is per game-second and is integrated over
segments that end at each output step (`dt_min`), each event time and each activity boundary.

    simulate(scenario) -> {series name: [(game hour, value), ...]}

A scenario is
    {"hours": float, "dt_min": float,
     "start": {...state...}, "settings": {...}, "events": [{"t_h": float, "kind": ..., ...}, ...]}

`start` keys (all optional): hunger, thirst, weight_kg (80), calories, carbs, lipids, proteins, health (100),
food_timer, fatigue, intoxication, strength_level (5), strength_xp (that level's total), strength_up_timer
(-50000), strength_mod (0).
`settings` keys (all optional): stats_decrease (the sandbox enum 1-5, default 3), day_length_min (90, the
DayLength 4 default), appetite (1.0; Hearty Appetite 1.5, Light Eater 0.75), thirst_trait (1.0), xp_multiplier
(1.0), sleep_allowed (False, the dedicated-server default; fatigue holds only when True), energy_multiplier (1.0),
protein_factor (None: read off the protein store at each grant; a number pins it, as the H3 and S4 lines do).

Event kinds:
  eat       hunger_change (stat units, e.g. -0.24) or hunger_script (script units, e.g. -24); calories, carbs,
            lipids, proteins; fraction (1.0); state fresh|cooked|burnt|stale|rotten (fresh); cooked (False,
            the timer doubling, also implied by state cooked); thirst_change (stat units, 0).
  drink     litres; fluid water|coffee|beer, or the per-litre values thirst_per_l, fatigue_per_l, alcohol_per_l.
  exercise  mode pushups: reps (60), xp_per_rep (6), duration_min (0, the set's time under the Fitness action);
            mode walking|running|sprinting|swing|action: duration_min, and calories_modifier for an action.
  sleep     duration_h.

Series (one point per output step, the start included): hunger, thirst, weight_kg, calories_store, carbs,
lipids, proteins, strength_xp, strength_level, health, food_timer, food_eaten_level, hungry_level,
thirst_level, fatigue, intoxication.

Usage: python tools/vanilla_model.py   (prints the source map's headline vanilla numbers)"""
import math

# ---- constants, each read off the register row its formula names ----------------------------------------
HUNGER_INCREASE = 9.6e-6             # #0470 per game-second, awake idle, food-eaten moodle down
HUNGER_EXERCISE = 1.92e-5            # #0471 HungerIncreaseWhenExercise; ÷3 with the moodle down
HUNGER_EXERCISE_DIV = 3.0            # #0471, #2773
HUNGER_ASLEEP = 1.0e-6               # #0472
HUNGER_WELL_FED = 0.0                # #0473 HungerIncreaseWhenWellFed
STATS_DECREASE = {1: 2.0, 2: 1.6, 3: 1.0, 4: 0.8, 5: 0.65}  # #0483
HUNGRY_THRESHOLDS = (0.15, 0.25, 0.45, 0.70)    # #0508, strict
THIRST_THRESHOLDS = (0.12, 0.25, 0.70, 0.84)    # #0509, strict

THIRST_INCREASE = 8.0e-6             # #0476
THIRST_ASLEEP = 1.0e-6               # #0477
WATER_THIRST_PER_L = -0.5            # #2928: ThirstChange -50 a litre, ÷100

FOOD_TIMER_PER_HUNGER = 13000.0      # #0503 getHealthFromFoodTimeByHunger
FOOD_TIMER_COOKED = 2.0              # #0054
FOOD_TIMER_CAP = 11000.0             # #0054, #0530
FOOD_TIMER_DECAY_PER_DAYMIN = 1.0 / 30.0   # #0529: day length (real minutes) / 30 units a game-second
FOOD_EATEN_THRESHOLDS = (0.0, 1600.0, 3200.0, 4800.0)   # #0511
MULT_UNITS_PER_DAYMIN_HOUR = 120.0   # #2922: the multiplier sums to 120 x minutesPerDay over a game-hour

COOKED_HUNGER = 1.3                  # #0029
BURNT_HUNGER_DIV = 3.0               # #0030
STALE_HUNGER_DIV = 1.3               # #0031
ROTTEN_HUNGER_DIV = 2.2              # #0032
HUNGER_FLOOR = 0.01                  # #0030-#0032
SCRIPT_SCALE = 100.0                 # #0011

BURN_ASLEEP = 0.003                  # #0454 kcal a game-second at 80 kg
BURN_IDLE = 0.016                    # #0455
BURN_MOVING = 0.13                   # #0458
BURN_WALK_MOD = 0.6                  # #0457
BURN_SPRINT_MOD = 1.3                # #0459
SWING_MOD = 8.0                      # #0460
FITNESS_MOD = 3.0                    # #2187
BURN_REF_KG = 80.0                   # #0453, #0461

CARB_DRAIN = 0.0035                  # #0069, #1193 a game-second
LIPID_DRAIN = 0.00113
PROTEIN_DRAIN = 0.00086
CAL_MIN, CAL_MAX = -2200.0, 3700.0   # #0022
MACRO_MIN, MACRO_MAX = -500.0, 1000.0    # #0023

GAIN_BASE = 1000.0                   # #0149
GAIN_SLOPE = 40.0
LOSS_REF_KG = 70.0                   # #0151
LOSS_SLOPE = 30.0
GAIN_RATE = 1.3e-5                   # #0152 kg a game-second
GAIN_FULL_CAL = 4000.0
LOSS_RATE = 8.5e-6                   # #0154
LOSS_FULL_CAL = 2500.0
MACRO_X3, MACRO_X2 = 700.0, 400.0    # #0153
MACRO_X3_MULT, MACRO_X2_MULT = 3.0, 2.0

CREATION_WEIGHTS = {"OBESE": 105.0, "OVERWEIGHT": 95.0, "UNDERWEIGHT": 70.0,
                    "VERY_UNDERWEIGHT": 60.0, "EMACIATED": 50.0, None: 80.0}   # #0533; none 80 (#0149 anchor)

SEVERE_HEALTH = 0.0165               # #0516 healthReductionFromSevereBadMoodles
HUNGER_HEALTH_DIV = 50.0             # #0516
THIRST_HEALTH_DIV = 10.0             # #0516

XP_PER_REP = 6.0                     # #3844: 60 reps, 360 a set
REPS_PER_SET = 60
PROTEIN_LO, PROTEIN_HI, PROTEIN_LOW = 50.0, 300.0, -300.0   # #2112
PROTEIN_HIGH_FACTOR, PROTEIN_LOW_FACTOR = 1.5, 0.7
LEVEL_COSTS = (1500, 3000, 6000, 9000, 18000, 30000, 60000, 90000, 120000, 150000)   # #2102

RUST_TICK = 10.0                     # #2154 a ten-minute pass
RUST_START = 20000.0                 # #2151
RUST_BUCKET = 1200.0
RUST_RESET = 31000.0
RUST_XP = -1.0
RUST_GRANT = -3000.0                 # #2156
RUST_FLOOR = -50000.0                # #2152, #2156

START_LEVEL = 5                      # #2104
MUSCLE_BOOSTS = {"WEAK": -5, "FEEBLE": -2, "STOUT": 2, "STRONG": 4}   # JT1 (T2.1)

COFFEE_FATIGUE_PER_L = -0.10         # #2949: fatigueChange -10 a litre, ÷100
BEER_ALCOHOL_PER_L = 0.05            # #2926
DRUNK_INCREASE = 400.0               # #2923, #2919
DRUNK_HUNGER_HI, DRUNK_HUNGER_MID = 0.8, 0.6
DRUNK_FACTOR_HI, DRUNK_FACTOR_MID = 1.1, 1.25
DRUNK_REDUCTION = 0.0042             # #2919, #2918 per multiplier unit

FLUIDS = {
    "water": {"thirst_per_l": WATER_THIRST_PER_L},
    "coffee": {"fatigue_per_l": COFFEE_FATIGUE_PER_L},
    "beer": {"alcohol_per_l": BEER_ALCOHOL_PER_L},
}

FORMULAS = {
    "VM1": {"claims": ["#0470", "#0474", "#0489", "#0490", "#0473", "#0524", "#0525", "#0483", "#2773"],
            "doc": "Hunger awake: dH/dt = 9.6e-6 x the StatsDecrease multiplier x (1 - H) x the appetite trait a "
                   "game-second, solved exactly over a segment; 0 while the food-eaten timer is above 0 and the "
                   "character is not exercising. hunger_rate_awake, hunger_step."},
    "VM2": {"claims": ["#0471", "#2774", "#2775", "#0472", "#2783", "#0498"],
            "doc": "Hunger exercising (running while moving, or a swing): 1.92e-5 / 3 with the moodle down, 1.92e-5 "
                   "with it up, with the appetite damping; asleep 1.0e-6 x (1 - H), 0 with the moodle up."},
    "VM3": {"claims": ["#0054", "#3597", "#0503", "#0530", "#0529", "#0511", "#0528"],
            "doc": "The food-eaten timer: after an eat, only when HUNGER is at its minimum 0, timer += "
                   "abs(hungerChange) x f x 13000, x2 cooked, capped at 11000; it decays day-length-minutes / 30 "
                   "units a game-second (3.0 at DayLength 4); the moodle level reads it against 0, 1600, 3200, 4800. "
                   "food_timer_fill, food_timer_decay_per_s, food_eaten_level."},
    "VM4": {"claims": ["#0006", "#0011", "#0021", "#0029", "#0030", "#0031", "#0032", "#0003"],
            "doc": "The eat: HUNGER += getHungerChange x f, clamped [0, 1]; getHungerChange is the script value / 100 "
                   "modified by state: cooked x1.3 (precedence), burnt max(|h|/3, 0.01), stale max(|h|/1.3, 0.01), "
                   "rotten max(|h|/2.2, 0.01), sign kept. effective_hunger_change."},
    "VM5": {"claims": ["#0476", "#0477", "#0491", "#0496", "#2765", "#2766", "#2928", "#0508", "#0509"],
            "doc": "Thirst: dT/dt = 8.0e-6 x StatsDecrease x thirst trait awake, 1.0e-6 asleep, linear, clamped [0, 1]; "
                   "water -0.5 THIRST a litre; HUNGRY above 0.15/0.25/0.45/0.70 and THIRST above 0.12/0.25/0.70/0.84, "
                   "strict. thirst_rate, moodle_level."},
    "VM6": {"claims": ["#0453", "#0454", "#0455", "#0456", "#0457", "#0458", "#0459", "#0460", "#0461", "#0187",
                       "#0462", "#2187", "#2720", "#0464"],
            "doc": "Calorie burn a game-second x (weight / 80): asleep 0.003 and idle 0.016, both x the action "
                   "modifier (Fitness 3, reading 0.5, building or swinging 8) x the thermoregulator energy "
                   "multiplier (>= 1, taken as 1); walking 0.13 x 0.6, running 0.13, sprinting 0.13 x 1.3, none of "
                   "which the modifier or the energy term reaches. burn_rate."},
    "VM7": {"claims": ["#0036", "#0069", "#1193", "#0168", "#0022", "#0023"],
            "doc": "The stores: calories and the macros += the item's unmodified values x f at the eat; carbohydrate, "
                   "lipid and protein drain 0.0035, 0.00113, 0.00086 a game-second; calories clamped [-2200, 3700], "
                   "macros [-500, 1000]."},
    "VM8": {"claims": ["#0149", "#0151", "#0152", "#0153", "#0154", "#0161", "#0166",
                       "#0158", "#0159", "#0160", "#0164"],
            "doc": "Weight: above 1000 + (w - 80) x 40 kcal gain 1.3e-5 x min(1, cal / 4000) kg a game-second, x3 "
                   "with carbohydrate or lipid above 700 g, x2 above 400 g; below min(0, (w - 70) x 30) lose 8.5e-6 x "
                   "min(1, |cal| / 2500). weight_rate."},
    "VM9": {"claims": ["#0155", "#0531", "#3069", "#0533", "#0534"],
            "doc": "Weight bands, inclusive at both ends: Emaciated <= 50, Very Underweight (50, 65], Underweight "
                   "(65, 75], none (75, 85), Overweight [85, 100), Obese >= 100; creation weights Obese 105, "
                   "Overweight 95, Underweight 70, Very Underweight 60, Emaciated 50, none 80. weight_band."},
    "VM10": {"claims": ["#0516", "#0518", "#0519", "#2353", "#2354", "#2721", "#0515", "#2385"],
             "doc": "Starvation and health: HUNGRY 4 costs 0.0165 / 50 and THIRST 4 0.0165 / 10 health a multiplier "
                    "unit, 120 x day-length minutes units a game-hour (3.564 and 17.82 at DayLength 4); at level 4 "
                    "(tier 3) nothing regenerates, asleep included; the model regenerates nothing at any tier "
                    "(health is plotted only on the way down). health_loss_per_hour."},
    "VM11": {"claims": ["#3844", "#2112", "#3835", "#3836", "#2102", "#2109", "#2122", "#2161", "#2874"],
             "doc": "Strength experience: 6 a push-up rep, 360 a set to exhaustion at Fitness 5; x1.5 with the protein "
                    "store strictly between 50 and 300, x0.7 strictly below -300; x the sandbox multiplier; per-level "
                    "costs 1500 ... 150000 (37500 at level 5, 487500 at 10); nothing past level 10; dropped while "
                    "asleep. strength_xp_grant, protein_factor, total_xp_for_level, level_for_xp."},
    "VM12": {"claims": ["#2151", "#2152", "#2154", "#2155", "#2156", "#2868"],
             "doc": "Rust, each ten game minutes: the timer += 10; above 20000, entering a new 1200-unit bucket takes "
                    "1 XP (while XP > 0) and the level drops only when XP falls below that level's total; the timer "
                    "resets to 0 once above 31000; each positive Strength grant takes 3000 off it, floor -50000 "
                    "(the default). rust_tick."},
    "VM13": {"claims": ["#2104", "#2157", "T2.1", "T2.2"],
             "doc": "Trait start levels: Strength is seeded at 5, then each trait's and the profession's XPBoosts "
                    "are added, clamped to [0, 10], and the perk raised one LevelPerk at a time with the "
                    "experience set to the level's total; the LevelPerk event remaps the band trait. "
                    "start_strength_level."},
    "VM14": {"claims": ["#0475", "#0501", "#0500", "#0488"],
             "doc": "What hunger does not read: getHungerMultiplier is a hard 1.0 and no hunger term reads fatigue, "
                    "sleep debt, weight or calories; the burn reads no hunger. Structural: hunger_step takes none "
                    "of them."},
    "VM15": {"claims": ["#2949", "#2270"],
             "doc": "Coffee: FATIGUE += fatigueChange x litres, Coffee -10 a litre / 100 = -0.1 a litre; the value "
                    "holds only with sleep allowed and needed, otherwise FATIGUE stays at its reset. The model does "
                    "not accumulate awake fatigue (#2270's term is not modelled). fatigue_change."},
    "VM16": {"claims": ["#2923", "#2926", "#2919", "#2922", "#2918", "#2950", "#2951"],
             "doc": "Intoxication: a drink adds 400 x alcohol x (1.1 above 0.8 HUNGER, 1.25 above 0.6 up to 0.8), Beer "
                    "0.05 alcohol a litre; it decays 0.0042 a multiplier unit, 0.504 x day-length minutes a game-hour "
                    "(45.36 at DayLength 4), floor 0. intoxication_gain, intoxication_decay_per_hour."},
    "JT1": {"claims": ["T2.1", "T2.2"],
            "doc": "The muscle traits' Strength XPBoosts from the 42.21 trait script (Weak -5, Feeble -2, Stout +2, "
                   "Strong +4) and applyTraits' arithmetic (seed 5, add, clamp [0, 10]): vanilla start levels Weak 0, "
                   "Feeble 3, none 5, Stout 7, Strong 9. MUSCLE_BOOSTS, start_strength_level."},
}

S_PER_H = 3600.0


# ---- VM1, VM2, VM14: hunger -----------------------------------------------------------------------------
def stats_decrease_multiplier(enum=3):
    """#0483: the StatsDecrease sandbox enum's multiplier."""
    return STATS_DECREASE[enum]


def hunger_rate_awake(hunger, timer_up=False, exercising=False, stats_mult=1.0, appetite=1.0):
    """VM1/VM2/#2773: the awake hunger rate a game-second."""
    if exercising:
        base = HUNGER_EXERCISE if timer_up else HUNGER_EXERCISE / HUNGER_EXERCISE_DIV
        return base * stats_mult * (1.0 - hunger) * appetite
    if timer_up:
        return HUNGER_WELL_FED * stats_mult
    return HUNGER_INCREASE * stats_mult * (1.0 - hunger) * appetite


def hunger_rate_asleep(hunger, timer_up=False, stats_mult=1.0, appetite=1.0):
    """VM2/#2783: the asleep hunger rate a game-second (0 with the moodle up at the shipped constant)."""
    if timer_up:
        return HUNGER_WELL_FED * HUNGER_ASLEEP * stats_mult * stats_mult
    return HUNGER_ASLEEP * stats_mult * (1.0 - hunger) * appetite


def _hunger_k(asleep, exercising, timer_up, stats_mult, appetite):
    """The first-order constant k of dH/dt = k (1 - H) for the branch, 0 for a frozen branch."""
    if asleep:
        return 0.0 if timer_up else HUNGER_ASLEEP * stats_mult * appetite
    if exercising:
        base = HUNGER_EXERCISE if timer_up else HUNGER_EXERCISE / HUNGER_EXERCISE_DIV
        return base * stats_mult * appetite
    return 0.0 if timer_up else HUNGER_INCREASE * stats_mult * appetite


def hunger_step(hunger, seconds, k):
    """VM1 (#0489): the exact solution H(t) = 1 - (1 - H0) e^(-k t)."""
    if k == 0.0:
        return hunger
    return 1.0 - (1.0 - hunger) * math.exp(-k * seconds)


def hours_to_hunger(target, start=0.0, stats_mult=1.0, appetite=1.0):
    """Game-hours for awake idle hunger to reach `target` from `start` (#0492-#0495)."""
    k = HUNGER_INCREASE * stats_mult * appetite
    return -math.log((1.0 - target) / (1.0 - start)) / k / S_PER_H


# ---- VM3: the food-eaten timer ------------------------------------------------------------------------------
def food_timer_fill(timer, hunger_after, hunger_change, fraction=1.0, cooked=False):
    """VM3 (#0054, #3597): JustAteFood's fill, gated on HUNGER at its minimum after the eat's stat writes."""
    if hunger_after > 0.0:
        return timer
    add = abs(hunger_change) * fraction * FOOD_TIMER_PER_HUNGER
    if cooked:
        add *= FOOD_TIMER_COOKED
    return min(timer + add, FOOD_TIMER_CAP)


def food_timer_decay_per_s(day_length_min=90.0):
    """VM3 (#0529): units a game-second, day-length minutes / 30."""
    return day_length_min * FOOD_TIMER_DECAY_PER_DAYMIN


def food_eaten_level(timer):
    """VM3 (#0511): the FOOD_EATEN moodle level, strict thresholds 0, 1600, 3200, 4800."""
    return sum(1 for t in FOOD_EATEN_THRESHOLDS if timer > t)


def multiplier_units_per_hour(day_length_min=90.0):
    """#2922: the game-time multiplier sums to 120 x minutesPerDay over a game-hour."""
    return MULT_UNITS_PER_DAYMIN_HOUR * day_length_min


# ---- VM4: the eat -------------------------------------------------------------------------------------------
def effective_hunger_change(h, state="fresh"):
    """VM4: Food.getHungerChange's state ladder on the instance value h (script / 100)."""
    if state == "cooked":
        return h * COOKED_HUNGER
    div = {"burnt": BURNT_HUNGER_DIV, "stale": STALE_HUNGER_DIV, "rotten": ROTTEN_HUNGER_DIV}.get(state)
    if div is None:
        return h
    return math.copysign(max(abs(h) / div, HUNGER_FLOOR), h)


def script_to_stat(script_value):
    """#0011: HungerChange and ThirstChange are divided by 100 at instantiation."""
    return script_value / SCRIPT_SCALE


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


# ---- VM5: thirst and the moodles ------------------------------------------------------------------------------
def thirst_rate(asleep=False, stats_mult=1.0, thirst_trait=1.0):
    """VM5 (#2765, #2766): linear, a game-second."""
    return (THIRST_ASLEEP if asleep else THIRST_INCREASE) * stats_mult * thirst_trait


def moodle_level(value, thresholds):
    """VM5: the level is the count of thresholds strictly below the value (#0508, #0509)."""
    return sum(1 for t in thresholds if value > t)


# ---- VM6: calorie burn ----------------------------------------------------------------------------------------
def burn_rate(state="idle", weight=80.0, modifier=1.0, energy=1.0):
    """VM6: kcal a game-second. `modifier` (an action's caloriesModifier, 8 for a swing) and `energy` reach
    only the asleep and idle branches (#0187, #0462)."""
    w = weight / BURN_REF_KG
    if state == "running":
        return BURN_MOVING * w
    if state == "sprinting":
        return BURN_MOVING * BURN_SPRINT_MOD * w
    if state == "walking":
        return BURN_MOVING * BURN_WALK_MOD * w
    if state == "asleep":
        return BURN_ASLEEP * modifier * energy * w
    return BURN_IDLE * modifier * energy * w


# ---- VM8: weight ----------------------------------------------------------------------------------------------
def gain_threshold(weight):
    return GAIN_BASE + (weight - BURN_REF_KG) * GAIN_SLOPE


def loss_threshold(weight):
    return min(0.0, (weight - LOSS_REF_KG) * LOSS_SLOPE)


def weight_rate(weight, calories, carbs=0.0, lipids=0.0):
    """VM8: kg a game-second."""
    if calories > gain_threshold(weight):
        r = GAIN_RATE * min(1.0, calories / GAIN_FULL_CAL)
        if carbs > MACRO_X3 or lipids > MACRO_X3:
            r *= MACRO_X3_MULT
        elif carbs > MACRO_X2 or lipids > MACRO_X2:
            r *= MACRO_X2_MULT
        return r
    if calories < loss_threshold(weight):
        return -LOSS_RATE * min(1.0, abs(calories) / LOSS_FULL_CAL)
    return 0.0


# ---- VM9: bands -----------------------------------------------------------------------------------------------
def weight_band(weight):
    """VM9 (#0531, #3069): the band trait applyTraitFromWeight would set, None in (75, 85)."""
    if weight >= 100.0:
        return "OBESE"
    if weight >= 85.0:
        return "OVERWEIGHT"
    if weight <= 50.0:
        return "EMACIATED"
    if weight <= 65.0:
        return "VERY_UNDERWEIGHT"
    if weight <= 75.0:
        return "UNDERWEIGHT"
    return None


def creation_weight(band=None):
    """VM9 (#0533): applyWeightFromTraits; none 80."""
    return CREATION_WEIGHTS[band]


# ---- VM10: health ---------------------------------------------------------------------------------------------
def health_loss_per_hour(hungry_level, thirst_level, day_length_min=90.0):
    """VM10 (#0516, #0518): health lost a game-hour from the level-4 terms."""
    per_unit = 0.0
    if hungry_level >= 4:
        per_unit += SEVERE_HEALTH / HUNGER_HEALTH_DIV
    if thirst_level >= 4:
        per_unit += SEVERE_HEALTH / THIRST_HEALTH_DIV
    return per_unit * multiplier_units_per_hour(day_length_min)


# ---- VM11, VM12, VM13: Strength --------------------------------------------------------------------------------
def total_xp_for_level(level):
    """#2102: PerkFactory's cumulative total for a Strength level."""
    return float(sum(LEVEL_COSTS[:level]))


def level_for_xp(xp):
    """The level whose total the experience has reached."""
    level = 0
    while level < 10 and xp >= total_xp_for_level(level + 1):
        level += 1
    return level


def protein_factor(proteins):
    """VM11 (#2112): strictly between 50 and 300 x1.5, strictly below -300 x0.7."""
    f = 1.0
    if PROTEIN_LO < proteins < PROTEIN_HI:
        f *= PROTEIN_HIGH_FACTOR
    if proteins < PROTEIN_LOW:
        f *= PROTEIN_LOW_FACTOR
    return f


def strength_xp_grant(xp, amount, proteins=0.0, xp_multiplier=1.0, asleep=False, factor=None):
    """VM11: (new xp, the change made). Dropped asleep (#2161), discarded at the level-10 total (#2109).
    `factor` pins the protein factor (a chart's fixed-factor line); None reads it off the protein store."""
    if asleep:
        return xp, 0.0
    cap = total_xp_for_level(10)
    if amount >= 0 and xp >= cap:
        return xp, 0.0
    a = amount * (protein_factor(proteins) if factor is None else factor) * xp_multiplier
    new = clamp(xp + a, 0.0, cap)
    return new, new - xp


def pushup_set_xp(reps=REPS_PER_SET, xp_per_rep=XP_PER_REP):
    """#3844: one set's raw Strength amount (360 at 60 reps)."""
    return reps * xp_per_rep


def rust_tick(timer, mod, xp, level):
    """VM12: one ten-minute pass of XpUpdate.everyTenMinutes on Strength; returns (timer, mod, xp, level)."""
    timer += RUST_TICK
    if timer > RUST_START and mod != math.floor(timer / RUST_BUCKET):
        mod = math.floor(timer / RUST_BUCKET)
        if xp > 0:
            xp = max(0.0, xp + RUST_XP)
        if 1 <= level <= 10 and xp < total_xp_for_level(level):
            level -= 1
    if timer > RUST_RESET:
        timer = 0.0
    return timer, mod, xp, level


def rust_after_grant(timer):
    """#2156: a positive grant takes 3000 off the timer, floored at -50000."""
    return max(RUST_FLOOR, timer + RUST_GRANT)


def start_strength_level(trait=None, profession_boost=0):
    """VM13/JT1: applyTraits' seed 5 plus the boosts, clamped to [0, 10]."""
    level = START_LEVEL + MUSCLE_BOOSTS.get(trait, 0) + profession_boost
    return max(0, min(10, level))


# ---- VM15, VM16: coffee and intoxication -------------------------------------------------------------------------
def fatigue_change(litres, fatigue_per_l=COFFEE_FATIGUE_PER_L):
    """VM15 (#2949)."""
    return fatigue_per_l * litres


def intoxication_gain(alcohol, hunger):
    """VM16 (#2923): JustDrankBoozeFluid's add for an alcohol amount (litres x per-litre alcohol)."""
    f = 1.0
    if hunger > DRUNK_HUNGER_HI:
        f = DRUNK_FACTOR_HI
    elif hunger > DRUNK_HUNGER_MID:
        f = DRUNK_FACTOR_MID
    return DRUNK_INCREASE * alcohol * f


def intoxication_decay_per_hour(day_length_min=90.0):
    """VM16 (#2922): 0.0042 a multiplier unit."""
    return DRUNK_REDUCTION * multiplier_units_per_hour(day_length_min)


# ---- the simulation -------------------------------------------------------------------------------------------
SERIES = ("hunger", "thirst", "weight_kg", "calories_store", "carbs", "lipids", "proteins", "strength_xp",
          "strength_level", "health", "food_timer", "food_eaten_level", "hungry_level", "thirst_level",
          "fatigue", "intoxication")
MOVING_MODES = ("walking", "running", "sprinting")


def _intervals(events):
    """Sleep and timed activity intervals as (start_s, end_s, kind, event)."""
    out = []
    for e in events:
        t0 = e["t_h"] * S_PER_H
        if e["kind"] == "sleep":
            out.append((t0, t0 + e["duration_h"] * S_PER_H, "sleep", e))
        elif e["kind"] == "exercise":
            dur = e.get("duration_min", 0.0) * 60.0
            if dur > 0:
                out.append((t0, t0 + dur, "exercise", e))
    return out


def _activity(t, intervals):
    """(asleep, burn state, modifier, exercising-for-hunger) for the segment starting at t."""
    asleep, state, mod, exercising = False, "idle", 1.0, False
    for t0, t1, kind, e in intervals:
        if not (t0 <= t < t1):
            continue
        if kind == "sleep":
            asleep = True
            continue
        mode = e.get("mode", "pushups")
        if mode in MOVING_MODES:
            state = mode
            exercising = exercising or mode in ("running", "sprinting")   # #2774: a player running while moving
        elif mode == "swing":
            mod, exercising = SWING_MOD, True
        elif mode == "pushups":
            mod = FITNESS_MOD
        else:
            mod = e.get("calories_modifier", 1.0)
    if asleep:
        return True, "asleep", 1.0, False
    return False, state, mod, exercising


def simulate(scenario):
    """Run a scenario; see the module docstring."""
    hours, dt_s = float(scenario["hours"]), float(scenario["dt_min"]) * 60.0
    st = dict(scenario.get("start", {}))
    cfg = dict(scenario.get("settings", {}))
    events = sorted(scenario.get("events", []), key=lambda e: e["t_h"])
    sm = stats_decrease_multiplier(cfg.get("stats_decrease", 3))
    dlm = float(cfg.get("day_length_min", 90.0))
    appetite, thirst_trait = cfg.get("appetite", 1.0), cfg.get("thirst_trait", 1.0)
    xp_mult, energy = cfg.get("xp_multiplier", 1.0), cfg.get("energy_multiplier", 1.0)
    sleep_allowed = cfg.get("sleep_allowed", False)
    fixed_factor = cfg.get("protein_factor")

    s = {
        "hunger": st.get("hunger", 0.0), "thirst": st.get("thirst", 0.0), "weight_kg": st.get("weight_kg", 80.0),
        "calories_store": st.get("calories", 0.0), "carbs": st.get("carbs", 0.0), "lipids": st.get("lipids", 0.0),
        "proteins": st.get("proteins", 0.0), "health": st.get("health", 100.0),
        "food_timer": st.get("food_timer", 0.0), "fatigue": st.get("fatigue", 0.0),
        "intoxication": st.get("intoxication", 0.0),
    }
    level = int(st.get("strength_level", START_LEVEL))
    s["strength_level"] = level
    s["strength_xp"] = float(st.get("strength_xp", total_xp_for_level(level)))
    rust_timer, rust_mod = st.get("strength_up_timer", RUST_FLOOR), st.get("strength_mod", 0)

    intervals = _intervals(events)
    decay = food_timer_decay_per_s(dlm)
    units_per_s = multiplier_units_per_hour(dlm) / S_PER_H
    out = {k: [] for k in SERIES}

    def record(t):
        s["food_eaten_level"] = food_eaten_level(s["food_timer"])
        s["hungry_level"] = moodle_level(s["hunger"], HUNGRY_THRESHOLDS)
        s["thirst_level"] = moodle_level(s["thirst"], THIRST_THRESHOLDS)
        for k in SERIES:
            out[k].append((t / S_PER_H, s[k]))

    def advance(t, seconds):
        """Integrate one segment with the activity at its start held."""
        asleep, state, mod, exercising = _activity(t, intervals)
        timer_up = s["food_timer"] > 0.0
        # hunger: frozen part while the timer runs out, then the moodle-down branch (VM1-VM3)
        rem = seconds
        if timer_up:
            up_s = min(rem, s["food_timer"] / decay)
            s["hunger"] = hunger_step(s["hunger"], up_s, _hunger_k(asleep, exercising, True, sm, appetite))
            rem -= up_s
        if rem > 0:
            s["hunger"] = hunger_step(s["hunger"], rem, _hunger_k(asleep, exercising, False, sm, appetite))
        s["food_timer"] = max(0.0, s["food_timer"] - decay * seconds)
        # thirst (VM5)
        s["thirst"] = clamp(s["thirst"] + thirst_rate(asleep, sm, thirst_trait) * seconds, 0.0, 1.0)
        # stores and weight (VM6-VM8)
        w = s["weight_kg"]
        s["weight_kg"] = w + weight_rate(w, s["calories_store"], s["carbs"], s["lipids"]) * seconds
        burn = burn_rate(state, w, mod, energy)
        s["calories_store"] = clamp(s["calories_store"] - burn * seconds, CAL_MIN, CAL_MAX)
        s["carbs"] = clamp(s["carbs"] - CARB_DRAIN * seconds, MACRO_MIN, MACRO_MAX)
        s["lipids"] = clamp(s["lipids"] - LIPID_DRAIN * seconds, MACRO_MIN, MACRO_MAX)
        s["proteins"] = clamp(s["proteins"] - PROTEIN_DRAIN * seconds, MACRO_MIN, MACRO_MAX)
        # intoxication (VM16)
        s["intoxication"] = max(0.0, s["intoxication"] - DRUNK_REDUCTION * units_per_s * seconds)

    def apply(e, t):
        nonlocal rust_timer
        asleep = _activity(t, intervals)[0]
        kind = e["kind"]
        if kind == "eat":
            f = e.get("fraction", 1.0)
            h = e["hunger_change"] if "hunger_change" in e else script_to_stat(e.get("hunger_script", 0.0))
            state = e.get("state", "fresh")
            hc = effective_hunger_change(h, state)
            s["hunger"] = clamp(s["hunger"] + hc * f, 0.0, 1.0)
            s["thirst"] = clamp(s["thirst"] + e.get("thirst_change", 0.0) * f, 0.0, 1.0)
            s["calories_store"] = clamp(s["calories_store"] + e.get("calories", 0.0) * f, CAL_MIN, CAL_MAX)
            for key, src in (("carbs", "carbs"), ("lipids", "lipids"), ("proteins", "proteins")):
                s[key] = clamp(s[key] + e.get(src, 0.0) * f, MACRO_MIN, MACRO_MAX)
            cooked = e.get("cooked", state == "cooked")
            s["food_timer"] = food_timer_fill(s["food_timer"], s["hunger"], hc, f, cooked)
        elif kind == "drink":
            litres = e["litres"]
            vals = dict(FLUIDS.get(e.get("fluid", "water"), {}))
            vals.update({k: e[k] for k in ("thirst_per_l", "fatigue_per_l", "alcohol_per_l") if k in e})
            s["thirst"] = clamp(s["thirst"] + vals.get("thirst_per_l", 0.0) * litres, 0.0, 1.0)
            if sleep_allowed:
                s["fatigue"] = clamp(s["fatigue"] + fatigue_change(litres, vals.get("fatigue_per_l", 0.0)), 0.0, 1.0)
            if vals.get("alcohol_per_l", 0.0):
                s["intoxication"] += intoxication_gain(vals["alcohol_per_l"] * litres, s["hunger"])
        elif kind == "exercise" and e.get("mode", "pushups") == "pushups":
            for _ in range(int(e.get("sets", 1))):
                raw = pushup_set_xp(e.get("reps", REPS_PER_SET), e.get("xp_per_rep", XP_PER_REP))
                s["strength_xp"], made = strength_xp_grant(s["strength_xp"], raw, s["proteins"], xp_mult, asleep,
                                                           fixed_factor)
                if made > 0:
                    rust_timer = rust_after_grant(rust_timer)
                while s["strength_level"] < 10 and s["strength_xp"] >= total_xp_for_level(s["strength_level"] + 1):
                    s["strength_level"] += 1   # #2122

    # segment boundaries: output steps, events, interval ends, ten-minute rust passes
    end = hours * S_PER_H
    n_steps = int(round(end / dt_s))
    grid = [i * dt_s for i in range(n_steps + 1)]
    cuts = set(grid)
    for e in events:
        cuts.add(e["t_h"] * S_PER_H)
    for t0, t1, _, _ in intervals:
        cuts.update((t0, t1))
    tick = 600.0
    cuts.update(i * tick for i in range(1, int(end // tick) + 1))
    cuts = sorted(c for c in cuts if 0.0 <= c <= end)
    grid_set = set(grid)
    ev_i = 0
    t = 0.0
    for c in cuts:
        if c > t:
            # health (VM10) at the segment's starting levels
            hl0 = moodle_level(s["hunger"], HUNGRY_THRESHOLDS)
            tl0 = moodle_level(s["thirst"], THIRST_THRESHOLDS)
            seconds = c - t
            advance(t, seconds)
            s["health"] = max(0.0, s["health"] - health_loss_per_hour(hl0, tl0, dlm) * seconds / S_PER_H)
            t = c
        if c > 0 and abs(c / tick - round(c / tick)) < 1e-9:
            rust_timer, rust_mod, s["strength_xp"], s["strength_level"] = rust_tick(
                rust_timer, rust_mod, s["strength_xp"], s["strength_level"])
        while ev_i < len(events) and events[ev_i]["t_h"] * S_PER_H <= c + 1e-9:
            apply(events[ev_i], c)
            ev_i += 1
        if c in grid_set:
            record(c)
    return out


def main():
    print("hunger moodle levels at", [round(hours_to_hunger(x), 2) for x in HUNGRY_THRESHOLDS], "h")
    print("idle burn at 80 kg", round(burn_rate() * 86400, 1), "kcal a game-day")
    print("start levels", {k: start_strength_level(k) for k in (None, "WEAK", "FEEBLE", "STOUT", "STRONG")})


if __name__ == "__main__":
    main()
