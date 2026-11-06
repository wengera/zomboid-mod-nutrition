"""The tactical view (Plan 31 Task 11, variant T; the proposal § 3): what the tactician reads, game state only, every
target a label (`Z<n>`, `D<n>`, `B<id>`, `P<i>`) so a validation is a set lookup (`plays.validate`).

`build(world, triggers=None, ctx=None) -> dict`, its keys in KEYS order:
- `trigger`: the trigger the view answers (`ctx["trigger"]`), else None.
- `me`: x, y (to 0.01), health (to 0.1), `inside` (a room square), `building` (its label, else None), `armed` (the
  wielded type, else None), `cond` (the weapon's condition), `endurance` (stats, to 0.01), `armPain` (body, to 0.1:
  over 10 divides every swing but the stomp, #4370), `hit` (`me.hitReaction`, None when empty), `attackers`.
- `zombies`: up to ZOMBIES_N (8) records, nearest first, `{label, id, bearing, dist, closing, posture, targets_me,
  known, state, behind, line, health}`: `bearing` the compass eighth from the player (`world.compass`, N is -y),
  `dist` tiles to 0.1, `closing` tiles a second to 0.1 (`Triggers.closing`, None unread), `posture` standing | floor |
  crawler (`crawler`, else `onFloor`), `targets_me` its `hasTarget` (the one player is the target), `known`, `state`,
  `behind` the frame's PZA/1.9 fields, `line` clear | door | wall | window | unknown (`line_of`), `health` to 0.01.
- `counts`: `standing_6` (standing within DANGER_R), `standing_keep` (within KEEP_R 2.5), `aware_12` (standing and
  targeting the player within LISTED_R 12), `listed_12`.
- `map`: MAP_N (21) rows of MAP_N characters around `@`, north up (`render_map`).
- `body`: health, `parts` (each part reading bleeding, bandaged, deep or wound: `{label, name, bleeding, bandaged,
  dirty, deep, wound, h}`), `armPain`.
- `kit`: weapon, cond, `bandages`, `rags`, `dirty_rags` (`care.held_dressings`), `rip` (1 when a held unworn cotton
  garment can be ripped, `care.rip_pick`), `unwear` (1 when a worn cotton garment can be taken off for it,
  `care.unwear_pick`), `water`, `food` (`World.by_use`), `load` (the frame's level).
- `doors`: up to DOORS_N (6) exterior doors of the known buildings within DOOR_VIEW_R (25), nearest first: `{label,
  building, dist, bearing, open, locked, zombies_near}` (`zombies_near`: listed within DOOR_NEAR_R 3 of it).
- `buildings`: up to BUILDINGS_N (6) known buildings, nearest first: `{label, dist, bearing, looted, shelter,
  zombies_near, here}` (`looted` `goals.looted`; `shelter` a `night.shelter_plan` answers; `zombies_near` listed within
  `view.BUILDING_ZOMBIE_R` 12 of its box; `here` the player stands in it).
- `needs`: thirst, hunger, fatigue (to 0.01), `night` (the hour at `night.LATE_HOUR` or later or under DAWN_HOUR).
- `play` (`ctx["play"]`: the running play's `{play, target, age_s, tally}`), `last_plays` (`ctx["last_plays"]`: up to
  three `{play, end, bound_broken}`), `goal` (`ctx["goal"]`: `{type, building}` of the strategic goal), `refusal`
  (`ctx["refusal"]`: the last answer's refusal why, once).

`render(view) -> str`: one `key: <compact sorted JSON>` line per key, the map as its own lines; under RENDER_MAX
bytes. The view only reads."""
import json
import math

from agent.base.planner import care as C
from agent.base.planner.goals import int_id, looted
from agent.base.planner.night import DAWN_HOUR, LATE_HOUR, exterior_doors, shelter_plan
from agent.base.planner.policies import DANGER_R, KEEP_R, LISTED_R, line_to, on_floor, zdist
from agent.base.planner.view import BUILDING_ZOMBIE_R
from agent.base.world import compass, me_floor, me_xy

KEYS = ("trigger", "me", "zombies", "counts", "map", "body", "kit", "doors", "buildings", "needs", "play",
        "last_plays", "goal", "refusal")
ZOMBIES_N = 8          # the proposal's "up to 8 records"
DOORS_N = 6            # doors listed (a first guess for the trials; the goal view's BUILDINGS_SHOWN)
BUILDINGS_N = 6        # buildings listed (the goal view's BUILDINGS_SHOWN, P24-B 3)
DOOR_VIEW_R = 25.0     # tiles: a door this near is listed (the goal view's widest zombie band, view.ZOMBIE_BANDS)
DOOR_NEAR_R = 3.0      # tiles: a zombie this near a door is counted at it (a first guess for the trials)
MAP_N = 21             # the proposal's 21 x 21 map
RENDER_MAX = 6144      # bytes: the rendered view's bound (the proposal: about 1.5 KB over today's 7.5 KB prompt)
PART_NAMES = ("Hand_L", "Hand_R", "ForeArm_L", "ForeArm_R", "UpperArm_L", "UpperArm_R", "Torso_Upper",
              "Torso_Lower", "Head", "Neck", "Groin", "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R",
              "Foot_L", "Foot_R")   # BodyPartType's order: the frame's part index `i` (care.LEG_FIRST 11 the first leg)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _r(v, n):
    return round(v, n) if _num(v) else None


def _sq(world):
    x, y = me_xy(world)
    return int(math.floor(x)), int(math.floor(y)), me_floor(world)


def posture(z):
    """standing | floor | crawler."""
    if z.get("crawler") is True:
        return "crawler"
    return "floor" if on_floor(z) else "standing"


def line_of(world, z):
    """clear | door | wall | window | unknown: the line from the player to zombie `z` (`policies.line_to`), a blocked
    one named by what its squares carry (a closed door's record first, then a window's), else a wall."""
    clear = line_to(world, z)
    if clear is None:
        return "unknown"
    if clear:
        return "clear"
    mx, my = me_xy(world)
    fl = me_floor(world)
    cells = world._bresenham(int(math.floor(mx)), int(math.floor(my)), int(math.floor(z["x"])),
                             int(math.floor(z["y"])))
    recs = [world.map.get((x, y, fl)) or {} for x, y in cells]
    if any(isinstance(s.get("door"), dict) and not s["door"].get("open") for s in recs):
        return "door"
    if any(s.get("window") is not None for s in recs):
        return "window"
    return "wall"


def zombie_rows(world, triggers=None):
    """The listed zombies with a position, nearest first (ties by id), as (zid, z, tiles)."""
    rows = [(zid, z, zdist(world, z)) for zid, z in world.zombies.items()
            if z.get("x") is not None and z.get("y") is not None and int_id(zid)]
    return sorted(rows, key=lambda r: (r[2], r[0]))


def _zombies(world, triggers):
    mx, my = me_xy(world)
    out = []
    for k, (zid, z, d) in enumerate(zombie_rows(world)[:ZOMBIES_N], 1):
        closing = triggers.closing(zid) if triggers is not None else None
        out.append({"label": "Z%d" % k, "id": zid, "bearing": compass(z["x"] - mx, z["y"] - my), "dist": round(d, 1),
                    "closing": _r(closing, 1), "posture": posture(z), "targets_me": z.get("hasTarget") is True,
                    "known": z.get("known"), "state": z.get("state"), "behind": z.get("behind"),
                    "line": line_of(world, z), "health": _r(z.get("health"), 2)})
    return out


def _counts(world):
    rows = zombie_rows(world)
    stand = [(z, d) for _, z, d in rows if not on_floor(z)]
    return {"standing_6": sum(1 for _, d in stand if d <= DANGER_R),
            "standing_keep": sum(1 for _, d in stand if d <= KEEP_R),
            "aware_12": sum(1 for z, d in stand if d <= LISTED_R and z.get("hasTarget") is True),
            "listed_12": sum(1 for _, _, d in rows if d <= LISTED_R)}


def _char(s):
    if s is None:
        return " "
    if isinstance(s.get("door"), dict):
        return "/" if s["door"].get("open") else "+"
    if s.get("window") is not None:
        return "="
    if s.get("solid"):
        return "#"
    if s.get("hopN") is True or s.get("hopW") is True:
        return "^"
    return "." if s.get("room") is not None else ","


def render_map(world, zombies=()):
    """MAP_N strings, north up, the player's square `@` at the centre, each square's character (`_char`: unknown ` `,
    a door `+` closed or `/` open, a window `=`, solid `#`, a hoppable fence `^`, a room square `.`, else `,`), the
    listed zombies' label digits (Z1-Z9) over their squares."""
    px, py, fl = _sq(world)
    h = MAP_N // 2
    grid = [[_char(world.map.get((px + dx, py + dy, fl))) for dx in range(-h, h + 1)] for dy in range(-h, h + 1)]
    for z in reversed(list(zombies)):
        rec = world.zombies.get(z["id"]) or {}
        if rec.get("x") is None:
            continue
        gx, gy = int(math.floor(rec["x"])) - px + h, int(math.floor(rec["y"])) - py + h
        n = int(z["label"][1:])
        if 0 <= gx < MAP_N and 0 <= gy < MAP_N and n <= 9:
            grid[gy][gx] = str(n)
    grid[h][h] = "@"
    return ["".join(row) for row in grid]


def _parts(world):
    parts = (world.body or {}).get("parts")
    out = []
    for p in parts if isinstance(parts, list) else ():
        if not isinstance(p, dict) or not int_id(p.get("i")):
            continue
        if not any(p.get(k) is True for k in ("bleeding", "bandaged", "deep", "wound")):
            continue
        i = p["i"]
        out.append({"label": "P%d" % i, "name": PART_NAMES[i] if 0 <= i < len(PART_NAMES) else None,
                    "bleeding": p.get("bleeding") is True, "bandaged": p.get("bandaged") is True,
                    "dirty": p.get("bandageDirty") is True, "deep": p.get("deep") is True,
                    "wound": p.get("wound") is True, "h": _r(p.get("h"), 1)})
    return out


def _kit(world):
    d = C.held_dressings(world)
    uses = world.by_use()
    w = world.weapon or {}
    return {"weapon": w.get("type"), "cond": _r(w.get("cond"), 2), "bandages": len(d["bandage"]),
            "rags": len(d["rag"]), "dirty_rags": len(d["dirty"]), "rip": int(C.rip_pick(world) is not None),
            "unwear": int(bool(world.item_fields()) and C.unwear_pick(world) is not None),
            "water": len(uses.get("water", ())), "food": len(uses.get("food", ())),
            "load": (world.load or {}).get("level")}


def _bearing(world, x, y):
    mx, my = me_xy(world)
    return compass(x - mx, y - my)


def building_rows(world):
    """(tiles, building, its nearest room square) of each known building with an integer id, nearest first (by its box,
    `World.building_dist`; ties by id)."""
    mx, my = me_xy(world)
    fl = me_floor(world)
    out = []
    for b, rooms in world.interiors().items():
        if not int_id(b):
            continue
        near = [sq for sq in rooms if sq[2] == fl] or rooms
        sq = min(near, key=lambda q: (math.hypot(q[0] + 0.5 - mx, q[1] + 0.5 - my), q))
        d = world.building_dist(mx, my, b)
        out.append((d if d is not None else math.inf, b, sq))
    return sorted(out, key=lambda r: (r[0], r[1]))


def _buildings(world, here):
    zs = [(z["x"], z["y"]) for _, z, d in zombie_rows(world)]
    boxes = world.building_boxes()
    out = []
    for d, b, sq in building_rows(world)[:BUILDINGS_N]:
        box = boxes.get(b)
        near = sum(1 for x, y in zs if box is not None and _box_dist(box, x, y) <= BUILDING_ZOMBIE_R)
        out.append({"label": "B%d" % b, "dist": round(d, 1), "bearing": _bearing(world, sq[0] + 0.5, sq[1] + 0.5),
                    "looted": looted(world, b), "shelter": shelter_plan(world, b) is not None, "zombies_near": near,
                    "here": b == here})
    return out


def _box_dist(box, x, y):
    dx = max(box[0] - x, 0.0, x - (box[2] + 1))
    dy = max(box[1] - y, 0.0, y - (box[3] + 1))
    return math.hypot(dx, dy)


def door_rows(world):
    """(tiles, door square, building) of the known buildings' exterior doors on the player's floor within DOOR_VIEW_R,
    nearest first (ties by the square)."""
    mx, my = me_xy(world)
    fl = me_floor(world)
    out = []
    for b in world.building_boxes():
        if not int_id(b):
            continue
        for sq in exterior_doors(world, b, fl, marked=True):
            d = math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my)
            if d <= DOOR_VIEW_R:
                out.append((d, sq, b))
    return sorted(out, key=lambda r: (r[0], r[1]))


def _doors(world):
    zs = [(z["x"], z["y"]) for _, z, d in zombie_rows(world)]
    out = []
    for k, (d, sq, b) in enumerate(door_rows(world)[:DOORS_N], 1):
        rec = (world.map.get(sq) or {}).get("door") or {}
        out.append({"label": "D%d" % k, "building": "B%d" % b, "dist": round(d, 1),
                    "bearing": _bearing(world, sq[0] + 0.5, sq[1] + 0.5), "open": bool(rec.get("open")),
                    "locked": bool(rec.get("locked")),
                    "zombies_near": sum(1 for x, y in zs if math.hypot(x - sq[0] - 0.5, y - sq[1] - 0.5)
                                        <= DOOR_NEAR_R)})
    return out


def here_building(world):
    """The building id of the room square the player stands on, else None."""
    return (world.map.get(_sq(world)) or {}).get("building") if (world.map.get(_sq(world)) or {}).get(
        "room") is not None else None


def build(world, triggers=None, ctx=None):
    """The tactical view (the module docstring)."""
    ctx = ctx or {}
    me, st, body = world.me or {}, world.stats or {}, world.body or {}
    here = here_building(world)
    hour = me.get("hour")
    zombies = _zombies(world, triggers)
    v = {"trigger": ctx.get("trigger"),
         "me": {"x": _r(me.get("x"), 2), "y": _r(me.get("y"), 2), "health": _r(body.get("health"), 1),
                "inside": (world.map.get(_sq(world)) or {}).get("room") is not None,
                "building": "B%d" % here if int_id(here) else None, "armed": (world.weapon or {}).get("type"),
                "cond": _r((world.weapon or {}).get("cond"), 2), "endurance": _r(st.get("endurance"), 2),
                "armPain": _r(body.get("armPain"), 1), "hit": me.get("hitReaction") or None,
                "attackers": me.get("attackers")},
         "zombies": zombies,
         "counts": _counts(world),
         "map": render_map(world, zombies),
         "body": {"health": _r(body.get("health"), 1), "parts": _parts(world), "armPain": _r(body.get("armPain"), 1)},
         "kit": _kit(world),
         "doors": _doors(world),
         "buildings": _buildings(world, here),
         "needs": {"thirst": _r(st.get("thirst"), 2), "hunger": _r(st.get("hunger"), 2),
                   "fatigue": _r(st.get("fatigue"), 2),
                   "night": _num(hour) and (hour >= LATE_HOUR or hour < DAWN_HOUR)},
         "play": ctx.get("play"),
         "last_plays": list(ctx.get("last_plays") or ())[-3:],
         "goal": ctx.get("goal"),
         "refusal": ctx.get("refusal")}
    return {k: v[k] for k in KEYS}


def render(view):
    """The view as the model's user message (the module docstring)."""
    lines = []
    for k in KEYS:
        if k == "map":
            lines.append("map:")
            lines.extend(view.get("map") or ())
            continue
        lines.append("%s: %s" % (k, json.dumps(view.get(k), sort_keys=True, separators=(",", ":"))))
    text = "\n".join(lines)
    if len(text.encode("utf-8")) > RENDER_MAX:
        text = text.encode("utf-8")[:RENDER_MAX].decode("utf-8", "ignore")
    return text
