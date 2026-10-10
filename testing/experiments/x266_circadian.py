"""x266-circadian -- Plan 11f Task 4 session 6 (live): research row 5, the circadian factor -- identical Mixed650 meals
at 19:00 and 08:00 on successive days, the factor read at every minute, and the 19:00 dinner's wake-up HUNGER. One boot
of profile x26-meals (fixture default, admin -debug, Nutrition false, DayLength 1) on the STAGED copy of the tree
(release/x26-meals, staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build
42.21.0. The engine is testing/experiments/x26_meals_lib.py (frozen with x261's run). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

RESEARCH ROW 5 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 5 | Circadian | S1273 (Scheer 2013) | `test_circadian_peaks_at_19_50_and_troughs_at_07_50`, `test_callahans_replay_
  minutes...the_09_00_factor_matters`; 11c amendment "dinner at 19:00 wakes at about 0.34" | warm-up day; identical
  `Mixed650` at 08:00 and at 19:00 on two days; ring through each return | ~48 | 1 (fast) | written HUNGER over the
  day; ratio written/replay-without-factor | factor within 1 % of `1 + 0.085 cos(2pi(h - 19.833)/24)` at every minute
  (`NR_Kernel_Satiety.lua:41-42, 126-127`); 19:00 dinner's wake-up HUNGER vs the amendment's 0.34 as a reading |
THE AMENDMENTS: identical Mixed650 at 08:00 and at 19:00. Check the factor within 1 % of 1 + 0.085 cos(2pi(h - 19.833)/24)
at every minute (read the constant from NR_Kernel_Satiety.lua; do not trust this formula over the code). Read the 19:00
dinner's wake-up HUNGER as a reading.

THE DESIGN, NAMED BEFORE THE RUN: the warm-up is the first afternoon's request-level Mixed650s (requests read before
17:30); then Mixed650 at 19:00 on day 0, 08:00 on day 1, 19:00 on day 1 and 08:00 on day 2, each at its fixed time
whatever the HUNGER, nothing eaten between them (so the 08:00 meals follow a 13 h fast and the 19:00 meals an 11 h one).
The admin stays awake (sleep off, #2961): "wake-up" is the written HUNGER at 07:00 the next morning, read off the ring.
The factor is the live HUNGER over a replay without the factor (the same replay with the mod's own K.satiety.circadian
replaced by 1 in the replay host, every other line the mod's), on every graded row whose HUNGER is below the cap on both
sides; the expected factor is the code's constants (CIRCADIAN_A, CIRCADIAN_PEAK_H parsed from NR_Kernel_Satiety.lua)
at the hour of the drain that wrote the row (the previous ring row's age, through the replay's hour offset).

PHASES (the engine's S, H, W; then X; then R, D, Z, the replay):
  X  speed 5; Mixed650 at each request read before WARM_CUTOFF (labels W1, W2); to_age(12.0) Mixed650 (E19d0);
     to_age(25.0) (E08d1); to_age(36.0) (E19d1); to_age(49.0) (E08d2); the next request marked; end.
PREDICTIONS:
  R5FAC   the live factor within 1 % of the code's formula at every compared row (and the replay's own factor too).
  R5REQ   every labelled eat's live request minute within max(3 min, 2 %) of the replay's.
  REPLAY, H1, RING, F, Z  the engine's.
READINGS: each fixed meal's return minute (live and replay), 08:00 against 19:00; the written HUNGER at 07:00 after each
19:00 dinner against the 11c amendment's 0.34.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x26_meals_lib as L   # noqa: E402

PROFILE = "x26-meals"
PREFIX = "x266"
ARTIFACT = "circadian.json"
STAGE_ROOT = "release/x26-meals/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 760.0
MIX650 = "TKX.Mixed650"
WARM_CUTOFF = 10.5             # 17:30 on day 0 (world age 0 is 07:00, #2890)
FIXED = (("E19d0", 12.0), ("E08d1", 25.0), ("E19d1", 36.0), ("E08d2", 49.0))
WAKES = (("WAKE_d1", 24.0, "E19d0"), ("WAKE_d2", 48.0, "E19d1"))
SATIETY_LUA = "mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua"
SESSION = ("Plan 11f Task 4 session 6: row 5, Mixed650 at 19:00 and 08:00 on successive days, the factor at every "
           "minute and the wake-up HUNGER, on the staged copy; one boot of " + PROFILE)
PRED = {
    "R5FAC": {"every compared row": "live HUNGER / no-factor replay within 1 % of the code's circadian formula"},
    "R5REQ": {"each labelled eat": "live request minute within max(3, 2 %) of the replay's"},
    "REPLAY": {"whole session diff": "ok"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    S.out["phases"]["X"] = {}
    S.spawn(MIX650, 6, "spawn")
    S.fast("X_fast0")
    for lab in ("W1", "W2"):
        r = S.to_request(lab, cap_age=WARM_CUTOFF)
        if r is None or (r["age"] is not None and r["age"] >= WARM_CUTOFF):
            S.fast(lab + "_skip_fast")
            break
        S.eat(MIX650, lab)
        S.fast(lab + "_fast")
    for lab, age in FIXED:
        S.fast(lab + "_fast0")
        S.to_age(age, lab)
        S.eat(MIX650, lab)
        S.fast(lab + "_fast")
    S.to_request("X_next")
    S.fast("X_end_fast")


def constants():
    with open(os.path.join(L.REPO, SATIETY_LUA), encoding="utf-8") as fh:
        src = fh.read()
    a = float(re.search(r"K\.satiety\.CIRCADIAN_A\s*=\s*([0-9.]+)", src).group(1))
    p = float(re.search(r"K\.satiety\.CIRCADIAN_PEAK_H\s*=\s*([0-9.]+)", src).group(1))
    return a, p


def grade(S, ring, rows_rep):
    import replay_live as RL
    R = S.out["readings"]
    req = R.get("requests") or {}
    oks = [v["ok"] for v in req.values()]
    S.out["verdicts"]["R5REQ"] = {"predicted": PRED["R5REQ"], "observed": req,
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

    class NoCircadian(RL.ServerReplay):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.rt.execute("NutritionRevamp.kernel.satiety.circadian = function(h) return 1 end")

    orig = RL.ServerReplay
    RL.ServerReplay = NoCircadian
    try:
        rows_nc, be = RL.replay_live(rr, ev, start, paths=rp, user=L.USER, player=pl, start_stats=ss)
    finally:
        RL.ServerReplay = orig
    amp, peak = constants()
    off = be.R.offset
    ring_by = {r["s"]: r for r in rr}
    rep_by = {r["s"]: r for r in rows_rep}
    prev_age = {}
    for i in range(1, len(rr)):
        prev_age[rr[i]["s"]] = rr[i - 1]["age"]
    worst_live = worst_rep = 0.0
    n = 0
    over = []
    for q in rows_nc:
        s = q["s"]
        if q.get("between") or q.get("suspect") or q.get("offline") or s not in ring_by or s not in prev_age:
            continue
        hn, hl, hr = L.num(q.get("HUNGER")), L.num(ring_by[s].get("HUNGER")), L.num((rep_by.get(s) or {}).get("HUNGER"))
        if hn is None or hl is None or hn <= 0 or hn * (1 + amp) >= 0.69 - 1e-9 or hl >= 0.69 - 1e-9:
            continue
        tod = math.fmod(prev_age[s] + off, 24.0)
        exp = 1 + amp * math.cos(2 * math.pi * (tod - peak) / 24.0)
        fl = hl / hn
        dl = abs(fl / exp - 1)
        n += 1
        worst_live = max(worst_live, dl)
        if hr is not None:
            worst_rep = max(worst_rep, abs((hr / hn) / exp - 1))
        if dl > 0.01:
            over.append({"s": s, "tod": tod, "live_factor": fl, "expected": exp, "rel": dl})
    S.out["verdicts"]["R5FAC"] = {"predicted": PRED["R5FAC"], "observed": {
        "constants": {"CIRCADIAN_A": amp, "CIRCADIAN_PEAK_H": peak}, "hour_offset": off, "rows_compared": n,
        "max_rel_live": worst_live, "max_rel_replay": worst_rep, "over_1pct": over[:20], "over_n": len(over)},
        "verdict": "as_predicted" if (n > 0 and not over) else ("unmeasured" if n == 0 else "falsified")}
    by = {e["label"]: e for e in S.eats if e.get("ring_s") is not None}
    fixed = {}
    for lab, _ in FIXED:
        e = by.get(lab)
        if e is None:
            continue
        fixed[lab] = {"landing_age": e["ring_age"], "tod": math.fmod(e["ring_age"] + off, 24.0),
                      "live_return_min": L.request_after(ring, e["ring_age"]),
                      "replay_return_min": L.request_after(rows_rep, e["ring_age"]),
                      "nofactor_return_min": L.request_after(rows_nc, e["ring_age"])}
    wakes = {}
    for lab, age, after in WAKES:
        lv = L.at_minute(ring, age, 0)
        rpv = L.at_minute(rows_rep, age, 0)
        wakes[lab] = {"age": age, "after": after, "live": lv["value"] if lv else None,
                      "replay": rpv["value"] if rpv else None, "amendment_11c": 0.34}
    R["fixed_meals"] = fixed
    R["wakes"] = wakes


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x266_circadian.py",
              scenario, grade).run()
