"""Actions (spec § 5): the typed commands the agent sends and the state of each, driven by the `act` lines.

`send(cmd)` checks the command dataclass's fields against the schema's `ACTION_ARGS` (a violation raises TypeError
before anything is written), names it `a<n>`, sends `{seq, aid, type, args}` through the transport and returns its
`Action`. `pump(lines)` takes the list a transport's `lines()` returned and moves each action by its `act` lines:
`sent -> accepted -> progress* -> done | failed`, or `rejected`; an action still open past `deadline_s` wall seconds
from `sent_wall` goes `timeout`, once. The terminal states are final: a late act line is counted in `late_acts`.
Actions knows the transport's seam only, never its files.
"""
import dataclasses
import math
import time
from typing import Any, Optional

from agent.base import pza1

TERMINAL = frozenset(("rejected", "done", "failed", "timeout"))
_ENUMS = {"gait": pza1.GAITS, "ikind": pza1.IKINDS, "filter": pza1.FILTERS}


@dataclasses.dataclass(eq=False)
class Action:
    aid: str
    type: str
    args: dict
    deadline_s: float
    sent_wall: float
    state: str = "sent"             # sent | accepted | rejected | progress | done | failed | timeout
    reason: str = ""
    result: Any = None
    snapshot: Any = None
    acked_wall: Optional[float] = None
    ended_wall: Optional[float] = None
    progress: list = dataclasses.field(default_factory=list)   # every progress act line, whole


def _ok(kind, v):
    if kind == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if kind == "float":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    if kind == "str":
        return isinstance(v, str)
    return isinstance(v, str) and v in _ENUMS[kind]


def check(cmd):
    """The command's args, or TypeError when the command or a field breaks the schema's ACTION_ARGS."""
    typ = getattr(cmd, "TYPE", None)
    if not dataclasses.is_dataclass(cmd) or typ not in pza1.ACTION_ARGS:
        raise TypeError("PZA/1: not a command: %r" % (cmd,))
    want = pza1.ACTION_ARGS[typ]
    args = cmd.args()
    if set(args) != set(want):
        raise TypeError("PZA/1 %s: fields %s, the schema wants %s" % (typ, sorted(args), sorted(want)))
    for name, kind in want.items():
        if not _ok(kind, args[name]):
            raise TypeError("PZA/1 %s.%s: %r is not a %s" % (typ, name, args[name], kind))
    return args


class Actions:
    def __init__(self, transport, clock=time.time):
        self.transport = transport
        self.clock = clock
        self.history = []           # every action sent, in order
        self.unknown_acts = 0       # act lines for an aid never sent
        self.late_acts = 0          # act lines for an action already in a terminal state
        self._n = 0
        self._by_aid = {}
        self._open = []             # actions not yet terminal

    def send(self, cmd, deadline_s=30.0):
        args = check(cmd)
        aid = "a%d" % (self._n + 1)
        self.transport.send({"seq": self.transport.cmd_seq + 1, "aid": aid, "type": cmd.TYPE, "args": args})
        self._n += 1
        a = Action(aid=aid, type=cmd.TYPE, args=args, deadline_s=deadline_s, sent_wall=self.clock())
        self.history.append(a)
        self._by_aid[aid] = a
        self._open.append(a)
        return a

    def stop(self):
        """Send Stop(); the earlier action is left for the mod to end (it answers `failed "superseded"`)."""
        return self.send(pza1.Stop())

    def pump(self, lines):
        now = self.clock()
        for l in lines:
            if l["kind"] == "act":
                self._act(l, now)
        for a in self._open:
            if a.state not in TERMINAL and now - a.sent_wall > a.deadline_s:
                a.state = "timeout"
                a.ended_wall = now
        self._open = [a for a in self._open if a.state not in TERMINAL]

    def _act(self, l, now):
        a = self._by_aid.get(l["aid"])
        if a is None:
            self.unknown_acts += 1
            return
        if a.state in TERMINAL:
            self.late_acts += 1
            return
        state = l["state"]
        if l.get("snapshot") is not None:
            a.snapshot = l["snapshot"]
        if state == "accepted":
            if a.state == "sent":
                a.state = state
            if a.acked_wall is None:
                a.acked_wall = now
        elif state == "progress":
            a.state = state
            a.progress.append(l)
        elif state in ("done", "failed", "rejected"):
            a.state = state
            a.reason = l.get("reason", "")
            a.result = l.get("result")
            a.ended_wall = now

    @property
    def current(self):
        """The last action sent, while it is not in a terminal state; else None."""
        if self.history and self.history[-1].state not in TERMINAL:
            return self.history[-1]
        return None

    def done(self, a):
        return a.state in TERMINAL
