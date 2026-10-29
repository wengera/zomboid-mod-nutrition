"""World (Plan 22 Task 9, spec § 8): the planner's picture of the game, a pure function of the PZA/1 lines it is given.

It reads what the transport gives: keyed full dicts, every delta frame already merged (`FileTransport.lines()`).
`apply(line)` dispatches on `line["kind"]`; an unknown kind counts in `unknown_kinds` and never raises.

- `frame`: each group (`me`, `stats`, `body`, `load`, `weapon`, `action`, `act`, `cost`) kept as the dict the frame
  carries, None when the frame's group is null; `game_min`, `world_age` (the frame's `worldAge`, hours; not in
  `to_json`, so the goldens keep their bytes), `frame_wall_ms`; zombies keyed by id with
  `seenWallMs = wallMs`, a zombie unseen for more than `ZOMBIE_TTL_S` aged out at the next frame. No clock is read.
- `map`: each square applied at once (no whole-scan hold): `map[(x, y, z)]` the square dict as decoded, its
  containers at `containers[(x, y, z, i)] = {type, n, items, looted}`, `looted` the set of uses a loot took there
  (Plan 23 Task 11 fix 1: a loot filters one use, so a container looted for water is still unlooted for food), the
  marks kept across a re-scan of the same square and type (Plan 21's rule), a container index the new square no
  longer has dropped; `buildings` the set of
  building names seen. A `full` part whose `scanId` is below the newest seen is dropped and counted in
  `dropped_scans`; a delta is never dropped. `map_lines` counts every map line, `missing` is the union of every map
  line's missing names in first-seen order.
- `event`: every event line in `events` (deque 500); `item_added`/`item_removed` build `inventory[itemId] =
  {fullType, weight[, use]}` (ruling P22-2; `use` only when the line carried it), an unknown id's removal counted in
  `missing_items`; a client
  `damage` event appends `{tag, amount, side, wallMs}` to `damage` (deque 500); `zombie_dead` drops the zombie;
  `scan_dropped`
  (ruling S-32: a scan job the Lua dropped after its one act line, done) adds the scan's aid to `scans_dropped`, which
  `to_json` does not carry (the planner reads it; the line itself is in `events`).
- `act`: `acts[str(aid)]` the last act line for the aid. `hello`: the last hello line, and a new session: the Lua
  restarts its `scanId` and the server's `damage.watch` record numbers restart with the server, so a hello resets the
  newest scanId seen and `damage_seen_i` (else a relaunched client's scans would all be dropped as older).
  `reply`: `last_reply`.

The planner's game clock (Plan 23 fix wave P, I-1): `world_minutes()` is `worldAge * 60`, the game minutes since the
world began, monotonic across midnight (the frame's `gameMin` is the minute of the day, `h * 60 + m`, and wraps); a
frame with no number for `worldAge` falls back to `gameMin`. Every game-minute timer of the planner reads it (the
stuck marks here, the night's and the Shelter goal's shuns); `game_min` stays for the logs.

`stuck` is the planner's memory, not the lines': `mark_stuck(x, y)` records a walk target that ended stuck at the
current `world_minutes()` and `unexplored_edge` leaves it out for STUCK_TTL_MIN game minutes; `to_json` does not
carry it. Survival 4 (ruling P23-AP 1, the chain's E4: twelve walks failed `stuck` one after the other from the square
north of a locked gate, each target the next square of one fenced-off area, 21.85 game minutes): `mark_stuck_pair(frm,
to)` records a walk from square `frm` to `to` that failed `stuck` having moved the player under 0.5 tiles
(`policies.Explore`), `stuck_run` the pairs in a row from one square (`clear_stuck_run` ends the row: a walk that
moved or arrived); once STUCK_AREA_N (2) stand in a row from the player's own square within STUCK_TTL_MIN
(`stuck_here`, the player within 1.0 tile of the run's square: fix round 1, M1), `unexplored_edge` proposes only an
edge square whose straight line from the player is clear
(`line_clear`, `unknown_open=False`: no known blocking edge, no unknown square, between) and which a bounded flood
from the player reaches (`flood`, `reachable`: REACH_LIMIT 400 squares over the kept map, each step `blocked`-read),
and none when no such square is known (the goal source then loots or scans: never a third walk from that square).
After STUCK_WALK_CAP (3) more unmoved stuck walks in a row (those in the open failing too: fix round 1, R2) it answers
none. Neither is in `to_json`. `unmark_stuck(x, y)` drops a walk target's mark (a route climb over its fence ended
done: Task 10 fix 1, minor 9, `goals.Kit.climbed`).

The water sources (Plan 24 Task 10, ruling P24-G 3; moved here at Task 10 fix 1, the review's minors 4 and 14, from
the care branch, which the wash and the fill both read): `water_squares()` is the map's squares carrying a `water`
record, memoised per map version (`memo`: one walk of the map per scan, never per tick); `water_sources(r)` reads
them each call: the squares on the player's floor with water in them (`infinite`, or an `amount` above 0) within `r`
tiles of the player (by the square's centre), nearest first (ties by the square), a square in `tainted_sources` (a
fill found it tainted, Task 9 fix 2) read tainted, and a square in the dry store left out: `mark_dry(sq)` records a
source a wash or a fill failed at for its water or its walk, at the current world minute, and `dry_now()` is the
squares marked within SOURCE_RETRY_MIN game minutes (a judgment: a map's `water.amount` is refreshed only by a scan,
so the retry is the only way a refilled source comes back). The planner's, never a line's; not in `to_json`.
`frame_n` counts the frames applied (the care branch's one-frame wait after a bandage, Task 10 fix 1, minor 6).
`killed` (Plan 24 Task 12, ruling P24-Q: zombies killed is the iteration's metric) holds the zombie ids a Fight read
`targetDead` on (`note_kill`); `kills`, its count, goes into `to_json` once non-zero and into the goal layer's view.
It is the planner's lower bound, never the metric (Task 12 fix 1, the review's minor 8): only the running
`Survive.fight`'s own attack or aim result is read, so a Fight replaced before its result was read loses that kill and
a kill by any other means is not read; the drivers grade kills off the death event's own count (#4321) and read
`kills` as a cross-check.

The met memory (Plan 24 survival 5, ruling P24-A (a): E5's horde was listed at the 12-tile edge while the threat
branch counted within 6, #4268): `met` keeps, for each zombie id a frame listed with a position, where it was last
listed and the world minute of that frame (`{id: (x, y, minute)}`), for MET_TTL_MIN (10) game minutes off
`worldAge` (a frame with no number for `worldAge` adds nothing: the memory never moves the gameMin fallback's
origin); `zombie_dead` drops its id. `met_density(x, y, r=MET_R)` counts the distinct zombies met within `r` tiles of
(x, y); `met_window(r=MET_R)` is the densest window: of the met positions taken as centres, the one with the most met
zombies within `r` (ties: nearest the player, then by position), answered as `(cx, cy, n)`, the centroid of those `n`
zombies, else None. The flee's first leg is pushed off the window's centre (`policies.Flee`). Not in `to_json`.

The goal sources' met ground (Plan 24 Task 3, ruling P24-B; F1's goals kept walking toward the one gate zombie, #4278):
`met_near(r=MET_VIEW_R)` is the densest MET_R window centred within `r` (25) tiles of the player, `(cx, cy, n)` (the
centroid of the `n` met zombies within MET_R of the centre) else None; the view reads it as `met`. Its search is
bucketed (Task 3 fix 1, review I1: `met_window`'s every-met-centre search is quadratic, 9.6 ms at 400 met; the bounded
search with its cache reads about 2 ms a tick there): only the met within `r + MET_R` of the player are read, bucketed
into MET_R cells; the candidate centres are each occupied cell's centroid and each 2 x 2 block of cells' centroid, each
then shifted to its window's centroid up to MET_SHIFTS (3) times (a mean shift, so a group straddling the cells' lines
is found whole), each window counted over the 3 x 3 cells round its centre, so the search is linear in the met for a
bounded area; the rank is `met_window`'s (most met, then nearest the player, then position). Its answer is cached on
(`met_version`, the player's position, `r`): `met_version` rises on every change of the memory (a frame that listed or
expired a zombie, a `zombie_dead` that dropped one), so the tick's several reads (the view, `avoid_cone`,
`policies.Explore`) cost one search. `avoid_cone()` is its bearing (`bearing_deg`: degrees clockwise from north, -y)
while `n` >= MET_AVOID_N (3), else None, and `in_cone(x, y)` whether the square's centre lies within MET_AVOID_DEG (45,
inclusive) of that bearing from the player (the player's own square, no bearing, never does). `unexplored_edge` leaves
every square `in_cone` out, under both its rules, so the edge walk never heads at a met group; when every edge lies in
the cone it answers None (the source then loots, scans or rests: never a walk at them). Under MET_AVOID_N the choice is
the plain one. `compass(dx, dy)` names a bearing's eighth (N, NE, ... NW), None for no offset.

The server's side comes in through `merge_server(stats, wall_ms)` and `merge_damage(reply, wall_ms)`, a
`damage.watch` reply whose `last` records not yet seen (by `i`) land in `damage` tagged `server` (spec § 9).

Plan 23 Task 9 (P23-D, P23-K) adds the planner's reads of the kept map and the inventory:
- `blocked(a, b)`: the edge between two adjacent squares, read as the jar reads `IsoGridSquare.isBlockedTo`
  (`docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md` § 1): a square stores only its own north and west edges
  (`blockN`, `blockW`, movement-blocking: a wall, a closed or barricaded door, an intact closed window), so the north
  neighbour reads `a`'s `blockN`, the south `b`'s, the west `a`'s `blockW`, the east `b`'s; a diagonal is blocked when
  any of the four edges meeting at the shared corner is, or either corner square is solid. Unlike the jar (which reads
  an unloaded neighbour's edge open), an unknown square or a null edge counts blocked: the planner never assumes a way.
  `blocked(a, b, climb=True)` (Plan 24, PZA/1.4, ruling P24-C; the jar reads in
  `docs/superpowers/specs/2026-10-29-plan-24-jar-reads.md` § 1): a hoppable fence loads with its edge's collide flag,
  so `blockN`/`blockW` read it blocked, while the path follower climbs any edge whose square carries `HoppableN`/
  `HoppableW` at a walk; an orthogonal step over a blocked edge whose holder's `hopN`/`hopW` reads True is crossable.
  `flood` and `reachable` read with it; `line_clear` (a steered walk, free movement, vaults only at a run) and every
  other reader never do; a diagonal never climbs.
- `line_clear(a, b)`: Bresenham over the squares from `a` to `b` (positions floored, on the player's floor), false at
  any blocked edge a step crosses (`blocked`) or any solid or unknown square strictly between the ends. It reads the
  blocked edges, never `edgeN`/`edgeW` (any wall, window or door edge whatever its state), which the square record
  keeps for the view and a later sight reading (ruling P23-K). With `unknown_open=True` (the flee's steer probe, Plan
  23 survival 1 fix round 2) an unknown square is open ground: only a known solid square, or a blocked edge between
  two known squares, refuses the line; a diagonal step's unknown corner square is neither solid nor edged (fix round
  3, F5), a known one read as by default (`blocked(a, b, unknown_open=True)`).
- `reachable_adjacent(target_xy, z)`, `interiors()`, `doors_of(building)`. The map walk behind the last two is cached
  per map version (fix wave P, M-4): `map_version` rises on every square applied, and `_index()` (one walk: the room
  squares and the door squares by building) is rebuilt lazily on the first read after it moved; `memo(key, fn)`
  keeps any other read of the map (the night's exterior doors) for the same version. A cached answer is shared, so a
  caller only reads it.
- The stuck doors (ruling P24-Z, Plan 24 Task 18; E7 stood 55.6 s at building 5's locked back door while eight
  loots failed `not adjacent`): `note_door_fail(sq, reason)` counts a door's failures, the DOOR_FAILS_TO_MARK-th
  (2) within DOOR_RETRY_MIN (30) game minutes marking it (`door_marks`, the reason kept); `marked_doors()` the marks
  standing now; `door_near(xy, z, r)` the door square nearest a point. The planner's, never in `to_json`.
- `building_boxes()` (ruling P24-Y, Plan 24 Task 18: every walk has a building as its destination): each known
  building's room squares' bounding box, memoised per map version; `building_dist(x, y, b)` the tiles from a point
  to a box (0.0 inside), `nearest_building(x, y)` and `building_near(x, y, r)`, the woods test (no building within
  `goals.WOODS_R` of a square); `unexplored_edge(woods_r)` leaves the woods out once a building is known.
- `openings(building)` (Plan 23 survival 2, ruling P23-AJ 3 as amended: the chain's E2 died in building 3, whose
  doors were all broken, door debris on the floor, so `exterior_doors` was empty while its doorways stood open): each
  `(room square, outside square)` pair of the building, sorted, whose orthogonal step from a room square of it to a
  mapped, non-solid square with no room reads not blocked (`blocked`: the kept `blockN`/`blockW` false, a null read
  blocked) — a doorway whose door is open or gone, or a missing wall; memoised per map version. A window's edge is
  never one (survival 2 fix round 1, the review's G1: five of building 3's seven were smashed windows, and the jar's
  path follower fails a player's path at a window it cannot climb, `PathFindBehavior2.checkDoorHoppableWindow`, a
  review reading): the square holding the edge carries a `window` record and that edge's `edgeN`/`edgeW` reads
  true (both edges flagged on one window square read both as windows).
- `by_use()`: the inventory's ids by the item's own `use` (the engine's answer, Plan 23 Task 9b), else
  `agent.base.items.use_of` (the
  dataset; a `food` the dataset marks `cant_eat` reads `other`), an id the planner marked empty (`mark_empty`, kept in
  `empty_ids` and dropped with its item) moved from `water` to `container` (Task 9 fix 2),
  and an id the planner found refused (`mark_refused`, fix wave P I-4: a food whose consume ended `failed "not
  valid"`, kept in `refused` {id: the world minute of its refusal} and dropped with its item) moved from `food` to
  `other` for REFUSED_TTL_MIN (120) world minutes from the refusal only (ruling P23-AD: a refusal may be passing, the
  vanilla eat refusing a character that ate too much lately), so `spare()` may drop a refused food only inside that
  window; and an id the planner found to have no effect (`mark_no_effect`, ruling P24-F: a consume that ended `done`
  with no fall in its stat, F2's Disinfectant drunk 68 times; kept in `no_effect_ids` for the session and dropped
  with its item) moved from any use to `other`. `container` (PZA/1.4.1) is a use as the line carries it.
  `nearest_unlooted(want)` keys on the same use. The three are one store since Plan 24 Task 10 (ruling P24-I, the
  Task 4b review's minor 6): `marks` {held id: (reason, world minute)}, one reason an item (the latest mark wins:
  `MARK_REASONS`), dropped with its item; `empty_ids`, `refused` and `no_effect_ids` are its read views, and the care
  branch's `unrippable` (a rip the Lua refused `worn`, `not cotton` or `needs tool`: never asked again) lives there
  too, and the water chain's `filled`, `tainted` and `undrinkable` (a vessel the need's `fill` filled from a clean
  source, which `by_use` reads `water` whatever its line's use; one filled from a tainted source, which `tainted_ids`
  lists with any held item whose record names `TaintedWater`; one whose drink the Lua refused, read `other`).
  `item_changed` (PZA/1.5.1, Task 9 fix 1: an item's use or fluid read again after a fill, a consume, a wash or a
  rip) sets the held item's `use` ("a reader takes the event's use as the item's use from then on"), its `fluid`
  and `amount` (each dropped when the line leaves it out), and drops a vessel-state mark (`empty`, `filled`,
  `tainted`: the engine's read supersedes the planner's). `first_sight` (Task 10) is the set of ids an `item_added` named between a hello and the first frame after it:
  the inventory's first sight (ruling P22-2), the clothes the character stands in, which the care branch never rips.
  `to_json` carries `emptyIds`, `refusedIds` (the ids excluded now)
  and `noEffectIds` sorted, each only while it is non-empty,
  so a World that never marked one serialises as before (the replay goldens keep their bytes). For the same reason a
  container's `looted` set serialises as its uses sorted, or `false` while it is empty.
"""
import json
import math
import re
from collections import deque

from agent.base.items import USES, cant_eat, use_of

ZOMBIE_TTL_S = 10
STUCK_TTL_MIN = 60   # game minutes an edge whose walk ended stuck is left out of unexplored_edge
STUCK_AREA_N = 2     # unmoved stuck walks in a row from one square before its edges must lie in the open (P23-AP 1)
REACH_LIMIT = 400    # squares a reachability flood visits at most (P23-AP 1)
STUCK_WALK_CAP = 3   # unmoved stuck walks in a row past STUCK_AREA_N before no edge is answered (P23-AP fix 1, R2)
REFUSED_TTL_MIN = 120   # world minutes a food whose consume was refused `not valid` reads `other` (P23-AD)
SOURCE_RETRY_MIN = 10.0   # game minutes a source a wash or a fill failed at is left out (`mark_dry`; a judgment)
DOOR_RETRY_MIN = 30.0     # game minutes a door marked stuck is never tried again (ruling P24-Z, Plan 24 Task 18)
DOOR_FAILS_TO_MARK = 2    # failures on one door within DOOR_RETRY_MIN that mark it (P24-Z: "fails twice")
MARK_REASONS = ("empty", "refused", "no_effect", "unrippable", "filled", "tainted", "undrinkable", "in_bag")   # the planner's
                     # item marks (P24-I), one an item; `undrinkable` and the two before it the water chain's (P24-G 3), `in_bag` a care action the Lua refused
                     # `in bag` for good (Task 10 fix 2)
VESSEL_MARKS = ("empty", "filled", "tainted")   # the marks an item_changed line drops (the engine's read wins)
MET_TTL_MIN = 10     # game minutes a zombie listed stays in the met memory (ruling P24-A (a), a judgment: a group
                     # met within the last ten minutes is still about; E5's was first listed at gameMin 590 and at
                     # melee range by 593)
MET_R = 10.0         # tiles: the met window's radius (ruling P24-A (a), the spec's "densest 10-tile window")
MET_VIEW_R = 25.0    # tiles: a met window counts for the goal sources only with its centre this near (ruling P24-B 1,
                     # the view's widest zombie band)
MET_AVOID_N = 3      # met zombies in the window before the edge choice leaves its bearing out (ruling P24-B 2)
MET_AVOID_DEG = 45.0  # degrees either side of the window's bearing the edge choice leaves out (ruling P24-B 2)
MET_SHIFTS = 3       # met_near's shifts of a cell's centre to its window's centroid (Task 3 fix 1, I1: a group
                     # straddling the cells' lines is found whole)
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
GROUPS = ("me", "stats", "body", "load", "weapon", "action", "act", "cost")
DEQUE_N = 500


def me_xy(world):
    """The player's (x, y) from the frame's `me`, 0.0 for a coordinate it reads no number for (the one reader of the
    World's and the planner's)."""
    me = world.me or {}
    return me.get("x") or 0.0, me.get("y") or 0.0


def me_floor(world):
    """The player's floor, the frame's `me.z` floored (0 when it reads no number); a zombie record carries no floor,
    so a zombie is read on the player's."""
    z = (world.me or {}).get("z")
    return int(math.floor(z)) if isinstance(z, (int, float)) and not isinstance(z, bool) else 0


def bearing_deg(dx, dy):
    """The bearing of the offset (dx, dy), degrees clockwise from north (-y), in [0, 360); None for no offset."""
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return math.degrees(math.atan2(dx, -dy)) % 360.0


def compass(dx, dy):
    """The eighth of the compass (N, NE, ... NW) the offset (dx, dy) points into, None for no offset."""
    b = bearing_deg(dx, dy)
    return None if b is None else COMPASS[int((b + 22.5) // 45.0) % 8]


def _cell(x, y):
    """The MET_R cell of position (x, y): met_near's bucket."""
    return math.floor(x / MET_R), math.floor(y / MET_R)


def _mean(ps):
    """The centroid of the points `ps` (x, y)."""
    return sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)


def _num_first(v):
    """A sort key: numbers ascending first, then anything else by its JSON."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (0, v, "")
    return (1, 0, json.dumps(v, sort_keys=True))


def _box_dist(box, x, y):
    """Tiles from the point (x, y) to a building box (minx, miny, maxx, maxy) of squares, 0.0 inside it."""
    dx = max(box[0] - x, 0.0, x - (box[2] + 1))
    dy = max(box[1] - y, 0.0, y - (box[3] + 1))
    return math.hypot(dx, dy)


def _key(k):
    return ",".join(str(p) for p in k)


class World:
    ZOMBIE_TTL_S = ZOMBIE_TTL_S

    def __init__(self):
        for g in GROUPS:
            setattr(self, g, None)
        self.game_min = None
        self._gm0 = None             # the first gameMin read without a worldAge (world_minutes' fallback origin)
        self.world_age = None        # the frame's worldAge (hours), the clock world_minutes() reads
        self.frame_wall_ms = None
        self.zombies = {}            # id -> {x, y, dist, hasTarget, crawler, health, seenWallMs}
        self.map = {}                # (x, y, z) -> the square dict
        self.containers = {}         # (x, y, z, i) -> {type, n, items, looted}
        self.buildings = set()
        self.inventory = {}          # itemId -> {fullType, weight}
        self.marks = {}              # held id -> (reason, world minute): the planner's marks (`mark`), never a line's
        self.changes = {}            # held id -> item_changed lines read for it (the planner's settle wait, never serialised)
        self.tainted_sources = set() # water squares (x, y, z) a fill found tainted (the planner's, never a line's)
        self.dry = {}                # water square (x, y, z) -> world minute a wash or fill failed there (`mark_dry`)
        self.door_fails = {}         # door square (x, y, z) -> [(world minute, reason)] of its failures (P24-Z)
        self.door_marks = {}         # door square (x, y, z) -> (world minute, reason): marked stuck (P24-Z)
        self.frame_n = 0             # the frames applied (a frame-newer test's counter, never serialised)
        self.killed = set()          # the zombie ids a Fight read dead off its own attack or aim (P24-Q: `kills`)
        self.first_sight = set()     # the ids the inventory's first sight named (between a hello and the next frame)
        self._sighting = False       # a hello came and no frame yet: item_added is the first sight
        self.damage = deque(maxlen=DEQUE_N)
        self.damage_seen_i = set()   # the damage.watch record numbers already merged
        self.damage_counts_server = None
        self.events = deque(maxlen=DEQUE_N)
        self.acts = {}
        self.hello = None
        self.last_reply = None
        self.server = {}
        self.missing = []
        self.unknown_kinds = 0
        self.missing_items = 0
        self.dropped_scans = 0
        self.scans_dropped = set()   # the aids of the scans whose job the Lua dropped (scan_dropped, S-32)
        self.map_lines = 0
        self.stuck = {}              # (x, y) -> world_minutes(): a walk target that ended stuck, set by the planner
        self.stuck_run = None        # {"from": (x, y), "to": [(x, y)...], "at": world_minutes()}: the unmoved stuck
                                     # walks in a row from one square (P23-AP 1), set by the planner
        self.met = {}                # zombie id -> (x, y, world minute) where a frame last listed it (P24-A (a))
        self.met_version = 0         # rises on every change of `met`: the key of met_near's cache (Task 3 fix 1)
        self._met_near = None        # ((met_version, px, py, r), answer): met_near's cache
        self.map_version = 0         # rises on every square applied: the key of the map's cached reads
        self._memo = {}              # key -> (map_version, value): the cache of memo()
        self._indexed = None         # (map_version, {building: [room squares]}, {building: [door squares]})
        self._newest_scan = None
        self._handlers = {"hello": self._hello, "frame": self._frame, "map": self._map, "event": self._event,
                          "act": self._act, "reply": self._reply}

    # -- the lines ------------------------------------------------------------------------------------------------
    def apply(self, line):
        fn = self._handlers.get(line.get("kind")) if isinstance(line, dict) else None
        if fn is None:
            self.unknown_kinds += 1
        else:
            fn(line)

    def _hello(self, line):
        self.hello = line
        self._sighting, self.first_sight = True, set()
        self._newest_scan = None
        self.damage_seen_i = set()

    def _reply(self, line):
        self.last_reply = line

    def _act(self, line):
        self.acts[str(line.get("aid"))] = line

    def _frame(self, line):
        wall = line.get("wallMs", 0)
        self._sighting = False
        self.frame_n += 1
        for g in GROUPS:
            setattr(self, g, line.get(g))
        self.game_min = line.get("gameMin")
        self.world_age = line.get("worldAge")
        self.frame_wall_ms = wall
        for z in line.get("zombies") or ():
            self.zombies[z.get("id")] = dict({k: v for k, v in z.items() if k != "id"}, seenWallMs=wall)
        ttl = ZOMBIE_TTL_S * 1000
        for zid in [i for i, z in self.zombies.items() if wall - z["seenWallMs"] > ttl]:
            del self.zombies[zid]
        self._meet(line.get("zombies") or ())

    def _meet(self, zombies):
        """The met memory's frame update (the module docstring): each listed zombie with an id and a position at this
        frame's world minute, and every entry older than MET_TTL_MIN dropped; nothing without a `worldAge`."""
        wa = self.world_age
        if not isinstance(wa, (int, float)) or isinstance(wa, bool):
            return
        now = self.world_minutes()
        changed = False
        for z in zombies:
            if z.get("id") is not None and z.get("x") is not None and z.get("y") is not None:
                self.met[z["id"]] = (z["x"], z["y"], now)
                changed = True
        for zid in [i for i, m in self.met.items() if now - m[2] > MET_TTL_MIN]:
            del self.met[zid]
            changed = True
        if changed:
            self.met_version += 1

    def _map(self, line):
        self.map_lines += 1
        for m in line.get("missing") or ():
            if m not in self.missing:
                self.missing.append(m)
        sid = line.get("scanId")
        if line.get("mode") == "full" and isinstance(sid, int):
            if self._newest_scan is not None and sid < self._newest_scan:
                self.dropped_scans += 1
                return
            self._newest_scan = sid
        for s in line.get("squares") or ():
            self._square(s)

    def _square(self, s):
        if not isinstance(s, dict) or s.get("x") is None or s.get("y") is None:
            return
        x, y, z = s["x"], s["y"], s.get("z") or 0
        self.map[(x, y, z)] = s
        self.map_version += 1
        if s.get("building") is not None:
            self.buildings.add(s["building"])
        cs = s.get("containers") or []
        for i, c in enumerate(cs):
            old = self.containers.get((x, y, z, i))
            looted = set(old["looted"]) if old and old["type"] == c.get("type") else set()
            self.containers[(x, y, z, i)] = {"type": c.get("type"), "n": c.get("n") or 0,
                                             "items": list(c.get("items") or ()), "looted": looted}
        for k in [k for k in self.containers if k[:3] == (x, y, z) and k[3] >= len(cs)]:
            del self.containers[k]

    def _event(self, line):
        self.events.append(line)
        kind = line.get("event")
        if kind == "item_added":
            it = {"fullType": line.get("fullType"), "weight": line.get("weight")}
            if line.get("use") is not None:
                it["use"] = line["use"]
            if line.get("worn") is True:
                it["worn"] = True       # PZA/1.5.2: absent means not worn
            if line.get("rip") is not None:
                it["rip"] = line["rip"]   # PZA/1.5.2: cotton, denim or leather; absent means none
            self.inventory[line.get("itemId")] = it
            if self._sighting:
                self.first_sight.add(line.get("itemId"))
        elif kind == "item_removed":
            if self.inventory.pop(line.get("itemId"), None) is None:
                self.missing_items += 1
            self.marks.pop(line.get("itemId"), None)
            self.changes.pop(line.get("itemId"), None)
        elif kind == "item_changed":
            it = self.inventory.get(line.get("itemId"))
            if it is not None:
                self.changes[line.get("itemId")] = self.changes.get(line.get("itemId"), 0) + 1
                if line.get("use") is not None:
                    it["use"] = line["use"]
                if self.item_fields():   # a 1.5.2 line states both: absent is not worn, no class
                    for k, v in (("worn", line.get("worn") is True or None), ("rip", line.get("rip"))):
                        if v is None:
                            it.pop(k, None)
                        else:
                            it[k] = v
                for k in ("fluid", "amount"):
                    if line.get(k) is None:
                        it.pop(k, None)
                    else:
                        it[k] = line[k]
                if (self.marks.get(line.get("itemId")) or ("",))[0] in VESSEL_MARKS:
                    del self.marks[line.get("itemId")]
        elif kind == "damage":
            self.damage.append({"tag": line.get("tag"), "amount": line.get("amount"), "side": line.get("side"),
                                "wallMs": line.get("wallMs")})
        elif kind == "zombie_dead":
            self.zombies.pop(line.get("id"), None)
            if self.met.pop(line.get("id"), None) is not None:
                self.met_version += 1
        elif kind == "scan_dropped":
            self.scans_dropped.add(str(line.get("aid")))

    def item_fields(self):
        """Whether the last hello's mod version is 1.5.2 or later: its `item_added` and `item_changed` lines carry `worn`
        and `rip` (absent meaning not worn, no class: Task 10 fix 2). An older or unparsable version reads False."""
        m = re.match(r"(\d+)\.(\d+)\.(\d+)", str((self.hello or {}).get("mod") or ""))
        return m is not None and tuple(int(g) for g in m.groups()) >= (1, 5, 2)

    def can(self, action_type):
        """Whether the last hello's `caps` announce `action_type`: the planner sends a PZA/1.5 skill (aim, climb,
        bandage, rip, wash, fill) only to a build that takes it (ruling P24-G); no hello, no caps."""
        return action_type in ((self.hello or {}).get("caps") or ())

    # -- the server's side ----------------------------------------------------------------------------------------
    def merge_server(self, stats, wall_ms):
        self.server = {"stats": stats, "wallMs": wall_ms}

    def merge_damage(self, reply, wall_ms):
        """A `damage.watch` reply ({ok, counts, n, last = [{i, tag, amount, wall}], dropped}): each `last` record not
        yet seen lands in `damage` tagged `server` at `wall_ms`; `counts` is kept as the server's totals."""
        for r in reply.get("last") or ():
            if not isinstance(r, dict):
                continue
            i = r.get("i")
            if i in self.damage_seen_i:
                continue
            self.damage_seen_i.add(i)
            self.damage.append({"tag": r.get("tag"), "amount": r.get("amount"), "side": "server", "wallMs": wall_ms})
        if reply.get("counts") is not None:
            self.damage_counts_server = reply["counts"]

    # -- the planner's questions (Plan 21's heuristics) -----------------------------------------------------------
    def mark_looted(self, key, use=None):
        """Mark the container at `key` looted for `use` (one of USES), or for every use when `use` is None (a loot
        that took the whole container); an unknown key is ignored."""
        if key in self.containers:
            self.containers[key]["looted"] |= set(USES) if use is None else {use}

    def nearest_unlooted(self, want=None, exclude=()):
        """The key of the nearest non-empty container not looted for `want`, ties by key; with `want` (one of USES)
        only a container holding an item of that use and not yet looted for it, with None one marked for no use. A
        map line names full types only, so this keeps the dataset's `items.use_of` on a container's items. A key in
        `exclude` is never nearest."""
        mx, my = me_xy(self)
        best = None
        for key, c in self.containers.items():
            if not c["n"] or not c["items"] or key in exclude:
                continue
            if (want in c["looted"]) if want else c["looted"]:
                continue
            if want and not any(use_of(i) == want for i in c["items"]):
                continue
            rank = (math.hypot(key[0] - mx, key[1] - my), key)
            if best is None or rank < best:
                best = rank
        return best[1] if best else None

    def world_minutes(self):
        """Game minutes since the world began, `worldAge * 60` (monotonic across midnight) rounded to 1e-6 minute (so a
        whole minute carried in hours reads whole, and a TTL boundary falls on it), else (an older frame without
        worldAge) the frame's gameMin since the first one read, wrapped at 1440 (`(gameMin - first) % 1440`: D-7, the
        simpler of the two fixes, so no TTL site handles a None; the clock then falls back at each day's end, so a
        timer outlives at most the part of a day), else 0.0: the clock of every planner timer in game minutes."""
        wa = self.world_age
        if isinstance(wa, (int, float)) and not isinstance(wa, bool):
            return round(wa * 60.0, 6)
        gm = self.game_min
        if gm is None:
            return 0.0
        if self._gm0 is None:
            self._gm0 = gm
        return (gm - self._gm0) % 1440.0

    def mark_stuck(self, x, y):
        """Remember the walk target (x, y) as stuck at the current world_minutes() (the planner's, never a line's)."""
        self.stuck[(x, y)] = self.world_minutes()

    def unmark_stuck(self, x, y):
        """Drop the walk target (x, y)'s stuck mark (a climb over the route's fence ended done)."""
        self.stuck.pop((x, y), None)

    def _stuck_now(self):
        now = self.world_minutes()
        return {k for k, at in self.stuck.items() if now - at < STUCK_TTL_MIN}

    def mark_stuck_pair(self, frm, to):
        """A walk from square `frm` (x, y) to `to` failed `stuck` with the player moved under 0.5 tiles (P23-AP 1): the
        pair joins `stuck_run` when the run is from `frm` or a square touching it (fix round 1, M1: a half-tile drift
        across a square's edge), else starts a new run (the planner's, never a line's)."""
        run = self.stuck_run
        near = run is not None and max(abs(run["from"][0] - frm[0]), abs(run["from"][1] - frm[1])) <= 1
        self.stuck_run = {"from": run["from"] if near else frm, "to": (run["to"] if near else []) + [to],
                          "at": self.world_minutes()}

    def clear_stuck_run(self):
        """A walk that moved the player or arrived ends the run of stuck pairs."""
        self.stuck_run = None

    def stuck_here(self):
        """STUCK_AREA_N or more stuck pairs in a row from the run's square, the last within STUCK_TTL_MIN, the player
        within 1.0 tile of that square's centre (fix round 1, M1: not the exact floored square)."""
        run = self.stuck_run
        if run is None or len(run["to"]) < STUCK_AREA_N or self.world_minutes() - run["at"] >= STUCK_TTL_MIN:
            return False
        mx, my = me_xy(self)
        return math.hypot(mx - run["from"][0] - 0.5, my - run["from"][1] - 0.5) <= 1.0

    def unexplored_edge(self, woods_r=None):
        """The nearest open square with an unmapped neighbour, ties by (x, y); a square marked stuck within the last
        STUCK_TTL_MIN game minutes is left out, and so is a square `in_cone` of a met group (P24-B 2), and, with
        `woods_r` and a building known, a square with no building within `woods_r` tiles of its centre (`building_near`:
        the woods, ruling P24-Y). While `stuck_here` (P23-AP 1), only a square on the player's floor that the player's
        `flood` reaches and whose straight line from the player is clear (`line_clear` to its centre,
        `unknown_open=False`), else None."""
        mx, my = me_xy(self)
        skip = self._stuck_now() if self.stuck else ()
        cone = self.avoid_cone()
        boxes = list(self.building_boxes().values()) if woods_r is not None else []
        cands = []
        for (x, y, z), s in self.map.items():
            if s.get("solid") or (x, y) in skip:
                continue
            if cone is not None and self.in_cone(x, y, cone):
                continue
            if boxes and not any(_box_dist(b, x + 0.5, y + 0.5) <= woods_r for b in boxes):
                continue
            if all((x + dx, y + dy, z) in self.map for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue
            cands.append((math.hypot(x - mx, y - my), x, y, z))
        if not cands:
            return None
        if not self.stuck_here():
            best = min(cands)
            return best[1], best[2]
        if len(self.stuck_run["to"]) >= STUCK_AREA_N + STUCK_WALK_CAP:
            return None   # fix round 1, R2: STUCK_WALK_CAP walks in the open failed unmoved too: a loot or a scan
        floor = me_floor(self)
        reach = self.flood((int(math.floor(mx)), int(math.floor(my)), floor))
        for _, x, y, z in sorted(c for c in cands if c[3] == floor and (c[1], c[2], floor) in reach):
            if self.line_clear((mx, my), (x + 0.5, y + 0.5)):
                return x, y
        return None

    def flood(self, start, limit=REACH_LIMIT, r=None):
        """The squares a breadth-first flood from `start` (x, y, z) reaches over the kept map (P23-AP 1): each step to
        one of the 8 neighbours on its floor, mapped, not solid, the step not `blocked` with `climb=True` (a closed or
        locked door's edge is; a hoppable fence's is not, P24-C); `start` itself always, at most `limit` squares in
        all; with `r`, only squares within `r` tiles of `start` (Task 18 fix 1: the engage's reach, bounded round the
        player)."""
        start = tuple(start)
        seen, queue, i = {start}, [start], 0
        while i < len(queue):
            a = queue[i]
            i += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    b = (a[0] + dx, a[1] + dy, a[2])
                    if b in seen or (r is not None and math.hypot(b[0] - start[0], b[1] - start[1]) > r):
                        continue
                    if self._solid(b) or self.blocked(a, b, climb=True):
                        continue
                    seen.add(b)
                    queue.append(b)
                    if len(seen) >= limit:
                        return seen
        return seen

    def reachable(self, frm, to, limit=REACH_LIMIT):
        """`to` (x, y, z) lies within `flood(frm, limit)`: a way over the kept map's open steps (P23-AP 1)."""
        return tuple(to) in self.flood(frm, limit)

    def met_near(self, r=MET_VIEW_R):
        """The densest met window centred within `r` tiles of the player (the module docstring): `(cx, cy, n)`, else
        None; cached on (`met_version`, the player's position, `r`)."""
        px, py = me_xy(self)
        key = (self.met_version, px, py, r)
        if self._met_near is None or self._met_near[0] != key:
            self._met_near = (key, self._met_search(px, py, r))
        return self._met_near[1]

    def _met_search(self, px, py, r):
        """`met_near`'s bucketed search (the module docstring)."""
        reach = r + MET_R
        cells = {}
        for m in self.met.values():
            if math.hypot(m[0] - px, m[1] - py) <= reach:
                cells.setdefault(_cell(m[0], m[1]), []).append((m[0], m[1]))

        def around(c):
            i, j = _cell(c[0], c[1])
            return [p for di in (-1, 0, 1) for dj in (-1, 0, 1) for p in cells.get((i + di, j + dj), ())]

        starts = [own for _, own in sorted(cells.items())]
        for bi, bj in sorted({(i + di, j + dj) for i, j in cells for di in (-1, 0) for dj in (-1, 0)}):
            own = [p for di in (0, 1) for dj in (0, 1) for p in cells.get((bi + di, bj + dj), ())]
            if len(own) > len(cells.get((bi, bj), ())):    # a block adding to its corner cell: a group across a line
                starts.append(own)
        ranked = sorted(((len(around(_mean(own))), k, _mean(own)) for k, own in enumerate(starts)),
                        key=lambda t: (-t[0], t[1]))
        best = None
        for bound, _, c in ranked:
            if best is not None and bound < -best[0][0]:
                break                                # no window round this start can hold more than the best
            n = 0
            for _ in range(MET_SHIFTS + 1):          # the start, then shifted to its window's centroid
                d = math.hypot(c[0] - px, c[1] - py)
                inn = [p for p in around(c) if math.hypot(p[0] - c[0], p[1] - c[1]) <= MET_R] if d <= r else []
                if len(inn) <= n:
                    break
                n = len(inn)
                rank = (-n, d, c)
                if best is None or rank < best[0]:
                    best = (rank, inn)
                c = _mean(inn)
        if best is None:
            return None
        inn = best[1]
        return _mean(inn) + (len(inn),)

    def avoid_cone(self):
        """The bearing (degrees) of `met_near`'s window from the player while it holds MET_AVOID_N or more, else
        None (P24-B 2)."""
        m = self.met_near()
        if m is None or m[2] < MET_AVOID_N:
            return None
        px, py = me_xy(self)
        return bearing_deg(m[0] - px, m[1] - py)

    def in_cone(self, x, y, cone=None):
        """Whether square (x, y)'s centre lies within MET_AVOID_DEG of the avoid cone's bearing from the player (the
        module docstring); `cone` the bearing when read already."""
        cone = self.avoid_cone() if cone is None else cone
        if cone is None:
            return False
        px, py = me_xy(self)
        b = bearing_deg(x + 0.5 - px, y + 0.5 - py)
        if b is None:
            return False
        off = abs(b - cone) % 360.0
        return min(off, 360.0 - off) <= MET_AVOID_DEG + 1e-9

    def met_density(self, x, y, r=MET_R):
        """The distinct zombies of the met memory within `r` tiles of (x, y) (P24-A (a))."""
        return sum(1 for mx, my, _ in self.met.values() if math.hypot(mx - x, my - y) <= r)

    def met_window(self, r=MET_R):
        """The densest met window (the module docstring): `(cx, cy, n)`, else None with nothing met."""
        if not self.met:
            return None
        px, py = me_xy(self)
        pts = sorted((m[0], m[1]) for m in self.met.values())
        best = None
        for c in pts:
            inn = [p for p in pts if math.hypot(p[0] - c[0], p[1] - c[1]) <= r]
            rank = (-len(inn), math.hypot(c[0] - px, c[1] - py), c)
            if best is None or rank < best[0]:
                best = (rank, inn)
        inn = best[1]
        return sum(p[0] for p in inn) / len(inn), sum(p[1] for p in inn) / len(inn), len(inn)

    def nearest_zombie(self, exclude=()):
        """(id, zombie) nearest the current `me` by its last seen `x, y`, ties by id; None if none. A zombie kept up to
        ZOMBIE_TTL_S after it left the frames is ranked from where the player is now, never by its stored frame
        `dist` (the whole-pass review's M7); a zombie whose id is not an int (a nil read keys it None), without a
        position, or in `exclude` is never nearest."""
        mx, my = me_xy(self)
        best = None
        for zid, z in self.zombies.items():
            if not isinstance(zid, int) or isinstance(zid, bool) or zid in exclude:
                continue
            if z.get("x") is None or z.get("y") is None:
                continue
            rank = (math.hypot(z["x"] - mx, z["y"] - my), zid)
            if best is None or rank < best:
                best = rank
        return (best[1], self.zombies[best[1]]) if best else None

    # -- the square's edges, the line, interiors (Plan 23 Task 9, P23-K) -------------------------------------------
    def _edge(self, sq, field):
        """The edge `field` of the square at `sq`, True (blocked) when the square is unknown or the edge null."""
        s = self.map.get(sq)
        v = None if s is None else s.get(field)
        return True if v is None else bool(v)

    def _solid(self, sq):
        """A square unknown to the map counts solid."""
        s = self.map.get(sq)
        return s is None or bool(s.get("solid"))

    def _orth_blocked(self, a, b, climb=False):
        """The edge between two orthogonally adjacent squares: a square stores its own north and west edges. With
        `climb` a blocked edge whose holder carries its hop flag (`hopN`/`hopW` True) is crossable."""
        if b[1] == a[1] - 1:
            holder, side = a, "N"
        elif b[1] == a[1] + 1:
            holder, side = b, "N"
        elif b[0] == a[0] - 1:
            holder, side = a, "W"
        else:
            holder, side = b, "W"
        if not self._edge(holder, "block" + side):
            return False
        return not (climb and (self.map.get(holder) or {}).get("hop" + side) is True)

    def blocked(self, a, b, unknown_open=False, climb=False):
        """Whether the step between two adjacent squares `(x, y, z)` is blocked (the module docstring's rule); a
        pair that is not adjacent on one floor raises ValueError, the same square is never blocked, and a step to or
        from a square the map does not hold always is. `unknown_open` (the flee's steer probe): a step to or from an
        unknown square never is, and a diagonal's unknown corner square is neither solid nor bounded by a blocked
        edge (a known corner is read as by default; survival 1 fix round 3, F5). `climb` (PZA/1.4, ruling P24-C): an
        orthogonal step over a blocked edge whose square carries the hop flag is not blocked, the path follower
        climbing it at a walk; a diagonal step never climbs, its corner edges read as by default."""
        a, b = tuple(a), tuple(b)
        dx, dy = b[0] - a[0], b[1] - a[1]
        if a[2] != b[2] or abs(dx) > 1 or abs(dy) > 1:
            raise ValueError("blocked: not adjacent: %r %r" % (a, b))
        if dx == 0 and dy == 0:
            return False
        if a not in self.map or b not in self.map:
            return not unknown_open
        if dx == 0 or dy == 0:
            return self._orth_blocked(a, b, climb)
        corners = [c for c in ((b[0], a[1], a[2]), (a[0], b[1], a[2])) if not unknown_open or c in self.map]
        if any(self._solid(c) for c in corners):
            return True
        return any(self._orth_blocked(a, c) or self._orth_blocked(c, b) for c in corners)

    @staticmethod
    def _bresenham(x0, y0, x1, y1):
        """The squares of the integer line from (x0, y0) to (x1, y1), both ends included, 8-connected."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
        err = dx + dy
        out = [(x0, y0)]
        while (x0, y0) != (x1, y1):
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
            out.append((x0, y0))
        return out

    def line_clear(self, a, b, unknown_open=False):
        """Whether the line from position `a` to `b` ((x, y) floats, on the player's floor) crosses no blocked edge
        and no solid or unknown square strictly between its end squares. The walk is Bresenham's on the floored ends
        (integer squares), not the float line between the two positions. `unknown_open`: an unknown square is
        neither solid nor bounded by a blocked edge (the module docstring)."""
        z = me_floor(self)
        cells = self._bresenham(int(math.floor(a[0])), int(math.floor(a[1])), int(math.floor(b[0])),
                                int(math.floor(b[1])))
        sqs = [(x, y, z) for x, y in cells]
        if unknown_open:
            if any(sq in self.map and self._solid(sq) for sq in sqs[1:-1]):
                return False
            return not any(self.blocked(p, q, unknown_open=True) for p, q in zip(sqs, sqs[1:]))
        if any(self._solid(sq) for sq in sqs[1:-1]):
            return False
        return not any(self.blocked(p, q) for p, q in zip(sqs, sqs[1:]))

    def reachable_adjacent(self, target_xy, z):
        """The target square's 8 neighbours that are mapped, not solid, and whose step to the target is not blocked,
        nearest the player first (by the neighbour's centre, ties by x, y)."""
        tx, ty = int(math.floor(target_xy[0])), int(math.floor(target_xy[1]))
        t = (tx, ty, z)
        mx, my = me_xy(self)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (tx + dx, ty + dy, z)
                if n == t or self._solid(n) or self.blocked(n, t):
                    continue
                out.append((math.hypot(n[0] + 0.5 - mx, n[1] + 0.5 - my), n[0], n[1], n))
        return [r[3] for r in sorted(out)]

    def memo(self, key, fn):
        """`fn()`, computed once per map version for `key` (a read of the map only; the answer is shared)."""
        hit = self._memo.get(key)
        if hit is not None and hit[0] == self.map_version:
            return hit[1]
        value = fn()
        self._memo[key] = (self.map_version, value)
        return value

    def water_squares(self):
        """[((x, y, z), water record)] of the map's squares carrying a `water` record, sorted by square; memoised per
        map version (read it, never change it)."""
        return self.memo(("water",), lambda: sorted(((sq, rec["water"]) for sq, rec in self.map.items()
                                                     if isinstance(rec.get("water"), dict)), key=lambda t: t[0]))

    def water_sources(self, r=math.inf):
        """[(dist, (x, y, z), water record)] of the known water sources (the module docstring): on the player's floor,
        water in them, within `r` tiles by the square's centre, a dry one left out (`dry_now`), one in
        `tainted_sources` read tainted; nearest first, ties by the square."""
        floor = me_floor(self)
        mx, my = me_xy(self)
        dry = self.dry_now()
        out = []
        for sq, w in self.water_squares():
            if sq[2] != floor or sq in dry:
                continue
            if sq in self.tainted_sources:
                w = dict(w, tainted=True)
            if not (w.get("infinite") is True or (isinstance(w.get("amount"), (int, float)) and w["amount"] > 0)):
                continue
            d = math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my)
            if d <= r:
                out.append((d, sq, w))
        return sorted(out, key=lambda t: (t[0], t[1]))

    def mark_dry(self, sq):
        """Leave the water square `sq` (x, y, z) out of `water_sources` for SOURCE_RETRY_MIN game minutes."""
        self.dry[sq] = self.world_minutes()

    def note_door_fail(self, sq, reason):
        """A door at square `sq` (x, y, z) failed `reason` (ruling P24-Z: an open locked, a close interrupted, its
        approach not adjacent, a loot's route stood against it): the second failure within DOOR_RETRY_MIN marks it
        (`door_marks`, with the reason) and clears its count. True when this one marked it. The planner's, never a
        line's; not in `to_json`."""
        now = self.world_minutes()
        fails = [f for f in self.door_fails.get(sq, []) if now - f[0] < DOOR_RETRY_MIN] + [(now, reason)]
        if len(fails) < DOOR_FAILS_TO_MARK:
            self.door_fails[sq] = fails
            return False
        self.door_fails.pop(sq, None)
        self.door_marks[sq] = (now, reason)
        return True

    def marked_doors(self):
        """The door squares marked within DOOR_RETRY_MIN game minutes (P24-Z): never tried again meanwhile."""
        now = self.world_minutes()
        return {sq for sq, (at, _) in self.door_marks.items() if now - at < DOOR_RETRY_MIN}

    def door_near(self, xy, z, r):
        """The mapped door square on floor `z` whose centre lies nearest the point `xy` within `r` tiles, read open
        or not, ties by the square; None with none (P24-Z: the door a loot's route stood against)."""
        best = None
        for sq in (d for ds in self._indexes()[2].values() for d in ds):
            if sq[2] != z:
                continue
            d = math.hypot(sq[0] + 0.5 - xy[0], sq[1] + 0.5 - xy[1])
            if d <= r and (best is None or (d, sq) < best):
                best = (d, sq)
        return None if best is None else best[1]

    def dry_now(self):
        """The squares `mark_dry` marked within SOURCE_RETRY_MIN game minutes."""
        if not self.dry:
            return set()
        now = self.world_minutes()
        return {sq for sq, at in self.dry.items() if now - at < SOURCE_RETRY_MIN}

    def _index(self):
        """One walk of the map: ({building: [room squares sorted]}, {building: [door squares sorted]})."""
        rooms, doors = {}, {}
        for sq, s in self.map.items():
            if s.get("room") is not None:
                rooms.setdefault(s.get("building"), []).append(sq)
            if s.get("door") is not None:
                doors.setdefault(self.door_building(sq), []).append(sq)
        return {b: sorted(v) for b, v in rooms.items()}, {b: sorted(v) for b, v in doors.items()}

    def _indexes(self):
        if self._indexed is None or self._indexed[0] != self.map_version:
            self._indexed = (self.map_version,) + self._index()
        return self._indexed

    def interiors(self):
        """{building: [(x, y, z) sorted]}: the mapped squares with a room, grouped by their building (cached per map
        version: read it, never change it)."""
        return self._indexes()[1]

    def doors_of(self, building):
        """The mapped squares of `building` with a door (`door_building`), sorted (cached per map version: read it,
        never change it)."""
        return self._indexes()[2].get(building, [])

    def building_boxes(self):
        """{building: (minx, miny, maxx, maxy)}: the bounding box of each known building's room squares (any floor; a
        building id None, the rooms the scan gave no building, left out), cached per map version (`memo`): the goal
        layer's building destinations (ruling P24-Y, Plan 24 Task 18)."""
        def boxes():
            out = {}
            for b, rooms in self.interiors().items():
                if b is None:
                    continue
                xs, ys = [sq[0] for sq in rooms], [sq[1] for sq in rooms]
                out[b] = (min(xs), min(ys), max(xs), max(ys))
            return out
        return self.memo(("building_boxes",), boxes)

    def building_dist(self, x, y, b):
        """Tiles from the point (x, y) to building `b`'s box (`building_boxes`, its squares' full extent), 0.0 inside
        it, None for a building the map does not hold."""
        box = self.building_boxes().get(b)
        return None if box is None else _box_dist(box, x, y)

    def nearest_building(self, x, y, exclude=()):
        """(tiles, building) of the known building whose box is nearest the point (x, y), ties by the building's
        JSON; a building in `exclude` left out; None with none known."""
        best = None
        for b in self.building_boxes():
            if b in exclude:
                continue
            rank = (self.building_dist(x, y, b), json.dumps(b, sort_keys=True), b)
            if best is None or rank[:2] < best[:2]:
                best = rank
        return None if best is None else (best[0], best[2])

    def building_near(self, x, y, r):
        """A known building's box lies within `r` tiles of the point (x, y) (the woods test of ruling P24-Y: a square
        with none within WOODS_R is the woods)."""
        nb = self.nearest_building(x, y)
        return nb is not None and nb[0] <= r

    def door_building(self, sq):
        """The building a door square belongs to: its own `building`, else (survival 3 fix round 1, the review's R2)
        the building of the room square across its first flagged edge, north then west. A door stands on its square's
        north or west edge, so a door on a room's south or east wall is kept on the outdoor square below or right of
        it, and the scan gives a square with no room no building (`IsoGridSquare.getBuilding` nil: E3's kitchen door
        (10721, 10638), open, `building` None, its room square (10721, 10637) north of it); None when neither reads
        one."""
        s = self.map.get(sq) or {}
        if s.get("building") is not None:
            return s.get("building")
        for edge, n in (("edgeN", (sq[0], sq[1] - 1, sq[2])), ("edgeW", (sq[0] - 1, sq[1], sq[2]))):
            o = self.map.get(n) or {}
            if s.get(edge) and o.get("room") is not None:
                return o.get("building")
        return None

    def _window_edge(self, a, b):
        """The edge between two orthogonally adjacent squares is a window's: the square holding it (a square keeps its
        own north and west edges) carries a `window` record and that edge's `edgeN`/`edgeW` reads true. With both its
        edges flagged the record does not say which holds the window, so both read as windows."""
        if b[1] != a[1]:
            holder, field = (a, "edgeN") if b[1] == a[1] - 1 else (b, "edgeN")
        else:
            holder, field = (a, "edgeW") if b[0] == a[0] - 1 else (b, "edgeW")
        s = self.map.get(holder) or {}
        return s.get("window") is not None and bool(s.get(field))

    def door_way(self, sq):
        """The way an exterior door at `sq` leads (Plan 23 survival 3, the coordinator's amendment 5 to ruling P23-AM:
        E2's and E3's shelter door (10725, 10629) of building 2 was a bedroom's door to the corridor, counted exterior
        through the outdoor square across the bedroom's north wall): `(room square, outside square)`, else None. The
        door stands on one of `sq`'s own edges (a square keeps its north and west edges), one whose `edgeN`/`edgeW`
        reads true; with the door read open, only an edge that reads not blocked (`blockN`/`blockW` False: an open
        door's edge is, a wall's never). Each such edge is read across, as `openings` reads a step: it leads out when
        one side is a room square (the door's building, `door_building`) and the other a mapped, non-solid square
        with no room (a door on a room's south or east wall is kept on the outdoor square, whose own `building` the
        scan reads None, `sq` then the outside one); it leads in when both
        sides are room squares. The door is exterior when an edge leads out and none leads in (a closed door on a room's
        corner square, a wall on its other edge, reads one of each and is not one); the first of north, west."""
        s = self.map.get(sq)
        if s is None or s.get("door") is None:
            return None
        is_open = bool(s["door"].get("open"))
        out, inward = [], False
        for edge, block, n in (("edgeN", "blockN", (sq[0], sq[1] - 1, sq[2])),
                               ("edgeW", "blockW", (sq[0] - 1, sq[1], sq[2]))):
            if not s.get(edge) or (is_open and s.get(block) is not False):
                continue
            o = self.map.get(n)
            if o is None or o.get("solid") or s.get("solid"):
                continue
            rooms = [q for q, r in ((sq, s), (n, o)) if r.get("room") is not None]
            if len(rooms) == 2:
                inward = True
            elif len(rooms) == 1:   # the door's building is the room's (`door_building`)
                out.append((rooms[0], n if rooms[0] == sq else sq))
        return out[0] if out and not inward else None

    def openings(self, building):
        """The building's openings (the module docstring): `(room square, outside square)` pairs, sorted, each step
        between the two read not blocked and not a window's edge (`_window_edge`); memoised per map version (read it,
        never change it)."""
        def walk():
            out = []
            for sq in self.interiors().get(building, ()):
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    n = (sq[0] + dx, sq[1] + dy, sq[2])
                    s = self.map.get(n)
                    if s is None or s.get("solid") or s.get("room") is not None:
                        continue
                    if not self._orth_blocked(sq, n) and not self._window_edge(sq, n):
                        out.append((sq, n))
            return sorted(out)
        return self.memo(("openings", building), walk)

    # -- the inventory by use and the empties (Plan 23 Task 9, P23-D) -----------------------------------------------
    def mark(self, item_id, reason):
        """Mark a held item with `reason` (one of MARK_REASONS), replacing its mark, at the current world minute: read
        by `world_minutes` for `refused` (its TTL's clock, as before the fold), else without fixing the gameMin
        fallback's origin (`_peek_minutes`: a mark never moves a timer's clock)."""
        if reason not in MARK_REASONS:
            raise ValueError("World.mark: %r not in %s" % (reason, MARK_REASONS))
        self.marks[item_id] = (reason, self.world_minutes() if reason == "refused" else self._peek_minutes())

    def _peek_minutes(self):
        """`world_minutes` without its first-read side effect: None while the gameMin fallback has no origin."""
        wa = self.world_age
        if isinstance(wa, (int, float)) and not isinstance(wa, bool):
            return round(wa * 60.0, 6)
        if self.game_min is None or self._gm0 is None:
            return None
        return (self.game_min - self._gm0) % 1440.0

    def marked(self, reason):
        """{id: world minute} of the items marked `reason`."""
        return {i: at for i, (r, at) in self.marks.items() if r == reason}

    @property
    def empty_ids(self):
        """The held ids the planner found empty (`mark_empty`)."""
        return set(self.marked("empty"))

    @property
    def refused(self):
        """{held food id: world minute the Lua refused its consume} (`mark_refused`)."""
        return self.marked("refused")

    def tainted_ids(self):
        """The held ids the need's fill filled from a tainted source (`tainted`), and any held item whose record
        names `TaintedWater` as its fluid (an `item_changed` line's), less the ones marked `undrinkable`."""
        out = set(self.marked("tainted")) | {i for i, it in self.inventory.items() if it.get("fluid") == "TaintedWater"}
        return out - set(self.marked("undrinkable"))

    def hop_ahead(self, frm, to):
        """The fence square (x, y) of the hoppable edge the straight line from position `frm` toward `to` crosses at
        its first step out of `frm`'s square, else None (Plan 24 Task 10, ruling P24-G 4: a route's next edge): the
        step blocked (`blocked`) and crossable with `climb=True` (its square's `hopN`/`hopW` true), the fence's square
        the edge's holder (the square storing that north or west edge); a diagonal first step is read through either
        corner square, open and unblocked on its other leg. The line is Bresenham's on the floored ends, on the
        player's floor."""
        z = me_floor(self)
        cells = self._bresenham(int(math.floor(frm[0])), int(math.floor(frm[1])), int(math.floor(to[0])),
                                int(math.floor(to[1])))
        if len(cells) < 2:
            return None
        a, b = (cells[0][0], cells[0][1], z), (cells[1][0], cells[1][1], z)
        if a not in self.map or b not in self.map:
            return None
        if a[0] == b[0] or a[1] == b[1]:
            return self._hop(a, b)
        for c in ((b[0], a[1], z), (a[0], b[1], z)):
            if c not in self.map or self._solid(c):
                continue
            first, second = self._hop(a, c), self._hop(c, b)
            if first is not None and not self.blocked(c, b):
                return first
            if second is not None and not self.blocked(a, c):
                return second
        return None

    def fence_on_line(self, a, b):
        """The straight line from position `a` to `b` ((x, y) floats, on the player's floor; Bresenham's on the floored
        ends) crosses a known hoppable edge (`_hop`: blocked, climbable): an orthogonal step over one, or a diagonal
        step with one on either leg (Task 18 fix 1, the review's ruling 2: a chasing zombie across a fence is not
        sought; the fence is the chokepoint). An unmapped square is never a fence."""
        z = me_floor(self)
        sqs = [(x, y, z) for x, y in self._bresenham(int(math.floor(a[0])), int(math.floor(a[1])),
                                                     int(math.floor(b[0])), int(math.floor(b[1])))]
        for p, q in zip(sqs, sqs[1:]):
            if p not in self.map or q not in self.map:
                continue
            if p[0] == q[0] or p[1] == q[1]:
                if self._hop(p, q) is not None:
                    return True
                continue
            for c in ((q[0], p[1], z), (p[0], q[1], z)):
                if c in self.map and (self._hop(p, c) is not None or self._hop(c, q) is not None):
                    return True
        return False

    def _hop(self, a, b):
        """The fence square of the orthogonal step a -> b when it is blocked but climbable, else None."""
        if not self.blocked(a, b) or self.blocked(a, b, climb=True):
            return None
        holder = a if (b[1] == a[1] - 1 or b[0] == a[0] - 1) else b
        return holder[0], holder[1]

    @property
    def no_effect_ids(self):
        """The held ids whose consume moved no stat (`mark_no_effect`, P24-F)."""
        return set(self.marked("no_effect"))

    def mark_empty(self, item_id):
        """Remember a held item as empty (the planner's, never a line's): `by_use` moves a `water` item to `container`
        (a drinkable vessel, empty, for the ticks before its `item_changed` arrives, and on a log without one)."""
        self.mark(item_id, "empty")

    def mark_refused(self, item_id):
        """Remember a held food the Lua refused to consume, at the current world minute (the planner's, never a
        line's): `by_use` reads it `other` for REFUSED_TTL_MIN world minutes, so the need does not pick it again
        meanwhile (and `spare()` may drop it only then); afterwards it is food again."""
        self.mark(item_id, "refused")

    def note_kill(self, zid):
        """Count zombie `zid` killed (the planner's, never a line's: ruling P24-Q, Plan 24 Task 12, the iteration's
        metric): a Fight read `targetDead` on its attack's or aim's result. True when it is a new kill, so a zombie
        read dead by two results counts once."""
        if zid is None or zid in self.killed:
            return False
        self.killed.add(zid)
        return True

    @property
    def kills(self):
        """The session's kills so far (`note_kill`): the view tells the goal source, `to_json` carries it."""
        return len(self.killed)

    def mark_no_effect(self, item_id):
        """Remember a held item whose consume ended `done` and moved no stat (the planner's, never a line's, P24-F):
        `by_use` reads it `other` while it is held, so the need moves to the next item of its use."""
        self.mark(item_id, "no_effect")

    def refused_now(self):
        """The ids whose refusal is younger than REFUSED_TTL_MIN world minutes (the clock read only when one is
        marked: `world_minutes` fixes its gameMin fallback's origin at its first read)."""
        refused = self.refused
        if not refused:
            return set()
        now = self.world_minutes()
        return {i for i, at in refused.items() if now - at < REFUSED_TTL_MIN}

    def by_use(self):
        """{use: [ids sorted]} for every use in USES: the inventory's ids by the item's `use` (else `items.use_of` of
        its fullType; a `food` the dataset marks `cant_eat` reads `other`, a stray `use` falls back to the dataset), an
        id in `empty_ids` read as `container` rather than `water`, one refused within REFUSED_TTL_MIN (`refused_now`) as
        `other` rather than `food`, one in `no_effect_ids` as `other` whatever its use."""
        out = {u: [] for u in USES}
        refused = self.refused_now()
        empty, no_effect = (self.empty_ids, self.no_effect_ids) if self.marks else ((), ())
        filled = set(self.marked("filled")) if self.marks else ()
        undrinkable = set(self.marked("undrinkable")) if self.marks else ()
        for iid, it in self.inventory.items():
            use = it.get("use")
            if use not in USES:                       # no use, or a stray value: the dataset's answer, never a raise
                use = use_of(it.get("fullType"))
            elif use == "food" and cant_eat(it.get("fullType")):
                use = "other"                         # N-3: the dataset overrides the engine's IsFood for a sealed can
            if use == "water" and iid in empty and iid not in no_effect and iid not in undrinkable:
                use = "container"                     # Task 9 fix 2: an emptied vessel is still a vessel
            elif ((use == "water" and iid in empty) or (use == "food" and iid in refused) or iid in no_effect
                    or iid in undrinkable):
                use = "other"
            elif iid in filled:
                use = "water"
            out[use].append(iid)
        return {u: sorted(v, key=_num_first) for u, v in out.items()}

    # -- serialisation --------------------------------------------------------------------------------------------
    def to_json(self):
        """Byte-stable: sorted keys, indent 1, tuple keys as "x,y,z", sets sorted, deques as lists."""
        d = {g: getattr(self, g) for g in GROUPS}
        d.update({
            "gameMin": self.game_min,
            "frameWallMs": self.frame_wall_ms,
            "zombies": {str(k): v for k, v in self.zombies.items()},
            "map": {_key(k): v for k, v in self.map.items()},
            "containers": {_key(k): dict(v, looted=sorted(v["looted"]) or False)
                           for k, v in self.containers.items()},
            "buildings": sorted(self.buildings, key=lambda b: json.dumps(b, sort_keys=True)),
            "inventory": {str(k): v for k, v in self.inventory.items()},
            "damage": list(self.damage),
            "damageSeenI": sorted(self.damage_seen_i, key=_num_first),
            "damageCountsServer": self.damage_counts_server,
            "events": list(self.events),
            "acts": self.acts,
            "hello": self.hello,
            "lastReply": self.last_reply,
            "server": self.server,
            "missing": self.missing,
            "unknownKinds": self.unknown_kinds,
            "missingItems": self.missing_items,
            "droppedScans": self.dropped_scans,
            "mapLines": self.map_lines,
        })
        if self.empty_ids:
            d["emptyIds"] = sorted(self.empty_ids, key=_num_first)
        refused = self.refused_now()
        if refused:
            d["refusedIds"] = sorted(refused, key=_num_first)
        if self.no_effect_ids:
            d["noEffectIds"] = sorted(self.no_effect_ids, key=_num_first)
        if self.killed:
            d["kills"] = self.kills   # P24-Q: only once a kill is read, so a line replay's bytes keep theirs
        return json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False)
