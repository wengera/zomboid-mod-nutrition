"""The utility's offline replay and its goldens (Plan 31 Task 11 U; the proposal's § 5 "Goldens"): `Survive` under
`control="utility"` ticked once per decision line of a committed ring, open loop, and its decisions and scores pinned
as `testing/tests/pzagent/fixtures/survive-utility-<key>.json`.

THE METHOD (no wall clock is read; a run twice gives identical output):
- The frames: the ring's lines through `replay_decisions.read_record` (the state log decoded as live, the delta
  frames merged); before each decision line every line written by the line's `wall` (`wallMs / 1000 <= wall`) is
  applied to the World, in order. The alignment is by wall time, not `replay_decisions.align`'s hour match, which
  refuses F15 (two frames share line 164's hour).
- The clock: Survive's injected clock reads the decision line's recorded `wall`.
- The goal: `ReplayGoals`, `replay_decisions.RecordedGoals` (the record's own goal answers: the goal is not
  replayed) reading a line whose record holds no goal at all (the ladder never asked its runner that tick) as a
  source pending: live, the utility asks its runner then (`core.Utility._goal_read`), which proposes or waits on its
  source, so the replay's goal candidate holds where the live one would walk or wait (fix 1, review-t11-utility M4:
  the record's silence is no answer of the runner's).
- The acts (`OpenLoop`): no recorded act line drives a replayed action (the record's aids are its own); each send
  supersedes every open one (the Lua's one command at a time); a `steer`, `aim` or `melee` ends `done` at its
  `seconds` (PZA/1.10's melee has none: it never ends on time), a `stop` or a posture at POSTURE_DONE_S, any other at
  the Actions deadline. The World follows the
  recorded frames whatever the replay sends, so a replayed line checks a decision at a recorded situation, never an
  outcome.

THE GOLDENS (`golden_text`): `{artifact, base, decisions, recorded}`, one decision a line, each `{line, gameMin,
branch, action, act, select, held_by, runner_up, margin, scores: {key: total}}`. Re-recorded only under a named change
of the utility (`python -m agent.base.planner.utility.replay --write <key>` from `testing/`), each moved line
attributed in the task's report.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

from agent.base.actions import TERMINAL, Actions
from agent.base.planner.goal_runner import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.planner.utility import features as F
from agent.base.replay_decisions import ARTIFACTS, REPO, RecordedGoals, _Transport, read_record
from agent.base.world import World

RUNS = {"f15": "f_goals_16-20261105-164332", "e23": "e_day_23-20261105-095110"}
FIXTURES = os.path.join(REPO, "testing", "tests", "pzagent", "fixtures")
LEG_TYPES = ("steer", "aim", "melee")   # ended `done` at their `seconds`, as the Lua ends them
QUICK_TYPES = ("stop", "sneak")         # ended `done` POSTURE_DONE_S after their send
POSTURE_DONE_S = 0.5                    # seconds: a stop's or a posture's end (one planner tick; the Lua's is a frame)
AID_OFFSET = 100000                     # the replay's first aid less one: past every record's own


class OpenLoop:
    """The replay's act model (the module docstring's THE ACTS)."""

    def __init__(self, actions):
        self.actions = actions

    def end(self, now):
        for a in self.actions.history + self.actions.postures:
            if a.state in TERMINAL:
                continue
            if a.type in LEG_TYPES and "seconds" in a.args and now - a.sent_wall >= a.args["seconds"]:
                a.state, a.ended_wall, a.result = "done", now, {}
            elif a.type in QUICK_TYPES and now - a.sent_wall >= POSTURE_DONE_S:
                a.state, a.ended_wall, a.result = "done", now, {}

    def sent(self, a, open_before, now):
        if a.type in QUICK_TYPES and a.type != "stop":
            return   # a posture supersedes nothing (PZA/1.9: the running skill is left as it is)
        for b in open_before:
            if b.type == "sneak":
                continue
            b.state, b.reason, b.ended_wall = "failed", "superseded", now


class ReplayGoals(RecordedGoals):
    """The record's goal answers, a line with no goal at all read as a source pending (the module docstring)."""

    def feed(self, row):
        super().feed(row)
        if row.get("goal") is None:
            self.pending = True


def walk(lines, rows, world):
    """(k, row) of each decision row, 1-based, once every line written by its `wall` is applied to `world` in order
    (the module docstring's THE FRAMES): the one alignment the replay, the situations and `tools/utility_fit.py`
    share."""
    i = 0
    for k, row in enumerate(rows, 1):
        while i < len(lines) and lines[i]["wallMs"] / 1000.0 <= row["wall"]:
            world.apply(lines[i])
            i += 1
        yield k, row


def unlisted(world):
    """The ids the World keeps that the newest frame did not list (its ZOMBIE_TTL_S memory): left out of an offline
    situation, which reads the frame as it stands."""
    return frozenset(zid for zid, z in world.zombies.items() if z.get("seenWallMs") != world.frame_wall_ms)


def situations(lines, rows, fresh_only=True):
    """[(k, row, Situation, World)] of each decision row read offline (`walk`, the closing speeds across the rows),
    the World the one being walked (read it before the next row): with `fresh_only` the newest frame's zombies only
    (the fit's mining, which knows no kill), else every zombie the World keeps, as the live selector reads it."""
    world, tracks = World(), F.Tracks()
    for k, row in walk(lines, rows, world):
        if world.me is None:
            continue
        stale = unlisted(world) if fresh_only else frozenset()
        tracks.update(world, row["wall"], stale)
        yield k, row, F.read(world, row["wall"], tracks, stale), world


def replay(artifact_dir, mutate=None, upto=None):
    """Every replayed decision line, as the replayed Survive logged it (the module docstring). `mutate(survive)` runs
    once on the fresh Survive before the first tick (the mutation pass's seam); `upto` replays lines 1 to `upto`."""
    lines, rows = read_record(artifact_dir)
    rows = rows if upto is None else rows[:upto]
    now = {"t": rows[0]["wall"] if rows else 0.0}

    def clock():
        return now["t"]

    world, actions = World(), Actions(_Transport(), clock=clock)
    actions._n = AID_OFFSET   # the replay's aids never the record's (its act lines reach the World's `act_n`)
    loop = OpenLoop(actions)
    with tempfile.TemporaryDirectory() as d:
        log_path = os.path.join(d, "decision.log")
        sv = Survive(world, actions, log_path, clock, source=ScriptedSource(), control="utility")
        sv.goals = ReplayGoals(sv.goals.kit)
        if mutate is not None:
            mutate(sv)
        for _, row in walk(lines, rows, world):
            now["t"] = row["wall"]
            loop.end(now["t"])
            actions.pump([])
            sv.goals.feed(row)
            open_before = [a for a in actions.history + actions.postures if a.state not in TERMINAL]
            a = sv.tick(world, actions)
            if a is not None:
                loop.sent(a, open_before, now["t"])
        with open(log_path, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f]


def decisions(replayed):
    """The golden's rows of a replayed log (the module docstring)."""
    out = []
    for k, rep in enumerate(replayed, 1):
        u = rep["inputs"].get("utility") or {}
        out.append({"line": k, "gameMin": rep["gameMin"], "branch": rep["branch"], "action": rep["action"],
                    "act": u.get("act"), "select": u.get("select"), "held_by": u.get("held_by"),
                    "runner_up": u.get("runner_up"), "margin": u.get("margin"),
                    "scores": {key: v[0] for key, v in sorted((u.get("scores") or {}).items())}})
    return out


def golden_text(rows, base, artifact, recorded):
    body = ",\n".join(json.dumps(r, sort_keys=True) for r in rows)
    return ('{"artifact": %s, "base": %s, "decisions": [\n%s\n], "recorded": %s}\n'
            % (json.dumps(artifact), json.dumps(base), body, json.dumps(recorded)))


def golden_path(key):
    return os.path.join(FIXTURES, "survive-utility-%s.json" % key)


def run_dir(key):
    return os.path.join(ARTIFACTS, RUNS[key])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay Survive(control='utility') over a ring; --write re-records.")
    ap.add_argument("keys", nargs="+", choices=sorted(RUNS))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip()
    for key in args.keys:
        rows = decisions(replay(run_dir(key)))
        acts = {}
        for r in rows:
            k = (r["act"] or "none").split(":")[0]
            acts[k] = acts.get(k, 0) + 1
        print(key, len(rows), json.dumps(acts, sort_keys=True))
        if args.write:
            with open(golden_path(key), "w", encoding="utf-8", newline="\n") as f:
                f.write(golden_text(rows, base, RUNS[key], datetime.date.today().isoformat()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
