The bench: the table does not tie the model (75.4 % type agreement with the default, sonnet, against the 95 % bar; 0 rubric violations against its 17): T's trials run the model (sonnet) with the doctrine's veto, the table answering at zero latency meanwhile and alone under `--no-llm`.

# The tactician (Plan 31 Task 11, variant T)

The design is `rebuild-proposal-model-tactician.md` (Plan 30's workspace) and spec § 3's T bullet. The model is asked
on every situation change for one **play** from a closed vocabulary; a play runs until its **bound** breaks; Angus's
rules answer at zero latency whenever no play holds; scripted guards take the tick in any play. Whether the model or
the cached table answers is the bench's verdict above (`MODE` in `decide.py`, `PZA_TACTICIAN=table|model` overrides;
the scripted goal source of `--no-llm` always runs the table, no call of any kind).

## What it decides, and how

`assess(survive, inputs)` (`__init__.py` → `decide.Tactician`, kept on `survive.control_state["tactician"]`), each
2 Hz tick:

1. **Triggers** (`trigger.py`): `notice`, `count`, `hit`, `wound`, `down`, `clear`, `arrived`, `need`, `ended`, each
   once per change, never a clock.
2. **The bound** of the running play (`executors.Exec.bound`); an end is logged and fires `ended`.
3. **The model** (model mode, `source.py`): a call starts on a trigger, one in flight, the rest coalesced (the flight
   marked dirty and asked again at once when it lands); its answer is validated against the view of the tick it
   lands on (`plays.validate`: a zombie that died since is `unknown_label`), vetoed `doctrine` when it breaks a rubric
   rule there (`rubric.violations`), and applied when it names another play or target; a refusal's why reaches the
   next view once.
4. **Guards** (scripted, any play): `hit` (a hit reaction with a standing zombie within the melee's release: the
   melee takes the tick), `swing` (a standing zombie within SWING_GUARD_R 1.0: the melee starts), `fallen` (in a
   fight at a standing target, a fallen zombie within FIGHT_REACH and none standing within KEEP_R: finished first).
5. **The table** (`table.py`) on a trigger, or with no play: a labelled cell's play, else the doctrine
   (`fallback.py`); where one of Angus's rules binds (one standing zombie within DANGER_R while armed; a bleed with
   nothing standing within KEEP_R and something to dress with) the doctrine answers whatever the cell holds, so the
   table never breaks a rule. With no rule answering, the strategic goal layer runs (`travel` to `explore`).
6. **The play steps** (`executors.py`) and its (branch, owner, command, why) is the `Decision`.

The doctrine (`fallback.RULES`, in order): `reach` (armed, a standing zombie within KEEP_R → fight it), `bleed` (a
bleed, nothing standing within KEEP_R, something to dress or tear → dress the worst part: bandage, else rag, else rip),
`group` (three or more standing within DANGER_R, or three or more aware within 12 unless exactly one stands within
DANGER_R while armed, or two within DANGER_R unarmed → kite toward a refuge while any stands within DANGER_R, else
avoid toward one), `fight` (armed, one or two standing within DANGER_R or coming within ENGAGE_R 9 → fight the
nearest), `unarmed` (→ kite), `night` (→ shelter), `goal`, `loot`, `travel`, `explore` (the strategic layer). A refuge
is a listed door with no zombie at it and no standing zombie within DANGER_R in its compass eighth or either
neighbour, else such a shelter building; with none, a kite holds the stance (`toward` "stance"), never an open-ground
leg.

## The plays and their executors (`plays.json`, `executors.py`)

| play | args | executor | bound (ends) |
|---|---|---|---|
| `fight` | target Z | the shared `Melee` within MELEE_RELEASE_R (one call site, `melee_step`); beyond it the stance facing the target, standing for a chaser, walking toward an idle one; a walk to its square when the line is blocked (a door: the path opens it, never a wait) | `dead`, `second_standing` (a nearer standing zombie within KEEP_R, or the meet's `handback`), `lost` (beyond DISENGAGE_R, or the meet's `lost` for no progress or out of reach); never health |
| `kite` | target Z, toward D/B/`stance` | `Aim` facing the target with a move vector toward the refuge while that runs away from the zombies, else away, turned to a clear heading (never across a fence) | `alone` (armed, one standing within DANGER_R: then fight), `reached`, `time` (KITE_S 8) |
| `avoid` | toward D/B, gait | `night.shelter_plan`/`shelter_step` (approach, open, enter, close), at a run with a chaser near, else a walk (the sneak gait) | `reached`, `shun`, `contact` (a standing zombie within KEEP_R), `clear` |
| `dress` | part P, with | the shared `Dress` maneuver (stop, tear, bandage), no ride | `dressed`, `nothing` (then no new dress of that part until an item is added or `care.DRESS_RETRY_S` pass), `contact` |
| `loot`, `travel`, `shelter` | building / place / building | Survive's lower steps in the ladder's order (care, need, load, night, the rag stock, goal): the goal runner and its source (scripted, or the LLM's) choose; a model's play pins its goal once (`PlaySource`) | the pinned goal's end (`looted`, `arrived`, `inside`; `stuck` failed or refused), `contact` |

An answer is one JSON object `{play, <args>, bound, why}`, every arg a label the view lists or a closed enum, `why`
one of `lone_chaser|group|bleeding|unarmed|need|door|night|clear`; any other key is refused (`extra_key`: no free
text, P28-K).

## What it drops of the ladder, and why

The decider layer, each decision now a play's: `threat.py`'s ladder and its hysteresis (`held`, `pair`, `flip`, `many`,
`health`, `strain`, `unreachable`, REFIGHT_MARGIN, P29-E, P29-G: F15 fled all 27 fights on these, 211 of its 298 flee
lines with one standing zombie or none within 6 tiles); `hold.py` (the endurance and arms holds: their reads are view
fields, `endurance`, `armPain`); `still.py` (P30-E); `pull.py` and `engage.py`'s seek (the `fight` rule's ENGAGE_R
reach replaces the seek); `door_held.py`'s decision (P30-C: `survive.DOOR_HELD` off on the instance; a door is a
`fight` through it or a retreat by another way); `care_yield.py` (P29-D, P30-F: the dressing is a play of its own,
ahead of every retreat from a zombie beyond KEEP_R); `goal_policies.py`'s GOAL_CONTINUE and the hop extension (P30-B:
`survive.GOAL_CONTINUE` off on the instance; the strategic layer walks only to a named goal); `survive.py`'s branch
order. Kept: the World, the Actions, the Lua skills, `Melee` and `Dress`, `night.py`'s shelter machine, the goal
runner and its sources, the care branch's stock and wear, the need and the load, the sneak gait (`sneak.SneakGait`,
applied by `Survive._apply` on every Decision).

## Constants and their sources

`trigger.py`: NOTICE_R = `policies.LISTED_R` 12 (#4268), NOTICE_GAP_S 10 and CLEAR_S 5 (the proposal § 2),
CLOSING_WINDOW_S 1.5 and CLOSING_MIN_S 0.4 (first guesses for the trials), THIRST_T 0.12 (#0509), HUNGER_T 0.15
(#0508), `night.TIRED_T`. `fallback.py`: GROUP_N 3 (the common amendments' item 5), UNARMED_GROUP_N 2 (the proposal's
fallback rule 2), `policies.DANGER_R`, KEEP_R, ENGAGE_R (ruling P24-X), LISTED_R. `table.py`: HEALTH_BANDS 40 and 70
(the ladder's FLEE_HEALTH 40 and FLEE_HEALTH_PAIR 60 rounded up). `executors.py`: SWING_GUARD_R 1.0 (P30-A's
SWING_CLOSE_R, which Task 2 removes from `policies`), KITE_S 8, REACHED_R 1.5, WALK_R 10 (first guesses for the
trials), `policies.AIM_LEG_S`, MELEE_RELEASE_R, ATTACK_MARGIN (P27-M), STEER_TURNS, UNREACHABLE_S. `decide.py`:
REFUGE_HOLD_S 60 (a first guess), `care.DRESS_RETRY_S`. `source.py`: TACTIC_TIMEOUT_S 15 (a first guess against the
proposal's notice-to-contact medians, 9.6 to 21.3 s, desk reads). `tview.py`: ZOMBIES_N 8, MAP_N 21 (the proposal),
DOORS_N and BUILDINGS_N 6 (`view.BUILDINGS_SHOWN`), DOOR_VIEW_R 25, DOOR_NEAR_R 3 (first guesses). No constant asserts
an engine mechanism.

## The decision line and the scorecard's labels

Beside the ladder's own keys (`need`, `consume_refused`, `cooled`, `branches`, `x`, `y`), every line carries:
- `inputs.play` `{kind, type, target, play_id}`: `kind` the scorecard's label (`fight`, `dress`, `loot`, `travel`,
  `shelter`, and a retreat `kite_door`, `kite_shelter`, `kite_stance`, `avoid_door`, `avoid_shelter`: RETREAT_LABELS
  prefixes, the refuge's kind a REFUGE_WORDS word), `target` a zombie id (fight, kite) or the square it heads to (none
  on a dress).
- `inputs.tactician` `{play, target, source, bound, age, rule, triggers, play_id, mode, guard, ended, refused}`.
- `branch` "threat" on a fight, kite or avoid tick, `branches.threat.flee` the retreat's why on kite and avoid; "care"
  on a dress; the ladder step's branch on a strategic tick.

`plays.log` beside `decision.log`: `play` lines `{play_id, play, source, rule, triggers, applied_at}`, `call` lines
`{trigger, view, answer, play, refused_why, latency_s, model, coalesced, applied_at, source}` and `play_end` lines
`{play_id, end, bound_broken, aids}`.

## The bench (`tools/tactician_bench.py`, `data/fits/tactician-bench.json`)

`python tools/tactician_bench.py views | record | score [--write-table]`. 200 trigger views from the 19 rings
(F2 to F15, E19 to E23: 3669 trigger points, chosen round-robin over 14 classes of the standing count within DANGER_R, a
standing zombie within KEEP_R and a bleed, so the fights and bleeds dominate: the doctrine answers fight 102, dress 54,
kite 35, loot 6, avoid 2, travel 1). 450 real `claude -p` calls in one sitting (200 haiku, 200 sonnet, 50 for the
self-agreement: k = 3 on 25 views of sonnet, the amendments' "k = 3 on 50 views" not fitting their own 450), none
failed, none limited; the answers are recorded in `data/fits/tactician-bench.json` and every score reads them.

| chooser | valid | rubric violations | type agreement with sonnet | type and target | with haiku | latency p50 / p95 / p99 (s) |
|---|---|---|---|---|---|---|
| doctrine (`fallback.py`) | 1.000 | 0 | 0.678 | 0.633 | 0.569 | 0 |
| table, leave one ring out | 1.000 | 0 | **0.754** | 0.683 | 0.574 | 0 |
| table, in sample (`table.json`, 31 cells) | 1.000 | 0 | 0.809 | 0.719 | 0.629 | 0 |
| ladder (the recorded line, as a play type) | 0.985 | 63 (45 bleeds not dressed, 18 lone not fought) | 0.439 | - | 0.392 | - |
| haiku | 0.985 | 39 (38 bleeds not dressed) | 0.741 | 0.726 | - | 4.16 / 7.13 / 8.91 |
| sonnet (the default) | 0.995 | 17 (13 bleeds not dressed, 4 lone not fought) | - | - | 0.741 | 4.42 / 7.16 / 7.69 |

Sonnet's self-agreement over k = 3 is 0.88 (25 views), below the 95 % bar: no table could tie it, and the table agrees
with it as well as haiku does (0.754 against 0.741). The disagreements, the doctrine's rule against sonnet's play:
group kite → avoid 17 (both retreats, the model walking off where the doctrine backpedals), reach fight → kite 13 (a
zombie within KEEP_R in a group), bleed dress → fight 12 (a rule broken), group kite → fight 9. Neither configuration
passes the proposal's pick (violations no worse than the reference's and p95 under F14's notice-to-contact p25 7.1 s,
a desk read): haiku has 39 violations, sonnet's p95 is 7.16 s. So the model runs where it may add something, the
ambiguous middle: the decider refuses (`doctrine`) any model answer that breaks a rubric rule on the moment's view,
which removes the 17 by construction, and the table stands in while a call is out. `PZA_TACTICIAN=table` runs the
table alone (the doctrine and the 31 labelled cells), the trial to compare it with.

## The Melee call site, and what it needs from the harness

The fight's one Melee call is `executors.melee_step`: on Task 2's PZA/1.10 meet (`MeleeInputs(mode, reach,
floor_swing)`, no back leg, no closeR, no time end; ends `kill`, `handback`, `lost`) it passes the three; on today's
PZA/1.9 melee it passes the back leg (0, 0) and the swing close SWING_GUARD_R. The two are told apart by
`MeleeInputs`' fields (`MELEE_API`); the meet's ends map onto the fight's bounds (`kill` → `dead`, `handback` →
`second_standing`, `lost` for no progress or out of reach → `lost`). The Lua and the schema are frozen for this
variant; it would want: a window as a refuge (the `window` act through `night.window_exits`, not yet a play's
executor), a fence filter (no hoppable edge is a refuge yet), and, if the 2 Hz guard proves late (hits taken in
non-fight plays), a frame-rate guard in the reflex. The model mode's calls share Angus's account with the agents
(the bench's `limited` read stops at the first exit 1 or 429).
