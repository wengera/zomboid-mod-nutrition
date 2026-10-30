"""The goal layer's view (Plan 23 Task 13, spec § 8, P23-10): what a goal source reads, game state only (principle 8).

`view(world, survive) -> dict`, built by `Survive`'s goal branch on a tick that proposes (`survive` supplies the
planner's memory: `need_marks`, `night`, `goals`, `clock`; a missing one reads empty). Its keys, in `KEYS` order:
- `pos {x, y, z}` (the frame's `me`), `hour`, `health` (`body.health`), `kills` (`World.kills`: the zombies the
  fights killed this session, ruling P24-Q, Plan 24 Task 12: the iteration's metric, told to the model), `needs {hunger, thirst, fatigue}` (`stats`),
  `load {weight, max, level}`, `weapon` (the wielded type, else None), `inventory_by_use` ({use: count} over
  `items.USES`, by `world.by_use()`).
- `night` and `tired` (Plan 24 Task 29: the strategy lines' reads, `goal_prompt.py`): `night` the frame's `me.hour` at
  `night.LATE_HOUR` or later or under `night.DAWN_HOUR` (the hours `Night.late` reads), `tired` the frame's
  `stats.fatigue` above `night.TIRED_T` (the first TIRED moodle, the line `Night.wants` reads); each None when its
  field reads no number.
- `worn` (PZA/1.6, Plan 24 Task 24): the defence worn per body location, `[[loc, bite, scratch, holes], ...]` by
  location (`World.worn`, the last `me.worn` a frame carried; bite and scratch to 0.1; `holes` 0 where the build does
  not carry it), None until one frame has carried it (unknown, never "nothing worn"): the model picks what to look for
  (a jacket over a bare torso) from it, and `inventory_by_use` counts the clothing held.
- `needs_wanted`: the uses (water, then food, then container, then water_source, then bandage: NEED_USES) the need
  branch marked (`bandage` the care branch's, ruling P24-AB: a bleeding part with nothing to dress it)
  (nothing of the use held; `container` when no water and no vessel at all is held, the water chain's third step,
  Plan 24 Task 10, ruling P24-G 3; `water_source` when a vessel is held and no clean water source is known, ruling
  P24-L: a building's sink is the goal layer's to find) within the last NEED_MEMORY_S (120) seconds on Survive's clock
  (`survive.need_marks`).
- `buildings`: each known building with an integer id (`world.interiors()`), nearest first then by id: `id`, `x`, `y`
  (its nearest room square on the player's floor, else on any floor: P24-B 3, the model's positions), `door` (its
  first exterior door square on the player's floor, `night.exterior_doors`'s ranking, as [x, y], else None), `dist`
  (tiles from the player to that square's centre, to 0.1), `containers` (the containers on its squares), `looted`
  (a bool, P24-B 3: a container known on it and none a loot could take anything more from, `goals.open_uses` empty
  for each, so a container holding only `other` items or waiting on the cap counts looted; a building with no
  container known reads false, unsearched ground being lootable: Task 3 fix 1, M1),
  `doors` (its exterior doors on the player's floor), `visited` (in `night.visited`), `shunned` (by the night or a
  Shelter goal, within `night.SHUN_MIN`), `shelter` (`night.shelter_plan` answers for it: rooms and an exterior door
  on the player's floor; the scripted Shelter requires it, fix 1 I3), and (ruling P24-Y, Plan 24 Task 18) `holds`
  ({use: items} over its containers of each use of `policies.LOOT_WANTS` a loot has not yet taken there: what it is
  known to hold) and `box` (`World.building_boxes`' [minx, miny, maxx, maxy], the woods test's, unrendered);
  `blocked` (ruling P24-Z: every exterior door on the player's floor marked stuck, `night.door_blocked`; `door` is
  then None, the marked doors left out of `doors` too); `zombies_near` (Task 29: the zombies the World holds within
  BUILDING_ZOMBIE_R (12, the view's middle band) of the building's `box`, else of its nearest listed square: the
  zombies listed beside it, which the strategy lines read).
- `zombies_near {"6", "12", "25"}`: the zombies the World holds (seen within its ZOMBIE_TTL_S) within 6, 12 and 25
  tiles, each count cumulative.
- `met {dense, n, bearing, dist}` (P24-B 1): the World's met ground, `world.met_near()` (the densest MET_R window
  centred within MET_VIEW_R 25 tiles): `dense` its centroid [x, y] to 0.1, `n` the met zombies in it, `bearing` its
  eighth of the compass from the player (`world.compass`, N is -y), `dist` tiles to 0.1; `{null, 0, null, null}` with
  no window. `attackers` (`me.attackers`) and `hit_reaction` (`me.hitReaction`, an empty string read None): PZA/1.4's
  reads, None on a frame that does not carry them.
- `last_goal {type, args, end, why}` (P24-B 3): the runner's last record row, `end` its state (done, failed or
  superseded), `why` its meaning, one of the closed set WHYS (`why_of`): `done` (it ended done); `stuck` (failed for
  a `policies.STUCK_REASONS` reason: stuck, no path, no square); `superseded by the threat` (superseded by an
  `attack`, `steer`, `walkTo` or `stop`, the threat branch's sends, or by `hold`, a branch holding without sending:
  a night's shelter walk reads the same); `superseded by an instinct` (superseded by any other send: a need's
  consume, the load's drop); `looted already` (a LootBuilding failed `nothing to loot`); `refused` and `out of range`
  (the LLM source's refusal of its own last answer, laid over the view it sends: `llm.py`); `failed` (any other
  failure: the goal budget, the load, no plan, a shun, none found). None before any goal ended. `events`: the kinds of
  the last three event lines. `want_shelter`: `night.want_shelter` (the night wants and knows no shelter).
- Beyond the brief's keys, the scripted source's reads: `woods_r` (the goal kit's woods radius, `goals.Kit.woods_r`:
  WOODS_R, widened after REST_N rests in a row, Task 18 fix 1's ruling 3; WOODS_R with no kit), `edge`
  (`world.unexplored_edge(woods_r)` as [x, y], else None: with a building known never a square in the woods, none
  within `woods_r`, ruling P24-Y; after two unmoved
  stuck walks from the player's square only a square in the open, P23-AP 1), `toward` (P24-Y: `{for, building,
  door, square, dist}` of the building a walk heads to when none is to be looted near: `for` "unlooted", the nearest
  building with a container known and not looted beyond `goals.BUILDING_R` when none such is within it, else
  "cluster", the nearest known building when the player stands beyond `woods_r` of every one; `door` its first exterior
  door [x, y] else None, `square` its nearest room square; else None),
  `scanned_here` (the player's place, `policies.place_of`, is in the goal kit's `Explore.scanned`), `stock_uses` (the
  uses of `goals.wanted_uses` for which the kit's `LootHouse.target` answers a container now: `container`, a known
  empty vessel, the water chain's want, among them since P24-Y made it a loot's want, while fewer than
  `goals.CONTAINERS_HELD_N` vessels are held, Task 18 fix 1's major 5), `cooled` (the goals
  the runner refuses for now, `GoalRunner.cooling()`: `[{type, args}]`, fix 1 I4).

The view only reads: the kit is bound by its runner's `observe`, never here (fix 1 M5).

`render(view) -> str`: one `key: value` line per key in `KEYS` order (a key of OPTIONAL_KEYS only when the view
carries it: Task 29), values as compact sorted JSON except
`buildings`, capped at the BUILDINGS_SHOWN (6, P24-B 3) nearest, each `id @x,y door x,y dist cN flags h:holds z:N`
(`door -` with none; flags `L` looted, `v` visited, `s` shunned, `x` blocked (P24-Z), `-` none; `holds` its `use count` pairs, sorted, as
`food3,water1`, `-` with none: P24-Y; ` z:N` its `zombies_near`, only when the building carries it: Task 29),
joined by "; "; the whole stays under RENDER_MAX
(2048) bytes, asserted at return. On overflow the lowest-value line goes first: `events` (the last event kinds, which
no rule reads) is emptied to `[]`; then the buildings are cut from the farthest; then the longest line is halved (its
tail replaced by "...") until it fits, so a long string off the game (an event kind, a goal's reason) cannot pass the
bound (a test asserts every key present and nothing cut on a full fixture: 20 buildings, 50 containers, 30 zombies, a
met window, a goal ended, the needs and a cooled goal; and the bound on a view of oversized strings). The places a
model may name are the shown buildings (`shown_ids`) and an ExploreToward within `llm.EXPLORE_MAX_TILES` of `pos`.
"""
import json
import math
import time

from agent.base.items import USES
from agent.base.items import holds_use
from agent.base.planner.goals import BUILDING_R, WOODS_R, int_id, open_uses, wanted_uses, window_pick
from agent.base.planner.night import DAWN_HOUR, LATE_HOUR, TIRED_T, door_blocked, exterior_doors, shelter_plan
from agent.base.planner.policies import LOOT_WANTS, STUCK_REASONS, me_floor, me_xy, place_of
from agent.base.world import MET_VIEW_R, compass

NEED_MEMORY_S = 120.0
NEED_USES = ("water", "food", "container", "water_source", "bandage")   # the need marks the view lists, in order
                                                                         # (P24-G 3, P24-L; the care's, P24-AB)
ZOMBIE_BANDS = (6, 12, 25)
BUILDING_ZOMBIE_R = 12.0   # tiles from a building's box within which a held zombie is listed beside it (Task 29: the
                           # view's middle band, ZOMBIE_BANDS[1], a judgment: the strategy's avoid and load lines)
BUILDINGS_SHOWN = 6
RENDER_MAX = 2048
EVENTS_N = 3
KEYS = ("pos", "hour", "night", "health", "kills", "needs", "tired", "needs_wanted", "load", "weapon", "inventory_by_use",
        "worn",
        "buildings",
        "zombies_near", "met", "attackers", "hit_reaction", "last_goal", "events", "want_shelter", "woods_r", "edge",
        "toward", "scanned_here", "stock_uses", "cooled")
WHYS = ("done", "stuck", "superseded by the threat", "superseded by an instinct", "looted already", "refused",
        "out of range", "in the woods", "failed")
THREAT_SENDS = ("attack", "steer", "walkTo", "stop", "hold")   # a superseding send read as the threat's (why_of)
OPTIONAL_KEYS = ("night", "tired")   # rendered only when the view carries them (Task 29)

__all__ = ["view", "render", "why_of", "shown_ids", "KEYS", "OPTIONAL_KEYS", "WHYS", "NEED_MEMORY_S",
           "ZOMBIE_BANDS", "BUILDING_ZOMBIE_R", "BUILDINGS_SHOWN", "RENDER_MAX", "MET_VIEW_R"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _box_dist(box, x, y):
    """Tiles from the point (x, y) to the box [minx, miny, maxx, maxy] of whole squares (0 inside it)."""
    return math.hypot(max(box[0] - x, 0.0, x - (box[2] + 1)), max(box[1] - y, 0.0, y - (box[3] + 1)))


def _buildings(world, night, kit, zxy=()):
    z = me_floor(world)
    mx, my = me_xy(world)
    loot = kit.loot if kit is not None else None
    waiting = {u: (loot.waiting(u) if loot is not None else set()) for u in LOOT_WANTS}
    keys = {}
    for k in world.containers:
        keys.setdefault((world.map.get(k[:3]) or {}).get("building"), []).append(k)
    shunned = set(night.shunned_now()) if night is not None else set()
    if kit is not None:
        shunned |= kit.shunned_now(world)
    visited = night.visited if night is not None else set()
    boxes = world.building_boxes()
    out = []
    for b, rooms in world.interiors().items():
        if not int_id(b):
            continue
        near = [sq for sq in rooms if sq[2] == z] or rooms
        dist, sq = min((math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my), sq) for sq in near)
        box = boxes[b] if b in boxes else (sq[0], sq[1], sq[0], sq[1])
        cs = keys.get(b, [])
        doors = exterior_doors(world, b, z)
        out.append({"id": b, "x": sq[0], "y": sq[1], "door": [doors[0][0], doors[0][1]] if doors else None,
                    "dist": round(dist, 1), "containers": len(cs),
                    "looted": bool(cs) and not any(open_uses(world, loot, k, waiting) for k in cs),
                    "doors": len(doors), "visited": b in visited, "shunned": b in shunned,
                    "shelter": shelter_plan(world, b) is not None, "holds": _holds(world, cs),
                    "blocked": door_blocked(world, b, z) and window_pick(world, b, shunned) is None,
                    "box": list(boxes[b]) if b in boxes else None,
                    "zombies_near": sum(1 for x, y in zxy if _box_dist(box, x, y) <= BUILDING_ZOMBIE_R)})
    return sorted(out, key=lambda r: (r["dist"], r["id"]))


def _worn(world):
    """`[[loc, bite, scratch, holes], ...]` over `World.worn` by location, else None while no frame has carried it."""
    if world.worn is None:
        return None
    return [[e.get("loc"), round(e.get("bite") or 0.0, 1), round(e.get("scratch") or 0.0, 1), e.get("holes") or 0]
            for e in sorted((e for e in world.worn if isinstance(e, dict)), key=lambda e: str(e.get("loc")))]


def _holds(world, keys):
    """{use: items} over the containers `keys`: each item of a LOOT_WANTS use a loot has not taken there yet (P24-Y:
    what the building is known to hold)."""
    out = {}
    for k in keys:
        c = world.containers.get(k) or {}
        for item in c.get("items") or ():
            for u in LOOT_WANTS:
                if (u != "clothing" or world.can("wear")) and u not in c.get("looted", ()) and holds_use(item, u):
                    out[u] = out.get(u, 0) + 1
    return dict(sorted(out.items()))


def _toward(world, buildings, woods_r=WOODS_R):
    """P24-Y's walk toward a building (the module docstring's `toward`), else None."""
    near = [b for b in buildings if b["looted"] is False and b["containers"] > 0 and not b["shunned"]
            and not b["blocked"]]
    target, why = None, None
    if near and not any(b["dist"] <= BUILDING_R for b in near):
        target, why = near[0], "unlooted"
    elif buildings and not world.building_near(*me_xy(world), woods_r):
        target, why = min(buildings, key=lambda b: (world.building_dist(*me_xy(world), b["id"]), b["id"])), "cluster"
    if target is None:
        return None
    return {"for": why, "building": target["id"], "door": target["door"], "square": [target["x"], target["y"]],
            "dist": target["dist"]}


def _met(world):
    m = world.met_near()
    if m is None:
        return {"dense": None, "n": 0, "bearing": None, "dist": None}
    mx, my = me_xy(world)
    return {"dense": [round(m[0], 1), round(m[1], 1)], "n": m[2], "bearing": compass(m[0] - mx, m[1] - my),
            "dist": round(math.hypot(m[0] - mx, m[1] - my), 1)}


def why_of(row):
    """The meaning of a record row's end, one of WHYS (the module docstring)."""
    state, reason = row.get("state"), row.get("reason")
    if state == "done":
        return "done"
    if state == "superseded":
        return "superseded by the threat" if reason in THREAT_SENDS else "superseded by an instinct"
    if reason in STUCK_REASONS:
        return "stuck"
    if reason == "nothing to loot":
        return "looted already"
    return "failed"


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
    zxy = [(z["x"], z["y"]) for z in world.zombies.values() if z.get("x") is not None and z.get("y") is not None]
    zs = [math.hypot(x - mx, y - my) for x, y in zxy]
    woods_r = kit.woods_r if kit is not None else WOODS_R
    edge = world.unexplored_edge(woods_r)
    last = runner.history[-1] if runner is not None and runner.history else None
    buildings = _buildings(world, night, kit, zxy)
    hour, fatigue = me.get("hour"), st.get("fatigue")
    return {
        "pos": {"x": me.get("x"), "y": me.get("y"), "z": me.get("z")},
        "hour": hour,
        "night": (hour >= LATE_HOUR or hour < DAWN_HOUR) if _num(hour) else None,   # the hours Night.late reads
        "health": (world.body or {}).get("health"),
        "kills": world.kills,
        "needs": {k: st.get(k) for k in ("hunger", "thirst", "fatigue")},
        "tired": fatigue > TIRED_T if _num(fatigue) else None,                    # the line Night.wants reads
        "needs_wanted": [u for u in NEED_USES if u in marks and now - marks[u] <= NEED_MEMORY_S],
        "load": {k: load.get(k) for k in ("weight", "max", "level")},
        "weapon": (world.weapon or {}).get("type"),
        "inventory_by_use": {u: len(by_use[u]) for u in USES},
        "worn": _worn(world),
        "buildings": buildings,
        "zombies_near": {str(r): sum(1 for d in zs if d <= r) for r in ZOMBIE_BANDS},
        "met": _met(world),
        "attackers": me.get("attackers"),
        "hit_reaction": me.get("hitReaction") or None,
        "last_goal": ({"type": last["type"], "args": last["args"], "end": last["state"], "why": why_of(last)}
                      if last is not None else None),
        "events": [e.get("event") for e in list(world.events)[-EVENTS_N:]],
        "want_shelter": bool(getattr(night, "want_shelter", False)),
        "woods_r": woods_r,
        "edge": list(edge) if edge else None,
        "toward": _toward(world, buildings, woods_r),
        "scanned_here": kit is not None and place_of(world) in kit.explore.scanned,
        "stock_uses": [u for u in wanted_uses(world, kit.wants if kit is not None else ())
                       if kit is not None and kit.loot.target(u) is not None],
        "cooled": runner.cooling() if runner is not None else [],
    }


def shown_ids(v):
    """The ids of the buildings `render` shows at most (the BUILDINGS_SHOWN nearest): the buildings a model may
    name."""
    return [b.get("id") for b in (v.get("buildings") or [])[:BUILDINGS_SHOWN] if isinstance(b, dict)]


def _building(b):
    mark = "L" if b.get("looted") else ""
    mark += "v" if b.get("visited") else ""
    mark += "s" if b.get("shunned") else ""
    mark += "x" if b.get("blocked") else ""
    door = b.get("door")
    door = "%s,%s" % (door[0], door[1]) if door else "-"
    holds = ",".join("%s%s" % (u, n) for u, n in sorted((b.get("holds") or {}).items())) or "-"
    zs = " z:%s" % b["zombies_near"] if "zombies_near" in b else ""
    return "%s @%s,%s door %s %s c%s %s h:%s%s" % (b.get("id"), b.get("x"), b.get("y"), door, b.get("dist"),
                                                   b.get("containers"), mark or "-", holds, zs)


def _lines(v, shown, events=True):
    lines = []
    for k in KEYS:
        if k in OPTIONAL_KEYS and k not in v:
            continue
        if k == "buildings":
            text = "; ".join(_building(b) for b in (v.get(k) or [])[:shown])
        else:
            text = json.dumps(v.get(k) if events or k != "events" else [], sort_keys=True, separators=(",", ":"))
        lines.append("%s: %s" % (k, text))
    return lines


def _size(lines):
    return len("\n".join(lines).encode("utf-8"))


def render(v):
    """The view as text (the module docstring), under RENDER_MAX bytes, asserted."""
    shown = BUILDINGS_SHOWN
    lines = _lines(v, shown)
    if _size(lines) >= RENDER_MAX:
        lines = _lines(v, shown, events=False)
    while _size(lines) >= RENDER_MAX and shown > 0:
        shown -= 1
        lines = _lines(v, shown, events=False)
    while _size(lines) >= RENDER_MAX:
        i = max(range(len(lines)), key=lambda j: len(lines[j].encode("utf-8")))
        keep = max(len(lines[i]) // 2, len(lines[i].split(": ", 1)[0]) + 2)
        lines[i] = lines[i][:keep] + "..."
    text = "\n".join(lines)
    assert len(text.encode("utf-8")) < RENDER_MAX
    return text
