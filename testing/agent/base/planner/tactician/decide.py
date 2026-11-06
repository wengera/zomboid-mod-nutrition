"""The tactician's decider (Plan 31 Task 11, variant T; the proposal § 2 "The control model", spec § 3's T bullet):
`Tactician(survive).assess(inputs) -> Decision`, kept on `survive.control_state["tactician"]` (`tactician(survive)`).

Each tick, in order:
1. `prepare` (the instance switches), then the triggers (`trigger.Triggers.step`) over the tick's World.
2. The running play's bound (`executors.Exec.bound`): an end is logged (`play_end`) and fires `ended`.
3. The model's answer, in model mode (`source.TacticianSource.poll`): validated on the view it was asked on, its
   labels rebound by id to this tick's (`plays.rebind`; fix 1, review-t11 H4: a zombie or door gone is refused
   `gone`), refused `doctrine` when it breaks a rubric rule on this tick's view (the veto), applied when it names another
   play or target id than the running one (`source` "model"); a refusal's why reaches the next view once. Then a call
   on this tick's trigger (`_ask`; fix 1, H3): coalesced into the one out, else started CALL_GAP_S after the last
   start (a trigger inside the gap kept due), at most CALLS_MAX a session.
4. The guards (`GUARDS`, scripted, any play): `hit` (the frame's hit reaction with a standing zombie within
   MELEE_RELEASE_R), `swing` (a standing zombie within `executors.SWING_GUARD_R`), `fallen` (in a fight at a standing
   target, a fallen zombie within FIGHT_REACH and no standing one within KEEP_R). Each starts a `fight` (`guard`).
5. The table (`_table_due`): with no play, after a veto, wherever one of Angus's rules binds this tick's view and the
   running play is of another type (fix 1, H1: the doctrine applied to the running play, in both modes), and in table
   mode on an interrupt (INTERRUPTS) or on any trigger once the play has run TABLE_HOLD_S (fix 1, M2); a running fight
   is held against the dressing while a standing zombie reads within KEEP_R + DRESS_MARGIN, and against a trigger's
   strategic play while its target chases within ENGAGE_R (`_fight_holds`). Its answer (`table.Table.answer`: the
   doctrine where a rule binds, else a labelled cell, else the doctrine; source "table" or "doctrine") starts when it
   differs by type or target id. With no rule answering, the strategic goal layer runs (`travel` to `explore`).
6. The play steps (`executors`): its (branch, owner, command, why) is the Decision.

The modes (`MODE`, "model" by the bench's verdict, README.md's first line): "table" (no tactical model call; always
under the trial driver's `--no-llm`, whose goal source is the scripted one) or "model" (the triggered call, the
session's goal source an `llm.LLMSource`); `PZA_TACTICIAN` in the environment overrides `MODE`.

The decision line (`inputs`, beside the ladder's own keys: `need`, `consume_refused`, `cooled`, `branches`):
- `play` `{kind, type, target, play_id}`: `kind` the scorecard's label (`tools/trial_score.py`: `fight`, `dress`,
  `loot`, `travel`, `shelter`; a retreat `kite_door`, `kite_shelter`, `kite_stance`, `avoid_door`, `avoid_shelter`, so
  a retreat names its refuge's kind), `type` the play, `target` a zombie id (fight, kite) or the square [x, y] it heads
  to, absent for a dress (its part is no square).
- `tactician` `{play, target, source, bound, age, rule, triggers, play_id, guard, mode, ended, refused, table, capped,
  walk_failed}`: the play and
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
from agent.base.planner.policies import (ENGAGE_R, FIGHT_REACH, KEEP_R, MELEE_RELEASE_R, blocked, chasing, on_floor,
                                         standing, zdist)
from agent.base.planner.survive import Decision
from agent.base.planner.tactician import executors as X
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician import rubric as R
from agent.base.planner.tactician import tview as V
from agent.base.planner.tactician.source import TacticianSource, cli
from agent.base.planner.tactician import table as T
from agent.base.planner.tactician.table import Table
from agent.base.planner.tactician.trigger import Triggers

MODE = "model"            # the bench's verdict (README.md's first line): the table does not tie the model, so T runs
                          # the model, the doctrine's veto on (below); the scripted goal source (`--no-llm`) runs the
                          # table whatever MODE reads
MODES = ("table", "model")
ENV_MODE = "PZA_TACTICIAN"
TACTIC_MODEL = "sonnet"   # the model mode's configuration: the bench's default (llm.DEFAULT_CLI's), 17 rubric
                          # violations on 200 views against haiku's 39, p95 7.16 s against 7.13 (README.md's bench)
PLAYS_LOG = "plays.log"
REFUGE_HOLD_S = 60.0      # wall seconds a refuge whose avoid or shelter ended `failed` or `shun` is left out of the
                          # table's read (a first guess for the trials; the night's shun is longer, night.SHUN_MIN)
STATE_KEY = "tactician"
INTERRUPTS = ("hit", "wound", "down", "count", "arrived")   # the triggers that re-answer a running play at once in
                          # table mode (fix 1, review-t11 M2): the hit, a new bleed, a fall, a count band crossed, a
                          # building reached; `notice`, `clear`, `need` and `ended` wait TABLE_HOLD_S
TABLE_HOLD_S = 5.0        # wall seconds a play holds before a non-interrupt trigger may replace it in table mode (fix
                          # 1, review-t11 M2: E23's open loop flipped A->B->A within 10 s 14 times): a first guess for
                          # the trials, about two stance legs of AIM_LEG_S
DRESS_MARGIN = 1.0        # tiles past KEEP_R a standing zombie keeps a running fight against the dressing rule (fix 1,
                          # the rule's hysteresis: `_fight_holds`): a first guess for the trials, a chaser's 0.6 s
                          # at about 1.6 tiles a second (spec section 1)
CALL_GAP_S = 15.0         # wall seconds between two calls' starts (fix 1, review-t11 H3): a trigger inside the gap is
                          # kept due and asked once the gap passes; fitted on the open-loop estimate (README.md: at
                          # sonnet's p50 F15 36 calls and F14 48, 1.8 and 1.71 times their 20 and 28 goal calls,
                          # task-11-tactician-fix-1-calls.json; no gap 77 and 104)
CALLS_MAX = 48            # calls a session at most, after which the table answers alone (fix 1, review-t11 H3): under
                          # twice F14's 28 goal calls (the proposal's 1.6 to 2 times today's); F14's own estimate, 48,
                          # reaches it; the account the agents share (F6's exit 1)
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


def _label(play, view):
    """The scorecard's label of a play (the module docstring): a retreat's refuge kind is `door`, `shelter` (a
    building with a shelter plan), `building` (one without: no REFUGE_WORDS word, fix 1, review-t11 L3) or `stance`."""
    if play.play not in P.RETREATS:
        return play.play
    t = play.args.get("toward")
    if t == "stance":
        kind = "stance"
    elif isinstance(t, str) and t.startswith("D"):
        kind = "door"
    else:
        b = next((b for b in view.get("buildings") or () if b.get("label") == t), {})
        kind = "shelter" if b.get("shelter") else "building"
    return "%s_%s" % (play.play, kind)


def prepare(survive):
    """The ladder's reads this variant drops, switched off on the instance (never the class): P30-B's GOAL_CONTINUE
    and P30-C's DOOR_HELD. The package exports it (`__init__.py`) for the fork's construction hook (`control.prepare_of`
    on main, called at the end of `Survive.__init__`, before any `_read`: fix 2, N2), and `assess` calls it on every
    tick too (a tree without the hook: from the second tick on). It reads nothing but the two switches, so it runs
    whatever part of the instance is built."""
    survive.GOAL_CONTINUE = False   # `Survive._read` copies it into the goal runner on every tick
    survive.DOOR_HELD = False


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
        prepare(survive)          # P30-B and P30-C dropped (README: what it drops), on the instance
        self._last_ask = None     # wall of the last call started (CALL_GAP_S)
        self._due = None          # a trigger inside the gap, asked once it passes
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
    @staticmethod
    def _ref(play, bind):
        """(type, the id its target names) of a play under `bind` (`tview.binding`; fix 1, review-t11 H4: labels are
        distance ranks, so plays compare by id); a literal target (`stance`, `explore`) is itself."""
        t = play.target()
        return play.play, bind.get(t, t)

    def _same(self, play, bind):
        ex = self.exec
        return ex is not None and ex.ref == self._ref(play, bind)

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

    def _start(self, play, view, bind, source, rule=None, triggers=(), end="replaced"):
        """Start `play`; a running play ends `end` ("replaced", or "doctrine" when one of Angus's rules took it: fix 2,
        L2, so `plays.log` alone tells a doctrine break)."""
        if self.exec is not None:
            self._end(end, broken=end == "doctrine")
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
        ex.ref, ex.label = self._ref(play, bind), _label(play, view)
        self.exec = ex
        self.play_id += 1
        self.meta = {"source": source, "rule": rule, "triggers": list(triggers)}
        self._log({"kind": "play", "play_id": self.play_id, "play": play.row(), "source": source, "rule": rule,
                   "triggers": list(triggers), "applied_at": now, "wall": now, "gameMin": self.sv.world.game_min})

    def _masked(self, view):
        """`view` for the table's read: each part a failed dress holds out read not bleeding (the care's no-restart
        rule: no new Dress of it until the inventory gains an item or DRESS_RETRY_S pass, `care.DRESS_RETRY_S`), and each
        refuge a failed avoid or shelter holds out (REFUGE_HOLD_S) left out of `doors` and read no shelter, and each
        zombie a fight's failed walk left unreachable (`Survive.unreachable`, fix 1, review-t11 M3) left out of
        `zombies`, so the table re-routes."""
        now, inv = self.sv.clock(), frozenset(self.sv.world.inventory)
        self.dress_held = {i: h for i, h in self.dress_held.items() if now < h[0] and inv <= h[1]}
        self.refuge_held = {k: t for k, t in self.refuge_held.items() if now < t}
        gone = blocked(self.sv.unreachable, now)
        if not self.dress_held and not self.refuge_held and not gone:
            return view
        v = copy.deepcopy(view)
        v["zombies"] = [z for z in v.get("zombies") or () if z.get("id") not in gone]
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

    # -- the model's calls ----------------------------------------------------------------------------------------
    def _ask(self, view, bind, fired, tac):
        """A call on this tick's trigger (fix 1, review-t11 H3): coalesced into the one out; else started when
        CALL_GAP_S have passed since the last start and fewer than CALLS_MAX were made this session, a trigger inside
        the gap kept due and asked once the gap passes (as a dirty flight is); past CALLS_MAX the table answers alone."""
        s, now = self.source, self.sv.clock()
        if s.busy():
            if fired:
                s.ask(view, fired[0], bind)              # coalesced: the flight marked dirty
            return
        want = fired[0] if fired else ("coalesced" if (s.dirty or self._due) else None)
        if want is None:
            return
        if s.started >= CALLS_MAX:
            self._due, s.dirty = None, False
            tac["capped"] = s.started
            return
        if self._last_ask is not None and now - self._last_ask < CALL_GAP_S:
            self._due = self._due or want
            return
        s.ask(view, want, bind)
        self._last_ask, self._due = now, None

    # -- the tick -----------------------------------------------------------------------------------------------
    def assess(self, inputs):
        sv = self.sv
        sv.need_mark = None   # the need's mark is this tick's (`_assess_ladder` resets it so too)
        prepare(sv)
        fired = self.triggers.step(sv.world, sv.clock())
        tac = {"mode": self.mode, "triggers": fired}
        if self.exec is not None:
            end = self.exec.bound()
            if end is not None:
                tac["ended"] = self._end(end)
        view = self.view(fired[0] if fired else None)
        bind = V.binding(sv.world, view)
        self.refusal = None
        vetoed = False
        if self.source is not None:
            r = self.source.poll(view, bind)
            if r is not None:
                if r["_play"] is not None and R.violations(self._masked(view), r["_play"].row()):
                    r = dict(r, _play=None, play=None, refused_why="doctrine")   # the veto: a rule the doctrine keeps
                    vetoed = True
                applied = r["_play"] is not None and not self._same(r["_play"], bind)
                if applied:
                    self._start(r["_play"], view, bind, "model", triggers=[r["trigger"]])
                if r["refused_why"] is not None:
                    self.refusal = r["refused_why"]
                    tac["refused"] = {"why": r["refused_why"]}
                self._log(dict({k: v for k, v in r.items() if k != "_play"}, kind="call", source="model",
                               applied_at=sv.clock() if applied else None))
            self._ask(view, bind, fired, tac)
        g = self._guard(view)
        if g is not None:
            tac["guard"] = g[0]
            self._start(P.Play("fight", {"target": g[1]}, "dead", "lone_chaser"), view, bind, "guard", rule=g[0],
                        triggers=fired)
        else:
            why = self._table_due(view, fired, vetoed)
            if why is not None:
                play, src, rule = self._table(view)
                tac["table"] = why
                held = why in ("rule", "trigger", "veto") and self._fight_holds(play.row(), why)
                if held:
                    tac["table"] = "held"   # the running fight kept (DRESS_MARGIN in both modes: fix 2, L1)
                elif not self._same(play, bind):
                    self._start(play, view, bind, src, rule, fired,
                                end="doctrine" if why in ("rule", "veto") else "replaced")
        branch, owner, cmd, why = self.exec.step()
        ex = self.exec
        tac.update(play=ex.play.play, target=ex.play.target(), source=self.meta.get("source"), bound=ex.play.bound,
                   age=round(ex.age(), 3), rule=self.meta.get("rule"), play_id=self.play_id)
        if getattr(ex, "walk_failed", None):
            tac["walk_failed"] = ex.walk_failed
        line_play = {"kind": ex.label, "type": ex.play.play, "play_id": self.play_id}
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

    def _fight_holds(self, ans, why):
        """The running fight is kept (the table's hysteresis, fix 1): against the dressing rule while a standing
        zombie reads within KEEP_R + DRESS_MARGIN (the Dress ends `contact` at KEEP_R, so a chaser hovering at its edge
        flipped the fight and the dressing; F15's open loop did 11 times within 10 s, its hands bleeding while the
        zombie hung at 2.5 tiles); and against a trigger's strategic play (loot, travel, shelter) while its target
        stands within ENGAGE_R chasing the character (E23's open loop flipped fight, loot, fight on the count's edge
        at 6 tiles: a zombie coming is cleared before a loot, fallback's `fight` rule)."""
        ex = self.exec
        if ex is None or ex.play.play != "fight":
            return False
        if ans["play"] == "dress":
            return bool(standing(self.sv.world, KEEP_R + DRESS_MARGIN))
        t = ex.target()
        return (why == "trigger" and ans["play"] in P.STRATEGIC and t is not None and t.get("x") is not None
                and not on_floor(t) and chasing(t) and zdist(self.sv.world, t) <= ENGAGE_R)

    def _table_due(self, view, fired, vetoed):
        """Why the table answers this tick, else None (the module docstring's step 5): `none` (no play runs), `veto`
        (a model answer vetoed: the table's play takes over), `rule` (one of Angus's rules binds the masked view and
        the running play is of another type: fix 1, review-t11 H1, the doctrine applied to the running play), `trigger`
        (table mode: an interrupt, or any trigger once the play has run TABLE_HOLD_S: fix 1, review-t11 M2, the
        table's hysteresis)."""
        ex = self.exec
        if ex is None:
            return "none"
        if vetoed:
            return "veto"
        masked = self._masked(view)
        if T.bound(masked):
            _, _, ans = self.table.answer(masked)
            if ans is not None and ans["play"] != ex.play.play:
                return "rule"
        if self.source is None and fired and (any(t in INTERRUPTS for t in fired) or ex.age() >= TABLE_HOLD_S):
            return "trigger"
        return None
