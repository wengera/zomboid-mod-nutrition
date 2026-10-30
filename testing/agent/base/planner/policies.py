"""The multi-step policies (Plan 22 Task 10, spec § 3): fight, flee, explore and loot-house, each a Python machine over
the Lua's one-step skills, sending typed commands through `Actions` and reading the `World`.

One action at a time. A policy's `step()` returns the `Action` it sent, or None: it sends nothing while its own last
action is `actions.current` (sent, accepted or in progress), and decides again once that action reads a terminal
state (`done`, `failed`, `rejected`, `timeout`) or another sender's action replaced it. `step()` is `observe()` (the
policy's bookkeeping from the World and its last action's end), then `choose()` (the next command, or None) and
`send(cmd)`; `survive.Survive` calls the three apart so its cooldown can pass a choice over before it is sent. A
walk or steer leg stays running under a bandage sent with `keepMoving` after it (PZA/1.5.3, ruling P24-R: the Lua
keeps the leg and rides the bandage beside it; ruling P24-U, Task 12 fix 1): `running` reads it so, and `busy` and the
Flee's leg reads go through it. Every
command is validated by `Actions.send` against the schema's `ACTION_ARGS` (a TypeError is a policy bug). A policy
never reads `cmd.txt` or the state lines: its driver pumps the transport's lines into the World and Actions first.
`why` is the policy's own inputs to its last choice, logged by Survive.

Distances are tiles from the frame's `me` to a zombie's `x, y` (the World's last sighting), so a zombie kept within
`ZOMBIE_TTL_S` but missing from the latest frame is measured from where the player is now.

- `Fight` and `Flee`: `planner/fight.py` and `planner/flee.py`, each module's docstring its record (moved out of this
  module at Plan 24 Task 36, a pure move); this module keeps the constants they read, the reads they share (the
  line, the heading, the pull's group, the way out's and the shelter's squares) and the `Policy` base, and names
  both classes for the frozen drivers that import them from here (`__getattr__`).
- `Explore`: it scans per 10-tile place, spec § 6's "once at a new building or on request" read as the place
  grid: a `Scan(SCAN_R)` once per place (the player's square rounded half up to a `SCAN_R`-tile grid, kept in
  `scanned` from its send and dropped again when the scan ends other than `done`, so a pre-empted, timed-out or
  rejected scan is retried, and dropped when the World names the last scan's aid in `scans_dropped`, a job the Lua
  dropped after its `done` line (ruling S-32), so that place is scanned again), then a `WalkTo` at a walk to
  `world.unexplored_edge()`; no edge, no
  command. A walk that ends `failed` with a reason in `STUCK_REASONS` has its target marked in the World
  (`world.mark_stuck`), and
  `unexplored_edge` leaves it out for `STUCK_TTL_MIN` (60) game minutes, so it is never re-sent inside them (the
  whole-pass review's I4: run 1 re-sent a walk that failed `stuck` to the same edge 20 times). Survival 4 (ruling
  P23-AP 1, E4's twelve walks from one square north of a locked gate): a walk failed `stuck` with the player moved
  under STUCK_MOVE is a stuck pair from its start square (`world.mark_stuck_pair`), a walk that moved or arrived ends
  the run (`clear_stuck_run`); at the STUCK_AREA_N-th pair in a row the player's place is dropped from `scanned` (the
  scan the goal source falls back to), and `unexplored_edge` then answers only a square in the open.
- `LootHouse` (Plan 23 Task 11, P23-7, P23-8): at load level `LOOT_MAX_LEVEL` (1) or below an
  `Interact(x, y, "loot", want, maxWeight=cap)` at `world.nearest_unlooted(want)`, `want` one of `LOOT_WANTS`
  (`food`, `water`, `weapon`, `bandage`), set by the caller (the `Stock` and `LootBuilding` goals), and never `all`:
  Plan 22's loot of
  `all` took whole containers, one interact at level 2 lifting runs 1 and 2 to level 3 and 4. Any other want (None
  included) loots nothing. `cap` is the frame's `load.max` times `LOAD_RATIO_MAX` (1.0), the Lua's loot stopping
  before the carried weight would pass it; 0.0 (no cap) when `load.max` reads no positive number; logged as
  `why["cap"]`. The looted mark is per use (Task 11 fix 1): when the interact ends done, or failed `no match`
  (`LOOT_MARKS`: nothing of the use there), every container on its square holding an item of the loot's filter is
  marked looted for that use only (`world.mark_looted(key, use)`), so a counter looted for water is still looted for
  food later; any other end (failed, rejected, timed out: Task 18 fix 1, the review's major 3, E7's eight loots failed
  `not adjacent` from outside a locked door) counts one failure on each such container (`fails`), the
  LOOT_FAILS_TO_PASS-th (2) marking it, so a container that really cannot be reached is tried twice; except a `failed
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

from agent.base.items import holds_use, use_of
from agent.base.pza1 import Interact, Scan, WalkTo
from agent.base.world import STUCK_AREA_N, STUCK_WALK_CAP, me_floor, me_xy

DANGER_R = 6.0        # tiles: a zombie this close is a threat (Survive's threat branch; the night sends nothing)
FIGHT_REACH = 2.0     # tiles: a nearest zombie beyond this is walked to, within it attacked
FIGHT_MAX_S = 20.0    # wall seconds the target may stay beyond FIGHT_REACH before the fight reads stalled
DISENGAGE_R = 10.0    # tiles: a pinned target beyond this is dropped (and Survive's hold radius while a threat runs)
ENGAGE_R = 9.0        # tiles: one or two zombies listed this near are sought (ruling P24-X, Plan 24 Task 18: E7 killed
                      # nothing in 227 game minutes, its goal walking on with a lone zombie listed at 7 to 10 tiles);
                      # Task 18 fix 1, the review's minor 8: a tile inside DISENGAGE_R, the band in which a fight holds
                      # but none is engaged, so a zombie idling at 10 tiles does not flap goal, fight, goal
REPOSITION_R = 2.5    # tiles: a reposition square farther than this from the player is never walked to (P23-Q)
REPOSITION_MIN = 1.2  # tiles: ... nor one whose centre is nearer than this, inside the Lua walk's DONE_R 1.0 (P23-AJ 5)
MISSES_TO_APPROACH = 2   # attack results in a row with attackStarted false before one approach walk
STALL_SWINGS = 3      # started swings in a row on one target that took no health before it reads unreachable
UNREACHABLE_S = 20.0  # wall seconds a no-progress target is skipped
SEEK_SWITCH_R = 0.5   # tiles: a seek re-pins to another zombie at least this much nearer than its target (Task 18 fix
                      # 1, the review's blocker: E7's 564 closed to 2.84 tiles while the seek was on 534 at 5.3; a
                      # judgment, the margin keeping two zombies at about one distance from flapping the pin)
SEEK_SKIP_S = 60.0    # wall seconds a target whose seek walk failed for a walk reason is skipped (Task 18 fix 1, the
                      # review's major 2, a judgment: three UNREACHABLE_S, so a zombie behind a gate is not walked at
                      # again every 20 s while the goal loots)
FLEE_S = 3.0          # seconds a flee's steer runs before it is re-aimed
NEAR_R = 2.0          # tiles: a held threat this near is never `ahead` of a heading (the cone and tube reads look
                      # beyond it: fix 2, T2); named SPRINT_R while the steer sprinted within it (P24-O renamed it)
SHELTER_FLEE_R = 25.0  # tiles: a flee runs to a known door whose approach square is this near (ruling P23-AG)
FLEE_GAIT = "run"     # every flee leg and walk's gait (P23-AG; ruling P24-O: the planner never sprints, #4296)
CORRIDOR_R = 2.0      # tiles: a zombie this near the line to a door's approach square, ahead, refuses it (fix 1, I1)
STEER_PROBE = 3.0     # tiles: a steer heading is clear when the map's line this far along it is (fix 1, I4)
STEER_TURNS = (0, 30, -30, 60, -60, 90, -90)   # degrees a blocked heading turns, nearest first
WIDE_TURNS = (120, -120, 150, -150, 180)         # ... then, with none of those clear, the rest of the circle (Task 18,
                                                 # the E7 write-up's T19.5: four legs ran into a known fence corner)
STEP_PROBE = 1.0      # tiles: the last resort's probe, a heading whose first tile crosses no known blocked edge
STUCK_MOVE = 0.5      # tiles: a steer leg that moved less is stuck, and the next turns off the away vector
AHEAD_R = 9.0         # tiles: a 3 s leg at about 3 tiles/s (E1's flee): a held threat this far ahead refuses a heading
AHEAD_CONE = 20.0     # degrees: ... within this cone of it (or in its CORRIDOR_R tube), beyond NEAR_R (fix 2, T2)
DOOR_CLEAR_R = 1.5    # tiles: no re-close is tried with a known zombie this near the door square's centre (fix 2)
EXIT_CLEAR_R = 1.5    # tiles: no exit is walked with a held threat this near its outside square or ahead on its
                      # straight line (the tube, `_in_tube`): P23-AJ fix 1, narrowed at P24-A fix 1 (3), never one at
                      # the player's back
WALK_STALL_S = 1.0    # wall seconds a flee walk may leave the player within STUCK_MOVE before it is dropped: the exit
                      # walk (P23-AJ fix 1, G2), a shelter step's walk while a held threat is within DANGER_R (P23-AM 2)
                      # and a running steer leg's stuck read (P23-AM fix 1, R1); one quantity (P24-A (g), the close
                      # review's M3: the old EXIT_STALL_S and STEP_STALL_S merged)
CORNERED_R = 1.5      # tiles: Survive's corner's trigger radius (P23-AJ 2)
STUCK_NEAR_R = 1.5    # tiles: a running leg unmoved WALK_STALL_S with a held threat this near is stuck (P23-AM fix 1,
                      # R1; split from CORNERED_R, P24-A (g), the close review's M4)
LISTED_R = 12.0       # tiles: the listing's edge, the frame's zombie list (#4268: E5's horde listed at 12 tiles):
                      # the `many` count (Survive) and a fight's look behind its target (P24-A (a), (b))
POINT_BLANK_R = 1.0   # tiles: a cornered Fight's target this near is swung at whatever its line reads (P23-AJ fix 1)
REPIN_MARGIN = 0.3    # tiles: the point-blank re-pin goes when the new zombie is at least this much nearer than the pin
                      # (or the pin beyond CORNERED_R): P24-A fix 1 (2), a ruling (F1's pin alternated at 0.18 apart)
BEHIND_MARGIN = 0.5   # tiles: a zombie is behind a fight's target only this much farther or more (P24-A fix 1 (5), a
                      # ruling: one beside the target, 0.16 tiles farther, is not behind it)
AIM_LEG_S = 2.0       # seconds one stance leg (`aim`) holds before the stance fight re-aims (ruling P24-G 1)
STAND_MAX_S = 20.0    # wall seconds a standing fight may go without its target's health falling (or a new target
                      # after a kill) before it closes on the target in the stance (`advance`; ruling P24-N: no
                      # stand-off, and no run)
KEEP_R = 2.5          # tiles: a target inside this and beyond FIGHT_REACH is backpedalled from; farther, the stance
                      # stands facing it and lets it come (ruling P24-N, superseding P24-M's band of FIGHT_REACH + 1)
KEEP_MARGIN = 0.25    # tiles: a running backpedal holds until its target is this far past KEEP_R, so the back and
                      # stand legs do not flap at the line (Task 12 fix 1, the review's major 1)
AIM_HOLD_S = 2.0      # seconds the Lua keeps a stance an attack swung from once nothing runs (K.AIM_HOLD_MS 2000,
                      # PZAgent_Stance.lua): an attack ended longer ago left the character out of the stance
STUCK_SKIP_DEG = 15.0  # degrees: after a stuck leg, no heading this near its heading is chosen again (fix 3, F4)
SCAN_R = 10           # tiles: the scan radius, and the grid a place is rounded to
LOOT_MAX_LEVEL = 1    # spec § 9 (1) "stops looting before level 3": a loot is sent only at load level 0-1
CLOTHING_HELD_N = 3   # unworn garments held at which `clothing` is no longer wanted (Task 24: the wear rule judges each
                      # garment once held; a judgment bounding the surplus the loot carries)
CLOTHING_LOOT_KG = 1.5   # kg a clothing loot may take per garment still wanted (review-t24 major 3; a judgment: a
                      # coat or boilersuit weighs about that), so a full wardrobe leaves the cap to the food
LOAD_RATIO_MAX = 1.0  # a loot fills to this times the frame's load.max (level 1 holds up to 1.25 of it, #3926)
LOOT_FAILS_TO_PASS = 2   # failed loots of one container for one use before it is passed (Task 18 fix 1, the review's
                         # major 3: as a door's DOOR_FAILS_TO_MARK; a failure is not an empty container)
LOOT_MARKS = ("no match",)   # the failed loot's reasons that mark at once: nothing of the use there
LOOT_WANTS = ("food", "water", "weapon", "bandage", "container", "clothing")   # a loot's want and filter: one use,
                      # never `all` (P23-8); `container` (an empty vessel, the Lua's filter since PZA/1.5.1) by P24-Y;
                      # `clothing` (the Lua's filter since PZA/1.6, Plan 24 Task 24; a build without `wear` never loots it)
DROP_AT = 3           # at this load level or above Survive's load branch drops (the heavy-load drain falls at 3) ...
DROP_TO = 2           # ... down to this level, and between the two neither drops nor loots
KEPT_USES = ("weapon", "food", "water")   # the uses a drop never takes
AIM_R = 12.0   # tiles: the Lua's K.AIM_R (PZAgent_Stance.lua), the farthest target an aim takes: beyond it the aim is refused `no target`
NO_TARGET = "no target"   # the Lua's refusal of an aim whose target is gone (Task 10 fix 2: not a stand-off)
PREEMPTED = "superseded"   # the reason the Lua fails an action a newer send replaced
RIDE_TYPES = ("walkTo", "steer")   # the legs a keepMoving bandage rides (PZA/1.5.3, ruling P24-R)
STUCK_REASONS = ("stuck", "no path", "no square")   # a walkTo failed for one of these: its target is remembered
SWING_TYPES = ("attack", "aim", "shove", "stomp")   # the Fight's sends whose result's `targetDead` is a kill (P24-Q)
STRAIN_SOFT = 10.0    # the frame's body.armPain at which a swing's damage starts to fall (divided by armPain / 10,
                      # #4370): the Fight prefers the stomp and the point-blank shove (ruling P24-AG); under it again
                      # the strain hold ends
STRAIN_HARD = 20.0    # ... at which the damage is halved: the Fight never swings (`arms_hurt`, P24-AP), and the
                      # threat branch reads the pain as the `wounded` reason, a lone target still sought (ruling P24-AT)
STIFF_HARD = 20.0     # the frame's `body.strain` (an arm's stiffness, #4369) at which the arms' hold starts on either
                      # arm (ruling P24-AT, superseding P24-AG's read of the pain: the health panel calls a part's
                      # stiffness minor under 20, #4369) ...
STIFF_SOFT = 5.0      # ... and under which, on both arms, it ends (the panel names a stiffness from 5, #4369)
ENDURANCE_T = 0.75    # the frame's stats.endurance at or under which the ENDURANCE moodle reads level 1 (#3926, #4076),
                      # whose first level halves every swing (#4371): the disengage of P24-AG
ENDURANCE_RELEASE = 0.80   # ... and above which that hold ends (review-t27: rest gives back 0.003-0.005 a game minute,
                           # a fight takes far more, so the edge alone flickered flee / one swing / flee)
TIRED_FIGHT_T = 0.6   # stats.fatigue at or above which no fight is sought or stood (ruling P24-AK; the first TIRED
                      # moodle, night.TIRED_T, halves every swing at its first level too, #4371)
SHOVE_R = 1.5         # tiles: the Lua's shove refuses a target beyond this (`too far`, PZAgent_Stance.lua K.SHOVE_R)
STAND_MIN_R = 0.61    # tiles: a standing zombie this near the player makes the engine's call shove it (the weapon's
                      # MinRange, #4372: the bat's 0.61, the bare hand's 0.6), so no shove or stomp of another is sent
                      # (ruling P24-AH; the frame carries no MinRange, the bat's the widest read)
SWING_SKIP_S = UNREACHABLE_S   # wall seconds a target whose shove or stomp the Lua refused or failed is not sent that
                               # skill again (the stomp's floor strike follows instead: ruling P24-AL)
KNOCK_READ_S = 2.0    # wall seconds a shove's `knockdown` true is waited on for the frame's `onFloor` (PZA/1.7.1, 9 fix
                      # 12: the result is read off the knocked-down state at the hit, onFloor follows about a second
                      # later; a judgment, two of those): the Fight sends nothing meanwhile and stomps on the first
                      # frame reading it fallen (ruling P24-AV: E10's a59, sent on the knockdown alone, was rejected
                      # `not valid`); before P24-AV the knockdown read the target downed and the stomp went at once
STOOD_STOMPS = 2      # stomps at one target failed `stood` (it rose before the stomp landed) after which the floor strike
                      # follows (ruling P24-AV: "fallen again, one more stomp, then the floor strike")
PULL_R = FIGHT_REACH + KEEP_R   # tiles: the pull of a lone chaser ends, the stance taken, once it is this near (ruling
                      # P24-AN: "until the chaser alone is within FIGHT_REACH + KEEP_R"; 4.5)
EDGE_HOLD_TICKS = 6   # planner ticks a zombie that left the listing (beyond LISTED_R, AIM_R's 12) is held in the seek's
                      # and the pull's reads at its last listed square (ruling P24-AU: 3 s at the drivers' PLANNER_HZ 2;
                      # E10's run 4 flipped seek, pull, seek seven aims running as a group at the edge came and went)


def place_of(world):
    """The player's square on a uniform SCAN_R grid (half up, never Python's half-even round): Explore's place."""
    mx, my = me_xy(world)
    return int(math.floor(mx / SCAN_R + 0.5)) * SCAN_R, int(math.floor(my / SCAN_R + 0.5)) * SCAN_R


def centre(sq):
    """The centre `(x + 0.5, y + 0.5)` of the square holding (x, y): every walk the planner sends to a square targets
    it. The Lua's walk ends `done` within its DONE_R (1.0 tiles) of the target, so a square's integer corner, which
    lies within 1.0 of the character on any square touching its own, ended every X5-2 reposition walk on its accept
    tick without a step (T18.4)."""
    return math.floor(sq[0]) + 0.5, math.floor(sq[1]) + 0.5


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

    trans = True   # ruling P24-AS: a heading read (`clear_heading`) refuses a `solidTrans` square; Survive sets it each
                   # tick from its TRANS switch (the replay tests' seam onto the rules before it)

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.last = None      # the last Action this policy sent
        self.why = {}

    def busy(self):
        """True while this policy's last action runs (`running`: the current one and not yet terminal, or a leg a
        riding bandage left running)."""
        return running(self.actions, self.last)

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
    `world.by_use()` (so a bottle marked empty is `other`, and spare) nor a worn garment (use `clothing`, PZA/1.6),
    ties by the least id; else None. Survive's load
    branch and its flee drop it."""
    wielded = (world.weapon or {}).get("type")
    by_use = world.by_use()
    kept = {iid for use in KEPT_USES for iid in by_use[use]}
    best = None
    for iid, it in world.inventory.items():
        if not item_id_ok(iid) or iid in kept or (it.get("fullType") or "") == wielded:
            continue
        if it.get("use") == "clothing" and it.get("worn") is True:
            continue   # Task 24: the garment on the back is never the spare (dropping it would undo the wear)
        rank = (-(it.get("weight") or 0.0), iid)
        if best is None or rank < best:
            best = rank
    return best[1] if best else None


def line_to(world, z):
    """The line from the player to zombie record `z` (`world.line_clear`), None when the frame has no position or the
    map lacks either end square on the player's floor: an unscanned end is never read as a wall. The Fight's line
    check and Survive's inside hold (fix wave P, M-6) share it."""
    me = world.me or {}
    a, b = (me.get("x"), me.get("y")), (z.get("x"), z.get("y"))
    if a[0] is None or a[1] is None or b[0] is None or b[1] is None:
        return None
    floor = me_floor(world)
    if any((int(math.floor(q[0])), int(math.floor(q[1])), floor) not in world.map for q in (a, b)):
        return None
    return world.line_clear(a, b)


def in_reach(world, z, r):
    """Zombie `z` is in a cornered Fight's reach (fix round 2, G4): within POINT_BLANK_R, or within `r` with its line
    not read blocked (`line_to` True or None). A zombie at 1.0-1.5 tiles behind a blocked line is no corner's target:
    it is hitting the wall from outside."""
    if z.get("x") is None or z.get("y") is None:
        return False
    d = zdist(world, z)
    return d <= POINT_BLANK_R or (d <= r and line_to(world, z) is not False)


def others_behind(world, zid, z):
    """Ruling P24-A (b) (E5 line 219: the fight walked at 19275, 5.99 tiles off, with 19278 and 19249 listed 11 tiles
    out within 13 degrees of its bearing; the group arrived round it): the ids, sorted, of the other zombies listed
    within LISTED_R of the player that lie BEHIND_MARGIN or more beyond the target `z` (id `zid`; P24-A fix 1 (5))
    and within AHEAD_CONE of its bearing. A
    zombie with no position, or the target at the player's own position, is none."""
    mx, my = me_xy(world)
    tx, ty = z["x"] - mx, z["y"] - my
    td = math.hypot(tx, ty)
    if td == 0.0:
        return []
    cos_cone = math.cos(math.radians(AHEAD_CONE))
    out = []
    for oid, o in world.zombies.items():
        if oid == zid or o.get("x") is None or o.get("y") is None:
            continue
        dx, dy = o["x"] - mx, o["y"] - my
        d = math.hypot(dx, dy)
        if td + BEHIND_MARGIN <= d <= LISTED_R and (dx * tx + dy * ty) >= d * td * cos_cone:
            out.append(oid)
    return sorted(out, key=repr)


def hit_reaction(world):
    """The frame's `me.hitReaction` when it names one (PZA/1.4, a non-empty string), else None (absent on a PZA/1.3
    frame): no swing starts while it is set (#4292, #4293)."""
    h = (world.me or {}).get("hitReaction")
    return h if isinstance(h, str) and h else None


def arm_pain(world):
    """The frame's `body.armPain` (PZA/1.7: the summed pain of the six arm parts, #4370) when a number, else None (a
    frame written before PZA/1.7 carries none: no strain rule reads it)."""
    v = (world.body or {}).get("armPain")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def arms_hurt(world):
    """Ruling P24-AP (#4370: a swing that is not a stomp divides its damage by the summed arm pain over 10, whatever
    the pain's source, a bite's included): the frame's `body.armPain` at STRAIN_HARD or above, where a swing does half
    its damage or less, so the Fight never swings (the shove ignores damage, #4373; the stomp's damage is set after
    the divider, #4374)."""
    pain = arm_pain(world)
    return pain is not None and pain >= STRAIN_HARD


def arm_stiffness(world):
    """Ruling P24-AT: the larger of the frame's two arms' stiffness (`body.strain` {l, r}, PZA/1.7: each the largest
    `getStiffness()` of its side's three arm parts, #4369) when both read numbers, else None (a frame before PZA/1.7)."""
    s = (world.body or {}).get("strain")
    if not isinstance(s, dict):
        return None
    v = [s.get(k) for k in ("l", "r")]
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return None
    return max(v)


def on_floor(z):
    """Zombie record `z` lies on the floor (PZA/1.7's `onFloor`: knocked down, or crawling); absent is standing."""
    return z.get("onFloor") is True


def pull_from(world, t, skip=(), reach=ENGAGE_R, edge=None):
    """Ruling P24-AN, the pull (the guides notes § 9 change 8: draw one from a group by walking away, then fight it
    alone; E9 dropped six fights for a chaser 10.74 to 11.90 tiles behind the target, the look behind's `held`): the
    centroid (x, y) of the other zombies listed within LISTED_R when target `t` (id, zombie, dist) chases the player
    (`hasTarget`) within `reach` (ENGAGE_R; a chaser already pulled is kept to DISENGAGE_R: `Fight.seeking`), no other
    zombie chases within ENGAGE_R (one chaser), every other listed zombie stands beyond DANGER_R and at least one is
    listed; else None. The ids in `skip` (read dead) are no zombies. Ruling P24-AU: `edge` ({id: its record at its last
    listed square}, `Fight.edge`) are zombies that left the listing within EDGE_HOLD_TICKS: each counts as listed, read
    at that square, whatever the World holds of it now."""
    zid, z, d = t
    if not chasing(z) or d > reach:
        return None
    edge = edge or {}
    xs, ys = [], []
    for oid, o in list(world.zombies.items()) + [(i, rec) for i, rec in edge.items() if i not in world.zombies]:
        o = edge.get(oid, o)
        if oid == zid or oid in skip or o.get("x") is None or o.get("y") is None:
            continue
        od = zdist(world, o)
        if od > LISTED_R and oid not in edge:
            continue
        if od <= DANGER_R or (od <= ENGAGE_R and chasing(o)):
            return None
        xs.append(o["x"])
        ys.append(o["y"])
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else None


def away_vector(world, points):
    """The unit vector along the sum of the unit vectors from each of `points` ((x, y)) to the player, each weighted
    by 1/distance (ruling P23-AG 3: away from the centroid and from the nearest, so a group spread round the player is
    not fled into), else None when the sum is zero. The flee's legs and the stance fight's backpedal (P24-G 1) share
    it."""
    mx, my = me_xy(world)
    vx = vy = 0.0
    for px, py in points:
        dx, dy = mx - px, my - py
        d2 = dx * dx + dy * dy
        if d2 > 0.0:
            vx, vy = vx + dx / d2, vy + dy / d2   # (unit vector) / distance
    n = math.hypot(vx, vy)
    return None if n == 0.0 else (vx / n, vy / n)


def clear_heading(world, v, reach=STEER_PROBE, trans=True):
    """The map's line `reach` tiles along `v` from the player, an unknown square open (fix round 2, concern 1). A
    hoppable fence's edge reads blocked (`line_clear` never climbs: a steer or a backpedal never vaults, ruling P24-G
    4). `trans` (ruling P24-AS; a policy's `trans`, Survive's TRANS): a `solidTrans` square (a fence, a window or a
    counter the engine blocks but sees through: E9 held its y 16.511 s against such a row while every steer pointed
    into it) refuses the heading as a solid one does; off, `solid` alone, the rule before it."""
    mx, my = me_xy(world)
    return world.line_clear((mx, my), (mx + reach * v[0], my + reach * v[1]), unknown_open=True, trans=trans)


def stance_leg_kind(d, advance, seek=False, pull=False):
    """The stance leg a standing fight's target `d` tiles off calls for (rulings P24-G 1, P24-N, P24-X and P24-AN):
    `enter` within FIGHT_REACH, `toward` in the advance, `pull` while the fight pulls a lone chaser away from the group
    (`pull`: the caller's `Fight.pulling`, beyond PULL_R), `seek` while the fight seeks it (`seek`: the caller's
    `Fight.seeking`, whose `seek_allowed` holds the one KEEP_R guard: Task 18 fix 1, the review's minor 13; the caller
    has already excluded a target inside KEEP_R, so `seek` here means d > KEEP_R: fix 2, minor 4), `back`
    inside KEEP_R, else `stand`. `Fight._stance_leg` sends it and `Fight.busy` gives a running leg way when it changes
    (Task 12 fix 1)."""
    if d <= FIGHT_REACH:
        return "enter"
    if advance:
        return "toward"
    if pull:
        return "pull"
    if seek:
        return "seek"
    return "back" if d <= KEEP_R else "stand"


def chasing(z):
    """Zombie record `z` reads a target (`hasTarget` true): it is coming."""
    return z.get("hasTarget") is True


def seek_allowed(world, t, hold_ground):
    """Ruling P24-X as Task 18 fix 1 narrows it (the review's ruling 2): target `t` (id, zombie, dist) may be sought:
    beyond KEEP_R, the character not holding ground (`hold_ground`: on a room or door square, Survive's
    `_chokepoint`: inside a building, the broken hold's and the trapped fight's included, or in a doorway, the stance
    stands and lets it come), and not a chasing target whose straight line to the character crosses a known fence
    (`World.fence_on_line`: the fence is the chokepoint)."""
    if t[2] <= KEEP_R or hold_ground:
        return False
    if not chasing(t[1]):
        return True
    mx, my = me_xy(world)
    return not world.fence_on_line((mx, my), (t[1]["x"], t[1]["y"]))


def rides_on(actions, a):
    """Leg `a` (a walkTo or a steer, not yet terminal) is kept running by the Lua under the bandages sent after it,
    every one of them with `keepMoving` (PZA/1.5.3, ruling P24-R: a riding bandage leaves the leg its slot; a new leg
    takes the ride along, any other send ends both): Task 12 fix 1, P24-U."""
    if a.type not in RIDE_TYPES or actions.done(a):
        return False
    for b in reversed(actions.history):
        if b is a:
            return True
        if b.type != "bandage" or b.args.get("keepMoving") is not True:
            return False
    return False


def running(actions, a):
    """Action `a` runs: the current action, or a leg a riding bandage sent since has left running (`rides_on`)."""
    return a is not None and (actions.current is a or rides_on(actions, a))


def blocked(unreachable, now):
    """The ids of `unreachable` (id -> wall until) still skipped at `now`."""
    return {zid for zid, until in unreachable.items() if until > now}


def _night():
    """`planner.night`, imported at the call: night imports this module at its top, so a top-level import here would
    be circular. The flee's shelter runs night's own steps (`shelter_plan`, `shelter_step`, `shelter_ended`)."""
    from agent.base.planner import night
    return night


def _rotate(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return v[0] * c - v[1] * s, v[0] * s + v[1] * c


def _square_of(world, z):
    """The map record of zombie `z`'s floored square on the player's floor, else None."""
    return world.map.get((int(math.floor(z["x"])), int(math.floor(z["y"])), me_floor(world)))


def in_building(world, z, building):
    """Zombie `z` stands on a square of `building` (a room square or its door square, a door kept on an outdoor
    square read by `World.door_building`: survival 3 fix round 1, R2): Survive's door fight reads it."""
    s = _square_of(world, z)
    if s is None or building is None:
        return False
    if s.get("room") is not None:
        return s.get("building") == building
    sq = (int(math.floor(z["x"])), int(math.floor(z["y"])), me_floor(world))
    return s.get("door") is not None and world.door_building(sq) == building


def in_corridor(me, end, z):
    """Zombie `z` lies ahead of the player within CORRIDOR_R of the straight segment from `me` to `end` (past `end`,
    within CORRIDOR_R of it): the flee would run through it (P23-AG fix round 1, I1)."""
    ux, uy = end[0] - me[0], end[1] - me[1]
    length = math.hypot(ux, uy)
    zx, zy = z["x"] - me[0], z["y"] - me[1]
    if length == 0.0:
        return math.hypot(zx, zy) < CORRIDOR_R
    ux, uy = ux / length, uy / length
    t = zx * ux + zy * uy
    if t <= 0.0:
        return False
    if t > length:
        return math.hypot(z["x"] - end[0], z["y"] - end[1]) < CORRIDOR_R
    return abs(zx * uy - zy * ux) < CORRIDOR_R


def on_room(world):
    """The player's square is a room square (the night's `inside()` read off the World alone)."""
    return (world.map.get(_night().player_square(world)) or {}).get("room") is not None


def exit_plan(world, threats, refused=(), trans=True):
    """The way out of the building the player stands in (ruling P23-AJ 3 as amended, and its fix round 1), else
    None: standing on a room square of a building, of its `night.exits` on the player's floor (an opening, or a
    closed exterior door to open first) whose outside square is not in `refused`, whose outside square's centre is no
    nearer any threat than the player is to it (the shelter pick's rule), and whose straight line from the player to
    that centre passes no threat within EXIT_CLEAR_R (fix round 1: E2's offline check at gameMin 585 chose an opening
    across the building past the zombie at 0.48 tiles), and whose square beyond is open (`_beyond`; the review's I1:
    a walk to the outside square itself ends `done` on the room square and is refused), the nearest to the player,
    ties by that square; `{building, inner, outer, door, target, step, opened}`, `target` the square the walk goes to,
    `step` "walk" (the review's I2: the jar's path follower opens a closed door on a player's path,
    `PathFindBehavior2.checkDoorHoppableWindow`, a review reading; the open is the fallback), `opened` False. `trans`:
    `_beyond`'s (ruling P24-AS)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    if s.get("room") is None or b is None:
        return None
    ts = [z for z in threats if z.get("x") is not None and z.get("y") is not None]
    me = me_xy(world)
    marked = world.marked_doors()   # Task 18 fix 1, major 4: a marked door stays a way out, ranked after the others
    best = None
    for e in N.exits(world, b, me_floor(world)):
        if e["outer"] in refused:
            continue
        c = centre(e["outer"])
        if any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(world, z)
               or _in_tube(me, c, (z["x"], z["y"]), EXIT_CLEAR_R) for z in ts):
            continue
        if _beyond(world, e["inner"], e["outer"], trans) is None:
            continue
        rank = (e["door"] in marked, math.hypot(c[0] - me[0], c[1] - me[1]), e["outer"], e["inner"])
        if best is None or rank < best[0]:
            best = (rank, e)
    if best is None:
        return None
    e = best[1]
    return dict(e, building=b, target=_beyond(world, e["inner"], e["outer"], trans), step="walk", opened=False)


def _in_tube(a, b, p, r):
    """Point `p` lies within `r` of the end `b`, or ahead of `a` (its projection on the segment from `a` to `b` past
    `a`) within `r` of the segment: the exit's own square and its straight line, never the player's back (P24-A fix 1
    (3), the tube of P23-AP 3's cut)."""
    if math.hypot(p[0] - b[0], p[1] - b[1]) < r:
        return True
    ux, uy = b[0] - a[0], b[1] - a[1]
    if (p[0] - a[0]) * ux + (p[1] - a[1]) * uy <= 0.0:
        return False
    return _seg_dist(a, b, p) < r


def _seg_dist(a, b, p):
    """Tiles from point `p` to the segment from `a` to `b`."""
    ux, uy = b[0] - a[0], b[1] - a[1]
    n2 = ux * ux + uy * uy
    t = 0.0 if n2 == 0.0 else max(0.0, min(1.0, ((p[0] - a[0]) * ux + (p[1] - a[1]) * uy) / n2))
    return math.hypot(p[0] - a[0] - t * ux, p[1] - a[1] - t * uy)


def _beyond(world, inner, outer, trans=True):
    """The square the exit walks to: one more square on from `outer` away from `inner` when the map holds it open (not
    solid, no room, the step to it not blocked), else None (the exit is skipped: fix round 1, the review's I1). A walk
    ends `done` within the Lua's DONE_R (1.0) of its target, so a walk to the outside square's own centre may end on
    the room square beside it (rule 5's lesson); from the square beyond it ends at least a tile from the room
    square's centre. With `trans` (ruling P24-AS) a `solidTrans` square beyond is no walk's end either."""
    sq = (2 * outer[0] - inner[0], 2 * outer[1] - inner[1], outer[2])
    s = world.map.get(sq)
    if (s is None or s.get("solid") or (trans and s.get("solidTrans")) or s.get("room") is not None
            or world.blocked(outer, sq)):
        return None
    return sq


def stand_post(world, way, building, trans=True):
    """The square a doorway stand's walks aim at (ruling P24-AO, Task 32 fix 1, the review's blocker): of the door's
    `way` (`World.door_way`: the room square inside the threshold, the outside square), the square one on from the
    room square away from the outside one, when it is a room square of `building`, not solid (nor `solidTrans` with
    `trans`) and its step from the threshold square not blocked; else None (no stand: the door is closed as today).
    A walk ends `done` within the Lua's DONE_R (1.0) of its target: E9's enter to the threshold square's own centre
    (10711.5, 10596.5) ended 0.84 tiles off it, on the outdoor door square (10712, 10596), open on three sides; to the
    square beyond (10710.5, 10596.5), 1.5 tiles from the door's edge, it ends at least half a tile inside it, as
    `_beyond` reads for an exit."""
    inner, outer = way
    deep = (2 * inner[0] - outer[0], 2 * inner[1] - outer[1], inner[2])
    s = world.map.get(deep)
    if (s is None or s.get("room") is None or s.get("building") != building or s.get("solid")
            or (trans and s.get("solidTrans")) or world.blocked(inner, deep)):
        return None
    return deep


def on_post(world, building):
    """The player stands on a room square of `building` (the doorway stand's post: the threshold square inside or one
    beside it, never the outdoor door square of a door on a south or east wall)."""
    s = world.map.get(_night().player_square(world)) or {}
    return s.get("room") is not None and s.get("building") == building


def adoptable(world):
    """The building the player stands in has an exterior door on the player's floor (`Flee._adopt` can adopt it), a
    marked one included (read from inside: Task 18 fix 1, the review's major 4)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    return (s.get("room") is not None and b is not None
            and bool(N.exterior_doors(world, b, me_floor(world), marked=True)))


class Explore(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.scanned = set()   # the places scanned from, or with a scan still running
        self._scan = None      # (place, Action) of the last scan sent, until it ends
        self._walk = None      # ((x, y), Action) of the last walk sent, until it ends
        self._last = None      # (aid, place) of the last scan sent: its job may still be dropped after its done line

    def place(self):
        return place_of(self.world)

    def observe(self):
        if self._walk is not None and self.actions.done(self._walk[1]):
            self._walk_ended(*self._walk)
            self._walk = None
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
        return WalkTo(*centre(edge), "walk")

    def sent(self, cmd, action, leg=False):
        """`leg`: the walk is a goal's leg toward a farther point (ruling P24-AC, `goals._Legs`): its `no square` marks
        nothing."""
        if cmd.TYPE == "scan":
            self.scanned.add(self.place())
            self._scan = (self.place(), action)
            self._last = (action.aid, self.place())
        elif cmd.TYPE == "walkTo":   # the target square, for mark_stuck; the player's position, for the stuck pair
            self._walk = ((int(math.floor(cmd.x)), int(math.floor(cmd.y))), action, me_xy(self.world), leg)

    def _walk_ended(self, to, a, start, leg=False):
        """A walk's end: a target failed for a STUCK_REASONS reason is marked stuck (a leg's `no square` never: the
        client's unloaded ground is no stuck square, P24-AC); one failed `stuck` with the
        player moved under STUCK_MOVE from its start is a stuck pair from the start's square (P23-AP 1), and the
        rescan of the player's place once STUCK_AREA_N stand in a row there (the goal source's scan, never a third
        walk); a walk that moved the player or ended done ends the run."""
        moved = math.hypot(me_xy(self.world)[0] - start[0], me_xy(self.world)[1] - start[1])
        if a.state == "failed" and a.reason in STUCK_REASONS and not (leg and a.reason == "no square"):
            self.world.mark_stuck(*to)
        if a.state == "failed" and a.reason == "stuck" and moved < STUCK_MOVE:
            self.world.mark_stuck_pair((int(math.floor(start[0])), int(math.floor(start[1]))), to)
            if len(self.world.stuck_run["to"]) in (STUCK_AREA_N, STUCK_AREA_N + STUCK_WALK_CAP):
                self.scanned.discard(self.place())   # the scan the source falls back to (fix round 1, R2: at the cap)
        elif a.state == "done" or moved >= STUCK_MOVE:
            self.world.clear_stuck_run()


class LootHouse(Policy):
    def __init__(self, world, actions, clock=time.time, want=None):
        super().__init__(world, actions, clock)
        self.want = want        # one of LOOT_WANTS, set by the caller: the container's want and the loot's filter
        self.pending = []       # (x, y, z, Action) of each loot sent and not yet seen ended
        self.capped = {}        # (x, y, z, use) -> the carried weight when a loot there skipped items for the cap
        self.within = None      # a set of container keys a target is kept to (a LootBuilding goal's), None for any
        self._key = None        # the container the last choose picked
        self.fails = {}         # (container key, use) -> failed loots there (Task 18 fix 1, major 3)

    def level(self):
        return (self.world.load or {}).get("level") or 0

    def cap(self):
        """The loot's maxWeight: the frame's load.max times LOAD_RATIO_MAX, 0.0 (no cap) when it reads no positive
        number. A `clothing` loot takes at most CLOTHING_LOOT_KG per garment still wanted on top of the carried weight
        (CLOTHING_HELD_N less the unworn garments held), never past that cap (review-t24 major 3)."""
        m = (self.world.load or {}).get("max")
        ok = isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0
        cap = float(m) * LOAD_RATIO_MAX if ok else 0.0
        w = self.weight()
        if self.want == "clothing" and ok and w is not None:
            spare = sum(1 for i in self.world.by_use().get("clothing", ()) if self.world.inventory[i].get("worn") is not True)
            cap = min(cap, w + max(CLOTHING_HELD_N - spare, 0) * CLOTHING_LOOT_KG)
        return cap

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
            mark = a.state == "done" or (a.state == "failed" and a.reason in LOOT_MARKS)
            for key, c in self.world.containers.items():
                if key[:3] != (x, y, z) or not any(holds_use(i, use) for i in c["items"]):
                    continue
                n = 0 if mark else self.fails.get((key, use), 0) + 1
                if mark or n >= LOOT_FAILS_TO_PASS:
                    self.fails.pop((key, use), None)
                    self.world.mark_looted(key, use)
                else:
                    self.fails[(key, use)] = n
        self.pending = still

    def waiting(self, want):
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
        exclude = self.waiting(want)
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


def __getattr__(name):
    """`Fight` and `Flee` by their old module (Plan 24 Task 36 moved them to `planner/fight.py` and `planner/flee.py`):
    the frozen drivers (`x5_combat.py`, `x5_combat_2.py`, never edited after their runs) import `Fight` from here.
    Read at the access, so neither module is imported while this one loads (both import it)."""
    if name == "Fight":
        from agent.base.planner.fight import Fight
        return Fight
    if name == "Flee":
        from agent.base.planner.flee import Flee
        return Flee
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
