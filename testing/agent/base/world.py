"""World (Plan 22 Task 9, spec § 8): the planner's picture of the game, a pure function of the PZA/1 lines it is given.

It reads what the transport gives: keyed full dicts, every delta frame already merged (`FileTransport.lines()`).
`apply(line)` dispatches on `line["kind"]`; an unknown kind counts in `unknown_kinds` and never raises.

- `frame`: each group (`me`, `stats`, `body`, `load`, `weapon`, `action`, `act`, `cost`) kept as the dict the frame
  carries, None when the frame's group is null; `game_min`, `frame_wall_ms`; zombies keyed by id with
  `seenWallMs = wallMs`, a zombie unseen for more than `ZOMBIE_TTL_S` aged out at the next frame. No clock is read.
- `map`: each square applied at once (no whole-scan hold): `map[(x, y, z)]` the square dict as decoded, its
  containers at `containers[(x, y, z, i)] = {type, n, items, looted}`, a looted mark kept across a re-scan of the same
  square and type (Plan 21's rule), a container index the new square no longer has dropped; `buildings` the set of
  building names seen. A `full` part whose `scanId` is below the newest seen is dropped and counted in
  `dropped_scans`; a delta is never dropped. `map_lines` counts every map line, `missing` is the union of every map
  line's missing names in first-seen order.
- `event`: every event line in `events` (deque 500); `item_added`/`item_removed` build `inventory[itemId] =
  {fullType, weight}` (ruling P22-2), an unknown id's removal counted in `missing_items`; a client `damage` event
  appends `{tag, amount, side, wallMs}` to `damage` (deque 500); `zombie_dead` drops the zombie.
- `act`: `acts[str(aid)]` the last act line for the aid. `hello`: the last hello line, and a new session: the Lua
  restarts its `scanId` and the server's `damage.watch` record numbers restart with the server, so a hello resets the
  newest scanId seen and `damage_seen_i` (else a relaunched client's scans would all be dropped as older).
  `reply`: `last_reply`.

The server's side comes in through `merge_server(stats, wall_ms)` and `merge_damage(reply, wall_ms)`, a
`damage.watch` reply whose `last` records not yet seen (by `i`) land in `damage` tagged `server` (spec § 9).

HEURISTIC: FOOD_RX and WATER_RX guess from an item's fullType whether a container holds food or drink (Plan 21's,
widened): the prefix words `Canned` and `Tinned` take any suffix, so `Base.CannedMilk` and `Base.TinnedSoup` match,
`Macandcheese` and `PowerBar` are named, every other name keeps its trailing word boundary (`Base.Hammer` is not
`Ham`), and water names `WaterBottle` and `WaterBottleFull`, never `WaterBottleEmpty`. They are guesses, not game
data (`docs/reference/research-notes.md`: matching against `data/food-items.json` would replace them).
"""
import json
import math
import os
import re
import shutil
import tempfile
from collections import deque

from agent.base.transport.files import FileTransport

FOOD_RX = re.compile(r"\.(?:(?:Canned|Tinned)\w*|Macandcheese|PowerBar|Apple|Bread|Milk|Water|Pop|Chips|Cereal|"
                     r"Cabbage|Carrots|Tomato|Egg|Steak|Chicken|Ham|Tuna|Peanut|Candy|Chocolate|Juice|Soda|Beer|Wine|"
                     r"Whiskey|Orange|Banana|Lettuce|Potato)\b")
WATER_RX = re.compile(r"\.(?:WaterBottle(?:Full)?|Pop|Juice|Milk|Soda|Bowl|Pot|Kettle|Bucket)\b")

ZOMBIE_TTL_S = 10
GROUPS = ("me", "stats", "body", "load", "weapon", "action", "act", "cost")
DEQUE_N = 500


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
        self.frame_wall_ms = None
        self.zombies = {}            # id -> {x, y, dist, hasTarget, crawler, health, seenWallMs}
        self.map = {}                # (x, y, z) -> the square dict
        self.containers = {}         # (x, y, z, i) -> {type, n, items, looted}
        self.buildings = set()
        self.inventory = {}          # itemId -> {fullType, weight}
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
        self.map_lines = 0
        self.replay_bad = 0          # replay(): the transport's dropped lines; 0 for a live World
        self.replay_gaps = []        # replay(): the transport's seq gaps; [] for a live World
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
        if s.get("building") is not None:
            self.buildings.add(s["building"])
        cs = s.get("containers") or []
        for i, c in enumerate(cs):
            old = self.containers.get((x, y, z, i))
            looted = bool(old and old["looted"] and old["type"] == c.get("type"))
            self.containers[(x, y, z, i)] = {"type": c.get("type"), "n": c.get("n") or 0,
                                             "items": list(c.get("items") or ()), "looted": looted}
        for k in [k for k in self.containers if k[:3] == (x, y, z) and k[3] >= len(cs)]:
            del self.containers[k]

    def _event(self, line):
        self.events.append(line)
        kind = line.get("event")
        if kind == "item_added":
            self.inventory[line.get("itemId")] = {"fullType": line.get("fullType"), "weight": line.get("weight")}
        elif kind == "item_removed":
            if self.inventory.pop(line.get("itemId"), None) is None:
                self.missing_items += 1
        elif kind == "damage":
            self.damage.append({"tag": line.get("tag"), "amount": line.get("amount"), "side": line.get("side"),
                                "wallMs": line.get("wallMs")})
        elif kind == "zombie_dead":
            self.zombies.pop(line.get("id"), None)

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
    def mark_looted(self, key):
        if key in self.containers:
            self.containers[key]["looted"] = True

    def _me_xy(self):
        me = self.me or {}
        return me.get("x") or 0.0, me.get("y") or 0.0

    def nearest_unlooted(self, want=None):
        rx = {"food": FOOD_RX, "water": WATER_RX}.get(want)
        mx, my = self._me_xy()
        best = None
        for key, c in self.containers.items():
            if c["looted"] or not c["n"] or not c["items"] or (rx and not any(rx.search(i) for i in c["items"])):
                continue
            rank = (math.hypot(key[0] - mx, key[1] - my), key)
            if best is None or rank < best:
                best = rank
        return best[1] if best else None

    def unexplored_edge(self):
        mx, my = self._me_xy()
        best = None
        for (x, y, z), s in self.map.items():
            if s.get("solid"):
                continue
            if all((x + dx, y + dy, z) in self.map for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue
            rank = (math.hypot(x - mx, y - my), x, y)
            if best is None or rank < best:
                best = rank
        return (best[1], best[2]) if best else None

    def nearest_zombie(self, exclude=()):
        """(id, zombie) of the least `dist`, ties by id; a zombie without a dist or whose id is in `exclude` is never
        nearest; None if none."""
        best = None
        for zid, z in self.zombies.items():
            if zid in exclude:
                continue
            d = z.get("dist")
            if d is None:
                continue
            rank = (d, str(zid))
            if best is None or rank < best[0]:
                best = (rank, zid)
        return (best[1], self.zombies[best[1]]) if best else None

    # -- serialisation --------------------------------------------------------------------------------------------
    def to_json(self):
        """Byte-stable: sorted keys, indent 1, tuple keys as "x,y,z", sets sorted, deques as lists."""
        d = {g: getattr(self, g) for g in GROUPS}
        d.update({
            "gameMin": self.game_min,
            "frameWallMs": self.frame_wall_ms,
            "zombies": {str(k): v for k, v in self.zombies.items()},
            "map": {_key(k): v for k, v in self.map.items()},
            "containers": {_key(k): v for k, v in self.containers.items()},
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
        return json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False)


def replay(path):
    """A World from a state.log read through FileTransport, so delta frames merge as they do live; the transport's
    `bad` and `gaps` are kept as `replay_bad` and `replay_gaps`. A file named
    `state.log` is read from its own directory (its rotations and chunks with it); any other name is copied alone
    into a temporary directory as `state.log`."""
    w = World()
    if os.path.basename(path) == "state.log":
        tr = FileTransport(os.path.dirname(os.path.abspath(path)))
        lines = tr.lines()
    else:
        with tempfile.TemporaryDirectory() as d:
            shutil.copyfile(path, os.path.join(d, "state.log"))
            tr = FileTransport(d)
            lines = tr.lines()
    for line in lines:
        w.apply(line)
    w.replay_bad = tr.bad
    w.replay_gaps = list(tr.gaps)
    return w
