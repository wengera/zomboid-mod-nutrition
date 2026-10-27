"""The scripted survivor (Plan 22 Task 10, spec § 3): a priority list over the World, ticked by its driver.

`Survive(world, actions, log_path, clock).tick(world, actions)` tries the branches in order (threat, need, forage,
explore; no sleep, ruling P22-1), takes the first that answers, and returns the `Action` it sent or None. A branch
answers with a command to send or, while its own action is still current, with none (it holds: nothing is sent and
no lower branch runs). A branch whose answer differs from the current action's sender sends at once, so a higher
branch pre-empts a lower one's action (the Lua fails the old one `superseded`). The branches run the policies of
`policies.py`; `need` is one `Consume`. Every tick appends one JSON line to `log_path` (decision.log): `{wall,
gameMin, branch, inputs, action, sent}`, sorted keys, `wall` from the injected clock, `action` the command's `type`
and `args` or null, so a replayed session reproduces its decisions byte for byte.

The thresholds and the threat hysteresis are Plan 21b's (`testing/agent/policy.py`'s docstring, frozen; ported):
- A zombie is a threat within DANGER_R; while a threat policy runs (the "mode", `fight` or `flee`, kept while the
  threat branch answers), the branch holds every zombie within DISENGAGE_R: a threat engaged at 6 tiles holds the
  branch until it is beyond 10 or dead, so the bot never turns its back to loot.
- The hold-radius fix (`docs/reference/research-notes.md`, "The hold radius widens the 'too many' count"; the Plan
  21b ledger's ruling): the rules that turn to a flee (`many`, `pair`) count the zombies within DANGER_R only, so a
  fight engaged at 5 tiles with two more zombies at 8 and 9 is no "too many"; the rules that keep a flee running
  (`held`) read the held list, being the hold itself.
- Fight or flee: flee when unarmed (`world.weapon` is None), when the DANGER_R count > MAX_FIGHT, when health <
  FLEE_HEALTH, or when that count >= 2 and health < FLEE_HEALTH_PAIR. A running flee turns back to fight only with
  one held threat and health >= FLEE_HEALTH + REFIGHT_MARGIN, and a flee sent because a fight stalled is held while
  the nearest stays beyond FIGHT_REACH; a running fight turns to flee only on the flee conditions or its stall
  (`Fight.stalled`: the nearest beyond FIGHT_REACH for more than FIGHT_MAX_S unbroken seconds), never because a
  threat count dropped. The flee steers from the held threats' centroid.
- Unreachable (the whole-pass review's I2): a target whose STALL_SWINGS started swings took no health is skipped for
  UNREACHABLE_S (`policies.Fight`); Survive keeps that memory in `unreachable` across its Fights, and when every held
  threat is skipped the branch flees (reason `unreachable`), never attacking it again until its time runs out.
- `need`: while its own `Consume` is current it holds, before any threshold is read (a frame that already reads the
  drink's effect must not let a lower branch supersede it); else thirst > THIRST_T consumes the held item of least id whose fullType matches WATER_RX, else marks `water`;
  then hunger > HUNGER_T consumes a held FOOD_RX item, else marks `food`; nothing held, the branch passes and
  `forage` loots for the mark (`all` with none) through `LootHouse`, which loots only at load level 0-1, never at 2,
  and drops from 3 down to 2 (spec § 9 (1)). `explore` scans each new place and walks to the unexplored edge.
- A command whose action ended `failed` (any reason but `superseded`, which this planner's own next send caused),
  `timeout` or `rejected` is not chosen again with the same type and args for FAILED_COOLDOWN_TICKS planner ticks:
  its branch is passed over and the next one tried (logged as inputs.cooled); the threat branch is never passed
  over. Every branch tried logs its own inputs under inputs.branches[<branch>].
- The log's inputs carry `mode` (the running threat policy at the tick's start, else None), `threats` (the DANGER_R
  count), `held` (the count within the hold radius) and `fight_s` (the running fight's stall clock read before this
  tick restarts it, else None).
"""
import json
import time

from agent.base.planner.policies import (FIGHT_MAX_S, FIGHT_REACH, PREEMPTED, Explore, Fight, Flee, LootHouse,
                                         blocked, item_id_ok, zdist)
from agent.base.pza1 import Consume
from agent.base.world import FOOD_RX, WATER_RX

DANGER_R = 6.0            # a zombie this close is a threat
DISENGAGE_R = 10.0        # while a fight or flee runs, a zombie this close is still held
THIRST_T = 0.5
HUNGER_T = 0.5
FLEE_HEALTH = 40.0        # under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
REFIGHT_MARGIN = 20.0     # a running flee turns to fight only at health >= FLEE_HEALTH + this, one threat
MAX_FIGHT = 2             # more threats than this are fled
BRANCHES = ("threat", "need", "forage", "explore")
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed command is not chosen again with the same type and args
FAILED = ("failed", "timeout", "rejected")

__all__ = ["Survive", "BRANCHES", "DANGER_R", "DISENGAGE_R", "THIRST_T", "HUNGER_T", "FLEE_HEALTH",
           "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "FIGHT_MAX_S", "FIGHT_REACH", "FAILED_COOLDOWN_TICKS"]


def _key(typ, args):
    return typ, json.dumps(args, sort_keys=True)


class Survive:
    def __init__(self, world, actions, log_path, clock=time.time):
        self.world = world
        self.actions = actions
        self.log_path = log_path
        self.clock = clock
        self.mode = None          # the running threat policy: "fight", "flee" or None
        self.fight = None
        self.flee = None
        self.stall_flee = False   # the running flee was chosen because a fight stalled
        self.unreachable = {}     # zombie id -> wall until it is skipped (policies.Fight), kept across Fights
        self.loot = LootHouse(world, actions, clock)
        self.explore = Explore(world, actions, clock)
        self.need_last = None     # the last Consume sent
        self.need_mark = None     # "water" or "food" when need found nothing held; forage loots for it
        self.ticks = 0
        self.last_failed = None   # (type, args json, tick first seen failed) of the last command that failed
        self._watch = []          # actions sent and not yet seen terminal
        self.why = {}

    # ---------------------------------------------------------------- reading the world
    def _policies(self):
        return [p for p in (self.loot, self.explore, self.fight, self.flee) if p is not None]

    def _within(self, r):
        return [z for z in self.world.zombies.values()
                if z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= r]

    def _hold_r(self):
        return DISENGAGE_R if self.mode is not None else DANGER_R

    def _health(self):
        h = (self.world.body or {}).get("health")
        return 100.0 if h is None else h

    def _armed(self):
        return self.world.weapon is not None

    def _held_item(self, rx):
        ids = [i for i, it in self.world.inventory.items()
               if item_id_ok(i) and rx.search(it.get("fullType") or "")]
        return min(ids) if ids else None

    def _reachable_held(self):
        """The held threats not marked unreachable."""
        skip = blocked(self.unreachable, self.clock())
        r = self._hold_r()
        return [z for zid, z in self.world.zombies.items() if zid not in skip and z.get("x") is not None
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
        if n >= 2 and health < FLEE_HEALTH_PAIR:
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
        if self.mode == "fight" and self.fight.stalled and near > FIGHT_REACH:
            return "stalled"
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
            self.mode, self.fight, self.flee, self.stall_flee = None, None, None, False
            return None
        reason = self._flee_reason(held, len(self._within(DANGER_R)))
        want = "fight" if reason is None else "flee"
        if want != self.mode:
            if want == "fight":
                self.fight = Fight(self.world, self.actions, self.clock, unreachable=self.unreachable)
                self.flee, self.stall_flee = None, False
            else:
                self.flee, self.fight = Flee(self.world, self.actions, self.clock), None
                self.stall_flee = reason == "stalled"
            self.mode = want
        policy = self.fight if want == "fight" else self.flee
        if want == "flee":
            policy.threats = held
        ans = self._answer(policy)
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        return ans if ans is not None else (policy, None)

    def _need(self):
        if self.need_last is not None and self.actions.current is self.need_last:
            self.why = {"holding": self.need_last.aid}   # hold first: a frame past the drink must not supersede it
            return None, None
        st = self.world.stats or {}
        pick = None
        if (st.get("thirst") or 0.0) > THIRST_T:
            pick = self._held_item(WATER_RX)
            if pick is None:
                self.need_mark = "water"
        if pick is None and (st.get("hunger") or 0.0) > HUNGER_T:
            pick = self._held_item(FOOD_RX)
            if pick is None:
                self.need_mark = self.need_mark or "food"
        self.why = {"item": pick, "mark": self.need_mark}
        if pick is None:
            return None
        return None, Consume(pick)

    def _forage(self):
        self.loot.want = self.need_mark or "all"
        return self._answer(self.loot)

    def _explore(self):
        return self._answer(self.explore)

    # ---------------------------------------------------------------- the tick
    def _note_failures(self):
        still = []
        for a in self._watch:
            if not self.actions.done(a):
                still.append(a)
            elif a.state in FAILED and not (a.state == "failed" and a.reason == PREEMPTED):
                self.last_failed = _key(a.type, a.args) + (self.ticks,)
        self._watch = still

    def _cooling(self, cmd):
        f = self.last_failed
        return f is not None and _key(cmd.TYPE, cmd.args()) == f[:2] and self.ticks - f[2] < FAILED_COOLDOWN_TICKS

    def _inputs(self):
        me = self.world.me or {}
        st = self.world.stats or {}
        held = self._within(self._hold_r())
        cur = self.actions.current
        return {"x": me.get("x"), "y": me.get("y"), "health": self._health(), "hunger": st.get("hunger"),
                "thirst": st.get("thirst"), "armed": self._armed(), "load": (self.world.load or {}).get("level"),
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
        self.loot.observe()
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
        inputs["cooled"] = cooled
        inputs["branches"] = tried
        action = None
        if cmd is not None:
            action = owner.send(cmd) if owner is not None else self.actions.send(cmd)
            if owner is None:
                self.need_last = action
            self._watch.append(action)
        line = {"wall": self.clock(), "gameMin": self.world.game_min, "branch": branch, "inputs": inputs,
                "action": {"type": cmd.TYPE, "args": cmd.args()} if cmd is not None else None,
                "sent": action is not None}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return action
