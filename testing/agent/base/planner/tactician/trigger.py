"""The tactician's triggers (Plan 31 Task 11, variant T; the proposal § 2): the situation changes the model is asked on,
never a clock. `Triggers.step(world, now)` reads one frame (the bench: every frame of a ring; live: every planner tick)
and returns the triggers it fires, in TRIGGERS order, each once per change:

- `notice`: a standing zombie within NOTICE_R (12, the listing's edge `policies.LISTED_R`) that was not within it at
  any read in the last NOTICE_GAP_S (10 s).
- `count`: the standing count within DANGER_R (6), by band (0, 1, 2, 3 or more: COUNT_TOP), reads a band other than
  the last fired one for COUNT_HOLD_S unbroken (fix 1, review-t11 H3: the raw count flickered, F14's 140 of 210
  trigger ticks and F15's 132 of 176 were `count`); a change inside the top band, or one back within the hold, fires
  nothing.
- `hit`: the frame's `me.hitReaction` turns non-empty (a zombie attack that reached the damage roll).
- `wound`: a part reads `bleeding` that did not at the last read.
- `down`: a zombie within DANGER_R turns `onFloor`, or a `zombie_dead` event arrived since the last read.
- `clear`: no zombie listed within NOTICE_R for CLEAR_S (5 s) unbroken; once per clear stretch.
- `arrived`: the player's square turns a room square (a building reached).
- `need`: thirst over THIRST_T, hunger over HUNGER_T or fatigue over TIRED_T, crossed upward since the last read.
- `ended`: a play ended (`note_ended`, the executor's; never read off a frame).

The tracker beside them: `closing(zid)` the zombie's closing speed in tiles a second (positive closing), over the
oldest of its distance samples within CLOSING_WINDOW_S (1.5 s) at least CLOSING_MIN_S (0.4 s) old, else None; the
tactical view reads it (`tview`).

Every constant: a first guess for the trials but the radii, which are the planner's (`policies.DANGER_R`, LISTED_R)
and the proposal's (the 10 s notice gap and the 5 s clear hold, `rebuild-proposal-model-tactician.md` § 2)."""
from collections import deque

from agent.base.planner.night import TIRED_T
from agent.base.planner.policies import DANGER_R, LISTED_R, on_floor, zdist
from agent.base.world import me_floor, me_xy

TRIGGERS = ("notice", "count", "hit", "wound", "down", "clear", "arrived", "need", "ended")
COUNT_TOP = 3            # the top band of `count`: 3 or more standing within DANGER_R (fallback.GROUP_N, the group)
COUNT_HOLD_S = 1.0       # wall seconds a new band must hold before `count` fires (fix 1, review-t11 H3: "hold it for
                         # about 1 s"): two planner ticks at PLANNER_HZ 2
NOTICE_R = LISTED_R      # tiles: the listing's edge (policies.LISTED_R, #4268)
NOTICE_GAP_S = 10.0      # wall seconds a zombie must have been out of NOTICE_R before it is noticed again (the proposal)
CLEAR_S = 5.0            # wall seconds with nobody within NOTICE_R before `clear` fires (the proposal)
CLOSING_WINDOW_S = 1.5   # wall seconds of distance samples the closing speed reads (a first guess for the trials)
CLOSING_MIN_S = 0.4      # ... the oldest at least this old (a first guess: four frames at the Lua's 10 Hz)
THIRST_T = 0.12          # the first THIRST moodle (#0509; survive.THIRST_T)
HUNGER_T = 0.15          # the first HUNGRY moodle (#0508; survive.HUNGER_T)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _bleeding(world):
    parts = (world.body or {}).get("parts")
    return {p.get("i") for p in parts if isinstance(p, dict) and p.get("bleeding") is True} if isinstance(
        parts, list) else set()


def _inside(world):
    me = world.me or {}
    if not (_num(me.get("x")) and _num(me.get("y"))):
        return False
    x, y = me_xy(world)
    sq = (int(x // 1), int(y // 1), me_floor(world))
    return (world.map.get(sq) or {}).get("room") is not None


class Triggers:
    """The triggers and the closing tracker (the module docstring)."""

    def __init__(self, banded=True):
        """`banded` False: `count` on every change of the raw count, no hold (the triggers before fix 1, which chose
        the bench's recorded views: `tools/tactician_bench.py` keeps them, so its recording's shas hold)."""
        self.banded = banded
        self.within = {}          # zombie id -> wall of its last read within NOTICE_R
        self.count = None         # the last fired band of the standing count within DANGER_R (COUNT_TOP)
        self._band_since = None   # (band, wall) of a band other than `count` read since, until it holds COUNT_HOLD_S
        self.hit = False          # the last read's hit reaction was set
        self.bleeding = set()     # the last read's bleeding part indices
        self.floor = set()        # the ids within DANGER_R read onFloor at the last read
        self.clear_since = None   # wall of the first read of the current clear stretch, else None
        self.clear_fired = False  # `clear` fired in this stretch
        self.inside = None        # the last read's inside
        self.needs = {}           # stat -> above its mark at the last read
        self.samples = {}         # zombie id -> deque of (wall, tiles)
        self._event = None        # the last event line read (identity)
        self._ended = False       # a play ended since the last step (`note_ended`)
        self.reads = 0            # the reads stepped
        self.fired = {t: 0 for t in TRIGGERS}

    def note_ended(self):
        """A play ended: `ended` fires at the next step."""
        self._ended = True

    def closing(self, zid):
        """The zombie's closing speed in tiles a second, else None (the module docstring)."""
        s = self.samples.get(zid)
        if not s or len(s) < 2:
            return None
        t1, d1 = s[-1]
        old = next(((t, d) for t, d in s if t1 - t >= CLOSING_MIN_S), None)
        if old is None:
            return None
        return (old[1] - d1) / (t1 - old[0])

    def _track(self, world, now):
        live = set()
        for zid, z in world.zombies.items():
            if z.get("x") is None or z.get("y") is None:
                continue
            live.add(zid)
            s = self.samples.setdefault(zid, deque())
            s.append((now, zdist(world, z)))
            while s and now - s[0][0] > CLOSING_WINDOW_S:
                s.popleft()
        for zid in [k for k in self.samples if k not in live]:
            del self.samples[zid]

    def _deaths(self, world):
        """Whether a `zombie_dead` event arrived since the last read (the World's event deque, read back to the last
        line seen)."""
        ev = world.events
        if not ev:
            return False
        last, self._event = self._event, ev[-1]
        if self.reads == 0:
            return False   # the first read: the events before it are the session's past, never a change
        for line in reversed(ev):
            if line is last:
                return False
            if line.get("event") == "zombie_dead":
                return True
        return False

    def step(self, world, now):
        """The triggers this read fires, in TRIGGERS order (the module docstring)."""
        out = []
        self._track(world, now)
        listed = [(zid, z, zdist(world, z)) for zid, z in world.zombies.items()
                  if z.get("x") is not None and z.get("y") is not None]
        standing = [(zid, z, d) for zid, z, d in listed if not on_floor(z)]
        notice = False
        for zid, z, d in standing:
            if d <= NOTICE_R:
                last = self.within.get(zid)
                if last is None or now - last > NOTICE_GAP_S:
                    notice = True
        for zid, z, d in listed:
            if d <= NOTICE_R:
                self.within[zid] = now
        if notice:
            out.append("notice")
        n = sum(1 for _, _, d in standing if d <= DANGER_R)
        band = min(n, COUNT_TOP) if self.banded else n
        if not self.banded:
            if self.count is not None and band != self.count:
                out.append("count")
            self.count = band
        elif self.count is None:
            self.count = band
        elif band == self.count:
            self._band_since = None
        else:
            if self._band_since is None or self._band_since[0] != band:
                self._band_since = (band, now)
            if now - self._band_since[1] >= COUNT_HOLD_S:
                out.append("count")
                self.count, self._band_since = band, None
        hit = bool((world.me or {}).get("hitReaction"))
        if hit and not self.hit:
            out.append("hit")
        self.hit = hit
        bleeding = _bleeding(world)
        if bleeding - self.bleeding:
            out.append("wound")
        self.bleeding = bleeding
        floor = {zid for zid, z, d in listed if d <= DANGER_R and on_floor(z)}
        if (floor - self.floor) or self._deaths(world):
            out.append("down")
        self.floor = floor
        if any(d <= NOTICE_R for _, _, d in listed):
            self.clear_since, self.clear_fired = None, False
        else:
            if self.clear_since is None:
                self.clear_since = now
            if not self.clear_fired and now - self.clear_since >= CLEAR_S:
                out.append("clear")
                self.clear_fired = True
        inside = _inside(world)
        if inside and self.inside is False:
            out.append("arrived")
        self.inside = inside
        st = world.stats or {}
        crossed = False
        for k, t in (("thirst", THIRST_T), ("hunger", HUNGER_T), ("fatigue", TIRED_T)):
            above = _num(st.get(k)) and st[k] > t
            if above and self.needs.get(k) is False:
                crossed = True
            self.needs[k] = above
        if crossed:
            out.append("need")
        if self._ended:
            out.append("ended")
            self._ended = False
        for t in out:
            self.fired[t] += 1
        self.reads += 1
        return out
