#!/usr/bin/env python3
"""The trials' scorecard (Plan 31 Task 7; ruling P31-T: a trial is not evidence, so it is scored by this script and
never written up). The label contract a variant's decision line follows to be scored: it names its choice under
`intent`, `play` or `act` (on the line or in its `inputs`), as a string or a dict whose `kind`, `name` or `type` is
one; a label starting `avoid`, `kite`, `retreat`, `string` or `flee` (RETREAT_LABELS) is a flee or retreat leg; the
other known words (KNOWN_LABELS: `meet`, `finish`, `filter_door`, `strike`, `dress`, `fight`, `door`, `loot`, `travel`,
`stock`, `needs`, `sneak`, `rest`) are counted as seen, and any other label is printed marked `?` in the detail's
label histogram; a `play` or `intent` dict names its target under `target` as a square ([x, y] or {x, y}) or as the id
of a zombie the frame lists, and a target that resolves to neither is counted as unresolved in the detail; a label or
a string target containing `filter`, `door`, `window`, `shelter` or `refuge` (REFUGE_WORDS) names a refuge, which
takes the line's movement out of the `away` minutes. A retreat toward a named refuge counts both as fleeing and, when
its distance falls, as toward a target: both are true of it.

    python tools/trial_score.py <run> [--seen "..."]... [--dry] [--log PATH]
    python tools/trial_score.py --rescore-all [--dry] [--log PATH] [--runs DIR]

Reads one run folder (`testing/runs/<run>/`, or an artifact folder for a test): `trial.json` (the trial driver's:
`variant`, `switches`, `commit`, `dirty`, `fixture`, `minutes`, `waves`, `no_llm`, `started_at`; a missing file, an old
run scored for a test, prints `-` in its cells), the record (the run root's JSON other than `trial.json`), its
`decision.log` and every state log (beside the JSON, else under `clients/*/Lua/pzagent/*/`, the `admin` client's
first). It prints one row of `testing/trials/trials.md` in the log's column order, then one detail line per reading
with its count and its denominator, and writes the row into the log unless `--dry`: a row whose trial id is already in
the table is replaced in place (its `seen` text kept unless `--seen` is given), any other appended. `--seen` fills the
last column, up to three times, the lines joined by ` / `. `--rescore-all` rebuilds every row from the run folders
named `x_trial-*` under `--runs` (default `$PZT_RUNS`, else `testing/runs/`), keeping each row's `seen` text, a row
whose folder is gone on this machine kept as it stands, a new folder's row appended in name order.

The readers are imported live from the grades (the scorecard is not a frozen grade and no artifact carries its output,
P31-T): `gates_e.session_lines` (the state lines of every rotation), `gates_e._Lines` (the decision lines with the frame
at or before each line's wall, by the wall-time bisect `gates_e._frame_at`; `replay_decisions.align` refuses a log
whose two frames share a line's hour, F15's write-up), `grades.e21.e_kills_matched` (the kills read whole and the
`zombie_dead` events matched to a press), `grades.e21.e_hits_union` (the frames' reaction runs and their union with
the reflex's `hit` steps), `grades.e21.e_goal_wait` (`unmoved_near_s`, the standing on a model wait),
`grades.e21.e_standing` (the standing stretches) and `grades.e19._spans` (the melee spans). The four new readings are
`flee_minutes` (with the frame-based `away_minutes` beside it in its cell, and the ladder's `leg_minutes` in its
detail), `toward_minutes`, `dressed` and `melees_superseded`, each documented with its rule.

The clocks: a decision line's game minute is its `inputs.hour` x 60 (a float; the line's `gameMin` is whole minutes,
too coarse for a 2 Hz line), a frame's its `me.hour` x 60, each unwrapped past midnight; a line stands from its own
wall to the next line's (the log's last line stands for nothing). Stdlib plus the agent base; read-only over the run.
"""
import argparse
import bisect
import glob
import json
import math
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "testing") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "testing"))
from agent.base import gates_e as E  # noqa: E402
from agent.base.grades import e18 as G18  # noqa: E402
from agent.base.grades import e19 as G19  # noqa: E402
from agent.base.grades import e21 as G21  # noqa: E402

LOG = os.path.join(REPO, "testing", "trials", "trials.md")
RUNS = os.environ.get("PZT_RUNS") or os.path.join(REPO, "testing", "runs")
RUN_GLOB = "x_trial-*"
TRIAL_JSON = "trial.json"
DECISION_LOG = "decision.log"
COLUMNS = ("trial", "variant", "commit", "fixture", "min", "kills", "hits (runs / union)", "hits per kill",
           "min fleeing", "min toward target", "dressed <1 min", "melees superseded", "end", "health", "seen")
DASH = "-"
SEEN_JOIN = " / "
# The readings' own numbers.
RETREAT_LABELS = ("avoid", "kite", "retreat", "string", "flee")   # a label starting with one is a retreat (T's
                                                # `string` is a kite: the spec's section 4 item 1)
KNOWN_LABELS = ("meet", "finish", "filter_door", "strike", "dress", "fight", "door", "loot", "travel", "stock", "needs",
                "sneak", "rest")                # the spec's other words (D's intents, U's acts, T's plays): no `?`
LABEL_KEYS = ("intent", "play", "act")          # the line's (or its inputs') keys a variant names its choice under
REFUGE_WORDS = ("filter", "door", "window", "shelter", "refuge")   # a label or target naming one names a refuge
LEGS = ("pull", "back")                         # the ladder's fight legs walking off a zombie, printed in the detail
MOVE_EPS = 0.05        # tiles: a fall in the distance to the target this small is drift, not movement (a 2 Hz line
                       # of the slowest walk, the sneak's, covers several times it)
DRESS_MIN = 1.0        # game minutes: a bleed stopped this soon after its first bleeding frame is dressed in time
PRESS_STEPS = G21.PRESS_STEPS                   # ("swing", "shove", "stomp", "floor"): the melee's presses
SUPERSEDED = "superseded"                       # the melee's terminal reason when the planner sent another act
CRASH_STOPS = ("error", "bus_dead", "lua_error_storm", "client_end")   # driverlib/session.py STOPS that end a crash
CAP_STOPS = ("day_cap",)


class ScoreError(Exception):
    """A run folder that cannot be read at all (it does not exist)."""


# ---------------------------------------------------------------- the run folder
def _json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def find_record(run):
    """The record's path: the run root's JSON other than trial.json, the one named for the run's key first (the run id
    before its `-YYYYMMDD-HHMMSS`), else the largest; None without one."""
    names = [n for n in os.listdir(run) if n.endswith(".json") and n != TRIAL_JSON]
    if not names:
        return None
    key = re.sub(r"-\d{8}-\d{6}$", "", os.path.basename(os.path.normpath(run)))
    named = [n for n in names if n == key + ".json"]
    if named:
        return os.path.join(run, named[0])
    return max((os.path.join(run, n) for n in names), key=os.path.getsize)


def _has_state(d):
    try:
        return any(E.STATE_RX.fullmatch(n) for n in os.listdir(d))
    except OSError:
        return False


def find_state_dir(run):
    """The folder holding the run's state logs: the run root (an artifact), else the client tree's (the `admin`
    client's first); None without one."""
    if _has_state(run):
        return run
    found = sorted(d for d in glob.glob(os.path.join(run, "clients", "*", "Lua", "pzagent", "*")) if _has_state(d))
    admin = [d for d in found if os.path.basename(d) == "admin"]
    return (admin or found or [None])[0]


def read_decisions(path):
    """The decision log's rows (a line that is no JSON object dropped); [] without the file."""
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                try:
                    r = json.loads(ln) if ln.strip() else None
                except ValueError:
                    r = None
                if isinstance(r, dict):
                    rows.append(r)
    except OSError:
        return []
    return rows


def load_run(run):
    """{run, run_id, trial, out, rows, lines}: each source empty when its file is missing (trial None, out {})."""
    if not os.path.isdir(run):
        raise ScoreError("no run folder %s" % run)
    rec = find_record(run)
    out = E._d(_json(rec)) if rec else {}
    trial = _json(os.path.join(run, TRIAL_JSON))
    sd = find_state_dir(run)
    lines = E.session_lines(sd)[0] if sd else []
    rid = out.get("run_id") or os.path.basename(os.path.normpath(run))
    return {"run": run, "run_id": rid, "trial": trial if isinstance(trial, dict) else None, "out": out,
            "rows": read_decisions(os.path.join(run, DECISION_LOG)), "lines": lines}


# ---------------------------------------------------------------- the clocks
def _unwrap(mins):
    """Minutes of the day (a None kept) unwrapped past midnight: a fall of more than half a day adds a day."""
    out, off, prev = [], 0.0, None
    for m in mins:
        if m is None:
            out.append(None)
            continue
        if prev is not None and m + off < prev - 720.0:
            off += 1440.0
        out.append(m + off)
        prev = m + off
    return out


def line_minutes(rows):
    """Each decision line's game minute, its `inputs.hour` x 60 unwrapped (None without an hour)."""
    return _unwrap([(lambda h: h * 60.0 if h is not None else None)(E._n(E._d(r.get("inputs")).get("hour")))
                    for r in rows])


def frame_minutes(frames):
    """Each frame's game minute, its `me.hour` x 60 unwrapped, else its `gameMin` (None without either)."""
    def one(f):
        h = E._n(E._d(f.get("me")).get("hour"))
        return h * 60.0 if h is not None else E._n(f.get("gameMin"))
    return _unwrap([one(f) for f in frames])


def _gap(a, b):
    return b - a if a is not None and b is not None and b >= a else 0.0


def log_minutes(rows):
    """The decision log's game minutes, from its first line to its last (0.0 under two lines)."""
    gm = [m for m in line_minutes(rows) if m is not None]
    return gm[-1] - gm[0] if len(gm) > 1 else 0.0


# ---------------------------------------------------------------- the four new readings
def _label(v):
    """A variant's choice as a lower-case string: the value itself, or a dict's `kind`, `name` or `type`."""
    if isinstance(v, dict):
        v = next((v[k] for k in ("kind", "name", "type") if isinstance(v.get(k), str)), None)
    return v.lower() if isinstance(v, str) else None


def _labels(r):
    """The labels of the line's (then its inputs') LABEL_KEYS, in that order (`_label`; an unreadable value none)."""
    return [lab for src in (r, E._d(r.get("inputs"))) for k in LABEL_KEYS for lab in [_label(src.get(k))]
            if lab is not None]


def _retreat_label(r):
    """The first of the line's labels (`_labels`) starting with a RETREAT_LABELS word, else None."""
    return next((lab for lab in _labels(r) if lab.startswith(RETREAT_LABELS)), None)


def mark(lab):
    """The label as the detail's histogram prints it: marked `?` unless it starts with a RETREAT_LABELS or a
    KNOWN_LABELS word (a shape the scorecard does not know, so a variant's unknown word shows on its first trial)."""
    return lab if lab.startswith(RETREAT_LABELS + KNOWN_LABELS) else lab + "?"


def label_histogram(rows):
    """{marked label: lines} of every label the lines carry under LABEL_KEYS (`_labels`, `mark`)."""
    out = {}
    for r in rows:
        for lab in _labels(r):
            out[mark(lab)] = out.get(mark(lab), 0) + 1
    return out


def leg_minutes(rows):
    """{leg: {lines, minutes}} of the ladder's fight legs walking off a zombie (LEGS: `pull`, drawing one from a group
    by walking away, `planner/pull.py`; `back`, the stance's backpedal), off the threat why's `leg`, each line standing
    to the next as `flee_minutes` reads it. Printed in the fleeing detail, never in the cell (the controller's ruling
    on review-t7 M2)."""
    gm = line_minutes(rows)
    out = {leg: {"lines": 0, "minutes": 0.0} for leg in LEGS}
    for i, r in enumerate(rows):
        leg = E._bw(r, "threat").get("leg")
        if leg not in out:
            continue
        out[leg]["lines"] += 1
        if i + 1 < len(rows):
            out[leg]["minutes"] += _gap(gm[i], gm[i + 1])
    return out


def flee_minutes(rows):
    """The minutes fleeing or retreating: {lines, minutes, seconds, total_minutes, by}. A line is a flee or retreat
    leg when the ladder's threat why `inputs.branches.threat.flee` is set (its flee reason, the field
    `driverlib/session.py` `Fights.feed` counts) or, from a variant, a label of the line's or its inputs' `intent`,
    `play` or `act` (a string, or a dict's `kind`, `name` or `type`) starts with a RETREAT_LABELS word (`avoid`,
    `kite`, `retreat`, `string`, `flee`); each such line stands from its own game minute to the next line's
    (`line_minutes`) and from its wall to the next line's wall. `by` the lines by flee reason or label;
    `total_minutes` the log's (`log_minutes`), the denominator."""
    gm = line_minutes(rows)
    n, mins, secs, by = 0, 0.0, 0.0, {}
    for i, r in enumerate(rows):
        why = E._bw(r, "threat").get("flee")
        lab = "flee:%s" % why if why is not None else _retreat_label(r)
        if lab is None:
            continue
        n += 1
        by[lab] = by.get(lab, 0) + 1
        if i + 1 < len(rows):
            mins += _gap(gm[i], gm[i + 1])
            secs += _gap(E._n(r.get("wall")), E._n(rows[i + 1].get("wall")))
    return {"lines": n, "minutes": mins, "seconds": secs, "total_minutes": log_minutes(rows), "by": by}


def _xy(v):
    """(x, y) of a [x, y] or {x, y}, else None."""
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        x, y = E._n(v[0]), E._n(v[1])
    elif isinstance(v, dict):
        x, y = E._n(v.get("x")), E._n(v.get("y"))
    else:
        return None
    return (x, y) if x is not None and y is not None else None


def _zombie_xy(frame, label):
    """The (x, y) of the zombie whose id is `label` on the frame, else None."""
    z = next((E._d(q) for q in E._l(E._d(frame).get("zombies")) if E._d(q).get("id") == label), None)
    return _xy(z) if z is not None else None


def _play_targets(r):
    """The `target` values of the line's (then its inputs') `play` and `intent` dicts, in that order."""
    return [p["target"] for src in (r, E._d(r.get("inputs"))) for k in ("play", "intent") for p in [src.get(k)]
            if isinstance(p, dict) and p.get("target") is not None]


def _resolve(t, frame):
    """(label, (x, y)) of a play's target: a square ("play:<x>,<y>") or a zombie id the frame lists ("zombie:<id>"),
    else None (unresolved)."""
    sq = _xy(t)
    if sq is not None:
        return "play:%s,%s" % sq, sq
    sq = _zombie_xy(frame, t)
    return ("zombie:%s" % t, sq) if sq is not None else None


def named_target(r, frame=None):
    """(label, (x, y)) of the target the line's decider names, else None. A variant's play or intent (the line's or
    its inputs' `play`, then `intent`) a dict carrying `target` as a square ([x, y] or {x, y}; label "play:<x>,<y>")
    or as a zombie id listed on the frame at the line (label "zombie:<id>"); else, on a line whose `branch` is `goal`,
    the goal's `args` square (label its `type`) or, on a goal line whose args carry no square (a model wait, or a
    LootBuilding or Stock running), the goal why's `goal_continue.target` (label "continue:<source>"). A goal line with
    neither names none."""
    for t in _play_targets(r):
        got = _resolve(t, frame)
        if got is not None:
            return got
    if r.get("branch") != "goal":
        return None
    g = E._d(r.get("goal"))
    sq = _xy(E._d(g.get("args")))
    if sq is not None:
        return str(g.get("type")), sq
    c = E._d(E._bw(r, "goal").get("goal_continue"))
    sq = _xy(c.get("target"))
    return ("continue:%s" % c.get("source"), sq) if sq is not None else None


def toward_minutes(L):
    """The minutes moving toward a named target: {lines, minutes, named_lines, named_minutes, total_minutes, by}. A
    line (after the first) moved toward its target when it names one (`named_target`, the frame at the line by the
    wall-time bisect) and the character's position (`inputs.x`, `inputs.y`) lies more than MOVE_EPS tiles nearer it
    than the line before's position did; it counts the game minutes from the line before to it (`line_minutes`).
    The interval is line i's target's, though line i-1 decided its motion (`flee_minutes` gives line i the interval
    after it): left as is on review-t7 L2, since on F15 no interval is counted both ways. `named_*` every line naming
    a target, the same way; `unresolved` the lines (the first included) whose play or intent carries a `target` that
    resolved to nothing (`_resolve`); `by` the moving lines by target label; `total_minutes` the log's, the
    denominator."""
    rows = L.rows
    gm = line_minutes(rows)
    n, mins, nn, nmins, by = 0, 0.0, 0, 0.0, {}
    unresolved = sum(1 for r in rows for ts in [_play_targets(r)]
                     if ts and all(_resolve(t, L.frame(r)) is None for t in ts))
    for i in range(1, len(rows)):
        t = named_target(rows[i], L.frame(rows[i]))
        if t is None:
            continue
        nn += 1
        span = _gap(gm[i - 1], gm[i])
        nmins += span
        p, q = G21._pos(rows[i]), G21._pos(rows[i - 1])
        if p is None or q is None:
            continue
        if math.hypot(p[0] - t[1][0], p[1] - t[1][1]) < math.hypot(q[0] - t[1][0], q[1] - t[1][1]) - MOVE_EPS:
            n += 1
            mins += span
            lab = t[0].split(":")[0]
            by[lab] = by.get(lab, 0) + 1
    return {"lines": n, "minutes": mins, "named_lines": nn, "named_minutes": nmins, "unresolved": unresolved,
            "total_minutes": log_minutes(rows), "by": by}


def _refuge_word(v):
    return isinstance(v, str) and any(w in v.lower() for w in REFUGE_WORDS)


def names_refuge(r):
    """Whether the line names a filter, door, window or shelter target: a label (`_labels`) or a string play target
    containing a REFUGE_WORDS word; or the ladder's own, its threat why's `shelter` set (the shelter's building),
    its `doorway_pick` set to anything but `no_door` (a doorway stand, a filter), or its goal's `type` a Shelter. The
    threat why's `leg` is not read: `leg: enter` is the melee stance's entry leg (`planner/dispatch.py` MELEE_LEGS),
    no building's (review-t7-fix1 R1), and a shelter is caught by `shelter`."""
    if any(_refuge_word(x) for x in _labels(r) + _play_targets(r)):
        return True
    t = E._bw(r, "threat")
    if t.get("shelter") is not None or t.get("doorway_pick") not in (None, "no_door"):
        return True
    return _refuge_word(E._d(r.get("goal")).get("type"))


def _chaser(f):
    """(id, distance) of the frame's nearest zombie whose `hasTarget` is true (the one player on the server is its
    target, as `e21.e_sneak` reads it), by `e18._zd`, else None."""
    best = None
    for q in (E._d(x) for x in E._l(E._d(f).get("zombies"))):
        if q.get("hasTarget") is not True:
            continue
        d = G18._zd(f, q)
        if d is not None and (best is None or d < best[1]):
            best = (q.get("id"), d)
    return best


def away_minutes(L):
    """The frame-based minutes moving away from a chaser with no refuge named (spec section 8; the controller's
    ruling on review-t7 M2: it scores the ladder and the variants alike, with no label read): {intervals, minutes,
    refuge_skipped}. Over each pair of consecutive frames (wall order): the character moved (its `me` position more
    than MOVE_EPS tiles from the frame before's), the nearest zombie targeting it on the first frame (`_chaser`) is
    listed on the second, more than MOVE_EPS tiles farther, and no decision line in force over the interval (the
    line at or before its first frame's wall, and every line written within it) names a refuge (`names_refuge`): the
    interval's game minutes (`frame_minutes`) count, an interval whose game clock steps back (the frames' `me.hour`
    jitters against the wall order: five of F15's counted intervals, 0.107 min) counting 0. `refuge_skipped` the
    intervals moving away but under a refuge. The cell prints the minutes beside the label-based ones as `(away N)`;
    the denominator is the fleeing reading's, the log's game minutes."""
    walls, frames = L.index
    gm = frame_minutes(frames)
    lwalls = [(E._n(r.get("wall")) or 0.0) * 1000.0 for r in L.rows]
    n, mins, skipped = 0, 0.0, 0
    for k in range(1, len(frames)):
        a, b = frames[k - 1], frames[k]
        pa, pb = G21._me(a), G21._me(b)
        if pa is None or pb is None or G21._hyp(pa, pb) <= MOVE_EPS:
            continue
        c = _chaser(a)
        if c is None:
            continue
        q = next((E._d(x) for x in E._l(b.get("zombies")) if E._d(x).get("id") == c[0]), None)
        d1 = G18._zd(b, q) if q is not None else None
        if d1 is None or d1 <= c[1] + MOVE_EPS:
            continue
        j = bisect.bisect_right(lwalls, walls[k - 1]) - 1
        hi = bisect.bisect_right(lwalls, walls[k])
        if any(names_refuge(L.rows[i]) for i in range(max(j, 0), hi)):
            skipped += 1
            continue
        n += 1
        mins += _gap(gm[k - 1], gm[k])
    return {"intervals": n, "minutes": mins, "refuge_skipped": skipped}


def dressed(frames):
    """The wounds dressed within one game minute: {wounds, dressed, stopped, rows}. A wound is a bleed's onset on a
    body part: a frame (wall order) whose `body.parts` entry {i, bleeding} reads `bleeding` true while the part has no
    open wound (so the first frame's bleeding parts are onsets), the parts as the care readers read them
    (`gates_e.real_part`'s `body.parts[i]` entries). It ends at the part's first later frame reading `bleeding` not
    true, or the first frame not listing the part; `dressed` the wounds ending within DRESS_MIN game minutes of their
    onset (`frame_minutes`), `stopped` those ending at all; each row {part, seq0, seq1, minutes, bandaged (the end
    frame's `bandaged`)}, None past the log's end. `wounds` the denominator."""
    gm = frame_minutes(frames)
    opened, rows = {}, []
    for f, m in zip(frames, gm):
        cur = {p.get("i"): p for p in (E._d(x) for x in E._l(E._d(f.get("body")).get("parts"))) if "i" in p}
        for i, p in cur.items():
            b = p.get("bleeding") is True
            if b and i not in opened:
                opened[i] = len(rows)
                rows.append({"part": i, "seq0": f.get("seq"), "m0": m, "seq1": None, "minutes": None,
                             "bandaged": None})
            elif not b and i in opened:
                r = rows[opened.pop(i)]
                r.update(seq1=f.get("seq"), minutes=_gap(r["m0"], m), bandaged=p.get("bandaged"))
        for i in [i for i in opened if i not in cur]:   # a part no longer listed reads not bleeding
            r = rows[opened.pop(i)]
            r.update(seq1=f.get("seq"), minutes=_gap(r["m0"], m))
    for r in rows:
        r.pop("m0")
    return {"wounds": len(rows), "dressed": sum(1 for r in rows if r["minutes"] is not None
                                                and r["minutes"] <= DRESS_MIN),
            "stopped": sum(1 for r in rows if r["seq1"] is not None), "rows": rows}


def melees_superseded(out, lines):
    """The melees superseded before their swing: {superseded_before, superseded, no_swing_step, sent, spans, aids}. A
    melee span (`e19._spans`) whose terminal act line reads state `failed` and reason `superseded` (the planner sent
    another act) is `superseded`; `superseded_before` those whose progress steps hold none of PRESS_STEPS (swing,
    shove, stomp, floor: a finish's floor swing and a shove are its press) and `aids` theirs; `no_swing_step` the
    superseded with no `swing` step itself (the narrower read, beside it); `sent` the denominator, the record's
    `loop.actions` of type melee (the spans' count without a record)."""
    spans = G19._spans(lines)
    sup, before, noswing, aids = 0, 0, 0, []
    for s in spans:
        t = E._d(s["terminal"])
        if t.get("state") != "failed" or t.get("reason") != SUPERSEDED:
            continue
        sup += 1
        steps = {E._d(r).get("step") for _, r in s["progress"]}
        if not steps & set(PRESS_STEPS):
            before += 1
            aids.append(s["aid"])
        if "swing" not in steps:
            noswing += 1
    acts = [a for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions"))) if a.get("type") == "melee"]
    return {"superseded_before": before, "superseded": sup, "no_swing_step": noswing,
            "sent": len(acts) if acts else len(spans), "spans": len(spans), "aids": aids}


# ---------------------------------------------------------------- the score
def end_cell(out):
    """`death@<game minute>` off the record's `stop`, `cap` on the day cap, `crash` on a crash stop (CRASH_STOPS) or a
    record carrying `error` or `phase_errors` with no stop, else `end`; `-` without a record."""
    if not out:
        return DASH
    stop = E._d(out.get("stop"))
    reason = stop.get("reason")
    if reason == "death":
        gm = E._n(stop.get("gameMin"))
        return "death@%s" % (int(gm) if gm is not None else "?")
    if reason in CAP_STOPS:
        return "cap"
    if reason in CRASH_STOPS or (reason is None and (out.get("error") or out.get("phase_errors"))):
        return "crash"
    return "end"


def score(run):
    """The trial's score: the run's sources (`load_run`) read by the imported readers and the four new readings."""
    r = load_run(run) if isinstance(run, str) else run
    out, rows, lines = r["out"], r["rows"], r["lines"]
    L = E._Lines(out, rows, lines)
    frames = L.index[1]
    km = G21.e_kills_matched(out, lines)
    events = len(set(E._l(km.get("event_ids")))) if km.get("event_ids") is not None else None
    hu = G21.e_hits_union(frames, lines, events)
    loop = E._d(out.get("loop"))
    g0, g1 = E._n(loop.get("first_game_min")), E._n(loop.get("game_min"))
    health = E._n(E._d(frames[-1].get("body")).get("health")) if frames else None
    return {"run_id": r["run_id"], "trial": r["trial"], "minutes": g1 - g0 if g0 is not None and g1 is not None
            else None, "kills_events": events, "kills_matched": km.get("planner"), "hits": hu,
            "flee": flee_minutes(rows), "away": away_minutes(L), "legs": leg_minutes(rows),
            "labels": label_histogram(rows), "toward": toward_minutes(L), "dressed": dressed(frames),
            "melees": melees_superseded(out, lines), "goal_wait": G21.e_goal_wait(L if rows else None),
            "standing": G21.e_standing(L if rows else None), "end": end_cell(out), "health": health,
            "decision_lines": len(rows), "frames": len(frames)}


def _num(v, f="%.1f"):
    return DASH if v is None else (f % v if isinstance(v, float) else str(v))


def _variant(t):
    if t is None or t.get("variant") is None:
        return DASH
    sw = t.get("switches")
    if isinstance(sw, dict):
        sw = ["%s=%s" % (k, v) for k, v in sw.items()]
    sw = [str(x) for x in sw] if isinstance(sw, (list, tuple)) else ([str(sw)] if sw else [])
    return "%s%s" % (t["variant"], " [%s]" % ", ".join(sw) if sw else "")


def _commit(t):
    if t is None or not t.get("commit"):
        return DASH
    c, d = str(t["commit"])[:8], t.get("dirty")
    if isinstance(d, str) and d:
        return "%s-dirty-%s" % (c, d[:8])
    if d:
        h = t.get("diff_hash")
        return "%s-dirty%s" % (c, "-%s" % str(h)[:8] if h else "")
    return c


def _fixture(t):
    if t is None or not t.get("fixture"):
        return DASH
    w = t.get("waves")
    return "%s%s" % (t["fixture"], " / %s" % w if w else "")


def cells(s, seen=""):
    """The row's cells in COLUMNS order."""
    hu, fl, tw, dr, ml = s["hits"], s["flee"], s["toward"], s["dressed"], s["melees"]
    k, km = s["kills_events"], s["kills_matched"]
    kills = DASH if k is None else (str(k) if km in (None, k) else "%s (matched %s)" % (k, km))
    union = hu.get("union") if hu.get("read") else None
    hits = "%s / %s" % (hu.get("runs"), union) if hu.get("read") else DASH
    per = "%.2f" % (union / k) if union is not None and k else DASH
    sup = "%s / %s (%s superseded)" % (ml["superseded_before"], ml["sent"], ml["superseded"]) if s["frames"] or \
        ml["sent"] else DASH
    rows = s["decision_lines"]
    away = "%.1f" % s["away"]["minutes"] if s["frames"] else DASH
    return [s["run_id"], _variant(s["trial"]), _commit(s["trial"]), _fixture(s["trial"]), _num(s["minutes"]), kills,
            hits, per,
            "%.1f / %.1f (away %s)" % (fl["minutes"], fl["total_minutes"], away) if rows else DASH,
            "%.1f / %.1f" % (tw["minutes"], tw["total_minutes"]) if rows else DASH,
            "%s / %s" % (dr["dressed"], dr["wounds"]) if s["frames"] else DASH, sup, s["end"],
            _num(s["health"]), seen or ""]


def detail(s):
    """One line per reading with its count and its denominator."""
    hu, fl, tw, dr, ml = s["hits"], s["flee"], s["toward"], s["dressed"], s["melees"]
    gw, sd, aw = E._d(s["goal_wait"]), E._d(s["standing"]), s["away"]
    return [
        "kills: %s zombie_dead events, %s matched to a press (e21.e_kills_matched)" % (s["kills_events"],
                                                                                       s["kills_matched"]),
        "hits: %s reaction runs, %s hit steps, %s landed by the union, over %s kills" % (
            hu.get("runs"), hu.get("steps"), hu.get("union"), s["kills_events"]),
        "fleeing: %d lines, %.2f game minutes (%.1f s) over %.2f, by %s; the ladder's legs %s" % (
            fl["lines"], fl["minutes"], fl["seconds"], fl["total_minutes"], fl["by"],
            ", ".join("leg: %s %d lines %.2f min" % (k, v["lines"], v["minutes"]) for k, v in s["legs"].items())),
        "away from a chaser, no refuge named (frames): %d intervals, %.2f game minutes over %.2f (%d intervals under "
        "a refuge skipped)" % (aw["intervals"], aw["minutes"], fl["total_minutes"], aw["refuge_skipped"]),
        "labels (intent/play/act, `?` unknown): %s" % (s["labels"],),
        "toward a named target: %d lines, %.2f game minutes over %.2f (named on %d lines, %.2f min; %d lines' play "
        "targets resolved to nothing), by %s" % (
            tw["lines"], tw["minutes"], tw["total_minutes"], tw["named_lines"], tw["named_minutes"],
            tw["unresolved"], tw["by"]),
        "dressed within %.0f game minute: %d of %d wounds (%d stopped bleeding): %s" % (
            DRESS_MIN, dr["dressed"], dr["wounds"], dr["stopped"],
            [(r["part"], r["seq0"], r["seq1"], None if r["minutes"] is None else round(r["minutes"], 2))
             for r in dr["rows"]]),
        "melees superseded before their press: %d of %d sent (%d superseded in all, %d with no swing step) %s" % (
            ml["superseded_before"], ml["sent"], ml["superseded"], ml["no_swing_step"], ml["aids"]),
        "goal wait: %s s standing near a zombie on a model wait (e21.e_goal_wait unmoved_near_s)" % (
            gw.get("unmoved_near_s"),),
        "standing: %s stretches, %s s (e21.e_standing)" % (sd.get("stretches"), sd.get("seconds")),
    ]


# ---------------------------------------------------------------- the log
_SPLIT = re.compile(r"(?<!\\)\|")


def _esc(c):
    return str(c).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def format_row(cs):
    return "| " + " | ".join(_esc(c) for c in cs) + " |"


def parse_row(line):
    """The cells of a table row (an escaped `\\|` kept inside its cell, unescaped), else None."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    parts = [p.strip().replace("\\|", "|") for p in _SPLIT.split(s[1:-1])]
    return parts


def read_log(path):
    """(the lines before the first data row and the separator included, [row line]) of the log."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read().splitlines()
    sep = next((i for i, ln in enumerate(text) if re.match(r"^\|(\s*-+\s*\|)+\s*$", ln)), None)
    if sep is None:
        raise ScoreError("no table in %s" % path)
    return text[:sep + 1], [ln for ln in text[sep + 1:] if ln.strip()]


def write_log(path, head, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(head + rows) + "\n")


def _row_id(line):
    p = parse_row(line)
    return p[0] if p else None


def put_row(path, cs, keep_seen=True):
    """The row `cs` written into the log at `path`: in place of the row with its trial id (that row's `seen` kept when
    `cs` has none and `keep_seen`), else appended; the row written."""
    head, rows = read_log(path)
    for i, ln in enumerate(rows):
        if _row_id(ln) == cs[0]:
            if keep_seen and not cs[-1]:
                old = parse_row(ln)
                cs = cs[:-1] + [old[-1] if old and len(old) == len(COLUMNS) else ""]
            rows[i] = format_row(cs)
            break
    else:
        rows.append(format_row(cs))
    write_log(path, head, rows)
    return format_row(cs)


def rescore_all(log, runs, dry=False):
    """The log rebuilt from every run folder `x_trial-*` under `runs`: each row rescored keeping its `seen`, a row whose
    folder is gone kept, a new folder's row appended in name order; the rows."""
    head, rows = read_log(log)
    seen = {}
    for ln in rows:
        p = parse_row(ln)
        if p:
            seen[p[0]] = p[-1] if len(p) == len(COLUMNS) else ""
    folders = sorted(d for d in glob.glob(os.path.join(runs, RUN_GLOB)) if os.path.isdir(d))
    fresh = {}
    for d in folders:
        s = score(d)
        fresh[s["run_id"]] = format_row(cells(s, seen.get(s["run_id"], "")))
    out = [fresh.pop(_row_id(ln)) if _row_id(ln) in fresh else ln for ln in rows]
    out += [fresh[k] for k in sorted(fresh)]
    if not dry:
        write_log(log, head, out)
    return out


# ---------------------------------------------------------------- the command line
def parse_args(argv):
    ap = argparse.ArgumentParser(prog="trial_score.py", allow_abbrev=False,
                                 description="Score a trial's run folder into testing/trials/trials.md.")
    ap.add_argument("run", nargs="?", help="the run folder")
    ap.add_argument("--seen", action="append", default=[], help="a line of what was seen (up to three)")
    ap.add_argument("--rescore-all", action="store_true", help="rebuild every row from the x_trial-* run folders")
    ap.add_argument("--dry", action="store_true", help="print, write nothing")
    ap.add_argument("--log", default=LOG, help="the trials log (default testing/trials/trials.md)")
    ap.add_argument("--runs", default=RUNS, help="the run folders' root for --rescore-all")
    a = ap.parse_args(argv)
    if (a.run is None) == (not a.rescore_all):
        ap.error("give one run folder, or --rescore-all")
    if a.rescore_all and a.seen:
        ap.error("--seen names one run's row; --rescore-all keeps every row's own")
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
        s = score(a.run)
        cs = cells(s, SEEN_JOIN.join(x.strip() for x in a.seen))
        print(format_row(cs) if a.dry else put_row(a.log, cs))
        for ln in detail(s):
            print("  " + ln)
        return 0
    except ScoreError as e:
        print("trial_score: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
