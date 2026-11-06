"""mix_1's decider (Plan 31 Task 13; `task-13-composition-read.md` § 7): the tactician's `Tactician` whole
(`tactician.decide`, 829038d6: its triggers, the running play's bound, the model in model mode with the doctrine's veto,
the guards, the table, the executors, `PlaySource`), kept on `survive.control_state["mix_1"]`, with the two pieces of
`rules.py` wired in:

1. **`clear`** (the ladder's lone-idle seek, `engage.Engage._sought` cut to one zombie): each tick `_clear_label`
   reads `rules.lone` on the tick's view and asks the Survive instance's own `_engageable` (`engage.py`, Task 18 fix 1:
   its side, chase, line and bounded-flood reading, its `unsought` marks and its cached flood, called on the instance
   and never copied) whether that zombie may be engaged; the label goes on the masked view as `clear`, which the
   doctrine, the table, the bound and the veto read (`_masked`).
2. **The crawler**: a `crawler` guard after the tactician's three (`_guard`): a crawler within KEEP_R (`rules.
   is_crawler`), nothing standing within KEEP_R, the running play no retreat, and no finish at hand already running
   at a zombie on the floor as near (within the ladder's re-pin margin, `policies.REPIN_MARGIN` 0.3: trial 10's ring,
   the knocked-down 15436 at 2.0 tiles finished while the crawler bit at 0.9) → a `fight` at the nearest such crawler
   (the executor's mode `finish`, its target on the floor). A
   running finish at hand (a zombie on the floor within KEEP_R, a crawler or one knocked down, nothing standing within
   KEEP_R) is held against the table's other answers but a retreat (`_fight_holds`), so a trigger does not hand it to
   a travel or to a standing zombie beyond KEEP_R and back. The dressing waits for it (`rules.keep_clear`).

What is copied, and why: `Tactician.assess` and `Tactician._table_due` read the tactician's own `rubric.violations` and
`table.bound` by module name, so this module carries both bodies as they stand at 829038d6 with those two reads pointed
at `rules` (`_veto`, `rules.bound`), the view's `clear` computed before the first read, and the decision line's
`mix_1` key added. Every other method is the tactician's, inherited.

The decision line keeps the tactician's keys (`play`, `tactician`, `branches`, `need`, `consume_refused`, `cooled`)
and adds `inputs.mix_1` `{piece, added, started, kind, play, target, clear}`: `piece` the rule that decided the tick,
the running play's starter (`guard.hit`, `guard.swing`, `guard.fallen`, `guard.crawler`, `rule.<doctrine rule>`
(`rule.clear` among them), `table`, `model`); `added` true for mix_1's two pieces (ADDED); `started` true on the
tick its play began; `kind` the scorecard's label (`inputs.play.kind`: `fight`, `dress`, `loot`, `travel`, `shelter`,
or a retreat `kite_*`/`avoid_*`); `play` the play type; `target` a zombie id (fight, kite), a square [x, y] (the rest),
or the part label of a dress; `clear` the zombie id the `clear` rule could fight this tick, else None."""
from agent.base.planner.policies import KEEP_R, REPIN_MARGIN, blocked, on_floor, standing, zdist
from agent.base.planner.survive import Decision
from agent.base.planner.tactician import decide as TD
from agent.base.planner.tactician import executors as X
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician import tview as V
from agent.base.planner.mix_1 import rules as M

STATE_KEY = "mix_1"
ADDED = ("rule.clear", "guard.crawler")   # the pieces mix_1 adds to the tactician (the module docstring)
GUARDS = TD.GUARDS + ("crawler",)


def mix(survive):
    """The survive's Mix1, made at the first tick and kept on `control_state`."""
    t = survive.control_state.get(STATE_KEY)
    if t is None:
        t = survive.control_state[STATE_KEY] = Mix1(survive)
    return t


def piece_of(meta):
    """The piece name of a play's starter (the module docstring) from the decider's `meta` {source, rule}."""
    src, rule = meta.get("source"), meta.get("rule")
    if src == "guard":
        return "guard.%s" % rule
    if src == "doctrine":
        return "rule.%s" % rule
    return src


class Mix1(TD.Tactician):
    """The tactician with `clear` and the crawler (the module docstring)."""

    def __init__(self, survive, source=None, table=None, log_path=None):
        super().__init__(survive, source=source, table=table if table is not None else M.Table.load(),
                         log_path=log_path)
        self._clear = None        # this tick's `clear` label (`_clear_label`), on every masked view
        self._clear_id = None     # ... and its zombie id, for the line
        self._by_clear = False    # this tick's `rule` path fired on the lone zombie's binding alone

    # -- piece 1: the lone zombie's reach -----------------------------------------------------------------------------
    def _clear_label(self, view):
        """The label `clear` may fight this tick (`rules.lone` on the unmasked view, so an unreachable second zombie
        still counts against "alone"), when the zombie is neither read dead nor left unreachable and the instance's
        `_engageable` (engage.py) reads it reachable; else None."""
        label = M.lone(view)
        if label is None:
            return None, None
        zid = next((z["id"] for z in view.get("zombies") or () if z.get("label") == label), None)
        z = self.sv.world.zombies.get(zid)
        now = self.sv.clock()
        if z is None or zid in blocked(self.sv.unreachable, now) | blocked(self.sv.dead, now):
            return None, None
        if not self.sv._engageable(zid, z):
            return None, None
        return label, zid

    def _masked(self, view):
        """The tactician's masked view (`Tactician._masked`) with this tick's `clear` label on it (a shallow copy:
        the rules only read it)."""
        return dict(super()._masked(view), clear=self._clear)

    # -- piece 2: the crawler ------------------------------------------------------------------------------------------
    def _guard(self, view):
        """The tactician's guards (`hit`, `swing`, `fallen`), then `crawler` (the module docstring)."""
        g = super()._guard(view)
        return g if g is not None else self._crawler_guard(view)

    def _crawler_guard(self, view):
        w = self.sv.world
        if standing(w, KEEP_R):
            return None   # the standing first: the swing guard, the `reach` rule (the tactician's order)
        ex = self.exec
        if ex is not None and ex.play.play in P.RETREATS:
            return None   # a retreat runs on: the crawler is left behind at a crawl
        now = self.sv.clock()
        skip = blocked(self.sv.dead, now) | blocked(self.sv.unreachable, now)
        labels = {z["id"]: z["label"] for z in view.get("zombies") or ()}
        near = sorted(((zid, z) for zid, z in w.zombies.items() if zid in labels and zid not in skip
                       and z.get("x") is not None and z.get("y") is not None and M.is_crawler(z)
                       and zdist(w, z) <= KEEP_R), key=lambda r: (zdist(w, r[1]), r[0]))
        if not near:
            return None
        zid, z = near[0]
        if ex is not None and ex.play.play == "fight" and self._finishing(ex) and (
                ex.zid == zid or zdist(w, ex.target()) < zdist(w, z) + REPIN_MARGIN):
            return None   # a zombie on the floor at hand, as near or nearer, is being finished (held: `_fight_holds`)
        return "crawler", labels[zid]

    def _fight_holds(self, ans, why):
        """The tactician's two holds, and a finish at hand: a running fight at a zombie on the floor within KEEP_R (a
        crawler, or one knocked down), nothing standing within KEEP_R, held against every answer but a retreat (the
        module docstring). The crawler guard leaves such a finish running, so the hold is the guard's other half: the
        tactician's table hands a finish at 0.9 tiles to a travel on a `down` trigger (trial 10's ring, 15436 at 0.9
        with the crawler at 2.2), and the guard would then take the crawler and leave the knocked-down zombie to rise."""
        if super()._fight_holds(ans, why):
            return True
        ex = self.exec
        if ex is None or ex.play.play != "fight" or ans["play"] in P.RETREATS:
            return False
        return self._finishing(ex)

    def _finishing(self, ex):
        """`ex`, a fight, is at a zombie on the floor within KEEP_R and nothing stands within KEEP_R."""
        t, w = ex.target(), self.sv.world
        return (t is not None and t.get("x") is not None and on_floor(t) and zdist(w, t) <= KEEP_R
                and not standing(w, KEEP_R))

    # -- the copies (the module docstring: the tactician's bodies at 829038d6, two reads pointed at `rules`) ------------
    def _veto(self, view, row):
        return M.violations(self._masked(view), row)

    def _table_due(self, view, fired, vetoed):
        """`Tactician._table_due` with `rules.bound` (the tactician's `table.bound` plus the lone zombie's
        `clear_due`). Where the lone zombie binds, a running fight at another zombie re-pins to it too (`rule`; F15's
        ring: a table fight at the idle 16038 at 9.9 tiles held on while the aware 16032 came at 8.7), unless that
        fight is a finish at hand (`_fight_holds`). A `rule` answer only the lone zombie's binding gives is marked
        `_by_clear`, and its play starts with the rule `clear` (piece 1: an aware zombie coming within ENGAGE_R, which
        the doctrine's `fight` rule names, fought at once over a running play)."""
        ex = self.exec
        if ex is None:
            return "none"
        if vetoed:
            return "veto"
        masked = self._masked(view)
        if M.bound(masked):
            _, _, ans = self.table.answer(masked)
            lone = M.clear_due(masked)
            if ans is not None and (ans["play"] != ex.play.play or (
                    lone and isinstance(ex, X.FightExec) and ex.zid != self._clear_id)):
                self._by_clear = lone and not (M.fight_due(masked) or M.dress_due(masked))   # the lone zombie's alone
                return "rule"
        if self.source is None and fired and (any(t in TD.INTERRUPTS for t in fired) or ex.age() >= TD.TABLE_HOLD_S):
            return "trigger"
        return None

    def assess(self, inputs):
        """`Tactician.assess` (829038d6) with the veto read off `rules.violations`, `clear` read first, and the line's
        `mix_1` key."""
        sv = self.sv
        sv.need_mark = None
        TD.prepare(sv)
        fired = self.triggers.step(sv.world, sv.clock())
        tac = {"mode": self.mode, "triggers": fired}
        if self.exec is not None:
            end = self.exec.bound()
            if end is not None:
                tac["ended"] = self._end(end)
        view = self.view(fired[0] if fired else None)
        bind = V.binding(sv.world, view)
        self._clear, self._clear_id = self._clear_label(view)
        self._by_clear = False
        started_at = self.play_id
        self.refusal = None
        vetoed = False
        if self.source is not None:
            r = self.source.poll(view, bind)
            if r is not None:
                if r["_play"] is not None and self._veto(view, r["_play"].row()):
                    r = dict(r, _play=None, play=None, refused_why="doctrine")
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
                if why == "rule" and self._by_clear:
                    rule = "clear"
                tac["table"] = why
                held = why in ("rule", "trigger", "veto") and self._fight_holds(play.row(), why)
                if held:
                    tac["table"] = "held"
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
        piece = piece_of(self.meta)
        target = line_play.get("target")
        if target is None and isinstance(ex, X.DressExec):
            target = ex.play.args.get("part")
        inputs["need"] = sv.need_mark
        inputs["consume_refused"] = sv.consume_refused
        inputs["cooled"] = None
        inputs["branches"] = branches
        inputs["play"] = line_play
        inputs["tactician"] = tac
        inputs[STATE_KEY] = {"piece": piece, "added": piece in ADDED, "started": self.play_id != started_at,
                             "kind": ex.label, "play": ex.play.play, "target": target, "clear": self._clear_id}
        return Decision(branch, owner, cmd, inputs)
