"""The agent's model of the world, a pure function of the link lines it is given.

No clock is read: zombies age by the frame's own `wallMs`, so `replay(path)` over a log is
deterministic and `to_json()` is byte-stable (sorted keys, tuple keys rendered "x,y,z").

A scan arrives either whole (a `scan` line, Stage A passes 1-2) or in parts (`scanPart` lines, Stage A pass 3: one per
tick, each carrying its scanId, part and parts). Parts are held by scanId and applied exactly as a `scan` line once every
part 1..parts is held, so map, containers and buildings change once, at completion, never from a half scan. A part of a
new scanId drops every other held, incomplete scan (the Lua replaces a running scan, and its parts stop): each counts in
`dropped_scans`.

HEURISTIC: FOOD_RX and WATER_RX guess from an item's fullType whether a container holds food or
drink; a trailing word boundary keeps Base.Hammer from matching Ham. They are guesses, not game data; the spike grades on outcomes, not on the heuristic.
"""
import json
import math
import re
from collections import deque

FOOD_RX = re.compile(r"\.(Apple|Bread|Milk|Water|Pop|Chips|Cereal|Cabbage|Carrots|Tomato|Egg|Steak|Chicken|Ham|Canned|Tuna|Peanut|Candy|Chocolate|Juice|Soda|Beer|Wine|Whiskey|Orange|Banana|Lettuce|Potato)\b")
WATER_RX = re.compile(r"\.(WaterBottle|Pop|Juice|Milk|Soda|Bowl|Pot|Kettle|Bucket)\b")

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
        self.unknown_kinds = 0
        self.dropped_scans = 0
        self._parts = {}          # scanId -> {part number: line}, the scans still arriving
        self._handlers = {"hello": self._hello, "frame": self._frame, "event": self._event,
                          "scan": self._scan, "scanPart": self._scan_part, "ack": self._ack}

    def apply(self, line):
        fn = self._handlers.get(line.get("kind"))
        if fn:
            fn(line)
        else:
            self.unknown_kinds += 1

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
        if line.get("event") in ("goal_done", "goal_failed") and self.goal and self.goal.get("seq") == line.get("goalSeq"):
            self.goal = dict(self.goal, state=line["event"][5:], detail=line.get("reason", self.goal.get("detail", "")))
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

    def _scan_part(self, line):
        sid = line.get("scanId")
        for old in [k for k in self._parts if k != sid]:
            del self._parts[old]
            self.dropped_scans += 1
        held = self._parts.setdefault(sid, {})
        held[line.get("part")] = line
        n = line.get("parts")
        if not isinstance(n, int) or any(i not in held for i in range(1, n + 1)):
            return
        del self._parts[sid]
        parts = [held[i] for i in range(1, n + 1)]
        missing = []
        for pl in parts:
            for m in _seq(pl.get("missing")):
                if m not in missing:
                    missing.append(m)
        whole = dict(parts[-1], kind="scan", squares=[q for pl in parts for q in _seq(pl.get("squares"))],
                     missing=missing)
        self._scan(whole)

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
