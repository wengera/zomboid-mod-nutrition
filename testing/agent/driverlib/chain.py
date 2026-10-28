"""A chained day: sessions booted one after another, each from a fixture snapshotted off the last one's run.

`snapshot_cmd(run_dir, name, parent, session)` is the `pzt snapshot --from-run` argv the controller runs between two
sessions. `lineage_diff(prev_artifact, first_frame)` checks the new session picked up where the last one ended: the
last session's last kept frame (`out["loop"]["last_frames"][-1]`) against the new session's first frame, each quantity
{prev, now, delta, tol, ok}, `ok` only when every `now` lies within LINEAGE_TOL of its `prev` (ruling P23-Y: the
clock and the stats move a little between the last kept frame and the server's save at teardown).
"""
import math
import os
import sys

from agent.driverlib.session import _d, _num

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PZT = os.path.join(TESTING, "pzt")

# Ruling P23-Y: the server saves the world at teardown, a few game minutes after the last kept frame, so the restored
# clock and stats move a little past it; position, health and the inventory count do not move with time alone
LINEAGE_TOL = {"position": 0.5, "health": 0.01, "stat": 0.005, "inventory_n": 0, "game_min": 3.0}
STATS = ("hunger", "thirst", "fatigue")


def _last_frame(prev_artifact):
    frames = _d(_d(prev_artifact).get("loop")).get("last_frames")
    return frames[-1] if isinstance(frames, list) and frames and isinstance(frames[-1], dict) else {}


def _pair(prev, now, tol):
    """{prev, now, delta (now - prev, None unless both are numbers), tol, ok (|delta| within tol)}."""
    delta = now - prev if _num(prev) is not None and _num(now) is not None else None
    return {"prev": prev, "now": now, "delta": delta, "tol": tol,
            "ok": delta is not None and abs(delta) <= tol + 1e-12}


def lineage_diff(prev_artifact, first_frame):
    """{position {prev, now, d, tol, ok}, health, stats {hunger, thirst, fatigue}, inventory_n, game_min (each
    {prev, now, delta, tol, ok}), ok}: each quantity's delta beside its LINEAGE_TOL tolerance. Position is [x, y] and
    d the planar distance in tiles; inventory_n is the frame's load.n; ok only when every quantity is."""
    a, b = _last_frame(prev_artifact), _d(first_frame)
    am, bm = _d(a.get("me")), _d(b.get("me"))
    pa = [am.get("x"), am.get("y")] if am else None
    pb = [bm.get("x"), bm.get("y")] if bm else None
    d = None
    if pa and pb and all(_num(v) is not None for v in pa + pb):
        d = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    tol = LINEAGE_TOL
    out = {"position": {"prev": pa, "now": pb, "d": d, "tol": tol["position"],
                        "ok": d is not None and d <= tol["position"] + 1e-12},
           "health": _pair(_d(a.get("body")).get("health"), _d(b.get("body")).get("health"), tol["health"]),
           "stats": {k: _pair(_d(a.get("stats")).get(k), _d(b.get("stats")).get(k), tol["stat"]) for k in STATS},
           "inventory_n": _pair(_d(a.get("load")).get("n"), _d(b.get("load")).get("n"), tol["inventory_n"]),
           "game_min": _pair(a.get("gameMin"), b.get("gameMin"), tol["game_min"])}
    out["ok"] = bool(out["position"]["ok"] and out["health"]["ok"] and all(v["ok"] for v in out["stats"].values())
                     and out["inventory_n"]["ok"] and out["game_min"]["ok"])
    return out


def snapshot_cmd(run_dir, name, parent, session):
    """The argv of `pzt snapshot --from-run <run_dir> --name <name> --parent <parent> --session <n>`."""
    return [sys.executable, PZT, "snapshot", "--from-run", str(run_dir), "--name", str(name), "--parent", str(parent),
            "--session", str(int(session))]
