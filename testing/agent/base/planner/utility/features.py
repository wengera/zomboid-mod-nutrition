"""The situation's features (Plan 31 Task 11 U; the proposal's § 2): what one frame tells the selector, read off the
World alone, plus the few readings that need the frames before it (`Tracks`: each zombie's closing speed, the hit
reaction's and the bleeding's onsets). Nothing here decides; `acts.py` turns a `Situation` into candidates and
`select.py` scores them.

- `Zed`: one listed zombie, the dead ones left out (`read`'s `dead`): its distance, `standing` (not `onFloor`),
  `chasing` (`hasTarget`), `aware` (chasing, and PZA/1.9's `known` not false: a zombie with a target it has not seen
  just now still reads chasing on a ring before PZA/1.9, whose `known` is null), `attacking` (PZA/1.9's `state` in
  ATTACK_STATES), its health and its closing speed (tiles a second, positive closing; `Tracks`).
- `Part`: one bleeding body part (`body.parts` reading `bleeding` true), `leg` from `care.LEG_FIRST` (#4337: a
  bandage on a leg or a foot stops on a walk).
- `Situation`: the frame's player (position, armed and the weapon's reach, health, the arms' pain, endurance and
  fatigue, moving, aiming, the hit reaction, the attackers), the zombies nearest first, the bleeding parts worst
  first, and whether the player stands on a room square (`policies.on_room`) of which building.
- `Tracks.update(world, now)`: once a tick before `read`; the closing speed is an EMA (CLOSING_EMA) of each zombie's
  distance change over the wall clock between the ticks it was listed; `hit_onset` is True on the tick the frame's
  `me.hitReaction` turns non-empty, `new_bleeding` the part indices bleeding now and not on the last tick (the
  selector's two body interrupts).
"""
import dataclasses
import math

from agent.base.planner.care import LEG_FIRST
from agent.base.planner.policies import on_room
from agent.base.world import me_floor

ATTACK_STATES = ("attack", "attack-network", "lunge", "lunge-network")   # PZA/1.9's `state` names of a zombie in its
                                                                         # attack or its lunge (the schema's list)
CLOSING_EMA = 0.5         # the closing speed's smoothing: each tick's read weighs this much against the last (a first
                          # guess for the trials: two planner ticks, about a second)
CLOSING_DT_MIN = 0.05     # seconds: a distance change over less wall time than this is not read as a speed


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@dataclasses.dataclass(frozen=True)
class Zed:
    id: object
    x: float
    y: float
    d: float
    standing: bool
    chasing: bool
    aware: bool
    attacking: bool
    health: object
    closing: float

    @property
    def fallen(self):
        return not self.standing


@dataclasses.dataclass(frozen=True)
class Part:
    i: int
    bleeding_time: float
    h: object

    @property
    def leg(self):
        return self.i >= LEG_FIRST


@dataclasses.dataclass(frozen=True)
class Situation:
    now: float
    x: float
    y: float
    z: int
    armed: bool
    reach: float
    health: float
    arm_pain: object
    endurance: object
    fatigue: object
    moving: bool
    aiming: bool
    hit_reaction: str
    attackers: int
    zeds: tuple            # Zed, nearest first
    bleeding: tuple        # Part, the longest bleeding first
    on_room: bool
    building: object
    hit_onset: bool = False
    new_bleeding: tuple = ()

    def standing(self, r):
        return [z for z in self.zeds if z.standing and z.d <= r]

    def aware_standing(self, r):
        return [z for z in self.zeds if z.standing and z.aware and z.d <= r]

    def nearest_standing(self):
        return next((z for z in self.zeds if z.standing), None)

    def zed(self, zid):
        return next((z for z in self.zeds if z.id == zid), None)


class Tracks:
    """The readings across frames (the module docstring)."""

    def __init__(self):
        self.last = {}            # zombie id -> (wall, d)
        self.closing = {}         # zombie id -> tiles a second
        self.hit = ""             # the last tick's `me.hitReaction`
        self.bleeding = frozenset()
        self.hit_onset = False
        self.new_bleeding = ()

    def update(self, world, now, dead=()):
        me = world.me or {}
        mx, my = me.get("x"), me.get("y")
        seen = {}
        if _num(mx) and _num(my):
            for zid, z in world.zombies.items():
                if zid in dead or not (_num(z.get("x")) and _num(z.get("y"))):
                    continue
                d = math.hypot(z["x"] - mx, z["y"] - my)
                seen[zid] = (now, d)
                prev = self.last.get(zid)
                if prev is not None and now - prev[0] >= CLOSING_DT_MIN:
                    v = (prev[1] - d) / (now - prev[0])
                    old = self.closing.get(zid)
                    self.closing[zid] = v if old is None else CLOSING_EMA * v + (1.0 - CLOSING_EMA) * old
        self.last = seen
        self.closing = {zid: v for zid, v in self.closing.items() if zid in seen}
        h = me.get("hitReaction")
        h = h if isinstance(h, str) else ""
        self.hit_onset = bool(h) and not self.hit
        self.hit = h
        now_b = frozenset(p.i for p in bleeding_parts(world))
        self.new_bleeding = tuple(sorted(now_b - self.bleeding))
        self.bleeding = now_b


def bleeding_parts(world):
    """The bleeding parts (`Part`), the longest bleeding first, ties by the index."""
    out = []
    for p in (world.body or {}).get("parts") or ():
        if isinstance(p, dict) and p.get("bleeding") is True and isinstance(p.get("i"), int):
            bt = p.get("bleedingTime")
            out.append(Part(p["i"], float(bt) if _num(bt) else 0.0, p.get("h")))
    return tuple(sorted(out, key=lambda p: (-p.bleeding_time, p.i)))


def read(world, now, tracks=None, dead=()):
    """The frame's `Situation` (the module docstring); `tracks` its cross-frame readings (a fresh one reads every
    closing speed 0 and no onset), `dead` the ids read dead and still listed."""
    me = world.me or {}
    body = world.body or {}
    st = world.stats or {}
    mx, my = me.get("x"), me.get("y")
    mx, my = (mx if _num(mx) else 0.0), (my if _num(my) else 0.0)
    closing = tracks.closing if tracks is not None else {}
    zeds = []
    for zid, z in world.zombies.items():
        if zid in dead or not (_num(z.get("x")) and _num(z.get("y"))):
            continue
        chasing = z.get("hasTarget") is True
        state = z.get("state") if isinstance(z.get("state"), str) else None
        zeds.append(Zed(zid, z["x"], z["y"], math.hypot(z["x"] - mx, z["y"] - my), z.get("onFloor") is not True,
                        chasing, chasing and z.get("known") is not False, state in ATTACK_STATES, z.get("health"),
                        closing.get(zid, 0.0)))
    zeds.sort(key=lambda q: (q.d, repr(q.id)))
    weapon = world.weapon
    reach = (weapon or {}).get("reach") if isinstance(weapon, dict) else None
    sq = world.map.get((int(math.floor(mx)), int(math.floor(my)), me_floor(world))) or {}
    hit = me.get("hitReaction")
    health = body.get("health")
    return Situation(
        now=now, x=mx, y=my, z=me_floor(world), armed=weapon is not None, reach=reach if _num(reach) else 0.0,
        health=health if _num(health) else 100.0, arm_pain=body.get("armPain"), endurance=st.get("endurance"),
        fatigue=st.get("fatigue"), moving=me.get("moving") is True, aiming=me.get("aiming") is True,
        hit_reaction=hit if isinstance(hit, str) else "", attackers=me.get("attackers") or 0, zeds=tuple(zeds),
        bleeding=bleeding_parts(world), on_room=on_room(world), building=sq.get("building"),
        hit_onset=tracks.hit_onset if tracks is not None else False,
        new_bleeding=tracks.new_bleeding if tracks is not None else ())
