"""The doctrine's arbiter (Plan 31 Task 11, the variant D; the intent-machine proposal's section 2.1): one intent at a
time under six hard priorities, the one-deep resume slot, and the decision line's record of each tick.

`Arbiter.step(wants, make)` takes the tick's wants top down (`situation.read`: the first is the highest; the order's is
always last) and a factory `make(want, prev) -> Intent` (`prev` the intent that ended this tick, else None, for a
hand-over: a Strike's melee kept by the Fight that follows it). Its rules:

1. The running intent's end first: one it set itself (`intent.end`) or its own test (`intent.check()`), `done` or
   `failed`, each with its why; an intent that ended is dropped (`ended` on the tick's event).
2. With no intent running: the slot's intent is resumed when it has not ended by its own test meanwhile and no want
   is strictly higher than it (`resumed`); a higher want starts and the slot is kept for after it; else the top want
   starts.
3. With an intent running, only a want of a strictly higher priority (a lower `p`) pre-empts it, and only when the
   running intent does not already answer that want (`intent.covers(want)`: a Fight's melee is the strike at its own
   zombie). The pre-empted intent waits in the slot (one deep: the newest pre-empted kept; a Strike, the top priority,
   is never pre-empted). Nothing of equal or lower priority interrupts: an equal want with
   another target (a second Fight, a nearer zombie) waits for the running intent's end.

`equal_switches` counts the ticks on which an intent that had not ended was replaced by one of the same priority; by
rule 3 it reads zero by construction (it guards the rule against a mutation, it measures nothing). The measured reading
is the decision line's (`assess.line_switches`, review-t11-doctrine m6): each intent the arbiter starts takes a serial
(`Intent.n`, on `inputs.doctrine.n`), and a line whose serial differs from the line before's at the same `p` with no
`ended` on it is a switch. The tick's event (`step`'s answer) is
`{preempted_by, resumed, ended}`: `preempted_by` `{was, p}` names the intent this tick's pre-empted (the line's own
intent the one that pre-empted it), `resumed` True on the tick the slot's intent came back, `ended` `{intent, p, end,
why}` of an intent that ended this tick."""
ENDS = ("done", "failed")
ENDS_KEPT = 64   # the ended intents `ends` keeps, newest last


class Arbiter:
    """One intent at a time (the module docstring)."""

    def __init__(self):
        self.current = None        # the running intent
        self.slot = None           # the one-deep resume slot: the intent a higher one pre-empted
        self.equal_switches = 0    # rule 3's count, zero by construction
        self.made = 0              # the intents started: each one's serial (`Intent.n`)
        self.ends = []             # (kind, p, end, why) of every intent that ended, in order (bounded by the caller)

    @staticmethod
    def _ended(it):
        """The intent's end, `(done | failed, why)`, set by itself or read by its own test; None while it runs."""
        return it.end if it.end is not None else it.check()

    def step(self, wants, make):
        """The tick's one decision over `wants` (top down); returns the event (the module docstring)."""
        ev = {"preempted_by": None, "resumed": False, "ended": None}
        prev = None
        cur = self.current
        if cur is not None:
            end = self._ended(cur)
            if end is not None:
                ev["ended"] = {"intent": cur.kind, "p": cur.p, "end": end[0], "why": end[1]}
                self.ends = (self.ends + [(cur.kind, cur.p, end[0], end[1])])[-ENDS_KEPT:]
                prev, cur = cur, None
                self.current = None
        top = wants[0]
        if cur is None:
            slot, self.slot = self.slot, None
            if slot is not None and self._ended(slot) is None:
                if top.p < slot.p:
                    self.slot = slot
                else:
                    self._set(slot, ended=True)
                    slot.resume()
                    adopt = getattr(slot, "adopt", None)
                    if adopt is not None:
                        adopt(prev)   # m2: the ended intent's melee handed over or retired, never orphaned
                    ev["resumed"] = True
                    return ev
            self._set(make(top, prev), ended=True)
            return ev
        if top.p < cur.p and not cur.covers(top):
            cur.suspend()
            self.slot = cur
            self._set(make(top, None), ended=False, was=cur)
            ev["preempted_by"] = {"was": cur.kind, "p": cur.p}
        return ev

    def _set(self, new, ended, was=None):
        """`new` the running intent; an unended predecessor of the same priority counts in `equal_switches`."""
        if was is not None and not ended and new.p == was.p:
            self.equal_switches += 1
        if getattr(new, "n", None) is None:
            self.made += 1
            new.n = self.made
        self.current = new
