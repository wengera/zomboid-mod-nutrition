# The situation utility (Plan 31 Task 11, variant U)

`Survive(control="utility")`. The design is the proposal `rebuild-proposal-situation-utility.md` (Plan 30's workspace)
and the spec's § 3 U bullet. A trial build (ruling P31-T): nothing here is evidence, and no row cites it.

## What it decides and how

About once a second (`select.SELECT_S`), and at once on an interrupt, it scores six to ten candidate acts and holds
the best one. The candidates are `fight:<id>` (the three nearest standing zombies within ENGAGE_R, every fallen one
within FINISH_R, and the held fight's own target out to DISENGAGE_R), `stand:<id>`, `dress:<part>`,
`retreat:door:<x>,<y>` (to each door filter), `travel` or `loot` (the goal runner's goal, only while one runs or its
source is pending; with neither the runner is asked to propose), `sneak`, `needs:<branch>` and `rest`. `acts.py`
generates them and `features.py` reads the frame they are built from.

A group arriving takes away every walk: no travel, loot, sneak or needs candidate is generated (fix 1, review-t11-utility M1, the refuge ruling: the walk away from an arriving group is the
open-ground leg, whatever its goal). In their place stands the `stand`: the stance where the character is, facing the
nearest aware zombie, the arrivals met one at a time (the ruling's string), its hits taken at BACK_FACTOR with a wall
or fence within two tiles behind; it is generated while no aware zombie is in reach, since one in reach is the
fight's. The retreat to a filter stays a candidate. A group arrives (fix 2, review-t11-utility-fix1 M2) while three or
more aware standing zombies listed can come: each within DANGER_R or beyond it closing, and each able to reach the
character, its fight not vetoed (`acts.arriving`), and one of them stood within DANGER_R inside the last
STAND_RECEDE_S (5 s, a first guess; `acts.GroupClock`). So the stand never targets a zombie across a blocked edge or
marked unreachable, and a group that recedes or cannot come ends the stand and gives the walks back (F6 478-481, E23
476-477 and 523-524).

Each score is a sum of named terms (`select.terms`), linear in five weights, with H, the cost of one hit, as the unit:

| term | weight | what it is |
|---|---|---|
| `kill` | K | P_kill, the chance of the kill within the act's span |
| `hit` | H = 1 | minus the expected hits over the span (for a retreat, the hits it saves) |
| `bleed` | B | bleeding part-minutes: the dress credits the bleed it stops, every other act pays for its span |
| `chase` | C | 1 for a fight (or the stand) at a standing aware zombie while armed: a lone chaser always scores the fight |
| `goal` | V | the goal's progress (the needs at NEED_VALUE, the rest by the endurance level) |
| `regress` | G | minus the tiles a retreat runs off the way, over 10 |

The held act is kept for its minimum span (a fight 4 s or until its target ends, a dress until done, a travel 3 s,
a retreat until it reaches its filter). After the span, a rival replaces it only when it beats the held act by
delta = 0.3 + 0.2·|U_held|.

Four interrupts re-score at once and lift the span: a new hit reaction, a part newly bleeding, a standing zombie
other than the target entering 1.5 tiles, and a goal answer. The act's own end is the fifth. None of them lifts a
retreat's span: the run goes to its filter and ends in the stance there, and no retreat is generated while the
character stands on that filter. The sixth, `reach` (fix 1: an aware standing zombie other than the fight's target
come within KEEP_R), chooses afresh with the margin and every span lifted, a retreat's too: one zombie in reach is
fought, the controller's ruling on M3. A held act stays eligible whatever its score, so a retreat already taken is not
dropped when the group's count changes its score on the way.

Three vetoes sit outside the utility, as feasibility. The first is an unreachable target: the planner's
`unreachable` and edge marks, this package's own `out of reach` marks, a known blocked edge with no door passing it,
or a door the door read decided to `leave`. The second is the ride: a leg part's bandage never rides a walk [#4337].
The third is the zombie in reach: no dress while an aware standing zombie is within KEEP_R (fix 1, M2), and no fight
at a standing zombie beyond KEEP_R while one in reach can be fought (fix 2, review-t11-utility-fix1 M1, the
controller's ruling: the fight at the zombie in reach wins whatever is listed; the kill term alone, with K unset, let a
receding zombie 6 tiles off outrank one at 1.64 on E23 322). A fallen zombie's finish stays a candidate and pays the
unfaced zombie's hits (`select.UNFACED_FACTOR` 2.0, a first guess: a player attacking and facing a zombie is not
bitten by it, #4688, so one left behind the swing is). A retreat scoring at or under 0 saves no hits; it would be an open-ground leg, so it is never chosen. There is no flee act and
no wait act.

The executors (`execute.py`) run the held act through the shared plays:

- `fight`: the `Melee` maneuver within KEEP_R. Its mode is `finish` at a fallen target, `shove` when spent (the arms'
  pain over 10, or the endurance or tired moodle at level 2: the spec's § 4 2b) and `strike` otherwise. Farther off
  it uses the stance: `Aim` standing facing an aware chaser (it comes to the character), `Aim` walking toward an
  unaware or fallen zombie, a walk beyond 6 tiles, or a route through the door of a known blocked edge. A zombie
  behind a closed door that the door read opens gets P30-C's post, open and meet (`door_held.FightDoorHeld`).
- `dress`: the `Dress` maneuver: stop, tear, bandage, riding the walk for a part above the legs.
- `stand`: the stance (`Aim` standing) facing the nearest aware zombie, never a step toward or away; the first to
  come within reach is the fight's.
- `retreat`: a run (`WalkTo` at a run) to the post inside the door's threshold (`policies.stand_post`).
- `travel`, `loot` and `sneak`: the goal runner (`Survive._goal`). The sneak posture is SneakGait's, sent when the
  tick is sent whatever the act (the common amendments' item 5, the sneak gait near unaware zombies while walking,
  holds through `Survive._apply`). The `sneak` act itself is chosen where it beats the fight at an unaware zombie:
  at the first fit's K 3.7 it never was (a fight at any unaware zombie within 9 tiles outranked it, about 3.2 against
  0.37: review m7); at fix 2's K 0.47, which no direction sets, it is chosen on 5 F15 and 60 E23 lines. Whether an
  unaware zombie near is sneaked past or fought is a question no ruling answers yet: the kill's worth K decides it.
- `needs`: the ladder's quiet steps (`_need`, `_load`, `_night`, `_care` with nothing bleeding, `_care_stock`), only
  with no standing zombie within DANGER_R.
- `rest`: sends nothing.

## The models (fitted, `models.py`; `tools/utility_fit.py`, the artifact's `models`)

With tens of hits, these models are bounded rather than learned.

The hazard is P(hit-reaction onset within 1 s | the nearest standing zombie at d) = sigma(b0 + b1·d). It is fitted
on E19 to E23 and F11 to F15: n = 9184 samples, 95 positive, 51 onsets. b0 = -0.0569 and b1 = -3.5825, so the rate
is 0.0259 hits/s at 1.0 tile and 0.00073 at 2.0 tiles. The ±5 % probes give a rate at 1.0 tile of 0.0260 / 0.0259
(b0) and 0.0309 / 0.0217 (b1).

The full model adds the attack `state` term. Only F15 carries `state`: n = 868, 6 onsets, b_attack = 0.144. It is
reported and not used. A situation's rate is the sum of each zombie's: that is additive structure, not a reading.

The kill chance per press is kills over presses weighted by the structure:

- Swing: 27 kills over 152 swings (127.6 weighted), p_swing = 0.2115, so P_kill over the 20 s horizon is 0.978
  (±5 %: 0.972 / 0.982).
- Finish: 12 over 67 (stomps and floor swings), p_finish = 0.1832 (P_kill over the horizon 0.961; ±5 %: 0.953 /
  0.967).

The fixed structure is:

- the arm-pain divisor clamp(s/10, 1, 30) on swings [#4370];
- the moodle multipliers 0.5, 0.2, 0.1 and 0.05 per level [#4371], with the levels from #3926 and #2279;
- the drag-down, the rows' event (#4290: three zombies attacking together from under 0.9 tiles zero the defences;
  #4291: the drag-down kills), priced once at DRAG_HITS = 3 hits (a first guess) when three aware listed zombies are
  predicted within KEEP_R inside a standing act's span; none on a fight whose target is already in reach, none on
  the move or at a filter, none on the stand (fix 1, M2; before it, 3 hits per zombie past the second anywhere in the
  span, which the rows' shape did not support). The rings hold no drag-down to fit one on.

## The weights (`weights.py`, the linear program's chosen point)

The verdict set is the aligned decision lines of F2 to F15 and E19 to E23, labelled by Angus's directions, re-mined at
fix 1 and fix 2 with the controller's ruling on M3: `one` applies to an aware zombie within the stance's reach and
makes the fight at it win whatever else is listed, every act that is not a fight and the fights at standing zombies
beyond reach (fix 2; those fights are vetoed while one in reach can be fought, so the rows against them stay empty: the
veto is the ruling's structure, never a score), and `group_coming` applies to the acts beyond reach (with three aware
within DANGER_R and a filter, the retreat beats the stand and the fights beyond reach; with no filter and a group
arriving, read by `GroupClock` across the ring's lines, the stand beats each walk into the group: a fight at another
aware zombie beyond reach whose span the drag-down reaches). Each labelled line is a ranking row: U(labelled) ≥
U(other) + 0.1. That gives 4154 rows over 54778 candidates scored. The rules: `one` (2882 lines), `dress_quiet`
(2623), `dress_far` (676), `sneak` (165, structural: all held), `group` (0: no line had three aware zombies within
KEEP_R and a filter), `group_coming` (533) and `door` (1851 lines, structural: no wait candidate exists). The region
is feasible: no pair conflicts.

| weight | value (Chebyshev centre) | feasible interval |
|---|---|---|
| K | 0.471 | [0, 4.903], at its lower bound; no direction sets it |
| B | 1.152 | [0.286, 3.222] |
| C | 3.583 | [0, 4.992], at its lower bound |
| G | 1.191 | [0, 5.170], at its lower bound |
| V | 0.471 | [0, 1.810], at its lower bound; no direction sets it |

The radius is 0.471 and the least slack 0.512 (the artifact lists one slack per row).

**What "no direction sets it" means** (the artifact's `lp.unset`). K and V sit at the Chebyshev ball's radius off
the box face 0: the box, not a ruling, places them. For V, no labelled line asks the goal to pull (no rule ranks the
travel or the loot first): the goal's pull is bounded only from above, by the dress's and the fight's rows, and at V
near 0 a quiet tick's goal walk scores about nothing, so only the commitment and the goal runner keep the character
moving. For K, the rule `one` ranks the fight at an aware zombie in reach first through the chase credit C, so no
line needs the kill's own worth; a fight at an unaware zombie, priced by K alone, is sought only weakly. A
clear-then-loot rule (the travel over the rest and the needs when quiet; the fight at an unaware zombie near over the
walk past it) would set them: a ruling for the controller.

**The drag-down sets the caps.** The region is the drag-down's projection: at DRAG_HITS 1, 2, 3 and 6 hits the radius
is 0.163, 0.322, 0.471 and 0.835, K's upper end 2.00, 3.62, 4.90 and 8.16, and C's 2.99, 3.99, 4.99 and 7.99
(`lp.drag_probe`). DRAG_HITS 3 is a first guess; the caps follow it.

**The probes, on decisions** (`decision_probes`, fix 1, M5): each parameter scaled by 0.95 and 1.05, the two goldens'
rings replayed whole, the lines whose decision moves counted over 1660 lines (fix 2's build): B 13, C 34, K 34, V 21
and DRAG_HITS 21 move decisions; G and the hazard's b0 move none at +-5 % (at 0.5 and 2.0, b0 moves 34 at 2.0, G none:
on F15 and E23 no retreat is taken, so the regress decides nothing there). `test_utility_fit.py` asserts every probe
moves a decision and marks the two flat ones strict xfail, for the controller's ruling.

## The constants with their sources

Every module constant carries its source on its line: a row by id, a memory, or "a first guess for the trials".
The first guesses are:

- spans and margins: SELECT_S, DELTA0, the spans;
- timings and paces: SHOVE_CYCLE_S, STANCE_PACE, CHASE_MIN, DRESS_HELD_S / DRESS_TEAR_S, ROUTE_S;
- shares and prices: STOMPS_PER_DOWN, FALLEN_FACTOR, UNAWARE_FACTOR, NOTICE_HITS, BLEED_HORIZON_M, DRAG_HITS,
  BACK_FACTOR;
- filter search: RETREAT_R, FILTERS_N;
- verdict margin: MARGIN 0.1.

## What it drops of the ladder, and why

- **The flee ladder and its hysteresis** (`threat.py`'s `_decide`, `_hysteresis`; the reasons `held`, `pair`,
  `flip`, `many`, `health`, `strain`, `unreachable`; the `many_tail`, the health pass, the refight margin). Each was a
  hard boundary written for one incident, and two boundaries disagreeing on one frame made the flips. F15 fled all 27
  fights. Here the retreat is one scored act toward a filter.
- **The holds and yields** (`hold.py`, `care_yield.py`): the commitment and the bleed term replace them.
- **The pull** (`pull.py`) and **the engage seek** (`engage.py`): a fight's score is the seek.
- **The still rule** (`still.py`).
- **The rule halves of `finish.py` and `door_held.py`**: the finish is a fight at a fallen zombie, and P30-C's read
  is kept as the generator.
- **The Fight's per-tick leg ladder** (`fight.py`'s `_choose`): 19 of F15's 26 melees were superseded by the next
  tick's rule. Here a fight is held for its span.
- **The fourteen switch tuples' rules**: they are not read on this path.
- **Most of `policies.py`'s constants**: they became features or weights.

## The decision line

`branch` is `threat` on a fight, a stand or a retreat, `care` on a dress, `goal` on travel, loot or sneak, the needs step's own
branch, and none on rest. `inputs.x` and `inputs.y` come from `_read`.

`inputs.branches.<branch>` holds the executor's why:

- the maneuver's log;
- `flee` "retreat:door" on a retreat;
- `kill` on the tick a kill is read, and P30-C's `door_held`, whatever answered.

`inputs.intent` is `{kind, target}`: the scorecard's label and target. The kind starts `retreat:door` on a retreat, so
the line reads as a retreat and as a refuge, and reads `meet:stand` on the stand (a meet in place, never a retreat).
The target is the zombie id for a fight or a stand, the door square [x, y] for a retreat, and the goal's square for
travel, loot or sneak (its `stall_target`, else its args' square: fix 1, m6). A dress, the needs and the rest carry none, since a part
index is no square.

`inputs.utility` holds:

- `act`, `kind` and `target`;
- `scores`, as `{key: [total, {term: weighted}]}`;
- `vetoes` (`{key: why}`), `runner_up` and `margin`;
- `held_by` (`cadence`, `span` or `margin`) and `select` (`new`, `end`, `gone`, `beat`, `fresh`, `fallback` or
  `none`);
- `interrupts` and `end`;
- `ride`, `note` (`leg`) and `passed` (the act a fallback passed over) when set.

A score is a pure function of the logged features and the weights, so a ring can be rescored under new weights.
`tools/trial_score.py` reads `inputs.intent` for both label and target. It never reads `act` for a target, so the
`intent` key is used.

## Task 2's melee API (the one call site)

`execute.FightExec.melee_step` builds its `MeleeInputs` through `execute.melee_inputs`, which reads the class's
fields:

- Task 2's PZA/1.10 is `MeleeInputs(mode, reach, floor_swing)`: the meet, with no back step and no swing close.
- Today's PZA/1.9 is `(mode, reach, back, floor_swing, close_r)`, sent with back (0, 0) (no back leg: J4) and closeR 0
  (the swing within the reach, #4596).

The ends map both APIs:

- `dead` and `kill` mean the kill;
- `crowd` and `handback` mean the next selection fights the other zombie;
- `out of reach` and `lost`/`out of reach` mark the target for SEEK_SKIP_S;
- `lost`/`no progress` marks it for UNREACHABLE_S;
- anything else starts a new melee.

The replay ends an unbound melee on time only when it carries `seconds`, since PZA/1.10's has none.

## What it still needs from the harness (the Lua and the schema are frozen for Explore)

- **The window and the fence as filters.** The climb is a round trip this cut does not plan. Only door filters are
  generated, and the rings rarely offer one (no `group` line at all; with none, the stand).
- **The zombie's forward direction**, so the hazard could read "facing me" (the proposal's § 8).
- **The door read's health floor** (review m8): the reused P30-C read (`door_held.ThreatDoorHeld._door_held_read`, run
  in `Survive._read`) decides `stance_open` only at a health of FLEE_HEALTH_FLOOR or more, else `leave`; a health
  term outside the utility, at doors only. Taking the door decision into the utility is a later cut.
- **A composite Lua `dress` skill.** The Dress maneuver is three round trips.

## Risks (the proposal's, and what the build showed)

- **A closed-loop cycle.** Retreat lowers the hazard and the fight wins again at the filter. The open-loop replay
  cannot see it. The guards are the retreat's locked span, a held retreat staying eligible, and no retreat while on
  a filter.
- **Steps in the drag-down term.** The event still steps the scores by DRAG_HITS as the third zombie's predicted
  arrival enters a standing act's span. The first build's README said the commitment absorbs the step; the pinned
  lines showed it did not (F15 280 dropped the held fight at 1.33 tiles for travel, F15 326 had travel beat it). Fix 1
  takes the step off the fight whose target is in reach and off the stand, so F15 280 and 326 stay fights (a test);
  a fight farther off and a dress still carry it, and the commitment holds them only within their span and margin.
- **The goal's pull and the kill's worth are unset** (above). A trial may find the character standing where Angus
  wants it to loot, or sneaking past what it should clear.
- **The replay's goal** (`replay.ReplayGoals`): a line whose record holds no goal is read as a source pending, so the
  goal candidate holds there; live, the runner proposes or waits. The door test reads the send and names those lines
  as the replay's blind spot (fix 2, review-t11-utility-fix1 M3: E23 2 of 3, F6 72 of 72 door lines), never passing
  them as sends.
- **The swing that lowers nothing** is outside this framing: it is Task 2's meet.
