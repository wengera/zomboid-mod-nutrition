"""The scripted survivor (Plan 22 Task 10, spec § 3): a priority list over the World, ticked by its driver.

`Survive(world, actions, log_path, clock, source=None).tick(world, actions)` tries the branches in order (threat,
need, load, night, goal; Plan 23 Task 12 added `load` and `night`, Task 13 replaced `forage` and `explore` with the
goal), takes the first that answers, and returns the `Action` it sent or None. A branch
answers with a command to send or, while its own action is still current, with none (it holds: nothing is sent and
no lower branch runs). A branch whose answer differs from the current action's sender sends at once, so a higher
branch pre-empts a lower one's action (the Lua fails the old one `superseded`). The branches run the policies of
`policies.py`; `need` is one `Consume`. Every tick appends one JSON line to `log_path` (decision.log): `{wall,
gameMin, branch, inputs, action, sent, goal}`, sorted keys, `wall` from the injected clock, `action` the command's
`type` and `args` or null, `goal` the goal runner's `{type, args, state, source}` (the running goal, or the one that
ended this tick; null when none), so a replayed session reproduces its decisions byte for byte.

The thresholds and the threat hysteresis are Plan 21b's (`testing/agent/policy.py`'s docstring, frozen; ported):
- A zombie is a threat within DANGER_R; while a threat policy runs (the "mode", `fight` or `flee`, kept while the
  threat branch answers), the branch holds every zombie within DISENGAGE_R: a threat engaged at 6 tiles holds the
  branch until it is beyond 10 or dead, so the bot never turns its back to loot. DISENGAGE_R is also the radius at
  which the Fight drops its pinned target (`policies.Fight`, Plan 23 Task 10), so it lives in `policies.py`.
- The hold-radius fix (`docs/reference/research-notes.md`, "The hold radius widens the 'too many' count"; the Plan
  21b ledger's ruling): `pair` counts the zombies within DANGER_R only; `held`, which keeps a flee running, reads the
  held list, being the hold itself. `many` (ruling P23-AG 2, the chain's E1: a fight engaged with one zombie fled only
  once four were within 6, and died) counts the held list while a fight runs and the DANGER_R count otherwise, so a
  fight engaged at 5 tiles with two more zombies closing from 8 and 9 turns to a flee before they are within 6.
- Fight or flee: flee when unarmed (`world.weapon` is None), when the `many` count > MAX_FIGHT, when health <
  FLEE_HEALTH, or when that count >= 2 and either health < FLEE_HEALTH_PAIR or the body carries a wound (the frame's
  `body.bleeding + scratched + bitten` > 0, a missing count read 0; Plan 23 Task 10: a wounded player does not take
  on a pair at any health), the reason `pair`. A running flee turns back to fight only with
  one held threat and health >= FLEE_HEALTH + REFIGHT_MARGIN, and a flee sent because a fight stalled is held while
  the nearest stays beyond FIGHT_REACH; a running fight turns to flee only on the flee conditions or its stall
  (`Fight.stalled`: its target beyond FIGHT_REACH for more than FIGHT_MAX_S unbroken seconds), never because a
  threat count dropped; the stall guard reads the distance to the Fight's target (`Fight.target_dist()`, the pinned
  one), the zombie its stall clock follows, never the nearest held one (Task 10's review M3). The flee steers from
  the held threats (`policies.Flee`: every leg away from each by 1/distance, turned off a known edge and off a
  held group ahead).
- The flee to shelter (ruling P23-AG 1, fix round 1): each flee episode's `Flee` takes the night's shun store and, at
  its first choose, a known building's exterior door within `policies.SHELTER_FLEE_R` with no zombie in its corridor
  and none inside the building; it then runs the night's shelter steps at a run, a failed step falling back to the
  steer (`policies.Flee`). While those steps run (the close not yet ended) the inside hold below waits, since the
  character stands inside with the door still open. Once the close ended inside (`sheltered`: the Flee's plan done
  and the character inside) the inside hold applies; when it does not (a line clears), an armed character fights only
  the reachable held threats standing in the building's doorway or inside it (`policies.in_building`; the Fight's
  `only`), whatever the flee reason (`many` and `health` included: a doorway kill beats running out into the group),
  and with none there the Flee answers (reason `sheltered` when no other holds): it holds while every threat reads
  line-blocked, re-closes an open door, else falls back to the steer. The sheltered Flee is kept across the door
  fight, so after the doorway kill it re-sends the close; both log `sheltered`.
- The flee's load drop (Plan 23 Task 10): run 2's last flee was pinned at load level 4. While the mode is `flee` and
  the frame's load level is at or above `policies.DROP_AT` (3), the flee episode's first free answer is one `Drop` of
  `LootHouse.spare()` (logged `flee_drop`, the item's id), sent as the Flee's own action so its steer waits on the
  drop (the drop skill is quick) and follows on the next tick; at most one drop per episode (`flee_dropped`, reset when
  the mode leaves `flee`), none when nothing is spare.
- Unreachable (the whole-pass review's I2): a target whose STALL_SWINGS started swings took no health, or whose line
  stays blocked after the Fight's one reposition (or has no clear square to reposition to), is skipped for
  UNREACHABLE_S (`policies.Fight`); Survive keeps that memory in `unreachable` across its Fights, and when every held
  threat is skipped the branch flees (reason `unreachable`), never attacking it again until its time runs out.
- Held inside (fix wave P, M-6): when the character is `inside()` (the night's read: a room square) and every held
  threat's line reads blocked (`policies.line_to` False: both end squares mapped, a wall, closed door or intact window
  between), the branch holds with no command (logged `flee: held_inside`) instead of fighting or fleeing out of its
  shelter; the hold ends when a threat's line clears or reads unknown, or the character is not inside.
- Survival 2 (ruling P23-AJ, the chain's E2: it died at game minute 592 inside building 3, the hold standing while a
  zombie closed from 5.78 to 3.05 tiles behind a wall the map read, then nine sprint steers pinned against its own
  room's walls, the bat never swung). `_threat_plan` makes the branch's one decision from the inputs (cornered, hold,
  door fight, broken hold, sheltered, Plan 21b's hysteresis; its docstring is the order), the Fight and the Flee only
  executing it:
  1. Every hold breaks (`_breach`, logged `breach`) with a held threat within HOLD_BREAK_R (3.0) whatever its line
     reads (`near`), or once the nearest held threat has read nearer than the tick before on CLOSING_TICKS (3)
     consecutive ticks within DANGER_R (`closing`: a threat coming through an opening the map does not show). That is
     the M-6 hold and the sheltered Flee's (its `hold_ok`). A broken hold flees when a way out of the building is
     known (`policies.exit_plan`: the Flee walks out, rule 3), else fights with one or two held and one reachable,
     else flees.
  2. Cornered (`_cornered`, logged `cornered`: the zombie id): armed, the nearest held threat within CORNERED_R (1.5)
     and either the flee's last steer leg ended stuck or the character on a room square (fix round 1: at melee range
     inside, the fight comes before any walk out), the Fight runs on the nearest reachable held threat whatever the
     count (MAX_FIGHT aside) or the flee reason, keeping its pin and stall and its line check beyond POINT_BLANK_R
     (1.0; within it the swing goes whatever the map's line says); it ends when that zombie is dead, gone or marked
     unreachable, or the nearest held threat is beyond CORNERED_R (a corner taken on a room square) or CORNER_FREE_R
     (5.0, a stuck leg's), and the next flee is a fresh Flee whose first leg is not stuck.
  3. Inside a building the flee walks out (`policies.Flee`'s way out, `night.exits`: the building's openings and its
     closed exterior doors; fix round 1: the nearest whose straight line passes no held threat within 1.5 tiles);
     with none it adopts the building (the sheltered hold, the re-close, the door fight), else, armed, fights the
     nearest (`_trapped_fight`), else holds (an unarmed character inside with no way out stands: the review's M4):
     on a room square it never steers. No window's edge is a way out; a walk out that stops moving for 1 s is
     dropped, and the corner pre-empts a running walk at melee range. While a walk out runs the inside hold waits,
     as for the shelter steps. The door fight stays for a sheltered building, ahead of the corner.
- Survival 3 (ruling P23-AM, the chain's E3: it died at game minute 600 after a fight and a `many` shelter flee
  superseded each other four times in 8 s, then the shelter's enter walk stood while a group of six closed):
  1. A flee started under a group stays a flee (`flee_many`, the episode's reason once `many`; `_many`): while it
     runs, `many` reads the hold radius's count over MAX_FIGHT or the nearest held threat within DANGER_R, so the
     fight resumes only with at most MAX_FIGHT held, the nearest beyond DANGER_R, and the `held` and refight rules
     above passed. A flee the hysteresis would end is kept (`_kept_flee`) while a `many` episode's shelter steps or
     way out run (`steps`: their end is the flee's), and while the Flee's own walk or steer leg sent under FLIP_MIN_S
     (5 s) ago runs and the Fight would walk (`flip`); a flee is never held back for a fight's walk (the retreat wins
     the tie).
  2. A shelter step's walk that stands STEP_STALL_S with a held threat within DANGER_R is dropped (`policies.Flee`,
     `ended` `stalled`): the plan for the episode, the steer at once.
  3. A `many` flee beyond SPRINT_R steers and walks its shelter steps at a sprint while the frame's endurance reads
     above SPRINT_END (`Flee.many`, `policies.Flee._group_sprint`).
  4. GROUP_R_N (3) or more held within CORNERED_R after a steer leg that moved are steered from, not cornered
     (`group_steer`, `Flee.steer_now`, on a room square too); after a stuck leg, or against one or two, the corner
     stands.
  The coordinator's amendments (E3's write-up): 5, an exterior door is one whose own edge joins a room square to an
  outside square (`World.door_way`, `night.exterior_doors`), the approach square that outside square; 6, the corner
  is judged on every threat tick whatever runs (`_cornered`'s `walk` corner: a line not read blocked, no mark; a
  running fight keeps its pin), so a shelter or exit walk at melee range is superseded by the corner's attack, or,
  with three or more within CORNERED_R and no stuck leg, by rule 4's steer (`Flee.give_way` drops the walk); rule 4
  then reads "not stuck" for "a leg that moved", a walk having no leg.
- Survival 4 (ruling P23-AP, the chain's E4: it died at game minute 627 after a `walk` corner on one or two zombies
  held 35 ticks while the group formed outside 1.5 tiles, and a steer leg aimed before two zombies ahead were listed
  ran into them; twelve walks from one stuck square cost 21.85 game minutes before):
  1. The goal source leaves a stuck area (`world.unexplored_edge` after two unmoved stuck walks from the player's
     square: only a square in the open, else a loot or the scan; `goals.py`'s docstring).
  2. A corner ends for a closing group (`_group`): GROUP_HOLD_N (4) held, or GROUP_R_N (3) within GROUP_NEAR_R (3.0
     tiles), whichever first, ends a `walk` or `inside` corner and blocks a new one while the last leg is not stuck
     (the group steer, logged `group`); a `stuck` corner keeps swinging, but with the nearest beyond POINT_BLANK_R
     and its stuck read STUCK_RETRY_S (2 s) old one steer leg is tried (`group` "retry").
  3. A running steer leg is cut and re-aimed when a held threat comes ahead of it (`policies.Flee._cut_leg`).
- `need` (Plan 23 Task 11, P23-7): Plan 22's character never ate or drank, its thresholds 0.5, which vanilla reaches
  in 17 to 20 game hours; the needs now fire at the game's first moodle, THIRST_T 0.12 (#0509) and HUNGER_T 0.15
  (#0508). While its own `Consume` is current the branch holds, before any threshold is read (a frame that already
  reads the drink's effect must not let a lower branch supersede it); while the night's `Sleep` is current (sent,
  accepted or in progress) the branch sends nothing and passes, logged `holding_sleep` (ruling P23-AB: the night's own
  hold then answers the tick, and the needs are answered at the wake; the threat above still pre-empts the sleep);
  else thirst > THIRST_T consumes the held item of least id whose use is `water` (`world.by_use()`: the dataset's
  drinkable, non-poisonous fluid containers, an id marked empty left out), else marks `water`; then hunger >
  HUNGER_T consumes the held `food` item of least `items.days_fresh` (the most perishable first, the spec's "smallest
  spoil risk"; a food with none last; ties by least id: fix wave P, I-4), a sealed can (`cant_eat`) never being food
  and a refused id left out, else marks `food`; nothing held, the branch passes (to the goal). Each mark is also kept in
  `need_marks` {use: wall of its last mark} (both uses, where `need_mark` logs the first), which the view reads as
  `needs_wanted` for `view.NEED_MEMORY_S`; a held item of the use found clears its mark.
- The empties (P23-D): a `Consume` whose action ended `failed "not valid"` on an id `by_use()` reads `water` marks it
  empty (`world.mark_empty`), so the next tick takes the next bottle and `spare()` may drop it; on an id it reads
  `food` marks it refused (`world.mark_refused`, fix wave P I-4, P23-AD: `by_use` then reads it `other` for
  `world.REFUSED_TTL_MIN` world minutes, so the need does not retry it meanwhile and takes the next food), logged as
  inputs.consume_refused on the tick that read the end (else None), as is any other id refused so (one no longer
  held when the end was read), which is never marked.
- `goal` (Plan 23 Task 13, P23-10; ruling P23-F): `goals.GoalRunner` over the goal source (`source`, default
  `goals.ScriptedSource()`; Task 14's LLM source shares the seam), whose module docstring is the design record: one
  goal at a time, proposed from `view.view(world, self)` (built only on a tick that proposes) when none runs,
  `superseded` when an instinct sent since its own last action, failed at `goals.GOAL_MAX_S`. The old `forage`
  (P23-8: a loot for one use, never `all`, with `maxWeight` = the frame's `load.max` times
  `policies.LOAD_RATIO_MAX`, the level guard the backstop, spec § 9 (1)) and `explore` (scan each new place, walk to
  the unexplored edge) are now the `Stock`, `LootBuilding` and `ExploreToward` goals' steps over the same
  `LootHouse` and `Explore` (`policies.py`). A running goal holds the branch (no command while its action runs, or
  while it rests); with no goal running it passes. Its `why` is the goal's own plus `goal`, `args`, `state`,
  `reason`, `proposed` (the type proposed this tick, else None) and `ended` (the record row of a goal that ended
  before the proposal, else None).
- A command whose action ended `failed` (any reason but `superseded`, which this planner's own next send caused),
  `timeout` or `rejected` is not chosen again with the same type and args for FAILED_COOLDOWN_TICKS planner ticks:
  its branch is passed over and the next one tried (logged as inputs.cooled); the threat branch is never passed
  over. Every branch tried logs its own inputs under inputs.branches[<branch>].
- `load` (Plan 23 Task 12, split out of `LootHouse`): at load level `policies.DROP_AT` (3) or above it sends one
  `Drop` of `policies.spare(world)` a decision (logged `level`, `drop`), holding while that drop is current, until the
  frame's level reads `DROP_TO` (2); with nothing spare, or under DROP_AT, it passes. It runs before `night`, so a
  heavy load is dropped before the sleep; while the night's `Sleep` is current it passes as the need does (P23-AB).
- `night` (Plan 23 Task 12, P23-9): `night.Night` (its docstring is the design record). Its own running action holds
  first, before the want is read (a sleep is never superseded by its fatigue falling under the want); not wanting, it
  passes (logged `{"wants": false}`); wanting (counted in `night.wants_n`), it shelters in a known interior and
  sleeps, holds NOT_SAFE_S after a sleep refused `not safe` and NOT_VALID_S after `not valid`, stops wanting for the
  session after `not allowed` (ruling P23-U), and with no shelter known sets `night.want_shelter` and passes. Its
  `why` carries `step`, `building`, `shunned` and the sent action's `aid`.
- `last_branch` (Plan 23 Task 16c) is the branch of the last decision line (None when no branch answered), so a
  driver's action rows name the branch that sent each action without re-reading the log.
- Each tick ends by telling the goal runner whether a branch other than the goal answered without sending
  (`GoalRunner.held`), so a goal an instinct holds without a send is superseded `hold` (fix wave P, M-7).
- The log's inputs carry `mode` (the running threat policy at the tick's start, else None), `threats` (the DANGER_R
  count), `held` (the count within the hold radius), `fight_s` (the running fight's stall clock read before this
  tick restarts it, else None), and the frame's `fatigue` and `hour` (the night's inputs).
"""
import json
import math
import time

from agent.base.items import days_fresh
from agent.base.planner.goals import GoalRunner, ScriptedSource
from agent.base.planner.night import Night
from agent.base.planner.policies import (CORNERED_R, DANGER_R, DISENGAGE_R, DROP_AT, FIGHT_MAX_S, FIGHT_REACH,
                                         POINT_BLANK_R, PREEMPTED, Fight, Flee, adoptable, blocked, exit_plan,
                                         in_building, in_reach, item_id_ok, line_to, spare, target_id_ok, zdist)
from agent.base.planner.view import view
from agent.base.pza1 import Consume, Drop

THIRST_T = 0.12          # the first THIRST moodle fires above 0.12 [#0509]
HUNGER_T = 0.15          # the first HUNGRY moodle fires above 0.15 [#0508]
FLEE_HEALTH = 40.0        # under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
REFIGHT_MARGIN = 20.0     # a running flee turns to fight only at health >= FLEE_HEALTH + this, one threat
MAX_FIGHT = 2             # more threats than this are fled
HOLD_BREAK_R = 3.0        # tiles: a held threat this near breaks every hold whatever its line reads (P23-AJ 1)
CLOSING_TICKS = 3         # ... as does the nearest held threat closing on this many ticks in a row within DANGER_R
CORNER_FREE_R = DISENGAGE_R / 2   # tiles: a cornered Fight ends once the nearest held threat is beyond this
FLIP_MIN_S = 5.0          # wall seconds a flee walk runs before a fight's walk may supersede it (P23-AM 1)
GROUP_R_N = 3             # zombies within GROUP_NEAR_R that make a group: steered from, not cornered (P23-AM 4, AP 2)
GROUP_NEAR_R = 3.0        # tiles: ... (P23-AP 2: a third zombie this near; P23-AM 4 read 1.5, CORNERED_R)
GROUP_HOLD_N = 4          # held threats (within the hold radius) that make a group too (P23-AP 2)
STUCK_RETRY_S = 2.0       # wall seconds after a stuck read before a stuck corner against a group tries a leg (P23-AP 2)
BRANCHES = ("threat", "need", "load", "night", "goal")
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed command is not chosen again with the same type and args
FAILED = ("failed", "timeout", "rejected")
REFUSED = "not valid"    # the reason the Lua's consume fails an item it cannot eat or drink (an empty bottle)

__all__ = ["Survive", "BRANCHES", "DANGER_R", "DISENGAGE_R", "THIRST_T", "HUNGER_T", "FLEE_HEALTH",
           "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "FIGHT_MAX_S", "FIGHT_REACH", "FAILED_COOLDOWN_TICKS",
           "HOLD_BREAK_R", "CLOSING_TICKS", "CORNERED_R", "CORNER_FREE_R", "FLIP_MIN_S", "GROUP_R_N", "GROUP_NEAR_R",
           "GROUP_HOLD_N", "STUCK_RETRY_S"]


def _key(typ, args):
    return typ, json.dumps(args, sort_keys=True)


class Survive:
    def __init__(self, world, actions, log_path, clock=time.time, source=None):
        self.world = world
        self.actions = actions
        self.log_path = log_path
        self.clock = clock
        self.mode = None          # the running threat policy: "fight", "flee" or None
        self.fight = None
        self.flee = None
        self.stall_flee = False   # the running flee was chosen because a fight stalled
        self.flee_dropped = False  # the running flee episode sent its one load drop
        self.flee_many = False    # the running flee episode's reason was `many` (P23-AM 1: it stays a flee)
        self.group_steer = None   # this tick: why a group at melee range is steered from, not cornered (`_group`:
                                  # "near" or "hold", P23-AM 4 and AP 2; "retry", a stuck corner's leg), else None
        self.sheltered = False    # a flee's shelter plan ended inside: a threat whose line clears is fought (P23-AG)
        self.door = None          # the door fight's targets this tick (`_door_targets`) while sheltered, else None
        self.broken = None        # the breach that broke a due hold this tick (P23-AJ 1), else None
        self.closing = (0, None)  # (ticks the nearest held threat has closed within DANGER_R, its last distance)
        self.cornered = None      # the zombie id a cornered Fight runs on (P23-AJ 2), else None
        self.corner_free = CORNER_FREE_R   # tiles: the nearest beyond this ends the corner (fix round 1)
        self.corner_kind = None   # "stuck", "inside" or "walk" (amendment 6: taken on any walk), the running corner's
        self.stuck_wall = None    # wall of the stuck read a `stuck` corner was taken on (P23-AP 2: STUCK_RETRY_S)
        self._corner_fight = None   # the Fight made for the corner
        self.unreachable = {}     # zombie id -> wall until it is skipped (policies.Fight), kept across Fights
        self.night = Night(world, actions, clock)
        # one shun store: the goals' Shelter shuns into the night's (Task 13 fix 1, M6), so neither re-tries the other's
        self.goals = GoalRunner(ScriptedSource() if source is None else source, clock, shunned=self.night.shunned)
        self.goals.kit.bind(world, actions)
        self.need_last = None     # the last Consume sent
        self.load_last = None     # the last load Drop sent
        self.need_mark = None     # "water" or "food" when need found nothing held this tick (logged)
        self.need_marks = {}      # use -> wall of its last mark: the view's needs_wanted
        self.consume_refused = None   # a non-water id whose consume ended failed "not valid" this tick (logged)
        self.ticks = 0
        self.last_failed = None   # (type, args json, tick first seen failed) of the last command that failed
        self._watch = []          # actions sent and not yet seen terminal
        self.why = {}
        self.last_branch = None   # the branch of the last decision line (a driver's action rows read it at the send)

    # ---------------------------------------------------------------- reading the world
    def _policies(self):
        return [p for p in (self.night, self.fight, self.flee) if p is not None]

    def _within(self, r):
        return [z for z in self.world.zombies.values()
                if z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= r]

    def _hold_r(self):
        return DISENGAGE_R if self.mode is not None else DANGER_R

    def _health(self):
        h = (self.world.body or {}).get("health")
        return 100.0 if h is None else h

    def _wounds(self):
        """The body's bleeding, scratched and bitten counts summed (a missing count reads 0)."""
        body = self.world.body or {}
        return sum(body.get(k) or 0 for k in ("bleeding", "scratched", "bitten"))

    def _armed(self):
        return self.world.weapon is not None

    def _held_use(self, use):
        """The id to consume among the held items of `use` (`world.by_use()`), else None: a food the least
        `days_fresh` first (None last), any use then the least id."""
        ids = [i for i in self.world.by_use()[use] if item_id_ok(i)]
        if not ids:
            return None
        if use != "food":
            return min(ids)

        def spoil(i):
            d = days_fresh((self.world.inventory.get(i) or {}).get("fullType"))
            return (math.inf if d is None else d), i
        return min(ids, key=spoil)

    def _sleeping(self):
        """The night's Sleep while it is the current action (sent, accepted or in progress), else None (P23-AB)."""
        a = self.night.last
        return a if a is not None and a.type == "sleep" and self.actions.current is a else None

    def _held_inside(self, held):
        """Every held threat line-blocked (`line_to` False) and the character inside (M-6)."""
        return bool(held) and self.night.inside() and all(line_to(self.world, z) is False for z in held)

    def _reachable_held(self):
        """(id, zombie) of each held threat a Fight can target and not marked unreachable (a nil-id zombie is a
        danger, never a target)."""
        skip = blocked(self.unreachable, self.clock())
        r = self._hold_r()
        return [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                and z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= r]

    def _many(self, held, n):
        """The `many` rule: the hold radius's count over MAX_FIGHT while a fight runs (P23-AG ruling 2), the DANGER_R
        count `n` over it while none does; and while a flee episode whose reason was `many` runs (P23-AM 1: E3's flee
        under a group ended the tick its count fell back to DANGER_R's, four times in 8 s), the hold radius's count
        over MAX_FIGHT or the nearest held threat within DANGER_R."""
        if self.mode == "flee" and self.flee_many:
            return len(held) > MAX_FIGHT or min(zdist(self.world, z) for z in held) <= DANGER_R
        return (len(held) if self.mode == "fight" else n) > MAX_FIGHT

    def _flee_reason(self, held, n):
        """Why the threat branch flees, by the hysteresis in the module docstring; None when it fights. `n` is the
        DANGER_R count (the `pair` rule's); `many` is `_many`."""
        health = self._health()
        if not self._armed():
            return "unarmed"
        if self._many(held, n):
            return "many"
        if health < FLEE_HEALTH:
            return "health"
        if n >= 2 and (health < FLEE_HEALTH_PAIR or self._wounds() > 0):
            return "pair"
        if not self._reachable_held():
            return "unreachable"
        near = min(zdist(self.world, z) for z in held)
        if self.mode == "flee":
            if self.stall_flee and near > FIGHT_REACH:
                return "stalled"
            if len(held) > 1 or health < FLEE_HEALTH + REFIGHT_MARGIN:
                return "held"
            return None
        if self.mode == "fight" and self.fight.stalled and (self.fight.target_dist() or 0.0) > FIGHT_REACH:
            return "stalled"   # the pinned target's distance: the one the stall clock follows (M3)
        return None

    # ---------------------------------------------------------------- the branches, in order
    # Each returns None (pass) or (policy or None, command or None): a None command holds the branch's running action.
    def _answer(self, policy):
        policy.observe()
        if policy.busy():
            self.why = dict(policy.why, holding=policy.last.aid)
            return policy, None
        cmd = policy.choose()
        self.why = dict(policy.why)
        return None if cmd is None else (policy, cmd)

    def _breach(self, held):
        """Why a hold breaks this tick (ruling P23-AJ 1), else None: `near` with a held threat within HOLD_BREAK_R
        whatever its line reads, `closing` once the nearest held threat has read nearer than at the tick before on
        CLOSING_TICKS consecutive ticks within DANGER_R (the first such reading counts one: 5.5, 5.0, 4.5 breaks at
        the third), a threat coming through an opening the map does not show. The count is kept every threat tick."""
        d = min(zdist(self.world, z) for z in held)
        n, last = self.closing
        n = (n + 1 if last is not None and d < last else 1) if d <= DANGER_R else 0
        self.closing = (n, d)
        if d <= HOLD_BREAK_R:
            return "near"
        return "closing" if n >= CLOSING_TICKS else None

    def _exit_known(self, held):
        """A way out of the building the character stands in (`policies.exit_plan`, P23-AJ 3): the flee's running
        one, or one not refused this episode."""
        f = self.flee
        if f is not None and f.exit is not None:
            return True
        return exit_plan(self.world, held, f.refused if f is not None else ()) is not None

    def _cornered(self, held, inside):
        """The zombie id a cornered Fight runs on (ruling P23-AJ 2, its fix rounds, and the coordinator's amendment 6
        to P23-AM), else None. Armed, with the nearest held threat within CORNERED_R, it corners (`corner_kind`):
        - `stuck`: the flee's last steer leg ended stuck (`Flee.stuck`: moved under STUCK_MOVE), or `inside`: the
          character stands on a room square (fix round 1: at melee range the branch fights before any walk out);
          on the nearest zombie `in_reach` (fix round 2, G4: within POINT_BLANK_R, or within CORNERED_R with its line
          not read blocked; its unreachable mark aside, I3);
        - `walk` (amendment 6, E3: lines 260-275 passed with a zombie within 1.5 tiles while the enter walk ran): on
          any other threat tick whatever runs (a shelter or exit walk, a steer leg, a goal walk the threat superseded),
          except while a fight runs (it keeps its own pin, Task 10), on the nearest zombie within CORNERED_R whose
          line is not read blocked and that is not marked unreachable (run 1's 103 swings at a zombie behind a locked
          door: these corners respect the marks, their Fight's `mark_free_r` 0).
        Rule 4 (P23-AM 4, as amendment 6 widens the corner, and survival 4's ruling P23-AP 2: E4's `walk` corner on
        one or two zombies held 35 ticks while the group formed outside 1.5 tiles, the held count rising from three to
        six): with a group (`_group`: GROUP_HOLD_N held, or GROUP_R_N within GROUP_NEAR_R) and the last leg not stuck,
        no corner, and a running corner not taken `stuck` ends (fix round 1, G1: E3's group came one at a time onto a
        `walk` corner): `group_steer`, the flee steers (sprints) while a leg can move, until one ends stuck. A
        `stuck` corner keeps swinging against the group, re-tested every tick: with the nearest beyond POINT_BLANK_R
        and its stuck read STUCK_RETRY_S old, it ends for one steer leg (`group_steer` "retry"; that leg read stuck in
        turn is a new `stuck` corner). Fix round 1: on a room square with no way out (`_trapped`, R3) no group is read:
        no leg can move there, so the corner stands at once; and the corner follows its Fight's re-pin to the nearest
        zombie within POINT_BLANK_R (R4, `policies.Fight`). It stays
        cornered on that id until the zombie is dead, gone, or marked unreachable and out of reach (a `walk` corner:
        marked at all), or the nearest held threat is beyond `corner_free`: CORNER_FREE_R for a stuck leg's corner,
        CORNERED_R for the others (a way out is never known at melee range, every exit's line starting within
        EXIT_CLEAR_R). The cornered Fight swings at a target within POINT_BLANK_R whatever its line reads
        (`Fight.point_blank`). A new corner makes a new Fight, superseding whatever ran; the next flee's Flee is a new
        one too, whose first leg is not stuck."""
        nearest = min(zdist(self.world, z) for z in held)
        if not self._armed():
            self.cornered = None
            return None
        skip = blocked(self.unreachable, self.clock())
        group = self._group(held)
        if group and self._trapped(held, inside):
            group = None   # fix round 1, R3: on a room square with no way out no leg can move: the corner stands
        if self.cornered is not None:
            if group and self.corner_kind != "stuck":   # fix round 1, G1: a group gathering on a corner is steered from
                self.cornered, self._corner_fight, self.group_steer = None, None, group
                return None
            if (group and nearest > POINT_BLANK_R and self.stuck_wall is not None
                    and self.clock() - self.stuck_wall >= STUCK_RETRY_S):   # P23-AP 2: a moved leg's chance
                self.cornered, self._corner_fight, self.group_steer = None, None, "retry"
                return None
            z = self.world.zombies.get(self.cornered)
            if (z is not None and z.get("x") is not None and z.get("y") is not None and nearest <= self.corner_free
                    and (self.cornered not in skip
                         or (self.corner_kind != "walk" and in_reach(self.world, z, CORNERED_R)))):
                return self.cornered
            self.cornered, self._corner_fight = None, None
            return None
        stuck = self.mode == "flee" and self.flee is not None and self.flee.stuck()
        if stuck or inside:   # I3, G4: marks aside, within 1.0 or a line not blocked
            reach = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid)
                     and in_reach(self.world, z, CORNERED_R)]
        elif self.mode == "fight":
            return None   # a running fight keeps its own pin (Task 10): the corner pre-empts walks, not swings
        else:   # amendment 6, on any walk: a line not read blocked and no mark (run 1's 103 swings at a locked door)
            reach = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                     and z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= CORNERED_R
                     and line_to(self.world, z) is not False]
        if nearest > CORNERED_R or not reach:
            return None
        if group and not stuck:
            self.group_steer = group   # P23-AM 4: against a group the branch steers (sprints) until a leg ends stuck
            return None
        self.corner_kind = "stuck" if stuck else ("inside" if inside else "walk")
        self.corner_free = CORNER_FREE_R if stuck else CORNERED_R
        self.stuck_wall = self.clock() if stuck else None
        self.cornered = min(reach, key=lambda p: (zdist(self.world, p[1]), repr(p[0])))[0]
        return self.cornered

    def _group(self, held):
        """Why the held threats are a group the branch steers from rather than corners (P23-AM 4, ruling P23-AP 2),
        else None: `hold` with GROUP_HOLD_N or more held (the hold radius's list), `near` with GROUP_R_N or more within
        GROUP_NEAR_R (a third zombie that near; iteration 3 read three within CORNERED_R, which this takes in)."""
        if len(held) >= GROUP_HOLD_N:
            return "hold"
        return "near" if sum(1 for z in held if zdist(self.world, z) <= GROUP_NEAR_R) >= GROUP_R_N else None

    def _threat_plan(self, held, breach):
        """The threat branch's one decision (ruling P23-AJ), `(kind, reason)`, the machines only executing it:
        - `door`: sheltered (a chosen shelter's plan done, the character inside) with a reachable held threat in its
          doorway or inside it: the door fight (I3). It goes first, before the corner and before the inside hold
          (a decision-order change from 21e3716b, which held first; ruled at fix round 1, the review's M1: a threat
          that opened the door or stands inside is the nearest danger, and its line may read blocked from another
          room).
        - `cornered`: `_cornered` names a zombie: a Fight on it whatever the held count or the flee reason (rule 2).
        - `hold`: the character inside, every held threat line-blocked (M-6, `held_inside`), no shelter or exit step
          running, and no breach (rule 1).
        - A broken hold (a breach while the inside hold, or the sheltered Flee's, would hold): `flee` when a way out is
          known (the Flee walks it: rule 3), else `fight` with one or two held and one reachable, else `flee`;
          `reason` the flee reason, else `broken`.
        - Sheltered with nobody in the doorway: `flee` (the sheltered Flee holds, re-closes or drops), reason
          `sheltered` when no other holds.
        - Otherwise Plan 21b's hysteresis (`_flee_reason`): `fight` when it reads None, else `flee`.
        - Fix round 1: a broken hold at a chosen shelter fights only in its doorway or inside (`door`, the review's
          I4); a `flee` on a room square with no way out and no adoption left is the Fight when armed
          (`_trapped_fight`, G3).
        Not a pure function: it sets `sheltered`, `door`, `broken` and `cornered` (`_breach` before it set `closing`),
        and a corner inside a chosen shelter drops the sheltered Flee, so the next flee walks out rather than
        re-closing."""
        inside = self.night.inside()
        self.sheltered = self.flee is not None and self.flee.sheltered and inside
        self.broken, self.group_steer = None, None
        self.door = self._door_targets() if self.sheltered else None
        if self.door:
            return "door", None
        if self._cornered(held, inside) is not None:
            return "cornered", None
        if self.group_steer:
            return "flee", self._flee_reason(held, len(self._within(DANGER_R))) or "many"
        steps = self.mode == "flee" and self.flee is not None and (self.flee.running_shelter()
                                                                   or self.flee.running_exit())
        held_inside = not steps and self._held_inside(held)
        if held_inside and breach is None:
            return "hold", "held_inside"
        reason = self._flee_reason(held, len(self._within(DANGER_R)))
        if breach is not None and (held_inside or (self.sheltered and self.flee.shelter_holds(held))):
            self.broken = breach
            if self._exit_known(held):
                return "flee", reason or "broken"
            if self._armed() and len(held) <= MAX_FIGHT and self._reachable_held():
                return ("door", None) if self.sheltered else ("fight", None)   # I4: a shelter's fight stays inside
            return self._trapped_fight(held, inside) or ("flee", reason or "broken")
        if self.sheltered:
            return "flee", reason or "sheltered"
        if reason is None:
            reason = self._kept_flee()
            if reason is None:
                return "fight", None
        return self._trapped_fight(held, inside) or ("flee", reason)

    def _kept_flee(self):
        """Why a running flee the hysteresis would end is kept (ruling P23-AM 1), else None: `steps` while a `many`
        episode's shelter plan or way out runs (its end, sheltered inside or walked out, is the flee's end), and
        `flip` while the Flee's own walk or steer leg sent under FLIP_MIN_S ago runs and the Fight would walk (the
        nearest reachable held threat beyond FIGHT_REACH): a fight's walk never supersedes it sooner. The other way
        the flee wins: a flee is never held back for a fight's walk (it is the retreat)."""
        f = self.flee
        if self.mode != "flee" or f is None:
            return None
        if self.flee_many and (f.running_shelter() or f.running_exit()):
            return "steps"
        a = f.last
        if a is None or a.type not in ("walkTo", "steer") or not f.busy() or self.clock() - a.sent_wall >= FLIP_MIN_S:
            return None
        reach = self._reachable_held()
        return "flip" if reach and min(zdist(self.world, z) for _, z in reach) > FIGHT_REACH else None

    def _trapped(self, held, inside):
        """On a room square with no way out (`_exit_known`) and no adoption left (`policies.adoptable`: no exterior
        door on this floor, or this episode's adoption already dropped)."""
        if not inside or self._exit_known(held):
            return False
        f = self.flee
        return not (adoptable(self.world) and (f is None or not f.adopted or f.plan is not None))

    def _trapped_fight(self, held, inside):
        """Fix round 1, the review's G3: a flee trapped on a room square (`_trapped`) never steers: armed with a
        reachable held threat, `("fight", None)`; else None (the Flee's trapped hold: M4, an unarmed character inside
        with no way out stands)."""
        if not (self._armed() and self._reachable_held() and self._trapped(held, inside)):
            return None
        return "fight", None

    def _end_flee_episode(self):
        """A flee episode's own flags cleared: its stall origin, its one load drop and its `many` (P23-AM 1)."""
        self.stall_flee, self.flee_dropped, self.flee_many = False, False, False

    def _threat(self):
        held = self._within(self._hold_r())
        if not held:
            self.mode, self.fight, self.flee = None, None, None
            self._end_flee_episode()
            self.sheltered, self.cornered, self.closing = False, None, (0, None)
            return None
        if self.flee is not None:
            self.flee.observe()   # a shelter or exit step's end read before the hold (the close may just have ended)
        breach = self._breach(held)
        kind, reason = self._threat_plan(held, breach)
        if kind == "hold":
            self.why = {"flee": "held_inside", "held": len(held)}
            return None, None
        door = self.door if kind == "door" else None
        want = "flee" if kind == "flee" else "fight"
        if kind == "cornered":
            if self.fight is None or self.fight is not self._corner_fight:
                self.fight = self._corner_fight = Fight(self.world, self.actions, self.clock,
                                                        unreachable=self.unreachable, target=self.cornered)
                self.fight.point_blank = True
                self.fight.mark_free_r = 0.0 if self.corner_kind == "walk" else CORNERED_R
                self.flee = None
                self._end_flee_episode()
            self.mode = "fight"
        elif want != self.mode:
            if want == "fight":
                self.fight = Fight(self.world, self.actions, self.clock, unreachable=self.unreachable)
                if door is None:
                    self.flee = None   # a door fight keeps the sheltered Flee for the re-close
                self._end_flee_episode()
            else:
                if self.flee is None or not self.sheltered:   # only a sheltered Flee outlives a door fight
                    self.flee = Flee(self.world, self.actions, self.clock, shunned=self.night.shunned)
                self.fight = None
                self.stall_flee = reason == "stalled"
            self.mode = want
        if want == "fight" and door is None:
            self.flee = None   # a door fight that left the room: the stale shelter plan goes (the next flee re-picks)
        policy = self.fight if want == "fight" else self.flee
        if want == "flee":
            self.flee_many = self.flee_many or reason == "many"
            policy.threats = held
            policy.hold_ok = breach is None
            policy.many, policy.steer_now = self.flee_many, self.group_steer is not None
            if self.group_steer:
                policy.give_way()   # amendment 6: the group pre-empts a running walk, as the corner does
            ans = self._flee_drop() or self._answer(policy)
        else:
            policy.only = None if door is None else {zid for zid, _ in door}
            ans = self._answer(policy)
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        if self.sheltered:
            self.why["sheltered"] = True
        if kind == "cornered":
            if self.fight.target is not None:
                self.cornered = self.fight.target   # fix round 1, R4: the corner follows its Fight's point-blank re-pin
            self.why["cornered"] = self.cornered
        if self.group_steer is not None:
            self.why["group"] = self.group_steer
        if self.broken is not None:
            self.why["breach"] = self.broken
        return ans if ans is not None else (policy, None)

    def _door_targets(self):
        """(id, zombie) of each reachable held threat standing in the sheltered building's doorway or inside it
        (`policies.in_building`), when the character is armed; else [] (I3: the door fight never walks out)."""
        if not self._armed():
            return []
        b = self.flee.plan["building"]
        return [(zid, z) for zid, z in self._reachable_held() if in_building(self.world, z, b)]

    def _flee_drop(self):
        """At load level DROP_AT or above, a flee episode's first answer is one `Drop` of `LootHouse.spare()`, sent
        as the Flee's own action so the steer waits on it (the drop skill is quick); None otherwise."""
        if self.flee_dropped or self.flee.busy() or ((self.world.load or {}).get("level") or 0) < DROP_AT:
            return None
        iid = spare(self.world)
        if iid is None:
            return None
        self.flee_dropped = True
        self.why = {"flee_drop": iid}
        return self.flee, Drop(iid)

    def _need(self):
        if self.need_last is not None and self.actions.current is self.need_last:
            self.why = {"holding": self.need_last.aid}   # hold first: a frame past the drink must not supersede it
            return None, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}       # P23-AB: answered at the wake; the night holds the tick
            return None
        st = self.world.stats or {}
        pick = None
        for use, stat, t in (("water", "thirst", THIRST_T), ("food", "hunger", HUNGER_T)):
            if pick is not None or (st.get(stat) or 0.0) <= t:
                continue
            pick = self._held_use(use)
            if pick is None:
                self.need_mark = self.need_mark or use
                self.need_marks[use] = self.clock()
            else:
                self.need_marks.pop(use, None)
        self.why = {"item": pick, "mark": self.need_mark}
        if pick is None:
            return None
        return None, Consume(pick)

    def _load(self):
        """At load level DROP_AT or above, one `Drop` of `spare(world)` a decision, holding while it is current; with
        nothing spare, or under DROP_AT, it passes."""
        if self.load_last is not None and self.actions.current is self.load_last:
            self.why = {"holding": self.load_last.aid}
            return None, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}       # P23-AB, as the need
            return None
        level = (self.world.load or {}).get("level") or 0
        if level < DROP_AT:
            self.why = {"level": level}
            return None
        iid = spare(self.world)
        self.why = {"level": level, "drop": iid}
        return None if iid is None else (None, Drop(iid))

    def _night(self):
        """`night.Night`: its own running action holds first (a sleep is never superseded by a fatigue falling under
        the want); not wanting, it passes; a refused sleep's hold answers with no command. Each tick it wants counts in
        `night.wants_n`; `self.why` is the night's own `why`, so the `aid` its `sent` adds reaches the log."""
        n = self.night
        n.observe()
        if n.busy():
            self.why = dict(n.why, holding=n.last.aid)
            return n, None
        if not n.wants():
            n.idle()
            self.why = dict(n.why)
            return None
        n.wants_n += 1
        cmd = n.choose()
        self.why = n.why
        if cmd is None:
            return (n, None) if n.why.get("hold") else None
        return n, cmd

    def _goal(self):
        """The goal runner's command (owner: the runner, which hands the sent Action to its goal); with none, a
        running goal or a pending source (P23-AC) holds the branch, and otherwise the branch passes."""
        cmd = self.goals.tick(self.world, self.actions, lambda: view(self.world, self))
        self.why = dict(self.goals.why)
        if cmd is not None:
            return self.goals, cmd
        return (self.goals, None) if self.goals.current is not None or self.goals.pending else None

    # ---------------------------------------------------------------- the tick
    def _note_failures(self):
        still = []
        self.consume_refused = None
        for a in self._watch:
            if not self.actions.done(a):
                still.append(a)
            elif a.state in FAILED and not (a.state == "failed" and a.reason == PREEMPTED):
                self.last_failed = _key(a.type, a.args) + (self.ticks,)
                if a.type == "consume" and a.state == "failed" and a.reason == REFUSED:
                    self._refused(a.args.get("itemId"))
        self._watch = still

    def _refused(self, iid):
        """A consume refused `not valid`: an id `by_use()` reads `water` is empty (P23-D), one it reads `food` is
        refused (I-4), each marked so it reads `other`; a food and any other id (no longer held) are logged."""
        uses = self.world.by_use()
        if iid in uses["water"]:
            self.world.mark_empty(iid)
            return
        if iid in uses["food"]:
            self.world.mark_refused(iid)
        self.consume_refused = iid

    def _cooling(self, cmd):
        f = self.last_failed
        return f is not None and _key(cmd.TYPE, cmd.args()) == f[:2] and self.ticks - f[2] < FAILED_COOLDOWN_TICKS

    def _inputs(self):
        me = self.world.me or {}
        st = self.world.stats or {}
        held = self._within(self._hold_r())
        cur = self.actions.current
        return {"x": me.get("x"), "y": me.get("y"), "health": self._health(), "hunger": st.get("hunger"),
                "thirst": st.get("thirst"), "fatigue": st.get("fatigue"), "hour": me.get("hour"),
                "armed": self._armed(), "load": (self.world.load or {}).get("level"),
                "threats": len(self._within(DANGER_R)), "held": len(held),
                "nearest": min((zdist(self.world, z) for z in held), default=None),
                "running": cur.type if cur is not None else None, "mode": self.mode,
                "fight_s": self.fight.fight_s() if self.mode == "fight" else None}

    def tick(self, world, actions):
        self.world, self.actions = world, actions
        for p in self._policies():
            p.world, p.actions = world, actions
        self.ticks += 1
        self._note_failures()
        self.goals.observe(world, actions)
        inputs = self._inputs()
        if self.fight is not None:
            self.fight.observe()
        self.need_mark = None
        branch, owner, cmd, cooled, tried = None, None, None, None, {}
        for name in BRANCHES:
            self.why = {}
            ans = getattr(self, "_" + name)()
            tried[name] = self.why
            if ans is None:
                continue
            if name != "threat" and ans[1] is not None and self._cooling(ans[1]):   # a threat is never waited out
                cooled = {"type": ans[1].TYPE, "args": ans[1].args()}
                continue
            branch, (owner, cmd) = name, ans
            break
        inputs["need"] = self.need_mark
        inputs["consume_refused"] = self.consume_refused
        inputs["cooled"] = cooled
        inputs["branches"] = tried
        action = None
        if cmd is not None:
            action = owner.send(cmd) if owner is not None else self.actions.send(cmd)
            if owner is None and branch == "need":
                self.need_last = action
            elif owner is None and branch == "load":
                self.load_last = action
            self._watch.append(action)
        self.goals.held(branch not in (None, "goal") and cmd is None)
        self.last_branch = branch
        line = {"wall": self.clock(), "gameMin": self.world.game_min, "branch": branch, "inputs": inputs,
                "action": {"type": cmd.TYPE, "args": cmd.args()} if cmd is not None else None,
                "sent": action is not None, "goal": self.goals.line()}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return action
