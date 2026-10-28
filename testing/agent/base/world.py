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
carry it.

The server's side comes in through `merge_server(stats, wall_ms)` and `merge_damage(reply, wall_ms)`, a
`damage.watch` reply whose `last` records not yet seen (by `i`) land in `damage` tagged `server` (spec § 9).

Plan 23 Task 9 (P23-D, P23-K) adds the planner's reads of the kept map and the inventory:
- `blocked(a, b)`: the edge between two adjacent squares, read as the jar reads `IsoGridSquare.isBlockedTo`
  (`docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md` § 1): a square stores only its own north and west edges
  (`blockN`, `blockW`, movement-blocking: a wall, a closed or barricaded door, an intact closed window), so the north
  neighbour reads `a`'s `blockN`, the south `b`'s, the west `a`'s `blockW`, the east `b`'s; a diagonal is blocked when
  any of the four edges meeting at the shared corner is, or either corner square is solid. Unlike the jar (which reads
  an unloaded neighbour's edge open), an unknown square or a null edge counts blocked: the planner never assumes a way.
- `line_clear(a, b)`: Bresenham over the squares from `a` to `b` (positions floored, on the player's floor), false at
  any blocked edge a step crosses (`blocked`) or any solid or unknown square strictly between the ends. It reads the
  blocked edges, never `edgeN`/`edgeW` (any wall, window or door edge whatever its state), which the square record
  keeps for the view and a later sight reading (ruling P23-K). With `unknown_open=True` (the flee's steer probe, Plan
  23 survival 1 fix round 2) an unknown square is open ground: only a known solid square, or a blocked edge between
  two known squares, refuses the line.
- `reachable_adjacent(target_xy, z)`, `interiors()`, `doors_of(building)`. The map walk behind the last two is cached
  per map version (fix wave P, M-4): `map_version` rises on every square applied, and `_index()` (one walk: the room
  squares and the door squares by building) is rebuilt lazily on the first read after it moved; `memo(key, fn)`
  keeps any other read of the map (the night's exterior doors) for the same version. A cached answer is shared, so a
  caller only reads it.
- `by_use()`: the inventory's ids by the item's own `use` (the engine's answer, Plan 23 Task 9b), else
  `agent.base.items.use_of` (the
  dataset; a `food` the dataset marks `cant_eat` reads `other`), an id the planner marked empty (`mark_empty`, kept in
  `empty_ids` and dropped with its item) moved from `water` to `other`,
  and an id the planner found refused (`mark_refused`, fix wave P I-4: a food whose consume ended `failed "not
  valid"`, kept in `refused` {id: the world minute of its refusal} and dropped with its item) moved from `food` to
  `other` for REFUSED_TTL_MIN (120) world minutes from the refusal only (ruling P23-AD: a refusal may be passing, the
  vanilla eat refusing a character that ate too much lately), so `spare()` may drop a refused food only inside that
  window;
  `nearest_unlooted(want)` keys on the same use. `to_json` carries `emptyIds` and `refusedIds` (the ids excluded now)
  sorted, each only while it is non-empty,
  so a World that never marked one serialises as before (the replay goldens keep their bytes). For the same reason a
  container's `looted` set serialises as its uses sorted, or `false` while it is empty.
"""
import json
import math
from collections import deque

from agent.base.items import USES, cant_eat, use_of

ZOMBIE_TTL_S = 10
STUCK_TTL_MIN = 60   # game minutes an edge whose walk ended stuck is left out of unexplored_edge
REFUSED_TTL_MIN = 120   # world minutes a food whose consume was refused `not valid` reads `other` (P23-AD)
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


def _num_first(v):
    """A sort key: numbers ascending first, then anything else by its JSON."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (0, v, "")
    return (1, 0, json.dumps(v, sort_keys=True))


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
        self.empty_ids = set()       # the held ids the planner found empty (mark_empty), never a line's
        self.refused = {}            # held food id -> world minute the Lua refused its consume (mark_refused)
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
        self._newest_scan = None
        self.damage_seen_i = set()

    def _reply(self, line):
        self.last_reply = line

    def _act(self, line):
        self.acts[str(line.get("aid"))] = line

    def _frame(self, line):
        wall = line.get("wallMs", 0)
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
            self.inventory[line.get("itemId")] = it
        elif kind == "item_removed":
            if self.inventory.pop(line.get("itemId"), None) is None:
                self.missing_items += 1
            self.empty_ids.discard(line.get("itemId"))
            self.refused.pop(line.get("itemId"), None)
        elif kind == "damage":
            self.damage.append({"tag": line.get("tag"), "amount": line.get("amount"), "side": line.get("side"),
                                "wallMs": line.get("wallMs")})
        elif kind == "zombie_dead":
            self.zombies.pop(line.get("id"), None)
        elif kind == "scan_dropped":
            self.scans_dropped.add(str(line.get("aid")))

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

    def _stuck_now(self):
        now = self.world_minutes()
        return {k for k, at in self.stuck.items() if now - at < STUCK_TTL_MIN}

    def unexplored_edge(self):
        """The nearest open square with an unmapped neighbour, ties by (x, y); a square marked stuck within the last
        STUCK_TTL_MIN game minutes is left out."""
        mx, my = me_xy(self)
        skip = self._stuck_now() if self.stuck else ()
        best = None
        for (x, y, z), s in self.map.items():
            if s.get("solid") or (x, y) in skip:
                continue
            if all((x + dx, y + dy, z) in self.map for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue
            rank = (math.hypot(x - mx, y - my), x, y)
            if best is None or rank < best:
                best = rank
        return (best[1], best[2]) if best else None

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

    def _orth_blocked(self, a, b):
        """The edge between two orthogonally adjacent squares: a square stores its own north and west edges."""
        if b[1] == a[1] - 1:
            return self._edge(a, "blockN")
        if b[1] == a[1] + 1:
            return self._edge(b, "blockN")
        if b[0] == a[0] - 1:
            return self._edge(a, "blockW")
        return self._edge(b, "blockW")

    def blocked(self, a, b):
        """Whether the step between two adjacent squares `(x, y, z)` is blocked (the module docstring's rule); a
        pair that is not adjacent on one floor raises ValueError, the same square is never blocked, and a step to or
        from a square the map does not hold always is."""
        a, b = tuple(a), tuple(b)
        dx, dy = b[0] - a[0], b[1] - a[1]
        if a[2] != b[2] or abs(dx) > 1 or abs(dy) > 1:
            raise ValueError("blocked: not adjacent: %r %r" % (a, b))
        if dx == 0 and dy == 0:
            return False
        if a not in self.map or b not in self.map:
            return True
        if dx == 0 or dy == 0:
            return self._orth_blocked(a, b)
        c1, c2 = (b[0], a[1], a[2]), (a[0], b[1], a[2])
        if self._solid(c1) or self._solid(c2):
            return True
        return (self._orth_blocked(a, c1) or self._orth_blocked(a, c2) or self._orth_blocked(c1, b)
                or self._orth_blocked(c2, b))

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
            return not any(p in self.map and q in self.map and self.blocked(p, q) for p, q in zip(sqs, sqs[1:]))
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

    def _index(self):
        """One walk of the map: ({building: [room squares sorted]}, {building: [door squares sorted]})."""
        rooms, doors = {}, {}
        for sq, s in self.map.items():
            if s.get("room") is not None:
                rooms.setdefault(s.get("building"), []).append(sq)
            if s.get("door") is not None:
                doors.setdefault(s.get("building"), []).append(sq)
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
        """The mapped squares of `building` with a door, sorted (cached per map version: read it, never change it)."""
        return self._indexes()[2].get(building, [])

    # -- the inventory by use and the empties (Plan 23 Task 9, P23-D) -----------------------------------------------
    def mark_empty(self, item_id):
        """Remember a held item as empty (the planner's, never a line's): `by_use` moves it from `water` to `other`."""
        self.empty_ids.add(item_id)

    def mark_refused(self, item_id):
        """Remember a held food the Lua refused to consume, at the current world minute (the planner's, never a
        line's): `by_use` reads it `other` for REFUSED_TTL_MIN world minutes, so the need does not pick it again
        meanwhile (and `spare()` may drop it only then); afterwards it is food again."""
        self.refused[item_id] = self.world_minutes()

    def refused_now(self):
        """The ids whose refusal is younger than REFUSED_TTL_MIN world minutes."""
        now = self.world_minutes()
        return {i for i, at in self.refused.items() if now - at < REFUSED_TTL_MIN}

    def by_use(self):
        """{use: [ids sorted]} for every use in USES: the inventory's ids by the item's `use` (else `items.use_of` of
        its fullType; a `food` the dataset marks `cant_eat` reads `other`, a stray `use` falls back to the dataset), an
        id in `empty_ids` read as `other` rather than `water`, one refused within REFUSED_TTL_MIN (`refused_now`) as
        `other` rather than `food`."""
        out = {u: [] for u in USES}
        refused = self.refused_now() if self.refused else ()
        for iid, it in self.inventory.items():
            use = it.get("use")
            if use not in USES:                       # no use, or a stray value: the dataset's answer, never a raise
                use = use_of(it.get("fullType"))
            elif use == "food" and cant_eat(it.get("fullType")):
                use = "other"                         # N-3: the dataset overrides the engine's IsFood for a sealed can
            if (use == "water" and iid in self.empty_ids) or (use == "food" and iid in refused):
                use = "other"
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
        refused = self.refused_now() if self.refused else ()
        if refused:
            d["refusedIds"] = sorted(refused, key=_num_first)
        return json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False)
