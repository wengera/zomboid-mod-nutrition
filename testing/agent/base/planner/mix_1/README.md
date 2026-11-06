# mix_1: the tactician with the seek and the crawler (Plan 31 Task 13)

The design is `task-13-composition-read.md` § 7's "mix_1" (in Plan 31's workspace), from round one's trials
(`testing/trials/trials.md`). mix_1 is the tactician package whole, plus one rule and one guard condition. Round two
reads it against the tactician unchanged, so the pair isolates the seek and the crawler.

`Survive(control="mix_1")` loads it. `prepare` is the tactician's (DOOR_HELD and GOAL_CONTINUE off on the instance).
`assess` runs `decide.Mix1`, a `tactician.decide.Tactician` kept on `survive.control_state["mix_1"]`. The mode is the
tactician's: `MODE` "model" with `PZA_TACTICIAN` overriding it, the table alone under `--no-llm`, and the doctrine's veto
on in model mode.

## What it took, and from where

| piece | source | how |
|---|---|---|
| the triggers, bounds, executors, `PlaySource`, the table's cells, the model source, the view, the guards `hit`, `swing` and `fallen` | `planner/tactician/` (829038d6) | inherited or imported, unchanged |
| the doctrine's rules `reach` to `unarmed`, `night` to `explore` | `tactician/fallback.py` | imported; `_tests` and `doctrine` copied into `rules.py` to insert `clear` |
| the rubric's three rules | `tactician/rubric.py` | copied into `rules.violations`, reading this package's `dress_due` |
| `Tactician.assess`, `Tactician._table_due` | `tactician/decide.py` | copied into `decide.Mix1`: they read the tactician's `rubric` and `table.bound` by module name |
| the lone zombie's reach | `engage.Engage._engageable` (Task 18 fix 1) | called on the Survive instance, never copied: its side, chase, line and flood reading, its `unsought` marks and its cached flood |
| the seek's predicate | `engage.Engage._sought` (P24-X), cut to one zombie after P24-AT's `_lone` | `rules.lone` and `rules.clear_target` |
| the re-pin margin | `policies.REPIN_MARGIN` 0.3 (P24-A fix 1) | a nearer crawler takes a running finish only by this much |

## The two pieces

### 1. `clear`: the ladder's lone-idle seek, as a doctrine rule

**When it fires.** All of these hold:
- the character is armed;
- there is no group (`fallback.is_group`);
- exactly one standing zombie is listed within ENGAGE_R 9, idle or aware (`rules.lone`);
- the instance's `_engageable` reads that zombie reachable.

The answer is `fight` at that zombie, why `clear`. The rule sits after `fight` and `unarmed` and before `night`. The
executor's `toward` leg walks to an idle zombie in the stance; a chaser is met standing.

**It binds** (`rules.clear_due`) whenever the doctrine fights that lone zombie. That is `clear` for an idle one, or the
tactician's `fight` rule for one coming within ENGAGE_R. The tactician's own `bound` leaves the second case to a
running travel until the zombie is within DANGER_R (E23 71.5-73.5 s: 26240 coming from 7.2 to 6.1 tiles). Binding has
three effects:
- No table cell answers over it.
- A running strategic play is replaced at once (the tactician's `rule` path).
- A running fight at another zombie re-pins to it, unless that fight is a finish at hand. F15's ring had a table fight
  at the idle 16038 at 9.9 tiles while the aware 16032 came at 8.7.

**The veto.** A model answer that is no fight is vetoed `lone_not_cleared`. A start that only this binding caused is
logged rule `clear`.

**Why.** Round one's tactician defect: an idle zombie beyond DANGER_R stood for 63 to 79 s (trial 4's 6073 at 8.4
tiles; trial 8's 25371 and 25372).

**Two or more within ENGAGE_R: no seek.** The `fight` rule's stand lets them come. That kept T's pair trial at 0 hits,
and it avoids U's trial-7 walk toward one of a pair.

### 2. The crawler, a threat at the dressing

**What it does.**
- A crawler within KEEP_R 2.5 blocks the dressing (`rules.keep_clear`, read by `bleed`'s test and by `dress_due`).
- The decider's `crawler` guard finishes it first. The guard runs after the tactician's three and fires when all of
  these hold:
  - nothing stands within KEEP_R (the standing first, the tactician's order);
  - the running play is no retreat;
  - no finish at hand is already running at a zombie on the floor as near, within REPIN_MARGIN.
- The executor's mode is `finish`.
- A running finish at hand is held against the table's answers, a retreat's excepted (`Mix1._fight_holds`). A finish
  at hand is a fight at a zombie on the floor within KEEP_R, a crawler or one knocked down, with nothing standing within
  KEEP_R. Without the hold, the tactician's table hands such a finish to a travel on a `down` trigger, and the guard then
  takes the crawler while the knocked-down zombie rises (trial 10's ring: 15436 at 0.9 tiles, the crawler at 2.2).
- A model answer that leaves the crawler for anything but a retreat is vetoed `crawler_first`.

**How a crawler reads.** In the frame, a crawler has `crawler` and `onFloor` both true (the zombie record in `schema/pza1.json`;
`rules.is_crawler`). In the tactical view it is `posture` "crawler" (`tactician.tview.posture`). Every crawler record in
the four rings read had both fields: 528 in trial 10, none in F15, E23 or trial 4.

**Why.** Round one's doctrine death, trial 10. The crawler 15465 lay at 1.0 to 1.1 tiles in `attack` and bit at 48.4,
50.5 and 63.4 s through the Dress. Every variant's `standing` drops a crawler. T's bleed rule had the same gap,
untested.

## What it drops

Nothing of the tactician's. The ladder's pull and its flee stay out: T already handles pairs by standing, and the pull
drifts with no leash (trial 5, 37 tiles).

## Constants

None is new, and none is changed. ENGAGE_R 9 (P24-X), DANGER_R 6, KEEP_R 2.5, LISTED_R 12 and REPIN_MARGIN 0.3 are
`policies`'. GROUP_N 3, SWING_GUARD_R 1.0, FIGHT_REACH 2.0, DRESS_MARGIN 1.0 and TABLE_HOLD_S 5 are the tactician's.

## The decision line

The tactician's keys stay on the line as they are: `play` `{kind, type, target, play_id}`, `tactician`, `branches`
(`threat.flee` the retreat's why), `need`, `consume_refused` and `cooled`.

`inputs.mix_1` is `{piece, added, started, kind, play, target, clear}`:
- `piece`: the running play's starter, the rule that decided the tick. It is one of `guard.hit`, `guard.swing`,
  `guard.fallen`, `guard.crawler`, `rule.<doctrine rule>` (`rule.clear` among them), `table` or `model`.
- `added`: true for mix_1's own pieces, `rule.clear` and `guard.crawler`.
- `started`: true on the tick its play began.
- `kind`: the scorecard's label (`tools/trial_score.py`). It is `fight`, `dress`, `loot`, `travel` or `shelter`, or a
  retreat naming its refuge: `kite_door`, `kite_shelter`, `kite_building`, `avoid_door`, `avoid_shelter` or
  `avoid_building`.
- `play`: the play type.
- `target`: a zombie id for a fight or a kite, the square [x, y] for the rest, or the part label for a dress.
- `clear`: the zombie id `clear` could fight this tick, else None.

`plays.log` beside `decision.log` keeps the tactician's three line kinds. `rule` is `clear` on a start the lone
zombie's binding alone caused, and `crawler` on the guard's.

## Observations for Harden (the Lua and the schema are frozen here)

The round's two Lua questions belong to the meet, not to any composition:
- **The point-blank presses.** 7 of 8 presses at d_press under 0.6 did nothing (round one, § 1.4).
- **The shove-only meet under arm pain.** After an arm bite, `body.armPain` over K.MELEE_SPENT_PAIN 10 turned the meet
  spent, and 7 of 8 shoves at 0.87 to 0.89 tiles did nothing (trial 11).

The crawler is finished by the meet's own finish (mode `finish`, the floor swing), the same as a knocked-down zombie.
Whether a crawler's lower head changes the floor swing's distance is not read.
