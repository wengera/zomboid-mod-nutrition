"""The goal layer's view (Plan 23 Task 13, spec § 8, P23-10): what a goal source reads, game state only (principle 8).

`view(world, survive) -> dict`, built by `Survive`'s goal branch on a tick that proposes (`survive` supplies the
planner's memory: `need_marks`, `night`, `goals`, `clock`; a missing one reads empty). Its keys, in `KEYS` order:
- `pos {x, y, z}` (the frame's `me`), `hour`, `health` (`body.health`), `needs {hunger, thirst, fatigue}` (`stats`),
  `load {weight, max, level}`, `weapon` (the wielded type, else None), `inventory_by_use` ({use: count} over
  `items.USES`, by `world.by_use()`).
- `needs_wanted`: the uses (water, then food) the need branch marked (nothing of the use held) within the last
  NEED_MEMORY_S (120) seconds on Survive's clock (`survive.need_marks`).
- `buildings`: each known building with an integer id (`world.interiors()`), nearest first then by id: `id`, `dist`
  (tiles from the player to the centre of its nearest room square on the player's floor, else on any floor, to 0.1),
  `containers` (the containers on its squares), `looted` (those a loot could take nothing more from:
  `goals.open_uses` empty, so a container holding only `other` items, or waiting on the cap, counts looted), `doors`
  (its exterior doors on the player's floor, `night.exterior_doors`), `visited` (in `night.visited`), `shunned` (by
  the night or a Shelter goal, within `night.SHUN_MIN`), `shelter` (`night.shelter_plan` answers for it: rooms and
  an exterior door on the player's floor; the scripted Shelter requires it, fix 1 I3).
- `zombies_near {"6", "12", "25"}`: the zombies the World holds (seen within its ZOMBIE_TTL_S) within 6, 12 and 25
  tiles, each count cumulative.
- `last_goal {type, args, state, reason}`: the runner's last record row, else None. `events`: the kinds of the last
  three event lines. `want_shelter`: `night.want_shelter` (the night wants and knows no shelter).
- Beyond the brief's keys, the scripted source's reads: `edge` (`world.unexplored_edge()` as [x, y], else None),
  `scanned_here` (the player's place, `policies.place_of`, is in the goal kit's `Explore.scanned`), `stock_uses` (the
  uses of `goals.STOCK_WANTS` for which the kit's `LootHouse.target` answers a container now), `cooled` (the goals
  the runner refuses for now, `GoalRunner.cooling()`: `[{type, args}]`, fix 1 I4).

The view only reads: the kit is bound by its runner's `observe`, never here (fix 1 M5).

`render(view) -> str`: one `key: value` line per key in `KEYS` order, values as compact sorted JSON except
`buildings`, capped at the BUILDINGS_SHOWN (10) nearest, each `id dist c/l/d v` (`v` visited, `s` shunned, `-`
neither), joined by "; "; the whole stays under RENDER_MAX (2048) bytes, asserted at return: the buildings are cut
from the farthest until it fits, then the longest line is halved (its tail replaced by "...") until it does, so a
long string off the game (an event kind, a goal's reason) cannot pass the bound (a test asserts the bound on a World
of 20 buildings and 50 containers, and on a view of oversized strings).
"""
import json
import math
import time

from agent.base.items import USES
from agent.base.planner.goals import STOCK_WANTS, int_id, open_uses
from agent.base.planner.night import exterior_doors, shelter_plan
from agent.base.planner.policies import LOOT_WANTS, me_floor, me_xy, place_of

NEED_MEMORY_S = 120.0
ZOMBIE_BANDS = (6, 12, 25)
BUILDINGS_SHOWN = 10
RENDER_MAX = 2048
EVENTS_N = 3
KEYS = ("pos", "hour", "health", "needs", "needs_wanted", "load", "weapon", "inventory_by_use", "buildings",
        "zombies_near", "last_goal", "events", "want_shelter", "edge", "scanned_here", "stock_uses", "cooled")

__all__ = ["view", "render", "KEYS", "NEED_MEMORY_S", "ZOMBIE_BANDS", "BUILDINGS_SHOWN", "RENDER_MAX"]


def _buildings(world, night, kit):
    z = me_floor(world)
    mx, my = me_xy(world)
    loot = kit.loot if kit is not None else None
    waiting = {u: (loot.waiting(u) if loot is not None else set()) for u in LOOT_WANTS}
    keys = {}
    for k in world.containers:
        keys.setdefault((world.map.get(k[:3]) or {}).get("building"), []).append(k)
    shunned = set(night.shunned_now()) if night is not None else set()
    if kit is not None:
        shunned |= kit.shunned_now(world.game_min)
    visited = night.visited if night is not None else set()
    out = []
    for b, rooms in world.interiors().items():
        if not int_id(b):
            continue
        near = [sq for sq in rooms if sq[2] == z] or rooms
        dist = min(math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my) for sq in near)
        cs = keys.get(b, [])
        out.append({"id": b, "dist": round(dist, 1), "containers": len(cs),
                    "looted": sum(1 for k in cs if not open_uses(world, loot, k, waiting)),
                    "doors": len(exterior_doors(world, b, z)), "visited": b in visited, "shunned": b in shunned,
                    "shelter": shelter_plan(world, b) is not None})
    return sorted(out, key=lambda r: (r["dist"], r["id"]))


def view(world, survive):
    """The goal source's view (the module docstring)."""
    night = getattr(survive, "night", None)
    runner = getattr(survive, "goals", None)
    kit = runner.kit if runner is not None else None
    clock = getattr(survive, "clock", time.time)
    me, st, load = world.me or {}, world.stats or {}, world.load or {}
    now = clock()
    marks = getattr(survive, "need_marks", None) or {}
    by_use = world.by_use()
    mx, my = me_xy(world)
    zs = [math.hypot(z["x"] - mx, z["y"] - my) for z in world.zombies.values()
          if z.get("x") is not None and z.get("y") is not None]
    edge = world.unexplored_edge()
    last = runner.history[-1] if runner is not None and runner.history else None
    return {
        "pos": {"x": me.get("x"), "y": me.get("y"), "z": me.get("z")},
        "hour": me.get("hour"),
        "health": (world.body or {}).get("health"),
        "needs": {k: st.get(k) for k in ("hunger", "thirst", "fatigue")},
        "needs_wanted": [u for u in ("water", "food") if u in marks and now - marks[u] <= NEED_MEMORY_S],
        "load": {k: load.get(k) for k in ("weight", "max", "level")},
        "weapon": (world.weapon or {}).get("type"),
        "inventory_by_use": {u: len(by_use[u]) for u in USES},
        "buildings": _buildings(world, night, kit),
        "zombies_near": {str(r): sum(1 for d in zs if d <= r) for r in ZOMBIE_BANDS},
        "last_goal": {k: last[k] for k in ("type", "args", "state", "reason")} if last is not None else None,
        "events": [e.get("event") for e in list(world.events)[-EVENTS_N:]],
        "want_shelter": bool(getattr(night, "want_shelter", False)),
        "edge": list(edge) if edge else None,
        "scanned_here": kit is not None and place_of(world) in kit.explore.scanned,
        "stock_uses": [u for u in STOCK_WANTS if kit is not None and kit.loot.target(u) is not None],
        "cooled": runner.cooling() if runner is not None else [],
    }


def _building(b):
    mark = "v" if b.get("visited") else ""
    mark += "s" if b.get("shunned") else ""
    return "%s %s %s/%s/%s %s" % (b.get("id"), b.get("dist"), b.get("containers"), b.get("looted"), b.get("doors"),
                                  mark or "-")


def _lines(v, shown):
    lines = []
    for k in KEYS:
        if k == "buildings":
            text = "; ".join(_building(b) for b in (v.get(k) or [])[:shown])
        else:
            text = json.dumps(v.get(k), sort_keys=True, separators=(",", ":"))
        lines.append("%s: %s" % (k, text))
    return lines


def _size(lines):
    return len("\n".join(lines).encode("utf-8"))


def render(v):
    """The view as text (the module docstring), under RENDER_MAX bytes, asserted."""
    shown = BUILDINGS_SHOWN
    lines = _lines(v, shown)
    while _size(lines) >= RENDER_MAX and shown > 0:
        shown -= 1
        lines = _lines(v, shown)
    while _size(lines) >= RENDER_MAX:
        i = max(range(len(lines)), key=lambda j: len(lines[j].encode("utf-8")))
        keep = max(len(lines[i]) // 2, len(KEYS[i]) + 2)
        lines[i] = lines[i][:keep] + "..."
    text = "\n".join(lines)
    assert len(text.encode("utf-8")) < RENDER_MAX
    return text
