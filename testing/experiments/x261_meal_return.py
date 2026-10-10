"""x261-meal-return -- Plan 11f Task 4 session 1 (live): the speed-5 gating window (ruling S0-1), then research row 1,
the single-meal hunger return. One boot of profile x26-meals (fixture default, admin -debug, Nutrition false, DayLength
1) on the STAGED copy of the tree at HEAD (release/x26-meals; `python tools/release_pack.py stage mod/NutritionRevamp
--out release/x26-meals` before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The
engine is testing/experiments/x26_meals_lib.py (frozen with this run). Written BEFORE the boot with every prediction in
it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

RESEARCH ROW 1 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 1 | Single-meal hunger return | S1247 (Callahan 2004), S1248 (Cummings 2004) | `test_a_650_kcal_mixed_meal_holds_
  hunger_off_for_four_to_five_hours` (240-300 x 1.1, <= 425), `test_a_fasted_400_kcal_breakfast...` (>= 180 min),
  `test_one_meal_or_three_items...` (equal +-2 min) | warm-up day; wait to the request (written HUNGER >= 0.25); eat
  `TKX_StudyFoods.Mixed650`; ring to the next request; next morning a fasted `Mixed400` at 08:00; then three `Mixed217`
  items at once | ~48 | 1 (fast) | request minute after the landing, held-below duration, P, stomach mass | live request
  within +-3 min of replay-of-live; replay-of-live within the oracle's band (the oracle holds circadian at 1, live does
  not: reported) |
THE AMENDMENTS (task-4-amendments.md): `Mixed650`, then the fasted `Mixed400`, then three `Mixed217` at once. The first
fast session opens with a speed-5 window of at least 60 game minutes containing at least one eat, and that window's
replay must read ok under the tolerances before any row is graded at speed 5; if it fails, stop and report.

DEPARTURES FROM THE ROW, NAMED BEFORE THE RUN:
  - No separate warm-up day (the session budget): the gate's Mixed650 (eaten at speed 5 at about 12:00, not at the
    request) and request-level eating through the first evening stand in for it; es is whatever the live body reads,
    and the replay starts from the live record (ruling 11f-4: the study figure is a reading on the live body).
  - "At once" is three eat actions queued one after another at the slow clock (each waits for the last to land, with
    foodtimer.set 0 between: FOOD_EATEN refuses an eat at level 3, #0077); about 1.5-2 game minutes apart. The
    oracle's partition-invariance is read on a replay arm (ruling 11f-3: the three Mixed217 substituted by one Mixed650
    at the first one's landing row, on the live clock and record), labelled as a replay arm.
  - The admin stays awake all night (sleep off in the profile; the sleep factor inert, #2961); thirst is left to the
    writer's cap 0.83 (no water is drunk, autodrink off), so no drink lands outside the logged events.

PHASES (the engine's S, H, W; then X, this driver's scenario; then R, D, Z, the replay):
  X.G  the gate: RCON additem Mixed650; RCON settimespeed 5 (window start a0); eat.action Mixed650 at speed 5; wait to
       max(a0 + GATE_MIN, landing + 60 min); a1; minute.ring read (pages copied as gate-*.json); replay_live from W's
       start record over the pages; the diff restricted to replay rows aged in [a0, a1].
       GATE as_predicted: the window >= 60 game minutes, >= GATE_ROWS_MIN graded rows, the eat landed inside it, and
       the windowed diff ok (HUNGER 0.002, es 0.005, L 0.5 %). Else falsified, and the scenario stops there (speed 1,
       R, D): every fast row would then run slow (amendments).
  X.R1 at speed 5 the next request (to_request: HUNGER >= 0.246 at speed 5, then speed 1 to >= 0.25, then the slow
       clock), eat Mixed650 (label R1a), back to speed 5; again at each later request whose read age is before
       CUTOFF_AGE (22:30 on day 0), labels R1b, R1c; after the last, no eat until 08:00.
  X.F  to_age(FAST_AGE = 25.0, 08:00 day 1): eat Mixed400 at the slow clock (label F400), speed 5.
  X.T  the next request: three Mixed217 (labels T217a, T217b, T217c), speed 5; the next request marked (T_next) and
       END_TAIL_MIN game minutes on; end.

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  GATE  as above.
  R1    every labelled eat's live request minute (the first ring row after its landing row with HUNGER >= 0.25, after it
        first fell below) is within max(3 min, 2 %) of the replay's (the engine's `requests`).
  REPLAY  the whole session's replay diff ok under the plan's tolerances.
  H1, RING, F, Z  the engine's (paths resolved and the ring armed; pages read, errors 0; the departure flush; no mod
        error line, admin not parked).
READINGS (not graded live; the grader names each one's distance from the oracle pin):
  R1a/R1b intervals against the oracle's 320 min (650 kcal from the request at 13:50, the factor 1; band 240/1.1-330 and
  <= 425; studies S1247 247-321, S1248 320-425); F400's held-below minutes against >= 180; T217 against the replay arm's
  one Mixed650 (oracle: equal; spread within 2 min); P and stomach mass at each landing.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x261"
ARTIFACT = "meal-return.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
MIX650, MIX400, MIX217 = "TKX.Mixed650", "TKX.Mixed400", "TKX.Mixed217"
GATE_MIN = 75
GATE_ROWS_MIN = 50
CUTOFF_AGE = 15.5          # 22:30 on day 0 (world age 0 is 07:00, #2890)
FAST_AGE = 25.0            # 08:00 on day 1
END_TAIL_MIN = 10
SESSION = ("Plan 11f Task 4 session 1: the speed-5 gating window, then row 1 (a Mixed650 at each request, a fasted "
           "Mixed400 at 08:00, three Mixed217 at the next request), on the staged copy; one boot of " + PROFILE)
PRED = {
    "GATE": {"window game minutes": ">= 60", "graded rows": f">= {GATE_ROWS_MIN}", "eat landed inside": True,
             "windowed diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "R1": {"each labelled eat": "live request minute within max(3, 2 %) of the replay's"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    # -- G: the speed-5 gating window
    S.spawn(MIX650, 1, "G_spawn")
    fs = S.fast("G_fast")
    a0 = L.num(fs.get("worldAge"))
    S.mark("gate_start")
    e = S.eat(MIX650, "G650")
    land = L.num(e.get("landed_age_polled"))
    target = max(a0 + GATE_MIN / 60.0, (land if land is not None else a0) + 1.0)
    S.wait_age(target, "G_wait")
    a1 = S.age("G_end")
    S.mark("gate_end")
    pages = S.read_pages("G", prefix="gate-")
    files = [p["file"] for p in pages if p.get("file")]
    G = X["gate"] = {"a0": a0, "a1": a1, "window_min": (a1 - a0) * 60 if (a0 is not None and a1 is not None) else None,
                     "files": files, "eat": {k: e.get(k) for k in ("landed", "landed_age_polled")}}
    RP = S.replay(files, window=(a0, a1), write=False)
    RP.pop("_rows", None)
    RP.pop("_ring", None)
    RP.pop("_events", None)
    G["replay"] = RP
    in_win = e.get("ring_age") is not None and a0 <= e["ring_age"] <= a1
    graded = None
    fields = L.g(RP, "diff", "fields") or {}
    if fields:
        graded = max((v.get("n") or 0) for v in fields.values())
    G["eat_ring_age"], G["eat_in_window"], G["graded_rows"] = e.get("ring_age"), in_win, graded
    ok = bool(L.g(RP, "diff", "ok")) and in_win and (G["window_min"] or 0) >= 60 and (graded or 0) >= GATE_ROWS_MIN
    S.out["verdicts"]["GATE"] = {"predicted": PRED["GATE"], "observed": {
        "window_min": G["window_min"], "graded_rows": graded, "eat_in_window": in_win,
        "diff_ok": L.g(RP, "diff", "ok"), "fields": fields, "classes": L.g(RP, "diff", "classes"),
        "findings": L.g(RP, "diff", "findings")}, "verdict": "as_predicted" if ok else "falsified"}
    S.persist()
    if not ok:
        S.note("GATE falsified: the scenario stops; every fast row would run slow (amendments)")
        S.one("G_stop_one")
        return
    # -- R1: a Mixed650 at each request before the cutoff
    for lab in ("R1a", "R1b", "R1c"):
        S.spawn(MIX650, 1, lab + "_spawn")
        S.fast(lab + "_fast0")
        r = S.to_request(lab, cap_age=CUTOFF_AGE)
        if r is None:
            break
        if r["age"] is not None and r["age"] >= CUTOFF_AGE:
            S.mark(lab + "_after_cutoff", hunger=r["hunger"])
            break
        S.eat(MIX650, lab)
        S.fast(lab + "_fast")
    # -- F: the fasted Mixed400 at 08:00
    S.spawn(MIX400, 1, "F400_spawn")
    S.fast("F_fast0")
    S.to_age(FAST_AGE, "F400")
    S.eat(MIX400, "F400")
    S.fast("F_fast")
    # -- T: three Mixed217 at the next request
    S.spawn(MIX217, 3, "T217_spawn")
    r = S.to_request("T217")
    if r is not None:
        for lab in ("T217a", "T217b", "T217c"):
            S.eat(MIX217, lab)
        S.fast("T_fast")
        S.to_request("T_next")
        a = S.age("T_end")
        S.fast("T_tail_fast")
        S.wait_age(a + END_TAIL_MIN / 60.0, "T_tail")


def grade(S, ring, rows_rep):
    """R1 and the readings the session can compute without the oracle host (the grader adds the oracle pins)."""
    req = S.out["readings"].get("requests") or {}
    lab = [k for k in req if k.startswith(("R1", "F400", "T217", "G650"))]
    oks = [req[k]["ok"] for k in lab]
    S.out["verdicts"]["R1"] = {"predicted": PRED["R1"], "observed": {k: req[k] for k in lab},
                               "verdict": ("as_predicted" if oks and all(o is True for o in oks) else
                                           ("unmeasured" if not oks or all(o is None for o in oks) else "falsified"))}
    R = S.out["readings"]
    # the held-below minutes of F400: the first ring row below 0.25 after the landing, then the return
    f = next((e for e in S.eats if e["label"] == "F400" and e.get("ring_age") is not None), None)
    if f is not None:
        out = {}
        for name, rows in (("live", ring), ("replay", rows_rep)):
            first = next((r for r in rows if L.num(r.get("age")) is not None and r["age"] > f["ring_age"] + 1e-12
                          and L.num(r.get("HUNGER")) is not None and r["HUNGER"] < L.H_REQ), None)
            back = L.request_after(rows, f["ring_age"])
            out[name] = {"first_below_min": ((first["age"] - f["ring_age"]) * 60) if first else None,
                         "return_min": back,
                         "held_min": (back - (first["age"] - f["ring_age"]) * 60) if (first and back) else None}
        R["F400_held"] = out
    # the replay arm: the three Mixed217 replaced by one Mixed650 at the first one's landing row (ruling 11f-3)
    t = [e for e in S.eats if e["label"].startswith("T217") and e.get("ring_s") is not None]
    if t:
        import json
        import replay_live as RL
        with open(os.path.join(S.run_dir, "events.json"), encoding="utf-8") as fh:
            ev = json.load(fh)
        with open(os.path.join(S.run_dir, "start.json"), encoding="utf-8") as fh:
            start = json.load(fh)
        with open(os.path.join(S.run_dir, "start-stats.json"), encoding="utf-8") as fh:
            ss = json.load(fh)
        with open(os.path.join(S.run_dir, "player.json"), encoding="utf-8") as fh:
            pl = json.load(fh)
        arm = [x for x in ev if x.get("label") not in ("T217a", "T217b", "T217c")]
        arm.append({"s": t[0]["ring_s"], "kind": "eat", "food": MIX650, "label": "T_one650_arm"})
        arm.sort(key=lambda x: x["s"])
        files = S.ring_files()
        rr, rp = RL.load_ring([os.path.join(S.run_dir, x) for x in files])
        rows_arm, _ = RL.replay_live(rr, arm, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
        a0 = t[0]["ring_age"]
        R["T217_arm"] = {"kind": "replay arm (ruling 11f-3): the three Mixed217 replaced by one Mixed650 at the first "
                                 "one's landing row, on the live clock and record",
                         "landings": [(e["label"], e.get("ring_s"), e.get("ring_age")) for e in t],
                         "three_live_min": L.request_after(ring, a0), "three_replay_min": L.request_after(rows_rep, a0),
                         "one650_arm_min": L.request_after(rows_arm, a0)}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x261_meal_return.py",
              scenario, grade).run()
