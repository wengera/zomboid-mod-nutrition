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
  first: `weapon`, OPTIONAL_FIELDS, an explicit null read as absent; the scripted source never names one, and `args()`
  leaves an unset want out, so its rows read as before; a `bag` want is not offered until the Lua lane lands a bag
  loot filter and `LOOT_WANTS` takes it): the want's loot use (`WANT_USES`: `weapon`, the use `items.WEAPON_RX`
  reads) goes first after the kit's wants, and the goal ends `done "want met"` once the held items of the want
  (`held_of`: `world.by_use()`'s) number more than at its start, so a want already held asks for one more; with none to take there
  the loot goes on in the default order.
- `Shelter(building)`: Night's shelter machine for a named building (`night.shelter_plan`, `shelter_step`,
  `shelter_ended`, never re-implemented): approach the exterior door, open it, step in, close it (a step's walk failed
  `stuck` at a hoppable edge climbs it first, as `ExploreToward` does, and walks again; a climb that fails is read as
  that walk's stuck end, the machine's next door or shun); `done "inside"` once the plan reads done, `failed "no
  plan"` with no exterior door or room on the player's floor, `failed "shun"` when the machine shuns the building; both shun the building in the kit's `shunned` for `night.SHUN_MIN` game
  minutes (fix 1, I3) on `World.world_minutes()` (monotonic across midnight: fix wave P, I-1); a building already
  shunned there ends the goal `failed "shunned"` at its start, before any plan or walk, its stamp untouched (ruling
  P25-G); the store
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
them over, and a cooled goal a source still proposes is refused for that tick (`why.refused`), no row written. A goal
whose leg failed for good (`_Legs`: `no path`, `stuck` with no fence, `no square` at LEG_MIN) is cooled too though it
sent, and ExploreToward marks its far target stuck (Task 21 fix 1). A goal that failed for a
shun (COOL_REASONS: `shun`, `shunned`, `no plan`, `no door`; ruling P25-G, Plan 25 Task 7, F4's 57 Shelters failed
`shun` within 1.5 s, each after a walk) is cooled whatever it sent.
`send(cmd)` sends the
goal's command and hands the `Action` to the goal (Survive sends through it, as the owner). `line()` is the
decision log's `goal` field: `{type, args, state, source}` of the running goal, or of the one that ended this tick,
else `{"pending": <source NAME>}` while the source is pending, else None.
"""
import json
import math
import os

from agent.base.items import holds_use
from agent.base.planner.night import door_blocked
from agent.base.planner.policies import CLOTHING_HELD_N, LOOT_WANTS, me_floor, me_xy

GOAL_MAX_S = 90.0     # wall seconds a goal may run before it is failed "goal budget" and replaced (a Rest: P23-W)
GOAL_COOL_S = 30.0    # wall seconds a goal that failed having sent nothing is not taken again (fix 1, I4)
COOL_REASONS = ("shun", "shunned", "no plan", "no door")   # a goal failed for one of these is cooled whatever it sent
                      # (ruling P25-G: F4's Shelter of a shunned building re-proposed 67 times, each after a walk)
GOAL_HOLD_SUPERSEDE_TICKS = 20   # planner ticks another branch holds without sending before the goal is superseded
ARRIVE_R = 1.5        # tiles: an ExploreToward whose place is scanned is done within this of its point
REST_S = 30.0         # the scripted source's rest
STOCK_WANTS = ("water", "container", "clothing", "food", "bandage", "weapon")   # LootBuilding's order of uses (P24-Y)
CONTAINERS_HELD_N = 2   # vessels held (`water` and `container`) at which `container` is no longer wanted (Task 18 fix
                        # 1, the review's major 5, its number: one or two held, so the cap goes to the food)
SMASH_MIN_HEALTH = 60.0   # health at or above which a window may be smashed (a smash is noise and, 1 time in 2, a glass cut:
                      # review-t9-fix9 ruling 6, "health above the bandage threshold"; a judgment, survive's pair-flee line)
SMASH_ZOMBIE_R = 25.0   # tiles: a smash waits while a zombie is listed this near (the noise carries: the view's widest band)
WINDOW_DEAD = ("not a window", "not valid", "fell", "failed", "no square", "stalled")   # a window action's ends that
                      # leave the window out for DOOR_RETRY_MIN game minutes (World.note_window_fail); `locked` is read
                      # apart; `stalled` (the Flee's climb dropped for its hold, ruling P26-J2) is a mark, not an end
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
WANT_USES = {"weapon": "weapon"}   # a LootBuilding want's loot use (Task 29; a bag want waits for a PZA bag loot filter)
OPTIONAL_FIELDS = {"LootBuilding": ("want",)}    # schema fields a goal may leave out (None, left out of args())
EXAMPLES = {"ExploreToward": {"x": 120, "y": 205}, "LootBuilding": {"building": 3}, "Shelter": {"building": 3},
            "Stock": {"kind": "water"}, "Rest": {"seconds": 30.0}}

__all__ = ["Goal", "ExploreToward", "LootBuilding", "Shelter", "Stock", "Rest", "GoalSource", "ScriptedSource",
           "GoalRunner", "Kit", "validate", "open_uses", "int_id", "goal_key", "GOAL_MAX_S", "GOAL_COOL_S",
           "GOAL_HOLD_SUPERSEDE_TICKS", "COOL_REASONS",
           "ARRIVE_R", "REST_S", "STOCK_WANTS", "BUILDING_R", "WOODS_R", "WINDOW_REPEAT", "CONTAINERS_HELD_N",
           "CLOTHING_HELD_N", "SMASH_MIN_HEALTH", "SMASH_ZOMBIE_R", "smash_ok", "window_pick",
           "usable_windows", "note_window_end", "REST_N", "WOODS_STEP",
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
    """How many held items answer a LootBuilding `want` (Task 29): the want's use in `world.by_use()`."""
    return len(world.by_use().get(WANT_USES.get(want) or want, ()))


def looted(world, building, loot=None, wants=(), waiting=None, keys=None):
    """Whether `building` is looted (Plan 25 Task 4, spec 2.2(a): the one rule the view's `L` flag and
    LootBuilding's `nothing to loot` both read): a container is known on it (one with none known reads false,
    unsearched ground being lootable: Plan 24 Task 3 fix 1, M1) and no container of it holds a use a loot would take
    now, a use of `wanted_uses(world, wants)` that `open_uses` answers there (not marked looted for it,
    not waiting on the cap: `loot`'s, unless `waiting` {use: keys} is given). So a building whose containers hold
    only uses no longer wanted (clothing past CLOTHING_HELD_N spare garments, a vessel past CONTAINERS_HELD_N) reads
    looted, as every container read looted does: F3's building 2 read `open_uses`, every LOOT_WANTS use, and never
    turned looted through twelve failed loots. `keys` the building's container keys when the caller holds them."""
    if keys is None:
        keys = [k for k in world.containers if (world.map.get(k[:3]) or {}).get("building") == building]
    if not keys:
        return False
    uses = set(wanted_uses(world, wants))
    return not any(uses.intersection(open_uses(world, loot, k, waiting)) for k in keys)


def _usable_building(world, b, shunned):
    """Whether building `b` is one the view would send a loot to (review-t24 minor 5): not shunned, its exterior doors
    not all marked stuck (the window route is left out: it would recurse into `smash_ok`), and not looted out
    (`looted`, the view's `L`: a building with containers known and no use a loot would still take at any is; one with
    none known is not)."""
    if b in shunned or door_blocked(world, b, me_floor(world)):
        return False
    return not looted(world, b)


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


def usable_windows(world, building, z):
    """`[(sq, locked)]`, the building's windows on floor `z` a window try may take (ruling P26-7c, one filter for
    `window_pick` and `night.window_exits`): not barricaded and not left out by a failed end (`WINDOW_DEAD`),
    `locked` True for a record read locked or a try that ended `locked`; the order of `World.windows`."""
    out = []
    for sq in world.windows(building):
        rec = (world.map.get(sq) or {}).get("window") or {}
        fail = world.window_fail(sq)
        if sq[2] != z or rec.get("barricaded") is True or fail in WINDOW_DEAD:
            continue
        out.append((sq, rec.get("locked") is True or fail == "locked"))
    return out


def note_window_end(world, sq, action):
    """The reason a window action's failed end `action` at square `sq` is noted under (`World.note_window_fail`) and
    returned (ruling P26-7c, one failure leg for the goal layer's `_window_ended` and the Flee's): the end's reason,
    else its state; review-t24 major 2: a smash try refused `locked` (a barricade or a frame a smash cannot cure), a
    second `locked`, or a second `WINDOW_REPEAT` end within DOOR_RETRY_MIN leaves the window out for good (`failed`).
    A `locked` end of an unsmashed try is noted `locked` (the next `usable_windows` reads the window locked, and
    smashed)."""
    reason = action.reason or action.state
    prior = world.window_fail(sq)
    if reason == "locked" and (action.args.get("smash") is True or prior == "locked"):
        reason = "failed"
    elif reason in WINDOW_REPEAT and prior == reason:
        reason = "failed"
    world.note_window_fail(sq, reason)
    return reason


def window_pick(world, building, shunned=()):
    """`(x, y, z, smash)` of the building's window to try, else None (Task 24, the route past a stuck door): the
    build announces `window`; windows on the player's floor not barricaded and not left out by a failed end
    (`usable_windows`); an open one first, then a shut unlocked one (opened, then climbed: no noise), then a locked
    one (the record's `locked`, or a try that ended `locked`) only when `smash_ok`, with `smash` true; each nearest
    the player."""
    if not world.can("window"):
        return None
    z = me_floor(world)
    mx, my = me_xy(world)
    smash = None   # smash_ok's answer, read at most once and only for a locked window
    best = None
    for sq, locked in usable_windows(world, building, z):
        rec = (world.map.get(sq) or {}).get("window") or {}
        if locked:
            smash = smash_ok(world, building, shunned) if smash is None else smash
            if not smash:
                continue
        rank = (locked, rec.get("open") is not True, math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my), sq)
        if best is None or rank < best[0]:
            best = (rank, sq, locked)
    return None if best is None else (best[1][0], best[1][1], best[1][2], best[2])


# the names Plan 25 Task 2 moved to `goal_policies.py` and `goal_runner.py`, by the module that holds each
_MOVED = {"goal_policies": ("Kit", "Goal", "_Climbing", "leg_max", "_Legs", "ExploreToward", "_Looting", "LootBuilding",
                            "Shelter", "Stock", "Rest", "TYPES"),
          "goal_runner": ("_SCHEMA", "_entries", "_JSON_TYPES", "_field", "validate", "GoalSource", "_nearest_first",
                          "ScriptedSource", "GoalRunner")}


def __getattr__(name):
    """The goals, the runner and the sources by their old module (Plan 25 Task 2 moved them to
    `planner/goal_policies.py` and `planner/goal_runner.py`): the frozen drivers (`e_day*.py`, `f_goals*.py`, never
    edited after their runs) import `ScriptedSource` from here, as do `llm.py` and the tests; the live planner modules
    import each name from its home (Plan 25 Task 3, review-t2's minor 3). Read at the access, so neither module is
    imported while this one loads (both import it)."""
    for mod, names in _MOVED.items():
        if name in names:
            m = __import__("agent.base.planner." + mod, fromlist=[name])
            return getattr(m, name)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
