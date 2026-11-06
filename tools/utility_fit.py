#!/usr/bin/env python3
"""The situation utility's fit (Plan 31 Task 11 U; the proposal's § 5 stages 1 and 2): the outcome models fitted on
the committed rings' recorded acts, and the five weights bounded by a linear program over decision lines labelled by
Angus's directions. A trial tool, never a grade (ruling P31-T): its artifact `data/fits/utility-weights.json` is the
utility's dial source, cited by no row.

    python tools/utility_fit.py [--write] [--check] [--out PATH]

Stdlib and numpy (no package installed in the host Python; scipy's `linprog` would replace `lp_max`). Read-only over
the rings; `--write` writes the compact artifact, `--check` recomputes it and exits 1 on any difference, printing the
first differing key.

STAGE 1, THE MODELS (`fit_models`), on the HIT_SET rings (E19 to E23 and F11 to F15, the proposal's):
- The hazard: one sample per SAMPLE_S of wall time over the frames (every rotation, wall order) that list a standing
  zombie within LISTED_R and read no hit reaction; the label a hit-reaction onset (`me.hitReaction` turning
  non-empty) within `models.HIT_WINDOW_S` after it; the feature the nearest standing zombie's distance. A logistic
  fit by Newton's method (`logistic`, RIDGE on the slope only). The full model adds the nearest one's attack state
  (PZA/1.9's `state` in `features.ATTACK_STATES`) on F15 alone, the one ring that carries it: reported, never used.
- The kill chances: kills over weighted presses (`press_rows`): each done act line of an `attack` (a swing) or a
  `stomp`, and each done `melee` span (its `swings`, its `floors` and `stomps`), weighted at its frame (the frame at or
  before its wall) by `models.moodle_mult` and, for a swing, over `models.pain_divisor`; a kill (`targetDead`, the
  melee's `kill`) counts to the finish when the span pressed a floor swing or a stomp, else to the swing.
- Each model with its n, its events and its +-5 % probes (`probes`: each coefficient times 0.95 and 1.05, the
  mean log-likelihood's change and the rate at MELEE_D, or the kill chance over the horizon).

STAGE 2, THE WEIGHTS (`verdicts`, `fit_lp`), on the VERDICT_SET rings (F2 to F15 and E19 to E23): each ring's
decision lines walked in order with its lines applied by wall time (`replay`'s method), the frame's `Situation` read
over the zombies the newest frame lists, the context off the record's own line (the goal's type and square, the needs
branch when the line answered from one, no mark), the candidates generated and scored by the package itself
(`select.terms`, with stage 1's models). A line one of the RULES rules on is a verdict: its labelled candidate must
beat each other unvetoed candidate the rule names by MARGIN, a linear row a.w + c >= MARGIN over w = (K, B, C, G, V)
with H = 1 (a, the weights' terms' difference; c, the hit terms'); a labelled retreat also beats RETREAT_FLOOR by
MARGIN (`select.eligible`: a retreat saving no hits is never chosen; the row's other is "floor"). A row whose a is
zero is structural (no weight moves it): it holds or not, reported. The rest:
- `chebyshev`: the point deepest inside the region (the largest ball, the rows normalised), the chosen point; its
  radius under 0 means the region is empty: two directions conflict, reported by rule pairs, never resolved here.
- `intervals`: each weight's least and greatest value over the region inside the box BOX; an end at the box is a
  weight at its bound, reported.
- `slacks`: each row's slack at the chosen point, rows grouped by (rule, labelled kind, other kind): their n, least
  and greatest slack and the least one's line.
- `stability`: each weight times 0.95 and 1.05 at the chosen point, the labelled lines whose margin (the labelled
  score less the best rival's) moves; a weight that moves none is flat.

THE RULES (Angus's directions; memories `stand-and-fight-dress-first`, `intent-doors-sneak`, `combat-stance-and-wound-
care`, the spec's § 4 item 2b): `one`, armed with one standing zombie within DANGER_R, fewer than GROUP_N aware
standing ones listed, and the one aware or the character not spent (2b: no new fight is sought spent), the fight at
it beats every candidate that is not a fight; `dress_quiet`, a part bleeding and no standing zombie within DANGER_R,
and `dress_far`, a part bleeding and the nearest standing zombie beyond KEEP_R, fewer than GROUP_N aware standing
ones listed, the dress beats every candidate that is not a fight (the memory's "before the goal and before any flee
from a zombie beyond the stance's reach": a zombie, not a group, which the doctrine avoids; the dress against a fight
is left to the scores, no direction ruling on it); `sneak`, the goal walking with a standing zombie within SNEAK_R
and every one unaware, the sneak beats the travel, the loot and every retreat; `group`, GROUP_N or more aware standing zombies
within KEEP_R and a filter generated (the amendments' rule), the nearest filter's retreat beats every fight at a
zombie beyond KEEP_R (one within the stance's reach is struck: the doctrine's first word, left to the scores);
`group_coming`, the same with them within DANGER_R (the doctrine's "a group is avoided before it arrives"); `door`
(structural), a zombie within DOOR_HELD_R behind a portal (`door_held.portal_between`): the candidates hold no wait
(no candidate is a hold), counted.
"""
import argparse
import bisect
import hashlib
import json
import math
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "testing") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "testing"))
from agent.base import gates_e as E  # noqa: E402
from agent.base.planner.door_held import portal_between  # noqa: E402
from agent.base.planner.policies import DANGER_R, DOOR_HELD_R, KEEP_R, LISTED_R  # noqa: E402
from agent.base.planner.utility import acts as A  # noqa: E402
from agent.base.planner.utility import features as F  # noqa: E402
from agent.base.planner.utility import models as M  # noqa: E402
from agent.base.planner.utility import replay as R  # noqa: E402
from agent.base.planner.utility import select as S  # noqa: E402
from agent.base.planner.utility import weights as W  # noqa: E402

ARTIFACTS = os.path.join(REPO, "testing", "artifacts")
OUT = os.path.join(REPO, "data", "fits", "utility-weights.json")
# The rings by the session names the plans use (F<n> the LLM goals sessions, E<n> the chains' days).
RINGS = {"F2": "f_goals_2-20261029-041705", "F3": "f_goals_4-20261030-114742", "F4": "f_goals_5-20261030-180527",
         "F5": "f_goals_6-20261030-192251", "F6": "f_goals_7-20261031-000629", "F7": "f_goals_8-20261102-093241",
         "F8": "f_goals_9-20261102-181937", "F9": "f_goals_10-20261102-231705",
         "F10": "f_goals_11-20261103-075140", "F11": "f_goals_12-20261103-144240",
         "F12": "f_goals_13-20261104-203950", "F13": "f_goals_14-20261105-021722",
         "F14": "f_goals_15-20261105-092752", "F15": "f_goals_16-20261105-164332",
         "E19": "e_day_19-20261103-072904", "E20": "e_day_20-20261103-121340", "E21": "e_day_21-20261104-201749",
         "E22": "e_day_22-20261105-004919", "E23": "e_day_23-20261105-095110"}
HIT_SET = ("E19", "E20", "E21", "E22", "E23", "F11", "F12", "F13", "F14", "F15")   # the proposal's reduced model's
FULL_SET = ("F15",)       # the one ring whose frames carry PZA/1.9's `state`
VERDICT_SET = tuple(RINGS)   # F2 to F15 and E19 to E23 (every ring decodes)
SAMPLE_S = 0.5            # seconds of wall time per hazard sample (the planner's tick)
RIDGE = 1e-3              # the logistic fit's ridge on the slope (a numerical floor, never a prior)
NEWTON_ITERS = 50
MARGIN = 0.1              # hits: a labelled candidate beats each other by at least this (a first guess)
BOX = (0.0, 20.0)         # every weight's bounds in the program (hits; K = 20 is a kill worth twenty hits)
PROBE = (0.95, 1.05)      # the +-5 % probes (CLAUDE.md § 6, fits)
TOL = 1e-9
DIGITS = 9                # the artifact's floats
NAMES = W.NAMES           # ("K", "B", "C", "G", "V")
RULES = ("one", "dress_quiet", "dress_far", "sneak", "group", "group_coming", "door")
GROUP_N = 3               # aware standing zombies that make a group (the doctrine's "three or more aware zombies")


def _r(v, d=DIGITS):
    if isinstance(v, float):
        return round(v, d) + 0.0 if math.isfinite(v) else repr(v)
    if isinstance(v, dict):
        return {k: _r(x, d) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_r(x, d) for x in v]
    return v


def ring_dir(key):
    return os.path.join(ARTIFACTS, RINGS[key])


def ring_files(key):
    d = ring_dir(key)
    return [os.path.join(d, "decision.log")] + E.state_files(d)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_LOADED = {}   # ring -> load()'s answer, kept from stage 1 to stage 2 (each ring decoded once), dropped after use


def load(key, keep=False):
    """(lines in seq order, frames in wall order, decision rows) of ring `key`: every rotation's lines; `keep` holds
    the answer for the next call, which takes it (`_LOADED`)."""
    if key in _LOADED:
        return _LOADED.pop(key) if not keep else _LOADED[key]
    got = _decode(key)
    if keep:
        _LOADED[key] = got
    return got


def _decode(key):
    lines, _ = E.session_lines(ring_dir(key))
    frames = sorted((ln for ln in lines if ln.get("kind") == "frame"), key=lambda f: f["wallMs"])
    with open(os.path.join(ring_dir(key), "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return lines, frames, rows


# ================================================================ the linear program
def lp_max(c, A_ub, b_ub):
    """max c.x subject to A_ub x <= b_ub, x free (bound it with rows), by the simplex method on the dual (min b.y
    subject to A_ub^T y = c, y >= 0; n equality rows, one column a row of A_ub), Bland's rule. Returns (status, x,
    value): "optimal" with the primal x the dual's multipliers, "infeasible" when the dual is unbounded (the primal
    region empty), "unbounded" when the dual is infeasible (a direction the rows leave open)."""
    A = np.asarray(A_ub, dtype=float).T          # n x m: the dual's equality matrix
    b = np.asarray(b_ub, dtype=float)            # the dual's costs
    c = np.asarray(c, dtype=float)
    n, m = A.shape
    sign = np.where(c < 0, -1.0, 1.0)
    T = np.hstack([A * sign[:, None], np.eye(n)])   # artificials last, the rows sign-fixed so the rhs is >= 0
    rhs = c * sign
    basis = list(range(m, m + n))
    x = rhs.copy()

    def run(cost, allowed):
        nonlocal x
        for _ in range(50 * (m + n) + 100):
            B = T[:, basis]
            Binv = np.linalg.inv(B)
            x = Binv @ rhs
            pi = cost[basis] @ Binv
            red = cost - pi @ T
            enter = next((j for j in range(m + n) if allowed[j] and j not in basis and red[j] < -TOL), None)
            if enter is None:
                return "optimal", pi
            d = Binv @ T[:, enter]
            ratios = [(x[i] / d[i], basis[i], i) for i in range(n) if d[i] > TOL]
            if not ratios:
                return "unbounded", pi
            best = min(r[0] for r in ratios)
            leave = min((r for r in ratios if r[0] <= best + TOL), key=lambda r: r[1])[2]
            basis[leave] = enter
        raise RuntimeError("lp_max: no convergence")

    cost1 = np.concatenate([np.zeros(m), np.ones(n)])
    run(cost1, [True] * (m + n))
    if float(cost1[basis] @ x) > 1e-7:
        return "unbounded", None, None   # the dual infeasible: the primal unbounded (never with a box)
    for i in range(n):   # drive the artificials out (the box rows give the system full rank)
        if basis[i] >= m:
            B = T[:, basis]
            row = np.linalg.inv(B)[i] @ T[:, :m]
            j = next((j for j in range(m) if abs(row[j]) > 1e-7 and j not in basis), None)
            if j is not None:
                basis[i] = j
    cost2 = np.concatenate([b, np.zeros(n)])
    status, pi = run(cost2, [True] * m + [False] * n)
    if status == "unbounded":
        return "infeasible", None, None
    primal = pi * sign   # the multipliers of the sign-fixed rows, back to the original rows' signs
    return "optimal", primal, float(c @ primal)


# ================================================================ stage 1: the models
def hit_samples(keys):
    """([(d, att, label, ring)] of the hazard's samples, the hit-reaction onsets in the rings' frames) (the module
    docstring)."""
    out, n_onsets = [], 0
    for key in keys:
        _, frames, _ = load(key, keep=True)
        onsets, prev = [], ""
        for f in frames:
            h = (f.get("me") or {}).get("hitReaction") or ""
            if h and not prev:
                onsets.append(f["wallMs"])
            prev = h
        n_onsets += len(onsets)
        last = None
        for f in frames:
            me = f.get("me") or {}
            if me.get("hitReaction") or not isinstance(me.get("x"), (int, float)):
                continue
            w = f["wallMs"]
            if last is not None and w - last < SAMPLE_S * 1000.0:
                continue
            best = None
            for z in f.get("zombies") or ():
                if z.get("onFloor") is True or not isinstance(z.get("x"), (int, float)):
                    continue
                d = math.hypot(z["x"] - me["x"], z["y"] - me["y"])
                if d <= LISTED_R and (best is None or d < best[0]):
                    best = (d, z.get("state") in F.ATTACK_STATES)
            if best is None:
                continue
            last = w
            i = bisect.bisect_right(onsets, w)
            label = i < len(onsets) and onsets[i] <= w + M.HIT_WINDOW_S * 1000.0
            out.append((best[0], best[1], label, key))
    return out, n_onsets


def logistic(X, y):
    """Maximum-likelihood logistic coefficients of `y` on `X` (a column of ones first), RIDGE on the others."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], RIDGE)
    pen[0] = 0.0
    for _ in range(NEWTON_ITERS):
        p = 1.0 / (1.0 + np.exp(-(X @ beta)))
        g = X.T @ (y - p) - pen * beta
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-12:
            break
    return beta


def mean_ll(X, y, beta):
    z = np.asarray(X, float) @ beta
    y = np.asarray(y, float)
    return float(np.mean(y * z - np.logaddexp(0.0, z)))


def fit_hazard(got, full=False):
    samples, n_onsets = got
    X = [[1.0, d] + ([1.0 if att else 0.0] if full else []) for d, att, _, _ in samples]
    y = [1.0 if lab else 0.0 for _, _, lab, _ in samples]
    beta = logistic(X, y)
    names = ["b0", "b1"] + (["b_attack"] if full else [])
    base_ll = mean_ll(X, y, beta)
    m = M.Models(float(beta[0]), float(beta[1]), 0.0, 0.0)
    probes = {}
    for i, name in enumerate(names):
        row = {}
        for k in PROBE:
            b = beta.copy()
            b[i] *= k
            mm = M.Models(float(b[0]), float(b[1]), 0.0, 0.0)
            row["x%.2f" % k] = {"mean_ll_change": mean_ll(X, y, b) - base_ll,
                                "rate_at_melee_d": mm.hazard(S.MELEE_D)}
        probes[name] = row
    return {"n": len(samples), "positive": int(sum(y)), "onsets": n_onsets, "coef": dict(zip(names, map(float, beta))),
            "mean_ll": base_ll, "rate_at_melee_d": m.hazard(S.MELEE_D), "rate_at_2": m.hazard(2.0), "probes": probes,
            "rings": sorted({s[3] for s in samples})}


def press_rows(keys):
    """[(kind "swing" | "finish", weight, killed)] of the presses (the module docstring)."""
    out = []
    for key in keys:
        lines, frames, _ = load(key, keep=True)
        walls = [f["wallMs"] for f in frames]
        for ln in lines:
            if ln.get("kind") != "act" or ln.get("state") != "done" or ln.get("type") not in ("attack", "stomp",
                                                                                                 "melee"):
                continue
            i = bisect.bisect_right(walls, ln["wallMs"]) - 1
            f = frames[i] if i >= 0 else {}
            body, st = f.get("body") or {}, f.get("stats") or {}
            mood = M.moodle_mult(st.get("endurance"), st.get("fatigue"))
            swing_w = mood / M.pain_divisor(body.get("armPain"))
            r = ln.get("result") or {}
            if ln["type"] == "attack":
                if r.get("attackStarted") is not False:
                    out.append(("swing", swing_w, r.get("targetDead") is True))
            elif ln["type"] == "stomp":
                out.append(("finish", mood, r.get("targetDead") is True))
            else:
                swings = r.get("swings") or 0
                fins = (r.get("floors") or 0) + (r.get("stomps") or 0)
                kill = r.get("kill") is True
                for k in range(swings):
                    out.append(("swing", swing_w, kill and fins == 0 and k == swings - 1))
                for k in range(fins):
                    out.append(("finish", mood, kill and k == fins - 1))
    return out


def fit_presses(rows):
    out = {}
    for kind in ("swing", "finish"):
        rs = [r for r in rows if r[0] == kind]
        kills = sum(1 for r in rs if r[2])
        units = sum(r[1] for r in rs)
        p = kills / units if units > 0 else 0.0
        probes = {}
        for k in PROBE:
            q = min(p * k, 1.0)
            probes["x%.2f" % k] = {"p": q, "p_kill_horizon": 1.0 - (1.0 - q) ** (S.T_MAX / S.SWING_S)}
        out[kind] = {"n": len(rs), "kills": kills, "weighted_presses": units, "p": p,
                     "p_kill_horizon": 1.0 - (1.0 - min(p, 1.0)) ** (S.T_MAX / S.SWING_S), "probes": probes}
    return out


def fit_models():
    reduced = fit_hazard(hit_samples(HIT_SET))
    full = fit_hazard(hit_samples(FULL_SET), full=True)
    presses = fit_presses(press_rows(HIT_SET))
    models = M.Models(reduced["coef"]["b0"], reduced["coef"]["b1"], presses["swing"]["p"], presses["finish"]["p"])
    return models, {"hazard": reduced, "hazard_full_f15": full, "presses": presses,
                    "used": {"hit_b0": models.hit_b0, "hit_b1": models.hit_b1, "p_swing": models.p_swing,
                             "p_finish": models.p_finish}}


# ================================================================ stage 2: the verdicts
def _ctx(row):
    g = row.get("goal") or {}
    args = g.get("args") or {}
    target = (args["x"], args["y"]) if isinstance(args.get("x"), (int, float)) and isinstance(
        args.get("y"), (int, float)) else None
    branch = row.get("branch")
    needs = branch if branch in ("need", "load", "night") else None
    return A.Context(goal="loot" if g.get("type") in ("LootBuilding", "Stock") else "travel", goal_target=target,
                     needs=needs)


def _walking(row):
    a = row.get("action") or {}
    return row.get("branch") == "goal" and (a.get("type") == "walkTo" or (row.get("inputs") or {}).get(
        "running") == "walkTo")


def _behind_door(world, sit):
    me = (sit.x, sit.y)
    marked = world.marked_doors()
    return any(z.d <= DOOR_HELD_R and portal_between(world, me, (z.x, z.y), marked, sit.on_room) is not None
               for z in sit.zeds)


def label(sit, cands, world, row):
    """[(rule, labelled candidate, [the others it must beat])] of one line (the module docstring's THE RULES)."""
    ok = [c for c in cands if c.veto is None]
    by = {c.key: c for c in ok}
    out = []
    near = sit.standing(DANGER_R)
    crowd = sit.aware_standing(LISTED_R)
    if (sit.armed and len(near) == 1 and "fight:%s" % near[0].id in by and len(crowd) < GROUP_N
            and (near[0].aware or not S.spent(sit))):
        c = by["fight:%s" % near[0].id]
        out.append(("one", c, [o for o in ok if o.kind != "fight"]))
    dress = next((c for c in ok if c.kind == "dress"), None)
    if dress is not None and len(crowd) < GROUP_N:
        others = [o for o in ok if o is not dress and o.kind != "fight"]
        if not near:
            out.append(("dress_quiet", dress, others))
        elif sit.nearest_standing().d > KEEP_R:
            out.append(("dress_far", dress, others))
    sneak = by.get("sneak")
    if sneak is not None and _walking(row):
        out.append(("sneak", sneak, [o for o in ok if o.kind in ("travel", "loot", "retreat")]))
    rets = sorted((c for c in ok if c.kind == "retreat"), key=lambda c: (c.filter.d, c.key))
    far = [o for o in ok if o.kind == "fight" and o.zed.d > KEEP_R]
    if rets and far and len(sit.aware_standing(KEEP_R)) >= GROUP_N:
        out.append(("group", rets[0], far))
    elif rets and far and len(sit.aware_standing(DANGER_R)) >= GROUP_N:
        out.append(("group_coming", rets[0], far))
    if _behind_door(world, sit):
        out.append(("door", None, ok))
    return out


def verdicts(models, keys=VERDICT_SET):
    """{rows: [...], structural: {...}, door: {...}, labelled: [...], candidates: n} over the rings."""
    rows, structural, labelled = [], {}, []
    door = {"lines": 0, "with_fight_or_goal": 0, "wait_candidates": 0}
    n_cands = 0
    for key in keys:
        lines, _, drows = load(key)
        for k, row, sit, world in R.situations(lines, drows):
            ctx = _ctx(row)
            cands = A.generate(sit, ctx, world)
            n_cands += len(cands)
            raws = {c.key: S.terms(c, sit, ctx, models) for c in cands}
            for rule, lab, others in label(sit, cands, world, row):
                if rule == "door":
                    door["lines"] += 1
                    door["with_fight_or_goal"] += any(c.kind in ("fight", "travel", "loot", "sneak") for c in others)
                    door["wait_candidates"] += sum(1 for c in others if c.kind == "wait")
                    continue
                labelled.append({"ring": key, "line": k, "rule": rule, "act": lab.key,
                                 "raw": {c.key: raws[c.key] for c in [lab] + others}})
                pairs = [(o.key, o.kind, raws[o.key]) for o in others]
                if lab.kind == "retreat":   # a retreat is chosen only above RETREAT_FLOOR (`select.eligible`)
                    pairs.append(("floor", "floor", dict.fromkeys(S.TERMS, 0.0)))
                for okey, okind, oraw in pairs:
                    a, const = _row(raws[lab.key], oraw)
                    if okind == "floor":
                        const -= S.RETREAT_FLOOR
                    rec = {"ring": key, "line": k, "rule": rule, "act": lab.key, "kind": lab.kind, "other": okey,
                           "other_kind": okind, "a": a, "c": const}
                    if all(abs(x) <= TOL for x in a):
                        s = structural.setdefault(rule, {"n": 0, "held": 0, "least": None})
                        s["n"] += 1
                        s["held"] += const >= MARGIN - TOL
                        if s["least"] is None or const < s["least"]["c"]:
                            s["least"] = {"ring": key, "line": k, "act": lab.key, "other": okey, "c": const}
                    else:
                        rows.append(rec)
    return {"rows": rows, "structural": structural, "door": door, "labelled": labelled, "candidates": n_cands}


def _row(raw_l, raw_o):
    """(a over NAMES, c): U(l) - U(o) = a.w + c, H's terms in c (`select.TERM_WEIGHT`)."""
    a = dict.fromkeys(NAMES, 0.0)
    c = 0.0
    for t, wname in S.TERM_WEIGHT.items():
        diff = raw_l[t] - raw_o[t]
        if wname == "H":
            c += W.H * diff
        else:
            a[wname] += diff
    return [a[n] for n in NAMES], c


def fit_lp(rows):
    """The chosen point, the intervals, the slacks (the module docstring)."""
    n = len(NAMES)
    if not rows:
        return {"status": "no rows"}
    Arow = np.array([r["a"] for r in rows])
    crow = np.array([r["c"] for r in rows])
    norms = np.linalg.norm(Arow, axis=1)
    lo, hi = BOX
    # chebyshev: max t; -a.w + |a| t <= c - MARGIN; -w + t <= -lo; w + t <= hi; t in [-hi, hi]
    G, h = [], []
    for a, c, nm in zip(Arow, crow, norms):
        G.append(list(-a) + [nm])
        h.append(c - MARGIN)
    for j in range(n):
        e = [0.0] * (n + 1)
        e[j], e[n] = -1.0, 1.0
        G.append(e)
        h.append(-lo)
        e = [0.0] * (n + 1)
        e[j], e[n] = 1.0, 1.0
        G.append(e)
        h.append(hi)
    G.append([0.0] * n + [1.0])
    h.append(hi)
    G.append([0.0] * n + [-1.0])
    h.append(hi)
    status, x, t = lp_max([0.0] * n + [1.0], G, h)
    out = {"status": status, "radius": t, "box": list(BOX), "margin": MARGIN, "rows": len(rows)}
    if status != "optimal" or t < -TOL:
        out["status"] = "empty"
        out["conflicts"] = conflicts(rows)
        return out
    w = x[:n]
    out["chosen"] = dict(zip(NAMES, map(float, w)))
    # intervals: rows -a.w <= c - MARGIN, box
    G2 = [list(-a) for a in Arow] + [list(e) for j in range(n) for e in (_unit(n, j, -1.0), _unit(n, j, 1.0))]
    h2 = list(crow - MARGIN) + [v for j in range(n) for v in (-lo, hi)]
    intervals, at_bound = {}, []
    for j, name in enumerate(NAMES):
        _, xa, va = lp_max(_unit(n, j, 1.0), G2, h2)
        _, xb, vb = lp_max(_unit(n, j, -1.0), G2, h2)
        intervals[name] = [float(-vb), float(va)]
        for end, b in ((-vb, lo), (va, hi)):
            if abs(end - b) <= 1e-7:
                at_bound.append({"weight": name, "bound": b})
    out["intervals"] = intervals
    out["at_bound"] = at_bound
    slack = Arow @ w + crow - MARGIN
    groups = {}
    for r, s in zip(rows, slack):
        g = groups.setdefault("%s|%s|%s" % (r["rule"], r["kind"], r["other_kind"]),
                              {"n": 0, "least": None, "greatest": None})
        g["n"] += 1
        if g["least"] is None or s < g["least"]["slack"]:
            g["least"] = {"slack": float(s), "ring": r["ring"], "line": r["line"], "act": r["act"],
                          "other": r["other"]}
        if g["greatest"] is None or s > g["greatest"]:
            g["greatest"] = float(s)
    out["slacks"] = dict(sorted(groups.items()))
    out["least_slack"] = float(np.min(slack))
    return out


def _unit(n, j, v):
    e = [0.0] * n
    e[j] = v
    return e


def conflicts(rows):
    """{rule pair: feasible} of the rows two rules make together (an empty region's report, never its resolution)."""
    rules = sorted({r["rule"] for r in rows})
    out = {}
    for i, a in enumerate(rules):
        for b in rules[i:]:
            sub = [r for r in rows if r["rule"] in (a, b)]
            res = fit_lp_feasible(sub)
            out["%s+%s" % (a, b)] = res
    return out


def fit_lp_feasible(rows):
    n = len(NAMES)
    lo, hi = BOX
    G = [list(-np.array(r["a"])) for r in rows] + [e for j in range(n) for e in (_unit(n, j, -1.0), _unit(n, j, 1.0))]
    h = [r["c"] - MARGIN for r in rows] + [v for j in range(n) for v in (-lo, hi)]
    status, _, _ = lp_max([0.0] * n, G, h)
    return status == "optimal"


def stability(labelled, chosen):
    """{weight: {x0.95: {moved, least, greatest}, x1.05: ...}}: the labelled lines whose margin (the labelled score
    less the best rival's) moves when the weight is scaled (the module docstring)."""
    def margins(w):
        out = []
        for v in labelled:
            raw = v["raw"]
            score = {k: sum(w[S.TERM_WEIGHT[t]] * x for t, x in r.items()) for k, r in raw.items()}
            rivals = [s for k, s in score.items() if k != v["act"]]
            if rivals:
                out.append(score[v["act"]] - max(rivals))
        return np.array(out)
    base_w = dict(chosen, H=W.H)
    base = margins(base_w)
    res = {}
    for name in NAMES:
        row = {}
        for k in PROBE:
            m = margins(dict(base_w, **{name: base_w[name] * k}))
            diff = m - base
            moved = int(np.sum(np.abs(diff) > 1e-9))
            row["x%.2f" % k] = {"moved": moved, "least": float(np.min(diff)) if len(diff) else 0.0,
                                "greatest": float(np.max(diff)) if len(diff) else 0.0}
        res[name] = row
    return {"lines": int(len(base)), "probes": res}


# ================================================================ the artifact
def compute():
    _LOADED.clear()
    models, model_rep = fit_models()
    ver = verdicts(models)
    lp = fit_lp(ver["rows"])
    stab = stability(ver["labelled"], lp["chosen"]) if "chosen" in lp else None
    counts = dict.fromkeys((r for r in RULES if r != "door"), 0)
    for v in ver["labelled"]:
        counts[v["rule"]] = counts.get(v["rule"], 0) + 1
    return {
        "tool": "tools/utility_fit.py",
        "inputs": {key: {os.path.basename(p): sha256(p) for p in ring_files(key)} for key in RINGS},
        "rings": dict(RINGS),
        "models": model_rep,
        "verdicts": {"labelled_lines": counts, "rows": len(ver["rows"]), "structural": ver["structural"],
                     "door": ver["door"], "candidates": ver["candidates"]},
        "lp": lp,
        "stability": stab,
    }


def text(art):
    return json.dumps(_r(art), sort_keys=True, indent=1) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fit the situation utility's models and bound its weights.")
    ap.add_argument("--write", action="store_true", help="write the compact artifact")
    ap.add_argument("--check", action="store_true", help="recompute and compare with the artifact")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    got = text(compute())
    if args.check:
        with open(args.out, encoding="utf-8") as f:
            have = f.read()
        if have != got:
            a, b = json.loads(have), json.loads(got)
            diff = next((k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)), None)
            print("utility_fit --check: differs at %r" % diff)
            return 1
        print("utility_fit --check: in sync")
        return 0
    if args.write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(got)
    print(got[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
