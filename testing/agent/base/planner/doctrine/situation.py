"""The doctrine's read of the situation (Plan 31 Task 11, the variant D): `read(world, mem, now)`, the wants of the six
priorities top down, each a `Want(p, kind, target, why, ids)`, read over the World and the doctrine's own memory (no
send, no Survive): the arbiter takes the first, and the replay test reads it at the recorded situations. It is pure but
for two writes to the memory: `mem.bandage_want` (this read's: a bleed with nothing to dress it) and a lifted dress
hold cleared (`dress_held`).

The six (the spec's section 3, D; the README's table the record):
- P0 `strike`: the nearest standing zombie within the strike radius (the frame's `weapon.reach` plus STRIKE_MARGIN, the
  bare hands' UNARMED_REACH unarmed), or with `me.attackers` > 0 the nearest standing one; never one behind a door or a
  window (`door_held.portal_between`) nor one whose straight line the map reads blocked (`policies.line_to` False: a
  wall between), since the hit list drops a target across a blocked line or a closed door (#4681). The same two
  exclusions hold for every want below but the door's: a zombie behind a wall is no one's until it comes round. A
  zombie whose melee backed off (`mem.backoff`: an `interrupted`, `timeout`, `no target` or `no weapon` end, or a
  rejection) is struck again only after BACKOFF_TICKS.
- P1 `dress`: the worst bleeding unbandaged part (deep first, then the longest bleeding time), with no standing zombie
  within DRESS_CLEAR_R, something held or worn to dress it with (`care.dress_pick`: a dressing, else a cotton garment to
  rip or take off) and no failed Dress's hold standing (`dress_held`: until a dressing or a garment is added or
  `care.DRESS_RETRY_S` pass); a bleed with nothing to dress it reads `bandage_want` (the goal's loot then takes one).
- P2 `avoid`: GROUP_N or more standing aware zombies (`aware`: `hasTarget` or `known`) within GROUP_R, not strung out
  (the nearest leading the second by STRING_GAP or more is fought instead), or two or more unarmed, with a named
  refuge (`refuge`: a building, its way out, a door, a fence line; never open ground, the controller's ruling on
  review-t11-doctrine M5); none while a failed Avoid's hold stands (`mem.avoid_until`). With no refuge the Avoid is
  not taken: the stand is (P3's, below).
- P3 `fight`: the nearest standing aware zombie within ENGAGE_R that no Fight failed on (`mem.skip`) and none behind a
  portal, when the group rule does not hold (or a failed Avoid's hold stands: the stance against any count); its
  `ids` the one or two the Fight owns (the lead alone when strung out); else a fallen zombie within DOWNED_R with no
  standing one within it (the finish). A group with no refuge is the stand: the lead alone, `why.stand` true, and
  `why.ground` the square with a wall or a fence at its back within GROUND_R (`ground`), else none (the character's
  own square): the arrivals fought one at a time where the character stands.
- P4 `door`: the zombies within DOOR_R whose straight line meets a door or a window first (`portal_between`), grouped
  by that portal, the nearest group's portal decided once (`stance_open` for a door with DOOR_OPEN_MAX or fewer behind,
  armed, on a build announcing `interact` and `aim`; else `leave`), unless the same decision for the same zombies was
  taken within DOOR_DECIDED_S (`mem.doors`).
- P5 `order`: always (the needs, then the goal runner's loot, travel and stock).

Health is read by none of them: a lone zombie in reach is fought whatever the health (memory
`stand-and-fight-dress-first`)."""
import dataclasses
import math

from agent.base.planner import care as C
from agent.base.planner.doctrine import constants as K
from agent.base.planner.door_held import door_post, portal_between
from agent.base.planner.edges import _across, side_of
from agent.base.planner.night import approach_square, exterior_doors
from agent.base.planner.policies import (away_vector, centre, exit_plan, in_building, in_corridor, line_to, on_floor,
                                         on_room, stand_post, target_id_ok, zdist)
from agent.base.world import me_floor, me_xy


@dataclasses.dataclass
class Want:
    """One priority's answer this tick: `p` (P_STRIKE..P_ORDER), `kind` (its intent's name), `target` (a zombie id, a
    part index, the refuge or the door plan, None for the order), `why` (logged) and `ids` (the zombies it concerns)."""
    p: int
    kind: str
    target: object = None
    why: dict = dataclasses.field(default_factory=dict)
    ids: tuple = ()


@dataclasses.dataclass
class Memory:
    """The doctrine's memory across ticks: zombie id -> wall until it is skipped as dead (`dead`) or as a Fight's
    failure (`skip`); portal edge -> (decision, ids, wall) of a door decided (`doors`); the failed Dress's hold
    (inventory ids, wall) or None; the wall until which no Avoid starts (`avoid_until`)."""
    dead: dict = dataclasses.field(default_factory=dict)
    skip: dict = dataclasses.field(default_factory=dict)
    doors: dict = dataclasses.field(default_factory=dict)
    dress_hold: object = None
    avoid_until: float = -math.inf
    backoff: dict = dataclasses.field(default_factory=dict)   # zombie id -> doctrine ticks its melee waits
    bandage_want: bool = False   # this read: a bleeding part with nothing to dress it


def aware(z):
    """The zombie knows of the player: it has a target (`hasTarget`) or reads the player's location known (`known`,
    PZA/1.9)."""
    return z.get("hasTarget") is True or z.get("known") is True


def strike_r(world):
    """The strike radius: the frame's `weapon.reach` plus STRIKE_MARGIN (FALLBACK_REACH when it reads none), the bare
    hands' UNARMED_REACH with no weapon."""
    w = world.weapon
    if w is None:
        return K.UNARMED_REACH
    r = w.get("reach")
    ok = isinstance(r, (int, float)) and not isinstance(r, bool) and r > 0.0
    return (r if ok else K.FALLBACK_REACH) + K.STRIKE_MARGIN


def bleeding_parts(world):
    """The bleeding unbandaged parts, worst first: deep, then the longest bleeding time, then the least index (the care
    branch's order, `care.Care._bleeding`)."""
    ps = [p for p in ((world.body or {}).get("parts") or ()) if isinstance(p, dict) and isinstance(p.get("i"), int)
          and p.get("bleeding") is True and p.get("bandaged") is not True]
    return sorted(ps, key=lambda p: (p.get("deep") is not True, -(p.get("bleedingTime") or 0.0), p["i"]))


def dress_held(world, mem, now):
    """A failed Dress's hold stands (`care.Care._dress_held_off`'s rule): no dressing or garment added to the inventory
    since it failed and `care.DRESS_RETRY_S` not yet passed; a lifted hold is cleared."""
    h = mem.dress_hold
    if h is None:
        return False
    added = set(world.inventory) - h[0]
    if any(C.dress_material(world, iid) for iid in added) or now - h[1] >= C.DRESS_RETRY_S:
        mem.dress_hold = None
        return False
    return True


def listed(world, mem, now):
    """(tiles, id, record) of every listed zombie with a position, not read dead (`mem.dead`), nearest first."""
    out = []
    for zid, z in world.zombies.items():
        if mem.dead.get(zid, -math.inf) > now or z.get("x") is None or z.get("y") is None:
            continue
        out.append((zdist(world, z), zid, z))
    out.sort(key=lambda e: (e[0], repr(e[1])))
    return out


def portals(world, near):
    """{zombie id: (edge, kind)} of the zombies of `near` within DOOR_R whose straight line from the player meets a door
    or a window first (`door_held.portal_between`, the doors P24-Z marked read locked, a locked building door read
    openable from a room square)."""
    me = me_xy(world)
    inside = on_room(world)
    marked = world.marked_doors()
    out = {}
    for d, zid, z in near:
        if d > K.DOOR_R:
            break
        p = portal_between(world, me, (z["x"], z["y"]), marked, inside)
        if p is not None:
            out[zid] = p
    return out


def read(world, mem, now):
    """The wants of the six priorities this tick, top down (the module docstring); the last is always the order. It
    writes `mem.bandage_want` and may clear a lifted dress hold, nothing else."""
    near = listed(world, mem, now)
    behind = portals(world, near)
    free = [e for e in near if e[1] not in behind and line_to(world, e[2]) is not False]
    upright = [e for e in free if not on_floor(e[2])]
    wants = []
    s = _strike(world, mem, upright)
    if s is not None:
        wants.append(s)
    d = _dress(world, mem, now, upright)
    if d is not None:
        wants.append(d)
    group = [e for e in upright if aware(e[2]) and e[0] <= K.GROUP_R]
    strung = len(group) >= K.GROUP_N and group[1][0] - group[0][0] >= K.STRING_GAP
    armed = world.weapon is not None
    is_group = (len(group) >= K.GROUP_N and not strung) or (not armed and len(group) >= 2)
    held = mem.avoid_until > now
    stand = None
    if is_group and not held:
        zs = [z for _, _, z in group]
        ref = refuge(world, zs)
        if ref is not None:
            wants.append(Want(K.P_AVOID, "avoid", ref, {"n": len(group), "nearest": group[0][0]},
                              tuple(e[1] for e in group)))
        else:
            stand = zs   # no named refuge: the stand where the character is (the controller's ruling on M5)
    f = _fight(world, mem, now, free, upright, strung, is_group and not held and stand is None, stand)
    if f is not None:
        wants.append(f)
    door = _door(world, mem, now, near, behind)
    if door is not None:
        wants.append(door)
    wants.append(Want(K.P_ORDER, "order"))
    return wants


def _strike(world, mem, upright):
    r = strike_r(world)
    upright = [e for e in upright if not mem.backoff.get(e[1])]
    attackers = (world.me or {}).get("attackers") or 0
    inside = [e for e in upright if e[0] <= r]
    if not inside and attackers > 0 and upright:
        inside = upright[:1]   # an attack reads on the frame before its zombie's square does
    inside = [e for e in inside if target_id_ok(e[1])]
    if not inside:
        return None
    dist, zid, _ = inside[0]
    return Want(K.P_STRIKE, "strike", zid, {"d": dist, "reach": r, "attackers": attackers}, (zid,))


def _dress(world, mem, now, upright):
    mem.bandage_want = False
    parts = bleeding_parts(world)
    if not parts or any(e[0] <= K.DRESS_CLEAR_R for e in upright):
        return None
    if dress_held(world, mem, now):
        return None
    p = parts[0]
    pick = C.dress_pick(world, p.get("bleedingTime") or 0.0, dirty_ok=True)
    if pick is None:
        mem.bandage_want = True
        return None
    return Want(K.P_DRESS, "dress", p["i"], {"part": p["i"], "bleeding": len(parts), "with": pick[0],
                                             "deep": p.get("deep") is True})


def _fight(world, mem, now, free, upright, strung, is_group, stand=None):
    if is_group:
        return None
    able = [e for e in upright if aware(e[2]) and e[0] <= K.ENGAGE_R and target_id_ok(e[1])
            and mem.skip.get(e[1], -math.inf) <= now]
    if able:
        lead = strung or stand is not None
        ids = (able[0][1],) if lead else tuple(e[1] for e in able[:2])
        why = {"d": able[0][0], "n": len(able), "strung": strung}
        if stand is not None:
            g = ground(world, stand)
            why.update(stand=True, ground=None if g is None else [g[0], g[1], g[2]])
        return Want(K.P_FIGHT, "fight", able[0][1], why, ids)
    if any(e[0] <= K.DOWNED_R for e in upright):
        return None
    downed = [e for e in free if on_floor(e[2]) and e[0] <= K.DOWNED_R and target_id_ok(e[1])
              and mem.skip.get(e[1], -math.inf) <= now]
    if downed:
        return Want(K.P_FIGHT, "fight", downed[0][1], {"d": downed[0][0], "n": 1, "downed": True}, (downed[0][1],))
    return None


def _door(world, mem, now, near, behind):
    if not behind:
        return None
    groups = {}
    for d, zid, z in near:
        if zid in behind:
            groups.setdefault(behind[zid], []).append((d, zid))
    (edge, kind), zs = min(groups.items(), key=lambda kv: (kv[1][0][0], kv[0][0]))
    ids = tuple(sorted((zid for _, zid in zs), key=repr))
    opens = (kind == "door" and len(zs) <= K.DOOR_OPEN_MAX and world.weapon is not None and world.can("interact")
             and world.can("aim") and all(target_id_ok(z) for z in ids))
    decision = "stance_open" if opens else "leave"
    seen = mem.doors.get(edge)
    if seen is not None and seen[0] == decision and seen[1] == ids and now - seen[2] < K.DOOR_DECIDED_S:
        return None
    plan = {"edge": edge, "kind": kind, "decision": decision, "door": edge[0], "zid": zs[0][1]}
    if opens:
        plan["post"], plan["near"] = door_post(world, edge, me_xy(world))
    holder = edge[0]
    return Want(K.P_DOOR, "door", plan, {"door": [holder[0], holder[1]], "kind": kind, "n_behind": len(zs),
                                         "decision": decision}, ids)


# ---------------------------------------------------------------- the refuge
def refuge(world, group, refused=()):
    """The Avoid's refuge from the zombies `group`, chosen once (`{kind, square, label, ...}`), a named structure
    within REFUGE_R or None (the controller's ruling on review-t11-doctrine M5: never open ground; with none the stand
    is taken where the character is):
    - on a room square, with no zombie of the group inside the building: the building itself (`inside`: the stance
      at the player's own square, the filter of its doors); with one inside, its way out (`policies.exit_plan`, the
      windows among them on a build announcing `window`): an opening or a closed exterior door, the square beyond it
      (`exit`), or a window, its inside square then the climb (`window`, its square and `smash`);
    - outdoors, the nearest known exterior door within REFUGE_R that is neither locked nor barricaded, whose outside
      square no zombie of the group is nearer than the player and whose straight line from the player passes none
      (`policies.in_corridor`), no listed zombie inside its building: the square past its post inside
      (`policies.stand_post`, else its room square), `door`;
    - else a fence line (`fence`): a hoppable edge (`hopN`/`hopW`, `World.memo`'d per map version) with every zombie
      of the group on one side of its line (`edges.side_of`), the square across it from them (the climb on the walk's
      stuck end, `night.hop_after`), its centre within REFUGE_R, no zombie of the group nearer it than the player and
      none in its corridor; the nearest first.
    `refused` squares (x, y) are never chosen again (a route that failed). `label` is the scorecard's `avoid_refuge`
    (a refuge word, `tools/trial_score.py` REFUGE_WORDS)."""
    me = me_xy(world)
    if me[0] is None or me[1] is None:
        return None
    floor = me_floor(world)
    if on_room(world):
        b = (world.map.get((int(math.floor(me[0])), int(math.floor(me[1])), floor)) or {}).get("building")
        if not any(in_building(world, z, b) for z in group):
            sq = (int(math.floor(me[0])), int(math.floor(me[1])), floor)
            return {"kind": "inside", "square": sq, "label": "avoid_refuge", "building": b}
        e = exit_plan(world, group, refused={(r[0], r[1], floor) for r in refused}, windows=world.can("window"))
        if e is None or not _ok(e["target"], refused):
            return None
        if e.get("step") == "window":
            return {"kind": "window", "square": e["target"], "label": "avoid_refuge", "building": e["building"],
                    "window": e["window"], "smash": bool(e.get("smash"))}
        return {"kind": "exit", "square": e["target"], "label": "avoid_refuge", "building": e["building"],
                "door": e.get("door")}
    return _door_refuge(world, group, refused, me, floor) or _fence_refuge(world, group, refused, me, floor)


def _ok(sq, refused):
    return sq is not None and (sq[0], sq[1]) not in {(r[0], r[1]) for r in refused}


def _clear_of(group, me, c, mine):
    """No zombie of `group` nearer the point `c` than the player (`mine` tiles) nor in the corridor to it."""
    return not any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < mine or in_corridor(me, c, z) for z in group)


def _door_refuge(world, group, refused, me, floor):
    best = None
    for b in sorted(world.interiors(), key=repr):
        if any(in_building(world, z, b) for z in world.zombies.values()
               if z.get("x") is not None and z.get("y") is not None):
            continue
        for door in exterior_doors(world, b, floor):
            rec = (world.map.get(door) or {}).get("door") or {}
            if rec.get("locked") or rec.get("barricaded"):
                continue
            outer = approach_square(world, door)
            way = world.door_way(door)
            if outer is None or way is None:
                continue
            oc = centre(outer)
            mine = math.hypot(oc[0] - me[0], oc[1] - me[1])
            if mine > K.REFUGE_R or not _clear_of(group, me, oc, mine):
                continue
            target = stand_post(world, way, b) or way[0]
            if not _ok(target, refused):
                continue
            rank = (mine, repr(b), door)
            if best is None or rank < best[0]:
                best = (rank, {"kind": "door", "square": target, "label": "avoid_refuge", "building": b,
                               "door": door})
    return None if best is None else best[1]


def hop_edges(world, floor):
    """The hoppable edges `(holder, side)` the map holds on `floor` (a fence's `hopN`/`hopW`), sorted; read once per
    map version (`World.memo`)."""
    def edges():
        return sorted(((sq, side) for sq, rec in world.map.items() if sq[2] == floor
                       for side in ("N", "W") if rec.get("hop" + side)), key=repr)
    return world.memo(("doctrine_hops", floor), edges)


def _fence_refuge(world, group, refused, me, floor):
    best = None
    for edge in hop_edges(world, floor):
        sq, side = edge
        if abs(sq[0] - me[0]) > K.REFUGE_R + 1 or abs(sq[1] - me[1]) > K.REFUGE_R + 1:
            continue
        sides = {side_of(edge, (z["x"], z["y"])) for z in group}
        if len(sides) != 1:
            continue
        theirs = sides.pop()
        for t in (sq, _across(sq, side)):
            tc = centre(t)
            rec = world.map.get(t)
            if side_of(edge, tc) == theirs or rec is None or rec.get("solid") or rec.get("solidTrans"):
                continue
            mine = math.hypot(tc[0] - me[0], tc[1] - me[1])
            if mine > K.REFUGE_R or not _ok(t, refused) or not _clear_of(group, me, tc, mine):
                continue
            rank = (mine, repr(t))
            if best is None or rank < best[0]:
                best = (rank, {"kind": "fence", "square": t, "label": "avoid_refuge",
                               "fence": [sq[0], sq[1], side]})
    return None if best is None else best[1]


# ---------------------------------------------------------------- the stand
def ground(world, group):
    """The stand's square (the controller's ruling on review-t11-doctrine M5): the nearest known open square within
    GROUND_R of the player, its straight line from the player clear, whose step on away from the group (along the
    larger axis of `policies.away_vector`) the map reads blocked (a wall or a fence at its back, `World.blocked`);
    else None (the character's own square)."""
    me = me_xy(world)
    av = away_vector(world, [(z["x"], z["y"]) for z in group])
    if av is None or me[0] is None:
        return None
    floor = me_floor(world)
    step = (1 if av[0] > 0 else -1, 0) if abs(av[0]) >= abs(av[1]) else (0, 1 if av[1] > 0 else -1)
    px, py = int(math.floor(me[0])), int(math.floor(me[1]))
    reach = int(math.ceil(K.GROUND_R))
    best = None
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            sq = (px + dx, py + dy, floor)
            c = centre(sq)
            d = math.hypot(c[0] - me[0], c[1] - me[1])
            rec = world.map.get(sq)
            back = (sq[0] + step[0], sq[1] + step[1], floor)
            if d > K.GROUND_R or rec is None or rec.get("solid") or rec.get("solidTrans") or back not in world.map:
                continue
            if not world.blocked(sq, back) or (sq[:2] != (px, py) and not world.line_clear(me, c)):
                continue
            rank = (d, sq)
            if best is None or rank < best:
                best = rank
    return None if best is None else best[1]


__all__ = ["Want", "Memory", "aware", "strike_r", "bleeding_parts", "dress_held", "listed", "portals", "read",
           "refuge", "ground", "hop_edges"]
