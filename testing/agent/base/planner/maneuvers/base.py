"""The maneuver base (Plan 28 Task 7b, survival iteration 22; the architecture review `arch-review-cerebellum.md` § 3.5,
cut 1 of the maneuver layer): a `Maneuver` is one named physical sequence with its own state, sent one command at a
time, beside `policies.Policy` (which decides which sequence runs). Its owner (the Fight, `fight.Fight.m`) asks it for
its next command (`step`), sends that command itself (`Policy.send`) and tells the maneuver (`sent`); the maneuver reads
its own actions' ends and its current action's progress lines (`observe`), and its end (`over`) is None while it runs.
The cross-tick flags a sequence needs live in the maneuver and die with it (the review's § 1.3), never on the Fight.

- `observe()`: every action the maneuver sent and has not yet read terminal is read once at its end (`ended(a,
  current)`: `current` False for an earlier send its own later send superseded, whose late end, a kill among them, is
  still read); the current action's new progress lines are read once each, in order (`progressed(line)`). Once another
  sender's action is current while the maneuver's own has not ended (the Lua supersedes it: one command at a time), the
  maneuver ends `superseded` at once, its late `failed superseded` line still read once.
- `step()`: the next command, or None (a subclass's: it never sends itself).
- `over()`: None while it runs, else its end (a subclass sets it through `_end`); `drained()`: every action it sent has
  been read terminal, so an owner that dropped it may stop observing it.
- `why`: its own fields; `log()` is `{maneuver: name, ...why}`, what its owner logs on every tick it runs.
Idempotent within a tick: a second `observe()` with no new line reads nothing.
"""
import time

from agent.base.planner.policies import running


class Maneuver:
    """One named physical sequence, one command at a time (the module docstring)."""

    name = None   # the maneuver's name, logged as `maneuver`

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.action = None          # the maneuver's current Action: the last command it sent
        self.n = 0                  # the commands it sent
        self.why = {}               # its own fields (`log`)
        self._end = None            # its end, None while it runs (`over`)
        self._open = []             # the Actions it sent not yet read terminal, in send order
        self._seen = 0              # the current action's progress lines read so far

    def sent(self, cmd, action):
        """Its owner sent `cmd` as `action`: the current action from now, read by `observe` until its end."""
        self.action = action
        self._open.append(action)
        self._seen = 0
        self.n += 1

    def running(self):
        """Its current action runs (`policies.running`: the current one, not yet terminal)."""
        return running(self.actions, self.action)

    def observe(self):
        """Its actions' ends and its current action's progress (the module docstring)."""
        a = self.action
        if a is not None:
            for line in a.progress[self._seen:]:
                self.progressed(line)
            self._seen = len(a.progress)
        for b in [b for b in self._open if self.actions.done(b)]:
            self._open.remove(b)
            self.ended(b, b is a)
        if self._end is None and a is not None and not self.actions.done(a) and not self.running():
            self._end = "superseded"   # another sender's action is current: the Lua supersedes this one

    def ended(self, a, current):
        """Hook: action `a` the maneuver sent read terminal (`current`: it is the current one)."""

    def progressed(self, line):
        """Hook: one new progress act line of the current action (the whole line, its `result` the skill's)."""

    def step(self):
        """The next command, or None."""
        raise NotImplementedError

    def over(self):
        """None while the maneuver runs, else its end."""
        return self._end

    def drained(self):
        """Every action it sent has been read terminal."""
        return not self._open

    def log(self):
        """What its owner logs on every tick it runs: `{maneuver: name, ...why}`."""
        return dict({"maneuver": self.name}, **self.why)
