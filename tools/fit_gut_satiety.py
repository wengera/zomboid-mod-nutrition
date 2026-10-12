"""The gut-satiety joint fit (Plan 11g Task 5; spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 4).

    python tools/fit_gut_satiety.py --out <dir> [--grid <spec.json>] [--jobs N] [--stage A]

Scores candidate constants against every oracle of testing/tests/kernel/gut_oracles.py (ORACLES: the 11c/11d meal-study
replays, the gut-satiety oracles of Task 3, Karl's surplus day, the fat trio of ruling T3-3 and the stability checks of
Task 6c) and writes <dir>/fit.json.

The search: every point of the grid (the product of the spec's value lists, in the spec's order), then a coordinate
refinement from the best point: for each refined constant in turn, the value times and over the step factor; a move is
kept when it lowers the loss; a round with no move takes the square root of the factor. Values are rounded to six
significant digits, and a point already scored is not re-run.

The loss: the sum over every hard and one-sided oracle of its relative miss beyond its tolerance (gut_oracles.Oracle.miss,
each at weight 1); a reading-kind oracle is reported beside it, never in it. Ties keep the earlier candidate.

The patch: one fresh lupa kernel host per candidate (the kernel tests' LuaHost) with the constants set on its kernel
table, and the server path's hosts (tools/replay_live.py builds server_host.Host for Karl's twin) patched the same way
while the candidate runs; no tracked file is ever written. A constant is named under K.satiety (FULL_WEIGHT) or by its
kernel path (stomach.CAPACITY_MAX_G); an unknown or non-numeric one is refused.

The spec (JSON):
    {"params": {"FULL_WEIGHT": [0.5, 0.55], "MEAL_REQ": [6]},
     "refine": {"rounds": 3, "factor": 1.25, "params": ["FULL_WEIGHT", "MEAL_REQ"]}}
`refine.params` defaults to every grid parameter, `rounds` to 3 and `factor` to 1.25; rounds 0 runs the grid alone.
Without --grid the spec is DEFAULT_PARAMS at their shipped values, refined.

fit.json is deterministic: the same spec on the same tree gives byte-identical output, apart from `date`. It holds the
spec, the HEAD sha, the date, every candidate (its phase, params, loss, and each oracle's value and miss) and the chosen
point.

--stage A adds the absorbed stage's constants (STAGE_A_PARAMS) to the search; no kernel builds A (Task 6 ruled a single
stage), so it exits 2, naming the constants it did not find.
"""
import argparse
import datetime
import itertools
import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(REPO, "testing", "tests")
TOOLS = os.path.join(REPO, "tools")
for _p in (TESTS, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from kernel import gut_oracles as GO  # noqa: E402
from kernel.conftest import LuaHost  # noqa: E402
import replay_live as RL  # noqa: E402

DEFAULT_PARAMS = ("FULL_WEIGHT", "MEAL_REQ", "MEAL_STEEP", "MEAL_HALF_LIFE_H", "W_PROTEIN", "W_FAT", "PROTEIN_FILL")
STAGE_A_PARAMS = ("A_REQ", "A_STEEP", "A_HALF_LIFE_H")
DEFAULT_REFINE = {"rounds": 3, "factor": 1.25}
SIG = 6                         # significant digits a refined value keeps
BOUNDS = {"FULL_WEIGHT": (0, 1), "LIQUID_WEIGHT": (0, 1)}    # (exclusive low, inclusive high); any other: (0, inf)

_ACTIVE = {}                    # the candidate's patch while it runs, read by the server path's patched hosts


def _path(name):
    return name.split(".") if "." in name else ["satiety", name]


def _apply(K, patch):
    """Set each constant of `patch` on the kernel table K; refuses an unknown or non-numeric constant."""
    for name, value in patch.items():
        segs = _path(name)
        t = K
        for s in segs[:-1]:
            t = t[s]
            if t is None:
                raise ValueError("unknown constant %s" % name)
        cur = t[segs[-1]]
        if isinstance(cur, bool) or not isinstance(cur, (int, float)):
            raise ValueError("unknown constant %s (not a number on the kernel)" % name)
        t[segs[-1]] = float(value)


def _bounds(name):
    return BOUNDS.get(name, (0, math.inf))


class ReadError(str):
    """A reading group that raised: its error string stands in for the reading, and every oracle on it misses."""
    def __getitem__(self, k):
        raise TypeError("the reading failed: %s" % str(self))


def _patch_server_path():
    """Wraps the top-level server_host module's Host.__init__ once so the active candidate's patch reaches the hosts
    tools/replay_live.py builds. The rebind is process-wide and permanent (it marks the class `_fit_patched`), and a
    no-op while _ACTIVE is empty, so nothing else in the process sees a patch."""
    _, server_host, _ = RL._lua()
    if getattr(server_host.Host, "_fit_patched", False):
        return
    init = server_host.Host.__init__

    def patched(self, *a, **kw):
        init(self, *a, **kw)
        _apply(self.K, _ACTIVE)
    server_host.Host.__init__ = patched
    server_host.Host._fit_patched = True


def new_host(patch=None):
    """A fresh kernel host, `patch` applied."""
    h = LuaHost()
    _apply(h.K, patch or {})
    return h


def current(names):
    """The shipped value of each named constant."""
    h = LuaHost()
    out = {}
    for name in names:
        t = h.K
        for s in _path(name):
            t = None if t is None else t[s]
        if isinstance(t, bool) or not isinstance(t, (int, float)):
            raise ValueError("unknown constant %s" % name)
        out[name] = float(t)
    return out


def _clean(x):
    """JSON-safe: tuples as lists, a non-finite float as a string."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return repr(x)
    return x


def evaluate(patch):
    """Every oracle on a fresh host with `patch`: {params, loss, oracles: {name: {value, miss}}, readings}."""
    _patch_server_path()
    global _ACTIVE
    _ACTIVE = dict(patch)
    try:
        h = new_host(patch)
        readings = {}
        for name, fn in GO.GROUPS.items():
            try:
                readings[name] = fn(h)
            except Exception as e:               # a candidate the kernel cannot run scores NONE_MISS, not a crash
                readings[name] = ReadError("%s: %s" % (type(e).__name__, e))
    finally:
        _ACTIVE = {}
    oracles = {}
    loss = 0.0
    for o in GO.ORACLES:
        try:
            if isinstance(readings[o.group], ReadError):
                raise TypeError(readings[o.group])
            v = o.pick(readings)
            m = o.miss(v)
        except Exception:
            v, m = None, (None if o.kind == "reading" else GO.NONE_MISS)
        oracles[o.name] = {"value": _clean(v), "miss": m}
        if m is not None:
            loss += m
    return {"params": dict(patch), "loss": loss, "oracles": oracles, "readings": _clean(readings)}


def _eval_worker(patch):
    r = evaluate(patch)
    r.pop("readings")
    return r


def round_sig(x, sig=SIG):
    if x == 0:
        return 0.0
    return float(round(x, sig - 1 - int(math.floor(math.log10(abs(x))))))


def load_spec(spec):
    """A spec from a dict, a JSON file path or a JSON string; validated (the constants are checked at evaluation)."""
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
        lo, hi = _bounds(name)
        for v in values:
            if not lo < v <= hi:
                raise ValueError("params.%s: %r is outside its bound (%g, %g]" % (name, v, lo, hi))
    refine = spec.get("refine", {})
    for name in refine.get("params", []):
        if name not in params:
            raise ValueError("refine.params names %s, which the grid does not" % name)
    return spec


def default_spec():
    return {"params": {k: [v] for k, v in current(DEFAULT_PARAMS).items()}, "refine": dict(DEFAULT_REFINE)}


class _Search:
    def __init__(self, jobs):
        self.jobs = jobs
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
        """Score each new patch (in order); returns the results for all of them."""
        keys = [tuple(sorted(p.items())) for p in patches]
        todo = []
        for k, p in zip(keys, patches):
            if k not in self.seen and k not in [t[0] for t in todo]:
                todo.append((k, p))
        if self.pool is not None:
            results = self.pool.map(_eval_worker, [p for _, p in todo])
        else:
            results = [_eval_worker(p) for _, p in todo]
        for (k, _), r in zip(todo, results):
            r = {"phase": phase, "params": r["params"], "loss": r["loss"], "oracles": r["oracles"]}
            self.seen[k] = r
            self.order.append(r)
        return [self.seen[k] for k in keys]

    def best(self):
        return min(self.order, key=lambda r: r["loss"])      # min keeps the first of equal losses


def search(spec, jobs=1):
    params = spec["params"]
    names = list(params)
    s = _Search(jobs)
    try:
        grid = [dict(zip(names, vals)) for vals in itertools.product(*(params[n] for n in names))]
        s.score(grid, "grid")
        refine = dict(DEFAULT_REFINE)
        refine.update(spec.get("refine", {}))
        rnames = refine.get("params", names)
        factor = float(refine["factor"])
        point = dict(s.best()["params"])
        for _ in range(int(refine["rounds"])):
            moved = False
            for n in rnames:
                here = s.score([point], "refine")[0]
                hi = _bounds(n)[1]
                vals = []
                for v in (round_sig(point[n] * factor), round_sig(point[n] / factor)):
                    v = min(v, hi)
                    if v != point[n] and v not in vals:
                        vals.append(v)
                for r in (s.score([dict(point, **{n: v}) for v in vals], "refine") if vals else []):
                    if r["loss"] < here["loss"]:
                        here = r
                if here["params"] != point:
                    point = dict(here["params"])
                    moved = True
            if not moved:
                factor = math.sqrt(factor)
        return s.order, s.best()
    finally:
        s.close()


def head_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()


def fit(spec, out, jobs=1):
    """Runs the search and writes <out>/fit.json; returns the chosen candidate."""
    current(list(spec["params"]))                        # refuse an unknown constant before any run
    cands, chosen = search(spec, jobs)
    doc = {"grid": spec, "head": head_sha(), "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "oracles": [{"name": o.name, "kind": o.kind, "row": o.row, "target": _clean(o.target), "lo": o.lo,
                        "hi": o.hi, "scale": o.scale, "tol": o.tol} for o in GO.ORACLES],
           "candidates": cands, "chosen": chosen}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "fit.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return chosen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grid", help="the grid spec: a JSON file or a JSON string (default: the shipped values, refined)")
    ap.add_argument("--out", required=True, help="the directory fit.json is written to")
    ap.add_argument("--jobs", type=int, default=1, help="candidates scored in parallel (one host per process)")
    ap.add_argument("--stage", choices=("A",), help="A: add the absorbed stage's constants to the search")
    args = ap.parse_args(argv)
    spec = load_spec(args.grid) if args.grid else default_spec()
    if args.stage == "A":
        h = LuaHost()
        missing = [n for n in STAGE_A_PARAMS if h.K.satiety[n] is None]
        if missing:
            sys.stderr.write("fit_gut_satiety: stage A is not in the kernel: K.satiety has no %s. Build A first "
                             "(Plan 11g Task 6, the stage rule), then rerun with --stage A.\n" % ", ".join(missing))
            return 2
        for name, value in current(STAGE_A_PARAMS).items():
            spec["params"].setdefault(name, [value])
            if "params" in spec.get("refine", {}) and name not in spec["refine"]["params"]:
                spec["refine"]["params"].append(name)
    chosen = fit(spec, args.out, args.jobs)
    print("chosen: loss %.6g at %s" % (chosen["loss"], json.dumps(chosen["params"], sort_keys=True)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
