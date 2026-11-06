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
    `situation._fight`'s `reach`), so the next want names the zombie the re-pin read and no tick re-pins to the pin it left;
  - `failed dud` after DUD_N strikes that lowered nothing (backed-off ends included) or the meet's `lost no progress`;
    `failed unreached` on the meet's `lost out of reach`; `failed stall` when a close's distance has not fallen for
    STALL_S; each leaves the pin skipped for SKIP_S. Health is never read.
- `Dress` (P1): the doctrine's (`maneuvers.Dress`), failing `crawler near` once a crawler reads within KEEP_R (the
  read's item 2, the crawler as a threat at the dress; D's Dress maneuver ends `superseded` on a standing one only).
"""
import math

from agent.base.planner.doctrine import intents as DI
from agent.base.planner.doctrine.intents import (CLOSE_WALK_R, DUD, GROUND_DONE_R, OFF_ENDS, PROGRESS_R, UNREACHED,
                                                 Avoid, Door, Intent, Order, fallback_press, melee_backoff,
                                                 melee_command, melee_end, press_mode)
from agent.base.planner.doctrine.situation import listed, portals, strike_r
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.mix_2.situation import crawlers_near
from agent.base.planner.policies import (AIM_LEG_S, DISENGAGE_R, DOOR_POST_PACE, chasing, line_to, on_floor,
                                         target_id_ok)
from agent.base.pza1 import Aim, WalkTo
from agent.base.world import me_xy


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
    def _upright(self):
        """(tiles, id, record) of the standing zombies listed free (no door, window or wall between: the wants'
        population), not read dead, nearest first."""
        w, mem, now = self.ctx.world, self.ctx.mem, self.ctx.now()
        near = listed(w, mem, now)
        behind = portals(w, near)
        return [e for e in near if e[1] not in behind and line_to(w, e[2]) is not False and not on_floor(e[2])]

    def repin_to(self):
        """{id, by} of the zombie the tactician's re-pin takes over the pin (the module docstring), else None."""
        mem, now, w = self.ctx.mem, self.ctx.now(), self.ctx.world
        got = self.zombie(self.pin)
        if got is None:
            return None
        d, z = got
        up = self._upright()
        guard = [e for e in up if not mem.backoff.get(e[1]) and target_id_ok(e[1])]
        if (w.me or {}).get("hitReaction"):
            hit = [e for e in guard if e[0] <= K.MELEE_RELEASE_R]
            if hit:
                return None if hit[0][1] == self.pin else {"id": hit[0][1], "by": "hit"}
        swing = [e for e in guard if e[0] <= K.SWING_GUARD_R]
        if swing:
            return None if swing[0][1] == self.pin else {"id": swing[0][1], "by": "swing"}
        if w.weapon is None or on_floor(z):
            return None
        reach = [e for e in up if e[0] <= K.KEEP_R and target_id_ok(e[1]) and mem.skip.get(e[1], -math.inf) <= now]
        if reach and reach[0][1] != self.pin and reach[0][0] < d:
            return {"id": reach[0][1], "by": "second_standing"}
        return None

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
            self.repin = {"id": zid, "by": "handback"}
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
        """D's stand's leg to its ground (`doctrine.intents.Fight._ground_leg`): the stance's walk to the square with a
        wall or a fence at its back, facing the pin, until within GROUND_DONE_R; then the stand is taken there."""
        if self.grounded:
            return None
        mx, my = me_xy(self.ctx.world)
        cx, cy = self.ground[0] + 0.5, self.ground[1] + 0.5
        far = math.hypot(cx - mx, cy - my)
        if far <= GROUND_DONE_R:
            self.grounded = True
            return None
        return self.leg("ground", Aim((cx - mx) / far, (cy - my) / far, min(AIM_LEG_S, far / DOOR_POST_PACE),
                                      targetId=self.pin))

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
