"""The doctrine's constants (Plan 31 Task 11, the variant D), each with its source: a register row by id
(`docs/reference/claims.tsv`), a memory under Angus's project memory, a planner constant it borrows, or "a first guess
for the trials" (a trial is no evidence, ruling P31-T: these are the numbers the first round reads, never a
measurement). No constant here asserts an engine mechanism without a row."""
from agent.base.planner.policies import (ATTACK_MARGIN, DANGER_R, DISENGAGE_R, DOOR_HELD_R, ENGAGE_R as LADDER_ENGAGE_R,
                                         FINISH_CLEAR_R, KEEP_R, MELEE_BACKOFF_TICKS, SHELTER_FLEE_R, SHOVE_R, STILL_S,
                                         STRAIN_SOFT, UNREACHABLE_S)

# ---------------------------------------------------------------- the priorities
P_STRIKE, P_DRESS, P_AVOID, P_FIGHT, P_DOOR, P_ORDER = range(6)   # the six priorities, top down (spec section 3, D)
PRIORITY_NAMES = ("strike", "dress", "avoid", "fight", "door", "order")

GROUP_N = 3          # standing aware zombies within GROUP_R that make a group, avoided: three is where the drag-down
                     # counts at the fixture's Strength (#4290: 3 or more attackers within 0.9 tiles at Strength 2);
                     # Angus's "one zombie is never a reason to flee" (memory `stand-and-fight-dress-first`) and the
                     # doctrine's "one or two are fought" (spec section 3, D)
GROUP_R = DANGER_R   # 6.0 tiles: the radius the group is counted in, the combat doctrine's class radius (its section 2:
                     # "aware standing zombies within DANGER_R 6"); a first guess for the trials
GROUP_CLEAR_R = DISENGAGE_R   # 10.0 tiles: an Avoid ends `done` with no aware standing zombie this near, or with two
                     # or fewer this near (the group thinned, a Fight then): wider than GROUP_R so a group read at its
                     # edge does not flip the intent each tick; a first guess for the trials
ENGAGE_R = LADDER_ENGAGE_R   # 9.0 tiles: one or two aware zombies this near are fought (ruling P24-X's radius, Plan 24
                     # Task 18 fix 1, inside DISENGAGE_R)
STRING_GAP = 3.0     # tiles: three or more aware zombies whose nearest leads the second by this much are strung out, so
                     # the lead is fought, not the group avoided; and a pair arriving closer together than this is
                     # strung (the backpedal on one heading until the lead is this far ahead): two swings and a finish
                     # at 1.6 tiles a second with clips of 0.625 to 1.25 s (#4668), the combat doctrine's section 3;
                     # a first guess for the trials, the first constant to measure
STALL_S = STILL_S    # 6.0 wall seconds: a walk (an Avoid's, a Fight's approach) whose distance to its target has not
                     # fallen for this long is stalled: P30-E's still read (STILL_S) borrowed; a first guess for the
                     # trials

# ---------------------------------------------------------------- the strike (P0)
STRIKE_MARGIN = ATTACK_MARGIN   # 0.35 tiles past the frame's `weapon.reach`: the strike radius, P27-M's attack line
UNARMED_REACH = SHOVE_R         # 1.1 tiles: the strike radius with no weapon, the bare hands' shove reach (#4592)
FALLBACK_REACH = 1.2            # tiles: the strike radius's reach when the frame reads none, the fixture's bat's
                                # `weapon.reach` (the fake mod's and F15's frames); a first guess for the trials

# ---------------------------------------------------------------- the fight (P3)
DOWNED_R = FINISH_CLEAR_R   # 3.0 tiles: a fallen zombie this near, with no standing one within it, is finished (the
                     # combat doctrine's `downed` class; P27-A's FINISH_CLEAR_R)
SPENT_PAIN = STRAIN_SOFT    # 10.0: the arms' summed pain over which a swing's damage is divided (#4370), the Fight then
                     # pressing in `shove` mode, the shove's knock-down ignoring damage (#4373) and the stomp's damage
                     # set after the divider (#4374): the spec's section 4 item 2b
DUD_N = 6            # strikes in a row at one target that lowered nothing before the Fight ends `failed` "dud" and the
                     # target is left (UNREACHABLE_S): twice the ladder's STALL_SWINGS (3); a first guess for the trials
SKIP_S = UNREACHABLE_S   # 20.0 wall seconds a zombie a Fight failed on (stalled, dud, unreachable) is not fought again
                     # (it is still struck at P0 within reach)
BACKOFF_TICKS = MELEE_BACKOFF_TICKS   # 10 doctrine ticks a melee that ended `interrupted`, `timeout`, `no target` or
                     # `no weapon`, or was rejected, is not sent at its zombie again: the ladder's back-off (Plan 28 Task
                     # 7b fix 1, review-t7b m2; review-t11-doctrine Major 2)

# ---------------------------------------------------------------- the dress (P1)
DRESS_CLEAR_R = KEEP_R   # 2.5 tiles: a bleeding part is dressed unless a standing zombie is this near (the Dress
                     # maneuver's own `superseded` radius, `maneuvers.dress`); Angus: "dressed before the goal and
                     # before any flee from a zombie beyond the stance's reach" (memory `stand-and-fight-dress-first`)

# ---------------------------------------------------------------- the avoid (P2)
REFUGE_R = SHELTER_FLEE_R   # 25.0 tiles: a named structure this near is a refuge (P23-AG's shelter radius): a door,
                     # a building's way out (an opening, a door or a window), a fence line; the controller's ruling on
                     # review-t11-doctrine M5: never open ground (the doctrine of item 5, "never an open-ground leg")
REFUGE_KINDS = ("inside", "exit", "window", "door", "fence")   # the refuges `situation.refuge` names; with none the
                     # Avoid is not taken and the stand is (`GROUND_R`)
GROUND_R = 2.0       # tiles: with no refuge, the stand takes the nearest square this near with a wall or a fence at its
                     # back (the blocked edge on its side away from the group), else the character's own square, and
                     # fights the arrivals one at a time (the controller's ruling on M5; memory
                     # `stand-and-fight-dress-first`: no aimless running)
AVOID_RETRY_S = 20.0   # wall seconds after an Avoid failed (its route failed twice) or held its time out before another
                     # starts; meanwhile the Fight takes the nearest whatever the count (the stance, never a leg); a first
                     # guess
AVOID_HOLD_S = 10.0  # wall seconds the stance at the refuge holds before the Avoid ends `done held` into the Fight at the
                     # refuge (the filter play, the doorway stand: review-t11-doctrine M6, E23's `held`); a first guess
ROUTE_TRIES = 2      # route failures (a walk failed stuck, no path or no square) an Avoid takes before it fails

# ---------------------------------------------------------------- the door (P4)
DOOR_R = DOOR_HELD_R   # 4.0 tiles: a zombie behind a door or window this near is a door decision (ruling P30-C)
DOOR_OPEN_MAX = 2      # zombies behind a door at most for the stance-and-open; more re-routes (the task's amendments,
                       # Angus's "leave, or take the stance and open it", memory `intent-doors-sneak`)
DOOR_DECIDED_S = 60.0  # wall seconds a door's `leave` decision stands for the same zombies behind it before it is read
                       # again; a first guess for the trials
DOOR_WAIT_S = STALL_S  # 6.0 wall seconds the stance waits at an opened door for its zombie to come through, then as long
                       # again fighting it through the doorway (the walk to the threshold and the meet at it); a Door
                       # never holds longer (review-t11-doctrine Major 1; Angus's "sticks near the door", memory
                       # `intent-doors-sneak`); a first guess for the trials

# ---------------------------------------------------------------- the standing order (P5)
RESUME_MAX = 3       # times one goal (its type and args) is resumed after a supersede before it is let go; a first guess
PREFETCH_S = 2.0     # wall seconds between the prefetch asks of the model's next order during a Loot; a first guess
