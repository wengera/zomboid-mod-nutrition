"""x276-sixmeals -- Plan 11f Task 5 (live): research row 8, six meals against three, on a FRESH fixture (one session,
no chain). One boot of profile x27-energy (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on
the STAGED copy of the tree (release/x27-energy, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x27_energy_lib.py (frozen with x271's run;
not edited: this driver overrides two of its methods in a subclass, named below). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

WHY A FRESH SESSION, NOT x275: the chain's admin died at world age 113.78 (00:46 on chain day 4, in x273-20261010-142109,
"players: admin is dead"): the record's fluids read na -1,804 mmol and water -3,550 g, the hyponatraemia band
(finding F-T5-1, for the controller: the basal loss carries sodium whatever the intake, about 337 mmol a day on this
body, and the study foods carry none). x274 and x275 cannot run on a dead body; they stay unrun. Row 8 does not need the
chain (research row 8: a warm-up day, then the six-meal day), and its 45 game hours on a fresh record stay far from the
sodium band, so it runs here as the research row describes, with no water stops (the oracle's six-against-three water
is the meals' own 900 g; Task 4's sessions ran 53 h without water).

RESEARCH ROW 8 (01-harness-facts.md s6, copied): | 8 | Six meals vs three | S1608 (Ohkawara 2013), S1607 (Raynor 2015) |
`test_six_meals_against_three_is_pinned_inside_the_band` (0.969, state held), `..._with_the_energy_state_live_is_pinned`
(0.994) | warm-up day; from 08:00 admin eats three `Mixed667`, bob six `Mixed333` every 150 min (fixture `two`), same mass
| ~48 | 1 (fast) | 24 h mean written HUNGER per arm | ratio within 1 % of replay-of-live and within [0.9, 1.3]; S1608's
direction stays a named non-reproduction (#3622) |
THE AMENDMENTS (copied): Row 8: three Mixed667 from 08:00, against six Mixed333 every 150 min, on sequential days or one
arm as a replay arm; the 24 h mean written-HUNGER ratio within 1 % of the replay, and within [0.9, 1.3].

THE DESIGN, NAMED BEFORE THE RUN: the warm-up is the fixture's first afternoon, Mixed667 at 13:00 and 18:00 on day -1
(the oracle's warm days eat three Mixed667 at 08:00, 13:00 and 18:00 for SIX_WARM_DAYS = 3 days; the fresh record's
empty trailing window starts at its first sight, about 11:00). Day 0: six Mixed333 at 08:00, 10:30, 13:00, 15:30,
18:00 and 20:30 (ages 25.0 to 37.5), the live arm; the window is 08:00 day 0 to 08:00 day 1 (ages 25 to 49); the
session ends at age 49.3. The three-Mixed667 arm is a replay arm of this session (ruling 11f-3): its replay of live with
the six Mixed333 eats replaced by Mixed667 at 08:00, 13:00 and 18:00, on the ring's clock (x27_grade.py). Each stop runs
at speed 1 from 5 game minutes before its age (the lib's to_stop); everything else at speed 5.
THE SUBCLASS (this driver's own code, the lib untouched): (1) run_phase: the lib's budget and error marks pass phase=
into Timeline.mark(phase, ...), a TypeError that escapes run_phase and skips R, D and Z (finding F-T5-2, x273 lost its
ring and its departure flush that way); this driver's copy marks them under other key names; (2) run_schedule: this
driver's own stop list (SCHED below) with a "w667" kind (one Mixed667 at the stop); the lib's verbs otherwise.

PREDICTIONS (graded in `verdicts`): STOPS every stop done, every eat landed; REPLAY the session's replay of live
(sleep_allowed false) ok under HUNGER 0.002, es 0.005, L 0.5 %, the auto-drink detector finding none; H1, RING, F, Z the
engine's. READINGS (x27_grade.py): the live 24 h mean written HUNGER from 08:00 day 0 and its replay; the three-arm's;
six over three predicted about 0.98 (the 70 kg man on the server path: 0.981 live, 0.969 held; the chain's offline
prediction on this body 0.981), within [0.9, 1.3], and live within 1 % of the replay's ratio.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x27_energy_lib as L   # noqa: E402

PROFILE = "x27-energy"
PREFIX = "x276"
ARTIFACT = "energy-6.json"
STAGE_ROOT = "release/x27-energy/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 49.3
ROW8_T0 = L.at(0, 8.0)         # 25.0
SCHED = [(L.at(-1, 13.0), "w667", "Wm1_13"), (L.at(-1, 18.0), "w667", "Wm1_18")] + \
        [(ROW8_T0 + 2.5 * k, "six", "S0_%d" % k) for k in range(6)]
SESSION = ("Plan 11f Task 5: row 8, six Mixed333 against three Mixed667 (a replay arm) on a fresh fixture, on the "
           "staged copy; one boot of " + PROFILE)
PRED = {
    "STOPS": {"every stop": "done, none missed, every eat landed"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), auto-drinks detected 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"row8_ratio": 0.98, "band": [0.9, 1.3], "agree": 0.01},
}


class Session(L.Session):
    def run_phase(self, name, fn):
        self.cur = name
        self.out["phase_walls"][name] = {"start": self.wall()}
        try:
            fn()
        except L.Budget as e:
            self.out["budget_stop"] = {"phase": name, "why": str(e), "wall": self.wall()}
            self.tl.mark("budget_stop", stopped_phase=name)
            self.note(f"phase {name} stopped: {e}")
        except Exception as e:                     # noqa: BLE001
            self.out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
            self.tl.mark("error", failed_phase=name, detail=str(e)[:200])
            self.note(f"phase {name} raised: {type(e).__name__}: {e}")
        self.out["phase_walls"][name]["end"] = self.wall()
        self.persist()

    def run_schedule(self):
        X = self.out["phases"].setdefault("X", {})
        a0 = self.age("X_a0")
        X["start_age"], X["end_age"] = a0, self.end_age
        todo, missed, late = [], [], []
        for age, kind, label in SCHED:
            if a0 is not None and age < a0:
                (late if a0 - age < L.LATE_MAX_H else missed).append(label)
                if a0 - age < L.LATE_MAX_H:
                    todo.append((age, kind, label))
                continue
            todo.append((age, kind, label))
        X["late"], X["missed"] = late, missed
        if missed or late:
            self.out["deviations"].append(f"stops missed {missed}, late {late}")
        for age, kind, label in todo:
            self.check()
            self.to_stop(age, label)
            if kind == "six":
                self.six(label, age)
            else:
                st = {"label": label, "kind": kind, "sched_age": age}
                self.stops.append(st)
                b = self.body_read(label + "_body")
                st["read"] = {"es": b.get("energyState"), "age": self.age(label + "_t")}
                landed, labs = self.eat_all([(L.MIX667, 1)], label)
                st["eats"], st["landed"] = labs, landed
            self.persist()
        self.check()
        a = self.age("X_tail_a")
        if a is not None and a < self.end_age:
            self.fast("X_tail_fast")
            self.wait_age(self.end_age, "X_tail_wait")
        self.one("X_end_one")
        X["done"] = True


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x276_sixmeals_fresh.py",
            scenario, grade, end_age=END_AGE).run()
