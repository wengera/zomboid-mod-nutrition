"""x45h_lib -- the session engine of x453b (Plan 15 Task 11, live review F6): Overfull 4, the refused eat and the nausea
re-measured after x453 never reached Overfull 4. x45g_lib.py is frozen with x452-x457, so this lib imports it unchanged
and adds only x453b's phases, its grades' wiring and the review's F3/F4 fixes; its main patches the frozen module's
session table, session class and lib name in the driver's process only (x445b's precedent: a driver overriding a frozen lib's constants in its
own process).

THE SESSION (x453b, profile x45g-mod, the staged copy at x45g_lib.STAGED_FROM):
  S, H (x453's ring), F (SPAWN_B Base.Broccoli by RCON),
  SEED  the true multiplier to SLOW_MULT_B (0.05: a game minute 12.5 wall s, so a networked eat, which ends in real
        time, #3766, costs under half a game minute of emptying); record.set stomach.buffer.calories SEED_KCAL FIRST
        (the lane then empties at its slow energy rate, not as water: x453's seed lost about 50 g when a writer minute fell
        between a water set and a calories set), then stomach.buffer.water to bring the stomach to SEED_G_B (Overfull 3);
        the stomach read again, and the water re-set once (logged) when it reads under SEED_MIN_G.
  X     one Broccoli eaten (about +30 g, past 1100 g); the server's food timer polled every TIMER_POLL_S until it reads
        above 3200 (refusing(): the writer has seen Overfull 4) or TIMER_CAP_S; the trigger read (the stomach bracketed,
        a pair, FOOD_SICKNESS, SICK); then x453's refusal block (the stomach at the attempt, eat.action, a pair 1.5 s into
        the 8 s wait, the landing and the mass after), action.cancel, and the hold's bracketed reads for HOLD_GM_B game
        minutes (so ENDURANCE has settled reads two settles past the landing).
  C     action.cancel; the clock restored from S's read.  R  the ring read.

THE GRADES are x453's (x45g_lib.grade_of_*, Sess.grade_x453), on the same checks.X keys, with two changes from the
review: PAIRS_foodEaten admits server reads to PAIR_SLACK_B (0.8 s) after the client read, so a pair's own later server
read counts (F3); and every pair is saved under checks.pairs (F4). OF_REACH reads the one eat's level before it and the
trigger read's level after it.

FROZEN WITH ITS FIRST RUN: once x453b has run, this file is never edited (CLAUDE.md s5).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x45g_lib as G                                                          # noqa: E402

LIB_FILE = "x45h_lib.py"
SESSIONS = {"x453b": {"driver": "x453b_overfull.py", "artifact": "overfull.json"}}
SLOW_MULT_B = 0.05
SEED_G_B = 1085.0
SEED_MIN_G = 1070.0
SPAWN_B = 3
TIMER_POLL_S = 0.5
TIMER_CAP_S = 60.0
HOLD_GM_B = 3.5
PAIR_SLACK_B = 0.8
CONSTANTS = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, (int, float, str))}



class Sess(G.Sess):
    """x453b's phases on x45g_lib.Sess."""

    def __init__(self, xs, key, run_dir=None):
        super().__init__(xs, "x453" if key in SESSIONS else key, run_dir=run_dir)
        if key in SESSIONS:
            self.key, self.spec = key, SESSIONS[key]
        self.out["constants_x45h"] = dict(CONSTANTS)
        self.out["lib_x45h"] = LIB_FILE

    def phases(self):
        if self.key != "x453b":
            return super().phases()
        return [("S", self.phase_S), ("H", self.phase_H), ("F", self.phase_F_b), ("SEED", self.phase_SEED_b),
                ("X", self.phase_X_b), ("C", self.phase_C453), ("R", self.phase_R)]

    def phase_H(self):
        key, self.key = self.key, "x453"                                     # x453's ring paths
        try:
            super().phase_H()
        finally:
            self.key = key

    def phase_F_b(self):
        self.D["F"] = {"broccoli": self.spawn(G.BROCCOLI, SPAWN_B, "F_broc")}

    def phase_SEED_b(self):
        P = self.D["SEED"] = {}
        P["slow"] = self.set_mult(SLOW_MULT_B, "SEED_slow")
        st = self.stomach("SEED_st0")
        P["before"] = st
        w = G.num(st["values"].get("stomach.buffer.water"))
        cal = G.num(st["values"].get("stomach.buffer.calories"))
        if st["mass"] is None or w is None:
            raise RuntimeError(f"the stomach did not read: {st}")
        P["calories"] = self.record_set("SEED_kcal", "stomach.buffer.calories", f"{max(cal or 0.0, G.SEED_KCAL):.3f}")
        P["water"] = self.record_set("SEED_water", "stomach.buffer.water", f"{w + (SEED_G_B - st['mass']):.3f}")
        st1 = self.stomach("SEED_st1")
        P["after"] = st1
        if st1["mass"] is not None and st1["mass"] < SEED_MIN_G:
            w1 = G.num(st1["values"].get("stomach.buffer.water")) or 0.0
            P["reset"] = self.record_set("SEED_water2", "stomach.buffer.water", f"{w1 + (SEED_G_B - st1['mass']):.3f}")
            P["after_reset"] = self.stomach("SEED_st2")
            self.xs.note(f"SEED: the stomach read {st1['mass']} g after the seed, under {SEED_MIN_G}; water re-set once")

    def phase_X_b(self):
        P = self.D.setdefault("X", {})
        P["eats"] = []
        seed_age = G.num(G.g(self.D, "SEED", "water", "age"))
        pre = self.of_read("X_pre0", seed_age)       # settled against the seed: the writer has not yet seen it
        e = self.eat(G.BROCCOLI, "X_eat0")
        e["pre_level"], e["pre_mass"] = pre["level"], pre["mass"]
        P["eats"].append(e)
        if not e["landed"]:
            self.xs.note(f"X_eat0: not landed (validStart {e.get('validStart')!r}) at Overfull {pre['level']}")
            return
        last_land = e["landed_age"]
        polls = P.setdefault("timer_polls", [])

        def fn():
            s = self.stats("X_timer")
            polls.append({"age": s.get("worldAge"), "timer": s.get("foodTimer"), "wall": s.get("wall"),
                          "foodEaten": G.g(s, "moodles", "foodEaten")})
            return G.refusing({"timer": s.get("foodTimer")}), s
        P["timer_poll"] = {k: v for k, v in self.poll("X_timer", fn, TIMER_CAP_S, TIMER_POLL_S).items() if k != "last"}
        trig = self.of_read("X_trig", last_land)
        e["post_level"], e["post_mass"] = trig["level"], trig["mass"]
        trig["food_sick"] = self.food_sick("X_trig_fs")
        trig["sick"] = G.num(self.moodle("X_trig_sick", "SICK").get("level"))
        P["trigger"] = trig
        if trig["level"] != 4 or not G.refusing(trig):
            self.xs.note(f"X: no refusal attempt: the trigger read Overfull {trig['level']}, timer {trig['timer']}")
            return
        ref = {"pre_level": trig["level"], "mass0": trig["mass"], "timer0": trig["timer"], "settled": trig["settled"],
               "food_eaten0": trig["food_eaten"]}
        st0 = self.stomach("X_ref_st0")
        ref["level_at_attempt"], ref["mass_at_attempt"] = st0["level"], st0["mass"]
        b = self.intake("X_ref_before")
        t_ref = self.xs.clock()
        q = self.k("X_ref_eat", G.CLI, "eat.action", f"{G.BROCCOLI} 1")
        ref.update({k: q.get(k) for k in ("queued", "spawned", "validStart", "moodleFoodEaten", "maxTime")})
        self.sleep_until(self.xs.clock() + G.PUSH_S + 0.3)
        P["trigger_pair"] = self.pair("X_trig_pair")
        self.sleep_until(t_ref + G.REFUSE_WAIT_S)
        a = self.intake("X_ref_after")
        ref["landed"] = (a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"])
        ref["mass1"] = self.stomach("X_ref_st")["mass"]
        P["refusal"] = ref
        P["cancel"] = self.k("X_ref_cancel", G.CLI, "action.cancel")
        P["hold"] = self.of_read("X_hold0", last_land)
        end = (G.num(trig.get("age")) or self.age("X_hold_a") or 0.0) + HOLD_GM_B / 60.0
        self.run_until(end, SLOW_MULT_B, "X_hold", every_s=G.PAIR_EVERY_S, fn=lambda x: self.of_read("X_hold", last_land),
                       mult=True)

    def grade_all(self):
        self.D["pairs"] = list(self.pairs)                                     # review F4
        super().grade_all()

    def grade_x453b(self, rows):
        saved = G.PAIR_SLACK_S
        G.PAIR_SLACK_S = PAIR_SLACK_B                                          # review F3, this grade only
        try:
            self.grade_x453(rows)
            self.out["verdicts"]["PAIRS_foodEaten"]["observed"]["pair_slack_s"] = PAIR_SLACK_B
        finally:
            G.PAIR_SLACK_S = saved


def main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file):
    G.SESSIONS.update(SESSIONS)                                                # this process only: preboot and main
    G.Sess = Sess
    G.LIB_FILE = LIB_FILE
    return G.main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file)
