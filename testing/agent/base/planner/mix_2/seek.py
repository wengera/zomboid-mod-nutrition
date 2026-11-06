"""The lone-idle seek's reachability (Plan 31 Task 13, mix_2's item (d); `task-13-composition-read.md` section 7):
`Reach(world, clock).engageable(zid, z)`, the ladder's own test (`engage.Engage._engageable`, ruling P24-X and Plan 24
Task 18 fixes 1 and 2), called unedited through the `Engage` mixin over an object holding only what it reads: the World,
the clock, its own `unsought` marks and its own bounded flood (`_flood`). The Survive's ladder state is never written
(its `unsought` and `_flood` are the ladder's), and the World's map is the one Survive's `_read` keeps.

What it answers (the ladder's docstring, `engage.py`): the zombie is on the character's side of a building's walls, and
chasing, or its straight line clear, or a square beside it in the player's bounded flood (ENGAGE_R + 2 tiles, a closed
door shut, a hoppable fence open); held ground (a room or door square) never seeks an idle zombie beyond DANGER_R; one
that is not reachable is marked `unsought` for UNREACHABLE_S, no flood re-read meanwhile."""
from agent.base.planner.engage import Engage


class Reach(Engage):
    """The `Engage` mixin's reachability reads over a World (the module docstring)."""

    def __init__(self, world, clock):
        self.world = world
        self.clock = clock
        self.unsought = {}   # zombie id -> wall until no reach re-read (`Engage._engageable`)
        self._flood = None   # (map version, player square, squares): the bounded flood (`Engage._reach`)

    def engageable(self, zid, z):
        return self._engageable(zid, z)


__all__ = ["Reach"]
