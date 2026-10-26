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
- A loot goal that finishes, done or failed, marks every container on its square looted, so a failing square is not
  retried. An explore walk that finishes is followed by one `scan` from where it ended.
"""
import json
import math

from agent.world import FOOD_RX, WATER_RX

DANGER_R = 6.0        # a zombie this close is a threat
THIRST_T = 0.5
HUNGER_T = 0.5
FATIGUE_T = 0.7
FLEE_HEALTH = 40.0    # PZA.act.FLEE_HEALTH: under it a threat is fled, never fought
MAX_FIGHT = 2         # more threats than this are fled
FLEE_DIST = 8         # tiles, when no known square lies away from the threats
NIGHT_FROM, NIGHT_TO = 21 * 60, 6 * 60   # game minutes of the day
SLEEP_NEAR = 1.5      # within this of the chosen indoor square, sleep where standing
SCAN_R = 10
BRANCHES = ("threat", "need", "sleep", "forage", "explore")
BY_NAME = ("fight", "flee")
CONFIG = ("scan",)
FINISHED = ("done", "failed")


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

    # ---------------------------------------------------------------- reading the world
    def _xy(self):
        me = self.world.me
        return me.get("x", 0.0), me.get("y", 0.0)

    def _threats(self):
        mx, my = self._xy()
        return [z for z in self.world.zombies.values()
                if z.get("x") is not None and math.hypot(z["x"] - mx, z["y"] - my) <= DANGER_R]

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

    # ---------------------------------------------------------------- the branches, in order
    def threat(self):
        ts = self._threats()
        if not ts:
            return None
        health = self.world.me.get("health", 100.0)
        if self._armed() and len(ts) <= MAX_FIGHT and health >= FLEE_HEALTH:
            return ("fight", "")
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
            return ("flee", "%d %d" % (best[1], best[2]))
        mx, my = self._xy()
        vx, vy = mx - cx, my - cy
        n = math.hypot(vx, vy) or 1.0
        return ("flee", "%d %d" % (math.floor(mx + vx / n * FLEE_DIST), math.floor(my + vy / n * FLEE_DIST)))

    def need(self):
        me = self.world.me
        food, water_ok = self._held()
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
        if best is not None and best[0] > SLEEP_NEAR:
            return ("goto", "%d %d" % (best[1], best[2]))
        return ("sleep", "")

    def forage(self):
        key = self.world.nearest_unlooted(self.need_mark)
        if key is None:
            return None
        return ("loot", "%d %d %s" % (key[0], key[1], self.need_mark or "all"))

    def explore(self):
        if self.explore_target not in self.scanned and self._current() is None:
            return ("scan", str(SCAN_R))
        edge = self.world.unexplored_edge()
        if edge is None:
            return None
        return ("goto", "%d %d" % edge)

    # ---------------------------------------------------------------- the tick
    def _inputs(self):
        me = self.world.me
        ts = self._threats()
        mx, my = self._xy()
        cur = self._current()
        return {"x": me.get("x"), "y": me.get("y"), "health": me.get("health"), "hunger": me.get("hunger"),
                "thirst": me.get("thirst"), "fatigue": me.get("fatigue"), "armed": self._armed(),
                "threats": len(ts),
                "nearest": min((math.hypot(z["x"] - mx, z["y"] - my) for z in ts), default=None),
                "running": cur[0] if cur else None}

    def tick(self):
        self._settle_loots()
        inputs = self._inputs()
        self.need_mark = None
        branch, choice = None, None
        for name in BRANCHES:
            choice = getattr(self, name)()
            if choice is not None:
                branch = name
                break
        inputs["need"] = self.need_mark
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
                if branch == "explore":
                    self.explore_target = args
        line = {"wall": self.clock(), "gameMin": self.world.me.get("gameMin"), "branch": branch,
                "inputs": inputs, "goal": goal, "args": args, "sent": sent}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return goal if sent else None
