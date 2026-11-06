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
    (#4687) and a knocked-down zombie does not until it rises; and it yields while a standing zombie is within the
    meet's HANDBACK_R (fix 1, review-t13-mix2 F2a: the meet hands a finish back then, trial 10's lines 98, 99 and
    116), P3's `reach` taking the standing one;
  - `fallen`: a zombie lying on the floor within FIGHT_REACH, none standing within KEEP_R, no fight skip on it (T's
    `fallen` guard: the standing ones dealt with first, then the finish).
  A zombie whose melee backed off (`mem.backoff`) is in no guard until BACKOFF_TICKS pass (D's Strike's rule); a fight
  skip (`mem.skip`) holds off the two finishes only: a standing zombie in the swing radius is met whatever the skip
  (D's "still struck at P0"); a handback hold (`Memory.hold`: HANDBACK_MAX handbacks in a row at one pin, fix 1, F2b)
  holds a zombie out of every guard and every Fight's want for SKIP_S. Each guard is a Fight to the kill
  (`intents.Fight`), never one press.
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
    pair fought when it comes (the read's item 3). The predicate is one function (`lone_idle`), read by the want and by
    a running seek Fight's end alike (fix 1, F1: `intents.Fight.lapsed`);
  - `downed`: D's, a fallen zombie within DOWNED_R with no standing one within it.
  The string is gone with D's Fight's string state (the read: trial 10's pair arrived together anyway).

Health is read by none of them (memory `stand-and-fight-dress-first`)."""
import dataclasses
import math

from agent.base.planner.doctrine import situation as DS
from agent.base.planner.doctrine.situation import Want, aware
from agent.base.planner.mix_2 import constants as K
from agent.base.planner.mix_2.constants import DK
from agent.base.planner.policies import line_to, on_floor, target_id_ok


@dataclasses.dataclass
class Memory(DS.Memory):
    """D's memory (`doctrine.situation.Memory`) with the handback hold: zombie id -> wall until it is held out of every
    Fight's want after HANDBACK_MAX handbacks in a row (fix 1, review-t13-mix2 F2b)."""
    hold: dict = dataclasses.field(default_factory=dict)


def crawling(z):
    """Zombie record `z` crawls (the frame's `crawler`, PZA/1.x's `isCrawling`; it lies on the floor with `onFloor`):
    the tactical view's own read (`tactician.tview`: `crawler` first)."""
    return z.get("crawler") is True


def _free(world, near, behind):
    return [e for e in near if e[1] not in behind and line_to(world, e[2]) is not False]


def populations(world, mem, now):
    """(near, behind, free, upright): every listed zombie not read dead, nearest first (`doctrine.situation.listed`);
    those behind a door or a window within DOOR_R (`portals`); those with no portal and no wall between (`free`,
    #4681); the free ones standing (`upright`). The one population every want and the Fight's re-pin read."""
    near = DS.listed(world, mem, now)
    behind = DS.portals(world, near)
    free = _free(world, near, behind)
    return near, behind, free, [e for e in free if not on_floor(e[2])]


def held(mem, zid, now):
    """The zombie is held out of every Fight's want after a bounded handback loop (`Memory.hold`, HANDBACK_MAX)."""
    return (getattr(mem, "hold", None) or {}).get(zid, -math.inf) > now


def _ok(mem, now, e):
    """A Fight's target: a valid id, no fight skip on it (`mem.skip`) and no handback hold."""
    return target_id_ok(e[1]) and mem.skip.get(e[1], -math.inf) <= now and not held(mem, e[1], now)


def guard(world, mem, now, free, upright):
    """The P0 want (the module docstring), else None."""
    up = [e for e in upright if not mem.backoff.get(e[1]) and target_id_ok(e[1]) and not held(mem, e[1], now)]
    if (world.me or {}).get("hitReaction"):
        hit = [e for e in up if e[0] <= K.MELEE_RELEASE_R]
        if hit:
            return _want(K.P_GUARD, hit[0], "hit")
    swing = [e for e in up if e[0] <= K.SWING_GUARD_R]
    if swing:
        return _want(K.P_GUARD, swing[0], "swing")
    down = [e for e in free if on_floor(e[2]) and not mem.backoff.get(e[1]) and _ok(mem, now, e)]
    crawl = [e for e in down if crawling(e[2]) and e[0] <= K.KEEP_R]
    if crawl and not any(e[0] <= K.HANDBACK_R for e in upright):   # fix 1 (review-t13-mix2 F2a): it yields to a
        #                    standing zombie the meet would hand its finish back for (HANDBACK_R); P3's `reach` then
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
    return [e for e in populations(world, mem, now)[2] if crawling(e[2]) and e[0] <= r]


def reach(world, mem, now, upright):
    """P3's `reach` want (T's fallback `reach` rule): armed, the nearest standing zombie within KEEP_R, else None. The
    Fight's `second_standing` re-pin reads it too, so its next want is the zombie it read."""
    if world.weapon is None:
        return None
    r = [e for e in upright if e[0] <= K.KEEP_R and _ok(mem, now, e)]
    return _want(K.P_FIGHT, r[0], "reach") if r else None


def lone_idle(world, mem, now, near, upright, seek, pin=None):
    """The seek's predicate, read by the want and by a running seek Fight's end alike (fix 1, review-t13-mix2 F1):
    armed, a reachability read (`seek`), exactly one standing zombie listed within SEEK_R wherever it stands (with
    `pin`: none but the pin, the pin itself read at any distance, so a pin just past SEEK_R inside DISENGAGE_R keeps the
    seek's hysteresis), that one idle, free, reachable, no skip or hold on it. Its (tiles, id, record), else None."""
    if world.weapon is None or seek is None:
        return None
    others = [e for e in near if not on_floor(e[2]) and e[0] <= K.SEEK_R and e[1] != pin]
    if pin is None:
        if len(others) != 1:
            return None
        cand = others[0]
    else:
        if others:
            return None
        cand = next((e for e in near if e[1] == pin and not on_floor(e[2])), None)
    if cand is None or aware(cand[2]) or cand not in upright or not _ok(mem, now, cand) or not seek(cand[1], cand[2]):
        return None
    return cand


def _fight(world, mem, now, near, free, upright, strung, avoid, stand, seek):
    """The P3 want (the module docstring), else None. `avoid`: the group's Avoid is wanted (no P3)."""
    if avoid:
        return None

    def ok(e):
        return _ok(mem, now, e)
    r = reach(world, mem, now, upright)
    if r is not None:
        return r
    able = [e for e in upright if aware(e[2]) and e[0] <= DK.ENGAGE_R and ok(e)]
    if able:
        lead = able[0]
        why = {"n": len(able), "strung": strung}
        if stand is not None:
            g = DS.ground(world, stand)
            why.update(stand=True, ground=None if g is None else [g[0], g[1], g[2]])
        return _want(K.P_FIGHT, lead, "stand" if stand is not None else "fight", **why)
    lone = lone_idle(world, mem, now, near, upright, seek)
    if lone is not None:
        return _want(K.P_FIGHT, lone, "seek")
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
    near, behind, free, upright = populations(world, mem, now)
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


__all__ = ["Memory", "read", "guard", "reach", "lone_idle", "populations", "held", "crawling", "crawlers_near",
           "piece_of", "Want"]
