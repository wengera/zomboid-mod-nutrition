"""mix_2 over recorded rings (Plan 31 Task 13; the build amendments' item 4, the common amendments' item 6): the two
committed rings F15 (`testing/artifacts/f_goals_16-20261105-164332/`) and E23 (`testing/artifacts/e_day_23-20261105-
095110/`), and three of round one's trial runs where this machine still has them (`testing/runs/` is per-machine and
gitignored, so each is skipped where absent): trial 2 (`x_trial-doctrine-20261105-221158`: D left the idle 9810 at 8
tiles for 120 s), trial 4 (`x_trial-tactician-20261105-221951`: T left the idle 6073 at 8.4 tiles for 79 s) and trial
10 (`x_trial-doctrine-20261105-231313`: the crawler 15465 bit through D's dress, the death). The state lines are decoded
as live (`FileTransport`: `pza1.decode` and `merge_delta`; `replay_decisions.read_record` for the artifacts, the run's
admin state logs copied beside its `decision.log` for a trial run) and applied to one World up to each decision line's
wall. The replay is open loop: it checks mix_2's decisions at the situations the rings recorded, never an outcome.

Read at every line (`situation.read` with a fresh memory, the seek's reach `seek.Reach` over the replayed World):
- a standing zombie free within SWING_GUARD_R: the first want is the P0 Fight at the nearest standing one (`swing`, or
  `hit` under a hit reaction);
- one standing aware zombie within ENGAGE_R, no other within GROUP_R, armed: never an avoid; a fight or a dress first;
- a bleeding part with nothing standing or crawling within KEEP_R and something to dress it with: the dress first, or
  a P0 finish of a fallen zombie within FIGHT_REACH (T's `fallen` guard);
- a bleeding part with a crawler within KEEP_R: never the dress first, a P0 Fight first (trial 10's death mode);
- three or more standing aware within GROUP_R, not strung out, armed: an avoid toward a named refuge or the stand;
- a zombie behind a door within DOOR_R with no free aware zombie near: the door decided;
- exactly one standing zombie listed within ENGAGE_R, idle, free and reachable, armed, nothing bleeding: the Fight at
  it (`seek`, or a guard or `reach` once it is near), never the order;
- two or more standing listed within ENGAGE_R, none aware, none within KEEP_R and no fallen one within DOWNED_R: no
  Fight wanted (none sought).
And the whole decider (`Survive(control="mix_2")`) open loop at 2 Hz over the same frames, its sends through a stub
transport ended `done` after DONE_S: no tick raises, every line carries `inputs.mix_2` with its piece, the arbiter
switches no intent for another of the same priority (`assess.line_switches`), a Fight's line is on the threat branch
(and no line a string's `inputs.play`),
no sprint is sent, and no tick runs a Dress with a standing or crawling zombie free within KEEP_R."""
import glob
import json
import os
import shutil
import tempfile

import pytest

from agent.base.actions import Actions
from agent.base.planner import care as C
from agent.base.planner.doctrine.situation import Memory, aware, bleeding_parts
from agent.base.planner.door_held import portal_between
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2 import situation as SI
from agent.base.planner.mix_2.assess import line_switches
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.mix_2.seek import Reach
from agent.base.planner.policies import line_to, on_floor, on_room, zdist
from agent.base.planner.survive import Survive
from agent.base.replay_decisions import ARTIFACTS, read_record
from agent.base.transport.files import FileTransport
from agent.base.world import World, me_xy

RINGS = ("f_goals_16-20261105-164332", "e_day_23-20261105-095110")
TRIALS = ("x_trial-doctrine-20261105-221158", "x_trial-tactician-20261105-221951", "x_trial-doctrine-20261105-231313")
SEEK_TRIALS = TRIALS[:2]      # the idle zombie left 120 s and 79 s: each carries the seek
CRAWLER_TRIAL = TRIALS[2]     # the crawler at the dress
TICK = 5           # the decider's every fifth frame (2 Hz)
DONE_S = 1.0       # wall seconds after which the stub ends an open action `done`
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_dir(run):
    """The trial run's folder on this machine (`$PZT_RUNS`, else `testing/runs/` under this tree or any tree it sits
    in: a worktree lives inside the main checkout), else None."""
    roots = [os.environ.get("PZT_RUNS")] + [os.path.join(p, "testing", "runs") for p in _parents(REPO)]
    for root in roots:
        if root and os.path.isdir(os.path.join(root, run)):
            return os.path.join(root, run)
    return None


def _parents(p):
    out = [p]
    while os.path.dirname(p) != p:
        p = os.path.dirname(p)
        out.append(p)
    return out


def record(ring):
    """(state lines decoded as live, decision rows) of a committed ring or a trial run, else None (absent)."""
    if ring in RINGS:
        return read_record(os.path.join(ARTIFACTS, ring))
    root = run_dir(ring)
    if root is None:
        return None
    logs = glob.glob(os.path.join(root, "clients", "admin", "Lua", "pzagent", "*", "state*.log"))
    if not logs:
        return None
    with tempfile.TemporaryDirectory() as d:
        for p in logs:
            shutil.copy(p, d)
        lines = list(FileTransport(d).lines())
    with open(os.path.join(root, "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(ln) for ln in f if ln.strip()]
    return lines, rows


def situations(lines, rows):
    """[(decision line, World, wall)]: one World advanced to each line's wall, yielded in turn."""
    w = World()
    i = 0
    for k, row in enumerate(rows, 1):
        wall = row["wall"]
        while i < len(lines) and lines[i].get("wallMs", 0) / 1000.0 <= wall:
            w.apply(lines[i])
            i += 1
        if w.me is not None and w.me.get("x") is not None:
            yield k, w, wall


# ---------------------------------------------------------------- the situations, read off the frame
def _free(w, z):
    me = me_xy(w)
    return line_to(w, z) is not False and portal_between(w, me, (z["x"], z["y"]), w.marked_doors(),
                                                         on_room(w)) is None


def _listed(w):
    return sorted(((zdist(w, z), zid, z) for zid, z in w.zombies.items()
                   if z.get("x") is not None and z.get("y") is not None), key=lambda e: (e[0], repr(e[1])))


def _standing(w, r, free=True):
    return [e for e in _listed(w) if not on_floor(e[2]) and e[0] <= r and (not free or _free(w, e[2]))]


def _crawling(w, r):
    return [e for e in _listed(w) if e[2].get("crawler") is True and e[0] <= r and _free(w, e[2])]


def swing_near(w):
    return _standing(w, K.SWING_GUARD_R)


def lone_armed(w):
    near = [e for e in _standing(w, DK.ENGAGE_R) if aware(e[2])]
    return w.weapon is not None and len(near) == 1 and len([e for e in near if e[0] <= DK.GROUP_R]) <= 1


def _material(w):
    parts = bleeding_parts(w)
    return parts and C.dress_pick(w, parts[0].get("bleedingTime") or 0.0, dirty_ok=True) is not None


def bleeding_clear(w):
    return bool(_material(w)) and not _standing(w, K.KEEP_R) and not _crawling(w, K.KEEP_R)


def bleeding_crawler(w):
    return bool(_material(w)) and bool(_crawling(w, K.KEEP_R))


def group(w):
    g = [e[0] for e in _standing(w, DK.GROUP_R) if aware(e[2])]
    return w.weapon is not None and len(g) >= DK.GROUP_N and g[1] - g[0] < DK.STRING_GAP


def door_held(w):
    me = me_xy(w)
    behind = [e for e in _listed(w) if e[0] <= DK.DOOR_R
              and portal_between(w, me, (e[2]["x"], e[2]["y"]), w.marked_doors(), on_room(w)) is not None]
    return bool(behind) and not [e for e in _standing(w, DK.ENGAGE_R) if aware(e[2])]


def lone_idle(w, reach):
    """The one standing zombie listed within ENGAGE_R (free or not), idle, free and reachable, armed, nothing
    bleeding, else None."""
    near = _standing(w, K.SEEK_R, free=False)
    if w.weapon is None or len(near) != 1 or aware(near[0][2]) or not _free(w, near[0][2]) or bleeding_parts(w):
        return None
    return near[0][1] if reach.engageable(near[0][1], near[0][2]) else None


def idle_pair(w):
    near = _standing(w, K.SEEK_R, free=False)
    fallen = [e for e in _listed(w) if on_floor(e[2]) and e[0] <= DK.DOWNED_R]
    return (len(near) >= 2 and not any(aware(e[2]) for e in near) and not any(e[0] <= K.KEEP_R for e in near)
            and not fallen and not door_held(w))


SITUATIONS = ("swing", "lone", "bleed", "crawler", "group", "door", "seek", "pair")


def read_ring(ring):
    got = record(ring)
    if got is None:
        pytest.skip("%s is not on this machine (testing/runs/ is per-machine)" % ring)
    found = {s: [] for s in SITUATIONS}
    bad = []
    reach = None
    for k, w, wall in situations(*got):
        if reach is None:
            reach = Reach(w, lambda: wall)
        reach.clock = (lambda t: (lambda: t))(wall)
        ws = SI.read(w, Memory(), wall, reach.engageable)
        kinds = [x.kind for x in ws]
        first = (ws[0].kind, ws[0].p, SI.piece_of(ws[0]), ws[0].target)
        s = swing_near(w)
        if s:
            found["swing"].append(k)
            if first[:2] != ("fight", K.P_GUARD) or first[2] not in ("swing", "hit") or (
                    first[2] == "swing" and first[3] != s[0][1]):
                bad.append(("swing", k, first))
        if lone_armed(w):
            found["lone"].append(k)
            if "avoid" in kinds or kinds[0] not in ("fight", "dress"):
                bad.append(("lone", k, kinds))
        if bleeding_clear(w):
            found["bleed"].append(k)
            if kinds[0] != "dress" and first[2] != "fallen":
                bad.append(("bleed", k, first))
        if bleeding_crawler(w):
            found["crawler"].append(k)
            if kinds[0] == "dress" or first[1] != K.P_GUARD:
                bad.append(("crawler", k, first))
        if group(w):
            found["group"].append(k)
            a = next((x for x in ws if x.kind == "avoid"), None)
            stand = next((x for x in ws if x.kind == "fight" and x.why.get("stand")), None)
            ok = (a is not None and a.target.get("kind") in DK.REFUGE_KINDS) or stand is not None or \
                first[2] in K.GUARD_PIECES + ("reach",)
            if not ok or kinds[0] not in ("dress", "avoid", "fight"):
                bad.append(("group", k, kinds))
        if door_held(w):
            found["door"].append(k)
            d = next((x for x in ws if x.kind == "door"), None)
            if (d is None or d.target["decision"] not in ("stance_open", "leave")) and kinds[0] != "fight":
                bad.append(("door", k, kinds))
        z = lone_idle(w, reach)
        if z is not None:
            found["seek"].append(k)
            if first[0] != "fight" or first[3] != z or first[2] not in ("seek", "reach") + K.GUARD_PIECES:
                bad.append(("seek", k, first))
        if idle_pair(w):
            found["pair"].append(k)
            if "fight" in kinds:
                bad.append(("pair", k, first))
    return {"ring": ring, "found": found, "bad": bad}


@pytest.fixture(scope="module", params=RINGS + TRIALS)
def ring(request):
    return read_ring(request.param)


def test_mix_2_s_doctrine_holds_at_every_recorded_situation(ring):
    assert ring["bad"] == [], ring["bad"][:5]


def test_the_committed_rings_carry_a_lone_chaser_and_a_bleed(ring):
    if ring["ring"] in RINGS:
        assert ring["found"]["lone"] and ring["found"]["bleed"], {k: len(v) for k, v in ring["found"].items()}


def test_the_trials_carry_the_idle_zombie_mix_2_seeks_and_the_crawler_at_the_dress(ring):
    """Trials 2 and 4 left one idle zombie listed for 120 s and 79 s: mix_2 seeks it from their first lines; trial 10's
    crawler lay within KEEP_R of a bleeding character: mix_2's first want is a P0 Fight, never the dress."""
    f = ring["found"]
    if ring["ring"] in SEEK_TRIALS:
        assert len(f["seek"]) >= 20, len(f["seek"])
    if ring["ring"] == CRAWLER_TRIAL:
        assert f["crawler"] and f["swing"], {k: len(v) for k, v in f.items()}


def test_the_rings_between_them_carry_a_group_a_door_and_an_idle_pair():
    seen = {"group": 0, "door": 0, "pair": 0}
    for ring in RINGS:
        f = read_ring(ring)["found"]
        for k in seen:
            seen[k] += len(f[k])
    assert seen["group"] > 0 and seen["door"] > 0 and seen["pair"] > 0, seen


# ---------------------------------------------------------------- the whole decider, open loop
class StubTransport:
    """The commands sent, in order; no file."""

    def __init__(self):
        self.cmd_seq, self.sent = 0, []

    def send(self, cmd):
        self.cmd_seq = cmd["seq"]
        self.sent.append(cmd)


@pytest.fixture(scope="module", params=RINGS + (CRAWLER_TRIAL,))
def loop(request, tmp_path_factory):
    got = record(request.param)
    if got is None:
        pytest.skip("%s is not on this machine (testing/runs/ is per-machine)" % request.param)
    lines, _ = got
    tmp = tmp_path_factory.mktemp("mix2loop")
    clock = {"t": 0.0}
    w, tr = World(), StubTransport()
    acts = Actions(tr, clock=lambda: clock["t"])
    sv = Survive(w, acts, str(tmp / "decision.log"), lambda: clock["t"], control="mix_2")
    fi, ticks, dress_near = 0, 0, []
    for ln in lines:
        if ln["kind"] == "act":
            continue   # the record's own aids: never this replay's
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
        ticks += 1
        it = sv.control_state["mix_2"].arbiter.current
        if it.kind == "dress" and (_standing(w, K.KEEP_R) or _crawling(w, K.KEEP_R)) and it.end is None:
            dress_near.append(ticks)
    rows = [json.loads(x) for x in (tmp / "decision.log").read_text(encoding="utf-8").splitlines()]
    return {"ring": request.param, "rows": rows, "ticks": ticks, "sent": tr.sent, "dress_near": dress_near}


def test_the_decider_runs_open_loop_and_names_its_piece_on_every_line(loop):
    rows = loop["rows"]
    assert len(rows) == loop["ticks"] > 100
    pieces = {}
    for r in rows:
        m = r["inputs"]["mix_2"]
        assert m["piece"] in K.PIECES and "doctrine" not in r["inputs"] and "play" not in r["inputs"], m   # no string
        pieces[m["piece"]] = pieces.get(m["piece"], 0) + 1
        if m["intent"] == "fight":
            assert r["branch"] == "threat" and r["inputs"]["intent"]["kind"] == "fight", r
    assert any(p in pieces for p in K.GUARD_PIECES + K.FIGHT_PIECES), pieces


def test_the_arbiter_switches_no_intent_for_one_of_the_same_priority(loop):
    assert line_switches(loop["rows"]) == 0
    assert len({r["inputs"]["mix_2"]["n"] for r in loop["rows"]}) > 1


def test_no_sprint_and_no_dress_with_a_zombie_standing_or_crawling_within_keep_r(loop):
    assert all(c["args"].get("gait") != "sprint" for c in loop["sent"])
    assert loop["dress_near"] == [], loop["dress_near"][:5]
