# The doctrine variant (Plan 31 Task 11, D)

`Survive(control="doctrine")` (the fork, `planner/control.py`). The design is the union of two proposals in Plan 30's
workspace: `rebuild-proposal-intent-machine.md` (the arbiter) and `rebuild-proposal-combat-doctrine.md` (the plays and
the bound on "fight everything"). The spec's section 3, D bullet, is the contract.

## What it decides and how

The character holds exactly one intent at a time. Each tick (2 Hz), `situation.read` turns the World into the wants of
six hard priorities, top down. The arbiter (`arbiter.py`) then picks one:

| P | Want (`situation.py`) | Intent (`intents.py`) |
|---|---|---|
| 0 | A standing zombie within the strike radius (the frame's `weapon.reach` + 0.35, or 1.1 bare-handed), or `me.attackers` > 0. | **Strike**: one melee press, then back to the slot. |
| 1 | A bleeding, unbandaged part. No standing zombie within KEEP_R. Something held or worn to dress it with. | **Dress**: `maneuvers.Dress`. It stops, tears worn cotton if nothing is held, and bandages. |
| 2 | Three or more standing aware zombies within GROUP_R, not strung out. Or two unarmed. | **Avoid**: a run to a refuge chosen once, then the stance there. |
| 3 | The nearest standing aware zombie within ENGAGE_R: one or two of them, or the lead of a strung-out three. Else a fallen zombie within 3 tiles with none standing there. | **Fight**: the melee to the kill, and the finish. |
| 4 | A zombie behind a door or a window within 4 tiles. | **Door**: decided once. Stance and open with two or fewer behind, else leave. |
| 5 | Always. | **Order**: the needs, then the goal runner's loot, travel and stock. |

Every want except P4's excludes a zombie behind a door, a window or a wall the map reads, because the hit list drops
such a target (#4681). "Aware" is `hasTarget` or `known`. Health is read by no want, so a lone zombie in reach is fought
whatever the health (memory `stand-and-fight-dress-first`).

An intent ends in one of three ways:

- `done`, by its own success test;
- `failed`, by its own failure test;
- pre-empted, by a strictly higher priority only.

Nothing of equal or lower priority interrupts. A second Fight's want waits for the first Fight's end, and a want at the
same priority with another target does nothing.

A pre-empted intent waits in a one-deep resume slot. It comes back when the pre-empting intent ends, unless it ended by
its own test meanwhile or a higher want is up. The goal layer gets the same rule through `source.Resume`: a goal the
runner closed as `superseded` is proposed again on the next ask, up to RESUME_MAX times (a Rest never). So a Loot
resumes after a Strike. A Strike's live melee is handed to the Fight that follows it at the same zombie.

The intents, each with its tests:

- **Strike**: `done` on its one press (`press`: today's melee's span, or the meet's new press leaf), `kill`, `gone`
  or `out` (beyond MELEE_RELEASE_R), or the melee's other ends. `failed` on
  `not loaded`, `bad args` or `unknown type`. Under arm pain over 10 (#4370) the press is in `shove` mode.
- **Fight**:
  - Within MELEE_RELEASE_R, or at a fallen zombie, it sends the melee. The mode is `strike`, `shove` (unarmed or
    spent) or `finish`.
  - Farther out:
    - A pair arriving within STRING_GAP of each other is strung: the stance backpedals on one heading, chosen once.
    - A chaser is met standing in the stance ("let it come").
    - An idle, aware zombie is closed on.
  - `done` when none of its zombies is left (`kill` or `gone`).
  - `failed dud` after DUD_N strikes that lowered nothing, or on the meet's own stall (`lost` `no progress`).
    `failed stall` when the pin's distance has not fallen for
    STALL_S. Either way the pin is skipped for SKIP_S, but still struck at P0.
- **Dress**:
  - It rides the pre-empted intent's walk for a part above the legs.
  - `done` when the part reads not bleeding.
  - `failed` with the maneuver's own end (`nothing`, `moving`, `sends`). P1 is then held off until a dressing or a
    garment is added, or `care.DRESS_RETRY_S` passes.
  - `failed zombie near` when a standing zombie comes within KEEP_R. There is no hold then: the fight takes it.
- **Avoid**:
  - It runs to the refuge, never a sprint. The refuge is one of:
    - the building itself, on a room square with the group outside;
    - the building's way out (`policies.exit_plan`), with the group inside;
    - the nearest safe unlocked exterior door within 25 tiles, its post inside;
    - the farthest open square along the clear headings off the away vector.
  - It re-routes only when the route fails (stuck, no path, no square, a timeout, or a stall), up to ROUTE_TRIES times.
  - At the refuge it holds the stance facing the nearest: one leg, never a second.
  - `done clear` with no aware zombie within GROUP_CLEAR_R. `done thinned` with two or fewer, armed: the Fight takes
    them.
  - `failed no refuge` or `failed route` holds P2 off for AVOID_RETRY_S. Meanwhile P3 fights the nearest whatever the
    count: the stance, never a leg.
  - The sneak once out of sight is Survive's gait (`sneak.py`). A walk with no zombie near chasing goes crouched.
- **Door**:
  - `stance_open` runs the stance's leg to the door's post (`door_held.door_post`), then `Interact open`, then the
    stance facing the zombie (`meet`).
  - `leave` does three things in one tick, then ends `done leave`, and the same tick goes to the order. It marks the
    door held. It ends the running goal whose way goes through the portal. It hands the portal to the goal runner
    (`door_left`).
  - `done crossed` or `done gone`. `failed open <reason>` leaves the door.
  - A decision is not taken again for the same zombies within DOOR_DECIDED_S.
- **Order**:
  - It runs Survive's own `_need`, `_load`, `_night`, `_care_stock` and `_goal`, in that order. A command still
    cooling (`Survive._cooling`) is passed over.
  - While a LootBuilding runs, it prefetches the model's next order (`source.Resume.prefetch`, every PREFETCH_S, only
    for the `llm` source).
  - It never ends by itself.

## What it drops of the ladder, and why

All of the ladder stays in place behind the fork. Under `control="doctrine"`, `Survive._assess_ladder` is never called,
so none of the following run:

- **The threat branch's decision** (`threat.py`): `_threat` (`threat.py:949`), `_threat_plan` (`threat.py:756`),
  `_flee_reason` (`threat.py:394`), `_hysteresis` (`threat.py:468`), `_unpaired` (`threat.py:568`), the kept flee
  and the flip (`_kept_flee`, `threat.py:841`), `_breach` (`threat.py:592`), `_cornered` (`threat.py:616`), `_group`
  (`threat.py:748`), `_trapped_fight` (`threat.py:866`), `_low_fight` (`threat.py:502`), `_unarmed_fight`
  (`threat.py:492`) and `_finish_lone` (`threat.py:408`).
  - The flee reasons `held`, `pair`, `flip`, `health`, `strain`, `unreachable`, `stalled` and `many` go with them,
    with REFIGHT_MARGIN, FLEE_HEALTH and FLEE_HEALTH_PAIR.
  - Why: F15 fled all 27 of its fights, and 211 of its 298 flee lines had one standing zombie or none within 6 tiles.
  - The stateless 2 Hz re-choice is the structure that needs these latches. The one reaction the doctrine keeps is
    P2, the group (spec section 1; #4669-#4677).
- **`hold.py`** (the strain and endurance holds) and **`still.py`** (P30-E):
  - They stood the character while zombies closed (memory `intent-doors-sneak`).
  - The doctrine's Fight never stands for a hold. Spent means the shove mode, not a stop.
- **`care_yield.py`** (the threat's yields to the care) and **`_care`'s bleeding step**:
  - The yields are what made the nine unwears go out under a moving flee leg (`moving`, F15).
  - P1 replaces them with one Dress that stops first, ahead of every priority but P0.
- **`pull.py`** and **`engage.py`** (the seek):
  - Replaced by P3: one or two aware zombies within ENGAGE_R are fought.
  - A chaser is met in the stance rather than pulled or sought.
- **The Fight's per-tick ladder** (`fight.py`'s `_choose` and `_ladder`, `fight.py:924` and `fight.py:932`;
  `shove.py`'s corner reads; `finish.py`'s flee finish; `doorway.py`'s stand ends; and `dispatch.py`'s dispatch point,
  `_melee_mode` and `_melee_dispatch`, `dispatch.py:181` and `dispatch.py:211`):
  - They re-decided the physical sequence every tick: 19 of F15's 26 melees ended `failed superseded`.
  - The doctrine's Fight sends the melee and lets it run to its own end.
- **`door_held.py`'s read in `_read`** is turned off on the doctrine's Survive instance (`DOOR_HELD = False`, an
  instance attribute, never the class). Its leave would mark the zombies and end goals before the doctrine decides.
  The Door intent reuses its geometry (`portal_between`, `door_post`, `meets_portal`).

It keeps, read or called unedited:

- the World and the protocol;
- the Lua skills and the melee reflex;
- `maneuvers.Melee` and `maneuvers.Dress`;
- the goal runner and the model;
- the water chain, the night and the rag stock (through the Order);
- `policies.exit_plan`, `night.exterior_doors`, `door_held.py`'s geometry and `edges.same_side`;
- the sneak gait (`Survive._apply`).

## The constants and their sources

`constants.py` carries each constant's source on its line. In summary:

| Constant | Value | Source |
|---|---|---|
| GROUP_N | 3 | The drag-down counts three attackers at the fixture's Strength (#4290). Spec section 3, D. |
| GROUP_R | 6.0 | DANGER_R, the combat doctrine's class radius. A first guess. |
| GROUP_CLEAR_R | 10.0 | DISENGAGE_R. Wider than GROUP_R, so a group at its edge does not flip the intent. A first guess. |
| ENGAGE_R | 9.0 | P24-X's ENGAGE_R. |
| STRING_GAP | 3.0 | The combat doctrine's section 3: two swings and a finish at 1.6 tiles/s, clips of 0.625-1.25 s (#4668). A first guess, the first constant to measure. |
| STALL_S | 6.0 | P30-E's STILL_S. A first guess. |
| STRIKE_MARGIN | 0.35 | P27-M's ATTACK_MARGIN. |
| UNARMED_REACH | 1.1 | The bare hands' MaxRange (#4592). |
| SPENT_PAIN | 10.0 | STRAIN_SOFT. Over it a swing's damage is divided (#4370). |
| DOWNED_R | 3.0 | FINISH_CLEAR_R. |
| DUD_N | 6 | Twice STALL_SWINGS. A first guess. |
| SKIP_S | 20.0 | UNREACHABLE_S. |
| DRESS_CLEAR_R | 2.5 | KEEP_R, the Dress maneuver's own `superseded` radius. |
| REFUGE_R | 25.0 | SHELTER_FLEE_R. |
| OPEN_REACHES | 12, 9, 6 | A first guess. |
| AVOID_RETRY_S | 20.0 | A first guess. |
| ROUTE_TRIES | 2 | A first guess. |
| DOOR_R | 4.0 | P30-C's DOOR_HELD_R. |
| DOOR_OPEN_MAX | 2 | The task's amendments. |
| DOOR_DECIDED_S | 60.0 | A first guess. |
| RESUME_MAX | 3 | A first guess. |
| PREFETCH_S | 2.0 | A first guess. |
| CLOSE_WALK_R | 5.0 | In `intents.py`. A first guess. |

None of them asserts an engine mechanism without a row.

## The decision line's keys

The fork's contract holds:

- `branch` is `threat` on a strike, fight, avoid or door tick, `care` on a dress tick, and the ladder step's own name on
  an order tick (`need`, `load`, `night`, `care`, `goal`).
- `inputs.x` and `inputs.y` are as the ladder writes them.
- `inputs.branches.<branch>` holds the act's why. A kill read this tick is on `branches.threat.kill`. The goal
  runner's stuck mark and stall are on `branches.goal`, as the ladder puts them.
- While an Avoid walks, `inputs.branches.threat.flee` reads `group`.

The doctrine's own keys:

- `inputs.doctrine` = `{intent, p, why, state, target, preempted_by, resumed, ended, slot, wants}`, plus
  `step` (the order's label) and `resumed_goal` (the goal type the source resumed this tick).
  - `preempted_by` is `{was, p}`, the intent this line's intent pre-empted.
  - `resumed` is true on the tick the slot came back.
  - `ended` is `{intent, p, end, why}` of an intent that ended this tick, or a list of them if more than one ended.
  - `wants` is the priorities that read true this tick.
- `inputs.intent` = `{kind, target[, play]}` is the scorecard's label (`tools/trial_score.py`). Its `target` is a zombie
  id or a square `[x, y]`.

## The label contract for the scorecard

| Intent | `inputs.intent.kind` | Target | Scored as |
|---|---|---|---|
| Strike | `strike` | the zombie id | |
| Fight | `fight` | the pin's id | `play: "string"` while it strings a pair: a retreat label, so the backpedal counts as fleeing |
| Dress | `dress` | none (a part is no place) | |
| Avoid, walking | `avoid_refuge` (a building's door or way out, or the building itself) or `avoid_open` (open ground) | the refuge square | a retreat; `avoid_refuge` also names a refuge |
| Avoid, holding | `filter_door` at a door, way out or inside; `fight_hold` in the open | the refuge square | |
| Door | `filter_door` for stance and open; `door_leave` for leave | the door square | |
| Order | `needs`, `rest`, `stock`, `loot` or `travel` | the goal's walk target where it has one | On goal lines the scorecard also reads the goal's own args, as for the ladder. |

## What it still needs from the harness, and the risks a trial row will show

- **Task 2's meet (PZA/1.10).**
  - The Strike and the Fight press through one call site, `intents.melee_command`. It builds its inputs with
    `intents.melee_inputs`, which reads which `Melee` API the tree carries: the guard is `intents.MEET`, true when
    `MeleeInputs` has no `back` field.
    - On Task 2's meet: `MeleeInputs(mode, reach, floor_swing)`. There is no back step, no swing close and no time
      end in the API at all.
    - On today's PZA/1.9 melee: `MeleeInputs(mode, reach, (0, 0), floor_swing, 0)`, with no back step and no swing
      close.
  - The ends are read one way on either API (`intents.melee_end`):
    - `kill` (PZA/1.9's `dead`) ends the Strike or Fight on its kill.
    - `handback` (PZA/1.9's `crowd`) re-pins the Fight to the other zombie.
    - `lost` `out of reach` skips the target. `lost` `no progress` is the Fight's `dud`. `lost` `out of range` drops
      the melee, and the Fight closes again.
  - A Strike's one press is read as today's span or as a new press leaf (`d_press`, `d_collide_pred`, `look_off`,
    `hp0`, `hp1`, `knock`, `cut_by`). It is logged through the maneuver's `log()` under the act's `maneuver`.
  - The tests run on both APIs. One test of the `lost` `no progress` end is skipped where the meet is absent. On a
    scratch copy of Task 2's tree (4d646a0a, without Task 8's fix 1), the whole file passes except two dress-hold tests
    that need `care.DRESS_RETRY_S`, which main has.
  - Until the meet boots, the first trials' hits per kill are provisional. Commitment amplifies a bad swing: the
    doctrine fights every lone zombie to its end, and F15's 22 swings killed nothing (#4649).
- **The string.**
  - It is planner-side: a stance backpedal on one heading. There is no circling of a pair and no shove-one-strike-the-
    other until a `string` play exists.
  - Its gap rests on one session's zombie speed.
- **A coarse P2.**
  - Three strung-out zombies are fought one at a time only when the lead is STRING_GAP ahead of the second.
  - A group whose arrivals are 2 to 3 tiles apart is avoided.
- **Avoid in the woods.**
  - With no known building near, the refuge is open ground, labelled `avoid_open`. That is the old flee leg under a new
    name. It ends in the stance, never a second leg.
  - The trial row's `min fleeing`, with its `(away N)` cell, will show how much time it takes.
- **A chaser that never closes.** One held behind a fence or an edge the map does not read is met standing for
  STALL_S, then left for SKIP_S, and the goal walks meanwhile. That can show as the walk-pause-walk Angus ruled out
  (memory `intent-doors-sneak`), bounded at one stall per SKIP_S per zombie.
- **Windows as ways out.** The Avoid's exit is a walk only (`exit_plan`'s `walk` step). A window's climb is the ladder
  Flee's and is not used.
- **No Lua change of its own.** The variant asks nothing of the Lua or the schema beyond Task 2's meet: the look
  angle, the timed press and the finish aimed at the fallen zombie's head (J1) are the reflex's. On a PZA/1.9 build
  the floor swing goes where that reflex points it.
