"""x49c_lib -- the session engine of Plan 18 Task 4's second live session, x495 (controller ruling T4-2): the release of
the symptom layer after a snack, which x494-20261021-121229 left unmeasured (its own budget stopped it at phase L).
One boot under 10 wall minutes in a foreground call, build 42.21.0, profile x49-accept (x494's).

Built on testing/experiments/x49b_lib.py (x494's; frozen with that run, imported unchanged): its Sess (the probe's
pairs and trackers, the record writes, the progress placement, the floor seed, the ring, the replay with REPLAY_health
graded to the lapse row), its pure grades and its preboot and main. Its preboot and main are reused with this file's
session bound in (rebind: the same code over this module's SESSIONS, PRERUN_FILE, load_prerun, LIB_FILE and Sess), so
nothing is copied and the frozen file is never edited.

THE BUDGET (measured on x494's artifact, accept.json phase_walls, arms and steps): the boot to ready 74.8 s; S 22.0 s,
H 3.5 s, W 42.1 s, A 22.1 s; a seeded arm cost its pairs plus about 31 s (P1 66.1 s for 35 s of pairs, P2 69.9 s for
39.8 s), a plain arm its pairs plus 10-16 s (ON 79.8 s for 70 s, B 66.1 s for 50 s); the lapse's write and poll 11.9 s;
C 7.2 s, R 2.8 s; a logged bus step about 1 s, the pairs about 2 s apart. x495 spends its budget after the lapse.

THE SESSION x495 release (DayLength 4, sleep off, Realistic, Multiply, Severity 1):
  S   x49b's, with the S pair retried up to S_PAIR_TRIES times until its two reads fall within 1 s (x494's one pair was
      1.012 s apart, P0_BASE unmeasured).
  H, W, A  x49b's (the ring, start.json, x484's seed to the onset at speed 5 with its wall bracket; speed 1).
  P1  x49b's seed at P1_P (the cap 0.355, the floors 0.30 and 25 seeded once at max(read, floor)), with no pairs.
  B   x481's thiamine (wet beriberi at clinical: both lower legs, which keep a Pain 1 under the lower torso's decay after
      the lapse); then the pre-lapse arm, named B: ARM_SETTLE_S, trackers reset, PRE_S of pairs, trackers and parts.
  L   x49b's release at SNACK_M (240, the 200 kcal snack's pool), then L1 (L1_S at speed 1) and L2 (L2_S at SPEED_FAST:
      about L2_GM game minutes, past REL_HEAL_MIN_GM after the lapse and short of STRESS reaching beriberi's 0.06 row
      target).
  C, R  x49b's.

THE GRADES: x49b's pure grades over this schedule's arms (OPT, ONSET, P0_BASE, BERI_ON, H1, RING, Z, REPLAY_ for each
x49b REPLAY_TOL field, PAIN_PART and END_CAP over every arm, PAIN_TARGET at B, PAIN_LEVELS at B and L2, PAIN_FOLLOWS over B and L1, END_LEVELS, STRESS_FLOOR, UNHAPPY_FLOOR, STRESS_LEVELS and
UNHAPPY_LEVELS at B, REL_LAPSE, REL_PAIN, REL_UNHAPPY, REL_STRESS), REL_HEAL for this session (grade_rel_heal_x495:
health held on beriberi's falling target is the drain at work, so a fall counts only under the row's own target; x495
review F1), and REL_END for this session (grade_rel_end_x495): the cap eased by EASE_MIN; no
pull-down below the cap, a fall between pairs counted only when the pair before read under the cap in force less
END_CLIMB_TOL (ENDURANCE climbs from 0.355 to the eased cap about 0.73 in about 57 game minutes of L2_GM, and from then
on the writer pulls it to the cap each minute: the cap at work, not a pull-down); L2's last STEADY_N pairs each side at
its own ENDURANCE's level away from an edge and at most END_EASED_LEVEL_MAX_X495 (B's Endurance 2 eased to 1).
PAIN_ONSET is not graded here: beriberi's legs are set before the onset's window (about 31 s after the onset live), so
the torso-only window does not apply; x494-20261021-121229 measured the onset as predicted. Every tolerance is x49b's. A reading guide or delta built on this run never claims the mod raised
STRESS or UNHAPPINESS to its floor (the seed put each there; x49b's F8).

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49b_lib as B                                                          # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x49_lib as L49                                                         # noqa: E402

REPO = B.REPO
SRV, CLIENT, USER = B.SRV, B.CLIENT, B.USER
LIB_FILE = "x49c_lib.py"
PRERUN_FILE = "testing/experiments/x49c_prerun.json"
PROFILE = "x49-accept"
SESSIONS = {"x495": {"driver": "x495_release.py", "artifact": "release.json", "profile": PROFILE}}
PROFILES = B.PROFILES
STAGED_FROM = B.STAGED_FROM
DAY_MIN = B.DAY_MIN

# ---- the schedule
P1_P = B.P1_P                            # 0.5: the cap 0.355 (Endurance 2), the floors 0.30 (Stress 1) and 25 (Unhappy 1)
SNACK_M = B.SNACK_M                      # 240
PRE_S = 90.0                             # the pre-lapse arm after beriberi: PAIN approaches the summed target from the
                                         # torso's own approach since the onset (about 30 s before the legs' set live,
                                         # under 10 s in the fake world); 90 s puts the last pair over PAIN_TARGET's
                                         # lower edge either way; Pain 2 by about 31 s plus the moodle's timer
L1_S = B.L1_S                            # 16.0 at speed 1: the release's first minutes
L2_S = 70.0                              # at SPEED_FAST: about 93 game minutes (REL_HEAL from 50; STRESS from 0.30 at
                                         # 0.0018 a game minute stays over beriberi's 0.06 row target to about 133);
                                         # 70, not 80, buys 10 s of the budget (x495 review F4)
L2_GM = L2_S / 0.75                      # a game minute 0.75 wall s at speed 5, DayLength 4
S_PAIR_TRIES = 3
END_EASED_LEVEL_MAX_X495 = 1

# ---- the measured costs (x494-20261021-121229, read 2026-10-21 off accept.json)
COST = {"ready": 74.8, "S": 22.0, "H": 3.5, "W": 42.1, "A": 22.1, "seed": 31.0, "arm_over": 16.0, "lapse": 11.9,
        "C": 7.2, "R": 2.8}

ARM_NAMES = ("B", "L1", "L2")
CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple, dict)) and k not in ("REPO", "HERE")}

num = B.num
g = B.g


def load_prerun(path=None):
    return L48.load_prerun(path or os.path.join(REPO, PRERUN_FILE))


def predicted_wall():
    """The phases' end and the call's end in wall seconds from the driver's start, off COST and the schedule."""
    pre = COST["ready"] + COST["S"] + (S_PAIR_TRIES - 1) * 4.0 + COST["H"] + COST["W"] + COST["A"]   # S's retries (F4)
    seed = COST["seed"] - B.ARM_SETTLE_S                  # P1's seed without its arm's settle
    b = 8.0 + B.ARM_SETTLE_S + PRE_S + COST["arm_over"] - B.ARM_SETTLE_S
    lapse = COST["lapse"] + L1_S + 6.0 + L2_S + 6.0
    end_phases = pre + seed + b + lapse + COST["C"] + COST["R"]
    return {"phases_end": end_phases, "lapse_at": pre + seed + b + COST["lapse"],
            "worst_call": end_phases + B.TEARDOWN_QUIT_S + B.TEARDOWN_STOP_S + 10.0}


def grade_rel_end_x495(pairs, inf, a_lapse, cap_before, short=False):
    """REL_END for x495: the cap in force at L2's last pair above cap_before by B.EASE_MIN; no fall over B.END_FALL_EPS
    between valid pairs after the lapse where the pair before read under its larger cap in force less B.END_CLIMB_TOL (a
    fall from the cap that lands at the cap in force is the writer holding the eased cap, x495 review F2); L2's last STEADY_N pairs read, on both sides, their own
    ENDURANCE's level away from an edge (B.L49.FOLLOW_EPS_END), at most END_EASED_LEVEL_MAX_X495, at least
    LEVEL_MIN_PAIRS a side; a short L2 leaves the level bound unmeasured."""
    obs = {"cap_before": cap_before, "short": short, "eased_max": END_EASED_LEVEL_MAX_X495}
    l2 = B.arm_pairs(pairs, "L2")
    if a_lapse is None or not l2 or cap_before is None:
        obs["why"] = "no lapse row, no L2 pair or no B cap"
        return "unmeasured", obs, []
    cap_after = inf.lo(B.pair_age(l2[-1]), "effects.enduranceCap")
    obs["cap_after"] = cap_after
    ps = B.after_pairs(pairs, a_lapse)
    falls, at_cap = [], 0
    for a, b in zip(ps, ps[1:]):
        ea, eb = num(g(a, "s", "endurance")), num(g(b, "s", "endurance"))
        cap = inf.hi(B.pair_age(a), "effects.enduranceCap")
        if ea is None or eb is None or cap is None or eb >= ea - B.END_FALL_EPS:
            continue
        cap_b = inf.lo(B.pair_age(b), "effects.enduranceCap")
        if ea >= cap - B.END_CLIMB_TOL and cap_b is not None and eb >= cap_b - B.END_CLIMB_TOL:
            at_cap += 1                                    # the writer's pull lands on the cap (x495 review F2)
            continue
        falls.append({"tag": b.get("tag"), "from": ea, "to": eb, "cap": cap})
    lv, n_side = [], {"s": 0, "c": 0}
    for p in l2[-B.STEADY_N:]:
        for side in ("s", "c"):
            e, got = num(g(p, side, "endurance")), g(p, side, "lvEnd")
            if e is None or B.near_threshold("endurance", e, L49.FOLLOW_EPS_END):
                continue
            n_side[side] += 1
            lv.append({"tag": p.get("tag"), "side": side, "endurance": e, "got": got,
                       "want": B.level_of("endurance", e)})
    lv_bad = [x for x in lv if x["got"] != x["want"] or x["got"] is None or x["got"] > END_EASED_LEVEL_MAX_X495]
    obs.update({"n_pairs": len(ps), "falls": falls[:10], "falls_at_cap": at_cap, "levels": lv,
                "graded_a_side": n_side, "off_levels": lv_bad[:10]})
    if cap_after is None:
        obs["why"] = "no cap in force at L2's end"
        return "unmeasured", obs, []
    if cap_after < cap_before + B.EASE_MIN or falls:
        return "falsified", obs, ps
    if short:
        obs["why"] = "L2 shortened by the budget: the level bound is unmeasured"
        return "unmeasured", obs, []
    if min(n_side.values()) < B.LEVEL_MIN_PAIRS:
        obs["why"] = f"fewer than {B.LEVEL_MIN_PAIRS} level samples a side away from an edge"
        return "unmeasured", obs, []
    return ("falsified" if lv_bad else "as_predicted"), obs, ps


def git_commit_of(path, repo=REPO):
    """The last commit touching path (short), or None."""
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h", "--", path], cwd=repo, capture_output=True, text=True)
    except OSError:
        return None
    return out.stdout.strip() or None


def grade_rel_heal_x495(rows, i_lapse, rep=None):
    """REL_HEAL for x495 (x495 review F1): x49b's grade_rel_heal, except that health held on beriberi's falling target
    is the drain at work, not a take: a fall counts only under the row's own target (each row's fall on the target is
    about 0.00198 a game minute, and a live row spans 0.931-1.065 game minutes at speed 5, so x49b's REL_HEAL_TOL on
    the step alone falsifies the correct mod). The over-the-target and last-row clauses are x49b's."""
    if i_lapse is None:
        return "unmeasured", {"why": "no lapse row"}, []
    span = [r for r in rows[i_lapse + 1:] if num(r.get("health")) is not None and num(r.get("drain.target")) is not None]
    rep_h = {r.get("s"): num(r.get("health")) for r in rep or []}
    obs = {"n": len(span), "lag": [{"s": r.get("s"), "live": num(r["health"]), "replay": rep_h.get(r.get("s"))}
                                   for r in span[::5]][:40]}
    tol = B.REL_HEAL_TOL
    over = [{"s": r.get("s"), "health": num(r["health"]), "target": num(r["drain.target"])} for r in span
            if num(r["health"]) > num(r["drain.target"]) + tol]
    falls = [{"s": b.get("s"), "from": num(a["health"]), "to": num(b["health"]), "target": num(b["drain.target"])}
             for a, b in zip(span, span[1:])
             if num(b["health"]) < num(a["health"]) - tol and num(b["health"]) < num(b["drain.target"]) - tol]
    obs.update({"over": over[:10], "falls": falls[:10]})
    if over or falls:
        return "falsified", obs, span
    a0 = B.ring_age(rows[i_lapse])
    if not span or a0 is None or (B.ring_age(span[-1]) - a0) * 60.0 < B.REL_HEAL_MIN_GM:
        obs["why"] = f"the ring ends under {B.REL_HEAL_MIN_GM} game minutes past the lapse row"
        return "unmeasured", obs, []
    last = span[-1]
    obs["last_gap"] = num(last["drain.target"]) - num(last["health"])
    return ("as_predicted" if abs(obs["last_gap"]) <= tol else "falsified"), obs, span


class Sess(B.Sess):
    """x495's phases on x49b_lib.Sess."""

    def __init__(self, xs, key, run_dir=None, prerun=None):
        self.out = xs.out
        super().__init__(xs, "x494", run_dir=run_dir, prerun={} if prerun is None else prerun)
        self.key = key
        self.spec = SESSIONS[key]
        self.prof = PROFILES[self.spec["profile"]]
        self.P = prerun if prerun is not None else load_prerun().get(key, {})
        self.out["lib_x49c"] = LIB_FILE
        self.out["lib_x49b"] = B.LIB_FILE                  # the engine under this lib (x495 review F5)
        self.out["lib_x49b_commit"] = git_commit_of("testing/experiments/" + B.LIB_FILE)
        self.out["constants_x49c"] = dict(CONSTANTS)
        self.out["prerun_x49c"] = self.P

    def phase_S(self):
        super().phase_S()
        P = self.D["S"]
        tries = [P["pair"]]
        while not tries[-1].get("valid") and len(tries) < S_PAIR_TRIES:
            self.xs.sleep(1.0)
            tries.append(self.pair(f"S_pair{len(tries) + 1}", "S"))
        P["pair_tries"] = len(tries)
        P["pair"] = next((p for p in tries if p.get("valid")), tries[-1])

    def phase_P1(self):
        self.seed("P1", P1_P)

    def phase_B(self):
        L48.Sess.phase_B(self)
        self.arm("B", PRE_S)

    def phase_L(self):
        P = self.D["L"] = {}
        self.set_speed(1, "L_one")
        P["pre"] = self.rec("L_pre", ("drain.mask", "drain.pS", "effects.enduranceCap", "effects.stressFloor",
                                      "effects.unhappyFloor", "moodLast.u", "satiety.M"), log=True)
        P["set_M"] = self.write("L_M", "satiety.M", f"{SNACK_M}")

        def fn():
            v = self.rec("L_poll", ("drain.mask", "drain.recovering", "drain.pS"))
            return v.get("drain.mask") is not None and not B.has_bit(v.get("drain.mask"), B.MASK_STARVE), v
        P["poll"] = self.poll("L_lapse", fn, B.LAPSE_CAP_S, B.POLL_S)
        P["after"] = self.rec("L_after", ("drain.mask", "drain.recovering", "drain.pS", "effects.enduranceCap",
                                          "effects.stressFloor", "effects.unhappyFloor", "moodLast.u"), log=True)
        self.arm("L1", L1_S, settle=False)
        self.set_speed(B.SPEED_FAST, "L_fast")
        self.arm("L2", L2_S, settle=False)

    def phases(self):
        return [("S", self.phase_S), ("H", self.phase_H), ("W", self.phase_W48), ("A", self.phase_A),
                ("P1", self.phase_P1), ("B", self.phase_B), ("L", self.phase_L), ("C", self.phase_C),
                ("R", self.phase_R)]

    def grade_symptoms(self, rows, rep):
        inf = B.InForce(rows, rep or [])
        dm = num(rows[0].get(B.OPT_DAYMIN)) if rows else None
        dm = dm or DAY_MIN
        inj = self.injury
        short = tuple(n for n in ARM_NAMES if self.arm_short(n))
        self.out["arms_short"] = list(short)
        reads = {}
        for name in ("B",):
            pe = self.arm_rec(name).get("parts_end") or {}
            if pe.get("parts"):
                reads[name] = {"age": pe.get("age"), "parts": pe.get("parts")}
        self._g3("PAIN_PART", B.grade_part(self.pairs, inf, reads, ("B",), dm),
                 "the lower torso's added pain, or a painful part at the pre-lapse arm's end, outside its band")
        self._g3("PAIN_TARGET", B.grade_pain_target(self.pairs, "B", inf, dm, inj, short),
                 "the server's PAIN outside its band at the pre-lapse arm's end")
        self._g3("PAIN_LEVELS", B.grade_pain_levels(self.pairs, inf, dm, inj, arms=("B", "L2"), short=short),
                 "an arm's last pairs reading a Pain level other than the replay's mid PAIN's")
        self._g3("PAIN_FOLLOWS", L49.grade_follows(self.pairs, ("B", "L1"), "pain", "pain", "lvPain", B.FOLLOW_EPS),
                 "a side's Pain level off its own PAIN's")
        self._g3("END_CAP", B.grade_end_cap(self.pairs, inf, ARM_NAMES), "the server's ENDURANCE over the cap in force")
        trk = {n: self.arm_rec(n).get("trk") for n in ARM_NAMES}
        self._g3("END_LEVELS", B.grade_held_levels(self.pairs, inf, trk, "lvEnd", "endurance",
                                                   lambda r: num(r.get("effects.enduranceCap")), ("B",)),
                 "a pair or a tracker reading an Endurance level other than the cap's")
        self._g3("STRESS_FLOOR", B.grade_stress_floor(self.pairs, inf, ("B",)), "the server's STRESS under its floor")
        self._g3("UNHAPPY_FLOOR", B.grade_unhappy_floor(self.pairs, inf, rows, {"B": self.arm_span("B")}, ("B",)),
                 "the server's UNHAPPINESS under its floor, or the writer's target under the floor")
        self._g3("STRESS_LEVELS", B.grade_held_levels(self.pairs, inf, trk, "lvStress", "stress",
                                                      lambda r: num(r.get("effects.stressFloor")), ("B",)),
                 "a pair or a tracker reading a Stress level other than the floor's")
        self._g3("UNHAPPY_LEVELS", B.grade_held_levels(self.pairs, inf, trk, "lvUnhappy", "unhappy",
                                                       lambda r: num(r.get("effects.unhappyFloor")), ("B",)),
                 "a pair or a tracker reading an Unhappy level other than the floor's")
        a_m = num(g(self.D, "L", "set_M", "age"))
        self._g("REL_LAPSE", B.grade_lapse(rows, a_m), "no row with starvation lapsed and beriberi active")
        i_l = B.lapse_index(rows, a_m)
        a_l = B.ring_age(rows[i_l]) if i_l is not None else None
        pb = B.arm_pairs(self.pairs, "B")
        cap_b = inf.hi(B.pair_age(pb[-1]), "effects.enduranceCap") if pb else None
        fl_b = inf.lo(B.pair_age(pb[-1]), "effects.stressFloor") if pb else None
        self._g3("REL_PAIN", B.grade_rel_pain(self.pairs, a_l, dm),
                 "the lower torso's added pain set again, or falling off vanilla's decay, after the lapse")
        self._g3("REL_END", grade_rel_end_x495(self.pairs, inf, a_l, cap_b, "L2" in short),
                 "the cap not eased, ENDURANCE pulled down, or an end level off its own or over level 1")
        self._g3("REL_UNHAPPY", B.grade_rel_unhappy(rows, self.pairs, a_m),
                 "UNHAPPINESS not dropping by the target's fall at once, or Unhappy shown after the release")
        self._g3("REL_STRESS", B.grade_rel_stress(self.pairs, a_l, fl_b, "L2" in short),
                 "STRESS raised after the lapse, falling off vanilla's decay, or an end level off the prediction")
        self._g3("REL_HEAL", grade_rel_heal_x495(rows, i_l, rep),
                 "health over its target, taken after the lapse, or short of the target REL_HEAL_MIN_GM past it")


def _rebind(fn, **names):
    """x49b's function over x49b's globals with this module's session bound in (same code, nothing copied)."""
    gl = dict(fn.__globals__)
    gl.update(names)
    return types.FunctionType(fn.__code__, gl, fn.__name__, fn.__defaults__, fn.__closure__)


def preboot(key, driver_file, repo=REPO, compute=None):
    """x49b's preboot over x495's session and prerun."""
    if compute is None:
        import x49c_prerun as PR
        compute = PR.compute
    return _rebind(B.preboot, SESSIONS=SESSIONS, PRERUN_FILE=PRERUN_FILE, load_prerun=load_prerun)(
        key, driver_file, repo, compute)


parse_argv = B.parse_argv


def main(key, driver_file, session_text, pred, budget_s):
    """x49b's main (doctor, the dirty gates, the staged gate, memory, the lint, the boot, the bounded teardown, the
    copy) over x495's session, preboot, lib name and Sess."""
    return _rebind(B.main, SESSIONS=SESSIONS, preboot=preboot, LIB_FILE=LIB_FILE, Sess=Sess, PRERUN_FILE=PRERUN_FILE,
                   CONSTANTS=dict(B.CONSTANTS, **CONSTANTS))(key, driver_file, session_text, pred, budget_s)
