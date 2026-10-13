"""x361-course -- Plan 11g Task 8 session 1 (live): two meal time courses of different size on the final satiety model.
One boot of profile x36-gut (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED copy
of the tree at the final build (release/x36-gut, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x36_gut_lib.py (frozen with this run).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE TASK 8 AMENDMENTS (copied in substance): two meals of different size from TKX_StudyFoods; HUNGER and M rung every
minute for 4-6 game hours; graded live against the replay at the 11f tolerances; a HUNGER-within-DEFAULT_TOL assertion
restored on a ring recorded on this build (the Task 4 and 6c review notes: the 11f rings were recorded on P).

THE DESIGN, NAMED BEFORE THE RUN:
  The live body is the default fixture's admin (male, lean 65.6 kg, fat 14.4 kg), awake (sleep off, #2961), no drink
  (no container carried, the server's autodrink flag false: THIRST rises toward the writer's cap over the session, as
  in x261), so no sip lands outside the logged events.
  X: TKX.Mixed650 and TKX.Mixed400 spawned; speed 5 to the first request (to_request: HUNGER >= 0.246 at speed 5, then
     speed 1 to >= 0.25, then the slow clock; cap at world age CAP_AGE); eat Mixed650 (label C650) at the slow clock;
     its course at speed 1 (Session.course: until HUNGER is back at 0.25 after falling below and at least MIN_H game
     hours after the landing, or MAX_H), paired client/server stats every PAIR_M game minutes; then eat Mixed400
     (label C400) at once at the slow clock, its course the same way; end at speed 1.
  The two meals are 650 and 400 kcal of the oracles' mixed composition (Mixed400 carries 250 g water); each from the
  request its own course ends at (the second meal's hour and state differ from the first's: named, a reading).
PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  COURSE   for each of C650 and C400, over the rows from its landing row to its course's end, live against the replay
           (x36_gut_lib.course_reading, TOL_GRADE): HUNGER within 0.002, es within 0.005, L within 0.5 % (the 11f
           tolerances), satiety.M within 0.5 % (floor 1), the physical and the food fill within 0.002, the buffer kcal
           within 0.5 % (floor 0.5); the live request minute within max(3, 2 %) of the replay's (both none when capped).
  REPLAY   the whole session's replay diff ok under DEFAULT_TOL (HUNGER 0.002, es 0.005, L 0.5 %): the HUNGER
           assertion restored on this build.
  GRADE_DIFF  the whole session under TOL_GRADE (the lib's).
  PAIRS    every paired read's client and server HUNGER within 0.002 where the pair's wall gap is within one second
           (a reading of the client's copy; the writer owns HUNGER).
  H1, RING, F, Z  the engine's.
READINGS (the study distance, never graded: ruling 8-R): C650's live request minute against the oracle anchor 240-300
  min (S1247, S1248; the hard replays' band 218-330); C400's held-below minutes against >= 180 (the fasted 400 kcal
  breakfast anchor; this one is at a request, not fasted at 08:00: named); each nadir's minute against harvest 11's
  15-30 min (inference); the M and fill series every 15 minutes.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x36_gut_lib as L   # noqa: E402

PROFILE = "x36-gut"
PREFIX = "x361"
ARTIFACT = "course.json"
STAGE_ROOT = "release/x36-gut/NutritionRevamp"
STAGED_AT = "7093079b"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
CAP_AGE = 16.0                 # 23:00 on day 0: the first request's cap
MIN_H = 4.0
MAX_H = 6.0
PAIR_M = 30.0
PAIR_TOL = 0.002
SESSION = ("Plan 11g Task 8 session 1: a Mixed650 at the first request and a Mixed400 at the next, each course at speed "
           "1, on the staged copy; one boot of " + PROFILE)
PRED = {
    "COURSE": {"C650 and C400": "live within TOL_GRADE of the replay on every graded row; request within max(3, 2 %)"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "GRADE_DIFF": {"whole session": "ok under TOL_GRADE"},
    "PAIRS": {"paired reads": "client HUNGER within 0.002 of the server's where the wall gap is within 1 s"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    S.spawn(L.MIX650, 1, "spawn_650")
    S.spawn(L.MIX400, 1, "spawn_400")
    S.fast("X_fast")
    X["r0"] = S.to_request("R0", cap_age=CAP_AGE)
    if X["r0"] is None:
        S.out["deviations"].append("the first request never came before CAP_AGE; C650 eaten at the cap")
    S.eat(L.MIX650, "C650")
    S.course("C650", MIN_H, MAX_H, pair_every_m=PAIR_M)
    S.eat(L.MIX400, "C400")
    S.course("C400", MIN_H, MAX_H, pair_every_m=PAIR_M)
    S.one("X_end_one")
    X["done"] = True


def grade(S, ring, rows_rep):
    R, V = S.out["readings"], S.out["verdicts"]
    by_lab = {e["label"]: e for e in S.eats}
    out, oks = {}, []
    for c in S.courses:
        e = by_lab.get(c["label"]) or {}
        a0, a1 = e.get("ring_age"), c.get("end_age")
        if a0 is None or a1 is None:
            out[c["label"]] = {"error": "no landing row or no course end", "eat": e.get("ring_s")}
            oks.append(None)
            continue
        cr = L.course_reading(ring, rows_rep, a0, a1)
        cr["landing_s"] = e.get("ring_s")
        cr["capped"] = c.get("capped")
        out[c["label"]] = cr
        oks.append(cr["ok"])
    R["courses"] = out
    V["COURSE"] = {"predicted": PRED["COURSE"],
                   "observed": {k: {"ok": v.get("ok"), "request": v.get("request"),
                                    "fields": L.g(v, "diff", "fields"), "findings_n": L.g(v, "diff", "findings_n")}
                                for k, v in out.items()},
                   "verdict": ("unmeasured" if not oks or all(o is None for o in oks) else
                               "as_predicted" if all(o is True for o in oks) and len(oks) == 2 else "falsified")}
    pr = []
    for p in S.pairs:
        gap = L.num(p.get("wall_gap"))
        c, s = L.g(p, "client", "HUNGER"), L.g(p, "server", "HUNGER")
        if gap is None or abs(gap) > L.PAIR_GAP_MAX_S or c is None or s is None:
            pr.append({"tag": p["tag"], "graded": False, "wall_gap": gap})
            continue
        pr.append({"tag": p["tag"], "graded": True, "d": c - s, "ok": abs(c - s) <= PAIR_TOL, "wall_gap": gap})
    g_ = [x for x in pr if x["graded"]]
    V["PAIRS"] = {"predicted": PRED["PAIRS"], "observed": pr,
                  "verdict": ("unmeasured" if not g_ else "as_predicted" if all(x["ok"] for x in g_) else "falsified")}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x361_course.py",
              scenario, grade).run()
