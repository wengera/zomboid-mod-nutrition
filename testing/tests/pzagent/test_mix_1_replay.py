"""mix_1 over recorded rings (Plan 31 Task 13; the build amendments' item 4, the common amendments' item 6): the two
committed rings F15 (`f_goals_16-20261105-164332`) and E23 (`e_day_23-20261105-095110`), decoded as live
(`replay_decisions.read_record`), and two of round one's trial runs where this machine has them (`testing/runs/`, or
`$PZT_RUNS`; skipped elsewhere: the runs are per-machine and never committed): trial 4 (`x_trial-tactician-20261105-
221951`, the tactician on the arena's lone waves, which left the idle 6073 at 8.4 tiles for 79 s) and trial 10
(`x_trial-doctrine-20261105-231313`, the doctrine on the street, whose crawler 15465 bit through the Dress), their
admin client's state logs decoded by the same reader (`gates_e.session_lines`: `FileTransport`, `pza1.decode`,
`merge_delta`).

The replay is open loop (`replay_decisions.py`'s docstring): `Survive(control="mix_1")` ticks at 2 Hz over the
recorded frames, its commands sent through a stub transport and ended `done` after DONE_S (the record's own act lines
are never replayed); it checks the decisions at the recorded situations, never their outcomes. At each tick the
situation is read off the decider's own masked view (`Mix1._masked(Mix1.view())`, after the tick: the world it decided
on, with its `clear` label, its held dressings and refuges), and the tick's decision line is checked against it:

- `lone`: one standing zombie within DANGER_R, armed, no dressing due and no crawler to finish → a `fight`, on the
  threat branch, never a retreat (the doctrine, item 5's first rule).
- `bleed`: a dressing due (nothing standing or crawling within KEEP_R, something to dress with) and nothing standing
  within KEEP_R + DRESS_MARGIN (the tactician's held fight) → a `dress`, or the finish of a zombie on the floor within
  KEEP_R (mix_1's hold: it would rise during the dressing).
- `group`: three or more standing within DANGER_R → a fight (one within KEEP_R, or no refuge: the stand), a retreat
  whose label names its refuge (never `kite_stance`), on the threat branch with its flee reason, or the dressing where
  it is due (the doctrine's order: a bleed is dressed before any retreat from zombies beyond KEEP_R).
- `door`: the nearest standing zombie within DANGER_R behind a door → the tick sends or holds a running action (its
  play's own, or the goal runner's under a strategic play), never a wait. (Within LISTED_R, as the tactician's
  doctrine-level replay reads it, a loot's goal runner holds one tick between its interact and its next step with a
  zombie behind a door at 10 tiles, E23: the runner's pace, no wait at a door.)
- `clear` (piece 1): the lone zombie binds (`rules.clear_due`) → a fight at it, or a guard's fight.
- `crawler` (piece 2): a crawler within KEEP_R, nothing standing within KEEP_R, no retreat running → a fight at a
  zombie on the floor within KEEP_R; and no tick dresses while a crawler lies within KEEP_R.

Each ring's situations are counted and the counts asserted (`SEEN`), so a ring that stops carrying one fails here.
The ring-specific readings: trial 4's 6073 is fought from the first tick the lone-zombie rule names it; trial 10's
crawler is finished by the `crawler` guard and never dressed beside."""
import json
import os

import pytest

from agent.base import gates_e as GE
from agent.base.actions import Actions
from agent.base.planner.mix_1 import rules as M
from agent.base.planner.policies import DANGER_R, KEEP_R
from agent.base.planner.survive import Survive
from agent.base.planner.tactician import decide as TD
from agent.base.planner.tactician import fallback as F
from agent.base.replay_decisions import ARTIFACTS, read_record
from agent.base.world import World

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNS = os.environ.get("PZT_RUNS") or os.path.join(REPO, "testing", "runs")
COMMITTED = ("f_goals_16-20261105-164332", "e_day_23-20261105-095110")
TRIALS = ("x_trial-tactician-20261105-221951", "x_trial-doctrine-20261105-231313")
TICK = 5           # the decider's every fifth frame (2 Hz, PLANNER_HZ)
DONE_S = 1.0       # wall seconds after which the stub ends an open action `done`
RETREAT_REFUGE = ("kite_door", "kite_shelter", "kite_building", "avoid_door", "avoid_shelter", "avoid_building")
SEEN = {           # the situations each ring carries at least (`situations`); the counts read at the package's
    # first green run: F15 lone 176, clear 126, bleed 468, group 6; E23 lone 171, clear 109, door 16, bleed 34, group
    # 14; trial 4 clear 161, lone 53; trial 10 lone 42, clear 40, crawler 21, group 4, bleed 2
    "f_goals_16-20261105-164332": {"lone": 1, "bleed": 1, "clear": 1, "group": 1},
    "e_day_23-20261105-095110": {"lone": 1, "bleed": 1, "clear": 1, "group": 1, "door": 1},
    "x_trial-tactician-20261105-221951": {"clear": 1, "lone": 1},
    "x_trial-doctrine-20261105-231313": {"crawler": 1, "group": 1, "bleed": 1, "lone": 1, "clear": 1},
}
IDLE_6073 = 6073     # trial 4: idle at 8.4 tiles for 79 s under the tactician (task-13-composition-read.md § 2)
CRAWLER_15465 = 15465   # trial 10: bit at 48.4, 50.5 and 63.4 s through the doctrine's Dress (ibid. § 3, group C)


def load(name):
    """The ring's decoded lines: a committed artifact's `state.log`, else a trial run's admin client's state logs."""
    if name in COMMITTED:
        return read_record(os.path.join(ARTIFACTS, name))[0]
    d = os.path.join(RUNS, name, "clients", "admin", "Lua", "pzagent", "admin")
    if not os.path.isdir(d):
        pytest.skip("trial run %s is not on this machine (%s)" % (name, RUNS))
    lines = GE.session_lines(d)[0]
    if not lines:
        pytest.skip("trial run %s: no state lines decode" % name)
    return lines


class StubTransport:
    def __init__(self):
        self.cmd_seq, self.sent = 0, []

    def send(self, cmd):
        self.cmd_seq = cmd["seq"]
        self.sent.append(cmd)


def situations(v):
    """The situations the masked view `v` carries (the module docstring)."""
    out = []
    s6 = F._standing(v, DANGER_R)
    if len(s6) == 1 and F.armed(v) and not M.dress_due(v) and not M.crawler_due(v):
        out.append("lone")
    if M.dress_due(v) and not F._standing(v, KEEP_R + TD.DRESS_MARGIN):
        out.append("bleed")
    if len(s6) >= 3:
        out.append("group")
    near = F._standing(v, DANGER_R)
    if near and near[0].get("line") == "door":
        out.append("door")
    if M.clear_due(v):
        out.append("clear")
    if M.crawler_due(v):
        out.append("crawler")
    return out


def replay(name, tmp_path):
    """(rows, ticks): each tick's decision line beside {sits, view, busy, crawler_near, floor_near}."""
    lines = load(name)
    clock = {"t": 0.0}
    w, tr = World(), StubTransport()
    acts = Actions(tr, clock=lambda: clock["t"])
    sv = Survive(w, acts, str(tmp_path / "decision.log"), lambda: clock["t"], control="mix_1")
    fi, ticks = 0, []
    for ln in lines:
        if ln["kind"] == "act":
            continue
        w.apply(ln)
        if ln["kind"] != "frame":
            continue
        fi += 1
        clock["t"] = ln["wallMs"] / 1000.0
        if fi % TICK:
            continue
        for a in acts.history + acts.postures:
            if a.state not in ("done", "failed", "rejected", "timeout") and clock["t"] - a.sent_wall >= DONE_S:
                a.state, a.ended_wall, a.result = "done", clock["t"], {}
        sv.tick(w, acts)
        t = sv.control_state["mix_1"]
        v = t._masked(t.view())
        cur = acts.current
        ticks.append({"sits": situations(v), "view": v, "busy": t.exec.busy() or (
                          cur is not None and cur.state not in ("done", "failed", "rejected", "timeout")),
                      "retreat": t.exec.play.play in ("kite", "avoid"),
                      "crawler_near": [z["id"] for z in M.crawlers(v, KEEP_R)],
                      "floor_near": [z["id"] for z in v["zombies"] if z["posture"] != "standing" and z["dist"] <= KEEP_R]})
    rows = [json.loads(x) for x in (tmp_path / "decision.log").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(ticks) > 100
    return rows, ticks, tr


@pytest.fixture(scope="module", params=COMMITTED + TRIALS)
def ring(request, tmp_path_factory):
    name = request.param
    return (name,) + replay(name, tmp_path_factory.mktemp(name[:12]))


def check(sit, row, tk):
    """The tick's line keeps the doctrine at situation `sit` (the module docstring)."""
    inp = row["inputs"]
    play, mx = inp["play"], inp["mix_1"]
    if sit == "lone":
        return play["type"] == "fight" and row["branch"] == "threat" and "flee" not in inp["branches"]["threat"]
    if sit == "bleed":
        return play["kind"] == "dress" or (play["type"] == "fight" and mx["target"] in tk["floor_near"])
    if sit == "group":
        if play["type"] == "fight" or (play["kind"] == "dress" and M.dress_due(tk["view"])):
            return True
        return play["kind"] in RETREAT_REFUGE and row["branch"] == "threat" and bool(inp["branches"]["threat"]["flee"])
    if sit == "door":
        return row["action"] is not None or tk["busy"]
    if sit == "clear":
        return play["type"] == "fight" and (mx["target"] == mx["clear"] or mx["piece"].startswith("guard."))
    if sit == "crawler":
        return tk["retreat"] or (play["type"] == "fight" and mx["target"] in tk["floor_near"])
    return True


def test_the_doctrine_and_the_two_pieces_hold_at_every_situation_the_ring_carries(ring):
    name, rows, ticks, _ = ring
    seen, bad = {}, []
    for row, tk in zip(rows, ticks):
        for sit in tk["sits"]:
            seen[sit] = seen.get(sit, 0) + 1
            if not check(sit, row, tk):
                bad.append((row["wall"], sit, row["inputs"]["mix_1"], row["inputs"]["tactician"].get("table")))
    print("%s: %s" % (name, seen))
    assert not bad, bad[:5]
    for sit, n in SEEN[name].items():
        assert seen.get(sit, 0) >= n, (sit, seen)


def test_no_tick_dresses_with_a_crawler_within_keep_r_and_none_sprints(ring):
    name, rows, ticks, tr = ring
    assert not [r["wall"] for r, tk in zip(rows, ticks) if r["inputs"]["play"]["kind"] == "dress" and tk["crawler_near"]]
    assert all(c["type"] != "steer" or c["args"].get("gait") != "sprint" for c in tr.sent)
    for r in rows:   # the line's contract: a piece on every tick, a retreat on the threat branch with its reason
        mx = r["inputs"]["mix_1"]
        assert mx["piece"] and mx["added"] == (mx["piece"] in ("rule.clear", "guard.crawler"))
        if r["inputs"]["play"]["type"] in ("kite", "avoid"):
            assert r["branch"] == "threat" and r["inputs"]["branches"]["threat"]["flee"]


def test_trial_4_s_idle_zombie_is_fought_from_the_first_tick_the_rule_names_it(tmp_path):
    rows, ticks, _ = replay(TRIALS[0], tmp_path)
    named = [r for r in rows if r["inputs"]["mix_1"]["clear"] == IDLE_6073]
    assert named, "6073 never named"
    first = named[0]["inputs"]["mix_1"]
    assert (first["piece"], first["started"], first["target"]) == ("rule.clear", True, IDLE_6073)
    left = [r["wall"] for r, tk in zip(rows, ticks) if "clear" in tk["sits"] and r["inputs"]["mix_1"]["clear"] ==
            IDLE_6073 and r["inputs"]["mix_1"]["target"] != IDLE_6073]
    assert not left, left[:5]


def test_trial_10_s_crawler_is_finished_by_the_guard_and_never_dressed_beside(tmp_path):
    rows, ticks, _ = replay(TRIALS[1], tmp_path)
    guard = [r for r in rows if r["inputs"]["mix_1"]["piece"] == "guard.crawler"]
    assert guard and {r["inputs"]["mix_1"]["target"] for r in guard} == {CRAWLER_15465}
    near = [(r, tk) for r, tk in zip(rows, ticks) if CRAWLER_15465 in tk["crawler_near"]]
    assert near and not [r["wall"] for r, _ in near if r["inputs"]["play"]["kind"] == "dress"]
