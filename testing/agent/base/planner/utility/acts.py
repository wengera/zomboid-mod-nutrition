"""The candidate acts (Plan 31 Task 11 U; the proposal's § 2 "Candidates"): six to ten per tick, generated from the
frame's `Situation`, the World's map and the planner's `Context` (what the goal runner, the needs, the door read and
the edge marks say this tick). Each `Candidate` names its kind, its target and the geometry its score reads; a vetoed
candidate (`veto`) is kept on the line with its reason and never chosen (the two vetoes are feasibility, outside the
utility: an unreachable target, and a leg bandage while moving).

- `fight:<id>` for the FIGHT_N nearest standing zombies within ENGAGE_R and every fallen one within FINISH_R, and the
  held fight's own target to DISENGAGE_R (so a fight taken at ENGAGE_R's edge does not vanish a tile later). Vetoed
  `unreachable` when the planner's marks skip it (`Context.unreachable`: `Survive.unreachable` and the edge marks,
  this package's own `out of reach` marks), when its straight line crosses a known blocked edge with no door passing
  it (`edges.edge_read` with no `via`, ruling P25-X's refusal), or when it stands behind a portal the door read decided
  to `leave` (P30-C: its marks are in `unreachable`). A zombie behind a closed door the door read opens
  (`Context.door_open`) is a fight through the opened door (`execute.py` runs P30-C's post, open and meet).
- `dress:<part>` for the bleeding part bleeding longest, its item read now (`care.dress_pick`, an unwashed rag taken);
  vetoed `nothing` with nothing held and nothing to tear (the want `bandage` is then marked for the goal's loot) and
  `cooled` within `care.DRESS_RETRY_S` of a Dress that failed with no item gained since. It rides (`ride`, a bandage
  with `keepMoving` over the held walk) when the held act moves (travel, sneak, loot, retreat), the part is above the
  legs and a dressing is held [#4337]; a leg part under a moving act is the standing dress, the ride vetoed `leg`.
- `retreat:door:<x>,<y>` for each filter (`filters`): a known building's exterior door within RETREAT_R whose post
  (`policies.stand_post`, the room square one on from the threshold) the player can reach with no standing zombie in
  the corridor (`policies.in_corridor`) nor nearer the door than the player, and none inside the building; inside the
  building, its own doors' posts with no standing zombie in its rooms. None while the player stands on a filter it
  retreated to (`Context.at_filter`): the retreat ends in the stance there, never another leg. Windows and fences are
  not generated (README: the climb is a harness round trip this cut does not plan).
- `travel` (or `loot`, by the running goal's type) while the goal runner has a goal running or a source pending;
  `sneak` beside it while a standing zombie is within SNEAK_R and every zombie there reads unaware (the sneak posture
  `sneak.SneakGait` sends at the tick's send).
- `needs:<branch>` while no standing zombie is within DANGER_R and one of the ladder's need, load, night, care or
  stock steps would answer (`Context.needs`).
- `rest` with no zombie listed and the endurance moodle at level 1 or more [#3926].
- A group arriving (`Context.group`, read by `GroupClock` over `arriving`: GROUP_N or more aware standing zombies
  listed that can reach the character, their fight not vetoed, one of them within DANGER_R inside the last
  STAND_RECEDE_S; fix 1, review-t11-utility M1, the refuge ruling: no open-ground leg; fix 2, review-t11-utility-fix1
  M2: an unreachable or receding group arrives at nothing): no travel, loot, sneak or needs candidate (the walk away
  from an arriving group is the open leg, whatever the goal); in their place `stand:<id>`, the stand where the
  character is at the nearest arriving zombie (the ruling's string: the arrivals fought one at a time, `back` when a
  wall or fence lies within BACK_R behind the character, away from them), generated while none is within KEEP_R (one
  within reach is the fight's: the controller's ruling on M3). The retreat to a filter stays a candidate.
- The dress is vetoed `in_reach` while an aware standing zombie is within KEEP_R (fix 1, M2: a zombie in reach is
  fought, never dressed in front of), and so is every fight at a standing zombie beyond KEEP_R while an aware one
  within it can be fought (fix 2, review-t11-utility-fix1 M1, the controller's ruling: the fight at the zombie in
  reach wins whatever is listed, a farther fight included; a fallen one's finish is left to the scores, which charge it
  the unfaced zombie's hits, `select.UNFACED_FACTOR`).
"""
import dataclasses
import math

from agent.base.planner import care as C
from agent.base.planner import night as N
from agent.base.planner.edges import edge_read
from agent.base.planner.policies import (DANGER_R, DISENGAGE_R, ENGAGE_R, FINISH_R, KEEP_R, LISTED_R, SNEAK_R,
                                         centre, in_building, in_corridor, stand_post)
from agent.base.planner.utility import models as M

FIGHT_N = 3               # the nearest standing zombies a fight is generated for (the proposal's "the three nearest")
RETREAT_R = 15.0          # tiles: the farthest filter a retreat is generated to (a first guess for the trials, inside
                          # the ladder's SHELTER_FLEE_R 25: a run of 15 tiles is about 4 s)
FILTERS_N = 3             # the nearest filters a retreat is generated to (a first guess: one per side at most)
AT_FILTER_R = 1.0         # tiles: the player this near a filter's target stands on it (the Lua walk's DONE_R,
                          # `policies.WALK_DONE_R`)
MOVING_KINDS = ("travel", "sneak", "loot", "retreat")   # the acts a riding bandage rides
KINDS = ("fight", "stand", "dress", "retreat", "travel", "loot", "sneak", "needs", "rest")
GROUP_N = 3               # aware standing zombies listed that make a group arriving (the doctrine's "three or more
                          # aware zombies", the common amendments' item 5)
BACK_R = 2.0              # tiles: a wall or fence this near behind the character covers the stand's back (the fix
                          # brief's "within two tiles")
STAND_RECEDE_S = 5.0      # seconds with no arriving zombie within DANGER_R after which a group no longer arrives: the
                          # stand ends and the walks return (fix 2, M2; a first guess for the trials: ten planner
                          # ticks, a receding zombie at 2.7 tiles a second, F6 478-481's, gains 13 tiles)


@dataclasses.dataclass(frozen=True)
class Filter:
    kind: str          # "door"
    square: tuple      # the door square (x, y, z)
    target: tuple      # the post's centre (x, y): the walk's end, the stance's square
    building: object
    d: float           # tiles from the player to the target

    @property
    def key(self):
        return "retreat:%s:%d,%d" % (self.kind, self.square[0], self.square[1])


@dataclasses.dataclass(frozen=True)
class Candidate:
    kind: str
    key: str
    target: object = None      # the zombie id, the part index, the filter's door square [x, y], the goal's square
    zed: object = None         # features.Zed of a fight
    part: object = None        # features.Part of a dress
    item: object = None        # the dress's pick (`care.dress_pick`)
    ride: bool = False
    filter: object = None      # Filter of a retreat
    door: bool = False         # a fight through a door the door read opens
    back: bool = False         # a stand with a wall or fence within BACK_R behind
    veto: object = None
    note: object = None        # a vetoed alternative's reason kept on the line (the ride's `leg`)


@dataclasses.dataclass(frozen=True)
class Context:
    goal: object = None             # "travel" or "loot" while the goal runner holds a goal or a pending source
    goal_target: object = None      # the goal's target (x, y) when it reads one
    needs: object = None            # the branch name of the need step that would answer, else None
    door_open: object = None        # the zombie id the door read opens a door on (P30-C), else None
    unreachable: frozenset = frozenset()
    dress_cooled: bool = False
    held_kind: object = None        # the held act's kind
    held_target: object = None      # the held fight's zombie id
    at_filter: object = None        # the Filter the player stands on after its retreat
    group: bool = False             # a group arriving (`GroupClock`)


def arriving(sit, ctx, world):
    """The aware standing zombies listed that come: within DANGER_R, or beyond it closing (a receding one comes to
    nothing: F6 478-481's, at -2.7 tiles a second), and able to reach the character, their fight not vetoed
    (`_fight_veto`: no planner mark, no known blocked edge with no door); nearest first."""
    return [z for z in sit.aware_standing(LISTED_R) if (z.d <= DANGER_R or z.closing > 0.0)
            and _fight_veto(sit, ctx, world, z) is None]


class GroupClock:
    """When an arriving zombie last stood within DANGER_R (`near`), the recede test of the group (the module
    docstring): a group arrives while GROUP_N or more arrive (`arriving`) and one stood within DANGER_R inside the
    last STAND_RECEDE_S."""

    def __init__(self):
        self.near = None

    def read(self, zs, now):
        if any(z.d <= DANGER_R for z in zs):
            self.near = now
        return len(zs) >= GROUP_N and self.near is not None and now - self.near < STAND_RECEDE_S


def generate(sit, ctx, world):
    """The tick's candidates, in KINDS order then by distance (the module docstring)."""
    out = _fights(sit, ctx, world)
    group = ctx.group
    if group:
        st = _stand(sit, ctx, world)
        if st is not None:
            out.append(st)
    d = _dress(sit, ctx, world)
    if d is not None:
        out.append(d)
    if ctx.at_filter is None:
        out.extend(Candidate("retreat", f.key, target=[f.square[0], f.square[1]], filter=f)
                   for f in filters(world, sit))
    if ctx.goal is not None and not group:
        out.append(Candidate(ctx.goal, ctx.goal, target=_xy(ctx.goal_target)))
        near = [z for z in sit.zeds if z.d <= SNEAK_R]
        if any(z.standing for z in near) and not any(z.aware for z in near):
            out.append(Candidate("sneak", "sneak", target=_xy(ctx.goal_target)))
    if ctx.needs is not None and not group and not sit.standing(DANGER_R):
        out.append(Candidate("needs", "needs:%s" % ctx.needs, target=ctx.needs))
    if not [z for z in sit.zeds if z.d <= LISTED_R] and M.endurance_level(sit.endurance) >= 1:
        out.append(Candidate("rest", "rest"))
    return out


def _xy(t):
    return None if t is None else [t[0], t[1]]


def _fights(sit, ctx, world):
    standing = [z for z in sit.zeds if z.standing and z.d <= ENGAGE_R][:FIGHT_N]
    held = sit.zed(ctx.held_target) if ctx.held_target is not None else None
    if held is not None and held.standing and held.d <= DISENGAGE_R and held not in standing:
        standing.append(held)   # the held fight's target keeps its candidate to DISENGAGE_R (the ladder's hold radius)
    fallen = [z for z in sit.zeds if z.fallen and z.d <= FINISH_R]
    out = []
    for z in sorted(standing + fallen, key=lambda q: (q.d, repr(q.id))):
        out.append(Candidate("fight", "fight:%s" % z.id, target=z.id, zed=z, door=z.id == ctx.door_open,
                             veto=_fight_veto(sit, ctx, world, z)))
    if any(c.veto is None and c.zed.standing and c.zed.aware and c.zed.d <= KEEP_R for c in out):
        out = [dataclasses.replace(c, veto="in_reach") if c.veto is None and c.zed.standing and c.zed.d > KEEP_R
               else c for c in out]   # fix 2: the zombie in reach first, never a farther standing one
    return out


def _fight_veto(sit, ctx, world, z):
    if z.id in ctx.unreachable:
        return "unreachable"
    if z.id == ctx.door_open:
        return None
    read = edge_read(world, (sit.x, sit.y), (z.x, z.y), DISENGAGE_R, marked=world.marked_doors())
    if read is not None and read["via"] is None:
        return "blocked_edge"
    return None


def _stand(sit, ctx, world):
    """The stand at the nearest arriving zombie (`arriving`: never one the planner marks unreachable nor one across a
    blocked edge), while no aware zombie is within KEEP_R (the module docstring), else None."""
    aware = arriving(sit, ctx, world)
    if not aware or sit.aware_standing(KEEP_R):
        return None
    z = aware[0]
    away = _away(sit, aware)
    back = away is not None and world.line_clear(
        (sit.x, sit.y), (sit.x + BACK_R * away[0], sit.y + BACK_R * away[1]), unknown_open=True, trans=True) is False
    return Candidate("stand", "stand:%s" % z.id, target=z.id, zed=z, back=back)


def _away(sit, zs):
    """The unit vector away from the zombies `zs`, each weighted by 1 / its distance (`policies.away_vector`'s rule,
    read off the situation), else None."""
    vx = vy = 0.0
    for q in zs:
        dx, dy = sit.x - q.x, sit.y - q.y
        d2 = dx * dx + dy * dy
        if d2 > 0.0:
            vx, vy = vx + dx / d2, vy + dy / d2
    n = math.hypot(vx, vy)
    return None if n == 0.0 else (vx / n, vy / n)


def _dress(sit, ctx, world):
    if not sit.bleeding:
        return None
    p = sit.bleeding[0]
    item = C.dress_pick(world, p.bleeding_time, dirty_ok=True)
    key = "dress:%d" % p.i
    if item is None:
        return Candidate("dress", key, target=p.i, part=p, veto="nothing")
    if sit.aware_standing(KEEP_R):
        return Candidate("dress", key, target=p.i, part=p, item=item, veto="in_reach")
    if ctx.dress_cooled:
        return Candidate("dress", key, target=p.i, part=p, item=item, veto="cooled")
    moving = ctx.held_kind in MOVING_KINDS and sit.moving
    if moving and p.leg:
        return Candidate("dress", key, target=p.i, part=p, item=item, note="leg")
    return Candidate("dress", key, target=p.i, part=p, item=item, ride=moving and item[0] == "bandage")


def filters(world, sit):
    """The retreat's filters (the module docstring), nearest first, at most FILTERS_N."""
    me = (sit.x, sit.y)
    out = []
    for b in world.building_boxes():
        bd = world.building_dist(sit.x, sit.y, b)
        if bd is None or bd > RETREAT_R:
            continue
        inside = sit.on_room and sit.building == b
        standing = [z for z in sit.zeds if z.standing]
        zs = [{"x": z.x, "y": z.y} for z in standing]
        if any(in_building(world, q, b) for q in zs):
            continue
        for door in N.exterior_doors(world, b, sit.z, marked=inside):
            way = world.door_way(door)
            post = None if way is None else stand_post(world, way, b)
            if post is None:
                continue
            target = centre(post)
            d = math.hypot(target[0] - me[0], target[1] - me[1])
            if d > RETREAT_R or d <= AT_FILTER_R:
                continue
            if not inside:
                outer = centre(way[1])
                if any(math.hypot(z.x - outer[0], z.y - outer[1]) < math.hypot(outer[0] - me[0], outer[1] - me[1])
                       or in_corridor(me, target, {"x": z.x, "y": z.y}) for z in standing if z.aware):
                    continue
            out.append(Filter("door", door, target, b, d))
    out.sort(key=lambda f: (f.d, f.square))
    return out[:FILTERS_N]


def filter_at(sit, f):
    """The player stands on filter `f`'s target (within AT_FILTER_R)."""
    return f is not None and math.hypot(f.target[0] - sit.x, f.target[1] - sit.y) <= AT_FILTER_R
