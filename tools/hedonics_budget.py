"""The food hedonics budget oracle (Plan 19 Task 5; spec docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md
section B.3): seven reference diets over 14 days, the mod's food mood against vanilla's model of the same eats.

    python tools/hedonics_budget.py            the table: each diet's mean UNHAPPINESS and BOREDOM, mod and vanilla
    python tools/hedonics_budget.py --sweep    the table, then each hedonics dial at x0.8 and x1.2
    python tools/hedonics_budget.py --json P   the table (and the sweep with --sweep) as JSON at P

Exit 1 when a band fails. It runs no game and is read-only.

The diets (DIETS): mixed (a four-day rotation of plates of ready foods, a little butter at breakfast); cooked (six
evolved dishes over two days, two distinct ingredients and a salt each); canned (a three-day rotation of nine open
cans); butter (three quarters of a stick of butter a day, a quarter at each meal beside one food of a mixed plate); sugar (seven
bags of sugar a day); one food (five open cans of bolognese a day); butter fast (one meal a day at 08:00, half a stick
of butter beside the first food of a mixed breakfast, eaten Hungry: the arm that reaches R3, reported with no band).
Meals at 08:00, 13:00 and 20:00, water as the guide's (mod_guide_series.autodrops), from a fresh record at 07:00.

The two sides eat the same eats (a ruling of this oracle: the reference diet is a fixed schedule, so the comparison is
of the mood rules, not of vanilla's hunger, which would have a vanilla survivor eat three and a half sticks of butter
a day for its HungerChange -24):
- vanilla: each eat adds its UnhappyChange and BoredomChange times the share eaten (BodyDamage.JustAteFood, inventory
  section 1.1; #3655), the stat held in 0..100; an evolved dish adds its own value (DISH_UNHAPPY: -5 for each of its
  two distinct ingredients and -2 for its salt, #0298 and #4119's spice term). Vanilla never lowers UNHAPPINESS
  passively (#3033), so a stat fed only by food would sum every sad eat for ever and pin at 100 on any diet with a sad
  food in it; the oracle gives both sides the same upkeep, UPKEEP_H mood points a game hour off both stats (the
  player's own reading, rest and company), a game choice of the oracle, swept in the report. The upkeep moves each
  stat toward a standing background bg (0 in the table: the plain upkeep); the sizing arm (Oracle.sizing, printed by
  --sweep) stands both sides at BG_U with BG_UPKEEP_H, the stat a survivor carries from the rest of play, so a dish's
  relief (R2) is no longer spent at the 0 clamp and the Cooking level shows. Vanilla's idle boredom
  and its BORED-to-unhappy rise are left out on both sides: they are the same whatever is eaten (inventory 1.8).
- mod: the same adds after R2 (K.hedonics.prep at COOKING_LEVEL on a dish) and R3 (K.hedonics.allies at the HUNGER
  the mod's own server pipeline wrote the minute before the eat); each eat booked into monotony (K.monotony.record,
  with its taste class, R4) and the plain-energy ring (K.hedonics.book, R1; a dish books its kcal as not plain, its
  ingredients exempt); each minute the writer's floor (K.hybrid.floor at the floors' rise rates) toward the composed
  target, monotony's plus the plain-energy floor (K.hedonics.target) held under writer.UNHAPPY_HI, through the dead
  zone (K.monotony.hold), and BOREDOM toward monotony's. The effects floors (sleep loss, caffeine, the drain states)
  are left out: they are not food mood.
The diets keep the character alive and hydrated (CLAUDE.md section 5): each is first run through the mod's server
pipeline on the lupa host (mod_guide_series.server_run, rule R-1's assert_viable), which also gives the HUNGER at
each eat. The mood rules read nothing back into the body, so the hedonics sweep re-runs the mood model only.

The bands (K.hedonics.BUDGET_FAIR and BUDGET_DEGEN, dials): the balanced diet (mixed) and the cooked diet, at each of
COOKING_LEVELS, must be no sadder than vanilla by more than FAIR, on UNHAPPINESS and on BOREDOM, as means over the 14
days; a degenerate diet (butter, sugar, one food) must be sadder than vanilla on UNHAPPINESS by DEGEN or more. The
canned diet is reported with no band: it is neither (the spec's bands name balanced, cooked and degenerate diets), and
a canned diet repeats its few dense cans, the field-ration monotony the existing monotony prices (S1597, S2303).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import food_hedonics as FH  # noqa: E402

DAYS = 14
MINUTES = DAYS * 1440
MEAL_MIN = (60, 360, 780)            # 08:00, 13:00 and 20:00 from world age 0 at 07:00 (mod_guide_series.REQUEST_MIN)
UPKEEP_H = 1.0                       # mood points a game hour off both stats on both sides: the oracle's game choice
COOKING_LEVEL = 0                    # the stated Cooking level of the checks' cooked rows: a fresh survivor's
COOKING_LEVELS = (0, 5, 10)          # the cooked diet is checked at each
SIZING_LEVELS = tuple(sorted(set(COOKING_LEVELS) | {0, 3, 10}))   # the sizing arm's: PREP_KNOTS' three knots too
BG_U = 20.0                          # the sizing arm's standing background on both stats: the oracle's game choice
BG_UPKEEP_H = 2.0                    # the sizing arm's upkeep toward it, mood points a game hour: the oracle's game choice
DISH_UNHAPPY = -12                   # two distinct ingredients at -5 each (#0298) and a salt at -2 (#4119: 200 x use 0.01)

BALANCED = ("mixed",)
COOKED = ("cooked",)
DEGENERATE = ("butter", "sugar", "one food")
REPORTED = ("canned", "butter fast")  # neither balanced nor degenerate (a canned diet repeats its few dense cans; the
                                      # butter fast is R3's arm): no band

# the sweep: each game-choice hedonics dial, set on the kernel's field at x0.8 and x1.2 (ALLIES_LEVEL is a moodle
# level, swept one level down and up instead); S2291's thresholds are a definition and are not swept
SWEEP = ("hedonics.PLAIN_SHARE", "hedonics.PLAIN_KCAL", "hedonics.FATTY_SHARE", "hedonics.SHARE_MIN_KCAL",
         "hedonics.FLOOR_KNOTS.1.1", "hedonics.FLOOR_KNOTS.2.1", "hedonics.FLOOR_KNOTS.2.2", "hedonics.FLOOR_KNOTS.3.1",
         "hedonics.FLOOR_KNOTS.3.2", "hedonics.PAIR_SHARE", "hedonics.PREP_KNOTS.1.2", "hedonics.PREP_KNOTS.2.1", "hedonics.PREP_KNOTS.3.2",
         "hedonics.ALLIES_F", "hedonics.ALLIES_LEVEL", "hedonics.CLASS_W")


def P(t, f=1.0):
    """A portion: a share f of one item of full type t."""
    return ("item", t, f)


def DISH(t, *portions):
    """An evolved dish of result type t eaten whole: its ingredient portions (its class is K.hedonics.dishClass's)."""
    return ("dish", t, portions)


MIXED_DAYS = (
    ((P("Base.Oatmeal"), P("Base.Banana"), P("Base.PeanutButter", 0.1), P("Base.Butter", 0.03)),
     (P("Base.Burger"), P("Base.Apple"), P("Base.Crisps", 0.5)),
     (P("Base.Ham", 0.4), P("Base.Bread", 0.3), P("Base.Cabbage", 0.5), P("Base.Orange"))),
    ((P("Base.BagelPlain"), P("Base.BagelPlain"), P("Base.Cheese"), P("Base.EggBoiled"), P("Base.EggBoiled"),
      P("Base.Butter", 0.03)),
     (P("Base.Burrito"), P("Base.Banana"), P("Base.GranolaBar")),
     (P("Base.ChickenFried"), P("Base.ChickenFried"), P("Base.Fries"), P("Base.Lettuce"), P("Base.Pie"))),
    ((P("Base.Pancakes"), P("Base.Pancakes"), P("Base.Orange"), P("Base.Yoghurt"), P("Base.Yoghurt"),
      P("Base.Butter", 0.03)),
     (P("Base.Sandwich"), P("Base.Sandwich"), P("Base.Apple")),
     (P("Base.Salmon"), P("Base.Salmon"), P("Base.Bread", 0.3), P("Base.Kale", 0.5), P("Base.Chocolate", 0.3))),
    ((P("Base.Cereal", 0.15), P("Base.Banana"), P("Base.Peanuts"), P("Base.Peanuts")),
     (P("Base.Hotdog"), P("Base.Hotdog"), P("Base.Apple")),
     (P("Base.PorkChop"), P("Base.PorkChop"), P("Base.Tortilla"), P("Base.Tortilla"), P("Base.Tomato"),
      P("Base.Tomato"), P("Base.Salami"), P("Base.Icecream", 0.15))),
)

COOKED_DAYS = (
    (DISH("Base.Oatmeal", P("Base.Oatmeal"), P("Base.Banana"), P("Base.PeanutButter", 0.15)),
     DISH("Base.Sandwich", P("Base.Bread", 0.5), P("Base.Salami"), P("Base.Cheese")),
     DISH("Base.PotOfStew", P("Base.Ham", 0.6), P("Base.Cabbage", 0.5))),
    (DISH("Base.PancakesRecipe", P("Base.Pancakes"), P("Base.Pancakes"), P("Base.Banana"), P("Base.Yoghurt")),
     DISH("Base.PotOfSoupRecipe", P("Base.Pork"), P("Base.CannedCornOpen")),
     DISH("Base.PanFriedVegetables", P("Base.Rice", 0.25), P("Base.Chicken"))),
)

CANNED_DAYS = (
    ((P("Base.CannedPeachesOpen"), P("Base.TunaTinOpen")),
     (P("Base.CannedBologneseOpen"), P("Base.CannedPeasOpen")),
     (P("Base.CannedCornedBeefOpen"), P("Base.CannedCornOpen"))),
    ((P("Base.CannedFruitCocktailOpen"), P("Base.CannedSardinesOpen"), P("Base.CannedChiliOpen")),
     (P("Base.CannedCornedBeefOpen", 0.6), P("Base.CannedCarrotsOpen"), P("Base.CannedPineappleOpen")),
     (P("Base.CannedBologneseOpen"), P("Base.TunaTinOpen"))),
    ((P("Base.CannedPeachesOpen"), P("Base.CannedChiliOpen"), P("Base.CannedMushroomSoupOpen")),
     (P("Base.TunaTinOpen"), P("Base.CannedPotatoOpen"), P("Base.CannedPeasOpen")),
     (P("Base.CannedCornedBeefOpen"), P("Base.CannedTomatoOpen"), P("Base.CannedFruitCocktailOpen"))),
)

BUTTER_DAYS = tuple(tuple((P("Base.Butter", 0.25),) + meal[:1] for meal in day) for day in MIXED_DAYS)

SUGAR_DAYS = (((P("Base.Sugar"), P("Base.Sugar")), (P("Base.Sugar"), P("Base.Sugar")),
               (P("Base.Sugar"), P("Base.Sugar"), P("Base.Sugar"))),)

ONE_DAYS = (((P("Base.CannedBologneseOpen"),), (P("Base.CannedBologneseOpen"), P("Base.CannedBologneseOpen")),
             (P("Base.CannedBologneseOpen"), P("Base.CannedBologneseOpen"))),)

FAST_DAYS = tuple(((P("Base.Butter", 0.5),) + day[0][:1],) for day in MIXED_DAYS)

DIETS = {"mixed": MIXED_DAYS, "cooked": COOKED_DAYS, "canned": CANNED_DAYS, "butter": BUTTER_DAYS,
         "sugar": SUGAR_DAYS, "one food": ONE_DAYS, "butter fast": FAST_DAYS}

ORACLE_LUA = r"""
NR_BUDGET = {}
-- One diet's 14 days on both sides. eats is an array of { minute, key, kcal, unhappy, bored, plain, class, staple,
-- dish, hunger } sorted by minute. Returns the four means: vanilla UNHAPPINESS, vanilla BOREDOM, mod UNHAPPINESS, mod
-- BOREDOM, and the mod's largest plain-energy floor and largest composed UNHAPPINESS target. Every stat starts at the
-- standing background bg and its upkeep moves it toward bg.
function NR_BUDGET.run(eats, n, minutes, upkeepH, level, hi, bg)
    local K = NutritionRevamp.kernel
    local m = K.monotony.new()
    local h = K.hedonics.new(0)
    local vU, vB, U, B = bg, bg, bg, bg
    local lastU, lastB = 0, 0
    local sVU, sVB, sU, sB = 0, 0, 0, 0
    local maxFloor, maxTarget = 0, 0
    local riseU = K.hybrid.MOOD_RISE_UNHAPPY * 60
    local riseB = K.hybrid.MOOD_RISE_BORED * 60
    local up = upkeepH / 60
    local j = 1
    for t = 0, minutes - 1 do
        local ageH = t / 60
        while j <= n and eats[j].minute == t do
            local e = eats[j]
            vU = K.clamp(vU + e.unhappy, 0, 100)
            vB = K.clamp(vB + e.bored, 0, 100)
            local d = e.unhappy
            if e.dish then
                d = K.hedonics.prep(d, level)
            end
            d = K.hedonics.allies(d, e.hunger)
            U = K.clamp(U + d, 0, 100)
            B = K.clamp(B + e.bored, 0, 100)
            K.monotony.prune(m, ageH)
            K.monotony.record(m, e.key, ageH, K.monotony.weightOf(e.kcal), e.staple, e.class)
            K.hedonics.book(h, ageH, e.kcal, e.plain)
            j = j + 1
        end
        vU = NR_BUDGET.toward(vU, bg, up)
        vB = NR_BUDGET.toward(vB, bg, up)
        U = NR_BUDGET.toward(U, bg, up)
        B = NR_BUDGET.toward(B, bg, up)
        local mu, mb = K.monotony.target(m, ageH)
        local pf = K.hedonics.target(h, ageH)
        if pf > maxFloor then maxFloor = pf end
        local ut = K.monotony.hold(K.min(mu + pf, hi), lastU, K.monotony.UNHAPPY_AT)
        local bt = K.monotony.hold(mb, lastB, K.monotony.BORED_AT)
        if ut > maxTarget then maxTarget = ut end
        local nu, ku = K.hybrid.floor(U, ut, lastU, riseU)
        if nu ~= nil then U = nu end
        lastU = ku
        local nb, kb = K.hybrid.floor(B, bt, lastB, riseB)
        if nb ~= nil then B = nb end
        lastB = kb
        sVU = sVU + vU
        sVB = sVB + vB
        sU = sU + U
        sB = sB + B
    end
    return sVU / minutes, sVB / minutes, sU / minutes, sB / minutes, maxFloor, maxTarget
end

-- The upkeep: v moved toward the standing background bg by at most up (bg 0 is the plain upkeep, max(0, v - up)).
function NR_BUDGET.toward(v, bg, up)
    if v > bg then
        return math.max(bg, v - up)
    end
    return math.min(bg, v + up)
end
"""


class Oracle:
    """The mood model's kernel host (food_hedonics.runtime: NR_Core, the registry and the kernels) and the diets' body
    runs (the mod's server pipeline, once per diet; the mood rules never reach the body)."""

    def __init__(self):
        self.rt = FH.runtime()
        self.rt.execute(ORACLE_LUA)
        self.K = self.rt.globals().NutritionRevamp.kernel
        self.items = FH._items()
        self.foods = {f["pz_id"]: f for f in FH._foods()}
        self._body = {}
        self._eat = {}

    # ---- the eats ----------------------------------------------------------------------------------------------------

    def eat_event(self, minute, t):
        """mod_guide_series.eat's event of a whole item (its script read once a type)."""
        if t not in self._eat:
            import mod_guide_series as S
            self._eat[t] = S.eat(0, t)
        e = dict(self._eat[t])
        e["minute"] = minute
        return e

    def kcal(self, t, f):
        """The landed kcal of a portion: the item pass's calories (as mod_guide_series.eat reads them) times f."""
        return float(self.eat_event(0, t)["cal"]) * f

    def classify(self, t):
        """(plain, class, staple) of a food type by the kernel's rules at the kernel's current dials."""
        food, item = self.foods[t], self.items.get(t, {})
        p, c, l, na, kcal100, unhappy, food_type = FH.inputs(food, item)
        staple = bool(self.K.monotony.isStaple(t, food_type))
        plain = bool(self.K.hedonics.isPlain(p, c, l, na, kcal100, unhappy))
        return plain, str(self.K.hedonics.tasteClass(p, c, l, staple, FH.sweet(item, food))), staple

    def dish_class(self, portions, kcals):
        """R4: a dish's taste class, K.hedonics.dishClass over one entry an ingredient TYPE (its landed kcal summed,
        in first-appearance order), as the eat seat hands it (ruling T6-1 as refined; NR_Server_Hedonics H.dishClass)."""
        types, sums = [], {}
        for (_, pt, _), k in zip(portions, kcals):
            if pt not in sums:
                types.append(pt)
                sums[pt] = 0.0
            sums[pt] += k
        classes = self.rt.table_from([self.classify(pt)[1] for pt in types])
        return str(self.K.hedonics.dishClass(classes, self.rt.table_from([sums[pt] for pt in types])))

    def mood(self, t, f):
        item = self.items.get(t, {})
        return float(item.get("unhappy_change") or 0) * f, float(item.get("boredom_change") or 0) * f

    def schedule(self, diet):
        """[(minute, entry)]: every meal entry of a diet over DAYS, in order."""
        days = DIETS[diet]
        out = []
        for d in range(DAYS):
            for k, meal in enumerate(days[d % len(days)]):
                entries = meal if isinstance(meal, tuple) and meal and meal[0] == "dish" else None
                for entry in ((meal,) if entries else meal):
                    out.append((d * 1440 + MEAL_MIN[k], entry))
        return out

    def server_events(self, diet):
        """The diet's eats as the server replay's eat events (each portion of a dish too), and the guide's water."""
        import mod_guide_series as S
        ev = [S.FRESH]
        for minute, entry in self.schedule(diet):
            portions = entry[2] if entry[0] == "dish" else (entry,)
            for _, t, f in portions:
                e = self.eat_event(minute, t)
                e["frac"] = f
                ev.append(e)
        return ev + S.autodrops(DAYS)

    def body(self, diet):
        """The diet through the mod's server pipeline (cached): rule R-1's viability, and the HUNGER before each minute."""
        if diet not in self._body:
            import mod_guide_series as S
            rows, be = S.server_run(self.server_events(diet), MINUTES)
            v = S.assert_viable("hedonics budget: " + diet, S.viability(rows, be.K))
            self._body[diet] = ([r["HUNGER"] for r in rows], v)
        return self._body[diet]

    def eats(self, diet):
        """The mood model's eats of a diet at the kernel's current dials."""
        hunger, _ = self.body(diet)
        out = []
        for minute, entry in self.schedule(diet):
            h = hunger[minute - 1] if minute > 0 else 0.0
            if entry[0] == "dish":
                _, t, portions = entry
                kcals = [self.kcal(pt, f) for _, pt, f in portions]
                out.append({"minute": minute, "key": t, "kcal": sum(kcals), "unhappy": float(DISH_UNHAPPY),
                            "bored": 0.0, "plain": False, "class": self.dish_class(portions, kcals), "staple": False,
                            "dish": True, "hunger": h})
                continue
            _, t, f = entry
            plain, cls, staple = self.classify(t)
            u, b = self.mood(t, f)
            out.append({"minute": minute, "key": t, "kcal": self.kcal(t, f), "unhappy": u, "bored": b,
                        "plain": plain, "class": cls, "staple": staple, "dish": False, "hunger": h})
        return out

    # ---- the run -----------------------------------------------------------------------------------------------------

    def run(self, diet, level=COOKING_LEVEL, upkeep=UPKEEP_H, bg=0.0):
        """One diet's means: {vu, vb, mu, mb, du, db, floor, target, kcal_day}."""
        eats = self.eats(diet)
        lua = self.rt.table_from([self.rt.table_from(e) for e in eats])
        hi = float(self.K.dials.get("writer.UNHAPPY_HI"))
        vu, vb, mu, mb, fl, tg = self.rt.globals().NR_BUDGET.run(lua, len(eats), MINUTES, float(upkeep), float(level), hi,
                                                                 float(bg))
        return {"vu": vu, "vb": vb, "mu": mu, "mb": mb, "du": mu - vu, "db": mb - vb, "floor": fl, "target": tg,
                "kcal_day": sum(e["kcal"] for e in eats) / DAYS}

    def rows(self, upkeep=UPKEEP_H):
        """[(label, kind, result)]: every diet, the cooked one at each of COOKING_LEVELS."""
        out = []
        for diet in DIETS:
            if diet in COOKED:
                for lv in COOKING_LEVELS:
                    out.append(("%s (Cooking %d)" % (diet, lv), "cooked", self.run(diet, lv, upkeep)))
                continue
            kind = "balanced" if diet in BALANCED else ("reported" if diet in REPORTED else "degenerate")
            out.append((diet, kind, self.run(diet, COOKING_LEVEL, upkeep)))
        return out

    def sizing(self):
        """The sizing arm: (rows, verdicts, fast). rows and verdicts: the cooked diet at each of SIZING_LEVELS and the
        mixed diet, both sides standing at BG_U with BG_UPKEEP_H, with FAIR applied; fast: the butter fast's row at
        the registry's ALLIES_F and at 1.0 (R3 off), {"allies": row, "off": row}."""
        rows = [("cooked (Cooking %d)" % lv, "cooked", self.run("cooked", lv, BG_UPKEEP_H, BG_U))
                for lv in SIZING_LEVELS]
        rows.append(("mixed", "balanced", self.run("mixed", COOKING_LEVEL, BG_UPKEEP_H, BG_U)))
        f0 = self.K.hedonics.ALLIES_F
        fast = {"allies": self.run("butter fast")}
        try:
            self.K.hedonics.ALLIES_F = 1.0
            fast["off"] = self.run("butter fast")
        finally:
            self.K.hedonics.ALLIES_F = f0
        return rows, self.verdicts(rows), fast

    def bands(self):
        return float(self.K.hedonics.BUDGET_FAIR), float(self.K.hedonics.BUDGET_DEGEN)

    def verdicts(self, rows, fair=None, degen=None):
        """[(label, ok, why)] of the bands over rows."""
        f0, g0 = self.bands()
        fair = f0 if fair is None else fair
        degen = g0 if degen is None else degen
        out = []
        for label, kind, r in rows:
            if kind == "reported":
                ok = True
                why = "no band (UNHAPPINESS %+.2f, BOREDOM %+.2f)" % (r["du"], r["db"])
            elif kind == "degenerate":
                ok = r["du"] >= degen
                why = "UNHAPPINESS %+.2f, needs %+.2f or more" % (r["du"], degen)
            else:
                ok = r["du"] <= fair and r["db"] <= fair
                why = "UNHAPPINESS %+.2f, BOREDOM %+.2f, each at most %+.2f" % (r["du"], r["db"], fair)
            out.append((label, ok, why))
        return out

    # ---- the sweep ---------------------------------------------------------------------------------------------------

    def _slot(self, dial_id):
        import replay_live
        return replay_live.kernel_slot(self.K, dial_id)

    def sweep(self):
        """{dial: {"x0.8": rows, "x1.2": rows}}: each SWEEP dial set on its kernel field, the rows re-run, restored."""
        out = {}
        for dial in SWEEP:
            tbl, key = self._slot(dial)
            v0 = tbl[key]
            arms = {}
            for name, v in self.arms(dial, v0):
                tbl[key] = v
                try:
                    arms[name] = self.rows()
                finally:
                    tbl[key] = v0
            out[dial] = arms
        return out

    @staticmethod
    def arms(dial, v0):
        if dial == "hedonics.ALLIES_LEVEL":
            return [("level %d" % (v0 - 1), v0 - 1), ("level %d" % (v0 + 1), v0 + 1)]
        return [("x0.8", v0 * 0.8), ("x1.2", v0 * 1.2)]


def table_text(rows, verdicts):
    lines = ["%-20s %-10s %8s %8s %8s %8s %8s %8s %7s %7s %6s  %s" % (
        "diet", "kind", "van U", "mod U", "dU", "van B", "mod B", "dB", "floor", "target", "kcal/d", "verdict")]
    for (label, kind, r), (_, ok, why) in zip(rows, verdicts):
        lines.append("%-20s %-10s %8.2f %8.2f %+8.2f %8.2f %8.2f %+8.2f %7.2f %7.2f %6.0f  %s: %s" % (
            label, kind, r["vu"], r["mu"], r["du"], r["vb"], r["mb"], r["db"], r["floor"], r["target"],
            r["kcal_day"], "pass" if ok else "FAIL", why))
    return "\n".join(lines)


def main(argv=None, oracle=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sweep", action="store_true", help="also run each hedonics dial at x0.8 and x1.2")
    ap.add_argument("--json", metavar="PATH", help="write the table (and the sweep) as JSON")
    a = ap.parse_args(argv)
    o = oracle or Oracle()
    rows = o.rows()
    ver = o.verdicts(rows)
    fair, degen = o.bands()
    print("hedonics budget: %d days, upkeep %.2f a game hour, bands FAIR %.2f DEGEN %.2f (mean mood points)"
          % (DAYS, UPKEEP_H, fair, degen))
    print(table_text(rows, ver))
    doc = {"rows": [{"diet": l, "kind": k, **r} for l, k, r in rows],
           "verdicts": [{"diet": l, "ok": ok, "why": w} for l, ok, w in ver]}
    if a.sweep:
        doc["upkeep"] = {}
        for up in (UPKEEP_H * 0.5, UPKEEP_H * 2.0):
            r2 = o.rows(up)
            v2 = o.verdicts(r2)
            print("\nupkeep %.2f a game hour" % up)
            print(table_text(r2, v2))
            doc["upkeep"][str(up)] = [{"diet": l, "kind": k, **r} for l, k, r in r2]
        sz, szv, fast = o.sizing()
        print("\nsizing: both sides standing at %.2f, upkeep %.2f a game hour toward it" % (BG_U, BG_UPKEEP_H))
        print(table_text(sz, szv))
        print("butter fast dU %+.2f at ALLIES_F %.2f, %+.2f at 1.00 (R3 off)"
              % (fast["allies"]["du"], float(o.K.hedonics.ALLIES_F), fast["off"]["du"]))
        doc["sizing"] = {"bg": BG_U, "upkeep": BG_UPKEEP_H, "rows": [{"diet": l, "kind": k, **r} for l, k, r in sz],
                         "verdicts": [{"diet": l, "ok": ok, "why": w} for l, ok, w in szv],
                         "butter fast": fast}
        sw = o.sweep()
        doc["sweep"] = {}
        print("\nsweep: each diet's dU (dB for the fair rows in brackets); * a failed band")
        for dial, arms in sw.items():
            doc["sweep"][dial] = {}
            for name, r2 in arms.items():
                v2 = o.verdicts(r2)
                cells = []
                for (label, kind, r), (_, ok, _) in zip(r2, v2):
                    cell = "%s %+.2f" % (label.split(" (")[0] + ("" if kind != "cooked" else label[-3:-1].strip()),
                                         r["du"])
                    if kind != "degenerate":
                        cell += " (%+.2f)" % r["db"]
                    cells.append(cell + ("" if ok else "*"))
                print("%-26s %-9s %s" % (dial, name, "; ".join(cells)))
                doc["sweep"][dial][name] = [{"diet": l, "du": r["du"], "db": r["db"], "ok": ok}
                                            for (l, k, r), (_, ok, _) in zip(r2, v2)]
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
    return 0 if all(ok for _, ok, _ in ver) else 1


if __name__ == "__main__":
    sys.exit(main())
