"""A chained day: sessions booted one after another, each from a fixture snapshotted off the last one's run.

`snapshot_cmd(run_dir, name, parent, session)` is the `pzt snapshot --from-run` argv the controller runs between two
sessions. `lineage_diff(prev_artifact, first_frame)` checks the new session picked up where the last one ended: the
last session's last kept frame (`out["loop"]["last_frames"][-1]`) against the new session's first frame, each quantity
{prev, now}, `ok` only when every `now` lies within LINEAGE_TOL of its `prev`.
"""
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PZT = os.path.join(TESTING, "pzt")

LINEAGE_TOL = {"position": 0.5, "health": 0.01, "stat": 0.001, "inventory_n": 0, "game_min": 0.0}
STATS = ("hunger", "thirst", "fatigue")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _d(v):
    return v if isinstance(v, dict) else {}


def _within(prev, now, tol):
    return _num(prev) is not None and _num(now) is not None and abs(now - prev) <= tol + 1e-12


def _last_frame(prev_artifact):
    frames = _d(_d(prev_artifact).get("loop")).get("last_frames")
    return frames[-1] if isinstance(frames, list) and frames and isinstance(frames[-1], dict) else {}


def lineage_diff(prev_artifact, first_frame):
    """{position {prev, now, d}, health, stats {hunger, thirst, fatigue}, inventory_n, game_min (each {prev, now}),
    ok}. Position is [x, y] and d the planar distance in tiles; inventory_n is the frame's load.n."""
    a, b = _last_frame(prev_artifact), _d(first_frame)
    am, bm = _d(a.get("me")), _d(b.get("me"))
    pa = [am.get("x"), am.get("y")] if am else None
    pb = [bm.get("x"), bm.get("y")] if bm else None
    d = None
    if pa and pb and all(_num(v) is not None for v in pa + pb):
        d = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    out = {"position": {"prev": pa, "now": pb, "d": d},
           "health": {"prev": _d(a.get("body")).get("health"), "now": _d(b.get("body")).get("health")},
           "stats": {k: {"prev": _d(a.get("stats")).get(k), "now": _d(b.get("stats")).get(k)} for k in STATS},
           "inventory_n": {"prev": _d(a.get("load")).get("n"), "now": _d(b.get("load")).get("n")},
           "game_min": {"prev": a.get("gameMin"), "now": b.get("gameMin")}}
    ok = (d is not None and d <= LINEAGE_TOL["position"]
          and _within(out["health"]["prev"], out["health"]["now"], LINEAGE_TOL["health"])
          and all(_within(v["prev"], v["now"], LINEAGE_TOL["stat"]) for v in out["stats"].values())
          and _within(out["inventory_n"]["prev"], out["inventory_n"]["now"], LINEAGE_TOL["inventory_n"])
          and _within(out["game_min"]["prev"], out["game_min"]["now"], LINEAGE_TOL["game_min"]))
    out["ok"] = bool(ok)
    return out


def snapshot_cmd(run_dir, name, parent, session):
    """The argv of `pzt snapshot --from-run <run_dir> --name <name> --parent <parent> --session <n>`."""
    return [sys.executable, PZT, "snapshot", "--from-run", str(run_dir), "--name", str(name), "--parent", str(parent),
            "--session", str(int(session))]
