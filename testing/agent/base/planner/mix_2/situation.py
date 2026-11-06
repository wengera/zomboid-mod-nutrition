"""mix_2's read of the situation (Plan 31 Task 13; `task-13-composition-read.md` section 7, mix_2): `read(world, mem,
now, seek)`, the wants of the six priorities top down, each a doctrine `Want(p, kind, target, why, ids)` whose `why`
names its `piece` (the rule that answers). It is the doctrine's read (`doctrine.situation.read`) with three changes and
everything else imported unchanged: the listing, the portals and the straight-line exclusions (#4681), the group, the
refuge and the stand's ground, the door's decision and the order.

- P0 `fight` (in place of D's one-press Strike, the read's item 1), the tactician's guards (`Tactician._guard`) and the
  crawler's finish, the first that holds:
  - `hit`: the frame's hit reaction (`me.hitReaction`) with a standing zombie within MELEE_RELEASE_R: the nearest;
  - `swing`: a standing zombie within SWING_GUARD_R: the nearest;
  - `crawler`: a crawler (`crawler` true, lying on the floor) within KEEP_R and no fight skip on it (the read's item 2:
    "a crawler within KEEP_R is a P0 finish"; it bit through D's dress three times in trial 10); after the swing guard,
    so a standing zombie within SWING_GUARD_R is met first, before any standing one beyond it, since a crawler bites
    (#4687) and a knocked-down zombie does not until it rises;
  - `fallen`: a zombie lying on the floor within FIGHT_REACH, none standing within KEEP_R, no fight skip on it (T's
    `fallen` guard: the standing ones dealt with first, then the finish).
  A zombie whose melee backed off (`mem.backoff`) is in no guard until BACKOFF_TICKS pass (D's Strike's rule); a fight
  skip (`mem.skip`) holds off the two finishes only: a standing zombie in the swing radius is met whatever the skip
  (D's "still struck at P0"). Each guard is a Fight to the kill (`intents.Fight`), never one press.
- P1 `dress`: D's, with a crawler within KEEP_R holding it off as a standing zombie does (the read's item 2, T's rule
  order: "the Dress only with nothing standing or crawling within KEEP_R").
- P3 `fight`, the first that holds, armed where it says so:
  - `reach` (armed): the nearest standing zombie within KEEP_R, aware or not (T's fallback `reach` rule). It is the
    re-pin's other half: a Fight ends `done repin` when a nearer standing zombie reads within KEEP_R (`intents.Fight`),
    and the next want names that one (the read's item 1, "the next tick's P3 takes the nearest");
  - `fight` / `stand`: D's, the nearest standing aware zombie within ENGAGE_R, the stand's ground with a group and no
    refuge;
  - `seek` (armed): exactly one standing zombie listed within SEEK_R, wherever it stands (behind a wall or a door it
    still counts as the second), none aware, that one free and reachable (`seek(zid, z)`: the ladder's
    `engage.Engage._engageable` over its own flood, `seek.Reach`), no fight skip on it: the ladder's seek
    (`engage.Engage._sought`) cut to one zombie (P24-AT's `_lone`). Two or more listed: none sought, the farther of a
    pair fought when it comes (the read's item 3);
  - `downed`: D's, a fallen zombie within DOWNED_R with no standing one within it.
  The string is gone with D's Fight's string state (the read: trial 10's pair arrived together anyway).

Health is read by none of them (memory `stand-and-fight-dress-first`)."""
import math

from agent.base.planner.doctrine import situation as DS
from agent.base.planner.doctrine.situation import Want, aware
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.policies import line_to, on_floor, target_id_ok


def crawling(z):
    """Zombie record `z` crawls (the frame's `crawler`, PZA/1.x's `isCrawling`; it lies on the floor with `onFloor`):
    the tactical view's own read (`tactician.tview`: `crawler` first)."""
    return z.get("crawler") is True


def _free(world, near, behind):
    return [e for e in near if e[1] not in behind and line_to(world, e[2]) is not False]


def guard(world, mem, now, free, upright):
    """The P0 want (the module docstring), else None."""
    up = [e for e in upright if not mem.backoff.get(e[1]) and target_id_ok(e[1])]
    if (world.me or {}).get("hitReaction"):
        hit = [e for e in up if e[0] <= K.MELEE_RELEASE_R]
        if hit:
            return _want(K.P_GUARD, hit[0], "hit")
    swing = [e for e in up if e[0] <= K.SWING_GUARD_R]
    if swing:
        return _want(K.P_GUARD, swing[0], "swing")
    down = [e for e in free if on_floor(e[2]) and not mem.backoff.get(e[1]) and target_id_ok(e[1])
            and mem.skip.get(e[1], -math.inf) <= now]
    crawl = [e for e in down if crawling(e[2]) and e[0] <= K.KEEP_R]
    if crawl:
        return _want(K.P_GUARD, crawl[0], "crawler")
    fallen = [e for e in down if e[0] <= K.FIGHT_REACH]
    if fallen and not any(e[0] <= K.KEEP_R for e in upright):
        return _want(K.P_GUARD, fallen[0], "fallen")
    return None


def _want(p, e, piece, **why):
    d, zid, _ = e
    return Want(p, "fight", zid, dict({"d": d, "piece": piece}, **why), (zid,))


def crawlers_near(world, mem, now, r=None):
    """(tiles, id, record) of the crawlers listed within `r` (KEEP_R) not behind a door, a window or a wall."""
    r = K.KEEP_R if r is None else r
    near = DS.listed(world, mem, now)
    behind = DS.portals(world, near)
    return [e for e in _free(world, near, behind) if crawling(e[2]) and e[0] <= r]


def _fight(world, mem, now, near, free, upright, strung, avoid, stand, seek):
    """The P3 want (the module docstring), else None. `avoid`: the group's Avoid is wanted (no P3)."""
    if avoid:
        return None
    armed = world.weapon is not None

    def ok(e):
        return target_id_ok(e[1]) and mem.skip.get(e[1], -math.inf) <= now
    if armed:
        reach = [e for e in upright if e[0] <= K.KEEP_R and ok(e)]
        if reach:
            return _want(K.P_FIGHT, reach[0], "reach")
    able = [e for e in upright if aware(e[2]) and e[0] <= DK.ENGAGE_R and ok(e)]
    if able:
        lead = able[0]
        why = {"n": len(able), "strung": strung}
        if stand is not None:
            g = DS.ground(world, stand)
            why.update(stand=True, ground=None if g is None else [g[0], g[1], g[2]])
        return _want(K.P_FIGHT, lead, "stand" if stand is not None else "fight", **why)
    if armed and seek is not None:
        listed = [e for e in near if not on_floor(e[2]) and e[0] <= K.SEEK_R]
        if len(listed) == 1 and not aware(listed[0][2]) and listed[0] in upright and ok(listed[0]) and \
                seek(listed[0][1], listed[0][2]):
            return _want(K.P_FIGHT, listed[0], "seek")
    if any(e[0] <= DK.DOWNED_R for e in upright):
        return None
    downed = [e for e in free if on_floor(e[2]) and e[0] <= DK.DOWNED_R and ok(e)]
    if downed:
        return _want(K.P_FIGHT, downed[0], "downed", downed=True)
    return None


def read(world, mem, now, seek=None):
    """The wants of the six priorities this tick, top down (the module docstring); the last is always the order. It
    writes `mem.bandage_want` and may clear a lifted dress hold (D's `_dress`), nothing else. `seek(zid, z)` is the
    reachability of the lone idle zombie (`seek.Reach.engageable`); None reads no seek."""
    near = DS.listed(world, mem, now)
    behind = DS.portals(world, near)
    free = _free(world, near, behind)
    upright = [e for e in free if not on_floor(e[2])]
    wants = []
    g = guard(world, mem, now, free, upright)
    if g is not None:
        wants.append(g)
    crawl = [e for e in free if crawling(e[2]) and e[0] <= DK.DRESS_CLEAR_R]
    d = DS._dress(world, mem, now, upright + crawl)   # D's dress read, a crawler holding it off as a standing one does
    if d is not None:
        d.why["piece"] = "dress"
        wants.append(d)
    group = [e for e in upright if aware(e[2]) and e[0] <= DK.GROUP_R]
    strung = len(group) >= DK.GROUP_N and group[1][0] - group[0][0] >= DK.STRING_GAP
    armed = world.weapon is not None
    is_group = (len(group) >= DK.GROUP_N and not strung) or (not armed and len(group) >= 2)
    held = mem.avoid_until > now
    stand = None
    if is_group and not held:
        zs = [z for _, _, z in group]
        ref = DS.refuge(world, zs)
        if ref is not None:
            wants.append(Want(K.P_AVOID, "avoid", ref, {"n": len(group), "nearest": group[0][0], "piece": "avoid"},
                              tuple(e[1] for e in group)))
        else:
            stand = zs   # no named refuge: the stand where the character is (the controller's ruling on D's M5)
    f = _fight(world, mem, now, near, free, upright, strung, is_group and not held and stand is None, stand, seek)
    if f is not None:
        wants.append(f)
    door = DS._door(world, mem, now, near, behind)
    if door is not None:
        door.why["piece"] = "door"
        wants.append(door)
    wants.append(Want(K.P_ORDER, "order", None, {"piece": "order"}))
    return wants


def piece_of(want):
    """The want's piece (the decision line's `pieces`)."""
    return (want.why or {}).get("piece", want.kind)


__all__ = ["read", "guard", "crawling", "crawlers_near", "piece_of", "Want"]
