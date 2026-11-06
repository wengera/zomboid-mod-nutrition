# The composition mix_2 (Plan 31 Task 13)

`Survive(control="mix_2")` (the fork, `planner/control.py`). The design is section 7 of round one's composition read
(`task-13-composition-read.md` in Plan 31's workspace): the doctrine's arbiter (D) with the tactician's (T) crowd guards
in place of D's one-press Strike, T's re-pin, T's dress-waits rule with the crawler read as a threat, and the ladder's
(L) lone-idle seek. It drops D's string and D's Strike, and asks no tactical model: the model stays strategic, through
D's goal running. A trial is no evidence (ruling P31-T); round two reads it.

## What it decides and how

D's arbiter, unchanged (`doctrine.arbiter.Arbiter`): one intent at a time, pre-empted only by a strictly higher
priority, the pre-empted one waiting in a one-deep resume slot. Each tick (2 Hz) `situation.read` turns the World into
the wants of six priorities, top down:

| P | Want (`situation.py`), its `piece` | Intent (`intents.py`) |
|---|---|---|
| 0 | `hit`: a hit reaction with a standing zombie within MELEE_RELEASE_R, the nearest. `swing`: a standing zombie within SWING_GUARD_R, the nearest. `crawler`: a crawler within KEEP_R. `fallen`: a zombie lying within FIGHT_REACH, none standing within KEEP_R. | **Fight** at P0, to the kill |
| 1 | `dress`: D's, with a crawler within KEEP_R holding it off as a standing zombie does | **Dress** (D's, failing `crawler near`) |
| 2 | `avoid`: D's, a group toward a named refuge | **Avoid** (D's, unchanged) |
| 3 | `reach` (armed): the nearest standing within KEEP_R. `fight` / `stand`: D's, the nearest aware within ENGAGE_R, the stand's ground for a group with no refuge. `seek` (armed): exactly one standing zombie listed within SEEK_R, idle, free and reachable. `downed`: D's fallen within DOWNED_R with none standing within it. | **Fight** at P3, to the kill |
| 4 | `door`: D's, decided once | **Door** (D's, unchanged) |
| 5 | `order`: always | **Order** (D's, unchanged: the care in the lull, the needs, the goal runner with `source.Resume` and the prefetch) |

**The Fight** (`intents.Fight`) is a copy of D's Fight (`doctrine/intents.py`) cut to one pin. Its `p` is its want's:
P0 for a guard, P3 otherwise.

- Within MELEE_RELEASE_R, or at a fallen pin, it sends the melee through D's one call site (`doctrine.intents.
  melee_command`, on Task 2's three-field `MeleeInputs`). The mode is `strike`, `shove` (unarmed or spent) or `finish`.
- Farther out:
  - a stand first walks the stance to its ground;
  - a chaser is met standing in the stance, and closed on once it has not closed for STALL_S;
  - an idle pin is closed on with D's `close` leg (a walk beyond CLOSE_WALK_R, else the stance's walk). This is the
    seek's leg.
- Its ends:
  - `done kill` or `done gone` when its pin is read killed, unlisted, or past DISENGAGE_R;
  - `done repin`, T's re-pin folded into its own test:
    - a hit reaction with another standing zombie nearest within MELEE_RELEASE_R (T's `hit` guard);
    - another standing zombie nearest within SWING_GUARD_R (T's `swing` guard);
    - armed with the pin standing, another standing zombie nearer than the pin within KEEP_R (T's `second_standing`);
    - the meet's `handback`.
    The same tick, the next want names the zombie the re-pin read: the re-pin calls the wants' own reads over their
    one population (`situation.guard`, `situation.reach`, `situation.populations`);
  - `failed handback` on the HANDBACK_MAX-th (3) handback in a row by Fights at one pin: the pin is held out of every
    Fight's want for SKIP_S and the arbiter's next answer takes the tick (fix 1, below);
  - `done lapsed`: a seek Fight whose pin is idle and beyond DANGER_R once the seek's own predicate
    (`situation.lone_idle`, the want's own function) no longer holds at it (fix 1, below);
  - `failed dud` (DUD_N strikes that lowered nothing, or the meet's `lost no progress`), `failed unreached` (the meet's
    `lost out of reach`) or `failed stall` (a close whose distance has not fallen for STALL_S). Each leaves the pin
    skipped for SKIP_S.
- Never one press, and never on health.

**Order inside P0.** The swing guard comes before the crawler: a standing zombie within 1.0 tile is met first. The
crawler comes before a standing zombie beyond 1.0, because a crawler bites (#4687) and a knocked-down zombie does not
until it rises. The crawler's guard yields while a standing zombie is within the meet's HANDBACK_R 2.0 (the meet
hands a finish back then), so P3's `reach` takes the standing one. A knocked-down zombie is finished only once nothing
stands within KEEP_R, as T does.

**Skips and back-offs.**
- A zombie whose melee backed off is in no guard for BACKOFF_TICKS.
- A fight skip holds off the two finishes only. A standing zombie in the swing radius is met whatever the skip, as D
  struck a skipped one.
- A handback hold (HANDBACK_MAX) holds a zombie out of every guard and every Fight's want for SKIP_S.
- A Fight made from the tick's wants after the Fight that ended this tick skipped its pin ends `done skipped` as it
  acts (every piece but `hit` and `swing`), and the tick is handed on.

## The pieces and their sources

| Piece | Source | How |
|---|---|---|
| The arbiter, the six priorities, the resume slot, the intents' done/failed contract | D: `doctrine/arbiter.py`, `doctrine/intents.py` `Intent` | import, unchanged |
| The tick's bookkeeping, the kills, skips and back-offs, the bandage want, the Avoid's gait, `source.Resume`, the P30-C door read off | D: `doctrine/assess.py` `Doctrine` | `assess.Mix2` subclasses it; `tick` is D's over mix_2's read (copied, 15 lines) |
| The listing, the portals, the line exclusions (#4681), the group, the refuge, the stand's ground, the door's decision, D's dress read | D: `doctrine/situation.py` | import (`listed`, `portals`, `refuge`, `ground`, `_door`, `_dress`) |
| Avoid, Door, Order | D: `doctrine/intents.py` | import, unchanged |
| The guards `hit`, `swing` and `fallen` | T: `tactician/decide.py` `Tactician._guard` | rewritten as P0 wants (`situation.guard`) over D's populations |
| The re-pin (`second_standing`, the guards over any play, the handback) | T: `tactician/executors.py` `FightExec.bound`; `_guard` | folded into `intents.Fight.check` and `observe` as `done repin` |
| The `reach` rule (armed, the nearest standing within KEEP_R) | T: `tactician/fallback.py` `_tests`'s `reach` | P3's first clause: the re-pin's next ("the next tick's P3 takes the nearest") |
| The dress waits until nothing stands or crawls within KEEP_R | T: `fallback.py`'s `bleed` rule; the read's item 2 | D's `_dress` read with the crawlers within KEEP_R added to its standing list |
| The crawler as a threat (a P0 finish; a running Dress fails `crawler near`) | The read's mix_2 item 2 (D's trial-10 death) | `situation.guard`'s `crawler`; `intents.Dress.check` |
| The fight to the kill | D's Fight | copied in `intents.Fight` (its string and its two-zombie pin dropped) |
| The lone-idle seek | L: `engage.Engage._sought`, cut to one zombie (P24-AT's `_lone`) | `situation._fight`'s `seek` clause; its reachability is `engage.Engage._engageable`, called unedited through `seek.Reach` over its own flood (the Survive's ladder state is never written) |

## What it drops, and why

- **D's Strike** (P0's one press, then back to the slot). In trial 10 it pressed 15436 at 0.73 tiles. The press did
  nothing, and the character cycled back to a Dress that the adjacent zombie then cut. The guards fight to the kill
  instead.
- **D's strike radius** (`weapon.reach` + 0.35) and its `me.attackers` read go with the Strike. P0's standing radius is
  T's SWING_GUARD_R 1.0. A standing zombie between 1.0 and KEEP_R is P3's `reach`.
- **D's string** (the stance backpedal on one heading for a pair arriving together). Trial 10's pair arrived together
  anyway. A pair is now met standing, one pin at a time, and re-pinned to the nearer.
- **D's two-zombie Fight** (one Fight owning one or two ids, re-picking with SEEK_SWITCH_R). Each Fight has one pin. The
  re-pin ends it, and the arbiter starts the next at the nearest.
- **T's tactical model, its triggers, its table and its plays.** No tactical call is made, so there is no `plays.log`.
- **T's DRESS_MARGIN hysteresis.** The read takes T's 2.5-tile rule only. D's T1 observation (the dress against a chaser
  beyond 2.5 tiles) stands.
- Everything of the ladder's beyond the seek's reachability. D's README lists what of it does not run behind the fork.

## The constants and their sources

`constants.py` imports every number but HANDBACK_MAX, fix 1's own. None is changed from its package.

| Constant | Value | Source |
|---|---|---|
| SWING_GUARD_R | 1.0 | T's `executors.SWING_GUARD_R` (P30-A's SWING_CLOSE_R) |
| FIGHT_REACH | 2.0 | `policies.FIGHT_REACH`, T's `fallen` guard radius |
| KEEP_R | 2.5 | `policies.KEEP_R`: T's `second_standing` and `reach`, the dress's clear radius (D's DRESS_CLEAR_R) |
| MELEE_RELEASE_R | 2.75 | `policies.MELEE_RELEASE_R`, T's `hit` guard radius |
| SEEK_R | 9.0 | `policies.ENGAGE_R`, the ladder's seek radius (ruling P24-X) |
| HANDBACK_R | 2.0 | `policies.HANDBACK_R`, the meet's `handbackR`: the crawler's guard yields while a standing zombie is this near |
| DANGER_R | 6.0 | `policies.DANGER_R`: a seek Fight's pin beyond it ends `done lapsed` once the seek's predicate fails |
| HANDBACK_MAX | 3 | mix_2's own (fix 1): handbacks in a row at one pin before it is held; a first guess for the trials |
| D's numbers (GROUP_N, GROUP_R, ENGAGE_R, STALL_S, DUD_N, SKIP_S, BACKOFF_TICKS, DOWNED_R, the Avoid's and the Door's) | as D's README | `doctrine/constants.py`, read as `DK` |

## The decision line's keys

The fork's contract holds, as D's does:
- `branch` is `threat` on a fight, avoid or door tick, `care` on a dress tick, and the ladder step's own name on an
  order tick;
- `inputs.branches.threat.flee` is `group` while an Avoid walks;
- `inputs.x` and `inputs.y` are written as the ladder writes them.

mix_2's own keys:
- **`inputs.mix_2`** carries D's `inputs.doctrine` keys: `intent`, `p`, `why`, `state`, `target`, `n`, `preempted_by`,
  `resumed`, `ended`, `slot`, `wants`, plus an order's `step` and `resumed_goal`. It also carries:
  - `piece`: the rule that started the running intent, one of `constants.PIECES`;
  - `pieces`: this tick's wants' pieces;
  - `repin`: on the tick a Fight ends by a re-pin, `{id, by, pin, end}` (`by` one of `hit`, `swing`,
    `second_standing`, `handback`; a handback's `n` its count in a row at the pin; `end` `done`, or `failed` on the
    bound), copied from the ended Fight by `Mix2._note_end` (a list when two ended in one tick). Round two counts the
    handbacks and their same-pin runs off it.

  There is no `inputs.doctrine`, so a trial's lines tell the two variants apart by key. `assess.line_switches` reads
  the equal-priority switches off `inputs.mix_2`.
- **`inputs.intent`** is `{kind, target}`, the scorecard's label (`tools/trial_score.py`):

| Intent | `kind` | `target` |
|---|---|---|
| Fight (any piece) | `fight` | the pin's id |
| Dress | `dress` | none |
| Avoid, walking | `avoid_refuge` (a retreat naming a refuge) | the refuge square |
| Avoid, holding | `filter_door`, `filter_window` or `filter_fence` | the refuge square |
| Door | `filter_door` or `door_leave` | the door square |
| Order | `dress`, `stock`, `needs`, `rest`, `loot` or `travel` | the goal's square |

There is no `inputs.play`. The string is gone, so no Fight line is read as a retreat.

## What it needs from the harness, and the observations round two reads

- **No Lua change of its own.** The reflex and the PZA schema stay frozen (ruling P31-T). The read raised two Lua
  questions, both Harden's:
  - the point-blank presses: 7 of 8 swings under 0.6 tiles did nothing;
  - the shove-only meet under arm pain: after trial 11's first arm bite, 7 of 8 spent shoves did nothing;
  - fix 1's crowd case (review-t13-mix2 F2b): two standing zombies within the meet's STAND_R 0.6, the meet handing
    back `crowd` before every press (`PZAgent_StanceMelee.lua`), so no press goes at either while both stand there.
    mix_2 bounds the planner's side (HANDBACK_MAX, then the pin held and the other fought, which the meet hands back
    too); the press itself is the Lua's.

  mix_2 sets no meet constant.
- **The crawler read** is the frame's `crawler` (true with `onFloor`). `tactician.tview` reads it the same way.
- **The risks the read names:**
  - The arbiter's strict pre-emption: a P3 Fight at the first of a pair holds against an equal want for the second.
    Only the swing guard at 1.0, the hit guard and the re-pin move it, and whether this re-pin is as quick as T's play
    end is untested live.
  - D's goal pace on the street is unmeasured (one call before its death).
  - The Dress maneuver has never completed live under any arm.
  - The seek walks toward a lone idle zombie that may have a second just beyond the listing (L's smoke-run walk leg).
- **The P0 order inside the crawler case.** With a standing zombie at 0.9 tiles and a crawler at 1.0, the swing guard
  fights the standing one to the kill. The crawler is finished after it, or once the standing one leaves the swing
  radius while the Fight's pin is down. Over trial 10's 122 lines the read's first want is the crawler's on 22 and the
  swing's on 21; in the open loop over the same frames the running intent is a swing Fight on 56 of 134 ticks and
  never a crawler's (the stub kills nothing, so the swing Fight never ends by a kill). This is my reading of the
  read's two clauses (the swing guard "in any play", a crawler "a P0 finish"). Round two reads whether the crawler's bites through that fight cost more than the
  standing zombie's.

## Fix 1 (review-t13-mix2)

- **The seek's end (F1, major).** A running seek Fight re-reads the seek's predicate each tick through the want's own
  function (`situation.lone_idle`, with the pin read at any distance so the seek keeps its hysteresis just past
  SEEK_R) and ends `done lapsed` when its pin is idle and beyond DANGER_R and the predicate fails: a second standing
  zombie listed within SEEK_R, an aware newcomer (D's `fight` then takes it), or the pin no longer free or reachable.
  Inside DANGER_R it runs on: trial 2 at 245-251 s, 9815 listed idle at 8.2 tiles while the pin 9812 stands at 3.8
  (the replay test's line).
- **The handback loop (F2, major).** (a) The crawler's guard yields while a standing zombie is within HANDBACK_R
  (trial 10's lines 98, 99 and 116: 15436 standing at 1.25 to 1.52 tiles by the crawler), so the guard never asks the
  meet for a finish it hands back. (b) The handbacks in a row by Fights at one pin are counted (`Mix2.handbacks`, a
  Fight at the pin ending otherwise clearing it); the HANDBACK_MAX-th ends the Fight `failed handback`, the pin held
  out of every Fight's want for SKIP_S (`situation.Memory.hold`), the arbiter's next answer taking the tick. Five in a
  row at one pin no longer happen (the reviewer's probe shapes are unit tests).
- **The line's `repin` (F3, medium)** now reaches the decision line on the tick the Fight ends.
- **Quality (F5).** The re-pin calls `situation.guard` and `situation.reach` over `situation.populations`;
  `_ground_leg` calls D's own method; a drift test compares `Mix2.tick` with `Doctrine.tick` but for its read and
  its three `# mix_2` lines.
- **A one-tick artefact closed.** D's tick makes the next intent from wants read before the ended Fight skipped its
  pin (a stall); such a Fight now ends `done skipped` as it acts, the tick handed on.
