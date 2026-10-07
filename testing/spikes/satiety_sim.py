"""Plan 10 Task S4 (fix round 1): hunger feel and the satiety default, an offline simulation across day lengths.

Simulates vanilla's HUNGER and five takeover HUNGER models over game days in one-game-minute steps, on
four day lengths, and writes one CSV per (day length, model, parameter) plus a summary per day length
and an index. Deterministic: no randomness, no clock, no environment read; the outputs are a pure
function of the repository's kernel files and the constants below.

The day lengths. The sandbox DayLength setting k maps to the real minutes of a game day through
SandboxOptions.getDayLengthMinutes (jar L556-L561: 1 -> 15, 2 -> 30, 3 -> 60, 4 -> 90; the harness
table at docs/platform/harness.md:153 reads 1 = 15 min, 4 = 1 h 30 m). Every name below is "a
<N>-minute day (DayLength <k>)". The fixture runs DayLength 4, the mod's acceptance profile
DayLength 1, vanilla's default is DayLength 3.

What depends on the day length. Every stat rate carries deltaMinutesPerDay, so hunger per game-second
is the same on every day (#2773). The health-from-food timer does not: it decays by the day length in
real minutes over 30 units per game-second (#0529; 0.5 on a 15-minute day, 2.0 on a 60-minute day,
3.0 on a 90-minute day). So vanilla's FOOD_EATEN freeze lasts six times longer in game time on a
15-minute day than on a 90-minute one, and only the models that read the timer move with the day.

Vanilla (each figure's register row beside it):
  * per game-second, dH = rate x StatsDecrease x appetite x (1 - H), appetite = the trait factor
    (Hearty Appetite 1.5, Light Eater 0.75; #0485, #0474, #2773, #2783);
  * rate: awake idle 9.6e-6 with the FOOD_EATEN moodle down (#0470) and 0 with it up (#0473);
    exercising 6.4e-6 down and 1.92e-5 up, so exercise never freezes (#0471, #2773); asleep 1.0e-6
    down and 0 up (#0472, #2783);
  * the moodle is up while healthFromFoodTimer > 0 (#0511), and the timer decays as above (#0529);
  * an eat adds getHungerChange x f to HUNGER, clamped to [0, 1] (#0017, #0021); getHungerChange is the
    script HungerChange / 100 (#0011) times 1.3 when cooked (#0029);
  * then JustAteFood: only when HUNGER sits at its minimum after that write, the timer becomes
    (int)(timer + |getHungerChange| x f x 13000), and again for a cooked item, capped at 11000
    (#0054, #0503; jar BodyDamage.JustAteFood @461 L650, @491 L653, @516 L656, @532 L660);
  * the HUNGRY moodle: strictly above 0.15, 0.25, 0.45, 0.70 (#0508, #0507).
  Each minute is integrated in closed form over its frozen and open seconds, so the step size never
  biases the curve.

The takeover (the mod) still runs vanilla's Eat and JustAteFood: the eat writes the item's relief onto
the stat the takeover last wrote, and the timer fills when that write leaves the stat at 0. The runner
models that for every takeover model (the column model_timer), so the freeze a takeover model reads is
the one its own displayed hunger earns. Every takeover model is capped at hungerCap 0.69
(K.fast.defaults, ruling 14) at energyState 1.

Models:
  vanilla            the reference above.
  stomach-<T>        the shipped design: the kernels loaded under lupa as
                     testing/tests/kernel/conftest.py loads them, a meal landed as NR_Server_Intake.lua
                     lands it (seed vector, instance scale 1, share 1, retention, K.stomach.ingest), the
                     stomach emptied every game minute, HUNGER = clamp(K.fast.hungerTarget(fill, 1), 0,
                     0.69). K.stomach.HALF_TIME_H = T; nothing in mod/ is edited. No freeze.
  decoupled          a satiety scalar S on [0, 1]: an eat raises it by the relief |getHungerChange| x f,
                     clamped at 1; it decays as vanilla's (1 - H) decays, with vanilla's awake, asleep
                     and exercise rates and the appetite traits, but never frozen; HUNGER = 1 - S.
  decoupled-freeze   the same S held while the timer is above 0 and the character is not exercising,
                     exactly vanilla's gate.
  blend-relief-b<B>  decoupled-freeze, with the relief scaled by the food's bulk: m = clamp(r / r0,
                     0.25, 4) ^ B, r = (bulk / FULL_BULK) / relief, r0 the menu day's total fill over
                     its total relief (so the day's mean is unchanged and only the ranking moves).
  blend-floor-w<W>-T<T>  decoupled-freeze, with the stomach (half-time T) as a floor on satiety:
                     HUNGER = 1 - max(S, W x fill).

Scenarios: `meals` (the menu day: 07:00, 12:00, 19:00, awake all day, the fixture's SleepNeeded false,
no exercise, no traits), `sleep` (asleep 23:00-07:00), `water` (0.3 L at 10:00, 16:00, 22:00; only
the stomach sees water), `light` (07:00 a banana, 12:00 bread slices, 19:00 opened beans: no meal
covers the hunger it meets, so no eat clamps S at 1 and the blends' bulk terms can act), and `active` (the code-path check: exercising 17:00-17:59 under Hearty
Appetite, vanilla and the two decoupled models only). Day 3 of 3 is reported.

Run: python testing/spikes/satiety_sim.py   (writes testing/spikes/out/)
"""
import csv
import glob
import io
import math
import os

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# --- vanilla constants (rows in the module docstring) ---
RATE_IDLE = 9.6e-6                # HungerIncrease, awake idle, moodle down (#0470)
RATE_FED = 0.0                    # HungerIncreaseWhenWellFed, idle or asleep with the moodle up (#0473, #2783)
RATE_ASLEEP = 1.0e-6              # HungerIncreaseWhileAsleep, moodle down (#0472)
RATE_EX_FED = 1.92e-5             # HungerIncreaseWhenExercise, exercising, moodle up (#0471)
RATE_EX = RATE_EX_FED / 3.0       # exercising, moodle down (#0471)
STATS_DECREASE = 1.0              # the default StatsDecrease setting 3 maps to 1.0 (#0483)
TIMER_PER_HUNGER = 13000.0        # getHealthFromFoodTimeByHunger (#0503)
TIMER_CAP = 11000.0               # (#0054)
COOKED_HUNGER = 1.3               # getHungerChange cooked ladder (#0029)
HUNGRY_AT = (0.15, 0.25, 0.45, 0.70)   # strict greater-than (#0508, #0507)
HEARTY = 1.5                      # Hearty Appetite (#0485)

# --- the day lengths: (real minutes per game day, DayLength setting); jar getDayLengthMinutes L556-L561 ---
DAY_LENGTHS = ((15, 1), (30, 2), (60, 3), (90, 4))

# --- the day ---
DAYS = 3                          # two warm-up days, the third reported
MEALS = {                          # game minute of the day -> [(fullType, script HungerChange, cooked)]
    7 * 60: [("Base.CerealBowl", -20.0, False), ("Base.Banana", -16.0, False)],
    12 * 60: [("Base.OpenBeans", -24.0, False), ("Base.BreadSlices", -10.0, False)],
    19 * 60: [("Base.Steak", -40.0, True)],
}
LIGHT = {                          # the `light` scenario: meals smaller than the hunger they meet, so no eat saturates
    7 * 60: [("Base.Banana", -16.0, False)],
    12 * 60: [("Base.BreadSlices", -10.0, False)],
    19 * 60: [("Base.OpenBeans", -24.0, False)],
}
DRINKS = {10 * 60: 0.3, 16 * 60: 0.3, 22 * 60: 0.3}   # litres of Water, the `water` scenario only
SLEEP = (23 * 60, 7 * 60)         # asleep 23:00-07:00, the `sleep` scenario only
EXERCISE = (17 * 60, 18 * 60)     # exercising 17:00-17:59, the `active` scenario only

SWEEP = [q / 4.0 for q in range(4, 33)]          # stomach half-times 1.00 to 8.00 h by 0.25
CSV_HALF_TIMES = (2.0, 4.25)                     # the shipped 2 h and the c57c82e sweep best, at every day
BETAS = (0.25, 0.5, 1.0)
FLOOR_WS = (0.25, 0.5, 0.75, 1.0)
FLOOR_T = 2.0                                    # the stomach keeps the shipped absorption half-time


def level(h):
    lv = 0
    for i, t in enumerate(HUNGRY_AT):
        if h > t:
            lv = i + 1
    return lv


def day_name(daylen, setting):
    return "a %d-minute day (DayLength %d)" % (daylen, setting)


def relief(script_hunger, cooked, ladder=True):
    """|getHungerChange| x f at f = 1 (ladder) or the raw |getHungChange| (no cooked ladder, #0002)."""
    r = abs(script_hunger) / 100.0
    if cooked and ladder:
        r = r * COOKED_HUNGER
    return r


def hunger_rate(asleep, exercising, fed):
    if asleep:
        return RATE_FED if fed else RATE_ASLEEP
    if exercising:
        return RATE_EX_FED if fed else RATE_EX
    return RATE_FED if fed else RATE_IDLE


def decay_factor(asleep, exercising, trait, fed_s):
    """exp of minus the integrated rate over one game minute: fed_s seconds with the moodle up, the rest down."""
    k_fed = hunger_rate(asleep, exercising, True)
    k_open = hunger_rate(asleep, exercising, False)
    return math.exp(-(k_fed * fed_s + k_open * (60.0 - fed_s)) * STATS_DECREASE * trait)


class Timer:
    """BodyDamage.healthFromFoodTimer: filled by JustAteFood, decayed by the day length / 30 per game-second."""

    def __init__(self, decay):
        self.value = 0.0
        self.decay = decay

    def just_ate(self, stat_after, script_hunger, cooked):
        if stat_after > 0.0:
            return
        add = relief(script_hunger, cooked) * TIMER_PER_HUNGER
        self.value = float(int(self.value + add))
        if cooked:
            self.value = float(int(self.value + add))
        if self.value > TIMER_CAP:
            self.value = TIMER_CAP

    def minute(self):
        fed_s = min(60.0, self.value / self.decay)
        self.value = max(0.0, self.value - self.decay * 60.0)
        return fed_s


def load_kernel():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    loader = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    files = ([os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
             + [os.path.join(SHARED, "NR_Data_Nutrients.lua")])
    for path in files:
        with open(path, encoding="utf-8") as fh:
            loader(fh.read(), "@" + os.path.basename(path))()
    return rt, rt.globals().NutritionRevamp


class Stomach:
    """The mod's stomach at one half-time (the kernels, unedited)."""

    def __init__(self, rt, NR, half_time):
        self.NR = NR
        self.K = NR.kernel
        self.half_time = half_time
        self.cap = self.K.fast.defaults().hungerCap
        self.stomach = self.K.stomach.seedFull(self.K.stomach.new())   # a new record starts full
        self.flags = rt.table()

    def eat(self, full_type, script_hunger, cooked):
        K = self.K
        seed = self.NR.data.nutrients.get(full_type)
        if seed is None:
            raise SystemExit("no seed vector for " + full_type)
        inst_base = script_hunger / 100.0            # an unscaled instance: instBase == scriptHunger
        vec = K.vector.meat(seed, inst_base, inst_base)
        vec = K.vector.add(K.vector.new(), vec, 1)   # share 1: the whole item
        self.flags.cooked = cooked
        self.flags.burnt = False
        self.flags.rotten = False
        self.flags.frozen = False
        vec = K.retention.apply(vec, self.flags)
        vec.ethanol = 0
        vec.caffeine = 0
        K.stomach.ingest(self.stomach, vec)
        return K.stomach.bulkOf(vec)

    def drink(self, litres):
        K = self.K
        vec = K.vector.add(K.vector.new(), self.NR.data.fluids.get("Water"), litres)
        K.stomach.ingest(self.stomach, vec)

    def minute(self):
        self.K.stomach.HALF_TIME_H = self.half_time   # set per step: several stomachs share one kernel
        self.K.stomach.empty(self.stomach, 1.0 / 60.0)
        return self.K.stomach.fill(self.stomach)


class Vanilla:
    """Vanilla HUNGER, integrated on H itself."""
    name = "vanilla"

    def __init__(self, *_):
        self.h = 0.0
        self.fill = None
        self.s = None

    def view(self):
        return self.h

    def eat(self, full_type, script_hunger, cooked):
        self.h = min(max(self.h - relief(script_hunger, cooked), 0.0), 1.0)

    def drink(self, litres):
        pass

    def minute(self, asleep, exercising, trait, fed_s):
        self.h = 1.0 - (1.0 - self.h) * decay_factor(asleep, exercising, trait, fed_s)
        return self.h


class StomachModel:
    def __init__(self, rt, NR, half_time):
        self.st = Stomach(rt, NR, half_time)
        self.cap = self.st.cap
        self.h = 0.0
        self.fill = 1.0
        self.s = None

    def view(self):
        return self.h

    def eat(self, full_type, script_hunger, cooked):
        self.st.eat(full_type, script_hunger, cooked)

    def drink(self, litres):
        self.st.drink(litres)

    def minute(self, asleep, exercising, trait, fed_s):
        self.fill = self.st.minute()
        self.h = min(max(self.st.K.fast.hungerTarget(self.fill, 1), 0.0), self.cap)
        return self.h


class Decoupled:
    """The satiety scalar S; freeze, relief getter, bulk modulation (beta) and fill floor (w) are parameters."""

    def __init__(self, rt, NR, freeze=False, ladder=True, beta=None, r0=None, bulks=None, floor_w=None,
                 floor_t=FLOOR_T):
        self.cap = NR.kernel.fast.defaults().hungerCap
        self.freeze = freeze
        self.ladder = ladder
        self.beta = beta
        self.r0 = r0
        self.bulks = bulks
        self.full_bulk = NR.kernel.stomach.FULL_BULK
        self.floor_w = floor_w
        self.st = Stomach(rt, NR, floor_t) if floor_w is not None else None
        self.s = 1.0                      # a new record: S = 1 (the migration seeds 1 - HUNGER instead)
        self.fill = 1.0 if self.st else None
        self.h = 0.0

    def view(self):
        return self.h

    def eat(self, full_type, script_hunger, cooked):
        r = relief(script_hunger, cooked, self.ladder)
        if self.beta is not None:
            ratio = (self.bulks[full_type] / self.full_bulk) / relief(script_hunger, cooked)
            r = r * min(max(ratio / self.r0, 0.25), 4.0) ** self.beta
        self.s = min(1.0, self.s + r)
        if self.st is not None:
            self.st.eat(full_type, script_hunger, cooked)

    def drink(self, litres):
        if self.st is not None:
            self.st.drink(litres)

    def minute(self, asleep, exercising, trait, fed_s):
        self.s = self.s * decay_factor(asleep, exercising, trait, fed_s if self.freeze else 0.0)
        s_eff = self.s
        if self.st is not None:
            self.fill = self.st.minute()
            s_eff = max(s_eff, self.floor_w * self.fill)
        self.h = min(max(1.0 - s_eff, 0.0), self.cap)   # (1 - S) x energyState + 0, energyState 1
        return self.h


def state_at(m, scenario):
    asleep = scenario == "sleep" and (m >= SLEEP[0] or m < SLEEP[1])
    exercising = scenario == "active" and EXERCISE[0] <= m < EXERCISE[1]
    trait = HEARTY if scenario == "active" else 1.0
    return asleep, exercising, trait


def run(model, daylen, scenario):
    """One model on one day length; returns the reported day's rows (minute, H, timer, S, fill)."""
    timer = Timer(daylen / 30.0)
    rows = []
    for day in range(DAYS):
        for m in range(1440):
            meal = (LIGHT if scenario == "light" else MEALS).get(m, ())
            if meal:
                stat = model.view()                 # the stat as the model last wrote it
                for full_type, hc, cooked in meal:
                    stat = min(max(stat - relief(hc, cooked), 0.0), 1.0)   # vanilla's Eat write (#0017, #0021)
                    timer.just_ate(stat, hc, cooked)                        # then JustAteFood (#0054)
                    model.eat(full_type, hc, cooked)
            if scenario == "water" and m in DRINKS:
                model.drink(DRINKS[m])
            asleep, exercising, trait = state_at(m, scenario)
            fed_s = timer.minute()                  # exercising, the fed seconds read RATE_EX_FED: no freeze
            h = model.minute(asleep, exercising, trait, fed_s)
            if day == DAYS - 1:
                rows.append((m, h, timer.value, model.s, model.fill))
    return rows


def compare(rows, van):
    counts = [0, 0, 0, 0, 0]
    agree = hungrier = lighter = 0
    mad = 0.0
    zeros = 0
    for r, v in zip(rows, van):
        lm, lv = level(r[1]), level(v[1])
        counts[lm] += 1
        agree += lm == lv
        hungrier += lm > lv
        lighter += lm < lv
        mad += abs(r[1] - v[1])
        zeros += r[1] <= 0.0
    pre = [rows[k - 1][1] for k in sorted(MEALS)]
    return {"counts": counts, "agree": agree, "hungrier": hungrier, "lighter": lighter,
            "mad": mad / len(rows), "zeros": zeros, "max": max(r[1] for r in rows), "pre": pre}


def fmt(x):
    return "%.6f" % x


def write_csv(path, rows, van):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["minute", "clock", "vanilla_hunger", "vanilla_level", "vanilla_food_timer", "model_hunger",
                "model_level", "model_food_timer", "model_satiety", "model_fill"])
    for r, v in zip(rows, van):
        m = r[0]
        w.writerow([m, "%02d:%02d" % (m // 60, m % 60), fmt(v[1]), level(v[1]), "%.1f" % v[2], fmt(r[1]),
                    level(r[1]), "%.1f" % r[2], "" if r[3] is None else fmt(r[3]),
                    "" if r[4] is None else fmt(r[4])])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def line(label, param, st, with_cmp=True):
    pre = " / ".join("%.3f" % x for x in st["pre"])
    tail = ("| %d | %d | %d | %.4f |" % (st["agree"], st["hungrier"], st["lighter"], st["mad"])) if with_cmp \
        else "| - | - | - | - |"
    return "| %s | %s | %s | %.3f | %s | %d %s" % (label, param, " | ".join(str(c) for c in st["counts"]),
                                                   st["max"], pre, st["zeros"], tail)


HEADER = ("| model | parameter | L0 | L1 | L2 | L3 | L4 | max hunger | hunger before 07:00 / 12:00 / 19:00 | "
          "minutes at hunger 0 | level agreement (min) | min hungrier than vanilla | min less hungry than vanilla | "
          "mean abs diff |")
RULE = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"


def g(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def main():
    os.makedirs(OUT, exist_ok=True)
    rt, NR = load_kernel()
    K = NR.kernel
    # the menu's bulks, landed once through the kernel (bulk does not depend on the half-time)
    probe = Stomach(rt, NR, 2.0)
    bulks = {}
    for meal in MEALS.values():
        for full_type, hc, cooked in meal:
            bulks[full_type] = probe.eat(full_type, hc, cooked)
    fill_total = sum(bulks[ft] / K.stomach.FULL_BULK for meal in MEALS.values() for ft, _, _ in meal)
    relief_total = sum(relief(hc, c) for meal in MEALS.values() for _, hc, c in meal)
    r0 = fill_total / relief_total
    kcal = sum(NR.data.nutrients.get(ft).calories for meal in MEALS.values() for ft, _, _ in meal)

    def make(kind, param=None):
        if kind == "vanilla":
            return Vanilla()
        if kind == "stomach":
            return StomachModel(rt, NR, param)
        if kind == "decoupled":
            return Decoupled(rt, NR)
        if kind == "decoupled-freeze":
            return Decoupled(rt, NR, freeze=True)
        if kind == "decoupled-freeze-raw":
            return Decoupled(rt, NR, freeze=True, ladder=False)
        if kind == "blend-relief":
            return Decoupled(rt, NR, freeze=True, beta=param, r0=r0, bulks=bulks)
        if kind == "blend-floor":
            return Decoupled(rt, NR, freeze=True, floor_w=param)
        raise ValueError(kind)

    index = []
    index.append("# S4 satiety simulation across day lengths: the index")
    index.append("")
    index.append("Generated by testing/spikes/satiety_sim.py (deterministic). One table per day length in "
                 "satiety-<N>-summary.md; the CSVs are satiety-<N>-<model>-<parameter>.csv. The menu day "
                 "(scenario `meals`) and the `light` menu (a banana, bread slices, opened beans), day 3 of 3, "
                 "energyState 1, no exercise, no traits. \"Hungrier\" and \"less hungry\" count the minutes the "
                 "model's HUNGRY level sits above or below vanilla's own level at that minute.")
    index.append("")
    index.append("Meal bulks (K.stomach.bulkOf, FULL_BULK %g): %s; the day's three meals carry %.2f kcal; "
                 "the menu's fill over relief r0 = %.4f (the blend-relief normaliser)." % (
                     K.stomach.FULL_BULK, ", ".join("%s %.3f" % (k, bulks[k]) for k in sorted(bulks)), kcal, r0))
    index.append("")
    index.append("| day | option | model | parameter | meals: level agreement (min) | meals: min hungrier | "
                 "meals: min less hungry | meals: minutes at hunger 0 (vanilla's) | meals: mean abs diff | "
                 "light: level agreement (min) | light: min hungrier | light: min less hungry | "
                 "light: minutes at hunger 0 (vanilla's) | light: mean abs diff |")
    index.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    for daylen, setting in DAY_LENGTHS:
        name = day_name(daylen, setting)
        van_rows = {sc: run(make("vanilla"), daylen, sc) for sc in ("meals", "light", "sleep", "water", "active")}
        van = van_rows["meals"]
        vst = compare(van, van)
        lines = []
        lines.append("# S4 satiety simulation on %s" % name)
        lines.append("")
        lines.append("Generated by testing/spikes/satiety_sim.py (deterministic). On %s one game minute lasts "
                     "%g real seconds; the food timer decays %g units per game-second (#0529), so the "
                     "11000 cap freezes hunger for %.1f game-minutes. Day 3 of 3; meals at 07:00, 12:00, "
                     "19:00; energyState 1; every takeover model capped at 0.69." % (
                         name, daylen * 60.0 / 1440.0, daylen / 30.0, TIMER_CAP / (daylen / 30.0) / 60.0))
        lines.append("")
        lines.append("## Scenario `meals` (the menu day: awake, no exercise, no traits)")
        lines.append("")
        lines.append(HEADER)
        lines.append(RULE)
        lines.append(line("vanilla", "-", vst, with_cmp=False))
        csvs = {("vanilla", "na"): van}

        res = {}
        for kind in ("decoupled", "decoupled-freeze", "decoupled-freeze-raw"):
            rows = run(make(kind), daylen, "meals")
            res[kind] = compare(rows, van)
            if kind != "decoupled-freeze-raw":
                csvs[(kind, "na")] = rows
            lines.append(line(kind, "-", res[kind]))

        sweep = []
        for t in SWEEP:
            rows = run(make("stomach", t), daylen, "meals")
            st = compare(rows, van)
            sweep.append((t, st))
            if t in CSV_HALF_TIMES:
                csvs[("stomach", g(t))] = rows
        best_t, best_st = min(sweep, key=lambda x: (round(x[1]["mad"], 12), x[0]))
        if best_t not in CSV_HALF_TIMES:
            csvs[("stomach", g(best_t))] = run(make("stomach", best_t), daylen, "meals")
        for t, st in sweep:
            if t in CSV_HALF_TIMES or t == best_t:
                tag = " (shipped)" if t == 2.0 else (" (sweep best)" if t == best_t else "")
                lines.append(line("stomach" + tag, "T %s h" % g(t), st))

        blends = []
        for b in BETAS:
            rows = run(make("blend-relief", b), daylen, "meals")
            st = compare(rows, van)
            blends.append(("blend-relief", "beta %s" % g(b), "b" + g(b), rows, st))
        for wv in FLOOR_WS:
            rows = run(make("blend-floor", wv), daylen, "meals")
            st = compare(rows, van)
            blends.append(("blend-floor", "w %s, T %s h" % (g(wv), g(FLOOR_T)), "w%s-T%s" % (g(wv), g(FLOOR_T)),
                           rows, st))
        for kind, label, tag, rows, st in blends:
            lines.append(line(kind, label, st))
        best_relief = min((x for x in blends if x[0] == "blend-relief"), key=lambda x: x[4]["mad"])
        best_floor = min((x for x in blends if x[0] == "blend-floor"), key=lambda x: x[4]["mad"])
        csvs[("blend-relief", best_relief[2])] = best_relief[3]
        csvs[("blend-floor", best_floor[2])] = best_floor[3]

        for (kind, tag), rows in csvs.items():
            write_csv(os.path.join(OUT, "satiety-%d-%s-%s.csv" % (daylen, kind, tag)), rows, van)

        lines.append("")
        lines.append("Rows: `decoupled-freeze-raw` is decoupled-freeze with the relief read off the raw "
                     "`getHungChange` (no cooked ladder, #0002), the getter `IN.readBefore` captures today. "
                     "\"Hungrier\" and \"less hungry\" count the minutes the model's HUNGRY level is above or "
                     "below vanilla's own level at that minute. Minutes at hunger 0 are counted at the end of "
                     "each game minute, so a freeze that ends inside a minute does not count that minute.")

        lines.append("")
        lines.append("## Other scenarios")
        lines.append("")
        lines.append(HEADER)
        lines.append(RULE)
        light = {}
        for sc in ("light", "sleep", "water", "active"):
            v = van_rows[sc]
            lines.append(line("vanilla", sc, compare(v, v), with_cmp=False))
            kinds = [("decoupled", None), ("decoupled-freeze", None)]
            if sc != "active":
                kinds += [("stomach", 2.0), ("stomach", best_t)]
            if sc == "light":
                kinds += [("blend-relief", b) for b in BETAS] + [("blend-floor", wv) for wv in FLOOR_WS]
            elif sc != "active":
                kinds += [("blend-relief", 1.0), ("blend-floor", 0.75)]
            for kind, p in kinds:
                rows = run(make(kind, p), daylen, sc)
                st = compare(rows, v)
                if sc == "light":
                    light[(kind, p)] = st
                label = kind if p is None else "%s %s" % (kind, g(p))
                lines.append(line(label, sc, st))
        lines.append("")
        lines.append("`sleep`: asleep 23:00-07:00. `water`: 0.3 L of water at 10:00, 16:00 and 22:00, which only "
                     "the stomach sees. `active`: exercising 17:00-17:59 under Hearty Appetite (x1.5), the "
                     "code-path check of the exercise rates and the appetite trait. `light`: a banana, bread slices "
                     "and opened beans, no meal covering the hunger it meets.")

        lines.append("")
        lines.append("## Stomach sweep, scenario `meals`, half-time 1.00 to 8.00 h by 0.25")
        lines.append("")
        lines.append("| half-time h | L0 | L1 | L2 | L3 | L4 | max hunger | minutes at hunger 0 | level agreement (min) | "
                     "min hungrier | min less hungry | mean abs diff |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for t, st in sweep:
            lines.append("| %.2f | %s | %.3f | %d | %d | %d | %d | %.4f |" % (
                t, " | ".join(str(c) for c in st["counts"]), st["max"], st["zeros"], st["agree"], st["hungrier"],
                st["lighter"], st["mad"]))
        lines.append("")
        lines.append("Least mean absolute difference in the sweep: %.2f h (%.4f; level agreement %d of 1440 minutes)."
                     % (best_t, best_st["mad"], best_st["agree"]))
        with open(os.path.join(OUT, "satiety-%d-summary.md" % daylen), "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(lines) + "\n")

        vl = compare(van_rows["light"], van_rows["light"])

        def idx(option, model, param, st, lst):
            index.append("| %d min (DayLength %d) | %s | %s | %s | %d | %d | %d | %d (%d) | %.4f | %d | %d | %d | %d (%d) | %.4f |" % (
                daylen, setting, option, model, param, st["agree"], st["hungrier"], st["lighter"], st["zeros"],
                vst["zeros"], st["mad"], lst["agree"], lst["hungrier"], lst["lighter"], lst["zeros"], vl["zeros"],
                lst["mad"]))
        idx("(a)", "decoupled-freeze", "-", res["decoupled-freeze"], light[("decoupled-freeze", None)])
        idx("(a) without the freeze", "decoupled", "-", res["decoupled"], light[("decoupled", None)])
        idx("(b) sweep best", "stomach", "T %s h" % g(best_t), best_st, light[("stomach", best_t)])
        idx("(b) shipped", "stomach", "T 2 h", dict(sweep)[2.0], light[("stomach", 2.0)])
        for kind, label, tag, rows, st in blends:
            p = float(label.split()[1].rstrip(","))
            idx("(c)", kind, label, st, light[(kind, p)])

    with open(os.path.join(OUT, "satiety-summary.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(index) + "\n")
    print("\n".join(index))


if __name__ == "__main__":
    main()
