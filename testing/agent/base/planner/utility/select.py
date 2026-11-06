"""The scores and the commitment (Plan 31 Task 11 U; the proposal's § 2 "Scores" and "Commitment"): each candidate's
utility as a sum of named terms, linear in the five weights (`weights.py`) with H, the cost of one hit, the unit;
and the `Selector`, which holds the chosen act for its minimum span and replaces it only when a rival beats it by the
margin, re-scoring at once on the five interrupts.

THE TERMS (`terms(c, sit, ctx, models)` -> {term: raw value}; the score is sum over terms of W[term] x raw, W the
weight each term is read in, `TERM_WEIGHT`; the decision line logs each weighted term):
- `kill` (K): P_kill, the chance the act kills its target within its span. A fight's: 1 - (1 - p)^presses, p the kill
  chance of one press (`models.Models.p_press`: the finish's at a fallen zombie, else the swing's divided by the arms'
  pain [#4370], each under the moodles [#4371]; spent, the arms' pain over 10 or a moodle at level 2 (the spec's
  § 4 item 2b), the shove and stomp: a shove's knock-down (P_KNOCK [#4373], less 0.05 per endurance level) then
  STOMPS_PER_DOWN finish presses), presses the span left after the approach over the press's seconds.
- `hit` (H = 1): minus the expected hits over the act's span (`exposure`: each zombie's hazard `models.hazard(d)`,
  summed; a standing zombie that is aware arrives at MELEE_D after (d - MELEE_D) / its closing speed (CHASE_MIN at
  least) and stands there; an unaware one counts UNAWARE_FACTOR of its hazard where it is; a fallen one
  FALLEN_FACTOR). A retreat's is the hits it saves: the exposure of fighting the aware group here at once less one at
  a time at the filter, over the group's kill time, less the route's.
- `bleed` (B): bleeding-part minutes, minus those the act's span lets run, plus, for a dress, the BLEED_HORIZON_M
  minutes of the part it dresses.
- `chase` (C): 1 for a fight at a standing zombie that chases (`hasTarget`, PZA/1.9's `known` not false) while armed:
  the doctrine in one number (a lone chaser is met anyway; running removes no hits).
- `goal` (V): the goal's progress: GOAL_VALUE for travel, loot and sneak, NEED_VALUE for the needs, REST_VALUE per
  endurance moodle level for the rest.
- `regress` (G): minus the tiles a retreat runs off, over 10.

`TERM_SIGN` (all 1) is the mutation pass's seam (a sign flipped, a term dropped); `DELTA0` and `DELTA_FRAC` the
margin's (delta = 0 their mutation).

THE COMMITMENT (`Selector.decide`): over the eligible candidates (`eligible`: not vetoed, a retreat only above
RETREAT_FLOOR, since one saving no hits is an open-ground leg, and a fallback only above FALLBACK_FLOOR; the held
act stays eligible whatever its score, so a retreat taken runs to its filter though the group's count changes the
score on the way). With nothing held, or the held act ended, vetoed or no longer generated, the best candidate is
taken (`select` "new", "end", "gone"). Otherwise it is kept (`held_by`): `cadence` between selections (one each
SELECT_S, unless an interrupt fires), `span` inside its minimum span (SPAN_S; a dress and a retreat until
their own end), `margin` while no rival beats it by delta = DELTA0 + DELTA_FRAC x |U_held|; a rival that does is taken
(`select` "beat"). An interrupt (a new hit reaction, a part newly bleeding, a standing zombie not the act's target
entering NEAR_R, a goal answer; the act's own end is the `end` above) re-scores at once and lifts the span, but never a
retreat's, whose span runs to its filter (the proposal's guard against the closed-loop cycle). A retarget inside the
fight takes the same margin. Ties go to the KINDS order, then the key.
"""
import math

from agent.base.planner.policies import DANGER_R, DRAG_DOWN_N as PDRAG_N, SNEAK_R
from agent.base.planner.utility import acts as A
from agent.base.planner.utility import models as M
from agent.base.planner.utility import weights as W

TERMS = ("kill", "hit", "bleed", "chase", "goal", "regress")
TERM_WEIGHT = {"kill": "K", "hit": "H", "bleed": "B", "chase": "C", "goal": "V", "regress": "G"}
TERM_SIGN = {t: 1.0 for t in TERMS}   # the mutation pass's seam: each term's sign (0 drops it); never changed live

MELEE_D = 1.0             # tiles: the distance a fight's press stands at (#4596: E21's swings from 1.0575 to 1.385
                          # tiles all lowered their target, #4631: F13's 1.147 to 1.444), the hazard read there
CHASE_MIN = 0.5           # tiles a second: the least closing speed an aware standing zombie is read to arrive at (a
                          # first guess; F15's chaser closed at about 1.6, the spec's § 1)
STANCE_PACE = 1.0         # tiles a second: the stance's walk toward an unaware or fallen target (a first guess)
RUN_PACE = 3.0            # tiles a second: a retreat's run (`policies.AHEAD_R`'s 3 s leg at about 3 tiles a second)
T_MAX = 20.0              # seconds: a fight's horizon (the ladder's STAND_MAX_S and FIGHT_MAX_S, 20)
SWING_S = 1.25            # seconds a swing or a floor press takes: the bat's clip at its slowest, 1.0 s / CombatSpeed
                          # 0.8 [#4668]
SHOVE_CYCLE_S = 2.0       # seconds one shove, its knock and a stomp take (a first guess)
P_KNOCK = 0.35            # a shove's knock-down chance: `calculateCritChance`'s 35 at no moodle [#4373]; its
                          # Strength term (+2 per level) unread, so the least of it
KNOCK_PER_LEVEL = 0.05    # ... less 5 per endurance level [#4373]
STOMPS_PER_DOWN = 2       # finish presses a knocked-down zombie takes before it rises (a first guess)
FALLEN_FACTOR = 0.25      # the share of a standing zombie's hazard a fallen one (a crawler bites from 1.4, #4687)
                          # carries, read no nearer than MELEE_D (the hazard is fitted on standing zombies only; a
                          # first guess)
UNAWARE_FACTOR = 0.25     # the share of its hazard an unaware zombie carries (a first guess: it must notice first)
SNEAK_FACTOR = 0.5        # a sneak step's volume over a walk's, 0.25 / 0.5 [#4661]: the unaware zombies' share under
                          # the sneak
NOTICE_HITS = 0.25        # hits an unaware zombie within SNEAK_R costs a walk past it upright (a first guess: one in
                          # four turns and lands one), SNEAK_FACTOR of it sneaking
BLEED_HORIZON_M = 2.0     # wall minutes an undressed bleed would run (the proposal's M; a first guess: the doctrine
                          # wants it dressed within the minute, `tools/trial_score.py` DRESS_MIN)
DRESS_HELD_S = 4.0        # seconds a dress with a held dressing takes: the stop and the bandage (a first guess)
DRESS_TEAR_S = 12.0       # ... tearing a garment first: the unwear, the rip and the bandage (a first guess)
ROUTE_S = 5.0             # seconds of a travel, a sneak, a loot, the needs or the rest scored (their horizon)
GOAL_VALUE = 1.0          # the goal's progress over ROUTE_S, in V
NEED_VALUE = 2.0          # the needs' (a drink, a meal, the load, the night, the care's quiet steps), over the goal's:
                          # the ladder's order, need before goal
REST_VALUE = 0.5          # the rest's per endurance moodle level (the spec's § 4 item 2b: rest once clear)
REGRESS_TILES = 10.0      # tiles run off per unit of `regress`
DRAG_DOWN_N = PDRAG_N     # aware standing zombies at once that drag the character down [#4290, #4291]
DRAG_HITS = 3.0           # hits a drag-down is priced at, per zombie past the second (a first guess: a death's price
                          # damped by the chance the three attack together)

SELECT_S = 1.0            # seconds between selections (the proposal's "about once a second")
NEAR_R = 1.5              # tiles: a standing zombie not the act's target entering this is an interrupt (the proposal)
DELTA0 = 0.3              # hits: the margin's floor (a first guess for the trials)
DELTA_FRAC = 0.2          # ... and its share of the held act's |U| (the proposal's 0.2)
SPAN_S = {"fight": 4.0, "travel": 3.0, "loot": 3.0, "sneak": 3.0, "needs": 3.0, "rest": 3.0,
          "dress": math.inf, "retreat": math.inf}   # the minimum spans (the proposal: a fight 4 s or its target's
                                                    # end, a dress until done, a travel 3 s; a retreat to its filter)
SPAN_LOCKED = ("retreat",)   # the kinds whose span no interrupt lifts
INTERRUPTS = ("hit", "bleeding", "near", "goal")   # the four the frame raises; the act's own end is the fifth
SPENT_LEVEL = 2           # a moodle at this level or more makes the fight the shove and stomp (the spec's § 4 2b)
RETREAT_FLOOR = 0.0       # hits: a retreat scoring at or under this saves nothing (an open-ground leg) and is never
                          # chosen (the doctrine: a retreat goes to a filter that takes the group one at a time)
FALLBACK_FLOOR = 0.0      # hits: a fallback (the held act's executor ended on its first step) takes only an act
                          # scoring above this; else nothing is sent this tick


def spent(sit):
    """The spec's § 4 item 2b: the arms' pain over 10 [#4370], or the endurance or tired moodle at level 2."""
    pain = sit.arm_pain
    return ((isinstance(pain, (int, float)) and pain > M.PAIN_FREE) or M.endurance_level(sit.endurance) >= SPENT_LEVEL
            or M.tired_level(sit.fatigue) >= SPENT_LEVEL)


def arrival(z):
    """Seconds an aware standing zombie takes to stand at MELEE_D."""
    return max(z.d - MELEE_D, 0.0) / max(z.closing, CHASE_MIN)


def drag(zs, span, filtered=False):
    """The drag-down's price over `span` seconds standing (#4290: three zombies attacking from under 0.9 tiles zero the
    defences and the hit is `EndDeath`, #4291's kill): DRAG_HITS for each aware standing zombie past DRAG_DOWN_N - 1
    that arrives within the span (`arrival`); none at a filter or on the move (`filtered`: they come one at a time,
    or follow strung out). Structure, not a fit: the rings hold no drag-down to fit one on."""
    if filtered:
        return 0.0
    n = sum(1 for z in zs if z.standing and z.aware and arrival(z) <= span)
    return DRAG_HITS * max(n - (DRAG_DOWN_N - 1), 0)


def exposure(zs, span, models, skip=None, filtered=False):
    """Expected hits over `span` seconds from the zombies `zs` (the module docstring's `hit`), `skip` the id left out;
    `filtered`, at a filter: an aware standing one stays at its distance (they come one at a time)."""
    out = 0.0
    for z in zs:
        if z.id == skip:
            continue
        if z.fallen:
            out += FALLEN_FACTOR * models.hazard(max(z.d, MELEE_D)) * span
        elif not z.aware:
            out += UNAWARE_FACTOR * models.hazard(z.d) * span
        elif filtered:
            out += models.hazard(z.d) * span
        else:
            a = min(arrival(z), span)
            out += models.hazard(z.d) * a + models.hazard(MELEE_D) * (span - a)
    return out


def press(sit, z, models):
    """(the kill chance of one press, its seconds) at zombie `z` (the module docstring's `kill`)."""
    if z.fallen:
        return models.p_press(True, sit.arm_pain, sit.endurance, sit.fatigue, z.health), SWING_S
    if spent(sit) or not sit.armed:
        fin = models.p_press(True, sit.arm_pain, sit.endurance, sit.fatigue, z.health)
        knock = max(P_KNOCK - KNOCK_PER_LEVEL * M.endurance_level(sit.endurance), 0.0)
        return knock * (1.0 - (1.0 - fin) ** STOMPS_PER_DOWN), SHOVE_CYCLE_S
    return models.p_press(False, sit.arm_pain, sit.endurance, sit.fatigue, z.health), SWING_S


def fight_plan(sit, z, models):
    """(P_kill, span seconds, approach seconds) of a fight at `z`."""
    p, step = press(sit, z, models)
    if z.d <= MELEE_D:
        t_app = 0.0
    elif z.standing and z.aware:
        t_app = arrival(z)
    else:
        t_app = (z.d - MELEE_D) / STANCE_PACE
    left = max(T_MAX - t_app, 0.0)
    p_kill = 1.0 - (1.0 - p) ** (left / step) if p > 0.0 else 0.0
    t_kill = step / p if p > 0.0 else math.inf
    return p_kill, t_app + min(t_kill, left), t_app


def terms(c, sit, ctx, models=M.FITTED):
    """{term: raw} of candidate `c` (the module docstring)."""
    n_bleed = len(sit.bleeding)
    zs = sit.zeds
    filtered = ctx.at_filter is not None
    t = dict.fromkeys(TERMS, 0.0)
    if c.kind == "fight":
        z = c.zed
        p_kill, span, t_app = fight_plan(sit, z, models)
        own = models.hazard(MELEE_D) * (span - t_app) + models.hazard(z.d) * t_app
        if z.fallen:
            own *= FALLEN_FACTOR
        t["kill"] = p_kill
        t["hit"] = -(own + exposure(zs, span, models, skip=z.id, filtered=filtered) + drag(zs, span, filtered))
        t["bleed"] = -n_bleed * span / 60.0
        t["chase"] = 1.0 if z.standing and z.aware and sit.armed else 0.0
    elif c.kind == "dress":
        span = DRESS_HELD_S if c.item is not None and c.item[0] == "bandage" else DRESS_TEAR_S
        if c.ride:
            t["hit"] = -exposure(zs, span, models, filtered=True)   # moving on: the chasers keep their distance
        else:
            t["hit"] = -(exposure(zs, span, models, filtered=filtered) + drag(zs, span, filtered))
        t["bleed"] = BLEED_HORIZON_M - (n_bleed - 1) * span / 60.0
    elif c.kind == "retreat":
        f = c.filter
        t_f = f.d / RUN_PACE
        group = sit.aware_standing(DANGER_R)
        kill_s = sum(min(fight_plan(sit, z, models)[1], T_MAX) for z in group)
        here = exposure(group, kill_s, models) + drag(group, kill_s)
        at_f = models.hazard(MELEE_D) * kill_s
        route = exposure(zs, t_f, models, filtered=True)
        t["hit"] = here - at_f - route
        t["bleed"] = -n_bleed * t_f / 60.0
        t["regress"] = -f.d / REGRESS_TILES
    elif c.kind in ("travel", "loot", "sneak"):
        near_unaware = [z for z in zs if z.d <= SNEAK_R and not z.aware and z.standing]
        share = SNEAK_FACTOR if c.kind == "sneak" else 1.0
        moving = [z for z in zs if z.aware or z.fallen]
        t["hit"] = -(exposure(moving, ROUTE_S, models, filtered=True)
                     + share * (UNAWARE_FACTOR * sum(models.hazard(z.d) for z in near_unaware) * ROUTE_S
                                + NOTICE_HITS * len(near_unaware)))
        t["bleed"] = -n_bleed * ROUTE_S / 60.0
        t["goal"] = GOAL_VALUE
    elif c.kind == "needs":
        t["hit"] = -(exposure(zs, ROUTE_S, models, filtered=filtered) + drag(zs, ROUTE_S, filtered))
        t["bleed"] = -n_bleed * ROUTE_S / 60.0
        t["goal"] = NEED_VALUE
    elif c.kind == "rest":
        t["bleed"] = -n_bleed * ROUTE_S / 60.0
        t["goal"] = REST_VALUE * M.endurance_level(sit.endurance)
    return t


def weighted(raw, weights=None):
    """{term: W[term] x raw x TERM_SIGN[term]} and their sum."""
    w = W.values() if weights is None else weights
    out = {k: TERM_SIGN[k] * w[TERM_WEIGHT[k]] * v for k, v in raw.items()}
    return sum(out.values()), out


def score_all(cands, sit, ctx, models=M.FITTED, weights=None):
    """{key: (total, {term: weighted})} of every candidate, the vetoed included."""
    out = {}
    for c in cands:
        out[c.key] = weighted(terms(c, sit, ctx, models), weights)
    return out


def _rank(c, scores):
    return (-scores[c.key][0], A.KINDS.index(c.kind), c.key)


def delta(u):
    return DELTA0 + DELTA_FRAC * abs(u)


def eligible(c, total, floor=None):
    """Candidate `c` may be chosen at score `total` (`Selector.decide`)."""
    if c.kind == "retreat" and total <= RETREAT_FLOOR:
        return False
    return floor is None or total > floor


class Selector:
    """The commitment (the module docstring); `held` the held candidate's key and kind."""

    def __init__(self):
        self.key = None
        self.kind = None
        self.since = None         # wall the held act was taken
        self.last = None          # wall of the last selection

    def drop(self):
        self.key = self.kind = self.since = None

    def decide(self, cands, scores, now, interrupts=(), ended=False, floor=None):
        """(the chosen candidate or None, its line fields {runner_up, margin, held_by, select, interrupts}). Eligible:
        the candidates not vetoed, but a retreat that saves no hits (its total at or under RETREAT_FLOOR: an open
        leg), and with `floor` (a fallback's) none at or under it."""
        ok = sorted((c for c in cands if c.veto is None and (eligible(c, scores[c.key][0], floor) or (
            c.key == self.key and floor is None))), key=lambda c: _rank(c, scores))   # the held act stays eligible
        info = {"runner_up": None, "margin": None, "held_by": None, "select": None,
                "interrupts": list(interrupts)}
        if not ok:
            self.drop()
            self.last = now
            info["select"] = "none"
            return None, info
        best = ok[0]
        held = next((c for c in ok if c.key == self.key), None)
        due = self.last is None or now - self.last >= SELECT_S or bool(interrupts)
        if held is None or ended:
            info["select"] = "new" if self.key is None else ("end" if ended else "gone")
            chosen = best
        elif not due:
            info["held_by"], chosen = "cadence", held
        elif (now - self.since < SPAN_S.get(held.kind, 0.0)
              and (not interrupts or held.kind in SPAN_LOCKED)):
            info["held_by"], chosen = "span", held
        elif best.key != held.key and scores[best.key][0] > scores[held.key][0] + delta(scores[held.key][0]):
            info["select"], chosen = "beat", best
        else:
            info["held_by"], chosen = "margin", held
        if due or chosen is not held:
            self.last = now
        if chosen is not held:
            self.key, self.kind, self.since = chosen.key, chosen.kind, now
        rival = next((c for c in ok if c.key != chosen.key), None)
        if rival is not None:
            info["runner_up"] = rival.key
            info["margin"] = scores[chosen.key][0] - scores[rival.key][0]
        return chosen, info
