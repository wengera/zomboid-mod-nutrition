#!/usr/bin/env python3
"""The facing trials' scorecard (Plan 32 Task 2; ruling P31-T: a trial is not evidence, so it is scored by this script
and never written up). It reads a run of `testing/agent/drivers/x_facing.py` into `testing/trials/facing.md`, one row
per `probe` act that ended `done`.

    python tools/facing_score.py <run> [--seen "..."]... [--dry] [--log PATH]
    python tools/facing_score.py --rescore-all [--dry] [--log PATH] [--runs DIR]

Reads one run folder (`testing/runs/<run>/`): `trial.json` (its `commit` and `dirty`, shown as `trial_score.py` shows
them; a missing file prints `-`), every state log under `clients/*/Lua/pzagent/*/` (the `admin` client's first,
`gates_e.session_lines`: the rotations and the live file in seq order) for the act lines of type `probe` and state
`done`, and `decision.log` for the plan: the sequencer's decision line that sent an act carries its `aid`, `mode`,
`move` and `k` (a done line whose aid no decision line names is read from the Nth sent line instead).

The columns (COLUMNS): `run` the run id; `commit` the booted commit; `mode`; `move` (`still` or `back`: the character
standing, or back-pedalling away from the cursor's bearing); `k` (turn_k's turn delta, `-` otherwise); `ticks` (the ring
ticks); `body med` and `body p90` (the median and the 90th percentile of the absolute error of the body angle against
the bearing to the target, degrees, one decimal, as the Lua wrote them); `look med` and `look p90` (the same for the
look angle); `hold30` (the share of the ring ticks whose body error held within 30 degrees, two decimals); `aiming`
(the share of ticks `isAiming` read true, two decimals); `pressed` (`yes` when the mode pressed an attack, else `-`);
`hp0 -> hp1` (the press's health before and after, two decimals, else `-`); `seen` (three lines at most, joined by
` / `, written by the caller). A row's identity is its run, mode, move and k: a rescore replaces it in place, keeping
its `seen`. `--rescore-all` rebuilds every row whose `x_facing-*` folder is under `--runs` (default `$PZT_RUNS`, else
`testing/runs/`), a row whose folder is gone kept as it stands, a folder with no row never added. `--dry` prints and
writes nothing. The log helpers are `trial_score.py`'s (`read_log_parts`, `format_row`, `parse_row`, `write_log`: the
row block ends at the first non-row line, and the lines after it are kept as they stand).
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trial_score as TS  # noqa: E402

LOG = os.path.join(REPO, "testing", "trials", "facing.md")
RUNS = os.environ.get("PZT_RUNS") or os.path.join(REPO, "testing", "runs")
RUN_GLOB = "x_facing-*"
COLUMNS = ("run", "commit", "mode", "move", "k", "ticks", "body med", "body p90", "look med", "look p90", "hold30",
           "aiming", "pressed", "hp0 -> hp1", "seen")
DASH = TS.DASH
SEEN_JOIN = TS.SEEN_JOIN


def _plan(rows):
    """({aid: {mode, move, k}}, [{mode, move, k}] in sent order) off the decision lines that sent a probe."""
    by_aid, ordered = {}, []
    for r in rows:
        act = r.get("action")
        if r.get("branch") == "probe" and isinstance(act, dict) and act.get("type") == "probe" and r.get("mode"):
            p = {"mode": r["mode"], "move": r.get("move") or DASH, "k": r.get("k")}
            ordered.append(p)
            if r.get("aid"):
                by_aid[r["aid"]] = p
    return by_aid, ordered


def score(run):
    """One dict per done probe, in the order the log wrote them: {run_id, trial, mode, move, k, result}."""
    L = TS.load_run(run)
    by_aid, ordered = _plan(L["rows"])
    out, n = [], 0
    for line in L["lines"]:
        if not (isinstance(line, dict) and line.get("kind") == "act" and line.get("type") == "probe"
                and line.get("state") == "done" and isinstance(line.get("result"), dict)):
            continue
        plan = by_aid.get(line.get("aid")) or (ordered[n] if n < len(ordered) else {})
        n += 1
        res = line["result"]
        out.append({"run_id": L["run_id"], "trial": L["trial"], "mode": plan.get("mode") or res.get("mode") or DASH,
                    "move": plan.get("move") or DASH, "k": plan.get("k"), "result": res})
    return out


def _f(v, f):
    return DASH if not isinstance(v, (int, float)) or isinstance(v, bool) else f % v


def _k(k):
    if not isinstance(k, (int, float)) or isinstance(k, bool) or k < 0:
        return DASH
    return "%d" % k if float(k).is_integer() else "%s" % k


def cells(r, seen=""):
    """The row's cells in COLUMNS order."""
    res, press = r["result"], r["result"].get("press")
    hp = DASH
    if isinstance(press, dict) and isinstance(press.get("hp0"), (int, float)) and isinstance(press.get("hp1"), (int, float)):
        hp = "%.2f -> %.2f" % (press["hp0"], press["hp1"])
    return [r["run_id"], TS._commit(r["trial"]), r["mode"], r["move"], _k(r["k"]), _f(res.get("ticks"), "%d"),
            _f(res.get("err_body_med"), "%.1f"), _f(res.get("err_body_p90"), "%.1f"),
            _f(res.get("err_look_med"), "%.1f"), _f(res.get("err_look_p90"), "%.1f"), _f(res.get("hold30"), "%.2f"),
            _f(res.get("aiming_share"), "%.2f"), "yes" if res.get("pressed") else DASH, hp, seen or ""]


def row_id(cs):
    """(run, mode, move, k): a row's identity."""
    return (cs[0], cs[2], cs[3], cs[4])


def _identity(line):
    p = TS.parse_row(line)
    return row_id(p) if p and len(p) == len(COLUMNS) else None


def put_rows(path, new, keep_seen=True):
    """The rows `new` (cell lists) written into the log at `path`: each in place of the row with its identity (that
    row's `seen` kept when the new one has none and `keep_seen`), else appended; the row lines written."""
    head, rows, tail = TS.read_log_parts(path)
    wrote = []
    for cs in new:
        for i, ln in enumerate(rows):
            if _identity(ln) == row_id(cs):
                if keep_seen and not cs[-1]:
                    cs = cs[:-1] + [TS.parse_row(ln)[-1]]
                rows[i] = TS.format_row(cs)
                break
        else:
            rows.append(TS.format_row(cs))
        wrote.append(TS.format_row(cs))
    TS.write_log(path, head, rows, tail)
    return wrote


def rescore_all(log, runs, dry=False):
    """The log's rows rebuilt from the run folders `x_facing-*` under `runs`: each row whose folder is there rescored
    keeping its `seen`, a row whose folder is gone (or that the rescore no longer yields) kept as it stands, a folder
    with no row left out; the rows."""
    head, rows, tail = TS.read_log_parts(log)
    seen = {}
    for ln in rows:
        i = _identity(ln)
        if i:
            seen[i] = TS.parse_row(ln)[-1]
    held = {i[0] for i in seen}
    fresh = {}
    for d in sorted(d for d in glob.glob(os.path.join(runs, RUN_GLOB)) if os.path.isdir(d)):
        if os.path.basename(d) not in held:
            continue                                    # a folder with no row: not the log's
        for r in score(d):
            cs = cells(r)
            if row_id(cs) in seen:
                fresh[row_id(cs)] = TS.format_row(cells(r, seen[row_id(cs)]))
    out = [fresh.get(_identity(ln), ln) for ln in rows]
    if not dry:
        TS.write_log(log, head, out, tail)
    return out


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="facing_score.py", allow_abbrev=False,
                                 description="Score a facing trial's run folder into testing/trials/facing.md.")
    ap.add_argument("run", nargs="?", help="the run folder")
    ap.add_argument("--seen", action="append", default=[], help="a line of what was seen (up to three)")
    ap.add_argument("--rescore-all", action="store_true", help="rescore every row whose x_facing-* folder is under --runs")
    ap.add_argument("--dry", action="store_true", help="print, write nothing")
    ap.add_argument("--log", default=LOG, help="the facing log (default testing/trials/facing.md)")
    ap.add_argument("--runs", default=RUNS, help="the run folders' root for --rescore-all")
    a = ap.parse_args(argv)
    if (a.run is None) == (not a.rescore_all):
        ap.error("give one run folder, or --rescore-all")
    if a.rescore_all and a.seen:
        ap.error("--seen names one run's rows; --rescore-all keeps every row's own")
    if len(a.seen) > 3:
        ap.error("--seen at most three times")
    return a


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if a.rescore_all:
            for ln in rescore_all(a.log, a.runs, a.dry):
                print(ln)
            return 0
        seen = SEEN_JOIN.join(x.strip() for x in a.seen)
        rows = [cells(r, seen) for r in score(a.run)]
        if a.dry:
            for cs in rows:
                print(TS.format_row(cs))
        else:
            for ln in put_rows(a.log, rows):
                print(ln)
        if not rows:
            print("facing_score: no probe act ended done in %s" % a.run, file=sys.stderr)
        return 0
    except TS.ScoreError as e:
        print("facing_score: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
