"""The agent's model of the world, a pure function of the link lines it is given.

No clock is read: zombies age by the frame's own `wallMs`, so `replay(path)` over a log is
deterministic and `to_json()` is byte-stable (sorted keys, tuple keys rendered "x,y,z").

HEURISTIC: FOOD_RX and WATER_RX guess from an item's fullType whether a container holds food or
drink. They are guesses, not game data; the spike grades on outcomes, not on the heuristic.
"""
import json
import math
import re
from collections import deque

FOOD_RX = re.compile(r"\.(Apple|Bread|Milk|Water|Pop|Chips|Cereal|Cabbage|Carrots|Tomato|Egg|Steak|Chicken|Ham|Canned|Tuna|Peanut|Candy|Chocolate|Juice|Soda|Beer|Wine|Whiskey|Orange|Banana|Lettuce|Potato)")
WATER_RX = re.compile(r"\.(WaterBottle|Pop|Juice|Milk|Soda|Bowl|Pot|Kettle|Bucket)")

_ME_DROP = ("kind", "seq", "tick", "zombies", "goal")


def _key(k):
    return ",".join(str(p) for p in k)


def _seq(v):
    """A Lua empty table arrives as {}; a table of rows may arrive as a list or a dict."""
    if isinstance(v, dict):
        return list(v.values())
    return list(v or ())


class World:
    ZOMBIE_TTL_S = 10.0

    def __init__(self):
        self.me = {}
        self.zombies = {}
        self.map = {}
        self.containers = {}
        self.buildings = set()
        self.server = {}
        self.events = deque(maxlen=200)
        self.goal = None
        self.missing = []
        self.hello = None
        self.last_ack = None

    def apply(self, line):
        fn = getattr(self, "_" + str(line.get("kind")), None)
        if fn:
            fn(line)

    def _hello(self, line):
        self.hello = {k: v for k, v in line.items() if k not in ("kind", "seq", "tick")}

    def _frame(self, line):
        wall = line.get("wallMs", 0)
        self.me = {k: v for k, v in line.items() if k not in _ME_DROP}
        for z in _seq(line.get("zombies")):
            self.zombies[z.get("id")] = {"x": z.get("x"), "y": z.get("y"), "dist": z.get("dist"),
                                         "hasTarget": z.get("hasTarget", False),
                                         "crawler": z.get("crawler", False), "seenWallMs": wall}
        ttl = self.ZOMBIE_TTL_S * 1000
        for zid in [i for i, z in self.zombies.items() if wall - z["seenWallMs"] > ttl]:
            del self.zombies[zid]
        if line.get("goal"):
            self.goal = line["goal"]

    def _event(self, line):
        self.events.append({k: v for k, v in line.items() if k not in ("kind", "seq", "tick")})
        if line.get("event") == "zombie_leave":
            self.zombies.pop(line.get("id"), None)

    def _scan(self, line):
        for s in _seq(line.get("squares")):
            if not (isinstance(s, dict) and "x" in s and "y" in s):
                continue
            x, y, z = s["x"], s["y"], s.get("z", 0)
            self.map[(x, y, z)] = s
            if s.get("building") is not None:
                self.buildings.add(s["building"])
            for i, c in enumerate(_seq(s.get("containers"))):
                old = self.containers.get((x, y, z, i))
                looted = bool(old and old["looted"] and old["type"] == c.get("type"))
                self.containers[(x, y, z, i)] = {"type": c.get("type"), "n": c.get("n", 0),
                                                 "items": _seq(c.get("items")), "looted": looted}
        self.missing = _seq(line.get("missing"))

    def _ack(self, line):
        self.last_ack = {k: line.get(k) for k in ("cmdSeq", "ok", "reason")}

    def merge_server(self, stats, wall_ms):
        self.server = {"stats": stats, "wallMs": wall_ms}

    def mark_looted(self, key):
        if key in self.containers:
            self.containers[key]["looted"] = True

    def _me_xy(self):
        return self.me.get("x", 0.0), self.me.get("y", 0.0)

    def nearest_unlooted(self, want=None):
        rx = {"food": FOOD_RX, "water": WATER_RX}.get(want)
        mx, my = self._me_xy()
        best = None
        for key, c in self.containers.items():
            if c["looted"] or (rx and not any(rx.search(i) for i in c["items"])):
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

    def to_json(self):
        return json.loads(json.dumps({
            "me": self.me,
            "zombies": {str(k): v for k, v in self.zombies.items()},
            "map": {_key(k): v for k, v in self.map.items()},
            "containers": {_key(k): v for k, v in self.containers.items()},
            "buildings": sorted(self.buildings),
            "server": self.server,
            "events": list(self.events),
            "goal": self.goal,
            "missing": self.missing,
            "hello": self.hello,
            "last_ack": self.last_ack,
        }, sort_keys=True))


def replay(path):
    w = World()
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                w.apply(json.loads(ln))
    return w
