"""x265-liquid -- Plan 11f Task 4 session 5 (live): research row 4, liquid against solid calories (partial; graded live
against the replay only, ruling 11f-4). One boot of profile x26-meals (fixture default, admin -debug, Nutrition false,
DayLength 1) on the STAGED copy of the tree (release/x26-meals, staged fresh from HEAD before the boot; mod/ is never
booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x26_meals_lib.py (frozen with
x261's run). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2).

RESEARCH ROW 4 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 4 | Liquid vs solid calories | S1233, S1247 (liquid preloads), S1228 (Melanson, non-reproduction) |
  `test_rolls_1998_milk_volume_check`, `test_callahans_preloads_*` (250/279/339) | **partial**: a vanilla caloric fluid
  the mod's table carries (Milk) by `drink.action` against a declared solid of the same kcal and water, both from the
  request at 09:00 | ~24 | 1 (fast) | request minutes, liquid-lane mass | live vs replay-of-live only; the oracle's
  composition cannot be drunk (s3.1), so no study band is inherited -- flagged |
THE AMENDMENTS: Milk by `drink.action` against a declared solid of the same kcal and water (TKX.MilkSolid, added for
this row with the int-key rule kept). Graded live against the replay only (ruling 11f-4).

THE DESIGN, NAMED BEFORE THE RUN: the milk is 0.5 L of the vanilla fluid CowMilk (the mod's fluid table: 628.3 kcal,
49.44 g carbohydrate, 33.475 g fat, 32.445 g protein and 907.739 g water a litre) in Base.WaterBottle's server copy
(fluid.fill, server) drunk by drink.action (x151's route, #3149); TKX.MilkSolid declares the same 0.5 L vector as a
food (314.15 kcal, 24.72 g, 16.7375 g, 16.2225 g, water 453.8695 g). Not at 09:00: the milk at the first request and
the solid at the next, each from its request (the session budget; the hour and state differ, named). The contrast on
equal footing is read on REPLAY ARMS (ruling 11f-3): the milk's landing rows given the solid instead, and the solid's
landing row given the milk (its litres over as many rows as live), every other event as live.

PHASES (the engine's S, H, W; then X; then R, D, Z, the replay):
  X  spawn WaterBottle and MilkSolid; check TKX.MilkSolid's script on the server (item.script); speed 5;
     to_request(MILK): fill the bottle with CowMilk 0.5 and drink it (label MILK); speed 5;
     to_request(SOLID): eat MilkSolid (label SOLID); speed 5; the next request marked; end.
PREDICTIONS:
  R4REQ   the live request minute after the milk's first sip row and after the solid's landing within max(3 min, 2 %)
          of the replay's.
  R4LIQ   the milk lands in the liquid lane: the ring's stomach.liquid rises at the milk's sip rows and not at the
          solid's landing row; and the live stomach.liquid within 2 g of the replay's on every graded row (a reading
          of the lane mass; HUNGER and es are graded by REPLAY).
  REPLAY, H1, RING, F, Z  the engine's.
READINGS: the replay arms' request minutes (milk at the solid's slot and the solid at the milk's), the liquid-over-
solid interval ratio at each slot. No study band (ruling 11f-4).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x265"
ARTIFACT = "liquid.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
SOLID = "TKX.MilkSolid"
BOTTLE, MILK, MILK_L = "Base.WaterBottle", "CowMilk", 0.5
SESSION = ("Plan 11f Task 4 session 5: row 4, 0.5 L CowMilk by drink.action at one request and TKX.MilkSolid (the same "
           "vector) at the next, on the staged copy; one boot of " + PROFILE)
PRED = {
    "R4REQ": {"milk and solid": "live request minute within max(3, 2 %) of the replay's"},
    "R4LIQ": {"liquid lane": "stomach.liquid rises at the milk's sip rows, not at the solid's landing; live within 2 g "
                             "of the replay"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    X["script"] = S.keep(S.step("X_script", L.SRV, "item.script", SOLID))
    S.spawn(BOTTLE, 1, "spawn_bottle")
    S.spawn(SOLID, 1, "spawn_solid")
    S.fast("X_fast0")
    S.to_request("MILK")
    S.drink(BOTTLE, MILK, MILK_L, "MILK")
    S.fast("MILK_fast")
    S.to_request("SOLID")
    S.eat(SOLID, "SOLID")
    S.fast("SOLID_fast")
    S.to_request("X_next")
    S.fast("X_end_fast")


def grade(S, ring, rows_rep):
    import replay_live as RL
    R = S.out["readings"]
    with open(os.path.join(S.run_dir, "events.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    milk_rows = sorted(x["s"] for x in ev if x.get("label") == "MILK")
    solid = next((e for e in S.eats if e["label"] == "SOLID" and e.get("ring_s") is not None), None)
    by_s = {r["s"]: r for r in ring}
    req = {}
    anchors = []
    if milk_rows and milk_rows[0] in by_s:
        anchors.append(("MILK", milk_rows[0], by_s[milk_rows[0]]["age"]))
    if solid is not None:
        anchors.append(("SOLID", solid["ring_s"], solid["ring_age"]))
    for lab, s, a in anchors:
        lv, rp = L.request_after(ring, a), L.request_after(rows_rep, a)
        tol = max(3.0, 0.02 * rp) if rp is not None else None
        req[lab] = {"anchor_s": s, "anchor_age": a, "live_min": lv, "replay_min": rp,
                    "diff_min": (lv - rp) if (lv is not None and rp is not None) else None, "tol_min": tol,
                    "ok": (abs(lv - rp) <= tol) if (lv is not None and rp is not None) else None}
    oks = [v["ok"] for v in req.values()]
    S.out["verdicts"]["R4REQ"] = {"predicted": PRED["R4REQ"], "observed": req,
                                  "verdict": ("as_predicted" if len(oks) == 2 and all(o is True for o in oks) else
                                              ("unmeasured" if not oks or all(o is None for o in oks) else
                                               "falsified"))}
    # the liquid lane
    def dliq(s):
        a, b = by_s.get(s - 1), by_s.get(s)
        if a is None or b is None or L.num(a.get("stomach.liquid")) is None or L.num(b.get("stomach.liquid")) is None:
            return None
        return b["stomach.liquid"] - a["stomach.liquid"]
    rise_milk = [dliq(s) for s in milk_rows]
    rise_solid = dliq(solid["ring_s"]) if solid is not None else None
    rep_by = {r["s"]: r for r in rows_rep}
    worst = 0.0
    n = 0
    for r in ring:
        q = rep_by.get(r["s"])
        if q is None or q.get("between") or q.get("suspect") or q.get("offline"):
            continue
        if L.num(r.get("stomach.liquid")) is None or L.num(q.get("stomach.liquid")) is None:
            continue
        n += 1
        worst = max(worst, abs(r["stomach.liquid"] - q["stomach.liquid"]))
    ok = (bool(rise_milk) and all((x or 0) > 0 for x in rise_milk) and rise_solid is not None
          and rise_solid <= 0.5 and n > 0 and worst <= 2.0)
    S.out["verdicts"]["R4LIQ"] = {"predicted": PRED["R4LIQ"], "observed": {
        "milk_sip_rows": milk_rows, "liquid_rise_at_milk_rows": rise_milk, "liquid_rise_at_solid_row": rise_solid,
        "rows_compared": n, "max_abs_g": worst}, "verdict": "as_predicted" if ok else "falsified"}
    R["requests_anchored"] = req
    # replay arms: swap the two at their slots
    with open(os.path.join(S.run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(S.run_dir, "start-stats.json"), encoding="utf-8") as fh:
        ss = json.load(fh)
    with open(os.path.join(S.run_dir, "player.json"), encoding="utf-8") as fh:
        pl = json.load(fh)
    rr, rp = RL.load_ring([os.path.join(S.run_dir, x) for x in S.ring_files()])
    if milk_rows and solid is not None:
        milk_ev = [x for x in ev if x.get("label") == "MILK"]
        base = [x for x in ev if x.get("label") not in ("MILK", "SOLID")]
        shift = solid["ring_s"] - milk_rows[0]
        swapped = base + [{"s": milk_rows[0], "kind": "eat", "food": SOLID}] + \
            [dict(x, s=x["s"] + shift) for x in milk_ev]
        swapped.sort(key=lambda x: x["s"])
        rows_sw, _ = RL.replay_live(rr, swapped, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
        a_m, a_s = by_s[milk_rows[0]]["age"], solid["ring_age"]
        live_like = {"milk_at_slot1": L.request_after(rows_rep, a_m), "solid_at_slot2": L.request_after(rows_rep, a_s)}
        swap = {"solid_at_slot1": L.request_after(rows_sw, a_m), "milk_at_slot2": L.request_after(rows_sw, a_s)}
        R["swap_arms"] = {"kind": "replay arms (ruling 11f-3): the milk's sips moved to the solid's landing row (as many "
                                  "rows on) and the solid put at the milk's first sip row", "as_live": live_like,
                          "swapped": swap,
                          "liquid_over_solid_slot1": (live_like["milk_at_slot1"] / swap["solid_at_slot1"])
                          if (live_like["milk_at_slot1"] and swap["solid_at_slot1"]) else None,
                          "liquid_over_solid_slot2": (swap["milk_at_slot2"] / live_like["solid_at_slot2"])
                          if (swap["milk_at_slot2"] and live_like["solid_at_slot2"]) else None}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x265_liquid.py",
              scenario, grade).run()
