"""x264-density -- Plan 11f Task 4 session 4 (live): research row 3, part 2 -- Marciani 2012's soup against the same
meal with its water drunk (over 3 h), and energy density at 400 kcal (Dense400Lo at 0.8 kcal/g against Dense400Hi at
1.6 kcal/g, the 180-minute sum and the request). One boot of profile x26-meals (fixture default, admin -debug,
Nutrition false, DayLength 1) on the STAGED copy of the tree (release/x26-meals, staged fresh from HEAD before the
boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x26_meals_lib.py (frozen with x261's run). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

RESEARCH ROW 3 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 3 | Energy density and volume | S1231 (Rolls 1999), S1233 (Rolls 1998, check), S1232 (Marciani), S1235 (Goetze),
  S1230 (Robinson), S1229 (Rolls 1999 ED) | `test_rolls_1999_soup_casserole...` (1.1x), `test_soup_sates_more...`,
  `test_fullness_is_linear...` (r2 > 0.999), `test_a_less_energy_dense_meal_sates_more` | from the request:
  `Casserole`, `Soup` (same + 356 g water), `Casserole` + 356 mL water by `drink.action`; HUNGER at minute 17 (slow
  clock around the eat); `Marc` solid+water vs soup over 3 h; `Dense400@0.8` vs `@1.6` over 15 h; water-only foods
  100-600 g at minute 1 | ~60 | 2 (mixed slow/fast) | HUNGER at minute 17 -> intake mapping (kJ), 3 h means, minute-1
  fullness | live within 0.002 of replay at the reading minute; replay's Rolls ratios vs 1.1x (oracle) |
THE AMENDMENTS: Marc against MarcSoup over 3 h. Dense400Lo against Dense400Hi over 15 h. (The Rolls arms and the
water-only foods are session 3, x263.)

THE DESIGN, NAMED BEFORE THE RUN: the oracle's solid arm is MARC_SOLID with MARC_WATER (300 g) drunk alongside, so the
live solid arm is TKX.Marc and 0.300 L of Water drunk right after it lands (Base.WaterBottle's server copy refilled by
fluid.fill, drink.action; x151's route, #3149). Each arm is eaten at its own request, so the arms differ in hour and
state; live is graded against the replay, and the clean contrasts are read on REPLAY ARMS (ruling 11f-3) at the first
arm's landing row. Order: MARC (+ water), MSOUP, DLO, DHI.

PHASES (the engine's S, H, W; then X; then R, D, Z, the replay):
  X  spawn Marc, MarcSoup, Dense400Lo, Dense400Hi, WaterBottle; speed 5; for each arm: to_request(arm), eat (MARC: then
     fill the bottle with 0.300 L Water and drink it), speed 5; the next request marked; end.
PREDICTIONS:
  R3REQ   every labelled eat's live request minute within max(3 min, 2 %) of the replay's.
  R3MEAN  each arm's live mean HUNGER over the 180 min after its landing within 0.002 of the replay's.
  REPLAY, H1, RING, F, Z  the engine's.
READINGS (graded against the oracle in the grader): on replay arms at the MARC landing row, the soup's 3 h mean HUNGER
below the solid + water's (oracle direction: lower, every minute no higher) and the difference against the oracle's;
at the DLO landing row, Dense400Lo's 180-minute sum below Dense400Hi's and its request no earlier (oracle direction),
with the minutes.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x264"
ARTIFACT = "density.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
MARC, MSOUP, DLO, DHI = "TKX.Marc", "TKX.MarcSoup", "TKX.Dense400Lo", "TKX.Dense400Hi"
BOTTLE, WATER, WATER_L = "Base.WaterBottle", "Water", 0.300
SESSION = ("Plan 11f Task 4 session 4: row 3 part 2, Marc with 300 mL water against MarcSoup, Dense400Lo against "
           "Dense400Hi, each from its request, on the staged copy; one boot of " + PROFILE)
PRED = {
    "R3REQ": {"each labelled eat": "live request minute within max(3, 2 %) of the replay's"},
    "R3MEAN": {"each arm": "live mean HUNGER over 180 min after the landing within 0.002 of the replay's"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}
ARMS = (("MARC", MARC), ("MSOUP", MSOUP), ("DLO", DLO), ("DHI", DHI))


def scenario(S):
    S.out["phases"]["X"] = {}
    for lab, full in ARMS:
        S.spawn(full, 1, "spawn_" + lab)
    S.spawn(BOTTLE, 1, "spawn_bottle")
    S.fast("X_fast0")
    for lab, full in ARMS:
        S.to_request(lab)
        e = S.eat(full, lab)
        if lab == "MARC" and e.get("landed"):
            S.drink(BOTTLE, WATER, WATER_L, "MARC_water")
        S.fast(lab + "_fast")
    S.to_request("X_next")
    S.fast("X_end_fast")


def grade(S, ring, rows_rep):
    import replay_live as RL
    R = S.out["readings"]
    req = R.get("requests") or {}
    by = {e["label"]: e for e in S.eats if e.get("ring_s") is not None}
    means = {}
    for lab, _ in ARMS:
        e = by.get(lab)
        if e is None:
            continue
        lv, rpv = L.mean_over(ring, e["ring_age"], 180), L.mean_over(rows_rep, e["ring_age"], 180)
        means[lab] = {"landing_s": e["ring_s"], "live": lv, "replay": rpv,
                      "diff": (lv - rpv) if (lv is not None and rpv is not None) else None}
        means[lab]["ok"] = (abs(means[lab]["diff"]) <= 0.002) if means[lab]["diff"] is not None else None
    for name, d in (("R3REQ", req), ("R3MEAN", means)):
        oks = [v.get("ok") for v in d.values()]
        S.out["verdicts"][name] = {"predicted": PRED[name], "observed": d,
                                   "verdict": ("as_predicted" if oks and all(o is True for o in oks) else
                                               ("unmeasured" if not oks or all(o is None for o in oks) else
                                                "falsified"))}
    with open(os.path.join(S.run_dir, "events.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    with open(os.path.join(S.run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(S.run_dir, "start-stats.json"), encoding="utf-8") as fh:
        ss = json.load(fh)
    with open(os.path.join(S.run_dir, "player.json"), encoding="utf-8") as fh:
        pl = json.load(fh)
    rr, rp = RL.load_ring([os.path.join(S.run_dir, x) for x in S.ring_files()])
    drops = tuple(a for a, _ in ARMS) + ("MARC_water",)

    def arm(add):
        evs = [x for x in ev if x.get("label") not in drops] + add
        evs.sort(key=lambda x: x["s"])
        rows, _ = RL.replay_live(rr, evs, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
        return rows

    m = by.get("MARC")
    if m is not None:
        w = [x for x in ev if x.get("label") == "MARC_water"]
        shift = (w[0]["s"] - m["ring_s"]) if w else 2
        solid = arm([{"s": m["ring_s"], "kind": "eat", "food": MARC},
                     {"s": m["ring_s"] + max(0, shift), "kind": "drink", "fluid": WATER, "litres": WATER_L}])
        soup = arm([{"s": m["ring_s"], "kind": "eat", "food": MSOUP}])
        a0 = m["ring_age"]
        hs = [r for r in soup if a0 < r["age"] <= a0 + 3.0]
        hl = [r for r in solid if a0 < r["age"] <= a0 + 3.0]
        pairs = list(zip([r["HUNGER"] for r in hs], [r["HUNGER"] for r in hl]))
        R["marc_arms"] = {"kind": "replay arms (ruling 11f-3): every arm removed, then MARC + 0.300 L Water (as many "
                                  "rows after as live) or MSOUP at the MARC landing row",
                          "landing_s": m["ring_s"], "soup_mean_180": L.mean_over(soup, a0, 180),
                          "solid_water_mean_180": L.mean_over(solid, a0, 180),
                          "soup_never_higher": all(a <= b + 1e-12 for a, b in pairs) if pairs else None,
                          "rows": len(pairs)}
    d = by.get("DLO")
    if d is not None:
        lo = arm([{"s": d["ring_s"], "kind": "eat", "food": DLO}])
        hi = arm([{"s": d["ring_s"], "kind": "eat", "food": DHI}])
        a0 = d["ring_age"]
        R["dense_arms"] = {"kind": "replay arms (ruling 11f-3): every arm removed, then Dense400Lo or Dense400Hi at the "
                                   "DLO landing row", "landing_s": d["ring_s"],
                           "lo_mean_180": L.mean_over(lo, a0, 180), "hi_mean_180": L.mean_over(hi, a0, 180),
                           "lo_request_min": L.request_after(lo, a0), "hi_request_min": L.request_after(hi, a0)}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x264_density.py",
              scenario, grade).run()
