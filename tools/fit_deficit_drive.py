"""The deficit drive's fit (Plan 11g Task 7; the method of Plan 11f Task 2c fix 1, its widened search).

    python tools/fit_deficit_drive.py --out <dir> [--grid <spec.json>] [--jobs N]
    python tools/fit_deficit_drive.py --compact <fit.json> --out <dir>

Scores candidate constants of the deficit drive (K.deficit, NR_Kernel_Deficit.lua: the balance span, the deficit floor
and the bypass ramp's two ends) against testing/tests/kernel/deficit_oracles.py on the server path and writes
<dir>/fit.json and <dir>/fit-compact.json (the compact projection is fit_gut_satiety's, ruling T6c-4).

The objective (deficit_oracles.objective): a candidate is feasible when every constraint holds (Karl's BAL arm, now
carried by satiety, inside -64 to -46 %; the steady eater; six meals against three; S1255's ceiling) and every fixed
oracle holds; among the feasible the fit maximises the smallest scored margin (the 36 h fast's two days, Karl's DEF arm
at the worst of twin K's five billings, King 2011 at steady state), each a distance inside its band over its
half-width. The loss written per candidate is

    loss = -(the smallest scored margin) + PENALTY x (the constraints' total shortfall)

so a lower loss is better and an infeasible point ranks below any feasible one whose margin is above -PENALTY x its
shortfall. The chosen point is the lowest loss; a candidate within TIE of it that lies nearer the start point (the
shipped constants) is preferred (Plan 11f Task 2c's tie rule: a margin difference under 0.001 is noise of the replay's
whole minutes).

The fixed oracles (Whybrow 2008, E-MECHANIC) read the exercise lag L, which none of the fitted constants touches, so
they are read once at the start point and once at the chosen point (both written), not per candidate.

The search: every point of the grid (the product of the spec's value lists, in the spec's order) whose bypass ramp
rises (EX_BYPASS_HI above EX_BYPASS_LO), then a coordinate refinement from the best point as in fit_gut_satiety: each
refined constant times and over the factor (a zero tries ZERO_STEP), a move kept when it lowers the loss, a round
with no move taking the square root of the factor. Values are rounded to six significant digits and clamped to their
bounds; a point already scored is not re-run.

The spec (JSON): {"params": {"deficit.BALANCE_SPAN_KCAL": [3100, 3800], ...}, "refine": {"rounds": 3, "factor": 1.1}}
Without --grid the spec is PARAMS at their shipped values, refined. fit.json is deterministic apart from `date`.
"""
import argparse
import datetime
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fit_gut_satiety as FG  # noqa: E402  (puts testing/tests and tools on sys.path)
from kernel import deficit_oracles as DO  # noqa: E402
from kernel.conftest import LuaHost  # noqa: E402

PARAMS = ("deficit.BALANCE_SPAN_KCAL", "deficit.DEFICIT_FLOOR", "deficit.EX_BYPASS_LO", "deficit.EX_BYPASS_HI")
# (low, high, low inclusive): the span positive; the floor non-negative; LO at least S1318's bound (Whybrow 2008: the
# men's high-exercise arm runs a 24-h deficit share of 0.2814, which compensates about 30 % and so takes a bypass weight
# of 0: LO >= 0.282, Plan 11f Task 2c fix 2); HI at most a whole day's expenditure
BOUNDS = {"deficit.BALANCE_SPAN_KCAL": (0.0, math.inf, False), "deficit.DEFICIT_FLOOR": (0.0, math.inf, True),
          "deficit.EX_BYPASS_LO": (0.282, 1.0, True), "deficit.EX_BYPASS_HI": (0.282, 1.0, False)}
PENALTY = 10.0                  # a DESIGN CHOICE: the loss per unit of constraint shortfall (margins run -inf..1)
TIE = 0.001                     # a DESIGN CHOICE: Plan 11f Task 2c's tie (its margins rounded to 0.001)
ZERO_STEP = 0.005               # the refinement's step away from a zero (the floor)
DEFAULT_REFINE = {"rounds": 3, "factor": 1.1}


def _bounds(name):
    return BOUNDS.get(name, (0.0, math.inf, False))


def _inside(name, v):
    lo, hi, inc = _bounds(name)
    return (v >= lo if inc else v > lo) and v <= hi


def _valid(patch):
    lo = patch.get("deficit.EX_BYPASS_LO")
    hi = patch.get("deficit.EX_BYPASS_HI")
    return lo is None or hi is None or hi > lo


def load_spec(spec):
    """A spec from a dict, a JSON file path or a JSON string; validated against BOUNDS."""
    if isinstance(spec, str):
        if os.path.exists(spec):
            with open(spec, encoding="utf-8") as fh:
                spec = json.load(fh)
        else:
            spec = json.loads(spec)
    params = spec.get("params")
    if not isinstance(params, dict) or not params:
        raise ValueError("the spec names no params")
    for name, values in params.items():
        if not isinstance(values, list) or not values or not all(isinstance(v, (int, float)) for v in values):
            raise ValueError("params.%s is not a non-empty list of numbers" % name)
        for v in values:
            if not _inside(name, v):
                raise ValueError("params.%s: %r is outside its bound %r" % (name, v, _bounds(name)))
    for name in spec.get("refine", {}).get("params", []):
        if name not in params:
            raise ValueError("refine.params names %s, which the grid does not" % name)
    return spec


def default_spec():
    return {"params": {k: [v] for k, v in FG.current(PARAMS).items()}, "refine": dict(DEFAULT_REFINE)}


def read_groups(patch, names):
    """The named reading groups on a fresh host with `patch`, the server path's hosts patched the same."""
    FG._patch_server_path()
    FG._ACTIVE = dict(patch)
    try:
        h = FG.new_host(patch)
        out = {}
        for name in names:
            try:
                out[name] = DO.GROUPS[name](h)
            except Exception as e:           # a candidate the kernel cannot run is infeasible, not a crash
                out[name] = FG.ReadError("%s: %s" % (type(e).__name__, e))
        return out
    finally:
        FG._ACTIVE = {}


def score(readings):
    """{loss, feasible, smallest, shortfall, margins, values} for a full set of readings."""
    margins = DO.margins(readings)
    values = {}
    for o in DO.ORACLES:
        try:
            values[o.name] = o.pick(readings)
        except Exception:
            values[o.name] = None
    feasible, smallest, short = DO.objective(readings)
    loss = -smallest + PENALTY * short
    if not math.isfinite(loss):
        loss = 1e9
    return {"loss": loss, "feasible": feasible, "smallest": smallest, "shortfall": short,
            "margins": FG._clean(margins), "values": FG._clean(values)}


def evaluate(patch, fixed):
    """Every moving group on a fresh host with `patch`, the fixed readings `fixed` beside them, scored."""
    moving = [g for g in DO.GROUPS if g not in DO.FIXED_GROUPS]
    readings = read_groups(patch, moving)
    readings.update(fixed)
    r = score(readings)
    r["params"] = dict(patch)
    return r


def _worker(args):
    return evaluate(*args)


def round_sig(x):
    return FG.round_sig(x)


class _Search:
    def __init__(self, jobs, fixed):
        self.fixed = fixed
        self.seen = {}
        self.order = []
        self.pool = None
        if jobs > 1:
            import multiprocessing
            self.pool = multiprocessing.get_context("spawn").Pool(jobs)

    def close(self):
        if self.pool is not None:
            self.pool.close()
            self.pool.join()

    def score(self, patches, phase):
        keys = [tuple(sorted(p.items())) for p in patches]
        todo = []
        for k, p in zip(keys, patches):
            if k not in self.seen and k not in [t[0] for t in todo]:
                todo.append((k, p))
        args = [(p, self.fixed) for _, p in todo]
        results = self.pool.map(_worker, args, chunksize=1) if self.pool is not None else [_worker(a) for a in args]
        for (k, _), r in zip(todo, results):
            r = dict(r, phase=phase)
            self.seen[k] = r
            self.order.append(r)
        return [self.seen[k] for k in keys]


def distance(params, start):
    """The distance from the start point: each constant's relative change (the floor's over 0.1), squared, summed."""
    d = 0.0
    for k, v in params.items():
        v0 = start.get(k, v)
        d += ((v - v0) / max(abs(v0), 0.1)) ** 2
    return math.sqrt(d)


def choose(cands, start):
    """The lowest loss; among the candidates within TIE of it, the one nearest the start point (then the first)."""
    best = min(c["loss"] for c in cands)
    near = [c for c in cands if c["loss"] <= best + TIE]
    return min(near, key=lambda c: distance(c["params"], start))


def search(spec, jobs=1, fixed=None, start=None):
    params = spec["params"]
    names = list(params)
    if start is None:
        start = FG.current(names)
    if fixed is None:
        fixed = read_groups({}, DO.FIXED_GROUPS)
    s = _Search(jobs, fixed)
    try:
        grid = [dict(zip(names, vals)) for vals in itertools.product(*(params[n] for n in names))]
        s.score([p for p in grid if _valid(p)], "grid")
        refine = dict(DEFAULT_REFINE)
        refine.update(spec.get("refine", {}))
        rnames = refine.get("params", names)
        factor = float(refine["factor"])
        point = dict(min(s.order, key=lambda r: r["loss"])["params"])
        for _ in range(int(refine["rounds"])):
            moved = False
            for n in rnames:
                here = s.score([point], "refine")[0]
                vals = []
                cands = (ZERO_STEP,) if point[n] == 0 else (round_sig(point[n] * factor), round_sig(point[n] / factor))
                for v in cands:
                    lo, hi, _ = _bounds(n)
                    v = min(max(v, lo), hi)
                    if v != point[n] and v not in vals and _inside(n, v) and _valid(dict(point, **{n: v})):
                        vals.append(v)
                for r in (s.score([dict(point, **{n: v}) for v in vals], "refine") if vals else []):
                    if r["loss"] < here["loss"]:
                        here = r
                if here["params"] != point:
                    point = dict(here["params"])
                    moved = True
            if not moved:
                factor = math.sqrt(factor)
        return s.order, choose(s.order, start), fixed, start
    finally:
        s.close()


def fit(spec, out, jobs=1):
    """Runs the search and writes <out>/fit.json and <out>/fit-compact.json; returns the chosen candidate."""
    FG.current(list(spec["params"]))                     # refuse an unknown constant before any run
    cands, chosen, fixed, start = search(spec, jobs)
    at_chosen = read_groups(chosen["params"], DO.FIXED_GROUPS)
    doc = {"grid": spec, "head": FG.head_sha(), "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "start": start, "penalty": PENALTY, "tie": TIE,
           "oracles": [{"name": o.name, "group": o.group, "role": o.role, "row": o.row, "lo": o.lo, "hi": o.hi,
                        "scale": o.scale, "tol": o.tol} for o in DO.ORACLES],
           "fixed": {"start": FG._clean(fixed), "chosen": FG._clean(at_chosen)},
           "candidates": cands, "chosen": chosen}
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "fit.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    FG.write_compact(path, out)
    return chosen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grid", help="the grid spec: a JSON file or a JSON string (default: the shipped values, refined)")
    ap.add_argument("--out", required=True, help="the directory fit.json and fit-compact.json are written to")
    ap.add_argument("--compact", metavar="FIT_JSON", help="write <out>/fit-compact.json from this full fit.json; no fit runs")
    ap.add_argument("--jobs", type=int, default=1, help="candidates scored in parallel (one host per process)")
    args = ap.parse_args(argv)
    if args.compact:
        print("wrote " + FG.write_compact(args.compact, args.out))
        return 0
    spec = load_spec(args.grid) if args.grid else default_spec()
    chosen = fit(spec, args.out, args.jobs)
    print("chosen: loss %.6g (smallest margin %.4f, feasible %s) at %s" % (
        chosen["loss"], chosen["smallest"], chosen["feasible"], json.dumps(chosen["params"], sort_keys=True)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
