"""The goal layer (Plan 23 Task 13, spec § 8, P23-10, P23-B): typed goals under the instincts, chosen by a source
behind one seam (`GoalSource.propose(view) -> Goal | None`) that the scripted source and Task 14's LLM source share;
None is *pending* (ruling P23-AC): the source has no answer yet (the LLM's call in flight), and the scripted source
never answers it.

`Survive`'s last branch, `goal`, runs one goal at a time through `GoalRunner`; the instincts above it (threat, need,
load, night) pre-empt it. The goal types are `schema/goals.json`'s five, each a dataclass whose fields are that
entry's properties less `type` (P23-B, asserted by the tests), plus three run fields every goal carries (`RUN_FIELDS`:
`state` "running" | "done" | "failed" | "superseded", `reason`, `started_wall`, keyword-only and defaulted), `TYPE`
a class attribute equal to the entry's `const`:
- `ExploreToward(x, y)`: Explore's logic aimed at a point: a `Scan(SCAN_R)` of the player's place while the place is
  unscanned, then a `WalkTo(x, y)` at a walk; `done "arrived"` when its walk ends done, or when the place is scanned
  and the player stands within ARRIVE_R (1.5 tiles) of (x, y); a walk or scan that ends any other way but
  `superseded` fails the goal under the action's reason (a walk failed for a `STUCK_REASONS` reason is marked stuck by
  `Explore.observe`, so the scripted source's next edge leaves it out). A point farther than the leg length is
  walked to in legs (ruling P24-AC, Plan 24 Task 21, `_Legs`: E8's 278 walks 62 to 234 tiles off all failed `no
  square`; the length is `leg_max`, read off the frame's `me.loadedWidth` since ruling P24-AI, Task 27: 40 tiles at the
  harness's 1280 x 720 window, 64 at 1920 x 1080, LEG_MAX 40 with none read), a leg failed `no square` halved down to LEG_MIN (10) and re-sent, never marking the target; the woods
  radius's widening and the cluster step reach it through ExploreToward, so they walk in legs too. The climb in routes (Plan 24 Task 10, ruling
  P24-G 4; #4296: a short fence climbed at a walk never trips; `_Climbing` and the kit's `hop_after`, shared with
  `Shelter` since Task 10 fix 1, minor 9): a walk the path follower could not finish, ended `failed "stuck"` where the
  straight line from the player toward the walk's target first crosses a hoppable edge (`World.hop_ahead`: blocked,
  its square's `hopN`/`hopW` true, at the player's own square), sends `Climb(x, y)` of that fence's square (the build
  announcing `climb`, `World.can`) and walks again once the climb ends done, the climbed walk target's stuck mark
  dropped (`Kit.climbed`: `Explore.observe` marked it at the stuck end, which would leave the edge out of
  `unexplored_edge` for STUCK_TTL_MIN after a climb that crossed it); a climb that ends any other way (`fell`, a tall
  fence's `failed`) fails the goal under its reason, and a second stuck walk at a fence it already climbed fails it
  `stuck`. A walk whose path crosses a hoppable edge the follower climbs itself needs nothing; nothing here ever runs or
  sprints over a fence (no vault).
- `LootBuilding(building)`: `LootHouse` kept to the containers on the building's squares (`LootHouse.within`), one
  loot at a time for the first of STOCK_WANTS (ruling P24-Y, Plan 24 Task 18: water and container, clothing, food,
  bandage, weapon; `clothing` since Task 24 is a loot's want with the Lua's `clothing` filter (PZA/1.6, a build that
  announces `wear`), a container's garments told by name only, `items.garment`, and the want bounded by
  CLOTHING_HELD_N unworn garments held) that `LootHouse.target` answers there, `container`
  only while fewer than CONTAINERS_HELD_N (2) vessels are held (`wanted_uses`: Task 18 fix 1, the review's major 5,
  E7's map knew 14 empty vessels in building 5 and 8 in building 2, each loot filling to the cap before the food);
  `done "looted"` when none answers after at least one loot, `failed "nothing to loot"` when none answered at all,
  `failed "load"` above `LOOT_MAX_LEVEL` (the level guard, spec § 9 (1)). A container farther than the leg length is walked
  to in legs first (P24-AC, `_Legs`), a leg's failure other than a halved `no square` failing the goal. The route (ruling P24-Z, Plan 24 Task 18;
  E7's eight loots failed `not adjacent` from outside building 5's locked back door, 55.6 s): a loot that failed `not
  adjacent` is a route that stood against a door (Survive counts it on that door, `World.note_door_fail`, the second
  marking it); while the player is not on a room square of the building, the next steps are the shelter machine's
  approach, open and enter by the building's best exterior door the World has not marked (`night.shelter_plan`,
  `night.exterior_doors`), a step's end read by `night.shelter_ended` (its next door on a door's failure), and the loot
  resumes from inside; with no door left, the window route (Task 24, review-t9-fix9's ruling: E7's back door stood
  locked and the building had windows): `window_pick` (a build announcing `window`; the building's exterior windows,
  `World.windows`, on the player's floor, not barricaded and not left out by a failed end; an open one first, then a
  shut unlocked one with `smash` false, then a locked one only when `smash_ok`: no other usable (unshunned, not stuck, not looted out) known building within
  BUILDING_R, no zombie listed within SMASH_ZOMBIE_R and health at or above SMASH_MIN_HEALTH, with `smash` true)
  sends one `Window(x, y, smash)` at a time, the route due at once when every exterior door is already marked from
  outside; a window that ends done leaves the route (the care branch reads the wounds from the frame's body parts,
  the result's `cut` being unreliable in multiplayer, and `cut` and `wounds` are logged), one that fails leaves the
  window out (`World.note_window_fail`; `locked` lets the next try smash it); with no window either,
  `failed "no door"` (the view then reads the building `blocked` once all its doors are marked and no window is to be
  tried, and the source passes it over for the next). Its optional `want` (Plan 24 Task 29, the written guides' weapon
  first and the first bag: `weapon` or `bag`, OPTIONAL_FIELDS; the scripted source never names one, and `args()`
  leaves an unset want out, so its rows read as before): the want's loot use (`WANT_USES`: `weapon` the use
  `items.WEAPON_RX` reads; `bag` none, no loot filter taking a bag) goes first after the kit's wants, and the goal ends
  `done "want met"` once the held items of the want (`held_of`: `world.by_use()`'s for a use, `items.bag`'s name
  guess for a bag) number more than at its start, so a want already held asks for one more; with none to take there
  the loot goes on in the default order.
- `Shelter(building)`: Night's shelter machine for a named building (`night.shelter_plan`, `shelter_step`,
  `shelter_ended`, never re-implemented): approach the exterior door, open it, step in, close it (a step's walk failed
  `stuck` at a hoppable edge climbs it first, as `ExploreToward` does, and walks again; a climb that fails is read as
  that walk's stuck end, the machine's next door or shun); `done "inside"` once the plan reads done, `failed "no
  plan"` with no exterior door or room on the player's floor, `failed "shun"` when the machine shuns the building; both shun the building in the kit's `shunned` for `night.SHUN_MIN` game
  minutes (fix 1, I3) on `World.world_minutes()` (monotonic across midnight: fix wave P, I-1), the store
  `Night.shunned` is when the runner is given it (`GoalRunner(..., shunned=)`, M6), so the night and the goal pass
  over the same buildings; the view reads it.
- `Stock(kind)`: `LootHouse` with `want = kind` (water or food) over the nearest containers holding that use;
  `done "stocked"` once `world.by_use()[kind]` holds more ids than at the goal's start, `failed "none found"` when no
  container answers, `failed "load"` above `LOOT_MAX_LEVEL`.
- `Rest(seconds)`: nothing sent (the frame keeps coming) until its seconds pass on the injected clock, then
  `done "rested"`. Its budget is `max(GOAL_MAX_S, seconds)` (ruling P23-W: a rest is the one goal whose length is its
  content, so a schema-valid Rest up to 120 s ends rested, never on the budget); every other goal's is GOAL_MAX_S.

A goal's `step(world, actions, clock)` is `observe` (the end of its own last action, its own done test) then, while
it runs and its own action is not still running, `choose` (the next command, or None); it returns that command or
None and sets `state`/`reason` itself when it ends. The machines are built on the first step: a goal takes the
runner's `Kit` (one `Explore`, one `LootHouse` and the shelter shuns, shared by every goal of a session, so a place
scanned, a container looted or capped and a pending loot superseded by an instinct outlive the goal that made them,
as the old `forage`/`explore` branches' long-lived machines did), else builds its own (a goal run alone).

`validate(obj) -> Goal` checks a dict against `goals.json` with a stdlib walk (the `type` const, `required`,
`additionalProperties`, each field's `type`, `enum`, `minimum`, `maximum`; a bool is never a number, a non-finite
number is refused) and raises
`ValueError` with a one-line reason; it returns the dataclass. `EXAMPLES` holds one valid argument dict per type.

`ScriptedSource` (`NAME = "scripted"`) is the old forage and explore reshaped, its order: `Stock(kind)` when the view's
`needs_wanted` names water or food (water first) and `stock_uses` says a container answers it; with `needs_wanted`
naming `bandage` (ruling P24-AB, Plan 24 Task 21: a bleeding part with nothing to dress it), `LootBuilding` the
nearest building within BUILDING_R whose `holds` names a bandage, not blocked (its loot takes the kit's `wants`
first: `wanted_uses`); `Shelter` the nearest
known building for which the view's `shelter` reads true (`night.shelter_plan` answers: rooms and an exterior door on
the player's floor) and that is not shunned, when `want_shelter`; then ruling P24-Y's loop (Plan 24 Task 18; E7 walked
on into the woods from game minute 622 to its cap at 786, 545 tiles from the nearest building it knew by 746; Angus:
"clear/kill zombies in the immediate vicinity, then move to the next house"): the clearing is the threat branch's
(P24-X: no goal runs while a fight is sought); `LootBuilding` the nearest building within BUILDING_R (60) with a
container known and not yet looted (the view's `looted` false and `containers` above 0, P24-B 3); `ExploreToward` the
view's `toward` when it names an unlooted building beyond BUILDING_R (its door, else its nearest room square); the
view's `edge` (which leaves out the bearing of a met group, `World.unexplored_edge`, ruling P24-B 2, and, with a
building known, any square with no building within WOODS_R (40): the woods); the view's `toward` when it names the
nearest building with the player beyond WOODS_R of every one (the step back to the known cluster); else the player's
own square while `scanned_here` is false (a fresh session's first scan, before the map holds an edge; with no
building known at all the edge is the plain one, the first building still to find); else `Rest(REST_S)`. The woods
radius is the kit's (`Kit.woods_r`, the view's `woods_r`; Task 18 fix 1, the review's major 6 and ruling 3, E7's
sparse spawn mapped its 40-tile ring and the source then rested): after REST_N (3) Rests in a row ended rested
(another goal's end restarts the run) it widens by WOODS_STEP (20) up to WOODS_MAX_R (80), so the edge grows outward
from the known cluster in rings; a building newly read (`GoalRunner.observe`) resets it to WOODS_R. A
building the view reads `blocked` (every exterior door marked stuck, P24-Z) is never looted nor walked toward. A walk's
target is so always a building or a square within WOODS_R of one, once one is known.
The edge leaves a stuck area (ruling P23-AP 1, E4's twelve walks from one square north of a locked gate): after two
walks from the player's square failed `stuck` unmoved, `world.unexplored_edge` answers only a square a bounded flood
from the player reaches and whose straight line from it crosses no known blocking edge, else none, and the kit's
`Explore` has dropped the place from `scanned`; so the source proposes a loot, else the scan of the player's own
square, never a third walk from that square. A loot goal (`Stock`, `LootBuilding`) is proposed only at the view's load
level `LOOT_MAX_LEVEL` or below, so a heavy load never proposes a goal that fails on its first step. A candidate the
view's `cooled` lists is passed over for the next.

`GoalRunner(source, clock, shunned=None)`: `current` (the running goal or None), `history` (the record rows,
`loop.goals` of task-15-amendments.md: `{type, args, state, reason, startS, endS, source}`, `startS`/`endS` seconds
on the injected clock from the runner's creation, `source` the source's `NAME`), `kit`, `cooled`, `why`.
`rows()` is the record's `loop.goals`: copies of `history`, then the running goal's row (state "running", `endS`
None; Task 16d, the drivers' copy of it removed).
`observe(world, actions)`, which Survive calls every tick before its branches whether or not the goal branch runs
(fix 1, I1): the kit's bookkeeping, then the running goal is closed `superseded` (reason: the type of the action
that replaced it) when the last action sent is not its own, its own being its last sent action, else its `mark` (the
last action sent when the runner took it, so a goal that has sent nothing, a Rest or one whose first command was
cooled, is superseded too: fix 1, the spec gap), closed `superseded` (reason `hold`) once another branch has answered
GOAL_HOLD_SUPERSEDE_TICKS (20) planner ticks in a row without sending (an instinct's hold-without-send never moves
the history, so the mark never reads it: fix wave P, M-7; Survive reports each tick through `held(by_other)`), or
closed `failed "goal budget"` past its budget in wall seconds from when it was taken; so the row's `endS` and the
log's `goal` read the pre-emption on the tick after the instinct's send, not when the goal branch next runs.
`tick(world, actions, view=None)` observes first unless `observe` ran since the last tick (a runner ticked alone),
lets the running goal read its own end, and with no goal running asks the source once (`view` is the dict, or a
callable building it only then), so at most one proposal a tick; the new goal steps at once. A source answering None
is pending (P23-AC): no goal this tick, `pending` true (Survive's goal branch then holds, so nothing lower runs), the
log's `goal` reads `{"pending": <source NAME>}`, and the next tick asks again with a fresh view; the budget starts
only when a goal is taken. A superseded goal is gone; the source may propose the same goal again. A goal that ends
`failed` having sent nothing (a first-step failure: an unknown building, no plan) is cooled per `(type, args)` for
GOAL_COOL_S (30) wall seconds (fix 1, I4): the view lists the cooled goals (`cooled`), the scripted source passes
them over, and a cooled goal a source still proposes is refused for that tick (`why.refused`), no row written. A goal whose leg failed for good (`_Legs`: `no path`, `stuck` with no fence, `no square` at LEG_MIN) is cooled too though it sent, and ExploreToward marks its far target stuck (Task 21 fix 1).
`send(cmd)` sends the
goal's command and hands the `Action` to the goal (Survive sends through it, as the owner). `line()` is the
decision log's `goal` field: `{type, args, state, source}` of the running goal, or of the one that ended this tick,
else `{"pending": <source NAME>}` while the source is pending, else None.
"""
import json
import math
import os
import time
from dataclasses import dataclass, field, fields
from typing import ClassVar, Optional, Protocol, runtime_checkable

from agent.base.items import bag, holds_use
from agent.base.planner.night import (SHUN_MIN, door_blocked, hop_after, player_square, shelter_ended,
                                      shelter_plan, shelter_step)
from agent.base.planner.policies import (CLOTHING_HELD_N, LOOT_MAX_LEVEL, LOOT_WANTS, PREEMPTED, SCAN_R, Explore, LootHouse, centre,
                                         me_floor, me_xy, place_of)
from agent.base.pza1 import Climb, Scan, WalkTo, Window

GOAL_MAX_S = 90.0     # wall seconds a goal may run before it is failed "goal budget" and replaced (a Rest: P23-W)
GOAL_COOL_S = 30.0    # wall seconds a goal that failed having sent nothing is not taken again (fix 1, I4)
GOAL_HOLD_SUPERSEDE_TICKS = 20   # planner ticks another branch holds without sending before the goal is superseded
ARRIVE_R = 1.5        # tiles: an ExploreToward whose place is scanned is done within this of its point
REST_S = 30.0         # the scripted source's rest
STOCK_WANTS = ("water", "container", "clothing", "food", "bandage", "weapon")   # LootBuilding's order of uses (P24-Y)
CONTAINERS_HELD_N = 2   # vessels held (`water` and `container`) at which `container` is no longer wanted (Task 18 fix
                        # 1, the review's major 5, its number: one or two held, so the cap goes to the food)
SMASH_MIN_HEALTH = 60.0   # health at or above which a window may be smashed (a smash is noise and, 1 time in 2, a glass cut:
                      # review-t9-fix9 ruling 6, "health above the bandage threshold"; a judgment, survive's pair-flee line)
SMASH_ZOMBIE_R = 25.0   # tiles: a smash waits while a zombie is listed this near (the noise carries: the view's widest band)
WINDOW_DEAD = ("not a window", "not valid", "fell", "failed", "no square")   # a window action's ends that leave the
                      # window out for DOOR_RETRY_MIN game minutes (World.note_window_fail); `locked` is read apart
WINDOW_REPEAT = ("no path", "not adjacent", "interrupted")   # a window action's ends that are tried once more; the
                      # second within DOOR_RETRY_MIN leaves the window out like a WINDOW_DEAD end (review-t24 major 2)
BUILDING_R = 60.0     # tiles: an unlooted building this near is looted; farther, it is walked toward first (P24-Y)
WOODS_R = 40.0        # tiles: a square with no building known this near is the woods, never a walk's target (P24-Y)
REST_N = 3            # Rests in a row, no building newly read, before the woods radius widens (Task 18 fix 1, ruling
                      # 3, a judgment: 90 s of rest)
WOODS_STEP = 20.0     # tiles the woods radius widens by at each REST_N rests (ruling 3)
WOODS_MAX_R = 80.0    # tiles: the widest woods radius (ruling 3: walks reach up to 60, then 80 tiles from the cluster)
STOCK_KINDS = ("water", "food")                        # Stock's kinds, the scripted source's order
LEG_MAX = 40.0        # tiles: a goal destination farther than the leg length is walked to in legs of at most it; the
                      # length is `leg_max(world)` off the frame's `me.loadedWidth` (ruling P24-AI, #4375: the client
                      # holds a grid of 8-tile chunks centred on the player's chunk, 104 tiles wide at 1280 x 720, so a
                      # square more than 48 tiles off on an axis may answer no square), this constant with none read
                      # (an older Lua: the 1280 x 720 harness's 40); P24-AC's 30 superseded
LEG_CHUNK = 8         # tiles in a chunk (#4375): the leg keeps one chunk inside the half window
LEG_MIN = 10.0        # tiles: a leg failed `no square` is halved down to this (P24-AC), then the goal fails `no square`
LEG_SQ_MARGIN = 0.75  # tiles a leg's point is drawn short of LEG_MAX so its square's centre lies within it (<= sqrt 2 / 2)
RUN_FIELDS = ("state", "reason", "started_wall")
STATES = ("running", "done", "failed", "superseded")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema", "goals.json")
WANT_USES = {"weapon": "weapon", "bag": None}   # a LootBuilding want's loot use (Task 29); a bag: no loot filter
OPTIONAL_FIELDS = {"LootBuilding": ("want",)}    # schema fields a goal may leave out (None, left out of args())
EXAMPLES = {"ExploreToward": {"x": 120, "y": 205}, "LootBuilding": {"building": 3}, "Shelter": {"building": 3},
            "Stock": {"kind": "water"}, "Rest": {"seconds": 30.0}}

__all__ = ["Goal", "ExploreToward", "LootBuilding", "Shelter", "Stock", "Rest", "GoalSource", "ScriptedSource",
           "GoalRunner", "Kit", "validate", "open_uses", "int_id", "goal_key", "GOAL_MAX_S", "GOAL_COOL_S",
           "GOAL_HOLD_SUPERSEDE_TICKS",
           "ARRIVE_R", "REST_S", "STOCK_WANTS", "BUILDING_R", "WOODS_R", "WINDOW_REPEAT", "CONTAINERS_HELD_N", "CLOTHING_HELD_N", "SMASH_MIN_HEALTH", "SMASH_ZOMBIE_R", "smash_ok", "window_pick", "REST_N", "WOODS_STEP",
           "WOODS_MAX_R", "wanted_uses", "LEG_MAX", "LEG_MIN", "LEG_CHUNK", "leg_max",
           "STOCK_KINDS", "RUN_FIELDS", "STATES", "SCHEMA_PATH", "EXAMPLES", "WANT_USES", "OPTIONAL_FIELDS", "held_of"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def int_id(v):
    """An int that is not a bool (a building id the schema's integer admits)."""
    return isinstance(v, int) and not isinstance(v, bool)


def goal_key(typ, args):
    """The cooling key of a goal: its type and its args as sorted JSON."""
    return typ, json.dumps(args, sort_keys=True)


def open_uses(world, loot, key, waiting=None):
    """The uses of LOOT_WANTS a loot could still take at container `key`: the container holds an item of the use, is
    not marked looted for it, and is not waiting on the cap (`LootHouse.waiting`, read off `loot` unless `waiting`
    {use: keys} is given). The view counts a container with none as looted."""
    c = world.containers.get(key)
    if c is None or not c["n"] or not c["items"]:
        return []
    out = []
    for u in LOOT_WANTS:
        if (u == "clothing" and not world.can("wear")) or u in c["looted"] or not any(holds_use(i, u) for i in c["items"]):
            continue
        skip = waiting[u] if waiting is not None else (loot.waiting(u) if loot is not None else ())
        if key not in skip:
            out.append(u)
    return out


def wanted_uses(world, wants=()):
    """STOCK_WANTS in order, `container` left out once CONTAINERS_HELD_N or more vessels are held (`by_use()`'s
    `water` and `container`: Task 18 fix 1, the review's major 5), `clothing` left out on a build without `wear`
    (PZA/1.6: no filter, no wear) and once CLOTHING_HELD_N or more unworn garments are held (a container's garments
    are told by name only, so what would beat a worn location is the wear rule's to say once they are held, and the
    surplus is bounded here: Task 24); the uses of `wants` (the kit's: the care's `bandage`, ruling P24-AB) first, in
    their order."""
    uses = world.by_use()
    held = len(uses.get("water", ())) + len(uses.get("container", ()))
    spare_clothes = sum(1 for i in uses.get("clothing", ()) if world.inventory[i].get("worn") is not True)
    order = tuple(wants) + tuple(u for u in STOCK_WANTS if u not in wants)
    return tuple(u for u in order if (u != "container" or held < CONTAINERS_HELD_N)
                 and (u != "clothing" or (world.can("wear") and spare_clothes < CLOTHING_HELD_N)))


def held_of(world, want):
    """How many held items answer a LootBuilding `want` (Task 29): a bag by `items.bag`'s name guess, else the
    want's use in `world.by_use()`."""
    if want == "bag":
        return sum(1 for it in world.inventory.values() if bag(it.get("fullType")))
    return len(world.by_use().get(WANT_USES.get(want) or want, ()))


def _usable_building(world, b, shunned):
    """Whether building `b` is one the view would send a loot to (review-t24 minor 5): not shunned, its exterior doors
    not all marked stuck (the window route is left out: it would recurse into `smash_ok`), and not looted out (a
    building with containers known and no open use at any is; one with none known is not, as in the view)."""
    if b in shunned or door_blocked(world, b, me_floor(world)):
        return False
    cs = [k for k in world.containers if (world.map.get(k[:3]) or {}).get("building") == b]
    return not cs or any(open_uses(world, None, k) for k in cs)


def smash_ok(world, building, shunned=()):
    """Whether a window may be smashed now (review-t9-fix9 ruling 6; the brief's rule): the character has no other
    usable building (`_usable_building`) known within BUILDING_R (this one is the only roof), no zombie is listed
    within SMASH_ZOMBIE_R and the health is at or above SMASH_MIN_HEALTH."""
    mx, my = me_xy(world)
    if any(world.building_dist(mx, my, b) <= BUILDING_R and _usable_building(world, b, shunned)
           for b in world.building_boxes() if b != building):
        return False
    if any(z.get("x") is not None and z.get("y") is not None and math.hypot(z["x"] - mx, z["y"] - my) <= SMASH_ZOMBIE_R
           for z in world.zombies.values()):
        return False
    health = (world.body or {}).get("health")
    return _num(health) and health >= SMASH_MIN_HEALTH


def window_pick(world, building, shunned=()):
    """`(x, y, z, smash)` of the building's window to try, else None (Task 24, the route past a stuck door): the
    build announces `window`; windows on the player's floor not barricaded and not left out by a failed end
    (`WINDOW_DEAD`); an open one first, then a shut unlocked one (opened, then climbed: no noise), then a locked one
    (the record's `locked`, or a try that ended `locked`) only when `smash_ok`, with `smash` true; each nearest
    the player."""
    if not world.can("window"):
        return None
    z = me_floor(world)
    mx, my = me_xy(world)
    smash = None   # smash_ok's answer, read at most once and only for a locked window
    best = None
    for sq in world.windows(building):
        rec = (world.map.get(sq) or {}).get("window") or {}
        fail = world.window_fail(sq)
        if sq[2] != z or rec.get("barricaded") is True or fail in WINDOW_DEAD:
            continue
        locked = rec.get("locked") is True or fail == "locked"
        if locked:
            smash = smash_ok(world, building, shunned) if smash is None else smash
            if not smash:
                continue
        rank = (locked, rec.get("open") is not True, math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my), sq)
        if best is None or rank < best[0]:
            best = (rank, sq, locked)
    return None if best is None else (best[1][0], best[1][1], best[1][2], best[2])


# ---------------------------------------------------------------- the shared machines
class Kit:
    """The machines a session's goals share: one `Explore` (its scanned places), one `LootHouse` (its pending loots,
    capped squares), `shunned` {building: world minutes}, the Shelter goals' shuns (`Night.shunned` when given, M6),
    and the woods radius (`woods_r`, `rests` the Rests in a row ended rested, `known` the buildings known when it was
    last reset: Task 18 fix 1, ruling 3), and `wants` (the uses a loot takes first: the care's `bandage`, P24-AB)."""

    def __init__(self, world=None, actions=None, clock=time.time, shunned=None):
        self.explore = Explore(world, actions, clock)
        self.loot = LootHouse(world, actions, clock)
        self.shunned = {} if shunned is None else shunned
        self.woods_r, self.rests, self.known = WOODS_R, 0, 0
        self.wants = ()   # the uses a loot takes first (Survive's need marks, `survive.KIT_WANTS`: P24-AB)

    def rested(self, goal):
        """A goal ended: a Rest ended rested counts one, REST_N in a row widening the woods radius by WOODS_STEP up
        to WOODS_MAX_R; any other goal's end restarts the count (a superseded Rest neither counts nor restarts it)."""
        if goal.TYPE != "Rest":
            self.rests = 0
        elif goal.state == "done":
            self.rests += 1
            if self.rests >= REST_N:
                self.woods_r, self.rests = min(self.woods_r + WOODS_STEP, WOODS_MAX_R), 0

    def read_buildings(self, world):
        """A building newly read (`World.building_boxes` grew) resets the woods radius to WOODS_R."""
        n = len(world.building_boxes())
        if n > self.known:
            self.woods_r, self.rests = WOODS_R, 0
        self.known = n

    def bind(self, world, actions):
        for m in (self.explore, self.loot):
            m.world, m.actions = world, actions

    def observe(self, world, actions):
        """The machines' bookkeeping, every tick (idempotent): a loot's end marks its containers, a stuck walk its
        square, a scan ended badly unmarks its place."""
        self.bind(world, actions)
        self.loot.observe()
        self.explore.observe()

    def hop_after(self, world, action, climbed=()):
        """The route climb's read (ruling P24-G 4): `night.hop_after`, shared with `Night`'s own shelter walk."""
        return hop_after(world, action, climbed)

    def climbed(self, world, walk):
        """A climb after `walk` ended done: the walk target's stuck mark (`Explore`'s, at the stuck end) is dropped."""
        world.unmark_stuck(int(math.floor(walk.args.get("x"))), int(math.floor(walk.args.get("y"))))

    def shunned_now(self, world):
        """The buildings shunned within SHUN_MIN game minutes of `world.world_minutes()` (I-1)."""
        now = world.world_minutes()
        return {b for b, at in self.shunned.items() if now - at < SHUN_MIN}


# ---------------------------------------------------------------- the goals
@dataclass
class Goal:
    """A goal: see the module docstring. Subclasses add their schema fields and `choose`."""
    TYPE: ClassVar[str] = ""
    state: str = field(default="running", kw_only=True)
    reason: Optional[str] = field(default=None, kw_only=True)
    started_wall: Optional[float] = field(default=None, kw_only=True)

    def __post_init__(self):
        self.kit = None        # the runner's Kit, else built on the first step
        self.last = None       # the last Action this goal sent
        self.mark = None       # the last action sent (by anyone) when the runner took this goal
        self.why = {}          # the goal's inputs to its last choice, logged under the goal branch
        self.sent_n = 0        # commands this goal sent
        self._read = None      # the last action whose end observe() has read
        self._begun = False

    # -- the record ---------------------------------------------------------------------------------------------
    def args(self):
        """The schema fields, an optional one left unset (None: OPTIONAL_FIELDS) left out."""
        opt = OPTIONAL_FIELDS.get(self.TYPE, ())
        return {f.name: getattr(self, f.name) for f in fields(self)
                if f.name not in RUN_FIELDS and not (f.name in opt and getattr(self, f.name) is None)}

    def row(self):
        return {"type": self.TYPE, "args": self.args(), "state": self.state, "reason": self.reason}

    @property
    def running(self):
        return self.state == "running"

    def end(self, state, reason):
        if self.running:
            self.state, self.reason = state, reason

    def budget(self):
        """Wall seconds this goal may run from its proposal."""
        return GOAL_MAX_S

    # -- the step -----------------------------------------------------------------------------------------------
    def begin(self, world, actions, clock):
        """Once, on the first observe: the machines (the runner's kit, else its own), the clock's start."""
        if self._begun:
            return
        self._begun = True
        if self.kit is None:
            self.kit = Kit(world, actions, clock)
        if self.started_wall is None:
            self.started_wall = clock()
        self.kit.bind(world, actions)
        self.start(world)

    def start(self, world):
        """A subclass's first-step setup."""

    def busy(self, actions):
        return self.last is not None and not actions.done(self.last)

    def observe(self, world, actions, clock):
        self.begin(world, actions, clock)
        if not self.running:
            return
        a = self.last
        if a is not None and a is not self._read and actions.done(a):
            self._read = a
            if not (a.state == "failed" and a.reason == PREEMPTED):   # a superseded step is chosen again
                self.ended(world, a)
        if self.running and not self.busy(actions):
            self.check(world, clock)

    def ended(self, world, action):
        """Read the end of this goal's own last action (never a superseded one)."""

    def check(self, world, clock):
        """The goal's own done test, read while its action is not running."""

    def step(self, world, actions, clock):
        self.observe(world, actions, clock)
        if not self.running or self.busy(actions):
            return None
        return self.choose(world, actions, clock)

    def choose(self, world, actions, clock):
        raise NotImplementedError

    def sent(self, cmd, action):
        self.last = action
        self.sent_n += 1


class _Climbing:
    """The route climb's goal side (ruling P24-G 4; lifted out of `ExploreToward` at Task 10 fix 1, minor 9, for the
    `Shelter` walks too): `_climbs()` once at the start; `_stuck(world, walk)` after a walk's end, True when a climb is
    due (`Kit.hop_after`); `_climb_ended(world, action)` after the climb's, True when it ended done (the fence kept in
    `climbed`, the walk target's stuck mark dropped: `Kit.climbed`); `_climb_cmd()` the due `Climb`, else None."""

    def _climbs(self):
        self.climb = None        # the fence square (x, y) the next choose climbs, else None
        self.climbed = set()     # the fence squares this goal climbed
        self.stuck_walk = None   # the walk whose stuck end the due or running climb answers

    def _stuck(self, world, walk):
        hop = self.kit.hop_after(world, walk, self.climbed)
        if hop is None:
            return False
        self.climb, self.stuck_walk = hop, walk
        return True

    def _climb_ended(self, world, action):
        if action.state != "done":
            return False
        self.climbed.add((action.args.get("x"), action.args.get("y")))
        self.kit.climbed(world, self.stuck_walk)
        return True

    def _climb_cmd(self):
        if self.climb is None:
            return None
        x, y = self.climb
        self.climb = None
        return Climb(x, y)


def leg_max(world):
    """Ruling P24-AI (#4375): the longest goal leg, `LEG_CHUNK * floor(width / 16) - LEG_CHUNK` tiles off the World's
    last `me.loadedWidth` (40 at 104 tiles, 64 at 152: half the window's chunks less the player's own, one chunk to
    spare for a chunk not yet streamed in at the edge), never under LEG_MIN; LEG_MAX with no width read."""
    w = getattr(world, "loaded_width", None)
    if not isinstance(w, int) or isinstance(w, bool) or w <= 0:
        return LEG_MAX
    return max(float(LEG_CHUNK * (w // (2 * LEG_CHUNK)) - LEG_CHUNK), LEG_MIN)


class _Legs:
    """Ruling P24-AC (Plan 24 Task 21; E8, `e_day_8-20261029-174023`: from game minute 618 every one of the goal's 278
    walks failed `no square` within 0.53 s, its targets 62 to 234 tiles off, each failure marking the target stuck so
    the edge stepped to the next far square): a goal destination farther than `leg_len` (`leg_max`, P24-AI) is approached in
    legs along the straight line, each a `WalkTo` at a walk to the centre of the square `leg_len` - LEG_SQ_MARGIN
    tiles toward it (so within `leg_len`); a leg that ends done restores the full length and the next leg follows; one that
    fails `no square` (the client holds no square there) halves `leg_len`, down to LEG_MIN, and the next leg is
    re-sent shorter; at LEG_MIN a `no square` fails the goal. A leg's `no square` never marks a square stuck
    (`Explore.sent`'s `leg`), so the far target stays the goal's. `_legs()` once at the start; `_leg_cmd(world, x, y)`
    the leg toward (x, y), else None when it lies within `leg_len` (the direct walk is the goal's own); `_leg_ended(
    action)` "next" (go on), "fail" (the leg's own failure: the goal reads it) or None (not a leg)."""

    def _legs(self):
        self.leg_len = None      # tiles: the next leg's length, None for the full `leg_max` (P24-AI: read at each leg)
        self.leg = None          # (x, y) of the leg the last choose sent, else None
        self.cool = False        # a leg failed for good: the runner cools the goal though it sent (`GoalRunner._close`)

    def _leg_cmd(self, world, x, y):
        if self.leg_len is None:
            self.leg_len = leg_max(world)
        mx, my = me_xy(world)
        d = math.hypot(x - mx, y - my)
        if d <= self.leg_len:
            self.leg = None
            return None
        k = (self.leg_len - LEG_SQ_MARGIN) / d
        self.leg = centre((mx + (x - mx) * k, my + (y - my) * k))
        return WalkTo(self.leg[0], self.leg[1], "walk")

    def _leg_ended(self, action):
        if self.leg is None or action.type != "walkTo" or (action.args.get("x"), action.args.get("y")) != self.leg:
            return None
        self.leg = None
        if action.state == "done":
            self.leg_len = None   # the full length again, read off the window at the next leg
            return "next"
        if action.reason == "no square" and self.leg_len is not None and self.leg_len > LEG_MIN:
            self.leg_len = max(self.leg_len / 2.0, LEG_MIN)
            return "next"
        return "fail"

    def _leg_failed(self, world):
        """A leg's final failure (`no path`; `stuck` with no fence to climb; `no square` at LEG_MIN; review-t21's
        blocker, the E8 loop without the edge's stepping): the goal is cooled for GOAL_COOL_S whatever it sent, so the
        source proposes another; a goal with a far target of its own (`mark_far`) marks it as a direct walk's failure
        would."""
        self.cool = True
        self.mark_far(world)

    def mark_far(self, world):
        """The goal's far target marked stuck (ExploreToward's; a loot's container is left to the cooling)."""


@dataclass
class ExploreToward(_Legs, _Climbing, Goal):
    TYPE: ClassVar[str] = "ExploreToward"
    x: int
    y: int

    def _dist(self, world):
        mx, my = me_xy(world)
        return math.hypot(self.x - mx, self.y - my)

    def start(self, world):
        self._climbs()
        self._legs()

    def mark_far(self, world):
        world.mark_stuck(self.x, self.y)

    def ended(self, world, action):
        leg = self._leg_ended(action)
        if leg == "next":
            return
        if action.type == "walkTo":
            if action.state == "done":
                self.end("done", "arrived")
            elif not self._stuck(world, action):
                if leg == "fail":
                    self._leg_failed(world)
                self.end("failed", action.reason or action.state)
        elif action.type == "climb":
            if not self._climb_ended(world, action):
                self.end("failed", action.reason or action.state)
        elif action.type == "scan" and action.state != "done":
            self.end("failed", action.reason or action.state)

    def check(self, world, clock):
        if place_of(world) in self.kit.explore.scanned and self._dist(world) <= ARRIVE_R:
            self.end("done", "arrived")

    def choose(self, world, actions, clock):
        ex = self.kit.explore
        place = place_of(world)
        if place not in ex.scanned:
            self.why = {"scanAt": list(place), "toward": [self.x, self.y]}
            return Scan(SCAN_R)
        climb = self._climb_cmd()
        if climb is not None:
            self.why = {"toward": [self.x, self.y], "climb": [climb.x, climb.y]}
            return climb
        self.why = {"toward": [self.x, self.y], "dist": self._dist(world)}
        leg = self._leg_cmd(world, self.x, self.y)   # P24-AC: a far target in legs
        if leg is not None:
            self.why.update(leg=[leg.x, leg.y], legLen=self.leg_len)
            return leg
        return WalkTo(self.x, self.y, "walk")

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self.kit.explore.sent(cmd, action, leg=self.leg is not None and cmd.TYPE == "walkTo")


class _Looting:
    """The loot goals' shared send: the kit's LootHouse records its pending loot (a loot's own interact only, never a
    route step's open)."""

    def sent(self, cmd, action):
        super().sent(cmd, action)
        if cmd.TYPE == "interact" and cmd.args().get("kind") == "loot":
            self.kit.loot.sent(cmd, action)

    def _guard(self):
        level = self.kit.loot.level()
        if level > LOOT_MAX_LEVEL:
            self.why = {"level": level, "hold": True}
            self.end("failed", "load")
            return True
        return False


@dataclass
class LootBuilding(_Legs, _Looting, Goal):
    TYPE: ClassVar[str] = "LootBuilding"
    building: int
    want: Optional[str] = None

    def start(self, world):
        self._legs()
        self.base = held_of(world, self.want) if self.want is not None else None   # Task 29: the want's held count
        self.route = None        # the entry plan (night.shelter_plan) while the route is due (P24-Z), else None
        self.route_due = False   # a loot failed `not adjacent`: in by a door the World has not marked first
        self.window = None       # the window route's (x, y, z) while its Window runs, else None (Task 24)
        self.no_doors = False    # the route's doors are spent (the plan answered none or the machine shunned): windows

    def keys(self, world):
        """The container keys on the building's squares."""
        return {k for k in world.containers if (world.map.get(k[:3]) or {}).get("building") == self.building}

    def _inside(self, world):
        sq = player_square(world)
        s = world.map.get(sq) if sq is not None else None
        return s is not None and s.get("room") is not None and s.get("building") == self.building

    def ended(self, world, action):
        """A loot failed `not adjacent` makes the route due (P24-Z); a route step's end is read into its plan
        (`night.shelter_ended`), `shun` (no door left) failing the goal `no door`; a leg toward a far container
        (P24-AC) goes on, or fails the goal under its reason."""
        leg = self._leg_ended(action)
        if leg is not None:
            if leg == "fail":
                self._leg_failed(world)
                self.end("failed", action.reason or action.state)
            return
        if action.type == "interact" and action.args.get("kind") == "loot":
            if action.state == "failed" and action.reason == "not adjacent":
                self.route_due = True
            return
        if action.type == "window":
            self._window_ended(world, action)
            return
        if self.route is not None:
            out = shelter_ended(self.route, action)
            self.why = dict(self.why, ended=out)
            if out == "shun":
                self.route, self.no_doors = None, True   # no exterior door left: the window route, else it fails
                if window_pick(world, self.building, self.kit.shunned_now(world)) is None:
                    self.end("failed", "no door")

    def check(self, world, clock):
        if self.want is not None and held_of(world, self.want) > self.base:
            self.why = dict(self.why, want=self.want, met=True)
            self.end("done", "want met")

    def _uses(self, world):
        """The uses in the order the loot takes them: the kit's wants, then the goal's want's use (Task 29)."""
        use = WANT_USES.get(self.want)
        wants = tuple(self.kit.wants) + ((use,) if use is not None and use not in self.kit.wants else ())
        return wanted_uses(world, wants)

    def _window_ended(self, world, action):
        """A window action's end (Task 24): done leaves the route (the character stands inside; the care branch reads the
        wounds from the frame's body parts whatever `cut` says, the result's `cut` being unreliable in multiplayer: it is
        logged); a failure leaves the window out (`World.note_window_fail`): `locked` lets the next try smash it."""
        sq = self.window
        self.window = None
        if action.state == "done":
            self.route_due = False
            res = action.result if isinstance(action.result, dict) else {}
            self.why = dict(self.why, ended="window", cut=res.get("cut"), wounds=res.get("wounds"))
            return
        if sq is not None:
            reason = action.reason or action.state
            prior = world.window_fail(sq)
            # review-t24 major 2: a smash try refused `locked` (a barricade or a frame a smash cannot cure), a second
            # `locked`, or a second `no path` / `not adjacent` / `interrupted` leaves the window out for good
            if reason == "locked" and (action.args.get("smash") is True or prior == "locked"):
                reason = "failed"
            elif reason in WINDOW_REPEAT and prior == reason:
                reason = "failed"
            world.note_window_fail(sq, reason)
        self.why = dict(self.why, ended="window " + (action.reason or action.state))

    def _route(self, world):
        """The route's next step while it is due and the player is not inside the building, else None (the route
        done or not due); with no unmarked exterior door left (`night.shelter_plan` answers none, or the machine shuns
        every door) the window route (`_window_pick`, one `Window` at a time), else the goal ends `failed "no door"`."""
        if not self.route_due or self._inside(world):
            self.route_due, self.route, self.window, self.no_doors = False, None, None, False
            return None
        if self.route is None and not self.no_doors:
            self.route = shelter_plan(world, self.building)
        cmd, step = (None, "shun") if self.route is None else shelter_step(world, self.route)
        if step == "shun":
            self.route = None
            pick = window_pick(world, self.building, self.kit.shunned_now(world))
            if pick is None:
                self.why = {"building": self.building, "route": None}
                self.end("failed", "no door")
                return None
            self.window = pick[:3]
            self.why = {"building": self.building, "route": "window", "window": [pick[0], pick[1]], "smash": pick[3]}
            return Window(pick[0], pick[1], smash=pick[3])
        if step in ("close", "done"):   # in: the loot resumes from inside
            self.route_due, self.route = False, None
            return None
        door = self.route["doors"][self.route["door_i"]]
        self.why = {"building": self.building, "route": step, "door": [door[0], door[1]]}
        return cmd

    def choose(self, world, actions, clock):
        if self._guard():
            return None
        if (not self.route_due and world.can("window") and not self._inside(world)
                and door_blocked(world, self.building, me_floor(world))):
            self.route_due = True   # Task 24: every exterior door marked from outside, so the loot is not tried first
        cmd = self._route(world)
        if cmd is not None or not self.running:
            return cmd
        loot = self.kit.loot
        loot.within = self.keys(world)
        try:
            want = next((u for u in self._uses(world) if loot.target(u) is not None), None)
            if want is not None:
                key = loot.target(want)
                leg = self._leg_cmd(world, *centre(key))   # P24-AC: a container beyond the leg length is walked to in legs
                if leg is not None:
                    self.why = {"building": self.building, "want": want, "container": list(key),
                                "leg": [leg.x, leg.y], "legLen": self.leg_len}
                    return leg
                loot.want = want
                cmd = loot.choose()
                self.why = dict(loot.why, building=self.building)
                return cmd
        finally:
            loot.within = None
        self.why = {"building": self.building, "want": None}
        if self.sent_n:
            self.end("done", "looted")
        else:
            self.end("failed", "nothing to loot")
        return None


@dataclass
class Shelter(_Climbing, Goal):
    TYPE: ClassVar[str] = "Shelter"
    building: int

    def start(self, world):
        self._climbs()
        self.plan = shelter_plan(world, self.building)
        if self.plan is None:
            self.why = {"building": self.building, "plan": None}
            self.kit.shunned[self.building] = world.world_minutes()   # I3: never re-proposed every tick
            self.end("failed", "no plan")

    def _shun(self, world):
        self.kit.shunned[self.building] = world.world_minutes()
        self.end("failed", "shun")

    def ended(self, world, action):
        """A step's end into the plan (`shelter_ended`); a walk stuck at a hoppable edge climbs first (the plan's step
        kept), and a climb that did not end done is read as that walk's own stuck end."""
        if action.type == "climb":
            if self._climb_ended(world, action):
                self.why = dict(self.why, ended="climbed")
                return
            action = self.stuck_walk
        elif self._stuck(world, action):
            self.why = dict(self.why, ended="climb")
            return
        out = shelter_ended(self.plan, action)
        self.why = dict(self.why, ended=out)
        if out == "shun":
            self._shun(world)

    def check(self, world, clock):
        if self.plan["step"] == "done":
            self.why = dict(self.why, step="done")
            self.end("done", "inside")

    def choose(self, world, actions, clock):
        climb = self._climb_cmd()
        if climb is not None:
            self.why = {"step": "climb", "building": self.building, "climb": [climb.x, climb.y]}
            return climb
        cmd, step = shelter_step(world, self.plan)
        self.why = {"step": step, "building": self.building, "door": list(self.plan["doors"][self.plan["door_i"]])}
        if step == "shun":
            self._shun(world)
            return None
        if step == "done":
            self.end("done", "inside")
            return None
        return cmd


@dataclass
class Stock(_Looting, Goal):
    TYPE: ClassVar[str] = "Stock"
    kind: str

    def _held(self, world):
        return len(world.by_use().get(self.kind, ()))

    def start(self, world):
        self.base = self._held(world)

    def check(self, world, clock):
        if self._held(world) > self.base:
            self.end("done", "stocked")

    def choose(self, world, actions, clock):
        if self._guard():
            return None
        loot = self.kit.loot
        loot.want, loot.within = self.kind, None
        cmd = loot.choose()
        self.why = dict(loot.why, held=self._held(world), base=self.base)
        if cmd is None:
            self.end("failed", "none found")
        return cmd


@dataclass
class Rest(Goal):
    TYPE: ClassVar[str] = "Rest"
    seconds: float

    def budget(self):
        return max(GOAL_MAX_S, self.seconds)   # ruling P23-W

    def check(self, world, clock):
        if clock() - self.started_wall >= self.seconds - 1e-9:
            self.end("done", "rested")

    def choose(self, world, actions, clock):
        self.why = {"rest": self.seconds, "left": self.seconds - (clock() - self.started_wall)}
        return None


TYPES = {c.TYPE: c for c in (ExploreToward, LootBuilding, Shelter, Stock, Rest)}


# ---------------------------------------------------------------- validate
_SCHEMA = {}


def _entries():
    if not _SCHEMA:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            for e in json.load(f)["oneOf"]:
                _SCHEMA[e["properties"]["type"]["const"]] = e
    return _SCHEMA


_JSON_TYPES = {"integer": int_id, "number": _num, "string": lambda v: isinstance(v, str)}


def _field(t, name, spec, v):
    kind = spec.get("type")
    if kind is not None and not _JSON_TYPES[kind](v):
        raise ValueError("%s.%s: %r is not of type %s" % (t, name, v, kind))
    if _num(v) and not math.isfinite(v):
        raise ValueError("%s.%s: %r is not finite" % (t, name, v))
    if "enum" in spec and v not in spec["enum"]:
        raise ValueError("%s.%s: %r not in %s" % (t, name, v, spec["enum"]))
    if "maximum" in spec and v > spec["maximum"]:
        raise ValueError("%s.%s: %r above the maximum %s" % (t, name, v, spec["maximum"]))
    if "minimum" in spec and v < spec["minimum"]:
        raise ValueError("%s.%s: %r below the minimum %s" % (t, name, v, spec["minimum"]))


def validate(obj):
    """The goal `obj` names, checked against `goals.json` (the module docstring); ValueError with a one-line reason."""
    if not isinstance(obj, dict):
        raise ValueError("goal: %r is not an object" % (obj,))
    t = obj.get("type")
    e = _entries().get(t) if isinstance(t, str) else None
    if e is None:
        raise ValueError("goal: unknown goal type %r" % (t,))
    props = e["properties"]
    for k in e.get("required", ()):
        if k not in obj:
            raise ValueError("%s: missing %s" % (t, k))
    if e.get("additionalProperties") is False:
        extra = sorted(k for k in obj if k not in props)
        if extra:
            raise ValueError("%s: unexpected %s" % (t, ", ".join(extra)))
    for k, v in obj.items():
        if k != "type":
            _field(t, k, props[k], v)
    return TYPES[t](**{k: v for k, v in obj.items() if k != "type"})


# ---------------------------------------------------------------- the sources
@runtime_checkable
class GoalSource(Protocol):
    NAME: str

    def propose(self, view: dict) -> Optional[Goal]:
        """A goal, or None while the source is pending (P23-AC)."""
        ...


def _nearest_first(buildings):
    return sorted((b for b in buildings if int_id(b.get("id"))),
                  key=lambda b: (b["dist"] if _num(b.get("dist")) else math.inf, b["id"]))


class ScriptedSource:
    """The scripted order (the module docstring)."""
    NAME = "scripted"

    def propose(self, view):
        cooled = {goal_key(c.get("type"), c.get("args")) for c in view.get("cooled") or () if isinstance(c, dict)}
        return next((g for g in self.candidates(view) if goal_key(g.TYPE, g.args()) not in cooled), Rest(REST_S))

    def candidates(self, view):
        """The goals in the scripted order (the module docstring), each one the view admits."""
        level = (view.get("load") or {}).get("level")
        loot_ok = not _num(level) or level <= LOOT_MAX_LEVEL
        wanted, ready = view.get("needs_wanted") or (), view.get("stock_uses") or ()
        if loot_ok:
            for kind in STOCK_KINDS:
                if kind in wanted and kind in ready:
                    yield Stock(kind)
        bs = _nearest_first(view.get("buildings") or ())
        if loot_ok and "bandage" in wanted:   # P24-AB: a wound with nothing to dress it loots a known bandage first
            for b in bs:
                if ((b.get("holds") or {}).get("bandage") and _num(b.get("dist")) and b["dist"] <= BUILDING_R
                        and not b.get("blocked")):
                    yield LootBuilding(b["id"])
        if view.get("want_shelter"):
            for b in bs:
                if b.get("shelter") and not b.get("shunned"):
                    yield Shelter(b["id"])
        if loot_ok:
            for b in bs:
                if (b.get("looted") is False and (b.get("containers") or 0) > 0 and _num(b.get("dist"))
                        and b["dist"] <= BUILDING_R and not b.get("blocked")):   # P24-Z: every door stuck
                    yield LootBuilding(b["id"])
        toward = view.get("toward") or {}
        to = toward.get("door") or toward.get("square")
        if toward.get("for") == "unlooted" and to:
            yield ExploreToward(int(to[0]), int(to[1]))
        edge = view.get("edge")
        if edge:
            yield ExploreToward(int(edge[0]), int(edge[1]))
        if toward.get("for") == "cluster" and to:
            yield ExploreToward(int(to[0]), int(to[1]))
        pos = view.get("pos") or {}
        if not view.get("scanned_here") and _num(pos.get("x")) and _num(pos.get("y")):
            yield ExploreToward(int(math.floor(pos["x"])), int(math.floor(pos["y"])))


# ---------------------------------------------------------------- the runner
class GoalRunner:
    def __init__(self, source, clock=time.time, shunned=None):
        self.source = source
        self.clock = clock
        self.t0 = clock()
        self.kit = Kit(clock=clock, shunned=shunned)
        self.current = None
        self.history = []      # loop.goals: {type, args, state, reason, startS, endS, source} per goal run
        self.cooled = {}       # goal_key -> wall until a goal that failed having sent nothing is refused
        self.why = {}
        self.actions = None
        self.pending = False   # the source answered None (P23-AC) on the last ask and no goal runs
        self.hold_ticks = 0    # planner ticks in a row another branch held without sending, the goal running (M-7)
        self._ended_now = None
        self._observed = False

    def _name(self):
        return getattr(self.source, "NAME", None)

    def _s(self, wall):
        return wall - self.t0 if _num(wall) else None

    def _close(self, g):
        now = self.clock()
        self.history.append(dict(g.row(), startS=self._s(g.started_wall), endS=self._s(now), source=self._name()))
        if g.state == "failed" and (g.sent_n == 0 or getattr(g, "cool", False)):
            self.cooled[goal_key(g.TYPE, g.args())] = now + GOAL_COOL_S
        self.kit.rested(g)
        self._ended_now, self.current, self.hold_ticks = g, None, 0

    def cooling(self):
        """The goals cooled now, as `[{type, args}]` sorted (the view's `cooled`)."""
        now = self.clock()
        return [{"type": k[0], "args": json.loads(k[1])} for k, until in sorted(self.cooled.items()) if until > now]

    def observe(self, world, actions):
        """The kit's bookkeeping and the running goal's pre-emption and budget (the module docstring); Survive calls
        it every tick before its branches."""
        self.actions = actions
        self._ended_now, self._observed = None, True
        self.kit.observe(world, actions)
        self.kit.read_buildings(world)
        g = self.current
        if g is None:
            return
        top = actions.history[-1] if actions.history else None
        if top is not (g.last if g.last is not None else g.mark):
            g.end("superseded", top.type)
        elif self.hold_ticks >= GOAL_HOLD_SUPERSEDE_TICKS:
            g.end("superseded", "hold")
        elif self.clock() - g.started_wall > g.budget():
            g.end("failed", "goal budget")
        if not g.running:
            self._close(g)

    def tick(self, world, actions, view=None):
        """The goal's command this tick, or None (the module docstring)."""
        if not self._observed:
            self.observe(world, actions)
        self._observed = False
        ended = self.history[-1] if self._ended_now is not None else None
        proposed, refused = None, None
        g = self.current
        if g is not None:
            g.observe(world, actions, self.clock)
            if not g.running:
                self._close(g)
                ended = self.history[-1]
        if self.current is None:
            g = self.source.propose(view() if callable(view) else (view if view is not None else {}))
            self.pending = g is None
            if g is not None and self.cooled.get(goal_key(g.TYPE, g.args()), 0.0) > self.clock():
                refused, g = {"type": g.TYPE, "args": g.args()}, None
            if g is None:
                self.why = {"proposed": None, "refused": refused, "ended": ended, "pending": self.pending}
                return None
            proposed = g.TYPE
            g.started_wall, g.kit = self.clock(), self.kit   # the budget starts here, never while pending
            g.mark = actions.history[-1] if actions.history else None
            self.current, self.hold_ticks = g, 0
        cmd = g.step(world, actions, self.clock)
        if not g.running:
            self._close(g)
            cmd = None
        self.why = dict(g.why, goal=g.TYPE, args=g.args(), state=g.state, reason=g.reason, proposed=proposed,
                        ended=ended)
        return cmd

    def held(self, by_other):
        """Survive's report at the end of each tick: `by_other` when a branch other than the goal answered with no
        command (a hold that sends nothing). Counts the ticks in a row while a goal runs (M-7)."""
        self.hold_ticks = self.hold_ticks + 1 if by_other and self.current is not None else 0

    def send(self, cmd):
        action = self.actions.send(cmd)
        if self.current is not None:
            self.current.sent(cmd, action)
        return action

    def rows(self):
        """loop.goals: every goal that ended (copies of `history`), then the running one with endS None."""
        rows = [dict(r) for r in self.history]
        g = self.current
        if g is not None:
            rows.append(dict(g.row(), startS=self._s(g.started_wall), endS=None, source=self._name()))
        return rows

    def line(self):
        g = self.current or self._ended_now
        if g is None:
            return {"pending": self._name()} if self.pending else None
        return {"type": g.TYPE, "args": g.args(), "state": g.state, "source": self._name()}
