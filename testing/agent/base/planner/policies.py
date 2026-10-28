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

- `Fight`: one pinned target (Plan 23 Task 10): the zombie id given as `target=`, else the nearest by
  `world.nearest_zombie()` at the first `choose`, kept until it is dead or gone from the World, unreachable, or beyond
  `DISENGAGE_R` (10 tiles), and never swapped for a nearer one otherwise; dropped, the next `choose` pins again. Beyond
  `FIGHT_REACH` a `WalkTo` of its square at a run (the Lua's `walkTo` paths there, around walls), within it an
  `Attack` of its id once the line holds. The line check (ruling P23-K) answers run 1 swinging 103 attacks at a zombie
  behind a locked door: within reach the Fight reads `world.line_clear` from the player to the target over the map's
  blocked edges (a closed door or an intact window blocks, an open doorway does not); false, it walks once at a run to
  the square of `world.reachable_adjacent(target)` nearest the player, within REPOSITION_R (2.5 tiles) of the
  player by its centre, from whose centre the line is clear (`repositioned`), and a second blocked read, or no such
  square, marks the target unreachable and the next is tried. `reachable_adjacent` lists the squares open to the
  target, not to the player, and the radius is crow-fly, so it bounds the detour without excluding it: a square
  within 2.5 tiles may still lie across the wall the line crosses (`test_policies.walled_south`'s case at 2.5 tiles
  walks round a solid block). Ruling P23-R keeps the radius alone this plan: the base has no path search, and a
  walk that cannot reach the square fails or ends short, and the next choose's blocked read (the second, as
  `repositioned` holds) marks the target; cost if wrong, a short detour walked before the target is dropped.
  The line is read only when the map holds both end squares on the player's floor; over an unscanned end it is None
  and the swing goes ahead, left to the no-progress stall below. `why` logs `target`, `pinned`, `dist`, `approach`,
  `line` and `reposition` (the square chosen, else None), and `marked` when this choose marked a target. Two `attack`
  results in a row whose `attackStarted` is False force one approach walk before the next attack (a result that is
  not a dict, as a failed attack's null, neither counts nor resets). The stall clock is Plan 21's
  `out_of_reach_since`: started when the Fight is made and restarted by every `observe()` that reads no target or the
  target within `FIGHT_REACH`; `stalled` reads true once the target has been beyond `FIGHT_REACH` for more than
  `FIGHT_MAX_S` unbroken wall seconds (a knock-back for one tick restarts nothing old; the clock counts the unbroken
  time out of reach only). Within reach that clock is not the stall: run 1 (the whole-pass review's I2) swung 103
  attacks, every one `done` with `attackStarted` true, at zombie 32404 behind a locked door, its health 1.167 on all
  1530 frames listing it, and the out-of-reach clock restarted on every tick. The no-progress stall: `STALL_SWINGS`
  consecutive `done` attacks on one target with `attackStarted` true, read off `Actions`' ended records, whose
  target's health (the frame's `zombies[*].health` for its id) did not fall below the health at the streak's start,
  make that target unreachable for `UNREACHABLE_S` wall seconds: `nearest_zombie` skips it, so the Fight takes another
  target or, with none, sends nothing (Survive then flees, reason `unreachable`). A swing not started neither counts
  nor resets the streak; a fall, a new target or a target no frame lists restarts it. `unreachable` (id -> wall until)
  is passed in so a later Fight of the same planner keeps it. An attack ending `failed` for a walk reason
  (`STUCK_REASONS`) marks its target the same way.
- `Flee`: a `Steer` of `FLEE_S` seconds along the unit vector from the threats' centroid through the player (the
  `threats` list its caller passes, else every zombie the World holds), at a sprint when the nearest is within
  `SPRINT_R`, else a run; re-aimed on every end of its steer. A player standing on the centroid steers along +x.
- `Explore`: it scans per 10-tile place, spec § 6's "once at a new building or on request" read as the place
  grid: a `Scan(SCAN_R)` once per place (the player's square rounded half up to a `SCAN_R`-tile grid, kept in
  `scanned` from its send and dropped again when the scan ends other than `done`, so a pre-empted, timed-out or
  rejected scan is retried, and dropped when the World names the last scan's aid in `scans_dropped`, a job the Lua
  dropped after its `done` line (ruling S-32), so that place is scanned again), then a `WalkTo` at a walk to `world.unexplored_edge()`; no edge, no command. A walk
  that ends `failed` with a reason in `STUCK_REASONS` has its target marked in the World (`world.mark_stuck`), and
  `unexplored_edge` leaves it out for `STUCK_TTL_MIN` (60) game minutes, so it is never re-sent inside them (the
  whole-pass review's I4: run 1 re-sent a walk that failed `stuck` to the same edge 20 times).
- `LootHouse` (Plan 23 Task 11, P23-7, P23-8): at load level `LOOT_MAX_LEVEL` (1) or below an
  `Interact(x, y, "loot", want, maxWeight=cap)` at `world.nearest_unlooted(want)`, `want` one of `LOOT_WANTS`
  (`food`, `water`, `weapon`, `bandage`), set by the caller (the `Stock` and `LootBuilding` goals), and never `all`: Plan 22's loot of
  `all` took whole containers, one interact at level 2 lifting runs 1 and 2 to level 3 and 4. Any other want (None
  included) loots nothing. `cap` is the frame's `load.max` times `LOAD_RATIO_MAX` (1.0), the Lua's loot stopping
  before the carried weight would pass it; 0.0 (no cap) when `load.max` reads no positive number; logged as
  `why["cap"]`. The looted mark is per use (Task 11 fix 1): when the interact ends, done, failed, rejected or timed
  out, every container on its square holding an item of the loot's filter is marked looted for that use only
  (`world.mark_looted(key, use)`), so a counter looted for water is still looted for food later; except a `failed
  "superseded"`, which a newer send replaced before it ran (Plan 21 lost such a square for the session:
  `docs/reference/research-notes.md`, "A pre-empted loot's square is marked looted"), and a loot whose result carries
  `skipped > 0` (the cap left items), which marks nothing: its square waits in `capped` for that use until the
  frame's `load.weight` falls below its reading at that loot's end (a drop or a meal), so the bot never re-sends a
  loot that cannot fit, and `target(want)` (the container a loot would go to, which the goal layer's view reads too)
  leaves it out meanwhile; an unreadable weight keeps it waiting. `within` (Plan 23 Task 13), a set of container
  keys or None, keeps `target` to those keys: the `LootBuilding` goal sets it to its building's. The level
  guard stays the backstop, spec § 9 (1), "a policy stops looting before level 3": above LOOT_MAX_LEVEL it sends
  nothing (`why["hold"]`), and no loot is sent again until the level is back under 2. It never drops (Plan 23 Task 12):
  the drop is Survive's `load` branch, which at `DROP_AT` (3) or above sends `Drop` of `spare(world)`, the heaviest
  held item that is neither the wielded weapon's type, nor of use `weapon`, `food` or `water` by `world.by_use()` (a
  bottle the planner marked empty reads `other`, so it is dropped), one a decision, until the frame's level reads
  `DROP_TO` (2); Survive's flee sends one `spare()` drop of its own at `DROP_AT` (`survive.py`).

HEURISTIC: an item's use is `agent.base.items.use_of`: food and water off `data/food-items.json` (the dataset's food and
fluid containers), a weapon by `items.WEAPON_RX`'s fullType names, which is no game data (the dataset names no weapon).
"""
import math
import time

from agent.base.items import use_of
from agent.base.pza1 import Attack, Interact, Scan, Steer, WalkTo

DANGER_R = 6.0        # tiles: a zombie this close is a threat (Survive's threat branch; the night sends nothing)
FIGHT_REACH = 2.0     # tiles: a nearest zombie beyond this is walked to, within it attacked
FIGHT_MAX_S = 20.0    # wall seconds the target may stay beyond FIGHT_REACH before the fight reads stalled
DISENGAGE_R = 10.0    # tiles: a pinned target beyond this is dropped (and Survive's hold radius while a threat runs)
REPOSITION_R = 2.5    # tiles: a reposition square farther than this from the player is never walked to (P23-Q)
MISSES_TO_APPROACH = 2   # attack results in a row with attackStarted false before one approach walk
STALL_SWINGS = 3      # started swings in a row on one target that took no health before it reads unreachable
UNREACHABLE_S = 20.0  # wall seconds a no-progress target is skipped
FLEE_S = 3.0          # seconds a flee's steer runs before it is re-aimed
SPRINT_R = 2.0        # tiles: a nearest zombie within this is fled at a sprint
SCAN_R = 10           # tiles: the scan radius, and the grid a place is rounded to
LOOT_MAX_LEVEL = 1    # spec § 9 (1) "stops looting before level 3": a loot is sent only at load level 0-1
LOAD_RATIO_MAX = 1.0  # a loot fills to this times the frame's load.max (level 1 holds up to 1.25 of it, #3926)
LOOT_WANTS = ("food", "water", "weapon", "bandage")   # a loot's want and filter: one use, never `all` (P23-8)
DROP_AT = 3           # at this load level or above Survive's load branch drops (the heavy-load drain falls at 3) ...
DROP_TO = 2           # ... down to this level, and between the two neither drops nor loots
KEPT_USES = ("weapon", "food", "water")   # the uses a drop never takes
PREEMPTED = "superseded"   # the reason the Lua fails an action a newer send replaced
STUCK_REASONS = ("stuck", "no path", "no square")   # a walkTo failed for one of these: its target is remembered


def me_xy(world):
    me = world.me or {}
    return me.get("x") or 0.0, me.get("y") or 0.0


def me_floor(world):
    """The player's floor, the frame's `me.z` floored (0 when it reads no number); a zombie record carries no floor,
    so a zombie is read on the player's."""
    z = (world.me or {}).get("z")
    return int(math.floor(z)) if isinstance(z, (int, float)) and not isinstance(z, bool) else 0


def item_id_ok(iid):
    """An inventory key usable as a command's itemId: an int, not a bool."""
    return isinstance(iid, int) and not isinstance(iid, bool)


def target_id_ok(zid):
    """A zombie id a Fight can target: an int, not a bool (a nil read keys the zombie None); the one rule
    `world.nearest_zombie` and Survive's reachable-threat set share."""
    return isinstance(zid, int) and not isinstance(zid, bool)


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


def spare(world):
    """The id of the heaviest held item that is neither the wielded weapon's type nor of use weapon, food or water by
    `world.by_use()` (so a bottle marked empty is `other`, and spare), ties by the least id; else None. Survive's load
    branch and its flee drop it."""
    wielded = (world.weapon or {}).get("type")
    by_use = world.by_use()
    kept = {iid for use in KEPT_USES for iid in by_use[use]}
    best = None
    for iid, it in world.inventory.items():
        if not item_id_ok(iid) or iid in kept or (it.get("fullType") or "") == wielded:
            continue
        rank = (-(it.get("weight") or 0.0), iid)
        if best is None or rank < best:
            best = rank
    return best[1] if best else None


def blocked(unreachable, now):
    """The ids of `unreachable` (id -> wall until) still skipped at `now`."""
    return {zid for zid, until in unreachable.items() if until > now}


class Fight(Policy):
    def __init__(self, world, actions, clock=time.time, unreachable=None, target=None):
        super().__init__(world, actions, clock)
        self.out_of_reach_since = clock()   # the stall clock: since when the target has been out of reach
        self.misses = 0                     # attack results in a row with attackStarted false
        self.approach = False               # the next command is an approach walk
        self.unreachable = {} if unreachable is None else unreachable   # target id -> wall until it is skipped
        self.target = target                # the pinned zombie id, None until the first choose pins one
        self.repositioned = False           # the one reposition walk on the pinned target was sent
        self.no_progress = 0                # started swings in a row on `_streak_id` that took no health
        self._streak_id = None
        self._streak_h = None               # the target's health at the streak's start
        self._counted = None                # the last attack whose result was counted

    def blocked(self):
        return blocked(self.unreachable, self.clock())

    def _target_health(self, zid):
        z = self.world.zombies.get(zid)
        return None if z is None else z.get("health")

    def _mark_unreachable(self, zid):
        self.unreachable[zid] = self.clock() + UNREACHABLE_S
        if zid == self.target:
            self._unpin()

    def _unpin(self):
        self.target, self.repositioned = None, False

    def _swing_landed_nothing(self, zid):
        """Count one started swing on `zid` against its health at the streak's start; mark the target unreachable
        after STALL_SWINGS that took none."""
        h = self._target_health(zid)
        if zid != self._streak_id or h is None:
            self._streak_id, self._streak_h, self.no_progress = None, None, 0
            return
        if self._streak_h is None or h < self._streak_h:
            self._streak_h, self.no_progress = h, 0
            return
        self.no_progress += 1
        if self.no_progress >= STALL_SWINGS:
            self._mark_unreachable(zid)
            self._streak_id, self._streak_h, self.no_progress = None, None, 0

    def _pinned(self):
        """(id, zombie, dist) of the pinned target while it holds: it is dropped once dead or gone from the World,
        positionless, unreachable, or beyond DISENGAGE_R."""
        if self.target is None:
            return None
        z = self.world.zombies.get(self.target)
        if z is None or z.get("x") is None or z.get("y") is None or self.target in self.blocked():
            self._unpin()
            return None
        d = zdist(self.world, z)
        if d > DISENGAGE_R:
            self._unpin()
            return None
        return self.target, z, d

    def _nearest(self):
        nz = self.world.nearest_zombie(exclude=self.blocked())
        if nz is None or nz[1].get("x") is None or nz[1].get("y") is None:
            return None
        zid, z = nz
        return zid, z, zdist(self.world, z)

    def _target(self, pin):
        """The Fight's target: the pinned one while it holds, else the nearest reachable zombie, pinned when `pin`."""
        t = self._pinned() or self._nearest()
        if pin and t is not None and self.target != t[0]:
            self.target, self.repositioned = t[0], False
        return t

    def _line(self, z):
        """The line from the player to `z` (`world.line_clear`), None when the map lacks either end square: an
        unscanned end is never read as a wall, the swing then left to the no-progress stall."""
        me = self.world.me or {}
        a, b = (me.get("x"), me.get("y")), (z["x"], z["y"])
        if a[0] is None or a[1] is None:
            return None
        floor = me_floor(self.world)
        if any((int(math.floor(p[0])), int(math.floor(p[1])), floor) not in self.world.map for p in (a, b)):
            return None
        return self.world.line_clear(a, b)

    def _reposition(self, z):
        """The square to reposition to: of `world.reachable_adjacent` of the target's square (nearest the player
        first), the first within REPOSITION_R of the player (by its centre) from whose centre the line to the target
        is clear; None when none is. `reachable_adjacent` reads the squares open to the target, not to the player:
        the radius keeps a detour round a building out of the reflex (ruling P23-Q)."""
        floor = me_floor(self.world)
        mx, my = me_xy(self.world)
        for sq in self.world.reachable_adjacent((z["x"], z["y"]), floor):
            c = (sq[0] + 0.5, sq[1] + 0.5)
            if math.hypot(c[0] - mx, c[1] - my) > REPOSITION_R:
                break   # nearest the player first: every later square is as far or farther
            if self.world.line_clear(c, (z["x"], z["y"])):
                return sq
        return None

    def observe(self):
        t = self._target(pin=False)
        if t is None or t[2] <= FIGHT_REACH:
            self.out_of_reach_since = self.clock()
        a = self.last
        if a is None or a.type != "attack" or not self.actions.done(a) or a is self._counted:
            return
        self._counted = a
        if a.state == "failed" and a.reason in STUCK_REASONS:   # the approach walk could not queue (Minor 3)
            self._mark_unreachable(a.args.get("targetId"))
            return
        if not isinstance(a.result, dict):
            return
        if a.result.get("attackStarted") is False:
            self.misses += 1
            if self.misses >= MISSES_TO_APPROACH:
                self.approach = True
                self.misses = 0
        else:
            self.misses = 0
            if a.state == "done" and a.result.get("attackStarted") is True:
                self._swing_landed_nothing(a.args.get("targetId"))

    def fight_s(self):
        """Seconds the target has been out of reach (the stall clock)."""
        return self.clock() - self.out_of_reach_since

    def target_dist(self):
        """Tiles to the target the stall clock follows (the pinned one while it holds, else the nearest reachable),
        None with no target: Survive's stall guard reads the same zombie as the clock."""
        t = self._target(pin=False)
        return None if t is None else t[2]

    @property
    def stalled(self):
        return self.fight_s() > FIGHT_MAX_S

    def choose(self):
        cmd = self._choose()
        skipped = sorted(self.blocked(), key=str)
        if skipped:
            self.why["unreachable"] = skipped
        return cmd

    def _choose(self):
        t = self._target(pin=True)
        if t is None:
            self.why = {"target": None, "pinned": False}
            return None
        zid, z, d = t
        line = self._line(z) if d <= FIGHT_REACH else None
        self.why = {"target": zid, "pinned": True, "dist": d, "approach": self.approach, "line": line,
                    "reposition": None}
        if line is False:
            sq = None if self.repositioned else self._reposition(z)
            if sq is None:   # a second blocked read, or no clear square: the target is unreachable, the next tried
                self._mark_unreachable(zid)
                read = self.why
                cmd = self._choose()
                self.why = dict(read if self.why["target"] is None else self.why, marked=zid)
                return cmd
            self.repositioned = True
            self.why["reposition"] = list(sq)
            return WalkTo(sq[0], sq[1], "run")
        if self.approach or d > FIGHT_REACH:
            return WalkTo(int(z["x"]), int(z["y"]), "run")
        return Attack(zid)   # nearest_zombie yields int ids only (M7)

    def sent(self, cmd, action):
        if cmd.TYPE == "walkTo":
            self.approach = False
        elif cmd.TYPE == "attack" and cmd.targetId != self._streak_id:   # a new target: its streak starts here
            self._streak_id, self._streak_h, self.no_progress = cmd.targetId, self._target_health(cmd.targetId), 0


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
        self.scanned = set()   # the places scanned from, or with a scan still running
        self._scan = None      # (place, Action) of the last scan sent, until it ends
        self._walk = None      # ((x, y), Action) of the last walk sent, until it ends
        self._last = None      # (aid, place) of the last scan sent: its job may still be dropped after its done line

    def place(self):
        """The player's square on a uniform SCAN_R grid (half up, never Python's half-even round)."""
        mx, my = me_xy(self.world)
        return int(math.floor(mx / SCAN_R + 0.5)) * SCAN_R, int(math.floor(my / SCAN_R + 0.5)) * SCAN_R

    def observe(self):
        if self._walk is not None and self.actions.done(self._walk[1]):
            (x, y), a = self._walk
            self._walk = None
            if a.state == "failed" and a.reason in STUCK_REASONS:
                self.world.mark_stuck(x, y)
        if self._last is not None and self._last[0] in self.world.scans_dropped:
            self.scanned.discard(self._last[1])   # S-32: the job stopped short of its parts, the scan stays done
            self._last = None
        if self._scan is None or not self.actions.done(self._scan[1]):
            return
        place, a = self._scan
        self._scan = None
        if a.state != "done":
            self.scanned.discard(place)

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
            self._scan = (self.place(), action)
            self._last = (action.aid, self.place())
        elif cmd.TYPE == "walkTo":
            self._walk = ((cmd.x, cmd.y), action)


class LootHouse(Policy):
    def __init__(self, world, actions, clock=time.time, want=None):
        super().__init__(world, actions, clock)
        self.want = want        # one of LOOT_WANTS, set by the caller: the container's want and the loot's filter
        self.pending = []       # (x, y, z, Action) of each loot sent and not yet seen ended
        self.capped = {}        # (x, y, z, use) -> the carried weight when a loot there skipped items for the cap
        self.within = None      # a set of container keys a target is kept to (a LootBuilding goal's), None for any
        self._key = None        # the container the last choose picked

    def level(self):
        return (self.world.load or {}).get("level") or 0

    def cap(self):
        """The loot's maxWeight: the frame's load.max times LOAD_RATIO_MAX, 0.0 (no cap) when it reads no positive
        number."""
        m = (self.world.load or {}).get("max")
        ok = isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0
        return float(m) * LOAD_RATIO_MAX if ok else 0.0

    def weight(self):
        w = (self.world.load or {}).get("weight")
        return w if isinstance(w, (int, float)) and not isinstance(w, bool) else None

    def observe(self):
        still = []
        for x, y, z, a in self.pending:
            if not self.actions.done(a):
                still.append((x, y, z, a))
                continue
            if a.state == "failed" and a.reason == PREEMPTED:
                continue
            use = a.args.get("filter")
            skipped = a.result.get("skipped") if isinstance(a.result, dict) else None
            if isinstance(skipped, (int, float)) and not isinstance(skipped, bool) and skipped > 0:
                self.capped[(x, y, z, use)] = self.weight()   # the items left may fit once the load falls
                continue
            self.capped.pop((x, y, z, use), None)
            for key, c in self.world.containers.items():
                if key[:3] == (x, y, z) and any(use_of(i) == use for i in c["items"]):
                    self.world.mark_looted(key, use)
        self.pending = still

    def _waiting(self, want):
        """The container keys on a square whose loot for `want` skipped items for the cap, while the carried weight
        has not fallen below its reading at that loot's end (an unreadable weight on either side keeps waiting)."""
        now = self.weight()
        squares = {k[:3] for k, w in self.capped.items() if k[3] == want and (now is None or w is None or now >= w)}
        return {k for k in self.world.containers if k[:3] in squares}

    def target(self, want):
        """The container a loot for `want` would go to: `world.nearest_unlooted(want)` less the squares waiting on
        the cap, and kept to `within` when it is set; None for a want outside LOOT_WANTS."""
        if want not in LOOT_WANTS:
            return None
        exclude = self._waiting(want)
        if self.within is not None:
            exclude = exclude | {k for k in self.world.containers if k not in self.within}
        return self.world.nearest_unlooted(want, exclude=exclude)

    def choose(self):
        level = self.level()
        if level > LOOT_MAX_LEVEL:
            self.why = {"level": level, "hold": True}
            return None
        key = self.target(self.want)
        cap = self.cap()
        self._key = key
        self.why = {"level": level, "want": self.want, "container": list(key) if key else None, "cap": cap}
        if key is None:
            return None
        return Interact(int(key[0]), int(key[1]), "loot", self.want, maxWeight=cap)

    def sent(self, cmd, action):
        if cmd.TYPE == "interact":
            self.pending.append((self._key[0], self._key[1], self._key[2], action))
