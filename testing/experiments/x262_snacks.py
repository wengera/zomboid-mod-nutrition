"""x262-snacks -- Plan 11f Task 4 session 2 (live): research row 2, protein against carbohydrate against fat snacks.
One boot of profile x26-meals (fixture default, admin -debug, Nutrition false, DayLength 1) on the STAGED copy of the
tree (release/x26-meals, staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its
path. Build 42.21.0. The engine is testing/experiments/x26_meals_lib.py (frozen with x261's run). Written BEFORE the
boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

RESEARCH ROW 2 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 2 | Protein vs carbohydrate (isoenergetic) | S1222 (Kohanmoo), S1223 (Dhillon), S1224 (Marmonier, differences), S1384
  (null, checked) | `test_marmonier_snack_delay_differences_bound_the_protein_weight` (p-c 34 vs 26, p-f 26 vs 35, within
  1.5x), `test_a_protein_preload_leaves_less_hunger...`, `test_s1222_vas_level_is_reproduced_at_half_or_more` (0.0134) |
  per arm: `Mixed650` lunch at the request, a 239 kcal `Snack{P,C,F}` (77/84/58 % share) at +240 min, ring to the
  dinner request; base arm with no snack; arms sequential (admin), or two in parallel on fixture `two` | ~100 (4 x 25)
  | 2 (fast; 1 with two players) | dinner-request delays, protein contrast in HUNGER over 3 h | live delays within +-3 min
  of replay; differences' ratio to the study pinned as oracle; S1224's absolute delays and S1222's half-size stay named
  non-reproductions (#3622) |
THE AMENDMENTS: 239 kcal SnackP, SnackC and SnackF at +240 min after a Mixed650 lunch, plus a no-snack base arm. Arms are
sequential on admin, or one arm live and the rest as replay arms (ruling 11f-3).

THE DESIGN, NAMED BEFORE THE RUN: the four arms run live in one session, chained: each arm's dinner request is the next
arm's lunch (base, then P, then C, then F). The lunches therefore fall at different clock times and energy states, so
the live arms' delays against the base arm are confounded by the hour; the clean contrast is read on REPLAY ARMS (ruling
11f-3), labelled as such: for each live snack arm's lunch, the replay of the whole session with that arm's snack
replaced by each of none, SnackP, SnackC and SnackF at the live snack's landing row, every other event as live; the
delays are each arm's dinner request against the no-snack arm's, and p-c, p-f are read per lunch. A lunch and its
snack are eaten at the slow clock; the snack lands at the lunch's polled landing + 240 game minutes (to_age).

PHASES (the engine's S, H, W; then X; then R, D, Z, the replay):
  X  spawn Mixed650; speed 5; at the request (to_request) eat Mixed650 (B650), speed 5; at the next request eat Mixed650
     (P650), speed 5; to_age(P650's landing + 4 h) eat SnackP (SP), speed 5; at the next request eat Mixed650 (C650),
     SnackC (SC) at + 4 h; at the next request Mixed650 (F650), SnackF (SF) at + 4 h; the next request marked (F_dinner)
     and END_TAIL_MIN on; end.
PREDICTIONS:
  R2      every labelled eat's live request minute (after its landing) within max(3 min, 2 %) of the replay's; the
          dinner request of each snack arm is the request after its snack (SP, SC, SF) and of the base arm after B650.
  REPLAY, H1, RING, F, Z  the engine's.
READINGS (graded against the oracle in the grader, not live): per snack-arm lunch, the replay arms' delays p, c, f
over the no-snack arm and p-c, p-f against the oracle's 34 and 26 (study 26 and 35, 1.5x band); the absolute delays
against the oracle's 193/159/167 (S1224's 60/34/25, a named non-reproduction); the live arms' raw delays over the base
arm (confounded by the hour, a reading); the protein contrast: mean HUNGER over the 180 min after each snack, SnackP
arm against SnackC arm on the replay arms.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x262"
ARTIFACT = "snacks.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
MIX650 = "TKX.Mixed650"
SNACKS = {"P": "TKX.SnackP", "C": "TKX.SnackC", "F": "TKX.SnackF"}
SNACK_AFTER_H = 4.0
END_TAIL_MIN = 10
SESSION = ("Plan 11f Task 4 session 2: row 2, four chained arms (base, SnackP, SnackC, SnackF at +240 min after a "
           "Mixed650 lunch at the request), on the staged copy; one boot of " + PROFILE)
PRED = {
    "R2": {"each labelled eat": "live request minute within max(3, 2 %) of the replay's"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    S.out["phases"]["X"] = {}
    S.spawn(MIX650, 1, "B_spawn")
    S.fast("B_fast0")
    S.to_request("B650")
    S.eat(MIX650, "B650")
    S.fast("B_fast")
    for k in ("P", "C", "F"):
        S.spawn(MIX650, 1, k + "_spawn")
        S.spawn(SNACKS[k], 1, k + "_spawn_snack")
        S.fast(k + "_fast0")
        S.to_request(k + "650")
        e = S.eat(MIX650, k + "650")
        S.fast(k + "_fast1")
        land = L.num(e.get("landed_age_polled"))
        if land is None:
            S.note(f"arm {k}: the lunch did not land; the arm stops")
            return
        S.to_age(land + SNACK_AFTER_H, "S" + k)
        S.eat(SNACKS[k], "S" + k)
        S.fast(k + "_fast2")
    S.to_request("F_dinner")
    a = S.age("F_end")
    S.fast("F_tail_fast")
    S.wait_age(a + END_TAIL_MIN / 60.0, "F_tail")


def grade(S, ring, rows_rep):
    req = S.out["readings"].get("requests") or {}
    oks = [v["ok"] for v in req.values()]
    S.out["verdicts"]["R2"] = {"predicted": PRED["R2"], "observed": req,
                               "verdict": ("as_predicted" if oks and all(o is True for o in oks) else
                                           ("unmeasured" if not oks or all(o is None for o in oks) else "falsified"))}
    import replay_live as RL
    R = S.out["readings"]
    with open(os.path.join(S.run_dir, "events.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    with open(os.path.join(S.run_dir, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(S.run_dir, "start-stats.json"), encoding="utf-8") as fh:
        ss = json.load(fh)
    with open(os.path.join(S.run_dir, "player.json"), encoding="utf-8") as fh:
        pl = json.load(fh)
    rr, rp = RL.load_ring([os.path.join(S.run_dir, x) for x in S.ring_files()])
    by = {e["label"]: e for e in S.eats if e.get("ring_s") is not None}
    # the live arms' raw dinner requests: base from B650's landing; a snack arm from its lunch's landing
    live = {}
    for k, lunch in (("base", "B650"), ("P", "P650"), ("C", "C650"), ("F", "F650")):
        e = by.get(lunch)
        if e is None:
            continue
        anchor = by.get("S" + k, e) if k != "base" else e
        off = (anchor["ring_age"] - e["ring_age"]) * 60
        t_live, t_rep = L.request_after(ring, anchor["ring_age"]), L.request_after(rows_rep, anchor["ring_age"])
        live[k] = {"lunch_s": e["ring_s"], "lunch_age": e["ring_age"], "anchor": anchor["label"],
                   "dinner_live_min_from_lunch": (t_live + off) if t_live is not None else None,
                   "dinner_replay_min_from_lunch": (t_rep + off) if t_rep is not None else None}
    R["live_arms"] = live
    # the replay arms: each snack arm's snack replaced by none / P / C / F at its landing row
    arms = {}
    for k in ("P", "C", "F"):
        lunch, snack = by.get(k + "650"), by.get("S" + k)
        if lunch is None or snack is None:
            continue
        res = {}
        for alt in ("none", "P", "C", "F"):
            evs = [x for x in ev if x.get("label") != "S" + k]
            if alt != "none":
                evs.append({"s": snack["ring_s"], "kind": "eat", "food": SNACKS[alt], "label": "arm_" + alt})
            evs.sort(key=lambda x: x["s"])
            rows_arm, _ = RL.replay_live(rr, evs, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
            t = L.request_after(rows_arm, snack["ring_age"])
            res[alt] = {"dinner_min_from_lunch": (t + (snack["ring_age"] - lunch["ring_age"]) * 60) if t else None,
                        "mean_hunger_180_after_snack": L.mean_over(rows_arm, snack["ring_age"], 180)}
        base = res["none"]["dinner_min_from_lunch"]
        d = {a: (res[a]["dinner_min_from_lunch"] - base) if (base and res[a]["dinner_min_from_lunch"]) else None
             for a in ("P", "C", "F")}
        arms[k] = {"lunch_s": lunch["ring_s"], "lunch_age": lunch["ring_age"], "snack_s": snack["ring_s"],
                   "snack_age": snack["ring_age"], "snack_after_lunch_min": (snack["ring_age"] - lunch["ring_age"]) * 60,
                   "arms": res, "delays": d,
                   "p_minus_c": (d["P"] - d["C"]) if (d["P"] is not None and d["C"] is not None) else None,
                   "p_minus_f": (d["P"] - d["F"]) if (d["P"] is not None and d["F"] is not None) else None}
    R["replay_arms"] = {"kind": "replay arms (ruling 11f-3): the live session replayed with one snack replaced by each "
                                "alternative at its landing row, every other event as live", "by_lunch": arms}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x262_snacks.py",
              scenario, grade).run()
