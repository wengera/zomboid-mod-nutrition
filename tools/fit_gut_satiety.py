"""The gut-satiety joint fit (Plan 11g Task 5; spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 4).

    python tools/fit_gut_satiety.py --out <dir> [--grid <spec.json>] [--jobs N]
    python tools/fit_gut_satiety.py --compact <fit.json> --out <dir>

Scores candidate constants against every oracle of testing/tests/kernel/gut_oracles.py (ORACLES: the 11c/11d meal-study
replays, the gut-satiety oracles of Task 3, Karl's surplus day, the fat trio of ruling T3-3 and the stability checks of
Task 6c) and writes <dir>/fit.json.

The search: every point of the grid (the product of the spec's value lists, in the spec's order), then a coordinate
refinement from the best point: for each refined constant in turn, the value times and over the step factor; a move is
kept when it lowers the loss; a round with no move takes the square root of the factor. Values are rounded to six
significant digits and clamped to their bounds (BOUNDS: the high bound inclusive, a value at or under the exclusive
low bound skipped), and a point already scored is not re-run. The search is tools/fitlib.py's, shared with
fit_deficit_drive.

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

A fit run also writes <dir>/fit-compact.json, the projection that is committed (ruling T6c-4; the full fit.json stays in
the gitignored testing/runs/). --compact rebuilds it from a full fit.json: a pure function of the file's bytes, holding
source_sha256 and source_bytes, head, spec (the grid), candidates (the count), chosen (as fit.json records it) and
profile (for each parameter, every distinct value tried with the best loss seen at it, sorted by value).
"""
import argparse
import datetime
import hashlib
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
import dials  # noqa: E402
import fitlib  # noqa: E402

DEFAULT_PARAMS = ("FULL_WEIGHT", "MEAL_REQ", "MEAL_STEEP", "MEAL_HALF_LIFE_H", "W_PROTEIN", "W_FAT", "PROTEIN_FILL",
                  "LIQUID_WEIGHT")
DEFAULT_REFINE = {"rounds": 3, "factor": 1.25}
SIG = fitlib.SIG                # significant digits a refined value keeps
# (exclusive low, inclusive high); any other: (0, inf). LIQUID_WEIGHT is a weight on drunk liquid's mass, at most the
# solid lane's 1 (ruling T6c-5): the bound is the quantity's own range, and two scored rows set the value inside it,
# S1231's null for water drunk alongside (rolls_cw_minus_cas, and the soup's drop rolls_drop) from above and S1233's
# volume slope (rolls98_slope) from below
BOUNDS = {"FULL_WEIGHT": (0, 1), "LIQUID_WEIGHT": (0, 1)}

_ACTIVE = {}                    # the candidate's patch while it runs, read by the server path's patched hosts


def _path(name):
    return name.split(".") if "." in name else ["satiety", name]


def _slot(K, segs):
    """(the kernel table holding the number at the path segs, its key), or None where the path names no number on K
    (an array element's segment is its index)."""
    t = K
    keys = [int(x) if x.isdigit() else x for x in segs]
    for k in keys[:-1]:
        t = t[k] if t is not None and hasattr(t, "items") else None
        if t is None:
            return None
    cur = t[keys[-1]] if hasattr(t, "items") else None
    if isinstance(cur, bool) or not isinstance(cur, (int, float)):
        return None
    return t, keys[-1]


def _apply(K, patch):
    """Set each constant of `patch` on the kernel table K; refuses an unknown or non-numeric constant. The constant's
    dial writes as one dial (tools/dials.py linked): the field its same chain ends at first, then every kernel field
    whose row names it, so a fit of MEAL_REQ (satiety.MEAL_REQ, same = hungerCurve.FED_M) moves the fed threshold with
    it and the pair stays in step; a linked field on a table this host does not load (an adapter's) is skipped. Only
    kernel fields are written, never the registry."""
    for name, value in patch.items():
        own = ".".join(_path(name))
        if _slot(K, own.split(".")) is None:
            raise ValueError("unknown constant %s (not a number on the kernel)" % name)
        for dial_id in dials.linked(own):
            segs = dial_id.split(".")
            slot = _slot(K, segs)
            if slot is None:
                if K[segs[0]] is None:
                    continue
                raise ValueError("%s: the linked dial %s is not a number on the kernel" % (name, dial_id))
            slot[0][slot[1]] = float(value)


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
    return fitlib.round_sig(x, sig)


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


def _record(r, phase):
    return {"phase": phase, "params": r["params"], "loss": r["loss"], "oracles": r["oracles"]}


def _admit(name, v, point):
    """A refined value inside BOUNDS: clamped to the inclusive high bound; at or under the exclusive low, skipped."""
    lo, hi = _bounds(name)
    v = min(v, hi)
    return v if v > lo else None


def search(spec, jobs=1):
    s = fitlib.Search(_eval_worker, jobs, record=_record)
    try:
        fitlib.grid_then_refine(spec, s, DEFAULT_REFINE, _admit)
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


def compact(src):
    """The compact projection of a full fit.json (a pure function of its bytes); see the module doc."""
    with open(src, "rb") as fh:
        raw = fh.read()
    doc = json.loads(raw.decode("utf-8"))
    best = {}
    for c in doc["candidates"]:
        for name, v in c["params"].items():
            row = best.setdefault(name, {})
            if v not in row or c["loss"] < row[v]:
                row[v] = c["loss"]
    profile = {n: [{"value": v, "best_loss": row[v]} for v in sorted(row)] for n, row in best.items()}
    return {"source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw), "head": doc["head"],
            "spec": doc["grid"], "candidates": len(doc["candidates"]), "chosen": doc["chosen"], "profile": profile}


def write_compact(src, out):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "fit-compact.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(compact(src), fh, indent=1, sort_keys=True)
        fh.write("\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grid", help="the grid spec: a JSON file or a JSON string (default: the shipped values, refined)")
    ap.add_argument("--out", required=True, help="the directory fit.json and fit-compact.json are written to")
    ap.add_argument("--compact", metavar="FIT_JSON", help="write <out>/fit-compact.json from this full fit.json; no fit runs")
    ap.add_argument("--jobs", type=int, default=1, help="candidates scored in parallel (one host per process)")
    args = ap.parse_args(argv)
    if args.compact:
        print("wrote " + write_compact(args.compact, args.out))
        return 0
    spec = load_spec(args.grid) if args.grid else default_spec()
    chosen = fit(spec, args.out, args.jobs)
    write_compact(os.path.join(args.out, "fit.json"), args.out)
    print("chosen: loss %.6g at %s" % (chosen["loss"], json.dumps(chosen["params"], sort_keys=True)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
