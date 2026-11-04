#!/usr/bin/env python3
"""The visual pass's screenshot sheet (Plan 27, ruling P27-8: a cheap visual pass per live agent session).

    python tools/shot_sheet.py <run or artifact folder> <out.md> [--every N]

Reads a run folder (`testing/runs/<run>/`) or an artifact folder (`testing/artifacts/<run>/`) and writes one markdown
sheet, so a reader opens the images with the fixed questions at hand and the metrics beside each. It selects the shots
within two of every wound (a wound event: a frame on which `body.scratched`, `body.bitten` or `body.bleeding` rose, or
the first frame of a run reading `me.hitReaction` non-empty; never a frame whose health merely fell: Plan 28 Task 1,
2026-11-04), within two of every kill (an act line whose `result.targetDead` is true) and the last twelve (the death),
plus every N-th shot (default 5), and writes the
questions at the top and a section per selected shot: the image's absolute path, the marks (WOUND@seq, KILL@seq,
DEATH), the index line's moment (game minute, health, branch, flee, fight, goal, trigger, decision line, seq), the
decision line's action (type and its gait, target and velocity args) and threat (leg, target, dist, stance, approach,
reposition), and the state frame at the shot's seq (facing, moving, running, sprinting, aiming, attackers, the
hit reaction, the zombies listed and within 3 tiles, the nearest one's id, distance, hasTarget, onFloor and health,
the body's health, parts and armPain, the endurance).

The inputs are `shots/shots.jsonl` (shots with a `skipped` key are dropped), `decision.log` and every state log
(`state.log`, its rotations `state.<n>.log` and chunks `state-NNNNNN.log`) in the run's
`clients/<user>/Lua/pzagent/<user>/` (the `admin` client's when there are several) or beside the JSON in an artifact,
decoded with `agent.base.transport.files.FileTransport` on a temporary copy. Read-only over the folder; a missing
index, decision log or state log is an error on stderr and exit 2. Stdlib plus the agent base.
"""
import argparse
import bisect
import glob
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "testing") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "testing"))
from agent.base.transport.files import FileTransport  # noqa: E402

STATE_RX = re.compile(r"state(\.\d+|-\d{6})?\.log$")
NEAR_TILES = 3.0
DEATH_SHOTS = 12
NEIGHBOURS = 2
ACTION_ARGS = ("gait", "run", "x", "y", "targetId", "vx", "vy", "bearing")
WOUND_COUNTS = ("scratched", "bitten", "bleeding")

QUESTIONS = """Questions, answered per shot in one line each (the shot's number first), then a summary tying the \
answers to the marks:
1. What is the character doing (standing, walking, running, swinging, shoving, stomping, bandaging, climbing, \
looting), and does it match the decision line's action?
2. Is the character facing the nearest zombie (the frame's `dir` against the zombie's bearing), or looking elsewhere?
3. Is the character moving toward a zombie within 3 tiles, and at what gait (the frame's moving/running flags)? A run \
or walk into a zombie's reach is the thing Angus saw go wrong.
4. How many zombies are within reach (the image) and is any behind or beside the character?
5. Any obstacle at play (door, window, fence, car, corpse, furniture) and how is it used?
6. On a WOUND row: what did the character do in the shots before it that a player would not (closing at a run, \
standing in reach, facing away, fighting several)? On a KILL row: what worked (the knock-down, the stomp, the swing at \
a fallen one)? On a DEATH row: what the guides would have had it do.
"""


class SheetError(Exception):
    """An input the sheet needs is missing (a message for stderr, exit 2)."""


class Run:
    """A run folder read: its name, the shots dir, the shot index, the decision rows, the state frames and acts."""

    def __init__(self, path, shots_dir, shots, rows, frames, acts):
        self.path = path
        self.name = os.path.basename(os.path.normpath(path))
        self.shots_dir = shots_dir
        self.shots = shots
        self.rows = rows
        self.frames = frames
        self.acts = acts


def _jsonl(path):
    if not os.path.isfile(path):
        raise SheetError("missing %s" % path)
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _has_state(d):
    return any(STATE_RX.fullmatch(n) for n in os.listdir(d))


def find_state_dir(run):
    """The folder holding the run's state logs: beside the JSON (an artifact), else the run's client tree."""
    if _has_state(run):
        return run
    found = sorted(d for d in glob.glob(os.path.join(run, "clients", "*", "Lua", "pzagent", "*")) if _has_state(d))
    if not found:
        raise SheetError("no state log in %s (not beside the JSON, nor under clients/*/Lua/pzagent/*/)" % run)
    admin = [d for d in found if os.path.basename(d) == "admin"]
    return (admin or found)[0]


def read_state(state_dir):
    """The decoded lines of every state log in state_dir, read from a temporary copy."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in os.listdir(state_dir):
            if STATE_RX.fullmatch(name):
                shutil.copy(os.path.join(state_dir, name), tmp)
        return FileTransport(tmp).lines()


def load_run(path):
    """The Run at path; SheetError when the index, the decision log or a state log is missing."""
    shots_dir = os.path.join(path, "shots")
    shots = [s for s in _jsonl(os.path.join(shots_dir, "shots.jsonl")) if not s.get("skipped")]
    rows = _jsonl(os.path.join(path, "decision.log"))
    lines = read_state(find_state_dir(path))
    frames = [ln for ln in lines if ln["kind"] == "frame"]
    acts = [ln for ln in lines if ln["kind"] == "act"]
    return Run(path, shots_dir, shots, rows, frames, acts)


def find_wounds(frames):
    """The seqs of the wound events: the frames on which body.scratched, body.bitten or body.bleeding rose above the
    last value read, or me.hitReaction turned non-empty from empty or unread (a run's first frame). A frame whose
    health merely fell is no wound (Plan 28 Task 1, 2026-11-04: F11's bleed made 114 of 131 shots WOUND marks under
    the health-fall rule, and the full sheet's pass stalled)."""
    wounds = []
    last = {}
    reacting = False
    for f in frames:
        body = f.get("body") or {}
        hit = False
        for k in WOUND_COUNTS:
            v = body.get(k)
            if v is None:
                continue
            if k in last and v > last[k]:
                hit = True
            last[k] = v
        reaction = (f.get("me") or {}).get("hitReaction")
        if reaction and not reacting:
            hit = True
        reacting = bool(reaction)
        if hit:
            wounds.append(f["seq"])
    return wounds


def find_kills(acts):
    """The seqs of the act lines whose result reads targetDead."""
    return [a["seq"] for a in acts if (a.get("result") or {}).get("targetDead") is True]


def frame_at(frames, seq):
    """The last frame at or before seq, or None."""
    i = bisect.bisect_right([f["seq"] for f in frames], seq) - 1
    return frames[i] if i >= 0 else None


def near_shots(shots, seq, k=NEIGHBOURS):
    """The numbers of the shots within k places of the first shot at or after seq."""
    at = [i for i, s in enumerate(shots) if s["seq"] >= seq]
    if not at:
        return set()
    return {shots[j]["n"] for j in range(max(0, at[0] - k), min(len(shots), at[0] + k + 1))}


def select_shots(run, every=5):
    """(the selected shots in index order, {shot n: set of marks}, the wound seqs, the kill seqs)."""
    wounds, kills = find_wounds(run.frames), find_kills(run.acts)
    marks = {}
    for tag, seqs in (("WOUND", wounds), ("KILL", kills)):
        for seq in seqs:
            for n in near_shots(run.shots, seq):
                marks.setdefault(n, set()).add("%s@%d" % (tag, seq))
    for s in run.shots[-DEATH_SHOTS:]:
        marks.setdefault(s["n"], set()).add("DEATH")
    selected = [s for s in run.shots if s["n"] in marks or (s["n"] - 1) % every == 0]
    return selected, marks, wounds, kills


def _dist(z):
    d = z.get("dist")
    return 99 if d is None else d


def _section(run, s, marks):
    row = run.rows[s["decision_line"] - 1] if s.get("decision_line") and s["decision_line"] - 1 < len(run.rows) else {}
    a = row.get("action") or {}
    th = ((row.get("inputs") or {}).get("branches") or {}).get("threat") or {}
    f = frame_at(run.frames, s["seq"]) or {}
    me, body = f.get("me") or {}, f.get("body") or {}
    zs = f.get("zombies") or []
    near = [z for z in zs if _dist(z) <= NEAR_TILES]
    nearest = min(zs, key=_dist) if zs else {}
    args = {k: v for k, v in (a.get("args") or {}).items() if k in ACTION_ARGS}
    return (
        "## shot %d  %s\n" % (s["n"], os.path.abspath(os.path.join(run.shots_dir, s["file"]))) +
        "- marks: %s\n" % (", ".join(sorted(marks.get(s["n"], ()))) or "-") +
        "- moment: gm %s, health %s, branch %s, flee %s, fight %s, goal %s, trigger %s, decision line %s, seq %s\n" % (
            s.get("gameMin"), s.get("health"), s.get("branch"), s.get("flee"), s.get("fight"), s.get("goal"),
            s.get("trigger"), s.get("decision_line"), s["seq"]) +
        "- decision: action %s %s; threat leg %s target %s dist %s stance %s approach %s reposition %s\n" % (
            a.get("type"), json.dumps(args), th.get("leg"), th.get("target"), th.get("dist"), th.get("stance"),
            th.get("approach"), th.get("reposition")) +
        "- frame seq %s: dir %s moving %s running %s sprinting %s aiming %s attackers %s hitReaction %r; "
        "zombies listed %d, within 3 tiles %d, nearest %s at %s (hasTarget %s, onFloor %s, health %s); "
        "body health %s parts %d armPain %s endurance %s\n\n" % (
            f.get("seq"), me.get("dir"), me.get("moving"), me.get("running"), me.get("sprinting"), me.get("aiming"),
            me.get("attackers"), me.get("hitReaction"), len(zs), len(near), nearest.get("id"), nearest.get("dist"),
            nearest.get("hasTarget"), nearest.get("onFloor"), nearest.get("health"), body.get("health"),
            len(body.get("parts") or []), body.get("armPain"), (f.get("stats") or {}).get("endurance")))


def write_sheet(run, out, every=5):
    """Write the sheet for run to out; the selection counts as a dict (shots, selected, wounds, kills)."""
    selected, marks, wounds, kills = select_shots(run, every)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Shot sheet: %s (%d of %d shots: around %d wounds, %d kills, the death, every %d-th)\n\n" % (
            run.name, len(selected), len(run.shots), len(wounds), len(kills), every))
        fh.write(QUESTIONS + "\n")
        fh.write("Per shot: the image path; the index moment (game minute, health, branch/flee/fight/goal); "
                 "the decision line's action; the frame at the shot's seq.\n\n")
        for s in selected:
            fh.write(_section(run, s, marks))
    return {"shots": len(run.shots), "selected": len(selected), "wounds": wounds, "kills": kills}


def _every(text):
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("--every is at least 1")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="The visual pass's sheet over a run or artifact folder.")
    ap.add_argument("run", help="a testing/runs/<run> or testing/artifacts/<run> folder")
    ap.add_argument("out", help="the markdown sheet to write")
    ap.add_argument("--every", type=_every, default=5, help="also take every N-th shot (default 5)")
    args = ap.parse_args(argv)
    try:
        summary = write_sheet(load_run(args.run), args.out, args.every)
    except SheetError as e:
        print("shot_sheet: %s" % e, file=sys.stderr)
        return 2
    print("wrote %s: %d of %d shots, wounds %d, kills %d" % (
        args.out, summary["selected"], summary["shots"], len(summary["wounds"]), len(summary["kills"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
