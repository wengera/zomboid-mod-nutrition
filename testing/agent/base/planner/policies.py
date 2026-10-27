"""The multi-step policies (Plan 22 Task 10, spec § 3): fight, flee, explore and loot-house, each a Python machine over
the Lua's one-step skills, sending typed commands through `Actions` and reading the `World`.

One action at a time. A policy's `step()` returns the `Action` it sent, or None: it sends nothing while its own last
action is `actions.current` (sent, accepted or in progress), and decides again once that action reads a terminal
state (`done`, `failed`, `rejected`, `timeout`) or another sender's action replaced it. `step()` is `observe()` (the
policy's bookkeeping from the World and its last action's end), then `choose()` (the next command, or None) and
`send(cmd)`; `survive.Survive` calls the three apart so its cooldown can pass a choice over before it is sent. Every
command is validated by `Actions.send` against the schema's `ACTION_ARGS` (a TypeError is a policy bug). A policy
never reads `cmd.txt` or the state lines: its driver pumps the transport's lines into the World and Actions first.
`why` is the policy's own inputs to its last choice, logged by Survive.

Distances are tiles from the frame's `me` to a zombie's `x, y` (the World's last sighting), so a zombie kept within
`ZOMBIE_TTL_S` but missing from the latest frame is measured from where the player is now.

- `Fight`: the nearest zombie by `world.nearest_zombie()`; beyond `FIGHT_REACH` a `WalkTo` of its square at a run
  (the Lua's `walkTo` paths there), within it an `Attack` of its id. Two `attack` results in a row whose
  `attackStarted` is False force one approach walk before the next attack (a result that is not a dict, as a
  failed attack's null, neither counts nor resets). The stall clock is Plan 21's `out_of_reach_since`: started when
  the Fight is made and restarted by every `observe()` that reads no zombie or the nearest within `FIGHT_REACH`;
  `stalled` reads true once the nearest has been beyond `FIGHT_REACH` for more than `FIGHT_MAX_S` unbroken wall
  seconds (a knock-back for one tick restarts nothing old; the clock counts the unbroken time out of reach only).
- `Flee`: a `Steer` of `FLEE_S` seconds along the unit vector from the threats' centroid through the player (the
  `threats` list its caller passes, else every zombie the World holds), at a sprint when the nearest is within
  `SPRINT_R`, else a run; re-aimed on every end of its steer. A player standing on the centroid steers along +x.
- `Explore`: a `Scan(SCAN_R)` once per place (the player's square rounded to `SCAN_R` tiles, kept in `scanned` when
  the scan is sent), then a `WalkTo` at a walk to `world.unexplored_edge()`; no edge, no command.
- `LootHouse`: below load level `LOAD_STOP` an `Interact(x, y, "loot", want)` at `world.nearest_unlooted(want)` (any
  container for `want="all"`), every container on that square marked looted when the interact ends, done, failed,
  rejected or timed out, except a `failed "superseded"`, which a newer send replaced before it ran (Plan 21 lost such
  a square for the session: `docs/reference/research-notes.md`, "A pre-empted loot's square is marked looted"). At
  level `LOAD_STOP` or above (spec § 9 (1): the heavy-load drain falls at level 3) it never loots: it sends `Drop` of
  the heaviest held item that is neither the wielded weapon's type, nor a `WEAPON_RX` name, nor food or water by
  `FOOD_RX`/`WATER_RX`, one a decision, until the frame's level reads 2 or less; with nothing to drop, no command.

HEURISTIC: WEAPON_RX names the weapons a survivor keeps by fullType, as FOOD_RX and WATER_RX guess food and drink
(`agent.base.world`); none is game data.
"""
import math
import re
import time

from agent.base.pza1 import Attack, Drop, Interact, Scan, Steer, WalkTo
from agent.base.world import FOOD_RX, WATER_RX

FIGHT_REACH = 2.0     # tiles: a nearest zombie beyond this is walked to, within it attacked
FIGHT_MAX_S = 20.0    # wall seconds the nearest may stay beyond FIGHT_REACH before the fight reads stalled
MISSES_TO_APPROACH = 2   # attack results in a row with attackStarted false before one approach walk
FLEE_S = 3.0          # seconds a flee's steer runs before it is re-aimed
SPRINT_R = 2.0        # tiles: a nearest zombie within this is fled at a sprint
SCAN_R = 10           # tiles: the scan radius, and the grid a place is rounded to
LOAD_STOP = 3         # the heavy-load level at which looting stops and dropping starts
PREEMPTED = "superseded"   # the reason the Lua fails an action a newer send replaced
WEAPON_RX = re.compile(r"\.(BaseballBat|Hammer|Axe|Crowbar|Knife|Pan|Pistol|Shotgun|Rifle)")


def me_xy(world):
    me = world.me or {}
    return me.get("x") or 0.0, me.get("y") or 0.0


def zdist(world, z):
    """Tiles from the player to a zombie's last seen square."""
    mx, my = me_xy(world)
    return math.hypot(z["x"] - mx, z["y"] - my)


class Policy:
    """One action at a time: see the module docstring."""

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.last = None      # the last Action this policy sent
        self.why = {}

    def busy(self):
        """True while this policy's last action is the current one and not yet terminal."""
        return self.last is not None and self.actions.current is self.last

    def observe(self):
        """Bookkeeping from the World and the last action's end; called every tick, idempotent."""

    def choose(self):
        """The next command, or None; called only when not busy."""
        raise NotImplementedError

    def sent(self, cmd, action):
        """Bookkeeping once `cmd` went out as `action`."""

    def send(self, cmd):
        action = self.actions.send(cmd)
        self.last = action
        self.sent(cmd, action)
        return action

    def step(self):
        self.observe()
        if self.busy():
            return None
        cmd = self.choose()
        return None if cmd is None else self.send(cmd)


class Fight(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.out_of_reach_since = clock()   # the stall clock: since when the nearest has been out of reach
        self.misses = 0                     # attack results in a row with attackStarted false
        self.approach = False               # the next command is an approach walk
        self._counted = None                # the last attack whose result was counted

    def _nearest(self):
        nz = self.world.nearest_zombie()
        if nz is None or nz[1].get("x") is None or nz[1].get("y") is None:
            return None
        zid, z = nz
        return zid, z, zdist(self.world, z)

    def observe(self):
        near = self._nearest()
        if near is None or near[2] <= FIGHT_REACH:
            self.out_of_reach_since = self.clock()
        a = self.last
        if a is None or a.type != "attack" or not self.actions.done(a) or a is self._counted:
            return
        self._counted = a
        if not isinstance(a.result, dict):
            return
        if a.result.get("attackStarted") is False:
            self.misses += 1
            if self.misses >= MISSES_TO_APPROACH:
                self.approach = True
                self.misses = 0
        else:
            self.misses = 0

    def fight_s(self):
        """Seconds the nearest has been out of reach (the stall clock)."""
        return self.clock() - self.out_of_reach_since

    @property
    def stalled(self):
        return self.fight_s() > FIGHT_MAX_S

    def choose(self):
        near = self._nearest()
        if near is None:
            self.why = {"target": None}
            return None
        zid, z, d = near
        self.why = {"target": zid, "dist": d, "approach": self.approach}
        if self.approach or d > FIGHT_REACH:
            return WalkTo(int(z["x"]), int(z["y"]), "run")
        return Attack(int(zid))

    def sent(self, cmd, action):
        if cmd.TYPE == "walkTo":
            self.approach = False


class Flee(Policy):
    def __init__(self, world, actions, clock=time.time, threats=None):
        super().__init__(world, actions, clock)
        self.threats = threats   # the zombies to flee; None: every zombie the World holds

    def choose(self):
        ts = self.threats if self.threats is not None else list(self.world.zombies.values())
        ts = [z for z in ts if z.get("x") is not None and z.get("y") is not None]
        if not ts:
            self.why = {"centroid": None}
            return None
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for z in ts) / len(ts)
        cy = sum(z["y"] for z in ts) / len(ts)
        vx, vy = mx - cx, my - cy
        n = math.hypot(vx, vy)
        if n == 0.0:
            vx, vy, n = 1.0, 0.0, 1.0
        near = min(zdist(self.world, z) for z in ts)
        gait = "sprint" if near <= SPRINT_R else "run"
        self.why = {"centroid": [cx, cy], "nearest": near}
        return Steer(vx / n, vy / n, FLEE_S, gait)


class Explore(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.scanned = set()   # the places scanned from

    def place(self):
        mx, my = me_xy(self.world)
        return int(round(mx / SCAN_R)) * SCAN_R, int(round(my / SCAN_R)) * SCAN_R

    def choose(self):
        place = self.place()
        if place not in self.scanned:
            self.why = {"scanAt": list(place)}
            return Scan(SCAN_R)
        edge = self.world.unexplored_edge()
        self.why = {"edge": list(edge) if edge else None}
        if edge is None:
            return None
        return WalkTo(edge[0], edge[1], "walk")

    def sent(self, cmd, action):
        if cmd.TYPE == "scan":
            self.scanned.add(self.place())


class LootHouse(Policy):
    def __init__(self, world, actions, clock=time.time, want="all"):
        super().__init__(world, actions, clock)
        self.want = want        # "food", "water" or "all": the container's want and the loot's filter
        self.pending = []       # (x, y, z, Action) of each loot sent and not yet seen ended
        self._key = None        # the container the last choose picked

    def level(self):
        return (self.world.load or {}).get("level") or 0

    def observe(self):
        still = []
        for x, y, z, a in self.pending:
            if not self.actions.done(a):
                still.append((x, y, z, a))
                continue
            if a.state == "failed" and a.reason == PREEMPTED:
                continue
            for key in [k for k in self.world.containers if k[:3] == (x, y, z)]:
                self.world.mark_looted(key)
        self.pending = still

    def spare(self):
        """The id of the heaviest held item that is neither a weapon nor food or water, else None."""
        wielded = (self.world.weapon or {}).get("type")
        best = None
        for iid, it in self.world.inventory.items():
            ft = it.get("fullType") or ""
            if not isinstance(iid, int) or isinstance(iid, bool):
                continue
            if ft == wielded or WEAPON_RX.search(ft) or FOOD_RX.search(ft) or WATER_RX.search(ft):
                continue
            rank = (-(it.get("weight") or 0.0), iid)
            if best is None or rank < best:
                best = rank
        return best[1] if best else None

    def choose(self):
        level = self.level()
        if level >= LOAD_STOP:
            iid = self.spare()
            self.why = {"level": level, "drop": iid}
            return None if iid is None else Drop(iid)
        key = self.world.nearest_unlooted(None if self.want == "all" else self.want)
        self._key = key
        self.why = {"level": level, "want": self.want, "container": list(key) if key else None}
        if key is None:
            return None
        return Interact(int(key[0]), int(key[1]), "loot", self.want)

    def sent(self, cmd, action):
        if cmd.TYPE == "interact":
            self.pending.append((self._key[0], self._key[1], self._key[2], action))
