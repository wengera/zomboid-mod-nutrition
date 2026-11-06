# The situation utility (Plan 31 Task 11, variant U)

`Survive(control="utility")`. The design is the proposal `rebuild-proposal-situation-utility.md` (Plan 30's workspace)
and the spec's § 3 U bullet. A trial build (ruling P31-T): nothing here is evidence, and no row cites it.

## What it decides and how

About once a second (`select.SELECT_S`), and at once on an interrupt, it scores six to ten candidate acts and holds
the best one. The candidates are `fight:<id>` (the three nearest standing zombies within ENGAGE_R, every fallen one
within FINISH_R, and the held fight's own target out to DISENGAGE_R), `dress:<part>`, `retreat:door:<x>,<y>` (to
each door filter), `travel` or `loot` (the goal runner's goal), `sneak`, `needs:<branch>` and `rest`. `acts.py`
generates them and `features.py` reads the frame they are built from.

Each score is a sum of named terms (`select.terms`), linear in five weights, with H, the cost of one hit, as the unit:

| term | weight | what it is |
|---|---|---|
| `kill` | K | P_kill, the chance of the kill within the act's span |
| `hit` | H = 1 | minus the expected hits over the span (for a retreat, the hits it saves) |
| `bleed` | B | bleeding part-minutes: the dress credits the bleed it stops, every other act pays for its span |
| `chase` | C | 1 for a fight at a standing aware zombie while armed: a lone chaser always scores the fight |
| `goal` | V | the goal's progress (the needs at NEED_VALUE, the rest by the endurance level) |
| `regress` | G | minus the tiles a retreat runs off the way, over 10 |

The held act is kept for its minimum span (a fight 4 s or until its target ends, a dress until done, a travel 3 s,
a retreat until it reaches its filter). After the span, a rival replaces it only when it beats the held act by
delta = 0.3 + 0.2·|U_held|.

Four interrupts re-score at once and lift the span: a new hit reaction, a part newly bleeding, a standing zombie
other than the target entering 1.5 tiles, and a goal answer. The act's own end is the fifth. No interrupt lifts a
retreat's span: the run goes to its filter and ends in the stance there, and no retreat is generated while the
character stands on that filter. A held act stays eligible whatever its score, so a retreat already taken is not
dropped when the group's count changes its score on the way.

Two vetoes sit outside the utility, as feasibility. The first is an unreachable target: the planner's `unreachable`
and edge marks, this package's own `out of reach` marks, a known blocked edge with no door passing it, or a door the
door read decided to `leave`. The second is the ride: a leg part's bandage never rides a walk [#4337]. A retreat
scoring at or under 0 saves no hits; it would be an open-ground leg, so it is never chosen. There is no flee act and
no wait act.

The executors (`execute.py`) run the held act through the shared plays:

- `fight`: the `Melee` maneuver within KEEP_R. Its mode is `finish` at a fallen target, `shove` when spent (the arms'
  pain over 10, or the endurance or tired moodle at level 2: the spec's § 4 2b) and `strike` otherwise. Farther off
  it uses the stance: `Aim` standing facing an aware chaser (it comes to the character), `Aim` walking toward an
  unaware or fallen zombie, a walk beyond 6 tiles, or a route through the door of a known blocked edge. A zombie
  behind a closed door that the door read opens gets P30-C's post, open and meet (`door_held.FightDoorHeld`).
- `dress`: the `Dress` maneuver: stop, tear, bandage, riding the walk for a part above the legs.
- `retreat`: a run (`WalkTo` at a run) to the post inside the door's threshold (`policies.stand_post`).
- `travel`, `loot` and `sneak`: the goal runner (`Survive._goal`). The sneak posture is SneakGait's, sent when the
  tick is sent.
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
- the drag-down price, DRAG_HITS = 3 per aware zombie past the second arriving within a standing span [#4290,
  #4291]. The rings hold no drag-down to fit one on.

## The weights (`weights.py`, the linear program's chosen point)

The verdict set is the aligned decision lines of F2 to F15 and E19 to E23, labelled by Angus's directions. Each
labelled line is a ranking row: U(labelled) ≥ U(other) + 0.1. That gives 9696 rows from 7575 labelled lines and
66177 candidates scored. The rules are `one` (4098 lines), `dress_quiet` (2623), `dress_far` (676), `sneak` (165,
structural: all held), `group` (0: no line had three aware zombies within KEEP_R and a filter), `group_coming` (13)
and `door` (1851 lines, structural: no wait candidate exists).

| weight | value (Chebyshev centre) | feasible interval |
|---|---|---|
| K | 3.712 | [1.491, 7.835] |
| B | 1.092 | [0.382, 1.683] |
| C | 3.347 | [0.260, 6.002] |
| G | 0.342 | [0, 3.451], at its lower bound |
| V | 0.499 | [0, 1.645], at its lower bound |

The radius is 0.342 and the least slack is 0.35. Every weight's ±5 % probe moves labelled lines: K 4111, B 4380, C
3829, G 19, V 6311.

The first program was empty, and three readings made the region non-empty:

1. Rule `one`'s exclusions follow the spec's 2b: a spent character seeks no unaware zombie, and a group listed is not
   "one zombie".
2. The dress rules rank the dress over everything except a fight. The memory says "before the goal and any flee",
   not before a fight.
3. The group rules rank the retreat over fights beyond KEEP_R only, since the doctrine's first word is that a zombie
   in reach is struck.

With these, the tool reports conflicts by rule pairs and resolves none of them. The verdicts were also inconsistent
with the model in one structural way: a fallen zombie's hazard was read at d ≈ 0, and is now floored at MELEE_D.

## The constants with their sources

Every module constant carries its source on its line: a row by id, a memory, or "a first guess for the trials".
The first guesses are:

- spans and margins: SELECT_S, DELTA0, the spans;
- timings and paces: SHOVE_CYCLE_S, STANCE_PACE, CHASE_MIN, DRESS_HELD_S / DRESS_TEAR_S, ROUTE_S;
- shares and prices: STOMPS_PER_DOWN, FALLEN_FACTOR, UNAWARE_FACTOR, NOTICE_HITS, BLEED_HORIZON_M, DRAG_HITS;
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

`branch` is `threat` on a fight or a retreat, `care` on a dress, `goal` on travel, loot or sneak, the needs step's own
branch, and none on rest. `inputs.x` and `inputs.y` come from `_read`.

`inputs.branches.<branch>` holds the executor's why:

- the maneuver's log;
- `flee` "retreat:door" on a retreat;
- `kill` on the tick a kill is read, and P30-C's `door_held`, whatever answered.

`inputs.intent` is `{kind, target}`: the scorecard's label and target. The kind starts `retreat:door` on a retreat, so
the line reads as a retreat and as a refuge. The target is the zombie id for a fight, the door square [x, y] for a
retreat, and the goal's square for travel, loot or sneak. A dress, the needs and the rest carry none, since a part
index is no square.

`inputs.utility` holds:

- `act`, `kind` and `target`;
- `scores`, as `{key: [total, {term: weighted}]}`;
- `vetoes` (`{key: why}`), `runner_up` and `margin`;
- `held_by` (`cadence`, `span` or `margin`) and `select` (`new`, `end`, `gone`, `beat`, `fallback` or `none`);
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
  generated, and the rings rarely offer one (no `group` line at all).
- **The zombie's forward direction**, so the hazard could read "facing me" (the proposal's § 8).
- **A composite Lua `dress` skill.** The Dress maneuver is three round trips.

## Risks (the proposal's, and what the build showed)

- **A closed-loop cycle.** Retreat lowers the hazard and the fight wins again at the filter. The open-loop replay
  cannot see it. The guards are the retreat's locked span, a held retreat staying eligible, and no retreat while on
  a filter.
- **Cliffs in the drag-down term.** The term is a step as the third zombie's arrival crosses the span, so the scores
  jump by DRAG_HITS between ticks; the commitment absorbs it. With a group coming and no filter, standing acts go
  negative and travel (moving, no drag) wins. That reads as walking on toward the goal's named target, not an
  aimless leg, but the scorecard's `away` minutes will show it.
- **K is capped only by `group_coming`'s 13 lines.** A first session may find the fight optimistic under a group.
- **The swing that lowers nothing** is outside this framing: it is Task 2's meet.
