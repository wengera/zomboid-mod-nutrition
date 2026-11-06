"""The doctrine over two committed rings (Plan 31 Task 11, D; the task's common amendments, item 6): F15
(`testing/artifacts/f_goals_16-20261105-164332/`) and E23 (`testing/artifacts/e_day_23-20261105-095110/`), the state
lines decoded as live (`replay_decisions.read_record`: `FileTransport`, so every delta frame merged by
`pza1.merge_delta`) and applied to one World up to each decision line's wall, the doctrine's wants read at every line
(`situation.read`). The replay is open loop: it checks the doctrine's decisions at the situations the rings recorded,
never an outcome (the frames are the ladder's session, whatever the doctrine would have sent).

The doctrine asserted (the common amendments' item 5), at each line whose situation is the rule's:
- one standing aware zombie within ENGAGE_R in reach of a straight line, no other standing aware one within GROUP_R,
  a weapon in hand: never an avoid; a strike, a fight or (bleeding) a dress first;
- a bleeding part with no standing zombie within KEEP_R and something held or worn to dress it: the dress first;
- three or more standing aware zombies within GROUP_R, not strung out, armed: the avoid toward a named refuge, unless a
  strike or a dress came first;
- a zombie behind a door within DOOR_R with no free aware zombie near: the door decided (`stance_open` or `leave`), its
  first act a command or the leave's marks at once, never a wait;
and over each ring the arbiter (with the real intents, their acts read but never sent) switches no intent for another
of the same priority."""
import math
import os

import pytest

from agent.base.actions import Actions
from agent.base.planner import care as C
from agent.base.planner.doctrine import constants as K
from agent.base.planner.doctrine import situation as SI
from agent.base.planner.doctrine.arbiter import Arbiter
from agent.base.planner.doctrine.intents import INTENTS
from agent.base.planner.door_held import portal_between
from agent.base.planner.policies import KEEP_R, line_to, on_floor, on_room, zdist
from agent.base.replay_decisions import _Transport, read_record
from agent.base.world import World, me_xy

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts")
RINGS = ("f_goals_16-20261105-164332", "e_day_23-20261105-095110")


def situations(ring):
    """[(decision line, World, wall)] of the ring: the World advanced to each line's wall (every state line written
    at or before it applied), one World shared and yielded in turn (read it before the next)."""
    lines, rows = read_record(os.path.join(ART, ring))
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


def _standing_aware(w, r):
    return [z for z in w.zombies.values() if z.get("x") is not None and z.get("y") is not None and not on_floor(z)
            and SI.aware(z) and zdist(w, z) <= r and _free(w, z)]


def lone_armed(w):
    near = _standing_aware(w, K.ENGAGE_R)
    return w.weapon is not None and len(near) == 1 and len(_standing_aware(w, K.GROUP_R)) <= 1


def bleeding_clear(w):
    parts = SI.bleeding_parts(w)
    if not parts:
        return False
    standing = [z for z in w.zombies.values() if z.get("x") is not None and not on_floor(z) and zdist(w, z) <= KEEP_R]
    return not standing and C.dress_pick(w, parts[0].get("bleedingTime") or 0.0, dirty_ok=True) is not None


def group(w):
    g = sorted(zdist(w, z) for z in _standing_aware(w, K.GROUP_R))
    return w.weapon is not None and len(g) >= K.GROUP_N and g[1] - g[0] < K.STRING_GAP


def door_held(w):
    me = me_xy(w)
    behind = [z for z in w.zombies.values() if z.get("x") is not None and zdist(w, z) <= K.DOOR_R
              and portal_between(w, me, (z["x"], z["y"]), w.marked_doors(), on_room(w)) is not None]
    return bool(behind) and not _standing_aware(w, K.ENGAGE_R)


# ---------------------------------------------------------------- the open-loop context the intents read
class _Goals:
    current = None
    door_left = None


class _Sv:
    def __init__(self):
        self.goals = _Goals()


class Ctx:
    """What an intent reads (`assess.Doctrine`'s face) over a replayed World: no send ever goes."""

    def __init__(self, w):
        self.world = w
        self.actions = Actions(_Transport(), clock=self.now)
        self.wall = 0.0
        self.mem = SI.Memory()
        self.arbiter = Arbiter()
        self.sv = _Sv()
        self.retired = []

    @property
    def clock(self):
        return self.now

    def now(self):
        return self.wall

    def note_kill(self, zid):
        self.mem.dead[zid] = self.wall + K.SKIP_S

    def skip(self, zid):
        self.mem.skip[zid] = self.wall + K.SKIP_S

    def retire(self, m):
        pass


@pytest.fixture(scope="module", params=RINGS)
def ring(request):
    """{situation: [lines]} and the arbiter's run over the ring (`run`)."""
    found = {"lone": [], "bleed": [], "group": [], "door": []}
    bad = []
    ctx = None
    for k, w, wall in situations(request.param):
        if ctx is None:
            ctx = Ctx(w)
        ctx.wall = wall
        ws = SI.read(w, SI.Memory(), wall)
        kinds = [x.kind for x in ws]
        if lone_armed(w):
            found["lone"].append(k)
            if "avoid" in kinds or kinds[0] not in ("strike", "fight", "dress"):
                bad.append(("lone", k, kinds))
        if bleeding_clear(w):
            found["bleed"].append(k)
            if kinds[0] != "dress":
                bad.append(("bleed", k, kinds))
        if group(w):
            found["group"].append(k)
            a = next((x for x in ws if x.kind == "avoid"), None)
            if a is None or a.target is None or not a.target.get("label") or kinds[0] not in ("strike", "dress",
                                                                                                "avoid"):
                bad.append(("group", k, kinds))
        if door_held(w):
            found["door"].append(k)
            d = next((x for x in ws if x.kind == "door"), None)
            if d is None or d.target["decision"] not in ("stance_open", "leave") or not _door_acts(ctx, d):
                bad.append(("door", k, kinds))
        _arbiter_tick(ctx)
    return {"ring": request.param, "found": found, "bad": bad, "ctx": ctx}


def _door_acts(ctx, want):
    """The Door intent made for `want` acts at once: a command, or the leave's marks with its end (never a wait)."""
    ctx2 = Ctx(ctx.world)
    ctx2.wall = ctx.wall
    it = INTENTS["door"](ctx2, want)
    cmd = it.command()
    return cmd is not None or it.end == ("done", "leave")


def _arbiter_tick(ctx):
    """One tick of the arbiter with the real intents over the replayed World: the running and suspended intents'
    maneuvers read, the wants, the step, the running intent's command read (the order's never: its steps are the
    ladder's Survive), an intent that ended while it acted handing the tick on, as `assess.Doctrine.tick` does."""
    a = ctx.arbiter
    for it in (a.current, a.slot):
        if it is not None:
            it.observe()
    for _ in range(3):
        ws = SI.read(ctx.world, ctx.mem, ctx.wall)
        a.step(ws, lambda want, prev: INTENTS[want.kind](ctx, want, prev))
        if a.current.kind != "order":
            a.current.command()
        if a.current.end is None:
            break


def test_each_ring_carries_the_doctrine_s_situations(ring):
    f = ring["found"]
    assert f["lone"] and f["bleed"], {k: len(v) for k, v in f.items()}


def test_the_two_rings_carry_a_group_and_a_door_between_them():
    """F15 carries no door within DOOR_R; E23 carries three lines of one (its gate); both carry a group."""
    seen = {"group": 0, "door": 0}
    for ring in RINGS:
        for _, w, _ in situations(ring):
            seen["group"] += group(w)
            seen["door"] += door_held(w)
    assert seen["group"] > 0 and seen["door"] > 0, seen


def test_the_doctrine_holds_at_every_recorded_situation(ring):
    assert ring["bad"] == [], ring["bad"][:5]


def test_the_arbiter_switches_no_intent_for_one_of_the_same_priority_over_a_ring(ring):
    a = ring["ctx"].arbiter
    assert a.equal_switches == 0
    assert a.ends, "the arbiter ran no intent to its end over the ring"


def test_a_lone_zombie_is_never_avoided_whatever_the_health(ring):
    """The lone-armed lines, health read on each: the want never reads it (memory `stand-and-fight-dress-first`)."""
    assert ring["found"]["lone"]
    assert not [b for b in ring["bad"] if b[0] == "lone"]
