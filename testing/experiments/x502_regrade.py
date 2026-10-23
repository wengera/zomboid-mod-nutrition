"""x502_regrade -- a derived artifact (Plan 19 Task 7 write-up): x502's REPLAY_moodLast.u graded again against the
replay's own placement resolution, its committed inputs re-read, never re-run.

x502's frozen grade (x50_lib.Floor.grade_replay) places each landed eat at the first ring row whose intake `eats`
counter rose (x50_lib.eat_events: an `s` event, applied at that row's age), and holds moodLast.u to 1e-3 of the HEAD
replay. The live eat landed somewhere inside the minute before that row: after row s-1 sampled the counter, at or before
row s did. The minute ring does not log the landing age. monotony's portion count decays with HALF_LIFE_H 72 game h
(K.monotony.count), so the count, and with it the composed target moodLast.u, depends on each eat's age inside its
minute: a target of SLOPE x (n - 1) moves by about SLOPE x n x ln2 / 72 x (1/60) = 0.0021 for n = 3.15 over one game
minute at DayLength 4's ring spacing. The 1e-3 tolerance is under that resolution. hedonics.f (the plain-energy floor)
reads the ring's hourly slots, which a placement inside the minute does not move.

This script runs tools/replay_live.py (unchanged since 212e89f2, the run's replay_tool_commit) on x502's committed
inputs three times:
  frozen  the committed events.json as the driver placed them (reproduces the run's replay.json diff);
  early   each eat at the age of the ring row before its landing row plus EPS_H (the earliest admissible landing);
  late    each eat at its landing row's age (the frozen placement, written as an `age` event);
and a fourth, `mid`, each eat half-way through its minute, as a reading beside the grade.

The grade, stated before this script's first run: REPLAY_moodLast.u_band is as_predicted when every ring row the frozen
diff graded (not `between`, `offline` or `suspect`) reads a live moodLast.u inside [min(early, late) - 1e-3,
max(early, late) + 1e-3], and hedonics.f within 1e-4 of both the early and the late replay; falsified when any graded
row lies outside; unmeasured when a replay raises or no row is graded. A live value inside the band is the mod's
arithmetic at some landing age inside the minute; one outside it is a defect the placement cannot explain.

`python testing/experiments/x502_regrade.py [--out <dir>]`; the default output is
testing/artifacts/x502-regrade-20261022/regrade.json. It refuses any other argument. Frozen once its output is
committed (CLAUDE.md s5).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)

RUN = "x502-20261022-223712"
SRC = os.path.join(REPO, "testing", "artifacts", RUN)
OUT = os.path.join(REPO, "testing", "artifacts", "x502-regrade-20261022")
FILES = ("floor.json", "minute-ring-admin-1.json", "events.json", "start.json", "start-stats.json", "player.json",
         "replay.json")
EPS_H = 1e-6                             # the earliest placement: just after the row before the landing row
TOL_U = 1e-3                             # x50_lib.REPLAY_TOL["moodLast.u"], unchanged
TOL_F = 1e-4                             # x50_lib.REPLAY_TOL["hedonics.f"], unchanged


def num(v):
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as fh:
        return json.load(fh)


def placed(events, ages, frac):
    """Each s-keyed eat moved to an age inside its landing minute: frac 0 the row before (+EPS_H), 1 the row itself."""
    out = []
    for e in events:
        e = dict(e)
        s = e.pop("s")
        a0, a1 = ages[s - 1], ages[s]
        e["age"] = a1 if frac >= 1 else a0 + EPS_H + frac * (a1 - a0 - EPS_H)
        e["placed_from_s"] = s
        out.append(e)
    return out


def replay(RL, L, rows, events, start, player, start_stats, inputs):
    rep, _ = RL.replay_live(rows, events, start, paths=list(L.RING_502), user=L.USER, player=player,
                            start_stats=start_stats, sleep_allowed=inputs["sleep_allowed"],
                            death_pace=inputs["death_pace"], health_combine=inputs["health_combine"],
                            day_minutes=inputs["day_minutes"], game_heal=True)
    return rep, RL.diff(rep, rows, L.REPLAY_TOL)


def grade_band(rows, reps, diff_frozen):
    """The band grade over the rows the frozen diff graded (see the docstring)."""
    live = {r["s"]: r for r in rows}
    by = {k: {r["s"]: r for r in v} for k, v in reps.items()}
    skip = set(diff_frozen.get("skipped") or []) | set(diff_frozen.get("offline") or []) | \
        set(diff_frozen.get("suspect") or [])
    out, off, n = [], [], 0
    for r in reps["late"]:
        s = r["s"]
        if s in skip or s not in live:
            continue
        lu, lf = num(live[s].get("moodLast.u")), num(live[s].get("hedonics.f"))
        eu, uu = num(by["early"].get(s, {}).get("moodLast.u")), num(by["late"].get(s, {}).get("moodLast.u"))
        ef, uf = num(by["early"].get(s, {}).get("hedonics.f")), num(by["late"].get(s, {}).get("hedonics.f"))
        mu = num(by["mid"].get(s, {}).get("moodLast.u"))
        if None in (lu, eu, uu):
            continue
        n += 1
        lo, hi = min(eu, uu) - TOL_U, max(eu, uu) + TOL_U
        ok_u = lo <= lu <= hi
        ok_f = lf is None or (ef is not None and uf is not None and abs(lf - ef) <= TOL_F and abs(lf - uf) <= TOL_F)
        row = {"s": s, "live": lu, "early": eu, "late": uu, "mid": mu, "width": abs(uu - eu),
               "d_late": abs(lu - uu), "d_mid": None if mu is None else abs(lu - mu), "in_band": ok_u, "f_ok": ok_f}
        out.append(row)
        if not (ok_u and ok_f):
            off.append(s)
    if n == 0:
        return "unmeasured", {"why": "no graded row", "rows": out}
    return ("as_predicted" if not off else "falsified"), {"n": n, "off": off, "rows": out,
                                                        "max_width": max(x["width"] for x in out),
                                                        "max_d_late": max(x["d_late"] for x in out),
                                                        "max_d_mid": max(x["d_mid"] for x in out if x["d_mid"] is not None)}


def main(argv):
    out = OUT
    rest = list(argv)
    if rest[:1] == ["--out"] and len(rest) == 2:
        out = rest[1]
    elif rest:
        raise SystemExit("x502_regrade: unknown arguments %r (only --out <dir>)" % (rest,))
    import replay_live as RL
    import x50_lib as L
    sha = {}
    for f in FILES:
        with open(os.path.join(SRC, f), "rb") as fh:
            sha[f] = hashlib.sha256(fh.read()).hexdigest()
    run = load("floor.json")
    inputs = run["model_inputs"]
    rows = load("minute-ring-admin-1.json")["rows_list"]
    events, start = load("events.json"), load("start.json")
    player, start_stats = load("player.json"), load("start-stats.json")
    ages = {r["s"]: r["age"] for r in rows}
    res = {"script": "testing/experiments/x502_regrade.py", "kind": "derived artifact (analysis, not a live run)",
           "run": RUN, "source_sha256": sha, "tol": {"moodLast.u": TOL_U, "hedonics.f": TOL_F}, "eps_h": EPS_H,
           "frozen_verdict": run["verdicts"]["REPLAY_moodLast.u"]["verdict"], "arms": {}}
    reps, diffs = {}, {}
    try:
        for name, evs in (("frozen", events), ("early", placed(events, ages, 0.0)), ("late", placed(events, ages, 1.0)),
                          ("mid", placed(events, ages, 0.5))):
            reps[name], diffs[name] = replay(RL, L, rows, evs, start, player, start_stats, inputs)
            res["arms"][name] = {"fields": diffs[name]["fields"], "findings_n": len(diffs[name].get("findings") or []),
                                 "events": [{k: e.get(k) for k in ("label", "s", "age", "placed_from_s")}
                                            for e in evs]}
    except Exception as e:                       # noqa: BLE001 - recorded, graded unmeasured
        res["error"] = f"{type(e).__name__}: {e}"
        res["verdict"], res["observed"] = "unmeasured", {"why": "a replay raised"}
    else:
        committed = load("replay.json")["diff"]["fields"]
        res["frozen_reproduces_committed"] = diffs["frozen"]["fields"] == committed
        res["verdict"], res["observed"] = grade_band(rows, reps, diffs["frozen"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    o = res.get("observed") or {}
    print(json.dumps({"verdict": res["verdict"], "frozen_reproduces_committed": res.get("frozen_reproduces_committed"),
                      "n": o.get("n"), "off": o.get("off"), "max_width": o.get("max_width"),
                      "max_d_late": o.get("max_d_late"), "max_d_mid": o.get("max_d_mid"),
                      "arms": {k: v["fields"] for k, v in res["arms"].items()}}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
