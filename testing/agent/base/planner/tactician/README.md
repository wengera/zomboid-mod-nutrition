The bench: the table does not tie the model under the 95 percent bar (68.8 % type agreement with the default model, sonnet, after fix 1's doctrine; 0 rubric violations against its 17), and the model's own agreement with itself (0.92 pairwise) bounds what any table could reach. T's trials run the model (sonnet). Wherever one of Angus's rules binds, the doctrine overrides the model and the running play on every tick, with one hysteresis in both modes: a running fight is kept against the dressing while a standing zombie reads within KEEP_R + DRESS_MARGIN (2.5 to 3.5 tiles). The table answers whenever no play runs, and alone under `--no-llm`.

# The tactician (Plan 31 Task 11, variant T)

The design is `rebuild-proposal-model-tactician.md` (in Plan 30's workspace) and spec § 3's T bullet. The model is asked
on a situation change for one **play** from a closed vocabulary. A play runs until its **bound** breaks. Angus's rules
answer at zero latency wherever they bind and whenever no play holds. Scripted guards take the tick in any play.

`MODE` in `decide.py` is "model"; `PZA_TACTICIAN=table|model` overrides it. The scripted goal source of `--no-llm`
always runs the table and makes no call of any kind. The bench below chose the mode.

## What it decides, and how

`assess(survive, inputs)` (`__init__.py` → `decide.Tactician`, kept on `survive.control_state["tactician"]`) runs each
2 Hz tick in this order:

1. **Triggers** (`trigger.py`). They are `notice`, `count`, `hit`, `wound`, `down`, `clear`, `arrived`, `need` and
   `ended`; each fires once per change, never on a clock. `count` fires on a band edge of the standing count within
   DANGER_R (0, 1, 2, 3+), and only once the new band has held COUNT_HOLD_S (fix 1, H3).
2. **The bound** of the running play (`executors.Exec.bound`). An end is logged and fires `ended`.
3. **The model** (model mode only, `source.py`).
   - A call starts on a trigger, at most one in flight. The rest coalesce, and the dirty flight is asked again when it
     lands.
   - Two starts are at least CALL_GAP_S apart; a trigger inside the gap stays due. After CALLS_MAX calls in a
     session, the table answers alone.
   - An answer is validated on the view it was asked on. Its labels are rebound by id to the moment's labels
     (`plays.rebind`): a zombie or door that is gone is refused `gone` (fix 1, H4).
   - It is vetoed `doctrine` when it breaks a rubric rule on the moment's view, and then the table's play takes over.
   - It is applied when it names a play or a target id other than the running one's.
4. **Guards** (scripted, any play).
   - `hit`: a hit reaction with a standing zombie within the melee's release; the melee takes the tick.
   - `swing`: a standing zombie within SWING_GUARD_R 1.0; the melee starts.
   - `fallen`: in a fight at a standing target, a fallen zombie within FIGHT_REACH and none standing within KEEP_R; it
     is finished first.
5. **The table** (`table.py`, `decide._table_due`) answers when:
   - no play runs;
   - a model answer was vetoed;
   - one of Angus's rules binds the moment's view and the running play is of another type (fix 1, H1: on every tick, in
     both modes);
   - in table mode, on an interrupt trigger (`hit`, `wound`, `down`, `count`, `arrived`), or on any trigger once the
     play has run TABLE_HOLD_S (fix 1, M2, the hysteresis).

   A running fight is kept in two cases. Against the dressing, while a standing zombie reads within KEEP_R +
   DRESS_MARGIN, on the `rule`, `trigger` and `veto` paths alike (fix 2, L1). Against a trigger's strategic play, while
   its target stands within ENGAGE_R chasing. A play the doctrine takes (`rule`, `veto`) is logged ended `doctrine` in
   `plays.log` (fix 2, L2).

   Where a rule binds, the doctrine answers whatever a cell holds: one standing zombie within DANGER_R while armed, or
   a bleed with nothing standing within KEEP_R and something to dress with. Elsewhere a labelled cell's play answers,
   else the doctrine. With no rule answering, the strategic goal layer runs (`travel` to `explore`).
6. **The play steps** (`executors.py`). Its (branch, owner, command, why) is the `Decision`.

### The doctrine

The rules, in order (`fallback.RULES`):

- **`reach`**: armed, with a standing zombie within KEEP_R → fight it.
- **`bleed`**: a bleed, nothing standing within KEEP_R, and something to dress or tear → dress the worst part with a
  bandage, else a rag, else a rip.
- **`group`** → kite toward a refuge while any stands within DANGER_R, else avoid toward one. A group is any of:
  - three or more standing within DANGER_R;
  - three or more aware within 12, unless exactly one stands within DANGER_R while armed;
  - two within DANGER_R while unarmed.
- **`fight`**: armed, with one or two standing within DANGER_R, or one or two coming within ENGAGE_R 9 → fight the
  nearest.
- **`unarmed`** → kite.
- **`night`** → shelter.
- **`goal`**, **`loot`**, **`travel`**, **`explore`** → the strategic layer.

A refuge is a listed door within DOOR_VIEW_R that has no zombie at it and no standing zombie within DANGER_R in its
compass eighth or either neighbour. Failing a door, a shelter building placed the same way counts.

With no refuge there is no retreat, only the stand: the nearest standing zombie is fought where the character stands,
and the arrivals one at a time. This is the controller's refuge ruling, the doctrine variant's too. There is never an
open-ground leg. A target beyond WALK_R is faced in the stance where the character stands, never walked to, and a
chaser beyond DISENGAGE_R is held so, never ended `lost` (fix 2, N1: the stand against a far group walked at it and
restarted every tick).

## The plays and their executors (`plays.json`, `executors.py`)

| play | args | executor | bound (ends) |
|---|---|---|---|
| `fight` | target Z | The shared `Melee` within MELEE_RELEASE_R (one call site, `melee_step`). Beyond it and within WALK_R, the stance facing the target: standing for a chaser, walking toward an idle one; a walk to its square when the line is blocked: through a door, never a wait. Beyond WALK_R, the stance held where the character stands (fix 2). | `dead`; `second_standing` (a nearer standing zombie within KEEP_R, or the meet's `handback`); `lost` (an idle target beyond DISENGAGE_R, left unreachable; the meet's `lost` for no progress, out of reach or refused, fix 2 L5; or a walk to it that failed: the door marked once, the zombie left unreachable and out of the table's read, fix 1, M3). Never on health. |
| `kite` | target Z, toward D/B/`stance` | `Aim` facing the target. It moves only along the refuge's heading while that runs away from the zombies and reads clear. Else, and with `stance`, it holds where it stands (fix 1, H2). | `alone` (armed, one standing within DANGER_R: then fight), `reach` (armed, a standing zombie within KEEP_R: then fight, fix 2, L6), `reached`, `time` (KITE_S 8) |
| `avoid` | toward D/B, gait | `night.shelter_plan`/`shelter_step` (approach, open, enter, close), at a run with a chaser near, else a walk (the sneak gait) | `reached`, `shun`, `contact` (a standing zombie within KEEP_R), `alone` (armed, one standing within DANGER_R: fix 1, H1), `clear` |
| `dress` | part P, with | The shared `Dress` maneuver (stop, tear, bandage), no ride | `dressed`; `nothing` (then no new dress of that part until an item is added or `care.DRESS_RETRY_S` pass); `contact` |
| `loot`, `travel`, `shelter` | building / place / building | Survive's lower steps in the ladder's order (care, need, load, night, the rag stock, goal). The goal runner and its source (scripted, or the LLM's) choose. A model's play pins its goal once (`PlaySource`). | the pinned goal's end (`looted`, `arrived`, `inside`; `stuck` when it failed or was refused); `contact` |

An answer is one JSON object `{play, <args>, bound, why}`:

- every arg is a label the view lists or a closed enum;
- `why` is one of `lone_chaser|group|bleeding|unarmed|need|door|night|clear`;
- any other key is refused `extra_key` (no free text, P28-K).

Labels are distance ranks. The decider and the source bind them through `tview.binding` to the zombie's online id,
the door's square, the building's id or the part's index, and compare plays by those ids (fix 1, H4).

## The calls per session (fix 1, H3)

The open-loop estimate (`.superpowers/sdd/2026-11-05-plan-31-the-rebuild/task-11-tactician-fix-1-calls.json`) uses
the package's triggers at 2 Hz over the rings, one call in flight, the dirty flight re-asked, the gap and the cap. At
sonnet's p50 of 4.42 s:

| session | goal calls today | calls with no gap (banded, held count) | calls with CALL_GAP_S 15 and CALLS_MAX 48 | times today |
|---|---|---|---|---|
| F15 | 20 | 77 | 36 | 1.8 |
| F14 | 28 | 104 | 48 (the cap) | 1.71 |
| E23 | – | 53 | 20 | – |

Before the fix the count was 99 on F15 and 108 on F14. The figures are the same at p95's 7.16 s. They come on top of
the strategic LLMSource's own goal calls, on the account the agents share (F6's exit 1).

## What it drops of the ladder, and why

The decider layer goes; each decision is now a play's:

- `threat.py`'s ladder and its hysteresis: `held`, `pair`, `flip`, `many`, `health`, `strain`, `unreachable`,
  REFIGHT_MARGIN, P29-E, P29-G. F15 fled all 27 fights on these.
- `hold.py`: the endurance and arms holds, whose reads are now view fields.
- `still.py` (P30-E).
- `pull.py` and `engage.py`'s seek: the `fight` rule's ENGAGE_R reach replaces them.
- `door_held.py`'s decision (P30-C): `DOOR_HELD` is off on the instance.
- `care_yield.py`: the dressing is a play of its own.
- `goal_policies.py`'s GOAL_CONTINUE and the hop extension (P30-B): off on the instance.
- `survive.py`'s branch order.

`prepare(survive)` (exported by the package, `decide.prepare`) switches DOOR_HELD and GOAL_CONTINUE off on the
instance; `Survive._read` copies GOAL_CONTINUE into the goal runner every tick. The fork's construction hook on main
(`control.prepare_of`, called at the end of `Survive.__init__`) finds it, so the switches are off before the first
`_read`. `assess` also calls it on every tick, which covers a tree without the hook from the second tick on (fix 2,
N2).

Kept:

- the World, the Actions and the Lua skills;
- `Melee` and `Dress`;
- the night's shelter machine;
- the goal runner and its sources;
- the care branch's stock and wear;
- the need and the load;
- the sneak gait (`sneak.SneakGait`).

## Constants and their sources

- **`trigger.py`**:
  - NOTICE_R: `policies.LISTED_R` 12 (#4268).
  - NOTICE_GAP_S 10 and CLEAR_S 5: the proposal § 2.
  - COUNT_TOP 3: fallback.GROUP_N.
  - COUNT_HOLD_S 1: the review's "hold it for about 1 s".
  - CLOSING_WINDOW_S 1.5 and CLOSING_MIN_S 0.4: first guesses for the trials.
  - THIRST_T (#0509), HUNGER_T (#0508), `night.TIRED_T`.
- **`fallback.py`**: GROUP_N 3 (the common amendments' item 5); UNARMED_GROUP_N 2 (the proposal); DANGER_R, KEEP_R,
  ENGAGE_R (P24-X) and LISTED_R from `policies`.
- **`table.py`**: HEALTH_BANDS 40 and 70, the ladder's flee lines rounded up.
- **`executors.py`**:
  - SWING_GUARD_R 1.0: P30-A's SWING_CLOSE_R.
  - DOOR_NEAR_R 1.5: survive.DOOR_NEAR_R.
  - KITE_S 8, REACHED_R 1.5, WALK_R 10: first guesses.
  - AIM_LEG_S, MELEE_RELEASE_R, ATTACK_MARGIN, UNREACHABLE_S from `policies`.
- **`decide.py`**:
  - INTERRUPTS.
  - TABLE_HOLD_S 5 and DRESS_MARGIN 1.0: first guesses.
  - CALL_GAP_S 15 and CALLS_MAX 48: fitted on the estimate above.
  - REFUGE_HOLD_S 60: a first guess.
  - `care.DRESS_RETRY_S`.
- **`source.py`**: TACTIC_TIMEOUT_S 15.
- **`tview.py`**: ZOMBIES_N 8 and MAP_N 21 (the proposal); DOORS_N and BUILDINGS_N 6; DOOR_VIEW_R 25; DOOR_NEAR_R 3.

No constant asserts an engine mechanism.

## The decision line and the scorecard's labels

`inputs.play` is `{kind, type, target, play_id}`:

- `kind` is `fight`, `dress`, `loot`, `travel` or `shelter`, or a retreat label: `kite_door`, `kite_shelter`,
  `kite_building`, `kite_stance`, `avoid_door`, `avoid_shelter` or `avoid_building`. `_shelter` appears only for a
  building with a shelter plan (fix 1, L3).
- `target` is a zombie id (fight, kite) or a square; a dress has none.

`inputs.tactician` is `{play, target, source, bound, age, rule, triggers, play_id, mode, guard, ended, refused, table,
capped, walk_failed}`.

`branch` is "threat" on a fight, kite or avoid tick, with `branches.threat.flee` holding the retreat's why on a kite
or avoid. It is "care" on a dress tick, and the ladder step's own branch on a strategic tick.

`plays.log` sits beside `decision.log`, with three kinds of line:

- `play`: `{play_id, play, source, rule, triggers, applied_at}`;
- `call`: `{trigger, view, answer, play, refused_why, latency_s, model, coalesced, applied_at, source}`;
- `play_end`: `{play_id, end, bound_broken, aids}`.

## The bench (`tools/tactician_bench.py`, `data/fits/tactician-bench.json`)

The commands are `python tools/tactician_bench.py views | record | score [--write-table] | check`; `check` is
read-only.

- **The views**: 200 trigger views from the 19 rings (F2 to F15, E19 to E23; 3669 trigger points). They were chosen
  round-robin over 14 classes, with the recording's triggers (`Triggers(banded=False)`).
- **The calls**: 450 real `claude -p` calls in one sitting: 200 haiku, 200 sonnet, and 50 for self-agreement (k = 3
  on 25 views of sonnet). None failed and none was limited.
- **Rescored after fix 1**: the answers are as recorded; the doctrine and the table are re-read under the stand
  ruling.

| chooser | valid | rubric violations | type agreement with sonnet | type and target | with haiku | latency p50 / p95 / p99 (s) |
|---|---|---|---|---|---|---|
| doctrine (`fallback.py`) | 1.000 | 0 | 0.653 | 0.613 | 0.584 | 0 |
| table, leave one ring out | 1.000 | 0 | **0.688** | 0.628 | 0.584 | 0 |
| table, in sample (`table.json`, 31 cells) | 1.000 | 0 | 0.754 | 0.668 | 0.650 | 0 |
| ladder (the recorded line, as a play type) | 0.985 | 63 (45 bleeds not dressed, 18 lone not fought) | 0.439 | – | 0.392 | – |
| haiku | 0.985 | 39 (38 bleeds not dressed) | 0.741 | 0.726 | – | 4.16 / 7.13 / 8.91 |
| sonnet (the default) | 0.995 | 17 (13 bleeds not dressed, 4 lone not fought) | – | – | 0.741 | 4.42 / 7.16 / 7.69 |

Sonnet's self-agreement on play type over k = 3 and 25 views:

- pairwise: 0.92;
- the first two samples only: 0.96;
- all three the same: 0.88.

All three disagreements were kite against avoid. This is the like-for-like ceiling on 25 views, and the table's 0.688
is well under it.

The stand ruling lowered the doctrine's and the table's agreement with the model (from 0.678 and 0.754 before fix 1).
Where no refuge is listed the doctrine stands and fights, while sonnet kites or avoids toward the stance or an
unnamed building.

Neither configuration passes the proposal's pick, which needs violations no worse than the reference's and a p95
under 7.1 s: haiku has 39 violations, and sonnet's p95 is 7.16 s. So the model runs where it may add something, the
ambiguous middle: the veto removes its 17 violations, and the running play is held to the same rules every tick.
`PZA_TACTICIAN=table` runs the table alone, the trial to compare it with.

## The Melee call site, and what it needs from the harness

The fight's one Melee call is `executors.melee_step`:

- on Task 2's PZA/1.10 meet (`4d646a0a`), `MeleeInputs(mode, reach, floor_swing)`;
- on today's PZA/1.9 melee, the back leg (0, 0) and the swing close SWING_GUARD_R.

The two are told apart by `MeleeInputs`' fields (`MELEE_API`). The meet's ends map onto the fight's bounds: `kill` →
`dead`, `handback` → `second_standing`, `lost` (no progress or out of reach) → `lost`.

The Lua and the schema are frozen for this variant. It would want:

- a window as a refuge;
- a fence filter;
- a frame-rate guard in the reflex, if the 2 Hz guard proves late.
