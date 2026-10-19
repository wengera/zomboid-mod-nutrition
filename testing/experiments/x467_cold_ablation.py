"""x467_cold_ablation -- a derived artifact (Plan 16 Task 9, the live review's F3): x467's THIRST replay with the ring's
cold multiplier fed and not fed, on its committed inputs, never re-run; #3947's discriminating reading.

x461a's own ablation (`checks.cold_ablation`) stayed under the tolerance with the cold near 1.003, so it cannot show the
cold mattered; x452's and x452b's rings carry no `cold`. x467's day (cold 1.00029 to 1.00441) can. This script replays
x467's committed ring (`minute-ring-admin-1/721/1441.json`) from its `start.json`, `start-stats.json`, `player.json`
and `events.json` through x46_lib.replay_grade (tools/replay_live.replay_live, sleep off) twice: ring_cold auto (fed)
and ring_cold False (not fed), each diffed under x45g_lib.REPLAY_TOL (THIRST 0.002), and grades:
  COLD_DISCRIMINATES  with the cold fed, every THIRST row over the tolerance is an auto-drink row (a ring row whose
                      next row books `fluids.autoDrop` above 0: the engine's own write a row before the mod books the
                      sip, which the replay does not model); and with the cold not fed, at least MIN_OFF_GAP more rows
                      fall over. Unmeasured with no rows.
The counts (`over`, `n`, the over rows' s) of both arms are the readings.

`python testing/experiments/x467_cold_ablation.py [--out <dir>]`; the default output is
testing/artifacts/x467-cold-ablation-20261019/ablation.json. Frozen once its output is committed (CLAUDE.md s5).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
RUN = "x467-20261019-025016"
OUT = os.path.join(REPO, "testing", "artifacts", "x467-cold-ablation-20261019")
MIN_OFF_GAP = 50                         # rows: x452b's cold-blind drift fell over on 407 rows


def autodrink_rows(rows):
    """The s of every ring row whose next row books fluids.autoDrop above 0."""
    out = []
    for a, b in zip(rows, rows[1:]):
        v = b.get("fluids.autoDrop")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 and a.get("s") is not None:
            out.append(a["s"])
    return out


def over_rows(diff, field="THIRST"):
    return sorted(f["s"] for f in (diff or {}).get("findings") or [] if f.get("field") == field and "s" in f)


def grade(on_over, off_over, auto, n):
    o = {"on_over": len(on_over), "off_over": len(off_over), "n": n, "on_over_s": on_over[:20],
         "off_first_s": off_over[:5], "autodrink_s": auto, "min_off_gap": MIN_OFF_GAP}
    if not n:
        return "unmeasured", dict(o, why="no graded rows")
    stray = [s for s in on_over if s not in set(auto)]
    o["on_over_not_autodrink"] = stray
    ok = not stray and len(off_over) - len(on_over) >= MIN_OFF_GAP
    return ("as_predicted" if ok else "falsified"), o


def main(argv):
    import x46_lib as L
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT
    art = os.path.join(REPO, "testing", "artifacts", RUN)
    raw = open(os.path.join(art, "day.json"), "rb").read()
    d = json.loads(raw.decode("utf-8"))
    pages = d["model_inputs"]["ring"]
    rows = {}
    for f in pages:
        for r in json.load(open(os.path.join(art, f), encoding="utf-8"))["rows_list"]:
            rows[r["s"]] = r
    rows = [rows[s] for s in sorted(rows)]
    start = json.load(open(os.path.join(art, "start.json"), encoding="utf-8"))
    stats = json.load(open(os.path.join(art, "start-stats.json"), encoding="utf-8"))
    player = json.load(open(os.path.join(art, "player.json"), encoding="utf-8"))
    events = json.load(open(os.path.join(art, "events.json"), encoding="utf-8"))
    tol = {"THIRST": L.G.REPLAY_TOL["THIRST"]}
    arms = {}
    for name, rc in (("cold_fed", None), ("cold_not_fed", False)):
        _, diff, _ = L.replay_grade(rows, events, start, tol, paths=list(L.RING46["x467"]), player=player,
                                    start_stats=stats, ring_cold=rc)
        arms[name] = {"fields": diff.get("fields"), "over_s": over_rows(diff), "classes": diff.get("classes")}
    auto = autodrink_rows(rows)
    n = (arms["cold_fed"]["fields"] or {}).get("THIRST", {}).get("n")
    v, o = grade(arms["cold_fed"]["over_s"], arms["cold_not_fed"]["over_s"], auto, n)
    res = {"verdicts": {"COLD_DISCRIMINATES": {"verdict": v, "observed": o,
                                               "falsifier": "a cold-fed THIRST row over the tolerance that is not an "
                                                            "auto-drink row, or no gain from the cold"}},
           "arms": arms, "source": f"testing/artifacts/{RUN}/day.json", "source_sha256": hashlib.sha256(raw).hexdigest(),
           "pages": pages, "tol": {k: list(t) for k, t in tol.items()},
           "script": "testing/experiments/x467_cold_ablation.py", "kind": "derived artifact (analysis, not a live run)"}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "ablation.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    print(json.dumps({"verdict": v, "on_over": o["on_over"], "off_over": o["off_over"], "n": n}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
