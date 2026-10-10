"""x263-volume -- Plan 11f Task 4 session 3 (live): research row 3, part 1 -- Rolls 1999's three preloads (Casserole,
Soup, Casserole with 356 mL of water drunk) read at minute 17, and the water-only foods' minute-1 fullness. One boot
of profile x26-meals (fixture default, admin -debug, Nutrition false, DayLength 1) on the STAGED copy of the tree
(release/x26-meals, staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path.
Build 42.21.0. The engine is testing/experiments/x26_meals_lib.py (frozen with x261's run). Written BEFORE the boot
with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

RESEARCH ROW 3 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 3 | Energy density and volume | S1231 (Rolls 1999), S1233 (Rolls 1998, check), S1232 (Marciani), S1235 (Goetze),
  S1230 (Robinson), S1229 (Rolls 1999 ED) | `test_rolls_1999_soup_casserole...` (1.1x), `test_soup_sates_more...`,
  `test_fullness_is_linear...` (r2 > 0.999), `test_a_less_energy_dense_meal_sates_more` | from the request:
  `Casserole`, `Soup` (same + 356 g water), `Casserole` + 356 mL water by `drink.action`; HUNGER at minute 17 (slow
  clock around the eat); `Marc` solid+water vs soup over 3 h; `Dense400@0.8` vs `@1.6` over 15 h; water-only foods
  100-600 g at minute 1 | ~60 | 2 (mixed slow/fast) | HUNGER at minute 17 -> intake mapping (kJ), 3 h means, minute-1
  fullness | live within 0.002 of replay at the reading minute; replay's Rolls ratios vs 1.1x (oracle) |
THE AMENDMENTS: Casserole against Soup against Casserole + 356 mL water (`drink.action` with a vanilla water fluid the
mod's table carries; check `IN.fluidVector`). Water-only foods at minute 1. Slow the clock around readings within 30
game minutes of an eat. (Marc/MarcSoup and Dense400Lo/Hi are session 4, x264.)

THE DESIGN, NAMED BEFORE THE RUN: each arm is eaten at its own request (to_request), so the arms sit at different
clock times and states; live is graded against the replay at the reading minute, and the clean study contrast is read
on REPLAY ARMS (ruling 11f-3) in which the first Rolls arm's eat is replaced by each arm's food (and the water drink) at
the same landing row. The water is Base.WaterBottle's server copy refilled with 0.356 L of Water (fluid.fill, server;
the mod's fluid table carries Water, 999 g water a litre) and drunk by drink.action right after the casserole lands
(x151's route: the server drinks its own copy, #3149); its litres are split over the ring rows whose sips rose. The
water-only arms are eaten at successive requests; each lowers HUNGER a little and the request returns soon.

PHASES (the engine's S, H, W; then X; then R, D, Z, the replay):
  X  spawn Casserole, Soup, Casserole, WaterBottle (both copies prefilled) and Water100..Water600; speed 5;
     for arm in CAS, SOUP, CW: to_request(arm); eat (CW: then fluid.fill the bottle with Water 0.356 and drink it);
       stay slow to the landing + READ_MIN game minutes; speed 5.
     for W in 100..600: to_request(W<n>); eat Water<n>; stay slow to the landing + 3 game minutes; speed 5.
     The next request marked; end. The budget may stop the water arms early (recorded as budget_stop).
PREDICTIONS:
  R3M17   at each Rolls arm, the live HUNGER at minute 17 after the landing (interpolated between the ring rows either
          side) within 0.002 of the replay's at the same minute.
  R3M1    at each water arm, the live HUNGER at minute 1 after the landing within 0.002 of the replay's.
  R3REQ   every labelled eat's live request minute within max(3 min, 2 %) of the replay's.
  REPLAY, H1, RING, F, Z  the engine's.
READINGS (graded against the oracle in the grader): the replay arms' minute-17 HUNGER through the intake mapping (kJ =
10878.4 x HUNGER) against S1231's 1209 (soup) / 1657 (casserole + water) / 1639 (casserole) kJ and the drop 448 kJ, at
1.1x, and the oracle's own figures; the water arms' minute-1 HUNGER: decreasing in the mass and r2 of the line on a
replay-arm set (each water food at the first water arm's landing row) against > 0.999.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x263"
ARTIFACT = "volume.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
CAS, SOUP = "TKX.Casserole", "TKX.Soup"
BOTTLE, WATER, WATER_L = "Base.WaterBottle", "Water", 0.356
WATERS = [("W%d" % n, "TKX.Water%d" % n) for n in (100, 200, 300, 400, 500, 600)]
READ_MIN = 18
M1_MIN = 3
KJ_PER_HUNGER = 650.0 * 4.184 / 0.25
SESSION = ("Plan 11f Task 4 session 3: row 3 part 1, Rolls 1999's three preloads read at minute 17 and the water-only "
           "foods at minute 1, each from its request, on the staged copy; one boot of " + PROFILE)
PRED = {
    "R3M17": {"each Rolls arm": "live HUNGER at minute 17 within 0.002 of the replay's"},
    "R3M1": {"each water arm": "live HUNGER at minute 1 within 0.002 of the replay's"},
    "R3REQ": {"each labelled eat": "live request minute within max(3, 2 %) of the replay's"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    S.out["phases"]["X"] = {}
    S.spawn(CAS, 2, "spawn_cas")
    S.spawn(SOUP, 1, "spawn_soup")
    S.spawn(BOTTLE, 1, "spawn_bottle")
    for lab, full in WATERS:
        S.spawn(full, 1, "spawn_" + lab)
    S.fast("X_fast0")
    for lab, full in (("CAS", CAS), ("SOUP", SOUP), ("CW", CAS)):
        S.to_request(lab)
        e = S.eat(full, lab)
        if lab == "CW" and e.get("landed"):
            S.drink(BOTTLE, WATER, WATER_L, "CW_water")
        land = L.num(e.get("landed_age_polled"))
        if land is not None:
            S.wait_age(land + READ_MIN / 60.0, lab + "_read")
        S.fast(lab + "_fast")
    for lab, full in WATERS:
        S.to_request(lab)
        e = S.eat(full, lab)
        land = L.num(e.get("landed_age_polled"))
        if land is not None:
            S.wait_age(land + M1_MIN / 60.0, lab + "_read")
        S.fast(lab + "_fast")
    S.to_request("X_next")
    S.fast("X_end_fast")


def _arm(RL, rr, rp, start, ss, pl, ev, drop_labels, add):
    evs = [x for x in ev if x.get("label") not in drop_labels] + add
    evs.sort(key=lambda x: x["s"])
    rows, _ = RL.replay_live(rr, evs, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
    return rows


def grade(S, ring, rows_rep):
    import replay_live as RL
    R = S.out["readings"]
    req = R.get("requests") or {}
    by = {e["label"]: e for e in S.eats if e.get("ring_s") is not None}
    m17, m1 = {}, {}
    for lab in ("CAS", "SOUP", "CW"):
        e = by.get(lab)
        if e is None:
            continue
        lv, rpv = L.at_minute(ring, e["ring_age"], 17), L.at_minute(rows_rep, e["ring_age"], 17)
        m17[lab] = {"landing_s": e["ring_s"], "live": lv, "replay": rpv,
                    "diff": (lv["value"] - rpv["value"]) if (lv and rpv) else None}
        m17[lab]["ok"] = (abs(m17[lab]["diff"]) <= 0.002) if m17[lab]["diff"] is not None else None
    for lab, _ in WATERS:
        e = by.get(lab)
        if e is None:
            continue
        lv, rpv = L.at_minute(ring, e["ring_age"], 1), L.at_minute(rows_rep, e["ring_age"], 1)
        m1[lab] = {"landing_s": e["ring_s"], "live": lv, "replay": rpv,
                   "diff": (lv["value"] - rpv["value"]) if (lv and rpv) else None}
        m1[lab]["ok"] = (abs(m1[lab]["diff"]) <= 0.002) if m1[lab]["diff"] is not None else None
    for name, d in (("R3M17", m17), ("R3M1", m1), ("R3REQ", req)):
        oks = [v.get("ok") for v in d.values()]
        S.out["verdicts"][name] = {"predicted": PRED[name], "observed": d,
                                   "verdict": ("as_predicted" if oks and all(o is True for o in oks) else
                                               ("unmeasured" if not oks or all(o is None for o in oks) else
                                                "falsified"))}
    # replay arms (ruling 11f-3)
    with open(os.path.join(S.run_dir, "events.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    with open(os.path.join(S.run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(S.run_dir, "start-stats.json"), encoding="utf-8") as fh:
        ss = json.load(fh)
    with open(os.path.join(S.run_dir, "player.json"), encoding="utf-8") as fh:
        pl = json.load(fh)
    rr, rp = RL.load_ring([os.path.join(S.run_dir, x) for x in S.ring_files()])
    first = by.get("CAS")
    if first is not None:
        s0, a0 = first["ring_s"], first["ring_age"]
        drops = ("CAS", "SOUP", "CW", "CW_water") + tuple(w for w, _ in WATERS)
        water_ev = [x for x in ev if x.get("label") == "CW_water"]
        shift = (water_ev[0]["s"] - by["CW"]["ring_s"]) if (water_ev and by.get("CW")) else 2
        arms = {}
        for name, add in (("cas", [{"s": s0, "kind": "eat", "food": CAS}]),
                          ("soup", [{"s": s0, "kind": "eat", "food": SOUP}]),
                          ("cw", [{"s": s0, "kind": "eat", "food": CAS},
                                  {"s": s0 + max(0, shift), "kind": "drink", "fluid": WATER, "litres": WATER_L}])):
            rows = _arm(RL, rr, rp, start, ss, pl, ev, drops, add)
            h = L.at_minute(rows, a0, 17)
            arms[name] = {"hunger_m17": h["value"] if h else None,
                          "kj": KJ_PER_HUNGER * h["value"] if h else None}
        R["rolls_arms"] = {"kind": "replay arms (ruling 11f-3): every Rolls and water eat removed, then one arm's food "
                                   "(and for cw the water, as many rows after as live) at the first Rolls landing row",
                           "landing_s": s0, "landing_age": a0, "arms": arms}
    w0 = by.get("W100")
    if w0 is not None:
        drops = tuple(w for w, _ in WATERS)
        out = {}
        for lab, full in WATERS:
            rows = _arm(RL, rr, rp, start, ss, pl, ev, drops, [{"s": w0["ring_s"], "kind": "eat", "food": full}])
            h = L.at_minute(rows, w0["ring_age"], 1)
            out[lab] = h["value"] if h else None
        xs = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
        ys = [out[lab] for lab, _ in WATERS]
        r2 = None
        if all(y is not None for y in ys):
            mx, my = sum(xs) / 6, sum(ys) / 6
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            sxx = sum((x - mx) ** 2 for x in xs)
            syy = sum((y - my) ** 2 for y in ys)
            r2 = (sxy * sxy / (sxx * syy)) if syy > 0 else None
        R["water_arms"] = {"kind": "replay arms (ruling 11f-3): every water eat removed, then one water food at the "
                                   "W100 landing row", "landing_s": w0["ring_s"], "minute1": out, "r2": r2,
                           "decreasing": all(a > b for a, b in zip(ys, ys[1:])) if all(y is not None for y in ys)
                           else None}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x263_volume.py",
              scenario, grade).run()
