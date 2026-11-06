#!/usr/bin/env python3
"""The tactician's offline bench (Plan 31 Task 11, variant T; the amendments' item 2, the proposal § 5 and § 7): does
the model add anything tactically over a cached table of Angus's rules?

    python tools/tactician_bench.py views            # build the 200 trigger views from the rings, print their mix
    python tools/tactician_bench.py record [--max-calls N] [--dry]   # the real `claude -p` calls, cached and resumed
    python tools/tactician_bench.py score [--write-table]            # the verdict, from the recorded answers
    python tools/tactician_bench.py check                            # read-only: the recorded scores and table hold

THE VIEWS (deterministic; no clock, no model). The rings are the committed artifacts of F2 to F15 and E19 to E23
(RINGS: `f_goals_2`, `f_goals_4` to `f_goals_16`, `e_day_19` to `e_day_23`; F1 is `f_goals`, F3 `f_goals_4`, the
F-number one less than the driver's from F3 on). Each ring's `state.log` is decoded as live
(`replay_decisions.read_record`: `FileTransport`, the delta frames merged) into a fresh World, every frame stepped
through the tactician's own triggers (`tactician.trigger.Triggers(banded=False)`, the frame's `wallMs` as the clock:
the triggers the recording was made with, `count` on every change of the raw count; the live decider's `count` fires
on a band edge held COUNT_HOLD_S since fix 1, which would choose other frames). Pass 1 keeps
every (ring, frame, triggers) point with a cheap class (the standing count within DANGER_R by band, a standing zombie
within KEEP_R, a bleed); 200 points are chosen round-robin over the classes in sorted order, each class's points taken
evenly spaced over (ring, frame), so the quiet `clear` and `notice` triggers do not drown the fights. Pass 2 replays
again and builds each chosen point's view (`tactician.tview.build`), its `goal` the recorded decision line's goal at or
before the frame's wall (LootBuilding or Shelter: its building's label). A view's `sha` is the sha256 of its sorted
JSON: `score` rebuilds the views and refuses a recording whose shas differ.

THE CHOOSERS:
- `doctrine`: `tactician.fallback.doctrine` (Angus's rules, zero latency).
- `table`: the cached table (`tactician.table`) fitted on the default model's answers with the view's own ring held
  out (leave one ring out: a cell the other rings never labelled answers the doctrine's play); `table_in` the same
  fitted on every view (in sample, the table the live build ships as `table.json`).
- `ladder`: the recorded decision line at or before the frame, mapped onto a play (a threat line with a flee reason
  `kite`, a threat line otherwise `fight`, care `dress`, a goal line `loot`/`travel` by its goal's type, the night
  `shelter`, else none).
- `haiku` and `sonnet` (the default, `llm.DEFAULT_CLI`'s model): real `claude -p` calls through `llm.py`'s argv
  (`tactician.source.cli`), the system prompt `tactician.plays.SYSTEM`, the view rendered (`tview.render`) on stdin.

THE CALLS (`record`): at most CALL_BUDGET (450) in all, counted in the recording, interleaved view by view (haiku
then sonnet, so a stop leaves both configurations equally covered), then SELF_N (25) views asked SELF_K - 1 (2) more
times of the default (self-agreement, k = 3: 25 x 2 = 50 calls, the budget's last 50; the amendments' "k = 3 on 50
views" does not fit its own 450 = 200 + 200 + 50, so the views are halved and k kept). Every call is appended to the
recording as it lands; the run stops at the first call that exits non-zero or reads as a limit (`source.call`'s
`limited`), as the amendments require. A rerun resumes: a (config, view, sample) already recorded is never asked
again.

THE SCORES (`score`): per chooser, the valid share (an answer `plays.validate` passes on its view), the rubric
violations (`tactician.rubric`: `lone_not_fight`, `bleed_not_dress`, `travel_nowhere`; an invalid answer read as no
play), the agreement with each model configuration (the same play type; and the same type and target on the tactical
plays `fight`, `kite`, `avoid`, `dress`, the strategic plays' buildings being the goal layer's choice either way), and
for the models the latency p50, p95 and p99 (wall seconds, the process start included) and the self-agreement. The
verdict: the table ties the model when its type agreement with the default model is at least TIE_SHARE (0.95) of the
views both answered validly and its violations are no more than the model's; then T's trials run the table and the
model stays strategic (the amendments' item 2). `--write-table` writes the in-sample table to
`testing/agent/base/planner/tactician/table.json`.

The recording: `data/fits/tactician-bench.json` (`{meta, views: [{id, ring, frame, wall, trigger, cls, sha}], calls:
[{config, view, k, answer, text, latency_s, error, limited, returncode}], scores}`), committed so the bench is
deterministic afterwards: no test and no `score` makes a call.
"""
import argparse
import bisect
import hashlib
import json
import math
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "testing") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "testing"))

from agent.base.planner.policies import DANGER_R, KEEP_R, on_floor, zdist  # noqa: E402
from agent.base.planner.tactician import fallback as F  # noqa: E402
from agent.base.planner.tactician import plays as P  # noqa: E402
from agent.base.planner.tactician import rubric as R  # noqa: E402
from agent.base.planner.tactician import source as S  # noqa: E402
from agent.base.planner.tactician import table as T  # noqa: E402
from agent.base.planner.tactician import tview as V  # noqa: E402
from agent.base.planner.tactician.trigger import Triggers  # noqa: E402
from agent.base.replay_decisions import read_record  # noqa: E402
from agent.base.world import World  # noqa: E402

ARTIFACTS = os.path.join(REPO, "testing", "artifacts")
RECORDING = os.path.join(REPO, "data", "fits", "tactician-bench.json")
RINGS = ("f_goals_2-20261029-041705", "f_goals_4-20261030-114742", "f_goals_5-20261030-180527",
         "f_goals_6-20261030-192251", "f_goals_7-20261031-000629", "f_goals_8-20261102-093241",
         "f_goals_9-20261102-181937", "f_goals_10-20261102-231705", "f_goals_11-20261103-075140",
         "f_goals_12-20261103-144240", "f_goals_13-20261104-203950", "f_goals_14-20261105-021722",
         "f_goals_15-20261105-092752", "f_goals_16-20261105-164332", "e_day_19-20261103-072904",
         "e_day_20-20261103-121340", "e_day_21-20261104-201749", "e_day_22-20261105-004919",
         "e_day_23-20261105-095110")   # F2..F15 (f_goals_2, f_goals_4..f_goals_16), E19..E23
VIEWS_N = 200          # the amendments' 200 recorded trigger views
CONFIGS = ("haiku", "sonnet")   # `--model haiku`, and the default (llm.DEFAULT_CLI's sonnet)
REFERENCE = "sonnet"   # the default configuration: the table's labels and the verdict's model
CALL_BUDGET = 450      # the amendments' cap on real calls in all
SELF_N = 25            # views asked again for the self-agreement (see THE CALLS)
SELF_K = 3             # samples per such view, the first the main pass's
TIE_SHARE = 0.95       # the table ties the model at this type agreement or more (the amendments' item 2)
TACTICAL = P.TACTICAL


# ---------------------------------------------------------------- the views
def _cls(world):
    """The cheap class of a frame (THE VIEWS): (standing band within DANGER_R, a standing zombie within KEEP_R, a
    bleed)."""
    s = [zdist(world, z) for z in world.zombies.values() if z.get("x") is not None and z.get("y") is not None
         and not on_floor(z)]
    n6 = sum(1 for d in s if d <= DANGER_R)
    keep = any(d <= KEEP_R for d in s)
    parts = (world.body or {}).get("parts")
    bleed = isinstance(parts, list) and any(isinstance(p, dict) and p.get("bleeding") is True for p in parts)
    return "s%s|k%d|b%d" % (min(n6, 3), keep, bleed)


def _replay(ring, want=None):
    """Pass 1 (`want` None): [(frame index, wall, triggers, cls)] of every trigger point of `ring`; pass 2: {frame
    index: view} for the frame indexes in `want`."""
    lines, rows = read_record(os.path.join(ARTIFACTS, ring))
    walls = [r["wall"] for r in rows]
    w, trig = World(), Triggers(banded=False)   # the recording's triggers (fix 1 banded the live ones: trigger.py)
    pts, views, fi = [], {}, -1
    for ln in lines:
        w.apply(ln)
        if ln["kind"] != "frame":
            continue
        fi += 1
        now = ln["wallMs"] / 1000.0
        fired = trig.step(w, now)
        if not fired:
            continue
        if want is None:
            pts.append((fi, now, fired, _cls(w)))
        elif fi in want:
            k = bisect.bisect_right(walls, now) - 1
            row = rows[k] if k >= 0 else None
            views[fi] = V.build(w, trig, {"trigger": fired[0], "goal": _goal(row)})
    return pts if want is None else (views, rows, walls)


def _goal(row):
    """The recorded decision line's strategic goal as the view's `goal` ({type, building}), else None."""
    g = (row or {}).get("goal") or {}
    if not isinstance(g, dict) or "type" not in g:
        return None
    b = (g.get("args") or {}).get("building")
    return {"type": g["type"], "building": "B%d" % b if isinstance(b, int) and not isinstance(b, bool) else None}


def choose(points, n=VIEWS_N):
    """`n` points round-robin over the classes in sorted order, each class's taken evenly spaced over (ring, frame)
    (THE VIEWS); returns them sorted by (ring order, frame)."""
    by = {}
    for p in points:
        by.setdefault(p["cls"], []).append(p)
    classes = sorted(by)
    quota = {c: 0 for c in classes}
    left, active = n, [c for c in classes]
    while left > 0 and active:
        for c in list(active):
            if left == 0:
                break
            if quota[c] < len(by[c]):
                quota[c] += 1
                left -= 1
            else:
                active.remove(c)
    out = []
    for c in classes:
        pts, q = by[c], quota[c]
        if q == 0:
            continue
        step = len(pts) / q
        out += [pts[int(math.floor(i * step + step / 2))] for i in range(q)]
    order = {r: i for i, r in enumerate(RINGS)}
    return sorted(out, key=lambda p: (order[p["ring"]], p["frame"]))


def sha(view):
    return hashlib.sha256(json.dumps(view, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_views(rings=RINGS, n=VIEWS_N, log=print):
    """[(record {id, ring, frame, wall, trigger, cls, sha}, view, ladder play or None)] of the chosen points."""
    points = []
    for ring in rings:
        t0 = time.time()
        pts = _replay(ring)
        points += [{"ring": ring, "frame": fi, "wall": now, "triggers": fired, "cls": cls}
                   for fi, now, fired, cls in pts]
        log("%s: %d trigger points (%.1f s)" % (ring, len(pts), time.time() - t0))
    chosen = choose(points, n)
    out = []
    for ring in rings:
        mine = [p for p in chosen if p["ring"] == ring]
        if not mine:
            continue
        views, rows, walls = _replay(ring, {p["frame"] for p in mine})
        for p in mine:
            v = views[p["frame"]]
            k = bisect.bisect_right(walls, p["wall"]) - 1
            out.append(({"id": "%s#%d" % (ring.split("-")[0], p["frame"]), "ring": ring, "frame": p["frame"],
                         "wall": p["wall"], "trigger": p["triggers"], "cls": p["cls"], "sha": sha(v)}, v,
                        ladder_play(rows[k] if k >= 0 else None)))
    return out, points


def ladder_play(row):
    """The recorded ladder line mapped onto a play type (THE CHOOSERS' `ladder`), else None."""
    if not row:
        return None
    b = row.get("branch")
    why = ((row.get("inputs") or {}).get("branches") or {}).get(b) or {}
    if b == "threat":
        return "kite" if why.get("flee") else "fight"
    if b == "care":
        return "dress"
    if b == "night":
        return "shelter"
    if b == "goal":
        g = (row.get("goal") or {}).get("type")
        return {"LootBuilding": "loot", "Stock": "loot", "Shelter": "shelter"}.get(g, "travel")
    return None


# ---------------------------------------------------------------- the recording
def load(path=RECORDING):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(rec, path=RECORDING):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def plan_calls(views, rec_calls):
    """The (config, view id, k) still to ask, in THE CALLS order."""
    done = {(c["config"], c["view"], c["k"]) for c in rec_calls}
    main = [(cfg, v["id"], 0) for v, _, _ in views for cfg in CONFIGS]
    step = max(1, len(views) // SELF_N)
    selfs = [(REFERENCE, views[i][0]["id"], k) for i in range(0, len(views), step)[:SELF_N] for k in range(1, SELF_K)]
    return [c for c in main + selfs if c not in done]


def record(max_calls=CALL_BUDGET, dry=False, runner=None, path=RECORDING, log=print, views=None):
    """THE CALLS (the module docstring); returns the recording. `views` the built views (`build_views`), else built
    from the rings."""
    if views is None:
        views, _ = build_views(log=log)
    rec = load(path) or {}
    if rec.get("views") and [v["sha"] for v in rec["views"]] != [v["sha"] for v, _, _ in views]:
        raise SystemExit("the recording's views differ from the rings' (sha): refusing to mix them")
    rec.setdefault("calls", [])
    rec["views"] = [v for v, _, _ in views]
    rec["meta"] = dict(rec.get("meta") or {}, rings=list(RINGS), configs=list(CONFIGS), reference=REFERENCE,
                       budget=CALL_BUDGET, self_n=SELF_N, self_k=SELF_K, system_sha=hashlib.sha256(
                           P.SYSTEM.encode("utf-8")).hexdigest())
    todo = plan_calls(views, rec["calls"])
    room = min(max_calls, CALL_BUDGET - len(rec["calls"]))
    log("%d calls recorded, %d to make, room %d" % (len(rec["calls"]), len(todo), room))
    if dry:
        return rec
    by_id = {v["id"]: view for v, view, _ in views}
    argv = {cfg: S.cli(cfg) for cfg in CONFIGS}
    for cfg, vid, k in todo[:max(0, room)]:
        out = S.call(argv[cfg], V.render(by_id[vid]), runner or S.run, S.TACTIC_TIMEOUT_S * 4)
        rec["calls"].append({"config": cfg, "view": vid, "k": k, "answer": out["answer"], "text": out["text"],
                             "latency_s": out["latency_s"], "error": out["error"], "limited": out["limited"],
                             "returncode": out["returncode"], "stderr": out["stderr"]})
        save(rec, path)
        log("%d/%d %s %s k%d %.2fs %s %s" % (len(rec["calls"]), CALL_BUDGET, cfg, vid, k, out["latency_s"] or 0,
                                              out["error"], json.dumps(out["answer"])[:120]))
        if out["limited"] or str(out["error"]).startswith(("exit", "spawn")):
            log("STOP: %s (exit %s)" % (out["error"], out["returncode"]))
            break
    return rec


# ---------------------------------------------------------------- the scores
def _valid(ans, view):
    if ans is None:
        return None
    try:
        return P.validate(ans, view).row()
    except P.Refused:
        return None


def _same(a, b, target=True):
    if a is None or b is None or a.get("play") != b.get("play"):
        return False
    if not target or a["play"] not in TACTICAL:
        return True
    return P.Play(a["play"], {k: a[k] for k in P.ARGS[a["play"]]}).target() == P.Play(
        b["play"], {k: b[k] for k in P.ARGS[b["play"]]}).target()


def _pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)]


def score(rec, views, write_table=False):
    """THE SCORES (the module docstring): `{choosers: {name: {...}}, verdict, ...}`."""
    by_id = {v["id"]: (view, lad) for v, view, lad in views}
    shas = {v["id"]: v["sha"] for v, _, _ in views}
    if any(shas.get(v["id"]) != v["sha"] for v in rec.get("views") or ()):
        raise SystemExit("the recording's views differ from the rings' (sha)")
    ids = [v["id"] for v, _, _ in views]
    ring_of = {v["id"]: v["ring"] for v, _, _ in views}
    calls = rec.get("calls") or []
    model = {cfg: {} for cfg in CONFIGS}
    selfs, lat = {}, {cfg: [] for cfg in CONFIGS}
    for c in calls:
        if c["view"] not in by_id:
            continue
        if c.get("latency_s") is not None and c.get("error") in (None, "malformed"):
            lat[c["config"]].append(c["latency_s"])
        ans = _valid(c.get("answer"), by_id[c["view"]][0])
        if c["k"] == 0:
            model[c["config"]][c["view"]] = {"raw": c.get("answer"), "ans": ans, "error": c.get("error")}
        else:
            selfs.setdefault(c["view"], []).append(ans)
    ref = model[REFERENCE]
    answers = {"doctrine": {}, "table": {}, "table_in": {}, "ladder": {}}
    rows_all = [(by_id[i][0], ref[i]["ans"]) for i in ids if i in ref]
    tin = T.Table.fit(rows_all)
    for i in ids:
        view, lad = by_id[i]
        answers["doctrine"][i] = F.doctrine(view)[1]
        loo = T.Table.fit([(by_id[j][0], ref[j]["ans"]) for j in ids if j in ref and ring_of[j] != ring_of[i]])
        answers["table"][i] = loo.answer(view)[2]
        answers["table_in"][i] = tin.answer(view)[2]
        answers["ladder"][i] = {"play": lad} if lad is not None else None
    for cfg in CONFIGS:
        answers[cfg] = {i: model[cfg][i]["ans"] for i in ids if i in model[cfg]}
    out = {"n_views": len(ids), "calls": len(calls), "calls_by_config": {cfg: sum(1 for c in calls if c["config"] == cfg)
                                                                          for cfg in CONFIGS}, "choosers": {}}
    for name, got in answers.items():
        asked = [i for i in ids if i in got] if name in CONFIGS else ids
        valid = [i for i in asked if got.get(i) is not None]
        viol = {r: 0 for r in R.RULES}
        for i in asked:
            for r in R.violations(by_id[i][0], got.get(i) if name != "ladder" else (got.get(i) or None)):
                viol[r] += 1
        row = {"asked": len(asked), "valid": len(valid), "valid_share": _r(len(valid) / len(asked)) if asked else None,
               "violations": viol, "violations_total": sum(viol.values()),
               "plays": _hist(got.get(i) for i in asked)}
        for cfg in CONFIGS:
            both = [i for i in valid if answers[cfg].get(i) is not None]
            if name == cfg or not both:
                continue
            row["agree_type_%s" % cfg] = _r(sum(_same(got[i], answers[cfg][i], False) for i in both) / len(both))
            if name != "ladder":
                row["agree_target_%s" % cfg] = _r(sum(_same(got[i], answers[cfg][i]) for i in both) / len(both))
            row["agree_n_%s" % cfg] = len(both)
        if name in CONFIGS:
            row.update(latency_p50=_r(_pct(lat[name], 0.50)), latency_p95=_r(_pct(lat[name], 0.95)),
                       latency_p99=_r(_pct(lat[name], 0.99)), latency_n=len(lat[name]),
                       errors=_hist(model[name][i]["error"] for i in asked if model[name][i]["error"]),
                       refused=_hist(_refusal(model[name][i]["raw"], by_id[i][0]) for i in asked
                                     if model[name][i]["ans"] is None and model[name][i]["error"] is None))
        out["choosers"][name] = row
    sa = [(i, [ref[i]["ans"]] + s) for i, s in selfs.items() if i in ref]
    full = [(i, xs) for i, xs in sa if len(xs) == SELF_K]
    out["self_agreement"] = {"views": len(full), "k": SELF_K,
                             "all_same_type": _r(sum(all(_same(x, xs[0], False) for x in xs) and xs[0] is not None
                                                     for _, xs in full) / len(full)) if full else None,
                             "all_same_target": _r(sum(all(_same(x, xs[0]) for x in xs) and xs[0] is not None
                                                       for _, xs in full) / len(full)) if full else None,
                             "pairwise_type": _r(_pairwise(full)) if full else None,
                             "first_two_type": _r(sum(_same(xs[0], xs[1], False) for _, xs in full) / len(full))
                             if full else None}
    out["verdict"] = verdict(out)
    if write_table:
        tin.save(meta={"source": "tools/tactician_bench.py score --write-table", "reference": REFERENCE,
                       "views": len(rows_all), "verdict": out["verdict"]["text"]})
    return out


def _refusal(raw, view):
    try:
        P.validate(raw, view)
    except P.Refused as e:
        return e.why
    return None


def _pairwise(full):
    """The share of sample pairs of a view agreeing on the play type (fix 1, review-t11 L4: like for like with the
    table's pairwise agreement), over every view's SELF_K samples."""
    pairs = [(xs[i], xs[j]) for _, xs in full for i in range(len(xs)) for j in range(i + 1, len(xs))]
    return sum(_same(a, b, False) for a, b in pairs) / len(pairs)


def verdict(out):
    """The table against the reference model (THE SCORES)."""
    ch = out["choosers"]
    t, m = ch.get("table") or {}, ch.get(REFERENCE) or {}
    agree = t.get("agree_type_%s" % REFERENCE)
    if agree is None or not m.get("asked"):
        return {"tie": None, "text": "no model answers recorded: no verdict"}
    tie = agree >= TIE_SHARE and t["violations_total"] <= m["violations_total"]
    text = ("the table ties the model (%.1f %% type agreement, %d violations against %d): T runs the table, the model "
            "stays strategic" if tie else
            "the table does not tie the model under the 95 percent bar (%.1f %% type agreement, %d violations "
            "against %d), and the model's own agreement with itself bounds what any table could reach") % (
        100 * agree, t["violations_total"], m["violations_total"])
    return {"tie": tie, "agree_type": agree, "table_violations": t["violations_total"],
            "model_violations": m["violations_total"], "text": text}


def _hist(xs):
    out = {}
    for x in xs:
        k = x.get("play") if isinstance(x, dict) else (x if x is not None else "none")
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def print_table(sc, log=print):
    cols = ("asked", "valid_share", "violations_total", "agree_type_sonnet", "agree_target_sonnet", "agree_type_haiku",
            "latency_p50", "latency_p95", "latency_p99")
    log("| chooser | " + " | ".join(cols) + " |")
    log("|---" * (len(cols) + 1) + "|")
    for name, row in sc["choosers"].items():
        log("| %s | %s |" % (name, " | ".join(str(row.get(c, "-")) for c in cols)))
    log("violations: " + json.dumps({n: r["violations"] for n, r in sc["choosers"].items()}, sort_keys=True))
    log("self-agreement: " + json.dumps(sc["self_agreement"], sort_keys=True))
    log("verdict: " + sc["verdict"]["text"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("views")
    r = sub.add_parser("record")
    r.add_argument("--max-calls", type=int, default=CALL_BUDGET)
    r.add_argument("--dry", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("--write-table", action="store_true")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    if a.cmd == "views":
        views, points = build_views()
        print("%d points, %d views; classes %s" % (len(points), len(views), json.dumps(
            _hist({"play": v["cls"]} for v, _, _ in views))))
        print("doctrine plays: %s" % json.dumps(_hist(F.doctrine(view)[1] for _, view, _ in views)))
        return 0
    if a.cmd == "record":
        record(a.max_calls, a.dry)
        return 0
    rec = load()
    if rec is None:
        raise SystemExit("no recording at %s: run `record` first" % RECORDING)
    views, _ = build_views(log=lambda *_: None)
    if a.cmd == "check":
        return check(rec, views)
    sc = score(rec, views, a.write_table)
    rec["scores"] = sc
    save(rec)
    print_table(sc)
    return 0


def check(rec, views, log=print, table=None):
    """`check` (fix 1, review-t11 L2): the scores re-read from the recording and the rings, compared with the
    recording's own `scores` and the committed `table.json`; nothing written. 0 when both agree, else 1."""
    sc = score(rec, views, write_table=False)
    same = json.dumps(sc, sort_keys=True) == json.dumps(rec.get("scores"), sort_keys=True)
    fitted = T.Table.fit([(view, _valid(c.get("answer"), view)) for c in rec.get("calls") or ()
                          if c["config"] == REFERENCE and c["k"] == 0
                          for view in [next(v for r, v, _ in views if r["id"] == c["view"])]])
    table_same = fitted.cells == (table if table is not None else T.Table.load()).cells
    print_table(sc, log)
    log("check: scores %s, table.json %s" % ("match" if same else "DIFFER", "matches" if table_same else "DIFFERS"))
    return 0 if same and table_same else 1


if __name__ == "__main__":
    sys.exit(main())
