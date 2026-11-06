"""The tactician's decider (Plan 31 Task 11, variant T; the proposal § 2 "The control model", spec § 3's T bullet):
`Tactician(survive).assess(inputs) -> Decision`, kept on `survive.control_state["tactician"]` (`tactician(survive)`).

Each tick, in order:
1. The triggers (`trigger.Triggers.step`) over the tick's World.
2. The running play's bound (`executors.Exec.bound`): an end is logged (`play_end`) and fires `ended`.
3. The model's answer, in model mode (`source.TacticianSource.poll`): validated against this tick's view, applied
   when it names another play or target than the running one (`source` "model"); a refusal's why reaches the next
   view once (`refusal`). A dirty flight (a trigger fired while it was out) asks again at once.
4. The guards (`GUARDS`, scripted, any play): `hit` (the frame's hit reaction with a standing zombie within
   MELEE_RELEASE_R: the melee takes the tick, the reflex holding its hit-reaction step), `swing` (a standing zombie
   within `executors.SWING_GUARD_R`: the melee starts), `fallen` (in a fight at a standing target, a fallen zombie within FIGHT_REACH
   and no standing one within KEEP_R: it is finished first). Each starts a `fight` (`source` "guard").
5. With no play, or on a trigger, the table answers at zero latency (`table.Table.answer`: a labelled cell, else the
   doctrine, `fallback.doctrine`), applied when it differs from the running play (`source` "table" or "doctrine"); in
   model mode a call starts on the trigger (one in flight, the rest coalesced). With no rule answering, the strategic
   goal layer runs (`GoalExec`, `source` "doctrine", play `travel` to `explore`).
6. The play steps (`executors`): its (branch, owner, command, why) is the Decision.

The modes (`MODE`): "table" (no tactical model call: the trials' default when the bench's table ties the model, and
always under the trial driver's `--no-llm`, whose goal source is the scripted one) or "model" (the triggered call,
the session's goal source an `llm.LLMSource`); `PZA_TACTICIAN` in the environment overrides `MODE`.

The decision line (`inputs`, beside the ladder's own keys: `need`, `consume_refused`, `cooled`, `branches`):
- `play` `{kind, type, target, play_id}`: `kind` the scorecard's label (`tools/trial_score.py`: `fight`, `dress`,
  `loot`, `travel`, `shelter`; a retreat `kite_door`, `kite_shelter`, `kite_stance`, `avoid_door`, `avoid_shelter`, so
  a retreat names its refuge's kind), `type` the play, `target` a zombie id (fight, kite) or the square [x, y] it heads
  to, absent for a dress (its part is no square).
- `tactician` `{play, target, source, bound, age, rule, triggers, play_id, guard, mode, ended, refused}`: the play and
  its target label, its source (model, table, doctrine, guard), the answer's bound, its age in wall seconds, the
  table's cell or the doctrine's rule, this tick's triggers, the guard that took the tick, the mode, a play end read
  this tick `{play_id, end}`, a model answer refused this tick `{why}`.
- The ladder's contract: `branch` "threat" on a fight, kite or avoid tick, with `branches.threat.flee` the retreat's
  why on a kite or avoid tick; `branch` "care" on a dress tick; a strategic tick's branch the ladder step's.

`plays.log` beside `decision.log`: one JSON line a play (`kind` "play": `{play_id, play, source, rule, triggers,
applied_at, wall, gameMin}`), a collected call (`kind` "call": `{trigger, view, answer, play, refused_why, latency_s,
model, coalesced, applied_at, source "model"}`) and a play's end (`kind` "play_end": `{play_id, end, bound_broken,
aids}`)."""
import copy
import json
import os

from agent.base.planner.care import DRESS_RETRY_S
from agent.base.planner.llm import LLMSource
from agent.base.planner.policies import FIGHT_REACH, KEEP_R, MELEE_RELEASE_R, on_floor, standing, zdist
from agent.base.planner.survive import Decision
from agent.base.planner.tactician import executors as X
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician import tview as V
from agent.base.planner.tactician.source import TacticianSource, cli
from agent.base.planner.tactician.table import Table
from agent.base.planner.tactician.trigger import Triggers

MODE = "table"            # the bench's verdict (README.md's first line): the table ties the model
MODES = ("table", "model")
ENV_MODE = "PZA_TACTICIAN"
TACTIC_MODEL = "haiku"    # the model mode's configuration (the bench's cheapest that held; README.md)
PLAYS_LOG = "plays.log"
REFUGE_HOLD_S = 60.0      # wall seconds a refuge whose avoid or shelter ended `failed` or `shun` is left out of the
                          # table's read (a first guess for the trials; the night's shun is longer, night.SHUN_MIN)
STATE_KEY = "tactician"
GUARDS = ("hit", "swing", "fallen")


def tactician(survive):
    """The survive's Tactician, made at the first tick and kept on `control_state`."""
    t = survive.control_state.get(STATE_KEY)
    if t is None:
        t = survive.control_state[STATE_KEY] = Tactician(survive)
    return t


def _mode(survive):
    m = os.environ.get(ENV_MODE) or MODE
    if m not in MODES:
        raise ValueError("%s=%r: expected one of %s" % (ENV_MODE, m, MODES))
    if m == "model" and not isinstance(getattr(survive.goals, "source", None), (LLMSource, X.PlaySource)):
        return "table"   # the scripted goal source (`--no-llm`): no model call of any kind
    if m == "model" and isinstance(survive.goals.source, X.PlaySource) and not isinstance(
            survive.goals.source.inner, LLMSource):
        return "table"
    return m


def _label(play):
    """The scorecard's label of a play (the module docstring)."""
    if play.play not in P.RETREATS:
        return play.play
    t = play.args.get("toward")
    kind = "stance" if t == "stance" else ("door" if isinstance(t, str) and t.startswith("D") else "shelter")
    return "%s_%s" % (play.play, kind)


class Tactician:
    """The decider (the module docstring)."""

    def __init__(self, survive, source=None, table=None, log_path=None):
        self.sv = survive
        self.triggers = Triggers()
        self.table = table if table is not None else Table.load()
        self.mode = _mode(survive)
        self.source = source if source is not None else (
            TacticianSource(cli(TACTIC_MODEL), clock=survive.clock) if self.mode == "model" else None)
        self.log_path = log_path if log_path is not None else os.path.join(
            os.path.dirname(os.path.abspath(survive.log_path)), PLAYS_LOG)
        self.exec = None          # the running play's executor
        self.play_id = 0
        self.last_plays = []      # the last three ends {play, end, bound_broken}
        self.refusal = None       # the last refused answer's why, for the next view once
        self.meta = {}            # the running play's {source, rule, triggers}
        self.dress_held = {}      # part index -> (wall until, the inventory's ids then): a dress that ended `nothing`
        self.refuge_held = {}     # ("door", square) or ("building", id) -> wall until: a refuge that failed
        survive.GOAL_CONTINUE = False   # P30-B dropped (README: what it drops); an instance field, never the class
        survive.DOOR_HELD = False       # P30-C's decision dropped: a door is a play's (README)
        survive.goals.goal_continue = False
        if not isinstance(survive.goals.source, X.PlaySource):
            survive.goals.source = X.PlaySource(survive.goals.source)

    # -- the log ------------------------------------------------------------------------------------------------
    def _log(self, row):
        try:
            with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        except OSError:
            pass

    # -- the view -----------------------------------------------------------------------------------------------
    def view(self, trigger=None):
        ex = self.exec
        play = None if ex is None else {"play": ex.play.play, "target": ex.play.target(), "age_s": round(ex.age(), 1)}
        g = getattr(self.sv.goals, "current", None)
        b = (g.args() if g is not None else {}).get("building")
        goal = None if g is None else {"type": g.TYPE, "building": "B%d" % b if isinstance(b, int) else None}
        v = V.build(self.sv.world, self.triggers, {"trigger": trigger, "play": play, "last_plays": self.last_plays,
                                                   "goal": goal, "refusal": self.refusal})
        return v

    # -- the plays ----------------------------------------------------------------------------------------------
    def _same(self, play):
        ex = self.exec
        return ex is not None and ex.play.play == play.play and ex.play.target() == play.target()

    def _end(self, end, broken=True):
        ex = self.exec
        if ex is None:
            return None
        row = {"kind": "play_end", "play_id": self.play_id, "end": end, "bound_broken": broken, "aids": ex.aids,
               "play": ex.play.play, "wall": self.sv.clock()}
        self._log(row)
        self.last_plays = (self.last_plays + [{"play": ex.play.play, "end": end, "bound_broken": broken}])[-3:]
        if isinstance(ex, X.DressExec) and end == "nothing":   # the care's no-restart rule (care.DRESS_RETRY_S)
            self.dress_held[ex.part] = (self.sv.clock() + DRESS_RETRY_S, frozenset(self.sv.world.inventory))
        if isinstance(ex, X.ShelterExec) and end in ("failed", "shun"):   # no plan, or its doors spent: left out
            until = self.sv.clock() + REFUGE_HOLD_S
            if ex.door is not None:
                self.refuge_held[("door", ex.door)] = until
            if ex.building is not None:
                self.refuge_held[("building", ex.building)] = until
        ex.drop()
        self.exec = None
        self.triggers.note_ended()
        return {"play_id": self.play_id, "end": end}

    def _start(self, play, view, source, rule=None, triggers=()):
        if self.exec is not None:
            self._end("replaced", broken=False)
        now = self.sv.clock()
        cls = X.EXECS.get(play.play)
        if cls is None:
            pin = X.pin_goal(play, view, self.sv.world) if source == "model" else None
            if pin is not None:
                g = getattr(self.sv.goals, "current", None)
                if g is not None and g.running:
                    g.end("superseded", "play")   # the runner closes it and proposes the pin next
                self.sv.goals.source.pin = pin
            ex = X.GoalExec(self.sv, play, now, view, pin)
        else:
            ex = cls(self.sv, play, now, view)
        self.exec = ex
        self.play_id += 1
        self.meta = {"source": source, "rule": rule, "triggers": list(triggers)}
        self._log({"kind": "play", "play_id": self.play_id, "play": play.row(), "source": source, "rule": rule,
                   "triggers": list(triggers), "applied_at": now, "wall": now, "gameMin": self.sv.world.game_min})

    def _masked(self, view):
        """`view` for the table's read: each part a failed dress holds out read not bleeding (the care's no-restart
        rule: no new Dress of it until the inventory gains an item or DRESS_RETRY_S pass, `care.DRESS_RETRY_S`), and each
        refuge a failed avoid or shelter holds out (REFUGE_HOLD_S) left out of `doors` and read no shelter."""
        now, inv = self.sv.clock(), frozenset(self.sv.world.inventory)
        self.dress_held = {i: h for i, h in self.dress_held.items() if now < h[0] and inv <= h[1]}
        self.refuge_held = {k: t for k, t in self.refuge_held.items() if now < t}
        if not self.dress_held and not self.refuge_held:
            return view
        v = copy.deepcopy(view)
        for p in (v.get("body") or {}).get("parts") or ():
            if int(p["label"][1:]) in self.dress_held:
                p["bleeding"] = False
        rows = V.door_rows(self.sv.world)
        v["doors"] = [d for d in v.get("doors") or () if ("door", rows[int(d["label"][1:]) - 1][1]) not in
                      self.refuge_held and ("building", X.building_id(d["building"])) not in self.refuge_held]
        for b in v.get("buildings") or ():
            if ("building", X.building_id(b["label"])) in self.refuge_held:
                b["shelter"] = False
        return v

    def _table(self, view):
        """The table's answer as a Play (the doctrine's strategic default when no rule answers)."""
        view = self._masked(view)
        src, rule, ans = self.table.answer(view)
        if ans is None:
            ans = {"play": "travel", "to": "explore", "gait": "walk", "bound": "arrived", "why": "clear"}
            src, rule = "doctrine", "explore"
        try:
            return P.validate(ans, view), src, rule
        except P.Refused:
            return P.Play("travel", {"to": "explore", "gait": "walk"}, "arrived", "clear"), "doctrine", "explore"

    def _guard(self, view):
        """(guard, zombie label) of the first guard that takes the tick (the module docstring), else None."""
        w = self.sv.world
        labels = {z["id"]: z["label"] for z in view.get("zombies") or ()}
        stand = sorted(standing(w, MELEE_RELEASE_R), key=lambda z: zdist(w, z))
        ids = {id(z): zid for zid, z in w.zombies.items()}
        ex = self.exec
        fighting = ex.play.play == "fight" if ex is not None else False
        if (w.me or {}).get("hitReaction") and stand:
            zid = ids.get(id(stand[0]))
            if not (fighting and ex.zid == zid) and zid in labels:
                return "hit", labels[zid]
        close = [z for z in stand if zdist(w, z) <= X.SWING_GUARD_R]
        if close:
            zid = ids.get(id(close[0]))
            if not (fighting and ex.zid == zid) and zid in labels:
                return "swing", labels[zid]
        if fighting and not standing(w, KEEP_R):
            t = ex.target()
            if t is not None and not on_floor(t):
                fallen = sorted((z for z in w.zombies.values() if on_floor(z) and z.get("x") is not None
                                 and zdist(w, z) <= FIGHT_REACH), key=lambda z: zdist(w, z))
                if fallen and ids.get(id(fallen[0])) in labels:
                    return "fallen", labels[ids[id(fallen[0])]]
        return None

    # -- the tick -----------------------------------------------------------------------------------------------
    def assess(self, inputs):
        sv = self.sv
        sv.need_mark = None   # the need's mark is this tick's (`_assess_ladder` resets it so too)
        fired = self.triggers.step(sv.world, sv.clock())
        tac = {"mode": self.mode, "triggers": fired}
        if self.exec is not None:
            end = self.exec.bound()
            if end is not None:
                tac["ended"] = self._end(end)
        view = self.view(fired[0] if fired else None)
        self.refusal = None
        if self.source is not None:
            r = self.source.poll(view)
            if r is not None:
                applied = r["_play"] is not None and not self._same(r["_play"])
                if applied:
                    self._start(r["_play"], view, "model", triggers=[r["trigger"]])
                if r["refused_why"] is not None:
                    self.refusal = r["refused_why"]
                    tac["refused"] = {"why": r["refused_why"]}
                self._log(dict({k: v for k, v in r.items() if k != "_play"}, kind="call", source="model",
                               applied_at=sv.clock() if applied else None))
            if fired:
                self.source.ask(view, fired[0])          # out already: coalesced into it, the flight marked dirty
            elif self.source.dirty and not self.source.busy():
                self.source.ask(view, "coalesced")       # the triggers coalesced while it was out: asked at once
        g = self._guard(view)
        if g is not None:
            tac["guard"] = g[0]
            self._start(P.Play("fight", {"target": g[1]}, "dead", "lone_chaser"), view, "guard", rule=g[0],
                        triggers=fired)
        elif self.exec is None or (fired and (self.source is None or self.exec is None)):
            play, src, rule = self._table(view)
            if not self._same(play):
                self._start(play, view, src, rule, fired)
        branch, owner, cmd, why = self.exec.step()
        ex = self.exec
        tac.update(play=ex.play.play, target=ex.play.target(), source=self.meta.get("source"), bound=ex.play.bound,
                   age=round(ex.age(), 3), rule=self.meta.get("rule"), play_id=self.play_id)
        line_play = {"kind": _label(ex.play), "type": ex.play.play, "play_id": self.play_id}
        xy = ex.target_xy() if not isinstance(ex, X.FightExec) else None
        if isinstance(ex, (X.FightExec, X.KiteExec)) and ex.zid is not None:
            line_play["target"] = ex.zid
        elif xy is not None:
            line_play["target"] = [round(xy[0], 2), round(xy[1], 2)]
        branches = {}
        if branch == "threat":
            branches["threat"] = dict(why, play=ex.play.play)
            if ex.play.play in P.RETREATS:
                branches["threat"]["flee"] = ex.play.why
        elif branch is not None:
            branches[branch] = dict(why)
        if isinstance(ex, X.GoalExec):
            for k, v in (why.get("tried") or {}).items():
                branches.setdefault(k, v)
        inputs["need"] = sv.need_mark
        inputs["consume_refused"] = sv.consume_refused
        inputs["cooled"] = None
        inputs["branches"] = branches
        inputs["play"] = line_play
        inputs["tactician"] = tac
        return Decision(branch, owner, cmd, inputs)
