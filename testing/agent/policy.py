"""The scripted bot (spec § 3): a priority list over the World, ticked by its driver at PLANNER_HZ.

`Policy(world, link, log_path, clock).tick()` tries the branches in order (threat, need, sleep, forage, explore),
each a method returning `(goal, args)` or None, takes the first answer, and sends it through `link.send` only when it
differs from the goal still running; it returns the goal sent, or None. Every tick appends one JSON line to
`log_path` (decision.log): `{wall, gameMin, branch, inputs, goal, args, sent}`, sorted keys, `wall` from the injected
clock, so a replayed log reproduces its decisions byte for byte.

The goal strings are PZAgent_Act.lua's own forms, every x y a world square: `fight`, `flee x y`, `drink`, `eat T`,
`goto x y`, `sleep`, `loot x y <food|water|all>`, and the configuration command `scan r`, which runs no goal.

HEURISTIC (a spike, deliberately dumb):
- "Differs" compares goal and args, except `fight` and `flee`, compared by name: the Lua re-aims a flee itself, and
  a flee whose args followed the moving centroid would be re-sent every tick.
- What is held is read off the World's events: an `item_added` adds its fullType, a finished `eat T` takes one T
  (all of them when it failed), and a `drink` that failed `none held` blocks drinking until an item matching
  world.WATER_RX is added. The events deque is bounded, so a long session forgets its oldest pickups.
- A goal that failed is not chosen again with the same name and args for FAILED_COOLDOWN_TICKS planner ticks: its
  branch is passed over and the next one tried (logged as inputs.cooled). Two exceptions: a goal the Lua failed as
  `superseded` (this policy's own next send replaced it) is not a failure and never cools, and the `threat` branch is
  never passed over (a threat is not waited out; its own choice adapts, `flee` when unarmed). Every branch tried
  logs its own inputs (the chosen square, container or edge) under inputs.branches[<branch>].
- A loot goal that finishes, done or failed, marks every container on its square looted, so a failing square is not
  retried. An explore walk that finishes is followed by one `scan` from where it ended.
- Threat hysteresis (Plan 21b Stage C pass 2, from run c_survive-20261026-183905's death). A zombie is a threat
  within DANGER_R, but while a threat goal (`fight` or `flee`, the running "mode") runs, within DISENGAGE_R: a threat
  engaged at 6 tiles holds the branch until it is beyond 10 or dead, so the bot never turns its back to loot.
- Fight or flee: flee when unarmed, when threats > MAX_FIGHT, when health < FLEE_HEALTH, or when threats >= 2 and
  health < FLEE_HEALTH_PAIR. A running flee turns back to fight only with one threat and health >= FLEE_HEALTH +
  REFIGHT_MARGIN; a running fight turns to flee only on the flee conditions, never because a threat count dropped.
- A fight that does not close: a stall clock (out_of_reach_since) starts when a fight is sent and restarts on every
  planner tick of the running fight whose nearest threat is within FIGHT_REACH or that reads no threat at all; a
  fight whose nearest threat has stayed beyond FIGHT_REACH for longer than FIGHT_MAX_S flees. A melee whose zombie is
  knocked back a tick, or a new zombie arriving after the last one died, restarts nothing old: the clock counts only
  the unbroken time out of reach, never the fight's age. Run 1's 210 s standoff: its zombie stood 2.74 tiles away, inside the Lua's FIGHT_R 3 but beyond the bat's
  reach, and the fight swung without approaching (endurance 0.95 to 0.32). That flee is held, not turned back to
  fight, while it runs and the nearest threat stays beyond FIGHT_REACH.
- The decision log's inputs carry `mode` (the running threat goal, else None) and `fight_s` (the running fight's
  stall clock: seconds its nearest threat has been out of FIGHT_REACH, read before this tick restarts it; else None).
"""
import json
import math

from agent.world import FOOD_RX, WATER_RX

DANGER_R = 6.0        # a zombie this close is a threat
DISENGAGE_R = 10.0    # while a fight or flee runs, a zombie this close is still a threat
THIRST_T = 0.5
HUNGER_T = 0.5
FATIGUE_T = 0.7
FLEE_HEALTH = 40.0    # PZA.act.FLEE_HEALTH: under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
REFIGHT_MARGIN = 20.0     # a running flee turns to fight only at health >= FLEE_HEALTH + this, one threat
FIGHT_MAX_S = 20.0    # wall seconds a fight may run with its nearest threat out of reach
FIGHT_REACH = 2.0     # tiles: a nearest threat beyond this is not being fought
MAX_FIGHT = 2         # more threats than this are fled
FLEE_DIST = 8         # tiles, when no known square lies away from the threats
NIGHT_FROM, NIGHT_TO = 21 * 60, 6 * 60   # game minutes of the day
SLEEP_NEAR = 1.5      # within this of the chosen indoor square, sleep where standing
SCAN_R = 10
BRANCHES = ("threat", "need", "sleep", "forage", "explore")
BY_NAME = ("fight", "flee")
CONFIG = ("scan",)
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed goal is not chosen again with the same name and args
FINISHED = ("done", "failed")
PREEMPTED = "superseded"     # the detail PZAgent_Act.lua A.start gives the goal a new send replaced


class Policy:
    def __init__(self, world, link, log_path, clock):
        self.world = world
        self.link = link
        self.log_path = log_path
        self.clock = clock
        self.running = None          # (goal, args, seq) of the last goal sent
        self.sent = {}               # cmd seq -> (goal, args)
        self.need_mark = None        # "water" or "food" when the need branch found nothing held; forage loots it
        self.explore_target = None   # the args of the last explore goto
        self.scanned = set()         # explore targets already scanned from (None: the start)
        self.ticks = 0               # planner ticks so far
        self.last_failed = None      # (goal, args, tick first seen failed) of the last goal that failed
        self.failures_seen = set()   # cmd seqs whose failure has been noted
        self.why = {}                # the branch being tried: its own inputs
        self.out_of_reach_since = None   # the stall clock: clock() since the running fight's nearest is out of reach
        self.stall_flee = False      # the running flee was sent because a fight did not close

    # ---------------------------------------------------------------- reading the world
    def _xy(self):
        me = self.world.me
        return me.get("x", 0.0), me.get("y", 0.0)

    def _mode(self):
        """The running threat goal, `fight` or `flee`, else None."""
        cur = self._current()
        return cur[0] if cur is not None and cur[0] in BY_NAME else None

    def _fight_s(self):
        """Seconds the running fight's nearest threat has been beyond FIGHT_REACH (the stall clock), else None."""
        if self._mode() != "fight" or self.out_of_reach_since is None:
            return None
        return self.clock() - self.out_of_reach_since

    def _restart_stall_clock(self):
        """Restarts the running fight's stall clock when no threat is read or the nearest is within FIGHT_REACH."""
        if self._mode() != "fight":
            return
        near = self._nearest(self._threats())
        if near is None or near <= FIGHT_REACH:
            self.out_of_reach_since = self.clock()

    def _threats(self):
        mx, my = self._xy()
        r = DISENGAGE_R if self._mode() is not None else DANGER_R
        return [z for z in self.world.zombies.values()
                if z.get("x") is not None and math.hypot(z["x"] - mx, z["y"] - my) <= r]

    def _nearest(self, ts):
        mx, my = self._xy()
        return min((math.hypot(z["x"] - mx, z["y"] - my) for z in ts), default=None)

    def _armed(self):
        w = self.world.me.get("weapon")
        return bool(w) and (w.get("condition") is None or w.get("condition") > 0)

    def _finished(self):
        """{seq: (state, detail)} of every goal this policy sent that the World has seen finish."""
        out = {}
        for e in self.world.events:
            s = e.get("goalSeq")
            if s in self.sent and e.get("event") in ("goal_done", "goal_failed"):
                out[s] = (e["event"][5:], e.get("reason", ""))
        g = self.world.goal
        if g and g.get("seq") in self.sent and g.get("state") in FINISHED:
            out.setdefault(g["seq"], (g["state"], g.get("detail", "")))
        return out

    def _held(self):
        """(food fullTypes held, whether drinking is worth a try), read off the events in order."""
        food, water_ok = [], True
        for e in self.world.events:
            ev = e.get("event")
            if ev == "item_added":
                ft = e.get("fullType", "")
                if FOOD_RX.search(ft):
                    food.append(ft)
                if WATER_RX.search(ft):
                    water_ok = True
            elif ev in ("goal_done", "goal_failed") and e.get("goalSeq") in self.sent:
                goal, args = self.sent[e["goalSeq"]]
                if goal == "eat" and args in food:
                    if ev == "goal_done":
                        food.remove(args)
                    else:
                        food = [f for f in food if f != args]
                if goal == "drink" and ev == "goal_failed" and e.get("reason") == "none held":
                    water_ok = False
        return food, water_ok

    def _current(self):
        """The goal still running as (goal, args, seq), or None once it is seen finished."""
        if self.running is not None and self.running[2] in self._finished():
            self.running = None
        return self.running

    def _differs(self, goal, args):
        if goal in CONFIG:
            return True
        cur = self._current()
        if cur is None:
            return True
        if goal in BY_NAME:
            return goal != cur[0]
        return (goal, args) != cur[:2]

    def _settle_loots(self):
        for seq in self._finished():
            goal, args = self.sent[seq]
            if goal == "loot":
                x, y = (int(v) for v in args.split()[:2])
                for key in list(self.world.containers):
                    if key[0] == x and key[1] == y:
                        self.world.mark_looted(key)

    def _flee_reason(self, ts):
        """Why the threat branch flees, by the hysteresis in the module docstring; None when it fights."""
        health = self.world.me.get("health", 100.0)
        n, mode = len(ts), self._mode()
        if not self._armed():
            return "unarmed"
        if n > MAX_FIGHT:
            return "many"
        if health < FLEE_HEALTH:
            return "health"
        if n >= 2 and health < FLEE_HEALTH_PAIR:
            return "pair"
        near = self._nearest(ts)
        if mode == "flee":
            if self.stall_flee and near > FIGHT_REACH:
                return "stalled"
            if n > 1 or health < FLEE_HEALTH + REFIGHT_MARGIN:
                return "held"
            return None
        fs = self._fight_s()
        if fs is not None and fs > FIGHT_MAX_S and near > FIGHT_REACH:
            return "stalled"
        return None

    # ---------------------------------------------------------------- the branches, in order
    # Each sets self.why, its own inputs (the chosen square, container or edge), logged under inputs.branches[<branch>].
    def threat(self):
        ts = self._threats()
        if not ts:
            return None
        reason = self._flee_reason(ts)
        if reason is None:
            self.why = {"fight": True}
            return ("fight", "")
        self.why = {"flee": reason}
        cx = sum(z["x"] for z in ts) / len(ts)
        cy = sum(z["y"] for z in ts) / len(ts)
        best = None
        for (x, y, z), s in self.world.map.items():
            if s.get("solid"):
                continue
            rank = (math.hypot(x - cx, y - cy), -x, -y)
            if best is None or rank > best[0]:
                best = (rank, x, y)
        if best is not None:
            self.why.update(centroid=[cx, cy], square=[best[1], best[2]])
            return ("flee", "%d %d" % (best[1], best[2]))
        mx, my = self._xy()
        vx, vy = mx - cx, my - cy
        n = math.hypot(vx, vy) or 1.0
        tx, ty = math.floor(mx + vx / n * FLEE_DIST), math.floor(my + vy / n * FLEE_DIST)
        self.why.update(centroid=[cx, cy], away=[tx, ty])
        return ("flee", "%d %d" % (tx, ty))

    def need(self):
        me = self.world.me
        food, water_ok = self._held()
        self.why = {"food": food, "waterOk": water_ok}
        self.need_mark = None
        if me.get("thirst", 0.0) > THIRST_T:
            if water_ok:
                return ("drink", "")
            self.need_mark = "water"
        if me.get("hunger", 0.0) > HUNGER_T:
            if food:
                return ("eat", food[0])
            self.need_mark = self.need_mark or "food"
        return None

    def sleep(self):
        me = self.world.me
        gm = me.get("gameMin", 0)
        if me.get("fatigue", 0.0) <= FATIGUE_T or not (gm >= NIGHT_FROM or gm < NIGHT_TO):
            return None
        mx, my = self._xy()
        best = None
        for (x, y, z), s in self.world.map.items():
            if s.get("solid") or (s.get("room") is None and s.get("building") is None):
                continue
            rank = (math.hypot(x - mx, y - my), x, y)
            if best is None or rank < best:
                best = rank
        self.why = {"square": [best[1], best[2]] if best else None}
        if best is not None and best[0] > SLEEP_NEAR:
            return ("goto", "%d %d" % (best[1], best[2]))
        return ("sleep", "")

    def forage(self):
        key = self.world.nearest_unlooted(self.need_mark)
        self.why = {"container": list(key) if key else None}
        if key is None:
            return None
        return ("loot", "%d %d %s" % (key[0], key[1], self.need_mark or "all"))

    def explore(self):
        if self.explore_target not in self.scanned and self._current() is None:
            self.why = {"scanFrom": self.explore_target}
            return ("scan", str(SCAN_R))
        edge = self.world.unexplored_edge()
        self.why = {"edge": list(edge) if edge else None}
        if edge is None:
            return None
        return ("goto", "%d %d" % edge)

    # ---------------------------------------------------------------- the tick
    def _inputs(self):
        me = self.world.me
        ts = self._threats()
        cur = self._current()
        return {"x": me.get("x"), "y": me.get("y"), "health": me.get("health"), "hunger": me.get("hunger"),
                "thirst": me.get("thirst"), "fatigue": me.get("fatigue"), "armed": self._armed(),
                "threats": len(ts), "nearest": self._nearest(ts),
                "running": cur[0] if cur else None, "mode": self._mode(), "fight_s": self._fight_s()}

    def _note_failures(self):
        """The last failed goal sent, with the planner tick that first saw it fail."""
        for seq, (state, why) in sorted(self._finished().items()):
            if state == "failed" and why != PREEMPTED and seq not in self.failures_seen:
                self.failures_seen.add(seq)
                self.last_failed = self.sent[seq] + (self.ticks,)

    def _cooling(self, choice):
        f = self.last_failed
        return f is not None and choice == f[:2] and self.ticks - f[2] < FAILED_COOLDOWN_TICKS

    def tick(self):
        self.ticks += 1
        self._settle_loots()
        self._note_failures()
        inputs = self._inputs()
        self._restart_stall_clock()
        self.need_mark = None
        branch, choice, cooled, tried = None, None, None, {}
        for name in BRANCHES:
            self.why = {}
            c = getattr(self, name)()
            tried[name] = self.why
            if name != "threat" and c is not None and self._cooling(c):   # a threat is never waited out
                cooled = list(c)                 # failed within FAILED_COOLDOWN_TICKS: the next branch is tried
                continue
            if c is not None:
                branch, choice = name, c
                break
        inputs["need"] = self.need_mark
        inputs["cooled"] = cooled
        inputs["branches"] = tried
        goal, args = choice if choice else (None, None)
        sent = False
        if choice is not None and self._differs(goal, args):
            seq = self.link.send(goal, args)
            self.sent[seq] = (goal, args)
            sent = True
            if goal in CONFIG:
                self.scanned.add(self.explore_target)
            else:
                self.running = (goal, args, seq)
                self.out_of_reach_since = self.clock() if goal == "fight" else None
                self.stall_flee = goal == "flee" and tried["threat"].get("flee") == "stalled"
                if branch == "explore":
                    self.explore_target = args
        line = {"wall": self.clock(), "gameMin": self.world.me.get("gameMin"), "branch": branch,
                "inputs": inputs, "goal": goal, "args": args, "sent": sent}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return goal if sent else None
