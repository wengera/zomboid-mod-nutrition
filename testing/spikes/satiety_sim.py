"""Plan 10 Task S4: hunger feel and the satiety default -- an offline simulation.

Simulates vanilla's HUNGER and the mod's takeover HUNGER over game days in one-game-minute steps, at
DayLength = 1 (a 60-minute real day, so one game minute is 2.5 real seconds), and writes one CSV per
half-time plus a summary. Deterministic: no randomness, no clock, no environment read; the outputs
are a pure function of the repository's kernel files and the constants below.

Vanilla (each figure's register row is named beside it; the memo section carries the citations):
  * awake, idle, FOOD_EATEN down: dH/dt = 9.6e-6 x (1 - H) per game-second at StatsDecrease 3
    (#0470, #0474, #2773); closed form per step, so the step size never biases the curve;
  * asleep, FOOD_EATEN down: 1.0e-6 x (1 - H) per game-second (#0472, #2783);
  * FOOD_EATEN up (healthFromFoodTimer > 0): hunger frozen, awake or asleep (#0473, #0524, #2783);
  * the timer decays DayLength/30 = 2.0 units per game-second on the 60-minute day (#0529);
  * an eat adds getHungerChange x f to HUNGER, clamped to [0, 1] (#0017, #0021); getHungerChange is
    the script HungerChange / 100 (#0011) times 1.3 when cooked (#0029);
  * then JustAteFood: only when HUNGER is at its minimum after that write, the timer gains
    (int)(|getHungerChange| x f x 13000), doubled when cooked, capped at 11000 (#0054, #0503, #0637);
  * the HUNGRY moodle: strictly above 0.15, 0.25, 0.45, 0.70 (#0508, #0507).
  The plan's "linear rise" reference (vanilla_lin) is also written: 0.03456 per game-hour with no
  appetite damping and no freeze, the per-hour figure at H = 0 (#0574).

The mod: the repository's kernels loaded under lupa as testing/tests/kernel/conftest.py loads them
(NR_Core.lua then every NR_Kernel*.lua, sorted), plus NR_Data_Nutrients.lua for the seed vectors,
without the coverage hook. A meal lands as NR_Server_Intake.lua lands it: the seed vector
(NR.data.nutrients.get), the instance scale K.vector.meat(seed, instBase, scriptHunger) = 1 for an
unscaled item, times the share 1, the four macros as Eat delivers them (the seed's, which the item
pass writes), K.retention.apply with the item's cooked flag, then K.stomach.ingest (IN.land's last
step; ethanol and caffeine are zero for these foods). Each game minute the stomach empties over
1/60 h (NR_Server_Kinetics.lua's step), and HUNGER = clamp(K.fast.hungerTarget(fill, 1), 0,
hungerCap) with hungerCap 0.69 (K.fast.defaults, ruling 14), as K.fast.step writes it.
K.stomach.HALF_TIME_H is set per run; nothing in mod/ is edited.

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
HUNGER_INCREASE = 9.6e-6          # per game-second, awake idle, FOOD_EATEN down (#0470)
HUNGER_ASLEEP = 1.0e-6            # per game-second, asleep, FOOD_EATEN down (#0472)
STATS_DECREASE = 1.0              # the default StatsDecrease setting 3 maps to 1.0 (#0483)
TIMER_DECAY_PER_S = 60.0 / 30.0   # DayLength 60 real minutes / 30 (#0529)
TIMER_PER_HUNGER = 13000.0        # getHealthFromFoodTimeByHunger (#0503)
TIMER_CAP = 11000.0               # (#0054)
COOKED_HUNGER = 1.3               # getHungerChange cooked ladder (#0029)
HUNGRY_AT = (0.15, 0.25, 0.45, 0.70)   # strict greater-than (#0508, #0507)
LINEAR_PER_H = HUNGER_INCREASE * 3600.0   # 0.03456 per game-hour at H = 0 (#0574)

# --- the day ---
DAYS = 3                          # two warm-up days, the third reported
MEALS = {                          # game minute of the day -> [(fullType, script HungerChange, cooked)]
    7 * 60: [("Base.CerealBowl", -20.0, False), ("Base.Banana", -16.0, False)],
    12 * 60: [("Base.OpenBeans", -24.0, False), ("Base.BreadSlices", -10.0, False)],
    19 * 60: [("Base.Steak", -40.0, True)],
}
DRINKS = {10 * 60: 0.3, 16 * 60: 0.3, 22 * 60: 0.3}   # litres of Water, the "water" scenario only
SLEEP = (23 * 60, 7 * 60)         # asleep from 23:00 to 07:00, the "sleep" scenario only

HALF_TIMES = (2.0, 3.0, 4.0, 5.0, 6.0, 8.0)   # the plan's 2-6, plus the draft dial's upper bound 8


def level(h):
    lv = 0
    for i, t in enumerate(HUNGRY_AT):
        if h > t:
            lv = i + 1
    return lv


def load_kernel():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    loader = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    files = ([os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
             + [os.path.join(SHARED, "NR_Data_Nutrients.lua")])
    for path in files:
        with open(path, encoding="utf-8") as fh:
            loader(fh.read(), "@" + os.path.basename(path))()
    return rt, rt.globals().NutritionRevamp


class Mod:
    """The mod's stomach and HUNGER view at one half-time."""

    def __init__(self, rt, NR, half_time):
        self.NR = NR
        self.K = NR.kernel
        self.K.stomach.HALF_TIME_H = half_time
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
        self.K.stomach.empty(self.stomach, 1.0 / 60.0)
        fill = self.K.stomach.fill(self.stomach)
        h = self.K.fast.hungerTarget(fill, 1)
        return min(max(h, 0.0), self.cap), fill, self.stomach.bulk


class Vanilla:
    """Vanilla HUNGER with the appetite damping and the FOOD_EATEN freeze."""

    def __init__(self):
        self.h = 0.0
        self.timer = 0.0
        self.lin = 0.0

    def eat(self, script_hunger, cooked):
        hc = script_hunger / 100.0
        if cooked:
            hc = hc * COOKED_HUNGER
        self.h = min(max(self.h + hc, 0.0), 1.0)
        self.lin = min(max(self.lin + hc, 0.0), 1.0)
        if self.h <= 0.0:
            add = abs(hc) * TIMER_PER_HUNGER
            if cooked:
                add = add * 2.0
            self.timer = float(int(self.timer + add))
            if self.timer > TIMER_CAP:
                self.timer = TIMER_CAP

    def minute(self, asleep):
        frozen_s = min(60.0, self.timer / TIMER_DECAY_PER_S)
        self.timer = max(0.0, self.timer - TIMER_DECAY_PER_S * 60.0)
        open_s = 60.0 - frozen_s
        rate = (HUNGER_ASLEEP if asleep else HUNGER_INCREASE) * STATS_DECREASE
        self.h = 1.0 - (1.0 - self.h) * math.exp(-rate * open_s)
        self.lin = min(1.0, self.lin + (LINEAR_PER_H / 60.0 if not asleep else HUNGER_ASLEEP * 60.0))
        return self.h


class Decoupled:
    """The proposed decoupled satiety term (the memo's design): a satiety scalar S on [0, 1] that an eat
    raises by the hunger relief vanilla's Eat writes (|getHungerChange| x f, cooked x 1.3), clamped at
    1 so an overshoot is discarded as vanilla discards it (#0021), and that decays first-order at
    vanilla's own rate (awake 9.6e-6, asleep 1.0e-6 per game-second, x StatsDecrease); HUNGER = 1 - S
    at energyState 1. No FOOD_EATEN freeze: the only term it drops from vanilla."""

    def __init__(self):
        self.s = 1.0

    def eat(self, script_hunger, cooked):
        hc = abs(script_hunger) / 100.0
        if cooked:
            hc = hc * COOKED_HUNGER
        self.s = min(1.0, self.s + hc)

    def minute(self, asleep):
        rate = (HUNGER_ASLEEP if asleep else HUNGER_INCREASE) * STATS_DECREASE
        self.s = self.s * math.exp(-rate * 60.0)
        return 1.0 - self.s


def asleep_at(mod_minute, scenario):
    if scenario != "sleep":
        return False
    return mod_minute >= SLEEP[0] or mod_minute < SLEEP[1]


def run(rt, NR, half_time, scenario):
    van = Vanilla()
    dec = Decoupled()
    mod = Mod(rt, NR, half_time)
    rows = []
    bulks = {}
    for day in range(DAYS):
        for m in range(1440):
            for full_type, hc, cooked in MEALS.get(m, ()):
                b = mod.eat(full_type, hc, cooked)
                bulks[full_type] = b
                van.eat(hc, cooked)
                dec.eat(hc, cooked)
            if scenario == "water" and m in DRINKS:
                mod.drink(DRINKS[m])
            asleep = asleep_at(m, scenario)
            vh = van.minute(asleep)
            dh = dec.minute(asleep)
            mh, fill, bulk = mod.minute()
            if day == DAYS - 1:
                rows.append((m, vh, level(vh), van.lin, level(van.lin), van.timer, mh, level(mh), fill, bulk,
                             dh, level(dh)))
    return rows, bulks


def fmt(x):
    return "%.6f" % x


def write_csv(path, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["minute", "clock", "vanilla_hunger", "vanilla_level", "vanilla_linear_hunger",
                "vanilla_linear_level", "vanilla_food_timer", "mod_hunger", "mod_level", "mod_fill", "mod_bulk",
                "decoupled_hunger", "decoupled_level"])
    for (m, vh, vl, lh, ll, timer, mh, ml, fill, bulk, dh, dl) in rows:
        w.writerow([m, "%02d:%02d" % (m // 60, m % 60), fmt(vh), vl, fmt(lh), ll, "%.1f" % timer,
                    fmt(mh), ml, fmt(fill), fmt(bulk), fmt(dh), dl])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def per_level(rows, idx):
    counts = [0, 0, 0, 0, 0]
    for r in rows:
        counts[r[idx]] += 1
    return counts


def stats(rows, h_idx=6, l_idx=7):
    van = per_level(rows, 2)
    lin = per_level(rows, 4)
    mod = per_level(rows, l_idx)
    agree = sum(1 for r in rows if r[2] == r[l_idx])
    mae = sum(abs(r[1] - r[h_idx]) for r in rows) / len(rows)
    pre = {}
    for meal in sorted(MEALS):
        r = rows[meal - 1]
        pre[meal] = (r[1], r[h_idx])
    zv = sum(1 for r in rows if r[1] <= 0.0)
    zm = sum(1 for r in rows if r[h_idx] <= 0.0)
    return van, lin, mod, agree, mae, max(r[1] for r in rows), max(r[h_idx] for r in rows), pre, zv, zm


def row_line(scenario, t, model, counts, vmax, pre_vals, zeros, agree="-", mae="-"):
    pv = " / ".join("%.3f" % x for x in pre_vals)
    return "| %s | %s | %s | %s | %.3f | %s | %d | %s | %s |" % (
        scenario, t, model, " | ".join(str(c) for c in counts), vmax, pv, zeros, agree, mae)


def main():
    os.makedirs(OUT, exist_ok=True)
    rt, NR = load_kernel()
    th = HUNGRY_AT[0]
    # Plan 11 draft Task 9 Step 2: T* = H_vanilla / log2(1 / (1 - threshold)); H_vanilla first-order (#0492)
    h_first = -math.log(1.0 - th) / (HUNGER_INCREASE * STATS_DECREASE) / 3600.0
    t_star = round((h_first / math.log2(1.0 / (1.0 - th))) * 4.0) / 4.0
    halves = list(HALF_TIMES) + [t_star]
    lines = []
    lines.append("# S4 satiety simulation: minutes of the reported game day at each HUNGRY level")
    lines.append("")
    lines.append("Generated by testing/spikes/satiety_sim.py (deterministic). DayLength = 1: one game minute is 2.5 real seconds, so divide game minutes by 24 for real minutes.")
    lines.append("Day %d of %d simulated (two warm-up days); meals at 07:00, 12:00, 19:00. Scenario `meals`: awake all day (the fixture default SleepNeeded false). `sleep`: asleep 23:00-07:00 (vanilla's asleep rate; the mod's stomach empties unchanged). `water`: `meals` plus 0.3 L of water at 10:00, 16:00 and 22:00. The mod at energyState 1." % (DAYS, DAYS))
    lines.append("")
    lines.append("H_vanilla (hunger 0 to the first moodle, 0.15, first-order, no freeze) = %.4f game-hours; the Plan 11 draft Task 9 formula gives T* = %.2f h (rounded to 0.25 h), simulated as the last half-time." % (h_first, t_star))
    meal_bulk = None
    table = []
    for scenario in ("meals", "sleep", "water"):
        first = True
        for t in halves:
            rows, bulks = run(rt, NR, t, scenario)
            if scenario == "meals":
                write_csv(os.path.join(OUT, "satiety-%g.csv" % t), rows)
                meal_bulk = bulks
            van, lin, mod, agree, mae, vmax, mmax, pre, zv, zm = stats(rows)
            if first:
                first = False
                table.append(row_line(scenario, "-", "vanilla", van, vmax, [pre[k][0] for k in sorted(pre)], zv))
                if scenario == "meals":
                    table.append("| meals | - | vanilla, linear (the plan's reference) | %s | - | - | - | - | - |" % " | ".join(str(c) for c in lin))
                dv, dl, dm, dag, dmae, _, dmax, dpre, _, dz = stats(rows, 10, 11)
                table.append(row_line(scenario, "-", "decoupled satiety (proposed)", dm, dmax, [dpre[k][1] for k in sorted(dpre)], dz, str(dag), "%.4f" % dmae))
            table.append(row_line(scenario, "%g" % t, "mod", mod, mmax, [pre[k][1] for k in sorted(pre)], zm, str(agree), "%.4f" % mae))
    total_kcal = 0.0
    for meal in MEALS.values():
        for full_type, hc, cooked in meal:
            total_kcal += NR.data.nutrients.get(full_type).calories
    lines.append("")
    lines.append("Meal bulks (K.stomach.bulkOf of each landed vector, FULL_BULK 8): " + ", ".join(
        "%s %.3f" % (k, meal_bulk[k]) for k in sorted(meal_bulk)) + "; the day's three meals carry %.2f kcal." % total_kcal)
    lines.append("")
    lines.append("| scenario | half-time h | model | L0 | L1 | L2 | L3 | L4 | max hunger | hunger before 07:00 / 12:00 / 19:00 | minutes at hunger 0 | level agreement with vanilla (min) | mean abs diff |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    lines.extend(table)
    # the sweep: every 0.25 h from 1 to 8, the meals scenario only (no CSVs)
    lines.append("")
    lines.append("## Sweep, scenario `meals`, half-time 1.00 to 8.00 h by 0.25")
    lines.append("")
    lines.append("| half-time h | L0 | L1 | L2 | L3 | L4 | max hunger | minutes at hunger 0 | level agreement (min) | mean abs diff |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    best = None
    for q in range(4, 33):
        t = q / 4.0
        rows, _ = run(rt, NR, t, "meals")
        van, lin, mod, agree, mae, vmax, mmax, pre, zv, zm = stats(rows)
        lines.append("| %.2f | %s | %.3f | %d | %d | %.4f |" % (t, " | ".join(str(c) for c in mod), mmax, zm, agree, mae))
        if best is None or mae < best[1] - 1e-12:
            best = (t, mae, agree)
    lines.append("")
    lines.append("Least mean absolute difference in the sweep: %.2f h (%.4f; level agreement %d of 1440 minutes)." % best)
    with open(os.path.join(OUT, "satiety-summary.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
