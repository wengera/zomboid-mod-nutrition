"""The Survive decision golden (Plan 24 Task 1, spec § 2 and § 3.1): the survival planner replayed offline over a live
artifact's recorded inputs, its decisions the oracle every later change to the planner reproduces or re-records.

`run(artifact_dir, source="scripted") -> list[dict]` ticks one `Survive` (built with `goals.ScriptedSource()`, its
goal runner then replaced, below) once per line of the artifact's `decision.log`, and returns one row per tick whose
branch is not `goal`: `{line, gameMin, branch, action: {type, args} or null, why}`, `line` the 1-based decision.log
line, `why` the threat branch's own why fields (`inputs.branches.threat` of the replayed decision line; {} when the
threat branch passed). Floats are the replayed log's own (json round trip of the frames' values, no rounding).

THE METHOD (no wall clock is read; a run twice gives identical output):
- The frames. The artifact's `state.log` is decoded through `FileTransport` (the delta frames merged as live). Each
  decision line is aligned to the one frame whose `me.hour` equals the line's recorded `inputs.hour` (a float that
  changes every frame: on E5 and F1 every line matches exactly one frame, the last one written before the line's
  `wall`); the World and the Actions take every line up to that frame, then the trailing lines after it (acts and
  events before the next frame) written by the tick's wall (`wallMs / 1000 <= wall`: the client and the driver share
  the host clock): what the live loop's last pump before the tick had read. The log's `wall` is read at the tick's
  end, after its pump, so a trailing line may have been written after that pump: when the trailing lines would end
  the current action and the record's own `inputs.running` still names that action's type, the tick had not read
  them, and they are taken at the next tick (on F1 once, at line 498: a60's `done`, written 2 ms before the
  line's wall; on E5 never).
- The clock. Survive's injected clock (its `clock` seam, which its policies, Night and goal runner share) reads the
  recorded `wall` of the decision line being replayed; the Actions' pump runs at that clock too, so an action's
  `sent_wall` is its recorded send's wall. The log's `wall` is read at the tick's end, so a clock read inside the
  tick (a Fight's stall clock started there) is late by the tick's own run: the logged `inputs.fight_s` differs from
  the record's by at most 0.0033 s on F1. A clock difference read against a threshold is late by as much: the nearest
  such read on E5 and F1 is Flee's `_leg_still` against WALK_STALL_S (1.0 s, then STEP_STALL_S, through
  `Flee.stuck()`, the `stuck` corner) at E5 line 228, 0.993975 s, 6.0 ms under it (Task 1's review, M2: 0.99 moves
  E5 there). The
  replay agrees there because its clock error is under that margin; a slower tick in a later artifact could read a
  false divergence at such a line. The stall clock `fight_s` stays far from FIGHT_MAX_S (20 s).
- The acts. The record's aids are read off the act lines (the k-th sent decision line's action is the record's
  aid `a<k + offset>`, the offset the session's pre-loop sends, checked by the act lines' `type`; the replay's own
  aids are numbered from the same offset, so a `holding` aid in a why reads as the record's). A replayed send
  that equals the record's send on the same line (type and args, each read through `as_run`: Task 12 fix 1, the
  review's minor 5, so a leg the record sprinted binds to the run the planner sends since P24-O, a steer ending at its
  seconds whatever its gait) is bound to that aid, and the record's act lines of
  that aid drive it through `Actions.pump` as live (accepted, progress, done, failed, superseded). A replayed send
  the record did not make is unbound: it fails every action still open before it `superseded` at its send (the Lua's
  supersede); a bound one fails only the older unbound ones (the record's own act lines supersede the bound ones);
  an unbound `steer` or `aim` ends `done` once its `seconds` have passed on the clock (the Lua ends a steer and a
  stance leg at its seconds; Task 10 fix 1, the review's major 3: an unbound aim held open would make every stand one
  leg), and any other unbound action ends only by a supersede or the Actions deadline. An action the replay superseded is
  unbound, its later recorded act lines dropped. A recorded aid the replay did not send has its act lines dropped.
  The replay is open loop: the World follows the recorded frames whatever the replay sends, so after a first
  divergence the later lines of that episode are counterfactual (an unbound attack or walk held open longer than it
  ran live); the first moved line is faithful, and a later one is attributed "downstream of line N (open loop)".
- The goal (excluded). The goal branch's proposals are not replayed: `RecordedGoals` stands in for the goal runner
  and answers each tick from the record: the recorded goal action when the record's line sent one from the goal
  branch (so the goal's sends supersede the threat policies' actions as they did live), else a hold while the
  recorded `goal` field names a running or pending goal, else a pass; its `line()` is the recorded `goal` field and
  its `why` the recorded `inputs.branches.goal`. The ticks the replay answers from the goal branch are left out of
  the output; no threat decision reads the goal itself.

THE GOLDENS: `testing/tests/pzagent/golden/survive-decisions-<key>.json` (`golden_text`: `{artifact, base, caps,
decisions, recorded, span}`, `caps` only where `HELLO_CAPS` names the key, `span` only where `SPANS` does, sorted keys,
one decision a line, LF), checked byte for byte by `test_replay_decisions.py`. E5 and F1 ran on HEAD's rules and agree with their records; E2, E3 and E4 (Task 1 fix 1:
the hold, breach, shelter, exit and stuck paths E5 and F1 never reach) ran on older rules, so their goldens are HEAD's
decisions over the old inputs, regression goldens whose divergence from the record is named, not agreement-pinned
oracles: E2 (planner at 42e7f49b) diverges first at line 94, the reposition floor (P23-AJ 5, aa130e9d); E3 (145868e2)
at 137, the exterior door by its own edge and the room-less door (amendment 5, c41f9880; R2, 259a58bc); E4
(259a58bc) at 302, the running leg cut on a new threat ahead (P23-AP 3, e07a52cb). `f1-caps15` (Task 10 fix 1, the
review's major 3) is F1's inputs replayed with a hello whose caps add the PZA/1.5 skills (`CAPS_15`: the record's
own hello announced none, so the World's `can` keeps the stance, the care, the fill and the climb off every other
golden): a regression pin of HEAD's decisions over real frame sequences, never an agreement oracle (the record ran
the approach and swing, so its first moved line, the first stance leg, is the only faithful one and every later line
of that episode is open loop); it pins the stand decision, the stance's legs and its stand-off fallback on real
target and health sequences, and that no rule raises on a real record. The care branch and the fill are not
exercised there (F1's parts decode `bleeding` None and its squares carry no `water`). The re-record
rule (CLAUDE.md § 6, golden trace): a golden is re-recorded only under a named behaviour change of the planner, in the
commit of the task whose change reaches it (`python -m agent.base.replay_decisions --write <key>` from `testing/`),
with every moved decision attributed in that task's report; never to make a failing test pass otherwise. Plan 24
Task 18 re-recorded all six under ruling P24-X (the fight sought within ENGAGE_R), each first moved at its line 1
(the engage of the zombie listed 7 tiles from the fixture's spawn, where the record looted); `Survive.ENGAGE` off
reproduces the files of 24987f2a byte for byte (`test_replay_decisions.PRE_X`), so the tests pinning an earlier
ruling's line read it there (`pre_x`).

`agreement(artifact_dir, replayed)` compares the replayed log with the record's own decision.log at every line where
the replayed World holds the recorded world inputs (`WORLD_INPUTS` equal) and either side answered from the threat
branch: the branch and the action, a recorded `sprint` gait read as `run` (`as_run`, ruling P24-O, Plan 24 Task 12:
the planner never sprints; the goldens were re-recorded under it where a sprint became a run; the binder reads the
same, Task 12 fix 1). It is an offline oracle's reading; a divergence is a finding about the planner or
the replay's act model, named in the task report, not a failure. At the goldens' recording (Plan 24 Task 1): E5 116
of 116 threat lines agree, F1 331 of 331, none skipped, and every threat why equals the record's; at fix 1's
recording E2 97 of 119, E3 113 of 131, E4 1134 of 1341, none skipped.

`source` names the goal source Survive is built with (`SOURCES`: "scripted" only); the goal runner it makes is
replaced by `RecordedGoals` before the first tick, so the source never proposes.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

from agent.base import pza1
from agent.base.actions import TERMINAL, Actions
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.base.world import World

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ARTIFACTS = os.path.join(REPO, "testing", "artifacts")
GOLDEN_DIR = os.path.join(REPO, "testing", "tests", "pzagent", "golden")
RUNS = {"e5": "e_day_5-20261028-201255", "f1": "f_goals-20261028-202437", "e2": "e_day_2-20261028-124249",
        "e3": "e_day_3-20261028-153631", "e4": "e_day_4-20261028-173649"}
# a golden's `span` where it needs naming (Task 1 fix 1)
SPANS = {"e4": "the whole decision.log (1680 lines) as the planner saw it, uncut: the character died at game minute "
               "627 (its inventory removed at seq 4236-4254) and the record read no death event, so the loop ran on "
               "to the day cap; the lines after the death replay a dead character's frames"}
CAPS_15 = ("aim", "climb", "bandage", "rip", "wash", "fill")   # the PZA/1.5 skills (Task 9)
# a golden replayed with its record's hello caps plus these (Task 10 fix 1, the review's major 3): key -> added caps
HELLO_CAPS = {"f1-caps15": CAPS_15}
RUNS["f1-caps15"] = RUNS["f1"]
LEG_TYPES = ("steer", "aim")   # the unbound actions the replay ends `done` at their `seconds` (THE ACTS)
SOURCES = {"scripted": ScriptedSource}
WORLD_INPUTS = ("x", "y", "health", "hunger", "thirst", "fatigue", "hour", "armed", "load", "threats")
COMMANDS = {c.TYPE: c for c in vars(pza1).values() if isinstance(c, type) and issubclass(c, pza1._Cmd)
            and c is not pza1._Cmd}


def command(action):
    """The pza1 command of a recorded `{type, args}`."""
    return COMMANDS[action["type"]](**action["args"])


def read_record(artifact_dir):
    """(state lines decoded as live, decision.log rows)."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(artifact_dir, "state.log"), "rb") as src:
            data = src.read()
        with open(os.path.join(d, "state.log"), "wb") as dst:
            dst.write(data)
        lines = list(FileTransport(d).lines())
    with open(os.path.join(artifact_dir, "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(ln) for ln in f if ln.strip()]
    return lines, rows


def align(lines, rows):
    """For each decision row `(frame_end, wall_end)`: one past its frame (the one whose `me.hour` is the row's
    `inputs.hour`), and one past the non-frame lines after that frame written by the row's `wall` (the trailing
    lines, before the next frame; the module docstring)."""
    by_hour = {}
    for i, ln in enumerate(lines):
        if ln["kind"] == "frame":
            by_hour.setdefault(ln["me"].get("hour"), []).append(i)
    ends, last = [], 0
    for k, row in enumerate(rows, 1):
        hits = [i for i in by_hour.get(row["inputs"]["hour"], []) if i >= last]
        if len(hits) != 1:
            raise ValueError("decision line %d: %d frames read hour %r" % (k, len(hits), row["inputs"]["hour"]))
        end = hits[0] + 1
        while end < len(lines) and lines[end]["kind"] != "frame" and lines[end]["wallMs"] / 1000.0 <= row["wall"]:
            end += 1
        ends.append((hits[0] + 1, end))
        last = hits[0]
    return ends


def recorded_aids(lines, rows):
    """({decision line: the record's aid of the action that line sent}, offset): the k-th sent line's aid is
    `a<k + offset>`, the offset the aids first acked before the first sent line's wall (the session's pre-loop sends),
    each checked against the act lines' `type`."""
    types, first = {}, {}
    for ln in lines:
        if ln["kind"] == "act":
            types.setdefault(ln["aid"], ln.get("type"))
            first.setdefault(ln["aid"], ln["wallMs"])
    sent = [(k, row["action"]["type"]) for k, row in enumerate(rows, 1) if row["sent"]]
    if not sent:
        return {}, len(first)
    first_wall = rows[sent[0][0] - 1]["wall"]
    offset = sum(1 for w in first.values() if w / 1000.0 < first_wall)
    out = {}
    for n, (k, typ) in enumerate(sent, 1):
        aid = "a%d" % (n + offset)
        if types.get(aid, typ) != typ:
            raise ValueError("decision line %d sent %s; the act lines name %s %s" % (k, typ, aid, types[aid]))
        out[k] = aid
    return out, offset


class _Transport:
    """The replay's command sink: `cmd_seq` and `send`, nothing written."""

    def __init__(self):
        self.cmd_seq = 0

    def send(self, cmd):
        self.cmd_seq = cmd["seq"]


class RecordedGoals:
    """The goal runner's seam on Survive, answered from the record (the module docstring's THE GOAL)."""

    def __init__(self, kit):
        self.kit = kit
        self.row = None
        self.actions = None
        self.current = None
        self.pending = False
        self.why = {}

    def feed(self, row):
        g = row.get("goal") or {}
        why = (row["inputs"].get("branches") or {}).get("goal") or {}
        self.row = row
        self.pending = "pending" in g or why.get("pending") is True
        self.current = g if g.get("state") == "running" else None

    def observe(self, world, actions):
        self.actions = actions

    def tick(self, world, actions, view=None):
        self.actions = actions
        self.why = dict((self.row["inputs"].get("branches") or {}).get("goal") or {})
        if self.row["branch"] == "goal" and self.row["sent"] and self.row["action"] is not None:
            return command(self.row["action"])
        return None

    def held(self, by_other):
        pass

    def send(self, cmd):
        return self.actions.send(cmd)

    def line(self):
        return self.row.get("goal")


class _Acts:
    """The replay's act model (the module docstring's THE ACTS): the record's act lines onto the bound actions."""

    def __init__(self, actions, rec_aids):
        self.actions, self.rec_aids = actions, rec_aids
        self.bound = {}        # the record's aid -> the replay's Action
        self.unbound = []      # the replay's Actions bound to no recorded aid, in send order

    def translate(self, got):
        return [dict(ln, aid=self.bound[ln["aid"]].aid) for ln in got
                if ln["kind"] == "act" and ln["aid"] in self.bound]

    def ends_current(self, got):
        """True when the act lines of `got` end the current action."""
        cur = self.actions.current
        return cur is not None and any(ln["aid"] == cur.aid and ln["state"] in TERMINAL for ln in self.translate(got))

    def end_legs(self, now):
        """Each unbound steer or aim (LEG_TYPES) ends `done` once its `seconds` have passed (the Lua's own end)."""
        for a in self.unbound:
            if a.type in LEG_TYPES and a.state not in TERMINAL and now - a.sent_wall >= a.args["seconds"]:
                a.state, a.ended_wall, a.result = "done", now, {}

    def sent(self, k, row, a, open_before, now):
        rec = row["action"] if row["sent"] else None
        is_bound = rec is not None and as_run(rec) == as_run({"type": a.type, "args": a.args})
        if is_bound:
            self.bound[self.rec_aids[k]] = a
        else:
            self.unbound.append(a)
        for b in open_before:
            if b in self.unbound or not is_bound:   # the Lua's supersede of what the record did not supersede
                b.state, b.reason, b.ended_wall = "failed", "superseded", now
                if b in self.unbound:
                    self.unbound.remove(b)
                for aid in [r for r, x in self.bound.items() if x is b]:
                    del self.bound[aid]


def with_caps(line, caps):
    """A hello line with `caps` added to its own (in order, each once); any other line unchanged."""
    if caps is None or line.get("kind") != "hello":
        return line
    own = list(line.get("caps") or ())
    return dict(line, caps=own + [c for c in caps if c not in own])


def replay(artifact_dir, source="scripted", mutate=None, caps=None):
    """Every replayed decision line, the goal branch's included, as the replayed Survive logged it (the module
    docstring). `mutate(survive)`, when given, runs once on the fresh Survive before the first tick (the tests'
    mutation seam); `caps`, when given, are added to every hello's (`HELLO_CAPS`)."""
    if source not in SOURCES:
        raise ValueError("source %r: one of %s" % (source, sorted(SOURCES)))
    lines, rows = read_record(artifact_dir)
    ends = align(lines, rows)
    rec_aids, offset = recorded_aids(lines, rows)
    lines = [with_caps(ln, caps) for ln in lines]
    now = {"t": rows[0]["wall"] if rows else 0.0}

    def clock():
        return now["t"]   # the recorded wall of the line being replayed

    world, actions = World(), Actions(_Transport(), clock=clock)
    actions._n = offset   # the replay's aids numbered as the record's (the session's pre-loop sends are not replayed)
    acts = _Acts(actions, rec_aids)
    with tempfile.TemporaryDirectory() as d:
        log_path = os.path.join(d, "decision.log")
        sv = Survive(world, actions, log_path, clock, source=SOURCES[source]())
        sv.goals = RecordedGoals(sv.goals.kit)
        if mutate is not None:
            mutate(sv)
        i = 0
        for k, (row, (frame_end, wall_end)) in enumerate(zip(rows, ends), 1):
            now["t"] = row["wall"]
            for trailing, chunk in ((False, lines[i:frame_end]), (True, lines[max(i, frame_end):wall_end])):
                if trailing and acts.ends_current(chunk) and row["inputs"]["running"] == actions.current.type:
                    break   # lines the tick had not read: the record still ran the action they end
                for ln in chunk:
                    world.apply(ln)
                acts.end_legs(now["t"])
                actions.pump(acts.translate(chunk))
                i += len(chunk)
            sv.goals.feed(row)
            open_before = [a for a in actions.history if a.state not in TERMINAL]
            a = sv.tick(world, actions)
            if a is not None:
                acts.sent(k, row, a, open_before, now["t"])
        with open(log_path, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f]


def decisions(replayed):
    """The output rows of a replayed log: every tick not answered by the goal branch (the module docstring)."""
    return [{"line": k, "gameMin": rep["gameMin"], "branch": rep["branch"], "action": rep["action"],
             "why": (rep["inputs"].get("branches") or {}).get("threat") or {}}
            for k, rep in enumerate(replayed, 1) if rep["branch"] != "goal"]


def run(artifact_dir, source="scripted", mutate=None, caps=None):
    """The replayed decisions: `decisions(replay(...))`."""
    return decisions(replay(artifact_dir, source, mutate, caps))


def as_run(action):
    """The action with a recorded `sprint` gait read as `run` (ruling P24-O, Plan 24 Task 12: the planner never
    sprints, so a record's sprint and the replay's run of the same leg are one decision); others unchanged."""
    if not action or (action.get("args") or {}).get("gait") != "sprint":
        return action
    return dict(action, args=dict(action["args"], gait="run"))


def agreement(artifact_dir, replayed):
    """{compared, agree, skipped_world, first_divergence, gait_only}: the replayed log against the record's own
    decision.log at every line where either answered from the threat branch and the replayed World held the recorded
    world inputs (`WORLD_INPUTS` equal; the lines where it did not are counted in `skipped_world`): the branch and
    the action, a recorded sprint read as the run P24-O sends (`as_run`; `gait_only` counts the agreeing lines that
    differ only so)."""
    _, rows = read_record(artifact_dir)
    compared, agree, skipped, first, gait_only = 0, 0, 0, None, 0
    for k, (rec, rep) in enumerate(zip(rows, replayed), 1):
        if rec["branch"] != "threat" and rep["branch"] != "threat":
            continue
        if any(rec["inputs"].get(f) != rep["inputs"].get(f) for f in WORLD_INPUTS):
            skipped += 1
            continue
        compared += 1
        if (rep["branch"], rep["action"]) == (rec["branch"], as_run(rec["action"])):
            agree += 1
            gait_only += rep["action"] != rec["action"]
        elif first is None:
            first = {"line": k, "gameMin": rec["gameMin"],
                     "record": {"branch": rec["branch"], "action": rec["action"], "sent": rec["sent"],
                                "why": rec["inputs"]["branches"].get("threat")},
                     "replay": {"branch": rep["branch"], "action": rep["action"], "sent": rep["sent"],
                                "why": rep["inputs"]["branches"].get("threat")}}
    return {"compared": compared, "agree": agree, "skipped_world": skipped, "first_divergence": first,
            "gait_only": gait_only}


def golden_text(decisions_, base, artifact, recorded, span=None, caps=None):
    """The golden file's bytes: `{artifact, base, caps, decisions, recorded, span}` (`caps` and `span` only when
    given), sorted keys, one decision a line, LF."""
    body = ",\n".join(json.dumps(d, sort_keys=True) for d in decisions_)
    head = "" if caps is None else ', "caps": %s' % json.dumps(list(caps))
    tail = "" if span is None else ', "span": %s' % json.dumps(span)
    return ('{"artifact": %s, "base": %s%s, "decisions": [\n%s\n], "recorded": %s%s}\n'
            % (json.dumps(artifact), json.dumps(base), head, body, json.dumps(recorded), tail))


def golden_path(key):
    return os.path.join(GOLDEN_DIR, "survive-decisions-%s.json" % key)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay Survive over a live artifact; --write re-records a golden.")
    ap.add_argument("keys", nargs="+", choices=sorted(RUNS))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip()
    for key in args.keys:
        run_dir = os.path.join(ARTIFACTS, RUNS[key])
        replayed = replay(run_dir, caps=HELLO_CAPS.get(key))
        text = golden_text(decisions(replayed), base, RUNS[key], datetime.date.today().isoformat(), SPANS.get(key),
                           HELLO_CAPS.get(key))
        print(key, json.dumps(agreement(run_dir, replayed), sort_keys=True))
        if args.write:
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(golden_path(key), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
