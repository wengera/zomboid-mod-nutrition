"""The outcome models of the situation utility (Plan 31 Task 11 U; the proposal's § 5 stage 1): the hit hazard
`hazard(d)` and the kill chance per press, fitted on the committed rings' recorded acts by `tools/utility_fit.py`,
with the arm-pain divisor and the moodle multipliers as fixed structure. They are not the policy: they price what an
act costs and earns, and the selector (`select.py`) ranks the acts by them.

With tens of hits the models are bounded, not learned: 51 hit-reaction onsets over ten rings (E19 to E23 and F11 to
F15), nearly all at 0.5 to 0.9 tiles from one standing zombie, so the hazard is a two-parameter curve in the nearest
standing zombie's distance and nothing else (the `state` field PZA/1.9 carries is fitted on F15 alone, n = 6, and reported, never used here).
Every fitted number below is the artifact's (`data/fits/utility-weights.json`, `models`), pinned there by
`test_utility_fit.py`; `tools/utility_fit.py --check` reproduces it from the rings.

- The hazard (`hazard`): P(a hit-reaction onset within HIT_WINDOW_S | the nearest standing zombie at d) is the
  logistic sigma(b0 + b1 d), fitted by maximum likelihood over the frame samples with a standing zombie listed; the
  rate per second is -ln(1 - p) / HIT_WINDOW_S. A situation's rate is the sum over the zombies of each one's own
  (`exposure` in `select.py`): additive structure, an assumption, not a reading.
- The kill chance per press (`Models.p_press`): kills over presses of each kind, the standing swing's with its
  presses weighted by the structure below (a ratio estimator: the kills the data shows over the kill units the
  presses carried), the finish's (a stomp or a floor swing at a fallen zombie) weighted by the moodles only (#4374:
  the stomp's damage is set after the arm-pain divider). The swing's chance at pain p and moodles m is
  min(1, P_SWING x m / divisor(p)); the zombie's own health scales it by HEALTH_REF / health (a weaker zombie dies in
  fewer presses; a first guess).
- The structure: `pain_divisor` [#4370] (a swing that is not a stomp divides its damage by clamp(s / 10, 1, 30), s
  the six arm parts' summed pain, over 10), `moodle_mult` [#4371] (x 0.5, 0.2, 0.1, 0.05 at endurance moodle levels
  1 to 4 and again at tired levels 1 to 4), the levels off the stats by #3926 (endurance) and #2279 (fatigue).
"""
import dataclasses
import math

HIT_WINDOW_S = 1.0        # seconds: the hazard's label, a hit-reaction onset within this of the sample (the proposal's
                          # "a hit reaction beginning within the next second")
ENDURANCE_LEVELS = (0.75, 0.5, 0.25, 0.10)   # the ENDURANCE moodle's levels 1-4 below these [#3926]
TIRED_LEVELS = (0.6, 0.7, 0.8, 0.9)          # the TIRED moodle's levels 1-4 above these [#2279]
MOODLE_MULT = (1.0, 0.5, 0.2, 0.1, 0.05)     # a swing's damage at moodle levels 0-4, each moodle [#4371]
PAIN_FREE = 10.0          # the arms' summed pain over which a swing's damage is divided [#4370]
PAIN_CAP = 30.0           # ... by at most this [#4370]
HEALTH_REF = 2.0          # a zombie's health the press chances are read at: the rings' zombies read 1.4 to 2.3 at
                          # their first listing (F15 2.338, E23 1.692); a first guess for the trials


def endurance_level(endurance):
    """The ENDURANCE moodle's level 0-4 [#3926]: 0 above 0.75, 1 above 0.5, 2 above 0.25, 3 above 0.10, else 4; 0
    for an unread stat."""
    if not _num(endurance):
        return 0
    return sum(1 for t in ENDURANCE_LEVELS if endurance <= t)


def tired_level(fatigue):
    """The TIRED moodle's level 0-4 [#2279]: one per threshold the fatigue is strictly above; 0 for an unread stat."""
    if not _num(fatigue):
        return 0
    return sum(1 for t in TIRED_LEVELS if fatigue > t)


def moodle_mult(endurance, fatigue):
    """The damage multiplier of the two moodles [#4371]."""
    return MOODLE_MULT[endurance_level(endurance)] * MOODLE_MULT[tired_level(fatigue)]


def pain_divisor(pain):
    """A swing's damage divisor at the arms' summed pain [#4370]: clamp(pain / 10, 1, 30) over 10, else 1."""
    if not _num(pain) or pain <= PAIN_FREE:
        return 1.0
    return min(max(pain / PAIN_FREE, 1.0), PAIN_CAP)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


@dataclasses.dataclass(frozen=True)
class Models:
    """The fitted numbers (the artifact's `models`), one place: the selector reads `FITTED`, the fit tool builds its
    own from the rings it reads."""
    hit_b0: float          # the hazard's intercept
    hit_b1: float          # ... and its slope per tile
    p_swing: float         # kill chance per standing swing at no pain and no moodle, at HEALTH_REF
    p_finish: float        # kill chance per finish press (stomp or floor swing) at a fallen zombie, no moodle

    def hazard(self, d):
        """Hits a second from one standing zombie at `d` tiles (the module docstring)."""
        if not _num(d):
            return 0.0
        p = sigmoid(self.hit_b0 + self.hit_b1 * max(d, 0.0))
        return -math.log(max(1.0 - p, 1e-12)) / HIT_WINDOW_S

    def p_press(self, fallen, pain, endurance, fatigue, health=None):
        """The kill chance of one press at a zombie: the finish's at a fallen one (the moodles only, #4374), else the
        swing's (divided by the arms' pain, #4370); scaled by HEALTH_REF / its health when read; at most 1."""
        base = self.p_finish if fallen else self.p_swing / pain_divisor(pain)
        p = base * moodle_mult(endurance, fatigue)
        if _num(health) and health > 0.0:
            p *= HEALTH_REF / health
        return min(max(p, 0.0), 1.0)


# The fitted numbers (`tools/utility_fit.py`, `data/fits/utility-weights.json` "models"; pinned by
# `test_utility_fit.py::test_the_models_are_the_artifact_s`). n and the probes are the artifact's and the README's.
FITTED = Models(hit_b0=-0.056866743, hit_b1=-3.582494441, p_swing=0.211542386, p_finish=0.183206107)
