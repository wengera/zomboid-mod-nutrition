"""The search the fit tools share (Plan 11g close): fit_gut_satiety.py and fit_deficit_drive.py.

Search scores candidate patches once each (a patch already scored, or twice in one batch, is not re-run), in order,
serially or on a spawn pool of `jobs` processes; `order` holds every scored candidate in the order it was first
scored, and `best()` the lowest loss (min keeps the first of equal losses).

grid_then_refine runs every point of the spec's grid (the product of its value lists, in the spec's order; `valid`
drops a point the tool refuses), then a coordinate refinement from the best grid point: for each refined constant in
turn, the value times and over the step factor, each rounded to SIG significant digits and passed through the tool's
`admit` (its bounds, and any rule of its own), a move kept when it lowers the loss; a round with no move takes the
square root of the factor. Each tool keeps its own loss, bounds and choice of the final point.
"""
import itertools
import math

SIG = 6                         # significant digits a refined value keeps


def round_sig(x, sig=SIG):
    if x == 0:
        return 0.0
    return float(round(x, sig - 1 - int(math.floor(math.log10(abs(x))))))


class Search:
    """Scores patches through `worker(job(patch))`; `record(result, phase)` is the candidate kept."""

    def __init__(self, worker, jobs, job=None, record=None):
        self.worker = worker
        self.job = job if job is not None else (lambda p: p)
        self.record = record if record is not None else (lambda r, phase: dict(r, phase=phase))
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
        args = [self.job(p) for _, p in todo]
        if self.pool is not None:
            results = self.pool.map(self.worker, args, chunksize=1)
        else:
            results = [self.worker(a) for a in args]
        for (k, _), r in zip(todo, results):
            r = self.record(r, phase)
            self.seen[k] = r
            self.order.append(r)
        return [self.seen[k] for k in keys]

    def best(self):
        return min(self.order, key=lambda r: r["loss"])      # min keeps the first of equal losses


def grid_then_refine(spec, s, default_refine, admit, valid=None):
    """The grid, then the coordinate refinement (module doc) on the Search `s`. admit(name, value, point) returns the
    value to try (clamped to the tool's bounds) or None to skip it."""
    params = spec["params"]
    names = list(params)
    grid = [dict(zip(names, vals)) for vals in itertools.product(*(params[n] for n in names))]
    if valid is not None:
        grid = [p for p in grid if valid(p)]
    s.score(grid, "grid")
    refine = dict(default_refine)
    refine.update(spec.get("refine", {}))
    rnames = refine.get("params", names)
    factor = float(refine["factor"])
    point = dict(s.best()["params"])
    for _ in range(int(refine["rounds"])):
        moved = False
        for n in rnames:
            here = s.score([point], "refine")[0]
            vals = []
            for v in (round_sig(point[n] * factor), round_sig(point[n] / factor)):
                v = admit(n, v, point)
                if v is not None and v != point[n] and v not in vals:
                    vals.append(v)
            for r in (s.score([dict(point, **{n: v}) for v in vals], "refine") if vals else []):
                if r["loss"] < here["loss"]:
                    here = r
            if here["params"] != point:
                point = dict(here["params"])
                moved = True
        if not moved:
            factor = math.sqrt(factor)
    return s.order
