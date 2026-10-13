"""x363-drink -- Plan 11g Task 8 session 3 (live): a drink against a meal on the final satiety model, with the physical
and the food fill (ruling T6c-1). One boot of profile x36-gut (fixture default, admin -debug, Nutrition false, DayLength
1, sleep off) on the STAGED copy of the tree at the final build (release/x36-gut, staged fresh from HEAD before the
boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x36_gut_lib.py (frozen with x361's run). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE TASK 8 AMENDMENTS (copied in substance): a 500 mL drink, then a solid meal of equal energy; the physical fill shows
the drink (about 0.68) while the food fill stays 0; the satiety response follows the replay.

THE DESIGN, NAMED BEFORE THE RUN (the amendment's two clauses read as two drinks, named):
  W500  0.5 L of the vanilla fluid Water (the mod's fluid table: 999 g of water a litre, no macro) by drink.action from
        Base.WaterBottle's server copy (fluid.fill, server; x263's route), at once at the scenario's start on the
        fresh record's empty stomach (ruling 11c-15: a new stomach is empty, so the food fill reads 0 until the milk);
        the world at speed 1 for WATCH_M game minutes after the drink (the liquid lane half-empties in 13 min, S1245).
  MILK  then at once 0.5 L of CowMilk (628.3 kcal, 49.44 g carbohydrate, 33.475 g fat, 32.445 g protein, 907.739 g
        water a litre) by drink.action from a Base.Milk carton spawned just before its fill (a second container type, so
        the client's copy of the drunk water bottle is never asked to drink again; the carton is spawned just before so
        the engine's auto-drink from a carried container, which the server's flag does not stop, #2941 and finding
        F-T4-2, has no full container to drink from before the milk's drink); its water to the liquid lane, its macros
        to the solid buffer (K.stomach.ingestLiquid), so the milk lifts the food fill by its solids (about 0.08).
  SOLID TKX.MilkSolid (the same 0.5 L vector as a food: 314.15 kcal, water 453.8695 g) at the next request (to_request,
        cap CAP_H after the milk), eaten at the slow clock; the next request marked (cap); end at speed 1. The milk is
        drunk at once and not at a request (x265's order, F-T4-2); the two arms on equal footing are the replay arms of
        x36_grade.py (ruling 11f-3: the milk's sips at the solid's landing row and the solid at the milk's first sip).
  No canteen (the autodrink flag false; no container is left full after its drink).
PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  W500FILL the water's sip rows lift stomach.liquid; the peak physical fill after its first sip row in 0.55-0.70 (500 g
           over 730 g is 0.684, less what empties while the sips land) and within 0.002 of the replay's peak; the food
           fill 0 on every ring row from the scenario's start to the row before the milk's first sip row.
  MILKFILL the milk's sip rows lift the food fill (its solids) and stomach.liquid; the live fills within 0.002 of the
           replay on every graded row (GRADE_DIFF).
  COURSE   the milk's course (its first sip row to the solid's landing) and the solid's (its landing to the session's
           last row) live against the replay (course_reading, TOL_GRADE; the request within max(3, 2 %)).
  REPLAY   the whole session's replay diff ok under DEFAULT_TOL (HUNGER 0.002, es 0.005, L 0.5 %).
  GRADE_DIFF  the whole session under TOL_GRADE.
  H1, RING, F, Z  the engine's.
READINGS: the request minutes after the milk and after the solid (live and replay); the liquid-over-solid interval
  ratio on the replay arms (x36_grade.py); M after each.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x36_gut_lib as L   # noqa: E402

PROFILE = "x36-gut"
PREFIX = "x363"
ARTIFACT = "drink.json"
STAGE_ROOT = "release/x36-gut/NutritionRevamp"
STAGED_AT = "7093079b"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
BOTTLE, WATER, WATER_L = "Base.WaterBottle", "Water", 0.5
CARTON, MILK, MILK_L = "Base.Milk", "CowMilk", 0.5
WATCH_M = 45.0
CAP_H = 9.0
PEAK = (0.55, 0.70)
FILL_TOL = 0.002
SESSION = ("Plan 11g Task 8 session 3: 0.5 L of water, then 0.5 L of CowMilk at once, then TKX.MilkSolid at the next "
           "request, on the staged copy; one boot of " + PROFILE)
PRED = {
    "W500FILL": {"water": "liquid rises at its sip rows; peak fill in 0.55-0.70 and within 0.002 of the replay's; food "
                          "fill 0 until the milk"},
    "MILKFILL": {"milk": "food fill and liquid rise at its sip rows"},
    "COURSE": {"MILK and SOLID": "live within TOL_GRADE of the replay; request within max(3, 2 %)"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "GRADE_DIFF": {"whole session": "ok under TOL_GRADE"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    X["script"] = S.keep(S.step("X_script", L.SRV, "item.script", L.MILKSOLID))
    S.spawn(L.MILKSOLID, 1, "spawn_solid")
    S.slow("W_slow")
    S.spawn(BOTTLE, 1, "spawn_bottle")
    S.drink(BOTTLE, WATER, WATER_L, "W500")
    S.one("W_one")
    a = S.age("W_watch_a")
    S.wait_age((a or 0.0) + WATCH_M / 60.0, "W_watch")
    S.slow("MILK_slow")
    S.spawn(CARTON, 1, "spawn_carton")
    S.drink(CARTON, MILK, MILK_L, "MILK")
    a = S.age("MILK_a")
    S.fast("MILK_fast")
    X["solid_request"] = S.to_request("SOLID", cap_age=(a or 0.0) + CAP_H)
    S.eat(L.MILKSOLID, "SOLID")
    a = S.age("SOLID_a")
    S.fast("SOLID_fast")
    X["next_request"] = S.to_request("X_next", cap_age=(a or 0.0) + CAP_H)
    S.one("X_end_one")
    X["done"] = True


def sip_rows(S, label):
    d = next((x for x in S.drinks if x.get("label") == label), None)
    return list((d or {}).get("ring_s") or [])


def grade(S, ring, rows_rep):
    R, V = S.out["readings"], S.out["verdicts"]
    w, m = sip_rows(S, "W500"), sip_rows(S, "MILK")
    by_s = {r["s"]: r for r in ring if r.get("s") is not None}
    m0 = min(m) if m else None
    a_m0 = by_s[m0]["age"] if m0 in by_s else None
    wr = L.drink_reading(ring, rows_rep, w, a_m0 if a_m0 is not None else (ring[-1]["age"] if ring else 0.0))
    pre = [L.food_fill(r) for r in ring if r.get("s") is not None and (m0 is None or r["s"] < m0)]
    pre = [x for x in pre if x is not None]
    lrise = []
    for s in w:
        a, b = by_s.get(s - 1), by_s.get(s)
        if a is not None and b is not None and L.num(a.get(L.LIQ)) is not None and L.num(b.get(L.LIQ)) is not None:
            lrise.append(b[L.LIQ] - a[L.LIQ])
    pk, pkr = wr.get("peak_fill"), wr.get("peak_fill_replay")
    ok = (bool(w) and bool(lrise) and all(x > 0 for x in lrise) and pk is not None and pkr is not None
          and PEAK[0] <= pk <= PEAK[1] and abs(pk - pkr) <= FILL_TOL and bool(pre) and max(pre) <= 1e-12)
    R["w500"] = wr
    V["W500FILL"] = {"predicted": PRED["W500FILL"],
                     "observed": {"sip_rows": w, "liquid_rise": lrise, "peak_fill": pk, "peak_fill_replay": pkr,
                                  "food_fill_max_before_milk": max(pre) if pre else None, "rows_before_milk": len(pre)},
                     "verdict": ("unmeasured" if not w else "as_predicted" if ok else "falsified")}
    mr = L.drink_reading(ring, rows_rep, m, (a_m0 or 0.0) + 1.0)
    frise = []
    for s in m:
        a, b = by_s.get(s - 1), by_s.get(s)
        if a is not None and b is not None:
            x, y = L.food_fill(a), L.food_fill(b)
            q0, q1 = L.num(a.get(L.LIQ)), L.num(b.get(L.LIQ))
            frise.append({"s": s, "food": (y - x) if (x is not None and y is not None) else None,
                          "liquid": (q1 - q0) if (q0 is not None and q1 is not None) else None})
    ok2 = bool(frise) and all((f["food"] or 0) > 0 and (f["liquid"] or 0) > 0 for f in frise[:1])
    R["milk"] = mr
    V["MILKFILL"] = {"predicted": PRED["MILKFILL"], "observed": {"sip_rows": m, "rises": frise},
                     "verdict": ("unmeasured" if not m else "as_predicted" if ok2 else "falsified")}
    solid = next((e for e in S.eats if e.get("label") == "SOLID" and e.get("ring_age") is not None), None)
    out, oks = {}, []
    end = ring[-1]["age"] if ring else None
    if a_m0 is not None and solid is not None:
        out["MILK"] = L.course_reading(ring, rows_rep, a_m0, solid["ring_age"] - 1e-6)
        oks.append(out["MILK"]["ok"])
    if solid is not None and end is not None:
        out["SOLID"] = L.course_reading(ring, rows_rep, solid["ring_age"], end)
        oks.append(out["SOLID"]["ok"])
    R["courses"] = out
    V["COURSE"] = {"predicted": PRED["COURSE"],
                   "observed": {k: {"ok": v.get("ok"), "request": v.get("request"),
                                    "fields": L.g(v, "diff", "fields"), "findings_n": L.g(v, "diff", "findings_n")}
                                for k, v in out.items()},
                   "verdict": ("unmeasured" if not oks else "as_predicted" if all(oks) and len(oks) == 2
                               else "falsified")}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x363_drink.py",
              scenario, grade).run()
