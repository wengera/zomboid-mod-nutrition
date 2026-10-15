"""The deficit-drive oracle registry (Plan 11g Task 7): one table of every server-path oracle the deficit drive's fit
(tools/fit_deficit_drive.py) scores and test_replay_live_energy.py's tests read, so a band lives in one place.

The deficit drive (K.deficit: the balance span, the exercise lag and its bypass ramp, and the hunger target; the
deficit floor until Plan 11g Task 7 fix 1) was fitted in Plan 11f Task 2c against Karl 2021 as reported, the well-fed arm (BAL) included (ruling 2c-2).
Since Plan 11g Task 6c the meal pool M and the stomach's fill to its hard capacity carry BAL inside its band (-54.5 %),
so this refit scores the deficit studies alone and holds BAL as a constraint.

An oracle is a name, the reading group it is picked from, its band (`lo`, `hi`; one bound None for a one-sided check),
its role and its row:
    "scored"      a deficit study; its margin enters the fit's objective;
    "constraint"  a band the fit must keep (Karl's BAL arm, now satiety's; the steady eater; six meals against three;
                  S1255's ceiling); outside it the candidate is infeasible;
    "fixed"       a deficit study no fitted constant moves (Whybrow and E-MECHANIC read the exercise lag L, which the
                  span and the bypass never touch); read and asserted, its margin reported.
S1254 (Plan 13 Task 10c) is scored on the fat term's gain K.deficit.FAT_GAIN: the reference body held at three fat
depletions inside the ramp's linear part, eating at the request, its intake rise per kg of FAT lost against 125 kcal/d
within 1.5x, read as ln(slope / 125) so the band's centre is 125. S1254 (Polidori 2016) is per kg of body WEIGHT
(~100; k_P 95 kcal/d per kg in Polidori's own model, S2208), and that model splits a weight change by the Forbes
relation (S2206), whose fat share at the trial's fat mass is about 0.76 (S2200's SGLT2 pooling and S2203's
canagliflozin DXA agree; S2199's 0.63 is the low end and gives 150, inside the band): 95 / 0.76 = 125 kcal/d per kg of
fat (Plan 13 Task 10c fix 2; the controller's ruling on review finding 2). Three stability checks sit
beside it as constraints (CLAUDE.md section 6): the two pair slopes within 2x of each other (a clamped or degenerate
read fails), every pair slope at least 30 kcal/d per kg (a flat read fails) and the intake below FAT_DEP_LO within 25
kcal/d of no loss (the soft threshold). A fit of FAT_GAIN alone (fit_deficit_drive's fat mode) ranks by S1254 and
holds every other oracle as a constraint, read once: no other study reaches a depletion of FAT_DEP_LO.
The margin of a reading is its distance inside the band over the band's half-width (1 at the centre, 0 at an edge,
negative outside); a one-sided band's margin is its distance inside over its `scale`. King 2011's band is the
exercise arm's distance from control under min(3.3 mm, a quarter of the restriction's rise), with the rise above 0.02.

Twin K's alternatives (Plan 11f ruling 2c-1, the worst case the fit ranks by): the loaded walks billed whole at
ClimbRope, at Running10kmh or as loaded Walking5kmh (33.5 kg of 50), and the day without the task battery; the
as-built twin is test_replay_live_energy.py's. Karl DEF is scored at the worst of the five; BAL is constrained on the
as-built twin and reported over the five.

The readings are test_replay_live_energy.py's own functions, run on whatever host is passed (the kernel tests' `host`,
or the fit's patched one); the server-path replays build their own hosts (tools/replay_live.py), which the fit patches.
"""
from . import test_replay_live_energy as E
from . import test_satiety_activity as A
from . import test_satiety_meal_studies as M

import math

import replay_live as RL  # noqa: E402  (test_replay_live_energy puts tools/ on the path)

KARL_ALTS = ("asbuilt", "climb", "run10", "loadwalk", "nobattery")
KARL_BAL_BAND = (-64.0, -46.0)        # S1325 with S1892 (open: +/- 9 points about -55 %, a labelled DESIGN CHOICE)
KARL_DEF_BAND = (26.0 / 1.5, 26.0 * 1.5)   # S1325: +26 % within 1.5x (karl_pass), 17.3-39 inside the study's CI


# --- twin K's alternatives -----------------------------------------------------------------------------------------

def _walk_spans(day0, am_dur):
    """The two loaded walks of a SUSOPS day as (start, minutes)."""
    return [(day0 + E.KARL_AM[0], am_dur), (day0 + E.KARL_EVE[0], E.KARL_EVE[1])]


def karl_alt_events(arm, alt):
    """twin K's events (E.karl_events) with the loaded walks billed as `alt` ("climb", "run10", "loadwalk") or the task
    battery removed ("nobattery"); "asbuilt" is E.karl_events unchanged. Returns (events, days, am_dur, player)."""
    ev, days, am_dur = E.karl_events(arm)
    player = {"weight": E.KARL_KG, "female": False}
    if alt == "asbuilt" or arm == "REST":
        return ev, days, am_dur, player
    spans = [s for d in range(E.KARL_WARM, days) for s in _walk_spans(d * 1440, am_dur)]
    battery = max(E.KARL_BATTERY[0], E.KARL_AM[0] + am_dur + 4)
    batt = [(d * 1440 + battery, E.KARL_BATTERY[1]) for d in range(E.KARL_WARM, days)]
    out = []
    for e in ev:
        m = e["minute"]
        if e["kind"] == "activity":
            if alt != "nobattery" and any(st <= m <= st + dur for st, dur in spans):
                continue
            if alt == "nobattery" and any(st <= m <= st + dur for st, dur in batt):
                continue
        out.append(e)
    if alt != "nobattery":
        cls = {"climb": "ClimbRope", "run10": "Running10kmh", "loadwalk": "Walking5kmh"}[alt]
        for st, dur in spans:
            out.append({"minute": st, "kind": "activity", "rate": ALT_RATE[cls], "moving": True})
            out.append({"minute": st + dur, "kind": "activity", "rate": E.IDLE, "moving": False})
        if alt == "loadwalk":
            player.update({"inv": 33.5, "maxW": 50.0})
    out.sort(key=lambda e: e["minute"])
    return out, days, am_dur, player


ALT_RATE = {"ClimbRope": 8.0, "Running10kmh": 6.9, "Walking5kmh": 3.1}   # the engine rates (K.energy.CLASS_MET)


def karl_alt_mean(arm, alt):
    """The mean HUNGER at the VAS rows of the arm's study days under twin K's alternative `alt`."""
    ev, days, am_dur, player = karl_alt_events(arm, alt)
    rows, _ = RL.replay_arm(ev, minutes=days * 1440, backend="server", start_age=0.0, player=player, rng="half")
    reads = [rows[m]["HUNGER"] for d in range(E.KARL_WARM, days) for m in E.karl_vas(d * 1440, am_dur)]
    return sum(reads) / len(reads)


def karl(host, alts=KARL_ALTS):
    """{alt: {"bal": %, "dfc": %}} against the as-built REST day (Table 2's quantity)."""
    rest = karl_alt_mean("REST", "asbuilt")
    return {a: {"bal": 100 * (karl_alt_mean("BAL", a) / rest - 1), "dfc": 100 * (karl_alt_mean("DEF", a) / rest - 1)}
            for a in alts}


# --- the readings: each group run once per host --------------------------------------------------------------------

def _fast(h):
    f = E.fast_server()
    return {"r2": f["r2"], "r3": f["r3"]}


def _steady(h):
    ratios, es = E.steady_server()
    return {"ratios": ratios, "es": [min(es), max(es)]}


def _king(h):
    bout, k = E.king_steady_server(h)
    rise = k["restriction"] - k["control"]
    return {"bout": bout, "rise": rise, "risemm": rise * A.MM_PER_HUNGER,
            "dmm": abs(k["exercise"] - k["control"]) * A.MM_PER_HUNGER}


def _s1255(h):
    e, mm = E.deficit_server(h)
    return {"es": e, "mm": mm}


def _whybrow(h):
    return [list(E.whybrow_server(h, mj)) for mj in (3.5, 1.75)]


def _emech(h):
    return [E.e_mechanic_server(h, cls, weeks=(24,))[0] for cls in ("MediumWork", "UsingTools")]


def _s1254(h):
    return E.fat_loss_server(h)


GROUPS = {
    "fast": _fast,
    "karl": karl,
    "king": _king,
    "steady": _steady,
    "six": lambda h: E.six_live_sum(6, 150) / E.six_live_sum(3, 300),
    "s1255": _s1255,
    "whybrow": _whybrow,
    "emech": _emech,
    "s1254": _s1254,
}
FIXED_GROUPS = ("whybrow", "emech")     # no fitted constant moves them: the fit reads them once, at its start point
FAT_GROUPS = ("s1254",)                 # the only group K.deficit.FAT_GAIN moves (no other reaches FAT_DEP_LO)
FAT_SCORED = ("s1254",)                 # what a fit of FAT_GAIN alone ranks by
S1254_KCAL_PER_KG_WEIGHT = 95.0         # S1254 (Polidori 2016, ~100) as k_P in its own model (S2208): kcal/d of intake per kg of WEIGHT lost
S1254_FAT_SHARE = 0.76                  # the fat share of that weight: the Forbes split Polidori's model assumes (S2206; S2200, S2203 agree; S2199 0.63)
S1254_KCAL_PER_KG = S1254_KCAL_PER_KG_WEIGHT / S1254_FAT_SHARE   # 125 kcal/d per kg of FAT lost: the oracle's unit
S1254_TOL = 1.5                         # within 1.5x (the brief's band; a labelled DESIGN CHOICE)


# --- the oracles -----------------------------------------------------------------------------------------------------

class Oracle:
    def __init__(self, name, group, pick, lo=None, hi=None, role="scored", row="", tol="", scale=None):
        self.name, self.group, self.pick, self.lo, self.hi = name, group, pick, lo, hi
        self.role, self.row, self.tol = role, row, tol
        assert lo is not None or hi is not None, name
        if scale is None:
            scale = (hi - lo) / 2.0 if lo is not None and hi is not None else None
        assert scale is not None and scale > 0, (name, scale)
        self.scale = scale

    def margin(self, value):
        """The distance inside the band over the scale: >= 0 inside, < 0 outside; -inf for a missing reading."""
        if value is None or value != value:
            return -float("inf")
        m = float("inf")
        if self.lo is not None:
            m = min(m, value - self.lo)
        if self.hi is not None:
            m = min(m, self.hi - value)
        return m / self.scale


def _king_margin_value(r):
    """King 2011's reading as a margin-ready number: the exercise arm's distance less its bound min(3.3 mm, a quarter
    of the rise), so the band is (-inf, 0] on it; a rise at or under 0.02 reads +inf (outside)."""
    k = r["king"]
    if not k["rise"] > 0.02:
        return float("inf")
    return k["dmm"] - min(3.3, 0.25 * k["risemm"])


def _log_ratio(slope):
    """ln(slope / S1254_KCAL_PER_KG), the slope per kg of fat lost; None for a slope that is not positive (outside any band)."""
    if slope is None or not slope > 0:
        return None
    return math.log(slope / S1254_KCAL_PER_KG)


def _pair_ratio(r):
    """The smaller pair slope over the larger (1 linear, toward 0 bent or clamped), None when neither rises."""
    p = r["s1254"]["pairs"]
    if not max(p) > 0:
        return None
    return min(p) / max(p)


def _karl_worst_dfc(r):
    """The alternative whose DEF reading sits nearest an edge of its band (the worst case)."""
    return min((x["dfc"] for x in r["karl"].values()), key=lambda v: _DEF.margin(v))


_DEF = Oracle("karl_def", "karl", _karl_worst_dfc, lo=KARL_DEF_BAND[0], hi=KARL_DEF_BAND[1], row="S1325",
              tol="+26 % within 1.5x (17.3-39), the worst of twin K's five")

ORACLES = [
    # S1613 (Johnstone 2002: the day after a 36 h fast 1.20) and S1614 (Clayton 2016: day 3 1.0), each within 1.1x
    # (ruling 11c-30)
    Oracle("fast_r2", "fast", lambda r: r["fast"]["r2"], lo=1.20 / M.TOL, hi=1.20 * M.TOL, row="S1613", tol="1.1x"),
    Oracle("fast_r3", "fast", lambda r: r["fast"]["r3"], lo=1.0 / M.TOL, hi=1.0 * M.TOL, row="S1614", tol="1.1x"),
    _DEF,
    # S1312 (King 2011 at steady state): the exercise arm within min(3.3 mm, a quarter of the restriction's rise) of
    # control (Plan 11c Task 4b's band); the scale 3.3 mm
    Oracle("king", "king", _king_margin_value, hi=0.0, scale=3.3, row="S1312",
           tol="distance <= min(3.3 mm, rise / 4), rise > 0.02"),
    # constraints: Karl's BAL arm (now satiety's, Plan 11g Task 6c), the steady eater, six meals against three, S1255
    Oracle("karl_bal", "karl", lambda r: r["karl"]["asbuilt"]["bal"], lo=KARL_BAL_BAND[0], hi=KARL_BAL_BAND[1],
           role="constraint", row="S1325, S1892", tol="-64 to -46 % (as built)"),
    Oracle("steady", "steady", lambda r: max(abs(x - 1) for x in r["steady"]["ratios"] + r["steady"]["es"]),
           hi=M.STEADY_TOL, scale=M.STEADY_TOL, role="constraint", row="", tol="every day and hour within 1 +/- 0.03"),
    Oracle("six", "six", lambda r: r["six"], lo=0.9, hi=1.3, role="constraint", row="S1608, S1607", tol="0.9-1.3"),
    Oracle("s1255", "s1255", lambda r: r["s1255"]["mm"], hi=10.0, scale=10.0, role="constraint", row="S1255",
           tol="< 10 mm at a 25 % deficit"),
    # the lag studies: fixed under the fit (no fitted constant moves L)
    Oracle("whybrow_35", "whybrow", lambda r: r["whybrow"][0][1], lo=0.30 / A.TOL, hi=0.30 * A.TOL, role="fixed",
           row="S1318", tol="0.30 within 1.5x, the 3.5 MJ arm"),
    Oracle("whybrow_175", "whybrow", lambda r: r["whybrow"][1][1], lo=0.30 / A.TOL, hi=0.30 * A.TOL, role="fixed",
           row="S1318", tol="0.30 within 1.5x, the 1.75 MJ arm"),
    Oracle("whybrow_day1", "whybrow", lambda r: max(r["whybrow"][0][2], r["whybrow"][1][2]), hi=0.05, scale=0.05,
           role="fixed", row="S1318", tol="< 0.05 the same day, both arms"),
    Oracle("emech_high", "emech", lambda r: r["emech"][0], lo=0.53, hi=0.89, role="fixed", row="S1320, S1664",
           tol="0.53-0.89 at 24 weeks, the high dose"),
    Oracle("emech_low", "emech", lambda r: r["emech"][1], lo=0.53, hi=0.89, role="fixed", row="S1320, S1664",
           tol="0.53-0.89 at 24 weeks, the low dose"),
    # S1254 (Plan 13 Task 10c; fix 2): the fat term's intake rise per kg of fat lost, S1254 converted (see the header),
    # and its stability checks
    Oracle("s1254", "s1254", lambda r: _log_ratio(r["s1254"]["slope"]), lo=-math.log(S1254_TOL),
           hi=math.log(S1254_TOL), row="S1254, S2208, S2206",
           tol="125 kcal/d per kg of fat lost (S1254 as k_P 95 per kg of weight, S2208, / the Forbes fat share 0.76) within 1.5x, as ln(slope / 125)"),
    Oracle("s1254_linear", "s1254", _pair_ratio, lo=0.5, scale=0.5, role="constraint", row="",
           tol="the two pair slopes within 2x (a clamped or degenerate read fails)"),
    Oracle("s1254_flat", "s1254", lambda r: min(r["s1254"]["pairs"]), lo=30.0, scale=30.0, role="constraint", row="",
           tol="every pair slope >= 30 kcal/d per kg of fat (a flat read fails)"),
    Oracle("s1254_low", "s1254", lambda r: abs(r["s1254"]["low"] - r["s1254"]["base"]), hi=25.0, scale=25.0,
           role="constraint", row="S1255", tol="below FAT_DEP_LO within 25 kcal/d of no loss (the soft threshold)"),
]

assert len({o.name for o in ORACLES}) == len(ORACLES)
BY_NAME = {o.name: o for o in ORACLES}


def margins(readings):
    """{name: margin} for every oracle on `readings` ({group: reading})."""
    out = {}
    for o in ORACLES:
        try:
            out[o.name] = o.margin(o.pick(readings))
        except Exception:
            out[o.name] = -float("inf")
    return out


def objective(readings, scored=None):
    """(feasible, the smallest scored margin, the constraints' total shortfall): a candidate is feasible when every
    oracle outside the ranked ones holds; the fit maximises the smallest ranked margin among the feasible. The ranked
    ones are the scored oracles, or `scored` (FAT_SCORED for a fit of FAT_GAIN alone, every other oracle then held)."""
    m = margins(readings)
    names = list(scored or [o.name for o in ORACLES if o.role == "scored"])
    short = sum(-min(0.0, m[o.name]) for o in ORACLES if o.name not in names)
    return short == 0, min(m[n] for n in names), short
