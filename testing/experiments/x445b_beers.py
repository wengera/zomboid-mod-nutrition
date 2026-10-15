"""x445b-beers -- Plan 14 Task 5 fix round 3, session V4's beer arm again (live): four beers back to back in the vanilla
game and INTOXICATION to 0 (the guide's S6b; gap G5).

WHY A NEW RUN: x445-20261015-175946 graded its coffee, but V4_B_decay and V4_B_zero read unmeasured: two of its four
beer containers (Base.BeerBottle, Base.BeerImported) are sealed in the item scripts, their fluid.fill read back 0 L and
those beers never landed (a driver defect, the ledger's ruling: a fixed new run, not a re-run to fit). This driver runs
only the beer arm, with unsealed containers (x44_beers.BEERS: BeerCan, Pop2, Pop, SodaCan) checked against the install's
item scripts before any run folder is made. The lib x44_guide_lib.py is frozen with x441-x446, so the session's key,
phases and grade are added here (register(), BeerSess) and the lib's BEER_CONTAINERS is overridden in this process.

One boot of profile x44-vanilla-sleep (fixture default, PZTestKit only, Nutrition true, DayLength 4, SleepAllowed and
SleepNeeded true, admin -debug), build 42.21.0. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (V4's phase S and arm B, unchanged in the lib):
  S  the sandbox, the clock's trueMult, minute.ring admin start (no paths), the start's fluid containers
     (autodrink.probe), the model's start; speed 1; stats.set admin thirst 0.
  B  at speed 1, four beers back to back, each in its own container type (BeerCan, Pop2, Pop, SodaCan), spawned by
     RCON, its server copy filled with 0.3 L Beer by fluid.fill (the fill gated: ok, fluid Beer, the probe's first
     container the drink's own), drunk whole by drink.action, INTOXICATION polled to its rise and settle; then polled
     every 2 s until 0 (cap one game hour).
  C  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model.simulate from the run's own start with sleep_allowed true; L.prerun("V4")): each can adds
6.0 INTOXICATION (400 x 0.015, the hunger factor 1 below HUNGER 0.6, #2923), decaying 45.36 a game hour at DayLength 4
(#2922), so the four reach 0 about 0.53 game hours after the first.
  Grades: V4_B_decay (the slope after the last can within 5 % of the model's), V4_B_zero (the first zero read within
  0.05 game hour of the model's; no zero past it falsified); both unmeasured unless all four cans landed past their gate.

WALL: about 4.5 min (boot about 70 s, four cans about 40 s, the decay about 2 min at speed 1, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_beers as BE      # noqa: E402
import x44_guide_lib as L   # noqa: E402

KEY = "V4b"
PROFILE = "x44-vanilla-sleep"
PREFIX = "x445b"
ARTIFACT = "beers.json"
BUDGET_S = 360.0
BEERS = BE.BEERS
SPEC = {"prefix": PREFIX, "profile": PROFILE, "kind": "vanilla", "sleep": True, "artifact": ARTIFACT}
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 fix 3, V4's beer arm: four unsealed beers back to back in the vanilla game with sleep on; "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun("V4"),
    "V4_B_decay": "INTOXICATION's slope after the last can within 5 % of the model's -45.36 a game hour",
    "V4_B_zero": "INTOXICATION first read 0 within 0.05 game hour of the model's zero",
    "beer_containers": list(BEERS),
}


class BeerSess(L.Sess):
    """The lib's session with V4's phase S and beer arm only, and their grade."""

    def phases(self):
        if self.key == KEY:
            return (("S", self.v4_S), ("B", self.v4_B), ("C", self.restore_clock), ("R", self.phase_R))
        return super().phases()

    def grade_v4b(self, model, rows, ev_ages):
        a0 = self.a0
        B = self.D.get("B") or {}
        cans = [c for c in B.get("cans") or [] if c.get("landed") and c.get("fill_ok")]
        if len(cans) < L.V4_BEERS:
            for n in ("V4_B_decay", "V4_B_zero"):
                self.xs.grade(n, "unmeasured", {"why": f"{len(cans)} of {L.V4_BEERS} cans landed with their fill gate",
                                                "cans": B.get("cans")}, "")
            return
        last = max(c.get("settle_age") or c.get("event_age") for c in cans)
        last_ev = max(c["event_age"] for c in cans if c.get("event_age") is not None)
        self._g("V4_B_decay", L.grade_intox_decay(B.get("polls"), last, model, a0),
                "INTOXICATION's decay off the model's 0.504 x day minutes a game hour by more than INTOX_DECAY_REL")
        last_poll = max((p["age"] for p in B.get("polls") or [] if L.num(p.get("age")) is not None), default=None)
        self._g("V4_B_zero", L.grade_intox_zero(B.get("polls"), last_ev, model, a0, last_age=last_poll),
                "INTOXICATION reaching 0 off the model's zero age by more than INTOX_ZERO_TOL_H")
        R = self.out.setdefault("readings", {})
        R["intox_peak"] = max((p["intox"] for p in B.get("polls") or [] if L.num(p.get("intox")) is not None),
                              default=None)
        R["intox_model_peak"] = max((v for _t, v in model.get("intoxication") or []), default=None)


def register():
    """The session's key in the lib's table, the beer containers overridden, the lib's Sess the BeerSess (all in this
    process only; the lib file is untouched)."""
    L.SESSIONS[KEY] = dict(SPEC)
    L.BEER_CONTAINERS = BEERS
    L.Sess = BeerSess


def beers_preboot():
    checks, ok = BE.script_check(BEERS)
    if not ok:
        print(json.dumps(checks, indent=1))
        print("a beer container fails the script check; the session was not started")
        sys.exit(1)
    PRED["beer_script_check"] = checks
    return checks


if __name__ == "__main__":
    beers_preboot()
    register()
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
