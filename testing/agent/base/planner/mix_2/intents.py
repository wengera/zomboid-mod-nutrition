"""mix_2's intents (Plan 31 Task 13; `task-13-composition-read.md` section 7, mix_2): the doctrine's contract
(`doctrine.intents.Intent`, its README the record), its Avoid, Door and Order imported unchanged, and two intents of its
own:

- `Fight` (P0 for a guard, P3 otherwise: its `p` is its want's): a copy of the doctrine's `Fight`
  (`doctrine/intents.py`, `class Fight`) cut to one pin, with the string state dropped and the tactician's re-pin folded
  into its own `done` test, the melee sent through the doctrine's one call site (`doctrine.intents.melee_command`, which
  reads Task 2's three-field `MeleeInputs` on this tree). To the kill, never one press:
  - within MELEE_RELEASE_R or at a fallen pin, the melee (`press_mode`: `strike`, `shove` unarmed or spent, `finish`),
    nothing while its melee backs off (`wait`); farther, a stand first walks the stance to its ground (`ground`), a
    chaser is met standing in the stance (`stand`, "let it come") until it has not closed for STALL_S, then closed on
    (`close`, D's M1), an idle pin is closed on (`close`: the stance's walk, a walk beyond CLOSE_WALK_R; the seek's
    leg);
  - `done kill` / `done gone` when its pin is read killed, unlisted or past DISENGAGE_R;
  - `done repin` (the tactician's re-pin, the read's item 1: `FightExec.bound`'s `second_standing` and the guards that
    take any play): a hit reaction with another standing zombie nearest within MELEE_RELEASE_R (T's `hit` guard),
    another standing zombie nearest within SWING_GUARD_R (T's `swing` guard), or, armed and the pin standing, another
    standing zombie nearer than the pin within KEEP_R (`second_standing`, its next T's `reach` rule); or the meet's
    `handback` (PZA/1.10; PZA/1.9's `crowd`). The populations are the wants' own (`situation.guard`,
    `situation.reach`, one population: `situation.populations`), so the next want names the zombie the re-pin read
    and no tick re-pins to the pin it left;
  - `done lapsed` (fix 1, review-t13-mix2 F1): a seek Fight whose pin is idle and beyond DANGER_R once the seek's own
    predicate (`situation.lone_idle`, the want's) no longer holds at it (a second standing zombie listed within SEEK_R,
    the pin no longer free or reachable); inside DANGER_R it runs on;
  - `failed handback` (fix 1, F2b): the HANDBACK_MAX-th handback in a row by Fights at one pin (`Mix2.note_handback`;
    a Fight at the pin ending otherwise clears the count): the pin is held out of every Fight's want for SKIP_S
    (`Mix2.hold`) and the arbiter's next answer takes the tick;
  - `done skipped` (fix 1): a Fight made from wants read before the Fight that ended this tick skipped its pin, at a
    pin its own want would skip (every piece but the `hit` and `swing` guards), ends as it acts, the tick handed on;
  - `failed dud` after DUD_N strikes that lowered nothing (backed-off ends included) or the meet's `lost no progress`;
    `failed unreached` on the meet's `lost out of reach`; `failed stall` when a close's distance has not fallen for
    STALL_S; each leaves the pin skipped for SKIP_S. Health is never read. A Fight's `repin` {id, by[, n]} reaches the
    decision line on the tick it ends (`Mix2._note_end`, fix 1, F3).
- `Dress` (P1): the doctrine's (`maneuvers.Dress`), failing `crawler near` once a crawler reads within KEEP_R (the
  read's item 2, the crawler as a threat at the dress; D's Dress maneuver ends `superseded` on a standing one only).
"""
from agent.base.planner.doctrine import intents as DI
from agent.base.planner.doctrine.intents import (CLOSE_WALK_R, DUD, OFF_ENDS, PROGRESS_R, UNREACHED, Avoid, Door,
                                                 Intent, Order, fallback_press, melee_backoff, melee_command,
                                                 melee_end, press_mode)
from agent.base.planner.doctrine.situation import aware, strike_r
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2 import situation as SI
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.mix_2.situation import crawlers_near
from agent.base.planner.policies import AIM_LEG_S, DISENGAGE_R, DOOR_POST_PACE, chasing, on_floor
from agent.base.pza1 import Aim, WalkTo
from agent.base.world import me_xy


UNSKIPPED = ("hit", "swing")   # the guards a fight skip does not hold off (D's "still struck at P0")


class Fight(Intent):
    """The fight to the kill (the module docstring)."""

    kind = "fight"
    p = K.P_FIGHT

    def __init__(self, ctx, want, prev=None):
        self.p = want.p   # P0 for a guard, P3 otherwise
        super().__init__(ctx, want, prev)
        self.pin = want.target
        self.ids = (want.target,)
        self.piece = want.why.get("piece", "fight")
        self.duds = 0
        self.best = None        # (the pin, its least distance) since the stall clock started
        self.best_at = ctx.now()
        self.melee_off = False
        self.closing = False    # a stand that stalled closes on its zombie (D's M1)
        self.repin = None       # {id, by} of the zombie the re-pin read, on its `done repin`
        g = want.why.get("ground")
        self.ground = None if g is None else tuple(g)   # the stand's square (no refuge for a group), else None
        self.grounded = self.ground is None

    # -- the reads ------------------------------------------------------------------------------------------------
    def repin_to(self):
        """{id, by} of the zombie the tactician's re-pin takes over the pin (the module docstring), else None: the
        wants' own reads over their one population (`situation.populations`): the P0 guard (`situation.guard`) when it
        is a `hit` or a `swing` at another zombie, else P3's `reach` (`situation.reach`) at a standing zombie nearer
        than a standing pin (`second_standing`), so the arbiter's next want names the zombie the re-pin read (fix 1,
        review-t13-mix2 F5)."""
        w, mem, now = self.ctx.world, self.ctx.mem, self.ctx.now()
        got = self.zombie(self.pin)
        if got is None:
            return None
        d, z = got
        _, _, free, upright = SI.populations(w, mem, now)
        g = SI.guard(w, mem, now, free, upright)
        if g is not None and SI.piece_of(g) in ("hit", "swing"):
            return None if g.target == self.pin else {"id": g.target, "by": SI.piece_of(g)}
        if on_floor(z):
            return None
        r = SI.reach(w, mem, now, upright)
        if r is not None and r.target != self.pin and r.why["d"] < d:
            return {"id": r.target, "by": "second_standing"}
        return None

    def lapsed(self):
        """A seek Fight's end (fix 1, review-t13-mix2 F1): its pin idle (not aware), beyond DANGER_R, and the seek's
        own predicate (`situation.lone_idle`, the want's) no longer holding at it: a second standing zombie listed
        within SEEK_R, or the pin no longer free or reachable. Inside DANGER_R the Fight runs on."""
        if self.piece != "seek":
            return False
        got = self.zombie(self.pin)
        if got is None or aware(got[1]) or got[0] <= K.DANGER_R:
            return False
        w, mem, now = self.ctx.world, self.ctx.mem, self.ctx.now()
        near, _, _, upright = SI.populations(w, mem, now)
        seek = self.ctx.seek_read() if hasattr(self.ctx, "seek_read") else None
        return SI.lone_idle(w, mem, now, near, upright, seek, pin=self.pin) is None

    # -- the contract ---------------------------------------------------------------------------------------------
    def observe(self):
        super().observe()
        m = self.m
        if m is None:
            return
        span = m.take_span()
        if span is not None and span[0] > 0:
            self.duds = 0 if span[1] is not False else self.duds + span[0]
        end = melee_end(m)
        if end is None:
            return
        kind, why = end
        back = melee_backoff(m)
        if back is not None:
            self.ctx.backoff(m.target)
            self.duds += 1   # consecutive backed-off presses count toward the dud
        elif kind == "other":
            zid = (why or {}).get("id")
            n = self.ctx.note_handback(self.pin)   # fix 1 (review-t13-mix2 F2b): the handbacks in a row at this pin
            self.repin = {"id": zid, "by": "handback", "n": n}
            if n >= K.HANDBACK_MAX:
                self.ctx.hold(self.pin)   # held out of every Fight's want for SKIP_S: the arbiter's next answer
                self.finish("failed", "handback")
            else:
                self.finish("done", "repin")
        elif kind == "lost" and why in UNREACHED:
            self.ctx.skip(m.target)
            self.finish("failed", "unreached")
        elif kind == "lost" and why == DUD:
            self.duds = max(self.duds, DK.DUD_N)   # the meet's own stall: the Fight's dud
        elif kind in OFF_ENDS:
            self.melee_off = True
        self.ctx.retire(m)
        self.m = None

    def check(self):
        if self.end is not None:
            return self.end
        got = self.zombie(self.pin)
        if got is None or got[0] > DISENGAGE_R:
            return "done", "kill" if self.kills else "gone"
        if self.duds >= DK.DUD_N:
            self.ctx.skip(self.pin)
            return "failed", "dud"
        r = self.repin_to()
        if r is not None:
            self.repin = r
            return "done", "repin"
        if self.lapsed():
            return "done", "lapsed"
        if self.state in ("stand", "close"):
            now = self.ctx.now()
            if self.best is None or got[0] < self.best[1] - PROGRESS_R:
                self.best, self.best_at = (self.pin, got[0]), now
            elif now - self.best_at >= DK.STALL_S:
                if self.state == "stand":   # D's M1: a chaser that does not close is closed on, never left standing
                    self.closing, self.best, self.best_at = True, None, now
                    return None
                self.ctx.skip(self.pin)
                return "failed", "stall"
        return None

    def covers(self, want):
        return want.kind == "fight" and want.target == self.pin

    def command(self):
        got = self.zombie(self.pin)
        if got is None:
            return None
        if self.piece not in UNSKIPPED and not SI._ok(self.ctx.mem, self.ctx.now(), (got[0], self.pin, got[1])):
            self.finish("done", "skipped")   # fix 1: made from this tick's wants, read before the Fight that ended
            return None                      # skipped its pin (a stall, a dud): the tick is handed on at once
        d, z = got
        w = self.ctx.world
        if self.ctx.mem.backoff.get(self.pin):
            self.state = "wait"   # its melee backed off: nothing sent at it until BACKOFF_TICKS pass
            return None
        if on_floor(z) or d <= K.MELEE_RELEASE_R:
            self.best, self.best_at = None, self.ctx.now()
            mode = press_mode(w, z)
            self.state = "finish" if mode == "finish" else "meet"
            if self.melee_off or not w.can("melee"):
                return fallback_press(self, self.pin, mode)
            return melee_command(self, self.pin, mode)
        leg = self._ground_leg()
        if leg is not None or self.state == "ground":
            return leg
        if chasing(z) and not self.closing:
            return self.leg("stand", Aim(0.0, 0.0, AIM_LEG_S, targetId=self.pin))
        mx, my = me_xy(w)
        ux, uy = (z["x"] - mx) / d, (z["y"] - my) / d
        if d > CLOSE_WALK_R:
            stop = d - strike_r(w)
            return self.leg("close", WalkTo(mx + ux * stop, my + uy * stop, "walk"))
        return self.leg("close", Aim(ux, uy, min(AIM_LEG_S, (d - strike_r(w)) / DOOR_POST_PACE), targetId=self.pin))

    def _ground_leg(self):
        """D's stand's leg to its ground, D's own method (`doctrine.intents.Fight._ground_leg`, which reads only
        `grounded`, `ground`, `ctx` and `leg`) at this Fight's pin."""
        return DI.Fight._ground_leg(self, self.pin)

    def target_label(self):
        return self.pin

    def branch_why(self):
        why = super().branch_why()
        why.update(target=self.pin, duds=self.duds, piece=self.piece)
        got = self.zombie(self.pin)
        if got is not None:
            why["d"] = got[0]
        if self.repin is not None:
            why["repin"] = self.repin
        return why

    def line(self):
        out = super().line()
        out["piece"] = self.piece
        if self.repin is not None:
            out["repin"] = self.repin
        return out


class Dress(DI.Dress):
    """D's Dress, failing `crawler near` with a crawler within KEEP_R (the module docstring)."""

    piece = "dress"

    def check(self):
        if self.end is None and crawlers_near(self.ctx.world, self.ctx.mem, self.ctx.now(), DK.DRESS_CLEAR_R):
            return "failed", "crawler near"
        return super().check()


def piece_of(intent):
    """The running intent's piece: a Fight's own (its want's), else its kind."""
    return getattr(intent, "piece", None) or intent.kind


INTENTS = {c.kind: c for c in (Fight, Dress, Avoid, Door, Order)}

__all__ = ["Fight", "Dress", "Avoid", "Door", "Order", "INTENTS", "piece_of"]
