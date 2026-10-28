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
  21b ledger's ruling): the rules that turn to a flee (`many`, `pair`) count the zombies within DANGER_R only, so a
  fight engaged at 5 tiles with two more zombies at 8 and 9 is no "too many"; the rules that keep a flee running
  (`held`) read the held list, being the hold itself.
- Fight or flee: flee when unarmed (`world.weapon` is None), when the DANGER_R count > MAX_FIGHT, when health <
  FLEE_HEALTH, or when that count >= 2 and either health < FLEE_HEALTH_PAIR or the body carries a wound (the frame's
  `body.bleeding + scratched + bitten` > 0, a missing count read 0; Plan 23 Task 10: a wounded player does not take
  on a pair at any health), the reason `pair`. A running flee turns back to fight only with
  one held threat and health >= FLEE_HEALTH + REFIGHT_MARGIN, and a flee sent because a fight stalled is held while
  the nearest stays beyond FIGHT_REACH; a running fight turns to flee only on the flee conditions or its stall
  (`Fight.stalled`: its target beyond FIGHT_REACH for more than FIGHT_MAX_S unbroken seconds), never because a
  threat count dropped; the stall guard reads the distance to the Fight's target (`Fight.target_dist()`, the pinned
  one), the zombie its stall clock follows, never the nearest held one (Task 10's review M3). The flee steers from
  the held threats' centroid.
- The flee's load drop (Plan 23 Task 10): run 2's last flee was pinned at load level 4. While the mode is `flee` and
  the frame's load level is at or above `policies.DROP_AT` (3), the flee episode's first free answer is one `Drop` of
  `LootHouse.spare()` (logged `flee_drop`, the item's id), sent as the Flee's own action so its steer waits on the
  drop (the drop skill is quick) and follows on the next tick; at most one drop per episode (`flee_dropped`, reset when
  the mode leaves `flee`), none when nothing is spare.
- Unreachable (the whole-pass review's I2): a target whose STALL_SWINGS started swings took no health, or whose line
  stays blocked after the Fight's one reposition (or has no clear square to reposition to), is skipped for
  UNREACHABLE_S (`policies.Fight`); Survive keeps that memory in `unreachable` across its Fights, and when every held
  threat is skipped the branch flees (reason `unreachable`), never attacking it again until its time runs out.
- `need` (Plan 23 Task 11, P23-7): Plan 22's character never ate or drank, its thresholds 0.5, which vanilla reaches
  in 17 to 20 game hours; the needs now fire at the game's first moodle, THIRST_T 0.12 (#0509) and HUNGER_T 0.15
  (#0508). While its own `Consume` is current the branch holds, before any threshold is read (a frame that already
  reads the drink's effect must not let a lower branch supersede it); else thirst > THIRST_T consumes the held item
  of least id whose use is `water` (`world.by_use()`: the dataset's drinkable, non-poisonous fluid containers, an id
  marked empty left out), else marks `water`; then hunger > HUNGER_T consumes the held `food` item of least id (the
  dataset's food), else marks `food`; nothing held, the branch passes (to the goal). Each mark is also kept in
  `need_marks` {use: wall of its last mark} (both uses, where `need_mark` logs the first), which the view reads as
  `needs_wanted` for `view.NEED_MEMORY_S`; a held item of the use found clears its mark.
- The empties (P23-D): a `Consume` whose action ended `failed "not valid"` on an id `by_use()` reads `water` marks it
  empty (`world.mark_empty`), so the next tick takes the next bottle and `spare()` may drop it; any other id refused
  so (a food, which is eaten whole or refused for another reason, or a bottle no longer held when the end was read)
  is never marked, only logged as inputs.consume_refused on the tick that read the end (else None).
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
  heavy load is dropped before the sleep.
- `night` (Plan 23 Task 12, P23-9): `night.Night` (its docstring is the design record). Its own running action holds
  first, before the want is read (a sleep is never superseded by its fatigue falling under the want); not wanting, it
  passes (logged `{"wants": false}`); wanting (counted in `night.wants_n`), it shelters in a known interior and
  sleeps, holds NOT_SAFE_S after a sleep refused `not safe` and NOT_VALID_S after `not valid`, stops wanting for the
  session after `not allowed` (ruling P23-U), and with no shelter known sets `night.want_shelter` and passes. Its
  `why` carries `step`, `building`, `shunned` and the sent action's `aid`.
- The log's inputs carry `mode` (the running threat policy at the tick's start, else None), `threats` (the DANGER_R
  count), `held` (the count within the hold radius), `fight_s` (the running fight's stall clock read before this
  tick restarts it, else None), and the frame's `fatigue` and `hour` (the night's inputs).
"""
import json
import time

from agent.base.planner.goals import GoalRunner, ScriptedSource
from agent.base.planner.night import Night
from agent.base.planner.policies import (DANGER_R, DISENGAGE_R, DROP_AT, FIGHT_MAX_S, FIGHT_REACH, PREEMPTED, Fight,
                                         Flee, blocked, item_id_ok, spare, target_id_ok, zdist)
from agent.base.planner.view import view
from agent.base.pza1 import Consume, Drop

THIRST_T = 0.12          # the first THIRST moodle fires above 0.12 [#0509]
HUNGER_T = 0.15          # the first HUNGRY moodle fires above 0.15 [#0508]
FLEE_HEALTH = 40.0        # under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
REFIGHT_MARGIN = 20.0     # a running flee turns to fight only at health >= FLEE_HEALTH + this, one threat
MAX_FIGHT = 2             # more threats than this are fled
BRANCHES = ("threat", "need", "load", "night", "goal")
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed command is not chosen again with the same type and args
FAILED = ("failed", "timeout", "rejected")
REFUSED = "not valid"    # the reason the Lua's consume fails an item it cannot eat or drink (an empty bottle)

__all__ = ["Survive", "BRANCHES", "DANGER_R", "DISENGAGE_R", "THIRST_T", "HUNGER_T", "FLEE_HEALTH",
           "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "FIGHT_MAX_S", "FIGHT_REACH", "FAILED_COOLDOWN_TICKS"]


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
        self.unreachable = {}     # zombie id -> wall until it is skipped (policies.Fight), kept across Fights
        self.night = Night(world, actions, clock)
        self.goals = GoalRunner(ScriptedSource() if source is None else source, clock)
        self.goals.kit.bind(world, actions)
        self.need_last = None     # the last Consume sent
        self.load_last = None     # the last load Drop sent
        self.need_mark = None     # "water" or "food" when need found nothing held this tick (logged)
        self.need_marks = {}      # use -> wall of its last mark: the view's needs_wanted
        self.consume_refused = None   # a non-water id whose consume ended failed "not valid" this tick (logged only)
        self.ticks = 0
        self.last_failed = None   # (type, args json, tick first seen failed) of the last command that failed
        self._watch = []          # actions sent and not yet seen terminal
        self.why = {}

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
        """The least usable id among the held items of `use` (`world.by_use()`), else None."""
        ids = [i for i in self.world.by_use()[use] if item_id_ok(i)]
        return min(ids) if ids else None

    def _reachable_held(self):
        """The held threats a Fight can target and not marked unreachable (a nil-id zombie is a danger, never a
        target)."""
        skip = blocked(self.unreachable, self.clock())
        r = self._hold_r()
        return [z for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip and z.get("x") is not None
                and z.get("y") is not None and zdist(self.world, z) <= r]

    def _flee_reason(self, held, n):
        """Why the threat branch flees, by the hysteresis in the module docstring; None when it fights."""
        health = self._health()
        if not self._armed():
            return "unarmed"
        if n > MAX_FIGHT:
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

    def _threat(self):
        held = self._within(self._hold_r())
        if not held:
            self.mode, self.fight, self.flee, self.stall_flee, self.flee_dropped = None, None, None, False, False
            return None
        reason = self._flee_reason(held, len(self._within(DANGER_R)))
        want = "fight" if reason is None else "flee"
        if want != self.mode:
            if want == "fight":
                self.fight = Fight(self.world, self.actions, self.clock, unreachable=self.unreachable)
                self.flee, self.stall_flee, self.flee_dropped = None, False, False
            else:
                self.flee, self.fight = Flee(self.world, self.actions, self.clock), None
                self.stall_flee = reason == "stalled"
            self.mode = want
        policy = self.fight if want == "fight" else self.flee
        if want == "flee":
            policy.threats = held
            ans = self._flee_drop() or self._answer(policy)
        else:
            ans = self._answer(policy)
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        return ans if ans is not None else (policy, None)

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
        running goal holds the branch and no goal passes."""
        cmd = self.goals.tick(self.world, self.actions, lambda: view(self.world, self))
        self.why = dict(self.goals.why)
        if cmd is not None:
            return self.goals, cmd
        return (self.goals, None) if self.goals.current is not None else None

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
        """A consume refused `not valid`: an id `by_use()` reads `water` is empty (P23-D), marked so it reads
        `other`; any other id (a food, eaten whole or refused for another reason, or a bottle no longer held) is only
        logged."""
        if iid in self.world.by_use()["water"]:
            self.world.mark_empty(iid)
        else:
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
        line = {"wall": self.clock(), "gameMin": self.world.game_min, "branch": branch, "inputs": inputs,
                "action": {"type": cmd.TYPE, "args": cmd.args()} if cmd is not None else None,
                "sent": action is not None, "goal": self.goals.line()}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return action
